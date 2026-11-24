"""R2: identifier通道接地概率化——绑定评分器与校准配置 (99号Phase 3 / 98号B类切口①).

问题(06号C06QA-016/017实证): ``verify_identifier`` 的 support 路径信任
"ID字面在场 ⇒ support@1.0"。但标识符出现在证据里不代表 answer 声称的
**绑定关系**成立——发送方跨行污染(r_sender_swap)/效果性断言杜撰
(n_effect_claim)都产出"ID在场但绑定错"的假 support(right detail,
wrong entity)。

本模块按 PL-Guard(97号§2.4)的"接地概率化"思想, 把在场证据落成
P(绑定|在场, context) 的校准概率:

1. **特征层**(:func:`extract_grounding_features`): 纯确定性词法/邻近
   特征(零模型调用/零I/O/零远程API), 全部在空白折叠文本上计算:
   - ``subject_bind_ratio``  —— answer的subject核心前缀在ID局部绑定
     窗口(证据ID所在行段)中的最长命中占比;
   - ``predicate_hit_ratio`` —— answer局部断言上下文的内容词在证据
     ID绑定段中的命中率(上下文谓词一致性, 97号§2.4的接地谓词);
   - ``id_block_ratio``      —— ID在多少个证据块中在场(跨块佐证广度);
   - ``subject_id_proximity``—— subject前缀到ID的邻近距离软特征
     (原30/100硬窗口升格为软分数, 99号R2)。
2. **评分层**(:class:`IdentifierGroundingJudge`): 逻辑回归
   sigmoid(w·f + b)——权重与阈值由 tools/calibrate_identifier_grounding.py
   在误判案例库上确定性校准(IRLS闭式牛顿迭代, 固定迭代数, 无随机源),
   校准产物写进 config/claim_channels_rules_v1.json 的
   channel_confidences.identifier_grounding 节(阈值+特征权重+谓词
   胶水词表), 与内置回退常量逐值相同(E7双层保险, 等价性由
   tests/test_claim_channels_rules.py 锁定)。

通道层契约(98号B类判定: 代数本体零学习, 学习的是代数的输入信任):
- 评分函数不进 ``claim_channels``——通道保持确定性, 概率由外部
  校准器实例注入(:class:`IdentifierGroundingJudge`, qa_module构造
  参数 ``identifier_grounding``, None=不注入, 行为与R2前逐位一致);
- presence保持必要条件: 无在场→refute/NIE路径完全不变;
- refute路径(同subject窗口内唯一不同ID)保持确定性1.0;
- 低于阈值→**降级NIE**("在场但绑定不确定"的新保守语义, 不是refute
  ——无法证明绑定成立时不说矛盾, 只说不可信)。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # 仅类型契约, 运行时零导入(模块顶层零I/O/零循环依赖)
    from algorithms.consistency.answer_claims import AnswerClaim
    from algorithms.consistency.qa_models import QAInput

#: 空白折叠(与通道层同一归一化口径)
_COMPACT_RE = re.compile(r"\s+")

#: answer局部上下文的内容词: 中文连续段(2-20字; 上限20防长谓词被切碎
#: 产生"用软件"式碎片假命中, 胶水词切分负责拆框架词)
_CHINESE_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,20}")

#: answer局部上下文的内容词: 字母数字连续段(3-16字, 如 4.1.2 / API)
_ALNUM_RUN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9./]{2,16}")

#: 表格块的行段切分标记(HTML行边界; 非表格块整块为一个绑定段)
_ROW_SPLIT = "</tr>"

#: 绑定段内的HTML标记剥离(单元格文本拼接, 与线性化层同语义)
_TAG_RE = re.compile(r"<[^>]+>")

#: subject前缀到ID邻近距离的归一化尺度(软窗口: 距离≥60字符→0分)
_PROXIMITY_SCALE = 60.0

#: 跨块佐证广度的封顶块数(≥3块记满分)
_MAX_BLOCKS = 3


@dataclass(frozen=True)
class IdentifierGroundingConfig:
    """identifier接地概率化的校准配置(规则资产, JSON↔内置回退逐值相同).

    由 tools/calibrate_identifier_grounding.py 在误判案例库上确定性
    校准后写入 config/claim_channels_rules_v1.json; 修改任一侧必须
    同步另一侧(tests/test_claim_channels_rules.py 锁定等价性)。
    """

    threshold: float
    """support降级阈值: P(绑定) ≥ threshold → support@P; < → 保守NIE."""

    subject_bind_weight: float
    predicate_hit_weight: float
    id_block_weight: float
    proximity_weight: float
    intercept: float
    """逻辑回归权重(四个特征 + 截距), sigmoid线性项系数."""

    predicate_glue: tuple[str, ...]
    """answer局部断言上下文的胶水词表(模板功能词/框架词): 命中不计入
    谓词一致性(如 通过/实现/发送至/信息交互 是answer模板框架而非绑定
    内容; 数据安全/高并发这类内容词**不在**此表, 正是它们的缺席暴露
    绑定可疑)。"""

    description: str = ""
    """配置说明(文档用途; 不参与等价比较)."""

    def feature_weights(self) -> dict[str, float]:
        return {
            "subject_bind_ratio": self.subject_bind_weight,
            "predicate_hit_ratio": self.predicate_hit_weight,
            "id_block_ratio": self.id_block_weight,
            "subject_id_proximity": self.proximity_weight,
            "intercept": self.intercept,
        }


@dataclass(frozen=True)
class GroundingFeatures:
    """一次ID在场判定的接地特征(全部∈[0,1], 确定性纯函数输出)."""

    subject_bind_ratio: float
    predicate_hit_ratio: float
    id_block_ratio: float
    subject_id_proximity: float
    #: 诊断字段(不进评分): 局部断言内容词数(0=无约束→谓词一致性取1.0)
    n_predicate_terms: int = 0
    #: 诊断字段(不进评分): ID在场的证据绑定段数
    n_hit_segments: int = 0

    def as_dict(self) -> dict[str, float | int]:
        return {
            "subject_bind_ratio": self.subject_bind_ratio,
            "predicate_hit_ratio": self.predicate_hit_ratio,
            "id_block_ratio": self.id_block_ratio,
            "subject_id_proximity": self.subject_id_proximity,
            "n_predicate_terms": self.n_predicate_terms,
            "n_hit_segments": self.n_hit_segments,
        }


def compact(text: str) -> str:
    """空白折叠(与通道/表段同一归一化)."""
    return _COMPACT_RE.sub("", text)


def answer_assertion_context(answer: str, target: str,
                             span: tuple[int, int] | None) -> str:
    """answer中含ID的**局部断言上下文**: 所在行→行内所在句.

    语义: identifier claim是answer的原子断言, 其绑定语境=answer中承载
    该ID的那一行/那一句(列表项不跨行、句子不跨句读), 而不是任意半径
    窗口——"序号1：ID"的下一列表项不属于本ID的断言语境。
    """
    if span is not None:
        start = span[0]
    else:
        start = answer.find(target)
        if start < 0:
            return ""
    line_begin = answer.rfind("\n", 0, start) + 1
    line_end = answer.find("\n", start)
    line = answer[line_begin: len(answer) if line_end < 0 else line_end]
    # 行内向后找第一个句读终点(句读不切分, 保留完整谓词语境)
    sent_end = len(line)
    for mark in "。；！？":
        pos = line.find(mark, start - line_begin)
        if 0 <= pos < sent_end:
            sent_end = pos
    sent_begin = 0
    for mark in "。；！？":
        pos = line.rfind(mark, 0, start - line_begin)
        if pos >= 0:
            sent_begin = max(sent_begin, pos + 1)
    return line[sent_begin:sent_end]


def evidence_binding_segments(evidence_text: str) -> list[str]:
    """一个证据块的**绑定段**列表: 表格块按</tr>行段切分(剥离HTML标记),
    其他块整段.

    行段=表格中一条记录(接口表一行/能力表一行)的紧凑文本——绑定
    (接口→发送方, 用例→任务书章节)是**行内**关系, 跨行命中是污染而
    非佐证(C06QA-016: 发送方"界面集成框架"来自同表第3行)。
    """
    if _ROW_SPLIT in evidence_text:
        parts = (_TAG_RE.sub("", part)
                 for part in evidence_text.split(_ROW_SPLIT))
        return [compact(part) for part in parts if compact(part)]
    text = compact(_TAG_RE.sub("", evidence_text))
    return [text] if text else []


def _longest_subject_prefix(subject_core: str, segment: str) -> int:
    """subject核心在绑定段内的最长前缀命中长度(≥2字符才有效)."""
    if not subject_core:
        return 0
    for length in range(len(subject_core), 1, -1):
        if subject_core[:length] in segment:
            return length
    return 0


def _split_on_glue(text: str, glue: tuple[str, ...]) -> list[str]:
    """按胶水词(长词优先)切开文本, 返回非空碎片(内容词候选)."""
    pieces = [text]
    for word in sorted(set(glue), key=len, reverse=True):
        expanded: list[str] = []
        for piece in pieces:
            expanded.extend(piece.split(word))
        pieces = [piece for piece in expanded if piece]
    return pieces


def _content_terms(context: str, target: str,
                   glue: tuple[str, ...]) -> list[str]:
    """answer局部断言上下文的内容词: 中文/字母数字连续段→按胶水词切开
    →过滤ID片段→去重保序.

    注意: 不过滤问句回声词与subject词——interface_flow族的问句
    ("{发送方}与{接收方}接口的接口流向是什么?")与subject(接口名)
    内嵌发送方/接收方, 过滤会把绑定内容词误删(实测label-1的
    predicate_hit_ratio被压到0.5); 问句模板词由glue词表承担。
    """
    terms: list[str] = []
    for run in [*(_CHINESE_RUN_RE.findall(context)),
                *(_ALNUM_RUN_RE.findall(context))]:
        for piece in _split_on_glue(run, glue):
            if len(piece) < 2 or piece in terms:
                continue
            if piece == target or piece in target or target in piece:
                continue
            terms.append(piece)
    return terms


def extract_grounding_features(
        request: QAInput, claim: AnswerClaim,
        subject_suffix: re.Pattern[str],
        predicate_glue: tuple[str, ...]) -> GroundingFeatures:
    """ID在场判定的接地特征(纯确定性, CPU词法, 零模型调用).

    消费通道层既有规则资产: ``subject_suffix``(identifier的subject后缀
    剥离正则)与胶水词表(配置面)——特征语义与refute路径同源。
    """
    target = claim.text
    # ── answer局部断言上下文与内容词 ──────────────────────────────
    context = compact(answer_assertion_context(
        request.answer, target, claim.span))
    context = context.replace(target, "", 1)
    subject = compact(claim.attr or "")
    subject_core = subject_suffix.sub("", subject) if subject else ""
    if len(subject_core) < 2:
        subject_core = subject
    terms = _content_terms(context, target, predicate_glue)
    # ── 证据侧ID绑定段(与hit_refs同口径: 原文在场才计) ────────────
    hit_segments: list[str] = []
    n_blocks = 0
    for ev in request.evidence:
        if target not in ev.text:
            continue
        n_blocks += 1
        for segment in evidence_binding_segments(ev.text):
            if target in segment:
                hit_segments.append(segment)
    # ── f1: subject核心前缀在绑定段内的最长命中占比 ──────────────
    if not subject_core:
        subject_bind_ratio = 1.0  # 裸ID声明: subject无约束
        best_prefix = ""
    else:
        best_len = 0
        for segment in hit_segments:
            best_len = max(best_len,
                           _longest_subject_prefix(subject_core, segment))
        subject_bind_ratio = (
            best_len / len(subject_core) if subject_core else 1.0)
        best_prefix = subject_core[:best_len] if best_len else ""
    # ── f2: 局部断言内容词在绑定段中的命中率(无内容词→无约束→1.0) ─
    if terms:
        hits = sum(1 for term in terms
                   if any(term in segment for segment in hit_segments))
        predicate_hit_ratio = hits / len(terms)
    else:
        predicate_hit_ratio = 1.0
        hits = 0
    # ── f3: 跨块佐证广度 ─────────────────────────────────────────
    id_block_ratio = min(n_blocks, _MAX_BLOCKS) / _MAX_BLOCKS
    # ── f4: subject前缀→ID邻近距离软特征(30/100硬窗口的软化) ──────
    if not subject_core or not best_prefix:
        subject_id_proximity = 1.0 if not subject_core else 0.0
    else:
        best_distance = _PROXIMITY_SCALE  # 未命中→0分
        for segment in hit_segments:
            id_at = segment.find(target)
            while id_at >= 0:
                prefix_at = segment.find(best_prefix)
                while prefix_at >= 0:
                    distance = abs(id_at - (prefix_at + len(best_prefix)))
                    best_distance = min(best_distance, distance)
                    prefix_at = segment.find(best_prefix, prefix_at + 1)
                id_at = segment.find(target, id_at + 1)
        subject_id_proximity = max(
            0.0, 1.0 - best_distance / _PROXIMITY_SCALE)
    return GroundingFeatures(
        subject_bind_ratio=subject_bind_ratio,
        predicate_hit_ratio=predicate_hit_ratio,
        id_block_ratio=id_block_ratio,
        subject_id_proximity=subject_id_proximity,
        n_predicate_terms=len(terms),
        n_hit_segments=len(hit_segments),
    )


@dataclass(frozen=True)
class IdentifierGroundingJudge:
    """identifier通道的实例级接地校准器(predictor+阈值, SemanticNliJudge模式).

    由调用方(qa_module ``identifier_grounding``参数)注入; None=不注入
    =R2前行为逐位一致。评分=逻辑回归sigmoid, 权重/阈值来自校准配置。
    """

    threshold: float
    subject_bind_weight: float
    predicate_hit_weight: float
    id_block_weight: float
    proximity_weight: float
    intercept: float
    predicate_glue: tuple[str, ...]

    @classmethod
    def from_config(cls, config: IdentifierGroundingConfig
                    ) -> IdentifierGroundingJudge:
        """从规则资产构建(E7挂点: 校准产物在JSON/内置回退双侧)."""
        return cls(
            threshold=config.threshold,
            subject_bind_weight=config.subject_bind_weight,
            predicate_hit_weight=config.predicate_hit_weight,
            id_block_weight=config.id_block_weight,
            proximity_weight=config.proximity_weight,
            intercept=config.intercept,
            predicate_glue=config.predicate_glue,
        )

    def grounding_probability(self, request: QAInput, claim: AnswerClaim,
                              subject_suffix: re.Pattern[str],
                              ) -> tuple[float, GroundingFeatures]:
        """P(绑定|在场, context) ∈ (0,1) 与特征明细(可审计)."""
        features = extract_grounding_features(
            request, claim, subject_suffix, self.predicate_glue)
        return self.score(features), features

    def score(self, features: GroundingFeatures) -> float:
        linear = (
            self.subject_bind_weight * features.subject_bind_ratio
            + self.predicate_hit_weight * features.predicate_hit_ratio
            + self.id_block_weight * features.id_block_ratio
            + self.proximity_weight * features.subject_id_proximity
            + self.intercept)
        return 1.0 / (1.0 + math.exp(-linear))


__all__ = [
    "GroundingFeatures",
    "IdentifierGroundingConfig",
    "IdentifierGroundingJudge",
    "answer_assertion_context",
    "compact",
    "evidence_binding_segments",
    "extract_grounding_features",
]
