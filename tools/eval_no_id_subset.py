#!/usr/bin/env python3
"""Quantify the explicit-identifier lexical shortcut in training_pairs_v1.

Protocol (protocol #48, task 2):
  - no-ID subset: pairs where BOTH the anchor and candidate texts contain no
    explicit identifier matching ``r'\\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\\b'``.
  - control subset: positives that contain an explicit identifier paired with
    negatives that contain none.
  - Native frozen-BGE cosine AUC on each subset (vectors.npz, no projection,
    no training). The AUC gap between the two groups measures how much of the
    apparent separability is the trivial literal-ID shortcut rather than
    semantics.

Silver positives are constructed from shared explicit identifiers, so the
no-ID subset is expected to have very few (here: zero) positives; the counts
are reported honestly either way and a supplementary "both-sides-with-ID"
control (positives vs identifier-bearing negatives) is included to measure
discriminability once the shortcut is neutralized on the negative side.

Usage: python tools/eval_no_id_subset.py
Output: printed summary + runs protocol result.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
SNAPSHOT_DIR = BASE / "data/gjb_438c/feature_snapshot_v1"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
ID_PATTERN = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")

sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402


def load_pairs(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_snapshot(path: Path) -> tuple[dict[str, int], np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(value) for value in data["ids"].tolist()]
    index = {occurrence_id: position for position, occurrence_id in enumerate(ids)}
    return index, matrix


def rank_auc(scores: list[float], labels: list[int]) -> float | None:
    """AUC = P(score_pos > score_neg) with midrank tie correction; None if one-sided."""

    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    order = sorted(range(len(scores)), key=lambda position: scores[position])
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and scores[order[end + 1]] == scores[order[start]]:
            end += 1
        average_rank = (start + end) / 2.0 + 1.0
        for position in order[start : end + 1]:
            ranks[position] = average_rank
        start = end + 1
    rank_sum_pos = sum(
        ranks[position] for position, label in enumerate(labels) if label == 1
    )
    return (rank_sum_pos - positives * (positives + 1) / 2.0) / (positives * negatives)


def native_subset_metrics(
    index: dict[str, int], matrix: np.ndarray, members: list[dict[str, Any]]
) -> dict[str, Any]:
    scores: list[float] = []
    labels: list[int] = []
    skipped = 0
    for pair in members:
        anchor_id = pair["anchor"]["occurrence_id"]
        candidate_id = pair["candidate"]["occurrence_id"]
        if anchor_id not in index or candidate_id not in index:
            skipped += 1
            continue
        vector_a = matrix[index[anchor_id]]
        vector_b = matrix[index[candidate_id]]
        norm = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
        scores.append(float(vector_a @ vector_b) / max(norm, 1e-12))
        labels.append(int(pair["label"]))
    auc = rank_auc(scores, labels)
    positives = sum(labels)
    return {
        "n_pairs": len(labels),
        "n_pos": positives,
        "n_neg": len(labels) - positives,
        "auc_native_bge": round(auc, 4) if auc is not None else None,
        "mean_score_pos": (
            round(sum(s for s, lb in zip(scores, labels) if lb == 1) / positives, 4)
            if positives
            else None
        ),
        "mean_score_neg": (
            round(
                sum(s for s, lb in zip(scores, labels) if lb == 0)
                / max(len(labels) - positives, 1),
                4,
            )
            if labels
            else None
        ),
        "skipped_missing_vector": skipped,
    }


def main() -> None:
    pairs = load_pairs(PAIRS_PATH)
    index, matrix = load_snapshot(SNAPSHOT_DIR / "vectors.npz")

    def has_id(text: str) -> bool:
        return bool(ID_PATTERN.search(text))

    no_id = [
        pair
        for pair in pairs
        if not has_id(pair["anchor"]["text"]) and not has_id(pair["candidate"]["text"])
    ]
    pos_with_id = [
        pair
        for pair in pairs
        if pair["label"] == 1
        and (has_id(pair["anchor"]["text"]) or has_id(pair["candidate"]["text"]))
    ]
    neg_without_id = [
        pair
        for pair in pairs
        if pair["label"] == 0
        and not has_id(pair["anchor"]["text"])
        and not has_id(pair["candidate"]["text"])
    ]
    neg_with_id = [
        pair
        for pair in pairs
        if pair["label"] == 0
        and has_id(pair["anchor"]["text"])
        and has_id(pair["candidate"]["text"])
    ]
    pos_without_id = [pair for pair in pairs if pair["label"] == 1 and pair not in pos_with_id]

    no_id_metrics = native_subset_metrics(index, matrix, no_id)
    control_metrics = native_subset_metrics(index, matrix, pos_with_id + neg_without_id)
    both_id_metrics = native_subset_metrics(index, matrix, pos_with_id + neg_with_id)

    if no_id_metrics["auc_native_bge"] is None:
        gap = None
        conclusion = (
            "no-ID positives = "
            f"{no_id_metrics['n_pos']}: every silver P1 positive carries an "
            "explicit identifier, so an ID-free AUC is undefined; the "
            "identifier shortcut is not merely present, it constitutes the "
            "entire positive supervision basis. Control AUC "
            f"(pos-with-ID vs neg-without-ID) = {control_metrics['auc_native_bge']} "
            "measures the shortcut's separability; the both-sides-with-ID "
            "control "
            f"({both_id_metrics['auc_native_bge']}) measures discriminability "
            "once negatives also carry identifiers."
        )
    else:
        gap = round(
            float(control_metrics["auc_native_bge"]) - float(no_id_metrics["auc_native_bge"]), 4
        )
        conclusion = (
            f"explicit-ID shortcut AUC gap (control - no-ID) = {gap}: "
            "positives without identifiers are separable at "
            f"{no_id_metrics['auc_native_bge']}, with identifiers at "
            f"{control_metrics['auc_native_bge']}."
        )

    result = {
        "protocol": (
            "native frozen-BGE cosine AUC on explicit-ID lexical subsets of "
            "training_pairs_v1; no projection, no training"
        ),
        "id_regex": ID_PATTERN.pattern,
        "total_pairs": len(pairs),
        "no_id_subset": no_id_metrics,
        "control_pos_id_neg_noid": control_metrics,
        "control_both_sides_with_id": both_id_metrics,
        "pos_without_id_total": len(pos_without_id),
        "auc_gap_control_minus_no_id": gap,
        "conclusion": conclusion,
    }
    run = open_run(
        "eval_no_id_subset",
        {
            "pairs": str(PAIRS_PATH),
            "snapshot": str(SNAPSHOT_DIR),
            "id_regex": ID_PATTERN.pattern,
            "subsets": ["no_id", "pos_id_neg_noid", "both_sides_with_id"],
        },
        RUNS_ROOT,
    )
    run.save_result(result)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
