#!/usr/bin/env python3
"""合并 anchor_v2 + anchor_v3, 补齐Visio底层缺失格 → visio_features_v2.

背景(两版解析产物互补, 谁都不全):
    anchor_v3/anchors_v3.json (m0_anchor_extract_v3):
        nodes: id/text/type/cx/cy/w/h/rx/ry
        edges: src/dst/src_text/dst_text/label/connector_id/via
               + uml_type/line_pattern/begin_arrow/end_arrow     ← v3独有
    anchor_v2/anchors_v2.json (m11_full_parser):
        nodes: 同上 + master_type/via_master/bbox                 ← v2独有
        edges: 同上 + label_pos/waypoints                         ← v2独有

合并规则:
    - 结构对齐: (规范化doc名, embed_index); 对不上的记 alignment_failures.jsonl
      (不静默丢弃), 其中v3侧存在的structure仍照常产出(v3_only行)
    - 节点对齐: source node id (同一Visio Shape ID); 边对齐: connector_id
    - 枚举基准 = v3 → node_id/edge_id/diagram_id 与 structured_corpus_v1 的
      DGM/NOD/EDG 映射完全一致(stable_id同式); v2只提供补齐字段
    - v2独有残余(节点/边): 不进输出(v3为枚举基准), 计数入summary, 不静默丢弃
    - 共有字段两版漂移(text/type/geometry/src/dst/via等): 一律取v3
      (与structured_corpus_v1一致), 漂移计数入 summary.field_drift
    - 父组/深度: 两版锚点产物均未导出(m11解析器内部计算后丢弃), 本任务不
      重跑解析器 → 输出与summary声明 parent_depth_status = "not_available_in_artifacts"

方向推断(infer_direction, 仅基于箭头格):
    end_arrow有箭头   → "directed_src_to_dst" (箭头指向dst)
    begin_arrow有箭头 → "directed_dst_to_src" (箭头指向src)
    双端箭头          → "bidirectional"
    none + none       → "undetermined"
    任一端"unknown"(箭头格值无法映射到已知箭头型) → "undetermined" (诚实缺失)

Usage:
    python tools/build_visio_features_v2.py
    python tools/build_visio_features_v2.py --output data/gjb_438c/visio_features_v2
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from tools.build_structured_corpus import doc_id_from_name, sha256_file, stable_id, write_jsonl
except ImportError:  # 直接以脚本运行时(python tools/xxx.py), sys.path[0]=tools/
    from build_structured_corpus import doc_id_from_name, sha256_file, stable_id, write_jsonl

BASE = Path(__file__).resolve().parent.parent
ANCHOR_V2_PATH = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
ANCHOR_V3_PATH = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/visio_features_v2"
SCHEMA_VERSION = "visio_features_v2"

PARENT_DEPTH_STATUS = "not_available_in_artifacts"
PARENT_DEPTH_NOTE = (
    "父组/深度: m11解析器内部计算但两版锚点产物均未导出; "
    "本任务不重跑解析器, 如实声明缺失(不伪造)"
)

# 节点: v2独有字段(补齐) / v3基准字段(枚举+取值), 顺序即fields_provenance顺序
NODE_FIELDS_FROM_V2 = ("master_type", "via_master", "bbox")
NODE_FIELDS_FROM_V3 = (
    ("text", "text_raw"),
    ("type", "type_candidate"),
    ("cx", "cx"),
    ("cy", "cy"),
    ("w", "w"),
    ("h", "h"),
    ("rx", "rx"),
    ("ry", "ry"),
)
# 边: v2独有字段 / v3独有字段
EDGE_FIELDS_FROM_V2 = ("label_pos", "waypoints")
EDGE_FIELDS_FROM_V3 = ("uml_type", "line_pattern", "begin_arrow", "end_arrow")
# 两版共有字段(取v3, 漂移计数)
NODE_SHARED_DRIFT_FIELDS = ("text", "type", "cx", "cy", "w", "h", "rx", "ry")
EDGE_SHARED_DRIFT_FIELDS = ("src", "dst", "label", "via", "src_text", "dst_text")

ARROW_NONE = "none"
ARROW_UNKNOWN = "unknown"
DIRECTION_STATUSES = (
    "undetermined",
    "directed_src_to_dst",
    "directed_dst_to_src",
    "bidirectional",
)


def normalize_doc_name(name: object) -> str:
    """规范化doc键: 去首尾空白(含全角空格). 两版应都用全名, 此处仅防御性统一."""
    return str(name if name is not None else "").replace("\u3000", " ").strip()


def arrow_state(value: object) -> str:
    """箭头格值 → 'arrow' | 'absent' | 'unknown'.

    'none'=确定无箭头; 'unknown'=格值存在但无法映射到已知箭头型(m0解析器
    ARROW_TYPES.get(v,'unknown')的兜底), 箭头有无不可判定.
    """
    text = str(value if value is not None else "").strip()
    if text == ARROW_NONE:
        return "absent"
    if not text or text == ARROW_UNKNOWN:
        return "unknown"
    return "arrow"


def infer_direction(begin_arrow: object, end_arrow: object) -> str:
    """由Begin/EndArrow推断方向: end箭头→src到dst, begin箭头→dst到src."""
    begin_state = arrow_state(begin_arrow)
    end_state = arrow_state(end_arrow)
    if ARROW_UNKNOWN in (begin_state, end_state):
        return "undetermined"
    if begin_state == "arrow" and end_state == "arrow":
        return "bidirectional"
    if end_state == "arrow":
        return "directed_src_to_dst"
    if begin_state == "arrow":
        return "directed_dst_to_src"
    return "undetermined"


def _failure_row(
    doc_name: str, embed_index: str, source: object, failure_type: str, version: str, reason: str
) -> dict[str, Any]:
    return {
        "doc_name": doc_name,
        "embed_index": embed_index,
        "source": str(source or ""),
        "failure_type": failure_type,
        "version": version,
        "reason": reason,
    }


def align_structures(
    anchors_v2: dict[str, Any], anchors_v3: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """按(规范化doc名, embed_index)对齐两版structure.

    Returns:
        pairs: 结构键并集中每项 {doc_name, doc_id, embed_index, struct_v2, struct_v3}
               (单版缺失的一侧为None; v3侧存在→照常产出v3_only行)
        failures: 对齐失败记录(单版缺失 / 同版内embed_index重复)
    """
    index_v2: dict[tuple[str, str], dict[str, Any]] = {}
    index_v3: dict[tuple[str, str], dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for label, anchors, index in (
        ("v2", anchors_v2, index_v2),
        ("v3", anchors_v3, index_v3),
    ):
        for doc_name, payload in anchors.items():
            norm_doc = normalize_doc_name(doc_name)
            for position, struct in enumerate(payload.get("structures", [])):
                embed_index = str(struct.get("embed_index", position))
                key = (norm_doc, embed_index)
                if key in index:
                    failures.append(
                        _failure_row(
                            norm_doc,
                            embed_index,
                            struct.get("source", ""),
                            "duplicate_embed_index",
                            label,
                            "同版内embed_index重复, 保留首个出现",
                        )
                    )
                    continue
                index[key] = struct

    pairs: list[dict[str, Any]] = []
    for key in sorted(set(index_v2) | set(index_v3)):
        norm_doc, embed_index = key
        struct_v2 = index_v2.get(key)
        struct_v3 = index_v3.get(key)
        pairs.append(
            {
                "doc_name": norm_doc,
                "doc_id": doc_id_from_name(norm_doc),
                "embed_index": embed_index,
                "struct_v2": struct_v2,
                "struct_v3": struct_v3,
            }
        )
        if struct_v2 is None:
            failures.append(
                _failure_row(
                    norm_doc, embed_index, struct_v3.get("source", ""),
                    "missing_in_v2", "v3", "该structure仅存在于v3(以v3_only行产出)",
                )
            )
        elif struct_v3 is None:
            failures.append(
                _failure_row(
                    norm_doc, embed_index, struct_v2.get("source", ""),
                    "missing_in_v3", "v2", "该structure仅存在于v2(无v3基准, 不产出行)",
                )
            )
    return pairs, failures


def merge_structure(
    doc_id: str,
    diagram_id: str,
    struct_v3: dict[str, Any],
    struct_v2: dict[str, Any] | None,
) -> dict[str, Any]:
    """单图合并: v3节点/边为枚举基准, 按id对齐补v2独有字段.

    Returns: {node_rows, edge_rows, node_residuals, edge_residuals,
              node_drift, edge_drift}  (residuals=v2独有id, 已排序)
    """
    v2_nodes: dict[str, dict[str, Any]] = (
        {str(n.get("id", "")): n for n in struct_v2.get("nodes", [])} if struct_v2 else {}
    )
    v2_edges: dict[str, dict[str, Any]] = (
        {str(e.get("connector_id", "")): e for e in struct_v2.get("edges", [])} if struct_v2 else {}
    )

    node_id_map = {
        str(node.get("id", "")): stable_id("NOD", diagram_id, node.get("id", ""))
        for node in struct_v3.get("nodes", [])
    }

    node_rows: list[dict[str, Any]] = []
    node_drift: Counter[str] = Counter()
    for node in struct_v3.get("nodes", []):
        source_node_id = str(node.get("id", ""))
        v2_node = v2_nodes.pop(source_node_id, None)
        if v2_node is not None:
            for field in NODE_SHARED_DRIFT_FIELDS:
                if v2_node.get(field) != node.get(field):
                    node_drift[field] += 1
        from_v2 = [name for name in NODE_FIELDS_FROM_V2 if v2_node is not None and name in v2_node]
        from_v3 = [out for src, out in NODE_FIELDS_FROM_V3 if src in node]
        geometry = {key: node.get(key) for key in ("cx", "cy", "w", "h", "rx", "ry")}
        geometry["bbox"] = v2_node.get("bbox") if v2_node is not None and "bbox" in v2_node else None
        node_rows.append(
            {
                "node_id": stable_id("NOD", diagram_id, node.get("id", "")),
                "diagram_id": diagram_id,
                "doc_id": doc_id,
                "source_node_id": source_node_id,
                "text_raw": node.get("text", ""),
                "type_candidate": node.get("type", "unknown"),
                "master_type": v2_node.get("master_type") if v2_node is not None else None,
                "via_master": v2_node.get("via_master") if v2_node is not None else None,
                "geometry": geometry,
                "fields_provenance": {"from_v2": from_v2, "from_v3": from_v3},
                "parse_status": "merged" if v2_node is not None else "v3_only",
            }
        )

    edge_rows: list[dict[str, Any]] = []
    edge_drift: Counter[str] = Counter()
    for index, edge in enumerate(struct_v3.get("edges", [])):
        connector_id = str(edge.get("connector_id", index))
        v2_edge = v2_edges.pop(connector_id, None)
        if v2_edge is not None:
            for field in EDGE_SHARED_DRIFT_FIELDS:
                if v2_edge.get(field) != edge.get(field):
                    edge_drift[field] += 1
        begin_arrow = edge.get("begin_arrow")
        end_arrow = edge.get("end_arrow")
        edge_rows.append(
            {
                "edge_id": stable_id("EDG", diagram_id, edge.get("connector_id", index)),
                "diagram_id": diagram_id,
                "doc_id": doc_id,
                "src_node": node_id_map.get(str(edge.get("src", "")), str(edge.get("src", ""))),
                "dst_node": node_id_map.get(str(edge.get("dst", "")), str(edge.get("dst", ""))),
                "connector_id": connector_id,
                "label_raw": edge.get("label", ""),
                "label_pos": (
                    v2_edge.get("label_pos")
                    if v2_edge is not None and "label_pos" in v2_edge
                    else None
                ),
                "waypoints": (
                    v2_edge.get("waypoints")
                    if v2_edge is not None and "waypoints" in v2_edge
                    else None
                ),
                "uml_type": edge.get("uml_type"),
                "line_pattern": edge.get("line_pattern"),
                "begin_arrow": begin_arrow,
                "end_arrow": end_arrow,
                "via": edge.get("via", "unknown"),
                "direction_status": infer_direction(begin_arrow, end_arrow),
                "parse_status": "merged" if v2_edge is not None else "v3_only",
            }
        )

    return {
        "node_rows": node_rows,
        "edge_rows": edge_rows,
        "node_residuals": sorted(v2_nodes),
        "edge_residuals": sorted(v2_edges),
        "node_drift": node_drift,
        "edge_drift": edge_drift,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def build(anchors_v2: dict[str, Any], anchors_v3: dict[str, Any]) -> dict[str, Any]:
    """纯函数: 两版锚点 → 合并行 + 对齐失败 + summary统计(无I/O)."""
    pairs, failures = align_structures(anchors_v2, anchors_v3)

    node_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    node_residuals = 0
    edge_residuals = 0
    node_drift: Counter[str] = Counter()
    edge_drift: Counter[str] = Counter()
    aligned_structures = 0
    v3_only_structures = 0
    v2_only_structures = 0

    for pair in pairs:
        struct_v3 = pair["struct_v3"]
        if struct_v3 is None:
            v2_only_structures += 1
            continue
        if pair["struct_v2"] is None:
            v3_only_structures += 1
        else:
            aligned_structures += 1
        diagram_id = stable_id(
            "DGM", pair["doc_id"], struct_v3.get("embed_index", pair["embed_index"])
        )
        merged = merge_structure(pair["doc_id"], diagram_id, struct_v3, pair["struct_v2"])
        node_rows.extend(merged["node_rows"])
        edge_rows.extend(merged["edge_rows"])
        node_residuals += len(merged["node_residuals"])
        edge_residuals += len(merged["edge_residuals"])
        node_drift.update(merged["node_drift"])
        edge_drift.update(merged["edge_drift"])

    merged_nodes = sum(1 for row in node_rows if row["parse_status"] == "merged")
    merged_edges = sum(1 for row in edge_rows if row["parse_status"] == "merged")
    master_present = sum(1 for row in node_rows if row["master_type"] is not None)
    master_nonempty = sum(1 for row in node_rows if row["master_type"])
    via_master_true = sum(1 for row in node_rows if row["via_master"] is True)
    via_master_false = sum(1 for row in node_rows if row["via_master"] is False)
    bbox_present = sum(1 for row in node_rows if row["geometry"]["bbox"] is not None)

    label_pos_present = sum(1 for row in edge_rows if row["label_pos"] is not None)
    waypoints_present = sum(1 for row in edge_rows if row["waypoints"] is not None)
    waypoints_nonempty = sum(
        1 for row in edge_rows if row["waypoints"] not in (None, [])
    )
    begin_arrow_present = sum(1 for row in edge_rows if row["begin_arrow"] is not None)
    end_arrow_present = sum(1 for row in edge_rows if row["end_arrow"] is not None)
    both_arrows_present = sum(
        1 for row in edge_rows
        if row["begin_arrow"] is not None and row["end_arrow"] is not None
    )
    uml_type_present = sum(1 for row in edge_rows if row["uml_type"] is not None)
    line_pattern_present = sum(1 for row in edge_rows if row["line_pattern"] is not None)

    direction_counts = Counter(row["direction_status"] for row in edge_rows)
    determinable = sum(
        direction_counts[status]
        for status in ("directed_src_to_dst", "directed_dst_to_src", "bidirectional")
    )
    undetermined_no_arrows = sum(
        1 for row in edge_rows
        if row["direction_status"] == "undetermined"
        and arrow_state(row["begin_arrow"]) == "absent"
        and arrow_state(row["end_arrow"]) == "absent"
    )
    undetermined_unknown_arrow = sum(
        1 for row in edge_rows
        if row["direction_status"] == "undetermined"
        and ARROW_UNKNOWN in (arrow_state(row["begin_arrow"]), arrow_state(row["end_arrow"]))
    )

    structure_keys = len(pairs)
    summary: dict[str, Any] = {
        "builder": "tools/build_visio_features_v2.py",
        "schema_version": SCHEMA_VERSION,
        "enumeration_base": (
            "v3 (node_id/edge_id/diagram_id与structured_corpus_v1的DGM/NOD/EDG映射一致)"
        ),
        "parent_depth_status": PARENT_DEPTH_STATUS,
        "parent_depth_note": PARENT_DEPTH_NOTE,
        "residual_policy": (
            "v2独有节点/边不进输出(v3为枚举基准), 计数入本summary, 不静默丢弃"
        ),
        "alignment": {
            "structures_v2": sum(
                len(payload.get("structures", [])) for payload in anchors_v2.values()
            ),
            "structures_v3": sum(
                len(payload.get("structures", [])) for payload in anchors_v3.values()
            ),
            "structure_keys": structure_keys,
            "aligned_structures": aligned_structures,
            "v3_only_structures": v3_only_structures,
            "v2_only_structures": v2_only_structures,
            "alignment_failures": len(failures),
            "structure_alignment_rate": _rate(aligned_structures, structure_keys),
            "node_match_rate": _rate(merged_nodes, len(node_rows)),
            "edge_match_rate": _rate(merged_edges, len(edge_rows)),
        },
        "nodes": {
            "emitted": len(node_rows),
            "merged": merged_nodes,
            "v3_only": len(node_rows) - merged_nodes,
            "v2_only_residual": node_residuals,
            "master_type_present": master_present,
            "master_type_coverage": _rate(master_present, len(node_rows)),
            "master_type_nonempty": master_nonempty,
            "master_type_nonempty_coverage": _rate(master_nonempty, len(node_rows)),
            "via_master_true": via_master_true,
            "via_master_false": via_master_false,
            "bbox_present": bbox_present,
            "bbox_coverage": _rate(bbox_present, len(node_rows)),
        },
        "edges": {
            "emitted": len(edge_rows),
            "merged": merged_edges,
            "v3_only": len(edge_rows) - merged_edges,
            "v2_only_residual": edge_residuals,
            "label_pos_present": label_pos_present,
            "label_pos_coverage": _rate(label_pos_present, len(edge_rows)),
            "waypoints_present": waypoints_present,
            "waypoints_coverage": _rate(waypoints_present, len(edge_rows)),
            "waypoints_nonempty": waypoints_nonempty,
            "begin_arrow_present": begin_arrow_present,
            "end_arrow_present": end_arrow_present,
            "arrow_coverage": _rate(both_arrows_present, len(edge_rows)),
            "uml_type_present": uml_type_present,
            "line_pattern_present": line_pattern_present,
        },
        "direction": {
            "counts": {status: direction_counts[status] for status in DIRECTION_STATUSES},
            "determinable": determinable,
            "determinable_rate": _rate(determinable, len(edge_rows)),
            "undetermined_reasons": {
                "no_arrows": undetermined_no_arrows,
                "unknown_arrow": undetermined_unknown_arrow,
            },
            "rule": (
                "end_arrow有箭头→directed_src_to_dst; begin_arrow有箭头→directed_dst_to_src; "
                "双端→bidirectional; none+none或任一端unknown→undetermined"
            ),
        },
        "field_drift": {
            "policy": "两版共有字段取v3(与structured_corpus_v1一致), 此处记录两版取值不一致计数",
            "nodes": dict(sorted(node_drift.items())),
            "edges": dict(sorted(edge_drift.items())),
        },
    }
    return {"node_rows": node_rows, "edge_rows": edge_rows, "failures": failures, "summary": summary}


def _load_anchors(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"锚点文件应为dict[doc名→payload]: {path}")
    return data


def write_outputs(
    output: Path,
    node_rows: list[dict[str, Any]],
    edge_rows: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """落盘: 3个jsonl + summary.json + manifest.json(全确定性, 可重复构建)."""
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / "visio_nodes_v2.jsonl", node_rows)
    write_jsonl(output / "visio_edges_v2.jsonl", edge_rows)
    write_jsonl(output / "alignment_failures.jsonl", failures)
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "files": {
            name: sha256_file(output / f"{name}.jsonl")
            for name in ("visio_nodes_v2", "visio_edges_v2", "alignment_failures")
        },
        "summary_sha256": sha256_file(output / "summary.json"),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def _rel_path(path: Path) -> str:
    """仓库相对路径(不在仓库内则原样), 保证summary跨机器确定."""
    try:
        return str(path.resolve().relative_to(BASE))
    except ValueError:
        return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anchor-v2", type=Path, default=ANCHOR_V2_PATH)
    parser.add_argument("--anchor-v3", type=Path, default=ANCHOR_V3_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    anchors_v2 = _load_anchors(args.anchor_v2)
    anchors_v3 = _load_anchors(args.anchor_v3)
    built = build(anchors_v2, anchors_v3)
    summary = built["summary"]
    summary["sources"] = {
        "anchor_v2": {
            "path": _rel_path(args.anchor_v2),
            "sha256": sha256_file(args.anchor_v2),
        },
        "anchor_v3": {
            "path": _rel_path(args.anchor_v3),
            "sha256": sha256_file(args.anchor_v3),
        },
    }
    write_outputs(
        args.output, built["node_rows"], built["edge_rows"], built["failures"], summary
    )

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    alignment = summary["alignment"]
    print(
        json.dumps(
            {
                "output": str(args.output),
                "structures": alignment["structure_keys"],
                "alignment_failures": alignment["alignment_failures"],
                "nodes_emitted": summary["nodes"]["emitted"],
                "edges_emitted": summary["edges"]["emitted"],
                "master_type_coverage": summary["nodes"]["master_type_coverage"],
                "waypoints_coverage": summary["edges"]["waypoints_coverage"],
                "label_pos_coverage": summary["edges"]["label_pos_coverage"],
                "arrow_coverage": summary["edges"]["arrow_coverage"],
                "direction_determinable_rate": summary["direction"]["determinable_rate"],
                "parent_depth_status": PARENT_DEPTH_STATUS,
            },
            ensure_ascii=False,
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
