#!/usr/bin/env python3
"""
SRS结构化JSON 7项修复脚本
========================
修复MinerU结构化JSON的7个已知问题:
1. 图片提取失败(EMF→PNG)
2. 约束重复提取(去重)
3. 约束unit缺失(扩展单位提取)
4. 用例表动作约束未提取(专用解析器)
5. req_id无位置信息(记录location)
6. 版本号噪声(格式校验)
7. caption格式不统一(归一化)

用法: python3 tools/srs_fix_structured.py
"""
import re
import json
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
INPUT_DIR = BASE / "data/gjb_438c/mineru_structured"
OUTPUT_DIR = BASE / "data/gjb_438c/mineru_structured_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 修复1: 图片提取(EMF→PNG)
# ============================================================

def fix_images(doc_name: str, content_list: list, office_dir: Path, output_img_dir: Path) -> list:
    """从docx中提取所有图片(EMF→PNG, 其他直接用),返回新路径列表"""
    docx_path = office_dir / f"{doc_name}_origin.docx"
    if not docx_path.exists():
        return []

    # 从docx中提取所有媒体文件(按文件名排序保持顺序)
    with zipfile.ZipFile(docx_path, 'r') as z:
        all_media = sorted([n for n in z.namelist() if 'media/' in n],
                          key=lambda x: int(re.search(r'image(\d+)', x).group(1)) if re.search(r'image(\d+)', x) else 999)

    if not all_media:
        return []

    # 获取content_list中的image条目数
    content_images = [(i, item) for i, item in enumerate(content_list)
                     if isinstance(item, dict) and item.get('type') == 'image']
    num_images = len(content_images)

    output_img_dir.mkdir(parents=True, exist_ok=True)
    doc_subdir = doc_name[:20]
    new_paths = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 按顺序处理每个图片
        for idx in range(min(num_images, len(all_media))):
            mf = all_media[idx]
            ext = Path(mf).suffix.lower()
            png_name = f"img_{idx+1:03d}.png"
            png_path = output_img_dir / png_name
            rel_path = f"images/{doc_subdir}/{png_name}"

            # 跳过已存在的
            if png_path.exists() and png_path.stat().st_size > 0:
                new_paths.append(rel_path)
                content_images[idx][1]['img_path'] = rel_path
                continue

            if ext == '.emf':
                # EMF→PNG (LibreOffice)
                with zipfile.ZipFile(docx_path, 'r') as z:
                    z.extract(mf, tmpdir)
                emf_path = tmpdir / mf

                result = subprocess.run(
                    ['soffice', '--headless', '--convert-to', 'png',
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
                # 直接复制
                with zipfile.ZipFile(docx_path, 'r') as z:
                    with z.open(mf) as src, open(png_path, 'wb') as dst:
                        dst.write(src.read())
                new_paths.append(rel_path)
                content_images[idx][1]['img_path'] = rel_path
            else:
                # 未知格式,跳过
                new_paths.append(content_images[idx][1].get('img_path', ''))

        # 如果图片文件数少于image条目数
        for idx in range(len(all_media), num_images):
            new_paths.append(content_images[idx][1].get('img_path', ''))

    return new_paths


# ============================================================
# 修复2: 约束去重
# ============================================================

def dedup_constraints(constraints: list) -> list:
    """按(param, operator, value, unit, section)去重,优先保留有source标记的"""
    seen = {}  # key → index in result
    result = []
    for c in constraints:
        key = (
            c.get('param', ''),
            c.get('operator', ''),
            c.get('value', ''),
            c.get('unit', ''),
            c.get('section', ''),
        )
        if key not in seen:
            seen[key] = len(result)
            result.append(c)
        else:
            # 如果已有记录但没有source,而新记录有source,则替换
            existing = result[seen[key]]
            if not existing.get('source') and c.get('source'):
                result[seen[key]] = c
    return result


# ============================================================
# 修复3: 约束unit缺失 - 扩展单位提取
# ============================================================

# 扩展单位模式: 覆盖原文中常见的单位
UNIT_PATTERNS = [
    # 复合单位
    (r'条/秒', '条/秒'),
    (r'条每秒', '条/秒'),
    (r'次/秒', '次/秒'),
    (r'笔/秒', '笔/秒'),
    (r'路/秒', '路/秒'),
    (r'Mpps', 'Mpps'),
    (r'Tbps', 'Tbps'),
    (r'Gbps', 'Gbps'),
    (r'Mbps', 'Mbps'),
    (r'kbps', 'kbps'),
    # 标准单位
    (r'(GB|gb)', 'GB'),
    (r'(TB|tb)', 'TB'),
    (r'(MB|mb)', 'MB'),
    (r'(KB|kb)', 'KB'),
    (r'(GHz|ghz)', 'GHz'),
    (r'(MHz|mhz)', 'MHz'),
    (r'(ms|毫秒)', 'ms'),
    (r'(s|秒)(?![\w])', 's'),
    (r'分钟', '分钟'),
    (r'小时', '小时'),
    (r'天', '天'),
    (r'%', '%'),
    (r'(V|v)(?![\w])', 'V'),
    (r'(A|a)(?![\w])', 'A'),
    (r'(W|w)(?![\w])', 'W'),
    # 中文单位
    (r'核', '核'),
    (r'个', '个'),
    (r'块', '块'),
    (r'台', '台'),
    (r'路', '路'),
    (r'层', '层'),
    (r'屏', '屏'),
    (r'次', '次'),
    (r'维', '维'),
    # 分辨率特殊处理
    (r'(\d+×\d+)', None),  # 分辨率,作为值的一部分
]

def extract_unit_from_original(original: str, value: str, param: str = '') -> str:
    """从约束原文中提取单位"""
    # 找到value在原文中的位置
    val_str = str(value)
    if '.' in val_str:
        val_str = val_str.rstrip('0').rstrip('.')

    # 找value后面的文本
    idx = original.find(val_str)
    if idx < 0:
        # 尝试整数形式
        try:
            idx = original.find(str(int(float(value))))
        except (ValueError, TypeError):
            pass
    if idx < 0:
        return ''

    after = original[idx + len(val_str):].strip()

    # 特殊处理: "Hz" (通常是GHz的OCR残留)
    if re.match(r'^Hz', after, re.IGNORECASE):
        if '主频' in param or 'CPU' in param or '频率' in param:
            return 'GHz'
        return 'Hz'

    # 检查各种单位
    for pattern, unit_name in UNIT_PATTERNS:
        m = re.match(pattern, after, re.IGNORECASE)
        if m:
            if unit_name:
                return unit_name
            else:
                return m.group(0)

    # 检查value后面紧跟的×符号(分辨率)
    if after.startswith('×') or after.startswith('*'):
        m = re.match(r'[×*]\s*(\d+)', after)
        if m:
            return f'×{m.group(1)}'

    # 特殊: "g" → "GB" (用例表中"4g"应为"4GB")
    if re.match(r'^g\b', after, re.IGNORECASE):
        return 'GB'

    # 特殊: "分屏" 
    if re.match(r'^分屏', after):
        return '分屏'

    return ''


def fix_constraint_units(constraints: list) -> list:
    """补充缺失的unit"""
    for c in constraints:
        if not c.get('unit'):
            unit = extract_unit_from_original(c.get('original', ''), c.get('value', ''), c.get('param', ''))
            if unit:
                c['unit'] = unit
    return constraints


# ============================================================
# 修复4: 用例表动作约束提取
# ============================================================

class TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == 'tr': self.current_row = []
        elif tag in ('td', 'th'): self.in_cell = True; self.current_cell = []

    def handle_data(self, data):
        if self.in_cell: self.current_cell.append(data.strip())

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


# 约束正则(扩展版,支持用例表中的约束)
CONSTRAINT_LE_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
CONSTRAINT_GE_RE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|以上|≥|>=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
# 用例表特有的"大于""小于"约束
CONSTRAINT_GT_RE = re.compile(
    r'(?:大于|超过|高于)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)

# 版本号约束(用例表中常见)
VERSION_CONSTRAINT_RE = re.compile(
    r'(nodejs|Node\.js|java|Python|Qt|达梦|Oracle|MySQL|Redis|Nginx)'
    r'[^。]*?(V?\d+\.?\d*(?:\.\d+)?)\s*以上', re.IGNORECASE)


def _extract_param_name(before_text):
    """从约束前的文本提取参数名"""
    parts = re.split(r'[，。；：、\s：:;,\n]+', before_text.strip())
    for part in reversed(parts):
        part = part.strip()
        if not part:
            continue
        cn_m = re.search(r'([\u4e00-\u9fa5]{2,8})$', part)
        if cn_m:
            return cn_m.group(1)
        if re.match(r'^[\u4e00-\u9fa5]{2,8}$', part):
            return part
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


def extract_constraints_from_text(text, section, source="text"):
    """从文本中提取约束(扩展版)"""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    results = []
    for m in CONSTRAINT_LE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":"≤","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section,
                       "source":source})
    for m in CONSTRAINT_GE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":"≥","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section,
                       "source":source})
    for m in CONSTRAINT_GT_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2) or ""
        before = text[max(0,m.start()-20):m.start()]
        param = _extract_param_name(before)
        results.append({"param":param,"operator":">","value":val,"unit":unit,
                       "role":classify_role(param,section),
                       "original":text[max(0,m.start()-20):m.end()+20],"section":section,
                       "source":source})
    return results


def extract_usecase_constraints(table_body: str, caption: str, section: str):
    """从用例描述表中提取动作约束"""
    rows = parse_html_table(table_body)
    if not rows:
        return [], None

    # 检测是否为用例表
    headers = rows[0] if rows else []
    headers_text = ' '.join(str(h) for h in headers)
    if 'Use Case' not in headers_text and 'Actor' not in headers_text:
        return [], None

    # 找"动作约束"行的位置
    constraint_col_idx = -1
    constraint_header_row = -1
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if '动作约束' in str(cell) or ('性能' in str(cell) and '可靠性' in str(cell)):
                constraint_col_idx = j
                constraint_header_row = i
                break
        if constraint_col_idx >= 0:
            break

    if constraint_col_idx < 0:
        return [], None

    # 提取约束列内容(从header行后一行开始)
    constraint_texts = []
    for i in range(constraint_header_row + 1, len(rows)):
        row = rows[i]
        if constraint_col_idx < len(row):
            cell = row[constraint_col_idx].strip()
            if cell and cell != '—' and cell != '-':
                constraint_texts.append(cell)

    # 从约束文本中提取结构化约束
    all_constraints = []
    for ct in constraint_texts:
        cs = extract_constraints_from_text(ct, section, source="usecase_action_constraint")
        all_constraints.extend(cs)
        # 也提取版本约束
        for m in VERSION_CONSTRAINT_RE.finditer(ct):
            before = ct[max(0,m.start()-10):m.start()]
            param = _extract_param_name(before) or m.group(1)
            all_constraints.append({
                "param": param, "operator": "≥",
                "value": m.group(2), "unit": "版本",
                "role": "config",
                "original": ct[max(0,m.start()-20):m.end()+20],
                "section": section,
                "source": "usecase_action_constraint"
            })

    # 用例表信息
    usecase_info = {
        "has_action_constraints": len(constraint_texts) > 0,
        "constraint_count": len(all_constraints),
        "constraint_texts": constraint_texts[:3],  # 保留前3条原文
    }

    return all_constraints, usecase_info


# ============================================================
# 修复5: req_id位置信息
# ============================================================

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9]+')
SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')

def extract_req_ids_with_location(content_list: list, sections: dict) -> list:
    """提取req_id并记录位置"""
    req_id_locations = defaultdict(list)
    current_section = ""

    for item in content_list:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type", "text")

        if item_type == "text":
            text = item.get("text", "")
            text_level = item.get("text_level", 0)

            if text_level > 0:
                m = SECTION_RE.match(text.strip())
                if m:
                    current_section = m.group(1)
                # 标题中的ID
                for rid_m in REQ_ID_RE.finditer(text):
                    rid = rid_m.group(0)
                    req_id_locations[rid].append({
                        "section": current_section,
                        "location": "section_title",
                        "context": text.strip()[:80]
                    })
                continue

            # 正文中的ID
            for rid_m in REQ_ID_RE.finditer(text):
                rid = rid_m.group(0)
                req_id_locations[rid].append({
                    "section": current_section,
                    "location": "text",
                    "context": text[max(0,rid_m.start()-20):rid_m.end()+20].strip()
                })

        elif item_type == "table":
            table_body = item.get("table_body", "")
            caption = ' '.join(item.get("table_caption", []))
            rows = parse_html_table(table_body)
            headers = rows[0] if rows else []
            headers_text = ' '.join(str(h) for h in headers)

            # 判断表格类型
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
                ctx = full_text[max(0,rid_m.start()-20):rid_m.end()+20].strip()[:80]
                # 清理HTML标签
                ctx = re.sub(r'<[^>]+>', '', ctx)
                req_id_locations[rid].append({
                    "section": current_section,
                    "location": table_loc,
                    "context": ctx
                })

    # 转为列表
    result = []
    for rid, locations in sorted(req_id_locations.items()):
        result.append({
            "id": rid,
            "locations": locations,
            "location_count": len(locations)
        })
    return result


# ============================================================
# 修复6: 版本号噪声过滤
# ============================================================

# 已知软件的标准版本模式
VALID_VERSION_PATTERNS = {
    '达梦': re.compile(r'^V?\d+(?:\.\d+)*$'),  # V7.6, V8, V7.2
    '银河麒麟': re.compile(r'^V?\d+(?:\.\d+)*$'),  # V4.0.2, V10, V5
    'WPS': re.compile(r'^V?\d+(?:\.\d+)*$', re.IGNORECASE),  # V10.1, V11
    'wps': re.compile(r'^V?\d+(?:\.\d+)*$'),
    'Qt': re.compile(r'^\d+\.\d+(?:\.\d+)?$'),  # 5.9.6, 5.6.0
    'Oracle': re.compile(r'^\d+[cg]$', re.IGNORECASE),  # 11g, 12c
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

def is_valid_version(software: str, version: str, original: str) -> bool:
    """检查版本号是否有效"""
    # 1. 单数字版本且不是Windows版本
    if version.isdigit() and len(version) <= 2:
        sw_lower = software.lower()
        # Windows 7/10/11 是合法的
        if software == 'Windows' and version in ('7', '10', '11', 'XP'):
            # 但检查是否是双版本拆分(如Windows7/Windows 10)
            idx = original.find(version)
            if idx > 0:
                before = original[:idx]
                if '/' in before[-15:] and 'Windows' in before[-15:]:
                    return False  # 双版本拆分,跳过
            return True
        # 其他软件的单数字版本通常是行号
        if sw_lower not in ('windows',):
            return False

    # 2. 检查是否匹配软件的标准版本模式
    pattern = VALID_VERSION_PATTERNS.get(software)
    if pattern:
        if not pattern.match(version):
            return False

    # 3. 检查版本号是否紧跟在软件名后面(排除行号)
    idx = original.find(version)
    if idx > 0:
        before = original[:idx]
        # 如果前面是纯数字+空格,可能是表格行号
        if re.search(r'\d+\s*$', before) and software not in before[-20:]:
            return False

    return True


def fix_versions(versions: list) -> list:
    """过滤版本号噪声"""
    result = []
    for v in versions:
        if is_valid_version(v.get('software',''), v.get('version',''), v.get('original','')):
            result.append(v)
    return result


# ============================================================
# 修复7: caption格式统一
# ============================================================

CAPTION_RE = re.compile(r'(图|表)\s*(\d+)\s*[.、:：]?\s*(.*)')

def normalize_caption(caption: str) -> str:
    """统一caption格式为 '图N 标题' 或 '表N 标题'"""
    if not caption:
        return ''
    caption = caption.strip()
    # 清理markdown标记
    caption = re.sub(r'\*+', '', caption)
    # 清理前缀文字(如"本文档的追踪性见表51和表50。 表51...")
    # 找最后一个"图N"或"表N"匹配
    matches = list(CAPTION_RE.finditer(caption))
    if matches:
        m = matches[-1]  # 取最后一个匹配
        prefix = m.group(1)  # 图 or 表
        num = m.group(2)
        title = m.group(3).strip()
        if title:
            return f"{prefix}{num} {title}"
        return f"{prefix}{num}"
    return caption


def fix_captions(data: dict) -> dict:
    """统一所有caption格式"""
    for sec_id, sd in data['sections'].items():
        for table in sd.get('tables', []):
            if table.get('caption'):
                table['caption'] = normalize_caption(table['caption'])
        for img in sd.get('images', []):
            if img.get('caption'):
                img['caption'] = normalize_caption(img['caption'])
    return data


# ============================================================
# 主修复流程
# ============================================================

def fix_document(doc_dir: Path) -> dict:
    """修复单个文档"""
    doc_name = doc_dir.name
    office_dir = doc_dir / "office"
    cl_path = office_dir / f"{doc_name}_content_list.json"

    if not cl_path.exists():
        return {"error": f"content_list不存在: {cl_path}"}

    content_list = json.loads(cl_path.read_text(encoding="utf-8"))

    # ===== 读取旧结构化JSON作为基础 =====
    old_json_path = INPUT_DIR / f"{doc_name}_structured.json"
    if old_json_path.exists():
        data = json.loads(old_json_path.read_text(encoding="utf-8"))
    else:
        return {"error": f"旧structured.json不存在: {old_json_path}"}

    fix_log = {"doc": doc_name[:30], "fixes": []}

    # ===== 修复1: 图片提取(EMF→PNG) =====
    output_img_dir = OUTPUT_DIR / "images" / doc_name[:20]
    try:
        new_paths = fix_images(doc_name, content_list, office_dir, output_img_dir)
        # 更新sections中的图片路径 — 按顺序匹配
        img_idx = 0
        unique_paths = set()
        for sec_id, sd in data['sections'].items():
            for img in sd.get('images', []):
                if img_idx < len(new_paths):
                    img['path'] = new_paths[img_idx]
                    img_idx += 1
                if img.get('path'):
                    unique_paths.add(img['path'])
        total_images = img_idx
        fix_log["fixes"].append({
            "fix": "图片提取(EMF→PNG)",
            "status": "修复" if new_paths else "无需修复",
            "detail": f"转换{len(new_paths)}张图片, 唯一路径: {len(unique_paths)}/{total_images}"
        })
    except Exception as e:
        fix_log["fixes"].append({"fix": "图片提取(EMF→PNG)", "status": "失败", "detail": str(e)})

    # ===== 修复4: 用例表动作约束提取 =====
    usecase_constraints = []
    usecase_count = 0
    for sec_id, sd in data['sections'].items():
        for table in sd.get('tables', []):
            if table.get('type') == 'other':
                # 重新解析原始table_body
                # 从content_list中找对应的table
                pass  # 用content_list重新处理

    # 从content_list中重新提取用例表约束
    current_section = ""
    for item in content_list:
        if not isinstance(item, dict):
            continue
        if item.get('type') == 'text':
            text = item.get('text', '')
            text_level = item.get('text_level', 0)
            if text_level > 0:
                m = SECTION_RE.match(text.strip())
                if m:
                    current_section = m.group(1)
        elif item.get('type') == 'table':
            table_body = item.get('table_body', '')
            caption = ' '.join(item.get('table_caption', []))
            cs, usecase_info = extract_usecase_constraints(table_body, caption, current_section)
            if cs:
                usecase_constraints.extend(cs)
                usecase_count += 1
                # 标记用例表
                for sec_id, sd in data['sections'].items():
                    if sec_id == current_section:
                        for t in sd.get('tables', []):
                            if not t.get('usecase_info'):
                                t['usecase_info'] = usecase_info
                                break

    fix_log["fixes"].append({
        "fix": "用例表动作约束提取",
        "status": "修复" if usecase_constraints else "无新增",
        "detail": f"从{usecase_count}个用例表中提取{len(usecase_constraints)}条约束"
    })

    # ===== 修复2+3: 约束去重+unit补充 =====
    all_constraints = data.get('all_constraints', [])
    old_count = len(all_constraints)

    # 合并用例表约束
    all_constraints.extend(usecase_constraints)

    # 补充unit
    all_constraints = fix_constraint_units(all_constraints)

    # 去重
    all_constraints = dedup_constraints(all_constraints)

    data['all_constraints'] = all_constraints

    # 更新section级别的约束
    for sec_id, sd in data['sections'].items():
        cs = sd.get('constraints', [])
        cs = fix_constraint_units(cs)
        cs = dedup_constraints(cs)
        sd['constraints'] = cs

    unit_fixed = sum(1 for c in all_constraints if c.get('unit'))
    fix_log["fixes"].append({
        "fix": "约束去重",
        "status": "修复" if len(all_constraints) < old_count + len(usecase_constraints) else "无重复",
        "detail": f"原始{old_count}+用例表{len(usecase_constraints)} → 去重后{len(all_constraints)}"
    })
    fix_log["fixes"].append({
        "fix": "约束unit补充",
        "status": "修复",
        "detail": f"有unit约束: {unit_fixed}/{len(all_constraints)} ({unit_fixed/len(all_constraints)*100:.1f}%)"
    })

    # ===== 修复5: req_id位置信息 =====
    req_id_with_loc = extract_req_ids_with_location(content_list, data['sections'])
    data['all_req_ids'] = req_id_with_loc
    fix_log["fixes"].append({
        "fix": "req_id位置信息",
        "status": "修复",
        "detail": f"{len(req_id_with_loc)}个ID, 共{sum(r['location_count'] for r in req_id_with_loc)}个位置"
    })

    # ===== 修复6: 版本号噪声过滤 =====
    old_ver_count = len(data.get('all_versions', []))
    data['all_versions'] = fix_versions(data.get('all_versions', []))
    # 更新section级别
    for sec_id, sd in data['sections'].items():
        sd['versions'] = fix_versions(sd.get('versions', []))

    fix_log["fixes"].append({
        "fix": "版本号噪声过滤",
        "status": "修复" if len(data['all_versions']) < old_ver_count else "无噪声",
        "detail": f"{old_ver_count} → {len(data['all_versions'])} (过滤{old_ver_count - len(data['all_versions'])}条)"
    })

    # ===== 修复7: caption格式统一 =====
    data = fix_captions(data)
    fix_log["fixes"].append({
        "fix": "caption格式统一",
        "status": "修复",
        "detail": "统一为'图N 标题'格式"
    })

    # ===== 更新统计信息 =====
    data['statistics']['constraints'] = len(all_constraints)
    data['statistics']['versions'] = len(data['all_versions'])
    data['statistics']['req_ids'] = len(req_id_with_loc)
    data['parse_date'] = datetime.now().isoformat()
    data['source'] = "MinerU标准解析 + 7项修复(v2)"
    data['fix_log'] = fix_log

    return data


def main():
    print("=" * 60)
    print("SRS结构化JSON 7项修复脚本")
    print("=" * 60)

    all_logs = []
    for doc_dir in sorted(MINERU_DIR.iterdir()):
        if not doc_dir.is_dir():
            continue
        doc_name = doc_dir.name[:35]
        result = fix_document(doc_dir)
        if "error" in result:
            print(f"  [{doc_name}] 错误: {result['error']}")
            continue

        out = OUTPUT_DIR / f"{doc_dir.name}_structured.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

        log = result['fix_log']
        s = result['statistics']
        print(f"\n  [{doc_name[:30]}]")
        for fix in log['fixes']:
            status_icon = "✓" if "修复" in fix['status'] else "○"
            print(f"    {status_icon} {fix['fix']}: {fix['detail']}")
        print(f"    最终: 章:{s['sections']} 表:{s['tables']} 图:{s['images']} "
              f"约束:{s['constraints']} 版本:{s['versions']} ID:{s['req_ids']}")

        all_logs.append(log)

    # 保存汇总
    total_constraints = sum(l.get('constraints', 0) for l in all_logs)
    summary = {
        "fix_date": datetime.now().isoformat(),
        "total_docs": len(all_logs),
        "fixes_applied": ["图片EMF→PNG", "约束去重", "unit补充", "用例表约束提取",
                         "req_id位置", "版本号过滤", "caption统一"],
        "docs": all_logs,
    }
    (OUTPUT_DIR / "_fix_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"修复完成: {len(all_logs)}份文档")
    print(f"输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
