#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一视图导出器: anchors_v2 → 类型分流的Mermaid + DOT.

背景(2026-09-09全量审计, 替换m12的导出半区):
  m12对373图100%硬编码flowchart → 121对用例图被错渲染
  (actor画成平行四边形/关联画成有向箭头/boundary当普通节点).
  本工具按锚点类型组成分流渲染, UML关系语义采用mermaid_v3已验证的约定:

  类型分流(classify_diagram):
    usecase    actor+usecase(或usecase占比≥0.4)
    state      纯state节点
    interface  纯interface/component节点
    flowchart  process/decision/start/end主导
    other      兜底(如实声明)

  Mermaid UML约定(usecase模式):
    subgraph "系统名"        ← boundary节点(按几何包含框住用例)
    (["用例名"])             ← usecase节点(stadium≈UML椭圆)
    ["👤 参与者名"]          ← actor节点(mermaid无棒人, 👤前缀标注)
    A --- B                  ← 关联(无向)
    A -.->|<<include>>| B    ← include/extend(按边标签判定)
    流程/网关图沿用标准形状.

  DOT出口(完整语义源码): ellipse=用例, plaintext+👤=参与者, cluster=boundary,
    box=process, diamond=decision, dir=none=关联.

输出: data/gjb_438c/anchor_v2/mermaid_export.json (覆盖m12产物, 增dot字段;
      m12的visual_verification.json不受影响)
之后: python tools/build_pair_md.py  重生成pair .md

用法: python tools/export_pair_views.py [--dry]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ANCHOR_V2 = BASE / "data/gjb_438c/anchor_v2/anchors_v2.json"
OUT_PATH = BASE / "data/gjb_438c/anchor_v2/mermaid_export.json"
RECOVERED_PATH = BASE / "data/gjb_438c/anchor_v2/recovered_edges.json"

# ═══════════════════════════════════════════════════════════════
# 类型判定
# ═══════════════════════════════════════════════════════════════

_FLOW_TYPES = ("process", "decision", "start", "end", "gateway", "fork")


# ═══════════════════════════════════════════════════════════════
# 几何类型精化(1_012教训: M0/M11的Master类型识别对部分图全败, 26节点全other)
# ═══════════════════════════════════════════════════════════════

def promote_containers(nodes: list[dict]) -> list[dict]:
    """几何容器提升: 'other'类型带文本的大框框住≥2个语义文本节点 → boundary.

    1_096教训: '查询名录结构信息'系统边界框typed other(M0类型规则未命中)
    → 渲染成扁平节点, 系统整体语义丢失. 阈值: w≥1.2且h≥0.8(边界框
    都是大框), 面积≥2×最大内节点(防止误提升).
    """
    text_nodes = [n for n in nodes if (n.get("text") or "").strip()]
    if len(text_nodes) < 3:
        return nodes
    out = []
    for n in nodes:
        if (n.get("type") == "other" and (n.get("text") or "").strip()
                and n.get("w", 0) >= 1.2 and n.get("h", 0) >= 0.8):
            contained = [t for t in text_nodes if t is not n and _inside(t, n)]
            if len(contained) >= 2:
                max_inner_area = max(
                    (t.get("w", 0) * t.get("h", 0) for t in contained),
                    default=0.0)
                if n.get("w", 0) * n.get("h", 0) >= 2 * max(max_inner_area, 0.05):
                    nt = dict(n)
                    nt["type"] = "boundary"
                    out.append(nt)
                    continue
        out.append(n)
    return out


def attach_edge_labels(nodes: list[dict],
                       edges: list[dict]) -> tuple[list[dict], list[dict]]:
    """线标注几何关联(接口图/其他图): 独立文本形状 → 就近连线段的边标签.

    3_016教训: 接口图的接口名(交互设备输入等9个)是独立文本形状,
    M0当节点渲染成扁平state; 真实语义是组件间连线上的标签
    (VLM读图: 10条带标签的有向边=5对组件×2).
    判定:
      组件 = 有文本 且(扁h≤0.25 或 边度≥2)   (3_016: 6个组件全中)
      标签 = 其余有文本节点
      吸附 = 标签中心到(组件A中心-组件B中心)线段距离≤0.6英寸
    每对组件2个标签 → 双向两条边(各自带标签); 1个 → 单边.
    """
    import math

    def _seg_dist(px, py, a, b):
        ax, ay, bx, by = a["cx"], a["cy"], b["cx"], b["cy"]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        if l2 < 1e-9:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

    text_nodes = [n for n in nodes if (n.get("text") or "").strip()]
    if len(text_nodes) < 4:
        return nodes, edges
    degree: dict[str, int] = {}
    for e in edges:
        degree[e.get("src", "")] = degree.get(e.get("src", ""), 0) + 1
        degree[e.get("dst", "")] = degree.get(e.get("dst", ""), 0) + 1
    comps = [n for n in text_nodes
             if n.get("h", 0) <= 0.25 or degree.get(n["id"], 0) >= 2]
    labels = [n for n in text_nodes if n not in comps]
    if not labels or len(comps) < 2:
        return nodes, edges

    # hub星型约束: 中心节点(度≥3)存在时只考虑hub-辐条对
    # (3_016教训: 长弦线段"路过"标签附近, 点线距离偏袒长线; 接口图
    # 是星型拓扑, 接口名都挂在中心-外部系统的辐条上)
    hub_id = max(degree, key=degree.get) if degree else None
    if hub_id and degree.get(hub_id, 0) >= 3:
        hub = next(c for c in comps if c["id"] == hub_id)
        pairs = [(hub, c) for c in comps if c["id"] != hub_id]
    else:
        import itertools
        pairs = list(itertools.combinations(comps, 2))

    label_ids = {n["id"] for n in labels}
    # 标签端点的边 = 粘到标签上的连线 → 丢弃, 由几何重关联重建
    edges_clean = [dict(e) for e in edges
                   if e.get("src") not in label_ids
                   and e.get("dst") not in label_ids]
    pair_labels: dict[tuple, list] = {}
    for lb in labels:
        best = None
        for a, b in pairs:
            ax, ay, bx, by = a["cx"], a["cy"], b["cx"], b["cy"]
            seg_len = max(math.hypot(bx - ax, by - ay), 0.5)
            d = _seg_dist(lb["cx"], lb["cy"], a, b)
            score = d * seg_len               # 距离×线长: 惩罚长弦
            if best is None or score < best[0]:
                best = (score, d, a, b)
        if best and best[1] <= 0.6:
            pair_labels.setdefault((best[2]["id"], best[3]["id"]), []).append(lb)

    if not pair_labels:
        return nodes, edges          # 几何不匹配 → 不动(诚实保守)

    comp_map = {c["id"]: c for c in comps}
    new_edges = edges_clean
    for (aid, bid), lbs in pair_labels.items():
        a, b = comp_map[aid], comp_map[bid]
        # 标签按与a端距离排序: 近a者→a出发的边, 第二个→反向边
        lbs_sorted = sorted(lbs, key=lambda x: math.hypot(
            x["cx"] - a["cx"], x["cy"] - a["cy"]))
        fwd = next((e for e in new_edges
                    if e.get("src") == aid and e.get("dst") == bid), None)
        if fwd is None:
            fwd = {"src": aid, "dst": bid, "label": "", "via": "label_attach"}
            new_edges.append(fwd)
        fwd["label"] = lbs_sorted[0]["text"].replace("\n", " ")
        if len(lbs_sorted) >= 2:
            rev = next((e for e in new_edges
                        if e.get("src") == bid and e.get("dst") == aid), None)
            if rev is None:
                rev = {"src": bid, "dst": aid, "label": "",
                       "via": "label_attach"}
                new_edges.append(rev)
            rev["label"] = lbs_sorted[1]["text"].replace("\n", " ")
    nodes_out = [n for n in nodes if n["id"] not in label_ids]
    return nodes_out, new_edges


def refine_untyped(nodes: list[dict]) -> list[dict]:
    """几何启发式类型精化: 仅当全部节点类型缺失(全other)时启用.

    规则(投影层精化, canonical锚点不变):
      大空框(面积≥8×文本中位面积, 框住≥3个文本) = boundary(系统边界)
      框内最上方扁文本 = 边界标题 | 框内其余文本 = usecase | 框外文本 = actor
    依据: 1_012实测 — 服务开发支撑大框(4.6×9.0in)+顶部标题+开发人员/应用
    软件在框外两侧+9个用例文本在框内, 几何结构完全规则.
    """
    text_nodes = [n for n in nodes if (n.get("text") or "").strip()]
    if len(text_nodes) < 4:
        return nodes
    if any(n.get("type") not in ("other", "") for n in nodes):
        return nodes                       # 有类型信息, 不干预
    areas = sorted(n.get("w", 0) * n.get("h", 0) for n in text_nodes)
    med = areas[len(areas) // 2] or 1.0
    candidates = [n for n in nodes
                  if not (n.get("text") or "").strip()
                  and n.get("w", 0) * n.get("h", 0) >= max(8 * med, 4.0)
                  and sum(1 for t in text_nodes
                          if t is not n and _inside(t, n)) >= 3]
    if not candidates:
        return nodes
    b = max(candidates, key=lambda n: n.get("w", 0) * n.get("h", 0))
    inner = [t for t in text_nodes if _inside(t, b)]
    outer = [t for t in text_nodes if not _inside(t, b)]
    if len(inner) < 3:
        return nodes
    flat = [t for t in inner if t.get("h", 0) <= 0.4]
    title = max(flat, key=lambda t: t.get("cy", 0)) if flat else None

    out = []
    bnode = dict(b)
    bnode["type"] = "boundary"
    bnode["text"] = (title or {}).get("text", "")
    out.append(bnode)
    for t in inner:
        if t is title:
            continue
        nt = dict(t)
        nt["type"] = "usecase"
        out.append(nt)
    for t in outer:
        nt = dict(t)
        nt["type"] = "actor"
        out.append(nt)
    return out


def classify_diagram(nodes: list[dict]) -> str:
    """锚点节点类型组成 → 图类型.

    信号分两级(教训来自2_087与25个状态图的拉锯):
      actor/usecase/boundary → 数全部节点(可能无文本, 如2_087)
      proc/state/interface   → 只数有文本节点(无文本装饰件不应翻转类型)
    """
    types_all = Counter(n.get("type", "") for n in nodes)
    types_text = Counter(n.get("type", "") for n in nodes
                         if (n.get("text") or "").strip())
    n_text = max(1, sum(types_text.values()))
    uc = types_all.get("usecase", 0)
    actor = types_all.get("actor", 0)
    boundary = types_all.get("boundary", 0)
    proc = sum(types_text.get(t, 0) for t in _FLOW_TYPES)
    state = types_text.get("state", 0)
    itf = types_text.get("interface", 0) + types_text.get("component", 0)
    if (uc > 0 and actor > 0) or (uc > 0 and uc / n_text >= 0.4):
        return "usecase"
    # 用例类型主导(≥2)且流程类型≤1 → 用例图(1_076教训: 文本other节点
    # 稀释了uc/n_text比值, 但usecase×3+process×1的组成语义明确)
    if uc >= 2 and proc <= 1:
        return "usecase"
    # 参与者+无流程节点/参与者+系统边界/参与者占多数 = 用例图
    # (M11可能把用例椭圆typed成process或无文本; actor信号优先)
    if actor > 0 and (proc == 0 or boundary > 0 or actor > proc):
        return "usecase"
    if state > 0 and proc == 0 and uc == 0:
        return "state"
    if itf > 0 and proc == 0 and uc == 0:
        return "interface"
    if proc > 0:
        return "flowchart"
    return "other"


def sanitize(text: str, maxlen: int = 24) -> str:
    """标签清洗: 去换行/引号/方括号/弯引号.

    弯引号(U+201C/201D等)会让PlantUML状态标签解析器报错
    (02界面集成框架oleObject19实测), 与ASCII引号一并归一为'.
    """
    t = (text or "").replace("\n", " ").replace('"', "'")
    t = t.replace("\u201c", "'").replace("\u201d", "'")   # “ ”
    t = t.replace("\u2018", "'").replace("\u2019", "'")   # ‘ ’
    t = t.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    return t.strip()[:maxlen]


# ═══════════════════════════════════════════════════════════════
# Mermaid渲染
# ═══════════════════════════════════════════════════════════════

# flowchart模式形状(process=矩形, decision=菱形, start/end=体育场)
_FLOW_SHAPE = {"process": ("[", "]"), "decision": ("{", "}"),
               "start": ("([", "])"), "end": ("([", "])"),
               "state": ("[", "]"), "gateway": ("{", "}"), "fork": ("{", "}"),
               "interface": ("[", "]"), "component": ("[", "]"),
               "boundary": ("[", "]"), "other": ("[", "]"),
               "offpage": ("[[", "]]"), "note": ("[", "]")}


def _node_decl_flow(n: dict) -> str:
    left, right = _FLOW_SHAPE.get(n.get("type"), ("[", "]"))
    label = sanitize(n.get("text")) or n.get("type", "节点")
    return f'    N{n["id"]}{left}"{label}"{right}'


def _node_decl_usecase(n: dict) -> str:
    t = n.get("type")
    label = sanitize(n.get("text"))
    if t == "actor":
        return f'    N{n["id"]}["👤 {label}"]'
    if t == "usecase":
        return f'    N{n["id"]}(["{label}"])'
    return f'    N{n["id"]}["{label}"]'


def _inside(n: dict, b: dict) -> bool:
    """节点中心是否在boundary bbox内(英寸坐标)."""
    try:
        return (abs(n["cx"] - b["cx"]) <= b["w"] / 2 + 1e-6
                and abs(n["cy"] - b["cy"]) <= b["h"] / 2 + 1e-6)
    except (KeyError, TypeError):
        return False


def to_mermaid_usecase(s: dict) -> str:
    """用例图UML投影: subgraph=boundary, stadium=用例, 👤=actor, ---=关联."""
    nodes = s.get("nodes", [])
    lines = ["flowchart TD"]
    bounds = [n for n in nodes if n.get("type") == "boundary"
              and (n.get("text") or "").strip()]
    contained: dict[str, dict] = {}
    for b in bounds:
        for n in nodes:
            if n is b or n["id"] in contained:
                continue
            if n.get("type") in ("usecase", "process") and _inside(n, b):
                contained[n["id"]] = b
    b_with_inner = {id(b) for b in bounds
                    if any(v is b for v in contained.values())}

    for n in nodes:
        if not (n.get("text") or "").strip() and n.get("type") == "other":
            continue                      # 无文本装饰件
        if n["id"] in contained:
            continue                      # 在subgraph里声明
        if n.get("type") == "boundary" and (n.get("text") or "").strip():
            if id(n) in b_with_inner:
                continue                  # boundary自身→subgraph标题
            lines.append(f'    N{n["id"]}["{sanitize(n["text"])}"]')  # 空boundary保留
            continue
        lines.append(_node_decl_usecase(n))

    for b in bounds:
        if id(b) not in b_with_inner:
            continue
        lines.append(f'    subgraph SG{b["id"]}["{sanitize(b["text"])}"]')
        for n in nodes:
            if contained.get(n["id"]) is b:
                lines.append("    " + _node_decl_usecase(n).strip())
        lines.append("    end")

    emitted = {n["id"] for n in nodes
               if (n.get("text") or "").strip() or n.get("type") != "other"}
    node_map = {n["id"]: n for n in nodes}
    for e in s.get("edges", []):
        s_id, d_id = e.get("src"), e.get("dst")
        for nid in (s_id, d_id):          # 隐藏端点兜底
            if nid not in emitted and nid in node_map:
                lines.append(_node_decl_usecase(node_map[nid]))
                emitted.add(nid)
        lbl = (e.get("label") or "").strip()
        low = lbl.lower()
        if "include" in low or "包含" in lbl:
            lines.append(f'    N{s_id} -.->|"<<include>>"| N{d_id}')
        elif "extend" in low or "扩展" in lbl:
            lines.append(f'    N{s_id} -.->|"<<extend>>"| N{d_id}')
        elif lbl:
            lines.append(f'    N{s_id} ---|"{sanitize(lbl, 12)}"| N{d_id}')
        else:
            lines.append(f'    N{s_id} --- N{d_id}')
    return "\n".join(lines)


def to_mermaid_flow(s: dict) -> str:
    """流程图/接口/other模式: 标准形状+有向边(流程图本身有向)."""
    lines = ["flowchart TD"]
    nodes = {n["id"]: n for n in s.get("nodes", [])}
    emitted = set()
    for n in s.get("nodes", []):
        if not (n.get("text") or "").strip() and n.get("type") == "other":
            continue
        lines.append(_node_decl_flow(n))
        emitted.add(n["id"])
    for e in s.get("edges", []):
        s_id, d_id = e.get("src"), e.get("dst")
        for nid in (s_id, d_id):
            if nid not in emitted and nid in nodes:
                lines.append(_node_decl_flow(nodes[nid]))
                emitted.add(nid)
        lbl = sanitize(e.get("label") or "", 12)
        if lbl:
            lines.append(f'    N{s_id} -->|"{lbl}"| N{d_id}')
        else:
            lines.append(f'    N{s_id} --> N{d_id}')
    return "\n".join(lines)


def to_mermaid_state(s: dict) -> str:
    """状态图 → stateDiagram-v2 (start/end映射[*])."""
    lines = ["stateDiagram-v2"]
    start_id = end_id = None
    emitted = set()
    for n in s.get("nodes", []):
        t = n.get("type")
        if t == "start":
            start_id = n["id"]
            continue
        if t == "end":
            end_id = n["id"]
            continue
        if not (n.get("text") or "").strip() and t == "other":
            continue
        lines.append(f'    S{n["id"]} : {sanitize(n.get("text")) or t}')
        emitted.add(n["id"])

    def _name(nid: str) -> str | None:
        if nid == start_id:
            return "[*]"
        if nid == end_id:
            return "[*]"
        if nid in emitted:
            return f"S{nid}"
        return None

    for e in s.get("edges", []):
        s_name, d_name = _name(e.get("src")), _name(e.get("dst"))
        if s_name is None or d_name is None:
            continue
        lbl = sanitize(e.get("label") or "", 12)
        lines.append(f"    {s_name} --> {d_name}" + (f" : {lbl}" if lbl else ""))
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# PlantUML渲染(usecase的主投影: UML母语, 语义完整)
# ═══════════════════════════════════════════════════════════════

def _puml_alias(nid) -> str:
    return f"P{nid}"


def _puml_header() -> list[str]:
    """PlantUML公共头: smetana纯Java布局(免graphviz依赖, 本地渲染闭环)."""
    return ["@startuml", "!pragma layout smetana"]


def to_plantuml_usecase(s: dict) -> str:
    """用例图 → PlantUML(语义母语): actor小人/rectangle系统边界/--关联/..>include.

    mermaid的subgraph无法表达"系统整体"语义(1_007用户反馈); PlantUML的
    rectangle{}是UML标准系统边界. 布局: left-to-right(用例图惯例).
    """
    nodes = s.get("nodes", [])
    lines = _puml_header() + ["left to right direction"]
    bounds = [n for n in nodes if n.get("type") == "boundary"
              and (n.get("text") or "").strip()]
    contained: dict[str, dict] = {}
    for b in bounds:
        for n in nodes:
            if n is b or n["id"] in contained:
                continue
            if n.get("type") in ("usecase", "process") and _inside(n, b):
                contained[n["id"]] = b
    b_with_inner = {id(b) for b in bounds
                    if any(v is b for v in contained.values())}
    # 包含边抑制: boundary↔其内部节点的连线=包含关系而非关联(3_010教训:
    # 接口图里大框→组件的6条glue线被渲染成"流转"完全错误)
    inner_of: dict[str, set] = {}
    for b in bounds:
        inner_of[b["id"]] = {n["id"] for n in nodes
                             if contained.get(n["id"]) is b}

    def _decl(n: dict) -> str:
        label = sanitize(n.get("text")) or n.get("type", "节点")
        if n.get("type") == "actor":
            return f'actor "{label}" as {_puml_alias(n["id"])}'
        if n.get("type") == "usecase":
            return f'usecase "{label}" as {_puml_alias(n["id"])}'
        return f'rectangle "{label}" as {_puml_alias(n["id"])}'

    for n in nodes:
        if not (n.get("text") or "").strip() and n.get("type") == "other":
            continue
        if n["id"] in contained:
            continue
        if n.get("type") == "boundary" and (n.get("text") or "").strip():
            if id(n) in b_with_inner:
                continue
            lines.append(_decl(n))       # 空boundary保留为rectangle
            continue
        lines.append(_decl(n))

    for b in bounds:
        if id(b) not in b_with_inner:
            continue
        lines.append(f'rectangle "{sanitize(b["text"])}" {{')
        for n in nodes:
            if contained.get(n["id"]) is b:
                label = sanitize(n.get("text")) or n.get("type", "节点")
                lines.append(f'  usecase "{label}" as {_puml_alias(n["id"])}')
        lines.append("}")

    emitted = {n["id"] for n in nodes
               if (n.get("text") or "").strip() or n.get("type") != "other"}
    node_map = {n["id"]: n for n in nodes}
    for e in s.get("edges", []):
        s_id, d_id = e.get("src"), e.get("dst")
        for nid in (s_id, d_id):
            if nid not in emitted and nid in node_map:
                lines.append(_decl(node_map[nid]))
                emitted.add(nid)
        lbl = (e.get("label") or "").strip()
        low = lbl.lower()
        if "include" in low or "包含" in lbl:
            lines.append(f"{_puml_alias(s_id)} ..> {_puml_alias(d_id)} : <<include>>")
        elif "extend" in low or "扩展" in lbl:
            lines.append(f"{_puml_alias(s_id)} ..> {_puml_alias(d_id)} : <<extend>>")
        else:
            lines.append(f"{_puml_alias(s_id)} -- {_puml_alias(d_id)}")
    lines.append("@enduml")
    return "\n".join(lines)


def to_plantuml_state(s: dict) -> str:
    """状态图 → PlantUML state(母语): [*]起止/状态/迁移标签."""
    lines = _puml_header()
    start_id = end_id = None
    emitted = set()
    for n in s.get("nodes", []):
        t = n.get("type")
        if t == "start":
            start_id = n["id"]
            continue
        if t == "end":
            end_id = n["id"]
            continue
        if not (n.get("text") or "").strip() and t == "other":
            continue
        label = sanitize(n.get("text")) or t or "状态"
        lines.append(f'state "{label}" as S{n["id"]}')
        emitted.add(n["id"])

    def _name(nid):
        if nid == start_id or nid == end_id:
            return "[*]"
        return f"S{nid}" if nid in emitted else None

    for e in s.get("edges", []):
        s_name, d_name = _name(e.get("src")), _name(e.get("dst"))
        if s_name is None or d_name is None:
            continue
        lbl = sanitize(e.get("label") or "", 12)
        lines.append(f"{s_name} --> {d_name}" + (f" : {lbl}" if lbl else ""))
    lines.append("@enduml")
    return "\n".join(lines)


def to_plantuml_flow(s: dict) -> str:
    """流程图/接口/other → PlantUML state语法投影(任意有向图通用).

    PlantUML无通用有向图模式; state语法的S{n}-->S{m}可表达任意结构
    (含环/断链), 判定节点用<<choice>>立体类型标注语义(菱形视觉的
    语义等价物), 无文本start/end映射[*].
    """
    lines = _puml_header()
    nodes = s.get("nodes", [])
    start_ids = {n["id"] for n in nodes if n.get("type") == "start"}
    end_ids = {n["id"] for n in nodes if n.get("type") == "end"}
    emitted = set()
    for n in nodes:
        if n["id"] in start_ids or n["id"] in end_ids:
            continue
        if not (n.get("text") or "").strip() and n.get("type") == "other":
            continue
        label = sanitize(n.get("text")) or n.get("type") or "节点"
        if n.get("type") == "decision":
            lines.append(f'state "{label}" as S{n["id"]} <<choice>>')
        else:
            lines.append(f'state "{label}" as S{n["id"]}')
        emitted.add(n["id"])

    def _name(nid):
        if nid in start_ids:
            return "[*]"
        if nid in end_ids:
            return "[*]"
        return f"S{nid}" if nid in emitted else None

    node_map = {n["id"]: n for n in nodes}
    for e in s.get("edges", []):
        s_id, d_id = e.get("src"), e.get("dst")
        for nid in (s_id, d_id):          # 隐藏端点兜底
            if _name(nid) is None and nid in node_map:
                n = node_map[nid]
                if n["id"] in start_ids or n["id"] in end_ids:
                    continue
                label = sanitize(n.get("text")) or n.get("type") or "节点"
                lines.append(f'state "{label}" as S{nid}')
                emitted.add(nid)
        s_name, d_name = _name(s_id), _name(d_id)
        if s_name is None or d_name is None:
            continue
        lbl = sanitize(e.get("label") or "", 12)
        lines.append(f"{s_name} --> {d_name}" + (f" : {lbl}" if lbl else ""))
    lines.append("@enduml")
    return "\n".join(lines)


def to_plantuml(s: dict, dtype: str) -> str:
    """全部图类型 → PlantUML(用户决策: 全量统一PlantUML, 2026-09-09)."""
    if dtype == "usecase":
        return to_plantuml_usecase(s)
    if dtype == "state":
        return to_plantuml_state(s)
    return to_plantuml_flow(s)


def to_mermaid(s: dict, dtype: str) -> str:
    if dtype == "usecase":
        return to_mermaid_usecase(s)
    if dtype == "state":
        return to_mermaid_state(s)
    return to_mermaid_flow(s)      # flowchart / interface / other


# ═══════════════════════════════════════════════════════════════
# DOT渲染(完整语义出口)
# ═══════════════════════════════════════════════════════════════

_DOT_SHAPE = {"usecase": "ellipse", "actor": "plaintext", "process": "box",
              "decision": "diamond", "start": "circle", "end": "doublecircle",
              "state": "ellipse", "interface": "box", "component": "box",
              "boundary": "box", "other": "box"}


def to_dot(s: dict, dtype: str) -> str:
    lines = ["digraph G {", '  rankdir=TB;',
             '  node [fontname="Microsoft YaHei"];']
    nodes = s.get("nodes", [])
    bounds = [n for n in nodes if n.get("type") == "boundary"
              and (n.get("text") or "").strip()] if dtype == "usecase" else []
    contained: dict[str, dict] = {}
    if bounds:
        for b in bounds:
            for n in nodes:
                if n is b or n["id"] in contained:
                    continue
                if n.get("type") in ("usecase", "process") and _inside(n, b):
                    contained[n["id"]] = b
        b_with_inner = {id(b) for b in bounds
                        if any(v is b for v in contained.values())}
    else:
        b_with_inner = set()

    for n in nodes:
        if not (n.get("text") or "").strip() and n.get("type") == "other":
            continue
        if n["id"] in contained:
            continue
        if id(n) in b_with_inner:
            continue
        shape = _DOT_SHAPE.get(n.get("type"), "box")
        label = sanitize(n.get("text")) or n.get("type", "")
        if n.get("type") == "actor":
            label = f"👤 {label}"
        lines.append(f'  N{n["id"]} [shape={shape}, label="{label}"];')
    for b in bounds:
        if id(b) not in b_with_inner:
            continue
        lines.append(f'  subgraph cluster_{b["id"]} {{')
        lines.append(f'    label="{sanitize(b["text"])}";')
        for n in nodes:
            if contained.get(n["id"]) is b:
                label = sanitize(n.get("text")) or n.get("type", "")
                lines.append(f'    N{n["id"]} [shape=ellipse, label="{label}"];')
        lines.append("  }")
    node_map = {n["id"]: n for n in nodes}
    emitted = {n["id"] for n in nodes
               if (n.get("text") or "").strip() or n.get("type") != "other"}
    for e in s.get("edges", []):
        s_id, d_id = e.get("src"), e.get("dst")
        for nid in (s_id, d_id):
            if nid not in emitted and nid in node_map:
                n = node_map[nid]
                lines.append(f'  N{nid} [shape=box, '
                             f'label="{sanitize(n.get("text")) or n.get("type")}"];')
                emitted.add(nid)
        lbl = (e.get("label") or "").strip()
        low = lbl.lower()
        if dtype == "usecase":
            if "include" in low or "包含" in lbl:
                lines.append(f'  N{s_id} -> N{d_id} [style=dashed, '
                             f'label="<<include>>"];')
            elif "extend" in low or "扩展" in lbl:
                lines.append(f'  N{s_id} -> N{d_id} [style=dashed, '
                             f'label="<<extend>>"];')
            else:
                name = f', label="{sanitize(lbl, 12)}"' if lbl else ""
                lines.append(f'  N{s_id} -> N{d_id} [dir=none{name}];')
        else:
            name = f', label="{sanitize(lbl, 12)}"' if lbl else ""
            lines.append(f'  N{s_id} -> N{d_id}{name};')
    lines.append("}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def suppress_containment_edges(nodes: list[dict],
                               edges: list[dict]) -> list[dict]:
    """boundary↔其几何内部节点的连线 = 包含关系, 渲染成关联/流转是语义错误.

    3_010教训: 接口图的大框→6个组件的glue线被渲染成S1-->S54"流转",
    实际是组件在系统框内的包含关系. UML用例图中关联从不指向系统边界.
    """
    bounds = [n for n in nodes if n.get("type") == "boundary"]
    if not bounds:
        return edges
    inner_of: dict[str, set] = {}
    for b in bounds:
        inner_of[b["id"]] = {n["id"] for n in nodes
                             if n is not b and _inside(n, b)}
    out = []
    for e in edges:
        sid, did = e.get("src"), e.get("dst")
        dropped = False
        for b in bounds:
            bid = b["id"]
            inner = inner_of.get(bid, set())
            if (sid == bid and did in inner) or (did == bid and sid in inner):
                dropped = True
                break
        if not dropped:
            out.append(e)
    return out


def export_all() -> dict:
    """全量导出: anchors_v2 → {key: entry}(mermaid+plantuml+dot).

    类型全缺失的图先做几何精化(标注type_refined);
    悬空端点恢复边(recover_dangling_edges产出)并入投影(标注via=dangling_snap,
    canonical锚点不变, 每条带距离证据).
    """
    anchors = json.loads(ANCHOR_V2.read_text(encoding="utf-8"))
    recovered: dict[str, list] = {}
    if RECOVERED_PATH.exists():
        recovered = json.loads(RECOVERED_PATH.read_text(encoding="utf-8"))
    export = {}
    for doc, d in anchors.items():
        for s in d.get("structures", []):
            refined = promote_containers(refine_untyped(s.get("nodes", [])))
            dtype = classify_diagram(refined)
            key = f"{doc[:8]}:{s['embed_index']}"
            rec_edges = recovered.get(key, [])
            base_edges = suppress_containment_edges(
                refined, s.get("edges", []))
            n_suppressed = len(s.get("edges", [])) - len(base_edges)
            if dtype in ("interface", "other"):
                refined, base_edges = attach_edge_labels(refined, base_edges)
                dtype = classify_diagram(refined)   # 关联后重判类
            s2 = dict(s)
            s2["nodes"] = refined
            if rec_edges or n_suppressed:
                s2 = dict(s2)
                s2["edges"] = base_edges + rec_edges
            else:
                s2["edges"] = base_edges
            export[key] = {
                "doc": doc,
                "embed": s["embed_index"],
                "diagram_type": dtype,
                "n_nodes": len([n for n in s.get("nodes", []) if n.get("text")]),
                "n_edges": len(base_edges) + len(rec_edges),
                "n_suppressed": n_suppressed,
                "mermaid": to_mermaid(s2, dtype),
                "plantuml": to_plantuml(s2, dtype),
                "dot": to_dot(s2, dtype),
                "dangling_ends": (s.get("meta") or {}).get("dangling_ends", 0),
                "n_recovered": len(rec_edges),
                "type_refined": refined is not s.get("nodes"),
            }
    return export


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="统一视图导出(Mermaid+DOT)")
    ap.add_argument("--dry", action="store_true", help="只统计不写文件")
    args = ap.parse_args()

    export = export_all()
    if not args.dry:
        OUT_PATH.write_text(json.dumps(export, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    from collections import Counter
    dist = Counter(v["diagram_type"] for v in export.values())
    total = sum(dist.values())
    print(f"统一导出: {total}图 → {OUT_PATH}")
    for t, n in dist.most_common():
        print(f"  {t}: {n} ({n / total:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
