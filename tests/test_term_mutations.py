"""Tests for TERM-family answer-only mutation operators."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.term_mutations import (  # noqa: E402
    propose_command_action_swap,
    propose_definition_swap,
    propose_interface_id_conflict,
    propose_status_term_conflict,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402


def make_input(question: str, answer: str, evidence_text: str) -> QAInput:
    return QAInput(
        instance_id="term-1", question=question, answer=answer,
        context_freeze_id="freeze-term",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text=evidence_text, source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),),
    )


def test_definition_swap_is_refute() -> None:
    request = make_input(
        "X的定义是什么？", "X（数据缓存）负责加速。",
        "术语定义：X（数据缓存）、Y（连接池）。")
    proposal = propose_definition_swap(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "X（连接池）" in proposal.answer_after
    assert proposal.check_item == "TERM-02"


def test_definition_swap_requires_source_alignment() -> None:
    request = make_input(
        "X的定义是什么？", "X（连接池）负责管理。",
        "术语定义：X（数据缓存）、Y（连接池）。")
    with pytest.raises(ValueError, match="does not match"):
        propose_definition_swap(request, evidence_id="e1")


def test_status_term_conflict_is_refute() -> None:
    request = make_input(
        "系统有哪些运行状态？", "运行状态包括正常态、故障态。",
        "系统状态包括正常态、故障态，不包括维护态。")
    proposal = propose_status_term_conflict(
        request, evidence_id="e1", excluded_status="维护态")
    assert proposal.gold_candidate == "refute"
    assert "维护态" in proposal.answer_after
    assert proposal.check_item == "TERM-04"


def test_status_term_requires_explicit_exclusion() -> None:
    request = make_input(
        "系统有哪些运行状态？", "运行状态包括正常态、故障态。",
        "系统状态包括正常态、故障态。")
    with pytest.raises(ValueError, match="exclude"):
        propose_status_term_conflict(
            request, evidence_id="e1", excluded_status="维护态")


def test_command_action_swap_is_refute() -> None:
    request = make_input(
        "启动指令做什么？", "指令启动（连接数据库）。",
        "指令定义：指令启动（连接数据库）、指令停止（断开连接）。")
    proposal = propose_command_action_swap(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "指令启动（断开连接）" in proposal.answer_after
    assert proposal.check_item == "TERM-05"


def test_command_swap_requires_matching_action() -> None:
    request = make_input(
        "启动指令做什么？", "指令启动（断开连接）。",
        "指令定义：指令启动（连接数据库）、指令停止（断开连接）。")
    with pytest.raises(ValueError, match="does not match"):
        propose_command_action_swap(request, evidence_id="e1")


def test_interface_id_conflict_is_refute() -> None:
    request = make_input(
        "数据查询接口的标识是什么？", "数据查询接口的标识为PZXQ-JK-SJCX。",
        "数据查询接口的标识为PZXQ-JK-SJCX。")
    proposal = propose_interface_id_conflict(request, evidence_id="e1")
    assert proposal.gold_candidate == "refute"
    assert "PZXQ-JK-SJCX" not in proposal.answer_after
    assert "ZZ" in proposal.answer_after
    assert proposal.check_item == "TERM-07"


def test_interface_conflict_requires_evidenced_id() -> None:
    request = make_input(
        "数据查询接口的标识是什么？", "数据查询接口的标识为PZXQ-JK-OTHER。",
        "数据查询接口的标识为PZXQ-JK-SJCX。")
    with pytest.raises(ValueError, match="not the evidenced"):
        propose_interface_id_conflict(request, evidence_id="e1")
