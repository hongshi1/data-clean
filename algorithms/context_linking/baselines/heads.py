"""复现baseline的统一头实现(与evidence_recall同接口).

BM25UnitHead:  单元级BM25, owner分=max单元BM25 (k1=1.5, b=0.75)
TokenMaxSimHead: ColBERT式token级MaxSim, token编码器注入,
torch可选(GPU打分; 缺省numpy, 测试/小规模)
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Protocol

import numpy as np

from ..evidence_recall.evidence import EvidenceStore
from ..evidence_recall.heads import tokenize


class BM25UnitHead:
    """BM25-unit协议: 单元级BM25, owner分 = max_{u∈owner} bm25(q,u).

    与tools/eval_baselines的BM25-unit同数学(k1=1.5, b=0.75),
    单元=表头=值序列化行/图元素.
    """

    name = "bm25_unit"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1, self._b = k1, b
        self._store: EvidenceStore | None = None
        self._tf: list[dict[str, int]] = []
        self._df: dict[str, int] = {}
        self._dl: list[int] = []
        self._avgdl = 0.0

    def build(self, store: EvidenceStore) -> "BM25UnitHead":
        unit_docs = [tokenize(u.text) for u in store.units]
        self._store = store
        self._tf = []
        self._df = defaultdict(int)
        for d in unit_docs:
            tfd: dict[str, int] = defaultdict(int)
            for t in d:
                tfd[t] += 1
            self._tf.append(dict(tfd))
            for t in set(d):
                self._df[t] += 1
        self._dl = [len(d) for d in unit_docs]
        self._avgdl = sum(self._dl) / max(len(unit_docs), 1)
        return self

    def _unit_scores(self, query: str) -> np.ndarray:
        n = self._store.n_units
        qt = tokenize(query)
        if not qt:
            return np.zeros(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        qset = set(qt)
        for i in range(n):
            tfd = self._tf[i]
            if not tfd:
                continue
            s = 0.0
            for t in qset:
                f = tfd.get(t)
                if not f:
                    continue
                df = self._df.get(t, 1)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = f + self._k1 * (
                    1 - self._b + self._b * self._dl[i]
                    / max(self._avgdl, 1e-8))
                s += idf * f * (self._k1 + 1) / max(denom, 1e-8)
            out[i] = s
        return out

    def score_query(self, query: str) -> np.ndarray:
        if self._store is None:
            raise RuntimeError("BM25UnitHead未build")
        us = self._unit_scores(query)
        out = np.full(self._store.n_owners, -1e9, dtype=np.float32)
        for i, owner in enumerate(self._store.owners):
            s, e = self._store.segments[owner]
            if s < e:
                out[i] = us[s:e].max()
        return out


class TokenEncoder(Protocol):
    """token级编码器协议(嵌入到token矩阵, 供MaxSim)."""

    def embed_tokens(self, texts: list[str],
                     max_length: int | None = None
                     ) -> dict[str, list[list[float]]]:
        ...


class TokenMaxSimHead:
    """Token-MaxSim(ColBERT式后期交互): score(q,d)=Σ_qt max_dt cos.

    doc表示=全部非pad token(512窗口, 继承单向量限制——与O1-unit的
    结构性对照点); token编码器注入(BGE家族embed_tokens).
    torch可选: 传入则GPU打分, 否则numpy(测试/小规模).
    """

    name = "token_maxsim"

    def __init__(self, token_encoder: TokenEncoder,
                 torch_mod=None, device: str = "cpu") -> None:
        self._enc = token_encoder
        self._torch = torch_mod
        self._device = device
        self._store: EvidenceStore | None = None
        self._doc_t: np.ndarray | None = None    # (总token, dim)
        self._owner_bounds: list[tuple[str, int, int]] = []

    def build(self, store: EvidenceStore) -> "TokenMaxSimHead":
        mats = []
        bounds = []
        pos = 0
        for owner in store.owners:
            doc = " ".join(u.text for u in store.units_of(owner))
            v = self._enc.embed_tokens([doc])[doc]
            mats.append(np.asarray(v, dtype=np.float32))
            bounds.append((owner, pos, pos + len(v)))
            pos += len(v)
        self._store = store
        self._doc_t = (np.concatenate(mats) if mats
                       else np.zeros((0, 8), dtype=np.float32))
        if self._doc_t.size:
            norms = np.maximum(
                np.linalg.norm(self._doc_t, axis=1, keepdims=True), 1e-8)
            self._doc_t = self._doc_t / norms
        self._owner_bounds = bounds
        if self._torch is not None and self._device != "cpu":
            self._doc_t = self._torch.as_tensor(
                self._doc_t, dtype=self._torch.float32,
                device=self._device)
        return self

    def score_query(self, query: str) -> np.ndarray:
        if self._store is None or self._doc_t is None:
            raise RuntimeError("TokenMaxSimHead未build")
        qv = self._enc.embed_tokens([query[:200]], max_length=64)[
            query[:200]]
        q = np.asarray(qv, dtype=np.float32)
        if len(q) == 0 or self._doc_t.shape[0] == 0:
            return np.zeros(self._store.n_owners, dtype=np.float32)
        qn = np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-8)
        q = q / qn
        if self._torch is not None:
            torch = self._torch
            qt = torch.as_tensor(q, dtype=torch.float32,
                                 device=self._doc_t.device)
            sims = (qt @ self._doc_t.T).cpu().numpy()
        else:
            sims = q @ self._doc_t.T
        max_per_tok = sims.max(axis=1)      # Σ_qt max_dt
        out = np.zeros(self._store.n_owners, dtype=np.float32)
        for i, (owner, s, e) in enumerate(self._owner_bounds):
            if e > s:
                out[i] = float(max_per_tok[s:e].sum())
        return out
