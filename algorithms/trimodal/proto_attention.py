"""蒸馏原型对齐投影头(DPA): Teacher-Student + 可学习语义原型.

三组件(可独立开关, 消融用):
  D1 蒸馏损失: Teacher(Text-Bridge=BGE同空间)的排序分布通过KL
     蒸馏给Student(投影头) — teacher的软排序包含"第二像/完全不像"
     等比0/1标签更丰富的负例结构, 攻小数据瓶颈
  D2 可学习原型codebook: 原型从k-means固定→端到端训练
     (初始化保留k-means, 梯度流过原型)
     +原型语义对齐正则: 每个原型学一个文本概念向量, cos约束
  D3 查询自适应门控(见gating.py): 推理时α(q)动态融合teacher/student

总损失: L = L_InfoNCE + λ₁·L_distill + λ₂·L_proto_align
"""
from __future__ import annotations

from typing import Any

import numpy as np

try:
    import torch
    from torch import nn
    import torch.nn.functional as Fn
    _HAS_TORCH = True
except ImportError:  # pragma: no cover
    _HAS_TORCH = False


def kmeans_prototypes(feat: np.ndarray, k: int = 64, iters: int = 30,
                      seed: int = 42) -> np.ndarray:
    """轻量k-means(手写, 确定性): (N, D)→(k, D)原型."""
    rng = np.random.default_rng(seed)
    x = np.asarray(feat, dtype=np.float32)
    n = x.shape[0]
    k = min(k, n)
    idx = rng.choice(n, size=k, replace=False)
    centers = x[idx].copy()
    for _ in range(iters):
        d = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for j in range(k):
            m = lab == j
            if m.any():
                centers[j] = x[m].mean(0)
    return centers


class ProtoAttentionProjector:
    """蒸馏原型注意力投影头(text+image双模态).

    新增参数:
        use_distill: 训练时是否加蒸馏损失(D1)
        learnable_proto: 原型是否端到端可学习(D2)
        use_proto_align: 是否加原型语义对齐正则(D2)

    fit签名扩展: teacher_scores(dict[qid→np.array候选分数])可选传入
    """

    def __init__(self, native_dims: dict[str, int], prototypes: np.ndarray,
                 shared_dim: int = 256, seed: int = 42,
                 n_heads: int = 4, use_distill: bool = False,
                 learnable_proto: bool = False,
                 use_proto_align: bool = False) -> None:
        if not _HAS_TORCH:
            raise RuntimeError("ProtoAttentionProjector需要torch")
        if set(native_dims) != {"text", "image"}:
            raise ValueError("本投影头为text+image双模态设计")
        self.native_dims = dict(native_dims)
        self.shared_dim = shared_dim
        self.seed = seed
        self.use_distill = use_distill
        self.use_proto_align = use_proto_align
        torch.manual_seed(seed)
        d_model = 128
        self.n_proto = prototypes.shape[0]
        proto_t = torch.as_tensor(
            np.asarray(prototypes, dtype=np.float32))

        class _Head(nn.Module):
            def __init__(self, in_dim: int, proto: Any, d_m: int,
                         n_h: int, out_dim: int,
                         learnable: bool) -> None:
                super().__init__()
                p = proto / proto.norm(dim=-1, keepdim=True).clamp_min(1e-8)
                self.proto = nn.Parameter(p, requires_grad=learnable)
                self.wq = nn.Linear(in_dim, d_m)
                self.wkv = nn.Linear(proto.shape[1], d_m)
                self.attn = nn.MultiheadAttention(d_m, n_h, batch_first=True)
                self.out = nn.Sequential(
                    nn.Linear(in_dim + d_m, out_dim),
                    nn.LayerNorm(out_dim), nn.GELU(),
                    nn.Linear(out_dim, out_dim))

            def forward(self, x: Any) -> Any:
                q = self.wq(x).unsqueeze(1)
                kv = self.wkv(self.proto).unsqueeze(0).expand(
                    x.shape[0], -1, -1)
                a, _ = self.attn(q, kv, kv)
                return self.out(torch.cat([x, a.squeeze(1)], dim=-1))

        self._heads = nn.ModuleDict({
            m: _Head(native_dims[m], proto_t.clone(), d_model, n_heads,
                     shared_dim, learnable_proto)
            for m in ("text", "image")})

        # D2: 原型语义对齐头 — 每个原型学一个文本概念向量
        modules = list(self._heads.children())
        if use_proto_align:
            self._proto_txt = nn.Linear(
                proto_t.shape[1] if learnable_proto else IMG_PROTO_DIM,
                shared_dim)
            modules.append(self._proto_txt)
        self._all = nn.ModuleList(modules)
        # 统一收集所有可训练参数(含proto_txt)
        _params = []
        for m in self._all.children():
            _params.extend(m.parameters())
        # proto_txt already collected via _all (append above)
        self._optim = torch.optim.AdamW(_params, lr=1e-3)
        self.history: list[float] = []
        self.distill_weight = 0.3
        self.proto_align_weight = 0.1

    def parameters(self) -> Any:
        return [p for m in self._all.children()
                for p in m.parameters()] + (
            [self._proto_txt.parameters()] if self.use_proto_align else [])

    def forward_torch(self, batch: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for m, h in batch.items():
            z = self._heads[m](h)
            out[m] = Fn.normalize(z, dim=-1)
        return out

    def forward_numpy(self, modality: str, h: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            t = torch.as_tensor(np.atleast_2d(
                np.asarray(h, dtype=np.float32)))
            z = self.forward_torch({modality: t})[modality]
            z = z.cpu().numpy()
            return z[0] if np.asarray(h).ndim == 1 else z

    def _proto_align_loss(self) -> Any:
        """D2: 原型语义对齐 — image原型的text投影↔text原型对齐."""
        if not self.use_proto_align:
            return torch.tensor(0.0)
        img_proto = self._heads["image"].proto          # (K, D_img)
        txt_proto = self._heads["text"].proto           # (K, D_text)
        pi = Fn.normalize(self._proto_txt(img_proto), dim=-1)
        pt = Fn.normalize(self._proto_txt(txt_proto), dim=-1)
        # 对角余弦(同index原型应对齐)
        return (1 - (pi * pt).sum(-1)).mean()

    def fit(self, text_feats: dict[str, np.ndarray],
            image_feats: dict[str, np.ndarray],
            pairs: list[tuple[str, str]], epochs: int = 60,
            batch_size: int = 48, tau: float = 0.07,
            teacher_scores: dict[str, np.ndarray] | None = None,
            teacher_ids: list[str] | None = None) -> list[float]:
        """对称InfoNCE + 可选蒸馏 + 可选原型对齐.

        teacher_scores: {query_text_id: np.array(len(teacher_ids))}
            — teacher(Text-Bridge)对全部候选的BGE cos分数.
        teacher_ids: 候选image_id列表(与teacher_scores维度对应).
        """
        rng = np.random.default_rng(self.seed)
        t_map = {k: torch.as_tensor(np.asarray(v, dtype=np.float32))
                 for k, v in text_feats.items()}
        i_map = {k: torch.as_tensor(np.asarray(v, dtype=np.float32))
                 for k, v in image_feats.items()}
        teacher_t = None
        if self.use_distill and teacher_scores and teacher_ids:
            teacher_t = {k: torch.as_tensor(np.asarray(v, dtype=np.float32))
                         for k, v in teacher_scores.items()}
        idx = list(range(len(pairs)))
        for ep in range(epochs):
            rng.shuffle(idx)
            ep_loss = 0.0
            for b0 in range(0, len(idx), batch_size):
                chunk = [pairs[i] for i in idx[b0:b0 + batch_size]]
                ht = torch.stack([t_map[a] for a, _ in chunk])
                hi = torch.stack([i_map[b] for _, b in chunk])
                z = self.forward_torch({"text": ht, "image": hi})
                sim = z["text"] @ z["image"].t() / tau
                n = sim.shape[0]
                labels = torch.arange(n)
                loss = 0.5 * (Fn.cross_entropy(sim, labels)
                              + Fn.cross_entropy(sim.t(), labels))
                # D1: 蒸馏 — teacher排序KL(teacher对每个query的
                # 全候选cos→softmax分布 vs student同分布)
                if teacher_t is not None and teacher_ids:
                    for qi, (a, _) in enumerate(chunk):
                        if a in teacher_t and len(teacher_ids) == \
                                sim.shape[1]:
                            t_s = teacher_t[a] / 0.05
                            s_s = sim[qi] / 0.05
                            loss = loss + self.distill_weight * (
                                Fn.kl_div(
                                    Fn.log_softmax(s_s, dim=-1),
                                    Fn.softmax(t_s, dim=-1),
                                    reduction="batchmean"))
                # D2: 原型对齐正则
                if self.use_proto_align:
                    loss = loss + self.proto_align_weight * \
                        self._proto_align_loss()
                self._optim.zero_grad()
                loss.backward()
                self._optim.step()
                ep_loss += float(loss.detach())
            self.history.append(ep_loss / max(1, len(idx) // batch_size))
        return self.history


IMG_PROTO_DIM = 1536  # CLIP(512)+VLM-BGE(1024)拼接维

