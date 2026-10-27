#!/usr/bin/env python3
"""semantic_features_v2: SRS图语义/实体/对齐特征抽取(8格, 确定性/离线).

格子与输入输出:
1. lanes.jsonl               泳道检测: boundary或(w>60%页宽且h>60%页高)大矩形→lane_container,
                              内部节点按cy分带(间距<0.5in聚带); 无container→no_lane_detected.
2. graph_structures.jsonl    图算法: 环=SCC(>1节点)+自环; fork=出度≥2∧type含fork/gateway;
                              join=入度≥2∧type含gateway/join/merge.
3. usecase_relations.jsonl   scene_models的uc_relations按kind透传(include/extend/unknown).
4. interface_semantics.jsonl 接口方向: connections/interfaces元组 × anchors_v3同doc边
                              (begin/end_arrow→a_to_b/b_to_a/bidirectional/undirected);
                              协议候选: 词典(TCP/UDP/HTTP/API/网络/消息)命中接口名+接口表行;
                              数据项候选: 接口表(接口caption∧发送方/接收方表头)的
                              接口内容/描述列与"xx接口数据元素说明"表的数据集/数据组成列.
5. state_transitions.jsonl   状态图候选: 含state节点且存在state-state边的图→
                              迁移表{state,events(边label),next_state}.
                              图-caption与diagram在语料中无链接键, caption仅作doc级统计.
6. entity_type_v2.jsonl      requirement/diagram_node/claim的title或text词典分类:
                              分系统(含分系统/服务结尾)>模块>接口(含接口|ID含-NBJK-)
                              >参数(srs_kb param_dictionary同义词)>数据项(含数据)>功能(默认).
7. interface_alignment.jsonl 接口图connection×接口表(表头含发送方/接收方)按接口名
                              精确/包含匹配; direction_consistency=图箭头方向vs表发送→接收.
8. alignment_status_v2.jsonl anchor_expansion_v1/anchors.jsonl的layer三档化:
                              L1→explicit, L2→supported, 无/其他→speculative.

输出根目录: data/gjb_438c/semantic_features_v2/ (8个jsonl + summary.json + manifest.json).
全部为候选级特征(非金标); 排序键稳定可复现.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.build_evidence_graph import read_jsonl, sha256, write_jsonl

SCHEMA_VERSION = "semantic_features_v2"
TOOL_NAME = "build_semantic_features_v2"

DEFAULT_SCENE_MODELS = BASE / "data/gjb_438c/anchor_v2/scene_models.json"
DEFAULT_ANCHORS_V3 = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
DEFAULT_CORPUS = BASE / "data/gjb_438c/structured_corpus_v1"
DEFAULT_KB = BASE / "knowledge/srs_kb.json"
DEFAULT_EXPANSION = BASE / "data/gjb_438c/anchor_expansion_v1"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/semantic_features_v2"

LANE_BAND_GAP_IN = 0.5
LANE_MIN_W_RATIO = 0.6
LANE_MIN_H_RATIO = 0.6
DEFAULT_PAGE_W = 8.5
DEFAULT_PAGE_H = 11.0

NAV_END = {"filled_triangle", "filled_circle_s", "closed", "open_60", "open",
           "filled_diamond_s", "filled_square", "block"}
NAV_BEGIN = {"filled_square", "filled_circle_s", "filled_triangle", "open"}

FORK_TYPE_TOKENS = ("fork", "gateway")
JOIN_TYPE_TOKENS = ("gateway", "join", "merge")
STATE_TYPE = "state"
PSEUDO_STATE_TYPES = ("start", "end")
STATE_CAPTION_TOKENS = ("状态", "初始", "最终")

PROTOCOL_TERMS = ("TCP", "UDP", "HTTP", "API", "网络", "消息")
NAME_HEADER_CANDIDATES = ("接口名称/标识", "接口需求名称", "接口名称", "名称")
TYPE_HEADER = "接口类型"
SENDER_HEADER = "发送方"
RECEIVER_HEADER = "接收方"
CONTENT_HEADER_CANDIDATES = ("接口内容", "接口描述", "接口需求描述")
DATA_ITEM_HEADER_TOKENS = ("数据集名称", "数据组成", "数据内容",
                           "接口内容", "接口描述", "接口需求描述")
ITEM_SPLIT_RE = re.compile(r"[、，,;；/]")
STRIP_CHARS = "。；;，,、 \t"

ENTITY_TYPE_SUBSYSTEM = "分系统"
ENTITY_TYPE_MODULE = "模块"
ENTITY_TYPE_INTERFACE = "接口"
ENTITY_TYPE_PARAM = "参数"
ENTITY_TYPE_DATA_ITEM = "数据项"
ENTITY_TYPE_FUNCTION = "功能"

_WS_RE = re.compile(r"[\s\u3000]+")


def norm_name(text: str | None) -> str:
    """名称归一化: 去全部空白(含全角空格/换行), 供接口名/系统名匹配."""
    return _WS_RE.sub("", text or "")


def name_match(left: str, right: str) -> bool:
    """归一化后精确相等或包含(双方归一化长度≥3才允许包含)."""
    a, b = norm_name(left), norm_name(right)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 3 and len(b) >= 3 and (a in b or b in a):
        return True
    return False


def split_items(cell: str | None) -> list[str]:
    """数据项候选拆分: 按[、，,;；/]切分并去标点/占位符."""
    items = []
    for part in ITEM_SPLIT_RE.split(cell or ""):
        token = (part or "").strip(STRIP_CHARS)
        if token and token not in {"-", "—", "——"}:
            items.append(token)
    return items


def arrow_dir(begin_arrow: str | None, end_arrow: str | None) -> str:
    """边箭头语义: forward=src→dst, backward=dst→src, bidirectional, none=无箭头."""
    forward = (end_arrow or "") in NAV_END
    backward = (begin_arrow or "") in NAV_BEGIN
    if forward and backward:
        return "bidirectional"
    if forward:
        return "forward"
    if backward:
        return "backward"
    return "none"


def protocol_hits(*texts: str | None) -> list[str]:
    """协议词典命中(TCP/UDP/HTTP/API/网络/消息; ASCII词大小写不敏感)."""
    hits = set()
    for term in PROTOCOL_TERMS:
        for text in texts:
            if not text:
                continue
            if term.isascii():
                if term.lower() in text.lower():
                    hits.add(term)
                    break
            elif term in text:
                hits.add(term)
                break
    return sorted(hits)


def _geometry(node: dict[str, Any]) -> tuple[float, float, float, float]:
    geo = node.get("geometry") or {}
    try:
        cx = float(geo.get("cx") or 0.0)
        cy = float(geo.get("cy") or 0.0)
        w = float(geo.get("w") or 0.0)
        h = float(geo.get("h") or 0.0)
    except (TypeError, ValueError):
        return 0.0, 0.0, 0.0, 0.0
    return cx, cy, w, h


def band_by_y(nodes: list[dict[str, Any]], gap: float = LANE_BAND_GAP_IN) -> list[dict[str, Any]]:
    """按cy一维聚类分带: 相邻间距<gap聚为同带; 返回[{y_min,y_max,nodes}](按y升序)."""
    keyed = sorted(
        ((node, _geometry(node)[1]) for node in nodes),
        key=lambda pair: (pair[1], pair[0].get("node_id") or ""),
    )
    bands: list[dict[str, Any]] = []
    for node, cy in keyed:
        if bands and cy - bands[-1]["y_max"] < gap:
            bands[-1]["y_max"] = cy
            bands[-1]["nodes"].append(node)
        else:
            bands.append({"y_min": cy, "y_max": cy, "nodes": [node]})
    return bands


def detect_lanes(diagram_id: str, nodes: list[dict[str, Any]],
                 page_w: float, page_h: float) -> dict[str, Any]:
    """单图泳道检测: lane_container=boundary或大矩形(取最大面积候选), 内部节点y分带."""
    candidates: list[tuple[float, dict[str, Any], list[str]]] = []
    for node in nodes:
        _, _, w, h = _geometry(node)
        basis = []
        if (node.get("type_candidate") or "") == "boundary":
            basis.append("type=boundary")
        if w > LANE_MIN_W_RATIO * page_w and h > LANE_MIN_H_RATIO * page_h:
            basis.append(f"big_rect(w={w / page_w:.2f}pw,h={h / page_h:.2f}ph)")
        if basis:
            candidates.append((w * h, node, basis))
    record: dict[str, Any] = {
        "diagram_id": diagram_id,
        "n_nodes": len(nodes),
        "lanes_status": "no_lane_detected",
        "lane_container": None,
        "n_lanes": 0,
        "n_banded_nodes": 0,
        "lanes": [],
    }
    if not candidates:
        return record
    container = max(candidates, key=lambda item: item[0])[1]
    container_ids = {c[1].get("node_id") for c in candidates}
    ccx, ccy, cw, ch = _geometry(container)
    inside = []
    for node in nodes:
        if node.get("node_id") in container_ids:
            continue
        cx, cy, _, _ = _geometry(node)
        if (node.get("geometry") or {}) and abs(cx - ccx) <= cw / 2 and abs(cy - ccy) <= ch / 2:
            inside.append(node)
    bands = band_by_y(inside, LANE_BAND_GAP_IN)
    lanes = []
    for index, band in enumerate(bands):
        lane_id = f"{diagram_id}::LANE-{index:02d}"
        lanes.append({
            "lane_id": lane_id,
            "lane_index": index,
            "y_min": round(band["y_min"], 4),
            "y_max": round(band["y_max"], 4),
            "nodes": [{
                "node_id": node.get("node_id"),
                "source_node_id": node.get("source_node_id"),
                "text_raw": node.get("text_raw") or "",
                "lane_id": lane_id,
            } for node in band["nodes"]],
        })
    container_basis = next(basis for area, node, basis in candidates
                           if node.get("node_id") == container.get("node_id"))
    record.update({
        "lanes_status": "lane_detected",
        "lane_container": {
            "node_id": container.get("node_id"),
            "source_node_id": container.get("source_node_id"),
            "text_raw": container.get("text_raw") or "",
            "type_candidate": container.get("type_candidate") or "",
            "geometry": {"cx": ccx, "cy": ccy, "w": cw, "h": ch},
            "container_basis": container_basis,
        },
        "n_lanes": len(lanes),
        "n_banded_nodes": sum(len(lane["nodes"]) for lane in lanes),
        "lanes": lanes,
    })
    return record


def tarjan_scc(adj: dict[str, set[str]]) -> list[list[str]]:
    """迭代Tarjan强连通分量; 返回每个分量的有序节点列表(确定性)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[list[str]] = []
    counter = 0
    for root in sorted(adj):
        if root in index:
            continue
        work: list[tuple[str, Any]] = [(root, iter(sorted(adj[root])))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, successors = work[-1]
            next_node = None
            for succ in successors:
                if succ not in index:
                    next_node = succ
                    break
                if succ in on_stack:
                    low[node] = min(low[node], index[succ])
            if next_node is None:
                work.pop()
                if low[node] == index[node]:
                    component = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    sccs.append(sorted(component))
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[node])
            else:
                index[next_node] = low[next_node] = counter
                counter += 1
                stack.append(next_node)
                on_stack.add(next_node)
                work.append((next_node, iter(sorted(adj[next_node]))))
    return sccs


def detect_graph_structures(diagram_id: str, doc_id: str,
                            nodes: list[dict[str, Any]],
                            edges: list[dict[str, Any]]) -> dict[str, Any]:
    """单图环/fork/join检测(边按src→dst建图)."""
    node_by_src = {}
    for node in sorted(nodes, key=lambda n: n.get("node_id") or ""):
        node_by_src.setdefault(node.get("source_node_id"), node)
    adj: dict[str, set[str]] = defaultdict(set)
    self_loop_srcs: set[str] = set()
    for edge in edges:
        src = edge.get("source_node_id")
        dst = edge.get("target_node_id")
        if not src or not dst:
            continue
        if src == dst:
            self_loop_srcs.add(src)
        adj[src].add(dst)
    for node in nodes:
        adj.setdefault(node.get("source_node_id"), set())

    def texts_of(src_ids: list[str]) -> list[str]:
        return [(node_by_src.get(sid) or {}).get("text_raw") or "" for sid in src_ids]

    loops = []
    for component in tarjan_scc(adj):
        if len(component) > 1:
            loops.append({
                "kind": "scc",
                "cycle_nodes": [node_by_src.get(sid, {}).get("node_id") or sid for sid in component],
                "cycle_texts": texts_of(component),
            })
    for sid in sorted(self_loop_srcs):
        node = node_by_src.get(sid) or {}
        loops.append({
            "kind": "self_loop",
            "cycle_nodes": [node.get("node_id") or sid],
            "cycle_texts": [node.get("text_raw") or ""],
        })

    out_degree: dict[str, int] = {src: len(targets) for src, targets in adj.items()}
    in_degree: Counter = Counter()
    for src, targets in adj.items():
        for target in targets:
            in_degree[target] += 1
    forks, joins = [], []
    for node in sorted(nodes, key=lambda n: n.get("node_id") or ""):
        src = node.get("source_node_id")
        node_type = node.get("type_candidate") or ""
        if out_degree.get(src, 0) >= 2 and any(tok in node_type for tok in FORK_TYPE_TOKENS):
            forks.append({
                "node_id": node.get("node_id"),
                "text_raw": node.get("text_raw") or "",
                "node_type": node_type,
                "out_degree": out_degree.get(src, 0),
            })
        if in_degree.get(src, 0) >= 2 and any(tok in node_type for tok in JOIN_TYPE_TOKENS):
            joins.append({
                "node_id": node.get("node_id"),
                "text_raw": node.get("text_raw") or "",
                "node_type": node_type,
                "in_degree": in_degree.get(src, 0),
            })

    has_loops = bool(loops)
    has_fork_join = bool(forks or joins)
    if has_loops and has_fork_join:
        status = "loop_and_fork_join"
    elif has_loops:
        status = "loop_found"
    elif has_fork_join:
        status = "fork_join_found"
    else:
        status = "plain"
    return {
        "diagram_id": diagram_id,
        "doc_id": doc_id,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "loops": loops,
        "forks": forks,
        "joins": joins,
        "has_loops": has_loops,
        "has_forks": bool(forks),
        "has_joins": bool(joins),
        "status": status,
    }


def detect_state_diagram(diagram_id: str, doc_id: str,
                         nodes: list[dict[str, Any]],
                         edges: list[dict[str, Any]]) -> dict[str, Any] | None:
    """状态图候选: 含state节点且存在state-state边; 迁移表{state,events,next_state}."""
    node_by_src = {node.get("source_node_id"): node for node in nodes}
    state_nodes = [n for n in nodes if (n.get("type_candidate") or "") == STATE_TYPE]
    pseudo_nodes = [n for n in nodes if (n.get("type_candidate") or "") in PSEUDO_STATE_TYPES]
    state_srcs = {n.get("source_node_id") for n in state_nodes}
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in sorted(edges, key=lambda e: e.get("edge_id") or ""):
        src, dst = edge.get("source_node_id"), edge.get("target_node_id")
        if src not in state_srcs or dst not in state_srcs:
            continue
        src_text = (node_by_src.get(src) or {}).get("text_raw") or ""
        dst_text = (node_by_src.get(dst) or {}).get("text_raw") or ""
        key = (src or "", dst or "")
        entry = grouped.setdefault(key, {
            "state": src_text,
            "next_state": dst_text,
            "events": [],
            "edge_ids": [],
        })
        label = (edge.get("label_raw") or "").strip()
        if label and label not in entry["events"]:
            entry["events"].append(label)
        entry["edge_ids"].append(edge.get("edge_id"))
    if not state_nodes or not grouped:
        return None
    transitions = [grouped[key] for key in sorted(grouped)]
    return {
        "diagram_id": diagram_id,
        "doc_id": doc_id,
        "status": "state_diagram_candidate",
        "basis": {
            "n_state_nodes": len(state_nodes),
            "n_start_end_nodes": len(pseudo_nodes),
            "n_state_state_edges": sum(len(t["edge_ids"]) for t in transitions),
        },
        "n_state_nodes": len(state_nodes),
        "n_start_end_nodes": len(pseudo_nodes),
        "n_transitions": len(transitions),
        "transitions": transitions,
    }


def build_param_terms(kb: dict[str, Any]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """srs_kb param_dictionary → (中文术语表, 英文小写术语表), 各为(术语,参数键)."""
    cn_terms: set[tuple[str, str]] = set()
    en_terms: set[tuple[str, str]] = set()
    for key, entry in (kb.get("param_dictionary") or {}).items():
        if not isinstance(entry, dict):
            continue
        for term in [entry.get("canonical_cn")] + list(entry.get("synonyms_cn") or []):
            if term:
                cn_terms.add((term, key))
        for term in [entry.get("canonical_en")] + list(entry.get("synonyms_en") or []):
            if term:
                en_terms.add((term.strip().lower(), key))
    return sorted(cn_terms), sorted(en_terms)


def classify_entity(text: str | None, requirement_id: str = "",
                    cn_param_terms: list[tuple[str, str]] | None = None,
                    en_param_terms: list[tuple[str, str]] | None = None) -> tuple[str, str]:
    """词典实体分类(优先级: 分系统>模块>接口>参数>数据项>功能默认)."""
    target = (text or "").strip()
    if not target:
        return ENTITY_TYPE_FUNCTION, "default:no_text"
    if "分系统" in target:
        return ENTITY_TYPE_SUBSYSTEM, "dict:分系统:含分系统"
    if target.endswith("服务"):
        return ENTITY_TYPE_SUBSYSTEM, "dict:分系统:服务结尾"
    if "模块" in target:
        return ENTITY_TYPE_MODULE, "dict:模块:含模块"
    if "接口" in target:
        return ENTITY_TYPE_INTERFACE, "dict:接口:含接口"
    if requirement_id and "-NBJK-" in requirement_id:
        return ENTITY_TYPE_INTERFACE, "dict:接口:id含-NBJK-"
    for term, key in cn_param_terms or []:
        if term in target:
            return ENTITY_TYPE_PARAM, f"dict:参数:param_dict:{key}"
    lowered = target.lower()
    for term, key in en_param_terms or []:
        if term and term in lowered:
            return ENTITY_TYPE_PARAM, f"dict:参数:param_dict:{key}"
    if "数据" in target:
        return ENTITY_TYPE_DATA_ITEM, "dict:数据项:含数据"
    return ENTITY_TYPE_FUNCTION, "default:功能"


def interface_tuples(models: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """interface_diagram模型的连接元组: connections优先, 否则由interfaces.connects合成."""
    tuples = []
    for model_index, model in enumerate(models):
        if (model.get("diagram_type") or "") != "interface_diagram":
            continue
        connections = model.get("connections") or []
        if connections:
            for conn in connections:
                tuples.append({
                    "model_index": model_index,
                    "tuple_source": "connections",
                    "interface": conn.get("interface") or "",
                    "system_a": conn.get("system_a") or "",
                    "system_b": conn.get("system_b") or "",
                })
            continue
        for item in model.get("interfaces") or []:
            connects = item.get("connects") or []
            tuples.append({
                "model_index": model_index,
                "tuple_source": "interfaces",
                "interface": item.get("name") or "",
                "system_a": connects[0] if len(connects) > 0 else "",
                "system_b": connects[1] if len(connects) > 1 else "",
            })
    return tuples


def structured_interface_rows(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """表头含发送方/接收方的接口表 → 结构化行(name/sender/receiver/type/content)."""
    rows = []
    for table in sorted(tables, key=lambda t: t.get("table_id") or ""):
        header = table.get("header_candidate") or []
        if SENDER_HEADER not in header or RECEIVER_HEADER not in header:
            continue
        name_col = next((i for i, cell in enumerate(header)
                         if cell in NAME_HEADER_CANDIDATES), None)
        if name_col is None:
            continue
        type_col = header.index(TYPE_HEADER) if TYPE_HEADER in header else None
        content_col = next((i for i, cell in enumerate(header)
                            if cell in CONTENT_HEADER_CANDIDATES), None)
        send_col = header.index(SENDER_HEADER)
        recv_col = header.index(RECEIVER_HEADER)
        table_rows = table.get("rows") or []
        for row_index, row in enumerate(table_rows):
            if len(row) != len(header) or list(row) == list(header):
                continue
            name_cell = row[name_col] or ""
            if not norm_name(name_cell) or name_cell == header[name_col]:
                continue
            rows.append({
                "table_id": table.get("table_id"),
                "caption_raw": table.get("caption_raw") or "",
                "row_index": row_index,
                "name_cell": name_cell,
                "iface_type": (row[type_col] or "") if type_col is not None else "",
                "sender": row[send_col] or "",
                "receiver": row[recv_col] or "",
                "content": (row[content_col] or "") if content_col is not None else "",
            })
    return rows


def match_structured_row(rows: list[dict[str, Any]],
                         interface_name: str) -> tuple[dict[str, Any] | None, str | None]:
    """接口名×结构化接口表行: 精确(含'名称/ID'按'/'拆分)优先, 其次包含."""
    target = norm_name(interface_name)
    if len(target) < 2:
        return None, None
    best: tuple[int, str, dict[str, Any]] | None = None
    for row in rows:
        cell = norm_name(row["name_cell"])
        parts = [norm_name(part) for part in (row["name_cell"] or "").split("/")]
        level = None
        if cell == target or target in parts:
            level = "exact"
        elif len(target) >= 3 and len(cell) >= 3 and (target in cell or cell in target):
            level = "contains"
        if level is None:
            continue
        rank = 0 if level == "exact" else 1
        if best is None or rank < best[0]:
            best = (rank, level, row)
        if best[0] == 0:
            break
    if best is None:
        return None, None
    return best[2], best[1]


def element_table_matches(tables: list[dict[str, Any]],
                          interface_name: str) -> list[dict[str, Any]]:
    """接口caption表(如'xx接口数据元素说明')按caption包含接口名匹配(容错去前缀'与')."""
    target = norm_name(interface_name)
    stripped = target[1:] if target.startswith("与") else target
    matches = []
    for table in sorted(tables, key=lambda t: t.get("table_id") or ""):
        caption = norm_name(table.get("caption_raw") or "")
        if "接口" not in caption:
            continue
        if (len(target) >= 3 and target in caption) or (len(stripped) >= 3 and stripped in caption):
            matches.append(table)
    return matches


def data_items_from_table(table: dict[str, Any]) -> list[str]:
    """表内数据项列(数据集名称/数据组成/接口内容等)的取值拆分."""
    header = table.get("header_candidate") or []
    columns = [i for i, cell in enumerate(header)
               if any(token in cell for token in DATA_ITEM_HEADER_TOKENS)]
    items: set[str] = set()
    for row in table.get("rows") or []:
        if len(row) != len(header) or list(row) == list(header):
            continue
        for col in columns:
            items.update(split_items(row[col] or ""))
    return sorted(items)


def connection_direction(system_a: str, system_b: str,
                         structures: list[dict[str, Any]]) -> tuple[str, list[str]]:
    """接口方向候选: anchors_v3同doc边中系统对匹配边, 由begin/end箭头投票."""
    a, b = norm_name(system_a), norm_name(system_b)
    votes: list[str] = []
    if len(a) >= 2 and len(b) >= 2:
        for structure in structures:
            for edge in structure.get("edges") or []:
                src = norm_name(edge.get("src_text"))
                dst = norm_name(edge.get("dst_text"))
                if not src or not dst:
                    continue
                src_a, src_b = name_match(src, a), name_match(src, b)
                dst_a, dst_b = name_match(dst, a), name_match(dst, b)
                if not ((src_a and dst_b) or (src_b and dst_a)):
                    continue
                direction = arrow_dir(edge.get("begin_arrow"), edge.get("end_arrow"))
                forward_pair = "a_to_b" if src_a else "b_to_a"
                backward_pair = "b_to_a" if src_a else "a_to_b"
                votes.append({
                    "forward": forward_pair,
                    "backward": backward_pair,
                    "bidirectional": "bidirectional",
                    "none": "undirected",
                }[direction])
    if not votes:
        return "unknown", votes
    unique = sorted(set(votes))
    if len(unique) == 1:
        return unique[0], votes
    return "mixed", votes


def table_direction(row: dict[str, Any], system_a: str, system_b: str) -> str:
    """接口表行方向: 发送方/接收方映射到system_a/system_b."""
    a, b = norm_name(system_a), norm_name(system_b)
    sender, receiver = norm_name(row.get("sender")), norm_name(row.get("receiver"))
    if name_match(sender, a) and name_match(receiver, b):
        return "a_to_b"
    if name_match(sender, b) and name_match(receiver, a):
        return "b_to_a"
    return "unmapped"


def direction_consistency(diagram_direction: str, table_dir: str) -> str:
    """图箭头方向 vs 表发送→接收: consistent/inconsistent/unknown."""
    if diagram_direction in ("unknown", "mixed", "undirected") or table_dir == "unmapped":
        return "unknown"
    if diagram_direction == "bidirectional":
        return "consistent"
    if diagram_direction == table_dir:
        return "consistent"
    return "inconsistent"


def alignment_status_of_layer(layer: str | None) -> str:
    """锚点层三档映射: L1→explicit, L2→supported, 无/其他→speculative."""
    if layer == "L1":
        return "explicit"
    if layer == "L2":
        return "supported"
    return "speculative"


def _doc_id_of(doc_name: str) -> str:
    match = re.match(r"(\d+)", doc_name)
    return match.group(1) if match else doc_name


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build(scene_models: Path, anchors_v3: Path, corpus: Path, kb_path: Path,
          expansion: Path, output: Path) -> dict[str, Any]:
    """全量构建8格语义特征; 返回summary(同时落盘summary.json/manifest.json)."""
    required = [
        ("anchor_v2/scene_models.json", scene_models),
        ("anchor_v3/anchors_v3.json", anchors_v3),
        ("structured_corpus_v1/diagrams.jsonl", corpus / "diagrams.jsonl"),
        ("structured_corpus_v1/diagram_nodes.jsonl", corpus / "diagram_nodes.jsonl"),
        ("structured_corpus_v1/diagram_edges.jsonl", corpus / "diagram_edges.jsonl"),
        ("structured_corpus_v1/tables.jsonl", corpus / "tables.jsonl"),
        ("structured_corpus_v1/requirements.jsonl", corpus / "requirements.jsonl"),
        ("structured_corpus_v1/claims.jsonl", corpus / "claims.jsonl"),
        ("knowledge/srs_kb.json", kb_path),
        ("anchor_expansion_v1/anchors.jsonl", expansion / "anchors.jsonl"),
    ]
    missing = [label for label, path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required inputs: {missing}")

    models = _read_json(scene_models)
    anchors = _read_json(anchors_v3)
    kb = _read_json(kb_path)
    diagrams = read_jsonl(corpus / "diagrams.jsonl")
    nodes = read_jsonl(corpus / "diagram_nodes.jsonl")
    edges = read_jsonl(corpus / "diagram_edges.jsonl")
    tables = read_jsonl(corpus / "tables.jsonl")
    requirements = read_jsonl(corpus / "requirements.jsonl")
    claims = read_jsonl(corpus / "claims.jsonl")
    expansion_anchors = read_jsonl(expansion / "anchors.jsonl")
    images = read_jsonl(corpus / "images.jsonl")

    nodes_by_diagram: dict[str, list[dict[str, Any]]] = defaultdict(list)
    edges_by_diagram: dict[str, list[dict[str, Any]]] = defaultdict(list)
    tables_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        nodes_by_diagram[node.get("diagram_id") or ""].append(node)
    for edge in edges:
        edges_by_diagram[edge.get("diagram_id") or ""].append(edge)
    for table in tables:
        tables_by_doc[table.get("doc_id") or ""].append(table)

    cn_param_terms, en_param_terms = build_param_terms(kb)

    lane_rows = []
    graph_rows = []
    state_rows = []
    state_node_diagrams_without_transitions = 0
    for diagram in sorted(diagrams, key=lambda d: d.get("diagram_id") or ""):
        diagram_id = diagram.get("diagram_id") or ""
        doc_id = diagram.get("doc_id") or ""
        page = diagram.get("page") or {}
        page_w = float(page.get("w") or DEFAULT_PAGE_W)
        page_h = float(page.get("h") or DEFAULT_PAGE_H)
        diagram_nodes = nodes_by_diagram.get(diagram_id, [])
        diagram_edges = edges_by_diagram.get(diagram_id, [])
        lane_rows.append(detect_lanes(diagram_id, diagram_nodes, page_w, page_h))
        graph_rows.append(detect_graph_structures(diagram_id, doc_id, diagram_nodes, diagram_edges))
        state_row = detect_state_diagram(diagram_id, doc_id, diagram_nodes, diagram_edges)
        if state_row is not None:
            state_rows.append(state_row)
        elif any((n.get("type_candidate") or "") == STATE_TYPE for n in diagram_nodes):
            state_node_diagrams_without_transitions += 1

    usecase_rows = []
    usecase_models = 0
    models_with_relations = 0
    uc_kind_counts: Counter = Counter()
    for doc_name in sorted(models):
        doc_models = (models[doc_name] or {}).get("models") or []
        for model_index, model in enumerate(doc_models):
            if (model.get("diagram_type") or "") == "usecase_diagram":
                usecase_models += 1
            relations = model.get("uc_relations") or []
            if relations:
                models_with_relations += 1
            for relation_index, relation in enumerate(relations):
                kind = relation.get("kind") or "unknown"
                uc_kind_counts[kind] += 1
                usecase_rows.append({
                    "doc_id": _doc_id_of(doc_name),
                    "doc_name": doc_name,
                    "model_index": model_index,
                    "diagram_type": model.get("diagram_type") or "",
                    "relation_index": relation_index,
                    "src": relation.get("src") or "",
                    "dst": relation.get("dst") or "",
                    "kind": kind,
                    "status": "passthrough",
                })

    semantics_rows = []
    alignment_rows = []
    direction_counts: Counter = Counter()
    consistency_counts: Counter = Counter()
    tuple_source_counts: Counter = Counter()
    matched_count = 0
    for doc_name in sorted(models):
        doc_id = _doc_id_of(doc_name)
        doc_models = (models[doc_name] or {}).get("models") or []
        structures = (anchors.get(doc_name) or {}).get("structures") or []
        doc_tables = tables_by_doc.get(doc_id, [])
        structured_rows = structured_interface_rows(doc_tables)
        for item in interface_tuples(doc_models):
            tuple_source_counts[item["tuple_source"]] += 1
            interface_name = item["interface"]
            system_a, system_b = item["system_a"], item["system_b"]
            direction, votes = connection_direction(system_a, system_b, structures)
            direction_counts[direction] += 1
            row, level = match_structured_row(structured_rows, interface_name)
            element_tables = element_table_matches(doc_tables, interface_name)
            protocol = protocol_hits(interface_name,
                                     row.get("iface_type") if row else "",
                                     row.get("content") if row else "")
            data_items: set[str] = set()
            if row:
                data_items.update(split_items(row.get("content")))
            for element_table in element_tables:
                data_items.update(data_items_from_table(element_table))
            semantics_rows.append({
                "doc_id": doc_id,
                "doc_name": doc_name,
                "model_index": item["model_index"],
                "tuple_source": item["tuple_source"],
                "interface": interface_name,
                "system_a": system_a,
                "system_b": system_b,
                "direction": direction,
                "direction_basis": {
                    "n_system_pair_edges": len(votes),
                    "vote_values": sorted(set(votes)),
                    "arrow_semantics": "NAV_END=end箭头(src→dst), NAV_BEGIN=begin箭头(dst→src)",
                },
                "protocol_candidates": protocol,
                "data_item_candidates": sorted(data_items),
                "table_match": {
                    "status": "matched" if row is not None else "unmatched",
                    "match_level": level,
                    "structured_row": row,
                    "element_table_ids": [t.get("table_id") for t in element_tables],
                },
            })
            diagram_direction = direction
            table_dir = table_direction(row, system_a, system_b) if row else "unmapped"
            consistency = direction_consistency(diagram_direction, table_dir)
            consistency_counts[consistency] += 1
            if row is not None:
                matched_count += 1
            alignment_rows.append({
                "doc_id": doc_id,
                "doc_name": doc_name,
                "model_index": item["model_index"],
                "tuple_source": item["tuple_source"],
                "interface": interface_name,
                "diagram_connection": {
                    "system_a": system_a,
                    "system_b": system_b,
                    "interface": interface_name,
                    "source": item["tuple_source"],
                },
                "table_row": row,
                "status": "matched" if row is not None else "unmatched",
                "match_level": level,
                "direction_diagram": diagram_direction,
                "direction_table": table_dir,
                "direction_consistency": consistency,
            })

    entity_rows = []
    entity_type_counts: Counter = Counter()
    entity_kind_counts: Counter = Counter()
    entity_basis_counts: Counter = Counter()
    for req in sorted(requirements, key=lambda r: (r.get("doc_id") or "", r.get("requirement_id") or "")):
        text = req.get("title") or req.get("raw_text") or ""
        entity_type, basis = classify_entity(text, req.get("requirement_id") or "",
                                             cn_param_terms, en_param_terms)
        entity_rows.append({
            "occurrence_id": req.get("requirement_id"),
            "kind": "requirement",
            "doc_id": req.get("doc_id"),
            "text": text,
            "entity_type": entity_type,
            "basis": basis,
        })
    for node in sorted(nodes, key=lambda n: (n.get("diagram_id") or "", n.get("node_id") or "")):
        entity_type, basis = classify_entity(node.get("text_raw"), "",
                                             cn_param_terms, en_param_terms)
        entity_rows.append({
            "occurrence_id": node.get("node_id"),
            "kind": "diagram_node",
            "doc_id": node.get("diagram_id"),
            "text": node.get("text_raw") or "",
            "entity_type": entity_type,
            "basis": basis,
        })
    for claim in sorted(claims, key=lambda c: (c.get("doc_id") or "", c.get("claim_id") or "")):
        entity_type, basis = classify_entity(claim.get("raw_text"), "",
                                             cn_param_terms, en_param_terms)
        entity_rows.append({
            "occurrence_id": claim.get("claim_id"),
            "kind": "claim",
            "doc_id": claim.get("doc_id"),
            "text": claim.get("raw_text") or "",
            "entity_type": entity_type,
            "basis": basis,
        })
    for row in entity_rows:
        entity_type_counts[row["entity_type"]] += 1
        entity_kind_counts[row["kind"]] += 1
        entity_basis_counts[row["basis"]] += 1

    status_rows = []
    tier_counts: Counter = Counter()
    layer_counts: Counter = Counter()
    for anchor in expansion_anchors:
        layer = anchor.get("layer")
        status = alignment_status_of_layer(layer)
        tier_counts[status] += 1
        layer_counts[layer or "none"] += 1
        status_rows.append({
            "anchor_id": anchor.get("anchor_id"),
            "doc_id": anchor.get("doc_id"),
            "layer": layer,
            "anchor_type": anchor.get("anchor_type"),
            "node_id": anchor.get("node_id"),
            "requirement_id": anchor.get("requirement_id"),
            "alignment_status_v2": status,
        })

    state_caption_images = sum(
        1 for image in images
        if any(token in (image.get("caption_raw") or "")
               for token in STATE_CAPTION_TOKENS)
        or "state" in (image.get("caption_raw") or "").lower()
    )

    output.mkdir(parents=True, exist_ok=True)
    files = {
        "lanes": write_jsonl(output / "lanes.jsonl", lane_rows),
        "graph_structures": write_jsonl(output / "graph_structures.jsonl", graph_rows),
        "usecase_relations": write_jsonl(output / "usecase_relations.jsonl", usecase_rows),
        "interface_semantics": write_jsonl(output / "interface_semantics.jsonl", semantics_rows),
        "state_transitions": write_jsonl(output / "state_transitions.jsonl", state_rows),
        "entity_type_v2": write_jsonl(output / "entity_type_v2.jsonl", entity_rows),
        "interface_alignment": write_jsonl(output / "interface_alignment.jsonl", alignment_rows),
        "alignment_status_v2": write_jsonl(output / "alignment_status_v2.jsonl", status_rows),
    }

    lane_status_counts: Counter = Counter(row["lanes_status"] for row in lane_rows)
    graph_status_counts: Counter = Counter(row["status"] for row in graph_rows)
    total_tuples = len(semantics_rows)
    n_loops = sum(len(row["loops"]) for row in graph_rows)
    scc_loops = sum(1 for row in graph_rows for loop in row["loops"] if loop["kind"] == "scc")
    self_loops = n_loops - scc_loops
    summary = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "policy": {
            "candidate_not_gold": "全部输出为词典/几何/图算法候选, 非人工金标",
            "state_caption_linkage": "语料中diagram与image caption无链接键, 状态图候选仅由节点类型判定",
        },
        "counts": {
            "docs_in_scene_models": len(models),
            "diagrams_total": len(diagrams),
            "files": files,
            "lanes": {
                "lane_detected_diagrams": lane_status_counts.get("lane_detected", 0),
                "no_lane_detected_diagrams": lane_status_counts.get("no_lane_detected", 0),
                "multiband_diagrams": sum(1 for row in lane_rows if row["n_lanes"] >= 2),
                "total_lanes": sum(row["n_lanes"] for row in lane_rows),
                "banded_nodes": sum(row["n_banded_nodes"] for row in lane_rows),
                "boundary_container_diagrams": sum(
                    1 for row in lane_rows
                    if row["lane_container"] and "type=boundary" in row["lane_container"]["container_basis"]
                ),
                "big_rect_container_diagrams": sum(
                    1 for row in lane_rows
                    if row["lane_container"] and any(b.startswith("big_rect") for b in row["lane_container"]["container_basis"])
                ),
            },
            "graph_structures": {
                "diagrams_with_loops": sum(1 for row in graph_rows if row["has_loops"]),
                "loops_total": n_loops,
                "scc_loops": scc_loops,
                "self_loops": self_loops,
                "forks_total": sum(len(row["forks"]) for row in graph_rows),
                "joins_total": sum(len(row["joins"]) for row in graph_rows),
                "status_dist": dict(graph_status_counts),
            },
            "usecase_relations": {
                "relations_total": len(usecase_rows),
                "by_kind": dict(uc_kind_counts),
                "usecase_models": usecase_models,
                "models_with_relations": models_with_relations,
            },
            "interface_semantics": {
                "tuples": total_tuples,
                "tuples_by_source": dict(tuple_source_counts),
                "direction_dist": dict(direction_counts),
                "tuples_with_protocol": sum(1 for row in semantics_rows if row["protocol_candidates"]),
                "tuples_with_data_items": sum(1 for row in semantics_rows if row["data_item_candidates"]),
            },
            "state_diagrams": {
                "candidates": len(state_rows),
                "transitions_total": sum(row["n_transitions"] for row in state_rows),
                "state_node_diagrams_without_transitions": state_node_diagrams_without_transitions,
                "state_caption_images": state_caption_images,
                "caption_diagram_linkage": "unavailable_in_corpus",
            },
            "entity_types": {
                "total": len(entity_rows),
                "by_kind": dict(entity_kind_counts),
                "by_type": dict(entity_type_counts),
                "by_basis": dict(entity_basis_counts),
            },
            "interface_alignment": {
                "tuples": total_tuples,
                "matched": matched_count,
                "unmatched": total_tuples - matched_count,
                "match_rate": round(matched_count / total_tuples, 4) if total_tuples else 0.0,
                "match_level_dist": dict(Counter(
                    row["match_level"] or "unmatched" for row in alignment_rows)),
                "direction_consistency_dist": dict(consistency_counts),
            },
            "alignment_status": {
                "explicit": tier_counts.get("explicit", 0),
                "supported": tier_counts.get("supported", 0),
                "speculative": tier_counts.get("speculative", 0),
                "by_layer": dict(layer_counts),
            },
        },
        "source_sha256": {label: sha256(path) for label, path in required},
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "inputs": {label: sha256(path) for label, path in required},
        "files": {name: {"sha256": sha256(output / f"{name}.jsonl"), "rows": rows}
                  for name, rows in files.items()},
        "summary_sha256": sha256(output / "summary.json"),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-models", type=Path, default=DEFAULT_SCENE_MODELS)
    parser.add_argument("--anchors-v3", type=Path, default=DEFAULT_ANCHORS_V3)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--kb", type=Path, default=DEFAULT_KB)
    parser.add_argument("--expansion", type=Path, default=DEFAULT_EXPANSION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    summary = build(args.scene_models.resolve(), args.anchors_v3.resolve(),
                    args.corpus.resolve(), args.kb.resolve(),
                    args.expansion.resolve(), args.output.resolve())
    counts = summary["counts"]
    lanes = counts["lanes"]
    graph = counts["graph_structures"]
    print(f"semantic_features_v2: {counts['diagrams_total']}图 / {counts['docs_in_scene_models']}doc")
    print(f"  [1]泳道: 检出{lanes['lane_detected_diagrams']}图 "
          f"(多带{lanes['multiband_diagrams']}) / 总带数{lanes['total_lanes']} / "
          f"无泳道{lanes['no_lane_detected_diagrams']}图")
    print(f"  [2]图结构: 循环图{graph['diagrams_with_loops']} "
          f"(环{graph['loops_total']}={graph['scc_loops']}SCC+{graph['self_loops']}自环) / "
          f"fork{graph['forks_total']} / join{graph['joins_total']}")
    uc = counts["usecase_relations"]
    print(f"  [3]用例关系: {uc['relations_total']}条 "
          f"include={uc['by_kind'].get('include', 0)} extend={uc['by_kind'].get('extend', 0)} "
          f"unknown={uc['by_kind'].get('unknown', 0)}")
    sem = counts["interface_semantics"]
    print(f"  [4]接口语义: {sem['tuples']}元组 方向分布{sem['direction_dist']} "
          f"协议命中{sem['tuples_with_protocol']} 数据项命中{sem['tuples_with_data_items']}")
    st = counts["state_diagrams"]
    print(f"  [5]状态图: 候选{st['candidates']}图 / 迁移{st['transitions_total']} "
          f"/ caption含状态图片{st['state_caption_images']}")
    ent = counts["entity_types"]
    print(f"  [6]实体分类: {ent['total']}条 分布{ent['by_type']}")
    al = counts["interface_alignment"]
    print(f"  [7]接口对齐: {al['matched']}/{al['tuples']} 匹配率{al['match_rate']} "
          f"一致性{al['direction_consistency_dist']}")
    tier = counts["alignment_status"]
    print(f"  [8]对齐三档: explicit={tier['explicit']} supported={tier['supported']} "
          f"speculative={tier['speculative']}")


if __name__ == "__main__":
    main()
