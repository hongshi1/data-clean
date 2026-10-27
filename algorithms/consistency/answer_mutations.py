"""Answer-side controlled mutation proposals over a frozen QA/context input.

Question and retrieved context are immutable. Proposals without a deterministic
proof remain ``needs_review`` and never receive an automatic gold label.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

from algorithms.consistency.qa_models import QAInput, SourceRef
from algorithms.consistency.qa_router import route_question

MutationTarget = Literal["answer"]
MutationVerdict = Literal["support", "refute", "not_in_evidence"]


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
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _question_hash(request: QAInput) -> str:
    return hashlib.sha256(request.question.encode("utf-8")).hexdigest()


def _question_mentions_subject(question: str, subject: str) -> bool:
    q = re.sub(r"\s+", "", question)
    s = re.sub(r"\s+", "", subject)
    return bool(s and s in q)


def _numeric_check_item(request: QAInput) -> str:
    candidates = route_question(request.question)
    numeric = [item for item in candidates if item.startswith("PARAM-")]
    if not numeric:
        raise ValueError("question does not route to a numeric check item")
    return numeric[0]


def _numeric_equality(request: QAInput, evidence_id: str):
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    pattern = re.compile(
        r"(?P<subject>[\u4e00-\u9fffA-Za-z]{2,16})\s*(?:为|等于|=)\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节)?"
    )
    answer_match = pattern.search(request.answer)
    evidence_match = pattern.search(evidence.text)
    if not answer_match or not evidence_match:
        raise ValueError("operator requires an explicit numeric equality claim")
    subject = answer_match.group("subject")
    if subject != evidence_match.group("subject"):
        raise ValueError("answer/evidence parameter subjects do not match exactly")
    question_compact = re.sub(r"\s+", "", request.question)
    if subject not in question_compact:
        raise ValueError("question does not explicitly ask about the mutated parameter")
    answer_unit = answer_match.group("unit") or ""
    evidence_unit = evidence_match.group("unit") or ""
    if answer_unit != evidence_unit:
        raise ValueError("unit conversion is not supported by this equality operator")
    if float(answer_match.group("value")) != float(evidence_match.group("value")):
        raise ValueError("source answer is not numerically supported by selected evidence")
    return evidence, answer_match, evidence_match


def propose_numeric_identity(request: QAInput, *,
                             evidence_id: str) -> AnswerMutationProposal:
    """Keep the original answer as a deterministic support control."""
    evidence, answer_match, _evidence_match = _numeric_equality(request, evidence_id)
    return AnswerMutationProposal(
        operator_id="ANSWER-NUM-IDENTITY-V1",
        check_item=_numeric_check_item(request),
        source_instance_id=request.instance_id,
        question=request.question,
        answer_before=request.answer,
        answer_after=request.answer,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,),
        target="answer",
        gold_candidate="support",
        proof_kind="explicit_equality_match",
        proof=(f"question询问{answer_match.group('subject')}；answer与evidence均显式"
               f"声明{answer_match.group('value')}{answer_match.group('unit') or ''}。"),
        requires_manual_review=False,
    )


@dataclass(frozen=True)
class AnswerMutationProposal:
    operator_id: str
    check_item: str
    source_instance_id: str
    question: str
    answer_before: str
    answer_after: str
    context_freeze_id: str
    context_hash: str
    question_hash: str
    context_refs: tuple[SourceRef, ...]
    target: MutationTarget
    gold_candidate: MutationVerdict | None
    proof_kind: str
    proof: str
    requires_manual_review: bool


def propose_exact_numeric_conflict(
    request: QAInput,
    *,
    evidence_id: str,
    mutated_value: float,
) -> AnswerMutationProposal:
    """Propose refutation of one explicit numeric equality claim.

    This narrow operator only accepts an answer/evidence pair with the same
    parameter name and an explicit equality value; other forms require a
    type-specific operator and are rejected rather than guessed.
    """
    evidence, answer_match, evidence_match = _numeric_equality(request, evidence_id)
    source_value = float(evidence_match.group("value"))
    if float(mutated_value) == source_value:
        raise ValueError("mutated value must differ from the explicit evidence value")

    value_text = f"{mutated_value:g}"
    answer_after = (
        request.answer[:answer_match.start("value")]
        + value_text
        + request.answer[answer_match.end("value"):]
    )
    return AnswerMutationProposal(
        operator_id="ANSWER-NUM-EQ-CONFLICT-V1",
        check_item=_numeric_check_item(request),
        source_instance_id=request.instance_id,
        question=request.question,
        answer_before=request.answer,
        answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,),
        target="answer",
        gold_candidate="refute",
        proof_kind="explicit_equality_conflict",
        proof=(f"context显式声明{evidence_match.group('subject')}="
               f"{source_value:g}{evidence_match.group('unit') or ''}；"
               f"answer变异为{value_text}{answer_match.group('unit') or ''}；"
               "谓词、参数名和单位完全相同，显式等式冲突。"),
        requires_manual_review=False,
    )


def propose_unsupported_answer(
    request: QAInput,
    *,
    answer_after: str,
    operator_id: str,
    check_item: str,
) -> AnswerMutationProposal:
    """Create an NIE candidate only; absence cannot be proved automatically."""
    if not answer_after.strip() or answer_after == request.answer:
        raise ValueError("answer_after must be non-empty and differ from source answer")
    return AnswerMutationProposal(
        operator_id=operator_id,
        check_item=check_item,
        source_instance_id=request.instance_id,
        question=request.question,
        answer_before=request.answer,
        answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=tuple(e.source_ref for e in request.evidence),
        target="answer",
        gold_candidate=None,
        proof_kind="absence_candidate_unproven",
        proof="Answer已变异，但当前context未命中不能证明事实为假；需人工确认scope与合理蕴含后才能标NIE。",
        requires_manual_review=True,
    )


OPERATOR_STATUS: dict[str, str] = {
    "ANSWER-NUM-IDENTITY-V1": "deterministic_prototype",
    "ANSWER-NUM-EQ-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-NUM-EQUIV-V1": "deterministic_prototype",
    "ANSWER-QUOTE-EXPLICIT-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-ENUM-EXPLICIT-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-UNSUPPORTED-REVIEW": "candidate_manual_review_only",
    # Existing pair/multimodal mutations are not valid answer-side operators.
    "LEGACY-PAIR-MUTATIONS": "quarantined_legacy",
    "LEGACY-MMQA-CONTEXT-MUTATIONS": "quarantined_until_context_gold",
}


_UNIT_TO_BASE: dict[str, tuple[str, float]] = {
    "ms": ("time", 1.0), "毫秒": ("time", 1.0),
    "s": ("time", 1000.0), "秒": ("time", 1000.0),
    "min": ("time", 60000.0), "分钟": ("time", 60000.0),
    "B": ("storage", 1.0), "字节": ("storage", 1.0),
    "KB": ("storage", 1024.0), "MB": ("storage", 1048576.0),
    "GB": ("storage", 1073741824.0),
}


def propose_equivalent_numeric_surface(
    request: QAInput,
    *,
    evidence_id: str,
    target_unit: str,
) -> AnswerMutationProposal:
    """Rewrite an explicitly supported equality using an exactly equivalent unit."""
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    pattern = re.compile(
        r"(?P<subject>[\u4e00-\u9fffA-Za-z]{2,16})\s*(?:为|等于|=)\s*"
        r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节)"
    )
    answer_match = pattern.search(request.answer)
    evidence_match = pattern.search(evidence.text)
    if not answer_match or not evidence_match:
        raise ValueError("operator requires explicit numeric equality and units")
    if answer_match.group("subject") != evidence_match.group("subject"):
        raise ValueError("answer/evidence parameter subjects do not match exactly")
    if not _question_mentions_subject(request.question, answer_match.group("subject")):
        raise ValueError("question does not ask about the mutated parameter")
    source_unit = evidence_match.group("unit")
    answer_unit = answer_match.group("unit")
    target = target_unit.strip()
    if any(unit not in _UNIT_TO_BASE for unit in (source_unit, answer_unit, target)):
        raise ValueError("unit is not in the frozen conversion table")
    source_family, source_factor = _UNIT_TO_BASE[source_unit]
    answer_family, answer_factor = _UNIT_TO_BASE[answer_unit]
    target_family, target_factor = _UNIT_TO_BASE[target]
    if len({source_family, answer_family, target_family}) != 1:
        raise ValueError("unit families do not match")
    source_base = float(evidence_match.group("value")) * source_factor
    answer_base = float(answer_match.group("value")) * answer_factor
    if abs(source_base - answer_base) > max(abs(source_base), 1.0) * 1e-9:
        raise ValueError("source answer is not numerically supported by selected evidence")
    target_value = source_base / target_factor
    value_text = f"{target_value:g}"
    answer_after = (
        request.answer[:answer_match.start("value")]
        + value_text + target
        + request.answer[answer_match.end("unit"):]
    )
    return AnswerMutationProposal(
        operator_id="ANSWER-NUM-EQUIV-V1",
        check_item=(_numeric_check_item(request)
                    if any(item.startswith("PARAM-")
                           for item in route_question(request.question))
                    else "TERM-06"),
        source_instance_id=request.instance_id,
        question=request.question,
        answer_before=request.answer,
        answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,),
        target="answer",
        gold_candidate="support",
        proof_kind="unit_conversion_equality",
        proof=(f"context {evidence_match.group('value')}{source_unit}="
               f"answer {answer_match.group('value')}{answer_unit}="
               f"变异answer {value_text}{target}；使用冻结单位换算表。"),
        requires_manual_review=False,
    )


def _quoted_term(text: str) -> tuple[str, int, int]:
    match = re.search(r"[「\"](?P<term>[^「」\"]{2,80})[」\"]", text)
    if not match:
        raise ValueError("operator requires an explicit quoted answer term")
    return match.group("term"), match.start("term"), match.end("term")


def propose_explicit_quote_conflict(
    request: QAInput,
    *,
    evidence_id: str,
    contradicted_term: str,
) -> AnswerMutationProposal:
    """Replace an answer quote with a term explicitly denied by evidence."""
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    _source_term, start, end = _quoted_term(request.answer)
    target = contradicted_term.strip()
    if len(target) < 2 or target == _source_term:
        raise ValueError("contradicted_term must differ from the source quote")
    normalized = re.sub(r"\s+", "", evidence.text)
    target_pos = normalized.find(target)
    if target_pos < 0:
        raise ValueError("evidence does not mention the contradicted term")
    prefix = normalized[max(0, target_pos - 14):target_pos]
    if not re.search(r"(?:不包括|不包含|不支持|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)", prefix):
        raise ValueError("evidence does not explicitly negate the contradicted term")
    answer_after = request.answer[:start] + target + request.answer[end:]
    return AnswerMutationProposal(
        operator_id="ANSWER-QUOTE-EXPLICIT-CONFLICT-V1",
        check_item="TERM-01",
        source_instance_id=request.instance_id,
        question=request.question,
        answer_before=request.answer,
        answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,),
        target="answer",
        gold_candidate="refute",
        proof_kind="explicit_quote_negation",
        proof=f"context显式否定「{target}」；answer变异后声称包含该项。",
        requires_manual_review=False,
    )


def propose_enum_explicit_conflict(
    request: QAInput,
    *,
    evidence_id: str,
    added_term: str,
) -> AnswerMutationProposal:
    """Add a term to an answer when evidence explicitly excludes it."""
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    target = added_term.strip()
    if len(target) < 2 or target in request.answer:
        raise ValueError("added_term must be new and non-empty")
    normalized = re.sub(r"\s+", "", evidence.text)
    target_pos = normalized.find(target)
    if target_pos < 0:
        raise ValueError("evidence does not mention the added term")
    prefix = normalized[max(0, target_pos - 14):target_pos]
    if not re.search(r"(?:不包括|不包含|不支持|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)", prefix):
        raise ValueError("evidence does not explicitly exclude the added term")
    answer_after = f"{request.answer.rstrip('。')}、{target}。"
    return AnswerMutationProposal(
        operator_id="ANSWER-ENUM-EXPLICIT-CONFLICT-V1",
        check_item="TERM-03",
        source_instance_id=request.instance_id,
        question=request.question,
        answer_before=request.answer,
        answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,),
        target="answer",
        gold_candidate="refute",
        proof_kind="explicit_enum_exclusion",
        proof=f"context显式排除「{target}」；answer变异后将其加入枚举。",
        requires_manual_review=False,
    )


def propose_abbreviation_expansion(
    request: QAInput, *, evidence_id: str,
) -> AnswerMutationProposal:
    """Expand an acronym only when the same evidence explicitly defines it."""
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    match = re.search(r"(?P<abbr>[A-Z][A-Z0-9-]{1,15})\s*[（(](?P<full>[^）)；;]{2,80})[）)]", evidence.text)
    if not match:
        raise ValueError("evidence must explicitly define acronym followed by its full form")
    abbr, full = match.group("abbr"), match.group("full").strip()
    answer_term, start, end = _quoted_term(request.answer)
    if answer_term != abbr or not _question_mentions_subject(request.question, abbr):
        raise ValueError("answer must quote the explicitly defined acronym asked by question")
    return AnswerMutationProposal(
        operator_id="ANSWER-TERM-08-EXPANSION-V1", check_item="TERM-08",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer,
        answer_after=request.answer[:start] + full + request.answer[end:],
        context_freeze_id=request.context_freeze_id, context_hash=_context_hash(request),
        question_hash=_question_hash(request), context_refs=(evidence.source_ref,),
        target="answer", gold_candidate="support", proof_kind="explicit_acronym_definition",
        proof=f"evidence显式定义{abbr}（{full}）；answer展开为该全称。",
        requires_manual_review=False,
    )


def propose_out_of_range_conflict(
    request: QAInput, *, evidence_id: str, mutated_value: float,
) -> AnswerMutationProposal:
    """Move an explicitly stated numeric answer outside its evidenced range."""
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    pattern = re.compile(
        r"(?P<subject>[\u4e00-\u9fffA-Za-z]{2,16}?)\s*(?:为|等于|=)?\s*"
        r"(?P<lo>\d+(?:\.\d+)?)\s*(?:至|到|~|～|-)\s*"
        r"(?P<hi>\d+(?:\.\d+)?)\s*(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节)?"
    )
    range_match = pattern.search(evidence.text)
    answer_match = re.search(r"(?P<subject>[\u4e00-\u9fffA-Za-z]{2,16})\s*(?:为|等于|=)\s*(?P<value>\d+(?:\.\d+)?)(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节)?", request.answer)
    if not range_match or not answer_match:
        raise ValueError("operator requires explicit numeric range and equality answer")
    range_subject = re.sub(r"(?:范围|要求|应为)$", "", range_match.group("subject"))
    if range_subject != answer_match.group("subject"):
        raise ValueError("answer/evidence parameter subjects do not match exactly")
    if not _question_mentions_subject(request.question, answer_match.group("subject")):
        raise ValueError("question does not ask about the ranged parameter")
    if (range_match.group("unit") or "") != (answer_match.group("unit") or ""):
        raise ValueError("range and answer units must match exactly")
    lo, hi = float(range_match.group("lo")), float(range_match.group("hi"))
    if lo > hi:
        raise ValueError("range lower bound exceeds upper bound")
    if lo <= mutated_value <= hi:
        raise ValueError("mutated value remains inside the explicit range")
    value_text = f"{mutated_value:g}"
    answer_after = request.answer[:answer_match.start("value")] + value_text + request.answer[answer_match.end("value"):]
    return AnswerMutationProposal(
        operator_id="ANSWER-PARAM-06-OUT-OF-RANGE-V1", check_item="PARAM-06",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id, context_hash=_context_hash(request),
        question_hash=_question_hash(request), context_refs=(evidence.source_ref,),
        target="answer", gold_candidate="refute", proof_kind="explicit_range_violation",
        proof=f"evidence规定闭区间[{lo:g}, {hi:g}]；变异值{value_text}在区间外。",
        requires_manual_review=False,
    )


def propose_reversed_data_flow(
    request: QAInput, *, evidence_id: str,
) -> AnswerMutationProposal:
    """Reverse one explicit directed data-flow claim."""
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    match = re.search(r"(?P<src>[A-Z][A-Za-z0-9_-]{0,23}|[\u4e00-\u9fff]{2,8})\s*(?:向|发送至|传输至)\s*(?P<dst>[A-Z][A-Za-z0-9_-]{0,23}|[\u4e00-\u9fff]{2,8})", evidence.text)
    if not match:
        raise ValueError("evidence must state an explicit directed data flow")
    src, dst = match.group("src"), match.group("dst")
    answer_match = re.search(re.escape(src) + r"\s*(?:向|发送至|传输至)\s*" + re.escape(dst), request.answer)
    if not answer_match or not _question_mentions_subject(request.question, src):
        raise ValueError("answer/question must refer to the explicit source flow")
    answer_after = request.answer[:answer_match.start()] + f"{dst}向{src}" + request.answer[answer_match.end():]
    return AnswerMutationProposal(
        operator_id="ANSWER-LOGIC-04-REVERSED-FLOW-V1", check_item="LOGIC-04",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id, context_hash=_context_hash(request),
        question_hash=_question_hash(request), context_refs=(evidence.source_ref,),
        target="answer", gold_candidate="refute", proof_kind="explicit_flow_direction_conflict",
        proof=f"evidence显式规定{src}向{dst}；answer反转为{dst}向{src}。",
        requires_manual_review=False,
    )
