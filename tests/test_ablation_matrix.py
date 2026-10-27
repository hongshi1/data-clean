"""Tests for tools/eval_ablation_matrix.py (protocol #48 ablation matrix).

Pure-function tests only: structural-gate fusion rules, ECE/Brier arithmetic
and temperature scaling on synthetic scores. No real model, dataset or GPU is
loaded (train_projection/run_b1_late_interaction are intentionally untested
here; they are covered by the recorded runs).
"""

import math

import numpy as np
import pytest

from algorithms.context_linking.alignment.structural_gate import StructuralCompatibility
from tools.eval_ablation_matrix import (
    GATE_ALPHA,
    brier_score,
    build_rows,
    expected_calibration_error,
    fit_temperature,
    fuse_one,
    fused_scores,
    gate_features_from_pair,
    metrics_from_scores,
    nll_of_tau,
    temperature_probs,
)


def _pair(
    anchor_doc: str = "01",
    candidate_doc: str = "01",
    same_section: bool = False,
    identifiers: list[str] | None = None,
) -> dict:
    return {
        "anchor": {"doc_id": anchor_doc, "occurrence_id": "a", "text": "甲"},
        "candidate": {"doc_id": candidate_doc, "occurrence_id": "b", "text": "乙"},
        "features": {
            "same_section": same_section,
            "shared_identifiers": identifiers or [],
        },
        "label": 0,
        "split": "test",
    }


# ── gate fusion rules ────────────────────────────────────────────────────


def test_fuse_one_hard_veto_is_neg_inf() -> None:
    features = StructuralCompatibility(hard_veto=True)
    assert fuse_one(0.97, features) == float("-inf")


def test_fuse_one_arithmetic_matches_gate_weights() -> None:
    all_unknown = StructuralCompatibility()
    assert fuse_one(0.5, all_unknown) == pytest.approx(GATE_ALPHA * 0.5)
    gated = StructuralCompatibility(same_doc="compatible", identifier_match=True)
    # structural_score = 0.15 (same_doc) + 0.75 (identifier) = 0.90
    assert fuse_one(0.5, gated) == pytest.approx(GATE_ALPHA * 0.5 + (1 - GATE_ALPHA) * 0.90)
    incompatible = StructuralCompatibility(same_doc="incompatible")
    assert fuse_one(0.5, incompatible) == pytest.approx(GATE_ALPHA * 0.5 - (1 - GATE_ALPHA) * 0.15)


def test_a4_clean_excludes_identifier_evidence() -> None:
    pair_with_id = _pair(identifiers=["SYS-GN-01"])
    pair_without_id = _pair(identifiers=[])
    clean = gate_features_from_pair(pair_with_id, use_identifier=False)
    leak = gate_features_from_pair(pair_with_id, use_identifier=True)

    assert clean.identifier_match is False
    assert leak.identifier_match is True
    # The clean variant must not see the identifiers at all.
    assert fuse_one(0.4, clean) == pytest.approx(
        fuse_one(0.4, gate_features_from_pair(pair_without_id, use_identifier=False))
    )
    # The leak variant gains exactly the identifier weight share.
    assert fuse_one(0.4, leak) - fuse_one(0.4, clean) == pytest.approx(
        (1 - GATE_ALPHA) * 0.75
    )


def test_gate_feature_mapping_from_pair() -> None:
    features = gate_features_from_pair(_pair(anchor_doc="01", candidate_doc="01", same_section=True), True)
    assert features.same_doc == "compatible"
    assert features.same_section == "compatible"
    assert features.same_role == "unknown"
    assert features.same_scope == "unknown"

    cross_doc = gate_features_from_pair(_pair(anchor_doc="01", candidate_doc="02"), False)
    assert cross_doc.same_doc == "incompatible"
    # same_section False is evidence-absence ("unknown"), not incompatibility.
    cross_section = gate_features_from_pair(_pair(same_section=False), False)
    assert cross_section.same_section == "unknown"


def test_fused_scores_pairs_with_scores_in_order() -> None:
    pairs = [_pair(identifiers=["X"]), _pair()]
    clean = fused_scores([0.5, 0.2], pairs, use_identifier=False)
    leak = fused_scores([0.5, 0.2], pairs, use_identifier=True)
    # Without identifiers both pairs fuse identically per their own score.
    assert clean[0] == pytest.approx(GATE_ALPHA * 0.5 + (1 - GATE_ALPHA) * 0.15)
    assert clean[1] == pytest.approx(GATE_ALPHA * 0.2 + (1 - GATE_ALPHA) * 0.15)
    assert leak[0] - clean[0] == pytest.approx((1 - GATE_ALPHA) * 0.75)
    assert leak[1] == pytest.approx(clean[1])


def test_build_rows_keeps_pair_and_applies_fold_map() -> None:
    pairs = [
        {
            "anchor": {"doc_id": "06", "occurrence_id": "x"},
            "candidate": {"doc_id": "06", "occurrence_id": "y"},
            "features": {},
            "label": 1,
            "split": "train",
            "fold": 9,
        },
        {  # missing from index -> skipped
            "anchor": {"doc_id": "06", "occurrence_id": "nope"},
            "candidate": {"doc_id": "06", "occurrence_id": "y"},
            "features": {},
            "label": 0,
            "split": "train",
        },
    ]
    rows, missing = build_rows(pairs, {"x": 3, "y": 7}, {"06": 0})
    assert missing == 1
    assert len(rows) == 1
    assert rows[0]["anchor"] == 3 and rows[0]["candidate"] == 7
    assert rows[0]["label"] == 1
    assert rows[0]["split"] == "test"  # fold 0 -> test via the fold map
    assert rows[0]["pair"] is pairs[0]


# ── ECE / Brier ──────────────────────────────────────────────────────────


def test_ece_perfectly_calibrated_is_zero() -> None:
    # Each bin's mean label equals its confidence exactly.
    probs = [0.2] * 5 + [0.5] * 4 + [0.8] * 5
    labels = [1, 0, 0, 0, 0] + [1, 1, 0, 0] + [1, 1, 1, 1, 0]
    assert expected_calibration_error(probs, labels) == pytest.approx(0.0, abs=1e-12)


def test_ece_single_bin_extreme_case() -> None:
    # All mass in one bin: ECE = |confidence - accuracy| with full weight.
    assert expected_calibration_error([0.9] * 10, [1] * 10) == pytest.approx(0.1)
    assert expected_calibration_error([0.9] * 10, [0] * 10) == pytest.approx(0.9)


def test_ece_boundary_probabilities_clamp_to_outer_bins() -> None:
    assert expected_calibration_error([1.0], [0]) == pytest.approx(1.0)
    assert expected_calibration_error([1.0], [1]) == pytest.approx(0.0)
    assert expected_calibration_error([0.0], [0]) == pytest.approx(0.0)


def test_ece_empty_input_returns_zero() -> None:
    assert expected_calibration_error([], []) == 0.0


def test_ece_weighted_by_bin_size() -> None:
    # 9 samples in the 0.9 bin (perfectly calibrated), 1 sample in the 0.05
    # bin (fully wrong): ECE = 0.9*|0.9-1.0| + 0.1*|0.05-0.0|.
    probs = [0.9] * 9 + [0.05]
    labels = [1] * 9 + [0]
    assert expected_calibration_error(probs, labels) == pytest.approx(
        0.9 * abs(0.9 - 1.0) + 0.1 * abs(0.05 - 0.0)
    )


def test_brier_score() -> None:
    assert brier_score([0.5, 0.5], [0, 1]) == pytest.approx(0.25)
    assert brier_score([0.0, 1.0], [0, 1]) == pytest.approx(0.0)
    assert brier_score([1.0, 1.0], [0, 0]) == pytest.approx(1.0)
    assert brier_score([], []) == 0.0


# ── temperature scaling ──────────────────────────────────────────────────


def test_temperature_probs_monotonic_in_tau() -> None:
    taus = [0.05, 0.25, 1.0, 2.0, 5.0]
    for score in (0.7, 2.5):
        values = [float(temperature_probs([score], tau)[0]) for tau in taus]
        assert all(a > b for a, b in zip(values, values[1:]))
    for score in (-0.7, -2.5):
        values = [float(temperature_probs([score], tau)[0]) for tau in taus]
        assert all(a < b for a, b in zip(values, values[1:]))
    # Zero score stays at chance regardless of tau; huge tau -> 0.5.
    for tau in taus:
        assert temperature_probs([0.0], tau)[0] == pytest.approx(0.5)
    assert temperature_probs([4.0], 1e6)[0] == pytest.approx(0.5, abs=1e-5)


def test_temperature_probs_extreme_scores_do_not_overflow() -> None:
    values = temperature_probs([-1e6, 1e6], 0.05)
    assert math.isfinite(float(values[0])) and math.isfinite(float(values[1]))
    assert values[0] == pytest.approx(0.0)
    assert values[1] == pytest.approx(1.0)


def test_fit_temperature_softens_overconfident_scores() -> None:
    # Well-separated magnitudes with a couple of mistakes: sigma(s) at tau=1
    # is overconfident, so the NLL-optimal tau should soften (tau > 1) and
    # never do worse than the identity temperature.
    scores = [4.0, 4.0, 4.0, -4.0, -4.0, -4.0, 4.0, -4.0]
    labels = [1, 1, 1, 0, 0, 0, 0, 1]
    tau, nll = fit_temperature(scores, labels)
    assert 0.05 <= tau <= 5.0
    assert tau > 1.0
    assert nll <= nll_of_tau(scores, labels, 1.0) + 1e-12


def test_fit_temperature_identity_optimal_on_matched_data() -> None:
    # Ten samples at log-odds s=ln(9) (sigma(s)=0.9) with 9/10 positives: the
    # NLL-optimal confidence is 0.9, reached at tau = s/ln(9) = 1.
    s = math.log(9.0)
    scores = [s] * 10
    labels = [1] * 9 + [0]
    tau, nll = fit_temperature(scores, labels)
    assert 0.05 <= tau <= 5.0
    assert nll <= nll_of_tau(scores, labels, 1.0) + 1e-9
    assert abs(tau - 1.0) < 0.15


# ── metrics block ────────────────────────────────────────────────────────


def test_metrics_from_scores_perfect_separation() -> None:
    metrics = metrics_from_scores([0.9, 0.8, 0.3, 0.2], [1, 1, 0, 0], 0.5)
    assert metrics["auc"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["false_merge_rate"] == 0.0
    assert metrics["n_pairs"] == 4


def test_metrics_from_scores_tie_corrected_auc() -> None:
    # pos {0.5, 0.8}, neg {0.5, 0.2}: one tie contributes 0.5 -> AUC 0.875.
    metrics = metrics_from_scores([0.5, 0.8, 0.5, 0.2], [1, 1, 0, 0], 0.6)
    assert metrics["auc"] == 0.875
    # threshold 0.6: predicts positive only for 0.8 -> TP=1 FP=0 FN=1.
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 0.5
    assert metrics["false_merge_rate"] == 0.0


def test_metrics_from_scores_false_merge_rate() -> None:
    metrics = metrics_from_scores([0.9, 0.9, 0.9, 0.1], [1, 0, 0, 1], 0.5)
    # 2 false positives over 2 negatives -> fm 1.0; precision 1/3 (4-dp rounded).
    assert metrics["false_merge_rate"] == 1.0
    assert metrics["precision"] == 0.3333


def test_metrics_from_scores_neg_inf_scores_never_pass_threshold() -> None:
    metrics = metrics_from_scores([0.9, float("-inf")], [1, 0], 0.5)
    assert metrics["auc"] == 1.0
    assert metrics["false_merge_rate"] == 0.0


def test_np_array_inputs_accepted() -> None:
    probs = temperature_probs(np.asarray([0.2, -0.3, 1.0]), 0.5)
    assert isinstance(probs, np.ndarray)
    assert brier_score(probs.tolist(), [1, 0, 1]) == pytest.approx(
        np.mean((probs - np.asarray([1.0, 0.0, 1.0])) ** 2)
    )
