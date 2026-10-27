"""Answer claim extraction for the post-retrieval QA consistency module.

Deterministic decomposition of a free-form answer into atomic verifiable
claims (numeric / quoted / enum / identifier, with a structural semantic
fallback). Extracted from ``algorithms.consistency.qa_module`` in the
Wave 8-H2 architecture split with unchanged behavior:

- ``AnswerClaim`` — the per-claim dataclass shared by all channels;
- the module-level extraction patterns (``_NUMERIC_PREFIX`` …);
- ``extract_numeric_claims`` / ``extract_enum_claims`` — reusable claim
  extractors (also consumed by the numeric_z3 expert);
- ``question_numeric_subject`` — short-numeric-answer subject resolution;
- ``decompose_claims`` — the former ``QAConsistencyModule._decompose``
  extraction logic.

This layer is deterministic: patterns only, no model calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from algorithms.consistency.answer_structure import decompose_answer
from algorithms.consistency.qa_router import route_question


@dataclass(frozen=True)
class AnswerClaim:
    """One atomic answer claim produced by decomposition."""

    kind: str
    text: str
    attr: str = ""
    operator: str = ""
    value: str = ""
    unit: str = ""
    negative: bool = False


_OPERATOR_PATTERN = (
    r"不大于|不超过|不高于|小于等于|不小于|不少于|不低于|大于等于|"
    r"不小于|不大于|至少|最多|至多|最低|大于|小于|≤|≥|<=|>=|<|>|为|等于|="
)
_NUMERIC_PREFIX = re.compile(
    rf"(?P<op>{_OPERATOR_PATTERN})\s*(?P<value>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节|%|条|个|次|种|路)?"
)
_NUMERIC_POSTFIX = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节|%|条|个|次|种|路)\s*"
    r"(?P<op>以上|及以上|以下|及以下)"
)
_ENUM_PREFIX = re.compile(r"(?:包括|包含|分别为|如下)[：:]?\s*(?P<items>[^。；\n]{3,100})")
_ANSWER_NUMBER = re.compile(r"(?<!\d)(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|毫秒|min|分钟|s|秒|GB|MB|KB|B|字节|%|条|个|次|种|路|小时)")
_IDENTIFIER = re.compile(
    r"(?<![A-Z0-9-])[A-Z]{2,8}(?:-[A-Z0-9]{1,12}){1,6}(?![A-Z0-9-])")
#: quoted-term extraction for the quoted claim kind (former
#: ``QAConsistencyModule._QUOTED`` class attribute)
_QUOTED = re.compile(r"[「\"]([^「」\"]{2,80})[」\"]")
#: negation markers in the prefix of a quoted term (former
#: ``QAConsistencyModule._NEGATIVE`` class attribute)
_NEGATIVE = re.compile(r"(?:不包括|不包含|不支持|没有|不存在|未定义|不允许)")


def _attribute_before(text: str, start: int) -> str:
    before = text[max(0, start - 48):start].rstrip()
    before = re.split(r"[，,；。！？\n]", before)[-1].strip()
    before = re.sub(
        r"^(?:在|当|若|如果|对于)[^，,；。！？\n]{0,24}"
        r"(?:条件下|情况下|时|之时)\s*",
        "",
        before,
    )
    quoted = re.search(r"[「\"]([^「」\"]{2,24})[」\"]\s*(?:的)?$", before)
    if quoted:
        return quoted.group(1).strip()
    match = re.search(r"([\u4e00-\u9fffA-Za-z]{2,16}?)(?:的)?(?:要求|应|为|是|达到|保持)?\s*$", before)
    if not match:
        return ""
    attr = match.group(1).strip()
    return "" if attr in {"系统", "文档", "功能", "数据", "该", "本", "至少", "最多"} else attr


def extract_numeric_claims(text: str) -> list[tuple[str, str, str, str]]:
    claims: list[tuple[str, str, str, str]] = []
    occupied: list[tuple[int, int]] = []
    for match in _NUMERIC_PREFIX.finditer(text):
        attr = _attribute_before(text, match.start())
        claims.append((attr, match.group("op"), match.group("value"),
                       match.group("unit") or ""))
        occupied.append(match.span())
    for match in _NUMERIC_POSTFIX.finditer(text):
        if any(match.start() < end and start < match.end() for start, end in occupied):
            continue
        op = "以上" if "以上" in match.group("op") else "以下"
        attr = _attribute_before(text, match.start())
        claims.append((attr, op, match.group("value"), match.group("unit")))
    return claims


def extract_enum_claims(text: str) -> list[list[str]]:
    result: list[list[str]] = []
    for match in _ENUM_PREFIX.finditer(text):
        body = re.split(r"[，,；。]其中", match.group("items"), maxsplit=1)[0]
        items = [item.strip(" ：:、，,；") for item in re.split(r"[、，,]", body)]
        items = [item for item in items if 1 < len(item) <= 32]
        if len(items) >= 2:
            result.append(items)
    return result


def question_numeric_subject(question: str) -> str:
    """Resolve a short numeric answer's omitted subject from the question."""
    q = re.sub(r"\s+", "", question)
    match = re.search(
        r"([\u4e00-\u9fffA-Za-z]{2,12}?)(?:要求是多少|是多少|为多少|的上限|的下限|阈值)",
        q,
    )
    subject = match.group(1).removesuffix("的") if match else ""
    return subject.removeprefix("系统")


def decompose_claims(question: str, answer: str) -> list[AnswerClaim]:
    """Split an answer into atomic AnswerClaims (former ``_decompose``)."""
    claims: list[AnswerClaim] = []
    numeric_claims = extract_numeric_claims(answer)
    numeric_question = any(item.startswith("PARAM-") for item in route_question(question))
    if numeric_question:
        values = list(_ANSWER_NUMBER.finditer(answer))
        subject = question_numeric_subject(question)
        explicit_matches = list(_NUMERIC_PREFIX.finditer(answer))
        explicit_matches.extend(_NUMERIC_POSTFIX.finditer(answer))
        bare_values = [
            value for value in values
            if not any(
                match.start() <= value.start() and value.end() <= match.end()
                for match in explicit_matches
            )
        ]
        if len(bare_values) == 1 and subject:
            value = bare_values[0]
            numeric_claims.append(
                (subject, "为", value.group("value"), value.group("unit"))
            )
    for attr, operator, value, unit in numeric_claims:
        if not attr:
            attr = question_numeric_subject(question)
        claims.append(AnswerClaim("numeric", f"{attr} {operator}{value}{unit}",
                                  attr, operator, value, unit))
    for match in _QUOTED.finditer(answer):
        prefix = answer[max(0, match.start() - 12):match.start()]
        claims.append(AnswerClaim("quoted", match.group(1),
                                  negative=bool(_NEGATIVE.search(prefix))))
    for items in extract_enum_claims(answer):
        cleaned = [re.split(r"[，,]", item)[0].strip() for item in items]
        cleaned = [item for item in cleaned if len(item) >= 2]
        if len(cleaned) >= 2:
            claims.append(AnswerClaim("enum", "、".join(cleaned)))
    for identifier in _IDENTIFIER.findall(answer):
        position = answer.find(identifier)
        prefix = answer[max(0, position - 24):position]
        cleaned_prefix = re.sub(
            r"[（(「\",，。：:为是*`_~]+", " ", prefix).rstrip()
        subject_match = re.search(
            r"([\u4e00-\u9fffA-Za-z]{2,16})\s*$", cleaned_prefix)
        subject = subject_match.group(1) if subject_match else ""
        claims.append(AnswerClaim("identifier", identifier, attr=subject))
    if not claims:
        structured = decompose_answer(answer, question)
        for structural in structured:
            claims.append(AnswerClaim(
                "semantic", structural.text, attr=structural.scope_hint))
    if not claims:
        claims.append(AnswerClaim("semantic", answer.strip()))
    return claims
