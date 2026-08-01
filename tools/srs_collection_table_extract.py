#!/usr/bin/env python3
"""
SRS Collection Table Extractor
扫描 srs_collection 下所有 .md 文件，提取 HTML 表格和 Markdown 表格并分类。

表格格式支持:
  1. HTML 表格: <table>...</table>
  2. Markdown 表格: | col1 | col2 | 后跟 |---|---|

表格分类:
  - modification:  表头含 "序号"+"版本号"+"标记"
  - reference:     表头含 "序号"+"名称"+"版本"
  - qualification: 表头含 "需求名称"+"标识"+"合格性方法" (或 "状态/方式")
  - traceability:  表头含 "可行性研究报告" 或 "总体目标" 或 "追溯"
  - interface:     表头含 "接口"+"信号"
  - data:          表头含 "数据"+"类型"
  - other:         其他
"""

import json
import re
import glob
import os
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION_DIR = REPO_ROOT / "data" / "gjb_438c" / "srs_collection"
OUTPUT_ALL_TABLES = COLLECTION_DIR / "all_tables.json"
OUTPUT_STATISTICS = COLLECTION_DIR / "table_statistics.json"


# ---------------------------------------------------------------------------
# HTML table parser
# ---------------------------------------------------------------------------

class HTMLTableParser(HTMLParser):
    """Parse HTML <table> into headers + rows."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self._table = None
        self._row = None
        self._cell = None
        self._is_header_cell = False
        self._in_table = False
        self._in_row = False
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._table = {"headers": [], "rows": []}
            self._in_table = True
        elif tag == "tr" and self._in_table:
            self._row = []
            self._in_row = True
        elif tag in ("td", "th") and self._in_row:
            self._cell = ""
            self._is_header_cell = (tag == "th")
            self._in_cell = True

    def handle_data(self, data):
        if self._in_cell:
            self._cell += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_cell:
            text = self._cell.strip()
            if self._row is not None:
                self._row.append({"text": text, "is_header": self._is_header_cell})
            self._cell = None
            self._in_cell = False
        elif tag == "tr" and self._row is not None:
            if self._table is not None:
                row_texts = [c["text"] for c in self._row]
                if not self._table["headers"] and any(c["is_header"] for c in self._row):
                    self._table["headers"] = row_texts
                else:
                    self._table["rows"].append(row_texts)
            self._row = None
            self._in_row = False
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
            self._in_table = False


# ---------------------------------------------------------------------------
# Table extraction helpers
# ---------------------------------------------------------------------------

def _find_section(lines: list, table_start_line: int) -> str:
    """Find the nearest preceding markdown header (# ...) before the table."""
    for j in range(table_start_line - 1, -1, -1):
        stripped = lines[j].lstrip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _split_md_row(line: str) -> list:
    """Split a markdown table row into cell values."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells = line.split("|")
    return [c.strip() for c in cells]


def _is_separator_row(line: str) -> bool:
    """Check if a line is a markdown table separator (|---|---| or |:--:|)."""
    stripped = line.strip()
    if not stripped or "|" not in stripped:
        return False
    # Remove leading/trailing pipes
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    parts = stripped.split("|")
    if len(parts) < 1:
        return False
    for p in parts:
        p = p.strip()
        if not p:
            return False
        # Must be dashes/colons only: ---, :--, --:, :--:
        if not re.match(r"^:?-+:?$", p):
            return False
    return True


def _is_table_row(line: str) -> bool:
    """Check if a line looks like a markdown table data row."""
    stripped = line.strip()
    if not stripped:
        return False
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 1


def extract_markdown_tables(content: str, lines: list) -> list:
    """Extract markdown-style tables from file content."""
    tables = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # Look for potential header row: must have | and at least one cell
        if _is_table_row(line) and i + 1 < n and _is_separator_row(lines[i + 1]):
            # Found a markdown table
            header_cells = _split_md_row(line)
            # Filter out completely empty headers (degenerate)
            if not any(h for h in header_cells):
                i += 1
                continue

            rows = []
            j = i + 2  # skip header + separator
            while j < n and _is_table_row(lines[j]):
                row_cells = _split_md_row(lines[j])
                rows.append(row_cells)
                j += 1

            section = _find_section(lines, i)
            tables.append({
                "headers": header_cells,
                "rows": rows,
                "line": i + 1,
                "section": section,
                "format": "markdown",
            })
            i = j
        else:
            i += 1
    return tables


def extract_html_tables(content: str, lines: list) -> list:
    """Extract HTML <table> blocks from file content."""
    tables = []
    pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(content):
        html = match.group(0)
        parser = HTMLTableParser()
        try:
            parser.feed(html)
        except Exception:
            continue
        for t in parser.tables:
            if not t["headers"] and not t["rows"]:
                continue
            # Calculate approximate line number
            line_num = content[:match.start()].count("\n") + 1
            section = _find_section(lines, line_num)
            tables.append({
                "headers": t["headers"],
                "rows": t["rows"],
                "line": line_num,
                "section": section,
                "format": "html",
            })
    return tables


def extract_all_tables(content: str) -> list:
    """Extract all tables (markdown + HTML) from file content."""
    lines = content.splitlines()
    md_tables = extract_markdown_tables(content, lines)
    html_tables = extract_html_tables(content, lines)
    # Merge and sort by line number
    all_tables = md_tables + html_tables
    all_tables.sort(key=lambda t: t["line"])
    return all_tables


# ---------------------------------------------------------------------------
# Table classification
# ---------------------------------------------------------------------------

def classify_table(headers: list, rows: list) -> str:
    """Classify table type based on header text."""
    headers_text = " ".join(str(h) for h in headers)
    # Remove markdown bold markers for matching
    headers_clean = headers_text.replace("**", "").replace("__", "")

    # modification: 序号 + 版本号 + 标记
    if "序号" in headers_clean and "版本号" in headers_clean and "标记" in headers_clean:
        return "modification"

    # reference: 序号 + 名称 + 版本
    if "序号" in headers_clean and "名称" in headers_clean and "版本" in headers_clean:
        return "reference"

    # qualification: 需求名称 + 标识 + 合格性方法, or 状态/方式
    if ("需求名称" in headers_clean and "合格性方法" in headers_clean):
        return "qualification"
    if "状态/方式" in headers_clean or ("状态" in headers_clean and "方式" in headers_clean and "演示方式" in headers_clean):
        return "qualification"

    # traceability: 可行性研究报告 or 总体目标 or 追溯
    if "可行性研究报告" in headers_clean or "总体目标" in headers_clean:
        return "traceability"
    if "追溯" in headers_clean:
        return "traceability"

    # interface: 接口 + 信号
    if "接口" in headers_clean and "信号" in headers_clean:
        return "interface"

    # data: 数据 + 类型
    if "数据" in headers_clean and "类型" in headers_clean:
        return "data"

    return "other"


def is_empty_table(headers: list, rows: list) -> bool:
    """Check if a table is an empty template (all data cells blank)."""
    if not rows:
        return True
    for row in rows:
        for cell in row:
            cell_text = str(cell).strip()
            if cell_text and cell_text not in ("-", "", "—", "N/A", "n/a"):
                return False
    return True


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def get_source_dir(md_path: Path) -> str:
    """Get the relative directory path from srs_collection/."""
    try:
        rel = md_path.relative_to(COLLECTION_DIR)
        return str(rel.parent)
    except ValueError:
        return str(md_path.parent)


def process_file(md_path: Path) -> list:
    """Process a single .md file and return list of table records."""
    try:
        content = md_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        print(f"  [ERROR] Cannot read {md_path}: {e}")
        return []

    tables = extract_all_tables(content)
    results = []
    for idx, table in enumerate(tables):
        headers = table["headers"]
        rows = table["rows"]
        table_type = classify_table(headers, rows)
        empty = is_empty_table(headers, rows)

        # Normalize col_count: use max of header length and row lengths
        col_count = len(headers)
        for row in rows:
            if len(row) > col_count:
                col_count = len(row)

        record = {
            "file": md_path.name,
            "file_path": str(md_path.relative_to(REPO_ROOT)),
            "source_dir": get_source_dir(md_path),
            "table_index": idx,
            "table_type": table_type,
            "format": table["format"],
            "headers": [str(h) for h in headers],
            "row_count": len(rows),
            "col_count": col_count,
            "is_empty": empty,
            "section": table["section"],
            "line": table["line"],
        }
        results.append(record)
    return results


def compute_statistics(all_tables: list, all_files: list, files_with_tables: set) -> dict:
    """Compute summary statistics."""
    total_tables = len(all_tables)

    # By type
    by_type = defaultdict(int)
    for t in all_tables:
        by_type[t["table_type"]] += 1

    # By source_dir
    by_source = defaultdict(int)
    for t in all_tables:
        by_source[t["source_dir"]] += 1

    # Empty vs filled
    empty_count = sum(1 for t in all_tables if t["is_empty"])
    filled_count = total_tables - empty_count

    # Average rows/cols
    avg_rows = sum(t["row_count"] for t in all_tables) / total_tables if total_tables else 0
    avg_cols = sum(t["col_count"] for t in all_tables) / total_tables if total_tables else 0

    # By format
    by_format = defaultdict(int)
    for t in all_tables:
        by_format[t["format"]] += 1

    # Documents
    total_docs = len(all_files)
    docs_with_tables = len(files_with_tables)
    docs_without_tables = total_docs - docs_with_tables

    return {
        "generated_at": datetime.now().isoformat(),
        "total_tables": total_tables,
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "by_format": dict(sorted(by_format.items(), key=lambda x: -x[1])),
        "by_source": dict(sorted(by_source.items(), key=lambda x: -x[1])),
        "empty_template_tables": empty_count,
        "filled_tables": filled_count,
        "avg_row_count": round(avg_rows, 2),
        "avg_col_count": round(avg_cols, 2),
        "total_documents": total_docs,
        "documents_with_tables": docs_with_tables,
        "documents_without_tables": docs_without_tables,
    }


def main():
    print("=" * 70)
    print("SRS Collection Table Extractor")
    print("=" * 70)

    # Find all .md files
    pattern = str(COLLECTION_DIR / "**" / "*.md")
    md_files = sorted(glob.glob(pattern, recursive=True))
    print(f"Found {len(md_files)} .md files in {COLLECTION_DIR}")

    all_tables = []
    files_with_tables = set()
    files_no_tables = []

    for md_file in md_files:
        md_path = Path(md_file)
        tables = process_file(md_path)
        if tables:
            files_with_tables.add(md_path.name)
            all_tables.extend(tables)
            type_summary = defaultdict(int)
            for t in tables:
                type_summary[t["table_type"]] += 1
            type_str = ", ".join(f"{k}:{v}" for k, v in sorted(type_summary.items()))
            print(f"  [{len(tables):3d} tables] {md_path.relative_to(COLLECTION_DIR)}  ({type_str})")
        else:
            files_no_tables.append(md_path.name)

    # Write all_tables.json
    OUTPUT_ALL_TABLES.write_text(
        json.dumps(all_tables, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nWrote {len(all_tables)} tables to {OUTPUT_ALL_TABLES}")

    # Compute and write statistics
    stats = compute_statistics(all_tables, md_files, files_with_tables)
    OUTPUT_STATISTICS.write_text(
        json.dumps(stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Wrote statistics to {OUTPUT_STATISTICS}")

    # Print summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total documents scanned:     {stats['total_documents']}")
    print(f"Documents with tables:       {stats['documents_with_tables']}")
    print(f"Documents without tables:    {stats['documents_without_tables']}")
    print(f"Total tables extracted:      {stats['total_tables']}")
    print(f"  Markdown tables:           {stats['by_format'].get('markdown', 0)}")
    print(f"  HTML tables:               {stats['by_format'].get('html', 0)}")
    print(f"  Empty template tables:     {stats['empty_template_tables']}")
    print(f"  Filled tables:             {stats['filled_tables']}")
    print(f"  Avg rows per table:        {stats['avg_row_count']}")
    print(f"  Avg cols per table:        {stats['avg_col_count']}")
    print(f"\nBy type:")
    for t, count in stats["by_type"].items():
        print(f"  {t:25s} {count}")
    print(f"\nBy source (top 15):")
    for src, count in list(stats["by_source"].items())[:15]:
        print(f"  {src:50s} {count}")


if __name__ == "__main__":
    main()
