#!/usr/bin/env python3
"""
SRS一致性校验 Pipeline v2 — 关联与检测彻底分离
================================================
方向A(上下文关联): 找到所有"潜在关联对"，不判断是否不一致
方向B(不一致性校验): 三层(语法/语义/逻辑)对Pair做判定

Pipeline:
  L2: 解析提取
    ├── ContentListReader → SectionExtractor → AssetExtractor
  L2/L3: 方向A — 上下文关联(只配对，不判定)
    ├── PairFinder — 找到7类潜在关联对
  L3: 方向B — 不一致性校验(三层判定)
    ├── SyntaxChecker — 语法层(GJB标准7项)
    ├── SemanticChecker — 语义层(值比较+NLI)
    └── LogicChecker — 逻辑层(Z3求解)

用法: python3 tools/srs_pipeline_v2.py --all
"""
import sys
import re
import json
import math
import argparse
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from html.parser import HTMLParser
from dataclasses import dataclass, field
from itertools import combinations

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "references/DataFlow"))
from dataflow.core.operator import OperatorABC

MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
OUTPUT_DIR = BASE / "data/srs_pipeline_v2_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
EMB_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
EMB_MODEL = "ep-qrkeon-1785654358657880827"

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')
CONSTRAINT_LE_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?')
CONSTRAINT_GE_RE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|≥|>=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?')
VERSION_RE = re.compile(
    r'(达梦|Oracle|MySQL|Linux|内核|GCC|CentOS|Ubuntu|Windows|Qt|银河麒麟|WPS|wps)'
    r'[^。]{0,15}?(V?\d+\.\d+(?:\.\d+)?)')  # 必须有至少一个小数点, 且15字内
EXPECTED_3X = [f'3.{i}' for i in range(1, 19)]


# ═══════════════════════════════════════════════════════════════
# L2: 解析提取 (从MinerU content_list提取结构化数据)
# ═══════════════════════════════════════════════════════════════

class TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cur_row, self.cur_cell, self.in_cell = [], [], [], False
    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.cur_row = []
        elif tag in ('td','th'): self.in_cell = True; self.cur_cell = []
    def handle_data(self, data):
        if self.in_cell: self.cur_cell.append(data.strip())
    def handle_endtag(self, tag):
        if tag in ('td','th') and self.in_cell:
            self.cur_row.append(' '.join(self.cur_cell)); self.in_cell = False
        elif tag == 'tr' and self.cur_row: self.rows.append(self.cur_row)


def _classify_table(caption, headers):
    c = (caption + ' '.join(headers)).lower()
    if any(kw in c for kw in ['序号','版本号','标记']): return 'modification'
    if any(kw in c for kw in ['需求名称','合格性方法','本文档章节号']): return 'qualification'
    if any(kw in c for kw in ['追踪','跟踪','任务书']): return 'traceability'
    if any(kw in c for kw in ['接口','信号']): return 'interface'
    if any(kw in c for kw in ['文档编号','标题','修订']): return 'reference'
    if any(kw in c for kw in ['功能名称','标识','子功能']): return 'capability'
    return 'other'

def _classify_role(param, section):
    for kw in ['时间','间隔','延迟','误差','精度','响应','定时','偏差','周期']:
        if kw in param: return "threshold"
    for kw in ['版本','型号','主频','内存','硬盘','存储','分辨率','显存']:
        if kw in param: return "config"
    for kw in ['最多','支持','容量','数量','上限','最大','并发']:
        if kw in param: return "capacity"
    if section.startswith('3.10'): return "config"
    if section.startswith('3.11'): return "threshold"
    return "description"

def _extract_constraints(text, section):
    # 先清洗HTML标签
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    results = []
    for m in CONSTRAINT_LE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-15):m.start()]
        pm = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)
        param = pm.group(1) if pm else before[-8:].strip()
        results.append({"param":param,"operator":"≤","value":val,"unit":unit,
                       "role":_classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section})
    for m in CONSTRAINT_GE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-15):m.start()]
        pm = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)
        param = pm.group(1) if pm else before[-8:].strip()
        results.append({"param":param,"operator":"≥","value":val,"unit":unit,
                       "role":_classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section})
    return results

def _extract_versions(text, section):
    return [{"software":m.group(1),"version":m.group(2),"section":section,
             "original":text[max(0,m.start()-10):m.end()+10]}
            for m in VERSION_RE.finditer(text)]

def _normalize_version(v):
    """版本号归一化: V7.6→7.6, V4.0.2→4.0.2, 7.6.0→7.6"""
    v = str(v).strip().lstrip("Vv")
    parts = v.split(".")
    while len(parts) > 1 and parts[-1] == "0":
        parts.pop()
    return ".".join(parts)


class L2_Parser(OperatorABC):
    """L2: 从MinerU content_list提取章节/表格/约束/版本/图片"""
    
    def run(self, content_list, **kwargs):
        sections = defaultdict(lambda: {"title":"","text":"","tables":[],
                                        "images":[],"constraints":[],"versions":[]})
        current = ""
        all_constraints, all_versions, all_req_ids = [], [], set()
        table_count, image_count = 0, 0
        
        for item in content_list:
            t = item.get("type","text")
            
            if t == "text":
                text = item.get("text","")
                level = item.get("text_level",0)
                if level > 0:
                    m = SECTION_RE.match(text.strip())
                    if m:
                        current = m.group(1)
                        sections[current]["title"] = m.group(2).strip()
                        req_m = REQ_ID_RE.search(m.group(2))
                        if req_m:
                            sections[current]["req_id"] = req_m.group(0)
                            all_req_ids.add(req_m.group(0))
                    continue
                if 'PAGEREF' in text: continue
                if current: sections[current]["text"] += text + "\n"
                cs, vs = _extract_constraints(text, current), _extract_versions(text, current)
                if cs: sections[current]["constraints"].extend(cs); all_constraints.extend(cs)
                if vs: sections[current]["versions"].extend(vs); all_versions.extend(vs)
                for m in REQ_ID_RE.finditer(text): all_req_ids.add(m.group(0))
            
            elif t == "table":
                table_count += 1
                body = item.get("table_body","")
                caption = ' '.join(item.get("table_caption",[]))
                parser = TableHTMLParser(); parser.feed(body)
                rows = parser.rows
                headers = rows[0] if rows else []
                ttype = _classify_table(caption, headers)
                full = caption + " " + body
                cs, vs = _extract_constraints(full, current), _extract_versions(full, current)
                if cs: sections[current]["constraints"].extend(cs); all_constraints.extend(cs)
                if vs: sections[current]["versions"].extend(vs); all_versions.extend(vs)
                for m in REQ_ID_RE.finditer(full): all_req_ids.add(m.group(0))
                sections[current]["tables"].append({
                    "table_id":f"T_{table_count}","type":ttype,"caption":caption,
                    "headers":headers,"rows":rows[1:] if len(rows)>1 else []})
            
            elif t == "image":
                image_count += 1
                sections[current]["images"].append({
                    "image_id":f"IMG_{image_count}",
                    "path":item.get("img_path",""),
                    "caption":' '.join(item.get("image_caption",[]))})
        
        return {"sections":dict(sections), "constraints":all_constraints,
                "versions":all_versions, "req_ids":sorted(all_req_ids)}


# ═══════════════════════════════════════════════════════════════
# 方向A: 上下文关联 — 只找潜在关联对，不判断是否不一致
# ═══════════════════════════════════════════════════════════════

@dataclass
class PotentialPair:
    """潜在关联对 — 描述同一事物的两个位置"""
    pair_id: str
    pair_type: str        # same_param / req_id_ref / same_version / text_table / image_text / cross_section / logic_constraint
    source: dict          # {section, content, value?, unit?, type}
    target: dict          # {section, content, value?, unit?, type}
    match_signal: str     # param_name / req_id / software_name / section_ref / image_ref / semantic / constraint_relation


class PairFinder(OperatorABC):
    """
    方向A核心: 找到所有"潜在关联对"
    
    7类关联对:
      1. same_param: 同参数名在不同章节出现 → 语义层值比较
      2. req_id_ref: 同需求ID在正文和表格出现 → 语法层覆盖完整性
      3. same_version: 同软件名在不同章节出现 → 语义层版本一致性
      4. text_table: 正文描述与表格行对应 → 语义层内容一致性
      5. image_text: 图片与所在章节文字 → 语义层图文一致性
      6. cross_section: 3.12设计约束 vs 3.2.X能力需求 → 语义层语义矛盾
      7. logic_constraint: 多个约束可能存在逻辑关系 → 逻辑层Z3求解
    """
    
    _emb_cache = {}
    
    def run(self, sections, constraints, versions, req_ids, **kwargs):
        pairs = []
        seq = 0
        
        # ── 1. 同参数跨章节对(只对threshold角色, 排除同用例不同步骤) ──
        param_groups = defaultdict(list)
        for c in constraints:
            param_groups[c["param"]].append(c)
        
        for param, cs in param_groups.items():
            if len(cs) < 2: continue
            threshold_cs = [c for c in cs if c.get("role") == "threshold"]
            if len(threshold_cs) < 2: continue
            seen_pairs = set()
            for c1, c2 in combinations(threshold_cs, 2):
                if c1["section"] == c2["section"]: continue
                # 排除同用例不同步骤(如1.8.2.1 vs 1.8.5.1.1是不同用例)
                # 用例章节号格式: X.Y.Z.W — 不同用例的相同参数不应配对
                s1_parts = c1["section"].split(".")
                s2_parts = c2["section"].split(".")
                # 如果都是4+级章节(用例级), 且前3级不同, 说明是不同用例
                if len(s1_parts) >= 4 and len(s2_parts) >= 4:
                    if s1_parts[:3] != s2_parts[:3]:
                        continue  # 不同用例, 不配对
                key = (c1["section"], c2["section"])
                if key in seen_pairs: continue
                seen_pairs.add(key)
                seq += 1
                pairs.append(PotentialPair(
                    pair_id=f"P-{seq:04d}", pair_type="same_param",
                    source={"section":c1["section"],"content":c1["original"][:60],
                            "value":c1["value"],"unit":c1["unit"],"role":c1.get("role","")},
                    target={"section":c2["section"],"content":c2["original"][:60],
                            "value":c2["value"],"unit":c2["unit"],"role":c2.get("role","")},
                    match_signal=f"param:{param}").__dict__)
        
        # ── 2. 需求ID跨位置对(正文→表格) ──
        for sec_id, sec_data in sections.items():
            if not (sec_id.startswith('3.2.') and sec_id.count('.')==2): continue
            req_id = sec_data.get('req_id','')
            if not req_id: continue
            for tsec_id, tsec_data in sections.items():
                for table in tsec_data.get('tables',[]):
                    if table.get('type') not in ('qualification','traceability'): continue
                    for row in table.get('rows',[]):
                        row_text = ' '.join(str(c) for c in row)
                        if req_id in row_text:
                            seq += 1
                            pairs.append(PotentialPair(
                                pair_id=f"P-{seq:04d}", pair_type="req_id_ref",
                                source={"section":sec_id,"content":sec_data["title"],
                                        "req_id":req_id,"type":"definition"},
                                target={"section":tsec_id,"content":row_text[:60],
                                        "req_id":req_id,"type":"table_ref",
                                        "table_type":table["type"]},
                                match_signal=f"req_id:{req_id}").__dict__)
        
        # ── 3. 同版本跨章节对(归一化后只配对不同版本) ──
        version_groups = defaultdict(list)
        for v in versions:
            version_groups[v["software"]].append(v)
        
        for software, vs in version_groups.items():
            if len(vs) < 2: continue
            seen_ver_pairs = set()
            for v1, v2 in combinations(vs, 2):
                if v1["section"] == v2["section"]: continue  # 不同章节
                # 细化: 版本归一化后比较, 只在归一化后不同时才配对
                nv1 = _normalize_version(v1["version"])
                nv2 = _normalize_version(v2["version"])
                if nv1 == nv2: continue  # 归一化后相同, 不配对
                key = (v1["section"], v2["section"])
                if key in seen_ver_pairs: continue
                seen_ver_pairs.add(key)
                seq += 1
                pairs.append(PotentialPair(
                    pair_id=f"P-{seq:04d}", pair_type="same_version",
                    source={"section":v1["section"],"content":v1["original"][:60],
                            "version":v1["version"],"normalized":nv1},
                    target={"section":v2["section"],"content":v2["original"][:60],
                            "version":v2["version"],"normalized":nv2},
                    match_signal=f"software:{software}").__dict__)
        
        # ── 4. 正文-表格对(只配对有共同需求ID/章节号的) ──
        for sec_id, sec_data in sections.items():
            text = sec_data.get("text","")
            if len(text) < 20: continue
            sec_req_id = sec_data.get("req_id","")
            for table in sec_data.get("tables",[]):
                if table.get("type") not in ("qualification","traceability","interface"): continue
                for row in table.get("rows",[]):
                    row_text = ' '.join(str(c) for c in row)
                    if len(row_text) < 10: continue
                    # 细化: 只配对有共同需求ID或章节号引用的
                    has_req_id = sec_req_id and sec_req_id in row_text
                    has_section_ref = sec_id in row_text
                    if not (has_req_id or has_section_ref): continue
                    seq += 1
                    pairs.append(PotentialPair(
                        pair_id=f"P-{seq:04d}", pair_type="text_table",
                        source={"section":sec_id,"content":text[:80],"type":"text"},
                        target={"section":sec_id,"content":row_text[:80],"type":"table_row",
                                "table_type":table["type"]},
                        match_signal=f"req_id:{sec_req_id}" if has_req_id else f"section:{sec_id}").__dict__)
        
        # ── 5. 图文对(图片与所在章节文字) ──
        for sec_id, sec_data in sections.items():
            text = sec_data.get("text","")
            if len(text) < 20: continue
            for img in sec_data.get("images",[]):
                seq += 1
                pairs.append(PotentialPair(
                    pair_id=f"P-{seq:04d}", pair_type="image_text",
                    source={"section":sec_id,"content":img.get("caption",""),
                            "image_path":img["path"],"type":"image"},
                    target={"section":sec_id,"content":text[:80],"type":"text"},
                    match_signal=f"section:{sec_id}").__dict__)
        
        # ── 6. 跨章节语义对(3.12设计约束 vs 3.2.X能力需求, embedding精筛) ──
        design_constraints = [(sid,sd) for sid,sd in sections.items()
                              if sid.startswith('3.12')]
        capability_reqs = [(sid,sd) for sid,sd in sections.items()
                           if sid.startswith('3.2.') and sid.count('.')==2]
        # 细化: 用embedding相似度>0.7才配对
        d_texts = [sd.get("text","")[:200] for _,sd in design_constraints if len(sd.get("text",""))>10]
        c_texts = [sd.get("text","")[:200] for _,sd in capability_reqs if len(sd.get("text",""))>10]
        if d_texts and c_texts:
            d_embs = self._get_embeddings(d_texts)
            c_embs = self._get_embeddings(c_texts)
            for di, (d_sid, d_data) in enumerate(design_constraints):
                d_text = d_data.get("text","")[:200]
                if len(d_text) < 10 or di >= len(d_embs): continue
                for ci, (c_sid, c_data) in enumerate(capability_reqs):
                    c_text = c_data.get("text","")[:200]
                    if len(c_text) < 10 or ci >= len(c_embs): continue
                    # embedding相似度>0.7才配对
                    sim = self._cosine(d_embs[di], c_embs[ci]) if d_embs[di] and c_embs[ci] else 0.0
                    if sim > 0.7:
                        seq += 1
                        pairs.append(PotentialPair(
                            pair_id=f"P-{seq:04d}", pair_type="cross_section",
                            source={"section":d_sid,"content":d_text[:60],"type":"design_constraint"},
                            target={"section":c_sid,"content":c_text[:60],"type":"capability"},
                            match_signal=f"3.12_vs_3.2.X(sim:{sim:.2f})").__dict__)
                    elif not any(d_embs):  # embedding不可用时fallback到关键词匹配
                        # 有共同关键词才配对
                        common_kws = set(d_text) & set(c_text)
                        if len(common_kws) > 5:
                            seq += 1
                            pairs.append(PotentialPair(
                                pair_id=f"P-{seq:04d}", pair_type="cross_section",
                                source={"section":d_sid,"content":d_text[:60],"type":"design_constraint"},
                                target={"section":c_sid,"content":c_text[:60],"type":"capability"},
                                match_signal="3.12_vs_3.2.X(keyword)").__dict__)
        
        # ── 7. 逻辑约束对(同参数threshold约束 + 串行约束) ──
        for param, cs in param_groups.items():
            threshold_cs = [c for c in cs if c.get("role") == "threshold"]
            if len(threshold_cs) >= 2:
                for c1, c2 in combinations(threshold_cs, 2):
                    seq += 1
                    pairs.append(PotentialPair(
                        pair_id=f"P-{seq:04d}", pair_type="logic_constraint",
                        source={"section":c1["section"],"content":c1["original"][:60],
                                "value":c1["value"],"operator":c1["operator"],"unit":c1["unit"]},
                        target={"section":c2["section"],"content":c2["original"][:60],
                                "value":c2["value"],"operator":c2["operator"],"unit":c2["unit"]},
                        match_signal=f"logic:{param}").__dict__)
        
        # 新增: 串行约束对(执行时间之和 vs 总预算)
        exec_cs = [c for c in constraints if any(kw in c["param"] for kw in ["执行时间","分析时间","计算时间"])]
        budget_cs = [c for c in constraints if any(kw in c["param"] for kw in ["总","预算"]) 
                     and not any(kw in c["param"] for kw in ["执行时间","分析时间","计算时间"])]
        for ec in exec_cs:
            for bc in budget_cs:
                if ec["section"] != bc["section"]:
                    seq += 1
                    pairs.append(PotentialPair(
                        pair_id=f"P-{seq:04d}", pair_type="logic_constraint",
                        source={"section":ec["section"],"content":ec["original"][:60],
                                "value":ec["value"],"operator":ec["operator"],"unit":ec["unit"],
                                "constraint_type":"exec_time"},
                        target={"section":bc["section"],"content":bc["original"][:60],
                                "value":bc["value"],"operator":bc["operator"],"unit":bc["unit"],
                                "constraint_type":"budget"},
                        match_signal="serial:exec_vs_budget").__dict__)
        
        # ── 8. 表格-表格对(合格性表↔追溯表同一需求) ──
        qual_tables = [(sid,t) for sid,sd in sections.items() 
                       for t in sd.get("tables",[]) if t.get("type")=="qualification"]
        trace_tables = [(sid,t) for sid,sd in sections.items() 
                        for t in sd.get("tables",[]) if t.get("type")=="traceability"]
        for q_sid, q_table in qual_tables:
            for q_row in q_table.get("rows",[]):
                q_text = ' '.join(str(c) for c in q_row)
                for m in REQ_ID_RE.finditer(q_text):
                    req_id = m.group(0)
                    for t_sid, t_table in trace_tables:
                        for t_row in t_table.get("rows",[]):
                            t_text = ' '.join(str(c) for c in t_row)
                            if req_id in t_text:
                                seq += 1
                                pairs.append(PotentialPair(
                                    pair_id=f"P-{seq:04d}", pair_type="table_table",
                                    source={"section":q_sid,"content":q_text[:60],"req_id":req_id,
                                            "type":"qualification_row"},
                                    target={"section":t_sid,"content":t_text[:60],"req_id":req_id,
                                            "type":"traceability_row"},
                                    match_signal=f"req_id:{req_id}").__dict__)
                                break
        
        # ── 9. 章节层级对(3.2概述↔3.2.X子节) ──
        sec_3_2 = sections.get("3.2",{})
        overview_text = sec_3_2.get("text","")
        if len(overview_text) > 20:
            for sec_id, sec_data in sections.items():
                if not (sec_id.startswith("3.2.") and sec_id.count(".") == 2): continue
                title = sec_data.get("title","")
                if title and title in overview_text:
                    seq += 1
                    pairs.append(PotentialPair(
                        pair_id=f"P-{seq:04d}", pair_type="section_hierarchy",
                        source={"section":"3.2","content":overview_text[:80],"type":"overview"},
                        target={"section":sec_id,"content":title,"type":"subsection"},
                        match_signal=f"overview→{sec_id}").__dict__)
        
        # ── Embedding补充: 同义参数名合并 ──
        # (对参数名做embedding, 相似度>0.85的参数也生成关联对)
        unique_params = list(param_groups.keys())
        if len(unique_params) >= 2:
            embs = self._get_embeddings(unique_params)
            if any(embs):
                for i in range(len(unique_params)):
                    for j in range(i+1, len(unique_params)):
                        sim = self._cosine(embs[i], embs[j])
                        if sim > 0.85 and unique_params[i] != unique_params[j]:
                            # 不同名称但语义相似的参数也配对
                            for c1 in param_groups[unique_params[i]]:
                                for c2 in param_groups[unique_params[j]]:
                                    if c1["section"] != c2["section"]:
                                        seq += 1
                                        pairs.append(PotentialPair(
                                            pair_id=f"P-{seq:04d}", pair_type="same_param",
                                            source={"section":c1["section"],"content":c1["original"][:60],
                                                    "value":c1["value"],"unit":c1["unit"],"role":c1.get("role","")},
                                            target={"section":c2["section"],"content":c2["original"][:60],
                                                    "value":c2["value"],"unit":c2["unit"],"role":c2.get("role","")},
                                            match_signal=f"embed:{unique_params[i]}~{unique_params[j]}({sim:.2f})").__dict__)
        
        return {"pairs": pairs}
    
    def _get_embeddings(self, texts):
        uncached = [(i,t) for i,t in enumerate(texts) if t not in self._emb_cache]
        if uncached:
            try:
                resp = requests.post(EMB_URL, headers={
                    "Authorization":f"Bearer {EMB_KEY}","Content-Type":"application/json"
                }, json={"model":EMB_MODEL,"input":[t for _,t in uncached],
                        "encoding_format":"float"}, timeout=30)
                resp.raise_for_status()
                for (i,t),d in zip(uncached, resp.json()["data"]):
                    self._emb_cache[t] = d["embedding"]
            except:
                return [[] for _ in texts]
        return [self._emb_cache.get(t,[]) for t in texts]
    
    def _cosine(self, a, b):
        if not a or not b: return 0.0
        return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b))+1e-10)


# ═══════════════════════════════════════════════════════════════
# 方向B: 不一致性校验 — 三层判定
# ═══════════════════════════════════════════════════════════════

class SyntaxChecker(OperatorABC):
    """语法层: GJB标准7项检测(有标准条文支撑)"""
    
    def run(self, sections, **kwargs):
        v = []
        v.extend(self._r001(sections))
        v.extend(self._r002(sections))
        v.extend(self._r003(sections))
        v.extend(self._r004(sections))
        v.extend(self._r005(sections))
        v.extend(self._r006(sections))
        v.extend(self._r007(sections))
        return {"syntax_violations": v}
    
    def _r001(self, s):
        text = s.get('1.1',{}).get('text','')
        if any(kw not in text for kw in ['标识','名称','版本']):
            return [{"layer":"syntax","rule":"R-001","gjb_clause":"附录J 1.1 (L2179)",
                    "severity":"HIGH","description":"1.1标识不完整(缺标识/名称/版本)"}]
        return []
    
    def _r002(self, s):
        rids = [(sd.get('req_id',''),sid) for sid,sd in s.items()
                if sid.startswith('3.2.') and sid.count('.')==2 and sd.get('req_id')]
        counts = Counter(rid for rid,_ in rids)
        return [{"layer":"syntax","rule":"R-002","gjb_clause":"附录J 3 (L2195)","severity":"HIGH",
                "description":f"需求标识符'{rid}'重复{c}次"} for rid,c in counts.items() if c>1]
    
    def _r003(self, s):
        v = []
        for sid,sd in s.items():
            if not sid.startswith('4'): continue
            for table in sd.get('tables',[]):
                if table.get('type')!='qualification': continue
                headers = table.get('headers',[])
                mcol = next((i for i,h in enumerate(headers) if '合格性' in h or '方法' in h), -1)
                if mcol<0: continue
                for row in table.get('rows',[]):
                    if mcol<len(row):
                        method = row[mcol].strip()
                        if method and not self._valid(method):
                            v.append({"layer":"syntax","rule":"R-003","gjb_clause":"附录J 4 (L2403)",
                                     "severity":"MEDIUM","description":f"合格性方法'{method}'非GJB规定的5种之一"})
        return v
    
    def _valid(self, m):
        m = m.strip().lower()
        if not m: return True
        if any(k in m for k in ['演示','测试','分析','审查','特殊']): return True
        letters = re.findall(r'[a-e]', m)
        return bool(letters) and all(l in 'abcde' for l in letters)
    
    def _r004(self, s):
        v = []
        if not any(sid.startswith('5') for sid in s):
            v.append({"layer":"syntax","rule":"R-004","gjb_clause":"附录J 5","severity":"HIGH",
                      "description":"缺少第5章(需求可追踪性)"})
            return v
        if not any(sid.startswith('5.1') or '正向' in s.get(sid,{}).get('title','') for sid in s):
            v.append({"layer":"syntax","rule":"R-004","gjb_clause":"附录J 5 a)","severity":"MEDIUM",
                      "description":"缺少正向追溯(a): CSCI需求→系统需求"})
        if not any(sid.startswith('5.2') or '逆向' in s.get(sid,{}).get('title','') for sid in s):
            v.append({"layer":"syntax","rule":"R-004","gjb_clause":"附录J 5 b)","severity":"MEDIUM",
                      "description":"缺少逆向追溯(b): 系统需求→CSCI需求"})
        defined = {sid for sid in s if sid.startswith('3.2.') and sid.count('.')==2}
        if len(defined) >= 3:
            ref = set()
            for sid,sd in s.items():
                for table in sd.get('tables',[]):
                    if table.get('type') in ('qualification','traceability'):
                        for row in table.get('rows',[]):
                            for cell in row:
                                for m in re.finditer(r'(3\.\d+\.\d+)', str(cell)):
                                    ref.add(m.group(1))
            for p in sorted(ref - defined):
                v.append({"layer":"syntax","rule":"R-004","gjb_clause":"附录J 5 (L2423)",
                          "severity":"HIGH","description":f"幽灵需求: 章节{p}被引用但未定义"})
        return v
    
    def _r005(self, s):
        found = {sid for sid in s if re.match(r'^3\.\d+$', sid)}
        if len(found) < 5: return []
        missing = [x for x in EXPECTED_3X if x not in found]
        if missing:
            sev = "LOW" if len(missing)<=2 else "MEDIUM"
            return [{"layer":"syntax","rule":"R-005","gjb_clause":"附录J 3 (L2195)","severity":sev,
                    "description":f"第3章缺少子章节: {missing}"}]
        return []
    
    def _r006(self, s):
        return [{"layer":"syntax","rule":"R-006","gjb_clause":"附录J 3.3 (L2217)","severity":"MEDIUM",
                "description":f"接口{sid}({sd.get('title','')[:20]})缺少唯一标识符"}
               for sid,sd in s.items()
               if sid.startswith(('3.3.','3.4.')) and sid.count('.')==2
               and not sd.get('req_id') and not REQ_ID_RE.search(sd.get('title',''))]
    
    def _r007(self, s):
        sec = s.get('3.18',{})
        if not sec:
            return [{"layer":"syntax","rule":"R-007","gjb_clause":"附录J 3.18 (L2399)","severity":"MEDIUM",
                    "description":"缺少3.18节(需求的优先顺序和关键性)"}]
        if len(sec.get('text',''))<10:
            return [{"layer":"syntax","rule":"R-007","gjb_clause":"附录J 3.18 (L2399)","severity":"LOW",
                    "description":"3.18节内容为空或过短"}]
        return []


class SemanticChecker(OperatorABC):
    """
    语义层: 对潜在关联对做值比较/语义判断
    
    输入: pairs (来自PairFinder)
    检测:
      - same_param对: 同参数threshold角色的值是否一致
      - same_version对: 同软件版本是否一致
      - text_table对: 正文与表格内容是否矛盾(待NLI)
      - cross_section对: 设计约束与能力需求是否矛盾(待NLI)
      - image_text对: 图文是否一致(待VLM)
    
    注意: 语义层的具体检测内容是"下一步需要定义的点"
    当前只实现值比较(same_param/same_version), NLI/VLM待实现
    """
    
    def run(self, pairs, **kwargs):
        violations = []
        
        for pair in pairs:
            ptype = pair["pair_type"]
            
            # same_param: 同参数值比较
            if ptype == "same_param":
                src_role = pair["source"].get("role","")
                tgt_role = pair["target"].get("role","")
                src_val = pair["source"].get("value")
                tgt_val = pair["target"].get("value")
                # 只对threshold角色报值不一致
                if src_role == "threshold" and tgt_role == "threshold":
                    if src_val is not None and tgt_val is not None and src_val != tgt_val:
                        violations.append({
                            "layer":"semantic","check":"param_value_conflict",
                            "severity":"HIGH",
                            "description":f"参数值冲突: {pair['source']['section']}={src_val} vs {pair['target']['section']}={tgt_val} ({pair['match_signal']})",
                            "pair_id":pair["pair_id"],
                        })
            
            # same_version: 版本号归一化后比较
            elif ptype == "same_version":
                src_ver = pair["source"].get("version","")
                tgt_ver = pair["target"].get("version","")
                if src_ver and tgt_ver:
                    nv1 = _normalize_version(src_ver)
                    nv2 = _normalize_version(tgt_ver)
                    if nv1 != nv2:  # 归一化后不同才报
                        violations.append({
                            "layer":"semantic","check":"version_conflict",
                            "severity":"HIGH",
                            "description":f"版本冲突: {pair['source']['section']}={src_ver} vs {pair['target']['section']}={tgt_ver} ({pair['match_signal']})",
                            "pair_id":pair["pair_id"],
                        })
            
            # text_table/cross_section/image_text/table_table/section_hierarchy: 待NLI/VLM实现
            elif ptype in ("text_table","cross_section","image_text","table_table","section_hierarchy"):
                pass  # 待实现: NLI判断/VLM判断
        
        return {"semantic_violations": violations,
                "pending_pairs": sum(1 for p in pairs if p["pair_type"] in ("text_table","cross_section","image_text","table_table","section_hierarchy"))}


class LogicChecker(OperatorABC):
    """
    逻辑层: 对逻辑约束对做Z3可满足性求解
    
    输入: pairs中pair_type="logic_constraint"的对
    检测:
      - 同参数的多个约束是否逻辑可满足(A≤5且A≥10 → UNSAT)
      - 串行约束之和是否超过总预算(待实现)
    
    注意: 逻辑层的具体检测内容是"下一步需要定义的点"
    当前只实现单参数约束可满足性, 串行/累积约束待实现
    """
    
    def run(self, pairs, **kwargs):
        violations = []
        
        # 收集同参数的所有约束
        param_constraints = defaultdict(list)
        for pair in pairs:
            if pair["pair_type"] == "logic_constraint":
                signal = pair["match_signal"]
                param = signal.split(":")[1] if ":" in signal else ""
                if param:
                    param_constraints[param].append(pair["source"])
                    param_constraints[param].append(pair["target"])
        
        # Z3求解: 单参数约束可满足性
        try:
            from z3 import Solver, Real, RealVal, sat, unsat
            for param, constraints in param_constraints.items():
                if len(constraints) < 2: continue
                solver = Solver()
                var = Real(param)
                for c in constraints:
                    val = c.get("value")
                    op = c.get("operator","")
                    if val is None: continue
                    if op in ("≤","<="): solver.add(var <= float(val))
                    elif op in ("≥",">="): solver.add(var >= float(val))
                    elif op == "=": solver.add(var == float(val))
                if solver.check() == unsat:
                    violations.append({
                        "layer":"logic","check":"z3_unsatisfiable",
                        "severity":"HIGH",
                        "description":f"参数'{param}'的约束逻辑不可满足(UNSAT)",
                    })
            
            # 新增: 串行约束之和 vs 总预算
            exec_pairs = [p for p in pairs if p["pair_type"] == "logic_constraint"
                         and p["source"].get("constraint_type") == "exec_time"
                         and p["target"].get("constraint_type") == "budget"]
            for pair in exec_pairs:
                src_val = pair["source"].get("value")
                tgt_val = pair["target"].get("value")
                tgt_op = pair["target"].get("operator","")
                if src_val and tgt_val and tgt_op in ("≤","<="):
                    # 单个执行时间 vs 总预算(简化: 不做求和, 只比较单个)
                    # 完整串行需要识别同流程的多个执行时间约束
                    if float(src_val) > float(tgt_val):
                        violations.append({
                            "layer":"logic","check":"serial_exceeds_budget",
                            "severity":"HIGH",
                            "description":f"执行时间{src_val}{pair['source'].get('unit','')} > 总预算{tgt_val}{pair['target'].get('unit','')} ({pair['match_signal']})",
                            "pair_id":pair["pair_id"],
                        })
        except ImportError:
            pass  # Z3未安装
        
        return {"logic_violations": violations}


# ═══════════════════════════════════════════════════════════════
# Pipeline编排
# ═══════════════════════════════════════════════════════════════

def process_document(doc_dir: Path) -> dict:
    doc_name = doc_dir.name
    cl_path = doc_dir / "office" / f"{doc_name}_content_list.json"
    if not cl_path.exists():
        return {"error": f"content_list不存在: {cl_path}"}
    
    content_list = json.loads(cl_path.read_text(encoding="utf-8"))
    
    # L2: 解析提取
    l2 = L2_Parser()
    l2_result = l2.run(content_list)
    sections = l2_result["sections"]
    constraints = l2_result["constraints"]
    versions = l2_result["versions"]
    req_ids = l2_result["req_ids"]
    
    # 方向A: 上下文关联(只配对)
    pair_finder = PairFinder()
    pair_result = pair_finder.run(sections, constraints, versions, req_ids)
    pairs = pair_result["pairs"]
    
    # 方向B: 不一致性校验(三层)
    # 语法层
    syntax = SyntaxChecker()
    syntax_result = syntax.run(sections)
    
    # 语义层(基于pairs)
    semantic = SemanticChecker()
    semantic_result = semantic.run(pairs)
    
    # 逻辑层(基于pairs)
    logic = LogicChecker()
    logic_result = logic.run(pairs)
    
    # 汇总
    all_violations = syntax_result["syntax_violations"] + \
                     semantic_result["semantic_violations"] + \
                     logic_result["logic_violations"]
    
    by_layer = Counter(v["layer"] for v in all_violations)
    by_pair_type = Counter(p["pair_type"] for p in pairs)
    
    return {
        "doc_name": doc_name,
        "pipeline_date": datetime.now().isoformat(),
        "pipeline": "DataFlow Core (OperatorABC) — 关联与检测分离",
        "statistics": {
            "sections": len(sections),
            "tables": sum(len(s.get("tables",[])) for s in sections.values()),
            "images": sum(len(s.get("images",[])) for s in sections.values()),
            "constraints": len(constraints),
            "versions": len(versions),
            "req_ids": len(req_ids),
            "pairs": len(pairs),
            "pair_types": dict(by_pair_type),
        },
        "violations": {
            "total": len(all_violations),
            "by_layer": dict(by_layer),
            "syntax": len(syntax_result["syntax_violations"]),
            "semantic": len(semantic_result["semantic_violations"]),
            "logic": len(logic_result["logic_violations"]),
            "pending_semantic": semantic_result["pending_pairs"],
        },
        "pair_samples": [{"pair_id":p["pair_id"],"type":p["pair_type"],
                          "signal":p["match_signal"],
                          "src":p["source"]["section"],"tgt":p["target"]["section"]} 
                         for p in pairs[:10]],
        "violation_details": all_violations,
    }


def main():
    parser = argparse.ArgumentParser(description="SRS Pipeline v2 (关联与检测分离)")
    parser.add_argument("--doc", type=str)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SRS一致性校验 Pipeline v2")
    print("方向A(关联): PairFinder — 只找潜在关联对")
    print("方向B(检测): 三层 — 语法(GJB标准)/语义(值比较)/逻辑(Z3)")
    print("基于DataFlow Core: OperatorABC")
    print("=" * 60)
    
    if args.doc:
        doc_dir = MINERU_DIR / args.doc
        result = process_document(doc_dir)
        _print(result)
        out = OUTPUT_DIR / f"{args.doc[:20]}_v2.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        all_results = []
        for doc_dir in sorted(MINERU_DIR.iterdir()):
            if not doc_dir.is_dir(): continue
            result = process_document(doc_dir)
            _print(result)
            out = OUTPUT_DIR / f"{doc_dir.name[:20]}_v2.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            all_results.append(result)
        
        total_p = sum(r["statistics"]["pairs"] for r in all_results)
        total_v = sum(r["violations"]["total"] for r in all_results)
        print(f"\n{'='*60}")
        print(f"汇总: {len(all_results)}份文档, {total_p}个关联对, {total_v}条违规")
        
        all_layers = Counter()
        all_pair_types = Counter()
        for r in all_results:
            all_layers.update(r["violations"]["by_layer"])
            all_pair_types.update(r["statistics"]["pair_types"])
        print(f"按层: {dict(all_layers)}")
        print(f"关联对类型: {dict(all_pair_types)}")
        
        (OUTPUT_DIR / "_summary.json").write_text(
            json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")


def _print(result):
    if "error" in result:
        print(f"  {result['error']}")
        return
    name = result["doc_name"][:35]
    s = result["statistics"]
    v = result["violations"]
    print(f"\n[{name}]")
    print(f"  L2: 章节:{s['sections']} 表格:{s['tables']} 图片:{s['images']} 约束:{s['constraints']}")
    print(f"  方向A(关联): {s['pairs']}个潜在关联对 {dict(s['pair_types'])}")
    print(f"  方向B(检测): {v['total']}条违规 [语法:{v['syntax']} 语义:{v['semantic']} 逻辑:{v['logic']}]")
    if v['pending_semantic'] > 0:
        print(f"    待检测(NLI/VLM): {v['pending_semantic']}个关联对")
    for d in result.get("violation_details",[])[:3]:
        print(f"    [{d['layer']}] {d['description'][:65]}")


if __name__ == "__main__":
    main()
