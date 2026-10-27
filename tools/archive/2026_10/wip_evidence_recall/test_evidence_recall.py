"""evidence_recall框架测试: 全确定性(FakeEncoder/FakeReranker, 无模型).

覆盖: 物证库构建/分段/IDF; 语义单元头数学(max×IDF);
词面头BM25; 场景路由召回; 两阶段精排(融合+直通); 端到端管线.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_association.evidence_recall import (  # noqa: E402
    EvidenceHit,
    EvidenceRecallPipeline,
    EvidenceStore,
    LexicalHead,
    MultiHeadRecall,
    SemanticUnitHead,
    UnitFocusedRerank,
    tokenize,
)

DIM = 32


class FakeEncoder:
    """确定性语义编码器: token袋向量(共享token→高余弦, 与真实编码器
    的相关性单调一致, 使头排序语义可测)."""

    def embed(self, texts):
        out = {}
        for t in texts:
            v = np.zeros(DIM, dtype=np.float32)
            for tok in tokenize(t):
                h = int(hashlib.sha256(tok.encode()).hexdigest()[:8], 16)
                v[h % DIM] += 1.0
            n = float(np.linalg.norm(v))
            out[t] = (v / n if n > 1e-8 else v).tolist()
        return out


class FakeReranker:
    """确定性精排器: 分数=查询与doc的二元组重叠率."""

    name = "fake_cross"

    def score(self, pairs):
        out = []
        for q, d in pairs:
            qb = set(tokenize(q))
            db = set(tokenize(d))
            out.append(len(qb & db) / max(len(qb), 1))
        return out


def _mini_ure():
    return [
        {"chunk_id": "doc1_T01", "type": "table", "title": "接口数据一览表",
         "units": ["接口数据一览表",
                   "文档编号=GJB 438B 标题=规范 编写单位=总装备部",
                   "文档编号=GJB 438C 标题=要求 编写单位=装备发展部"]},
        {"chunk_id": "doc1_T02", "type": "table", "title": "合格性表",
         "units": ["合格性表", "编号=Q01 方法=审查 阶段=需求",
                   "编制单位=总装备部"]},
        {"chunk_id": "doc1_I01", "type": "image", "title": "图3.1 系统组成",
         "units": ["图3.1 系统组成", "数据获取", "传输服务"]},
    ]


# ── EvidenceStore ─────────────────────────────────────────

def test_store_build_and_segments():
    s = EvidenceStore.from_ure(_mini_ure())
    assert s.n_owners == 3
    # T01: title+2行 | T02: title+2行 | I01: title+3元素
    assert s.n_units == 10
    # 单元按owner聚集
    for owner in s.owners:
        seg = s.segments[owner]
        assert all(u.owner == owner for u in s.units[seg[0]:seg[1]])
    # 池过滤
    assert set(s.pool("table_row")) == {"doc1_T01", "doc1_T02"}
    assert s.pool("image_element") == ["doc1_I01"]


def test_store_idf():
    s = EvidenceStore.from_ure(_mini_ure())
    idf = s.idf()
    # "合格性表"只在1/3个owner出现 → 原始比值3(log在头内施加)
    assert idf["合格性表"] == pytest.approx(3.0)
    # "编制单位=总装备部"在2/3个owner(T01/T02)出现 → 1.5
    assert idf["编制单位=总装备部"] == pytest.approx(1.5)
    assert min(idf.values()) == pytest.approx(1.5)


# ── SemanticUnitHead ──────────────────────────────────────

def test_semantic_head_math():
    """O1-unit数学: owner分 = max_u(sim×IDF); top_units对齐."""
    enc = FakeEncoder()
    s = EvidenceStore.from_ure(_mini_ure())
    head = SemanticUnitHead(enc).build(s)
    sc = head.score_query("接口数据一览表")
    assert sc.shape == (3,)
    # 查询=表头文本 → 该表语义匹配最强(自身单元与查询编码相同)
    assert int(np.argmax(sc)) == s.owners.index("doc1_T01")
    # top_units属于该owner
    tops = head.top_units("GJB 438B 编写单位", "doc1_T01", topn=2)
    assert len(tops) == 2
    assert any("GJB 438B" in t for t in tops)


def test_semantic_head_requires_build():
    head = SemanticUnitHead(FakeEncoder())
    with pytest.raises(RuntimeError):
        head.score_query("q")


# ── LexicalHead ───────────────────────────────────────────

def test_lexical_head_bm25():
    s = EvidenceStore.from_ure(_mini_ure())
    head = LexicalHead().build(s)
    sc = head.score("系统组成 数据获取")
    assert int(np.argmax(sc)) == s.owners.index("doc1_I01")
    sc2 = head.score("合格性 方法")
    assert int(np.argmax(sc2)) == s.owners.index("doc1_T02")
    # 无词面重叠 → 全零
    assert float(np.max(head.score("zzz qqq"))) == pytest.approx(0.0)


# ── MultiHeadRecall ───────────────────────────────────────

def test_recall_scene_routing():
    """table池路由语义头; image池路由词面头; 池外owner被屏蔽."""
    s = EvidenceStore.from_ure(_mini_ure())
    rc = MultiHeadRecall(s, FakeEncoder())
    r = rc.recall("接口数据一览表 GJB", pool="table", topk=3)
    assert r.hits[0].owner == "doc1_T01"
    assert all(h.owner != "doc1_I01" for h in r.hits)
    r2 = rc.recall("图3.1 系统组成 数据获取", pool="image", topk=1)
    assert r2.hits[0].owner == "doc1_I01"
    assert r2.hits[0].head == "lexical"


def test_recall_fusion_zmax():
    s = EvidenceStore.from_ure(_mini_ure())
    rc = MultiHeadRecall(s, FakeEncoder())
    r = rc.recall("接口数据", pool="table", topk=3, fusion="zmax")
    assert len(r.hits) == 2
    assert set(r.scores) == {"semantic_unit", "lexical"}


# ── UnitFocusedRerank ─────────────────────────────────────

def test_rerank_passthrough_keeps_order():
    s = EvidenceStore.from_ure(_mini_ure())
    rc = MultiHeadRecall(s, FakeEncoder())
    r = rc.recall("接口数据一览表", pool="table", topk=3)
    out = UnitFocusedRerank(reranker=None).rerank("接口数据一览表", r, s)
    assert [h.owner for h in out] == [h.owner for h in r.hits]
    assert all(isinstance(h, EvidenceHit) for h in out)


def test_rerank_fake_reorders():
    """词面精排器把词面重叠高的候选顶到首位."""
    s = EvidenceStore.from_ure(_mini_ure())
    rc = MultiHeadRecall(s, FakeEncoder())
    r = rc.recall("合格性 方法 审查", pool="table", topk=2)
    out = UnitFocusedRerank(reranker=FakeReranker(), blend=0.0).rerank(
        "合格性 方法 审查", r, s)
    assert out[0].owner == "doc1_T02"
    assert out[0].head == "fake_cross"


# ── Pipeline(端到端) ─────────────────────────────────────

def test_pipeline_end_to_end():
    pipe = EvidenceRecallPipeline(
        _mini_ure(), encoder=FakeEncoder(), reranker=FakeReranker())
    hits = pipe.search("接口数据一览表 GJB 438B 编写单位", topk=2)
    assert hits[0].owner == "doc1_T01"
    assert hits[0].kind == "table_row"
    assert hits[0].title == "接口数据一览表"
    assert hits[0].best_units

    img_hits = pipe.search("图3.1 系统组成", pool="image", topk=1)
    assert img_hits[0].owner == "doc1_I01"

    no_rr = pipe.search("接口数据一览表", topk=2, rerank=False)
    assert no_rr[0].head in ("semantic_unit", "lexical")


def test_pipeline_lazy_encoder_injection():
    """auto_reranker=False: 不加载真实精排器(召回序直通)."""
    pipe = EvidenceRecallPipeline(_mini_ure(), encoder=FakeEncoder(),
                                  auto_reranker=False)
    hits = pipe.search("GJB", topk=1)
    assert hits
    assert hits[0].head in ("semantic_unit", "lexical")
