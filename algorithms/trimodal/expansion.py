"""关系约束的上下文扩展: 白名单关系图 + ExpandScore + MMR (§7).

文档依据:
  §7.1 Top-K只是anchor证据, 需在严格预算内扩展邻域(BRIT子图思想)
  §7.2 关系白名单7类: same_source/entity/event, time_overlap/near,
       generated_from(强桥), describes, contains/belongs_to
  §7.3 ExpandScore = η1·retrieval_score + η2·relation_confidence
       + η3·temporal_overlap + η4·semantic_similarity
       - η5·redundancy(v, selected); 1-hop为主(高置信才2-hop);
       MMR/预算子模选择保多样
  §7.4 ContextPackage: 证据+跨模态链接+溯源; 不把embedding当prompt拼

下游渲染(§7.4): 纯文本LLM→图像转caption/OCR、时序转摘要+统计;
时序证据的summary/stats由调用方在item.metadata里预置.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from .retrieval import HybridRetriever
from .schemas import (ContextPackage, Evidence, Modality, MultimodalItem,
                      RelationType)

# §7.2 扩展白名单(1-hop优先; generated_from/describes为强桥高优先)
_EXPAND_WHITELIST = {
    RelationType.SAME_EVENT,
    RelationType.GENERATED_FROM,
    RelationType.DESCRIBES,
    RelationType.SAME_ENTITY,
    RelationType.SAME_SOURCE,
    RelationType.TIME_OVERLAP,
    RelationType.TIME_NEAR,
    RelationType.CONTAINS,
    RelationType.BELONGS_TO,
}
_STRONG_REL = {RelationType.SAME_EVENT, RelationType.GENERATED_FROM,
               RelationType.DESCRIBES}


def _time_overlap(a: tuple[float, float] | None,
                  b: tuple[float, float] | None) -> float:
    """时间重叠度[0,1]: 交叠时长/min(时长); 无时间信息返回0."""
    if a is None or b is None:
        return 0.0
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if hi <= lo:
        return 0.0
    denom = min(a[1] - a[0], b[1] - b[0])
    return (hi - lo) / denom if denom > 0 else 0.0


def _semantic_sim(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None or len(a) == 0 or len(b) == 0:
        return 0.0
    na = np.asarray(a, dtype=np.float32)
    nb = np.asarray(b, dtype=np.float32)
    na = na / max(np.linalg.norm(na), 1e-8)
    nb = nb / max(np.linalg.norm(nb), 1e-8)
    return float(na @ nb)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.asarray(a, dtype=np.float32)
    nb = np.asarray(b, dtype=np.float32)
    na = na / max(np.linalg.norm(na), 1e-8)
    nb = nb / max(np.linalg.norm(nb), 1e-8)
    return float(na @ nb)


class ContextExpander:
    """从Top-K anchor沿白名单关系做受控扩展 + 预算内MMR选择."""

    def __init__(self, retriever: HybridRetriever,
                 eta: dict[str, float] | None = None,
                 max_hop: int = 1, expansion_budget: int = 12,
                 mmr_lambda: float = 0.7) -> None:
        self.retriever = retriever
        # §7.3 ExpandScore权重(缺省为文档建议形态)
        self.eta = eta or {"retrieval": 1.0, "relation": 0.8,
                           "temporal": 0.5, "semantic": 0.4,
                           "redundancy": 0.6}
        self.max_hop = max_hop
        self.budget = expansion_budget
        self.mmr_lambda = mmr_lambda

    def expand(self, anchors: list[tuple[MultimodalItem, dict[str, float]]],
               query: str = "") -> list[tuple[MultimodalItem, dict[str, Any]]]:
        """anchors(Top-K) → 扩展候选(含关系路径) → MMR选择到预算."""
        # ① 邻域收集(白名单, ≤max_hop; 2-hop仅强关系)
        cand: dict[str, dict[str, Any]] = {}
        for item, info in anchors:
            cand[item.item_id] = {"item": item, "score": info.get("fused", 0.0),
                                  "path": [], "from_anchor": item.item_id,
                                  "rel_conf": 1.0}
        for item, info in anchors:
            frontier = [(item, 1.0, [])]
            for hop in range(1, self.max_hop + 1):
                nxt: list[tuple[MultimodalItem, float, list[str]]] = []
                for cur, carry, path in frontier:
                    for rel in cur.relations:
                        if rel.type not in _EXPAND_WHITELIST:
                            continue
                        if hop == 2 and rel.type not in _STRONG_REL:
                            continue  # 2-hop只走强关系
                        tgt = self.retriever.items.get(rel.target_id)
                        if tgt is None:
                            continue
                        new_path = path + [f"{cur.item_id}"
                                           f"--{rel.type.value}-->"
                                           f"{tgt.item_id}"]
                        if tgt.item_id not in cand:
                            cand[tgt.item_id] = {
                                "item": tgt, "score": 0.0,
                                "path": new_path,
                                "from_anchor": item.item_id,
                                "rel_conf": rel.confidence * carry}
                        nxt.append((tgt, rel.confidence * carry, new_path))
                frontier = nxt
        # ② ExpandScore打分
        scored: list[tuple[str, float]] = []
        for iid, rec in cand.items():
            it = rec["item"]
            anchor = self.retriever.items.get(rec["from_anchor"])
            anchor_score = rec["score"]
            t_ov = _time_overlap(
                anchor.time_span if anchor else None, it.time_span)
            sem = _semantic_sim(
                anchor.shared_embedding if anchor else None,
                it.shared_embedding)
            e = self.eta
            s = (e["retrieval"] * anchor_score
                 + e["relation"] * rec["rel_conf"]
                 + e["temporal"] * t_ov
                 + e["semantic"] * sem)
            rec["expand_score"] = round(float(s), 4)
            rec["temporal_overlap"] = round(t_ov, 3)
            scored.append((iid, float(s)))
        # ③ MMR预算选择(η5·redundancy的显式化: 最大边际相关)
        scored.sort(key=lambda x: -x[1])
        selected: list[str] = [anchors[0][0].item_id] if anchors else []
        pool = [iid for iid, _ in scored if iid not in selected]
        while pool and len(selected) < self.budget:
            best, best_val = None, -1e9
            for iid in pool:
                rel_s = next(s for i, s in scored if i == iid)
                red = max((_cosine(
                    cand[iid]["item"].shared_embedding,
                    cand[s2]["item"].shared_embedding)
                    for s2 in selected), default=0.0) if len(
                    cand[iid]["item"].shared_embedding) else 0.0
                mmr = self.mmr_lambda * rel_s - (1 - self.mmr_lambda) * red
                if mmr > best_val:
                    best, best_val = iid, mmr
            if best is None:
                break
            selected.append(best)
            pool.remove(best)
        return [(cand[i]["item"], cand[i]) for i in selected]


def _render_evidence(item: MultimodalItem) -> Evidence:
    """§7.4 模态感知渲染: 纯文本LLM可消费的证据形态."""
    md = item.metadata or {}
    if item.modality == Modality.TEXT:
        content = md.get("content", "") or md.get("text", "")
    elif item.modality == Modality.IMAGE:
        parts = [md.get("caption", ""), md.get("ocr", "")]
        content = " | ".join(p for p in parts if p)
    else:
        parts = [md.get("summary", ""),
                 f"统计: {md.get('stats', '')}" if md.get("stats") else "",
                 f"异常点: {md.get('anomaly_points', '')}"
                 if md.get("anomaly_points") else ""]
        content = " | ".join(p for p in parts if p)
    return Evidence(type=item.modality.value, item_id=item.item_id,
                    content=content[:400], source=item.source_id,
                    time_span=item.time_span, payload_ref=item.payload_ref)


def build_context_package(query_id: str, query: str,
                          expanded: list[tuple[MultimodalItem,
                                               dict[str, Any]]],
                          stats: dict[str, Any] | None = None
                          ) -> ContextPackage:
    """扩展结果 → ContextPackage(§7.4): 证据+跨模态链接+溯源."""
    evidences = [_render_evidence(it) for it, _ in expanded]
    for ev, (_, rec) in zip(evidences, expanded):
        ev.score = rec.get("expand_score", 0.0)
        ev.relation_path = rec.get("path", [])
    # 跨模态链接: 同event_id的异模态证据对
    links: list[dict[str, Any]] = []
    by_event: dict[str, list[Evidence]] = defaultdict(list)
    for it, _ in expanded:
        if it.event_id:
            by_event[it.event_id].append(_render_evidence(it))
    for ev_id, evs in by_event.items():
        mods = sorted({e.type for e in evs})
        if len(mods) > 1:
            links.append({"event_id": ev_id, "modalities": mods,
                          "item_ids": [e.item_id for e in evs]})
    by_mod: dict[str, int] = defaultdict(int)
    for it, _ in expanded:
        by_mod[it.modality.value] += 1
    return ContextPackage(
        query_id=query_id,
        evidences=evidences,
        cross_modal_links=links,
        provenance={"query": query[:80], "n_evidences": len(evidences),
                    "by_modality": dict(by_mod),
                    "relation_paths": [r.get("path", [])
                                       for _, r in expanded if r.get("path")]},
        stats=stats or {"n_expanded": len(expanded)})
