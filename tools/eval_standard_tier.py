"""Evaluate the standard tier (L2 NLI residual channel enabled)."""
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

    mod = QAConsistencyModule(
        use_experts=True,
        use_nli_residual=True,
        nli_model_path="models/nli/egt_finetuned_v2",
    )
    y_true: list[str] = []
    y_pred: list[str] = []
    errors: list[str] = []
    for rec in records:
        req = build_qa_input(rec)
        res = mod.verify(req)
        gt = labels.get(rec["instance_id"], "not_in_evidence")
        y_true.append(gt)
        y_pred.append(res.verdict)
        if res.verdict != gt:
            errors.append(rec["instance_id"])

    m = classification_metrics(y_true, y_pred)
    print("L2 NLI channel enabled (standard tier):")
    print(f"  acc={m['accuracy']:.4f}")
    print(f"  macro_f1={m['macro_f1']:.4f}")
    for cls, pm in m["per_class"].items():
        print(f"  {cls}: P={pm['precision']:.3f} "
              f"R={pm['recall']:.3f} F1={pm['f1']:.3f}")
    print(f"  errors: {sorted(errors)}")


if __name__ == "__main__":
    main()
