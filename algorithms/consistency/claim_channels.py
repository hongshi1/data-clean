"""Deterministic per-claim verification channels for the QA module.

Migrated from ``algorithms.consistency.qa_module`` in the Wave 8-H2
architecture split with unchanged behavior. Each channel takes the
frozen request plus one ``AnswerClaim`` and returns a ``ClaimResult``:

- ``verify_numeric`` — numeric interval containment/disjointness;
- ``verify_quoted`` — explicit quote polarity in the evidence;
- ``verify_enum`` — enum member exact match with explicit exclusion;
- ``verify_identifier`` — identifier exact match / same-subject mismatch;
- ``verify_semantic`` — exact statement match, with the optional residual
  NLI judge (``SemanticNliJudge`` carries the former instance state:
  the predictor callable and its two calibrated thresholds).

R2 (99号Phase 3): ``verify_identifier`` accepts an optional injected
:class:`~algorithms.consistency.identifier_grounding.IdentifierGroundingJudge`
— the support path's confidence becomes the calibrated binding
probability P(绑定|在场, context) and below-threshold cases downgrade to
a conservative NIE. The scoring function itself lives outside this
module (通道层保持确定性); the judge defaults to None = pre-R2 behavior
bit-identical.

Shared helpers (``interval`` / ``subset`` / ``disjoint`` /
``same_subject`` / ``unresolved``) are also module-level pure functions
here. This layer is deterministic: no model calls except the explicitly
injected NLI judge.

E7 (96号§8 / 99号Phase 3): the channel rule assets are table-driven —
the explicit-negation lexicon, the NLI slot-field mapping, the
identifier/enum patterns, the window/threshold knobs and the calibrated
channel confidences live in ``config/claim_channels_rules_v1.json`` and
are consumed through the lazy ``default_rules()`` accessor (same
config/engine split as ``config/ner_lexicons`` + ``ner_lexicon``).
Behavior is unchanged by construction: the JSON content equals the
built-in fallback constants below (double insurance — a missing or
corrupt JSON falls back to the constants with a visible warning, so
every environment behaves identically), and the equivalence is locked
by ``tests/test_claim_channels_rules.py``. Interval algebra, closed
scope logic and the channel control flow stay in code (98号 B类判定:
数学逻辑不外置).
"""
from __future__ import annotations

import json
import re
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from algorithms.consistency.answer_claims import (
    _IDENTIFIER,
    AnswerClaim,
    extract_numeric_claims,
)
from algorithms.consistency.answer_structure import (
    decompose_answer,
    pair_statements,
)
from algorithms.consistency.identifier_grounding import (
    IdentifierGroundingConfig,
)
from algorithms.consistency.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    Verdict,
)
from algorithms.consistency.templates import normalize_op, normalize_unit

if TYPE_CHECKING:  # R2: judge类型仅作签名契约(评分函数不进通道层)
    from algorithms.consistency.identifier_grounding import (
        IdentifierGroundingJudge,
    )

# ── E7规则外置: 配置文件 + 内置回退常量(双层保险) ──────────────────────
#
# 约定: 下面每个 ``_*`` 模块常量与 config/claim_channels_rules_v1.json
# 中对应字段逐值相同(JSON是第一真源; 常量是JSON缺失/损坏时的回退).
# 修改任一侧必须同步另一侧, tests/test_claim_channels_rules.py 锁定
# 二者的等价性(行为保持的验收标准).

#: 规则配置文件路径(模块顶层只存路径不读文件; 加载在 default_rules()
#: 惰性发生, 首次通道调用才触发)
CLAIM_CHANNELS_RULES_FILE = (
    Path(__file__).resolve().parents[2] / "config/claim_channels_rules_v1.json")

#: 内置回退: 显式否定标记正则(原 ``_EXPLICIT_NEGATION``, quoted/enum
#: 通道的否定前缀判定)
_EXPLICIT_NEGATION_PATTERN: str = (
    r"(?:不包括|不包含|不支持|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)")

#: 内置回退: claim文本关键词→statement字段槽位映射(原 ``_SLOT_FIELDS``,
#: 残余NLI通道的pair过滤)
_SLOT_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("前置条件", ("前置条件",)),
    ("后置条件", ("后置条件",)),
    ("异常流", ("异常流",)),
    ("参与者", ("Actors", "参与者")),
    ("Actor", ("Actors", "参与者")),
)

#: 内置回退: identifier通道的subject后缀剥离正则(用例/的/唯一/标识符/…)
_IDENTIFIER_SUBJECT_SUFFIX: str = (
    r"(?:用例)?(?:的)?(?:唯一)?(?:标识符?|编号|代号|名称|项目名)?$")

#: 内置回退: enum通道的成员切分正则(顿号/全半角逗号/分号)
_ENUM_SEPARATOR: str = r"[、，,；]"

#: 内置回退: quoted/enum命中项前的否定检查窗口(字符数)
_NEGATION_PREFIX_WINDOW: int = 14

#: 内置回退: identifier同subject局部窗口——subject核心前字符数
_IDENTIFIER_WINDOW_BEFORE: int = 30

#: 内置回退: identifier同subject局部窗口——subject核心后字符数
_IDENTIFIER_WINDOW_AFTER: int = 100

#: 内置回退: subject核心短于该长度时放弃后缀剥离(防过度剥离成空)
_IDENTIFIER_SUBJECT_MIN_LEN: int = 2

#: 内置回退: enum成员最短长度(更短的切分碎片按噪声丢弃)
_ENUM_MEMBER_MIN_LEN: int = 2

#: 内置回退: closed_scope_exclusion(封闭scope未出现条目)的置信度
_CLOSED_SCOPE_EXCLUSION_CONFIDENCE: float = 0.85

#: 内置回退: nli_residual(残余NLI矛盾/蕴含)的置信度
_NLI_RESIDUAL_CONFIDENCE: float = 0.9

#: 内置回退: identifier接地概率化的校准配置(R2, 99号Phase 3/98号B类
#: 切口①). 权重与阈值由 tools/calibrate_identifier_grounding.py 在误判
#: 案例库(296例: d3_train interface_flow 257 + refute路径最小对孪生39,
#: 排除评测文档04/06)上确定性校准(IRLS无随机源, 训练F1最大化阈值
#: 0.4571@F1=0.8762); 与JSON的channel_confidences.identifier_grounding
#: 逐值相同(双层保险, 等价性由tests/test_claim_channels_rules.py锁定).
#: 通道默认不消费此配置——只有调用方显式注入 IdentifierGroundingJudge
#: (qa_module的identifier_grounding参数)时生效(向后兼容, 论文数字不动).
_IDENTIFIER_GROUNDING_THRESHOLD: float = 0.4571
_IDENTIFIER_GROUNDING_W_SUBJECT_BIND: float = 0.5620
_IDENTIFIER_GROUNDING_W_PREDICATE_HIT: float = 5.4590
_IDENTIFIER_GROUNDING_W_ID_BLOCK: float = -0.6191
_IDENTIFIER_GROUNDING_W_PROXIMITY: float = 1.2717
_IDENTIFIER_GROUNDING_INTERCEPT: float = -5.7383

#: 内置回退: predicate_glue词表(answer局部断言上下文的模板功能词,
#: 命中不计入谓词一致性). 单独成常量便于测试逐值钉住.
_IDENTIFIER_GROUNDING_GLUE: tuple[str, ...] = (
    "通过接口", "通过", "实现", "由", "发送至", "发送", "用于",
    "之间的", "之间", "信息交互", "采用", "保障", "并支持", "支持",
    "提供", "的", "与", "并", "且", "将", "向", "至", "追溯至", "追溯",
    "对应", "任务书", "目前", "处于", "已通过", "经过了", "经过", "已",
    "经", "其", "中", "序号", "什么", "哪些", "是什么",
)

_IDENTIFIER_GROUNDING: IdentifierGroundingConfig = IdentifierGroundingConfig(
    threshold=_IDENTIFIER_GROUNDING_THRESHOLD,
    subject_bind_weight=_IDENTIFIER_GROUNDING_W_SUBJECT_BIND,
    predicate_hit_weight=_IDENTIFIER_GROUNDING_W_PREDICATE_HIT,
    id_block_weight=_IDENTIFIER_GROUNDING_W_ID_BLOCK,
    proximity_weight=_IDENTIFIER_GROUNDING_W_PROXIMITY,
    intercept=_IDENTIFIER_GROUNDING_INTERCEPT,
    predicate_glue=_IDENTIFIER_GROUNDING_GLUE,
)

#: 残余NLI predictor contract: list of (statement, hypothesis)
#: pairs -> NLI labels (dict with label/p_contra/p_entail or bare label)
NliPredictor = Callable[[list[tuple[str, str]]], list]

#: identifier接地配置的必填键(阈值/特征权重/胶水词表)
_GROUNDING_WEIGHT_KEYS: tuple[str, ...] = (
    "subject_bind_ratio", "predicate_hit_ratio",
    "id_block_ratio", "subject_id_proximity", "intercept",
)

_REQUIRED_SECTIONS: tuple[str, ...] = (
    "explicit_negation", "slot_fields", "channel_patterns",
    "channel_thresholds", "channel_confidences",
)
_PATTERN_KEYS: tuple[str, ...] = ("identifier_subject_suffix", "enum_separator")
_THRESHOLD_KEYS: tuple[str, ...] = (
    "negation_prefix_window", "identifier_window_before",
    "identifier_window_after", "identifier_subject_min_len",
    "enum_member_min_len",
)
_CONFIDENCE_KEYS: tuple[str, ...] = ("closed_scope_exclusion", "nli_residual")


@dataclass(frozen=True)
class ClaimChannelRules:
    """通道规则资产的数据形态(JSON往返无损, 字段全为可比较的纯数据).

    与 :class:`CompiledChannelRules` 分离沿用 ner_lexicon 的
    NerLexicon/NerPatterns 约定: 数据层可比较/可序列化(等价性测试与
    场景编写), 编译层持有预编译正则供通道直接消费. 字段语义即
    ``config/claim_channels_rules_v1.json`` 的字段语义(逐一同名).
    """

    explicit_negation_pattern: str
    """显式否定标记正则: quoted/enum通道在命中项前缀窗口内搜索, 命中即判否定/排除."""

    slot_fields: tuple[tuple[str, tuple[str, ...]], ...]
    """claim文本关键词→statement字段槽位: 残余NLI通道只保留field_name命中的pair."""

    identifier_subject_suffix: str
    """identifier通道subject后缀剥离正则(如"数据查询接口的标识"→"数据查询接口")."""

    enum_separator: str
    """enum通道成员切分正则(顿号/全半角逗号/分号)."""

    negation_prefix_window: int
    """quoted/enum命中项前检查否定标记的窗口字符数(原硬编码14)."""

    identifier_window_before: int
    """identifier同subject局部窗口: subject核心之前的字符数(原硬编码30)."""

    identifier_window_after: int
    """identifier同subject局部窗口: subject核心之后的字符数(原硬编码100)."""

    identifier_subject_min_len: int
    """subject核心短于该长度时放弃后缀剥离, 退回原subject(原硬编码2)."""

    enum_member_min_len: int
    """enum成员短于该长度时按碎片噪声丢弃(原硬编码2)."""

    closed_scope_exclusion_confidence: float
    """closed_scope_exclusion方法(封闭scope未出现条目)的置信度(原硬编码0.85)."""

    nli_residual_confidence: float
    """nli_residual方法(残余NLI矛盾/蕴含)的置信度(原硬编码0.9)."""

    identifier_grounding: IdentifierGroundingConfig
    """identifier接地概率化配置(R2挂点, 通道默认不消费; 校准器经
    IdentifierGroundingJudge.from_config构建后由调用方注入)."""

    description: str = field(default="", compare=False)
    """配置说明(仅文档用途, 不参与通道行为; 不参与等价比较)."""

    def to_dict(self) -> dict[str, Any]:
        """与配置文件同形状的dict(json.dumps写回后load_rules可无损读出)."""
        return {
            "schema_version": 1,
            "description": self.description,
            "explicit_negation": {
                "pattern": self.explicit_negation_pattern,
            },
            "slot_fields": [[keyword, list(fields)]
                            for keyword, fields in self.slot_fields],
            "channel_patterns": {
                "identifier_subject_suffix": self.identifier_subject_suffix,
                "enum_separator": self.enum_separator,
            },
            "channel_thresholds": {
                "negation_prefix_window": self.negation_prefix_window,
                "identifier_window_before": self.identifier_window_before,
                "identifier_window_after": self.identifier_window_after,
                "identifier_subject_min_len": self.identifier_subject_min_len,
                "enum_member_min_len": self.enum_member_min_len,
            },
            "channel_confidences": {
                "closed_scope_exclusion":
                    self.closed_scope_exclusion_confidence,
                "nli_residual": self.nli_residual_confidence,
                "identifier_grounding": {
                    "threshold": self.identifier_grounding.threshold,
                    "feature_weights":
                        self.identifier_grounding.feature_weights(),
                    "predicate_glue":
                        list(self.identifier_grounding.predicate_glue),
                },
            },
        }


@dataclass(frozen=True)
class CompiledChannelRules:
    """``ClaimChannelRules`` 的编译形态(通道直接消费的执行层)."""

    explicit_negation: re.Pattern[str]
    identifier_subject_suffix: re.Pattern[str]
    enum_separator: re.Pattern[str]
    slot_fields: tuple[tuple[str, tuple[str, ...]], ...]
    negation_prefix_window: int
    identifier_window_before: int
    identifier_window_after: int
    identifier_subject_min_len: int
    enum_member_min_len: int
    closed_scope_exclusion_confidence: float
    nli_residual_confidence: float
    identifier_grounding: IdentifierGroundingConfig


def _rules_error(path: Path, message: str) -> ValueError:
    return ValueError(f"claim通道规则配置错误 {path}: {message}")


def _check_pattern(path: Path, name: str, value: Any) -> None:
    """字段必须是可编译的非空正则(坏正则→可读ValueError, 不静默)."""
    if not isinstance(value, str) or not value.strip():
        raise _rules_error(path, f"{name}期望非空字符串, 实际{value!r}")
    try:
        re.compile(value)
    except re.error as exc:
        raise _rules_error(
            path, f"{name}的正则{value!r}无法编译: {exc}") from exc


def _check_description(path: Path, section_name: str, section: Any) -> None:
    if not isinstance(section.get("description", ""), str):
        raise _rules_error(path, f"{section_name}.description期望字符串")


def _validate_negation_section(path: Path, section: Any) -> None:
    if not isinstance(section, dict):
        raise _rules_error(
            path, f"'explicit_negation'期望对象, 实际{type(section).__name__}")
    unknown = sorted(set(section) - {"pattern", "description"})
    if unknown:
        raise _rules_error(path, f"'explicit_negation'未知字段 {unknown}")
    if "pattern" not in section:
        raise _rules_error(path, "'explicit_negation.pattern'缺失")
    _check_pattern(path, "explicit_negation.pattern", section["pattern"])
    _check_description(path, "explicit_negation", section)


def _validate_slot_fields(path: Path, section: Any) -> None:
    if not isinstance(section, list):
        raise _rules_error(
            path, f"'slot_fields'期望数组, 实际{type(section).__name__}")
    keywords: list[str] = []
    for index, entry in enumerate(section):
        if (not isinstance(entry, list) or len(entry) != 2
                or not isinstance(entry[0], str) or not entry[0].strip()):
            raise _rules_error(
                path, f"slot_fields[{index}]期望[关键词, [字段...]]二元组, "
                f"实际{entry!r}")
        keyword, fields = entry
        if (not isinstance(fields, list) or not fields
                or any(not isinstance(f, str) or not f.strip()
                       for f in fields)):
            raise _rules_error(
                path, f"slot_fields[{index}]{keyword!r}的字段表"
                f"期望非空字符串数组")
        keywords.append(keyword)
    duplicates = sorted({k for k in keywords if keywords.count(k) > 1})
    if duplicates:
        raise _rules_error(
            path, f"slot_fields关键词重复 {duplicates}"
            f"(重复条目会重复注入同名字段)")


def _validate_pattern_section(path: Path, section: Any) -> None:
    if not isinstance(section, dict):
        raise _rules_error(
            path, f"'channel_patterns'期望对象, 实际{type(section).__name__}")
    unknown = sorted(set(section) - set(_PATTERN_KEYS) - {"description"})
    if unknown:
        raise _rules_error(path, f"'channel_patterns'未知字段 {unknown}")
    missing = [key for key in _PATTERN_KEYS if key not in section]
    if missing:
        raise _rules_error(path, f"'channel_patterns'缺失字段 {missing}")
    for key in _PATTERN_KEYS:
        _check_pattern(path, f"channel_patterns.{key}", section[key])
    _check_description(path, "channel_patterns", section)


def _validate_threshold_section(path: Path, section: Any) -> None:
    if not isinstance(section, dict):
        raise _rules_error(
            path, f"'channel_thresholds'期望对象, 实际{type(section).__name__}")
    unknown = sorted(set(section) - set(_THRESHOLD_KEYS) - {"description"})
    if unknown:
        raise _rules_error(path, f"'channel_thresholds'未知字段 {unknown}")
    missing = [key for key in _THRESHOLD_KEYS if key not in section]
    if missing:
        raise _rules_error(path, f"'channel_thresholds'缺失字段 {missing}")
    for key in _THRESHOLD_KEYS:
        value = section[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise _rules_error(
                path, f"channel_thresholds.{key}期望>=1的整数, 实际{value!r}")
    _check_description(path, "channel_thresholds", section)


def _validate_grounding_section(path: Path, section: Any) -> None:
    """identifier_grounding配置节校验(阈值范围/权重键/胶水词表)."""
    if not isinstance(section, dict):
        raise _rules_error(
            path, f"channel_confidences.identifier_grounding期望对象, "
            f"实际{type(section).__name__}")
    unknown = sorted(set(section)
                     - {"threshold", "feature_weights", "predicate_glue",
                        "description"})
    if unknown:
        raise _rules_error(
            path, f"identifier_grounding未知字段 {unknown}")
    threshold = section.get("threshold")
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not 0.0 < float(threshold) < 1.0):
        raise _rules_error(
            path, f"identifier_grounding.threshold期望(0,1)内数值, "
            f"实际{threshold!r}")
    weights = section.get("feature_weights")
    if not isinstance(weights, dict):
        raise _rules_error(
            path, "identifier_grounding.feature_weights期望对象")
    missing_weights = [key for key in _GROUNDING_WEIGHT_KEYS
                       if key not in weights]
    if missing_weights:
        raise _rules_error(
            path, f"identifier_grounding.feature_weights缺失键 "
            f"{missing_weights}")
    for key in _GROUNDING_WEIGHT_KEYS:
        value = weights[key]
        if (isinstance(value, bool) or not isinstance(value, (int, float))):
            raise _rules_error(
                path, f"feature_weights.{key}期望数值, 实际{value!r}")
    glue = section.get("predicate_glue")
    if (not isinstance(glue, list) or not glue
            or any(not isinstance(word, str) or not word.strip()
                   for word in glue)):
        raise _rules_error(
            path, "identifier_grounding.predicate_glue期望非空字符串数组")
    _check_description(path, "identifier_grounding", section)


def _validate_confidence_section(path: Path, section: Any) -> None:
    if not isinstance(section, dict):
        raise _rules_error(
            path, f"'channel_confidences'期望对象, 实际{type(section).__name__}")
    unknown = sorted(set(section) - set(_CONFIDENCE_KEYS)
                     - {"identifier_grounding", "description"})
    if unknown:
        raise _rules_error(path, f"'channel_confidences'未知字段 {unknown}")
    missing = [key for key in _CONFIDENCE_KEYS if key not in section]
    if missing:
        raise _rules_error(path, f"'channel_confidences'缺失字段 {missing}")
    for key in _CONFIDENCE_KEYS:
        value = section[key]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not 0.0 <= value <= 1.0):
            raise _rules_error(
                path, f"channel_confidences.{key}期望[0,1]内数值, 实际{value!r}")
    if "identifier_grounding" not in section:
        raise _rules_error(
            path, "channel_confidences.identifier_grounding缺失"
            "(R2挂点; 校准配置, 通道默认不消费)")
    _validate_grounding_section(path, section["identifier_grounding"])
    _check_description(path, "channel_confidences", section)


def _validate(path: Path, raw: Any) -> dict[str, Any]:
    """schema校验: 缺节/未知键/类型错/坏正则 → 可读ValueError(不静默)."""
    if not isinstance(raw, dict):
        raise _rules_error(
            path, f"顶层期望JSON对象, 实际{type(raw).__name__}")
    missing = [section for section in _REQUIRED_SECTIONS if section not in raw]
    if missing:
        raise _rules_error(path, f"缺失字段 {missing}")
    unknown = sorted(set(raw) - set(_REQUIRED_SECTIONS)
                     - {"schema_version", "description"})
    if unknown:
        raise _rules_error(path, f"未知字段 {unknown}")
    if raw.get("schema_version", 1) != 1:
        raise _rules_error(
            path, f"不支持的schema_version {raw.get('schema_version')!r}(期望1)")
    if not isinstance(raw.get("description", ""), str):
        raise _rules_error(path, "'description'期望字符串")
    _validate_negation_section(path, raw["explicit_negation"])
    _validate_slot_fields(path, raw["slot_fields"])
    _validate_pattern_section(path, raw["channel_patterns"])
    _validate_threshold_section(path, raw["channel_thresholds"])
    _validate_confidence_section(path, raw["channel_confidences"])
    return raw


def _grounding_from_section(
        section: dict[str, Any]) -> IdentifierGroundingConfig:
    weights = section["feature_weights"]
    return IdentifierGroundingConfig(
        threshold=float(section["threshold"]),
        subject_bind_weight=float(weights["subject_bind_ratio"]),
        predicate_hit_weight=float(weights["predicate_hit_ratio"]),
        id_block_weight=float(weights["id_block_ratio"]),
        proximity_weight=float(weights["subject_id_proximity"]),
        intercept=float(weights["intercept"]),
        predicate_glue=tuple(str(word) for word in section["predicate_glue"]),
    )


def load_rules(path: str | Path) -> ClaimChannelRules:
    """加载并校验一份通道规则JSON(非法配置抛可读ValueError, 不静默降级)."""
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"claim通道规则文件不存在: {config_path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _rules_error(config_path, f"JSON解析失败: {exc}") from exc
    validated = _validate(config_path, raw)
    patterns = validated["channel_patterns"]
    thresholds = validated["channel_thresholds"]
    confidences = validated["channel_confidences"]
    return ClaimChannelRules(
        explicit_negation_pattern=validated["explicit_negation"]["pattern"],
        slot_fields=tuple((entry[0], tuple(entry[1]))
                          for entry in validated["slot_fields"]),
        identifier_subject_suffix=patterns["identifier_subject_suffix"],
        enum_separator=patterns["enum_separator"],
        negation_prefix_window=thresholds["negation_prefix_window"],
        identifier_window_before=thresholds["identifier_window_before"],
        identifier_window_after=thresholds["identifier_window_after"],
        identifier_subject_min_len=thresholds["identifier_subject_min_len"],
        enum_member_min_len=thresholds["enum_member_min_len"],
        closed_scope_exclusion_confidence=float(
            confidences["closed_scope_exclusion"]),
        nli_residual_confidence=float(confidences["nli_residual"]),
        identifier_grounding=_grounding_from_section(
            confidences["identifier_grounding"]),
        description=str(validated.get("description", "")),
    )


def compile_rules(rules: ClaimChannelRules) -> CompiledChannelRules:
    """把数据形态规则编译为执行形态(正则预编译, 通道直接消费)."""
    return CompiledChannelRules(
        explicit_negation=re.compile(rules.explicit_negation_pattern),
        identifier_subject_suffix=re.compile(rules.identifier_subject_suffix),
        enum_separator=re.compile(rules.enum_separator),
        slot_fields=rules.slot_fields,
        negation_prefix_window=rules.negation_prefix_window,
        identifier_window_before=rules.identifier_window_before,
        identifier_window_after=rules.identifier_window_after,
        identifier_subject_min_len=rules.identifier_subject_min_len,
        enum_member_min_len=rules.enum_member_min_len,
        closed_scope_exclusion_confidence=(
            rules.closed_scope_exclusion_confidence),
        nli_residual_confidence=rules.nli_residual_confidence,
        identifier_grounding=rules.identifier_grounding,
    )


_BUILTIN_RULES: ClaimChannelRules | None = None


def builtin_rules() -> ClaimChannelRules:
    """内置默认规则(与 config/claim_channels_rules_v1.json 逐值相同).

    双层保险的Python侧: JSON缺失/损坏时 default_rules() 回退到这里,
    任何环境下行为一致. 修改任一侧须同步另一侧并跑
    tests/test_claim_channels_rules.py 的等价性锁定.
    """
    global _BUILTIN_RULES
    if _BUILTIN_RULES is None:
        _BUILTIN_RULES = ClaimChannelRules(
            explicit_negation_pattern=_EXPLICIT_NEGATION_PATTERN,
            slot_fields=_SLOT_FIELDS,
            identifier_subject_suffix=_IDENTIFIER_SUBJECT_SUFFIX,
            enum_separator=_ENUM_SEPARATOR,
            negation_prefix_window=_NEGATION_PREFIX_WINDOW,
            identifier_window_before=_IDENTIFIER_WINDOW_BEFORE,
            identifier_window_after=_IDENTIFIER_WINDOW_AFTER,
            identifier_subject_min_len=_IDENTIFIER_SUBJECT_MIN_LEN,
            enum_member_min_len=_ENUM_MEMBER_MIN_LEN,
            closed_scope_exclusion_confidence=(
                _CLOSED_SCOPE_EXCLUSION_CONFIDENCE),
            nli_residual_confidence=_NLI_RESIDUAL_CONFIDENCE,
            identifier_grounding=_IDENTIFIER_GROUNDING,
        )
    return _BUILTIN_RULES


def _load_or_default(path: str | Path) -> ClaimChannelRules:
    """读一份规则文件; 失败回退内置默认(可见RuntimeWarning, 行为不变)."""
    try:
        return load_rules(path)
    except (ValueError, OSError) as exc:
        warnings.warn(
            f"claim通道规则配置加载失败({exc}); 回退内置默认规则"
            f"(与{CLAIM_CHANNELS_RULES_FILE.name}同内容, 通道行为不变)",
            RuntimeWarning, stacklevel=2)
        return builtin_rules()


_DEFAULT_COMPILED_RULES: CompiledChannelRules | None = None


def default_rules() -> CompiledChannelRules:
    """通道消费的默认编译规则(惰性加载 + 模块级缓存, 模块顶层零I/O).

    优先读 config/claim_channels_rules_v1.json; 文件缺失/损坏时回退
    内置常量并发出可见警告——两个来源内容相同, 行为完全一致.
    """
    global _DEFAULT_COMPILED_RULES
    if _DEFAULT_COMPILED_RULES is None:
        _DEFAULT_COMPILED_RULES = compile_rules(
            _load_or_default(CLAIM_CHANNELS_RULES_FILE))
    return _DEFAULT_COMPILED_RULES


@dataclass(frozen=True)
class SemanticNliJudge:
    """Instance-level NLI configuration for the residual semantic channel.

    Carries the former QAConsistencyModule state: the predictor callable
    and the two calibrated decision thresholds.
    """

    predictor: NliPredictor
    contra_threshold: float
    entail_threshold: float


def unresolved(request: QAInput, claim: AnswerClaim, index: int,
               check_items: tuple[str, ...], rationale: str,
               refs: tuple[str, ...] = ()) -> ClaimResult:
    """Conservative not-in-evidence ClaimResult (former ``_unresolved``)."""
    return ClaimResult(
        claim_id=f"{request.instance_id}-c{index:02d}",
        claim_text=claim.text,
        verdict="not_in_evidence",
        check_item_candidates=check_items,
        evidence_refs=refs,
        rationale=rationale,
        method="conservative_unresolved",
        confidence=0.0,
        span=claim.span,
    )


def same_subject(answer_subject: str, evidence_subject: str,
                 question: str) -> bool:
    """Subject match with question-anchored short-form acceptance."""
    a = re.sub(r"\s+", "", answer_subject).removesuffix("的")
    e = re.sub(r"\s+", "", evidence_subject).removesuffix("的")
    if not a or not e:
        return False
    if a == e:
        return True
    # Short answer may use an unqualified form of the question's parameter
    # (e.g. answer "响应时间" vs evidence "系统响应时间"). Accept only when
    # one is a qualified form of the other and the unqualified form appears
    # in the question, so unrelated parameters are not silently merged.
    if a in e or e in a:
        shorter = a if len(a) < len(e) else e
        return shorter in re.sub(r"\s+", "", question)
    return False


def interval(operator: str, value: float) -> tuple[float, bool, float, bool] | None:
    op = normalize_op(operator)
    if op == "le":
        return float("-inf"), False, value, True
    if op == "lt":
        return float("-inf"), False, value, False
    if op == "ge":
        return value, True, float("inf"), False
    if op == "gt":
        return value, False, float("inf"), False
    if op == "eq":
        return value, True, value, True
    return None


def subset(a: tuple[float, bool, float, bool],
           b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    lower_ok = al > bl or (al == bl and (not alc or blc))
    upper_ok = au < bu or (au == bu and (not auc or buc))
    return lower_ok and upper_ok


def disjoint(a: tuple[float, bool, float, bool],
             b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    a_before_b = au < bl or (au == bl and not (auc and blc))
    b_before_a = bu < al or (bu == al and not (buc and alc))
    return a_before_b or b_before_a


def verify_numeric(request: QAInput, claim: AnswerClaim,
                   index: int, check_items: tuple[str, ...]) -> ClaimResult:
    answer_unit = normalize_unit(claim.value, claim.unit)
    if answer_unit is None:
        return unresolved(request, claim, index, check_items,
                          "answer数值单位无法归一化")
    answer_interval = interval(claim.operator, answer_unit[0])
    if answer_interval is None:
        return unresolved(request, claim, index, check_items,
                          "answer操作符不在已验证范围")

    matches: list[tuple[RetrievedEvidence, Verdict, str]] = []
    for evidence in request.evidence:
        for attr, operator, value, unit in extract_numeric_claims(evidence.text):
            if not same_subject(claim.attr, attr, request.question):
                continue
            ev_unit = normalize_unit(value, unit)
            if ev_unit is None or ev_unit[1] != answer_unit[1]:
                continue
            ev_interval = interval(operator, ev_unit[0])
            if ev_interval is None:
                continue
            if (subset(ev_interval, answer_interval)
                    or subset(answer_interval, ev_interval)):
                matches.append((evidence, "support", "context约束蕴含answer约束"))
            elif disjoint(ev_interval, answer_interval):
                matches.append((evidence, "refute", "context与answer数值区间互斥"))
            else:
                matches.append((evidence, "not_in_evidence",
                                "数值区间重叠但不互相蕴含，无法证明一致或矛盾"))
    decisive = [x for x in matches if x[1] in ("support", "refute")]
    decisive_labels = {x[1] for x in decisive}
    if len(decisive_labels) > 1:
        return unresolved(request, claim, index, check_items,
                          "冻结context含相互冲突的数值证据",
                          tuple(sorted({x[0].evidence_id for x in decisive})))
    if decisive:
        ev, verdict, reason = decisive[0]
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict=verdict,
            check_item_candidates=check_items,
            evidence_refs=(ev.evidence_id,),
            rationale=reason,
            method="numeric_interval",
            confidence=1.0,
                span=claim.span,
        )
    refs = tuple(sorted({x[0].evidence_id for x in matches}))
    return unresolved(request, claim, index, check_items,
                      matches[0][2] if matches else "context无同subject/单位数值证据",
                      refs)


def verify_quoted(request: QAInput, claim: AnswerClaim,
                  index: int, check_items: tuple[str, ...]) -> ClaimResult:
    rules = default_rules()
    target = re.sub(r"\s+", "", claim.text)
    positive_refs: list[str] = []
    negative_refs: list[str] = []
    for ev in request.evidence:
        normalized = re.sub(r"\s+", "", ev.text)
        start = 0
        while True:
            pos = normalized.find(target, start)
            if pos < 0:
                break
            prefix = normalized[
                max(0, pos - rules.negation_prefix_window):pos]
            if rules.explicit_negation.search(prefix):
                negative_refs.append(ev.evidence_id)
            else:
                positive_refs.append(ev.evidence_id)
            start = pos + len(target)

    supporting_refs = negative_refs if claim.negative else positive_refs
    refuting_refs = positive_refs if claim.negative else negative_refs
    if supporting_refs:
        if refuting_refs:
            return unresolved(
                request, claim, index, check_items,
                "冻结context对同一引用项同时包含支持和显式否定证据",
                tuple(sorted(set(supporting_refs + refuting_refs))),
            )
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(supporting_refs))),
            rationale="answer声明的极性与context中的显式提及一致",
            method="explicit_quote_polarity",
            confidence=1.0,
                span=claim.span,
        )
    if refuting_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="refute",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(refuting_refs))),
            rationale="context对answer引用项存在显式相反极性",
            method="explicit_quote_polarity",
            confidence=1.0,
                span=claim.span,
        )
    closed = [ev for ev in request.evidence
              if ev.completeness == "closed" and ev.completeness_proof.strip()]
    if (closed and len(closed) == len(request.evidence)
            and all(ev.scope_id == closed[0].scope_id for ev in closed)):
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support" if claim.negative else "refute",
            check_item_candidates=check_items,
            evidence_refs=tuple(ev.evidence_id for ev in closed),
            rationale="封闭scope中未出现该条目，与answer极性相符",
            method="closed_scope_exclusion",
            confidence=rules.closed_scope_exclusion_confidence,
                span=claim.span,
        )
    return unresolved(request, claim, index, check_items,
                      "引用项未命中冻结context，scope不完整或未证明穷举")


def verify_identifier(request: QAInput, claim: AnswerClaim,
                      index: int, check_items: tuple[str, ...],
                      grounding: IdentifierGroundingJudge | None = None,
                      ) -> ClaimResult:
    """Exact identifier matching against the frozen evidence (TERM-07).

    support: the answer identifier appears verbatim in the evidence.
    refute: the evidence states a different identifier for the same
    subject statement. Everything else stays NIE.

    R2 (99号Phase 3, 98号B类切口①): when a grounding judge is injected,
    the support path's confidence becomes the calibrated
    P(binding | presence, context) instead of the constant 1.0 — the
    "ID present ⇒ support@1.0" trust assumption is exactly what
    C06QA-016/017 falsified (right detail, wrong entity). Contract:

    - ``grounding=None`` (default): bit-identical to the pre-R2 channel;
    - presence stays a necessary condition (absent → refute/NIE paths
      unchanged);
    - the same-subject-mismatch refute path stays deterministic 1.0
      (B类代数本体不动);
    - P < judge threshold → conservative NIE downgrade ("在场但绑定
      不确定"——not a refute: failure to corroborate the binding is
      uncertainty, not contradiction).
    """
    rules = default_rules()
    target = claim.text
    subject = re.sub(r"\s+", "", claim.attr or "")
    subject_core = re.sub(rules.identifier_subject_suffix, "", subject)
    if len(subject_core) < rules.identifier_subject_min_len:
        subject_core = subject
    hit_refs = tuple(
        ev.evidence_id for ev in request.evidence
        if target in ev.text
    )
    if hit_refs:
        if grounding is None:
            return ClaimResult(
                claim_id=f"{request.instance_id}-c{index:02d}",
                claim_text=claim.text,
                verdict="support",
                check_item_candidates=check_items,
                evidence_refs=hit_refs,
                rationale="answer标识符在冻结context中精确出现",
                method="identifier_exact_match",
                confidence=1.0,
                span=claim.span,
            )
        probability, features = grounding.grounding_probability(
            request, claim, rules.identifier_subject_suffix)
        if probability >= grounding.threshold:
            return ClaimResult(
                claim_id=f"{request.instance_id}-c{index:02d}",
                claim_text=claim.text,
                verdict="support",
                check_item_candidates=check_items,
                evidence_refs=hit_refs,
                rationale=(f"answer标识符在冻结context中精确出现, "
                           f"绑定接地概率{probability:.3f}"
                           f"(谓词一致性{features.predicate_hit_ratio:.2f})"),
                method="identifier_exact_match",
                confidence=probability,
                span=claim.span,
            )
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="not_in_evidence",
            check_item_candidates=check_items,
            evidence_refs=hit_refs,
            rationale=(f"标识符在冻结context在场, 但answer局部断言与证据"
                       f"ID绑定段的接地概率{probability:.3f}低于阈值"
                       f"{grounding.threshold:.3f}(谓词一致性"
                       f"{features.predicate_hit_ratio:.2f}, "
                       f"内容词{features.n_predicate_terms}个)——在场但"
                       f"绑定不确定, 保守降级"),
            method="identifier_grounding",
            confidence=probability,
            span=claim.span,
        )
    if subject_core:
        for ev in request.evidence:
            compact = re.sub(r"\s+", "", ev.text)
            start = compact.find(subject_core)
            while start >= 0:
                window = compact[max(0, start - rules.identifier_window_before):
                                  min(len(compact),
                                      start + len(subject_core)
                                      + rules.identifier_window_after)]
                window_ids = _IDENTIFIER.findall(window)
                if len(window_ids) == 1 and window_ids[0] != target:
                    return ClaimResult(
                        claim_id=f"{request.instance_id}-c{index:02d}",
                        claim_text=claim.text,
                        verdict="refute",
                        check_item_candidates=check_items,
                        evidence_refs=(ev.evidence_id,),
                        rationale=("同subject局部窗口中context声明了不同标识符"
                                   f"（{window_ids[0]}），显式值冲突"),
                        method="identifier_exact_match",
                        confidence=1.0,
                            span=claim.span,
                    )
                start = compact.find(subject_core, start + 1)
    return unresolved(request, claim, index, check_items,
                      "标识符未在冻结context命中，且无同subject的显式不同值")


def verify_enum(request: QAInput, claim: AnswerClaim,
                index: int, check_items: tuple[str, ...]) -> ClaimResult:
    """Legacy per-member substring enum channel.

    Known design flaw: member-level hits can mask set-level conflicts
    (e.g. answer {A,B,C} vs evidence {A,B} where each member hits
    individually). The ``enum_join_expert`` (L1) handles set-level joins
    with domain registries. This legacy channel is retained only for
    explicit-exclusion detection (context explicitly negates a member),
    and its per-member "all found -> support" path is downgraded to
    NIE to avoid false supports when the evidence set is not proven
    exhaustive.
    """
    rules = default_rules()
    items = [part.strip()
             for part in rules.enum_separator.split(claim.text)
             if len(part.strip()) >= rules.enum_member_min_len]
    found: dict[str, list[str]] = {}
    excluded: dict[str, list[str]] = {}
    for item in items:
        needle = re.sub(r"\s+", "", item)
        found[item] = []
        excluded[item] = []
        for ev in request.evidence:
            text = re.sub(r"\s+", "", ev.text)
            start = 0
            while True:
                pos = text.find(needle, start)
                if pos < 0:
                    break
                prefix = text[
                    max(0, pos - rules.negation_prefix_window):pos]
                target = (excluded if rules.explicit_negation.search(prefix)
                          else found)
                target[item].append(ev.evidence_id)
                start = pos + len(needle)
    explicit_exclusions = tuple(sorted({
        ref for refs in excluded.values() for ref in refs
    }))
    positive_refs = tuple(sorted({ref for refs in found.values() for ref in refs}))
    if explicit_exclusions and positive_refs:
        return unresolved(
            request, claim, index, check_items,
            "枚举context同时含正向命中与显式排除，需仲裁context内部冲突",
            tuple(sorted(set(explicit_exclusions + positive_refs))),
        )
    if explicit_exclusions:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="refute",
            check_item_candidates=check_items,
            evidence_refs=explicit_exclusions,
            rationale="context对answer枚举成员存在显式排除语句",
            method="explicit_enum_exclusion",
            confidence=1.0,
                span=claim.span,
        )
    missing = [item for item, refs in found.items() if not refs]
    refs = positive_refs
    if not missing:
        return unresolved(
            request, claim, index, check_items,
            "枚举成员均在context出现，但context未证明穷举；"
            "集合级比对由enum_join专家负责",
            refs)
    return unresolved(request, claim, index, check_items,
                      f"枚举成员未全部命中({len(missing)}项)；未证明context穷举", refs)


def verify_semantic(request: QAInput, claim: AnswerClaim,
                    index: int, check_items: tuple[str, ...],
                    statements: tuple,
                    judge: SemanticNliJudge | None = None) -> ClaimResult:
    answer_text = re.sub(r"\s+", "", claim.text)
    exact_refs = tuple(
        ev.evidence_id for ev in request.evidence
        if answer_text and answer_text in re.sub(r"\s+", "", ev.text)
    )
    if exact_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=exact_refs,
            rationale="answer原子声明在冻结context中精确出现",
            method="exact_statement",
            confidence=1.0,
                span=claim.span,
        )
    for statement in statements:
        if answer_text and answer_text in re.sub(r"\s+", "", statement.text):
            return ClaimResult(
                claim_id=f"{request.instance_id}-c{index:02d}",
                claim_text=claim.text,
                verdict="support",
                check_item_candidates=check_items,
                evidence_refs=(statement.evidence_id,),
                rationale=(f"answer声明与线性化证据语句精确匹配"
                           f"（{statement.statement_id}）"),
                method="statement_exact",
                confidence=1.0,
                    span=claim.span,
            )
    nli_result = verify_semantic_nli(request, claim, index,
                                     check_items, statements, judge)
    if nli_result is not None:
        return nli_result
    return ClaimResult(
        claim_id=f"{request.instance_id}-c{index:02d}",
        claim_text=claim.text,
        verdict="not_in_evidence",
        check_item_candidates=check_items,
        evidence_refs=(),
        rationale="当前语义声明没有经过验证的三态判定器；不将旧pair二分类结果映射为三态。",
        method="semantic_unresolved",
        confidence=0.0,
            span=claim.span,
    )


def verify_semantic_nli(request: QAInput, claim: AnswerClaim,
                        index: int, check_items: tuple[str, ...],
                        statements: tuple,
                        judge: SemanticNliJudge | None) -> ClaimResult | None:
    """Residual NLI channel on scope- and slot-matched statement pairs."""
    rules = default_rules()
    if judge is None or not statements:
        return None
    structured = decompose_answer(claim.text, request.question)
    if not structured:
        return None
    pairs = pair_statements(structured, list(statements))
    if not pairs:
        return None
    claim_slots = tuple(
        field for keyword, fields in rules.slot_fields
        if keyword in claim.text for field in fields)
    if claim_slots:
        pairs = [(structural, statement) for structural, statement in pairs
                 if statement.field_name in claim_slots]
    if not pairs:
        return None
    hypotheses = [(statement.text, structural.text)
                  for structural, statement in pairs]
    labels = judge.predictor(hypotheses)
    contradiction_refs = []
    entailment_refs = []
    scope = re.sub(r"\s+", "", claim.attr or "")
    for (structural, statement), label in zip(pairs, labels):
        verdict = (str(label.get("label", "neutral"))
                   if isinstance(label, dict) else str(label))
        contra_prob = (float(label.get("p_contra", 0.0))
                       if isinstance(label, dict) else
                       (1.0 if verdict == "contradiction" else 0.0))
        entail_prob = (float(label.get("p_entail", 0.0))
                       if isinstance(label, dict) else
                       (1.0 if verdict == "entailment" else 0.0))
        scope_matched = (scope and statement.scope_key
                         and (scope in statement.scope_key
                              or statement.scope_key in scope))
        if (verdict == "contradiction"
                and contra_prob >= judge.contra_threshold
                and scope_matched):
            contradiction_refs.append(statement.evidence_id)
        elif verdict == "entailment" and entail_prob >= judge.entail_threshold:
            entailment_refs.append(statement.evidence_id)
    if contradiction_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="refute",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(contradiction_refs))),
            rationale="scope匹配的证据语句与answer声明NLI矛盾",
            method="nli_residual",
            confidence=rules.nli_residual_confidence,
                span=claim.span,
        )
    if entailment_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(entailment_refs))),
            rationale="scope匹配的证据语句NLI蕴含answer声明",
            method="nli_residual",
            confidence=rules.nli_residual_confidence,
                span=claim.span,
        )
    return None
