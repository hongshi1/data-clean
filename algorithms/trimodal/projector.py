"""三模态投影头: modality-specific两层MLP + L2归一化 (§5.2).

文档依据:
  §5.2 第一版用 modality-specific two-layer MLP, 不用Transformer
       (先验证"既有unimodal表征可否被简单变换对齐" — Freeze-Align设定)
  §5.2 消融: Linear vs 2层MLP; shared projector vs modality-specific
  §5.5 所有shared embedding统一L2归一化; 温度τ固定/分阶段
  §9.1 冻结优势: native特征可预计算, 训练时只过projector

实现: torch(nn.Module); 接口与numpy双轨(训练用torch, 推理可numpy).
零初始化门控(Flamingo思想)作为可选项 — 小数据安全阀.
"""
from __future__ import annotations

from typing import Any

import numpy as np

try:  # torch在训练路径才必需; schema/检索路径可无torch
    import torch
    from torch import nn
    _HAS_TORCH = True
except ImportError:  # pragma: no cover
    _HAS_TORCH = False

_MODALITIES = ("text", "image", "timeseries")


def _build_head(in_dim: int, shared_dim: int, gated: bool) -> Any:
    """单模态头: Linear→LN→GELU→Linear(+可选零初始化线性桥)→L2.

    桥 = 零初始化Linear(in→shared): 训练中可学"输入直通共享空间"
    的线性捷径, MLP承担残差修正 — 兼得Linear projector的表达力
    (§5.2消融A1的隐式对照)与渐进稳定(Flamingo零初始化思想).
    """
    layers: list[Any] = [
        nn.Linear(in_dim, shared_dim),
        nn.LayerNorm(shared_dim),
        nn.GELU(),
        nn.Linear(shared_dim, shared_dim),
    ]
    if not gated:
        return nn.Sequential(*layers)
    bridge = nn.Linear(in_dim, shared_dim)
    nn.init.zeros_(bridge.weight)
    nn.init.zeros_(bridge.bias)

    class _Bridged(nn.Module):
        def __init__(self, body: Any, bridge: Any) -> None:
            super().__init__()
            self.body = body
            self.bridge = bridge

        def forward(self, x: Any) -> Any:
            return self.body(x) + self.bridge(x)

    return _Bridged(nn.Sequential(*layers), bridge)


class TriModalProjector:
    """模态投影头集合: native_dims给哪些模态就建哪些头(支持双模态).

    用法(训练, torch):
        proj = TriModalProjector({"text":1024,"image":768}, 512)  # 双模态
        z = proj.forward_torch({"text": h_t, "image": h_i})
    用法(推理, numpy):
        z = proj.forward_numpy("text", np.array([...]))
    """

    def __init__(self, native_dims: dict[str, int], shared_dim: int = 512,
                 gated: bool = True, seed: int = 42) -> None:
        if not _HAS_TORCH:
            raise RuntimeError("TriModalProjector训练路径需要torch")
        unknown = [m for m in native_dims if m not in _MODALITIES]
        if unknown:
            raise ValueError(f"未知模态: {unknown}(可选: {_MODALITIES})")
        if len(native_dims) < 2:
            raise ValueError("至少需要两个模态才能对齐")
        self.native_dims = dict(native_dims)
        self.shared_dim = shared_dim
        self.seed = seed
        torch.manual_seed(seed)
        self._heads = nn.ModuleDict({
            m: _build_head(d, shared_dim, gated)
            for m, d in native_dims.items()})

    # ── 训练路径 ─────────────────────────────────────────
    def parameters(self) -> Any:
        return self._heads.parameters()

    def forward_torch(self, batch: dict[str, Any]) -> dict[str, Any]:
        """{modality: tensor(N, native_dim)} → {modality: z(N, d) L2归一}."""
        out: dict[str, Any] = {}
        for m, h in batch.items():
            if m not in self._heads:
                raise KeyError(f"未初始化的模态: {m}(已建: {list(self._heads)})")
            z = self._heads[m](h)
            out[m] = nn.functional.normalize(z, dim=-1)
        return out

    # ── 推理/落盘路径 ────────────────────────────────────
    def forward_numpy(self, modality: str, h: np.ndarray) -> np.ndarray:
        """单模态推理(底座特征→共享向量), 不需要梯度图."""
        if modality not in self._heads:
            raise KeyError(f"未初始化的模态: {modality}(已建: {list(self._heads)})")
        with torch.no_grad():
            t = torch.as_tensor(np.asarray(h, dtype=np.float32))
            if t.ndim == 1:
                t = t.unsqueeze(0)
            z = self.forward_torch({modality: t})[modality]
            return z.cpu().numpy().squeeze(0) if h.ndim == 1 else z.cpu().numpy()

    def state(self) -> dict[str, Any]:
        """序列化(磁盘缓存/复现)."""
        return {"native_dims": self.native_dims,
                "shared_dim": self.shared_dim, "seed": self.seed,
                "weights": {m: self._heads[m].state_dict()
                            for m in self._heads}}

    def load_state(self, st: dict[str, Any]) -> None:
        self.native_dims = st["native_dims"]
        self.shared_dim = st["shared_dim"]
        for m in self.native_dims:
            if m not in self._heads:
                self._heads[m] = _build_head(self.native_dims[m],
                                             self.shared_dim, True)
            self._heads[m].load_state_dict(st["weights"][m])
