#!/usr/bin/env python3
"""P0: 把注入值写进渲染上下文

对eval_set.json做后处理:
  1. 深拷贝occurrences，把injected值替换到对应位置的content
  2. 生成rendered_context文本(各位置的格式化内容,含注入后的值)
  3. 存回eval_set.json: 新增 occurrences_injected / rendered_context 字段

这样下游(多LLM标注/人工标注/盲测)直接用rendered_context，
不需要各自猜怎么回写注入值——保证注入可见性。

用法:
  python tools/render_context.py            # 处理+验证
  python tools/render_context.py --sample 10 # 只看10条样例
"""
import argparse
import copy
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"

# "op value" 或 "op value unit" 格式解析 (PARAM/TERM-06的original/injected格式)
CONSTRAINT_RE = re.compile(r'^(ge|le|gt|lt|eq)\s+([\d.]+)\s*(.*)$')


def parse_constraint(text):
    """解析 'ge 256.0' / 'gt 10秒' / 'eq 256GB' → (op, val, unit)"""
    m = CONSTRAINT_RE.match(str(text).strip())
    if m:
        return m.group(1), m.group(2), m.group(3).strip()
    return None


def apply_injection(occurrences, injection):
    """把injected值替换到对应occurrence的content,返回新的occurrences列表

    替换策略(按优先级):
      1. inject_location匹配的occurrence
      2. 找不到匹配location → 第一个occurrence
    替换方式(按content类型):
      - 约束串(op val [unit]): 更新op/content/unit三个字段
      - str: original==content则整体替换; original in content则子串替换
      - list/dict: 整体替换
    """
    occs = copy.deepcopy(occurrences)
    if not injection or injection.get("method", "") in ("positive", ""):
        return occs

    injected = injection.get("injected", "")
    original = injection.get("original", "")
    inject_location = injection.get("inject_location", "")

    # 找目标occurrence
    target = None
    for occ in occs:
        if occ.get("location") == inject_location:
            target = occ
            break
    if target is None and occs:
        target = occs[0]
    if target is None:
        return occs

    content = target.get("content", "")

    # 情况1: original/injected是约束串格式 "op val[unit]" → 更新op/content/unit
    c_orig = parse_constraint(original) if isinstance(original, str) else None
    c_inj = parse_constraint(injected) if isinstance(injected, str) else None
    if c_orig and c_inj and isinstance(content, str):
        try:
            val_match = float(content.strip()) == float(c_orig[1])
        except (ValueError, TypeError):
            val_match = False
        if val_match or content.strip() == str(original).strip():
            target["op"] = c_inj[0]
            target["content"] = c_inj[1]
            if c_inj[2]:
                target["unit"] = c_inj[2]
            return occs

    # 情况2: content是str
    if isinstance(content, str) and isinstance(injected, str):
        if str(original) == content:
            target["content"] = injected
        elif original and str(original) in content:
            target["content"] = content.replace(str(original), injected, 1)
        else:
            # 无法精确定位(如注入的是重新表述) → 直接替换(保底,保证可见)
            target["content"] = injected
        return occs

    # 情况3: content是list/dict → 整体替换
    if isinstance(content, (list, dict)) and isinstance(injected, (list, dict)):
        target["content"] = injected
        return occs

    # 情况4: 类型不匹配(如content是数值,injected是str) → 保底替换
    target["content"] = injected
    return occs


def render_context(occurrences, max_positions=6):
    """把occurrences渲染成可读文本(标注者看到的检测上下文)"""
    lines = []
    for i, occ in enumerate(occurrences[:max_positions]):
        location = occ.get("location", "?")
        section = occ.get("section", "")
        content = occ.get("content", "")
        if isinstance(content, dict):
            content = json.dumps(content, ensure_ascii=False)
        elif isinstance(content, list):
            content = " → ".join(str(c) for c in content)
        # 参数类: 拼上操作符和单位,如 "≥256GB"
        op = occ.get("op", "")
        unit = occ.get("unit", "")
        if op and isinstance(occ.get("content"), str):
            op_sym = {"ge": "≥", "le": "≤", "gt": ">", "lt": "<", "eq": "="}.get(op, op)
            content = f"{op_sym}{content}{unit}"
        lines.append(f"位置{i+1} [{location}] 章节{section}: {content}")
    if len(occurrences) > max_positions:
        lines.append(f"... 共{len(occurrences)}个位置(仅展示前{max_positions}个)")
    return "\n".join(lines)


def check_visible(entry):
    """验证注入是否在渲染上下文中可见

    规则: 渲染上下文中,至少一个位置的内容与其他位置不同(对str类),
    或直接对比注入前后target位置是否变化
    """
    occs = entry.get("occurrences_injected", [])
    inj = entry.get("injection", {})
    if inj.get("method") == "positive" or not occs:
        return True  # 正例无注入,无需可见性
    rendered = entry.get("rendered_context", "")
    injected_val = str(inj.get("injected", ""))[:50]
    # 注入值(或其数值部分)应出现在渲染文本中
    if injected_val and injected_val != "None":
        # 取injected的核心片段(list取首尾元素,约束串取数值+单位)
        frag = injected_val
        m = CONSTRAINT_RE.match(frag)
        if m:
            frag = f"{m.group(2)}{m.group(3)}".strip()
        elif frag.startswith("["):
            inner = re.findall(r"'([^']+)'", frag)
            if inner:
                frag = inner[0]
        if frag and frag in rendered:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=0, help="只打印N条样例不写回")
    args = parser.parse_args()

    with open(EVAL_PATH, encoding="utf-8") as f:
        data = json.load(f)
    entries = data["entries"]
    print(f"加载 {len(entries)} 条")

    # 处理每条
    visible_count = 0
    negative_count = 0
    for entry in entries:
        occs = entry.get("entity", {}).get("occurrences", [])
        inj = entry.get("injection", {})
        occs_inj = apply_injection(occs, inj)
        entry["occurrences_injected"] = occs_inj
        entry["rendered_context"] = render_context(occs_inj)
        if inj.get("method") != "positive":
            negative_count += 1
            if check_visible(entry):
                visible_count += 1

    print(f"负例 {negative_count} 条, 注入可见 {visible_count} 条 "
          f"({visible_count/max(1,negative_count)*100:.1f}%)")

    if args.sample:
        # 打印样例: 负例优先,各类型抽几条
        seen = {}
        for entry in entries:
            ci = entry.get("check_item", "")
            if entry.get("injection", {}).get("method") == "positive":
                continue
            if seen.get(ci, 0) >= 1:
                continue
            seen[ci] = 1
            if sum(seen.values()) > args.sample:
                break
            print(f"\n{'='*70}")
            print(f"{entry['eval_id']} | {ci} | {entry.get('injection',{}).get('method','')}")
            print(f"original: {str(entry.get('injection',{}).get('original',''))[:60]}")
            print(f"injected: {str(entry.get('injection',{}).get('injected',''))[:60]}")
            print("--- rendered_context ---")
            print(entry["rendered_context"][:400])
        return

    # 写回
    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已写回 {EVAL_PATH} (新增 occurrences_injected / rendered_context 字段)")


if __name__ == "__main__":
    main()
