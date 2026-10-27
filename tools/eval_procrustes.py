#!/usr/bin/env python3
"""Procrustes cross-space alignment control (protocol #48, task 3 / A-matrix A2 row).

Fits a deterministic orthogonal map from frozen BGE vectors to Qwen3-Embedding
vectors on train-split P1 anchor pairs, then compares three similarity
families on the (doc-disjoint) test split:

  native-BGE   : cos(BGE anchor, BGE candidate)      — same-space control
  native-Qwen3 : cos(Qwen3 anchor, Qwen3 candidate)  — same-space control
  procrustes   : cos(W @ BGE anchor, Qwen3 candidate) — BGE side projected
                 into the Qwen3 space and compared cross-space

Anchor protocol: train-split positives with label_basis=explicit_identifier,
deduplicated by (anchor_text, candidate_text), sampled to <= 1500 pairs with
a fixed seed. Each anchor pair contributes TWO fit rows (its anchor-side and
candidate-side occurrences, each a BGE<->Qwen3 correspondence of the same
text); row ids are the pair's occurrence-id concatenations
"anchor/candidate" and "candidate/anchor" (unique, traceable to the pair).
Both pair ends are document-like text, so all Qwen3 encoding uses
``embed_docs``. Test-pair texts are taken from features.jsonl (the snapshot
the BGE vectors encode), not from pairs.jsonl.

Usage: python tools/eval_procrustes.py
Output: printed summary + runs protocol result.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
SNAPSHOT_DIR = BASE / "data/gjb_438c/feature_snapshot_v1"
MODEL_DIR = BASE / "models/embedding/qwen3-embedding-0.6b"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
ANCHOR_LIMIT = 1500
SAMPLE_SEED = 42
SOURCE_NAME = "bge-large-zh-v1.5"
TARGET_NAME = "qwen3-embedding-0.6b"

sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.path.insert(0, str(BASE / "tools/eval"))
from run_utils import open_run  # noqa: E402

from algorithms.context_linking.alignment import fit_orthogonal_map  # noqa: E402


def load_pairs(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_feature_texts(path: Path) -> dict[str, str]:
    """occurrence_id -> text from features.jsonl (the snapshot's text truth)."""

    mapping: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            mapping[str(row["occurrence_id"])] = str(row["text"])
    return mapping


def load_snapshot(path: Path) -> tuple[dict[str, int], np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(value) for value in data["ids"].tolist()]
    index = {occurrence_id: position for position, occurrence_id in enumerate(ids)}
    return index, matrix


def rank_auc(scores: list[float], labels: list[int]) -> float | None:
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


def select_anchor_pairs(
    pairs: list[dict[str, Any]], limit: int, seed: int
) -> tuple[list[dict[str, Any]], int, int]:
    """Dedup train-split P1 positives by (anchor_text, candidate_text), sample <= limit.

    Returns (selected_pairs, n_train_p1_positives, n_unique_text_pairs).
    """

    train_pos = [
        pair
        for pair in pairs
        if pair["split"] == "train"
        and pair["label"] == 1
        and pair["label_basis"] == "explicit_identifier"
    ]
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for pair in train_pos:
        key = (pair["anchor"]["text"], pair["candidate"]["text"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(pair)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(unique))
    selected = [unique[position] for position in order[:limit]]
    return selected, len(train_pos), len(unique)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, default=PAIRS_PATH)
    parser.add_argument("--snapshot-dir", type=Path, default=SNAPSHOT_DIR)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--anchor-limit", type=int, default=ANCHOR_LIMIT)
    parser.add_argument("--seed", type=int, default=SAMPLE_SEED)
    args = parser.parse_args()

    import torch

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA is unavailable; this protocol requires GPU encoding "
            "(no silent CPU fallback by design)"
        )
    if not (args.model_dir / "config.json").exists():
        raise SystemExit(f"Qwen3 model missing: {args.model_dir}")

    from eval_qwen3_backbone import Qwen3Encoder

    pairs = load_pairs(args.pairs)
    feature_texts = load_feature_texts(args.snapshot_dir / "features.jsonl")
    bge_index, bge_matrix = load_snapshot(args.snapshot_dir / "vectors.npz")

    anchors, n_train_pos, n_unique_text_pairs = select_anchor_pairs(
        pairs, args.anchor_limit, args.seed
    )
    test_pairs = [pair for pair in pairs if pair["split"] == "test"]

    needed: set[str] = set()
    for pair in anchors + test_pairs:
        needed.add(pair["anchor"]["occurrence_id"])
        needed.add(pair["candidate"]["occurrence_id"])
    missing_set = {
        occ for occ in needed if occ not in bge_index or occ not in feature_texts
    }
    text_mismatches = sum(
        1
        for pair in anchors + test_pairs
        for side in ("anchor", "candidate")
        if pair[side]["occurrence_id"] in feature_texts
        and feature_texts[pair[side]["occurrence_id"]] != pair[side]["text"]
    )

    unique_texts = sorted({feature_texts[occ] for occ in needed if occ in feature_texts})
    encoder = Qwen3Encoder(args.model_dir)
    encoded = encoder.embed_docs(unique_texts)
    text_row = {text: position for position, text in enumerate(unique_texts)}

    def qwen_of(occurrence_id: str) -> np.ndarray:
        return encoded[text_row[feature_texts[occurrence_id]]]

    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    anchor_ids: list[str] = []
    seen_ids: set[str] = set()
    skipped_missing = 0
    skipped_duplicate = 0
    for pair in anchors:
        sides = (
            pair["anchor"]["occurrence_id"],
            pair["candidate"]["occurrence_id"],
        )
        if sides[0] in missing_set or sides[1] in missing_set:
            skipped_missing += 1
            continue
        for left, right in (sides, sides[::-1]):
            row_id = f"{left}/{right}"
            if row_id in seen_ids:
                skipped_duplicate += 1
                continue
            seen_ids.add(row_id)
            x_rows.append(bge_matrix[bge_index[left]])
            y_rows.append(qwen_of(left))
            anchor_ids.append(row_id)

    mapping = fit_orthogonal_map(
        source=np.vstack(x_rows).astype(np.float64),
        target=np.vstack(y_rows).astype(np.float64),
        anchor_ids=anchor_ids,
        source_name=SOURCE_NAME,
        target_name=TARGET_NAME,
    )

    usable = [
        pair
        for pair in test_pairs
        if pair["anchor"]["occurrence_id"] not in missing_set
        and pair["candidate"]["occurrence_id"] not in missing_set
    ]
    bge_anchor = np.vstack(
        [bge_matrix[bge_index[pair["anchor"]["occurrence_id"]]] for pair in usable]
    )
    bge_candidate = np.vstack(
        [bge_matrix[bge_index[pair["candidate"]["occurrence_id"]]] for pair in usable]
    )
    qwen_anchor = np.vstack([qwen_of(pair["anchor"]["occurrence_id"]) for pair in usable])
    qwen_candidate = np.vstack([qwen_of(pair["candidate"]["occurrence_id"]) for pair in usable])
    labels = [int(pair["label"]) for pair in usable]

    projected_anchor = mapping.transform(bge_anchor)

    def rows_dot(left: np.ndarray, right: np.ndarray) -> list[float]:
        return (np.sum(left * right, axis=1) / np.maximum(
            np.linalg.norm(left, axis=1) * np.linalg.norm(right, axis=1), 1e-12
        )).tolist()

    scores = {
        "native_bge": rows_dot(bge_anchor, bge_candidate),
        "native_qwen3": rows_dot(qwen_anchor, qwen_candidate),
        "procrustes": rows_dot(projected_anchor, qwen_candidate),
    }
    auc = {name: rank_auc(values, labels) for name, values in scores.items()}
    positives = sum(labels)

    result: dict[str, Any] = {
        "protocol": (
            "orthogonal Procrustes BGE->Qwen3 fit on train P1 anchors; three "
            "similarity families AUC on the doc-disjoint test split; splits as "
            "stored in pairs.jsonl (original hash folds)"
        ),
        "anchors": {
            "n_train_p1_positives": n_train_pos,
            "n_unique_text_pairs": n_unique_text_pairs,
            "n_sampled_pairs": len(anchors),
            "n_fit_rows": len(anchor_ids),
            "n_rows_skipped_missing_vector": skipped_missing,
            "n_rows_skipped_duplicate_id": skipped_duplicate,
        },
        "anchor_hash": mapping.anchor_hash,
        "source_name": SOURCE_NAME,
        "target_name": TARGET_NAME,
        "test": {
            "n_pairs": len(usable),
            "n_pos": positives,
            "n_neg": len(usable) - positives,
            "auc_native_bge": (
                round(auc["native_bge"], 4) if auc["native_bge"] is not None else None
            ),
            "auc_native_qwen3": (
                round(auc["native_qwen3"], 4) if auc["native_qwen3"] is not None else None
            ),
            "auc_procrustes": (
                round(auc["procrustes"], 4) if auc["procrustes"] is not None else None
            ),
        },
        "n_occurrences_missing_vector": len(missing_set),
        "n_pairs_text_mismatch_vs_features": text_mismatches,
    }
    run = open_run(
        "eval_procrustes",
        {
            "pairs": str(args.pairs),
            "snapshot": str(args.snapshot_dir),
            "model_dir": str(args.model_dir),
            "anchor_limit": args.anchor_limit,
            "seed": args.seed,
            "qwen_encode": "embed_docs both sides",
        },
        RUNS_ROOT,
    )
    run.save_result(result)
    print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
