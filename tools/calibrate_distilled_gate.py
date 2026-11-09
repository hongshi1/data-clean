"""Gate calibration for the distilled checkpoint on dev-45 (honest contract).

Also runs crossdoc-150 generalization at the dev-calibrated gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from algorithms.consistency.eval_lib import (
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule

BASE = Path(__file__).resolve().parents[1]
LABELS = BASE / ("data/gjb_438c/runs/"
                 "review_qa_with_glm53_582b51e5_20261021_145212"
                 "/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"

GATES = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    records = load_frozen_qa()
    silver = load_silver_labels(LABELS)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    dev_recs = [r for r in records if r["instance_id"] in dev_ids]
    test_recs = [r for r in records if r["instance_id"] not in dev_ids]

    # crossdoc-150
    cross: list[dict] = []
    for doc in ("05", "06", "07", "08", "10"):
        p = BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}_evalset_v1.jsonl"
        cross += [json.loads(line) for line in
                  p.read_text(encoding="utf-8").splitlines() if line.strip()]
    cross_labels = {r["instance_id"]: r["sound_label"] for r in cross}

    for ckpt in ("distilled_v1",):
        best = (0.0, 0.7)
        for gate in GATES:
            module = QAConsistencyModule(
                use_experts=True, use_nli_residual=True,
                nli_model_path=f"models/nli/{ckpt}", nli_gate=gate)
            y_true = [silver.get(r["instance_id"], "not_in_evidence")
                      for r in dev_recs]
            y_pred = [module.verify(build_qa_input(r)).verdict
                      for r in dev_recs]
            m = classification_metrics(y_true, y_pred)
            rc = m["per_class"].get("refute", {"f1": 0.0})
            print(f"DEV {ckpt} gate={gate:.2f} acc={m['accuracy']:.4f} "
                  f"mF1={m['macro_f1']:.4f} refuteF1={rc['f1']:.3f}")
            if m["macro_f1"] > best[0]:
                best = (m["macro_f1"], gate)
        gate = best[1]
        print(f"dev-calibrated gate = {gate}")

        # honest test + crossdoc at calibrated gate
        module = QAConsistencyModule(
            use_experts=True, use_nli_residual=True,
            nli_model_path=f"models/nli/{ckpt}", nli_gate=gate)
        y_true = [silver.get(r["instance_id"], "not_in_evidence")
                  for r in test_recs]
        y_pred = [module.verify(build_qa_input(r)).verdict
                  for r in test_recs]
        m = classification_metrics(y_true, y_pred)
        rc = m["per_class"].get("refute", {"f1": 0.0,
                                           "precision": 0.0,
                                           "recall": 0.0})
        print(f"TEST46 {ckpt} gate={gate:.2f} acc={m['accuracy']:.4f} "
              f"mF1={m['macro_f1']:.4f} refuteF1={rc['f1']:.3f} "
              f"(P={rc['precision']:.2f} R={rc['recall']:.2f})")

        y_true = [cross_labels.get(r["instance_id"], "support")
                  for r in cross]
        y_pred = [module.verify(build_qa_input(r)).verdict
                  for r in cross]
        m = classification_metrics(y_true, y_pred)
        print(f"CROSS150 {ckpt} gate={gate:.2f} acc={m['accuracy']:.4f} "
              f"mF1={m['macro_f1']:.4f}")


if __name__ == "__main__":
    main()
