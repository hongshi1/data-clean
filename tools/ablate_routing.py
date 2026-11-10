"""Ablation: does route_question gate anything in the default path?

Patches route_question to return () everywhere it is imported and
re-runs the 91QA fast-tier evaluation. If verdicts are identical, the
router is pure annotation (traceability labels), not a gating stage.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import algorithms.consistency.answer_claims as ac_mod  # noqa: E402
import algorithms.consistency.deq_pipeline as dq_mod  # noqa: E402
import algorithms.consistency.qa_module as qm_mod  # noqa: E402
import algorithms.consistency.qa_router as qr_mod  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

LABELS = (Path(__file__).resolve().parents[1]
          / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")


def run_eval(module: QAConsistencyModule) -> tuple[list[str], dict]:
    records = load_frozen_qa()
    labels = load_silver_labels(LABELS)
    y_true: list[str] = []
    y_pred: list[str] = []
    for rec in records:
        res = module.verify(build_qa_input(rec))
        y_true.append(labels.get(rec["instance_id"], "not_in_evidence"))
        y_pred.append(res.verdict)
    return y_pred, classification_metrics(y_true, y_pred)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    mod = QAConsistencyModule(use_experts=True)
    base_pred, m_base = run_eval(mod)
    print(f"基线(路由正常): acc={m_base['accuracy']:.4f} "
          f"mF1={m_base['macro_f1']:.4f}")

    targets = (qr_mod, ac_mod, qm_mod, dq_mod)
    originals = [m.route_question for m in targets]
    for target in targets:
        target.route_question = lambda q: ()
    abl_pred, m_abl = run_eval(mod)
    for target, orig in zip(targets, originals):
        target.route_question = orig

    print(f"消融(路由为空): acc={m_abl['accuracy']:.4f} "
          f"mF1={m_abl['macro_f1']:.4f}")
    records = load_frozen_qa()
    diff = [rec["instance_id"] for rec, a, b in
            zip(records, base_pred, abl_pred) if a != b]
    print(f"预测差异实例数: {len(diff)}/{len(records)}")
    if diff:
        print(f"  差异实例: {diff[:10]}")


if __name__ == "__main__":
    main()
