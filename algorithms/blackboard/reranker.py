"""BGE-Reranker-v2-m3重排器: 召回候选的精排层(本地GPU, 惰性加载).

角色: hybrid_recall的rerank后处理——召回top-K0 → cross-encoder逐对打分
(query, chunk富化文本) → 重排取top_k. 攻排序质量缺口(R@10=0.770 vs
R@20=0.846: 召回找得到但排序不靠前).

模型: data/models/bge-reranker-v2-m3 (2.27GB, 100+语言, XLM-RoBERTa架构;
  输入(query, passage)对, 输出logits→sigmoid=相关性分)

设计(与bge_local同规范):
  - 模块顶层零I/O: torch/transformers只在ensure()内import
  - eval+no_grad确定性; 失败显式last_error不吞错
  - 图片chunk用caption+VLM key_elements富化文本参与重排(与dense索引
    同一富化策略)
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE / "data/models/bge-reranker-v2-m3"

_BATCH_GPU = 16
_BATCH_CPU = 4
_MAX_LEN = 512


class BgeReranker:
    """Cross-encoder重排器. mode: "unavailable" | "cpu" | "gpu"."""

    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = Path(model_dir or MODEL_DIR)
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {"n_calls": 0, "n_pairs": 0,
                                       "n_batches": 0, "infer_ms": 0.0,
                                       "device": ""}
        self._ready = False
        self._torch: Any = None
        self._tok: Any = None
        self._mdl: Any = None
        self._device = ""

    def ensure(self) -> str:
        """初始化并返回mode. 失败原因在last_error."""
        if self._ready:
            return self.mode
        self._ready = True
        if not (self.model_dir / "config.json").exists():
            self.last_error = f"model not found: {self.model_dir}"
            return self.mode
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as e:
            self.last_error = f"torch/transformers unavailable: {e}"
            return self.mode
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._torch = torch
            self._tok = AutoTokenizer.from_pretrained(str(self.model_dir),
                                                      local_files_only=True)
            self._mdl = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_dir), local_files_only=True)
            self._mdl.to(self._device)
            self._mdl.eval()
        except (OSError, ValueError, RuntimeError) as e:
            self.last_error = f"model load failed({self._device}): {e}"
            return self.mode
        self.mode = self._device
        self.stats["device"] = self._device
        return self.mode

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        """批量打分(query, passage)对 → [0,1]相关性分(逐对独立, 确定性).

        空串输入返回0.5(中性分, 不奖不惩).
        """
        mode = self.ensure()
        self.stats["n_calls"] += 1
        self.stats["n_pairs"] += len(pairs)

        def _neutral() -> float:
            return 0.5

        out: list[float] = [_neutral() for _ in pairs]
        valid: list[tuple[int, tuple[str, str]]] = [
            (i, (q, p)) for i, (q, p) in enumerate(pairs)
            if q.strip() and p.strip()]
        if not valid or mode == "unavailable":
            return out
        batch = _BATCH_GPU if mode == "gpu" else _BATCH_CPU
        t0 = time.time()
        for i in range(0, len(valid), batch):
            chunk = valid[i:i + batch]
            qs = [q for _, (q, _) in chunk]
            ps = [p for _, (_, p) in chunk]
            enc = self._tok(qs, ps, padding=True, truncation="longest_first",
                            max_length=_MAX_LEN, return_tensors="pt")
            enc = {k: v.to(self._device) for k, v in enc.items()}
            with self._torch.no_grad():
                logits = self._mdl(**enc).logits
                probs = self._torch.sigmoid(logits.float()).squeeze(-1)
            for (idx, _), s in zip(chunk, probs.tolist()):
                out[idx] = float(s)
            self.stats["n_batches"] += 1
        self.stats["infer_ms"] += round((time.time() - t0) * 1000, 1)
        return out
