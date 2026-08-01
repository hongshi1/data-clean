#!/usr/bin/env python3
"""
SRS 约束标准化 + Schema统一
=============================
修复3个数据质量问题:
  D1: scheduler_srs全部numerical约束value为字符串 → 拆分为{value, operator, unit}
  H1: 三份文档Schema不统一 → 统一字段名
  补充: 空value从original字段重新提取数值

统一Schema:
  {doc, date, total, constraints: [{
    type, original, param, value(float|None), operator, unit,
    section(纯编号), line, description(可选)
  }]}

用法: python3 tools/srs_constraint_normalize.py
"""
import json
import re
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
INPUT_DIR = BASE / "data/gjb_438c/extracted_constraints"
OUTPUT_DIR = BASE / "data/gjb_438c/extracted_constraints"

DOCS = ["battery_srs", "compiler_srs", "scheduler_srs"]


# ── value字符串拆分 ──────────────────────────────────────────

# 操作符模式 (按优先级排序)
OPERATOR_PATTERNS = [
    (re.compile(r'不超过|至多|最多|不大于|小于等于|≤'), '≤'),
    (re.compile(r'不小于|至少|最少|不低于|大于等于|≥'), '≥'),
    (re.compile(r'<='), '≤'),
    (re.compile(r'>='), '≥'),
    (re.compile(r'(?<![<>=])='), '='),
    (re.compile(r'<(?![=])'), '<'),
    (re.compile(r'>(?![=])'), '>'),
]

# 数值正则 (支持小数、科学计数法)
VALUE_RE = re.compile(r'(\d+\.?\d*(?:e[+-]?\d+)?)')

# 单位正则 (按长度降序匹配，避免ms被m匹配)
UNIT_PATTERNS = [
    'MHz', 'GHz', 'kHz',
    'ms', 'KB', 'MB', 'GB', 'TB',
    'Ah', 'Ω',
    's', '%', 'V', 'A', 'W', 'Hz',
    '层', '个', '次', '秒', '分钟', '小时',
]
UNIT_RE = re.compile(r'(' + '|'.join(UNIT_PATTERNS) + r')')

# ±容差正则
TOLERANCE_RE = re.compile(r'±\s*(\d+\.?\d*)\s*(' + '|'.join(UNIT_PATTERNS) + r')?')


def normalize_value(raw_value, original_text=""):
    """
    将value字段标准化为 {value, operator, unit}.
    
    处理:
      "不超过0.01ms" → {value:0.01, operator:"≤", unit:"ms"}
      "<= 0.01ms"    → {value:0.01, operator:"≤", unit:"ms"}
      ">= 4.1.15"    → {value:4.1.15, operator:"≥", unit:""}
      25             → {value:25.0, operator:"", unit:""}
      ""             → 从original_text补提取
    """
    # 如果已经是数值
    if isinstance(raw_value, (int, float)):
        return float(raw_value), "", ""

    raw_str = str(raw_value).strip() if raw_value else ""

    # 空值: 从original补提取
    if not raw_str:
        return extract_value_from_original(original_text)

    # ±容差特殊处理
    tol_m = TOLERANCE_RE.search(raw_str)
    if tol_m:
        val = float(tol_m.group(1))
        unit = tol_m.group(2) or ""
        return val, "±", unit

    # 提取操作符
    operator = ""
    for pattern, op in OPERATOR_PATTERNS:
        if pattern.search(raw_str):
            operator = op
            break

    # 提取数值
    val_m = VALUE_RE.search(raw_str)
    if not val_m:
        return None, operator, ""
    value = float(val_m.group(1))

    # 提取单位
    unit_m = UNIT_RE.search(raw_str)
    unit = unit_m.group(1) if unit_m else ""

    return value, operator, unit


def extract_value_from_original(original_text):
    """从约束原文中提取数值、操作符、单位"""
    if not original_text:
        return None, "", ""

    text = original_text.strip()

    # 尝试±容差
    tol_m = TOLERANCE_RE.search(text)
    if tol_m:
        return float(tol_m.group(1)), "±", tol_m.group(2) or ""

    # 尝试操作符+数值
    for pattern, op in OPERATOR_PATTERNS:
        m = pattern.search(text)
        if m:
            # 在操作符后找数值
            after = text[m.end():]
            val_m = VALUE_RE.search(after)
            if val_m:
                value = float(val_m.group(1))
                # 在数值后找单位
                after_val = after[val_m.end():]
                unit_m = UNIT_RE.search(after_val)
                unit = unit_m.group(1) if unit_m else ""
                return value, op, unit

    # 尝试纯数值
    val_m = VALUE_RE.search(text)
    if val_m:
        value = float(val_m.group(1))
        after_val = text[val_m.end():]
        unit_m = UNIT_RE.search(after_val)
        unit = unit_m.group(1) if unit_m else ""
        return value, "", unit

    return None, "", ""


# ── Schema统一 ───────────────────────────────────────────────

def parse_section_number(section_str):
    """从各种格式提取纯章节号 '3.2.1'"""
    if not section_str:
        return ""
    s = str(section_str).strip()
    m = re.match(r'(\d+(?:\.\w+)*)', s)
    return m.group(1) if m else ""


def normalize_constraint(c, doc_name):
    """
    将单条约束统一到标准Schema.
    兼容三种输入格式:
      battery: section_number + section_title + line_start + unit + description
      compiler: section + line + operator + unit
      scheduler: section + line (无operator/unit)
    """
    # 获取section (纯编号)
    section_raw = c.get("section_number") or c.get("section") or c.get("section_title") or ""
    section = parse_section_number(section_raw)

    # 获取line
    line = c.get("line_start", c.get("line", 0))

    # 获取original
    original = c.get("original", c.get("sentence", ""))

    # 标准化value
    raw_value = c.get("value")
    raw_operator = c.get("operator", "")
    raw_unit = c.get("unit", "")

    if raw_operator and raw_unit and isinstance(raw_value, (int, float)):
        # compiler_srs格式: 已有operator+unit+数值value
        value = float(raw_value)
        operator = raw_operator
        unit = raw_unit
    elif isinstance(raw_value, (int, float)):
        # battery_srs格式: 数值value + unit, 可能无operator
        value = float(raw_value)
        operator = raw_operator
        unit = raw_unit
    else:
        # scheduler_srs格式: value是字符串或空 → 标准化
        value, operator, unit = normalize_value(raw_value, original)
        # 如果原始有unit且标准化后unit为空, 保留原始unit
        if not unit and raw_unit:
            unit = raw_unit

    return {
        "type": c.get("type", ""),
        "original": original,
        "param": c.get("param", ""),
        "value": value,
        "operator": operator or "",
        "unit": unit or "",
        "section": section,
        "line": line or 0,
        "description": c.get("description", "") or "",
    }


def normalize_doc(doc_name):
    """标准化单份文档的约束"""
    input_path = INPUT_DIR / f"{doc_name}_constraints.json"
    if not input_path.exists():
        print(f"  [!] 文件不存在: {input_path}")
        return None

    data = json.loads(input_path.read_text(encoding="utf-8"))
    constraints = data.get("constraints", [])

    normalized = [normalize_constraint(c, doc_name) for c in constraints]

    output = {
        "doc": doc_name,
        "date": data.get("extract_date") or data.get("date") or datetime.now().isoformat(),
        "total": len(normalized),
        "constraints": normalized,
    }

    output_path = OUTPUT_DIR / f"{doc_name}_constraints_normalized.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


# ── 验证 ─────────────────────────────────────────────────────

def verify_normalized(doc_name, data):
    """验证标准化结果"""
    constraints = data["constraints"]
    print(f"\n  [{doc_name}] {len(constraints)}条约束")

    # V1: numerical value类型检查
    numerical = [c for c in constraints if c["type"] == "numerical"]
    float_count = sum(1 for c in numerical if isinstance(c["value"], float))
    none_count = sum(1 for c in numerical if c["value"] is None)
    print(f"    numerical: {len(numerical)}条, value为float: {float_count}, value为None: {none_count}")

    # 显示标准化后的numerical约束
    for c in numerical:
        status = "✓" if isinstance(c["value"], float) else "✗"
        unit_str = c['unit'] or ""
    op_str = c['operator'] or ""
    print(f"    {status} param={c['param']:20s} value={str(c['value']):10s} op={op_str:3s} unit={unit_str:5s} section={c['section']}")

    # V2: Schema字段一致性检查
    required_fields = {"type", "original", "param", "value", "operator", "unit", "section", "line"}
    for c in constraints:
        missing = required_fields - set(c.keys())
        if missing:
            print(f"    [!] 缺失字段: {missing}")

    # V3: section完整性
    empty_section = sum(1 for c in constraints if not c["section"])
    print(f"    section为空: {empty_section}/{len(constraints)}")

    return float_count, none_count, empty_section


def main():
    print("=" * 70)
    print("SRS 约束标准化 + Schema统一")
    print("=" * 70)

    all_results = {}
    total_float = 0
    total_none = 0
    total_empty_section = 0

    for doc in DOCS:
        print(f"\n[{doc}]")
        data = normalize_doc(doc)
        if data:
            all_results[doc] = data
            f_count, n_count, e_count = verify_normalized(doc, data)
            total_float += f_count
            total_none += n_count
            total_empty_section += e_count

    # 汇总
    print(f"\n{'=' * 70}")
    print(f"[汇总]")
    total_numerical = sum(1 for doc in all_results.values()
                          for c in doc["constraints"] if c["type"] == "numerical")
    print(f"  总numerical约束: {total_numerical}")
    print(f"  value为float: {total_float} ({total_float/max(1,total_numerical):.1%})")
    print(f"  value为None: {total_none} ({total_none/max(1,total_numerical):.1%})")
    print(f"  section为空: {total_empty_section}")

    # 评估
    print(f"\n[评估]")
    if total_none == 0:
        print(f"  ✓ D1修复: 全部numerical约束value为float")
    else:
        print(f"  △ D1部分修复: {total_none}条value仍为None(需从original补提取)")
    if total_empty_section == 0:
        print(f"  ✓ H1修复: 无空section")
    else:
        print(f"  △ H1部分修复: {total_empty_section}条section为空")

    # 保存汇总
    summary = {
        "normalize_date": datetime.now().isoformat(),
        "docs": {doc: {"total": len(data["constraints"]),
                       "numerical_float": sum(1 for c in data["constraints"]
                                              if c["type"] == "numerical" and isinstance(c["value"], float)),
                       "numerical_none": sum(1 for c in data["constraints"]
                                             if c["type"] == "numerical" and c["value"] is None),
                       "empty_section": sum(1 for c in data["constraints"] if not c["section"])}
                 for doc, data in all_results.items()},
    }
    summary_path = OUTPUT_DIR / "_normalize_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  汇总已保存: {summary_path.relative_to(BASE)}")


if __name__ == "__main__":
    main()
