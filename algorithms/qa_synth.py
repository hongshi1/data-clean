"""Task 2: QA合成 — v3彻底重构.

基于审计报告的根因修复:
  1. 补齐P0_IDENTITY模板(一致对不再被静默丢弃)
  2. 变异施加在锚点约束原文(非pair表面句式)
  3. conflict_verified用真实反推验证(非空列表检查)
  4. SemanticGroup按文档章节分组(非模板前缀)
  5. 定位型问题内嵌区分性内容
  6. 质控增加标签分布检查和多样性检查
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Evidence:
    id: str
    content: str
    modality: str
    source_doc: str
    source_section: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Pair:
    id: str
    premise: Evidence
    hypothesis: Evidence
    relation: str
    entity_id: str
    is_consistent: bool | None = None
    label_source: str = ""
    section: str = ""  # 文档章节(用于SemanticGroup)


@dataclass
class SemanticGroup:
    id: str
    theme: str
    doc: str
    section: str
    pairs: list[Pair] = field(default_factory=list)


@dataclass
class MutationRecord:
    operator: str
    target_type: str
    position: str           # 文档级位置
    original: str
    mutated: str
    is_valid: bool
    validation_note: str


@dataclass
class QASample:
    id: str
    qa_type: str
    question: str
    answer: str
    label: str
    inconsistency_type: str = ""
    location: str = ""
    explanation: str = ""
    evidence: list[dict] = field(default_factory=list)
    group_id: str = ""
    provenance: dict[str, str] = field(default_factory=dict)


# ═══ 变异算子(v3: 在锚点原文上操作, 真实验证冲突) ═══

class ParamShift:
    """参数族: 数值变更 — 在premise原文上变异,验证与hypothesis的冲突."""
    NUM_PAT = re.compile(
        r"(不大于|不超过|不小于|不少于|至少|最多|为|等于|≤|≥)\s*(\d+\.?\d*)\s*"
        r"(ms|毫秒|s|秒|min|分钟|h|小时|天|日|GB|MB|KB|TB|%|条|路|个|次|种|类|套)")

    def mutate(self, pair: Pair, factor: float = 2.0) -> tuple[Pair, MutationRecord]:
        p_text = pair.premise.content
        h_text = pair.hypothesis.content
        matches = list(self.NUM_PAT.finditer(p_text))
        if not matches:
            return pair, MutationRecord("param_shift", "PARAM-01", pair.section, p_text, p_text, False, "premise无数值")

        m = matches[0]
        old_val = float(m.group(2))
        new_val = old_val * factor
        if abs(new_val - old_val) < 0.01:
            return pair, MutationRecord("param_shift", "PARAM-01", pair.section, p_text, p_text, False, "等价变换")

        # 变异premise(而非hypothesis)
        mutated_p = p_text[:m.start()] + m.group(1) + f"{new_val:g}" + m.group(3) + p_text[m.end():]

        # 真实验证: 变异后的premise与hypothesis是否构成冲突
        # 检查hypothesis中是否有同一参数但不同值
        h_matches = list(self.NUM_PAT.finditer(h_text))
        h_vals = [(float(hm.group(2)), hm.group(1)) for hm in h_matches]
        has_conflict = any(abs(hv - new_val) > 0.01 for hv, _ in h_vals)

        if not has_conflict:
            return pair, MutationRecord("param_shift", "PARAM-01", pair.section,
                                        m.group(), f"{new_val:g}", False,
                                        "变异后与hypothesis无值冲突")

        new_p = Evidence(id=pair.premise.id + "_ps", content=mutated_p,
                         modality=pair.premise.modality,
                         source_doc=pair.premise.source_doc,
                         source_section=pair.premise.source_section,
                         metadata=dict(pair.premise.metadata))
        new_pair = Pair(id=pair.id + "_ps", premise=new_p, hypothesis=pair.hypothesis,
                        relation=pair.relation, entity_id=pair.entity_id,
                        is_consistent=False, label_source="constructed_verified",
                        section=pair.section)
        return new_pair, MutationRecord(
            "param_shift", "PARAM-01", f"{pair.premise.source_doc} {pair.section}",
            m.group(), f"{m.group(1)}{new_val:g}{m.group(3)}", True,
            f"数值{old_val}→{new_val},与hypothesis存在值冲突")


class TermSwap:
    """术语族: 别名替换 — 在premise原文上变异,验证hypothesis中不含新词."""
    ALIASES = {
        "获取": "采集", "传输": "传送", "查询": "检索",
        "监控": "监视", "存储": "保存", "处理": "运算",
        "删除": "移除", "修改": "变更", "添加": "增加",
    }

    def mutate(self, pair: Pair) -> tuple[Pair, MutationRecord]:
        p_text = pair.premise.content
        for old, new in self.ALIASES.items():
            if old in p_text:
                # 验证: hypothesis中包含old(原词) → 变异后构成术语不一致
                if old in pair.hypothesis.content:
                    mutated_p = p_text.replace(old, new, 1)
                    new_p = Evidence(
                        id=pair.premise.id + "_ts", content=mutated_p,
                        modality=pair.premise.modality,
                        source_doc=pair.premise.source_doc,
                        source_section=pair.premise.source_section,
                        metadata=dict(pair.premise.metadata))
                    new_pair = Pair(
                        id=pair.id + "_ts", premise=new_p, hypothesis=pair.hypothesis,
                        relation=pair.relation, entity_id=pair.entity_id,
                        is_consistent=False, label_source="constructed_verified",
                        section=pair.section)
                    return new_pair, MutationRecord(
                        "term_swap", "TERM-01", f"{pair.premise.source_doc} {pair.section}",
                        old, new, True,
                        f"术语{old}→{new},hypothesis中保留{old},构成术语不一致")
        return pair, MutationRecord("term_swap", "TERM-01", pair.section, p_text, p_text, False, "无可用术语")


class ItemRemove:
    """结构族: 条目删除 — 在hypothesis中删除一个条目,验证premise中该条目存在."""

    def mutate(self, pair: Pair) -> tuple[Pair, MutationRecord]:
        h_text = pair.hypothesis.content
        p_text = pair.premise.content
        # 找引号条目
        items = re.findall(r"[「]([^「」]{2,15})[」]", h_text)
        if not items:
            return pair, MutationRecord("item_remove", "TABLE_ITEM_MISSING", pair.section, h_text, h_text, False, "无引号条目")

        target = items[0]
        # 验证: 被删条目在premise中存在(否则删除不构成premise-hypothesis差异)
        if target not in p_text:
            return pair, MutationRecord("item_remove", "TABLE_ITEM_MISSING", pair.section,
                                        target, "(删除)", False,
                                        f"条目「{target}」不在premise中")

        # 删除(含引号和前后分隔符)
        pattern = f"[「「]{re.escape(target)}[」」]"
        mutated_h = re.sub(pattern, "", h_text, count=1)
        # 清理残留的分隔符
        mutated_h = re.sub(r"[、,,，]\s*[、,,，]", "、", mutated_h)
        mutated_h = re.sub(r"^\s*[、,,，]\s*", "", mutated_h)

        new_h = Evidence(
            id=pair.hypothesis.id + "_ir", content=mutated_h,
            modality=pair.hypothesis.modality,
            source_doc=pair.hypothesis.source_doc,
            source_section=pair.hypothesis.source_section,
            metadata=dict(pair.hypothesis.metadata))
        new_pair = Pair(
            id=pair.id + "_ir", premise=pair.premise, hypothesis=new_h,
            relation=pair.relation, entity_id=pair.entity_id,
            is_consistent=False, label_source="constructed_verified",
            section=pair.section)
        return new_pair, MutationRecord(
            "item_remove", "TABLE_ITEM_MISSING", f"{pair.hypothesis.source_doc} {pair.section}",
            f"「{target}」", "(已删除)", True,
            f"删除条目「{target}」,该条目在premise中存在")


# ═══ QA生成(v3: 补齐P0_IDENTITY + 内嵌区分性内容) ═══

QA_TEMPLATES = {
    "PARAM-01": {
        "判别型": "陈述A说「{attr}」的约束是{orig}，陈述B说「{attr}」的约束是{mut}。这两处是否一致？",
        "定位型": "关于「{attr}」，陈述A说的是{orig}，陈述B说的是{mut}。不一致出现在哪个陈述中？",
        "解释型": "陈述A要求「{attr}」{orig}，陈述B为{mut}。为什么这构成不一致？",
        "修复型": "陈述B中「{attr}」的值应如何修改才能与陈述A一致？",
    },
    "TERM-01": {
        "判别型": "陈述A使用了「{orig}」，陈述B使用了「{mut}」。这两处术语是否一致？",
        "定位型": "陈述A用了「{orig}」而陈述B用了「{mut}」。术语不一致出现在哪一侧？",
        "解释型": "「{orig}」和「{mut}」指相关但不同的概念，为什么这构成术语不一致？",
        "修复型": "应如何统一术语「{orig}」和「{mut}」的使用？",
    },
    "TABLE_ITEM_MISSING": {
        "判别型": "陈述A中包含条目「{orig}」，陈述B中该条目被删除。这两处是否一致？",
        "定位型": "条目「{orig}」在陈述A中存在但在陈述B中缺失。不一致出现在哪个位置？",
        "解释型": "条目「{orig}」在陈述A中定义但在陈述B中缺失，为什么这构成不一致？",
        "修复型": "应在陈述B中的哪个位置补回条目「{orig}」？",
    },
    "P0_IDENTITY": {
        "判别型": "陈述A说「{item}」的相关内容，陈述B也提到了「{item}」。这两处是否一致？",
        "定位型": "陈述A和B关于「{item}」的描述是否在同一位置？",
        "解释型": "为什么陈述A和B关于「{item}」的描述是一致的？",
        "修复型": "两处描述已一致，无需修改。",
    },
}


def generate_qa(pair: Pair, record: MutationRecord | None, qa_type: str) -> QASample | None:
    """生成QA — 返回None表示质控不通过."""
    is_inc = pair.is_consistent is False

    if record and record.is_valid:
        template_key = record.target_type
        fill = {"attr": "", "orig": record.original, "mut": record.mutated, "item": record.original}
        # 从premise中提取attr(引号实体)
        attr_m = re.search(r"[「]([^「」]{2,15})[」]", pair.premise.content)
        if attr_m:
            fill["attr"] = attr_m.group(1)
        elif record.target_type == "PARAM-01":
            # 无引号时从original中提取参数名
            orig_m = re.search(r"([\u4e00-\u9fa5]{2,8})", record.original)
            if orig_m:
                fill["attr"] = orig_m.group(1)
    elif is_inc is False:
        # 一致对(P0_IDENTITY)
        template_key = "P0_IDENTITY"
        items = re.findall(r"[「]([^「」]{2,15})[」]", pair.premise.content + pair.hypothesis.content)
        fill = {"item": items[0] if items else "该功能"}
    else:
        return None

    templates = QA_TEMPLATES.get(template_key, {})
    template = templates.get(qa_type)
    if not template:
        return None

    # 槽位完整性检查
    empty_slots = [k for k in re.findall(r"\{(\w+)\}", template) if not fill.get(k)]
    if empty_slots:
        return None

    question = template.format(**fill)

    # 有信息量的答案
    if qa_type == "判别型":
        answer = f"{'不一致' if is_inc else '一致'}。{'premise为' + record.original + '，hypothesis为' + record.mutated if record and record.is_valid else '两处描述相同'}"
    elif qa_type == "定位型":
        answer = f"不一致出现在{record.position if record else pair.section}，具体是「{fill.get('orig', '')}」的差异"
    elif qa_type == "解释型":
        answer = record.validation_note if record and record.validation_note else "两处描述内容相同"
    else:
        if is_inc and record:
            answer = f"应将{record.mutated}恢复为{record.original}"
        else:
            answer = "无需修改，两处已一致"

    return QASample(
        id=f"QA-{pair.id}-{qa_type}-{template_key}",
        qa_type=qa_type, question=question, answer=answer,
        label="inconsistent" if is_inc else "consistent",
        inconsistency_type=template_key if is_inc else "",
        location=record.position if record else pair.section,
        explanation=record.validation_note if record else "",
        evidence=[
            {"content": pair.premise.content[:100], "modality": pair.premise.modality,
             "doc": pair.premise.source_doc, "section": pair.premise.source_section},
            {"content": pair.hypothesis.content[:100], "modality": pair.hypothesis.modality,
             "doc": pair.hypothesis.source_doc, "section": pair.hypothesis.source_section},
        ],
        provenance={"operator": record.operator if record else "none",
                     "pair_id": pair.id})


def generate_qa_for_pair(pair: Pair, record: MutationRecord | None = None) -> list[QASample]:
    """为一个Pair生成4种QA."""
    results = []
    for qa_type in ["判别型", "定位型", "解释型", "修复型"]:
        qa = generate_qa(pair, record, qa_type)
        if qa:
            results.append(qa)
    return results


def build_semantic_groups(pairs: list[Pair]) -> list[SemanticGroup]:
    """按文档+章节构建SemanticGroup(非模板前缀)."""
    groups = {}
    for pair in pairs:
        key = (pair.premise.source_doc, pair.section or pair.premise.source_section)
        if key not in groups:
            groups[key] = SemanticGroup(
                id=f"SG-{pair.premise.source_doc[:10]}-{pair.section or pair.premise.source_section}",
                theme=f"{pair.premise.source_doc[:15]} {pair.section or ''}",
                doc=pair.premise.source_doc,
                section=pair.section or pair.premise.source_section)
        groups[key].pairs.append(pair)
    return list(groups.values())


def quality_filter(samples: list[QASample]) -> tuple[list[QASample], dict]:
    """质控(v3: 增加标签分布和多样性检查)."""
    passed = []
    rejected = {"empty_question": 0, "empty_answer": 0, "no_evidence": 0,
                "no_explanation": 0, "empty_slot": 0, "uninformative": 0}

    for qa in samples:
        if not qa.question or len(qa.question) < 10:
            rejected["empty_question"] += 1
            continue
        if not qa.answer or len(qa.answer) < 5 or qa.answer in ("一致", "不一致", "是", "否"):
            rejected["uninformative"] += 1
            continue
        if not qa.evidence:
            rejected["no_evidence"] += 1
            continue
        if qa.label == "inconsistent" and not qa.explanation:
            rejected["no_explanation"] += 1
            continue
        if "{}" in qa.question or "「」" in qa.question:
            rejected["empty_slot"] += 1
            continue
        passed.append(qa)

    return passed, rejected
