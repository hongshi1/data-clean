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


# ═══════════════════════════════════════════════════════════════
# 详细根因解释生成器(M109): 逐字差异分析+成因推断+修正建议
# ═══════════════════════════════════════════════════════════════

#: 根因操作→成因推断与解读的模板(声明式; {}占位: claim=答案值, doc=文档值,
#: diff=逐字差异描述, extra=操作特定线索)
OPERATION_NARRATIVES: dict[str, dict[str, str]] = {
    "value_substitution": {
        "mechanism": "答案引用的值与文档登记值不一致",
        "likely_cause": "疑为复制不完整（截断）、串用了同表其他行的相似值，或转写时变形",
        "fix": "以文档登记值为准修正答案的该处断言",
    },
    "dual_registration": {
        "mechanism": "文档内部同一标识符被登记给了两个不同主体",
        "likely_cause": "文档注册表唯一性缺陷（模板复制或修订时引入），答案如实转述了其中一侧",
        "fix": "需修订文档：为两个主体分别分配不同的唯一标识符",
    },
    "scope_leakage": {
        "mechanism": "答案枚举的成员不属于锚定行的封闭集合",
        "likely_cause": "疑为把同表其他行的成员（或正文别处的枚举）误并入本主体的集合",
        "fix": "以锚定行登记的封闭集合为准修正答案",
    },
    "quantifier_scope_expansion": {
        "mechanism": "答案把文档的限定断言扩大成了无限定断言",
        "likely_cause": "答案生成时丢失了限定词（仅/部分/特定场景），把限定集合泛化",
        "fix": "恢复文档原始限定范围",
    },
    "quantifier_scope_reduction": {
        "mechanism": "答案把文档的全称断言缩小成了部分断言",
        "likely_cause": "答案附加了文档没有的限定",
        "fix": "去掉答案中多余的限定",
    },
    "precondition_weakening": {
        "mechanism": "答案弱化了文档要求的前置条件",
        "likely_cause": "答案遗漏了必要的条件（如需二次认证、需审批），扩大了允许范围",
        "fix": "补全文档要求的前置条件",
    },
    "precondition_fabrication": {
        "mechanism": "答案声称了文档未规定的前置条件",
        "likely_cause": "答案编造了约束",
        "fix": "删除虚构条件",
    },
    "necessity_sufficiency_swap": {
        "mechanism": "答案混淆了文档条件的必要性/充分性",
        "likely_cause": "把'仅当X才允许Y'（必要条件）读成'X后一定Y'（充分条件）",
        "fix": "按文档条件的逻辑方向重述",
    },
    "modal_conflict": {
        "mechanism": "答案的模态与文档相反（允许/必须/禁止）",
        "likely_cause": "答案把禁止说成支持，或把必须说成可选",
        "fix": "按文档模态修正",
    },
    "temporal_reversal": {
        "mechanism": "答案颠倒了文档规定的顺序/依赖方向",
        "likely_cause": "步骤或依赖被反转",
        "fix": "按文档规定的顺序修正",
    },
    "negation_mismatch": {
        "mechanism": "答案的极性与文档相反",
        "likely_cause": "否定被丢失或误加",
        "fix": "按文档极性修正",
    },
    "relation_inversion": {
        "mechanism": "答案反转了文档的方向性关系",
        "likely_cause": "发送/接收、依赖方向被对调",
        "fix": "按文档原始方向修正",
    },
    "entity_substitution": {
        "mechanism": "答案把断言主体换成了另一实体",
        "likely_cause": "张冠李戴——值真实存在但属于别的主体",
        "fix": "把值归位到正确的主体",
    },
    "exception_flow_mismatch": {
        "mechanism": "答案对异常流内容的归属错位",
        "likely_cause": "把约束列/主事件流的内容误归到E1异常流（或反之）",
        "fix": "按文档流程归属修正",
    },
    "coverage_fabrication": {
        "mechanism": "答案声称了文档未规定的子功能/操作",
        "likely_cause": "答案过度泛化或引入了外部知识",
        "fix": "删除文档未规定的声称",
    },
    "compliance_gap": {
        "mechanism": "封闭清单要求的条款在文档中缺失",
        "likely_cause": "文档编写遗漏了该合规条款的覆盖",
        "fix": "需修订文档：补充该条款的规定内容",
    },
    "semantic_unspecified": {
        "mechanism": "语义层面的不一致",
        "likely_cause": "答案与证据存在语义冲突（机制待细分）",
        "fix": "对照文档证据人工复核该断言",
    },
}

_ROOT_CAUSE_SOURCE_ZH = {
    "answer": "答案侧错误",
    "document_internal": "文档内部不一致",
    "document_gap": "文档缺失（合规条款未覆盖）",
    "recall_insufficient": "证据召回不足",
}
ROOT_CAUSE_SOURCE_ZH = _ROOT_CAUSE_SOURCE_ZH
ROOT_CAUSE_OPERATION_ZH = {op: nar["mechanism"] for op, nar in
                           OPERATION_NARRATIVES.items()}


def _extract_value(text: str) -> str:
    """从证据语句提取登记值(『：』后的部分; 无冒号取末段)."""
    text = str(text).strip()
    if "：" in text:
        return text.split("：", 1)[1].strip()
    if ":" in text:
        return text.split(":", 1)[1].strip()
    parts = re.split(r"[，。；]", text)
    return parts[-1].strip() if parts else text


def _char_diff(claim_value: str, doc_value: str) -> str:
    """逐字差异描述(声明式: 前缀/后缀/替换块; 短值直白描述)."""
    claim_value = str(claim_value).strip()
    doc_value = str(doc_value).strip()
    if not claim_value or not doc_value or claim_value == doc_value:
        return ""
    import difflib
    matcher = difflib.SequenceMatcher(None, claim_value, doc_value)
    ops = [op for op in matcher.get_opcodes() if op[0] != "equal"]
    parts = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "delete":
            parts.append(f"答案多出「{claim_value[i1:i2]}」")
        elif tag == "insert":
            parts.append(f"答案缺少「{doc_value[j1:j2]}」")
        else:
            parts.append(f"「{claim_value[i1:i2]}」应为「{doc_value[j1:j2]}」")
    return "；".join(parts)


def detailed_explanation(loc: dict | object, answer: str) -> str:
    """一条不一致的详细中文根因分析(多行结构化叙述).

    组成(每行一个【】标签段):
      【差异分析】  逐字比对答案值与文档登记值的具体差异
      【成因推断】  该操作机制的成因解释(17条模板)
      【影响说明】  根因源归属+语义
      【修正建议】  按文档值/机制给出修正方向
    loc参数: InconsistencyLocalization实例(取claim_text/evidence/
    root_cause/rationale)或等价dict.
    """
    claim = str(getattr(loc, "claim_text", "") or
                (loc.get("claim_text", "") if isinstance(loc, dict) else ""))
    evidence = (getattr(loc, "evidence", None) or
                (loc.get("evidence") if isinstance(loc, dict) else None)
                or ())
    rc = (getattr(loc, "root_cause", None) or
          (loc.get("root_cause") if isinstance(loc, dict) else None) or {})
    source = str(rc.get("source", ""))
    operation = str(rc.get("operation", ""))
    narrative = OPERATION_NARRATIVES.get(operation,
                                         OPERATION_NARRATIVES[
                                             "semantic_unspecified"])
    lines = []
    # 差异分析: 有证据语句时逐字比对
    doc_value = ""
    if evidence:
        ev = evidence[0]
        doc_text = str(getattr(ev, "statement_text", "") or
                       (ev.get("statement_text", "")
                        if isinstance(ev, dict) else ""))
        doc_value = _extract_value(doc_text)
        diff = _char_diff(claim, doc_value)
        if diff:
            lines.append(f"【差异分析】答案值「{claim}」与文档登记值"
                         f"「{doc_value}」逐字比对：{diff}。")
    # 成因推断
    lines.append(f"【成因推断】{narrative['mechanism']}——"
                 f"{narrative['likely_cause']}。")
    # 影响说明
    source_zh = _ROOT_CAUSE_SOURCE_ZH.get(source, "待细分")
    op_zh = ROOT_CAUSE_OPERATION_ZH.get(operation, "语义差异")
    lines.append(f"【根因判定】{source_zh}·{op_zh}。")
    # 修正建议
    fix = narrative["fix"]
    if doc_value and source == "answer":
        fix = f"{fix}（文档登记值：{doc_value}）"
    lines.append(f"【修正建议】{fix}。")
    return "\n".join(lines)


__all__ = [
    "CHANNEL_ROOT_CAUSE",
    "NLI_DIFFERENCE_OPERATIONS",
    "NLI_OPERATION_KEYWORDS",
    "OPERATION_NARRATIVES",
    "RATIONALE_REFINEMENTS",
    "ROOT_CAUSE_OPERATION",
    "ROOT_CAUSE_SOURCE",
    "ROOT_CAUSE_SOURCE_ZH",
    "ROOT_CAUSE_OPERATION_ZH",
    "STRUCTURAL_OPERATIONS",
    "classify_root_cause",
    "detailed_explanation",
]
