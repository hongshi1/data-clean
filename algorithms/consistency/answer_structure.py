"""Deterministic answer structural decomposition.

Real answers are Markdown structures (numbered steps, bold headers,
multi-line sentences). The old blob fallback turned 74% of them into a
single claim, destroying claim-level localization. This module splits
answers into atomic structural claims, each carrying a scope hint for
evidence-statement pairing.

This layer is deterministic: structure rules only, no model calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_BULLET_SPLIT = re.compile(r"\n\s*(?=\d+[.)、]\s|[-*•]\s|\*\*)")
_SENTENCE_SPLIT = re.compile(r"(?<=[。；！？])")
_MIN_CLAIM_CHARS = 6
_SCOPE_HINT = re.compile(
    r"(?:[「\"](?P<quoted>[^」\"]{2,16})[」\"])"
    r"|(?P<name>[\u4e00-\u9fffA-Za-z]{2,14})"
    r"(?=用例|流程|接口|功能|状态下)"
    r"|(?P<possessive>[\u4e00-\u9fffA-Za-z]{2,14})"
    r"(?=的(?:前置条件|主事件流|后置条件|异常流|标识符?|名称|步骤|参数))")


@dataclass(frozen=True)
class StructuredClaim:
    """One atomic answer claim with a scope hint for pairing."""

    text: str
    scope_hint: str
    structure: str  # step | bullet | sentence | header
    claim_id: str


def _clean_segment(segment: str) -> str:
    text = segment.replace("**", "").replace("###", "")
    text = re.sub(r"^\s*(?:\d+[.)、]|[-*•])\s*", "", text)
    text = re.sub(r"^\s*(?:答案|回答|Answer)\s*[：:]\s*", "", text)
    return re.sub(r"\s+", " ", text).strip(" ：:，,\n")


def _extract_scope(text: str, question: str) -> str:
    for source in (text, question):
        match = _SCOPE_HINT.search(source)
        if match:
            return (match.group("quoted") or match.group("name")
                    or match.group("possessive") or "")
    return ""


def decompose_answer(answer: str, question: str = "") -> list[StructuredClaim]:
    """Split a real answer into atomic structural claims with scope hints."""
    claims: list[StructuredClaim] = []
    for segment in _BULLET_SPLIT.split(answer):
        cleaned = _clean_segment(segment)
        if not cleaned:
            continue
        structure = "step"
        if re.match(r"^[-*•]", segment.strip()):
            structure = "bullet"
        elif re.match(r"^\*\*", segment.strip()):
            structure = "header"
        header_prefix = ""
        if structure == "header" and "：" in cleaned.split("。")[0]:
            header_prefix = cleaned.split("：", 1)[0]
        for sentence in _SENTENCE_SPLIT.split(cleaned):
            text = sentence.strip(" 。：:，,；\n")
            if len(text) < _MIN_CLAIM_CHARS:
                continue
            scope = _extract_scope(text, question) or header_prefix
            claims.append(StructuredClaim(
                text=text,
                scope_hint=scope,
                structure=structure,
                claim_id=f"ac{len(claims) + 1:02d}",
            ))
    if not claims:
        fallback = _clean_segment(answer)
        if len(fallback) >= _MIN_CLAIM_CHARS:
            claims.append(StructuredClaim(
                text=fallback, scope_hint=_extract_scope(fallback, question),
                structure="sentence", claim_id="ac01"))
    return claims


def pair_statements(claims: list[StructuredClaim],
                    statements: list) -> list[tuple]:
    """Scope-first pairing: bind each claim to evidence statements.

    Scope-matched statements are preferred. When no scope match exists the
    claim pairs with every statement of the frozen context: retrieval is
    already question-conditioned, so cross-scope field conflicts remain
    visible to the residual NLI channel (neutral pairs are harmless).
    """
    pairs: list[tuple] = []
    for claim in claims:
        scope = re.sub(r"\s+", "", claim.scope_hint)
        matched = ([statement for statement in statements
                    if scope and statement.scope_key
                    and (scope in statement.scope_key
                         or statement.scope_key in scope)]
                   if scope else [])
        if matched:
            pairs.extend((claim, statement) for statement in matched)
        else:
            pairs.extend((claim, statement) for statement in statements)
    return pairs


__all__ = ["StructuredClaim", "decompose_answer", "pair_statements"]
