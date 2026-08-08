#!/usr/bin/env python3
"""
SRS Markdown → outline.xml + all_content.xml
=============================================
改自 AgentFlow DocDancer 的 projects/DocDancer/PDF_preprocess/3_get_outline_and_root.py

把解析后的SRS markdown转为AgentFlow可消费的XML格式:
- outline.xml: 章节层级树(精简,作seed)
- all_content.xml: 全部内容(含段落/表格/图片引用)

节点类型 (仿DocDancer):
  Section(section_id, title, start_line)
  Paragraph(line, text)
  Table(table_id, type, section, headers, rows)
  Image(image_id, section, caption)

用法: python3 tools/srs_to_xml.py
"""
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE / "data/gjb_438c/parsed_srs_dataset"
OUTPUT_DIR = BASE / "data/srs_outline"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 章节标题正则 (与srs_doc_batch_parse.py一致)
SECTION_RE = re.compile(r'^(#{2,5})\s+(\d+(?:\.\w+)*)\s+(.+)', re.MULTILINE)

# 需求ID正则
REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')


class TableHTMLParser(HTMLParser):
    """简单HTML表格解析器"""
    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.current_cell = None
        self.in_table = False
    
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
            self.current_table = {'headers': [], 'rows': []}
        elif tag == 'tr' and self.current_table:
            self.current_row = []
        elif tag in ('td', 'th') and self.current_row is not None:
            self.current_cell = ''
    
    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell += data.strip()
    
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.current_row is not None:
            self.current_row.append(self.current_cell or '')
            self.current_cell = None
        elif tag == 'tr' and self.current_row is not None:
            row = self.current_row
            if self.current_table['headers'] and not self.current_table['rows']:
                # 第一行可能已经是headers了
                pass
            if not self.current_table['headers']:
                self.current_table['headers'] = row
            else:
                self.current_table['rows'].append(row)
            self.current_row = None
        elif tag == 'table' and self.current_table:
            self.tables.append(self.current_table)
            self.current_table = None
            self.in_table = False


def classify_table(headers: list, section: str) -> str:
    """分类表格类型 (参考srs_table_parser.py:125-141)"""
    header_text = ' '.join(headers).lower()
    if any(kw in header_text for kw in ['序号', '版本号', '标记']):
        return 'modification'
    elif any(kw in header_text for kw in ['需求名称', '需求标识', '合格性方法', '合格性']):
        return 'qualification'
    elif any(kw in header_text for kw in ['追踪', '跟踪', '任务书']):
        return 'traceability'
    elif any(kw in header_text for kw in ['接口', '信号']):
        return 'interface'
    elif any(kw in header_text for kw in ['文档编号', '标题', '修订']):
        return 'reference'
    elif any(kw in header_text for kw in ['数据', '类型', '大小']):
        return 'data_dictionary'
    return 'other'


def parse_markdown_to_xml(md_text: str, doc_id: str) -> tuple[ET.Element, ET.Element]:
    """
    把SRS markdown转为outline.xml + all_content.xml
    
    改进:
    1. Word SEQ表格解析 (表 SEQ 表 \* ARABIC N 标题 + 后续纯文本行)
    2. 章节去重 (目录+正文重复时只保留有内容的版本)
    """
    lines = md_text.split('\n')
    
    outline_root = ET.Element("Outline")
    outline_root.set("doc_id", doc_id)
    
    content_root = ET.Element("Document")
    content_root.set("doc_id", doc_id)
    
    section_stack = []  # [(number, level, outline_elem, content_elem)]
    table_counter = 0
    image_counter = 0
    current_content_sec = None
    
    # 章节去重: 记录已有section_id → content_elem (只保留有段落的版本)
    section_map = {}  # section_id → content_elem
    
    # 表格解析状态
    in_seq_table = False
    seq_table_title = ""
    seq_table_lines = []
    seq_table_section = ""
    
    TABLE_SEQ_RE = re.compile(r'表\s*SEQ\s*表\s*\\\*\s*ARABIC\s*(\d+)\s*(.*)')
    
    def flush_seq_table():
        """结束当前Word SEQ表格,创建Table节点"""
        nonlocal table_counter, in_seq_table, seq_table_title, seq_table_lines, seq_table_section
        if not seq_table_lines:
            in_seq_table = False
            return
        
        table_counter += 1
        
        # 判断列数: 根据表头关键词
        header_keywords = {
            'qualification': ['需求名称', '需求标识', '合格性方法', '合格性', '本文档章节号'],
            'traceability': ['追踪', '跟踪', '任务书', '本文档章节', '跟踪说明'],
            'reference': ['文档编号', '标题', '修订版本', '修订日期', '编写单位'],
            'modification': ['序号', '版本号', '标记', '处数', '更改文件号'],
        }
        
        # 判断表格类型
        all_text = ' '.join(seq_table_lines[:15])
        table_type = 'other'
        for t, keywords in header_keywords.items():
            if sum(1 for kw in keywords if kw in all_text) >= 2:
                table_type = t
                break
        
        # 估算列数
        col_counts = {'qualification': 5, 'traceability': 5, 'reference': 5, 'modification': 8}
        num_cols = col_counts.get(table_type, 5)
        
        # 分组为行
        headers = seq_table_lines[:num_cols] if len(seq_table_lines) >= num_cols else seq_table_lines
        data_rows = []
        remaining = seq_table_lines[num_cols:]
        for i in range(0, len(remaining), num_cols):
            row = remaining[i:i+num_cols]
            if any(cell.strip() for cell in row):
                data_rows.append(row)
        
        # 创建Table XML节点
        table_elem = ET.SubElement(content_root, "Table")
        table_elem.set("table_id", f"T_{table_counter}")
        table_elem.set("type", table_type)
        table_elem.set("title", seq_table_title)
        table_elem.set("section", seq_table_section)
        
        headers_elem = ET.SubElement(table_elem, "Headers")
        for h in headers:
            cell = ET.SubElement(headers_elem, "Cell")
            cell.text = h.strip()
        
        for row_data in data_rows:
            row_elem = ET.SubElement(table_elem, "Row")
            for cell_data in row_data:
                cell = ET.SubElement(row_elem, "Cell")
                cell.text = cell_data.strip()
        
        # 重置
        in_seq_table = False
        seq_table_title = ""
        seq_table_lines = []
        seq_table_section = ""
    
    for line_no, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # 检测Word SEQ表格标记
        seq_m = TABLE_SEQ_RE.match(stripped)
        if seq_m:
            # 结束上一个表格
            if in_seq_table:
                flush_seq_table()
            
            in_seq_table = True
            seq_table_title = seq_m.group(2).strip()
            seq_table_section = current_content_sec.get('section_id', '') if current_content_sec is not None else ''
            seq_table_lines = []
            continue
        
        # 如果在表格中,收集行
        if in_seq_table:
            # 跳过空行
            if not stripped:
                continue
            # 遇到章节标题→结束表格,继续处理章节标题(不continue)
            if re.match(r'^#{2,5}\s+\d', stripped):
                flush_seq_table()
                # 不continue,继续往下处理章节标题
            else:
                seq_table_lines.append(stripped)
                continue
        
        # 跳过HTML表格行
        if '<table>' in stripped.lower():
            continue
        
        # 章节标题
        m = SECTION_RE.match(stripped)
        if m:
            # 结束当前表格
            if in_seq_table:
                flush_seq_table()
            
            number = m.group(2)
            title = m.group(3).strip()
            level = number.count('.')
            
            # 弹栈
            while section_stack and section_stack[-1][1] >= level:
                section_stack.pop()
            
            # 章节不去重,保留所有版本(目录+正文),lint检测中调阈值
            # 新章节
            outline_sec = ET.SubElement(outline_root, "Section")
            outline_sec.set("section_id", number)
            outline_sec.set("title", title)
            
            content_sec = ET.SubElement(content_root, "Section")
            content_sec.set("section_id", number)
            content_sec.set("title", title)
            content_sec.set("start_line", str(line_no))
            
            req_id_m = REQ_ID_RE.search(title)
            if req_id_m:
                content_sec.set("req_id", req_id_m.group(0))
            
            section_map[number] = content_sec
            section_stack.append((number, level, outline_sec, content_sec))
            current_content_sec = content_sec
            continue
        
        # 段落
        if stripped and current_content_sec is not None:
            if len(stripped) < 2:
                continue
            
            para = ET.SubElement(current_content_sec, "Paragraph")
            para.set("line", str(line_no))
            para.text = stripped[:500]
        
        # 图片引用
        if ('EMBED' in stripped or '图 SEQ' in stripped) and current_content_sec is not None:
            image_counter += 1
            img = ET.SubElement(current_content_sec, "Image")
            img.set("image_id", f"IMG_{image_counter}")
            img.set("section", current_content_sec.get("section_id", ""))
            caption_m = re.search(r'图\s*SEQ.*?(\d+)\s*(.+)', stripped)
            if caption_m:
                img.set("figure_number", caption_m.group(1))
                img.set("caption", caption_m.group(2).strip())
    
    # 结束最后一个表格
    if in_seq_table:
        flush_seq_table()
    
    return outline_root, content_root


def xml_to_string(elem: ET.Element) -> str:
    """XML元素转字符串(带缩进)"""
    ET.indent(elem, space="  ")
    return ET.tostring(elem, encoding='unicode', method='xml')


def main():
    print("=" * 60)
    print("SRS Markdown → outline.xml + all_content.xml")
    print("=" * 60)
    
    meta_path = INPUT_DIR / "_dataset_metadata.json"
    if not meta_path.exists():
        print("[!] 元数据不存在,请先运行srs_doc_batch_parse.py")
        return
    
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    usable_docs = [d for d in meta["docs"] if d["section_count"] >= 20]
    
    print(f"可用文档: {len(usable_docs)}")
    
    results = []
    for doc_info in usable_docs:
        doc_name = doc_info["doc_name"]
        md_path = Path(doc_info["md_path"])
        if not md_path.exists():
            continue
        
        md_text = md_path.read_text(encoding="utf-8")
        doc_id = doc_name[:20]
        
        outline_root, content_root = parse_markdown_to_xml(md_text, doc_id)
        
        # 保存
        outline_path = OUTPUT_DIR / f"{doc_id}_outline.xml"
        content_path = OUTPUT_DIR / f"{doc_id}_content.xml"
        
        outline_path.write_text(xml_to_string(outline_root), encoding="utf-8")
        content_path.write_text(xml_to_string(content_root), encoding="utf-8")
        
        # 统计
        sections = outline_root.findall(".//Section")
        paragraphs = content_root.findall(".//Paragraph")
        tables = content_root.findall(".//Table")
        images = content_root.findall(".//Image")
        
        results.append({
            "doc_id": doc_id,
            "sections": len(sections),
            "paragraphs": len(paragraphs),
            "tables": len(tables),
            "images": len(images),
        })
        
        print(f"  {doc_name[:35]:35s} 章节:{len(sections):3d} 段落:{len(paragraphs):4d} 表格:{len(tables):2d} 图片:{len(images):2d}")
    
    # 保存元数据
    summary = {
        "generate_date": datetime.now().isoformat(),
        "total_docs": len(results),
        "output_dir": str(OUTPUT_DIR),
        "docs": results,
    }
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n生成完成: {len(results)}份文档 → {OUTPUT_DIR}")
    print(f"每份产出: {{doc_id}}_outline.xml + {{doc_id}}_content.xml")


if __name__ == "__main__":
    main()
