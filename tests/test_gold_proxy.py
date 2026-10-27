"""Tests for tools/build_gold_proxy.py (triple-consensus gold-proxy builder).

Pure-logic tests: upgrade-rule classification on synthetic scores, threshold
calibration (nearest-rank percentiles), rank AUC, Spearman, review-queue
ordering, and the fold_map -> split mapping. The anti-leakage asset test reads
gold_proxy_v1 only when the builder has produced it (skip otherwise).
No model loads, no GPU.
"""

import json
from pathlib import Path

import pytest

from tools.build_gold_proxy import (
    EXPECTED_TEST_DOCS,
    FOLD_TO_SPLIT,
    NEGATIVE_LABEL,
    POSITIVE_LABEL,
    REVIEW_LABEL,
    REVIEW_TOP_N,
    build_review_queue,
    calibrate_thresholds,
    classify_pair,
    nearest_rank_percentile,
    rank_auc,
    rule_label,
    spearman,
    split_of_pair,
)

BASE = Path(__file__).resolve().parents[1]
GOLD_PROXY_DIR = BASE / "data/gjb_438c/gold_proxy_v1"

BGE_TH = {"theta": 0.80, "theta_low": 0.50}
QWEN_TH = {"theta": 0.75, "theta_low": 0.45}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# ------------------------------------------------------------ upgrade rule


def test_positive_consensus_requires_both_encoders() -> None:
    assert classify_pair(1, 0.90, 0.80, BGE_TH, QWEN_TH) == (POSITIVE_LABEL, "")
    assert classify_pair(1, 0.80, 0.75, BGE_TH, QWEN_TH) == (POSITIVE_LABEL, "")


def test_positive_encoder_disagreement_goes_to_review() -> None:
    assert classify_pair(1, 0.90, 0.70, BGE_TH, QWEN_TH) == (
        REVIEW_LABEL, "pos_bge_high_qwen_low",
    )
    assert classify_pair(1, 0.70, 0.90, BGE_TH, QWEN_TH) == (
        REVIEW_LABEL, "pos_bge_low_qwen_high",
    )
    assert classify_pair(1, 0.60, 0.60, BGE_TH, QWEN_TH) == (
        REVIEW_LABEL, "pos_both_below_theta",
    )


def test_negative_consensus_requires_both_encoders_low() -> None:
    assert classify_pair(0, 0.40, 0.30, BGE_TH, QWEN_TH) == (NEGATIVE_LABEL, "")
    assert classify_pair(0, 0.4999, 0.44, BGE_TH, QWEN_TH) == (NEGATIVE_LABEL, "")


def test_negative_encoder_disagreement_goes_to_review() -> None:
    assert classify_pair(0, 0.40, 0.60, BGE_TH, QWEN_TH) == (
        REVIEW_LABEL, "neg_bge_low_qwen_high",
    )
    assert classify_pair(0, 0.60, 0.40, BGE_TH, QWEN_TH) == (
        REVIEW_LABEL, "neg_bge_high_qwen_low",
    )
    assert classify_pair(0, 0.60, 0.60, BGE_TH, QWEN_TH) == (
        REVIEW_LABEL, "neg_both_above_theta_low",
    )


def test_threshold_boundaries_are_conservative() -> None:
    assert classify_pair(0, 0.50, 0.30, BGE_TH, QWEN_TH)[0] == REVIEW_LABEL
    assert classify_pair(1, 0.7999, 0.90, BGE_TH, QWEN_TH)[0] == REVIEW_LABEL


def test_classify_rejects_unknown_rule_label() -> None:
    with pytest.raises(ValueError, match="rule must be 0 or 1"):
        classify_pair(2, 0.9, 0.9, BGE_TH, QWEN_TH)


def test_rule_label_maps_p1_and_sibling_bases() -> None:
    assert rule_label({"label_basis": "explicit_identifier"}) == 1
    assert rule_label({"label_basis": "sibling_distinct_identifier"}) == 0
    with pytest.raises(ValueError, match="unknown label_basis"):
        rule_label({"label_basis": "human_annotation"})


# -------------------------------------------------------- threshold calibration


def test_nearest_rank_percentile_on_uniform_scores() -> None:
    values = list(range(100))
    assert nearest_rank_percentile(values, 0.95) == 94.0
    assert nearest_rank_percentile(values, 0.05) == 4.0
    assert nearest_rank_percentile([7.0], 0.95) == 7.0


def test_nearest_rank_percentile_rejects_bad_input() -> None:
    with pytest.raises(ValueError, match="empty"):
        nearest_rank_percentile([], 0.95)
    with pytest.raises(ValueError, match="q must be"):
        nearest_rank_percentile([1.0, 2.0], 0.0)


def test_calibrate_thresholds_uses_neg95_and_pos5() -> None:
    dev_pos = [round(0.50 + i * 0.01, 2) for i in range(100)]
    dev_neg = [round(i * 0.01, 2) for i in range(100)]
    thresholds = calibrate_thresholds(dev_pos, dev_neg)
    assert thresholds["theta"] == pytest.approx(0.94)
    assert thresholds["theta_low"] == pytest.approx(0.54)
    assert thresholds["theta_low"] < thresholds["theta"]


# ----------------------------------------------------------------- metrics


def test_rank_auc_perfect_reversed_and_ties() -> None:
    assert rank_auc([0.9, 0.8, 0.3, 0.2], [1, 1, 0, 0]) == 1.0
    assert rank_auc([0.2, 0.3, 0.8, 0.9], [1, 1, 0, 0]) == 0.0
    assert rank_auc([0.5, 0.5, 0.5, 0.5], [1, 1, 0, 0]) == 0.5
    with pytest.raises(ValueError, match="at least one positive"):
        rank_auc([0.1, 0.2], [1, 1])


def test_spearman_monotone_relationships() -> None:
    assert spearman([1.0, 2.0, 3.0], [10.0, 20.0, 30.0]) == pytest.approx(1.0)
    assert spearman([1.0, 2.0, 3.0], [30.0, 20.0, 10.0]) == pytest.approx(-1.0)
    assert spearman([1.0, 1.0, 2.0], [5.0, 5.0, 9.0]) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        spearman([], [])


# -------------------------------------------------------------- review queue


def test_review_queue_orders_by_score_gap_desc_and_caps_rows() -> None:
    rows = [
        {"pair_id": "PAIR-a", "score_gap": 0.10},
        {"pair_id": "PAIR-b", "score_gap": 0.50},
        {"pair_id": "PAIR-c", "score_gap": 0.30},
    ]
    queue = build_review_queue(rows, 2)
    assert [row["pair_id"] for row in queue] == ["PAIR-b", "PAIR-c"]
    assert build_review_queue(rows, REVIEW_TOP_N)[0]["pair_id"] == "PAIR-b"


def test_review_queue_ties_break_by_pair_id() -> None:
    rows = [
        {"pair_id": "PAIR-b", "score_gap": 0.40},
        {"pair_id": "PAIR-a", "score_gap": 0.40},
    ]
    queue = build_review_queue(rows, 5)
    assert [row["pair_id"] for row in queue] == ["PAIR-a", "PAIR-b"]


# ------------------------------------------------------- fold / split mapping


def test_split_of_pair_follows_fold_map() -> None:
    fold_map = {"06": 0, "01": 1, "02": 2, "03": 3}
    assert split_of_pair({"anchor": {"doc_id": "06"}}, fold_map) == "test"
    assert split_of_pair({"anchor": {"doc_id": "01"}}, fold_map) == "dev"
    assert split_of_pair({"anchor": {"doc_id": "02"}}, fold_map) == "train"
    assert split_of_pair({"anchor": {"doc_id": "03"}}, fold_map) == "train"
    assert set(FOLD_TO_SPLIT.values()) == {"test", "dev", "train"}


def test_split_of_pair_rejects_doc_outside_fold_map() -> None:
    with pytest.raises(SystemExit, match="missing from fold_map"):
        split_of_pair({"anchor": {"doc_id": "99"}}, {"06": 0})


# ----------------------------------------------- anti-leakage on built assets


@pytest.mark.skipif(
    not (GOLD_PROXY_DIR / "gold_proxy_pairs.jsonl").exists(),
    reason="gold_proxy_v1未构建(先跑 python tools/build_gold_proxy.py)",
)
def test_gold_proxy_pairs_come_only_from_test_fold() -> None:
    rows = read_jsonl(GOLD_PROXY_DIR / "gold_proxy_pairs.jsonl")
    assert rows, "gold_proxy_pairs.jsonl不应为空"
    for row in rows:
        assert row["split"] == "test"
        assert row["exogenous_evaluation_only"] is True
        assert row["anchor"]["doc_id"] in EXPECTED_TEST_DOCS
        assert row["candidate"]["doc_id"] in EXPECTED_TEST_DOCS
        assert row["proxy_label"] in (POSITIVE_LABEL, NEGATIVE_LABEL)
        assert row["proxy_basis"] == "triple_consensus"
        assert row["quality_tier"] == "gold_proxy"


@pytest.mark.skipif(
    not (GOLD_PROXY_DIR / "review_queue.jsonl").exists(),
    reason="gold_proxy_v1未构建(先跑 python tools/build_gold_proxy.py)",
)
def test_review_queue_rows_are_test_fold_and_sorted_by_gap() -> None:
    rows = read_jsonl(GOLD_PROXY_DIR / "review_queue.jsonl")
    for row in rows:
        assert row["split"] == "test"
        assert row["exogenous_evaluation_only"] is True
        assert row["anchor"]["doc_id"] in EXPECTED_TEST_DOCS
        assert row["proxy_label"] == REVIEW_LABEL
        assert row["review_type"].startswith(("pos_", "neg_"))
        assert row["score_gap"] == pytest.approx(
            abs(row["bge_cos"] - row["qwen3_cos"]), abs=1e-9
        )
    gaps = [row["score_gap"] for row in rows]
    assert gaps == sorted(gaps, reverse=True)
    assert len(rows) <= REVIEW_TOP_N


@pytest.mark.skipif(
    not (GOLD_PROXY_DIR / "summary.json").exists(),
    reason="gold_proxy_v1未构建(先跑 python tools/build_gold_proxy.py)",
)
def test_summary_counts_match_files_and_policy_is_exogenous() -> None:
    summary = json.loads(
        (GOLD_PROXY_DIR / "summary.json").read_text(encoding="utf-8")
    )
    policy = summary["policy"]
    assert policy["exogenous_only"] is True
    assert policy["silver_bound_not_gold"] is True
    assert summary["exogenous_evaluation_only"] is True
    assert set(summary["test_docs"]) == EXPECTED_TEST_DOCS
    gold_rows = read_jsonl(GOLD_PROXY_DIR / "gold_proxy_pairs.jsonl")
    n_pos = sum(1 for row in gold_rows if row["proxy_label"] == POSITIVE_LABEL)
    n_neg = sum(1 for row in gold_rows if row["proxy_label"] == NEGATIVE_LABEL)
    assert summary["counts"]["gold_proxy_positive"] == n_pos
    assert summary["counts"]["gold_proxy_negative"] == n_neg
    thresholds = summary["thresholds"]
    for encoder in ("bge", "qwen3"):
        assert thresholds[encoder]["theta_low"] < thresholds[encoder]["theta"]
