"""Unified post-retrieval QA consistency module.

Input is ``question + answer + upstream-frozen retrieved context``. This module
does not retrieve context or compare evidence sources with each other.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from algorithms.consistency.llm_residual import REFUTE_CONFIDENCE_GATE
from algorithms.consistency.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    VerificationResult,
    Verdict,
)
from algorithms.consistency.qa_router import route_question
from algorithms.consistency.templates import normalize_op, normalize_unit
from algorithms.consistency.answer_structure import pair_statements
from algorithms.consistency.answer_structure import decompose_answer
from algorithms.consistency.evidence_statements import linearize_context


@dataclass(frozen=True)
class _AnswerClaim:
    kind: str
    text: str
    attr: str = ""
    operator: str = ""
    value: str = ""
    unit: str = ""
    negative: bool = False


#: cross-claim aggregation variants (P1 support-recall study,
#: docs/srs_project/50_support_recall_analysis.md)
AGGREGATION_VARIANTS: tuple[str, ...] = (
    "strict",          # current ∀ semantics: any NIE blocks support
    "dominant_70",     # decidable-claim support ratio >= 0.70 -> support
    "no_minor_block",  # core (non effect/summary) claims all support
)

#: support ratio gate for the dominant_70 aggregation variant
_DOMINANT_SUPPORT_RATIO = 0.70

#: NIE rationales that record an active negative observation from a
#: structured channel — the channel checked the frozen evidence and the
#: claimed content is absent (an explicit decision signal). Only such NIE
#: claims count into the dominant_70 denominator; pure inability NIEs
#: ("时序不可核对"/"未证明穷举"/no validated method) stay outside it.
_ACTIVE_NIE_RATIONALE_MARKERS: tuple[str, ...] = (
    "凭空步骤",             # sequence: answer step absent from the evidence flow
    "无匹配",               # sequence: no flow step matched the answer step
    "未全部命中",           # enum: a claimed member is absent from evidence
    "未在冻结context命中",   # identifier: the claimed ID is absent
    "未命中冻结context",     # quoted: the quoted item is absent
    "无同subject",          # numeric: no same-subject numeric evidence
)

#: claim-text markers of 效果性/总结性 fragments (explanatory/effect
#: extensions and framing/summary sentences). GLM's silver decomposition
#: does not assert them as standalone blocking claims, so the
#: no_minor_block variant refuses to let them veto instance-level support.
_MINOR_CLAIM_MARKERS: tuple[str, ...] = (
    "包括但不限于", "这意味着",
    "有以下特点", "包括以下", "支持以下", "如下", "主要方面", "涵盖了",
    "这些操作", "这些核心操作", "这些能力", "分别是什么",
    "确保", "便于", "旨在",
)

#: compact length under which a claim is a framing fragment, not an
#: assertion (e.g. "4．1.1" table-cell artifacts, "如下" lead-ins)
_MINOR_CLAIM_MAX_LEN = 6

#: leading enumeration prefix stripped from the claim text when computing
#: the per-claim fusion key. Decomposers that re-split numbered answer
#: lists emit "1．X" duplicates of an already-verified "X" claim; the
#: exact-text fusion key cannot merge the twins, so the prefixed NIE
#: fragment vetoes the verified verdict (G4 P1 c-fix,
#: docs/srs_project/50_support_recall_analysis.md §6). claim_text itself
#: is untouched — only the grouping changes.
_FUSION_PREFIX_RE = re.compile(r"^\s*[\d一二三四五六七八九十]+[．.、,，]\s*")


def _is_active_nie(result: ClaimResult) -> bool:
    """True when a NIE claim records an active negative observation."""
    if result.verdict != "not_in_evidence":
        return False
    if result.method == "semantic_unresolved":
        return False
    return any(marker in result.rationale
               for marker in _ACTIVE_NIE_RATIONALE_MARKERS)


def _is_minor_claim(result: ClaimResult) -> bool:
    """True for 效果性/总结性 (effect/summary) claim fragments."""
    text = re.sub(r"\s+", "", result.claim_text)
    if len(text) <= _MINOR_CLAIM_MAX_LEN:
        return True
    return any(marker in result.claim_text for marker in _MINOR_CLAIM_MARKERS)


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


def _extract_numeric_claims(text: str) -> list[tuple[str, str, str, str]]:
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


def _extract_enum_claims(text: str) -> list[list[str]]:
    result: list[list[str]] = []
    for match in _ENUM_PREFIX.finditer(text):
        body = re.split(r"[，,；。]其中", match.group("items"), maxsplit=1)[0]
        items = [item.strip(" ：:、，,；") for item in re.split(r"[、，,]", body)]
        items = [item for item in items if 1 < len(item) <= 32]
        if len(items) >= 2:
            result.append(items)
    return result


def _context_hash(request: QAInput) -> str:
    payload = [{
        "evidence_id": ev.evidence_id,
        "text": ev.text,
        "source_type": ev.source_type,
        "source_ref": ev.source_ref.__dict__,
        "scope_id": ev.scope_id,
        "completeness": ev.completeness,
        "completeness_proof": ev.completeness_proof,
        "extraction_method": ev.extraction_method,
        "extraction_confidence": ev.extraction_confidence,
    } for ev in request.evidence]
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def _interval(operator: str, value: float) -> tuple[float, bool, float, bool] | None:
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


def _subset(a: tuple[float, bool, float, bool],
            b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    lower_ok = al > bl or (al == bl and (not alc or blc))
    upper_ok = au < bu or (au == bu and (not auc or buc))
    return lower_ok and upper_ok


def _disjoint(a: tuple[float, bool, float, bool],
              b: tuple[float, bool, float, bool]) -> bool:
    al, alc, au, auc = a
    bl, blc, bu, buc = b
    a_before_b = au < bl or (au == bl and not (auc and blc))
    b_before_a = bu < al or (bu == al and not (buc and alc))
    return a_before_b or b_before_a


class QAConsistencyModule:
    """Question-aware verifier with a conservative legacy-rule adapter.

    The first implementation only auto-decides explicit quotations and numeric
    constraints. Unsupported semantic shapes return NIE with a diagnostic; the
    old binary NLI verdict is deliberately not mapped into three-way gold.
    """

    _QUOTED = re.compile(r"[「\"]([^「」\"]{2,80})[」\"]")
    _NEGATIVE = re.compile(r"(?:不包括|不包含|不支持|没有|不存在|未定义|不允许)")
    _EXPLICIT_NEGATION = re.compile(
        r"(?:不包括|不包含|不支持|不存在|不允许|禁止|不得|不能|未定义|不具备|不含)"
    )

    def __init__(self, semantic_nli=None,
                 nli_contra_threshold: float = 0.6,
                 nli_entail_threshold: float = 0.6,
                 use_deq: bool = False,
                 use_experts: bool = True,
                 use_bge_experts: bool = False,
                 use_llm_residual: bool = False,
                 use_nli_residual: bool = False,
                 use_cascade: bool = False,
                 cascade_keep_confidence: float | None = None,
                 use_learned_router: str | None = None,
                 nli_model_path: str = "",
                 nli_gate: float = 0.6,
                 llm_refute_gate: float = REFUTE_CONFIDENCE_GATE,
                 expert_filter: tuple[str, ...] | None = None,
                 fuse_per_claim: bool = True,
                 aggregation: str = "strict") -> None:
        """semantic_nli: optional callable predict(pairs)->NLI labels for the
        residual semantic channel. Thresholds are calibrated on dev splits.
        use_deq: opt-in the detection-item-aware evidence quality pipeline
        (E0 scope gate + E1 item scoring) to filter evidence before L1/L2.
        use_experts: opt-in the L0/L1 expert channels (entity detection,
        E1 template, sequence alignment, trace join) whose ClaimResults are
        union-merged with per-claim results before aggregation.
        use_bge_experts: opt-in BGE-based sequence alignment (local model,
        lazy-loaded); off by default for deterministic cheap runs.
        use_llm_residual: opt-in the L3 LLM residual channel. Claims left
        unresolved by L0/L1/L2 (semantic_unresolved/conservative_unresolved)
        are batched into one cached llm_json call per instance (C1 residual
        principle: decided claims never enter the LLM); the returned
        support/refute ClaimResults fuse over the unresolved NIE.
        Default off for backward compatibility with unit-test fixtures.
        use_nli_residual: opt-in the L2 NLI residual channel (S4): the same
        residual claims are judged by the locally EGT-fine-tuned mDeBERTa
        (pure local inference, no LLM). Mutually exclusive with
        use_llm_residual, NLI takes precedence (cheap channel first).
        use_cascade: opt-in the S5 L2→L3 escalation routing (paper C4:
        the FrugalGPT/RouteLLM cost-quality pattern generalized to
        heterogeneous verifiers). Implies use_nli_residual +
        use_llm_residual, replacing the mutually-exclusive dispatch: the
        cheap local NLI (L2) judges every residual claim; only its refute
        candidates — the one silver-measured failure mode (refute
        P=0.368) — are re-checked by the L3 LLM channel (refute P=1.0)
        in one batched cached call, and the L3 verdict fully replaces the
        L2 one on that claim. NLI support/NIE verdicts pass through
        untouched, so the LLM only pays for the pseudo-refutes. An L3
        call failure keeps the L2 refute verdict — escalation never
        leaves a run less informed than L2-only.
        cascade_keep_confidence: conformal-style high-confidence tier —
        an NLI refute whose softmax probability reaches this threshold is
        trusted directly without an L3 re-check (saves calls); None
        (default) escalates every NLI refute.
        use_learned_router: path to a learned router artifact
        (algorithms/consistency/router.py, trained by
        tools/build_router_dataset.py). When the artifact loads, the fixed
        S5 cascade policy is replaced by a per-instance learned decision
        made after L1 and before L2: "accept_l1" skips the residual
        channels, "accept_l2" runs L2 and trusts it without escalation,
        "call_l2" runs L2 with the fixed refute escalation, "escalate_l3"
        skips L2 and judges the residual claims directly with the L3 LLM
        channel. The decision is recorded as a "router_decision:<route>"
        diagnostic. A load failure degrades to the fixed cascade it
        replaces (never less informed) and surfaces a
        "router_load_failed_fallback_cascade" diagnostic.
        nli_model_path: fine-tuned checkpoint (default: MODELS registry's
        egt_finetuned entry, the centralized path config).
        nli_gate: softmax max-probability gate for emitting a verdict
        (below it the claim stays NIE).
        llm_refute_gate: L3 LLM refute confidence gate — an LLM refute
        whose reported confidence is below this stays NIE (see
        llm_residual.REFUTE_CONFIDENCE_GATE; default 0.8, backward
        compatible). Exposed as a constructor parameter so held-out
        calibration can sweep it without touching the frozen prompt.
        expert_filter: ablation hook — when set, only the named expert
        sub-channel(s) of _expert_channels run (valid names: "entity",
        "e1", "sequence", "trace", "gjb", "id_join", "enum_join",
        "numeric_z3", "coverage"); None
        (default) keeps all experts (backward compatible).
        fuse_per_claim: ablation hook — False skips the per-claim channel
        fusion so aggregation runs directly over the raw multi-channel
        ClaimResults (True/default keeps the fused behavior).
        aggregation: cross-claim aggregation variant over the fused
        per-claim verdicts (P1 support-recall study, docs/srs_project/
        50_support_recall_analysis.md). "strict" (default, backward
        compatible) keeps the ∀ semantics: any not_in_evidence claim
        blocks support (refute > NIE > support). "dominant_70" lets
        verified support win when at least 70% of the decidable claims
        (claims carrying an explicit decision signal — a support/refute
        verdict, or a NIE whose rationale records an active negative
        observation from a structured channel, see
        _ACTIVE_NIE_RATIONALE_MARKERS) are supported; inability NIEs
        (semantic_unresolved, "时序不可核对") no longer veto alone.
        "no_minor_block" only lets substantive core claims block —
        效果性/总结性 fragments (see _MINOR_CLAIM_MARKERS) cannot veto;
        a claim set with no core claims falls back to the strict rule.
        Refute wins in every variant. Default "strict" keeps every
        existing configuration and paper number untouched."""
        if aggregation not in AGGREGATION_VARIANTS:
            raise ValueError(
                f"aggregation must be one of {AGGREGATION_VARIANTS}, "
                f"got {aggregation!r}")
        self.semantic_nli = semantic_nli
        self.nli_contra_threshold = nli_contra_threshold
        self.nli_entail_threshold = nli_entail_threshold
        self.use_deq = use_deq
        self.use_experts = use_experts
        self.use_bge_experts = use_bge_experts
        self.use_llm_residual = use_llm_residual
        self.use_nli_residual = use_nli_residual
        self.use_cascade = use_cascade
        self.cascade_keep_confidence = cascade_keep_confidence
        if use_cascade:
            # cascade = smart dispatch over both residual channels (S5):
            # L2 judges everything, L3 re-checks only L2 refute candidates.
            self.use_nli_residual = True
            self.use_llm_residual = True
        self.router = None
        self._router_load_error = ""
        if use_learned_router:
            # learned router subsumes both residual channels; the fixed
            # cascade stays as the degradation path on load failure.
            self.use_nli_residual = True
            self.use_llm_residual = True
            try:
                from algorithms.consistency.router import LearnedRouter
                self.router = LearnedRouter.load(use_learned_router)
            except (OSError, ValueError, KeyError, AttributeError,
                    ImportError, RuntimeError) as exc:
                self._router_load_error = f"{type(exc).__name__}: {exc}"
                self.use_cascade = True
        self.nli_model_path = nli_model_path
        self.nli_gate = nli_gate
        self.llm_refute_gate = llm_refute_gate
        self.expert_filter = expert_filter
        self.fuse_per_claim = fuse_per_claim
        self.aggregation = aggregation

    def verify(self, request: QAInput) -> VerificationResult:
        self._validate(request)

        verification_request = request
        deq_diagnostic: list[str] = []
        if self.use_deq and request.evidence:
            from dataclasses import replace

            from algorithms.consistency.deq_pipeline import deq_pipeline
            deq_result = deq_pipeline(
                question=request.question,
                answer=request.answer,
                evidence_blocks=request.evidence,
            )
            if deq_result.ranked_evidence != request.evidence:
                verification_request = replace(
                    request, evidence=deq_result.ranked_evidence)
            if deq_result.original_count > deq_result.gated_count:
                deq_diagnostic.append(
                    f"deq_filtered_{deq_result.original_count - deq_result.gated_count}"
                    f"_of_{deq_result.original_count}_blocks"
                )
            if deq_result.gated_count == 0 and deq_result.original_count > 0:
                deq_diagnostic.append("deq_all_evidence_rejected")

        check_items = route_question(request.question)
        claims = self._decompose(request.question, request.answer)
        statements = linearize_context(verification_request.evidence)
        claim_results = tuple(
            self._verify_claim(verification_request, claim, i, check_items,
                               statements)
            for i, claim in enumerate(claims, 1)
        )
        expert_diag: list[str] = []
        if self.use_experts and verification_request.evidence and statements:
            expert_results, expert_diag = self._expert_channels(
                verification_request, statements)
            if expert_results:
                claim_results = claim_results + tuple(expert_results)
        # Residual channels (C1 residual principle): only claims the
        # deterministic channels left unresolved enter a residual judge.
        # L2 NLI (local fine-tuned model) takes precedence over L3 LLM —
        # mutually exclusive, cheap channel first — unless use_cascade
        # routes the L2 refute candidates up to L3 for a re-check (S5
        # escalation: support/NIE pass through, refutes are re-judged by
        # the precise LLM), or a learned router (use_learned_router)
        # decides the route per instance: accept_l1 (skip residual
        # judges), accept_l2 (L2, no escalation), call_l2 (L2 + the fixed
        # escalation), escalate_l3 (L3 directly, L2 skipped). Instances
        # already carrying a refute are skipped — refute wins aggregation,
        # so a residual judge cannot change them.
        nli_diag: list[str] = []
        llm_diag: list[str] = []
        router_diag: list[str] = []
        if self._router_load_error:
            router_diag.append("router_load_failed_fallback_cascade")
        residual = ([r for r in claim_results
                     if r.method in ("semantic_unresolved",
                                     "conservative_unresolved")]
                    if statements
                    and not any(r.verdict == "refute" for r in claim_results)
                    else [])
        route: str | None = None
        if residual and self.router is not None:
            route = self._route_instance(verification_request, claim_results,
                                         claims, check_items)
            router_diag.append(f"router_decision:{route}")
        if residual and route == "escalate_l3":
            from algorithms.consistency.llm_residual import (
                verify_residual_claims)

            llm_results = verify_residual_claims(
                verification_request, residual, statements,
                refute_gate=self.llm_refute_gate)
            if llm_results:
                claim_results = claim_results + tuple(llm_results)
                if any(r.method == "llm_residual_failed" for r in llm_results):
                    llm_diag.append("llm_residual_call_failed")
        elif residual and route == "accept_l1":
            pass  # the learned router trusts the deterministic channels;
            # residual claims keep their conservative NIE verdicts.
        elif residual and self.use_nli_residual:
            from algorithms.consistency.nli_residual import (
                verify_residual_claims_nli)

            nli_results = verify_residual_claims_nli(
                verification_request, residual, statements,
                model_path=self.nli_model_path, gate=self.nli_gate)
            if nli_results:
                escalate = (route == "call_l2" if route is not None
                            else self.use_cascade)
                if escalate:
                    nli_results, cascade_diag = self._escalate_nli_refutes(
                        verification_request, nli_results, statements)
                    llm_diag.extend(cascade_diag)
                claim_results = claim_results + tuple(nli_results)
                if any(r.method == "nli_residual_unavailable"
                       for r in nli_results):
                    nli_diag.append("nli_residual_model_unavailable")
        elif residual and self.use_llm_residual:
            from algorithms.consistency.llm_residual import (
                verify_residual_claims)

            llm_results = verify_residual_claims(
                verification_request, residual, statements,
                refute_gate=self.llm_refute_gate)
            if llm_results:
                claim_results = claim_results + tuple(llm_results)
                if any(r.method == "llm_residual_failed" for r in llm_results):
                    llm_diag.append("llm_residual_call_failed")
        # per-claim channel fusion: when multiple channels judge the SAME
        # claim text, a structured expert's decisive verdict (support/refute)
        # outranks a generic channel's "unresolved" NIE — inability to verify
        # must not veto a verified verdict on the identical claim.
        # fuse_per_claim=False (ablation) aggregates the raw channels.
        fused_results = (self._fuse_per_claim(claim_results)
                         if self.fuse_per_claim else claim_results)
        verdict, aggregate_diagnostics = self._aggregate(fused_results)

        evidence_by_id = {ev.evidence_id: ev for ev in request.evidence}
        cited = sorted({ref for result in fused_results for ref in result.evidence_refs})
        diagnostics = (list(aggregate_diagnostics) + deq_diagnostic
                       + expert_diag + nli_diag + llm_diag + router_diag)
        if not check_items:
            diagnostics.append("no_check_item_candidate")
        if not request.evidence:
            diagnostics.append("empty_retrieved_context")
        if any(ev.completeness == "closed" and not ev.completeness_proof.strip()
                for ev in request.evidence):
            diagnostics.append("closed_scope_missing_proof_treated_as_open")
        if any(result.method == "semantic_unresolved" for result in claim_results):
            diagnostics.append("semantic_claim_requires_validated_three_way_method")
        if any(result.method == "legacy_binary_nli_unresolved"
               for result in claim_results):
            diagnostics.append("legacy_binary_nli_cannot_decide_three_way_verdict")
        if any(result.method == "conservative_unresolved" for result in claim_results):
            diagnostics.append("one_or_more_claims_unresolved")

        evidence_chain = tuple(evidence_by_id[eid] for eid in cited if eid in evidence_by_id)
        return VerificationResult(
            instance_id=request.instance_id,
            question=request.question,
            answer=request.answer,
            verdict=verdict,
            status="partial" if diagnostics else "ok",
            claim_results=fused_results,
            evidence_chain=evidence_chain,
            considered_evidence_ids=tuple(
                ev.evidence_id for ev in verification_request.evidence),
            context_freeze_id=request.context_freeze_id,
            context_hash=_context_hash(request),
            context_integrity=(
                "partial" if any(
                    ev.extraction_confidence is not None
                    and ev.extraction_confidence < 0.8 for ev in request.evidence
                ) else "unknown"
            ),
            applicability="applicable" if check_items else "uncertain",
            rationale="; ".join(r.rationale for r in fused_results),
            diagnostics=tuple(diagnostics),
        )

    def _route_instance(self, request: QAInput,
                        claim_results: tuple[ClaimResult, ...],
                        claims: list[_AnswerClaim],
                        check_items: tuple[str, ...]) -> str | None:
        """Query the learned router with phi(instance) at the decision point.

        The features see exactly the pre-fusion L0/L1 state (per-claim plus
        expert results) that the residual dispatch below acts on — the same
        distribution tools/build_router_dataset.py records.
        """
        if self.router is None:
            return None
        from algorithms.consistency.router import extract_route_features

        features = extract_route_features(
            question=request.question,
            answer=request.answer,
            evidence=request.evidence,
            claim_results=claim_results,
            claim_kinds=tuple(claim.kind for claim in claims),
            check_items=check_items,
        )
        return self.router.route(features)

    def _escalate_nli_refutes(
            self, request: QAInput, nli_results: list[ClaimResult],
            statements: list) -> tuple[list[ClaimResult], list[str]]:
        """S5 L2→L3 cascade escalation of the NLI refute candidates.

        FrugalGPT/RouteLLM-style routing over heterogeneous verifiers: the
        local NLI (cheap, refute precision 0.368 on silver) has already
        judged every residual claim; its refute candidates — the only
        silver-measured pain point — are re-checked by the L3 LLM channel
        (expensive, refute precision 1.0) in one batched cached call, and
        the L3 verdict fully replaces the L2 one on that claim (including
        a conservative NIE). NLI support/NIE verdicts pass through
        untouched. An L3 call failure keeps the L2 refute verdict, so
        escalation never leaves a run less informed than L2-only. A refute
        whose NLI probability reaches cascade_keep_confidence is trusted
        directly without an L3 call (conformal-style high-confidence tier).
        """
        refutes = [r for r in nli_results if r.verdict == "refute"]
        kept = ([r for r in refutes
                 if r.confidence >= self.cascade_keep_confidence]
                if self.cascade_keep_confidence is not None else [])
        keep_ids = {r.claim_id for r in kept}
        diagnostics = [f"cascade_nli_claims_{len(nli_results)}"]
        if kept:
            diagnostics.append(f"cascade_high_confidence_kept_{len(kept)}")
        if not refutes:
            diagnostics.append("cascade_llm_calls_0")
            return nli_results, diagnostics
        # instance-level escalation: a refute signal escalates the
        # instance's full residual claim set, not only the flagged claim —
        # NLI's claim-level refute flag can sit on the wrong claim while
        # the true contradiction was judged NIE (S1QA-068/074 pattern).
        escalate = [r for r in nli_results if r.claim_id not in keep_ids]
        diagnostics.append(f"cascade_llm_calls_{len(escalate)}")
        from algorithms.consistency.llm_residual import verify_residual_claims

        llm_results = verify_residual_claims(request, escalate, statements,
                                             refute_gate=self.llm_refute_gate)
        if any(r.method == "llm_residual_failed" for r in llm_results):
            diagnostics.append("llm_residual_call_failed")
        replaced = {r.claim_id: r for r in llm_results
                    if r.method != "llm_residual_failed"}
        final = [replaced.get(r.claim_id, r) for r in nli_results]
        return final, diagnostics

    @staticmethod
    def _validate(request: QAInput) -> None:
        if not request.instance_id.strip():
            raise ValueError("instance_id must not be empty")
        if not request.question.strip():
            raise ValueError("question must not be empty")
        if not request.answer.strip():
            raise ValueError("answer must not be empty")
        if not request.context_freeze_id.strip():
            raise ValueError("context_freeze_id must not be empty")
        ids = [ev.evidence_id for ev in request.evidence]
        if any(not eid.strip() for eid in ids) or len(set(ids)) != len(ids):
            raise ValueError("evidence_id values must be non-empty and unique")
        if any(not ev.source_ref.doc_id.strip() for ev in request.evidence):
            raise ValueError("every evidence item must carry a document source_ref")

    def _decompose(self, question: str, answer: str) -> list[_AnswerClaim]:
        claims: list[_AnswerClaim] = []
        numeric_claims = _extract_numeric_claims(answer)
        numeric_question = any(item.startswith("PARAM-") for item in route_question(question))
        if numeric_question:
            values = list(_ANSWER_NUMBER.finditer(answer))
            subject = self._question_numeric_subject(question)
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
                attr = self._question_numeric_subject(question)
            claims.append(_AnswerClaim("numeric", f"{attr} {operator}{value}{unit}",
                                       attr, operator, value, unit))
        for match in self._QUOTED.finditer(answer):
            prefix = answer[max(0, match.start() - 12):match.start()]
            claims.append(_AnswerClaim("quoted", match.group(1),
                                       negative=bool(self._NEGATIVE.search(prefix))))
        for items in _extract_enum_claims(answer):
            cleaned = [re.split(r"[，,]", item)[0].strip() for item in items]
            cleaned = [item for item in cleaned if len(item) >= 2]
            if len(cleaned) >= 2:
                claims.append(_AnswerClaim("enum", "、".join(cleaned)))
        for identifier in _IDENTIFIER.findall(answer):
            position = answer.find(identifier)
            prefix = answer[max(0, position - 24):position]
            cleaned_prefix = re.sub(
                r"[（(「\",，。：:为是*`_~]+", " ", prefix).rstrip()
            subject_match = re.search(
                r"([\u4e00-\u9fffA-Za-z]{2,16})\s*$", cleaned_prefix)
            subject = subject_match.group(1) if subject_match else ""
            claims.append(_AnswerClaim("identifier", identifier, attr=subject))
        if not claims:
            structured = decompose_answer(answer, question)
            for structural in structured:
                claims.append(_AnswerClaim(
                    "semantic", structural.text, attr=structural.scope_hint))
        if not claims:
            claims.append(_AnswerClaim("semantic", answer.strip()))
        return claims

    @staticmethod
    def _question_numeric_subject(question: str) -> str:
        """Resolve a short numeric answer's omitted subject from the question."""
        q = re.sub(r"\s+", "", question)
        match = re.search(
            r"([\u4e00-\u9fffA-Za-z]{2,12}?)(?:要求是多少|是多少|为多少|的上限|的下限|阈值)",
            q,
        )
        subject = match.group(1).removesuffix("的") if match else ""
        return subject.removeprefix("系统")

    def _verify_claim(self, request: QAInput, claim: _AnswerClaim,
                      index: int, check_items: tuple[str, ...],
                      statements: tuple = ()) -> ClaimResult:
        if not request.evidence:
            return self._unresolved(request, claim, index, check_items,
                                    "上游冻结context为空；无法支持或反驳answer")
        if claim.kind == "numeric":
            return self._verify_numeric(request, claim, index, check_items)
        if claim.kind == "quoted":
            return self._verify_quoted(request, claim, index, check_items)
        if claim.kind == "enum":
            return self._verify_enum(request, claim, index, check_items)
        if claim.kind == "identifier":
            return self._verify_identifier(request, claim, index, check_items)
        return self._verify_semantic(request, claim, index, check_items,
                                     tuple(statements))

    def _verify_semantic(self, request: QAInput, claim: _AnswerClaim,
                         index: int, check_items: tuple[str, ...],
                         statements: tuple) -> ClaimResult:
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
        nli_result = self._verify_semantic_nli(request, claim, index,
                                               check_items, statements)
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

    _SLOT_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
        ("前置条件", ("前置条件",)),
        ("后置条件", ("后置条件",)),
        ("异常流", ("异常流",)),
        ("参与者", ("Actors", "参与者")),
        ("Actor", ("Actors", "参与者")),
    )

    def _verify_semantic_nli(self, request: QAInput, claim: _AnswerClaim,
                             index: int, check_items: tuple[str, ...],
                             statements: tuple) -> ClaimResult | None:
        """Residual NLI channel on scope- and slot-matched statement pairs."""
        if self.semantic_nli is None or not statements:
            return None
        structured = decompose_answer(claim.text, request.question)
        if not structured:
            return None
        pairs = pair_statements(structured, list(statements))
        if not pairs:
            return None
        claim_slots = tuple(
            field for keyword, fields in self._SLOT_FIELDS
            if keyword in claim.text for field in fields)
        if claim_slots:
            pairs = [(structural, statement) for structural, statement in pairs
                     if statement.field_name in claim_slots]
        if not pairs:
            return None
        hypotheses = [(statement.text, structural.text)
                      for structural, statement in pairs]
        labels = self.semantic_nli(hypotheses)
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
                    and contra_prob >= self.nli_contra_threshold
                    and scope_matched):
                contradiction_refs.append(statement.evidence_id)
            elif verdict == "entailment" and entail_prob >= self.nli_entail_threshold:
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

    def _verify_numeric(self, request: QAInput, claim: _AnswerClaim,
                        index: int, check_items: tuple[str, ...]) -> ClaimResult:
        answer_unit = normalize_unit(claim.value, claim.unit)
        if answer_unit is None:
            return self._unresolved(request, claim, index, check_items,
                                    "answer数值单位无法归一化")
        answer_interval = _interval(claim.operator, answer_unit[0])
        if answer_interval is None:
            return self._unresolved(request, claim, index, check_items,
                                    "answer操作符不在已验证范围")

        matches: list[tuple[RetrievedEvidence, Verdict, str]] = []
        for evidence in request.evidence:
            for attr, operator, value, unit in _extract_numeric_claims(evidence.text):
                if not self._same_subject(claim.attr, attr, request.question):
                    continue
                ev_unit = normalize_unit(value, unit)
                if ev_unit is None or ev_unit[1] != answer_unit[1]:
                    continue
                ev_interval = _interval(operator, ev_unit[0])
                if ev_interval is None:
                    continue
                if (_subset(ev_interval, answer_interval)
                        or _subset(answer_interval, ev_interval)):
                    matches.append((evidence, "support", "context约束蕴含answer约束"))
                elif _disjoint(ev_interval, answer_interval):
                    matches.append((evidence, "refute", "context与answer数值区间互斥"))
                else:
                    matches.append((evidence, "not_in_evidence",
                                    "数值区间重叠但不互相蕴含，无法证明一致或矛盾"))
        decisive = [x for x in matches if x[1] in ("support", "refute")]
        decisive_labels = {x[1] for x in decisive}
        if len(decisive_labels) > 1:
            return self._unresolved(request, claim, index, check_items,
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
        return self._unresolved(request, claim, index, check_items,
                                matches[0][2] if matches else "context无同subject/单位数值证据",
                                refs)

    def _verify_quoted(self, request: QAInput, claim: _AnswerClaim,
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
                if self._EXPLICIT_NEGATION.search(prefix):
                    negative_refs.append(ev.evidence_id)
                else:
                    positive_refs.append(ev.evidence_id)
                start = pos + len(target)

        supporting_refs = negative_refs if claim.negative else positive_refs
        refuting_refs = positive_refs if claim.negative else negative_refs
        if supporting_refs:
            if refuting_refs:
                return self._unresolved(
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
        return self._unresolved(request, claim, index, check_items,
                                "引用项未命中冻结context，scope不完整或未证明穷举")

    def _verify_identifier(self, request: QAInput, claim: _AnswerClaim,
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
        return self._unresolved(request, claim, index, check_items,
                                "标识符未在冻结context命中，且无同subject的显式不同值")

    def _verify_enum(self, request: QAInput, claim: _AnswerClaim,
                     index: int, check_items: tuple[str, ...]) -> ClaimResult:
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
                    target = excluded if self._EXPLICIT_NEGATION.search(prefix) else found
                    target[item].append(ev.evidence_id)
                    start = pos + len(needle)
        explicit_exclusions = tuple(sorted({
            ref for refs in excluded.values() for ref in refs
        }))
        positive_refs = tuple(sorted({ref for refs in found.values() for ref in refs}))
        if explicit_exclusions and positive_refs:
            return self._unresolved(
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
            return ClaimResult(
                f"{request.instance_id}-c{index:02d}", claim.text, "support",
                check_items, refs, "answer枚举的每个成员均在冻结context精确出现",
                "enum_member_exact", 1.0)
        return self._unresolved(request, claim, index, check_items,
                                f"枚举成员未全部命中({len(missing)}项)；未证明context穷举", refs)

    @staticmethod
    def _same_subject(answer_subject: str, evidence_subject: str,
                      question: str) -> bool:
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

    @staticmethod
    def _unresolved(request: QAInput, claim: _AnswerClaim, index: int,
                    check_items: tuple[str, ...], rationale: str,
                    refs: tuple[str, ...] = ()) -> ClaimResult:
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

    def _expert_channels(self, request: QAInput,
                         statements: list) -> tuple[list[ClaimResult], list[str]]:
        """Run the L0/L1 expert channels on the frozen input.

        Each expert is deterministic and independently tested; a failing
        expert is surfaced as a diagnostic (never silently swallowed) while
        the remaining experts still contribute their ClaimResults.
        """
        from algorithms.consistency.answer_structure import decompose_answer
        from algorithms.consistency.coverage_expert import verify_coverage
        from algorithms.consistency.e1_expert import verify_e1_consistency
        from algorithms.consistency.entity_detector import detect_term_conflicts
        from algorithms.consistency.enum_join_expert import verify_enum_joins
        from algorithms.consistency.gjb_presence_expert import (
            verify_gjb_presence)
        from algorithms.consistency.id_join_expert import verify_id_joins
        from algorithms.consistency.numeric_z3_expert import (
            verify_numeric_constraints)
        from algorithms.consistency.sequence_expert import verify_sequence
        from algorithms.consistency.trace_expert import verify_trace

        structured = decompose_answer(request.answer, request.question)
        collected: list[ClaimResult] = []
        failures: list[str] = []
        experts: tuple[tuple[str, object], ...] = (
            ("entity", lambda: detect_term_conflicts(
                request, statements, structured)),
            ("e1", lambda: verify_e1_consistency(
                request, statements, structured)),
            ("sequence", lambda: verify_sequence(
                request, statements, structured,
                use_bge=self.use_bge_experts)),
            ("trace", lambda: verify_trace(request)),
            ("gjb", lambda: verify_gjb_presence(request, statements)),
            ("id_join", lambda: verify_id_joins(request, statements)),
            ("enum_join", lambda: verify_enum_joins(request, statements)),
            ("numeric_z3", lambda: verify_numeric_constraints(
                request, statements)),
            ("coverage", lambda: verify_coverage(request, statements)),
        )
        for name, run in experts:
            if self.expert_filter is not None and name not in self.expert_filter:
                continue
            try:
                collected.extend(run())
            except Exception as exc:  # reported in diagnostics, not silent
                failures.append(
                    f"expert_{name}_failed:{type(exc).__name__}")
        return collected, failures

    @staticmethod
    def _fuse_per_claim(
            results: tuple[ClaimResult, ...]) -> tuple[ClaimResult, ...]:
        """Fuse multi-channel verdicts on the same claim text.

        Channels (per-claim + L0/L1 experts) can judge the identical claim;
        the most decisive verdict wins per claim: refute (safety) >
        support (a structured expert verified it) > not_in_evidence (an
        unresolved channel's inability must not veto a verified verdict).
        Cross-claim aggregation stays refute > NIE > support.

        The fusion key strips a leading enumeration prefix (``_FUSION_PREFIX_RE``)
        before whitespace compaction: a sequence-decomposed "1．X" claim and the
        per-claim "X" claim are the same assertion and must fuse (the
        claim_text of the surviving result is unchanged).
        """
        groups: dict[str, list[ClaimResult]] = {}
        for result in results:
            key = re.sub(r"\s+", "", _FUSION_PREFIX_RE.sub("", result.claim_text))
            groups.setdefault(key, []).append(result)
        fused: list[ClaimResult] = []
        for group in groups.values():
            labels = {r.verdict for r in group}
            if "refute" in labels:
                pick = next(r for r in group if r.verdict == "refute")
            elif "support" in labels:
                pick = next(r for r in group if r.verdict == "support")
            else:
                pick = group[0]
            fused.append(pick)
        return tuple(fused)

    def _aggregate(self, results: tuple[ClaimResult, ...]
                   ) -> tuple[Verdict, list[str]]:
        """Cross-claim aggregation over the fused per-claim verdicts.

        strict (default): refute > not_in_evidence > support — any NIE
        claim blocks instance-level support (strict ∀ semantics).
        dominant_70: without a refute, support wins when the decidable
        claims (explicit decision signal: support/refute verdict or an
        active-observation NIE) reach the 0.70 support ratio; inability
        NIEs do not vote.
        no_minor_block: without a refute, support wins when every core
        (non effect/summary) claim is support; minor fragments cannot
        veto. A claim set with no core claims falls back to strict.
        Refute wins in every variant.
        """
        labels = {r.verdict for r in results}
        if "refute" in labels:
            return "refute", []
        if self.aggregation == "dominant_70":
            decidable = [r for r in results
                         if r.verdict != "not_in_evidence" or _is_active_nie(r)]
            if not decidable:
                return "not_in_evidence", ["agg_dominant_70_no_decidable_claim"]
            support_count = sum(1 for r in decidable
                                if r.verdict == "support")
            ratio = support_count / len(decidable)
            diagnostic = f"agg_dominant_70_ratio_{ratio:.2f}"
            if ratio >= _DOMINANT_SUPPORT_RATIO:
                return "support", [diagnostic]
            return "not_in_evidence", [diagnostic]
        if self.aggregation == "no_minor_block":
            core = [r for r in results if not _is_minor_claim(r)]
            if not core:
                core = list(results)  # minor-only claim set: strict fallback
            if all(r.verdict == "support" for r in core):
                return "support", ["agg_no_minor_block_core_all_support"]
            return "not_in_evidence", ["agg_no_minor_block_core_blocked"]
        if "not_in_evidence" in labels:
            return "not_in_evidence", []
        return "support", []
