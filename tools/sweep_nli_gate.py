"""Sweep the NLI refute gate on the dev split (theme-cluster safe).

The residual NLI channel issues refutes with miscalibrated precision
(0.39 on 91QA). The gate is the confidence threshold at which an NLI
refute is accepted. Higher gate -> fewer, more precise refutes.

This is a *calibration* experiment on dev (45 instances, 29 theme
clusters); the test split (46) stays untouched.
"""
from __future__ import annotations

from pathlib import Path

from algorithms.consistency.eval_lib import (
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.nli_residual import verify_residual_claims_nli
from algorithms.consistency.evidence_statements import linearize_context
from algorithms.consistency.qa_module import QAConsistencyModule

LABELS = Path("data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
              "/final_labels.jsonl")
SPLIT = Path("data/gjb_438c/qa_frozen/dev_test_split_v1.json")

GATES = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]


def main() -> None:
    records = load_frozen_qa()
    labels = load_silver_labels(LABELS)
    split = __import__("json").loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])

    mod = QAConsistencyModule(use_experts=True)

    # Collect residual claims per dev instance once (deterministic part).
    cache: dict[str, tuple] = {}
    for rec in records:
        if rec["instance_id"] not in dev_ids:
            continue
        req = build_qa_input(rec)
        res = mod.verify(req)
        residual = [r for r in res.claim_results
                    if r.method in ("semantic_unresolved",
                                    "conservative_unresolved")]
        statements = linearize_context(req.evidence)
        cache[rec["instance_id"]] = (req, res, residual, statements)

    for gate in GATES:
        y_true: list[str] = []
        y_pred: list[str] = []
        for iid, (req, res, residual, statements) in cache.items():
            verdicts = [r for r in res.claim_results]
            if residual and statements:
                nli_results = verify_residual_claims_nli(
                    req, residual, statements,
                    model_path="models/nli/egt_finetuned_v2",
                    gate=gate)
                verdicts = list(verdicts) + list(nli_results)
            # replicate _fuse_per_claim + strict aggregation
            fused = mod._fuse_per_claim(tuple(verdicts))
            verdict, _ = mod._aggregate(fused)
            y_true.append(labels.get(iid, "not_in_evidence"))
            y_pred.append(verdict)
        m = classification_metrics(y_true, y_pred)
        rc = m["per_class"].get("refute", {"f1": 0.0,
                                           "precision": 0.0,
                                           "recall": 0.0})
        print(f"gate={gate:.2f}  acc={m['accuracy']:.4f} "
              f"mF1={m['macro_f1']:.4f} "
              f"refuteF1={rc['f1']:.3f} "
              f"(P={rc['precision']:.2f} R={rc['recall']:.2f})")


if __name__ == "__main__":
    main()
