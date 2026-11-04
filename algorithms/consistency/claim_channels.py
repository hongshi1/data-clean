"""Deterministic per-claim verification channels for the QA module.

Migrated from ``algorithms.consistency.qa_module`` in the Wave 8-H2
architecture split with unchanged behavior. Each channel takes the
frozen request plus one ``AnswerClaim`` and returns a ``ClaimResult``:

- ``verify_numeric`` — numeric interval containment/disjointness;
- ``verify_quoted`` — explicit quote polarity in the evidence;
- ``verify_enum`` — enum member exact match with explicit exclusion;
- ``verify_identifier`` — identifier exact match / same-subject mismatch;
- ``verify_semantic`` — exact statement match, with the optional residual
  NLI judge (``SemanticNliJudge`` carries the former instance state:
  the predictor callable and its two calibrated thresholds).

Shared helpers (``interval`` / ``subset`` / ``disjoint`` /
``same_subject`` / ``unresolved``) are also module-level pure functions
here. This layer is deterministic: no model calls except the explicitly
injected NLI judge.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from algorithms.consistency.answer_claims import (
    _IDENTIFIER,
    AnswerClaim,
    extract_numeric_claims,
)
from algorithms.consistency.answer_structure import (
    decompose_answer,
    pair_statements,
)
from algorithms.consistency.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    Verdict,
)
from algorithms.consistency.templates import normalize_op, normalize_unit

#: explicit negation markers preceding a matched item (former
#: ``QAConsistencyModule._EXPLICIT_NEGATION`` class attribute)
_EXPLICIT_NEGATION = re.compile(
    r"(?:不包括|不包含|不支持|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)"
)

#: claim-text keyword -> statement field slots for the residual NLI
#: channel (former ``QAConsistencyModule._SLOT_FIELDS`` class attribute)
_SLOT_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("前置条件", ("前置条件",)),
    ("后置条件", ("后置条件",)),
    ("异常流", ("异常流",)),
    ("参与者", ("Actors", "参与者")),
    ("Actor", ("Actors", "参与者")),
)

#: residual NLI predictor contract: list of (statement, hypothesis)
#: pairs -> NLI labels (dict with label/p_contra/p_entail or bare label)
NliPredictor = Callable[[list[tuple[str, str]]], list]


@dataclass(frozen=True)
class SemanticNliJudge:
    """Instance-level NLI configuration for the residual semantic channel.

    Carries the former QAConsistencyModule state: the predictor callable
    and the two calibrated decision thresholds.
    """

    predictor: NliPredictor
    contra_threshold: float
    entail_threshold: float


def unresolved(request: QAInput, claim: AnswerClaim, index: int,
               check_items: tuple[str, ...], rationale: str,
               refs: tuple[str, ...] = ()) -> ClaimResult:
    """Conservative not-in-evidence ClaimResult (former ``_unresolved``)."""
    return ClaimResult(
        claim_id=f"{request.instance_id}-c{index:02d}",
        claim_text=claim.text,
        verdict="not_in_evidence",
        check_item_candidates=check_items,
        evidence_refs=refs,
        rationale=rationale,
        method="conservative_unresolved",
        confidence=0.0,
    )


def same_subject(answer_subject: str, evidence_subject: str,
                 question: str) -> bool:
    """Subject match with question-anchored short-form acceptance."""
    a = re.sub(r"\s+", "", answer_subject).removesuffix("的")
    e = re.sub(r"\s+", "", evidence_subject).removesuffix("的")
    if not a or not e:
        return False
    if a == e:
        return True
    # Short answer may use an unqualified form of the question's parameter
    # (e.g. answer "响应时间" vs evidence "系统响应时间"). Accept only when
    # one is a qualified form of the other and the unqualified form appears
    # in the question, so unrelated parameters are not silently merged.
    if a in e or e in a:
        shorter = a if len(a) < len(e) else e
        return shorter in re.sub(r"\s+", "", question)
    return False


def interval(operator: str, value: float) -> tuple[float, bool, float, bool] | None:
    op = normalize_op(operator)
    if op == "le":
        return float("-inf"), False, value, True
    if op == "lt":
        return float("-inf"), False, value, False
    if op == "ge":
        return value, True, float("inf"), False
    if op == "gt":
        return value, False, float("inf"), False
    if op == "eq":
        return value, True, value, True
    return None


def subset(a: tuple[float, bool, float, bool],
           b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    lower_ok = al > bl or (al == bl and (not alc or blc))
    upper_ok = au < bu or (au == bu and (not auc or buc))
    return lower_ok and upper_ok


def disjoint(a: tuple[float, bool, float, bool],
             b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    a_before_b = au < bl or (au == bl and not (auc and blc))
    b_before_a = bu < al or (bu == al and not (buc and alc))
    return a_before_b or b_before_a


def verify_numeric(request: QAInput, claim: AnswerClaim,
                   index: int, check_items: tuple[str, ...]) -> ClaimResult:
    answer_unit = normalize_unit(claim.value, claim.unit)
    if answer_unit is None:
        return unresolved(request, claim, index, check_items,
                          "answer数值单位无法归一化")
    answer_interval = interval(claim.operator, answer_unit[0])
    if answer_interval is None:
        return unresolved(request, claim, index, check_items,
                          "answer操作符不在已验证范围")

    matches: list[tuple[RetrievedEvidence, Verdict, str]] = []
    for evidence in request.evidence:
        for attr, operator, value, unit in extract_numeric_claims(evidence.text):
            if not same_subject(claim.attr, attr, request.question):
                continue
            ev_unit = normalize_unit(value, unit)
            if ev_unit is None or ev_unit[1] != answer_unit[1]:
                continue
            ev_interval = interval(operator, ev_unit[0])
            if ev_interval is None:
                continue
            if (subset(ev_interval, answer_interval)
                    or subset(answer_interval, ev_interval)):
                matches.append((evidence, "support", "context约束蕴含answer约束"))
            elif disjoint(ev_interval, answer_interval):
                matches.append((evidence, "refute", "context与answer数值区间互斥"))
            else:
                matches.append((evidence, "not_in_evidence",
                                "数值区间重叠但不互相蕴含，无法证明一致或矛盾"))
    decisive = [x for x in matches if x[1] in ("support", "refute")]
    decisive_labels = {x[1] for x in decisive}
    if len(decisive_labels) > 1:
        return unresolved(request, claim, index, check_items,
                          "冻结context含相互冲突的数值证据",
                          tuple(sorted({x[0].evidence_id for x in decisive})))
    if decisive:
        ev, verdict, reason = decisive[0]
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict=verdict,
            check_item_candidates=check_items,
            evidence_refs=(ev.evidence_id,),
            rationale=reason,
            method="numeric_interval",
            confidence=1.0,
        )
    refs = tuple(sorted({x[0].evidence_id for x in matches}))
    return unresolved(request, claim, index, check_items,
                      matches[0][2] if matches else "context无同subject/单位数值证据",
                      refs)


def verify_quoted(request: QAInput, claim: AnswerClaim,
                  index: int, check_items: tuple[str, ...]) -> ClaimResult:
    target = re.sub(r"\s+", "", claim.text)
    positive_refs: list[str] = []
    negative_refs: list[str] = []
    for ev in request.evidence:
        normalized = re.sub(r"\s+", "", ev.text)
        start = 0
        while True:
            pos = normalized.find(target, start)
            if pos < 0:
                break
            prefix = normalized[max(0, pos - 14):pos]
            if _EXPLICIT_NEGATION.search(prefix):
                negative_refs.append(ev.evidence_id)
            else:
                positive_refs.append(ev.evidence_id)
            start = pos + len(target)

    supporting_refs = negative_refs if claim.negative else positive_refs
    refuting_refs = positive_refs if claim.negative else negative_refs
    if supporting_refs:
        if refuting_refs:
            return unresolved(
                request, claim, index, check_items,
                "冻结context对同一引用项同时包含支持和显式否定证据",
                tuple(sorted(set(supporting_refs + refuting_refs))),
            )
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(supporting_refs))),
            rationale="answer声明的极性与context中的显式提及一致",
            method="explicit_quote_polarity",
            confidence=1.0,
        )
    if refuting_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="refute",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(refuting_refs))),
            rationale="context对answer引用项存在显式相反极性",
            method="explicit_quote_polarity",
            confidence=1.0,
        )
    closed = [ev for ev in request.evidence
              if ev.completeness == "closed" and ev.completeness_proof.strip()]
    if (closed and len(closed) == len(request.evidence)
            and all(ev.scope_id == closed[0].scope_id for ev in closed)):
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support" if claim.negative else "refute",
            check_item_candidates=check_items,
            evidence_refs=tuple(ev.evidence_id for ev in closed),
            rationale="封闭scope中未出现该条目，与answer极性相符",
            method="closed_scope_exclusion",
            confidence=0.85,
        )
    return unresolved(request, claim, index, check_items,
                      "引用项未命中冻结context，scope不完整或未证明穷举")


def verify_identifier(request: QAInput, claim: AnswerClaim,
                      index: int, check_items: tuple[str, ...]) -> ClaimResult:
    """Exact identifier matching against the frozen evidence (TERM-07).

    support: the answer identifier appears verbatim in the evidence.
    refute: the evidence states a different identifier for the same
    subject statement. Everything else stays NIE.
    """
    target = claim.text
    subject = re.sub(r"\s+", "", claim.attr or "")
    subject_core = re.sub(
        r"(?:用例)?(?:的)?(?:唯一)?(?:标识符?|编号|代号|名称|项目名)?$",
        "", subject)
    if len(subject_core) < 2:
        subject_core = subject
    hit_refs = tuple(
        ev.evidence_id for ev in request.evidence
        if target in ev.text
    )
    if hit_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=hit_refs,
            rationale="answer标识符在冻结context中精确出现",
            method="identifier_exact_match",
            confidence=1.0,
        )
    if subject_core:
        for ev in request.evidence:
            compact = re.sub(r"\s+", "", ev.text)
            start = compact.find(subject_core)
            while start >= 0:
                window = compact[max(0, start - 30):
                                  min(len(compact), start + len(subject_core) + 100)]
                window_ids = _IDENTIFIER.findall(window)
                if len(window_ids) == 1 and window_ids[0] != target:
                    return ClaimResult(
                        claim_id=f"{request.instance_id}-c{index:02d}",
                        claim_text=claim.text,
                        verdict="refute",
                        check_item_candidates=check_items,
                        evidence_refs=(ev.evidence_id,),
                        rationale=("同subject局部窗口中context声明了不同标识符"
                                   f"（{window_ids[0]}），显式值冲突"),
                        method="identifier_exact_match",
                        confidence=1.0,
                    )
                start = compact.find(subject_core, start + 1)
    return unresolved(request, claim, index, check_items,
                      "标识符未在冻结context命中，且无同subject的显式不同值")


def verify_enum(request: QAInput, claim: AnswerClaim,
                index: int, check_items: tuple[str, ...]) -> ClaimResult:
    """Legacy per-member substring enum channel.

    Known design flaw: member-level hits can mask set-level conflicts
    (e.g. answer {A,B,C} vs evidence {A,B} where each member hits
    individually). The ``enum_join_expert`` (L1) handles set-level joins
    with domain registries. This legacy channel is retained only for
    explicit-exclusion detection (context explicitly negates a member),
    and its per-member "all found -> support" path is downgraded to
    NIE to avoid false supports when the evidence set is not proven
    exhaustive.
    """
    items = [part.strip() for part in re.split(r"[、，,；]", claim.text)
             if len(part.strip()) >= 2]
    found: dict[str, list[str]] = {}
    excluded: dict[str, list[str]] = {}
    for item in items:
        needle = re.sub(r"\s+", "", item)
        found[item] = []
        excluded[item] = []
        for ev in request.evidence:
            text = re.sub(r"\s+", "", ev.text)
            start = 0
            while True:
                pos = text.find(needle, start)
                if pos < 0:
                    break
                prefix = text[max(0, pos - 14):pos]
                target = excluded if _EXPLICIT_NEGATION.search(prefix) else found
                target[item].append(ev.evidence_id)
                start = pos + len(needle)
    explicit_exclusions = tuple(sorted({
        ref for refs in excluded.values() for ref in refs
    }))
    positive_refs = tuple(sorted({ref for refs in found.values() for ref in refs}))
    if explicit_exclusions and positive_refs:
        return unresolved(
            request, claim, index, check_items,
            "枚举context同时含正向命中与显式排除，需仲裁context内部冲突",
            tuple(sorted(set(explicit_exclusions + positive_refs))),
        )
    if explicit_exclusions:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="refute",
            check_item_candidates=check_items,
            evidence_refs=explicit_exclusions,
            rationale="context对answer枚举成员存在显式排除语句",
            method="explicit_enum_exclusion",
            confidence=1.0,
        )
    missing = [item for item, refs in found.items() if not refs]
    refs = positive_refs
    if not missing:
        return unresolved(
            request, claim, index, check_items,
            "枚举成员均在context出现，但context未证明穷举；"
            "集合级比对由enum_join专家负责",
            refs)
    return unresolved(request, claim, index, check_items,
                      f"枚举成员未全部命中({len(missing)}项)；未证明context穷举", refs)


def verify_semantic(request: QAInput, claim: AnswerClaim,
                    index: int, check_items: tuple[str, ...],
                    statements: tuple,
                    judge: SemanticNliJudge | None = None) -> ClaimResult:
    answer_text = re.sub(r"\s+", "", claim.text)
    exact_refs = tuple(
        ev.evidence_id for ev in request.evidence
        if answer_text and answer_text in re.sub(r"\s+", "", ev.text)
    )
    if exact_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=exact_refs,
            rationale="answer原子声明在冻结context中精确出现",
            method="exact_statement",
            confidence=1.0,
        )
    for statement in statements:
        if answer_text and answer_text in re.sub(r"\s+", "", statement.text):
            return ClaimResult(
                claim_id=f"{request.instance_id}-c{index:02d}",
                claim_text=claim.text,
                verdict="support",
                check_item_candidates=check_items,
                evidence_refs=(statement.evidence_id,),
                rationale=(f"answer声明与线性化证据语句精确匹配"
                           f"（{statement.statement_id}）"),
                method="statement_exact",
                confidence=1.0,
            )
    nli_result = verify_semantic_nli(request, claim, index,
                                     check_items, statements, judge)
    if nli_result is not None:
        return nli_result
    return ClaimResult(
        claim_id=f"{request.instance_id}-c{index:02d}",
        claim_text=claim.text,
        verdict="not_in_evidence",
        check_item_candidates=check_items,
        evidence_refs=(),
        rationale="当前语义声明没有经过验证的三态判定器；不将旧pair二分类结果映射为三态。",
        method="semantic_unresolved",
        confidence=0.0,
    )


def verify_semantic_nli(request: QAInput, claim: AnswerClaim,
                        index: int, check_items: tuple[str, ...],
                        statements: tuple,
                        judge: SemanticNliJudge | None) -> ClaimResult | None:
    """Residual NLI channel on scope- and slot-matched statement pairs."""
    if judge is None or not statements:
        return None
    structured = decompose_answer(claim.text, request.question)
    if not structured:
        return None
    pairs = pair_statements(structured, list(statements))
    if not pairs:
        return None
    claim_slots = tuple(
        field for keyword, fields in _SLOT_FIELDS
        if keyword in claim.text for field in fields)
    if claim_slots:
        pairs = [(structural, statement) for structural, statement in pairs
                 if statement.field_name in claim_slots]
    if not pairs:
        return None
    hypotheses = [(statement.text, structural.text)
                  for structural, statement in pairs]
    labels = judge.predictor(hypotheses)
    contradiction_refs = []
    entailment_refs = []
    scope = re.sub(r"\s+", "", claim.attr or "")
    for (structural, statement), label in zip(pairs, labels):
        verdict = (str(label.get("label", "neutral"))
                   if isinstance(label, dict) else str(label))
        contra_prob = (float(label.get("p_contra", 0.0))
                       if isinstance(label, dict) else
                       (1.0 if verdict == "contradiction" else 0.0))
        entail_prob = (float(label.get("p_entail", 0.0))
                       if isinstance(label, dict) else
                       (1.0 if verdict == "entailment" else 0.0))
        scope_matched = (scope and statement.scope_key
                         and (scope in statement.scope_key
                              or statement.scope_key in scope))
        if (verdict == "contradiction"
                and contra_prob >= judge.contra_threshold
                and scope_matched):
            contradiction_refs.append(statement.evidence_id)
        elif verdict == "entailment" and entail_prob >= judge.entail_threshold:
            entailment_refs.append(statement.evidence_id)
    if contradiction_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="refute",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(contradiction_refs))),
            rationale="scope匹配的证据语句与answer声明NLI矛盾",
            method="nli_residual",
            confidence=0.9,
        )
    if entailment_refs:
        return ClaimResult(
            claim_id=f"{request.instance_id}-c{index:02d}",
            claim_text=claim.text,
            verdict="support",
            check_item_candidates=check_items,
            evidence_refs=tuple(sorted(set(entailment_refs))),
            rationale="scope匹配的证据语句NLI蕴含answer声明",
            method="nli_residual",
            confidence=0.9,
        )
    return None
