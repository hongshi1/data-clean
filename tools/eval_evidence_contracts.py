#!/usr/bin/env python3
"""F3形态合同命中率测量: 108评测实例的证据形态标注.

对应文档: 79号(70号F3 v1——标注优先于删除).

问题: 检测项路由的活跃合同, 其statement_fields/content_markers
在证据池中的命中率如何(合同质量的直接测量)?
用法: python tools/eval_evidence_contracts.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_purifier import (  # noqa: E402
    annotate_contracts,
)

CONTRACTS = BASE / "config/evidence_contracts_v1.json"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
QA = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
OUT = BASE / "data/gjb_438c/localization_gold/contract_match_v1.json"


def main() -> int:
    doc = json.loads(CONTRACTS.read_text(encoding="utf-8"))
    contracts = doc["contracts"]
    records = []
    for line in VIO.open(encoding="utf-8"):
        records.append(json.loads(line))
    for line in QA.open(encoding="utf-8"):
        records.append(json.loads(line))
    print(f"评测集: {len(records)}实例, 合同{len(contracts)}项")

    n_blocks = n_matched = n_active = 0
    item_match: Counter = Counter()
    item_active: Counter = Counter()
    gold_hit = gold_total = 0
    per_inst: list[dict] = []
    for r in records:
        ann = annotate_contracts(r["question"], r["evidence"], contracts)
        gold_ids = set(r.get("gold_evidence_refs", []))
        gold_total += len(gold_ids)
        matched_ids = set()
        for a in ann:
            n_blocks += 1
            n_active += len(a["active_items"]) > 0
            if a["matched_items"]:
                n_matched += 1
            for it in a["active_items"]:
                item_active[it] += 1
            for it in a["matched_items"]:
                item_match[it] += 1
                matched_ids.add(a["evidence_id"])
        gold_hit += len(gold_ids & matched_ids)
        per_inst.append({
            "instance_id": r["instance_id"],
            "n_evidence": len(ann),
            "n_active": len(ann[0]["active_items"]) if ann else 0,
            "n_matched_blocks": sum(
                1 for a in ann if a["matched_items"]),
            "gold_matched": len(gold_ids & matched_ids),
            "gold_total": len(gold_ids),
        })

    print(f"\n块级: {n_blocks}块中{n_matched}块形态命中"
          f"({100 * n_matched / max(n_blocks, 1):.1f}%)")
    print(f"活跃路由: {n_active}/{n_blocks}块被路由到活跃合同")
    print(f"gold证据被形态匹配覆盖: {gold_hit}/{gold_total}"
          f"({100 * gold_hit / max(gold_total, 1):.1f}%)")
    print("\n按检测项命中率(前10):")
    for it, n in item_match.most_common(10):
        print(f"  {it}: {n}/{item_active[it]}"
              f" ({100 * n / max(item_active[it], 1):.0f}%)")
    OUT.write_text(json.dumps({
        "n_instances": len(records), "n_blocks": n_blocks,
        "block_match_rate": round(n_matched / max(n_blocks, 1), 4),
        "gold_coverage": f"{gold_hit}/{gold_total}",
        "per_instance": per_inst,
        "item_match": dict(item_match), "item_active": dict(item_active),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
