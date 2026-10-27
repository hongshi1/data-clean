#!/usr/bin/env python3
"""
SRS一致性校验测试数据集生成器

借鉴MultiModalQA(ICLR 2021)格式, 面向SRS四类不一致:
  1.术语层面  2.参数指标  3.业务逻辑  4.GJB合规

数据集格式(每条QA):
{
  "qid": "srs_test_0001",
  "question": "表{table}中功能「X」与图{image}的用例名称是否一致？",
  "placeholders": {"image": "path", "table": "path", "text": "path"},
  "modalities": ["image", "table", "text"],         // 需要哪些模态(MMQA风格)
  "answer": "...",
  "answer_modality": "table",                        // 答案来自哪个模态(MMQA风格)
  "inconsistency_type": "terminology",               // 四类之一
  "subtype": "name_typo",
  "label": "inconsistent",                           // consistent/inconsistent
  "is_injected": true,
  "inject_detail": "...",
  "rule_id": "TERM-001",
  "context_note": "...",                             // 注入说明
  "evidence": {"doc":"...", "section":"...", "image_caption":"...", "table_caption":"..."},
  "difficulty": "medium",
  "split": "test"                                    // train/dev/test
}

输出: data/gjb_438c/data_assets/srs_test_dataset.json
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
OUT_PATH = "data/gjb_438c/data_assets/srs_test_dataset.json"

ID_RE = re.compile(r"[A-Z]{2,8}(?:-[A-Z0-9]{2,8}){2,}")
NUM_RE = re.compile(r'(\d+(?:\.\d+)?)\s*(GB|MB|KB|TB|ms|s|sec|min|hour|Mbps|Gbps|%|人|路|条|个|帧|Hz|kHz|MHz|GHz|米|km|W|kW|V|A|倍)')
random.seed(42)


def load_pairs():
    """加载全部pair实例"""
    pairs = []
    for sc in sorted(os.listdir(PAIR_DIR)):
        sc_dir = os.path.join(PAIR_DIR, sc)
        if not os.path.isdir(sc_dir):
            continue
        for inst in sorted(os.listdir(sc_dir)):
            ip = os.path.join(sc_dir, inst)
            if not os.path.isdir(ip):
                continue
            mp = os.path.join(ip, "meta.json")
            if not os.path.exists(mp):
                continue
            meta = json.loads(open(mp, encoding="utf-8").read())
            rows = []
            tp = os.path.join(ip, "table.csv")
            if os.path.exists(tp):
                with open(tp, encoding="utf-8") as f:
                    rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
            text = ""
            txtp = os.path.join(ip, "text.txt")
            if os.path.exists(txtp):
                text = open(txtp, encoding="utf-8").read()
            imgp = os.path.join(ip, "image.png")
            pairs.append({
                "meta": meta,
                "table_rows": rows,
                "text": text,
                "image_path": imgp,
                "image_exists": os.path.exists(imgp),
                "inst_path": ip,
                "sc_dir": sc,
            })
    return pairs


def _ph(p):
    """占位符路径(MMQA supporting_context风格)"""
    return {
        "image": p["image_path"] if p["image_exists"] else "",
        "table": os.path.join(p["inst_path"], "table.csv"),
        "text": os.path.join(p["inst_path"], "text.txt"),
    }


def _ev(p):
    m = p["meta"]
    return {
        "doc": m.get("doc", ""),
        "section": m.get("section", ""),
        "image_caption": m.get("image_caption", ""),
        "table_caption": m.get("table_caption", ""),
    }


def _modalities(question, has_image, has_table, has_text):
    """根据问题内容和可用模态推断需要的模态(MMQA风格)"""
    mods = []
    if "{image}" in question and has_image:
        mods.append("image")
    if "{table}" in question and has_table:
        mods.append("table")
    if "{text}" in question and has_text:
        mods.append("text")
    return mods if mods else ["text"]


# ══════════════════════════════════════════════════════════
# 1. 术语层面
# ══════════════════════════════════════════════════════════
def gen_terminology(p):
    qas = []
    fns = p["meta"].get("func_names", [])
    rows = p["table_rows"]
    ph = _ph(p)
    ev = _ev(p)
    if not fns:
        return qas
    name = fns[0]

    # 正例: 名称一致性
    q = f"表{{table}}中功能「{name}」的名称，与图{{image}}中的用例名称是否一致？"
    qas.append({
        "question": q, "placeholders": ph,
        "modalities": _modalities(q, p["image_exists"], True, True),
        "answer": f"一致。表格和图中均使用「{name}」。",
        "answer_modality": "table",
        "inconsistency_type": "terminology", "subtype": "name_consistency",
        "label": "consistent", "is_injected": False, "rule_id": "TERM-001",
        "evidence": ev, "difficulty": "easy",
    })

    # 注入: 错字
    if len(name) >= 3:
        pos = random.randint(1, len(name) - 2)
        chars = list(name)
        chars[pos] = "操" if chars[pos] != "操" else "控"
        wrong = "".join(chars)
        q = f"表{{table}}中功能「{wrong}」与图{{image}}中的用例名称是否一致？如不一致请指出差异。"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, p["image_exists"], True, True),
            "answer": f"不一致。图中用例名为「{name}」，若表格中误写为「{wrong}」，"
                      f"第{pos+1}个字「{name[pos]}」被误写为「{wrong[pos]}」，属于错字。",
            "answer_modality": "image",
            "inconsistency_type": "terminology", "subtype": "name_typo",
            "label": "inconsistent", "is_injected": True, "rule_id": "TERM-001",
            "inject_detail": f"功能名「{name}」被改为「{wrong}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    # 注入: 截断
    if len(name) >= 4:
        trunc = name[1:]
        q = f"表{{table}}中功能「{trunc}」与正文{{text}}中描述的功能名称是否一致？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, p["image_exists"], True, True),
            "answer": f"不一致。正文中的功能名为「{name}」，若表格中误写为「{trunc}」，"
                      f"缺少开头的「{name[0]}」字，属于名称截断。",
            "answer_modality": "text",
            "inconsistency_type": "terminology", "subtype": "name_truncation",
            "label": "inconsistent", "is_injected": True, "rule_id": "TERM-001",
            "inject_detail": f"功能名「{name}」被截断为「{trunc}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    # 注入: 字序颠倒
    if len(name) >= 4:
        chars = list(name)
        i, j = 0, 1
        chars[i], chars[j] = chars[j], chars[i]
        swapped = "".join(chars)
        q = f"表{{table}}中功能「{swapped}」与图{{image}}中的用例名称是否一致？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, p["image_exists"], True, True),
            "answer": f"不一致。图中用例名为「{name}」，若表格中误写为「{swapped}」，"
                      f"前两个字顺序颠倒，属于字序错误。",
            "answer_modality": "image",
            "inconsistency_type": "terminology", "subtype": "name_charorder",
            "label": "inconsistent", "is_injected": True, "rule_id": "TERM-001",
            "inject_detail": f"功能名「{name}」字序颠倒为「{swapped}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    # 注入: 多实体映射(同一名对应多ID)
    if len(rows) >= 3:
        id2 = None
        for row in rows[1:]:
            for cell in row:
                m = ID_RE.search(cell)
                if m and m.group(0) != name:
                    id2 = m.group(0)
                    break
            if id2:
                break
        if id2:
            q = f"表{{table}}中两个不同的需求标识符是否都对应同一功能名「{name}」？这是否合理？"
            qas.append({
                "question": q, "placeholders": ph,
                "modalities": _modalities(q, False, True, False),
                "answer": f"不合理。若两个不同标识符都对应「{name}」，属于多实体映射冲突，"
                          f"违反GJB'一个ID对应一个需求'的规范。",
                "answer_modality": "table",
                "inconsistency_type": "terminology", "subtype": "multi_entity_mapping",
                "label": "inconsistent", "is_injected": True, "rule_id": "TERM-002",
                "inject_detail": f"假设两个不同ID都映射到功能名「{name}」",
                "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
                "evidence": ev, "difficulty": "hard",
            })

    return qas


# ══════════════════════════════════════════════════════════
# 2. 参数指标
# ══════════════════════════════════════════════════════════
def gen_parameter(p):
    qas = []
    rows = p["table_rows"]
    text = p["text"]
    ph = _ph(p)
    ev = _ev(p)

    if len(rows) < 2:
        return qas
    headers = [h.strip() for h in rows[0]]

    # 从表格提取接口属性
    receiver = iface_type = None
    iface_name = None
    for i, h in enumerate(headers):
        for row in rows[1:]:
            if i < len(row):
                if "接收" in h:
                    receiver = row[i].strip()
                elif "类型" in h:
                    iface_type = row[i].strip()
                elif any(kw in h for kw in ["名称", "Use case"]):
                    iface_name = row[i].strip().split("/")[0]

    # 正例: 接口属性
    if receiver and iface_name:
        q = f"表{{table}}中接口「{iface_name}」的接收方是什么？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, False),
            "answer": f"接收方为「{receiver}」。",
            "answer_modality": "table",
            "inconsistency_type": "parameter", "subtype": "interface_attr",
            "label": "consistent", "is_injected": False, "rule_id": "PARAM-003",
            "evidence": ev, "difficulty": "easy",
        })

        # 注入: 接收方不一致
        wrong_r = "高" if receiver != "高" else "中"
        q = (f"接口「{iface_name}」在表{{table}}中接收方为「{wrong_r}」，"
             f"但在文档其他位置接收方为「{receiver}」，是否一致？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, True),
            "answer": f"不一致。若表中接收方为「{wrong_r}」而其他位置为「{receiver}」，"
                      f"存在接口属性值矛盾。",
            "answer_modality": "table",
            "inconsistency_type": "parameter", "subtype": "receiver_mismatch",
            "label": "inconsistent", "is_injected": True, "rule_id": "PARAM-003",
            "inject_detail": f"接收方从「{receiver}」改为「{wrong_r}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "hard",
        })

    # 注入: 接口类型不一致
    if iface_type and iface_name:
        wrong_t = "DLL接口" if "API" in iface_type else "API接口"
        q = (f"表{{table}}中接口「{iface_name}」类型为「{wrong_t}」，"
             f"但图{{image}}中标注为「{iface_type}」，是否一致？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, p["image_exists"], True, False),
            "answer": f"不一致。若表中为「{wrong_t}」而图中为「{iface_type}」，"
                      f"存在接口类型矛盾。",
            "answer_modality": "image",
            "inconsistency_type": "parameter", "subtype": "type_mismatch",
            "label": "inconsistent", "is_injected": True, "rule_id": "PARAM-003",
            "inject_detail": f"接口类型从「{iface_type}」改为「{wrong_t}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    # 从表格/正文提取数值参数
    all_text = " ".join(c for row in rows for c in row) + " " + text
    nums = NUM_RE.findall(all_text)
    for val_str, unit in nums[:2]:
        val = float(val_str)
        wrong_val = val * 2 if val > 0 else 100
        # 正例: 参数事实
        q = f"表{{table}}和正文{{text}}中出现的参数「{val}{unit}」出现在什么上下文中？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, True),
            "answer": f"该参数值{val}{unit}出现在文档的{ev['section']}节相关描述中。",
            "answer_modality": "text",
            "inconsistency_type": "parameter", "subtype": "param_factual",
            "label": "consistent", "is_injected": False, "rule_id": "PARAM-001",
            "evidence": ev, "difficulty": "easy",
        })
        # 注入: 参数值修改
        q = (f"表{{table}}中某参数标注为「{wrong_val}{unit}」，"
            f"但正文{{text}}中为「{val}{unit}」，两者是否一致？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, True),
            "answer": f"不一致。若表中为「{wrong_val}{unit}」而正文为「{val}{unit}」"
                      f"（原始值{val}{unit}），存在参数值矛盾。",
            "answer_modality": "table",
            "inconsistency_type": "parameter", "subtype": "value_mismatch",
            "label": "inconsistent", "is_injected": True, "rule_id": "PARAM-001",
            "inject_detail": f"参数值「{val}{unit}」被改为「{wrong_val}{unit}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "hard",
        })

    # 功能属性正例(无数值时)
    fns = p["meta"].get("func_names", [])
    if not nums and fns:
        q = f"表{{table}}中功能「{fns[0]}」的属性信息是什么？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, False),
            "answer": f"功能「{fns[0]}」记录在「{ev['table_caption']}」中，"
                      f"所在章节为{ev['section']}。",
            "answer_modality": "table",
            "inconsistency_type": "parameter", "subtype": "attr_factual",
            "label": "consistent", "is_injected": False, "rule_id": "PARAM-003",
            "evidence": ev, "difficulty": "easy",
        })

    return qas


# ══════════════════════════════════════════════════════════
# 3. 业务逻辑
# ══════════════════════════════════════════════════════════
def gen_logic(p):
    qas = []
    text = p["text"]
    fns = p["meta"].get("func_names", [])
    ph = _ph(p)
    ev = _ev(p)
    sc = p["sc_dir"]
    if not fns:
        return qas
    name = fns[0]

    # 正例: 功能描述(修复: 问题与答案匹配)
    if text and len(text) > 30:
        # 根据正文内容选择合适的问题措辞
        if "包括" in text or "包含" in text:
            q = f"根据正文{{text}}，{name}包含哪些组成部分？"
        else:
            q = f"根据正文{{text}}，{name}的主要描述内容是什么？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, False, True),
            "answer": text[:150],
            "answer_modality": "text",
            "inconsistency_type": "business_logic", "subtype": "flow_description",
            "label": "consistent", "is_injected": False, "rule_id": "LOGIC-001",
            "evidence": ev, "difficulty": "easy",
        })

    # 注入: 流程步骤顺序(sc2流程图)
    if "flowchart" in sc:
        q = f"图{{image}}中{name}的流程步骤顺序，与表{{table}}描述的步骤顺序是否一致？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, p["image_exists"], True, False),
            "answer": "不一致。若图中步骤为1→3→2→4，但表格描述为1→2→3→4，"
                      "步骤2和3顺序颠倒。",
            "answer_modality": "image",
            "inconsistency_type": "business_logic", "subtype": "step_order_error",
            "label": "inconsistent", "is_injected": True, "rule_id": "LOGIC-001",
            "inject_detail": "流程图步骤2和3顺序颠倒",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "hard",
        })

    # 注入: 异常流悬挂引用
    if "usecase" in sc.lower() or "capability" in sc.lower():
        q = (f"表{{table}}中{name}的用例描述引用了异常流E9，"
            f"但文档中未定义E9。该引用是否有效？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, False),
            "answer": "无效。若引用了E9但文档未定义E9，属于悬挂引用。",
            "answer_modality": "table",
            "inconsistency_type": "business_logic", "subtype": "dangling_exception",
            "label": "inconsistent", "is_injected": True, "rule_id": "LOGIC-003",
            "inject_detail": "用例描述引用了不存在的异常流E9",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    # 注入: 功能列表缺失
    if fns and len(fns) >= 3 and text:
        missing = fns[-1]
        q = (f"表{{table}}列出了{len(fns)}个功能，但正文{{text}}只提到了{len(fns)-1}个"
            f"（缺少「{missing}」），是否一致？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, True),
            "answer": f"不一致。若正文缺少功能「{missing}」，存在图文功能列表不一致。",
            "answer_modality": "text",
            "inconsistency_type": "business_logic", "subtype": "func_list_mismatch",
            "label": "inconsistent", "is_injected": True, "rule_id": "LOGIC-001",
            "inject_detail": f"正文缺少功能「{missing}」",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    return qas


# ══════════════════════════════════════════════════════════
# 4. GJB合规
# ══════════════════════════════════════════════════════════
def gen_gjb(p):
    qas = []
    rows = p["table_rows"]
    fns = p["meta"].get("func_names", [])
    ph = _ph(p)
    ev = _ev(p)
    if len(rows) < 2:
        return qas
    # 修复: 从真正的表头行(rows[0])取字段名, 过滤掉值
    raw_headers = [h.strip() for h in rows[0] if h.strip()]
    # 表头特征: 短文本(≤15字)、不含具体功能名、含关键词
    HEADER_KW = {"序号", "标识", "描述", "接收", "类型", "名称", "Use case", "use case",
                 "重用", "方式", "运行", "任务书", "备注", "功能", "子功能", "发送"}
    headers = []
    for h in raw_headers:
        # 过滤: 含冒号的(是值不是表头, 如"Use Case名称：连接池配置")
        if "：" in h or ":" in h:
            h = h.split("：")[0].split(":")[0].strip()
        if len(h) <= 20 and any(kw in h for kw in HEADER_KW):
            headers.append(h)

    # 正例: 表头完整性
    if headers:
        q = "表{table}的表头包含哪些字段？是否符合GJB 438C要求？"
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, False),
            "answer": f"表头字段为：{'、'.join(headers[:6])}。"
                      f"包含GJB 438C要求的必要字段，符合规范。",
            "answer_modality": "table",
            "inconsistency_type": "gjb_compliance", "subtype": "table_header_check",
            "label": "consistent", "is_injected": False, "rule_id": "GJB-001",
            "evidence": ev, "difficulty": "easy",
        })

        # 注入: 删除必填字段(从真正表头取)
        required = [h for h in headers if any(kw in h for kw in ["标识", "描述", "接收", "类型", "名称"])]
        if required:
            deleted = required[0]
            q = f"假设表{{table}}中缺少字段「{deleted}」，是否符合GJB 438C规范？"
            qas.append({
                "question": q, "placeholders": ph,
                "modalities": _modalities(q, False, True, False),
                "answer": f"不符合。GJB 438C要求表格包含「{deleted}」字段，"
                          f"若缺失则违反规范。",
                "answer_modality": "table",
                "inconsistency_type": "gjb_compliance", "subtype": "missing_required_field",
                "label": "inconsistent", "is_injected": True, "rule_id": "GJB-001",
                "inject_detail": f"删除GJB必填字段「{deleted}」",
                "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
                "evidence": ev, "difficulty": "medium",
            })

    # 注入: ID格式违规(从数据行取真实ID)
    for row in rows[1:]:
        for cell in row:
            m = ID_RE.search(cell)
            if m:
                real_id = m.group(0)
                wrong_id = real_id.lower()[:10]
                q = (f"表{{table}}中某功能的需求标识符为「{wrong_id}」，"
                     f"是否符合GJB 438C的ID格式规范？")
                qas.append({
                    "question": q, "placeholders": ph,
                    "modalities": _modalities(q, False, True, False),
                    "answer": f"不符合。GJB要求ID为大写字母数字"
                              f"（[A-Z]{{2,8}}(-[A-Z0-9]{{2,8}}){{2,}}），"
                              f"「{wrong_id}」使用了小写，正确应为「{real_id}」。",
                    "answer_modality": "table",
                    "inconsistency_type": "gjb_compliance", "subtype": "id_format_violation",
                    "label": "inconsistent", "is_injected": True, "rule_id": "GJB-004",
                    "inject_detail": f"ID「{real_id}」被改为小写「{wrong_id}」",
                    "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
                    "evidence": ev, "difficulty": "medium",
                })
                break
        else:
            continue
        break

    # 注入: ID重复
    if fns:
        q = ("假设表{table}中有两条不同功能使用了相同的需求标识符，"
             "是否符合GJB 438C规范？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, False, True, False),
            "answer": "不符合。GJB 438C要求每个CSCI需求指定项目唯一标识符，"
                      "若两个功能共用同一ID则违反唯一性规范。",
            "answer_modality": "table",
            "inconsistency_type": "gjb_compliance", "subtype": "id_duplicate",
            "label": "inconsistent", "is_injected": True, "rule_id": "GJB-004",
            "inject_detail": "两个不同功能使用相同ID",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "medium",
        })

    # 新增: 图表引用检查(GJB-005)
    if ev.get("image_caption") and ev.get("table_caption"):
        q = ("图{image}和表{table}是否都在正文{text}中被引用？"
             "（GJB 438C要求图表在正文中被引用）")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": _modalities(q, p["image_exists"], True, True),
            "answer": f"应检查正文中是否包含「{ev['image_caption'][:10]}」"
                      f"和「{ev['table_caption'][:10]}」的引用。"
                      f"若未引用则违反GJB 438C规范。",
            "answer_modality": "text",
            "inconsistency_type": "gjb_compliance", "subtype": "fig_table_reference",
            "label": "consistent", "is_injected": False, "rule_id": "GJB-005",
            "evidence": ev, "difficulty": "medium",
        })

    # 新增: 章节结构检查(GJB-003)
    section = ev.get("section", "")
    if section:
        chapter = section.split(".")[0] if "." in section else section
        q = (f"假设文档缺少第{chapter}章，是否符合GJB 438C规范？")
        qas.append({
            "question": q, "placeholders": ph,
            "modalities": ["text"],
            "answer": f"不符合。GJB 438C要求SRS包含6章"
                      f"（1范围/2引用文档/3需求/4合格性/5可追踪性/6注解），"
                      f"若缺少第{chapter}章则违反结构规范。",
            "answer_modality": "text",
            "inconsistency_type": "gjb_compliance", "subtype": "missing_chapter",
            "label": "inconsistent", "is_injected": True, "rule_id": "GJB-003",
            "inject_detail": f"删除第{chapter}章",
            "context_note": "此QA为注入场景: 原始文档文件未修改, inject_detail描述的是假设引入的错误。",
            "evidence": ev, "difficulty": "easy",
        })

    return qas


# ══════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════
def main():
    pairs = load_pairs()
    print(f"加载pair实例: {len(pairs)}个")

    # 按文档划分train/dev/test (MMQA风格)
    # train: 文档01-10, dev: 文档11-13, test: 文档14-16
    def get_split(doc_name):
        num = int(re.match(r'(\d+)', doc_name).group(1))
        if num <= 10:
            return "train"
        elif num <= 13:
            return "dev"
        else:
            return "test"

    all_qa = []
    qid_counter = 0

    for i, p in enumerate(pairs):
        doc = p["meta"].get("doc", "")
        split = get_split(doc)

        pair_qa = []
        pair_qa.extend(gen_terminology(p))
        pair_qa.extend(gen_parameter(p))
        pair_qa.extend(gen_logic(p))
        pair_qa.extend(gen_gjb(p))

        for qa in pair_qa:
            all_qa.append({
                "qid": f"srs_{split}_{qid_counter:05d}",
                "split": split,
                "pair_id": p["meta"]["instance_id"],
                **qa,
            })
            qid_counter += 1

        if (i + 1) % 50 == 0:
            print(f"  已处理 {i+1}/{len(pairs)}, 生成{len(all_qa)}条QA")

    # 保存
    json.dump(all_qa, open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 统计
    from collections import Counter
    by_split = Counter(q["split"] for q in all_qa)
    by_type = Counter(q["inconsistency_type"] for q in all_qa)
    by_label = Counter(q["label"] for q in all_qa)
    by_diff = Counter(q["difficulty"] for q in all_qa)
    by_mod = Counter(tuple(sorted(q["modalities"])) for q in all_qa)
    has_img = sum(1 for q in all_qa if "image" in q["modalities"])

    print(f"\n{'='*60}")
    print(f"✅ SRS测试数据集生成完成: {len(all_qa)}条 → {OUT_PATH}")
    print(f"\n按划分: {dict(by_split)}")
    print(f"按类型: {dict(by_type)}")
    print(f"按标签: {dict(by_label)}")
    print(f"按难度: {dict(by_diff)}")
    print(f"按模态: {dict(by_mod)}")
    print(f"含图片: {has_img}/{len(all_qa)}")


if __name__ == "__main__":
    main()
