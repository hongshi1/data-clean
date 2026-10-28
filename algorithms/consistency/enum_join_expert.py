"""枚举join专家（L1确定性组件，修复enum通道的"子串宽容"缺陷）。

旧enum通道对answer枚举只做"每个成员在证据文本中字面出现→support"的
逐成员子串匹配——成员级命中掩盖了集合级冲突：

- VIO-06 正文5项vs表3四行：正文说"SQL访问功能包括数据库操作、修改数据、
  查询数据、逐行获取数据、BLOB数据操作"，表3顶层能力行只有4行（逐行
  获取数据并入查询数据行的需求描述而非独立能力行）——answer断言正文侧
  5项枚举，表侧封闭集合反对它，旧通道逐成员命中→误判一致；
- VIO-09 平版错别字：表9/表13方式名称列写"桌面、平版、手持"（错字），
  answer声明正确值"平板"——需要值域检查+编辑距离1的错字检测；
- S1QA-056/074（91QA漏检refute）：answer"支持在桌面、平版和平板设备上
  运行"（多出错字"平版"且遗漏"手持"）；"BLOB数据操作在桌面版、平板版
  和手持版上均可使用"（BLOB行的方式名称只有平板、桌面，多出手持）。

本专家先把冻结evidence的线性化语句（linearize_context输出）聚合成
主体值域注册表（主体 → [(成员集合, 位置, 字段)]），再对answer的每条
枚举声明执行三项同主体跨位置检查：

1. 同主体集合比对：answer的(subject, members)与注册表同主体（精确+
   包含式匹配）同字段的封闭集合比对——answer多出成员（S1QA-074的
   "手持"）、封闭枚举遗漏注册成员（S1QA-056的"手持"）、证据同主体
   多来源成员集不一致（VIO-06正文vs表3行、VIO-07正文vs表32行，
   answer取任一侧）→ refute；
2. 值域错字检查：终端形态/运行状态的封闭值域{桌面,平板,手持}/
   {开发阶段,运行阶段}外、与值域词编辑距离为1的成员→错字——answer侧
   错字（S1QA-056的"平版"）与证据侧错字（VIO-09表9的"平版"vs answer
   的正确值"平板"）均refute；
3. 成员存在性：answer封闭枚举（"包括/支持在…上"语义）成员不在同主体
   任何注册条目中→refute（编辑距离1时按错字归因，≥2时按多出成员
   归因）；开放枚举（"…等"）不裁多出/遗漏，未注册主体保守跳过。

注册表两个确定性提取来源：表格字段语句（"X的方式名称：平板、桌面"，
linearize_context对能力表的行级线性化）与正文枚举句（"X包括A、B、C"）；
能力表行主体按ID父段（PZXQ-GN-SQLFW-*→PZXQ-GN-SQLFW）聚合为
"父主体的封闭能力行集合"（表3四行 vs 正文5项的比对基础）。

claim_text使用answer的原始成员列表（与旧enum通道的claim一致），
per-claim融合（refute>support>NIE）中本专家的refute压制旧通道的
误support。完全确定性：无模型调用、无检索、无文件读写；编辑距离为
自实现Levenshtein（不引第三方依赖）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.qa_models import ClaimResult, QAInput
from algorithms.consistency.rulepack import RulePack, default_rulepack

METHOD = "enum_join_registry"
CHECK_ITEMS: tuple[str, ...] = ("TERM-03",)


@dataclass(frozen=True)
class _EnumConfig:
    """从rule pack编译的枚举join配置(字段模式+值域+词表+错字距离)."""

    field_value: re.Pattern[str]
    enum_sentence: re.Pattern[str]
    id_binding: re.Pattern[str]
    section_title: re.Pattern[str]
    device: re.Pattern[str]
    question_subject: re.Pattern[str]
    member_valid: re.Pattern[str]
    member_split: re.Pattern[str]
    count_function_suffix: re.Pattern[str]
    subject_role_suffix: re.Pattern[str]
    leading_table: re.Pattern[str]
    generic_subject: re.Pattern[str]
    phase_words: re.Pattern[str]
    member_split_device: re.Pattern[str]
    device_subject_run: re.Pattern[str]
    terminal_bases: frozenset[str]
    phase_bases: frozenset[str]
    subject_garbage_infixes: tuple[str, ...]
    generic_subjects: frozenset[str]
    dev_tail_strip: tuple[str, ...]
    field_kinds: dict[str, str]
    field_labels: dict[str, str]
    typo_distance: int
    device_subject_window: int
    row_enum_block_isolated: bool


def _build_config(pack: RulePack) -> _EnumConfig:
    return _EnumConfig(
        field_value=pack.template("enum_field_value"),
        enum_sentence=pack.template("enum_sentence"),
        id_binding=pack.template("enum_id_binding"),
        section_title=pack.template("enum_section_title"),
        device=pack.template("enum_device"),
        question_subject=pack.template("enum_question_subject"),
        member_valid=pack.template("enum_member_valid"),
        member_split=pack.template("enum_member_split"),
        count_function_suffix=pack.template("enum_count_function_suffix"),
        subject_role_suffix=pack.template("enum_subject_role_suffix"),
        leading_table=pack.template("enum_leading_table"),
        generic_subject=pack.template("enum_generic_subject"),
        phase_words=pack.template("enum_phase_words"),
        member_split_device=pack.template("enum_member_split_device"),
        device_subject_run=pack.template("enum_device_subject_run"),
        terminal_bases=frozenset(pack.vocabulary("enum_terminal_bases")),
        phase_bases=frozenset(pack.vocabulary("enum_phase_bases")),
        subject_garbage_infixes=pack.vocabulary("enum_subject_garbage_infixes"),
        generic_subjects=frozenset(pack.vocabulary("enum_generic_subjects")),
        dev_tail_strip=pack.vocabulary("enum_dev_tail_strip"),
        field_kinds=dict(pack.join_param("enum_join", "field_kinds", {})),
        field_labels=dict(pack.join_param("enum_join", "field_labels", {})),
        typo_distance=int(pack.join_param("enum_join", "typo_distance", 1)),
        device_subject_window=int(
            pack.join_param("enum_join", "device_subject_window", 24)),
        row_enum_block_isolated=bool(
            pack.join_param("enum_join", "row_enum_block_isolated", True)),
    )


_ENUM_CONFIG: _EnumConfig | None = None


def _cfg() -> _EnumConfig:
    """惰性加载默认rule pack并编译枚举join配置(模块级缓存, import期零I/O)."""
    global _ENUM_CONFIG
    if _ENUM_CONFIG is None:
        _ENUM_CONFIG = _build_config(default_rulepack())
    return _ENUM_CONFIG



def levenshtein(a: str, b: str) -> int:
    """自实现编辑距离（不引依赖）：两串均为短词（≤16字符）。"""
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            current.append(min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + (char_a != char_b),
            ))
        previous = current
    return previous[-1]


def _norm_terminal(member: str) -> str:
    """终端形态归一：桌面版→桌面（值域外词如"平版"保持原样供错字检测）。"""
    if member in _cfg().terminal_bases:
        return member
    if member.endswith("版") and member[:-1] in _cfg().terminal_bases:
        return member[:-1]
    return member


def _norm_functional(member: str) -> str:
    """功能成员归一：去"N项功能/功能/等"尾缀（最短保留原词）。"""
    stripped = _cfg().count_function_suffix.sub("", member)
    stripped = stripped.removesuffix("等")
    if stripped.endswith("功能") and len(stripped) >= 4:
        stripped = stripped[:-2]
    return stripped or member


def _norm_subject(raw: str) -> str:
    """主体归一：去表引用前缀/角色尾缀/「功能」尾缀。"""
    subject = raw.strip().strip("「」『』\"' ")
    subject = _cfg().leading_table.sub("", subject)
    subject = _cfg().subject_role_suffix.sub("", subject)
    while len(subject) > 4 and subject.endswith("功能"):
        subject = subject[:-2]
    return subject.strip()


def _subject_key(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold()


def _subject_match(a: str, b: str) -> bool:
    """主体匹配：精确相等或（≥3字符的）包含关系（双向）。"""
    key_a, key_b = _subject_key(a), _subject_key(b)
    if not key_a or not key_b:
        return False
    if key_a == key_b:
        return True
    shorter = min(len(key_a), len(key_b))
    return shorter >= 3 and (key_a in key_b or key_b in key_a)


def _entry_kind(entry: "DomainEntry") -> str:
    return _cfg().field_kinds.get(entry.source_field, "other")


@dataclass(frozen=True)
class DomainEntry:
    """注册表中一条 (主体, 成员集合, 位置) 记录。

    statement_ids为该条目贡献的全部语句定位（row_enum聚合多行时>1）。
    """

    subject: str
    members: tuple[str, ...]
    source_field: str
    evidence_ids: tuple[str, ...]
    statement_ids: tuple[str, ...]

    def describe(self) -> str:
        field = _cfg().field_labels.get(self.source_field, self.source_field)
        refs = "、".join(self.statement_ids[:3])
        more = "" if len(self.statement_ids) <= 3 else "等"
        return (f"{self.subject}的{field}{{{'、'.join(self.members)}}}"
                f"（{refs}{more}）")


@dataclass(frozen=True)
class EnumAssertion:
    """answer中的一条枚举声明：(候选主体序列, 成员, 封闭语义)。"""

    subjects: tuple[str, ...]
    raw_members: tuple[str, ...]
    members: tuple[str, ...]
    kind: str
    closed: bool

    @property
    def claim_text(self) -> str:
        return "、".join(self.raw_members)


def _valid_member(member: str) -> bool:
    return bool(_cfg().member_valid.fullmatch(member))


def _split_items(items_text: str) -> list[str]:
    return [part for part in _cfg().member_split.split(items_text) if part]


def _field_members(field: str, value: str) -> tuple[str, ...]:
    """字段单元格→成员：运行状态按阶段词切（"运行阶段开发阶段"无分隔符）。"""
    value = value.strip().rstrip("。；;、")
    if field == "运行状态":
        words = _cfg().phase_words.findall(value)
        if words:
            return tuple(dict.fromkeys(words))
    items = [item for item in re.split(r"[、，,]", value) if item]
    if field == "方式名称":
        return tuple(dict.fromkeys(
            _norm_terminal(item) for item in items if _valid_member(item)))
    return tuple(dict.fromkeys(item for item in items if _valid_member(item)))


def _subject_rejected(raw: str) -> bool:
    if any(term in raw for term in _cfg().subject_garbage_infixes):
        return True
    subject = _norm_subject(raw)
    return (not subject or subject in _cfg().generic_subjects
            or bool(_cfg().generic_subject.fullmatch(subject)))


def build_domain_registry(
        statements: list[EvidenceStatement],
        ) -> list[DomainEntry]:
    """从线性化证据语句构建主体值域注册表。

    三个确定性提取来源：①表格字段语句（"X的方式名称：平板、桌面"）；
    ②正文枚举句（"X包括A、B、C"，含能力表需求描述单元格内的枚举）；
    ③能力表行主体按ID父段聚合（行ID去尾段→父ID，父ID经"X的项目唯一
    标识符"或节标题绑定到父主体）→"父主体的封闭能力行集合"。
    """
    entries: list[DomainEntry] = []
    id_subject: dict[str, str] = {}
    rows: list[tuple[str, str, EvidenceStatement]] = []
    for statement in statements:
        compact = re.sub(r"\s+", "", statement.text)
        for match in _cfg().field_value.finditer(compact):
            subject = _norm_subject(match.group("subj"))
            members = _field_members(match.group("field"), match.group("value"))
            if subject and members:
                entries.append(DomainEntry(
                    subject=subject, members=members,
                    source_field=match.group("field"),
                    evidence_ids=(statement.evidence_id,),
                    statement_ids=(statement.statement_id,)))
        for match in _cfg().enum_sentence.finditer(compact):
            subject = _make_prose_entry(match, statement)
            if subject is not None:
                entries.append(subject)
        for match in _cfg().id_binding.finditer(compact):
            subject = _norm_subject(match.group("subj"))
            identifier = match.group("id")
            if len(subject) >= 2:
                id_subject.setdefault(identifier, subject)
                rows.append((subject, identifier, statement))
        for match in _cfg().section_title.finditer(compact):
            name = match.group("name")
            leaf = name.rsplit("-", 1)[-1] if "-" in name else name
            subject = _norm_subject(leaf)
            if len(subject) >= 2:
                id_subject.setdefault(match.group("id"), subject)
    # row_enum: 同父ID的行主体集合 → 父主体封闭枚举（能力表"所有能力
    # 标识"行）。分块聚合：同一父ID前缀常被多张表共用（真实04文档表9的
    # 行ID PZXQ-GN-SQLFW-SJXG与表3的行共用PZXQ-GN-SQLFW父段），跨块
    # 合并会把两张表的行集错并成一个封闭集合。
    block_isolated = _cfg().row_enum_block_isolated
    groups: dict[tuple[str, str], list[tuple[str, EvidenceStatement]]] = {}
    for scope, identifier, statement in rows:
        parent = identifier.rsplit("-", 1)[0]
        if parent and parent != identifier and parent in id_subject:
            block_key = (parent, statement.evidence_id) if block_isolated else (
                parent, "")
            groups.setdefault(block_key, []).append((scope, statement))
    for (parent, _), items in groups.items():
        scopes: list[str] = []
        statement_ids: list[str] = []
        evidence_ids: list[str] = []
        for scope, statement in items:
            scopes.append(scope)
            statement_ids.append(statement.statement_id)
            evidence_ids.append(statement.evidence_id)
        members = tuple(dict.fromkeys(scopes))
        if len(members) >= 2:
            entries.append(DomainEntry(
                subject=id_subject[parent], members=members,
                source_field="row_enum",
                evidence_ids=tuple(dict.fromkeys(evidence_ids)),
                statement_ids=tuple(dict.fromkeys(statement_ids))))
    return entries


def _make_prose_entry(match: re.Match[str],
                      statement: EvidenceStatement) -> DomainEntry | None:
    subj_raw = match.group("subj")
    if _subject_rejected(subj_raw):
        return None
    items_text = match.group("items")
    raw_items = _split_items(items_text)
    if len(raw_items) < 2 or not all(_valid_member(i) for i in raw_items):
        return None
    subject = _norm_subject(subj_raw)
    if not subject:
        return None
    members = tuple(dict.fromkeys(_norm_functional(i) for i in raw_items))
    if len(members) < 2:
        return None
    return DomainEntry(
        subject=subject, members=members, source_field="prose",
        evidence_ids=(statement.evidence_id,),
        statement_ids=(statement.statement_id,))


def _classify_members(raw_members: tuple[str, ...]) -> str:
    """声明kind：终端形态（值域内或距值域词1）/阶段/功能枚举。"""
    if not raw_members:
        return "functional"
    terminal = [_norm_terminal(member) for member in raw_members]
    if all(member in _cfg().terminal_bases for member in terminal):
        return "terminal"
    if all(
            member in _cfg().terminal_bases
            or any(levenshtein(member, base) == _cfg().typo_distance for base in sorted(_cfg().terminal_bases))
            for member in terminal):
        return "terminal"
    if all(member in _cfg().phase_bases for member in raw_members):
        return "phase"
    return "functional"


def _normalize_members(raw_members: tuple[str, ...], kind: str) -> tuple[str, ...]:
    if kind == "terminal":
        return tuple(dict.fromkeys(
            _norm_terminal(member) for member in raw_members))
    if kind == "phase":
        return tuple(dict.fromkeys(raw_members))
    return tuple(dict.fromkeys(
        _norm_functional(member) for member in raw_members))


def _strip_tail(text: str) -> str:
    stripped = text
    changed = True
    while changed and stripped:
        changed = False
        for suffix in _cfg().dev_tail_strip:
            if stripped.endswith(suffix) and len(stripped) > len(suffix):
                stripped = stripped[: -len(suffix)]
                changed = True
                break
    return stripped


def _question_subject(question: str) -> str | None:
    compact = re.sub(r"\s+", "", question)
    match = _cfg().question_subject.search(compact)
    if match is None:
        return None
    subject = _norm_subject(match.group("subj"))
    if not subject or subject in _cfg().generic_subjects:
        return None
    if _cfg().generic_subject.fullmatch(subject):
        return None
    return subject


def _device_subject_candidates(text: str, start: int,
                               question: str) -> tuple[str, ...]:
    """DEV声明的候选主体：局部名词（去泛指/anaphor）优先，问题主题回退。"""
    window = _strip_tail(text[max(0, start - _cfg().device_subject_window):start])
    candidates: list[str] = []
    run = _cfg().device_subject_run.search(window)
    if run:
        subject = _norm_subject(run.group(0))
        if (subject and subject not in _cfg().generic_subjects
                and not _cfg().generic_subject.fullmatch(subject)):
            candidates.append(subject)
    fallback = _question_subject(question)
    if fallback:
        candidates.append(fallback)
    return tuple(dict.fromkeys(candidates))


def extract_enum_assertions(answer: str,
                            question: str) -> list[EnumAssertion]:
    """提取answer的枚举声明：(候选主体, 成员, 封闭语义)。

    两个形态：①"X包括A、B、C"（主体显式）；②"支持在A、B、C[设备]上
    运行"（主体取局部名词或问题主题）。成员含markdown/标点/单成员/
    "但不限于"开放引导/垃圾主体→整条拒绝（保守）。
    """
    compact = re.sub(r"\s+", "", answer)
    assertions: list[EnumAssertion] = []
    seen: set[tuple[str, ...]] = set()
    for match in _cfg().enum_sentence.finditer(compact):
        items_text = match.group("items")
        if "但不限于" in items_text:
            continue
        raw_items = _split_items(items_text)
        if len(raw_items) < 2 or not all(_valid_member(i) for i in raw_items):
            continue
        subj_raw = match.group("subj")
        if _subject_rejected(subj_raw):
            continue
        subject = _norm_subject(subj_raw)
        if not subject:
            continue
        key = (subject,) + tuple(raw_items)
        if key in seen:
            continue
        seen.add(key)
        kind = _classify_members(tuple(raw_items))
        assertions.append(EnumAssertion(
            subjects=(subject,), raw_members=tuple(raw_items),
            members=_normalize_members(tuple(raw_items), kind), kind=kind,
            closed=not items_text.endswith("等")))
    for match in _cfg().device.finditer(compact):
        raw_items = [item for item in
                     _cfg().member_split_device.split(match.group("items")) if item]
        if len(raw_items) < 2 or not all(_valid_member(i) for i in raw_items):
            continue
        subjects = _device_subject_candidates(compact, match.start(), question)
        if not subjects:
            continue
        key = subjects + tuple(raw_items)
        if key in seen:
            continue
        seen.add(key)
        kind = _classify_members(tuple(raw_items))
        assertions.append(EnumAssertion(
            subjects=subjects, raw_members=tuple(raw_items),
            members=_normalize_members(tuple(raw_items), kind), kind=kind,
            closed=not match.group("items").endswith("等")))
    return assertions


def _matched_entries(
        assertion: EnumAssertion,
        registry: list[DomainEntry]) -> list[DomainEntry] | None:
    """按候选主体依次尝试；首个有同kind匹配的主体现身，无匹配→None。"""
    for subject in assertion.subjects:
        matched = [entry for entry in registry
                   if _entry_kind(entry) == assertion.kind
                   and _subject_match(subject, entry.subject)]
        if matched:
            return _dedupe_entries(matched)
    return None


def _dedupe_entries(entries: list[DomainEntry]) -> list[DomainEntry]:
    """(主体, 字段, 成员)相同的条目合并定位（多表同值行不算多来源）。"""
    merged: dict[tuple[str, str, tuple[str, ...]], DomainEntry] = {}
    for entry in entries:
        key = (entry.subject, entry.source_field, entry.members)
        existing = merged.get(key)
        if existing is None:
            merged[key] = entry
        else:
            merged[key] = DomainEntry(
                subject=existing.subject, members=existing.members,
                source_field=existing.source_field,
                evidence_ids=tuple(dict.fromkeys(
                    existing.evidence_ids + entry.evidence_ids)),
                statement_ids=tuple(dict.fromkeys(
                    existing.statement_ids + entry.statement_ids)))
    return list(merged.values())


def _bases_for(kind: str) -> frozenset[str]:
    if kind == "terminal":
        return _cfg().terminal_bases
    if kind == "phase":
        return _cfg().phase_bases
    return frozenset()


def _typo_target(member: str, bases: frozenset[str],
                 union: set[str]) -> str | None:
    """成员不在值域但与值域词/注册成员编辑距离=1→返回正确词。"""
    for candidate in sorted(bases | union):
        if candidate != member and levenshtein(member, candidate) == _cfg().typo_distance:
            return candidate
    return None


def _compare(assertion: EnumAssertion,
             matched: list[DomainEntry],
             ) -> tuple[str, tuple[str, ...]] | None:
    """三项检查：证据侧错字→answer多出成员(错字归因)→多来源冲突→遗漏。"""
    answer_members = list(dict.fromkeys(assertion.members))
    union: set[str] = set()
    for entry in matched:
        union.update(entry.members)
    inter: set[str] = set(matched[0].members)
    for entry in matched[1:]:
        inter &= set(entry.members)
    bases = _bases_for(assertion.kind)
    extra = ([member for member in answer_members if member not in union]
             if assertion.closed else [])
    conflict = [member for member in answer_members
                if member in union and member not in inter]
    signals: list[str] = []
    refs: list[str] = []
    # 检查②（证据侧）：注册成员是值域外错字且answer声明了正确值
    for member in sorted(union):
        if not bases or member in bases:
            continue
        for base in sorted(bases):
            if levenshtein(member, base) == _cfg().typo_distance and base in answer_members:
                signals.append(
                    f"证据侧疑似错别字：{member}→{base}（answer声明了正确值"
                    f"「{base}」，注册值「{member}」不在值域"
                    f"{{{'、'.join(sorted(bases))}}}）")
                for entry in matched:
                    if member in entry.members:
                        refs.extend(entry.statement_ids)
                break
    # 检查①/③（answer侧）：多出成员（answer自身错字优先归因；成员本就是
    # 值域词而注册集合只有其距离1变体时，错字在证据侧——归因交给检查②）
    for member in extra:
        typo = (_typo_target(member, bases, union)
                if member not in bases else None)
        if typo is not None:
            signals.append(
                f"answer多出成员「{member}」：疑似错别字（应为「{typo}」），"
                f"不在同主体{matched[0].describe()}中")
        else:
            signals.append(
                f"answer多出成员「{member}」：同主体"
                f"{matched[0].describe()}不含该成员")
        for entry in matched:
            refs.extend(entry.statement_ids)
    # 检查①（多来源）：answer成员见于部分来源但不在其余来源的封闭集合
    for member in conflict:
        with_side = [entry for entry in matched if member in entry.members]
        without_side = [entry for entry in matched if member not in entry.members]
        signals.append(
            f"answer成员「{member}」见于{with_side[0].describe()}"
            f"但不在{without_side[0].describe()}的封闭集合中")
        for entry in with_side + without_side:
            refs.extend(entry.statement_ids)
    # 检查①（遗漏）：封闭枚举缺注册成员（所有匹配来源均含该成员）；
    # 注册成员本身是证据侧错字且answer已声明正确值时不裁遗漏
    if assertion.closed:
        for member in sorted(inter):
            if member in answer_members:
                continue
            if bases and member not in bases:
                corrected = next(
                    (base for base in sorted(bases)
                     if levenshtein(member, base) == _cfg().typo_distance), None)
                if corrected is not None and corrected in answer_members:
                    continue
            signals.append(
                f"answer封闭枚举遗漏注册成员「{member}」：同主体"
                f"{matched[0].describe()}均含该成员")
            for entry in matched:
                refs.extend(entry.statement_ids)
    if not signals:
        return None
    rationale = "枚举集合冲突（" + "；".join(signals) + "）"
    return rationale, tuple(dict.fromkeys(refs))


def verify_enum_joins(request: QAInput,
                      statements: list[EvidenceStatement],
                      ) -> list[ClaimResult]:
    """对冻结QA输入执行三项枚举join检查（L1确定性，TERM-03）。

    返回method="enum_join_registry"的refute ClaimResult列表；claim_text
    为answer原始成员列表（与旧enum通道一致，per-claim融合中refute压制
    旧通道的误support）。注册表为空、answer无枚举声明或声明主体未注册
    →返回[]（保守，判给旧通道/NIE）。
    """
    registry = build_domain_registry(statements)
    if not registry:
        return []
    assertions = extract_enum_assertions(request.answer, request.question)
    results: list[ClaimResult] = []
    for index, assertion in enumerate(assertions, start=1):
        matched = _matched_entries(assertion, registry)
        if matched is None:
            continue
        fired = _compare(assertion, matched)
        if fired is None:
            continue
        rationale, refs = fired
        results.append(ClaimResult(
            claim_id=f"{request.instance_id}-enumjoin{index:02d}",
            claim_text=assertion.claim_text,
            verdict="refute",
            check_item_candidates=CHECK_ITEMS,
            evidence_refs=refs,
            rationale=rationale,
            method=METHOD,
            confidence=1.0,
        ))
    return results


__all__ = [
    "CHECK_ITEMS",
    "METHOD",
    "DomainEntry",
    "EnumAssertion",
    "build_domain_registry",
    "extract_enum_assertions",
    "levenshtein",
    "verify_enum_joins",
]
