#!/usr/bin/env python3
"""
Pair Dataset 重建脚本（修复版）

修复内容:
1. 数据源: mineru_correct(已删) → mineru_standard
2. 表格清洗: 过滤表头行(序号/项目唯一标识符/需求描述等), 只保留功能行
3. 正文补全: 从同章节提取完整段落(不只前200字), 保留所有正文
4. 质量分级: strong/medium/weak/none 四级
   - strong: 图注与表注有共同功能关键词
   - medium: 同章节且表型匹配, 但无共同关键词
   - weak:   仅有同章节关联
5. 图片校验: 检查image.png真实存在, 缺失的标记

用法: python3 tools/build_pair_dataset.py --doc 03
      python3 tools/build_pair_dataset.py --all
"""
import json
import re
import shutil
import argparse
from pathlib import Path
from collections import defaultdict
from html.parser import HTMLParser

BASE = Path(__file__).resolve().parent.parent
SRC_DIR = BASE / "data/gjb_438c/mineru_standard"     # 修复1: 数据源
OUT_DIR = BASE / "data/gjb_438c/pair_dataset"          # 输出
META_OUT = BASE / "data/gjb_438c/data_assets/semantic_modality_data.json"

SECTION_RE = re.compile(r'^(\d+(?:\.\d+)*)\s+(.+)')
CAPTION_RE = re.compile(r'(图|表)\s*(\d+)\s*(.*)')

# 表头噪音词(修复2: 过滤)
HEADER_NOISE = {
    '序号', '项目唯一标识符', '需求描述', '需求重用', '方式名称', '运行方式',
    '对应的任务书功能/性能', '备注', '编号', '名称/标识', '子功能名称/标识',
    '功能名称/标识', 'use case名称', 'usecase名称', 'use case 名称', 'usecase 名称',
    '功能', '子功能', '标识', '名称', '说明', '适用性', '等级', '优先级',
    'requirement id', 'description', '序号/项目唯一标识符/需求描述',
    '需求 重用', '方式 名称', '运行状态', '运行 方式', '对应的任务书功能/性能',
}


class TP(HTMLParser):
    """HTML表格解析器"""
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


def clean_table_rows(rows):
    """修复2: 清洗表格 — 去掉表头行和空行, 只保留功能数据行

    规则:
    1. 第一行通常是表头(序号/名称/标识...) → 检测为表头则跳过
    2. 行内所有单元格都是噪音词 → 跳过
    3. 行内无任何中文功能名(纯数字/纯ID) → 跳过
    """
    if not rows:
        return []
    cleaned = []
    for row in rows:
        cells = [str(c).strip() for c in row if str(c).strip()]
        if not cells:
            continue
        # 表头检测1: 行内含"序号"或整行都是表头词
        if '序号' in cells or (len(cells) >= 3 and all(
                any(n in c for n in ['标识', '名称', '描述', '重用', '方式', '运行', '备注', '任务书'])
                for c in cells)):
            continue
        # 表头检测2: 所有非空单元格都是噪音词
        non_noise = [c for c in cells if c not in HEADER_NOISE]
        if not non_noise:
            continue
        # 至少有一个单元格含中文功能名(2字以上)
        has_cn = any(re.search(r'[\u4e00-\u9fff]{2,}', c) for c in cells)
        if not has_cn:
            continue
        cleaned.append(row)
    return cleaned


def extract_func_names(rows):
    """从清洗后的表格行提取功能名列表

    功能名 = 每行第一个非ID、非纯数字的中文单元格(去ID后缀)
    """
    names = []
    for row in rows:
        for cell in row:
            cell = str(cell).strip()
            # 跳过纯ID/纯数字/空
            if not cell or cell == '—' or cell == '-':
                continue
            if re.match(r'^[A-Z0-9\-]+$', cell):
                continue
            # 提取中文名(去掉ID部分)
            m = re.search(r'([\u4e00-\u9fff][\u4e00-\u9fff/（）()]{1,20})', cell)
            if m:
                name = m.group(1).split('/')[0].strip()
                # 过滤: 纯表头词/过短/含"描述"长文本
                if (len(name) >= 2 and name not in HEADER_NOISE
                        and not any(k in name for k in ['描述', '标识符', '重用'])
                        and name not in {'需求'}):
                    names.append(name)
                    break  # 每行取第一个功能名
    return names


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
    headers_text = ' '.join(str(h) for h in headers)
    all_text = (caption + ' ' + headers_text).lower()

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

    if '项目唯一标识符' in headers_text or '需求重用' in headers_text:
        return 'capability'
    if 'actor' in all_text or 'actors' in all_text:
        return 'usecase'
    if ('use case' in all_text or 'usecase' in all_text) and '能力标识' not in caption:
        if any(kw in all_text for kw in ['主事件流', 'actor的动作', '系统的动作', '动作约束']):
            return 'usecase'
        return 'capability'

    if any(kw in all_text for kw in ['接口需求名称', '接口名称', '接口需求标识', '接口描述']):
        return 'interface'
    if any(kw in all_text for kw in ['数据集名称', '数据组成']):
        return 'data_spec'
    if any(kw in all_text for kw in ['设备名称', '硬件要求', '软件要求']):
        return 'environment'
    if any(kw in all_text for kw in ['功能名称', '子功能', '功能标识']):
        return 'capability'
    return 'other'


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
    """从content_list收集条目, 标注section"""
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

        item = {"section": current_section, "section_title": current_title}

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

            # 修复2: 清洗表格行
            clean_rows = clean_table_rows(rows)

            table_num = None
            cap_m = CAPTION_RE.match(caption)
            if cap_m and cap_m.group(1) == '表':
                table_num = int(cap_m.group(2))

            item["type"] = "table"
            item["table_type"] = ttype
            item["caption"] = caption
            item["table_num"] = table_num
            item["headers"] = [str(h)[:30] for h in headers[:8]]
            item["rows"] = [[str(c)[:60] for c in row[:8]] for row in clean_rows[:20]]
            item["row_count"] = len(clean_rows)
            item["func_names"] = extract_func_names(clean_rows)  # 修复2: 功能名
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
            item["path"] = raw_item.get('image_path', '')
            items.append(item)

    return items


def extract_keywords(text):
    if not text:
        return set()
    text = re.sub(r'^[图表]\s*\d+\s*', '', text)
    words = set()
    for m in re.finditer(r'[\u4e00-\u9fa5]{2,4}', text):
        words.add(m.group(0))
    generic = {'用例图', '流程图', '接口图', '功能图', '活动图', '框架图', '状态图',
               '用例描述', '所有能力', '能力标识', '外部接口', '内部接口', '接口需求',
               '接口标识', '功能划分', '运行流程', '组成图', '设计', '需求规格', '说明',
               '软件需求', '规格说明', '终稿', '功能'}
    return words - generic


def _pick_text(section_texts, img_idx, table_item=None, items=None, img_section=None):
    """选择正文: 优先含功能名的段落, 否则取同章节最长段落

    改进: 之前取"最近的正文"导致只拿到"见图N"引导句,
    现在优先找真正描述功能的段落; 同章节找不到时向下找子章节
    """
    if not section_texts:
        return None
    # 优先: 含表格功能名的正文段
    if table_item:
        func_names = table_item.get("func_names", [])
        for _, t in section_texts:
            content = t.get("content", "")
            hits = sum(1 for n in func_names if n and n in content)
            if hits >= 2:  # 至少2个功能名命中 → 这是真正的功能描述
                return t
    # 次选: 同章节最长的正文段
    best = max(section_texts, key=lambda x: len(x[1].get("content", "")))[1]
    if len(best.get("content", "")) > 80:
        return best

    # 兜底: 找兄弟章节/子章节中含功能名的正文
    # GJB结构: 父章节放图+表(如3.2.1.2), 功能描述在兄弟/子章节(3.2.1.3, 3.2.1.3.1)
    if items is not None and img_section and table_item:
        func_names = table_item.get("func_names", [])
        if func_names:
            parent_prefix = ".".join(img_section.split(".")[:-1])  # 3.2.1.2 → 3.2.1
            for i, item in enumerate(items):
                if item.get("type") != "text":
                    continue
                sec = item.get("section", "")
                # 兄弟或子章节: 同一父章节下, 但不是自己
                if (sec != img_section and sec.startswith(parent_prefix)
                        and len(sec) >= len(img_section)):
                    content = item.get("content", "")
                    hits = sum(1 for n in func_names if n and n in content)
                    if hits >= 1 and len(content) > 50:
                        return item
    return best


def find_contextual_table_and_text(items, img_idx, img_path_real):
    """为图片找上下文关联的表格和正文"""
    img_item = items[img_idx]
    img_section = img_item["section"]
    img_type = img_item.get("image_type", "unknown")
    img_caption = img_item.get("caption", "")

    if not img_section:
        return None, None, "none"

    sections_to_check = [img_section]
    parts = img_section.split('.')
    for n in range(len(parts) - 1, 1, -1):
        parent = '.'.join(parts[:n])
        if parent not in sections_to_check:
            sections_to_check.append(parent)

    required_table_types = set()
    for sid, combos in SCENARIO_MAP.items():
        for req_img, req_table in combos:
            if img_type == req_img:
                required_table_types.add(req_table)

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

        # 优先级1: 同section + 表型匹配 + 关键词匹配 → strong
        for _, tbl in section_tables:
            if tbl.get("table_type") in required_table_types:
                tbl_keywords = extract_keywords(tbl.get("caption", ""))
                if img_keywords & tbl_keywords:
                    nearest_text = _pick_text(section_texts, img_idx, tbl, items, img_section)
                    return tbl, nearest_text, "strong"

        # 优先级2: 同section + 表型匹配(无关键词) → medium
        for _, tbl in section_tables:
            if tbl.get("table_type") in required_table_types:
                nearest_text = _pick_text(section_texts, img_idx, tbl, items, img_section)
                return tbl, nearest_text, "medium"

        # 优先级3: 同section + 关键词匹配(表型不匹配) → medium
        for _, tbl in section_tables:
            tbl_keywords = extract_keywords(tbl.get("caption", ""))
            if img_keywords & tbl_keywords:
                nearest_text = _pick_text(section_texts, img_idx, tbl, items, img_section)
                return tbl, nearest_text, "medium"

        # 优先级4: 同section最近表格 → weak
        nearest_table = min(section_tables, key=lambda x: abs(x[0] - img_idx))[1]
        nearest_text = _pick_text(section_texts, img_idx, nearest_table, items, img_section)
        return nearest_table, nearest_text, "weak"

    return None, None, "none"


def build_for_doc(doc_dir):
    """构建单份文档的pair数据"""
    doc_name = doc_dir.name
    office_dir = doc_dir / "office"
    cl_path = office_dir / f"{doc_name}_content_list.json"
    if not cl_path.exists():
        cl_path = office_dir / f"{doc_name}_content_list_v2.json"
    if not cl_path.exists():
        print(f"  ✗ content_list不存在: {doc_name}")
        return {}

    cl = json.loads(cl_path.read_text())
    items = collect_items(cl)

    # 图片真实路径
    img_base = office_dir / "images"

    scenarios = defaultdict(list)

    for i, item in enumerate(items):
        if item["type"] != "image":
            continue

        img_type = item.get("image_type", "unknown")
        table_item, text_item, quality = find_contextual_table_and_text(items, i, None)

        # 图片真实存在性(修复3)
        img_rel = item.get("path", "")
        img_exists = False
        if img_rel:
            img_path = office_dir / img_rel   # image_path是相对office的, 如 images/fig_001.png
            img_exists = img_path.exists() and img_path.stat().st_size > 500
        elif item.get("fig_num"):
            # 尝试按编号找
            for cand in img_base.glob(f"fig_*{item['fig_num']:03d}.png"):
                img_exists = cand.exists() and cand.stat().st_size > 500
                break

        instance = {
            "doc": doc_name,
            "section": item["section"],
            "section_title": item["section_title"],
            "image": {
                "caption": item.get("caption", ""),
                "image_type": img_type,
                "fig_num": item.get("fig_num"),
                "path": item.get("path", ""),
                "exists": img_exists,
            },
            "table": None,
            "text": None,
            "match_quality": quality,
            "match_keywords": []
        }

        if table_item:
            instance["table"] = {
                "caption": table_item.get("caption", ""),
                "table_type": table_item.get("table_type", ""),
                "table_num": table_item.get("table_num"),
                "headers": table_item.get("headers", []),
                "row_count": table_item.get("row_count", 0),
                "rows": table_item.get("rows", []),
                "func_names": table_item.get("func_names", []),  # 修复2
            }
            img_kw = extract_keywords(item.get("caption", ""))
            tbl_kw = extract_keywords(table_item.get("caption", ""))
            common = sorted(img_kw & tbl_kw)
            if common:
                instance["match_quality"] = "strong"
                instance["match_keywords"] = common

        if text_item:
            instance["text"] = {
                "content": text_item.get("content", "")[:500]  # 修复3: 500字
            }

        # 场景匹配
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
            scenarios[8].append(instance)
        else:
            scenarios["unclassified"].append(instance)

    return dict(scenarios)


def materialize_pairs(scenarios, doc_name):
    """把场景实例落盘为pair_dataset文件结构"""
    created = 0
    for sid, instances in scenarios.items():
        if sid == "unclassified":
            continue
        sc_dir = OUT_DIR / f"sc{sid}_{SCENARIO_NAMES[sid]}"
        sc_dir.mkdir(parents=True, exist_ok=True)

        # 已有实例数(续编号): 目录名是 sid_next 格式(如1_001), 取next部分
        existing = [d for d in sc_dir.iterdir() if d.is_dir() and len(d.name.split('_')) >= 2
                    and d.name.split('_')[1].isdigit()]
        next_num = max((int(d.name.split('_')[1]) for d in existing), default=0) + 1

        for inst in instances:
            if not inst["image"].get("exists"):
                continue  # 图片不存在不落盘
            inst_dir = sc_dir / f"{sid}_{next_num:03d}"
            if inst_dir.exists():
                print(f"  ⚠ 目录冲突跳过: {inst_dir}")
                next_num += 1
                continue
            inst_dir.mkdir()
            inst_id = f"{sid}_{next_num:03d}"

            # 图片
            office_dir_src = SRC_DIR / doc_name / "office"
            img_rel = inst["image"].get("path", "")
            src_img = office_dir_src / img_rel if img_rel else None
            if src_img and src_img.exists():
                shutil.copy2(src_img, inst_dir / "image.png")

            # 表格 → CSV
            if inst.get("table"):
                with open(inst_dir / "table.csv", "w", encoding="utf-8") as f:
                    tbl = inst["table"]
                    # 表头
                    if tbl.get("headers"):
                        f.write(",".join(str(h).replace(',', ' ') for h in tbl["headers"]) + "\n")
                    # 数据行
                    for row in tbl.get("rows", []):
                        f.write(",".join(str(c).replace(',', ' ') for c in row) + "\n")

            # 正文
            if inst.get("text"):
                with open(inst_dir / "text.txt", "w", encoding="utf-8") as f:
                    f.write(inst["text"]["content"])

            # meta
            meta = {
                "instance_id": inst_id,
                "scenario": str(sid),
                "doc": inst["doc"],
                "section": inst["section"],
                "section_title": inst.get("section_title", ""),
                "image_caption": inst["image"]["caption"],
                "image_file": "image.png",
                "table_caption": inst["table"]["caption"] if inst.get("table") else "",
                "table_file": "table.csv" if inst.get("table") else "",
                "text_file": "text.txt" if inst.get("text") else "",
                "match_quality": inst["match_quality"],
                "match_keywords": inst["match_keywords"],
                "func_names": inst["table"]["func_names"] if inst.get("table") else [],
                "image_exists": inst["image"]["exists"],
            }
            with open(inst_dir / "meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            created += 1
            next_num += 1
    return created


SCENARIO_NAMES = {
    1: "usecase_capability", 2: "flowchart_usecase", 3: "interface_interface",
    4: "flowchart_capability", 5: "function_capability", 6: "framework_other",
    7: "usecase_usecase", 8: "pure_image",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc", help="只跑指定文档(如03)")
    parser.add_argument("--all", action="store_true", help="跑全部")
    args = parser.parse_args()

    print("=" * 60)
    print("Pair Dataset 重建(修复版) — mineru_standard数据源")
    print("=" * 60)

    doc_dirs = []
    if args.doc:
        doc_dirs = [d for d in sorted(SRC_DIR.iterdir())
                    if d.is_dir() and d.name.startswith(args.doc)]
    else:
        doc_dirs = [d for d in sorted(SRC_DIR.iterdir()) if d.is_dir()]

    all_scenarios = defaultdict(lambda: defaultdict(list))
    total_created = 0

    for doc_dir in doc_dirs:
        print(f"\n[{doc_dir.name[:30]}]")
        result = build_for_doc(doc_dir)
        if not result:
            continue
        for sid, instances in result.items():
            all_scenarios[sid][doc_dir.name] = instances
            print(f"  场景{sid}: {len(instances)}个实例")
        n = materialize_pairs(result, doc_dir.name)
        total_created += n
        print(f"  → 落盘{n}个文件实例")

    # 汇总
    print(f"\n{'='*60}")
    print("汇总(内存):")
    for sid in [1, 2, 3, 4, 5, 6, 7, 8]:
        if sid in all_scenarios:
            total = sum(len(insts) for insts in all_scenarios[sid].values())
            doc_count = len(all_scenarios[sid])
            print(f"  场景{sid}: {total}个实例, {doc_count}份文档")
    print(f"落盘文件实例总数: {total_created}")

    # 保存语义数据JSON
    output = {
        "description": "Pair Dataset语义数据(修复版) — 从mineru_standard重建",
        "source": "mineru_standard",
        "build_date": "2026-08-12",
        "scenarios": dict(all_scenarios),
        "stats": {str(sid): {"total": sum(len(v) for v in vs.values()),
                              "docs": len(vs)}
                  for sid, vs in all_scenarios.items()},
    }
    META_OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n保存: {META_OUT}")


if __name__ == "__main__":
    main()
