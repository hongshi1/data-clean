#!/usr/bin/env python3
"""Compute a balanced doc->fold assignment for training_pairs_v1.

The hash fold rule (``fold=int(sha1('doc:<doc_id>')[:12],16)%4``) put 6 of 16
docs (68% positives) into the dev fold and left test with 31% positives, so
dev and test conclusions pointed in opposite directions. This tool produces a
replacement assignment:

  start   : greedy round-robin — docs in descending pair count, each placed in
            the fold minimizing a normalized pair/positive cost (8 starts:
            two cost variants x four first-placement tie-breaks).
  improve : deterministic local search (single-doc relocation with a
            no-empty-fold guard, plus two-doc swaps) minimizing
            ``sum_folds (pair-total deviation)^2
              + sum_{eval folds} (positive-ratio deviation)^2``.
            Ratio balance is only demanded of the eval folds because the two
            train folds are pooled into one train split downstream, while dev
            and test are the individually reported decision folds.

Why plain greedy is not enough: doc 02 alone holds 4623 of 13489 positives
(34%), so every fold containing it overshoots the global positive ratio; the
local search concentrates that skew into a train fold and balances the rest.

Output: a per-fold table plus the suggested ``--fold-map`` argument string
for ``tools/train_shared_projection.py`` (split mapping unchanged:
0=test, 1=dev, 2/3=train). The assignment is archived via runs protocol and
is a pure deterministic function of the per-doc pair statistics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

N_FOLDS = 4
FOLD_TO_SPLIT = {0: "test", 1: "dev", 2: "train", 3: "train"}
EVAL_FOLDS = (0, 1)
TRAIN_FOLDS = (2, 3)
_COSTS = ("pairs_positives", "positives_negatives")


def _validate(doc_stats: dict[str, tuple[int, int]]) -> None:
    if N_FOLDS < 1:
        raise ValueError("N_FOLDS must be a positive integer")
    for doc, stats in doc_stats.items():
        pairs, positives = stats
        if pairs < 1 or positives < 0 or positives > pairs:
            raise ValueError(f"invalid stats for doc {doc!r}: {stats!r}")


def objective(doc_stats: dict[str, tuple[int, int]], assignment: dict[str, int]) -> float:
    """Pair-total deviation over all folds + ratio deviation over eval folds."""

    totals = [(0, 0)] * N_FOLDS
    for doc, fold in assignment.items():
        pairs, positives = doc_stats[doc]
        base_pairs, base_pos = totals[fold]
        totals[fold] = (base_pairs + pairs, base_pos + positives)
    total_pairs = sum(pairs for pairs, _ in totals)
    total_pos = sum(pos for _, pos in totals)
    mean_pairs = max(total_pairs / N_FOLDS, 1e-9)
    global_ratio = total_pos / max(total_pairs, 1)
    score = 0.0
    for fold in range(N_FOLDS):
        pairs, positives = totals[fold]
        score += ((pairs - mean_pairs) / mean_pairs) ** 2
        if fold in EVAL_FOLDS:
            ratio = positives / max(pairs, 1)
            score += ((ratio - global_ratio) / max(global_ratio, 1e-9)) ** 2
    return score


def _greedy_start(
    doc_stats: dict[str, tuple[int, int]], cost_kind: str, first_fold: int
) -> dict[str, int]:
    """Greedy round-robin: docs desc by pair count into the cheapest fold."""

    if first_fold not in range(N_FOLDS):
        raise ValueError(f"first_fold must be in 0..{N_FOLDS - 1}")
    total_pairs = sum(pairs for pairs, _ in doc_stats.values())
    total_pos = sum(pos for _, pos in doc_stats.values())
    mean_pairs = max(total_pairs / N_FOLDS, 1e-9)
    mean_pos = max(total_pos / N_FOLDS, 1e-9)
    mean_neg = max((total_pairs - total_pos) / N_FOLDS, 1e-9)
    order = sorted(doc_stats, key=lambda doc: (-doc_stats[doc][0], doc))
    fold_pairs = [0] * N_FOLDS
    fold_pos = [0] * N_FOLDS
    assignment: dict[str, int] = {}
    for position, doc in enumerate(order):
        pairs, positives = doc_stats[doc]
        # First doc: all folds tie, so consider first_fold before the others.
        fold_order: list[int] | range = (
            [first_fold] + [f for f in range(N_FOLDS) if f != first_fold]
            if position == 0
            else range(N_FOLDS)
        )
        best_fold = first_fold if position == 0 else 0
        best_cost: float | None = None
        for fold in fold_order:
            if cost_kind == "pairs_positives":
                cost = (fold_pairs[fold] + pairs) / mean_pairs + (
                    fold_pos[fold] + positives
                ) / mean_pos
            elif cost_kind == "positives_negatives":
                negs = fold_pairs[fold] - fold_pos[fold] + pairs - positives
                cost = (fold_pos[fold] + positives) / mean_pos + negs / mean_neg
            else:
                raise ValueError(f"unknown cost kind: {cost_kind!r}")
            if best_cost is None or cost < best_cost - 1e-12:
                best_fold = fold
                best_cost = cost
        assignment[doc] = best_fold
        fold_pairs[best_fold] += pairs
        fold_pos[best_fold] += positives
    return assignment


def _local_search(
    doc_stats: dict[str, tuple[int, int]], assignment: dict[str, int]
) -> dict[str, int]:
    """Best-improvement relocation + swap search; fully deterministic."""

    current = dict(assignment)
    current_obj = objective(doc_stats, current)
    docs = sorted(doc_stats)
    while True:
        best_key: tuple[float, tuple[tuple[str, int], ...]] | None = None
        best_assignment: dict[str, int] | None = None
        for doc in docs:
            for fold in range(N_FOLDS):
                if fold == current[doc]:
                    continue
                candidate = dict(current)
                candidate[doc] = fold
                counts = [0] * N_FOLDS
                for other in docs:
                    counts[candidate[other]] += 1
                if min(counts) == 0:
                    continue
                cand_obj = objective(doc_stats, candidate)
                key = (cand_obj, tuple(sorted(candidate.items())))
                if best_key is None or key < best_key:
                    best_key = key
                    best_assignment = candidate
        for index, doc_a in enumerate(docs):
            for doc_b in docs[index + 1 :]:
                if current[doc_a] == current[doc_b]:
                    continue
                candidate = dict(current)
                candidate[doc_a], candidate[doc_b] = current[doc_b], current[doc_a]
                cand_obj = objective(doc_stats, candidate)
                key = (cand_obj, tuple(sorted(candidate.items())))
                if best_key is None or key < best_key:
                    best_key = key
                    best_assignment = candidate
        if best_key is None or best_key[0] >= current_obj - 1e-12:
            return current
        current = best_assignment if best_assignment is not None else current
        current_obj = best_key[0]


def assign_folds(doc_stats: dict[str, tuple[int, int]]) -> dict[str, int]:
    """Deterministic balanced doc->fold assignment ({doc: fold}).

    Multi-start greedy (desc pair count, 8 starts) followed by deterministic
    local search; the best assignment under :func:`objective` wins, with
    ties broken by lexicographic assignment order. Raises ValueError on
    invalid stats and when fewer docs than folds make non-empty folds
    impossible.
    """

    _validate(doc_stats)
    if not doc_stats:
        return {}
    if len(doc_stats) < N_FOLDS:
        raise ValueError(f"need at least {N_FOLDS} docs, got {len(doc_stats)}")
    best_key: tuple[float, tuple[tuple[str, int], ...]] | None = None
    best: dict[str, int] = {}
    for cost_kind in _COSTS:
        for first_fold in range(N_FOLDS):
            start = _greedy_start(doc_stats, cost_kind, first_fold)
            improved = _local_search(doc_stats, start)
            key = (objective(doc_stats, improved), tuple(sorted(improved.items())))
            if best_key is None or key < best_key:
                best_key = key
                best = improved
    empty = [fold for fold in range(N_FOLDS) if not any(f == fold for f in best.values())]
    if empty:
        raise RuntimeError(f"local search left folds empty: {empty}")
    return best


def load_doc_stats(pairs_path: Path) -> dict[str, tuple[int, int]]:
    """Aggregate per-doc (n_pairs, n_positives) from pairs.jsonl."""

    stats: dict[str, tuple[int, int]] = {}
    with pairs_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            pair = json.loads(line)
            doc_id = str(pair["anchor"]["doc_id"])
            pairs, positives = stats.get(doc_id, (0, 0))
            stats[doc_id] = (pairs + 1, positives + int(pair["label"]))
    return stats


def main() -> None:
    doc_stats = load_doc_stats(PAIRS_PATH)
    if not doc_stats:
        raise SystemExit(f"no pairs found in {PAIRS_PATH}")
    assignment = assign_folds(doc_stats)

    total_pairs = sum(pairs for pairs, _ in doc_stats.values())
    total_pos = sum(pos for _, pos in doc_stats.values())
    per_fold: dict[int, dict[str, Any]] = {}
    for fold in range(N_FOLDS):
        docs = sorted(doc for doc, value in assignment.items() if value == fold)
        fold_pairs = sum(doc_stats[doc][0] for doc in docs)
        fold_pos = sum(doc_stats[doc][1] for doc in docs)
        per_fold[fold] = {
            "split": FOLD_TO_SPLIT[fold],
            "docs": docs,
            "n_pairs": fold_pairs,
            "n_pos": fold_pos,
            "pos_ratio": round(fold_pos / max(fold_pairs, 1), 4),
        }

    fold_map_arg = ",".join(f"{doc}:{assignment[doc]}" for doc in sorted(assignment))

    print(f"docs: {len(doc_stats)}  pairs: {total_pairs}  positives: {total_pos} "
          f"(ratio {total_pos / max(total_pairs, 1):.4f})")
    for fold in range(N_FOLDS):
        info = per_fold[fold]
        print(f"fold {fold} ({info['split']}): docs={','.join(info['docs'])} "
              f"pairs={info['n_pairs']} pos={info['n_pos']} "
              f"pos_ratio={info['pos_ratio']}")
    print("\nsuggested --fold-map argument:")
    print(fold_map_arg)

    run = open_run("balance_folds", {"pairs": str(PAIRS_PATH), "n_folds": N_FOLDS}, RUNS_ROOT)
    run.save_result(
        {
            "doc_stats": {doc: list(stats) for doc, stats in sorted(doc_stats.items())},
            "assignment": {doc: assignment[doc] for doc in sorted(assignment)},
            "per_fold": {str(fold): per_fold[fold] for fold in range(N_FOLDS)},
            "objective": round(objective(doc_stats, assignment), 6),
            "fold_map_arg": fold_map_arg,
            "fold_rule": (
                "greedy desc-pair round-robin (8 starts) + local search "
                "(relocate/swap); pair totals balanced on all folds, positive "
                "ratio balanced on eval folds only (train folds are pooled); "
                "0=test 1=dev 2,3=train"
            ),
        }
    )
    print(f"\nrun saved: {run.path}")


if __name__ == "__main__":
    main()
