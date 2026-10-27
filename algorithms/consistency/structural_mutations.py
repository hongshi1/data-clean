"""Conservative answer-only structural mutation operators.

These operators intentionally accept only explicit, closed evidence.  They do
not infer list membership, sequence completeness, or exception exclusivity.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from algorithms.consistency.answer_mutations import AnswerMutationProposal
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence


def _context_hash(request: QAInput) -> str:
    payload = [{
        "evidence_id": e.evidence_id,
        "text": e.text,
        "source_type": e.source_type,
        "source_ref": e.source_ref.__dict__,
        "scope_id": e.scope_id,
        "completeness": e.completeness,
        "completeness_proof": e.completeness_proof,
    } for e in request.evidence]
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True
    ).encode("utf-8")).hexdigest()


def _question_hash(request: QAInput) -> str:
    return hashlib.sha256(request.question.encode("utf-8")).hexdigest()


def _evidence(request: QAInput, evidence_id: str) -> RetrievedEvidence:
    evidence = next((item for item in request.evidence
                     if item.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    if evidence.completeness != "closed":
        raise ValueError("structural mutation requires closed completeness")
    if not evidence.completeness_proof.strip():
        raise ValueError("closed evidence requires a non-empty completeness proof")
    return evidence


@dataclass(frozen=True)
class _Enumeration:
    items: tuple[str, ...]
    start: int
    end: int
    separator: str


_ENUM_MARKER = re.compile(
    r"(?:包括|包含|枚举为|清单为|成员为|参与者为|角色为|actors?\s*are|roles?\s*are)"
    r"\s*[:：]?\s*"
)

_EXHAUSTIVE_MARKER = re.compile(
    r"(?:清单为|枚举为|全部(?:包括|为)?|所有(?:包括|为)?|完整(?:清单|列表)?|"
    r"仅包括|仅有|共\s*\d+\s*项)"
)
_ACTOR_ROLE_MARKER = re.compile(r"(?:参与者|角色|actor|role)", re.IGNORECASE)


def _split_items(raw: str) -> tuple[tuple[str, ...], str]:
    separator_match = re.search(r"([、,，;；])", raw)
    if separator_match is None:
        raise ValueError("evidence does not contain an explicit enumeration")
    separator = separator_match.group(1)
    values = tuple(re.sub(r"^\s*(?:\d+[.)、]|[-*])\s*", "", part).strip()
                   for part in re.split(r"\s*[、,，;；]\s*", raw))
    values = tuple(value.rstrip("。．.") for value in values if value.strip())
    if not values or len(set(values)) != len(values):
        raise ValueError("enumeration is empty or contains duplicate members")
    return values, separator


def _enumeration(text: str) -> _Enumeration:
    bracket = re.search(r"[\[【](?P<body>[^\]】]+)[\]】]", text)
    if bracket is not None:
        raw = bracket.group("body")
        items, separator = _split_items(raw)
        return _Enumeration(items, bracket.start("body"), bracket.end("body"), separator)
    marker = _ENUM_MARKER.search(text)
    if marker is None:
        raise ValueError("text has no explicit enumeration marker")
    end_match = re.search(r"[。.!！？\n]", text[marker.end():])
    end = marker.end() + (end_match.start() if end_match else len(text[marker.end():]))
    raw = text[marker.end():end].strip()
    leading = len(text[marker.end():end]) - len(text[marker.end():end].lstrip())
    items, separator = _split_items(raw)
    start = marker.end() + leading
    return _Enumeration(items, start, end, separator)


def _enumeration_subject(text: str, enumeration: _Enumeration) -> str:
    subject = text[:enumeration.start]
    subject = re.sub(r"[：:，,、；;\s]+$", "", subject)
    return subject.strip()


def _same_enumeration_subject(text: str, first: _Enumeration,
                              second_text: str, second: _Enumeration) -> bool:
    return _enumeration_subject(text, first) == _enumeration_subject(
        second_text, second
    )


def _question_requests_enumeration(question: str, subject: str) -> bool:
    compact_question = re.sub(r"\s+", "", question)
    compact_subject = re.sub(r"(?:清单|列表|枚举|包括|包含|为)$", "", re.sub(r"\s+", "", subject))
    asks_for_members = re.search(
        r"(?:有哪些|包含哪些|包括哪些|列出|枚举|哪些|what\s+are|which)",
        question,
        re.IGNORECASE,
    )
    subject_terms = tuple(term for term in re.split(r"[：:，,、；;\s]+", compact_subject)
                          if term)
    subject_matches = compact_subject in compact_question or (
        len(subject_terms) == 1 and subject_terms[0] in compact_question
    )
    return bool(subject_matches and asks_for_members)


def _proposal(request: QAInput, evidence: RetrievedEvidence, *, operator_id: str,
              check_item: str, answer_after: str, proof_kind: str,
              proof: str, verdict: Literal["support", "refute"]
              = "refute") -> AnswerMutationProposal:
    if answer_after == request.answer:
        raise ValueError("mutation must change the answer")
    return AnswerMutationProposal(
        operator_id=operator_id, check_item=check_item,
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer", gold_candidate=verdict,
        proof_kind=proof_kind, proof=proof, requires_manual_review=False,
    )


def _mutate_list(request: QAInput, evidence_id: str, member: str, *, remove: bool,
                 operator_id: str, check_item: str) -> AnswerMutationProposal:
    evidence = _evidence(request, evidence_id)
    source = _enumeration(evidence.text)
    answer = _enumeration(request.answer)
    member = member.strip()
    if not member:
        raise ValueError("member must be non-empty")
    if not _same_enumeration_subject(evidence.text, source, request.answer, answer):
        raise ValueError("answer and evidence must have the same explicit list subject")
    subject = _enumeration_subject(evidence.text, source)
    asks_actor_members = bool(
        _ACTOR_ROLE_MARKER.search(request.question)
        and re.search(r"(?:有哪些|哪些|列出|枚举|what\s+are|which)",
                      request.question, re.IGNORECASE)
    )
    if (not remove and not _question_requests_enumeration(request.question, subject)
            and not asks_actor_members):
        raise ValueError("supporting list addition requires a question explicitly asking for members")
    if remove:
        if (not _EXHAUSTIVE_MARKER.search(request.answer)
                or answer.items != source.items):
            raise ValueError("answer must be an exhaustive exact copy of the closed evidence set")
        if member not in answer.items:
            raise ValueError("removed member is not an explicitly evidenced answer member")
        if len(answer.items) == 1:
            raise ValueError("cannot create an empty answer enumeration")
        items = tuple(item for item in answer.items if item != member)
        action = f"remove {member!r}"
    else:
        missing = set(source.items) - set(answer.items)
        if (not set(answer.items) < set(source.items)
                or missing != {member}):
            raise ValueError(
                "answer must be a proper subset of the closed evidence set with one missing member"
            )
        items = source.items
        action = f"add {member!r}"
    replacement = answer.separator.join(items)
    after = request.answer[:answer.start] + replacement + request.answer[answer.end:]
    return _proposal(
        request, evidence, operator_id=operator_id, check_item=check_item,
        answer_after=after, proof_kind="closed_explicit_enumeration_mutation",
        proof=(f"Closed evidence explicitly enumerates {source.items!r}; "
               f"answer enumeration is {answer.items!r}; deterministic operation: {action}. "
               f"Completeness proof: {evidence.completeness_proof.strip()}"),
        verdict="refute" if remove else "support",
    )


def propose_closed_list_add(request: QAInput, *, evidence_id: str,
                            member: str) -> AnswerMutationProposal:
    """Add one member that is explicitly present in a closed evidence list."""
    return _mutate_list(request, evidence_id, member, remove=False,
                        operator_id="ANSWER-STRUCT-CLOSED-LIST-ADD-SUPPORT-V2",
                        check_item="TERM-03")


def propose_closed_list_remove(request: QAInput, *, evidence_id: str,
                               member: str) -> AnswerMutationProposal:
    """Remove one member from an answer backed by a closed evidence list."""
    return _mutate_list(request, evidence_id, member, remove=True,
                        operator_id="ANSWER-STRUCT-CLOSED-LIST-REMOVE-V1",
                        check_item="TERM-03")


_STEP = re.compile(r"(?:^|[;；\n])\s*(\d+)\s*[.)、:：]\s*([^;；\n。]+)")


def _steps(text: str) -> tuple[tuple[str, str, int, int], ...]:
    found = tuple((match.group(1), match.group(2).strip(), match.start(2), match.end(2))
                  for match in _STEP.finditer(text))
    if len(found) < 2 or [int(item[0]) for item in found] != list(range(1, len(found) + 1)):
        raise ValueError("text must contain an explicit contiguous ordered step sequence")
    return found


def _step_answer(request: QAInput, evidence_id: str) -> tuple[RetrievedEvidence, tuple, tuple]:
    evidence = _evidence(request, evidence_id)
    evidence_steps = _steps(evidence.text)
    answer_steps = _steps(request.answer)
    if tuple(item[1] for item in evidence_steps) != tuple(item[1] for item in answer_steps):
        raise ValueError("answer steps are not aligned with the explicit evidence sequence")
    return evidence, evidence_steps, answer_steps


_ORDER_MARKER = re.compile(r"先|然后|最后|必须按顺序|precedence", re.IGNORECASE)
_MANDATORY_MARKER = re.compile(
    r"必须|应当|需要|要求|必需|mandatory|required", re.IGNORECASE
)


def propose_step_reorder(request: QAInput, *, evidence_id: str,
                         first_step: int, second_step: int) -> AnswerMutationProposal:
    evidence, _evidence_steps, answer_steps = _step_answer(request, evidence_id)
    if _ORDER_MARKER.search(evidence.text) is None:
        raise ValueError("evidence has no explicit normative order marker")
    count = len(answer_steps)
    if first_step == second_step or not (1 <= first_step <= count and 1 <= second_step <= count):
        raise ValueError("step positions must be distinct and in range")
    values = [item[1] for item in answer_steps]
    values[first_step - 1], values[second_step - 1] = values[second_step - 1], values[first_step - 1]
    after = re.sub(r"(?<=\d[.)、:：])\s*[^;；\n。]+",
                   lambda match: match.group(0), request.answer)
    # Rebuild only the explicit numbered sequence, preserving its separators.
    matches = list(_STEP.finditer(request.answer))
    for match, value in reversed(list(zip(matches, values))):
        after = after[:match.start(2)] + value + after[match.end(2):]
    return _proposal(
        request, evidence, operator_id="ANSWER-STRUCT-STEP-REORDER-V1", check_item="LOGIC-05",
        answer_after=after, proof_kind="explicit_aligned_step_reorder",
        proof=(f"Closed evidence and answer align on ordered steps; positions {first_step} and "
               f"{second_step} are swapped. Completeness proof: {evidence.completeness_proof.strip()}"),
    )


def propose_step_delete(request: QAInput, *, evidence_id: str,
                        step_number: int) -> AnswerMutationProposal:
    evidence, evidence_steps, answer_steps = _step_answer(request, evidence_id)
    if not 1 <= step_number <= len(answer_steps):
        raise ValueError("step number is out of range")
    if len(answer_steps) == 2:
        raise ValueError("deletion would leave an underspecified one-step sequence")
    target = answer_steps[step_number - 1][1]
    target_evidence = evidence_steps[step_number - 1][1]
    if _MANDATORY_MARKER.search(target_evidence) is None:
        raise ValueError("target step is not explicitly mandatory in evidence")
    matches = list(_STEP.finditer(request.answer))
    match = matches[step_number - 1]
    next_start = matches[step_number].start() if step_number < len(matches) else len(request.answer)
    after = request.answer[:match.start()] + request.answer[next_start:]
    remaining = list(_STEP.finditer(after))
    for new_number, remaining_match in reversed(list(enumerate(remaining, start=1))):
        after = (after[:remaining_match.start(1)] + str(new_number)
                 + after[remaining_match.end(1):])
    return _proposal(
        request, evidence, operator_id="ANSWER-STRUCT-STEP-DELETE-V1", check_item="LOGIC-05",
        answer_after=after, proof_kind="closed_explicit_mandatory_step_deletion",
        proof=(f"Closed evidence explicitly enumerates the complete ordered sequence "
               f"{tuple(item[1] for item in evidence_steps)!r}; deleted mandatory step "
               f"{step_number}: {target!r}. Completeness proof: {evidence.completeness_proof.strip()}"),
    )


def propose_exception_outcome_swap(request: QAInput, *, evidence_id: str,
                                   mutated_outcome: str) -> AnswerMutationProposal:
    """Replace an answer outcome only when evidence explicitly excludes it."""
    evidence = _evidence(request, evidence_id)
    outcome = mutated_outcome.strip()
    if not outcome:
        raise ValueError("mutated_outcome must be non-empty")
    condition_match = re.search(r"(?:发生|当|若|如果)\s*(?P<condition>[^，,；;时]+)\s*(?:时|情况下)", evidence.text)
    answer_condition = re.search(
        r"(?:发生|当|若|如果)\s*(?P<condition>[^，,；;时]+)\s*(?:时|情况下)",
        request.answer,
    )
    if (condition_match is None or answer_condition is None
            or condition_match.group("condition").strip()
            != answer_condition.group("condition").strip()):
        raise ValueError("evidence and answer must share an explicit exception condition")
    explicit_prohibition = re.search(
        r"(?:不得|禁止|不能|不可|不应|不允许)\s*(?:执行|采取|选择)?\s*"
        + re.escape(outcome), evidence.text
    )
    exclusive = re.search(
        r"(?:只能|仅能)\s*(?:执行|采取|选择)?\s*(?P<only>[^，,。；;]+)",
        evidence.text,
    )
    if explicit_prohibition is None and (
        exclusive is None or exclusive.group("only").strip() == outcome
    ):
        raise ValueError("evidence does not explicitly exclude the mutated outcome")
    answer_outcome = re.search(r"(?:应|应该|必须|采取|执行|选择)\s*(?P<outcome>[^，,。；;]+)", request.answer)
    if answer_outcome is None or answer_outcome.group("outcome").strip() == outcome:
        raise ValueError("answer has no distinct explicit outcome to swap")
    after = request.answer[:answer_outcome.start("outcome")] + outcome + request.answer[answer_outcome.end("outcome"):]
    return _proposal(
        request, evidence, operator_id="ANSWER-STRUCT-EXCEPTION-OUTCOME-SWAP-V1", check_item="LOGIC-06",
        answer_after=after, proof_kind="explicit_exception_outcome_exclusion",
        proof=(f"Same explicit condition {condition_match.group('condition').strip()!r}; evidence "
               f"explicitly excludes outcome {outcome!r}. No retry/fallback/terminate exclusivity "
               "is inferred beyond that wording."),
    )


def propose_actor_role_list_mutation(request: QAInput, *, evidence_id: str,
                                     member: str, remove: bool = False) -> AnswerMutationProposal:
    """Add or remove an actor/role only from an explicitly closed actor set."""
    if not all(_ACTOR_ROLE_MARKER.search(text) for text in (
            request.question, request.answer,
            _evidence(request, evidence_id).text)):
        raise ValueError("question, answer, and evidence must explicitly name actors or roles")
    return _mutate_list(request, evidence_id, member, remove=remove,
                        operator_id=("ANSWER-STRUCT-ACTOR-REMOVE-REFUTE-V2" if remove
                                     else "ANSWER-STRUCT-ACTOR-ADD-SUPPORT-V2"),
                        check_item="TERM-03")


__all__ = [
    "propose_closed_list_add", "propose_closed_list_remove",
    "propose_step_reorder", "propose_step_delete",
    "propose_exception_outcome_swap", "propose_actor_role_list_mutation",
]
