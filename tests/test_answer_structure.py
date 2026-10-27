"""Tests for deterministic answer structural decomposition."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_structure import (  # noqa: E402
    decompose_answer,
    pair_statements,
)
from algorithms.consistency.evidence_statements import EvidenceStatement  # noqa: E402


REAL_ANSWER = (
    "在获取LOB数据时发生连接错误，系统执行以下处理：\n\n"
    "1. **连接检测**：系统检测数据库连接状态，发现不成功。\n\n"
    "2. **触发异常流E1**：系统触发异常流E1并记录日志。\n\n"
    "3. **结果通知**：系统向操作人员发送错误提示。"
)


def test_numbered_markdown_steps_split_into_atomic_claims() -> None:
    claims = decompose_answer(REAL_ANSWER, "获取LOB时连接错误触发什么异常？")
    texts = [claim.text for claim in claims]
    assert any("系统检测数据库连接状态" in text for text in texts)
    assert any("触发异常流E1" in text for text in texts)
    assert any("发送错误提示" in text for text in texts)
    assert all(len(claim.text) < 60 for claim in claims)
    assert {claim.structure for claim in claims} <= {"step", "header", "sentence"}


def test_scope_hint_binds_usecase_or_question_subject() -> None:
    claims = decompose_answer(
        "读取配置文件连接的前置条件是数据库初始化成功。连接失败触发异常流E1。",
        "读取配置文件连接的前置条件是什么？")
    assert claims
    assert all(claim.scope_hint for claim in claims)
    assert any("读取配置文件连接" in claim.scope_hint for claim in claims)


def test_plain_prose_answer_falls_back_to_sentences() -> None:
    claims = decompose_answer(
        "系统包括A功能。系统还包括B功能。", "系统包括哪些功能？")
    assert len(claims) == 2
    assert claims[0].text == "系统包括A功能"


def test_pair_statements_prefers_scope_matched_evidence() -> None:
    claims = decompose_answer(
        "读取配置文件连接的前置条件是数据库初始化成功。",
        "读取配置文件连接的前置条件是什么？")
    statements = [
        EvidenceStatement("ev1#s0", "ev1", "前置条件：数据库初始化成功",
                          "前置条件", "读取配置文件连接", 3),
        EvidenceStatement("ev2#s0", "ev2", "数据库操作包括数据库初始化功能",
                          "sentence", "", 1),
    ]
    pairs = pair_statements(claims, statements)
    assert pairs
    assert all(statement.evidence_id == "ev1" for _claim, statement in pairs)


def test_scopeless_claim_pairs_with_all_question_conditioned_statements() -> None:
    claims = decompose_answer("系统支持热插拔连接。", "系统的连接方式是什么？")
    statements = [
        EvidenceStatement("ev1#s0", "ev1", "前置条件：数据库初始化成功",
                          "前置条件", "读取配置文件连接", 3),
        EvidenceStatement("ev2#s0", "ev2", "系统支持多种连接方式",
                          "sentence", "", 1),
    ]
    pairs = pair_statements(claims, statements)
    assert pairs
    assert {statement.evidence_id for _claim, statement in pairs} == {"ev1", "ev2"}
