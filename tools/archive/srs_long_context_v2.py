#!/usr/bin/env python3
"""
SRS长程上下文关联引擎 v2
=========================
基于MinerU Pipeline产出的结构化JSON(含表格约束)做长程关联+检测

改进:
  1. 消费structured JSON(含表格cells约束) ← 解决参数提取问题
  2. 更多检测规则: 幽灵需求+章节偏移+ID分裂+参数冲突+版本冲突+覆盖缺失
  3. 长程上下文: 全局参数索引+版本索引+需求ID索引

用法:
  python3 tools/srs_long_context_v2.py --doc 03服务集成
  python3 tools/srs_long_context_v2.py --all
"""
import json
import re
import math
import argparse
import requests
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from itertools import combinations

BASE = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE / "data/gjb_438c/mineru_parsed"
OUTPUT_DIR = BASE / "data/srs_context_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
EMB_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
EMB_MODEL = "ep-qrkeon-1785654358657880827"

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')


@dataclass
class ContextItem:
    item_id: str
    item_type: str
    canonical_name: str
    occurrences: list = field(default_factory=list)
    features: list = field(default_factory=list)
    has_conflict: bool = False


_emb_cache = {}
def get_embeddings(texts):
    uncached = [(i, t) for i, t in enumerate(texts) if t not in _emb_cache]
    if uncached:
        try:
            resp = requests.post(EMB_URL, headers={
                "Authorization": f"Bearer {EMB_KEY}", "Content-Type": "application/json"
            }, json={"model": EMB_MODEL, "input": [t for _, t in uncached],
                     "encoding_format": "float"}, timeout=30)
            resp.raise_for_status()
            for (i, t), d in zip(uncached, resp.json()["data"]):
                _emb_cache[t] = d["embedding"]
        except:
            return [[] for _ in texts]
    return [_emb_cache.get(t, []) for t in texts]

def cosine(a, b):
    if not a or not b: return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot/(na*nb) if na>0 and nb>0 else 0.0


def process_document(doc_name: str) -> dict:
    """处理单份文档: 索引→关联→检测"""
    json_path = PARSED_DIR / f"{doc_name}_structured.json"
    if not json_path.exists():
        return {"error": f"文件不存在: {json_path}"}
    
    data = json.loads(json_path.read_text(encoding="utf-8"))
    sections = data.get("sections", {})
    all_constraints = data.get("all_constraints", [])
    all_versions = data.get("all_versions", [])
    all_req_ids = set(data.get("all_req_ids", []))
    
    # === 1. 构建索引 ===
    # 参数索引: param_name → [(section, value, unit, role)]
    param_index = defaultdict(list)
    for c in all_constraints:
        param_index[c["param"]].append(c)
    
    # 版本索引: software → [(section, version)]
    version_index = defaultdict(list)
    for v in all_versions:
        version_index[v["software"]].append(v)
    
    # 需求ID → section
    req_id_sections = defaultdict(list)
    for sec_id, sec_data in sections.items():
        if "req_id" in sec_data:
            req_id_sections[sec_data["req_id"]].append(sec_id)
    
    # 表格索引: table_type → [rows]
    table_index = defaultdict(list)
    for sec_id, sec_data in sections.items():
        for table in sec_data.get("tables", []):
            table_index[table["type"]].append({"section": sec_id, **table})
    
    # === 2. 长程关联 ===
    items = []
    
    # 参数级关联
    for param, constraints in param_index.items():
        sections_with_param = set(c["section"] for c in constraints)
        values = set(c["value"] for c in constraints)
        threshold_values = set(c["value"] for c in constraints if c.get("role") == "threshold")
        
        items.append(ContextItem(
            item_id=f"PARAM-{param}",
            item_type="parameter",
            canonical_name=param,
            occurrences=[{"section": c["section"], "value": c["value"], 
                         "unit": c["unit"], "role": c["role"]} for c in constraints],
            has_conflict=len(threshold_values) > 1,
        ))
    
    # 版本级关联
    for software, versions in version_index.items():
        version_set = set(v["version"] for v in versions)
        items.append(ContextItem(
            item_id=f"VERSION-{software}",
            item_type="version",
            canonical_name=software,
            occurrences=[{"section": v["section"], "version": v["version"]} for v in versions],
            has_conflict=len(version_set) > 1,
        ))
    
    # 需求级关联
    for req_id, sec_ids in req_id_sections.items():
        # 搜索req_id在表格中的出现
        table_occurrences = []
        for table_type, tables in table_index.items():
            for table in tables:
                for row in table.get("rows", []):
                    row_text = ' '.join(str(cell) for cell in row)
                    if req_id in row_text:
                        table_occurrences.append({
                            "section": table["section"],
                            "table_type": table_type,
                            "cells": row,
                        })
        
        items.append(ContextItem(
            item_id=req_id,
            item_type="function",
            canonical_name=sections[sec_ids[0]]["title"] if sec_ids else req_id,
            occurrences=[{"section": s, "type": "definition"} for s in sec_ids] + 
                       [{"section": t["section"], "type": "table_ref", "table_type": t["table_type"]} 
                        for t in table_occurrences],
        ))
    
    # === 3. 不一致性检测 ===
    violations = []
    
    # 3.1 参数值冲突
    for param, constraints in param_index.items():
        threshold_cs = [c for c in constraints if c.get("role") == "threshold"]
        if len(threshold_cs) >= 2:
            values = set(c["value"] for c in threshold_cs)
            if len(values) > 1:
                violations.append({
                    "check": "param_value_conflict", "severity": "HIGH",
                    "description": f"参数'{param}'阈值不一致: {[(c['section'], c['value']) for c in threshold_cs]}",
                    "param": param, "locations": [{"section": c["section"], "value": c["value"]} for c in threshold_cs],
                })
    
    # 3.2 版本号冲突
    for software, versions in version_index.items():
        version_set = set(v["version"] for v in versions)
        if len(version_set) > 1:
            violations.append({
                "check": "version_conflict", "severity": "HIGH",
                "description": f"软件'{software}'版本不一致: {[(v['section'], v['version']) for v in versions]}",
                "software": software,
            })
    
    # 3.3 需求ID分裂
    req_id_prefixes = defaultdict(set)
    for req_id in all_req_ids:
        parts = req_id.split('-')
        if len(parts) >= 2:
            req_id_prefixes[f"{parts[0]}-{parts[1]}"].add(req_id)
    for prefix, ids in req_id_prefixes.items():
        if len(ids) > 1:
            violations.append({
                "check": "id_split", "severity": "MEDIUM",
                "description": f"需求ID前缀'{prefix}'有{len(ids)}个不同ID: {sorted(ids)[:3]}",
            })
    
    # 3.4 幽灵需求(被引用但未定义)
    defined_sections = set()
    for sec_id, sec_data in sections.items():
        if sec_id.startswith('3.2.') and sec_id.count('.') == 2:
            defined_sections.add(sec_id)
    
    referenced_sections = set()
    for table in table_index.get("qualification", []) + table_index.get("traceability", []):
        for row in table.get("rows", []):
            for cell in row:
                m = re.search(r'(3\.\d+\.\d+)', str(cell))
                if m:
                    referenced_sections.add(m.group(1))
    
    phantoms = referenced_sections - defined_sections
    for p in phantoms:
        violations.append({
            "check": "phantom_requirement", "severity": "HIGH",
            "description": f"幽灵需求: 章节{p}被引用但未定义",
        })
    
    # 3.5 覆盖缺失(需求在第4/5章未出现)
    for req_id, sec_ids in req_id_sections.items():
        all_occs = [o for item in items if item.item_id == req_id for o in item.occurrences]
        has_table_ref = any(o.get("type") == "table_ref" for o in all_occs)
        if not has_table_ref:
            violations.append({
                "check": "coverage_missing", "severity": "MEDIUM",
                "description": f"需求'{req_id}'在第4/5章表格中未出现",
            })
    
    # 3.6 章节编号重复
    sec_counts = Counter(sections.keys())
    for sec_id, count in sec_counts.items():
        if count > 1 and sec_id:
            violations.append({
                "check": "duplicate_section", "severity": "HIGH",
                "description": f"章节编号'{sec_id}'重复{count}次",
            })
    
    # 3.7 章节号系统性偏移(合格性表 vs 第3章)
    ch3_secs = sorted([s for s in defined_sections if s.startswith('3.2.')])
    ch4_refs = sorted(referenced_sections)
    if ch3_secs and ch4_refs:
        best_offset, best_rate = 0, 0
        for offset in range(-2, 3):
            def adjust(s, o):
                parts = s.split('.')
                if len(parts) >= 3:
                    try: parts[-1] = str(int(parts[-1]) + o); return '.'.join(parts)
                    except: return s
                return s
            matched = sum(1 for r in ch4_refs if adjust(r, offset) in ch3_secs)
            rate = matched / len(ch4_refs)
            if rate > best_rate: best_offset, best_rate = offset, rate
        if best_offset != 0 and best_rate > 0.8:
            violations.append({
                "check": "systematic_offset", "severity": "HIGH",
                "description": f"合格性表章节号系统性偏移{best_offset:+d}(匹配率{best_rate:.0%})",
            })
    
    # === 汇总 ===
    by_check = Counter(v["check"] for v in violations)
    by_severity = Counter(v["severity"] for v in violations)
    
    return {
        "doc_name": doc_name,
        "detect_date": datetime.now().isoformat(),
        "statistics": {
            "sections": len(sections),
            "constraints": len(all_constraints),
            "versions": len(all_versions),
            "req_ids": len(all_req_ids),
            "tables": sum(len(v) for v in table_index.values()),
            "context_items": len(items),
        },
        "violations": {
            "total": len(violations),
            "by_check": dict(by_check),
            "by_severity": dict(by_severity),
        },
        "context_items": [
            {"item_id": i.item_id, "type": i.item_type, "name": i.canonical_name,
             "occurrences": len(i.occurrences), "has_conflict": i.has_conflict}
            for i in items
        ],
        "violation_details": violations,
    }


def main():
    parser = argparse.ArgumentParser(description="SRS长程上下文关联v2")
    parser.add_argument("--doc", type=str)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SRS长程上下文关联 v2 (基于结构化JSON)")
    print("=" * 60)
    
    if args.doc:
        result = process_document(args.doc)
        print(f"\n[{args.doc[:35]}]")
        _print_result(result)
        out = OUTPUT_DIR / f"{args.doc[:20]}_v2.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        json_files = sorted(PARSED_DIR.glob("*_structured.json"))
        all_results = []
        for f in json_files:
            doc_name = f.name.replace("_structured.json", "")
            result = process_document(doc_name)
            print(f"\n[{doc_name[:35]}]")
            _print_result(result)
            all_results.append(result)
        
        total_v = sum(r["violations"]["total"] for r in all_results)
        print(f"\n{'='*60}")
        print(f"汇总: {len(all_results)}份文档, {total_v}条违规")
        
        all_checks = Counter()
        for r in all_results:
            all_checks.update(r["violations"]["by_check"])
        print(f"按检测类型: {dict(all_checks)}")
        
        (OUTPUT_DIR / "_summary.json").write_text(
            json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")


def _print_result(result):
    if "error" in result:
        print(f"  {result['error']}")
        return
    s = result["statistics"]
    v = result["violations"]
    print(f"  章节:{s['sections']} 约束:{s['constraints']} 版本:{s['versions']} "
          f"需求ID:{s['req_ids']} 表格:{s['tables']} 条目:{s['context_items']}")
    print(f"  违规:{v['total']}条 {dict(v['by_check'])}")
    for detail in result["violation_details"][:3]:
        print(f"    [{detail['check']}] {detail['description'][:70]}")


if __name__ == "__main__":
    main()
