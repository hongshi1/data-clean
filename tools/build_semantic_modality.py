#!/usr/bin/env python3
"""
语义层数据构建 — 按8个模态场景组织

原则:
1. 只做收集和组织，不做不一致检测
2. 按上下文关联匹配图+表+正文(同section内的真实关联)
3. 先跑doc03验证，确认后扩展

8个场景:
1. 用例图+capability表+正文
2. 流程图+usecase表+正文
3. 接口图+interface表+正文
4. 流程图+capability表+正文
5. 功能图+capability表+正文
6. 功能框架图+其他表+正文
7. 用例图+usecase表+正文
8. 纯图片+正文(无表)

用法: python3 tools/build_semantic_modality.py --doc 03  # 先跑doc03
      python3 tools/build_semantic_modality.py --all      # 跑全部16份
"""
import json
import re
import argparse
from pathlib import Path
from collections import defaultdict
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
CORRECT_DIR = BASE / "data/gjb_438c/mineru_correct"
OUTPUT_PATH = BASE / "data/gjb_438c/data_assets/semantic_modality_data.json"

SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')
CAPTION_RE = re.compile(r'(图|表)\s*(\d+)\s*(.*)')


class TP(HTMLParser):
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
            for i in range(colspan):
                self.cur_row.append(cell_text if i == 0 else '')
            self.in_cell = False
        elif tag == 'tr' and self.cur_row:
            self.rows.append(self.cur_row)


def parse_table(html):
    p = TP()
    p.feed(html)
    return p.rows


def classify_image(cap):
    if not cap:
        return 'unknown'
    if '用例' in cap:
        return 'usecase_diagram'
    if '流程' in cap:
        return 'flowchart'
    if '接口' in cap:
        return 'interface_diagram'
    if '活动' in cap:
        return 'activity_diagram'
    if '框架' in cap or '组成' in cap or '划分' in cap:
        return 'function_framework'
    if '功能' in cap:
        return 'function_diagram'
    if '状态' in cap:
        return 'state_diagram'
    return 'other'


def classify_table(caption, headers):
    """表型分类 — caption优先于headers,避免能力标识表被误分类为usecase"""
    cap_lower = caption.lower()
    headers_text = ' '.join(str(h) for h in headers)
    all_text = (caption + ' ' + headers_text).lower()

    # 1. caption特异关键词优先(最可靠)
    if '能力标识' in caption or '所有能力' in caption:
        return 'capability'
    if '用例描述' in caption or '用例场景' in caption:
        return 'usecase'
    if any(kw in caption for kw in ['合格性方法', '合格性规定']):
        return 'qualification'
    if any(kw in caption for kw in ['追踪', '跟踪']):
        return 'traceability'
    if any(kw in caption for kw in ['接口需求', '外部接口', '内部接口']):
        return 'interface'
    if any(kw in caption for kw in ['引用文档']):
        return 'reference'

    # 2. header关键词(caption无特异信息时)
    # capability表特征: 含"项目唯一标识符"+"需求描述"+"需求重用"
    if '项目唯一标识符' in headers_text or '需求重用' in headers_text:
        return 'capability'
    # usecase表特征: 含"Actor"(不是能力标识表的"Use case名称")
    if 'actor' in all_text or 'actors' in all_text:
        return 'usecase'
    # usecase表: caption含"Use Case"且不含"能力标识"
    if ('use case' in all_text or 'usecase' in all_text) and '能力标识' not in caption:
        # 进一步检查: 如果含"Actor的动作"或"主事件流",才是真正的usecase描述表
        if any(kw in all_text for kw in ['主事件流', 'actor的动作', '系统的动作', '动作约束']):
            return 'usecase'
        # 否则是能力标识表(含Use case名称但不是用例描述表)
        return 'capability'

    # 3. 其他表型
    if any(kw in all_text for kw in ['接口需求名称', '接口名称', '接口需求标识', '接口描述']):
        return 'interface'
    if any(kw in all_text for kw in ['数据集名称', '数据组成']):
        return 'data_spec'
    if any(kw in all_text for kw in ['设备名称', '硬件要求', '软件要求']):
        return 'environment'
    if any(kw in all_text for kw in ['软件名称', '软件版本', '软件种类']):
        return 'software_list'
    if any(kw in all_text for kw in ['合格性方法', '本文档章节号']):
        return 'qualification'
    if any(kw in all_text for kw in ['追踪', '跟踪', '任务书']):
        return 'traceability'
    if any(kw in all_text for kw in ['功能名称', '子功能', '功能标识']):
        return 'capability'
    return 'other'


# 场景定义: [(图片类型, 表格类型), ...] — 每个场景支持多种组合
SCENARIO_MAP = {
    1: [('usecase_diagram', 'capability')],
    2: [('flowchart', 'usecase')],
    3: [('interface_diagram', 'interface')],
    4: [('flowchart', 'capability'), ('activity_diagram', 'capability')],
    5: [('function_diagram', 'capability'), ('function_framework', 'capability'), ('other', 'capability')],
    6: [('function_framework', 'other'), ('other', 'other')],
    7: [('usecase_diagram', 'usecase')],
}


def collect_items(content_list):
    """从content_list收集所有条目，标注section信息"""
    items = []
    current_section = ""
    current_title = ""

    for raw_item in content_list:
        if not isinstance(raw_item, dict):
            continue

        if raw_item.get('type') == 'text' and raw_item.get('text_level', 0) > 0:
            m = SECTION_RE.match(raw_item.get('text', '').strip())
            if m:
                current_section = m.group(1)
                current_title = m.group(2).strip()
            continue

        item = {
            "section": current_section,
            "section_title": current_title,
        }

        if raw_item.get('type') == 'text':
            text = raw_item.get('text', '')
            text_clean = re.sub(r'<[^>]+>', '', text).strip()
            if text_clean and len(text_clean) > 3:
                item["type"] = "text"
                item["content"] = text_clean
                items.append(item)

        elif raw_item.get('type') == 'table':
            body = raw_item.get('table_body', '')
            if len(body) < 50:
                continue
            caption = ' '.join(raw_item.get('table_caption', []))
            rows = parse_table(body)
            headers = rows[0] if rows else []
            ttype = classify_table(caption, headers)

            # 提取表号
            table_num = None
            cap_m = CAPTION_RE.match(caption)
            if cap_m and cap_m.group(1) == '表':
                table_num = int(cap_m.group(2))

            item["type"] = "table"
            item["table_type"] = ttype
            item["caption"] = caption
            item["table_num"] = table_num
            item["headers"] = [str(h)[:30] for h in headers[:8]]
            item["rows"] = [[str(c)[:60] for c in row[:8]] for row in rows[:20]]  # 保留前20行
            item["row_count"] = len(rows)
            items.append(item)

        elif raw_item.get('type') == 'image':
            cap = ' '.join(raw_item.get('image_caption', []))
            img_type = classify_image(cap)
            fig_num = None
            fig_m = CAPTION_RE.match(cap)
            if fig_m and fig_m.group(1) == '图':
                fig_num = int(fig_m.group(2))

            item["type"] = "image"
            item["image_type"] = img_type
            item["caption"] = cap
            item["fig_num"] = fig_num
            item["path"] = raw_item.get('img_path', '')
            items.append(item)

    return items


def find_contextual_table_and_text(items, img_idx):
    """为图片找上下文关联的表格和正文
    
    关联规则(按优先级):
    1. 同section内,优先找caption有共同功能关键词的表格
    2. 同section内,若无关键词匹配,取最近的表格
    3. 若同section无表格,逐级向上查父section
    4. 正文取同section内最近的文字
    """
    img_item = items[img_idx]
    img_section = img_item["section"]
    img_type = img_item.get("image_type", "unknown")
    img_caption = img_item.get("caption", "")

    if not img_section:
        return None, None

    # 收集要检查的section(逐级向上)
    sections_to_check = [img_section]
    parts = img_section.split('.')
    if len(parts) >= 4:
        parent4 = '.'.join(parts[:4])
        if parent4 != img_section:
            sections_to_check.append(parent4)
    if len(parts) >= 3:
        parent3 = '.'.join(parts[:3])
        if parent3 not in sections_to_check:
            sections_to_check.append(parent3)
    if len(parts) >= 2:
        parent2 = '.'.join(parts[:2])
        if parent2 not in sections_to_check:
            sections_to_check.append(parent2)

    # 该图片类型对应的场景所需表型
    required_table_types = set()
    for sid, combos in SCENARIO_MAP.items():
        for req_img, req_table in combos:
            if img_type == req_img:
                required_table_types.add(req_table)

    # 从图片caption提取功能关键词
    img_keywords = extract_keywords(img_caption)

    for check_section in sections_to_check:
        section_tables = []
        section_texts = []
        for i, item in enumerate(items):
            if i == img_idx:
                continue
            if item.get("section") != check_section:
                continue
            if item["type"] == "table":
                section_tables.append((i, item))
            elif item["type"] == "text":
                section_texts.append((i, item))

        if not section_tables:
            continue

        # 优先级1: 同section + caption有共同关键词 + 表型匹配场景
        for _, tbl in section_tables:
            if tbl.get("table_type") in required_table_types:
                tbl_keywords = extract_keywords(tbl.get("caption", ""))
                if img_keywords & tbl_keywords:
                    nearest_text = None
                    if section_texts:
                        nearest_text = min(section_texts, key=lambda x: abs(x[0] - img_idx))[1]
                    return tbl, nearest_text

        # 优先级2: 同section + 表型匹配场景(无关键词匹配但表型对)
        for _, tbl in section_tables:
            if tbl.get("table_type") in required_table_types:
                nearest_text = None
                if section_texts:
                    nearest_text = min(section_texts, key=lambda x: abs(x[0] - img_idx))[1]
                return tbl, nearest_text

        # 优先级3: 同section + caption有共同关键词(表型不匹配但内容关联)
        for _, tbl in section_tables:
            tbl_keywords = extract_keywords(tbl.get("caption", ""))
            if img_keywords & tbl_keywords:
                nearest_text = None
                if section_texts:
                    nearest_text = min(section_texts, key=lambda x: abs(x[0] - img_idx))[1]
                return tbl, nearest_text

        # 优先级4: 同section内最近的表格(兜底)
        nearest_table = min(section_tables, key=lambda x: abs(x[0] - img_idx))[1]
        nearest_text = None
        if section_texts:
            nearest_text = min(section_texts, key=lambda x: abs(x[0] - img_idx))[1]
        return nearest_table, nearest_text

    return None, None


def extract_keywords(text):
    """从caption中提取功能关键词(用于匹配图片和表格)
    
    改进: 提取2-4字核心功能词,避免整串匹配导致假阴性
    例如"语音识别流程图"和"语音识别能力标识"应匹配到"语音识别"
    """
    if not text:
        return set()
    text = re.sub(r'^[图表]\s*\d+\s*', '', text)
    words = set()
    # 提取2-4字连续中文(比2-6字更细粒度,能匹配子串)
    for m in re.finditer(r'[\u4e00-\u9fa5]{2,4}', text):
        words.add(m.group(0))
    generic = {'用例图', '流程图', '接口图', '功能图', '活动图', '框架图', '状态图',
               '用例描述', '所有能力', '能力标识', '外部接口', '内部接口', '接口需求',
               '接口标识', '功能划分', '运行流程', '组成图', '设计', '需求规格', '说明',
               '软件需求', '规格说明', '终稿'}
    return words - generic


def build_for_doc(doc_name):
    """构建单份文档的语义层数据"""
    cl_path = CORRECT_DIR / doc_name / "final" / "content_list.json"
    if not cl_path.exists():
        print(f"  ✗ content_list不存在: {doc_name}")
        return None

    cl = json.loads(cl_path.read_text())
    items = collect_items(cl)

    # 8个场景的实例
    scenarios = defaultdict(list)

    for i, item in enumerate(items):
        if item["type"] != "image":
            continue

        img_type = item.get("image_type", "unknown")
        table_item, text_item = find_contextual_table_and_text(items, i)

        # 构建实例
        instance = {
            "doc": doc_name,
            "section": item["section"],
            "section_title": item["section_title"],
            "image": {
                "caption": item.get("caption", ""),
                "image_type": img_type,
                "fig_num": item.get("fig_num"),
                "path": item.get("path", "")
            },
            "table": None,
            "text": None,
            "match_quality": "none",  # strong/weak/none
            "match_keywords": []  # 共同关键词
        }

        if table_item:
            instance["table"] = {
                "caption": table_item.get("caption", ""),
                "table_type": table_item.get("table_type", ""),
                "table_num": table_item.get("table_num"),
                "headers": table_item.get("headers", []),
                "row_count": table_item.get("row_count", 0),
                "rows": table_item.get("rows", [])
            }
            # 判断匹配质量
            img_kw = extract_keywords(item.get("caption", ""))
            tbl_kw = extract_keywords(table_item.get("caption", ""))
            common = sorted(img_kw & tbl_kw)
            if common:
                instance["match_quality"] = "strong"
                instance["match_keywords"] = common
            else:
                instance["match_quality"] = "weak"

        if text_item:
            instance["text"] = {
                "content": text_item.get("content", "")[:200]
            }

        # 匹配到场景
        matched_scenario = None
        if table_item:
            table_type = table_item.get("table_type", "")
            for sid, combos in SCENARIO_MAP.items():
                for req_img, req_table in combos:
                    if img_type == req_img and table_type == req_table:
                        matched_scenario = sid
                        break
                if matched_scenario:
                    break

        if matched_scenario:
            scenarios[matched_scenario].append(instance)
        elif not table_item:
            # 无表格 → 场景8
            scenarios[8].append(instance)
        else:
            # 有表格但不匹配任何场景 → 未分类
            scenarios["unclassified"].append(instance)

    return dict(scenarios)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", help="只跑指定文档(如03)")
    parser.add_argument("--all", action="store_true", help="跑全部16份")
    args = parser.parse_args()

    print("=" * 60)
    print("语义层数据构建 — 按8个模态场景组织")
    print("=" * 60)

    all_scenarios = defaultdict(lambda: defaultdict(list))

    if args.doc:
        # 只跑指定文档
        doc_dirs = [d for d in sorted(CORRECT_DIR.iterdir())
                    if d.is_dir() and d.name.startswith(args.doc)
                    and not d.name.startswith('.') and not d.name.startswith('_')]
    else:
        doc_dirs = [d for d in sorted(CORRECT_DIR.iterdir())
                    if d.is_dir() and not d.name.startswith('.') and not d.name.startswith('_')]

    for doc_dir in doc_dirs:
        doc_name = doc_dir.name
        print(f"\n[{doc_name[:30]}]")
        result = build_for_doc(doc_name)
        if result is None:
            continue

        for sid, instances in result.items():
            all_scenarios[sid][doc_name] = instances
            print(f"  场景{sid}: {len(instances)}个实例")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总:")
    for sid in [1, 2, 3, 4, 5, 6, 7, 8, "unclassified"]:
        if sid in all_scenarios:
            total = sum(len(insts) for insts in all_scenarios[sid].values())
            doc_count = len(all_scenarios[sid])
            print(f"  场景{sid}: {total}个实例, {doc_count}份文档")
        else:
            print(f"  场景{sid}: 0个实例")

    # 保存
    output = {
        "description": "语义层数据 — 按8个模态场景组织(仅收集,不做检测)",
        "scenarios": dict(all_scenarios),
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n保存: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
