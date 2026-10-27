"""pair级NLI声明编译器: 多模态pair → 自然语言声明对(确定性内核).

方法核心(针对零样本NLI的已知失败模式):
  裸枚举对("包括A、B、C" vs "包括B、C、D")被NLI判为entailment(集合重叠偏置).
  → 闭世界模板: 声明附加"除此之外没有其他..."后缀, 将集合差异显式化为
    可判矛盾. 模板消融: T_closed(闭世界) vs T_plain(裸枚举).

声明网格(每pair, 按场景):
  A. enum       表格父实体子成员集合 vs 图中该实体邻居集合
                - sc1/sc4/sc5: 双列层级表(功能|子功能) + ID前缀分组
                - sc3:         接口表按发送方分组(接收方集合)
                - sc2/sc7:     用例名+步骤(图侧无对应节点时落aggregate)
                图侧邻居方向自适应(入边/出边/全部, 取与表侧重叠最大者,
                确定性: 并列取集合小者, 再按 入>出>全)
  B. aggregate  整表条目集合 vs 整图节点集合 (父实体未匹配时兜底,
                图侧过滤开始/结束/是否等流程修饰节点)
  C. text       正文句(提及表格实体) vs 表格闭世界条目声明

方向性: 闭世界后缀加在双侧, 由nli_local.predict_bidirectional覆盖.
依赖: 纯stdlib + lexical_kit + kt_compilers (无torch, 无网络).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from algorithms.blackboard.kt_compilers import (
    compile_for_scene,
    read_rows,
    split_name_id,
)
from algorithms.blackboard.lexical_kit import normalize_text, text_match_score

# ── 数据结构 ──────────────────────────────────────────────


@dataclass(slots=True)
class ClaimPair:
    """一对NLI输入(premise=声明侧, hypothesis=被验证侧)."""

    why: str             # "enum" | "aggregate" | "text"
    entity: str
    premise: str
    hypothesis: str
    template: str        # "closed" | "plain"
    meta: dict = field(default_factory=dict)


# ── 常量 ──────────────────────────────────────────────────

TABLE_LABEL = {
    "sc1_usecase_capability": "能力表", "sc4_flowchart_capability": "能力表",
    "sc5_function_capability": "子功能表",
    "sc2_flowchart_usecase": "用例描述表", "sc7_usecase_usecase": "用例描述表",
    "sc3_interface_interface": "接口表",
}

_MAX_MEMBERS = 12          # 集合成员上限(NLI max_len约束)
_PARENT_MATCH_TH = 0.55    # 表格父实体↔图节点 对齐阈值
_MEMBER_MATCH_TH = 0.8     # 成员重叠计数阈值
GRAPH_STOPWORDS = {"开始", "结束", "是", "否", "yes", "no", "end",
                   "start", "开始处理", "结束处理"}

# name-like场景: 图节点≈表格条目名(用例图/接口图/功能图), aggregate声明
# 的图侧可做成员过滤(滤actor/外部实体噪声); 流程图场景(sc2/sc4)节点为
# 步骤改写, 词法对齐不可靠, 保留全量节点作计数对照.
NAME_LIKE_SCENES = {"sc1_usecase_capability", "sc3_interface_interface",
                    "sc5_function_capability", "sc7_usecase_usecase"}


# ── 模板渲染 ──────────────────────────────────────────────

def _fmt(members: list[str]) -> str:
    return "、".join(members[:_MAX_MEMBERS])


def render_enum(role: str, entity: str, members: list[str],
                template: str, table_label: str = "功能表",
                member_noun: str = "子功能") -> str:
    """集合声明渲染. role=table|graph|graph_agg; closed=闭世界后缀."""
    if template == "closed":
        noun = member_noun if role == "table" else "节点"
        closed = f"，除此之外没有其他{noun}。"
    else:
        closed = "。"
    if role == "table":
        return (f"{table_label}规定，「{entity}」的{member_noun}共"
                f"{len(members)}项，包括：{_fmt(members)}{closed}")
    if role == "graph":
        return (f"图中显示，与「{entity}」直接相连的节点共{len(members)}个，"
                f"包括：{_fmt(members)}{closed}")
    return (f"图中显示，本图共包含{len(members)}个节点，"
            f"包括：{_fmt(members)}{closed}")


def render_flat(table_label: str, items: list[str], template: str) -> str:
    """整表扁平条目闭世界声明."""
    closed = "，除此之外没有其他条目。" if template == "closed" else "。"
    return f"{table_label}规定，本表共包含{len(items)}项条目，包括：{_fmt(items)}{closed}"


# ── 表侧: 分组 ────────────────────────────────────────────

def _strip_id(name: str) -> str:
    """'名称/标识' → 名称(标识不规范时partition兜底, 如含空格的ID)."""
    return name.partition("/")[0].strip() if "/" in name else name.strip()


def _hier_groups(csv_path: Path) -> list[tuple[str, list[str]]]:
    """层级表(序号|功能/标识|子功能/标识|...): 双列收集(名,ID) → ID前缀分组.

    例: 任务制定ID=JGHSJGJ-JGHSJGJRWZD 以 归集ID=JGHSJGJ 为前缀 → 归其子.
    """
    entries: list[tuple[str, str]] = []
    for r in read_rows(csv_path)[1:]:
        for col in (1, 2):
            if len(r) > col:
                name, tid = split_name_id(r[col])
                name = _strip_id(name)
                if name and tid and name not in ("—", "-"):
                    entries.append((name, tid))
    groups: dict[str, list[str]] = {}
    for name, tid in entries:
        for pname, pid in entries:
            if pid != tid and tid.startswith(pid + "-"):
                groups.setdefault(pname, [])
                if name not in groups[pname]:
                    groups[pname].append(name)
                break
    return sorted(groups.items())


def _interface_groups(csv_path: Path) -> list[tuple[str, list[str]]]:
    """接口表: 按发送方分组, 成员=去重接收方(发送方↔接收方闭世界)."""
    kt = compile_for_scene("sc3_interface_interface", csv_path)
    if not kt:
        return []
    by_sender: dict[str, list[str]] = {}
    for it in kt.get("interfaces", []):
        for a in it.get("interactions", []):
            s, r = a.get("sender", ""), a.get("receiver", "")
            if s and r:
                by_sender.setdefault(s, [])
                if r not in by_sender[s]:
                    by_sender[s].append(r)
    return sorted(by_sender.items())


def _usecase_groups(csv_path: Path) -> list[tuple[str, list[str]]]:
    """用例表: (用例名, 步骤列表) — 图侧常无同名节点, 多落aggregate."""
    kt = compile_for_scene("sc2_flowchart_usecase", csv_path)
    if not kt:
        return []
    uc = kt.get("uc_name", "")
    steps = [s for s in (kt.get("steps") or {}).values() if s]
    if uc and steps:
        return [(uc, steps)]
    return []


def table_groups(scene: str, csv_path: Path) -> tuple[list[tuple[str, list[str]]],
                                                      str]:
    """场景→(分组列表, 成员名词). 返回空分组时由aggregate兜底."""
    if scene in ("sc1_usecase_capability", "sc4_flowchart_capability",
                 "sc5_function_capability"):
        return _hier_groups(csv_path), "子功能"
    if scene == "sc3_interface_interface":
        return _interface_groups(csv_path), "接收方"
    if scene in ("sc2_flowchart_usecase", "sc7_usecase_usecase"):
        return _usecase_groups(csv_path), "步骤"
    return [], "条目"


def table_flat_items(scene: str, csv_path: Path) -> list[str]:
    """κ_T编译 → 扁平条目名列表(aggregate/text声明用, 含清洗).

    interface: 只留接口名(含"接口"或有标识), 滤组件名混入行;
    usecase:   只留步骤+异常(滤actor/用例结束标记).
    """
    kt = compile_for_scene(scene, csv_path)
    if not kt:
        return []
    t = kt.get("type")
    if t in ("capability", "subfunction"):
        return [c["name"] for c in (kt.get("caps") or kt.get("subs") or [])
                if c.get("name")]
    if t == "usecase":
        items = []
        for n in (kt.get("nodes") or []):
            txt = n.get("text", "")
            if not txt or n.get("type") == "actor":
                continue
            if normalize_text(txt).startswith(("用例结束", "用例开始")):
                continue
            items.append(txt)
        return items
    if t == "interface":
        return [_strip_id(it["name"]) for it in kt.get("interfaces", [])
                if it.get("name") and ("接口" in it["name"] or it.get("id"))]
    return []


# ── 图侧: 节点/方向感知邻居 ────────────────────────────────

def _clean_node_text(t: str) -> str:
    return t.strip().replace("\n", "")


def _lev(a: str, b: str) -> int:
    """编辑距离(截断容差用; lexical_kit._lev为私有, 不跨模块引用)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            cur.append(min(prev[j + 1] + 1, cur[-1] + 1, prev[j] + (ca != cb)))
        prev = cur
    return prev[-1]


def _is_subsequence(short: str, long: str) -> bool:
    """short是否为long的子序列(保序)."""
    it = iter(long)
    return all(c in it for c in short)


def align_score(name: str, node: str) -> float:
    """对齐分: max(lexical_kit基础分, 离散子序列截断证据).

    截断案例: 节点"半构化数据归集"(缺中间'结') vs 表格"半结构化数据归集" —
    离散子序列(保序但非连续), 与连续包含的兄弟名("结构化数据归集"⊂
    "半结构化数据归集")可区分: 前者0.92, 后者维持text_match_score的0.9.
    """
    s = text_match_score(name, node)
    na, nb = normalize_text(name), normalize_text(node)
    if min(len(na), len(nb)) >= 4:
        shorter, longer = (nb, na) if len(nb) <= len(na) else (na, nb)
        if shorter not in longer and _is_subsequence(shorter, longer) \
                and len(shorter) / len(longer) >= 0.75:
            return max(s, 0.92)
        if s < 0.55:
            d = _lev(na, nb)
            ratio = 1 - d / max(len(na), len(nb))
            if ratio >= 0.75:
                return 0.7 + 0.2 * ratio
    return s


def graph_node_texts(anchor: dict, drop_stop: bool = True) -> list[str]:
    """去重节点文本列表; drop_stop剔除开始/结束/是否等流程修饰节点."""
    seen: set[str] = set()
    out: list[str] = []
    for n in anchor.get("nodes", []):
        if not n.get("text"):
            continue
        t = _clean_node_text(n["text"])
        nt = normalize_text(t)
        if not nt or nt in seen:
            continue
        if drop_stop and nt.lower() in GRAPH_STOPWORDS:
            continue
        seen.add(nt)
        out.append(t)
    return out


def graph_adjacency(anchor: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """(入边邻居, 出边邻居): node_id → 邻居文本列表(按边方向拆分)."""
    nodes = {n["id"]: n for n in anchor.get("nodes", [])}
    adj_in: dict[str, list[str]] = {nid: [] for nid in nodes}
    adj_out: dict[str, list[str]] = {nid: [] for nid in nodes}
    for e in anchor.get("edges", []):
        s, d = e.get("src"), e.get("dst")
        if s not in nodes or d not in nodes or s == d:
            continue
        adj_out[s].append(_clean_node_text(nodes[d]["text"]))
        adj_in[d].append(_clean_node_text(nodes[s]["text"]))
    return adj_in, adj_out


def _dedup(texts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for t in texts:
        nt = normalize_text(t)
        if nt and nt not in seen:
            seen.add(nt)
            out.append(_clean_node_text(t))
    return out


def best_neighbor_set(nid: str, adj_in: dict[str, list[str]],
                      adj_out: dict[str, list[str]],
                      children: list[str]) -> list[str] | None:
    """方向自适应邻居: 入/出/全三候选, 取与表侧成员重叠(≥0.8)最大者.

    确定性tie-break: 重叠相等→集合更小者(高精度); 再相等→入>出>全.
    层级图子→父边(入邻居=子成员), 流程图序列边(全邻居).
    """
    cand: list[tuple[str, list[str]]] = [
        ("in", _dedup(adj_in.get(nid, []))),
        ("out", _dedup(adj_out.get(nid, []))),
        ("all", _dedup(adj_in.get(nid, []) + adj_out.get(nid, []))),
    ]
    order = {"in": 0, "out": 1, "all": 2}
    ranked: list[tuple[tuple[int, int, int], list[str]]] = []
    for label, texts in cand:
        if not texts:
            continue
        overlap = sum(1 for c in children
                      if any(align_score(c, t) >= _MEMBER_MATCH_TH
                             for t in texts))
        ranked.append(((overlap, -len(texts), -order[label]), texts))
    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]


def assign_parents_to_nodes(parents: list[str], node_texts: list[str],
                            th: float = _PARENT_MATCH_TH) -> dict[str, str]:
    """父实体→图节点 一对一分配(贪心, 确定性).

    排序键: (对齐分, 前缀对齐加成, 节点更长优先, 父名, 节点文本).
    冲突案例: "结构化数据归集"与"半结构化数据归集"都包含节点"结构化数据归"
    (截断文本) → 前缀对齐加成使包含关系成立者(前者)胜出.
    """
    cands: list[tuple[float, int, int, str, str]] = []
    for p in parents:
        np_ = normalize_text(p)
        for t in node_texts:
            s = align_score(p, t)
            if s < th:
                continue
            nt = normalize_text(t)
            prefix = bool(nt) and bool(np_) and (np_.startswith(nt)
                                                 or nt.startswith(np_))
            cands.append((s, 1 if prefix else 0, len(nt), p, t))
    claimed_nodes: set[str] = set()
    out: dict[str, str] = {}
    for s, pre, ln, p, t in sorted(cands, key=lambda x: (-x[0], -x[1], -x[2], x[3], x[4])):
        if p in out or t in claimed_nodes:
            continue
        out[p] = t
        claimed_nodes.add(t)
    return out


# ── 文侧: 句子切分 ─────────────────────────────────────────

_SENT_SPLIT = re.compile(r"[。；;.!？?\n]+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text)
            if s.strip() and len(s.strip()) >= 8]


# ── 声明对构造 ─────────────────────────────────────────────

def build_claim_pairs(scene: str, table_csv: Path, text: str,
                      anchor: dict | None, template: str = "closed",
                      pair_id: str = "") -> list[ClaimPair]:
    """构造一个pair的NLI声明对集合(全确定性). 空输出=诚实排除."""
    label = TABLE_LABEL.get(scene, "功能表")
    out: list[ClaimPair] = []
    groups, member_noun = table_groups(scene, table_csv)
    flat_items = table_flat_items(scene, table_csv)

    # A. enum: 表格父分组 vs 图方向自适应邻居
    if groups and anchor:
        node_texts = graph_node_texts(anchor)
        adj_in, adj_out = graph_adjacency(anchor)
        node_id_by_text: dict[str, str] = {}
        for n in anchor.get("nodes", []):
            if n.get("text"):
                node_id_by_text[_clean_node_text(n["text"])] = n["id"]
        assignment = assign_parents_to_nodes([p for p, _ in groups],
                                             node_texts)
        # 图侧成员过滤基准: 全表成员(父+子) — 滤除上游链接/系统根节点等
        # 非表内实体(保留错挂检测: 子成员出现在错误父的邻居集仍触发矛盾)
        all_members = [p for p, _ in groups] + [c for _, cs in groups for c in cs]

        def _is_table_member(t: str) -> bool:
            return any(align_score(t, m) >= 0.75 for m in all_members)

        for parent, children in groups:
            gn = assignment.get(parent)
            if gn is None:
                continue
            nid = node_id_by_text.get(gn, "")
            g_nbrs = best_neighbor_set(nid, adj_in, adj_out, children)
            if not g_nbrs:
                continue
            g_nbrs = [t for t in g_nbrs if _is_table_member(t)]
            if not g_nbrs:
                continue
            out.append(ClaimPair(
                why="enum", entity=parent,
                premise=render_enum("table", parent, children, template,
                                    label, member_noun),
                hypothesis=render_enum("graph", gn, g_nbrs, template),
                template=template,
                meta={"table_members": children, "graph_members": g_nbrs}))

    # B. aggregate: 整表条目 vs 整图节点 (enum未产出时兜底)
    #    name-like场景图侧成员过滤: 滤actor/外部实体; 过滤后<2节点
    #    (内容错配信号)则保留全量. sc3特例: 图侧优先只留接口节点
    #    (谓词对齐, 组件名经接口解包匹配会虚增计数).
    if anchor and not out and flat_items:
        nodes = graph_node_texts(anchor)
        if scene in NAME_LIKE_SCENES:
            settled = False
            if scene == "sc3_interface_interface":
                ifaces = [t for t in nodes if "接口" in normalize_text(t)]
                if len(ifaces) >= 2:
                    nodes, settled = ifaces, True
            if not settled:
                matched = [t for t in nodes
                           if any(align_score(t, m) >= 0.55 for m in flat_items)]
                if len(matched) >= 2:
                    nodes = matched
        if nodes:
            out.append(ClaimPair(
                why="aggregate", entity="(整表)",
                premise=render_flat(label, flat_items, template),
                hypothesis=render_enum("graph_agg", "", nodes, template),
                template=template,
                meta={"table_members": flat_items, "graph_members": nodes}))

    # C. text: 正文句(提及任一表格实体) vs 整表闭世界声明
    if flat_items:
        entities = {p for p, _ in groups} | set(flat_items)
        for sent in split_sentences(text):
            if any(_mentions(sent, e) for e in entities):
                out.append(ClaimPair(
                    why="text", entity="(正文)",
                    premise=f"正文规定：{sent}",
                    hypothesis=render_flat(label, flat_items, template),
                    template=template,
                    meta={"sentence": sent, "table_members": flat_items}))
    return out


def _mentions(sentence: str, entity: str) -> bool:
    """正文句是否提及该实体(规范化包含)."""
    ns, ne = normalize_text(sentence), normalize_text(entity)
    return bool(ne) and ne in ns


# ── 薄I/O层 ────────────────────────────────────────────────

def load_pair_claims(pair_dir: Path, template: str = "closed"
                     ) -> tuple[str, list[ClaimPair]]:
    """读取pair目录 → (pair_id, 声明对). sc8/无表/无锚点→空列表(诚实排除)."""
    pair_id = pair_dir.name
    scene = pair_dir.parent.name
    table_csv = pair_dir / "table.csv"
    text = ""
    text_path = pair_dir / "text.txt"
    if text_path.exists():
        text = text_path.read_text(encoding="utf-8")
    anchor = None
    anchor_path = pair_dir / "visio_anchor.json"
    if anchor_path.exists():
        try:
            anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            anchor = None
    if scene.startswith("sc8") or not table_csv.exists():
        return pair_id, []
    claims = build_claim_pairs(scene, table_csv, text, anchor,
                               template=template, pair_id=pair_id)
    return pair_id, claims
