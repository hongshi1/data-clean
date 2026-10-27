"""Tests for tools/eval_conditional_calibration.py (D2/D3/E50 calibration).

Pure-function tests on synthetic data only: PAVA isotonic regression,
bucketed ECE decomposition (including the triangle-inequality direction),
split-conformal quantiles and coverage, selective prediction / AURC, and the
conformal x contract dual-axis matrix. No model, dataset or GPU is loaded.
"""

import math

import numpy as np
import pytest

from tools.eval_conditional_calibration import (
    aurc,
    aurc_oracle,
    bucket_key,
    bucketed_ece,
    conformal_covered_flags,
    conformal_quantile,
    dual_axis_matrix,
    log_loss,
    pava_fit,
    pava_predict,
    selective_prediction_rows,
    weighted_bucket_ece,
)
from tools.eval_ablation_matrix import expected_calibration_error


# ── PAVA isotonic regression ──────────────────────────────────────────────


def test_pava_pools_adjacent_violators() -> None:
    edges, values = pava_fit([1.0, 2.0, 3.0], [0, 1, 0])
    assert edges.tolist() == [1.0, 3.0]
    assert values.tolist() == pytest.approx([0.0, 0.5])
    predicted = pava_predict([0.5, 1.0, 2.0, 3.0, 4.0], edges, values)
    assert predicted.tolist() == pytest.approx([0.0, 0.0, 0.5, 0.5, 0.5])


def test_pava_aggregates_tied_scores_before_pooling() -> None:
    edges, values = pava_fit([1.0, 1.0, 2.0], [0, 1, 1])
    # The two tied scores share one block with mean 0.5; already monotone.
    assert edges.tolist() == [1.0, 2.0]
    assert values.tolist() == pytest.approx([0.5, 1.0])
    predicted = pava_predict([1.0, 2.0], edges, values)
    assert predicted.tolist() == pytest.approx([0.5, 1.0])


def test_pava_perfectly_isotonic_input_unchanged() -> None:
    edges, values = pava_fit([1.0, 2.0, 3.0, 4.0], [0, 0, 1, 1])
    assert values.tolist() == pytest.approx([0.0, 0.0, 1.0, 1.0])
    predicted = pava_predict([1.0, 2.0, 3.0, 4.0], edges, values)
    assert predicted.tolist() == pytest.approx([0.0, 0.0, 1.0, 1.0])


def test_pava_output_is_monotone_on_random_data() -> None:
    rng = np.random.default_rng(7)
    scores = rng.uniform(0.0, 1.0, size=400)
    labels = (rng.uniform(size=400) < scores).astype(int)
    edges, values = pava_fit(scores, labels)
    assert np.all(np.diff(values) >= -1e-12)
    order = np.argsort(scores)
    predicted = pava_predict(scores[order], edges, values)
    assert np.all(np.diff(predicted) >= -1e-12)


def test_pava_fit_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        pava_fit([], [])
    with pytest.raises(ValueError):
        pava_fit([1.0, 2.0], [0])


# ── bucketed ECE decomposition ────────────────────────────────────────────


def test_bucketed_ece_stats_and_zero_for_calibrated_buckets() -> None:
    probs = [0.2] * 5 + [0.8] * 5
    labels = [1, 0, 0, 0, 0] + [1, 1, 1, 1, 0]
    buckets = ["a"] * 5 + ["b"] * 5
    stats = bucketed_ece(probs, labels, buckets)
    assert stats["a"]["n"] == 5 and stats["a"]["n_pos"] == 1
    assert stats["b"]["n"] == 5 and stats["b"]["n_pos"] == 4
    assert stats["a"]["ece"] == pytest.approx(0.0, abs=1e-12)
    assert stats["b"]["ece"] == pytest.approx(0.0, abs=1e-12)
    assert weighted_bucket_ece(probs, labels, buckets) == pytest.approx(0.0, abs=1e-12)


def test_weighted_bucket_ece_weights_by_bucket_size() -> None:
    # Bucket a: p=0.4, all-negative -> ECE 0.4 (n=10).
    # Bucket b: p=0.8, all-positive -> ECE 0.2 (n=30).
    probs = [0.4] * 10 + [0.8] * 30
    labels = [0] * 10 + [1] * 30
    buckets = ["a"] * 10 + ["b"] * 30
    expected = (10 / 40) * 0.4 + (30 / 40) * 0.2
    assert weighted_bucket_ece(probs, labels, buckets) == pytest.approx(expected)


def test_global_ece_never_exceeds_weighted_bucket_sum() -> None:
    # Opposite-signed within-bucket errors cancel in shared global bins:
    # the triangle inequality direction behind the mixture signature.
    probs = [0.6] * 10 + [0.6] * 10
    labels = [1] * 9 + [0] + [1] * 3 + [0] * 7  # bucket rates 0.9 / 0.3
    buckets = ["a"] * 10 + ["b"] * 10
    weighted = weighted_bucket_ece(probs, labels, buckets)
    overall = expected_calibration_error(np.asarray(probs), np.asarray(labels))
    assert overall < weighted
    assert weighted == pytest.approx(0.3)
    assert overall == pytest.approx(0.0, abs=1e-12)


# ── split-conformal quantiles ─────────────────────────────────────────────


def test_conformal_quantile_is_finite_sample_order_statistic() -> None:
    calibration = [i / 100 for i in range(100)]  # 0.00 .. 0.99
    # rank = ceil(101 * 0.9) = 91 -> 91st smallest = 0.90
    assert conformal_quantile(calibration, 0.1) == pytest.approx(0.90)
    # rank = ceil(101 * 0.5) = 51 -> 51st smallest = 0.50
    assert conformal_quantile(calibration, 0.5) == pytest.approx(0.50)


def test_conformal_quantile_infinite_when_correction_exceeds_sample() -> None:
    # rank = ceil(6 * 0.9) = 6 > n=5 -> always-accept.
    assert conformal_quantile([0.1, 0.2, 0.3, 0.4, 0.5], 0.1) == float("inf")


def test_conformal_quantile_rejects_empty_and_bad_alpha() -> None:
    with pytest.raises(ValueError):
        conformal_quantile([], 0.1)
    with pytest.raises(ValueError):
        conformal_quantile([0.5], 0.0)
    with pytest.raises(ValueError):
        conformal_quantile([0.5], 1.0)


def test_conformal_coverage_guarantee_on_exchangeable_grid() -> None:
    calibration = [i / 100 for i in range(100)]
    quantile = conformal_quantile(calibration, 0.1)
    test_scores = [i / 1000 for i in range(1000)]
    covered = sum(1 for score in test_scores if score <= quantile)
    assert covered / len(test_scores) >= 0.9


def test_conformal_covered_flags_abstains_uncalibrated_buckets() -> None:
    flags = conformal_covered_flags(
        [0.9, 0.5, 0.2], ["a", "a", "b"], {"a": 0.1}
    )
    assert flags == [True, False, False]


def test_conformal_covered_flags_boundary_is_inclusive() -> None:
    # 1 - 0.75 == 0.25 exactly in binary; equality still counts as covered.
    flags = conformal_covered_flags([0.75, 0.74], ["a", "a"], {"a": 0.25})
    assert flags == [True, False]


# ── D3: selective prediction / AURC ───────────────────────────────────────


def test_selective_prediction_rows_perfect_model() -> None:
    rows = selective_prediction_rows(
        [0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0], [0.5, 0.85, 0.95]
    )
    assert [row["coverage"] for row in rows] == [1.0, 0.5, 0.0]
    assert rows[0]["selective_risk"] == 0.0
    assert rows[1]["selective_risk"] == 0.0
    assert rows[2]["selective_risk"] is None
    assert rows[2]["n_covered"] == 0


def test_selective_prediction_rows_hand_case() -> None:
    rows = selective_prediction_rows([0.9, 0.6, 0.4], [1, 0, 0], [0.55, 0.65])
    # pred = p >= 0.5 -> [1, 1, 0]; errors = [0, 1, 0].
    assert rows[0]["selective_risk"] == pytest.approx(1 / 3, abs=1e-4)
    assert rows[1]["selective_risk"] == 0.0


def test_selective_prediction_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        selective_prediction_rows([], [], [0.5])


def test_aurc_perfect_model_is_zero() -> None:
    assert aurc([0.9, 0.8, 0.2, 0.1], [1, 1, 0, 0]) == 0.0


def test_aurc_fully_miscalibrated_is_one() -> None:
    assert aurc([0.9, 0.9, 0.9, 0.9], [0, 0, 0, 0]) == 1.0


def test_aurc_hand_computed_value() -> None:
    # pred=[1,1,1,0], errors=[0,0,1,0], conf=[.9,.8,.6,.6] (stable ties).
    # cumulative risks: [0, 0, 1/3, 1/4] -> mean 7/48.
    assert aurc([0.9, 0.8, 0.6, 0.4], [1, 1, 0, 0]) == pytest.approx(7 / 48)


def test_aurc_oracle_and_bounds() -> None:
    assert aurc_oracle(0, 4) == 0.0
    assert aurc_oracle(4, 4) == 1.0
    # One error ranked last: risks [0, 0, 0, 1/4] -> mean 1/16.
    assert aurc_oracle(1, 4) == pytest.approx(1 / 16)
    with pytest.raises(ValueError):
        aurc_oracle(5, 4)


def test_aurc_excess_is_nonnegative() -> None:
    rng = np.random.default_rng(11)
    probs = rng.uniform(0.05, 0.95, size=200)
    labels = (rng.uniform(size=200) < 0.5).astype(int)
    errors = int(((probs >= 0.5).astype(int) != labels).sum())
    assert aurc(probs, labels) >= aurc_oracle(errors, len(labels)) - 1e-12


# ── E50 dual axis ─────────────────────────────────────────────────────────


def test_dual_axis_matrix_cells_and_precision() -> None:
    matrix = dual_axis_matrix(
        covered=[True, True, False, False],
        obligations_met=[True, False, True, False],
        labels=[1, 0, 1, 0],
    )
    cells = matrix["cells"]
    assert cells["conformal_covered|contract_met"] == {
        "n": 1, "n_pos": 1, "precision": 1.0,
    }
    assert cells["conformal_covered|contract_unmet"]["precision"] == 0.0
    assert cells["conformal_abstain|contract_met"]["precision"] == 1.0
    assert cells["conformal_abstain|contract_unmet"]["precision"] == 0.0
    margins = matrix["margins"]
    assert margins["conformal_covered"]["n"] == 2
    assert margins["conformal_covered"]["precision"] == 0.5
    assert margins["contract_met"]["precision"] == 1.0
    assert margins["all"]["n_pos"] == 2


def test_dual_axis_matrix_empty_cell_has_none_precision() -> None:
    matrix = dual_axis_matrix(
        covered=[False, False], obligations_met=[False, False], labels=[0, 0]
    )
    cell = matrix["cells"]["conformal_covered|contract_met"]
    assert cell["n"] == 0 and cell["precision"] is None


def test_dual_axis_matrix_rejects_misaligned_inputs() -> None:
    with pytest.raises(ValueError):
        dual_axis_matrix([True], [True], [1, 0])


# ── misc pure helpers ─────────────────────────────────────────────────────


def test_bucket_key_format() -> None:
    pair = {
        "anchor": {"doc_id": "01"},
        "candidate": {"doc_id": "01"},
        "features": {"kind_pair": "claim+requirement", "same_section": True},
    }
    assert bucket_key(pair) == "claim+requirement|True"


def test_log_loss_matches_manual_computation() -> None:
    value = log_loss([0.8, 0.3], [1, 0])
    expected = -(math.log(0.8) + math.log(0.7)) / 2
    assert value == pytest.approx(expected)
    with pytest.raises(ValueError):
        log_loss([], [])
