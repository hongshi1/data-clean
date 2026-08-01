#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描 srs_collection/{nasa,ieee830,pure_extended} 子目录, 为每个
.md / .pdf / .docx / .txt 文件收集细粒度元数据。

输出:
  data/gjb_438c/srs_collection/public_metadata.json         # 逐文件元数据列表
  data/gjb_438c/srs_collection/public_metadata_summary.json # 统计汇总

用法:
  python3 tools/srs_public_metadata_collect.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------- #
# 路径
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]
COLLECTION_DIR = ROOT / "data" / "gjb_438c" / "srs_collection"

SOURCE_DIRS = ["nasa", "ieee830", "pure_extended"]
TARGET_EXTS = {".md", ".pdf", ".docx", ".txt"}

OUT_META = COLLECTION_DIR / "public_metadata.json"
OUT_SUMMARY = COLLECTION_DIR / "public_metadata_summary.json"

# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
SHALL_RE = re.compile(r"\bshall\b", re.IGNORECASE)

# 需求 ID 模式 (按优先级匹配)
REQ_ID_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("REQ-xxx-n",   re.compile(r"\bREQ[-_]\d+", re.IGNORECASE)),
    ("FR-n",        re.compile(r"\bFR[-_]\d+", re.IGNORECASE)),
    ("R-n.n",       re.compile(r"\bR\d+\.\d+\b")),
    ("R-n",         re.compile(r"\bR\d+\b")),
    ("UC-n",        re.compile(r"\bUC[-_ ]?\d+", re.IGNORECASE)),
    ("REQ-n",       re.compile(r"\bREQ\d+\b", re.IGNORECASE)),
    ("n.n.n",       re.compile(r"(?m)^\s*(\d+\.){2,}\d+\s")),
    ("shall-n",     re.compile(r"shall[-_ ]?\d+", re.IGNORECASE)),
]

# 数值约束 (带单位 / 比较符 / 范围)
NUM_CONSTRAINT_RES = [
    re.compile(r"\d+\s*(?:ms|milliseconds?|s\b|seconds?|sec|min|minutes?|hours?|h\b)"),
    re.compile(r"\d+\s*(?:%|percent)"),
    re.compile(r"\d+\s*(?:B|KB|MB|GB|TB|bps|Kbps|Mbps|Gbps|Hz|kHz|MHz|GHz)"),
    re.compile(r"\d+\s*(?:°C|°F|celsius|fahrenheit|kelvin)", re.IGNORECASE),
    re.compile(r"\d+\s*(?:kg|g|km|m|cm|mm|mile|inch|foot|feet)", re.IGNORECASE),
    re.compile(r"[±≤≥<>]=?\s*\d+|\d+\s*[±≤≥<>]=?"),
    re.compile(r"\b(?:at least|at most|within|no (?:more|less) than|minimum|maximum|between)\s+\d+",
               re.IGNORECASE),
    re.compile(r"\d+\s*[-~–到]\s*\d+\s*(?:ms|s|sec|min|%|MB|GB|Hz)"),
]

# 模板 / 非填充 SRS 标记
TEMPLATE_MARKERS = [
    "lorem ipsum", "{{", "}}", "<project name>", "<author>", "<date",
    "{{project", "{{author", "{{organization", "placeholder",
    "your text here", "insert here", "tbd", "todo:",
]

# 系统类型关键词
SYS_KEYWORDS = {
    "aerospace": [
        "aerospace", "aircraft", "flight", "spacecraft", "satellite", "orbit",
        "nasa", "cfs", "cfe", "fprime", "f prime", "ccsds", "hdtn", "cryptolib",
        "space data link", "sdls", "telemetry", "command and data handling",
        "launch vehicle", "rocket", "avionics", "mil-std-498", "mil std 498",
        "guidance", "navigation", "attitude", "propulsion",
    ],
    "web": [
        "website", "web application", "web app", "web-based", "e-commerce",
        "ecommerce", "online shop", "online store", "portal", "browser",
        "html", "http", "rest api", "web portal", "web site", "online platform",
    ],
    "education": [
        "course", "student", "university", "school", "exam", "learning",
        "education", "teaching", "campus", "classroom", "enrollment",
        "lms", "learning management",
    ],
}

# 标准关键词
STD_KEYWORDS = [
    ("NASA",       ["nasa", "tm-2024", "nasa/tm", "nasa technical memorandum"]),
    ("MIL-STD-498", ["mil-std-498", "mil std 498", "military standard 498", "did template"]),
    ("GJB",        ["gjb 438", "gjb438", "gjb 1330"]),
    ("ESA",        ["esa pss", "ecss-", "ecss "]),
    ("ISO29148",   ["iso/ieC/ieee 29148", "iso/iec/ieee 29148", "ieee 29148",
                    "iso 29148", "29148:2018", "29148:2011"]),
    ("IEEE830",    ["ieee 830", "ieee std 830", "ieee830", "830-1998"]),
]


def detect_language(text: str) -> str:
    """简单语言检测: zh / en / ja"""
    if not text:
        return "unknown"
    cjk = 0
    hira = kata = 0
    for ch in text[:20000]:
        cp = ord(ch)
        if 0x4E00 <= cp <= 0x9FFF:
            cjk += 1
        elif 0x3040 <= cp <= 0x309F:
            hira += 1
        elif 0x30A0 <= cp <= 0x30FF:
            kata += 1
    kana = hira + kata
    # 日文: 含假名 (即使少量也基本可判定)
    if kana > 0 and kana >= cjk * 0.05:
        return "ja"
    if cjk > 50:
        return "zh"
    if cjk > 0 and kana == 0:
        return "zh"
    return "en"


def infer_standard(text: str, source_dir: str, filename: str) -> str:
    low = (text[:8000] + " " + filename).lower()
    for std, kws in STD_KEYWORDS:
        for kw in kws:
            if kw in low:
                return std
    # 兜底: 按来源
    if source_dir == "nasa":
        return "NASA"
    if source_dir == "ieee830":
        return "IEEE830"
    if source_dir == "pure_extended":
        return "PURE"
    return "unknown"


def count_md_tables(text: str) -> int:
    """统计 Markdown 表格块数 (连续的 | 起始行, 含分隔行)"""
    count = 0
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        is_row = stripped.startswith("|") and stripped.endswith("|")
        if is_row:
            if not in_table:
                count += 1
                in_table = True
        else:
            in_table = False
    return count


def detect_req_ids(text: str) -> tuple[bool, str]:
    """检测需求 ID 模式, 返回 (是否存在, 模式描述)"""
    for label, pat in REQ_ID_PATTERNS:
        if pat.search(text):
            return True, label
    return False, ""


def has_numerical_constraints(text: str) -> bool:
    for pat in NUM_CONSTRAINT_RES:
        if pat.search(text):
            return True
    return False


def infer_system_type(text: str, filename: str) -> str:
    low = (text[:10000] + " " + filename).lower()
    scores = {k: 0 for k in SYS_KEYWORDS}
    for sys_type, kws in SYS_KEYWORDS.items():
        for kw in kws:
            if kw in low:
                scores[sys_type] += 1
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "unknown"
    return best


def extract_title(text: str, filename: str, fmt: str) -> str:
    if fmt == "MD":
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("# "):
                return s[2:].strip()
        # 退回到首个非空行
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s[:120]
        return filename
    if fmt == "TXT":
        for line in text.splitlines():
            s = line.strip()
            if s:
                return s[:120]
        return filename
    if fmt == "DOCX":
        return Path(filename).stem
    # PDF: 调用方传入 text (前几页文字)
    for line in text.splitlines():
        s = line.strip()
        if s:
            return s[:120]
    return filename


def is_template(text: str, filename: str) -> bool:
    fn = filename.lower()
    if any(k in fn for k in ("template", "did_", "did-", "_did", "bare",
                              "readme", "catalog", "analysis", "sample")):
        return True
    low = text[:6000].lower()
    hits = sum(1 for m in TEMPLATE_MARKERS if m in low)
    if hits >= 2:
        return True
    return False


# --------------------------------------------------------------------------- #
# 文件解析
# --------------------------------------------------------------------------- #
def analyze_text(text: str, filename: str, source_dir: str, fmt: str
                 ) -> dict:
    """对已读取的文本内容做元数据分析 (MD/TXT/PDF文本通用)"""
    lines = text.splitlines()
    line_count = len(lines)
    shall_count = len(SHALL_RE.findall(text))
    has_shall = shall_count > 0

    table_count = count_md_tables(text) if fmt == "MD" else 0
    # TXT/PDF 的表格在各自解析阶段统计
    has_tables = table_count > 0

    has_num = has_numerical_constraints(text)
    has_req, req_pat = detect_req_ids(text)

    template = is_template(text, filename)
    # is_filled: 有实质 shall / 数值约束 / 需求ID, 且非模板, 且有足够行
    is_filled = (not template) and line_count > 20 and (
        shall_count >= 2 or has_num or has_req
    )

    title = extract_title(text, filename, fmt)
    language = detect_language(text)
    standard = infer_standard(text, source_dir, filename)
    system_type = infer_system_type(text, filename)

    return {
        "line_count": line_count,
        "language": language,
        "standard": standard,
        "is_filled": is_filled,
        "has_shall": has_shall,
        "shall_count": shall_count,
        "has_tables": has_tables,
        "table_count": table_count,
        "has_numerical_constraints": has_num,
        "has_requirement_ids": has_req,
        "req_id_pattern": req_pat,
        "system_type": system_type,
        "title": title,
    }


def read_text_file(path: Path) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="ignore")


def parse_pdf(path: Path) -> dict:
    """用 pdfplumber 提取页数/前几页文字/表格数/shall数"""
    import pdfplumber

    page_count = 0
    table_count = 0
    shall_count = 0
    first_pages_text = []
    full_text_sample = []  # 用于语言/系统类型/标准/数值约束判断 (限制长度)

    try:
        with pdfplumber.open(str(path)) as pdf:
            page_count = len(pdf.pages)
            max_full_pages = min(page_count, 60)  # 全文分析前60页
            for i, page in enumerate(pdf.pages):
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                if i < 3 and txt:
                    first_pages_text.append(txt)
                if i < max_full_pages:
                    full_text_sample.append(txt)
                    shall_count += len(SHALL_RE.findall(txt))
                # 表格
                try:
                    tables = page.find_tables()
                    if tables:
                        table_count += len(tables)
                except Exception:
                    pass
                if i >= max_full_pages and i >= 3:
                    # 仍可继续统计 shall/table 直到末页, 但跳过文本采样
                    try:
                        tables = page.find_tables()
                        if tables:
                            table_count += len(tables)
                    except Exception:
                        pass
                    if txt and i < page_count:
                        shall_count += len(SHALL_RE.findall(txt))
    except Exception as e:
        return {
            "page_count": 0,
            "pdf_error": str(e)[:200],
            "_text": "",
            "table_count": 0,
            "shall_count": 0,
        }

    first_text = "\n".join(first_pages_text)
    sample_text = "\n".join(full_text_sample) if full_text_sample else first_text
    return {
        "page_count": page_count,
        "_text": sample_text,
        "first_text": first_text,
        "table_count": table_count,
        "shall_count": shall_count,
        "pdf_error": None,
    }


def parse_docx(path: Path) -> dict:
    """DOCX: 仅记录文件大小, 尝试提取段落数与标题"""
    try:
        import docx
        doc = docx.Document(str(path))
        para_count = len(doc.paragraphs)
        title = ""
        for p in doc.paragraphs:
            if p.text.strip():
                title = p.text.strip()[:120]
                break
        table_count = len(doc.tables)
        return {"para_count": para_count, "title": title,
                "table_count": table_count}
    except Exception as e:
        return {"para_count": 0, "title": path.stem,
                "table_count": 0, "docx_error": str(e)[:200]}


# --------------------------------------------------------------------------- #
# 主收集流程
# --------------------------------------------------------------------------- #
def collect_file(path: Path, source_dir: str) -> dict:
    rel = path.relative_to(COLLECTION_DIR).as_posix()
    ext = path.suffix.lower()
    fmt = {".md": "MD", ".pdf": "PDF", ".docx": "DOCX", ".txt": "TXT"}[ext]
    size = path.stat().st_size

    meta = {
        "file_path": rel,
        "filename": path.name,
        "source_dir": source_dir,
        "file_size_bytes": size,
        "format": fmt,
    }

    if fmt == "MD" or fmt == "TXT":
        text = read_text_file(path)
        info = analyze_text(text, path.name, source_dir, fmt)
        meta.update(info)
        meta["page_count"] = None
    elif fmt == "PDF":
        pdf = parse_pdf(path)
        text = pdf.pop("_text", "")
        first_text = pdf.pop("first_text", "")
        # 用 sample 文本做分析
        info = analyze_text(text if text else first_text, path.name,
                            source_dir, "PDF")
        # 覆盖表格/shall 为 PDF 专用统计 (更准)
        info["table_count"] = pdf["table_count"]
        info["has_tables"] = pdf["table_count"] > 0
        info["shall_count"] = pdf["shall_count"]
        info["has_shall"] = pdf["shall_count"] > 0
        # 标题用首页文字
        info["title"] = extract_title(first_text, path.name, "PDF")
        meta.update(info)
        meta["page_count"] = pdf.get("page_count", 0)
        if pdf.get("pdf_error"):
            meta["pdf_error"] = pdf["pdf_error"]
    elif fmt == "DOCX":
        d = parse_docx(path)
        meta["line_count"] = d.get("para_count", 0)
        meta["language"] = "unknown"
        # 标准按来源兜底
        meta["standard"] = infer_standard("", source_dir, path.name)
        meta["is_filled"] = d.get("para_count", 0) > 20
        meta["has_shall"] = False
        meta["shall_count"] = 0
        meta["has_tables"] = d.get("table_count", 0) > 0
        meta["table_count"] = d.get("table_count", 0)
        meta["has_numerical_constraints"] = False
        meta["has_requirement_ids"] = False
        meta["req_id_pattern"] = ""
        meta["system_type"] = "unknown"
        meta["title"] = d.get("title") or path.stem
        meta["page_count"] = None
        if d.get("docx_error"):
            meta["docx_error"] = d["docx_error"]

    # 字段顺序对齐 schema
    ordered = {}
    schema = [
        "file_path", "filename", "source_dir", "file_size_bytes",
        "line_count", "format", "language", "standard", "is_filled",
        "has_shall", "shall_count", "has_tables", "table_count",
        "has_numerical_constraints", "has_requirement_ids",
        "req_id_pattern", "system_type", "title", "page_count",
    ]
    for k in schema:
        ordered[k] = meta.get(k)
    # 附加错误信息 (如有)
    for k in ("pdf_error", "docx_error"):
        if k in meta:
            ordered[k] = meta[k]
    return ordered


def main() -> int:
    if not COLLECTION_DIR.exists():
        print(f"[ERR] collection dir not found: {COLLECTION_DIR}", file=sys.stderr)
        return 1

    records: list[dict] = []
    for src in SOURCE_DIRS:
        base = COLLECTION_DIR / src
        if not base.exists():
            print(f"[WARN] missing source dir: {base}", file=sys.stderr)
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TARGET_EXTS:
                continue
            # 跳过明显的辅助报告/索引文件 (顶层 .md 报告)
            if path.name in ("ANALYSIS_REPORT.md", "CATALOG.md",
                             "DOWNLOAD_METADATA.md"):
                continue
            try:
                rec = collect_file(path, src)
                records.append(rec)
                tag = "OK"
                if rec.get("pdf_error") or rec.get("docx_error"):
                    tag = "WARN"
                print(f"[{tag}] {src:14s} {rec['format']:4s} "
                      f"{rec['filename'][:50]:50s} "
                      f"lines={rec['line_count']} shall={rec['shall_count']}")
            except Exception as e:
                print(f"[FAIL] {path}: {e}", file=sys.stderr)

    OUT_META.write_text(json.dumps(records, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n[SAVED] {OUT_META}  ({len(records)} files)")

    # ---------------- 统计汇总 ---------------- #
    def dist(field):
        return dict(Counter(r.get(field) for r in records))

    by_source = dist("source_dir")
    by_format = dist("format")
    by_language = dist("language")
    by_standard = dist("standard")
    by_system = dist("system_type")

    has_tables_n = sum(1 for r in records if r.get("has_tables"))
    has_num_n = sum(1 for r in records if r.get("has_numerical_constraints"))
    has_req_n = sum(1 for r in records if r.get("has_requirement_ids"))
    has_shall_n = sum(1 for r in records if r.get("has_shall"))
    is_filled_n = sum(1 for r in records if r.get("is_filled"))

    # 平均页数 (仅 PDF) / 平均行数 (MD/TXT)
    pdf_pages = [r["page_count"] for r in records
                 if r.get("format") == "PDF" and r.get("page_count")]
    md_lines = [r["line_count"] for r in records
                if r.get("format") in ("MD", "TXT") and r.get("line_count")]

    summary = {
        "total_files": len(records),
        "by_source_dir": by_source,
        "by_format": by_format,
        "by_language": by_language,
        "by_standard": by_standard,
        "by_system_type": by_system,
        "docs_with_tables": has_tables_n,
        "docs_with_numerical_constraints": has_num_n,
        "docs_with_requirement_ids": has_req_n,
        "docs_with_shall": has_shall_n,
        "docs_is_filled": is_filled_n,
        "pdf_page_stats": {
            "count": len(pdf_pages),
            "total_pages": sum(pdf_pages),
            "avg_pages": round(sum(pdf_pages) / len(pdf_pages), 2)
            if pdf_pages else 0,
            "max_pages": max(pdf_pages) if pdf_pages else 0,
            "min_pages": min(pdf_pages) if pdf_pages else 0,
        },
        "md_txt_line_stats": {
            "count": len(md_lines),
            "total_lines": sum(md_lines),
            "avg_lines": round(sum(md_lines) / len(md_lines), 2)
            if md_lines else 0,
            "max_lines": max(md_lines) if md_lines else 0,
            "min_lines": min(md_lines) if md_lines else 0,
        },
        "shall_count_stats": {
            "total_shall": sum(r.get("shall_count", 0) for r in records),
            "avg_shall": round(
                sum(r.get("shall_count", 0) for r in records) / len(records), 2
            ) if records else 0,
            "max_shall": max((r.get("shall_count", 0) for r in records),
                             default=0),
        },
    }

    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(f"[SAVED] {OUT_SUMMARY}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
