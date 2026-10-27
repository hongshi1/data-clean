"""Chinese-CLIP本地编码器: 双模态对齐的图像侧底座(惰性GPU+磁盘缓存).

模型: models/clip/chinese-clip-vit-base-patch16 (753MB, ViT-B/16+RoBERTa)
  - image_embed: 图像→512维(CLIP投影空间, 图文原生对齐)
  - text_embed:  文本→512维(同空间 — CLIP原生zero-shot检索用)

设计(与bge_local/reranker同规范): 模块顶层零I/O、ensure()内加载、
eval+no_grad确定性、图像嵌入磁盘缓存(381张一次性编码).
"""
from __future__ import annotations

import pickle
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE / "models" / "clip" / "chinese-clip-vit-base-patch16"
CACHE_PATH = BASE / "data/gjb_438c/blackboard/clip_image_index.pkl"

_BATCH = 16


class ChineseClipEncoder:
    """Chinese-CLIP图文编码器. mode: "unavailable" | "cpu" | "gpu"."""

    def __init__(self, use_cache: bool = True) -> None:
        self.use_cache = use_cache
        self.mode = "unavailable"
        self.last_error = ""
        self.stats: dict[str, Any] = {"n_images": 0, "n_texts": 0,
                                       "infer_ms": 0.0, "device": ""}
        self._ready = False
        self._torch: Any = None
        self._model: Any = None
        self._proc: Any = None
        self._device = ""
        self._img_cache: dict[str, list[float]] = {}

    def ensure(self) -> str:
        if self._ready:
            return self.mode
        self._ready = True
        if not (MODEL_DIR / "config.json").exists():
            self.last_error = f"model not found: {MODEL_DIR}"
            return self.mode
        try:
            import torch
            from transformers import ChineseCLIPModel, ChineseCLIPProcessor
        except ImportError as e:
            self.last_error = f"torch/transformers不可用: {e}"
            return self.mode
        try:
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._torch = torch
            self._model = ChineseCLIPModel.from_pretrained(
                str(MODEL_DIR), local_files_only=True)
            self._proc = ChineseCLIPProcessor.from_pretrained(
                str(MODEL_DIR), local_files_only=True)
            self._model.to(self._device)
            self._model.eval()
        except (OSError, ValueError, RuntimeError) as e:
            self.last_error = f"模型加载失败({self._device}): {e}"
            return self.mode
        if self.use_cache and CACHE_PATH.exists():
            try:
                with open(CACHE_PATH, "rb") as f:
                    self._img_cache = pickle.load(f)
                self.stats["cache_hits"] = len(self._img_cache)
            except (pickle.UnpicklingError, EOFError, OSError):
                self._img_cache = {}
        self.mode = self._device
        self.stats["device"] = self._device
        return self.mode

    @staticmethod
    def _feats(out: Any) -> Any:
        """兼容transformers新旧API: 旧返回tensor, 5.x返回ModelOutput."""
        if hasattr(out, "pooler_output"):
            return out.pooler_output      # (N, 512) 投影特征
        if hasattr(out, "image_embeds"):
            return out.image_embeds
        return out

    def image_embed(self, images: list[Any]) -> list[list[float]]:
        """PIL.Image/路径列表 → 512维向量(GPU批量, eval+no_grad)."""
        mode = self.ensure()
        self.stats["n_images"] += len(images)
        if mode == "unavailable" or not images:
            return [[0.0] * 512 for _ in images]
        from PIL import Image
        out: list[list[float]] = []
        t0 = time.time()
        for i in range(0, len(images), _BATCH):
            chunk = images[i:i + _BATCH]
            loaded = [Image.open(p).convert("RGB") if isinstance(p, (str, Path))
                      else p for p in chunk]
            inputs = self._proc(images=loaded, return_tensors="pt")
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with self._torch.no_grad():
                feats = self._feats(self._model.get_image_features(**inputs))
                feats = self._torch.nn.functional.normalize(feats, dim=-1)
            out.extend(feats.float().cpu().tolist())
        self.stats["infer_ms"] += round((time.time() - t0) * 1000, 1)
        return out

    def image_embed_cached(self, path: str) -> list[float]:
        """单图带磁盘缓存(路径→向量, 381张SRS图一次性编码后复用)."""
        if path in self._img_cache:
            return self._img_cache[path]
        vec = self.image_embed([path])[0]
        self._img_cache[path] = vec
        if len(self._img_cache) % 64 == 0:
            self.save_cache()
        return vec

    def save_cache(self) -> None:
        if not (self.use_cache and self._img_cache):
            return
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(self._img_cache, f)

    def text_embed(self, texts: list[str]) -> list[list[float]]:
        """文本→512维(CLIP文本投影空间 — 原生zero-shot图文检索)."""
        mode = self.ensure()
        self.stats["n_texts"] += len(texts)
        if mode == "unavailable" or not texts:
            return [[0.0] * 512 for _ in texts]
        out: list[list[float]] = []
        t0 = time.time()
        for i in range(0, len(texts), _BATCH * 2):
            chunk = [t[:200] for t in texts[i:i + _BATCH * 2]]
            inputs = self._proc(text=chunk, return_tensors="pt",
                                padding=True, truncation=True,
                                max_length=64)
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with self._torch.no_grad():
                feats = self._feats(self._model.get_text_features(**inputs))
                feats = self._torch.nn.functional.normalize(feats, dim=-1)
            out.extend(feats.float().cpu().tolist())
        self.stats["infer_ms"] += round((time.time() - t0) * 1000, 1)
        return out
