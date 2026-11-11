"""Audit claim extraction on the known support-failure instances.

Prints the decomposed claims for S1QA-066/069/077 (support-class
weakness) plus a typical narrative instance, so the extraction quality
can be judged against a manual reading of the answer text.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import decompose_claims  # noqa: E402
from algorithms.consistency.eval_lib import load_frozen_qa  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    qa = load_frozen_qa()
    by_id = {r["instance_id"]: r for r in qa}
    for iid in ("S1QA-066", "S1QA-069", "S1QA-077"):
        rec = by_id[iid]
        print(f"===== {iid} =====")
        print(f"Q: {rec['question'][:60]}")
        print(f"A: {str(rec['answer'])[:180]}...")
        claims = decompose_claims(rec["question"], rec["answer"])
        print(f"claims ({len(claims)}):")
        for c in claims:
            print(f"  [{c.kind:10s}] {c.text[:60]}")
        print()

    # 全corpus统计: claim类型分布
    kind_counts: dict[str, int] = {}
    per_answer: list[int] = []
    for rec in qa:
        claims = decompose_claims(rec["question"], rec["answer"])
        per_answer.append(len(claims))
        for c in claims:
            kind_counts[c.kind] = kind_counts.get(c.kind, 0) + 1
    n = len(per_answer)
    print("===== 91QA claim提取统计 =====")
    print(f"claims/answer: mean={sum(per_answer)/n:.1f} "
          f"min={min(per_answer)} max={max(per_answer)}")
    print(f"kind分布: {kind_counts}")
    empty = sum(1 for x in per_answer if x == 0)
    print(f"零claim答案数: {empty}/{n}")


if __name__ == "__main__":
    main()
