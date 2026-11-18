"""Analyze NLI items labels: verdict alignment + diff_type vs gold."""
from __future__ import annotations

import json
import sys
from collections import Counter

PATH = ("data/gjb_438c/distillation/nli_items_labels_v1.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = [json.loads(line) for line in
            open(PATH, encoding="utf-8").read().splitlines()
            if line.strip()]
    print(f"n: {len(rows)}")
    print("verdict:", dict(Counter(r["verdict"] for r in rows)))
    vio = [r for r in rows if r["corpus"] == "violations"]
    print()
    print("=== violations-17 (根因gold=构造category) ===")
    agree = 0
    for r in vio:
        expect = ("CONTRADICTED" if r["orig_label"] == "refute"
                  else r["orig_label"].upper())
        ok = r["verdict"] == expect
        agree += ok
        diffs = [f["difference_type"] for f in r["findings"]]
        mark = "OK" if ok else "MISS"
        print(f"  {r['instance_id'][-2:]} {r['verdict']:14s} "
              f"expect={expect:14s} {mark} diff={diffs}")
    print(f"violations判定一致: {agree}/{len(vio)}")
    n_f = sum(len(r["findings"]) for r in rows)
    n_ev = sum(1 for r in rows for f in r["findings"]
               if f.get("evidence_quote_verified"))
    n_cl = sum(1 for r in rows for f in r["findings"]
               if f.get("claim_quote_verified"))
    print(f"findings总数: {n_f} | claim_quote✓: {n_cl} | "
          f"evidence_quote✓: {n_ev}")
    print("diff_type分布:",
          dict(Counter(f["difference_type"]
                       for r in rows for f in r["findings"])))


if __name__ == "__main__":
    main()
