"""Tests for proof-backed, answer-only structural mutations."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402
from algorithms.consistency.structural_mutations import (  # noqa: E402
    propose_actor_role_list_mutation,
    propose_closed_list_add,
    propose_closed_list_remove,
    propose_exception_outcome_swap,
    propose_step_delete,
    propose_step_reorder,
)


def make_input(answer: str, text: str, *, question: str = "系统配置是什么？",
               complete: str = "closed",
               proof: str = "explicit table header says complete set") -> QAInput:
    return QAInput(
        instance_id="struct-1", question=question, answer=answer,
        context_freeze_id="freeze-1", evidence=(RetrievedEvidence(
            evidence_id="e1", text=text, source_type="text",
            source_ref=SourceRef("doc", section="3.1"), scope_id="doc:3.1",
            completeness=complete, completeness_proof=proof),))


def test_closed_list_add_and_remove_are_proof_backed() -> None:
    request = make_input("系统包括A、B。", "系统包括A、B、C。", question="系统包括哪些？")
    added = propose_closed_list_add(request, evidence_id="e1", member="C")
    assert added.answer_after == "系统包括A、B、C。"
    assert added.gold_candidate == "support"
    assert added.proof and added.context_hash and added.question_hash
    removed = propose_closed_list_remove(
        make_input("系统清单为A、B、C。", "系统清单为A、B、C。",
                   question="系统清单有哪些？"),
        evidence_id="e1", member="B")
    assert removed.answer_after == "系统清单为A、C。"
    assert removed.gold_candidate == "refute"
    assert removed.question == "系统清单有哪些？"
    assert removed.context_freeze_id == "freeze-1"


@pytest.mark.parametrize("complete,proof", [("open", "complete"), ("closed", "")])
def test_closed_list_rejects_open_or_unproved_scope(complete: str, proof: str) -> None:
    request = make_input("系统包括A、B。", "系统包括A、B、C。", complete=complete, proof=proof)
    with pytest.raises(ValueError):
        propose_closed_list_add(request, evidence_id="e1", member="C")


@pytest.mark.parametrize("answer", ["系统包括A。", "系统包括A、B、D。"])
def test_closed_list_add_rejects_incomplete_or_extra_answer(answer: str) -> None:
    with pytest.raises(ValueError):
        propose_closed_list_add(
            make_input(answer, "系统包括A、B、C。", question="系统包括哪些？"),
            evidence_id="e1", member="C")


@pytest.mark.parametrize("question", ["系统是什么？", "系统包括A吗？", "有哪些配置？"])
def test_closed_list_add_rejects_ambiguous_question_intent(question: str) -> None:
    with pytest.raises(ValueError, match="question explicitly asking"):
        propose_closed_list_add(
            make_input("系统包括A、B。", "系统包括A、B、C。", question=question),
            evidence_id="e1", member="C")


def test_closed_list_remove_rejects_nonexhaustive_answer() -> None:
    with pytest.raises(ValueError):
        propose_closed_list_remove(
            make_input("系统包括A、B。", "系统包括A、B、C。"),
            evidence_id="e1", member="B")


def test_step_reorder_and_delete_require_aligned_explicit_sequence() -> None:
    text = "必须按顺序；1. 校验；2. 必须处理；3. 输出。"
    request = make_input(text, text)
    reordered = propose_step_reorder(request, evidence_id="e1", first_step=1, second_step=3)
    assert reordered.answer_after == "必须按顺序；1. 输出；2. 必须处理；3. 校验。"
    assert reordered.gold_candidate == "refute"
    deleted = propose_step_delete(request, evidence_id="e1", step_number=2)
    assert "处理" not in deleted.answer_after
    assert "1. 校验；2. 输出。" in deleted.answer_after
    assert deleted.proof_kind == "closed_explicit_mandatory_step_deletion"
    assert deleted.gold_candidate == "refute"


def test_step_mutations_reject_open_or_misaligned_sequences() -> None:
    with pytest.raises(ValueError):
        propose_step_reorder(make_input("1. 校验；2. 处理。", "1. 校验；2. 处理。", complete="open"),
                             evidence_id="e1", first_step=1, second_step=2)
    with pytest.raises(ValueError):
        propose_step_delete(make_input("1. 校验；2. 处理；3. 输出。", "1. 校验；2. 其他；3. 输出。"),
                             evidence_id="e1", step_number=2)
    with pytest.raises(ValueError):
        propose_step_reorder(make_input("1. 校验；2. 处理。", "1. 校验；2. 处理。"),
                             evidence_id="e1", first_step=1, second_step=2)
    with pytest.raises(ValueError):
        propose_step_delete(make_input("1. 校验；2. 处理；3. 输出。", "1. 校验；2. 处理；3. 输出。"),
                            evidence_id="e1", step_number=2)


def test_exception_swap_requires_explicit_exclusion_and_same_condition() -> None:
    request = make_input("发生超时情况下应终止。", "发生超时时不得重试，只能终止。")
    proposal = propose_exception_outcome_swap(request, evidence_id="e1", mutated_outcome="重试")
    assert proposal.answer_after == "发生超时情况下应重试。"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "explicit_exception_outcome_exclusion"
    with pytest.raises(ValueError):
        propose_exception_outcome_swap(
            make_input("发生超时情况下应重试。", "发生超时时可重试或终止。"),
            evidence_id="e1", mutated_outcome="重试")


def test_exception_swap_does_not_infer_retry_fallback_exclusivity() -> None:
    request = make_input("发生超时情况下应终止。", "发生超时时应重试，必要时可回退或终止。")
    with pytest.raises(ValueError):
        propose_exception_outcome_swap(request, evidence_id="e1", mutated_outcome="重试")


def test_exception_swap_only_semantics_and_condition_equality() -> None:
    proposal = propose_exception_outcome_swap(
        make_input("发生超时情况下应终止。", "发生超时时只能终止。"),
        evidence_id="e1", mutated_outcome="重试")
    assert proposal.answer_after == "发生超时情况下应重试。"
    assert proposal.gold_candidate == "refute"
    with pytest.raises(ValueError):
        propose_exception_outcome_swap(
            make_input("发生通信超时情况下应终止。", "发生超时时不得重试。"),
            evidence_id="e1", mutated_outcome="重试")
    with pytest.raises(ValueError):
        propose_exception_outcome_swap(
            make_input("发生超时情况下应终止。", "发生超时时只能重试。"),
            evidence_id="e1", mutated_outcome="重试")


def test_actor_role_mutation_requires_closed_actor_set() -> None:
    request = make_input("参与者包括操作员、管理员。", "参与者包括操作员、管理员、审计员。",
                         question="参与者有哪些？")
    proposal = propose_actor_role_list_mutation(request, evidence_id="e1", member="审计员")
    assert proposal.answer_after == "参与者包括操作员、管理员、审计员。"
    assert proposal.gold_candidate == "support"
    with pytest.raises(ValueError):
        propose_actor_role_list_mutation(
            make_input("参与者包括操作员、管理员。", "参与者包括操作员、管理员、审计员。", complete="open"),
            evidence_id="e1", member="审计员")


def test_actor_role_mutation_rejects_generic_question() -> None:
    with pytest.raises(ValueError):
        propose_actor_role_list_mutation(
            make_input("参与者包括操作员、管理员。", "参与者包括操作员、管理员、审计员。"),
            evidence_id="e1", member="审计员")
