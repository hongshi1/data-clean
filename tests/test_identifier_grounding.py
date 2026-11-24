"""R2: identifier接地概率化的行为锁定(评分器确定性/judge注入对照/阈值边界).

锁定五件事(硬规则: 新逻辑配测试):

1. 特征确定性: 同输入同特征(逐位快照), 重复调用零漂移;
2. 向后兼容: judge不注入(grounding=None)时verify_identifier与R2前
   逐位一致(ClaimResult字面量钉住);
3. refute路径不受judge影响(同subject窗口唯一不同ID→确定性refute@1.0,
   B类代数本体不动);
4. 语义契约: P≥threshold→support@P(不再是恒定1.0), P<threshold→
   保守NIE(method=identifier_grounding, 理由不与_ACTIVE_NIE标记
   误撞——降级是"无法确证绑定"不是"主动负观察");
5. qa_module注入线路: identifier_grounding参数贯通到通道; 阈值边界
   (P恰等于threshold→support, ≥语义)。

合成夹具模拟C06QA-016结构(接口表三行+发送方污染), 自包含不依赖
数据文件; 真实校准judge来自规则资产(default_rules, JSON=内置回退)。
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import AnswerClaim  # noqa: E402
from algorithms.consistency.claim_channels import (  # noqa: E402
    default_rules,
    verify_identifier,
)
from algorithms.consistency.identifier_grounding import (  # noqa: E402
    GroundingFeatures,
    IdentifierGroundingJudge,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

# ── 合成夹具: C06QA-016结构的自包含简化版 ─────────────────────────

_TABLE = (
    "<table><thead><tr><th><p>序号</p></th><th><p>接口需求名称</p></th>"
    "<th><p>接口需求标识</p></th><th><p>发送方</p></th>"
    "<th><p>接收方</p></th><th><p>接口内容</p></th></tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>人机交互接口</p></td>"
    "<td><p>PZXQ-JK-RJJHJK</p></td><td><p>用户</p></td>"
    "<td><p>本软件</p></td><td><p>模式切换、键盘输入</p></td></tr>"
    "<tr><td><p>2</p></td><td><p>与集成框架接口</p></td>"
    "<td><p>PZXQ-JK-JMJCKJ</p></td><td><p>集成框架</p></td>"
    "<td><p>本软件</p></td><td><p>组件集成状态信息</p></td></tr>"
    "<tr><td><p>3</p></td><td><p>与传输服务接口</p></td>"
    "<td><p>PZXQ-JK-TYCSFW</p></td><td><p>传输服务</p></td>"
    "<td><p>本软件</p></td><td><p>统一时延信息</p></td></tr>"
    "</tbody></table>"
)


def _request(answer: str, evidence_text: str = _TABLE,
             question: str = "人机交互接口的接口流向是什么？") -> QAInput:
    return QAInput(
        instance_id="qa-grounding",
        question=question,
        answer=answer,
        context_freeze_id="freeze-grounding",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text=evidence_text, source_type="table",
            source_ref=SourceRef(doc_id="docT", section="3.3.1"),
            scope_id="docT:block-1", completeness="open",
            completeness_proof="open scope",
        ),),
    )


#: 绑定对(answer复述第1行的真实流向: 用户→本软件)
_ANSWER_CORRECT = ("人机交互接口通过接口PZXQ-JK-RJJHJK实现，"
                   "由用户发送至本软件，用于用户与本软件之间的信息交互。")
#: 绑定错(发送方污染自第2行——C06QA-016的同构: right detail, wrong entity)
_ANSWER_SWAPPED = ("人机交互接口通过接口PZXQ-JK-RJJHJK实现，"
                   "由集成框架发送至本软件，用于集成框架与本软件之间"
                   "的信息交互。")
#: 效果性断言杜撰(C06QA-026同构: ID在场, 断言内容无证据)
_ANSWER_EFFECT = "接口PZXQ-JK-RJJHJK采用加密传输保障数据安全，并支持高并发批量调用。"


def _identifier_claim(request: QAInput, text: str) -> AnswerClaim:
    position = request.answer.find(text)
    return AnswerClaim(kind="identifier", text=text,
                       attr="人机交互接口通过接口",
                       span=(position, position + len(text)))


def _judge() -> IdentifierGroundingJudge:
    """真实校准judge(规则资产=JSON=内置回退, 校准产物)."""
    return IdentifierGroundingJudge.from_config(
        default_rules().identifier_grounding)


# ── 1. 特征确定性与快照 ──────────────────────────────────────────


def test_features_deterministic_snapshot() -> None:
    """同输入→同特征(逐位快照锁定, 含三类answer的判别形状)."""
    rules = default_rules()
    judge = _judge()
    correct = judge.grounding_probability(
        _request(_ANSWER_CORRECT), _identifier_claim(
            _request(_ANSWER_CORRECT), "PZXQ-JK-RJJHJK"),
        rules.identifier_subject_suffix)[1]
    swapped = judge.grounding_probability(
        _request(_ANSWER_SWAPPED), _identifier_claim(
            _request(_ANSWER_SWAPPED), "PZXQ-JK-RJJHJK"),
        rules.identifier_subject_suffix)[1]
    effect = judge.grounding_probability(
        _request(_ANSWER_EFFECT, question="接口PZXQ-JK-RJJHJK采用什么保障机制？"),
        _identifier_claim(_request(_ANSWER_EFFECT), "PZXQ-JK-RJJHJK"),
        rules.identifier_subject_suffix)[1]
    assert correct == GroundingFeatures(
        subject_bind_ratio=pytest.approx(0.6, abs=1e-9),
        predicate_hit_ratio=pytest.approx(1.0, abs=1e-9),
        id_block_ratio=pytest.approx(1 / 3, abs=1e-9),
        subject_id_proximity=pytest.approx(1.0, abs=1e-9),
        n_predicate_terms=3, n_hit_segments=1)
    assert swapped.predicate_hit_ratio == pytest.approx(2 / 3, abs=1e-9)
    assert swapped.n_predicate_terms == 3  # 人机交互接口/集成框架/本软件
    # 效果性断言: 4个内容词(接口/加密传输/数据安全/高并发批量调用),
    # 仅结构词"接口"撞上绑定段→0.25(与真实C06QA-026的f2一致)
    assert effect.predicate_hit_ratio == pytest.approx(0.25, abs=1e-9)
    assert effect.n_predicate_terms == 4


def test_features_reproducible_across_calls() -> None:
    """重复调用零漂移(确定性纯函数)."""
    rules = default_rules()
    request = _request(_ANSWER_SWAPPED)
    claim = _identifier_claim(request, "PZXQ-JK-RJJHJK")
    first = judge = _judge()
    features_a = judge.grounding_probability(
        request, claim, rules.identifier_subject_suffix)[1]
    del first
    features_b = _judge().grounding_probability(
        request, claim, rules.identifier_subject_suffix)[1]
    assert features_a == features_b


# ── 2. 向后兼容: judge不注入=R2前行为逐位一致 ────────────────────


def test_verify_identifier_none_judge_bit_identical() -> None:
    """grounding=None: 与R2前字面量逐位一致(support@1.0语义不变)."""
    request = _request(_ANSWER_SWAPPED)
    claim = _identifier_claim(request, "PZXQ-JK-RJJHJK")
    result = verify_identifier(request, claim, 1, ())
    assert result == ClaimResult(
        claim_id="qa-grounding-c01",
        claim_text="PZXQ-JK-RJJHJK",
        verdict="support",
        check_item_candidates=(),
        evidence_refs=("e1",),
        rationale="answer标识符在冻结context中精确出现",
        method="identifier_exact_match",
        confidence=1.0,
        span=claim.span,
    )
    explicit_none = verify_identifier(request, claim, 1, (), grounding=None)
    assert explicit_none == result


def test_qa_module_default_untouched() -> None:
    """qa_module默认(identifier_grounding=None): 通道行为与注入前一致
    (模块级: 合成实例的裁决与字面量期望逐位一致)."""
    module = QAConsistencyModule(use_experts=True)
    result = module.verify(_request(_ANSWER_SWAPPED))
    identifier = [c for c in result.claim_results
                  if c.method == "identifier_exact_match"]
    assert identifier and identifier[0].verdict == "support"
    assert identifier[0].confidence == 1.0


# ── 3. refute路径不受judge影响 ───────────────────────────────────


def test_refute_path_unaffected_by_judge() -> None:
    """同subject窗口内唯一不同ID→确定性refute@1.0(有无judge都一样)."""
    evidence = ("表4中人机交互接口的标识为PZXQ-JK-OTHER。")
    request = QAInput(
        instance_id="qa-refute", question="人机交互接口的标识是什么？",
        answer="人机交互接口的标识为PZXQ-JK-RJJHJK。",
        context_freeze_id="freeze",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text=evidence, source_type="text",
            source_ref=SourceRef(doc_id="docT", section="3.2"),
            scope_id="docT:block-1"),))
    claim = AnswerClaim(kind="identifier", text="PZXQ-JK-RJJHJK",
                        attr="人机交互接口的标识")
    without = verify_identifier(request, claim, 1, ())
    with_judge = verify_identifier(request, claim, 1, (),
                                    grounding=_judge())
    assert without.verdict == "refute"
    assert without.confidence == 1.0
    assert with_judge == without  # refute路径零变化(B类代数本体)


# ── 4. 语义契约: 概率化support与保守降级 ─────────────────────────


def test_support_downgrade_below_threshold() -> None:
    """绑定错(发送方污染): P<threshold→NIE降级, method可审计, 置信度=P."""
    request = _request(_ANSWER_SWAPPED)
    claim = _identifier_claim(request, "PZXQ-JK-RJJHJK")
    judge = _judge()
    probability, _ = judge.grounding_probability(
        request, claim, default_rules().identifier_subject_suffix)
    assert probability < judge.threshold  # 夹具必须落在降级区
    result = verify_identifier(request, claim, 1, (), grounding=judge)
    assert result.verdict == "not_in_evidence"
    assert result.method == "identifier_grounding"
    assert result.confidence == pytest.approx(probability, abs=1e-9)
    assert "保守降级" in result.rationale
    assert result.evidence_refs == ("e1",)  # 在场证据仍可审计
    # 降级理由不得撞_ACTIVE_NIE_RATIONALE_MARKERS(降级是"无法确证绑定",
    # 不是主动负观察——dominant_70聚合下不投票)
    from algorithms.consistency.qa_module import _ACTIVE_NIE_RATIONALE_MARKERS
    assert not any(marker in result.rationale
                   for marker in _ACTIVE_NIE_RATIONALE_MARKERS)


def test_effect_claim_downgrade_below_threshold() -> None:
    """效果性断言杜撰(C06QA-026同构): P<threshold→NIE降级."""
    request = _request(
        _ANSWER_EFFECT, question="接口PZXQ-JK-RJJHJK采用什么保障机制？")
    claim = AnswerClaim(kind="identifier", text="PZXQ-JK-RJJHJK",
                        attr="接口",
                        span=(2, 2 + len("PZXQ-JK-RJJHJK")))
    result = verify_identifier(request, claim, 1, (), grounding=_judge())
    assert result.verdict == "not_in_evidence"
    assert result.method == "identifier_grounding"


def test_support_kept_above_threshold() -> None:
    """绑定对(answer复述真实流向): P≥threshold→support@P(≠恒定1.0)."""
    request = _request(_ANSWER_CORRECT)
    claim = _identifier_claim(request, "PZXQ-JK-RJJHJK")
    judge = _judge()
    probability, _ = judge.grounding_probability(
        request, claim, default_rules().identifier_subject_suffix)
    assert probability >= judge.threshold  # 夹具必须落在保留区
    result = verify_identifier(request, claim, 1, (), grounding=judge)
    assert result.verdict == "support"
    assert result.method == "identifier_exact_match"
    assert result.confidence == pytest.approx(probability, abs=1e-9)
    assert result.confidence != 1.0  # 概率化: 不再恒定1.0
    assert "接地概率" in result.rationale


def test_missing_id_paths_unchanged_with_judge() -> None:
    """ID不在场: 现有refute/NIE路径与judge无关(judge只作用于support路径)."""
    evidence = "系统包含数据库初始化用例，标识为PZXQ-GN-SJKCZ-SJKCSH。"
    request = QAInput(
        instance_id="qa-absent", question="X的标识是什么？",
        answer="X的标识为PZXQ-GN-UNKNOWN。",
        context_freeze_id="freeze",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text=evidence, source_type="text",
            source_ref=SourceRef(doc_id="docT", section="3.2"),
            scope_id="docT:block-1"),))
    claim = AnswerClaim(kind="identifier", text="PZXQ-GN-UNKNOWN",
                        attr="X的标识")
    without = verify_identifier(request, claim, 1, ())
    with_judge = verify_identifier(request, claim, 1, (),
                                    grounding=_judge())
    assert with_judge == without
    assert with_judge.verdict == "not_in_evidence"


# ── 5. 注入线路与阈值边界 ────────────────────────────────────────


def test_qa_module_injection_flips_instance() -> None:
    """qa_module(identifier_grounding=judge): 合成绑定错实例support→NIE."""
    judge = _judge()
    baseline = QAConsistencyModule(use_experts=True).verify(
        _request(_ANSWER_SWAPPED))
    injected = QAConsistencyModule(
        use_experts=True, identifier_grounding=judge).verify(
        _request(_ANSWER_SWAPPED))
    assert baseline.verdict == "support"
    assert injected.verdict == "not_in_evidence"
    downgraded = [c for c in injected.claim_results
                  if c.method == "identifier_grounding"]
    assert downgraded and downgraded[0].verdict == "not_in_evidence"
    assert downgraded[0].confidence < 1.0


def test_qa_module_injection_keeps_correct_recap_support() -> None:
    """注入后绑定对实例仍是support(校准的91QA零回退约束的同构夹具)."""
    judge = _judge()
    injected = QAConsistencyModule(
        use_experts=True, identifier_grounding=judge).verify(
        _request(_ANSWER_CORRECT))
    assert injected.verdict == "support"


def test_threshold_boundary_inclusive() -> None:
    """P恰等于threshold→support(≥语义); 略高→降级."""
    request = _request(_ANSWER_SWAPPED)
    claim = _identifier_claim(request, "PZXQ-JK-RJJHJK")
    judge = _judge()
    probability, _ = judge.grounding_probability(
        request, claim, default_rules().identifier_subject_suffix)
    at_edge = dataclasses.replace(judge, threshold=probability)
    assert verify_identifier(
        request, claim, 1, (), grounding=at_edge).verdict == "support"
    above = dataclasses.replace(judge, threshold=probability + 1e-9)
    assert verify_identifier(
        request, claim, 1, (), grounding=above).verdict == "not_in_evidence"


def test_judge_config_json_equals_builtin() -> None:
    """规则资产挂点: JSON第一真源与内置回退构建出同一judge(双层保险)."""
    from algorithms.consistency.claim_channels import (
        CLAIM_CHANNELS_RULES_FILE, builtin_rules, load_rules)
    from_json = IdentifierGroundingJudge.from_config(
        load_rules(CLAIM_CHANNELS_RULES_FILE).identifier_grounding)
    from_builtin = IdentifierGroundingJudge.from_config(
        builtin_rules().identifier_grounding)
    assert from_json.threshold == from_builtin.threshold
    assert from_json.predicate_glue == from_builtin.predicate_glue
    assert from_json.subject_bind_weight == from_builtin.subject_bind_weight
    assert from_json.predicate_hit_weight == from_builtin.predicate_hit_weight
    assert from_json.id_block_weight == from_builtin.id_block_weight
    assert from_json.proximity_weight == from_builtin.proximity_weight
    assert from_json.intercept == from_builtin.intercept


def test_calibration_values_are_the_frozen_run_output() -> None:
    """校准产物钉住(IRLS确定性, 复现命令:
    python tools/calibrate_identifier_grounding.py --report)."""
    config = default_rules().identifier_grounding
    assert config.threshold == pytest.approx(0.4571, abs=1e-9)
    assert config.subject_bind_weight == pytest.approx(0.562, abs=1e-9)
    assert config.predicate_hit_weight == pytest.approx(5.459, abs=1e-9)
    assert config.id_block_weight == pytest.approx(-0.6191, abs=1e-9)
    assert config.proximity_weight == pytest.approx(1.2717, abs=1e-9)
    assert config.intercept == pytest.approx(-5.7383, abs=1e-9)
    assert "通过接口" in config.predicate_glue
    assert "信息交互" in config.predicate_glue
