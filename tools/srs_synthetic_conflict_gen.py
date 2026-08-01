#!/usr/bin/env python3
"""
合成矛盾数据集生成器
基于3份GJB SRS(scheduler/compiler/battery)，通过合成注入矛盾的方式扩充Gold Standard。
生成5种类型的合成矛盾标注，总计150+个，每份文档约50个。
"""

import json
import os
import re
import copy
from collections import defaultdict
from html.parser import HTMLParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC_DIR = os.path.join(BASE_DIR, "data", "gjb_438c", "processed_documents")
OUT_DIR = os.path.join(BASE_DIR, "data", "gjb_438c", "gold_standard")

DOC_NAMES = ["scheduler_srs", "compiler_srs", "battery_srs"]

# GJB 438C 必需章节(语法层检测用)
GJB_REQUIRED_CHAPTERS = [
    ("1", "范围"), ("1.1", "标识"), ("1.2", "系统概述"), ("1.3", "文档概述"),
    ("2", "引用文档"),
    ("3", "需求"), ("3.1", "要求的状态和方式"),
    ("3.2", "软件能力需求"),
    ("3.3", "软件外部接口需求"),
    ("3.4", "软件内部接口需求"),
    ("3.5", "软件内部数据需求"),
    ("3.6", "适应性需求"), ("3.7", "安全性需求"), ("3.8", "保密性需求"),
    ("3.9", "软件环境需求"),
    ("3.10", "计算机资源需求"),
    ("3.10.1", "计算机硬件需求"), ("3.10.2", "计算机硬件资源使用需求"),
    ("3.10.3", "计算机软件需求"), ("3.10.4", "计算机通信需求"),
    ("3.11", "软件质量因素"),
    ("3.12", "设计和实现约束"),
    ("3.13", "人员需求"), ("3.14", "培训需求"), ("3.15", "软件保障需求"),
    ("3.16", "其他需求"), ("3.17", "验收、交付和包装需求"),
    ("3.18", "需求的优先顺序和关键程度"),
    ("4", "合格性规定"),
    ("5", "需求可追踪性"),
    ("6", "注释"),
]


class TableParser(HTMLParser):
    """解析HTML表格，返回二维列表"""
    def __init__(self):
        super().__init__()
        self.rows = []
        self._cur_row = []
        self._cur_cell = ""
        self._in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._cur_row = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._cur_cell = ""

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self._in_cell = False
            self._cur_row.append(self._cur_cell.strip())
        elif tag == "tr":
            if self._cur_row:
                self.rows.append(self._cur_row)

    def handle_data(self, data):
        if self._in_cell:
            self._cur_cell += data


def parse_table_html(raw_html):
    """解析表格HTML为行列表"""
    p = TableParser()
    try:
        p.feed(raw_html)
    except Exception:
        pass
    return p.rows


def load_doc(name):
    path = os.path.join(PROC_DIR, f"{name}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_param_groups(doc):
    """
    从constraints和llm_constraints中提取参数组。
    返回: {param_key: [{section, value, unit, sentence, param, operator}]}
    param_key = (value, unit) 用于匹配同值同单位参数
    """
    groups = defaultdict(list)

    # 从regex constraints提取
    for c in doc.get("constraints", []):
        val = c.get("value")
        unit = c.get("unit", "")
        sec = c.get("section_number") or c.get("section", "")
        if val is None or sec is None:
            continue
        key = (val, unit)
        groups[key].append({
            "section": sec,
            "value": val,
            "unit": unit,
            "operator": c.get("operator", "="),
            "sentence": c.get("sentence", ""),
            "param": "",
            "source": "regex",
        })

    # 从llm_constraints提取数值约束
    for c in doc.get("llm_constraints", []):
        ctype = c.get("type", "")
        val = c.get("value")
        unit = c.get("unit", "")
        sec = c.get("section_number") or c.get("section", "")
        param = c.get("param", "")

        if ctype == "numerical" and val is not None and sec:
            key = (val, unit)
            groups[key].append({
                "section": sec,
                "value": val,
                "unit": unit,
                "operator": c.get("operator", "≤"),
                "sentence": c.get("original", ""),
                "param": param,
                "source": "llm_numerical",
            })
        elif ctype in ("design", "default") and val is not None and sec:
            # 尝试提取数值
            if isinstance(val, (int, float)):
                key = (val, unit)
                groups[key].append({
                    "section": sec,
                    "value": val,
                    "unit": unit,
                    "operator": "=",
                    "sentence": c.get("original", ""),
                    "param": param,
                    "source": "llm_design",
                })

    return groups


def extract_numerical_constraints(doc):
    """提取所有数值约束(带operator)，用于逻辑矛盾生成"""
    results = []

    for c in doc.get("constraints", []):
        val = c.get("value")
        unit = c.get("unit", "")
        sec = c.get("section_number") or c.get("section", "")
        op = c.get("operator", "")
        if val is not None and sec and op:
            results.append({
                "section": sec,
                "value": val,
                "unit": unit,
                "operator": op,
                "sentence": c.get("sentence", ""),
                "param": "",
            })

    for c in doc.get("llm_constraints", []):
        if c.get("type") == "numerical":
            val = c.get("value")
            unit = c.get("unit", "")
            sec = c.get("section_number") or c.get("section", "")
            op = c.get("operator", "≤")
            if val is not None and sec:
                results.append({
                    "section": sec,
                    "value": val,
                    "unit": unit,
                    "operator": op,
                    "sentence": c.get("original", ""),
                    "param": c.get("param", ""),
                })

    return results


def extract_table_data(doc):
    """提取合格性表和追踪表数据"""
    tables = []
    for t in doc.get("tables", []):
        if t["type"] in ("qualification", "traceability"):
            rows = parse_table_html(t.get("raw_html", ""))
            tables.append({
                "type": t["type"],
                "section": t.get("section", ""),
                "index": t.get("index", 0),
                "rows": rows,
                "headers": t.get("headers", []),
            })
    return tables


def extract_req_ids(doc):
    """从合格性表中提取REQ-ID及其关联信息"""
    req_ids = []
    for t in doc.get("tables", []):
        if t["type"] == "qualification":
            rows = parse_table_html(t.get("raw_html", ""))
            for row in rows:
                for cell in row:
                    m = re.match(r"REQ-([\d.]+)", cell.strip())
                    if m:
                        req_ids.append({
                            "req_id": cell.strip(),
                            "row": row,
                            "table_section": t.get("section", ""),
                        })
    return req_ids


def extract_sections(doc):
    """提取章节列表"""
    sections = []
    for s in doc.get("sections", []):
        if s.get("number"):
            sections.append({
                "number": s["number"],
                "title": s.get("title", ""),
                "text_length": s.get("text_length", 0),
            })
    return sections


def lookup_param_name(doc, value, unit, section):
    """从llm_constraints中查找参数名称"""
    for c in doc.get("llm_constraints", []):
        cval = c.get("value")
        cunit = c.get("unit", "")
        csec = c.get("section_number") or c.get("section", "")
        param = c.get("param", "")
        if not param:
            continue
        # 尝试数值匹配
        if isinstance(cval, (int, float)) and cval == value:
            if not unit or not cunit or unit == cunit:
                return param
        # 尝试从字符串值中提取数值匹配
        if isinstance(cval, str):
            num_match = re.search(r"[\d.]+", cval)
            if num_match:
                try:
                    cval_num = float(num_match.group())
                    if cval_num == value:
                        # 检查单位是否兼容
                        cval_unit = re.sub(r"[\d.\s]+", "", cval).strip()
                        if not unit or not cval_unit or unit in cval_unit or cval_unit in unit:
                            return param
                except ValueError:
                    pass
        # 尝试section匹配
        if csec and section and csec == section:
            # 检查原始文本中是否包含该值
            orig = c.get("original", "")
            if orig and str(value) in orig:
                return param
    return ""


# ============================================================
# 矛盾生成器
# ============================================================

def gen_same_param_diff_value(doc_name, doc, count=10, start_id=0):
    """
    类型1: 同参数不同值(语义层)
    找到在多个章节出现的参数，生成一个修改版将某处值改为不同值。
    """
    conflicts = []
    groups = extract_param_groups(doc)

    # 筛选: 同值同单位出现在2+章节的参数组
    multi_section_groups = {
        k: v for k, v in groups.items()
        if len(v) >= 2 and k[0] is not None
    }

    # 按值排序，优先选择有明确数值的
    sorted_keys = sorted(
        multi_section_groups.keys(),
        key=lambda k: (len(multi_section_groups[k]), k[0]),
        reverse=True,
    )

    idx = start_id
    used_combos = set()

    for key in sorted_keys:
        if len(conflicts) >= count:
            break
        val, unit = key
        occurrences = multi_section_groups[key]

        # 对每组中每对(原始位置, 修改位置)生成一个矛盾
        for i in range(len(occurrences)):
            if len(conflicts) >= count:
                break
            orig = occurrences[i]
            # 选择另一个位置作为"保持不变"的参照
            j = (i + 1) % len(occurrences)
            ref = occurrences[j]

            combo = (orig["section"], ref["section"], val, unit)
            if combo in used_combos:
                continue
            used_combos.add(combo)

            # 生成修改值: 根据原始值生成一个不同的值
            mod_val = _generate_diff_value(val)

            param_desc = orig.get("param", "") or lookup_param_name(doc, val, unit, orig["section"]) or f"参数值{val}{unit}"
            desc = (
                f"{param_desc}在{orig['section']}为{val}{unit}，"
                f"但在修改版中被改为{mod_val}{unit}，"
                f"与{ref['section']}处的{val}{unit}不一致"
            )

            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "same_param_diff_value",
                "layer": "semantic",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {
                    "sections": [orig["section"], ref["section"]],
                },
                "original_value": f"{val}{unit}",
                "modified_value": f"{mod_val}{unit}",
                "original_sentence": orig.get("sentence", "")[:200],
                "note": f"合成矛盾: 将{orig['section']}处的{val}{unit}改为{mod_val}{unit}，与{ref['section']}不一致",
            })
            idx += 1

    # 如果不够，从单出现参数也生成
    if len(conflicts) < count:
        for key in sorted_keys:
            if len(conflicts) >= count:
                break
            val, unit = key
            for occ in groups[key]:
                if len(conflicts) >= count:
                    break
                combo = (occ["section"], val, unit)
                if combo in used_combos:
                    continue
                used_combos.add(combo)

                mod_val = _generate_diff_value(val)
                param_desc = occ.get("param", "") or lookup_param_name(doc, val, unit, occ["section"]) or f"参数值{val}{unit}"
                desc = (
                    f"{param_desc}在{occ['section']}为{val}{unit}，"
                    f"但在修改版中被改为{mod_val}{unit}，"
                    f"与其他章节引用的{val}{unit}不一致"
                )

                conflicts.append({
                    "gt_id": f"SYN-{idx:03d}",
                    "doc_name": doc_name,
                    "type": "same_param_diff_value",
                    "layer": "semantic",
                    "is_conflict": True,
                    "severity": "HIGH",
                    "description": desc,
                    "location": {"sections": [occ["section"]]},
                    "original_value": f"{val}{unit}",
                    "modified_value": f"{mod_val}{unit}",
                    "original_sentence": occ.get("sentence", "")[:200],
                    "note": f"合成矛盾: 将{occ['section']}处的{val}{unit}改为{mod_val}{unit}",
                })
                idx += 1

    return conflicts


def _generate_diff_value(val):
    """根据原始值生成一个不同的修改值"""
    if isinstance(val, (int, float)):
        if val == 0:
            return 1
        if val < 1 and val > 0:
            # 小数: 放大2倍
            return round(val * 2, 6)
        if val < 10:
            return val + 5
        if val < 100:
            return val + 20
        if val < 1000:
            return val + 200
        return val + 2000
    return val


def gen_text_table_conflict(doc_name, doc, count=10, start_id=0):
    """
    类型2: 文本-表格矛盾(语义层)
    找到合格性表/追踪表中的值，生成修改版将表格中的值改掉。
    """
    conflicts = []
    tables = extract_table_data(doc)
    idx = start_id

    # 1. 合格性表: 修改REQ-ID、章节号、合格性方法、合格性级别
    for t in tables:
        if t["type"] != "qualification":
            continue
        rows = t["rows"]
        for row in rows:
            if len(conflicts) >= count:
                break
            # 跳过表头行
            req_cell = None
            sec_cell = None
            method_cell = None
            level_cell = None
            name_cell = None
            for cell in row:
                if re.match(r"REQ-[\d.]+", cell.strip()):
                    req_cell = cell.strip()
                elif re.match(r"^[\d.]+$", cell.strip()) and len(cell.strip()) <= 8:
                    sec_cell = cell.strip()
                elif cell.strip() in ("关键", "一般", "低", "高"):
                    level_cell = cell.strip()

            if not req_cell and not sec_cell:
                continue

            # 生成修改版
            if req_cell:
                orig_val = req_cell
                mod_val = _modify_req_id(req_cell)
                desc = (
                    f"合格性规定表(章节4)中需求标识'{orig_val}'"
                    f"在修改版中被改为'{mod_val}'，"
                    f"与正文中对应需求的标识不一致"
                )
                conflicts.append({
                    "gt_id": f"SYN-{idx:03d}",
                    "doc_name": doc_name,
                    "type": "text_table_conflict",
                    "layer": "semantic",
                    "is_conflict": True,
                    "severity": "HIGH",
                    "description": desc,
                    "location": {"sections": ["4"], "table_type": "qualification"},
                    "original_value": orig_val,
                    "modified_value": mod_val,
                    "note": f"合成矛盾: 合格性表中REQ-ID {orig_val}→{mod_val}",
                })
                idx += 1

            if len(conflicts) >= count:
                break

            if sec_cell:
                orig_val = sec_cell
                mod_val = _modify_section_number(sec_cell)
                desc = (
                    f"合格性规定表(章节4)中章节号'{orig_val}'"
                    f"在修改版中被改为'{mod_val}'，"
                    f"与正文中实际需求章节号不一致"
                )
                conflicts.append({
                    "gt_id": f"SYN-{idx:03d}",
                    "doc_name": doc_name,
                    "type": "text_table_conflict",
                    "layer": "semantic",
                    "is_conflict": True,
                    "severity": "HIGH",
                    "description": desc,
                    "location": {"sections": ["4"], "table_type": "qualification"},
                    "original_value": orig_val,
                    "modified_value": mod_val,
                    "note": f"合成矛盾: 合格性表中章节号 {orig_val}→{mod_val}",
                })
                idx += 1

            if len(conflicts) >= count:
                break

            # 合格性方法修改
            methods = [c for c in row if c.strip() and not re.match(r"REQ-[\d.]+", c.strip())
                       and not re.match(r"^[\d.]+$", c.strip())
                       and c.strip() not in ("关键", "一般", "低", "高")
                       and "需求名称" not in c and "唯一标识" not in c
                       and "章节号" not in c and "合格性方法" not in c
                       and "合格性级别" not in c and "注" not in c]
            if methods:
                orig_val = methods[0].strip()
                mod_val = _modify_method(orig_val)
                desc = (
                    f"合格性规定表(章节4)中合格性方法'{orig_val}'"
                    f"在修改版中被改为'{mod_val}'，"
                    f"与实际需求应采用的验证方法不一致"
                )
                conflicts.append({
                    "gt_id": f"SYN-{idx:03d}",
                    "doc_name": doc_name,
                    "type": "text_table_conflict",
                    "layer": "semantic",
                    "is_conflict": True,
                    "severity": "MEDIUM",
                    "description": desc,
                    "location": {"sections": ["4"], "table_type": "qualification"},
                    "original_value": orig_val,
                    "modified_value": mod_val,
                    "note": f"合成矛盾: 合格性方法 {orig_val}→{mod_val}",
                })
                idx += 1

    # 2. 追踪表: 修改追踪关系中的章节号或指标内容
    for t in tables:
        if t["type"] != "traceability":
            continue
        if len(conflicts) >= count:
            break
        rows = t["rows"]
        for row in rows:
            if len(conflicts) >= count:
                break
            for cell in row:
                if len(conflicts) >= count:
                    break
                # 修改追踪表中的章节号
                m = re.match(r"^(3\.\d+(?:\.\d+)?)$", cell.strip())
                if m:
                    orig_val = cell.strip()
                    mod_val = _modify_section_number(orig_val)
                    desc = (
                        f"需求可追踪性表(章节5)中需求章节号'{orig_val}'"
                        f"在修改版中被改为'{mod_val}'，"
                        f"与正文中实际需求定义的章节号不一致"
                    )
                    conflicts.append({
                        "gt_id": f"SYN-{idx:03d}",
                        "doc_name": doc_name,
                        "type": "text_table_conflict",
                        "layer": "semantic",
                        "is_conflict": True,
                        "severity": "HIGH",
                        "description": desc,
                        "location": {"sections": ["5"], "table_type": "traceability"},
                        "original_value": orig_val,
                        "modified_value": mod_val,
                        "note": f"合成矛盾: 追踪表章节号 {orig_val}→{mod_val}",
                    })
                    idx += 1

                # 修改追踪表中的数值指标(如25ms)
                m2 = re.search(r"(\d+(?:\.\d+)?\s*(?:ms|s|MHz|MB|KB|V|A|Ω|%))", cell)
                if m2 and len(conflicts) < count:
                    orig_val = m2.group(1).strip()
                    num_match = re.match(r"([\d.]+)", orig_val)
                    if num_match:
                        num = float(num_match.group(1))
                        mod_num = _generate_diff_value(num)
                        unit = re.sub(r"[\d.\s]+", "", orig_val)
                        mod_val = f"{mod_num}{unit}"
                        desc = (
                            f"需求可追踪性表(章节5)中指标'{cell.strip()[:50]}'"
                            f"包含值'{orig_val}'，在修改版中被改为'{mod_val}'，"
                            f"与正文中的参数值不一致"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "text_table_conflict",
                            "layer": "semantic",
                            "is_conflict": True,
                            "severity": "HIGH",
                            "description": desc,
                            "location": {"sections": ["5"], "table_type": "traceability"},
                            "original_value": orig_val,
                            "modified_value": mod_val,
                            "note": f"合成矛盾: 追踪表指标值 {orig_val}→{mod_val}",
                        })
                        idx += 1

    # 3. 如果还不够，生成需求名称修改矛盾
    if len(conflicts) < count:
        for t in tables:
            if len(conflicts) >= count:
                break
            if t["type"] != "qualification":
                continue
            for row in t["rows"]:
                if len(conflicts) >= count:
                    break
                for cell in row:
                    if len(conflicts) >= count:
                        break
                    c = cell.strip()
                    if (len(c) > 2 and not re.match(r"REQ-[\d.]+", c)
                            and not re.match(r"^[\d.]+$", c)
                            and c not in ("关键", "一般", "低", "高")
                            and "需求名称" not in c and "唯一标识" not in c
                            and "章节号" not in c and "合格性方法" not in c
                            and "合格性级别" not in c and "注" not in c
                            and "GB/T" not in c and "合规" not in c):
                        mod_val = c + "(修改)"
                        desc = (
                            f"合格性规定表(章节4)中需求名称'{c}'"
                            f"在修改版中被改为'{mod_val}'，"
                            f"与正文3.x章节中的需求名称不一致"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "text_table_conflict",
                            "layer": "semantic",
                            "is_conflict": True,
                            "severity": "MEDIUM",
                            "description": desc,
                            "location": {"sections": ["4"], "table_type": "qualification"},
                            "original_value": c,
                            "modified_value": mod_val,
                            "note": f"合成矛盾: 需求名称 {c}→{mod_val}",
                        })
                        idx += 1
                        break

    # 4. 如果还不够，生成占位符未替换矛盾(compiler_srs情况)和合格性级别修改矛盾
    if len(conflicts) < count:
        for t in tables:
            if len(conflicts) >= count:
                break
            if t["type"] != "qualification":
                continue
            for row in t["rows"]:
                if len(conflicts) >= count:
                    break
                for cell in row:
                    if len(conflicts) >= count:
                        break
                    c = cell.strip()
                    # 修改合格性级别
                    if c in ("关键", "一般"):
                        level_map = {"关键": "一般", "一般": "关键"}
                        mod_val = level_map[c]
                        desc = (
                            f"合格性规定表(章节4)中合格性级别'{c}'"
                            f"在修改版中被改为'{mod_val}'，"
                            f"与需求实际关键程度不匹配，影响验收优先级"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "text_table_conflict",
                            "layer": "semantic",
                            "is_conflict": True,
                            "severity": "MEDIUM",
                            "description": desc,
                            "location": {"sections": ["4"], "table_type": "qualification"},
                            "original_value": c,
                            "modified_value": mod_val,
                            "note": f"合成矛盾: 合格性级别 {c}→{mod_val}",
                        })
                        idx += 1
                    # 修改占位符内容
                    elif "GB/T" in c or "合规" in c:
                        mod_val = c.replace("GB/T", "GJB").replace("合规", "验证") if c else "已替换"
                        desc = (
                            f"合格性规定表(章节4)中占位符'{c}'"
                            f"在修改版中被改为'{mod_val}'，"
                            f"表格内容仍为模板占位符，未填写真实需求合格性数据"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "text_table_conflict",
                            "layer": "semantic",
                            "is_conflict": True,
                            "severity": "HIGH",
                            "description": desc,
                            "location": {"sections": ["4"], "table_type": "qualification"},
                            "original_value": c,
                            "modified_value": mod_val,
                            "note": f"合成矛盾: 占位符修改 {c}→{mod_val}",
                        })
                        idx += 1

    # 5. 如果还不够，从追踪表占位符内容生成矛盾
    if len(conflicts) < count:
        for t in tables:
            if len(conflicts) >= count:
                break
            if t["type"] != "traceability":
                continue
            for row in t["rows"]:
                if len(conflicts) >= count:
                    break
                for cell in row:
                    c = cell.strip()
                    # 追踪表中的占位符内容(如"指标内容"、"需求名称"、"章节号")
                    if c in ("指标内容", "需求名称", "章节号"):
                        mod_val = c + "(占位符)"
                        desc = (
                            f"需求可追踪性表(章节5)中'{c}'"
                            f"在修改版中仍为模板占位符'{mod_val}'，"
                            f"未填写实际追踪数据，无法建立需求与指标的双向映射"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "text_table_conflict",
                            "layer": "semantic",
                            "is_conflict": True,
                            "severity": "HIGH",
                            "description": desc,
                            "location": {"sections": ["5"], "table_type": "traceability"},
                            "original_value": c,
                            "modified_value": mod_val,
                            "note": f"合成矛盾: 追踪表占位符未替换 '{c}'",
                        })
                        idx += 1
                        break

    # 6. 如果还不够，从正文3.2.x需求中生成"表格遗漏需求行"矛盾
    if len(conflicts) < count:
        sections = extract_sections(doc)
        req_sections = [s for s in sections if s["number"] and s["number"].startswith("3.2.")
                        and s["text_length"] > 10]
        for sec in req_sections:
            if len(conflicts) >= count:
                break
            num = sec["number"]
            title = sec["title"]
            desc = (
                f"正文{num}({title})定义了软件能力需求，"
                f"但合格性规定表(章节4)在修改版中缺少该需求的合格性规定行，"
                f"导致该需求无合格性验证方法定义"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "text_table_conflict",
                "layer": "semantic",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": [num, "4"], "table_type": "qualification"},
                "original_value": f"REQ-{num}行存在",
                "modified_value": f"REQ-{num}行被删除",
                "note": f"合成矛盾: 合格性表遗漏{num}需求行",
            })
            idx += 1

    return conflicts


def _modify_req_id(req_id):
    """修改REQ-ID"""
    m = re.match(r"REQ-([\d.]+)", req_id)
    if m:
        parts = m.group(1).split(".")
        if len(parts) >= 2:
            parts[-1] = str(int(parts[-1]) + 5)
            return f"REQ-{'.'.join(parts)}"
    return "REQ-9.9.9"


def _modify_section_number(sec):
    """修改章节号"""
    parts = sec.split(".")
    if len(parts) >= 2:
        parts[-1] = str(int(parts[-1]) + 3)
        return ".".join(parts)
    return sec + ".9"


def _modify_method(method):
    """修改合格性方法"""
    replacements = {
        "单元测试": "演示验证",
        "集成测试": "代码审查",
        "功能测试": "形式化验证",
        "对比验证": "逻辑分析",
        "精度测量": "压力测试",
    }
    for k, v in replacements.items():
        if k in method:
            return method.replace(k, v)
    return method + "(变更)"


def gen_logic_unsatisfiable(doc_name, doc, count=10, start_id=0):
    """
    类型3: 逻辑不可满足(逻辑层)
    找到数值约束，生成修改版添加矛盾约束。
    """
    conflicts = []
    constraints = extract_numerical_constraints(doc)
    idx = start_id

    # 去重: 同一(section, value, unit, operator)只保留一个
    seen = set()
    unique_constraints = []
    for c in constraints:
        key = (c["section"], c["value"], c["unit"], c["operator"])
        if key not in seen:
            seen.add(key)
            unique_constraints.append(c)

    for c in unique_constraints:
        if len(conflicts) >= count:
            break
        val = c["value"]
        unit = c["unit"]
        op = c["operator"]
        sec = c["section"]
        param = c.get("param", "") or lookup_param_name(doc, val, unit, sec) or f"参数(值={val}{unit})"

        if op in ("≤", "<"):
            # 原约束: x ≤ val, 添加矛盾: x ≥ val*2
            mod_val = _generate_diff_value(val)
            mod_op = "≥"
            desc = (
                f"{sec}要求{param}{op}{val}{unit}，"
                f"但修改版在{sec}添加了矛盾约束{param}{mod_op}{mod_val}{unit}，"
                f"两个约束不可同时满足(需{op}{val}且{mod_op}{mod_val}, {val}<{mod_val})"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "logic_unsatisfiable",
                "layer": "logic",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": [sec]},
                "original_constraint": f"{param} {op} {val}{unit}",
                "added_constraint": f"{param} {mod_op} {mod_val}{unit}",
                "original_value": f"{val}{unit}",
                "modified_value": f"{mod_val}{unit}",
                "note": f"合成矛盾(逻辑不可满足): 原约束{op}{val}{unit} vs 新增约束{mod_op}{mod_val}{unit}, Z3求解结果为UNSAT",
            })
            idx += 1

        elif op in ("≥", ">"):
            # 原约束: x ≥ val, 添加矛盾: x ≤ val/2
            mod_val = val / 2 if val > 0 else 0
            if isinstance(val, int):
                mod_val = int(mod_val)
            mod_op = "≤"
            desc = (
                f"{sec}要求{param}{op}{val}{unit}，"
                f"但修改版在{sec}添加了矛盾约束{param}{mod_op}{mod_val}{unit}，"
                f"两个约束不可同时满足(需{op}{val}且{mod_op}{mod_val}, {val}>{mod_val})"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "logic_unsatisfiable",
                "layer": "logic",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": [sec]},
                "original_constraint": f"{param} {op} {val}{unit}",
                "added_constraint": f"{param} {mod_op} {mod_val}{unit}",
                "original_value": f"{val}{unit}",
                "modified_value": f"{mod_val}{unit}",
                "note": f"合成矛盾(逻辑不可满足): 原约束{op}{val}{unit} vs 新增约束{mod_op}{mod_val}{unit}, Z3求解结果为UNSAT",
            })
            idx += 1

        elif op in ("=",):
            # 原约束: x = val, 添加矛盾: x ≠ val (用 x = mod_val)
            mod_val = _generate_diff_value(val)
            desc = (
                f"{sec}要求{param}={val}{unit}，"
                f"但修改版在{sec}添加了矛盾约束{param}={mod_val}{unit}，"
                f"两个约束不可同时满足(同一参数被约束为两个不同的值)"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "logic_unsatisfiable",
                "layer": "logic",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": [sec]},
                "original_constraint": f"{param} = {val}{unit}",
                "added_constraint": f"{param} = {mod_val}{unit}",
                "original_value": f"{val}{unit}",
                "modified_value": f"{mod_val}{unit}",
                "note": f"合成矛盾(逻辑不可满足): 同一参数被约束为{val}{unit}和{mod_val}{unit}两个不同值, Z3求解结果为UNSAT",
            })
            idx += 1

    # 如果不够，生成跨章节逻辑矛盾
    if len(conflicts) < count:
        # 找执行时间约束和周期约束，生成"执行时间 > 周期"的矛盾
        exec_constraints = [c for c in unique_constraints if c["unit"] in ("ms", "秒", "s")
                           and c["operator"] in ("≤", "<") and c["value"] < 100]
        for ec in exec_constraints:
            if len(conflicts) >= count:
                break
            # 添加一个更大的下界约束
            mod_val = ec["value"] * 10
            if isinstance(ec["value"], int):
                mod_val = int(mod_val)
            param = ec.get("param", "") or lookup_param_name(doc, ec["value"], ec["unit"], ec["section"]) or "执行时间"
            desc = (
                f"{ec['section']}要求{param}{ec['operator']}{ec['value']}{ec['unit']}，"
                f"但修改版添加了矛盾约束{param}≥{mod_val}{ec['unit']}(新增3.12节)，"
                f"执行时间下界{mod_val}{ec['unit']}超过上界{ec['value']}{ec['unit']}，逻辑不可满足"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "logic_unsatisfiable",
                "layer": "logic",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": [ec["section"], "3.12"]},
                "original_constraint": f"{param} {ec['operator']} {ec['value']}{ec['unit']}",
                "added_constraint": f"{param} ≥ {mod_val}{ec['unit']}",
                "original_value": f"{ec['value']}{ec['unit']}",
                "modified_value": f"{mod_val}{ec['unit']}",
                "note": f"合成矛盾(逻辑不可满足): 执行时间上界{ec['value']}{ec['unit']} vs 下界{mod_val}{ec['unit']}, Z3=UNSAT",
            })
            idx += 1

    return conflicts


def gen_missing_chapter(doc_name, doc, count=10, start_id=0):
    """
    类型4: 章节缺失(语法层)
    生成缺少某个必需章节的版本。
    """
    conflicts = []
    sections = extract_sections(doc)
    existing_numbers = {s["number"] for s in sections}
    idx = start_id

    # 从GJB必需章节中筛选文档实际存在的章节
    existing_required = [
        (num, title) for num, title in GJB_REQUIRED_CHAPTERS
        if num in existing_numbers
    ]

    # 优先选择有实际内容的章节
    content_sections = [s for s in sections if s["text_length"] > 10]

    used = set()
    for sec in content_sections:
        if len(conflicts) >= count:
            break
        num = sec["number"]
        if num in used:
            continue
        used.add(num)

        # 找到对应的GJB章节标题
        gjb_title = ""
        for gn, gt in GJB_REQUIRED_CHAPTERS:
            if gn == num:
                gjb_title = gt
                break

        title = sec["title"]
        desc = (
            f"修改版缺少GJB 438C必需章节'{num} {gjb_title or title}'，"
            f"该章节在原文档中存在(内容长度{sec['text_length']}字符)，"
            f"缺失将导致SRS不符合GJB 438C格式规范"
        )

        conflicts.append({
            "gt_id": f"SYN-{idx:03d}",
            "doc_name": doc_name,
            "type": "missing_chapter",
            "layer": "syntax",
            "is_conflict": True,
            "severity": "HIGH",
            "description": desc,
            "location": {"sections": [num]},
            "missing_chapter": num,
            "missing_chapter_title": title,
            "original_text_length": sec["text_length"],
            "note": f"合成矛盾(章节缺失): 删除章节{num} {gjb_title or title}, 违反GJB 438C格式要求",
        })
        idx += 1

    # 如果不够，从所有必需章节中补充
    if len(conflicts) < count:
        for num, title in existing_required:
            if len(conflicts) >= count:
                break
            if num in used:
                continue
            used.add(num)

            # 找到section的text_length
            tl = 0
            for s in sections:
                if s["number"] == num:
                    tl = s["text_length"]
                    break

            desc = (
                f"修改版缺少GJB 438C必需章节'{num} {title}'，"
                f"该章节在原文档中存在，"
                f"缺失将导致SRS不符合GJB 438C格式规范"
            )

            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "missing_chapter",
                "layer": "syntax",
                "is_conflict": True,
                "severity": "MEDIUM",
                "description": desc,
                "location": {"sections": [num]},
                "missing_chapter": num,
                "missing_chapter_title": f"{num} {title}",
                "original_text_length": tl,
                "note": f"合成矛盾(章节缺失): 删除章节{num} {title}, 违反GJB 438C格式要求",
            })
            idx += 1

    return conflicts


def gen_missing_req_id(doc_name, doc, count=10, start_id=0):
    """
    类型5: 需求标识缺失(语法层)
    生成缺少REQ-ID的版本。
    """
    conflicts = []
    req_ids = extract_req_ids(doc)
    idx = start_id

    # 如果文档有REQ-ID，生成删除REQ-ID的矛盾
    if req_ids:
        for req in req_ids:
            if len(conflicts) >= count:
                break
            rid = req["req_id"]
            row = req["row"]

            # 提取需求名称
            name = ""
            for cell in row:
                c = cell.strip()
                if c and not re.match(r"REQ-[\d.]+", c) and not re.match(r"^[\d.]+$", c):
                    if c not in ("关键", "一般", "低", "高"):
                        name = c
                        break

            desc = (
                f"合格性规定表(章节4)中需求'{name}'的标识'{rid}'"
                f"在修改版中被删除(留空)，"
                f"导致该需求无法被唯一标识和追踪，违反GJB 438C需求标识规范"
            )

            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "missing_req_id",
                "layer": "syntax",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": ["4"], "table_type": "qualification"},
                "missing_req_id": rid,
                "requirement_name": name,
                "note": f"合成矛盾(需求标识缺失): 删除合格性表中的{rid}",
            })
            idx += 1

        # 生成REQ-ID格式错误的矛盾
        for req in req_ids:
            if len(conflicts) >= count:
                break
            rid = req["req_id"]
            # 生成格式错误的ID
            bad_ids = [
                rid.replace("REQ-", ""),
                rid.replace("REQ-", "req-"),
                rid.replace("REQ-", "REQ_"),
                "REQ-" + rid.replace("REQ-", "").replace(".", "-"),
            ]
            for bad_id in bad_ids:
                if len(conflicts) >= count:
                    break
                desc = (
                    f"合格性规定表(章节4)中需求标识'{rid}'"
                    f"在修改版中被改为格式错误的'{bad_id}'，"
                    f"不符合GJB 438C规定的REQ-X.Y.Z格式规范"
                )
                conflicts.append({
                    "gt_id": f"SYN-{idx:03d}",
                    "doc_name": doc_name,
                    "type": "missing_req_id",
                    "layer": "syntax",
                    "is_conflict": True,
                    "severity": "MEDIUM",
                    "description": desc,
                    "location": {"sections": ["4"], "table_type": "qualification"},
                    "original_req_id": rid,
                    "modified_req_id": bad_id,
                    "note": f"合成矛盾(需求标识格式错误): {rid}→{bad_id}",
                })
                idx += 1

    # 如果文档没有REQ-ID(如compiler_srs)或数量不够，生成"正文中有需求但合格性表缺少REQ-ID"的矛盾
    if len(conflicts) < count:
        sections = extract_sections(doc)
        req_sections = [s for s in sections if s["number"] and s["number"].startswith("3.2.")
                        and s["text_length"] > 10]

        for sec in req_sections:
            if len(conflicts) >= count:
                break
            num = sec["number"]
            rid = f"REQ-{num}"
            title = sec["title"]

            desc = (
                f"正文{num}({title})定义了软件能力需求，"
                f"但合格性规定表(章节4)中缺少对应的需求标识'{rid}'，"
                f"导致该需求无法被合格性验证和追踪，违反GJB 438C需求标识规范"
            )

            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "missing_req_id",
                "layer": "syntax",
                "is_conflict": True,
                "severity": "HIGH",
                "description": desc,
                "location": {"sections": [num, "4"]},
                "missing_req_id": rid,
                "requirement_section": num,
                "note": f"合成矛盾(需求标识缺失): 正文{num}有需求定义但合格性表缺少{rid}",
            })
            idx += 1

    # 如果还不够，生成追踪表缺少REQ-ID的矛盾
    if len(conflicts) < count:
        tables = extract_table_data(doc)
        for t in tables:
            if len(conflicts) >= count:
                break
            if t["type"] != "traceability":
                continue
            for row in t["rows"]:
                if len(conflicts) >= count:
                    break
                for cell in row:
                    c = cell.strip()
                    if re.match(r"REQ-[\d.]+", c):
                        desc = (
                            f"需求可追踪性表(章节5)中需求标识'{c}'"
                            f"在修改版中被删除(留空)，"
                            f"导致追踪关系断裂，无法建立需求与指标的双向映射"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "missing_req_id",
                            "layer": "syntax",
                            "is_conflict": True,
                            "severity": "MEDIUM",
                            "description": desc,
                            "location": {"sections": ["5"], "table_type": "traceability"},
                            "missing_req_id": c,
                            "note": f"合成矛盾(追踪表需求标识缺失): 删除{c}",
                        })
                        idx += 1
                        break

    # 最后补充: 生成正文3.2.x章节中缺少REQ-ID标注的矛盾
    if len(conflicts) < count:
        sections = extract_sections(doc)
        req_sections = [s for s in sections if s["number"] and s["number"].startswith("3.2.")
                        and s["text_length"] > 10]
        for sec in req_sections:
            if len(conflicts) >= count:
                break
            num = sec["number"]
            desc = (
                f"正文{num}({sec['title']})的需求描述中"
                f"缺少需求唯一标识(REQ-ID)标注，"
                f"无法与合格性规定表(章节4)和需求可追踪性表(章节5)建立映射关系"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "missing_req_id",
                "layer": "syntax",
                "is_conflict": True,
                "severity": "MEDIUM",
                "description": desc,
                "location": {"sections": [num]},
                "missing_req_id": f"REQ-{num}",
                "note": f"合成矛盾(正文缺少REQ-ID标注): {num}章节无REQ-ID",
            })
            idx += 1

    # 补充: 为其他有需求的章节(3.1.x, 3.3.x等)生成缺少REQ-ID的矛盾
    if len(conflicts) < count:
        sections = extract_sections(doc)
        other_req_sections = [s for s in sections if s["number"]
                              and (s["number"].startswith("3.1.") or s["number"].startswith("3.3."))
                              and s["text_length"] > 30]
        for sec in other_req_sections:
            if len(conflicts) >= count:
                break
            num = sec["number"]
            rid = f"REQ-{num}"
            desc = (
                f"正文{num}({sec['title']})定义了状态/接口需求，"
                f"但合格性规定表(章节4)中缺少对应的需求标识'{rid}'，"
                f"导致该需求无法被合格性验证和追踪"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "missing_req_id",
                "layer": "syntax",
                "is_conflict": True,
                "severity": "MEDIUM",
                "description": desc,
                "location": {"sections": [num, "4"]},
                "missing_req_id": rid,
                "note": f"合成矛盾(需求标识缺失): {num}章节需求在合格性表中缺少{rid}",
            })
            idx += 1

    # 补充: 合格性表使用占位符代替REQ-ID的矛盾
    if len(conflicts) < count:
        tables = extract_table_data(doc)
        for t in tables:
            if len(conflicts) >= count:
                break
            if t["type"] != "qualification":
                continue
            for row in t["rows"]:
                if len(conflicts) >= count:
                    break
                for cell in row:
                    c = cell.strip()
                    # 检测占位符ID(如"0028"等非REQ格式ID)
                    if c and re.match(r"^\d+$", c) and not re.match(r"^3\.\d+", c):
                        desc = (
                            f"合格性规定表(章节4)中需求标识'{c}'"
                            f"不符合GJB 438C规定的REQ-X.Y.Z格式，"
                            f"使用纯数字占位符代替标准需求标识，无法唯一标识需求"
                        )
                        conflicts.append({
                            "gt_id": f"SYN-{idx:03d}",
                            "doc_name": doc_name,
                            "type": "missing_req_id",
                            "layer": "syntax",
                            "is_conflict": True,
                            "severity": "HIGH",
                            "description": desc,
                            "location": {"sections": ["4"], "table_type": "qualification"},
                            "original_req_id": c,
                            "modified_req_id": "",
                            "note": f"合成矛盾(需求标识格式错误): 占位符'{c}'不符合REQ-X.Y.Z格式",
                        })
                        idx += 1
                        break

    # 补充: 追踪表缺少需求名称映射的矛盾
    if len(conflicts) < count:
        sections = extract_sections(doc)
        req_sections = [s for s in sections if s["number"] and s["number"].startswith("3.2.")
                        and s["text_length"] > 10]
        for sec in req_sections:
            if len(conflicts) >= count:
                break
            num = sec["number"]
            title = sec["title"]
            # 提取需求名称(去掉章节号前缀)
            name = re.sub(r"^[\d.]+\s*", "", title)
            desc = (
                f"需求可追踪性表(章节5)中缺少需求'{name}'(对应{num})的追踪记录，"
                f"导致该需求无法追溯到系统指标，违反GJB 438C可追踪性要求"
            )
            conflicts.append({
                "gt_id": f"SYN-{idx:03d}",
                "doc_name": doc_name,
                "type": "missing_req_id",
                "layer": "syntax",
                "is_conflict": True,
                "severity": "MEDIUM",
                "description": desc,
                "location": {"sections": [num, "5"], "table_type": "traceability"},
                "missing_req_id": f"REQ-{num}",
                "note": f"合成矛盾(追踪表缺少需求映射): {num}需求在追踪表中缺失",
            })
            idx += 1

    return conflicts


# ============================================================
# 主流程
# ============================================================

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    all_conflicts = []
    per_type_count = defaultdict(int)
    per_doc_count = defaultdict(int)
    per_doc_type = defaultdict(lambda: defaultdict(int))

    for doc_name in DOC_NAMES:
        doc = load_doc(doc_name)

        start = len(all_conflicts)

        # 每种类型生成10个，每份文档50个
        c1 = gen_same_param_diff_value(doc_name, doc, count=10, start_id=len(all_conflicts) + 1)
        all_conflicts.extend(c1)

        c2 = gen_text_table_conflict(doc_name, doc, count=10, start_id=len(all_conflicts) + 1)
        all_conflicts.extend(c2)

        c3 = gen_logic_unsatisfiable(doc_name, doc, count=10, start_id=len(all_conflicts) + 1)
        all_conflicts.extend(c3)

        c4 = gen_missing_chapter(doc_name, doc, count=10, start_id=len(all_conflicts) + 1)
        all_conflicts.extend(c4)

        c5 = gen_missing_req_id(doc_name, doc, count=10, start_id=len(all_conflicts) + 1)
        all_conflicts.extend(c5)

        # 统计
        for c in c1 + c2 + c3 + c4 + c5:
            per_type_count[c["type"]] += 1
            per_doc_count[doc_name] += 1
            per_doc_type[doc_name][c["type"]] += 1

    # 构建输出
    output = {
        "source": "synthetic_injection",
        "description": "基于scheduler/compiler/battery三份GJB SRS合成的矛盾标注集，通过注入5种类型矛盾生成",
        "generation_method": {
            "same_param_diff_value": "找到文档中多处出现的参数值，将某处改为不同值",
            "text_table_conflict": "修改合格性表/追踪表中的REQ-ID、章节号、合格性方法等值",
            "logic_unsatisfiable": "对数值约束添加矛盾约束(如x≤5且x≥30)，Z3求解为UNSAT",
            "missing_chapter": "生成缺少GJB 438C必需章节的版本",
            "missing_req_id": "生成缺少或格式错误的REQ-ID标注",
        },
        "source_documents": DOC_NAMES,
        "total": len(all_conflicts),
        "by_type": dict(per_type_count),
        "by_doc": dict(per_doc_count),
        "by_doc_type": {k: dict(v) for k, v in per_doc_type.items()},
        "conflicts": all_conflicts,
    }

    out_path = os.path.join(OUT_DIR, "synthetic_conflicts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 打印统计
    print(f"=== 合成矛盾数据集生成完成 ===")
    print(f"输出: {out_path}")
    print(f"总计: {len(all_conflicts)} 个合成矛盾标注")
    print(f"\n按类型:")
    for t, c in sorted(per_type_count.items()):
        print(f"  {t}: {c}")
    print(f"\n按文档:")
    for d, c in sorted(per_doc_count.items()):
        print(f"  {d}: {c}")
    print(f"\n按文档×类型:")
    for d in DOC_NAMES:
        print(f"  {d}:")
        for t, c in sorted(per_doc_type[d].items()):
            print(f"    {t}: {c}")

    return output


if __name__ == "__main__":
    main()
