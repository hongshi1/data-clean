"""场景五图谱交互API回归测试(graph_api.py: activate + node_detail).

确定性内核快照: body数据通路完全自包含(不依赖内置数据集文件);
内置数据集通路覆盖C-3同图异判跨模态冲突(数据集受MANIFEST保护).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1] / "deploy" / "nkuDataProject" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from scenarios.kg_supervision import graph_api  # noqa: E402

# ---- 自包含body数据: 口罩场景, 含C-3式同图异判 ----
_BODY = {
    "qa_records": [
        {"qa_id": "m0", "question": "判断图片中人员是否佩戴口罩",
         "answer": 1, "evidence": "画面中人员面部无口罩覆盖",
         "task": "口罩佩戴检测", "image_id": "mask_a.jpg", "hazard_level": "一般"},
        {"qa_id": "m1", "question": "判断图片中人员是否佩戴口罩",
         "answer": 0, "evidence": "画面中人员正确佩戴医用口罩",
         "task": "口罩佩戴检测", "image_id": "mask_b.jpg"},
        {"qa_id": "m2", "question": "判断图片中人员是否佩戴口罩",
         "answer": 0, "evidence": "画面中所有人员均佩戴口罩",
         "task": "口罩佩戴检测", "image_id": "mask_a.jpg"},  # C-3: 同图异判
    ],
    "visual_chunks": [
        {"chunk_id": "mA#p1", "type": "person", "label": "人员#1",
         "bbox": [100.0, 200.0, 400.0, 800.0], "det_conf": 0.91,
         "pose": {"state": "standing", "prone_like": False, "head_down": False},
         "image_id": "mask_a.jpg"},
        {"chunk_id": "mA#ppe1", "type": "ppe", "label": "口罩",
         "ppe_class": "NO-Mask", "wearing_state": "not_wearing",
         "bbox": [180.0, 210.0, 320.0, 260.0], "det_conf": 0.85,
         "matched_person": "mA#p1", "image_id": "mask_a.jpg"},
    ],
    "analyzed_images": ["mask_a.jpg", "mask_b.jpg"],
}


def test_extract_relation_triples_captures_negation() -> None:
    elements = [{"kind": "qa_answer", "qa_id": "1",
                 "question": "判断图片中是否有人员未佩戴安全帽",
                 "text": "画面中右侧人员未佩戴安全帽", "answer": 1,
                 "image_id": "x.jpg"}]
    triples = graph_api.extract_relation_triples(elements)
    by_key = {(t["source"], t["relation"], t["target"]): t for t in triples}
    t = by_key[("人员", "未佩戴", "安全帽")]
    assert t["negated"] is True
    assert t["rel_en"] == "wearing"
    assert t["id"] == "rel_person_neg_wearing_helmet"
    assert t["qa_ids"] == ["1"]
    assert t["evidence"]  # 证据子句随行
    # graph.py原始提取的否定盲区: 主语吞掉"未"仍能匹配到人员, 但negated错判
    assert ("人员", "佩戴", "安全帽") not in by_key


def test_activate_returns_browser_contract() -> None:
    r, status = graph_api.handle_activate({"query": "口罩", "k": 2, "top_k": 12,
                                           **_BODY})
    assert status == 200
    assert r["ok"] is True
    assert r["center"]["id"] == "ent_mask"
    assert r["center"]["label"] == "口罩"
    assert r["center"]["type"] == "entity"
    # 五要素齐备 + 四个固定分组键
    for key in ("center", "related", "groups", "edges", "stats"):
        assert key in r
    assert set(r["groups"]) == {"QA", "PERSON", "PPE", "RELATION"}
    # QA组载荷: question/answer/evidence
    qa = r["groups"]["QA"][0]
    assert qa["payload"]["question"]
    assert qa["payload"]["answer"] in (0, 1)
    assert qa["payload"]["evidence"]
    # PERSON组载荷: bbox/det_conf/pose
    person = r["groups"]["PERSON"][0]
    assert person["payload"]["bbox"] == [100.0, 200.0, 400.0, 800.0]
    assert person["payload"]["det_conf"] == 0.91
    assert person["payload"]["pose"]["state"] == "standing"
    # PPE组载荷: ppe_class/wearing_state
    ppe = r["groups"]["PPE"][0]
    assert ppe["payload"]["ppe_class"] == "NO-Mask"
    assert ppe["payload"]["wearing_state"] == "not_wearing"
    # RELATION组载荷: source/target/relation
    rel = r["groups"]["RELATION"][0]
    assert rel["payload"]["source"] == "人员"
    assert rel["payload"]["target"] == "口罩"
    assert rel["payload"]["relation"] == "佩戴"
    # related: 实体带id_str/name/rel/score
    assert r["related"] and r["related"][0]["id_str"]
    assert {"source", "target", "rel", "w"} <= set(r["edges"][0])
    assert r["stats"]["by_type"] == {"QA": 3, "PERSON": 1, "PPE": 1, "RELATION": 1}
    assert r["stats"]["data_source"] == "body"
    # 中心不出现在内容分组里
    assert all(it["id"] != "ent_mask"
               for lst in r["groups"].values() for it in lst)


def test_cross_modal_conflict_detection() -> None:
    """C-3式同图异判: 同图两条clean/violation断言, 冻结观测只能支持其一."""
    d, status = graph_api.handle_node_detail({"node_id": "ent_口罩",
                                              "node_type": "entity", **_BODY})
    assert status == 200 and d["ok"]
    cm = d["structured"]["cross_modal"]
    by_qa = {x["qa_id"]: x for x in cm}
    assert by_qa["m0"]["observation_status"] == "supported"  # 未佩戴↔NO-Mask
    assert by_qa["m2"]["observation_status"] == "refuted"    # 均佩戴↔NO-Mask
    assert by_qa["m1"]["observation_status"] == "NIE"        # mask_b无Chunk
    assert by_qa["m0"]["linked_chunks"] == ["mA#ppe1"]
    assert "PPE检测: 未佩戴×1 @mask_a.jpg" == by_qa["m0"]["observation"]


def test_node_detail_entity_contract() -> None:
    d, _ = graph_api.handle_node_detail({"node_id": "ent_口罩",
                                         "node_type": "entity", **_BODY})
    assert d["node"] == {"id": "ent_mask", "label": "口罩", "type": "entity"}
    s = d["structured"]
    assert s["kind"] == "entity"
    assert s["name"] == "口罩"
    assert s["type"] == "mask"
    assert len(s["qa_mentions"]) == 3
    assert {m["qa_id"] for m in s["qa_mentions"]} == {"m0", "m1", "m2"}
    # 算法检测结果: bbox/置信度/PPE状态
    chunk = s["visual_chunks"][0]
    assert chunk["ppe_class"] == "NO-Mask"
    assert chunk["wearing_state"] == "not_wearing"
    assert chunk["bbox"] == [180.0, 210.0, 320.0, 260.0]
    assert chunk["det_conf"] == 0.85
    # 特征面板: 模态链计数 + 关系方向(口罩为三元组宾语 → ←)
    f = d["features"]
    assert f["modality_links"] == {"QA": 3, "PERSON": 1, "PPE": 1, "RELATION": 1}
    assert f["relations"] == [{"direction": "←", "target": "人员",
                               "rel": "佩戴", "negated": False,
                               "target_id": "ent_person"}]


def test_node_detail_other_kinds() -> None:
    # QA节点: 问题/回答/证据 + 同图Chunk + 跨模态核验
    d, _ = graph_api.handle_node_detail({"node_id": "qa_m0",
                                         "node_type": "qa_answer", **_BODY})
    s = d["structured"]
    assert s["kind"] == "qa_answer"
    assert s["question"] == "判断图片中人员是否佩戴口罩"
    assert s["answer"] == 1
    assert len(s["visual_chunks"]) == 2  # mask_a.jpg上的person+pe
    assert s["cross_modal"][0]["observation_status"] == "supported"
    # 视觉Chunk节点(裸chunk_id解析): 算法检测结果 + 接地实体 + 同图QA
    d, _ = graph_api.handle_node_detail({"node_id": "mA#ppe1",
                                         "node_type": "visual", **_BODY})
    s = d["structured"]
    assert s["kind"] == "visual_chunk"
    assert s["ppe_class"] == "NO-Mask"
    assert s["grounded_entities"][0]["id"] == "ent_mask"
    assert len(s["qa_mentions"]) == 2  # m0与m2同图
    # 关系三元组节点
    d, _ = graph_api.handle_node_detail({"node_id": "rel_person_wearing_mask",
                                         "node_type": "relation", **_BODY})
    s = d["structured"]
    assert s["kind"] == "relation"
    assert (s["source"], s["relation"], s["target"]) == ("人员", "佩戴", "口罩")
    assert s["negated"] is False


def test_task_word_fallback_center_is_most_mentioned_entity() -> None:
    """任务词查询(无实体命中) → 借道QA提及实体, 中心取提及最多者."""
    body = {"qa_records": _BODY["qa_records"] + [
        {"qa_id": "f0", "question": "判断图片中是否存在人员睡岗行为",
         "answer": 1, "evidence": "人员趴伏于工位桌面且闭眼",
         "task": "睡岗检测", "image_id": "sleep.jpg"}]}
    r, _ = graph_api.handle_activate({"query": "睡岗", **body})
    assert r["ok"] is True
    assert r["center"]["id"] == "ent_person"  # 人员(提及最多)而非工位
    assert "任务词命中QA" in r["center"]["why"]


def test_error_and_edge_cases() -> None:
    r, status = graph_api.handle_activate({"query": ""})
    assert status == 400 and r["error"]["code"] == "BAD_REQUEST"
    r, status = graph_api.handle_activate({"query": "口罩", "k": "x"})
    assert status == 400
    r, status = graph_api.handle_node_detail({})
    assert status == 400
    r, status = graph_api.handle_node_detail({"node_id": "ent_不存在"})
    assert status == 200 and r["ok"] is False
    r, _ = graph_api.handle_activate({"query": "完全不匹配的词"})
    assert r["ok"] is False and r["message"]


_BUILTIN_DATASET = (_BACKEND.parent / "data" / "kg_supervision" / "qa_dataset.jsonl")


def test_builtin_dataset_snapshot() -> None:
    """内置演示数据集快照(数据集受MANIFEST保护, 数字变更须有意为之).

    2026-11-23: 视觉观测源从demo模拟切换为真实CV检测
    (visual_chunks_real.json, YOLO人员+安全帽) — QA声明与真实观测的
    矛盾被真实检出(refuted 1→6), 数字为有意变更.
    """
    if not _BUILTIN_DATASET.exists():
        pytest.skip("内置数据集缺失")
    r, _ = graph_api.handle_activate({"query": "安全帽", "k": 2, "top_k": 12})
    assert r["ok"] is True
    assert r["center"]["id"] == "ent_helmet"
    assert r["stats"]["n_related"] == 8
    assert r["stats"]["by_type"] == {"QA": 12, "PERSON": 12, "PPE": 12,
                                     "RELATION": 12}
    d, _ = graph_api.handle_node_detail({"node_id": "ent_helmet",
                                         "node_type": "entity"})
    s = d["structured"]
    assert len(s["qa_mentions"]) == 11
    statuses = [x["observation_status"] for x in s["cross_modal"]]
    # 真实CV观测: 6条QA声明被YOLO观测驳回(如QA称"有人员未佩戴"而实际全员
    # 佩戴Hardhat); ppe_005无人员观测→NIE
    assert statuses.count("supported") == 4
    assert statuses.count("NIE") == 1
    refuted = [x for x in s["cross_modal"] if x["observation_status"] == "refuted"]
    assert [x["qa_id"] for x in refuted] == ["0", "2", "3", "6", "8", "42"]
    assert d["features"]["modality_links"] == {"QA": 11, "PERSON": 32,
                                               "PPE": 31, "RELATION": 3}
    # 中文别名id解析(ent_安全帽 == ent_helmet)
    d2, _ = graph_api.handle_node_detail({"node_id": "ent_安全帽"})
    assert d2 == d
