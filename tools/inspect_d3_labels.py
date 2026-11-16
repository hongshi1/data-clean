"""Inspect D3 teacher labels: span quality + issue quality."""
from __future__ import annotations

import json
import sys
from pathlib import Path

PATH = (Path(__file__).resolve().parents[1]
        / "data/gjb_438c/distillation/d3_teacher_labels_v1.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [json.loads(line) for line in
            PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"n rows: {len(rows)}")
    refutes = [r for r in rows if r["verdict"] == "refute"]
    print(f"refute rows: {len(refutes)}")
    for r in refutes[:3]:
        print(f"== {r['instance_id']} ({r['corpus']})")
        for i in r["issues"]:
            print(f"  quote: {i['quote'][:50]}")
            print(f"  span={i['span']} verified={i['span_verified']}")
            if i["span"]:
                start, end = i["span"]
                fetched = r["answer"][start:end]
                print(f"  answer切片: {fetched[:40]!r}")
                print(f"  一致: {fetched == i['quote']}")
            print(f"  rule={i['rule_id']} ev={i['evidence_ref']}")
            print(f"  explanation: {i['explanation'][:80]}")


if __name__ == "__main__":
    main()
