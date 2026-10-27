"""三模态对齐与混合召回框架 — 数据模型层.

依据: 《文本-图像-时序多模态对齐与混合召回_技术调研与方案设计》v1.0
  §4.1 统一数据对象 MultimodalItem (native+shared双表示+关系+粒度)
  §7.4 ContextPackage (证据包: 溯源/关系路径/分数分解)
  §7.2 关系类型白名单 (7类)

设计原则(文档§3.1):
  - 共享空间只负责"可比性", 模态身份保留(§1.2纠正: 不说"投影到同一模态")
  - 双表示: native_embedding(单模态细节) + shared_embedding(跨模态可比)
  - 关系/时间信息与向量同等重要(§4.1)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TIMESERIES = "timeseries"


class RelationType(str, Enum):
    """§7.2 白名单关系(上下文扩展只沿这些边走)."""

    SAME_SOURCE = "same_source"        # 同文档/同数据源
    SAME_ENTITY = "same_entity"        # 同主题(设备/实体/指标)
    SAME_EVENT = "same_event"          # 同一事件(优先级最高的语义扩展)
    TIME_OVERLAP = "time_overlap"      # 时间重叠
    TIME_NEAR = "time_near"            # 时间邻近
    GENERATED_FROM = "generated_from"  # 图像/plot由某时序或数据生成(强桥)
    DESCRIBES = "describes"            # 文本描述某图像/时序/表格
    CONTAINS = "contains"              # 层级从属(段落⊃句子, session⊃窗口)
    BELONGS_TO = "belongs_to"


class Granularity(str, Enum):
    """§4.4 两级粒度(router可输出 modality×granularity 对)."""

    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    SECTION = "section"
    PAGE = "page"
    IMAGE = "image"
    TS_SHORT_WINDOW = "ts_short_window"
    TS_LONG_WINDOW = "ts_long_window"


@dataclass(slots=True)
class Relation:
    """条目间关系边(带置信度, 供扩展打分与加权对比损失使用)."""

    type: RelationType
    target_id: str
    confidence: float = 1.0


@dataclass(slots=True)
class MultimodalItem:
    """§4.1 统一数据对象.

    native_embedding: 冻结编码器的原生表示(单模态细节, 检索兜底)
    shared_embedding: 投影头输出的共享空间表示(跨模态可比)
    relations:        关系邻接(上下文扩展的图结构)
    time_span:        时间位置 [start, end] | None(时序对齐/邻接判定)
    """

    item_id: str
    modality: Modality
    source_id: str
    native_embedding: list[float] = field(default_factory=list)
    shared_embedding: list[float] = field(default_factory=list)
    entity_id: str = ""
    event_id: str = ""
    time_span: tuple[float, float] | None = None
    granularity: Granularity = Granularity.PARAGRAPH
    relations: list[Relation] = field(default_factory=list)
    payload_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_record(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id, "modality": self.modality.value,
            "source_id": self.source_id, "entity_id": self.entity_id,
            "event_id": self.event_id, "granularity": self.granularity.value,
            "time_span": list(self.time_span) if self.time_span else None,
            "payload_ref": self.payload_ref,
            "relations": [{"type": r.type.value, "target_id": r.target_id,
                           "confidence": r.confidence} for r in self.relations],
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class PairSample:
    """§4.2 对比训练样本对: 带relation_type与置信度(加权对比损失).

    pair_type: text-image | text-timeseries | image-timeseries
    level: strong(1.0) / weak(0.4-0.8) / bridge(桥接, 如TS plot↔text)
    """

    pair_type: str
    a_id: str
    b_id: str
    level: str = "strong"
    confidence: float = 1.0
    relation_type: RelationType = RelationType.SAME_EVENT


@dataclass(slots=True)
class RetrievedCandidate:
    """检索候选(融合/重排流水线的中间产物)."""

    item: MultimodalItem
    score: float
    shared_score: float = 0.0
    native_score: float = 0.0
    lexical_score: float = 0.0
    channels: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Evidence:
    """§7.4 ContextPackage内的单条证据(下游LLM/一致性校验消费)."""

    type: str                       # text | image | timeseries
    item_id: str
    content: str = ""               # 文本内容/图像caption+OCR/时序摘要
    source: str = ""
    score: float = 0.0
    relation_path: list[str] = field(default_factory=list)
    time_span: tuple[float, float] | None = None
    payload_ref: str = ""


@dataclass(slots=True)
class ContextPackage:
    """§7.4 最终产出: 证据集合+跨模态链接+全量溯源.

    下游消费注意(文档§7.4): 不把embedding当prompt token拼;
    纯文本LLM→图像转caption/OCR, 时序转摘要+统计量+关键点.
    """

    query_id: str
    evidences: list[Evidence] = field(default_factory=list)
    cross_modal_links: list[dict[str, Any]] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)
