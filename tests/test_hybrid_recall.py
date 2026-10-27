"""多路召回器(HybridRecaller)测试: 通道行为与融合结构(确定性, 含dense降级).

锁定内容(科研数字关联, eval_hybrid_recall):
  - dense通道磁盘缓存复用(索引不重建)
  - cascade融合的席位调度(multimodal保底figure模态)
  - 章节配额后处理
  - 通道可插拔(单通道/消融配置)
  - rrf与cascade两种融合策略的输出schema
  - 查询理解层: LCS检索反推 vs 停用词剥离
"""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.blackboard.evidence_store import EvidenceStore
from algorithms.blackboard.hybrid_recall import (
    CHANNELS,
    HybridRecaller,
    _lcs_cjk,
    detect_entity,
    extract_entity,
)

BASE = Path(__file__).resolve().parents[1]
HAS_DATA = (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json").exists()

pytestmark = pytest.mark.skipif(not HAS_DATA, reason="chunks资产缺失")


@pytest.fixture(scope="module")
def rec() -> HybridRecaller:
    return HybridRecaller()


def test_recall_output_schema(rec: HybridRecaller):
    r = rec.recall("结构化数据归集", "", top_k=10)
    assert r["hits"]
    for h in r["hits"]:
        assert set(h) >= {"chunk_id", "type", "section", "doc", "snippet",
                          "rrf_score", "channels", "rank", "tier"}
    assert r["fusion"]["strategy"] == "cascade"
    assert set(r["per_channel"]) == set(CHANNELS)
    assert r["degraded"] == []


def test_cascade_multimodal_seat(rec: HybridRecaller):
    """cascade席位调度: multimodal保底席位保证figure模态召回(Mod指标)."""
    r = rec.recall("文电收发与管理", "", top_k=20)
    types = {h["type"] for h in r["hits"]}
    assert "image" in types


def test_cascade_structural_section_completion(rec: HybridRecaller):
    """structural通道=章节补全: 直通命中只进新章节(不重复覆盖)."""
    r = rec.recall("结构化数据归集", "", top_k=20,
                   channels=("structural",))
    secs = [h["section"] for h in r["hits"]]
    assert len(secs) == len(set(secs))  # 章节不重复
    assert len(r["hits"]) <= 4  # 席位上限


def test_fusion_rrf_mode(rec: HybridRecaller):
    r = rec.recall("结构化数据归集", "", top_k=10, fusion="rrf")
    assert all(h["tier"] == "rrf" for h in r["hits"])


def test_channels_pluggable(rec: HybridRecaller):
    """通道可插拔: 单通道与消融配置正常工作."""
    r1 = rec.recall("结构化数据归集", "", top_k=5,
                    channels=("lexical",))
    assert r1["per_channel"]["lexical"]["n"] > 0
    assert "sparse" not in r1["per_channel"]
    r2 = rec.recall("结构化数据归集", "", top_k=10,
                    channels=tuple(c for c in CHANNELS if c != "dense"))
    assert "dense" not in r2["per_channel"]


def test_dense_index_cached(rec: HybridRecaller):
    """dense索引磁盘缓存: 二次初始化不重建(缓存命中数>0)."""
    mode = rec._ensure_dense()
    if mode == "unavailable":
        pytest.skip("BGE/dense不可用")
    assert rec.stats["dense_cache_hits"] > 0  # 全量索引来自缓存
    assert rec.stats["dense_index_s"] == 0.0  # 无重建耗时


def test_quota_postprocessing(rec: HybridRecaller):
    r = rec.recall("数据", "", top_k=20, quota=1)
    by_sec: dict[str, int] = {}
    for h in r["hits"]:
        by_sec[h["section"]] = by_sec.get(h["section"], 0) + 1
    assert all(v <= 1 for v in by_sec.values())


def test_empty_query(rec: HybridRecaller):
    assert rec.recall("", "")["hits"] == []


def test_rerank_keeps_factual_and_schema(rec: HybridRecaller):
    """重排: factual直通位保序在前, 其余带rerank_score; 输出schema完整."""
    r = rec.recall("结构化数据归集", "", top_k=10, rerank=True)
    assert r["hits"]
    assert r["fusion"].get("rerank") is True
    factual = [h for h in r["hits"] if h.get("tier") == "factual"]
    reranked = [h for h in r["hits"] if "rerank_score" in h]
    # factual在前(保序), 重排候选在后
    if factual and reranked:
        assert r["hits"].index(factual[-1]) < r["hits"].index(reranked[0])
    for h in reranked:
        assert 0.0 <= h["rerank_score"] <= 1.0


def test_lcs_cjk():
    assert _lcs_cjk("查询收件箱和发件箱接口用来做什么", "支持查询收件箱和发件箱接口的功能") \
        == "查询收件箱和发件箱接口"
    assert _lcs_cjk("短", "无关内容") == ""      # 低于min_len
    assert _lcs_cjk("", "任意") == ""


def test_extract_entity():
    # ID优先
    assert extract_entity("ZZSJHQZHFW-GN-SJHQ的合格性是什么") == "ZZSJHQZHFW-GN-SJHQ"
    # 停用词剥离后的最长段
    assert extract_entity("运维管理框架入口具体是做什么的") == "运维管理框架入口"


@pytest.mark.skipif(not HAS_DATA, reason="chunks资产缺失")
def test_detect_entity_lcs(store_fixture: EvidenceStore):
    """LCS检索反推: 保留实体连续性(优于停用词剥离)."""
    ent = detect_entity("查询收件箱和发件箱接口主要是用来做什么的", store_fixture)
    assert "收件箱" in ent and len(ent) >= 6


@pytest.mark.skipif(not HAS_DATA, reason="chunks资产缺失")
def test_structural_id_prefix_expansion(rec: HybridRecaller):
    """ID前缀层级扩展: 父实体→子ID chunks(盲区修复).

    '服务运行控制'(PZXQ-GN-FWYXKZ)的子功能chunks文本不含父名,
    仅可经ID前缀桥接召回.
    """
    res = rec._structural("服务运行控制", "")
    assert res.n > 0
    # 前缀扩展命中在前(通道内优先排序)
    by_id = rec.store._chunk_by_id()
    has_sub = any("PZXQ-GN-FWYXKZ-" in (by_id.get(h.chunk_id, {}).get("text") or "")
                  for h in res.hits)
    assert has_sub, "ID前缀子实体chunks应被召回"


@pytest.fixture(scope="module")
def store_fixture() -> EvidenceStore:
    return EvidenceStore()
