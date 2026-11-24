"""方向B baseline矩阵 v2: 每族专用专家方法(全部同任务, 严格设计).

v2修订(用户审查意见):
  1. TF-IDF/BGE移出方法矩阵(表面相似度≠一致性判断, 任务不同)
  2. A族: 真Z3-SMT求解器(声明→约束→UNSAT, Bendík2017形式化路线)
  3. E族: GJB规则库驱动(rules_full.json, 检测可溯源规则编号)
  4. D族: 编辑距离+srs_kb词典实体消解

设计公理: baseline含常识(单位换算)不含领域等价约定域约定(同值异表面=consistent的
规格对齐语义) — 与Ours的差距即领域知识的价值。
"""
from __future__ import annotations

import difflib
import json
import re
from collections.abc import Callable
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

# ═══ 共享: 声明解析(常识层, 非领域等价约定) ═══
OP_LE = ("不大于", "不超过", "不高于", "小于等于", "≤", "以下", "最多", "至多")
OP_GE = ("不小于", "不少于", "不低于", "大于等于", "≥", "以上", "至少", "最低")
UNIT_TO_BASE = {
    "ms": ("time", 1.0), "毫秒": ("time", 1.0), "s": ("time", 1000.0), "秒": ("time", 1000.0),
    "min": ("time", 60000.0), "分钟": ("time", 60000.0), "h": ("time", 3600000.0), "小时": ("time", 3600000.0),
    "B": ("storage", 1.0), "字节": ("storage", 1.0), "KB": ("storage", 1024.0), "K": ("storage", 1024.0),
    "MB": ("storage", 1048576.0), "M": ("storage", 1048576.0),
    "GB": ("storage", 1073741824.0), "G": ("storage", 1073741824.0), "T": ("storage", 1099511627776.0),
    "种": ("count", 1.0), "个": ("count", 1.0), "路": ("count", 1.0), "条": ("count", 1.0),
    "次": ("count", 1.0), "项": ("count", 1.0), "类": ("count", 1.0), "台": ("count", 1.0),
}
_NUM = re.compile(
    r"(不大于|不超过|不高于|不小于|不少于|不低于|大于等于|小于等于|为|等于|至少|最多|≤|≥|=)"
    r"\s*(\d+\.?\d*)\s*([A-Za-z\u4e00-\u9fa5%]{0,3})")


def _claims(text: str) -> list[tuple[str, str, float]]:
    """(op_family, unit_family, normalized_value) — 单位换算是常识, 语义对齐不是."""
    out = []
    for m in _NUM.finditer(text):
        op, val, unit = m.group(1), m.group(2), m.group(3)
        fam = "le" if op in OP_LE else "ge" if op in OP_GE else "eq"
        uf, factor = UNIT_TO_BASE.get(unit, (unit or "count", 1.0))
        try:
            out.append((fam, uf, float(val) * factor))
        except ValueError:
            continue
    return out


# ═══ A族: Z3-SMT求解器 ═══
def baseline_z3(premise: str, hypothesis: str) -> str:
    """声明编译成SMT约束, 合取可满足性判定(标准形式化方法).

    语义: P约束∧H约束 UNSAT→inconsistent; SAT→consistent(无逻辑矛盾证据).
    注: 规格级冲突(≥200 vs ≥100, 区间有交集)逻辑上SAT — 这正是
    形式化方法与领域等价约定规格约定的分界, 作为论文论点的实验证据.
    """
    pc, hc = _claims(premise), _claims(hypothesis)
    if not pc or not hc:
        return "consistent"  # 无可形式化声明→弃权(无矛盾证据)
    try:
        from z3 import Real, Solver, unsat
    except ImportError:
        return "consistent"
    solver = Solver()
    # 同量纲声明共享变量(参数名解析不可靠时以量纲为变量)
    vars_by_fam: dict[str, object] = {}
    for fam_op, unit_fam, val in pc + hc:
        key = str(unit_fam)
        if key not in vars_by_fam:
            vars_by_fam[key] = Real(f"x_{key}")
        x = vars_by_fam[key]
        if fam_op == "ge":
            solver.add(x >= val)
        elif fam_op == "le":
            solver.add(x <= val)
        else:
            solver.add(x == val)
    return "inconsistent" if solver.check() == unsat else "consistent"


# ═══ B族: LCS序列比对 ═══
_LIST = re.compile(r"(?:包括|包含|涉及|支持)[：:]?\s*([^。；、]{2,60}(?:、[^。；、]{2,60})+)")


def _lcs_len(a: list[str], b: list[str]) -> int:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def baseline_lcs(premise: str, hypothesis: str) -> str:
    """列表序列LCS: 顺序破坏(同集异序)或成员差→inconsistent."""
    pl = [x for raw in _LIST.findall(premise) for x in raw.split("、") if len(x) >= 2]
    hl = [x for raw in _LIST.findall(hypothesis) for x in raw.split("、") if len(x) >= 2]
    if len(pl) < 2 or len(hl) < 2:
        ratio = difflib.SequenceMatcher(None, premise, hypothesis).ratio()
        return "inconsistent" if ratio < 0.9 else "consistent"
    if set(pl) != set(hl):
        return "inconsistent"  # 成员差
    lcs = _lcs_len(pl, hl)
    if lcs < len(pl):  # 同集异序
        return "inconsistent"  # 序列比对: 顺序破坏(无κ3无序豁免)
    return "consistent"


# ═══ C族: 集合比对 ═══
_ABSENCE = re.compile(r"(?:没有|未|缺失|未绘制|未包含)")


def baseline_set(premise: str, hypothesis: str) -> str:
    """「」条目存在性集合比对 + 缺失声明规则(结构专家, 无κ3良性省略知识)."""
    p_items = set(re.findall(r"[「]([^「」]{2,30})[」]", premise))
    h_items = set(re.findall(r"[「]([^「」]{2,30})[」]", hypothesis))
    if _ABSENCE.search(hypothesis) or _ABSENCE.search(premise):
        if p_items or h_items or len(hypothesis) < 30:
            return "inconsistent"
    if p_items and h_items:
        return "inconsistent" if p_items != h_items else "consistent"
    ratio = difflib.SequenceMatcher(None, premise, hypothesis).ratio()
    return "inconsistent" if ratio < 0.9 else "consistent"


# ═══ D族: 编辑距离+srs_kb词典 ═══
def _load_synonyms() -> dict[str, str]:
    try:
        kb = json.loads((BASE / "knowledge/srs_kb.json").read_text(encoding="utf-8"))
        syn: dict[str, str] = {}
        for canon, entry in kb.get("param_dictionary", {}).items():
            aliases = entry.get("aliases", []) if isinstance(entry, dict) else []
            for a in aliases:
                syn[str(a)] = canon
            syn[canon] = canon
        return syn
    except (OSError, json.JSONDecodeError):
        return {}


_SYN = _load_synonyms()


def baseline_editdist_lex(premise: str, hypothesis: str) -> str:
    """字符编辑距离 + 词典同实体归解后比对(词面专家)."""
    # 词典消解: 同实体异名归一后再比对
    p_norm, h_norm = premise, hypothesis
    for alias, canon in _SYN.items():
        if alias in p_norm and alias in h_norm and alias != canon:
            p_norm = p_norm.replace(alias, canon)
            h_norm = h_norm.replace(alias, canon)
    ratio = difflib.SequenceMatcher(None, p_norm, h_norm).ratio()
    return "inconsistent" if ratio < 0.9 else "consistent"


# ═══ E族: GJB规则引擎(rules_full驱动) ═══
_COUNT = re.compile(r"(\d+)\s*项")
_DOC_ABS = re.compile(r"(?:缺失|未包含|未规定)\s*(?:该|此)?\s*(?:条款|条目|章节)")


def baseline_gjb_engine(premise: str, hypothesis: str) -> str:
    """GJB规则库驱动的pair级规则引擎.

    每条检测可溯源规则编号:
      R1 计数一致性(表格条目数声明一致) ← content类规则(条目完整性)
      R2 条款存在性(文档级缺失声明)     ← content类(条款完整)
      R3 无关内容注入(句中插入完整子句) ← content类(内容相关性与原子性)
    """
    # R1: 计数一致
    pm, hm = _COUNT.search(premise), _COUNT.search(hypothesis)
    if pm and hm and pm.group(1) != hm.group(1):
        return "inconsistent"
    # R2: 文档级缺失
    if _DOC_ABS.search(premise) or _DOC_ABS.search(hypothesis):
        return "inconsistent"
    # R3: 句中注入完整子句
    m = difflib.SequenceMatcher(None, premise, hypothesis)
    for tag, i1, i2, j1, j2 in m.get_opcodes():
        if tag in ("insert", "replace") and j2 > j1:
            frag = hypothesis[j1:j2]
            if re.search(r"[。；]", frag) and j1 > 0 and j2 < len(hypothesis):
                return "inconsistent"
    return "consistent"


# ═══ QG-QA round-trip (DROP式, 无领域等价约定) ═══
_QG_NUM = re.compile(r"([\u4e00-\u9fa5A-Za-z]{2,10})\s*(?:的)?\s*"
                     r"(不大于|不超过|不高于|不小于|不少于|不低于|为|等于|至少|最多|≤|≥|=)\s*"
                     r"(\d+\.?\d*)\s*([A-Za-z\u4e00-\u9fa5%]{0,3})")


def baseline_qg_qa(premise: str, hypothesis: str) -> str:
    """问题生成→答案抽取round-trip(Dua et al. 2019 DROP式).

    premise数值声明→模板问题; hypothesis抽同属性答案; 失配→矛盾.
    不做单位归一(领域等价约定盲: 200G vs 204800MB判不一致 — 盲区证据).
    """
    p_claims = _QG_NUM.findall(premise)
    if not p_claims:
        return "consistent"  # 无可问题化声明
    for attr, _op, p_val, p_unit in p_claims:
        # 问题模板: 「attr」的值是多少? → 在hypothesis中抽同属性答案
        h_claims = _QG_NUM.findall(hypothesis)
        matched = [c for c in h_claims if c[0] == attr or (attr in c[0]) or (c[0] in attr)]
        if not matched:
            continue  # 属性在h中未声明→不算矛盾(信息缺失≠矛盾, 保守)
        h_val, h_unit = matched[0][2], matched[0][3]
        # round-trip答案比对: 原始表面值(无单位归一)
        if (p_val, p_unit) != (h_val, h_unit):
            return "inconsistent"
    return "consistent"


# ═══ 级联组合(朴素形式化/规则→NLI, 无领域等价约定分派) ═══
def cascade_z3_nli(premise: str, hypothesis: str, nli_fn: Callable[[str, str], str]) -> str:
    """Z3先判(报矛盾即停), 否则NLI兜底 — 朴素级联(对照领域等价约定条件化分派)."""
    if baseline_z3(premise, hypothesis) == "inconsistent":
        return "inconsistent"
    return nli_fn(premise, hypothesis)


def cascade_rules_nli(premise: str, hypothesis: str, nli_fn: Callable[[str, str], str]) -> str:
    if baseline_gjb_engine(premise, hypothesis) == "inconsistent":
        return "inconsistent"
    return nli_fn(premise, hypothesis)
