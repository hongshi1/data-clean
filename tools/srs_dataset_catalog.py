#!/usr/bin/env python3
"""
srs_dataset_catalog.py
======================
Scan the SRS collection directory and produce a unified dataset catalog,
a statistics report, and a human-readable Markdown report.

Outputs (written into the collection root):
  - dataset_catalog.json
  - dataset_statistics_report.json
  - DATASET_REPORT.md
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/gexuancheng/Desktop/research2/data_clean/data/gjb_438c/srs_collection")
OUT_DIR = ROOT

# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------

SOURCE_MAP = {
    "asyncTask": "asyncTask",
    "buaa": "buaa",
    "fault_prone_srs": "fault_prone_srs",
    "gjb438b": "gjb438b",
    "ieee830": "ieee830",
    "kaggle_testcase_req": "kaggle_testcase_req",
    "more_gjb": "more_gjb",
    "nasa": "nasa",
    "nice_nfr": "nice_nfr",
    "promise_plus": "promise_plus",
    "pure_extended": "pure_extended",
    "pure_original": "pure_original",
    "radar": "radar",
    "railway_req": "railway_req",
    "re_uts_srs": "re_uts_srs",
    "reqlist_reqnet_reqsim": "reqlist_reqnet_reqsim",
    "respa_spanish": "respa_spanish",
    "search_results": "search_results",
    "semantic_frame_req": "semantic_frame_req",
    "srs_ground_truth": "srs_ground_truth",
    "usecasedocs": "usecasedocs",
    "xwarfare": "xwarfare",
}

FORMAT_MAP = {
    ".md": "MD", ".markdown": "MD",
    ".pdf": "PDF",
    ".docx": "DOCX", ".doc": "DOC",
    ".txt": "TXT",
    ".tex": "TEX",
    ".xml": "XML",
    ".json": "JSON", ".jsonl": "JSONL",
    ".csv": "CSV",
    ".html": "HTML", ".htm": "HTML",
    ".xlsx": "XLSX", ".xls": "XLS",
    ".rtf": "RTF",
    ".py": "PY",
    ".zip": "ZIP",
    ".arff": "ARFF",
    ".pickle": "PICKLE",
    ".xsd": "XSD",
    ".lyx": "LYX",
    ".iml": "IML",
}

# Text-based formats we can read & analyse deeply
TEXT_FORMATS = {"MD", "TXT", "TEX", "HTML", "RTF", "CSV", "JSON", "JSONL", "XML", "ARFF", "PY", "XSD"}

# ---------------------------------------------------------------------------
# GJB 438C structural markers
# ---------------------------------------------------------------------------
# Each entry: (section_label, list_of_regex_patterns)
GJB_438C_MARKERS = [
    ("1 范围",            [r"##\s*1[\.\s]*范围", r"^1[\.\s]+范围", r"#\s*范围"]),
    ("1.1 标识",          [r"1\.1\s*标识", r"1\.1\s*标识"]),
    ("1.2 系统概述",      [r"1\.2\s*(系统概述|系统?概述|概述)"]),
    ("1.3 文档概述",      [r"1\.3\s*文档概述"]),
    ("1.4 基线",          [r"1\.4\s*基线"]),
    ("2 引用文件",        [r"##\s*2[\.\s]*引用文件", r"^2[\.\s]+引用文件", r"#\s*引用文件", r"引用文档"]),
    ("3 需求",            [r"##\s*3[\.\s]*需求", r"^3[\.\s]+需求", r"#\s*需求"]),
    ("3.1 需求概述",      [r"3\.1\s*需求概述", r"3\.1\s*需求概述"]),
    ("3.2 CSCI能力需求",  [r"CSCI\s*能力需求", r"3\.2.*能力需求", r"能力需求"]),
    ("3.3 接口需求",      [r"3\.3.*接口需求", r"接口需求"]),
    ("3.4 数据需求",      [r"3\.4.*数据需求", r"数据需求"]),
    ("4 合格性规定",      [r"4[\.\s]*合格性规定", r"合格性规定"]),
    ("5 需求可追踪性",    [r"5[\.\s]*需求可追踪性", r"需求可追踪性", r"可追溯性"]),
    ("6 注解",            [r"6[\.\s]*注解", r"^#\s*注解"]),
]

# Strong filename/content signals that a document is GJB-style
GJB_FILENAME_SIGNALS = re.compile(
    r"(438[CB]|GJB438|GJB\s*438|软件需求规格说明|需求规格说明[书明]?|研制任务书|概要设计说明|软件设计说明)",
    re.IGNORECASE,
)

TEMPLATE_SIGNALS = re.compile(
    r"(template|模板|skill|README|CONTRIBUTING|LICENSE|\.gitignore|format-lock|writing-prompts|"
    r"template-structure|standard_formatted|standard_ocr)",
    re.IGNORECASE,
)

# Constraint keywords for has_constraints / constraint_count
CONSTRAINT_PATTERNS = [
    re.compile(r"应(?!当)?[^\n]{0,40}"),       # 应 (but not 应当 handled below)
    re.compile(r"不得"),
    re.compile(r"必须"),
    re.compile(r"严禁"),
    re.compile(r"至少"),
    re.compile(r"最多|不超过|不大于|不小于|不低于|不高于"),
    re.compile(r"范围[在为]?|介于"),
    re.compile(r"[≤≥±≠]|<=|>=|!="),
    re.compile(r"\d+\s*(?:ms|MHz|kHz|Hz|GHz|MB|KB|GB|TB|%|次/秒|fps|rpm|°C|dB|V|A|W)\b", re.IGNORECASE),
    re.compile(r"\bshall\b", re.IGNORECASE),
    re.compile(r"\bmust\b", re.IGNORECASE),
    re.compile(r"\bshould\b", re.IGNORECASE),
    re.compile(r"\bat (?:least|most)\b", re.IGNORECASE),
    re.compile(r"\bno (?:more|less) than\b", re.IGNORECASE),
]

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SPANISH_SIGNALS = re.compile(r"(respa|spanish|Lista\s+dos|requisito|debe|sistema)", re.IGNORECASE)

HEADER_RE = re.compile(r"^\s{0,3}(#{1,6})\s+\S", re.MULTILINE)
NUMBERED_SECTION_RE = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){0,3})\s+\S", re.MULTILINE)
MD_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
HTML_TABLE_RE = re.compile(r"<table", re.IGNORECASE)

# System-type keyword scoring
SYSTEM_TYPE_KEYWORDS = {
    "aerospace": [r"radar|雷达|阵面|信号处理|satellite|flight|spacecraft|telescope|landsat|"
                  r"muon|spectrometer|CCSDS|HDTN|crypto|orbit|fprime|evla|nasa|航天|航空|飞行"],
    "defense":   [r"military|军工|军标|武器|warfare|战斗|missile|防御|defense|GJB|军"],
    "embedded":  [r"embedded|嵌入式|firmware|FPGA|MCU|STM32|driver|驱动|sensor|传感器|"
                  r"motor|电机|pump|泵|insulin|battery|电池|CSCI|配置项|realtime|实时"],
    "web":       [r"web|网站|购物|shop|commerce|电商|交易|platform|平台|portal|portal|"
                  r"online|在线|voting|投票|restaurant|餐厅|menu|菜单|library|图书馆|"
                  r"election|选举|campus|校园|course|课程|volunteer|ngo"],
    "education": [r"training|训练|exercise|练习|arithmetic|四则运算|teach|教学|edu|BUAA|"
                  r"school|学校|student|学生|exam|考试|bachelor|课程"],
    "medical":   [r"medical|医疗|health|健康|patient|病人|insulin|胰岛素|pharma|药房"],
    "railway":   [r"railway|铁路|train|列车|轨道"],
    "industrial":[r"industrial|工业|manufactur|制造|SCADA|PLC|焊接|welding|factory|工厂"],
    "finance":   [r"finance|金融|bank|银行|payment|支付|trading|交易|clearing|结算"],
    "communication": [r"communication|通信|network|网络|protocol|协议|middleware|中间件|"
                      r"router|路由|5G|LTE|buffer|协程|async"],
}

# Standard detection
def detect_standard(filename: str, source: str, content_head: str) -> str:
    blob = f"{filename}\n{content_head}"
    if re.search(r"438[Cc]|GJB438[Cc]|GJB\s*438[Cc]", blob):
        return "GJB 438C"
    if re.search(r"438[Bb]|GJB438[Bb]|GJB\s*438[Bb]", blob):
        return "GJB 438B"
    if source == "gjb438b" or "templates_438b" in filename or "examples_438b" in filename:
        return "GJB 438B"
    if re.search(r"MIL-STD-498|MIL\s*STD\s*498|498", blob) and source == "nasa":
        return "MIL-STD-498"
    if re.search(r"IEEE\s*830|IEEE-830|IEEE\s*Std\s*830", blob, re.IGNORECASE) or source == "ieee830":
        return "IEEE 830"
    if source == "nasa":
        return "NASA"
    if re.search(r"GB/T\s*8564|GBT\s*8564", blob):
        return "GB/T 8564"
    # GJB-style Chinese SRS without explicit standard number
    if re.search(r"需求规格说明[书明]?|研制任务书|概要设计说明|软件设计说明", blob) and CJK_RE.search(blob):
        return "GJB-style"
    return "Other"


def detect_system_type(filename: str, content_head: str, source: str) -> str:
    blob = f"{filename}\n{content_head}"
    best, best_score = "general", 0
    for stype, patterns in SYSTEM_TYPE_KEYWORDS.items():
        score = 0
        for p in patterns:
            score += len(re.findall(p, blob, re.IGNORECASE))
        if score > best_score:
            best, best_score = stype, score
    return best


def read_text(path: Path, limit_bytes: int = 200_000) -> str:
    """Read a text file with encoding fallback; return head of content."""
    data = path.read_bytes()[:limit_bytes]
    for enc in ("utf-8", "gbk", "gb18030", "latin-1"):
        try:
            return data.decode(enc, errors="strict")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def count_markdown_tables(text: str) -> int:
    """Count distinct markdown table blocks (consecutive | rows)."""
    count = 0
    in_table = False
    for line in text.splitlines():
        if MD_TABLE_ROW_RE.match(line):
            if not in_table:
                count += 1
                in_table = True
        else:
            in_table = False
    count += len(HTML_TABLE_RE.findall(text))
    return count


def count_sections(text: str) -> int:
    n = len(HEADER_RE.findall(text))
    n += len(NUMBERED_SECTION_RE.findall(text))
    # avoid double counting where a numbered section is also a header
    return max(n, 0)


def count_constraints(text: str) -> int:
    total = 0
    for pat in CONSTRAINT_PATTERNS:
        total += len(pat.findall(text))
    # de-duplicate by line: a line matching many patterns counts once-ish
    lines = text.splitlines()
    line_hits = 0
    for ln in lines:
        if any(p.search(ln) for p in CONSTRAINT_PATTERNS):
            line_hits += 1
    # Use line-based count as a stable proxy
    return line_hits


def gjb_compliance(text: str) -> tuple[int, list[str]]:
    """Return (score 0-10, list_of_present_sections)."""
    present = []
    for label, patterns in GJB_438C_MARKERS:
        if any(re.search(p, text, re.MULTILINE) for p in patterns):
            present.append(label)
    # Weighted scoring
    weights = {
        "1 范围": 1.0, "1.1 标识": 0.5, "1.2 系统概述": 0.5,
        "1.3 文档概述": 0.5, "1.4 基线": 0.5,
        "2 引用文件": 1.0,
        "3 需求": 1.5, "3.1 需求概述": 0.5, "3.2 CSCI能力需求": 1.0,
        "3.3 接口需求": 0.5, "3.4 数据需求": 0.5,
        "4 合格性规定": 1.0,
        "5 需求可追踪性": 1.0,
        "6 注解": 0.5,
    }
    raw = sum(weights.get(s, 0.5) for s in present)
    score = round(min(10.0, raw / 10.0 * 10.0), 1)
    return int(score) if score == int(score) else score, present


def detect_language(filename: str, content_head: str, source: str) -> str:
    if CJK_RE.search(filename):
        return "zh"
    if source == "respa_spanish" or SPANISH_SIGNALS.search(filename):
        return "es"
    if CJK_RE.search(content_head):
        return "zh"
    if SPANISH_SIGNALS.search(content_head):
        return "es"
    # default by source
    if source in ("respa_spanish",):
        return "es"
    return "en"


# ---------------------------------------------------------------------------
# Main classification
# ---------------------------------------------------------------------------

def classify_file(path: Path, idx: int) -> dict:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    # Files directly in the collection root are auxiliary metadata/report docs
    if len(parts) == 1:
        source = "metadata"
    else:
        top = parts[0]
        source = SOURCE_MAP.get(top, top)

    ext = path.suffix.lower()
    fmt = FORMAT_MAP.get(ext, "OTHER")
    # files with no extension
    if not ext:
        if path.name in ("README",):
            fmt = "TXT"
        elif path.name == "LICENSE":
            fmt = "TXT"
        else:
            fmt = "OTHER"

    size = path.stat().st_size
    filename = path.name
    rel_path = str(rel)

    content_head = ""
    line_count = 0
    section_count = 0
    table_count = 0
    constraint_count = 0
    has_constraints = False
    compliance_score = 0
    is_gjb_format = False
    is_filled = False
    standard = "Other"
    system_type = "general"
    language = "en"

    if fmt in TEXT_FORMATS:
        try:
            text = read_text(path)
        except Exception:
            text = ""
        content_head = text[:4000]
        line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        section_count = count_sections(text)
        table_count = count_markdown_tables(text)
        constraint_count = count_constraints(text)
        has_constraints = constraint_count > 0
        language = detect_language(filename, content_head, source)
        standard = detect_standard(rel_path, source, content_head)
        system_type = detect_system_type(filename, content_head, source)

        # GJB format detection
        gjb_signal = bool(GJB_FILENAME_SIGNALS.search(rel_path))
        marker_hits = 0
        for _, patterns in GJB_438C_MARKERS:
            if any(re.search(p, text, re.MULTILINE) for p in patterns):
                marker_hits += 1
        is_gjb_format = gjb_signal or marker_hits >= 3 or (
            source in ("radar", "more_gjb", "gjb438b", "asyncTask", "xwarfare") and marker_hits >= 2
        )
        if standard.startswith("GJB"):
            is_gjb_format = True

        # is_filled: not a template, has real content
        is_template = bool(TEMPLATE_SIGNALS.search(rel_path))
        is_filled = (not is_template) and line_count >= 20 and size > 200

        # compliance
        if is_gjb_format:
            compliance_score, _ = gjb_compliance(text)
            if compliance_score == 0 and marker_hits >= 2:
                compliance_score = max(1, marker_hits // 2)
    else:
        # Binary / non-text formats: infer from filename only
        language = detect_language(filename, "", source)
        standard = detect_standard(rel_path, source, "")
        system_type = detect_system_type(filename, "", source)
        gjb_signal = bool(GJB_FILENAME_SIGNALS.search(rel_path))
        is_gjb_format = gjb_signal or standard.startswith("GJB") or source in (
            "radar", "more_gjb", "gjb438b", "asyncTask", "xwarfare")
        is_template = bool(TEMPLATE_SIGNALS.search(rel_path))
        # estimate line count for PDFs by size as a rough proxy (unknown)
        is_filled = (not is_template) and size > 1000 and fmt in ("PDF", "DOCX", "DOC")
        if is_gjb_format and is_filled:
            compliance_score = 4  # default placeholder for unreadable GJB binary docs

    # Cap / normalise
    doc = {
        "id": f"GJB-SRS-{idx:03d}",
        "filename": filename,
        "source": source,
        "format": fmt,
        "size_bytes": size,
        "language": language,
        "standard": standard,
        "system_type": system_type,
        "is_gjb_format": is_gjb_format,
        "is_filled": is_filled,
        "line_count": line_count,
        "section_count": section_count,
        "table_count": table_count,
        "has_constraints": has_constraints,
        "constraint_count": constraint_count,
        "compliance_score": compliance_score,
        "relative_path": rel_path,
    }
    return doc


def main():
    if not ROOT.exists():
        print(f"ERROR: root not found: {ROOT}", file=sys.stderr)
        sys.exit(1)

    # Gather all files (skip the output files we are about to write)
    skip_names = {"dataset_catalog.json", "dataset_statistics_report.json", "DATASET_REPORT.md"}
    files = []
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir():
            continue
        if p.name in skip_names:
            continue
        files.append(p)

    catalog = []
    for i, p in enumerate(files, start=1):
        try:
            catalog.append(classify_file(p, i))
        except Exception as e:
            print(f"WARN: failed to classify {p}: {e}", file=sys.stderr)

    # ---- Write dataset_catalog.json ----
    catalog_path = OUT_DIR / "dataset_catalog.json"
    catalog_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[ok] {catalog_path}  ({len(catalog)} entries)")

    # ---- Aggregate statistics ----
    def counter(key):
        return Counter(d[key] for d in catalog)

    by_source = dict(sorted(counter("source").items(), key=lambda x: -x[1]))
    by_format = dict(sorted(counter("format").items(), key=lambda x: -x[1]))
    by_language = dict(sorted(counter("language").items(), key=lambda x: -x[1]))
    by_standard = dict(sorted(counter("standard").items(), key=lambda x: -x[1]))
    by_system_type = dict(sorted(counter("system_type").items(), key=lambda x: -x[1]))

    gjb_format_count = sum(1 for d in catalog if d["is_gjb_format"])
    gjb_filled_count = sum(1 for d in catalog if d["is_gjb_format"] and d["is_filled"])
    scores = [d["compliance_score"] for d in catalog if d["is_gjb_format"] and d["compliance_score"] > 0]
    avg_compliance = round(sum(scores) / len(scores), 2) if scores else 0.0
    total_constraints = sum(d["constraint_count"] for d in catalog)
    total_tables = sum(d["table_count"] for d in catalog)

    # Potential conflict-type heuristics (proxy estimates)
    same_param = sum(1 for d in catalog if d["has_constraints"] and d["constraint_count"] >= 10)
    text_table = sum(1 for d in catalog if d["table_count"] >= 1 and d["is_gjb_format"])
    logic_unsat = sum(1 for d in catalog if d["constraint_count"] >= 20 and d["is_gjb_format"])
    format_violation = sum(1 for d in catalog if d["is_gjb_format"] and d["compliance_score"] < 8 and d["is_filled"])

    stats = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_documents": len(catalog),
        "by_source": by_source,
        "by_format": by_format,
        "by_language": by_language,
        "by_standard": by_standard,
        "by_system_type": by_system_type,
        "gjb_format_count": gjb_format_count,
        "gjb_filled_count": gjb_filled_count,
        "avg_compliance_score": avg_compliance,
        "total_constraints": total_constraints,
        "total_tables": total_tables,
        "potential_conflict_types": {
            "same_param_diff_value": same_param,
            "text_table_mismatch": text_table,
            "logic_unsatisfiable": logic_unsat,
            "format_violation": format_violation,
        },
    }
    stats_path = OUT_DIR / "dataset_statistics_report.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {stats_path}")

    # ---- Markdown report ----
    write_markdown_report(catalog, stats)
    print(f"[ok] {OUT_DIR / 'DATASET_REPORT.md'}")


def md_bar(value: int, total: int, width: int = 30) -> str:
    if total <= 0:
        return ""
    filled = int(round(width * value / total))
    return "#" * filled + "-" * (width - filled)


def write_markdown_report(catalog: list[dict], stats: dict):
    L: list[str] = []
    L.append("# SRS 数据集统一目录与统计报告")
    L.append("")
    L.append(f"> 生成时间: {stats['generated_at']}  ")
    L.append(f"> 数据根目录: `{ROOT}`  ")
    L.append(f"> 文档总数: **{stats['total_documents']}**")
    L.append("")

    # ---- 1. Overview table ----
    L.append("## 1. 数据集总览")
    L.append("")
    L.append("| 指标 | 数值 |")
    L.append("|------|------|")
    L.append(f"| 文档总数 | {stats['total_documents']} |")
    L.append(f"| GJB 格式文档数 | {stats['gjb_format_count']} |")
    L.append(f"| GJB 格式且已填充文档数 | {stats['gjb_filled_count']} |")
    L.append(f"| 平均合规评分 (GJB 文档) | {stats['avg_compliance_score']} |")
    L.append(f"| 约束总数 | {stats['total_constraints']} |")
    L.append(f"| 表格总数 | {stats['total_tables']} |")
    L.append("")

    # ---- 2. By source ----
    L.append("## 2. 按来源统计 (by_source)")
    L.append("")
    L.append("| 来源 | 文档数 | 占比 | 分布 |")
    L.append("|------|--------|------|------|")
    total = stats["total_documents"]
    for k, v in stats["by_source"].items():
        pct = f"{v/total*100:.1f}%"
        L.append(f"| {k} | {v} | {pct} | `{md_bar(v, total)}` |")
    L.append("")

    # ---- 3. By format ----
    L.append("## 3. 按格式统计 (by_format)")
    L.append("")
    L.append("| 格式 | 文档数 | 占比 | 分布 |")
    L.append("|------|--------|------|------|")
    for k, v in stats["by_format"].items():
        pct = f"{v/total*100:.1f}%"
        L.append(f"| {k} | {v} | {pct} | `{md_bar(v, total)}` |")
    L.append("")

    # ---- 4. By language ----
    L.append("## 4. 按语言统计 (by_language)")
    L.append("")
    L.append("| 语言 | 文档数 | 占比 |")
    L.append("|------|--------|------|")
    for k, v in stats["by_language"].items():
        L.append(f"| {k} | {v} | {v/total*100:.1f}% |")
    L.append("")

    # ---- 5. By standard ----
    L.append("## 5. 按标准统计 (by_standard)")
    L.append("")
    L.append("| 标准 | 文档数 | 占比 |")
    L.append("|------|--------|------|")
    for k, v in stats["by_standard"].items():
        L.append(f"| {k} | {v} | {v/total*100:.1f}% |")
    L.append("")

    # ---- 6. By system type ----
    L.append("## 6. 按系统类型统计 (by_system_type)")
    L.append("")
    L.append("| 系统类型 | 文档数 | 占比 | 分布 |")
    L.append("|----------|--------|------|------|")
    st_max = max(stats["by_system_type"].values()) if stats["by_system_type"] else 1
    for k, v in stats["by_system_type"].items():
        L.append(f"| {k} | {v} | {v/total*100:.1f}% | `{md_bar(v, st_max)}` |")
    L.append("")

    # ---- 7. Mermaid charts ----
    L.append("## 7. 可视化图表 (Mermaid)")
    L.append("")
    # Pie by source
    L.append("### 7.1 按来源分布")
    L.append("")
    L.append("```mermaid")
    L.append("pie title 文档来源分布")
    for k, v in list(stats["by_source"].items())[:12]:
        L.append(f'    "{k} ({v})" : {v}')
    L.append("```")
    L.append("")
    # Bar (xychart) by format
    L.append("### 7.2 按格式分布")
    L.append("")
    L.append("```mermaid")
    L.append("---")
    L.append("config:")
    L.append("    xyChart:")
    L.append("        width: 900")
    L.append("        height: 500")
    L.append("        xAxis:")
    L.append("            label: 格式")
    L.append("        yAxis:")
    L.append("            label: 文档数")
    L.append("---")
    L.append("xychart-beta")
    fmts = list(stats["by_format"].items())
    L.append('    title "文档格式分布"')
    L.append("    x-axis [" + ", ".join(f'"{k}"' for k, _ in fmts) + "]")
    L.append("    y-axis 文档数 0 --> " + str(max(v for _, v in fmts) + 5))
    L.append("    bar [" + ", ".join(str(v) for _, v in fmts) + "]")
    L.append("```")
    L.append("")
    # Pie by system type
    L.append("### 7.3 按系统类型分布")
    L.append("")
    L.append("```mermaid")
    L.append("pie title 系统类型分布")
    for k, v in stats["by_system_type"].items():
        L.append(f'    "{k} ({v})" : {v}')
    L.append("```")
    L.append("")

    # ---- 8. GJB format SRS list ----
    L.append("## 8. GJB 格式 SRS 清单")
    L.append("")
    gjb_docs = [d for d in catalog if d["is_gjb_format"]]
    gjb_docs.sort(key=lambda d: (-d["compliance_score"], -d["line_count"], d["filename"]))
    L.append(f"共 **{len(gjb_docs)}** 个 GJB 格式文档（其中已填充 {sum(1 for d in gjb_docs if d['is_filled'])} 个）。")
    L.append("")
    L.append("| ID | 文件名 | 来源 | 标准 | 类型 | 语言 | 已填充 | 合规分 | 行数 | 表格 | 约束 |")
    L.append("|----|--------|------|------|------|------|--------|--------|------|------|------|")
    for d in gjb_docs:
        L.append(
            f"| {d['id']} | {d['filename']} | {d['source']} | {d['standard']} | "
            f"{d['system_type']} | {d['language']} | {'是' if d['is_filled'] else '否'} | "
            f"{d['compliance_score']} | {d['line_count']} | {d['table_count']} | {d['constraint_count']} |"
        )
    L.append("")

    # ---- 9. Conflict type distribution ----
    L.append("## 9. 潜在冲突类型分布")
    L.append("")
    pc = stats["potential_conflict_types"]
    L.append("| 冲突类型 | 估计文档数 | 说明 |")
    L.append("|----------|-----------|------|")
    L.append(f"| 同参数不同值 (same_param_diff_value) | {pc['same_param_diff_value']} | 含较多约束、可能存在同名参数取值冲突 |")
    L.append(f"| 文本-表格不一致 (text_table_mismatch) | {pc['text_table_mismatch']} | GJB 文档含表格，文本与表格可能不一致 |")
    L.append(f"| 逻辑不可满足 (logic_unsatisfiable) | {pc['logic_unsatisfiable']} | 约束密集，可能存在逻辑矛盾 |")
    L.append(f"| 格式违规 (format_violation) | {pc['format_violation']} | GJB 已填充文档合规分 < 8 |")
    L.append("")
    L.append("```mermaid")
    L.append("pie title 潜在冲突类型分布")
    for k, v in pc.items():
        L.append(f'    "{k} ({v})" : {v}')
    L.append("```")
    L.append("")

    # ---- 10. Data quality assessment ----
    L.append("## 10. 数据质量评估")
    L.append("")
    filled_gjb = [d for d in catalog if d["is_gjb_format"] and d["is_filled"]]
    high_quality = [d for d in filled_gjb if d["compliance_score"] >= 8]
    medium = [d for d in filled_gjb if 4 <= d["compliance_score"] < 8]
    low = [d for d in filled_gjb if d["compliance_score"] < 4]
    L.append(f"- GJB 已填充文档: **{len(filled_gjb)}** 个")
    L.append(f"  - 高质量 (合规分 ≥ 8): **{len(high_quality)}** 个")
    L.append(f"  - 中等 (4 ≤ 分 < 8): **{len(medium)}** 个")
    L.append(f"  - 较低 (分 < 4): **{len(low)}** 个")
    L.append(f"- 含约束文档: **{sum(1 for d in catalog if d['has_constraints'])}** 个，约束总数 {stats['total_constraints']}")
    L.append(f"- 含表格文档: **{sum(1 for d in catalog if d['table_count'] > 0)}** 个，表格总数 {stats['total_tables']}")
    L.append("")
    L.append("**质量评估说明**：合规评分基于 GJB 438C 标准章节结构覆盖度（范围/引用文件/需求/合格性规定/需求可追踪性 等），满分 10。"
             "PDF/DOCX 等二进制文档无法解析正文，仅依据文件名与来源给出保守评分。")
    L.append("")

    # ---- 11. Recommended Top 20 ----
    L.append("## 11. 推荐用于一致性检测的文档 (Top 20)")
    L.append("")
    L.append("按 `合规分 × 2 + 约束数/10 + 表格数 + min(行数,2000)/200` 综合排序，优先选择已填充、章节齐全、含约束与表格的 GJB 文档。")
    L.append("")

    def quality_rank(d):
        return (
            d["compliance_score"] * 2
            + d["constraint_count"] / 10.0
            + d["table_count"]
            + min(d["line_count"], 2000) / 200.0
            + (5 if d["is_filled"] else 0)
        )

    candidates = [d for d in catalog if d["is_gjb_format"] and d["is_filled"] and d["format"] in TEXT_FORMATS]
    candidates.sort(key=quality_rank, reverse=True)
    top = candidates[:20]
    L.append("| 排名 | ID | 文件名 | 来源 | 合规分 | 行数 | 表格 | 约束 | 综合分 |")
    L.append("|------|----|--------|------|--------|------|------|------|--------|")
    for rank, d in enumerate(top, 1):
        L.append(
            f"| {rank} | {d['id']} | {d['filename']} | {d['source']} | "
            f"{d['compliance_score']} | {d['line_count']} | {d['table_count']} | "
            f"{d['constraint_count']} | {quality_rank(d):.2f} |"
        )
    if not top:
        L.append("| - | - | (无符合条件的可读 GJB 文档) | - | - | - | - | - | - |")
    L.append("")

    # ---- 12. Per-source detail ----
    L.append("## 12. 各来源明细")
    L.append("")
    for src in stats["by_source"]:
        docs = [d for d in catalog if d["source"] == src]
        gjb = sum(1 for d in docs if d["is_gjb_format"])
        filled = sum(1 for d in docs if d["is_filled"])
        cons = sum(d["constraint_count"] for d in docs)
        L.append(f"### {src} ({len(docs)} 个文件)")
        L.append("")
        L.append(f"- GJB 格式: {gjb}，已填充: {filled}，约束总数: {cons}")
        fmts = Counter(d["format"] for d in docs)
        L.append(f"- 格式分布: {dict(fmts.most_common())}")
        L.append("")

    (OUT_DIR / "DATASET_REPORT.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
