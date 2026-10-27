from tools.build_semantic_features_v2 import (
    alignment_status_of_layer,
    arrow_dir,
    band_by_y,
    classify_entity,
    detect_lanes,
    detect_state_diagram,
    match_structured_row,
    protocol_hits,
    tarjan_scc,
)


def _node(node_id: str, cy: float, node_type: str = "process", w: float = 0.5, h: float = 0.2) -> dict:
    return {
        "node_id": node_id,
        "type_candidate": node_type,
        "text_raw": node_id,
        "geometry": {"cx": 1.0, "cy": cy, "w": w, "h": h},
    }


def test_band_by_y_groups_nearby_nodes_only() -> None:
    bands = band_by_y([_node("a", 1.0), _node("b", 1.2), _node("c", 5.0)], gap=0.5)

    assert len(bands) == 2
    assert [n["node_id"] for n in bands[0]["nodes"]] == ["a", "b"]
    assert bands[1]["nodes"][0]["node_id"] == "c"


def test_arrow_direction_covers_all_arrow_patterns() -> None:
    assert arrow_dir("none", "none") == "none"
    assert arrow_dir("none", "filled_triangle") == "forward"
    assert arrow_dir("filled_triangle", "none") == "backward"
    assert arrow_dir("filled_triangle", "filled_triangle") == "bidirectional"


def test_detect_lanes_uses_boundary_container_and_bands() -> None:
    container = _node("lane", 2.0, "boundary", w=6.0, h=4.0)
    nodes = [container, _node("n1", 1.0), _node("n2", 1.1), _node("n3", 3.0)]
    result = detect_lanes("DGM-1", nodes, page_w=8.0, page_h=8.0)

    assert result["lanes_status"] == "lane_detected"
    assert result["lane_container"]["node_id"] == "lane"
    assert result["n_lanes"] >= 2


def test_tarjan_scc_finds_cycle_components() -> None:
    adjacency = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": set()}
    components = tarjan_scc(adjacency)

    assert {"a", "b", "c"} in [set(comp) for comp in components]
    assert {"d"} in [set(comp) for comp in components]


def test_classify_entity_covers_gjb_entity_lexicon() -> None:
    assert classify_entity("用户管理接口", "")[0] == "接口"
    assert classify_entity("数据传输模块", "")[0] == "模块"
    assert classify_entity("软件部署管理", "")[0] == "功能"
    assert classify_entity("某服务数据归集", "")[0] == "数据项"
    assert classify_entity("响应时间", "", cn_param_terms=[("响应时间", "response_time")])[0] == "参数"


def test_match_structured_row_matches_interface_name() -> None:
    rows = [
        {"name_cell": "用户管理接口", "cells": ["1", "用户管理接口", "API", "用户管理", "软件安装"]},
        {"name_cell": "数据传输接口", "cells": ["2", "数据传输接口", "网络"]},
    ]
    matched, basis = match_structured_row(rows, "用户管理接口")

    assert matched is not None
    assert basis == "exact"
    assert matched["cells"][4] == "软件安装"


def test_match_structured_row_returns_none_when_absent() -> None:
    rows = [{"name_cell": "其他接口", "cells": ["1", "其他接口", "API"]}]
    assert match_structured_row(rows, "不存在的接口") == (None, None)


def test_alignment_status_of_layer_maps_three_tiers() -> None:
    assert alignment_status_of_layer("L1") == "explicit"
    assert alignment_status_of_layer("L2") == "supported"
    assert alignment_status_of_layer(None) == "speculative"


def test_protocol_hits_detects_known_protocols() -> None:
    assert "API" in protocol_hits("用户管理接口为API类型")
    assert protocol_hits("无协议字段") == []


def test_detect_state_diagram_requires_state_nodes() -> None:
    result = detect_state_diagram(
        "DGM-2",
        "01",
        [_node("s1", 1.0, "state"), _node("s2", 2.0, "state")],
        [{"src": "s1", "dst": "s2", "label_raw": "触发"}],
    )

    assert result["status"] == "state_diagram_candidate"
    assert result["n_transitions"] >= 1
