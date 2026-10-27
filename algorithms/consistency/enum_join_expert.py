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

METHOD = "enum_join_registry"
CHECK_ITEMS: tuple[str, ...] = ("TERM-03",)

#: 终端形态（方式名称）与运行状态（阶段）的封闭值域——错字检测锚
_TERMINAL_BASES = frozenset({"桌面", "平板", "手持"})
_PHASE_BASES = frozenset({"开发阶段", "运行阶段"})

#: 声明kind → 参与比对的注册条目source_field
_KIND_BY_FIELD = {
    "方式名称": "terminal",
    "运行状态": "phase",
    "prose": "functional",
    "row_enum": "functional",
}
_FIELD_LABEL = {
    "方式名称": "方式名称",
    "运行状态": "运行状态",
    "prose": "正文枚举",
    "row_enum": "能力表行",
}

#: 表格字段语句（能力表线性化形态）："X的方式名称：平板、桌面"
_FIELD_VALUE_RE = re.compile(
    r"(?P<subj>[\u4e00-\u9fffA-Za-z0-9]{2,20})的"
    r"(?P<field>需求重用|方式名称|运行状态|对应的任务书功能性能)[：:]"
    r"(?P<value>.+)")

#: 枚举句（正文/answer共用）："X[功能]包括：A、B、C"——主体后缀
#: （功能/操作/服务/内容）可选吞掉，主体取最短合法形态
_ENUM_RE = re.compile(
    r"(?P<subj>[\u4e00-\u9fffA-Za-z0-9]{2,20}?)"
    r"(?:功能|操作|服务|内容)?(?:包括|包含|分为|划分为)[：:]?"
    r"(?P<items>[^，,。；;\n]{4,120})")

#: ID绑定（能力表"X的项目唯一标识符：ID"），供行主体→父主体聚合
_ID_BINDING_RE = re.compile(
    r"(?P<subj>[\u4e00-\u9fffA-Za-z0-9]{2,20}?)的"
    r"(?:项目唯一标识符|唯一标识符|接口需求标识|接口标识|功能标识)[：:]"
    r"(?P<id>PZXQ-[A-Z0-9-]+)")

#: 节标题绑定："3.2.1.2 SQL访问-修改数据（PZXQ-GN-SQLFW-XGSJ）"
_SECTION_TITLE_RE = re.compile(
    r"\d+(?:\.\d+)+(?P<name>[\u4e00-\u9fffA-Za-z0-9-]{2,40}?)"
    r"[（(](?P<id>PZXQ-[A-Z0-9-]+)[）)]")

#: answer侧终端形态声明："支持在桌面、平版和平板设备上运行"
_DEVICE_ENUM_RE = re.compile(
    r"在(?P<items>[\u4e00-\u9fffA-Za-z0-9、和]{6,60}?)"
    r"(?:等)?(?:种版本|版本|设备|终端|平台)?"
    r"上(?:运行|使用|提供|均可|实施)")

#: 问题主题回退（DEV声明缺局部主体时）："SQL访问修改数据功能包括哪些操作"
_QUESTION_SUBJECT_RE = re.compile(
    r"(?P<subj>[\u4e00-\u9fffA-Za-z0-9]{2,24}?)"
    r"(?:包括|包含|涉及|以哪些|有哪些|哪些)")

_MEMBER_VALID_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}")
_MEMBER_SPLIT_RE = re.compile(r"[、，,]|以及|和")
_COUNT_FUNCTION_SUFFIX_RE = re.compile(r"(?:[一二三四五六七八九十两\d]+)?项功能$")
_SUBJECT_ROLE_SUFFIX_RE = re.compile(
    r"(?:的支持方式|的方式名称|的运行状态|的功能标识表|的具体操作"
    r"|的主要功能|的核心操作|的子功能)$")
_LEADING_TABLE_RE = re.compile(r"^表\d+")
_GENERIC_SUBJECT_RE = re.compile(
    r"^(?:所有|这些|上述|全部|该|其|每|各)?"
    r"(?:操作|功能|用例|设备|版本|步骤|内容|方面|模块|场景|参数)$")

#: 提取主体含这些词→垃圾主体（"…按照其功能需求，包含…"式）
_SUBJECT_GARBAGE_INFIXES = (
    "按照", "如下", "以下", "上述", "其中", "以及", "并且", "还是",
    "通常", "主要", "常见", "需要", "但不限于",
)
_GENERIC_SUBJECTS = frozenset({
    "具体", "内容", "方面", "步骤", "类型", "模块", "场景", "参数",
    "系统", "软件", "服务", "功能", "操作", "数据", "需求", "能力",
    "该用例", "该功能", "其功能", "该操作", "这些操作", "所有操作",
    "上述操作", "全部操作", "这些功能", "所有功能", "这些设备",
    "所有设备", "以上内容", "以下内容",
})

_DEV_TAIL_STRIP = (
    "并且在", "并且", "支持", "提供", "使用", "运行", "实施", "基于",
    "实现", "在", "均", "都", "也", "和", "，", "。", "；", "、",
)


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
    if member in _TERMINAL_BASES:
        return member
    if member.endswith("版") and member[:-1] in _TERMINAL_BASES:
        return member[:-1]
    return member


def _norm_functional(member: str) -> str:
    """功能成员归一：去"N项功能/功能/等"尾缀（最短保留原词）。"""
    stripped = _COUNT_FUNCTION_SUFFIX_RE.sub("", member)
    stripped = stripped.removesuffix("等")
    if stripped.endswith("功能") and len(stripped) >= 4:
        stripped = stripped[:-2]
    return stripped or member


def _norm_subject(raw: str) -> str:
    """主体归一：去表引用前缀/角色尾缀/「功能」尾缀。"""
    subject = raw.strip().strip("「」『』\"' ")
    subject = _LEADING_TABLE_RE.sub("", subject)
    subject = _SUBJECT_ROLE_SUFFIX_RE.sub("", subject)
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
    return _KIND_BY_FIELD.get(entry.source_field, "other")


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
        field = _FIELD_LABEL.get(self.source_field, self.source_field)
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
    return bool(_MEMBER_VALID_RE.fullmatch(member))


def _split_items(items_text: str) -> list[str]:
    return [part for part in _MEMBER_SPLIT_RE.split(items_text) if part]


def _field_members(field: str, value: str) -> tuple[str, ...]:
    """字段单元格→成员：运行状态按阶段词切（"运行阶段开发阶段"无分隔符）。"""
    value = value.strip().rstrip("。；;、")
    if field == "运行状态":
        words = re.findall(r"开发阶段|运行阶段", value)
        if words:
            return tuple(dict.fromkeys(words))
    items = [item for item in re.split(r"[、，,]", value) if item]
    if field == "方式名称":
        return tuple(dict.fromkeys(
            _norm_terminal(item) for item in items if _valid_member(item)))
    return tuple(dict.fromkeys(item for item in items if _valid_member(item)))


def _subject_rejected(raw: str) -> bool:
    if any(term in raw for term in _SUBJECT_GARBAGE_INFIXES):
        return True
    subject = _norm_subject(raw)
    return (not subject or subject in _GENERIC_SUBJECTS
            or bool(_GENERIC_SUBJECT_RE.fullmatch(subject)))


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
        for match in _FIELD_VALUE_RE.finditer(compact):
            subject = _norm_subject(match.group("subj"))
            members = _field_members(match.group("field"), match.group("value"))
            if subject and members:
                entries.append(DomainEntry(
                    subject=subject, members=members,
                    source_field=match.group("field"),
                    evidence_ids=(statement.evidence_id,),
                    statement_ids=(statement.statement_id,)))
        for match in _ENUM_RE.finditer(compact):
            subject = _make_prose_entry(match, statement)
            if subject is not None:
                entries.append(subject)
        for match in _ID_BINDING_RE.finditer(compact):
            subject = _norm_subject(match.group("subj"))
            identifier = match.group("id")
            if len(subject) >= 2:
                id_subject.setdefault(identifier, subject)
                rows.append((subject, identifier, statement))
        for match in _SECTION_TITLE_RE.finditer(compact):
            name = match.group("name")
            leaf = name.rsplit("-", 1)[-1] if "-" in name else name
            subject = _norm_subject(leaf)
            if len(subject) >= 2:
                id_subject.setdefault(match.group("id"), subject)
    # row_enum: 同父ID的行主体集合 → 父主体封闭枚举（能力表"所有能力
    # 标识"行）。分块聚合：同一父ID前缀常被多张表共用（真实04文档表9的
    # 行ID PZXQ-GN-SQLFW-SJXG与表3的行共用PZXQ-GN-SQLFW父段），跨块
    # 合并会把两张表的行集错并成一个封闭集合。
    groups: dict[tuple[str, str], list[tuple[str, EvidenceStatement]]] = {}
    for scope, identifier, statement in rows:
        parent = identifier.rsplit("-", 1)[0]
        if parent and parent != identifier and parent in id_subject:
            groups.setdefault((parent, statement.evidence_id),
                              []).append((scope, statement))
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
    if all(member in _TERMINAL_BASES for member in terminal):
        return "terminal"
    if all(
            member in _TERMINAL_BASES
            or any(levenshtein(member, base) == 1 for base in _TERMINAL_BASES)
            for member in terminal):
        return "terminal"
    if all(member in _PHASE_BASES for member in raw_members):
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
        for suffix in _DEV_TAIL_STRIP:
            if stripped.endswith(suffix) and len(stripped) > len(suffix):
                stripped = stripped[: -len(suffix)]
                changed = True
                break
    return stripped


def _question_subject(question: str) -> str | None:
    compact = re.sub(r"\s+", "", question)
    match = _QUESTION_SUBJECT_RE.search(compact)
    if match is None:
        return None
    subject = _norm_subject(match.group("subj"))
    if not subject or subject in _GENERIC_SUBJECTS:
        return None
    if _GENERIC_SUBJECT_RE.fullmatch(subject):
        return None
    return subject


def _device_subject_candidates(text: str, start: int,
                               question: str) -> tuple[str, ...]:
    """DEV声明的候选主体：局部名词（去泛指/anaphor）优先，问题主题回退。"""
    window = _strip_tail(text[max(0, start - 24):start])
    candidates: list[str] = []
    run = re.search(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}$", window)
    if run:
        subject = _norm_subject(run.group(0))
        if (subject and subject not in _GENERIC_SUBJECTS
                and not _GENERIC_SUBJECT_RE.fullmatch(subject)):
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
    for match in _ENUM_RE.finditer(compact):
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
    for match in _DEVICE_ENUM_RE.finditer(compact):
        raw_items = [item for item in
                     re.split(r"[、和]", match.group("items")) if item]
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
        return _TERMINAL_BASES
    if kind == "phase":
        return _PHASE_BASES
    return frozenset()


def _typo_target(member: str, bases: frozenset[str],
                 union: set[str]) -> str | None:
    """成员不在值域但与值域词/注册成员编辑距离=1→返回正确词。"""
    for candidate in sorted(bases | union):
        if candidate != member and levenshtein(member, candidate) == 1:
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
            if levenshtein(member, base) == 1 and base in answer_members:
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
                     if levenshtein(member, base) == 1), None)
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
