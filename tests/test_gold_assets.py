"""金标资产守卫测试: 论文数字与评测基准的回归保护.

每个断言 = 一个"论文里引用过的数字"或"评测基准的规模".
数字漂移 = 有人重生成/篡改了数据 或 内核行为变化 → 必须显式确认.

注意: 有意更新数据后, 重跑 tools/build_data_manifest.py 并同步本文件快照.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
D = BASE / "data/gjb_438c"


def _j(rel: str):
    p = D / rel
    if not p.exists():
        pytest.skip(f"资产缺失: {rel}")
    return json.loads(p.read_text(encoding="utf-8"))


# ═══════════════════════════════════════════════════════════════
# Born-digital锚点 (M0/M11产出)
# ═══════════════════════════════════════════════════════════════

def test_anchors_v2_scale():
    a = _j("anchor_v2/anchors_v2.json")
    n_struct = sum(d["visio_count"] for d in a.values())
    n_nodes = sum(len(s["nodes"]) for d in a.values() for s in d["structures"])
    n_edges = sum(len(s["edges"]) for d in a.values() for s in d["structures"])
    assert len(a) == 16
    assert n_struct == 373
    assert n_nodes == 3759
    assert n_edges == 2680
    # 注: docs/srs_project记载3757/2610(M11口径), 实测文件为3759/2680 — 以文件为准


# ═══════════════════════════════════════════════════════════════
# Pair Dataset (v3.0: 366对×8场景)
# ═══════════════════════════════════════════════════════════════

def test_pair_dataset_scale():
    pd = D / "pair_dataset"
    if not pd.exists():
        pytest.skip("pair_dataset缺失")
    counts = {}
    for sd in sorted(pd.iterdir()):
        if sd.is_dir():
            counts[sd.name] = sum(1 for x in sd.iterdir()
                                  if (x / "meta.json").exists())
    assert counts == {
        "sc1_usecase_capability": 141, "sc2_flowchart_usecase": 90,
        "sc3_interface_interface": 30, "sc4_flowchart_capability": 49,
        "sc5_function_capability": 27, "sc7_usecase_usecase": 9,
        "sc8_pure_image": 20,
    }
    assert sum(counts.values()) == 366


# ═══════════════════════════════════════════════════════════════
# M3校准θ (论文核心数字: VLM通道误差模型)
# ═══════════════════════════════════════════════════════════════

def test_calibration_theta_global():
    c = _j("anchor_sc2/calibration.json")
    tg = c["theta_global"]
    assert c["n_pairs"] == 89
    assert tg["node_recall"]["value"] == pytest.approx(0.9436, abs=1e-4)
    assert tg["node_recall"]["n"] == 514
    assert tg["node_precision"]["value"] == pytest.approx(0.9898, abs=1e-4)
    assert tg["edge_recall"]["value"] == pytest.approx(0.982, abs=1e-4)
    assert tg["edge_extra_rate"]["value"] == pytest.approx(0.2406, abs=1e-4)


def test_calibration_theta_by_phi():
    c = _j("anchor_sc2/calibration.json")
    phi = {k: v["node_miss_rate"] for k, v in c["theta_by_phi"].items()}
    assert phi == {"large(>10)": 0.113, "medium(6-10)": 0.079, "small(≤5)": 0.02}


# ═══════════════════════════════════════════════════════════════
# Tier1预计算比较
# ═══════════════════════════════════════════════════════════════

def test_scene_tier1_1_001():
    t = _j("anchor_v2/scene_tier1.json")
    assert len(t) == 227
    r = t["1_001"]
    assert (r["n_table"], r["n_diag"], r["n_matched"]) == (8, 6, 4)
    assert len(r["discrepancies"]) == 5


def test_sc2_tier1_2_001():
    t = _j("anchor_sc2/tier1_discrepancies_v2.json")
    assert len(t) == 89
    r = t["2_001"]
    assert (r["n_table_steps"], r["n_diag_nodes"], r["n_matched"]) == (7, 6, 6)
    assert {d["dtype"] for d in r["discrepancies"]} == {
        "STEP_MISSING", "ACTOR_MISSING", "EXC_MISSING", "ORDER_CONFLICT"}


# ═══════════════════════════════════════════════════════════════
# ID-Graph / chunks / 图片分析 (M5轨道资产)
# ═══════════════════════════════════════════════════════════════

def test_id_document_graph():
    g = _j("data_assets/graph/id_document_graph.json")
    ents = sum(1 for n in g["nodes"] if n["id"].startswith("E_"))
    ments = sum(1 for n in g["nodes"] if n["id"].startswith("M_"))
    assert (len(g["nodes"]), len(g["edges"])) == (2181, 1613)
    assert (ents, ments) == (568, 1613)


def test_srs_chunks():
    ch = _j("data_assets/chunks/srs_chunks.json")
    types = {}
    for c in ch:
        types[c["type"]] = types.get(c["type"], 0) + 1
    assert len(ch) == 5231
    assert types == {"text": 3643, "table": 1207, "image": 381}


def test_image_analyses():
    ia = _j("data_assets/chunks/srs_image_analyses.json")
    assert len(ia["analyses"]) == 379


def test_drift_census():
    dc = _j("anchor_v2/scene_drift_census.json")
    assert len(dc) == 236


# ═══════════════════════════════════════════════════════════════
# Blackboard embedding校准 (本包产出, agreement=0.779)
# ═══════════════════════════════════════════════════════════════

def test_embedding_calibration():
    ec = _j("blackboard/embedding_calibration.json")
    assert ec["n_pairs"] == 40
    assert ec["n_emb_matches"] == 86
    assert ec["agreement_rate"] == pytest.approx(0.7791, abs=1e-4)
