"""多头冻结投影头(勘验显影技术).

头 = (单元提取, 冻结投影, 评分函数), 全程无可训练参数:
  SemanticUnitHead: s(q,d)=max_u cos(q,u)·log(1+N/df(u))   [O1-unit数学]
  LexicalHead:      BM25(文档级, CJK二元组+拉丁词)           [词面显影]
  DenseHead:        文档级余弦(对照头)

编码器经Encoder协议注入(默认BgeLocal惰性; 测试用确定性FakeEncoder).
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Protocol

import numpy as np

from .evidence import EvidenceStore

QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
_CJK = re.compile(r"[\u4e00-\u9fff]+")
_LATIN = re.compile(r"[a-z0-9]+")


class Encoder(Protocol):
    """冻结编码器协议: 文本→单位向量."""

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        ...


def tokenize(text: str) -> list[str]:
    """CJK二元组+拉丁词(小写) — 与tools/eval_baselines.tokenize一致."""
    text = text or ""
    out: list[str] = []
    for seg in _CJK.findall(text):
        out.extend(seg[i:i + 2] for i in range(len(seg) - 1))
    out.extend(_LATIN.findall(text.lower()))
    return out


def _unit_vec(v: list[float] | np.ndarray) -> np.ndarray:
    a = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(a))
    return a / n if n > 1e-8 else a


class SemanticUnitHead:
    """语义单元头: max_u[cos(q,u)·IDF(u)] — 表行/图元素通用."""

    name = "semantic_unit"

    def __init__(self, encoder: Encoder,
                 prefix: str = QUERY_PREFIX) -> None:
        self._encoder = encoder
        self._prefix = prefix
        # build后填充(冻结缓存, 无梯度)
        self._store: EvidenceStore | None = None
        self._U: np.ndarray | None = None       # (n_units, dim)单位化
        self._idf: np.ndarray | None = None     # (n_units,)
        self._owner_pos: list[tuple[str, int, int]] = []
        # 查询向量单条memo(同一查询的score/top_units只编码一次)
        self._last_q: str | None = None
        self._last_v: list[float] | None = None

    def _qvec(self, query: str) -> list[float] | None:
        """查询编码(带单条memo: recall流程中score+top_units复用)."""
        if self._last_q != query:
            self._last_v = self._encoder.embed(
                [self._prefix + query[:200]]).get(
                    self._prefix + query[:200])
            self._last_q = query
        return self._last_v

    def build(self, store: EvidenceStore) -> "SemanticUnitHead":
        """冻结投影构建: 编码全部单元+IDF(一次性, 之后只读)."""
        texts = store.unit_texts()
        vecs = self._encoder.embed(texts)
        if texts:
            U = np.stack([_unit_vec(vecs.get(t, [0.0] * 32)) for t in texts])
        else:
            U = np.zeros((0, 32), dtype=np.float32)
        df_raw = store.idf()
        idf = np.asarray(
            [math.log(1 + df_raw.get(t, store.n_owners))
             for t in texts], dtype=np.float32)
        self._store = store
        self._U = U
        self._idf = idf
        self._owner_pos = [(o, *store.segments[o]) for o in store.owners]
        return self

    def score_query(self, query: str) -> np.ndarray:
        """查询→每owner证据分(与统一评测O1-unit同数学)."""
        if self._U is None or self._store is None:
            raise RuntimeError("SemanticUnitHead未build")
        v = self._qvec(query)
        if not v:
            return np.zeros(self._store.n_owners, dtype=np.float32)
        qn = _unit_vec(v)
        sims = (self._U @ qn) * self._idf
        out = np.full(self._store.n_owners, -1e9, dtype=np.float32)
        for i, (owner, s, e) in enumerate(self._owner_pos):
            if s < e:
                out[i] = sims[s:e].max()
        return out

    def top_units(self, query: str, owner: str, topn: int = 2
                  ) -> list[str]:
        """owner内与查询最相关的top-n单元(精排文档来源)."""
        if self._U is None or self._store is None:
            raise RuntimeError("SemanticUnitHead未build")
        v = self._qvec(query)
        seg = self._store.segments.get(owner)
        if not v or not seg:
            return []
        qn = _unit_vec(v)
        s, e = seg
        sims = (self._U[s:e] @ qn) * self._idf[s:e]
        uu = [u.text for u in self._store.units[s:e]]
        return [u for _, u in sorted(zip(sims, uu), reverse=True)[:topn]]


class LexicalHead:
    """词面头: 文档级BM25(k1=1.5, b=0.75) — 图片场景主导."""

    name = "lexical"

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1, self._b = k1, b
        self._store: EvidenceStore | None = None
        self._tf: list[dict[str, int]] = []
        self._df: dict[str, int] = {}
        self._dl: list[int] = []
        self._avgdl = 0.0

    def build(self, store: EvidenceStore) -> "LexicalHead":
        owner_docs = []
        for owner in store.owners:
            toks: list[str] = []
            for u in store.units_of(owner):
                toks.extend(tokenize(u.text))
            owner_docs.append(toks)
        self._store = store
        self._tf = []
        self._df = defaultdict(int)
        for d in owner_docs:
            tfd: dict[str, int] = defaultdict(int)
            for t in d:
                tfd[t] += 1
            self._tf.append(dict(tfd))
            for t in set(d):
                self._df[t] += 1
        self._dl = [len(d) for d in owner_docs]
        self._avgdl = sum(self._dl) / max(len(owner_docs), 1)
        return self

    def score(self, query: str) -> np.ndarray:
        if self._store is None:
            raise RuntimeError("LexicalHead未build")
        n = self._store.n_owners
        qt = tokenize(query)
        if not qt:
            return np.zeros(n, dtype=np.float32)
        out = np.zeros(n, dtype=np.float32)
        qtf: dict[str, int] = defaultdict(int)
        for t in qt:
            qtf[t] += 1
        for i in range(n):
            s = 0.0
            for t, _fq in qtf.items():
                tf = self._tf[i].get(t)
                if not tf:
                    continue
                df = self._df.get(t, 1)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = tf + self._k1 * (
                    1 - self._b + self._b * self._dl[i]
                    / max(self._avgdl, 1e-8))
                s += idf * tf * (self._k1 + 1) / max(denom, 1e-8)
            out[i] = s
        return out

    def score_query(self, query: str) -> np.ndarray:
        """统一头接口别名(=score)."""
        return self.score(query)


class DenseHead:
    """稠密头(对照): 文档全文余弦."""

    name = "dense"

    def __init__(self, encoder: Encoder) -> None:
        self._encoder = encoder
        self._store: EvidenceStore | None = None
        self._D: np.ndarray | None = None

    def build(self, store: EvidenceStore) -> "DenseHead":
        texts = [(t + " " + " ".join(u.text for u in store.units_of(t)))
                 [:512] for t in store.owners]
        vecs = self._encoder.embed(texts)
        self._store = store
        if texts:
            self._D = np.stack(
                [_unit_vec(vecs.get(t, [0.0] * 32)) for t in texts])
        else:
            self._D = np.zeros((0, 32), dtype=np.float32)
        return self

    def score(self, query: str) -> np.ndarray:
        if self._D is None or self._store is None:
            raise RuntimeError("DenseHead未build")
        v = self._encoder.embed([query[:200]]).get(query[:200])
        if not v:
            return np.zeros(self._store.n_owners, dtype=np.float32)
        return self._D @ _unit_vec(v)

    def score_query(self, query: str) -> np.ndarray:
        """统一头接口别名(=score)."""
        return self.score(query)
