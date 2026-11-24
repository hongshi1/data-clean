"""E7: claim_channels规则表驱动外置的等价性与回退契约.

锁定四件事(行为保持的验收标准, 不是尽力而为):

1. JSON↔内置回退常量逐值等价(``load_rules`` == ``builtin_rules``),
   且内置常量钉住外置前的硬编码字面量(防双侧漂移);
2. 编译层等价: ``default_rules``(通道实际消费的默认规则)与
   "编译内置常量"逐项一致, 且仓库内JSON合法时加载不告警;
3. 回退路径(双层保险): 规则文件缺失/损坏时 ``_load_or_default``
   回退内置默认并发出可见RuntimeWarning(不静默吞错);
4. 校验层: 坏正则/缺字段/未知键/类型错→可读ValueError.

另用直接调用 verify_quoted / verify_enum / verify_identifier 的
单元测试钉住规则驱动的原硬编码语义(否定窗口边界/枚举分隔符/
identifier局部窗口)——这些行为原写在代码里, 现由config驱动,
钉住即证明"改JSON不改代码"接口与旧行为逐位一致.
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import algorithms.consistency.claim_channels as cc  # noqa: E402
from algorithms.consistency.answer_claims import AnswerClaim  # noqa: E402
from algorithms.consistency.claim_channels import (  # noqa: E402
    CLAIM_CHANNELS_RULES_FILE,
    CompiledChannelRules,
    _load_or_default,
    builtin_rules,
    compile_rules,
    default_rules,
    load_rules,
    verify_enum,
    verify_identifier,
    verify_quoted,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)


def _ev(text: str, evidence_id: str = "e1", completeness: str = "open",
        proof: str = "", scope_id: str = "doc01:3.2.1",
        ) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id, text=text, source_type="text",
        source_ref=SourceRef(doc_id="doc01", section="3.2.1"),
        scope_id=scope_id, completeness=completeness,
        completeness_proof=proof,
    )


def _request(evidence: tuple[RetrievedEvidence, ...],
             question: str = "context定义了X功能吗？",
             answer: str = "定义了「X功能」。") -> QAInput:
    return QAInput(instance_id="qa-rules", question=question, answer=answer,
                   context_freeze_id="freeze-rules", evidence=evidence)


# ── 1. JSON↔内置回退常量等价(行为保持的根) ──────────────────────────


def test_json_rules_equal_builtin_fallback() -> None:
    """仓库JSON与内置回退常量逐值相同(双层保险的两层内容一致)."""
    assert load_rules(CLAIM_CHANNELS_RULES_FILE) == builtin_rules()


def test_builtin_fallback_pins_pre_e7_values() -> None:
    """内置回退常量=外置前硬编码值(逐值钉住: JSON与常量都不许漂移)."""
    rules = builtin_rules()
    assert rules.explicit_negation_pattern == (
        r"(?:不包括|不包含|不支持|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)")
    assert rules.slot_fields == (
        ("前置条件", ("前置条件",)),
        ("后置条件", ("后置条件",)),
        ("异常流", ("异常流",)),
        ("参与者", ("Actors", "参与者")),
        ("Actor", ("Actors", "参与者")),
    )
    assert rules.identifier_subject_suffix == (
        r"(?:用例)?(?:的)?(?:唯一)?(?:标识符?|编号|代号|名称|项目名)?$")
    assert rules.enum_separator == r"[、，,；]"
    assert rules.negation_prefix_window == 14
    assert rules.identifier_window_before == 30
    assert rules.identifier_window_after == 100
    assert rules.identifier_subject_min_len == 2
    assert rules.enum_member_min_len == 2
    assert rules.closed_scope_exclusion_confidence == 0.85
    assert rules.nli_residual_confidence == 0.9


def test_builtin_fallback_pins_r2_grounding_values() -> None:
    """R2挂点(显式断言, 不许静默漂移): identifier_grounding校准配置=
    tools/calibrate_identifier_grounding.py --write 的冻结产物
    (IRLS确定性: 296例案例库, 训练F1最大化阈值; 复现命令见
    tools/calibrate_identifier_grounding.py模块docstring)."""
    config = builtin_rules().identifier_grounding
    assert config.threshold == 0.4571
    assert config.subject_bind_weight == 0.562
    assert config.predicate_hit_weight == 5.459
    assert config.id_block_weight == -0.6191
    assert config.proximity_weight == 1.2717
    assert config.intercept == -5.7383
    # 胶水词表钉住关键成员(模板功能词; 数据安全/高并发等内容词不在)
    assert "通过接口" in config.predicate_glue
    assert "信息交互" in config.predicate_glue
    assert "发送至" in config.predicate_glue
    assert "数据安全" not in config.predicate_glue
    assert "加密传输" not in config.predicate_glue


# ── 2. 编译层等价与默认规则的JSON优先 ──────────────────────────────


def _assert_compiled_equal(left: CompiledChannelRules,
                           right: CompiledChannelRules) -> None:
    assert left.explicit_negation.pattern == right.explicit_negation.pattern
    assert (left.identifier_subject_suffix.pattern
            == right.identifier_subject_suffix.pattern)
    assert left.enum_separator.pattern == right.enum_separator.pattern
    assert left.slot_fields == right.slot_fields
    assert left.negation_prefix_window == right.negation_prefix_window
    assert left.identifier_window_before == right.identifier_window_before
    assert left.identifier_window_after == right.identifier_window_after
    assert left.identifier_subject_min_len == right.identifier_subject_min_len
    assert left.enum_member_min_len == right.enum_member_min_len
    assert (left.closed_scope_exclusion_confidence
            == right.closed_scope_exclusion_confidence)
    assert left.nli_residual_confidence == right.nli_residual_confidence
    # R2挂点: 接地概率化校准配置同样逐值等价(JSON=内置回退)
    assert (left.identifier_grounding.threshold
            == right.identifier_grounding.threshold)
    assert (left.identifier_grounding.predicate_glue
            == right.identifier_grounding.predicate_glue)
    for field in ("subject_bind_weight", "predicate_hit_weight",
                  "id_block_weight", "proximity_weight", "intercept"):
        assert (getattr(left.identifier_grounding, field)
                == getattr(right.identifier_grounding, field))


def test_default_rules_compiles_repo_json() -> None:
    """通道实际消费的default_rules()与"编译内置常量"逐项一致."""
    _assert_compiled_equal(default_rules(), compile_rules(builtin_rules()))


def test_default_rules_prefers_json_without_fallback_warning() -> None:
    """仓库内JSON存在且合法→加载不告警(回退只属于异常环境)."""
    saved = cc._DEFAULT_COMPILED_RULES
    cc._DEFAULT_COMPILED_RULES = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            compiled = cc.default_rules()
    finally:
        cc._DEFAULT_COMPILED_RULES = saved
    _assert_compiled_equal(
        compiled, compile_rules(load_rules(CLAIM_CHANNELS_RULES_FILE)))


def test_to_dict_round_trip(tmp_path: Path) -> None:
    """load→to_dict→写盘→load: 数据无损(to_dict可作场景编写起点)."""
    rules = load_rules(CLAIM_CHANNELS_RULES_FILE)
    out = tmp_path / "round_trip.json"
    out.write_text(json.dumps(rules.to_dict(), ensure_ascii=False, indent=2),
                   encoding="utf-8")
    assert load_rules(out) == rules


# ── 3. 回退路径(双层保险: 任何环境行为一致) ─────────────────────────


def test_missing_file_falls_back_to_builtin(tmp_path: Path) -> None:
    with pytest.warns(RuntimeWarning, match="回退内置默认"):
        rules = _load_or_default(tmp_path / "missing.json")
    assert rules == builtin_rules()


def test_corrupt_json_falls_back_to_builtin(tmp_path: Path) -> None:
    bad = tmp_path / "corrupt.json"
    bad.write_text("{not-json", encoding="utf-8")
    with pytest.warns(RuntimeWarning, match="回退内置默认"):
        rules = _load_or_default(bad)
    assert rules == builtin_rules()


def test_channels_identical_when_config_missing(tmp_path: Path) -> None:
    """双层保险的行为级证明: 规则JSON缺失时, 通道输出(ClaimResult逐位)
    与JSON在位时完全一致——回退常量与JSON同内容, 任何环境行为一致."""
    request = _request((_ev("本系统不支持「X功能」。",),))
    claim = AnswerClaim(kind="quoted", text="X功能", negative=False)
    with_json = verify_quoted(request, claim, 1, ())
    saved_path = cc.CLAIM_CHANNELS_RULES_FILE
    saved_compiled = cc._DEFAULT_COMPILED_RULES
    cc.CLAIM_CHANNELS_RULES_FILE = tmp_path / "missing.json"
    cc._DEFAULT_COMPILED_RULES = None
    try:
        with pytest.warns(RuntimeWarning, match="回退内置默认"):
            cc.default_rules()
        without_json = verify_quoted(request, claim, 1, ())
    finally:
        cc.CLAIM_CHANNELS_RULES_FILE = saved_path
        cc._DEFAULT_COMPILED_RULES = saved_compiled
    assert without_json == with_json


# ── 4. 校验层: 非法配置抛可读ValueError(不静默降级也不静默吞错) ────


@pytest.mark.parametrize("mutate,expect", [
    (lambda d: d.pop("slot_fields"), "缺失字段"),
    (lambda d: d.update({"unknown_section": 1}), "未知字段"),
    (lambda d: d.update({"schema_version": 2}), "不支持的schema_version"),
    (lambda d: d["explicit_negation"].update({"pattern": "(?:unclosed"}),
     "无法编译"),
    (lambda d: d["channel_patterns"].pop("enum_separator"), "缺失字段"),
    (lambda d: d["channel_patterns"].update({"unknown_pattern": "x"}),
     "未知字段"),
    (lambda d: d["channel_thresholds"].update({"negation_prefix_window": "14"}),
     "期望>=1的整数"),
    (lambda d: d["channel_thresholds"].update({"negation_prefix_window": True}),
     "期望>=1的整数"),
    (lambda d: d["channel_thresholds"].update({"negation_prefix_window": 0}),
     "期望>=1的整数"),
    (lambda d: d["channel_confidences"].update({"closed_scope_exclusion": 1.5}),
     r"期望\[0,1\]内数值"),
    (lambda d: d["channel_confidences"].pop("identifier_grounding"),
     "identifier_grounding缺失"),
    (lambda d: d["channel_confidences"]["identifier_grounding"].update(
        {"threshold": 1.5}),
     r"threshold期望\(0,1\)内数值"),
    (lambda d: d["channel_confidences"]["identifier_grounding"].update(
        {"threshold": True}),
     r"threshold期望\(0,1\)内数值"),
    (lambda d: d["channel_confidences"]["identifier_grounding"][
        "feature_weights"].pop("intercept"),
     "feature_weights缺失键"),
    (lambda d: d["channel_confidences"]["identifier_grounding"].update(
        {"feature_weights": [0.1, 0.2]}),
     "feature_weights期望对象"),
    (lambda d: d["channel_confidences"]["identifier_grounding"].update(
        {"predicate_glue": ["通过", ""]}),
     "predicate_glue期望非空字符串数组"),
    (lambda d: d["channel_confidences"]["identifier_grounding"].update(
        {"unknown_key": 1}),
     "identifier_grounding未知字段"),
    (lambda d: d["slot_fields"].append(["前置条件", ["前置条件"]]),
     "关键词重复"),
    (lambda d: d["slot_fields"].append(["前置条件", "前置条件"]),
     "字段表期望非空字符串数组"),
])
def test_invalid_rules_raise_readable_errors(
        tmp_path: Path, mutate, expect: str) -> None:
    payload = load_rules(CLAIM_CHANNELS_RULES_FILE).to_dict()
    mutate(payload)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match=expect):
        load_rules(bad)


# ── 5. 通道级行为钉住(规则驱动的原硬编码语义) ───────────────────────


def test_quoted_negation_inside_window_refutes() -> None:
    """否定标记落在命中项前缀窗口内→显式相反极性→refute(原行为)."""
    request = _request((_ev("本系统不支持「X功能」。",),))
    claim = AnswerClaim(kind="quoted", text="X功能", negative=False)
    result = verify_quoted(request, claim, 1, ())
    assert result.verdict == "refute"
    assert result.method == "explicit_quote_polarity"
    assert result.confidence == 1.0


def test_quoted_negation_window_boundary() -> None:
    """窗口边界逐字符钉住: 否定词恰在命中项前14字符内→refute; 被推到
    窗口外(第15字符起)→正向命中→support. 锁negation_prefix_window=14
    的包含语义, 改JSON窗口值本测试即感知."""
    claim = AnswerClaim(kind="quoted", text="X功能", negative=False)
    near = _request((_ev("不支持" + "备" * 11 + "X功能。",),))
    assert verify_quoted(near, claim, 1, ()).verdict == "refute"
    far = _request((_ev("不支持" + "备" * 12 + "X功能。",),))
    assert verify_quoted(far, claim, 1, ()).verdict == "support"


def test_quoted_closed_scope_confidence_from_rules() -> None:
    """封闭scope未出现条目→极性相符判定, 置信度=规则资产0.85(原硬编码)."""
    request = _request((
        _ev("本系统包括A功能。", completeness="closed",
            proof="表3穷举全部功能"),
    ))
    claim = AnswerClaim(kind="quoted", text="X功能", negative=False)
    result = verify_quoted(request, claim, 1, ())
    assert result.verdict == "refute"
    assert result.method == "closed_scope_exclusion"
    assert result.confidence == 0.85


def test_enum_separators_split_from_rules() -> None:
    """顿号/分号/全半角逗号都按enum_separator切分(原单硬编码正则)."""
    request = _request((_ev("系统包括A功能。",),))
    claim = AnswerClaim(kind="enum", text="A功能、B功能；C功能，D功能")
    result = verify_enum(request, claim, 1, ())
    assert result.verdict == "not_in_evidence"
    assert result.evidence_refs == ("e1",)
    assert "未全部命中" in result.rationale


def test_enum_explicit_exclusion_refutes() -> None:
    request = _request((_ev("本系统不包括B功能。",),))
    claim = AnswerClaim(kind="enum", text="A功能、B功能")
    result = verify_enum(request, claim, 1, ())
    assert result.verdict == "refute"
    assert result.method == "explicit_enum_exclusion"


def test_enum_short_fragments_dropped() -> None:
    """短于enum_member_min_len(2)的切分碎片不参与成员级扫描
    ("A"被丢弃, 缺席不计入missing, 锁原 len(part.strip())>=2 行为)."""
    request = _request((_ev("系统支持B功能。",),))
    claim = AnswerClaim(kind="enum", text="A、B功能")
    result = verify_enum(request, claim, 1, ())
    assert result.rationale.startswith("枚举成员均在context出现")


def test_identifier_exact_hit_supports() -> None:
    request = _request(
        (_ev("数据查询接口的标识为PZXQ-JK-SJCX。",),),
        question="数据查询接口的标识是什么？",
        answer="数据查询接口的标识为PZXQ-JK-SJCX。")
    claim = AnswerClaim(kind="identifier", text="PZXQ-JK-SJCX",
                        attr="数据查询接口的标识")
    result = verify_identifier(request, claim, 1, ())
    assert result.verdict == "support"
    assert result.method == "identifier_exact_match"


def test_identifier_same_subject_mismatch_refutes() -> None:
    """subject后缀剥离+局部窗口由规则驱动: 同subject窗口内唯一不同ID
    →显式值冲突refute(原行为)."""
    request = _request(
        (_ev("表4中数据库初始化的标识为PZXQ-GN-SJKCZ-SJKCSH。",),),
        question="数据库初始化用例的标识是什么？",
        answer="数据库初始化用例的标识为PZXQ-GN-OTHER。")
    claim = AnswerClaim(kind="identifier", text="PZXQ-GN-OTHER",
                        attr="数据库初始化用例的标识")
    result = verify_identifier(request, claim, 1, ())
    assert result.verdict == "refute"
    assert "显式值冲突" in result.rationale


def test_identifier_window_after_boundary() -> None:
    """identifier_window_after=100钉住: subject核心后100字符窗口内的
    不同ID→refute; 窗口外(远于100字符)→不构成显式值冲突→NIE."""
    claim = AnswerClaim(kind="identifier", text="PZXQ-GN-NEAR-ID",
                        attr="数据库初始化的标识")
    near = _request((_ev(
        "数据库初始化" + "填" * 60 + "标识为PZXQ-GN-FAR-ID。",),))
    assert verify_identifier(near, claim, 1, ()).verdict == "refute"
    far = _request((_ev(
        "数据库初始化" + "填" * 130 + "标识为PZXQ-GN-FAR-ID。",),))
    assert verify_identifier(far, claim, 1, ()).verdict == "not_in_evidence"
