"""E5 Step 2: 最小变更对增广 (表驱动, 零API — docs/srs_project/100号规格 Step 2).

对gated数据中faithful≥2的refute条目构造**修复版answer**: 把violation
按证据修正(数值→证据合法值 / 枚举→证据成员 / ID与绑定→证据绑定),
判定应翻转为support. 每对 = (original_answer, fixed_answer) 的最小变更
对照, 训练解释的"差异指认"能力.

修复算子(确定性, 表驱动, 不确定的不硬造):
  chapter_number  GJB-05      answer中错误章节号 → 证据行『任务书』列章节
  numeric_value   PARAM-*     违规数值 → 证据行『最大值/最小值』列值
  enum_member     TERM-03     枚举集合 → 证据行『方式名称/运行状态』列成员
                              (成员段替换 + 否定中和 + 多余成员条目删除)
  id_binding      TERM-07/08  错误标识符 → 证据行绑定的标识符
  party_binding   LOGIC-04    错误交互方/方向 → 证据接口表发送方/接收方
  term_unify      TERM-01     同义异名 → 证据用词(仅issue的span内)
  operator_flip   PARAM-06    操作符词 → 证据操作符(复用OP_FLIP表)

算子模式复用 algorithms/qa_mutation_ops.py (import复用, 反向使用: 修复
而非破坏): 数值检测用Param*Conflict四个模式(组2=数值/组3=单位), 单位
等价用TermUnitMismatch.UNIT_EQ, 同义词表用TermSynonymSwap.SYNONYMS,
操作符翻转表用ParamValueRangeConflict.OP_FLIP. import方向 tools→algorithms
为仓库允许方向(algorithms不得反向import tools; qa_mutation_ops无tools依赖).

行级规则: 一条refute行的**所有**issue都被安全修复, 且通过终检
(残余ID/章节号须在证据中, 接口流向声称的交互方须在证据双方集合内,
 固定answer长度在安全带内)才产出pair(expected_flip: refute→support);
任一环节不可修复→整行跳过并计数(不硬造).

产物: data/gjb_438c/distillation/e5_minimal_pairs_v1.jsonl
      + runs/e5_minimal_pairs_*/result.json (类型分布/跳过原因/数字)

用法: $env:PYTHONUTF8='1'; python tools/e5_minimal_pairs.py
      [--labels data/gjb_438c/distillation/d3_train_v3f_gated.jsonl]
      [--extra-gate <runs/e5_explanation_gate_*/gate_scores_union.jsonl>]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE), str(BASE / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# 复用qa_mutation_ops的算子模式(反向使用: 修复而非破坏).
# 四个Param模式的捕获组约定: 组1=限定词, 组2=数值, 组3=单位.
from algorithms.qa_mutation_ops import (  # noqa: E402
    ParamPeriodConflict,
    ParamResourceConflict,
    ParamStorageConflict,
    ParamTimeConflict,
    ParamValueRangeConflict,
    TermSynonymSwap,
    TermUnitMismatch,
)
from run_utils import open_run  # noqa: E402

LABELS_DEFAULT = BASE / "data/gjb_438c/distillation/d3_train_v3f_gated.jsonl"
OUT_PAIRS = BASE / "data/gjb_438c/distillation/e5_minimal_pairs_v1.jsonl"

#: 设备形态成员词(『方式名称』列的枚举词表)
DEVICE_MEMBERS = ("桌面", "平板", "手持", "大屏", "一体机")
#: 运行阶段/状态成员词(『运行状态』列: 限定前缀+阶段)
STAGE_MEMBER_RE = re.compile(
    r"(?:开发|集成|运行|测试|部署|设计|联调|验收|维护|试运行)阶段")
#: 章节号(含重复字母后缀"4.2a)b)"与复合"4.1.1 a) /4.2 a)b)")
#: 后缀字母后不得紧跟小写字母(防误吃"beta"式单词)
CHAPTER_RE = re.compile(
    r"\d+(?:\.\d+)+(?:\s*[a-e](?![a-z])[）)]?)*"
    r"(?:\s*/\s*\d+(?:\.\d+)+(?:\s*[a-e](?![a-z])[）)]?)*)*")
#: 项目/接口标识符
ID_RE = re.compile(r"[A-Z]{2,}(?:-[A-Z0-9]+){2,}")
#: 通用数值+单位(qa_mutation_ops四模式之外的单位, 如字节/字符)
NUM_GENERIC_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(字节|字符|字|位|byte|Byte|GB|MB|KB|TB|bit|bps|ms|s|"
    r"秒|分钟|min|h|小时|Hz|kHz|MHz|%|条|个|路|万|亿|天|日|月|年|页|帧|km|米)")
#: 裸数值(值为X式, 无单位 — 四个Param模式要求带单位, 此为补充)
NUM_BARE_RE = re.compile(
    r"(?:值|为|是|等于|超过|大于|小于|不超过|不大于|不少于|至少|最多)"
    r"\s*(\d+(?:\.\d+)?)(?![\d.])")
#: 数值边界(防误替换相邻数字)
_NUM_BOUND_L = r"(?<![\d.])"
_NUM_BOUND_R = r"(?![\d.])"
#: 固定answer长度安全带(防正则失控)
_LEN_BAND = (0.3, 2.0)
#: 全局替换party token的最小长度(过短的party只做span内替换)
_PARTY_GLOBAL_MIN = 4

_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_HEADER_HINTS = ("序号", "名称", "标识", "最大值", "最小值", "单位",
                 "发送方", "接收方", "任务书", "方式", "状态")
#: 接口表中的非交互方单元格值(过滤用)
_NON_PARTY_RE = re.compile(r"^(高|中|低)$|接口$|^(API|人机接口|数据接口)$|^\d+$")

_QUESTION_SPECS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(?:需求)?(?P<subj>[A-Z0-9][A-Z0-9-]{5,})追溯到任务书"),
     "chapter"),
    (re.compile(r"^(?P<subj>.{1,24}?)(?:功能)?的(?P<field>最大值|最小值)是多少"),
     "numeric"),
    (re.compile(r"^(?P<subj>.{2,30}?)(?:功能)?的接口流向是什么"), "interface"),
    (re.compile(r"^(?P<subj>.{2,24}?)(?:功能)?(?:支持)?在哪些运行阶段提供"),
     "stage"),
    (re.compile(r"^(?P<subj>.{2,24}?)(?:功能)?支持在哪些设备上使用"), "device"),
    (re.compile(r"^(?P<subj>.{2,24}?)用例的名称是什么"), "usecase_name"),
    (re.compile(r"^(?P<subj>.{2,24}?)用例的"
                r"(?:项目唯一标识符|标识符|标识|ID|编号)是什么"), "usecase_id"),
]


@dataclass
class RepairOutcome:
    ok: bool
    reason: str = ""
    operator: str = ""
    records: list[dict] = field(default_factory=list)


# ── 证据表解析 ───────────────────────────────────────────────

def _cell_text(cell_html: str) -> str:
    """单元格文本: 相邻<p>直接拼接(被拆开的值如ID), 其余标签剥离."""
    text = re.sub(r"</p>\s*<p[^>]*>", "", cell_html)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", "", text)


def parse_table(evidence_html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_match in _ROW_RE.finditer(evidence_html):
        cells = [_cell_text(c) for c in _CELL_RE.findall(row_match.group(1))]
        if cells:
            rows.append(cells)
    return rows


def _is_header_row(cells: list[str]) -> bool:
    return sum(1 for c in cells if any(h in c for h in _HEADER_HINTS)) >= 2


def find_column(rows: list[list[str]], keywords: tuple[str, ...]) -> int | None:
    for cells in rows[:2]:
        if not _is_header_row(cells):
            continue
        for idx, cell in enumerate(cells):
            if any(k in cell for k in keywords):
                return idx
    return None


def _header_len(rows: list[list[str]]) -> int:
    for cells in rows[:2]:
        if _is_header_row(cells):
            return len(cells)
    return 0


def find_subject_row(rows: list[list[str]], subject: str,
                     subject_alt: str = "") -> int | None:
    """含subject的数据行: 精确单元格命中优先(防单字主词误配),
    其次行文本包含; 表头行除外; 多行命中取格子最多且最先者.

    注意: 不做按[与和]拆词的模糊回退——问题主词不在证据行内时宁可
    返回None(跳过), 不绑定到只共享一个交互方的错误行(FLamE式陷阱).
    """
    def _pick(hits: list[tuple[int, int]]) -> int | None:
        if not hits:
            return None
        hits.sort(key=lambda t: (-t[1], t[0]))
        return hits[0][0]

    exact: list[tuple[int, int]] = []
    contains: list[tuple[int, int]] = []
    for r_idx, cells in enumerate(rows):
        if _is_header_row(cells):
            continue
        if subject in cells or (subject_alt and subject_alt in cells):
            exact.append((r_idx, len(cells)))
        elif subject in "".join(cells) or \
                (subject_alt and subject_alt in "".join(cells)):
            contains.append((r_idx, len(cells)))
    return _pick(exact) or _pick(contains)


def match_question(question: str) -> tuple[str, str, dict[str, str]] | None:
    for pattern, kind in _QUESTION_SPECS:
        m = pattern.match(question.strip())
        if m:
            return kind, m.group("subj"), m.groupdict()
    return None


def _evidence_index(issue: dict, row: dict) -> int | None:
    m = re.search(r"ev-(\d+)", str(issue.get("evidence_ref", "")))
    if not m:
        return None
    idx = int(m.group(1)) - 1
    evidence = row.get("evidence") or []
    if not (0 <= idx < len(evidence)):
        return None
    return idx


def _row_text(rows: list[list[str]], r_idx: int | None) -> str:
    """行文本: 单元格以"|"连接(防跨单元格token粘连, 如ID+相邻"API")."""
    if r_idx is None or r_idx >= len(rows):
        return ""
    return "|".join(rows[r_idx])


def _cell_by_keywords(rows: list[list[str]], r_idx: int | None,
                      keywords: tuple[str, ...]) -> str:
    if r_idx is None or r_idx >= len(rows):
        return ""
    col = find_column(rows, keywords)
    if col is not None and col < len(rows[r_idx]):
        return rows[r_idx][col]
    return ""


# ── 成员词表工具(枚举族) ─────────────────────────────────────

def _member_spans(text: str) -> list[tuple[int, int, str]]:
    """成员token位置表: 设备词 + 限定前缀的『xx阶段』."""
    spans: list[tuple[int, int, str]] = []
    for m in re.finditer("|".join(DEVICE_MEMBERS), text):
        spans.append((m.start(), m.end(), m.group()))
    for m in STAGE_MEMBER_RE.finditer(text):
        spans.append((m.start(), m.end(), m.group()))
    spans.sort()
    return spans


def member_tokens(text: str) -> list[str]:
    return [t for _, _, t in _member_spans(text)]


def _split_members(cell: str) -> list[str]:
    seen: list[str] = []
    for token in member_tokens(cell):
        if token not in seen:
            seen.append(token)
    return seen


def member_runs(text: str) -> list[tuple[int, int, list[str]]]:
    """[、和，]连接的成员连续段(≥2个成员才算段)."""
    spans = _member_spans(text)
    runs: list[tuple[int, int, list[str]]] = []
    cur: list[tuple[int, int, str]] = []
    for span in spans:
        if cur and re.fullmatch(r"\s*[、和，]\s*", text[cur[-1][1]:span[0]]):
            cur.append(span)
        else:
            if len(cur) >= 2:
                runs.append((cur[0][0], cur[-1][1], [t for _, _, t in cur]))
            cur = [span]
    if len(cur) >= 2:
        runs.append((cur[0][0], cur[-1][1], [t for _, _, t in cur]))
    return runs


# ── 数值token工具(复用qa_mutation_ops的四个Param模式) ─────────

_PARAM_PATTERNS = (ParamTimeConflict.TIME_PAT, ParamPeriodConflict.PERIOD_PAT,
                   ParamResourceConflict.RES_PAT, ParamStorageConflict.STORE_PAT)


def numeric_tokens(text: str) -> list[tuple[str, str]]:
    """text中(数值, 单位)token: 四个Param模式(组2数值/组3单位) + 通用/裸值.

    顺序即优先级: 带单位/带限定词的模式在前(单位非空), 裸值在后(单位空).
    """
    out: list[tuple[str, str]] = []
    for pat in _PARAM_PATTERNS:
        for m in pat.finditer(text):
            out.append((m.group(2), m.group(3)))
    for m in NUM_GENERIC_RE.finditer(text):
        out.append((m.group(1), m.group(2)))
    for m in NUM_BARE_RE.finditer(text):
        out.append((m.group(1), ""))
    return out


def _units_compatible(unit_a: str, unit_b: str) -> bool:
    if not unit_a or not unit_b or unit_a == unit_b:
        return True
    for u1, u2 in TermUnitMismatch.UNIT_EQ:
        if {unit_a, unit_b} == {u1, u2}:
            return True
    return False


def _replace_number(answer: str, old_value: str, new_value: str) -> str:
    return re.sub(_NUM_BOUND_L + re.escape(old_value) + _NUM_BOUND_R,
                  new_value.replace("\\", "\\\\"), answer)


def _number_present(answer: str, value: str) -> bool:
    return re.search(_NUM_BOUND_L + re.escape(value) + _NUM_BOUND_R,
                     answer) is not None


# ── 修复算子(签名统一: row, issue, answer → (fixed, outcome)) ──

def repair_chapter_number(row: dict, issue: dict,
                          answer: str) -> tuple[str, RepairOutcome]:
    """GJB-05: answer中错误章节号 → 证据行『任务书』列章节(token级替换)."""
    spec = match_question(str(row.get("question", "")))
    if spec is None or spec[0] != "chapter":
        return answer, RepairOutcome(False, "no_chapter_subject")
    subject = spec[1]
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    rows = parse_table(str(row["evidence"][ev_idx]))
    r_idx = find_subject_row(rows, subject)
    quote = str(issue.get("quote", ""))
    x_list = sorted({m.group() for m in CHAPTER_RE.finditer(quote)})
    if len(x_list) != 1:
        return answer, RepairOutcome(False, "chapter_ambiguous_or_absent")
    old = x_list[0]
    cell = _cell_by_keywords(rows, r_idx, ("任务书",))
    if cell and CHAPTER_RE.search(cell):
        if old in {m.group() for m in CHAPTER_RE.finditer(cell)}:
            return answer, RepairOutcome(False, "no_value_difference")
        new = re.sub(r"\s+", "", cell)     # 多值绑定整体替换("4.1.1；4.2")
    else:
        row_source = _row_text(rows, r_idx)
        y_list = [m.group() for m in CHAPTER_RE.finditer(row_source)
                  if m.group() != old]
        if len(y_list) != 1:
            return answer, RepairOutcome(False, "evidence_chapter_ambiguous")
        new = y_list[0]
    if new == old:
        return answer, RepairOutcome(False, "no_value_difference")
    fixed = answer
    for m in reversed(list(CHAPTER_RE.finditer(answer))):
        if m.group() == old:
            fixed = fixed[:m.start()] + new + fixed[m.end():]
    if old in {m.group() for m in CHAPTER_RE.finditer(fixed)}:
        return answer, RepairOutcome(False, "chapter_replace_incomplete")
    if new not in fixed:
        return answer, RepairOutcome(False, "chapter_replace_incomplete")
    return fixed, RepairOutcome(True, operator="chapter_number", records=[{
        "old": old, "new": new, "note": "任务书章节号对齐证据行"}])


def repair_numeric_value(row: dict, issue: dict,
                         answer: str) -> tuple[str, RepairOutcome]:
    """PARAM-*: 违规数值 → 证据行『最大值/最小值』列的值(单位须兼容)."""
    spec = match_question(str(row.get("question", "")))
    if spec is None or spec[0] != "numeric":
        return answer, RepairOutcome(False, "no_numeric_subject")
    subject, groups = spec[1], spec[2]
    field = groups.get("field", "最大值")
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    rows = parse_table(str(row["evidence"][ev_idx]))
    quote = str(issue.get("quote", ""))
    x_tokens = numeric_tokens(quote)
    x_values = sorted({v for v, _ in x_tokens})
    if len(x_values) != 1:
        return answer, RepairOutcome(False, "numeric_ambiguous_or_absent")
    old_value = x_values[0]
    with_unit = [u for v, u in x_tokens if v == old_value and u]
    old_unit = with_unit[0] if with_unit else ""
    r_idx = find_subject_row(rows, subject)
    if r_idx is None:
        return answer, RepairOutcome(False, "subject_row_not_found")
    col = find_column(rows, (field,))
    y_cell = (rows[r_idx][col] if col is not None and col < len(rows[r_idx])
              else _row_text(rows, r_idx))
    y_match = re.search(r"\d+(?:\.\d+)?", y_cell)
    if y_match is None:
        return answer, RepairOutcome(False, "evidence_value_unparseable")
    new_value = y_match.group()
    if float(new_value) == float(old_value):
        return answer, RepairOutcome(False, "no_value_difference")
    unit_col = find_column(rows, ("单位",))
    y_unit = (rows[r_idx][unit_col] if unit_col is not None
              and unit_col < len(rows[r_idx]) else "")
    if y_unit in ("-", "—", "无", ""):
        y_unit = ""
    if not _units_compatible(old_unit, y_unit):
        return answer, RepairOutcome(False, "unit_incompatible")
    fixed = _replace_number(answer, old_value, new_value)
    if _number_present(fixed, old_value):
        return answer, RepairOutcome(False, "numeric_replace_incomplete")
    return fixed, RepairOutcome(True, operator="numeric_value", records=[{
        "old": old_value + old_unit, "new": new_value + y_unit,
        "note": f"数值对齐证据『{field}』列"}])


def repair_enum_member(row: dict, issue: dict,
                       answer: str) -> tuple[str, RepairOutcome]:
    """TERM-03: 枚举集合修正(条目删除+成员段替换+否定中和+token替换)."""
    spec = match_question(str(row.get("question", "")))
    if spec is None or spec[0] not in ("device", "stage"):
        return answer, RepairOutcome(False, "no_enum_subject")
    kind, subject_raw = spec[0], spec[1]
    subject, subject_alt = _norm_subject(subject_raw)
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    evidence = str(row["evidence"][ev_idx])
    quote = str(issue.get("quote", ""))
    rows = parse_table(evidence)
    members_e: list[str] = []
    if rows:
        r_idx = find_subject_row(rows, subject, subject_alt)
        if r_idx is None:
            return answer, RepairOutcome(False, "subject_row_not_found")
        col = find_column(rows, ("方式名称", "方式", "设备") if kind == "device"
                          else ("运行状态", "状态"))
        cell = (rows[r_idx][col] if col is not None and col < len(rows[r_idx])
                else _row_text(rows, r_idx))
        members_e = _split_members(cell)
    else:
        for seg in re.split(r"[。；\n]", evidence):
            if subject in seg or subject_alt in seg:
                members_e = _split_members(seg)
                if members_e:
                    break
    if kind == "device":                 # 家族过滤: 整行回退时不混入阶段词
        members_e = [m for m in members_e if m in DEVICE_MEMBERS]
    else:
        members_e = [m for m in members_e if m not in DEVICE_MEMBERS]
    if not members_e:
        return answer, RepairOutcome(False, "evidence_members_empty")
    target = set(members_e)
    target_str = "、".join(members_e)
    quote_members = member_tokens(quote)
    wrong = [m for m in quote_members if m not in target]
    denied = [m for m in members_e if _denial_in_text(quote, m)]
    quote_run_mismatch = any(set(r) != target for _, _, r in member_runs(quote))
    if not wrong and not denied and not quote_run_mismatch:
        return answer, RepairOutcome(False, "no_enum_violation_pattern")
    fixed = answer
    records: list[dict] = []
    # (1) 多余成员: 删除含该成员的编号条目行
    for w in wrong:
        item_re = re.compile(r"(?m)^[ \t]*\d+[\.、][^\n]*" + re.escape(w)
                             + r"[^\n]*\n?")
        fixed, n_items = item_re.subn("", fixed)
        if n_items:
            records.append({"old": w, "new": "(条目删除)",
                            "note": f"删除多余成员「{w}」的编号条目"})
    # (2) 成员段集合≠证据集合 → 替换为证据成员串(从右往左保位置有效)
    for start, end, run_members in sorted(member_runs(fixed), reverse=True):
        if set(run_members) != target:
            records.append({"old": fixed[start:end], "new": target_str,
                            "note": "枚举成员段对齐证据集合"})
            fixed = fixed[:start] + target_str + fixed[end:]
    # (3) 残余的多余成员token → 逐位置替换为证据成员串
    for w in wrong:
        for start, end, token in sorted(_member_spans(fixed), reverse=True):
            if token == w:
                records.append({"old": w, "new": target_str,
                                "note": f"多余成员「{w}」替换为证据集合"})
                fixed = fixed[:start] + target_str + fixed[end:]
                break
    # (4) 被否认成员: 否定中和
    for m in denied:
        fixed, n = _neutralize_denials(fixed, m)
        if n:
            records.append({"old": f"不支持{m}", "new": f"支持{m}",
                            "note": f"否定中和: 恢复成员「{m}」"})
    # 验证
    for w in wrong:
        if w in fixed:
            return answer, RepairOutcome(False, "excess_member_remains")
    for m in denied:
        if m not in fixed:
            return answer, RepairOutcome(False, "denied_member_missing")
        if _denial_in_text(fixed, m):
            return answer, RepairOutcome(False, "denial_remains")
    for _, _, run_members in member_runs(fixed):
        if set(run_members) != target:
            return answer, RepairOutcome(False, "member_run_unaligned")
    if fixed == answer:
        # 幂等: 引用同一violation的先前issue已修复完毕 → 视为成功
        return fixed, RepairOutcome(True, operator="enum_member",
                                    records=records)
    return fixed, RepairOutcome(True, operator="enum_member", records=records)


def _denial_in_text(text: str, member: str) -> bool:
    patterns = (
        r"不支持[^。；\n，]{0,12}" + re.escape(member),
        re.escape(member) + r"(?:设备|终端|版|形态)?不(?:在|提供|适用|可用|支持)",
        r"不(?:在|提供)[^。；\n，]{0,12}?" + re.escape(member),
    )
    return any(re.search(p, text) for p in patterns)


def _neutralize_denials(text: str, member: str) -> tuple[str, int]:
    total = 0
    pat_a = re.compile(r"不支持(?=[^。；\n，]{0,12}" + re.escape(member) + ")")
    text, n = pat_a.subn("支持", text)
    total += n
    pat_b = re.compile("(" + re.escape(member)
                       + r"(?:设备|终端|版|形态)?)(不)(在|提供|适用|可用|支持)")
    text, n = pat_b.subn(r"\1\3", text)
    total += n
    pat_c = re.compile(r"不(在[^。；\n，]{0,12}?" + re.escape(member) + ")")
    text, n = pat_c.subn(r"\1", text)
    total += n
    return text, total


def repair_id_binding(row: dict, issue: dict,
                      answer: str) -> tuple[str, RepairOutcome]:
    """TERM-07/08: answer中错误标识符 → 证据行绑定的标识符(列单元格优先)."""
    spec = match_question(str(row.get("question", "")))
    if spec is None or spec[0] not in ("interface", "usecase_name",
                                       "usecase_id"):
        return answer, RepairOutcome(False, "no_id_subject")
    subject, subject_alt = _norm_subject(spec[1])
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    rows = parse_table(str(row["evidence"][ev_idx]))
    if not rows:
        return answer, RepairOutcome(False, "evidence_not_table")
    r_idx = find_subject_row(rows, subject, subject_alt)
    if r_idx is None:
        return answer, RepairOutcome(False, "subject_row_not_found")
    col = find_column(rows, ("标识符", "标识", "ID"))
    if col is not None and col < len(rows[r_idx]) and \
            ID_RE.fullmatch(rows[r_idx][col]):
        y_list = [rows[r_idx][col]]
    else:
        y_list = sorted({m.group() for m in
                         ID_RE.finditer(_row_text(rows, r_idx))})
    if len(y_list) != 1:
        return answer, RepairOutcome(False, "evidence_id_ambiguous")
    new = y_list[0]
    quote = str(issue.get("quote", ""))
    x_list = [x for x in sorted({m.group() for m in ID_RE.finditer(quote)})
              if x != new]
    if not x_list:
        return answer, RepairOutcome(False, "no_wrong_id_in_quote")
    fixed = answer
    replaced = 0
    for old in x_list:
        fixed, n = re.subn(r"(?<![A-Z0-9-])" + re.escape(old)
                           + r"(?![A-Z0-9-])", new, fixed)
        replaced += n
    for old in x_list:
        if re.search(r"(?<![A-Z0-9-])" + re.escape(old) + r"(?![A-Z0-9-])",
                     fixed):
            return answer, RepairOutcome(False, "id_replace_incomplete")
    if replaced == 0 and new not in fixed:
        return answer, RepairOutcome(False, "id_not_found_in_answer")
    if replaced == 0:
        return fixed, RepairOutcome(True, operator="id_binding", records=[
            {"old": x, "new": new, "note": "标识符已对齐(先前issue已修复)"}
            for x in x_list])
    return fixed, RepairOutcome(True, operator="id_binding", records=[
        {"old": x, "new": new, "note": "标识符对齐证据行绑定"} for x in x_list])


def repair_party_binding(row: dict, issue: dict,
                         answer: str) -> tuple[str, RepairOutcome]:
    """LOGIC-04: 错误交互方/方向 → 证据接口表发送方/接收方.

    单向接口: 流向声称须精确匹配(发送方→接收方), 反向则对调,
    错位则按位置修正; 双向接口(rowspan多行): 双方集合内即可,
    仅修错误交互方. 修复后校验fixed中的全部流向声称一致.
    """
    spec = match_question(str(row.get("question", "")))
    if spec is None or spec[0] != "interface":
        return answer, RepairOutcome(False, "no_interface_subject")
    subject, subject_alt = _norm_subject(spec[1])
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    rows = parse_table(str(row["evidence"][ev_idx]))
    if not rows:
        return answer, RepairOutcome(False, "evidence_not_table")
    r_idx = find_subject_row(rows, subject, subject_alt)
    if r_idx is None:
        return answer, RepairOutcome(False, "subject_row_not_found")
    sender, receiver, parties_e, bidirectional = _interface_parties(rows, r_idx)
    if not parties_e:
        return answer, RepairOutcome(False, "empty_party_cells")
    parties_stripped = {_strip_party_suffix(p) for p in parties_e}
    quote = str(issue.get("quote", ""))
    claims = _party_claims(quote)
    if not claims:
        return answer, RepairOutcome(False, "no_party_claim_in_quote")
    fixed = answer
    records: list[dict] = []
    for m, claimed_sender, claimed_receiver in claims:
        cs = _strip_party_suffix(claimed_sender)
        cr = _strip_party_suffix(claimed_receiver)
        ev_s = _strip_party_suffix(sender)
        ev_r = _strip_party_suffix(receiver)
        if bidirectional:
            if cs in parties_stripped and cr in parties_stripped:
                continue                     # 双向接口: 任一方向均可
            if cs not in parties_stripped:
                fixed, rec = _fix_party(
                    fixed, parties_stripped - {cr}, claimed_sender)
                records += rec
            if cr not in parties_stripped:
                fixed, rec = _fix_party(
                    fixed, parties_stripped - {cs}, claimed_receiver)
                records += rec
            continue
        if cs == ev_s and cr == ev_r:
            continue                         # 与证据流向一致
        if cs == ev_r and cr == ev_s and ev_s != ev_r:
            old_span = m.group(0)            # 反向 → 对调
            if old_span in fixed:
                new_span = (old_span.replace(claimed_sender, "@@A@@", 1)
                            .replace(claimed_receiver, claimed_sender, 1)
                            .replace("@@A@@", claimed_receiver, 1))
                fixed = fixed.replace(old_span, new_span, 1)
                records.append({"old": old_span, "new": new_span,
                                "note": "流向方向对调(对齐证据收发方)"})
            continue
        if cs != ev_s:                       # 错位 → 按位置修正
            fixed, rec = _fix_party(fixed, {ev_s}, claimed_sender)
            records += rec
        if cr != ev_r:
            fixed, rec = _fix_party(fixed, {ev_r}, claimed_receiver)
            records += rec
    # 校验: fixed中全部流向声称须一致(幂等: 先前issue已修复也通过)
    for m, a, b in _party_claims(fixed):
        cs, cr = _strip_party_suffix(a), _strip_party_suffix(b)
        if bidirectional:
            if cs not in parties_stripped or cr not in parties_stripped:
                return answer, RepairOutcome(False, "party_residual_mismatch")
        elif not (cs == _strip_party_suffix(sender)
                  and cr == _strip_party_suffix(receiver)):
            return answer, RepairOutcome(False, "party_residual_mismatch")
    if fixed == answer:
        return fixed, RepairOutcome(True, operator="party_binding",
                                    records=records)   # 已一致(幂等)
    return fixed, RepairOutcome(True, operator="party_binding", records=records)


def _fix_party(fixed: str, right_candidates: set[str],
               wrong: str) -> tuple[str, list[dict]]:
    """把错误交互方wrong替换为候选right(短词仅全局替换需≥4字)."""
    right = sorted(right_candidates)[0] if right_candidates else ""
    if not right or wrong not in fixed:
        return fixed, []
    core = _strip_party_suffix(wrong)
    if len(core) < _PARTY_GLOBAL_MIN:
        return fixed, []                     # 过短不做全局替换(风险高)
    return fixed.replace(wrong, right), [{
        "old": wrong, "new": right, "note": "交互方对齐证据"}]


def _interface_parties(rows: list[list[str]], r_idx: int
                       ) -> tuple[str, str, set[str], bool]:
    """接口行的(发送方, 接收方, 双方全集, 是否双向).

    双向=rowspan续行存在(同一接口多行流向); 续行单元格按值收集
    (过滤类型/优先级等非交互方值).
    """
    s_col = find_column(rows, ("发送方",))
    r_col = find_column(rows, ("接收方",))
    sender = receiver = ""
    cells = rows[r_idx]
    if s_col is not None and s_col < len(cells):
        sender = cells[s_col]
    if r_col is not None and r_col < len(cells):
        receiver = cells[r_col]
    parties = {p for p in (sender, receiver) if p}
    h_len = _header_len(rows)
    j = r_idx + 1
    bidirectional = False
    while h_len and j < len(rows) and len(rows[j]) < h_len \
            and not _is_header_row(rows[j]):
        bidirectional = True
        for cell in rows[j]:
            if cell and not _NON_PARTY_RE.search(cell):
                parties.add(cell)
        j += 1
    return sender, receiver, parties, bidirectional


def _party_claims(text: str) -> list[tuple[re.Match, str, str]]:
    claims: list[tuple[re.Match, str, str]] = []
    for pattern in (r"由([^，。；\n]{2,15}?)(?:单向)?发送[至到]([^，。；\n]{2,15})",
                    r"(?:是|为)([^，。；\n]{2,15}?)与([^，。；\n]{2,15}?)之间",
                    r"流向为([^，。；\n]{2,15}?)(?:端)?指向([^，。；\n]{2,15})"):
        for m in re.finditer(pattern, text):
            claims.append((m, m.group(1), m.group(2)))
    return claims


def _strip_party_suffix(party: str) -> str:
    return re.sub(r"(端|侧)$", "", party.strip())


def repair_term_unify(row: dict, issue: dict,
                      answer: str) -> tuple[str, RepairOutcome]:
    """TERM-01: 同义异名 → 证据用词(仅在issue引用的span内替换)."""
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    evidence = str(row["evidence"][ev_idx])
    quote = str(issue.get("quote", ""))
    pos = answer.find(quote)
    if pos < 0:
        return answer, RepairOutcome(False, "quote_not_in_answer")
    for old, new in TermSynonymSwap.SYNONYMS.items():
        for a, b in ((old, new), (new, old)):
            if a in quote and b in evidence and a not in evidence:
                seg = answer[pos:pos + len(quote)]
                fixed = answer[:pos] + seg.replace(a, b) + \
                    answer[pos + len(quote):]
                return fixed, RepairOutcome(True, operator="term_unify",
                                            records=[{
                                                "old": a, "new": b,
                                                "note": "术语统一为证据用词"
                                                        "(span内)"}])
    return answer, RepairOutcome(False, "no_synonym_pair")


def repair_operator_flip(row: dict, issue: dict,
                         answer: str) -> tuple[str, RepairOutcome]:
    """PARAM-06(操作符形): answer操作词 → 证据操作词(复用OP_FLIP表)."""
    spec = match_question(str(row.get("question", "")))
    if spec is None or spec[0] != "numeric":
        return answer, RepairOutcome(False, "no_numeric_subject")
    subject, groups = spec[1], spec[2]
    ev_idx = _evidence_index(issue, row)
    if ev_idx is None:
        return answer, RepairOutcome(False, "bad_evidence_ref")
    rows = parse_table(str(row["evidence"][ev_idx]))
    r_idx = find_subject_row(rows, subject)
    if r_idx is None:
        return answer, RepairOutcome(False, "subject_row_not_found")
    field = groups.get("field", "最大值")
    col = find_column(rows, (field,))
    cell = (rows[r_idx][col] if col is not None and col < len(rows[r_idx])
            else _row_text(rows, r_idx))
    quote = str(issue.get("quote", ""))
    flip = ParamValueRangeConflict.OP_FLIP
    answer_ops = [op for op in flip if op in quote]
    evidence_ops = [op for op in flip if op in cell]
    if not answer_ops or not evidence_ops:
        return answer, RepairOutcome(False, "no_operator_words")
    old, new = answer_ops[0], evidence_ops[0]
    if old == new:
        return answer, RepairOutcome(False, "no_operator_difference")
    pos = answer.find(quote)
    if pos < 0:
        return answer, RepairOutcome(False, "quote_not_in_answer")
    seg = answer[pos:pos + len(quote)]
    fixed = answer[:pos] + seg.replace(old, new, 1) + \
        answer[pos + len(quote):]
    return fixed, RepairOutcome(True, operator="operator_flip", records=[{
        "old": old, "new": new, "note": "操作符对齐证据"}])


def _norm_subject(subject: str) -> tuple[str, str]:
    """主词归一: 剥离功能/用例后缀作短形式, 原词作备用."""
    alt = subject
    for suffix in ("功能", "用例"):
        if subject.endswith(suffix) and len(subject) > len(suffix) + 1:
            alt = subject[: -len(suffix)]
            break
    return alt, subject


# ── 派发与行级装配 ───────────────────────────────────────────

#: rule_id → 算子链(依次应用, ≥1成功即issue修复; 终检兜底全局一致性)
RULE_OPERATORS: dict[str, list[str]] = {
    "GJB-05": ["chapter"],
    "PARAM-01": ["numeric"], "PARAM-02": ["numeric"], "PARAM-05": ["numeric"],
    "PARAM-06": ["numeric", "opflip"], "PARAM-07": ["numeric"],
    "TERM-03": ["enum"],
    "TERM-07": ["id", "party"], "TERM-08": ["id", "party"],
    "LOGIC-04": ["party"],
    "TERM-01": ["term"],
}
_OPERATOR_FUNCS = {
    "chapter": repair_chapter_number,
    "numeric": repair_numeric_value,
    "opflip": repair_operator_flip,
    "enum": repair_enum_member,
    "id": repair_id_binding,
    "party": repair_party_binding,
    "term": repair_term_unify,
}


def _repair_one(row: dict, issue: dict,
                answer: str) -> tuple[str, RepairOutcome]:
    rule = str(issue.get("rule_id", ""))
    op_names = RULE_OPERATORS.get(rule)
    if not op_names:
        return answer, RepairOutcome(False, f"no_operator_for_rule:{rule}")
    fixed = answer
    records: list[dict] = []
    operators: list[str] = []
    first_reason = ""
    for name in op_names:
        new_fixed, outcome = _OPERATOR_FUNCS[name](row, issue, fixed)
        if outcome.ok:
            fixed = new_fixed
            records += outcome.records
            operators.append(outcome.operator)
        elif not first_reason:
            first_reason = outcome.reason     # 主算子(首个)失败原因
    if not operators:
        return answer, RepairOutcome(False, first_reason or "no_op_succeeded")
    op = operators[0] if len(set(operators)) == 1 else "mixed"
    return fixed, RepairOutcome(True, operator=op, records=records)


def _evidence_flat(row: dict) -> str:
    text = "".join(str(e) for e in (row.get("evidence") or []))
    return re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", text))


def _final_sweeps(row: dict, fixed: str) -> str:
    """终检: 残余ID/章节号须在证据中; 接口流向声称的双方须在证据双方内."""
    ev_flat = _evidence_flat(row)
    for m in ID_RE.finditer(fixed):
        if m.group() not in ev_flat:
            return f"id_residual_out_of_evidence:{m.group()}"
    for m in CHAPTER_RE.finditer(fixed):
        if m.group() not in ev_flat:
            return f"chapter_residual_out_of_evidence:{m.group()}"
    spec = match_question(str(row.get("question", "")))
    if spec is not None and spec[0] == "interface":
        subject, subject_alt = _norm_subject(spec[1])
        for issue in row.get("issues") or []:
            ev_idx = _evidence_index(issue, row)
            if ev_idx is None:
                continue
            rows = parse_table(str(row["evidence"][ev_idx]))
            r_idx = find_subject_row(rows, subject, subject_alt)
            if r_idx is None:
                continue
            _, _, parties_e, _bidirectional = _interface_parties(rows, r_idx)
            if not parties_e:
                continue
            parties_stripped = {_strip_party_suffix(p) for p in parties_e}
            for _m, claimed_sender, claimed_receiver in _party_claims(fixed):
                for party in (claimed_sender, claimed_receiver):
                    if _strip_party_suffix(party) not in parties_stripped:
                        return f"party_residual_mismatch:{party}"
    return ""


def build_minimal_pair(row: dict) -> tuple[dict | None, str]:
    """行级装配: 所有issue全部修复+终检通过才产出pair."""
    issues = row.get("issues") or []
    answer = str(row.get("answer", ""))
    fixed = answer
    records: list[dict] = []
    ops: list[str] = []
    for idx, issue in enumerate(issues):
        quality = issue.get("quality") or {}
        faithful = quality.get("faithful")
        if faithful is None or faithful < 2:
            return None, f"faithful_lt2:issue{idx}"
        new_fixed, outcome = _repair_one(row, issue, fixed)
        if not outcome.ok:
            return None, f"issue{idx}:{outcome.reason}"
        fixed = new_fixed
        ops.append(outcome.operator)
        records += [{"issue_idx": idx,
                     "rule_id": str(issue.get("rule_id", "")),
                     **rec} for rec in outcome.records]
    if fixed == answer:
        return None, "no_change"
    ratio = len(fixed) / max(len(answer), 1)
    if not (_LEN_BAND[0] <= ratio <= _LEN_BAND[1]):
        return None, f"length_band:{ratio:.2f}"
    sweep = _final_sweeps(row, fixed)
    if sweep:
        return None, sweep
    repair_type = ops[0] if len(set(ops)) == 1 else "mixed"
    qualities = [(i.get("quality") or {}) for i in issues]
    pair = {
        "instance_id": str(row["instance_id"]),
        "corpus": row.get("corpus", ""),
        "question": str(row.get("question", "")),
        "evidence": list(row.get("evidence") or []),
        "original_answer": answer,
        "fixed_answer": fixed,
        "expected_flip": "refute→support",
        "orig_verdict": str(row.get("verdict", "")),
        "repair_type": repair_type,
        "repairs": records,
        "quality": {
            "min_faithful": min((q.get("faithful") for q in qualities
                                 if q.get("faithful") is not None), default=None),
            "min_truthful": min((q.get("truthful") for q in qualities
                                 if q.get("truthful") is not None), default=None),
            "min_useful": min((q.get("useful") for q in qualities
                               if q.get("useful") is not None), default=None),
        },
    }
    return pair, ""


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_candidates(labels_path: Path, extra_path: Path | None
                    ) -> tuple[list[dict], dict]:
    """faithful≥2的refute条目(按instance_id去重, labels优先, 确定序)."""
    rows: dict[str, dict] = {}
    low_ids: set[str] = set()
    stats = Counter()
    for path in (labels_path, extra_path):
        if path is None:
            continue
        for row in read_jsonl(path):
            sid = str(row.get("instance_id", ""))
            if str(row.get("verdict", "")) != "refute" or not row.get("issues"):
                continue
            if sid in rows or sid in low_ids:
                continue
            if not all((i.get("quality") or {}).get("faithful") is not None
                       and (i.get("quality") or {}).get("faithful", 0) >= 2
                       for i in row["issues"]):
                low_ids.add(sid)
                continue
            rows[sid] = row
    stats["rows_faithful_lt2"] = len(low_ids)
    candidates = sorted(rows.values(), key=lambda r: str(r["instance_id"]))
    return candidates, dict(stats)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BASE))
    except ValueError:
        return str(path)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, default=LABELS_DEFAULT,
                        help="gated数据(默认d3_train_v3f_gated.jsonl)")
    parser.add_argument("--extra-gate", type=Path, default=None,
                        help="补充gate评分文件(runs里的gate_scores_union.jsonl)")
    parser.add_argument("--out", type=Path, default=OUT_PAIRS)
    args = parser.parse_args()

    candidates, load_stats = load_candidates(args.labels, args.extra_gate)
    config = {
        "task": "e5_step2_minimal_pairs",
        "labels": _rel(args.labels),
        "extra_gate": _rel(args.extra_gate) if args.extra_gate else "",
        "rules_with_operators": sorted(RULE_OPERATORS),
        "length_band": list(_LEN_BAND),
        "qa_mutation_ops_reused": [
            "ParamTimeConflict.TIME_PAT", "ParamPeriodConflict.PERIOD_PAT",
            "ParamResourceConflict.RES_PAT", "ParamStorageConflict.STORE_PAT",
            "ParamValueRangeConflict.OP_FLIP", "TermUnitMismatch.UNIT_EQ",
            "TermSynonymSwap.SYNONYMS"],
    }
    run = open_run("e5_minimal_pairs", config)

    pairs: list[dict] = []
    skip: Counter = Counter()
    corpus_dist: Counter = Counter()
    for row in candidates:
        pair, reason = build_minimal_pair(row)
        if pair is None:
            skip[reason.split(":")[0]] += 1
            if ":" in reason:
                skip[reason] += 1
            continue
        pairs.append(pair)
        corpus_dist[pair["corpus"]] += 1

    with open(args.out, "w", encoding="utf-8") as f:
        for i, pair in enumerate(pairs, 1):
            pair["pair_id"] = f"E5MP-{i:04d}"
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    type_dist = Counter(p["repair_type"] for p in pairs)
    report = {
        "task": "e5_step2_minimal_pairs",
        "candidates": {
            "rows_faithful_ge2_refute": len(candidates),
            "rows_faithful_lt2_excluded": load_stats.get("rows_faithful_lt2", 0),
        },
        "pairs_written": len(pairs),
        "repair_type_distribution": dict(type_dist.most_common()),
        "pair_corpus_distribution": dict(corpus_dist.most_common()),
        "skip_reasons": {k: v for k, v in skip.most_common() if ":" not in k},
        "skip_reasons_detail": {k: v for k, v in skip.most_common()
                                if ":" in k},
        "out": _rel(args.out),
        "example_pair": {k: pairs[0][k] for k in
                         ("pair_id", "instance_id", "question",
                          "original_answer", "fixed_answer", "expected_flip",
                          "repair_type", "repairs")} if pairs else None,
    }
    run.save_result(report)
    print(f"候选refute行(全issue faithful≥2): {len(candidates)}"
          f" (faithful<2剔除{load_stats.get('rows_faithful_lt2', 0)})")
    print(f"最小变更对: {len(pairs)} → {args.out}")
    print(f"repair_type分布: {dict(type_dist.most_common())}")
    print(f"跳过原因: {report['skip_reasons']}")
    print(f"run目录: {run.path}")


if __name__ == "__main__":
    main()
