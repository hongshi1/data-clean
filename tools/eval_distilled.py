"""D1 distilled model end-to-end evaluation.

Compares the L2 residual channel with the EGT checkpoint vs the GLM-5.3
distilled checkpoint on the honest evaluation splits:
  - test-46 (91QA held-out, theme-cluster split, never in training)
  - full-91 (silver comparison; dev-45 was in the teacher data)
  - violations-17 (real injected violations)
  - crossdoc-150 (5 documents, sound answers)

Gate is calibrated on dev-45 only (the honest contract); test-46 runs
with the dev-calibrated gate.
"""
from __future__ import annotations

import argparse
import json
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
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"


def load_records(corpus: str) -> list[dict]:
    if corpus == "qa91":
        return load_frozen_qa()
    if corpus == "violations":
        return [json.loads(line) for line in
                VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
    raise ValueError(corpus)


def eval_config(module: QAConsistencyModule, records: list[dict],
                labels: dict[str, dict]) -> dict:
    y_true: list[str] = []
    y_pred: list[str] = []
    for rec in records:
        req = build_qa_input(rec)
        res = module.verify(req)
        row = labels.get(rec["instance_id"])
        if row is None:
            continue
        truth = row["label"] if isinstance(row, dict) else str(row)
        y_true.append(truth)
        y_pred.append(res.verdict)
    m = classification_metrics(y_true, y_pred)
    return m


def main() -> None:
    sys_stdout_reconfigure()
    parser = argparse.ArgumentParser()
    parser.add_argument("--gates", nargs="*", type=float, default=[0.7])
    parser.add_argument("--checkpoints", nargs="*",
                        default=["egt_finetuned_v2", "distilled_v1"])
    parser.add_argument("--corpora", nargs="*",
                        default=["test46", "qa91", "violations"])
    args = parser.parse_args()

    records = load_records("qa91")
    silver = load_silver_labels(LABELS)
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    test_recs = [r for r in records if r["instance_id"] not in dev_ids]

    vio_records = load_records("violations")
    vio_labels = {r["instance_id"]: {"label": r["expected_verdict"]}
                  for r in vio_records}

    corpora_map = {
        "test46": (test_recs, silver),
        "qa91": (records, silver),
        "violations": (vio_records, vio_labels),
    }

    results: dict[str, dict] = {}
    for ckpt in args.checkpoints:
        for gate in args.gates:
            module = QAConsistencyModule(
                use_experts=True,
                use_nli_residual=True,
                nli_model_path=f"models/nli/{ckpt}",
                nli_gate=gate)
            for corpus in args.corpora:
                recs, labels = corpora_map[corpus]
                m = eval_config(module, recs, labels)
                key = f"{ckpt}|gate={gate}|{corpus}"
                rc = m["per_class"].get("refute", {"f1": 0.0,
                                                   "precision": 0.0,
                                                   "recall": 0.0})
                print(f"{ckpt:22s} gate={gate:.2f} {corpus:12s} "
                      f"acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
                      f"refuteF1={rc['f1']:.3f} "
                      f"(P={rc['precision']:.2f} R={rc['recall']:.2f})")
                results[key] = m

    out = BASE / "data/gjb_438c/distillation/eval_distilled_v1.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"→ {out}")


def sys_stdout_reconfigure() -> None:
    import sys
    sys.stdout.reconfigure(encoding="utf-8")


if __name__ == "__main__":
    main()
