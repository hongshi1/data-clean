#!/usr/bin/env python3
"""
SRS Table Parser
从MinerU的HTML表格中提取结构化数据。

表格类型:
  - modification: 修改页 (空模板)
  - reference: 引用文档
  - qualification: 合格性规定 (需求ID/名称/方法/级别)
  - traceability_forward: 正向追踪 (系统需求→SRS需求)
  - traceability_backward: 逆向追踪 (SRS需求→系统需求)
  - interface: 接口表
  - other: 其他
"""

import json
import re
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
SRS_DIR = REPO_ROOT / "data" / "gjb_438c" / "mineru_srs"
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_tables"


class TableParser(HTMLParser):
    """Parse HTML table into structured rows with rowspan/colspan handling."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.cell_colspan = 1
        self.cell_rowspan = 1
        self.in_table = False
        self.in_row = False
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "table":
            self.current_table = {"headers": [], "rows": []}
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.current_row = []
            self.in_row = True
        elif tag in ("td", "th") and self.in_row:
            self.current_cell = ""
            self.cell_colspan = int(attrs_dict.get("colspan", 1))
            self.cell_rowspan = int(attrs_dict.get("rowspan", 1))
            self.in_cell = True

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            cell_text = self.current_cell.strip()
            if self.current_row is not None:
                self.current_row.append({
                    "text": cell_text,
                    "colspan": self.cell_colspan,
                    "rowspan": self.cell_rowspan,
                })
            self.current_cell = None
            self.in_cell = False
        elif tag == "tr" and self.current_row is not None:
            if self.current_table:
                if not self.current_table["headers"]:
                    self.current_table["headers"] = self.current_row
                else:
                    self.current_table["rows"].append(self.current_row)
            self.current_row = None
            self.in_row = False
        elif tag == "table" and self.current_table:
            self.tables.append(self.current_table)
            self.current_table = None
            self.in_table = False


def extract_tables_from_md(md_path: Path) -> list:
    """Extract all HTML tables from markdown file."""
    content = md_path.read_text(encoding="utf-8", errors="replace")

    # Find table positions in the markdown (which section they belong to)
    lines = content.splitlines()
    table_positions = []

    for i, line in enumerate(lines):
        if "<table>" in line:
            # Find the nearest preceding header
            section = ""
            for j in range(i - 1, -1, -1):
                if lines[j].lstrip().startswith("#"):
                    section = lines[j].lstrip().lstrip("#").strip()
                    break
            table_positions.append({"line": i + 1, "section": section})

    # Extract tables
    tables = []
    pattern = re.compile(r"<table>(.*?)</table>", re.DOTALL)
    for match in pattern.finditer(content):
        parser = TableParser()
        parser.feed(f"<table>{match.group(1)}</table>")
        for t in parser.tables:
            if t["headers"] or t["rows"]:
                tables.append(t)

    # Add position info
    for i, table in enumerate(tables):
        if i < len(table_positions):
            table["line"] = table_positions[i]["line"]
            table["section"] = table_positions[i]["section"]
        else:
            table["line"] = 0
            table["section"] = ""

    return tables


def classify_table(table: dict) -> str:
    """Classify table type based on headers."""
    headers_text = " ".join(h["text"] for h in table.get("headers", []))

    if "序号" in headers_text and "版本号" in headers_text and "标记" in headers_text:
        return "modification"
    if "序号" in headers_text and "名称" in headers_text and "版本" in headers_text:
        return "reference"
    if "需求名称" in headers_text or "需求的唯一标识" in headers_text:
        return "qualification"
    if "可行性研究报告" in headers_text or "总体目标" in headers_text:
        return "traceability"
    if "接口" in headers_text or "信号" in headers_text:
        return "interface"
    if "数据" in headers_text and "类型" in headers_text:
        return "data_dictionary"
    return "other"


def simplify_table(table: dict) -> dict:
    """Extract simple text rows from table (handling colspan/rowspan)."""
    headers = [h["text"] for h in table.get("headers", [])]
    rows = []
    for row in table.get("rows", []):
        simple_row = [cell["text"] for cell in row]
        rows.append(simple_row)
    return {"headers": headers, "rows": rows}


def extract_qualification_data(table: dict) -> list:
    """Extract requirement data from qualification table."""
    result = []
    simple = simplify_table(table)
    headers = simple["headers"]

    # Find column indices
    col_map = {}
    for i, h in enumerate(headers):
        if "需求名称" in h:
            col_map["name"] = i
        elif "标识" in h:
            col_map["id"] = i
        elif "章节号" in h:
            col_map["section"] = i
        elif "合格性方法" in h:
            col_map["method"] = i
        elif "级别" in h:
            col_map["level"] = i

    for row in simple["rows"]:
        entry = {}
        for key, idx in col_map.items():
            if idx < len(row):
                entry[key] = row[idx]
        if entry.get("name") or entry.get("id"):
            result.append(entry)

    return result


def extract_traceability_data(table: dict) -> list:
    """Extract traceability mappings."""
    result = []
    simple = simplify_table(table)
    headers = simple["headers"]

    for row in simple["rows"]:
        if len(row) < 2:
            continue
        entry = {
            "raw_headers": headers,
            "raw_row": row,
        }
        # Try to identify the pattern
        row_text = " ".join(row)
        if "REQ-" in row_text or "需求" in row_text:
            entry["type"] = "requirement_mapping"
        elif "ms" in row_text or "周期" in row_text:
            entry["type"] = "indicator_mapping"
        result.append(entry)

    return result


def parse_document(md_path: Path, doc_name: str) -> dict:
    """Parse all tables from a single SRS document."""
    tables = extract_tables_from_md(md_path)

    parsed_tables = []
    for table in tables:
        table_type = classify_table(table)
        simple = simplify_table(table)

        parsed = {
            "table_type": table_type,
            "section": table.get("section", ""),
            "line": table.get("line", 0),
            "headers": simple["headers"],
            "rows": simple["rows"],
            "num_rows": len(simple["rows"]),
        }

        # Extract type-specific data
        if table_type == "qualification":
            parsed["requirements"] = extract_qualification_data(table)
        elif table_type == "traceability":
            parsed["mappings"] = extract_traceability_data(table)

        parsed_tables.append(parsed)

    return {
        "doc_name": doc_name,
        "parse_date": datetime.now().isoformat(),
        "total_tables": len(parsed_tables),
        "tables": parsed_tables,
    }


def main():
    print("=" * 60)
    print("SRS Table Parser")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docs = [
        ("scheduler_srs.pdf", "scheduler_srs"),
        ("battery_srs.pdf", "battery_srs"),
        ("compiler_srs.pdf", "compiler_srs"),
    ]

    all_results = []

    for pdf_name, doc_name in docs:
        md_path = SRS_DIR / pdf_name / "auto" / f"{pdf_name}.md"

        if not md_path.exists():
            md_files = list((SRS_DIR / pdf_name).rglob("*.md"))
            if md_files:
                md_path = md_files[0]
            else:
                print(f"[{doc_name}] No markdown found, skipping")
                continue

        print(f"\n[{doc_name}] Parsing tables from: {md_path.name}")

        result = parse_document(md_path, doc_name)

        output_path = OUTPUT_DIR / f"{doc_name}_tables.json"
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        all_results.append(result)

        # Print summary
        for t in result["tables"]:
            req_count = len(t.get("requirements", []))
            map_count = len(t.get("mappings", []))
            extra = f" ({req_count} reqs)" if req_count else (f" ({map_count} maps)" if map_count else "")
            print(f"  [{t['table_type']:20s}] {t['num_rows']:3d} rows  section={t['section'][:30]}  {extra}")

    # Summary
    total_tables = sum(r["total_tables"] for r in all_results)
    print(f"\n{'=' * 60}")
    print(f"TABLE PARSING COMPLETE")
    print(f"  Documents: {len(all_results)}")
    print(f"  Total tables: {total_tables}")
    print(f"  Output: {OUTPUT_DIR}")

    # Cross-document analysis for scheduler
    print(f"\n{'=' * 60}")
    print("SCHEDULER SRS - TABLE ANALYSIS")
    scheduler = all_results[0]
    for t in scheduler["tables"]:
        print(f"\n  Table: {t['table_type']} (section: {t['section']})")
        print(f"  Headers: {t['headers']}")
        if t.get("requirements"):
            print(f"  Requirements:")
            for req in t["requirements"]:
                print(f"    {req}")
        elif t.get("mappings"):
            print(f"  Mappings:")
            for m in t["mappings"]:
                print(f"    {m['raw_row']}")
        elif t["rows"]:
            print(f"  First 3 rows:")
            for row in t["rows"][:3]:
                print(f"    {row}")


if __name__ == "__main__":
    main()
