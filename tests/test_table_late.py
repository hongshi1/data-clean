"""Table-Pali表单元检索: 单元测试+论文数字快照."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.table_late import (  # noqa: E402
    TablePaliIndex,
    parse_table,
    route_combine,
    table_row_texts,
    zscore,
)

EVAL_JSON = BASE / "data/gjb_438c/data_assets/table_late_eval.json"
INDEX_CACHE = BASE / "data/gjb_438c/blackboard/table_pali_index.pkl"


# ── 解析层 ─────────────────────────────────────────────

def test_parse_table_header_style():
    html = ("<table><thead><tr><th><p>序号</p></th><th><p>名称</p></th></tr>"
            "</thead><tbody><tr><td><p>1</p></td><td><p>获取</p></td></tr>"
            "</tbody></table>")
    headers, rows = parse_table(html)
    assert headers == ["序号", "名称"]
    assert rows == [["1", "获取"]]


def test_parse_table_kv_style_with_attrs():
    """GJB用例表: 无thead, td带colspan属性, 键值自含."""
    html = ('<table><tr><td colspan="2"><p>Use Case 名称：数据获取</p></td>'
            '<td colspan="2"><p>Actors：参谋</p></td></tr></table>')
    headers, rows = parse_table(html)
    assert headers == []
    assert rows == [["Use Case 名称：数据获取", "Actors：参谋"]]


def test_row_texts_caption_first_and_pairing():
    chunk = {"text": ("<table><thead><tr><th><p>参数</p></th>"
                      "<th><p>时延</p></th></tr></thead>"
                      "<tbody><tr><td><p>传输</p></td>"
                      "<td><p>30ms</p></td></tr></tbody></table>"),
             "table_caption": "表1 性能", "type": "table"}
    rts = table_row_texts(chunk)
    assert rts[0] == "表1 性能"
    assert rts[1] == "参数=传输 时延=30ms"


def test_row_texts_kv_fallback_when_mismatch():
    """行单元格数≠表头数时回退为原文join(不强行配对)."""
    chunk = {"text": ("<table><thead><tr><th><p>A</p></th>"
                      "<th><p>B</p></th></tr></thead>"
                      "<tbody><tr><td><p>x</p></td></tr></tbody></table>"),
             "type": "table"}
    rts = table_row_texts(chunk)
    assert rts == ["x"]


# ── 评分层(注入桩) ─────────────────────────────────────

class _StubBge:
    def __init__(self, vec: np.ndarray) -> None:
        n = float(np.linalg.norm(vec))
        self._v = vec / n if n > 1e-8 else np.zeros_like(vec)

    def embed(self, texts: list[str]) -> dict[str, list[float]]:
        return {t: self._v.tolist() for t in texts}


def _make_index(mats: dict[str, np.ndarray], qvec: np.ndarray) -> TablePaliIndex:
    idx = TablePaliIndex(use_cache=False)
    idx._idx._bge = _StubBge(qvec)
    idx._idx._mats = mats
    idx._idx.fuzzy_idf = None  # 聚合数学测试关闭池模糊(专项测试单独开)
    idx._idx.mode = "ok"
    idx._idx._ready = True
    return idx


def test_score_k1_max_sim():
    """默认k=1: score=最高行相似度(gate在k=1时为no-op)."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    mat_a = np.stack([q, orth, orth, orth])      # 标题行=1
    mat_b = np.stack([orth, q, orth, orth])      # 内容行=1
    idx = _make_index({"a": mat_a, "b": mat_b}, q)
    sc = idx.score("查询", ["a", "b"])
    assert sc["a"] == pytest.approx(1.0, abs=1e-5)
    assert sc["b"] == pytest.approx(1.0, abs=1e-5)


def test_score_idf_weighting():
    """IDF加权: 低idf的强匹配行被压制后低于高idf的弱匹配行."""
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    mat = np.stack([q, orth])
    idx = _make_index({"m": mat}, q)
    idx._idx._idf = {"m": np.array([0.5, 1.0], dtype=np.float32)}
    assert idx.score("q", ["m"])["m"] == pytest.approx(0.5, abs=1e-5)


def test_score_query_prefix_applied():
    seen: list[str] = []

    class _SpyBge:
        def embed(self, texts: list[str]) -> dict[str, list[float]]:
            seen.extend(texts)
            v = np.zeros(1024, dtype=np.float32)
            return {t: v.tolist() for t in texts}

    idx = TablePaliIndex(use_cache=False)
    idx._idx._bge = _SpyBge()
    idx._idx._mats = {"c": np.stack([np.zeros(1024, dtype=np.float32)])}
    idx._idx.mode = "ok"
    idx._idx._ready = True
    idx.score("测试", ["c"])
    assert seen == ["为这个句子生成表示以用于检索相关文章：测试"]


def test_pool_fuzzy_idf_suppresses_neardup():
    """池相对模糊IDF: near-dup单元被压低, 唯一单元保持.

    机制: 同构行(高互似)在多chunk出现→竞争大→IDF低;
    唯一行IDF=log(1+n/1)高. 池缓存: 同cand_ids只算一次.
    """
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    orth = np.zeros(1024, dtype=np.float32)
    orth[1] = 1.0
    # chunk a: 唯一单元(与q同向); chunk b: 同款单元(与a的单元完全相同→near-dup)
    idx = TablePaliIndex(use_cache=False)
    idx._idx._bge = _StubBge(q)
    idx._idx._mats = {"a": np.stack([q]), "b": np.stack([q])}
    idx._idx.fuzzy_idf = 0.90
    idx._idx.mode = "ok"
    idx._idx._ready = True
    sc = idx.score("q", ["a", "b"])
    # 两chunk单元互为near-dup(余弦1>0.9)→各覆盖2 chunks→idf=log(1+2/2)
    w = np.log(1 + 2 / 2)
    assert sc["a"] == pytest.approx(float(w), abs=1e-4)
    assert sc["b"] == pytest.approx(float(w), abs=1e-4)
    # 池缓存命中(第二次调用不重算)
    n_before = idx._idx.stats["fuzzy_pool_computations"]
    idx.score("q", ["a", "b"])
    assert idx._idx.stats["fuzzy_pool_computations"] == n_before
    # 换池→重算
    idx.score("q", ["a"])
    assert idx._idx.stats["fuzzy_pool_computations"] == n_before + 1


def test_title_concat_in_build(tmp_path: Path):
    """构建期标题拼接: 内容单元文本=标题。原文."""
    import numpy as np
    from algorithms.unit_retrieval import UnitIndex
    units = {"t": ["表1", "行A", "行B"]}
    idx = UnitIndex(lambda ch: units, gate=False, title_concat=True,
                    idf=False, cache_path=tmp_path / "c.pkl", use_cache=False)
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0
    idx._bge = _StubBge(q)
    idx._build()
    # 单元文本应被拼接: 2个内容单元
    assert idx._mats["t"].shape[0] == 3


def test_route_combine_unit_prior_damping():
    """路由= max(0.8·z(dense), z(unit))——单元通道优先."""
    a = np.array([0.9, 0.1, 0.5])
    b = np.array([0.2, 0.8, 0.4])
    r = route_combine(a, b)
    assert np.allclose(r, np.maximum(0.8 * zscore(a), zscore(b)))


def test_zscore_constant_returns_zero():
    assert np.allclose(zscore(np.full(5, 3.0)), np.zeros(5))


# ── 快照层 ─────────────────────────────────────────────

@pytest.mark.skipif(not INDEX_CACHE.exists(),
                    reason="TP索引未构建(先跑 tools/eval_table_late.py)")
def test_index_snapshot():
    import pickle
    with open(INDEX_CACHE, "rb") as f:
        data = pickle.load(f)
    # 默认门面(raw配置)缓存: format可为2(raw)或4(含raw_mats)
    assert data["format"] in (2, 3, 4)
    mats, idfs = data["mats"], data["idf"]
    assert len(mats) == 1207
    n_rows = sum(m.shape[0] for m in mats.values())
    assert n_rows in (12045, 12045 + 0)  # raw配置单元数(caption伪行)
    for cid, mat in mats.items():
        assert mat.ndim == 2 and mat.shape[1] == 1024
        assert len(idfs[cid]) == mat.shape[0]


@pytest.mark.skipif(not EVAL_JSON.exists(),
                    reason="评测结果未生成(先跑 tools/eval_table_late.py)")
def test_profile_matrix_snapshot():
    """画像矩阵快照(2026-10-07): 三画像各治一个查询regime.

    TP-raw=词面友好(复述式), TP-cc=标题级最优(+8.6), TP-cf=语义深行
    最优(0.329→0.394). 无单一配置全场景最优——查询分布决定画像.
    """
    data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    r = data["results"]
    cap = r["caption"]
    assert cap["TP-cc"]["R@1"] == pytest.approx(0.822, abs=1e-2)
    assert cap["TP-cc"]["R@1"] > cap["TP-raw"]["R@1"] + 0.05
    deep1 = r["deep_v1"]
    assert deep1["TP-raw"]["R@1"] == pytest.approx(0.703, abs=1e-2)
    assert deep1["TP-raw"]["R@1"] > deep1["TP-cc"]["R@1"] + 0.10
    deep2 = r["deep_v2"]
    assert deep2["O1-TP-raw"]["R@1"] == pytest.approx(0.389, abs=1e-2)
    assert deep2["O1-TP-raw"]["R@5"] == pytest.approx(0.645, abs=1e-2)
    assert deep2["O1-TP-raw"]["R@1"] > deep2["M3-dense"]["R@1"] + 0.10
    assert deep2["B1-dense"]["R@1"] == pytest.approx(0.084, abs=1e-2)
