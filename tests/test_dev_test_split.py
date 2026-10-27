"""dev/test冻结切分的契约测试 (P0 held-out评测体制改革).

覆盖:
  - 确定性: 同seed两次构建逐字段一致(重跑不漂移)
  - 冻结文件加载与不变量: 45/46, 无交集, 并集=全集, 主题簇不跨侧(防泄漏)
  - silver分层: 两侧S/R分布与冻结文件一致
  - question→topic聚类规则的基本行为
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from tools.build_dev_test_split import (  # noqa: E402
    QA_FROZEN,
    SEED,
    SILVER,
    SPLIT_PATH,
    build_split,
    load_corpora,
    load_split,
    question_topic,
)


@pytest.fixture(scope="module")
def corpora():
    return load_corpora()


@pytest.fixture(scope="module")
def split(corpora):
    rows, silver = corpora
    return build_split(rows, silver, seed=SEED)


def test_topic_rules_assign_expected_clusters() -> None:
    assert question_topic("BLOB数据插入用例中涉及的主要参与者有哪些？") \
        == "blob_data"
    assert question_topic("连接池管理功能支持哪些操作") == "conn_pool"
    assert question_topic("热点数据缓存功能有什么特点") == "hot_cache"
    assert question_topic("完全无关的问题") == "misc"


def test_split_is_deterministic(corpora) -> None:
    rows, silver = corpora
    first = build_split(rows, silver, seed=SEED)
    second = build_split(rows, silver, seed=SEED)
    assert first == second


def test_split_sizes_and_disjointness(split) -> None:
    assert len(split["dev"]) == 45
    assert len(split["test"]) == 46
    assert not set(split["dev"]) & set(split["test"])
    all_ids = sorted(split["cluster_map"])
    assert sorted(split["dev"] + split["test"]) == all_ids
    assert len(all_ids) == 91


def test_split_silver_stratification(split) -> None:
    dev = split["silver_distribution"]["dev"]
    test = split["silver_distribution"]["test"]
    assert dev == {"support": 3, "refute": 4, "not_in_evidence": 38}
    assert test == {"support": 3, "refute": 4, "not_in_evidence": 39}


def test_no_topic_spans_both_sides(split) -> None:
    dev_topics = {split["cluster_map"][iid] for iid in split["dev"]}
    test_topics = {split["cluster_map"][iid] for iid in split["test"]}
    assert not dev_topics & test_topics
    for topic, side in split["cluster_assignment"].items():
        expected = "dev" if topic in dev_topics else "test"
        assert side == expected


def test_cluster_map_covers_every_row(split, corpora) -> None:
    rows, _silver = corpora
    assert set(split["cluster_map"]) == {row["instance_id"] for row in rows}


def test_frozen_split_file_loads_and_matches_rebuild(
        split, corpora) -> None:
    if not (QA_FROZEN.exists() and SILVER.exists() and SPLIT_PATH.exists()):
        pytest.skip("冻结切分/语料资产不在本检出中")
    frozen = load_split()
    assert frozen == split


def test_load_split_rejects_corrupted_file(tmp_path) -> None:
    good = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    overlapping = {**good, "test": good["dev"][:46]}
    bad_path = tmp_path / "bad_split.json"
    bad_path.write_text(json.dumps(overlapping), encoding="utf-8")
    with pytest.raises(ValueError, match="交集"):
        load_split(bad_path)
    # 尺寸破坏但并集保持完整: 把一个test id搬到dev侧 (dev=46, test=45)
    moved = good["test"][:45]
    wrong_size = {**good, "test": moved,
                  "dev": sorted(good["dev"] + good["test"][45:])}
    size_path = tmp_path / "size_split.json"
    size_path.write_text(json.dumps(wrong_size), encoding="utf-8")
    with pytest.raises(ValueError, match="尺寸"):
        load_split(size_path)
