"""visio_features_v2合并逻辑测试: 合并补齐/方向推断/对齐失败记录 + 真实数据契约快照."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_visio_features_v2 import (
    ANCHOR_V2_PATH,
    ANCHOR_V3_PATH,
    build,
    infer_direction,
    normalize_doc_name,
)

BASE = Path(__file__).resolve().parent.parent
CORPUS_NODES_PATH = BASE / "data/gjb_438c/structured_corpus_v1/diagram_nodes.jsonl"
CORPUS_EDGES_PATH = BASE / "data/gjb_438c/structured_corpus_v1/diagram_edges.jsonl"

DOC_NAME = "01测试系统-终稿"
EMBED = "oleObject1.bin:page1.xml"


def _sid(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"


def _v3_structure(embed: str = EMBED) -> dict:
    return {
        "source": f"word/embeddings/{embed.split(':')[0]}",
        "embed_index": embed,
        "page": {"w": 8.5, "h": 11.0},
        "nodes": [
            {
                "id": "10", "text": "数据获取", "type": "process",
                "cx": 1.0, "cy": 2.0, "w": 0.5, "h": 0.3, "rx": 0.1, "ry": 0.2,
            },
            {
                "id": "11", "text": "数据转换", "type": "datastore",
                "cx": 3.0, "cy": 4.0, "w": 0.6, "h": 0.4, "rx": 0.1, "ry": 0.2,
            },
            {
                "id": "12", "text": "", "type": "other",
                "cx": 5.0, "cy": 6.0, "w": 0.2, "h": 0.0, "rx": 0.0, "ry": 0.0,
            },
        ],
        "edges": [
            {
                "src": "10", "dst": "11", "src_text": "数据获取", "dst_text": "数据转换",
                "label": "输入", "uml_type": "ASSOCIATION", "line_pattern": "solid",
                "begin_arrow": "none", "end_arrow": "filled_triangle",
                "connector_id": "20", "via": "glued",
            },
            {
                "src": "11", "dst": "10", "src_text": "数据转换", "dst_text": "数据获取",
                "label": "", "uml_type": "ASSOCIATION", "line_pattern": "solid",
                "begin_arrow": "none", "end_arrow": "none",
                "connector_id": "21", "via": "glued",
            },
        ],
        "meta": {},
    }


def _v2_structure(embed: str = EMBED) -> dict:
    return {
        "source": f"word/embeddings/{embed.split(':')[0]}",
        "embed_index": embed,
        "page": {"w": 8.5, "h": 11.0},
        "nodes": [
            {
                # id对齐但rx/ry漂移 → 输出必须取v3值
                "id": "10", "text": "数据获取", "type": "actor",
                "cx": 1.0, "cy": 2.0, "w": 0.5, "h": 0.3, "rx": 9.9, "ry": 9.9,
                "master_type": "Rectangle.5", "via_master": True,
                "bbox": [0.75, 1.85, 1.25, 2.15],
            },
            {
                "id": "11", "text": "数据转换", "type": "process",
                "cx": 3.0, "cy": 4.0, "w": 0.6, "h": 0.4, "rx": 9.9, "ry": 9.9,
                "master_type": "", "via_master": False,
                "bbox": [2.7, 3.8, 3.3, 4.2],
            },
            {
                # v2独有节点 → residual, 不进输出
                "id": "99", "text": "v2独有", "type": "other",
                "cx": 0.0, "cy": 0.0, "w": 0.1, "h": 0.1, "rx": 0.0, "ry": 0.0,
                "master_type": "", "via_master": False, "bbox": [0.0, 0.0, 0.1, 0.1],
            },
        ],
        "edges": [
            {
                "src": "10", "dst": "11", "src_text": "数据获取", "dst_text": "数据转换",
                "label": "输入", "label_pos": [0.5, 1.0], "connector_id": "20",
                "via": "glued", "waypoints": [[0.1, 0.2], [0.3, 0.4]],
            },
            {
                # 对齐成功但v2侧无label_pos/waypoints键 → 输出null
                "src": "11", "dst": "10", "src_text": "数据转换", "dst_text": "数据获取",
                "label": "", "connector_id": "21", "via": "glued",
            },
            {
                # v2独有边 → residual, 不进输出
                "src": "10", "dst": "11", "src_text": "数据获取", "dst_text": "数据转换",
                "label": "", "connector_id": "30", "via": "geo_arrow",
                "waypoints": [[0.0, 0.0], [1.0, 1.0]],
            },
        ],
        "meta": {},
    }


def test_merge_synthetic_fills_all_fields_from_both_versions() -> None:
    built = build({DOC_NAME: {"structures": [_v2_structure()]}},
                  {DOC_NAME: {"structures": [_v3_structure()]}})
    nodes = {row["source_node_id"]: row for row in built["node_rows"]}
    edges = {row["connector_id"]: row for row in built["edge_rows"]}

    # 合并后全有: v3基准字段 + v2补齐字段同在一行
    node_expected_keys = {
        "node_id", "diagram_id", "doc_id", "source_node_id", "text_raw", "type_candidate",
        "master_type", "via_master", "geometry", "fields_provenance", "parse_status",
    }
    assert set(nodes["10"]) == node_expected_keys
    assert nodes["10"]["master_type"] == "Rectangle.5"
    assert nodes["10"]["via_master"] is True
    assert nodes["10"]["geometry"]["bbox"] == [0.75, 1.85, 1.25, 2.15]
    assert nodes["10"]["geometry"]["cx"] == 1.0
    assert nodes["10"]["parse_status"] == "merged"
    assert nodes["10"]["fields_provenance"]["from_v2"] == ["master_type", "via_master", "bbox"]

    # 共有字段漂移取v3(与structured_corpus_v1一致), 且漂移被计数不静默
    assert nodes["10"]["geometry"]["rx"] == 0.1
    assert nodes["10"]["type_candidate"] == "process"
    assert built["summary"]["field_drift"]["nodes"]["rx"] >= 2

    # v2节点master为空串: 字段已交付(空值), 不算nonempty
    assert nodes["11"]["master_type"] == ""
    assert nodes["11"]["parse_status"] == "merged"

    # v3独有节点: v2补齐字段为null, provenance空
    assert nodes["12"]["master_type"] is None
    assert nodes["12"]["via_master"] is None
    assert nodes["12"]["geometry"]["bbox"] is None
    assert nodes["12"]["fields_provenance"]["from_v2"] == []
    assert nodes["12"]["parse_status"] == "v3_only"

    edge_expected_keys = {
        "edge_id", "diagram_id", "doc_id", "src_node", "dst_node", "connector_id",
        "label_raw", "label_pos", "waypoints", "uml_type", "line_pattern",
        "begin_arrow", "end_arrow", "via", "direction_status", "parse_status",
    }
    assert set(edges["20"]) == edge_expected_keys
    assert edges["20"]["label_pos"] == [0.5, 1.0]
    assert edges["20"]["waypoints"] == [[0.1, 0.2], [0.3, 0.4]]
    assert edges["20"]["uml_type"] == "ASSOCIATION"
    assert edges["20"]["end_arrow"] == "filled_triangle"
    assert edges["20"]["direction_status"] == "directed_src_to_dst"
    assert edges["20"]["parse_status"] == "merged"
    assert edges["20"]["src_node"] == nodes["10"]["node_id"]
    assert edges["20"]["dst_node"] == nodes["11"]["node_id"]

    # 对齐的v2边缺waypoints/label_pos键 → null; none+none → undetermined
    assert edges["21"]["waypoints"] is None
    assert edges["21"]["label_pos"] is None
    assert edges["21"]["direction_status"] == "undetermined"
    assert edges["21"]["parse_status"] == "merged"

    # v2独有残余(节点99/边30): 不进输出, 但计数入summary(不静默丢)
    assert set(nodes) == {"10", "11", "12"}
    assert set(edges) == {"20", "21"}
    assert built["summary"]["nodes"]["v2_only_residual"] == 1
    assert built["summary"]["edges"]["v2_only_residual"] == 1
    assert built["summary"]["nodes"]["emitted"] == 3
    assert built["summary"]["edges"]["emitted"] == 2
    assert built["summary"]["alignment"]["alignment_failures"] == 0


def test_merged_ids_follow_structured_corpus_stable_id_formula() -> None:
    built = build({DOC_NAME: {"structures": [_v2_structure()]}},
                  {DOC_NAME: {"structures": [_v3_structure()]}})
    diagram_id = _sid("DGM", "01", EMBED)
    nodes = {row["source_node_id"]: row for row in built["node_rows"]}
    edges = {row["connector_id"]: row for row in built["edge_rows"]}
    assert nodes["10"]["node_id"] == _sid("NOD", diagram_id, "10")
    assert nodes["10"]["diagram_id"] == diagram_id
    assert edges["20"]["edge_id"] == _sid("EDG", diagram_id, "20")


def test_direction_inference_rules() -> None:
    # case 1: none + none → 无方向信息
    assert infer_direction("none", "none") == "undetermined"
    # case 2: 单端箭头 → directed并标注哪端(end箭头指向dst, begin箭头指向src)
    assert infer_direction("none", "filled_triangle") == "directed_src_to_dst"
    assert infer_direction("filled_triangle", "none") == "directed_dst_to_src"
    assert infer_direction("none", "open_60") == "directed_src_to_dst"
    # case 3: 双端箭头 → bidirectional
    assert infer_direction("open", "closed") == "bidirectional"
    assert infer_direction("filled_square", "filled_triangle") == "bidirectional"
    # 箭头格值无法映射("unknown"/缺失) → 诚实undetermined, 不猜
    assert infer_direction("unknown", "none") == "undetermined"
    assert infer_direction("unknown", "filled_triangle") == "undetermined"
    assert infer_direction(None, "") == "undetermined"


def test_alignment_failures_recorded_and_rows_not_silently_dropped() -> None:
    v3 = {"structures": [
        _v3_structure(EMBED),
        _v3_structure("oleObject2.bin:page1.xml"),
    ]}
    v2 = {"structures": [
        _v2_structure(EMBED),
        # v2缺oleObject2 → missing_in_v2
        _v2_structure("oleObject3.bin:page1.xml"),  # v2独有 → missing_in_v3
    ]}
    built = build({DOC_NAME: v2}, {DOC_NAME: v3})
    failures = built["failures"]
    by_type = {row["failure_type"]: row for row in failures}

    assert len(failures) == 2
    # v3侧存在的structure: 记失败, 但行照常产出(v3_only)
    miss_v2 = by_type["missing_in_v2"]
    assert miss_v2["embed_index"] == "oleObject2.bin:page1.xml"
    assert miss_v2["version"] == "v3"
    assert miss_v2["doc_name"] == DOC_NAME
    dgm2 = _sid("DGM", "01", "oleObject2.bin:page1.xml")
    rows_of_dgm2 = [r for r in built["node_rows"] if r["diagram_id"] == dgm2]
    assert len(rows_of_dgm2) == 3
    assert all(r["parse_status"] == "v3_only" for r in rows_of_dgm2)
    # v2独有structure: 记失败, 无v3基准不产出行
    miss_v3 = by_type["missing_in_v3"]
    assert miss_v3["embed_index"] == "oleObject3.bin:page1.xml"
    assert miss_v3["version"] == "v2"
    dgm3 = _sid("DGM", "01", "oleObject3.bin:page1.xml")
    assert not [r for r in built["node_rows"] if r["diagram_id"] == dgm3]
    # summary如实计数
    alignment = built["summary"]["alignment"]
    assert alignment["structure_keys"] == 3
    assert alignment["aligned_structures"] == 1
    assert alignment["v3_only_structures"] == 1
    assert alignment["v2_only_structures"] == 1
    assert alignment["alignment_failures"] == 2


def test_doc_name_normalization_enables_cross_version_alignment() -> None:
    v2_key = f" {DOC_NAME}\u3000 "  # 首尾空白+全角空格
    built = build({v2_key: {"structures": [_v2_structure()]}},
                  {DOC_NAME: {"structures": [_v3_structure()]}})
    assert built["failures"] == []
    assert normalize_doc_name(v2_key) == DOC_NAME
    assert built["summary"]["alignment"]["aligned_structures"] == 1


def test_real_data_merge_matches_structured_corpus_and_snapshot() -> None:
    """真实16文档373图: ID与structured_corpus_v1完全一致 + 头部数字快照(论文数字锁定)."""
    with ANCHOR_V2_PATH.open("r", encoding="utf-8") as handle:
        anchors_v2 = json.load(handle)
    with ANCHOR_V3_PATH.open("r", encoding="utf-8") as handle:
        anchors_v3 = json.load(handle)
    built = build(anchors_v2, anchors_v3)
    summary = built["summary"]

    # DGM/NOD/EDG映射契约: 与structured_corpus_v1逐ID一致
    corpus_node_ids = {
        json.loads(line)["node_id"] for line in
        CORPUS_NODES_PATH.read_text(encoding="utf-8").splitlines() if line
    }
    corpus_edge_ids = {
        json.loads(line)["edge_id"] for line in
        CORPUS_EDGES_PATH.read_text(encoding="utf-8").splitlines() if line
    }
    assert {row["node_id"] for row in built["node_rows"]} == corpus_node_ids
    assert {row["edge_id"] for row in built["edge_rows"]} == corpus_edge_ids

    # 头部数字快照(数据资产受MANIFEST保护, 变动=有意重生成, 须同步更新此处)
    assert summary["alignment"]["structure_keys"] == 373
    assert summary["alignment"]["aligned_structures"] == 373
    assert summary["alignment"]["alignment_failures"] == 0
    assert summary["nodes"]["emitted"] == 5165
    assert summary["nodes"]["merged"] == 3747
    assert summary["nodes"]["master_type_present"] == 3747
    assert summary["nodes"]["master_type_nonempty"] == 2620
    assert summary["nodes"]["v2_only_residual"] == 12
    assert summary["edges"]["emitted"] == 2557
    assert summary["edges"]["merged"] == 2518
    assert summary["edges"]["label_pos_present"] == 173
    assert summary["edges"]["waypoints_present"] == 2518
    assert summary["edges"]["arrow_coverage"] == 1.0
    direction = summary["direction"]
    assert direction["counts"] == {
        "undetermined": 2174,
        "directed_src_to_dst": 316,
        "directed_dst_to_src": 57,
        "bidirectional": 10,
    }
    assert direction["determinable"] == 383
    assert direction["undetermined_reasons"] == {"no_arrows": 2124, "unknown_arrow": 50}
    # 父组/深度: 两版产物均无 → 诚实缺失声明
    assert summary["parent_depth_status"] == "not_available_in_artifacts"
