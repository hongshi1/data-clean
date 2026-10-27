r"""LEGACY: pair-level mutation operators, not the new QA answer contract.

The active post-retrieval QA module uses ``algorithms.consistency.answer_mutations``.
This file is retained only for historical pair experiments and must not feed the
new benchmark without an explicit migration adapter and proof.

Historical Task 2: 48种变异算子 — 基于不一致类型的严格定义.

每种算子对应48种不一致类型之一, 数学形式:
  T_k: (x_p, x_h; θ, K) → (x'_p, x'_h, y'=inconsistent)
  其中K = K1(实体) + K2(模板) + K3(判别约束)

变异施加位置: x_p(premise) 或 x_h(hypothesis), 取决于类型语义.
有效性验证: 确定性规则(不依赖概率).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MutationRecord:
    operator: str
    target_type: str
    position: str
    original: str
    mutated: str
    is_valid: bool
    validation_note: str


@dataclass
class PairInput:
    premise: str
    hypothesis: str
    doc: str = ""
    section: str = ""


class MutationOperator(ABC):
    """变异算子基类."""
    name: str = "base"
    target_type: str = ""

    @abstractmethod
    def mutate(self, pair: PairInput, **kwargs) -> tuple[PairInput, MutationRecord]:
        ...

    def _record(self, pair: PairInput, original: str, mutated: str,
                valid: bool, note: str) -> tuple[PairInput, MutationRecord]:
        rec = MutationRecord(
            self.name, self.target_type,
            f"{pair.doc} {pair.section}" if pair.doc else pair.section,
            original, mutated, valid, note)
        if valid:
            return PairInput(premise=pair.premise, hypothesis=mutated,
                            doc=pair.doc, section=pair.section), rec
        return pair, rec


# ═══ TERM族(8种): 术语不一致 ═══

class TermSynonymSwap(MutationOperator):
    """TERM-01 同义异名: premise用A名,hypothesis保留B名(同义但不同名)."""
    name = "term_synonym_swap"
    target_type = "TERM-01"
    SYNONYMS = {"获取": "采集", "传输": "传送", "查询": "检索", "监控": "监视",
                "存储": "保存", "处理": "运算", "删除": "移除", "修改": "变更",
                "添加": "增加", "导入": "引入", "导出": "输出", "配置": "设定"}

    def mutate(self, pair, **kw):
        for old, new in self.SYNONYMS.items():
            # 在premise中替换,hypothesis保留原词 → 构成术语不一致
            if old in pair.premise and old in pair.hypothesis:
                mutated_p = pair.premise.replace(old, new, 1)
                rec = MutationRecord(self.name, self.target_type,
                                    pair.section, old, new, True,
                                    f"premise用{new},hypothesis保留{old}")
                return PairInput(premise=mutated_p, hypothesis=pair.hypothesis,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无同义词对")


class TermPolysemy(MutationOperator):
    """TERM-02 同名异义: 同一术语在两处指不同概念."""
    name = "term_polysemy"
    target_type = "TERM-02"
    POLYSEMS = {"安全模式": ["防护模式", "加密模式"], "正常模式": ["标准模式", "默认模式"],
                "服务": ["系统服务", "网络服务"], "数据": ["业务数据", "配置数据"]}

    def mutate(self, pair, **kw):
        for term, variants in self.POLYSEMS.items():
            if term in pair.hypothesis and variants[0] in pair.premise:
                mutated_h = pair.hypothesis.replace(term, variants[1], 1)
                rec = MutationRecord(self.name, self.target_type,
                                    pair.section, term, variants[1], True,
                                    f"同名「{term}」在两处指不同概念")
                return PairInput(premise=pair.premise, hypothesis=mutated_h,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无同名异义词")


class TermEnumMismatch(MutationOperator):
    """TERM-03 枚举集合不一致: 两处列举的集合不同."""
    name = "term_enum_mismatch"
    target_type = "TERM-03"

    def mutate(self, pair, **kw):
        # 找premise中的枚举列表(逗号/顿号分隔的2+项)
        enum_pat = re.compile(r"([、,，][^、,，\s]{2,10}){2,}")
        m = enum_pat.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无枚举列表")
        # 删除最后一项(制造集合不一致)
        items = re.split(r"[、,，]", pair.premise)
        if len(items) < 3:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "枚举项不足")
        removed = items[-1].strip()
        mutated = "、".join(items[:-1])
        # 验证: hypothesis中包含被删项
        if removed not in pair.hypothesis:
            return pair, MutationRecord(self.name, self.target_type, pair.section,
                                        removed, "(删)", False, "被删项不在hypothesis中")
        rec = MutationRecord(self.name, self.target_type, pair.section,
                            removed, "(已删除)", True,
                            f"premise枚举集缺少「{removed}」,hypothesis包含该项")
        return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                        doc=pair.doc, section=pair.section), rec


class TermUnitMismatch(MutationOperator):
    """TERM-06 量纲单位不一致: 同一参数用不同单位."""
    name = "term_unit_mismatch"
    target_type = "TERM-06"
    UNIT_EQ = [("ms", "毫秒"), ("s", "秒"), ("min", "分钟"), ("h", "小时"),
               ("GB", "G"), ("MB", "M"), ("KB", "K")]

    def mutate(self, pair, **kw):
        # 找premise中的 数值+单位
        num_pat = re.compile(r"(\d+\.?\d*)\s*(ms|s|min|h|GB|MB|KB)")
        m = num_pat.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无单位数值")
        val, unit = m.group(1), m.group(2)
        # 换算到不同单位(不换算值,只换单位表述 → 构成表述不一致)
        for u1, u2 in self.UNIT_EQ:
            if unit == u1:
                mutated = pair.premise[:m.start()] + val + u2 + pair.premise[m.end():]
                rec = MutationRecord(self.name, self.target_type, pair.section,
                                    f"{val}{u1}", f"{val}{u2}", True,
                                    f"单位表述不一致: {u1} vs {u2}")
                return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无匹配单位对")


# ═══ PARAM族(10种): 参数不一致 ═══

class ParamTimeConflict(MutationOperator):
    """PARAM-01 时间约束冲突: 同一时间参数不同值."""
    name = "param_time_conflict"
    target_type = "PARAM-01"
    TIME_PAT = re.compile(r"(不大于|不超过|不小于|至少|最多|为|等于)\s*(\d+\.?\d*)\s*(ms|s|秒|min|分钟|h|小时)")

    def mutate(self, pair, factor=2.0, **kw):
        matches = list(self.TIME_PAT.finditer(pair.premise))
        if not matches:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无时间参数")
        m = matches[0]
        old_val = float(m.group(2))
        new_val = old_val * factor
        if abs(new_val - old_val) < 0.01:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "等价变换")
        # 验证: hypothesis中同一参数的值与new_val不同
        h_matches = list(self.TIME_PAT.finditer(pair.hypothesis))
        for hm in h_matches:
            if hm.group(1) == m.group(1) and float(hm.group(2)) != new_val:
                mutated = pair.premise[:m.start()] + m.group(1) + f"{new_val:g}" + m.group(3) + pair.premise[m.end():]
                rec = MutationRecord(self.name, self.target_type, pair.section,
                                    m.group(), f"{m.group(1)}{new_val:g}{m.group(3)}", True,
                                    f"时间参数{old_val}→{new_val},与hypothesis冲突")
                return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "hypothesis无对应参数")


class ParamPeriodConflict(MutationOperator):
    """PARAM-02 周期参数冲突: 周期值变更."""
    name = "param_period_conflict"
    target_type = "PARAM-02"
    PERIOD_PAT = re.compile(r"(周期|间隔|频率)\D{0,10}(\d+\.?\d*)\s*(ms|s|秒|min|分钟|h|小时|Hz)")

    def mutate(self, pair, factor=2.0, **kw):
        m = self.PERIOD_PAT.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无周期参数")
        old_val = float(m.group(2))
        new_val = old_val * factor
        mutated = pair.premise[:m.start(2)] + f"{new_val:g}" + pair.premise[m.end(2):]
        # 验证: hypothesis中有不同值
        h_m = self.PERIOD_PAT.search(pair.hypothesis)
        if h_m and float(h_m.group(2)) != new_val:
            rec = MutationRecord(self.name, self.target_type, pair.section,
                                m.group(2), f"{new_val:g}", True,
                                f"周期参数{old_val}→{new_val}")
            return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                            doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "hypothesis无不同周期")


class ParamResourceConflict(MutationOperator):
    """PARAM-05 资源占用冲突: 资源数值变更."""
    name = "param_resource_conflict"
    target_type = "PARAM-05"
    RES_PAT = re.compile(r"(内存|CPU|磁盘|存储|带宽)\D{0,10}(\d+\.?\d*)\s*(GB|MB|KB|TB|%)")

    def mutate(self, pair, factor=2.0, **kw):
        m = self.RES_PAT.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无资源参数")
        old_val = float(m.group(2))
        new_val = old_val * factor
        mutated = pair.premise[:m.start(2)] + f"{new_val:g}" + pair.premise[m.end(2):]
        h_m = self.RES_PAT.search(pair.hypothesis)
        if h_m and float(h_m.group(2)) != new_val:
            rec = MutationRecord(self.name, self.target_type, pair.section,
                                f"{m.group(1)}{old_val}{m.group(3)}", f"{m.group(1)}{new_val}{m.group(3)}", True,
                                f"资源参数{old_val}→{new_val}")
            return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                            doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "hypothesis无对应资源参数")


class ParamValueRangeConflict(MutationOperator):
    """PARAM-06 值域范围冲突: 区间边界或操作符翻转."""
    name = "param_range_conflict"
    target_type = "PARAM-06"
    OP_FLIP = {"不大于": "不小于", "不超过": "不少于", "≤": "≥", "至少": "最多", "最多": "至少"}

    def mutate(self, pair, **kw):
        for old_op, new_op in self.OP_FLIP.items():
            if old_op in pair.premise:
                mutated = pair.premise.replace(old_op, new_op, 1)
                if old_op in pair.hypothesis:  # hypothesis保留原操作符
                    rec = MutationRecord(self.name, self.target_type, pair.section,
                                        old_op, new_op, True,
                                        f"操作符翻转: {old_op}→{new_op}")
                    return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                                    doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无操作符可翻转")


class ParamStorageConflict(MutationOperator):
    """PARAM-07 存储时长/容量冲突."""
    name = "param_storage_conflict"
    target_type = "PARAM-07"
    STORE_PAT = re.compile(r"(保存|存储|保留|备份)\D{0,10}(\d+\.?\d*)\s*(天|日|月|年|GB|MB|TB)")

    def mutate(self, pair, factor=2.0, **kw):
        m = self.STORE_PAT.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无存储参数")
        old_val = float(m.group(2))
        new_val = old_val * factor
        mutated = pair.premise[:m.start(2)] + f"{new_val:g}" + pair.premise[m.end(2):]
        rec = MutationRecord(self.name, self.target_type, pair.section,
                            f"{m.group(1)}{old_val}{m.group(3)}", f"{m.group(1)}{new_val}{m.group(3)}", True,
                            f"存储参数{old_val}→{new_val}")
        return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                        doc=pair.doc, section=pair.section), rec


# ═══ LOGIC族(11种): 逻辑不一致 ═══

class LogicOrderConflict(MutationOperator):
    """ORDER_CONFLICT 步骤顺序矛盾."""
    name = "logic_order_conflict"
    target_type = "ORDER_CONFLICT"
    SEQ_PAT = re.compile(r"(\d+)\s*[→到至]\s*(\d+)")

    def mutate(self, pair, **kw):
        m = self.SEQ_PAT.search(pair.premise)
        if not m or m.group(1) == m.group(2):
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无顺序模式")
        a, b = m.group(1), m.group(2)
        swapped = f"{b}→{a}"
        mutated = pair.premise[:m.start()] + swapped + pair.premise[m.end():]
        # 验证: hypothesis中有原始顺序
        h_m = self.SEQ_PAT.search(pair.hypothesis)
        if h_m and h_m.group() == m.group():
            rec = MutationRecord(self.name, self.target_type, pair.section,
                                m.group(), swapped, True, f"顺序{a}→{b}反转为{b}→{a}")
            return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                            doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "hypothesis无对应顺序")


class LogicBranchIncomplete(MutationOperator):
    """LOGIC-05 分支不完备: 删除一个分支/模式."""
    name = "logic_branch_incomplete"
    target_type = "LOGIC-05"

    def mutate(self, pair, **kw):
        # 找模式列表(如"正常模式、降级模式、故障模式")
        mode_pat = re.compile(r"((?:正常|降级|故障|应急|手动|自动|标准)[\u4e00-\u9fa5]{0,2}模式[、,，]?){2,}")
        m = mode_pat.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无模式列表")
        modes = re.findall(r"((?:正常|降级|故障|应急|手动|自动|标准)[\u4e00-\u9fa5]{0,2}模式)", m.group())
        if len(modes) < 2:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "模式不足2种")
        removed = modes[-1]
        remaining = "、".join(modes[:-1])
        mutated = pair.premise[:m.start()] + remaining + pair.premise[m.end():]
        # 验证: hypothesis中包含被删模式
        if removed in pair.hypothesis:
            rec = MutationRecord(self.name, self.target_type, pair.section,
                                removed, "(删)", True, f"premise缺少「{removed}」分支")
            return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                            doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "被删分支不在hypothesis中")


class LogicPriorityConflict(MutationOperator):
    """LOGIC-01 模式优先级冲突."""
    name = "logic_priority_conflict"
    target_type = "LOGIC-01"
    PRIOR_PAT = re.compile(r"(应急|手动|自动|标准)[\u4e00-\u9fa5]{0,2}模式.{0,5}优先")

    def mutate(self, pair, **kw):
        m = self.PRIOR_PAT.search(pair.premise)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无优先级声明")
        # 替换优先模式
        for old, new in [("应急", "自动"), ("手动", "自动"), ("自动", "应急")]:
            if old in m.group():
                mutated = pair.premise.replace(m.group(), m.group().replace(old, new), 1)
                rec = MutationRecord(self.name, self.target_type, pair.section,
                                    m.group(), m.group().replace(old, new), True,
                                    f"优先级模式{old}→{new}")
                return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无可替换优先级")


# ═══ GJB族(11种): 合规不一致 ═══

class GJBTestabilityViolation(MutationOperator):
    """GJB-01 可测试性违规: 插入模糊不可测语句."""
    name = "gjb_testability_violation"
    target_type = "GJB-01"
    VAGUE = ["系统应运行稳定", "系统应性能良好", "系统应可靠", "系统应高效"]

    def mutate(self, pair, **kw):
        # 在premise中插入模糊语句
        for vague in self.VAGUE:
            if vague not in pair.premise and vague not in pair.hypothesis:
                mutated = pair.premise + f" {vague}。"
                rec = MutationRecord(self.name, self.target_type, pair.section,
                                    "(无)", vague, True,
                                    f"插入不可测试的模糊语句「{vague}」")
                return PairInput(premise=mutated, hypothesis=pair.hypothesis,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无可用模糊语句")


class GJBFaultToleranceViolation(MutationOperator):
    """GJB-02 容错不完备: 删除容错相关条款."""
    name = "gjb_fault_tolerance_violation"
    target_type = "GJB-02"
    FT_KEYWORDS = ["容错", "异常处理", "故障恢复", "降级处理"]

    def mutate(self, pair, **kw):
        for kw in self.FT_KEYWORDS:
            if kw in pair.hypothesis:
                # 从hypothesis中删除容错关键词
                mutated = pair.hypothesis.replace(kw, "正常处理", 1)
                rec = MutationRecord(self.name, self.target_type, pair.section,
                                    kw, "正常处理", True,
                                    f"容错条款「{kw}」被替换为正常处理")
                return PairInput(premise=pair.premise, hypothesis=mutated,
                                doc=pair.doc, section=pair.section), rec
        return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无容错关键词")


class GJBAuditLogViolation(MutationOperator):
    """GJB-04 审计日志缺失: 删除审计要求."""
    name = "gjb_audit_violation"
    target_type = "GJB-04"

    def mutate(self, pair, **kw):
        audit_pat = re.compile(r"(审计|操作日志|日志记录|日志留存)")
        m = audit_pat.search(pair.hypothesis)
        if not m:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无审计关键词")
        mutated = pair.hypothesis.replace(m.group(), "", 1)
        rec = MutationRecord(self.name, self.target_type, pair.section,
                            m.group(), "(删除)", True, f"删除审计条款「{m.group()}」")
        return PairInput(premise=pair.premise, hypothesis=mutated,
                        doc=pair.doc, section=pair.section), rec


# ═══ 结构族(8种): 结构不一致 ═══

class StructureItemMissing(MutationOperator):
    """TABLE_ITEM_MISSING 表格条目缺失."""
    name = "structure_item_missing"
    target_type = "TABLE_ITEM_MISSING"

    def mutate(self, pair, **kw):
        items = re.findall(r"[「]([^「」]{2,15})[」]", pair.hypothesis)
        if not items:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无引号条目")
        target = items[0]
        if target not in pair.premise:
            return pair, MutationRecord(self.name, self.target_type, pair.section,
                                        target, "(删)", False, "条目不在premise中")
        mutated_h = pair.hypothesis.replace(f"「{target}」", "", 1)
        mutated_h = re.sub(r"[、,,，]\s*[、,,，]", "、", mutated_h)
        rec = MutationRecord(self.name, self.target_type, pair.section,
                            f"「{target}」", "(删除)", True,
                            f"删除premise中存在的条目「{target}」")
        return PairInput(premise=pair.premise, hypothesis=mutated_h,
                        doc=pair.doc, section=pair.section), rec


class StructureActorMissing(MutationOperator):
    """ACTOR_MISSING 参与者缺失."""
    name = "structure_actor_missing"
    target_type = "ACTOR_MISSING"

    def mutate(self, pair, **kw):
        actors = re.findall(r"(?:参与者|Actor|操作者|执行者)[：:]?\s*[「]?([^「」。,，\s]{2,8})[」]?", pair.hypothesis)
        if not actors:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无参与者声明")
        actor = actors[0]
        if actor not in pair.premise:
            return pair, MutationRecord(self.name, self.target_type, pair.section,
                                        actor, "(删)", False, "参与者不在premise中")
        mutated = pair.hypothesis.replace(actor, "未指定", 1)
        rec = MutationRecord(self.name, self.target_type, pair.section,
                            actor, "未指定", True, f"参与者「{actor}」被替换为未指定")
        return PairInput(premise=pair.premise, hypothesis=mutated,
                        doc=pair.doc, section=pair.section), rec


class StructureStepMissing(MutationOperator):
    """STEP_MISSING 步骤缺失."""
    name = "structure_step_missing"
    target_type = "STEP_MISSING"
    STEP_PAT = re.compile(r"步骤\s*(\d+)[：:]\s*([^\n。]{5,50})")

    def mutate(self, pair, **kw):
        steps = list(self.STEP_PAT.finditer(pair.hypothesis))
        if not steps:
            return pair, MutationRecord(self.name, self.target_type, pair.section, "", "", False, "无步骤声明")
        # 删除最后一步
        last = steps[-1]
        step_content = last.group(2)[:20]
        if step_content not in pair.premise:
            return pair, MutationRecord(self.name, self.target_type, pair.section,
                                        step_content, "(删)", False, "步骤内容不在premise中")
        mutated = pair.hypothesis[:last.start()] + pair.hypothesis[last.end():]
        rec = MutationRecord(self.name, self.target_type, pair.section,
                             f"步骤{last.group(1)}", "(删除)", True,
                             f"删除步骤{last.group(1)}「{step_content}」")
        return PairInput(premise=pair.premise, hypothesis=mutated,
                        doc=pair.doc, section=pair.section), rec


# ═══ 算子注册表 ═══

OPERATORS = {
    # TERM族
    "TERM-01": TermSynonymSwap,
    "TERM-02": TermPolysemy,
    "TERM-03": TermEnumMismatch,
    "TERM-06": TermUnitMismatch,
    # PARAM族
    "PARAM-01": ParamTimeConflict,
    "PARAM-02": ParamPeriodConflict,
    "PARAM-05": ParamResourceConflict,
    "PARAM-06": ParamValueRangeConflict,
    "PARAM-07": ParamStorageConflict,
    # LOGIC族
    "ORDER_CONFLICT": LogicOrderConflict,
    "LOGIC-01": LogicPriorityConflict,
    "LOGIC-05": LogicBranchIncomplete,
    # GJB族
    "GJB-01": GJBTestabilityViolation,
    "GJB-02": GJBFaultToleranceViolation,
    "GJB-04": GJBAuditLogViolation,
    # 结构族
    "TABLE_ITEM_MISSING": StructureItemMissing,
    "ACTOR_MISSING": StructureActorMissing,
    "STEP_MISSING": StructureStepMissing,
}


def get_operator(type_code: str) -> MutationOperator | None:
    """获取指定类型的变异算子."""
    cls = OPERATORS.get(type_code)
    return cls() if cls else None


def get_available_types() -> list[str]:
    """返回当前可用的变异类型."""
    return list(OPERATORS.keys())


# ═══ QA模板 ═══

QA_TEMPLATES = {
    "PARAM-01": {
        "判别型": "陈述A说「{item}」{orig}，陈述B说{mut}。是否一致？",
        "定位型": "「{item}」的不一致出现在哪两个位置？",
        "解释型": "为什么「{item}」的{orig}与{mut}构成不一致？",
        "修复型": "应如何修改使「{item}」两处描述一致？",
    },
    "TERM-01": {
        "判别型": "陈述A用「{orig}」表述，陈述B用「{mut}」。术语是否一致？",
        "定位型": "术语不一致出现在哪个位置？",
        "解释型": "为什么「{orig}」和「{mut}」构成术语不一致？",
        "修复型": "应统一使用哪个术语？",
    },
    "TABLE_ITEM_MISSING": {
        "判别型": "陈述A包含「{orig}」，陈述B中缺失。是否一致？",
        "定位型": "哪个条目在不一致中缺失？",
        "解释型": "为什么「{orig}」的缺失构成不一致？",
        "修复型": "应在哪个位置补回「{orig}」？",
    },
    "ORDER_CONFLICT": {
        "判别型": "陈述A的顺序为{orig}，陈述B为{mut}。是否一致？",
        "定位型": "顺序不一致出现在哪个位置？",
        "解释型": "为什么顺序{orig}与{mut}构成不一致？",
        "修复型": "应如何调整顺序使其一致？",
    },
    "GJB-01": {
        "判别型": "陈述中出现了「{mut}」这样的描述。是否满足可测试性要求？",
        "定位型": "可测试性问题出现在哪个位置？",
        "解释型": "为什么「{mut}」不满足GJB可测试性要求？",
        "修复型": "应如何修改「{mut}」使其可测试？",
    },
    "default": {
        "判别型": "陈述A和陈述B是否一致？",
        "定位型": "不一致出现在哪个位置？",
        "解释型": "为什么不一致？",
        "修复型": "应如何修改使其一致？",
    },
}


def generate_qa(mutated: PairInput, record: MutationRecord, qa_type: str) -> dict | None:
    """生成QA样本(含质控)."""
    templates = QA_TEMPLATES.get(record.target_type, QA_TEMPLATES["default"])
    template = templates.get(qa_type)
    if not template:
        return None

    fill = {"item": record.original[:15], "orig": record.original, "mut": record.mutated}
    empty = [k for k in re.findall(r"\{(\w+)\}", template) if not fill.get(k)]
    if empty:
        return None

    question = template.format(**fill)
    is_inc = record.is_valid

    if qa_type == "判别型":
        answer = f"{'不一致' if is_inc else '一致'}。{record.validation_note}"
    elif qa_type == "定位型":
        answer = f"不一致出现在{record.position}"
    elif qa_type == "解释型":
        answer = record.validation_note
    else:
        answer = f"应将{record.mutated}修改为{record.original}"

    return {
        "qa_type": qa_type, "question": question, "answer": answer,
        "label": "inconsistent" if is_inc else "consistent",
        "type": record.target_type, "location": record.position,
        "explanation": record.validation_note,
        "evidence": [
            {"content": mutated.premise[:100], "modality": "text"},
            {"content": mutated.hypothesis[:100], "modality": "text"},
        ],
        "provenance": {"operator": record.operator, "pair_premise": record.original},
    }
