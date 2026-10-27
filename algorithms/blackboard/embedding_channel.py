"""Embedding通道: 四级降级 (live API → 本地BGE → pickle缓存 → 不可用).

- live:   复用tools/m1_compare_engine.embed_batch (API+pickle缓存, 网络失败优雅返回[])
- local:  本地bge-large-zh-v1.5 (GPU优先, 自带磁盘缓存, 离线可用, 确定性可复现)
- cache:  直接读emb_cache.pkl (API向量空间, 仅覆盖已缓存文本)
- unavailable: 通道不可用 (router自动跳过语义富集)

原则: 通道降级是显式状态(mode), 不是静默失败 —— blackboard.embedding_mode记录.
阈值: API向量空间与BGE向量空间不互换, 各自校准(EMB_TH vs EMB_TH_LOCAL);
prefer="local"把本地BGE提为首选(离线实验/可复现优先).
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any

from algorithms.common.bge_local import BgeLocal

BASE = Path(__file__).resolve().parents[2]
TOOLS_DIR = BASE / "tools"
EMB_CACHE_PATH = BASE / "data/gjb_438c/anchor_sc2/emb_cache.pkl"

EMB_TH = 0.62        # API embedding余弦阈值(与m1一致, 既有校准值)
EMB_TH_LOCAL = 0.78  # 本地BGE余弦阈值(bge_threshold_sweep校准: 确认对p10=0.806/未确认对p90=0.755, agreement=0.9708)

_TIER_ORDER: dict[str, tuple[str, ...]] = {
    "auto": ("live", "local", "cache"),
    "local": ("local", "live", "cache"),
}


class EmbeddingChannel:
    """语义匹配通道. match()返回(i, j, score)三元组列表."""

    def __init__(self, tools_dir: Path | None = None,
                 cache_path: Path | None = None,
                 prefer: str = "auto",
                 bge: BgeLocal | None = None) -> None:
        if prefer not in _TIER_ORDER:
            raise ValueError(f"prefer must be one of {sorted(_TIER_ORDER)}, got {prefer!r}")
        self.tools_dir = tools_dir or TOOLS_DIR
        self.cache_path = cache_path or EMB_CACHE_PATH
        self.prefer = prefer
        self._bge = bge if bge is not None else BgeLocal()
        self.mode = "unavailable"
        self._embed_fn: Any = None
        self._cache: dict[str, list[float]] = {}
        self._ready = False
        self.last_error = ""
        self.stats = {"n_texts_requested": 0, "n_texts_covered": 0}

    # ── 惰性初始化 ────────────────────────────────────────
    def _ensure(self) -> None:
        if self._ready:
            return
        self._ready = True
        for tier in _TIER_ORDER[self.prefer]:
            if tier == "live" and self._try_live():
                return
            if tier == "local" and self._try_local():
                return
            if tier == "cache" and self._load_cache():
                self.mode = "cache"
                return
        self.mode = "unavailable"

    def _try_live(self) -> bool:
        try:
            if str(self.tools_dir) not in sys.path:
                sys.path.insert(0, str(self.tools_dir))
            import m1_compare_engine as m1  # noqa: F401  (import期加载emb_cache)
            if not _api_reachable(m1.EMB_URL):
                self.last_error = "wanqing embedding API不可达"
                return False
            self._embed_fn = m1.embed_batch
            self.mode = "live"
            return True
        except Exception as e:  # m1导入链含ai_config/.env, 缺失时降级
            self.last_error = f"m1 import failed: {e}"
            return False

    def _try_local(self) -> bool:
        if self._bge.ensure() == "unavailable":
            self.last_error = self._bge.last_error
            return False
        self.mode = "local"
        return True

    def _load_cache(self) -> bool:
        try:
            if self.cache_path.exists():
                with open(self.cache_path, "rb") as f:
                    self._cache = pickle.load(f)
                return isinstance(self._cache, dict) and bool(self._cache)
        except (pickle.UnpicklingError, EOFError, OSError) as e:
            self.last_error = f"emb_cache unreadable: {e}"
        self._cache = {}
        return False

    def ensure(self) -> str:
        """公开入口: 初始化并返回mode. runner在循环前调用一次."""
        self._ensure()
        return self.mode

    @property
    def effective_th(self) -> float:
        """当前模式的匹配阈值(向量空间不互换, 阈值随模式)."""
        return EMB_TH_LOCAL if self.mode == "local" else EMB_TH

    # ── 向量获取 ──────────────────────────────────────────
    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        self._ensure()
        self.stats["n_texts_requested"] += len(texts)
        if self.mode == "live":
            vecs = self._embed_fn(texts)
            covered = sum(1 for v in vecs if v)
            self.stats["n_texts_covered"] += covered
            return dict(zip(texts, vecs))
        if self.mode == "local":
            out = self._bge.embed(texts)
            self.stats["n_texts_covered"] += sum(1 for v in out.values() if v)
            return out
        if self.mode == "cache":
            out = {t: self._cache.get(t, []) for t in texts}
            self.stats["n_texts_covered"] += sum(1 for v in out.values() if v)
            return out
        return {t: [] for t in texts}

    # ── 匹配 ──────────────────────────────────────────────
    def match(self, texts_a: list[str], texts_b: list[str],
              th: float | None = None) -> list[tuple[int, int, float]]:
        """A×B余弦≥th的配对. 未覆盖文本(无向量)不参与 —— 覆盖率记录在stats."""
        if not texts_a or not texts_b:
            return []
        if th is None:
            th = self.effective_th
        vecs = self.embed(list(dict.fromkeys([*texts_a, *texts_b])))
        results: list[tuple[int, int, float]] = []
        for i, ta in enumerate(texts_a):
            va = vecs.get(ta) or []
            if not va:
                continue
            for j, tb in enumerate(texts_b):
                vb = vecs.get(tb) or []
                if not vb:
                    continue
                score = _cosine(va, vb)
                if score >= th:
                    results.append((i, j, round(score, 4)))
        results.sort(key=lambda x: -x[2])
        return results


def _api_reachable(url: str, timeout: float = 3.0) -> bool:
    """TCP层探测embedding API可达性(不发送真实请求, 不消耗配额)."""
    import socket
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
        host = p.hostname or ""
        port = p.port or (443 if p.scheme == "https" else 80)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    num = sum(x * y for x, y in zip(a, b))
    den = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5) + 1e-10
    return num / den
