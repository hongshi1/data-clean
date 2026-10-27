r"""变异注入评测集构建(设计§6.5 robustness: 变异算子家族×漏检率矩阵).

受控注入: 在冻结QA(scene1_qa_frozen_v1, 91条)的answer上施加变异算子库
(48个注册算子: 41个refute语义 + 7个support对照)的变异, 产出期望verdict
=refute的注入实例, 供 tools/eval_mutation_detection.py 测量确定性符号层
(QAConsistencyModule use_experts=True)的检出率/漏检率矩阵.

两级算子执行:
  strict(library_proof)  直接调用算子库propose_*——自带证明门(显式冲突
                         才发gold), 发出即sound refute;
  adaptive(受控扰动)     算子语义的answer侧受控扰动: 参数从冻结evidence
                         派生(跨用例值替换/步骤重排/数值扰动/域外术语注入),
                         期望refute来自注入协议(变异破坏answer对evidence的
                         grounding). 开放scope证据下可判定性差异进入漏检
                         原因分析, 不伪造证明.

守卫:
  - 变异有效性: mutated_answer == original_answer → 跳过并计数;
  - support对照算子(恒等/单位换算/清单补全/追溯命中)不进注入集, 只计数;
  - 去重: (source_instance, operator, mutated_answer);
  - 每QA每算子族超上限时 seed=42 抽样.

落盘: data/gjb_438c/mutation_injection_evalset_v1.jsonl (+ _metadata.json)

用法:
  python tools/build_mutation_injection_eval.py [--max-per-family N]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_mutations import (  # noqa: E402
    AnswerMutationProposal,
    propose_abbreviation_expansion,
    propose_enum_explicit_conflict,
    propose_equivalent_numeric_surface,
    propose_exact_numeric_conflict,
    propose_explicit_quote_conflict,
    propose_numeric_identity,
    propose_out_of_range_conflict,
    propose_reversed_data_flow,
)
from algorithms.consistency.gjb_mutations import (  # noqa: E402
    propose_gjb01_quantifier_fabrication,
    propose_gjb02_fault_tolerance_exclusion,
    propose_gjb03_access_control_exclusion,
    propose_gjb04_audit_field_exclusion,
    propose_gjb05_trace_conflict,
    propose_gjb05_trace_match,
    propose_gjb06_alarm_element_exclusion,
    propose_gjb07_self_check_exclusion,
    propose_gjb08_power_loss_exclusion,
    propose_gjb09_input_validation_exclusion,
    propose_gjb10_rollback_fabrication,
    propose_gjb11_degraded_mode_exclusion,
)
from algorithms.consistency.logic_mutations import (  # noqa: E402
    propose_atomicity_conflict,
    propose_event_order_swap,
    propose_exception_strategy_swap as propose_logic_exception_swap,
    propose_permission_conflict,
    propose_priority_reversal,
    propose_recovery_mode_conflict,
    propose_redundancy_arbitration_swap,
    propose_research_scope_conflict,
)
from algorithms.consistency.param_mutations import param_operator_registry  # noqa: E402
from algorithms.consistency.qa_models import QAInput  # noqa: E402
from algorithms.consistency.structural_mutations import (  # noqa: E402
    propose_actor_role_list_mutation,
    propose_closed_list_add,
    propose_closed_list_remove,
    propose_exception_outcome_swap,
    propose_step_delete,
    propose_step_reorder,
)
from algorithms.consistency.term_mutations import (  # noqa: E402
    propose_command_action_swap,
    propose_definition_swap,
    propose_interface_id_conflict,
    propose_status_term_conflict,
)
from tools.build_answer_mutation_candidates import (  # noqa: E402
    current_git_sha,
    request_from_dict,
    sha256_file,
)

SCHEMA = "mutation_injection_evalset_v1"
BUILDER_VERSION = "build_mutation_injection_eval_v1"
SOURCE = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
OUT = BASE / "data/gjb_438c/mutation_injection_evalset_v1.jsonl"
FAMILIES = ("BASE", "STRUCT", "TERM", "PARAM", "LOGIC", "GJB")
SEED = 42


# ---------------------------------------------------------------- 算子注册表
@dataclass(frozen=True)
class InjectionOperator:
    operator_id: str
    family: str
    check_item: str
    strategy: str  # adaptive策略key; "" = 仅strict/support对照
    refute_semantics: bool  # False → support对照, 不进注入集


OPERATORS: tuple[InjectionOperator, ...] = (
    # BASE(8): answer_mutations.py
    InjectionOperator("ANSWER-NUM-IDENTITY-V1", "BASE", "TERM-06", "", False),
    InjectionOperator("ANSWER-NUM-EQ-CONFLICT-V1", "BASE", "TERM-06",
                      "numeric_eq_conflict", True),
    InjectionOperator("ANSWER-NUM-EQUIV-V1", "BASE", "TERM-06", "", False),
    InjectionOperator("ANSWER-QUOTE-EXPLICIT-CONFLICT-V1", "BASE", "TERM-01",
                      "quoted_term_swap", True),
    InjectionOperator("ANSWER-ENUM-EXPLICIT-CONFLICT-V1", "BASE", "TERM-03",
                      "enum_member_inject", True),
    InjectionOperator("ANSWER-TERM-08-EXPANSION-V1", "BASE", "TERM-08",
                      "", False),
    InjectionOperator("ANSWER-PARAM-06-OUT-OF-RANGE-V1", "BASE", "PARAM-06",
                      "numeric_out_of_range", True),
    InjectionOperator("ANSWER-LOGIC-04-REVERSED-FLOW-V1", "BASE", "LOGIC-04",
                      "reversed_flow", True),
    # STRUCT(7): structural_mutations.py
    InjectionOperator("ANSWER-STRUCT-CLOSED-LIST-ADD-SUPPORT-V2", "STRUCT",
                      "TERM-03", "", False),
    InjectionOperator("ANSWER-STRUCT-CLOSED-LIST-REMOVE-V1", "STRUCT",
                      "TERM-03", "enum_member_remove", True),
    InjectionOperator("ANSWER-STRUCT-STEP-REORDER-V1", "STRUCT", "LOGIC-05",
                      "step_reorder", True),
    InjectionOperator("ANSWER-STRUCT-STEP-DELETE-V1", "STRUCT", "LOGIC-05",
                      "step_delete", True),
    InjectionOperator("ANSWER-STRUCT-EXCEPTION-OUTCOME-SWAP-V1", "STRUCT",
                      "LOGIC-06", "e1_outcome_swap", True),
    InjectionOperator("ANSWER-STRUCT-ACTOR-ADD-SUPPORT-V2", "STRUCT",
                      "TERM-03", "", False),
    InjectionOperator("ANSWER-STRUCT-ACTOR-REMOVE-REFUTE-V2", "STRUCT",
                      "TERM-03", "actor_member_remove", True),
    # TERM(4): term_mutations.py
    InjectionOperator("ANSWER-TERM-02-DEFINITION-SWAP-V1", "TERM", "TERM-02",
                      "definition_swap", True),
    InjectionOperator("ANSWER-TERM-04-STATUS-CONFLICT-V1", "TERM", "TERM-04",
                      "status_term_inject", True),
    InjectionOperator("ANSWER-TERM-05-COMMAND-SWAP-V1", "TERM", "TERM-05",
                      "command_action_swap", True),
    InjectionOperator("ANSWER-TERM-07-INTERFACE-CONFLICT-V1", "TERM", "TERM-07",
                      "identifier_swap", True),
    # PARAM(9): param_mutations.py
    InjectionOperator("ANSWER-PARAM-01-TIME-CONFLICT-V1", "PARAM", "PARAM-01",
                      "param_time", True),
    InjectionOperator("ANSWER-PARAM-02-PERIOD-CONFLICT-V1", "PARAM", "PARAM-02",
                      "param_period", True),
    InjectionOperator("ANSWER-PARAM-03-THRESHOLD-CONFLICT-V1", "PARAM",
                      "PARAM-03", "param_threshold", True),
    InjectionOperator("ANSWER-PARAM-05-RESOURCE-CONFLICT-V1", "PARAM",
                      "PARAM-05", "param_resource", True),
    InjectionOperator("ANSWER-PARAM-07-RETENTION-CONFLICT-V1", "PARAM",
                      "PARAM-07", "param_retention", True),
    InjectionOperator("ANSWER-PARAM-08-SYNC-CONFLICT-V1", "PARAM", "PARAM-08",
                      "param_sync", True),
    InjectionOperator("ANSWER-PARAM-09-DEGRADE-CONFLICT-V1", "PARAM",
                      "PARAM-09", "param_degrade", True),
    InjectionOperator("ANSWER-PARAM-10-FAULT-CONFLICT-V1", "PARAM", "PARAM-10",
                      "param_fault", True),
    InjectionOperator("ANSWER-PARAM-NUM-EQUIV-SUPPORT-V1", "PARAM", "TERM-06",
                      "", False),
    # LOGIC(8): logic_mutations.py
    InjectionOperator("ANSWER-LOGIC-01-PRIORITY-REVERSAL-V1", "LOGIC",
                      "LOGIC-01", "priority_reversal", True),
    InjectionOperator("ANSWER-LOGIC-02-EXCEPTION-SWAP-V1", "LOGIC", "LOGIC-02",
                      "condition_action_swap", True),
    InjectionOperator("ANSWER-LOGIC-03-ORDER-SWAP-V1", "LOGIC", "LOGIC-03",
                      "event_order_swap", True),
    InjectionOperator("ANSWER-LOGIC-07-ATOMICITY-CONFLICT-V1", "LOGIC",
                      "LOGIC-07", "atomicity_flip", True),
    InjectionOperator("ANSWER-LOGIC-08-ARBITRATION-SWAP-V1", "LOGIC",
                      "LOGIC-08", "arbitration_swap", True),
    InjectionOperator("ANSWER-LOGIC-09-PERMISSION-CONFLICT-V1", "LOGIC",
                      "LOGIC-09", "permission_flip", True),
    InjectionOperator("ANSWER-LOGIC-10-RECOVERY-CONFLICT-V1", "LOGIC",
                      "LOGIC-10", "recovery_flip", True),
    InjectionOperator("ANSWER-LOGIC-11-SCOPE-CONFLICT-V1", "LOGIC", "LOGIC-11",
                      "scope_flip", True),
    # GJB(12): gjb_mutations.py
    InjectionOperator("ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1", "GJB",
                      "GJB-01", "quantifier_fabrication", True),
    InjectionOperator("ANSWER-GJB-02-FT-EXCLUSION-V1", "GJB", "GJB-02",
                      "gjb_ft_inject", True),
    InjectionOperator("ANSWER-GJB-03-ACL-EXCLUSION-V1", "GJB", "GJB-03",
                      "gjb_acl_inject", True),
    InjectionOperator("ANSWER-GJB-04-AUDIT-EXCLUSION-V1", "GJB", "GJB-04",
                      "gjb_audit_inject", True),
    InjectionOperator("ANSWER-GJB-05-TRACE-CONFLICT-V1", "GJB", "GJB-05",
                      "trace_redirect", True),
    InjectionOperator("ANSWER-GJB-05-TRACE-MATCH-V1", "GJB", "GJB-05",
                      "", False),
    InjectionOperator("ANSWER-GJB-06-ALARM-EXCLUSION-V1", "GJB", "GJB-06",
                      "gjb_alarm_inject", True),
    InjectionOperator("ANSWER-GJB-07-SELFTEST-EXCLUSION-V1", "GJB", "GJB-07",
                      "gjb_selftest_inject", True),
    InjectionOperator("ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1", "GJB", "GJB-08",
                      "gjb_powerloss_inject", True),
    InjectionOperator("ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1", "GJB", "GJB-09",
                      "gjb_inputguard_inject", True),
    InjectionOperator("ANSWER-GJB-10-ROLLBACK-CONFLICT-V1", "GJB", "GJB-10",
                      "rollback_fabrication", True),
    InjectionOperator("ANSWER-GJB-11-DEGRADE-EXCLUSION-V1", "GJB", "GJB-11",
                      "gjb_degrade_inject", True),
)

OPERATORS_BY_ID = {op.operator_id: op for op in OPERATORS}


@dataclass(frozen=True)
class MutationAttempt:
    operator: InjectionOperator
    answer_after: str
    mode: str  # library_proof | adaptive
    gold: str  # support | refute
    rationale: str


# ---------------------------------------------------------------- 共用模式
_ID = re.compile(r"(?<![A-Z0-9-])(PZXQ-[A-Z0-9]+(?:-[A-Z0-9]+)*)(?![A-Z0-9-])")
_STEP_SEG = re.compile(r"(?m)^[ \t]*(?P<no>\d+)\s*[.)、:：]\s*(?P<body>[^\n]{4,})")
_ENUM_ANS = re.compile(
    r"(?P<head>[^。；\n，]{0,24}(?:包括|包含|记录))(?:以下|如下)?(?P<colon>[：:]?)\s*"
    r"(?P<items>[^。；\n]{6,160})")
_NUM_SPAN = re.compile(
    r"(?<![A-Za-z0-9.\-])(?P<value>\d{1,10}(?:\.\d+)?)(?P<unit>"
    r"ms|毫秒|秒|s|min|分钟|GB|MB|KB|字节|B|%)?(?![0-9A-Za-z])")
_QUOTED = re.compile(r"[「\"](?P<term>[^「」\"]{2,80})[」\"]")
_E1_OUTCOME = re.compile(r"异常流E(?P<no>\d)[：:]\s*(?P<outcome>[^。；\n，,]{4,40})")
_ORDER = re.compile(r"先(?P<a>[^，。；\n]{2,20})[，,]?然后(?P<b>[^，。；\n]{2,20})")
_PRIORITY = re.compile(
    r"(?P<a>[A-Za-z\u4e00-\u9fff]{1,12})优先(?:级?高于|于)(?P<b>[A-Za-z\u4e00-\u9fff]{1,12})")
_FLOW = re.compile(
    r"(?P<src>[A-Za-z\u4e00-\u9fff]{2,10})(?:向|发送至|传输至)(?P<dst>[A-Za-z\u4e00-\u9fff]{2,10})")
_CONDITION_ACTION = re.compile(
    r"(?:应|须|必须|将|会)(?:执行|采取|进行|触发)?(?P<action>[^，。；\n]{3,16})")
_DEF_PAIR = re.compile(r"(?P<term>[A-Za-z\u4e00-\u9fff]{1,12})（(?P<gloss>[^）]{1,24})）")
_COMMAND = re.compile(
    r"指令(?P<name>[A-Za-z\u4e00-\u9fff]{1,12})"
    r"(?:（(?:执行)?(?P<action>[^）]{1,16})）|(?P<action2>[^，。；\n]{1,16}))")
_TRACE_REF = re.compile(
    r"(?:追溯|对应|映射|回溯)[^。；\n]{0,12}(?P<ref>\d+(?:\.\d+){1,3}(?:\s*[a-c]\)?)?)")
_CHAPTER_REF = re.compile(r"(?<!\d)(?:3|4|5)\.\d(?:\.\d+){0,3}(?!\d)")
_ENUM_POOL = re.compile(r"(?:包括|包含|分为|支持)[：:]?\s*(?P<items>[^。；\n]{8,120})")
_NEGATION_TERM = re.compile(
    r"(?:不包括|不包含|不支持|禁止|不得)[「\"]?([^，。；、\s「」\"]{2,30})")

# GJB域外术语注入词表(须不出现在该QA任何冻结evidence中才可用)
_GJB_VOCAB: dict[str, tuple[str, ...]] = {
    "gjb_ft_inject": ("双机热备", "故障自动迁移", "磁盘阵列冗余"),
    "gjb_acl_inject": ("强制访问控制", "角色继承机制", "最小权限原则"),
    "gjb_audit_inject": ("操作者IP地址", "会话唯一标识", "数据前像后像"),
    "gjb_alarm_inject": ("声光报警", "报警处置人", "报警恢复时间"),
    "gjb_selftest_inject": ("开机自检", "周期自检", "内存校验自检"),
    "gjb_powerloss_inject": ("运行日志掉电保护", "事务回滚掉电保护"),
    "gjb_inputguard_inject": ("正则表达式校验", "输入语法校验", "长度上限校验"),
    "gjb_degrade_inject": ("只读降级模式", "缓存旁路降级", "最小功能模式"),
}
_GJB_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "gjb_ft_inject": ("容错", "故障"),
    "gjb_acl_inject": ("权限", "访问控制"),
    "gjb_audit_inject": ("审计", "日志"),
    "gjb_alarm_inject": ("报警", "告警"),
    "gjb_selftest_inject": ("自检",),
    "gjb_powerloss_inject": ("掉电", "断电"),
    "gjb_inputguard_inject": ("校验", "输入防护"),
    "gjb_degrade_inject": ("降级",),
}
_STATUS_VOCAB = ("异常告警状态", "离线告警状态", "过载告警状态")

_PARAM_STRATEGY_UNITS: dict[str, tuple[str, ...]] = {
    "param_time": ("ms", "毫秒", "秒", "s", "min", "分钟"),
    "param_resource": ("GB", "MB", "KB", "字节", "B", "%"),
    "param_retention": ("GB", "MB", "KB", "字节", "B"),
}
_PARAM_STRATEGY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "param_time": ("响应时间", "处理时间", "时延", "延迟", "时间"),
    "param_period": ("周期", "频率", "间隔"),
    "param_threshold": ("阈值", "门限"),
    "param_resource": ("CPU", "内存", "磁盘", "占用", "带宽", "容量"),
    "param_retention": ("保存时长", "保存期限", "保留", "存储容量"),
    "param_sync": ("同步精度", "同步误差", "守时", "对齐误差", "误差", "精度"),
    "param_degrade": ("降级", "触发"),
    "param_fault": ("故障", "持续", "判定"),
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _evidence_compact(request: QAInput) -> str:
    return _compact("".join(ev.text for ev in request.evidence))


# ---------------------------------------------------------------- strict层
def strict_attempts(op: InjectionOperator,
                    request: QAInput) -> list[AnswerMutationProposal]:
    """算子库propose_*的证明门执行: kwargs从answer/evidence派生.

    仿 tools/build_answer_mutation_candidates.py 的派生逻辑并补齐GJB族;
    ValueError=形状不可证明, 由调用方计入not_applicable.
    """
    outs: list[AnswerMutationProposal] = []

    def _try(fn: Callable[..., AnswerMutationProposal],
             **kwargs: Any) -> AnswerMutationProposal | None:
        try:
            return fn(request, **kwargs)
        except ValueError:
            return None

    for evidence in request.evidence:
        eid = evidence.evidence_id
        oid = op.operator_id
        if oid == "ANSWER-NUM-IDENTITY-V1":
            p = _try(propose_numeric_identity, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-NUM-EQ-CONFLICT-V1":
            numeric = re.search(
                r"=\s*(\d+(?:\.\d+)?)|(?:为|等于)\s*(\d+(?:\.\d+)?)",
                request.answer)
            if numeric:
                value = float(next(v for v in numeric.groups() if v))
                p = _try(propose_exact_numeric_conflict,
                         evidence_id=eid,
                         mutated_value=value + max(abs(value) * 0.1, 1.0))
                if p:
                    outs.append(p)
        elif oid == "ANSWER-NUM-EQUIV-V1":
            unit = re.search(r"(ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节)",
                             request.answer)
            targets = {"s": "ms", "秒": "毫秒", "ms": "秒", "毫秒": "秒",
                       "GB": "MB", "MB": "KB", "KB": "B"}
            if unit and targets.get(unit.group(1)):
                p = _try(propose_equivalent_numeric_surface,
                         evidence_id=eid, target_unit=targets[unit.group(1)])
                if p:
                    outs.append(p)
        elif oid == "ANSWER-PARAM-06-OUT-OF-RANGE-V1":
            numeric = re.search(r"(?:为|等于|=)\s*(\d+(?:\.\d+)?)", request.answer)
            if numeric:
                value = float(numeric.group(1))
                p = _try(propose_out_of_range_conflict, evidence_id=eid,
                         mutated_value=value + max(abs(value) * 0.1, 1.0))
                if p:
                    outs.append(p)
        elif oid in ("ANSWER-QUOTE-EXPLICIT-CONFLICT-V1",
                     "ANSWER-ENUM-EXPLICIT-CONFLICT-V1"):
            fn = (propose_explicit_quote_conflict
                  if oid.startswith("ANSWER-QUOTE")
                  else propose_enum_explicit_conflict)
            kw_name = "contradicted_term" if fn is propose_explicit_quote_conflict \
                else "added_term"
            for m in _NEGATION_TERM.finditer(evidence.text):
                p = _try(fn, evidence_id=eid, **{kw_name: m.group(1)})
                if p:
                    outs.append(p)
                if len(outs) >= 3:
                    break
        elif oid == "ANSWER-TERM-08-EXPANSION-V1":
            p = _try(propose_abbreviation_expansion, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-LOGIC-04-REVERSED-FLOW-V1":
            p = _try(propose_reversed_data_flow, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid.startswith("ANSWER-STRUCT-"):
            outs.extend(_strict_struct(op, request, eid))
        elif oid == "ANSWER-TERM-02-DEFINITION-SWAP-V1":
            p = _try(propose_definition_swap, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-TERM-04-STATUS-CONFLICT-V1":
            for m in re.finditer(r"(?:不包括|不包含|无|不含|只有|仅有)"
                                 r"([^，。；、\s]{2,12})", evidence.text):
                p = _try(propose_status_term_conflict, evidence_id=eid,
                         excluded_status=m.group(1))
                if p:
                    outs.append(p)
                if len(outs) >= 2:
                    break
        elif oid == "ANSWER-TERM-05-COMMAND-SWAP-V1":
            p = _try(propose_command_action_swap, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-TERM-07-INTERFACE-CONFLICT-V1":
            p = _try(propose_interface_id_conflict, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid.startswith("ANSWER-PARAM-"):
            outs.extend(_strict_param(op, request, eid))
        elif oid == "ANSWER-LOGIC-01-PRIORITY-REVERSAL-V1":
            p = _try(propose_priority_reversal, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-LOGIC-02-EXCEPTION-SWAP-V1":
            for m in re.finditer(r"(?:不得|禁止|不能|不允许)(?:执行|采取|进行|使用)?"
                                 r"([^，。；\s]{2,12})", evidence.text):
                p = _try(propose_logic_exception_swap, evidence_id=eid,
                         prohibited_action=m.group(1))
                if p:
                    outs.append(p)
                if len(outs) >= 2:
                    break
        elif oid == "ANSWER-LOGIC-03-ORDER-SWAP-V1":
            p = _try(propose_event_order_swap, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-LOGIC-07-ATOMICITY-CONFLICT-V1":
            p = _try(propose_atomicity_conflict, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-LOGIC-08-ARBITRATION-SWAP-V1":
            p = _try(propose_redundancy_arbitration_swap, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-LOGIC-09-PERMISSION-CONFLICT-V1":
            for m in re.finditer(
                    r"(?:禁止|不允许|不能)(?P<role>[A-Za-z\u4e00-\u9fff]{2,8})"
                    r"(?:执行|进行|访问|使用|操作)?"
                    r"(?P<action>[A-Za-z\u4e00-\u9fff]{2,10})", evidence.text):
                p = _try(propose_permission_conflict, evidence_id=eid,
                         role=m.group("role"), action=m.group("action"))
                if p:
                    outs.append(p)
                if len(outs) >= 2:
                    break
        elif oid == "ANSWER-LOGIC-10-RECOVERY-CONFLICT-V1":
            p = _try(propose_recovery_mode_conflict, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-LOGIC-11-SCOPE-CONFLICT-V1":
            p = _try(propose_research_scope_conflict, evidence_id=eid)
            if p:
                outs.append(p)
        elif oid == "ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1":
            rules = [e for e in request.evidence if e.source_type == "rule"]
            if rules:
                for rid in _ID.findall(request.answer)[:1]:
                    p = _try(propose_gjb01_quantifier_fabrication,
                             evidence_id=eid,
                             rule_evidence_id=rules[0].evidence_id,
                             requirement_id=rid, criterion_claim="500ms以内")
                    if p:
                        outs.append(p)
        elif oid in _STRICT_GJB_EXCLUSION:
            compact_ev = _evidence_compact(request)
            compact_ans = _compact(request.answer)
            for term in _GJB_VOCAB[op.strategy]:
                if term in compact_ev or term in compact_ans:
                    continue
                p = _try(_STRICT_GJB_EXCLUSION[oid], evidence_id=eid, term=term)
                if p:
                    outs.append(p)
                break
        elif oid == "ANSWER-GJB-05-TRACE-CONFLICT-V1":
            for rid in _ID.findall(request.answer)[:1]:
                p = _try(propose_gjb05_trace_conflict, evidence_id=eid,
                         requirement_id=rid, mutated_test_id="TEST-FAKE-999")
                if p:
                    outs.append(p)
        elif oid == "ANSWER-GJB-05-TRACE-MATCH-V1":
            for rid in _ID.findall(request.answer)[:1]:
                p = _try(propose_gjb05_trace_match, evidence_id=eid,
                         requirement_id=rid)
                if p:
                    outs.append(p)
        elif oid == "ANSWER-GJB-10-ROLLBACK-CONFLICT-V1":
            for m in re.finditer(r"(?:不支持|未提供|不具备|不允许|禁止)"
                                 r"([^，。；\s]{2,12})", evidence.text):
                p = _try(propose_gjb10_rollback_fabrication, evidence_id=eid,
                         term=m.group(1))
                if p:
                    outs.append(p)
                if len(outs) >= 2:
                    break
        if len(outs) >= 3:
            break
    return outs


_STRICT_GJB_EXCLUSION: dict[str, Callable[..., AnswerMutationProposal]] = {
    "ANSWER-GJB-02-FT-EXCLUSION-V1": propose_gjb02_fault_tolerance_exclusion,
    "ANSWER-GJB-03-ACL-EXCLUSION-V1": propose_gjb03_access_control_exclusion,
    "ANSWER-GJB-04-AUDIT-EXCLUSION-V1": propose_gjb04_audit_field_exclusion,
    "ANSWER-GJB-06-ALARM-EXCLUSION-V1": propose_gjb06_alarm_element_exclusion,
    "ANSWER-GJB-07-SELFTEST-EXCLUSION-V1": propose_gjb07_self_check_exclusion,
    "ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1": propose_gjb08_power_loss_exclusion,
    "ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1":
        propose_gjb09_input_validation_exclusion,
    "ANSWER-GJB-11-DEGRADE-EXCLUSION-V1": propose_gjb11_degraded_mode_exclusion,
}


def _strict_struct(op: InjectionOperator, request: QAInput,
                   eid: str) -> list[AnswerMutationProposal]:
    evidence = next(e for e in request.evidence if e.evidence_id == eid)
    outs: list[AnswerMutationProposal] = []
    oid = op.operator_id
    if oid in ("ANSWER-STRUCT-STEP-REORDER-V1",
               "ANSWER-STRUCT-STEP-DELETE-V1"):
        step_numbers = [int(n) for n in re.findall(
            r"(?:^|[;；\n])\s*(\d+)\s*[.)、:：]", request.answer)]
        if len(step_numbers) < 2:
            return outs
        try:
            if oid.endswith("STEP-REORDER-V1"):
                outs.append(propose_step_reorder(
                    request, evidence_id=eid, first_step=1, second_step=2))
            else:
                outs.append(propose_step_delete(
                    request, evidence_id=eid, step_number=2))
        except ValueError:
            return outs
        return outs
    if oid == "ANSWER-STRUCT-EXCEPTION-OUTCOME-SWAP-V1":
        m = re.search(r"(?:不得|禁止|不能|不可|不应|不允许)\s*"
                      r"(?:执行|采取|选择)?\s*([^，,。；;]+)", evidence.text)
        if m:
            try:
                outs.append(propose_exception_outcome_swap(
                    request, evidence_id=eid,
                    mutated_outcome=m.group(1).strip()))
            except ValueError:
                pass
        return outs
    ev_enum = re.search(r"(?:清单为|枚举为|包括|包含)\s*[:：]?\s*([^。.!！？\n]+)",
                        evidence.text)
    an_enum = re.search(r"(?:清单为|枚举为|包括|包含)\s*[:：]?\s*([^。.!！？\n]+)",
                        request.answer)
    if not (ev_enum and an_enum):
        return outs
    ev_items = re.findall(r"[^、,，;；\s]+", ev_enum.group(1))
    an_items = re.findall(r"[^、,，;；\s]+", an_enum.group(1))
    add_semantics = oid in ("ANSWER-STRUCT-CLOSED-LIST-ADD-SUPPORT-V2",
                            "ANSWER-STRUCT-ACTOR-ADD-SUPPORT-V2")
    if add_semantics:
        members = list(dict.fromkeys(set(ev_items) - set(an_items)))[:1]
    else:
        members = (an_items if set(an_items) == set(ev_items)
                   else list(set(an_items) - set(ev_items)))[:1]
    for member in members:
        if oid.startswith("ANSWER-STRUCT-CLOSED"):
            fn = (propose_closed_list_add if add_semantics
                  else propose_closed_list_remove)
            try:
                outs.append(fn(request, evidence_id=eid, member=member))
            except ValueError:
                continue
        else:
            try:
                outs.append(propose_actor_role_list_mutation(
                    request, evidence_id=eid, member=member,
                    remove=not add_semantics))
            except ValueError:
                continue
    return outs


def _strict_param(op: InjectionOperator, request: QAInput,
                  eid: str) -> list[AnswerMutationProposal]:
    registry = param_operator_registry()
    check_item = op.check_item
    outs: list[AnswerMutationProposal] = []
    if check_item not in registry:
        return outs
    operator, operator_id, keywords = registry[check_item]
    if not any(kw in request.question for kw in keywords):
        return outs
    evidence = next(e for e in request.evidence if e.evidence_id == eid)
    numeric = re.search(r"(?P<value>\d+(?:\.\d+)?)"r"(ms|毫秒|s|秒|min|分钟|GB|MB|KB|B|字节|%)",
                        evidence.text)
    if not numeric:
        return outs
    base = float(numeric.group("value"))
    delta = max(abs(base) * 0.5, 1.0)
    for mutated in (base + delta, base - delta):
        try:
            outs.append(operator(request, evidence_id=eid,
                                 mutated_value=mutated, check_item=check_item,
                                 operator_id=operator_id,
                                 subject_keywords=keywords))
            break
        except ValueError:
            continue
    return outs


# ---------------------------------------------------------------- adaptive层
def _safe_numeric_spans(answer: str) -> list[re.Match[str]]:
    """answer中可安全扰动的数值span(排除节号/表号/步骤号/字母邻接token)."""
    out: list[re.Match[str]] = []
    for m in _NUM_SPAN.finditer(answer):
        start, end = m.span("value")
        value = m.group("value")
        prefix = answer[:start]
        if re.search(r"\d+\.$", prefix):
            continue  # 3.2.1/4.1.1式点链
        if re.match(r"\.\d", answer[end:]):
            continue
        line_start = answer.rfind("\n", 0, start) + 1
        if (re.fullmatch(r"\s*(?:\*\*)?", answer[line_start:start])
                and re.match(r"\s*[.)、:：]", answer[end:])):
            continue  # 步骤序号
        if not m.group("unit") and re.search(r"[表图步第]$", prefix):
            continue  # 表21/图3/第2
        if re.search(r"[A-Za-z]$", prefix) or re.match(r"[A-Za-z]", answer[end:]):
            continue  # E1/V7.6等字母邻接
        if value.count(".") > 1:
            continue
        out.append(m)
    return out


def _numeric_formula(value: float, kind: str) -> str:
    if kind == "eq":
        mutated = value + max(abs(value) * 0.1, 1.0)
    elif kind == "oor":
        mutated = value * 100 + 1
    else:
        mutated = value * 2 + 1
    return f"{mutated:g}"


def _step_segments(answer: str) -> list[tuple[int, int, int]] | None:
    """answer的连续编号步骤段[(start, end, no)]; 编号不连续返回None."""
    matches = list(_STEP_SEG.finditer(answer))
    if len(matches) < 2:
        return None
    numbers = [int(m.group("no")) for m in matches]
    if numbers != list(range(1, len(numbers) + 1)):
        return None
    spans = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(answer)
        spans.append((m.start(), end, int(m.group("no"))))
    return spans


def _enum_members(answer: str) -> list[tuple[re.Match[str], list[str]]]:
    result: list[tuple[re.Match[str], list[str]]] = []
    for m in _ENUM_ANS.finditer(answer):
        raw_items = re.split(r"[、，,]", m.group("items"))
        members = [re.sub(r"^[：:\s\d.)、]+", "", x).strip()
                   for x in raw_items]
        members = [x for x in members if 2 <= len(x) <= 30]
        if len(members) >= 2:
            result.append((m, members))
    return result


def _evidence_cross_terms(request: QAInput, exclude: str) -> list[str]:
    """evidence枚举成员词池(排除已在answer中出现的词)——跨域替换值来源."""
    terms: list[str] = []
    exclude_compact = _compact(exclude)
    for ev in request.evidence:
        blocks = [m.group("items") for m in _ENUM_POOL.finditer(ev.text)]
        blocks.extend(re.findall(
            r"[\u4e00-\u9fffA-Za-z0-9]{2,16}(?:、[\u4e00-\u9fffA-Za-z0-9]{2,16}){2,}",
            ev.text))
        for block in blocks:
            for term in re.split(r"[、，,；;]", block):
                term = re.sub(r"^[：:\s\d.)、]+", "", term).strip(" 。．.")
                if (2 <= len(term) <= 16
                        and _compact(term) not in exclude_compact
                        and not re.fullmatch(r"[\dA-Z.\-]+", term)):
                    terms.append(term)
    return list(dict.fromkeys(terms))


def _adaptive(request: QAInput, op: InjectionOperator,
              answer_after: str, rationale: str) -> MutationAttempt:
    return MutationAttempt(operator=op, answer_after=answer_after,
                           mode="adaptive", gold="refute", rationale=rationale)


def _adaptive_numeric(request: QAInput, op: InjectionOperator, *, kind: str,
                      gate: tuple[str, ...] | None = None,
                      units: tuple[str, ...] | None = None,
                      ) -> list[MutationAttempt]:
    answer = request.answer
    attempts: list[MutationAttempt] = []
    for m in _safe_numeric_spans(answer):
        unit = m.group("unit") or ""
        if units is not None and unit and unit not in units:
            continue
        if gate:
            window = answer[max(0, m.start() - 24):m.end() + 24]
            if not (any(kw in window for kw in gate)
                    or any(kw in request.question for kw in gate)):
                continue
        value = float(m.group("value"))
        new_value = _numeric_formula(value, kind)
        after = (answer[:m.start("value")] + new_value
                 + answer[m.end("value"):])
        if after == answer:
            continue
        attempts.append(_adaptive(
            request, op, after,
            f"受控数值变异: answer数值{m.group('value')}{unit}变异为{new_value}"
            f"{unit}({kind}); 原值来自evidence grounding, 变异破坏数值一致性, "
            "期望refute(注入协议)。"))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_step_reorder(request: QAInput,
                           op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    spans = _step_segments(answer)
    attempts: list[MutationAttempt] = []
    if not spans:
        return attempts
    for i in range(min(2, len(spans) - 1)):
        s_i, e_i, no_i = spans[i]
        s_j, e_j, no_j = spans[i + 1]
        after = answer[:s_i] + answer[s_j:e_j] + answer[s_i:e_i] + answer[e_j:]
        if after == answer:
            continue
        attempts.append(_adaptive(
            request, op, after,
            f"受控步骤重排: 步骤{no_i}与步骤{no_j}整体交换; "
            "破坏evidence对齐的步骤顺序, 期望refute(注入协议)。"))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_step_delete(request: QAInput,
                          op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    spans = _step_segments(answer)
    if not spans or len(spans) < 3:
        return []
    s_j, e_j, _ = spans[2 - 1]
    after = answer[:s_j] + answer[e_j:]
    matches = list(_STEP_SEG.finditer(after))
    for new_no, m in reversed(list(enumerate(matches, start=1))):
        if int(m.group("no")) != new_no:
            after = (after[:m.start("no")] + str(new_no)
                     + after[m.end("no"):])
    if after == answer:
        return []
    return [_adaptive(
        request, op, after,
        "受控步骤删除: 步骤2整体删除并重编号; 破坏evidence对齐的完整"
        "步骤序列, 期望refute(注入协议)。")]


def _adaptive_enum_remove(request: QAInput, op: InjectionOperator, *,
                          actor_gate: bool = False) -> list[MutationAttempt]:
    answer = request.answer
    if actor_gate and not re.search(r"(?:参与者|角色|actor|Actor)",
                                     answer + request.question):
        return []
    ev_compact = _evidence_compact(request)
    attempts: list[MutationAttempt] = []
    for m, members in _enum_members(answer):
        member = members[1] if len(members) > 1 else members[0]
        if _compact(member) not in ev_compact:
            continue  # 只删除evidence可定位的grounded成员
        raw = m.group("items")
        pos = raw.find(member)
        if pos < 0:
            continue
        seg_start = m.start("items") + pos
        seg_end = seg_start + len(member)
        if raw[pos + len(member):pos + len(member) + 1] in "、，,":
            seg_end += 1
        elif pos > 0 and raw[pos - 1] in "、，,":
            seg_start -= 1
        after = answer[:seg_start] + answer[seg_end:]
        if after == answer:
            continue
        attempts.append(_adaptive(
            request, op, after,
            f"受控枚举删元: 成员「{member}」从answer枚举删除"
            "(成员在evidence中登记); 枚举声明不再覆盖evidence登记项, "
            "期望refute(注入协议)。"))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_enum_inject(request: QAInput, op: InjectionOperator, *,
                          fabricated: tuple[str, ...] | None = None,
                          domain: str = "枚举") -> list[MutationAttempt]:
    answer = request.answer
    ev_compact = _evidence_compact(request)
    ans_compact = _compact(answer)
    if fabricated:
        candidates = [t for t in fabricated
                      if t not in ev_compact and t not in ans_compact]
    else:
        candidates = _evidence_cross_terms(request, answer)
    if not candidates:
        return []
    term = candidates[0]
    for m, members in _enum_members(answer):
        after = answer[:m.end("items")] + "、" + term + answer[m.end("items"):]
        if after == answer:
            continue
        return [_adaptive(
            request, op, after,
            f"受控枚举注入: 域外成员「{term}」加入{domain}声明"
            f"(answer原成员: {('、'.join(members[:3]))}等); "
            "该成员不在本QA冻结evidence的对应清单中, 期望refute(注入协议)。")]
    return []


def _adaptive_identifier_swap(request: QAInput,
                              op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    answer_ids = list(_ID.finditer(answer))
    if not answer_ids:
        return []
    ev_ids: list[str] = []
    for ev in request.evidence:
        ev_ids.extend(_ID.findall(ev.text))
    ev_ids = list(dict.fromkeys(ev_ids))
    ans_compact = _compact(answer)
    attempts: list[MutationAttempt] = []
    for m in answer_ids[:2]:
        current = m.group(0)
        replacement = next(
            (x for x in ev_ids
             if x != current and _compact(x) not in ans_compact), None)
        if replacement is None:
            replacement = current[:-2] + "ZZ"
            if replacement == current or replacement in ev_ids:
                continue
        after = answer[:m.start()] + replacement + answer[m.end():]
        if after == answer:
            continue
        attempts.append(_adaptive(
            request, op, after,
            f"受控标识符冲突: answer标识符{current}替换为{replacement}"
            "(evidence登记的其它实体标识/伪造变体); 同主体不同标识, "
            "期望refute(注入协议)。"))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_e1_outcome_swap(request: QAInput,
                              op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    ev_outcomes: list[str] = []
    for ev in request.evidence:
        ev_outcomes.extend(m.group("outcome")
                           for m in _E1_OUTCOME.finditer(ev.text))
    ev_outcomes = list(dict.fromkeys(ev_outcomes))
    attempts: list[MutationAttempt] = []
    for m in _E1_OUTCOME.finditer(answer):
        current = m.group("outcome")
        replacement = next((x for x in ev_outcomes if x != current), None)
        if replacement is None:
            continue
        after = (answer[:m.start("outcome")] + replacement
                 + answer[m.end("outcome"):])
        if after == answer:
            continue
        attempts.append(_adaptive(
            request, op, after,
            f"受控异常流结果错配: E{m.group('no')}结果「{current}」替换为"
            f"其它用例的「{replacement}」(跨用例E1模板内容); 异常处置结果"
            "与evidence登记错位, 期望refute(注入协议)。"))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_pattern_swap(request: QAInput, op: InjectionOperator,
                           pattern: re.Pattern[str],
                           build: Callable[[re.Match[str]], tuple[str, str] | None],
                           ) -> list[MutationAttempt]:
    answer = request.answer
    attempts: list[MutationAttempt] = []
    for m in pattern.finditer(answer):
        built = build(m)
        if built is None:
            continue
        after, rationale = built
        if after == answer:
            continue
        attempts.append(_adaptive(request, op, after, rationale))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_condition_action_swap(
        request: QAInput, op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    if not re.search(r"(?:异常|故障|失败|错误)", answer):
        return []
    ev_terms = _evidence_cross_terms(request, answer)
    if not ev_terms:
        return []

    def build(m: re.Match[str]) -> tuple[str, str] | None:
        action = m.group("action").strip()
        replacement = next((t for t in ev_terms if t != action), None)
        if replacement is None:
            return None
        after = answer[:m.start("action")] + replacement + answer[m.end("action"):]
        return after, (f"受控异常策略错配: 处置动作「{action}」替换为域外"
                       f"「{replacement}」; 与evidence规定的处置策略冲突, "
                       "期望refute(注入协议)。")

    return _adaptive_pattern_swap(request, op, _CONDITION_ACTION, build)


def _adaptive_order_swap(request: QAInput,
                         op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer

    def build(m: re.Match[str]) -> tuple[str, str] | None:
        a, b = m.group("a").strip(), m.group("b").strip()
        if a == b:
            return None
        after = answer[:m.start()] + f"先{b}，然后{a}" + answer[m.end():]
        return after, (f"受控时序倒置: 先{a}然后{b} → 先{b}然后{a}; "
                       "事件顺序与evidence声明相反, 期望refute(注入协议)。")

    return _adaptive_pattern_swap(request, op, _ORDER, build)


def _adaptive_priority_reversal(request: QAInput,
                                op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer

    def build(m: re.Match[str]) -> tuple[str, str] | None:
        a, b = m.group("a"), m.group("b")
        if a == b:
            return None
        after = answer[:m.start()] + f"{b}优先于{a}" + answer[m.end():]
        return after, (f"受控优先级反转: {a}优先于{b} → {b}优先于{a}; "
                       "与evidence优先级声明相反, 期望refute(注入协议)。")

    return _adaptive_pattern_swap(request, op, _PRIORITY, build)


def _adaptive_atomicity_flip(request: QAInput,
                             op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    pos = answer.find("不可中断")
    if pos < 0:
        return []
    after = answer.replace("不可中断", "可以中断", 1)
    return [_adaptive(request, op, after,
                      "受控原子性冲突: 不可中断→可以中断; "
                      "与evidence原子性声明相反, 期望refute(注入协议)。")]


def _adaptive_arbitration_swap(request: QAInput,
                               op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    pattern = re.compile(
        r"主(?P<a>[^，。；\n]{0,10})(?:故障|失效)(?:时|后)?[^。\n]{0,12}?"
        r"切换到备(?P<b>[^，。；\n]{0,10})")

    def build(m: re.Match[str]) -> tuple[str, str] | None:
        a, b = m.group("a").strip(), m.group("b").strip()
        after = answer[:m.start()] + f"备{b}故障时切换到主{a}" + answer[m.end():]
        return after, (f"受控主备切换反转: 主{a}故障切换到备{b} → "
                       f"备{b}故障切换到主{a}; 与evidence切换规则相反, "
                       "期望refute(注入协议)。")

    return _adaptive_pattern_swap(request, op, pattern, build)


def _adaptive_permission_flip(request: QAInput,
                              op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    pattern = re.compile(
        r"(?:禁止|不允许|不能)(?P<role>[A-Za-z\u4e00-\u9fff]{2,8})"
        r"(?:执行|进行|访问|使用|操作)?(?P<action>[A-Za-z\u4e00-\u9fff]{2,10})")

    def build(m: re.Match[str]) -> tuple[str, str] | None:
        role, action = m.group("role"), m.group("action")
        allowed = f"{role}可以执行{action}"
        after = answer[:m.start()] + allowed + answer[m.end():]
        return after, (f"受控权限冲突: 禁止{role}执行{action} → {allowed}; "
                       "与evidence禁令相反, 期望refute(注入协议)。")

    return _adaptive_pattern_swap(request, op, pattern, build)


def _adaptive_recovery_flip(request: QAInput,
                            op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    if "自动恢复" not in answer:
        return []
    after = answer.replace("自动恢复", "手动恢复", 1)
    return [_adaptive(request, op, after,
                      "受控恢复方式冲突: 自动恢复→手动恢复; "
                      "与evidence恢复方式声明相反, 期望refute(注入协议)。")]


def _adaptive_scope_flip(request: QAInput,
                         op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    m = re.search(r"仅(?P<scope>增量|全量)(?:搜索|检索|查找)", answer)
    if not m:
        return []
    opposite = "全量" if m.group("scope") == "增量" else "增量"
    after = answer[:m.start("scope")] + opposite + answer[m.end("scope"):]
    return [_adaptive(request, op, after,
                      f"受控搜索范围冲突: 仅{m.group('scope')}→仅{opposite}; "
                      "与evidence范围声明相反, 期望refute(注入协议)。")]


def _adaptive_reversed_flow(request: QAInput,
                            op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer

    def build(m: re.Match[str]) -> tuple[str, str] | None:
        src, dst = m.group("src"), m.group("dst")
        if src == dst:
            return None
        after = answer[:m.start()] + f"{dst}向{src}" + answer[m.end():]
        return after, (f"受控流向反转: {src}向{dst} → {dst}向{src}; "
                       "数据流向与evidence声明相反, 期望refute(注入协议)。")

    return _adaptive_pattern_swap(request, op, _FLOW, build)


def _adaptive_quoted_term_swap(request: QAInput,
                               op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    cross_terms = _evidence_cross_terms(request, answer)
    if not cross_terms:
        return []
    attempts: list[MutationAttempt] = []
    for m in _QUOTED.finditer(answer):
        replacement = cross_terms[0]
        if replacement == m.group("term"):
            continue
        after = answer[:m.start("term")] + replacement + answer[m.end("term"):]
        if after == answer:
            continue
        attempts.append(_adaptive(
            request, op, after,
            f"受控引用项替换: 「{m.group('term')}」→「{replacement}」"
            "(evidence其它清单成员); 引用项与evidence显式登记错位, "
            "期望refute(注入协议)。"))
        if len(attempts) >= 2:
            break
    return attempts


def _adaptive_definition_swap(request: QAInput,
                              op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    answer_pair = _DEF_PAIR.search(answer)
    if not answer_pair:
        return []
    ev_glosses: list[str] = []
    for ev in request.evidence:
        ev_glosses.extend(m.group("gloss") for m in _DEF_PAIR.finditer(ev.text))
    replacement = next((g for g in ev_glosses
                        if g != answer_pair.group("gloss")), None)
    if replacement is None:
        return []
    after = (answer[:answer_pair.start("gloss")] + replacement
             + answer[answer_pair.end("gloss"):])
    if after == answer:
        return []
    return [_adaptive(
        request, op, after,
        f"受控释义错配: 「{answer_pair.group('term')}（"
        f"{answer_pair.group('gloss')}）」的括注释义替换为"
        f"「{replacement}」(evidence其它术语释义); 同名异义, "
        "期望refute(注入协议)。")]


def _adaptive_command_action_swap(
        request: QAInput, op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    answer_match = _COMMAND.search(answer)
    if not answer_match:
        return []
    ev_actions: list[str] = []
    for ev in request.evidence:
        ev_actions.extend(m.group("action") or ""
                          for m in _COMMAND.finditer(ev.text))
    current = answer_match.group("action") or answer_match.group("action2") or ""
    replacement = next((a for a in ev_actions if a and a != current), None)
    if replacement is None:
        return []
    group = "action" if answer_match.group("action") else "action2"
    after = (answer[:answer_match.start(group)] + f"（{replacement}）"
             + answer[answer_match.end(group):])
    if after == answer:
        return []
    return [_adaptive(
        request, op, after,
        f"受控指令动作错配: 指令{answer_match.group('name')}的动作"
        f"「{current}」替换为「{replacement}」; 期望refute(注入协议)。")]


def _adaptive_status_term_inject(
        request: QAInput, op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    if not re.search(r"(?:状态|告警|报警)", answer + request.question):
        return []
    ev_compact = _evidence_compact(request)
    ans_compact = _compact(answer)
    term = next((t for t in _STATUS_VOCAB
                 if t not in ev_compact and t not in ans_compact), None)
    if term is None:
        return []
    after = answer.rstrip().rstrip("。") + f"、{term}。"
    if after == answer:
        return []
    return [_adaptive(request, op, after,
                      f"受控状态项注入: 「{term}」加入answer状态声明; "
                      "evidence未登记该状态, 期望refute(注入协议)。")]


def _adaptive_trace_redirect(request: QAInput,
                             op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    m = _TRACE_REF.search(answer)
    if not m:
        return []
    chapters: list[str] = []
    for ev in request.evidence:
        chapters.extend(_CHAPTER_REF.findall(ev.text))
    replacement = next((c for c in chapters if c != m.group("ref")), None)
    if replacement is None:
        replacement = "9.9.9"
    after = answer[:m.start("ref")] + replacement + answer[m.end("ref"):]
    if after == answer:
        return []
    return [_adaptive(
        request, op, after,
        f"受控追溯目标错配: 追溯目标{m.group('ref')}改为{replacement}"
        "(evidence其它章节锚/伪造锚); 与evidence登记的追溯关系冲突, "
        "期望refute(注入协议)。")]


def _adaptive_quantifier_fabrication(
        request: QAInput, op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    if not re.search(r"(?:合格性|判据|量化|需求)", answer + request.question):
        return []
    claim = "500ms以内"
    if claim in answer:
        return []
    after = answer.rstrip().rstrip("。") + f"，量化判据为{claim}。"
    if after == answer:
        return []
    return [_adaptive(request, op, after,
                      f"受控量化编造: answer追加量化判据「{claim}」; "
                      "evidence无该量化约束, 编造判据破坏一致性, "
                      "期望refute(注入协议)。")]


def _adaptive_rollback_fabrication(
        request: QAInput, op: InjectionOperator) -> list[MutationAttempt]:
    answer = request.answer
    if not re.search(r"(?:升级|版本|回滚)", answer + request.question):
        return []
    ev_compact = _evidence_compact(request)
    term = next((t for t in ("升级失败自动回滚", "版本一键回滚", "增量回滚")
                 if t not in ev_compact and t not in _compact(answer)), None)
    if term is None:
        return []
    after = answer.rstrip().rstrip("。") + f"，并支持{term}。"
    if after == answer:
        return []
    return [_adaptive(request, op, after,
                      f"受控能力编造: answer追加升级能力「{term}」; "
                      "evidence未登记该能力, 期望refute(注入协议)。")]


def _make_gjb_inject(strategy: str):
    domain_keywords = _GJB_DOMAIN_KEYWORDS[strategy]

    def run(request: QAInput, op: InjectionOperator) -> list[MutationAttempt]:
        text = request.question + request.answer
        if not any(kw in text for kw in domain_keywords):
            return []
        return _adaptive_enum_inject(request, op,
                                     fabricated=_GJB_VOCAB[strategy])

    return run


_ADAPTIVE_STRATEGIES: dict[
    str, Callable[[QAInput, InjectionOperator], list[MutationAttempt]]] = {
    "numeric_eq_conflict": lambda r, o: _adaptive_numeric(r, o, kind="eq"),
    "numeric_out_of_range": lambda r, o: _adaptive_numeric(r, o, kind="oor"),
    "enum_member_remove": lambda r, o: _adaptive_enum_remove(r, o),
    "actor_member_remove": lambda r, o: _adaptive_enum_remove(
        r, o, actor_gate=True),
    "enum_member_inject": lambda r, o: _adaptive_enum_inject(r, o),
    "step_reorder": _adaptive_step_reorder,
    "step_delete": _adaptive_step_delete,
    "e1_outcome_swap": _adaptive_e1_outcome_swap,
    "identifier_swap": _adaptive_identifier_swap,
    "definition_swap": _adaptive_definition_swap,
    "status_term_inject": _adaptive_status_term_inject,
    "command_action_swap": _adaptive_command_action_swap,
    "priority_reversal": _adaptive_priority_reversal,
    "condition_action_swap": _adaptive_condition_action_swap,
    "event_order_swap": _adaptive_order_swap,
    "atomicity_flip": _adaptive_atomicity_flip,
    "arbitration_swap": _adaptive_arbitration_swap,
    "permission_flip": _adaptive_permission_flip,
    "recovery_flip": _adaptive_recovery_flip,
    "scope_flip": _adaptive_scope_flip,
    "reversed_flow": _adaptive_reversed_flow,
    "quoted_term_swap": _adaptive_quoted_term_swap,
    "trace_redirect": _adaptive_trace_redirect,
    "quantifier_fabrication": _adaptive_quantifier_fabrication,
    "rollback_fabrication": _adaptive_rollback_fabrication,
}
for _name in ("gjb_ft_inject", "gjb_acl_inject", "gjb_audit_inject",
              "gjb_alarm_inject", "gjb_selftest_inject",
              "gjb_powerloss_inject", "gjb_inputguard_inject",
              "gjb_degrade_inject"):
    _ADAPTIVE_STRATEGIES[_name] = _make_gjb_inject(_name)
for _name in ("param_time", "param_period", "param_threshold",
              "param_resource", "param_retention", "param_sync",
              "param_degrade", "param_fault"):
    _ADAPTIVE_STRATEGIES[_name] = (
        lambda r, o, s=_name: _adaptive_numeric(
            r, o, kind="param",
            gate=_PARAM_STRATEGY_KEYWORDS[s],
            units=_PARAM_STRATEGY_UNITS.get(s)))
del _name


def adaptive_attempts(op: InjectionOperator,
                      request: QAInput) -> list[MutationAttempt]:
    strategy = _ADAPTIVE_STRATEGIES.get(op.strategy)
    if strategy is None:
        return []
    return strategy(request, op)[:2]


# ---------------------------------------------------------------- 构建主流程
def build_injections(
        requests: list[QAInput], *,
        max_attempts_per_operator: int = 2,
        max_per_qa_family: int = 6,
        seed: int = SEED,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """冻结QA×算子 → 注入实例 + 统计(守卫/抽样/逐算子适用率)."""
    instances: list[dict[str, Any]] = []
    stats: Counter[str] = Counter()
    op_stats: dict[str, dict[str, int]] = {
        op.operator_id: {"qa_applicable": 0, "strict_proposals": 0,
                         "adaptive_attempts": 0, "injected": 0,
                         "noop_skipped": 0, "support_control": 0,
                         "dedup_skipped": 0} for op in OPERATORS}
    rng = random.Random(seed)
    seq = 0
    for request in requests:
        family_pool: dict[str, list[MutationAttempt]] = defaultdict(list)
        for op in OPERATORS:
            attempts: list[MutationAttempt] = []
            proposals = strict_attempts(op, request)
            if proposals:
                op_stats[op.operator_id]["qa_applicable"] += 1
                op_stats[op.operator_id]["strict_proposals"] += len(proposals)
                attempts.extend(
                    MutationAttempt(operator=op, answer_after=p.answer_after,
                                    mode="library_proof",
                                    gold=p.gold_candidate or "support",
                                    rationale=f"{p.proof_kind}: {p.proof}")
                    for p in proposals[:max_attempts_per_operator])
            if op.refute_semantics and op.strategy:
                adaptive = adaptive_attempts(op, request)
                if adaptive:
                    op_stats[op.operator_id]["qa_applicable"] += 1
                    op_stats[op.operator_id]["adaptive_attempts"] += len(adaptive)
                    attempts.extend(adaptive)
            if not attempts:
                stats["qa_operator_not_applicable"] += 1
                continue
            for attempt in attempts:
                if attempt.answer_after == request.answer:
                    # 变异有效性守卫: 恒等变异跳过并计数
                    op_stats[attempt.operator.operator_id]["noop_skipped"] += 1
                    stats["noop_mutations_skipped"] += 1
                    continue
                if attempt.gold != "refute":
                    # support对照算子(恒等/单位换算/清单补全等)不进注入集
                    op_stats[attempt.operator.operator_id]["support_control"] += 1
                    stats["support_control_not_injected"] += 1
                    continue
                family_pool[op.family].append(attempt)
        # 每QA每算子族抽样(超上限时, seed=42)
        for family in FAMILIES:
            pool = family_pool.get(family, [])
            if not pool:
                continue
            if len(pool) > max_per_qa_family:
                stats["family_sampled_away"] += len(pool) - max_per_qa_family
                pool = rng.sample(pool, max_per_qa_family)
            seen_answers: set[str] = set()
            for attempt in pool:
                if attempt.answer_after in seen_answers:
                    op_stats[attempt.operator.operator_id]["dedup_skipped"] += 1
                    stats["dedup_skipped"] += 1
                    continue
                seen_answers.add(attempt.answer_after)
                seq += 1
                op_stats[attempt.operator.operator_id]["injected"] += 1
                instances.append({
                    "schema": SCHEMA,
                    "instance_id": f"MIJ-{seq:06d}",
                    "source_instance_id": request.instance_id,
                    "operator_name": attempt.operator.operator_id,
                    "operator_family": attempt.operator.family,
                    "check_item": attempt.operator.check_item,
                    "mode": attempt.mode,
                    "question": request.question,
                    "answer": attempt.answer_after,
                    "mutated_answer": attempt.answer_after,
                    "original_answer": request.answer,
                    "expected_verdict": "refute",
                    "mutation_rationale": attempt.rationale,
                    "context_freeze_id": request.context_freeze_id,
                    "evidence": [{
                        "evidence_id": ev.evidence_id,
                        "text": ev.text,
                        "source_type": ev.source_type,
                        "source_ref": ev.source_ref.__dict__,
                        "scope_id": ev.scope_id,
                        "completeness": ev.completeness,
                        "completeness_proof": ev.completeness_proof,
                        "extraction_method": ev.extraction_method,
                        "extraction_confidence": ev.extraction_confidence,
                    } for ev in request.evidence],
                })
    stats["n_instances"] = len(instances)
    return instances, {"stats": dict(stats), "operator_stats": op_stats}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(SOURCE),
                        help="冻结QA JSONL(默认91条scene1)")
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--max-per-family", type=int, default=6,
                        help="每QA每算子族注入上限(超出seed=42抽样)")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    out = Path(args.out).resolve()
    rows = [json.loads(line) for line in
            source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError("source JSONL has no QA rows")
    requests = [request_from_dict(row) for row in rows]
    instances, report = build_injections(
        requests, max_per_qa_family=args.max_per_family, seed=args.seed)
    if not instances:
        raise SystemExit("no injection instances built; check operator applicability")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n"
                for row in instances), encoding="utf-8")
    family_counts = Counter(row["operator_family"] for row in instances)
    mode_counts = Counter(row["mode"] for row in instances)
    operator_counts = Counter(row["operator_name"] for row in instances)
    metadata = {
        "schema": SCHEMA,
        "builder": BUILDER_VERSION,
        "generated_at": round(time.time(), 1),
        "git_sha": current_git_sha(),
        "source": str(source.relative_to(BASE)),
        "source_sha256": sha256_file(source),
        "n_source_qa": len(requests),
        "n_instances": len(instances),
        "expected_verdicts": {"refute": len(instances)},
        "operator_registry": {
            "n_operators": len(OPERATORS),
            "n_refute_semantics": sum(
                1 for op in OPERATORS if op.refute_semantics),
            "n_support_control": sum(
                1 for op in OPERATORS if not op.refute_semantics),
        },
        "families": dict(family_counts),
        "modes": dict(mode_counts),
        "operators": dict(operator_counts),
        "guard_and_sampling": report["stats"],
        "operator_stats": report["operator_stats"],
        "sampling": {"max_per_qa_family": args.max_per_family,
                     "seed": args.seed},
        "protocol": (
            "strict(library_proof)=算子库证明门发出的sound refute; "
            "adaptive=算子语义的answer侧受控扰动, 期望refute来自注入协议"
            "(变异破坏answer对冻结evidence的grounding); 恒等变异守卫与"
            "support对照算子不进注入集, 只计数。"),
        "out": str(out.relative_to(BASE)),
    }
    meta_path = out.with_name(out.stem + "_metadata.json")
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"source QA: {len(requests)}")
    print(f"instances: {len(instances)} ({dict(mode_counts)})")
    print(f"families: {dict(family_counts)}")
    print(f"operators with instances: {len(operator_counts)}")
    print(f"guards: noop_skipped={report['stats'].get('noop_mutations_skipped', 0)}"
          f" support_control={report['stats'].get('support_control_not_injected', 0)}"
          f" dedup={report['stats'].get('dedup_skipped', 0)}"
          f" family_sampled={report['stats'].get('family_sampled_away', 0)}")
    print(f"injection set -> {out}")
    print(f"metadata -> {meta_path}")


if __name__ == "__main__":
    main()
