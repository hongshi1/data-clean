"""单元聚焦两阶段精排(交叉验证).

勘验对应: 粗勘(召回)后对top物证做交叉比对审讯 —
  doc = 表内与查询最相关的top-2单元(单元聚焦, 全表dump已被证伪-17pt)
  最终分 = rerank分 + 0.1×标准化召回分(融合, GJB深行+6.5pt标定)

精排器经Reranker协议注入(默认BgeReranker惰性加载;
不可用时直通召回序并标注head="passthrough").
"""
from __future__ import annotations

from typing import Protocol

import numpy as np

from .evidence import EvidenceHit, EvidenceStore
from .recall import RecallResult


class Reranker(Protocol):
    """精排器协议: (query, doc)对→分数."""

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        ...


class PassthroughReranker:
    """直通精排器(不可用环境/测试): 返回全零分=保持召回序."""

    name = "passthrough"

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        return [0.0] * len(pairs)


class UnitFocusedRerank:
    """两阶段精排: top-k召回→cross-encoder单元聚焦重排."""

    def __init__(self, reranker: Reranker | None = None,
                 unit_topn: int = 2, blend: float = 0.1,
                 batch: int = 16) -> None:
        self._reranker = reranker
        self._unit_topn = unit_topn
        self._blend = blend
        self._batch = batch

    def rerank(self, query: str, result: RecallResult,
               store: EvidenceStore) -> list[EvidenceHit]:
        """对召回结果精排, 返回重排后的证据列表."""
        hits = result.hits
        if not hits:
            return hits
        rr = self._reranker or PassthroughReranker()
        head = getattr(rr, "name", "cross_encoder")
        docs = [" ; ".join(h.best_units)[:2000] for h in hits]
        pairs = [(query, d) for d in docs]
        scores: list[float] = []
        for b0 in range(0, len(pairs), self._batch):
            scores.extend(rr.score(pairs[b0:b0 + self._batch]))
        if head == "passthrough":
            return [EvidenceHit(owner=h.owner, kind=h.kind, title=h.title,
                                score=h.score, head=h.head,
                                best_units=h.best_units)
                    for h in hits]
        # 融合: rerank分 + blend×标准化召回分
        base = np.asarray([h.score for h in hits], dtype=np.float32)
        bmin, bmax = float(base.min()), float(base.max())
        brng = max(bmax - bmin, 1e-8)
        base_n = (base - bmin) / brng
        r = np.asarray(scores, dtype=np.float32)
        rmin, rmax = float(r.min()), float(r.max())
        rrng = max(rmax - rmin, 1e-8)
        comb = r + self._blend * (base_n / rrng) * abs(rmax)
        order = sorted(range(len(hits)), key=lambda j: (-float(comb[j]), j))
        return [EvidenceHit(owner=hits[j].owner, kind=hits[j].kind,
                            title=hits[j].title,
                            score=float(comb[j]), head=head,
                            best_units=hits[j].best_units)
                for j in order]
