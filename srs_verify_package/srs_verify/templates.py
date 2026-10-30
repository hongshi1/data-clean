r"""K2 声明模板库: SRS需求文本→结构化声明的正式模板注册表.

设计:
  - 每个模板 = ClaimTemplate(名称, 声明类型, 编译正则, 槽位, 规则溯源, 说明)
  - parse_claims(text) → list[Claim]: 按模板优先级解析为结构化声明
  - 规则溯源: GJB规则族编号 / synth表面模板(T1/T2/T3) / 领域约定
  - 与checker行为严格一致(正则原样迁移, 消费方重构后须通过全量回归)

模板来源:
  - 数值声明(前缀/后缀): synth T1/T2/T3表面 + 语料数值约束形态
  - 引号声明: 跨模态引用格式(表格/图引用「X」)
  - 枚举列表: 功能表条目列举格式
  - 编号条目: 功能表编号行(\d、), 防误触排除表号/章节号
  - 计数声明: 条目计数(N项) → GJB条目一致性规则族
  - 文档缺失声明: 条款完整性 → GJB文档构成规则族
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClaimTemplate:
    name: str
    claim_type: str  # numeric / quoted / enum / numbered / count / absence
    pattern: re.Pattern
    slots: tuple[str, ...]
    rule_ref: str
    description: str


@dataclass
class Claim:
    template: str
    claim_type: str
    slots: dict[str, str] = field(default_factory=dict)
    rule_ref: str = ""
    text: str = ""

    def __repr__(self) -> str:  # 便于调试
        return f"Claim({self.claim_type}, {self.slots})"


# ═══ 单位token: 已知单位(长优先) + 通用fallback(复合单位如字/秒) ═══
UNIT_FAMILIES = {
    "time": {"ms": 1.0, "毫秒": 1.0, "s": 1000.0, "秒": 1000.0,
             "min": 60000.0, "分钟": 60000.0, "h": 3600000.0, "小时": 3600000.0,
             "天": 86400000.0, "日": 86400000.0},
    "storage": {"B": 1.0, "字节": 1.0, "KB": 1024.0, "K": 1024.0,
                "MB": 1048576.0, "M": 1048576.0, "GB": 1073741824.0, "G": 1073741824.0,
                "TB": 1099511627776.0, "T": 1099511627776.0},
    "count": {"种": 1.0, "个": 1.0, "路": 1.0, "条": 1.0, "次": 1.0,
              "项": 1.0, "类": 1.0, "台": 1.0, "用户": 1.0, "节点": 1.0},
    "percent": {"%": 1.0},
}
UNIT_TO_FAMILY = {u: (fam, fac) for fam, us in UNIT_FAMILIES.items() for u, fac in us.items()}

# 算子族: 同族操作符语义等价(领域等价约定)
OP_FAMILIES = {
    "le": {"不大于", "不超过", "不高于", "小于等于", "≤", "以下", "最多", "至多"},
    "ge": {"不小于", "不少于", "不低于", "大于等于", "≥", "以上", "至少", "最低"},
    "eq": {"为", "等于", "=", "是"},
    "gt": {"大于", "超过", ">"},
    "lt": {"小于", "<"},
}

_KNOWN_UNIT_ALT = "|".join(re.escape(u) for u in sorted(UNIT_TO_FAMILY, key=len, reverse=True))
UNIT_TOKEN = rf"(?:{_KNOWN_UNIT_ALT}|[A-Za-z%／/\u4e00-\u9fa5]{{1,4}})"

# ═══ 模板注册表(与checker行为严格一致) ═══
TEMPLATES: list[ClaimTemplate] = [
    ClaimTemplate(
        name="numeric_prefix",
        claim_type="numeric",
        pattern=re.compile(
            r"(不大于|不超过|不高于|不小于|不少于|不低于|大于等于|小于等于|大于|小于|至少|最多|为|等于|≤|≥|至多|最低|=|＞|＜)"
            rf"\s*(\d+\.?\d*)\s*({UNIT_TOKEN})?"),
        slots=("op", "value", "unit"),
        rule_ref="synth-T1/T2/T3数值表面",
        description="前缀式数值声明: 不超过500ms / ≥19种 / 为120px"),
    ClaimTemplate(
        name="numeric_postfix",
        claim_type="numeric",
        pattern=re.compile(
            rf"(\d+\.?\d*)\s*({UNIT_TOKEN})"
            r"(及以上|以上|及以下|以下|含)"),
        slots=("value", "unit", "postfix"),
        rule_ref="synth-T1/T2/T3数值表面",
        description="后缀式数值声明: 200G以上 / 500ms以下"),
    ClaimTemplate(
        name="quoted",
        claim_type="quoted",
        pattern=re.compile(r"[「]([^「」]+)[」]"),
        slots=("content",),
        rule_ref="跨模态引用格式(表格↔图「X」)",
        description="引号声明: 表格/图引用的约束原文"),
    ClaimTemplate(
        name="enum_list",
        claim_type="enum",
        pattern=re.compile(
            r"(?:包括|包含|涉及)(?:以下|均|都)?(?:元素|功能|节点|内容)?[：:]?\s*"
            r"([^。；、]{2,60}(?:、[^。；、]{2,60})+)"),
        slots=("items",),
        rule_ref="功能表条目列举格式",
        description="枚举列表: 包括/包含/涉及 + 顿号列表"),
    ClaimTemplate(
        name="numbered_item",
        claim_type="numbered",
        pattern=re.compile(r"(?<![\d.表图节章第页卷])(\d{1,2})、"),
        slots=("num",),
        rule_ref="功能表编号行格式(防误触: 排除表号/章节号/小数)",
        description="编号条目锚点: 2、主达梦库同步异常"),
    ClaimTemplate(
        name="count_decl",
        claim_type="count",
        pattern=re.compile(r"(\d+)\s*项(?:条目|条|需求)?"),
        slots=("count",),
        rule_ref="GJB条目计数一致性规则族(GJB-02/09)",
        description="计数声明: 9项条目"),
    ClaimTemplate(
        name="doc_absence",
        claim_type="absence",
        pattern=re.compile(r"(?:缺失|未包含|未规定|没有)\s*(?:该|此)?\s*(?:条款|条目|需求|章节|表格|说明)"),
        slots=(),
        rule_ref="GJB条款完整性规则族(GJB-10)",
        description="文档级缺失声明: 文档3.15章节缺失该条款"),
]

_BY_NAME = {t.name: t for t in TEMPLATES}


def get_template(name: str) -> ClaimTemplate:
    return _BY_NAME[name]


def parse_claims(text: str) -> list[Claim]:
    """按注册表解析文本为结构化声明(K2入口).

    消费方按claim_type取用: numeric/quoted/enum/numbered/count/absence.
    """
    claims: list[Claim] = []
    for tpl in TEMPLATES:
        if tpl.claim_type == "numbered":
            continue  # 编号条目需位置感知, 由消费方专用
        for m in tpl.pattern.finditer(text):
            slots = dict(zip(tpl.slots, m.groups()))
            claims.append(Claim(template=tpl.name, claim_type=tpl.claim_type,
                                slots=slots, rule_ref=tpl.rule_ref, text=m.group()))
    return claims


def normalize_op(op: str) -> str | None:
    for fam, ops in OP_FAMILIES.items():
        if op in ops:
            return fam
    return None


def normalize_unit(val: str, unit: str) -> tuple[float, str] | None:
    """归一化到(族基准值, 族名); 未知单位以单位串为族名(同串可比)."""
    try:
        v = float(val)
    except (ValueError, TypeError):
        return None
    u = str(unit).strip()
    if not u:
        return v, "count"
    if u in UNIT_TO_FAMILY:
        fam, fac = UNIT_TO_FAMILY[u]
        return v * fac, fam
    return v, u
