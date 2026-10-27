"""多头召回(场景路由+多通道).

勘验对应: 不同物证类型路由到不同显影头 —
  table池→语义单元头主导(S6实证: O1 0.365 vs BM25 0.183)
  image池→词面头主导(S4实证: BM25 0.685 vs O1 0.583)

融合策略: 默认场景路由; 可选zscore-max融合(ROUTE式, 已证不外推,
仅作鲁棒降级选项).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .evidence import EvidenceHit, EvidenceStore
from .heads import Encoder, LexicalHead, SemanticUnitHead

# 场景路由表(来源: 统一评测S4/S6实证, 见docs/srs_project/30)
SCENE_ROUTE: dict[str, list[str]] = {
    "table": ["semantic_unit"],
    "image": ["lexical", "semantic_unit"],
}


@dataclass
class RecallResult:
    """一次召回的完整结果."""

    hits: list[EvidenceHit]
    scores: dict[str, np.ndarray]   # 头名→owner分数向量
    owner_order: list[str]


def _zscore(x: np.ndarray) -> np.ndarray:
    sd = float(x.std())
    return (x - x.mean()) / (sd if sd > 1e-8 else 1.0)


class MultiHeadRecall:
    """多头并行评分+场景路由召回."""

    def __init__(self, store: EvidenceStore, encoder: Encoder,
                 heads: str = "default") -> None:
        self._store = store
        self._semantic = SemanticUnitHead(encoder).build(store)
        self._lexical = LexicalHead().build(store)
        self._head_for = {
            "semantic_unit": self._semantic,
            "lexical": self._lexical,
        }

    def score_all(self, query: str,
                  pool: str) -> tuple[dict[str, np.ndarray], np.ndarray]:
        """多头打分(原始分)+池掩码(池内True). 融合后统一施加掩码
        (先zscore后掩码, 避免-inf污染统计量)."""
        owners = self._store.pool(
            "image_element" if pool == "image" else "table_row")
        keep = np.zeros(self._store.n_owners, dtype=bool)
        for o in owners:
            keep[self._store.owners.index(o)] = True
        out = {}
        for name, head in self._head_for.items():
            s = head.score_query(query) if name == "semantic_unit" \
                else head.score(query)
            out[name] = np.asarray(s, dtype=np.float32)
        return out, keep

    def recall(self, query: str, pool: str = "table", topk: int = 50,
               fusion: str = "route") -> RecallResult:
        """召回top-k证据(默认场景路由)."""
        raw, keep = self.score_all(query, pool)
        route = SCENE_ROUTE.get(pool, ["semantic_unit"])
        if fusion == "zmax":
            fused = None
            for s in raw.values():
                zs = np.zeros_like(s)
                if keep.any():
                    zs[keep] = _zscore(s[keep])
                    zs[~keep] = float(zs[keep].min()) - 1.0
                fused = zs if fused is None else np.maximum(fused, zs)
        else:
            fused = None
            for name in route:
                s = raw.get(name)
                if s is None:
                    continue
                fused = s.copy() if fused is None else np.maximum(fused, s)
            if fused is None:
                fused = next(iter(raw.values())).copy()
        fused = np.where(keep, fused, -np.inf).astype(np.float32)
        # 头来源标注: 命中时哪个路由头给了最高分
        best_head = {}
        for name in route:
            s = raw.get(name)
            if s is None:
                continue
            for i in np.argsort(-np.where(keep, s, -np.inf))[:topk * 2]:
                if fused[i] > -np.inf and i not in best_head:
                    best_head[i] = name
        order = np.argsort(-fused)[:topk]
        hits: list[EvidenceHit] = []
        for i in order:
            if fused[i] == -np.inf:
                continue
            owner = self._store.owners[int(i)]
            top_units = tuple(
                self._semantic.top_units(query, owner, topn=2))
            hits.append(EvidenceHit(
                owner=owner, kind=self._store.owner_kinds.get(owner, ""),
                title=self._store.owner_titles.get(owner, ""),
                score=float(fused[i]), head=best_head.get(int(i), route[0]),
                best_units=top_units))
        return RecallResult(hits=hits, scores=raw,
                            owner_order=self._store.owners)
