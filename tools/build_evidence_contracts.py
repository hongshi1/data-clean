#!/usr/bin/env python3
"""导出检测项→证据形态合同v1(冻结合同注册表).

对应文档: 70号F3设计 / 79号. 来源: deq_pipeline的
DETECTION_EVIDENCE_REGISTRY(40项, 无类型dict)→结构化合同JSON.

合同schema(每项):
  table_types      需要的表型(use_case/capability/interface/value_domain)
  content_markers  内容标记词(加权不否决)
  statement_fields 语句级字段名(形态硬信号的文本代理)

用法: python tools/build_evidence_contracts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.deq_pipeline import (  # noqa: E402
    DETECTION_EVIDENCE_REGISTRY,
)

OUT = BASE / "config/evidence_contracts_v1.json"


def main() -> int:
    contracts = {}
    for item_id, spec in sorted(DETECTION_EVIDENCE_REGISTRY.items()):
        contracts[item_id] = {
            "table_types": sorted(spec.get("table_types", set())),
            "content_markers": list(spec.get("content_markers", ())),
            "statement_fields": list(spec.get("statement_fields", ())),
        }
    doc = {
        "schema": "evidence_contracts_v1",
        "n_items": len(contracts),
        "source": "algorithms/consistency/deq_pipeline.py::"
                  "DETECTION_EVIDENCE_REGISTRY",
        "design": "70号F3: 标注优先于删除(73号教训); markers加权不否决",
        "contracts": contracts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    n_types = sum(1 for c in contracts.values() if c["table_types"])
    n_fields = sum(1 for c in contracts.values() if c["statement_fields"])
    print(f"导出{len(contracts)}项合同 → {OUT}")
    print(f"  含表型约束: {n_types}项 | 含语句字段: {n_fields}项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
