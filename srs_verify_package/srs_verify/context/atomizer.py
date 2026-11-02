"""证据原子化与确定性配对(S1 blocking).

对应文档: docs/srs_project/63(E-Atom schema) / 64(信号独立) / 65(实证) / 66(FS形式化).
勘验对应: Atom=检材最小检定单元; 分槽比对=分项检验; blocking=初筛排嫌疑(廉价高召回).
设计: 纯函数+冻结数据类; 词典/语料由调用方注入(模块顶层零I/O).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

# 操作符规范化(匹配时长词优先; 顺序无关, 使用前按长度排序)
OPERATOR_PATTERNS: tuple[tuple[str, str], ...] = (
    ("大于等于", "≥"), ("小于等于", "≤"),
    ("不小于", "≥"), ("不低于", "≥"), ("不大于", "≤"), ("不超过", "≤"),
    ("不高于", "≤"), ("大于", ">"), ("超过", ">"), ("高于", ">"),
    ("小于", "<"), ("低于", "<"), ("至少", "≥"), ("最少", "≥"),
    ("至多", "≤"), ("最多", "≤"), ("以上", "≥"), ("以内", "≤"),
    ("之内", "≤"), ("等于", "="), ("为", "="),
    ("≥", "≥"), ("≤", "≤"), (">", ">"), ("<", "<"), ("=", "="),
)
_OPERATORS_BY_LEN: tuple[tuple[str, str], ...] = tuple(
    sorted(OPERATOR_PATTERNS, key=lambda kv: -len(kv[0])))

# 单位族: 族内换算到基单位(time→ms, storage→KB, frequency→MHz, ...)
UNIT_FAMILIES: dict[str, dict[str, float]] = {
    "time": {"ms": 1.0, "毫秒": 1.0, "msec": 1.0,
             "s": 1e3, "秒": 1e3, "sec": 1e3,
             "us": 1e-3, "微秒": 1e-3,
             "min": 6e4, "分钟": 6e4,
             "h": 3.6e6, "小时": 3.6e6},
    "storage": {"kb": 1.0, "b": 1.0 / 1024, "字节": 1.0 / 1024,
                "mb": 1024.0, "gb": 1024.0 ** 2, "tb": 1024.0 ** 3},
    "frequency": {"mhz": 1.0, "khz": 1e-3, "ghz": 1e3, "hz": 1e-6},
    "percentage": {"%": 1.0},
    "data_rate": {"mbps": 1.0, "kbps": 1e-3, "gbps": 1e3, "bps": 1e-6},
}

# 作用域线索的截断字符(标点/连接词/介词)
_SCOPE_STOP = set("，。；、：:|（）()\n\r 　\t的和与及为对在按其该")

# 数值与参数表面形式的最大距离(字符): 超过视为无关数值
_PROXIMITY_WINDOW = 40
# 无操作符时, 参数与数值之间以表/图/见结尾=引用编号而非取值
_REFERENCE_TAIL = re.compile(r"[表图见]$")


@dataclass(frozen=True)
class Atom:
    """四槽证据原子: (参数, 操作符, 数值, 单位) + 作用域线索.

    65号实证: scope为精度瓶颈; v1仅产出scope_hint(近邻修饰词),
    binding_status恒为"unbound", 绑定由S2/S3/L3级联完成.
    """

    param: str          # canonical参数名(response_time等)
    param_surface: str  # 文中命中的表面形式
    operator: str       # 规范化: ≥/≤/>/</=/""(未检出)
    value: float
    unit: str           # 原始单位(小写, ""=缺失)
    scope_hint: str     # 参数前的近邻修饰词(作用域线索, 可为空)
    binding_status: str
    claim_id: str
    doc_id: str
    section: str
    context: str        # 原文截断(可审计回溯)

    @property
    def quantity_hygiene(self) -> str:
        """数值卫生(65号: 原始槽95.5%为编号噪声, 距离过滤后残余无单位者标记)."""
        return "no_unit" if not self.unit else "unit_ok"


def find_param_occurrences(
        text: str, surface_map: Mapping[str, str]) -> list[tuple[str, str, int]]:
    """文本中全部参数表面形式命中(重叠时长表面优先)."""
    hits: list[tuple[str, str, int]] = []
    for surface, param in surface_map.items():
        if not surface:
            continue
        start = 0
        while True:
            pos = text.find(surface, start)
            if pos < 0:
                break
            hits.append((param, surface, pos))
            start = pos + len(surface)
    hits.sort(key=lambda h: (h[2], -len(h[1])))
    chosen: list[tuple[str, str, int]] = []
    last_end = -1
    for param, surface, pos in hits:
        if pos >= last_end:
            chosen.append((param, surface, pos))
            last_end = pos + len(surface)
    return chosen


# 表格行claim的行首模式: 可选行号+管道符(如"1 | 轻量化服务器 | ...")
_TABLE_ROW_HEAD = re.compile(r"^\s*(\d+\s*)?\|")


def _scope_hint(text: str, pos: int, max_len: int = 4) -> str:
    """作用域线索: 参数表面形式之前的近邻修饰词.

    65号实证修正: 表格行claim(管道符开头, 可带行号)的真正作用域是
    行首设备/条目单元格(如"轻量化服务器"), 局部窗口只能抓到参数复合词
    (如"CPU主频")导致配置档位表假阳性 — 故表格行走行首单元格.
    """
    if _TABLE_ROW_HEAD.match(text):
        cells = [c.strip() for c in text.split("|")
                 if c.strip() and not c.strip().isdigit()]
        # 仅当行内有≥2个实质单元格时, 首格才是行头标签(设备/条目名);
        # 单元格行(|  | 支持首屏...=续行/转写)无行头, 走局部窗口.
        if len(cells) >= 2:
            return cells[0][:12]
    chars: list[str] = []
    i = pos - 1
    while i >= 0 and len(chars) < max_len and text[i] not in _SCOPE_STOP:
        chars.append(text[i])
        i -= 1
    return "".join(reversed(chars))


def _normalize_operator(op_raw: str) -> str:
    """claim自带的operator_raw槽规范化(长词优先)."""
    op_raw = str(op_raw or "").strip()
    if not op_raw:
        return ""
    for pat, op in _OPERATORS_BY_LEN:
        if pat in op_raw:
            return op
    return ""


def _quantity_positions(
        text: str,
        quantities: Sequence[Mapping]) -> list[tuple[float, str, int, str]]:
    """数值槽定位: raw串在文中的位置(跨度不重叠, 按槽序分配).

    注: 真实语料的raw可含操作符与单位(如"不小于2秒"), 故同时携带
    operator_raw供规范化兜底.
    """
    out: list[tuple[float, str, int, str]] = []
    spans: list[tuple[int, int]] = []
    for q in quantities:
        raw = str(q.get("raw", "")).strip()
        value = q.get("value")
        if value is None or not raw:
            continue
        pos = -1
        start = 0
        while True:
            cand = text.find(raw, start)
            if cand < 0:
                break
            if all(not (cand < e and s < cand + len(raw))
                   for s, e in spans):
                pos = cand
                break
            start = cand + 1
        if pos < 0:
            continue
        spans.append((pos, pos + len(raw)))
        unit = str(q.get("unit_raw", "") or "").strip().lower()
        op_raw = str(q.get("operator_raw", "") or "")
        out.append((float(value), unit, pos, op_raw))
    return out


def _operator_between(text: str, start: int, end: int) -> str:
    """在参数表面形式与数值之间的文本段内识别操作符(长词优先)."""
    seg = text[start:end]
    for pat, op in _OPERATORS_BY_LEN:
        if pat in seg:
            return op
    return ""


def _atom_quality(a: Atom) -> tuple[int, int]:
    """原子槽位质量: (有操作符, 有单位) — 同claim同参数去重时优先保留."""
    return (1 if a.operator else 0, 1 if a.unit else 0)


def atomize_claim(claim: Mapping, surface_map: Mapping[str, str],
                  context_limit: int = 120) -> list[Atom]:
    """单条claim→原子列表.

    规则(全部确定性, 65号S1a/S1c):
      1. 参数表面形式命中(长表面优先, 去重叠);
      2. 数值就近附着: 参数后_PROXIMITY_WINDOW内最近的数值(行号因在前/过远被天然排除);
      3. 引用排除: 无操作符且间隔文本以"表/图/见"结尾=编号引用, 非取值;
      4. 作用域线索: 参数前近邻修饰词(如"用户"响应时间);
      5. 同claim同参数只保留槽位最完整的原子(排除"10吋"类弱命中吸附).
    """
    text = str(claim.get("raw_text", ""))
    if not text:
        return []
    features = claim.get("features", {})
    quants = _quantity_positions(
        text, features.get("quantities", []) if isinstance(features, Mapping) else [])
    atoms: list[Atom] = []
    for param, surface, pos in find_param_occurrences(text, surface_map):
        best: tuple[float, str, int, str] | None = None
        for value, unit, qpos, op_raw in quants:
            if qpos <= pos or qpos - pos > _PROXIMITY_WINDOW:
                continue
            if best is None or qpos - pos < best[2] - pos:
                best = (value, unit, qpos, op_raw)
        if best is None:
            continue
        between = text[pos + len(surface): best[2]]
        op = _operator_between(text, pos + len(surface), best[2])
        if not op:
            # 数值槽自带operator_raw(如raw="不小于2秒"时between为空)
            op = _normalize_operator(best[3])
        if not op and _REFERENCE_TAIL.search(between.strip().replace(" ", "")):
            continue
        atoms.append(Atom(
            param=param, param_surface=surface, operator=op,
            value=best[0], unit=best[1],
            scope_hint=_scope_hint(text, pos),
            binding_status="unbound",
            claim_id=str(claim.get("claim_id", "")),
            doc_id=str(claim.get("doc_id", "")),
            section=str(claim.get("section", "")),
            context=text[:context_limit],
        ))
    # 同claim同参数去重: 保留槽位质量最高的首个原子
    by_param: dict[str, Atom] = {}
    for a in atoms:
        keep = by_param.get(a.param)
        if keep is None or _atom_quality(a) > _atom_quality(keep):
            by_param[a.param] = a
    return [by_param[p] for p in sorted(by_param)]


def block_by_param(atoms: Iterable[Atom]) -> dict[tuple[str, str], list[Atom]]:
    """S1 blocking: 按(文档, 参数)分组 — 同文档内同参原子才可能构成可比对象."""
    groups: dict[tuple[str, str], list[Atom]] = {}
    for a in atoms:
        groups.setdefault((a.doc_id, a.param), []).append(a)
    return groups


def _base_value(atom: Atom) -> tuple[str | None, float | None]:
    """数值换算到族基单位; 无单位/未知单位返回(None, None)."""
    for fam, table in UNIT_FAMILIES.items():
        if atom.unit in table:
            return fam, atom.value * table[atom.unit]
    return None, None


@dataclass(frozen=True)
class AtomPair:
    """一对同参原子 + 比较向量γ的决策(66号3.2节三支规则的确定性部分)."""

    left: Atom
    right: Atom
    decision: str      # redundant/conflict_same_scope/conflict_scope_diff/
                       # conflict_scope_unknown/unit_mismatch
    gap: float | None  # 族基单位差(不可比时None)
    same_section: bool


def compare_atoms(left: Atom, right: Atom) -> AtomPair:
    """两原子比较: 值一致→冗余; 值异→冲突候选(按作用域线索分级); 异单位→不可比."""
    fam_l, vl = _base_value(left)
    fam_r, vr = _base_value(right)
    if fam_l is not None and fam_l == fam_r and vl is not None and vr is not None:
        comparable, gap = True, abs(vl - vr)
    else:
        comparable, gap = left.unit == right.unit, (
            abs(left.value - right.value) if left.unit == right.unit else None)
    if not comparable:
        decision = "unit_mismatch"
    elif gap == 0.0:
        decision = "redundant"
    elif left.scope_hint and left.scope_hint == right.scope_hint:
        decision = "conflict_same_scope"
    elif left.scope_hint and right.scope_hint:
        decision = "conflict_scope_diff"
    else:
        decision = "conflict_scope_unknown"
    return AtomPair(left=left, right=right, decision=decision, gap=gap,
                    same_section=left.section == right.section)


def pair_groups(groups: Mapping[tuple[str, str], Sequence[Atom]]) -> list[AtomPair]:
    """组内全配对(同文档同参数, 冗余对保留供去重, 冲突对供级联确认)."""
    pairs: list[AtomPair] = []
    for key in sorted(groups):
        atoms = list(groups[key])
        for i in range(len(atoms)):
            for j in range(i + 1, len(atoms)):
                pairs.append(compare_atoms(atoms[i], atoms[j]))
    return pairs
