"""模态感知混合检索: 路由 + 双路索引 + 校准融合 + RRF + 重排钩子 (§6).

文档依据:
  §6.2 Router输出多标签权重(modality×granularity), 非硬标签;
       先规则式/LLM训练-free, 稳定后再训分类器
  §6.3 双路打分: w_m(q)·[α·Calib(S_shared)+β·Calib(S_native)+γ·Calib(S_lex)]
       + relation_prior; 原始cosine不可跨索引直接相加→必须校准
  §6.4 每目标模态Top-K_m(50~100) → item_id去重 → RRF(无训练基线)
       → cross-modal rerank → 最终Top-K(10~20)
  §3.3 shared+native双表示多索引融合是推荐主方案(单索引=baseline)
  §10 统一分数不可比→"某模态长期霸占Top-K"→校准+路由加权

实现: 原型级numpy暴力cosine(可升级FAISS); 校准=每索引z-score.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from .schemas import Granularity, Modality, MultimodalItem


@dataclass(slots=True)
class RouterDecision:
    """§6.2 路由决策: 模态权重+粒度权重(多标签, 非硬选择)."""

    modality_weights: dict[str, float] = field(
        default_factory=lambda: {"text": 1.0, "image": 1.0,
                                 "timeseries": 1.0})
    granularity_weights: dict[str, float] = field(default_factory=dict)
    reason: str = "default"


class ModalityRouter:
    """规则式训练-free路由器(§6.2第一版).

    规则: ①query自身模态权重1.0; ②关键词信号加权(可扩展);
    ③granularity偏好(如时间词→ts_short_window).
    升级路径: 换LLM意图分类或小分类器(接口不变).
    """

    KW_SIGNALS: dict[str, tuple[str, ...]] = {
        "image": ("图", "曲线", "截图", "画面", "界面", "图示", "plot"),
        "timeseries": ("趋势", "参数", "时段", "变化", "窗口", "采样",
                       "时序", "飞参", "转速", "压力", "温度"),
        "text": ("描述", "说明", "记录", "工单", "报告", "原因", "处置"),
    }

    def route(self, query: str, query_modality: Modality | None = None,
              hint: dict[str, Any] | None = None) -> RouterDecision:
        w = {"text": 0.5, "image": 0.5, "timeseries": 0.5}
        if query_modality is not None:
            w[query_modality.value] = 1.0
        for mod, kws in self.KW_SIGNALS.items():
            if any(k in query for k in kws):
                w[mod] = min(1.0, w[mod] + 0.5)
        gran: dict[str, float] = {}
        if any(k in query for k in self.KW_SIGNALS["timeseries"]):
            gran[Granularity.TS_SHORT_WINDOW.value] = 0.9
            gran[Granularity.TS_LONG_WINDOW.value] = 0.4
        return RouterDecision(modality_weights=w, granularity_weights=gran,
                              reason="rule+vocab")


def _cos_matrix(q: np.ndarray, mat: np.ndarray) -> np.ndarray:
    qn = q / max(np.linalg.norm(q), 1e-8)
    mn = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
    return mn @ qn


def _zscore(scores: np.ndarray) -> np.ndarray:
    """§6.3 score calibration: 每索引z-score(跨索引可融合)."""
    s = np.asarray(scores, dtype=np.float64)
    if s.size == 0:
        return s
    std = s.std()
    return (s - s.mean()) / std if std > 1e-8 else np.zeros_like(s)


class HybridRetriever:
    """双路多索引检索+融合(§6.3-6.4).

    存储: items(dict) + 每模态的shared/native两个矩阵索引;
    查询: 任意模态query(native+shared双向量) → 路由 → 各索引Top-K_m
    → 校准融合/RRF → rerank钩子 → Top-K.
    """

    def __init__(self, items: list[MultimodalItem],
                 top_k_per_index: int = 100) -> None:
        self.items = {it.item_id: it for it in items}
        self.top_k_per_index = top_k_per_index
        self._idx: dict[str, dict[str, list[str]]] = {
            "shared": defaultdict(list), "native": defaultdict(list)}
        self._mats: dict[str, dict[str, np.ndarray]] = {
            "shared": {}, "native": {}}
        for it in items:
            if it.native_embedding:
                self._idx["native"][it.modality.value].append(it.item_id)
            if it.shared_embedding:
                self._idx["shared"][it.modality.value].append(it.item_id)
        for space in ("shared", "native"):
            for mod, ids in self._idx[space].items():
                if ids:
                    key = "native_embedding" if space == "native" \
                        else "shared_embedding"
                    self._mats[space][mod] = np.stack(
                        [np.asarray(self.items[i].__getattribute__(key),
                                    dtype=np.float32) for i in ids])

    def _search_space(self, space: str, mod: str, qvec: np.ndarray
                      ) -> list[tuple[str, float]]:
        ids = self._idx[space].get(mod, [])
        if not ids or qvec is None or len(qvec) == 0:
            return []
        mat = self._mats[space][mod]
        sims = _cos_matrix(np.asarray(qvec, dtype=np.float32), mat)
        k = min(self.top_k_per_index, len(ids))
        top = np.argsort(-sims)[:k]
        return [(ids[i], float(sims[i])) for i in top]

    def retrieve(self, query: str = "",
                 query_modality: Modality | None = None,
                 q_native: np.ndarray | None = None,
                 q_shared: np.ndarray | None = None,
                 router: ModalityRouter | None = None,
                 decision: RouterDecision | None = None,
                 alpha: float = 0.6, beta: float = 0.4,
                 final_k: int = 20,
                 reranker: Callable[[str, list[MultimodalItem]],
                                    list[float]] | None = None,
                 ) -> list[tuple[MultimodalItem, dict[str, float]]]:
        """完整检索流水线: 路由→双路Top-K_m→校准加权融合→(可选)rerank."""
        dec = decision or (router or ModalityRouter()).route(
            query, query_modality)
        # 每模态收集双路分数
        per_item: dict[str, dict[str, float]] = defaultdict(dict)
        for mod, w in dec.modality_weights.items():
            if w <= 0:
                continue
            if q_shared is not None and len(q_shared):
                for iid, s in self._search_space("shared", mod, q_shared):
                    per_item[iid]["shared"] = s
            if q_native is not None and len(q_native) \
                    and query_modality is not None \
                    and mod == query_modality.value:
                # native路只在query同模态索引上有意义(§6.3 S_native)
                for iid, s in self._search_space("native", mod, q_native):
                    per_item[iid]["native"] = s
        if not per_item:
            return []
        # 校准+加权融合(§6.3公式)
        shared_raw = {i: d.get("shared", 0.0) for i, d in per_item.items()}
        native_raw = {i: d.get("native", 0.0) for i, d in per_item.items()}
        ids_list = list(per_item)
        zs_shared = dict(zip(
            ids_list, _zscore([shared_raw[i] for i in ids_list])))
        zs_native = dict(zip(
            ids_list, _zscore([native_raw[i] for i in ids_list])))
        fused: list[tuple[str, float]] = []
        for iid in ids_list:
            w_mod = dec.modality_weights.get(
                self.items[iid].modality.value, 0.5)
            s = w_mod * (alpha * zs_shared[iid] + beta * zs_native[iid])
            fused.append((iid, s))
        fused.sort(key=lambda x: -x[1])
        ranked = fused[:max(final_k * 2, 30)]
        # rerank钩子(§6.5: 只对Top-30调贵模型)
        if reranker is not None and ranked:
            cands = [self.items[i] for i, _ in ranked[:30]]
            scores = reranker(query, cands)
            ranked = sorted(zip(ranked, scores), key=lambda x: -x[1])
            ranked = [(i, s) for (i, _), s in ranked]
        out: list[tuple[MultimodalItem, dict[str, float]]] = []
        for iid, s in ranked[:final_k]:
            d = dict(per_item[iid])
            d["fused"] = round(float(s), 4)
            out.append((self.items[iid], d))
        return out

    def rrf_baseline(self, q_shared: np.ndarray | None,
                     final_k: int = 20, k_rrf: int = 60
                     ) -> list[tuple[MultimodalItem, dict[str, float]]]:
        """§6.4 RRF无训练基线(全部模态shared空间, 等权)."""
        scores: dict[str, float] = defaultdict(float)
        hits: dict[str, dict[str, float]] = defaultdict(dict)
        for mod in ("text", "image", "timeseries"):
            for rank, (iid, s) in enumerate(
                    self._search_space("shared", mod, q_shared), 1):
                scores[iid] += 1.0 / (k_rrf + rank)
                hits[iid]["shared"] = s
        ranked = sorted(scores.items(), key=lambda x: -x[1])[:final_k]
        return [(self.items[i], dict(hits[i], fused=round(s, 6)))
                for i, s in ranked]
