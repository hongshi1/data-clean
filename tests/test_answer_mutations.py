"""Answer-side mutation operators preserve question/context and require proof."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_mutations import (  # noqa: E402
    OPERATOR_STATUS,
    propose_enum_explicit_conflict,
    propose_abbreviation_expansion,
    propose_equivalent_numeric_surface,
    propose_explicit_quote_conflict,
    propose_exact_numeric_conflict,
    propose_numeric_identity,
    propose_out_of_range_conflict,
    propose_reversed_data_flow,
    propose_unsupported_answer,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402


def make_input() -> QAInput:
    return QAInput(
        instance_id="q-1", question="系统响应时间要求是多少？",
        answer="响应时间为200ms。", context_freeze_id="upstream-freeze-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="响应时间为200ms。", source_type="text",
            source_ref=SourceRef(doc_id="d1", section="3.2.1"),
            scope_id="d1:3.2.1"),),
    )


def test_numeric_conflict_mutates_answer_only_and_has_proof() -> None:
    request = make_input()
    proposal = propose_exact_numeric_conflict(
        request, evidence_id="e1", mutated_value=300)
    assert proposal.target == "answer"
    assert proposal.question == request.question
    assert proposal.answer_before == request.answer
    assert proposal.answer_after == "响应时间为300ms。"
    assert proposal.context_freeze_id == request.context_freeze_id
    assert proposal.context_hash
    assert proposal.question_hash
    assert proposal.context_refs == (request.evidence[0].source_ref,)
    assert proposal.gold_candidate == "refute"
    assert proposal.operator_id == "ANSWER-NUM-EQ-CONFLICT-V1"
    assert proposal.proof_kind == "explicit_equality_conflict"
    assert proposal.requires_manual_review is False


def test_numeric_identity_is_support_control() -> None:
    request = make_input()
    proposal = propose_numeric_identity(request, evidence_id="e1")
    assert proposal.answer_after == request.answer
    assert proposal.gold_candidate == "support"
    assert proposal.proof_kind == "explicit_equality_match"


def test_numeric_conflict_rejects_wrong_scope_and_unproved_units() -> None:
    request = make_input()
    changed = QAInput(
        instance_id=request.instance_id, question=request.question,
        answer=request.answer, context_freeze_id=request.context_freeze_id,
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="吞吐量为200ms。", source_type="text",
            source_ref=request.evidence[0].source_ref, scope_id="scope"),),
    )
    try:
        propose_exact_numeric_conflict(changed, evidence_id="e1", mutated_value=300)
    except ValueError as exc:
        assert "subjects" in str(exc)
    else:
        raise AssertionError("different parameter subject must not be mutated as a proven conflict")


def test_numeric_operator_rejects_subject_not_asked_by_question() -> None:
    request = QAInput(
        instance_id="qa-wrong-question", question="CPU占用率要求是多少？",
        answer="响应时间为200ms。", context_freeze_id="ctx",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="响应时间为200ms。", source_type="text",
            source_ref=SourceRef(doc_id="d1", section="3.2.1"),
            scope_id="d1:3.2.1"),),
    )
    try:
        propose_exact_numeric_conflict(request, evidence_id="e1", mutated_value=300)
    except ValueError as exc:
        assert "question does not explicitly ask" in str(exc)
    else:
        raise AssertionError("operator must not mutate an attribute unrelated to the question")


def test_nie_candidate_is_not_automatically_labelled() -> None:
    proposal = propose_unsupported_answer(
        make_input(), answer_after="BLOB大小为65535字节。",
        operator_id="ANSWER-UNSUPPORTED-REVIEW", check_item="PARAM-05")
    assert proposal.gold_candidate is None
    assert proposal.requires_manual_review


def test_legacy_pair_mutations_are_quarantined() -> None:
    assert OPERATOR_STATUS["LEGACY-PAIR-MUTATIONS"] == "quarantined_legacy"
    assert OPERATOR_STATUS["LEGACY-MMQA-CONTEXT-MUTATIONS"] == "quarantined_until_context_gold"


def test_unit_equivalent_mutation_is_support_with_conversion_proof() -> None:
    request = QAInput(
        instance_id="qa-unit", question="系统响应时间是多少？",
        answer="响应时间为0.2秒。", context_freeze_id="ctx-unit",
        evidence=(RetrievedEvidence(
            evidence_id="e-unit", text="响应时间为0.2秒。", source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    proposal = propose_equivalent_numeric_surface(
        request, evidence_id="e-unit", target_unit="ms")
    assert proposal.answer_after == "响应时间为200ms。"
    assert proposal.gold_candidate == "support"
    assert proposal.proof_kind == "unit_conversion_equality"
    assert proposal.question_hash and proposal.context_hash


def test_equivalent_operator_rejects_non_equivalent_source_answer() -> None:
    request = QAInput(
        instance_id="qa-unit-bad", question="系统响应时间是多少？",
        answer="响应时间为20ms。", context_freeze_id="ctx-unit",
        evidence=(RetrievedEvidence(
            evidence_id="e-unit", text="响应时间为0.2秒。", source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    try:
        propose_equivalent_numeric_surface(request, evidence_id="e-unit", target_unit="ms")
    except ValueError as exc:
        assert "not numerically supported" in str(exc)
    else:
        raise AssertionError("non-equivalent source answer must not generate support gold")


def test_explicit_quote_conflict_has_refutation_proof() -> None:
    request = QAInput(
        instance_id="qa-quote", question="系统包括哪些功能？",
        answer="系统包括「X功能」。", context_freeze_id="ctx-quote",
        evidence=(RetrievedEvidence(
            evidence_id="e-quote", text="系统不支持「Y功能」。", source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    proposal = propose_explicit_quote_conflict(
        request, evidence_id="e-quote", contradicted_term="Y功能")
    assert proposal.answer_after == "系统包括「Y功能」。"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "explicit_quote_negation"
    assert proposal.requires_manual_review is False


def test_explicit_enum_conflict_has_refutation_proof() -> None:
    request = QAInput(
        instance_id="qa-enum", question="系统包括哪些功能？",
        answer="系统包括A功能、B功能。", context_freeze_id="ctx-enum",
        evidence=(RetrievedEvidence(
            evidence_id="e-enum", text="系统不包括C功能。", source_type="table",
            source_ref=SourceRef(doc_id="doc01", section="4.1", row_id="r1"),
            scope_id="doc01:4.1"),),
    )
    proposal = propose_enum_explicit_conflict(
        request, evidence_id="e-enum", added_term="C功能")
    assert proposal.answer_after == "系统包括A功能、B功能、C功能。"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "explicit_enum_exclusion"


def test_term08_expands_only_explicit_abbreviation_definition() -> None:
    request = QAInput(
        instance_id="term08", question="HTTP的全称是什么？", answer="「HTTP」是协议。",
        context_freeze_id="ctx", evidence=(RetrievedEvidence(
            evidence_id="e", text="HTTP（超文本传输协议）用于传输。", source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),))
    proposal = propose_abbreviation_expansion(request, evidence_id="e")
    assert proposal.answer_after == "「超文本传输协议」是协议。"
    assert proposal.check_item == "TERM-08" and proposal.gold_candidate == "support"
    assert proposal.proof_kind == "explicit_acronym_definition"


def test_param06_refutes_value_outside_explicit_range() -> None:
    request = QAInput(
        instance_id="range", question="响应时间是多少？", answer="响应时间为200ms。",
        context_freeze_id="ctx", evidence=(RetrievedEvidence(
            evidence_id="e", text="响应时间为100至200ms。", source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),))
    proposal = propose_out_of_range_conflict(request, evidence_id="e", mutated_value=201)
    assert proposal.answer_after == "响应时间为201ms。"
    assert proposal.check_item == "PARAM-06" and proposal.gold_candidate == "refute"
    try:
        propose_out_of_range_conflict(request, evidence_id="e", mutated_value=150)
    except ValueError:
        pass
    else:
        raise AssertionError("in-range mutation must be rejected")


def test_logic04_reverses_explicit_flow_direction() -> None:
    request = QAInput(
        instance_id="flow", question="A向哪里发送数据？", answer="A向B发送数据。",
        context_freeze_id="ctx", evidence=(RetrievedEvidence(
            evidence_id="e", text="A向B发送数据。", source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),))
    proposal = propose_reversed_data_flow(request, evidence_id="e")
    assert proposal.answer_after == "B向A发送数据。"
    assert proposal.check_item == "LOGIC-04" and proposal.gold_candidate == "refute"
