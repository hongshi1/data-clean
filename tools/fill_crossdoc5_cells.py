"""Fill missing matrix cells: GLM-5 / Erlangshen / CMNLI-finetuned on crossdoc5.

Runs the three external baselines on the 150-instance crossdoc x5 set using
the same direct-pair protocol as eval_public_matrix (premise=evidence text,
hypothesis=answer), producing macro-F1 per method for the final paper table.
"""
from __future__ import annotations

import json
import statistics

from algorithms.consistency.public_baselines import (
    glm_public_verdicts,
    nli_verdicts,
)
from algorithms.consistency.eval_lib import classification_metrics

SET = "data/gjb_438c/qa_frozen/crossdoc5_evalset_v1.jsonl"
PREMISE_LIMIT = 1500


def premise_of(record: dict) -> str:
    parts = []
    for ev in record["evidence"]:
        parts.append(ev.get("text", ""))
    text = "\n".join(parts)
    return text[:PREMISE_LIMIT]


def load_pairs() -> list[dict]:
    pairs = []
    for line in open(SET, encoding="utf-8"):
        rec = json.loads(line)
        pairs.append({
            "premise": premise_of(rec),
            "hypothesis": rec["answer"],
            "label": rec["sound_label"],
            "instance_id": rec["instance_id"],
        })
    return pairs


def score(y_true: list[str], y_pred: list[str], name: str) -> None:
    m = classification_metrics(y_true, y_pred)
    print(f"{name}: macroF1={m['macro_f1']:.4f} acc={m['accuracy']:.4f}")
    for cls, pm in m["per_class"].items():
        print(f"   {cls}: P={pm['precision']:.3f} R={pm['recall']:.3f}"
              f" F1={pm['f1']:.3f}")


def main() -> None:
    pairs = load_pairs()
    y_true = [p["label"] for p in pairs]
    print(f"crossdoc5: {len(pairs)} instances")

    model_dirs = {
        "mdeberta_zero": "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7",
        "erlangshen_zero": "models/nli/Erlangshen-Roberta-330M-NLI",
        "cmnli_finetuned": "models/nli/cmnli_finetuned_mdeberta",
    }
    for name, model_dir in model_dirs.items():
        print(f"== {name} ==")
        pred = nli_verdicts(pairs, model_dir)
        score(y_true, pred, name)

    print("== GLM-5 direct ==")
    pred = glm_public_verdicts(pairs)
    score(y_true, pred, "glm5_direct")


if __name__ == "__main__":
    main()
