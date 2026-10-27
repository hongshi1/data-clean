"""κ_P正文编译器(最小版): GJB正文 → 结构化特征三元组.

补齐方向A"正文模态缺位"的第一块板:
  行为(verb+object) / 枚举清单(功能列表) / 数值约束(op+value+unit) /
  交叉引用(图表节) / 需求ID / 句级语义角色

设计原则(与κ_T一致):
  - 纯确定性正则 → FACT, 置信度1.0("文档字面说了什么"的忠实读取)
  - 解析不做什么语义判断(那是方向B的事) —— 只把字面结构化
"""
from __future__ import annotations

import re
from typing import Any

# ═══════════════════════════════════════════════════════════════
# 模式库
# ═══════════════════════════════════════════════════════════════

SENT_SPLIT = re.compile(r'(?<=[。；;])\s*')

# 修复旧ID正则的8字符前缀限制(05_method_roadmap已知缺陷#6: ZZSJHQZHFW漏检)
ID_PAT = re.compile(
    r'(?<![A-Za-z0-9-])[A-Z][A-Z0-9]{1,15}(?:-[A-Z0-9]{2,15}){2,}(?![A-Za-z0-9-])')

BEHAVIOR_VERBS = ('提供', '实现', '支持', '采用', '完成', '进行',
                  '具备', '包含', '包括', '具有', '分为')

ENUM_PAT = re.compile(r'(包括|包含|分为|划分为|采用)(?:以下|如下)?')

_OP_MAP = [('不低于', 'ge'), ('不超过', 'le'), ('不少于', 'ge'), ('不多于', 'le'),
           ('不大于', 'le'), ('不小于', 'ge'),
           ('至少', 'ge'), ('最多', 'le'), ('大于', 'gt'), ('小于', 'lt'),
           ('≥', 'ge'), ('≤', 'le'), ('＞', 'gt'), ('＜', 'lt')]

UNIT = (r'(?:GB|TB|MB|KB|Gbps|Mbps|kbps|Kbps|ms|us|μs|Hz|kHz|MHz|GHz|%'
        r'|小时|分钟|分|秒|个|条|路|核|位|字节)')
CONSTRAINT_PAT = re.compile(
    r'(不低于|不超过|不少于|不多于|不大于|不小于|至少|最多|大于|小于|≥|≤|＞|＜)'
    r'\s*(\d+(?:\.\d+)?)\s*(' + UNIT + r')?')

FIGTAB_PAT = re.compile(r'(?:如|见|参见)?\s*([图表])\s*(\d+)')
SECTION_PAT = re.compile(r'第?\s*(\d+(?:\.\d+){1,4})\s*节')

# 枚举项切割: 顿号/逗号/和/与
ENUM_SPLIT = re.compile(r'[、,，]|和|与')
# 枚举尾部的"等"概括
ENUM_TAIL = re.compile(r'等(?:方式|手段|工具|类型|措施|形式)?$')

PARAM_HINT_PAT = re.compile(r'([\u4e00-\u9fffA-Za-z0-9]{2,10})$')


def _op_symbol(op: str) -> str:
    return dict(_OP_MAP).get(op, op)


# ═══════════════════════════════════════════════════════════════
# 主编译
# ═══════════════════════════════════════════════════════════════

def compile_prose(text: str, subject_hint: str = "") -> dict[str, Any]:
    """GJB正文段 → {behaviors, enumerations, constraints, references, ids, roles}.

    subject_hint: 章节标题(提供"谁在提供/实现"的语境线索, 仅记录不推断).
    """
    sentences = [s.strip() for s in SENT_SPLIT.split(text or "") if s.strip()]
    behaviors: list[dict[str, Any]] = []
    enumerations: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    roles: dict[int, str] = {}
    ids: list[str] = []

    for idx, sent in enumerate(sentences):
        role = "overview"

        # 1) 数值约束 (优先级最高: 约束句>枚举句>引用句>行为句)
        for m in CONSTRAINT_PAT.finditer(sent):
            prefix = sent[:m.start()]
            hm = PARAM_HINT_PAT.search(prefix)
            constraints.append({
                "op": _op_symbol(m.group(1)), "value": float(m.group(2)),
                "unit": m.group(3) or "", "param_hint": hm.group(0) if hm else "",
                "sent_idx": idx, "text": sent[:80],
            })
            role = "constraint"

        # 2) 枚举清单(精度优先: 截到首个逗号/句号, 再剥"等"概括尾)
        em = ENUM_PAT.search(sent)
        if em:
            rest = re.split(r'[。；;，,]', sent[em.end():])[0]
            rest = ENUM_TAIL.sub('', rest)
            items = [it.strip() for it in ENUM_SPLIT.split(rest)
                     if len(it.strip()) >= 3]
            if items:
                enumerations.append({
                    "keyword": em.group(1), "items": items,
                    "sent_idx": idx, "text": sent[:80],
                })
                if role == "overview":
                    role = "enumeration"

        # 3) 交叉引用
        for m in FIGTAB_PAT.finditer(sent):
            references.append({
                "kind": "figure" if m.group(1) == '图' else "table",
                "target": m.group(2), "sent_idx": idx,
            })
        for m in SECTION_PAT.finditer(sent):
            references.append({
                "kind": "section", "target": m.group(1), "sent_idx": idx,
            })
        if references and any(r["sent_idx"] == idx for r in references):
            if role == "overview":
                role = "reference"

        # 4) 行为(动词+宾语)
        for verb in BEHAVIOR_VERBS:
            pos = sent.find(verb)
            if pos < 0:
                continue
            after = sent[pos + len(verb):]
            obj = re.split(r'[。；;，,、]', after)[0][:30]
            if obj:
                behaviors.append({
                    "verb": verb, "object": obj, "sent_idx": idx,
                    "subject_hint": subject_hint,
                })
                if role == "overview":
                    role = "behavior"
            break

        # 5) 需求ID
        for m in ID_PAT.finditer(sent):
            gid = m.group(0)
            if gid not in ids:
                ids.append(gid)

        roles[idx] = role

    return {
        "n_sentences": len(sentences),
        "subject_hint": subject_hint,
        "sentence_roles": roles,
        "behaviors": behaviors,
        "enumerations": enumerations,
        "constraints": constraints,
        "references": references,
        "ids": ids,
        "n_features": (len(behaviors) + len(enumerations) + len(constraints)
                       + len(references) + len(ids)),
    }


def prose_item_names(compiled: dict[str, Any]) -> list[str]:
    """枚举项扁平化(供semantic_links与表格项对齐)."""
    return [it for en in compiled.get("enumerations", []) for it in en.get("items", [])]
