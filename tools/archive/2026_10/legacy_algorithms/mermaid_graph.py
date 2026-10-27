#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mermaid结构解析器: mermaid代码 → {节点/边/形状/标签/分支/拓扑特征}

支持 flowchart TD/LR 与 graph 语法:
  N123["标签"]        → process节点
  N124{"标签"}        → decision节点(分支)
  N125(["标签"])       → start/end端点
  A --> B             → 无条件边
  A -->|"条件"| B      → 条件边(异常流/分支)
"""
import re
from collections import defaultdict


NODE_RE = re.compile(
    r"([A-Za-z0-9_]+)\s*"
    r"(\(\[\s*(?:\"([^\"]*)\"|([^\]\[]*))\s*\]\)"      # stadium ([text])
    r"|\{(?:\"([^\"]*)\"|([^\"\}]*))\}"                 # decision {text}
    r"|\[(?:\"([^\"]*)\"|([^\"\[\]]*))\]"               # process [text]
    r"|\((?:\"([^\"]*)\"|([^\"()]*))\)"                 # data (text)
    r")")
EDGE_RE = re.compile(
    r"([A-Za-z0-9_]+)\s*-{1,2}>\s*(?:\|"
    r"(?:\"([^\"]*)\"|([^\"|>]*))\|\s*)?([A-Za-z0-9_]+)")


def parse_mermaid(code):
    """解析mermaid → 结构dict"""
    if not code:
        return {"nodes": [], "edges": [], "n_nodes": 0, "n_edges": 0,
                "n_decision": 0, "labels": [], "cond_edges": [], "starts": [],
                "ends": [], "decision_labels": [], "cond_labels": []}

    nodes = {}
    for m in NODE_RE.finditer(code):
        nid = m.group(1)
        label = None
        for g in (m.group(3), m.group(4), m.group(5), m.group(6),
                  m.group(7), m.group(8), m.group(9), m.group(10)):
            if g is not None and g.strip():
                label = g.strip()
                break
        raw = m.group(2) or ""
        shape = "process"
        if raw.startswith("{"):
            shape = "decision"
        elif raw.startswith("(["):
            shape = "terminal"
        elif raw.startswith("(") and not raw.startswith("(["):
            shape = "data"
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": label or "", "shape": shape}

    edges = []
    for m in EDGE_RE.finditer(code):
        src, cond, dst = m.group(1), m.group(2) or m.group(3), m.group(4)
        edges.append({"src": src, "dst": dst,
                      "cond": (cond.strip() if cond else ""),
                      "src_label": nodes.get(src, {}).get("label", ""),
                      "dst_label": nodes.get(dst, {}).get("label", "")})
    for e in edges:
        nodes.setdefault(e["src"], {"id": e["src"], "label": "", "shape": "process"})
        nodes.setdefault(e["dst"], {"id": e["dst"], "label": "", "shape": "process"})

    node_list = list(nodes.values())
    decisions = [n for n in node_list if n["shape"] == "decision"]
    cond_edges = [e for e in edges if e["cond"]]
    labels = [n["label"] for n in node_list if n["label"]]

    # 拓扑特征: 出入度(找起点/终点), 环检测
    outdeg = defaultdict(int)
    indeg = defaultdict(int)
    for e in edges:
        outdeg[e["src"]] += 1
        indeg[e["dst"]] += 1
    starts = [nodes[k]["label"] for k in outdeg if indeg.get(k, 0) == 0]
    ends = [nodes[k]["label"] for k in indeg if outdeg.get(k, 0) == 0]

    return {
        "n_nodes": len(node_list), "n_edges": len(edges),
        "n_decision": len(decisions),
        "nodes": node_list,
        "edges": edges,
        "labels": labels,
        "cond_edges": cond_edges,
        "starts": starts, "ends": ends,
        "decision_labels": [d["label"] for d in decisions],
        "cond_labels": [e["cond"] for e in cond_edges],
    }


def label_set(g):
    """节点标签集合(去空)"""
    return set(label for label in g["labels"] if len(label) >= 2)


def seq_from_edges(g):
    """从边推断主链顺序(最长简单路径近似: 按拓扑层)"""
    adj = defaultdict(list)
    indeg = defaultdict(int)
    ids = set()
    for e in g["edges"]:
        if not e["cond"]:
            adj[e["src"]].append(e["dst"])
            indeg[e["dst"]] += 1
        ids.add(e["src"])
        ids.add(e["dst"])
    order, layer = {}, 0
    frontier = [k for k in ids if indeg.get(k, 0) == 0]
    while frontier:
        for k in frontier:
            order[k] = layer
        nxt = []
        for k in frontier:
            for v in adj[k]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    nxt.append(v)
        frontier = nxt
        layer += 1
    label_of = {n["id"]: n["label"] for n in g["nodes"]}
    return [label_of.get(k, k) for k in sorted(order, key=lambda x: order[x])]


def diff_node_labels(g, table_steps):
    """图节点标签 vs 表格步骤: 双向差集"""
    gl = label_set(g)
    tl = set(s.strip() for s in table_steps if s and len(s.strip()) >= 2)
    # 标签前缀匹配去重(表步骤常含编号)
    def loose_match(a, b_set):
        for b in b_set:
            if a in b or b in a:
                return True
        return False
    only_graph = [label for label in gl if not loose_match(label, tl)]
    only_table = [t for t in tl if not loose_match(t, gl)]
    return only_graph, only_table
