"""召回融合层升级: A5·θ校准加权RRF + A1·查询自适应注意力融合.

替代HybridRecaller静态cascade席位(lexical直通+structural/multimodal
固定席位+等权RRF填充)的两档融合策略:

  A5 rrf_weighted            通道静态权重θ(CALIBRATED_WEIGHTS, 来自
                             M3/M21校准资产) → score(d)=Σ_c θ_c/(k+rank_c)
  A1 ChannelAttentionFusion  查询条件化α(查询特征+通道覆盖度→5维权重)
                             → score(d)=Σ_c α_c·rr_c(d)

通道分数口径(两档统一): 倒数秩 rr_c(d)=1/(k+rank_c(d)), 未召回=0 —
lexical/structural/multimodal的通道内原始分是平点数(1.0/0.9/0.85)
不携带序信息, 秩是通道间唯一可比的通用信号.

设计规范(与hybrid_recall/reranker一致):
  - 融合层纯函数: 只消费通道ChannelResult, 不触发任何检索
  - 模块顶层零I/O: torch在方法内惰性import
  - 确定性: 权重常量/固定seed/排序平分按chunk_id字典序
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from .hybrid_recall import CHANNELS
from .prose_compiler import ID_PAT

# 来源: M3/M21已有校准资产快照(银标agreement/单通道评测/模态唯一性),
# 写死为常量 —— 零训练成本且可复现; 与attention(A1)的静态先验对照.
CALIBRATED_WEIGHTS: dict[str, float] = {
    "lexical": 0.95,     # M3银标agreement最高: 完整子串命中≈事实
    "sparse": 0.70,      # BM25部分命中: 词频可靠但无语义泛化
    "dense": 0.55,       # M21单通道评测R@20=0.476: BGE域偏移(五通道最低)
    "structural": 0.80,  # ID-Graph硬桥: mention章节完整性高
    "multimodal": 0.85,  # VLM key_elements: figure模态唯一来源(不可替代)
    "unit": 0.85,        # 结构单元多向量: image结构内容/表深行唯一语义级
                         # 来源(对齐multimodal"模态唯一来源"定位;
                         # heuristic先验, 待单通道校准复跑后替换)
}

_FIG_TAB_PAT = re.compile(r"[图表]\s*\d")
_Z_CLIP = 3.0            # z-score截断(单活跃通道σ=0时未召回值会爆炸)
_SCORE_SCALE = 100.0     # 倒数秩O(1/k)≈0.016: 训练logits×100稳定softmax


def _channel_hits(res: Any) -> Sequence[Any]:
    """通道结果→hits序列: ChannelResult(.hits)或裸hits列表, 其余报错."""
    if isinstance(res, (list, tuple)):
        return res
    hits = getattr(res, "hits", None)
    if hits is None:
        raise TypeError(f"非法通道结果类型{type(res)!r}(需ChannelResult或hits列表)")
    return hits


def rrf_weighted(
    channel_results: Mapping[str, Any],
    k_rrf: int = 60,
    weights: Mapping[str, float] = CALIBRATED_WEIGHTS,
    top_k: int = 20,
    keep_factual: bool = False,
    meta_fn: Callable[[str], dict[str, Any] | None] | None = None,
) -> list[dict[str, Any]]:
    """A5·θ校准加权RRF: score(d) = Σ_c w_c/(k_rrf + rank_c(d)).

    channel_results: {channel: ChannelResult|hits列表}(HybridRecaller
        五通道产物, duck-typed: hit需含chunk_id/score属性).
    weights: 通道权重(传{c:1.0}即标准等权RRF, 消融对照用).
    keep_factual: True时lexical完整子串命中(score≥1.0)先顺序直通
        (镜像cascade Tier1的词法层; structural/multimodal席位由
        θ校准权重接管), 剩余配额由加权RRF填充.
    meta_fn: chunk_id→{section,type,doc,snippet}富化函数; 返回None则
        丢弃该候选(与HybridRecaller._hit_dict同语义).
    返回: 与HybridRecaller.recall()["hits"]同schema的列表(排序确定性:
        融合分降序, 平分按chunk_id字典序).
    """
    scores: dict[str, float] = defaultdict(float)
    hit_channels: dict[str, list[str]] = defaultdict(list)
    for ch, res in channel_results.items():
        w = float(weights.get(ch, 1.0))
        for rank, h in enumerate(_channel_hits(res), 1):
            scores[h.chunk_id] += w / (k_rrf + rank)
            if ch not in hit_channels[h.chunk_id]:
                hit_channels[h.chunk_id].append(ch)

    def _emit(cid: str, score: float, tier: str) -> dict[str, Any] | None:
        d: dict[str, Any] = {"chunk_id": cid, "rrf_score": round(score, 6),
                             "tier": tier, "channels": list(hit_channels[cid]),
                             "rank": 0}
        if meta_fn is not None:
            meta = meta_fn(cid)
            if meta is None:
                return None
            d.update(meta)
        return d

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    if keep_factual and "lexical" in channel_results:
        for h in _channel_hits(channel_results["lexical"]):
            if len(out) >= top_k:
                break
            if h.score < 1.0 or h.chunk_id in seen:
                continue
            d = _emit(h.chunk_id, scores[h.chunk_id], "factual")
            if d is None:
                continue
            seen.add(h.chunk_id)
            d["rank"] = len(out) + 1
            out.append(d)
    for cid, s in sorted(scores.items(), key=lambda x: (-x[1], x[0])):
        if len(out) >= top_k:
            break
        if cid in seen:
            continue
        d = _emit(cid, s, "rrf")
        if d is None:
            continue
        seen.add(cid)
        d["rank"] = len(out) + 1
        out.append(d)
    return out


def query_features(query: str) -> np.ndarray:
    """查询特征q(3维): [实体性, 含图/表号, 含ID].

    实体性 = 长度因子(12字饱和)×CJK字密度: 自然语言实体→接近1,
    ID型查询→0(由第3维接管). 图/表号与ID为0/1指示(A1的路由信号).
    """
    q = (query or "").strip()
    chars = [c for c in q if not c.isspace()]
    n = len(chars)
    cjk = sum(1 for c in chars if "\u4e00" <= c <= "\u9fff")
    entity_ness = min(n / 12.0, 1.0) * (cjk / n if n else 0.0)
    fig_tab = 1.0 if _FIG_TAB_PAT.search(q) else 0.0
    has_id = 1.0 if ID_PAT.search(q) else 0.0
    return np.array([entity_ness, fig_tab, has_id], dtype=float)


def zscore_channels(rr: np.ndarray | Sequence[Sequence[float]]) -> np.ndarray:
    """候选×通道倒数秩的z-score(A1的候选特征s).

    μ_c/σ_c在通道c的活跃候选(rr>0)上估计; 未召回候选经(0-μ_c)映射为
    低于活跃集的负值, 全空通道z=0, 单活跃通道σ=0(活跃z=0/其余clip).
    在全池上统计会使z均值恒0(mean_pool无信号), 故用活跃集统计 —
    mean_pool(z)携带"该通道覆盖了候选池多大比例"的信息.
    """
    rr = np.asarray(rr, dtype=float)
    z = np.zeros_like(rr)
    if rr.ndim != 2:
        return z
    for c in range(rr.shape[1]):
        col = rr[:, c]
        act = col > 0
        mu = float(col[act].mean()) if act.any() else 0.0
        sd = float(col[act].std()) if act.sum() >= 2 else 0.0
        z[:, c] = np.clip((col - mu) / (sd + 1e-6), -_Z_CLIP, _Z_CLIP)
    return z


class ChannelAttentionFusion:
    """A1·查询自适应注意力融合: 查询特征→通道权重α→加权融合.

    查询特征q(3维, query_features): [实体性, 含图/表号, 含ID]
    候选特征s(5维, zscore_channels): 候选在五通道的归一化倒数秩
    注意力: α = softmax(MLP([q; mean_pool(s)])) ∈ R^5
    融合: score(d) = Σ_c α_c·rr_c(d)  (查询自适应版加权RRF)

    训练: listwise softmax CE — 期望chunk的融合分应靠前, α被推向
    "命中期望chunk的通道". torch小MLP(8→d_hidden→5, 默认229参数<1K),
    CPU全批量, seed确定性; torch在方法内惰性import(顶层零I/O).
    """

    def __init__(self, d_hidden: int = 16, seed: int = 42,
                 n_channels: int | None = None) -> None:
        self.d_hidden = d_hidden
        self.seed = seed
        self.n_query_feat = 3
        self.n_channels = int(n_channels) if n_channels else len(CHANNELS)
        self.fitted = False
        self.loss_history: list[float] = []
        self.n_params = ((self.n_query_feat + self.n_channels) * d_hidden
                         + d_hidden + d_hidden * self.n_channels
                         + self.n_channels)
        self._params: dict[str, Any] | None = None
        self._np: dict[str, np.ndarray] | None = None

    # ── 内部: 惰性torch权重 ─────────────────────────────────

    def _ensure_params(self) -> dict[str, Any]:
        """权重初始化(seed确定性; torch缺失时ImportError显式抛出)."""
        if self._params is not None:
            return self._params
        import torch
        g = torch.Generator().manual_seed(self.seed)
        n_in = self.n_query_feat + self.n_channels
        params = {
            "W1": torch.randn(n_in, self.d_hidden, generator=g) / (n_in ** 0.5),
            "b1": torch.zeros(self.d_hidden),
            "W2": torch.randn(self.d_hidden, self.n_channels, generator=g)
                  / (self.d_hidden ** 0.5),
            "b2": torch.zeros(self.n_channels),
        }
        for p in params.values():
            p.requires_grad_(True)
        self._params = params
        return params

    def _forward_t(self, x: Any) -> Any:
        import torch
        p = self._params
        h = torch.tanh(x @ p["W1"] + p["b1"])
        return torch.softmax(h @ p["W2"] + p["b2"], dim=-1)

    def _qvec(self, q: str | Sequence[float]) -> np.ndarray:
        if isinstance(q, str):
            return query_features(q)
        v = np.asarray(q, dtype=float).reshape(-1)
        if v.shape[0] != self.n_query_feat:
            raise ValueError(f"查询特征须为{self.n_query_feat}维, 得到{v.shape[0]}维")
        return v

    # ── 对外API ─────────────────────────────────────────────

    def fit(
        self,
        train_queries: Sequence[str | Sequence[float]],
        channel_hit_matrix: tuple[Sequence[np.ndarray], Sequence[np.ndarray]],
        epochs: int = 200,
        lr: float = 0.01,
    ) -> list[float]:
        """训练α网络: 期望chunk在某通道命中→该通道得分高→α应放大它.

        train_queries: 查询串(内部query_features提特征)或3维特征序列.
        channel_hit_matrix: (scores, labels)二元组 —
            scores[i]: (m_i, 5)第i查询的候选×通道倒数秩矩阵(未召回=0);
            labels[i]: (m_i,)期望chunk二值标签(1=金标chunk).
        损失: listwise softmax CE(候选池内期望chunk的融合分应靠前).
        每次fit重置权重(同seed同初始化, 重复fit可复现); 返回逐epoch损失.
        """
        if self._params is not None:
            self._params = None      # 重复fit重置(确定性)
        scores, labels = channel_hit_matrix
        if len(train_queries) != len(scores) or len(scores) != len(labels):
            raise ValueError("train_queries/scores/labels长度不一致")
        if epochs <= 0:
            raise ValueError(f"epochs须为正数, 得到{epochs}")
        feats: list[np.ndarray] = []
        rows: list[np.ndarray] = []
        labs: list[np.ndarray] = []
        for q, sc, lb in zip(train_queries, scores, labels):
            sc = np.atleast_2d(np.asarray(sc, dtype=float))
            lb = np.asarray(lb, dtype=float).reshape(-1)
            if sc.ndim != 2 or sc.shape[1] != self.n_channels:
                raise ValueError(f"通道分数须为(m, {self.n_channels})矩阵, "
                                 f"得到{sc.shape}")
            if sc.shape[0] != lb.shape[0]:
                raise ValueError(f"候选行数{sc.shape[0]}与标签数{lb.shape[0]}不一致")
            z = zscore_channels(sc)
            zmean = z.mean(axis=0) if z.shape[0] else np.zeros(self.n_channels)
            feats.append(np.concatenate([self._qvec(q), zmean]))
            rows.append(sc)
            labs.append(lb)
        if not rows:
            raise ValueError("训练集为空")
        m_max = max(r.shape[0] for r in rows)
        if m_max == 0:
            raise ValueError("训练集候选池全部为空")
        if not any(lab.sum() > 0 for lab in labs):
            raise ValueError("训练集无正例(期望chunk均不在任何通道候选池)")
        n = len(rows)
        rr = np.zeros((n, m_max, self.n_channels))
        lb = np.zeros((n, m_max))
        mk = np.zeros((n, m_max), dtype=bool)
        for i, (r, lab) in enumerate(zip(rows, labs)):
            rr[i, :r.shape[0]] = r
            lb[i, :lab.shape[0]] = lab
            mk[i, :lab.shape[0]] = True
        import torch
        p = self._ensure_params()
        t_x = torch.tensor(np.stack(feats), dtype=torch.float32)
        t_rr = torch.tensor(rr, dtype=torch.float32)
        t_lb = torch.tensor(lb, dtype=torch.float32)
        t_mk = torch.tensor(mk)
        has_pos = t_lb.sum(dim=1) > 0
        opt = torch.optim.Adam(list(p.values()), lr=lr)
        self.loss_history = []
        for _ in range(epochs):
            opt.zero_grad()
            alpha = self._forward_t(t_x)
            fused = torch.einsum("nmc,nc->nm", t_rr, alpha) * _SCORE_SCALE
            fused = fused.masked_fill(~t_mk, -1e9)
            logp = torch.log_softmax(fused, dim=1)
            pos = t_lb * t_mk
            n_pos = pos.sum(dim=1).clamp(min=1.0)
            per_q = -(pos * logp).sum(dim=1) / n_pos
            loss = per_q[has_pos].mean()
            loss.backward()
            opt.step()
            self.loss_history.append(float(loss.item()))
        self.fitted = True
        self._np = {k: v.detach().cpu().numpy() for k, v in p.items()}
        return self.loss_history

    def fuse(
        self,
        query_features: str | Sequence[float],
        channel_scores: np.ndarray | Sequence[Sequence[float]],
    ) -> dict[str, Any]:
        """查询自适应融合.

        query_features: 查询串或3维特征向量; channel_scores: (m, 5)
        候选×通道倒数秩矩阵(与fit同口径, 未召回=0).
        返回 {"alpha": {channel: α_c}(4位小数),
              "ranked": [(候选行号, 融合分), ...]融合分降序,
              平分按输入行序(稳定排序, 确定性)}.
        """
        if not self.fitted or self._np is None:
            raise RuntimeError("ChannelAttentionFusion未经fit即fuse(权重未训练)")
        sc = np.atleast_2d(np.asarray(channel_scores, dtype=float))
        if sc.ndim != 2 or sc.shape[1] != self.n_channels:
            raise ValueError(f"通道分数须为(m, {self.n_channels})矩阵, 得到{sc.shape}")
        q = self._qvec(query_features)
        if sc.shape[0] == 0:
            return {"alpha": {}, "ranked": []}
        z = zscore_channels(sc)
        x = np.concatenate([q, z.mean(axis=0)])
        w1 = self._np["W1"]
        b1 = self._np["b1"]
        w2 = self._np["W2"]
        b2 = self._np["b2"]
        h = np.tanh(x @ w1 + b1)
        logits = h @ w2 + b2
        e = np.exp(logits - logits.max())
        alpha = e / e.sum()
        fused = sc @ alpha
        order = np.argsort(-fused, kind="stable")
        return {
            "alpha": {ch: round(float(a), 4) for ch, a in zip(CHANNELS, alpha)},
            "ranked": [(int(i), float(fused[i])) for i in order],
        }
