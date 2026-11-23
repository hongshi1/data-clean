"""Root-cause attribution for inconsistency localizations (M92).

两层根因分类, 填充InconsistencyLocalization.root_cause:

- 根因源(source): 不一致的根源住在哪一层 —
  ``answer``(answer侧引入错误, 文档本身一致) /
  ``document_internal``(文档自相矛盾, answer可能只是如实转述违例侧) /
  ``document_gap``(文档缺失应规定的内容, 合规缺口) /
  ``recall_insufficient``(证据召回不足/判定器不可用, 非文档也非answer).
- 根因操作(operation): 差异的语义机制 —
  knowledge/nli_difference_taxonomy.json的13条difference_type(条件/量词/
  模态/时序/否定/实体/值/关系/异常流/覆盖) + 4条结构性扩展操作
  (``dual_registration``注册表同ID双指 / ``scope_leakage``枚举成员泄漏出
  封闭注册集 / ``compliance_gap``GJB合规覆盖缺口 / ``semantic_unspecified``
  无法分类) — NLI条目体系不覆盖注册表/封闭集/合规类结构通道的机制.

设计契约(用户要求: 声明式表驱动, 零if-else链):
1. ``CHANNEL_ROOT_CAUSE`` — 检测通道method→默认{source, operation}直查表
   (专家通道按映射表直查);
2. ``RATIONALE_REFINEMENTS`` — (method前缀, rationale正则)→{source,
   operation}覆盖的有序规则表: 通道rationale携带的结构线索(双登记/错别字/
   见于正文枚举/同行矛盾)把根因从通道默认值细化到实例机制;
3. ``NLI_OPERATION_KEYWORDS`` — nli_residual通道的轻量操作分类器:
   rationale关键词(声明式有序正则表)→13条差异类型, 无命中→
   ``semantic_unspecified``.

``classify_root_cause``是纯函数(两张表+一段正则, 无I/O无模型调用);
本模块顶层零I/O, 13条差异类型以常量登记(与taxonomy文件同步, 由
tools/eval_root_cause.py交叉校验).
"""
from __future__ import annotations

import re

#: 根因源的封闭词表(四层)
ROOT_CAUSE_SOURCE: tuple[str, ...] = (
    "answer",            # answer侧引入(编造/替换/扩大), 文档本身自洽
    "document_internal", # 文档内部自相矛盾(双登记/跨位置值冲突/模板复制)
    "document_gap",      # 文档缺失应规定的内容(合格性方法/功能定义缺口)
    "recall_insufficient",  # 证据召回不足或判定器不可用, 根因在管线而非内容
)

#: 13条NLI语义差异操作(knowledge/nli_difference_taxonomy.json v1.0,
#: difference_type字段; 顺序=文件内条目顺序)
NLI_DIFFERENCE_OPERATIONS: tuple[str, ...] = (
    "precondition_weakening",
    "precondition_fabrication",
    "necessity_sufficiency_swap",
    "quantifier_scope_expansion",
    "quantifier_scope_reduction",
    "modal_conflict",
    "temporal_reversal",
    "negation_mismatch",
    "entity_substitution",
    "value_substitution",
    "relation_inversion",
    "exception_flow_mismatch",
    "coverage_fabrication",
)

#: 结构性扩展操作(13条NLI条目不覆盖的结构通道机制)
STRUCTURAL_OPERATIONS: tuple[str, ...] = (
    "dual_registration",     # 同一唯一标识符被注册给多个主体(注册表唯一性缺陷)
    "scope_leakage",         # answer枚举成员泄漏出封闭注册集(集合成员级冲突)
    "compliance_gap",        # GJB条款要求的覆盖/存在性缺口(文档侧缺内容)
    "semantic_unspecified",  # rationale无足够线索, 无法分类
)

#: 根因操作的封闭词表(13+4)
ROOT_CAUSE_OPERATION: tuple[str, ...] = (
    NLI_DIFFERENCE_OPERATIONS + STRUCTURAL_OPERATIONS)

#: 通道→默认根因直查表(专家通道按表直查, 不看rationale).
#: source语义: 结构/注册表类通道(id/enum/trace/e1)的refute多源于文档自身
#: 登记结构矛盾→document_internal; 逐claim值通道默认answer偏差; 合规覆盖
#: 通道(coverage/gjb)默认document_gap; NLI残差按13条差异类型(answer侧差异).
CHANNEL_ROOT_CAUSE: dict[str, dict[str, str]] = {
    # ── L0/L1专家通道 ──
    # ID注册表join: answer的ID与锚定主体登记值不符(截断/前缀/段序变形)
    "id_join_registry": {"source": "answer",
                         "operation": "value_substitution"},
    # 枚举封闭集join: answer成员不在锚定行封闭集合中
    "enum_join_registry": {"source": "answer",
                           "operation": "scope_leakage"},
    # E1异常流模板: 证据侧E1内容与用例主题错位(疑似跨用例复制)
    "e1_template_match": {"source": "document_internal",
                          "operation": "exception_flow_mismatch"},
    # 覆盖完备声明: 封闭清单要求的条款在冻结证据中缺失
    "coverage_join": {"source": "document_gap",
                      "operation": "compliance_gap"},
    # 正逆双向追踪join: 文档内正逆追踪映射不一致(方向性矛盾)
    "trace_bidirectional_join": {"source": "document_internal",
                                 "operation": "relation_inversion"},
    # 事件流顺序比对: answer步骤顺序与证据流冲突
    "sequence_alignment": {"source": "answer",
                           "operation": "temporal_reversal"},
    # 数值约束Z3: 数值区间/约束冲突
    "numeric_z3_expert": {"source": "answer",
                          "operation": "value_substitution"},
    # GJB规则簇存在性: 规则要求内容缺失/极性冲突
    "gjb_rule_engine": {"source": "document_gap",
                        "operation": "compliance_gap"},
    "gjb_presence_check": {"source": "document_gap",
                           "operation": "compliance_gap"},
    # ── 逐claim通道(claim_channels) ──
    "numeric_interval": {"source": "answer",
                         "operation": "value_substitution"},
    "identifier_exact_match": {"source": "answer",
                               "operation": "value_substitution"},
    "explicit_quote_polarity": {"source": "answer",
                                "operation": "negation_mismatch"},
    "explicit_enum_exclusion": {"source": "answer",
                                "operation": "negation_mismatch"},
    "closed_scope_exclusion": {"source": "answer",
                               "operation": "scope_leakage"},
    # ── 残差NLI通道 ──(operation由NLI_OPERATION_KEYWORDS覆盖)
    "nli_residual": {"source": "answer",
                     "operation": "semantic_unspecified"},
    "nli_residual_unavailable": {"source": "recall_insufficient",
                                 "operation": "semantic_unspecified"},
}

#: L0实体通道前缀(l0_entity_detector:TERM-xx[:warning])的TERM→操作表
#: (entity_detector.py: TERM-01同义异名/TERM-02同名异义/TERM-05名错配/
#:  TERM-07标识符冲突/TERM-08缩写不一致; TERM-03/04为枚举/否定族预留)
L0_ENTITY_TERM_OPERATIONS: dict[str, str] = {
    "TERM-01": "entity_substitution",
    "TERM-02": "entity_substitution",
    "TERM-03": "scope_leakage",
    "TERM-04": "negation_mismatch",
    "TERM-05": "value_substitution",
    "TERM-07": "value_substitution",
    "TERM-08": "value_substitution",
}
_L0_ENTITY_PREFIX = "l0_entity_detector:"
_L0_ENTITY_FALLBACK_OPERATION = "entity_substitution"

#: rationale结构线索→根因覆盖(有序: 先命中先赢; 仅在method前缀命中时生效).
#: 每条=(method前缀, rationale正则, 覆盖根因):
#: - id_join双登记线索: 同一ID注册给多个主体→文档侧注册表缺陷(而非answer替换);
#: - enum错别字线索: 证据侧注册值本身是错别字→文档侧值变形;
#: - enum"见于"线索: answer成员见于正文枚举但不在封闭表行→文档正文/表格
#:   两处登记不一致(文档侧), answer如实转述其中一侧;
#: - trace同行矛盾线索: 同一行内映射非空vs"不追踪"→极性矛盾(非方向反转).
RATIONALE_REFINEMENTS: tuple[tuple[str, str, dict[str, str]], ...] = (
    ("id_join_registry", "同ID|双登记|注册表.{0,12}多",
     {"source": "document_internal", "operation": "dual_registration"}),
    ("enum_join_registry", "错别字",
     {"source": "document_internal", "operation": "value_substitution"}),
    ("enum_join_registry", "见于",
     {"source": "document_internal", "operation": "scope_leakage"}),
    ("trace_bidirectional_join", "同行矛盾|不追踪",
     {"source": "document_internal", "operation": "negation_mismatch"}),
)

#: nli_residual的rationale关键词→13条差异类型(有序声明式正则表,
#: 先命中先赢; 无命中→semantic_unspecified). 当前nli_residual的rationale
#: 只含"NLI残差判定：CONTRADICTION(p=..)…"标签概率, 无差异机制线索→
#: 多数落入semantic_unspecified; 本表是通道升级为携带差异线索后的挂点.
NLI_OPERATION_KEYWORDS: dict[str, str] = {
    "前置条件.{0,6}弱化|弱化为|必要条件.{0,6}弱化":
        "precondition_weakening",
    "前置条件.{0,4}虚构|条件.{0,4}编造|未规定的条件":
        "precondition_fabrication",
    "必要.{0,4}充分|充分.{0,4}必要|充要":
        "necessity_sufficiency_swap",
    "范围扩大|全称|所有|全部|均支持|量化.{0,4}扩大":
        "quantifier_scope_expansion",
    "范围缩小|仅.{0,8}支持|限定为部分|部分断言":
        "quantifier_scope_reduction",
    "模态.{0,4}冲突|禁止.{0,8}允许|必须.{0,8}不支持":
        "modal_conflict",
    "时序.{0,4}颠倒|顺序.{0,4}颠倒|先后.{0,4}反|依赖方向.{0,4}反":
        "temporal_reversal",
    "极性.{0,4}相反|否定.{0,4}错配|不支持.{0,8}支持":
        "negation_mismatch",
    "主体.{0,4}替换|实体.{0,4}替换|张冠李戴|归属.{0,4}错":
        "entity_substitution",
    "值.{0,4}替换|值.{0,4}截断|标识符.{0,6}不符|参数.{0,4}不符":
        "value_substitution",
    "关系.{0,4}反转|方向.{0,4}反转|发送.{0,8}接收.{0,8}颠倒":
        "relation_inversion",
    "异常流.{0,4}错配|E1.{0,8}错位|例外.{0,4}流程":
        "exception_flow_mismatch",
    "覆盖.{0,4}虚构|声称存在.{0,12}未规定|子功能.{0,4}编造":
        "coverage_fabrication",
}

#: 兜底根因(未知method/refute来源无法归入已知通道)
UNKNOWN_ROOT_CAUSE: dict[str, str] = {
    "source": "answer", "operation": "semantic_unspecified"}

_REFINEMENT_CACHE: dict[str, re.Pattern[str]] = {}
for _prefix, _pattern, _cause in RATIONALE_REFINEMENTS:
    _REFINEMENT_CACHE[_pattern] = re.compile(_pattern)
_KEYWORD_CACHE: dict[str, re.Pattern[str]] = {
    pattern: re.compile(pattern) for pattern in NLI_OPERATION_KEYWORDS}


def _l0_entity_cause(method: str) -> dict[str, str] | None:
    """l0_entity_detector:TERM-xx[:warning] → 按TERM码查操作表."""
    if not method.startswith(_L0_ENTITY_PREFIX):
        return None
    code = method[len(_L0_ENTITY_PREFIX):].split(":", 1)[0]
    return {"source": "answer",
            "operation": L0_ENTITY_TERM_OPERATIONS.get(
                code, _L0_ENTITY_FALLBACK_OPERATION)}


def _nli_operation(rationale: str) -> str:
    """nli_residual rationale关键词→13条差异类型(先命中先赢)."""
    for pattern, operation in NLI_OPERATION_KEYWORDS.items():
        if _KEYWORD_CACHE[pattern].search(rationale):
            return operation
    return "semantic_unspecified"


def classify_root_cause(method: str, rationale: str) -> dict[str, str]:
    """method+rationale → 两层根因{"source", "operation"}(纯函数).

    查表顺序(全声明式):
    1. RATIONALE_REFINEMENTS: (method前缀, rationale正则)命中→覆盖值;
    2. CHANNEL_ROOT_CAUSE直查 / L0实体通道按TERM码查操作表;
    3. nli_residual: NLI_OPERATION_KEYWORDS关键词分类operation
       (source保持answer);
    4. 未知method→UNKNOWN_ROOT_CAUSE.

    返回新dict(调用方可安全改写; 不共享模块表对象).
    """
    for prefix, pattern, cause in RATIONALE_REFINEMENTS:
        if method.startswith(prefix) and _REFINEMENT_CACHE[pattern].search(
                rationale):
            return dict(cause)
    if method in CHANNEL_ROOT_CAUSE:
        base = dict(CHANNEL_ROOT_CAUSE[method])
        if method.startswith("nli_residual"):
            base["operation"] = _nli_operation(rationale)
        return base
    entity_cause = _l0_entity_cause(method)
    if entity_cause is not None:
        return entity_cause
    return dict(UNKNOWN_ROOT_CAUSE)


__all__ = [
    "CHANNEL_ROOT_CAUSE",
    "NLI_DIFFERENCE_OPERATIONS",
    "NLI_OPERATION_KEYWORDS",
    "RATIONALE_REFINEMENTS",
    "ROOT_CAUSE_OPERATION",
    "ROOT_CAUSE_SOURCE",
    "STRUCTURAL_OPERATIONS",
    "classify_root_cause",
]
