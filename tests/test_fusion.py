"""融合层测试: A5加权RRF + A1注意力(合成数据, 零数据资产依赖).

锁定内容:
  - rrf_weighted: 权重主导性/factual直通/meta富化与丢弃/平分确定性
  - query_features / zscore_channels: 特征口径
  - ChannelAttentionFusion: 可分数据上学得动/同seed确定性/未fit报错
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pytest

from algorithms.blackboard.fusion import (
    CALIBRATED_WEIGHTS,
    ChannelAttentionFusion,
    query_features,
    rrf_weighted,
    zscore_channels,
)
from algorithms.blackboard.hybrid_recall import CHANNELS


@dataclass(slots=True)
class _Hit:
    chunk_id: str
    score: float = 1.0


@dataclass(slots=True)
class _Chan:
    hits: list[_Hit] = field(default_factory=list)


def _chan(*cids: str, score: float = 1.0) -> _Chan:
    return _Chan([_Hit(c, score) for c in cids])


def test_calibrated_weights_cover_channels():
    from algorithms.blackboard.hybrid_recall import CHANNELS

    assert set(CALIBRATED_WEIGHTS) == set(CHANNELS)
    assert all(0.0 < v <= 1.0 for v in CALIBRATED_WEIGHTS.values())


def test_rrf_weighted_schema_and_default_order():
    cres = {"lexical": _chan("a", "b"), "sparse": _chan("b", "a")}
    out = rrf_weighted(cres, top_k=5)
    # lexical权重0.95 > sparse 0.70 → lexical首位候选a胜出
    assert [h["chunk_id"] for h in out] == ["a", "b"]
    assert all(h["tier"] == "rrf" for h in out)
    assert out[0]["channels"] == ["lexical", "sparse"]
    assert [h["rank"] for h in out] == [1, 2]
    # 等权下a/b同分 → 平分按chunk_id字典序(确定性)
    eq = rrf_weighted(cres, weights={"lexical": 1.0, "sparse": 1.0}, top_k=5)
    assert [h["chunk_id"] for h in eq] == ["a", "b"]


def test_rrf_weighted_weights_flip_order():
    cres = {"lexical": _chan("x", "y"), "sparse": _chan("y", "x")}
    hi_lex = rrf_weighted(cres, weights={"lexical": 0.9, "sparse": 0.1})
    hi_spr = rrf_weighted(cres, weights={"lexical": 0.1, "sparse": 0.9})
    assert hi_lex[0]["chunk_id"] == "x"     # lexical首位候选
    assert hi_spr[0]["chunk_id"] == "y"     # sparse首位候选


def test_rrf_keep_factual_direct_pass():
    cres = {"lexical": _chan("f"), "sparse": _chan("z")}
    with_f = rrf_weighted(cres, top_k=2, keep_factual=True)
    assert [h["chunk_id"] for h in with_f] == ["f", "z"]
    assert with_f[0]["tier"] == "factual"
    assert with_f[1]["tier"] == "rrf"
    without = rrf_weighted(cres, top_k=2)
    assert all(h["tier"] == "rrf" for h in without)
    # 非完整子串命中(score<1.0)不直通
    cres2 = {"lexical": _chan("f", score=0.5), "sparse": _chan("z")}
    w2 = rrf_weighted(cres2, top_k=2, keep_factual=True)
    assert all(h["tier"] == "rrf" for h in w2)


def test_rrf_meta_fn_enrich_and_drop():
    cres = {"sparse": _chan("a", "b")}

    def meta(cid: str) -> dict[str, str] | None:
        return None if cid == "b" else {"section": "3.1", "type": "text"}

    out = rrf_weighted(cres, top_k=5, meta_fn=meta)
    assert [h["chunk_id"] for h in out] == ["a"]
    assert out[0]["section"] == "3.1"
    assert out[0]["rank"] == 1


def test_zscore_channels_active_stats():
    rr = np.array([[1 / 61, 0.0], [1 / 62, 0.0], [0.0, 1 / 61]])
    z = zscore_channels(rr)
    # 通道0: 活跃集{r0,r1} → z≈±1(分母ε有~1%收缩); 未召回r2 → 负值被clip
    assert z[0, 0] == pytest.approx(1.0, abs=0.01)
    assert z[1, 0] == pytest.approx(-1.0, abs=0.01)
    assert z[2, 0] == -3.0
    # 通道1: 单活跃(σ=0) → 活跃z=0, 未召回clip到-3
    assert z[2, 1] == 0.0
    assert z[0, 1] == -3.0
    assert z[1, 1] == -3.0


def test_query_features():
    q = query_features("收件箱和发件箱接口")
    assert q[0] == pytest.approx(0.75)   # 9字全CJK: 9/12 × 1
    assert q[1] == 0.0 and q[2] == 0.0
    assert query_features("图3-1的部署结构")[1] == 1.0
    i = query_features("PZXQ-GN-SJHQ")
    assert i[2] == 1.0
    assert i[0] == pytest.approx(0.0)    # 无CJK → 实体性0
    assert query_features("")[0] == 0.0


def _mk_attention_data(n: int = 40, k: int = 60) -> tuple:
    """合成可分数据: 文本实体查询→lexical首位候选为期望chunk;
    ID查询→structural首位候选为期望chunk(α应按查询类型切换)."""
    qs, scores, labels = [], [], []
    for i in range(n):
        is_id = i % 2 == 1
        rr = np.zeros((4, len(CHANNELS)))
        if is_id:
            rr[1, 3] = 1.0 / (k + 1)
            rr[2, 2] = 1.0 / (k + 2)
            qs.append("PZXQ-GN-SJHQ")
            labels.append(np.array([0.0, 1.0, 0.0, 0.0]))
        else:
            rr[0, 0] = 1.0 / (k + 1)
            rr[2, 2] = 1.0 / (k + 2)
            qs.append("收件箱和发件箱接口")
            labels.append(np.array([1.0, 0.0, 0.0, 0.0]))
        scores.append(rr)
    return qs, scores, labels


def test_attention_learns_and_deterministic():
    qs, scores, labels = _mk_attention_data()
    a1 = ChannelAttentionFusion()
    hist = a1.fit(qs, (scores, labels), epochs=120)
    assert len(hist) == 120
    assert hist[-1] < hist[0]
    # 文本实体查询: lexical候选(行0)应排首位
    r_text = a1.fuse("收件箱和发件箱接口", scores[0])
    assert r_text["ranked"][0][0] == 0
    # ID查询: structural候选(行1)应排首位
    r_id = a1.fuse("PZXQ-GN-SJHQ", scores[1])
    assert r_id["ranked"][0][0] == 1
    # α是分布且路由正确
    assert sum(r_text["alpha"].values()) == pytest.approx(1.0, abs=1e-3)
    assert r_text["alpha"]["lexical"] > r_text["alpha"]["dense"]
    assert r_id["alpha"]["structural"] > r_id["alpha"]["lexical"]
    # 同seed两实例 → 同结果(确定性)
    a2 = ChannelAttentionFusion()
    a2.fit(qs, (scores, labels), epochs=120)
    r2 = a2.fuse("收件箱和发件箱接口", scores[0])
    assert r2["alpha"] == r_text["alpha"]
    assert r2["ranked"] == r_text["ranked"]


def test_attention_requires_fit():
    att = ChannelAttentionFusion()
    with pytest.raises(RuntimeError):
        att.fuse("查询", np.zeros((3, len(CHANNELS))))


def test_attention_fit_validation():
    att = ChannelAttentionFusion()
    with pytest.raises(ValueError, match="候选行数"):
        att.fit(["查询"], ([np.zeros((2, len(CHANNELS)))], [np.zeros(3)]))
    with pytest.raises(ValueError, match="矩阵"):
        att.fit(["查询"], ([np.zeros((2, 4))], [np.zeros(2)]))
    with pytest.raises(ValueError, match="无正例"):
        att.fit(["查询"], ([np.zeros((2, len(CHANNELS)))], [np.zeros(2)]))


def test_attention_fuse_query_feature_vector():
    """fuse接受3维特征向量(与查询串等价)."""
    qs, scores, labels = _mk_attention_data(4)
    att = ChannelAttentionFusion()
    att.fit(qs, (scores, labels), epochs=60)
    r_str = att.fuse("收件箱和发件箱接口", scores[0])
    r_vec = att.fuse(query_features("收件箱和发件箱接口"), scores[0])
    assert r_vec["ranked"] == r_str["ranked"]
    with pytest.raises(ValueError, match="3维"):
        att.fuse([0.5, 0.0], scores[0])
