"""DocQueryIndex单元测试: 标准形态/宿主召回/确定性/优雅缺失.

合成索引(tmp_path注入)覆盖确定性内核; 真实资产(600 chunk阶段)
做冒烟测试(skipif缺失)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.blackboard.doc_query_index import (  # noqa: E402
    DOC_QUERIES_PATH,
    DocQueryIndex,
)


def _make_index(tmp_path: Path) -> DocQueryIndex:
    qpath = tmp_path / "dq.json"
    cpath = tmp_path / "ch.json"
    chunks = [
        {"chunk_id": "docA_T01", "type": "text", "section": "3.3.5.1",
         "doc": "docA", "text": "收件箱和发件箱接口的子功能说明"},
        {"chunk_id": "docA_T02", "type": "table", "section": "3.2",
         "doc": "docA", "text": "接口合格性表"},
    ]
    cpath.write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
    qpath.write_text(json.dumps({
        "docA_T01": ["收件箱和发件箱接口包含哪些子功能",
                     "收件箱和发件箱接口在哪个章节定义"],
        "docA_T02": ["接口合格性表在哪"],
    }, ensure_ascii=False), encoding="utf-8")
    return DocQueryIndex(queries_path=qpath, chunks_path=cpath)


def test_search_returns_host_chunk_with_standard_shape(tmp_path: Path) -> None:
    idx = _make_index(tmp_path)
    hits = idx.search("收件箱和发件箱接口")
    assert hits, "应命中假想查询并返回宿主chunk"
    top = hits[0]
    assert top["chunk_id"] == "docA_T01"
    assert top["section"] == "3.3.5.1"
    assert top["type"] == "text"
    assert top["doc"] == "docA"
    assert top["rank"] == 1
    assert top["score"] > 0
    assert "收件箱" in top["snippet"]   # snippet=命中的假想查询


def test_search_deterministic_and_topk(tmp_path: Path) -> None:
    idx = _make_index(tmp_path)
    a = idx.search("接口")
    b = idx.search("接口")
    assert [h["chunk_id"] for h in a] == [h["chunk_id"] for h in b]
    assert len(idx.search("接口", top_k=1)) == 1
    assert idx.n_chunks == 2
    assert idx.indexed_chunk_ids == {"docA_T01", "docA_T02"}


def test_missing_or_invalid_assets_graceful(tmp_path: Path) -> None:
    idx = DocQueryIndex(queries_path=tmp_path / "none.json",
                        chunks_path=tmp_path / "none2.json")
    assert idx.search("任何查询") == []
    assert idx.n_chunks == 0
    bad = tmp_path / "bad.json"
    bad.write_text("[1,2,3]", encoding="utf-8")   # 非dict格式
    idx2 = DocQueryIndex(queries_path=bad, chunks_path=tmp_path / "n.json")
    assert idx2.search("任何查询") == []


def test_orphan_queries_dropped(tmp_path: Path) -> None:
    """chunk_id不在chunks资产中的孤儿条目应被忽略."""
    qpath = tmp_path / "dq.json"
    cpath = tmp_path / "ch.json"
    cpath.write_text(json.dumps(
        [{"chunk_id": "c1", "type": "text", "section": "3.1",
          "doc": "d", "text": "x"}], ensure_ascii=False), encoding="utf-8")
    qpath.write_text(json.dumps(
        {"c1": ["告警处理功能在哪里"], "GONE": ["孤儿查询"]},
        ensure_ascii=False), encoding="utf-8")
    idx = DocQueryIndex(queries_path=qpath, chunks_path=cpath)
    hits = idx.search("告警处理功能")
    assert [h["chunk_id"] for h in hits] == ["c1"]
    assert idx.n_chunks == 1


def test_real_asset_smoke() -> None:
    """真实doc_queries资产冒烟(生成阶段为--limit 600, 故skipif)."""
    import pytest

    if not DOC_QUERIES_PATH.exists():
        pytest.skip("doc_queries.json未生成(先跑gen_hypothetical_queries.py)")
    idx = DocQueryIndex()
    assert idx.n_chunks > 0
    hits = idx.search("接口", top_k=5)
    assert len(hits) <= 5
    for h in hits:
        assert {"chunk_id", "type", "section", "doc", "snippet",
                "rank", "score"} <= set(h)
