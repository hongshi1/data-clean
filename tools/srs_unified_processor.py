#!/usr/bin/env python3
"""
Unified SRS Document Processor
将每份SRS文档的所有信息(章节/约束/表格/图片)整合为统一结构。
确保图片与文本一一对应，数据规整。
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLECTION = REPO_ROOT / "data" / "gjb_438c" / "srs_collection"
MINERU_SRS = REPO_ROOT / "data" / "gjb_438c" / "mineru_srs"
DEMO_DIR = REPO_ROOT / "data" / "gjb_438c" / "demo"
CONSTRAINTS_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_constraints"
TABLES_DIR = REPO_ROOT / "data" / "gjb_438c" / "extracted_tables"
IMAGE_MATCHES_DIR = REPO_ROOT / "data" / "gjb_438c" / "image_text_matches"
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "processed_documents"


def find_mineru_md(doc_name: str) -> Path:
    """查找文档的MinerU MD文件。"""
    # Try mineru_srs first
    for p in MINERU_SRS.rglob("*.md"):
        if doc_name in p.name or p.stem == doc_name:
            return p
    # Try collection
    for p in COLLECTION.rglob("auto/*.md"):
        if doc_name in p.name or p.stem == doc_name:
            return p
    # Try raw MD in collection
    for p in COLLECTION.rglob("*.md"):
        if "mineru_parsed" not in str(p) and doc_name in p.stem:
            return p
    return None


def extract_sections(md_content: str) -> list:
    """提取章节树，含每章的文本内容。"""
    lines = md_content.splitlines()
    sections = []
    current = None
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            if current:
                current["text"] = "\n".join(current["lines"]).strip()
                sections.append(current)
            
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            
            # Extract section number
            num_match = re.match(r"^(\d+(?:\.\d+)*)\s+", title)
            section_num = num_match.group(1) if num_match else None
            
            current = {
                "level": level,
                "number": section_num,
                "title": title,
                "line_start": i + 1,
                "lines": [],
            }
        elif current:
            current["lines"].append(line)
    
    if current:
        current["text"] = "\n".join(current["lines"]).strip()
        sections.append(current)
    
    return sections


def extract_constraints_from_section(section_text: str, section_title: str) -> list:
    """从章节文本中提取约束(正则方法，快速)。"""
    constraints = []
    
    # Numerical constraints: number + unit
    patterns = [
        (r"不超过\s*[±]?\s*(\d+\.?\d*)\s*(ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω|hours?|小时|分钟|min)", "≤"),
        (r"不低于\s*(\d+\.?\d*)\s*(ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω|hours?|小时|分钟|min)", "≥"),
        (r"至少\s*(\d+\.?\d*)\s*(ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω|hours?|小时|分钟|min)", "≥"),
        (r"不超过±(\d+\.?\d*)\s*(ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω)", "±"),
        (r"默认\s*(\d+\.?\d*)\s*(ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω)", "="),
        (r"=\s*(\d+\.?\d*)\s*(ms|秒|s|MHz|GHz|Hz|KB|MB|GB|TB|%|V|mV|W|mW|dB|ppm|°C|A|Ω)", "="),
        (r"(?:shall|must)\s+(?:be|not exceed|not exceed|less than|greater than|at least|at most)?\s*(?:≤|≥|<|>|=)?\s*(\d+\.?\d*)\s*(ms|seconds?|minutes?|hours?|Hz|kHz|MHz|GHz|bps|Kbps|Mbps|Gbps|%|MB|GB|TB|bytes?|KB|°C|°F|V|mV|W|mW|dB|dBm|ppm)", "shall"),
    ]
    
    for line in section_text.split("\n"):
        for pattern, operator in patterns:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                value = float(match.group(1))
                unit = match.group(2) if match.lastindex >= 2 else ""
                
                # Get the sentence containing this match
                sent_start = max(0, match.start() - 50)
                sent_end = min(len(line), match.end() + 50)
                sentence = line[sent_start:sent_end].strip()
                
                constraints.append({
                    "value": value,
                    "unit": unit,
                    "operator": operator,
                    "sentence": sentence[:200],
                    "section": section_title,
                })
    
    return constraints


def extract_tables_from_md(md_content: str) -> list:
    """提取HTML和Markdown表格。"""
    tables = []
    lines_all = md_content.splitlines()
    
    def find_table_section(match_start_char):
        """找到表格所在的章节。"""
        pos = 0
        current_section = ""
        for line in lines_all:
            next_pos = pos + len(line) + 1
            if next_pos > match_start_char:
                return current_section
            if line.lstrip().startswith("#"):
                current_section = line.lstrip("#").strip()
            pos = next_pos
        return current_section
    
    def classify_table(headers_list, rows_list):
        """分类表格类型(中英文兼容)。"""
        header_text = " ".join(str(h) for h in headers_list).lower().replace("**","").replace("__","")
        
        # modification (修改页)
        if ("序号" in header_text and "版本号" in header_text) or \
           ("revision" in header_text and "date" in header_text and "page" in header_text):
            return "modification"
        # reference (引用文档)
        if ("序号" in header_text and "名称" in header_text and "版本" in header_text) or \
           ("document" in header_text and "version" in header_text) or \
           ("编号" in header_text and "标题" in header_text):
            return "reference"
        # qualification (合格性规定)
        if ("需求" in header_text and ("标识" in header_text or "合格性" in header_text or "方法" in header_text)) or \
           ("requirement" in header_text and ("verification" in header_text or "method" in header_text or "id" in header_text)):
            return "qualification"
        # traceability (追踪表)
        if ("追踪" in header_text or "可行性" in header_text or "指标" in header_text or "追溯" in header_text) or \
           ("trace" in header_text or "requirement" in header_text and "source" in header_text):
            return "traceability"
        # interface (接口表)
        if ("接口" in header_text and ("信号" in header_text or "协议" in header_text)) or \
           ("interface" in header_text and ("signal" in header_text or "protocol" in header_text)):
            return "interface"
        # data dictionary
        if "数据" in header_text and ("类型" in header_text or "单位" in header_text) or \
           ("data" in header_text and "type" in header_text):
            return "data_dictionary"
        return "other"
    
    def is_table_empty(headers_list, rows_list):
        """检查表格是否为空模板。"""
        for row in rows_list:
            for cell in row:
                if cell and cell.strip() and not cell.strip().startswith("rowspan") and not cell.strip().startswith("colspan"):
                    return False
        return len(rows_list) > 0
    
    # HTML tables
    html_pattern = re.compile(r"<table>(.*?)</table>", re.DOTALL)
    for i, match in enumerate(html_pattern.finditer(md_content)):
        table_html = match.group(1)
        
        # Extract headers (only from first row)
        first_row_match = re.search(r"<tr>(.*?)</tr>", table_html, re.DOTALL)
        headers = []
        if first_row_match:
            headers = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", first_row_match.group(1), re.DOTALL)
            headers = [h.strip() for h in headers if h.strip()]
        
        # Extract all rows
        all_rows = re.findall(r"<tr>(.*?)</tr>", table_html, re.DOTALL)
        data_rows = []
        for row_html in all_rows[1:]:  # Skip header row
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL)
            data_rows.append([c.strip() for c in cells])
        
        table_type = classify_table(headers, data_rows)
        table_section = find_table_section(match.start())
        is_empty = is_table_empty(headers, data_rows)
        
        tables.append({
            "index": i,
            "type": table_type,
            "format": "html",
            "headers": headers[:10],
            "row_count": len(all_rows),
            "data_row_count": len(data_rows),
            "is_empty": is_empty,
            "section": table_section,
            "raw_html": table_html[:500],
        })
    
    # Markdown tables
    md_table_pattern = re.compile(r"^\|.*\|\n\|[-:| ]+\|.*\n(?:\|.*\|\n?)*", re.MULTILINE)
    for match in md_table_pattern.finditer(md_content):
        lines = match.group().strip().split("\n")
        if len(lines) >= 2:
            headers = [h.strip() for h in lines[0].split("|") if h.strip()]
            data_rows = []
            for line in lines[2:]:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if cells:
                    data_rows.append(cells)
            
            table_type = classify_table(headers, data_rows)
            table_section = find_table_section(match.start())
            
            tables.append({
                "index": len(tables),
                "type": table_type,
                "format": "markdown",
                "headers": headers,
                "row_count": len(lines) - 1,
                "data_row_count": len(data_rows),
                "is_empty": len(data_rows) == 0,
                "section": table_section,
                "raw_html": None,
            })
    
    return tables


def extract_images_from_md(md_content: str, md_path: Path) -> list:
    """提取图片引用及其上下文。"""
    lines = md_content.splitlines()
    images = []
    
    img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
    
    for i, line in enumerate(lines):
        match = img_pattern.search(line)
        if not match:
            continue
        
        alt_text = match.group(1).strip()
        img_rel_path = match.group(2).strip()
        
        # Resolve image path
        img_full_path = md_path.parent / img_rel_path
        
        # Caption (next non-empty line, must not be markdown heading or too long)
        caption = ""
        for j in range(i + 1, min(i + 5, len(lines))):
            next_line = lines[j].strip()
            if next_line and not next_line.startswith("![") and not next_line.startswith("#"):
                # Validate: caption should be <150 chars and look like a figure caption
                if len(next_line) <= 150 and (
                    re.match(r"^(Figure|Fig\.?|图|表|Table|Diagram)\s*\d", next_line) or
                    (len(next_line) <= 80 and not next_line.startswith(("•", "-", "*", "o ")))
                ):
                    caption = next_line
                    break
                elif len(next_line) <= 80 and not next_line.startswith(("•", "-", "*", "o ", "+ ")):
                    caption = next_line
                    break
        
        # Figure number
        fig_num = None
        for pattern in [r"Figure\s+(\d+)", r"Fig\.\s*(\d+)", r"图\s*(\d+)", r"^(\d+)\."]:
            m = re.search(pattern, caption)
            if m:
                fig_num = int(m.group(1))
                break
        
        # Context before (up to 5 lines, skip image references and headings)
        context_before = []
        for j in range(i - 1, max(i - 10, -1), -1):
            prev_line = lines[j].strip()
            if prev_line and not prev_line.startswith("![") and not prev_line.startswith("#"):
                context_before.insert(0, prev_line)
                if len(context_before) >= 3:
                    break
        
        # Context after (skip image references and headings)
        context_after = []
        for j in range(i + 1, min(i + 6, len(lines))):
            next_line = lines[j].strip()
            if next_line and not next_line.startswith("![") and not next_line.startswith("#"):
                context_after.append(next_line)
                if len(context_after) >= 2:
                    break
        
        # Image type
        img_type = "unknown"
        caption_lower = caption.lower()
        type_keywords = {
            "architecture_diagram": ["block diagram", "architecture", "架构", "框图"],
            "flowchart": ["flow", "流程", "sequence", "时序", "activity"],
            "state_diagram": ["state", "状态", "transition"],
            "interface_diagram": ["interface", "接口", "connection"],
            "data_diagram": ["data", "数据", "format", "格式"],
            "context_diagram": ["context", "上下文", "overview"],
        }
        for t, kws in type_keywords.items():
            if any(kw in caption_lower for kw in kws):
                img_type = t
                break
        if img_type == "unknown" and caption:
            img_type = "figure"
        
        # Find which section this image belongs to
        section = ""
        for j in range(i - 1, -1, -1):
            if lines[j].lstrip().startswith("#"):
                section = lines[j].lstrip("#").strip()
                break
        
        images.append({
            "image_index": len(images) + 1,
            "image_file": os.path.basename(img_rel_path),
            "image_path": str(img_full_path),
            "image_exists": img_full_path.exists(),
            "image_size_kb": round(img_full_path.stat().st_size / 1024) if img_full_path.exists() else 0,
            "alt_text": alt_text if alt_text else None,
            "caption": caption[:200] if caption else None,
            "figure_number": fig_num,
            "image_type": img_type,
            "section": section,
            "context_before": "\n".join(context_before)[:300] if context_before else None,
            "context_after": "\n".join(context_after)[:200] if context_after else None,
            "md_line": i + 1,
            "has_caption": bool(caption),
            "has_context": bool(context_before),
        })
    
    # Fallback: if no images found via ![] references, scan images/ directory
    if not images:
        img_dir = md_path.parent / "images"
        if img_dir.exists():
            img_files = sorted(img_dir.glob("*.jpg"), key=lambda f: f.stat().st_mtime)
            for idx, img_file in enumerate(img_files):
                # Skip tiny images (< 5KB, likely icons/decorations)
                size_kb = round(img_file.stat().st_size / 1024)
                if size_kb < 5:
                    continue
                
                images.append({
                    "image_index": idx + 1,
                    "image_file": img_file.name,
                    "image_path": str(img_file),
                    "image_exists": True,
                    "image_size_kb": size_kb,
                    "alt_text": None,
                    "caption": None,
                    "figure_number": None,
                    "image_type": "orphaned_figure",
                    "section": None,
                    "context_before": None,
                    "context_after": None,
                    "md_line": None,
                    "has_caption": False,
                    "has_context": False,
                })
    
    return images


def process_document(md_path: Path, doc_name: str, source: str) -> dict:
    """处理单个文档，整合所有信息。"""
    md_content = md_path.read_text(encoding="utf-8", errors="replace")
    
    # Extract sections
    sections = extract_sections(md_content)
    
    # Extract constraints from each section
    all_constraints = []
    for sec in sections:
        sec_constraints = extract_constraints_from_section(sec.get("text", ""), sec["title"])
        for c in sec_constraints:
            c["section_number"] = sec.get("number")
            c["section_title"] = sec["title"]
            c["line_start"] = sec["line_start"]
        all_constraints.extend(sec_constraints)
    
    # Extract tables
    tables = extract_tables_from_md(md_content)
    
    # Extract images with context
    images = extract_images_from_md(md_content, md_path)
    
    # Load LLM-extracted constraints if available (exact match only)
    llm_constraints = None
    for cf in CONSTRAINTS_DIR.glob("*constraints.json"):
        try:
            cdata = json.loads(cf.read_text("utf-8"))
            cname = cdata.get("doc_name") or cdata.get("doc", "")
            if cname and cname == doc_name:
                llm_constraints = cdata
                break
        except:
            pass
    
    # Determine if GJB format (must have Chinese keywords to avoid English false positives)
    has_qualification = bool(re.search(r"合格性规定", md_content))
    has_traceability = bool(re.search(r"需求可追踪性", md_content))
    has_csci = bool(re.search(r"CSCI|软件配置项", md_content))
    has_chinese_scope = bool(re.search(r"范围|引用文档|引用文件|需求", md_content))
    is_gjb = has_chinese_scope and has_qualification and (has_traceability or has_csci)
    
    # GJB version
    gjb_version = None
    if "438C" in md_content[:5000]:
        gjb_version = "438C"
    elif "438B" in md_content[:5000]:
        gjb_version = "438B"
    
    # Language
    cjk_count = sum(1 for c in md_content[:5000] if '\u4e00' <= c <= '\u9fff')
    language = "zh" if cjk_count > 50 else "en"
    
    # System type
    text_lower = md_content[:3000].lower()
    system_type = "unknown"
    for stype, keywords in [
        ("embedded", ["嵌入式", "embedded", "mcu", "rtos", "定时器", "firmware"]),
        ("web", ["web", "浏览器", "html", "前端", "后端", "api"]),
        ("aerospace", ["nasa", "航空", "航天", "飞行", "orbit", "spacecraft"]),
        ("education", ["教学", "课程", "学生", "成绩", "考试"]),
        ("defense", ["雷达", "导弹", "武器", "军用", "radar"]),
        ("communication", ["通信", "网络", "协议", "protocol"]),
        ("compiler", ["编译器", "compiler", "词法", "语法分析"]),
    ]:
        if any(kw in text_lower for kw in keywords):
            system_type = stype
            break
    
    # Build unified document
    return {
        "doc_name": doc_name,
        "source": source,
        "md_path": str(md_path.relative_to(REPO_ROOT)) if md_path.is_relative_to(REPO_ROOT) else str(md_path),
        "md_lines": len(md_content.splitlines()),
        "md_chars": len(md_content),
        "language": language,
        "is_gjb_format": is_gjb,
        "gjb_version": gjb_version,
        "system_type": system_type,
        "title": sections[0]["title"] if sections else doc_name,
        
        # Sections
        "section_count": len(sections),
        "sections": [
            {
                "number": s["number"],
                "title": s["title"],
                "level": s["level"],
                "line_start": s["line_start"],
                "text_length": len(s.get("text", "")),
                "text_preview": s.get("text", "")[:200],
            }
            for s in sections
        ],
        
        # Constraints (regex-extracted)
        "constraint_count": len(all_constraints),
        "constraints": all_constraints[:100],  # Limit to 100
        
        # LLM constraints (if available)
        "llm_constraint_count": len(llm_constraints.get("constraints", [])) if llm_constraints else 0,
            "llm_constraints": llm_constraints.get("constraints", []) if llm_constraints else None,
        
        # Tables
        "table_count": len(tables),
        "tables": tables,
        
        # Images (with text matching)
        "image_count": len(images),
        "images": images,
        
        # Image-text pairs (matched)
        "image_text_pairs": [
            {
                "image_file": img["image_file"],
                "image_path": img["image_path"],
                "image_exists": img["image_exists"],
                "image_size_kb": img["image_size_kb"],
                "image_type": img["image_type"],
                "figure_number": img["figure_number"],
                "caption": img["caption"],
                "section": img["section"],
                "context_before": img["context_before"],
                "context_after": img["context_after"],
                "has_caption": img["has_caption"],
                "has_context": img["has_context"],
            }
            for img in images
        ],
    }


def main():
    print("=" * 60)
    print("Unified SRS Document Processor")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect all MD files to process
    docs_to_process = []
    
    # 1. Original 3 GJB SRS (MinerU parsed)
    for md in MINERU_SRS.rglob("auto/*.md"):
        doc_name = md.stem.replace(".pdf", "")
        docs_to_process.append((md, doc_name, "gjb_demo"))
    
    # 2. Collection MDs (both MinerU and raw)
    seen_names = set()
    for md in COLLECTION.rglob("*.md"):
        if "mineru_parsed" in str(md):
            # MinerU parsed MD
            doc_name = md.stem.replace(".pdf", "")
            if doc_name not in seen_names:
                docs_to_process.append((md, doc_name, "collection_mineru"))
                seen_names.add(doc_name)
        elif md.parent.parent.name in ["buaa", "radar", "asyncTask", "more_gjb", "gjb438b", "nasa", "ieee830", "pure_extended", "pure_original", "reqlist_reqnet_reqsim"]:
            # Raw MD (not MinerU)
            doc_name = md.stem
            if doc_name not in seen_names and not md.name.startswith("README") and not md.name.startswith("CATALOG"):
                docs_to_process.append((md, doc_name, "collection_raw"))
                seen_names.add(doc_name)
    
    print(f"\nFound {len(docs_to_process)} documents to process\n")
    
    all_docs = []
    stats = {
        "total_docs": 0,
        "gjb_docs": 0,
        "general_docs": 0,
        "total_sections": 0,
        "total_constraints": 0,
        "total_llm_constraints": 0,
        "total_tables": 0,
        "total_images": 0,
        "total_image_text_pairs": 0,
        "images_with_caption": 0,
        "images_with_context": 0,
        "by_source": defaultdict(int),
        "by_system_type": defaultdict(int),
        "by_language": defaultdict(int),
    }
    
    for i, (md_path, doc_name, source) in enumerate(sorted(docs_to_process)):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(docs_to_process)}")
        
        try:
            doc = process_document(md_path, doc_name, source)
            all_docs.append(doc)
            
            # Update stats
            stats["total_docs"] += 1
            if doc["is_gjb_format"]:
                stats["gjb_docs"] += 1
            else:
                stats["general_docs"] += 1
            stats["total_sections"] += doc["section_count"]
            stats["total_constraints"] += doc["constraint_count"]
            stats["total_llm_constraints"] += doc["llm_constraint_count"]
            stats["total_tables"] += doc["table_count"]
            stats["total_images"] += doc["image_count"]
            stats["total_image_text_pairs"] += len(doc["image_text_pairs"])
            stats["images_with_caption"] += sum(1 for img in doc["images"] if img["has_caption"])
            stats["images_with_context"] += sum(1 for img in doc["images"] if img["has_context"])
            stats["by_source"][source] += 1
            stats["by_system_type"][doc["system_type"]] += 1
            stats["by_language"][doc["language"]] += 1
            
            # Save individual document
            safe_name = doc_name.replace("/", "_")[:60]
            (OUTPUT_DIR / f"{safe_name}.json").write_text(
                json.dumps(doc, indent=2, ensure_ascii=False), "utf-8"
            )
            
        except Exception as e:
            print(f"  ERROR processing {doc_name}: {e}")
    
    # Convert defaultdicts to dicts
    stats["by_source"] = dict(stats["by_source"])
    stats["by_system_type"] = dict(stats["by_system_type"])
    stats["by_language"] = dict(stats["by_language"])
    stats["analysis_date"] = datetime.now().isoformat()
    
    # Save summary
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), "utf-8"
    )
    
    # Save index
    index = [
        {
            "doc_name": d["doc_name"],
            "source": d["source"],
            "is_gjb": d["is_gjb_format"],
            "language": d["language"],
            "system_type": d["system_type"],
            "sections": d["section_count"],
            "constraints": d["constraint_count"],
            "llm_constraints": d["llm_constraint_count"],
            "tables": d["table_count"],
            "images": d["image_count"],
            "image_text_pairs": len(d["image_text_pairs"]),
        }
        for d in all_docs
    ]
    (OUTPUT_DIR / "_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), "utf-8"
    )
    
    print(f"\n{'=' * 60}")
    print("PROCESSING COMPLETE")
    print(f"  Total documents: {stats['total_docs']}")
    print(f"  GJB format: {stats['gjb_docs']}")
    print(f"  General SRS: {stats['general_docs']}")
    print(f"  Total sections: {stats['total_sections']}")
    print(f"  Total constraints (regex): {stats['total_constraints']}")
    print(f"  Total constraints (LLM): {stats['total_llm_constraints']}")
    print(f"  Total tables: {stats['total_tables']}")
    print(f"  Total images: {stats['total_images']}")
    print(f"  Image-text pairs: {stats['total_image_text_pairs']}")
    print(f"  Images with caption: {stats['images_with_caption']} ({stats['images_with_caption']/max(stats['total_images'],1):.0%})")
    print(f"  Images with context: {stats['images_with_context']} ({stats['images_with_context']/max(stats['total_images'],1):.0%})")
    print(f"  By source: {stats['by_source']}")
    print(f"  By system type: {stats['by_system_type']}")
    print(f"  Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
