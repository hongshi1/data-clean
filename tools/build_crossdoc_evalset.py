"""构建06号文档跨文档泛化评测集(P1: 91QA全部来自04号, 泛化能力零验证).

背景
----
scene1_qa_frozen_v1(91QA)的证据与问题全部来自04号文档, 任何配置在其上的
指标都只衡量单文档拟合. 本脚本从06号(运行支撑服务, 476块/350条叙事事实)
提取表格行事实, 构造30条QA(10 S / 10 R / 10 N), 标签为**构造性sound**
(不用LLM silver——跨文档评测要可信, 标签必须构造可证):

  S(support)         answer断言冻结证据中真实存在的表格行事实;
  R(refute)          answer断言同表跨行污染值——污染值真实存在于证据
                     (同表其他行)但绑定到错误主体, 与EGT叙事文法的
                     narrative_*_swap/member_add构造同构;
  N(not_in_evidence) answer断言证据范围外内容: 效果性声明(标记词既不在
                     证据窗口也不在06号全文)或证据窗口外的同文档真实
                     事实(主体行缺席→无绑定信息, 不可判定且无矛盾).

每条的soundness由label_proof背书并由构造期程序化断言:
  S: 事实语句(scope+字段+值)在线性化证据语句中逐字命中;
  R: 真值绑定语句与污染源语句均在线性化证据中(跨行join有真实对象);
  N: 断言标记词/主体行确实缺席于线性化证据(效果性N另要求全文缺席).

证据冻结: seed表格块+邻近内容块(WINDOW_SIZE=4, 与EGT叙事协议一致——
同表完整块入premise→污染源行真实在场, 测跨行join能力); 落盘行格式
与scene1_qa_frozen_v1.jsonl一致(QAInput形状), 另加评测侧字段
sound_label/label_proof/family/operator/check_tokens.

确定性: 全部随机选择走random.Random(固定str种子)与文档序迭代, 重跑
逐字节一致. seed=42.

用法: python tools/build_crossdoc_evalset.py
产出: data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl (30条)
      + crossdoc06_evalset_v1_metadata.json + crossdoc06_evalset_v1_report.json
      + data/gjb_438c/runs/build_crossdoc_evalset_*/ (runs协议)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from algorithms.consistency.evidence_statements import (  # noqa: E402
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.egt_synthesis import (  # noqa: E402
    NarrativeFact,
    _split_members,
    _vnorm,
    collect_statement_seeds,
    evidence_from_dict,
    extract_narrative_corpus,
    narrative_evidence_window,
)
from algorithms.consistency.qa_models import RetrievedEvidence  # noqa: E402
from run_utils import open_run  # noqa: E402

SOURCE_GLOB = "data/gjb_438c/mineru_standard/06*/office/*_content_list.json"
DOC_ID = "06运行支撑服务软件需求规格说明-终稿"
OUT_JSONL = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
OUT_META = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1_metadata.json"
OUT_REPORT = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1_report.json"
SEED = 42
WINDOW_SIZE = 4
N_PER_LABEL = 10
LABELS = ("support", "refute", "not_in_evidence")
INSTANCE_PREFIX = "C06QA"

#: 族/操作配额(与任务口径S/R/N各10条对齐; N=效果性6+窗口外事实4)
QUOTAS: dict[str, list[tuple[str, int]]] = {
    "support": [("capability_device", 3), ("capability_state", 2),
                ("trace_binding", 2), ("interface_flow", 2),
                ("param_value", 1)],
    "refute": [("capability_device", 3), ("capability_state", 2),
               ("trace_binding", 2), ("interface_flow", 2),
               ("param_value", 1)],
    "not_in_evidence": [
        ("capability_device:n_effect", 1), ("capability_state:n_effect", 1),
        ("trace_binding:n_effect", 1), ("interface_flow:n_effect", 1),
        ("usecase_e1:n_effect", 1), ("param_value:n_effect", 1),
        ("capability_device:n_absent", 2), ("capability_state:n_absent", 1),
        ("trace_binding:n_absent", 1),
    ],
}

#: N效果性声明模板(标记词必须不在06号全文中→构造性N)
EFFECT_N_TEMPLATES: dict[str, dict[str, Any]] = {
    "capability_device": {
        "question": "{功能}功能有什么特点？",
        "answer": "{功能}功能经过完整的单元测试验证，"
                  "确保在不同设备形态下提供一致的用户体验。",
        "markers": ("单元测试", "用户体验"),
        "subject_field": "功能",
    },
    "capability_state": {
        "question": "{功能}功能有什么特点？",
        "answer": "{功能}功能在版本升级期间保持可用，保障业务连续运行。",
        "markers": ("版本升级", "业务连续"),
        "subject_field": "功能",
    },
    "trace_binding": {
        "question": "需求{需求ID}目前处于什么状态？",
        "answer": "需求{需求ID}已通过评审确认，其实现完整性经过了验证。",
        "markers": ("评审", "实现完整性"),
        "subject_field": "需求ID",
    },
    "interface_flow": {
        "question": "接口{接口ID}采用什么保障机制？",
        "answer": "接口{接口ID}采用加密传输保障数据安全，并支持高并发批量调用。",
        "markers": ("加密传输", "高并发"),
        "subject_field": "接口ID",
    },
    "param_value": {
        "question": "{参数}的取值是否支持在线调整？",
        "answer": "{参数}的取值支持在线调整，无需重启服务即可生效。",
        "markers": ("在线调整", "重启服务"),
        "subject_field": "参数",
    },
    "usecase_e1": {
        "question": "在{用例}过程中发生异常时系统如何处理？",
        "answer": "在{用例}过程中发生异常时，系统会自动重试该操作，"
                  "并在重试失败时记录告警日志，确保操作最终完成。",
        "markers": ("自动重试", "重试失败"),
        "subject_field": "用例",
    },
}

#: N窗口外事实: 各族主体字段与绑定行字段标签
N_ABSENT_FIELD: dict[str, tuple[str, str]] = {
    "capability_device": ("功能", "方式名称"),
    "capability_state": ("功能", "运行状态"),
    "trace_binding": ("需求ID", "标识符"),
}


# ── 数据模型 ───────────────────────────────────────────────


@dataclass
class Candidate:
    """一条构造完成的QA候选(证据窗口已冻结, 待程序化soundness自检)."""

    sound_label: str
    group: str            # 配额分组键(family 或 family:n_mode)
    family: str
    operator: str
    question: str
    answer: str
    seed_ref: str
    window: tuple[RetrievedEvidence, ...]
    label_proof: str
    in_evidence: tuple[str, ...]      # 必须出现(值级归一化)于线性化证据
    not_in_evidence: tuple[str, ...]  # 必须缺席于线性化证据
    doc_absent: tuple[str, ...] = ()  # 额外要求缺席于全文档(N效果性)


# ── 语句检索工具(对模块真实看到的线性化语句工作) ──────────────


def _window_statements(
        window: Sequence[RetrievedEvidence]) -> list[EvidenceStatement]:
    return list(linearize_context(tuple(window)))


def _window_norm(window: Sequence[RetrievedEvidence]) -> str:
    return _vnorm("；".join(s.text for s in _window_statements(window)))


def _field_statement(
        statements: Sequence[EvidenceStatement], subject: str,
        field_hint: str, value: str) -> str | None:
    """scope=subject(空subject不限)且字段含field_hint且『：』后值等于value的语句."""
    for stmt in statements:
        if field_hint not in stmt.field_name:
            continue
        if subject and stmt.scope_key and _vnorm(stmt.scope_key) != _vnorm(
                subject):
            continue
        head, sep, tail = stmt.text.rpartition("：")
        if sep and _vnorm(tail) == _vnorm(value):
            return stmt.text
        if subject and _vnorm(f"{subject}的{field_hint}：{value}") in _vnorm(
                stmt.text):
            return stmt.text
    return None


def _containing_statement(
        statements: Sequence[EvidenceStatement], needle: str,
        field_hint: str = "") -> str | None:
    """含needle的首条语句(可限定字段), 值级归一化containment."""
    for stmt in statements:
        if field_hint and field_hint not in stmt.field_name:
            continue
        if _vnorm(needle) in _vnorm(stmt.text):
            return stmt.text
    return None


def _scope_of_value(statements: Sequence[EvidenceStatement],
                    field_hint: str, value: str) -> str | None:
    """值(如标识符)所在行的scope键——trace_binding的行名不在fact字段中."""
    for stmt in statements:
        if field_hint not in stmt.field_name:
            continue
        head, sep, tail = stmt.text.rpartition("：")
        if sep and _vnorm(tail) == _vnorm(value):
            return stmt.scope_key
    return None


# ── answer叙述模板(模仿91QA的复述式自然中文) ─────────────────


def _fn(name: str) -> str:
    """主体名+『功能』后缀(名字已以功能结尾时不重复)."""
    return name if name.endswith("功能") else name + "功能"


def _device_answer(name: str, devices: str) -> str:
    members = _split_members(devices)
    tail = (f"用户在{devices}终端上均可以使用该功能。"
            if len(members) > 1 else f"用户在{devices}终端上可以使用该功能。")
    return f"{_fn(name)}支持在{devices}设备上使用。也就是说，{tail}"


def _state_answer(name: str, state: str) -> str:
    return (f"{_fn(name)}在{state}提供。该功能的运行状态绑定为{state}，"
            f"覆盖上述阶段。")


def _trace_answer(ident: str, task: str) -> str:
    return (f"需求{ident}追溯至任务书{task}，"
            f"对应任务书{task}的功能/性能要求。")


def _interface_answer(name: str, ident: str, sender: str,
                      receiver: str) -> str:
    return (f"{name}通过接口{ident}实现，由{sender}发送至{receiver}，"
            f"用于{sender}与{receiver}之间的信息交互。")


def _unit_display(unit: str) -> str:
    if not unit or unit in ("-", "—", "无"):
        return ""
    if unit.startswith("百分比"):
        return "%"
    return unit


def _param_answer(param: str, value: str, unit: str) -> str:
    disp = _unit_display(unit)
    return (f"{param}的最大值为{value}{disp}，"
            f"该数据项的取值不能超过此限值。")


# ── 候选构造: capability_device ─────────────────────────────


def _cap_device_candidates(fact: NarrativeFact, rng: random.Random,
                           blocks: Sequence[dict[str, Any]],
                           ) -> list[Candidate]:
    name = fact.field("功能")
    devices = fact.field("设备列表")
    members = _split_members(devices)
    if not name or not members:
        return []
    window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                       WINDOW_SIZE)
    statements = _window_statements(window)
    own_stmt = _field_statement(statements, name, "方式名称", devices)
    if own_stmt is None:
        return []
    question = f"{_fn(name)}支持在哪些设备上使用？"
    proof_row = f"b{fact.block_idx:03d}#{fact.row_key}"
    out = [Candidate(
        sound_label="support", group="capability_device",
        family="capability_device", operator="s_device_narrative",
        question=question, answer=_device_answer(name, devices),
        seed_ref=fact.seed_id, window=window,
        label_proof=(f"构造性S: {proof_row}行字面『{own_stmt}』"
                     f"在冻结证据中, answer复述该穷举绑定"),
        in_evidence=(own_stmt,), not_in_evidence=())]
    # R: 跨行成员污染——换入同表其他行的设备成员(污染值真实在证据中)
    foreign = sorted({m for sibling in fact.siblings
                      for m in _split_members(sibling)} - set(members))
    foreign = [m for m in foreign
               if not any(m in own or own in m for own in members)]
    if foreign:
        added = rng.choice(foreign)
        source_stmt = _containing_statement(statements, added, "方式名称")
        if source_stmt is not None:
            polluted = "、".join([*members, added])
            out.append(Candidate(
                sound_label="refute", group="capability_device",
                family="capability_device", operator="r_device_member_add",
                question=question, answer=_device_answer(name, polluted),
                seed_ref=fact.seed_id, window=window,
                label_proof=(
                    f"构造性R: 本行{proof_row}『{own_stmt}』为穷举绑定; "
                    f"污染值『{added}』来自同表其他行『{source_stmt}』; "
                    f"answer枚举多出{added} → 跨行绑定冲突"),
                in_evidence=(own_stmt, source_stmt), not_in_evidence=()))
    # R: 穷举缺员(仅/不支持)
    if len(members) >= 2:
        dropped = rng.choice(members)
        kept = "、".join(m for m in members if m != dropped)
        out.append(Candidate(
            sound_label="refute", group="capability_device",
            family="capability_device", operator="r_device_member_drop",
            question=question,
            answer=f"{_fn(name)}仅在{kept}设备上使用，不支持{dropped}设备。",
            seed_ref=fact.seed_id, window=window,
            label_proof=(
                f"构造性R: 本行{proof_row}穷举绑定含『{dropped}』; "
                f"answer断言『不支持{dropped}』→ 与本行绑定矛盾"),
            in_evidence=(own_stmt,), not_in_evidence=()))
    return out


# ── 候选构造: capability_state ─────────────────────────────


def _cap_state_candidates(fact: NarrativeFact, rng: random.Random,
                          blocks: Sequence[dict[str, Any]],
                          ) -> list[Candidate]:
    name = fact.field("功能")
    state = fact.field("状态")
    own = _split_members(state)
    if not name or not own:
        return []
    window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                       WINDOW_SIZE)
    statements = _window_statements(window)
    own_stmt = _field_statement(statements, name, "运行状态", state)
    if own_stmt is None:
        return []
    question = f"{_fn(name)}在哪些运行阶段提供？"
    proof_row = f"b{fact.block_idx:03d}#{fact.row_key}"
    out = [Candidate(
        sound_label="support", group="capability_state",
        family="capability_state", operator="s_state_narrative",
        question=question, answer=_state_answer(name, state),
        seed_ref=fact.seed_id, window=window,
        label_proof=(f"构造性S: {proof_row}行字面『{own_stmt}』"
                     f"在冻结证据中, answer复述该穷举绑定"),
        in_evidence=(own_stmt,), not_in_evidence=())]
    foreign = sorted({p for sibling in fact.siblings
                      for p in _split_members(sibling)} - set(own))
    foreign = [p for p in foreign
               if not any(p in o or o in p for o in own)]
    if foreign:
        target = rng.choice(foreign)
        source_stmt = _containing_statement(statements, target, "运行状态")
        if source_stmt is not None:
            if len(own) == 1:
                polluted, operator = target, "r_state_swap"
            else:
                position = rng.randrange(len(own))
                swapped = list(own)
                swapped[position] = target
                polluted, operator = "、".join(swapped), "r_state_member_swap"
            out.append(Candidate(
                sound_label="refute", group="capability_state",
                family="capability_state", operator=operator,
                question=question, answer=_state_answer(name, polluted),
                seed_ref=fact.seed_id, window=window,
                label_proof=(
                    f"构造性R: 本行{proof_row}『{own_stmt}』为穷举绑定; "
                    f"污染值『{target}』来自同表其他行『{source_stmt}』; "
                    f"answer断言的运行状态与本行绑定冲突"),
                in_evidence=(own_stmt, source_stmt), not_in_evidence=()))
    elif len(own) >= 2:
        dropped = rng.choice(own)
        kept = "、".join(m for m in own if m != dropped)
        out.append(Candidate(
            sound_label="refute", group="capability_state",
            family="capability_state", operator="r_state_member_drop",
            question=question,
            answer=f"{_fn(name)}仅在{kept}提供，不在{dropped}提供。",
            seed_ref=fact.seed_id, window=window,
            label_proof=(
                f"构造性R: 本行{proof_row}穷举绑定含『{dropped}』; "
                f"answer断言『不在{dropped}提供』→ 与本行绑定矛盾"),
            in_evidence=(own_stmt,), not_in_evidence=()))
    return out


# ── 候选构造: trace_binding(需求ID↔任务书) ────────────────────


def _trace_candidates(fact: NarrativeFact, rng: random.Random,
                      blocks: Sequence[dict[str, Any]],
                      ) -> list[Candidate]:
    ident = fact.field("需求ID")
    task = fact.field("任务书ID")
    if not ident or not task:
        return []
    window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                       WINDOW_SIZE)
    statements = _window_statements(window)
    row_name = _scope_of_value(statements, "标识符", ident)
    own_stmt = (_field_statement(statements, row_name, "任务书", task)
                if row_name else None)
    if row_name is None or own_stmt is None:
        return []
    question = f"需求{ident}追溯到任务书的哪一章节？"
    proof_row = f"b{fact.block_idx:03d}#{fact.row_key}"
    out = [Candidate(
        sound_label="support", group="trace_binding",
        family="trace_binding", operator="s_trace_narrative",
        question=question, answer=_trace_answer(ident, task),
        seed_ref=fact.seed_id, window=window,
        label_proof=(f"构造性S: {proof_row}行字面『{own_stmt}』"
                     f"在冻结证据中, answer复述该追溯映射"),
        in_evidence=(own_stmt,), not_in_evidence=())]
    siblings = [t for t in fact.siblings if _vnorm(t) != _vnorm(task)]
    if siblings:
        polluted = rng.choice(siblings)
        source_stmt = _field_statement(statements, "", "任务书", polluted)
        if source_stmt is not None:
            out.append(Candidate(
                sound_label="refute", group="trace_binding",
                family="trace_binding", operator="r_task_swap",
                question=question, answer=_trace_answer(ident, polluted),
                seed_ref=fact.seed_id, window=window,
                label_proof=(
                    f"构造性R: 本行{proof_row}『{own_stmt}』绑定{ident}→"
                    f"{task}; 污染值『{polluted}』来自同表其他行"
                    f"『{source_stmt}』; answer断言{ident}追溯至{polluted}"
                    f" → 跨行映射绑定冲突"),
                in_evidence=(own_stmt, source_stmt), not_in_evidence=()))
    return out


# ── 候选构造: interface_flow(发送方↔接收方) ────────────────────


def _interface_candidates(fact: NarrativeFact, rng: random.Random,
                          blocks: Sequence[dict[str, Any]],
                          ) -> list[Candidate]:
    name = fact.field("接口名")
    ident = fact.field("接口ID")
    sender = fact.field("发送方")
    receiver = fact.field("接收方")
    if not (name and ident and sender and receiver):
        return []
    window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                       WINDOW_SIZE)
    statements = _window_statements(window)
    own_stmt = _field_statement(statements, name, "发送方", sender)
    if own_stmt is None:
        return []
    question = f"{name}的接口流向是什么？"
    proof_row = f"b{fact.block_idx:03d}#{fact.row_key}"
    out = [Candidate(
        sound_label="support", group="interface_flow",
        family="interface_flow", operator="s_interface_narrative",
        question=question,
        answer=_interface_answer(name, ident, sender, receiver),
        seed_ref=fact.seed_id, window=window,
        label_proof=(f"构造性S: {proof_row}行字面『{own_stmt}』"
                     f"在冻结证据中, answer复述该接口流向"),
        in_evidence=(own_stmt,), not_in_evidence=())]
    candidates = [s for s in fact.siblings
                  if _vnorm(s) not in (_vnorm(sender), _vnorm(receiver))
                  and not (s in sender or sender in s)]
    if candidates:
        polluted = rng.choice(candidates)
        source_stmt = (_field_statement(statements, "", "发送方", polluted)
                       or _containing_statement(statements, polluted,
                                                "发送方"))
        if source_stmt is not None:
            out.append(Candidate(
                sound_label="refute", group="interface_flow",
                family="interface_flow", operator="r_sender_swap",
                question=question,
                answer=_interface_answer(name, ident, polluted, receiver),
                seed_ref=fact.seed_id, window=window,
                label_proof=(
                    f"构造性R: 本行{proof_row}『{own_stmt}』绑定{ident}的"
                    f"发送方为{sender}; 污染值『{polluted}』来自同表其他行"
                    f"『{source_stmt}』; answer断言{ident}由{polluted}发送"
                    f" → 跨行绑定冲突"),
                in_evidence=(own_stmt, source_stmt), not_in_evidence=()))
    return out


# ── 候选构造: param_value(数据项最大值) ─────────────────────


def _param_candidates(fact: NarrativeFact, rng: random.Random,
                      blocks: Sequence[dict[str, Any]],
                      ) -> list[Candidate]:
    param = fact.field("参数")
    value = fact.field("值")
    unit = fact.field("单位")
    if not param or not value:
        return []
    window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                       WINDOW_SIZE)
    statements = _window_statements(window)
    own_stmt = _field_statement(statements, param, "最大值", value)
    if own_stmt is None:
        return []
    question = f"{param}的最大值是多少？"
    proof_row = f"b{fact.block_idx:03d}#{fact.row_key}"
    out = [Candidate(
        sound_label="support", group="param_value",
        family="param_value", operator="s_param_narrative",
        question=question, answer=_param_answer(param, value, unit),
        seed_ref=fact.seed_id, window=window,
        label_proof=(f"构造性S: {proof_row}行字面『{own_stmt}』"
                     f"在冻结证据中, answer复述该数据项约束"),
        in_evidence=(own_stmt,), not_in_evidence=())]
    siblings = [v for v in fact.siblings if _vnorm(v) != _vnorm(value)]
    if siblings:
        polluted = rng.choice(siblings)
        source_stmt = _field_statement(statements, "", "最大值", polluted)
        if source_stmt is not None:
            out.append(Candidate(
                sound_label="refute", group="param_value",
                family="param_value", operator="r_value_swap",
                question=question, answer=_param_answer(param, polluted,
                                                        unit),
                seed_ref=fact.seed_id, window=window,
                label_proof=(
                    f"构造性R: 本行{proof_row}『{own_stmt}』绑定{param}的"
                    f"最大值为{value}; 污染值『{polluted}』来自同表其他行"
                    f"『{source_stmt}』; answer断言{param}最大值为{polluted}"
                    f" → 值唯一性绑定冲突"),
                in_evidence=(own_stmt, source_stmt), not_in_evidence=()))
    return out


# ── 候选构造: N(效果性声明 / 窗口外真实事实) ──────────────────


def _n_effect_candidates(fact: NarrativeFact,
                         blocks: Sequence[dict[str, Any]],
                         ) -> list[Candidate]:
    template = EFFECT_N_TEMPLATES.get(fact.family)
    if template is None:
        return []
    subject = fact.field(str(template["subject_field"]))
    if not subject:
        return []
    window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                       WINDOW_SIZE)
    statements = _window_statements(window)
    subject_stmt = _containing_statement(statements, subject)
    if subject_stmt is None:
        return []
    fields = {key: value for key, value in fact.fields}
    question = str(template["question"]).format(**fields)
    answer = str(template["answer"]).format(**fields)
    markers = tuple(str(m) for m in template["markers"])
    return [Candidate(
        sound_label="not_in_evidence", group=f"{fact.family}:n_effect",
        family=fact.family, operator="n_effect_claim",
        question=question, answer=answer, seed_ref=fact.seed_id,
        window=window,
        label_proof=(
            f"构造性N: 效果性断言标记词{'/'.join(markers)}既不在证据窗口"
            f"中也不在06号全文档中; 主体『{subject}』在场『{subject_stmt}』"
            f"但断言内容无证据且无矛盾"),
        in_evidence=(subject_stmt,), not_in_evidence=markers,
        doc_absent=markers)]


def _n_absent_candidates(fact: NarrativeFact,
                         blocks: Sequence[dict[str, Any]],
                         table_blocks: Sequence[int],
                         ) -> list[Candidate]:
    """N窗口外事实: 复用S问句/answer, 证据换成主体缺席的其他表窗口."""
    spec = N_ABSENT_FIELD.get(fact.family)
    if spec is None:
        return []
    subject_field, field_hint = spec
    subject = fact.field(subject_field)
    if not subject:
        return []
    if fact.family == "capability_device":
        question = f"{_fn(subject)}支持在哪些设备上使用？"
        answer = _device_answer(subject, fact.field("设备列表"))
        own_field = "方式名称"
    elif fact.family == "capability_state":
        question = f"{_fn(subject)}在哪些运行阶段提供？"
        answer = _state_answer(subject, fact.field("状态"))
        own_field = "运行状态"
    else:
        ident = fact.field("需求ID")
        task = fact.field("任务书ID")
        question = f"需求{ident}追溯到任务书的哪一章节？"
        answer = _trace_answer(ident, task)
        own_field = "标识符"
    own_window = narrative_evidence_window(DOC_ID, fact.block_idx, blocks,
                                           WINDOW_SIZE)
    own_stmt = (_field_statement(_window_statements(own_window), subject,
                                 own_field, fact.field(subject_field))
                if own_field != "标识符" else
                _containing_statement(_window_statements(own_window),
                                      subject, "标识符"))
    out: list[Candidate] = []
    for other in table_blocks:
        if other == fact.block_idx:
            continue
        window = narrative_evidence_window(DOC_ID, other, blocks,
                                           WINDOW_SIZE)
        env = _window_norm(window)
        if not env or _vnorm(subject) in env:
            continue
        binding = f"{subject}的{field_hint}"
        if _vnorm(binding) in env:
            continue
        window_ids = ", ".join(ev.source_ref.block_id for ev in window)
        out.append(Candidate(
            sound_label="not_in_evidence", group=f"{fact.family}:n_absent",
            family=fact.family, operator="n_value_absent",
            question=question, answer=answer, seed_ref=fact.seed_id,
            window=window,
            label_proof=(
                f"构造性N: {subject}的绑定行(b{fact.block_idx:03d}#"
                f"{fact.row_key}『{own_stmt or own_field}』)不在证据窗口"
                f"({window_ids})中, 窗口内无{subject}的任何行"
                f" → 证据无法判定且无矛盾"),
            in_evidence=(), not_in_evidence=(subject, binding)))
        if len(out) >= 2:
            break
    return out


# ── soundness自检与确定性选择 ──────────────────────────────


def verify_candidate(cand: Candidate, doc_norm: str) -> bool:
    """构造期程序化断言: 标签的sound性由token级验证背书."""
    env = _window_norm(cand.window)
    if not env:
        return False
    if cand.in_evidence and any(_vnorm(tok) not in env
                                for tok in cand.in_evidence):
        return False
    if cand.not_in_evidence and any(_vnorm(tok) in env
                                    for tok in cand.not_in_evidence):
        return False
    if cand.doc_absent and any(_vnorm(tok) in doc_norm
                               for tok in cand.doc_absent):
        return False
    return True


def _interleave_by_operator(pool: list[Candidate],
                            rng: random.Random) -> list[Candidate]:
    """组内按算子轮转交错(各族R/S含多个算子时保证算子多样性)."""
    by_operator: dict[str, list[Candidate]] = {}
    for cand in pool:
        by_operator.setdefault(cand.operator, []).append(cand)
    for group_pool in by_operator.values():
        rng.shuffle(group_pool)
    merged: list[Candidate] = []
    deepest = max(len(p) for p in by_operator.values())
    for cursor in range(deepest):
        for operator in sorted(by_operator):
            if cursor < len(by_operator[operator]):
                merged.append(by_operator[operator][cursor])
    return merged


def select_candidates(
        candidates: Sequence[Candidate],
        doc_norm: str) -> tuple[list[Candidate], dict[str, Any]]:
    """按配额确定性选取: 组内算子轮转+random.Random(固定str种子)."""
    verified: dict[str, list[Candidate]] = {}
    rejected: Counter = Counter()
    for cand in candidates:
        if verify_candidate(cand, doc_norm):
            verified.setdefault(f"{cand.sound_label}|{cand.group}",
                                []).append(cand)
        else:
            rejected[f"{cand.sound_label}|{cand.group}|{cand.operator}"] += 1
    selected: list[Candidate] = []
    seen_answers: set[tuple[str, str]] = set()
    shortfall: dict[str, int] = {}
    for label in QUOTAS:
        for group, quota in QUOTAS[label]:
            key = f"{label}|{group}"
            rng = random.Random(f"{SEED}|{key}")
            pool = _interleave_by_operator(list(verified.get(key, [])), rng)
            taken = 0
            for cand in pool:
                if taken >= quota:
                    break
                fingerprint = (cand.question, _vnorm(cand.answer))
                if fingerprint in seen_answers:
                    continue
                seen_answers.add(fingerprint)
                selected.append(cand)
                taken += 1
            if taken < quota:
                shortfall[key] = quota - taken
    return selected, {
        "n_verified_candidates": sum(len(v) for v in verified.values()),
        "n_selected": len(selected),
        "rejected_by_self_check": dict(rejected),
        "shortfall": shortfall,
    }


# ── 装配与序列化(格式与scene1_qa_frozen_v1.jsonl一致) ──────────


def _to_frozen_evidence(instance_id: str, ev: RetrievedEvidence,
                        section: str) -> dict[str, Any]:
    block_idx = int(ev.source_ref.block_id[1:])
    block_id = f"block-{block_idx:06d}"
    return {
        "evidence_id": f"{instance_id}-ev-{block_idx:06d}",
        "text": ev.text,
        "source_type": ev.source_type,
        "source_ref": {
            "doc_id": ev.source_ref.doc_id,
            "section": section,
            "page": ev.source_ref.page,
            "block_id": block_id,
        },
        "scope_id": f"{ev.source_ref.doc_id}:{block_id}",
        "completeness": "open",
        "completeness_proof": ("Only this source block was frozen; no claim "
                               "that the block or hit set is exhaustive."),
        "extraction_method": "crossdoc06_content_list_freeze",
        "extraction_confidence": 1.0,
    }


def _block_sections(blocks: Sequence[dict[str, Any]]) -> dict[int, str]:
    """块→当前章节标题(最近的'N.N.N 标题'文本块), 与04冻结集的section对齐."""
    sections: dict[int, str] = {}
    current = ""
    heading = re.compile(r"^([1-5](?:\.\d+){0,3})\s+\S")
    for index, block in enumerate(blocks):
        if str(block.get("type", "")) == "text":
            text = str(block.get("text", "")).strip()
            if len(text) < 80 and heading.match(text):
                current = text
        sections[index] = current
    return sections


def assemble_rows(selected: Sequence[Candidate], sections: dict[int, str],
                  ) -> tuple[list[dict[str, Any]], str]:
    label_order = {label: i for i, label in enumerate(LABELS)}
    ranked = sorted(selected, key=lambda c: (
        label_order[c.sound_label], c.group, c.seed_ref))
    rows: list[dict[str, Any]] = []
    for number, cand in enumerate(ranked, 1):
        instance_id = f"{INSTANCE_PREFIX}-{number:03d}"
        evidence = [
            _to_frozen_evidence(
                instance_id, ev,
                sections.get(int(ev.source_ref.block_id[1:]), ""))
            for ev in cand.window]
        rows.append({
            "instance_id": instance_id,
            "question": cand.question,
            "answer": cand.answer,
            "context_freeze_id": "",
            "evidence": evidence,
            "sound_label": cand.sound_label,
            "label_proof": cand.label_proof,
            "family": cand.family,
            "operator": cand.operator,
            "check_tokens": {
                "in_evidence": list(cand.in_evidence),
                "not_in_evidence": list(cand.not_in_evidence),
            },
        })
    canon = json.dumps(
        [{k: v for k, v in row.items() if k != "context_freeze_id"}
         for row in rows], ensure_ascii=False, sort_keys=True)
    freeze = ("crossdoc06-frozen-v1-"
              + hashlib.sha1(canon.encode("utf-8")).hexdigest()[:16])
    for row in rows:
        row["context_freeze_id"] = freeze
    return rows, freeze


def verify_evalset_file(path: Path) -> dict[str, Any]:
    """落盘后从JSONL独立复核: R污染值在证据中/N内容不在证据中/S值在证据中."""
    problems: list[str] = []
    labels: Counter = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        labels[str(row.get("sound_label", ""))] += 1
        statements = linearize_context(tuple(
            evidence_from_dict(ev) for ev in row["evidence"]))
        env = _vnorm("；".join(s.text for s in statements))
        tokens = row.get("check_tokens", {})
        for tok in tokens.get("in_evidence", []):
            if _vnorm(str(tok)) not in env:
                problems.append(f"{row['instance_id']}: in_evidence缺失 {tok}")
        for tok in tokens.get("not_in_evidence", []):
            if _vnorm(str(tok)) in env:
                problems.append(
                    f"{row['instance_id']}: not_in_evidence在场 {tok}")
    return {
        "labels": dict(labels),
        "total": sum(labels.values()),
        "problems": problems,
        "all_checks_pass": not problems,
    }


# ── 主流程 ─────────────────────────────────────────────────


def load_source_blocks() -> Path:
    matches = sorted(glob.glob(str(BASE / SOURCE_GLOB)))
    if len(matches) != 1:
        raise FileNotFoundError(
            f"期望唯一匹配{SOURCE_GLOB}, 实得{len(matches)}: {matches}")
    return Path(matches[0])


def build_evalset(
        source: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    blocks = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(blocks, list):
        raise ValueError(f"content_list应为块列表: {source}")
    facts, pools = extract_narrative_corpus(blocks, DOC_ID)
    doc_norm = pools.doc_text
    sections = _block_sections(blocks)
    seeds = collect_statement_seeds(blocks, DOC_ID)

    candidates: list[Candidate] = []
    family_blocks: dict[str, set[int]] = {}
    for fact in facts:
        rng = random.Random(f"{SEED}|{fact.seed_id}")
        if fact.family == "capability_device":
            candidates += _cap_device_candidates(fact, rng, blocks)
        elif fact.family == "capability_state":
            candidates += _cap_state_candidates(fact, rng, blocks)
        elif fact.family == "trace_binding":
            candidates += _trace_candidates(fact, rng, blocks)
        elif fact.family == "interface_flow":
            candidates += _interface_candidates(fact, rng, blocks)
        elif fact.family == "param_value":
            candidates += _param_candidates(fact, rng, blocks)
        candidates += _n_effect_candidates(fact, blocks)
        if fact.family in N_ABSENT_FIELD:
            family_blocks.setdefault(fact.family, set()).add(fact.block_idx)
            candidates += _n_absent_candidates(
                fact, blocks, sorted(family_blocks[fact.family]))
    selected, select_stats = select_candidates(candidates, doc_norm)
    rows, freeze = assemble_rows(selected, sections)

    stats = {
        "source_srs": str(source.relative_to(BASE)),
        "doc_id": DOC_ID,
        "blocks": {"total": len(blocks),
                   "by_type": dict(Counter(
                       str(b.get("type", "")) for b in blocks))},
        "statement_seeds": len(seeds),
        "narrative_facts": dict(Counter(f.family for f in facts)),
        "narrative_fact_total": len(facts),
        "n_candidates": len(candidates),
        "selection": select_stats,
        "label_distribution": dict(Counter(r["sound_label"] for r in rows)),
        "by_group": dict(Counter(
            f"{r['sound_label']}|{r['family']}"
            + ("|n_absent" if r["operator"] == "n_value_absent" else "")
            for r in rows)),
        "context_freeze_id": freeze,
        "seed": SEED,
        "window_size": WINDOW_SIZE,
        "label_policy": ("constructive sound (label_proof + programmatic "
                         "token checks; no LLM in label generation)"),
        "total": len(rows),
    }
    return rows, stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None,
                        help="覆盖06号content_list路径")
    args = parser.parse_args()
    source = args.source or load_source_blocks()

    rows, stats = build_evalset(source)
    counts = Counter(r["sound_label"] for r in rows)
    if len(rows) != 3 * N_PER_LABEL or any(
            counts[label] != N_PER_LABEL for label in LABELS):
        raise RuntimeError(
            f"评测集应各{N_PER_LABEL}条, 实得{dict(counts)}; "
            f"配额缺口: {stats['selection']['shortfall']}")

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    verification = verify_evalset_file(OUT_JSONL)
    if not verification["all_checks_pass"]:
        raise RuntimeError(f"落盘复核失败: {verification['problems'][:5]}")

    metadata = dict(stats)
    metadata["output"] = str(OUT_JSONL.relative_to(BASE))
    metadata["post_write_verification"] = verification
    OUT_META.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=1), encoding="utf-8")
    report = {
        "version": "crossdoc06_evalset_v1",
        "checks": {
            "row_count_30": verification["total"] == 30,
            "labels_10_10_10": all(verification["labels"].get(label, 0) == 10
                                   for label in LABELS),
            "token_checks_pass": verification["all_checks_pass"],
        },
        "counts": {"rows": verification["total"],
                   "labels": verification["labels"]},
        "selection": stats["selection"],
        "context_freeze_id": stats["context_freeze_id"],
    }
    OUT_REPORT.write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    run = open_run("build_crossdoc_evalset", {
        "source": stats["source_srs"],
        "output": metadata["output"],
        "seed": SEED,
        "window_size": WINDOW_SIZE,
        "quotas": QUOTAS,
        "label_policy": stats["label_policy"],
    })
    run.save_result(stats)
    run.log(event="evalset_built", total=len(rows), labels=dict(counts))

    print(f"06号块数: {stats['blocks']['total']} "
          f"({stats['blocks']['by_type']})")
    print(f"叙事事实: {stats['narrative_fact_total']} "
          f"{stats['narrative_facts']}")
    print(f"语句种子: {stats['statement_seeds']}")
    print(f"30条分布: {dict(counts)}")
    print(f"分组分布: {stats['by_group']}")
    print(f"context_freeze_id: {stats['context_freeze_id']}")
    print(f"落盘: {OUT_JSONL}")
    print(f"     + {OUT_META.name} / {OUT_REPORT.name}")
    print(f"runs: {run.path}")


if __name__ == "__main__":
    main()
