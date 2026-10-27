"""Contract tests for the learned cascade router (C4 learning half).

Deterministic kernels locked here: the pre-L2 feature extraction, the
minimum-cost-correct oracle labeling (four route classes + all-wrong
fallback), the learner train/save/load/predict round-trip on synthetic
data (seed=42), and the QAConsistencyModule integration — per-route
dispatch with monkeypatched L2/L3 channels (no real model, no LLM call),
the router_decision diagnostic, and the load-failure fallback to the
fixed cascade.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency import llm_residual  # noqa: E402
from algorithms.consistency import nli_residual  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.router import (  # noqa: E402
    FEATURE_ORDER,
    ROUTE_COSTS,
    ROUTE_LABELS,
    LearnedRouter,
    extract_route_features,
    oracle_route,
    save_scripted_router,
    train_router,
)


def sample_request() -> QAInput:
    return QAInput(
        instance_id="qa-router-1",
        question="SQL访问修改数据功能包括哪些操作",
        answer="所有操作均支持在桌面、平版和平板设备上运行。",
        context_freeze_id="frozen-router-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="SQL访问功能的方式名称：平板、桌面、手持。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc04", section="3.2.1"),
            scope_id="doc04:3.2.1",
        ), RetrievedEvidence(
            evidence_id="e2",
            text="对象化访问功能的方式名称：平板、桌面。",
            source_type="table",
            source_ref=SourceRef(doc_id="doc04", section="3.2.2"),
            scope_id="doc04:3.2.2",
        )),
    )


def claim(claim_id: str, verdict: str, method: str) -> ClaimResult:
    return ClaimResult(
        claim_id=claim_id,
        claim_text=f"claim-{claim_id}",
        verdict=verdict,
        check_item_candidates=("TERM-01",),
        evidence_refs=(),
        rationale="",
        method=method,
        confidence=0.9,
    )


# ── feature extraction ─────────────────────────────────────

def test_feature_extraction_counts_and_shares() -> None:
    request = sample_request()
    claim_results = (
        claim("c01", "support", "e1_template_match"),
        claim("c02", "refute", "l0_entity_detector:TERM-05"),
        claim("c03", "not_in_evidence", "semantic_unresolved"),
        claim("c04", "not_in_evidence", "conservative_unresolved"),
        claim("c05", "not_in_evidence", "numeric_interval"),
    )
    features = extract_route_features(
        question=request.question,
        answer=request.answer,
        evidence=request.evidence,
        claim_results=claim_results,
        claim_kinds=("semantic", "semantic", "numeric"),
        check_items=("TERM-03", "TERM-08", "PARAM-01", "LOGIC-02"),
    )
    assert set(features) == set(FEATURE_ORDER)
    assert features["n_evidence"] == 2.0
    assert features["evidence_table_fraction"] == 0.5
    assert features["question_len"] == len(request.question.replace(" ", ""))
    assert features["answer_len"] == len(request.answer.replace(" ", ""))
    assert features["n_claims"] == 3.0
    assert features["claim_numeric"] == 1.0
    assert features["claim_semantic"] == 2.0
    assert features["claim_quoted"] == 0.0
    assert features["n_check_items"] == 4.0
    assert features["check_term"] == 2.0
    assert features["check_param"] == 1.0
    assert features["check_logic"] == 1.0
    assert features["check_gjb"] == 0.0
    assert features["l1_support"] == 1.0
    assert features["l1_refute"] == 1.0
    assert features["l1_nie"] == 3.0
    assert features["l1_expert_hits"] == 2.0
    assert features["residual_count"] == 2.0


def test_feature_extraction_empty_evidence_is_total() -> None:
    features = extract_route_features(
        question="问题", answer="答案", evidence=(), claim_results=(),
        claim_kinds=(), check_items=())
    assert features["n_evidence"] == 0.0
    assert features["evidence_table_fraction"] == 0.0


# ── oracle labeling: four route classes ────────────────────

def test_oracle_l1_correct_is_accept_l1() -> None:
    assert oracle_route("support", "refute", "refute", "refute", "support") \
        == "accept_l1"


def test_oracle_l2_fix_is_accept_l2() -> None:
    assert oracle_route("not_in_evidence", "refute", "refute", "support",
                        "refute") == "accept_l2"


def test_oracle_only_escalation_fixes_is_call_l2() -> None:
    assert oracle_route("not_in_evidence", "not_in_evidence", "refute",
                        "not_in_evidence", "refute",
                        escalation_calls=1) == "call_l2"


def test_oracle_only_direct_l3_fixes_is_escalate_l3() -> None:
    assert oracle_route("not_in_evidence", "not_in_evidence",
                        "not_in_evidence", "refute", "refute") \
        == "escalate_l3"


def test_oracle_all_wrong_falls_back_to_accept_l2() -> None:
    assert oracle_route("support", "support", "support", "support", "refute") \
        == "accept_l2"


def test_oracle_unprobed_routes_count_as_not_correct() -> None:
    assert oracle_route("support", None, None, None, "refute") == "accept_l2"
    assert oracle_route("support", None, None, None,
                        "not_in_evidence") == "accept_l2"


def test_oracle_direct_l3_beats_escalated_call_l2_on_cost() -> None:
    """call_l2(2+10·k) vs escalate_l3(10): k>=1时直接L3更便宜."""
    assert oracle_route("not_in_evidence", "not_in_evidence", "refute",
                        "refute", "refute", escalation_calls=1) \
        == "escalate_l3"
    assert oracle_route("not_in_evidence", "not_in_evidence", "refute",
                        "refute", "refute", escalation_calls=0) == "call_l2"


def test_route_costs_follow_spec_units() -> None:
    assert ROUTE_COSTS["accept_l1"] == 0.0
    assert ROUTE_COSTS["accept_l2"] == 1.0
    assert ROUTE_COSTS["call_l2"] > ROUTE_COSTS["accept_l2"]
    assert ROUTE_COSTS["escalate_l3"] == 10.0
    assert set(ROUTE_LABELS) == set(ROUTE_COSTS)


# ── learner train / save / load / predict round-trip ───────

def synthetic_rows(n_per_class: int = 60) -> list[dict]:
    """Separable synthetic probe rows: residual_count & l1_refute decide."""
    rows: list[dict] = []
    templates = {
        "accept_l1": {"l1_refute": 0.0, "residual_count": 0.0},
        "accept_l2": {"l1_refute": 0.0, "residual_count": 3.0},
        "call_l2": {"l1_refute": 1.0, "residual_count": 3.0},
        "escalate_l3": {"l1_refute": 2.0, "residual_count": 5.0},
    }
    for label, template in templates.items():
        for i in range(n_per_class):
            features = {name: 0.0 for name in FEATURE_ORDER}
            features.update(template)
            features["question_len"] = 10.0 + (i % 7)
            rows.append({"features": features, "oracle_route": label})
    return rows


def test_train_router_round_trip(tmp_path: Path) -> None:
    rows = synthetic_rows()
    payload, report = train_router(rows, seed=42)
    assert report["seed"] == 42
    assert report["selected_model"] in ("gradient_boosting",
                                        "logistic_regression")
    router = LearnedRouter(payload)
    path = router.save(tmp_path / "router.joblib")
    loaded = LearnedRouter.load(path)
    assert loaded.kind == "learned"
    assert loaded.model_type == router.model_type

    probe = {"l1_refute": 1.0, "residual_count": 3.0}
    assert loaded.route(probe) == "call_l2"
    probs = loaded.probabilities(probe)
    assert set(probs) == set(ROUTE_LABELS)
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-6)

    assert loaded.route({"l1_refute": 0.0, "residual_count": 0.0}) == "accept_l1"
    assert loaded.route({"l1_refute": 0.0, "residual_count": 3.0}) == "accept_l2"
    assert loaded.route({"l1_refute": 2.0, "residual_count": 5.0}) \
        == "escalate_l3"


def test_train_router_single_class_degrades_to_scripted() -> None:
    rows = synthetic_rows(n_per_class=3)[:3]
    payload, report = train_router(rows, seed=42)
    assert report["selected_model"] == "majority_single_class"
    router = LearnedRouter(payload)
    assert router.route({"residual_count": 99.0}) == "accept_l1"


def test_cost_alpha_prefers_cheaper_routes() -> None:
    rows = synthetic_rows()
    payload, _ = train_router(rows, seed=42)
    router = LearnedRouter(payload)
    router.cost_alpha = 8.0
    assert router.route({}) == "accept_l1"
    router.cost_alpha = 0.0
    assert router.route({}) == "accept_l1"


def test_load_rejects_bad_payloads(tmp_path: Path) -> None:
    import joblib

    bad = tmp_path / "bad.joblib"
    joblib.dump({"format": "something_else"}, bad)
    with pytest.raises(ValueError):
        LearnedRouter.load(bad)
    with pytest.raises(OSError):
        LearnedRouter.load(tmp_path / "missing.joblib")


def test_scripted_router_records_features(tmp_path: Path) -> None:
    path = save_scripted_router(tmp_path / "s.joblib", "call_l2", record=True)
    router = LearnedRouter.load(path)
    assert router.route({"question_len": 3.0}) == "call_l2"
    assert router.recorded_features == [{"question_len": 3.0}]
    assert LearnedRouter.load(
        save_scripted_router(tmp_path / "s2.joblib", "accept_l1")
    ).route({}) == "accept_l1"


# ── qa_module integration (monkeypatched L2/L3) ────────────

@pytest.fixture()
def patch_nli(monkeypatch):
    state = {"calls": 0, "probs": []}

    def fake_load(path: str) -> dict:
        return {"mode": "cpu", "error": ""}

    def fake_infer(entry: dict, pairs: list) -> list:
        state["calls"] += len(pairs)
        queue = list(state["probs"])
        return queue[:len(pairs)] if queue else [
            {"entailment": 0.1, "neutral": 0.1, "contradiction": 0.8}
            for _ in pairs]

    monkeypatch.setattr(nli_residual, "_load_model", fake_load)
    monkeypatch.setattr(nli_residual, "_infer", fake_infer)
    return state


@pytest.fixture()
def patch_llm(monkeypatch):
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


def routed_module(tmp_path: Path, route: str, **kwargs) -> QAConsistencyModule:
    path = save_scripted_router(tmp_path / f"router_{route}.joblib", route)
    return QAConsistencyModule(
        use_experts=False, use_learned_router=str(path),
        nli_model_path="fake-path", **kwargs)


def test_module_learned_router_implies_both_channels(tmp_path: Path) -> None:
    module = routed_module(tmp_path, "accept_l1")
    assert module.use_nli_residual is True
    assert module.use_llm_residual is True
    assert module.use_cascade is False
    assert module.router is not None


def test_module_router_accept_l1_skips_residual_channels(
        tmp_path: Path, patch_nli, patch_llm) -> None:
    result = routed_module(tmp_path, "accept_l1").verify(sample_request())
    assert patch_nli["calls"] == 0
    assert patch_llm["calls"] == []
    assert result.verdict == "not_in_evidence"
    assert "router_decision:accept_l1" in result.diagnostics


def test_module_router_accept_l2_runs_l2_without_escalation(
        tmp_path: Path, patch_nli, patch_llm) -> None:
    result = routed_module(tmp_path, "accept_l2").verify(sample_request())
    assert patch_nli["calls"] > 0
    assert patch_llm["calls"] == []
    assert result.verdict == "refute"
    assert "router_decision:accept_l2" in result.diagnostics
    assert "cascade_llm_calls_0" not in result.diagnostics


def test_module_router_call_l2_escalates_nli_refutes(
        tmp_path: Path, patch_nli, patch_llm) -> None:
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "not_in_evidence",
        "evidence_refs": [], "rationale": "证据无该设备集合声明",
        "confidence": 0.7,
    }]}]
    result = routed_module(tmp_path, "call_l2").verify(sample_request())
    assert patch_nli["calls"] > 0
    assert len(patch_llm["calls"]) == 1
    assert result.verdict == "not_in_evidence"
    assert "router_decision:call_l2" in result.diagnostics
    assert "cascade_llm_calls_1" in result.diagnostics


def test_module_router_escalate_l3_skips_l2(
        tmp_path: Path, patch_nli, patch_llm) -> None:
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "refute",
        "evidence_refs": ["ev-1"], "rationale": "证据给出平板、桌面，矛盾",
        "confidence": 0.93,
    }]}]
    result = routed_module(tmp_path, "escalate_l3").verify(sample_request())
    assert patch_nli["calls"] == 0
    assert len(patch_llm["calls"]) == 1
    assert result.verdict == "refute"
    assert any(claim.method == "llm_residual" for claim in result.claim_results)
    assert "router_decision:escalate_l3" in result.diagnostics


def test_module_learned_router_matches_trained_model(
        tmp_path: Path, patch_nli, patch_llm) -> None:
    """A real trained router (synthetic, separable) drives the dispatch."""
    payload, _ = train_router(synthetic_rows(), seed=42)
    path = LearnedRouter(payload).save(tmp_path / "trained.joblib")
    module = QAConsistencyModule(
        use_experts=False, use_learned_router=str(path),
        nli_model_path="fake-path")
    result = module.verify(sample_request())
    decisions = [d for d in result.diagnostics if d.startswith("router_decision:")]
    assert len(decisions) == 1
    assert decisions[0] in {f"router_decision:{r}" for r in ROUTE_LABELS}


def test_module_router_load_failure_falls_back_to_fixed_cascade(
        tmp_path: Path, patch_nli, patch_llm) -> None:
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "not_in_evidence",
        "evidence_refs": [], "rationale": "证据无该设备集合声明",
        "confidence": 0.7,
    }]}]
    module = QAConsistencyModule(
        use_experts=False, use_learned_router=str(tmp_path / "missing.joblib"),
        nli_model_path="fake-path")
    assert module.router is None
    assert module.use_cascade is True
    assert module.use_nli_residual is True
    assert module.use_llm_residual is True
    result = module.verify(sample_request())
    assert "router_load_failed_fallback_cascade" in result.diagnostics
    assert "router_decision:" not in ";".join(result.diagnostics)
    assert "cascade_llm_calls_1" in result.diagnostics


def test_module_learned_router_off_keeps_legacy_dispatch(
        patch_nli, patch_llm) -> None:
    """use_learned_router=None (default) must behave exactly as before."""
    module = QAConsistencyModule(use_experts=False, use_nli_residual=True,
                                 nli_model_path="fake-path")
    assert module.router is None
    result = module.verify(sample_request())
    assert result.verdict == "refute"
    assert patch_llm["calls"] == []
    assert all(not d.startswith("router_decision:")
               for d in result.diagnostics)
