#!/usr/bin/env python3
"""
四类不一致QA合成器 — 基于pair dataset注入不一致

四类不一致(温老师会议反馈):
  1. 术语层面: 同名实体/多实体映射
  2. 参数指标: 参数/单位/数字一致
  3. 业务逻辑: 时序/流程一致
  4. GJB合规: 模板/接口定义规范

每个pair实例生成: 4类 × (1正例 + 1注入) = 8条QA
占位符格式: {image}/{table}/{text}
正负比: 1:1

输出: data/gjb_438c/data_assets/injected_qa.json
"""
import csv
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PAIR_DIR = "data/gjb_438c/pair_dataset"
RULES_PATH = "knowledge/inconsistency_rules.json"
OUT_PATH = "data/gjb_438c/data_assets/injected_qa.json"

random.seed(42)
ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")


def load_all_pairs():
    pairs = []
    for sc_dir in sorted(os.listdir(PAIR_DIR)):
        sc_path = os.path.join(PAIR_DIR, sc_dir)
        if not os.path.isdir(sc_path):
            continue
        for inst_name in sorted(os.listdir(sc_path)):
            inst_path = os.path.join(sc_path, inst_name)
            if not os.path.isdir(inst_path):
                continue
            meta_path = os.path.join(inst_path, "meta.json")
            if not os.path.exists(meta_path):
                continue
            meta = json.loads(open(meta_path).read())
            table_rows = []
            tbl_path = os.path.join(inst_path, "table.csv")
            if os.path.exists(tbl_path):
                with open(tbl_path, encoding="utf-8") as f:
                    table_rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
            text = ""
            txt_path = os.path.join(inst_path, "text.txt")
            if os.path.exists(txt_path):
                text = open(txt_path, encoding="utf-8").read()
            pairs.append({
                "meta": meta,
                "table_rows": table_rows,
                "text": text,
                "image_path": os.path.join(inst_path, "image.png"),
                "image_exists": os.path.exists(os.path.join(inst_path, "image.png")),
                "sc_dir": sc_dir,
                "inst_path": inst_path,
            })
    return pairs


def _ph(pair):
    """生成占位符路径"""
    return {
        "image": pair["image_path"] if pair["image_exists"] else "",
        "table": os.path.join(pair["inst_path"], "table.csv"),
        "text": os.path.join(pair["inst_path"], "text.txt"),
    }


def _meta(pair):
    m = pair["meta"]
    return {
        "image_caption": m.get("image_caption", ""),
        "table_caption": m.get("table_caption", ""),
        "section": m.get("section", ""),
        "doc": m.get("doc", ""),
        "scenario": m.get("scenario", ""),
    }


# ══════════════════════════════════════════════════════════
# 1. 术语层面 (terminology)
# ══════════════════════════════════════════════════════════
def gen_terminology_qa(pair):
    """术语一致性QA: 图/表/文的名称是否一致"""
    qas = []
    func_names = pair["meta"].get("func_names", [])
    table_rows = pair["table_rows"]
    text = pair["text"]
    ph = _ph(pair)
    ev = _meta(pair)

    if not func_names:
        return qas

    name = func_names[0]

    # ── 正例: 名称一致性确认 ──
    qas.append({
        "inconsistency_type": "terminology",
        "subtype": "name_consistency",
        "label": "consistent",
        "is_injected": False,
        "rule_id": "TERM-001",
        "question": f"表{{table}}中功能「{name}」的名称，与图{{image}}中的用例名称是否一致？",
        "placeholders": ph,
        "answer": f"一致。表格和图中均使用「{name}」。",
        "evidence": ev,
        "difficulty": "easy",
    })

    # ── 注入: 错字(typo) ──
    if len(name) >= 3:
        pos = random.randint(1, len(name) - 2)
        chars = list(name)
        # 替换为一个不常用字
        chars[pos] = "操" if chars[pos] != "操" else "控"
        wrong_name = "".join(chars)
        qas.append({
            "inconsistency_type": "terminology",
            "subtype": "name_typo",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"表格功能名「{name}」被改为「{wrong_name}」",
            "rule_id": "TERM-001",
            "question": f"表{{table}}中功能「{wrong_name}」与图{{image}}中的用例名称是否一致？如不一致请指出差异。",
            "placeholders": ph,
            "answer": f"不一致。图中用例名为「{name}」，但表格中写为「{wrong_name}」，"
                      f"第{pos+1}个字「{name[pos]}」被误写为「{wrong_name[pos]}」，属于错字。",
            "evidence": ev,
            "difficulty": "medium",
        })

    # ── 注入: 截断(truncation) ──
    if len(name) >= 4:
        truncated = name[1:]  # 去掉第一个字
        qas.append({
            "inconsistency_type": "terminology",
            "subtype": "name_truncation",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"功能名「{name}」被截断为「{truncated}」",
            "rule_id": "TERM-001",
            "question": f"表{{table}}中功能「{truncated}」与正文{{text}}中描述的功能名称是否一致？",
            "placeholders": ph,
            "answer": f"不一致。正文中的功能名为「{name}」，但表格中写为「{truncated}」，"
                      f"缺少了开头的「{name[0]}」字，属于名称截断。",
            "evidence": ev,
            "difficulty": "medium",
        })

    return qas


# ══════════════════════════════════════════════════════════
# 2. 参数指标 (parameter)
# ══════════════════════════════════════════════════════════
def gen_parameter_qa(pair):
    """参数一致性QA: 接口属性/数值/单位"""
    qas = []
    table_rows = pair["table_rows"]
    ph = _ph(pair)
    ev = _meta(pair)

    if len(table_rows) < 2:
        return qas
    headers = [h.strip() for h in table_rows[0]]
    data_row = table_rows[1] if len(table_rows) > 1 else []
    cells = [c.strip() for c in data_row if c.strip()]
    if len(cells) < 3:
        return qas

    # 找接口名和属性
    iface_name = cells[1] if len(cells) > 1 else cells[0]
    iface_name = iface_name.split("/")[0].strip() if "/" in iface_name else iface_name

    # 找接收方/类型
    receiver = None
    iface_type = None
    for i, h in enumerate(headers):
        if "接收" in h and i < len(data_row):
            receiver = data_row[i].strip()
        elif "类型" in h and i < len(data_row):
            iface_type = data_row[i].strip()

    # ── 正例: 接口属性确认 ──
    if receiver:
        qas.append({
            "inconsistency_type": "parameter",
            "subtype": "interface_attr",
            "label": "consistent",
            "is_injected": False,
            "rule_id": "PARAM-003",
            "question": f"表{{table}}中接口「{iface_name}」的接收方是什么？",
            "placeholders": ph,
            "answer": f"接收方为「{receiver}」。",
            "evidence": ev,
            "difficulty": "easy",
        })

        # ── 注入: 接收方不一致 ──
        wrong_receiver = "高" if receiver != "高" else "中"
        qas.append({
            "inconsistency_type": "parameter",
            "subtype": "receiver_mismatch",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"接口「{iface_name}」的接收方从「{receiver}」改为「{wrong_receiver}」",
            "rule_id": "PARAM-003",
            "question": f"接口「{iface_name}」在表{{table}}中的接收方为「{wrong_receiver}」，"
                        f"但在文档其他位置（如3.3.1节）的接收方为「{receiver}」，是否一致？",
            "placeholders": ph,
            "answer": f"不一致。该接口的接收方在表中为「{wrong_receiver}」，"
                      f"但在3.3.1节为「{receiver}」，存在属性值矛盾。",
            "evidence": ev,
            "difficulty": "hard",
        })

    # ── 注入: 接口类型不一致 ──
    if iface_type:
        wrong_type = "DLL接口" if "API" in iface_type else "API接口"
        qas.append({
            "inconsistency_type": "parameter",
            "subtype": "type_mismatch",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"接口「{iface_name}」的类型从「{iface_type}」改为「{wrong_type}」",
            "rule_id": "PARAM-003",
            "question": f"表{{table}}中接口「{iface_name}」的类型标注为「{wrong_type}」，"
                        f"但图{{image}}中标注为「{iface_type}」，两者是否一致？",
            "placeholders": ph,
            "answer": f"不一致。表格中接口类型为「{wrong_type}」，图中为「{iface_type}」，"
                      f"存在接口类型矛盾。",
            "evidence": ev,
            "difficulty": "medium",
        })

    return qas


# ══════════════════════════════════════════════════════════
# 3. 业务逻辑 (business_logic)
# ══════════════════════════════════════════════════════════
def gen_logic_qa(pair):
    """业务逻辑QA: 流程步骤/异常流引用"""
    qas = []
    text = pair["text"]
    func_names = pair["meta"].get("func_names", [])
    ph = _ph(pair)
    ev = _meta(pair)
    sc = pair["sc_dir"]

    if not func_names:
        return qas
    name = func_names[0]

    # ── 正例: 流程描述确认 ──
    if text and len(text) > 30:
        qas.append({
            "inconsistency_type": "business_logic",
            "subtype": "flow_description",
            "label": "consistent",
            "is_injected": False,
            "rule_id": "LOGIC-001",
            "question": f"根据正文{{text}}，{name}的主要功能是什么？",
            "placeholders": ph,
            "answer": text[:150],
            "evidence": ev,
            "difficulty": "easy",
        })

    # ── 注入: 流程步骤顺序错误(sc2流程图场景) ──
    if "flowchart" in sc and func_names:
        qas.append({
            "inconsistency_type": "business_logic",
            "subtype": "step_order_error",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"流程图{{image}}的步骤2和步骤3顺序被颠倒",
            "rule_id": "LOGIC-001",
            "question": f"图{{image}}中{name}的流程步骤顺序，与表{{table}}中描述的步骤顺序是否一致？"
                        f"请逐步对比。",
            "placeholders": ph,
            "answer": f"不一致。图中步骤顺序为「步骤1→步骤3→步骤2→步骤4」，"
                      f"但表格描述为「步骤1→步骤2→步骤3→步骤4」，步骤2和步骤3的顺序被颠倒。",
            "evidence": ev,
            "difficulty": "hard",
        })

    # ── 注入: 异常流悬挂引用 ──
    if "usecase" in sc.lower() or "capability" in sc.lower():
        qas.append({
            "inconsistency_type": "business_logic",
            "subtype": "dangling_exception",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"用例描述中引用了不存在的异常流E9",
            "rule_id": "LOGIC-003",
            "question": f"表{{table}}中{name}的用例描述引用了异常流E9，"
                        f"但文档中未定义E9。该引用是否有效？",
            "placeholders": ph,
            "answer": f"无效。用例描述引用了异常流E9，但文档中未定义E9，属于悬挂引用（dangling reference）。",
            "evidence": ev,
            "difficulty": "medium",
        })

    return qas


# ══════════════════════════════════════════════════════════
# 4. GJB合规 (gjb_compliance)
# ══════════════════════════════════════════════════════════
def gen_gjb_qa(pair):
    """GJB合规QA: 表头字段/ID格式/结构完整性"""
    qas = []
    table_rows = pair["table_rows"]
    func_names = pair["meta"].get("func_names", [])
    ph = _ph(pair)
    ev = _meta(pair)
    sc = pair["sc_dir"]

    if len(table_rows) < 2:
        return qas
    headers = [h.strip() for h in table_rows[0]]

    # ── 正例: 表头完整性确认 ──
    qas.append({
        "inconsistency_type": "gjb_compliance",
        "subtype": "table_header_check",
        "label": "consistent",
        "is_injected": False,
        "rule_id": "GJB-001",
        "question": f"表{{table}}的表头包含哪些字段？是否符合GJB 438C要求？",
        "placeholders": ph,
        "answer": f"表头字段为：{'、'.join(headers[:6])}。"
                  f"包含GJB 438C要求的必要字段，符合规范。",
        "evidence": ev,
        "difficulty": "easy",
    })

    # ── 注入: 删除必填字段 ──
    required_fields = []
    for h in headers:
        if any(kw in h for kw in ["标识", "描述", "接收", "类型", "名称"]):
            required_fields.append(h)
    if required_fields:
        deleted = required_fields[0]
        qas.append({
            "inconsistency_type": "gjb_compliance",
            "subtype": "missing_required_field",
            "label": "inconsistent",
            "is_injected": True,
            "inject_detail": f"表格删除了GJB必填字段「{deleted}」",
            "rule_id": "GJB-001",
            "question": f"表{{table}}中缺少字段「{deleted}」，是否符合GJB 438C接口表规范？",
            "placeholders": ph,
            "answer": f"不符合。GJB 438C要求接口表必须包含「{deleted}」字段，"
                      f"但该表中缺失此字段，属于GJB合规违规。",
            "evidence": ev,
            "difficulty": "medium",
        })

    # ── 注入: ID格式错误 ──
    if func_names:
        name = func_names[0]
        # 从表格行找ID
        for row in table_rows[1:]:
            for cell in row:
                m = ID_RE.search(cell)
                if m:
                    real_id = m.group(0)
                    wrong_id = real_id.lower()[:10]  # 小写化(违规)
                    qas.append({
                        "inconsistency_type": "gjb_compliance",
                        "subtype": "id_format_violation",
                        "label": "inconsistent",
                        "is_injected": True,
                        "inject_detail": f"需求ID「{real_id}」被改为小写「{wrong_id}」",
                        "rule_id": "GJB-004",
                        "question": f"表{{table}}中功能「{name}」的需求标识符为「{wrong_id}」，"
                                    f"是否符合GJB 438C的ID格式规范？",
                        "placeholders": ph,
                        "answer": f"不符合。GJB 438C要求需求标识符为大写字母和数字"
                                  f"（格式：[A-Z]{{2,8}}(-[A-Z0-9]{{2,8}}){{2,}}），"
                                  f"但「{wrong_id}」使用了小写字母，违反格式规范。"
                                  f"正确格式应为「{real_id}」。",
                        "evidence": ev,
                        "difficulty": "medium",
                    })
                    break
            else:
                continue
            break

    return qas


# ══════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════
def main():
    pairs = load_all_pairs()
    print(f"加载pair实例: {len(pairs)}个")

    all_qa = []
    for i, pair in enumerate(pairs):
        pair_qa = []
        pair_qa.extend(gen_terminology_qa(pair))
        pair_qa.extend(gen_parameter_qa(pair))
        pair_qa.extend(gen_logic_qa(pair))
        pair_qa.extend(gen_gjb_qa(pair))

        # 统一格式
        for j, qa in enumerate(pair_qa):
            all_qa.append({
                "id": f"qa_{i:04d}_{j:02d}",
                "pair_id": pair["meta"]["instance_id"],
                **qa,
            })

        if (i + 1) % 50 == 0:
            print(f"  已处理 {i+1}/{len(pairs)}, 生成{len(all_qa)}条QA")
            json.dump(all_qa, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)

    json.dump(all_qa, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)

    # 统计
    from collections import Counter
    by_type = Counter(q["inconsistency_type"] for q in all_qa)
    by_label = Counter(q["label"] for q in all_qa)
    by_diff = Counter(q["difficulty"] for q in all_qa)
    has_img = sum(1 for q in all_qa if q.get("placeholders", {}).get("image"))
    print(f"\n✅ 注入QA生成完成: {len(all_qa)}条 → {OUT_PATH}")
    print(f"按类型: {dict(by_type)}")
    print(f"按标签: {dict(by_label)}")
    print(f"按难度: {dict(by_diff)}")
    print(f"含图片占位符: {has_img}/{len(all_qa)}")


if __name__ == "__main__":
    main()
