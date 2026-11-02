"""BGE本地embedding客户端: GPU优先, CPU兜底, 磁盘缓存.

模型: models/embedding/bge-large-zh-v1.5 (1024维, CLS池化+L2归一).
向量语义空间与wanqing API embedding不互换 —— 阈值须各自校准
(embedding_channel.EMB_TH vs EMB_TH_LOCAL).

硬规则遵从:
  - 模块顶层零I/O/零重依赖: torch/transformers只在ensure()内import
  - 失败显式记录(last_error), 不静默吞
  - eval模式+no_grad: 向量确定性可复现(同文本→同向量)
"""
from __future__ import annotations

import atexit
import pickle
import time
from pathlib import Path
from typing import Any


BASE = Path.cwd()  # 部署契约: models/与运行目录同级(见README)
DEFAULT_MODEL_DIR = BASE / "models" / "embedding" / "bge-large-zh-v1.5"
DEFAULT_CACHE_PATH = BASE / "data" / "gjb_438c" / "blackboard" / "bge_cache.pkl"

_BATCH_GPU = 64
_BATCH_CPU = 16
_MAX_LEN = 256
_SAVE_EVERY = 512  # 每新增512条向量写盘一次(崩溃损失上限)


class BgeLocal:
    """本地BGE embedding客户端. mode: "unavailable" | "cpu" | "cuda"."""

    def __init__(self, model_dir: Path | None = None,
                 cache_path: Path | None = None,
                 use_cache: bool = True) -> None:
        self.model_dir = Path(model_dir or DEFAULT_MODEL_DIR)
        self.cache_path = Path(cache_path or DEFAULT_CACHE_PATH)
        self.use_cache = use_cache
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {"n_embed_calls": 0, "n_texts": 0,
                                      "n_cache_hits": 0, "n_batches": 0,
                                      "embed_ms": 0.0, "device": "", "dim": 0}
        self._ready = False
        self._dirty_since_save = 0
        self._atexit_registered = False
        self._cache: dict[str, list[float]] = {}
        self._torch: Any = None
        self._tok: Any = None
        self._mdl: Any = None
        self._device = ""

    # ── 惰性初始化 ────────────────────────────────────────
    def ensure(self) -> str:
        """初始化并返回mode ("gpu"|"cpu"|"unavailable"). 失败原因在last_error."""
        if self._ready:
            return self.mode
        self._ready = True
        if not (self.model_dir / "config.json").exists():
            self.last_error = f"model not found: {self.model_dir}"
            return self.mode
        if self.use_cache:
            self._load_cache()
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            self.last_error = f"torch/transformers unavailable: {e}"
            return self.mode
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._torch = torch
            self._tok = AutoTokenizer.from_pretrained(str(self.model_dir),
                                                      local_files_only=True)
            self._mdl = AutoModel.from_pretrained(str(self.model_dir),
                                                  local_files_only=True)
            self._mdl.to(self._device)
            self._mdl.eval()
        except (OSError, ValueError, RuntimeError) as e:
            self.last_error = f"model load failed({self._device}): {e}"
            return self.mode
        self.mode = self._device  # "gpu" | "cpu"
        self.stats["device"] = self._device
        self.stats["dim"] = int(self._mdl.config.hidden_size)
        if not self._atexit_registered:
            atexit.register(self.save)
            self._atexit_registered = True
        return self.mode

    # ── 缓存 ──────────────────────────────────────────────
    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        try:
            with open(self.cache_path, "rb") as f:
                data = pickle.load(f)
            if isinstance(data, dict):
                self._cache = {t: v for t, v in data.items()
                               if isinstance(t, str) and isinstance(v, list)}
        except (pickle.UnpicklingError, EOFError, OSError) as e:
            self.last_error = f"cache unreadable: {e}"
            self._cache = {}

    def save(self) -> None:
        """写盘缓存(atexit自动调用; 也可显式调用)."""
        if not (self.use_cache and self._cache):
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "wb") as f:
            pickle.dump(self._cache, f)
        self._dirty_since_save = 0

    # ── 向量计算 ──────────────────────────────────────────
    def _embed_chunk(self, chunk: list[str]) -> dict[str, list[float]]:
        torch = self._torch
        enc = self._tok(chunk, padding=True, truncation=True,
                        max_length=_MAX_LEN, return_tensors="pt")
        enc = {k: v.to(self._device) for k, v in enc.items()}
        with torch.no_grad():
            h = self._mdl(**enc).last_hidden_state[:, 0]  # CLS池化
            h = torch.nn.functional.normalize(h, dim=-1)  # L2归一
        rows = h.float().cpu().tolist()
        return dict(zip(chunk, rows))

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        """批量embedding(带磁盘缓存). 返回 text→向量(空列表=失败)."""
        mode = self.ensure()
        self.stats["n_embed_calls"] += 1
        out: dict[str, list[float]] = {}
        todo: list[str] = []
        for t in dict.fromkeys(texts):  # 去重保序
            if not t:
                out[t] = []
            elif t in self._cache:
                out[t] = self._cache[t]
                self.stats["n_cache_hits"] += 1
            elif mode != "unavailable":
                todo.append(t)
            else:
                out[t] = []
        if todo:
            batch = _BATCH_GPU if mode == "gpu" else _BATCH_CPU
            t0 = time.time()
            for i in range(0, len(todo), batch):
                fresh = self._embed_chunk(todo[i:i + batch])
                self._cache.update(fresh)
                out.update(fresh)
                self.stats["n_batches"] += 1
            self.stats["embed_ms"] += round((time.time() - t0) * 1000, 1)
            self._dirty_since_save += len(todo)
            if self._dirty_since_save >= _SAVE_EVERY:
                self.save()
        self.stats["n_texts"] += len(texts)
        return out

    def embed_tokens(self, texts: list[str],
                     max_length: int = _MAX_LEN,
                     batch_size: int = 0) -> dict[str, Any]:
        """token级向量(供ColBERT式后期交互对照): {text: (n_tokens,1024)}.

        每文本返回全部非padding token的归一化向量(含CLS, 不池化).
        无磁盘缓存(token矩阵体积大, 现算确定性可复现).
        注意: 单文本超过max_length即截断——与单向量相同的512限制,
        这是token级后期交互对照实验的一部分(单元级无总量限制).
        batch_size=0自动选择(GPU=64, CPU=16); 显式指定覆盖.
        """
        mode = self.ensure()
        out: dict[str, Any] = {}
        if mode == "unavailable":
            return out
        torch = self._torch
        if batch_size <= 0:
            batch_size = _BATCH_GPU if mode == "gpu" else _BATCH_CPU
        todo = [t for t in dict.fromkeys(texts) if t]
        for i in range(0, len(todo), batch_size):
            chunk = todo[i:i + batch_size]
            enc = self._tok(chunk, padding=True, truncation=True,
                            max_length=max_length, return_tensors="pt",
                            return_attention_mask=True)
            enc = {k: v.to(self._device) for k, v in enc.items()}
            with torch.no_grad():
                h = self._mdl(**enc).last_hidden_state
                h = torch.nn.functional.normalize(h, dim=-1)
            mask = enc["attention_mask"].bool()
            for bi, t in enumerate(chunk):
                out[t] = h[bi][mask[bi]].float().cpu().numpy()
        return out
