"""D1 gate sweep on crossdoc-150 (does crossdoc need a different gate?)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from algorithms.consistency.eval_lib import (
    build_qa_input,
    classification_metrics,
)
from algorithms.consistency.qa_module import QAConsistencyModule

BASE = Path(__file__).resolve().parents[1]
GATES = (0.5, 0.6, 0.7, 0.8)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    cross: list[dict] = []
    for doc in ("05", "06", "07", "08", "10"):
        p = BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}_evalset_v1.jsonl"
        cross += [json.loads(line) for line in
                  p.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = {r["instance_id"]: r["sound_label"] for r in cross}

    for ckpt in ("distilled_v1",):
        for gate in GATES:
            module = QAConsistencyModule(
                use_experts=True, use_nli_residual=True,
                nli_model_path=f"models/nli/{ckpt}", nli_gate=gate)
            y_true = [labels[r["instance_id"]] for r in cross]
            y_pred = [module.verify(build_qa_input(r)).verdict
                      for r in cross]
            m = classification_metrics(y_true, y_pred)
            print(f"{ckpt} gate={gate:.2f} acc={m['accuracy']:.4f} "
                  f"mF1={m['macro_f1']:.4f}")


if __name__ == "__main__":
    main()
