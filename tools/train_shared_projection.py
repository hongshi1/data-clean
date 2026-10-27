#!/usr/bin/env python3
"""Train a shared projection head over frozen BGE snapshot vectors.

Frozen inputs: ``feature_snapshot_v1`` vectors + ``training_pairs_v1`` silver
pairs (P1 explicit-identifier positives, deterministic sibling negatives).
Trains with InfoNCE plus an identity boundary loss; reports AUC, F1 and
false-merge rate on dev/test folds. Results are saved through runs protocol.

This is silver weak supervision; it never writes gold labels.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = BASE / "data/gjb_438c/feature_snapshot_v1"
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402


def load_snapshot(path: Path) -> tuple[dict[str, int], Any, list[str]]:
    import numpy as np

    with np.load(path, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(value) for value in data["ids"].tolist()]
    index = {occurrence_id: position for position, occurrence_id in enumerate(ids)}
    return index, matrix, ids


def load_pairs(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# Mirrors tools/build_training_pairs.py SPLIT_MAP: fold -> split role.
FOLD_TO_SPLIT = {0: "test", 1: "dev", 2: "train", 3: "train"}


def parse_fold_map(spec: str) -> dict[str, int]:
    """Parse a "doc:fold,doc:fold,..." override string into {doc: fold}.

    Malformed entries, empty specs and fold indices outside
    ``FOLD_TO_SPLIT`` abort with an explicit error (never silently ignored).
    """

    mapping: dict[str, int] = {}
    for chunk in spec.split(","):
        entry = chunk.strip()
        if not entry:
            continue
        doc, sep, fold_text = entry.partition(":")
        doc = doc.strip()
        fold_text = fold_text.strip()
        if not sep or not doc or not fold_text:
            raise SystemExit(f"invalid --fold-map entry (want doc:fold): {entry!r}")
        try:
            fold = int(fold_text)
        except ValueError:
            raise SystemExit(f"non-integer fold in --fold-map entry: {entry!r}") from None
        if fold not in FOLD_TO_SPLIT:
            raise SystemExit(
                f"fold {fold!r} outside {sorted(FOLD_TO_SPLIT)} in entry: {entry!r}"
            )
        if doc in mapping:
            raise SystemExit(f"duplicate doc in --fold-map: {doc!r}")
        mapping[doc] = fold
    if not mapping:
        raise SystemExit("--fold-map must contain at least one doc:fold entry")
    return mapping


def pair_indices(
    pairs: list[dict[str, Any]],
    index: dict[str, int],
    fold_map: dict[str, int] | None = None,
) -> list[tuple[int, int, int, str]]:
    """Map pairs to matrix rows; optionally override the hash fold per doc.

    ``fold_map`` (from ``--fold-map``) remaps a pair's fold by its anchor doc
    and re-derives the split via ``FOLD_TO_SPLIT`` (0=test, 1=dev, 2/3=train);
    docs absent from the map keep their stored hash fold. Without ``fold_map``
    behavior is identical to reading the stored ``split`` field directly.
    """

    rows: list[tuple[int, int, int, str]] = []
    missing = 0
    for pair in pairs:
        anchor_id = pair["anchor"]["occurrence_id"]
        candidate_id = pair["candidate"]["occurrence_id"]
        if anchor_id not in index or candidate_id not in index:
            missing += 1
            continue
        split = str(pair.get("split", "train"))
        if fold_map is not None:
            doc_id = str(pair["anchor"]["doc_id"])
            fold = fold_map.get(doc_id, pair.get("fold"))
            if fold is None:
                raise SystemExit(
                    f"pair {pair.get('pair_id', '?')} has no stored fold and "
                    f"doc {doc_id!r} is missing from --fold-map"
                )
            split = FOLD_TO_SPLIT[int(fold)]
        rows.append(
            (
                index[anchor_id],
                index[candidate_id],
                int(pair["label"]),
                split,
            )
        )
    return rows


def build_model(torch: Any, dim: int, shared_dim: int, seed: int) -> Any:
    torch.manual_seed(seed)
    return torch.nn.Sequential(
        torch.nn.Linear(dim, shared_dim),
        torch.nn.LayerNorm(shared_dim),
        torch.nn.GELU(),
        torch.nn.Linear(shared_dim, shared_dim),
    )


def evaluate(
    torch: Any,
    model: Any,
    matrix: Any,
    rows: list[tuple[int, int, int, str]],
    threshold: float,
    batch: int = 4096,
) -> dict[str, Any]:
    model.eval()
    with torch.no_grad():
        projected = []
        for start in range(0, matrix.shape[0], batch):
            chunk = torch.from_numpy(matrix[start : start + batch])
            projected.append(model(chunk))
        projected = torch.cat(projected)
        projected = torch.nn.functional.normalize(projected, dim=-1).cpu().numpy()
    scores = []
    labels = []
    for anchor, candidate, label, _ in rows:
        vector_a = projected[anchor]
        vector_b = projected[candidate]
        scores.append(float(vector_a @ vector_b))
        labels.append(label)
    positives = sum(labels)
    negatives = len(labels) - positives
    # Rank-based AUC: P(score_pos > score_neg) with tie correction.
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
    rank_sum_pos = sum(ranks[position] for position, label in enumerate(labels) if label == 1)
    auc = (rank_sum_pos - positives * (positives + 1) / 2.0) / max(positives * negatives, 1)
    predicted_positive = [1 if score >= threshold else 0 for score in scores]
    true_positive = sum(
        1 for predicted, label in zip(predicted_positive, labels) if predicted == 1 and label == 1
    )
    false_positive = sum(
        1 for predicted, label in zip(predicted_positive, labels) if predicted == 1 and label == 0
    )
    false_negative = sum(
        1 for predicted, label in zip(predicted_positive, labels) if predicted == 0 and label == 1
    )
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    false_merge = false_positive / max(negatives, 1)
    return {
        "n_pairs": len(labels),
        "auc": round(auc, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_merge_rate": round(false_merge, 4),
        "threshold": threshold,
    }


def sweep_threshold(scores: list[float], labels: list[int]) -> float:
    """Pick the dev negative-score 95th percentile.

    False merges are more dangerous than missed recalls, so the threshold
    targets <=5% negative leakage instead of F1 maximization (F1 degenerates
    under the severe fold-level label imbalance of the 4-fold doc split).
    """

    negatives = [score for score, label in zip(scores, labels) if label == 0]
    if not negatives:
        return 0.0
    negatives.sort()
    position = min(int(math.ceil(0.95 * len(negatives))) - 1, len(negatives) - 1)
    return round(negatives[position], 4)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--shared-dim", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--boundary-margin", type=float, default=0.10)
    parser.add_argument("--boundary-weight", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, default=None, help="Cap training pairs (smoke)")
    parser.add_argument("--dev-only", action="store_true", help="Skip test evaluation (smoke)")
    parser.add_argument(
        "--fold-map",
        type=str,
        default=None,
        help=(
            'doc->fold override "doc1:fold,doc2:fold,..." (e.g. "01:0,02:0"); '
            "re-derives each pair's split from the fold "
            "(0=test, 1=dev, 2/3=train). Default: keep stored hash-fold splits."
        ),
    )
    parser.add_argument("--snapshot-dir", type=Path, default=SNAPSHOT_DIR)
    parser.add_argument("--pairs", type=Path, default=PAIRS_PATH)
    args = parser.parse_args()

    import numpy as np
    import torch

    fold_map = parse_fold_map(args.fold_map) if args.fold_map else None
    index, matrix, ids = load_snapshot(args.snapshot_dir / "vectors.npz")
    pairs = load_pairs(args.pairs)
    rows = pair_indices(pairs, index, fold_map=fold_map)
    train_rows = [row for row in rows if row[3] == "train"]
    dev_rows = [row for row in rows if row[3] == "dev"]
    test_rows = [row for row in rows if row[3] == "test"]
    if args.limit:
        train_rows = train_rows[: args.limit]
        dev_rows = dev_rows[: max(args.limit // 4, 1)]
        test_rows = test_rows[: max(args.limit // 4, 1)]
    if not train_rows or not dev_rows:
        raise SystemExit("no usable train/dev pairs; check snapshot and pair inputs")

    config = {
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "shared_dim": args.shared_dim,
        "lr": args.lr,
        "temperature": args.temperature,
        "boundary_margin": args.boundary_margin,
        "boundary_weight": args.boundary_weight,
        "seed": args.seed,
        "limit": args.limit,
        "snapshot": str(args.snapshot_dir),
        "pairs": str(args.pairs),
        "n_train": len(train_rows),
        "n_dev": len(dev_rows),
        "n_test": len(test_rows),
        "fold_map": fold_map,
        "loss": "infonce_plus_identity_boundary",
        "supervision": "silver_p1_identifier_plus_sibling_negatives",
    }
    run = open_run("train_shared_projection", config, RUNS_ROOT)

    model = build_model(torch, matrix.shape[1], args.shared_dim, args.seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    matrix_tensor = torch.from_numpy(matrix)

    def project(indices: Any) -> Any:
        vectors = matrix_tensor[indices]
        output = model(vectors)
        return torch.nn.functional.normalize(output, dim=-1)

    train_positive = [row for row in train_rows if row[2] == 1]
    train_negative = [row for row in train_rows if row[2] == 0]
    rng = np.random.default_rng(args.seed)
    history: list[dict[str, float]] = []
    for epoch in range(args.epochs):
        model.train()
        order = rng.permutation(len(train_positive))
        total_infonce = 0.0
        total_boundary = 0.0
        batches = 0
        for start in range(0, len(order), args.batch_size):
            batch_rows = [train_positive[position] for position in order[start : start + args.batch_size]]
            anchors = torch.tensor([row[0] for row in batch_rows], dtype=torch.long)
            positives = torch.tensor([row[1] for row in batch_rows], dtype=torch.long)
            anchor_vectors = project(anchors)
            positive_vectors = project(positives)
            logits = anchor_vectors @ positive_vectors.T / args.temperature
            targets = torch.arange(len(batch_rows))
            loss_infonce = torch.nn.functional.cross_entropy(logits, targets)
            # Identity boundary loss on deterministic sibling negatives.
            if train_negative:
                sample_size = min(len(batch_rows), len(train_negative))
                positions = rng.integers(0, len(train_negative), size=sample_size)
                negative_rows = [train_negative[position] for position in positions]
                negative_anchors = torch.tensor(
                    [row[0] for row in negative_rows], dtype=torch.long
                )
                negative_candidates = torch.tensor(
                    [row[1] for row in negative_rows], dtype=torch.long
                )
                negative_scores = (
                    project(negative_anchors) * project(negative_candidates)
                ).sum(dim=-1)
                # Margin form: penalize negative-pair similarity above margin.
                loss_boundary = torch.clamp(
                    negative_scores + args.boundary_margin, min=0.0
                ).mean()
            else:
                loss_boundary = torch.tensor(0.0)
            loss = loss_infonce + args.boundary_weight * loss_boundary
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_infonce += float(loss_infonce.detach())
            total_boundary += float(loss_boundary.detach())
            batches += 1
        history.append(
            {
                "epoch": epoch + 1,
                "infonce": round(total_infonce / max(batches, 1), 4),
                "boundary": round(total_boundary / max(batches, 1), 4),
            }
        )

    # Threshold sweep uses dev folds only.
    model.eval()
    with torch.no_grad():
        projected = torch.cat(
            [model(matrix_tensor[start : start + 4096]) for start in range(0, matrix.shape[0], 4096)]
        )
        projected = torch.nn.functional.normalize(projected, dim=-1).cpu().numpy()
    dev_scores = [float(projected[a] @ projected[c]) for a, c, _, _ in dev_rows]
    dev_labels = [label for _, _, label, _ in dev_rows]
    threshold = sweep_threshold(dev_scores, dev_labels)

    results: dict[str, Any] = {
        "dev": evaluate(torch, model, matrix, dev_rows, threshold),
        "history": history,
        "threshold_from_dev": threshold,
        "config": config,
    }
    if not args.dev_only:
        results["test"] = evaluate(torch, model, matrix, test_rows, threshold)
    # Native-only control on the same rows, no projection, no training.
    native_dev_scores = [float(matrix[a] @ matrix[c]) for a, c, _, _ in dev_rows]
    native_threshold = sweep_threshold(native_dev_scores, dev_labels)
    results["native_control_dev"] = {
        "n_pairs": len(dev_rows),
        "auc": 0.0,
        "threshold": native_threshold,
    }
    # Native AUC via the same rank computation.
    def auc_of(scores: list[float], labels: list[int]) -> float:
        positives = sum(labels)
        negatives = len(labels) - positives
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
        return (rank_sum_pos - positives * (positives + 1) / 2.0) / max(
            positives * negatives, 1
        )

    results["native_control_dev"]["auc"] = round(
        auc_of(native_dev_scores, dev_labels), 4
    )
    if not args.dev_only:
        native_test_scores = [float(matrix[a] @ matrix[c]) for a, c, _, _ in test_rows]
        native_test_labels = [label for _, _, label, _ in test_rows]
        native_test_predictions = [
            1 if score >= native_threshold else 0 for score in native_test_scores
        ]
        negatives_test = sum(1 for label in native_test_labels if label == 0)
        false_positive = sum(
            1
            for predicted, label in zip(native_test_predictions, native_test_labels)
            if predicted == 1 and label == 0
        )
        results["native_control_test"] = {
            "n_pairs": len(test_rows),
            "auc": round(auc_of(native_test_scores, native_test_labels), 4),
            "false_merge_rate": round(false_positive / max(negatives_test, 1), 4),
            "threshold": native_threshold,
        }
    run.save_result(results)
    print(
        json.dumps(
            {
                "dev": results["dev"],
                "test": results.get("test"),
                "native_dev_auc": results["native_control_dev"]["auc"],
                "native_test_auc": results.get("native_control_test", {}).get("auc"),
                "run_dir": str(run.path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
