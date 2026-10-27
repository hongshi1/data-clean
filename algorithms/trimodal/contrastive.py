"""三模态对比对齐训练器: 三对对称InfoNCE + 加权pair + 课程 + 难负例.

文档依据:
  §5.3 L_total = λ_ti·L(text,image) + λ_ts·L(text,ts) + λ_is·L(image,ts);
       每对双向对称InfoNCE(温度τ); 第一版λ全1, 之后按指标调节
  §4.2 加权对比损失: pair带confidence(强1.0/弱0.4-0.8/桥接);
       避免把"共现"等价"语义等价"(装饰图假阳性污染)
  §4.3 难负例: batch负例+同实体错时间/同趋势不同语义/同主题错证据
  §5.5 课程式训练: 先Image↔Text/TS↔Image, 再提TS↔Text权重
  §9.1 预计算native特征: 训练只过projector, 大batch友好
  §9.3 超参起点: lr 1e-4~1e-3, τ 0.03~0.1, 有效batch≥256

训练协议: 每个epoch按pair_type分组采样batch, 组内对称InfoNCE
(同模态锚的batch内其他b侧样本即负例 — 文档§4.3 Batch negatives),
可注入显式hard negative(同实体错时间等)到batch.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except ImportError:  # pragma: no cover
    _HAS_TORCH = False

from .projector import TriModalProjector
from .schemas import PairSample

_MODAL_OF = {"text": "text", "image": "image", "ts": "timeseries",
             "timeseries": "timeseries"}
_ALL_PAIR_KEYS = ("text-image", "text-timeseries", "image-timeseries")


@dataclass(slots=True)
class TrainConfig:
    """§9.3 第一版超参起点(验证集为准)."""

    shared_dim: int = 512
    lr: float = 1e-4
    temperature: float = 0.07
    batch_size: int = 64            # 每pair_type的组内batch(梯度累积提有效值)
    epochs: int = 40
    seed: int = 42
    # §5.5 课程: pair权重(缺省1; text-timeseries按进度0.5→1线性提权)
    curriculum: dict[str, float] = field(default_factory=dict)
    log_every: int = 10


def _info_nce_sym(z_a: Any, z_b: Any, tau: float,
                  weights: Any = None) -> Any:
    """双向对称InfoNCE(带样本权重). 返回标量loss."""
    sim = z_a @ z_b.t() / tau                       # (N, N)
    n = z_a.shape[0]
    labels = torch.arange(n, device=sim.device)
    l_ab = F.cross_entropy(sim, labels, reduction="none")
    l_ba = F.cross_entropy(sim.t(), labels, reduction="none")
    if weights is not None:
        w = weights / weights.sum().clamp_min(1e-8)
        return (w * 0.5 * (l_ab + l_ba)).sum()
    return 0.5 * (l_ab.mean() + l_ba.mean())


class TrimodalContrastiveTrainer:
    """预计算native特征上的三对对比训练.

    输入不跑编码器(§9.1): features={item_id: np.ndarray(native_dim)},
    pairs=[PairSample...]; 训练后projector可forward_numpy产出shared向量.
    """

    def __init__(self, native_dims: dict[str, int],
                 cfg: TrainConfig | None = None) -> None:
        if not _HAS_TORCH:
            raise RuntimeError("训练需要torch")
        self.cfg = cfg or TrainConfig()
        self.projector = TriModalProjector(
            native_dims, self.cfg.shared_dim, gated=True, seed=self.cfg.seed)
        # 合法pair_type = 已配置模态的两两组合(支持双模态子集)
        mods = sorted(self.projector.native_dims)
        self.pair_keys = {
            f"{a}-{b}" if f"{a}-{b}" in _ALL_PAIR_KEYS else f"{b}-{a}"
            for i, a in enumerate(mods) for b in mods[i + 1:]}
        self._optim = torch.optim.AdamW(
            self.projector.parameters(), lr=self.cfg.lr)
        self.rng = random.Random(self.cfg.seed)
        self.history: list[dict[str, float]] = []

    def _modality_of(self, item_id: str, modality_map: dict[str, str]) -> str:
        m = modality_map[item_id]
        return m if m in ("text", "image", "timeseries") else _MODAL_OF.get(
            m, m)

    def _pair_key(self, a_mod: str, b_mod: str) -> str:
        mods = {a_mod, b_mod}
        if mods == {"text", "image"}:
            return "text-image"
        if mods == {"text", "timeseries"}:
            return "text-timeseries"
        if mods == {"image", "timeseries"}:
            return "image-timeseries"
        return ""

    def train(self, features: dict[str, np.ndarray],
              modality_map: dict[str, str],
              pairs: list[PairSample],
              hard_negative_ids: dict[str, list[str]] | None = None
              ) -> list[dict[str, float]]:
        """训练主循环: epoch × pair_type分组batch.

        hard_negative_ids: {pair_key: [item_id...]} 显式难负例池
        (§4.3 同实体错时间等), 按比例混入batch.
        """
        hard_negative_ids = hard_negative_ids or {}
        by_type: dict[str, list[PairSample]] = defaultdict(list)
        for p in pairs:
            key = p.pair_type
            if key not in self.pair_keys:
                raise ValueError(
                    f"pair_type {key} 不在已配置模态组合内: "
                    f"{sorted(self.pair_keys)}")
            by_type[key].append(p)
        ids = list(features)
        tensors = {i: torch.as_tensor(np.asarray(features[i], dtype=np.float32))
                   for i in ids}

        for epoch in range(self.cfg.epochs):
            # §5.5 课程权重: 缺省1.0; text-timeseries按进度0.5→1提权
            prog = epoch / max(self.cfg.epochs - 1, 1)
            w_cur = {}
            for key in self.pair_keys:
                base = self.cfg.curriculum.get(key, 1.0)
                if key == "text-timeseries":
                    base = base * (0.5 + 0.5 * prog)
                w_cur[key] = base
            epoch_log: dict[str, float] = {"epoch": epoch}
            self._optim.zero_grad()
            for key, samples in by_type.items():
                if not samples:
                    continue
                self.rng.shuffle(samples)
                a_mod, b_mod = key.split("-")
                b_mod = "timeseries" if b_mod == "timeseries" else b_mod
                for i in range(0, len(samples), self.cfg.batch_size):
                    batch = samples[i:i + self.cfg.batch_size]
                    a_ids = [p.a_id for p in batch]
                    b_ids = [p.b_id for p in batch]
                    w = torch.as_tensor(
                        [p.confidence for p in batch], dtype=torch.float32)
                    # 显式难负例混入(§4.3): 从池取同b侧模态样本附加
                    pool = [x for x in hard_negative_ids.get(key, [])
                            if x in tensors and x not in b_ids]
                    if pool and len(pool) >= 2:
                        extra = self.rng.sample(pool, min(len(pool),
                                                           self.cfg.batch_size))
                        b_ids = b_ids + extra
                        w = torch.cat([w, torch.zeros(len(extra))])
                    za = [tensors[x] for x in a_ids]
                    zb = [tensors[x] for x in b_ids]
                    # 锚侧数量与b侧不对齐时截齐(对称矩阵需N×N)
                    n = min(len(za), len(zb))
                    batch_tensors = {
                        a_mod: torch.stack(za[:n]),
                        b_mod: torch.stack(zb[:n]),
                    }
                    z = self.projector.forward_torch(batch_tensors)
                    loss = w_cur[key] * _info_nce_sym(
                        z[a_mod], z[b_mod], self.cfg.temperature,
                        w[:n])
                    loss.backward()
                    epoch_log[key] = epoch_log.get(key, 0.0) + float(
                        loss.detach())
            self._optim.step()
            self.history.append(epoch_log)
        return self.history

    def encode_all(self, features: dict[str, np.ndarray],
                   modality_map: dict[str, str]) -> dict[str, np.ndarray]:
        """训练后批量产出shared embedding(§4.1的shared_embedding槽)."""
        out: dict[str, np.ndarray] = {}
        by_mod: dict[str, list[str]] = defaultdict(list)
        for iid, m in modality_map.items():
            if iid in features:
                by_mod[m if m in ("text", "image", "timeseries")
                       else _MODAL_OF.get(m, m)].append(iid)
        for m, ids in by_mod.items():
            mat = np.stack([np.asarray(features[i], dtype=np.float32)
                            for i in ids])
            z = self.projector.forward_numpy(m, mat)
            for iid, vec in zip(ids, z):
                out[iid] = vec
        return out
