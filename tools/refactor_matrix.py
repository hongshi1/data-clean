"""Refactor decision matrix: decomposition × aggregation × datasets.

Determines the v3 architecture empirically. Decompositions:
  A typed     original decompose_claims (regex typed + fallbacks)
  B sentence  pure sentence/list split (SummaC-style)
  C fix       decompose_claims_v2 (colon-split + frame filter)
Aggregations: strict / dominant_70 / no_minor_block (existing variants).
Datasets: test46 / violations17 / crossdoc150.

Usage:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/refactor_matrix.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.answer_claims import (  # noqa: E402
    decompose_claims as typed_decompose,
)
from algorithms.consistency.answer_claims_v2 import (  # noqa: E402
    decompose_claims_v2 as fix_decompose,
)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_decomp_ablation import (  # noqa: E402
    load_datasets,
    load_labels,
    sentence_only_decompose,
)

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
OUT = BASE / "data/gjb_438c/distillation/refactor_matrix_v1.json"
NLI_PATH = "models/nli/distilled_v1"
GATE = 0.8
DECOMPS = {
    "A_typed": typed_decompose,
    "B_sentence": sentence_only_decompose,
    "C_fix": fix_decompose,
}
AGGS = ("strict", "dominant_70", "no_minor_block")
#: ratio扫描(dominant_70连续化: strict=1.0, 原版=0.70)
RATIOS = (0.60, 0.70, 0.80, 0.90, 1.0)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    datasets = load_datasets()
    labels = load_labels(datasets)
    original = qa_module.decompose_claims

    results: dict[str, dict[str, Any]] = {}
    for decomp_name, decomp_fn in DECOMPS.items():
        qa_module.decompose_claims = decomp_fn
        try:
            for agg in AGGS:
                if agg == "dominant_70":
                    for ratio in RATIOS:
                        qa_module._DOMINANT_SUPPORT_RATIO = ratio
                        module = QAConsistencyModule(
                            use_experts=True, use_nli_residual=True,
                            nli_model_path=NLI_PATH, nli_gate=GATE,
                            aggregation=agg)
                        row = run_all(module, datasets, labels)
                        key = f"{decomp_name}|dominant{ratio:.2f}"
                        results[key] = row
                        print_row(key, row)
                    qa_module._DOMINANT_SUPPORT_RATIO = 0.70
                    continue
                module = QAConsistencyModule(
                    use_experts=True, use_nli_residual=True,
                    nli_model_path=NLI_PATH, nli_gate=GATE,
                    aggregation=agg)
                row = run_all(module, datasets, labels)
                key = f"{decomp_name}|{agg}"
                results[key] = row
                print_row(key, row)
        finally:
            qa_module.decompose_claims = original
            qa_module._DOMINANT_SUPPORT_RATIO = 0.70

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"→ {OUT}")


def run_all(module: QAConsistencyModule,
            datasets: dict, labels: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ds_name, records in datasets.items():
        y_true = [labels[ds_name][str(r["instance_id"])] for r in records]
        y_pred = [module.verify(build_qa_input(r)).verdict for r in records]
        out[ds_name] = classification_metrics(y_true, y_pred)
    return out


def print_row(key: str, row: dict) -> None:
    parts = []
    for ds_name in ("test46", "violations17", "crossdoc150"):
        m = row[ds_name]
        parts.append(f"{ds_name} acc={m['accuracy']:.4f} "
                     f"mF1={m['macro_f1']:.4f}")
    print(f"{key:28s} " + " | ".join(parts), flush=True)


if __name__ == "__main__":
    main()
