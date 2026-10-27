"""Evaluate QAConsistencyModule (our method) against labels.

Label source: --labels silver (default, GLM-5.3 silver from
review_qa_with_glm53 run) or gold (qa_frozen/scene1_gold_v1.jsonl,
exported by tools/finalize_gold.py from human annotations).
"""
from __future__ import annotations

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
from tools.run_utils import open_run  # noqa: E402

LABELS = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
LABELS_GOLD = BASE / "data/gjb_438c/qa_frozen/scene1_gold_v1.jsonl"
VERDICTS = ("support", "refute", "not_in_evidence")


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def load_labels(path: Path) -> dict[str, dict]:
    """标签文件→instance_id行映射(重复id/缺id报错, 不静默)."""
    labels: dict[str, dict] = {}
    for row in read_jsonl(path):
        iid = str(row.get("instance_id", "") or "")
        if not iid:
            raise ValueError(f"标签文件{path}含缺instance_id的行")
        if iid in labels:
            raise ValueError(f"标签文件{path}instance_id重复: {iid}")
        labels[iid] = row
    return labels


def label_verdict(label_row: dict, iid: str) -> str:
    """标签行→三态verdict(silver读final_verdict, gold行兼容gold_verdict)."""
    verdict = label_row.get("final_verdict", label_row.get("gold_verdict"))
    if verdict not in VERDICTS:
        raise ValueError(
            f"{iid}: 标签verdict非法: {verdict!r}(合法: {VERDICTS})")
    return verdict


def macro_f1(confusion: Counter, labels) -> float:
    f1s = []
    for label in labels:
        tp = confusion[(label, label)]
        fp = sum(confusion[(pred, label)] for pred in labels if pred != label)
        fn = sum(confusion[(label, gold)] for gold in labels if gold != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        f1s.append(f1)
    return sum(f1s) / len(f1s)


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
    rows = read_jsonl(BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    labels = load_labels(labels_path)
    module = QAConsistencyModule(
        semantic_nli=semantic_nli,
        nli_contra_threshold=args.nli_contra_threshold,
        nli_entail_threshold=args.nli_entail_threshold,
    )
    confusion: Counter = Counter()
    methods: Counter = Counter()
    per_row = []
    missing_labels: list[str] = []
    for row in rows:
        request = request_from_dict(row)
        result = module.verify(request)
        if args.nli:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
        label_row: Any | None = labels.get(request.instance_id)
        if label_row is None:
            # gold标签可能只覆盖已标注实例: 跳过并单独计数, 不进指标分母
            missing_labels.append(request.instance_id)
            per_row.append({
                "instance_id": request.instance_id,
                "predicted": result.verdict,
                "label": None,
                "status": result.status,
                "claim_methods": [claim.method for claim in result.claim_results],
            })
            continue
        gold = label_verdict(label_row, request.instance_id)
        prediction = result.verdict
        confusion[(prediction, gold)] += 1
        methods.update(claim.method for claim in result.claim_results)
        per_row.append({
            "instance_id": request.instance_id,
            "predicted": prediction,
            "label": gold,
            "status": result.status,
            "claim_methods": [claim.method for claim in result.claim_results],
        })
    n_evaluated = len(rows) - len(missing_labels)
    if n_evaluated == 0:
        sys.exit(f"标签文件{labels_path}与冻结QA无共同instance_id, 无法评测")
    labels_set = ("support", "refute", "not_in_evidence")
    accuracy = sum(confusion[(p, g)] for p in labels_set for g in labels_set
                   if p == g) / n_evaluated
    run = open_run(f"eval_qa_module_{args.labels}", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(labels_path.relative_to(BASE)),
        "label_type": label_type,
        "n": len(rows),
        "n_evaluated": n_evaluated,
        "n_missing_labels": len(missing_labels),
    })
    run.save_result({
        "n": len(rows),
        "n_evaluated": n_evaluated,
        "n_missing_labels": len(missing_labels),
        "missing_label_instance_ids": missing_labels,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1(confusion, labels_set), 4),
        "confusion[predicted, label]": {
            f"{p}|{g}": confusion[(p, g)]
            for p in labels_set for g in labels_set if confusion[(p, g)]
        },
        "claim_method_distribution": dict(methods),
        "label_note": label_note,
        "per_row": per_row,
    })
    print(json.dumps({
        "n": len(rows),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1(confusion, labels_set), 4),
        "confusion": {f"{p}|{g}": confusion[(p, g)]
                      for p in labels_set for g in labels_set if confusion[(p, g)]},
        "claim_methods": dict(methods),
        "label_type": label_type,
        "n_evaluated": n_evaluated,
        "n_missing_labels": len(missing_labels),
    }, ensure_ascii=False, indent=2))
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
