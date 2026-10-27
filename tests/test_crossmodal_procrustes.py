"""跨模态Procrustes检索实验(tools/eval_crossmodal_procrustes)的合成数据单元测试.

不加载模型/不读真实数据资产: 只测纯函数——
ID提取/前缀丢弃/gold链构造(同doc同ID)/池构造确定性(seed复现)/
查询前缀正确性/折分配/检索指标与并列AUC.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from eval_crossmodal_procrustes import (  # noqa: E402
    QUERY_PREFIX,
    ClaimRecord,
    GoldQuery,
    NodeRecord,
    RequirementRow,
    build_gold_queries,
    build_pools,
    drop_prefix_identifiers,
    evaluate_group,
    extract_identifier_strings,
    find_gold_nodes,
    load_fold_map,
    prefixed,
    rank_auc,
    split_of_doc,
)


def _requirements() -> dict[str, list[RequirementRow]]:
    return {
        "01": [
            RequirementRow("01", "AAA-BBB-CCC", "数据获取", frozenset()),
            RequirementRow("01", "CCC-DDD-EEE-FFF", "具体功能", frozenset()),
            RequirementRow("01", "CCC-DDD-EEE", "宽泛功能", frozenset()),
            RequirementRow("01", "QQQ-RRR-SSS", "B功能", frozenset({"XX-YY-ZZZ"})),
        ],
        "02": [],
    }


def _nodes() -> dict[str, list[NodeRecord]]:
    return {
        "01": [
            NodeRecord("diagram_node:NOD-a", "01", "数据获取"),
            NodeRecord("diagram_node:NOD-b", "01", "数据\n获取"),
            NodeRecord("diagram_node:NOD-c", "01", "具体功能"),
            NodeRecord("diagram_node:NOD-d", "01", "宽泛功能"),
            NodeRecord("diagram_node:NOD-e", "01", "无关节点"),
            NodeRecord("diagram_node:NOD-g", "01", "B功能"),
        ],
        "02": [
            NodeRecord("diagram_node:NOD-f", "02", "数据获取"),
        ],
    }


# ── ID提取与前缀丢弃 ─────────────────────────────────────────


def test_extract_identifier_strings_whitespace_tolerant():
    assert extract_identifier_strings("x AAA-BBB-CCC y") == {"AAA-BBB-CCC"}
    # GJB表中带空格的子ID: 规范化后合并
    assert extract_identifier_strings("PZXQ-GN-JMJCKJ- JMKF-KFGCSC") == {
        "PZXQ-GN-JMJCKJ-JMKF-KFGCSC"
    }
    # 不合规形态不提取: 段数不足/小写/数字开头
    assert extract_identifier_strings("PZXQ-GN") == set()
    assert extract_identifier_strings("abc-de-fgh") == set()
    assert extract_identifier_strings("编号3.2.1-01") == set()


def test_drop_prefix_identifiers_keeps_deepest():
    assert drop_prefix_identifiers({"AA-BB-CC", "AA-BB-CC-DD"}) == {"AA-BB-CC-DD"}
    # 互不为前缀则都保留
    assert drop_prefix_identifiers({"AA-BB-CC", "AA-BB-DD"}) == {"AA-BB-CC", "AA-BB-DD"}
    assert drop_prefix_identifiers({"AA-BB", "AA-BB-CC-DD"}) == {"AA-BB-CC-DD"}


# ── gold链构造(同doc同ID) ────────────────────────────────────


def test_find_gold_nodes_same_doc_same_id_chain():
    reqs, nodes = _requirements(), _nodes()
    # requirement_id精确匹配 + 节点换行空白归一
    assert find_gold_nodes({"AAA-BBB-CCC"}, "01", reqs, nodes) == {
        "diagram_node:NOD-a",
        "diagram_node:NOD-b",
    }
    # 同文本异doc节点不是gold(02无该需求)
    assert find_gold_nodes({"AAA-BBB-CCC"}, "02", reqs, nodes) == set()
    # 经需求行raw_text ID路由(claim ID不必等于requirement_id)
    assert find_gold_nodes({"XX-YY-ZZZ"}, "01", reqs, nodes) == {"diagram_node:NOD-g"}
    # 无匹配ID
    assert find_gold_nodes({"ZZZ-YYY-XXX"}, "01", reqs, nodes) == set()


def test_build_gold_queries_filters_and_prefix_drop():
    claims = [
        ClaimRecord("claim:CLM-1", "01", "1 | 数据获取 | AAA-BBB-CCC | 新开发"),
        ClaimRecord("claim:CLM-2", "02", "1 | 数据获取 | AAA-BBB-CCC | 新开发"),
        ClaimRecord("claim:CLM-3", "01", "CCC-DDD-EEE CCC-DDD-EEE-FFF 树表行"),
        ClaimRecord("claim:CLM-4", "01", "无ID文本"),
        ClaimRecord("claim:CLM-5", "01", "ZZZ-YYY-XXX 无匹配ID"),
        ClaimRecord("claim:CLM-6", "01", "1 | 数据获取 | AAA-BBB-CCC | 快照缺失"),
    ]
    texts = {f"claim:CLM-{i}": f"文本{i}" for i in range(1, 6)}  # CLM-6无快照文本
    queries = build_gold_queries(claims, texts, _requirements(), _nodes())
    by_id = {q.claim_occurrence_id: q for q in queries}
    assert set(by_id) == {"claim:CLM-1", "claim:CLM-3"}
    assert by_id["claim:CLM-1"].gold_nodes == {
        "diagram_node:NOD-a",
        "diagram_node:NOD-b",
    }
    # 父ID CCC-DDD-EEE 被丢弃: 只剩最深层 CCC-DDD-EEE-FFF 对应的节点
    assert by_id["claim:CLM-3"].gold_nodes == {"diagram_node:NOD-c"}
    assert by_id["claim:CLM-1"].text == "文本1"
    assert by_id["claim:CLM-1"].identifiers == frozenset({"AAA-BBB-CCC"})


# ── 池构造确定性(seed复现) ───────────────────────────────────


def _pool_queries() -> list[GoldQuery]:
    return [
        GoldQuery(
            "claim:CLM-1", "d1", "q1", "q1",
            frozenset({"AAA-BBB-CCC"}), frozenset({"diagram_node:x1"}),
        ),
        GoldQuery(
            "claim:CLM-2", "d1", "q2", "q2",
            frozenset({"AAA-BBB-CCC"}), frozenset({"diagram_node:x2"}),
        ),
        GoldQuery(
            "claim:CLM-3", "d2", "q3", "q3",
            frozenset({"AAA-BBB-CCC"}), frozenset({"diagram_node:y1"}),
        ),
    ]


def test_build_pools_deterministic_and_structural():
    reachable = {
        "d1": frozenset({"diagram_node:x1", "diagram_node:x2"}),
        "d2": frozenset({"diagram_node:y1", "diagram_node:y2"}),
        "d3": frozenset({f"diagram_node:z{i}" for i in range(30)}),
    }
    queries = _pool_queries()
    pools_a = build_pools(queries, reachable, 5, 42)
    pools_b = build_pools(queries, reachable, 5, 42)
    assert pools_a == pools_b  # 同seed复现
    everything = reachable["d1"] | reachable["d2"] | reachable["d3"]
    for query in queries:
        pool = set(pools_a[query.claim_occurrence_id])
        assert reachable[query.doc_id] <= pool  # 同doc可达节点全在池内
        negatives = pool - reachable[query.doc_id]
        assert len(negatives) == 5  # 负例数量
        assert negatives <= everything
        assert not (negatives & reachable[query.doc_id])  # 负例只来自其他doc
        assert query.gold_nodes <= pool  # gold必在池内
    # 每查询独立: 增删其他查询不改变本查询的池
    single = build_pools(queries[:1], reachable, 5, 42)
    assert single["claim:CLM-1"] == pools_a["claim:CLM-1"]


def test_build_pools_negative_count_capped_by_availability():
    reachable = {
        "d1": frozenset({"diagram_node:x1"}),
        "d2": frozenset({"diagram_node:y1", "diagram_node:y2"}),
    }
    queries = [
        GoldQuery(
            "claim:CLM-1", "d1", "q1", "q1",
            frozenset({"AAA-BBB-CCC"}), frozenset({"diagram_node:x1"}),
        ),
    ]
    pools = build_pools(queries, reachable, 50, 42)
    assert set(pools["claim:CLM-1"]) == {
        "diagram_node:x1", "diagram_node:y1", "diagram_node:y2",
    }  # 可用负例不足时全取


# ── 查询前缀正确性 ───────────────────────────────────────────


def test_query_prefix_is_bge_instruction():
    assert QUERY_PREFIX == "为这个句子生成表示以用于检索相关文章："
    assert prefixed("测试查询") == QUERY_PREFIX + "测试查询"
    assert prefixed("") == QUERY_PREFIX


# ── 折分配 ───────────────────────────────────────────────────


def test_split_of_doc_fold_map_and_sha1_fallback():
    fold_map = {"01": 0, "02": 2, "03": 1}
    assert split_of_doc("01", fold_map) == "test"
    assert split_of_doc("02", fold_map) == "train"
    assert split_of_doc("03", fold_map) == "dev"
    # 未覆盖doc: sha1回退且确定
    first = split_of_doc("16", fold_map)
    assert split_of_doc("16", fold_map) == first
    # 回退分布在16个doc上可用(同时含train与test)
    splits = {split_of_doc(f"{i:02d}", None) for i in range(1, 17)}
    assert "train" in splits and "test" in splits


def test_load_fold_map_picks_latest_by_timestamp(tmp_path: Path):
    def make_run(name: str, fold_map: object) -> Path:
        path = tmp_path / name
        path.mkdir()
        config = {"script": "train_shared_projection", "config": {"fold_map": fold_map}}
        (path / "config.json").write_text(json.dumps(config), encoding="utf-8")
        return path

    make_run("train_shared_projection_zzz_20260101_000000", {"01": 0})  # 旧但哈希大
    latest = make_run("train_shared_projection_aaa_20260202_000000", {"02": 2})
    fold_map, source = load_fold_map(tmp_path)
    assert fold_map == {"02": 2}  # 按时间戳而非哈希字典序
    assert source == str(latest / "config.json")


def test_load_fold_map_fallback_when_absent(tmp_path: Path):
    (tmp_path / "train_shared_projection_abc_20260101_000000").mkdir()  # 无config.json
    fold_map, source = load_fold_map(tmp_path)
    assert fold_map is None
    assert "fallback" in source
    empty_map, empty_source = load_fold_map(tmp_path / "nonexistent")
    assert empty_map is None and "fallback" in empty_source


# ── 指标 ─────────────────────────────────────────────────────


def test_rank_auc_handles_ties():
    # 正0.9胜负0.8; 正0.8与负0.8并列计0.5 -> AUC=0.75
    assert rank_auc([0.9, 0.8, 0.8], [1, 0, 1]) == 0.75
    assert rank_auc([1.0, 0.0], [1, 0]) == 1.0
    assert rank_auc([0.5], [1]) is None  # 无负样本
    assert rank_auc([0.5, 0.6], [1, 1]) is None  # 无正样本


def test_evaluate_group_metrics_and_tie_break():
    pools = {
        "claim:CLM-1": ("diagram_node:n1", "diagram_node:n2", "diagram_node:n3"),
        "claim:CLM-2": ("diagram_node:n4", "diagram_node:n5"),
    }
    golds = {
        "claim:CLM-1": frozenset({"diagram_node:n1"}),
        "claim:CLM-2": frozenset({"diagram_node:n5"}),
    }
    scores = {
        "claim:CLM-1": [0.9, 0.5, 0.4],  # gold rank 1
        "claim:CLM-2": [0.6, 0.3],  # gold n5 rank 2
    }
    metrics = evaluate_group(pools, scores, golds, ks=(1, 5, 10), mrr_k=10)
    assert metrics["recall@1"] == 0.5
    assert metrics["recall@5"] == 1.0
    assert metrics["mrr@10"] == (1.0 + 0.5) / 2
    # 池化AUC: 正样本{0.9, 0.3}, 负样本{0.5, 0.4, 0.6} -> 3/6
    assert metrics["auc"] == 0.5
    # 得分并列按节点id字典序决胜: n4排在n5前, gold仍在rank 2
    tie = evaluate_group(
        pools,
        {"claim:CLM-1": [0.9, 0.5, 0.4], "claim:CLM-2": [0.7, 0.7]},
        golds,
        ks=(1,),
        mrr_k=10,
    )
    assert tie["recall@1"] == 0.5
