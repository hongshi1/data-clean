"""Answer claim decomposition v2 — audit-driven fix layer over v1.

The claim extraction audit (tools/audit_claim_extraction.py, 91QA) found
three defects in ``answer_claims.decompose_claims`` (v1) that the
decomposition ablation (tools/eval_decomp_ablation.py) confirmed to be
performance-relevant:

- **colon-fused claims (37%)**: a "题名：描述" markdown line
  ("**添加**：向数据库中插入数据") survives sentence splitting as ONE
  semantic claim — two assertions glued together, too long for the NLI
  residual channel to verify (S1QA-066/069/077 support failures);
- **framework-sentence noise (3%)**: "有以下特点" lead-ins carry no
  assertion but are counted as claims;
- **open-list enum claims**: "…如…" enumerations are open lists, not
  closed sets; closed-set enum comparison on them is invalid.

v2 keeps the v1 typed extraction (numeric / quoted / enum / identifier)
bit-identical — it calls ``decompose_claims`` and post-processes the
output with four deterministic fixes:

1. **colon split** — a semantic claim "题名：描述" with a short title
   (2–10 chars) and a substantial description (≥8 chars) splits into two
   semantic claims (title assertion + description assertion);
2. **framework filter** — claims matching ``(以下|如下)(特点|操作|功能…)``
   under 30 chars are dropped (no assertion value);
3. **subject inheritance** — a verb-initial description claim inherits
   the colon title as ``attr`` (subject-dropped sentences: the title is
   the subject for scope/subject matching downstream);
4. **open-list enum downgrade** — enum claims containing "如" or
   "包括但不限于" become semantic claims (open lists skip the closed-set
   enum comparison and fall to NLI).

Safety guard: if every claim were filtered away the v1 claim list is
returned unchanged — the claim set must never be empty (cross-claim
aggregation of an empty set degenerates to "support").

This layer is deterministic: regex rules only, no model calls.
"""
from __future__ import annotations

import re

from algorithms.consistency.answer_claims import (
    AnswerClaim,
    decompose_claims,
)

#: framework lead-ins with no assertion value ("有以下特点", "如下操作"…)
_FRAMEWORK_SENTENCE = re.compile(
    r"(?:以下|如下)(?:特点|操作|功能|几类|要求|参数|步骤|内容|方面)")
_FRAMEWORK_MAX_LEN = 30

#: colon-split thresholds: "题名：描述" splits only when the title is a
#: compact term (2–10 chars) and the description carries real content
#: (≥8 chars) — a long pre-colon text is a sentence, not a fused title
_COLON_TITLE_MIN = 2
_COLON_TITLE_MAX = 10
_COLON_DESC_MIN = 8

#: sentence-initial verbs/prepositions of subject-dropped description
#: claims ("提供对查询结果的数据缓存功能…"): such sentences omit the
#: real subject, which the colon title carries
_VERB_STARTS: tuple[str, ...] = (
    "提供", "支持", "允许", "包括", "包含", "涉及", "根据", "实现",
    "采用", "使用", "通过", "基于", "分为", "能够", "可以", "针对",
    "利用", "借助", "按照", "对", "从", "向", "将", "在", "当", "若",
    "需", "应", "可", "能",
)

#: open-list markers: an enum whose items are exemplified ("如…") is an
#: open list — closed-set comparison against it is invalid
_OPEN_LIST_MARKERS: tuple[str, ...] = ("如", "包括但不限于")


def _is_framework_sentence(text: str) -> bool:
    """True for a short lead-in claim with no assertion value."""
    return len(text) < _FRAMEWORK_MAX_LEN and bool(
        _FRAMEWORK_SENTENCE.search(text))


def _colon_split(text: str) -> tuple[str, str] | None:
    """Split "题名：描述" into (title, description); None when not fused.

    The first full-width colon wins (a "A：B：C" chain splits once); the
    pre-colon text must be a compact title, the post-colon text a real
    description.
    """
    position = text.find("：")
    if position < 0:
        return None
    title = text[:position].strip()
    description = text[position + 1:].strip()
    if not _COLON_TITLE_MIN <= len(title) <= _COLON_TITLE_MAX:
        return None
    if len(description) < _COLON_DESC_MIN:
        return None
    return title, description


def _split_semantic_claim(claim: AnswerClaim) -> list[AnswerClaim]:
    """Fix 1 + fix 3 applied to one semantic claim."""
    parts = _colon_split(claim.text)
    if parts is None:
        return [claim]
    title, description = parts
    description_attr = (title if description.startswith(_VERB_STARTS)
                        else claim.attr)
    return [
        AnswerClaim("semantic", title, attr=claim.attr),
        AnswerClaim("semantic", description, attr=description_attr),
    ]


def _needs_open_list_downgrade(claim: AnswerClaim) -> bool:
    """Fix 4 trigger: enum claim whose item list is open ("如"…)."""
    return any(marker in claim.text for marker in _OPEN_LIST_MARKERS)


def _apply_fixes(base: list[AnswerClaim]
                 ) -> tuple[list[AnswerClaim], dict[str, int]]:
    """Run fixes 1–4 over one v1 claim list → (fixed claims, trigger counts).

    The returned claim list is unfiltered only in the degenerate case
    where every claim would be dropped (handled by the caller).
    """
    fixed: list[AnswerClaim] = []
    splits = 0
    downgrades = 0
    for claim in base:
        if claim.kind == "enum" and _needs_open_list_downgrade(claim):
            claim = AnswerClaim("semantic", claim.text)
            downgrades += 1
        if claim.kind == "semantic":
            expanded = _split_semantic_claim(claim)
            splits += len(expanded) - 1
            fixed.extend(expanded)
        else:
            fixed.append(claim)
    kept = [claim for claim in fixed
            if not _is_framework_sentence(claim.text)]
    return kept, {
        "colon_splits": splits,
        "enum_open_list_downgrades": downgrades,
        "framework_drops": len(fixed) - len(kept),
    }


def decompose_claims_v2(question: str, answer: str) -> list[AnswerClaim]:
    """v1 typed extraction + colon split + framework filter + subject
    inheritance + open-list enum downgrade.

    Typed extraction (numeric / quoted / enum / identifier) is delegated
    unchanged to :func:`answer_claims.decompose_claims`; only its
    semantic claims (structural / whole-answer fallback) are split, and
    only its open-list enum claims are downgraded to semantic.
    """
    base = decompose_claims(question, answer)
    fixed, _ = _apply_fixes(base)
    return fixed if fixed else base


def fix_trigger_stats(question: str, answer: str) -> dict[str, int]:
    """Deterministic audit of which v2 fixes fire on one (question, answer).

    Counts: semantic claims colon-split (each yields +1 claim), claims
    dropped as framework sentences, enum claims downgraded from open
    lists. Diagnostic only — the numbers in decompose_claims_v2 itself
    stay the single source of truth.
    """
    base = decompose_claims(question, answer)
    fixed, stats = _apply_fixes(base)
    if not fixed:
        # degenerate all-filtered answer: the guard kept the v1 claims
        stats["framework_drops"] = 0
    return stats


__all__ = ["decompose_claims_v2", "fix_trigger_stats"]
