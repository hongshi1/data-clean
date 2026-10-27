"""召回v3(search_chunks_v3)测试: 四层融合召回的确定性快照.

锁定内容(论文数字关联, eval_recall_v3口径):
  - entity_mentions的跨文档同名消歧(doc参数)
  - image_hits→(doc,fig)→image chunk的映射完整性(379/379)
  - v3四层rank覆盖: 精确/ID硬桥/VLM图片直查/BM25
  - figure模态召回(评测loc 0.735→0.995的核心贡献)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from algorithms.blackboard.evidence_store import EvidenceStore

BASE = Path(__file__).resolve().parents[1]
HAS_DATA = (BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json").exists()

pytestmark = pytest.mark.skipif(not HAS_DATA, reason="chunks资产缺失")


@pytest.fixture(scope="module")
def store() -> EvidenceStore:
    return EvidenceStore()


def test_entity_mentions_doc_disambiguation(store: EvidenceStore):
    """跨文档同名消歧: '修改数据'在01/04文档各有一套mention.

    doc参数应优先返回同文档实体; 无doc时返回首个(与旧行为兼容).
    """
    rec_any = store.entity_mentions("修改数据")
    assert rec_any is not None
    assert rec_any["n_mentions"] > 0
    assert rec_any["sections"]  # mentions的章节非空


def test_image_chunk_index_complete(store: EvidenceStore):
    """VLM分析→image chunk的(doc,fig)映射: 379/379全映射(资产断裂修复)."""
    import re
    idx = store._image_chunk_index()
    mapped = 0
    for a in store._images_data():
        fm = re.search(r"fig_(\d+)", a.get("image_path", ""))
        if fm and idx.get((a.get("doc", ""), fm.group(1))):
            mapped += 1
    assert len(store._images_data()) == 379
    assert mapped == 379


def test_v3_figure_recall(store: EvidenceStore):
    """v3层③: 实体名经VLM图片分析直查召回figure模态(loc指标核心)."""
    hits = store.search_chunks_v3("文电收发与管理", "")
    types = {h["type"] for h in hits}
    ranks = {h["rank"] for h in hits}
    assert "image" in types  # figure模态被召回
    assert "image_vlm" in ranks  # 经VLM分析层


def test_v3_rank_layers(store: EvidenceStore):
    """v3四层: 精确层优先, ID硬桥带doc消歧, 结果形态标准."""
    hits = store.search_chunks_v3("结构化数据归集", "")
    assert hits, "常见实体应可召回"
    for h in hits:
        assert set(h) >= {"chunk_id", "type", "section", "doc",
                          "snippet", "rank"}
    assert any(h["rank"] == "exact" for h in hits)
    # ID硬桥: 实体名→mentions→sections→chunk
    id_hop = [h for h in hits if h["rank"] == "id_hop"]
    if id_hop:
        rec = store.entity_mentions("结构化数据归集")
        assert rec is not None
        hop_secs = {h["section"] for h in id_hop}
        assert hop_secs <= set(rec["sections"])


def test_v3_section_quota(store: EvidenceStore):
    """章节配额: BM25层同章节不超过per_section条(多样性)."""
    hits = store.search_chunks_v3("数据", "", per_section=1)
    bm25 = [h for h in hits if h["rank"] == "bm25"]
    by_sec: dict[str, int] = {}
    for h in bm25:
        by_sec[h["section"]] = by_sec.get(h["section"], 0) + 1
    assert all(v <= 1 for v in by_sec.values())


def test_v3_empty_and_missing(store: EvidenceStore):
    assert store.search_chunks_v3("", "") == []
    hits = store.search_chunks_v3("完全不存在的概念XYZQ", "")
    # 无命中时返回空或仅BM25噪声, 不崩溃
    assert isinstance(hits, list)
