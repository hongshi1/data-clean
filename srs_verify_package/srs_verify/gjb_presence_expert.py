"""GJB封闭清单有无检查器（L1组件，覆盖GJB-01~GJB-11共11个检测项）。

taxonomy v3的GJB-01~GJB-11均为"有没有"式检查：SRS文档是否包含GJB
438C标准强制要求的内容（合格性/质量因素/安全性/保密性/追溯表与掉电/
审计/自检/降级等条款）。本专家分两层，均为确定性符号匹配（无模型
调用、无检索、无文件读写）：

1. 证据侧审计（audit_gjb_presence）：按封闭清单GJB_CHECKS逐项检查
   冻结证据——表格存在性（表头关键词签名，复用evidence_statements
   的``_table_rows``/``_strip_tags``解析HTML表头）+ 条款存在性（正则
   匹配）。每个要求项=表签名或条款正则（OR语义：表格命中或条款文本
   命中任一即present），check级别为各要求项的AND。这是文档级审计，
   与answer无关，输出供answer检查与诊断用。
2. answer侧校验（verify_gjb_presence）：当answer对某GJB项做出存在/
   不存在声明（segment同时命中该check触发词与明确的存在/缺失语义
   标记）时，与证据侧审计比对：
     证据present+answer称有→support    证据absent+answer称有→refute
     证据present+answer称无→refute     证据absent+answer称无→
   completeness=closed上下文support，否则not_in_evidence。GJB项为
   封闭清单（标准对每份SRS强制要求该项内容），故answer声称存在而
   冻结证据无该项时判refute而非NIE；缺失声称则因冻结证据通常为open
   子集（completeness_proof明示不保证穷尽）判NIE，closed才support。

只在answer涉及GJB内容时返回非空ClaimResult（method=
"gjb_presence_check"，check_item_candidates=对应GJB-XX），避免对无关
QA输出审计噪音；question是否GJB类由qa_router.route_question判定并记
入rationale。GJB_CHECKS为模块常量（源：knowledge/
consistency_taxonomy_v3.json的GJB-01~11项original_example/
doc04_evidence，rule_ids关联knowledge/gjb_438c_rules_full.json的120条
规则编号，tests/test_gjb_presence_expert.py核验其存在性）。
存在/缺失极性词表外置于rule pack（gjb_absence_words/gjb_presence_words，
与coverage_expert/gjb_rule_engine共享同一配置来源，消除词表import漂移）。

条款正则校准（按04号SRS真实词频分布核验）：bare「容错」命中35个
用例表头样板「动作约束（性能、可靠性、容错等）」，故GJB-02仅匹配
容错处置/机制/能力/故障检测/失败重连等复合形态；「审计日志」要求
连续复合词——04号1.2的「访问审计以及日志记录功能」是概述级提及而
非需求条款，GJB-04判缺失（与taxonomy doc04_violation一致）；bare
「升级」仅命中3.15保障表一行「软件升级」，GJB-10仍判缺失。表块
条款匹配优先用linearize_context语句拼接（丢弃表头样板单元格），
无语句时回退到单元格拼接；文本块直接用原文（语句化会丢弃短句）。
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from srs_verify.evidence_statements import (
    EvidenceStatement,
    _strip_tags,
    _table_rows,
    linearize_context,
)
from srs_verify.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    Verdict,
)
from srs_verify.qa_router import route_question
from srs_verify.rulepack import default_rulepack

METHOD = "gjb_presence_check"
CHECK_ITEMS: tuple[str, ...] = tuple(
    f"GJB-{index:02d}" for index in range(1, 12))
_CHECK_ID_SET = frozenset(CHECK_ITEMS)


@dataclass(frozen=True)
class GjbComponent:
    """封闭清单中的一个要求项：表签名或条款正则（OR）。

    table_keywords非空时匹配表头（全部关键词都在首行表头中）；pattern
    非空时匹配块级条款文本；两者至少提供其一。
    """

    label: str
    table_keywords: tuple[str, ...] = ()
    pattern: re.Pattern[str] | None = None


@dataclass(frozen=True)
class GjbCheck:
    """一个GJB封闭清单检查项（taxonomy v3 GJB-01~GJB-11）。"""

    check_id: str
    name: str
    description: str
    components: tuple[GjbComponent, ...]
    rule_ids: tuple[str, ...]
    answer_triggers: tuple[str, ...]


GJB_CHECKS: tuple[GjbCheck, ...] = (
    GjbCheck(
        check_id="GJB-01",
        name="可测试性合规校验（国军标438C）",
        description="SRS应为每条需求指定合格性方法，并含质量因素规定"
                    "（可测试性等），04号对应表73质量因素+表80合格性规定。",
        components=(
            GjbComponent(
                label="合格性规定",
                table_keywords=("合格性",),
                pattern=re.compile(r"合格性方法|合格性规定|合格性检验方法")),
            GjbComponent(
                label="质量因素",
                table_keywords=("质量因素",),
                pattern=re.compile(r"质量因素")),
        ),
        rule_ids=("GJB-RULE-036", "GJB-RULE-065", "GJB-RULE-077",
                  "GJB-RULE-117"),
        answer_triggers=("可测试", "可验证", "量化指标", "合格性", "质量因素"),
    ),
    GjbCheck(
        check_id="GJB-02",
        name="故障容错需求完备性校验",
        description="SRS应含安全性需求及故障容错处置条款"
                    "（04号对应表68安全性：故障检测+失败重连）。",
        components=(
            GjbComponent(
                label="安全性/容错条款",
                table_keywords=("安全性",),
                pattern=re.compile(
                    r"容错(处置|机制|能力|设计|措施)|故障检测|失败重连"
                    r"|故障恢复|故障处置|自动重连")),
        ),
        rule_ids=("GJB-RULE-041", "GJB-RULE-063"),
        answer_triggers=("容错", "故障容错", "容错处置", "容错机制",
                         "容错能力", "故障检测", "失败重连"),
    ),
    GjbCheck(
        check_id="GJB-03",
        name="安全访问控制合规校验",
        description="SRS应含保密性需求及访问控制条款"
                    "（04号对应表69保密性：身份认证+数据库访问控制）。",
        components=(
            GjbComponent(
                label="保密性/访问控制条款",
                table_keywords=("保密性",),
                pattern=re.compile(
                    r"访问控制|身份认证|权限(等级|划分|控制)|越权拦截"
                    r"|操作权限")),
        ),
        rule_ids=("GJB-RULE-062", "GJB-RULE-063"),
        answer_triggers=("访问控制", "权限控制", "安全控制", "身份认证",
                         "保密性", "越权", "权限等级", "操作权限"),
    ),
    GjbCheck(
        check_id="GJB-04",
        name="审计日志合规校验",
        description="SRS应含关键操作/参数修改/权限变更的审计日志条款"
                    "（04号仅1.2概述级提及，判缺失）。",
        components=(
            GjbComponent(
                label="审计日志条款",
                pattern=re.compile(
                    r"审计日志|日志审计|操作日志|审计记录|审计追踪")),
        ),
        rule_ids=("GJB-RULE-034", "GJB-RULE-062"),
        answer_triggers=("审计日志", "日志审计", "审计功能", "审计记录",
                         "访问审计"),
    ),
    GjbCheck(
        check_id="GJB-05",
        name="需求可追溯性合规校验",
        description="SRS应含需求可追溯性规定（表头同时含任务书与本文档"
                    "的追踪表，04号对应表81正向+表82逆向；深度join检查"
                    "由trace_expert负责，此处仅做有无检查）。",
        components=(
            GjbComponent(
                label="需求追溯表",
                table_keywords=("任务书", "本文档"),
                pattern=re.compile(r"需求可追踪|可追溯性|可追踪性")),
        ),
        rule_ids=("GJB-RULE-037", "GJB-RULE-078", "GJB-RULE-079",
                  "GJB-RULE-118"),
        answer_triggers=("追溯表", "追踪表", "可追溯", "可追踪",
                         "追溯关系", "追踪关系", "需求追溯", "需求追踪"),
    ),
    GjbCheck(
        check_id="GJB-06",
        name="异常报警要素合规校验",
        description="报警/告警信息应含时间戳、故障位置、等级、处置建议"
                    "等要素（04号用例表E1仅提示文本，判缺失）。",
        components=(
            GjbComponent(
                label="报警要素条款",
                pattern=re.compile(
                    r"(报警|告警|警告)[^。；\n]{0,40}"
                    r"(时间|位置|等级|原因|处置|建议)"
                    r"|(时间戳|故障位置|故障等级|处置建议)[^。；\n]{0,40}"
                    r"(报警|告警|警告)")),
        ),
        rule_ids=("GJB-RULE-041",),
        answer_triggers=("报警要素", "报警级别", "报警内容", "报警原因",
                         "报警等级", "报警信息", "告警要素", "告警级别",
                         "告警内容", "告警信息"),
    ),
    GjbCheck(
        check_id="GJB-07",
        name="软件自检条款合规校验",
        description="SRS应含上电/启动/周期自检条款"
                    "（04号表68 row1系统自检命中）。",
        components=(
            GjbComponent(
                label="自检条款",
                pattern=re.compile(r"自检|自测试|开机检测")),
        ),
        rule_ids=("GJB-RULE-041", "GJB-RULE-063"),
        answer_triggers=("自检", "自测试", "开机检测"),
    ),
    GjbCheck(
        check_id="GJB-08",
        name="掉电数据保护合规校验",
        description="SRS应含关键配置/任务状态的掉电保存与恢复条款"
                    "（04号完全缺失）。",
        components=(
            GjbComponent(
                label="掉电保护条款",
                pattern=re.compile(r"掉电|断电")),
        ),
        rule_ids=("GJB-RULE-041", "GJB-RULE-063"),
        answer_triggers=("掉电", "断电保护", "断电恢复", "断电保存"),
    ),
    GjbCheck(
        check_id="GJB-09",
        name="输入数据防护合规校验",
        description="SRS应含非法报文/越界参数/畸形输入的拦截校验条款"
                    "（04号仅有值域约束，无显式输入校验声明）。",
        components=(
            GjbComponent(
                label="输入防护条款",
                pattern=re.compile(
                    r"非法(输入|报文|数据|字符|格式)"
                    r"|输入(校验|防护|过滤|检查|合法性)"
                    r"|畸形(输入|数据|报文)|越界(输入|参数|数据)"
                    r"|参数(校验|越界)")),
        ),
        rule_ids=("GJB-RULE-041", "GJB-RULE-057"),
        answer_triggers=("输入校验", "输入防护", "非法输入", "输入过滤",
                         "输入检查", "畸形输入", "非法报文", "越界参数"),
    ),
    GjbCheck(
        check_id="GJB-10",
        name="版本升级安全合规校验",
        description="升级流程应含升级包校验与失败自动回滚条款"
                    "（04号3.15仅有「软件升级」保障条目，判缺失）。",
        components=(
            GjbComponent(
                label="升级安全条款",
                pattern=re.compile(
                    r"升级包|回滚|升级(校验|失败|回退|兼容)|版本兼容"
                    r"|升级前校验")),
        ),
        rule_ids=("GJB-RULE-073",),
        answer_triggers=("升级包", "回滚", "升级校验", "升级失败",
                         "版本兼容", "升级安全", "升级回退"),
    ),
    GjbCheck(
        check_id="GJB-11",
        name="降级运行合规校验",
        description="故障场景应有分级降级运行策略"
                    "（04号3.1仅一个运行状态，判缺失）。",
        components=(
            GjbComponent(
                label="降级运行条款",
                pattern=re.compile(r"降级(运行|模式|策略|处理|机制|功能)"
                                   r"|分级降级")),
        ),
        rule_ids=("GJB-RULE-038", "GJB-RULE-097"),
        answer_triggers=("降级模式", "降级运行", "降级策略", "分级降级",
                         "降级功能"),
    ),
)


@dataclass(frozen=True)
class GjbCheckAudit:
    """一个检查项的证据侧审计结果（文档级，与answer无关）。"""

    check_id: str
    name: str
    present: tuple[str, ...]
    missing: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    @property
    def is_present(self) -> bool:
        """全部要求项命中。"""
        return bool(self.present) and not self.missing

    @property
    def is_absent(self) -> bool:
        """无任何要求项命中。"""
        return not self.present


@dataclass(frozen=True)
class GjbPresenceAudit:
    """GJB封闭清单的文档级审计结果。"""

    checks: tuple[GjbCheckAudit, ...]

    def by_check_id(self) -> dict[str, GjbCheckAudit]:
        return {audit.check_id: audit for audit in self.checks}

    def diagnostics(self) -> tuple[str, ...]:
        """缺失项诊断清单（每条一个缺失检查项）。"""
        return tuple(
            f"{audit.check_id}({audit.name})缺失"
            f"[{'、'.join(audit.missing)}]"
            for audit in self.checks if audit.missing)


def _table_signature_hit(text: str, keywords: tuple[str, ...]) -> bool:
    """表头签名匹配：全部关键词都在首行表头中（仅表块参与）。"""
    if "<table" not in text:
        return False
    rows = _table_rows(text)
    if not rows:
        return False
    header = _strip_tags("；".join(rows[0]))
    return all(keyword in header for keyword in keywords)


def _clause_text(block: RetrievedEvidence,
                 statements_by_id: dict[str, list[EvidenceStatement]]) -> str:
    """块级条款匹配文本。

    表块：优先用linearize_context语句拼接（表头样板单元格已被语句化
    规则丢弃，避免「容错等」样板误命中）；无语句时回退到全部单元格
    拼接。文本块：直接用原文（语句化会丢弃<8字符短句，如「提供自检。」）。
    """
    if "<table" in block.text:
        parts = [statement.text
                 for statement in statements_by_id.get(block.evidence_id, [])]
        if parts:
            return "；".join(parts)
        cells = [cell for row in _table_rows(block.text) for cell in row]
        return "；".join(cells) if cells else _strip_tags(block.text)
    return block.text


def _component_refs(
        component: GjbComponent,
        blocks: list[RetrievedEvidence],
        clause_texts: list[str]) -> tuple[str, ...]:
    """一个要求项的命中证据块（表签名或条款正则，OR语义）。"""
    refs: list[str] = []
    for block, clause_text in zip(blocks, clause_texts):
        if (component.table_keywords
                and _table_signature_hit(block.text, component.table_keywords)):
            refs.append(block.evidence_id)
            continue
        if component.pattern is not None and component.pattern.search(
                clause_text):
            refs.append(block.evidence_id)
    return tuple(refs)


def audit_gjb_presence(
        evidence: Iterable[RetrievedEvidence],
        statements: Iterable[EvidenceStatement] | None = None,
) -> GjbPresenceAudit:
    """对冻结证据块执行GJB封闭清单有无审计（文档级，与answer无关）。

    statements为linearize_context输出；缺省时由evidence自动推导。
    返回逐检查项的present/missing标签与证据块引用（evidence_id级）。
    """
    blocks = list(evidence)
    if statements is None:
        statement_list = linearize_context(tuple(blocks))
    else:
        statement_list = list(statements)
    statements_by_id: dict[str, list[EvidenceStatement]] = {}
    for statement in statement_list:
        statements_by_id.setdefault(statement.evidence_id, []).append(
            statement)
    clause_texts = [_clause_text(block, statements_by_id)
                    for block in blocks]
    audits: list[GjbCheckAudit] = []
    for check in GJB_CHECKS:
        present: list[str] = []
        missing: list[str] = []
        refs: set[str] = set()
        for component in check.components:
            found = _component_refs(component, blocks, clause_texts)
            if found:
                present.append(component.label)
                refs.update(found)
            else:
                missing.append(component.label)
        audits.append(GjbCheckAudit(
            check_id=check.check_id, name=check.name,
            present=tuple(present), missing=tuple(missing),
            evidence_refs=tuple(sorted(refs))))
    return GjbPresenceAudit(checks=tuple(audits))


#: 存在/缺失极性词表取自rule pack（平铺交替正则，成员与迁移前源码
#: 逐字一致）；模块级缓存避免逐segment重建，import期零I/O。
_ABSENCE_RE_CACHE: re.Pattern[str] | None = None
_PRESENCE_RE_CACHE: re.Pattern[str] | None = None


def _absence_re() -> re.Pattern[str]:
    """缺失语义标记词表（规则包gjb_absence_words）。"""
    global _ABSENCE_RE_CACHE
    if _ABSENCE_RE_CACHE is None:
        _ABSENCE_RE_CACHE = default_rulepack().vocabulary_regex(
            "gjb_absence_words")
    return _ABSENCE_RE_CACHE


def _presence_re() -> re.Pattern[str]:
    """存在语义标记词表（规则包gjb_presence_words）。"""
    global _PRESENCE_RE_CACHE
    if _PRESENCE_RE_CACHE is None:
        _PRESENCE_RE_CACHE = default_rulepack().vocabulary_regex(
            "gjb_presence_words")
    return _PRESENCE_RE_CACHE


_SEGMENT_SPLIT = re.compile(r"(?<=[。；！？\n])")
_MIN_SEGMENT_CHARS = 6


def _segment_polarity(segment: str,
                      triggers: tuple[str, ...]) -> str | None:
    """判定segment对触发主题的存在性语义：absent优先于present。

    absent：缺失语义标记，或触发词紧邻无/未/没前缀、后接缺失词；
    present：存在语义标记；均无→None（非存在性声明，跳过避免噪音）。
    """
    if _absence_re().search(segment):
        return "absent"
    for trigger in triggers:
        if re.search(r"[无未没]" + re.escape(trigger), segment) or re.search(
                re.escape(trigger) + r"(缺失|缺少|不存在|为空)", segment):
            return "absent"
    if _presence_re().search(segment):
        return "present"
    return None


def _answer_gjb_claims(
        answer: str,
) -> list[tuple[GjbCheck, str, str, tuple[str, ...]]]:
    """提取answer中的GJB封闭清单存在性声明。

    返回(check, polarity, segment, 触发词)；同一(check_id, polarity)
    只保留首个命中segment（answer内去重，保证判定确定性）。
    """
    claims: list[tuple[GjbCheck, str, str, tuple[str, ...]]] = []
    seen: set[tuple[str, str]] = set()
    for raw_segment in _SEGMENT_SPLIT.split(answer):
        segment = raw_segment.strip()
        if len(segment) < _MIN_SEGMENT_CHARS:
            continue
        for check in GJB_CHECKS:
            hits = tuple(trigger for trigger in check.answer_triggers
                         if trigger in segment)
            if not hits:
                continue
            polarity = _segment_polarity(segment, check.answer_triggers)
            if polarity is None:
                continue
            key = (check.check_id, polarity)
            if key in seen:
                continue
            seen.add(key)
            claims.append((check, polarity, segment, hits))
    return claims


def verify_gjb_presence(
        request: QAInput,
        statements: Iterable[EvidenceStatement] | None = None,
) -> list[ClaimResult]:
    """校验answer对GJB封闭清单项的存在性声称（L1确定性）。

    输出method="gjb_presence_check"的ClaimResult列表；answer不涉及GJB
    内容时返回[]。证据侧审计结果嵌入rationale；文档级审计诊断可经
    audit_gjb_presence单独获取（不产生answer判定）。
    """
    audit = audit_gjb_presence(request.evidence, statements)
    audits = audit.by_check_id()
    routed = tuple(item for item in route_question(request.question)
                   if item in _CHECK_ID_SET)
    context_closed = bool(request.evidence) and all(
        block.completeness == "closed" for block in request.evidence)
    results: list[ClaimResult] = []
    for order, (check, polarity, segment, hits) in enumerate(
            _answer_gjb_claims(request.answer), start=1):
        state = audits[check.check_id]
        labels = "、".join(component.label for component in check.components)
        route_note = (f"；question路由命中{check.check_id}"
                      if check.check_id in routed else "")
        verdict: Verdict
        if polarity == "present":
            if state.is_present:
                verdict = "support"
                refs = state.evidence_refs
                confidence = 0.9
                rationale = (
                    f"{check.check_id}{check.name}：冻结证据含全部要求项"
                    f"（{'、'.join(state.present)}），answer存在性声称"
                    f"（{'、'.join(hits)}）成立{route_note}")
            else:
                verdict = "refute"
                refs = state.evidence_refs
                confidence = 0.9
                rationale = (
                    f"GJB封闭清单项{check.check_id}{check.name}要求"
                    f"[{labels}]，冻结证据缺失"
                    f"[{'、'.join(state.missing) if state.missing else labels}]"
                    f"；answer声称存在（{'、'.join(hits)}）但证据中无该项"
                    f"内容——封闭清单存在性声称判refute{route_note}")
        else:
            if state.is_absent:
                if context_closed:
                    verdict = "support"
                    refs = ()
                    confidence = 0.9
                    rationale = (
                        f"{check.check_id}{check.name}：封闭上下文"
                        f"（completeness=closed）中未见[{labels}]，answer"
                        f"缺失声称（{'、'.join(hits)}）成立{route_note}")
                else:
                    verdict = "not_in_evidence"
                    refs = ()
                    confidence = 0.0
                    rationale = (
                        f"{check.check_id}{check.name}：冻结证据未见"
                        f"[{labels}]，但上下文completeness非closed（证据为"
                        f"open子集，不保证穷尽），无法证实文档整体缺失"
                        f"——answer缺失声称判not_in_evidence{route_note}")
            else:
                verdict = "refute"
                refs = state.evidence_refs
                confidence = 0.9
                rationale = (
                    f"{check.check_id}{check.name}：冻结证据存在"
                    f"[{'、'.join(state.present)}]，answer声称缺失"
                    f"（{'、'.join(hits)}）与证据矛盾{route_note}")
        results.append(ClaimResult(
            claim_id=f"{request.instance_id}-gjb{order:02d}",
            claim_text=segment,
            verdict=verdict,
            check_item_candidates=(check.check_id,),
            evidence_refs=refs,
            rationale=rationale,
            method=METHOD,
            confidence=confidence,
        ))
    return results


__all__ = [
    "CHECK_ITEMS",
    "GJB_CHECKS",
    "GjbCheck",
    "GjbCheckAudit",
    "GjbComponent",
    "GjbPresenceAudit",
    "METHOD",
    "audit_gjb_presence",
    "verify_gjb_presence",
]
