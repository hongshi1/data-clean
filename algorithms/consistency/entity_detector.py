"""L0 entity detection layer for cascaded QA verification.

Position in the cascade: layer 0, before the rule layer. Fully deterministic
(regex + counting only, no model calls, no I/O). Three jobs:

1. Entity extraction (``extract_entities``): domain terms (BLOB/SQL/...),
   PZXQ identifiers, stopword-filtered Chinese runs, quoted terms and mixed
   domain-term+Chinese surfaces (e.g. "BLOB数据插入").
2. Document lexicon freezing (``build_document_lexicon``): frozen evidence
   statements -> capability names / use-case names / interface ids /
   方式名称 and 运行状态 value domains / database names / bracketed alias
   pairs such as 大字段(BLOB) or E1(异常流).
3. Term-level conflict detection (``detect_term_conflicts``):
    TERM-01 同义异名 (warning), TERM-02 同名异义/定义互换 (refute),
    TERM-05 指令/用例名错配 (support or refute), TERM-07 接口标识冲突
    (refute, 全证据命中护栏见_check_interface_ids), TERM-08 缩写不一致
    (warning).

Warning-level reports carry verdict="support" with a ":warning" method
suffix so downstream layers can filter or downgrade them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from algorithms.consistency.answer_structure import StructuredClaim
from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.qa_models import ClaimResult, QAInput, Verdict

EntityKind = Literal["domain_term", "pzxq_id", "chinese", "quoted", "mixed"]
LinkType = Literal["exact", "alias", "prefix", "nil"]

DOMAIN_TERMS: frozenset[str] = frozenset(
    {"BLOB", "SQL", "JSON", "INT", "STRING", "FLOAT", "LOB", "DML", "API"})

CHINESE_STOPWORDS: frozenset[str] = frozenset({
    "的", "了", "是", "在", "和", "与", "或", "及", "等", "系统", "软件", "服务",
    "进行", "描述", "需要", "可以", "必须", "应当", "提供", "使用", "数据", "信息",
    "接口", "功能", "需求", "规格", "说明", "文档", "项目", "唯一", "标识", "名称",
    "方式", "状态", "阶段", "开发", "运行",
})

_DOMAIN_TERM_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:BLOB|SQL|JSON|INT|STRING|FLOAT|LOB|DML|API)(?![A-Za-z0-9])")
_MIXED_TERM_RE = re.compile(
    r"(?:BLOB|SQL|JSON|INT|STRING|FLOAT|LOB|DML|API)[\u4e00-\u9fff]{1,8}")
PZXQ_ID_RE = re.compile(r"PZXQ-[A-Z0-9-]+")
_CHINESE_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_QUOTED_TERM_RE = re.compile(r"[「\"『]([^「」\"『』]+)[」\"』]")

_IDENTIFIER_STATEMENT_RE = re.compile(
    r"^(?P<name>.+?)的项目唯一标识符[：:](?P<id>PZXQ-[A-Z0-9-]+)$")
_ENUM_SPLIT_RE = re.compile(r"[、,，/]")
_ENUM_LIST_RE = re.compile(
    r"(?:包括|包含|划分为|分为)(?:以下)?[：:]?(?P<items>[^，。；!,\n]{4,120})")
_ENUM_LIST_FIELDS = ("sentence", "需求描述", "标识符")
_STATUS_TOKENS = ("运行阶段", "开发阶段")
_DATABASE_RE = re.compile(r"达梦(?:数据库)?\s*(?:V[\d.]+)?|sqlite\d*", re.IGNORECASE)
_ALIAS_FORWARD_RE = re.compile(
    r"([\u4e00-\u9fffA-Za-z]{2,12})[（(]([A-Za-z0-9]{2,12})[）)]")
_ALIAS_REVERSE_RE = re.compile(
    r"([A-Za-z0-9]{1,10})[（(]([\u4e00-\u9fff]{2,10})[）)]")
_DEFINITION_PAIR_RE = re.compile(
    r"([A-Za-z\u4e00-\u9fff]{1,12})[（(]([^（）()]{1,24})[）)]")

_USECASE_MENTION_RE = re.compile(
    r"(?:调用|执行|触发|发出)(?:「(?P<quoted>[^「」]{2,16})」"
    r"|(?P<bare>[\u4e00-\u9fffA-Za-z0-9]{2,12}?))"
    r"(?=指令|用例|功能|接口|操作|服务|流程|，|。|；|！|、)")
_USECASE_VERBS = ("插入", "删除", "修改", "查询", "管理", "转换", "绑定", "输出",
                  "获取", "变更", "授权", "统计", "审计", "初始化", "连接", "生成",
                  "更新", "配置", "释放")
_USECASE_OBJECTS = ("数据", "对象", "字典", "类型", "数组", "错误", "权限", "用户",
                    "配置", "资源", "代码", "缓存", "连接", "池")
_USECASE_FIELDS = {"前置条件", "后置条件", "简要说明", "参与者",
                   "系统的动作", "Actor的动作", "动作约束"}

_STRIP_PREFIX_WORDS = ("提供", "支持", "包括", "包含", "使用", "通过", "采用", "调用",
                       "执行", "触发", "发出", "对于", "如果", "例如", "以及", "系统",
                       "软件", "服务", "进行", "描述", "需要", "可以", "必须", "应当",
                       "和", "及", "或", "与")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _strip_leading_prefixes(surface: str) -> str:
    """Trim leading verb/connective prefixes: 提供大字段（BLOB） -> 大字段."""
    stripped = surface
    while True:
        for prefix in _STRIP_PREFIX_WORDS:
            remainder = stripped[len(prefix):]
            if stripped.startswith(prefix) and len(remainder) >= 2:
                stripped = remainder
                break
        else:
            return stripped


@dataclass(frozen=True)
class Entity:
    """One extracted surface form with its kind and source span."""

    surface: str
    kind: EntityKind
    start: int
    end: int


@dataclass(frozen=True)
class AliasPair:
    """A bracketed alias pair observed in the evidence, e.g. 大字段(BLOB)."""

    surface: str
    target: str


@dataclass
class DocumentLexicon:
    """Known entities frozen from one SRS document's evidence statements."""

    capability_names: tuple[str, ...] = ()
    usecase_names: tuple[str, ...] = ()
    interface_ids: tuple[str, ...] = ()
    mode_values: tuple[str, ...] = ()
    status_values: tuple[str, ...] = ()
    database_names: tuple[str, ...] = ()
    alias_pairs: tuple[AliasPair, ...] = ()

    def __post_init__(self) -> None:
        self._exact: frozenset[str] = frozenset(
            self.capability_names + self.usecase_names + self.mode_values
            + self.status_values + self.database_names)
        self._sorted_terms: tuple[str, ...] = tuple(
            sorted(self._exact, key=len, reverse=True))
        self._alias_map: dict[str, str] = {}
        for pair in self.alias_pairs:
            self._alias_map.setdefault(pair.surface, pair.target)
        self._id_set: frozenset[str] = frozenset(self.interface_ids)

    @property
    def exact_terms(self) -> frozenset[str]:
        return self._exact

    @property
    def sorted_terms(self) -> tuple[str, ...]:
        return self._sorted_terms

    @property
    def alias_map(self) -> dict[str, str]:
        return self._alias_map

    @property
    def interface_id_set(self) -> frozenset[str]:
        return self._id_set


@dataclass(frozen=True)
class LinkResult:
    """The outcome of linking one answer entity to the document lexicon."""

    entity: Entity
    link_type: LinkType
    target: str
    confidence: float


def extract_entities(text: str) -> list[Entity]:
    """Extract domain terms, PZXQ ids, Chinese runs, quoted and mixed terms.

    Chinese runs equal to a stopword are dropped; results are deduplicated
    by (surface, kind) and ordered by source position.
    """
    entities: list[Entity] = []
    for match in _DOMAIN_TERM_RE.finditer(text):
        entities.append(Entity(match.group(0), "domain_term", match.start(), match.end()))
    for match in PZXQ_ID_RE.finditer(text):
        entities.append(Entity(match.group(0), "pzxq_id", match.start(), match.end()))
    for match in _CHINESE_RUN_RE.finditer(text):
        surface = match.group(0)
        if surface not in CHINESE_STOPWORDS:
            entities.append(Entity(surface, "chinese", match.start(), match.end()))
    for match in _QUOTED_TERM_RE.finditer(text):
        surface = match.group(1)
        if surface and surface not in CHINESE_STOPWORDS:
            entities.append(Entity(surface, "quoted", match.start() + 1, match.end() - 1))
    for match in _MIXED_TERM_RE.finditer(text):
        entities.append(Entity(match.group(0), "mixed", match.start(), match.end()))
    unique: dict[tuple[str, str], Entity] = {}
    for entity in entities:
        unique.setdefault((entity.surface, entity.kind), entity)
    return sorted(unique.values(), key=lambda e: (e.start, e.end))


def _is_usecase_field(field_name: str) -> bool:
    return (field_name.startswith("Use") or field_name.startswith("Actor")
            or field_name.startswith("异常流")
            or field_name in _USECASE_FIELDS)


def _status_values(value: str) -> list[str]:
    found = [token for token in _STATUS_TOKENS if token in value]
    if found:
        return found
    return [piece.strip() for piece in _ENUM_SPLIT_RE.split(value) if piece.strip()]


def _normalize_db_name(raw: str) -> str:
    name = raw.replace(" ", "").replace("数据库", "")
    return name or raw


def _valid_alias_pair(surface: str, target: str) -> bool:
    if surface == target or surface in CHINESE_STOPWORDS or target in CHINESE_STOPWORDS:
        return False
    if surface.isdigit() or target.isdigit():
        return False
    return bool(surface.strip()) and bool(target.strip())


def build_document_lexicon(
        evidence_statements: list[EvidenceStatement]) -> DocumentLexicon:
    """Freeze one document's known entities from its evidence statements.

    Capability vs use-case names come from three sources: identifier
    statements (PZXQ-GN-XXX = capability, deeper ids = use case), use-case
    table field statements (Use Case 名称 / 前置条件 / 异常流...), and
    enumeration lists in prose (X包括A、B、C / 划分为A、B及C) which recover
    sub-table names lost to empty leading cells.
    """
    name_class: dict[str, str] = {}
    interface_ids: list[str] = []
    mode_values: list[str] = []
    status_values: list[str] = []
    for statement in evidence_statements:
        identifier_match = _IDENTIFIER_STATEMENT_RE.match(statement.text)
        if identifier_match:
            name = identifier_match.group("name")
            identifier = identifier_match.group("id")
            if re.fullmatch(r"[A-Z0-9-]+", name):
                continue
            if identifier not in interface_ids:
                interface_ids.append(identifier)
            depth = identifier.count("-") + 1
            name_class.setdefault(name, "capability" if depth <= 3 else "usecase")
            continue
        if _is_usecase_field(statement.field_name) and statement.scope_key:
            name_class.setdefault(statement.scope_key, "usecase")
        elif statement.field_name == "方式名称":
            value = statement.text.rsplit("：", 1)[-1]
            mode_values.extend(
                piece.strip() for piece in _ENUM_SPLIT_RE.split(value)
                if piece.strip() and re.search(r"[\u4e00-\u9fff]", piece)
                and not re.fullmatch(r"(?:运行阶段|开发阶段)+", piece.strip()))
        elif statement.field_name == "运行状态":
            status_values.extend(
                piece for piece in _status_values(statement.text.rsplit("：", 1)[-1])
                if re.search(r"[\u4e00-\u9fff]", piece))
    for statement in evidence_statements:
        for identifier in PZXQ_ID_RE.findall(statement.text):
            if identifier not in interface_ids:
                interface_ids.append(identifier)
    for statement in evidence_statements:
        if statement.field_name not in _ENUM_LIST_FIELDS:
            continue
        for match in _ENUM_LIST_RE.finditer(statement.text):
            for raw in re.split(r"[、及和]", match.group("items")):
                item = _strip_leading_prefixes(raw.strip())
                if item.endswith("功能") and len(item) > 4:
                    item = item[:-2]
                if (3 <= len(item) <= 20 and re.search(r"[\u4e00-\u9fff]", item)
                        and item not in CHINESE_STOPWORDS):
                    name_class.setdefault(item, "usecase")

    database_names: list[str] = []
    alias_pairs: list[AliasPair] = []
    seen_pairs: set[tuple[str, str]] = set()
    for statement in evidence_statements:
        for raw in _DATABASE_RE.findall(statement.text):
            name = _normalize_db_name(raw)
            if name and name not in database_names:
                database_names.append(name)
        for raw_surface, inner in _ALIAS_FORWARD_RE.findall(statement.text):
            surface = _strip_leading_prefixes(raw_surface)
            if _valid_alias_pair(surface, inner) and (surface, inner) not in seen_pairs:
                seen_pairs.add((surface, inner))
                alias_pairs.append(AliasPair(surface=surface, target=inner))
        for outer, inner in _ALIAS_REVERSE_RE.findall(statement.text):
            if _valid_alias_pair(outer, inner) and (outer, inner) not in seen_pairs:
                seen_pairs.add((outer, inner))
                alias_pairs.append(AliasPair(surface=outer, target=inner))

    return DocumentLexicon(
        capability_names=tuple(n for n, c in name_class.items() if c == "capability"),
        usecase_names=tuple(n for n, c in name_class.items() if c == "usecase"),
        interface_ids=tuple(interface_ids),
        mode_values=tuple(dict.fromkeys(mode_values)),
        status_values=tuple(dict.fromkeys(status_values)),
        database_names=tuple(database_names),
        alias_pairs=tuple(alias_pairs),
    )


def _common_prefix_len(a: str, b: str) -> int:
    count = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        count += 1
    return count


def _prefix_match(surface: str, term: str) -> bool:
    if len(surface) < 2 or len(term) < 3:
        return False
    if surface in term or term in surface:
        return True
    common = _common_prefix_len(surface, term)
    return common >= 4 and common * 2 >= min(len(surface), len(term))


def _best_prefix_target(surface: str, terms: tuple[str, ...]) -> str:
    """Pick the term with the longest common prefix among prefix matches."""
    best, best_key = "", (-1, -1)
    for term in terms:
        if not _prefix_match(surface, term):
            continue
        key = (_common_prefix_len(surface, term), len(term))
        if key > best_key:
            best, best_key = term, key
    return best


def link_entities(entities: list[Entity],
                  lexicon: DocumentLexicon) -> list[LinkResult]:
    """Link answer entities to lexicon entries: exact / alias / prefix / nil."""
    results: list[LinkResult] = []
    for entity in entities:
        surface = entity.surface
        if entity.kind == "pzxq_id":
            if surface in lexicon.interface_id_set:
                results.append(LinkResult(entity, "exact", surface, 1.0))
            else:
                results.append(LinkResult(entity, "nil", "", 0.0))
            continue
        if surface in lexicon.exact_terms:
            results.append(LinkResult(entity, "exact", surface, 1.0))
            continue
        if surface in lexicon.alias_map:
            results.append(LinkResult(entity, "alias", lexicon.alias_map[surface], 0.85))
            continue
        target = _best_prefix_target(surface, lexicon.sorted_terms)
        if target:
            results.append(LinkResult(entity, "prefix", target, 0.6))
        else:
            results.append(LinkResult(entity, "nil", "", 0.0))
    return results


def _claim_result(claim: StructuredClaim, check_items: tuple[str, ...],
                  verdict: Verdict, evidence_refs: tuple[str, ...],
                  rationale: str, confidence: float, code: str, *,
                  warning: bool = False) -> ClaimResult:
    return ClaimResult(
        claim_id=claim.claim_id,
        claim_text=claim.text,
        verdict=verdict,
        check_item_candidates=check_items,
        evidence_refs=evidence_refs,
        rationale=rationale,
        method=f"l0_entity_detector:{code}" + (":warning" if warning else ""),
        confidence=confidence,
    )


def _scope_statements(claim: StructuredClaim,
                      statements: list[EvidenceStatement]) -> list[EvidenceStatement]:
    scope = _compact(claim.scope_hint)
    if scope:
        matched = [s for s in statements
                   if s.scope_key
                   and (scope in _compact(s.scope_key) or _compact(s.scope_key) in scope)]
        if matched:
            return matched
    return statements


def _id_segments(identifier: str) -> list[str]:
    return identifier.split("-")


def _same_id_family(a: str, b: str) -> bool:
    segments_a, segments_b = _id_segments(a), _id_segments(b)
    if len(segments_a) < 3 or len(segments_b) < 3:
        return False
    return segments_a[:-1] == segments_b[:-1] and segments_a[-1] != segments_b[-1]


def _id_prefix_of(a: str, b: str) -> bool:
    segments_a, segments_b = _id_segments(a), _id_segments(b)
    return len(segments_a) < len(segments_b) and segments_b[:len(segments_a)] == segments_a


def _check_interface_ids(claim: StructuredClaim,
                         scoped_statements: list[EvidenceStatement],
                         all_statements: list[EvidenceStatement],
                         ) -> list[ClaimResult]:
    """TERM-07 接口标识冲突（含全证据命中优先护栏, G4 P1 a-fix）.

    - claim的ID在scope语句中出现 → support;
    - claim的ID在冻结证据全文（all_statements）中逐字出现（仅在scope
      之外，如同标识表的兄弟行/节标题）→ support：ID真实存在，主体
      归属仲裁是id_join专家（subject-ID绑定）的职责，scope侧的同族
      ID不构成"answer使用了假标识"（S1QA-053：answer复述标识表时
      兄弟行的SJXG曾因scope包含式拉入父级行被判错配）;
    - scope同族冲突 → refute（answer使用了evidence中不存在的同族ID）;
    - 前缀缩短 → TERM-08 warning; 其余 → NIE。
    """
    claim_ids = sorted({e.surface for e in extract_entities(claim.text)
                        if e.kind == "pzxq_id"})
    if not claim_ids:
        return []
    evidence_id_refs: dict[str, list[str]] = {}
    for statement in scoped_statements:
        for identifier in PZXQ_ID_RE.findall(statement.text):
            evidence_id_refs.setdefault(identifier, []).append(statement.statement_id)
    full_id_refs: dict[str, list[str]] = {}
    for statement in all_statements:
        for identifier in PZXQ_ID_RE.findall(statement.text):
            full_id_refs.setdefault(identifier, []).append(statement.statement_id)
    results: list[ClaimResult] = []
    for identifier in claim_ids:
        if identifier in evidence_id_refs:
            results.append(_claim_result(
                claim, ("TERM-07",), "support",
                tuple(evidence_id_refs[identifier][:2]),
                f"answer的接口标识{identifier}与evidence一致", 0.9, "TERM-07"))
            continue
        if identifier in full_id_refs:
            results.append(_claim_result(
                claim, ("TERM-07",), "support",
                tuple(full_id_refs[identifier][:2]),
                f"answer的接口标识{identifier}在evidence中登记"
                f"（位于claim scope外：{full_id_refs[identifier][0]}），"
                f"标识存在；主体绑定归属由id_join仲裁", 0.85, "TERM-07"))
            continue
        conflicting = [e for e in evidence_id_refs if _same_id_family(identifier, e)]
        if conflicting:
            other = conflicting[0]
            results.append(_claim_result(
                claim, ("TERM-07",), "refute", tuple(evidence_id_refs[other][:2]),
                f"evidence规定接口标识{other}，answer却使用{identifier}（接口标识冲突）",
                0.95, "TERM-07"))
            continue
        shortened = [e for e in evidence_id_refs
                     if _id_prefix_of(identifier, e) or _id_prefix_of(e, identifier)]
        if shortened:
            other = shortened[0]
            results.append(_claim_result(
                claim, ("TERM-08",), "support", tuple(evidence_id_refs[other][:2]),
                f"answer使用标识符{identifier}，evidence使用{other}（缩写不一致）",
                0.7, "TERM-08", warning=True))
            continue
        results.append(_claim_result(
            claim, ("TERM-07",), "not_in_evidence", (),
            f"answer的接口标识{identifier}未在evidence中出现", 0.6, "TERM-07"))
    return results


def _check_definitions(claim: StructuredClaim,
                       statements: list[EvidenceStatement]) -> list[ClaimResult]:
    claim_pairs = _DEFINITION_PAIR_RE.findall(claim.text)
    if not claim_pairs:
        return []
    claim_pairs = [(_strip_leading_prefixes(term), definition)
                   for term, definition in claim_pairs]
    evidence_defs: dict[str, dict[str, str]] = {}
    for statement in statements:
        for raw_term, definition in _DEFINITION_PAIR_RE.findall(statement.text):
            term = _strip_leading_prefixes(raw_term)
            evidence_defs.setdefault(term, {}).setdefault(definition, statement.statement_id)
    results: list[ClaimResult] = []
    for term, definition in claim_pairs:
        if len(term) < 2 or term in CHINESE_STOPWORDS:
            continue
        defs = evidence_defs.get(term)
        if not defs:
            continue
        # ASCII definitions (db names/tech terms) differ only by case:
        # sqlite3 vs SQLite3 is the same product, not a definition swap
        if definition.casefold() in {d.casefold() for d in defs}:
            continue
        evidence_definition = next(iter(defs))
        swapped = [t for t, d in evidence_defs.items()
                   if definition.casefold() in {x.casefold() for x in d}
                   and t != term]
        rationale = (f"evidence将「{term}」定义为「{evidence_definition}」，"
                     f"answer却定义为「{definition}」（同名异义）")
        if swapped:
            rationale += f"；该定义实为「{swapped[0]}」的定义（定义互换）"
        results.append(_claim_result(
            claim, ("TERM-02",), "refute", (defs[evidence_definition],),
            rationale, 0.9, "TERM-02"))
    return results


def _usecase_mentions(text: str) -> list[str]:
    mentions: list[str] = []
    for match in _USECASE_MENTION_RE.finditer(text):
        mention = (match.group("quoted") or match.group("bare") or "").strip()
        if mention and mention not in mentions:
            mentions.append(mention)
    return mentions


def _usecase_like(mention: str) -> bool:
    return (any(mention.endswith(verb) for verb in _USECASE_VERBS)
            and any(obj in mention for obj in _USECASE_OBJECTS))


def _overlap_score(a: str, b: str) -> float:
    set_a, set_b = set(_compact(a)), set(_compact(b))
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / min(len(set_a), len(set_b))


def _usecase_match(a: str, b: str) -> bool:
    compact_a, compact_b = _compact(a), _compact(b)
    if not compact_a or not compact_b:
        return False
    if compact_a == compact_b:
        return True
    if len(compact_a) >= 2 and len(compact_b) >= 2:
        if compact_a in compact_b or compact_b in compact_a:
            return True
    return _overlap_score(compact_a, compact_b) >= 0.75


def _check_usecase_mentions(request: QAInput, claim: StructuredClaim,
                            statements: list[EvidenceStatement],
                            lexicon: DocumentLexicon) -> list[ClaimResult]:
    """TERM-05: 指令/用例名错配.

    Same use case (verbatim hit, containment or char-set overlap >= 0.75,
    e.g. 数据插入 vs 插入数据) -> support; a use-case-like mention that
    matches nothing -> refute.
    """
    mentions = _usecase_mentions(claim.text)
    if not mentions:
        return []
    names = lexicon.usecase_names + lexicon.capability_names
    question_text = _compact(request.question)
    results: list[ClaimResult] = []
    for mention in mentions:
        mention_compact = _compact(mention)
        hit = [s for s in statements
               if mention_compact and mention_compact in _compact(s.text)]
        if hit:
            results.append(_claim_result(
                claim, ("TERM-05",), "support",
                tuple(s.statement_id for s in hit[:2]),
                f"answer提到的指令/用例「{mention}」在evidence中明确出现",
                0.85, "TERM-05"))
            continue
        matched = next((n for n in names if _usecase_match(mention_compact, n)), "")
        if matched:
            refs = tuple(s.statement_id for s in statements
                         if s.scope_key == matched)[:2]
            results.append(_claim_result(
                claim, ("TERM-05",), "support", refs,
                f"answer的用例「{mention}」与evidence用例「{matched}」"
                f"指向同一用例（前缀/字符重合匹配）", 0.8, "TERM-05"))
            continue
        if names and _usecase_like(mention_compact):
            best = max(names, key=lambda n: _overlap_score(mention_compact, n))
            topic = next((n for n in names if n in question_text), "")
            suffix = f"，question围绕「{topic}」" if topic else ""
            results.append(_claim_result(
                claim, ("TERM-05",), "refute", (),
                f"answer提到用例「{mention}」，与evidence用例「{best}」"
                f"完全不同（用例名错配）{suffix}", 0.9, "TERM-05"))
    return results


def _check_alias_preferences(claim: StructuredClaim,
                             evidence_statements: list[EvidenceStatement],
                             lexicon: DocumentLexicon) -> list[ClaimResult]:
    """TERM-01 同义异名 / TERM-08 缩写不一致 (both warning-level).

    Fires when the answer picks one side of an evidence alias pair while the
    evidence text itself clearly prefers the other side (higher count).
    Pairs involving a domain term (e.g. 大字段/BLOB) are TERM-01; other
    abbreviation pairs (E1/异常流, ORM/对象关系映射) are TERM-08.
    """
    claim_text = _compact(claim.text)
    if not claim_text:
        return []
    evidence_text = _compact(" ".join(s.text for s in evidence_statements))
    results: list[ClaimResult] = []
    for pair in lexicon.alias_pairs:
        if pair.surface in claim_text and pair.target not in claim_text:
            answer_form, evidence_form = pair.surface, pair.target
        elif pair.target in claim_text and pair.surface not in claim_text:
            answer_form, evidence_form = pair.target, pair.surface
        else:
            continue
        if evidence_text.count(evidence_form) <= evidence_text.count(answer_form):
            continue
        code = ("TERM-01" if evidence_form in DOMAIN_TERMS or answer_form in DOMAIN_TERMS
                else "TERM-08")
        label = "同义异名" if code == "TERM-01" else "缩写不一致"
        refs = tuple(s.statement_id for s in evidence_statements
                     if evidence_form in _compact(s.text))[:2]
        results.append(_claim_result(
            claim, (code,), "support", refs,
            f"answer用「{answer_form}」而evidence用「{evidence_form}」"
            f"（{label}，指向同一概念）", 0.7, code, warning=True))
    return results


def detect_term_conflicts(request: QAInput,
                          evidence_statements: list[EvidenceStatement],
                          claims: list[StructuredClaim]) -> list[ClaimResult]:
    """Run all five TERM checks over every answer claim (L0, deterministic)."""
    lexicon = build_document_lexicon(evidence_statements)
    results: list[ClaimResult] = []
    for claim in claims:
        scoped = _scope_statements(claim, evidence_statements)
        results.extend(_check_interface_ids(claim, scoped, evidence_statements))
        results.extend(_check_definitions(claim, scoped))
        results.extend(_check_usecase_mentions(request, claim, scoped, lexicon))
        results.extend(_check_alias_preferences(claim, evidence_statements, lexicon))
    return results


__all__ = [
    "AliasPair",
    "DocumentLexicon",
    "Entity",
    "LinkResult",
    "build_document_lexicon",
    "detect_term_conflicts",
    "extract_entities",
    "link_entities",
]
