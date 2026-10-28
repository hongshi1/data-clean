"""L0 entity detection layer for cascaded QA verification (config-driven).

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

配置/引擎分离: 场景知识(域术语/停用词/ID正则/值域/数据库名/别名模式/
用例动词宾语)全部来自NerLexicon(config/ner_lexicons/*.json), 本模块只
保留GJB结构通用逻辑——换一份配置即切换场景, 引擎代码不动. 词表来源:
调用方注入``lexicon``参数, 或模块级惰性默认场景srs_scene1.
``build_document_lexicon``保持从证据动态学习(运行时配置, 本就不硬编码).

Warning-level reports carry verdict="support" with a ":warning" method
suffix so downstream layers can filter or downgrade them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from algorithms.consistency.answer_structure import StructuredClaim
from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.ner_lexicon import (
    NerLexicon,
    NerPatterns,
    compile_patterns,
    default_lexicon,
)
from algorithms.consistency.qa_models import ClaimResult, QAInput, Verdict

EntityKind = Literal["domain_term", "pzxq_id", "chinese", "quoted", "mixed"]
LinkType = Literal["exact", "alias", "prefix", "nil"]

#: 引擎侧GJB结构通用正则(与场景无关, 不进lexicon配置)
_CHINESE_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_ENUM_SPLIT_RE = re.compile(r"[、,，/]")
_ENUM_LIST_RE = re.compile(
    r"(?:包括|包含|划分为|分为)(?:以下)?[：:]?(?P<items>[^，。；!,\n]{4,120})")
_ENUM_LIST_FIELDS = ("sentence", "需求描述", "标识符")
_USECASE_MENTION_RE = re.compile(
    r"(?:调用|执行|触发|发出)(?:「(?P<quoted>[^「」]{2,16})」"
    r"|(?P<bare>[\u4e00-\u9fffA-Za-z0-9]{2,12}?))"
    r"(?=指令|用例|功能|接口|操作|服务|流程|，|。|；|！|、)")


def _patterns(lexicon: NerLexicon | None = None) -> NerPatterns:
    """调用方注入的lexicon(或模块级默认场景)→编译好的模式包(带缓存)."""
    return compile_patterns(lexicon or default_lexicon())


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _strip_leading_prefixes(surface: str,
                            prefix_words: tuple[str, ...]) -> str:
    """Trim leading verb/connective prefixes: 提供大字段（BLOB） -> 大字段."""
    stripped = surface
    while True:
        for prefix in prefix_words:
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


def _extract_entities(text: str, p: NerPatterns) -> list[Entity]:
    """Gazetteer NER内核: 词典匹配(域词/ID/引号)+正则切分+停用词过滤."""
    entities: list[Entity] = []
    if p.domain_term_re is not None:
        for match in p.domain_term_re.finditer(text):
            entities.append(
                Entity(match.group(0), "domain_term", match.start(), match.end()))
    for match in p.id_re.finditer(text):
        entities.append(Entity(match.group(0), "pzxq_id", match.start(), match.end()))
    for match in _CHINESE_RUN_RE.finditer(text):
        surface = match.group(0)
        if surface not in p.stopwords:
            entities.append(Entity(surface, "chinese", match.start(), match.end()))
    for quote_re in p.quote_res:
        for match in quote_re.finditer(text):
            surface = match.group(1)
            if surface and surface not in p.stopwords:
                entities.append(
                    Entity(surface, "quoted", match.start(1), match.end(1)))
    if p.mixed_term_re is not None:
        for match in p.mixed_term_re.finditer(text):
            entities.append(Entity(match.group(0), "mixed", match.start(), match.end()))
    unique: dict[tuple[str, str], Entity] = {}
    for entity in entities:
        unique.setdefault((entity.surface, entity.kind), entity)
    return sorted(unique.values(), key=lambda e: (e.start, e.end))


def extract_entities(text: str,
                     lexicon: NerLexicon | None = None) -> list[Entity]:
    """Extract domain terms, PZXQ ids, Chinese runs, quoted and mixed terms.

    Chinese runs equal to a stopword are dropped; results are deduplicated
    by (surface, kind) and ordered by source position. ``lexicon``不注入时
    用模块级默认场景(srs_scene1).
    """
    return _extract_entities(text, _patterns(lexicon))


def _is_usecase_field(field_name: str,
                      usecase_fields: frozenset[str]) -> bool:
    return (field_name.startswith("Use") or field_name.startswith("Actor")
            or field_name.startswith("异常流")
            or field_name in usecase_fields)


def _status_values(value: str, status_tokens: tuple[str, ...]) -> list[str]:
    found = [token for token in status_tokens if token in value]
    if found:
        return found
    return [piece.strip() for piece in _ENUM_SPLIT_RE.split(value) if piece.strip()]


def _normalize_db_name(raw: str) -> str:
    name = raw.replace(" ", "").replace("数据库", "")
    return name or raw


def _valid_alias_pair(surface: str, target: str,
                      stopwords: frozenset[str]) -> bool:
    if surface == target or surface in stopwords or target in stopwords:
        return False
    if surface.isdigit() or target.isdigit():
        return False
    return bool(surface.strip()) and bool(target.strip())


def build_document_lexicon(
        evidence_statements: list[EvidenceStatement],
        lexicon: NerLexicon | None = None) -> DocumentLexicon:
    """Freeze one document's known entities from its evidence statements.

    Capability vs use-case names come from three sources: identifier
    statements (PZXQ-GN-XXX = capability, deeper ids = use case), use-case
    table field statements (Use Case 名称 / 前置条件 / 异常流...), and
    enumeration lists in prose (X包括A、B、C / 划分为A、B及C) which recover
    sub-table names lost to empty leading cells. 词表/模式来自``lexicon``
    (默认srs_scene1), 条目本身始终从证据动态学习(运行时配置).
    """
    p = _patterns(lexicon)
    name_class: dict[str, str] = {}
    interface_ids: list[str] = []
    mode_values: list[str] = []
    status_values: list[str] = []
    for statement in evidence_statements:
        identifier_match = p.identifier_statement_re.match(statement.text)
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
        if _is_usecase_field(statement.field_name, p.usecase_fields) \
                and statement.scope_key:
            name_class.setdefault(statement.scope_key, "usecase")
        elif statement.field_name == "方式名称":
            value = statement.text.rsplit("：", 1)[-1]
            mode_values.extend(
                piece.strip() for piece in _ENUM_SPLIT_RE.split(value)
                if piece.strip() and re.search(r"[\u4e00-\u9fff]", piece)
                and not (p.status_filter_re is not None
                         and p.status_filter_re.fullmatch(piece.strip())))
        elif statement.field_name == "运行状态":
            status_values.extend(
                piece for piece in
                _status_values(statement.text.rsplit("：", 1)[-1], p.status_tokens)
                if re.search(r"[\u4e00-\u9fff]", piece))
    for statement in evidence_statements:
        for identifier in p.id_re.findall(statement.text):
            if identifier not in interface_ids:
                interface_ids.append(identifier)
    for statement in evidence_statements:
        if statement.field_name not in _ENUM_LIST_FIELDS:
            continue
        for match in _ENUM_LIST_RE.finditer(statement.text):
            for raw in re.split(r"[、及和]", match.group("items")):
                item = _strip_leading_prefixes(raw.strip(), p.strip_prefix_words)
                if item.endswith("功能") and len(item) > 4:
                    item = item[:-2]
                if (3 <= len(item) <= 20 and re.search(r"[\u4e00-\u9fff]", item)
                        and item not in p.stopwords):
                    name_class.setdefault(item, "usecase")

    database_names: list[str] = []
    alias_pairs: list[AliasPair] = []
    seen_pairs: set[tuple[str, str]] = set()
    for statement in evidence_statements:
        if p.database_re is not None:
            for raw in p.database_re.findall(statement.text):
                name = _normalize_db_name(raw)
                if name and name not in database_names:
                    database_names.append(name)
        for alias_re in p.alias_res:
            for raw_surface, inner in alias_re.findall(statement.text):
                surface = _strip_leading_prefixes(raw_surface, p.strip_prefix_words)
                if _valid_alias_pair(surface, inner, p.stopwords) \
                        and (surface, inner) not in seen_pairs:
                    seen_pairs.add((surface, inner))
                    alias_pairs.append(AliasPair(surface=surface, target=inner))

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
                         p: NerPatterns) -> list[ClaimResult]:
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
    claim_ids = sorted({e.surface for e in _extract_entities(claim.text, p)
                        if e.kind == "pzxq_id"})
    if not claim_ids:
        return []
    evidence_id_refs: dict[str, list[str]] = {}
    for statement in scoped_statements:
        for identifier in p.id_re.findall(statement.text):
            evidence_id_refs.setdefault(identifier, []).append(statement.statement_id)
    full_id_refs: dict[str, list[str]] = {}
    for statement in all_statements:
        for identifier in p.id_re.findall(statement.text):
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
                       statements: list[EvidenceStatement],
                       p: NerPatterns) -> list[ClaimResult]:
    claim_pairs: list[tuple[str, str]] = []
    for definition_re in p.definition_res:
        claim_pairs.extend(definition_re.findall(claim.text))
    if not claim_pairs:
        return []
    claim_pairs = [(_strip_leading_prefixes(term, p.strip_prefix_words), definition)
                   for term, definition in claim_pairs]
    evidence_defs: dict[str, dict[str, str]] = {}
    for statement in statements:
        for definition_re in p.definition_res:
            for raw_term, definition in definition_re.findall(statement.text):
                term = _strip_leading_prefixes(raw_term, p.strip_prefix_words)
                evidence_defs.setdefault(term, {}).setdefault(
                    definition, statement.statement_id)
    results: list[ClaimResult] = []
    for term, definition in claim_pairs:
        if len(term) < 2 or term in p.stopwords:
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


def _usecase_like(mention: str, usecase_verbs: tuple[str, ...],
                  usecase_objects: tuple[str, ...]) -> bool:
    return (any(mention.endswith(verb) for verb in usecase_verbs)
            and any(obj in mention for obj in usecase_objects))


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
                            lexicon: DocumentLexicon,
                            p: NerPatterns) -> list[ClaimResult]:
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
        if names and _usecase_like(
                mention_compact, p.usecase_verbs, p.usecase_objects):
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
                             lexicon: DocumentLexicon,
                             p: NerPatterns) -> list[ClaimResult]:
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
        code = ("TERM-01" if evidence_form in p.domain_terms
                or answer_form in p.domain_terms
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
                          claims: list[StructuredClaim],
                          lexicon: NerLexicon | None = None) -> list[ClaimResult]:
    """Run all five TERM checks over every answer claim (L0, deterministic).

    ``lexicon``不注入时用模块级默认场景(srs_scene1); 前三个位置参数与
    返回结构保持v1不变(qa_module/既有测试零改动).
    """
    p = _patterns(lexicon)
    doc_lexicon = build_document_lexicon(evidence_statements, lexicon)
    results: list[ClaimResult] = []
    for claim in claims:
        scoped = _scope_statements(claim, evidence_statements)
        results.extend(_check_interface_ids(claim, scoped, evidence_statements, p))
        results.extend(_check_definitions(claim, scoped, p))
        results.extend(
            _check_usecase_mentions(request, claim, scoped, doc_lexicon, p))
        results.extend(
            _check_alias_preferences(claim, evidence_statements, doc_lexicon, p))
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
