r"""Z3数值约束专家（L1组件，设计§6.3"区间算术+数值聚合"两行）。

任务定位：``qa_module._verify_numeric``（纯Python区间包含/交空判定）的
Z3深化，作为独立专家通道加入 ``qa_module._expert_channels``，**不替换**
原通道（原通道继续负责answer算子式声明与同单位族快速路径）。三处能力
增量：

1. **量纲换算**：srs_kb单位族（time/storage/frequency/data_rate/…）+
   中文别名（毫秒/秒/分钟/小时/字节/天/日）+ count族（条/个/次/种/路/
   项/类/台），单位不一致时换算到族基准后比较（"1s" vs "1000ms"换算后
   相等→support）；未知单位退化为同名族（仅同串可比，绝不跨族猜测）。
   temperature族为仿射换算（K/F→℃），乘法因子表不可表达，跳过。
2. **区间三态Z3判定**（PARAM-03/06/07）：answer约束C_a与同subject证据
   约束E（合取）：
   - E∧C_a UNSAT→refute（附unsat core与完整SMT-LIB，防scope laundering，
     Know Your Limits教训）；
   - C_a∧¬E UNSAT→support（answer解集⊆证据解集：answer声称的约束不弱于
     文档声明，如"最大100ms"vs"不超过50ms"）；
   - 其余SAT→NIE（部分重叠不可判定）；E自身UNSAT→NIE+unsat core
     （context内部数值矛盾，不仲裁answer）。
3. **跨参数聚合检查**（PARAM-01/05，Logic-LM式程序合成）：answer含聚合
   声明（subject含"总/之和/合计/总计/总共"，如"总时间不超过N"/"三者
   之和≤M"）而证据有同单位族≥2个互异subject的分量约束时，Z3构造
   Σ(分量_i)聚合约束与分量约束联查：E∧C UNSAT→refute（unsat core指明
   哪些分量参与矛盾）；E∧¬C UNSAT→support（分量值保证聚合成立）。
   91条真实QA中无此形态，能力由合成测试证明（对16份文档的能力声明）。

数值事实来源（evidence_statements线性化语句）：
- 字段式（数据表）："X的最大差：100ms"/"X的最小差：5ms"/"X的精度：N"
  （最大差/上限/最大值→le，最小差/下限/最小值→ge，精度→eq）；
  "X的单位：ms"作为同主体缺单位事实的族消解依据；
- 算子式（正文）："X不超过N{单位}"/"X至少N"/"X为N"（复用qa_module的
  _extract_numeric_claims，冒号删除以覆盖表格cell"内存：不小于16GB"
  形态）。

字段类join键（C06QA-008修复）：数据表同一数据项的最大值/最小值/精度是
**三个不同量**（上限、下限、小数位数），字段式事实携带字段类标记
（max/min/precision）；answer主体的字段限定词（"X的最大值为200"的
"的最大值"）同样解析为字段类并剥离出核心主体。区间join按字段类过滤：
带限定的声明只与同字段类（或同向算子式）事实比对，无限定声明（值本身）
与max/min/算子式事实比对——修复前answer的eq声明与证据"精度：1"行误join
（eq200∧eq1→UNSAT伪refute，06号表97最大连接数行）。

claim_text与qa_module数值通道同构（"{subject} {op}{value}{unit}"），
per-claim融合（refute>support>NIE）自动仲裁两通道对同一声明的分歧。
Z3求解带timeout（500ms，防坏约束挂死）；unknown/异常→NIE+诊断（不
静默）。完全确定性：无模型调用、无检索；文件读取两处——srs_kb.json
（单位族资产，函数内读取+lru_cache模块级缓存）与默认rule pack
（config/rulepacks/srs_gjb_v1.json的join_params.numeric_z3：中文单位
别名/补充单位因子/字段→算子映射/聚合声明标记，经_cfg()惰性编译，成员
与迁移前源码逐字一致）。Z3_TIMEOUT_MS与单位token文法留引擎（求解器
资源限制与抽取语法，非域知识）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from z3 import (
        And,
        Not,
        Real,
        RealVal,
        Solver,
        Sum,
        Z3Exception,
        get_version_string,
        sat,
        unsat,
    )
except ImportError:  # fast档零依赖: z3未装时本专家显式降级(诊断可见)
    And = Not = Real = RealVal = Solver = Sum = None  # type: ignore[assignment]
    Z3Exception = None  # type: ignore[assignment]
    get_version_string = None  # type: ignore[assignment]
    sat = unsat = None  # type: ignore[assignment]

from srs_verify.evidence_statements import EvidenceStatement
from srs_verify.qa_models import ClaimResult, QAInput
from srs_verify.answer_claims import (
    extract_numeric_claims as _extract_numeric_claims,
    question_numeric_subject,
)
from srs_verify.claim_channels import same_subject
from srs_verify.rulepack import RulePack, default_rulepack
from srs_verify.templates import normalize_op

METHOD = "numeric_z3_expert"
CHECK_ITEMS_INTERVAL: tuple[str, ...] = ("PARAM-03", "PARAM-06", "PARAM-07")
CHECK_ITEMS_AGGREGATE: tuple[str, ...] = ("PARAM-01", "PARAM-05")
#: Z3求解超时毫秒数（硬规则：防坏约束挂死）
Z3_TIMEOUT_MS = 500

def _srs_kb_path() -> Path:
    """单位族资产路径: 包内configs优先, 找不到回退仓库knowledge/原路径."""
    here = Path(__file__).resolve().parent
    candidates = (here / "configs" / "srs_kb.json",
                  Path(__file__).resolve().parents[2] / "knowledge"
                  / "srs_kb.json")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]

_OP_SYMBOLS = {"le": "≤", "lt": "<", "ge": "≥", "gt": ">", "eq": "="}

#: 中文单位别名/补充单位因子/字段→算子映射/聚合声明标记已迁入rule pack
#: （join_params.numeric_z3，经_cfg()惰性编译，成员与迁移前源码逐字一致）。

#: 字段名→字段类（量纲类型）：数据表同一数据项的最大值/最小值/精度是
#: 三个不同的量，字段类作为区间join的匹配键之一，防止跨字段误join。
#: 字段名词表在rule pack（field_name_ops）；此处只登记引擎已知的量纲
#: 语义——配置新增字段名缺省为""（值幅度类，与max/min/算子式事实同类）。
_FIELD_CLASS: dict[str, str] = {
    "最大差": "max", "上限": "max", "最大值": "max",
    "最小差": "min", "下限": "min", "最小值": "min",
    "精度": "precision",
}

#: answer主体尾部字段限定词→字段类（claim侧量纲解析）。最大值/最小值/
#: 最大差/最小差允许裸形（值/差后缀足够特异）；上限/下限/最大/最小/精度
#: 要求"的"前缀——裸形会与数据项名冲突（如"告警上限"/"定位精度"）。
_CLAIM_FIELD_QUALIFIERS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern), field_class)
    for pattern, field_class in (
        (r"(?:的)?(?:最大值|最大差)$", "max"),
        (r"(?:的)?(?:最小值|最小差)$", "min"),
        (r"的(?:上限|最大)$", "max"),
        (r"的(?:下限|最小)$", "min"),
        (r"的精度$", "precision"),
    )
)

_SUBJECT_TOKEN = r"[\u4e00-\u9fffA-Za-z0-9（）()\-]{2,32}"
_UNIT_TOKEN = (
    r"(?:[A-Za-zµμ%℃]{1,8}|毫秒|微秒|纳秒|秒|分钟|小时|天|日|字节"
    r"|条|个|次|种|路|项|类|台|用户|节点|核)"
)
_UNIT_DECL_RE = re.compile(
    rf"(?P<subject>{_SUBJECT_TOKEN})的(?:计量)?单位(?:[是为：:]\s*)"
    rf"(?P<unit>{_UNIT_TOKEN})"
)


@dataclass(frozen=True)
class _NumericConfig:
    """从rule pack编译的数值专家词典配置（成员与迁移前源码逐字一致）.

    field_name_ops的键序即field_fact_re字段alternation的顺序（JSON对象
    保序）；cn_unit_aliases/extra_unit_factors与srs_kb单位族资产在
    _unit_table()合并。field_fact_re由field_name_ops键序构建，字段命中
    即在映射内（构建不变量）。
    """

    cn_unit_aliases: dict[str, str]
    extra_unit_factors: dict[str, tuple[str, float]]
    field_name_ops: dict[str, str]
    aggregate_markers: tuple[str, ...]
    field_fact_re: re.Pattern[str]


def _build_config(pack: RulePack) -> _NumericConfig:
    where = f"rulepack {pack.pack_id!r} join_params.numeric_z3"
    aliases_raw = pack.join_param("numeric_z3", "cn_unit_aliases", {})
    if (not isinstance(aliases_raw, dict) or not aliases_raw
            or not all(isinstance(k, str) and k and isinstance(v, str) and v
                       for k, v in aliases_raw.items())):
        raise ValueError(f"{where}.cn_unit_aliases须为非空字符串映射")
    factors_raw = pack.join_param("numeric_z3", "extra_unit_factors", {})
    if not isinstance(factors_raw, dict) or not factors_raw:
        raise ValueError(
            f"{where}.extra_unit_factors须为非空"
            f"{{单位token: [族名, 因子]}}映射")
    factors: dict[str, tuple[str, float]] = {}
    for token, entry in factors_raw.items():
        if (not isinstance(token, str) or not token
                or not isinstance(entry, (list, tuple)) or len(entry) != 2
                or not isinstance(entry[0], str) or not entry[0]
                or not isinstance(entry[1], (int, float))
                or isinstance(entry[1], bool)):
            raise ValueError(
                f"{where}.extra_unit_factors.{token!r}须为"
                f"[非空族名, 数值因子]二元组")
        factors[token] = (entry[0], float(entry[1]))
    field_ops_raw = pack.join_param("numeric_z3", "field_name_ops", {})
    if (not isinstance(field_ops_raw, dict) or not field_ops_raw
            or not all(isinstance(k, str) and k and isinstance(v, str)
                       and v in _OP_SYMBOLS
                       for k, v in field_ops_raw.items())):
        raise ValueError(
            f"{where}.field_name_ops须为非空{{字段名: le/lt/ge/gt/eq}}映射")
    markers_raw = pack.join_param("numeric_z3", "aggregate_markers", ())
    if (not isinstance(markers_raw, (list, tuple)) or not markers_raw
            or not all(isinstance(m, str) and m for m in markers_raw)):
        raise ValueError(f"{where}.aggregate_markers须为非空字符串列表")
    field_fact_re = re.compile(
        rf"(?P<subject>{_SUBJECT_TOKEN}?)的"
        rf"(?P<field>{'|'.join(field_ops_raw)})"
        r"(?:值)?(?:[是为：:、，,]?\s*)(?P<value>\d+(?:\.\d+)?)\s*"
        rf"(?P<unit>{_UNIT_TOKEN})?"
    )
    return _NumericConfig(
        cn_unit_aliases=dict(aliases_raw),
        extra_unit_factors=factors,
        field_name_ops=dict(field_ops_raw),
        aggregate_markers=tuple(markers_raw),
        field_fact_re=field_fact_re,
    )


_NUMERIC_CONFIG: _NumericConfig | None = None
_NUMERIC_PACK: RulePack | None = None


def _cfg() -> _NumericConfig:
    """惰性加载默认rule pack并编译数值词典（按pack身份缓存, import期零I/O）."""
    global _NUMERIC_CONFIG, _NUMERIC_PACK
    pack = default_rulepack()
    if _NUMERIC_CONFIG is None or _NUMERIC_PACK is not pack:
        _NUMERIC_PACK = pack
        _NUMERIC_CONFIG = _build_config(pack)
    return _NUMERIC_CONFIG


@lru_cache(maxsize=1)
def _unit_table() -> dict[str, tuple[str, float]]:
    """单位token→(族名, 到族基准的乘法因子)。srs_kb单位族资产+补充表。

    读取失败立即抛RuntimeError（不静默降级——单位族错误会污染所有数值
    判定），由_expert_channels的per-expert异常诊断上报。
    """
    table: dict[str, tuple[str, float]] = dict(_cfg().extra_unit_factors)
    try:
        kb = json.loads(_srs_kb_path().read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"srs_kb.json不可读（单位族资产缺失）: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"srs_kb.json解析失败: {exc}") from exc
    families = kb.get("unit_dictionary") if isinstance(kb, dict) else None
    if not isinstance(families, dict):
        raise RuntimeError("srs_kb.json缺少unit_dictionary单位族资产")
    for family, spec in families.items():
        if family == "temperature":
            # K/F→℃是仿射换算（K→℃=-272.15+x），乘法因子表不可表达
            continue
        conversions = spec.get("conversions", {}) if isinstance(spec, dict) else {}
        for token, factor in conversions.items():
            table.setdefault(str(token), (str(family), float(factor)))
    return table


@dataclass(frozen=True)
class UnitNorm:
    """数值归一化结果：族名 + 族基准值（如100ms→("time", 0.1)）。"""

    family: str
    canonical_value: float


def normalize_numeric(value: str, unit: str) -> UnitNorm | None:
    """(值, 单位token)→(族名, 族基准值)。

    无单位→count族；中文token走别名表；srs_kb族换算到族基准；未知单位
    →"raw:{token}"同名退化族（仅同串可比）。值不可解析返回None。
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    token = str(unit).strip()
    if not token:
        return UnitNorm("count", number)
    token = _cfg().cn_unit_aliases.get(token, token)
    entry = _unit_table().get(token)
    if entry is None:
        return UnitNorm(f"raw:{token}", number)
    family, factor = entry
    return UnitNorm(family, number * factor)


@dataclass(frozen=True)
class NumericFact:
    """证据侧一条数值约束（值已换算到族基准，含语句级定位）。

    field_class标记事实的量纲类型：字段式事实携带来源字段类
    （max/min/precision），算子式事实为""（数据项值本身的约束）。
    """

    subject: str
    op: str            # 规范算子: le/lt/ge/gt/eq
    value: float       # 族基准值
    raw_value: str
    unit: str          # 原始单位token
    family: str
    evidence_id: str
    statement_id: str
    field_class: str = ""

    def describe(self) -> str:
        symbol = _OP_SYMBOLS.get(self.op, self.op)
        return f"{self.subject}{symbol}{self.raw_value}{self.unit}"


@dataclass(frozen=True)
class NumericClaim:
    """answer侧一条数值断言：(subject, op, value, unit) + claim_text。

    core_subject/field_class是主体量纲解析结果："最大连接数的最大值"
    →core_subject="最大连接数"、field_class="max"；无限定词时
    core_subject=subject、field_class=""（声明数据项值本身）。
    subject保持完整形态供claim_text构造与per-claim融合。
    """

    subject: str
    op: str            # 规范算子
    value: str
    unit: str
    claim_text: str
    aggregate: bool
    core_subject: str = ""
    field_class: str = ""


def _norm_subject(raw: str) -> str:
    """主体规范化：折叠空白、去首尾分隔标点。"""
    return re.sub(r"\s+", "", raw or "").strip("：:，,。；;、").strip()


def _split_field_qualifier(subject: str) -> tuple[str, str]:
    """answer声明主体→(核心主体, 字段类)：剥离尾部字段限定词。

    "最大连接数的最大值"→("最大连接数", "max")；"响应时间"→
    ("响应时间", "")。核心主体不足2字符时不剥离（整个主体即限定词，
    无从定位数据项）。字段类参与区间join匹配（见_FIELD_CLASS）。
    """
    for pattern, field_class in _CLAIM_FIELD_QUALIFIERS:
        match = pattern.search(subject)
        if match is None:
            continue
        core = subject[:match.start()]
        if len(core) >= 2:
            return core, field_class
    return subject, ""


def _append_fact(facts: list[NumericFact], statement: EvidenceStatement,
                 subject: str, op: str, value: str, unit: str,
                 unit_decls: dict[str, str],
                 field_class: str = "") -> None:
    subject = _norm_subject(subject)
    if not subject:
        return
    if not unit:
        unit = unit_decls.get(subject, "")
    norm = normalize_numeric(value, unit)
    if norm is None:
        return
    facts.append(NumericFact(
        subject=subject, op=op, value=norm.canonical_value, raw_value=value,
        unit=unit, family=norm.family, evidence_id=statement.evidence_id,
        statement_id=statement.statement_id, field_class=field_class))


def extract_numeric_facts(
        statements: list[EvidenceStatement]) -> list[NumericFact]:
    """从线性化证据语句抽取数值事实（确定性，无模型调用）。

    两个来源：①字段式——数据表语句"X的最大差：100ms"与正文同形句
    （field_fact_re，subject缺省取scope_key）；②算子式——"X不超过
    N{单位}"（复用qa_module._extract_numeric_claims，冒号删除以覆盖
    表格cell"内存：不小于16GB"形态——冒号换逗号会产生空分段抹掉
    subject，attr缺省取scope_key）。"X的单位：ms"语句先行收集，作为
    同主体缺单位事实的族消解依据。无subject的事实丢弃（无从与answer
    声明join）。
    """
    unit_decls: dict[str, str] = {}
    for statement in statements:
        for match in _UNIT_DECL_RE.finditer(statement.text):
            subject = _norm_subject(match.group("subject"))
            if subject:
                unit_decls[subject] = match.group("unit")
    facts: list[NumericFact] = []
    for statement in statements:
        compact = re.sub(r"\s+", "", statement.text)
        for match in _cfg().field_fact_re.finditer(compact):
            field = match.group("field")
            subject = match.group("subject") or statement.scope_key
            _append_fact(facts, statement, subject,
                         _cfg().field_name_ops[field],
                         match.group("value"), match.group("unit") or "",
                         unit_decls, _FIELD_CLASS.get(field, ""))
        colon_free = re.sub(r"[：:]", "", statement.text)
        for attr, operator, value, unit in _extract_numeric_claims(
                colon_free):
            op = normalize_op(operator)
            if op is None:
                continue
            subject = attr or statement.scope_key
            _append_fact(facts, statement, subject, op, value, unit,
                         unit_decls)
    return facts


def extract_numeric_claims(answer: str,
                           question: str = "") -> list[NumericClaim]:
    """answer数值断言抽取（复用qa_module的_NUMERIC_PREFIX风格）。

    "X不超过N{单位}"/"X至少N"/"X为N"→(subject, op, value, unit)；attr
    缺省回落question主体（与qa_module._decompose同构）。claim_text构造
    为"{subject} {op}{value}{unit}"，与数值通道同claim_text，使per-claim
    融合能仲裁两通道对同一声明的分歧。subject命中聚合标记→aggregate。
    """
    text = re.sub(r"[：:]", "", answer)
    claims: list[NumericClaim] = []
    seen: set[tuple[str, str, str, str]] = set()
    for attr, operator, value, unit in _extract_numeric_claims(text):
        subject = _norm_subject(
            attr or question_numeric_subject(question))
        if not subject:
            continue
        op = normalize_op(operator)
        if op is None:
            continue
        key = (subject, op, value, unit)
        if key in seen:
            continue
        seen.add(key)
        aggregate = any(marker in subject for marker in _cfg().aggregate_markers)
        core_subject, field_class = _split_field_qualifier(subject)
        claims.append(NumericClaim(
            subject=subject, op=op, value=value, unit=unit,
            claim_text=f"{subject} {operator}{value}{unit}",
            aggregate=aggregate, core_subject=core_subject,
            field_class=field_class))
    return claims


@dataclass(frozen=True)
class Z3Run:
    """一次Z3求解的完整透传结果（status/unsat core/SMT-LIB/诊断）。"""

    status: str        # "unsat" / "sat" / "unknown" / "error"
    core: tuple[str, ...]
    smt2: str
    diagnostic: str = ""


def _z3_solve(named: list[tuple[str, object]]) -> Z3Run:
    """求解命名约束集（assert_and_track→unsat core可溯源）。"""
    solver = Solver()
    solver.set("timeout", Z3_TIMEOUT_MS)
    for name, constraint in named:
        solver.assert_and_track(constraint, name)
    try:
        outcome = solver.check()
    except Z3Exception as exc:
        return Z3Run("error", (), "", f"z3求解异常: {exc}")
    try:
        smt2 = solver.to_smt2()
    except Z3Exception as exc:
        return Z3Run("error", (), "", f"SMT-LIB序列化异常: {exc}")
    if outcome == unsat:
        return Z3Run("unsat", tuple(str(item) for item in solver.unsat_core()),
                     smt2)
    if outcome == sat:
        return Z3Run("sat", (), smt2)
    return Z3Run("unknown", (), smt2, f"z3未决: {solver.reason_unknown()}")


def _z3_op(var, op: str, value: float):
    """规范算子→Z3算术约束（值经RealVal十进制精确有理化）。"""
    if op == "le":
        return var <= RealVal(value)
    if op == "lt":
        return var < RealVal(value)
    if op == "ge":
        return var >= RealVal(value)
    if op == "gt":
        return var > RealVal(value)
    if op == "eq":
        return var == RealVal(value)
    raise ValueError(f"未知规范算子: {op}")


def _three_way(ev_named: list[tuple[str, object]],
               target_name: str, target_constraint,
               ) -> tuple[str, Z3Run, str]:
    """E∪C三态判定：返回(verdict, 决定性求解结果, 细节说明)。

    判定序：E自身UNSAT→NIE(context内部矛盾)；E∧C UNSAT→refute；
    C∧¬E UNSAT→support（answer解集⊆证据解集）；其余→NIE（部分重叠）。
    求解unknown/error→NIE（诊断进rationale，不静默）。
    """
    ev_run = _z3_solve(ev_named)
    if ev_run.status == "unsat":
        return "not_in_evidence", ev_run, "证据数值约束自身UNSAT(context内部数值矛盾)"
    if ev_run.status != "sat":
        return "not_in_evidence", ev_run, f"证据约束求解失败: {ev_run.diagnostic}"
    both_run = _z3_solve(ev_named + [(target_name, target_constraint)])
    if both_run.status == "unsat":
        return "refute", both_run, "answer约束与证据约束合取UNSAT(无交集)"
    if both_run.status != "sat":
        return "not_in_evidence", both_run, f"合取求解失败: {both_run.diagnostic}"
    neg_ev = Not(And(*[constraint for _, constraint in ev_named]))
    subset_run = _z3_solve([(target_name, target_constraint),
                            ("neg_ev", neg_ev)])
    if subset_run.status == "unsat":
        return "support", subset_run, "answer约束解集⊆证据约束解集(C∧¬E UNSAT)"
    if subset_run.status != "sat":
        return "not_in_evidence", subset_run, f"蕴含检查求解失败: {subset_run.diagnostic}"
    return "not_in_evidence", both_run, "answer约束与证据约束可满足但互不蕴含(部分重叠)"


def _core_text(run: Z3Run, desc_map: dict[str, str]) -> str:
    parts = [f"{name}({desc_map.get(name, name)})" for name in run.core]
    return "; ".join(parts)


def _claim_result(request: QAInput, suffix: str, claim: NumericClaim,
                  verdict: str, check_items: tuple[str, ...],
                  refs: tuple[str, ...], rationale: str,
                  confidence: float) -> ClaimResult:
    return ClaimResult(
        claim_id=f"{request.instance_id}-numz3{suffix}",
        claim_text=claim.claim_text,
        verdict=verdict,
        check_item_candidates=check_items,
        evidence_refs=refs,
        rationale=rationale,
        method=METHOD,
        confidence=confidence,
    )


def _field_class_compatible(claim_class: str, fact: NumericFact) -> bool:
    """字段类兼容判定：answer声明的量纲 vs 证据事实的量纲。

    - 证据precision是独立量纲（小数位数），只与"X的精度"式声明同类；
      幅度声明与精度事实误join会产生伪refute（C06QA-008：eq200与
      "精度：1"行池进同一Z3变量撞UNSAT）；
    - 无限定声明（值本身）与max/min/算子式事实同类——三者都是对
      数据项值幅度的约束（x≤max、x≥min），可池进同一变量；
    - 带限定的声明（max/min）只与同字段类事实或同向算子式事实比对：
      "X的最大值"与"X的最小值"是同数据项的两个不同量。
    """
    if fact.field_class == "precision":
        return claim_class == "precision"
    if claim_class == "precision":
        return False
    if claim_class == "":
        return True
    if claim_class == "max":
        return fact.field_class == "max" or (
            fact.field_class == "" and fact.op in ("le", "lt"))
    return fact.field_class == "min" or (
        fact.field_class == "" and fact.op in ("ge", "gt"))


def _verify_interval_claim(request: QAInput, claim: NumericClaim,
                           facts: list[NumericFact], index: int,
                           ) -> ClaimResult | None:
    """单参数区间检查：answer约束 vs 同subject同族同类证据约束。"""
    answer_norm = normalize_numeric(claim.value, claim.unit)
    if answer_norm is None:
        return None
    core_subject = claim.core_subject or claim.subject
    matched = [
        fact for fact in facts
        if fact.family == answer_norm.family
        and fact.op in _OP_SYMBOLS
        and _field_class_compatible(claim.field_class, fact)
        and same_subject(core_subject, fact.subject, request.question)
    ]
    if not matched:
        return None
    var = Real(f"x{index}")
    ev_named: list[tuple[str, object]] = []
    desc_map: dict[str, str] = {}
    for i, fact in enumerate(matched):
        name = f"ev{i}"
        ev_named.append((name, _z3_op(var, fact.op, fact.value)))
        desc_map[name] = fact.describe()
    symbol = _OP_SYMBOLS.get(claim.op, claim.op)
    answer_desc = f"{claim.subject}{symbol}{claim.value}{claim.unit}"
    desc_map["ans"] = answer_desc
    constraint_text = "约束：" + "；".join(
        [f"ans({answer_desc})"] + [f"ev{i}({fact.describe()})"
                                   for i, fact in enumerate(matched)])
    verdict, run, detail = _three_way(ev_named, "ans",
                                      _z3_op(var, claim.op,
                                             answer_norm.canonical_value))
    refs = tuple(dict.fromkeys(fact.evidence_id for fact in matched))
    provenance = f"[z3 {get_version_string()} timeout={Z3_TIMEOUT_MS}ms]"
    if verdict == "refute":
        rationale = (f"{provenance}Z3区间refute：{detail}；{constraint_text}；"
                     f"unsat core：{_core_text(run, desc_map)}；"
                     f"SMT-LIB：{run.smt2}")
        confidence = 1.0
    elif verdict == "support":
        rationale = (f"{provenance}Z3区间support：{detail}；{constraint_text}")
        confidence = 0.9
    elif run.status == "unsat":
        rationale = (f"{provenance}Z3区间NIE：{detail}，不仲裁answer；"
                     f"{constraint_text}；unsat core：{_core_text(run, desc_map)}；"
                     f"SMT-LIB：{run.smt2}")
        confidence = 0.0
    elif run.status != "sat":
        rationale = (f"{provenance}Z3求解失败→NIE（不静默）：{run.diagnostic}；"
                     f"{constraint_text}")
        confidence = 0.0
    else:
        rationale = f"{provenance}Z3区间NIE：{detail}；{constraint_text}"
        confidence = 0.0
    return _claim_result(request, f"{index:02d}", claim, verdict,
                         CHECK_ITEMS_INTERVAL, refs, rationale, confidence)


def _is_aggregate_subject(subject: str) -> bool:
    return any(marker in subject for marker in _cfg().aggregate_markers)


def _verify_aggregate_claim(request: QAInput, claim: NumericClaim,
                            facts: list[NumericFact], index: int,
                            ) -> ClaimResult | None:
    """跨参数聚合检查：Σ(分量约束) vs answer聚合约束（PARAM-01/05）。

    分量=同单位族、非聚合subject、与聚合subject不同主体的互异subject
    数值事实（<2个分量不触发，防止把单点事实误当聚合）。三态判定方向
    与区间检查不同：聚合声明是"总和满足约束"的事实断言，support取
    分量蕴含方向（E∧¬C UNSAT→分量值保证聚合成立），refute取合取
    无交方向（E∧C UNSAT→分量约束使聚合不可能成立），unsat core指明
    参与矛盾的分量与聚合约束。
    """
    agg_norm = normalize_numeric(claim.value, claim.unit)
    if agg_norm is None:
        return None
    core_subject = claim.core_subject or claim.subject
    groups: dict[str, list[NumericFact]] = {}
    for fact in facts:
        if fact.family != agg_norm.family or fact.op not in _OP_SYMBOLS:
            continue
        if _is_aggregate_subject(fact.subject):
            continue
        if same_subject(
                core_subject, fact.subject, request.question):
            continue
        groups.setdefault(_norm_subject(fact.subject), []).append(fact)
    if len(groups) < 2:
        return None
    comp_named: list[tuple[str, object]] = []
    comp_vars = []
    desc_map: dict[str, str] = {}
    for gi, (_, group) in enumerate(groups.items()):
        var = Real(f"aggv{index}_{gi}")
        comp_vars.append(var)
        for fi, fact in enumerate(group):
            name = f"comp{gi}_{fi}"
            comp_named.append((name, _z3_op(var, fact.op, fact.value)))
            desc_map[name] = fact.describe()
    total = Sum(*comp_vars)
    agg_constraint = _z3_op(total, claim.op, agg_norm.canonical_value)
    symbol = _OP_SYMBOLS.get(claim.op, claim.op)
    agg_desc = f"{claim.subject}{symbol}{claim.value}{claim.unit}"
    desc_map["agg"] = f"Σ({agg_desc})"
    comp_text = "分量：" + "；".join(
        f"{name}({desc_map[name]})" for name, _ in comp_named)
    comp_run = _z3_solve(comp_named)
    if comp_run.status == "unsat":
        verdict, run, detail = ("not_in_evidence", comp_run,
                                "分量数值约束自身UNSAT(context内部数值矛盾)")
    elif comp_run.status != "sat":
        verdict, run, detail = ("not_in_evidence", comp_run,
                                f"分量约束求解失败: {comp_run.diagnostic}")
    else:
        both_run = _z3_solve(comp_named + [("agg", agg_constraint)])
        if both_run.status == "unsat":
            verdict, run, detail = ("refute", both_run,
                                    "分量约束与聚合约束合取UNSAT(总和不可能满足)")
        elif both_run.status != "sat":
            verdict, run, detail = ("not_in_evidence", both_run,
                                    f"合取求解失败: {both_run.diagnostic}")
        else:
            entail_run = _z3_solve(comp_named + [("neg_agg",
                                                  Not(agg_constraint))])
            if entail_run.status == "unsat":
                verdict, run, detail = ("support", entail_run,
                                        "分量约束蕴含聚合约束(E∧¬C UNSAT)")
            elif entail_run.status != "sat":
                verdict, run, detail = ("not_in_evidence", entail_run,
                                        f"蕴含检查求解失败: "
                                        f"{entail_run.diagnostic}")
            else:
                verdict, run, detail = ("not_in_evidence", both_run,
                                        "分量约束与聚合约束可满足但互不蕴含"
                                        "(部分重叠)")
    refs = tuple(dict.fromkeys(
        fact.evidence_id for group in groups.values() for fact in group))
    provenance = f"[z3 {get_version_string()} timeout={Z3_TIMEOUT_MS}ms]"
    if verdict == "refute":
        rationale = (f"{provenance}Z3聚合refute：{detail}；{comp_text}；"
                     f"agg({agg_desc})；unsat core：{_core_text(run, desc_map)}；"
                     f"SMT-LIB：{run.smt2}")
        confidence = 1.0
    elif verdict == "support":
        rationale = (f"{provenance}Z3聚合support：{detail}；{comp_text}；"
                     f"agg({agg_desc})")
        confidence = 0.9
    elif run.status == "unsat":
        rationale = (f"{provenance}Z3聚合NIE：{detail}，不仲裁answer；{comp_text}；"
                     f"unsat core：{_core_text(run, desc_map)}；"
                     f"SMT-LIB：{run.smt2}")
        confidence = 0.0
    elif run.status != "sat":
        rationale = (f"{provenance}Z3求解失败→NIE（不静默）：{run.diagnostic}；"
                     f"{comp_text}")
        confidence = 0.0
    else:
        rationale = f"{provenance}Z3聚合NIE：{detail}；{comp_text}；agg({agg_desc})"
        confidence = 0.0
    return _claim_result(request, f"agg{index:02d}", claim, verdict,
                         CHECK_ITEMS_AGGREGATE, refs, rationale, confidence)


def verify_numeric_constraints(
        request: QAInput,
        statements: list[EvidenceStatement]) -> list[ClaimResult]:
    """对冻结QA输入执行Z3数值约束检查（L1确定性专家通道入口）。

    answer无数值断言或证据无数值事实时返回[]（低触发，不产生噪音）；
    聚合声明同时跑聚合检查与（若证据有同主体事实的）区间检查，同
    claim_text的结果由per-claim融合仲裁。

    z3未安装时raise ImportError——由qa_module的per-expert异常诊断
    上报为expert_numeric_z3_failed(其余专家照常运行, 不静默).
    """
    if Solver is None:
        raise ImportError(
            "z3-solver未安装, numeric_z3专家不可用: "
            "pip install z3-solver (见README惰性依赖触发条件)")
    facts = extract_numeric_facts(statements)
    if not facts:
        return []
    claims = extract_numeric_claims(request.answer, request.question)
    results: list[ClaimResult] = []
    for index, claim in enumerate(claims, start=1):
        if claim.aggregate:
            aggregate = _verify_aggregate_claim(request, claim, facts, index)
            if aggregate is not None:
                results.append(aggregate)
        interval = _verify_interval_claim(request, claim, facts, index)
        if interval is not None:
            results.append(interval)
    return results


__all__ = [
    "METHOD",
    "CHECK_ITEMS_AGGREGATE",
    "CHECK_ITEMS_INTERVAL",
    "Z3_TIMEOUT_MS",
    "NumericClaim",
    "NumericFact",
    "UnitNorm",
    "Z3Run",
    "extract_numeric_claims",
    "extract_numeric_facts",
    "normalize_numeric",
    "verify_numeric_constraints",
]
