#!/usr/bin/env python3
"""覆盖差异检测全量运行: tables.jsonl → 平行表findings.

对应文档: 69号发现4(类型学补全) / 78号. 产出:
  data/gjb_438c/coverage_findings_v1/findings.jsonl + summary.json
用法: python tools/build_coverage_findings.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.coverage_detector import (  # noqa: E402
    detect_all,
    find_parallel_tables,
)

IN = BASE / "data/gjb_438c/structured_corpus_v1/tables.jsonl"
OUT = BASE / "data/gjb_438c/coverage_findings_v1"


def main() -> int:
    tables = [json.loads(line) for line in IN.open(encoding="utf-8")]
    print(f"tables: {len(tables)}")
    pairs = find_parallel_tables(tables)
    n_docs = len({a.get("doc_id") for a, _b, _s in pairs})
    print(f"平行表对: {len(pairs)} (覆盖{n_docs}文档)")

    findings = detect_all(tables)
    by_type = Counter(f["type"] for f in findings)
    by_doc = Counter(f["doc_id"] for f in findings)

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "findings.jsonl").open("w", encoding="utf-8") as f:
        for x in findings:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    (OUT / "summary.json").write_text(json.dumps({
        "n_tables": len(tables), "n_parallel_pairs": len(pairs),
        "n_findings": len(findings),
        "by_type": dict(by_type), "by_doc": dict(sorted(by_doc.items())),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"findings: {len(findings)} | 类型: {dict(by_type)}")
    print(f"按文档: {dict(sorted(by_doc.items()))}")

    print("\n=== value_conflict样例(前6) ===")
    for f in [x for x in findings if x["type"] == "value_conflict"][:6]:
        print(f"  [doc{f['doc_id']} {f['scope']}·{f['field']}] "
              f"{f['value_a'][:30]} vs {f['value_b'][:30]} "
              f"@{f['section_a']}/{f['section_b']}")
    print("\n=== value_subset_gap样例(前6) ===")
    for f in [x for x in findings if x["type"] == "value_subset_gap"][:6]:
        print(f"  [doc{f['doc_id']} {f['scope']}·{f['field']}] "
              f"{f['value_a'][:30]} vs {f['value_b'][:30]}")
    print(f"\n结果已写入: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
