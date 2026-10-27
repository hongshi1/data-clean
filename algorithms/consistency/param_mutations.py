"""PARAM-family answer-only mutation operators with numeric proof gates.

Every refute requires an explicit numeric contradiction: the mutated claim's
interval must be disjoint from the evidence interval after subject/operator/
unit alignment. Unprovable shapes raise ValueError and never emit gold.
"""
from __future__ import annotations

import re

from algorithms.consistency.answer_mutations import (
    AnswerMutationProposal,
    _UNIT_TO_BASE,
    _context_hash,
    _question_hash,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence

_CLAIM = re.compile(
    r"(?P<subject>[\u4e00-\u9fffA-Za-z]{2,16}?)\s*"
    r"(?P<op>不大于|不超过|不高于|最多|至多|不小于|不少于|不低于|至少|大于等于|"
    r"大于|超过|小于|为|等于|=)\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>ms|毫秒|s|秒|min|分钟|h|小时|天|GB|MB|KB|B|字节|%)?"
)

_LE_OPS = {"不大于", "不超过", "不高于", "最多", "至多"}
_GE_OPS = {"不小于", "不少于", "不低于", "至少", "大于等于"}
_GT_OPS = {"大于", "超过"}
_LT_OPS = {"小于"}
_EQ_OPS = {"为", "等于", "="}


def _interval(op: str, value: float) -> tuple[float, bool, float, bool]:
    if op in _LE_OPS:
        return float("-inf"), False, value, True
    if op in _LT_OPS:
        return float("-inf"), False, value, False
    if op in _GE_OPS:
        return value, True, float("inf"), False
    if op in _GT_OPS:
        return value, False, float("inf"), False
    return value, True, value, True


def _disjoint(a: tuple[float, bool, float, bool],
              b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    a_first = au < bl or (au == bl and not (auc and blc))
    b_first = bu < al or (bu == al and not (buc and alc))
    return a_first or b_first


def _find_evidence(request: QAInput, evidence_id: str) -> RetrievedEvidence:
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    return evidence


def _clean_subject(subject: str) -> str:
    return re.sub(r"\s+", "", subject).removesuffix("的")


def _aligned_claims(evidence_text: str, answer_text: str, question: str,
                    keywords: tuple[str, ...]):
    q_compact = re.sub(r"\s+", "", question)
    if not any(keyword in q_compact for keyword in keywords):
        raise ValueError("question does not mention the mutated parameter")
    evidence_match = None
    for match in _CLAIM.finditer(evidence_text):
        if any(keyword in match.group("subject") for keyword in keywords):
            evidence_match = match
            break
    if evidence_match is None:
        raise ValueError("evidence has no numeric claim for this parameter family")
    ev_clean = _clean_subject(evidence_match.group("subject"))
    answer_match = None
    for match in _CLAIM.finditer(answer_text):
        an_clean = _clean_subject(match.group("subject"))
        if an_clean == ev_clean:
            answer_match = match
            break
        if an_clean in ev_clean or ev_clean in an_clean:
            shorter = an_clean if len(an_clean) < len(ev_clean) else ev_clean
            if shorter in q_compact:
                answer_match = match
                break
    if answer_match is None:
        raise ValueError("answer has no aligned numeric claim for the evidence subject")
    return evidence_match, answer_match


def _unit_family(unit: str) -> tuple[str, float]:
    if unit in _UNIT_TO_BASE:
        return _UNIT_TO_BASE[unit]
    raise ValueError(f"unit not in frozen table: {unit or '(none)'}")


def propose_numeric_conflict(request: QAInput, *, evidence_id: str,
                             mutated_value: float,
                             check_item: str, operator_id: str,
                             subject_keywords: tuple[str, ...],
                             ) -> AnswerMutationProposal:
    """Rewrite one aligned numeric claim into an explicit conflicting equality."""
    evidence = _find_evidence(request, evidence_id)
    evidence_match, answer_match = _aligned_claims(
        evidence.text, request.answer, request.question, subject_keywords)
    ev_unit = _unit_family(evidence_match.group("unit") or "")
    an_unit = _unit_family(answer_match.group("unit") or "")
    if ev_unit[0] != an_unit[0]:
        raise ValueError("evidence and answer units are from different families")
    ev_value = float(evidence_match.group("value")) * ev_unit[1]
    an_value = float(answer_match.group("value")) * an_unit[1]
    ev_interval = _interval(evidence_match.group("op"), ev_value)
    an_interval = _interval(answer_match.group("op"), an_value)
    if _disjoint(ev_interval, an_interval):
        raise ValueError("source answer already conflicts with evidence")
    mutated_base = float(mutated_value) * an_unit[1]
    if not _disjoint(ev_interval, (mutated_base, True, mutated_base, True)):
        raise ValueError("mutated value does not contradict the evidence interval")
    value_text = f"{mutated_value:g}"
    replacement = (f"{answer_match.group('subject')}为{value_text}"
                   f"{answer_match.group('unit') or ''}")
    answer_after = (request.answer[:answer_match.start()]
                    + replacement
                    + request.answer[answer_match.end():])
    ev_op = evidence_match.group("op")
    return AnswerMutationProposal(
        operator_id=operator_id, check_item=check_item,
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="refute", proof_kind="numeric_interval_disjoint",
        proof=(f"evidence显式约束{evidence_match.group('subject')}{ev_op}"
               f"{evidence_match.group('value')}{evidence_match.group('unit') or ''}；"
               f"answer变异为{value_text}{answer_match.group('unit') or ''}，"
               "两者数值区间互斥，显式冲突。"),
        requires_manual_review=False,
    )


def propose_numeric_equivalent(request: QAInput, *, evidence_id: str,
                               target_unit: str,
                               check_item: str = "TERM-06",
                               ) -> AnswerMutationProposal:
    """Rewrite one aligned numeric claim into an exactly equivalent unit surface."""
    evidence = _find_evidence(request, evidence_id)
    evidence_match, answer_match = _aligned_claims(
        evidence.text, request.answer, request.question,
        ("时间", "周期", "阈值", "容量", "精度", "占用", "时长", "大小", "数量", "上限", "下限", "误差"))
    source_unit = answer_match.group("unit") or ""
    target = target_unit.strip()
    source_family, source_factor = _unit_family(source_unit)
    target_family, target_factor = _unit_family(target)
    if source_family != target_family:
        raise ValueError("unit families do not match")
    source_base = float(answer_match.group("value")) * source_factor
    target_value = source_base / target_factor
    if abs(target_value - round(target_value, 6)) > 1e-9 and target_value < 1:
        value_text = f"{target_value:.6f}".rstrip("0").rstrip(".")
    else:
        value_text = f"{target_value:g}"
    answer_after = (request.answer[:answer_match.start("value")]
                    + value_text + target
                    + request.answer[answer_match.end("unit"):])
    return AnswerMutationProposal(
        operator_id="ANSWER-PARAM-NUM-EQUIV-SUPPORT-V1", check_item=check_item,
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request),
        question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="support", proof_kind="unit_conversion_equality",
        proof=(f"{answer_match.group('value')}{source_unit}与{value_text}{target}"
               "按冻结单位换算表等价。"),
        requires_manual_review=False,
    )


_PARAM_FAMILIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("PARAM-01", "ANSWER-PARAM-01-TIME-CONFLICT-V1",
     ("响应时间", "处理时间", "时延", "延迟", "时间")),
    ("PARAM-02", "ANSWER-PARAM-02-PERIOD-CONFLICT-V1",
     ("周期", "频率", "间隔")),
    ("PARAM-03", "ANSWER-PARAM-03-THRESHOLD-CONFLICT-V1",
     ("阈值", "门限")),
    ("PARAM-05", "ANSWER-PARAM-05-RESOURCE-CONFLICT-V1",
     ("CPU", "内存", "磁盘", "占用", "带宽")),
    ("PARAM-07", "ANSWER-PARAM-07-RETENTION-CONFLICT-V1",
     ("保存时长", "保存期限", "保留", "存储容量", "容量")),
    ("PARAM-08", "ANSWER-PARAM-08-SYNC-CONFLICT-V1",
     ("同步精度", "同步误差", "守时", "对齐误差", "误差")),
    ("PARAM-09", "ANSWER-PARAM-09-DEGRADE-CONFLICT-V1",
     ("降级", "触发")),
    ("PARAM-10", "ANSWER-PARAM-10-FAULT-CONFLICT-V1",
     ("故障", "持续", "判定")),
)


def param_operator_registry() -> dict[str, tuple]:
    """check_item -> (callable, operator_id, subject keywords)."""
    return {
        check_item: (propose_numeric_conflict, operator_id, keywords)
        for check_item, operator_id, keywords in _PARAM_FAMILIES
    }


PARAM_OPERATOR_STATUS: dict[str, str] = {
    operator_id: "deterministic_prototype"
    for _item, operator_id, _keywords in _PARAM_FAMILIES
} | {"ANSWER-PARAM-NUM-EQUIV-SUPPORT-V1": "deterministic_prototype"}


def propose_param_conflict_for(request: QAInput, *, evidence_id: str,
                               check_item: str, mutated_value: float,
                               ) -> AnswerMutationProposal:
    registry = param_operator_registry()
    if check_item not in registry:
        raise ValueError(f"unknown PARAM check_item: {check_item}")
    operator, operator_id, keywords = registry[check_item]
    return operator(request, evidence_id=evidence_id,
                    mutated_value=mutated_value, check_item=check_item,
                    operator_id=operator_id, subject_keywords=keywords)


__all__ = [
    "propose_numeric_conflict",
    "propose_numeric_equivalent",
    "propose_param_conflict_for",
    "param_operator_registry",
    "PARAM_OPERATOR_STATUS",
]
