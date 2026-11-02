"""证据召回端到端管线(勘验流程总控).

  query → 冻结骨干 → 多头召回(场景路由) → 单元聚焦精排 → 排序证据

真实环境默认: BgeLocal编码器(algorithms/common) + BgeReranker精排器
(context_linking/blackboard, 均惰性); 测试环境: 注入确定性
FakeEncoder/FakeReranker + auto_reranker=False.

用法:
    from algorithms.context_linking.evidence_recall import (
        EvidenceRecallPipeline)
    pipe = EvidenceRecallPipeline(corpus)   # corpus=已加载的URE列表
    hits = pipe.search("接口数据一览表中GJB 438B的编写单位", topk=10)
"""
from __future__ import annotations

import sys

from .evidence import EvidenceHit, EvidenceStore
from .heads import Encoder
from .recall import MultiHeadRecall
from .rerank import Reranker, UnitFocusedRerank


def _default_encoder() -> Encoder:
    """真实编码器: BgeLocal惰性加载(模块顶层零I/O)."""
    from srs_verify.context import bge_local
    bge = bge_local.BgeLocal(cache_path=None)
    bge.ensure()
    return bge


def _default_reranker() -> Reranker | None:
    """真实精排器: BGE-Reranker-v2-m3, 不可用时返回None(直通)."""
    try:
        from srs_verify.context.reranker_stub import BgeReranker
        rr = BgeReranker()
        rr.ensure()
        return rr
    except (OSError, RuntimeError, ValueError):
        return None


class EvidenceRecallPipeline:
    """端到端证据检索管线(全部组件冻结/惰性).

    auto_reranker=False: 不加载真实精排器(召回序直通, 测试/轻量环境).
    """

    def __init__(self, corpus: list[dict],
                 encoder: Encoder | None = None,
                 reranker: Reranker | None = None,
                 topk_recall: int = 50,
                 auto_reranker: bool = True) -> None:
        self.store = EvidenceStore.from_ure(corpus)
        self._encoder = encoder
        self._reranker = reranker
        self._auto_reranker = auto_reranker
        self._topk_recall = topk_recall
        self._recall: MultiHeadRecall | None = None

    def _ensure_recall(self) -> MultiHeadRecall:
        if self._recall is None:
            enc = self._encoder
            if enc is None:
                enc = _default_encoder()
            self._recall = MultiHeadRecall(self.store, enc)
        return self._recall

    def search(self, query: str, pool: str = "table", topk: int = 10,
               rerank: bool = True) -> list[EvidenceHit]:
        """检索: 返回排序证据(含头来源与命中单元)."""
        rc = self._ensure_recall()
        result = rc.recall(query, pool=pool, topk=self._topk_recall)
        if not rerank:
            return result.hits[:topk]
        rr = self._reranker
        if rr is None and self._auto_reranker:
            rr = _default_reranker()
        stage2 = UnitFocusedRerank(reranker=rr)
        return stage2.rerank(query, result, self.store)[:topk]


if sys.version_info < (3, 12):
    raise RuntimeError("evidence_recall需要Python 3.12+")
