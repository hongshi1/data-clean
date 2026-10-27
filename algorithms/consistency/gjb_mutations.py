"""GJB-01..GJB-11 answer-only B-fact-verification mutation operators.

B-task semantics: the mutated answer claims SRS facts (mechanisms, fields,
trace mappings, capabilities) and only evidence that explicitly proves the
opposite yields a deterministic refutation.  GJB rule-compliance checking
(subtask C) is out of scope; rule text may still enter the frozen context as
evidence, and must then declare ``source_type="rule"``.

Hard rules enforced by every operator:
- closed-list refutation requires an explicit enumeration marker
  (包括/仅包括/以下/...) plus ``completeness="closed"`` and a non-empty
  ``completeness_proof``;
- open/unknown evidence, a list ending with 等, or a term that surfaces in
  the evidence text never yields ``refute``: the operator raises
  ``ValueError`` and defers the case to manual review;
- GJB-05 conflicts an explicit positive trace mapping (需求ID→测试项), so it
  needs no closedness proof;
- the question must mention the mutated subject; question and context stay
  frozen and every proposal carries proof, hashes and context refs.
"""
from __future__ import annotations

import hashlib
import json
import re

from algorithms.consistency.answer_mutations import AnswerMutationProposal
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence

_ENUM_MARKER = re.compile(
    r"(?<![不未无非])(?:仅包括|仅包含|只包括|只包含|包括|包含|如下|以下|分为)")
_ENUM_PREFIX = re.compile(r"^以下[^：:、，,；;]{0,4}[：:]")
_NUMBERING = re.compile(
    r"^(?:[0-9]{1,3}[)）]|[A-Za-z][)）.．]|[（(][0-9A-Za-z]{1,4}[)）])")
_TRAILING_COUNT = re.compile(r"(?:等|[一二三四五六七八九十两]+(?:种|项|个|类))$")
_ANSWER_ENUM_WORDS: tuple[str, ...] = ("包括", "包含", "记录")
_QUALITATIVE_MARKERS: tuple[str, ...] = (
    "及时", "快速", "迅速", "准确", "可靠", "稳定", "有效", "连续", "完整")
_QUANT_UNIT = re.compile(r"(?:ms|毫秒|秒|分钟|min|GB|MB|KB|%|％)")
_NEGATION = re.compile(
    r"(?:不包括|不包含|不支持|不提供|未提供|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)")
_TRACE_VERBS = r"(?:→|->|映射到|映射至|对应|追溯至|追溯到)"
_TEST_ID = r"[A-Za-z][A-Za-z0-9_-]{0,15}"


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


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
        payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _question_hash(request: QAInput) -> str:
    return hashlib.sha256(request.question.encode("utf-8")).hexdigest()


def _find_evidence(request: QAInput, evidence_id: str) -> RetrievedEvidence:
    evidence = next((e for e in request.evidence if e.evidence_id == evidence_id), None)
    if evidence is None:
        raise ValueError(f"unknown evidence_id: {evidence_id}")
    return evidence


def _mentions(text: str, subject: str) -> bool:
    target = _compact(subject)
    return bool(target) and target in _compact(text)


def _mentions_any(text: str, keywords: tuple[str, ...]) -> bool:
    compact = _compact(text)
    return any(keyword in compact for keyword in keywords)


def _enum_head(normalized: str, marker_start: int) -> str:
    chunk = normalized[max(0, marker_start - 24):marker_start]
    piece = re.split(r"[。；;，,：:、]", chunk)[-1]
    noun = piece.rsplit("的", 1)[-1] if "的" in piece else piece
    return noun or "封闭列表"


def _split_enum_items(segment: str) -> list[str]:
    items: list[str] = []
    for raw in re.split(r"[、，,；;]", segment):
        item = _NUMBERING.sub("", raw).strip("：: ")
        item = _TRAILING_COUNT.sub("", item)
        if len(item) >= 2:
            items.append(item)
    return items


def _closed_enumeration(evidence: RetrievedEvidence) -> tuple[str, list[str]]:
    if evidence.completeness != "closed" or not evidence.completeness_proof.strip():
        raise ValueError(
            "closed-list refutation requires completeness='closed' with a non-empty"
            " completeness_proof; open/unknown evidence goes to manual review, never refute")
    normalized = _compact(evidence.text)
    marker = _ENUM_MARKER.search(normalized)
    if marker is None:
        raise ValueError("evidence lacks an explicit enumeration marker (包括/仅包括/以下)")
    segment = _ENUM_PREFIX.sub("", normalized[marker.end():])
    stop = re.search(r"。", segment)
    if stop is not None:
        segment = segment[:stop.start()]
    if segment.endswith("等"):
        raise ValueError("enumeration ends with 等; the list is open")
    items = _split_enum_items(segment)
    if len(items) < 2:
        raise ValueError("closed-list evidence must enumerate at least two items")
    return _enum_head(normalized, marker.start()), items


def _closed_list_exclusion_conflict(
    request: QAInput, *, evidence_id: str, term: str, check_item: str,
    operator_id: str, keywords: tuple[str, ...], domain: str,
) -> AnswerMutationProposal:
    evidence = _find_evidence(request, evidence_id)
    head, items = _closed_enumeration(evidence)
    target = _compact(term)
    if len(target) < 2:
        raise ValueError("term must contain at least two non-space characters")
    if target in _compact(evidence.text):
        raise ValueError(
            "term appears in the evidence text; closed-list exclusion is unproven,"
            " manual review required")
    answer_compact = _compact(request.answer)
    if target in answer_compact:
        raise ValueError("term must be a new claim not already present in the answer")
    if not any(word in answer_compact for word in _ANSWER_ENUM_WORDS):
        raise ValueError("answer must state an enumeration claim that the mutation extends")
    if not _mentions_any(request.question, keywords):
        raise ValueError("question does not mention the mutated subject domain")
    if not _mentions_any(request.answer, keywords):
        raise ValueError("answer does not belong to the operator's subject domain")
    if not _mentions_any(evidence.text, keywords):
        raise ValueError("evidence does not belong to the operator's subject domain")
    answer_after = request.answer.rstrip().rstrip("。") + f"、{target}。"
    proof = (
        f"evidence为封闭枚举({evidence.completeness_proof})：{head}包括"
        f"{'、'.join(items)}；「{target}」未出现在封闭列表与evidence全文；"
        f"answer变异后把「{target}」加入{domain}，被封闭列表排除。")
    return AnswerMutationProposal(
        operator_id=operator_id, check_item=check_item,
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="refute", proof_kind="closed_list_exclusion",
        proof=proof, requires_manual_review=False,
    )


def propose_gjb01_quantifier_fabrication(
    request: QAInput, *, evidence_id: str, rule_evidence_id: str,
    requirement_id: str, criterion_claim: str,
) -> AnswerMutationProposal:
    """GJB-01: fabricate a quantified criterion for a closed qualitative requirement."""
    requirement = _find_evidence(request, evidence_id)
    rule = _find_evidence(request, rule_evidence_id)
    if rule.source_type != "rule":
        raise ValueError("GJB rule text used as evidence must declare source_type='rule'")
    if requirement.completeness != "closed" or not requirement.completeness_proof.strip():
        raise ValueError(
            "quantifier refutation requires the closed full text of the requirement;"
            " open/unknown evidence goes to manual review, never refute")
    normalized = _compact(requirement.text)
    if requirement_id not in requirement.scope_id and requirement_id not in normalized:
        raise ValueError("requirement evidence is not tied to the claimed requirement_id")
    if not _mentions(request.question, requirement_id):
        raise ValueError("question does not mention the mutated requirement")
    if requirement_id not in _compact(request.answer):
        raise ValueError("answer must state its claim about the same requirement")
    if re.search(r"\d", normalized) is not None or _QUANT_UNIT.search(normalized) is not None:
        raise ValueError("requirement text already carries a quantitative indicator")
    qualitative = next(
        (marker for marker in _QUALITATIVE_MARKERS if marker in normalized), None)
    if qualitative is None:
        raise ValueError("requirement text lacks an explicit qualitative statement")
    claim = _compact(criterion_claim)
    if re.search(r"\d", claim) is None:
        raise ValueError("criterion_claim must carry an explicit numeric quantifier")
    if claim in _compact(request.answer):
        raise ValueError("criterion_claim must be a new claim not already in the answer")
    answer_after = request.answer.rstrip().rstrip("。") + f"，量化判据为{claim}。"
    proof = (
        f"evidence为需求{requirement_id}全文({requirement.completeness_proof})，无数字"
        f"与单位型量化指标，仅有定性表述「{qualitative}」；规则证据"
        f"{rule.evidence_id}(source_type=rule)要求判据量化；answer变异后声称量化判据"
        f"「{claim}」，被封闭需求全文排除。")
    return AnswerMutationProposal(
        operator_id="ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1", check_item="GJB-01",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(requirement.source_ref, rule.source_ref), target="answer",
        gold_candidate="refute", proof_kind="closed_requirement_text_quantifier_absence",
        proof=proof, requires_manual_review=False,
    )


def propose_gjb02_fault_tolerance_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-02: claim a fault-tolerance mechanism excluded by the closed requirement list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-02",
        operator_id="ANSWER-GJB-02-FT-EXCLUSION-V1",
        keywords=("容错", "故障"), domain="故障容错机制")


def propose_gjb03_access_control_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-03: claim a permission control excluded by the closed permission list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-03",
        operator_id="ANSWER-GJB-03-ACL-EXCLUSION-V1",
        keywords=("访问控制", "权限"), domain="权限控制")


def propose_gjb04_audit_field_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-04: claim a logged event/field excluded by the closed audit-log field list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-04",
        operator_id="ANSWER-GJB-04-AUDIT-EXCLUSION-V1",
        keywords=("审计", "日志"), domain="审计日志字段")


def _evidenced_test_item(evidence: RetrievedEvidence, requirement_id: str) -> str:
    pattern = re.compile(
        re.escape(requirement_id) + _TRACE_VERBS + r"(?:测试项)?(?P<test>"
        + _TEST_ID + r")(?![A-Za-z0-9_-])")
    match = pattern.search(_compact(evidence.text))
    if match is None:
        raise ValueError("evidence lacks an explicit requirement→test-item mapping")
    return match.group("test")


def _answer_trace_claim(answer: str, requirement_id: str) -> re.Match[str]:
    pattern = re.compile(
        re.escape(requirement_id) + r"\s*" + _TRACE_VERBS + r"\s*(?:测试项)?\s*"
        r"(?P<test>" + _TEST_ID + r")(?![A-Za-z0-9_-])")
    match = pattern.search(answer)
    if match is None:
        raise ValueError("answer must state an explicit requirement→test-item mapping")
    return match


def _trace_context(
    request: QAInput, *, evidence_id: str, requirement_id: str,
) -> tuple[RetrievedEvidence, str, re.Match[str]]:
    evidence = _find_evidence(request, evidence_id)
    evidenced_test = _evidenced_test_item(evidence, requirement_id)
    if not _mentions(request.question, requirement_id):
        raise ValueError("question does not mention the mutated requirement")
    answer_match = _answer_trace_claim(request.answer, requirement_id)
    if answer_match.group("test") != evidenced_test:
        raise ValueError("source answer must state the mapping evidenced by the trace table")
    return evidence, evidenced_test, answer_match


def propose_gjb05_trace_conflict(
    request: QAInput, *, evidence_id: str, requirement_id: str, mutated_test_id: str,
) -> AnswerMutationProposal:
    """GJB-05: redirect an explicit trace mapping to a different test item."""
    evidence, evidenced_test, answer_match = _trace_context(
        request, evidence_id=evidence_id, requirement_id=requirement_id)
    mutated = mutated_test_id.strip()
    if re.fullmatch(_TEST_ID, mutated) is None:
        raise ValueError("mutated_test_id must be a valid test-item identifier")
    if mutated == evidenced_test:
        raise ValueError("mutated test item must differ from the evidenced mapping")
    answer_after = (request.answer[:answer_match.start("test")] + mutated
                    + request.answer[answer_match.end("test"):])
    proof = (
        f"evidence追溯表显式映射{requirement_id}→测试项{evidenced_test}；answer变异后"
        f"声称映射到测试项{mutated}，与显式映射冲突。")
    return AnswerMutationProposal(
        operator_id="ANSWER-GJB-05-TRACE-CONFLICT-V1", check_item="GJB-05",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="refute", proof_kind="explicit_trace_mapping_conflict",
        proof=proof, requires_manual_review=False,
    )


def propose_gjb05_trace_match(
    request: QAInput, *, evidence_id: str, requirement_id: str,
) -> AnswerMutationProposal:
    """GJB-05: keep the answer that hits the explicit trace mapping (support control)."""
    evidence, evidenced_test, _answer_match = _trace_context(
        request, evidence_id=evidence_id, requirement_id=requirement_id)
    proof = (
        f"evidence追溯表显式映射{requirement_id}→测试项{evidenced_test}；"
        f"answer命中该映射。")
    return AnswerMutationProposal(
        operator_id="ANSWER-GJB-05-TRACE-MATCH-V1", check_item="GJB-05",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=request.answer,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="support", proof_kind="explicit_trace_mapping_match",
        proof=proof, requires_manual_review=False,
    )


def propose_gjb06_alarm_element_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-06: claim an alarm element excluded by the closed alarm-element list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-06",
        operator_id="ANSWER-GJB-06-ALARM-EXCLUSION-V1",
        keywords=("报警", "告警"), domain="报警要素")


def propose_gjb07_self_check_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-07: claim a self-check mechanism excluded by the closed mechanism list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-07",
        operator_id="ANSWER-GJB-07-SELFTEST-EXCLUSION-V1",
        keywords=("自检",), domain="软件自检机制")


def propose_gjb08_power_loss_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-08: claim a power-loss protected data type excluded by the closed list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-08",
        operator_id="ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1",
        keywords=("掉电", "断电"), domain="掉电保护数据")


def propose_gjb09_input_validation_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-09: claim an input validation type excluded by the closed validation list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-09",
        operator_id="ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1",
        keywords=("校验", "输入"), domain="输入校验")


def propose_gjb10_rollback_fabrication(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-10: claim an upgrade-safety capability the evidence explicitly negates."""
    evidence = _find_evidence(request, evidence_id)
    keywords: tuple[str, ...] = ("升级", "版本", "回滚")
    target = _compact(term)
    if len(target) < 2:
        raise ValueError("term must contain at least two non-space characters")
    normalized = _compact(evidence.text)
    pos = normalized.find(target)
    if pos < 0:
        raise ValueError("evidence does not mention the claimed term")
    negation = _NEGATION.search(normalized[max(0, pos - 14):pos])
    if negation is None:
        raise ValueError("evidence does not explicitly negate the claimed term")
    if target in _compact(request.answer):
        raise ValueError("term must be a new claim not already present in the answer")
    if not _mentions_any(request.question, keywords):
        raise ValueError("question does not mention the mutated subject domain")
    if not _mentions_any(request.answer, keywords):
        raise ValueError("answer does not belong to the operator's subject domain")
    answer_after = request.answer.rstrip().rstrip("。") + f"，并支持{target}。"
    proof = (
        f"evidence在「{target}」前显式否定({negation.group(0)})；answer变异后声称"
        f"升级支持{target}，与显式否定冲突。")
    return AnswerMutationProposal(
        operator_id="ANSWER-GJB-10-ROLLBACK-CONFLICT-V1", check_item="GJB-10",
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="refute", proof_kind="explicit_negation_conflict",
        proof=proof, requires_manual_review=False,
    )


def propose_gjb11_degraded_mode_exclusion(
    request: QAInput, *, evidence_id: str, term: str,
) -> AnswerMutationProposal:
    """GJB-11: claim a degraded operation mode excluded by the closed mode list."""
    return _closed_list_exclusion_conflict(
        request, evidence_id=evidence_id, term=term, check_item="GJB-11",
        operator_id="ANSWER-GJB-11-DEGRADE-EXCLUSION-V1",
        keywords=("降级",), domain="降级运行模式")


GJB_OPERATOR_STATUS: dict[str, str] = {
    "ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1": "deterministic_prototype",
    "ANSWER-GJB-02-FT-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-03-ACL-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-04-AUDIT-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-05-TRACE-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-GJB-05-TRACE-MATCH-V1": "deterministic_prototype",
    "ANSWER-GJB-06-ALARM-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-07-SELFTEST-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1": "deterministic_prototype",
    "ANSWER-GJB-10-ROLLBACK-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-GJB-11-DEGRADE-EXCLUSION-V1": "deterministic_prototype",
}


__all__ = [
    "GJB_OPERATOR_STATUS",
    "propose_gjb01_quantifier_fabrication",
    "propose_gjb02_fault_tolerance_exclusion",
    "propose_gjb03_access_control_exclusion",
    "propose_gjb04_audit_field_exclusion",
    "propose_gjb05_trace_conflict",
    "propose_gjb05_trace_match",
    "propose_gjb06_alarm_element_exclusion",
    "propose_gjb07_self_check_exclusion",
    "propose_gjb08_power_loss_exclusion",
    "propose_gjb09_input_validation_exclusion",
    "propose_gjb10_rollback_fabrication",
    "propose_gjb11_degraded_mode_exclusion",
]
