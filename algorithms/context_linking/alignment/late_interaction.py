"""IDF-weighted MaxSim late interaction (ColBERT-style, numpy-only).

Token matrices come from frozen encoders (e.g. ``BgeLocal.embed_tokens``)
and are expected to carry one L2-normalized row per token. This module only
provides the deterministic scoring primitive, so it never touches torch,
disk, or the network.

Math: score = sum_i w_i * max_j cos(q_i, d_j) / sum_i w_i, where w is the
IDF vector. With ``idf=None`` every weight is 1 and the score degenerates to
mean MaxSim (length-normalized, not a sum, to avoid long-query bias).
"""
from __future__ import annotations

import re

import numpy as np

_CJK = re.compile(r"[\u4e00-\u9fff]+")
_LATIN = re.compile(r"[a-z0-9]+")


def bigram_tokens(text: str) -> list[str]:
    """CJK二元组+拉丁token(小写) — 与evidence_recall.heads.tokenize一致."""
    text = text or ""
    out: list[str] = []
    for segment in _CJK.findall(text):
        out.extend(segment[index : index + 2] for index in range(len(segment) - 1))
    out.extend(_LATIN.findall(text.lower()))
    return out


def _rows_normalized(matrix: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("token matrices must be two-dimensional")
    if values.shape[0] == 0:
        return values
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)


def idf_weighted_maxsim(
    query_tokens: np.ndarray,
    doc_tokens: np.ndarray,
    idf: np.ndarray | None,
) -> float:
    """Return sum_i w_i*max_j cos(q_i,d_j) / sum_i w_i (idf=None → w=1)."""
    query = _rows_normalized(query_tokens)
    doc = _rows_normalized(doc_tokens)
    if query.shape[0] == 0 or doc.shape[0] == 0:
        return 0.0
    if query.shape[1] != doc.shape[1]:
        raise ValueError("query and doc token dimensions must match")
    if idf is None:
        weights = np.ones(query.shape[0], dtype=np.float64)
    else:
        weights = np.asarray(idf, dtype=np.float64)
        if weights.ndim != 1 or weights.shape[0] != query.shape[0]:
            raise ValueError("idf must be a 1-D array matching the query token count")
    total = float(weights.sum())
    if total <= 0.0:
        return 0.0
    max_sims = (query @ doc.T).max(axis=1)
    return float((weights * max_sims).sum() / total)
