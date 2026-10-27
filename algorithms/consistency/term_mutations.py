"""TERM-family answer-only mutation operators with explicit lexical proof.

TERM-02/04/05/07 target definition swaps, status-term exclusion, command
action swaps, and interface identifier conflicts. All refutes require the
evidence to state the conflicting definition/identifier explicitly.
"""
from __future__ import annotations

import re

from algorithms.consistency.answer_mutations import (
    AnswerMutationProposal,
    _context_hash,
    _question_hash,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence

_INTERFACE_ID = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,12}){1,6}")


def _find_evidence(request: QAInput, evidence_id: str) -> RetrievedEvidence:
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    return evidence


def _question_mentions(question: str, *terms: str) -> None:
    compact = re.sub(r"\s+", "", question)
    if not any(term and term in compact for term in terms):
        raise ValueError("question does not mention the mutated subject")


def _proposal(request: QAInput, evidence: RetrievedEvidence, *, operator_id: str,
              check_item: str, answer_after: str, proof_kind: str,
              proof: str, verdict: str = "refute") -> AnswerMutationProposal:
    if answer_after == request.answer:
        raise ValueError("mutation must change the answer")
    return AnswerMutationProposal(
        operator_id=operator_id, check_item=check_item,
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate=verdict, proof_kind=proof_kind, proof=proof,
        requires_manual_review=False,
    )


def propose_definition_swap(request: QAInput, *, evidence_id: str,
                            ) -> AnswerMutationProposal:
    """Swap the bracketed definitions of two differently-named terms (TERM-02)."""
    evidence = _find_evidence(request, evidence_id)
    definitions = re.findall(
        r"[「\"]?(?P<term>[A-Za-z\u4e00-\u9fff]{1,12})[」\"]?（(?P<def>[^）]{1,24})）",
        evidence.text)
    if len(definitions) < 2:
        raise ValueError("evidence does not define two terms with bracketed definitions")
    answer_pair = re.search(
        r"[「\"]?(?P<term>[A-Za-z\u4e00-\u9fff]{1,12})[」\"]?（(?P<def>[^）]{1,24})）",
        request.answer)
    if answer_pair is None:
        raise ValueError("answer has no bracketed term definition to mutate")
    term, definition = answer_pair.group("term"), answer_pair.group("def")
    matched = [d for t, d in definitions if t == term]
    if not matched:
        raise ValueError("evidence does not define the answer's term")
    if definition != matched[0]:
        raise ValueError("source answer definition does not match the evidence")
    other = [d for t, d in definitions if t != term and d != definition]
    if not other:
        raise ValueError("no distinct second definition available for the swap")
    _question_mentions(request.question, term)
    answer_after = (request.answer[:answer_pair.start("def")] + other[0]
                    + request.answer[answer_pair.end("def"):])
    return _proposal(request, evidence,
                     operator_id="ANSWER-TERM-02-DEFINITION-SWAP-V1",
                     check_item="TERM-02", answer_after=answer_after,
                     proof_kind="explicit_definition_mismatch",
                     proof=(f"evidence显式定义{term}（{matched[0]}）；"
                            f"answer把定义换成了另一术语的（{other[0]}），同名异义冲突。"))


def propose_status_term_conflict(request: QAInput, *, evidence_id: str,
                                 excluded_status: str,
                                 ) -> AnswerMutationProposal:
    """Add an explicitly excluded status/alarm name to the answer (TERM-04)."""
    evidence = _find_evidence(request, evidence_id)
    status = excluded_status.strip()
    if len(status) < 2:
        raise ValueError("excluded_status must be at least two characters")
    if status not in evidence.text:
        raise ValueError("evidence does not mention the excluded status")
    if not re.search(r"(?:状态|告警|报警)", evidence.text + request.answer):
        raise ValueError("operator applies only to status/alarm terminology")
    position = evidence.text.find(status)
    prefix = evidence.text[max(0, position - 12):position]
    if not re.search(r"(?:不包括|不包含|无|不含|只有|仅有)", prefix):
        raise ValueError("evidence does not explicitly exclude the status")
    if status in request.answer:
        raise ValueError("answer already contains the excluded status")
    _question_mentions(request.question, "状态", "告警", "报警")
    answer_after = f"{request.answer.rstrip('。')}、{status}。"
    return _proposal(request, evidence,
                     operator_id="ANSWER-TERM-04-STATUS-CONFLICT-V1",
                     check_item="TERM-04", answer_after=answer_after,
                     proof_kind="explicit_status_exclusion",
                     proof=f"evidence显式排除状态「{status}」；answer变异后将其加入。")


def propose_command_action_swap(request: QAInput, *, evidence_id: str,
                                ) -> AnswerMutationProposal:
    """Swap a command's action with another command's evidenced action (TERM-05)."""
    evidence = _find_evidence(request, evidence_id)
    commands = re.findall(
        r"指令(?P<name>[A-Za-z\u4e00-\u9fff]{1,12})（(?:执行)?(?P<action>[^）]{1,16})）",
        evidence.text)
    if len(commands) < 2:
        raise ValueError("evidence does not define two commands with actions")
    answer_command = re.search(
        r"指令(?P<name>[A-Za-z\u4e00-\u9fff]{1,12})(?:执行|进行)?(?P<action>[^，。；\n]{1,16})",
        request.answer)
    if answer_command is None:
        raise ValueError("answer has no command action to mutate")
    name, action = (answer_command.group("name"),
                    answer_command.group("action").strip().strip("（）"))
    matched = [a for n, a in commands if n == name]
    if not matched or matched[0] != action:
        raise ValueError("answer's command action does not match the evidence")
    other = [a for n, a in commands if n != name and a != action]
    if not other:
        raise ValueError("no distinct second command action available")
    _question_mentions(request.question, name, "指令")
    answer_after = (request.answer[:answer_command.start("action")]
                    + f"（{other[0]}）"
                    + request.answer[answer_command.end("action"):])
    return _proposal(request, evidence,
                     operator_id="ANSWER-TERM-05-COMMAND-SWAP-V1",
                     check_item="TERM-05", answer_after=answer_after,
                     proof_kind="explicit_command_action_mismatch",
                     proof=(f"evidence显式定义指令{name}（{matched[0]}）；"
                            f"answer换成了另一指令的动作{other[0]}。"))


def propose_interface_id_conflict(request: QAInput, *, evidence_id: str,
                                  ) -> AnswerMutationProposal:
    """Contradict an explicitly stated interface identifier (TERM-07)."""
    evidence = _find_evidence(request, evidence_id)
    evidence_ids = _INTERFACE_ID.findall(evidence.text)
    answer_id = _INTERFACE_ID.search(request.answer)
    if answer_id is None:
        raise ValueError("answer contains no interface identifier")
    if answer_id.group(0) not in evidence_ids:
        raise ValueError("answer identifier is not the evidenced one")
    altered = answer_id.group(0)[:-2] + "ZZ"
    if altered in evidence_ids or altered in request.answer:
        raise ValueError("mutated identifier collides with existing values")
    if not re.search(r"接口", evidence.text + request.answer):
        raise ValueError("operator applies only to interface identifiers")
    _question_mentions(request.question, "接口", answer_id.group(0))
    answer_after = (request.answer[:answer_id.start()] + altered
                    + request.answer[answer_id.end():])
    return _proposal(request, evidence,
                     operator_id="ANSWER-TERM-07-INTERFACE-CONFLICT-V1",
                     check_item="TERM-07", answer_after=answer_after,
                     proof_kind="explicit_interface_id_conflict",
                     proof=(f"evidence显式规定接口标识{answer_id.group(0)}；"
                            f"answer变异为{altered}，同实体标识显式冲突。"))


TERM_OPERATOR_STATUS: dict[str, str] = {
    "ANSWER-TERM-02-DEFINITION-SWAP-V1": "deterministic_prototype",
    "ANSWER-TERM-04-STATUS-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-TERM-05-COMMAND-SWAP-V1": "deterministic_prototype",
    "ANSWER-TERM-07-INTERFACE-CONFLICT-V1": "deterministic_prototype",
}

__all__ = [
    "propose_definition_swap",
    "propose_status_term_conflict",
    "propose_command_action_swap",
    "propose_interface_id_conflict",
    "TERM_OPERATOR_STATUS",
]
