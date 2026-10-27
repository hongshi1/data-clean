"""Tests for tools/eval_contract_risk_coverage.py (E48: E0 vs E3 gating).

Pure-logic tests only: obligation checks, the E3 decision rule, threshold
computation on synthetic score distributions, and the derived metrics. No
model loads, no real data files.
"""

from tools.eval_contract_risk_coverage import (
    OBLIGATION_IDS,
    contract_decision,
    contract_gated_metrics,
    dev_negative_threshold,
    e0_predict,
    extract_sections,
    forced_classification_metrics,
    identity_evidence,
    obligation_status,
    percentile,
    resolve_claim_vector_id,
    risk_coverage_points,
    scope_evidence,
    value_parse_evidence,
)


def make_pair(
    anchor_text: str = "",
    candidate_text: str = "",
    same_section: bool = False,
    shared_ids: list[str] | None = None,
) -> dict:
    return {
        "anchor": {
            "text": anchor_text,
            "doc_id": "01",
            "kind": "claim",
            "occurrence_id": "claim:CLM-a",
            "section": "",
        },
        "candidate": {
            "text": candidate_text,
            "doc_id": "01",
            "kind": "claim",
            "occurrence_id": "claim:CLM-b",
            "section": "",
        },
        "features": {
            "same_section": same_section,
            "shared_identifiers": list(shared_ids or []),
            "kind_pair": "claim+claim",
        },
        "label": 1,
    }


# ---------------------------------------------------------------- obligations


def test_identity_evidence_true_only_with_shared_identifier() -> None:
    assert identity_evidence(make_pair(shared_ids=["JCYY-GN-JCYYKJYYWTX"])) is True
    assert identity_evidence(make_pair(shared_ids=[])) is False
    assert identity_evidence(make_pair(shared_ids=["", "x"])) is True


def test_scope_evidence_paths() -> None:
    # same_section feature short-circuits to satisfied.
    assert scope_evidence(make_pair(same_section=True)) is True
    # identical section citations in both texts.
    assert (
        scope_evidence(
            make_pair("见3.2.1节的描述", "同3.2.1节要求")
        )
        is True
    )
    # different section citations.
    assert scope_evidence(make_pair("见3.2节", "见3.3节")) is False
    # no section citations on either side.
    assert scope_evidence(make_pair("无编号文字", "亦无编号")) is False
    # only one side carries a citation.
    assert scope_evidence(make_pair("见3.2节", "无编号文字")) is False


def test_value_parse_evidence_paths() -> None:
    assert value_parse_evidence(make_pair("延时不超过100ms", "迅速响应")) is True
    assert value_parse_evidence(make_pair("无数字", "精度0.5度")) is True
    assert value_parse_evidence(make_pair("无数字", "亦无数字")) is False


def test_extract_sections_collects_full_matches() -> None:
    assert extract_sections("见3.2.1节与3.11节的说明") == {"3.2.1", "3.11"}
    assert extract_sections("没有编号") == set()
    assert extract_sections("3.2.2.2") == {"3.2.2.2"}


def test_obligation_status_reports_all_three() -> None:
    pair = make_pair(
        "共享标识的处理延时见3.2.1节",
        "同标识在3.2.1节的取值为100ms",
        shared_ids=["REQ-1"],
    )
    status = obligation_status(pair)
    assert set(status) == set(OBLIGATION_IDS)
    assert status == {
        "identity_evidence": True,
        "scope_evidence": True,
        "value_parse": True,
    }


# ------------------------------------------------------------- E3 decision


def test_contract_decision_confirmed_when_score_and_obligations_ok() -> None:
    obligations = {"identity_evidence": True, "scope_evidence": True, "value_parse": True}
    assert contract_decision(0.9, 0.75, obligations) == "confirmed_same"
    assert contract_decision(0.75, 0.75, obligations) == "confirmed_same"


def test_contract_decision_any_missing_obligation_forces_abstain() -> None:
    full = {"identity_evidence": True, "scope_evidence": True, "value_parse": True}
    for missing in OBLIGATION_IDS:
        obligations = dict(full)
        obligations[missing] = False
        assert contract_decision(0.9, 0.75, obligations) == "abstain"
    assert contract_decision(0.9, 0.75, {}) == "abstain"


def test_contract_decision_rejected_below_threshold_regardless_of_obligations() -> None:
    full = {"identity_evidence": True, "scope_evidence": True, "value_parse": True}
    assert contract_decision(0.749, 0.75, full) == "rejected"
    assert contract_decision(0.0, 0.75, {}) == "rejected"


def test_e0_predict_boundary_and_sides() -> None:
    assert e0_predict(0.8, 0.75) == 1
    assert e0_predict(0.75, 0.75) == 1
    assert e0_predict(0.7499, 0.75) == 0


# ---------------------------------------------------------------- thresholds


def test_percentile_order_statistics() -> None:
    assert percentile(sorted([1.0, 2.0, 3.0, 4.0]), 0.5) == 2.0
    assert percentile(sorted([1.0, 2.0, 3.0, 4.0]), 1.0) == 4.0
    assert percentile(sorted([1.0, 2.0]), 0.999) == 2.0
    assert percentile(sorted([1.0, 2.0]), 0.0) == 1.0
    assert percentile([], 0.95) == 0.0


def test_dev_negative_threshold_on_synthetic_distribution() -> None:
    # 100 negatives at 0.01..1.00; positives placed high to check exclusion.
    scores = [round(0.01 * (i + 1), 4) for i in range(100)] + [0.99, 0.995]
    labels = [0] * 100 + [1, 1]
    assert dev_negative_threshold(scores, labels, 0.95) == 0.95
    assert dev_negative_threshold(scores, labels, 0.50) == 0.5
    # No negatives at all -> degenerate 0.0.
    assert dev_negative_threshold([0.9, 0.8], [1, 1]) == 0.0


# ------------------------------------------------------------------- metrics


def test_forced_classification_metrics_counts() -> None:
    scores = [0.9, 0.8, 0.7, 0.3]
    labels = [1, 0, 1, 0]
    metrics = forced_classification_metrics(scores, labels, 0.75)
    assert metrics["tp"] == 1
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tn"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["false_merge_rate"] == 0.5
    assert metrics["error_rate"] == 0.5
    assert metrics["coverage"] == 1.0


def test_contract_gated_metrics_saved_fp_and_costs() -> None:
    scores = [0.9, 0.8, 0.7, 0.3]
    labels = [1, 0, 1, 0]
    full = {"identity_evidence": True, "scope_evidence": True, "value_parse": True}
    empty = {"identity_evidence": False, "scope_evidence": False, "value_parse": False}
    obligations_list = [full, empty, full, empty]
    metrics = contract_gated_metrics(scores, labels, obligations_list, 0.75)
    # pair 1: confirmed TP; pair 2: high-score negative -> abstain (saved FP);
    # pair 3: below tau positive -> rejected FN; pair 4: below tau negative -> OK.
    assert metrics["confirmed_tp"] == 1
    assert metrics["confirmed_fp"] == 0
    assert metrics["confirmed_precision"] == 1.0
    assert metrics["n_abstain"] == 1
    assert metrics["abstention_rate"] == 0.25
    assert metrics["coverage"] == 0.75
    assert metrics["e0_fp"] == 1
    assert metrics["saved_high_risk_fp"] == 1
    assert metrics["saved_rate"] == 1.0
    assert metrics["residual_fp"] == 0
    assert metrics["rejected_pos"] == 1
    assert metrics["selective_risk"] == round(1 / 3, 4)
    assert set(metrics["abstain_missing_obligations"]) == {
        "identity_evidence+scope_evidence+value_parse"
    }


def test_risk_coverage_points_rows_and_coverage() -> None:
    scores = [0.9, 0.8, 0.7, 0.3]
    labels = [1, 0, 1, 0]
    full = {"identity_evidence": True, "scope_evidence": True, "value_parse": True}
    empty = {"identity_evidence": False, "scope_evidence": False, "value_parse": False}
    obligations_list = [full, empty, full, empty]
    rows = risk_coverage_points(
        scores, labels, obligations_list, [(0.5, 0.5), (0.95, 0.75)]
    )
    assert len(rows) == 2
    assert rows[0]["q"] == 0.5 and rows[0]["tau"] == 0.5
    assert rows[0]["E0"]["coverage"] == 1.0
    # At tau=0.5 all four pairs pass the score gate; the negative abstains.
    assert rows[0]["E3"]["coverage"] == 0.75
    assert rows[0]["E3"]["n_abstain"] == 1
    # At tau=0.75 only pairs 1-2 pass the gate; same single abstention.
    assert rows[1]["E3"]["coverage"] == 0.75
    assert rows[1]["E0"]["fp"] == 1


def test_resolve_claim_vector_id_prefix_mapping() -> None:
    assert resolve_claim_vector_id("claims:CLM-abc") == "claim:CLM-abc"
    assert resolve_claim_vector_id("claim:CLM-abc") == "claim:CLM-abc"
    assert resolve_claim_vector_id("ITEM-xyz") == "ITEM-xyz"
