"""Aggregation-variant contract tests (P1 support-recall study).

Covers the three cross-claim aggregation variants of QAConsistencyModule
(strict-∀ / dominant_70 / no_minor_block) at the unit level — 3-claim
combinations through _aggregate — plus the classifier helpers
(_is_active_nie / _is_minor_claim) and the backward-compatibility
regression: the default constructor keeps the strict ∀ semantics, so
every existing configuration and paper number is untouched.
"""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import (  # noqa: E402
    AGGREGATION_VARIANTS,
    QAConsistencyModule,
    _is_active_nie,
    _is_minor_claim,
)


def _claim(cid: str, text: str, verdict: str, *,
           method: str = "semantic_unresolved",
           rationale: str = "", confidence: float = 0.0) -> ClaimResult:
    return ClaimResult(
        claim_id=cid,
        claim_text=text,
        verdict=verdict,
        check_item_candidates=(),
        evidence_refs=(),
        rationale=rationale,
        method=method,
        confidence=confidence,
    )


SUP = "support"
NIE = "not_in_evidence"
REF = "refute"


def _module(variant: str = "strict") -> QAConsistencyModule:
    return QAConsistencyModule(aggregation=variant)


# ── strict (default) semantics ─────────────────────────────────────────────

def test_strict_any_nie_blocks_support() -> None:
    results = (
        _claim("c1", "A", SUP, method="exact_statement"),
        _claim("c2", "B", NIE),
        _claim("c3", "C", SUP, method="llm_residual"),
    )
    assert _module()._aggregate(results) == (NIE, [])


def test_strict_all_support_is_support() -> None:
    results = (
        _claim("c1", "A", SUP, method="exact_statement"),
        _claim("c2", "B", SUP, method="llm_residual"),
    )
    assert _module()._aggregate(results) == (SUP, [])


def test_refute_wins_in_every_variant() -> None:
    results = (
        _claim("c1", "A", SUP, method="exact_statement"),
        _claim("c2", "B", REF, method="identifier_exact_match"),
        _claim("c3", "C", NIE),
    )
    for variant in AGGREGATION_VARIANTS:
        assert _module(variant)._aggregate(results)[0] == REF


def test_unknown_variant_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="aggregation"):
        QAConsistencyModule(aggregation="loose")


def test_default_construction_is_strict() -> None:
    assert QAConsistencyModule().aggregation == "strict"


# ── dominant_70 semantics ───────────────────────────────────────────────────

def _inability(cid: str) -> ClaimResult:
    return _claim(cid, f"step {cid}", NIE, method="semantic_unresolved")


def _active_nie(cid: str) -> ClaimResult:
    return _claim(cid, f"member {cid}", NIE,
                  method="conservative_unresolved",
                  rationale="枚举成员未全部命中(1项)；未证明context穷举")


def test_dominant_70_inability_nies_do_not_veto() -> None:
    # 066/069 mechanism: verified supports + inability NIEs -> support
    results = (
        _claim("c1", "A", SUP, method="llm_residual"),
        _claim("c2", "B", SUP, method="llm_residual"),
        _claim("c3", "C", SUP, method="llm_residual"),
        _inability("c4"),
        _inability("c5"),
    )
    verdict, diagnostics = _module("dominant_70")._aggregate(results)
    assert verdict == SUP
    assert any(d.startswith("agg_dominant_70_ratio_1.00") for d in diagnostics)


def test_dominant_70_active_nies_count_against_support() -> None:
    # 077 mechanism: one support vs three active observations -> ratio 0.25
    results = (
        _claim("c1", "A", SUP, method="llm_residual"),
        _active_nie("c2"),
        _active_nie("c3"),
        _active_nie("c4"),
    )
    verdict, diagnostics = _module("dominant_70")._aggregate(results)
    assert verdict == NIE
    assert any("0.25" in d for d in diagnostics)


def test_dominant_70_boundary_ratio_is_inclusive() -> None:
    supports = tuple(_claim(f"c{i}", f"claim {i}", SUP,
                            method="exact_statement") for i in range(7))
    actives = tuple(_active_nie(f"a{i}") for i in range(3))
    verdict, _diagnostics = _module("dominant_70")._aggregate(
        supports + actives)
    assert verdict == SUP  # 7 / 10 = 0.70 exactly -> support


def test_dominant_70_without_decidable_claims_stays_nie() -> None:
    results = (_inability("c1"), _inability("c2"))
    verdict, diagnostics = _module("dominant_70")._aggregate(results)
    assert verdict == NIE
    assert "agg_dominant_70_no_decidable_claim" in diagnostics


def test_dominant_70_below_threshold_stays_nie() -> None:
    results = (
        _claim("c1", "A", SUP, method="exact_statement"),
        _claim("c2", "B", SUP, method="llm_residual"),
        _active_nie("c3"),
        _active_nie("c4"),
        _inability("c5"),
    )
    # decidable = 2 support + 2 active NIE -> ratio 0.50 < 0.70
    verdict, _diagnostics = _module("dominant_70")._aggregate(results)
    assert verdict == NIE


# ── no_minor_block semantics ───────────────────────────────────────────────

def test_no_minor_block_effect_claim_cannot_veto() -> None:
    results = (
        _claim("c1", "查询结果缓存：提供对查询结果的数据缓存功能", SUP,
               method="llm_residual"),
        _claim("c2", "动态刷新机制确保缓存始终反映最新的信息", NIE,
               method="sequence_alignment",
               rationale="answer步骤在主事件流证据中无匹配, 判凭空步骤"),
    )
    verdict, diagnostics = _module("no_minor_block")._aggregate(results)
    assert verdict == SUP
    assert "agg_no_minor_block_core_all_support" in diagnostics


def test_no_minor_block_core_nie_still_blocks() -> None:
    results = (
        _claim("c1", "A", SUP, method="llm_residual"),
        _claim("c2", "1．查询结果缓存：提供对查询结果的数据缓存功能", NIE,
               method="sequence_alignment",
               rationale="answer步骤在主事件流证据中无匹配, 判凭空步骤"),
    )
    verdict, diagnostics = _module("no_minor_block")._aggregate(results)
    assert verdict == NIE
    assert "agg_no_minor_block_core_blocked" in diagnostics


def test_no_minor_block_minor_only_set_falls_back_to_strict() -> None:
    all_minor_nie = (
        _claim("c1", "确保系统可靠", NIE),
        _claim("c2", "便于维护", NIE),
    )
    assert _module("no_minor_block")._aggregate(all_minor_nie)[0] == NIE
    all_minor_sup = (
        _claim("c1", "确保系统可靠", SUP, method="llm_residual"),
    )
    assert _module("no_minor_block")._aggregate(all_minor_sup)[0] == SUP


# ── classifier helpers ─────────────────────────────────────────────────────

def test_is_active_nie_distinguishes_observation_from_inability() -> None:
    assert _is_active_nie(_active_nie("c1"))
    assert _is_active_nie(_claim("c2", "step", NIE,
                                 method="sequence_alignment",
                                 rationale="answer步骤在主事件流证据中无匹配"
                                           "(最佳相似度0.28低于配对阈值), "
                                           "判凭空步骤"))
    assert not _is_active_nie(_inability("c3"))
    assert not _is_active_nie(_claim("c4", "step", NIE,
                                     method="sequence_alignment",
                                     rationale="证据无用例主事件流编号步骤, "
                                               "时序不可核对"))
    assert not _is_active_nie(_claim("c5", "A", SUP,
                                     method="exact_statement"))


def test_is_minor_claim_marks_effect_summary_fragments() -> None:
    assert _is_minor_claim(_claim("c1", "动态刷新机制确保缓存始终反映最新", NIE))
    assert _is_minor_claim(_claim("c2", "这些操作通过数据对象方式实现", NIE))
    assert _is_minor_claim(_claim("c3", "4．1.1 |", NIE))
    assert not _is_minor_claim(_claim(
        "c4", "查询结果缓存：提供对查询结果的数据缓存功能", NIE))
    assert not _is_minor_claim(_claim(
        "c5", "添加：向数据库中插入数据", SUP, method="llm_residual"))


# ── end-to-end default regression (verify() path untouched) ────────────────

def sample_request() -> QAInput:
    return QAInput(
        instance_id="qa-agg-1",
        question="系统响应时间要求是多少？",
        answer="响应时间为200ms。",
        context_freeze_id="frozen-context-agg",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="响应时间为200ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1", page=3),
            scope_id="doc01:3.2.1",
            completeness="open",
        ),),
    )


def test_verify_default_matches_strict_aggregation_support() -> None:
    request = sample_request()
    assert QAConsistencyModule().verify(request).verdict == SUP


def test_verify_unresolved_answer_keeps_nie_by_default() -> None:
    request = QAInput(
        instance_id="qa-agg-2",
        question="系统的备份方式是什么？",
        answer="系统采用热备份方式。",
        context_freeze_id="frozen-context-agg-2",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="本系统提供冷备份功能。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )
    assert QAConsistencyModule().verify(request).verdict == NIE


def test_verify_explicit_conflict_refutes_under_every_variant() -> None:
    request = QAInput(
        instance_id="qa-agg-3",
        question="系统响应时间要求是多少？",
        answer="响应时间不超过200ms。",
        context_freeze_id="frozen-context-agg-3",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="系统响应时间不小于300ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )
    for variant in AGGREGATION_VARIANTS:
        module = QAConsistencyModule(aggregation=variant)
        assert module.verify(request).verdict == REF, variant
