"""Contract tests for the post-retrieval QA consistency module."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_mutations import (  # noqa: E402
    propose_exact_numeric_conflict,
    propose_unsupported_answer,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import (  # noqa: E402
    QAConsistencyModule,
    _extract_numeric_claims,
)
from algorithms.consistency.qa_router import route_question  # noqa: E402


def sample_request() -> QAInput:
    return QAInput(
        instance_id="qa-1",
        question="系统响应时间要求是多少？",
        answer="响应时间为200ms。",
        context_freeze_id="frozen-context-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="响应时间为200ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1", page=3),
            scope_id="doc01:3.2.1",
            completeness="open",
        ),),
    )


def test_question_router_returns_candidate_not_verdict() -> None:
    assert "PARAM-01" in route_question("系统响应时间要求是多少？")
    assert route_question("完全陌生的问题") == ()


def test_module_consumes_frozen_context_without_retrieval() -> None:
    request = sample_request()
    result = QAConsistencyModule().verify(request)
    assert result.instance_id == request.instance_id
    assert result.question == request.question
    assert result.verdict == "support"
    assert result.evidence_chain == request.evidence
    assert result.considered_evidence_ids == ("e1",)
    assert result.context_freeze_id == request.context_freeze_id
    assert len(result.context_hash) == 64
    assert "PARAM-01" in result.claim_results[0].check_item_candidates
    assert result.claim_results[0].evidence_refs == ("e1",)
    assert result.context_integrity == "unknown"
    assert result.applicability == "applicable"


def test_real_verifier_checks_qa_answer_against_frozen_context() -> None:
    request = sample_request()
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "support"
    assert result.claim_results[0].evidence_refs == ("e1",)
    assert result.evidence_chain[0].source_ref.section == "3.2.1"


def test_numeric_answer_is_bound_to_question_subject_and_context_interval() -> None:
    request = QAInput(
        instance_id="qa-short-answer",
        question="系统响应时间要求是多少？",
        answer="200ms",
        context_freeze_id="freeze-short-answer",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="系统响应时间不超过200ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "support"
    assert result.claim_results[0].claim_text.startswith("响应时间")
    assert result.claim_results[0].method == "numeric_interval"


def test_numeric_question_context_conflict_is_refute() -> None:
    request = QAInput(
        instance_id="qa-numeric-conflict",
        question="系统响应时间要求是多少？",
        answer="响应时间不超过200ms。",
        context_freeze_id="freeze-conflict",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="系统响应时间不小于300ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "refute"
    assert result.claim_results[0].evidence_refs == ("e1",)


def test_context_internal_numeric_conflict_is_partial_not_arbitrarily_resolved() -> None:
    request = QAInput(
        instance_id="qa-context-conflict",
        question="系统响应时间要求是多少？",
        answer="响应时间不超过200ms。",
        context_freeze_id="freeze-context-conflict",
        evidence=(
            RetrievedEvidence("e1", "响应时间不超过150ms。", "text",
                              SourceRef("doc01", section="3.2.1"), "scope-a"),
            RetrievedEvidence("e2", "响应时间不小于300ms。", "table",
                              SourceRef("doc01", section="3.2.2"), "scope-b"),
        ),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "not_in_evidence"
    assert result.status == "partial"
    assert "one_or_more_claims_unresolved" in result.diagnostics


def test_explicit_negative_evidence_refutes_positive_quote_claim() -> None:
    request = QAInput(
        instance_id="qa-negative-evidence",
        question="context定义了X功能吗？",
        answer="定义了「X功能」。",
        context_freeze_id="freeze-negative",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="本系统不支持「X功能」。",
            source_type="text",
            source_ref=SourceRef("doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "refute"
    assert result.claim_results[0].method == "explicit_quote_polarity"


def test_missing_enum_member_in_open_context_is_not_in_evidence() -> None:
    request = QAInput(
        instance_id="qa-enum-open",
        question="系统包括哪些功能？",
        answer="系统包括A功能、B功能。",
        context_freeze_id="freeze-enum",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="系统包括A功能。", source_type="text",
            source_ref=SourceRef("doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "not_in_evidence"


def test_empty_context_is_rejected_instead_of_labelled() -> None:
    request = sample_request()
    empty = QAInput(request.instance_id, request.question, request.answer,
                    request.context_freeze_id, ())
    result = QAConsistencyModule().verify(empty)
    assert result.verdict == "not_in_evidence"
    assert result.status == "partial"
    assert "empty_retrieved_context" in result.diagnostics


def test_module_validates_frozen_input_contract() -> None:
    request = sample_request()
    bad = QAInput("", request.question, request.answer,
                  request.context_freeze_id, request.evidence)
    with pytest.raises(ValueError, match="instance_id"):
        QAConsistencyModule().verify(bad)


def test_answer_mutation_changes_answer_only_and_proves_numeric_conflict() -> None:
    request = QAInput(
        instance_id="qa-num",
        question="响应时间是多少？",
        answer="响应时间为200ms。",
        context_freeze_id="ctx-num",
        evidence=(RetrievedEvidence(
            evidence_id="e-num", text="响应时间为200ms。", source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    mutation = propose_exact_numeric_conflict(
        request, evidence_id="e-num", mutated_value=300)
    assert mutation.answer_after == "响应时间为300ms。"
    assert mutation.answer_before == request.answer
    assert mutation.question == request.question
    assert mutation.context_freeze_id == request.context_freeze_id
    assert mutation.target == "answer"
    assert mutation.gold_candidate == "refute"
    assert mutation.requires_manual_review is False
    assert mutation.context_refs == (request.evidence[0].source_ref,)


def test_answer_mutation_rejects_unsupported_source_pair() -> None:
    request = sample_request()
    try:
        propose_exact_numeric_conflict(request, evidence_id="missing", mutated_value=300)
    except ValueError as exc:
        assert "unknown evidence_id" in str(exc)
    else:
        raise AssertionError("unknown evidence must be rejected")


def test_unsupported_mutation_does_not_forge_nie_gold() -> None:
    request = sample_request()
    mutation = propose_unsupported_answer(
        request,
        answer_after="数据吞吐量为100GB/s。",
        operator_id="ANSWER-UNSUPPORTED-REVIEW",
        check_item="PARAM-05",
    )
    assert mutation.gold_candidate is None
    assert mutation.requires_manual_review is True
    assert mutation.context_hash != request.context_freeze_id
    assert "未命中不能证明" in mutation.proof


def test_identifier_channel_supports_exact_hit_and_refutes_same_subject_mismatch() -> None:
    supported = QAInput(
        instance_id="qa-id-support",
        question="数据查询接口的标识是什么？",
        answer="数据查询接口的标识为PZXQ-JK-SJCX。",
        context_freeze_id="freeze-id",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="数据查询接口的标识为PZXQ-JK-SJCX。",
            source_type="text", source_ref=SourceRef(doc_id="doc01", section="3.4"),
            scope_id="doc01:3.4"),),
    )
    result = QAConsistencyModule().verify(supported)
    assert result.verdict == "support"
    assert result.claim_results[0].method == "identifier_exact_match"

    conflicted = QAInput(
        instance_id="qa-id-conflict",
        question="数据库初始化用例的标识是什么？",
        answer="数据库初始化用例的标识为PZXQ-GN-SQLFW-SJKCZ-SJKCSH。",
        context_freeze_id="freeze-id",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="表4中数据库初始化的标识为PZXQ-GN-SJKCZ-SJKCSH。",
            source_type="table", source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    result = QAConsistencyModule().verify(conflicted)
    assert result.verdict == "refute"
    assert "显式值冲突" in result.claim_results[0].rationale


def test_identifier_channel_unmatched_without_subject_statement_is_nie() -> None:
    request = QAInput(
        instance_id="qa-id-nie",
        question="系统的接口标识是什么？",
        answer="接口标识为PZXQ-JK-UNKNOWN。",
        context_freeze_id="freeze-id",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="接口标识和接口图如48所示。",
            source_type="text", source_ref=SourceRef(doc_id="doc01", section="3.4"),
            scope_id="doc01:3.4"),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "not_in_evidence"


def test_structural_decomposition_replaces_blob_fallback() -> None:
    request = QAInput(
        instance_id="qa-structural",
        question="获取LOB时连接错误如何处理？",
        answer=("获取LOB时连接错误处理流程：\n\n"
                "1. **连接检测**：系统检测数据库连接状态。\n\n"
                "2. **异常流E1**：系统提示获取失败，用例结束。\n\n"
                "3. **通知用户**：系统向用户提示连接错误。"),
        context_freeze_id="freeze-struct",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text=("<table><tr><td><p>Use Case 名称：获取LOB</p></td></tr>"
                  "<tr><td colspan=\"3\"><p>异常流E1：系统提示获取失败，用例结束"
                  "</p></td></tr></table>"),
            source_type="table",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    result = QAConsistencyModule().verify(request)
    assert len(result.claim_results) >= 3
    assert any("系统提示获取失败" in claim.claim_text
               for claim in result.claim_results)
    supported = [claim for claim in result.claim_results
                 if claim.method in ("exact_statement", "statement_exact")
                 and claim.verdict == "support"]
    assert supported
    assert any(claim.evidence_refs == ("e1",) for claim in supported)


def test_nli_residual_channel_refutes_scope_matched_contradiction() -> None:
    def fake_nli(pairs):
        verdicts = []
        for premise, hypothesis in pairs:
            if "前置条件：无" in premise and "前置条件" in hypothesis:
                verdicts.append("contradiction")
            else:
                verdicts.append("neutral")
        return verdicts

    request = QAInput(
        instance_id="qa-nli",
        question="数据库连接用例的前置条件是什么？",
        answer="数据库连接用例的前置条件是数据库初始化成功。",
        context_freeze_id="freeze-nli",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text=("<table><tr><td><p>Use Case 名称：数据库连接</p></td></tr>"
                  "<tr><td colspan=\"3\"><p>前置条件：无</p></td></tr></table>"),
            source_type="table",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    result = QAConsistencyModule(semantic_nli=fake_nli).verify(request)
    assert result.verdict == "refute"
    assert any(claim.method == "nli_residual" and claim.verdict == "refute"
               for claim in result.claim_results)
    assert all(claim.evidence_refs == ("e1",)
               for claim in result.claim_results if claim.method == "nli_residual")


def test_nli_residual_neutral_stays_unresolved() -> None:
    request = QAInput(
        instance_id="qa-nli-neutral",
        question="系统支持热插拔吗？",
        answer="系统支持热插拔连接。",
        context_freeze_id="freeze-nli",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="系统支持多种连接方式。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.6"),
            scope_id="doc01:3.6"),),
    )
    result = QAConsistencyModule(
        semantic_nli=lambda pairs: ["neutral"] * len(pairs)).verify(request)
    assert result.verdict == "not_in_evidence"


def test_composite_answer_aggregation_refute_takes_precedence() -> None:
    request = QAInput(
        instance_id="qa-composite", question="系统包括哪些功能？",
        answer="系统包括「X功能」，并且包括「Y功能」。",
        context_freeze_id="freeze-composite",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="系统支持「X功能」，但不支持「Y功能」。",
            source_type="text", source_ref=SourceRef("doc01", section="3.2.1"),
            scope_id="doc01:3.2.1"),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "refute"
    assert any(claim.verdict == "support" for claim in result.claim_results)
    assert any(claim.verdict == "refute" for claim in result.claim_results)


def test_parallel_quoted_answer_items_remain_independent_claims() -> None:
    claims = QAConsistencyModule()._decompose(
        "系统包括哪些功能？", "系统包括「X功能」和「Y功能」。"
    )

    assert [(claim.kind, claim.text) for claim in claims] == [
        ("quoted", "X功能"),
        ("quoted", "Y功能"),
    ]


def test_condition_prefix_is_not_attached_to_numeric_subject() -> None:
    claims = _extract_numeric_claims("在高负载条件下，响应时间不超过200ms。")

    assert claims == [("响应时间", "不超过", "200", "ms")]


def test_bare_numeric_answer_and_extra_numeric_answer_are_separate_claims() -> None:
    claims = QAConsistencyModule()._decompose(
        "系统响应时间要求是多少？", "200ms，吞吐量为100MB/s。"
    )

    assert [(claim.kind, claim.attr, claim.value) for claim in claims] == [
        ("numeric", "吞吐量", "100"),
        ("numeric", "响应时间", "200"),
    ]


# ── per-claim fusion key: enumeration-prefix strip (G4 P1 c-fix) ──────────

def _claim_result(cid: str, text: str, verdict: str, method: str) -> ClaimResult:
    return ClaimResult(
        claim_id=cid, claim_text=text, verdict=verdict,
        check_item_candidates=(), evidence_refs=(), rationale="",
        method=method, confidence=0.0)


def test_fuse_per_claim_merges_enumeration_prefixed_duplicate() -> None:
    """S1QA-066/069机制: "1．X"(序列通道NIE)与"X"(L3已判support)融合为单claim."""
    fused = QAConsistencyModule()._fuse_per_claim((
        _claim_result("S1QA-066-ac02", "查询结果缓存：提供对查询结果的数据缓存功能",
                      "support", "llm_residual"),
        _claim_result("S1QA-066-seq01", "1．查询结果缓存：提供对查询结果的数据缓存功能",
                      "not_in_evidence", "sequence_alignment"),
    ))
    assert len(fused) == 1
    assert fused[0].verdict == "support"
    # 幸存claim的文本不变(前缀剥离只影响分组, 不改写claim_result)
    assert fused[0].claim_text == "查询结果缓存：提供对查询结果的数据缓存功能"


def test_fuse_per_claim_prefix_forms_and_refute_priority() -> None:
    """全角/半角/顿号/逗号前缀均可合并; refute仍在融合层优先."""
    for prefix in ("1．", "2.", "3、", "4，", "十二．"):
        fused = QAConsistencyModule()._fuse_per_claim((
            _claim_result("c1", "删除数据记录", "support", "exact_statement"),
            _claim_result("c2", f"{prefix}删除数据记录", "not_in_evidence",
                          "sequence_alignment"),
        ))
        assert len(fused) == 1, prefix
        assert fused[0].verdict == "support", prefix
    fused = QAConsistencyModule()._fuse_per_claim((
        _claim_result("c1", "修改数据记录", "support", "exact_statement"),
        _claim_result("c2", "1．修改数据记录", "refute", "id_join_registry"),
    ))
    assert len(fused) == 1
    assert fused[0].verdict == "refute"


def test_fuse_per_claim_without_prefix_stays_exact() -> None:
    """无前缀的不同文本仍不合并——前缀剥离不引入跨claim误融合."""
    fused = QAConsistencyModule()._fuse_per_claim((
        _claim_result("c1", "响应时间为200ms", "support", "numeric_interval"),
        _claim_result("c2", "响应时间为300ms", "not_in_evidence",
                      "semantic_unresolved"),
    ))
    assert len(fused) == 2
