"""Tests for LOGIC-family answer-only mutation operators."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.logic_mutations import (  # noqa: E402
    propose_atomicity_conflict,
    propose_event_order_swap,
    propose_exception_strategy_swap,
    propose_permission_conflict,
    propose_priority_reversal,
    propose_recovery_mode_conflict,
    propose_redundancy_arbitration_swap,
    propose_research_scope_conflict,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402


def make_input(question: str, answer: str, evidence_text: str) -> QAInput:
    return QAInput(
        instance_id="logic-1", question=question, answer=answer,
        context_freeze_id="freeze-logic",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text=evidence_text, source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),),
    )


def test_priority_reversal_is_refute() -> None:
    request = make_input(
        "A与B谁优先？", "A优先于B。", "系统规定A优先于B。")
    proposal = propose_priority_reversal(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "B优先于A。"
    assert proposal.check_item == "LOGIC-01"


def test_priority_reversal_requires_answer_restate() -> None:
    request = make_input(
        "A与B谁优先？", "系统使用A。", "系统规定A优先于B。")
    with pytest.raises(ValueError, match="no explicit priority"):
        propose_priority_reversal(request, evidence_id="e1")


def test_exception_strategy_swap_is_refute() -> None:
    request = make_input(
        "超时时系统应如何处理？", "发生超时时应终止。",
        "发生超时时应终止，不得重试。")
    proposal = propose_exception_strategy_swap(
        request, evidence_id="e1", prohibited_action="重试")
    assert proposal.gold_candidate == "refute"
    assert "应重试" in proposal.answer_after
    assert proposal.check_item == "LOGIC-02"


def test_exception_strategy_swap_requires_explicit_prohibition() -> None:
    request = make_input(
        "超时时系统应如何处理？", "发生超时时应重试。",
        "发生超时时可重试或终止。")
    with pytest.raises(ValueError, match="prohibit"):
        propose_exception_strategy_swap(
            request, evidence_id="e1", prohibited_action="重试")


def test_event_order_swap_is_refute() -> None:
    request = make_input(
        "初始化顺序是什么？", "先校验配置，然后启动服务。",
        "流程为先校验配置，然后启动服务。")
    proposal = propose_event_order_swap(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "先启动服务，然后校验配置。"
    assert proposal.check_item == "LOGIC-03"


def test_event_order_swap_requires_aligned_answer() -> None:
    request = make_input(
        "初始化顺序是什么？", "系统直接启动。",
        "流程为先校验配置，然后启动服务。")
    with pytest.raises(ValueError, match="restate"):
        propose_event_order_swap(request, evidence_id="e1")


def test_atomicity_conflict_is_refute() -> None:
    request = make_input(
        "任务切换过程是否可中断？", "任务切换过程不可中断。",
        "任务切换为原子操作，过程不可中断。")
    proposal = propose_atomicity_conflict(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "可以中断" in proposal.answer_after


def test_atomicity_requires_explicit_evidence() -> None:
    request = make_input(
        "任务切换过程是否可中断？", "任务切换过程不可中断。",
        "任务切换由调度器管理。")
    with pytest.raises(ValueError, match="atomicity"):
        propose_atomicity_conflict(request, evidence_id="e1")


def test_redundancy_arbitration_swap_is_refute() -> None:
    request = make_input(
        "主库故障时如何切换？", "主库故障时切换到备库。",
        "当主库故障时，系统切换到备库。")
    proposal = propose_redundancy_arbitration_swap(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "备库故障时切换到主库" in proposal.answer_after
    assert proposal.check_item == "LOGIC-08"


def test_permission_conflict_is_refute() -> None:
    request = make_input(
        "访客能否修改配置？", "禁止访客执行修改配置。",
        "权限矩阵：禁止访客执行修改配置。")
    proposal = propose_permission_conflict(
        request, evidence_id="e1", role="访客", action="修改配置")
    assert proposal.gold_candidate == "refute"
    assert "访客可以执行修改配置" in proposal.answer_after
    assert proposal.check_item == "LOGIC-09"


def test_permission_requires_explicit_forbid() -> None:
    request = make_input(
        "访客能否修改配置？", "访客不能修改配置。",
        "权限矩阵未列出访客。")
    with pytest.raises(ValueError, match="forbid"):
        propose_permission_conflict(
            request, evidence_id="e1", role="访客", action="修改配置")


def test_recovery_mode_conflict_is_refute() -> None:
    request = make_input(
        "故障后如何恢复？", "系统故障后自动恢复。",
        "系统故障后仅支持自动恢复。")
    proposal = propose_recovery_mode_conflict(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "手动恢复" in proposal.answer_after
    assert proposal.check_item == "LOGIC-10"


def test_recovery_requires_exclusion_wording() -> None:
    request = make_input(
        "故障后如何恢复？", "系统故障后自动恢复。",
        "系统故障后自动恢复，必要时可人工介入。")
    with pytest.raises(ValueError, match="automatic-only"):
        propose_recovery_mode_conflict(request, evidence_id="e1")


def test_research_scope_conflict_is_refute() -> None:
    request = make_input(
        "追踪失效后采用哪种搜索？", "触发后仅增量搜索。",
        "触发条件命中后仅执行增量搜索。")
    proposal = propose_research_scope_conflict(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "仅全量搜索" in proposal.answer_after
    assert proposal.check_item == "LOGIC-11"
