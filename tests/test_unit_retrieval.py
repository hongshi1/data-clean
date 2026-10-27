"""单元检索核心(unit_retrieval): 统一打分/IDF/路由的单元测试.

覆盖: k=1默认MaxSim / k≥3的gate语义 / IDF特异性加权 / v2缓存格式 /
route_combine单元通道优先路由(阻尼0.8). 行为快照另见
test_va_colpali/test_table_late的eval快照.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.unit_retrieval import (  # noqa: E402
    UnitIndex,
    parse_table,
    route_combine,
    table_unit_extractor,
    table_unit_texts,
    zscore,
)


class _StubBge:
    def __init__(self, vec: np.ndarray) -> None:
        n = float(np.linalg.norm(vec))
        self._v = vec / n if n > 1e-8 else np.zeros_like(vec)

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        return {t: self._v.tolist() for t in texts}


def _make(gate: bool, mats: dict[str, np.ndarray],
          qvec: np.ndarray, min_units: int = 1,
          idfs: dict[str, np.ndarray] | None = None,
          top_k: int = 1) -> UnitIndex:
    idx = UnitIndex(lambda ch: {}, gate=gate, top_k=top_k,
                    min_units=min_units, use_cache=False)
    idx._bge = _StubBge(qvec)
    idx._mats = mats
    if idfs is not None:
        idx._idf = idfs
    idx.mode = "ok"
    idx._ready = True
    return idx


# ── 默认打分(k=1, IDF加权MaxSim) ──────────────────────

def test_score_default_k1_is_max_sim():
    """默认k=1: score=最高单元相似度(gate在k=1时为no-op)."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    # 5单元(1个同向+4个正交): MaxSim=1
    mat = np.stack([orth, q, orth, orth, orth])
    idx = _make(False, {"m": mat}, q)
    assert idx.score("q", ["m"])["m"] == pytest.approx(1.0, abs=1e-5)
    # gate=True在k=1时同结果(max(sims[0], max(sims))=max(sims))
    idx_g = _make(True, {"m": mat}, q)
    assert idx_g.score("q", ["m"])["m"] == pytest.approx(1.0, abs=1e-5)


def test_score_idf_weights_units():
    """IDF: 常见单元(低idf)被压制, 稀有单元(高idf)被放大."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    mat = np.stack([q, orth])  # 单元0与query同向
    idfs = {"m": np.array([0.5, 1.0], dtype=np.float32)}  # 单元0权重0.5
    idx = _make(False, {"m": mat}, q, idfs=idfs)
    assert idx.score("q", ["m"])["m"] == pytest.approx(0.5, abs=1e-5)


# ── k≥2时的gate语义(向后兼容路径) ─────────────────────

def test_score_gate_on_topk3():
    """top_k=3+gate: score=max(标题单元, top-3均值)."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    mat_title = np.stack([q, orth, orth, orth, orth])   # 标题=1, top3=1/3
    mat_row = np.stack([orth, q, orth, orth])            # 行=1, top3=1/3
    idx = _make(True, {"a": mat_title, "b": mat_row}, q, top_k=3)
    sc = idx.score("q", ["a", "b"])
    assert sc["a"] == pytest.approx(1.0, abs=1e-5)      # max(1, 1/3)
    assert sc["b"] == pytest.approx(1 / 3, abs=1e-5)    # max(0, 1/3)


def test_score_topk_fewer_than_k():
    """单元数<k时取全部均值."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    mat = np.stack([q, orth])
    idx = _make(False, {"m": mat}, q, top_k=3)
    assert idx.score("q", ["m"])["m"] == pytest.approx(0.5, abs=1e-5)


def test_score_missing_candidate_absent():
    idx = _make(False, {}, np.zeros(1024, dtype=np.float32))
    assert idx.score("q", ["x"]) == {}


def test_query_prefix_applied():
    seen: list[str] = []

    class _SpyBge:
        def embed(self, texts: list[str]) -> dict[str, list[float]]:
            seen.extend(texts)
            v = np.zeros(1024, dtype=np.float32)
            return {t: v.tolist() for t in texts}

    idx = UnitIndex(lambda ch: {}, gate=False, use_cache=False)
    idx._bge = _SpyBge()
    idx._mats = {"c": np.stack([np.zeros(1024, dtype=np.float32)])}
    idx.mode = "ok"
    idx._ready = True
    idx.score("测试", ["c"])
    assert seen == ["为这个句子生成表示以用于检索相关文章：测试"]


# ── 构建与v2缓存 ───────────────────────────────────────

def test_build_min_units_and_idf(tmp_path: Path):
    """构建: min_units过滤 + IDF与矩阵行对齐 + v2缓存落盘."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    units_map = {"a": ["稀有单元", "u2", "u3"],   # 3单元
                 "b": ["u1", "u2"]}                # 2单元
    cache = tmp_path / "idx.pkl"
    idx = UnitIndex(lambda ch: units_map, gate=False, min_units=3,
                    idf=True, cache_path=cache, use_cache=True)
    idx._bge = _StubBge(q)
    idx._build()
    assert set(idx.indexed_ids) == {"a"}
    assert len(idx._idf["a"]) == idx._mats["a"].shape[0]
    # v2缓存含format/mats/idf
    import pickle
    with open(cache, "rb") as f:
        data = pickle.load(f)
    assert data["format"] == 2
    assert set(data["mats"]) == {"a"}
    assert set(data["idf"]) == {"a"}


def test_v1_cache_rejected_when_idf(tmp_path: Path):
    """v1缓存(纯矩阵)在idf=True时拒绝加载(无对齐信息→强制重建)."""
    import pickle
    cache = tmp_path / "old.pkl"
    mat = np.stack([np.zeros(1024, dtype=np.float32)])
    with open(cache, "wb") as f:
        pickle.dump({"x": mat}, f)
    idx = UnitIndex(lambda ch: {}, gate=False, idf=True,
                    cache_path=cache, use_cache=True)
    assert idx._load_cache() is False


# ── 表单元提取 ─────────────────────────────────────────

def test_table_unit_texts_title_first():
    chunk = {"text": ("<table><thead><tr><th><p>参数</p></th>"
                      "<th><p>时延</p></th></tr></thead>"
                      "<tbody><tr><td><p>传输</p></td>"
                      "<td><p>30ms</p></td></tr></tbody></table>"),
             "table_caption": "表1 性能", "type": "table"}
    units = table_unit_texts(chunk)
    assert units[0] == "表1 性能"
    assert units[1] == "参数=传输 时延=30ms"


def test_parse_table_kv_style_with_attrs():
    html = ('<table><tr><td colspan="2"><p>Use Case 名称：数据获取</p></td>'
            '<td colspan="2"><p>Actors：参谋</p></td></tr></table>')
    headers, rows = parse_table(html)
    assert headers == []
    assert rows == [["Use Case 名称：数据获取", "Actors：参谋"]]


def test_table_unit_extractor_filters_by_type():
    chunks = [
        {"type": "table", "chunk_id": "t1",
         "text": "<table><tr><td><p>x</p></td></tr></table>",
         "table_caption": "表1"},
        {"type": "text", "chunk_id": "c1", "text": "正文"},
    ]
    out = table_unit_extractor(chunks)
    assert set(out) == {"t1"}
    assert out["t1"][0] == "表1"


# ── 组合规则 ───────────────────────────────────────────

def test_route_combine_unit_prior_damping():
    """路由= max(0.8·z(dense), z(unit)) —— 单元通道优先, dense阻尼0.8."""
    a = np.array([0.9, 0.1, 0.5])
    b = np.array([0.2, 0.8, 0.4])
    r = route_combine(a, b)
    assert np.allclose(r, np.maximum(0.8 * zscore(a), zscore(b)))


def test_zscore_constant_returns_zero():
    assert np.allclose(zscore(np.full(5, 3.0)), np.zeros(5))
