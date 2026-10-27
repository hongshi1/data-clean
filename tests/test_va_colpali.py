"""VA-ColPali图单元检索: 单元测试+论文数字快照.

覆盖:
  - score()的k=1 MaxSim语义(注入式桩, 不依赖模型)
  - caption映射(doc+fig精确对齐, 不受同名fig跨doc干扰)
  - 索引规模快照(378图=锚点362+VLM元素补足16, 与资产一致)
  - 评测结果快照(0.581/0.847/0.694, 论文数字锁定)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.va_colpali import VaColpaliIndex  # noqa: E402

EVAL_JSON = BASE / "data/gjb_438c/data_assets/va_colpali_eval.json"
INDEX_CACHE = BASE / "data/gjb_438c/blackboard/va_colpali_index.pkl"


class _StubBge:
    """固定向量桩: 查询前缀+任意文本→固定单位向量."""

    def __init__(self, vec: np.ndarray) -> None:
        n = float(np.linalg.norm(vec))
        self._v = vec / n if n > 1e-8 else np.zeros_like(vec)

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        return {t: self._v.tolist() for t in texts}


def _make_index(mats: dict[str, np.ndarray]) -> VaColpaliIndex:
    """注入单元矩阵+桩BGE到门面内部UnitIndex, 不触发ensure()."""
    idx = VaColpaliIndex(use_cache=False)
    idx._idx._bge = _StubBge(np.zeros(1024))
    idx._idx._mats = mats
    idx._idx.mode = "ok"
    idx._idx._ready = True
    return idx


def test_score_k1_max_sim():
    """默认k=1: score=最高单元相似度(MaxSim)."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    idx = _make_index({})
    idx._idx._bge = _StubBge(q)
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    mat5 = np.stack([orth, q, orth, orth, orth])   # 1个同向单元
    mat0 = np.stack([orth, orth, orth])            # 全正交
    idx._idx._mats = {"c5": mat5, "c0": mat0}
    sc = idx.score("任意查询", ["c5", "c0"])
    assert sc["c5"] == pytest.approx(1.0, abs=1e-5)
    assert sc["c0"] == pytest.approx(0.0, abs=1e-5)


def test_score_ignores_unindexed():
    """无单元索引的候选不出现在返回值(调用方负责兜底)."""
    idx = _make_index({})
    idx._idx._bge = _StubBge(np.zeros(1024))
    idx._idx._mats = {"only": np.stack([np.zeros(1024, dtype=np.float32)])}
    sc = idx.score("q", ["only", "missing"])
    assert set(sc) == {"only"}
    assert "missing" not in sc


def test_query_prefix_applied():
    """score内部对查询加BGE指令前缀(桩验证前缀文本确实传入embed)."""
    seen: list[str] = []

    class _SpyBge:
        def embed(self, texts: list[str]) -> dict[str, list[float]]:
            seen.extend(texts)
            v = np.zeros(1024, dtype=np.float32)
            return {t: v.tolist() for t in texts}

    idx = _make_index({})
    idx._idx._bge = _SpyBge()
    idx._idx._mats = {"c": np.stack([np.zeros(1024, dtype=np.float32)])}
    idx.score("测试查询", ["c"])
    assert seen == ["为这个句子生成表示以用于检索相关文章：测试查询"]


def test_captions_by_chunk_aligns_doc_and_fig():
    """caption映射用(doc, fig编号)对齐, 不受跨文档同名fig干扰."""
    import algorithms.va_colpali as vamod
    images = [
        {"doc": "A需求-终稿", "chunk_id": "A需求-终稿_I0001",
         "image_path": "images/fig_001.png", "type": "image"},
        {"doc": "B需求-终稿", "chunk_id": "B需求-终稿_I0002",
         "image_path": "images/fig_001.png", "type": "image"},
    ]
    analyses = {"analyses": [
        {"doc": "B需求-终稿",
         "image_path": "data/x/B需求-终稿/office/images/fig_001.png",
         "caption": ["图 1 B的图"]},
    ]}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "vlm.json"
        p.write_text(json.dumps(analyses, ensure_ascii=False),
                     encoding="utf-8")
        orig = vamod.SRS_IMAGE_ANALYSES
        vamod.SRS_IMAGE_ANALYSES = p
        try:
            caps = VaColpaliIndex._captions_by_chunk(images)
        finally:
            vamod.SRS_IMAGE_ANALYSES = orig
    assert caps == {"B需求-终稿_I0002": "图 1 B的图"}


@pytest.mark.skipif(not INDEX_CACHE.exists(),
                    reason="VA索引缓存未构建(先跑 tools/eval_va_colpali.py)")
def test_index_snapshot():
    """索引规模快照: 378图(锚点362+VLM元素单元补足16), v3格式IDF+CMSC对齐."""
    import pickle
    with open(INDEX_CACHE, "rb") as f:
        data = pickle.load(f)
    assert data["format"] == 3
    mats, idfs, cmsc = data["mats"], data["idf"], data["cmsc"]
    assert len(mats) == 378
    for cid, mat in mats.items():
        assert mat.ndim == 2 and mat.shape[1] == 1024
        norms = np.linalg.norm(mat, axis=1)
        assert np.all(norms > 0.99) and np.all(norms < 1.01)
        assert len(idfs[cid]) == mat.shape[0]
        assert cmsc[cid].shape == (mat.shape[0], 256)


@pytest.mark.skipif(not EVAL_JSON.exists(),
                    reason="评测结果未生成(先跑 tools/eval_va_colpali.py)")
def test_eval_snapshot():
    """论文数字快照(k=1+IDF+VLM元素单元, CMSC默认关——泄漏审计后诚实值)."""
    data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    res = data["results"]
    assert res["B1_bridge"]["R@1"] == pytest.approx(0.5151, abs=1e-3)
    assert res["B1_bridge"]["R@5"] == pytest.approx(0.7759, abs=1e-3)
    assert res["VA_colpali"]["R@1"] == pytest.approx(0.581, abs=1e-3)
    assert res["VA_colpali"]["R@5"] == pytest.approx(0.847, abs=1e-3)
    assert res["VA_colpali"]["MRR@10"] == pytest.approx(0.694, abs=1e-3)
    assert res["VA_colpali"]["R@1"] > res["B1_bridge"]["R@1"] + 0.05
    assert res["VA_colpali"]["R@5"] > res["B1_bridge"]["R@5"]
