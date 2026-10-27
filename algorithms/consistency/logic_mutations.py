"""LOGIC-family answer-only mutation operators with explicit normative proof.

Every refute requires explicit normative wording in the frozen evidence
(priority/order/prohibition/exclusivity). Coexistable strategies are never
treated as mutually exclusive without explicit exclusion text.
"""
from __future__ import annotations

import re

from algorithms.consistency.answer_mutations import (
    AnswerMutationProposal,
    _context_hash,
    _question_hash,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence

_NEGATION = r"(?:不得|禁止|不能|不可|不允许)"


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
              proof: str) -> AnswerMutationProposal:
    if answer_after == request.answer:
        raise ValueError("mutation must change the answer")
    return AnswerMutationProposal(
        operator_id=operator_id, check_item=check_item,
        source_instance_id=request.instance_id, question=request.question,
        answer_before=request.answer, answer_after=answer_after,
        context_freeze_id=request.context_freeze_id,
        context_hash=_context_hash(request), question_hash=_question_hash(request),
        context_refs=(evidence.source_ref,), target="answer",
        gold_candidate="refute", proof_kind=proof_kind, proof=proof,
        requires_manual_review=False,
    )


def propose_priority_reversal(request: QAInput, *, evidence_id: str,
                              ) -> AnswerMutationProposal:
    """Reverse an explicit priority statement (LOGIC-01)."""
    evidence = _find_evidence(request, evidence_id)
    answer_pair = re.search(
        r"(?P<a>[A-Za-z\u4e00-\u9fff]{1,12})优先(?:级?高于|于)(?P<b>[A-Za-z\u4e00-\u9fff]{1,12})",
        request.answer)
    if answer_pair is None:
        raise ValueError("answer has no explicit priority statement")
    first, second = answer_pair.group("a"), answer_pair.group("b")
    if (f"{first}优先" not in evidence.text
            or (f"于{second}" not in evidence.text
                and f"高于{second}" not in evidence.text)):
        raise ValueError("evidence has no matching explicit priority statement")
    _question_mentions(request.question, first, second)
    answer_after = request.answer.replace(
        answer_pair.group(0), f"{second}优先于{first}", 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-01-PRIORITY-REVERSAL-V1",
                     check_item="LOGIC-01", answer_after=answer_after,
                     proof_kind="explicit_priority_conflict",
                     proof=(f"evidence显式规定{first}优先于{second}；"
                            f"answer反转为{second}优先于{first}，与显式优先级冲突。"))


def propose_exception_strategy_swap(request: QAInput, *, evidence_id: str,
                                    prohibited_action: str,
                                    ) -> AnswerMutationProposal:
    """Swap the mandated exception action for an explicitly prohibited one (LOGIC-02)."""
    evidence = _find_evidence(request, evidence_id)
    mandate = re.search(
        r"(?:发生|当|若|如果)[^，。；]{1,16}(?:时|情况下)[^。\n]{0,24}?",
        evidence.text)
    if mandate is None:
        raise ValueError("evidence has no explicit exception condition")
    target = prohibited_action.strip()
    if not target:
        raise ValueError("prohibited_action must be non-empty")
    ban = re.search(_NEGATION + r"(?:执行|采取|进行|使用)?\s*" + re.escape(target),
                    evidence.text)
    if ban is None:
        raise ValueError("evidence does not explicitly prohibit the target action")
    action = re.search(r"(?:应|须|必须|只能)(?:执行|采取|进行|使用)?(?P<ok>[^，。；\n]{1,16})",
                       request.answer)
    if action is None or action.group("ok").strip() == target:
        raise ValueError("answer has no distinct mandated action to swap")
    _question_mentions(request.question, target, "处理", "策略", "动作")
    ok_action = action.group("ok")
    answer_after = (request.answer[:action.start("ok")] + target
                    + request.answer[action.end("ok"):])
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-02-EXCEPTION-SWAP-V1",
                     check_item="LOGIC-02", answer_after=answer_after,
                     proof_kind="explicit_prohibited_action",
                     proof=(f"同一异常条件下，evidence显式要求{ok_action}且显式禁止{target}；"
                            f"answer变异为执行{target}。"))


def propose_event_order_swap(request: QAInput, *, evidence_id: str,
                             ) -> AnswerMutationProposal:
    """Swap two explicitly ordered events (LOGIC-03)."""
    evidence = _find_evidence(request, evidence_id)
    order = re.search(r"先(?P<a>[^，。；\n]{1,16})[，,]?然后(?P<b>[^，。；\n]{1,16})",
                      evidence.text)
    if order is None:
        raise ValueError("evidence has no explicit ordered steps")
    first, second = order.group("a").strip(), order.group("b").strip()
    _question_mentions(request.question, first, second, "顺序", "流程", "步骤")
    aligned = f"先{first}，然后{second}"
    if aligned not in request.answer:
        raise ValueError("answer does not restate the evidenced order")
    answer_after = request.answer.replace(
        aligned, f"先{second}，然后{first}", 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-03-ORDER-SWAP-V1",
                     check_item="LOGIC-03", answer_after=answer_after,
                     proof_kind="explicit_order_conflict",
                     proof=(f"evidence用显式顺序词规定先{first}然后{second}；"
                            f"answer交换两者顺序。"))


def propose_atomicity_conflict(request: QAInput, *, evidence_id: str,
                               ) -> AnswerMutationProposal:
    """Claim interruptibility against an explicit atomicity statement (LOGIC-07)."""
    evidence = _find_evidence(request, evidence_id)
    if not re.search(r"不可中断|原子(?:性|操作)|不可被打断", evidence.text):
        raise ValueError("evidence has no explicit atomicity statement")
    if "不可中断" not in request.answer:
        raise ValueError("answer does not restate the atomicity claim")
    _question_mentions(request.question, "切换", "原子", "中断")
    answer_after = request.answer.replace("不可中断", "可以中断", 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-07-ATOMICITY-CONFLICT-V1",
                     check_item="LOGIC-07", answer_after=answer_after,
                     proof_kind="explicit_atomicity_conflict",
                     proof="evidence显式声明过程不可中断；answer变异为可以中断。")


def propose_redundancy_arbitration_swap(request: QAInput, *, evidence_id: str,
                                        ) -> AnswerMutationProposal:
    """Reverse an explicit primary-to-backup switchover rule (LOGIC-08)."""
    evidence = _find_evidence(request, evidence_id)
    answer_rule = re.search(
        r"(?:主用?|主)(?P<a>[^，。；\n]{0,12})(?:故障|失效|异常)(?:时|后)?[^。\n]{0,16}?"
        r"(?:切换|转)到(?:备用?|备)(?P<b>[^，。；\n]{0,12})",
        request.answer)
    if answer_rule is None:
        raise ValueError("answer has no primary/backup switchover statement")
    first, second = answer_rule.group("a").strip(), answer_rule.group("b").strip()
    if (f"主{first}故障" not in evidence.text
            and f"主{first}失效" not in evidence.text):
        raise ValueError("evidence has no matching primary-failure statement")
    if f"切换到备{second}" not in evidence.text and f"转到备{second}" not in evidence.text:
        raise ValueError("evidence has no matching backup switchover statement")
    _question_mentions(request.question, first, second, "主", "备", "切换")
    reversed_rule = f"备{second}故障时切换到主{first}"
    answer_after = request.answer.replace(answer_rule.group(0), reversed_rule, 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-08-ARBITRATION-SWAP-V1",
                     check_item="LOGIC-08", answer_after=answer_after,
                     proof_kind="explicit_arbitration_conflict",
                     proof=(f"evidence显式规定主{first}故障时切换到备{second}；"
                            f"answer反转为备{second}故障时切换到主{first}。"))


def propose_permission_conflict(request: QAInput, *, evidence_id: str,
                                role: str, action: str,
                                ) -> AnswerMutationProposal:
    """Allow an action that evidence explicitly forbids for the role (LOGIC-09)."""
    evidence = _find_evidence(request, evidence_id)
    if not role.strip() or not action.strip():
        raise ValueError("role and action must be non-empty")
    pattern = (_NEGATION + r"(?:角色)?\s*" + re.escape(role)
               + r"(?:执行|进行|访问|使用|操作)?\s*" + re.escape(action))
    if re.search(pattern, evidence.text) is None:
        raise ValueError("evidence does not explicitly forbid the role/action pair")
    _question_mentions(request.question, role, action)
    denial = re.search(
        r"(?:禁止|不允许|不能)" + re.escape(role)
        + r"(?:执行|进行|访问|使用|操作)?" + re.escape(action),
        request.answer)
    if denial is None:
        raise ValueError("answer does not restate the evidenced prohibition")
    allowed = f"{role}可以执行{action}"
    answer_after = request.answer.replace(denial.group(0), allowed, 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-09-PERMISSION-CONFLICT-V1",
                     check_item="LOGIC-09", answer_after=answer_after,
                     proof_kind="explicit_permission_conflict",
                     proof=(f"evidence显式禁止{role}执行{action}；"
                            f"answer变异为{allowed}。"))


def propose_recovery_mode_conflict(request: QAInput, *, evidence_id: str,
                                   ) -> AnswerMutationProposal:
    """Claim manual recovery when evidence restricts to automatic only (LOGIC-10)."""
    evidence = _find_evidence(request, evidence_id)
    if not re.search(r"仅(?:支持|采用|使用|通过)自动恢复|自动恢复[^\n。]{0,12}(?:不支持|无需|不得)[^\n。]{0,8}手动",
                     evidence.text):
        raise ValueError("evidence has no automatic-only recovery statement")
    if "自动恢复" not in request.answer:
        raise ValueError("answer does not restate the automatic recovery claim")
    _question_mentions(request.question, "恢复", "重启")
    answer_after = request.answer.replace("自动恢复", "手动恢复", 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-10-RECOVERY-CONFLICT-V1",
                     check_item="LOGIC-10", answer_after=answer_after,
                     proof_kind="explicit_recovery_exclusion",
                     proof="evidence显式限定仅自动恢复；answer变异为手动恢复。")


def propose_research_scope_conflict(request: QAInput, *, evidence_id: str,
                                    ) -> AnswerMutationProposal:
    """Flip an explicitly exclusive incremental/full search scope (LOGIC-11)."""
    evidence = _find_evidence(request, evidence_id)
    match = re.search(r"仅(?:执行|采用|使用)?(?P<scope>增量|全量)(?:搜索|检索|查找)",
                      evidence.text)
    if match is None:
        raise ValueError("evidence has no exclusive search-scope statement")
    scope = match.group("scope")
    opposite = "全量" if scope == "增量" else "增量"
    aligned = f"仅{scope}搜索"
    if aligned not in request.answer:
        raise ValueError("answer does not restate the evidenced search scope")
    _question_mentions(request.question, "搜索", "检索", scope)
    answer_after = request.answer.replace(aligned, f"仅{opposite}搜索", 1)
    return _proposal(request, evidence,
                     operator_id="ANSWER-LOGIC-11-SCOPE-CONFLICT-V1",
                     check_item="LOGIC-11", answer_after=answer_after,
                     proof_kind="exclusive_scope_conflict",
                     proof=(f"evidence显式限定仅{scope}搜索；"
                            f"answer变异为仅{opposite}搜索。"))


LOGIC_OPERATOR_STATUS: dict[str, str] = {
    "ANSWER-LOGIC-01-PRIORITY-REVERSAL-V1": "deterministic_prototype",
    "ANSWER-LOGIC-02-EXCEPTION-SWAP-V1": "deterministic_prototype",
    "ANSWER-LOGIC-03-ORDER-SWAP-V1": "deterministic_prototype",
    "ANSWER-LOGIC-07-ATOMICITY-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-LOGIC-08-ARBITRATION-SWAP-V1": "deterministic_prototype",
    "ANSWER-LOGIC-09-PERMISSION-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-LOGIC-10-RECOVERY-CONFLICT-V1": "deterministic_prototype",
    "ANSWER-LOGIC-11-SCOPE-CONFLICT-V1": "deterministic_prototype",
}

__all__ = [
    "propose_priority_reversal",
    "propose_exception_strategy_swap",
    "propose_event_order_swap",
    "propose_atomicity_conflict",
    "propose_redundancy_arbitration_swap",
    "propose_permission_conflict",
    "propose_recovery_mode_conflict",
    "propose_research_scope_conflict",
    "LOGIC_OPERATOR_STATUS",
]
