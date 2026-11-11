"""E3b baseline: frozen evidence alone on the 14 S/R instances.

The union result (8/14) matching pure recall (8/14) suggested evidence
pollution — but the correct baseline is frozen-evidence-only on the
SAME 14 instances (D1's S/R weakness, e.g. support F1 < refute F1,
could itself explain part of the 6 misses).
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    silver = load_silver_labels(SILVER)
    qa = load_frozen_qa()
    sr_recs = [r for r in qa
               if silver.get(r["instance_id"], "not_in_evidence")
               in ("support", "refute")]
    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)
    y_true: list[str] = []
    y_pred: list[str] = []
    for rec in sr_recs:
        res = module.verify(build_qa_input(rec))
        y_true.append(silver.get(rec["instance_id"]))
        y_pred.append(res.verdict)
        mark = "✓" if res.verdict == silver.get(rec["instance_id"]) else "✗"
        print(f"{mark} {rec['instance_id']} "
              f"truth={silver.get(rec['instance_id']):8s} "
              f"pred={res.verdict}")
    agree = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    print(f"\nE3b-frozen SR-{len(sr_recs)}: agreement {agree}/{len(sr_recs)} "
          f"({agree / len(sr_recs) * 100:.0f}%)")
    m = classification_metrics(y_true, y_pred)
    print(f"S/R子集 mF1={m['macro_f1']:.3f}")


if __name__ == "__main__":
    main()
