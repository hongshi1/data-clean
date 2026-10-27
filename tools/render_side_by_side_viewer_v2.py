#!/usr/bin/env python3
"""Render a self-contained side-by-side HTML viewer v2 for one GJB SRS document.

v2 在 v1（tools/render_side_by_side_viewer.py 左原文/右卡片/滚动联动/span高亮/
base64图/自包含HTML）结构上升级，消费 v2 系列特征产物:

左栏:
- text块: v1 regex span 高亮(编号/引用/数值单位/模态/否定) + v2 语句层高亮
  （claim 覆盖范围淡蓝底 / 条件短语橙色背景+边框 / 否定词红色下划线 /
  scope 实体紫色虚线边框），多层同段共存由分段渲染器合并 class
- table块: tables_v2 单元格网格重建（合并单元格 rowspan/colspan 跨格红边框，
  每格左上角 rNcN 坐标小字）+ 表头树（header_tree 嵌套缩进显示在表格上方）
- image块: caption + base64 图（同 v1, --max-images 控制）

右栏（与左滚动联动）:
- text卡: claim 五元组(v1 claim_slot_features 按 claim_id 联接) + 实体类型
  badge(entity_type_v2: 接口蓝/模块青/功能绿/参数橙/数据项紫/分系统棕) +
  条件/否定词计数 + 引用解析状态(resolved target_id 绿/unresolved 红)
- table卡: 表头树文本结构 + 合并单元格统计 + 空值分布
- image卡: Visio SVG 简绘图——nodes 几何画矩形(文本缩略+master_type小字) +
  edges 折线(waypoints 有则折线否则直线) + 箭头方向渲染(forward→/backward←/
  bidirectional↔/undetermined 灰线无箭头) + 泳道横带(lanes 交替底色+标签) +
  循环红圈/fork 菱形标注

顶部: v1 质量信号条 + v2 统计（实体类型分布条形 / 三档对齐 explicit 绿·
supported 琥珀 / 箭头方向分布 / 循环图数 / 泳道图数, 全数据集+本文档双层）
底部 policy: 单位完整率红色警示条 + include/extend 全 unknown 警示

Usage:
  python tools/render_side_by_side_viewer_v2.py [--doc 04] [--section 3.2]
      [--output PATH] [--max-images 20]
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
MINERU_STANDARD = BASE / "data/gjb_438c/mineru_standard"
FEATURE_V2_DIR = BASE / "data/gjb_438c/feature_matrix_v2"
VISIO_DIR = BASE / "data/gjb_438c/visio_features_v2"
SEMANTIC_DIR = BASE / "data/gjb_438c/semantic_features_v2"
FEATURE_V1_DIR = BASE / "data/gjb_438c/feature_matrix_v1"
CORPUS_DIR = BASE / "data/gjb_438c/structured_corpus_v1"
DEFAULT_OUTPUT = FEATURE_V1_DIR / "side_by_side_v2_{doc}.html"

RENDER_TYPES = ("text", "list", "table", "image")

SECTION_HEADING_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+\S")
REQ_ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
REF_RE = re.compile(r"(?:图|表)\s*[0-9]+")
MODAL_RE = re.compile(r"应当|不得|禁止|必须|应")
NEG_RE = re.compile(r"不允许|无法|不能|不可|没有|未能|未|无|非|不")
NUM_UNIT_RE = re.compile(
    r"([0-9]+(?:[.,][0-9]+)*)\s*"
    r"(毫秒|微秒|分钟|小时|万条|Mbps|Gbps|Kbps|bps|Mbit/s|kbit/s|bit/s|ms|us|μs|"
    r"KB|MB|GB|TB|kB|Kb|Mb|Gb|kHz|MHz|GHz|Hz|dB|kV|kW|MW|QPS|TPS|fps|Byte|byte|bit|"
    r"km|cm|mm|kg|秒|分|天|日|年|月|条|次|路|个|帧|用户|字节|比特|台|套|级|位|笔|页|"
    r"万|亿|℃|％|%|V|W|s|h)"
)
CAPTION_NUM_RE = re.compile(r"^\s*(图|表)\s*([0-9]+)")
TAG_SPLIT_RE = re.compile(r"(<[^>]*>)")
SCRIPT_RE = re.compile(r"<script\b.*?(?:</script>|$)", re.I | re.S)
ONEVENT_RE = re.compile(r"\son\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
HTTP_RE = re.compile(r"https?://", re.I)

SPAN_CLASSES = (
    ("fm-id", REQ_ID_RE),
    ("fm-ref", REF_RE),
    ("fm-num", NUM_UNIT_RE),
    ("fm-modal", MODAL_RE),
    ("fm-neg", NEG_RE),
)
SPAN_LABELS = {
    "fm-id": "编号",
    "fm-ref": "引用",
    "fm-num": "数值单位",
    "fm-modal": "模态",
    "fm-neg": "否定",
    "v2-claim": "claim覆盖",
    "v2-cond": "条件短语",
    "v2-neg": "否定词",
    "v2-scope": "scope实体",
}

# 实体类型 badge: 接口蓝 / 模块青 / 功能绿 / 参数橙 / 数据项紫 / 分系统棕
ENTITY_TYPE_META = {
    "接口": ("et-iface", "#1d4ed8"),
    "模块": ("et-module", "#0e7490"),
    "功能": ("et-func", "#15803d"),
    "参数": ("et-param", "#c2410c"),
    "数据项": ("et-data", "#7e22ce"),
    "分系统": ("et-sys", "#92400e"),
}
ENTITY_TYPE_ORDER = ("接口", "模块", "功能", "参数", "数据项", "分系统")

# 箭头方向: forward→ / backward← / bidirectional↔ / none—(灰线无箭头)
# 数据实际值: directed_src_to_dst / directed_dst_to_src / bidirectional / undetermined
DIRECTION_META = {
    "directed_src_to_dst": ("forward", "→", "v2-edge-forward", True, False),
    "forward": ("forward", "→", "v2-edge-forward", True, False),
    "directed_dst_to_src": ("backward", "←", "v2-edge-backward", False, True),
    "backward": ("backward", "←", "v2-edge-backward", False, True),
    "bidirectional": ("bidirectional", "↔", "v2-edge-bidirectional", True, True),
    "none": ("none", "—", "v2-edge-none", False, False),
    "undetermined": ("none", "—", "v2-edge-none", False, False),
}

# 节点类型配色 (fill, stroke)
NODE_TYPE_STYLE = {
    "start": ("#dcfce7", "#15803d"),
    "end": ("#fee2e2", "#b91c1c"),
    "process": ("#dbeafe", "#1d4ed8"),
    "decision": ("#fef3c7", "#b45309"),
    "datastore": ("#f3e8ff", "#7e22ce"),
    "actor": ("#cffafe", "#0e7490"),
    "usecase": ("#ede9fe", "#6d28d9"),
    "state": ("#e2e8f0", "#475569"),
    "boundary": ("#ffffff", "#94a3b8"),
    "interface": ("#e0f2fe", "#0369a1"),
    "io": ("#ecfeff", "#0891b2"),
    "message": ("#fef9c3", "#a16207"),
    "fork": ("#f59e0b", "#b45309"),
    "class": ("#e0e7ff", "#4338ca"),
    "deployment": ("#f1f5f9", "#475569"),
    "component": ("#dbeafe", "#1e40af"),
    "package": ("#f0fdf4", "#166534"),
    "activation": ("#ede9fe", "#6d28d9"),
    "other": ("#f1f5f9", "#64748b"),
}
NODE_TYPE_FALLBACK = ("#f1f5f9", "#64748b")

# (key, label, inverted, process) — process=True 为元指标（小灰字）
QUALITY_METRICS = (
    ("claim_slot_fill_rate_avg", "解析完整度(过程指标)", False, True),
    ("reference_resolution_rate", "引用解析率", False, False),
    ("unit_completeness", "单位完整率", False, False),
    ("table_header_missing_rate", "表头缺失率", True, False),
    ("empty_text_node_rate", "空文本率", True, False),
)

ALIGN_STATUS_META = {
    "explicit": ("g", "显式对齐"),
    "supported": ("a", "支撑对齐"),
    "speculative": ("r", "推测对齐"),
}


# ---------------------------------------------------------------- IO helpers


def read_jsonl(path: Path, doc_id: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and (doc_id is None or row.get("doc_id") == doc_id):
                rows.append(row)
    return rows


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return None


def find_doc_assets(doc_id: str) -> tuple[Path, Path, Path]:
    if not MINERU_STANDARD.is_dir():
        raise FileNotFoundError(f"mineru_standard 目录不存在: {MINERU_STANDARD}")
    matches = sorted(
        p for p in MINERU_STANDARD.iterdir() if p.is_dir() and p.name.startswith(doc_id)
    )
    if not matches:
        raise FileNotFoundError(f"mineru_standard 下未找到文档 {doc_id}")
    doc_dir = matches[0]
    office = doc_dir / "office"
    if not office.is_dir():
        raise FileNotFoundError(f"office 目录不存在: {office}")
    preferred = office / f"{doc_dir.name}_content_list.json"
    if preferred.exists():
        return doc_dir, office, preferred
    candidates = sorted(p for p in office.glob("*_content_list.json") if "_v2" not in p.name)
    if not candidates:
        raise FileNotFoundError(f"未找到 content_list.json: {office}")
    return doc_dir, office, candidates[0]


# ------------------------------------------------------------- text pipeline


def sanitize_fragment(fragment: str) -> str:
    """Keep MinerU light HTML (sub/sup/p), strip active content and external URLs."""
    fragment = SCRIPT_RE.sub("", fragment)
    fragment = ONEVENT_RE.sub("", fragment)
    return HTTP_RE.sub("hxxp://", fragment)


def plain_with_offsets(raw: str) -> tuple[str, list[int]]:
    """Strip tags for matching; keep a plain-offset -> raw-offset map per char."""
    parts = TAG_SPLIT_RE.split(raw)
    plain: list[str] = []
    offsets: list[int] = []
    pos = 0
    for part in parts:
        if not part:
            continue
        if part.startswith("<") and part.endswith(">") and len(part) > 2:
            pos += len(part)
        else:
            for ch in part:
                plain.append(ch)
                offsets.append(pos)
                pos += 1
    return "".join(plain), offsets


def plain_span_to_raw(offsets: list[int], ps: int, pe: int) -> tuple[int, int]:
    """Map plain [ps, pe) to a raw span (assumes pe > ps)."""
    rs = offsets[ps]
    re_ = offsets[pe - 1] + 1
    return rs, re_


def _sub_range(
    text: str, pos: Any, needle: str, base: int, domain: str, offsets: list[int] | None
) -> tuple[int, int] | None:
    """Resolve (pos, needle) relative to sentence text -> absolute raw range.

    domain="raw": base 为句子在 raw 中的起点, 直接平移; domain="plain": 先在
    plain 坐标平移再经 offsets 映射回 raw. pos 未命中时回退 find。
    """
    if not needle:
        return None
    try:
        ipos = int(pos) if pos is not None else -1
    except (TypeError, ValueError):
        ipos = -1
    if ipos >= 0 and 0 <= ipos <= len(text) and text[ipos : ipos + len(needle)] == needle:
        lo, hi = ipos, ipos + len(needle)
    else:
        p = text.find(needle)
        if p < 0:
            return None
        lo, hi = p, p + len(needle)
    if domain == "plain" and offsets:
        return plain_span_to_raw(offsets, lo, hi)
    return base + lo, base + hi


def sentence_layer_ranges(
    sentence: dict[str, Any], attach: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build v2 highlight ranges (raw coords within the render unit) for one sentence."""
    rs, re_ = attach["rs"], attach["re"]
    domain = attach.get("domain", "raw")
    offsets = attach.get("offsets")
    text = str(sentence.get("text") or "")
    out: list[dict[str, Any]] = []
    claim_id = str(sentence.get("claim_id") or "")
    if re_ > rs:
        out.append(
            {
                "rs": rs,
                "re": re_,
                "cls": "v2-claim",
                "title": claim_id or "claim",
                "claim": claim_id,
            }
        )
    for cond in sentence.get("conditions") or []:
        if not isinstance(cond, dict):
            continue
        needle = str(cond.get("raw") or cond.get("cond_text") or "")
        rng = _sub_range(text, cond.get("pos"), needle, rs, domain, offsets)
        if rng:
            out.append(
                {"rs": rng[0], "re": rng[1], "cls": "v2-cond", "title": f"条件: {needle[:24]}"}
            )
    for neg in sentence.get("negations") or []:
        if not isinstance(neg, dict):
            continue
        needle = str(neg.get("word") or "")
        rng = _sub_range(text, neg.get("pos"), needle, rs, domain, offsets)
        if rng:
            out.append(
                {"rs": rng[0], "re": rng[1], "cls": "v2-neg", "title": f"否定词: {needle}"}
            )
    for sc in sentence.get("scope_entity") or []:
        if not isinstance(sc, dict):
            continue
        needle = str(sc.get("raw") or sc.get("entity") or "")
        rng = _sub_range(text, sc.get("pos"), needle, rs, domain, offsets)
        if rng:
            out.append(
                {
                    "rs": rng[0],
                    "re": rng[1],
                    "cls": "v2-scope",
                    "title": f"scope: {str(sc.get('entity') or '')[:24]}",
                }
            )
    return out


def regex_raw_ranges(plain: str, offsets: list[int]) -> list[dict[str, Any]]:
    """v1 regex span classes, converted to raw coordinates."""
    out: list[dict[str, Any]] = []
    for cls, rx in SPAN_CLASSES:
        for m in rx.finditer(plain):
            if m.end() <= m.start():
                continue
            rs, re_ = plain_span_to_raw(offsets, m.start(), m.end())
            out.append({"rs": rs, "re": re_, "cls": cls, "title": SPAN_LABELS.get(cls, cls)})
    return out


def render_segmented(
    raw: str, ranges: list[dict[str, Any]]
) -> tuple[str, list[dict[str, Any]]]:
    """Layered segment renderer: 合并多层高亮 class, 无嵌套 mark.

    ranges: [{rs, re, cls, title?, claim?}] raw 坐标; 层间重叠(claim 覆盖条件/
    否定)通过同段合并 class 共存, 背景冲突由 CSS 声明顺序裁决(v2-cond 最后)。
    """
    valid = [r for r in ranges if 0 <= r["rs"] < r["re"] <= len(raw)]
    dedup: dict[tuple[int, int, str], dict[str, Any]] = {}
    for r in valid:
        dedup[(r["rs"], r["re"], r["cls"])] = r
    ordered = sorted(dedup.values(), key=lambda r: (r["rs"], r["re"]))
    if not ordered:
        return raw, []
    bounds: set[int] = {0, len(raw)}
    for r in ordered:
        bounds.add(r["rs"])
        bounds.add(r["re"])
    pts = sorted(bounds)
    out: list[str] = []
    for a, b in zip(pts, pts[1:]):
        seg = raw[a:b]
        if not seg:
            continue
        covering = [r for r in ordered if r["rs"] <= a and r["re"] >= b]
        if not covering:
            out.append(seg)
            continue
        classes = " ".join(sorted({r["cls"] for r in covering}))
        titles: list[str] = []
        for t in (r.get("title") for r in covering):
            if t and t not in titles:
                titles.append(t)
        claim = next((r["claim"] for r in covering if r.get("claim")), "")
        attrs = f' class="{classes}"'
        if titles:
            attrs += ' title="' + escape("; ".join(titles[:4])) + '"'
        if claim:
            attrs += f' data-claim="{escape(claim)}"'
        out.append(f"<mark{attrs}>{seg}</mark>")
    return "".join(out), ordered


def build_units(block: dict[str, Any]) -> list[str]:
    if block.get("type") == "text":
        return [str(block.get("text") or "")]
    if block.get("type") == "list":
        return [str(item) for item in block.get("list_items") or []]
    return []


def locate_sentences(
    render_list: list[dict[str, Any]],
    blocks: list[Any],
    sentences: list[dict[str, Any]],
    unit_data: dict[int, list[dict[str, Any]]],
) -> tuple[dict[int, list[dict[str, Any]]], set[str]]:
    """sentences.jsonl span{block_idx,start,end} -> 块内 raw 定位(带 find 回退)."""
    block_sents: dict[int, list[dict[str, Any]]] = {}
    located: set[str] = set()

    def attach(
        bi: int, ui: int, rs: int, re_: int, sent: dict[str, Any], domain: str,
        offsets: list[int] | None,
    ) -> None:
        cid = str(sent.get("claim_id") or "")
        block_sents.setdefault(bi, []).append(
            {
                "sentence": sent,
                "ui": ui,
                "rs": rs,
                "re": re_,
                "domain": domain,
                "offsets": offsets,
                "claim_id": cid,
            }
        )
        if cid:
            located.add(cid)

    for sent in sentences:
        text = str(sent.get("text") or "")
        if not text:
            continue
        span = sent.get("span") or {}
        bi, st, en = span.get("block_idx"), span.get("start"), span.get("end")
        attached = False
        if (
            isinstance(bi, int)
            and 0 <= bi < len(blocks)
            and isinstance(st, int)
            and isinstance(en, int)
        ):
            units = unit_data.get(bi) or []
            if units and isinstance(blocks[bi], dict) and blocks[bi].get("type") == "text":
                raw = units[0]["raw"]
                if 0 <= st < en <= len(raw) and raw[st:en] == text:
                    attach(bi, 0, st, en, sent, "raw", None)
                    attached = True
            if not attached and units and isinstance(blocks[bi], dict) and blocks[bi].get("type") == "list":
                for ui, ud in enumerate(units):
                    p = ud["plain"].find(text)
                    if p >= 0:
                        rs, re_ = plain_span_to_raw(ud["offsets"], p, p + len(text))
                        attach(bi, ui, rs, re_, sent, "plain", ud["offsets"])
                        attached = True
                        break
        if attached:
            continue
        # 回退: 全文 find 定位（span 指向异常块或坐标漂移时）
        for entry in render_list:
            if attached:
                break
            if entry["kind"] not in ("text", "list"):
                continue
            for ui, ud in enumerate(unit_data.get(entry["index"]) or []):
                p = ud["plain"].find(text)
                if p >= 0:
                    rs, re_ = plain_span_to_raw(ud["offsets"], p, p + len(text))
                    attach(entry["index"], ui, rs, re_, sent, "plain", ud["offsets"])
                    attached = True
                    break
    for items in block_sents.values():
        items.sort(key=lambda it: (it["ui"], it["rs"]))
    return block_sents, located


# ------------------------------------------------------------ table pipeline


def header_tree_lines(
    nodes: list[Any] | None,
    depth: int = 0,
    out: list[tuple[int, str, int, int]] | None = None,
) -> list[tuple[int, str, int, int]]:
    """header_tree 嵌套节点 -> [(depth, text, rowspan, colspan), ...] 缩进行."""
    if out is None:
        out = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        text = str(node.get("text") or "")
        try:
            rs = int(node.get("rowspan") or 1)
        except (TypeError, ValueError):
            rs = 1
        try:
            cs = int(node.get("colspan") or 1)
        except (TypeError, ValueError):
            cs = 1
        out.append((depth, text, rs, cs))
        header_tree_lines(node.get("children"), depth + 1, out)
    return out


def header_tree_html(header_tree: dict[str, Any] | None) -> str:
    """表头树嵌套缩进渲染（显示在表格上方）."""
    if not isinstance(header_tree, dict):
        return ""
    lines = header_tree_lines(header_tree.get("nodes") or [])
    lines = [ln for ln in lines if ln[1].strip() or ln[2] > 1 or ln[3] > 1]
    if not lines:
        return ""
    levels = header_tree.get("levels")
    head = "表头树" + (f" · {levels}级" if levels else "")
    parts = [f'<div class="v2-htree"><div class="v2-hthead">{escape(head)}</div>']
    for depth, text, rs, cs in lines:
        meta = f" r{rs}×c{cs}" if (rs > 1 or cs > 1) else ""
        prefix = "└ " if depth else ""
        parts.append(
            '<div class="v2-htline" style="margin-left:'
            + str(depth * 18)
            + 'px">'
            + prefix
            + escape(text)
            + '<span class="v2-htmeta">'
            + meta
            + "</span></div>"
        )
    parts.append("</div>")
    return "".join(parts)


def build_table_html_v2(table_row: dict[str, Any]) -> tuple[str, dict[str, int]]:
    """tables_v2 cells -> HTML 表格: 合并跨格红边框 + rNcN 坐标小字."""
    cells = [c for c in table_row.get("cells") or [] if isinstance(c, dict)]
    if not cells:
        return "", {}
    by_pos: dict[tuple[int, int], dict[str, Any]] = {}
    for c in cells:
        try:
            by_pos[(int(c.get("row", 0)), int(c.get("col", 0)))] = c
        except (TypeError, ValueError):
            continue
    max_r = max(k[0] for k in by_pos)
    max_c = max(k[1] for k in by_pos)
    occupied: set[tuple[int, int]] = set()
    stats = {
        "merged_origins": 0,
        "covered_cells": 0,
        "empty_cells": 0,
        "coord_labels": 0,
        "cells_rendered": 0,
    }
    parts = ['<table class="v2tbl">']
    for r in range(max_r + 1):
        parts.append("<tr>")
        for c in range(max_c + 1):
            if (r, c) in occupied:
                continue
            cell = by_pos.get((r, c))
            if cell is None:
                parts.append(f'<td class="v2-gap"><span class="v2-cc">r{r}c{c}</span></td>')
                stats["coord_labels"] += 1
                continue
            try:
                rs = max(1, int(cell.get("rowspan") or 1))
            except (TypeError, ValueError):
                rs = 1
            try:
                cs = max(1, int(cell.get("colspan") or 1))
            except (TypeError, ValueError):
                cs = 1
            for dr in range(rs):
                for dc in range(cs):
                    occupied.add((r + dr, c + dc))
            text = str(cell.get("text") or "")
            classes: list[str] = []
            if cell.get("is_merged_origin") or rs > 1 or cs > 1:
                classes.append("v2-merged")
                stats["merged_origins"] += 1
                stats["covered_cells"] += rs * cs
            if not text.strip():
                classes.append("v2-empty-cell")
                stats["empty_cells"] += 1
            attrs = ""
            if rs > 1:
                attrs += f' rowspan="{rs}"'
            if cs > 1:
                attrs += f' colspan="{cs}"'
            cls = (' class="' + " ".join(classes) + '"') if classes else ""
            parts.append(
                f"<td{attrs}{cls}><span class=\"v2-cc\">r{r}c{c}</span>"
                + escape(text)
                + "</td>"
            )
            stats["coord_labels"] += 1
            stats["cells_rendered"] += 1
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts), stats


def table_empty_distribution(cells: list[dict[str, Any]]) -> dict[str, int]:
    dist = {"empty": 0, "dash": 0, "text": 0}
    for c in cells:
        if not isinstance(c, dict):
            continue
        text = str(c.get("text") or "").strip()
        if not text:
            dist["empty"] += 1
        elif text in {"—", "-", "–", "/", "—"}:
            dist["dash"] += 1
        else:
            dist["text"] += 1
    return dist


def caption_number(captions: list[str] | None, kind: str) -> int | None:
    if not captions:
        return None
    m = CAPTION_NUM_RE.match(str(captions[0]))
    if m and m.group(1) == kind:
        try:
            return int(m.group(2))
        except ValueError:
            return None
    return None


# ------------------------------------------------- entity / direction mapping


def entity_badge_cls(entity_type: str) -> tuple[str, str]:
    """实体类型 -> (css class, 颜色); 未知类型回退灰色."""
    meta = ENTITY_TYPE_META.get(str(entity_type or "").strip())
    if meta:
        return meta
    return ("et-other", "#5c6b7a")


def entity_badge_html(entity_type: str, basis: str | None = None) -> str:
    cls, _color = entity_badge_cls(entity_type)
    label = str(entity_type or "").strip() or "未分类"
    title = f"实体类型 {label}" + (f" · 判定依据 {basis}" if basis else "")
    return f'<span class="ebadge {cls}" title="{escape(title)}">{escape(label)}</span>'


def direction_style(direction_status: Any) -> tuple[str, str, str, bool, bool]:
    """direction_status -> (label, glyph, polyline class, marker_end, marker_start)."""
    key = str(direction_status or "").strip().lower()
    meta = DIRECTION_META.get(key)
    if meta:
        return meta
    return DIRECTION_META["undetermined"]


# -------------------------------------------------------------- SVG renderer


def _fmt(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".") or "0"


def _wrap_cjk(text: str, per_line: int = 8, max_lines: int = 3) -> list[str]:
    flat = re.sub(r"\s+", " ", str(text or "").strip())
    if not flat:
        return []
    if len(flat) <= per_line:
        return [flat]
    lines = [flat[i : i + per_line] for i in range(0, len(flat), per_line)]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:-1] + "…"
    return lines


def _num(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def render_diagram_svg(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    lanes_row: dict[str, Any] | None,
    graph_row: dict[str, Any] | None,
    seq: int,
    width: float = 520.0,
) -> tuple[str, dict[str, int]]:
    """Visio 几何 -> SVG 简绘图.

    节点矩形(文本缩略+master_type小字), 边折线(waypoints 或直线)+箭头方向渲染,
    泳道横带(交替底色+标签), 循环红圈, fork 菱形. Visio y 向上, 渲染时翻转.
    """
    geo: dict[str, tuple[float, float, float, float]] = {}
    pts: list[tuple[float, float]] = []
    for n in nodes:
        g = n.get("geometry") or {}
        cx, cy = _num(g.get("cx")), _num(g.get("cy"))
        w, h = _num(g.get("w")), _num(g.get("h"))
        if cx is None or cy is None:
            continue
        w = max(w or 0.0, 0.0)
        h = max(h or 0.0, 0.0)
        geo[str(n.get("node_id") or "")] = (cx, cy, w, h)
        pts.append((cx - w / 2, cy - h / 2))
        pts.append((cx + w / 2, cy + h / 2))
    if not pts:
        return "", {"svg_nodes": 0}
    edge_polys: list[tuple[dict[str, Any], list[tuple[float, float]]]] = []
    for e in edges:
        wps: list[tuple[float, float]] = []
        for p in e.get("waypoints") or []:
            if not isinstance(p, (list, tuple)) or len(p) < 2:
                continue
            x, y = _num(p[0]), _num(p[1])
            if x is not None and y is not None:
                wps.append((x, y))
        if wps:
            edge_polys.append((e, wps))
        else:
            src = geo.get(str(e.get("src_node") or ""))
            dst = geo.get(str(e.get("dst_node") or ""))
            if src and dst:
                edge_polys.append((e, [(src[0], src[1]), (dst[0], dst[1])]))
    for _e, poly in edge_polys:
        pts.extend(poly)
    lane_bands: list[tuple[float, float]] = []
    for lane in (lanes_row or {}).get("lanes") or []:
        if not isinstance(lane, dict):
            continue
        y0, y1 = _num(lane.get("y_min")), _num(lane.get("y_max"))
        if y0 is None or y1 is None:
            continue
        if y1 - y0 < 0.3:
            mid = (y0 + y1) / 2
            y0, y1 = mid - 0.15, mid + 0.15
        lane_bands.append((y0, y1))
    if lane_bands:
        xs = [p[0] for p in pts]
        for y0, y1 in lane_bands:
            pts.append((min(xs), y0))
            pts.append((max(xs), y1))
    minx = min(p[0] for p in pts)
    maxx = max(p[0] for p in pts)
    miny = min(p[1] for p in pts)
    maxy = max(p[1] for p in pts)
    pad = 0.35
    if maxx - minx < 1.0:
        mid = (minx + maxx) / 2
        minx, maxx = mid - 0.5, mid + 0.5
    if maxy - miny < 1.0:
        mid = (miny + maxy) / 2
        miny, maxy = mid - 0.5, mid + 0.5
    vb_x = minx - pad
    vb_y = -(maxy + pad)
    vb_w = (maxx - minx) + 2 * pad
    vb_h = (maxy - miny) + 2 * pad
    height = width * vb_h / vb_w
    height = min(max(height, 120.0), 560.0)
    stats: Counter[str] = Counter()

    fwd_id = f"arr-fwd-{seq}"
    bwd_id = f"arr-bwd-{seq}"
    parts = [
        f'<svg class="v2-svg" viewBox="{_fmt(vb_x)} {_fmt(vb_y)} {_fmt(vb_w)} {_fmt(vb_h)}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img">',
        "<defs>",
        f'<marker id="{fwd_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#334155"/></marker>',
        f'<marker id="{bwd_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" '
        f'markerHeight="6" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#7c2d12"/></marker>',
        "</defs>",
    ]
    # 泳道横带(背景, 交替底色+标签)
    for i, (y0, y1) in enumerate(lane_bands):
        fill = "#e8f2fd" if i % 2 == 0 else "#fdf6d8"
        parts.append(
            f'<rect class="v2-svg-lane" x="{_fmt(minx - pad)}" y="{_fmt(-y1)}" '
            f'width="{_fmt(maxx - minx + 2 * pad)}" height="{_fmt(y1 - y0)}" '
            f'fill="{fill}" stroke="#c9d4e0" stroke-width="0.02"/>'
        )
        parts.append(
            f'<text class="v2-svg-lanelabel" x="{_fmt(minx - pad + 0.05)}" '
            f'y="{_fmt(-y1 + 0.16)}" font-size="0.12" fill="#5c6b7a">泳道{i}</text>'
        )
        stats["lane_bands"] += 1
    # 循环/fork 节点集合
    loop_nodes: set[str] = set()
    fork_nodes: set[str] = set()
    if isinstance(graph_row, dict):
        for loop in graph_row.get("loops") or []:
            if isinstance(loop, dict):
                loop_nodes.update(str(n) for n in loop.get("cycle_nodes") or [])
                stats["loop_cycles"] += 1
        for fork in graph_row.get("forks") or []:
            if isinstance(fork, dict) and fork.get("node_id"):
                fork_nodes.add(str(fork["node_id"]))
        for join in graph_row.get("joins") or []:
            if isinstance(join, dict) and join.get("node_id"):
                fork_nodes.add(str(join["node_id"]))
    # 边(折线+箭头方向)
    for e, poly in edge_polys:
        label, glyph, cls, m_end, m_start = direction_style(e.get("direction_status"))
        points = " ".join(f"{_fmt(x)},{_fmt(-y)}" for x, y in poly)
        attrs = f' class="{cls}"'
        if str(e.get("line_pattern") or "") == "dashed":
            attrs += ' stroke-dasharray="0.14 0.08"'
        if m_end:
            attrs += f' marker-end="url(#{fwd_id})"'
        if m_start:
            attrs += f' marker-start="url(#{bwd_id})"'
        title = f"{label} {glyph} · {e.get('uml_type') or ''} · {e.get('via') or ''}"
        parts.append(
            f'<polyline points="{points}"{attrs}><title>{escape(title)}</title></polyline>'
        )
        stats["svg_edges"] += 1
        if m_end or m_start:
            stats["arrow_edges"] += 1
            if m_end and m_start:
                stats["arrow_bidirectional"] += 1
            elif m_end:
                stats["arrow_forward"] += 1
            else:
                stats["arrow_backward"] += 1
        else:
            stats["arrow_none"] += 1
        edge_label = str(e.get("label_raw") or "").strip()
        if edge_label:
            mx = (poly[0][0] + poly[-1][0]) / 2
            my = -(poly[0][1] + poly[-1][1]) / 2
            parts.append(
                f'<text class="v2-edge-label" x="{_fmt(mx)}" y="{_fmt(my - 0.08)}" '
                f'font-size="0.1">{escape(edge_label[:14])}</text>'
            )
    # 节点
    for n in nodes:
        nid = str(n.get("node_id") or "")
        g = geo.get(nid)
        if g is None:
            continue
        cx, cy, w, h = g
        ntype = str(n.get("type_candidate") or "other").strip().lower() or "other"
        fill, stroke = NODE_TYPE_STYLE.get(ntype, NODE_TYPE_FALLBACK)
        text = str(n.get("text_raw") or "")
        master = str(n.get("master_type") or "")
        via = "via_master" if n.get("via_master") else ""
        title = " · ".join(t for t in (text[:40], ntype, master, via) if t)
        parts.append('<g class="v2-svg-node">')
        parts.append(f"<title>{escape(title)}</title>")
        if w < 0.05 and h < 0.05:
            parts.append(
                f'<circle class="v2-svg-dot" cx="{_fmt(cx)}" cy="{_fmt(-cy)}" r="0.09" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="0.03"/>'
            )
        elif ntype == "boundary":
            parts.append(
                f'<rect class="v2-svg-rect" x="{_fmt(cx - w / 2)}" y="{_fmt(-(cy + h / 2))}" '
                f'width="{_fmt(w)}" height="{_fmt(h)}" rx="0.05" fill="none" '
                f'stroke="{stroke}" stroke-width="0.03" stroke-dasharray="0.12 0.06"/>'
            )
        else:
            parts.append(
                f'<rect class="v2-svg-rect" x="{_fmt(cx - w / 2)}" y="{_fmt(-(cy + h / 2))}" '
                f'width="{_fmt(w)}" height="{_fmt(h)}" rx="0.05" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="0.03"/>'
            )
        if w >= 0.35:
            per_line = max(4, int(w / 0.14))
            lines = _wrap_cjk(text, per_line=per_line, max_lines=3)
            font = 0.13
            line_h = 0.16
            ty = -cy - len(lines) * line_h / 2 + font * 0.8
            for ln in lines:
                parts.append(
                    f'<text class="v2-svg-node-text" x="{_fmt(cx)}" y="{_fmt(ty)}" '
                    f'font-size="{_fmt(font)}" text-anchor="middle" fill="#1a2332">'
                    + escape(ln)
                    + "</text>"
                )
                ty += line_h
        if master and h >= 0.25:
            parts.append(
                f'<text class="v2-svg-master" x="{_fmt(cx)}" y="{_fmt(-(cy - h / 2) + 0.12)}" '
                f'font-size="0.065" text-anchor="middle" fill="#94a3b8">'
                + escape(master[:18])
                + "</text>"
            )
        if nid in loop_nodes:
            r = max(w, h) / 2 + 0.13
            parts.append(
                f'<circle class="v2-svg-loop" cx="{_fmt(cx)}" cy="{_fmt(-cy)}" '
                f'r="{_fmt(r)}"/>'
            )
            stats["loop_marks"] += 1
        if nid in fork_nodes:
            sz = 0.11
            parts.append(
                f'<polygon class="v2-svg-fork" points="{_fmt(cx)},{_fmt(-cy - sz)} '
                f'{_fmt(cx + sz)},{_fmt(-cy)} {_fmt(cx)},{_fmt(-cy + sz)} '
                f'{_fmt(cx - sz)},{_fmt(-cy)}"/>'
            )
            stats["fork_marks"] += 1
        parts.append("</g>")
        stats["svg_nodes"] += 1
    parts.append("</svg>")
    stats["lane_diagrams"] = 1 if lane_bands else 0
    return "".join(parts), dict(stats)


# ------------------------------------------------------------ card builders


def quality_chips_html(quality: dict[str, Any]) -> str:
    chips: list[str] = []
    for key, label, inverted, process in QUALITY_METRICS:
        raw = quality.get(key)
        try:
            value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            value = None
        if value is None:
            chips.append(f'<span class="qchip r">{escape(label)}: —</span>')
            continue
        score = 1.0 - value if inverted else value
        cls = "g" if score > 0.66 else ("a" if score >= 0.33 else "r")
        if process:
            cls = f"{cls} proc"
            title = label + "（元指标：解析管线过程信号，非内容特征）"
        else:
            title = label
        suffix = "（反向：低=好）" if inverted else ""
        chips.append(
            f'<span class="qchip {cls}" title="{escape(title + suffix)}">'
            f"{escape(label)} {value * 100:.1f}%</span>"
        )
    return "".join(chips)


def ref_resolution_html(refs: list[dict[str, Any]]) -> str:
    if not refs:
        return ""
    parts = ['<div class="refhead">引用解析</div>']
    for r in refs:
        status = str(r.get("status") or "")
        target = str(r.get("target_id") or "")
        ok = status == "resolved"
        cls = "ok" if ok else "bad"
        text = (f"✓ {target[:28]}" if ok else f"✗ {status or 'unresolved'}")[:40]
        parts.append(
            f'<div class="refrow"><span class="refchip">{escape(str(r.get("ref") or ""))}</span>'
            f'<span class="res {cls}" title="target {escape(target)}">{escape(text)}</span>'
            "</div>"
        )
    return "".join(parts)


def claim_card_html_v2(
    sentence: dict[str, Any],
    claim: dict[str, Any] | None,
    entity_row: dict[str, Any] | None,
    refs: list[dict[str, Any]],
) -> str:
    cid = str(sentence.get("claim_id") or "")
    text = str(sentence.get("text") or "")
    shown = text if len(text) <= 160 else text[:160] + "…"
    span_status = str(sentence.get("span_status") or "")
    if span_status == "located":
        ps = '<span class="ps ok">located</span>'
    else:
        ps = f'<span class="ps bad">{escape(span_status or "unlocated")}</span>'
    badge = entity_badge_html(
        str((entity_row or {}).get("entity_type") or ""),
        str((entity_row or {}).get("basis") or "") or None,
    )
    pieces = [f'<div class="claimbox" id="clm-{escape(cid)}">']
    pieces.append(
        f'<div class="claimrow1"><code>{escape(cid)}</code>{ps}{badge}'
        f'<span class="secchip">{escape(str(sentence.get("section") or "—"))}</span></div>'
    )
    pieces.append(f'<div class="raw">{escape(shown)}</div>')
    if claim is not None:
        pieces.append('<dl class="five">')
        pairs = (
            ("主语", claim.get("subject_candidate")),
            ("谓词", claim.get("predicate_candidate") or None),
            ("算子", claim.get("operator") or None),
            ("值", claim.get("object_value") or None),
            ("单位", claim.get("unit_raw") or None),
        )
        for label, value in pairs:
            if value in (None, ""):
                pieces.append(
                    f'<dt class="fh-dt">{label}</dt>'
                    f'<dd class="fh-empty" title="该槽位为空：提取层未产出该字段">未提取</dd>'
                )
            else:
                pieces.append(f'<dt class="fh-dt">{label}</dt><dd>{escape(str(value))}</dd>')
        pieces.append("</dl>")
    else:
        pieces.append('<p class="muted">五元组未联接（v1 claim_slot_features 无该 claim_id）</p>')
    n_cond = len([c for c in sentence.get("conditions") or [] if isinstance(c, dict)])
    n_neg = len([n for n in sentence.get("negations") or [] if isinstance(n, dict)])
    scopes = [s for s in sentence.get("scope_entity") or [] if isinstance(s, dict)]
    chips: list[str] = []
    if n_cond:
        chips.append(f'<span class="v2cchip cond" title="条件短语">条件 {n_cond}</span>')
    if n_neg:
        chips.append(f'<span class="v2cchip neg" title="否定词">否定词 {n_neg}</span>')
    if scopes:
        chips.append(f'<span class="v2cchip scope" title="scope 实体">scope {len(scopes)}</span>')
    if sentence.get("has_condition"):
        chips.append('<span class="v2cchip cond">has_condition</span>')
    if chips:
        pieces.append('<div class="v2cchips">' + "".join(chips) + "</div>")
    for sc in scopes[:4]:
        pieces.append(
            '<div class="scoperow"><span class="scopetag">scope</span><code>'
            + escape(str(sc.get("raw") or sc.get("entity") or ""))
            + '</code><span class="muted">@'
            + str(sc.get("pos", "?"))
            + "</span></div>"
        )
    pieces.append(ref_resolution_html(refs))
    pieces.append("</div>")
    return "".join(pieces)


def table_card_html_v2(table_row: dict[str, Any]) -> str:
    cells = [c for c in table_row.get("cells") or [] if isinstance(c, dict)]
    if not cells:
        return '<p class="muted">tables_v2 无单元格数据</p>'
    tree = table_row.get("header_tree")
    lines = header_tree_lines(tree.get("nodes") if isinstance(tree, dict) else None)
    parts: list[str] = []
    if lines:
        parts.append('<div class="sphead">表头树文本结构</div><div class="v2-htree compact">')
        for depth, text, rs, cs in lines:
            meta = f" r{rs}×c{cs}" if (rs > 1 or cs > 1) else ""
            prefix = "└ " if depth else ""
            parts.append(
                '<div class="v2-htline" style="margin-left:'
                + str(depth * 16)
                + 'px">'
                + prefix
                + escape(text)
                + '<span class="v2-htmeta">'
                + meta
                + "</span></div>"
            )
        parts.append("</div>")
    else:
        parts.append('<p class="muted">无表头树（thead_rows=0）</p>')
    merged = [c for c in cells if c.get("is_merged_origin")]
    covered = sum(
        max(1, int(c.get("rowspan") or 1)) * max(1, int(c.get("colspan") or 1)) for c in merged
    )
    dist = table_empty_distribution(cells)
    n_cells = len(cells)
    empty_rate = (dist["empty"] + dist["dash"]) / n_cells if n_cells else 0.0
    parts.append('<dl class="tstats">')
    parts.append(f"<dt>表ID</dt><dd>{escape(str(table_row.get('table_id') or '—'))}</dd>")
    parts.append(
        f"<dt>规模</dt><dd>{table_row.get('n_rows', '—')}行 × "
        f"{table_row.get('n_cols', '—')}列 · {n_cells}格</dd>"
    )
    parts.append(f"<dt>合并单元格</dt><dd>{len(merged)} 个合并源(覆盖{covered}格)</dd>")
    parts.append(
        f"<dt>空值分布</dt><dd>空 {dist['empty']} · 占位 {dist['dash']} · "
        f"文本 {dist['text']}（空率 {empty_rate * 100:.1f}%）</dd>"
    )
    parts.append("</dl>")
    return "".join(parts)


def direction_chips_html(edges: list[dict[str, Any]]) -> str:
    counts: Counter[str] = Counter()
    for e in edges:
        label, _glyph, _cls, _me, _ms = direction_style(e.get("direction_status"))
        counts[label] += 1
    if not counts:
        return ""
    chips = []
    for label, glyph, cls in (
        ("forward", "→", "fwd"),
        ("backward", "←", "bwd"),
        ("bidirectional", "↔", "bi"),
        ("none", "—", "none"),
    ):
        if counts.get(label):
            chips.append(
                f'<span class="dchip {cls}" title="箭头方向 {label}">{glyph} '
                f"{counts[label]}</span>"
            )
    return '<div class="dchips">' + "".join(chips) + "</div>"


def image_card_html(
    caption: str,
    svg_html: str,
    svg_stats: dict[str, int],
    diagram_ref: str,
    edges: list[dict[str, Any]],
    align_counts: Counter[str],
    mismatch_note: str,
) -> str:
    parts: list[str] = [f'<div class="raw">{escape(caption or "（无caption）")}</div>']
    if diagram_ref:
        parts.append(
            '<div class="dgmeta"><span class="dchip ref" '
            'title="图↔Visio 顺序近似映射（多页OLE/重复嵌入时计数不一致）">'
            f"Visio {escape(diagram_ref)}</span>"
            f'<span class="muted">节点 {svg_stats.get("svg_nodes", 0)} · '
            f"边 {svg_stats.get("svg_edges", 0)}</span></div>"
        )
    if mismatch_note:
        parts.append(f'<span class="warn">⚠ {escape(mismatch_note)}</span>')
    if svg_html:
        parts.append(svg_html)
        parts.append(direction_chips_html(edges))
        loop_n = svg_stats.get("loop_marks", 0)
        lane_n = svg_stats.get("lane_bands", 0)
        fork_n = svg_stats.get("fork_marks", 0)
        if loop_n:
            parts.append(
                f'<span class="v2cchip loop" title="循环环路上的节点(红圈)">循环 {loop_n}</span>'
            )
        if fork_n:
            parts.append(
                f'<span class="v2cchip fork" title="fork/join 节点(菱形)">fork {fork_n}</span>'
            )
        if lane_n:
            parts.append(
                f'<span class="v2cchip lane" title="泳道横带(交替底色)">泳道带 {lane_n}</span>'
            )
        if align_counts:
            chips = []
            for status, (cls, label) in ALIGN_STATUS_META.items():
                n = align_counts.get(status, 0)
                if n:
                    chips.append(
                        f'<span class="achip v2 {cls}" title="{label}（锚点对齐）">'
                        f"{label} {n}</span>"
                    )
            if chips:
                parts.append('<div class="sphead">锚点对齐（本图节点）</div>' + "".join(chips))
    else:
        parts.append('<p class="muted">无对应 Visio 结构（节点几何缺失或未映射）</p>')
    return "".join(parts)


# ---------------------------------------------------------- top/bottom bars


def build_v2_stats_panel(
    entity_counts: Counter[str],
    align_counts: Counter[str],
    direction_counts: Counter[str],
    loop_diagrams: int,
    lane_diagrams: int,
    doc_entity: Counter[str],
    doc_align: Counter[str],
    doc_direction: Counter[str],
    doc_loops: int,
    doc_lanes: int,
) -> str:
    total_ent = sum(entity_counts.values()) or 1
    max_ent = max(entity_counts.values()) or 1

    def type_key(kv: tuple[str, int]) -> tuple[float, int]:
        rank = ENTITY_TYPE_ORDER.index(kv[0]) if kv[0] in ENTITY_TYPE_ORDER else 99
        return (-kv[1], rank)

    bars = []
    for etype, n in sorted(entity_counts.items(), key=type_key)[:8]:
        _cls, color = entity_badge_cls(etype)
        width = n / max_ent * 100
        title = f"{etype}: {n} / {total_ent}（{n / total_ent * 100:.1f}%）"
        bars.append(
            f'<div class="entbar" title="{escape(title)}"><span class="elab">'
            f"{escape(etype)}</span>"
            f'<div class="etrack"><i style="width:{width:.1f}%;background:{color}"></i></div>'
            f'<span class="enum">{n}</span></div>'
        )
    align_chips = []
    for status, (cls, label) in ALIGN_STATUS_META.items():
        n = align_counts.get(status, 0)
        align_chips.append(
            f'<span class="achip v2 {cls}" title="{label}（锚点对齐, 全数据集）">'
            f"{label} {n}</span>"
        )
    doc_align_chips = []
    for status, (cls, label) in ALIGN_STATUS_META.items():
        n = doc_align.get(status, 0)
        if n:
            doc_align_chips.append(f'<span class="achip v2 {cls}">{label} {n}</span>')
    dir_chips = []
    for label, glyph, cls in (
        ("forward", "→", "fwd"),
        ("backward", "←", "bwd"),
        ("bidirectional", "↔", "bi"),
        ("none", "—", "none"),
    ):
        n = direction_counts.get(label, 0)
        dir_chips.append(
            f'<span class="dchip {cls}" title="箭头方向 {label}（全数据集）">{glyph} {n}</span>'
        )
    doc_dir_chips = []
    for label, glyph, cls in (
        ("forward", "→", "fwd"),
        ("backward", "←", "bwd"),
        ("bidirectional", "↔", "bi"),
        ("none", "—", "none"),
    ):
        n = doc_direction.get(label, 0)
        if n:
            doc_dir_chips.append(f'<span class="dchip {cls}">{glyph} {n}</span>')
    doc_ent_chips = []
    for etype, n in sorted(doc_entity.items(), key=type_key)[:6]:
        doc_ent_chips.append(f'<span class="schip">{escape(etype)} {n}</span>')
    return (
        '<div id="v2stats"><div class="v2srow">'
        '<span class="v2stag">v2统计</span>'
        f'<div class="v2sblock"><span class="v2slabel">实体类型分布（全数据集 {total_ent}）</span>'
        f'<div class="entbars">{"".join(bars)}</div>'
        + (
            f'<span class="v2docsub">本文档: {"".join(doc_ent_chips)}</span>'
            if doc_ent_chips
            else ""
        )
        + "</div>"
        '<div class="v2sblock"><span class="v2slabel">三档锚点对齐</span>'
        + "".join(align_chips)
        + (
            f'<span class="v2docsub">本文档: {"".join(doc_align_chips)}</span>'
            if doc_align_chips
            else ""
        )
        + "</div>"
        '<div class="v2sblock"><span class="v2slabel">箭头方向分布</span>'
        + "".join(dir_chips)
        + (
            f'<span class="v2docsub">本文档: {"".join(doc_dir_chips)}</span>'
            if doc_dir_chips
            else ""
        )
        + "</div>"
        '<div class="v2sblock"><span class="v2slabel">结构信号</span>'
        f'<span class="schip" title="含循环环路的图（全数据集）">循环图 {loop_diagrams}</span>'
        f'<span class="schip" title="含泳道的图（全数据集）">泳道图 {lane_diagrams}</span>'
        f'<span class="v2docsub">本文档: 循环 {doc_loops} · 泳道 {doc_lanes}</span>'
        "</div></div></div>\n"
    )


def build_policy_bar(
    unit_completeness: float | None, usecase_rel_rows: list[dict[str, Any]]
) -> str:
    parts = ['<div id="policybar">']
    if unit_completeness is None:
        parts.append('<span class="pol a">单位完整率: —（quality_features 缺失）</span>')
    else:
        rate = max(0.0, min(1.0, unit_completeness))
        cls = "r" if rate < 0.30 else ("a" if rate < 0.60 else "g")
        warn = (
            '<span class="polwarn">质量弱点：数值提取普遍缺单位</span>' if rate < 0.30 else ""
        )
        parts.append(
            f'<span class="pol {cls}" title="unit_completeness（quality_features.jsonl）">'
            f"单位完整率 {rate * 100:.1f}%"
            f'<span class="poltrack"><i style="width:{rate * 100:.1f}%"></i></span>'
            f"{warn}</span>"
        )
    if usecase_rel_rows:
        kinds = {str(r.get("kind") or "") for r in usecase_rel_rows}
        all_unknown = bool(kinds) and kinds <= {"unknown", ""}
        cls = "r" if all_unknown else "a"
        kind_txt = "/".join(sorted(k for k in kinds if k)) or "unknown"
        parts.append(
            f'<span class="pol {cls}" title="usecase_relations.jsonl: include/extend 关系语义">'
            f"include/extend 关系判定: 全unknown（{len(usecase_rel_rows)}条, kind={kind_txt}）"
            '<span class="polwarn">UML include/extend 语义未解析</span></span>'
        )
    else:
        parts.append(
            '<span class="pol a" title="usecase_relations.jsonl 无关系行">'
            "include/extend 关系: 无数据（usecase_relations 为空）</span>"
        )
    parts.append("</div>\n")
    return "".join(parts)


# -------------------------------------------------------------- html build


def build_viewer(
    doc_id: str, section_default: str, max_images: int
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    doc_dir, office, content_path = find_doc_assets(doc_id)
    blocks = read_json(content_path)
    if not isinstance(blocks, list):
        raise ValueError(f"content_list 结构异常: {content_path}")
    doc_name = doc_dir.name

    # ---- v2 特征 + v1 五元组/质量
    sentences = read_jsonl(FEATURE_V2_DIR / "sentences.jsonl", doc_id)
    refs_rows = read_jsonl(FEATURE_V2_DIR / "references_resolved.jsonl", doc_id)
    tables_v2 = read_jsonl(FEATURE_V2_DIR / "tables_v2.jsonl", doc_id)
    v1_claims = read_jsonl(FEATURE_V1_DIR / "claim_slot_features.jsonl", doc_id)
    quality_rows = read_jsonl(FEATURE_V1_DIR / "quality_features.jsonl", doc_id)
    nodes_v2 = read_jsonl(VISIO_DIR / "visio_nodes_v2.jsonl", doc_id)
    edges_v2 = read_jsonl(VISIO_DIR / "visio_edges_v2.jsonl", doc_id)
    graph_rows = read_jsonl(SEMANTIC_DIR / "graph_structures.jsonl", doc_id)
    align_rows = read_jsonl(SEMANTIC_DIR / "alignment_status_v2.jsonl", doc_id)
    usecase_rel_rows = read_jsonl(SEMANTIC_DIR / "usecase_relations.jsonl")
    entity_all = read_jsonl(SEMANTIC_DIR / "entity_type_v2.jsonl")
    align_all = read_jsonl(SEMANTIC_DIR / "alignment_status_v2.jsonl")
    edges_all = read_jsonl(VISIO_DIR / "visio_edges_v2.jsonl")
    graph_all = read_jsonl(SEMANTIC_DIR / "graph_structures.jsonl")
    lanes_all = read_jsonl(SEMANTIC_DIR / "lanes.jsonl")

    refs_by_claim: dict[str, list[dict[str, Any]]] = {}
    for r in refs_rows:
        refs_by_claim.setdefault(str(r.get("claim_id") or ""), []).append(r)
    claim_by_id = {str(c.get("claim_id") or ""): c for c in v1_claims}
    entity_by_claim = {
        str(r.get("occurrence_id") or ""): r
        for r in entity_all
        if r.get("kind") == "claim" and str(r.get("doc_id") or "") == doc_id
    }

    # ---- Visio 图分组 + 文档序（corpus diagrams.jsonl, 缺失时按首现序）
    nodes_by_dg: dict[str, list[dict[str, Any]]] = {}
    for n in nodes_v2:
        nodes_by_dg.setdefault(str(n.get("diagram_id") or ""), []).append(n)
    edges_by_dg: dict[str, list[dict[str, Any]]] = {}
    for e in edges_v2:
        edges_by_dg.setdefault(str(e.get("diagram_id") or ""), []).append(e)
    first_seen: list[str] = []
    seen: set[str] = set()
    for dg in [str(n.get("diagram_id") or "") for n in nodes_v2] + [
        str(e.get("diagram_id") or "") for e in edges_v2
    ]:
        if dg and dg not in seen:
            seen.add(dg)
            first_seen.append(dg)
    corpus_diagrams = read_jsonl(CORPUS_DIR / "diagrams.jsonl", doc_id)
    corpus_order = [str(d.get("diagram_id") or "") for d in corpus_diagrams if d.get("diagram_id")]
    corpus_seen = set(corpus_order)
    diagram_order = [d for d in corpus_order if d in seen] + [
        d for d in first_seen if d not in corpus_seen
    ]
    lanes_by_dg = {str(lr.get("diagram_id") or ""): lr for lr in lanes_all}
    gs_by_dg = {str(g.get("diagram_id") or ""): g for g in graph_rows}
    node_to_dg = {
        str(n.get("node_id") or ""): str(n.get("diagram_id") or "") for n in nodes_v2
    }
    align_by_dg: Counter[tuple[str, str]] = Counter()
    for a in align_rows:
        dg = node_to_dg.get(str(a.get("node_id") or ""))
        if dg:
            align_by_dg[(dg, str(a.get("alignment_status_v2") or ""))] += 1

    # ---- 数据集级 / 文档级统计
    entity_counts = Counter(str(r.get("entity_type") or "未分类") for r in entity_all)
    doc_entity = Counter(
        str(r.get("entity_type") or "未分类")
        for r in entity_all
        if str(r.get("doc_id") or "") == doc_id
    )
    align_counts = Counter(str(r.get("alignment_status_v2") or "") for r in align_all)
    doc_align = Counter(str(r.get("alignment_status_v2") or "") for r in align_rows)
    direction_counts: Counter[str] = Counter()
    for e in edges_all:
        direction_counts[direction_style(e.get("direction_status"))[0]] += 1
    doc_direction: Counter[str] = Counter()
    for e in edges_v2:
        doc_direction[direction_style(e.get("direction_status"))[0]] += 1
    loop_diagrams_total = sum(1 for g in graph_all if g.get("has_loops"))
    lane_diagrams_total = sum(1 for lr in lanes_all if (lr.get("n_lanes") or 0) > 0)
    doc_loop_diagrams = sum(1 for g in graph_rows if g.get("has_loops"))
    doc_lane_diagrams = sum(
        1 for lr in lanes_all if lr.get("diagram_id") in seen and (lr.get("n_lanes") or 0) > 0
    )
    quality = quality_rows[0] if quality_rows else {}
    try:
        unit_completeness = (
            float(quality["unit_completeness"])
            if quality.get("unit_completeness") is not None
            else None
        )
    except (TypeError, ValueError):
        unit_completeness = None

    # ---- 遍历块: 章节归属 + 渲染清单 + 顺序索引
    sec = ""
    headings: list[tuple[str, str]] = []
    render_list: list[dict[str, Any]] = []
    table_count = 0
    image_count = 0
    for i, block in enumerate(blocks):
        if not isinstance(block, dict):
            continue
        btype = str(block.get("type") or "")
        if btype == "text" and block.get("text_level"):
            m = SECTION_HEADING_RE.match(str(block.get("text") or ""))
            if m:
                sec = m.group(1)
                headings.append((sec, str(block.get("text") or "").strip()))
        if btype not in RENDER_TYPES:
            continue
        entry = {"index": i, "block": block, "kind": btype, "sec": sec}
        if btype == "table":
            entry["tk"] = table_count
            table_count += 1
        elif btype == "image":
            entry["ik"] = image_count
            image_count += 1
        render_list.append(entry)
    headings = [(s, t) for s, t in headings if s.count(".") <= 1 or s == section_default]

    # ---- 图片嵌入优先级: 默认章节内的图先嵌, 其余按块序补足
    section_prefix = section_default if section_default not in ("", "all", "全部") else ""

    def in_default_section(s: str) -> bool:
        if not section_prefix:
            return True
        return s == section_prefix or s.startswith(section_prefix + ".")

    image_entries = [e for e in render_list if e["kind"] == "image"]
    ordered_images = sorted(
        image_entries, key=lambda e: (0 if in_default_section(e["sec"]) else 1, e["index"])
    )
    embedded_sources: dict[int, str] = {}
    for entry in ordered_images[: max(0, max_images)]:
        img_rel = str(entry["block"].get("img_path") or entry["block"].get("image_path") or "")
        img_path = office / img_rel
        if not img_path.exists():
            continue
        try:
            data = img_path.read_bytes()
        except OSError:
            continue
        suffix = img_path.suffix.lower().lstrip(".")
        mime = "image/jpeg" if suffix in ("jpg", "jpeg") else "image/png"
        encoded = base64.b64encode(data).decode("ascii")
        embedded_sources[entry["index"]] = f"data:{mime};base64,{encoded}"

    # ---- unit 数据 + sentence 定位
    unit_data: dict[int, list[dict[str, Any]]] = {}
    for entry in render_list:
        if entry["kind"] not in ("text", "list"):
            continue
        units = []
        for raw in build_units(entry["block"]):
            raw_san = sanitize_fragment(raw)
            plain, offsets = plain_with_offsets(raw_san)
            units.append({"raw": raw_san, "plain": plain, "offsets": offsets})
        unit_data[entry["index"]] = units
    block_sents, located_ids = locate_sentences(render_list, blocks, sentences, unit_data)

    # ---- 渲染左/右栏
    layer_stats: Counter[str] = Counter()
    left_parts: list[str] = []
    right_parts: list[str] = []
    table_mismatch = len(tables_v2) != table_count
    diagram_mismatch = len(diagram_order) != image_count
    svg_total = 0
    arrows_total = 0
    entity_badges = 0
    header_trees = 0
    coord_labels = 0
    merged_cells_total = 0

    unlocated = [s for s in sentences if str(s.get("claim_id") or "") not in located_ids]
    if unlocated:
        unloc_parts: list[str] = [
            '<div class="rcard" id="rc-unlocated" data-sec="">'
            '<div class="rchead"><span class="tbadge tb-text">TEXT</span>'
            "<span>块#—（span 未定位到原文块）</span>"
            '<span class="secchip">汇总</span></div><div class="rcbody">'
            f'<div class="clhead">未定位 claim（{len(unlocated)}，展示前30条）</div>'
        ]
        for s in unlocated[:30]:
            cid = str(s.get("claim_id") or "")
            unloc_parts.append(
                claim_card_html_v2(
                    s, claim_by_id.get(cid), entity_by_claim.get(cid), refs_by_claim.get(cid, [])
                )
            )
        unloc_parts.append("</div></div>")
        right_parts.append("".join(unloc_parts))

    for entry in render_list:
        i = entry["index"]
        block = entry["block"]
        kind = entry["kind"]
        sec_now = entry["sec"]
        left_parts.append(
            f'<div class="lblock" id="lb-{i}" data-bi="{i}" data-sec="{escape(sec_now)}">'
            f'<span class="ltag">#{i} · {escape(sec_now or "前言")}</span>'
        )
        right_parts.append(
            f'<div class="rcard" id="rc-{i}" data-bi="{i}" data-sec="{escape(sec_now)}">'
            '<div class="rchead"><span class="tbadge tb-'
            + kind
            + '">'
            + kind.upper()
            + "</span>"
            + f"<span>块#{i}</span>"
            + f'<span class="secchip">{escape(sec_now or "前言")}</span>'
            + '<button class="jump" title="在左栏定位">↖ 原文</button></div>'
            + '<div class="rcbody">'
        )

        if kind == "text":
            if block.get("text_level"):
                try:
                    level = max(1, min(6, int(block.get("text_level"))))
                except (TypeError, ValueError):
                    level = 3
                left_parts.append(
                    f'<div class="h h{level}">{escape(str(block.get("text") or ""))}</div>'
                )
            else:
                raw_san = sanitize_fragment(str(block.get("text") or ""))
                plain, offsets = plain_with_offsets(raw_san)
                ranges = regex_raw_ranges(plain, offsets)
                for att in block_sents.get(i, []):
                    ranges.extend(sentence_layer_ranges(att["sentence"], att))
                marked, chosen = render_segmented(raw_san, ranges)
                left_parts.append(f'<p class="para">{marked}</p>')
                for r in chosen:
                    layer_stats[r["cls"]] += 1
        elif kind == "list":
            items_html: list[str] = []
            for ui, raw in enumerate(build_units(block)):
                raw_san = sanitize_fragment(raw)
                plain, offsets = plain_with_offsets(raw_san)
                ranges = regex_raw_ranges(plain, offsets)
                for att in block_sents.get(i, []):
                    if att["ui"] != ui:
                        continue
                    ranges.extend(sentence_layer_ranges(att["sentence"], att))
                marked, chosen = render_segmented(raw_san, ranges)
                items_html.append(f"<li>{marked}</li>")
                for r in chosen:
                    layer_stats[r["cls"]] += 1
            left_parts.append('<ul class="lul">' + "".join(items_html) + "</ul>")
        elif kind == "table":
            tk = entry["tk"]
            trow = tables_v2[tk] if tk < len(tables_v2) else None
            cap = str((block.get("table_caption") or [""])[0] or "")
            left_parts.append(f'<div class="capbar">{escape(cap)}</div>')
            if trow is not None:
                htree = header_tree_html(trow.get("header_tree"))
                if htree:
                    left_parts.append(htree)
                    header_trees += 1
                body_html, tstats = build_table_html_v2(trow)
                left_parts.append(f'<div class="tblwrap">{body_html}</div>')
                coord_labels += tstats.get("coord_labels", 0)
                merged_cells_total += tstats.get("merged_origins", 0)
                entry["trow"] = trow
            else:
                left_parts.append(
                    '<div class="imgph">tables_v2 无对应行（顺序错位或缺失）</div>'
                )
        elif kind == "image":
            cap = str((block.get("image_caption") or [""])[0] or "")
            left_parts.append(f'<div class="capbar">{escape(cap)}</div>')
            src = embedded_sources.get(i)
            if src:
                left_parts.append(f'<img class="fmimg" src="{src}" alt="{escape(cap)}">')
            else:
                img_rel = str(block.get("img_path") or block.get("image_path") or "")
                left_parts.append(
                    '<div class="imgph">图片未嵌入（--max-images 限额或文件缺失）<br>'
                    f"<code>{escape(img_rel)}</code></div>"
                )

        # ---- 右栏卡片内容
        card_parts: list[str] = []
        if kind in ("text", "list"):
            atts = block_sents.get(i, [])
            if atts:
                card_parts.append(f'<div class="clhead">命中 claim（{len(atts)}）</div>')
                for att in atts:
                    sent = att["sentence"]
                    cid = str(sent.get("claim_id") or "")
                    if entity_by_claim.get(cid):
                        entity_badges += 1
                    card_parts.append(
                        claim_card_html_v2(
                            sent,
                            claim_by_id.get(cid),
                            entity_by_claim.get(cid),
                            refs_by_claim.get(cid, []),
                        )
                    )
            if not card_parts:
                card_parts.append('<p class="muted">（无命中 v2 语句特征）</p>')
        elif kind == "table":
            trow = entry.get("trow")
            if trow is None:
                card_parts.append('<p class="muted">无对应 tables_v2 行（顺序错位或缺失）</p>')
            else:
                card_parts.append(table_card_html_v2(trow))
            warns: list[str] = []
            if table_mismatch:
                warns.append(
                    f"计数警示: tables_v2 {len(tables_v2)} 条 ≠ 原文表块 {table_count} 个"
                )
            if trow is not None:
                cap_num = caption_number(block.get("table_caption"), "表")
                m = CAPTION_NUM_RE.match(str(trow.get("caption_raw") or ""))
                fcap_num = int(m.group(2)) if m and m.group(2).isdigit() else None
                if cap_num is not None and fcap_num is not None and cap_num != fcap_num:
                    warns.append(
                        f"caption 编号不一致: 原文表{cap_num} vs tables_v2表{fcap_num}"
                    )
            for w in warns:
                card_parts.append(f'<span class="warn">⚠ {escape(w)}</span>')
        elif kind == "image":
            ik = entry["ik"]
            mismatch_note = (
                f"图↔Visio计数不一致: Visio {len(diagram_order)} 张 vs 图片块 "
                f"{image_count} 个（顺序近似映射）"
                if diagram_mismatch
                else ""
            )
            cap = str((block.get("image_caption") or [""])[0] or "")
            if ik < len(diagram_order):
                dg = diagram_order[ik]
                svg_html, svg_stats = render_diagram_svg(
                    nodes_by_dg.get(dg, []),
                    edges_by_dg.get(dg, []),
                    lanes_by_dg.get(dg),
                    gs_by_dg.get(dg),
                    seq=ik,
                )
                if svg_html:
                    svg_total += 1
                arrows_total += svg_stats.get("arrow_edges", 0)
                layer_stats["loop_marks"] += svg_stats.get("loop_marks", 0)
                layer_stats["lane_bands"] += svg_stats.get("lane_bands", 0)
                layer_stats["fork_marks"] += svg_stats.get("fork_marks", 0)
                dg_align: Counter[str] = Counter()
                for status in ALIGN_STATUS_META:
                    dg_align[status] = align_by_dg.get((dg, status), 0)
                card_parts.append(
                    image_card_html(
                        cap,
                        svg_html,
                        svg_stats,
                        f"#{ik} {dg}",
                        edges_by_dg.get(dg, []),
                        dg_align,
                        mismatch_note if ik == 0 else "",
                    )
                )
            else:
                card_parts.append(
                    image_card_html(cap, "", {}, "", [], Counter(),
                                    mismatch_note if ik == 0 else "")
                )
        right_parts.append("".join(card_parts))
        right_parts.append("</div></div>")
        left_parts.append("</div>")

    # ---- 尾卡: 未对应图片块的 Visio 图
    extra_diagrams = diagram_order[image_count:]
    if extra_diagrams:
        extra_parts: list[str] = [
            '<div class="rcard" id="rc-extra-diagrams" data-sec="">'
            '<div class="rchead"><span class="tbadge tb-image">IMAGE</span>'
            f"<span>补充 · 未对应图片块的Visio图（{len(extra_diagrams)}张）</span>"
            '<span class="secchip">尾部</span></div><div class="rcbody">'
            "<p class=\"muted\">Visio 嵌入页数多于 MinerU 图片块（多页OLE/重复嵌入），"
            "以下图无一一对应图片块，按文档序追加。</p>"
        ]
        for j, dg in enumerate(extra_diagrams[:24]):
            svg_html, svg_stats = render_diagram_svg(
                nodes_by_dg.get(dg, []),
                edges_by_dg.get(dg, []),
                lanes_by_dg.get(dg),
                gs_by_dg.get(dg),
                seq=1000 + j,
            )
            if svg_html:
                svg_total += 1
            arrows_total += svg_stats.get("arrow_edges", 0)
            layer_stats["loop_marks"] += svg_stats.get("loop_marks", 0)
            layer_stats["lane_bands"] += svg_stats.get("lane_bands", 0)
            layer_stats["fork_marks"] += svg_stats.get("fork_marks", 0)
            extra_parts.append(
                '<div class="dgmeta"><span class="dchip ref">Visio 尾#'
                + str(j)
                + " "
                + escape(dg)
                + '</span><span class="muted">节点 '
                + str(svg_stats.get("svg_nodes", 0))
                + " · 边 "
                + str(svg_stats.get("svg_edges", 0))
                + "</span></div>"
            )
            if svg_html:
                extra_parts.append(svg_html)
        if len(extra_diagrams) > 24:
            extra_parts.append(
                f'<p class="muted">… 其余 {len(extra_diagrams) - 24} 张省略</p>'
            )
        extra_parts.append("</div></div>")
        right_parts.append("".join(extra_parts))

    # ---- 顶部: 章节过滤 + 质量信号 + v2统计 + 图例
    section_options: list[str] = ['<option value="all">全部章节</option>']
    heading_secs = {s for s, _ in headings}
    default_sel = section_default if section_default in heading_secs else "all"
    for s, title in headings:
        sel = " selected" if s == default_sel else ""
        section_options.append(
            f'<option value="{escape(s)}"{sel}>{escape((s + " " + title.strip())[:34])}</option>'
        )
    doc_options = f'<option value="{escape(doc_id)}" selected>{escape(doc_name[:26])}</option>'

    legend_items = "".join(
        f'<span><i style="background:{color}"></i>{escape(SPAN_LABELS[cls])}</span>'
        for cls, color in (
            ("fm-id", "#1d4ed8"),
            ("fm-num", "#c2410c"),
            ("fm-modal", "#7e22ce"),
            ("fm-neg", "#b91c1c"),
            ("fm-ref", "#0e7490"),
            ("v2-claim", "#bfd8f6"),
            ("v2-cond", "#f59e0b"),
        )
    )
    v2_legend = (
        '<span class="v2leg"><i class="leg-neg">否定词</i>'
        '<i class="leg-scope">scope实体</i>'
        '<i class="leg-lane"><b></b><b></b>泳道带</i>'
        '<i class="leg-loop">循环</i></span>'
    )

    stats = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "viewer": "v2",
        "blocks_total": len(blocks),
        "blocks_rendered": len(render_list),
        "cards": len(render_list),
        "sentences_total": len(sentences),
        "sentences_located": len(located_ids),
        "sentences_unlocated": len(sentences) - len(located_ids),
        "claims_joined_v1": sum(
            1 for s in sentences if str(s.get("claim_id") or "") in claim_by_id
        ),
        "entity_badges": entity_badges,
        "layer_highlights": dict(sorted(layer_stats.items())),
        "cond_highlights": layer_stats.get("v2-cond", 0),
        "neg_word_highlights": layer_stats.get("v2-neg", 0),
        "scope_highlights": layer_stats.get("v2-scope", 0),
        "claim_spans": layer_stats.get("v2-claim", 0),
        "svg_diagrams": svg_total,
        "svg_arrows": arrows_total,
        "header_trees": header_trees,
        "coord_labels": coord_labels,
        "merged_cells": merged_cells_total,
        "lane_bands": layer_stats.get("lane_bands", 0),
        "loop_marks": layer_stats.get("loop_marks", 0),
        "fork_marks": layer_stats.get("fork_marks", 0),
        "refs_rows": len(refs_rows),
        "refs_resolved": sum(1 for r in refs_rows if r.get("status") == "resolved"),
        "tables_v2_count": len(tables_v2),
        "table_block_count": table_count,
        "diagram_count": len(diagram_order),
        "image_block_count": image_count,
        "extra_diagrams": len(extra_diagrams),
        "images_embedded": len(embedded_sources),
        "doc_loop_diagrams": doc_loop_diagrams,
        "doc_lane_diagrams": doc_lane_diagrams,
        "dataset_loop_diagrams": loop_diagrams_total,
        "dataset_lane_diagrams": lane_diagrams_total,
        "dataset_entity_types": dict(entity_counts),
        "dataset_alignment": dict(align_counts),
        "dataset_arrow_directions": dict(direction_counts),
        "section_default": default_sel,
        "unit_completeness": unit_completeness,
    }
    payload = {
        "meta": {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "content_path": str(content_path),
            "section_default": default_sel,
            "max_images": max_images,
            "viewer": "v2",
        },
        "stats": {
            "sentences_located": len(located_ids),
            "svg_diagrams": svg_total,
            "svg_arrows": arrows_total,
            "entity_badges": entity_badges,
            "header_trees": header_trees,
            "layer_highlights": dict(layer_stats),
            "lane_bands": layer_stats.get("lane_bands", 0),
            "loop_marks": layer_stats.get("loop_marks", 0),
        },
        "dataset": {
            "entity_types": dict(entity_counts),
            "alignment": dict(align_counts),
            "arrow_directions": dict(direction_counts),
            "loop_diagrams": loop_diagrams_total,
            "lane_diagrams": lane_diagrams_total,
        },
        "sections": [{"sec": s, "title": t} for s, t in headings],
    }

    html_doc = assemble_html(
        doc_id=doc_id,
        doc_name=doc_name,
        doc_options=doc_options,
        section_options="".join(section_options),
        quality_chips=quality_chips_html(quality),
        legend=legend_items,
        v2_legend=v2_legend,
        v2_stats_panel=build_v2_stats_panel(
            entity_counts,
            align_counts,
            direction_counts,
            loop_diagrams_total,
            lane_diagrams_total,
            doc_entity,
            doc_align,
            doc_direction,
            doc_loop_diagrams,
            doc_lane_diagrams,
        ),
        policy_bar=build_policy_bar(unit_completeness, usecase_rel_rows),
        left_html="".join(left_parts),
        right_html="".join(right_parts),
        payload=payload,
    )
    return html_doc, stats, payload


CSS_TEXT = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; height: 100%; }
body { display: flex; flex-direction: column; overflow: hidden; background: #eef1f6;
  color: #1a2332; font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", system-ui,
  sans-serif; font-size: 13.5px; }
#topbar { background: #fff; border-bottom: 1px solid #dde3ec; padding: 8px 14px 6px; flex: none; }
.tbrow { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.title { font-size: 15.5px; font-weight: 700; }
.docname { color: #5c6b7a; font-size: 12px; }
#topbar label { font-size: 12px; color: #5c6b7a; display: flex; align-items: center; gap: 6px; }
select { font: inherit; padding: 3px 8px; border: 1px solid #cdd6e0; border-radius: 6px;
  background: #fff; max-width: 330px; }
.qchips { display: flex; gap: 6px; flex-wrap: wrap; }
.qchip { font-size: 11px; padding: 2px 9px; border-radius: 999px; white-space: nowrap; }
.qchip.g { background: #e3f2e6; color: #256b2c; }
.qchip.a { background: #fdf3d7; color: #8a6a00; }
.qchip.r { background: #fde3e5; color: #b02a36; }
.qchip.proc { background: #eef2f7; color: #8a94a3; font-size: 10px; font-weight: 400;
  border: 1px dashed #d4dce6; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11px; color: #5c6b7a;
  margin-top: 6px; align-items: center; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
  margin-right: 4px; vertical-align: -1px; }
.v2leg { display: flex; gap: 10px; align-items: center; }
.v2leg i { width: auto; height: auto; border-radius: 3px; padding: 0 6px; font-style: normal;
  font-size: 10.5px; }
.v2leg .leg-neg { text-decoration: underline; text-decoration-color: #dc2626;
  text-decoration-thickness: 2px; text-underline-offset: 3px; color: #b02a36; }
.v2leg .leg-scope { border: 1.5px dashed #9333ea; color: #7e22ce; }
.v2leg .leg-lane { display: inline-flex; flex-direction: column; gap: 1px; padding: 0; }
.v2leg .leg-lane b { display: block; width: 26px; height: 5px; }
.v2leg .leg-lane b:first-child { background: #e8f2fd; border: 1px solid #c9d4e0; }
.v2leg .leg-lane b:last-child { background: #fdf6d8; border: 1px solid #c9d4e0; }
.v2leg .leg-loop { border: 2px solid #dc2626; border-radius: 50%; color: #b02a36; }
#v2stats { margin-top: 6px; border: 1px solid #e1e6ee; border-radius: 8px; background: #f8fafd;
  padding: 5px 10px; }
.v2srow { display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-start; font-size: 11.5px; }
.v2stag { font-weight: 700; color: #0f766e; background: #ccfbf1; padding: 1px 8px;
  border-radius: 4px; white-space: nowrap; }
.v2sblock { display: flex; flex-direction: column; gap: 3px; }
.v2slabel { color: #33404d; font-weight: 600; font-size: 11px; }
.v2docsub { color: #8a94a3; font-size: 10.5px; display: flex; gap: 4px; flex-wrap: wrap; }
.entbars { display: flex; flex-direction: column; gap: 2px; min-width: 280px; }
.entbar { display: flex; align-items: center; gap: 6px; font-size: 10.5px; }
.entbar .elab { width: 46px; text-align: right; color: #33404d; white-space: nowrap; }
.entbar .etrack { flex: 1; height: 9px; background: #edf1f5; border-radius: 3px; overflow: hidden;
  min-width: 120px; }
.entbar .etrack i { display: block; height: 100%; }
.entbar .enum { color: #5c6b7a; font-variant-numeric: tabular-nums; }
.achip.v2 { font-size: 10.5px; padding: 1px 9px; border-radius: 999px; display: inline-block;
  margin: 1px 4px 0 0; }
.achip.v2.g { background: #e3f2e6; color: #256b2c; }
.achip.v2.a { background: #fdf3d7; color: #8a6a00; }
.achip.v2.r { background: #fde3e5; color: #b02a36; }
.schip { font-size: 10.5px; padding: 1px 7px; border-radius: 4px; background: #e3f2e6;
  color: #256b2c; font-variant-numeric: tabular-nums; }
.dchip { font-size: 10.5px; padding: 1px 8px; border-radius: 999px; display: inline-block;
  margin: 1px 4px 0 0; white-space: nowrap; }
.dchip.fwd { background: #e3f2e6; color: #256b2c; }
.dchip.bwd { background: #fde3e5; color: #b02a36; }
.dchip.bi { background: #dbeafe; color: #1d4ed8; }
.dchip.none { background: #eef2f7; color: #8a94a3; }
.dchip.ref { background: #ede9fe; color: #6d28d9; font-family: Consolas, monospace;
  font-size: 10px; }
#notice { display: none; margin-top: 6px; padding: 5px 10px; border-radius: 6px;
  background: #fdf3d7; color: #8a6a00; font-size: 12px; }
#main { flex: 1; display: flex; min-height: 0; }
.col { display: flex; flex-direction: column; min-height: 0; min-width: 0; }
.leftcol { width: 55%; background: #fff; border-right: 1px solid #dde3ec; }
.rightcol { width: 45%; }
.panehead { flex: none; padding: 5px 14px; font-size: 11px; color: #5c6b7a;
  background: #f5f7fa; border-bottom: 1px solid #e5eaf1; }
#leftPane, #rightPane { flex: 1; overflow-y: auto; padding: 12px 16px 48px; }
.lblock { position: relative; margin: 0 0 14px; border-radius: 4px; }
.lblock.active { background: #f2f7ff; }
.ltag { position: absolute; top: -2px; right: 2px; font-size: 10px; color: #a6b0bd;
  opacity: 0; transition: opacity 0.2s; background: rgba(255,255,255,0.85); padding: 0 4px; }
.lblock:hover .ltag { opacity: 1; }
.h { font-weight: 700; margin: 12px 0 4px; color: #141d2b; }
.h1 { font-size: 16.5px; } .h2 { font-size: 15.5px; } .h3 { font-size: 14.5px; margin-left: 18px; }
.h4 { font-size: 14px; margin-left: 36px; } .h5 { font-size: 13.5px; margin-left: 54px; }
.h6 { font-size: 13.5px; margin-left: 72px; }
.para { margin: 5px 0; line-height: 1.85; text-align: justify; }
.lul { margin: 4px 0 4px 8px; padding-left: 18px; }
.lul li { margin: 3px 0; line-height: 1.75; }
mark { padding: 0 2px; border-radius: 3px; cursor: pointer; }
mark.v2-claim { background: #eff6ff; color: inherit; }
mark.fm-id { background: #dbeafe; color: #1d4ed8; }
mark.fm-num { background: #ffedd5; color: #c2410c; }
mark.fm-modal { background: #f3e8ff; color: #7e22ce; }
mark.fm-neg { background: #fee2e2; color: #b91c1c; }
mark.fm-ref { background: #cffafe; color: #0e7490; }
mark.v2-cond { background: #ffedd5; border: 1px solid #f59e0b; }
mark.v2-neg { text-decoration: underline; text-decoration-color: #dc2626;
  text-decoration-thickness: 2px; text-underline-offset: 3px; }
mark.v2-scope { border: 1.5px dashed #9333ea; border-radius: 3px; }
.capbar { font-weight: 600; font-size: 12px; color: #33404d; margin: 10px 0 5px; }
.v2-htree { border: 1px solid #e1e6ee; background: #f8fafd; border-radius: 6px;
  padding: 6px 10px; margin: 4px 0 6px; font-size: 11px; }
.v2-htree.compact { margin: 4px 0; }
.v2-hthead { font-weight: 700; color: #33404d; margin-bottom: 2px; }
.v2-htline { line-height: 1.7; color: #33404d; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.v2-htmeta { color: #8a94a3; font-size: 10px; margin-left: 6px; }
.tblwrap { overflow-x: auto; }
table.v2tbl { border-collapse: collapse; width: 100%; font-size: 12px; background: #fff; }
.v2tbl td { border: 1px solid #d5dbe3; padding: 4px 8px 4px 20px; vertical-align: top;
  line-height: 1.6; position: relative; }
td.v2-merged { outline: 2px solid #e53935; outline-offset: -2px; }
td.v2-empty-cell { background: #eceff1; }
td.v2-gap { background: #f8fafd; }
.v2-cc { position: absolute; top: 1px; left: 2px; font-size: 8.5px; color: #a6b0bd;
  font-family: Consolas, "Courier New", monospace; pointer-events: none; }
.fmimg { max-width: 100%; border: 1px solid #d5dbe3; border-radius: 4px; display: block; }
.imgph { border: 1.5px dashed #b7c2cf; color: #7d8896; padding: 18px 10px; text-align: center;
  border-radius: 6px; font-size: 12px; }
.imgph code { font-family: Consolas, "Courier New", monospace; font-size: 11px; }
svg.v2-svg { border: 1px solid #d5dbe3; border-radius: 6px; background: #fff; display: block;
  max-width: 100%; margin: 6px 0; }
.v2-svg-lane { opacity: 0.6; }
.v2-svg-loop { fill: none; stroke: #dc2626; stroke-width: 0.05; }
.v2-svg-fork { fill: #f59e0b; stroke: #b45309; stroke-width: 0.02; }
.v2-svg-master { fill: #94a3b8; }
.v2-edge-label { fill: #64748b; }
polyline.v2-edge-forward { stroke: #334155; stroke-width: 0.045; fill: none; }
polyline.v2-edge-backward { stroke: #7c2d12; stroke-width: 0.045; fill: none; }
polyline.v2-edge-bidirectional { stroke: #1d4ed8; stroke-width: 0.045; fill: none; }
polyline.v2-edge-none { stroke: #9aa4b2; stroke-width: 0.035; fill: none; }
.rcard { background: #fff; border: 1px solid #e1e6ee; border-radius: 9px; margin-bottom: 10px; }
.rcard.active { border-color: #2f6fed; box-shadow: 0 0 0 1.5px rgba(47, 111, 237, 0.3); }
.rchead { display: flex; align-items: center; gap: 8px; font-size: 11px; background: #f0f3f8;
  border-bottom: 1px solid #e7ecf3; border-radius: 9px 9px 0 0; padding: 4px 10px; color: #5c6b7a; }
.tbadge { font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 4px;
  letter-spacing: 0.5px; }
.tb-text { background: #dbeafe; color: #1d4ed8; } .tb-list { background: #e0e7ff; color: #4338ca; }
.tb-table { background: #dcfce7; color: #15803d; } .tb-image { background: #f3e8ff; color: #7e22ce; }
.secchip { background: #eef2f7; padding: 1px 7px; border-radius: 999px; }
.jump { margin-left: auto; background: none; border: 1px solid #cdd6e0; border-radius: 5px;
  padding: 1px 8px; cursor: pointer; font-size: 10.5px; color: #5c6b7a; }
.jump:hover { background: #eef2f7; }
.rcbody { padding: 8px 12px; }
.claimbox { border: 1px solid #e7ecf3; border-radius: 7px; padding: 7px 10px; margin: 6px 0;
  background: #fbfcfe; }
.claimbox.flash { border-color: #2f6fed; box-shadow: 0 0 0 2px rgba(47, 111, 237, 0.25); }
.claimrow1 { display: flex; gap: 8px; align-items: center; font-size: 11px; color: #5c6b7a;
  flex-wrap: wrap; }
.claimrow1 code { font-size: 10.5px; background: #eef2f7; padding: 1px 5px; border-radius: 4px; }
.ps { font-size: 10px; padding: 1px 7px; border-radius: 999px; }
.ps.ok { background: #e3f2e6; color: #256b2c; }
.ps.bad { background: #fde3e5; color: #b02a36; }
.ebadge { font-size: 10px; font-weight: 700; padding: 1px 8px; border-radius: 999px;
  white-space: nowrap; }
.ebadge.et-iface { background: #dbeafe; color: #1d4ed8; }
.ebadge.et-module { background: #cffafe; color: #0e7490; }
.ebadge.et-func { background: #dcfce7; color: #15803d; }
.ebadge.et-param { background: #ffedd5; color: #c2410c; }
.ebadge.et-data { background: #f3e8ff; color: #7e22ce; }
.ebadge.et-sys { background: #f5e9dc; color: #92400e; }
.ebadge.et-other { background: #eef2f7; color: #5c6b7a; }
.raw { font-size: 12px; margin: 4px 0; line-height: 1.7; color: #1a2332; }
.five { display: grid; grid-template-columns: 56px 1fr 56px 1fr; gap: 2px 8px;
  font-size: 11.5px; margin: 4px 0; }
.five dt { color: #8a94a3; } .five dd { margin: 0; color: #1a2332; word-break: break-all; }
.five dt.fh-dt { color: #5c6b7a; }
dd.fh-empty { color: #8a94a3; font-style: italic; }
.v2cchips { display: flex; gap: 6px; flex-wrap: wrap; margin: 3px 0; }
.v2cchip { font-size: 10.5px; padding: 1px 8px; border-radius: 999px; }
.v2cchip.cond { background: #ffedd5; color: #b45309; }
.v2cchip.neg { background: #fee2e2; color: #b91c1c; }
.v2cchip.scope { background: #f3e8ff; color: #7e22ce; }
.v2cchip.loop { background: #fde3e5; color: #b02a36; }
.v2cchip.fork { background: #fef3c7; color: #b45309; }
.v2cchip.lane { background: #dbeafe; color: #1e40af; }
.scoperow { display: flex; align-items: center; gap: 7px; font-size: 11.5px; margin: 2px 0; }
.scopetag { font-size: 10px; background: #f3e8ff; color: #7e22ce; border-radius: 4px;
  padding: 0 6px; }
.scoperow code { font-family: Consolas, "Courier New", monospace; font-size: 11px; }
.refrow { display: flex; align-items: center; gap: 7px; font-size: 11.5px; margin: 3px 0; }
.refchip { background: #cffafe; color: #0e7490; border-radius: 4px; padding: 1px 7px;
  font-size: 10.5px; }
.res { font-size: 10.5px; padding: 1px 7px; border-radius: 4px; }
.res.ok { background: #e3f2e6; color: #256b2c; }
.res.bad { background: #fde3e5; color: #b02a36; }
.refhead, .clhead, .sphead { font-size: 11px; font-weight: 700; color: #5c6b7a;
  margin: 8px 0 4px; }
.dchips { display: flex; gap: 4px; flex-wrap: wrap; margin: 3px 0; }
.dgmeta { display: flex; gap: 8px; align-items: center; margin: 4px 0; flex-wrap: wrap; }
.tstats { display: grid; grid-template-columns: 76px 1fr 76px 1fr; gap: 2px 8px;
  font-size: 11.5px; margin: 2px 0; }
.tstats dt { color: #8a94a3; } .tstats dd { margin: 0; word-break: break-all; }
.muted { color: #8a94a3; font-size: 11.5px; font-style: italic; margin: 4px 0; }
.warn { display: inline-block; font-size: 10.5px; color: #8a6a00; background: #fdf3d7;
  border-radius: 5px; padding: 2px 8px; margin: 3px 4px 0 0; }
#policybar { flex: none; background: #fff; border-top: 1px solid #dde3ec; padding: 7px 16px;
  display: flex; gap: 16px; align-items: center; flex-wrap: wrap; font-size: 12px;
  color: #33404d; }
.pol { display: flex; align-items: center; gap: 7px; padding: 3px 10px; border-radius: 6px; }
.pol.r { background: #fde3e5; color: #b02a36; }
.pol.a { background: #fdf3d7; color: #8a6a00; }
.pol.g { background: #e3f2e6; color: #256b2c; }
.poltrack { width: 110px; height: 8px; background: #f5d7da; border-radius: 4px; overflow: hidden; }
.poltrack i { display: block; height: 100%; background: #dc2626; }
.polwarn { font-size: 10px; opacity: 0.85; }
"""


def assemble_html(
    doc_id: str,
    doc_name: str,
    doc_options: str,
    section_options: str,
    quality_chips: str,
    legend: str,
    v2_legend: str,
    v2_stats_panel: str,
    policy_bar: str,
    left_html: str,
    right_html: str,
    payload: dict[str, Any],
) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>SRS 对照视图 v2 · {escape(doc_id)} {escape(doc_name[:30])}</title>\n"
        f"<style>{CSS_TEXT}</style>\n</head>\n<body>\n"
        '<div id="topbar">\n'
        '<div class="tbrow"><span class="title">SRS 对照视图 v2'
        "（原文 ↔ feature_matrix_v2 / visio_features_v2 / semantic_features_v2）"
        '</span><span class="docname">'
        + escape(doc_name)
        + "</span></div>\n"
        '<div class="tbrow"><label>文档 <select id="docsel">'
        + doc_options
        + '</select></label>\n'
        '<label>章节 <select id="secsel">'
        + section_options
        + "</select></label>\n"
        '<div class="qchips">'
        + quality_chips
        + "</div></div>\n"
        '<div class="legend"><b>span 图例：</b>'
        + legend
        + v2_legend
        + "<span>（点击左侧 mark 可在右栏定位 claim 卡）</span></div>\n"
        + v2_stats_panel
        + '<div id="notice"></div>\n</div>\n'
        '<div id="main">\n'
        '<div class="col leftcol"><div class="panehead">左侧 · 原文（MinerU content_list 顺序'
        "渲染：标题/段落/列表/表格/图片 · v2层: claim淡蓝/条件橙/否定红下划线/scope紫虚线）</div>"
        f'<div id="leftPane">{left_html}</div></div>\n'
        '<div class="col rightcol"><div class="panehead">右侧 · v2 提取结果'
        "（五元组+实体badge+引用解析 / 表头树+合并统计 / Visio SVG 简绘图）</div>"
        f'<div id="rightPane">{right_html}</div></div>\n'
        "</div>\n"
        + policy_bar
        + '<script type="application/json" id="fm-data">'
        + payload_json
        + "</script>\n"
        + "<script>"
        + JS_TEXT.replace("__DOC__", escape(doc_id))
        + "</script>\n</body>\n</html>\n"
    )


JS_TEXT = """
(function () {
"use strict";
var DOC = "__DOC__";
var leftPane = document.getElementById("leftPane");
var rightPane = document.getElementById("rightPane");
var secsel = document.getElementById("secsel");
var docsel = document.getElementById("docsel");
var noticeEl = document.getElementById("notice");
var noticeTimer = null;
var lock = 0;

function notice(msg) {
  noticeEl.textContent = msg;
  noticeEl.style.display = "block";
  if (noticeTimer) { window.clearTimeout(noticeTimer); }
  noticeTimer = window.setTimeout(function () { noticeEl.style.display = "none"; }, 8000);
}
function visible(el) {
  return el.style.display !== "none";
}
function applySection() {
  var v = secsel.value;
  var els = document.querySelectorAll("[data-sec]");
  for (var i = 0; i < els.length; i++) {
    var s = els[i].getAttribute("data-sec") || "";
    var show = v === "all" || s === v || s.indexOf(v + ".") === 0;
    els[i].style.display = show ? "" : "none";
  }
}
function setActive(bi) {
  var blocks = document.querySelectorAll(".lblock.active, .rcard.active");
  for (var i = 0; i < blocks.length; i++) { blocks[i].classList.remove("active"); }
  var lb = document.getElementById("lb-" + bi);
  var rc = document.getElementById("rc-" + bi);
  if (lb) { lb.classList.add("active"); }
  if (rc) { rc.classList.add("active"); }
}
function scrollToCard(bi) {
  var card = document.getElementById("rc-" + bi);
  if (!card || !visible(card)) { return; }
  lock = Date.now() + 250;
  card.scrollIntoView({ block: "start" });
  setActive(bi);
}
function scrollToBlock(bi) {
  var block = document.getElementById("lb-" + bi);
  if (!block || !visible(block)) { return; }
  lock = Date.now() + 250;
  block.scrollIntoView({ block: "start" });
  setActive(bi);
}
document.addEventListener("click", function (ev) {
  var mk = ev.target.closest ? ev.target.closest("mark") : null;
  if (mk && leftPane.contains(mk)) {
    var claim = mk.getAttribute("data-claim");
    if (claim) {
      var card = document.getElementById("clm-" + claim);
      if (card && visible(card)) {
        lock = Date.now() + 250;
        card.scrollIntoView({ block: "center" });
        card.classList.add("flash");
        window.setTimeout(function () { card.classList.remove("flash"); }, 1200);
        return;
      }
    }
    var bi = mk.closest(".lblock") ? mk.closest(".lblock").getAttribute("data-bi") : null;
    if (bi !== null) { scrollToCard(bi); }
    return;
  }
  var jump = ev.target.closest ? ev.target.closest(".jump") : null;
  if (jump) {
    var rcard = jump.closest(".rcard");
    if (rcard) { scrollToBlock(rcard.getAttribute("data-bi")); }
  }
});
secsel.onchange = applySection;
docsel.onchange = function () {
  var v = docsel.value;
  notice("本页仅内嵌 " + DOC + " 的数据。生成 " + v + " 视图请运行: " +
    "python tools/render_side_by_side_viewer_v2.py --doc " + v);
  docsel.value = DOC;
};
if ("IntersectionObserver" in window) {
  var io = new IntersectionObserver(function (entries) {
    if (Date.now() < lock) { return; }
    var best = null;
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!e.isIntersecting) { continue; }
      if (!best || e.intersectionRatio > best.intersectionRatio) { best = e; }
    }
    if (best) {
      var bi = best.target.getAttribute("data-bi");
      if (bi !== null && String(bi) !== "null") { scrollToCard(String(bi)); }
    }
  }, { root: leftPane, threshold: [0, 0.15, 0.5] });
  var lbs = document.querySelectorAll(".lblock");
  for (var j = 0; j < lbs.length; j++) { io.observe(lbs[j]); }
}
applySection();
})();
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render side-by-side v2 (原文/v2特征) self-contained HTML viewer"
    )
    parser.add_argument("--doc", default="04", help="doc id, e.g. 04 (default: 04)")
    parser.add_argument(
        "--output", type=Path, default=None, help="output HTML path (default: feature_matrix_v1)"
    )
    parser.add_argument(
        "--section", default="3.2", help="default section filter (e.g. 3.2; 'all' = 全部)"
    )
    parser.add_argument(
        "--max-images", type=int, default=20, help="max base64-embedded images (default: 20)"
    )
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    doc_id = args.doc.strip()
    output = args.output or Path(str(DEFAULT_OUTPUT).replace("{doc}", doc_id))
    output = output if output.is_absolute() else BASE / output
    html_doc, stats, _payload = build_viewer(doc_id, args.section, args.max_images)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(html_doc)
    stats["output"] = str(output)
    stats["output_bytes"] = output.stat().st_size if output.exists() else 0
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
