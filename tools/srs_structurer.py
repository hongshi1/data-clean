#!/usr/bin/env python3
"""
SRS Document Structurer
Phase 3 of Data Governance Pipeline.

Parses MinerU output (Markdown + JSON) for each SRS document and extracts
structured data in a unified format:
  - Section tree (from Markdown headers)
  - Tables (from HTML tables in Markdown)
  - Figures (from image references)
  - Constraints (sentences with "shall/must/应 + value")

Output: data/srs_requirements/structured/<doc_id>.json
"""

import json
import re
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser

REPO_ROOT = Path(__file__).resolve().parent.parent
MINERU_PARSED = REPO_ROOT / "data" / "srs_requirements" / "mineru_parsed"
OUTPUT_DIR = REPO_ROOT / "data" / "srs_requirements" / "structured"


class TableHTMLParser(HTMLParser):
    """Parse HTML table into structured rows."""
    
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.in_table = False
        self.in_row = False
        self.in_cell = False
    
    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.current_table = {"headers": [], "rows": []}
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.current_row = []
            self.in_row = True
        elif tag in ("td", "th") and self.in_row:
            self.current_cell = ""
            self.in_cell = True
    
    def handle_endtag(self, tag):
        if tag == "table" and self.current_table:
            self.tables.append(self.current_table)
            self.current_table = None
            self.in_table = False
        elif tag == "tr" and self.current_row is not None:
            if self.current_table:
                if not self.current_table["headers"]:
                    self.current_table["headers"] = self.current_row
                else:
                    self.current_table["rows"].append(self.current_row)
            self.current_row = None
            self.in_row = False
        elif tag in ("td", "th") and self.current_cell is not None:
            if self.current_row is not None:
                self.current_row.append(self.current_cell.strip())
            self.current_cell = None
            self.in_cell = False
    
    def handle_data(self, data):
        if self.in_cell and self.current_cell is not None:
            self.current_cell += data


def parse_tables(md_content: str) -> list:
    """Extract HTML tables from markdown content."""
    tables = []
    pattern = re.compile(r"<table>(.*?)</table>", re.DOTALL)
    for match in pattern.finditer(md_content):
        parser = TableHTMLParser()
        parser.feed(f"<table>{match.group(1)}</table>")
        for t in parser.tables:
            if t["headers"] or t["rows"]:
                tables.append(t)
    return tables


def parse_sections(md_content: str) -> list:
    """Extract section tree from markdown headers."""
    sections = []
    lines = md_content.splitlines()
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            if not title:
                continue
            
            section_num_match = re.match(r"^(\d+(?:\.\d+)*)\s+", title)
            section_num = section_num_match.group(1) if section_num_match else None
            
            content_start = i + 1
            content_end = len(lines)
            for j in range(i + 1, len(lines)):
                if lines[j].lstrip().startswith("#"):
                    content_end = j
                    break
            
            content_lines = lines[content_start:content_end]
            content = "\n".join(content_lines).strip()
            
            sections.append({
                "level": level,
                "number": section_num,
                "title": title,
                "content": content[:500],
                "content_length": len(content),
                "line_start": i + 1,
                "line_end": content_end,
            })
    
    return sections


def parse_figures(md_content: str) -> list:
    """Extract figure references from markdown."""
    figures = []
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    for match in pattern.finditer(md_content):
        caption = match.group(1).strip()
        image_path = match.group(2).strip()
        figures.append({
            "caption": caption,
            "image_path": image_path,
        })
    return figures


def parse_constraints(md_content: str) -> list:
    """Extract constraint sentences (shall/must/应 + value)."""
    constraints = []
    
    patterns = [
        r"(?:shall|must|should|will)\s+(?:be\s+)?(?:less\s+than|greater\s+than|at\s+least|at\s+most|exactly|no\s+more\s+than|no\s+less\s+than)?\s*(?:≤|≥|<|>|=|≤|≥)?\s*(\d+(?:\.\d+)?)\s*(ms|seconds?|minutes?|hours?|Hz|kHz|MHz|GHz|bps|Kbps|Mbps|Gbps|%|MB|GB|TB|bytes?|KB|°C|°F|V|mV|W|mW|dB|dBm|ppm)?",
        r"(?:应|必须|不得|不超过|不低于|至少|最多|最少)\s*(?:≤|≥|<|>|=)?\s*(\d+(?:\.\d+)?)\s*(ms|秒|分|时|Hz|kHz|MHz|GHz|%|MB|GB|TB|字节|KB|°C|V|mV|W|mW|dB|ppm)?",
        r"(?:availability|可用性|可靠性|MTBF)\s*(?:of|为|是|≥|≤|>|<|=)?\s*(\d+(?:\.\d+)?)\s*(%|hours?|小时)?",
    ]
    
    lines = md_content.splitlines()
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("|") or line.startswith("!"):
            continue
        
        for pattern in patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                value = match.group(1)
                unit = match.group(2) if match.lastindex >= 2 else ""
                
                operator = "unknown"
                line_lower = line.lower()
                if "≤" in line or "less than" in line_lower or "不超过" in line or "最多" in line:
                    operator = "≤"
                elif "≥" in line or "greater than" in line_lower or "不低于" in line or "至少" in line:
                    operator = "≥"
                elif "=" in line or "exactly" in line_lower or "为" in line or "是" in line:
                    operator = "="
                elif "<" in line:
                    operator = "<"
                elif ">" in line:
                    operator = ">"
                
                constraints.append({
                    "line": line_num,
                    "text": line[:200],
                    "value": float(value),
                    "unit": unit or "",
                    "operator": operator,
                    "pattern_matched": match.group(0)[:50],
                })
    
    return constraints


def structure_document(doc_dir: Path) -> dict:
    """Parse a single SRS document from MinerU output."""
    
    doc_name = doc_dir.name
    if doc_name.endswith(".pdf"):
        doc_name = doc_name[:-4]
    
    md_files = list(doc_dir.rglob("*.md"))
    json_files = list(doc_dir.rglob("*_middle.json"))
    
    if not md_files:
        return None
    
    md_path = md_files[0]
    md_content = md_path.read_text(encoding="utf-8", errors="replace")
    
    sections = parse_sections(md_content)
    tables = parse_tables(md_content)
    figures = parse_figures(md_content)
    constraints = parse_constraints(md_content)
    
    img_dir = doc_dir / "auto" / "images"
    num_images = len(list(img_dir.glob("*.jpg"))) + len(list(img_dir.glob("*.png"))) if img_dir.exists() else 0
    
    return {
        "doc_id": doc_name,
        "filename": doc_dir.name,
        "md_file": str(md_path),
        "json_file": str(json_files[0]) if json_files else None,
        "stats": {
            "md_lines": md_content.count("\n"),
            "num_sections": len(sections),
            "num_tables": len(tables),
            "num_figures": len(figures),
            "num_constraints": len(constraints),
            "num_images": num_images,
        },
        "sections": sections,
        "tables": tables,
        "figures": figures,
        "constraints": constraints,
    }


def main():
    print("=" * 60)
    print("SRS Document Structurer")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if not MINERU_PARSED.exists():
        print(f"ERROR: MinerU parsed directory not found: {MINERU_PARSED}")
        return 1
    
    doc_dirs = sorted([d for d in MINERU_PARSED.iterdir() if d.is_dir() and not d.name.startswith("_")])
    print(f"Found {len(doc_dirs)} documents to structure\n")
    
    all_results = []
    total_sections = 0
    total_tables = 0
    total_figures = 0
    total_constraints = 0
    
    for i, doc_dir in enumerate(doc_dirs, 1):
        doc_name = doc_dir.name
        print(f"[{i}/{len(doc_dirs)}] {doc_name}...", end=" ")
        
        result = structure_document(doc_dir)
        if result is None:
            print("SKIP (no markdown)")
            continue
        
        output_path = OUTPUT_DIR / f"{result['doc_id']}.json"
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        
        s = result["stats"]
        total_sections += s["num_sections"]
        total_tables += s["num_tables"]
        total_figures += s["num_figures"]
        total_constraints += s["num_constraints"]
        
        print(f"OK ({s['num_sections']}sec {s['num_tables']}tbl {s['num_figures']}fig {s['num_constraints']}con)")
        all_results.append(result)
    
    # Summary
    summary = {
        "struct_date": datetime.now().isoformat(),
        "total_docs": len(all_results),
        "total_sections": total_sections,
        "total_tables": total_tables,
        "total_figures": total_figures,
        "total_constraints": total_constraints,
        "docs": [{"doc_id": r["doc_id"], "stats": r["stats"]} for r in all_results],
    }
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    
    print(f"\n{'=' * 60}")
    print(f"STRUCTURING COMPLETE")
    print(f"  Documents: {len(all_results)}")
    print(f"  Total sections: {total_sections}")
    print(f"  Total tables: {total_tables}")
    print(f"  Total figures: {total_figures}")
    print(f"  Total constraints: {total_constraints}")
    print(f"  Output: {OUTPUT_DIR}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
