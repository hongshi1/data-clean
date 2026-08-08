#!/usr/bin/env python3
"""
真实数据资产构建 — Stage 0: 结构化预处理

从16份content_list.json提取8种结构化数据:
1. section_registry: 章节号→{title, req_id, doc_id}
2. table_index: 表号→表格条目
3. figure_index: 图号→图片条目
4. id_registry: 规范化ID→[5位置出现记录]
5. traceability_map: 追踪表章节号映射
6. interface_topology: 接口发送方/接收方拓扑
7. version_pairs: 3.9 vs 3.10版本对齐
8. exception_flows: 用例表异常流定义集/引用集

用法: python3 tools/build_data_assets.py
输出: data/gjb_438c/data_assets/
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
CORRECT_DIR = BASE / "data/gjb_438c/mineru_correct"
OUTPUT_DIR = BASE / "data/gjb_438c/data_assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REQ_ID_RE = re.compile(r'[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9-]+')
SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')
FIG_REF_RE = re.compile(r'(?:如图|见图|图)\s*(\d+)')
TABLE_REF_RE = re.compile(r'(?:如表|见表|表)\s*(\d+)')
CAPTION_RE = re.compile(r'(图|表)\s*(\d+)\s*(.*)')
VERSION_RE = re.compile(
    r'(达梦|Oracle|MySQL|Linux|内核|GCC|CentOS|Ubuntu|Windows|Qt|银河麒麟|WPS|wps|Redis|Nginx)'
    r'[^。]*?(V?\d+\.?\d*(?:\.\d+)?)')
CONSTRAINT_LE_RE = re.compile(
    r'(?:不超过|至多|最多|不大于|小于等于|≤|<=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
CONSTRAINT_GE_RE = re.compile(
    r'(?:不小于|至少|最少|不低于|大于等于|以上|≥|>=)\s*(\d+\.?\d*)\s*'
    r'(ms|s|秒|KB|MB|GB|TB|MHz|GHz|%|V|A|W|次|个|层|块|台|路|屏|核|维|分钟|小时|天|字节|条/秒|次/秒|笔/秒|Mpps|Tbps|Gbps|Mbps)?',
    re.IGNORECASE)
EXCEPTION_DEF_RE = re.compile(r'异常流\s*(E\d+)\s*[：:]')
EXCEPTION_REF_RE = re.compile(r'(?:进入|执行|转(?:至)?|触发)\s*异常流\s*(E\d+)')


class TableHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.cur_row = []
        self.cur_cell = []
        self.in_cell = False
        self.cell_attrs = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.cur_row = []
        elif tag in ('td', 'th'):
            self.in_cell = True
            self.cur_cell = []
            self.cell_attrs = dict(attrs)

    def handle_data(self, data):
        if self.in_cell:
            self.cur_cell.append(data.strip())

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.in_cell:
            colspan = int(self.cell_attrs.get('colspan', '1'))
            rowspan = int(self.cell_attrs.get('rowspan', '1'))
            cell_text = ' '.join(self.cur_cell)
            for _ in range(colspan):
                self.cur_row.append(cell_text if _ == 0 else '')
            self.in_cell = False
        elif tag == 'tr' and self.cur_row:
            self.rows.append(self.cur_row)


def parse_html_table(html: str) -> list:
    parser = TableHTMLParser()
    parser.feed(html)
    return parser.rows


def classify_table(caption, headers, section_id=""):
    c = (caption + ' '.join(str(h) for h in headers)).lower()
    if any(kw in c for kw in ['合格性方法', '本文档章节号', '合格性级别']):
        return 'qualification'
    if any(kw in c for kw in ['追踪', '跟踪', '任务书']):
        return 'traceability'
    if 'use case' in c or 'actor' in c:
        return 'usecase'
    if any(kw in c for kw in ['接口需求名称', '接口名称', '接口需求标识', '接口描述']):
        return 'interface'
    if any(kw in c for kw in ['数据集名称', '数据组成', '数据约束']):
        return 'data_spec'
    if any(kw in c for kw in ['设备名称', '硬件要求', '软件要求']):
        return 'environment'
    if any(kw in c for kw in ['软件名称', '软件版本', '软件种类']):
        return 'software_list'
    if any(kw in c for kw in ['软件质量因素', '要求程度']):
        return 'quality'
    if any(kw in c for kw in ['约束类型', '具体要求']):
        return 'design_constraint'
    if any(kw in c for kw in ['功能名称', '子功能', '功能标识']):
        return 'capability'
    if any(kw in c for kw in ['文档编号', '修订版本', '编写单位']):
        return 'reference'
    if any(kw in c for kw in ['保障需求', '保障设备']):
        return 'support'
    if any(kw in c for kw in ['培训内容', '培训对象']):
        return 'training'
    if any(kw in c for kw in ['数据项', '最大值', '最小值']):
        return 'data_constraint'
    return 'other'


def normalize_id(raw_id):
    return raw_id.strip().upper().replace(' ', '')


def build_all():
    print("=" * 60)
    print("真实数据资产构建 — Stage 0: 结构化预处理")
    print("=" * 60)

    # 8种数据结构
    section_registry = {}
    table_index = {}        # {doc_name: {table_num: table_item}}
    figure_index = {}       # {doc_name: {fig_num: image_item}}
    id_registry = defaultdict(list)  # {canonical_id: [{doc, section, location, context}]}
    traceability_map = []   # [{doc, upstream_section, local_section, note, direction}]
    interface_topology = [] # [{doc, interface_id, name, type, sender, receiver, content, priority}]
    version_pairs = []      # [{doc, software, versions: [{section, version}]}]
    exception_flows = []    # [{doc, section, usecase_name, defined_set, referenced_set}]

    doc_count = 0
    for doc_dir in sorted(CORRECT_DIR.iterdir()):
        if not doc_dir.is_dir() or doc_dir.name.startswith('.') or doc_dir.name.startswith('_'):
            continue
        cl_path = doc_dir / "final" / "content_list.json"
        if not cl_path.exists():
            continue

        doc_name = doc_dir.name
        doc_count += 1
        cl = json.loads(cl_path.read_text())

        current_section = ""
        current_title = ""
        doc_sections = {}
        doc_tables = {}
        doc_figures = {}
        doc_versions = defaultdict(list)

        # ===== 1. section_registry + 4. id_registry(标题位置) =====
        for item in cl:
            if not isinstance(item, dict):
                continue

            if item.get('type') == 'text':
                text = item.get('text', '')
                level = item.get('text_level', 0)

                if level > 0:
                    m = SECTION_RE.match(text.strip())
                    if m:
                        current_section = m.group(1)
                        current_title = m.group(2).strip()
                        doc_sections[current_section] = {
                            "title": current_title,
                            "req_id": None,
                            "doc_id": doc_name,
                            "level": level
                        }
                        # 从标题提取ID
                        id_m = REQ_ID_RE.search(text)
                        if id_m:
                            rid = normalize_id(id_m.group(0))
                            doc_sections[current_section]["req_id"] = rid
                            id_registry[rid].append({
                                "doc": doc_name,
                                "section": current_section,
                                "location": "section_title",
                                "context": text.strip()[:80]
                            })
                    continue

                # 清理HTML
                text_clean = re.sub(r'<[^>]+>', '', text)

                # 从正文提取ID
                for id_m in REQ_ID_RE.finditer(text_clean):
                    rid = normalize_id(id_m.group(0))
                    id_registry[rid].append({
                        "doc": doc_name,
                        "section": current_section,
                        "location": "text",
                        "context": text_clean[max(0, id_m.start() - 20):id_m.end() + 20].strip()
                    })

        section_registry[doc_name] = doc_sections

        # ===== 2. table_index + 4. id_registry(表格位置) + 5-7. 其他 =====
        current_section = ""
        for item in cl:
            if not isinstance(item, dict):
                continue

            if item.get('type') == 'text' and item.get('text_level', 0) > 0:
                m = SECTION_RE.match(item.get('text', '').strip())
                if m:
                    current_section = m.group(1)
                continue

            if item.get('type') != 'table':
                continue

            body = item.get('table_body', '')
            if len(body) < 50:
                continue

            caption = ' '.join(item.get('table_caption', []))
            rows = parse_html_table(body)
            headers = rows[0] if rows else []
            table_type = classify_table(caption, headers, current_section)

            # 表号索引
            cap_m = CAPTION_RE.match(caption)
            if cap_m:
                table_num = int(cap_m.group(2))
                doc_tables[table_num] = {
                    "caption": caption,
                    "type": table_type,
                    "section": current_section,
                    "headers": headers,
                    "row_count": len(rows)
                }

            # 从表格提取ID
            full_text = caption + " " + body
            for id_m in REQ_ID_RE.finditer(full_text):
                rid = normalize_id(id_m.group(0))
                location = "table"
                if current_section.startswith('4'):
                    location = "qualification_table"
                elif current_section.startswith('5'):
                    location = "traceability_table"
                elif current_section.startswith('3.3') or current_section.startswith('3.4'):
                    location = "interface_table"
                elif current_section.startswith('3.2'):
                    location = "func_table"
                id_registry[rid].append({
                    "doc": doc_name,
                    "section": current_section,
                    "location": location,
                    "context": full_text[max(0, id_m.start() - 20):id_m.end() + 20].strip()[:80]
                })

            # ===== 5. traceability_map =====
            if table_type == 'traceability':
                for row in rows[1:] if len(rows) > 1 else []:
                    if len(row) >= 5:
                        traceability_map.append({
                            "doc": doc_name,
                            "upstream_section": row[1] if len(row) > 1 else "",
                            "local_section": row[3] if len(row) > 3 else "",
                            "note": row[4] if len(row) > 4 else "",
                            "direction": "forward" if "正向" in caption else ("reverse" if "逆向" in caption else "unknown")
                        })
                    elif len(row) >= 4 and len(row) <= 4:
                        traceability_map.append({
                            "doc": doc_name,
                            "upstream_section": row[1] if len(row) > 1 else "",
                            "local_section": row[2] if len(row) > 2 else "",
                            "note": row[3] if len(row) > 3 else "",
                            "direction": "forward" if "正向" in caption else ("reverse" if "逆向" in caption else "unknown")
                        })

            # ===== 6. interface_topology =====
            if table_type == 'interface':
                # 按表头名称映射列索引(不同文档列顺序不同)
                col_map = {}
                for i, h in enumerate(headers):
                    h_lower = str(h).strip()
                    if '序号' in h_lower:
                        col_map['seq'] = i
                    elif '标识' in h_lower and '名称' not in h_lower:
                        col_map['id'] = i
                    elif '名称' in h_lower and '标识' in h_lower:
                        col_map['name_id'] = i  # doc01: 名称和标识合在一列
                    elif '名称' in h_lower and '标识' not in h_lower:
                        col_map['name'] = i
                    elif '描述' in h_lower or '内容' in h_lower:
                        col_map['content'] = i
                    elif '类型' in h_lower:
                        col_map['type'] = i
                    elif '发送' in h_lower:
                        col_map['sender'] = i
                    elif '接收' in h_lower:
                        col_map['receiver'] = i
                    elif '优先' in h_lower:
                        col_map['priority'] = i
                    elif '备注' in h_lower:
                        col_map['remark'] = i

                for row in rows[1:] if len(rows) > 1 else []:
                    def get_col(name):
                        idx = col_map.get(name)
                        if idx is not None and idx < len(row):
                            return str(row[idx]).strip()
                        return ""

                    # 处理名称/标识合在一列的情况(doc01)
                    name = get_col('name')
                    iface_id = get_col('id')
                    name_id = get_col('name_id')
                    if name_id and not name and not iface_id:
                        # doc01格式: "接口名称/标识" 合在一列,用/分割
                        parts = name_id.split('/')
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            iface_id = '/'.join(parts[1:]).strip()
                        else:
                            name = name_id

                    # 从ID列提取规范ID(如果有)
                    id_match = REQ_ID_RE.search(iface_id)
                    canonical_iface_id = id_match.group(0) if id_match else iface_id

                    interface_topology.append({
                        "doc": doc_name,
                        "section": current_section,
                        "interface_id": canonical_iface_id,
                        "name": name[:60],
                        "type": get_col('type'),
                        "sender": get_col('sender'),
                        "receiver": get_col('receiver'),
                        "content": get_col('content'),
                        "priority": get_col('priority')
                    })

            # ===== 7. version_pairs (从环境表+软件清单表) =====
            if table_type in ('environment', 'software_list'):
                section_prefix = '.'.join(current_section.split('.')[:2]) if current_section else 'unknown'

                if table_type == 'software_list':
                    # 软件清单表: 名称和版本在不同列
                    # 找列索引
                    name_col = None
                    ver_col = None
                    type_col = None
                    for i, h in enumerate(headers):
                        h_str = str(h).strip()
                        if '软件名称' in h_str:
                            name_col = i
                        elif '软件版本' in h_str:
                            ver_col = i
                        elif '软件种类' in h_str:
                            type_col = i

                    if name_col is not None and ver_col is not None:
                        for row in rows[1:] if len(rows) > 1 else []:
                            if name_col < len(row) and ver_col < len(row):
                                sw_name = str(row[name_col]).strip()
                                sw_ver = str(row[ver_col]).strip()
                                sw_type = str(row[type_col]).strip() if type_col is not None and type_col < len(row) else ""
                                if sw_name and sw_ver and sw_ver != '—':
                                    # 标准化软件名
                                    for std_name in ['达梦', '银河麒麟', 'WPS', 'wps', 'Qt', 'Redis', 'Nginx', 'Oracle', 'MySQL']:
                                        if std_name in sw_name:
                                            sw_name = std_name
                                            break
                                    doc_versions[sw_name].append({
                                        "section": current_section,
                                        "section_prefix": section_prefix,
                                        "version": sw_ver,
                                        "table_type": table_type,
                                        "original": f"{sw_name} {sw_ver}"
                                    })
                else:
                    # 环境表: 版本嵌入在"软件要求"列文本中
                    for row in rows[1:] if len(rows) > 1 else []:
                        for cell in row:
                            cell_text = str(cell)
                            for v_m in VERSION_RE.finditer(cell_text):
                                sw = v_m.group(1)
                                ver = v_m.group(2)
                                if ver.isdigit() and int(ver) < 20 and sw not in ('Windows',):
                                    continue
                                doc_versions[sw].append({
                                    "section": current_section,
                                    "section_prefix": section_prefix,
                                    "version": ver,
                                    "table_type": table_type,
                                    "original": cell_text[:80]
                                })

            # ===== 8. exception_flows (从usecase表) =====
            if table_type == 'usecase':
                defined = set(EXCEPTION_DEF_RE.findall(body))
                referenced = set(EXCEPTION_REF_RE.findall(body))
                usecase_name = ""
                if rows and rows[0]:
                    name_m = re.search(r'Use\s*Case\s*[名称:：]+\s*(.+)', rows[0][0], re.IGNORECASE)
                    if name_m:
                        usecase_name = name_m.group(1).strip()

                if defined or referenced:
                    exception_flows.append({
                        "doc": doc_name,
                        "section": current_section,
                        "usecase_name": usecase_name,
                        "defined_set": sorted(defined),
                        "referenced_set": sorted(referenced),
                        "dead_exceptions": sorted(defined - referenced),
                        "dangling_references": sorted(referenced - defined)
                    })

        table_index[doc_name] = doc_tables

        # 版本对齐: 同软件在不同section_prefix的版本
        for sw, entries in doc_versions.items():
            # 按 section_prefix 分组
            by_prefix = defaultdict(list)
            for e in entries:
                by_prefix[e["section_prefix"]].append(e)
            # 如果在2个以上不同section_prefix出现,且版本不同
            if len(by_prefix) >= 2:
                all_versions = set(e["version"] for e in entries)
                version_pairs.append({
                    "doc": doc_name,
                    "software": sw,
                    "versions": entries,
                    "unique_versions": sorted(all_versions),
                    "has_conflict": len(all_versions) > 1
                })

        print(f"  [{doc_name[:25]}] sections={len(doc_sections)} tables={len(doc_tables)} "
              f"ids={sum(1 for r in id_registry.values() if any(r2['doc']==doc_name for r2 in r))} "
              f"versions={len(doc_versions)}")

    # ===== 3. figure_index =====
    for doc_dir in sorted(CORRECT_DIR.iterdir()):
        if not doc_dir.is_dir() or doc_dir.name.startswith('.') or doc_dir.name.startswith('_'):
            continue
        cl_path = doc_dir / "final" / "content_list.json"
        if not cl_path.exists():
            continue
        doc_name = doc_dir.name
        cl = json.loads(cl_path.read_text())
        doc_figures = {}
        for item in cl:
            if not isinstance(item, dict) or item.get('type') != 'image':
                continue
            cap = ' '.join(item.get('image_caption', []))
            fig_m = CAPTION_RE.match(cap)
            if fig_m:
                fig_num = int(fig_m.group(2))
                doc_figures[fig_num] = {
                    "caption": cap,
                    "path": item.get('img_path', ''),
                    "section": item.get('section', '')
                }
        figure_index[doc_name] = doc_figures

    # ===== 保存所有数据资产 =====
    assets = {
        "section_registry": section_registry,
        "table_index": table_index,
        "figure_index": figure_index,
        "id_registry": dict(id_registry),
        "traceability_map": traceability_map,
        "interface_topology": interface_topology,
        "version_pairs": version_pairs,
        "exception_flows": exception_flows,
    }

    # 统计
    total_ids = len(id_registry)
    multi_pos_ids = sum(1 for v in id_registry.values() if len(set(occ['location'] for occ in v)) >= 3)
    cross_doc_ids = sum(1 for v in id_registry.values() if len(set(occ['doc'] for occ in v)) > 1)
    dead_exc = sum(len(e["dead_exceptions"]) for e in exception_flows)
    dangling_exc = sum(len(e["dangling_references"]) for e in exception_flows)
    version_conflicts = sum(1 for v in version_pairs if v.get("has_conflict", False))

    print(f"\n{'='*60}")
    print(f"Stage 0 完成: {doc_count}份文档")
    print(f"  section_registry: {sum(len(v) for v in section_registry.values())}个章节")
    print(f"  table_index: {sum(len(v) for v in table_index.values())}个表格(有表号)")
    print(f"  figure_index: {sum(len(v) for v in figure_index.values())}个图片(有图号)")
    print(f"  id_registry: {total_ids}个唯一ID, {multi_pos_ids}个出现在3+位置, {cross_doc_ids}个跨文档")
    print(f"  traceability_map: {len(traceability_map)}条追踪映射")
    print(f"  interface_topology: {len(interface_topology)}个接口")
    print(f"  version_pairs: {len(version_pairs)}组版本对齐, {version_conflicts}组有冲突")
    print(f"  exception_flows: {len(exception_flows)}个用例表, {dead_exc}个死异常, {dangling_exc}个悬空引用")

    # 保存
    output_file = OUTPUT_DIR / "stage0_assets.json"
    output_file.write_text(json.dumps(assets, ensure_ascii=False, indent=2))
    print(f"\n保存: {output_file} ({output_file.stat().st_size // 1024}KB)")

    # 统计文件
    stats = {
        "doc_count": doc_count,
        "total_sections": sum(len(v) for v in section_registry.values()),
        "total_tables_indexed": sum(len(v) for v in table_index.values()),
        "total_figures_indexed": sum(len(v) for v in figure_index.values()),
        "total_unique_ids": total_ids,
        "multi_position_ids": multi_pos_ids,
        "cross_doc_ids": cross_doc_ids,
        "traceability_edges": len(traceability_map),
        "interface_count": len(interface_topology),
        "version_pairs": len(version_pairs),
        "version_conflicts": version_conflicts,
        "exception_flow_tables": len(exception_flows),
        "dead_exceptions": dead_exc,
        "dangling_references": dangling_exc,
    }
    stats_file = OUTPUT_DIR / "stage0_stats.json"
    stats_file.write_text(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"统计: {stats_file}")

    return assets


if __name__ == "__main__":
    build_all()
