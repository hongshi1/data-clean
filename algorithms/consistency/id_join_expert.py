"""ID→主体注册表join专家（L1确定性组件，修复identifier通道的自信误support）。

旧identifier通道只做"answer的ID在证据文本中字面出现→support"的单向匹配；
17真实违例评测（violation_evalset_v1）中identifier类违例全部依赖"ID→主体"
的注册关系才能检出——ID字面存在不代表answer声称的绑定关系成立：

- VIO-01 同ID双登记：PZXQ-GN-LJCGL-LJCCSH被连接池配置/初始化两个用例共用
  （ID字面在证据中，旧通道误判support）；
- VIO-02 ID家族错配：数据库关闭在表4登记为SJKGBGN，节标题侧是SJKGB；
- VIO-03 前缀错配：同一接口在表48登记为SJTBGX前缀、3.3.x节标题用SJTYFW；
- VIO-04 段序颠倒：表53写DMSC-DXHFW，3.4.2节标题写DXHFW-DMSC；
- VIO-05 缺段：表23的BLOB子项ID缺BLOBSJCZ段。

本专家先把冻结evidence的线性化语句（linearize_context输出）聚合成ID注册表
（ID → [(主体, 位置, 字段)]三元组），再对answer的每条ID声明执行四项检查：

1. 双登记冲突：claimed ID在注册表中绑定到>1个互不包含的主体，且answer声称
   的主体在其中→refute（唯一标识符的唯一性被违反）。
2. subject-ID错配：answer声称"X的ID是Y"，但同族(family)注册中X登记的是
   其他ID→refute。
3. 组件段比对：同主体的注册ID与claimed ID逐段比对——段序颠倒/缺段/多段/
   家族错配→refute（仅当主体匹配时）。
4. 裸ID匹配：answer无主体短语时保持identifier通道现有行为——ID在注册表
   且在证据原文出现→support；否则not_in_evidence。

claim_text使用裸ID（与identifier通道的claim一致），per-claim融合
（refute>support>NIE）中本专家的refute正确压制旧通道的误support。

完全确定性：无模型调用、无检索、无文件读取。主体匹配为精确优先分层
（精确命中优先；无精确命中才用规范化包含，且回退方向固定为
claimed ⊂ registered——声称子功能而注册表只有父条目不算命中，
G4 P1 a-fix防S1QA-053式父子混淆误refute；ASCII大小写归一处理
Blob/BLOB、去"能力/功能/用例"后缀、节标题主体取"父-子"叶子名）；
冲突比对限定在同族ID（前两段相同，如PZXQ-GN/PZXQ-JK），
避免把父子层级（能力ID vs 接口ID）误判为冲突。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.qa_models import ClaimResult, QAInput

METHOD = "id_join_registry"
CHECK_ITEMS: tuple[str, ...] = ("TERM-07",)

#: PZXQ域标识符模式（与entity_detector的域术语模式同族）
PZXQ_ID_RE = re.compile(r"PZXQ-[A-Z0-9-]+")

#: 语句级绑定："X的项目唯一标识符：ID"（能力表）/"X的接口需求标识：ID"
#: （接口表）以及散文形态"X的标识为ID"（系词可组合，如"均为"）
_BINDING_RE = re.compile(
    r"(?P<name>[A-Za-z0-9\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff-]{0,40}?)"
    r"的(?:项目唯一标识符|唯一标识符|接口需求标识|接口标识|功能标识|标识符|标识|编号|代号)"
    r"(?:(?:分别|均|都|也|是|为)[：:]?)*[：:]?"
    r"(?P<id>PZXQ-[A-Z0-9-]+)")

#: 节标题绑定："3.2.1.1.1.4 数据库操作-数据库关闭（PZXQ-GN-...）"
_SECTION_TITLE_RE = re.compile(
    r"(?P<sec>\d+(?:\.\d+)+)"
    r"(?P<name>[\u4e00-\u9fffA-Za-z][\u4e00-\u9fffA-Za-z0-9-]{0,40}?)"
    r"[（(](?P<id>PZXQ-[A-Z0-9-]+)[）)]")

#: answer侧ID声明的角色词尾（"X的项目唯一标识符为ID"的"的…为"部分，
#: 系词可组合如"均为/都是"）
_ROLE_TAIL_RE = re.compile(
    r"的?(?:项目唯一标识符|唯一标识符|接口需求标识|接口标识|功能标识|标识符|标识"
    r"|编号|代号|名称|序号)"
    r"(?:(?:分别|均|都|也|是|为)[：:]?)*[：:]?$")

#: 别名形态："数据源适配接口（PZXQ-GN-SJYSP）"——ID前的括号主体
_BRACKET_SUBJECT_RE = re.compile(
    r"(?P<subj>[A-Za-z0-9\u4e00-\u9fff]{2,24})[（(]\s*[「\"]?\s*$")

#: answer侧主体提取的窗口（ID前文字）与分段边界
_ID_WINDOW = 32
_SEGMENT_SPLIT_RE = re.compile(r"[：:\n|，,。；;]")
_NOUN_RUN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,24}")
_WINDOW_TAIL_STRIP_RE = re.compile(r"[\s*_`#>|·]+$")
_SEGMENT_EDGE_STRIP_RE = " -—-*_`#>|·"
_LEADING_TABLE_REF_RE = re.compile(r"^表\d+中")
_SUBJECT_ROLE_TRIM_RE = re.compile(r"(?:用例|能力|功能)$")

#: 提取出的claimed subject若是这些泛指词/引导动词则视为无主体（裸ID路径）
_SUBJECT_STOPWORDS = frozenset({
    "接口", "标识", "标识符", "名称", "序号", "编号", "代号", "系统", "软件",
    "服务", "功能", "用例", "部分", "文档", "项目", "需求", "能力", "其他",
    "其他接口", "类似", "答案", "内容", "描述", "提供", "支持", "包括",
    "包含", "使用", "采用",
})


def _key(text: str) -> str:
    """主体比较键：空白折叠+大小写归一（Blob/BLOB同一实体）。"""
    return re.sub(r"\s+", "", text).casefold()


def _norm_subject(raw: str) -> str:
    """规范化主体：去表引用前缀/引号/空白，迭代去"用例|能力|功能"后缀。"""
    subject = raw.strip().strip("「」『』\"' ")
    subject = _LEADING_TABLE_REF_RE.sub("", subject)
    while True:
        trimmed = _SUBJECT_ROLE_TRIM_RE.sub("", subject)
        if trimmed == subject or len(trimmed) < 2:
            break
        subject = trimmed
    return subject.strip()


def _subject_match(a: str, b: str) -> bool:
    """主体匹配：精确相等或（≥3字符的）包含关系。"""
    key_a, key_b = _key(a), _key(b)
    if not key_a or not key_b:
        return False
    if key_a == key_b:
        return True
    shorter = min(len(key_a), len(key_b))
    return shorter >= 3 and (key_a in key_b or key_b in key_a)


def _id_segments(identifier: str) -> list[str]:
    return identifier.split("-")


def _id_family(identifier: str) -> tuple[str, ...]:
    """ID族键=前两段（PZXQ-GN / PZXQ-JK / PZXQ-NBJK），限定冲突比对范围。"""
    segments = _id_segments(identifier)
    return tuple(segments[:2]) if len(segments) >= 2 else tuple(segments)


@dataclass(frozen=True)
class IdRegistration:
    """注册表中一条 (ID, 主体) 绑定，携带定位三元组的证据位置。"""

    identifier: str
    subject: str        # 规范化主体（节标题取"父-子"叶子名）
    full_subject: str   # 完整主体（含"父-子"前缀）
    evidence_id: str
    statement_id: str
    field_name: str

    def subject_matches(self, claimed: str) -> bool:
        return (_subject_match(claimed, self.subject)
                or _subject_match(claimed, self.full_subject))

    def location(self) -> str:
        return f"{self.statement_id}[{self.field_name}]"


@dataclass(frozen=True)
class IdClaim:
    """answer中的一条ID声明：(ID, 声称的主体)，裸ID时subject为None。"""

    identifier: str
    subject: str | None


def _register(registry: dict[str, list[IdRegistration]], identifier: str,
              raw_name: str, statement: EvidenceStatement) -> None:
    full = _norm_subject(raw_name)
    if len(full) < 2 or re.fullmatch(r"[A-Za-z0-9.\-]+", full):
        return
    leaf = full.rsplit("-", 1)[-1] if "-" in full else full
    subject = _norm_subject(leaf) or full
    for existing in registry.get(identifier, ()):
        if (existing.subject == subject
                and existing.statement_id == statement.statement_id):
            return
    registry.setdefault(identifier, []).append(IdRegistration(
        identifier=identifier, subject=subject, full_subject=full,
        evidence_id=statement.evidence_id,
        statement_id=statement.statement_id,
        field_name=statement.field_name))


def build_id_registry(
        statements: list[EvidenceStatement],
        ) -> dict[str, tuple[IdRegistration, ...]]:
    """从线性化证据语句构建 ID → [(主体, 位置, 字段)] 注册表。

    两个确定性提取模式：语句级绑定（能力表"X的项目唯一标识符：ID"、接口表
    "X的接口需求标识：ID"与散文"X的标识为ID"）和节标题绑定（"3.2.X名称
    （ID）"，主体取"父-子"叶子名）。空白先折叠——真实文档存在
    "PZXQ-GN-SQLFW- BLOBSJXG"这类ID内空格。
    """
    registry: dict[str, list[IdRegistration]] = {}
    for statement in statements:
        compact = re.sub(r"\s+", "", statement.text)
        for match in _BINDING_RE.finditer(compact):
            _register(registry, match.group("id"), match.group("name"),
                      statement)
        for match in _SECTION_TITLE_RE.finditer(compact):
            _register(registry, match.group("id"), match.group("name"),
                      statement)
    return {identifier: tuple(items) for identifier, items in registry.items()}


def _claimed_subject(window: str) -> str | None:
    """从ID前窗口提取声称的主体短语（仅限与ID连续的分段）。

    只取最后一个分隔符（冒号/换行/竖线/句读）之后、与ID直接连续的短语，
    不跨列表/标题边界——markdown列表项"- 接口标识：ID"的上一行标题不算
    主体（裸ID路径）。角色词尾（"的项目唯一标识符为"）先剥离。
    """
    trimmed = _WINDOW_TAIL_STRIP_RE.sub("", window)
    if not trimmed:
        return None
    bracket = _BRACKET_SUBJECT_RE.search(trimmed)
    candidates = [bracket.group("subj")] if bracket else []
    stripped = _ROLE_TAIL_RE.sub("", trimmed)
    segment = _SEGMENT_SPLIT_RE.split(stripped)[-1]
    segment = segment.strip(_SEGMENT_EDGE_STRIP_RE)
    if segment:
        run = _NOUN_RUN_RE.search(segment)
        if run:
            candidates.append(run.group(0))
    for candidate in candidates:
        subject = _norm_subject(candidate)
        if len(subject) >= 2 and _key(subject) not in _SUBJECT_STOPWORDS:
            return subject
    return None


def extract_id_claims(answer: str) -> list[IdClaim]:
    """提取answer的 (ID, claimed_subject) 声明，按(ID, 主体)去重。"""
    claims: list[IdClaim] = []
    seen: set[tuple[str, str | None]] = set()
    for match in PZXQ_ID_RE.finditer(answer):
        identifier = match.group(0).rstrip("-")
        window = answer[max(0, match.start() - _ID_WINDOW):match.start()]
        subject = _claimed_subject(window)
        if (identifier, subject) in seen:
            continue
        seen.add((identifier, subject))
        claims.append(IdClaim(identifier=identifier, subject=subject))
    return claims


def _segment_diff(claimed: str, registered: str) -> str:
    """逐段比对两个同族ID，返回差异类型描述（rationale用）。"""
    a, b = _id_segments(claimed), _id_segments(registered)
    if a == b:
        return "组件段一致"
    if sorted(a) == sorted(b):
        return "组件段序颠倒"
    set_a, set_b = set(a), set(b)
    if set_a < set_b:
        return f"缺组件段{'、'.join(sorted(set_b - set_a))}"
    if set_a > set_b:
        return f"多组件段{'、'.join(sorted(set_a - set_b))}"
    return "ID家族错配"


def _subject_clusters(registrations: tuple[IdRegistration, ...],
                      ) -> list[list[IdRegistration]]:
    """按主体互相包含聚簇：同一主体的表侧/节标题侧登记不算双登记。"""
    clusters: list[list[IdRegistration]] = []
    for registration in registrations:
        for cluster in clusters:
            if _subject_match(cluster[0].subject, registration.subject):
                cluster.append(registration)
                break
        else:
            clusters.append([registration])
    return clusters


def _other_id_notes(subject: str,
                    registry: dict[str, tuple[IdRegistration, ...]],
                    exclude: str) -> list[str]:
    """该主体除claimed ID外的其他注册（VIO-01需在rationale暴露LJCPZ）。"""
    notes: list[str] = []
    for identifier, registrations in registry.items():
        if identifier == exclude:
            continue
        matched = next((registration for registration in registrations
                        if registration.subject_matches(subject)), None)
        if matched is not None:
            notes.append(f"{matched.subject}另注册为{identifier}"
                         f"（{matched.location()}）")
    return notes


def _claim_result(request: QAInput, index: int, identifier: str,
                  verdict: str, refs: tuple[str, ...], rationale: str,
                  confidence: float) -> ClaimResult:
    return ClaimResult(
        claim_id=f"{request.instance_id}-idjoin{index:02d}",
        claim_text=identifier,
        verdict=verdict,
        check_item_candidates=CHECK_ITEMS,
        evidence_refs=refs,
        rationale=rationale,
        method=METHOD,
        confidence=confidence,
    )


def _check_double_registration(
        claim: IdClaim,
        registry: dict[str, tuple[IdRegistration, ...]],
        ) -> tuple[str, tuple[str, ...]] | None:
    """检查①：claimed ID被>1个互不包含的主体注册且claimed主体在其中。"""
    if claim.subject is None:
        return None
    registrations = registry.get(claim.identifier, ())
    clusters = _subject_clusters(registrations)
    if len(clusters) < 2:
        return None
    if not any(registration.subject_matches(claim.subject)
               for registration in registrations):
        return None
    subjects_desc = "、".join(
        f"{cluster[0].subject}（{cluster[0].location()}）"
        for cluster in clusters)
    notes = _other_id_notes(claim.subject, registry, claim.identifier)
    rationale = (f"ID双登记：{claim.identifier}同时注册给主体{subjects_desc}；"
                 f"answer声称「{claim.subject}」持有该ID——项目唯一标识符"
                 f"应一主体一ID，唯一性被违反（TERM-07同ID双登记）")
    if notes:
        rationale += "；" + "；".join(notes)
    refs = tuple(dict.fromkeys(
        registration.statement_id for cluster in clusters
        for registration in cluster))
    return rationale, refs


def _binding_candidates(
        claim: IdClaim,
        registry: dict[str, tuple[IdRegistration, ...]],
        ) -> dict[str, list[IdRegistration]]:
    """同族ID的主体绑定候选：精确优先分层（G4 P1 a-fix）。

    第一层（精确）：注册主体（叶子名或"父-子"全名）与claimed主体
    规范化相等——claimed (主体, ID) 的精确绑定与同主体其他注册都
    在这一层仲裁（VIO-02/03/04/05全部经由精确层检出）。
    第二层（包含回退，仅当无任何精确命中）：包含方向固定为
    claimed ⊂ registered（answer用注册条目的简写/上位形态）；
    声称子功能而注册表只有父条目（registered ⊂ claimed，如声称
    「修改数据记录」时父功能「修改数据」的注册）不算命中——父功能
    的注册不仲裁子功能声称的ID，否则父子两级被混为同主体造成
    误refute（S1QA-053：子功能的精确绑定本身就在注册表里）。
    """
    family = _id_family(claim.identifier)
    claimed_key = _key(claim.subject)
    exact: dict[str, list[IdRegistration]] = {}
    contained: dict[str, list[IdRegistration]] = {}
    for identifier, registrations in registry.items():
        if _id_family(identifier) != family:
            continue
        for registration in registrations:
            registered_keys = (_key(registration.subject),
                               _key(registration.full_subject))
            if claimed_key in registered_keys:
                exact.setdefault(identifier, []).append(registration)
                continue
            if any(len(claimed_key) >= 3
                   and len(claimed_key) < len(registered_key)
                   and claimed_key in registered_key
                   for registered_key in registered_keys):
                contained.setdefault(identifier, []).append(registration)
    return exact or contained


def _check_subject_binding(
        claim: IdClaim,
        registry: dict[str, tuple[IdRegistration, ...]],
        ) -> tuple[str, tuple[str, ...]] | None:
    """检查②③：同族注册中，claimed主体的注册ID与claimed ID不一致。

    ② subject-ID错配：claimed ID不在该主体的注册集合中（VIO-02/03）；
    ③ 组件段比对：claimed ID在注册集合中但存在同主体的其他注册
    （VIO-04段序颠倒/VIO-05缺段）。主体匹配用精确优先分层
    （见_binding_candidates），仅当主体命中且ID同族时触发。
    """
    if claim.subject is None:
        return None
    matched = _binding_candidates(claim, registry)
    if not matched:
        return None
    others = [identifier for identifier in matched
              if identifier != claim.identifier]
    if not others:
        return None
    def closeness(identifier: str) -> tuple[int, int]:
        segments = set(_id_segments(identifier)) & set(
            _id_segments(claim.identifier))
        return (len(segments), len(identifier))
    other = max(others, key=closeness)
    registrations = matched[other]
    diff = _segment_diff(claim.identifier, other)
    if claim.identifier in matched:
        headline = "ID绑定冲突"
    else:
        headline = "subject-ID错配"
    rationale = (f"{headline}：主体「{claim.subject}」在注册表中登记为"
                 f"{other}（{registrations[0].location()}），与answer声称的"
                 f"{claim.identifier}不一致——{diff}"
                 f"（TERM-07同主体ID冲突）")
    refs = tuple(dict.fromkeys(
        [registration.statement_id
         for registration in registry.get(claim.identifier, ())]
        + [registration.statement_id
           for identifier in matched for registration in matched[identifier]]))
    return rationale, refs


def verify_id_joins(request: QAInput,
                    statements: list[EvidenceStatement],
                    ) -> list[ClaimResult]:
    """对冻结QA输入执行四项ID join检查（L1确定性，TERM-07）。

    返回method="id_join_registry"的ClaimResult列表；claim_text为裸ID，
    per-claim融合（refute>support>NIE）中本专家的refute压制identifier
    通道对同ID的误support。无PZXQ声明或注册表为空时返回[]。
    """
    registry = build_id_registry(statements)
    if not registry:
        return []
    claims = extract_id_claims(request.answer)
    results: list[ClaimResult] = []
    for index, claim in enumerate(claims, start=1):
        if claim.subject is not None:
            fired = _check_double_registration(claim, registry)
            if fired is None:
                fired = _check_subject_binding(claim, registry)
            if fired is not None:
                rationale, refs = fired
                results.append(_claim_result(
                    request, index, claim.identifier, "refute", refs,
                    rationale, 1.0))
            continue
        registrations = registry.get(claim.identifier, ())
        verbatim = any(claim.identifier in ev.text for ev in request.evidence)
        if registrations and verbatim:
            refs = tuple(dict.fromkeys(
                registration.statement_id
                for registration in registrations[:2]))
            results.append(_claim_result(
                request, index, claim.identifier, "support", refs,
                f"裸ID声明{claim.identifier}与注册表绑定一致"
                f"（{registrations[0].location()}）", 0.9))
            continue
        results.append(_claim_result(
            request, index, claim.identifier, "not_in_evidence", (),
            f"裸ID声明{claim.identifier}未在ID注册表中登记，无法绑定主体",
            0.5))
    return results


__all__ = [
    "CHECK_ITEMS",
    "METHOD",
    "IdClaim",
    "IdRegistration",
    "build_id_registry",
    "extract_id_claims",
    "verify_id_joins",
]
