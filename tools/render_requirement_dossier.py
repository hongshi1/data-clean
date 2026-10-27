#!/usr/bin/env python3
"""GJB需求条目档案视图(dossier)渲染器: 一份自包含HTML呈现单个需求的六路证据.

设计原则(主视觉=原始文档内容, 提取特征只作侧栏注脚):
- 左侧25%需求树: content_list 的 text_level 标题按正则解析(编号+名称+括号ID),
  叶子节点(无子需求)可点击切换档案
- 右侧75%档案页: 选中叶子 → 从该节标题到下一同级/上级标题之间的所有块, 按原文
  顺序渲染: ①正文段落(原样黑字, 无高亮) ②表格(table_body原HTML, 保留合并单元格)
  ③图片(原图base64); 每个片段右侧小字灰色客观计数注脚(查不到显示"—")
- 上下游条目区(档案页底部):
  上游 = 父节点标题 + 能力标识表(caption含"能力")中含本需求ID的行(渲染原行)
  合格性 = 第4章合格性表("本文档的章节号"列==本需求编号的行, 渲染原行)
  追溯   = 第5章追溯表(caption含"追踪/跟踪"或第5章区间内)含本需求编号/名称的行
  行匹配用 ID/编号/名称 三重匹配(ID优先); 直接行缺失时回退渲染最近上级行并明确标注
- 顶部: doc选择器 + 当前需求ID面包屑 + 六路证据齐全度指示器(✓/✗)

数据源:
- 原文: data/gjb_438c/mineru_standard/<doc>/office/<doc>_content_list.json(唯一主要来源)
- 图片: office/images/*.png → base64
- 侧栏注脚: feature_matrix_v1/{table,text}_features.jsonl + visio_features_v2(可选增强)

Usage:
  python tools/render_requirement_dossier.py [--doc 04] [--output PATH]
  默认输出 data/gjb_438c/requirement_dossier_04.html
"""
from __future__ import annotations

import argparse
import base64
import html as html_mod
import json
import re
import sys
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
MINERU_STANDARD = BASE / "data/gjb_438c/mineru_standard"
FEATURE_V1_DIR = BASE / "data/gjb_438c/feature_matrix_v1"
VISIO_V2_DIR = BASE / "data/gjb_438c/visio_features_v2"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/requirement_dossier_{doc}.html"

# 需求树标题解析: 编号 + 名称 + 括号内ID(严格版, ID内无空格)
REQ_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+?)[（(](\s*[A-Z0-9\-]+)\s*[)）]\s*$")
# 宽松版: 容忍ID内部空格/全角破折号(如 "PZXQ-GN-X- BLOBSJXG" / "…–GJWLZY-ZJML")
REQ_HEADING_LOOSE_RE = re.compile(
    r"^(\d+(?:\.\d+)+)\s+(.+?)[（(](\s*[A-Z][A-Z0-9\-–— ]*[A-Z0-9\-–—])\s*[)）]\s*$"
)
NUMBERED_HEAD_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)[\s、．]")
NUMBERED_SPLIT_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.*)$")
ROW_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.S | re.I)
CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script\b.*?(?:</script>|$)", re.I | re.S)
ONEVENT_RE = re.compile(r"\son\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
HTTP_RE = re.compile(r"https?://", re.I)
ID_TOKEN_RE = re.compile(r"(?<![A-Z0-9\-])[A-Z]{2,}(?:-[A-Z0-9]{2,})+(?![A-Z0-9\-])")
EXCEPTION_FLOW_RE = re.compile(r"异常流\s*[A-Z]*\d*")
CAPTION_LINE_RE = re.compile(r"^[-－*\s]*(图|表)\s*\d+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
IMG_CAP_HEAD_RE = re.compile(r"^图\s*\d+")
IMG_CAP_TAIL_RE = re.compile(
    r"(用例图|流程图|逻辑图|结构图|部署图|时序图|顺序图|状态图|活动图|"
    r"数据流图|拓扑图|框图|示意图|接口图|需求图|关系图|图)\s*$"
)
LIST_NUM_RE = re.compile(r"^\d+[\.、]\s+")
LIST_BULLET_RE = re.compile(r"^[-*－]\s+")
FLOW_NODE_TYPES = {"start", "end", "process", "state", "decision"}
USECASE_NODE_TYPES = {"usecase", "actor"}

EVIDENCE_ROUTES = (
    ("body", "正文"),
    ("usecase_table", "用例表"),
    ("flow_image", "流程图"),
    ("capability_row", "能力表行"),
    ("qualification_row", "合格性行"),
    ("trace_row", "追溯行"),
)


# ------------------------------------------------------------- 基础IO(调用期)

def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


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


def find_doc_office(doc_id: str) -> tuple[Path, Path, Path]:
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


def list_docs() -> list[dict[str, str]]:
    docs: list[dict[str, str]] = []
    if not MINERU_STANDARD.is_dir():
        return docs
    for p in sorted(MINERU_STANDARD.iterdir()):
        if p.is_dir() and re.match(r"^\d{2}", p.name):
            docs.append(
                {
                    "id": p.name[:2],
                    "name": p.name,
                    "file": f"requirement_dossier_{p.name[:2]}.html",
                }
            )
    return docs


# ------------------------------------------------------------- 纯函数内核

def sanitize_fragment(fragment: str) -> str:
    """保留MinerU轻量HTML(sub/sup/p), 剥离活动内容与外链."""
    fragment = SCRIPT_RE.sub("", fragment)
    fragment = ONEVENT_RE.sub("", fragment)
    return HTTP_RE.sub("hxxp://", fragment)


def plain_text(fragment: str) -> str:
    return html_mod.unescape(TAG_RE.sub("", fragment)).strip()


def parse_req_heading(text: str) -> tuple[str, str, str] | None:
    """标题 → (编号, 名称, 需求ID); 不含编号+括号ID的标题返回 None."""
    match = REQ_HEADING_RE.match(text)
    if match:
        num, name, req_id = match.group(1), match.group(2).strip(), match.group(3).strip()
        if name and "-" in req_id:
            return num, name, req_id
        return None
    match = REQ_HEADING_LOOSE_RE.match(text)
    if match:
        num, name, req_id = match.group(1), match.group(2).strip(), match.group(3)
        req_id = re.sub(r"\s+", "", req_id.replace("–", "-").replace("—", "-"))
        if name and "-" in req_id and len(req_id) >= 5:
            return num, name, req_id
    return None


def short_name(name: str) -> str:
    return name.rsplit("-", 1)[-1] if "-" in name else name


def build_tree(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从标题块解析需求树节点(编号+括号ID), 返回文档序平铺列表."""
    nodes: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks):
        if block.get("type") != "text" or "text_level" not in block:
            continue
        parsed = parse_req_heading(str(block.get("text", "")))
        if parsed is None:
            continue
        num, name, req_id = parsed
        nodes.append(
            {
                "num": num,
                "name": name,
                "short": short_name(name),
                "id": req_id,
                "level": int(block["text_level"]),
                "depth": num.count(".") + 1,
                "block": idx,
                "parent": None,
                "children": [],
            }
        )
    by_num = {n["num"]: n for n in nodes}
    for node in nodes:
        parts = node["num"].split(".")
        for k in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:k])
            if prefix in by_num:
                node["parent"] = prefix
                by_num[prefix]["children"].append(node["num"])
                break
    return nodes


def leaf_interval(blocks: list[dict[str, Any]], node: dict[str, Any]) -> tuple[int, int]:
    """叶子区间: 该节标题之后到下一同级/上级标题(编号深度更浅或相同)之前的所有块."""
    start = node["block"] + 1
    depth = node["depth"]
    for j in range(start, len(blocks)):
        block = blocks[j]
        if "text_level" not in block:
            continue
        text = str(block.get("text", ""))
        numbered = NUMBERED_HEAD_RE.match(text)
        if numbered:
            if numbered.group(1).count(".") + 1 <= depth:
                return start, j
        elif int(block["text_level"]) <= node["level"]:
            return start, j
    return start, len(blocks)


def split_table_rows(table_body: str) -> list[str]:
    return ROW_RE.findall(table_body or "")


def row_cells(row_html: str) -> list[str]:
    return [plain_text(c) for c in CELL_RE.findall(row_html)]


def id_suffix_segments(a: str, b: str) -> int:
    seg_a, seg_b = a.split("-"), b.split("-")
    count = 0
    while seg_a and seg_b and seg_a[-1] == seg_b[-1]:
        seg_a.pop()
        seg_b.pop()
        count += 1
    return count


def num_in_text(num: str, text: str) -> bool:
    pattern = re.compile(r"(?<![0-9.])" + re.escape(num) + r"(?![0-9.])")
    return bool(pattern.search(text))


def num_prefixes(num: str) -> list[str]:
    """编号的各级上级编号, 从近到远(不含自身)."""
    parts = num.split(".")
    return [".".join(parts[:k]) for k in range(len(parts) - 1, 0, -1)]


def match_row_to_req(
    row_html: str, req: dict[str, Any], ancestor_ids: set[str]
) -> tuple[int, str] | None:
    """行 → 需求的三重匹配: (优先级, 匹配方式) 或 None.

    ID直接 > ID后缀段(≥2段且非上级自身ID) / 编号 > 名称(整格相等).
    上级节点自身的ID出现在行中说明该行描述的是上级, 不算本需求的行.
    """
    plain = plain_text(row_html)
    if req["id"] and req["id"] in plain:
        return 3, "ID"
    cells = [c.strip() for c in row_cells(row_html)]
    for token in sorted(set(ID_TOKEN_RE.findall(plain))):
        if not token or token in ancestor_ids:
            continue
        if id_suffix_segments(token, req["id"]) >= 2:
            return 2, "ID后缀"
        if req["id"] and req["id"] in token:
            return 2, "ID包含"
    if req["num"] in cells:
        return 2, "编号"
    names = {req["name"], req.get("short", req["name"])}
    if any(c in names for c in cells if c):
        return 1, "名称"
    return None


def is_capability_table(block: dict[str, Any]) -> bool:
    captions = " ".join(str(c) for c in (block.get("table_caption") or []))
    if "能力" in captions:
        return True
    rows = split_table_rows(str(block.get("table_body", "")))
    if not rows:
        return False
    header = plain_text(rows[0])
    return "能力标识" in header or "项目唯一标识符" in header


def chapter_range(blocks: list[dict[str, Any]], chapter: int) -> tuple[int, int]:
    """第 N 章(一级标题)的块区间, 找不到返回 (len, len)."""
    start: int | None = None
    for idx, block in enumerate(blocks):
        if "text_level" not in block or int(block["text_level"]) != 1:
            continue
        text = str(block.get("text", ""))
        if re.match(rf"^{chapter}\s", text):
            if start is None:
                start = idx
        elif start is not None:
            return start, idx
    if start is None:
        return len(blocks), len(blocks)
    return start, len(blocks)


def find_qualification(
    blocks: list[dict[str, Any]], req: dict[str, Any]
) -> dict[str, Any]:
    """第4章合格性表: "本文档的章节号"列 == 本需求编号; 缺失时回退最近上级行."""
    start, end = chapter_range(blocks, 4)
    tables = [
        (idx, b)
        for idx, b in enumerate(blocks)
        if start <= idx < end and b.get("type") == "table"
    ]
    captioned = [
        (idx, b)
        for idx, b in tables
        if any("合格性" in str(c) for c in (b.get("table_caption") or []))
    ]
    chosen = captioned or tables

    def rows_for(num: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for idx, block in chosen:
            rows = split_table_rows(str(block.get("table_body", "")))
            if not rows:
                continue
            header_cells = row_cells(rows[0])
            col: int | None = None
            for ci, cell in enumerate(header_cells):
                if "章节号" in cell:
                    col = ci
                    if "本文档" in cell:
                        break
            for row in rows[1:]:
                cells = row_cells(row)
                target = col if col is not None and col < len(cells) else None
                hit = (
                    cells[target].strip() == num
                    if target is not None
                    else any(c.strip() == num for c in cells)
                )
                if hit:
                    caption = " / ".join(
                        str(c) for c in (block.get("table_caption") or [])
                    ).strip()
                    found.append(
                        {
                            "label": caption or f"第4章合格性表(块#{idx}, 无题注)",
                            "header": sanitize_fragment(rows[0]),
                            "rows": [sanitize_fragment(row)],
                            "match": "章节号",
                        }
                    )
        return found

    direct = rows_for(req["num"])
    if direct:
        return {"entries": direct, "fallback_of": None}
    for prefix in num_prefixes(req["num"]):
        rows = rows_for(prefix)
        if rows:
            for entry in rows:
                entry["fallback_of"] = prefix
            return {"entries": rows, "fallback_of": prefix}
    return {"entries": [], "fallback_of": None}


def find_trace(blocks: list[dict[str, Any]], req: dict[str, Any]) -> dict[str, Any]:
    """第5章追溯表: 含本需求编号(数字边界)/ID/名称的行; 缺失时回退最近上级行."""
    start, end = chapter_range(blocks, 5)
    tables: list[tuple[int, dict[str, Any]]] = [
        (idx, b) for idx, b in enumerate(blocks) if start <= idx < end and b.get("type") == "table"
    ]
    seen = {idx for idx, _ in tables}
    for idx, block in enumerate(blocks):
        if idx in seen or block.get("type") != "table":
            continue
        captions = " ".join(str(c) for c in (block.get("table_caption") or []))
        if "追踪" in captions or "跟踪" in captions:
            tables.append((idx, block))

    def rows_for(num: str, req_id: str, names: set[str]) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        for idx, block in tables:
            rows = split_table_rows(str(block.get("table_body", "")))
            if not rows:
                continue
            for row in rows[1:]:
                plain = plain_text(row)
                cells = [c.strip() for c in row_cells(row)]
                hit = (
                    (req_id and req_id in plain)
                    or num_in_text(num, plain)
                    or any(c in names for c in cells if c)
                )
                if hit:
                    caption = " / ".join(
                        str(c) for c in (block.get("table_caption") or [])
                    ).strip()
                    found.append(
                        {
                            "label": caption or f"第5章追溯表(块#{idx}, 无题注)",
                            "header": sanitize_fragment(rows[0]),
                            "rows": [sanitize_fragment(row)],
                            "match": "编号/名称/ID",
                        }
                    )
        return found

    names = {req["name"], req.get("short", req["name"])}
    direct = rows_for(req["num"], req["id"], names)
    if direct:
        return {"entries": direct, "fallback_of": None}
    for prefix in num_prefixes(req["num"]):
        rows = rows_for(prefix, "", set())
        if rows:
            for entry in rows:
                entry["fallback_of"] = prefix
            return {"entries": rows, "fallback_of": prefix}
    return {"entries": [], "fallback_of": None}


def find_capability_rows(
    blocks: list[dict[str, Any]],
    req: dict[str, Any],
    ancestor_ids: set[str],
    heading_by_num: dict[str, str],
    nodes_by_num: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """能力标识表(caption含"能力")中匹配本需求的行; 缺失时回退最近上级的行."""
    entries: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks):
        if block.get("type") != "table" or not is_capability_table(block):
            continue
        rows = split_table_rows(str(block.get("table_body", "")))
        if not rows:
            continue
        for row in rows[1:]:
            matched = match_row_to_req(row, req, ancestor_ids)
            if matched is None:
                continue
            caption = " / ".join(
                str(c) for c in (block.get("table_caption") or [])
            ).strip()
            entries.append(
                {
                    "label": caption or f"能力标识表(块#{idx}, 无题注)",
                    "header": sanitize_fragment(rows[0]),
                    "rows": [sanitize_fragment(row)],
                    "match": matched[1],
                }
            )
    if entries:
        return {"entries": entries, "fallback_of": None}

    for prefix in num_prefixes(req["num"]):
        prefix_node = nodes_by_num.get(prefix)
        prefix_req = {
            "num": prefix,
            "id": (prefix_node or {}).get("id", ""),
            "name": (prefix_node or {}).get("name", heading_by_num.get(prefix, prefix)),
            "short": (prefix_node or {}).get("short", heading_by_num.get(prefix, prefix)),
        }
        prefix_ids = set()
        parent = (prefix_node or {}).get("parent")
        while parent:
            parent_node = nodes_by_num.get(parent)
            if not parent_node:
                break
            prefix_ids.add(parent_node["id"])
            parent = parent_node["parent"]
        for idx, block in enumerate(blocks):
            if block.get("type") != "table" or not is_capability_table(block):
                continue
            rows = split_table_rows(str(block.get("table_body", "")))
            if not rows:
                continue
            for row in rows[1:]:
                matched = match_row_to_req(row, prefix_req, prefix_ids)
                if matched is None:
                    continue
                caption = " / ".join(
                    str(c) for c in (block.get("table_caption") or [])
                ).strip()
                entries.append(
                    {
                        "label": caption or f"能力标识表(块#{idx}, 无题注)",
                        "header": sanitize_fragment(rows[0]),
                        "rows": [sanitize_fragment(row)],
                        "match": matched[1],
                        "fallback_of": prefix,
                    }
                )
        if entries:
            return {"entries": entries, "fallback_of": prefix}
    return {"entries": [], "fallback_of": None}


# ------------------------------------------------------------- 侧栏注脚

def caption_stem(caption: str) -> str:
    stem = IMG_CAP_HEAD_RE.sub("", caption.strip())
    prev: str | None = None
    while prev != stem:
        prev = stem
        stem = IMG_CAP_TAIL_RE.sub("", stem).strip()
    return stem


def cjk_count(text: str) -> int:
    return len(CJK_RE.findall(text))


def lookup_table_feature(
    table_rows: list[dict[str, Any]], caption: str, section: str, ordinal: int
) -> dict[str, Any] | None:
    if caption:
        target = re.sub(r"\s+", "", caption)
        for row in table_rows:
            if re.sub(r"\s+", "", str(row.get("caption", ""))) == target:
                return row
    by_section = [r for r in table_rows if str(r.get("section", "")) == section]
    by_section.sort(key=lambda r: str(r.get("table_id", "")))
    if 0 <= ordinal < len(by_section):
        return by_section[ordinal]
    return None


def table_note(
    feature_row: dict[str, Any] | None, body: str, is_usecase: bool
) -> str:
    parts: list[str] = []
    if feature_row:
        n_rows = feature_row.get("n_rows")
        n_cols = feature_row.get("n_cols")
        if isinstance(n_rows, int) and isinstance(n_cols, int):
            parts.append(f"行×列：{n_rows}×{n_cols}")
        merged = feature_row.get("merged_cells")
        if isinstance(merged, list) and merged:
            parts.append(f"合并格：{len(merged)}")
    if is_usecase:
        labels: set[str] = set()
        for row in split_table_rows(body):
            for label in EXCEPTION_FLOW_RE.findall(plain_text(row)):
                normalized = re.sub(r"\s+", "", label)
                if normalized:
                    labels.add(normalized)
        parts.append(f"异常流条目：{len(labels)}")
    return "；".join(parts) if parts else "—"


def text_note(text_rows: list[dict[str, Any]], plain: str) -> str:
    if not plain:
        return "—"
    n_sent = n_quant = n_ref = 0
    for row in text_rows:
        sent = str(row.get("text") or "")
        if sent and sent in plain:
            n_sent += 1
            n_quant += len(row.get("quantities") or [])
            n_ref += len(row.get("references") or [])
    parts: list[str] = []
    if n_sent:
        parts.append(f"语句：{n_sent}")
    if n_quant:
        parts.append(f"数量词：{n_quant}")
    if n_ref:
        parts.append(f"引用：{n_ref}")
    return "；".join(parts) if parts else "—"


def image_note(diagrams: dict[str, dict[str, Any]], caption: str) -> str:
    stem = caption_stem(caption)
    if not stem or not diagrams:
        return "—"
    best: tuple[int, dict[str, Any]] | None = None
    for diag in diagrams.values():
        hits = sum(
            1 for t in diag["texts"] if t and (stem in t or t in stem)
        )
        if hits == 0:
            continue
        types = set(diag["types"])
        bonus = 0
        if "流程图" in caption and (types & FLOW_NODE_TYPES) and not (types & USECASE_NODE_TYPES):
            bonus = 2
        elif ("用例图" in caption or "用例" in caption) and (types & USECASE_NODE_TYPES):
            bonus = 2
        score = hits * 10 + bonus
        if best is None or score > best[0]:
            best = (score, diag)
    if best is None:
        return "—"
    diag = best[1]
    return f"图节点：{diag['n_nodes']}；连线：{diag['n_edges']}"


# ------------------------------------------------------------- 六路证据

def resolve_table_caption(
    blocks: list[dict[str, Any]], idx: int, start: int
) -> str:
    captions = [str(c) for c in (blocks[idx].get("table_caption") or [])]
    caption = " ".join(c for c in captions if c).strip()
    if caption:
        return caption
    for j in range(idx - 1, start - 1, -1):
        block = blocks[j]
        if block.get("type") == "table":
            continue
        if block.get("type") == "text":
            plain = plain_text(str(block.get("text", "")))
            if CAPTION_LINE_RE.match(plain) and plain.startswith("表"):
                return plain
        elif block.get("type") == "list":
            for item in reversed(block.get("list_items") or []):
                plain = plain_text(str(item))
                if CAPTION_LINE_RE.match(plain) and "表" in plain[:3]:
                    return plain.lstrip("-*－ ").strip()
        break
    return ""


def is_usecase_table(block: dict[str, Any], caption: str) -> bool:
    if "用例" in caption:
        return True
    body = str(block.get("table_body", ""))
    return "use case" in body.lower()


def has_body_text(range_blocks: list[dict[str, Any]]) -> bool:
    for block in range_blocks:
        if block.get("type") == "text":
            plain = plain_text(str(block.get("text", "")))
            if cjk_count(plain) >= 6 and not CAPTION_LINE_RE.match(plain):
                return True
        elif block.get("type") == "list":
            for item in block.get("list_items") or []:
                plain = plain_text(str(item)).lstrip("-*－ ").strip()
                if cjk_count(plain) >= 6 and not CAPTION_LINE_RE.match(plain):
                    return True
    return False


def compute_evidence(
    range_blocks: list[dict[str, Any]],
    fragments: list[dict[str, Any]],
    capability: dict[str, Any],
    qualification: dict[str, Any],
    trace: dict[str, Any],
) -> list[dict[str, Any]]:
    usecase_tables = [
        f.get("caption") or "(无题注用例表)"
        for f in fragments
        if f["kind"] == "table" and f.get("usecase")
    ]
    flow_images = [
        f.get("caption", "")
        for f in fragments
        if f["kind"] == "image" and "流程图" in f.get("caption", "")
    ]
    details = {
        "body": f"{sum(1 for b in range_blocks if b.get('type') in ('text', 'list'))}个文字块",
        "usecase_table": "；".join(usecase_tables[:2]) if usecase_tables else "区间内无用例表",
        "flow_image": "；".join(flow_images[:2]) if flow_images else "区间内无流程图",
        "capability_row": _row_detail(capability),
        "qualification_row": _row_detail(qualification),
        "trace_row": _row_detail(trace),
    }
    values = {
        "body": has_body_text(range_blocks),
        "usecase_table": bool(usecase_tables),
        "flow_image": bool(flow_images),
        "capability_row": bool(capability["entries"]) and not capability["fallback_of"],
        "qualification_row": bool(qualification["entries"]) and not qualification["fallback_of"],
        "trace_row": bool(trace["entries"]) and not trace["fallback_of"],
    }
    return [
        {"key": key, "label": label, "ok": values[key], "detail": details[key]}
        for key, label in EVIDENCE_ROUTES
    ]


def _row_detail(found: dict[str, Any]) -> str:
    if found["entries"] and not found["fallback_of"]:
        labels = "；".join(e["label"] for e in found["entries"][:2])
        return f"{len(found['entries'])}行 · {labels}"
    if found["entries"] and found["fallback_of"]:
        return f"直接行缺失；回退上级{found['fallback_of']}（{found['entries'][0]['label']}）"
    return "未找到任何匹配行"


# ------------------------------------------------------------- 档案装配

def image_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    return "image/png"


def build_fragments(
    blocks: list[dict[str, Any]],
    start: int,
    end: int,
    node: dict[str, Any],
    features: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    fragments: list[dict[str, Any]] = []
    image_paths: list[str] = []
    table_ord = 0
    table_features = features.get("table_features") or []
    text_features = features.get("text_features") or []
    diagrams = features.get("diagrams") or {}
    for idx in range(start, end):
        block = blocks[idx]
        kind = str(block.get("type", ""))
        if kind == "text":
            raw = sanitize_fragment(str(block.get("text", "")))
            if not plain_text(raw):
                continue
            fragments.append(
                {"kind": "text", "html": raw, "note": text_note(text_features, plain_text(raw))}
            )
        elif kind == "list":
            items = [sanitize_fragment(str(i)) for i in (block.get("list_items") or [])]
            items = [i for i in items if plain_text(i)]
            if not items:
                continue
            plain_join = " ".join(plain_text(i) for i in items)
            fragments.append(
                {"kind": "list", "items": items, "note": text_note(text_features, plain_join)}
            )
        elif kind == "table":
            caption = resolve_table_caption(blocks, idx, start)
            body = sanitize_fragment(str(block.get("table_body", "")))
            feature_row = lookup_table_feature(
                table_features, caption, node["num"], table_ord
            )
            table_ord += 1
            usecase = is_usecase_table(block, caption)
            fragments.append(
                {
                    "kind": "table",
                    "caption": caption,
                    "html": body,
                    "usecase": usecase,
                    "note": table_note(feature_row, body, usecase),
                }
            )
        elif kind == "image":
            path = str(block.get("image_path") or block.get("img_path") or "")
            caption = " ".join(
                str(c) for c in (block.get("image_caption") or []) if c
            ).strip()
            if path:
                image_paths.append(path)
            fragments.append(
                {
                    "kind": "image",
                    "caption": caption,
                    "path": path,
                    "note": image_note(diagrams, caption),
                }
            )
    return fragments, image_paths


def build_breadcrumb(
    node: dict[str, Any], heading_rest_by_num: dict[str, str]
) -> dict[str, Any]:
    crumbs: list[str] = []
    for prefix in num_prefixes(node["num"]):
        rest = heading_rest_by_num.get(prefix)
        if rest is None:
            continue
        parts = prefix.split(".")
        if len(parts) < 3:
            break
        crumbs.append(f"{prefix} {rest}")
    crumbs.reverse()
    return {"crumbs": crumbs, "leaf": node["short"], "id": node["id"]}


def build_dossier_payload(
    doc_id: str,
    doc_name: str,
    blocks: list[dict[str, Any]],
    office_dir: Path,
    features: dict[str, Any],
    docs: list[dict[str, str]],
) -> dict[str, Any]:
    nodes = build_tree(blocks)
    nodes_by_num = {n["num"]: n for n in nodes}
    heading_full_by_num: dict[str, str] = {}
    heading_rest_by_num: dict[str, str] = {}
    for block in blocks:
        if "text_level" not in block:
            continue
        match = NUMBERED_SPLIT_RE.match(str(block.get("text", "")))
        if match:
            num, rest = match.group(1), match.group(2).strip()
            heading_full_by_num.setdefault(num, str(block.get("text", "")).strip())
            heading_rest_by_num.setdefault(num, re.sub(r"[（(].*?[)）]\s*$", "", rest).strip())
    leaves = [n for n in nodes if not n["children"]]
    leaf_payloads: dict[str, dict[str, Any]] = {}
    needed_images: set[str] = set()
    for node in leaves:
        start, end = leaf_interval(blocks, node)
        fragments, image_paths = build_fragments(blocks, start, end, node, features)
        needed_images.update(image_paths)
        ancestor_ids: set[str] = set()
        parent = node["parent"]
        while parent:
            parent_node = nodes_by_num.get(parent)
            if not parent_node:
                break
            ancestor_ids.add(parent_node["id"])
            parent = parent_node["parent"]
        parent_heading = ""
        for prefix in num_prefixes(node["num"]):
            if prefix in heading_full_by_num:
                parent_heading = heading_full_by_num[prefix]
                break
        capability = find_capability_rows(
            blocks, node, ancestor_ids, heading_rest_by_num, nodes_by_num
        )
        qualification = find_qualification(blocks, node)
        trace = find_trace(blocks, node)
        range_blocks = blocks[start:end]
        evidence = compute_evidence(
            range_blocks, fragments, capability, qualification, trace
        )
        leaf_payloads[node["num"]] = {
            "num": node["num"],
            "name": node["name"],
            "short": node["short"],
            "id": node["id"],
            "title": str(blocks[node["block"]].get("text", "")).strip(),
            "level": node["level"],
            "blockStart": start,
            "blockEnd": end,
            "breadcrumb": build_breadcrumb(node, heading_rest_by_num),
            "fragments": fragments,
            "upstream": {
                "parent_heading": parent_heading,
                "parent_num": num_prefixes(node["num"])[0] if num_prefixes(node["num"]) else "",
                "entries": capability["entries"],
                "fallback_of": capability["fallback_of"],
            },
            "qualification": qualification,
            "trace": trace,
            "evidence": evidence,
        }

    images: dict[str, str] = {}
    for rel in sorted(needed_images):
        path = office_dir / rel
        if path.exists():
            data_uri = "data:" + image_mime(path) + ";base64," + base64.b64encode(
                path.read_bytes()
            ).decode("ascii")
            images[rel] = data_uri

    def tree_children(nums: list[str]) -> list[dict[str, Any]]:
        return [
            {
                "num": nodes_by_num[num]["num"],
                "name": nodes_by_num[num]["name"],
                "id": nodes_by_num[num]["id"],
                "leaf": not nodes_by_num[num]["children"],
                "children": tree_children(nodes_by_num[num]["children"]),
            }
            for num in nums
        ]

    roots = [n["num"] for n in nodes if n["parent"] is None]
    default_leaf = ""
    if "3.2.1.1.1.1" in leaf_payloads:
        default_leaf = "3.2.1.1.1.1"
    elif leaves:
        default_leaf = leaves[0]["num"]
    return {
        "doc": {"id": doc_id, "name": doc_name},
        "docs": docs,
        "tree": tree_children(roots),
        "defaultLeaf": default_leaf,
        "leaves": leaf_payloads,
        "images": images,
    }


def load_features(doc_id: str) -> dict[str, Any]:
    table_rows = read_jsonl(FEATURE_V1_DIR / "table_features.jsonl", doc_id)
    text_rows = read_jsonl(FEATURE_V1_DIR / "text_features.jsonl", doc_id)
    nodes = read_jsonl(VISIO_V2_DIR / "visio_nodes_v2.jsonl", doc_id)
    edges = read_jsonl(VISIO_V2_DIR / "visio_edges_v2.jsonl", doc_id)
    diagrams: dict[str, dict[str, Any]] = {}
    for node in nodes:
        diag = diagrams.setdefault(
            str(node.get("diagram_id", "")),
            {"n_nodes": 0, "n_edges": 0, "texts": [], "types": []},
        )
        diag["n_nodes"] += 1
        diag["texts"].append(str(node.get("text_raw") or ""))
        diag["types"].append(str(node.get("type_candidate") or ""))
    for edge in edges:
        diag = diagrams.setdefault(
            str(edge.get("diagram_id", "")),
            {"n_nodes": 0, "n_edges": 0, "texts": [], "types": []},
        )
        diag["n_edges"] += 1
    return {"table_features": table_rows, "text_features": text_rows, "diagrams": diagrams}


# ------------------------------------------------------------- HTML渲染

CSS = """
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.75 "Microsoft YaHei", "PingFang SC", sans-serif;
  color: #111; background: #fff; }
header { position: sticky; top: 0; z-index: 10; background: #fff;
  border-bottom: 1px solid #d9d9d9; padding: 10px 18px; }
.topbar { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
.doc-title { font-weight: 600; font-size: 15px; }
select { font: inherit; border: 1px solid #bbb; padding: 2px 6px; background: #fff; }
.crumbs { color: #555; font-size: 13px; }
.crumbs .sep { color: #aaa; margin: 0 4px; }
.crumbs .leaf { color: #111; font-weight: 600; }
.crumbs .rid { color: #888; font-size: 12px; margin-left: 6px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; }
.chip { border: 1px solid #ccc; border-radius: 3px; padding: 0 8px; font-size: 12px;
  color: #333; white-space: nowrap; }
.chip.ok { border-color: #666; }
.chip.ok b { color: #111; }
.chip.miss { border-style: dashed; color: #999; background: #fafafa; }
.layout { display: flex; height: calc(100vh - 96px); }
nav { width: 25%; min-width: 260px; border-right: 1px solid #d9d9d9; overflow: auto;
  padding: 8px 6px 40px; background: #fcfcfc; }
nav h2 { font-size: 12px; color: #888; font-weight: normal; margin: 4px 6px; }
.tree { list-style: none; margin: 0; padding-left: 10px; }
.tree .tree { padding-left: 16px; }
.tree li { margin: 1px 0; }
.tree summary { cursor: default; color: #333; padding: 2px 4px; }
.tree .tnum { color: #999; font-size: 12px; margin-right: 3px; }
.tree .leaf { padding: 3px 6px; cursor: pointer; border-left: 3px solid transparent; }
.tree .leaf:hover { background: #efefef; }
.tree .leaf.active { background: #e8f0fe; border-left-color: #2563eb; color: #1a56db; }
.tree .tid { color: #999; font-size: 11px; margin-left: 4px; }
main { width: 75%; overflow: auto; padding: 18px 30px 60px; }
.dossier-title { font-size: 18px; font-weight: 600; margin: 4px 0 2px; }
.dossier-meta { color: #999; font-size: 12px; margin-bottom: 12px; }
.frag { display: grid; grid-template-columns: minmax(0, 1fr) 170px; gap: 14px;
  border-bottom: 1px dashed #e5e5e5; padding: 12px 0; }
.frag-note { color: #999; font-size: 11px; text-align: right; line-height: 1.6;
  padding-top: 3px; }
.orig-text { margin: 4px 0; color: #000; }
.orig-list { margin: 4px 0; padding-left: 22px; }
.tbl-cap { font-size: 12px; color: #555; margin: 6px 0 3px; }
.tbl-wrap { overflow-x: auto; }
.tbl-wrap table { border-collapse: collapse; background: #fff; }
.tbl-wrap td, .tbl-wrap th { border: 1px solid #8f8f8f; padding: 4px 9px;
  font-size: 13px; vertical-align: top; }
figure.orig-fig { margin: 8px 0; }
figure.orig-fig img { max-width: 100%; height: auto; border: 1px solid #ddd; }
figure.orig-fig img.full { max-width: none; }
figure.orig-fig figcaption { font-size: 12px; color: #555; margin-top: 3px; }
.ctx h3 { font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 3px;
  margin: 26px 0 8px; }
.ctx h3 .hint { font-weight: normal; color: #999; font-size: 12px; margin-left: 8px; }
.parent-head { font-size: 14px; font-weight: 600; margin: 2px 0 4px; }
.row-entry { margin: 8px 0 14px; }
.row-meta { font-size: 12px; color: #666; margin-bottom: 3px; }
.row-meta .row-label { font-weight: 600; }
.row-match { margin-left: 10px; color: #888; }
.row-fb { margin-left: 10px; color: #888; font-style: italic; }
.missing { color: #999; font-size: 13px; padding: 6px 0; }
footer { color: #999; font-size: 11px; padding: 8px 18px; border-top: 1px solid #eee; }
"""

JS = """
const DATA = JSON.parse(document.getElementById('dossier-data').textContent);
const state = { leaf: DATA.defaultLeaf };

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function treeHtml(nodes) {
  return '<ul class="tree">' + nodes.map((n) => n.leaf
    ? '<li class="leaf' + (n.num === state.leaf ? ' active' : '') + '" data-num="' + esc(n.num)
      + '"><span class="tnum">' + esc(n.num) + '</span>' + esc(n.name)
      + ' <span class="tid">' + esc(n.id) + '</span></li>'
    : '<li class="branch"><details open><summary><span class="tnum">' + esc(n.num)
      + '</span>' + esc(n.name) + ' <span class="tid">' + esc(n.id) + '</span></summary>'
      + treeHtml(n.children) + '</details></li>'
  ).join('') + '</ul>';
}

function chipsHtml(evidence) {
  return '<div class="chips">' + evidence.map((e) =>
    '<span class="chip ' + (e.ok ? 'ok' : 'miss') + '" title="' + esc(e.detail) + '">'
    + esc(e.label) + ' ' + (e.ok ? '<b>✓</b>' : '✗') + '</span>'
  ).join('') + '</div>';
}

function crumbsHtml(bc) {
  const parts = bc.crumbs.map((c) => '<span>' + esc(c) + '</span>');
  parts.push('<span class="leaf">' + esc(bc.leaf) + '</span>');
  return '<span class="crumbs">' + parts.join('<span class="sep">›</span>')
    + '<span class="rid">' + esc(bc.id) + '</span></span>';
}

function fragHtml(f) {
  let main = '';
  if (f.kind === 'text') {
    main = '<p class="orig-text">' + f.html + '</p>';
  } else if (f.kind === 'list') {
    main = '<ul class="orig-list">' + f.items.map((i) => '<li>' + i + '</li>').join('') + '</ul>';
  } else if (f.kind === 'table') {
    main = '<div class="tbl-cap">' + esc(f.caption || '（无题注）') + '</div>'
      + '<div class="tbl-wrap">' + f.html + '</div>';
  } else if (f.kind === 'image') {
    const src = DATA.images[f.path];
    main = src
      ? '<figure class="orig-fig"><img src="' + src + '" alt="' + esc(f.caption)
        + '" loading="lazy" title="点击切换完整尺寸">'
        + '<figcaption>' + esc(f.caption || '') + '</figcaption></figure>'
      : '<figure class="orig-fig missing">图片文件缺失：' + esc(f.path) + '</figure>';
  }
  return '<div class="frag"><div class="frag-main">' + main + '</div>'
    + '<aside class="frag-note">' + esc(f.note || '—') + '</aside></div>';
}

function rowEntriesHtml(entries, emptyMsg) {
  if (!entries || !entries.length) {
    return '<div class="missing">' + esc(emptyMsg) + '</div>';
  }
  return entries.map((en) =>
    '<div class="row-entry"><div class="row-meta"><span class="row-label">'
    + esc(en.label || '（无题注）') + '</span>'
    + (en.match ? '<span class="row-match">匹配：' + esc(en.match) + '</span>' : '')
    + (en.fallback_of ? '<span class="row-fb">回退：上级' + esc(en.fallback_of) + '的行</span>' : '')
    + '</div><div class="tbl-wrap"><table>' + en.header + en.rows.join('') + '</table></div></div>'
  ).join('');
}

function renderLeaf(num) {
  const leaf = DATA.leaves[num];
  if (!leaf) { return; }
  state.leaf = num;
  document.querySelectorAll('.tree .leaf').forEach((el) => {
    el.classList.toggle('active', el.getAttribute('data-num') === num);
  });
  const crumbs = document.getElementById('crumbs');
  crumbs.innerHTML = crumbsHtml(leaf.breadcrumb);
  const chips = document.getElementById('chips');
  chips.innerHTML = chipsHtml(leaf.evidence);
  const page = document.getElementById('dossier');
  const fragCount = leaf.fragments.length;
  page.innerHTML =
    '<h2 class="dossier-title">' + esc(leaf.title) + '</h2>'
    + '<div class="dossier-meta">块区间 #' + leaf.blockStart + '–#' + leaf.blockEnd
    + ' · ' + fragCount + '个片段 · 需求ID ' + esc(leaf.id) + '</div>'
    + '<div class="fragments">' + leaf.fragments.map(fragHtml).join('') + '</div>'
    + '<div class="ctx">'
    + '<h3>上游 · 父节点与能力标识行</h3>'
    + '<div class="parent-head">' + esc(leaf.upstream.parent_heading || '（无上级标题）') + '</div>'
    + rowEntriesHtml(leaf.upstream.entries,
      '未在能力标识表(caption含"能力")中找到本需求的行')
    + '<h3>合格性 <span class="hint">第4章 · "本文档的章节号"列==本需求编号</span></h3>'
    + rowEntriesHtml(leaf.qualification.entries, '未找到合格性行(含上级回退)')
    + '<h3>追溯 <span class="hint">第5章 · 含本需求编号/名称/ID的行</span></h3>'
    + rowEntriesHtml(leaf.trace.entries, '未找到追溯行(含上级回退)')
    + '</div>';
}

document.getElementById('nav-tree').addEventListener('click', (ev) => {
  const target = ev.target.closest('.leaf');
  if (!target) { return; }
  renderLeaf(target.getAttribute('data-num'));
  document.getElementById('dossier').scrollIntoView();
});

document.getElementById('dossier').addEventListener('click', (ev) => {
  const img = ev.target.closest('figure.orig-fig img');
  if (img) { img.classList.toggle('full'); }
});

const docSelect = document.getElementById('doc-select');
DATA.docs.forEach((d, i) => {
  const opt = document.createElement('option');
  opt.value = String(i);
  opt.textContent = d.id + ' ' + d.name;
  if (d.id === DATA.doc.id) { opt.selected = true; }
  docSelect.appendChild(opt);
});
docSelect.addEventListener('change', () => {
  const d = DATA.docs[Number(docSelect.value)];
  if (d && d.id !== DATA.doc.id) { window.location.href = d.file; }
});

document.getElementById('nav-tree').innerHTML = treeHtml(DATA.tree);
document.getElementById('nav-count').textContent =
  '需求树：' + countNodes(DATA.tree) + '个节点（'
  + countLeaves(DATA.tree) + '个叶子，可点击）';

function countNodes(nodes) {
  return nodes.reduce((acc, n) => acc + 1 + countNodes(n.children), 0);
}
function countLeaves(nodes) {
  return nodes.reduce((acc, n) => acc + (n.leaf ? 1 : countLeaves(n.children)), 0);
}

renderLeaf(DATA.defaultLeaf);
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>GJB需求条目档案 · {doc_name}</title>
<style>{css}</style>
</head>
<body>
<header>
  <div class="topbar">
    <span class="doc-title">需求条目档案</span>
    <select id="doc-select" title="切换文档需先渲染对应 requirement_dossier_NN.html"></select>
    <span id="crumbs"></span>
  </div>
  <div id="chips" style="margin-top:6px;"></div>
</header>
<div class="layout">
  <nav>
    <h2 id="nav-count"></h2>
    <div id="nav-tree"></div>
  </nav>
  <main id="dossier"></main>
</div>
<footer>主视觉为原始文档内容（正文/原表HTML/原图base64）；右侧灰色小字为客观计数注脚
（feature_matrix_v1 / visio_features_v2，查不到显示"—"）。黑白灰+单强调色，原文不加高亮。</footer>
<script type="application/json" id="dossier-data">{data}</script>
<script>{js}</script>
</body>
</html>
"""


def render_html(payload: dict[str, Any]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.format(
        doc_name=payload["doc"]["name"], css=CSS, data=data_json, js=JS
    )


# ------------------------------------------------------------- 入口

def collect_stats(payload: dict[str, Any], output: Path) -> dict[str, Any]:
    nodes_by_depth: dict[str, int] = {}

    def walk(nodes: list[dict[str, Any]]) -> int:
        total = 0
        for node in nodes:
            depth = node["num"].count(".") + 1
            nodes_by_depth[str(depth)] = nodes_by_depth.get(str(depth), 0) + 1
            total += 1 + walk(node["children"])
        return total

    total_nodes = walk(payload["tree"])

    def count_leaves(nodes: list[dict[str, Any]]) -> int:
        return sum(1 if n["leaf"] else count_leaves(n["children"]) for n in nodes)

    default_leaf = payload["leaves"].get(payload["defaultLeaf"], {})
    return {
        "doc": payload["doc"]["id"],
        "doc_name": payload["doc"]["name"],
        "nodes_total": total_nodes,
        "nodes_by_depth": dict(sorted(nodes_by_depth.items(), key=lambda kv: int(kv[0]))),
        "leaves_total": count_leaves(payload["tree"]),
        "leaves_rendered": len(payload["leaves"]),
        "images_embedded": len(payload["images"]),
        "default_leaf": payload["defaultLeaf"],
        "default_leaf_title": default_leaf.get("title", ""),
        "default_evidence": {
            e["label"]: ("✓" if e["ok"] else "✗") + " " + e["detail"]
            for e in default_leaf.get("evidence", [])
        },
        "output": str(output),
        "output_bytes": output.stat().st_size if output.exists() else 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="渲染GJB需求条目档案dossier(自包含HTML)")
    parser.add_argument("--doc", default="04", help="doc id, 如 04 (默认: 04)")
    parser.add_argument(
        "--output", type=Path, default=None, help="输出HTML路径 (默认: data/gjb_438c/)"
    )
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    doc_id = args.doc.strip()
    doc_dir, office, content_list_path = find_doc_office(doc_id)
    blocks = read_json(content_list_path)
    if not isinstance(blocks, list):
        raise ValueError(f"content_list 不是列表: {content_list_path}")
    features = load_features(doc_id)
    payload = build_dossier_payload(
        doc_id, doc_dir.name, blocks, office, features, list_docs()
    )
    html_doc = render_html(payload)
    output = args.output or Path(str(DEFAULT_OUTPUT).replace("{doc}", doc_id))
    output = output if output.is_absolute() else BASE / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_doc, encoding="utf-8", newline="\n")
    stats = collect_stats(payload, output)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
