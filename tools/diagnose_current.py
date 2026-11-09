"""Diagnose current performance and identify improvement opportunities."""
from __future__ import annotations

from pathlib import Path

from algorithms.consistency.eval_lib import (
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule

LABELS = Path("data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
              "/final_labels.jsonl")


def main() -> None:
    records = load_frozen_qa()
    labels = load_silver_labels(LABELS)

    mod = QAConsistencyModule(use_experts=True)
    y_true: list[str] = []
    y_pred: list[str] = []
    unresolved = 0
    total_claims = 0
    method_counts: dict[str, int] = {}

    for rec in records:
        req = build_qa_input(rec)
        res = mod.verify(req)
        y_true.append(labels.get(rec["instance_id"], "not_in_evidence"))
        y_pred.append(res.verdict)
        for r in res.claim_results:
            total_claims += 1
            method_counts[r.method] = method_counts.get(r.method, 0) + 1
            if r.method in ("semantic_unresolved", "conservative_unresolved"):
                unresolved += 1

    m = classification_metrics(y_true, y_pred)
    print("Current deterministic layer (fast):")
    print(f"  acc={m['accuracy']:.4f}")
    print(f"  macroF1={m['macro_f1']:.4f}")
    for cls, pm in m["per_class"].items():
        print(f"  {cls}: P={pm['precision']:.3f} "
              f"R={pm['recall']:.3f} F1={pm['f1']:.3f}")
    print(f"  confusion: {m['confusion']}")
    print()
    print(f"Residual claims: {unresolved}/{total_claims} "
          f"= {unresolved / total_claims * 100:.1f}%")
    print()
    print("Method distribution:")
    for method, count in sorted(method_counts.items(),
                                key=lambda x: -x[1]):
        print(f"  {method}: {count}")


if __name__ == "__main__":
    main()
