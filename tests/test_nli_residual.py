"""Contract tests for the S4 residual NLI channel (deterministic, no GPU).

The fine-tuned model itself is a data artifact trained by
tools/train_residual_nli.py; these tests lock the deterministic kernels:
premise construction (nli_training), the EGT→NLI example mapping, the
hash split, statement selection, probability gating, verdict mapping,
dedup, the unavailable-model degradation, and the QAConsistencyModule
integration (residual dispatch, NLI-over-LLM precedence, and the S5
L2→L3 cascade escalation of NLI refute candidates).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency import llm_residual  # noqa: E402
from algorithms.consistency import nli_residual  # noqa: E402
from algorithms.consistency.evidence_statements import (  # noqa: E402
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.nli_residual import (  # noqa: E402
    verify_residual_claims_nli,
)
from algorithms.consistency.nli_training import (  # noqa: E402
    EGT_DATASET,
    VERDICT_TO_NLI,
    base_label_ids,
    build_dataset,
    build_premise,
    example_from_row,
    is_dev_sample,
    strip_html,
)
import algorithms.consistency.nli_training as nli_training  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402


def sample_request() -> QAInput:
    return QAInput(
        instance_id="qa-nli-1",
        question="SQL访问修改数据功能包括哪些操作",
        answer="所有操作均支持在桌面、平版和平板设备上运行。",
        context_freeze_id="frozen-nli-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="SQL访问功能的方式名称：平板、桌面、手持。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc04", section="3.2.1"),
            scope_id="doc04:3.2.1",
        ), RetrievedEvidence(
            evidence_id="e2",
            text="对象化访问功能的需求描述：提供对象化数据访问功能。",
            source_type="text",
            source_ref=SourceRef(doc_id="doc04", section="3.2.2"),
            scope_id="doc04:3.2.2",
        )),
    )


def unresolved_result(claim_id: str, claim_text: str) -> ClaimResult:
    return ClaimResult(
        claim_id=claim_id,
        claim_text=claim_text,
        verdict="not_in_evidence",
        check_item_candidates=("CS-01",),
        evidence_refs=(),
        rationale="当前语义声明没有经过验证的三态判定器",
        method="semantic_unresolved",
        confidence=0.0,
    )


def statements_for(request: QAInput) -> list[EvidenceStatement]:
    return linearize_context(request.evidence)


# ── nli_training: premise构造 ──────────────────────────────

def test_strip_html_removes_tags_and_collapses_whitespace() -> None:
    assert strip_html("<table><tr><td><p>平板</p></td><td>桌面</td></tr></table>"
                      ) == "平板 桌面"
    assert strip_html("a\n\nb\tc") == "a b c"


def test_build_premise_caps_total_and_orders_by_blocks() -> None:
    premise = build_premise("claim", ["甲" * 600, "乙" * 600, "丙" * 600],
                            per_block=500, total=1000)
    assert len(premise) == 1000
    assert premise.startswith("甲" * 500)
    assert "乙" in premise
    assert "丙" not in premise


def test_build_premise_window_keeps_claim_relevant_segment() -> None:
    filler = "无关填充内容" * 80
    anchor = "修改数据功能的方式名称为平板、桌面、手持。"
    block = filler + anchor + filler
    premise = build_premise("修改数据功能的方式名称", [block],
                            per_block=100, total=1500)
    assert "平板" in premise
    assert "修改数据功能" in premise


def test_build_premise_strips_table_html() -> None:
    premise = build_premise("标识符", [
        "<table><thead><tr><th><p>序号</p></th></tr></thead>"
        "<tbody><tr><td><p>ZZSJHQZHFW-GN-SJHQ</p></td></tr></tbody></table>"])
    assert "<" not in premise
    assert "ZZSJHQZHFW-GN-SJHQ" in premise


# ── nli_training: 样本映射与分割 ──────────────────────────

def test_example_from_row_maps_labels_and_keeps_claim_anchor() -> None:
    label_id = {"entailment": 0, "neutral": 1, "contradiction": 2}
    row = {
        "sample_id": "EGT-S-00001",
        "question": "该声明是否与文档一致",
        "claim_text": "结构化数据源引接/ZZSJHQZHFW-GN-SJHQ-JGHSJYYJ的概述",
        "label": "support",
        "source": "statement:table",
        "operator": "support_rewrite:filler_removal",
        "claim_kind": "generic",
        "evidence": [{"text": "<table><tr><td>用例名：结构化数据源引接</td>"
                              "<td>标识符：ZZSJHQZHFW-GN-SJHQ-JGHSJYYJ</td>"
                              "</tr></table>"}],
    }
    example = example_from_row(row, label_id)
    assert example is not None
    assert example["label_name"] == "entailment"
    assert example["label"] == 0
    assert example["hypothesis"] == row["claim_text"]
    assert "结构化数据源引接" in example["premise"]
    assert "<" not in example["premise"]


def test_example_from_row_rejects_bad_rows() -> None:
    label_id = {"entailment": 0, "neutral": 1, "contradiction": 2}
    assert example_from_row({"label": "unknown", "evidence": [{"text": "x"}],
                             "claim_text": "y"}, label_id) is None
    assert example_from_row({"label": "support", "evidence": [],
                             "claim_text": "y"}, label_id) is None
    assert example_from_row({"label": "support", "evidence": [{"text": "x"}],
                             "claim_text": ""}, label_id) is None


def test_verdict_mapping_covers_three_way_labels() -> None:
    assert VERDICT_TO_NLI == {"support": "entailment", "refute": "contradiction",
                              "not_in_evidence": "neutral"}


def test_base_label_ids_reads_model_config() -> None:
    if not (BASE / "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"
            / "config.json").exists():
        pytest.skip("mDeBERTa基座未安装")
    assert base_label_ids("mdeberta") == {"entailment": 0, "neutral": 1,
                                          "contradiction": 2}


def test_split_is_deterministic_by_sample_id_hash() -> None:
    assert is_dev_sample("EGT-S-00001") == is_dev_sample("EGT-S-00001")
    ids = [f"EGT-S-{i:05d}" for i in range(1000)]
    dev_ratio = sum(1 for sid in ids if is_dev_sample(sid)) / len(ids)
    assert 0.05 <= dev_ratio <= 0.15


@pytest.mark.skipif(not EGT_DATASET.exists(), reason="EGT数据集未构建")
def test_build_dataset_split_and_distribution() -> None:
    dataset = build_dataset()
    meta = dataset["meta"]
    assert meta["n_examples"] == meta["n_train"] + meta["n_dev"]
    assert 0.05 <= meta["n_dev"] / meta["n_examples"] <= 0.15
    dist = meta["verdict_dist"]
    # S:R:N均衡(组装均衡; example_from_row过滤可致±个位数)
    assert max(dist.values()) - min(dist.values()) <= 5
    assert min(dist.values()) >= 1000
    assert 3000 <= sum(dist.values()) <= 5000    # v2叙事升级规模
    again = build_dataset()
    assert [ex["sample_id"] for ex in again["dev"]] == \
        [ex["sample_id"] for ex in dataset["dev"]]
    for ex in dataset["train"] + dataset["dev"]:
        assert ex["premise"].strip()
        assert ex["hypothesis"].strip()


@pytest.mark.skipif(not EGT_DATASET.exists(), reason="EGT数据集未构建")
def test_egt_dataset_refute_narrative_share() -> None:
    """v2叙事升级契约: R样本中叙事(跨行值绑定)占比≥60%."""
    from algorithms.consistency.nli_training import load_egt_rows

    rows = load_egt_rows()
    refute = [row for row in rows if row.get("label") == "refute"]
    narrative = sum(1 for row in refute
                    if str(row.get("source", "")).startswith("narrative:"))
    assert refute
    assert narrative / len(refute) >= 0.6


# ── nli_training: 语句组选取 (训练/推理共用) ─────────────────

def test_select_statements_scope_group_wins_over_budget() -> None:
    sql_text = "SQL访问功能的方式名称：平板、桌面、手持"
    obj_text = "对象化访问功能的需求描述：提供对象化访问。"
    statements = [
        EvidenceStatement("s0", "e2", obj_text, "需求描述", "对象化访问功能", 1),
        EvidenceStatement("s1", "e1", sql_text, "方式名称", "SQL访问功能", 5),
    ] * 20
    picks = nli_training.select_statements(
        "所有操作均支持在桌面和平板设备上运行", "SQL访问功能包括哪些操作",
        statements, budget=20)
    assert picks == [(1, sql_text)]
    picks = nli_training.select_statements(
        "所有操作均支持在桌面和平板设备上运行", "SQL访问功能包括哪些操作",
        statements, budget=45)
    texts = [text for _, text in picks]
    assert sql_text in texts
    assert sum(len(text) for text in texts) <= 45 + len(sql_text)


def test_select_statements_restores_document_order() -> None:
    statements = [
        EvidenceStatement("s0", "e1", "低重叠语句一", "", "gA", 1),
        EvidenceStatement("s1", "e1", "平板、桌面设备支持", "", "gB", 2),
        EvidenceStatement("s2", "e1", "低重叠语句二", "", "gC", 3),
    ]
    picks = nli_training.select_statements("设备为平板、桌面", "", statements,
                                           budget=9)
    assert picks == [(1, "平板、桌面设备支持")]
    picks = nli_training.select_statements("设备为平板、桌面", "", statements,
                                           budget=200)
    assert [index for index, _ in picks] == [0, 1, 2]


def test_select_statements_dedupes_identical_text() -> None:
    statements = [EvidenceStatement("s0", "e1", "相同语句", "", "gA", 1),
                  EvidenceStatement("s1", "e1", "相同语句", "", "gA", 2)]
    picks = nli_training.select_statements("相同", "", statements)
    assert len(picks) == 1
    assert picks[0][0] == 0


def test_select_statements_keeps_group_complete() -> None:
    row = [EvidenceStatement(f"s{i}", "e1", f"用例X的字段{i}：值{i}", "字段",
                             "用例X", i) for i in range(3)]
    picks = nli_training.select_statements("用例X的字段", "", row, budget=20)
    assert [index for index, _ in picks] == [0, 1, 2]  # 整组不截半


# ── nli_residual: 门控与verdict映射(注入假模型) ────────────

@pytest.fixture()
def patch_model(monkeypatch):
    """注入假NLI模型: 跳过torch/transformers, 脚本化概率输出."""
    state = {"probs": [], "calls": []}

    def fake_load(path: str) -> dict:
        return {"mode": "cpu", "error": ""}

    def fake_infer(entry: dict, pairs: list) -> list:
        state["calls"].append(pairs)
        queue = list(state["probs"])
        return queue[:len(pairs)] if queue else [
            {"entailment": 0.1, "neutral": 0.1, "contradiction": 0.8}
            for _ in pairs]

    monkeypatch.setattr(nli_residual, "_load_model", fake_load)
    monkeypatch.setattr(nli_residual, "_infer", fake_infer)
    return state


def test_nli_contradiction_maps_to_refute_with_refs(patch_model) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-nli-1-c01",
                                  "所有操作均支持在桌面和平版和平板设备上运行。")]
    results = verify_residual_claims_nli(
        request, residual, statements_for(request), model_path="fake-path")
    assert len(results) == 1
    result = results[0]
    assert result.verdict == "refute"
    assert result.method == "nli_residual"
    assert result.claim_id == "qa-nli-1-c01"
    assert result.check_item_candidates == ("CS-01",)
    assert set(result.evidence_refs) == {"e1", "e2"}
    assert result.confidence == pytest.approx(0.8)
    assert "NLI残差判定：contradiction" in result.rationale


def test_nli_gate_below_threshold_stays_nie(patch_model) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-nli-1-c01", "设备集合声明。")]
    patch_model["probs"] = [{"entailment": 0.05, "neutral": 0.15,
                             "contradiction": 0.55}]
    results = verify_residual_claims_nli(
        request, residual, statements_for(request), model_path="fake-path")
    assert results[0].verdict == "not_in_evidence"
    assert results[0].evidence_refs == ()
    assert "门控" in results[0].rationale


def test_nli_entailment_maps_to_support(patch_model) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-nli-1-c01", "方式名称为平板、桌面。")]
    patch_model["probs"] = [{"entailment": 0.9, "neutral": 0.05,
                             "contradiction": 0.05}]
    results = verify_residual_claims_nli(
        request, residual, statements_for(request), model_path="fake-path",
        gate=0.8)
    assert results[0].verdict == "support"
    assert set(results[0].evidence_refs) == {"e1", "e2"}


def test_nli_dedupes_identical_claims(patch_model) -> None:
    request = sample_request()
    residual = [unresolved_result("qa-nli-1-c01", "相同声明。"),
                unresolved_result("qa-nli-1-c02", "相同声明。")]
    results = verify_residual_claims_nli(
        request, residual, statements_for(request), model_path="fake-path")
    assert len(results) == 1
    assert results[0].claim_id == "qa-nli-1-c01"


def test_nli_empty_inputs_return_empty(patch_model) -> None:
    request = sample_request()
    assert verify_residual_claims_nli(request, [], statements_for(request),
                                      model_path="fake-path") == []
    assert verify_residual_claims_nli(
        request, [unresolved_result("c", "x")], [],
        model_path="fake-path") == []


def test_nli_unavailable_model_degrades_to_nie(monkeypatch) -> None:
    monkeypatch.setattr(nli_residual, "_load_model",
                        lambda path: {"mode": "unavailable",
                                      "error": "FileNotFoundError: x"})
    request = sample_request()
    residual = [unresolved_result("qa-nli-1-c01", "任意声明。")]
    results = verify_residual_claims_nli(
        request, residual, statements_for(request), model_path="bad-path")
    assert results[0].verdict == "not_in_evidence"
    assert results[0].method == "nli_residual_unavailable"
    assert "不可用" in results[0].rationale


# ── qa_module集成: 残差分派与NLI优先 ──────────────────────

def test_module_nli_residual_replaces_unresolved_nie(patch_model,
                                                     monkeypatch) -> None:
    def llm_must_not_run(*args, **kwargs):
        raise AssertionError("NLI优先时LLM残差通道不应被调用")

    monkeypatch.setattr(
        "algorithms.consistency.llm_residual.verify_residual_claims",
        llm_must_not_run)
    request = sample_request()
    module = QAConsistencyModule(use_experts=False, use_nli_residual=True,
                                 nli_model_path="fake-path")
    result = module.verify(request)
    nli_claims = [claim for claim in result.claim_results
                  if claim.method == "nli_residual"]
    assert nli_claims
    assert result.verdict == "refute"
    assert "nli_residual_model_unavailable" not in result.diagnostics


def test_module_nli_and_llm_mutually_exclusive_by_default() -> None:
    module = QAConsistencyModule(use_experts=True, use_nli_residual=True)
    assert module.use_llm_residual is False
    module = QAConsistencyModule(use_experts=True, use_llm_residual=True)
    assert module.use_nli_residual is False


def test_module_unavailable_nli_surfaces_diagnostic(monkeypatch) -> None:
    monkeypatch.setattr(nli_residual, "_load_model",
                        lambda path: {"mode": "unavailable",
                                      "error": "FileNotFoundError: x"})
    request = sample_request()
    module = QAConsistencyModule(use_experts=False, use_nli_residual=True,
                                 nli_model_path="bad-path")
    result = module.verify(request)
    assert "nli_residual_model_unavailable" in result.diagnostics


# ── qa_module集成: S5级联升级(L2 refute→L3复核) ─────────────

@pytest.fixture()
def patch_llm(monkeypatch):
    """脚本化L3调用: 记录prompt, 消费队列; 空队列时断言不应有额外调用."""
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


def cascade_module(**kwargs) -> QAConsistencyModule:
    return QAConsistencyModule(use_experts=False, use_cascade=True,
                                nli_model_path="fake-path", **kwargs)


def test_module_cascade_implies_both_residual_channels() -> None:
    module = cascade_module()
    assert module.use_nli_residual is True
    assert module.use_llm_residual is True


def test_module_cascade_escalates_nli_refute_to_llm(patch_model,
                                                    patch_llm) -> None:
    """NLI refute(conf 0.8 < 0.95) → L3复核判NIE → NIE完全替换refute."""
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "not_in_evidence",
        "evidence_refs": [], "rationale": "证据无该设备集合声明",
        "confidence": 0.7,
    }]}]
    request = sample_request()
    result = cascade_module().verify(request)
    assert len(patch_llm["calls"]) == 1
    assert "所有操作均支持在桌面、平版和平板设备上运行" in patch_llm["calls"][0]
    assert "SQL访问修改数据功能" in patch_llm["calls"][0]
    assert result.verdict == "not_in_evidence"
    assert all(claim.verdict != "refute" for claim in result.claim_results)
    assert "cascade_llm_calls_1" in result.diagnostics
    assert "cascade_nli_claims_1" in result.diagnostics
    assert "cascade_high_confidence_kept_1" not in result.diagnostics


def test_module_cascade_keeps_llm_confirmed_refute(patch_model,
                                                   patch_llm) -> None:
    patch_llm["queue"] = [{"claims": [{
        "claim_id": "c1", "verdict": "refute",
        "evidence_refs": ["ev-1"], "rationale": "证据给出平板、桌面、手持，矛盾",
        "confidence": 0.93,
    }]}]
    result = cascade_module().verify(sample_request())
    assert len(patch_llm["calls"]) == 1
    assert result.verdict == "refute"
    assert any(claim.method == "llm_residual" and claim.verdict == "refute"
               for claim in result.claim_results)
    assert "cascade_llm_calls_1" in result.diagnostics


def test_module_cascade_nli_support_passes_through(patch_model,
                                                   patch_llm) -> None:
    """NLI support直接放行, 不进入L3(只有refute候选升级)."""
    patch_model["probs"] = [{"entailment": 0.9, "neutral": 0.05,
                             "contradiction": 0.05}]
    result = cascade_module().verify(sample_request())
    assert patch_llm["calls"] == []
    assert result.verdict == "support"
    assert "cascade_llm_calls_0" in result.diagnostics


def test_module_cascade_nli_nie_not_escalated(patch_model, patch_llm) -> None:
    patch_model["probs"] = [{"entailment": 0.1, "neutral": 0.7,
                             "contradiction": 0.2}]
    result = cascade_module().verify(sample_request())
    assert patch_llm["calls"] == []
    assert result.verdict == "not_in_evidence"
    assert "cascade_llm_calls_0" in result.diagnostics


def test_module_cascade_high_confidence_refute_skips_llm(
        patch_model, patch_llm) -> None:
    """conformal高置信档: NLI refute概率>=0.95直接信任, 不花L3调用."""
    patch_model["probs"] = [{"entailment": 0.01, "neutral": 0.02,
                             "contradiction": 0.97}]
    result = cascade_module(cascade_keep_confidence=0.95).verify(
        sample_request())
    assert patch_llm["calls"] == []
    assert result.verdict == "refute"
    assert any(claim.method == "nli_residual" and claim.verdict == "refute"
               for claim in result.claim_results)
    assert "cascade_high_confidence_kept_1" in result.diagnostics
    assert "cascade_llm_calls_0" in result.diagnostics


def test_module_cascade_llm_failure_keeps_nli_refute(patch_model,
                                                     patch_llm) -> None:
    """L3复核失败(重试1次后)保留L2 refute: 升级不比L2-only更不知情."""
    patch_llm["queue"] = [RuntimeError("LLM调用失败(glm)"),
                          RuntimeError("LLM调用失败(glm)")]
    result = cascade_module().verify(sample_request())
    assert len(patch_llm["calls"]) == 2
    assert result.verdict == "refute"
    assert any(claim.method == "nli_residual" and claim.verdict == "refute"
               for claim in result.claim_results)
    assert "llm_residual_call_failed" in result.diagnostics
    assert "cascade_llm_calls_1" in result.diagnostics
