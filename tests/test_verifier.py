"""CascadeVerifier facade契约测试(algorithms/consistency/verifier.py).

覆盖:
- facade等价性: fast preset在91QA抽样20条上与QAConsistencyModule(
  use_experts=True)判定完全一致(facade不改变内部行为)
- VerdictResult字段完整(verdict/refs/items/rationale/latency>0)
- scene切换: doc01场景下set_default_lexicon/set_default_rulepack生效
  (词典/规则包可从facade查询; 引擎侧派生缓存按pack身份重建)
- preset/scene校验报错(可读)
- verify_record/verify_batch格式
- full preset(含LLM通道): 只测构造与参数传递, monkeypatch模拟不真实调用
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import algorithms.consistency.verifier as verifier_module  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    LABELS,
    build_qa_input,
    load_frozen_qa,
)
from algorithms.consistency.ner_lexicon import (  # noqa: E402
    default_lexicon,
    load_lexicon,
    set_default_lexicon,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    VerificationResult,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.rulepack import (  # noqa: E402
    default_rulepack,
    load_rulepack,
    set_default_rulepack,
)
from algorithms.consistency.verifier import (  # noqa: E402
    CascadeVerifier,
    VerdictResult,
)

SRS_LEXICON = BASE / "config/ner_lexicons/srs_scene1.json"
SRS_RULEPACK = BASE / "config/rulepacks/srs_gjb_v1.json"
DOC06_RULEPACK = BASE / "config/rulepacks/doc06_v1.json"
DOC01_LEXICON = BASE / "config/ner_lexicons/doc01_scene.json"
DOC01_RULEPACK = BASE / "config/rulepacks/doc01_onboard_v1.json"

#: 等价性抽样: 91行跨全卷stride-4取20条(确定性)
SAMPLE_STRIDE = 4
SAMPLE_N = 20


@pytest.fixture
def srs_scene_default():
    """每个触碰场景默认的测试后恢复srs_scene1默认(避免跨测试污染)."""
    yield
    set_default_lexicon(load_lexicon(SRS_LEXICON))
    set_default_rulepack(load_rulepack(SRS_RULEPACK))


def _evidence_dict(evidence_id: str = "e1") -> dict:
    return {
        "evidence_id": evidence_id,
        "text": "响应时间为200ms。",
        "source_type": "text",
        "source_ref": {"doc_id": "doc01", "section": "3.2.1", "page": 3},
        "scope_id": "doc01:3.2.1",
        "completeness": "open",
    }


def _qa_input(instance_id: str = "qa-1") -> object:
    return build_qa_input({
        "instance_id": instance_id,
        "question": "系统响应时间要求是多少？",
        "answer": "响应时间为200ms。",
        "context_freeze_id": "frozen-context-1",
        "evidence": [_evidence_dict()],
    })


# ── facade等价性(行为保持) ────────────────────────────────


def test_fast_preset_equivalence_on_sampled_91qa(
        srs_scene_default) -> None:
    rows = load_frozen_qa()
    sample = rows[::SAMPLE_STRIDE][:SAMPLE_N]
    assert len(sample) == SAMPLE_N
    facade = CascadeVerifier(preset="fast", scene="srs_scene1")
    reference = QAConsistencyModule(use_experts=True)
    mismatches = [
        record["instance_id"] for record in sample
        if facade.verify_record(record).verdict
        != reference.verify(build_qa_input(record)).verdict
    ]
    assert mismatches == []
    assert len(sample) == len(load_frozen_qa()[::SAMPLE_STRIDE][:SAMPLE_N])


# ── VerdictResult字段完整 ────────────────────────────────


def test_verdict_result_fields_complete(srs_scene_default) -> None:
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify_record(load_frozen_qa()[0])
    assert isinstance(result, VerdictResult)
    assert result.verdict in LABELS
    assert isinstance(result.evidence_refs, tuple)
    assert isinstance(result.check_items, tuple)
    assert isinstance(result.rationale, str)
    assert isinstance(result.diagnostics, tuple)
    assert result.latency_ms > 0
    evidence_ids = {ev["evidence_id"]
                    for ev in load_frozen_qa()[0]["evidence"]}
    # 引用可带语句级后缀(evidence_id#sN), 归一到块级id后必须是证据子集
    assert {ref.split("#")[0] for ref in result.evidence_refs} <= evidence_ids


def test_rationale_truncated_at_reasonable_length(
        srs_scene_default) -> None:
    rows = load_frozen_qa()
    longest = max(rows, key=lambda row: len(row["answer"]))
    result = CascadeVerifier(preset="fast",
                             scene="srs_scene1").verify_record(longest)
    assert len(result.rationale) <= verifier_module._RATIONALE_MAX + 10


# ── scene切换真实生效 ────────────────────────────────────


def test_scene_switch_doc01_sets_module_defaults(
        srs_scene_default) -> None:
    verifier = CascadeVerifier(preset="fast", scene="doc01")
    # facade可查询场景资产
    assert verifier.lexicon.scene == "doc01_scene"
    assert verifier.lexicon.id_patterns == ("ZZSJHQZHFW-[A-Z0-9-]+",)
    assert verifier.rulepack.pack_id == "doc01_onboard_v1"
    # 模块级默认已切换(qa_module内部专家消费的默认配置)
    assert default_lexicon() is verifier.lexicon
    assert default_rulepack() is verifier.rulepack
    # 引擎侧派生缓存按pack身份重建(场景切换在引擎层真实生效)
    import algorithms.consistency.trace_expert as trace_expert

    trace_expert._cfg()
    assert trace_expert._TRACE_PACK is verifier.rulepack


def test_set_default_rulepack_switches_and_restores(
        srs_scene_default) -> None:
    doc06 = load_rulepack(DOC06_RULEPACK)
    set_default_rulepack(doc06)
    assert default_rulepack() is doc06
    # 引擎缓存随pack身份失效重建
    import algorithms.consistency.e1_expert as e1_expert

    e1_expert._cfg()
    assert e1_expert._E1_PACK is doc06
    srs = load_rulepack(SRS_RULEPACK)
    set_default_rulepack(srs)
    assert default_rulepack() is srs


def test_scene_assets_load_in_init_not_at_import() -> None:
    """模块顶层零I/O: 新进程import后默认词典/规则包仍为未加载态."""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(BASE)!r})\n"
        "import algorithms.consistency.verifier\n"
        "from algorithms.consistency.ner_lexicon import _DEFAULT_LEXICON\n"
        "from algorithms.consistency.rulepack import _DEFAULT_PACK\n"
        "assert _DEFAULT_LEXICON is None, 'lexicon loaded at import'\n"
        "assert _DEFAULT_PACK is None, 'rulepack loaded at import'\n"
        "print('no-io-ok')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        encoding="utf-8", cwd=BASE, timeout=120,
        env={**os.environ, "PYTHONUTF8": "1"})
    assert result.returncode == 0, result.stderr[-500:]
    assert "no-io-ok" in result.stdout


# ── preset/scene校验报错 ─────────────────────────────────


def test_unknown_preset_raises_readable_error() -> None:
    with pytest.raises(ValueError, match="turbo.*fast.*standard.*full"):
        CascadeVerifier(preset="turbo")


def test_unknown_scene_raises_readable_error() -> None:
    with pytest.raises(ValueError, match="doc99.*doc01.*doc06.*srs_scene1"):
        CascadeVerifier(preset="fast", scene="doc99")


# ── verify_record / verify_batch格式 ─────────────────────


def test_verify_batch_reuses_engine_and_matches_single(
        srs_scene_default) -> None:
    rows = load_frozen_qa()[:5]
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    batch = verifier.verify_batch(rows)
    assert isinstance(batch, list)
    assert len(batch) == len(rows)
    assert all(isinstance(item, VerdictResult) for item in batch)
    assert all(item.latency_ms > 0 for item in batch)
    singles = [verifier.verify_record(row) for row in rows]
    assert [item.verdict for item in batch] == [
        item.verdict for item in singles]
    # 内部复用: 引擎只构造一次
    assert verifier._engine is not None
    engine = verifier._engine
    verifier.verify_record(rows[0])
    assert verifier._engine is engine


def test_verify_three_arguments_builds_frozen_record(
        srs_scene_default) -> None:
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify(
        question="系统响应时间要求是多少？",
        answer="响应时间为200ms。",
        evidence=[_evidence_dict()],
    )
    assert isinstance(result, VerdictResult)
    assert result.verdict == "support"
    assert result.evidence_refs == ("e1",)
    assert result.latency_ms > 0


def test_preset_and_scene_properties(srs_scene_default) -> None:
    verifier = CascadeVerifier(preset="fast", scene="doc06")
    assert verifier.preset == "fast"
    assert verifier.scene == "doc06"
    assert verifier.rulepack.pack_id == "doc06_v1"
    set_default_lexicon(load_lexicon(SRS_LEXICON))
    set_default_rulepack(load_rulepack(SRS_RULEPACK))


# ── full preset: 构造与参数传递(mock, 不真实调用LLM/NLI) ──


def test_full_preset_passes_cascade_params(monkeypatch) -> None:
    recorded: dict = {}

    def fake_claim() -> ClaimResult:
        return ClaimResult(
            claim_id="c1", claim_text="响应时间为200ms", verdict="support",
            check_item_candidates=("PARAM-01",), evidence_refs=("e1",),
            rationale="ok", method="numeric_interval", confidence=1.0,
        )

    class FakeModule:
        def __init__(self, **kwargs) -> None:
            recorded.update(kwargs)

        def verify(self, request) -> VerificationResult:
            return VerificationResult(
                instance_id=request.instance_id,
                question=request.question,
                answer=request.answer,
                verdict="support",
                status="ok",
                claim_results=(fake_claim(),),
                evidence_chain=request.evidence,
                considered_evidence_ids=(
                    "e1",),
                context_freeze_id=request.context_freeze_id,
                context_hash="0" * 64,
                context_integrity="unknown",
                applicability="applicable",
                rationale="ok",
            )

    monkeypatch.setattr(verifier_module, "QAConsistencyModule", FakeModule)
    # 构造期不触碰引擎(mock从未被实例化)
    verifier = CascadeVerifier(preset="full", scene="srs_scene1")
    assert recorded == {}
    # 首次verify才惰性构造, 编排参数逐项传递
    result = verifier.verify("系统响应时间要求是多少？", "响应时间为200ms。",
                             [_evidence_dict()])
    assert recorded["use_experts"] is True
    assert recorded["use_nli_residual"] is True
    assert recorded["use_cascade"] is True
    assert isinstance(result, VerdictResult)
    assert result.verdict == "support"


def test_standard_preset_nli_model_path_passthrough(
        monkeypatch, srs_scene_default) -> None:
    recorded: dict = {}

    class FakeModule:
        def __init__(self, **kwargs) -> None:
            recorded.update(kwargs)

        def verify(self, request) -> VerificationResult:
            claim = ClaimResult(
                claim_id="c1", claim_text="x", verdict="not_in_evidence",
                check_item_candidates=(), evidence_refs=(),
                rationale="n", method="conservative_unresolved",
                confidence=0.0,
            )
            return VerificationResult(
                instance_id=request.instance_id,
                question=request.question, answer=request.answer,
                verdict="not_in_evidence", status="partial",
                claim_results=(claim,), evidence_chain=(),
                considered_evidence_ids=(),
                context_freeze_id=request.context_freeze_id,
                context_hash="0" * 64, context_integrity="unknown",
                applicability="uncertain", rationale="n",
            )

    monkeypatch.setattr(verifier_module, "QAConsistencyModule", FakeModule)
    verifier = CascadeVerifier(
        preset="standard", scene="srs_scene1",
        nli_model_path="models/nli/egt_finetuned_v2")
    verifier.verify("q", "a", [_evidence_dict()])
    assert recorded["use_nli_residual"] is True
    # standard档不含级联(use_cascade未传递, 引擎默认False)
    assert recorded.get("use_cascade", False) is False
    assert recorded["nli_model_path"] == "models/nli/egt_finetuned_v2"


def test_verdict_result_from_verification_result_conversion() -> None:
    result = VerificationResult(
        instance_id="qa-x", question="q", answer="a", verdict="refute",
        status="partial",
        claim_results=(
            ClaimResult("c1", "甲", "support", ("TERM-05",), ("e2",),
                        "r1", "m1", 1.0),
            ClaimResult("c2", "乙", "refute", ("TERM-03", "TERM-05"),
                        ("e1",), "r2", "m2", 0.9),
        ),
        evidence_chain=(), considered_evidence_ids=("e1", "e2"),
        context_freeze_id="f", context_hash="0" * 64,
        context_integrity="unknown", applicability="applicable",
        rationale="r1; r2",
    )
    verdict = verifier_module._to_verdict_result(result, 12.5)
    assert verdict.verdict == "refute"
    assert verdict.evidence_refs == ("e1", "e2")
    assert verdict.check_items == ("TERM-03", "TERM-05")
    assert verdict.rationale == "r1; r2"
    assert verdict.diagnostics == ()
    assert verdict.latency_ms == 12.5
