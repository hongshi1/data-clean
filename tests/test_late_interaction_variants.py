"""Tests for tools/eval_late_interaction_variants.py (B2/B4 variants).

Pure-function tests on synthetic token matrices only: top-k aggregation
mathematics (hand-computed cases, equivalence with idf_weighted_maxsim at
k=1, unnormalized inputs, edge cases), min-max normalization, and the clean
gate fusion composition. No model, dataset or GPU is loaded.
"""

import numpy as np
import pytest

from algorithms.context_linking.alignment.late_interaction import idf_weighted_maxsim
from tools.eval_ablation_matrix import GATE_ALPHA
from tools.eval_late_interaction_variants import (
    fuse_gate_scores,
    minmax_normalize,
    topk_weighted_maxsim,
)


def _pair(same_section: bool, shared_ids: list[str] | None = None) -> dict:
    return {
        "anchor": {"doc_id": "06", "occurrence_id": "a", "text": "甲"},
        "candidate": {"doc_id": "06", "occurrence_id": "b", "text": "乙"},
        "features": {
            "same_section": same_section,
            "shared_identifiers": shared_ids or [],
        },
        "label": 0,
        "split": "test",
    }


# ── top-k aggregation mathematics ─────────────────────────────────────────


def test_topk_k1_equals_idf_weighted_maxsim() -> None:
    rng = np.random.default_rng(5)
    query = rng.normal(size=(4, 8))
    doc = rng.normal(size=(6, 8))
    idf = np.asarray([2.0, 0.5, 1.0, 3.0])
    assert topk_weighted_maxsim(query, doc, idf, 1) == pytest.approx(
        idf_weighted_maxsim(query, doc, idf)
    )
    assert topk_weighted_maxsim(query, doc, None, 1) == pytest.approx(
        idf_weighted_maxsim(query, doc, None)
    )


def test_topk_hand_computed_single_query_token() -> None:
    query = [[1.0, 0.0]]
    doc = [[1.0, 0.0], [0.0, 1.0], [0.0, -1.0]]
    # Similarities of the query token: [1, 0, 0].
    idf = [3.0]
    assert topk_weighted_maxsim(query, doc, idf, 1) == pytest.approx(1.0)
    assert topk_weighted_maxsim(query, doc, idf, 2) == pytest.approx(0.5)
    assert topk_weighted_maxsim(query, doc, idf, 3) == pytest.approx(1.0 / 3.0)
    # k beyond the doc side -> mean over all doc tokens.
    assert topk_weighted_maxsim(query, doc, idf, 5) == pytest.approx(1.0 / 3.0)
    # idf=None behaves like weight 1 (score unchanged for a single token).
    assert topk_weighted_maxsim(query, doc, None, 2) == pytest.approx(0.5)


def test_topk_hand_computed_weighted_multiple_query_tokens() -> None:
    query = [[1.0, 0.0], [0.0, 1.0]]
    doc = [[0.6, 0.8]]  # already unit-norm
    # sims: query0 -> 0.6, query1 -> 0.8; top-1 per query token.
    idf = [2.0, 1.0]
    expected = (2.0 * 0.6 + 1.0 * 0.8) / 3.0
    assert topk_weighted_maxsim(query, doc, idf, 1) == pytest.approx(expected)
    # k=1 is the doc side's full width: same value for any k.
    assert topk_weighted_maxsim(query, doc, idf, 2) == pytest.approx(expected)


def test_topk_averages_top_k_not_any_k() -> None:
    query = [[1.0, 0.0]]
    doc = [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]]
    # Similarities [1, 0, 0, 0]: top-2 mean = 0.5, plain mean = 0.25.
    assert topk_weighted_maxsim(query, doc, [1.0], 2) == pytest.approx(0.5)
    assert topk_weighted_maxsim(query, doc, [1.0], 4) == pytest.approx(0.25)


def test_topk_normalizes_token_rows() -> None:
    rng = np.random.default_rng(9)
    query = rng.normal(size=(3, 5))
    doc = rng.normal(size=(4, 5))
    idf = [1.0, 2.0, 0.5]
    base = topk_weighted_maxsim(query, doc, idf, 2)
    scaled = topk_weighted_maxsim(query * 7.0, doc * 0.25, idf, 2)
    assert scaled == pytest.approx(base)


def test_topk_empty_side_returns_zero() -> None:
    query = [[1.0, 0.0]]
    assert topk_weighted_maxsim(query, [], [1.0], 2) == 0.0
    assert topk_weighted_maxsim([], query, None, 2) == 0.0


def test_topk_rejects_bad_arguments() -> None:
    query = [[1.0, 0.0]]
    doc = [[1.0, 0.0]]
    with pytest.raises(ValueError):
        topk_weighted_maxsim(query, doc, [1.0], 0)
    with pytest.raises(ValueError):
        topk_weighted_maxsim(query, doc, [1.0, 2.0], 1)  # idf length mismatch
    with pytest.raises(ValueError):
        topk_weighted_maxsim(query, [[1.0, 0.0, 0.0]], [1.0], 1)  # dim mismatch


# ── min-max normalization ─────────────────────────────────────────────────


def test_minmax_normalize_basic() -> None:
    values = minmax_normalize([1.0, 2.0, 3.0])
    assert values.tolist() == pytest.approx([0.0, 0.5, 1.0])


def test_minmax_normalize_order_preserved_and_bounded() -> None:
    rng = np.random.default_rng(13)
    scores = rng.uniform(-3.0, 3.0, size=100)
    values = minmax_normalize(scores)
    assert values.min() == 0.0 and values.max() == 1.0
    assert np.all(np.argsort(scores, kind="stable") == np.argsort(values, kind="stable"))


def test_minmax_normalize_constant_maps_to_midpoint() -> None:
    assert minmax_normalize([2.0, 2.0]).tolist() == pytest.approx([0.5, 0.5])
    with pytest.raises(ValueError):
        minmax_normalize([])


# ── B4 fusion composition (clean gate) ────────────────────────────────────


def test_fuse_gate_scores_composition() -> None:
    pairs = [_pair(same_section=True), _pair(same_section=False, shared_ids=["X"])]
    # Min-max normalize [0.2, 0.8] -> [0.0, 1.0].
    fused = fuse_gate_scores([0.2, 0.8], pairs, alpha=GATE_ALPHA)
    # same_doc=compatible (+0.15) + same_section=compatible (+0.15) -> gate 0.30;
    # identifier evidence must stay invisible (leak prevention).
    assert fused[0] == pytest.approx(GATE_ALPHA * 0.0 + (1 - GATE_ALPHA) * 0.30)
    assert fused[1] == pytest.approx(GATE_ALPHA * 1.0 + (1 - GATE_ALPHA) * 0.15)
    # shared_ids would add 0.75 to the gate if leaked; assert it does not.
    assert fused[1] == pytest.approx(fuse_gate_scores([0.2, 0.8], [_pair(same_section=False), pairs[1]], GATE_ALPHA)[1])


def test_fuse_gate_scores_rejects_misaligned_inputs() -> None:
    with pytest.raises(ValueError):
        fuse_gate_scores([0.1, 0.2], [_pair(same_section=True)], GATE_ALPHA)
