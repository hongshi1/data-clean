"""Contract tests for the L3 LLM residual verification channel."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency import llm_residual  # noqa: E402
from algorithms.consistency.llm_residual import (  # noqa: E402
    verify_residual_claims,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402


def sample_request() -> QAInput:
    return QAInput(
        instance_id="qa-res-1",
        question="系统响应时间要求是多少？",
        answer="响应时间为200ms。",
        context_freeze_id="frozen-res-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="响应时间为200ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )


def unresolved_result(claim_id: str, claim_text: str) -> ClaimResult:
    return ClaimResult(
        claim_id=claim_id,
        claim_text=claim_text,
        verdict="not_in_evidence",
        check_item_candidates=("PARAM-01",),
        evidence_refs=(),
        rationale="当前语义声明没有经过验证的三态判定器",
        method="semantic_unresolved",
        confidence=0.0,
    )


def statements_for(request: QAInput) -> list:
    from algorithms.consistency.evidence_statements import linearize_context

    return linearize_context(request.evidence)


@pytest.fixture()
def patch_llm(monkeypatch):
    """Replace the cached LLM call with a scriptable fake (no .env needed).

    The fake honours the ``_call_llm`` contract: it always returns a dict
    (``llm_json`` itself never returns raw strings) and consumes one queued
    response per invocation.
    """
    state = {"calls": [], "queue": []}

    def fake_call(prompt: str) -> dict:
        state["calls"].append(prompt)
        assert state["queue"], "unexpected extra LLM call"
        item = state["queue"].pop(0)
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, dict) else {}

    monkeypatch.setattr(llm_residual, "_call_llm", fake_call)
    return state


def test_llm_support_replaces_unresolved_claim(patch_llm) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-res-1-c01", "响应时间为200ms。")]
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "support",
        "evidence_refs": ["ev-1"], "rationale": "证据明确给出200ms",
        "confidence": 0.95,
    }]}]
    results = verify_residual_claims(request, residual,
                                     statements_for(request))
    assert len(results) == 1
    result = results[0]
    assert result.claim_id == "qa-res-1-c01"
    assert result.claim_text == "响应时间为200ms。"
    assert result.verdict == "support"
    assert result.method == "llm_residual"
    assert result.evidence_refs == ("e1",)
    assert result.check_item_candidates == ("PARAM-01",)
    assert result.confidence == 0.95
    assert "200ms" in patch_llm["calls"][0]


def test_refute_requires_confidence_gate_and_citation(patch_llm) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-res-1-c01", "响应时间为200ms。")]
    low_confidence = {"claims": [{
        "claim_id": "c1", "verdict": "refute",
        "evidence_refs": ["ev-1"], "rationale": "矛盾", "confidence": 0.5,
    }]}
    uncited = {"claims": [{
        "claim_id": "c1", "verdict": "refute",
        "evidence_refs": ["ev-99"], "rationale": "矛盾", "confidence": 0.9,
    }]}
    for payload in (low_confidence, uncited):
        patch_llm["queue"] = [payload]
        results = verify_residual_claims(request, residual,
                                         statements_for(request))
        assert results[0].verdict == "not_in_evidence", payload
        assert results[0].confidence == payload["claims"][0]["confidence"]
    assert "门控" in results[0].rationale or "证据编号" in results[0].rationale


def test_confident_cited_refute_is_kept(patch_llm) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-res-1-c01", "响应时间为500ms。")]
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "refute",
        "evidence_refs": ["ev-1"], "rationale": "证据给出200ms，与声明矛盾",
        "confidence": 0.93,
    }]}]
    results = verify_residual_claims(request, residual,
                                     statements_for(request))
    assert results[0].verdict == "refute"
    assert results[0].evidence_refs == ("e1",)


def test_parse_failure_retries_once_then_falls_back_to_nie(patch_llm) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-res-1-c01", "响应时间为200ms。")]
    patch_llm["queue"] = [{}, {}]
    results = verify_residual_claims(request, residual,
                                     statements_for(request))
    assert len(patch_llm["calls"]) == 2
    assert "无法解析" in patch_llm["calls"][1]
    assert results[0].verdict == "not_in_evidence"
    assert results[0].method == "llm_residual_failed"
    assert "保守NIE" in results[0].rationale


def test_api_failure_falls_back_to_nie_after_retry(patch_llm) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-res-1-c01", "响应时间为200ms。")]
    patch_llm["queue"] = [RuntimeError("LLM调用失败(glm+kimi)"),
                              RuntimeError("LLM调用失败(glm+kimi)")]
    results = verify_residual_claims(request, residual,
                                     statements_for(request))
    assert len(patch_llm["calls"]) == 2
    assert results[0].method == "llm_residual_failed"
    assert "RuntimeError" in results[0].rationale


def test_uncovered_claim_stays_conservative_nie(patch_llm) -> None:
    request = sample_request()
    residual = [
        unresolved_result("qa-res-1-c01", "响应时间为200ms。"),
        unresolved_result("qa-res-1-c02", "系统支持热备。"),
    ]
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "support",
        "evidence_refs": ["ev-1"], "rationale": "证据明确给出200ms",
        "confidence": 0.95,
    }]}]
    results = verify_residual_claims(request, residual,
                                     statements_for(request))
    assert [r.verdict for r in results] == ["support", "not_in_evidence"]
    assert results[1].method == "llm_residual"
    assert "未覆盖" in results[1].rationale


def test_no_residual_or_no_statements_is_noop(patch_llm) -> None:
    request = sample_request()
    assert verify_residual_claims(request, [], statements_for(request)) == []
    assert verify_residual_claims(
        request, [unresolved_result("qa-res-1-c01", "x")], []) == []
    assert patch_llm["calls"] == []


def test_statement_selection_prefers_scope_and_overlap(patch_llm) -> None:
    from algorithms.consistency.evidence_statements import EvidenceStatement

    statements = [
        EvidenceStatement("s1#s0", "s1", "完全无关的句子甲", "sentence", "", 1),
        EvidenceStatement("s2#s0", "s2", "BLOB数据操作的方式名称：平板、桌面", "方式名称",
                          "BLOB数据操作", 2),
        EvidenceStatement("s3#s0", "s3", "另一个无关句子乙", "sentence", "", 3),
    ]
    claims_text = "BLOB数据操作功能支持哪些设备？"
    selected = llm_residual._select_statements(claims_text, statements)
    assert selected[0].evidence_id == "s2"


def test_module_fuses_llm_support_over_unresolved_nie(patch_llm) -> None:
    request = QAInput(
        instance_id="qa-res-fuse",
        question="系统支持热插拔吗？",
        answer="系统支持热插拔连接。",
        context_freeze_id="frozen-res-3",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="系统支持多种连接方式。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.6"),
            scope_id="doc01:3.6",
        ),),
    )
    module = QAConsistencyModule(use_experts=False, use_llm_residual=True)
    patch_llm["queue"] = [{}, {}]
    assert module.verify(request).verdict == "not_in_evidence"
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "support",
        "evidence_refs": ["ev-1"], "rationale": "证据列举了连接方式支持",
        "confidence": 0.95,
    }]}]
    result = module.verify(request)
    assert result.verdict == "support"
    assert any(claim.method == "llm_residual" and claim.verdict == "support"
               for claim in result.claim_results)
    assert result.evidence_chain[0].evidence_id == "e1"


def test_module_skips_llm_when_refute_already_decided(patch_llm) -> None:
    request = QAInput(
        instance_id="qa-res-refute",
        question="系统响应时间要求是多少？",
        answer="响应时间不小于300ms。",
        context_freeze_id="frozen-res-2",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="响应时间不超过200ms。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
            scope_id="doc01:3.2.1",
        ),),
    )
    module = QAConsistencyModule(use_experts=False, use_llm_residual=True)
    result = module.verify(request)
    assert result.verdict == "refute"
    assert patch_llm["calls"] == []
    assert "llm_residual_call_failed" not in result.diagnostics
