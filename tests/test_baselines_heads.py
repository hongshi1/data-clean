"""baselines包测试: BM25-unit头与Token-MaxSim头(全确定性, 无模型).

复用test_evidence_recall的FakeEncoder模式; Token-MaxSim用
FakeTokenEncoder(每token确定性向量, 共享token→正相似).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_linking.baselines import (  # noqa: E402
    BASELINE_NAMES,
    BM25UnitHead,
    make_baseline,
    TokenMaxSimHead,
)
from algorithms.context_linking.evidence_recall import (  # noqa: E402
    EvidenceStore,
    LexicalHead,
    tokenize,
)


def _mini_ure():
    return [
        {"chunk_id": "doc1_T01", "type": "table", "title": "接口数据一览表",
         "units": ["接口数据一览表",
                   "文档编号=GJB 438B 标题=规范 编写单位=总装备部",
                   "文档编号=GJB 438C 标题=要求 编写单位=装备发展部"]},
        {"chunk_id": "doc1_T02", "type": "table", "title": "合格性表",
         "units": ["合格性表", "编号=Q01 方法=审查 阶段=需求"]},
        {"chunk_id": "doc1_I01", "type": "image", "title": "图3.1 系统组成",
         "units": ["图3.1 系统组成", "数据获取", "传输服务"]},
    ]


class FakeTokenEncoder:
    """确定性token编码器: 构造时锁定词表, 每个token→one-hot基向量
    (无碰撞; 共享token→cos=1, 词表外token→零向量cos=0)."""

    def __init__(self, vocab: list[str]) -> None:
        self._basis = {t: i for i, t in enumerate(sorted(set(vocab)))}
        self._dim = max(len(self._basis), 1)

    def embed_tokens(self, texts, max_length=None):
        out = {}
        for t in texts:
            toks = tokenize(t)
            vecs = []
            for tok in toks:
                v = [0.0] * self._dim
                if tok in self._basis:
                    v[self._basis[tok]] = 1.0
                vecs.append(v)
            if not vecs:
                vecs = [[0.0] * self._dim]
            out[t] = vecs
        return out


def _fake_token_enc(store, queries: list[str]) -> FakeTokenEncoder:
    """从物证库+查询构造词表(确定性)."""
    vocab: list[str] = []
    for u in store.units:
        vocab.extend(tokenize(u.text))
    for q in queries:
        vocab.extend(tokenize(q))
    return FakeTokenEncoder(vocab)


# ── BM25UnitHead ──────────────────────────────────────────

def test_bm25_unit_head():
    """单元级BM25: 查询命中表内特定行 → 该owner最高分."""
    s = EvidenceStore.from_ure(_mini_ure())
    head = BM25UnitHead().build(s)
    sc = head.score_query("方法=审查 阶段")
    assert int(np.argmax(sc)) == s.owners.index("doc1_T02")
    # 无重叠 → owner分=-1e9(单元全零, max仍取0? 单元BM25=0 → max=0)
    sc2 = head.score_query("zzz")
    assert float(np.max(sc2)) <= 0.0


def test_bm25_unit_vs_doc_distinction():
    """单元级与文档级的数学差异: 单元池≠文档池 → 分数不同(协议不同)."""
    s = EvidenceStore.from_ure(_mini_ure())
    uh = BM25UnitHead().build(s)
    dh = LexicalHead().build(s)
    q = "GJB 438B 编写单位 总装备部"
    su = uh.score_query(q)
    sd = dh.score_query(q)
    assert not np.allclose(su, sd)


def test_bm25_unit_requires_build():
    with pytest.raises(RuntimeError):
        BM25UnitHead().score_query("q")


# ── TokenMaxSimHead ───────────────────────────────────────

def test_token_maxsim_numpy():
    """MaxSim: 共享token的owner得分高; 词表外token→精确零分."""
    s = EvidenceStore.from_ure(_mini_ure())
    enc = _fake_token_enc(s, ["系统组成 数据获取", "zzz qqq"])
    head = TokenMaxSimHead(enc).build(s)
    sc = head.score_query("系统组成 数据获取")
    assert int(np.argmax(sc)) == s.owners.index("doc1_I01")
    # 词表外token(无共享) → 精确零
    sc2 = head.score_query("zzz qqq")
    assert float(np.max(sc2)) == pytest.approx(0.0)


def test_token_maxsim_requires_build():
    s = EvidenceStore.from_ure(_mini_ure())
    enc = _fake_token_enc(s, ["q"])
    with pytest.raises(RuntimeError):
        TokenMaxSimHead(enc).score_query("q")


# ── 注册表工厂 ────────────────────────────────────────────

def test_make_baseline_registry():
    s = EvidenceStore.from_ure(_mini_ure())
    bm = make_baseline("BM25-doc", s)
    bu = make_baseline("BM25-unit", s)
    # 稠密/Token需注入 → 报ValueError
    with pytest.raises(ValueError):
        make_baseline("B1-dense", s)
    with pytest.raises(ValueError):
        make_baseline("Token-MaxSim", s)
    with pytest.raises(KeyError):
        make_baseline("不存在的", s)
    assert bm.score_query("接口数据").shape == (3,)
    assert bu.score_query("合格性").shape == (3,)
    assert set(BASELINE_NAMES) >= {"BM25-doc", "BM25-unit",
                                   "B1-dense", "Token-MaxSim"}


def test_heads_uniform_interface():
    """所有baseline头实现score_query(query)→(n_owners,)向量."""
    s = EvidenceStore.from_ure(_mini_ure())
    heads = [
        make_baseline("BM25-doc", s),
        make_baseline("BM25-unit", s),
        TokenMaxSimHead(_fake_token_enc(s, ["接口数据 GJB"])).build(s),
    ]
    for h in heads:
        v = h.score_query("接口数据 GJB")
        assert isinstance(v, np.ndarray)
        assert v.shape == (s.n_owners,)
        assert np.all(np.isfinite(v))
