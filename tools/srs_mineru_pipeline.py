#!/usr/bin/env python3
"""
SRS文档标准解析 Pipeline (MinerU原生 + textutil→HTML)
======================================================
用macOS原生textutil做.doc→.html(保留表格)→结构化解析
然后调用MinerU office API做深度解析(章节/表格/图片)

Pipeline (参考DataFlow Core Operator模式):
  Step 1: .doc → .html (textutil, 保留表格结构)
  Step 2: .html → 结构化JSON (章节树 + 表格 + 文本)
  Step 3: 结构化JSON → MinerU content_list格式
  Step 4: MinerU深度解析 (可选, 传入docx)

用法: python3 tools/srs_mineru_pipeline.py
"""
import re
import json
import subprocess
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from dataclasses import dataclass, field

BASE = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE / "data/软件需归样例数据集"
OUTPUT_DIR = BASE / "data/gjb_438c/mineru_parsed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SRSHTMLParser(HTMLParser):
    """解析SRS的HTML，提取章节标题、段落、表格"""
    
    def __init__(self):
        super().__init__()
        self.blocks = []  # 有序的内容块列表
        self.current_text = []
        self.in_table = False
        self.current_table = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag == 'table':
            # 先保存之前的文本
            self._flush_text()
            self.in_table = True
            self.current_table = []
        elif tag == 'tr' and self.in_table:
            self.current_row = []
        elif tag in ('td', 'th') and self.in_table:
            self.in_cell = True
            self.current_cell = []
    
    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
            if self.current_table:
                self.blocks.append({"type": "table", "rows": self.current_table})
        elif tag == 'tr' and self.in_table:
            if self.current_row:
                self.current_table.append(self.current_row)
        elif tag in ('td', 'th') and self.in_cell:
            self.in_cell = False
            self.current_row.append(''.join(self.current_cell).strip())
        elif tag in ('p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self._flush_text()
    
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        if self.in_cell:
            self.current_cell.append(data)
        elif not self.in_table:
            self.current_text.append(data)
    
    def _flush_text(self):
        text = ' '.join(self.current_text).strip()
        if text:
            self.blocks.append({"type": "text", "content": text})
        self.current_text = []
    
    def get_result(self):
        self._flush_text()
        return self.blocks


# 章节标题正则
SECTION_RE = re.compile(r'^(\d+(?:\.\w+)*)\s+(.+)')
TABLE_SEQ_RE = re.compile(r'表\s*SEQ\s*表\s*\\\*\s*ARABIC\s*(\d+)\s*(.*)')
REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')

# 数值约束正则
CONSTRAINT_LE_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)'
    r'\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?'
)
CONSTRAINT_GE_RE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|≥|>=)'
    r'\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?'
)
VERSION_RE = re.compile(
    r'(达梦|Oracle|MySQL|Linux|内核|GCC|CentOS|Ubuntu|Windows|Qt|银河麒麟|WPS|wps)'
    r'[^。]*?(V?\d+\.?\d*(?:\.\d+)?)'
)


def classify_table(headers: list) -> str:
    """分类表格类型"""
    h = ' '.join(headers).lower()
    if any(kw in h for kw in ['序号', '版本号', '标记', '处数']):
        return 'modification'
    elif any(kw in h for kw in ['需求名称', '需求标识', '合格性方法', '合格性', '本文档章节号']):
        return 'qualification'
    elif any(kw in h for kw in ['追踪', '跟踪', '任务书', '本文档章节', '跟踪说明']):
        return 'traceability'
    elif any(kw in h for kw in ['接口', '信号']):
        return 'interface'
    elif any(kw in h for kw in ['文档编号', '标题', '修订']):
        return 'reference'
    elif any(kw in h for kw in ['功能名称', '标识', '子功能']):
        return 'capability'
    return 'other'


def classify_role(param: str, section: str) -> str:
    """semantic_role分类"""
    threshold_kw = ['时间', '间隔', '延迟', '误差', '精度', '响应', '定时', '偏差', '周期']
    config_kw = ['版本', '型号', '主频', '内存', '硬盘', '存储', '分辨率', '显存']
    capacity_kw = ['最多', '支持', '容量', '数量', '上限', '最大', '并发']
    for kw in threshold_kw:
        if kw in param: return "threshold"
    for kw in config_kw:
        if kw in param: return "config"
    for kw in capacity_kw:
        if kw in param: return "capacity"
    if section.startswith('3.10'): return "config"
    if section.startswith('3.11'): return "threshold"
    return "description"


def extract_constraints_from_text(text: str, section: str) -> list:
    """从文本中提取数值约束(从段落和表格cells)"""
    constraints = []
    for m in CONSTRAINT_LE_RE.finditer(text):
        value = float(m.group(1))
        unit = m.group(2) or ""
        before = text[max(0, m.start()-15):m.start()]
        param_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)
        param = param_m.group(1) if param_m else before[-8:].strip()
        constraints.append({
            "param": param, "operator": "≤", "value": value, "unit": unit,
            "role": classify_role(param, section),
            "original": text[max(0,m.start()-20):m.end()+20],
            "section": section,
        })
    for m in CONSTRAINT_GE_RE.finditer(text):
        value = float(m.group(1))
        unit = m.group(2) or ""
        before = text[max(0, m.start()-15):m.start()]
        param_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', before)
        param = param_m.group(1) if param_m else before[-8:].strip()
        constraints.append({
            "param": param, "operator": "≥", "value": value, "unit": unit,
            "role": classify_role(param, section),
            "original": text[max(0,m.start()-20):m.end()+20],
            "section": section,
        })
    return constraints


def extract_versions_from_text(text: str, section: str) -> list:
    """从文本中提取版本号"""
    versions = []
    for m in VERSION_RE.finditer(text):
        versions.append({
            "software": m.group(1),
            "version": m.group(2),
            "section": section,
            "original": text[max(0,m.start()-10):m.end()+10],
        })
    return versions


def extract_toc_mapping(html_text: str) -> dict:
    """
    从HTML的目录(TOC)中提取 标题文字→章节编号 映射
    先去除HTML标签，再从纯文本中提取TOC
    支持中文和英文(如CSCI)开头的标题
    """
    mapping = {}
    clean = re.sub(r'<[^>]+>', ' ', html_text)
    clean = re.sub(r'\s+', ' ', clean)
    
    # 提取TOC: "数字 标题 PAGEREF" — 标题可以是中文或英文开头，支持顿号等特殊字符
    for m in re.finditer(r'(\d+(?:\.\d+)*)\s+([\u4e00-\u9fa5A-Za-z][\u4e00-\u9fa5A-Za-z0-9（）/、，。\.]{1,30})\s+(?:PAGEREF|HYPERLINK)', clean):
        number = m.group(1)
        title = m.group(2).strip()
        if title and len(title) >= 2:
            mapping[title] = number
    
    # 补充: 从子章节推断父章节(如3.4.1存在→3.4存在)
    all_numbers = set(mapping.values())
    for num in list(all_numbers):
        parts = num.split('.')
        for i in range(1, len(parts)):
            parent = '.'.join(parts[:i])
            if parent not in mapping:
                # 不自动添加父章节(需要标题),只记录编号存在
                pass
    
    return mapping


def parse_doc_to_structured(doc_path: Path) -> dict:
    """
    完整解析流程: .doc → .html → 结构化JSON
    用TOC映射恢复章节编号(Word自动编号在HTML中丢失)
    """
    doc_name = doc_path.stem
    
    # Step 1: .doc → .html (textutil, 保留表格)
    html_path = OUTPUT_DIR / f"{doc_name}.html"
    subprocess.run(
        ['textutil', '-convert', 'html', '-output', str(html_path), str(doc_path)],
        capture_output=True, timeout=30
    )
    html_text = html_path.read_text(encoding='utf-8', errors='replace')
    
    # Step 2: 从TOC提取标题→编号映射
    toc_map = extract_toc_mapping(html_text)
    
    # Step 3: 解析HTML
    parser = SRSHTMLParser()
    parser.feed(html_text)
    blocks = parser.get_result()
    
    # Step 4: 构建章节树 + 提取结构化信息
    sections = {}
    current_section = ""
    all_constraints = []
    all_versions = []
    all_req_ids = set()
    table_count = 0
    seen_titles = set()  # 避免目录+正文重复
    
    for block in blocks:
        if block["type"] == "text":
            text = block["content"]
            
            # 跳过目录行
            if 'PAGEREF' in text or 'HYPERLINK' in text or 'TOC' in text:
                continue
            
            # 策略1: 直接匹配章节编号(有些文档保留了编号)
            m = SECTION_RE.match(text)
            if m:
                number = m.group(1)
                title = m.group(2).strip()
                if number not in seen_titles:
                    seen_titles.add(number)
                    current_section = number
                    if number not in sections:
                        sections[number] = {"title": title, "text": "", "tables": [],
                                           "constraints": [], "versions": []}
                        req_m = REQ_ID_RE.search(title)
                        if req_m:
                            sections[number]["req_id"] = req_m.group(0)
                            all_req_ids.add(req_m.group(0))
                    continue
            
            # 策略2: 用TOC映射匹配标题(Word自动编号丢失时)
            if text in toc_map and text not in seen_titles:
                number = toc_map[text]
                seen_titles.add(text)
                current_section = number
                if number not in sections:
                    sections[number] = {"title": text, "text": "", "tables": [],
                                       "constraints": [], "versions": []}
                    req_m = REQ_ID_RE.search(text)
                    if req_m:
                        sections[number]["req_id"] = req_m.group(0)
                        all_req_ids.add(req_m.group(0))
                continue
            
            # 策略3: 模糊匹配TOC(标题可能含额外文字)
            matched = False
            for toc_title, toc_num in toc_map.items():
                if len(toc_title) >= 4 and toc_title in text and toc_title not in seen_titles:
                    seen_titles.add(toc_title)
                    current_section = toc_num
                    if toc_num not in sections:
                        sections[toc_num] = {"title": toc_title, "text": "", "tables": [],
                                             "constraints": [], "versions": []}
                    matched = True
                    break
            if matched:
                continue
            
            # 添加到当前章节
            if current_section in sections:
                sections[current_section]["text"] += text + "\n"
            
            # 提取约束和版本号
            constraints = extract_constraints_from_text(text, current_section)
            versions = extract_versions_from_text(text, current_section)
            if constraints and current_section in sections:
                sections[current_section]["constraints"].extend(constraints)
                all_constraints.extend(constraints)
            if versions and current_section in sections:
                sections[current_section]["versions"].extend(versions)
                all_versions.extend(versions)
        
        elif block["type"] == "table":
            rows = block["rows"]
            if not rows:
                continue
            
            table_count += 1
            headers = rows[0] if rows else []
            table_type = classify_table(headers)
            
            # 从表格cells提取约束和版本号
            for row in rows:
                for cell in row:
                    constraints = extract_constraints_from_text(cell, current_section)
                    versions = extract_versions_from_text(cell, current_section)
                    if constraints and current_section in sections:
                        sections[current_section]["constraints"].extend(constraints)
                        all_constraints.extend(constraints)
                    if versions and current_section in sections:
                        sections[current_section]["versions"].extend(versions)
                        all_versions.extend(versions)
                    for m in REQ_ID_RE.finditer(cell):
                        all_req_ids.add(m.group(0))
            
            if current_section in sections:
                sections[current_section]["tables"].append({
                    "table_id": f"T_{table_count}",
                    "type": table_type,
                    "headers": headers,
                    "rows": rows[1:] if len(rows) > 1 else [],
                    "row_count": len(rows),
                })
    
    total_constraints = sum(len(s["constraints"]) for s in sections.values())
    total_versions = sum(len(s["versions"]) for s in sections.values())
    total_tables = sum(len(s["tables"]) for s in sections.values())
    
    return {
        "doc_name": doc_name,
        "parse_date": datetime.now().isoformat(),
        "source": "textutil→HTML→structured(TOC映射)",
        "statistics": {
            "sections": len(sections),
            "tables": total_tables,
            "constraints": total_constraints,
            "versions": total_versions,
            "req_ids": len(all_req_ids),
            "toc_entries": len(toc_map),
        },
        "sections": sections,
        "all_constraints": all_constraints,
        "all_versions": all_versions,
        "all_req_ids": sorted(all_req_ids),
    }


def main():
    print("=" * 60)
    print("SRS标准解析 Pipeline (textutil→HTML→结构化)")
    print("=" * 60)
    
    doc_files = sorted(DATASET_DIR.glob("*.doc"))
    print(f"文档数: {len(doc_files)}")
    
    all_results = []
    for doc_path in doc_files:
        doc_name = doc_path.stem
        print(f"\n[{doc_name[:35]}]")
        
        result = parse_doc_to_structured(doc_path)
        
        # 保存
        output_path = OUTPUT_DIR / f"{doc_name}_structured.json"
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        
        stats = result["statistics"]
        print(f"  章节:{stats['sections']} 表格:{stats['tables']} 约束:{stats['constraints']} "
              f"版本:{stats['versions']} 需求ID:{stats['req_ids']}")
        
        all_results.append(result)
    
    # 汇总
    print(f"\n{'='*60}")
    print(f"汇总: {len(all_results)}份文档")
    total_c = sum(r["statistics"]["constraints"] for r in all_results)
    total_v = sum(r["statistics"]["versions"] for r in all_results)
    total_t = sum(r["statistics"]["tables"] for r in all_results)
    total_s = sum(r["statistics"]["sections"] for r in all_results)
    total_r = sum(r["statistics"]["req_ids"] for r in all_results)
    print(f"  总章节:{total_s} 总表格:{total_t} 总约束:{total_c} 总版本号:{total_v} 总需求ID:{total_r}")
    
    # 保存汇总
    summary = {
        "parse_date": datetime.now().isoformat(),
        "total_docs": len(all_results),
        "totals": {
            "sections": total_s, "tables": total_t,
            "constraints": total_c, "versions": total_v, "req_ids": total_r,
        },
        "docs": [{"doc_name": r["doc_name"], "stats": r["statistics"]} for r in all_results],
    }
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  汇总已保存: {OUTPUT_DIR / '_summary.json'}")


if __name__ == "__main__":
    main()
