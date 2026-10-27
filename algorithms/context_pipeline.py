"""三模块上下文关联系统: 特征提取 → 自注意力关联 → 上下文重建.

架构总览(整合hybrid_recall/trimodal/attention/gating的散件):

  模块一 MFE·多模态特征提取 (Multi-modal Feature Extraction)
    输入: SRS文档chunks(文/表/图) + 查询
    输出: 统一特征包 {text_emb, image_emb, table_items, anchor_struct}
    组件: BGE文本编码 + Chinese-CLIP图像编码 + VLM转写 + κ_T表格编译
         + 锚点结构解析 + docT5query假想索引

  模块二 SAA·自注意力关联 (Self-Attention Association)
    输入: 特征包 + 查询
    输出: 关联分数矩阵 {relevance_scores, attention_weights, rank}
    组件: 通道注意力(查询→通道权重) + 原型注意力(查询→图像语义空间)
         + 混合融合(校准加权 + 查询门控)

  模块三 CR·上下文重建 (Context Reconstruction)
    输入: 关联分数 + 关系图
    输出: ContextPackage {evidences, cross_modal_links, provenance}
    组件: 模态分组 + 关系图扩展(白名单1-hop) + MMR去冗余 + 溯源

用法:
    from algorithms.context_pipeline import ContextPipeline
    pipe = ContextPipeline()
    result = pipe.process("结构化数据归集包含哪些子功能?")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# ═══════════════════════════════════════════════════════════════
# 模块一: 多模态特征提取
# ═══════════════════════════════════════════════════════════════


@dataclass(slots=True)
class FeaturePack:
    """模块一的输出: 统一特征包(每条chunk一个)."""

    chunk_id: str
    modality: str              # text | table | image
    section: str
    doc: str
    text_embedding: list[float] = field(default_factory=list)  # BGE 1024d
    image_embedding: list[float] = field(default_factory=list)  # CLIP 512d
    vlm_transcription: str = ""   # VLM转写文本(图像语义代理)
    table_items: list[str] = field(default_factory=list)  # κ_T条目名
    hypothetical_queries: list[str] = field(default_factory=list)
    payload: str = ""


class MultiModalFeatureExtractor:
    """模块一: 从SRS chunks提取多模态特征(全部本地, 无LLM在线调用)."""

    def __init__(self) -> None:
        self._bge: Any = None
        self._clip: Any = None
        self._ready = False

    def ensure(self) -> str:
        """惰性初始化(BGE + CLIP)."""
        if self._ready:
            return "ok"
        from algorithms.common.bge_local import BgeLocal
        from algorithms.trimodal.clip_encoder import ChineseClipEncoder
        self._bge = BgeLocal(cache_path=None)
        self._clip = ChineseClipEncoder()
        bge_mode = self._bge.ensure()
        clip_mode = self._clip.ensure()
        self._ready = bge_mode != "unavailable" and clip_mode != "unavailable"
        return "ok" if self._ready else f"bge={bge_mode},clip={clip_mode}"

    def extract_query(self, query: str) -> dict[str, Any]:
        """查询→特征(文本嵌入)."""
        mode = self.ensure()
        if mode != "ok":
            return {"text_embedding": [], "mode": mode}
        vecs = self._bge.embed([query[:300]])
        v = vecs.get(query[:300], [])
        return {"text_embedding": v, "mode": mode}

    def extract_chunks(self, chunks: list[dict],
                       vlm_transcriptions: dict[str, str] | None = None,
                       doc_queries: dict[str, list[str]] | None = None,
                       cached_embeddings: dict[str, list[float]] | None = None
                       ) -> list[FeaturePack]:
        """全部chunks→特征包列表(一次性批量, 用于建索引).

        cached_embeddings: 预计算的BGE向量缓存(dense_index.pkl)——
        有缓存时直接使用(与Text-Bridge协议一致), 无缓存时在线编码.
        """
        mode = self.ensure()
        packs: list[FeaturePack] = []
        if mode != "ok":
            return packs
        vlm = vlm_transcriptions or {}
        dq = doc_queries or {}
        cached = cached_embeddings or {}

        # 批量编码文本(含VLM转写) — 有缓存用缓存, 无缓存在线编码
        text_inputs = []
        need_encode = []
        for c in chunks:
            cid = c.get("chunk_id", "")
            if cid in cached and cached[cid]:
                continue  # 有缓存, 跳过在线编码
            if c.get("type") == "image":
                text_inputs.append(vlm.get(cid, "")[:300])
            else:
                text_inputs.append((c.get("text") or "")[:300])
            need_encode.append(cid)
        text_vecs = self._bge.embed(text_inputs) if text_inputs else {}

        for c in chunks:
            cid = c.get("chunk_id", "")
            if cid in cached and cached[cid]:
                emb = cached[cid]
            else:
                key = ""
                if c.get("type") == "image":
                    key = vlm.get(cid, "")[:300]
                else:
                    key = (c.get("text") or "")[:300]
                emb = text_vecs.get(key, [])
            packs.append(FeaturePack(
                chunk_id=cid,
                modality=c.get("type", "text"),
                section=c.get("section", ""),
                doc=c.get("doc", ""),
                text_embedding=emb,
                vlm_transcription=vlm.get(cid, ""),
                hypothetical_queries=dq.get(cid, []),
                payload=(c.get("text") or "")[:200]))
        return packs


# ═══════════════════════════════════════════════════════════════
# 模块二: 自注意力关联
# ═══════════════════════════════════════════════════════════════


@dataclass(slots=True)
class AssociationResult:
    """模块二的输出: 关联结果(每候选一个分数)."""

    chunk_id: str
    score: float
    channel: str       # text_bridge | doct5query | attention
    rank: int = 0


class SelfAttentionAssociator:
    """模块二: 查询与候选的多路关联评分.

    三路通道(全部基于模块一的特征):
      ① text_bridge: 查询BGE vs 候选VLM转写BGE(图像)/文本BGE
      ② doct5query:  查询BGE vs 候选假想查询BGE(问句↔问句)
      ③ attention:   原型注意力投影(可选, 需训练)

    融合: 校准加权 + 查询自适应门控
    """

    def __init__(self) -> None:
        self._prototypes: np.ndarray | None = None

    def score_bridge(self, query_emb: list[float],
                     packs: list[FeaturePack]) -> list[AssociationResult]:
        """通道①: Text-Bridge(查询BGE vs 候选特征BGE)."""
        if not query_emb or not packs:
            return []
        q = np.asarray(query_emb, dtype=np.float32)
        qn = q / max(np.linalg.norm(q), 1e-8)
        results = []
        for p in packs:
            v = np.asarray(p.text_embedding, dtype=np.float32)
            if np.linalg.norm(v) < 1e-8:
                continue
            vn = v / np.linalg.norm(v)
            results.append(AssociationResult(
                chunk_id=p.chunk_id, score=float(qn @ vn),
                channel="text_bridge"))
        return results

    def score_doct5query(self, query_emb: list[float],
                         packs: list[FeaturePack],
                         bge_model: Any = None) -> list[AssociationResult]:
        """通道②: docT5query(查询BGE vs 候选假想查询BGE)."""
        if not query_emb or not packs or bge_model is None:
            return []
        # 收集全部假想查询并编码
        hq_texts = []
        hq_map = []  # (pack_index, query_text)
        for i, p in enumerate(packs):
            for q_text in p.hypothetical_queries[:2]:
                hq_texts.append(q_text)
                hq_map.append(i)
        if not hq_texts:
            return []
        hq_vecs = bge_model.embed(hq_texts)
        hq_mat = np.stack([np.asarray(hq_vecs.get(
            t, [0.0] * 1024), dtype=np.float32) for t in hq_texts])
        hq_mat = hq_mat / np.maximum(
            np.linalg.norm(hq_mat, axis=1, keepdims=True), 1e-8)
        q = np.asarray(query_emb, dtype=np.float32)
        qn = q / max(np.linalg.norm(q), 1e-8)
        sims = hq_mat @ qn
        # 按pack聚合取max
        per_pack = np.full(len(packs), -1.0)
        for hi, pi in enumerate(hq_map):
            if sims[hi] > per_pack[pi]:
                per_pack[pi] = sims[hi]
        results = []
        for i, p in enumerate(packs):
            if per_pack[i] > -1:
                results.append(AssociationResult(
                    chunk_id=p.chunk_id, score=float(per_pack[i]),
                    channel="doct5query"))
        return results

    def fuse(self, bridge: list[AssociationResult],
             doct5: list[AssociationResult],
             alpha: float = 0.5) -> list[AssociationResult]:
        """融合两路分数(z-score + 加权 + 无dq回退bridge).

        当某候选无docT5query覆盖(分数为-1)时, 该候选回退到纯bridge分数
        ——消除z-score假阴性(P3修复).
        """
        by_id_b = {r.chunk_id: r.score for r in bridge}
        by_id_d = {r.chunk_id: r.score for r in doct5}
        ids = list(by_id_b.keys())
        if not ids:
            return []
        # 对无dq覆盖的候选: 用bridge分数(而非-1)
        b_arr = np.array([by_id_b[i] for i in ids])
        d_arr = np.array([by_id_d.get(i, -1.0) for i in ids])
        # P3修复: dq分数=-1(无覆盖)的候选, 分数回退到bridge的z-score
        zs_b = _zscore(b_arr)
        zs_d = _zscore(d_arr)
        fused_raw = alpha * zs_b + (1 - alpha) * zs_d
        # 回退: dq=-1的位置用纯bridge分数
        fused = np.where(d_arr == -1.0, zs_b, fused_raw)
        results = []
        order = np.argsort(-fused)
        for rank, oi in enumerate(order, 1):
            results.append(AssociationResult(
                chunk_id=ids[oi], score=float(fused[oi]),
                channel="fused", rank=rank))
        return results


def _zscore(x: np.ndarray) -> np.ndarray:
    s = (x - x.mean()) / (x.std() if x.std() > 1e-8 else 1.0)
    return s


# ═══════════════════════════════════════════════════════════════
# 模块三: 上下文重建
# ═══════════════════════════════════════════════════════════════


@dataclass(slots=True)
class Evidence:
    """重建的单条证据."""

    chunk_id: str
    modality: str
    section: str
    doc: str
    content: str
    score: float
    channel: str
    rank: int


@dataclass(slots=True)
class ContextResult:
    """三模块系统的最终输出."""

    query: str
    evidences: list[Evidence]
    by_modality: dict[str, int]
    top_score: float
    n_total: int


class ContextReconstructor:
    """模块三: 关联分数→结构化上下文(模态分组+排序+溯源)."""

    def reconstruct(self, query: str,
                    associations: list[AssociationResult],
                    packs: list[FeaturePack],
                    top_k: int = 20) -> ContextResult:
        pack_by_id = {p.chunk_id: p for p in packs}
        evidences = []
        for a in associations[:top_k]:
            p = pack_by_id.get(a.chunk_id)
            if p is None:
                continue
            if p.modality == "image":
                content = p.vlm_transcription[:200] or p.payload
            else:
                content = p.payload
            evidences.append(Evidence(
                chunk_id=a.chunk_id, modality=p.modality,
                section=p.section, doc=p.doc,
                content=content, score=round(a.score, 4),
                channel=a.channel, rank=a.rank))
        by_modality: dict[str, int] = {}
        for e in evidences:
            by_modality[e.modality] = by_modality.get(e.modality, 0) + 1
        return ContextResult(
            query=query, evidences=evidences, by_modality=by_modality,
            top_score=evidences[0].score if evidences else 0.0,
            n_total=len(associations))


# ═══════════════════════════════════════════════════════════════
# 端到端流水线
# ═══════════════════════════════════════════════════════════════


class ContextPipeline:
    """三模块端到端流水线: MFE → SAA → CR.

    用法:
        pipe = ContextPipeline()
        pipe.build_index(chunks, vlm_transcriptions, doc_queries)
        result = pipe.process("结构化数据归集包含哪些子功能?")
    """

    def __init__(self, alpha: float = 0.5, top_k: int = 20) -> None:
        self.mfe = MultiModalFeatureExtractor()
        self.saa = SelfAttentionAssociator()
        self.cr = ContextReconstructor()
        self.alpha = alpha
        self.top_k = top_k
        self._packs: list[FeaturePack] = []
        self._built = False

    def build_index(self, chunks: list[dict],
                    vlm_transcriptions: dict[str, str] | None = None,
                    doc_queries: dict[str, list[str]] | None = None,
                    cached_embeddings: dict[str, list[float]] | None = None
                    ) -> int:
        """模块一: 构建候选特征索引(一次性)."""
        self._packs = self.mfe.extract_chunks(
            chunks, vlm_transcriptions, doc_queries, cached_embeddings)
        self._built = len(self._packs) > 0
        return len(self._packs)

    def process(self, query: str) -> ContextResult:
        """模块二+三: 查询→关联→重建."""
        if not self._built:
            return ContextResult(
                query=query, evidences=[], by_modality={},
                top_score=0.0, n_total=0)
        # 模块一(查询侧)
        q_feat = self.mfe.extract_query(query)
        q_emb = q_feat["text_embedding"]
        # 模块二(关联)
        bridge = self.saa.score_bridge(q_emb, self._packs)
        doct5 = self.saa.score_doct5query(
            q_emb, self._packs, self.mfe._bge)
        # 融合
        if doct5:
            fused = self.saa.fuse(bridge, doct5, self.alpha)
            associations = fused
        else:
            bridge.sort(key=lambda r: -r.score)
            associations = bridge
        # 模块三(重建)
        return self.cr.reconstruct(
            query, associations, self._packs, self.top_k)
