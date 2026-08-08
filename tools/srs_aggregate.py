#!/usr/bin/env python3
"""
SRS上下文关联引擎 (方向A)
=========================
实体为中心的条目聚合: 从结构化JSON中提取需求实体→跨章节链接→多模态条目

输入: srs_mineru_pipeline.py产出的structured JSON
输出: List[ContextItem] — 每个条目聚合了"同一事物"的所有出现位置

技术路线:
  1. 实体识别: 从3.2.X/3.3.X/3.4.X章节提取功能/接口实体
  2. 跨章节链接: 用req_id在合格性表/追溯表中搜索引用
  3. 参数聚合: 同参数名的所有约束聚合成一个条目(含semantic_role)
  4. 版本聚合: 同软件名的所有版本号聚合成一个条目
  5. Embedding合并: 名称相似度>0.85的参数合并

用法: python3 tools/srs_aggregate.py --doc 03服务集成
      python3 tools/srs_aggregate.py --all
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

BASE = Path(__file__).resolve().parent.parent
PARSED_DIR = BASE / "data/gjb_438c/mineru_structured"
OUTPUT_DIR = BASE / "data/srs_aggregated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMB_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/embeddings"
EMB_KEY = "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
EMB_MODEL = "ep-qrkeon-1785654358657880827"

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')

THRESHOLD_KW = ['时间', '间隔', '延迟', '误差', '精度', '响应', '定时', '偏差', '周期']
CONFIG_KW = ['版本', '型号', '主频', '内存', '硬盘', '存储', '分辨率', '显存']
CAPACITY_KW = ['最多', '支持', '容量', '数量', '上限', '最大', '并发']


@dataclass
class Occurrence:
    section: str
    occ_type: str
    content: str
    value: float = None
    unit: str = ""
    role: str = ""

@dataclass
class ContextItem:
    item_id: str
    item_type: str
    canonical_name: str
    occurrences: list = field(default_factory=list)
    has_conflict: bool = False
    match_signals: dict = field(default_factory=dict)


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
    return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) + 1e-10)

def classify_role(param, section):
    for kw in THRESHOLD_KW:
        if kw in param: return "threshold"
    for kw in CONFIG_KW:
        if kw in param: return "config"
    for kw in CAPACITY_KW:
        if kw in param: return "capacity"
    if section.startswith('3.10'): return "config"
    if section.startswith('3.11'): return "threshold"
    return "description"


def aggregate_document(doc_name: str) -> dict:
    """对单份文档做上下文关联"""
    json_path = PARSED_DIR / f"{doc_name}_structured.json"
    if not json_path.exists():
        return {"error": f"文件不存在: {json_path}"}

    data = json.loads(json_path.read_text(encoding="utf-8"))
    sections = data.get("sections", {})
    all_constraints = data.get("all_constraints", [])
    all_versions = data.get("all_versions", [])
    all_req_ids = set(data.get("all_req_ids", []))

    items = []

    # 1. 功能实体: 从3.2.X章节提取
    for sec_id, sec_data in sections.items():
        if not (sec_id.startswith('3.2.') and sec_id.count('.') == 2):
            continue
        req_id = sec_data.get('req_id', '')
        title = sec_data.get('title', '')

        occurrences = [Occurrence(section=sec_id, occ_type="definition", content=title)]

        # 在合格性表/追溯表中搜索引用
        for table_sec_id, table_sec_data in sections.items():
            for table in table_sec_data.get('tables', []):
                if table.get('type') not in ('qualification', 'traceability'):
                    continue
                for row in table.get('rows', []):
                    row_text = ' '.join(str(c) for c in row)
                    if req_id and req_id in row_text:
                        occurrences.append(Occurrence(
                            section=table_sec_id, occ_type="table_ref",
                            content=row_text[:100], 
                        ))

        items.append(ContextItem(
            item_id=req_id or title,
            item_type="function",
            canonical_name=title,
            occurrences=occurrences,
        ))

    # 2. 接口实体: 从3.3.X/3.4.X章节提取
    for sec_id, sec_data in sections.items():
        if not (sec_id.startswith(('3.3.', '3.4.')) and sec_id.count('.') == 2):
            continue
        req_id = sec_data.get('req_id', '')
        title = sec_data.get('title', '')
        if req_id or title:
            items.append(ContextItem(
                item_id=req_id or f"IF-{sec_id}",
                item_type="interface",
                canonical_name=title,
                occurrences=[Occurrence(section=sec_id, occ_type="definition", content=title)],
            ))

    # 3. 参数聚合: 同参数名的所有约束
    param_groups = defaultdict(list)
    for c in all_constraints:
        param_groups[c["param"]].append(c)

    for param, constraints in param_groups.items():
        occurrences = [Occurrence(
            section=c["section"], occ_type="constraint",
            content=c.get("original", "")[:80],
            value=c["value"], unit=c["unit"],
            role=c.get("role", classify_role(param, c["section"])),
        ) for c in constraints]

        threshold_values = set(c["value"] for c in constraints if c.get("role") == "threshold")

        items.append(ContextItem(
            item_id=f"PARAM-{param}",
            item_type="parameter",
            canonical_name=param,
            occurrences=occurrences,
            has_conflict=len(threshold_values) > 1,
        ))

    # 4. 版本聚合: 同软件名的所有版本
    version_groups = defaultdict(list)
    for v in all_versions:
        version_groups[v["software"]].append(v)

    for software, versions in version_groups.items():
        version_set = set(v["version"] for v in versions)
        items.append(ContextItem(
            item_id=f"VERSION-{software}",
            item_type="version",
            canonical_name=software,
            occurrences=[Occurrence(
                section=v["section"], occ_type="version",
                content=v.get("original", "")[:80],
            ) for v in versions],
            has_conflict=len(version_set) > 1,
        ))

    # 5. Embedding合并: 参数名称相似度>0.85的合并
    param_items = [i for i in items if i.item_type == "parameter" and len(i.occurrences) <= 2]
    if len(param_items) >= 2:
        names = [i.canonical_name for i in param_items]
        embs = get_embeddings(names)
        if any(embs):
            merged = set()
            for i in range(len(param_items)):
                if i in merged: continue
                for j in range(i+1, len(param_items)):
                    if j in merged: continue
                    sim = cosine(embs[i], embs[j])
                    if sim > 0.85:
                        param_items[i].occurrences.extend(param_items[j].occurrences)
                        param_items[i].match_signals[f"embed_merge"] = round(sim, 3)
                        merged.add(j)
            items = [i for i in items if i.item_type != "parameter"] + \
                    [i for idx, i in enumerate(param_items) if idx not in merged]

    # 统计
    by_type = Counter(i.item_type for i in items)
    total_occs = sum(len(i.occurrences) for i in items)
    conflicts = sum(1 for i in items if i.has_conflict)

    return {
        "doc_name": doc_name,
        "aggregate_date": datetime.now().isoformat(),
        "statistics": {
            "total_items": len(items),
            "total_occurrences": total_occs,
            "conflicts": conflicts,
            "by_type": dict(by_type),
        },
        "items": [
            {
                "item_id": i.item_id, "type": i.item_type,
                "name": i.canonical_name, "occurrences": len(i.occurrences),
                "has_conflict": i.has_conflict, "signals": i.match_signals,
                "detail": [{"section": o.section, "type": o.occ_type, "value": o.value,
                           "unit": o.unit, "role": o.role, "content": o.content[:60]}
                          for o in i.occurrences],
            } for i in items
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="SRS上下文关联(方向A)")
    parser.add_argument("--doc", type=str)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print("SRS上下文关联引擎 (方向A: 实体为中心的条目聚合)")
    print("=" * 60)

    if args.doc:
        result = aggregate_document(args.doc)
        _print(result)
        out = OUTPUT_DIR / f"{args.doc[:20]}_items.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        all_results = []
        for f in sorted(PARSED_DIR.glob("*_structured.json")):
            doc_name = f.name.replace("_structured.json", "")
            result = aggregate_document(doc_name)
            _print(result)
            # 保存独立报告
            out = OUTPUT_DIR / f"{doc_name[:20]}_items.json"
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            all_results.append(result)

        total_items = sum(r["statistics"]["total_items"] for r in all_results)
        total_conflicts = sum(r["statistics"]["conflicts"] for r in all_results)
        print(f"\n{'='*60}")
        print(f"汇总: {len(all_results)}份文档, {total_items}个条目, {total_conflicts}个冲突")

        (OUTPUT_DIR / "_summary.json").write_text(
            json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")


def _print(result):
    if "error" in result:
        print(f"  {result['error']}")
        return
    name = result["doc_name"][:35]
    s = result["statistics"]
    print(f"\n[{name}]")
    print(f"  条目:{s['total_items']} 出现:{s['total_occurrences']} 冲突:{s['conflicts']} {dict(s['by_type'])}")
    for item in result["items"][:3]:
        conflict = "⚠冲突" if item["has_conflict"] else ""
        print(f"    [{item['type']}] {item['name'][:20]:20s} 出现{item['occurrences']}次 {conflict}")


if __name__ == "__main__":
    main()
