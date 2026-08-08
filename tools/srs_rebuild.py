#!/usr/bin/env python3
"""
SRS数据重建脚本：修复merge + 干净L2 + 统计验证
=============================================
1. 修复merge_mineru_outputs的图片路径(含文档子目录)和page_idx(按batch偏移)
2. 重新合并16份正确解析的content_list
3. 基于修复后的content_list运行干净L2(含全部修复)
4. 生成正确统计+质量验证

用法: python3 tools/srs_rebuild.py
"""
import json
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
CORRECT_DIR = BASE / "data/gjb_438c/mineru_correct"
OUTPUT_DIR = BASE / "data/gjb_438c/structured"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 修复后的TableHTMLParser（支持colspan/rowspan展开）
# ============================================================
class TableHTMLParser(HTMLParser):
    """支持colspan/rowspan的HTML表格解析器"""
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False
        self.cell_attrs = {}
        self.pending_rowspans = {}

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

            for i in range(colspan):
                col_idx = len(self.current_row)
                while col_idx in self.pending_rowspans:
                    text, remaining = self.pending_rowspans[col_idx]
                    self.current_row.append(text)
                    if remaining > 1:
                        self.pending_rowspans[col_idx] = (text, remaining - 1)
                    else:
                        del self.pending_rowspans[col_idx]
                    col_idx = len(self.current_row)

                if i == 0:
                    self.current_row.append(cell_text)
                else:
                    self.current_row.append('')

                if rowspan > 1:
                    actual_col = len(self.current_row) - 1
                    self.pending_rowspans[actual_col] = (cell_text, rowspan - 1)

            self.in_cell = False
        elif tag == 'tr' and self.current_row:
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


def parse_html_table(html):
    parser = TableHTMLParser()
    parser.feed(html)
    return parser.rows


# ============================================================
# 表格分类（修正版：解决3个重大分类错误）
# ============================================================
def classify_table(caption, headers, section_id=""):
    c = (caption + ' '.join(str(h) for h in headers)).lower()
    headers_text = ' '.join(str(h) for h in headers)
    
    # 1. usecase: 表头含Use Case/Actor
    if 'use case' in c or 'actor' in c:
        return 'usecase'
    
    # 2. usecase_fragment: 3.2.x下含主事件流/异常流/前置条件/后置条件但无Use Case表头
    if section_id and section_id.startswith('3.2'):
        if any(kw in c for kw in ['主事件流', '异常流', '前置条件', '后置条件']):
            return 'usecase_fragment'
    
    # 3. data_spec: 表头含数据集/数据元素 (必须在interface之前检查)
    if any(kw in c for kw in ['数据集名称', '数据组成', '数据元素名称', '数据元素标识', '数据项']):
        return 'data_spec'
    
    # 4. interface: 表头含接口关键词 或 在3.3/3.4节下
    if any(kw in c for kw in ['接口名称', '接口需求', '接口描述', '接口类型', '接口标识', '接口唯一标识']):
        return 'interface'
    if section_id and (section_id.startswith('3.3') or section_id.startswith('3.4')):
        # 3.3/3.4节下非data_spec的表归为interface
        return 'interface'
    
    # 5. traceability: caption含追踪/跟踪 且 在第5章 (严格限制)
    if any(kw in caption for kw in ['追踪', '跟踪', '任务书']):
        if section_id and section_id.startswith('5'):
            return 'traceability'
        # 第5章下headers含追踪也算
    if section_id and section_id.startswith('5'):
        if any(kw in c for kw in ['追踪', '跟踪', '任务书']):
            return 'traceability'
    
    # 6. capability: 表头含功能名称/功能标识/Usecase名称/项目唯一标识符/能力标识
    if any(kw in c for kw in ['功能名称', '功能标识', 'usecase名称', '项目唯一标识符', '能力标识', '子功能']):
        return 'capability'
    # 3.2.x下含"标识"的表(能力标识表)
    if section_id and section_id.startswith('3.2'):
        if '标识' in c and ('序号' in c or '需求描述' in c or '需求重用' in c):
            return 'capability'
    
    # 7. qualification: 第4章 或 caption含合格性
    if section_id and section_id == '4':
        return 'qualification'
    if any(kw in c for kw in ['合格性方法', '本文档章节号', '合格性级别', '合格性规定']):
        return 'qualification'
    
    # 8. reference: 第2章 或 表头含文档编号
    if section_id and section_id == '2':
        return 'reference'
    if any(kw in c for kw in ['文档编号', '修订版本', '编写单位']):
        return 'reference'
    
    # 9. other: 兜底
    return 'other'


# ============================================================
# 约束提取
# ============================================================
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

PARAM_PREFIX_NOISE = re.compile(r'^(的|应|为|不|小于|大于|等于|要|需|其|该|本)+')
PARAM_SUFFIX_NOISE = re.compile(r'(的|应|为|不|小于|大于|等于|要|需)+$')

def clean_param_name(param):
    if not param: return param
    prev = param
    while True:
        param = PARAM_PREFIX_NOISE.sub('', param)
        param = PARAM_SUFFIX_NOISE.sub('', param)
        if param == prev: break
        prev = param
    if param.startswith('录文件') and len(param) > 3:
        param = '名' + param
    return param.strip()

def _extract_param_name(before_text):
    parts = re.split(r'[，。；：、\s：:;,\n]+', before_text.strip())
    for part in reversed(parts):
        part = part.strip()
        if not part: continue
        cn_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', part)
        if cn_m: return cn_m.group(1)
        if re.match(r'^[\u4e00-\u9fa5]{2,8}$', part): return part
    return before_text[-8:].strip()

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

def extract_constraints(text, section, source="text"):
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


# ============================================================
# unit补充
# ============================================================
UNIT_PATTERNS = [
    (r'条/秒', '条/秒'), (r'次/秒', '次/秒'), (r'笔/秒', '笔/秒'),
    (r'Mpps', 'Mpps'), (r'Tbps', 'Tbps'), (r'Gbps', 'Gbps'), (r'Mbps', 'Mbps'),
    (r'(GB|gb)', 'GB'), (r'(TB|tb)', 'TB'), (r'(MB|mb)', 'MB'), (r'(KB|kb)', 'KB'),
    (r'(GHz|ghz)', 'GHz'), (r'(MHz|mhz)', 'MHz'),
    (r'(ms|毫秒)', 'ms'), (r'(s|秒)(?![\w])', 's'),
    (r'分钟', '分钟'), (r'小时', '小时'), (r'天', '天'), (r'%', '%'),
    (r'核', '核'), (r'个', '个'), (r'块', '块'), (r'台', '台'),
    (r'路', '路'), (r'层', '层'), (r'屏', '屏'), (r'次', '次'), (r'维', '维'),
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


# ============================================================
# 声明层去重
# ============================================================
def dedup_constraints(constraints):
    seen = {}
    result = []
    for c in constraints:
        c['param'] = clean_param_name(c.get('param', ''))
        key = (c.get('param',''), c.get('operator',''), str(c.get('value','')),
               c.get('unit',''), c.get('role',''))
        if key not in seen:
            seen[key] = len(result)
            result.append(c)
        else:
            existing = result[seen[key]]
            if not existing.get('source') and c.get('source'):
                result[seen[key]] = c
    return result


# ============================================================
# 版本号过滤
# ============================================================
VALID_VERSION_PATTERNS = {
    '达梦': re.compile(r'^V?\d+(?:\.\d+)*$'),
    '银河麒麟': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'WPS': re.compile(r'^V?\d+(?:\.\d+)*$', re.IGNORECASE),
    'wps': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'Qt': re.compile(r'^\d+\.\d+(?:\.\d+)?$'),
    'Windows': re.compile(r'^(?:XP|7|10|11|Vista|Server\s*\d+)$', re.IGNORECASE),
    'Redis': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'Nginx': re.compile(r'^\d+\.\d+(?:\.\d+)?$'),
}

def is_valid_version(software, version, original):
    ver = version.strip()
    sw = software.strip()
    if ver.isdigit() and len(ver) <= 2 and sw not in ('Windows',):
        return False
    pattern = VALID_VERSION_PATTERNS.get(sw)
    if pattern and not pattern.match(ver):
        return False
    idx = original.find(ver)
    if idx > 0:
        before = original[:idx]
        if re.search(r'\d+\s*$', before) and sw not in before[-20:]:
            return False
    if sw == 'Windows' and ver in ('7', '10', '11', 'XP'):
        if idx > 0:
            before = original[:idx]
            if '/' in before[-15:] and 'Windows' in before[-15:]:
                return False
    return True

def fix_versions(versions):
    return [v for v in versions if is_valid_version(v.get('software',''), v.get('version',''), v.get('original',''))]


# ============================================================
# caption统一
# ============================================================
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


# ============================================================
# req_id位置提取
# ============================================================
def extract_req_ids_with_location(content_list):
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


# ============================================================
# 用例表约束提取
# ============================================================
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
        cs = extract_constraints(ct, section, source="usecase_action_constraint")
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


# ============================================================
# Step2: 修复merge + Step3: 重新合并
# ============================================================
def rebuild_content_list(doc_dir):
    """重新合并batch输出,修复图片路径和page_idx"""
    doc_name = doc_dir.name
    final_dir = doc_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    
    # 收集所有batch
    batch_outputs = []
    for d in sorted(doc_dir.glob("batch_*")):
        if not (d / "done.flag").exists(): continue
        # 找auto目录下的content_list
        for auto in d.rglob("auto"):
            if auto.is_dir():
                cl_files = [f for f in auto.glob("*content_list.json") if 'v2' not in f.name]
                if cl_files:
                    batch_outputs.append((d, auto, cl_files[0]))
                    break
    
    if not batch_outputs:
        return None
    
    # 合并: 修复page_idx + 图片路径
    all_content = []
    page_offset = 0
    img_counter = 0
    doc_subdir = doc_name[:20]
    final_img_dir = final_dir / "images" / doc_subdir
    final_img_dir.mkdir(parents=True, exist_ok=True)
    
    for batch_idx, (batch_dir, auto_dir, cl_path) in enumerate(batch_outputs):
        cl = json.loads(cl_path.read_text())
        img_dir = auto_dir / "images"
        
        for item in cl:
            if not isinstance(item, dict):
                all_content.append(item)
                continue
            
            # 修复page_idx
            old_page = item.get('page_idx', 0)
            item['page_idx'] = old_page + page_offset
            
            # 修复图片路径
            if item.get('type') == 'image':
                old_path = item.get('img_path', '')
                if old_path:
                    old_full = img_dir / Path(old_path).name if img_dir.exists() else None
                    if old_full and old_full.exists():
                        img_counter += 1
                        new_name = f"img_{img_counter:04d}.jpg"
                        new_full = final_img_dir / new_name
                        shutil.copy(str(old_full), str(new_full))
                        item['img_path'] = f"images/{doc_subdir}/{new_name}"
            
            all_content.append(item)
        
        # 更新page_offset
        if cl:
            max_page = max((item.get('page_idx', 0) for item in cl if isinstance(item, dict)), default=0)
            page_offset += max_page + 1
    
    # 保存
    (final_dir / "content_list.json").write_text(
        json.dumps(all_content, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return all_content


# ============================================================
# Step4: 干净L2
# ============================================================
def run_l2(doc_name, content_list, final_dir):
    """基于修复后的content_list运行干净L2"""
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
            # 目录正文检测(含大量..引导线)
            if text.count('..') > 5:
                continue
            # HTML标签清理
            text = re.sub(r'<[^>]+>', '', text)
            # 检测body text中的章节标题(MinerU可能将短标题误判为level=0)
            # 如doc01的"3.5 分系统内部数据需求/XXX无。"被MinerU标记为level=0
            m = SECTION_RE.match(text.strip())
            if m:
                sec_num = m.group(1)
                sec_title = m.group(2).strip()
                # 只有当该章节号不存在于已有sections时才创建(避免覆盖正常标题)
                if sec_num not in sections and sec_num.count('.') >= 1:
                    current_section = sec_num
                    sections[current_section]["title"] = sec_title
                    req_m = REQ_ID_RE.search(text)
                    if req_m:
                        sections[current_section]["req_id"] = req_m.group(0)
                        all_req_ids.add(req_m.group(0))
                    continue  # 不将标题文本累积为正文
            if current_section:
                sections[current_section]["text"] += text + "\n"
            cs = extract_constraints(text, current_section)
            vs = extract_versions(text, current_section)
            if cs: sections[current_section]["constraints"].extend(cs); all_constraints.extend(cs)
            if vs: sections[current_section]["versions"].extend(vs); all_versions.extend(vs)
            for m in REQ_ID_RE.finditer(text): all_req_ids.add(m.group(0))
        
        elif item_type == "table":
            table_count += 1
            table_body = item.get("table_body", "")
            table_caption = item.get("table_caption", [])
            caption_str = ' '.join(table_caption) if table_caption else ""
            rows = parse_html_table(table_body)
            headers = rows[0] if rows else []
            table_type = classify_table(caption_str, headers, current_section)
            full_text = caption_str + " " + table_body
            cs = extract_constraints(full_text, current_section)
            vs = extract_versions(full_text, current_section)
            if cs: sections[current_section]["constraints"].extend(cs); all_constraints.extend(cs)
            if vs: sections[current_section]["versions"].extend(vs); all_versions.extend(vs)
            for m in REQ_ID_RE.finditer(full_text): all_req_ids.add(m.group(0))
            # 空表格过滤
            if len(table_body) < 30 and not caption_str:
                table_count -= 1
                continue
            # caption统一
            if caption_str:
                caption_str = normalize_caption(caption_str)
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
            if caption_str:
                caption_str = normalize_caption(caption_str)
            sections[current_section]["images"].append({
                "image_id": f"IMG_{image_count}", "path": img_path,
                "caption": caption_str, "section": current_section,
            })
    
    # 用例表约束
    current_section = ""
    usecase_constraints = []
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
            if cs: usecase_constraints.extend(cs)
    
    # 约束: 合并+unit补充+param清洗+声明层去重
    all_constraints.extend(usecase_constraints)
    all_constraints = fix_constraint_units(all_constraints)
    all_constraints = dedup_constraints(all_constraints)
    
    # 版本号过滤
    all_versions = fix_versions(all_versions)
    
    # req_id位置
    req_id_with_loc = extract_req_ids_with_location(content_list)
    
    # section级别约束去重
    for sec_id, sd in sections.items():
        sd['constraints'] = dedup_constraints(fix_constraint_units(sd.get('constraints', [])))
        sd['versions'] = fix_versions(sd.get('versions', []))
    
    return {
        "doc_name": doc_name,
        "parse_date": datetime.now().isoformat(),
        "source": "正确解析(EMF→PNG→PDF→MinerU分批) + 干净L2",
        "statistics": {
            "sections": len(sections), "tables": table_count,
            "images": image_count, "constraints": len(all_constraints),
            "versions": len(all_versions), "req_ids": len(req_id_with_loc),
        },
        "sections": dict(sections),
        "all_constraints": all_constraints,
        "all_versions": all_versions,
        "all_req_ids": req_id_with_loc,
    }


# ============================================================
# 主函数
# ============================================================
def main():
    print("=" * 60)
    print("SRS数据重建: 修复merge + 干净L2 + 统计")
    print("=" * 60)
    
    all_results = []
    
    for doc_dir in sorted(CORRECT_DIR.iterdir()):
        if not doc_dir.is_dir(): continue
        doc_name = doc_dir.name
        print(f"\n[{doc_name[:30]}]")
        
        # Step2+3: 重新合并
        print(f"  重新合并...", end=" ")
        content_list = rebuild_content_list(doc_dir)
        if not content_list:
            print("✗ 无batch输出")
            continue
        
        # 验证图片路径唯一性
        imgs = [i for i in content_list if isinstance(i, dict) and i.get('type') == 'image']
        unique_paths = set(i.get('img_path', '') for i in imgs)
        print(f"{len(content_list)}条, 图片{len(imgs)}张(唯一{len(unique_paths)})")
        
        # Step4: 干净L2
        print(f"  L2提取...", end=" ")
        final_dir = doc_dir / "final"
        data = run_l2(doc_name, content_list, final_dir)
        s = data['statistics']
        print(f"章:{s['sections']} 表:{s['tables']} 图:{s['images']} "
              f"约束:{s['constraints']} 版本:{s['versions']} ID:{s['req_ids']}")
        
        # 保存
        out = OUTPUT_DIR / f"{doc_name}_structured.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        all_results.append(data)
    
    # Step5: 统计汇总
    print(f"\n{'='*60}")
    print("统计汇总")
    print(f"{'='*60}")
    
    total = {'sections':0, 'tables':0, 'images':0, 'constraints':0, 'versions':0, 'req_ids':0}
    for r in all_results:
        for k in total:
            total[k] += r['statistics'][k]
    
    print(f"  文档数: {len(all_results)}")
    print(f"  章节: {total['sections']}")
    print(f"  表格: {total['tables']}")
    print(f"  图片: {total['images']}")
    print(f"  约束: {total['constraints']}")
    print(f"  版本: {total['versions']}")
    print(f"  需求ID: {total['req_ids']}")
    
    # 表格分类统计
    type_dist = Counter()
    for r in all_results:
        for sd in r['sections'].values():
            for t in sd.get('tables', []):
                type_dist[t.get('type', 'unknown')] += 1
    print(f"\n  表格分类:")
    for t, c in type_dist.most_common():
        print(f"    {t}: {c}")
    
    # 图片验证
    total_imgs = 0
    unique_imgs = set()
    missing = 0
    for r in all_results:
        for sd in r['sections'].values():
            for img in sd.get('images', []):
                total_imgs += 1
                path = img.get('path', '')
                if path:
                    unique_imgs.add(path)
                    # 检查文件存在
                    for doc_dir in CORRECT_DIR.iterdir():
                        full = doc_dir / "final" / path
                        if full.exists():
                            break
                    else:
                        missing += 1
    print(f"\n  图片验证:")
    print(f"    总数: {total_imgs}")
    print(f"    唯一路径: {len(unique_imgs)}")
    print(f"    文件不存在: {missing}")
    
    # 约束统计
    op_dist = Counter()
    unit_cover = 0
    param_noise = 0
    for r in all_results:
        for c in r.get('all_constraints', []):
            op_dist[c.get('operator', '')] += 1
            if c.get('unit'): unit_cover += 1
            param = c.get('param', '')
            if param and (param[0] in '的应为不小于大于等于' or param[-1] in '的应'):
                param_noise += 1
    total_c = total['constraints']
    print(f"\n  约束统计:")
    print(f"    算子: {dict(op_dist)}")
    print(f"    unit覆盖: {unit_cover}/{total_c} ({unit_cover/max(total_c,1)*100:.1f}%)")
    print(f"    param噪声: {param_noise}")
    
    # 保存汇总
    summary = {
        "rebuild_date": datetime.now().isoformat(),
        "total_docs": len(all_results),
        "totals": total,
        "table_types": dict(type_dist),
        "image_stats": {"total": total_imgs, "unique": len(unique_imgs), "missing": missing},
        "constraint_stats": {"operators": dict(op_dist), "unit_coverage": unit_cover,
                            "param_noise": param_noise},
        "docs": [{"doc_name": r['doc_name'][:30], "stats": r['statistics']} for r in all_results],
    }
    (OUTPUT_DIR / "_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  汇总: {OUTPUT_DIR / '_summary.json'}")


if __name__ == "__main__":
    main()
