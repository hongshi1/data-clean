#!/usr/bin/env python3
"""
SRS标准解析Pipeline (MinerU原生 L1→L2)
======================================
L1: MinerU标准解析(.doc→LibreOffice→.docx→MinerU→content_list.json)
L2: content_list→结构化JSON(章节/表格/图片/约束/版本)

MinerU content_list标准结构:
  text块: {type:"text", text:"...", text_level:1-6(标题), page_idx, anchor}
  table块: {type:"table", table_body:"<html>", table_caption:["..."], page_idx}
  image块: {type:"image", img_path:"...", image_caption:["..."], page_idx}

用法: python3 tools/srs_mineru_parse.py
"""
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
OUTPUT_DIR = BASE / "data/gjb_438c/mineru_structured"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')
CONSTRAINT_LE_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?')
CONSTRAINT_GE_RE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|≥|>=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|MHz|GHz|%|V|A|W|次|个|层|分钟|小时|天|字节|TB)?')
VERSION_RE = re.compile(
    r'(达梦|Oracle|MySQL|Linux|内核|GCC|CentOS|Ubuntu|Windows|Qt|银河麒麟|WPS|wps)'
    r'[^。]*?(V?\d+\.?\d*(?:\.\d+)?)')


class TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current_row = []
        elif tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.strip())

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.in_cell:
            self.current_row.append(' '.join(self.current_cell))
            self.in_cell = False
        elif tag == 'tr' and self.current_row:
            self.rows.append(self.current_row)


def parse_html_table(html: str) -> list:
    parser = TableHTMLParser()
    parser.feed(html)
    return parser.rows


def classify_table(caption: str, headers: list) -> str:
    c = (caption + ' '.join(headers)).lower()
    if any(kw in c for kw in ['序号', '版本号', '标记', '处数']):
        return 'modification'
    if any(kw in c for kw in ['需求名称', '合格性方法', '本文档章节号']):
        return 'qualification'
    if any(kw in c for kw in ['追踪', '跟踪', '任务书']):
        return 'traceability'
    if any(kw in c for kw in ['接口', '信号']):
        return 'interface'
    if any(kw in c for kw in ['文档编号', '标题', '修订']):
        return 'reference'
    if any(kw in c for kw in ['功能名称', '标识', '子功能']):
        return 'capability'
    return 'other'


def classify_role(param, section):
    for kw in ['时间','间隔','延迟','误差','精度','响应','定时','偏差','周期']:
        if kw in param:
            return "threshold"
    for kw in ['版本','型号','主频','内存','硬盘','存储','分辨率','显存']:
        if kw in param:
            return "config"
    for kw in ['最多','支持','容量','数量','上限','最大','并发']:
        if kw in param:
            return "capacity"
    if section.startswith('3.10'):
        return "config"
    if section.startswith('3.11'):
        return "threshold"
    return "description"


def extract_constraints(text, section):
    # 先清洗HTML标签
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    results = []
    for m in CONSTRAINT_LE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":"≤","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section})
    for m in CONSTRAINT_GE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":"≥","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section})
    return results


def _extract_param_name(before_text):
    """从约束前的文本提取参数名 — 按标点分割取最后一段"""
    # 按标点/空格分割,取最后一段含中文的部分
    parts = re.split(r'[，。；：、\s：:;,\n]+', before_text.strip())
    # 从后往前找含中文的段
    for part in reversed(parts):
        part = part.strip()
        if not part:
            continue
        # 提取其中的中文词(2-8字)
        cn_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', part)
        if cn_m:
            return cn_m.group(1)
        # 如果段本身是中文
        if re.match(r'^[\u4e00-\u9fa5]{2,8}$', part):
            return part
    # fallback: 取最后8个字符
    return before_text[-8:].strip()


def extract_versions(text, section):
    # 先清洗HTML标签
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    results = []
    for m in VERSION_RE.finditer(text):
        results.append({"software":m.group(1),"version":m.group(2),
                       "section":section,
                       "original":text[max(0,m.start()-10):m.end()+10]})
    return results


def parse_mineru_output(doc_dir: Path) -> dict:
    """从MinerU标准产出提取结构化数据"""
    doc_name = doc_dir.name
    office_dir = doc_dir / "office"
    cl_path = office_dir / f"{doc_name}_content_list.json"
    if not cl_path.exists():
        return {"error": f"content_list不存在: {cl_path}"}

    content_list = json.loads(cl_path.read_text(encoding="utf-8"))

    sections = defaultdict(lambda: {"title":"","text":"","tables":[],"images":[],
                                    "constraints":[],"versions":[]})
    current_section = ""
    all_constraints = []
    all_versions = []
    all_req_ids = set()
    table_count = 0
    image_count = 0

    for item in content_list:
        item_type = item.get("type", "text")

        if item_type == "text":
            text = item.get("text", "")
            text_level = item.get("text_level", 0)

            # 标题块(text_level > 0)
            if text_level > 0:
                m = SECTION_RE.match(text.strip())
                if m:
                    number, title = m.group(1), m.group(2).strip()
                    current_section = number
                    sections[number]["title"] = title
                    req_m = REQ_ID_RE.search(title)
                    if req_m:
                        sections[number]["req_id"] = req_m.group(0)
                        all_req_ids.add(req_m.group(0))
                continue

            # 跳过目录行
            if 'PAGEREF' in text or 'HYPERLINK' in text or text.strip() == '目    录':
                continue

            # 累积文本
            if current_section:
                sections[current_section]["text"] += text + "\n"

            # 提取约束/版本/需求ID
            cs = extract_constraints(text, current_section)
            vs = extract_versions(text, current_section)
            if cs:
                sections[current_section]["constraints"].extend(cs)
                all_constraints.extend(cs)
            if vs:
                sections[current_section]["versions"].extend(vs)
                all_versions.extend(vs)
            for m in REQ_ID_RE.finditer(text):
                all_req_ids.add(m.group(0))

        elif item_type == "table":
            table_count += 1
            table_body = item.get("table_body", "")
            table_caption = item.get("table_caption", [])
            caption_str = ' '.join(table_caption) if table_caption else ""

            # 解析HTML表格
            rows = parse_html_table(table_body)
            headers = rows[0] if rows else []
            table_type = classify_table(caption_str, headers)

            # 从表格内容提取约束/版本
            full_text = caption_str + " " + table_body
            cs = extract_constraints(full_text, current_section)
            vs = extract_versions(full_text, current_section)
            if cs:
                sections[current_section]["constraints"].extend(cs)
                all_constraints.extend(cs)
            if vs:
                sections[current_section]["versions"].extend(vs)
                all_versions.extend(vs)
            for m in REQ_ID_RE.finditer(full_text):
                all_req_ids.add(m.group(0))

            sections[current_section]["tables"].append({
                "table_id": f"T_{table_count}",
                "type": table_type,
                "caption": caption_str,
                "headers": headers,
                "rows": rows[1:] if len(rows) > 1 else [],
                "row_count": len(rows),
            })

        elif item_type == "image":
            image_count += 1
            img_path = item.get("img_path", "")
            img_caption = item.get("image_caption", [])
            caption_str = ' '.join(img_caption) if img_caption else ""

            sections[current_section]["images"].append({
                "image_id": f"IMG_{image_count}",
                "path": img_path,
                "caption": caption_str,
                "section": current_section,
            })

    total_tables = sum(len(s["tables"]) for s in sections.values())
    total_images = sum(len(s["images"]) for s in sections.values())

    return {
        "doc_name": doc_name,
        "parse_date": datetime.now().isoformat(),
        "source": "MinerU标准解析(LibreOffice→.docx→MinerU→content_list)",
        "statistics": {
            "sections": len(sections),
            "tables": total_tables,
            "images": total_images,
            "constraints": len(all_constraints),
            "versions": len(all_versions),
            "req_ids": len(all_req_ids),
            "content_blocks": len(content_list),
        },
        "sections": dict(sections),
        "all_constraints": all_constraints,
        "all_versions": all_versions,
        "all_req_ids": sorted(all_req_ids),
    }


def main():
    print("=" * 60)
    print("SRS标准解析 Pipeline (MinerU原生 L1→L2)")
    print("=" * 60)

    all_results = []
    for doc_dir in sorted(MINERU_DIR.iterdir()):
        if not doc_dir.is_dir():
            continue
        doc_name = doc_dir.name[:35]
        result = parse_mineru_output(doc_dir)
        if "error" in result:
            print(f"  [{doc_name}] {result['error']}")
            continue
        s = result["statistics"]
        print(f"  [{doc_name}] 章节:{s['sections']} 表格:{s['tables']} 图片:{s['images']} "
              f"约束:{s['constraints']} 版本:{s['versions']} 需求ID:{s['req_ids']}")
        out = OUTPUT_DIR / f"{doc_dir.name}_structured.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        all_results.append(result)

    total_s = sum(r["statistics"]["sections"] for r in all_results)
    total_t = sum(r["statistics"]["tables"] for r in all_results)
    total_i = sum(r["statistics"]["images"] for r in all_results)
    total_c = sum(r["statistics"]["constraints"] for r in all_results)
    total_v = sum(r["statistics"]["versions"] for r in all_results)
    total_r = sum(r["statistics"]["req_ids"] for r in all_results)

    print(f"\n{'='*60}")
    print(f"汇总: {len(all_results)}份文档")
    print(f"  章节:{total_s} 表格:{total_t} 图片:{total_i} 约束:{total_c} 版本:{total_v} 需求ID:{total_r}")

    (OUTPUT_DIR / "_summary.json").write_text(json.dumps({
        "parse_date": datetime.now().isoformat(),
        "pipeline": "MinerU标准(LibreOffice+MinerU+content_list)",
        "total_docs": len(all_results),
        "totals": {"sections":total_s,"tables":total_t,"images":total_i,
                   "constraints":total_c,"versions":total_v,"req_ids":total_r},
        "docs": [{"doc_name":r["doc_name"][:30],"stats":r["statistics"]} for r in all_results],
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
