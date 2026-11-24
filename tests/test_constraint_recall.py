"""场景五约束解析召回回归测试(constraint_recall.py: parse_constraints + recall_chunks).

确定性快照: 真实CV检测数据(visual_chunks_real.json, MANIFEST保护)上的
约束解析/切片过滤排序契约(93号文档§3 P1); 数据文件缺失时skip.
组织方式仿test_kg_graph_api.py: sys.path注入backend, 直接调模块函数不测HTTP.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1] / "deploy" / "nkuDataProject" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from scenarios.kg_supervision import constraint_recall  # noqa: E402

_DATA = _BACKEND.parent / "data" / "kg_supervision" / "visual_chunks_real.json"
requires_data = pytest.mark.skipif(
    not _DATA.exists(), reason="真实CV检测数据缺失(visual_chunks_real.json)")


# ---- parse_constraints: 约束解析器(规则层, 不依赖数据文件) ----

def test_parse_constraints_full_question() -> None:
    c = constraint_recall.parse_constraints("判断图片中右侧人员是否佩戴安全帽")
    assert c["spatial"] == "right"
    assert c["entity_types"] == ["person", "helmet"]  # 按文中出现顺序
    assert c["attributes"] == ["wearing"]
    assert c["count"] is None
    assert c["count_scope"] is None
    assert c["temporal"] is False


def test_parse_constraints_not_wearing_and_count() -> None:
    c = constraint_recall.parse_constraints("是否有2人未佩戴")
    assert c["count"] == 2
    # 否定前缀感知: "未佩戴"不误判为wearing
    assert c["attributes"] == ["not_wearing"]
    assert "wearing" not in c["attributes"]
    # "N 人"(带空白)同样命中计数
    assert constraint_recall.parse_constraints("画面中有 3 人")["count"] == 3


def test_parse_constraints_sleep_and_temporal() -> None:
    c = constraint_recall.parse_constraints("夜班是否存在人员长时间睡岗")
    assert "sleep" in c["attributes"]
    assert "person" in c["entity_types"]
    assert c["temporal"] is True


def test_parse_constraints_scope_all() -> None:
    c = constraint_recall.parse_constraints("画面中所有人员是否佩戴口罩")
    assert c["count_scope"] == "all"
    assert constraint_recall.parse_constraints("全部人员")["count_scope"] == "all"
    assert set(c["entity_types"]) == {"person", "mask"}
    assert c["attributes"] == ["wearing"]


def test_parse_constraints_spatial_words() -> None:
    assert constraint_recall.parse_constraints("左侧工人是否倒地")["spatial"] == "left"
    assert constraint_recall.parse_constraints("画面中央的作业人员")["spatial"] == "center"
    assert constraint_recall.parse_constraints("任意人员")["spatial"] is None
    # 作业人员与人员同型去重
    assert constraint_recall.parse_constraints("画面中央的作业人员")["entity_types"] == ["person"]


def test_parse_constraints_multiple_attributes() -> None:
    c = constraint_recall.parse_constraints("是否有人员未佩戴安全帽且倒地")
    assert c["attributes"] == ["not_wearing", "prone"]
    assert "prone" in constraint_recall.parse_constraints("是否有人摔倒")["attributes"]


def test_parse_constraints_empty_query() -> None:
    assert constraint_recall.parse_constraints("") == {
        "entity_types": [], "spatial": None, "attributes": [],
        "count": None, "count_scope": None, "temporal": False,
    }


# ---- recall_chunks: 过滤排序(真实CV数据, 确定性快照) ----

def _db() -> dict:
    return json.loads(_DATA.read_text(encoding="utf-8"))["chunks"]


def _person_cx(db: dict, chunk: dict) -> float:
    """chunk_id(stem#pN) → 人员bbox中心x/图宽(与模块同口径)."""
    stem, _, n = chunk["chunk_id"].partition("#p")
    entry = db[stem]
    b = entry["persons"][int(n) - 1]["bbox"]
    return (b[0] + b[2]) / 2 / entry["size"][0]


@requires_data
def test_recall_chunks_spatial_ranking() -> None:
    """右侧约束: x中心>67%的人员得分高于x<33%的, 且仅前者matched."""
    db = _db()
    r = constraint_recall.recall_chunks("右侧人员", ["ppe_001", "ppe_002"])
    assert r["constraints"]["spatial"] == "right"
    assert [im["image_id"] for im in r["images"]] == ["ppe_001.jpg", "ppe_002.jpg"]
    persons = [c for im in r["images"] for c in im["chunks"] if c["type"] == "person"]
    right = [c for c in persons if _person_cx(db, c) > 0.67]
    left = [c for c in persons if _person_cx(db, c) < 0.33]
    assert right and left  # ppe_001全员右侧 / ppe_002含左侧人员
    assert min(c["score"] for c in right) > max(c["score"] for c in left)
    assert all(c["matched"] for c in right)
    assert not any(c["matched"] for c in left)
    # 命中约束的可解释reason(x百分比)
    assert right[0]["reasons"][0] == "类型匹配:person"
    assert right[0]["reasons"][1].startswith("空间约束:右侧(x=")


@requires_data
def test_recall_chunks_ordering_invariant() -> None:
    """排序契约: matched在前, 组内按score降序, n_matched与stats对账."""
    r = constraint_recall.recall_chunks("右侧人员是否佩戴安全帽", ["ppe_001", "ppe_002"])
    for im in r["images"]:
        flags = [c["matched"] for c in im["chunks"]]
        assert flags == sorted(flags, reverse=True)  # matched(True)在前
        scores = [c["score"] for c in im["chunks"]]
        hit = [s for s, f in zip(scores, flags) if f]
        miss = [s for s, f in zip(scores, flags) if not f]
        assert hit == sorted(hit, reverse=True)
        assert miss == sorted(miss, reverse=True)
        assert im["n_matched"] == sum(flags)
    assert r["stats"] == {"n_images": 2,
                          "n_matched": sum(im["n_matched"] for im in r["images"])}


@requires_data
def test_recall_chunks_chunk_contract() -> None:
    """chunk载荷契约: 字段齐备/score有界/reasons必填; 双实体召回person+ppe两类."""
    r = constraint_recall.recall_chunks("画面中右侧人员是否佩戴安全帽", ["ppe_001"])
    chunks = r["images"][0]["chunks"]
    assert chunks
    for c in chunks:
        assert {"chunk_id", "type", "bbox", "conf", "pose", "state",
                "matched_person", "score", "matched", "reasons"} <= set(c)
        assert 0.0 <= c["score"] <= 1.0
        assert c["reasons"]  # 可解释文本必填(每条命中约束一条)
        assert c["chunk_id"].startswith("ppe_001#")
    assert {c["type"] for c in chunks} == {"person", "ppe"}
    person = next(c for c in chunks if c["type"] == "person")
    assert person["pose"] and person["state"] is None
    ppe = next(c for c in chunks if c["type"] == "ppe")
    assert ppe["state"] in ("worn", "missing")
    assert isinstance(ppe["matched_person"], int)  # persons数组下标


@requires_data
def test_recall_chunks_attribute_ranking() -> None:
    """未佩戴约束: state=missing的ppe块matched且排在worn前; 关联人员借道匹配."""
    r = constraint_recall.recall_chunks("画面中是否有人员未佩戴安全帽", ["corridor_002"])
    assert r["constraints"]["attributes"] == ["not_wearing"]
    chunks = r["images"][0]["chunks"]
    ppes = [c for c in chunks if c["type"] == "ppe"]
    assert ppes[0]["state"] == "missing"
    assert ppes[0]["matched"] is True
    assert all(c["matched"] is False for c in ppes[1:])
    assert any("未佩戴" in x and "state=missing" in x for x in ppes[0]["reasons"])
    # 借道: 关联missing ppe的人员同样matched, reason指向关联ppe
    borrowers = [c for c in chunks if c["type"] == "person" and c["matched"]]
    assert borrowers
    assert all(any("关联ppe#" in x for x in c["reasons"]) for c in borrowers)


@requires_data
def test_recall_chunks_helmet_only_query() -> None:
    """helmet单实体: 仅召回ppe块(93号§3.3 m_τ)."""
    r = constraint_recall.recall_chunks("未佩戴安全帽", ["corridor_002"])
    assert r["constraints"]["entity_types"] == ["helmet"]
    chunks = r["images"][0]["chunks"]
    assert {c["type"] for c in chunks} == {"ppe"}
    assert chunks[0]["state"] == "missing" and chunks[0]["matched"] is True


@requires_data
def test_recall_chunks_mask_query_no_hardhat_evidence() -> None:
    """口罩问题不借安全帽观测: 数据无Mask类ppe → 属性不命中, 无matched."""
    r = constraint_recall.recall_chunks("画面中人员是否佩戴口罩", ["ppe_001"])
    assert set(r["constraints"]["entity_types"]) == {"person", "mask"}
    chunks = r["images"][0]["chunks"]
    assert all(c["matched"] is False for c in chunks)
    assert not any("state=" in x for c in chunks for x in c["reasons"])


@requires_data
def test_recall_chunks_image_id_tolerance() -> None:
    """image_id带/不带.jpg等价; 未知图名跳过不报错; 重复图名去重保序."""
    a = constraint_recall.recall_chunks("右侧人员", ["ppe_001.jpg"])
    b = constraint_recall.recall_chunks("右侧人员", ["ppe_001"])
    assert a == b
    assert a["stats"]["n_images"] == 1
    r = constraint_recall.recall_chunks("右侧人员", ["ppe_001", "不存在的图", "ppe_001"])
    assert [im["image_id"] for im in r["images"]] == ["ppe_001.jpg"]


@requires_data
def test_recall_chunks_all_images() -> None:
    """image_ids=None → 全部图(stem排序确定性); 纯实体查询全员matched."""
    db = _db()
    r = constraint_recall.recall_chunks("人员", None)
    assert r["stats"]["n_images"] == len(db)
    ids = [im["image_id"] for im in r["images"]]
    assert ids == sorted(ids)
    assert all(i.endswith(".jpg") for i in ids)
    # 无σ/α约束时person块为直接类型命中(纯实体) → 全部matched
    assert r["stats"]["n_matched"] == sum(len(e["persons"]) for e in db.values())


@requires_data
def test_recall_chunks_graceful_no_constraint() -> None:
    """无可解析约束: 空切片不报错(κ/NIE判定留给方向B)."""
    r = constraint_recall.recall_chunks("今天天气如何", ["ppe_001"])
    assert r["constraints"]["entity_types"] == []
    assert r["images"][0]["chunks"] == []
    assert r["stats"] == {"n_images": 1, "n_matched": 0}
