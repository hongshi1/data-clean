"""单元子注意力聚合(UAA): 单元测试+收敛验证快照.

核心验证: warm-start精确性(初始状态=FIXED聚合器)与收敛性
(训练后≈FIXED——固定聚合器是学习注意力族的不动点, 论文claim).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.unit_attention import (  # noqa: E402
    FEAT_DIM,
    INPUT_DIM,
    QCTX_DIM,
    SubAttentionAggregator,
    _kinds,
    table_units_with_feats,
)

EVAL_JSON = BASE / "data/gjb_438c/data_assets/unit_attention_eval.json"
CMSC_MODEL = BASE / "models/cmsc_projection.pt"


def _cand(cid: str, sims: list, idfs: list, cmsc: list | None = None,
          feats: np.ndarray | None = None, pos: bool = False) -> list:
    n = len(sims)
    if feats is None:
        feats = np.zeros((n, FEAT_DIM), dtype=np.float32)
    if cmsc is None:
        cmsc = [0.0] * n
    return [cid, np.asarray(sims, dtype=np.float32),
            np.asarray(cmsc, dtype=np.float32),
            np.asarray(idfs, dtype=np.float32), feats, pos]


# ── warm-start精确性 ───────────────────────────────────

def test_warm_start_equals_fixed_aggregator():
    """初始状态(未训练): score≈max(sim·idf)——softmax(约定=8·value)平滑argmax.

    注意softmax是max的平滑版: logit差~5时α≈0.99, 分数偏低~0.5%.
    """
    att = SubAttentionAggregator()
    cands = [
        _cand("a", [0.9, 0.1], [2.0, 5.0]),   # values=[1.8, 0.5] → ≈1.8
        _cand("b", [0.2, 0.8], [1.0, 1.0]),   # values=[0.2, 0.8] → ≈0.8
    ]
    scores = att.chunk_scores(cands)
    assert scores[0] == pytest.approx(1.8, abs=0.01)
    assert scores[1] == pytest.approx(0.8, abs=0.01)
    assert scores[0] > 1.75 and scores[1] < 0.81


def test_attention_weights_sum_to_one():
    """α分布: 每候选softmax和=1, 维度=单元数."""
    att = SubAttentionAggregator()
    cands = [
        _cand("a", [0.9, 0.1, 0.3], [2.0, 5.0, 1.0]),
        _cand("b", [0.2, 0.8], [1.0, 1.0]),
    ]
    alphas = att.attention_weights(cands)
    assert len(alphas) == 2
    assert len(alphas[0]) == 3 and len(alphas[1]) == 2
    for a in alphas:
        assert a.sum() == pytest.approx(1.0, abs=1e-5)
        assert np.all(a >= 0)


def test_input_dim_consistent():
    """输入特征维数 = FEAT_DIM + sim + cmsc + idf + 查询上下文."""
    assert INPUT_DIM == FEAT_DIM + 3 + QCTX_DIM
    assert FEAT_DIM == 13 and QCTX_DIM == 5 and INPUT_DIM == 21


def test_query_context_in_batch():
    """_build_batch拼入查询级上下文(广播): X列数=INPUT_DIM."""
    att = SubAttentionAggregator()
    cands = [_cand("a", [0.5, 0.3], [1.0, 2.0])]
    X, seg, value = SubAttentionAggregator._build_batch(
        cands, att._init_net() or att._torch, with_grad=False)
    assert X.shape == (2, INPUT_DIM)
    assert seg.tolist() == [0, 0]
    assert value.numpy() == pytest.approx([0.5, 0.6])


# ── 训练与持久化 ───────────────────────────────────────

def test_fit_ranks_positive_first():
    """训练后: 正例候选分数高于负例(合成可分数据)."""
    att = SubAttentionAggregator()
    pos = _cand("pos", [0.9, 0.2], [3.0, 1.0], pos=True)
    neg = _cand("neg", [0.1, 0.15], [1.0, 1.0], pos=False)
    batches = [{"cands": [deepcopy(pos), deepcopy(neg)]} for _ in range(8)]
    att.fit(batches, epochs=5, reg=0.1)
    scores = att.chunk_scores([pos, neg])
    assert scores[0] > scores[1]


def test_save_load_roundtrip(tmp_path: Path):
    att = SubAttentionAggregator()
    cands = [_cand("a", [0.7, 0.2], [2.0, 1.0])]
    before = att.chunk_scores(cands)
    p = tmp_path / "uaa.pt"
    att.save(p)
    att2 = SubAttentionAggregator()
    assert att2.load(p) is True
    after = att2.chunk_scores(cands)
    assert after == pytest.approx(before, abs=1e-6)


from copy import deepcopy  # noqa: E402


# ── 特征提取 ───────────────────────────────────────────

def test_kinds_onehot():
    assert _kinds(True, False, False, False)[0] == 1.0
    assert _kinds(False, True, False, False)[1] == 1.0
    assert _kinds(False, False, True, False)[2] == 1.0
    assert _kinds(False, False, False, True)[3] == 1.0
    assert _kinds(False, False, False, False)[4] == 0.0


def test_table_feats_title_first_and_row_pos():
    chunk = {"type": "table", "chunk_id": "t1",
             "text": ("<table><thead><tr><th><p>A</p></th></tr></thead>"
                      "<tbody><tr><td><p>1</p></td></tr>"
                      "<tr><td><p>2</p></td></tr></tbody></table>"),
             "table_caption": "表1"}
    out = table_units_with_feats([chunk])
    texts, feats = out["t1"]
    assert texts[0] == "表1"
    assert feats.shape == (3, FEAT_DIM)
    # 特征布局: [kind(0..5), log_len(6), rx(7), ry(8), deg_in(9), deg_out(10),
    #            row_pos(11), n_cells(12)]
    assert feats[0][0] == 1.0 and feats[0][1] == 0.0  # 标题kind=0
    assert feats[1][3] == 1.0  # 行kind=3
    assert feats[1][FEAT_DIM - 2] == 0.0  # row_pos首行=0
    assert feats[2][FEAT_DIM - 2] > 0.0   # row_pos末行>0


@pytest.mark.skipif(not (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json").exists(),
                    reason="数据集不存在")
def test_table_feats_align_with_extractor():
    """表单元特征提取与unit_retrieval.table_unit_texts文本一致(对齐保证)."""
    from algorithms.unit_retrieval import table_unit_texts
    chunks = json.loads(
        (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json")
        .read_text(encoding="utf-8"))
    tables = [c for c in chunks if c.get("type") == "table"][:50]
    out = table_units_with_feats(tables)
    n_match = 0
    for c in tables:
        cid = c["chunk_id"]
        if cid in out:
            assert out[cid][0] == table_unit_texts(c), f"文本不对齐: {cid}"
            n_match += 1
    assert n_match > 10


@pytest.mark.skipif(not (BASE / "data/gjb_438c/anchor_v2/anchors_v2.json").exists(),
                    reason="锚点数据不存在")
def test_image_feats_align_with_extractor():
    """图单元特征提取与va_colpali.image_unit_extractor文本一致(对齐保证)."""
    from algorithms.va_colpali import image_unit_extractor
    chunks = json.loads(
        (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json")
        .read_text(encoding="utf-8"))
    base = image_unit_extractor(chunks)
    out = _image_feats(chunks)
    assert set(base) == set(out)
    for cid, texts in base.items():
        assert out[cid][0] == texts, f"文本不对齐: {cid}"
        assert out[cid][1].shape == (len(texts), FEAT_DIM)


def _image_feats(chunks):
    from algorithms.unit_attention import image_units_with_feats
    return image_units_with_feats(chunks)


@pytest.mark.skipif(not CMSC_MODEL.exists(), reason="CMSC模型不存在")
def test_cmsc_projector_shapes():
    """CMSC冻结投影头: query→(256,)归一, units→(n,256)归一."""
    from algorithms.unit_attention import CmscProjector
    proj = CmscProjector()
    assert proj.ensure() is True
    q = proj.project_query(np.zeros(1024, dtype=np.float32))
    assert q is not None and q.shape == (256,)
    u = proj.project_units(np.zeros((3, 1024), dtype=np.float32))
    assert u is not None and u.shape == (3, 256)


# ── 收敛验证快照(论文数字) ─────────────────────────────

@pytest.mark.skipif(not EVAL_JSON.exists(),
                    reason="评测结果未生成(先跑 tools/eval_unit_attention.py)")
def test_convergence_snapshot():
    """收敛验证: UAA(pinned)≈FIXED——固定聚合器是学习族的不动点."""
    data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    r = data["results"]
    # 图: ΔR@1 < 1pt
    assert abs(r["image"]["UAA"]["R@1"] - r["image"]["FIXED"]["R@1"]) < 0.01
    # caption: ΔR@1 < 1pt
    assert abs(r["table_caption"]["UAA"]["R@1"]
               - r["table_caption"]["FIXED"]["R@1"]) < 0.01
    # 深行: R@1持平, R@5允许小幅增益
    assert r["table_deep"]["UAA"]["R@1"] == pytest.approx(
        r["table_deep"]["FIXED"]["R@1"], abs=1e-3)
    assert r["table_deep"]["UAA"]["R@5"] >= r["table_deep"]["FIXED"]["R@5"]
