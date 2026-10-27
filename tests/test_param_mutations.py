"""Tests for PARAM-family answer-only mutation operators."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.param_mutations import (  # noqa: E402
    propose_numeric_equivalent,
    propose_param_conflict_for,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402


def make_input(question: str, answer: str, evidence_text: str) -> QAInput:
    return QAInput(
        instance_id="param-1", question=question, answer=answer,
        context_freeze_id="freeze-param",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text=evidence_text, source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),),
    )


def test_param01_time_conflict_is_refute_with_disjoint_interval() -> None:
    request = make_input(
        "系统响应时间要求是多少？",
        "响应时间不超过200ms。",
        "系统响应时间不超过200ms。",
    )
    proposal = propose_param_conflict_for(
        request, evidence_id="e1", check_item="PARAM-01", mutated_value=300)
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "响应时间为300ms。"
    assert proposal.proof_kind == "numeric_interval_disjoint"
    assert proposal.check_item == "PARAM-01"


def test_param02_period_conflict_below_ge_threshold() -> None:
    request = make_input(
        "采集周期是多少？",
        "采集周期为5秒。",
        "采集周期不少于5秒。",
    )
    proposal = propose_param_conflict_for(
        request, evidence_id="e1", check_item="PARAM-02", mutated_value=2)
    assert proposal.gold_candidate == "refute"
    assert "采集周期为2" in proposal.answer_after


def test_conflict_rejects_value_inside_evidence_interval() -> None:
    request = make_input(
        "系统响应时间要求是多少？",
        "响应时间不超过200ms。",
        "系统响应时间不超过200ms。",
    )
    with pytest.raises(ValueError, match="does not contradict"):
        propose_param_conflict_for(
            request, evidence_id="e1", check_item="PARAM-01", mutated_value=150)


def test_conflict_rejects_subject_mismatch() -> None:
    request = make_input(
        "CPU占用率上限是多少？",
        "响应时间不超过200ms。",
        "系统响应时间不超过200ms。",
    )
    with pytest.raises(ValueError, match="no numeric claim"):
        propose_param_conflict_for(
            request, evidence_id="e1", check_item="PARAM-05", mutated_value=90)


def test_conflict_rejects_question_not_mentioning_subject() -> None:
    request = make_input(
        "内存容量要求是多少？",
        "响应时间不超过200ms。",
        "系统响应时间不超过200ms。",
    )
    with pytest.raises(ValueError, match="question does not mention"):
        propose_param_conflict_for(
            request, evidence_id="e1", check_item="PARAM-01", mutated_value=300)


def test_conflict_rejects_source_answer_already_conflicting() -> None:
    request = make_input(
        "系统响应时间要求是多少？",
        "响应时间不小于500ms。",
        "系统响应时间不超过200ms。",
    )
    with pytest.raises(ValueError, match="already conflicts"):
        propose_param_conflict_for(
            request, evidence_id="e1", check_item="PARAM-01", mutated_value=600)


def test_conflict_rejects_cross_family_units() -> None:
    request = make_input(
        "存储容量要求是多少？",
        "存储容量为200MB。",
        "存储容量不少于10GB。",
    )
    with pytest.raises(ValueError, match="already conflicts"):
        propose_param_conflict_for(
            request, evidence_id="e1", check_item="PARAM-07", mutated_value=1)


def test_equivalent_unit_rewrite_is_support() -> None:
    request = make_input(
        "系统响应时间要求是多少？",
        "响应时间为200ms。",
        "响应时间不超过200ms。",
    )
    proposal = propose_numeric_equivalent(
        request, evidence_id="e1", target_unit="秒")
    assert proposal.gold_candidate == "support"
    assert "0.2秒" in proposal.answer_after
    assert proposal.proof_kind == "unit_conversion_equality"


def test_equivalent_rejects_cross_family_unit() -> None:
    request = make_input(
        "系统响应时间要求是多少？",
        "响应时间为200ms。",
        "响应时间不超过200ms。",
    )
    with pytest.raises(ValueError, match="families"):
        propose_numeric_equivalent(request, evidence_id="e1", target_unit="GB")


def test_unknown_check_item_rejected() -> None:
    request = make_input(
        "系统响应时间要求是多少？",
        "响应时间不超过200ms。",
        "系统响应时间不超过200ms。",
    )
    with pytest.raises(ValueError, match="unknown PARAM check_item"):
        propose_param_conflict_for(
            request, evidence_id="e1", check_item="PARAM-99", mutated_value=300)
