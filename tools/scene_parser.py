#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""场景专用 Visio 解析器 — 把 M11 通用结构层升级为场景语义层
================================================================

M11(anchors_v2)产出通用结构: nodes[{id,type,cx,cy,w,h,bbox,text}] + edges。
本模块按图型分派专用解析器, 输出场景语义模型(供context_graph/ACDD/检测器消费):

  usecase_diagram   → 用例模型: 系统边界/用例/主参与者/外部系统/关联/include-extend
  flowchart         → 流程模型: 流向/有序步骤/主路径/判断分支/异常流分支
  interface_diagram → 接口模型: 系统/接口点/连接(系统A-接口-系统B)
  function_diagram  → 层级模型: 根节点/层级树(功能图+功能框架图)
  state(并入flowchart), other → 基础模型(节点+边)

场景语义规则(全部来自真实数据样例验证):
  - 用例图: type=actor/usecase/boundary已有; 隐性边界=包含≥2用例的大矩形(几何包含);
            边界左侧actor=主参与者, 右侧=外部系统; uc-uc边=include/extend/泛化
  - 流程图: start→end向量定流向; 拓扑序+坐标序=步骤序; 决策分支带label;
            离开主路径且不回汇的分支=异常流候选(E\d/异常标签优先)
  - 接口图: 零尺寸节点=连接线/系统引用点(非语义节点); 圆形(w≈h)=系统;
            小矩形含"接口"文本=接口点; 接口点吸附到最近的系统对
  - 功能图: 最大bbox或出度最大者为根; 边+几何包含构成层级

输出: data/gjb_438c/anchor_v2/scene_models.json
用法: python tools/scene_parser.py [--doc 01] [--validate]
"""
import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict, deque

sys.stdout.reconfigure(encoding="utf-8")
BASE = __file__.rsplit("\\", 2)[0] if "\\" in __file__ else __file__.rsplit("/", 2)[0]
ANCHOR_PATH = BASE + "/data/gjb_438c/anchor_v2/anchors_v2.json"
OUT_PATH = BASE + "/data/gjb_438c/anchor_v2/scene_models.json"

EXC_RE = re.compile(r"异常|E\d+|失败|错误|超时|exception", re.IGNORECASE)


def area(n):
    return n["w"] * n["h"]


def bbox_contains(a, b, pad=0.0):
    """a的bbox是否包含b(带容差)"""
    return (a["bbox"][0] - pad <= b["bbox"][0] and a["bbox"][1] - pad <= b["bbox"][1]
            and a["bbox"][2] + pad >= b["bbox"][2] and a["bbox"][3] + pad >= b["bbox"][3])


def center_dist(a, b):
    return math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"])


# ═══════════════════════════════════════════════════════════════
# 图型分类器
# ═══════════════════════════════════════════════════════════════

def classify(s, fig_type_hint=None):
    """结构 → 图型。自含式节点组成判定 + figure_index类型提示(若有)。"""
    nodes = s["nodes"]
    n = len(nodes)
    if n == 0:
        return "empty", 0.0, "无节点"
    tc = Counter(nd["type"] for nd in nodes)
    texts = [nd["text"] for nd in nodes if nd["text"]]

    # 接口图: 接口文本 + 零尺寸节点密集
    iface_texts = sum(1 for t in texts if "接口" in t)
    zero_dim = sum(1 for nd in nodes if nd["w"] < 0.05 or nd["h"] < 0.05)
    if iface_texts >= 2:
        return "interface_diagram", 0.85, f"接口文本×{iface_texts}"
    if zero_dim >= max(3, n * 0.4) and iface_texts >= 1:
        return "interface_diagram", 0.7, f"零尺寸节点×{zero_dim}+接口文本"

    # 用例图
    uc, actor, bnd = tc.get("usecase", 0), tc.get("actor", 0), tc.get("boundary", 0)
    if uc >= 2 and (actor >= 1 or bnd >= 1):
        return "usecase_diagram", 0.95, f"usecase×{uc}+actor×{actor}+boundary×{bnd}"
    if uc >= 3:
        return "usecase_diagram", 0.8, f"usecase×{uc}"

    # 流程图/活动图/状态图
    ctrl = tc.get("start", 0) + tc.get("end", 0) + tc.get("decision", 0) + tc.get("fork", 0)
    body = tc.get("process", 0) + tc.get("state", 0)
    if ctrl >= 1 and body >= 1:
        return "flowchart", 0.9, f"控制节点×{ctrl}+过程×{body}"
    if tc.get("state", 0) >= max(2, n * 0.6):
        return "flowchart", 0.8, f"状态节点占比{tc['state']}/{n}"

    # 接口hint优先: 图所在章节的figure类型为interface时, 非强类型结构归接口
    # (sc3第二画法: 系统关系图 — actor/process画系统+网状边, 无usecase语义)
    if fig_type_hint == "interface_diagram":
        return "interface_diagram", 0.75, "接口章节hint(系统关系图画法)"

    # 功能图/框架图: 全process/other + 少边 或 层级形态
    if fig_type_hint in ("function_diagram", "function_framework"):
        return fig_type_hint, 0.9, "figure_index类型提示"

    # 泛化: 有文本节点较多但无边 → 框图(功能/框架)
    n_edges = len(s["edges"])
    if n == 1:
        return "other", 0.5, "单节点"
    if n_edges <= n:  # 边稀疏 → 层级/框架形态
        return "function_diagram", 0.6, f"边稀疏({n_edges}/{n})推断层级"
    return "other", 0.4, "未识别组合"


# ═══════════════════════════════════════════════════════════════
# 用例图解析器
# ═══════════════════════════════════════════════════════════════

def parse_usecase(s):
    nodes = s["nodes"]
    by_id = {nd["id"]: nd for nd in nodes}
    node_set = set(by_id)

    # 1. 显性边界 + 隐性边界(大矩形包含≥2用例)
    boundaries = [nd for nd in nodes if nd["type"] == "boundary" and nd["text"]]
    usecases = [nd for nd in nodes if nd["type"] == "usecase"]
    if not boundaries:
        big = [nd for nd in nodes
               if nd["type"] in ("process", "other") and nd["text"]
               and nd["w"] > 0.6 and nd["h"] > 1.0]
        for cand in sorted(big, key=lambda x: -area(x)):
            inside = [uc for uc in usecases if bbox_contains(cand, uc, 0.05)]
            if len(inside) >= 2:
                boundaries.append(cand)
                break

    # 2. 用例归属边界
    uc_models = []
    for uc in usecases:
        owner = next((b for b in boundaries if bbox_contains(b, uc, 0.05)), None)
        uc_models.append({
            "id": uc["id"], "name": uc["text"],
            "boundary": owner["text"] if owner else None,
        })

    # 3. 参与者: 边界左侧=主参与者, 右侧=外部系统(无边界时全算主参与者)
    actors = [nd for nd in nodes if nd["type"] == "actor" and nd["text"]]
    primary, external = [], []
    if boundaries:
        b = min(boundaries, key=lambda x: x["bbox"][0])  # 取最左边界作参照
        for a in actors:
            (primary if a["cx"] < b["bbox"][0] else external).append(a["text"])
    else:
        primary = [a["text"] for a in actors]

    # 4. 关联边(actor↔usecase)与uc-uc关系
    assoc, uc_rel = [], []
    for e in s["edges"]:
        if e["src"] not in node_set or e["dst"] not in node_set:
            continue
        sn, dn = by_id[e["src"]], by_id[e["dst"]]
        pair = {sn["type"], dn["type"]}
        if pair == {"actor", "usecase"}:
            a, u = (sn, dn) if sn["type"] == "actor" else (dn, sn)
            assoc.append({"actor": a["text"], "usecase": u["text"],
                          "dir": "actor_to_uc" if sn["type"] == "actor" else "uc_to_actor"})
        elif pair == {"usecase", "usecase"}:
            lab = (e.get("label") or "").strip()
            kind = ("include" if "include" in lab.lower() else
                    "extend" if "extend" in lab.lower() else "unknown")
            uc_rel.append({"src": sn["text"], "dst": dn["text"], "kind": kind})

    return {
        "diagram_type": "usecase_diagram",
        "boundaries": [b["text"] for b in boundaries],
        "usecases": uc_models,
        "primary_actors": primary,
        "external_systems": external,
        "associations": assoc,
        "uc_relations": uc_rel,
        "stats": {"n_usecases": len(uc_models), "n_actors": len(primary),
                  "n_external": len(external), "n_assoc": len(assoc)},
    }


# ═══════════════════════════════════════════════════════════════
# 流程图解析器
# ═══════════════════════════════════════════════════════════════

def parse_flowchart(s):
    nodes = s["nodes"]
    by_id = {nd["id"]: nd for nd in nodes}
    adj = defaultdict(list)
    for e in s["edges"]:
        if e["src"] in by_id and e["dst"] in by_id:
            adj[e["src"]].append((e["dst"], e))
            adj[e["dst"]].append((e["src"], e))  # 双向邻接(方向另行判定)

    starts = [nd for nd in nodes if nd["type"] == "start"]
    ends = [nd for nd in nodes if nd["type"] == "end"]
    steps_raw = [nd for nd in nodes if nd["type"] in ("process", "state", "decision", "gateway")]

    # 1. 流向: start→end 主向量
    direction = "unknown"
    if starts and ends:
        sx = sum(n["cx"] for n in starts) / len(starts)
        sy = sum(n["cy"] for n in ends) / len(ends)
        ey = sum(n["cy"] for n in ends) / len(ends)
        dx, dy = sum(n["cx"] for n in ends) / len(ends) - sx, ey - sy
        direction = ("top-down" if abs(dy) > abs(dx) and dy < 0 else
                     "bottom-up" if abs(dy) > abs(dx) else
                     "left-right" if dx > 0 else "right-left")

    # 2. 步骤序: start起BFS拓扑序, 坐标序为tiebreak
    def coord_key(nd):
        return {"top-down": (nd["cy"], nd["cx"]), "bottom-up": (-nd["cy"], nd["cx"]),
                "left-right": (nd["cx"], nd["cy"]),
                "right-left": (-nd["cx"], nd["cy"])}.get(direction, (nd["cy"], nd["cx"]))

    order = {}
    if starts:
        seen = {starts[0]["id"]}
        dq = deque([starts[0]["id"]])
        while dq:
            cur = dq.popleft()
            for nb, _ in adj[cur]:
                if nb not in seen and nb in by_id \
                        and by_id[nb]["type"] != "start":
                    seen.add(nb)
                    dq.append(nb)
        reach = [nd for nd in steps_raw if nd["id"] in seen]
        rest = [nd for nd in steps_raw if nd["id"] not in seen]
        # 可达步骤坐标序在前, 不可达(sidebar/断链)追加在后 — 保证order全覆盖
        ordered = sorted(reach, key=coord_key) + sorted(rest, key=coord_key)
        for i, nd in enumerate(ordered, 1):
            order[nd["id"]] = i
    else:
        for i, nd in enumerate(sorted(steps_raw, key=coord_key), 1):
            order[nd["id"]] = i

    steps = [{"order": order[nd["id"]], "id": nd["id"], "name": nd["text"],
              "node_type": nd["type"]} for nd in steps_raw]
    steps.sort(key=lambda x: x["order"])

    # 3. 主路径: start→end BFS最短路(按语义节点)
    main_path = []
    if starts and ends:
        start_id, end_id = starts[0]["id"], ends[0]["id"]
        prev = {start_id: None}
        dq = deque([start_id])
        while dq:
            cur = dq.popleft()
            if cur == end_id:
                break
            for nb, _ in adj[cur]:
                if nb not in prev:
                    prev[nb] = cur
                    dq.append(nb)
        if end_id in prev:
            cur = end_id
            while cur is not None:
                main_path.append(cur)
                cur = prev[cur]
            main_path.reverse()

    # 4. 判断分支与异常流
    main_set = set(main_path)
    decisions, exc_flows = [], []
    for nd in nodes:
        if nd["type"] not in ("decision", "gateway"):
            continue
        branches = []
        for e in s["edges"]:
            if e["src"] == nd["id"] and e["dst"] in by_id:
                branches.append({"label": (e.get("label") or "").strip(),
                                 "target": by_id[e["dst"]]["text"] or e["dst"]})
            elif e["dst"] == nd["id"] and e["src"] in by_id:
                branches.append({"label": (e.get("label") or "").strip(),
                                 "target": by_id[e["src"]]["text"] or e["src"],
                                 "reverse": True})
        decisions.append({"id": nd["id"], "name": nd["text"], "branches": branches})
    # 异常流: 步骤节点发出的、标签含异常特征、或指向主路径外节点的边
    step_ids = {nd["id"] for nd in steps_raw}
    for e in s["edges"]:
        if e["src"] not in by_id or e["dst"] not in by_id:
            continue
        sn, dn = by_id[e["src"]], by_id[e["dst"]]
        if sn["id"] not in step_ids or dn["id"] == sn["id"]:
            continue
        lab = (e.get("label") or "").strip()
        off_main = dn["id"] not in main_set and bool(main_set)
        if EXC_RE.search(lab) or (off_main and EXC_RE.search(dn["text"] or "")):
            exc_flows.append({"from_step": sn["text"], "to": dn["text"],
                              "label": lab, "evidence": "label" if lab else "off_main_target"})

    return {
        "diagram_type": "flowchart",
        "direction": direction,
        "steps": steps,
        "main_path": [by_id[i]["text"] or i for i in main_path],
        "decisions": decisions,
        "exception_flows": exc_flows,
        "stats": {"n_steps": len(steps), "n_decisions": len(decisions),
                  "n_exc": len(exc_flows), "path_len": len(main_path)},
    }


# ═══════════════════════════════════════════════════════════════
# 接口图解析器
# ═══════════════════════════════════════════════════════════════

def parse_interface(s):
    nodes = s["nodes"]
    by_id = {nd["id"]: nd for nd in nodes}

    # 1. 节点四分类(接口图中actor=外部系统, state/usecase也可能画系统)
    systems, ifaces, lines = [], [], []
    for nd in nodes:
        named = bool(nd["text"])
        tiny = nd["w"] < 0.05 or nd["h"] < 0.05
        small = nd["w"] < 0.7 and nd["h"] < 0.35
        circle = abs(nd["w"] - nd["h"]) < 0.15 * max(nd["w"], nd["h"]) and nd["w"] > 0.3
        if tiny:
            lines.append(nd)  # 连接线/锚点(零尺寸)
        elif named and ("接口" in nd["text"] or (small and nd["h"] < 0.3)):
            ifaces.append(nd)  # 接口点标签
        elif named and nd["type"] in ("actor", "usecase", "boundary", "state"):
            systems.append(nd)  # 系统关系图画法: actor/用例形画系统
        elif named and (nd["w"] * nd["h"] > 0.15 or circle):
            systems.append(nd)  # 系统/组件
        elif named:
            systems.append(nd)
    # 无文本零尺寸节点里的命名系统引用(如"数据中台" w=0) → 系统
    for nd in lines:
        if nd["text"]:
            systems.append(nd)
    lines = [nd for nd in lines if not nd["text"]]

    # 2. 连通性: 压缩line节点(系统-line-系统 = 系统-系统)
    sys_ids = {nd["id"] for nd in systems}
    adj = defaultdict(set)
    for e in s["edges"]:
        if e["src"] in by_id and e["dst"] in by_id:
            adj[e["src"]].add(e["dst"])
            adj[e["dst"]].add(e["src"])

    def resolve_system(nid, depth=0):
        """沿line节点传导找系统端点"""
        if nid in sys_ids:
            return nid
        if depth > 3:
            return None
        for nb in adj[nid]:
            r = resolve_system(nb, depth + 1)
            if r:
                return r
        return None

    conn_pairs = set()
    for nd in systems:
        for nb in adj[nd["id"]]:
            if nb in sys_ids:
                conn_pairs.add(tuple(sorted((nd["id"], nb))))
            else:  # 邻居是line节点 → 传导
                r = resolve_system(nb)
                if r and r != nd["id"]:
                    conn_pairs.add(tuple(sorted((nd["id"], r))))

    # 3. 接口点吸附: 每个接口点找最近的连接线段中点或两个最近系统
    def iface_attach(if_nd):
        near_sys = sorted(systems, key=lambda x: center_dist(x, if_nd))
        if len(near_sys) >= 2:
            return near_sys[0]["text"], near_sys[1]["text"]
        return (near_sys[0]["text"], None) if near_sys else (None, None)

    iface_models = []
    for ifn in ifaces:
        a, b = iface_attach(ifn)
        iface_models.append({"name": ifn["text"], "connects": [a, b]})

    connections = []
    for a_id, b_id in conn_pairs:
        a, b = by_id[a_id], by_id[b_id]
        # 找吸附在这对系统之间的接口点(到两系统距离都最小的)
        best_if = None
        best_d = 1e9
        for ifn in ifaces:
            d = center_dist(ifn, a) + center_dist(ifn, b)
            if d < best_d:
                best_d, best_if = d, ifn
        connections.append({"system_a": a["text"], "system_b": b["text"],
                            "interface": best_if["text"] if best_if else None})

    return {
        "diagram_type": "interface_diagram",
        "systems": [nd["text"] for nd in systems if nd["text"]],
        "interfaces": iface_models,
        "connections": connections,
        "stats": {"n_systems": len([x for x in systems if x["text"]]),
                  "n_interfaces": len(iface_models), "n_connections": len(connections)},
    }


# ═══════════════════════════════════════════════════════════════
# 功能图/框架图解析器
# ═══════════════════════════════════════════════════════════════

def parse_function(s):
    nodes = [nd for nd in s["nodes"] if nd["text"]]
    by_id = {nd["id"]: nd for nd in nodes}
    # 出边数(M11边方向: parent→child)
    out_deg = Counter()
    adj = defaultdict(list)
    for e in s["edges"]:
        if e["src"] in by_id and e["dst"] in by_id:
            out_deg[e["src"]] += 1
            adj[e["src"]].append(e["dst"])

    # 根: 出度最大, 平局取bbox最大
    if not nodes:
        return {"diagram_type": "function_diagram", "root": None, "levels": [],
                "stats": {"n_nodes": 0}}
    root = max(nodes, key=lambda nd: (out_deg[nd["id"]], area(nd)))

    # 层级: BFS + 几何包含(未被边覆盖的包含关系)
    levels, seen = [], {root["id"]}
    frontier = [root["id"]]
    while frontier:
        levels.append([by_id[i]["text"] for i in frontier if i in by_id])
        nxt = []
        for fid in frontier:
            for nb in adj[fid]:
                if nb not in seen:
                    seen.add(nb)
                    nxt.append(nb)
        # 包含补充: 前层节点包含的未分配节点
        for fid in list(frontier):
            f = by_id.get(fid)
            if f:
                for nd in nodes:
                    if nd["id"] not in seen and bbox_contains(f, nd, 0.05):
                        seen.add(nd["id"])
                        nxt.append(nd["id"])
        frontier = nxt

    orphan = [nd["text"] for nd in nodes if nd["id"] not in seen]
    return {
        "diagram_type": "function_diagram",
        "root": root["text"],
        "levels": levels,
        "orphans": orphan,
        "stats": {"n_nodes": len(nodes), "depth": len(levels)},
    }


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

PARSERS = {
    "usecase_diagram": parse_usecase,
    "flowchart": parse_flowchart,
    "interface_diagram": parse_interface,
    "function_diagram": parse_function,
    "function_framework": parse_function,
}


def parse_structure(s, fig_type_hint=None):
    dtype, conf, why = classify(s, fig_type_hint)
    model = {"diagram_type": dtype}
    if dtype in PARSERS:
        try:
            model = PARSERS[dtype](s)
        except Exception as ex:  # noqa: BLE001
            model = {"diagram_type": dtype, "error": str(ex)}
    model["_classify"] = {"type": dtype, "confidence": conf, "why": why}
    return model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=None)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    av = json.load(open(ANCHOR_PATH, encoding="utf-8"))
    # figure_index类型提示(section匹配: 结构序→visio_section_mapping→section→该节figure类型)
    s0 = json.load(open(BASE + "/data/gjb_438c/data_assets/stage0_assets.json", encoding="utf-8"))
    vmap = json.load(open(BASE + "/data/gjb_438c/data_assets/graph/visio_section_mapping.json",
                          encoding="utf-8"))
    sec_figtype = {}
    for doc, figs in s0["figure_index"].items():
        m = defaultdict(list)
        for f in figs:
            m[f.get("section", "")].append(f.get("type"))
        sec_figtype[doc] = m

    docs = {k: v for k, v in av.items() if not args.doc or k.startswith(args.doc)}
    out = {}
    type_dist = Counter()
    for doc, v in sorted(docs.items()):
        entries = []
        for i, st in enumerate(v["structures"]):
            hint = None
            vm = vmap.get(doc, [])
            if i < len(vm):
                hint = (sec_figtype.get(doc, {}).get(vm[i].get("matched_section", ""), [""])[0]
                        if vm[i].get("matched_section") else None)
            model = parse_structure(st, hint)
            entries.append(model)
            type_dist[model["_classify"]["type"]] += 1
        out[doc] = {"visio_count": v.get("visio_count", len(entries)), "models": entries}
        dt = Counter(m["_classify"]["type"] for m in entries)
        print(f"[{doc[:16]:18s}] {len(entries):3d}结构: " +
              " ".join(f"{k}:{n}" for k, n in dt.most_common()))

    json.dump(out, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("=" * 60)
    print(f"输出: {OUT_PATH}")
    print(f"图型分布: {dict(type_dist.most_common())}")

    # 语义质量统计
    n_uc = sum(1 for d in out.values() for m in d["models"]
               if m.get("stats", {}).get("n_usecases", 0) > 0)
    n_flow = sum(1 for d in out.values() for m in d["models"]
                 if m.get("stats", {}).get("n_steps", 0) > 0)
    n_if = sum(1 for d in out.values() for m in d["models"]
               if m.get("stats", {}).get("n_connections", 0) > 0)
    n_fn = sum(1 for d in out.values() for m in d["models"]
               if m.get("stats", {}).get("depth", 0) >= 2)
    print(f"有效语义模型: 用例图{n_uc} 流程图{n_flow} 接口图{n_if} 功能层级{n_fn}")


if __name__ == "__main__":
    main()
