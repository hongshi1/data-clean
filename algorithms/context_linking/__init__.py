"""上下文关联(方向A)命名空间.

治理边界(docs/srs_project/31_module_governance.md):
  - 本包 = 方向A的唯一规范家: 证据固证→多头召回→精排→[B2]条目聚合
  - 产出"证据/排序/聚合"的算法进此包; 根级平铺A模块为历史存量,
    归位路径: algorithms.context_linking.<module>
  - 禁止import algorithms.consistency(B)

旗舰模块: evidence_recall/(多头冻结投影+召回+精排, 勘验叙事见
docs/srs_project/30); baselines/(复现baseline统一头, 见33).
"""
from .baselines import (
    BASELINE_NAMES,
    make_baseline,
)
from .evidence_recall import (
    DenseHead,
    Encoder,
    EvidenceHit,
    EvidenceRecallPipeline,
    EvidenceStore,
    EvidenceUnit,
    LexicalHead,
    MultiHeadRecall,
    PassthroughReranker,
    QUERY_PREFIX,
    Reranker,
    SCENE_ROUTE,
    SemanticUnitHead,
    tokenize,
    UnitFocusedRerank,
)
from .alignment import ProcrustesMap, StructuralCompatibility, fit_orthogonal_map, structural_score

__all__ = [
    "BASELINE_NAMES", "make_baseline",
    "EvidenceUnit", "EvidenceStore", "EvidenceHit",
    "Encoder", "SemanticUnitHead", "LexicalHead", "DenseHead",
    "QUERY_PREFIX", "tokenize",
    "MultiHeadRecall", "SCENE_ROUTE",
    "Reranker", "PassthroughReranker", "UnitFocusedRerank",
    "EvidenceRecallPipeline",
    "ProcrustesMap", "StructuralCompatibility", "fit_orthogonal_map", "structural_score",
]
