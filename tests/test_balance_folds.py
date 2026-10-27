"""Tests for tools/balance_folds.py (greedy + local-search fold balancing)."""

from pathlib import Path

import pytest

from tools.balance_folds import (
    EVAL_FOLDS,
    N_FOLDS,
    PAIRS_PATH,
    TRAIN_FOLDS,
    assign_folds,
    load_doc_stats,
)

SYNTHETIC = {
    "A": (900, 450),
    "B": (800, 500),
    "C": (700, 200),
    "D": (600, 300),
    "E": (500, 250),
    "F": (400, 240),
    "G": (350, 100),
    "H": (300, 150),
    "I": (250, 120),
    "J": (200, 90),
    "K": (150, 60),
    "L": (100, 40),
}

PATHOLOGICAL = {
    "BIG": (5500, 4600),
    "d1": (1200, 300),
    "d2": (1100, 250),
    "d3": (1000, 200),
    "d4": (900, 350),
    "d5": (800, 300),
    "d6": (700, 250),
    "d7": (600, 200),
}


def _fold_totals(stats, assignment):
    totals = {fold: (0, 0) for fold in range(N_FOLDS)}
    for doc, fold in assignment.items():
        pairs, positives = stats[doc]
        base_pairs, base_pos = totals[fold]
        totals[fold] = (base_pairs + pairs, base_pos + positives)
    return totals


def test_assign_folds_is_deterministic() -> None:
    assert assign_folds(SYNTHETIC) == assign_folds(dict(reversed(list(SYNTHETIC.items()))))
    assert assign_folds(SYNTHETIC) == assign_folds(SYNTHETIC)


def test_assign_folds_balances_pair_totals_and_eval_ratios() -> None:
    assignment = assign_folds(SYNTHETIC)
    assert set(assignment) == set(SYNTHETIC)
    assert set(assignment.values()) == set(range(N_FOLDS))
    totals = _fold_totals(SYNTHETIC, assignment)
    total_pairs = sum(pairs for pairs, _ in totals.values())
    total_pos = sum(pos for _, pos in totals.values())
    global_ratio = total_pos / total_pairs
    mean_pairs = total_pairs / N_FOLDS
    for fold, (pairs, positives) in totals.items():
        assert pairs > 0
        assert abs(pairs - mean_pairs) / mean_pairs <= 0.25
        if fold in EVAL_FOLDS:
            assert abs(positives / pairs - global_ratio) <= 0.10


def test_assign_folds_puts_positive_dominant_doc_in_train_fold() -> None:
    assignment = assign_folds(PATHOLOGICAL)
    total_pos = sum(pos for _, pos in PATHOLOGICAL.values())
    mean_pos = total_pos / N_FOLDS
    heavy = [doc for doc, (_, pos) in PATHOLOGICAL.items() if pos > mean_pos]
    assert heavy == ["BIG"]
    assert assignment["BIG"] in TRAIN_FOLDS
    # Every fold still non-empty after concentrating the heavy doc.
    assert set(assignment.values()) == set(range(N_FOLDS))


def test_assign_folds_rejects_degenerate_inputs() -> None:
    with pytest.raises(ValueError, match="at least"):
        assign_folds({"a": (10, 5), "b": (10, 5), "c": (10, 5)})
    with pytest.raises(ValueError, match="invalid stats"):
        assign_folds({"a": (10, 12), "b": (10, 5), "c": (10, 5), "d": (10, 5)})
    assert assign_folds({}) == {}


def test_real_pairs_dataset_yields_balanced_eval_folds() -> None:
    if not Path(PAIRS_PATH).exists():
        pytest.skip("training_pairs_v1 not present")
    stats = load_doc_stats(Path(PAIRS_PATH))
    if len(stats) < N_FOLDS:
        pytest.skip("dataset too small for fold balancing")
    assignment = assign_folds(stats)
    totals = _fold_totals(stats, assignment)
    total_pairs = sum(pairs for pairs, _ in totals.values())
    total_pos = sum(pos for _, pos in totals.values())
    global_ratio = total_pos / total_pairs
    mean_pairs = total_pairs / N_FOLDS
    for fold, (pairs, positives) in totals.items():
        assert pairs > 0
        assert abs(pairs - mean_pairs) / mean_pairs <= 0.10
        if fold in EVAL_FOLDS:
            assert abs(positives / pairs - global_ratio) <= 0.06
    heavy = [doc for doc, (_, pos) in stats.items() if pos > total_pos / N_FOLDS]
    for doc in heavy:
        assert assignment[doc] in TRAIN_FOLDS
