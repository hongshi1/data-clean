"""证据召回框架: 多头冻结投影+召回+精排(勘验叙事, 见docs/srs_project/30).

公开API:
    EvidenceStore / EvidenceUnit / EvidenceHit  — 物证模型
    MultiHeadRecall                             — 多头场景路由召回
    UnitFocusedRerank                           — 单元聚焦两阶段精排
    EvidenceRecallPipeline                      — 端到端管线
"""
from .evidence import EvidenceHit, EvidenceStore, EvidenceUnit
from .heads import (
    DenseHead,
    Encoder,
    LexicalHead,
    QUERY_PREFIX,
    SemanticUnitHead,
    tokenize,
)
from .pipeline import EvidenceRecallPipeline
from .recall import MultiHeadRecall, SCENE_ROUTE
from .rerank import PassthroughReranker, Reranker, UnitFocusedRerank

__all__ = [
    "EvidenceUnit", "EvidenceStore", "EvidenceHit",
    "Encoder", "SemanticUnitHead", "LexicalHead", "DenseHead",
    "QUERY_PREFIX", "tokenize",
    "MultiHeadRecall", "SCENE_ROUTE",
    "Reranker", "PassthroughReranker", "UnitFocusedRerank",
    "EvidenceRecallPipeline",
]
