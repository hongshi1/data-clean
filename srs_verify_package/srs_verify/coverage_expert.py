"""覆盖完备专家（L1组件，GJB-01合格性逐章覆盖 + GJB-04/06条款覆盖声明）。

gjb_presence_expert只查表/条款的**存在性**（表80在不在），本专家是它的
逐章覆盖深化：把answer的全覆盖声明与合格性表行做**覆盖join**——
VIO-17模式（answer断言"3.1至3.17全部需求均规定了合格性方法"，表80仅
6行覆盖3.2.1~3.2.6，证据中3.3/3.4章节标题存在却无合格性行）在旧专家
判NIE/support，此处判refute。三段流水线：

1. 覆盖关系构建（build_coverage_map，纯确定性符号解析）：
   - 合格性表行：表头含「合格性」的表格按列对齐解析为
     (需求名称, 章节号, 合格性方法)行；方法列为「无/-」的行只登记
     章节事实（已知需求无方法=覆盖缺口），不计入已覆盖行。
   - 章节能力清单：表头含「标识符+需求描述」的能力表解析为
     (Use case名称, 项目唯一标识符)清单。
   - 章节事实：块文本/语句/source_ref.section中以「3.3 标题」形态
     出现的章节号→(章节元组, 标题, 证据引用)。**不读content_list**——
     章节清单全部从冻结证据语句推导；推导不出区间时answer声明无法
     逐章核对，判NIE（用answer声明的范围原文比对缺口的前置是范围内
     至少存在一个证据已知章节）。
2. answer覆盖声明提取（extract_coverage_claims）：
   - 范围声明：'X至Y章节(的)所有/全部/每个/均(有/规定了)合格性方法'；
   - 全称声明：无显式区间的'所有/全部/每条需求都有合格性方法'；
   - 精确断言：'X功能(有/规定了)合格性规定'（主体非泛指词）；
   - GJB条款声明：复用gjb_presence_expert的_answer_gjb_claims封闭
     清单触发词表（import避免行为漂移），仅取GJB-04审计日志/GJB-06
     报警要素的存在正极性segment。
3. 三项检查（verify_coverage → ClaimResult，method="coverage_join"）：
   ① 逐章覆盖比对：范围内已知章节无合格性行（路径重叠判定：行命中
     该章节或其祖先/后代路径才算覆盖）→refute并列缺口清单；
     全覆盖→support；无合格性表或范围内无已知章节→NIE。
   ② 精确断言核对：合格性行命中主体→support；主体在能力清单但表
     无其行→refute；主体不在清单→NIE。
   ③ GJB条款覆盖声明：GJB-04走gjb_presence同一封闭清单审计
     （audit_gjb_presence复用）；GJB-06在answer断言报警要素
     （时间戳/位置/等级/原因/处置建议）时做**逐要素**比对——
     证据报警语句缺失任一声称要素即refute（taxonomy doc04 E1仅提示
     文本的深化），未断言要素时回退条款级审计。

本层完全确定性：无模型调用、无检索、无文件读写；answer不含覆盖声明
时返回[]（91条冻结QA主集零噪音，tests核验）。被覆盖物/泛称主体/报警
要素/缺失极性词表外置于rule pack（config/rulepacks/srs_gjb_v1.json的
term_vocabularies与join_params.coverage，经_cfg()惰性编译——成员与
迁移前源码逐字一致）；范围/全称/标题等声明模式正则与三段流水线逻辑
留引擎。
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from srs_verify.evidence_statements import (
    EvidenceStatement,
    _EMPTY_CELL_VALUES,
    linearize_context,
    table_rows_positional,
)
from srs_verify.gjb_presence_expert import (
    GJB_CHECKS,
    GjbPresenceAudit,
    _answer_gjb_claims,
    _SEGMENT_SPLIT,
    audit_gjb_presence,
)
from srs_verify.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    Verdict,
)
from srs_verify.qa_router import route_question
from srs_verify.rulepack import RulePack, default_rulepack

METHOD = "coverage_join"
CHECK_ITEMS: tuple[str, ...] = ("GJB-01", "GJB-04", "GJB-06")
_CHECK_BY_ID = {check.check_id: check for check in GJB_CHECKS}
#: ③仅处理GJB-04/06条款覆盖声明（GJB-01存在性归gjb_presence，覆盖语义归①②）
_CLAUSE_CHECK_IDS = frozenset({"GJB-04", "GJB-06"})
_CHECK_ID_SET = frozenset(CHECK_ITEMS)


@dataclass(frozen=True)
class _CoverageConfig:
    """从rule pack编译的coverage词表配置（成员与迁移前源码逐字一致）.

    qualification_targets有序（长词在前，命中优先级敏感）；alarm_elements
    有序（要素断言顺序进rationale）；absence词表与gjb_presence/
    gjb_rule_engine共享同一配置来源（消除跨模块词表import漂移）。
    """

    absence_re: re.Pattern[str]
    qualification_targets: tuple[str, ...]
    generic_subjects: frozenset[str]
    alarm_elements: tuple[tuple[str, tuple[str, ...]], ...]
    alarm_synonyms: dict[str, tuple[str, ...]]


def _build_config(pack: RulePack) -> _CoverageConfig:
    raw_elements = pack.join_param("coverage", "alarm_elements", ())
    if not isinstance(raw_elements, (list, tuple)):
        raise ValueError(
            "rulepack coverage.alarm_elements须为"
            "[[标签, [同义词...]], ...]列表")
    elements: list[tuple[str, tuple[str, ...]]] = []
    for item in raw_elements:
        if (not isinstance(item, (list, tuple)) or len(item) != 2
                or not isinstance(item[0], str) or not item[0]
                or not isinstance(item[1], (list, tuple))
                or not all(isinstance(s, str) and s for s in item[1])):
            raise ValueError(
                f"rulepack coverage.alarm_elements项{item!r}须为"
                f"[非空标签, 非空字符串同义词列表]")
        elements.append((item[0], tuple(item[1])))
    if not elements:
        raise ValueError(
            "rulepack coverage.alarm_elements不能为空"
            "（GJB-06逐要素比对无要素清单）")
    return _CoverageConfig(
        absence_re=pack.vocabulary_regex("gjb_absence_words"),
        qualification_targets=pack.vocabulary(
            "coverage_qualification_targets"),
        generic_subjects=frozenset(
            pack.vocabulary("coverage_generic_subjects")),
        alarm_elements=tuple(elements),
        alarm_synonyms={label: synonyms for label, synonyms in elements},
    )


_COVERAGE_CONFIG: _CoverageConfig | None = None
_COVERAGE_PACK: RulePack | None = None


def _cfg() -> _CoverageConfig:
    """惰性加载默认rule pack并编译coverage词表（按pack身份缓存, import期零I/O）."""
    global _COVERAGE_CONFIG, _COVERAGE_PACK
    pack = default_rulepack()
    if _COVERAGE_CONFIG is None or _COVERAGE_PACK is not pack:
        _COVERAGE_PACK = pack
        _COVERAGE_CONFIG = _build_config(pack)
    return _COVERAGE_CONFIG


_RANGE = re.compile(
    r"(?P<start>\d+(?:\.\d+){0,5})\s*(?:个)?(?:章节|节)?\s*[至到~～]\s*"
    r"(?P<end>\d+(?:\.\d+){0,5})\s*(?:个)?\s*(?:章节|节)")
_UNIVERSAL = re.compile(r"所有|全部|各个?|每一?[条个项]|均|都")
_OBJECT = re.compile(r"(?:能力)?(?:需求|功能)")
_COVER_VERB = re.compile(
    r"(?:均|都|皆|已)?(?:有|具有|具备|包含|包括|规定|列出|注明|覆盖|指定|提供)")
_PRECISE_VERB = re.compile(
    r"(?:均|都|皆|已|也)?(?:有|具有|具备|包含|包括|规定|列出|注明|指定|提供)")
_HEADING = re.compile(
    r"^\s*(?P<num>\d+(?:\.\d+){0,5})\s+(?P<title>[^\d\s].{0,79})\s*$")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_SECTION_TOKEN = re.compile(r"\d+(?:\.\d+){0,5}")
_SUBJECT_STRIP = re.compile(r"(?:功能|需求|能力)$")
_SUBJECT_SPLIT = re.compile(r"[，,。；;：:（(、和与及]")
_MIN_SEGMENT_CHARS = 6
_MAX_HEADING_LINE_CHARS = 92
_MIN_CONTAIN_CHARS = 3
_ALARM_CONTEXT = re.compile(r"报警|告警|警告|警报|异常流|提示")


@dataclass(frozen=True)
class QualificationRow:
    """合格性表数据行：(需求名称, 章节号, 方法)。方法为空值时不成行。"""

    name: str
    section: tuple[int, ...]
    method: str
    evidence_id: str
    row_index: int


@dataclass(frozen=True)
class CapabilityItem:
    """能力清单条目：能力表的(Use case名称, 项目唯一标识符)。"""

    name: str
    identifier: str
    evidence_id: str


@dataclass(frozen=True)
class SectionFact:
    """证据中出现过的章节：(章节元组, 标题, 证据引用)。"""

    section: tuple[int, ...]
    title: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class CoverageMap:
    """冻结证据的覆盖关系汇总（合格性行+章节事实+能力清单）。"""

    qual_rows: tuple[QualificationRow, ...]
    sections: tuple[SectionFact, ...]
    capabilities: tuple[CapabilityItem, ...]

    @property
    def qualification_evidence_ids(self) -> tuple[str, ...]:
        """含合格性行的证据块（去重保序）。"""
        return tuple(dict.fromkeys(
            row.evidence_id for row in self.qual_rows))

    def is_covered(self, section: tuple[int, ...]) -> bool:
        """章节被任一合格性行覆盖：行命中该章节或其祖先/后代路径。

        路径重叠（而非严格相等）是保守方向：容器章节3.2因子节3.2.1有行
        而判覆盖，避免open证据下的假refute；兄弟路径（3.2.1行不覆盖
        3.3）仍判缺口。
        """
        return any(
            row.section and _path_overlap(row.section, section)
            for row in self.qual_rows)

    def match_qualification(self, subject: str) -> QualificationRow | None:
        """精确断言主体与合格性行的匹配（标识符经能力清单间接解析）。"""
        for row in self.qual_rows:
            if _subject_hit(subject, row.name):
                return row
        capability = self.match_capability(subject)
        if capability is not None:
            for row in self.qual_rows:
                if _subject_hit(capability.name, row.name):
                    return row
        return None

    def match_capability(self, subject: str) -> CapabilityItem | None:
        """精确断言主体与能力清单名称/标识的匹配。"""
        for item in self.capabilities:
            if _subject_hit(subject, item.name) or (
                    item.identifier and _subject_hit(subject, item.identifier)):
                return item
        return None


@dataclass(frozen=True)
class CoverageClaim:
    """answer中的一条覆盖声明。kind: range/universal/precise/gjb_clause。"""

    kind: str
    check_id: str
    segment: str
    target: str = ""
    start: tuple[int, ...] = ()
    end: tuple[int, ...] = ()
    subject: str = ""
    elements: tuple[str, ...] = ()


def _parse_section(token: str) -> tuple[int, ...] | None:
    """章节号文本→整数元组（全角点号归一，非法形态返回None）。"""
    normalized = token.strip().replace("．", ".").replace("。", ".")
    if not re.fullmatch(r"\d+(?:\.\d+){0,5}", normalized):
        return None
    parts = tuple(int(part) for part in normalized.split("."))
    return parts if any(part for part in parts) else None


def _section_text(section: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in section)


def _prefix_of(short: tuple[int, ...], long: tuple[int, ...]) -> bool:
    return len(short) <= len(long) and long[:len(short)] == short


def _path_overlap(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return _prefix_of(a, b) or _prefix_of(b, a)


def _in_range(section: tuple[int, ...],
              start: tuple[int, ...], end: tuple[int, ...]) -> bool:
    """章节是否在声称范围内（start/end为空=全称，恒真）。

    端点深度截断比较：范围3.1~3.17既包含容器3.2的子节3.2.1，也包含
    端点3.17的子节3.17.1；数值分量比较避免"3.9>3.17"的字符串序陷阱。
    """
    if not start or not end:
        return True
    lower = section[:len(start)]
    upper = section[:len(end)]
    return start <= lower and upper <= end


def _norm_header(cell: str) -> str:
    return re.sub(r"[\s/（）()]", "", cell)


def _qual_columns(header: list[str]) -> tuple[int, int, int] | None:
    """合格性表列定位：(名称列, 章节号列, 方法列)；非合格性表返回None。"""
    joined = "；".join(header)
    if "合格性" not in joined:
        return None
    normalized = [_norm_header(cell) for cell in header]
    name_idx = next((index for index, cell in enumerate(normalized)
                     if "需求名称" in cell or "名称" in cell or "标识" in cell), 0)
    section_idx = next((index for index, cell in enumerate(normalized)
                        if "章节号" in cell), -1)
    method_idx = next((index for index, cell in enumerate(normalized)
                       if "合格性方法" in cell or "方法" in cell), -1)
    return name_idx, section_idx, method_idx


def _capability_columns(header: list[str]) -> tuple[int, int] | None:
    """能力表列定位：(名称列, 标识符列)；非能力表返回None。"""
    normalized = [_norm_header(cell) for cell in header]
    joined = "；".join(normalized)
    if "标识符" not in joined or "需求描述" not in joined:
        return None
    name_idx = next((index for index, cell in enumerate(normalized)
                     if "usecase" in cell.lower() or "名称" in cell), 0)
    id_idx = next((index for index, cell in enumerate(normalized)
                   if "标识符" in cell), 1)
    return name_idx, id_idx


def _cell(row: list[str], index: int) -> str:
    if 0 <= index < len(row):
        return row[index].strip()
    return ""


def _collect_section_text(text: str, evidence_id: str,
                          titles: dict[tuple[int, ...], str],
                          refs: dict[tuple[int, ...], set[str]]) -> None:
    """从一段文本（块原文/语句/source_ref.section）登记章节事实。"""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) > _MAX_HEADING_LINE_CHARS:
            continue
        match = _HEADING.match(stripped)
        if match is None:
            continue
        title = match.group("title").strip()
        if not _CJK.search(title):
            continue
        section = _parse_section(match.group("num"))
        if section is None:
            continue
        if section not in titles:
            titles[section] = title
        refs.setdefault(section, set()).add(evidence_id)


def _row_sections(row: list[str], section_idx: int) -> list[tuple[int, ...]]:
    """数据行章节号列的全部章节元组（单元格可含多个章节号）。"""
    if section_idx < 0 or section_idx >= len(row):
        return []
    sections: list[tuple[int, ...]] = []
    for token in _SECTION_TOKEN.findall(row[section_idx]):
        section = _parse_section(token)
        if section is not None:
            sections.append(section)
    return sections


def build_coverage_map(
        evidence: Iterable[RetrievedEvidence],
        statements: Iterable[EvidenceStatement] | None = None,
) -> CoverageMap:
    """从冻结证据构建覆盖关系（合格性行+章节事实+能力清单）。

    statements为linearize_context输出；缺省由evidence自动推导。
    章节事实来自块文本行、语句文本与source_ref.section的标题形态匹配，
    不做任何文件读取。
    """
    blocks = list(evidence)
    statement_list = (list(statements) if statements is not None
                      else linearize_context(tuple(blocks)))
    qual_rows: list[QualificationRow] = []
    capabilities: list[CapabilityItem] = []
    titles: dict[tuple[int, ...], str] = {}
    refs: dict[tuple[int, ...], set[str]] = {}
    for block in blocks:
        _collect_section_text(block.text, block.evidence_id, titles, refs)
        _collect_section_text(block.source_ref.section, block.evidence_id,
                              titles, refs)
        if "<table" not in block.text:
            continue
        rows = table_rows_positional(block.text)
        if not rows:
            continue
        header = rows[0]
        qual_columns = _qual_columns(header)
        if qual_columns is not None:
            name_idx, section_idx, method_idx = qual_columns
            for row_number, row in enumerate(rows[1:], start=2):
                if not any(cell.strip() for cell in row):
                    continue
                name = _cell(row, name_idx)
                method = _cell(row, method_idx)
                sections = _row_sections(row, section_idx)
                for section in sections:
                    refs.setdefault(section, set()).add(block.evidence_id)
                    if name and section not in titles:
                        titles[section] = name
                if not name or method in _EMPTY_CELL_VALUES:
                    # 方法列为空值：已知需求但无方法（覆盖缺口），不成行
                    continue
                qual_rows.append(QualificationRow(
                    name=name, section=sections[0] if sections else (),
                    method=method, evidence_id=block.evidence_id,
                    row_index=row_number))
            continue
        capability_columns = _capability_columns(header)
        if capability_columns is not None:
            name_idx, id_idx = capability_columns
            for row in rows[1:]:
                if not any(cell.strip() for cell in row):
                    continue
                name = _cell(row, name_idx)
                identifier = _cell(row, id_idx)
                if name or identifier:
                    capabilities.append(CapabilityItem(
                        name=name, identifier=identifier,
                        evidence_id=block.evidence_id))
    for statement in statement_list:
        _collect_section_text(statement.text, statement.evidence_id,
                              titles, refs)
    sections = tuple(
        SectionFact(section=section, title=titles[section],
                    evidence_ids=tuple(sorted(refs[section])))
        for section in sorted(titles))
    return CoverageMap(
        qual_rows=tuple(qual_rows), sections=sections,
        capabilities=tuple(capabilities))


def _norm_subject(text: str) -> str:
    return re.sub(r"\s+", "", _SUBJECT_STRIP.sub("", text.strip()))


def _subject_hit(subject: str, name: str) -> bool:
    """主体与行名称/标识匹配：相等（≥2字符）或包含（较短侧≥3字符）。"""
    left = _norm_subject(subject)
    right = _norm_subject(name)
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    return len(shorter) >= _MIN_CONTAIN_CHARS and shorter in longer


def _subject_before_target(segment: str, target: str) -> str:
    """精确断言主体：被覆盖物之前的动词再之前的末段名词短语。"""
    target_pos = segment.find(target)
    if target_pos <= 0:
        return ""
    before = segment[:target_pos]
    verb_match = None
    for match in _PRECISE_VERB.finditer(before):
        verb_match = match
    if verb_match is None:
        return ""
    head = before[:verb_match.start()]
    parts = [part.strip() for part in _SUBJECT_SPLIT.split(head)]
    subject = _norm_subject(parts[-1]) if parts else ""
    if subject in _cfg().generic_subjects:
        return ""
    if not re.search(r"[\u4e00-\u9fffA-Za-z]", subject):
        return ""
    return subject if 2 <= len(subject) <= 24 else ""


def _asserted_elements(segment: str) -> tuple[str, ...]:
    """answer断言的报警要素（按alarm_elements封闭清单逐项命中）。"""
    return tuple(
        label for label, synonyms in _cfg().alarm_elements
        if any(synonym in segment for synonym in synonyms))


def _qual_claim(segment: str, target: str) -> CoverageClaim | None:
    """合格性覆盖声明分类：范围 > 全称 > 精确断言。"""
    if _cfg().absence_re.search(segment):
        return None
    if _OBJECT.search(segment) is None or _COVER_VERB.search(segment) is None:
        return None
    range_match = _RANGE.search(segment)
    if range_match is not None:
        start = _parse_section(range_match.group("start"))
        end = _parse_section(range_match.group("end"))
        if start is None or end is None or start > end:
            return None
        return CoverageClaim(kind="range", check_id="GJB-01", segment=segment,
                             target=target, start=start, end=end)
    if _UNIVERSAL.search(segment) is not None:
        return CoverageClaim(kind="universal", check_id="GJB-01",
                             segment=segment, target=target)
    subject = _subject_before_target(segment, target)
    if subject:
        return CoverageClaim(kind="precise", check_id="GJB-01", segment=segment,
                             target=target, subject=subject)
    return None


def _gjb_clause_claims(answer: str) -> list[CoverageClaim]:
    """③GJB条款覆盖声明：复用gjb_presence封闭清单触发词，仅正极性。"""
    claims: list[CoverageClaim] = []
    for check, polarity, segment, hits in _answer_gjb_claims(answer):
        if check.check_id not in _CLAUSE_CHECK_IDS or polarity != "present":
            continue
        elements = (_asserted_elements(segment)
                    if check.check_id == "GJB-06" else ())
        claims.append(CoverageClaim(
            kind="gjb_clause", check_id=check.check_id, segment=segment,
            target="、".join(hits), elements=elements))
    return claims


def extract_coverage_claims(answer: str) -> list[CoverageClaim]:
    """提取answer中的覆盖声明（无声明时为空列表）。"""
    claims: list[CoverageClaim] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_segment in _SEGMENT_SPLIT.split(answer):
        segment = raw_segment.strip()
        if len(segment) < _MIN_SEGMENT_CHARS:
            continue
        target = next((term for term in _cfg().qualification_targets
                       if term in segment), "")
        if not target:
            continue
        claim = _qual_claim(segment, target)
        if claim is None:
            continue
        key = (claim.kind, claim.check_id,
               claim.subject or f"{_section_text(claim.start)}"
                                f"-{_section_text(claim.end)}")
        if key in seen:
            continue
        seen.add(key)
        claims.append(claim)
    claims.extend(_gjb_clause_claims(answer))
    return claims


def _section_label(fact: SectionFact) -> str:
    return f"{_section_text(fact.section)} {fact.title}".strip()


def _scope_text(claim: CoverageClaim) -> str:
    if claim.kind == "range":
        return (f"{_section_text(claim.start)}至"
                f"{_section_text(claim.end)}章节")
    return "全部（所有章节）"


def _result(request: QAInput, claim: CoverageClaim, order: int,
            verdict: Verdict, refs: Iterable[str], rationale: str,
            confidence: float, routed: tuple[str, ...]) -> ClaimResult:
    route_note = (f"；question路由命中{claim.check_id}"
                  if claim.check_id in routed else "")
    return ClaimResult(
        claim_id=f"{request.instance_id}-cov{order:02d}",
        claim_text=claim.segment,
        verdict=verdict,
        check_item_candidates=(claim.check_id,),
        evidence_refs=tuple(sorted(set(refs))),
        rationale=rationale + route_note,
        method=METHOD,
        confidence=confidence,
    )


def _check_scope_claim(request: QAInput, claim: CoverageClaim,
                       coverage: CoverageMap, order: int,
                       routed: tuple[str, ...]) -> ClaimResult:
    """①逐章覆盖比对：范围/全称声明 vs 合格性表覆盖缺口。"""
    if not coverage.qual_rows:
        return _result(
            request, claim, order, "not_in_evidence", (),
            f"GJB-01覆盖比对：answer声称{_scope_text(claim)}的需求均有"
            f"{claim.target}，但冻结证据不含任何合格性行，无法逐章核对"
            f"全覆盖声明", 0.0, routed)
    in_scope = [fact for fact in coverage.sections
                if _in_range(fact.section, claim.start, claim.end)]
    if not in_scope:
        return _result(
            request, claim, order, "not_in_evidence", (),
            f"GJB-01覆盖比对：answer声称范围{_scope_text(claim)}内未能从"
            f"冻结证据推导出任何已知章节，无法比对覆盖缺口", 0.0, routed)
    gaps = [fact for fact in in_scope
            if not coverage.is_covered(fact.section)]
    covered_labels = "、".join(
        _section_text(row.section) for row in coverage.qual_rows
        if _in_range(row.section, claim.start, claim.end))
    if gaps:
        gap_labels = "、".join(_section_label(fact) for fact in gaps)
        refs = list(coverage.qualification_evidence_ids) + [
            evidence_id for fact in gaps
            for evidence_id in fact.evidence_ids]
        return _result(
            request, claim, order, "refute", refs,
            f"GJB-01覆盖比对：answer声称{_scope_text(claim)}的需求均有"
            f"{claim.target}，冻结证据合格性行仅覆盖[{covered_labels or '无'}]，"
            f"声称范围内已知章节[{gap_labels}]存在但无对应合格性行——"
            f"覆盖缺口{len(gaps)}项，全覆盖声明被反驳", 0.9, routed)
    scope_labels = "、".join(_section_text(fact.section) for fact in in_scope)
    return _result(
        request, claim, order, "support",
        coverage.qualification_evidence_ids,
        f"GJB-01覆盖比对：answer声称{_scope_text(claim)}的需求均有"
        f"{claim.target}，范围内已知章节[{scope_labels}]均在合格性行覆盖内，"
        f"无覆盖缺口", 0.9, routed)


def _check_precise_claim(request: QAInput, claim: CoverageClaim,
                         coverage: CoverageMap, order: int,
                         routed: tuple[str, ...]) -> ClaimResult:
    """②精确断言核对：X功能有合格性规定。"""
    if not coverage.qual_rows and not coverage.capabilities:
        return _result(
            request, claim, order, "not_in_evidence", (),
            f"GJB-01精确断言：answer声称[{claim.subject}]有{claim.target}，"
            f"但冻结证据既无合格性行也无能力清单，无法核对", 0.0, routed)
    row = coverage.match_qualification(claim.subject)
    if row is not None:
        return _result(
            request, claim, order, "support", (row.evidence_id,),
            f"GJB-01精确断言：answer声称[{claim.subject}]有{claim.target}，"
            f"合格性行[{row.name}@{_section_text(row.section)}方法{row.method}]"
            f"命中声称主体", 0.9, routed)
    capability = coverage.match_capability(claim.subject)
    if capability is not None:
        refs = [capability.evidence_id, *coverage.qualification_evidence_ids]
        label = capability.name or capability.identifier
        return _result(
            request, claim, order, "refute", refs,
            f"GJB-01精确断言：answer声称[{claim.subject}]有{claim.target}，"
            f"冻结证据能力清单含[{label}]但合格性行无其记录——该需求无"
            f"合格性方法，覆盖缺口", 0.9, routed)
    return _result(
        request, claim, order, "not_in_evidence", (),
        f"GJB-01精确断言：answer声称[{claim.subject}]有{claim.target}，"
        f"声称主体不在冻结证据合格性行/能力清单中，无法核对", 0.0, routed)


def _check_alarm_elements(request: QAInput, claim: CoverageClaim,
                          statements: list[EvidenceStatement], order: int,
                          routed: tuple[str, ...]) -> ClaimResult | None:
    """GJB-06逐要素比对：证据报警语句缺失任一声称要素→refute。

    无报警相关语句时返回None回退条款级审计（与gjb_presence同一封闭
    清单语义）。
    """
    contexts = [statement for statement in statements
                if _ALARM_CONTEXT.search(statement.text)]
    if not contexts:
        return None
    context_ids = [statement.evidence_id for statement in contexts]
    missing = tuple(
        label for label in claim.elements
        if not any(synonym in statement.text for statement in contexts
                   for synonym in _cfg().alarm_synonyms[label]))
    if missing:
        return _result(
            request, claim, order, "refute", context_ids,
            f"GJB-06要素覆盖：answer声称报警信息包含"
            f"[{'、'.join(claim.elements)}]，冻结证据报警相关语句缺失要素"
            f"[{'、'.join(missing)}]——要素覆盖缺口", 0.9, routed)
    return _result(
        request, claim, order, "support", context_ids,
        f"GJB-06要素覆盖：answer声称报警信息包含"
        f"[{'、'.join(claim.elements)}]，证据报警相关语句均含声称要素",
        0.9, routed)


def _check_gjb_clause_claim(request: QAInput, claim: CoverageClaim,
                            audit: GjbPresenceAudit,
                            statements: list[EvidenceStatement], order: int,
                            routed: tuple[str, ...]) -> ClaimResult:
    """③GJB条款覆盖声明（GJB-04审计日志/GJB-06报警要素，正极性）。"""
    check = _CHECK_BY_ID[claim.check_id]
    state = audit.by_check_id()[claim.check_id]
    labels = "、".join(component.label for component in check.components)
    if claim.elements:
        element_result = _check_alarm_elements(
            request, claim, statements, order, routed)
        if element_result is not None:
            return element_result
    if state.is_present:
        present_labels = "、".join(state.present)
        return _result(
            request, claim, order, "support", state.evidence_refs,
            f"{claim.check_id}{check.name}：冻结证据含[{present_labels}]，"
            f"answer提供/覆盖声称（{claim.target}）成立", 0.9, routed)
    return _result(
        request, claim, order, "refute", state.evidence_refs,
        f"{claim.check_id}{check.name}：封闭清单要求[{labels}]，冻结证据无"
        f"该条款内容，answer声称提供（{claim.target}）被反驳", 0.9, routed)


def verify_coverage(
        request: QAInput,
        statements: Iterable[EvidenceStatement] | None = None,
) -> list[ClaimResult]:
    """校验answer的覆盖完备声明（L1确定性，method="coverage_join"）。

    answer不含覆盖声明（范围/全称/精确合格性声明、GJB-04/06正极性
    条款声明）时返回[]，不产生审计噪音。
    """
    blocks = list(request.evidence)
    if not blocks:
        return []
    statement_list = (list(statements) if statements is not None
                      else linearize_context(tuple(blocks)))
    coverage = build_coverage_map(tuple(blocks), statement_list)
    audit = audit_gjb_presence(blocks, statement_list)
    routed = tuple(item for item in route_question(request.question)
                   if item in _CHECK_ID_SET)
    results: list[ClaimResult] = []
    for order, claim in enumerate(extract_coverage_claims(request.answer),
                                  start=1):
        if claim.kind in ("range", "universal"):
            result = _check_scope_claim(request, claim, coverage, order,
                                        routed)
        elif claim.kind == "precise":
            result = _check_precise_claim(request, claim, coverage, order,
                                          routed)
        else:
            result = _check_gjb_clause_claim(
                request, claim, audit, statement_list, order, routed)
        results.append(result)
    return results


__all__ = [
    "CHECK_ITEMS",
    "CapabilityItem",
    "CoverageClaim",
    "CoverageMap",
    "METHOD",
    "QualificationRow",
    "SectionFact",
    "build_coverage_map",
    "extract_coverage_claims",
    "verify_coverage",
]
