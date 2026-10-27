"""三模态对齐与混合召回框架 (依据2026-09-16技术调研与方案设计v1.0).

子模块:
  schemas.py     数据模型(MultimodalItem双表示/关系白名单/ContextPackage)
  projector.py   三模态MLP投影头(L2归一/零初始化门控)
  contrastive.py 三对对称InfoNCE训练(加权pair/课程/难负例)
  retrieval.py   模态路由+双路索引+校准融合+RRF基线+重排钩子
  expansion.py   白名单关系图扩展+ExpandScore+MMR+ContextPackage
"""
from .contrastive import TrainConfig, TrimodalContrastiveTrainer
from .expansion import ContextExpander, build_context_package
from .projector import TriModalProjector
from .retrieval import HybridRetriever, ModalityRouter, RouterDecision
from .schemas import (ContextPackage, Evidence, Granularity, Modality,
                      MultimodalItem, PairSample, Relation, RelationType)

__all__ = [
    "MultimodalItem", "PairSample", "Relation", "RelationType", "Modality",
    "Granularity", "Evidence", "ContextPackage",
    "TriModalProjector", "TrainConfig", "TrimodalContrastiveTrainer",
    "HybridRetriever", "ModalityRouter", "RouterDecision",
    "ContextExpander", "build_context_package",
]
