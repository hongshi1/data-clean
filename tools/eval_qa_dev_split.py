r"""Dev-split evaluation of the B4 QA configuration (L0/L1 experts + L3 LLM
residual, strict aggregation) — the variant-selection protocol of the G4
support-recall study (docs/srs_project/50_support_recall_analysis.md §5).

Only the frozen dev side (data/gjb_438c/qa_frozen/dev_test_split_v1.json,
seed=42, 45 instances) is evaluated here; the test side stays untouched and
is reserved for the later honest evaluation (tools/eval_test_honest.py).
The L3 residual calls go through the llm_json disk cache (cache=True) —
the P1 fixes do not change any residual claim set, so a fully cached run
must pay zero new API calls.

Usage:
  python tools/eval_qa_dev_split.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.build_dev_test_split import SPLIT_PATH, load_split  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
LABELS = ("support", "refute", "not_in_evidence")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def prf(confusion: Counter, label: str) -> tuple[float, float, float]:
    tp = confusion[(label, label)]
    fp = sum(confusion[(label, gold)] for gold in LABELS if gold != label)
    fn = sum(confusion[(pred, label)] for pred in LABELS if pred != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return precision, recall, f1


def metrics(confusion: Counter, n: int) -> dict[str, Any]:
    per_class = {}
    for label in LABELS:
        precision, recall, f1 = prf(confusion, label)
        per_class[label] = {"precision": round(precision, 4),
                            "recall": round(recall, 4),
                            "f1": round(f1, 4)}
    accuracy = sum(confusion[(p, g)] for p in LABELS for g in LABELS
                   if p == g) / n if n else 0.0
    return {
        "n": n,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(
            sum(per_class[label]["f1"] for label in LABELS) / len(LABELS), 4),
        "per_class": per_class,
        "confusion[predicted, silver]": {
            f"{p}|{g}": confusion[(p, g)]
            for p in LABELS for g in LABELS if confusion[(p, g)]},
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-llm-residual", action="store_true",
                        default=True,
                        help="B4配置(L0/L1专家+L3 LLM残差, 默认开; "
                             "--no-llm-residual退化为确定性专家配置)")
    parser.add_argument("--no-llm-residual", dest="use_llm_residual",
                        action="store_false")
    args = parser.parse_args(argv)

    if not SPLIT_PATH.exists():
        sys.exit(f"冻结切分不存在: {SPLIT_PATH}(先运行 "
                 "python tools/build_dev_test_split.py)")
    split = load_split(SPLIT_PATH)
    dev_ids = list(split["dev"])

    rows = {row["instance_id"]: row for row in read_jsonl(QA_FROZEN)}
    silver = {row["instance_id"]: row for row in read_jsonl(SILVER)}
    missing = [iid for iid in dev_ids if iid not in rows or iid not in silver]
    if missing:
        sys.exit(f"dev实例缺冻结行或silver标签: {missing}")

    module = QAConsistencyModule(
        use_experts=True, use_llm_residual=args.use_llm_residual)
    confusion: Counter = Counter()
    per_row = []
    for iid in dev_ids:
        result = module.verify(request_from_dict(rows[iid]))
        gold = silver[iid]["final_verdict"]
        confusion[(result.verdict, gold)] += 1
        per_row.append({
            "instance_id": iid,
            "predicted": result.verdict,
            "silver": gold,
            "claim_methods": [claim.method for claim in result.claim_results],
            "claims": [{
                "claim_text": claim.claim_text[:80],
                "verdict": claim.verdict,
                "method": claim.method,
            } for claim in result.claim_results],
        })

    score = metrics(confusion, len(dev_ids))
    run = open_run("eval_qa_dev_split", {
        "input": str(QA_FROZEN.relative_to(BASE)),
        "labels": str(SILVER.relative_to(BASE)),
        "split": str(SPLIT_PATH.relative_to(BASE)),
        "side": "dev",
        "n": len(dev_ids),
        "module_config": {"use_experts": True,
                          "use_llm_residual": args.use_llm_residual},
        "protocol": ("dev-side only (frozen split seed=42); test side "
                     "reserved for the honest evaluation"),
    })
    run.save_result({**score, "per_row": per_row})
    print(json.dumps(score, ensure_ascii=False, indent=2))
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
