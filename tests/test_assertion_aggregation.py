"""断言感知聚合契约测试(M88).

Covers: (1) ``_is_assertive_claim`` 边界(裸名词/谓词/typed通道/长句/
短列表片段); (2) assertive_strict / assertive_ratio 两个聚合变体在
``_aggregate`` 上的行为语义; (3) ``AGGREGATION_VARIANTS`` 注册与
verify()端到端的裸名词救回路径(M82 C/M87 D2的support塌方机制).
"""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import AnswerClaim  # noqa: E402
from algorithms.consistency.assertion import (  # noqa: E402
    is_assertive_text,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.qa_module import (  # noqa: E402
    AGGREGATION_VARIANTS,
    _ASSERTIVE_SUPPORT_RATIO,
    QAConsistencyModule,
    _is_assertive_claim,
)

SUP = "support"
NIE = "not_in_evidence"
REF = "refute"


def _claim(cid: str, text: str, verdict: str, *,
           method: str = "semantic_unresolved",
           rationale: str = "") -> ClaimResult:
    return ClaimResult(
        claim_id=cid,
        claim_text=text,
        verdict=verdict,
        check_item_candidates=(),
        evidence_refs=(),
        rationale=rationale,
        method=method,
        confidence=0.0,
    )


def _active_nie(cid: str, text: str) -> ClaimResult:
    return _claim(cid, text, NIE, method="conservative_unresolved",
                  rationale="枚举成员未全部命中(1项)；未证明context穷举")


def _module(variant: str) -> QAConsistencyModule:
    return QAConsistencyModule(aggregation=variant)


# ── _is_assertive_claim边界 ─────────────────────────────────────────────────

def test_bare_noun_fragments_are_not_assertive() -> None:
    """裸名词/裸动词原子("添加"式)非断言——NIE一票否决的元凶."""
    for text in ("添加", "修改", "查询", "插入", "支持"):
        assert not _is_assertive_claim(_claim("c1", text, NIE)), text


def test_predicate_object_phrase_is_assertive() -> None:
    """任务给定边界: "添加"→False / "向数据库中插入数据"→True."""
    assert not is_assertive_text("添加")
    assert _is_assertive_claim(
        _claim("c1", "向数据库中插入数据", NIE))


def test_predicate_sentence_is_assertive() -> None:
    assert _is_assertive_claim(_claim("c1", "系统支持热插拔连接", SUP))
    assert _is_assertive_claim(_claim("c1", "前置条件：无", NIE))


def test_long_description_defaults_assertive() -> None:
    """≥12字长描述句默认含谓词结构(无lexicon谓词也判assertive)."""
    assert _is_assertive_claim(
        _claim("c1", "每个条目具有其独特的能力标识", NIE))


def test_typed_method_marker_is_assertive() -> None:
    """typed通道(numeric/enum/identifier/quoted)构造上是断言."""
    for method in ("identifier_exact_match", "explicit_enum_exclusion",
                   "numeric_interval", "explicit_quote_polarity",
                   "closed_scope_exclusion"):
        assert _is_assertive_claim(
            _claim("c1", "PZXQ-JK", NIE, method=method)), method


def test_short_list_fragment_is_not_assertive() -> None:
    """短列表片段/纯名词短语(≤4字或无谓词的5-11字段)非断言."""
    for text in ("数据查询", "查询缓存", "200ms", "4．1.1", "连接状态"):
        assert not _is_assertive_claim(_claim("c1", text, NIE)), text


def test_semantic_method_falls_back_to_text_rules() -> None:
    """非typed方法(semantic/nli_residual等)回落到文本规则."""
    assert not _is_assertive_claim(
        _claim("c1", "添加", NIE, method="nli_residual"))
    assert _is_assertive_claim(
        _claim("c1", "系统支持热插拔连接", SUP, method="nli_residual"))


def test_empty_text_is_not_assertive() -> None:
    assert not _is_assertive_claim(_claim("c1", "", NIE))
    assert not _is_assertive_claim(_claim("c1", "  ", NIE))


# ── assertive_strict语义 ────────────────────────────────────────────────────

def test_assertive_strict_bare_noun_nie_cannot_veto() -> None:
    """M87 D2塌方机制的正向救回: 裸名词NIE不再一票否决assertive support."""
    results = (
        _claim("c1", "系统支持热插拔连接", SUP, method="exact_statement"),
        _claim("c2", "添加", NIE),
        _claim("c3", "查询", NIE),
    )
    verdict, diagnostics = _module("assertive_strict")._aggregate(results)
    assert verdict == SUP
    assert "agg_assertive_strict_all_support" in diagnostics


def test_assertive_strict_assertive_nie_still_blocks() -> None:
    results = (
        _claim("c1", "系统支持热插拔连接", SUP, method="exact_statement"),
        _claim("c2", "向数据库中插入数据", NIE),
    )
    verdict, diagnostics = _module("assertive_strict")._aggregate(results)
    assert verdict == NIE
    assert "agg_assertive_strict_blocked" in diagnostics


def test_assertive_strict_no_assertive_claim_falls_back_to_strict() -> None:
    """无assertive claim(全裸片段)→strict回退: NIE照旧阻塞, 全support照旧support."""
    all_bare_nie = (
        _claim("c1", "添加", NIE),
        _claim("c2", "查询", NIE),
    )
    assert _module("assertive_strict")._aggregate(all_bare_nie)[0] == NIE
    all_bare_sup = (
        _claim("c1", "添加", SUP, method="exact_statement"),
    )
    assert _module("assertive_strict")._aggregate(all_bare_sup)[0] == SUP


def test_assertive_strict_refute_wins_from_any_claim() -> None:
    results = (
        _claim("c1", "系统支持热插拔连接", SUP, method="exact_statement"),
        _claim("c2", "添加", REF, method="identifier_exact_match"),
    )
    assert _module("assertive_strict")._aggregate(results)[0] == REF


# ── assertive_ratio语义 ─────────────────────────────────────────────────────

def test_assertive_ratio_excludes_bare_and_inability_nie_from_pool() -> None:
    """裸名词NIE与能力不足NIE既不投票也不否决: ratio=1.0→support."""
    results = (
        _claim("c1", "系统支持热插拔连接", SUP, method="exact_statement"),
        _claim("c2", "系统提供数据缓存功能", SUP, method="nli_residual"),
        _claim("c3", "添加", NIE),
        _claim("c4", "查询", NIE, method="semantic_unresolved"),
    )
    verdict, diagnostics = _module("assertive_ratio")._aggregate(results)
    assert verdict == SUP
    assert any(d.startswith("agg_assertive_ratio_1.00")
               for d in diagnostics)


def test_assertive_ratio_active_nie_counts_in_denominator() -> None:
    """active-NIE(显式负观察)计入分母对抗support."""
    results = (
        _claim("c1", "系统支持热插拔连接", SUP, method="exact_statement"),
        _active_nie("c2", "系统包括数据查询功能"),
        _active_nie("c3", "系统包括数据删除功能"),
        _claim("c4", "添加", NIE),
    )
    # pool = 1 support + 2 active NIE → ratio 0.33 < τ
    verdict, diagnostics = _module("assertive_ratio")._aggregate(results)
    assert verdict == NIE
    assert any("0.33" in d for d in diagnostics)


def test_assertive_ratio_boundary_tau_is_inclusive() -> None:
    """4/5 = 0.80 = τ(默认0.8) → support(边界含等号; 第5条是active-NIE)."""
    assert _ASSERTIVE_SUPPORT_RATIO == 0.80
    supports = tuple(
        _claim(f"c{i}", "系统支持功能甲乙丙丁", SUP, method="exact_statement")
        for i in range(4))
    blockers = (_active_nie("c5", "系统包括数据查询功能"),)
    verdict, diagnostics = _module("assertive_ratio")._aggregate(
        supports + blockers)
    assert verdict == SUP  # 4 / 5 = 0.80 exactly -> support
    assert any(d.startswith("agg_assertive_ratio_0.80")
               for d in diagnostics)


def test_assertive_ratio_below_tau_stays_nie() -> None:
    supports = tuple(
        _claim(f"c{i}", "系统支持功能甲乙丙丁", SUP, method="exact_statement")
        for i in range(3))
    blockers = (
        _active_nie("c4", "系统包括数据查询功能"),
        _active_nie("c5", "系统包括数据删除功能"),
    )
    # pool = 3 support / 5 = 0.60 < 0.80
    assert _module("assertive_ratio")._aggregate(
        supports + blockers)[0] == NIE


def test_assertive_ratio_empty_pool_stays_nie() -> None:
    """无assertive可判定claim→保守NIE(不空转成support)."""
    results = (
        _claim("c1", "添加", NIE),
        _claim("c2", "查询", NIE, method="semantic_unresolved"),
    )
    verdict, diagnostics = _module("assertive_ratio")._aggregate(results)
    assert verdict == NIE
    assert "agg_assertive_ratio_no_decidable_claim" in diagnostics


def test_assertive_ratio_refute_wins() -> None:
    results = (
        _claim("c1", "系统支持热插拔连接", SUP, method="exact_statement"),
        _claim("c2", "添加", REF, method="identifier_exact_match"),
    )
    assert _module("assertive_ratio")._aggregate(results)[0] == REF


def test_assertive_ratio_tau_is_module_level_sweepable() -> None:
    """τ为模块级常量(评测脚本monkeypatch扫描, 同_DOMINANT_SUPPORT_RATIO口径)."""
    original = qa_module._ASSERTIVE_SUPPORT_RATIO
    try:
        qa_module._ASSERTIVE_SUPPORT_RATIO = 0.70
        supports = tuple(
            _claim(f"c{i}", "系统支持功能甲乙丙丁", SUP,
                   method="exact_statement") for i in range(3))
        blockers = (_active_nie("c4", "系统包括数据查询功能"),)
        # pool = 3 support / 4 = 0.75: τ0.70→support, τ0.80(默认)→NIE
        assert _module("assertive_ratio")._aggregate(
            supports + blockers)[0] == SUP
        qa_module._ASSERTIVE_SUPPORT_RATIO = 0.80
        assert _module("assertive_ratio")._aggregate(
            supports + blockers)[0] == NIE
    finally:
        qa_module._ASSERTIVE_SUPPORT_RATIO = original


# ── 注册与构造 ──────────────────────────────────────────────────────────────

def test_aggregation_variants_registered() -> None:
    assert "assertive_strict" in AGGREGATION_VARIANTS
    assert "assertive_ratio" in AGGREGATION_VARIANTS
    assert AGGREGATION_VARIANTS[0] == "strict"  # 默认档位不变


def test_new_aggregations_accepted_at_construction() -> None:
    for variant in ("assertive_strict", "assertive_ratio"):
        assert QAConsistencyModule(aggregation=variant).aggregation == variant


def test_unknown_aggregation_rejected() -> None:
    with pytest.raises(ValueError, match="aggregation"):
        QAConsistencyModule(aggregation="assertive_loose")


# ── verify()端到端: 蒸馏切分器塌方场景的救回 ───────────────────────────────

def _rescue_request() -> QAInput:
    """assertive support + 裸名词NIE的典型蒸馏切分器输出形态."""
    return QAInput(
        instance_id="qa-assert-1",
        question="系统支持热插拔吗？",
        answer="系统支持热插拔连接。添加。",
        context_freeze_id="frozen-assert-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="系统支持热插拔连接。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.6"),
            scope_id="doc01:3.6",
        ),),
    )


def _patched_decompose(question: str, answer: str) -> list[AnswerClaim]:
    del question
    return [AnswerClaim(kind="semantic", text="系统支持热插拔连接。"),
            AnswerClaim(kind="semantic", text="添加")]


def test_verify_strict_collapses_on_bare_noun_nie() -> None:
    original = qa_module.decompose_claims
    qa_module.decompose_claims = _patched_decompose
    try:
        module = QAConsistencyModule(aggregation="strict")
        assert module.verify(_rescue_request()).verdict == NIE
    finally:
        qa_module.decompose_claims = original


def test_verify_assertive_variants_rescue_bare_noun_collapse() -> None:
    original = qa_module.decompose_claims
    qa_module.decompose_claims = _patched_decompose
    try:
        for variant in ("assertive_strict", "assertive_ratio"):
            module = QAConsistencyModule(aggregation=variant)
            result = module.verify(_rescue_request())
            assert result.verdict == SUP, variant
            assert any(claim.claim_text == "添加"
                       for claim in result.claim_results)
    finally:
        qa_module.decompose_claims = original
