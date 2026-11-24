"""Tests for algorithms/consistency/answer_anchor.py (字面忠实修复, E1弱点#1).

字面契约逐条验证: 锚定后的claim_text必须answer[start:end]==text
(99号Phase 0-E1的answer[span]==text契约, 96号§5 span忠实=解释可信地基).
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_anchor import (  # noqa: E402
    anchor_claim,
    anchor_span,
)
from algorithms.consistency.qa_models import ClaimResult  # noqa: E402


def _claim(text: str) -> ClaimResult:
    return ClaimResult(
        claim_id="c1", claim_text=text, verdict="refute",
        check_item_candidates=("GJB-05",), evidence_refs=("ev-1",),
        rationale="原始rationale", method="trace_bidirectional_join",
        confidence=1.0)


ANSWER = "代码生成（3.2.4）需求追溯至任务书4.1.1 c)。"


# ── anchor_span: 最小覆盖区间数学 ─────────────────────────────────


def test_anchor_span_single_key() -> None:
    assert anchor_span(ANSWER, ("3.2.4",)) == (5, 10)


def test_anchor_span_multi_key_min_cover() -> None:
    # 两个命中词元(3.2.4@5-10, 4.1.1 c)@19-27)→最小覆盖span
    assert anchor_span(ANSWER, ("3.2.4", "4.1.1 c)", "4.1.1 a)")) == (5, 27)


def test_anchor_span_zero_hit_returns_none() -> None:
    assert anchor_span(ANSWER, ("4.5", "3.3", "3.4")) is None
    assert anchor_span("", ("3.2.4",)) is None


def test_anchor_span_skips_empty_and_whitespace_keys() -> None:
    assert anchor_span(ANSWER, ("", "   ", "3.2.4")) == (5, 10)
    assert anchor_span(ANSWER, ("", "  ")) is None


def test_anchor_span_uses_first_occurrence() -> None:
    answer = "3.2.4前文3.2.4后文"
    assert anchor_span(answer, ("3.2.4",)) == (0, 5)


# ── anchor_claim: 字面契约+信息保留 ───────────────────────────────


def test_anchor_claim_verbatim_contract() -> None:
    """字面契约: claim_text==answer[span]逐字, span精确到字符."""
    claim = _claim("表81与表82对本文档章节3.2.4的任务书追踪映射一致")
    anchored = anchor_claim(claim, ANSWER, ("3.2.4", "4.1.1 c)"))
    assert anchored.span == (5, 27)
    assert anchored.claim_text == "3.2.4）需求追溯至任务书4.1.1 c)"
    assert ANSWER[anchored.span[0]:anchored.span[1]] == anchored.claim_text
    assert anchored.claim_text in ANSWER


def test_anchor_claim_moves_synthesis_into_rationale() -> None:
    """合成断言不丢弃: 原claim_text移入rationale, 判定字段全不动."""
    claim = _claim("表81与表82对本文档章节3.2.4的任务书追踪映射一致")
    anchored = anchor_claim(claim, ANSWER, ("3.2.4", "4.1.1 c)"))
    assert "原始rationale" in anchored.rationale
    assert ("表81与表82对本文档章节3.2.4的任务书追踪映射一致"
            in anchored.rationale)
    # 判定逻辑零变更: verdict/method/confidence/refs/check_items原样
    assert anchored.verdict == claim.verdict
    assert anchored.method == claim.method
    assert anchored.confidence == claim.confidence
    assert anchored.evidence_refs == claim.evidence_refs
    assert anchored.check_item_candidates == claim.check_item_candidates
    assert anchored.claim_id == claim.claim_id


def test_anchor_claim_zero_hit_returns_claim_unchanged() -> None:
    """answer无关联文本: 原样返回同一claim(合成断言保持, 如实计残余)."""
    claim = _claim("表81 row20的追踪映射与跟踪说明「不追踪」自洽")
    same = anchor_claim(claim, ANSWER, ("4.5", "3.3", "3.4"))
    assert same is claim
    assert same.claim_text == claim.claim_text
    assert same.span is None
