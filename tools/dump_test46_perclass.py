"""Complete per-class metrics for the headline config (distilled_v1, gate 0.8)."""
from __future__ import annotations

import json
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
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    silver = load_silver_labels(SILVER)
    qa = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    test = [r for r in qa if r["instance_id"] not in dev_ids]

    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)
    y_true = [silver.get(r["instance_id"], "not_in_evidence") for r in test]
    y_pred = [module.verify(build_qa_input(r)).verdict for r in test]
    m = classification_metrics(y_true, y_pred)
    print(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
