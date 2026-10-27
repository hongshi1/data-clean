#!/usr/bin/env python3
r"""GJB提取图谱(extraction atlas)渲染器: 三Tab自包含HTML.

Tab1 追溯矩阵热力图: 全部叶子需求 × 六路证据(正文/用例表/流程图/能力表行/合格性行/追溯行),
    每格状态点 ●绿=直接命中 ◑黄=回退上级命中 ○红=缺失, 点击切到Tab2该需求档案;
    底部各路齐全数与断链Top(缺失路数最多的需求). CSS grid渲染, 保持可点击.
Tab2 需求档案: 左侧需求树(编号/名称/ID), 选中叶子 → 六路证据卡
    (①正文原文完整文本 ②用例表原HTML ③流程图原图base64 ④能力表行 ⑤合格性行 ⑥追溯行).
Tab3 逐句对照表(默认Tab): 双栏表格, 每行=一个提取单元, 按原文顺序
    (句子按block_idx排序, 表格行按表序插入, 图caption行插入);
    左列45%原文(句子/表行首3格/图caption, 完整不截断, 上方小灰字来源标注),
    右列55%提取结果12字段规整网格(值或灰"—", 整行无提取显示"（无提取）");
    顶部章节/需求ID/只看有谓词/只看有数值过滤; 底部真实提取率统计.

视觉铁律: 原文永远完整呈现不加高亮涂色; 提取结果规整表格逐格展示;
颜色只用于状态点(●绿/◑黄/○红), 主色黑白灰+一个强调蓝.

数据源(全部只读, 调用期IO):
- 原文: data/gjb_438c/mineru_standard/<doc>/office/<doc>_content_list.json (text/table/image块
  含text_level/table_body/image_path/caption); 图片office/images/*.png→base64
- 需求树: content_list标题 r'^(\d+(?:\.\d+)+)\s+(.+?)[（(]\s*([A-Z0-9\-]+)\s*[)）]'
  (宽松版兜底ID内部空格/全角破折号, 与render_requirement_dossier对齐)
- 逐句: feature_matrix_v2/sentences.jsonl + references_resolved.jsonl
  + feature_matrix_v1/claim_slot_features.jsonl + predicate_mining_v1/predicates.jsonl
- 表行: feature_matrix_v2/tables_v2.jsonl + feature_matrix_v1/table_features.jsonl
- 实体: semantic_features_v2/entity_type_v2.jsonl (occurrence_id=claim_id/需求ID)
- 六路状态: 由content_list独立重算(正文=叶子区间文字块; 用例表=区间含"用例"caption的表;
  流程图=区间有image; 能力表行=能力标识表ID后缀匹配; 合格性行=第4章章节号列;
  追溯行=第5章), 逻辑参照render_requirement_dossier.py已验证实现, 本脚本独立实现.

Usage:
  python tools/render_extraction_atlas.py [--doc 04] [--output PATH]
  默认输出 data/gjb_438c/extraction_atlas_04.html
"""
from __future__ import annotations

import argparse
import base64
import html as html_mod
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
MINERU_STANDARD = BASE / "data/gjb_438c/mineru_standard"
FEATURE_V2_DIR = BASE / "data/gjb_438c/feature_matrix_v2"
FEATURE_V1_DIR = BASE / "data/gjb_438c/feature_matrix_v1"
PREDICATE_DIR = BASE / "data/gjb_438c/predicate_mining_v1"
SEMANTIC_DIR = BASE / "data/gjb_438c/semantic_features_v2"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/extraction_atlas_{doc}.html"

# 需求树标题解析: 编号 + 名称 + 括号内ID(主用严格前缀版, ID含"-")
REQ_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)+)\s+(.+?)[（(]\s*([A-Z0-9\-]+)\s*[)）]")
# 宽松版兜底: 容忍ID内部空格/全角破折号(如 "PZXQ-GN-SQLFW-BLOBSJCZ- BLOBSJXG")
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
CAPTION_LINE_RE = re.compile(r"^[-－*\s]*(图|表)\s*\d+")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
TABLE_NO_RE = re.compile(r"^(表\s*\d+)")
FIGURE_NO_RE = re.compile(r"^(图\s*\d+)")

ROUTES = (
    ("body", "正文"),
    ("usecase", "用例表"),
    ("flow", "流程图"),
    ("capability", "能力表行"),
    ("qualification", "合格性行"),
    ("trace", "追溯行"),
)
ROUTE_KEYS = [key for key, _ in ROUTES]

MODAL_MULTI = (
    "必须", "应当", "应该", "不宜", "不得", "不能",
    "禁止", "尽量", "避免", "可以", "无须", "无需",
)
MODAL_SINGLE = ("应", "宜", "须", "可")
# 单字模态词落在这些双字组合里 = 非模态(应用/可靠/便宜等复合词)
NON_MODAL_PAIRS = {
    "应用", "反应", "适应", "对应", "供应", "响应", "应急", "应答", "应付", "应运",
    "可靠", "可能", "认可", "许可", "可视", "可选", "可比", "可调", "可维", "可读",
    "可写", "可用", "不可",
    "便宜", "适宜", "相宜",
}


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


def load_features(doc_id: str) -> dict[str, Any]:
    sentences = read_jsonl(FEATURE_V2_DIR / "sentences.jsonl", doc_id)
    refs = read_jsonl(FEATURE_V2_DIR / "references_resolved.jsonl", doc_id)
    tables_v2 = read_jsonl(FEATURE_V2_DIR / "tables_v2.jsonl", doc_id)
    slots = [
        row
        for row in read_jsonl(FEATURE_V1_DIR / "claim_slot_features.jsonl", doc_id)
        if row.get("kind") == "text_claim"
    ]
    table_features = read_jsonl(FEATURE_V1_DIR / "table_features.jsonl", doc_id)
    predicates = read_jsonl(PREDICATE_DIR / "predicates.jsonl", doc_id)
    entities: dict[str, str] = {}
    for row in read_jsonl(SEMANTIC_DIR / "entity_type_v2.jsonl", doc_id):
        occ = str(row.get("occurrence_id") or "")
        etype = str(row.get("entity_type") or "")
        if occ and etype and occ not in entities:
            entities[occ] = etype
    return {
        "sentences": sentences,
        "refs": refs,
        "tables_v2": tables_v2,
        "slots": slots,
        "table_features": table_features,
        "predicates": predicates,
        "entities": entities,
    }


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


def num_prefixes(num: str) -> list[str]:
    """编号的各级上级编号, 从近到远(不含自身)."""
    parts = num.split(".")
    return [".".join(parts[:k]) for k in range(len(parts) - 1, 0, -1)]


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
                    caption = " ".join(
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
                    caption = " ".join(
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
    heading_rest_by_num: dict[str, str],
    nodes_by_num: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """能力标识表(caption含"能力")中匹配本需求的行; 缺失时回退最近上级的行."""
    entries: list[dict[str, Any]] = []

    def scan(target: dict[str, Any], excluded: set[str], fallback_of: str | None) -> None:
        for idx, block in enumerate(blocks):
            if block.get("type") != "table" or not is_capability_table(block):
                continue
            rows = split_table_rows(str(block.get("table_body", "")))
            if not rows:
                continue
            for row in rows[1:]:
                matched = match_row_to_req(row, target, excluded)
                if matched is None:
                    continue
                caption = " ".join(
                    str(c) for c in (block.get("table_caption") or [])
                ).strip()
                entry = {
                    "label": caption or f"能力标识表(块#{idx}, 无题注)",
                    "header": sanitize_fragment(rows[0]),
                    "rows": [sanitize_fragment(row)],
                    "match": matched[1],
                }
                if fallback_of:
                    entry["fallback_of"] = fallback_of
                entries.append(entry)

    scan(req, ancestor_ids, None)
    if entries:
        return {"entries": entries, "fallback_of": None}

    for prefix in num_prefixes(req["num"]):
        prefix_node = nodes_by_num.get(prefix)
        prefix_req = {
            "num": prefix,
            "id": (prefix_node or {}).get("id", ""),
            "name": (prefix_node or {}).get("name", heading_rest_by_num.get(prefix, prefix)),
            "short": (prefix_node or {}).get("short", heading_rest_by_num.get(prefix, prefix)),
        }
        prefix_ids: set[str] = set()
        parent = (prefix_node or {}).get("parent")
        while parent:
            parent_node = nodes_by_num.get(parent)
            if not parent_node:
                break
            prefix_ids.add(parent_node["id"])
            parent = parent_node["parent"]
        scan(prefix_req, prefix_ids, prefix)
        if entries:
            return {"entries": entries, "fallback_of": prefix}
    return {"entries": [], "fallback_of": None}


# ------------------------------------------------------------- 六路证据状态

def cjk_count(text: str) -> int:
    return len(CJK_RE.findall(text))


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


def resolve_table_caption(blocks: list[dict[str, Any]], idx: int, start: int) -> str:
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


def found_state(found: dict[str, Any]) -> str:
    if found["entries"] and not found["fallback_of"]:
        return "direct"
    if found["entries"]:
        return "fallback"
    return "missing"


def _row_detail(found: dict[str, Any]) -> str:
    if found["entries"] and not found["fallback_of"]:
        labels = "；".join(e["label"] for e in found["entries"][:2])
        return f"{len(found['entries'])}行 · {labels}"
    if found["entries"] and found["fallback_of"]:
        return f"直接行缺失；回退上级{found['fallback_of']}（{found['entries'][0]['label']}）"
    return "未找到任何匹配行"


def build_leaf_view(
    blocks: list[dict[str, Any]],
    node: dict[str, Any],
    capability: dict[str, Any],
    qualification: dict[str, Any],
    trace: dict[str, Any],
    needed_images: set[str],
) -> dict[str, Any]:
    """Tab2单叶子档案: 六路状态+详情+六卡内容(原文完整, 不加高亮)."""
    start, end = leaf_interval(blocks, node)
    body: list[dict[str, Any]] = []
    usecases: list[dict[str, str]] = []
    images: list[dict[str, str]] = []
    for idx in range(start, end):
        block = blocks[idx]
        kind = str(block.get("type", ""))
        if kind == "text":
            raw = sanitize_fragment(str(block.get("text", "")))
            if plain_text(raw):
                body.append({"t": "p", "h": raw})
        elif kind == "list":
            items = [sanitize_fragment(str(i)) for i in (block.get("list_items") or [])]
            items = [i for i in items if plain_text(i)]
            if items:
                body.append({"t": "ul", "items": items})
        elif kind == "table":
            caption = resolve_table_caption(blocks, idx, start)
            if is_usecase_table(block, caption):
                usecases.append(
                    {
                        "caption": caption,
                        "html": sanitize_fragment(str(block.get("table_body", ""))),
                        "blk": idx,
                    }
                )
        elif kind == "image":
            path = str(block.get("image_path") or block.get("img_path") or "")
            caption = " ".join(
                str(c) for c in (block.get("image_caption") or []) if c
            ).strip()
            if path:
                needed_images.add(path)
            images.append({"caption": caption, "path": path, "blk": idx})
    range_blocks = blocks[start:end]
    states = {
        "body": "direct" if has_body_text(range_blocks) else "missing",
        "usecase": "direct" if usecases else "missing",
        "flow": "direct" if images else "missing",
        "capability": found_state(capability),
        "qualification": found_state(qualification),
        "trace": found_state(trace),
    }
    n_text = sum(1 for b in range_blocks if b.get("type") in ("text", "list"))
    details = {
        "body": f"{n_text}个文字块" if n_text else "区间无正文文字块",
        "usecase": (
            "；".join(u["caption"] or "(无题注)" for u in usecases[:2])
            if usecases
            else "区间内无用例表"
        ),
        "flow": (
            "；".join(i["caption"] or "(无题注)" for i in images[:2])
            if images
            else "区间内无图片"
        ),
        "capability": _row_detail(capability),
        "qualification": _row_detail(qualification),
        "trace": _row_detail(trace),
    }
    return {
        "num": node["num"],
        "title": str(blocks[node["block"]].get("text", "")).strip(),
        "id": node["id"],
        "blockStart": start,
        "blockEnd": end,
        "states": states,
        "details": details,
        "body": body,
        "usecases": usecases,
        "images": images,
        "capability": capability,
        "qualification": qualification,
        "trace": trace,
    }


# ------------------------------------------------------------- Tab3提取单元

def text_of(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    return str(value).strip()


def extract_modals(text: str) -> list[str]:
    """规则抽取模态词(应/宜/可/须/必须/不得/禁止…), 按首次出现顺序去重.

    单字模态词若落在复合词(应用/可靠/便宜等)里则跳过; 多字词优先匹配.
    """
    found: dict[str, int] = {}
    i = 0
    while i < len(text):
        matched: str | None = None
        for token in MODAL_MULTI:
            if text.startswith(token, i):
                matched = token
                break
        if matched is None:
            ch = text[i]
            if ch in MODAL_SINGLE:
                prev = text[i - 1] if i > 0 else ""
                nxt = text[i + 1] if i + 1 < len(text) else ""
                pair_hit = (prev and prev + ch in NON_MODAL_PAIRS) or (
                    nxt and ch + nxt in NON_MODAL_PAIRS
                )
                if not pair_hit:
                    matched = ch
        if matched:
            if matched not in found:
                found[matched] = i
            i += len(matched)
        else:
            i += 1
    return [token for token, _ in sorted(found.items(), key=lambda kv: kv[1])]


def req_id_for_section(section: str, nodes_by_num: dict[str, dict[str, Any]]) -> str:
    """章节号 → 最近的上级需求树节点ID(不含自身树外的章节返回空)."""
    if not section:
        return ""
    parts = str(section).split(".")
    for k in range(len(parts), 0, -1):
        prefix = ".".join(parts[:k])
        node = nodes_by_num.get(prefix)
        if node:
            return str(node.get("id") or "")
    return ""


def predicate_text(
    pred_row: dict[str, Any] | None, slot_row: dict[str, Any] | None
) -> str:
    """谓词: predicates的verb+object_stripped优先, 否则claim_slot的predicate_candidate."""
    if pred_row:
        pf = pred_row.get("predicate_function") or {}
        verb = text_of(pf.get("verb"))
        obj = text_of(pf.get("object_stripped"))
        if verb and obj:
            return f"{verb}｜{obj}"
        if verb or obj:
            return verb or obj
    if slot_row:
        cand = text_of(slot_row.get("predicate_candidate"))
        if cand:
            return cand
    return ""


def refs_text(ref_rows: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in ref_rows or []:
        ref = text_of(row.get("ref"))
        if not ref:
            continue
        if row.get("status") == "resolved" and row.get("target_id"):
            parts.append(f"{ref}→{text_of(row.get('target_id'))}")
        else:
            parts.append(f"{ref}→未解析")
    return "；".join(parts)


def scope_entities_of(sentence: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("scope_entities", "scope_entity"):
        value = sentence.get(key)
        if isinstance(value, list):
            return value
    return []


def sentence_unit(
    sentence: dict[str, Any],
    slots: dict[str, dict[str, Any]],
    predicates: dict[str, dict[str, Any]],
    refs: dict[str, list[dict[str, Any]]],
    entities: dict[str, str],
    nodes_by_num: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    claim_id = text_of(sentence.get("claim_id"))
    span = sentence.get("span") or {}
    text = str(sentence.get("text") or "")
    slot = slots.get(claim_id) or {}
    section = text_of(sentence.get("section"))
    fields = {
        "rid": req_id_for_section(section, nodes_by_num),
        "pred": predicate_text(predicates.get(claim_id), slot),
        "op": text_of(slot.get("operator")),
        "val": value_text(slot.get("object_value")),
        "unit": text_of(slot.get("unit_raw")),
        "modal": "、".join(extract_modals(text)),
        "neg": "、".join(
            text_of(n.get("word")) for n in (sentence.get("negations") or []) if isinstance(n, dict)
        ),
        "cond": "；".join(
            text_of(c.get("cond_text"))
            for c in (sentence.get("conditions") or [])
            if isinstance(c, dict)
        ),
        "ref": refs_text(refs.get(claim_id) or []),
        "ent": text_of(entities.get(claim_id)),
        "role": "",
        "scope": "、".join(
            text_of(e.get("entity"))
            for e in scope_entities_of(sentence)
            if isinstance(e, dict)
        ),
    }
    src = (
        f"{section}·块{span.get('block_idx', '')}"
        f"·句{span.get('start', '')}-{span.get('end', '')}"
    )
    return {"k": "sentence", "sec": section, "src": src, "text": text, "f": fields}


def table_label_of(t2: dict[str, Any]) -> str:
    caption = str(t2.get("caption_raw") or "").strip()
    match = TABLE_NO_RE.match(caption)
    if match:
        return re.sub(r"\s+", "", match.group(1))
    return text_of(t2.get("table_id")) or "表"


def table_row_units(
    t2: dict[str, Any],
    feature: dict[str, Any] | None,
    entities: dict[str, str],
    nodes_by_num: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """tables_v2表 → 数据行单元(跳过表头行): 原文=首3格文本拼接, 提取=表行特征."""
    cells_by_row: dict[int, list[tuple[int, str]]] = {}
    for cell in t2.get("cells") or []:
        row, col = cell.get("row"), cell.get("col")
        if not isinstance(row, int) or not isinstance(col, int):
            continue
        cells_by_row.setdefault(row, []).append((col, str(cell.get("text") or "")))
    thead = t2.get("thead_rows") or 0
    if not isinstance(thead, int) or thead < 0:
        thead = 0
    section = text_of(t2.get("section"))
    label = table_label_of(t2)
    units: list[dict[str, Any]] = []
    for row in sorted(cells_by_row):
        if row < thead:
            continue
        cells = sorted(cells_by_row[row])
        first3 = [txt for _, txt in cells[:3]]
        row_text = " | ".join(t for t in first3 if t) or "（空行）"
        rid = ""
        role = ""
        pred = ""
        val = ""
        if feature:
            req_cells = [
                x
                for x in (feature.get("requirement_id_cells") or [])
                if isinstance(x, dict) and x.get("row_index") == row
            ]
            values = [text_of(x.get("value")) for x in req_cells]
            values = [v for v in values if v]
            if values:
                rid = values[0]
            roles = [
                text_of(x.get("role_candidate"))
                for x in (feature.get("row_roles") or [])
                if isinstance(x, dict) and x.get("row_index") == row
            ]
            roles = [r for r in roles if r]
            if roles:
                role = roles[0]
            params = [
                x
                for x in (feature.get("parameter_cells") or [])
                if isinstance(x, dict) and x.get("row_index") == row
            ]
            pred_keys: list[str] = []
            for p in params:
                key = text_of(p.get("predicate_key"))
                if key and key not in pred_keys:
                    pred_keys.append(key)
            if pred_keys:
                pred = "、".join(pred_keys)
            pvals = [text_of(p.get("value")) for p in params]
            pvals = [v for v in pvals if v]
            if pvals:
                val = "；".join(pvals)
        if not rid:
            rid = req_id_for_section(section, nodes_by_num)
        fields = {
            "rid": rid,
            "pred": pred,
            "op": "",
            "val": val,
            "unit": "",
            "modal": "、".join(extract_modals(row_text)),
            "neg": "",
            "cond": "",
            "ref": "",
            "ent": text_of(entities.get(rid)) if rid else "",
            "role": role,
            "scope": "",
        }
        src = f"{section}·{label}·行{row}"
        units.append({"k": "table_row", "sec": section, "src": src, "text": row_text, "f": fields})
    return units


def image_unit(
    block: dict[str, Any],
    section: str,
    nodes_by_num: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    caption = " ".join(
        str(c) for c in (block.get("image_caption") or []) if c
    ).strip()
    path = str(block.get("image_path") or block.get("img_path") or "")
    match = FIGURE_NO_RE.match(caption)
    if match:
        label = re.sub(r"\s+", "", match.group(1))
    elif path:
        label = Path(path).name
    else:
        label = "图"
    src = f"{section}·{label}" if section else label
    text = caption or "（无题注）"
    fields = {
        "rid": req_id_for_section(section, nodes_by_num),
        "pred": "",
        "op": "",
        "val": "",
        "unit": "",
        "modal": "、".join(extract_modals(text)),
        "neg": "",
        "cond": "",
        "ref": "",
        "ent": "",
        "role": "",
        "scope": "",
    }
    return {"k": "image", "sec": section, "src": src, "text": text, "f": fields}


def map_tables_to_blocks(
    blocks: list[dict[str, Any]], tables: list[dict[str, Any]]
) -> dict[int, dict[str, Any]]:
    """tables_v2表 → content_list表块索引: 优先页号+页内序对齐, 兜底全局顺序/题注."""
    if not tables:
        return {}
    block_indices = [i for i, b in enumerate(blocks) if b.get("type") == "table"]
    if not block_indices:
        return {}

    def page_of(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1

    if len(block_indices) == len(tables):
        block_pages: dict[int, list[int]] = {}
        for i in block_indices:
            block_pages.setdefault(page_of(blocks[i].get("page_idx")), []).append(i)
        table_pages: dict[int, list[int]] = {}
        for k, t in enumerate(tables):
            table_pages.setdefault(page_of(t.get("page")), []).append(k)
        if set(block_pages) == set(table_pages) and all(
            len(block_pages[p]) == len(table_pages.get(p, [])) for p in block_pages
        ):
            mapping: dict[int, dict[str, Any]] = {}
            for page, idxs in block_pages.items():
                for bi, ti in zip(idxs, table_pages[page]):
                    mapping[bi] = tables[ti]
            return mapping
        return dict(zip(block_indices, tables))

    def norm_caption(value: Any) -> str:
        return re.sub(r"\s+", "", str(value or ""))

    mapping = {}
    used: set[int] = set()
    for i in block_indices:
        cap = norm_caption(" ".join(str(c) for c in (blocks[i].get("table_caption") or [])))
        if not cap:
            continue
        for k, t in enumerate(tables):
            if k in used:
                continue
            if cap == norm_caption(t.get("caption_raw")):
                mapping[i] = t
                used.add(k)
                break
    rest_tables = [t for k, t in enumerate(tables) if k not in used]
    rest_blocks = [i for i in block_indices if i not in mapping]
    for bi, t in zip(rest_blocks, rest_tables):
        mapping[bi] = t
    return mapping


def compute_block_sections(blocks: list[dict[str, Any]]) -> list[str]:
    """每个块所处章节(扫描编号标题维护当前章节, 供图caption单元定位)."""
    sections: list[str] = []
    current = ""
    for block in blocks:
        if "text_level" in block:
            match = NUMBERED_SPLIT_RE.match(str(block.get("text", "")))
            if match:
                current = match.group(1)
        sections.append(current)
    return sections


def build_units(
    blocks: list[dict[str, Any]],
    feats: dict[str, Any],
    nodes_by_num: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Tab3全部提取单元, 按原文块顺序: 句子(块内按span排序)/表行/图caption."""
    sentences_by_block: dict[int, list[dict[str, Any]]] = {}
    for sentence in feats["sentences"]:
        span = sentence.get("span") or {}
        bi = span.get("block_idx")
        if isinstance(bi, int) and 0 <= bi < len(blocks):
            sentences_by_block.setdefault(bi, []).append(sentence)
    for lst in sentences_by_block.values():
        lst.sort(
            key=lambda s: (
                (s.get("span") or {}).get("start") or 0,
                text_of(s.get("claim_id")),
            )
        )
    slots = {text_of(r.get("claim_id")): r for r in feats["slots"]}
    predicates = {text_of(r.get("claim_id")): r for r in feats["predicates"]}
    refs: dict[str, list[dict[str, Any]]] = {}
    for row in feats["refs"]:
        refs.setdefault(text_of(row.get("claim_id")), []).append(row)
    entities = feats["entities"]
    tf_by_id = {text_of(r.get("table_id")): r for r in feats["table_features"]}
    tables_by_block = map_tables_to_blocks(blocks, feats["tables_v2"])
    block_sections = compute_block_sections(blocks)
    units: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks):
        kind = block.get("type")
        if kind == "text":
            for sentence in sentences_by_block.get(idx, []):
                units.append(
                    sentence_unit(sentence, slots, predicates, refs, entities, nodes_by_num)
                )
        elif kind == "table":
            t2 = tables_by_block.get(idx)
            if t2 is not None:
                units.extend(
                    table_row_units(
                        t2, tf_by_id.get(text_of(t2.get("table_id"))), entities, nodes_by_num
                    )
                )
        elif kind == "image":
            units.append(image_unit(block, block_sections[idx], nodes_by_num))
    return units


def compute_stats(
    units: list[dict[str, Any]], sentences: list[dict[str, Any]], refs: list[dict[str, Any]]
) -> dict[str, Any]:
    kinds = Counter(u["k"] for u in units)
    sections: list[str] = []
    seen: set[str] = set()
    for unit in units:
        sec = unit["sec"]
        if sec and sec not in seen:
            seen.add(sec)
            sections.append(sec)
    return {
        "unitsTotal": len(units),
        "sentenceUnits": kinds.get("sentence", 0),
        "tableRowUnits": kinds.get("table_row", 0),
        "imageUnits": kinds.get("image", 0),
        "predicateFilled": sum(1 for u in units if u["f"]["pred"]),
        "valueFilled": sum(1 for u in units if u["f"]["val"]),
        "valueWithUnit": sum(1 for u in units if u["f"]["val"] and u["f"]["unit"]),
        "conditionSentences": sum(1 for s in sentences if s.get("has_condition")),
        "refTotal": len(refs),
        "refResolved": sum(1 for r in refs if r.get("status") == "resolved"),
        "sections": sections,
    }


# ------------------------------------------------------------- payload装配

def image_mime(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        return "image/jpeg"
    if suffix == ".gif":
        return "image/gif"
    return "image/png"


def build_atlas_payload(
    doc_id: str,
    doc_name: str,
    blocks: list[dict[str, Any]],
    office_dir: Path,
    feats: dict[str, Any],
) -> dict[str, Any]:
    nodes = build_tree(blocks)
    nodes_by_num = {n["num"]: n for n in nodes}
    heading_rest_by_num: dict[str, str] = {}
    for block in blocks:
        if "text_level" not in block:
            continue
        match = NUMBERED_SPLIT_RE.match(str(block.get("text", "")))
        if match:
            num, rest = match.group(1), match.group(2).strip()
            heading_rest_by_num.setdefault(num, re.sub(r"[（(].*?[)）]\s*$", "", rest).strip())
    leaves = [n for n in nodes if not n["children"]]
    needed_images: set[str] = set()
    views: dict[str, dict[str, Any]] = {}
    matrix_leaves: list[dict[str, Any]] = []
    for node in leaves:
        ancestor_ids: set[str] = set()
        parent = node["parent"]
        while parent:
            parent_node = nodes_by_num.get(parent)
            if not parent_node:
                break
            ancestor_ids.add(parent_node["id"])
            parent = parent_node["parent"]
        capability = find_capability_rows(
            blocks, node, ancestor_ids, heading_rest_by_num, nodes_by_num
        )
        qualification = find_qualification(blocks, node)
        trace = find_trace(blocks, node)
        view = build_leaf_view(blocks, node, capability, qualification, trace, needed_images)
        views[node["num"]] = view
        matrix_leaves.append(
            {
                "num": node["num"],
                "short": node["short"],
                "id": node["id"],
                "states": [view["states"][key] for key, _ in ROUTES],
            }
        )

    images: dict[str, str] = {}
    for rel in sorted(needed_images):
        path = office_dir / rel
        if path.exists():
            data_uri = "data:" + image_mime(path) + ";base64," + base64.b64encode(
                path.read_bytes()
            ).decode("ascii")
            images[rel] = data_uri

    units = build_units(blocks, feats, nodes_by_num)
    stats = compute_stats(units, feats["sentences"], feats["refs"])

    route_stats = []
    for key, label in ROUTES:
        counts = {"direct": 0, "fallback": 0, "missing": 0}
        for lf in matrix_leaves:
            state = views[lf["num"]]["states"][key]
            counts[state] += 1
        route_stats.append({"key": key, "label": label, **counts})

    def missing_count(num: str) -> int:
        return sum(1 for key, _ in ROUTES if views[num]["states"][key] == "missing")

    broken_top = [
        {"num": n["num"], "short": n["short"], "id": n["id"], "missing": missing_count(n["num"])}
        for n in sorted(leaves, key=lambda n: (-missing_count(n["num"]), n["num"]))
        if missing_count(n["num"]) > 0
    ][:10]

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
    if "3.2.1.1.1.1" in views:
        default_leaf = "3.2.1.1.1.1"
    elif leaves:
        default_leaf = leaves[0]["num"]
    return {
        "doc": {"id": doc_id, "name": doc_name},
        "routes": [{"key": key, "label": label} for key, label in ROUTES],
        "matrix": {"leaves": matrix_leaves, "routeStats": route_stats, "brokenTop": broken_top},
        "tree": tree_children(roots),
        "defaultLeaf": default_leaf,
        "leaves": views,
        "images": images,
        "units": units,
        "stats": stats,
        "docBlocks": [
            {
                "i": i,
                "t": str(b.get("type", "")),
                "x": sanitize_fragment(str(b.get("text", "")))
                if b.get("type") == "text"
                else " ".join(str(c) for c in (b.get("table_caption") or b.get("image_caption") or []) if c),
                "h": int(b.get("text_level") or 0),
                "b": sanitize_fragment(str(b.get("table_body", "")))
                if b.get("type") == "table"
                else "",
                "p": str(b.get("image_path") or b.get("img_path") or "")
                if b.get("type") == "image"
                else "",
            }
            for i, b in enumerate(blocks)
        ],
    }


# ------------------------------------------------------------- HTML渲染

CSS = """
:root{
  --primary:#2f7ef4; --primary-dark:#1c62d0; --primary-light:#e8f1ff;
  --bg:#f4f6fa; --card:#fff; --line:#e6eaf0; --line2:#eef1f6;
  --txt:#1f2733; --txt2:#5a6473; --txt3:#98a1b0;
  --green:#12b76a; --green-bg:#e7f8f0; --orange:#f79009; --orange-bg:#fff5e6;
  --red:#f04438; --red-bg:#fdecec; --blue-bg:#eaf2ff; --purple:#7a5af8; --purple-bg:#f1eeff;
  --radius:6px; --shadow:0 1px 3px rgba(20,35,70,.06),0 6px 18px rgba(20,35,70,.04);
}
*{ box-sizing:border-box; margin:0; padding:0; }
body{ font-family:"Microsoft YaHei","PingFang SC","Helvetica Neue",Arial,sans-serif;
  background:var(--bg); color:var(--txt); font-size:13px; line-height:1.6; }
a{ color:var(--primary); text-decoration:none; }

/* ── 顶栏（照抄原型 topbar） ───────────────────────── */
header{ position:sticky; top:0; z-index:60; height:64px; background:#fff;
  border-bottom:1px solid var(--line); display:flex; align-items:center;
  padding:0 16px; flex-wrap:nowrap; gap:0; }
.logo{ width:32px; height:32px; border-radius:8px;
  background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:17px;
  font-weight:700; flex:0 0 auto; }
.logo-txt{ margin-left:9px; font-size:16px; font-weight:700; white-space:nowrap; }
.logo-txt small{ display:block; font-size:10.5px; color:var(--txt3);
  font-weight:400; letter-spacing:0; line-height:1.2; }
.tabs{ flex:1; display:flex; justify-content:flex-start; margin-left:22px;
  flex-wrap:nowrap; }
.tabbtn{ padding:0 14px; height:63px; display:flex; align-items:center; gap:5px;
  cursor:pointer; color:var(--txt); background:none; border:none;
  border-bottom:2px solid transparent; border-top:none; border-left:none;
  border-right:none; white-space:nowrap; font-size:14px; font-family:inherit;
  position:relative; flex:0 0 auto; }
.tabbtn:hover{ color:var(--primary); background:var(--bg); }
.tabbtn.active{ color:var(--primary); border-bottom-color:var(--primary);
  font-weight:600; }
.doc-name{ margin-left:auto; padding:3px 11px; border-radius:11px;
  background:var(--primary-light); color:var(--primary); font-size:12px;
  white-space:nowrap; border:1px solid #cfe1ff; }

/* ── 面包屑 ───────────────────────── */
.tbar{ display:flex; align-items:center; gap:14px; color:var(--txt3);
  font-size:12px; margin:14px 24px 0; flex-wrap:wrap; }
.tbar b{ color:var(--txt2); font-weight:400; }

/* ── 卡片（原型 card） ───────────────────────── */
.card{ background:var(--card); border:1px solid var(--line); border-radius:8px;
  box-shadow:var(--shadow); margin:0 24px 14px; overflow:hidden; }
.cbody{ padding:14px 16px; }
.cbody.np{ padding:0; }
.panel-note{ background:var(--blue-bg); border:1px solid #cfe1ff; color:#2b5fbd;
  padding:9px 12px; border-radius:var(--radius); margin:12px 16px 0;
  display:flex; gap:8px; align-items:flex-start; font-size:12px; }
.panel-note.warn{ background:var(--orange-bg); border-color:#ffe0b2; color:#a35c00; }

/* ── 统计卡（原型 stats） ───────────────────────── */
.tstats,.mx-stats{ display:grid;
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px;
  margin:14px 24px; }
.tstats>div,.mx-stats>div{ background:#fff; border:1px solid var(--line);
  border-radius:8px; padding:13px 15px; box-shadow:var(--shadow); }
.tstats .k,.mx-stats .k{ font-size:12px; color:var(--txt2);
  display:flex; align-items:center; gap:6px; }
.tstats .v,.mx-stats .v{ font-size:23px; font-weight:700; margin-top:5px;
  letter-spacing:.5px; }
.tstats small,.mx-stats small{ font-size:12px; font-weight:400;
  color:var(--txt3); margin-left:3px; }
.tstats .v.g,.mx-stats .v.g{ color:var(--green); }
.tstats .v.o,.mx-stats .v.o{ color:var(--orange); }
.tstats .v.r,.mx-stats .v.r{ color:var(--red); }
.tstats .v.b,.mx-stats .v.b{ color:var(--primary); }

/* ── 状态点 ───────────────────────── */
.dot{ display:inline-block; width:9px; height:9px; border-radius:50%;
  vertical-align:middle; }
.st-direct{ background:var(--green); }
.st-fallback{ background:var(--orange); }
.st-missing{ background:none; border:2px solid var(--red); width:8px; height:8px; }

/* ── 追溯矩阵 ───────────────────────── */
.mx-grid{ display:grid; font-size:12.5px; }
.mx-h{ background:#f7f9fc; padding:9px 10px; font-weight:600; color:var(--txt2);
  border-bottom:1px solid var(--line2); display:flex; align-items:center;
  justify-content:center; text-align:center; font-size:12px; position:sticky;
  top:64px; z-index:5; }
.mx-corner{ background:#f7f9fc; border-bottom:1px solid var(--line2);
  border-right:1px solid var(--line2); position:sticky; left:0; z-index:6;
  padding:9px 12px; font-size:12px; color:var(--txt3); display:flex;
  align-items:center; position:sticky; top:64px; }
.mx-cell{ padding:8px 10px; border-bottom:1px solid var(--line2);
  display:flex; align-items:center; justify-content:center;
  cursor:pointer; transition:.12s; }
.mx-cell:hover{ background:var(--primary-light); }
.mx-rowlabel{ padding:8px 12px; border-bottom:1px solid var(--line2);
  border-right:1px solid var(--line2); background:#fff; position:sticky;
  left:0; z-index:4; min-width:210px; display:flex; flex-direction:column;
  gap:1px; }
.mx-rowlabel .mx-num{ color:var(--primary); font-weight:600; font-size:12px; }
.mx-rowlabel .mx-id{ color:var(--txt3); font-size:10.5px;
  font-family:Consolas,monospace; }
.mx-rowlabel.leaf{ cursor:pointer; }
.mx-rowlabel.leaf:hover{ background:var(--primary-light); }
.mx-rowlabel.active{ background:var(--primary-light); }

/* ── 档案布局 ───────────────────────── */
.dossier-layout{ display:flex; gap:14px; align-items:flex-start;
  margin:14px 24px; }
.dossier-layout .u-left{ width:270px; flex:0 0 auto; }
.dossier-layout .u-right{ flex:1; min-width:0; }

/* ── 树（原型 tree-i） ───────────────────────── */
.tree{ background:#fff; border:1px solid var(--line); border-radius:8px;
  box-shadow:var(--shadow); padding:6px; max-height:calc(100vh - 96px);
  overflow:auto; position:sticky; top:78px; }
.tree .bt-item{ padding:7px 11px; border-radius:var(--radius); cursor:pointer;
  display:flex; align-items:center; justify-content:space-between;
  margin-bottom:2px; color:var(--txt2); font-size:12.5px; }
.tree .bt-item:hover{ background:var(--bg); color:var(--txt); }
.tree .bt-item.active{ background:var(--primary-light); color:var(--primary);
  font-weight:600; }
.tree .bt-item .cd{ font-size:11px; color:var(--txt3); padding:1px 6px;
  background:var(--bg); border-radius:9px; }
.tree .bt-item.active .cd{ background:#fff; color:var(--primary); }
.tree .bt-item.hidden{ display:none; }
.lv-title{ font-weight:600; }
.lv-meta{ color:var(--txt3); font-size:10.5px; }

/* ── 档案证据卡片 ───────────────────────── */
.card .cardhd{ padding:12px 16px; border-bottom:1px solid var(--line2);
  display:flex; align-items:center; justify-content:space-between; gap:10px;
  flex-wrap:wrap; background:#fff; }
.card .cardhd h3{ font-size:14px; font-weight:600; display:flex;
  align-items:center; gap:7px; color:var(--txt); }
.card .cardhd h3::before{ content:''; width:3px; height:13px;
  background:var(--primary); border-radius:2px; }
.cardhd .tag,.tag{ display:inline-flex; align-items:center; gap:3px;
  height:21px; padding:0 9px; border-radius:11px; font-size:11.5px;
  background:var(--bg); color:var(--txt2); border:1px solid var(--line);
  white-space:nowrap; }
.tag.g{ background:var(--green-bg); color:var(--green);
  border-color:#bfe9d4; }
.tag.o{ background:var(--orange-bg); color:var(--orange);
  border-color:#ffe0b2; }
.tag.r{ background:var(--red-bg); color:var(--red);
  border-color:#f6c7c3; }
.tag.b{ background:var(--blue-bg); color:var(--primary);
  border-color:#cfe1ff; }
.tag.p{ background:var(--purple-bg); color:var(--purple);
  border-color:#ddd3fa; }

/* ── 原文片段 ───────────────────────── */
.orig{ padding:12px 16px; font-size:13px; line-height:1.8; color:var(--txt);
  background:#fff; }
.orig-list{ padding:6px 16px 10px; }
.orig-list .row-entry{ padding:7px 0; border-bottom:1px solid var(--line2);
  font-size:13px; line-height:1.7; }
.orig-list .row-entry:last-child{ border-bottom:none; }
.row-meta{ color:var(--txt3); font-size:11px; margin-bottom:2px;
  display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.row-label{ color:var(--txt3); }
.tbl-wrap{ padding:0 16px 14px; overflow:auto; }
.tbl-wrap table{ border-collapse:collapse; width:100%; font-size:12px;
  background:#fff; }
.tbl-wrap th{ background:#f7f9fc; color:var(--txt2); font-weight:600;
  padding:7px 9px; border:1px solid var(--line); text-align:left; }
.tbl-wrap td{ padding:7px 9px; border:1px solid var(--line2);
  color:var(--txt); vertical-align:top; line-height:1.6; }
.tbl-wrap tr:hover td{ background:#f9fbff; }
.tbl-cap{ padding:10px 16px 6px; color:var(--txt2); font-size:12.5px;
  font-weight:600; }
.fig{ padding:8px 16px 14px; text-align:center; }
.fig img{ max-width:100%; border-radius:6px; border:1px solid var(--line2);
  box-shadow:var(--shadow); }
.fig .fig-cap{ margin-top:7px; color:var(--txt3); font-size:11.5px; }
.noext{ padding:14px 16px; color:var(--txt3); font-size:12.5px;
  background:var(--bg); border-radius:var(--radius); }

/* ── 逐句对照 ───────────────────────── */
.uhead{ display:flex; gap:2px; position:sticky; top:64px; background:#fff;
  z-index:6; border-bottom:1px solid var(--line); }
.uhead .u-src{ flex:0 0 44%; }
.uhead .u-text{ flex:1; }
.uhead>div{ background:#f7f9fc; padding:9px 14px; font-weight:600;
  color:var(--txt2); font-size:12.5px; border-right:1px solid var(--line2); }
.urow{ display:flex; border-bottom:1px solid var(--line2); }
.urow:nth-child(even){ background:#fbfcfe; }
.urow:hover{ background:var(--blue-bg); }
.u-src{ flex:0 0 44%; padding:10px 14px; display:flex;
  flex-direction:column; gap:2px; border-right:1px solid var(--line2); }
.u-text{ flex:1; min-width:0; }
.u-text .u-line{ padding:10px 14px; font-size:13px; line-height:1.75; }
.fld{ display:grid; grid-template-columns:repeat(auto-fill,minmax(118px,1fr));
  gap:4px; padding:0 14px 10px; }
.fld>div{ background:#f8fafd; border:1px solid var(--line2);
  border-radius:5px; padding:4px 8px; min-width:0; }
.fld .rs-label{ display:block; font-size:10.5px; color:var(--txt3);
  line-height:1.3; }
.fld .rs-row{ font-size:12px; color:var(--txt); line-height:1.45;
  word-break:break-all; }
.fld .rs-row.none{ color:var(--txt3); }
.fld .rs-row.hit{ color:var(--primary); font-weight:600; }
.rs-row.miss{ color:#c3cad6; }

/* ── 匹配详情 ───────────────────────── */
.row-match{ background:var(--green-bg); border:1px solid #bfe9d4;
  color:#0b8a55; border-radius:5px; padding:4px 8px; font-size:11.5px; }
.row-match.fb{ background:var(--orange-bg); border-color:#ffe0b2;
  color:#a35c00; }
.row-match.miss{ background:var(--red-bg); border-color:#f6c7c3;
  color:#c0392b; }

/* ── Tab 面板 ───────────────────────── */
.tabpanel{ display:none; }
.tabpanel.active{ display:block; }
.tabpanel .card:first-child{ margin-top:0; }

/* ── 滚动条 ───────────────────────── */
::-webkit-scrollbar{ width:9px; height:9px; }
::-webkit-scrollbar-thumb{ background:#cfd6e0; border-radius:5px; }
::-webkit-scrollbar-thumb:hover{ background:#aeb8c6; }
::-webkit-scrollbar-track{ background:transparent; }

/* ═══ Tab2 需求档案：原文框 + 径向图谱 ═══ */
.dossier-layout{ display:flex; gap:14px; margin:14px 24px; align-items:stretch; }
.docpane-card{ width:46%; flex:0 0 auto; min-width:0; }
.docp-bar{ display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.docp-sel{ height:30px; border:1px solid var(--line); border-radius:var(--radius);
  padding:0 10px; font-size:12.5px; color:var(--txt); background:#fff; font-family:inherit;
  outline:none; width:100%; }
.docp-sel:focus{ border-color:var(--primary); box-shadow:0 0 0 2px rgba(47,126,244,.12); }
.docp-crumb{ font-size:12px; color:var(--txt2); margin-bottom:8px; padding:0 2px;
  display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.docp-crumb b{ color:var(--primary); font-weight:600; font-family:Consolas,monospace; }
.docp-id{ font-family:Consolas,monospace; font-size:10.5px; color:var(--txt3); }
.docpane{ background:#fff; border:1px solid var(--line); border-radius:8px;
  box-shadow:var(--shadow); padding:24px 28px 20px;
  max-height:calc(100vh - 210px); overflow:auto;
  font-size:13.5px; line-height:2.0; color:var(--txt); }
.docp-lead{ font-weight:600; font-size:15px; line-height:1.7; margin-bottom:6px; }
.docp-p{ margin:9px 0; text-indent:2em; }
.docp-ul{ margin:9px 0 9px 2em; }
.docp-ul li{ margin:4px 0; }
.docp-cap{ font-weight:600; font-size:12.5px; color:var(--txt2); margin:14px 0 6px; }
.docp-tbl table{ border-collapse:collapse; width:100%; font-size:12px; }
.docp-tbl th{ background:#f7f9fc; padding:7px 9px; border:1px solid var(--line); font-weight:600; }
.docp-tbl td{ padding:7px 9px; border:1px solid var(--line2); vertical-align:top; line-height:1.6; }
.docp-fig{ margin:14px 0; text-align:center; }
.docp-fig img{ max-width:100%; border-radius:6px; border:1px solid var(--line2); box-shadow:var(--shadow); }
.docp-fig figcaption{ margin-top:6px; color:var(--txt3); font-size:11.5px; }
.docp-empty{ color:var(--txt3); }
.graphside{ flex:1; min-width:0; display:flex; flex-direction:column; gap:14px; }
.graph-card{ padding:10px 8px 4px; }
.graph-card svg{ width:100%; height:auto; display:block; }
.detail-card .cbody{ max-height:calc(100vh - 560px); overflow:auto; }
/* 径向图元素 */
.rg-ring{ fill:none; stroke:var(--line2); stroke-dasharray:3 5; }
.rg-edge{ stroke:var(--line); stroke-width:1.5; }
.rg-edge.rg-e-direct{ stroke:var(--green); }
.rg-edge.rg-e-fallback{ stroke:var(--orange); stroke-dasharray:4 3; }
.rg-edge.rg-e-missing{ stroke:var(--red); stroke-dasharray:2 3; }
.rg-node rect{ fill:#fff; stroke:var(--line); cursor:pointer; transition:.14s; }
.rg-node:hover rect{ stroke:var(--primary); fill:var(--primary-light); }
.rg-node.on rect{ stroke:var(--primary); stroke-width:2; fill:var(--primary-light); }
.rg-label{ font-size:12.5px; font-weight:600; fill:var(--txt); }
.rg-node.on .rg-label{ fill:var(--primary); }
.rg-sub{ font-size:9.5px; fill:var(--txt3); }
.rg-dot.rg-d-direct{ fill:var(--green); }
.rg-dot.rg-d-fallback{ fill:var(--orange); }
.rg-dot.rg-d-missing{ fill:#fff; stroke:var(--red); stroke-width:1.6; }
.rg-center rect{ fill:var(--primary-light); stroke:var(--primary); stroke-width:1.6; }
.rg-c-num{ font-size:12px; font-weight:700; fill:var(--primary); text-anchor:middle;
  font-family:Consolas,monospace; }
.rg-c-name{ font-size:11px; fill:var(--txt2); text-anchor:middle; }

/* ═══ Tab2 doc原文定位与特征预览 ═══ */
#doc-pane .located{ box-shadow:inset 3px 0 0 var(--primary); background:#f6faff; }
#doc-pane .flash{ box-shadow:inset 3px 0 0 var(--orange); background:var(--orange-bg); }
.docp-h{ font-weight:600; font-size:14px; margin:18px 0 6px; line-height:1.7; }
.docp-h1{ font-size:16px; } .docp-h2{ font-size:15px; }
.docp-h3,.docp-h4,.docp-h5,.docp-h6{ font-size:13.5px; color:var(--txt2); }
.docp-blk{ font-family:Consolas,monospace; font-size:10px; color:var(--txt3); }
.docp-img-miss{ display:inline-block; padding:14px; color:var(--txt3);
  background:var(--bg); border-radius:6px; font-size:12px; }
.rg-legend{ display:flex; gap:14px; align-items:center; padding:6px 14px 10px;
  color:var(--txt2); font-size:11.5px; flex-wrap:wrap; }
.rg-legend .dot{ width:8px; height:8px; }
.rg-legend span{ display:inline-flex; gap:5px; align-items:center; }
.lg-tip{ color:var(--txt3); margin-left:auto; font-size:11px; }
.fp-row{ padding:8px 0; border-bottom:1px solid var(--line2); }
.fp-row:last-child{ border-bottom:none; }
.fp-src{ color:var(--txt3); font-size:10.5px; margin-bottom:2px; }
.fp-text{ font-size:12.5px; color:var(--txt); line-height:1.6; }
.fp-pills{ margin-top:4px; display:flex; gap:5px; flex-wrap:wrap; }
.fp-pills .tag{ height:19px; font-size:10.5px; padding:0 7px; }
.fp-none{ color:var(--txt3); font-size:11px; }
.fp-more{ color:var(--txt3); font-size:11.5px; padding:8px 0 2px; text-align:center; }
.fp-body{ max-height:300px; overflow:auto; }
.graphside{ flex:1; min-width:0; display:flex; flex-direction:column; gap:14px; }
.detail-card .cbody{ max-height:320px; overflow:auto; }
"""

JS = """
const DATA = JSON.parse(document.getElementById('atlas-data').textContent);
const FIELDS = [['rid','需求ID'],['pred','谓词'],['op','操作符'],['val','值'],['unit','单位'],
  ['modal','模态词'],['neg','否定词'],['cond','条件'],['ref','引用→目标'],['ent','实体类型'],
  ['role','行角色'],['scope','scope实体']];
const state = { leaf: DATA.defaultLeaf };

function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}
function dotHtml(st) {
  const ch = st === 'direct' ? '●' : (st === 'fallback' ? '◑' : '○');
  return '<span class="dot st-' + st + '">' + ch + '</span>';
}
function showTab(id) {
  document.querySelectorAll('.tabbtn').forEach((b) => {
    b.classList.toggle('active', b.getAttribute('data-tab') === id);
  });
  document.querySelectorAll('.tabpanel').forEach((p) => {
    p.classList.toggle('active', p.id === id);
  });
}
document.querySelectorAll('.tabbtn').forEach((b) => {
  b.addEventListener('click', () => showTab(b.getAttribute('data-tab')));
});

// ---------------- Tab1 追溯矩阵
function renderMatrix() {
  const routes = DATA.routes;
  let html = '<div class="mx-grid">';
  html += '<div class="mx-h mx-corner">需求＼证据</div>';
  routes.forEach((r) => { html += '<div class="mx-h">' + esc(r.label) + '</div>'; });
  DATA.matrix.leaves.forEach((lf) => {
    html += '<div class="mx-rowlabel" data-num="' + esc(lf.num)
      + '" title="' + esc(lf.num + ' ' + lf.id) + '"><span class="mx-num">'
      + esc(lf.num) + '</span>' + esc(lf.short)
      + ' <span class="mx-id">' + esc(lf.id) + '</span></div>';
    lf.states.forEach((st, i) => {
      const view = DATA.leaves[lf.num];
      const title = routes[i].label + '：' + (view ? view.details[routes[i].key] : '');
      html += '<div class="mx-cell" data-num="' + esc(lf.num) + '" title="'
        + esc(title) + '">' + dotHtml(st) + '</div>';
    });
  });
  html += '</div>';
  document.getElementById('mx-grid').innerHTML = html;
  document.getElementById('mx-routes').innerHTML = DATA.matrix.routeStats.map((r) =>
    '<div class="rs-row"><span class="rs-label">' + esc(r.label) + '</span>'
    + '<span class="st-direct">●直接 ' + r.direct + '</span>'
    + '<span class="st-fallback">◑回退 ' + r.fallback + '</span>'
    + '<span class="st-missing">○缺失 ' + r.missing + '</span></div>').join('');
  document.getElementById('mx-broken').innerHTML = DATA.matrix.brokenTop.map((b) =>
    '<span class="bt-item">' + esc(b.num) + ' ' + esc(b.short)
    + '（缺' + b.missing + '路）</span>').join('') || '无断链';
}
document.getElementById('mx-grid').addEventListener('click', (ev) => {
  const cell = ev.target.closest('[data-num]');
  if (!cell) { return; }
  openDossier(cell.getAttribute('data-num'));
});

// ---------------- Tab2 需求档案
function treeHtml(nodes) {
  return '<ul class="tree">' + nodes.map((n) => n.leaf
    ? '<li class="leaf' + (n.num === state.leaf ? ' active' : '') + '" data-num="' + esc(n.num)
      + '"><span class="tnum">' + esc(n.num) + '</span>' + esc(n.name)
      + ' <span class="tid">' + esc(n.id) + '</span></li>'
    : '<li class="branch"><details open><summary><span class="tnum">' + esc(n.num)
      + '</span>' + esc(n.name) + ' <span class="tid">' + esc(n.id) + '</span></summary>'
      + treeHtml(n.children) + '</details></li>').join('') + '</ul>';
}
function missingBox(msg) { return '<div class="missing">' + esc(msg) + '</div>'; }
function rowEntriesHtml(found, key) {
  const emptyMsg = {
    capability: '未在能力标识表(caption含"能力")中找到本需求的行(含上级回退)',
    qualification: '未在第4章合格性表中找到章节号匹配行(含上级回退)',
    trace: '未在第5章追溯表中找到匹配行(含上级回退)'
  }[key];
  if (!found || !found.entries || !found.entries.length) {
    return missingBox(emptyMsg);
  }
  return found.entries.map((en) =>
    '<div class="row-entry"><div class="row-meta"><span class="row-label">'
    + esc(en.label || '（无题注）') + '</span>'
    + (en.match ? '<span class="row-match">匹配：' + esc(en.match) + '</span>' : '')
    + (en.fallback_of ? '<span class="row-fb">回退：上级' + esc(en.fallback_of) + '的行</span>' : '')
    + '</div><div class="tbl-wrap"><table>' + en.header + en.rows.join('')
    + '</table></div></div>').join('');
}
function cardHtml(route, leaf) {
  const st = leaf.states[route.key];
  const detail = leaf.details[route.key] || '';
  let body = '';
  if (route.key === 'body') {
    body = leaf.body.map((fr) => fr.t === 'ul'
      ? '<ul class="orig-list">' + fr.items.map((i) => '<li>' + i + '</li>').join('') + '</ul>'
      : '<p class="orig">' + fr.h + '</p>').join('');
    if (!body) { body = missingBox('区间内无正文文字块'); }
  } else if (route.key === 'usecase') {
    body = leaf.usecases.map((u) => '<div class="tbl-cap">'
      + esc(u.caption || '（无题注）') + '</div><div class="tbl-wrap">' + u.html + '</div>').join('');
    if (!body) { body = missingBox('区间内无用例表'); }
  } else if (route.key === 'flow') {
    body = leaf.images.map((im) => {
      const src = DATA.images[im.path];
      if (src) {
        return '<figure class="fig"><img src="' + src + '" alt="' + esc(im.caption)
          + '" loading="lazy"><figcaption>' + esc(im.caption || '（无题注）') + '</figcaption></figure>';
      }
      return missingBox('图片文件缺失：' + (im.path || '（无路径）'));
    }).join('');
    if (!body) { body = missingBox('区间内无图片'); }
  } else {
    body = rowEntriesHtml(leaf[route.key], route.key);
  }
  return '<section class="card"><header>' + dotHtml(st) + '<b>' + esc(route.label)
    + '</b><span class="cd">' + esc(detail) + '</span></header><div class="cbody">'
    + body + '</div></section>';
}
function renderDocPane() {
  const pane = [];
  DATA.docBlocks.forEach((b) => {
    if (b.t === 'text') {
      if (!b.x) { return; }
      if (b.h > 0) {
        pane.push('<div class="docp-h docp-h' + Math.min(b.h, 6) + '" id="blk-' + b.i + '">' + b.x + '</div>');
      } else {
        pane.push('<p class="docp-p" id="blk-' + b.i + '">' + b.x + '</p>');
      }
    } else if (b.t === 'table') {
      pane.push('<div class="docp-cap" id="blk-' + b.i + '">' + esc(b.x || '') + '</div>'
        + '<div class="docp-tbl">' + (b.b || '') + '</div>');
    } else if (b.t === 'image') {
      const src = DATA.images[b.p];
      pane.push('<figure class="docp-fig" id="blk-' + b.i + '">'
        + (src ? '<img src="' + src + '" loading="lazy" alt="' + esc(b.x) + '">'
          : '<span class="docp-img-miss">[图片未嵌入]</span>')
        + '<figcaption>' + esc(b.x || '') + '</figcaption></figure>');
    }
  });
  document.getElementById('doc-pane').innerHTML = pane.join('');
}
function clearLocated() {
  document.querySelectorAll('#doc-pane .located').forEach((el) => el.classList.remove('located'));
  document.querySelectorAll('#doc-pane .flash').forEach((el) => el.classList.remove('flash'));
}
function scrollToBlk(idx, flash) {
  const el = document.getElementById('blk-' + idx);
  if (!el) { return; }
  clearLocated();
  if (flash) {
    el.classList.add('flash');
  } else {
    el.classList.add('located');
  }
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
function selectLeaf(num) {
  const leaf = DATA.leaves[num];
  if (!leaf) { return; }
  state.leaf = num;
  state.route = state.route || 'body';
  const picker = document.getElementById('leaf-picker');
  if (picker && picker.value !== num) { picker.value = num; }
  document.getElementById('docp-crumb').innerHTML =
    '<b>' + esc(leaf.num) + '</b> ' + esc(String(leaf.title).split('（')[0])
    + ' <span class="docp-id">' + esc(leaf.id) + '</span>'
    + ' <span class="docp-blk">块#' + leaf.blockStart + '–' + leaf.blockEnd + '</span>';
  // 左侧原文：整区间定位标记（不涂改文字）
  clearLocated();
  for (let i = leaf.blockStart; i < leaf.blockEnd; i++) {
    const el = document.getElementById('blk-' + i);
    if (el) { el.classList.add('located'); }
  }
  const first = document.getElementById('blk-' + leaf.blockStart);
  if (first) { first.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  drawRouteGraph(leaf);
  renderFeaturePane(leaf);
  showRouteDetail(state.route, leaf);
}
function renderFeaturePane(leaf) {
  const rows = DATA.units.filter((u) => {
    const s = u.sec || '';
    return s === leaf.num || s.indexOf(leaf.num + '.') === 0;
  });
  let inner;
  if (!rows.length) {
    inner = '<div class="noext">该需求区间内无已提取的结构化单元（句子/表行/图注）</div>';
  } else {
    inner = rows.slice(0, 30).map((u) => {
      const f = u.f || {};
      const pills = FIELDS.filter((p) => f[p[0]])
        .slice(0, 8)
        .map((p) => '<span class="tag b" title="' + esc(p[1]) + '">'
          + esc(String(f[p[0]]).slice(0, 24)) + '</span>')
        .join('');
      return '<div class="fp-row"><div class="fp-src">' + esc(u.src) + '</div>'
        + '<div class="fp-text">' + esc(String(u.text).slice(0, 90))
        + (String(u.text).length > 90 ? '…' : '') + '</div>'
        + '<div class="fp-pills">' + (pills || '<span class="fp-none">无字段</span>') + '</div></div>';
    }).join('');
    if (rows.length > 30) {
      inner += '<div class="fp-more">仅显示前30条，共' + rows.length + '条</div>';
    }
  }
  document.getElementById('feature-pane').innerHTML =
    '<div class="cardhd"><h3>结构化提取预览</h3>'
    + '<span class="tag">' + rows.length + '个提取单元</span></div>'
    + '<div class="cbody fp-body">' + inner + '</div>';
}
function drawRouteGraph(leaf) {
  const cx = 220, cy = 180, r = 122;
  const order = ['body', 'usecase', 'flow', 'capability', 'qualification', 'trace'];
  const labels = {
    body: '正文', usecase: '用例表', flow: '流程图',
    capability: '能力表行', qualification: '合格性行', trace: '追溯行',
  };
  let g = '<circle cx="' + cx + '" cy="' + cy + '" r="' + r + '" class="rg-ring"/>';
  order.forEach((key, i) => {
    const a = -Math.PI / 2 + i * (Math.PI / 3);
    const x = cx + r * Math.cos(a);
    const y = cy + r * Math.sin(a);
    const st = leaf.states[key];
    g += '<line x1="' + cx + '" y1="' + cy + '" x2="' + x + '" y2="' + y
      + '" class="rg-edge rg-e-' + st + '"/>';
  });
  order.forEach((key, i) => {
    const a = -Math.PI / 2 + i * (Math.PI / 3);
    const x = cx + r * Math.cos(a);
    const y = cy + r * Math.sin(a);
    const st = leaf.states[key];
    const on = state.route === key;
    g += '<g class="rg-node' + (on ? ' on' : '') + '" data-key="' + key + '">'
      + '<rect x="' + (x - 40) + '" y="' + (y - 19) + '" width="80" height="38" rx="8"/>'
      + '<circle cx="' + (x - 27) + '" cy="' + (y - 7) + '" r="4.5" class="rg-dot rg-d-' + st + '"/>'
      + '<text x="' + (x - 17) + '" y="' + (y - 3) + '" class="rg-label">' + labels[key] + '</text>'
      + '<text x="' + (x - 27) + '" y="' + (y + 12) + '" class="rg-sub">'
      + (st === 'direct' ? '直接命中' : st === 'fallback' ? '回退上级' : '缺失') + '</text>'
      + '</g>';
  });
  const name = esc(String(leaf.title).split('（')[0]).slice(0, 12);
  g += '<g class="rg-center">'
    + '<rect x="' + (cx - 62) + '" y="' + (cy - 26) + '" width="124" height="52" rx="10"/>'
    + '<text x="' + cx + '" y="' + (cy - 6) + '" class="rg-c-num">' + esc(leaf.num) + '</text>'
    + '<text x="' + cx + '" y="' + (cy + 12) + '" class="rg-c-name">' + name + '</text>'
    + '</g>';
  document.getElementById('route-graph').innerHTML = g;
}
function showRouteDetail(key, leafArg) {
  const leaf = leafArg || DATA.leaves[state.leaf];
  if (!leaf) { return; }
  state.route = key;
  // 左侧原文定位：正文→区间首块；用例表/流程图→对应块
  if (key === 'body') {
    scrollToBlk(leaf.blockStart, false);
  } else if (key === 'usecase' && leaf.usecases && leaf.usecases.length) {
    scrollToBlk(leaf.usecases[0].blk, true);
  } else if (key === 'flow' && leaf.images && leaf.images.length) {
    scrollToBlk(leaf.images[0].blk, true);
  }
  const route = DATA.routes.filter((r) => r.key === key)[0] || { key: key, label: key };
  document.getElementById('route-detail').innerHTML =
    '<div class="cardhd"><h3>' + esc(route.label) + '证据</h3>'
    + '<span class="tag ' + (leaf.states[key] === 'direct' ? 'g' : leaf.states[key] === 'fallback' ? 'o' : 'r') + '">'
    + (leaf.states[key] === 'direct' ? '直接命中' : leaf.states[key] === 'fallback' ? '回退上级' : '缺失')
    + '</span><span class="cd">' + esc(leaf.details[key] || '') + '</span></div>'
    + '<div class="cbody">' + routeBody(key, leaf) + '</div>';
  drawRouteGraph(leaf);
}
function routeBody(key, leaf) {
  if (key === 'body') {
    const h = leaf.body.map((fr) => fr.t === 'ul'
      ? '<ul class="orig-list">' + fr.items.map((i) => '<li>' + i + '</li>').join('') + '</ul>'
      : '<p class="orig">' + fr.h + '</p>').join('');
    return h || missingBox('区间内无正文文字块');
  }
  if (key === 'usecase') {
    const h = leaf.usecases.map((u) => '<div class="tbl-cap">' + esc(u.caption || '（无题注）')
      + '</div><div class="tbl-wrap">' + u.html + '</div>').join('');
    return h || missingBox('区间内无用例表');
  }
  if (key === 'flow') {
    const h = leaf.images.map((im) => {
      const src = DATA.images[im.path];
      if (src) {
        return '<figure class="fig"><img src="' + src + '" alt="' + esc(im.caption)
          + '" loading="lazy"><figcaption>' + esc(im.caption || '（无题注）') + '</figcaption></figure>';
      }
      return missingBox('图片文件缺失：' + (im.path || '（无路径）'));
    }).join('');
    return h || missingBox('区间内无图片');
  }
  return rowEntriesHtml(leaf[key], key);
}
document.getElementById('route-graph').addEventListener('click', (ev) => {
  const node = ev.target.closest('.rg-node');
  if (!node) { return; }
  showRouteDetail(node.getAttribute('data-key'));
});
(function setupPicker() {
  const picker = document.getElementById('leaf-picker');
  const nums = Object.keys(DATA.leaves).sort();
  nums.forEach((n) => {
    const leaf = DATA.leaves[n];
    picker.appendChild(new Option(n + ' ' + String(leaf.title).split('（')[0], n));
  });
  picker.addEventListener('change', () => selectLeaf(picker.value));
})();
function openDossier(num) {
  showTab('tab2');
  selectLeaf(num);
}
function countNodes(nodes) {
  return nodes.reduce((acc, n) => acc + 1 + countNodes(n.children), 0);
}
function countLeaves(nodes) {
  return nodes.reduce((acc, n) => acc + (n.leaf ? 1 : countLeaves(n.children)), 0);
}

// ---------------- Tab3 逐句对照
function renderUnits() {
  let html = '';
  DATA.units.forEach((u) => {
    const f = u.f || {};
    const hasAny = FIELDS.some((p) => f[p[0]]);
    let right;
    if (!hasAny) {
      right = '<div class="noext">（无提取）</div>';
    } else {
      right = '<dl class="fld">' + FIELDS.map((p) => {
        const v = f[p[0]];
        return '<dt>' + esc(p[1]) + '</dt><dd>'
          + (v ? esc(v) : '<span class="none">—</span>') + '</dd>';
      }).join('') + '</dl>';
    }
    html += '<div class="urow" data-sec="' + esc(u.sec) + '" data-rid="' + esc(f.rid || '')
      + '" data-pred="' + (f.pred ? 1 : 0) + '" data-val="' + (f.val ? 1 : 0) + '">'
      + '<div class="u-left"><div class="u-src">' + esc(u.src) + '</div><div class="u-text">'
      + esc(u.text) + '</div></div>'
      + '<div class="u-right">' + right + '</div></div>';
  });
  document.getElementById('urows').innerHTML = html;
}
const secSel = document.getElementById('sec-filter');
const ridInput = document.getElementById('rid-filter');
const predChk = document.getElementById('only-pred');
const valChk = document.getElementById('only-val');
function setupFilters() {
  secSel.appendChild(new Option('全部', '全部'));
  DATA.stats.sections.forEach((s) => secSel.appendChild(new Option(s, s)));
  secSel.value = DATA.stats.sections.indexOf('3.2') >= 0 ? '3.2' : '全部';
  [secSel, ridInput, predChk, valChk].forEach((el) => {
    el.addEventListener('input', applyFilters);
    el.addEventListener('change', applyFilters);
  });
}
function applyFilters() {
  const sec = secSel.value;
  const rid = ridInput.value.trim().toUpperCase();
  const onlyPred = predChk.checked;
  const onlyVal = valChk.checked;
  let vis = 0;
  document.querySelectorAll('#urows .urow').forEach((row) => {
    let ok = true;
    if (sec !== '全部') {
      const s = row.getAttribute('data-sec');
      ok = s === sec || (s && s.indexOf(sec + '.') === 0);
    }
    if (ok && rid) { ok = (row.getAttribute('data-rid') || '').toUpperCase().indexOf(rid) >= 0; }
    if (ok && onlyPred) { ok = row.getAttribute('data-pred') === '1'; }
    if (ok && onlyVal) { ok = row.getAttribute('data-val') === '1'; }
    row.classList.toggle('hidden', !ok);
    if (ok) { vis += 1; }
  });
  document.getElementById('vis-count').textContent = '显示 ' + vis + ' / '
    + DATA.stats.unitsTotal + ' 行';
}
function pct(a, b) { return b ? (100 * a / b).toFixed(1) + '%' : '—'; }
function renderStats() {
  const s = DATA.stats;
  document.getElementById('t3-stats').innerHTML =
    '提取单元 ' + s.unitsTotal + '（句子 ' + s.sentenceUnits + ' · 表行 '
    + s.tableRowUnits + ' · 图caption ' + s.imageUnits + '）<br>'
    + '谓词覆盖率 ' + s.predicateFilled + '/' + s.unitsTotal + '（' + pct(s.predicateFilled, s.unitsTotal) + '）· '
    + '数值带单位率 ' + s.valueWithUnit + '/' + s.valueFilled + '（' + pct(s.valueWithUnit, s.valueFilled) + '）<br>'
    + '条件率 ' + s.conditionSentences + '/' + s.sentenceUnits + '（' + pct(s.conditionSentences, s.sentenceUnits) + '）· '
    + '引用解析率 ' + s.refResolved + '/' + s.refTotal + '（' + pct(s.refResolved, s.refTotal) + '）';
}

// ---------------- 初始化(默认Tab3)
renderMatrix();
renderDocPane();
if (DATA.defaultLeaf) { selectLeaf(DATA.defaultLeaf); }
renderUnits();
setupFilters();
applyFilters();
renderStats();
showTab('tab3');
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>提取图谱 · {doc_name}</title>
<style>{css}</style>
</head>
<body>
<header>
  <div class="logo">析</div>
  <div class="logo-txt">SRS结构化提取图谱<small>Requirement Extraction Atlas</small></div>
  <nav class="tabs">
    <button class="tabbtn" data-tab="tab1" type="button">追溯矩阵</button>
    <button class="tabbtn" data-tab="tab2" type="button">需求档案</button>
    <button class="tabbtn" data-tab="tab3" type="button">逐句对照</button>
  </nav>
  <span class="doc-name">{doc_name}</span>
</header>
<section class="tabpanel" id="tab1">
  <div class="panel-note">行＝全部叶子需求，列＝六路证据；
    <span class="st-direct">●绿＝直接命中</span>
    <span class="st-fallback">◑黄＝回退上级命中</span>
    <span class="st-missing">○红＝缺失</span>；点击格子或行名→切换到Tab2该需求档案</div>
  <div id="mx-grid"></div>
  <div class="mx-stats">
    <h3>各路齐全统计</h3>
    <div id="mx-routes"></div>
    <h3>断链Top（缺失路数最多的需求）</h3>
    <div id="mx-broken"></div>
  </div>
</section>
<section class="tabpanel" id="tab2">
  <div class="dossier-layout">
    <aside class="docpane-card">
      <div class="docp-bar">
        <select id="leaf-picker" class="docp-sel"></select>
      </div>
      <div class="docp-crumb" id="docp-crumb"></div>
      <div class="docpane" id="doc-pane"></div>
    </aside>
    <main class="graphside">
      <div class="card graph-card">
        <svg id="route-graph" viewBox="0 0 440 340" preserveAspectRatio="xMidYMid meet"></svg>
        <div class="rg-legend">
          <span><i class="dot st-direct"></i>直接命中</span>
          <span><i class="dot st-fallback"></i>回退上级</span>
          <span><i class="dot st-missing"></i>缺失</span>
          <span class="lg-tip">点击卫星节点查看证据并定位原文</span>
        </div>
      </div>
      <div class="card" id="feature-pane"></div>
      <div class="card detail-card" id="route-detail"></div>
    </main>
  </div>
</section>
<section class="tabpanel" id="tab3">
  <div class="tbar">
    <label>章节 <select id="sec-filter"></select></label>
    <label>需求ID <input id="rid-filter" placeholder="如 PZXQ-GN-SQLFW"></label>
    <label><input type="checkbox" id="only-pred"> 只看有谓词</label>
    <label><input type="checkbox" id="only-val"> 只看有数值</label>
    <span id="vis-count"></span>
  </div>
  <div class="urow uhead">
    <div class="u-left">原文（完整呈现，不加高亮）</div>
    <div class="u-right">提取结果（值或"—"）</div>
  </div>
  <div id="urows"></div>
  <div id="t3-stats" class="tstats"></div>
</section>
<footer>原文永远完整呈现不加高亮涂色；提取结果规整表格逐格展示（值或"—"）；
颜色仅用于状态点（●绿直接/◑黄回退/○红缺失），主色黑白灰+强调蓝。
模态词为规则抽取（应/应当/宜/可/须/必须/不得/禁止…，过滤"应用/可靠"等复合词），非独立数据源字段。
数据源：content_list + feature_matrix_v1/v2 + predicate_mining_v1 + semantic_features_v2。</footer>
<script type="application/json" id="atlas-data">{data}</script>
<script>{js}</script>
</body>
</html>
"""


def render_html(payload: dict[str, Any]) -> str:
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.format(
        doc_name=payload["doc"]["name"], css=CSS, data=data_json, js=JS
    )


def verify_html(html_doc: str, payload: dict[str, Any]) -> dict[str, Any]:
    """自包含性断言: 三Tab存在/矩阵行数=叶子数/对照行数=单元数/base64图/零外链."""
    for tab in ("tab1", "tab2", "tab3"):
        assert f'id="{tab}"' in html_doc, f"缺少Tab面板 {tab}"
        assert f'data-tab="{tab}"' in html_doc, f"缺少Tab按钮 {tab}"
    island = re.search(
        r'<script type="application/json" id="atlas-data">(.*?)</script>',
        html_doc,
        re.S,
    )
    assert island, "缺少数据岛"
    parsed = json.loads(island.group(1).replace("<\\/", "</"))

    def count_tree_leaves(nodes: list[dict[str, Any]]) -> int:
        return sum(1 if n["leaf"] else count_tree_leaves(n["children"]) for n in nodes)

    n_leaves = count_tree_leaves(parsed["tree"])
    assert len(parsed["matrix"]["leaves"]) == n_leaves, "Tab1矩阵行数 != 叶子数"
    assert len(parsed["matrix"]["leaves"]) == len(payload["matrix"]["leaves"])

    n_units = len(parsed["units"])
    assert n_units == payload["stats"]["unitsTotal"], "Tab3行数 != 提取单元数"
    kinds = Counter(u["k"] for u in parsed["units"])
    assert kinds.get("sentence", 0) == payload["stats"]["sentenceUnits"]
    assert kinds.get("table_row", 0) == payload["stats"]["tableRowUnits"]
    assert kinds.get("image", 0) == payload["stats"]["imageUnits"]

    for uri in parsed["images"].values():
        assert uri.startswith("data:image/") and ";base64," in uri, "非base64内嵌图"
    for pattern in (
        r"<script\b[^>]*\bsrc=",
        r"<link\b",
        r"<iframe\b",
        r"(?:src|href)\s*=\s*[\"']?https?://",
        r"url\(",
        r"@import",
    ):
        assert not re.search(pattern, html_doc, re.I), f"发现外链/外资源: {pattern}"
    assert "{css}" not in html_doc and "{js}" not in html_doc and "{data}" not in html_doc
    return {
        "tabs": 3,
        "matrix_rows": n_leaves,
        "unit_rows": n_units,
        "unit_kinds": dict(kinds),
        "images_embedded": len(parsed["images"]),
        "external_refs": 0,
    }


def collect_report(payload: dict[str, Any], checks: dict[str, Any], output: Path) -> dict[str, Any]:
    default_view = payload["leaves"].get(payload["defaultLeaf"], {})
    return {
        "doc": payload["doc"]["id"],
        "doc_name": payload["doc"]["name"],
        "output": str(output),
        "html_bytes": output.stat().st_size if output.exists() else 0,
        "leaves": checks["matrix_rows"],
        "matrix_route_stats": {
            r["label"]: {"direct": r["direct"], "fallback": r["fallback"], "missing": r["missing"]}
            for r in payload["matrix"]["routeStats"]
        },
        "default_leaf": payload["defaultLeaf"],
        "default_leaf_six_routes": default_view.get("states", {}),
        "units": {
            "total": payload["stats"]["unitsTotal"],
            "sentence": payload["stats"]["sentenceUnits"],
            "table_row": payload["stats"]["tableRowUnits"],
            "image": payload["stats"]["imageUnits"],
        },
        "predicate_filled_rows": payload["stats"]["predicateFilled"],
        "value_filled_rows": payload["stats"]["valueFilled"],
        "value_with_unit_rows": payload["stats"]["valueWithUnit"],
        "condition_sentences": payload["stats"]["conditionSentences"],
        "refs_resolved": f"{payload['stats']['refResolved']}/{payload['stats']['refTotal']}",
        "images_embedded": checks["images_embedded"],
        "verify": "ok",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="渲染GJB提取图谱atlas(三Tab自包含HTML)")
    parser.add_argument("--doc", default="04", help="doc id, 如 04 (默认: 04)")
    parser.add_argument("--output", type=Path, default=None, help="输出HTML路径")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    doc_id = args.doc.strip()
    doc_dir, office, content_list_path = find_doc_office(doc_id)
    blocks = read_json(content_list_path)
    if not isinstance(blocks, list):
        raise ValueError(f"content_list 不是列表: {content_list_path}")
    feats = load_features(doc_id)
    payload = build_atlas_payload(doc_id, doc_dir.name, blocks, office, feats)
    html_doc = render_html(payload)
    output = args.output or Path(str(DEFAULT_OUTPUT).replace("{doc}", doc_id))
    output = output if output.is_absolute() else BASE / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_doc, encoding="utf-8", newline="\n")
    checks = verify_html(html_doc, payload)
    report = collect_report(payload, checks, output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
