"""BGE本地通道测试: 四级降级/阈值随模式/语义分区/缓存.

模型或torch缺失时跳过模型类测试(保持套件可移植);
缓存与参数校验为纯单元测试, 无模型依赖.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from algorithms.common.bge_local import BASE as BGE_BASE, BgeLocal
from algorithms.blackboard.embedding_channel import (
    EMB_TH,
    EMB_TH_LOCAL,
    EmbeddingChannel,
)

_MODEL_DIR = BGE_BASE / "models" / "embedding" / "bge-large-zh-v1.5"

requires_bge = pytest.mark.skipif(
    not (_MODEL_DIR / "config.json").exists()
    or importlib.util.find_spec("torch") is None,
    reason="本地bge模型或torch不可用")


# ── 纯单元(无模型) ────────────────────────────────────────

def test_prefer_invalid_rejected():
    with pytest.raises(ValueError, match="prefer"):
        EmbeddingChannel(prefer="bogus")


def test_effective_th_defaults_to_api_when_not_local():
    ch = EmbeddingChannel(prefer="local")
    assert ch.mode == "unavailable"          # ensure()前
    assert ch.effective_th == EMB_TH         # 非local模式用API阈值


def test_bge_cache_roundtrip(tmp_path: Path):
    p = tmp_path / "bge_cache.pkl"
    b1 = BgeLocal(cache_path=p)
    b1._cache = {"数据获取": [0.1, 0.2, 0.3]}
    b1.save()
    b2 = BgeLocal(cache_path=p)
    b2._load_cache()
    assert b2._cache["数据获取"] == [0.1, 0.2, 0.3]


# ── 模型类(需本地权重+torch) ─────────────────────────────

@pytest.fixture(scope="module")
def local_channel():
    ch = EmbeddingChannel(prefer="local")
    assert ch.ensure() == "local"
    return ch


@requires_bge
def test_local_mode_device_and_dim(local_channel):
    assert local_channel.mode == "local"
    assert local_channel._bge.mode in ("cuda", "cpu")
    assert local_channel._bge.stats["dim"] == 1024
    assert local_channel.effective_th == EMB_TH_LOCAL


@requires_bge
def test_match_semantic_separation(local_channel):
    # 同义改写(词法0分)应命中; 不相关功能不应命中
    same = local_channel.match(["数据获取与转换"], ["数据采集与转换"])
    diff = local_channel.match(["数据获取与转换"], ["流媒体传输服务"])
    assert len(same) == 1 and same[0][2] >= EMB_TH_LOCAL
    assert len(diff) == 0


@requires_bge
def test_embed_deterministic_and_coverage(local_channel):
    v1 = local_channel.embed(["结构化数据归集"])["结构化数据归集"]
    v2 = local_channel.embed(["结构化数据归集"])["结构化数据归集"]
    assert v1 and v1 == v2                     # 同文本→同向量(可复现)
    # local模式全部文本有向量(含缓存命中), 覆盖率应为1
    assert local_channel.stats["n_texts_covered"] == local_channel.stats["n_texts_requested"]
