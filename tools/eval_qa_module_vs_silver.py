"""Evaluate QAConsistencyModule (our method) against labels.

Label source: --labels silver (default, GLM-5.3 silver from
review_qa_with_glm53 run) or gold (qa_frozen/scene1_gold_v1.jsonl,
exported by tools/finalize_gold.py from human annotations).

加载/指标/运行骨架统一走algorithms.consistency.eval_lib (Wave 8-H1去重);
行为保持: 输出schema与数字与重构前逐位一致.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence

BASE = Path(__file__).resolve().parents[1]

if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    evaluate_module,
    label_verdict as _label_verdict,
    load_frozen_qa,
    load_label_rows,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

LABELS = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
LABELS_GOLD = BASE / "data/gjb_438c/qa_frozen/scene1_gold_v1.jsonl"


def load_labels(path: Path) -> dict[str, dict]:
    """标签文件→instance_id行映射(重复id/缺id报错, 不静默)."""
    return load_label_rows(path)


def label_verdict(label_row: dict, iid: str) -> str:
    """标签行→三态verdict(silver读final_verdict, gold行兼容gold_verdict)."""
    return _label_verdict(label_row, iid)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", choices=("silver", "gold"),
                        default="silver",
                        help="label source: silver (final_labels.jsonl, "
                             "default) or gold (qa_frozen/scene1_gold_v1.jsonl, "
                             "run tools/finalize_gold.py export first)")
    parser.add_argument("--nli", action="store_true",
                        help="enable the local NLI residual channel (mdeberta)")
    parser.add_argument("--nli-contra-threshold", type=float, default=0.6)
    parser.add_argument("--nli-entail-threshold", type=float, default=0.6)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    semantic_nli = None
    if args.nli:
        from algorithms.consistency.nli_local import NliLocal

        client = NliLocal("mdeberta")
        client.ensure()

        def semantic_nli(pairs):  # noqa: F811
            return client.predict(pairs)

        print(f"nli ready: mode={client.mode} "
              f"contra>={args.nli_contra_threshold} "
              f"entail>={args.nli_entail_threshold}")
    labels_path = LABELS if args.labels == "silver" else LABELS_GOLD
    if args.labels == "gold" and not labels_path.exists():
        sys.exit(f"gold标签不存在: {labels_path}"
                 "(先运行 python tools/finalize_gold.py export)")
    label_type = "glm53_silver_not_gold" if args.labels == "silver" \
        else "human_gold_v1"
    label_note = ("silver labels from GLM-5.3 review; not human gold"
                  if args.labels == "silver" else
                  "human gold labels (annotation workbench v1)")
    rows = load_frozen_qa()
    labels = load_silver_labels(
        labels_path, verdict_keys=("final_verdict", "gold_verdict"))
    module = QAConsistencyModule(
        semantic_nli=semantic_nli,
        nli_contra_threshold=args.nli_contra_threshold,
        nli_entail_threshold=args.nli_entail_threshold,
    )
    try:
        outcome = evaluate_module(module, rows, labels)
    except ValueError as exc:
        if "无共同instance_id" not in str(exc):
            raise
        # gold标签可能只覆盖已标注实例; 全缺时与原实现同文退出
        sys.exit(f"标签文件{labels_path}与冻结QA无共同instance_id, 无法评测")
    n_evaluated = outcome.n_evaluated
    per_row = [{
        "instance_id": row["instance_id"],
        "predicted": row["predicted"],
        "label": row["label"],
        "status": row["status"],
        "claim_methods": row["claim_methods"],
    } for row in outcome.per_row]
    run = open_run(f"eval_qa_module_{args.labels}", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(labels_path.relative_to(BASE)),
        "label_type": label_type,
        "n": len(rows),
        "n_evaluated": n_evaluated,
        "n_missing_labels": len(outcome.missing_labels),
    })
    run.save_result({
        "n": len(rows),
        "n_evaluated": n_evaluated,
        "n_missing_labels": len(outcome.missing_labels),
        "missing_label_instance_ids": outcome.missing_labels,
        "accuracy": outcome.metrics["accuracy"],
        "macro_f1": outcome.metrics["macro_f1"],
        "confusion[predicted, label]": outcome.metrics["confusion"],
        "claim_method_distribution": dict(outcome.methods),
        "label_note": label_note,
        "per_row": per_row,
    })
    print(json.dumps({
        "n": len(rows),
        "accuracy": outcome.metrics["accuracy"],
        "macro_f1": outcome.metrics["macro_f1"],
        "confusion": outcome.metrics["confusion"],
        "claim_methods": dict(outcome.methods),
        "label_type": label_type,
        "n_evaluated": n_evaluated,
        "n_missing_labels": len(outcome.missing_labels),
    }, ensure_ascii=False, indent=2))
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
