#!/usr/bin/env python3
"""
SRS数据处理流水线 (可复用)
=========================
从原始GJB格式.doc文件到高质量结构化JSON的完整3层流水线:

L1: .doc → LibreOffice → .docx → MinerU → content_list.json
L2: content_list.json → 结构化JSON (章节/表格/图片/约束/版本/req_id)
L3: 结构化JSON → 7项修复 (图片EMF→PNG / 约束去重 / unit补充 /
    用例表约束 / req_id位置 / 版本号过滤 / caption统一)

用法:
  # 处理单个文档
  python3 tools/srs_pipeline.py --input "data/软件需归样例数据集/01xxx.doc"
  
  # 处理整个目录
  python3 tools/srs_pipeline.py --input "data/软件需归样例数据集/"
  
  # 指定输出目录
  python3 tools/srs_pipeline.py --input "data/软件需归样例数据集/" --output "data/processed/"
  
  # 跳过L1(已有MinerU输出)
  python3 tools/srs_pipeline.py --input "data/软件需归样例数据集/" --skip-l1
  
  # 仅运行L3修复
  python3 tools/srs_pipeline.py --input "data/软件需归样例数据集/" --skip-l1 --skip-l2

依赖:
  - LibreOffice (soffice) : .doc→.docx, EMF→PNG
  - MinerU (~/mineru-env) : .docx→content_list.json
  - Python 3.12+ (.venv-srs)
"""
import argparse
import json
import re
import sys
import shutil
import zipfile
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from html.parser import HTMLParser

# ============================================================
# 配置
# ============================================================
BASE = Path(__file__).resolve().parent.parent
MINERU_PYTHON = Path.home() / "mineru-env" / "bin" / "python"
SOFFICE = "soffice"

# ============================================================
# L1: MinerU标准解析
# ============================================================

def run_l1(doc_path: Path, output_dir: Path) -> Path:
    """L1: .doc → .docx → MinerU → content_list.json
    返回: content_list.json所在的office目录
    """
    doc_name = doc_path.stem
    doc_dir = output_dir / doc_name
    office_dir = doc_dir / "office"
    office_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: .doc → .docx (LibreOffice)
    docx_path = office_dir / f"{doc_name}.docx"
    if not docx_path.exists():
        print(f"  [L1] .doc → .docx: {doc_name}")
        subprocess.run(
            [SOFFICE, '--headless', '--convert-to', 'docx',
             '--outdir', str(office_dir), str(doc_path)],
            capture_output=True, text=True, timeout=60
        )
        # LibreOffice可能输出不同文件名
        generated = list(office_dir.glob("*.docx"))
        if generated and generated[0] != docx_path:
            shutil.move(str(generated[0]), str(docx_path))

    if not docx_path.exists():
        print(f"  [L1] ✗ .docx生成失败: {doc_name}")
        return None

    # Step 2: .docx → MinerU
    content_list_path = office_dir / f"{doc_name}_content_list.json"
    if not content_list_path.exists():
        print(f"  [L1] MinerU解析: {doc_name}")
        mineru_script = BASE / "tools" / "srs_mineru_parse.py"
        # MinerU需要用mineru-env的python
        result = subprocess.run(
            [str(MINERU_PYTHON), '-c', f'''
import sys
sys.path.insert(0, "{BASE}")
from magic_pdf.pipe.UNIPipe import UNIPipe
from magic_pdf.rw.DiskReaderWriter import DiskReaderWriter
import os, json

image_dir = "{office_dir}/images"
os.makedirs(image_dir, exist_ok=True)
model_dir = "{office_dir}"

# 读取docx
from magic_pdf.libs.commons import join_path
from magic_pdf.tools.common import do_parse
do_parse(
    "{docx_path}",
    model_dir,
    image_dir,
    "{MINERU_PYTHON}",
    False,  # parse_mode
)
'''],
            capture_output=True, text=True, timeout=300,
            cwd=str(office_dir)
        )
        # MinerU输出文件名可能不同,查找content_list
        cls = list(office_dir.glob("*content_list*.json"))
        if cls:
            if cls[0] != content_list_path:
                shutil.move(str(cls[0]), str(content_list_path))

    if not content_list_path.exists():
        print(f"  [L1] ✗ MinerU解析失败: {doc_name}")
        return None

    print(f"  [L1] ✓ {doc_name}: {content_list_path.name}")
    return office_dir


# ============================================================
# L2: 结构化提取
# ============================================================

class TableHTMLParser(HTMLParser):
    """支持colspan/rowspan的HTML表格解析器
    
    将合并单元格展开为标准网格:
    - colspan=2的单元格复制到2列(第二列为空)
    - rowspan=2的单元格在下一行同列填充相同内容
    """
    def __init__(self):
        super().__init__()
        self.rows = []          # 最终的网格行
        self.current_row = []   # 当前行单元格
        self.current_cell = []  # 当前单元格文本
        self.in_cell = False
        self.cell_attrs = {}    # 当前单元格的colspan/rowspan
        self.pending_rowspans = {}  # col_idx → (text, remaining_rows)
    
    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.current_row = []
        elif tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = []
            self.cell_attrs = dict(attrs)
    
    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.strip())
    
    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.in_cell:
            cell_text = ' '.join(self.current_cell)
            colspan = int(self.cell_attrs.get('colspan', '1'))
            rowspan = int(self.cell_attrs.get('rowspan', '1'))
            
            # 展开colspan: 一个单元格复制到多列
            for i in range(colspan):
                col_idx = len(self.current_row)
                # 如果当前位置有pending rowspan,先填充它
                while col_idx in self.pending_rowspans:
                    text, remaining = self.pending_rowspans[col_idx]
                    self.current_row.append(text)
                    if remaining > 1:
                        self.pending_rowspans[col_idx] = (text, remaining - 1)
                    else:
                        del self.pending_rowspans[col_idx]
                    col_idx = len(self.current_row)
                
                # 填充当前单元格
                if i == 0:
                    self.current_row.append(cell_text)
                else:
                    self.current_row.append('')  # colspan展开的空列
                
                # 注册rowspan
                if rowspan > 1:
                    actual_col = len(self.current_row) - 1
                    self.pending_rowspans[actual_col] = (cell_text, rowspan - 1)
            
            self.in_cell = False
        elif tag == 'tr' and self.current_row:
            # 行结束: 填充pending rowspans
            col_idx = len(self.current_row)
            while col_idx in self.pending_rowspans:
                text, remaining = self.pending_rowspans[col_idx]
                self.current_row.append(text)
                if remaining > 1:
                    self.pending_rowspans[col_idx] = (text, remaining - 1)
                else:
                    del self.pending_rowspans[col_idx]
                col_idx = len(self.current_row)
            
            self.rows.append(self.current_row)

def parse_html_table(html: str) -> list:
    parser = TableHTMLParser()
    parser.feed(html)
    return parser.rows

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')
CONSTRAINT_LE_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
CONSTRAINT_GE_RE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|以上|≥|>=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
CONSTRAINT_GT_RE = re.compile(
    r'(?:大于|超过|高于)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
VERSION_RE = re.compile(
    r'(达梦|Oracle|MySQL|Linux|内核|GCC|CentOS|Ubuntu|Windows|Qt|银河麒麟|WPS|wps|Redis|Nginx)'
    r'[^。]*?(V?\d+\.?\d*(?:\.\d+)?)')

def classify_table(caption, headers, section_id=""):
    """表格分类 — 按优先级从高到低匹配
    
    关键: "接口"检查必须在"序号"之前,否则所有含"序号"的接口表都会被误分类为modification
    """
    c = (caption + ' '.join(headers)).lower()
    # 1. 合格性表(第4章,最特异)
    if any(kw in c for kw in ['合格性方法', '本文档章节号', '合格性级别']):
        return 'qualification'
    # 2. 追踪表(第5章)
    if any(kw in c for kw in ['追踪', '跟踪', '任务书']):
        return 'traceability'
    # 3. 用例表(特异度高)
    if 'use case' in c.lower() or 'actor' in c.lower():
        return 'usecase'
    # 4. 引用文档表
    if any(kw in c for kw in ['文档编号', '修订版本', '编写单位']):
        return 'reference'
    # 5. 数据集/数据元素表(表头特异度高,优先于接口判断)
    if any(kw in c for kw in ['数据集名称', '数据组成', '数据元素名称', '数据元素标识']):
        return 'data_spec'
    # 6. 接口表(3.3.x/3.4.x) — 检查表头中的接口关键词
    if any(kw in c for kw in ['接口名称', '接口需求', '接口描述', '接口类型', '接口标识']):
        return 'interface'
    if section_id and (section_id.startswith('3.3') or section_id.startswith('3.4')):
        return 'interface'
    # 7. 功能划分表
    if any(kw in c for kw in ['功能名称', '子功能', '功能标识']):
        return 'capability'
    # 8. 修改记录表
    if any(kw in c for kw in ['版本号', '标记', '处数', '修订']):
        return 'modification'
    # 9. 序号开头的通用表(最低优先级)
    if any(kw in c for kw in ['序号']):
        return 'modification'
    return 'other'

def classify_role(param, section):
    for kw in ['时间','间隔','延迟','误差','精度','响应','定时','偏差','周期']:
        if kw in param: return "threshold"
    for kw in ['版本','型号','主频','内存','硬盘','存储','分辨率','显存']:
        if kw in param: return "config"
    for kw in ['最多','支持','容量','数量','上限','最大','并发']:
        if kw in param: return "capacity"
    if section and section.startswith('3.10'): return "config"
    if section and section.startswith('3.11'): return "threshold"
    return "description"

def _extract_param_name(before_text):
    parts = re.split(r'[，。；：、\s：:;,\n]+', before_text.strip())
    for part in reversed(parts):
        part = part.strip()
        if not part: continue
        cn_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', part)
        if cn_m: return cn_m.group(1)
        if re.match(r'^[\u4e00-\u9fa5]{2,8}$', part): return part
    return before_text[-8:].strip()

def extract_constraints_from_text(text, section, source="text"):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    results = []
    for m in CONSTRAINT_LE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":"≤","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],
                       "section":section,"source":source})
    for m in CONSTRAINT_GE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":"≥","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],
                       "section":section,"source":source})
    for m in CONSTRAINT_GT_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":">","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],
                       "section":section,"source":source})
    return results

def extract_versions(text, section):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    results = []
    for m in VERSION_RE.finditer(text):
        results.append({"software":m.group(1),"version":m.group(2),
                       "section":section,
                       "original":text[max(0,m.start()-10):m.end()+10]})
    return results

def run_l2(doc_name: str, office_dir: Path) -> dict:
    """L2: content_list.json → 结构化JSON"""
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
        if not isinstance(item, dict): continue
        item_type = item.get("type", "text")

        if item_type == "text":
            text = item.get("text", "")
            text_level = item.get("text_level", 0)
            if text_level > 0:
                m = SECTION_RE.match(text.strip())
                if m:
                    current_section = m.group(1)
                    sections[current_section]["title"] = m.group(2).strip()
                    req_m = REQ_ID_RE.search(text)
                    if req_m:
                        sections[current_section]["req_id"] = req_m.group(0)
                        all_req_ids.add(req_m.group(0))
                continue
            if 'PAGEREF' in text or 'HYPERLINK' in text or text.strip() == '目    录':
                continue
            # 清理HTML标签残留
            text = re.sub(r'<[^>]+>', '', text)
            if current_section:
                sections[current_section]["text"] += text + "\n"
            cs = extract_constraints_from_text(text, current_section)
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
            rows = parse_html_table(table_body)
            headers = rows[0] if rows else []
            table_type = classify_table(caption_str, headers, current_section)
            full_text = caption_str + " " + table_body
            cs = extract_constraints_from_text(full_text, current_section)
            vs = extract_versions(full_text, current_section)
            if cs:
                sections[current_section]["constraints"].extend(cs)
                all_constraints.extend(cs)
            if vs:
                sections[current_section]["versions"].extend(vs)
                all_versions.extend(vs)
            for m in REQ_ID_RE.finditer(full_text):
                all_req_ids.add(m.group(0))
            # 过滤空表格(body<30字符且无caption)
            if len(table_body) < 30 and not caption_str:
                table_count -= 1  # 回退计数
                continue
            sections[current_section]["tables"].append({
                "table_id": f"T_{table_count}", "type": table_type,
                "caption": caption_str, "headers": headers,
                "rows": rows[1:] if len(rows) > 1 else [], "row_count": len(rows),
                "section": current_section,
            })

        elif item_type == "image":
            image_count += 1
            img_path = item.get("img_path", "")
            img_caption = item.get("image_caption", [])
            caption_str = ' '.join(img_caption) if img_caption else ""
            sections[current_section]["images"].append({
                "image_id": f"IMG_{image_count}", "path": img_path,
                "caption": caption_str, "section": current_section,
            })

    return {
        "doc_name": doc_name,
        "parse_date": datetime.now().isoformat(),
        "source": "L1+L2 pipeline",
        "statistics": {
            "sections": len(sections), "tables": table_count,
            "images": image_count, "constraints": len(all_constraints),
            "versions": len(all_versions), "req_ids": len(all_req_ids),
            "content_blocks": len(content_list),
        },
        "sections": dict(sections),
        "all_constraints": all_constraints,
        "all_versions": all_versions,
        "all_req_ids": sorted(all_req_ids),
        "_content_list": content_list,  # 保留供L3使用
    }


# ============================================================
# L3: 7项修复
# ============================================================

# --- L3-Fix1: 图片EMF→PNG ---
def fix_images(doc_name, content_list, office_dir, output_img_dir):
    docx_path = office_dir / f"{doc_name}_origin.docx"
    if not docx_path.exists():
        # 尝试其他文件名
        docx_candidates = list(office_dir.glob("*.docx"))
        if docx_candidates:
            docx_path = docx_candidates[0]
        else:
            return []

    with zipfile.ZipFile(docx_path, 'r') as z:
        all_media = sorted([n for n in z.namelist() if 'media/' in n],
                          key=lambda x: int(re.search(r'image(\d+)', x).group(1)) if re.search(r'image(\d+)', x) else 999)

    if not all_media:
        return []

    content_images = [(i, item) for i, item in enumerate(content_list)
                     if isinstance(item, dict) and item.get('type') == 'image']
    num_images = len(content_images)
    output_img_dir.mkdir(parents=True, exist_ok=True)
    doc_subdir = doc_name[:20]
    new_paths = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        for idx in range(min(num_images, len(all_media))):
            mf = all_media[idx]
            ext = Path(mf).suffix.lower()
            png_name = f"img_{idx+1:03d}.png"
            png_path = output_img_dir / png_name
            rel_path = f"images/{doc_subdir}/{png_name}"

            if png_path.exists() and png_path.stat().st_size > 0:
                new_paths.append(rel_path)
                content_images[idx][1]['img_path'] = rel_path
                continue

            if ext == '.emf':
                with zipfile.ZipFile(docx_path, 'r') as z:
                    z.extract(mf, tmpdir)
                emf_path = tmpdir / mf
                subprocess.run(
                    [SOFFICE, '--headless', '--convert-to', 'png',
                     '--outdir', str(output_img_dir), str(emf_path)],
                    capture_output=True, text=True, timeout=30
                )
                generated = output_img_dir / f"{emf_path.stem}.png"
                if generated.exists():
                    if generated != png_path:
                        shutil.move(str(generated), str(png_path))
                    new_paths.append(rel_path)
                    content_images[idx][1]['img_path'] = rel_path
                else:
                    new_paths.append(content_images[idx][1].get('img_path', ''))
            elif ext in ('.png', '.jpg', '.jpeg'):
                with zipfile.ZipFile(docx_path, 'r') as z:
                    with z.open(mf) as src, open(png_path, 'wb') as dst:
                        dst.write(src.read())
                new_paths.append(rel_path)
                content_images[idx][1]['img_path'] = rel_path
            else:
                new_paths.append(content_images[idx][1].get('img_path', ''))

        for idx in range(len(all_media), num_images):
            new_paths.append(content_images[idx][1].get('img_path', ''))

    return new_paths

# --- L3-Fix2: 约束去重 ---
def dedup_constraints(constraints):
    seen = {}
    result = []
    for c in constraints:
        key = (c.get('param',''), c.get('operator',''), c.get('value',''),
               c.get('unit',''), c.get('section',''))
        if key not in seen:
            seen[key] = len(result)
            result.append(c)
        else:
            existing = result[seen[key]]
            if not existing.get('source') and c.get('source'):
                result[seen[key]] = c
    return result

# --- L3-Fix3: unit补充 ---
UNIT_PATTERNS = [
    (r'条/秒', '条/秒'), (r'次/秒', '次/秒'), (r'笔/秒', '笔/秒'),
    (r'Mpps', 'Mpps'), (r'Tbps', 'Tbps'), (r'Gbps', 'Gbps'), (r'Mbps', 'Mbps'),
    (r'(GB|gb)', 'GB'), (r'(TB|tb)', 'TB'), (r'(MB|mb)', 'MB'), (r'(KB|kb)', 'KB'),
    (r'(GHz|ghz)', 'GHz'), (r'(MHz|mhz)', 'MHz'),
    (r'(ms|毫秒)', 'ms'), (r'(s|秒)(?![\w])', 's'),
    (r'分钟', '分钟'), (r'小时', '小时'), (r'天', '天'), (r'%', '%'),
    (r'核', '核'), (r'个', '个'), (r'块', '块'), (r'台', '台'),
    (r'路', '路'), (r'层', '层'), (r'屏', '屏'), (r'次', '次'), (r'维', '维'),
    (r'(\d+×\d+)', None),
]

def extract_unit_from_original(original, value, param=''):
    val_str = str(value)
    if '.' in val_str: val_str = val_str.rstrip('0').rstrip('.')
    idx = original.find(val_str)
    if idx < 0:
        try: idx = original.find(str(int(float(value))))
        except: pass
    if idx < 0: return ''
    after = original[idx + len(val_str):].strip()
    if re.match(r'^Hz', after, re.IGNORECASE):
        if '主频' in param or 'CPU' in param or '频率' in param: return 'GHz'
        return 'Hz'
    for pattern, unit_name in UNIT_PATTERNS:
        m = re.match(pattern, after, re.IGNORECASE)
        if m:
            return unit_name if unit_name else m.group(0)
    if after.startswith('×') or after.startswith('*'):
        m = re.match(r'[×*]\s*(\d+)', after)
        if m: return f'×{m.group(1)}'
    if re.match(r'^g\b', after, re.IGNORECASE): return 'GB'
    if re.match(r'^分屏', after): return '分屏'
    return ''

def fix_constraint_units(constraints):
    for c in constraints:
        if not c.get('unit'):
            unit = extract_unit_from_original(c.get('original',''), c.get('value',''), c.get('param',''))
            if unit: c['unit'] = unit
    return constraints

# --- L3-Fix4: 用例表约束 ---
VERSION_CONSTRAINT_RE = re.compile(
    r'(nodejs|Node\.js|java|Python|Qt|达梦|Oracle|MySQL|Redis|Nginx)'
    r'[^。]*?(V?\d+\.?\d*(?:\.\d+)?)\s*以上', re.IGNORECASE)

def extract_usecase_constraints(table_body, caption, section):
    rows = parse_html_table(table_body)
    if not rows: return [], None
    headers = rows[0] if rows else []
    headers_text = ' '.join(str(h) for h in headers)
    if 'Use Case' not in headers_text and 'Actor' not in headers_text:
        return [], None

    constraint_col_idx = -1
    constraint_header_row = -1
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if '动作约束' in str(cell) or ('性能' in str(cell) and '可靠性' in str(cell)):
                constraint_col_idx = j
                constraint_header_row = i
                break
        if constraint_col_idx >= 0: break
    if constraint_col_idx < 0: return [], None

    constraint_texts = []
    for i in range(constraint_header_row + 1, len(rows)):
        row = rows[i]
        if constraint_col_idx < len(row):
            cell = row[constraint_col_idx].strip()
            if cell and cell != '—' and cell != '-':
                constraint_texts.append(cell)

    all_constraints = []
    for ct in constraint_texts:
        cs = extract_constraints_from_text(ct, section, source="usecase_action_constraint")
        all_constraints.extend(cs)
        for m in VERSION_CONSTRAINT_RE.finditer(ct):
            before = ct[max(0,m.start()-10):m.start()]
            param = _extract_param_name(before) or m.group(1)
            all_constraints.append({
                "param": param, "operator": "≥",
                "value": m.group(2), "unit": "版本",
                "role": "config",
                "original": ct[max(0,m.start()-20):m.end()+20],
                "section": section, "source": "usecase_action_constraint"
            })

    usecase_info = {
        "has_action_constraints": len(constraint_texts) > 0,
        "constraint_count": len(all_constraints),
        "constraint_texts": constraint_texts[:3],
    }
    return all_constraints, usecase_info

# --- L3-Fix5: req_id位置 ---
def extract_req_ids_with_location(content_list, sections):
    req_id_locations = defaultdict(list)
    current_section = ""
    for item in content_list:
        if not isinstance(item, dict): continue
        item_type = item.get("type", "text")
        if item_type == "text":
            text = item.get("text", "")
            text_level = item.get("text_level", 0)
            if text_level > 0:
                m = SECTION_RE.match(text.strip())
                if m: current_section = m.group(1)
                for rid_m in REQ_ID_RE.finditer(text):
                    rid = rid_m.group(0)
                    req_id_locations[rid].append({
                        "section": current_section, "location": "section_title",
                        "context": text.strip()[:80]
                    })
                continue
            for rid_m in REQ_ID_RE.finditer(text):
                rid = rid_m.group(0)
                req_id_locations[rid].append({
                    "section": current_section, "location": "text",
                    "context": text[max(0,rid_m.start()-20):rid_m.end()+20].strip()
                })
        elif item_type == "table":
            table_body = item.get("table_body", "")
            caption = ' '.join(item.get("table_caption", []))
            rows = parse_html_table(table_body)
            headers = rows[0] if rows else []
            headers_text = ' '.join(str(h) for h in headers)
            table_loc = "table"
            if any(kw in caption + headers_text for kw in ['合格性方法', '本文档章节号', '合格性级别']):
                table_loc = "qualification_table"
            elif any(kw in caption for kw in ['追踪', '跟踪', '任务书']):
                table_loc = "traceability_table"
            elif any(kw in headers_text for kw in ['功能名称', '子功能', '功能标识']):
                table_loc = "capability_table"
            elif any(kw in caption + headers_text for kw in ['接口', '信号']):
                table_loc = "interface_table"
            elif any(kw in caption + headers_text for kw in ['文档编号', '修订', '版本号']):
                table_loc = "reference_table"
            elif 'Use Case' in headers_text or 'Actor' in headers_text:
                table_loc = "usecase_table"
            full_text = caption + " " + table_body
            for rid_m in REQ_ID_RE.finditer(full_text):
                rid = rid_m.group(0)
                ctx = re.sub(r'<[^>]+>', '', full_text[max(0,rid_m.start()-20):rid_m.end()+20].strip()[:80])
                req_id_locations[rid].append({
                    "section": current_section, "location": table_loc, "context": ctx
                })
    result = []
    for rid, locations in sorted(req_id_locations.items()):
        result.append({"id": rid, "locations": locations, "location_count": len(locations)})
    return result

# --- L3-Fix6: 版本号过滤 ---
VALID_VERSION_PATTERNS = {
    '达梦': re.compile(r'^V?\d+(?:\.\d+)*$'),
    '银河麒麟': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'WPS': re.compile(r'^V?\d+(?:\.\d+)*$', re.IGNORECASE),
    'wps': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'Qt': re.compile(r'^\d+\.\d+(?:\.\d+)?$'),
    'Oracle': re.compile(r'^\d+[cg]$', re.IGNORECASE),
    'MySQL': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'Linux': re.compile(r'^\d+\.\d+\.?\d*$'),
    '内核': re.compile(r'^\d+\.\d+\.?\d*$'),
    'Windows': re.compile(r'^(?:XP|7|10|11|Vista|Server\s*\d+)$', re.IGNORECASE),
    'GCC': re.compile(r'^\d+\.\d+\.?\d*$'),
    'CentOS': re.compile(r'^\d+(?:\.\d+)?$'),
    'Ubuntu': re.compile(r'^\d+\.\d+$'),
    'Redis': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'Nginx': re.compile(r'^\d+\.\d+(?:\.\d+)?$'),
    'nodejs': re.compile(r'^V?\d+(?:\.\d+)*$', re.IGNORECASE),
}

def is_valid_version(software, version, original):
    if version.isdigit() and len(version) <= 2:
        if software == 'Windows' and version in ('7', '10', '11', 'XP'):
            idx = original.find(version)
            if idx > 0:
                before = original[:idx]
                if '/' in before[-15:] and 'Windows' in before[-15:]:
                    return False
            return True
        if software.lower() not in ('windows',):
            return False
    pattern = VALID_VERSION_PATTERNS.get(software)
    if pattern and not pattern.match(version):
        return False
    idx = original.find(version)
    if idx > 0:
        before = original[:idx]
        if re.search(r'\d+\s*$', before) and software not in before[-20:]:
            return False
    return True

def fix_versions(versions):
    return [v for v in versions if is_valid_version(v.get('software',''), v.get('version',''), v.get('original',''))]

# --- L3-Fix7: caption统一 ---
CAPTION_RE = re.compile(r'(图|表)\s*(\d+)\s*[.、:：]?\s*(.*)')

def normalize_caption(caption):
    if not caption: return ''
    caption = re.sub(r'\*+', '', caption.strip())
    matches = list(CAPTION_RE.finditer(caption))
    if matches:
        m = matches[-1]
        prefix = m.group(1)
        num = m.group(2)
        title = m.group(3).strip()
        return f"{prefix}{num} {title}" if title else f"{prefix}{num}"
    return caption

def fix_captions(data):
    for sec_id, sd in data['sections'].items():
        for table in sd.get('tables', []):
            if table.get('caption'):
                table['caption'] = normalize_caption(table['caption'])
        for img in sd.get('images', []):
            if img.get('caption'):
                img['caption'] = normalize_caption(img['caption'])
    return data

# --- L3主函数 ---
def run_l3(data: dict, content_list: list, office_dir: Path, output_dir: Path) -> dict:
    """L3: 7项修复"""
    doc_name = data['doc_name']
    fix_log = {"doc": doc_name[:30], "fixes": []}

    # Fix1: 图片
    output_img_dir = output_dir / "images" / doc_name[:20]
    new_paths = fix_images(doc_name, content_list, office_dir, output_img_dir)
    img_idx = 0
    unique_paths = set()
    for sec_id, sd in data['sections'].items():
        for img in sd.get('images', []):
            if img_idx < len(new_paths):
                img['path'] = new_paths[img_idx]
                img_idx += 1
            if img.get('path'): unique_paths.add(img['path'])
    fix_log["fixes"].append({
        "fix": "图片EMF→PNG", "status": "修复" if new_paths else "跳过",
        "detail": f"{len(new_paths)}张, 唯一路径{len(unique_paths)}/{img_idx}"
    })

    # Fix4: 用例表约束
    usecase_constraints = []
    usecase_count = 0
    current_section = ""
    for item in content_list:
        if not isinstance(item, dict): continue
        if item.get('type') == 'text':
            text_level = item.get('text_level', 0)
            if text_level > 0:
                m = SECTION_RE.match(item.get('text', '').strip())
                if m: current_section = m.group(1)
        elif item.get('type') == 'table':
            table_body = item.get('table_body', '')
            caption = ' '.join(item.get('table_caption', []))
            cs, usecase_info = extract_usecase_constraints(table_body, caption, current_section)
            if cs:
                usecase_constraints.extend(cs)
                usecase_count += 1
                for sec_id, sd in data['sections'].items():
                    if sec_id == current_section:
                        for t in sd.get('tables', []):
                            if not t.get('usecase_info'):
                                t['usecase_info'] = usecase_info
                                break
    fix_log["fixes"].append({
        "fix": "用例表约束", "status": "修复" if usecase_constraints else "无约束",
        "detail": f"{usecase_count}个用例表, {len(usecase_constraints)}条约束"
    })

    # Fix2+3: 去重+unit
    all_constraints = data.get('all_constraints', [])
    old_count = len(all_constraints)
    all_constraints.extend(usecase_constraints)
    all_constraints = fix_constraint_units(all_constraints)
    all_constraints = dedup_constraints(all_constraints)
    data['all_constraints'] = all_constraints
    for sec_id, sd in data['sections'].items():
        sd['constraints'] = dedup_constraints(fix_constraint_units(sd.get('constraints', [])))
    unit_cover = sum(1 for c in all_constraints if c.get('unit'))
    fix_log["fixes"].append({
        "fix": "约束去重", "status": "修复",
        "detail": f"{old_count}+{len(usecase_constraints)} → {len(all_constraints)}"
    })
    fix_log["fixes"].append({
        "fix": "unit补充", "status": "修复",
        "detail": f"{unit_cover}/{len(all_constraints)} ({unit_cover/len(all_constraints)*100:.1f}%)"
    })

    # Fix5: req_id位置
    req_id_with_loc = extract_req_ids_with_location(content_list, data['sections'])
    data['all_req_ids'] = req_id_with_loc
    fix_log["fixes"].append({
        "fix": "req_id位置", "status": "修复",
        "detail": f"{len(req_id_with_loc)}个ID, {sum(r['location_count'] for r in req_id_with_loc)}个位置"
    })

    # Fix6: 版本号过滤
    old_ver = len(data.get('all_versions', []))
    data['all_versions'] = fix_versions(data.get('all_versions', []))
    for sec_id, sd in data['sections'].items():
        sd['versions'] = fix_versions(sd.get('versions', []))
    fix_log["fixes"].append({
        "fix": "版本号过滤", "status": "修复" if len(data['all_versions']) < old_ver else "无噪声",
        "detail": f"{old_ver} → {len(data['all_versions'])}"
    })

    # Fix7: caption统一
    data = fix_captions(data)
    fix_log["fixes"].append({"fix": "caption统一", "status": "修复", "detail": "图N 标题 / 表N 标题"})

    # 更新统计
    data['statistics']['constraints'] = len(all_constraints)
    data['statistics']['versions'] = len(data['all_versions'])
    data['statistics']['req_ids'] = len(req_id_with_loc)
    data['parse_date'] = datetime.now().isoformat()
    data['source'] = "L1+L2+L3 pipeline (3层完整流水线)"
    data['fix_log'] = fix_log

    # 移除内部字段
    data.pop('_content_list', None)

    return data


# ============================================================
# L4: P0+P1深度修复
# ============================================================

# --- L4-Fix8: 第4章拆分子节(P0-1) ---
def split_chapter4(data: dict, content_list: list) -> dict:
    """把第4章(合格性规定)按子表/子节拆分为4.1,4.2..."""
    sections = data['sections']
    if '4' not in sections:
        return data
    
    ch4 = sections['4']
    ch4_tables = ch4.get('tables', [])
    if not ch4_tables:
        return data
    
    # 按合格性表的行分组拆分
    # GJB标准第4章通常有 4.1 合格性方法, 4.2 合格性级别 等
    # 从content_list中找第4章下的标题
    ch4_subsections = {}
    in_ch4 = False
    for item in content_list:
        if not isinstance(item, dict): continue
        if item.get('type') == 'text':
            text = item.get('text', '').strip()
            text_level = item.get('text_level', 0)
            if text_level > 0:
                m = SECTION_RE.match(text)
                if m:
                    sec_num = m.group(1)
                    if sec_num == '4':
                        in_ch4 = True
                    elif sec_num.startswith('4.'):
                        if in_ch4:
                            ch4_subsections[sec_num] = {
                                "title": m.group(2).strip(),
                                "text": "", "tables": [], "images": [],
                                "constraints": [], "versions": []
                            }
                    elif in_ch4:
                        in_ch4 = False  # 离开第4章
    
    # 如果content_list中没有4.x子标题,从追踪表引用的章节号推断
    if not ch4_subsections:
        # 从追踪表的"本文档章节号"列找4.x引用
        ch4_refs = set()
        for sec_id, sd in sections.items():
            for table in sd.get('tables', []):
                if table.get('type') == 'traceability':
                    for row in table.get('rows', []):
                        for cell in row:
                            refs = re.findall(r'\b(4\.\d+)\b', str(cell))
                            ch4_refs.update(refs)
        
        # 为每个4.x引用创建空section
        for ref in sorted(ch4_refs):
            ch4_subsections[ref] = {
                "title": f"合格性规定子节{ref}",
                "text": "", "tables": [], "images": [],
                "constraints": [], "versions": []
            }
    
    # 如果有子节,把第4章的表格分配到子节
    if ch4_subsections:
        # 把合格性表分配到4.1(最常见的结构)
        if '4.1' in ch4_subsections and ch4_tables:
            ch4_subsections['4.1']['tables'] = ch4_tables
            ch4_subsections['4.1']['text'] = ch4.get('text', '')
        
        # 删除原section 4,添加子节
        del sections['4']
        for k, v in ch4_subsections.items():
            sections[k] = v
    
    return data

# --- L4-Fix9: 版本号同源校验(P0-2) ---
VERSION_WHITELIST = {
    '达梦': ['V7.6', 'V7.2', 'V8', 'V8.1.1', 'V6.0', 'V7.1.5'],
    '银河麒麟': ['V4.0.2', 'V10', 'V5', 'V4.0', 'V10.1'],
    'WPS': ['V10.1', 'V11', 'V2019'],
    'wps': ['V10.1', 'V11'],
    'Qt': ['5.9.6', '5.9.4', '5.6.0', '5.12.0', '5.15.0'],
    'Windows': ['7', '10', '11', 'XP'],
    'Redis': ['V5.0', 'V6.0', 'V6.2', 'V7.0'],
    'Nginx': ['1.18.0', '1.20.0', '1.22.0'],
    'Oracle': ['11g', '12c', '19c', '21c'],
    'MySQL': ['V5.7', 'V8.0', 'V5.6'],
}

def is_valid_version_v2(software, version, original):
    """升级版版本号校验: 格式+白名单+同源校验"""
    sw = software.strip()
    ver = version.strip()
    
    # 1. 白名单校验
    whitelist = VERSION_WHITELIST.get(sw, [])
    if whitelist:
        if ver in whitelist:
            return True
        # 不在白名单中,进一步检查
        if sw in ('达梦', '银河麒麟', 'WPS', 'wps'):
            # 这些软件的版本应该在白名单中,不在的可能是噪声
            # 但允许V开头的新版本
            if ver.startswith('V') and re.match(r'^V\d+(?:\.\d+)+$', ver):
                return True  # 可能是新版本,保留
            # 检查是否是行号(数字紧跟软件名后无V前缀)
            if not ver.startswith('V') and not ver.startswith('v'):
                return False  # 达梦/WPS/银河麒麟的版本应该有V前缀
    
    # 2. 格式校验
    pattern = VALID_VERSION_PATTERNS.get(sw)
    if pattern and not pattern.match(ver):
        return False
    
    # 3. 同源校验: software和version必须在原文中相邻(同单元格)
    # 检查original中software和version之间是否有其他数字(行号)
    idx_sw = original.find(sw)
    idx_ver = original.find(ver)
    if idx_sw >= 0 and idx_ver >= 0 and idx_ver > idx_sw:
        between = original[idx_sw + len(sw):idx_ver]
        # 如果中间有2位以上数字,可能是行号
        nums_in_between = re.findall(r'\d+', between)
        if nums_in_between:
            # 检查是否是表格行号(如 "3 达梦 V7.6" 中的3)
            if len(nums_in_between) >= 1 and int(nums_in_between[0]) < 100:
                # 可能是行号
                between_clean = re.sub(r'\d+', '', between).strip()
                if len(between_clean) < 3:  # 行号和软件名之间几乎无文字
                    return False
    
    # 4. Windows双版本拆分检查
    if sw == 'Windows' and ver in ('7', '10', '11', 'XP'):
        if idx_ver > 0:
            before = original[:idx_ver]
            if '/' in before[-15:] and 'Windows' in before[-15:]:
                return False
    
    # 5. 单数字版本(非Windows)通常是行号
    if ver.isdigit() and len(ver) <= 2 and sw not in ('Windows',):
        return False
    
    return True

def fix_versions_v2(versions):
    return [v for v in versions 
            if is_valid_version_v2(v.get('software',''), v.get('version',''), v.get('original',''))]

# --- L4-Fix10: 约束声明层去重(P0-3) + param清洗(P1) ---
PARAM_PREFIX_NOISE = re.compile(r'^(的|应|为|不|小于|大于|等于|要|需|其|该|本)+')
PARAM_SUFFIX_NOISE = re.compile(r'(的|应|为|不|小于|大于|等于|要|需)+$')

def clean_param_name(param):
    """清洗约束参数名: 去除首尾助词"""
    if not param:
        return param
    # 迭代清洗(处理"的的最大名录"→"最大名录")
    prev = param
    while True:
        param = PARAM_PREFIX_NOISE.sub('', param)
        param = PARAM_SUFFIX_NOISE.sub('', param)
        if param == prev:
            break
        prev = param
    # 特殊处理: "录文件的节点数应" → "名录文件的节点数"
    if param.startswith('录文件') and len(param) > 3:
        param = '名' + param
    return param.strip()

def dedup_constraints_v2(constraints):
    """声明层去重: 同param+op+value+unit跨节折叠为1声明+多位置"""
    declarations = {}  # key → {constraint, locations}
    
    for c in constraints:
        # 清洗param
        c['param'] = clean_param_name(c.get('param', ''))
        
        key = (c.get('param',''), c.get('operator',''), str(c.get('value','')),
               c.get('unit',''), c.get('role',''))
        
        if key not in declarations:
            declarations[key] = {
                "constraint": c,
                "locations": [{"section": c.get('section',''), "source": c.get('source','text'),
                              "original": c.get('original','')}]
            }
        else:
            declarations[key]["locations"].append({
                "section": c.get('section',''), "source": c.get('source','text'),
                "original": c.get('original','')
            })
    
    # 转为列表: 1声明+多位置
    result = []
    for decl in declarations.values():
        c = dict(decl["constraint"])
        c["locations"] = decl["locations"]
        c["location_count"] = len(decl["locations"])
        # 如果只有1个位置,不添加locations字段(保持简洁)
        if c["location_count"] == 1:
            c.pop("locations", None)
            c.pop("location_count", None)
        result.append(c)
    
    return result

# --- L4-Fix11: doc02编号映射表(P1-1) ---
DOC02_NUMBERING_MAP = {
    '1.1': '1.1', '1.2': '1.2', '1.3': '3.1', '1.4': '3.2',
    '1.5': '3.3', '1.6': '3.4', '1.7': '3.5', '1.8': '3.2',
    '1.9': '3.6', '1.10': '3.7', '1.11': '3.8', '1.12': '3.9',
    '1.13': '3.7', '1.14': '3.8', '1.15': '3.9',
    '1.16': '3.10', '1.17': '3.11', '1.18': '3.12',
    '1.19': '3.13', '1.20': '3.14', '1.21': '3.15',
    '1.22': '3.16', '1.23': '3.17', '1.24': '3.18',
    '1.25': '3.19', '1.26': '4', '1.27': '5', '1.28': '6',
}

def add_numbering_map(data):
    """为doc02添加编号映射表到元数据"""
    if data['doc_name'].startswith('02'):
        data['numbering_map'] = DOC02_NUMBERING_MAP
        data['numbering_type'] = 'flat_1x'
    else:
        data['numbering_type'] = 'standard_3x'
    return data

# --- L4-Fix12: 章节双基准(P1-2) ---
GJB_TEXT_BASELINE = {
    '3.1': '要求的状态与方式', '3.2': '能力需求', '3.3': '外部接口',
    '3.4': '内部接口', '3.5': '人机交互', '3.6': '内部数据',
    '3.7': '适应性需求', '3.8': '安全性需求', '3.9': '保密性需求',
    '3.10': 'CSCI环境需求', '3.11': '计算机资源需求',
    '3.12': '软件质量因素', '3.13': '设计约束', '3.14': '人员需求',
    '3.15': '培训需求', '3.16': '软件保障', '3.17': '其他需求',
    '3.18': '验收交付',
}

DE_FACTO_BASELINE = {
    '3.1': '要求的状态与方式', '3.2': '能力需求', '3.3': '外部接口',
    '3.4': '内部接口', '3.5': '人机交互', '3.6': '内部数据',
    '3.7': '安全性需求', '3.8': '保密性需求', '3.9': 'CSCI环境需求',
    '3.10': '计算机资源需求', '3.11': '软件质量因素',
    '3.12': '设计约束', '3.13': '人员需求', '3.14': '培训需求',
    '3.15': '软件保障', '3.16': '其他需求', '3.17': '验收交付',
}

def add_baselines(data):
    """添加章节双基准到元数据"""
    data['baselines'] = {
        'gjb_text': GJB_TEXT_BASELINE,
        'de_facto': DE_FACTO_BASELINE,
        'note': '14份文档遵循de_facto基准(3.7=安全性,无适应性);doc01顺序颠倒;doc11缺3.8;doc02使用1.x扁平编号'
    }
    return data

# --- L4-Fix13: 表格统一IR(P1-3) ---
def unify_table_ir(data):
    """统一合格性表/追踪表为中间表示"""
    for sec_id, sd in data['sections'].items():
        for table in sd.get('tables', []):
            ttype = table.get('type', '')
            if ttype == 'qualification':
                table['ir'] = _qual_table_ir(table)
            elif ttype == 'traceability':
                table['ir'] = _trace_table_ir(table)
            # 修复caption合并(一个caption含两个表号)
            caption = table.get('caption', '')
            if caption and caption.count('表') > 1:
                # 取最后一个表号
                matches = list(CAPTION_RE.finditer(caption))
                if matches:
                    m = matches[-1]
                    table['caption'] = normalize_caption(f"{m.group(1)}{m.group(2)} {m.group(3)}")
    return data

def _qual_table_ir(table):
    """合格性表统一IR"""
    headers = table.get('headers', [])
    rows = table.get('rows', [])
    # 4列: [需求名称/标识, 本文档章节号, 合格性方法, 合格性级别]
    # 5列: [序号, 需求名称/标识, 合格性方法, 测试类, 合格性级别]
    ir = {"type": "qualification", "column_count": len(headers)}
    if len(headers) == 4:
        ir["schema"] = "4col_standard"
        ir["columns"] = ["req_id_name", "section_ref", "method", "level"]
    elif len(headers) == 5:
        ir["schema"] = "5col_with_testtype"
        ir["columns"] = ["seq", "req_id_name", "method", "test_type", "level"]
    else:
        ir["schema"] = "unknown"
        ir["columns"] = headers
    ir["row_count"] = len(rows)
    return ir

def _trace_table_ir(table):
    """追踪表统一IR"""
    headers = table.get('headers', [])
    rows = table.get('rows', [])
    ir = {"type": "traceability", "column_count": len(headers)}
    if len(headers) == 4:
        ir["schema"] = "4col_separate"
        ir["columns"] = ["seq", "upstream_ref", "downstream_ref", "remark"]
    elif len(headers) == 5:
        ir["schema"] = "5col_merged"
        ir["columns"] = ["upstream_doc", "upstream_section", "downstream_doc", "downstream_section", "remark"]
    else:
        ir["schema"] = "unknown"
        ir["columns"] = headers
    ir["row_count"] = len(rows)
    # 检测正逆向
    caption = table.get('caption', '')
    if '正向' in caption:
        ir["direction"] = "forward"
    elif '逆向' in caption:
        ir["direction"] = "reverse"
    else:
        ir["direction"] = "unknown"
    return ir

# --- L4主函数 ---
def run_l4(data: dict, content_list: list) -> dict:
    """L4: P0+P1深度修复"""
    doc_name = data['doc_name']
    fix_log = data.get('fix_log', {"doc": doc_name[:30], "fixes": []})
    
    # Fix8: 第4章拆分(P0-1)
    old_sections = len(data['sections'])
    data = split_chapter4(data, content_list)
    new_sections = len(data['sections'])
    ch4_subcount = sum(1 for s in data['sections'] if s.startswith('4.'))
    fix_log["fixes"].append({
        "fix": "第4章拆分(P0-1)", "status": "修复" if ch4_subcount > 0 else "跳过",
        "detail": f"新增{ch4_subcount}个4.x子节, 总章节{old_sections}→{new_sections}"
    })
    
    # Fix9: 版本号同源校验(P0-2)
    old_ver = len(data.get('all_versions', []))
    data['all_versions'] = fix_versions_v2(data.get('all_versions', []))
    for sec_id, sd in data['sections'].items():
        sd['versions'] = fix_versions_v2(sd.get('versions', []))
    new_ver = len(data['all_versions'])
    fix_log["fixes"].append({
        "fix": "版本号同源校验(P0-2)", "status": "修复" if new_ver < old_ver else "无噪声",
        "detail": f"{old_ver} → {new_ver} (过滤{old_ver-new_ver}条)"
    })
    
    # Fix10: 约束声明层去重+param清洗(P0-3)
    old_c = len(data.get('all_constraints', []))
    data['all_constraints'] = dedup_constraints_v2(data.get('all_constraints', []))
    for sec_id, sd in data['sections'].items():
        sd['constraints'] = dedup_constraints_v2(sd.get('constraints', []))
    new_c = len(data['all_constraints'])
    # 统计样板折叠
    folded = sum(1 for c in data['all_constraints'] if c.get('location_count', 1) > 1)
    fix_log["fixes"].append({
        "fix": "约束声明层去重(P0-3)", "status": "修复",
        "detail": f"{old_c} → {new_c} (折叠{folded}组样板, param清洗{old_c-new_c+folded}条)"
    })
    
    # Fix11: doc02编号映射(P1-1)
    data = add_numbering_map(data)
    fix_log["fixes"].append({
        "fix": "编号映射(P1-1)", "status": "修复",
        "detail": f"编号类型: {data['numbering_type']}" + 
                  (f", 映射表{len(DOC02_NUMBERING_MAP)}项" if data['numbering_type'] == 'flat_1x' else "")
    })
    
    # Fix12: 章节双基准(P1-2)
    data = add_baselines(data)
    fix_log["fixes"].append({
        "fix": "章节双基准(P1-2)", "status": "修复",
        "detail": "GJB-text(3.7=适应性) + de-facto(3.7=安全性)"
    })
    
    # Fix13: 表格统一IR(P1-3)
    data = unify_table_ir(data)
    qual_count = sum(1 for sd in data['sections'].values() 
                     for t in sd.get('tables', []) if t.get('ir', {}).get('type') == 'qualification')
    trace_count = sum(1 for sd in data['sections'].values() 
                      for t in sd.get('tables', []) if t.get('ir', {}).get('type') == 'traceability')
    fix_log["fixes"].append({
        "fix": "表格统一IR(P1-3)", "status": "修复",
        "detail": f"合格性表{qual_count}个, 追踪表{trace_count}个"
    })
    
    # 更新统计
    data['statistics']['sections'] = len(data['sections'])
    data['statistics']['constraints'] = len(data['all_constraints'])
    data['statistics']['versions'] = len(data['all_versions'])
    data['source'] = "L1+L2+L3+L4 pipeline (4层完整流水线)"
    data['fix_log'] = fix_log
    
    return data


# ============================================================
# 主流水线
# ============================================================

def process_document(doc_path: Path, output_dir: Path, skip_l1=False, skip_l2=False):
    """处理单个文档"""
    doc_name = doc_path.stem
    print(f"\n{'='*60}")
    print(f"处理: {doc_name}")
    print(f"{'='*60}")

    # L1
    if skip_l1:
        # 尝试找到已有的MinerU输出
        mineru_dir = BASE / "data/gjb_438c/mineru_standard" / doc_name
        office_dir = mineru_dir / "office" if mineru_dir.exists() else None
        if not office_dir or not office_dir.exists():
            print(f"  [L1] 跳过但未找到已有MinerU输出")
            return None
        print(f"  [L1] 跳过(使用已有输出)")
    else:
        office_dir = run_l1(doc_path, output_dir / "mineru_standard")
        if not office_dir:
            return None

    # L2
    if skip_l2:
        # 尝试找到已有的结构化JSON
        structured_dir = BASE / "data/gjb_438c/mineru_structured"
        old_json = structured_dir / f"{doc_name}_structured.json"
        if old_json.exists():
            data = json.loads(old_json.read_text(encoding="utf-8"))
            content_list = json.loads((office_dir / f"{doc_name}_content_list.json").read_text(encoding="utf-8"))
            print(f"  [L2] 跳过(使用已有结构化JSON)")
        else:
            print(f"  [L2] 跳过但未找到已有JSON,运行L2")
            data = run_l2(doc_name, office_dir)
            content_list = data.pop('_content_list', [])
    else:
        data = run_l2(doc_name, office_dir)
        content_list = data.get('_content_list', [])
        if "error" in data:
            print(f"  [L2] ✗ {data['error']}")
            return None
        s = data['statistics']
        print(f"  [L2] ✓ 章:{s['sections']} 表:{s['tables']} 图:{s['images']} "
              f"约束:{s['constraints']} 版本:{s['versions']} ID:{s['req_ids']}")

    # L3: 7项基础修复
    data = run_l3(data, content_list, office_dir, output_dir)
    for fix in data['fix_log']['fixes']:
        icon = "✓" if "修复" in fix['status'] else "○"
        print(f"  [L3] {icon} {fix['fix']}: {fix['detail']}")

    # L4: P0+P1深度修复
    data = run_l4(data, content_list)
    for fix in data['fix_log']['fixes']:
        if 'P0' in fix['fix'] or 'P1' in fix['fix']:
            icon = "✓" if "修复" in fix['status'] else "○"
            print(f"  [L4] {icon} {fix['fix']}: {fix['detail']}")

    # 保存
    structured_output = output_dir / f"{doc_name}_structured.json"
    structured_output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [输出] {structured_output}")
    return data


def main():
    parser = argparse.ArgumentParser(description="SRS数据处理流水线")
    parser.add_argument("--input", required=True, help="输入.doc文件或目录")
    parser.add_argument("--output", default="data/gjb_438c/processed", help="输出目录")
    parser.add_argument("--skip-l1", action="store_true", help="跳过L1(使用已有MinerU输出)")
    parser.add_argument("--skip-l2", action="store_true", help="跳过L2(使用已有结构化JSON)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 收集.doc文件
    if input_path.is_file():
        doc_files = [input_path]
    elif input_path.is_dir():
        doc_files = sorted(list(input_path.glob("*.doc")))
    else:
        print(f"输入路径不存在: {input_path}")
        sys.exit(1)

    print(f"{'='*60}")
    print(f"SRS数据处理流水线")
    print(f"  输入: {input_path}")
    print(f"  输出: {output_dir}")
    print(f"  文档数: {len(doc_files)}")
    print(f"  跳过L1: {args.skip_l1}, 跳过L2: {args.skip_l2}")
    print(f"{'='*60}")

    all_results = []
    for doc_path in doc_files:
        result = process_document(doc_path, output_dir, args.skip_l1, args.skip_l2)
        if result:
            all_results.append(result)

    # 汇总
    print(f"\n{'='*60}")
    print(f"流水线完成: {len(all_results)}/{len(doc_files)}份文档")
    total_s = sum(r['statistics']['sections'] for r in all_results)
    total_t = sum(r['statistics']['tables'] for r in all_results)
    total_i = sum(r['statistics']['images'] for r in all_results)
    total_c = sum(r['statistics']['constraints'] for r in all_results)
    total_v = sum(r['statistics']['versions'] for r in all_results)
    total_r = sum(r['statistics']['req_ids'] for r in all_results)
    print(f"  章节:{total_s} 表格:{total_t} 图片:{total_i} "
          f"约束:{total_c} 版本:{total_v} ID:{total_r}")

    # 保存汇总
    summary = {
        "pipeline_date": datetime.now().isoformat(),
        "pipeline": "L1(MinerU)+L2(结构化)+L3(7项修复)",
        "total_docs": len(all_results),
        "totals": {"sections":total_s,"tables":total_t,"images":total_i,
                   "constraints":total_c,"versions":total_v,"req_ids":total_r},
        "docs": [{"doc_name":r['doc_name'][:30],"stats":r['statistics'],
                  "fix_log":r.get('fix_log',{})} for r in all_results],
    }
    (output_dir / "_pipeline_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  汇总: {output_dir / '_pipeline_summary.json'}")


if __name__ == "__main__":
    main()
