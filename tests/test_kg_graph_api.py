"""场景五图谱交互API回归测试(graph_api.py: activate + node_detail).

确定性内核快照: body数据通路完全自包含(不依赖内置数据集文件);
内置数据集通路覆盖C-3同图异判跨模态冲突(数据集受MANIFEST保护).

cross_modal自2026-11-24走claim_verify per-fact核验(93号文档§4.4):
真实CV可接地图用verify_qa结论(verdict/nie_reason/facts证据链),
body自带Chunk的图回退v0答案极性×观测聚合.
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
    """C-3式同图异判: 同图两条clean/violation断言, 冻结观测只能支持其一.

    body图(mask_a/mask_b)不在真实CV库(visual_chunks_real.json) →
    claim_verify不可per-fact接地, 走v0回退(答案极性×观测聚合),
    行为与升级前一致.
    """
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


def test_cross_modal_claim_verify_fields() -> None:
    """2026-11-24升级: cross_modal每条目带claim_verify per-fact三件套.

    verdict(support/refute/NIE)与observation_status(supported/refuted/NIE)
    为同义词对; facts证据链非空且逐条含{claim, grounded_chunk, observation,
    fact_verdict, reason}. body图无真实CV记录 → v0回退路径:
    m2的refute证据链为单事实聚合, m1的NIE带原因标签.
    """
    d, _ = graph_api.handle_node_detail({"node_id": "ent_口罩",
                                         "node_type": "entity", **_BODY})
    cm = d["structured"]["cross_modal"]
    by_qa = {x["qa_id"]: x for x in cm}
    synonym = {"support": "supported", "refute": "refuted", "NIE": "NIE"}
    for x in cm:
        assert x["verdict"] in synonym
        assert x["observation_status"] == synonym[x["verdict"]]  # API兼容同义词
        assert isinstance(x["facts"], list) and x["facts"]
        for f in x["facts"]:
            assert {"claim", "grounded_chunk", "observation", "fact_verdict",
                    "reason"} <= set(f)
            assert f["fact_verdict"] in ("support", "refute", "nie")
    # refute条目: facts非空且fact_verdict含refute
    assert by_qa["m2"]["verdict"] == "refute"
    assert by_qa["m2"]["nie_reason"] is None
    assert any(f["fact_verdict"] == "refute" for f in by_qa["m2"]["facts"])
    # NIE条目: v0回退的原因标签对齐claim_verify词表
    assert by_qa["m1"]["verdict"] == "NIE"
    assert by_qa["m1"]["nie_reason"] == "missing_observation"


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
_REAL_CHUNKS = (_BACKEND.parent / "data" / "kg_supervision" / "visual_chunks_real.json")


def test_builtin_dataset_snapshot() -> None:
    """内置演示数据集快照(数据集受MANIFEST保护, 数字变更须有意为之).

    2026-11-23: 视觉观测源从demo模拟切换为真实CV检测
    (visual_chunks_real.json, YOLO人员+安全帽) — QA声明与真实观测的
    矛盾被真实检出(refuted 1→6), 数字为有意变更.
    2026-11-24: cross_modal从_STATUS_MAP v0(答案极性×观测状态聚合)
    升级为claim_verify per-fact(声明分解→图内接地→逐事实比对→聚合,
    93号文档§4.4) — supported 4→2, NIE 1→3, refuted qa列表2/43移出
    (NIE: 空间指代无法接地/该图0人员)、4移入(声明无人员而观测7人),
    数字为有意变更.
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
    # claim_verify per-fact结论: qa2"左侧"指代无法接地/qa43该图0人员→NIE;
    # qa4声明"无人员"而YOLO观测7人→refute(v0误判supported)
    assert statuses.count("supported") == 2
    assert statuses.count("NIE") == 3
    refuted = [x for x in s["cross_modal"] if x["observation_status"] == "refuted"]
    assert [x["qa_id"] for x in refuted] == ["0", "3", "4", "6", "8", "42"]
    # per-fact证据链: refute条目facts非空且含refute事实(逐事实矛盾可追溯)
    assert all(x["verdict"] == "refute" and x["nie_reason"] is None
               for x in refuted)
    assert all(any(f["fact_verdict"] == "refute" for f in x["facts"])
               for x in refuted)
    # NIE条目带claim_verify原因标签(NIE原因学)
    nies = {x["qa_id"]: x["nie_reason"] for x in s["cross_modal"]
            if x["observation_status"] == "NIE"}
    assert nies == {"2": "ambiguous", "5": "answer_unverifiable",
                    "43": "no_person_target"}
    assert d["features"]["modality_links"] == {"QA": 11, "PERSON": 32,
                                               "PPE": 31, "RELATION": 3}
    # 中文别名id解析(ent_安全帽 == ent_helmet)
    d2, _ = graph_api.handle_node_detail({"node_id": "ent_安全帽"})
    assert d2 == d


def test_cross_modal_facts_truncated() -> None:
    """facts证据链截断到前5条(防payload过大, _MAX_CROSS_MODAL_FACTS).

    真实CV可接地图(ppe_002)上6个原子声明 → verify_qa产出6条fact → 截断为5.
    """
    if not _REAL_CHUNKS.exists():
        pytest.skip("真实CV观测数据缺失")
    ev = "，".join(["画面中所有人员均佩戴安全帽"] * 6)
    body = {"qa_records": [{"qa_id": "t5", "question": "判断人员安全帽佩戴",
                            "answer": 0, "evidence": ev, "task": "安全帽佩戴检测",
                            "image_id": "ppe_002.jpg"}]}
    d, _ = graph_api.handle_node_detail({"node_id": "ent_安全帽", **body})
    cm = d["structured"]["cross_modal"]
    assert len(cm) == 1
    assert len(cm[0]["facts"]) == 5  # 6条claim→6条fact, 截断到前5
    assert all(f["fact_verdict"] == "support" for f in cm[0]["facts"])
