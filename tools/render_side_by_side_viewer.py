#!/usr/bin/env python3
"""Render a self-contained side-by-side HTML viewer for one GJB SRS document.

场景一对照视图（04号SRS: 用例图 + 能力表 + 正文 三模态）:
左栏按 MinerU content_list 原样渲染原文（文字/表格/图片），
右栏渲染 feature_matrix_v1 / predicate_mining_v1 / anchor_expansion_v1
的提取结果，左右按块索引滚动联动。左栏段落中的每个高亮 span
（编号/数值单位/谓词/模态/否定/引用）在右栏均有对应卡片与
✓/✗ 人工验证按钮——标注写入 localStorage，可导出 JSON。
可视化即评估协议（Span-Grounded Extraction 的人工验证界面）。

GJB 438C 标准感知层（gjb_conformance_v1，缺失时优雅降级）:
- 顶部章节契约面板: conformance_score 进度条(x/18)、present/missing
  节号 chip、anomalies 黄标（数据: section_contract.jsonl）
- 左栏标题右侧节语义小标签（section_semantics，标准18节语义兜底）
- 右栏表卡片头部 GJB 表型 badge（gjb_table_type + confidence 色标）
- 右栏图卡片头部 GJB 标准图型标签（caption 关键词映射）

质量诚实标注层（feature_quality_audit_v1，缺失时优雅降级）:
- 顶部质量汇总条: subject幻觉率（field_quality.jsonl统计）+
  单位空缺率（本地重算）——缺失时提示运行 audit_feature_quality.py
- claim卡五元组逐字段质量: 幻觉字段红删除线+“幻觉”标记、
  verified字段绿✓、空字段灰“未提取”
- 元指标与内容特征分离: slot_fill_rate 改名“解析完整度(过程指标)”，
  小灰字低视觉权重，不再冒充内容特征

Usage:
  python tools/render_side_by_side_viewer.py [--doc 04] [--output PATH]
                                             [--section 3.2] [--max-images 20]
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
FEATURE_DIR = BASE / "data/gjb_438c/feature_matrix_v1"
PREDICATE_PATH = BASE / "data/gjb_438c/predicate_mining_v1/predicates.jsonl"
ANCHOR_PATH = BASE / "data/gjb_438c/anchor_expansion_v1/anchors.jsonl"
GJB_CONFORMANCE_DIR = BASE / "data/gjb_438c/gjb_conformance_v1"
DEFAULT_OUTPUT = FEATURE_DIR / "side_by_side_{doc}.html"

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
REF_NUM_RE = re.compile(r"^(图|表)\s*([0-9]+)$")
CAPTION_NUM_RE = re.compile(r"^\s*(图|表)\s*([0-9]+)")
TAG_SPLIT_RE = re.compile(r"(<[^>]*>)")
TABLE_TOKEN_RE = re.compile(r"(<tr\b[^>]*>|</tr\s*>|<t[dh]\b[^>]*>|</t[dh]\s*>)", re.I)
TAG_ATTRS_RE = re.compile(r"^<([a-zA-Z]+)([^>]*)>$")
TABLE_ID_NUM_RE = re.compile(r"([0-9]+)\s*$")

SPAN_LABELS = {
    "fm-id": "编号",
    "fm-pred": "谓词",
    "fm-ref": "引用",
    "fm-num": "数值单位",
    "fm-modal": "模态",
    "fm-neg": "否定",
}
SPAN_PRIO = {
    "fm-id": 0,
    "fm-pred": 1,
    "fm-ref": 2,
    "fm-num": 3,
    "fm-modal": 4,
    "fm-neg": 5,
}
SPAN_CLASSES = (
    ("fm-id", REQ_ID_RE),
    ("fm-ref", REF_RE),
    ("fm-num", NUM_UNIT_RE),
    ("fm-modal", MODAL_RE),
    ("fm-neg", NEG_RE),
)
ROLE_COLORS = {
    "requirement_row": "#1e88e5",
    "usecase_section_row": "#fb8c00",
    "data_row": "#90a4ae",
    "index_row": "#8e24aa",
}
ROLE_FALLBACK_COLOR = "#78909c"

# ---- GJB 438C 标准感知层（gjb_conformance_v1，缺失时优雅降级） ----
GJB_STANDARD_TOTAL = 18
GJB_SECTION_SEMANTICS = {
    "3.1": "要求的状态和方式",
    "3.2": "CSCI能力需求",
    "3.3": "CSCI外部接口需求",
    "3.4": "CSCI内部接口需求",
    "3.5": "CSCI内部数据需求",
    "3.6": "适应性需求",
    "3.7": "安全性需求",
    "3.8": "保密性需求",
    "3.9": "CSCI环境需求",
    "3.10": "计算机资源需求",
    "3.11": "软件质量因素",
    "3.12": "设计和构造的约束",
    "3.13": "人员需求",
    "3.14": "培训需求",
    "3.15": "软件保障需求",
    "3.16": "其他需求",
    "3.17": "验收、交付和包装需求",
    "3.18": "需求的优先顺序和关键性",
}
GJB_TABLE_TYPE_LABELS = {
    "usecase_table": "用例表",
    "usecase": "用例表",
    "use_case_table": "用例表",
    "trace_table": "追踪表",
    "trace": "追踪表",
    "traceability_table": "追踪表",
    "requirement_table": "需求表",
    "parameter_table": "参数表",
    "interface_table": "接口表",
    "data_table": "数据表",
    "index_table": "索引表",
    "other_table": "其他表",
    "unknown": "未分类表",
}
GJB_DIAGRAM_TYPES = (
    ("用例图", "usecase diagram"),
    ("流程图", "flowchart"),
    ("接口", "interface diagram"),
)
GJB_DEGRADE_HINT = "GJB conformance层未生成（运行tools/build_gjb_conformance.py）"
FIELD_QUALITY_PATH = BASE / "data/gjb_438c/feature_quality_audit_v1/field_quality.jsonl"
QUALITY_AUDIT_DEGRADE_HINT = "质量审计层未生成（运行tools/audit_feature_quality.py生成）"
# claim 五元组字段别名 -> 规范名（与 claim_slot_features 字段对齐）
CLAIM_FIELD_ALIASES = {
    "subject": "subject",
    "subject_candidate": "subject",
    "主语": "subject",
    "predicate": "predicate",
    "predicate_candidate": "predicate",
    "谓词": "predicate",
    "operator": "operator",
    "算子": "operator",
    "value": "value",
    "object_value": "value",
    "值": "value",
    "unit": "unit",
    "unit_raw": "unit",
    "单位": "unit",
}
# 审计状态值别名 -> 规范状态
FIELD_STATUS_ALIASES = {
    "hallucinated": "hallucinated",
    "hallucination": "hallucinated",
    "hall": "hallucinated",
    "fake": "hallucinated",
    "幻觉": "hallucinated",
    "verified": "verified",
    "ok": "verified",
    "correct": "verified",
    "true": "verified",
    "yes": "verified",
    "empty": "empty",
    "missing": "empty",
    "none": "empty",
    "未提取": "empty",
    "空": "empty",
}
HALL_STATUS = "hallucinated"
OK_STATUS = "verified"
EMPTY_STATUS = "empty"
# (key, label, inverted, process) — process=True 为元指标（小灰字，不冒充内容特征）
QUALITY_METRICS = (
    ("claim_slot_fill_rate_avg", "解析完整度(过程指标)", False, True),
    ("reference_resolution_rate", "引用解析率", False, False),
    ("unit_completeness", "单位完整率", False, False),
    ("table_header_missing_rate", "表头缺失率", True, False),
    ("empty_text_node_rate", "空文本率", True, False),
)
PARSE_OK = {"ok", "parsed", "success", "complete", "full"}
SCRIPT_RE = re.compile(r"<script\b.*?(?:</script>|$)", re.I | re.S)
ONEVENT_RE = re.compile(r"\son\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s>]+)", re.I)
HTTP_RE = re.compile(r"https?://", re.I)


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


def resolve_overlaps(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = {(m["s"], m["e"], m["cls"]): m for m in matches}
    ordered = sorted(
        deduped.values(),
        key=lambda m: (SPAN_PRIO.get(m["cls"], 99), m["s"], -(m["e"] - m["s"])),
    )
    chosen: list[dict[str, Any]] = []
    for m in ordered:
        if all(m["e"] <= c["s"] or m["s"] >= c["e"] for c in chosen):
            chosen.append(m)
    return sorted(chosen, key=lambda m: m["s"])


def predicate_matches(
    plain: str, rng: tuple[int, int], pred: dict[str, Any] | None
) -> list[dict[str, Any]]:
    if not pred:
        return []
    pf = pred.get("predicate_function") or {}
    out: list[dict[str, Any]] = []
    verb = str(pf.get("verb") or "").strip()
    if len(verb) >= 2:
        p = plain.find(verb, rng[0], rng[1])
        if p >= 0:
            out.append({"s": p, "e": p + len(verb), "cls": "fm-pred"})
    obj = str(pf.get("object_stripped") or pf.get("object_raw") or "").strip()
    if len(obj) >= 2:
        p = plain.find(obj, rng[0], rng[1])
        if p < 0:
            obj = str(pf.get("object_raw") or "").strip()
            if len(obj) >= 2:
                p = plain.find(obj, rng[0], rng[1])
        if p >= 0:
            out.append({"s": p, "e": p + len(obj), "cls": "fm-pred"})
    return out


def render_marked_unit(
    raw: str,
    plain: str,
    offsets: list[int],
    chosen: list[dict[str, Any]],
    block_index: int,
    seq_start: int = 0,
) -> tuple[str, list[dict[str, Any]], int]:
    spans: list[dict[str, Any]] = []
    raw_ranges: list[tuple[int, int, str, int]] = []
    for k, m in enumerate(chosen):
        rs = offsets[m["s"]]
        re_ = offsets[m["e"] - 1] + 1
        seq = seq_start + k
        raw_ranges.append((rs, re_, m["cls"], seq))
        spans.append({"seq": seq, "cls": m["cls"], "text": plain[m["s"]:m["e"]]})
    out = raw
    for rs, re_, cls, seq in sorted(raw_ranges, key=lambda x: x[0], reverse=True):
        out = (
            out[:rs]
            + f'<mark class="{cls}" data-bi="{block_index}" data-sp="{seq}"'
            + ' title="点击在右栏定位该span">'
            + out[rs:re_]
            + "</mark>"
            + out[re_:]
        )
    return out, spans, seq_start + len(chosen)


def build_units(block: dict[str, Any]) -> list[str]:
    if block.get("type") == "text":
        return [str(block.get("text") or "")]
    if block.get("type") == "list":
        return [str(item) for item in block.get("list_items") or []]
    return []


# ------------------------------------------------------------ table pipeline


def render_table_body(body: str, feat: dict[str, Any]) -> str:
    """Rebuild MinerU table HTML with overlay classes from table_features."""
    body = sanitize_fragment(str(body or ""))
    merged = {
        (int(m.get("row_index", -1)), int(m.get("col_index", -1)))
        for m in feat.get("merged_cells") or []
        if isinstance(m, dict)
    }
    empty = {
        (int(e.get("row_index", -1)), int(e.get("col_index", -1))): str(e.get("state") or "")
        for e in feat.get("empty_cells") or []
        if isinstance(e, dict)
    }
    roles = {
        int(r.get("row_index", -1)): str(r.get("role_candidate") or "")
        for r in feat.get("row_roles") or []
        if isinstance(r, dict)
    }
    tokens = TABLE_TOKEN_RE.split(body)
    out: list[str] = []
    row_idx = -1
    cell_idx = -1
    cell_open: tuple[str, str] | None = None
    cell_parts: list[str] = []
    for tok in tokens:
        if not tok:
            continue
        low = tok.lower()
        if low.startswith("<tr"):
            row_idx += 1
            cell_idx = -1
            role = roles.get(row_idx, "")
            role_cls = f"fm-role-{role}" if role else ""
            m = TAG_ATTRS_RE.match(tok)
            attrs = m.group(2) if m else ""
            out.append(f"<tr{attrs}" + (f' class="{role_cls}"' if role_cls else "") + ">")
        elif low.startswith("</tr"):
            out.append(tok)
        elif low.startswith(("<td", "<th")):
            cell_idx += 1
            m = TAG_ATTRS_RE.match(tok)
            if m:
                cell_open = (m.group(1).lower(), m.group(2))
            else:
                cell_open = ("td", "")
            cell_parts = []
        elif low.startswith(("</td", "</th")):
            if cell_open is None:
                out.append(tok)
                continue
            classes: list[str] = []
            if (row_idx, cell_idx) in merged:
                classes.append("fm-merged")
            state = empty.get((row_idx, cell_idx), "")
            if state == "empty":
                classes.append("fm-empty")
            elif state == "dash":
                classes.append("fm-dash")
            elif state:
                classes.append("fm-inherit")
            tag, attrs = cell_open
            cls = " ".join(classes)
            out.append(f"<{tag}{attrs}" + (f' class="{cls}"' if cls else "") + ">")
            out.extend(cell_parts)
            out.append(f"</{tag}>")
            cell_open = None
        else:
            if cell_open is not None:
                cell_parts.append(tok)
            else:
                out.append(tok)
    return '<table class="fmtbl">' + "".join(out) + "</table>"


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


def table_id_number(table_id: str) -> int | None:
    m = TABLE_ID_NUM_RE.search(str(table_id or ""))
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


# --------------------------------------------------------- GJB conformance


def gjb_section_label(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("section", "sec", "id", "number"):
            value = item.get(key)
            if value not in (None, ""):
                return str(value).strip()
        return ""
    return str(item or "").strip()


def parse_contract(contract: dict[str, Any] | None) -> dict[str, Any]:
    present = [s for s in (gjb_section_label(x) for x in (contract or {}).get("sections_present") or []) if s]
    missing = [s for s in (gjb_section_label(x) for x in (contract or {}).get("sections_missing") or []) if s]
    total = max(GJB_STANDARD_TOTAL, len(present) + len(missing))
    x = len(present)
    score = (contract or {}).get("conformance_score")
    score_text = ""
    if isinstance(score, bool) or score is None:
        score = None
    elif isinstance(score, (int, float)):
        score_text = f"{float(score):.3f}" if isinstance(score, float) else str(score)
    elif str(score).strip():
        score_text = str(score).strip()
    if not present and isinstance(score, (int, float)) and not isinstance(score, bool):
        sval = float(score)
        if 0 < sval <= 1:
            x = int(round(sval * total))
    return {"present": present, "missing": missing, "x": x, "total": total, "score_text": score_text}


def build_gjb_panel(doc_id: str, contract: dict[str, Any] | None, state: str) -> str:
    if state == "missing":
        return (
            '<div id="gjbpanel" class="degraded"><div class="gjbrow">'
            '<span class="gjbtag">GJB 438C</span>'
            f'<span class="gjbwarn">⚠ {GJB_DEGRADE_HINT}</span>'
            "</div></div>\n"
        )
    if state == "no-row" or contract is None:
        return (
            '<div id="gjbpanel" class="degraded"><div class="gjbrow">'
            '<span class="gjbtag">GJB 438C</span>'
            f'<span class="gjbwarn">⚠ GJB conformance层未包含文档 {escape(doc_id)} 的契约行</span>'
            "</div></div>\n"
        )
    info = parse_contract(contract)
    width = min(100.0, info["x"] / info["total"] * 100) if info["total"] else 0.0
    chips = "".join(
        f'<span class="schip" title="已具备">{escape(s)}</span>' for s in info["present"]
    )
    chips += "".join(
        f'<span class="schip miss" title="缺失">{escape(s)}</span>' for s in info["missing"]
    )
    anom_items: list[str] = []
    for a in (contract or {}).get("anomalies") or []:
        if isinstance(a, dict):
            txt = str(a.get("message") or a.get("description") or a.get("type") or "").strip()
        else:
            txt = str(a or "").strip()
        if txt:
            anom_items.append(txt)
    anom_html = ""
    if anom_items:
        shown = "".join(
            f'<span class="anom" title="{escape(t)}">{escape(t[:40])}</span>' for t in anom_items[:6]
        )
        more = ""
        if len(anom_items) > 6:
            rest = "; ".join(anom_items[6:])
            more = f'<span class="anom" title="{escape(rest)}">+{len(anom_items) - 6}</span>'
        anom_html = (
            f'<span class="anombadge" title="GJB契约异常（anomalies）">⚠ 异常 {len(anom_items)}</span>'
            f'<div class="anoms">{shown}{more}</div>'
        )
    score_html = (
        f'<span class="confscore">conformance {escape(info["score_text"])}</span>'
        if info["score_text"]
        else ""
    )
    return (
        '<div id="gjbpanel"><div class="gjbrow">'
        '<span class="gjbtag">GJB 438C</span><span class="gjblabel">章节契约</span>'
        f'<div class="confwrap" title="conformance_score {escape(info["score_text"] or "—")}">'
        f'<div class="conftrack"><i style="width:{width:.1f}%"></i></div>'
        f'<b class="confnum">{info["x"]}/{info["total"]}</b></div>'
        + score_html
        + f'<div class="schips">{chips}</div>'
        + anom_html
        + "</div></div>\n"
    )


def gjb_table_badge_html(tax: dict[str, Any] | None) -> str:
    if not tax:
        return ""
    ttype = str(tax.get("gjb_table_type") or "").strip()
    if not ttype:
        return ""
    label = GJB_TABLE_TYPE_LABELS.get(ttype, ttype)
    conf = tax.get("confidence")
    try:
        conf_val = float(conf) if conf is not None else None
    except (TypeError, ValueError):
        conf_val = None
    if conf_val is None:
        cls = "a"
        conf_txt = ""
        conf_title = "confidence 缺失"
    else:
        cls = "g" if conf_val >= 0.9 else "a"
        conf_txt = f" {conf_val:.2f}"
        conf_title = f"confidence {conf_val:.2f}"
    return (
        f'<span class="ttbadge {cls}" title="GJB表型 {escape(ttype)} · {escape(conf_title)}">'
        f"GJB表型 · {escape(label)}{escape(conf_txt)}</span>"
    )


def diagram_gjb_type(caption: str) -> str | None:
    for kw, std in GJB_DIAGRAM_TYPES:
        if kw in caption:
            return std
    return None


def load_gjb_semantics(contract: dict[str, Any] | None) -> dict[str, str]:
    semantics: dict[str, str] = dict(GJB_SECTION_SEMANTICS)
    extra = (contract or {}).get("section_semantics")
    if isinstance(extra, dict):
        for key, value in extra.items():
            if key and value:
                semantics[str(key)] = str(value)
    return semantics


# ------------------------------------------------------ feature quality audit


def norm_field_status(value: Any) -> str | None:
    """Normalize an audit status value (str/bool) to canonical status."""
    if value is None:
        return None
    if isinstance(value, bool):
        return OK_STATUS if value else None
    key = str(value).strip().lower()
    if not key:
        return None
    return FIELD_STATUS_ALIASES.get(key, FIELD_STATUS_ALIASES.get(str(value).strip()))


def norm_field_name(name: Any) -> str | None:
    if name is None:
        return None
    key = str(name).strip().lower()
    if not key:
        return None
    if key in CLAIM_FIELD_ALIASES:
        return CLAIM_FIELD_ALIASES[key]
    return CLAIM_FIELD_ALIASES.get(str(name).strip())


CLAIM_FIELDS = ("subject", "predicate", "operator", "value", "unit")


def parse_field_quality(row: dict[str, Any] | None) -> dict[str, str]:
    """Extract canonical field -> status from one field_quality.jsonl row.

    兼容多种审计 schema:
    - hallucinated_fields: [字段名, ...] 列表（hallucinated 为列表时同义）
    - field_verdicts / field_status / fields / field_quality: {字段名: 状态}
    - 逐字段键: subject_verified / unit_status / ...
    - 顶层 subject_verified / hallucinated（作用于主语）
    """
    out: dict[str, str] = {}
    if not isinstance(row, dict):
        return out
    hall_lists: list[Any] = [row.get("hallucinated_fields")]
    hall = row.get("hallucinated")
    if isinstance(hall, list):
        hall_lists.append(hall)
    for items in hall_lists:
        if not isinstance(items, (list, tuple)):
            continue
        for item in items:
            field = norm_field_name(item)
            if field:
                out[field] = HALL_STATUS
    for key in ("field_verdicts", "field_status", "fields", "field_quality"):
        mapping = row.get(key)
        if isinstance(mapping, dict):
            for fname, fval in mapping.items():
                field = norm_field_name(fname)
                status = norm_field_status(fval)
                if field and status:
                    out[field] = status
    for fname in CLAIM_FIELDS:
        for suffix in ("_verified", "_status", "_quality", "_verdict"):
            if f"{fname}{suffix}" in row:
                status = norm_field_status(row[f"{fname}{suffix}"])
                if status:
                    out[fname] = status
    if isinstance(row.get("subject_verified"), bool):
        status = norm_field_status(row["subject_verified"])
        if status:
            out["subject"] = status
    if hall is True:
        out.setdefault("subject", HALL_STATUS)
    return out


def claim_field_value(claim: dict[str, Any], field: str) -> Any:
    """Field value in claim_slot_features for canonical audit field name."""
    key = {
        "subject": "subject_candidate",
        "predicate": "predicate_candidate",
        "operator": "operator",
        "value": "object_value",
        "unit": "unit_raw",
    }.get(field, field)
    return claim.get(key)


def audit_summary(
    audit_rows: list[dict[str, Any]],
    field_quality_by_id: dict[str, dict[str, str]],
    claim_feats: list[dict[str, Any]],
) -> dict[str, Any]:
    """Top quality summary: subject 幻觉率（审计层）+ 单位空缺率（本地重算）。"""
    audited = len(audit_rows)
    subject_hall = sum(
        1 for fq in field_quality_by_id.values() if fq.get("subject") == HALL_STATUS
    )
    subject_rate = (subject_hall / audited) if audited else None
    unit_total = len(claim_feats)
    unit_empty = sum(
        1 for c in claim_feats if str(c.get("unit_raw") or "").strip() == ""
    )
    unit_rate = (unit_empty / unit_total) if unit_total else None
    return {
        "claims_audited": audited,
        "subject_hallucinated": subject_hall,
        "subject_hallucination_rate": subject_rate,
        "unit_total": unit_total,
        "unit_empty": unit_empty,
        "unit_empty_rate_local": unit_rate,
    }


def pct_text(rate: float | None) -> str:
    return "—" if rate is None else f"{rate * 100:.1f}%"


def build_quality_audit_bar(doc_id: str, summary: dict[str, Any], state: str) -> str:
    """顶部质量汇总条（feature_quality_audit_v1，缺失时优雅降级）。"""
    if state == "missing":
        return (
            '<div id="qualpanel" class="degraded"><div class="qarow">'
            '<span class="qatag">质量审计</span>'
            f'<span class="qawarn">⚠ {QUALITY_AUDIT_DEGRADE_HINT}</span>'
            "</div></div>\n"
        )
    if state == "no-row":
        return (
            '<div id="qualpanel" class="degraded"><div class="qarow">'
            '<span class="qatag">质量审计</span>'
            f'<span class="qawarn">⚠ field_quality.jsonl 未包含文档 {escape(doc_id)} 的审计行'
            "（运行tools/audit_feature_quality.py）</span>"
            "</div></div>\n"
        )
    srate = summary.get("subject_hallucination_rate")
    urate = summary.get("unit_empty_rate_local")
    audited = int(summary.get("claims_audited") or 0)
    sh = int(summary.get("subject_hallucinated") or 0)
    ue = int(summary.get("unit_empty") or 0)
    ut = int(summary.get("unit_total") or 0)
    s_cls = "r" if (srate or 0) >= 0.2 else ("a" if (srate or 0) >= 0.05 else "g")
    u_cls = "r" if (urate or 0) >= 0.5 else ("a" if (urate or 0) >= 0.3 else "g")
    return (
        '<div id="qualpanel"><div class="qarow">'
        '<span class="qatag">质量审计</span><span class="qalabel">字段诚实标注</span>'
        f'<span class="qchip {s_cls}" title="subject幻觉 / 审计claim数（来自field_quality.jsonl）">'
        f"subject幻觉率 {escape(pct_text(srate))}（幻觉{sh}/{audited}）</span>"
        f'<span class="qchip {u_cls}" title="unit_raw为空的claim占比（本地重算，非LLM判定）">'
        f"单位空缺率 {escape(pct_text(urate))}（空缺{ue}/{ut}，本地重算）</span>"
        '<span class="qahint">claim卡: 幻觉字段红删除线 · verified绿✓ · 空字段灰“未提取”</span>'
        "</div></div>\n"
    )


# -------------------------------------------------------------- card pieces


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


def parse_status_chip(status: Any) -> str:
    low = str(status or "").lower()
    if low in PARSE_OK:
        return f'<span class="ps ok">{escape(str(status or "—"))}</span>'
    if low == "partial":
        return '<span class="ps mid">partial</span>'
    if low in ("", "none", "empty"):
        return '<span class="ps bad">empty</span>'
    return f'<span class="ps mid">{escape(str(status))}</span>'


def claim_field_dd(label: str, value: Any, audit: dict[str, str] | None) -> str:
    """One five-tuple <dt><dd> pair with honest quality annotation.

    - 幻觉字段: 红色删除线 + “幻觉”标记
    - verified字段: 绿色✓
    - 空字段: 灰色“未提取”（章节等非五元组字段仍显示—）
    - 无审计信息: 原样展示（不冒充质量结论）
    """
    field = {
        "主语": "subject",
        "谓词": "predicate",
        "算子": "operator",
        "值": "value",
        "单位": "unit",
    }.get(label)
    if value in (None, ""):
        if field:
            return (
                f'<dt class="fh-dt">{label}</dt>'
                f'<dd class="fh-empty" title="该槽位为空：提取层未产出该字段">未提取</dd>'
            )
        return f"<dt>{label}</dt><dd>—</dd>"
    status = (audit or {}).get(field or "", "") if field else ""
    if status == HALL_STATUS:
        return (
            f'<dt class="fh-dt">{label}</dt>'
            f'<dd class="fh-hall"><s>{escape(str(value))}</s>'
            f'<span class="fhmark hall" title="审计判定：幻觉字段（原文无支撑）">幻觉</span></dd>'
        )
    if status == OK_STATUS:
        return (
            f'<dt class="fh-dt">{label}</dt>'
            f'<dd class="fh-ok">{escape(str(value))}'
            f'<span class="fhmark ok" title="审计判定：verified（有原文支撑）">✓</span></dd>'
        )
    return f"<dt>{label}</dt><dd>{escape(str(value))}</dd>"


def claim_card_html(
    claim: dict[str, Any],
    pred: dict[str, Any] | None,
    sent: dict[str, Any] | None,
    unlocated: bool = False,
    audit: dict[str, str] | None = None,
) -> str:
    raw_text = str(claim.get("raw_text") or "")
    shown = raw_text if len(raw_text) <= 160 else raw_text[:160] + "…"
    pf = (pred or {}).get("predicate_function") or {}
    verb = str(pf.get("verb") or "")
    obj = str(pf.get("object_stripped") or pf.get("object_raw") or "")
    predicate = str(claim.get("predicate_candidate") or "")
    if not predicate and (verb or obj):
        predicate = f"{verb} {obj}".strip()
    try:
        rate = max(0.0, min(1.0, float(claim.get("slot_fill_rate") or 0.0)))
    except (TypeError, ValueError):
        rate = 0.0
    pieces: list[str] = ['<div class="claimbox">']
    pieces.append(
        '<div class="claimrow1"><code>'
        + escape(str(claim.get("claim_id") or ""))
        + "</code>"
        + parse_status_chip(claim.get("parse_status"))
        + ('<span class="unloc">span未定位</span>' if unlocated else "")
        + "</div>"
    )
    pieces.append(f'<div class="raw">{escape(shown)}</div>')
    pieces.append('<dl class="five">')
    pairs = (
        ("主语", claim.get("subject_candidate")),
        ("谓词", predicate or None),
        ("算子", claim.get("operator") or None),
        ("值", claim.get("object_value") or None),
        ("单位", claim.get("unit_raw") or None),
        ("章节", claim.get("section")),
    )
    for label, value in pairs:
        pieces.append(claim_field_dd(label, value, audit))
    pieces.append("</dl>")
    pieces.append(
        '<div class="slotwrap" title="元指标：解析管线槽位填充程度（过程信号），'
        '非内容特征，不代表提取正确性">'
        "<span>解析完整度(过程指标)</span>"
        f'<div class="slottrack"><i style="width:{rate * 100:.1f}%"></i></div>'
        f"<b>{rate * 100:.0f}%</b></div>"
    )
    if pred:
        key = str(pred.get("predicate_key") or "")
        pieces.append(
            '<div class="prd">谓词挖掘: verb “'
            + escape(verb)
            + "” + obj “"
            + escape(obj)
            + '"'
            + (f" · {escape(key[:60])}" if key else "")
            + "</div>"
        )
    if sent:
        modal = "、".join(str(w) for w in sent.get("modal_words") or [])
        neg = "是" if sent.get("negative") else "否"
        pieces.append(
            '<div class="sentf">句特征: 模态['
            + escape(modal or "—")
            + "] 否定:"
            + neg
            + " 数量:"
            + str(len(sent.get("quantities") or []))
            + " 引用:"
            + str(len(sent.get("references") or []))
            + " 编号:"
            + str(len(sent.get("requirement_ids") or []))
            + "</div>"
        )
    pieces.append("</div>")
    return "".join(pieces)


def summarize_model(model: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    ts = model.get("type_specific") or {}
    if not isinstance(ts, dict):
        ts = {}
    dtype = str(model.get("diagram_type") or "")
    if dtype == "usecase_diagram":
        assoc = [a for a in ts.get("associations") or [] if isinstance(a, dict)]
        actors = sorted({str(a.get("actor")) for a in assoc if a.get("actor")})
        ucs = sorted({str(a.get("usecase")) for a in assoc if a.get("usecase")})
        pairs.append(("Actors", (f"{len(actors)}: " + "、".join(actors[:6])) if actors else "0"))
        pairs.append(("UseCases", (f"{len(ucs)}: " + "、".join(ucs[:6])) if ucs else "0"))
        pairs.append(("关联数", str(len(assoc))))
        boundaries = ts.get("boundaries")
        if isinstance(boundaries, list) and boundaries:
            pairs.append(("边界", "、".join(str(b) for b in boundaries[:4])))
    else:
        levels = model.get("levels") or []
        if isinstance(levels, list) and levels:
            nodes = sum(len(x) if isinstance(x, (list, tuple)) else 1 for x in levels)
            pairs.append(("层级", f"{len(levels)}层 · 节点{nodes}个"))
    consumed = {"associations", "boundaries"}
    for key, value in ts.items():
        if key in consumed:
            continue
        if isinstance(value, (list, tuple)):
            pairs.append((str(key), f"{len(value)}项"))
        elif value is not None and not isinstance(value, dict):
            pairs.append((str(key), str(value)[:48]))
    root = str(model.get("root") or "")
    if root:
        pairs.append(("root", root[:40]))
    conf = model.get("confidence")
    if conf is not None:
        pairs.append(("confidence", str(conf)))
    orphans = model.get("orphans_count")
    if orphans is not None:
        pairs.append(("孤儿节点", str(orphans)))
    return pairs


def model_stats_dl(model: dict[str, Any]) -> str:
    pairs = summarize_model(model)
    if not pairs:
        return '<p class="muted">语义模型无可用字段</p>'
    parts = ['<dl class="tstats">']
    for k, v in pairs:
        parts.append(f"<dt>{escape(k)}</dt><dd>{escape(v)}</dd>")
    parts.append("</dl>")
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
    text_feats = read_jsonl(FEATURE_DIR / "text_features.jsonl", doc_id)
    claim_feats = read_jsonl(FEATURE_DIR / "claim_slot_features.jsonl", doc_id)
    table_feats = read_jsonl(FEATURE_DIR / "table_features.jsonl", doc_id)
    diagram_feats = read_jsonl(FEATURE_DIR / "diagram_semantic_features.jsonl", doc_id)
    quality_rows = read_jsonl(FEATURE_DIR / "quality_features.jsonl", doc_id)
    doc_rows = read_jsonl(FEATURE_DIR / "document_features.jsonl")
    predicates = read_jsonl(PREDICATE_PATH, doc_id)
    anchors = read_jsonl(ANCHOR_PATH, doc_id)

    # ---- GJB conformance 标准感知层（缺失时优雅降级）
    contract_path = GJB_CONFORMANCE_DIR / "section_contract.jsonl"
    contract_rows = read_jsonl(contract_path, doc_id)
    taxonomy_by_id: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(GJB_CONFORMANCE_DIR / "table_taxonomy.jsonl"):
        tid = str(row.get("table_id") or "").strip()
        if tid:
            taxonomy_by_id[tid] = row
    contract = contract_rows[0] if contract_rows else None
    if contract is not None:
        gjb_state = "ok"
    elif contract_path.exists():
        gjb_state = "no-row"
    else:
        gjb_state = "missing"
    contract_info = parse_contract(contract)
    gjb_semantics = load_gjb_semantics(contract)

    # ---- 质量诚实标注层（feature_quality_audit_v1，缺失时优雅降级）
    # 行可按 doc_id 过滤；无 doc_id 的行按 claim_id 归属到本文档
    doc_claim_ids = {str(c.get("claim_id") or "") for c in claim_feats if c.get("claim_id")}
    audit_rows = []
    for row in read_jsonl(FIELD_QUALITY_PATH):
        rid_doc = row.get("doc_id")
        cid = str(row.get("claim_id") or "")
        if rid_doc is not None:
            if str(rid_doc) == doc_id:
                audit_rows.append(row)
        elif cid and cid in doc_claim_ids:
            audit_rows.append(row)
    field_quality_by_id: dict[str, dict[str, str]] = {}
    for row in audit_rows:
        cid = str(row.get("claim_id") or "").strip()
        if cid:
            field_quality_by_id[cid] = parse_field_quality(row)
    if audit_rows:
        audit_state = "ok"
    elif FIELD_QUALITY_PATH.exists():
        audit_state = "no-row"
    else:
        audit_state = "missing"
    quality_summary = audit_summary(audit_rows, field_quality_by_id, claim_feats)

    sent_by_id = {str(r.get("sentence_id")): r for r in text_feats}
    pred_by_id = {str(r.get("claim_id")): r for r in predicates}
    models_by_index: dict[int, dict[str, Any]] = {}
    for row in diagram_feats:
        try:
            models_by_index[int(row.get("model_index", -1))] = row
        except (TypeError, ValueError):
            continue
    anchor_counter = Counter(str(r.get("layer")) for r in anchors)
    quality = quality_rows[0] if quality_rows else {}

    # ---- 遍历块: 章节归属 + 渲染清单 + 表/图顺序索引
    sec = ""
    headings: list[tuple[str, str]] = []
    render_list: list[dict[str, Any]] = []
    table_count = 0
    image_count = 0
    image_caption_nums: set[int] = set()
    table_caption_nums: set[int] = set()
    image_caption_by_num: dict[int, str] = {}
    table_caption_by_num: dict[int, str] = {}
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
            num = caption_number(block.get("table_caption"), "表")
            if num is not None:
                table_caption_nums.add(num)
                table_caption_by_num.setdefault(
                    num, str((block.get("table_caption") or [""])[0])
                )
        elif btype == "image":
            entry["ik"] = image_count
            image_count += 1
            num = caption_number(block.get("image_caption"), "图")
            if num is not None:
                image_caption_nums.add(num)
                image_caption_by_num.setdefault(
                    num, str((block.get("image_caption") or [""])[0])
                )
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

    # ---- claim -> 块/单元 定位 (raw_text 在 text/list 块的 plain 中 find)
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

    block_claims: dict[int, list[dict[str, Any]]] = {}
    located_claims = 0
    for claim in claim_feats:
        raw_text = str(claim.get("raw_text") or "")
        cid = str(claim.get("claim_id") or "")
        if not raw_text or not cid:
            continue
        for entry in render_list:
            if entry["kind"] not in ("text", "list"):
                continue
            found = False
            for ui, ud in enumerate(unit_data[entry["index"]]):
                pos = ud["plain"].find(raw_text)
                if pos >= 0:
                    block_claims.setdefault(entry["index"], []).append(
                        {"claim": claim, "ui": ui, "pos": pos}
                    )
                    located_claims += 1
                    found = True
                    break
            if found:
                break

    # ---- 渲染左/右栏
    span_stats: Counter[str] = Counter()
    span_row_total = 0
    left_parts: list[str] = []
    right_parts: list[str] = []
    table_mismatch = len(table_feats) != table_count
    diagram_mismatch = len(models_by_index) != image_count
    gjb_table_badges = 0
    gjb_diagram_badges = 0

    # ---- 未定位 claim 汇总卡（raw_text 在任何 text/list 块中均 find 不到）
    located_ids = {
        str(item["claim"].get("claim_id"))
        for items in block_claims.values()
        for item in items
    }
    unlocated_claims = [
        c for c in claim_feats if str(c.get("claim_id") or "") not in located_ids
    ]
    if unlocated_claims:
        unloc_parts: list[str] = [
            '<div class="rcard" id="rc-unlocated" data-sec="">'
            '<div class="rchead"><span class="tbadge tb-text">TEXT</span>'
            "<span>块#—（raw_text 未在原文块中定位）</span>"
            '<span class="secchip">汇总</span></div><div class="rcbody">'
            f'<div class="clhead">span未定位 claim（{len(unlocated_claims)}，展示前'
            f"{min(30, len(unlocated_claims))} 条）</div>"
        ]
        for claim in unlocated_claims[:30]:
            cid = str(claim.get("claim_id") or "")
            unloc_parts.append(
                claim_card_html(
                    claim,
                    pred_by_id.get(cid),
                    sent_by_id.get(cid),
                    unlocated=True,
                    audit=field_quality_by_id.get(cid),
                )
            )
        if len(unlocated_claims) > 30:
            unloc_parts.append(
                f'<p class="muted">… 其余 {len(unlocated_claims) - 30} 条省略'
                "（多为 table_claim：单元格拼接文本无法 find 定位到正文块）</p>"
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
        gjb_head_badge = ""
        if kind == "table":
            feat_pre = table_feats[entry["tk"]] if entry["tk"] < len(table_feats) else None
            badge = gjb_table_badge_html(taxonomy_by_id.get(str((feat_pre or {}).get("table_id") or "")))
            if badge:
                gjb_head_badge = badge
                gjb_table_badges += 1
        elif kind == "image":
            dtype = diagram_gjb_type(str((block.get("image_caption") or [""])[0]))
            if dtype:
                gjb_head_badge = (
                    '<span class="ttbadge dg" title="GJB标准图型（caption关键词映射）">'
                    f"GJB图型 · {escape(dtype)}</span>"
                )
                gjb_diagram_badges += 1
        right_parts.append(
            f'<div class="rcard" id="rc-{i}" data-bi="{i}" data-sec="{escape(sec_now)}">'
            '<div class="rchead"><span class="tbadge tb-'
            + kind
            + '">'
            + kind.upper()
            + "</span>"
            + f"<span>块#{i}</span>"
            + f'<span class="secchip">{escape(sec_now or "前言")}</span>'
            + gjb_head_badge
            + '<button class="jump" title="在左栏定位">↖ 原文</button></div>'
            + '<div class="rcbody">'
        )

        if kind == "text":
            if block.get("text_level"):
                try:
                    level = max(1, min(6, int(block.get("text_level"))))
                except (TypeError, ValueError):
                    level = 3
                sem = gjb_semantics.get(sec_now)
                sem_html = f'<span class="secsem">{escape(str(sem))}</span>' if sem else ""
                left_parts.append(
                    f'<div class="h h{level}">{escape(str(block.get("text") or ""))}{sem_html}</div>'
                )
            else:
                raw_san = sanitize_fragment(str(block.get("text") or ""))
                plain, offsets = plain_with_offsets(raw_san)
                matches: list[dict[str, Any]] = []
                for cls, rx in SPAN_CLASSES:
                    for m in rx.finditer(plain):
                        matches.append({"s": m.start(), "e": m.end(), "cls": cls})
                for item in block_claims.get(i, []):
                    cid = str(item["claim"].get("claim_id") or "")
                    rng = (
                        item["pos"],
                        item["pos"] + len(str(item["claim"].get("raw_text") or "")),
                    )
                    matches.extend(predicate_matches(plain, rng, pred_by_id.get(cid)))
                chosen = resolve_overlaps(matches)
                marked, spans, _next = render_marked_unit(raw_san, plain, offsets, chosen, i)
                left_parts.append(f'<p class="para">{marked}</p>')
                entry["spans"] = spans
        elif kind == "list":
            items_html: list[str] = []
            unit_spans: list[dict[str, Any]] = []
            seq_cursor = 0
            for ui, raw in enumerate(build_units(block)):
                raw_san = sanitize_fragment(raw)
                plain, offsets = plain_with_offsets(raw_san)
                matches = []
                for cls, rx in SPAN_CLASSES:
                    for m in rx.finditer(plain):
                        matches.append({"s": m.start(), "e": m.end(), "cls": cls})
                for item in block_claims.get(i, []):
                    if item["ui"] != ui:
                        continue
                    cid = str(item["claim"].get("claim_id") or "")
                    rng = (
                        item["pos"],
                        item["pos"] + len(str(item["claim"].get("raw_text") or "")),
                    )
                    matches.extend(predicate_matches(plain, rng, pred_by_id.get(cid)))
                chosen = resolve_overlaps(matches)
                marked, spans, seq_cursor = render_marked_unit(
                    raw_san, plain, offsets, chosen, i, seq_start=seq_cursor
                )
                items_html.append(f"<li>{marked}</li>")
                unit_spans.extend(spans)
            left_parts.append('<ul class="lul">' + "".join(items_html) + "</ul>")
            entry["spans"] = unit_spans
        elif kind == "table":
            tk = entry["tk"]
            feat = table_feats[tk] if tk < len(table_feats) else None
            body_html = render_table_body(str(block.get("table_body") or ""), feat or {})
            cap = str((block.get("table_caption") or [""])[0])
            left_parts.append(f'<div class="capbar">{escape(cap)}</div>')
            left_parts.append(f'<div class="tblwrap">{body_html}</div>')
            entry["feat"] = feat
        elif kind == "image":
            cap = str((block.get("image_caption") or [""])[0])
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
            entry["model"] = models_by_index.get(entry["ik"])

        left_parts.append("</div>")

        # ---- 右栏卡片内容
        card_parts: list[str] = []
        if kind in ("text", "list"):
            claims = sorted(block_claims.get(i, []), key=lambda c: (c["ui"], c["pos"]))
            if claims:
                card_parts.append(f'<div class="clhead">命中 claim（{len(claims)}）</div>')
                for item in claims:
                    claim = item["claim"]
                    cid = str(claim.get("claim_id") or "")
                    card_parts.append(
                        claim_card_html(
                            claim,
                            pred_by_id.get(cid),
                            sent_by_id.get(cid),
                            audit=field_quality_by_id.get(cid),
                        )
                    )
            spans = entry.get("spans") or []
            if spans:
                card_parts.append(
                    f'<div class="sphead">高亮 span（{len(spans)}）— 点击 ✓/✗ 验证</div>'
                )
                for sp in spans:
                    span_stats[sp["cls"]] += 1
                    span_row_total += 1
                    label = SPAN_LABELS.get(sp["cls"], sp["cls"])
                    row_id = f"sr-{i}-{sp['seq']}"
                    card_parts.append(
                        f'<div class="spanrow" id="{row_id}" data-bi="{i}"'
                        f' data-key="{i}:{sp["seq"]}" data-text="{escape(sp["text"])}"'
                        f' data-type="{sp["cls"]}">'
                        f'<span class="spchip {sp["cls"]}">{escape(label)}</span>'
                        f'<code class="sptext">{escape(sp["text"])}</code>'
                        '<button class="vbtn vy" title="span 正确">✓</button>'
                        '<button class="vbtn vn" title="span 错误">✗</button>'
                        "</div>"
                    )
                ref_spans = [sp for sp in spans if sp["cls"] == "fm-ref"]
                if ref_spans:
                    card_parts.append('<div class="refhead">引用解析</div>')
                    for sp in ref_spans:
                        text = str(sp["text"]).strip()
                        m = REF_NUM_RE.match(text)
                        if not m:
                            continue
                        rkind = m.group(1)
                        try:
                            rnum = int(m.group(2))
                        except ValueError:
                            continue
                        if rkind == "图":
                            ok = rnum in image_caption_nums
                            target = image_caption_by_num.get(rnum, "")
                        else:
                            ok = rnum in table_caption_nums
                            target = table_caption_by_num.get(rnum, "")
                        res_cls = "ok" if ok else "bad"
                        res_text = ("✓ " + target[:36]) if ok else "✗ 未找到对应图表"
                        card_parts.append(
                            f'<div class="refrow"><span class="refchip">{escape(text)}</span>'
                            f'<span class="res {res_cls}">{escape(res_text)}</span></div>'
                        )
            if not card_parts:
                card_parts.append('<p class="muted">（无命中特征）</p>')
        elif kind == "table":
            tk = entry["tk"]
            feat = entry.get("feat")
            if feat is None:
                card_parts.append('<p class="muted">无对应 table_features（顺序错位或缺失）</p>')
            else:
                merged_n = len(feat.get("merged_cells") or [])
                empty_states = Counter(
                    str(e.get("state") or "?")
                    for e in feat.get("empty_cells") or []
                    if isinstance(e, dict)
                )
                role_counter = Counter(
                    str(r.get("role_candidate") or "?")
                    for r in feat.get("row_roles") or []
                    if isinstance(r, dict)
                )
                role_total = sum(role_counter.values()) or 1
                empty_txt = " · ".join(f"{k} {v}" for k, v in sorted(empty_states.items()))
                card_parts.append('<dl class="tstats">')
                card_parts.append(f"<dt>表ID</dt><dd>{escape(str(feat.get('table_id') or '—'))}</dd>")
                card_parts.append(
                    f"<dt>规模</dt><dd>{feat.get('n_rows', '—')}行 × "
                    f"{feat.get('n_cols', '—')}列</dd>"
                )
                card_parts.append(f"<dt>合并单元格</dt><dd>{merged_n}</dd>")
                card_parts.append(f"<dt>空值</dt><dd>{escape(empty_txt or '无')}</dd>")
                card_parts.append("</dl>")
                if role_counter:
                    card_parts.append('<div class="sphead">行角色分布</div>')
                    for role, cnt in sorted(role_counter.items(), key=lambda kv: (-kv[1], kv[0])):
                        color = ROLE_COLORS.get(role, ROLE_FALLBACK_COLOR)
                        width = cnt / role_total * 100
                        card_parts.append(
                            f'<div class="rolebar"><span class="rlab">{escape(role)}</span>'
                            f'<div class="rtrack"><i style="width:{width:.1f}%;'
                            f'background:{color}"></i></div>'
                            f'<span class="rnum">{cnt}</span></div>'
                        )
                    card_parts.append('<div class="sphead">前5行角色明细</div>')
                    first_roles = sorted(
                        feat.get("row_roles") or [],
                        key=lambda r: int(r.get("row_index", 0)) if isinstance(r, dict) else 0,
                    )[:5]
                    for r in first_roles:
                        if not isinstance(r, dict):
                            continue
                        card_parts.append(
                            f'<div class="rr">行{r.get("row_index")} · '
                            f"{escape(str(r.get('role_candidate') or '—'))}</div>"
                        )
            warns: list[str] = []
            if table_mismatch:
                warns.append(
                    f"计数警示: table_features {len(table_feats)} 条 ≠ 原文表块 {table_count} 个"
                )
            if feat is not None:
                tid = table_id_number(str(feat.get("table_id") or ""))
                if tid is not None and tid != tk:
                    warns.append(f"table_id 序号 {tid} ≠ 块表序 {tk}")
                cap_num = caption_number(block.get("table_caption"), "表")
                fcap_num = caption_number(feat.get("caption"), "表")
                if cap_num is not None and fcap_num is not None and cap_num != fcap_num:
                    warns.append(f"caption 编号不一致: 原文表{cap_num} vs 特征表{fcap_num}")
            for w in warns:
                card_parts.append(f'<span class="warn">⚠ {escape(w)}</span>')
        elif kind == "image":
            cap = str((block.get("image_caption") or [""])[0])
            card_parts.append(f'<div class="raw">{escape(cap)}</div>')
            model = entry.get("model")
            if model is not None:
                card_parts.append('<div class="sphead">图语义模型</div>')
                card_parts.append(model_stats_dl(model))
            else:
                card_parts.append('<p class="muted">无对应语义模型（model_index 未命中）</p>')
            l1 = anchor_counter.get("L1", 0)
            l2 = anchor_counter.get("L2", 0)
            card_parts.append('<div class="sphead">锚点状态（doc 级）</div>')
            card_parts.append(
                f'<span class="achip L1">L1 锚点 {l1}</span>'
                f'<span class="achip L2">L2 锚点 {l2}</span>'
            )
            if i not in embedded_sources:
                card_parts.append('<p class="muted">（本图未嵌入 base64，仅提取特征）</p>')
            if diagram_mismatch:
                card_parts.append(
                    f'<span class="warn">⚠ 计数警示: 语义模型 {len(models_by_index)} 个'
                    f" ≠ 原文图块 {image_count} 个</span>"
                )
        right_parts.append("".join(card_parts))
        right_parts.append("</div></div>")

    # ---- 顶部: doc 选择 + 章节过滤 + 质量信号 + 导出
    doc_options: list[str] = []
    if doc_rows:
        for row in doc_rows:
            did = str(row.get("doc_id") or "")
            dname = str(row.get("doc_name") or did)
            sel = " selected" if did == doc_id else ""
            doc_options.append(
                f'<option value="{escape(did)}"{sel}>{escape((did + " " + dname)[:26])}</option>'
            )
    else:
        doc_options.append(
            f'<option value="{escape(doc_id)}" selected>{escape(doc_name[:26])}</option>'
        )

    section_options: list[str] = ['<option value="all">全部章节</option>']
    heading_secs = {s for s, _ in headings}
    default_sel = section_default if section_default in heading_secs else "all"
    for s, title in headings:
        sel = " selected" if s == default_sel else ""
        section_options.append(
            f'<option value="{escape(s)}"{sel}>{escape((s + " " + title.strip())[:34])}</option>'
        )

    legend_items = "".join(
        f'<span><i style="background:{color}"></i>{escape(SPAN_LABELS[cls])}</span>'
        for cls, color in (
            ("fm-id", "#1d4ed8"),
            ("fm-num", "#c2410c"),
            ("fm-pred", "#15803d"),
            ("fm-modal", "#7e22ce"),
            ("fm-neg", "#b91c1c"),
            ("fm-ref", "#0e7490"),
        )
    )

    right_html = "".join(right_parts)
    hallucination_marks = right_html.count('class="fhmark hall"')
    verified_marks = right_html.count('class="fhmark ok"')
    empty_field_marks = right_html.count('class="fh-empty"')

    stats = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "blocks_total": len(blocks),
        "blocks_rendered": len(render_list),
        "cards": len(render_list),
        "span_rows": span_row_total,
        "spans_by_type": dict(sorted(span_stats.items())),
        "claims_total": len(claim_feats),
        "claims_located": located_claims,
        "claims_unlocated": len(claim_feats) - located_claims,
        "predicates_total": len(predicates),
        "table_feature_count": len(table_feats),
        "table_block_count": table_count,
        "diagram_model_count": len(models_by_index),
        "image_block_count": image_count,
        "images_embedded": len(embedded_sources),
        "section_default": default_sel,
        "gjb_layer": gjb_state,
        "gjb_sections_present": len(contract_info["present"]),
        "gjb_sections_missing": len(contract_info["missing"]),
        "gjb_conformance_score": contract_info["score_text"] or None,
        "gjb_table_badges": gjb_table_badges,
        "gjb_diagram_badges": gjb_diagram_badges,
        "quality_audit_layer": audit_state,
        "claims_audited": quality_summary["claims_audited"],
        "subject_hallucination_rate": quality_summary["subject_hallucination_rate"],
        "unit_empty_rate_local": quality_summary["unit_empty_rate_local"],
        "hallucination_marks": hallucination_marks,
        "verified_marks": verified_marks,
        "empty_field_marks": empty_field_marks,
    }
    payload = {
        "meta": {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "content_path": str(content_path),
            "section_default": default_sel,
            "max_images": max_images,
        },
        "anchors": {"L1": anchor_counter.get("L1", 0), "L2": anchor_counter.get("L2", 0)},
        "gjb": {
            "layer_state": gjb_state,
            "sections_present": len(contract_info["present"]),
            "sections_missing": len(contract_info["missing"]),
            "conformance_score": contract_info["score_text"] or None,
            "table_type_badges": gjb_table_badges,
            "diagram_type_badges": gjb_diagram_badges,
        },
        "quality_audit": {
            "layer_state": audit_state,
            "claims_audited": quality_summary["claims_audited"],
            "subject_hallucinated": quality_summary["subject_hallucinated"],
            "subject_hallucination_rate": quality_summary["subject_hallucination_rate"],
            "unit_total": quality_summary["unit_total"],
            "unit_empty": quality_summary["unit_empty"],
            "unit_empty_rate_local": quality_summary["unit_empty_rate_local"],
            "hallucination_marks": hallucination_marks,
            "verified_marks": verified_marks,
            "empty_field_marks": empty_field_marks,
        },
        "stats": {
            "span_rows": span_row_total,
            "spans_by_type": stats["spans_by_type"],
            "claims_located": located_claims,
            "images_embedded": len(embedded_sources),
        },
        "sections": [{"sec": s, "title": t} for s, t in headings],
    }

    html_doc = assemble_html(
        doc_id=doc_id,
        doc_name=doc_name,
        doc_options="".join(doc_options),
        section_options="".join(section_options),
        quality_chips=quality_chips_html(quality),
        legend=legend_items,
        gjb_panel=build_gjb_panel(doc_id, contract, gjb_state),
        quality_audit_bar=build_quality_audit_bar(doc_id, quality_summary, audit_state),
        left_html="".join(left_parts),
        right_html=right_html,
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
select, button { font: inherit; }
select { padding: 3px 8px; border: 1px solid #cdd6e0; border-radius: 6px; background: #fff;
  max-width: 330px; }
.qchips { display: flex; gap: 6px; flex-wrap: wrap; }
.qchip { font-size: 11px; padding: 2px 9px; border-radius: 999px; white-space: nowrap; }
.qchip.g { background: #e3f2e6; color: #256b2c; }
.qchip.a { background: #fdf3d7; color: #8a6a00; }
.qchip.r { background: #fde3e5; color: #b02a36; }
.qchip.proc { background: #eef2f7; color: #8a94a3; font-size: 10px; font-weight: 400;
  border: 1px dashed #d4dce6; }
.expbtn { background: #2f6fed; border: none; color: #fff; border-radius: 7px;
  padding: 5px 14px; cursor: pointer; font-size: 12.5px; }
.expbtn:hover { background: #2559c4; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; font-size: 11px; color: #5c6b7a;
  margin-top: 6px; align-items: center; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 2px;
  margin-right: 4px; vertical-align: -1px; }
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
mark.fm-id, .spchip.fm-id { background: #dbeafe; color: #1d4ed8; }
mark.fm-num, .spchip.fm-num { background: #ffedd5; color: #c2410c; }
mark.fm-pred, .spchip.fm-pred { background: #dcfce7; color: #15803d; }
mark.fm-modal, .spchip.fm-modal { background: #f3e8ff; color: #7e22ce; }
mark.fm-neg, .spchip.fm-neg { background: #fee2e2; color: #b91c1c; }
mark.fm-ref, .spchip.fm-ref { background: #cffafe; color: #0e7490; }
.capbar { font-weight: 600; font-size: 12px; color: #33404d; margin: 10px 0 5px; }
.tblwrap { overflow-x: auto; }
table.fmtbl { border-collapse: collapse; width: 100%; font-size: 12px; background: #fff; }
.fmtbl td, .fmtbl th { border: 1px solid #d5dbe3; padding: 4px 8px; vertical-align: top;
  line-height: 1.6; }
tr.fm-role-requirement_row > td:first-child { box-shadow: inset 4px 0 0 #1e88e5; }
tr.fm-role-usecase_section_row > td:first-child { box-shadow: inset 4px 0 0 #fb8c00; }
tr.fm-role-data_row > td:first-child { box-shadow: inset 4px 0 0 #90a4ae; }
tr.fm-role-index_row > td:first-child { box-shadow: inset 4px 0 0 #8e24aa; }
tr.fm-role-usecase_section_row { background: #fffaf3; }
tr.fm-role-index_row { background: #faf6fd; }
td.fm-merged { outline: 2px solid #e53935; outline-offset: -2px; }
td.fm-empty { background: #eceff1; }
td.fm-dash { background: #fff3b0; }
td.fm-inherit { background: #e8f2fd; box-shadow: inset 0 0 0 1px #7ba7d9; }
.fmimg { max-width: 100%; border: 1px solid #d5dbe3; border-radius: 4px; display: block; }
.imgph { border: 1.5px dashed #b7c2cf; color: #7d8896; padding: 18px 10px; text-align: center;
  border-radius: 6px; font-size: 12px; }
.imgph code { font-family: Consolas, "Courier New", monospace; font-size: 11px; }
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
.claimrow1 { display: flex; gap: 8px; align-items: center; font-size: 11px; color: #5c6b7a; }
.claimrow1 code { font-size: 10.5px; background: #eef2f7; padding: 1px 5px; border-radius: 4px; }
.ps { font-size: 10px; padding: 1px 7px; border-radius: 999px; }
.ps.ok { background: #e3f2e6; color: #256b2c; }
.ps.mid { background: #fdf3d7; color: #8a6a00; }
.ps.bad { background: #fde3e5; color: #b02a36; }
.raw { font-size: 12px; margin: 4px 0; line-height: 1.7; color: #1a2332; }
.five { display: grid; grid-template-columns: 56px 1fr 56px 1fr; gap: 2px 8px;
  font-size: 11.5px; margin: 4px 0; }
.five dt { color: #8a94a3; } .five dd { margin: 0; color: #1a2332; word-break: break-all; }
.five dt.fh-dt { color: #5c6b7a; }
dd.fh-hall { color: #b02a36; }
dd.fh-hall s { text-decoration: line-through; text-decoration-color: #b02a36;
  text-decoration-thickness: 1.5px; }
dd.fh-ok { color: #1a2332; }
.fhmark { font-size: 9.5px; font-weight: 700; padding: 0 6px; border-radius: 999px;
  margin-left: 5px; white-space: nowrap; vertical-align: 1px; }
.fhmark.hall { background: #fde3e5; color: #b02a36; border: 1px solid #f5c2c7; }
.fhmark.ok { background: #e3f2e6; color: #256b2c; }
dd.fh-empty { color: #8a94a3; font-style: italic; }
.slotwrap { display: flex; align-items: center; gap: 8px; font-size: 10px;
  color: #8a94a3; margin: 3px 0; }
.slottrack { flex: 1; height: 5px; background: #edf1f5; border-radius: 3px; overflow: hidden; }
.slottrack i { display: block; height: 100%; background: #b6c2cf; }
.slotwrap b { font-size: 10px; color: #8a94a3; font-variant-numeric: tabular-nums;
  font-weight: 400; }
.prd { font-size: 11px; color: #3f6212; background: #f0fdf4; border-radius: 5px;
  padding: 2px 8px; margin: 3px 0; }
.sentf { font-size: 10.5px; color: #5c6b7a; }
.unloc { font-size: 10px; background: #fde3e5; color: #b02a36; padding: 1px 7px;
  border-radius: 999px; }
.sphead, .refhead, .clhead { font-size: 11px; font-weight: 700; color: #5c6b7a;
  margin: 8px 0 4px; }
.spanrow { display: flex; align-items: center; gap: 7px; padding: 3px 8px;
  border: 1px solid #e5e9f0; border-radius: 6px; margin: 3px 0; font-size: 12px; }
.spanrow.flash { border-color: #2f6fed; box-shadow: 0 0 0 2px rgba(47, 111, 237, 0.25); }
.spanrow[data-verdict="yes"] { border-color: #2e7d32; background: #f2fbf3; }
.spanrow[data-verdict="no"] { border-color: #c62828; background: #fdf3f3; }
.spchip { font-size: 10px; padding: 1px 7px; border-radius: 4px; white-space: nowrap; }
.sptext { font-family: Consolas, "Courier New", monospace; font-size: 11.5px;
  word-break: break-all; }
.vbtn { width: 26px; height: 22px; border: 1px solid #cdd6e0; border-radius: 5px;
  background: #fff; cursor: pointer; font-size: 13px; line-height: 1; padding: 0; flex: none;
  color: #33404d; }
.vbtn.vy:hover { border-color: #2e7d32; color: #2e7d32; }
.vbtn.vn:hover { border-color: #c62828; color: #c62828; }
.vbtn.vy.on { background: #2e7d32; border-color: #2e7d32; color: #fff; }
.vbtn.vn.on { background: #c62828; border-color: #c62828; color: #fff; }
.refrow { display: flex; align-items: center; gap: 7px; font-size: 11.5px; margin: 3px 0; }
.refchip { background: #cffafe; color: #0e7490; border-radius: 4px; padding: 1px 7px;
  font-size: 10.5px; }
.res { font-size: 10.5px; padding: 1px 7px; border-radius: 4px; }
.res.ok { background: #e3f2e6; color: #256b2c; }
.res.bad { background: #fde3e5; color: #b02a36; }
.tstats { display: grid; grid-template-columns: 76px 1fr 76px 1fr; gap: 2px 8px;
  font-size: 11.5px; margin: 2px 0; }
.tstats dt { color: #8a94a3; } .tstats dd { margin: 0; word-break: break-all; }
.rolebar { display: flex; align-items: center; gap: 8px; font-size: 11px; margin: 3px 0; }
.rlab { width: 140px; text-align: right; color: #33404d; white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; flex: none; }
.rtrack { flex: 1; height: 12px; background: #edf1f5; border-radius: 3px; overflow: hidden; }
.rtrack i { display: block; height: 100%; }
.rnum { flex: none; color: #5c6b7a; font-variant-numeric: tabular-nums; }
.rr { font-size: 11px; color: #33404d; margin: 2px 0; }
.warn { display: inline-block; font-size: 10.5px; color: #8a6a00; background: #fdf3d7;
  border-radius: 5px; padding: 2px 8px; margin: 3px 4px 0 0; }
.achip { font-size: 10.5px; padding: 2px 9px; border-radius: 999px; display: inline-block;
  margin: 2px 6px 0 0; }
.achip.L1 { background: #e3f2e6; color: #256b2c; }
.achip.L2 { background: #fdf3d7; color: #8a6a00; }
#gjbpanel { margin-top: 6px; border: 1px solid #e1e6ee; border-radius: 8px; background: #f8fafd;
  padding: 5px 10px; }
#gjbpanel.degraded { background: #fff8e6; border-color: #eadfa8; }
.gjbrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 11.5px; }
.gjbtag { font-weight: 700; color: #3b3f8f; background: #e8eaf6; padding: 1px 8px;
  border-radius: 4px; white-space: nowrap; }
.gjblabel { color: #33404d; font-weight: 600; }
.gjbwarn { color: #8a6a00; font-size: 12px; }
.confwrap { display: flex; align-items: center; gap: 7px; }
.conftrack { width: 150px; height: 9px; background: #e6ebf2; border-radius: 5px; overflow: hidden; }
.conftrack i { display: block; height: 100%; background: #2e7d32; }
.confnum { font-variant-numeric: tabular-nums; color: #1a2332; }
.confscore { color: #5c6b7a; font-size: 10.5px; }
.schips { display: flex; gap: 4px; flex-wrap: wrap; }
.schip { font-size: 10.5px; padding: 1px 7px; border-radius: 4px; background: #e3f2e6;
  color: #256b2c; font-variant-numeric: tabular-nums; }
.schip.miss { background: #fde3e5; color: #b02a36; }
.anombadge { font-size: 10.5px; color: #8a6a00; background: #fdf3d7; border-radius: 999px;
  padding: 1px 9px; white-space: nowrap; }
.anoms { display: flex; gap: 4px; flex-wrap: wrap; }
.anom { font-size: 10.5px; color: #8a6a00; background: #fdf3d7; border-radius: 4px;
  padding: 1px 7px; max-width: 300px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }
#qualpanel { margin-top: 6px; border: 1px solid #e1e6ee; border-radius: 8px;
  background: #f8fafd; padding: 5px 10px; }
#qualpanel.degraded { background: #fff8e6; border-color: #eadfa8; }
.qarow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-size: 11.5px; }
.qatag { font-weight: 700; color: #8a2d3b; background: #f7e6ea; padding: 1px 8px;
  border-radius: 4px; white-space: nowrap; }
.qalabel { color: #33404d; font-weight: 600; }
.qawarn { color: #8a6a00; font-size: 12px; }
.qahint { color: #8a94a3; font-size: 10.5px; }
.secsem { font-size: 10px; color: #8a94a3; font-weight: 400; margin-left: 8px;
  white-space: nowrap; }
.ttbadge { font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 4px;
  white-space: nowrap; }
.ttbadge.g { background: #e3f2e6; color: #256b2c; }
.ttbadge.a { background: #fdf3d7; color: #8a6a00; }
.ttbadge.dg { background: #ede9fe; color: #6d28d9; }
.muted { color: #8a94a3; font-size: 11.5px; font-style: italic; margin: 4px 0; }
#bottombar { flex: none; background: #fff; border-top: 1px solid #dde3ec; padding: 7px 16px;
  display: flex; align-items: center; gap: 16px; font-size: 12.5px; color: #33404d; }
#bottombar b { font-variant-numeric: tabular-nums; }
.hint { color: #8a94a3; font-size: 11px; }
"""


def assemble_html(
    doc_id: str,
    doc_name: str,
    doc_options: str,
    section_options: str,
    quality_chips: str,
    legend: str,
    gjb_panel: str,
    quality_audit_bar: str,
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
        f"<title>SRS 对照视图 · {escape(doc_id)} {escape(doc_name[:30])}</title>\n"
        f"<style>{CSS_TEXT}</style>\n</head>\n<body>\n"
        '<div id="topbar">\n'
        '<div class="tbrow"><span class="title">SRS 对照视图（场景一：用例图 + 能力表 + 正文）'
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
        + '</div>\n<button id="expbtn1" class="expbtn">导出标注</button></div>\n'
        '<div class="legend"><b>span 图例：</b>'
        + legend
        + "<span>（点击左侧 mark 可在右栏定位）</span></div>\n"
        + gjb_panel
        + quality_audit_bar
        + '<div id="notice"></div>\n</div>\n'
        '<div id="main">\n'
        '<div class="col leftcol"><div class="panehead">左侧 · 原文（MinerU content_list 顺序'
        "渲染：标题/段落/列表/表格/图片）</div>"
        f'<div id="leftPane">{left_html}</div></div>\n'
        '<div class="col rightcol"><div class="panehead">右侧 · 提取结果（feature_matrix_v1 +'
        " predicate_mining_v1 + anchor_expansion_v1）</div>"
        f'<div id="rightPane">{right_html}</div></div>\n'
        "</div>\n"
        '<div id="bottombar"><span>已标 <b id="st-yes">0</b> ✓ / <b id="st-no">0</b> ✗ /'
        ' 当前视图 <b id="st-total">0</b> span</span>\n'
        '<button id="expbtn2" class="expbtn">导出标注 JSON</button>\n'
        '<span class="hint">标注存储于浏览器 localStorage（前缀 fmspan-'
        + escape(doc_id)
        + "），导出格式 [{span_text, span_type, block_index, verdict, ts, doc_id}]</span></div>\n"
        '<script type="application/json" id="fm-data">'
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
var PREFIX = "fmspan-" + DOC + ":";
var MEM = {};
var lock = 0;
var leftPane = document.getElementById("leftPane");
var rightPane = document.getElementById("rightPane");
var secsel = document.getElementById("secsel");
var docsel = document.getElementById("docsel");
var noticeEl = document.getElementById("notice");
var noticeTimer = null;

function lsGet(k) {
  try { return window.localStorage.getItem(PREFIX + k); } catch (e) { return MEM[k] || null; }
}
function lsSet(k, v) {
  try { window.localStorage.setItem(PREFIX + k, v); } catch (e) { MEM[k] = v; }
}
function lsDel(k) {
  try { window.localStorage.removeItem(PREFIX + k); } catch (e) { delete MEM[k]; }
}
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
  updateStats();
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
function updateStats() {
  var rows = document.querySelectorAll(".spanrow");
  var total = 0, yes = 0, no = 0;
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    if (!visible(r)) { continue; }
    total += 1;
    var raw = lsGet(r.getAttribute("data-key"));
    if (!raw) { continue; }
    try {
      var o = JSON.parse(raw);
      if (o.verdict === "yes") { yes += 1; }
      else if (o.verdict === "no") { no += 1; }
    } catch (e) { /* corrupt entry ignored */ }
  }
  document.getElementById("st-yes").textContent = String(yes);
  document.getElementById("st-no").textContent = String(no);
  document.getElementById("st-total").textContent = String(total);
}
function restore() {
  var rows = document.querySelectorAll(".spanrow");
  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    var raw = lsGet(r.getAttribute("data-key"));
    if (!raw) { continue; }
    try {
      var o = JSON.parse(raw);
      if (o.verdict === "yes" || o.verdict === "no") {
        r.setAttribute("data-verdict", o.verdict);
        var b = r.querySelector(o.verdict === "yes" ? ".vy" : ".vn");
        if (b) { b.classList.add("on"); }
      }
    } catch (e) { /* corrupt entry ignored */ }
  }
}
function exportAnnos() {
  var rows = [];
  var els = document.querySelectorAll(".spanrow");
  for (var i = 0; i < els.length; i++) {
    var r = els[i];
    var raw = lsGet(r.getAttribute("data-key"));
    if (!raw) { continue; }
    try {
      var o = JSON.parse(raw);
      o.doc_id = DOC;
      rows.push(o);
    } catch (e) { /* corrupt entry ignored */ }
  }
  var blob = new Blob([JSON.stringify(rows, null, 2)], { type: "application/json" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "side_by_side_annos_" + DOC + ".json";
  document.body.appendChild(a);
  a.click();
  window.setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  notice("已导出 " + rows.length + " 条标注（含全部已验证 span）");
}
document.addEventListener("click", function (ev) {
  var btn = ev.target.closest ? ev.target.closest(".vbtn") : null;
  if (btn) {
    var row = btn.closest(".spanrow");
    if (row) {
      var verdict = btn.classList.contains("vy") ? "yes" : "no";
      if (row.getAttribute("data-verdict") === verdict) {
        row.removeAttribute("data-verdict");
        var ons = row.querySelectorAll(".vbtn.on");
        for (var j = 0; j < ons.length; j++) { ons[j].classList.remove("on"); }
        lsDel(row.getAttribute("data-key"));
      } else {
        row.setAttribute("data-verdict", verdict);
        var all = row.querySelectorAll(".vbtn");
        for (var k = 0; k < all.length; k++) { all[k].classList.remove("on"); }
        btn.classList.add("on");
        lsSet(row.getAttribute("data-key"), JSON.stringify({
          span_text: row.getAttribute("data-text"),
          span_type: row.getAttribute("data-type"),
          block_index: parseInt(row.getAttribute("data-bi"), 10),
          verdict: verdict,
          ts: Date.now()
        }));
      }
      updateStats();
    }
    return;
  }
  var mk = ev.target.closest ? ev.target.closest("mark") : null;
  if (mk && leftPane.contains(mk)) {
    var bi = mk.getAttribute("data-bi");
    scrollToCard(bi);
    var sr = document.getElementById("sr-" + bi + "-" + mk.getAttribute("data-sp"));
    if (sr) {
      sr.classList.add("flash");
      window.setTimeout(function () { sr.classList.remove("flash"); }, 1200);
    }
    return;
  }
  var jump = ev.target.closest ? ev.target.closest(".jump") : null;
  if (jump) {
    var card = jump.closest(".rcard");
    if (card) { scrollToBlock(card.getAttribute("data-bi")); }
  }
});
secsel.onchange = applySection;
docsel.onchange = function () {
  var v = docsel.value;
  notice("本页仅内嵌 " + DOC + " 的数据。生成 " + v + " 视图请运行: " +
    "python tools/render_side_by_side_viewer.py --doc " + v);
  docsel.value = DOC;
};
document.getElementById("expbtn1").onclick = exportAnnos;
document.getElementById("expbtn2").onclick = exportAnnos;
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
  for (var i = 0; i < lbs.length; i++) { io.observe(lbs[i]); }
}
restore();
applySection();
})();
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render side-by-side (原文/提取) self-contained HTML viewer for one SRS doc"
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
