#!/usr/bin/env python3
"""
GJB SRS .doc → HTML → 结构化JSON 解析器
从textutil转换的HTML中提取章节文本、表格、结构信息。
"""
import os, json, re, sys
from pathlib import Path
from html.parser import HTMLParser
from collections import defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "gjb_438c" / "real_gjb_srs"
HTML_DIR = DATA_DIR / "html"
OUT_DIR = DATA_DIR / "parsed"
OUT_DIR.mkdir(exist_ok=True)


class GJBHtmlParser(HTMLParser):
    """解析GJB SRS HTML，提取章节文本和表格。"""

    def __init__(self):
        super().__init__()
        self.sections = []
        self.tables = []
        self._tag_stack = []
        self._current_text = []
        self._current_table = []
        self._current_row = []
        self._current_cell = []
        self._in_table = False
        self._in_cell = False
        self._section_id = 0
        self._page = 0
        self._heading_level = 0
        self._current_heading = ""

    def handle_starttag(self, tag, attrs):
        self._tag_stack.append(tag)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._heading_level = int(tag[1])
            self._current_text = []
        elif tag == "table":
            self._in_table = True
            self._current_table = []
        elif tag == "tr" and self._in_table:
            self._current_row = []
        elif tag in ("td", "th") and self._in_table:
            self._in_cell = True
            self._current_cell = []
        elif tag == "p":
            self._current_text = []

    def handle_endtag(self, tag):
        if self._tag_stack and self._tag_stack[-1] == tag:
            self._tag_stack.pop()

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            text = "".join(self._current_text).strip()
            if text:
                self._current_heading = text
                self.sections.append({
                    "id": self._section_id,
                    "type": "heading",
                    "level": self._heading_level,
                    "text": text,
                    "heading": text,
                })
                self._section_id += 1
            self._heading_level = 0

        elif tag == "p" and not self._in_table:
            text = "".join(self._current_text).strip()
            if text and len(text) > 2:
                self.sections.append({
                    "id": self._section_id,
                    "type": "text",
                    "text": text,
                    "heading": self._current_heading,
                })
                self._section_id += 1
            self._current_text = []

        elif tag in ("td", "th") and self._in_table:
            cell_text = "".join(self._current_cell).strip()
            self._current_row.append(cell_text)
            self._in_cell = False

        elif tag == "tr" and self._in_table:
            if self._current_row:
                self._current_table.append(self._current_row)

        elif tag == "table":
            if self._current_table:
                # Determine table type from content
                first_row = self._current_table[0] if self._current_table else []
                table_type = "unknown"
                all_text = " ".join([" ".join(r) for r in self._current_table])
                if "追踪" in all_text or "正向" in all_text:
                    table_type = "traceability"
                elif "合格性" in all_text or "验证" in all_text:
                    table_type = "qualification"
                elif "接口" in all_text:
                    table_type = "interface"
                elif "更改" in all_text:
                    table_type = "change_record"

                self.tables.append({
                    "id": len(self.tables),
                    "type": table_type,
                    "rows": self._current_table,
                    "row_count": len(self._current_table),
                    "col_count": max(len(r) for r in self._current_table) if self._current_table else 0,
                    "heading": self._current_heading,
                })
            self._in_table = False
            self._current_table = []

    def handle_data(self, data):
        if self._in_cell:
            self._current_cell.append(data)
        elif self._heading_level > 0 or (self._tag_stack and self._tag_stack[-1] == "p"):
            self._current_text.append(data)
        elif not self._in_table:
            # Capture text in other tags too
            self._current_text.append(data)


def parse_html_file(html_path: str) -> dict:
    """解析单个HTML文件。"""
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    parser = GJBHtmlParser()
    parser.feed(html_content)

    # Filter meaningful sections
    meaningful_sections = [s for s in parser.sections if len(s.get("text", "")) > 5]

    # Extract constraint-like sections
    constraint_sections = [s for s in meaningful_sections
                          if any(kw in s.get("text", "") for kw in
                                ["≤", "≥", "不超过", "应", "必须", "ms", "范围", "约束",
                                 "性能", "时间", "周期", "参数", "接口", "输入", "输出"])]

    return {
        "sections": meaningful_sections,
        "tables": parser.tables,
        "section_count": len(meaningful_sections),
        "table_count": len(parser.tables),
        "constraint_section_count": len(constraint_sections),
        "constraint_sections": constraint_sections,
    }


def main():
    print("=" * 60)
    print("GJB SRS HTML解析器")
    print("=" * 60)

    html_files = sorted(HTML_DIR.glob("*.html"))
    print(f"找到 {len(html_files)} 个HTML文件\n")

    all_results = {}

    for html_path in html_files:
        doc_name = html_path.stem
        print(f"📄 {doc_name[:40]}...")

        try:
            result = parse_html_file(str(html_path))
            print(f"  章节: {result['section_count']}, 表格: {result['table_count']}, "
                  f"约束相关: {result['constraint_section_count']}")

            # Show table types
            for t in result["tables"]:
                print(f"    表{t['id']}: {t['type']} ({t['row_count']}行×{t['col_count']}列)")

            # Save
            out_path = OUT_DIR / f"{doc_name}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            all_results[doc_name] = {
                "sections": result["section_count"],
                "tables": result["table_count"],
                "constraint_sections": result["constraint_section_count"],
                "table_types": [t["type"] for t in result["tables"]],
            }

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Summary
    print(f"\n{'='*60}")
    print("📊 汇总")
    print(f"{'='*60}")
    print(f"{'文档':<45} {'章节':>6} {'表格':>6} {'约束':>6}")
    print("-" * 66)
    total_s = total_t = total_c = 0
    for name, r in sorted(all_results.items()):
        print(f"{name[:45]:<45} {r['sections']:>6} {r['tables']:>6} {r['constraint_sections']:>6}")
        total_s += r["sections"]
        total_t += r["tables"]
        total_c += r["constraint_sections"]
    print("-" * 66)
    print(f"{'合计':<45} {total_s:>6} {total_t:>6} {total_c:>6}")

    # Save summary
    with open(OUT_DIR / "_summary.json", "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 解析结果: {OUT_DIR}/")
    print("✅ Done!")


if __name__ == "__main__":
    main()
