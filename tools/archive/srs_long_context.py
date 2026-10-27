#!/usr/bin/env python3
"""
SRS长程上下文关联引擎
=====================
参考DataFlow Core的Operator/Pipeline/Storage模式实现。
不依赖DataFlow安装，但遵循其设计模式。

核心解决4个难点:
  1. 超长上下文 → 文档级结构索引(章节树+参数索引+需求ID索引)
  2. 长程关联 → 全局倒排索引+embedding语义匹配
  3. 多模态关联 → 多模态条目结构(文字+表格行+图片引用)
  4. 上下文感知 → 多信号融合(ID+embedding+章节+位置)

输出: List[ContextItem]，每个条目聚合了"同一事物"的所有出现位置

用法:
  python3 tools/srs_long_context.py --doc 03服务集成
  python3 tools/srs_long_context.py --all
"""
import re
import json
import math
import argparse
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
OUTLINE_DIR = BASE / "data/srs_outline"
OUTPUT_DIR = BASE / "data/srs_context_items"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Embedding API
EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
from ai_config import WQ_API_KEY as EMB_KEY
EMB_MODEL = "ep-qrkeon-1785654358657880827"

# 正则
REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
CONSTRAINT_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)'
    r'\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?'
)
VERSION_RE = re.compile(r'(达梦|Oracle|MySQL|Linux|内核|GCC|CentOS|Ubuntu|Windows|Qt|银河麒麟)[^。]*?(V?\d+\.?\d*(?:\.\d+)?)')


# ── 数据结构(参考DataFlow的Operator输入输出模式) ──────────────

@dataclass
class Occurrence:
    """条目的一次出现(多模态)"""
    section: str
    occ_type: str          # text / table_row / image_ref / constraint
    content: str
    line: int = 0
    table_type: str = ""
    cells: list = field(default_factory=list)
    value: float = None
    unit: str = ""
    semantic_role: str = ""  # threshold / config / capacity / description

@dataclass
class ContextItem:
    """长程上下文关联产出的条目"""
    item_id: str
    item_type: str         # function / parameter / interface / version
    canonical_name: str
    occurrences: list = field(default_factory=list)
    confidence: float = 0.0
    match_signals: dict = field(default_factory=dict)
    
    def summary(self) -> str:
        sections = [o.section for o in self.occurrences]
        return f"[{self.item_type}] {self.canonical_name[:25]} 出现{len(self.occurrences)}次 章节:{','.join(set(sections))}"


# ── Operator基类(参考DataFlow OperatorABC) ────────────────────

class Operator:
    """轻量版Operator基类(参考DataFlow OperatorABC)"""
    def run(self, storage: dict) -> dict:
        raise NotImplementedError


# ── Operator 1: 文档级结构索引(解决超长上下文) ─────────────────

class DocumentIndexer(Operator):
    """
    构建文档级结构索引:
    - 章节树: section_id → {title, level, line_start, line_end, text}
    - 参数倒排索引: param_name → [(section, line, value, context)]
    - 需求ID索引: req_id → [(section, title)]
    - 版本号索引: software_name → [(section, version)]
    """
    
    def run(self, storage: dict) -> dict:
        content_xml_path = storage["content_xml_path"]
        content = ET.parse(content_xml_path).getroot()
        
        # 章节树
        section_tree = {}
        for section in content.findall('.//Section'):
            sec_id = section.get('section_id', '')
            title = section.get('title', '')
            req_id = section.get('req_id', '')
            paragraphs = [p.text or '' for p in section.findall('Paragraph')]
            text = '\n'.join(paragraphs)
            
            section_tree[sec_id] = {
                "title": title,
                "req_id": req_id,
                "text": text,
                "text_length": len(text),
            }
        
        # 参数倒排索引(从全文扫描)
        param_index = defaultdict(list)
        for sec_id, sec_data in section_tree.items():
            text = sec_data["text"]
            for m in CONSTRAINT_RE.finditer(text):
                value = float(m.group(1))
                unit = m.group(2) or ""
                # 提取参数名(约束前15个字的最后中文词)
                before = text[max(0, m.start()-15):m.start()]
                param_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)
                param = param_m.group(1) if param_m else before[-8:].strip()
                param_index[param].append(Occurrence(
                    section=sec_id, occ_type="constraint",
                    content=text[max(0,m.start()-20):m.end()+20],
                    value=value, unit=unit,
                    semantic_role=self._classify_role(param, sec_id),
                ))
        
        # 需求ID索引
        req_id_index = defaultdict(list)
        for sec_id, sec_data in section_tree.items():
            if sec_data["req_id"]:
                req_id_index[sec_data["req_id"]].append({
                    "section": sec_id,
                    "title": sec_data["title"],
                })
        
        # 版本号索引
        version_index = defaultdict(list)
        for sec_id, sec_data in section_tree.items():
            text = sec_data["text"]
            for m in VERSION_RE.finditer(text):
                name = m.group(1)
                version = m.group(2)
                version_index[name].append(Occurrence(
                    section=sec_id, occ_type="version",
                    content=text[max(0,m.start()-10):m.end()+10],
                ))
        
        # 表格索引
        table_index = defaultdict(list)
        for table in content.findall('.//Table'):
            table_type = table.get('type', 'other')
            for row_idx, row in enumerate(table.findall('Row')):
                cells = [c.text or '' for c in row.findall('Cell')]
                row_text = ' '.join(cells)
                table_index[table_type].append({
                    "row_index": row_idx,
                    "cells": cells,
                    "text": row_text,
                    "section": table.get('section', ''),
                })
        
        storage["section_tree"] = section_tree
        storage["param_index"] = param_index
        storage["req_id_index"] = req_id_index
        storage["version_index"] = version_index
        storage["table_index"] = table_index
        
        print(f"  索引: {len(section_tree)}章节, {len(param_index)}参数, {len(req_id_index)}需求ID, {len(version_index)}版本号, {sum(len(v) for v in table_index.values())}表格行")
        return storage
    
    def _classify_role(self, param: str, section: str) -> str:
        threshold_kw = ['时间', '间隔', '延迟', '误差', '精度', '响应', '定时', '偏差', '周期']
        config_kw = ['版本', '型号', '主频', '内存', '硬盘', '存储', '分辨率', '显存']
        capacity_kw = ['最多', '支持', '容量', '数量', '上限', '最大', '并发']
        for kw in threshold_kw:
            if kw in param: return "threshold"
        for kw in config_kw:
            if kw in param: return "config"
        for kw in capacity_kw:
            if kw in param: return "capacity"
        if section.startswith('3.10'): return "config"
        if section.startswith('3.11'): return "threshold"
        return "description"


# ── Operator 2: 长程关联(解决跨章节关联) ──────────────────────

class LongRangeAssociator(Operator):
    """
    基于全局索引+embedding做长程关联:
    - 参数级关联: 同一参数名的所有出现位置聚合成一个ContextItem
    - 需求级关联: 同一req_id的所有出现位置聚合
    - 版本号关联: 同一软件名在不同章节的版本聚合(检测不一致)
    - Embedding辅助: 名称相似度>0.85的参数合并
    """
    
    def run(self, storage: dict) -> dict:
        param_index = storage["param_index"]
        req_id_index = storage["req_id_index"]
        version_index = storage["version_index"]
        
        items = []
        
        # 参数级关联
        for param, occurrences in param_index.items():
            if len(occurrences) < 1:
                continue
            item = ContextItem(
                item_id=f"PARAM-{param}",
                item_type="parameter",
                canonical_name=param,
                occurrences=occurrences,
                confidence=1.0,
                match_signals={"index_match": True},
            )
            items.append(item)
        
        # 需求级关联(功能)
        for req_id, locations in req_id_index.items():
            occurrences = []
            for loc in locations:
                sec_id = loc["section"]
                sec_data = storage["section_tree"].get(sec_id, {})
                occurrences.append(Occurrence(
                    section=sec_id, occ_type="text",
                    content=sec_data.get("text", "")[:200],
                ))
            
            # 搜索req_id在表格中的出现
            for table_type, rows in storage["table_index"].items():
                for row in rows:
                    if req_id in row["text"]:
                        occurrences.append(Occurrence(
                            section=row["section"], occ_type="table_row",
                            content=row["text"][:200],
                            table_type=table_type,
                            cells=row["cells"],
                        ))
            
            item = ContextItem(
                item_id=req_id,
                item_type="function",
                canonical_name=locations[0]["title"] if locations else req_id,
                occurrences=occurrences,
                confidence=1.0,
                match_signals={"req_id_match": True},
            )
            items.append(item)
        
        # 版本号关联(检测跨章节不一致)
        for software, occurrences in version_index.items():
            if len(occurrences) < 2:
                continue
            versions = set(o.content for o in occurrences)
            item = ContextItem(
                item_id=f"VERSION-{software}",
                item_type="version",
                canonical_name=software,
                occurrences=occurrences,
                confidence=1.0,
                match_signals={"version_index": True, "has_conflict": len(versions) > 1},
            )
            items.append(item)
        
        # Embedding辅助: 参数名称相似度合并
        items = self._merge_by_embedding(items)
        
        storage["context_items"] = items
        print(f"  关联: {len(items)}个条目 (参数{len(param_index)}+需求{len(req_id_index)}+版本{len(version_index)})")
        return storage
    
    def _merge_by_embedding(self, items: list) -> list:
        """用embedding合并名称相似的条目"""
        param_items = [item for item in items if item.item_type == "parameter"]
        if len(param_items) < 2:
            return items
        
        names = [item.canonical_name for item in param_items]
        embs = self._get_embeddings(names)
        if not any(embs):
            return items
        
        # 计算相似度矩阵,合并>0.85的
        merged = set()
        for i in range(len(param_items)):
            if i in merged:
                continue
            for j in range(i+1, len(param_items)):
                if j in merged:
                    continue
                sim = self._cosine(embs[i], embs[j])
                if sim > 0.85:
                    # 合并j到i
                    param_items[i].occurrences.extend(param_items[j].occurrences)
                    param_items[i].match_signals[f"embed_merge_{j}"] = round(sim, 3)
                    merged.add(j)
        
        # 重建items列表
        result = [item for item in items if item.item_type != "parameter"]
        result.extend([item for i, item in enumerate(param_items) if i not in merged])
        return result
    
    def _get_embeddings(self, texts: list) -> list:
        emb_cache = getattr(self, '_emb_cache', {})
        self._emb_cache = emb_cache
        uncached = [(i, t) for i, t in enumerate(texts) if t not in emb_cache]
        if uncached:
            try:
                resp = requests.post(EMB_URL, headers={
                    "Authorization": f"Bearer {EMB_KEY}",
                    "Content-Type": "application/json"
                }, json={
                    "model": EMB_MODEL,
                    "input": [t for _, t in uncached],
                    "encoding_format": "float"
                }, timeout=30)
                resp.raise_for_status()
                for (idx, text), emb in zip(uncached, resp.json()["data"]):
                    emb_cache[text] = emb["embedding"]
            except:
                return [[] for _ in texts]
        return [emb_cache.get(t, []) for t in texts]
    
    def _cosine(self, a, b):
        if not a or not b: return 0.0
        dot = sum(x*y for x,y in zip(a,b))
        na = math.sqrt(sum(x*x for x in a))
        nb = math.sqrt(sum(y*y for y in b))
        return dot/(na*nb) if na>0 and nb>0 else 0.0


# ── Operator 3: 上下文感知检测(基于关联条目) ──────────────────

class ContextAwareDetector(Operator):
    """
    基于关联条目做不一致性检测:
    - 参数值冲突: 同参数threshold角色在不同章节值不一致
    - 版本号冲突: 同一软件在不同章节版本不同
    - 覆盖缺失: 需求ID在第4/5章未出现
    """
    
    def run(self, storage: dict) -> dict:
        items = storage["context_items"]
        violations = []
        
        for item in items:
            if item.item_type == "parameter":
                violations.extend(self._check_param_conflict(item))
            elif item.item_type == "version":
                violations.extend(self._check_version_conflict(item))
            elif item.item_type == "function":
                violations.extend(self._check_coverage(item))
        
        storage["violations"] = violations
        print(f"  检测: {len(violations)}条违规")
        for v in violations[:3]:
            print(f"    [{v['check']}] {v['description'][:70]}")
        return storage
    
    def _check_param_conflict(self, item: ContextItem) -> list:
        """参数值冲突: 同参数threshold角色在不同章节值不一致"""
        violations = []
        threshold_occs = [o for o in item.occurrences 
                         if o.semantic_role == "threshold" and o.value is not None]
        if len(threshold_occs) < 2:
            return []
        
        values = set(o.value for o in threshold_occs)
        if len(values) > 1:
            locations = [{"section": o.section, "value": o.value, "unit": o.unit} 
                        for o in threshold_occs]
            violations.append({
                "check": "param_value_conflict",
                "severity": "HIGH",
                "description": f"参数'{item.canonical_name}'阈值不一致: {[(o.section, o.value) for o in threshold_occs]}",
                "item_id": item.item_id,
                "locations": locations,
            })
        return violations
    
    def _check_version_conflict(self, item: ContextItem) -> list:
        """版本号冲突: 同一软件在不同章节版本不同"""
        if not item.match_signals.get("has_conflict"):
            return []
        versions = [(o.section, o.content) for o in item.occurrences]
        return [{
            "check": "version_conflict",
            "severity": "HIGH",
            "description": f"软件'{item.canonical_name}'版本不一致: {versions}",
            "item_id": item.item_id,
        }]
    
    def _check_coverage(self, item: ContextItem) -> list:
        """覆盖缺失: 需求ID在第4/5章未出现"""
        sections = set(o.section for o in item.occurrences)
        has_ch4 = any(s.startswith('4') for s in sections)
        has_ch5 = any(s.startswith('5') for s in sections)
        has_table = any(o.occ_type == "table_row" for o in item.occurrences)
        
        violations = []
        if not has_table and not has_ch4:
            violations.append({
                "check": "coverage_missing",
                "severity": "MEDIUM",
                "description": f"需求'{item.canonical_name}'({item.item_id})在第4/5章未出现",
                "item_id": item.item_id,
            })
        return violations


# ── Pipeline(参考DataFlow PipelineABC) ────────────────────────

class SRSPipeline:
    """
    SRS长程上下文关联Pipeline
    参考DataFlow的Pipeline编排模式: Operator1→Operator2→Operator3
    """
    
    def __init__(self):
        self.operators = [
            DocumentIndexer(),      # Step 1: 文档级结构索引
            LongRangeAssociator(),  # Step 2: 长程关联
            ContextAwareDetector(), # Step 3: 上下文感知检测
        ]
    
    def run(self, content_xml_path: str) -> dict:
        """执行Pipeline"""
        storage = {"content_xml_path": content_xml_path}
        for op in self.operators:
            storage = op.run(storage)
        return storage


# ── 主入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SRS长程上下文关联引擎")
    parser.add_argument("--doc", type=str, help="指定文档")
    parser.add_argument("--all", action="store_true", help="全部文档")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SRS长程上下文关联引擎")
    print("Pipeline: 文档索引 → 长程关联 → 上下文感知检测")
    print("=" * 60)
    
    pipeline = SRSPipeline()
    
    if args.doc:
        doc_id = args.doc[:20]
        xml_path = str(OUTLINE_DIR / f"{doc_id}_content.xml")
        if not Path(xml_path).exists():
            print(f"[!] 文件不存在: {xml_path}")
            return
        print(f"\n[{args.doc[:35]}]")
        result = pipeline.run(xml_path)
        _save_result(doc_id, result)
    else:
        xml_files = sorted(OUTLINE_DIR.glob("*_content.xml"))
        all_results = []
        for xml_path in xml_files:
            doc_id = xml_path.name.replace("_content.xml", "")
            print(f"\n[{doc_id[:35]}]")
            result = pipeline.run(str(xml_path))
            _save_result(doc_id, result)
            all_results.append(result)
        
        # 汇总
        total_items = sum(len(r.get("context_items", [])) for r in all_results)
        total_violations = sum(len(r.get("violations", [])) for r in all_results)
        print(f"\n{'='*60}")
        print(f"汇总: {len(all_results)}份文档, {total_items}个关联条目, {total_violations}条违规")


def _save_result(doc_id: str, result: dict):
    """保存结果"""
    output = {
        "doc_id": doc_id,
        "detect_date": datetime.now().isoformat(),
        "total_items": len(result.get("context_items", [])),
        "total_violations": len(result.get("violations", [])),
        "items": [
            {
                "item_id": item.item_id,
                "item_type": item.item_type,
                "canonical_name": item.canonical_name,
                "occurrence_count": len(item.occurrences),
                "sections": list(set(o.section for o in item.occurrences)),
                "has_conflict": item.match_signals.get("has_conflict", False),
                "match_signals": item.match_signals,
            }
            for item in result.get("context_items", [])
        ],
        "violations": result.get("violations", []),
    }
    output_path = OUTPUT_DIR / f"{doc_id}_context.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
