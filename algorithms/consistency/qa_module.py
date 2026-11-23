"""Unified post-retrieval QA consistency module.

Input is ``question + answer + upstream-frozen retrieved context``. This module
does not retrieve context or compare evidence sources with each other.

Architecture (Wave 8-H2 split): this file keeps only the
``QAConsistencyModule`` orchestration (verify / decomposition dispatch /
expert channel registry / residual dispatch / cascade escalation /
per-claim fusion / cross-claim aggregation). Deterministic answer claim
extraction lives in ``algorithms.consistency.answer_claims`` and the
per-claim verification channels in
``algorithms.consistency.claim_channels``; the historical module-level
names (``_AnswerClaim``, ``_extract_numeric_claims``) are re-exported
below for backward compatibility.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from algorithms.consistency.answer_claims import AnswerClaim as _AnswerClaim
from algorithms.consistency.answer_claims import (
    decompose_claims,
    decompose_claims_sentences,
)
from algorithms.consistency.answer_claims import (
    extract_numeric_claims as _extract_numeric_claims,
)
from algorithms.consistency.assertion import is_assertive_claim as _is_assertive_claim
from algorithms.consistency.answer_structure import StructuredClaim
from algorithms.consistency.answer_structure import decompose_answer
from algorithms.consistency.claim_channels import (
    SemanticNliJudge,
    unresolved,
    verify_enum,
    verify_identifier,
    verify_numeric,
    verify_quoted,
    verify_semantic,
)
from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.evidence_statements import linearize_context
from algorithms.consistency.qa_models import (
    ClaimResult,
    EvidenceLocalization,
    InconsistencyLocalization,
    QAInput,
    VerificationResult,
    Verdict,
)
from algorithms.consistency.qa_router import route_question

#: backward-compatible re-exports of the pre-split module surface
__all__ = [
    "AGGREGATION_VARIANTS",
    "ExpertSpec",
    "QAConsistencyModule",
    "_AnswerClaim",
    "_ASSERTIVE_SUPPORT_RATIO",
    "_extract_numeric_claims",
    "_is_active_nie",
    "_is_assertive_claim",
    "_is_minor_claim",
]

#: cross-claim aggregation variants (P1 support-recall study,
#: docs/srs_project/50_support_recall_analysis.md; M88 assertion-aware
#: variants for the distilled segmenter's bare-noun NIE collapse)
AGGREGATION_VARIANTS: tuple[str, ...] = (
    "strict",            # current ∀ semantics: any NIE blocks support
    "dominant_70",       # decidable-claim support ratio >= 0.70 -> support
    "no_minor_block",    # core (non effect/summary) claims all support
    "assertive_strict",  # assertive-claim set ∀: bare fragments cannot veto
    "assertive_ratio",   # assertive+decidable support ratio >= τ -> support
)

#: support ratio gate for the dominant_70 aggregation variant
_DOMINANT_SUPPORT_RATIO = 0.70

#: support ratio gate τ for the assertive_ratio aggregation variant
#: (M88; swept on dev-45 in tools/eval_agg_codesign.py, default 0.8)
_ASSERTIVE_SUPPORT_RATIO = 0.80

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


@dataclass(frozen=True)
class ExpertSpec:
    """One declaratively registered expert channel (uniform adapter).

    ``runner`` wraps the expert's original entry function (whose signature
    is NOT changed) into the uniform three-argument callable
    ``(request, statements, structured) -> list[ClaimResult]``.
    ``takes_claims`` records whether the underlying entry consumes the
    decomposed answer claims; ``takes_bge`` records whether it exposes a
    ``use_bge`` switch. Both are declarative metadata used when building
    the adapter in :func:`_expert_registry`.
    """

    name: str
    runner: Callable[
        [QAInput, list[EvidenceStatement], list[StructuredClaim]],
        list[ClaimResult],
    ]
    takes_claims: bool = True
    takes_bge: bool = False


def _expert_registry(use_bge: bool) -> tuple[ExpertSpec, ...]:
    """Build the declarative L0/L1 expert registry for one verification.

    Expert entry functions keep their heterogeneous original signatures;
    the adapters below wrap them into the uniform ``ExpertSpec.runner``
    callable. Imports stay lazy (inside this builder, outside the per-expert
    try blocks) exactly as in the pre-refactor ``_expert_channels``.
    """

    def three_arg(expert: Callable[..., list[ClaimResult]]) -> Callable[
            [QAInput, list, list], list[ClaimResult]]:
        def runner(request: QAInput, statements: list,
                   structured: list) -> list[ClaimResult]:
            return expert(request, statements, structured)

        return runner

    def bge_switch(expert: Callable[..., list[ClaimResult]]) -> Callable[
            [QAInput, list, list], list[ClaimResult]]:
        def runner(request: QAInput, statements: list,
                   structured: list) -> list[ClaimResult]:
            return expert(request, statements, structured, use_bge=use_bge)

        return runner

    def statements_only(expert: Callable[..., list[ClaimResult]]) -> Callable[
            [QAInput, list, list], list[ClaimResult]]:
        def runner(request: QAInput, statements: list,
                   structured: list) -> list[ClaimResult]:
            return expert(request, statements)

        return runner

    def request_only(expert: Callable[..., list[ClaimResult]]) -> Callable[
            [QAInput, list, list], list[ClaimResult]]:
        def runner(request: QAInput, statements: list,
                   structured: list) -> list[ClaimResult]:
            return expert(request)

        return runner

    from algorithms.consistency.coverage_expert import verify_coverage
    from algorithms.consistency.e1_expert import verify_e1_consistency
    from algorithms.consistency.entity_detector import detect_term_conflicts
    from algorithms.consistency.enum_join_expert import verify_enum_joins
    from algorithms.consistency.gjb_rule_engine import (
        verify_gjb_rules)
    from algorithms.consistency.id_join_expert import verify_id_joins
    from algorithms.consistency.numeric_z3_expert import (
        verify_numeric_constraints)
    from algorithms.consistency.sequence_expert import verify_sequence
    from algorithms.consistency.trace_expert import verify_trace

    return (
        ExpertSpec("entity", three_arg(detect_term_conflicts)),
        ExpertSpec("e1", three_arg(verify_e1_consistency)),
        ExpertSpec("sequence", bge_switch(verify_sequence), takes_bge=True),
        ExpertSpec("trace", request_only(verify_trace), takes_claims=False),
        ExpertSpec("gjb", statements_only(verify_gjb_rules),
                   takes_claims=False),
        ExpertSpec("id_join", statements_only(verify_id_joins),
                   takes_claims=False),
        ExpertSpec("enum_join", statements_only(verify_enum_joins),
                   takes_claims=False),
        ExpertSpec("numeric_z3", statements_only(verify_numeric_constraints),
                   takes_claims=False),
        ExpertSpec("coverage", statements_only(verify_coverage),
                   takes_claims=False),
    )


class QAConsistencyModule:
    """Question-aware verifier with a conservative legacy-rule adapter.

    The first implementation only auto-decides explicit quotations and numeric
    constraints. Unsupported semantic shapes return NIE with a diagnostic; the
    old binary NLI verdict is deliberately not mapped into three-way gold.
    """

    def __init__(self, semantic_nli=None,
                 nli_contra_threshold: float = 0.6,
                 nli_entail_threshold: float = 0.6,
                 use_deq: bool = False,
                 use_subtractor: bool = False,
                 use_experts: bool = True,
                 use_bge_experts: bool = False,
                 use_nli_residual: bool = False,
                 nli_model_path: str = "",
                 nli_gate: float = 0.7,
                 expert_filter: tuple[str, ...] | None = None,
                 fuse_per_claim: bool = True,
                 decomposer: str = "typed",
                 aggregation: str = "strict") -> None:
        """semantic_nli: optional callable predict(pairs)->NLI labels for the
        residual semantic channel. Thresholds are calibrated on dev splits.
        use_deq: opt-in the detection-item-aware evidence quality pipeline
        (E0 scope gate + E1 item scoring) to filter evidence before L1/L2.
        use_subtractor: opt-in the hard-veto evidence subtractor (F1 scope
        filter + F2 granularity normalization + F3 pointer removal, 70-72号)
        — deletes out-of-scope blocks and rewrites each kept block's text
        as row/sentence-level statements so NLI consumes sentence-grade
        premises (SummaC principle); every removal is auditable.
        use_experts: opt-in the L0/L1 expert channels (entity detection,
        E1 template, sequence alignment, trace join) whose ClaimResults are
        union-merged with per-claim results before aggregation.
        use_bge_experts: opt-in BGE-based sequence alignment (local model,
        lazy-loaded); off by default for deterministic cheap runs.
        channels, "accept_l2" runs L2 and trusts it without escalation,
        skips L2 and judges the residual claims directly with the L3 LLM
        nli_model_path: fine-tuned checkpoint (default: MODELS registry's
        egt_finetuned entry, the centralized path config).
        nli_gate: softmax max-probability gate for emitting a verdict
        (below it the claim stays NIE).
        whose reported confidence is below this stays NIE (see
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
        "assertive_strict" (M88) restricts the ∀ semantics to the
        assertive-claim subset (see algorithms.consistency.assertion):
        bare noun/verb fragments the distilled segmenter emits ("添加"
        style non-propositions that NLI can only judge NIE) cannot veto;
        a claim set with no assertive claim falls back to the strict
        rule. "assertive_ratio" (M88) computes the support ratio over
        the assertive AND decidable claims (support/refute verdict or
        an active-observation NIE, as in dominant_70) and emits support
        when it reaches _ASSERTIVE_SUPPORT_RATIO (τ, default 0.80).
        Refute wins in every variant. Default "strict" keeps every
        existing configuration and paper number untouched.
        decomposer: answer分解器选择 (v3域自适应配置面). "typed"
        (default, 向后兼容) = answer_claims.decompose_claims的正则
        typed提取(numeric/enum/identifier/quoted+回退链, GJB域文法
        前端, 域内有真实增益但typed通道跨域为负资产);
        "sentence" = decompose_claims_sentences纯句子/列表项切分
        (SummaC式域中立分解, refactor_matrix_v1.json实测跨文档档
        配dominant_70聚合最优)."""
        if aggregation not in AGGREGATION_VARIANTS:
            raise ValueError(
                f"aggregation must be one of {AGGREGATION_VARIANTS}, "
                f"got {aggregation!r}")
        if decomposer not in ("typed", "sentence"):
            raise ValueError(
                f"decomposer must be 'typed' or 'sentence', "
                f"got {decomposer!r}")
        self._decomposer = (decompose_claims if decomposer == "typed"
                            else decompose_claims_sentences)
        self.semantic_nli = semantic_nli
        self.nli_contra_threshold = nli_contra_threshold
        self.nli_entail_threshold = nli_entail_threshold
        self.use_deq = use_deq
        self.use_subtractor = use_subtractor
        self.use_experts = use_experts
        self.use_bge_experts = use_bge_experts
        self.use_nli_residual = use_nli_residual
        self.nli_model_path = nli_model_path
        self.nli_gate = nli_gate
        self.expert_filter = expert_filter
        self.fuse_per_claim = fuse_per_claim
        self.expert_filter = expert_filter
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
        if self.use_subtractor and verification_request.evidence:
            from dataclasses import asdict, replace

            from algorithms.consistency.evidence_purifier import (
                PurificationConfig,
                purify,
            )
            # evidence模式(只删块不改写): 粒度归一由本模块
            # linearize_evidence的表格类型感知行级化负责(能力表/
            # 数据表/接口表/用例表), 证据级重写会破坏其类型检测
            # (73号实验教训); 故语句预算关闭.
            pack = purify(
                question=verification_request.question,
                answer=verification_request.answer,
                evidence=[asdict(ev)
                          for ev in verification_request.evidence],
                config=PurificationConfig(mode="evidence"),
            )
            kept_ids = {str(k.get("evidence_id", "")) for k in pack["kept"]}
            new_blocks = [ev for ev in verification_request.evidence
                          if ev.evidence_id in kept_ids]
            verification_request = replace(
                verification_request, evidence=tuple(new_blocks))
            stats = pack["stats"]
            deq_diagnostic.append(
                f"subtractor_removed_{stats['n_removed']}"
                f"_of_{stats['n_in']}_blocks")
            if stats["n_removed"]:
                deq_diagnostic.append(
                    "subtractor_reasons:"
                    + ",".join(f"{k}x{v}"
                               for k, v in stats["by_reason"].items()))
            if stats["n_kept"] == 0 and stats["n_in"] > 0:
                deq_diagnostic.append("subtractor_all_evidence_rejected")

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
        # routes the L2 refute candidates up to L3 for a re-check (S5
        # escalation: support/NIE pass through, refutes are re-judged by
        # judges), accept_l2 (L2, no escalation), call_l2 (L2 + the fixed
        # already carrying a refute are skipped — refute wins aggregation,
        # so a residual judge cannot change them.
        nli_diag: list[str] = []
        residual = ([r for r in claim_results
                     if r.method in ("semantic_unresolved",
                                     "conservative_unresolved")]
                    if statements
                    and not any(r.verdict == "refute" for r in claim_results)
                    else [])
        if residual and self.use_nli_residual:
            from algorithms.consistency.nli_residual import (
                verify_residual_claims_nli)

            nli_results = verify_residual_claims_nli(
                verification_request, residual, statements,
                model_path=self.nli_model_path, gate=self.nli_gate)
            if nli_results:
                claim_results = claim_results + tuple(nli_results)
                if any(r.method == "nli_residual_unavailable"
                       for r in nli_results):
                    nli_diag.append("nli_residual_model_unavailable")
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
                       + expert_diag + nli_diag)
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
        localizations = self._build_localizations(
            fused_results, statements, evidence_by_id, request.answer)
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
            localizations=localizations,
        )

    @staticmethod
    def _build_localizations(
            results: tuple[ClaimResult, ...],
            statements: list[EvidenceStatement],
            evidence_by_id: dict,
            answer: str) -> tuple[InconsistencyLocalization, ...]:
        """把refute claim的引用升级为结构化定位报告(语句/块/行/字段).

        answer侧: claim_text在answer中的字符区间(best-effort文本搜索,
        清洗过的claim可能无逐字命中→None); 证据侧: statement_id
        ({evidence_id}#s{N}) join语句元数据. 非refute不产出定位.
        根因(M92): 每条定位附带root_cause两层分类(根因源×根因操作),
        由classify_root_cause(method, rationale)表驱动填充.
        """
        from algorithms.consistency.root_cause import classify_root_cause

        if not any(result.verdict == "refute" for result in results):
            return ()
        statements_by_id = {s.statement_id: s for s in statements}
        out: list[InconsistencyLocalization] = []
        for result in results:
            if result.verdict != "refute":
                continue
            if result.span is not None:
                span: tuple[int, int] | None = result.span
            else:
                position = answer.find(result.claim_text)
                span = ((position, position + len(result.claim_text))
                        if position >= 0 else None)
            evidence_locs: list[EvidenceLocalization] = []
            for ref in result.evidence_refs:
                statement = statements_by_id.get(ref)
                base_id = str(ref).split("#", 1)[0]
                ev = evidence_by_id.get(base_id)
                if statement is not None:
                    block = (ev.source_ref.block_id if ev is not None
                             else "")
                    section = (ev.source_ref.section if ev is not None
                               else "")
                    evidence_locs.append(EvidenceLocalization(
                        evidence_id=base_id,
                        statement_id=ref,
                        statement_text=statement.text,
                        field_name=statement.field_name,
                        row_index=statement.row_index,
                        block_id=str(block),
                        section=str(section)))
                elif ev is not None:
                    evidence_locs.append(EvidenceLocalization(
                        evidence_id=base_id,
                        statement_id=str(ref),
                        statement_text=str(ev.text)[:200],
                        field_name="",
                        row_index=-1,
                        block_id=str(ev.source_ref.block_id),
                        section=str(ev.source_ref.section)))
            out.append(InconsistencyLocalization(
                claim_id=result.claim_id,
                claim_text=result.claim_text,
                answer_span=span,
                check_item_candidates=result.check_item_candidates,
                method=result.method,
                confidence=result.confidence,
                rationale=result.rationale,
                evidence=tuple(evidence_locs),
                root_cause=classify_root_cause(
                    result.method, result.rationale)))
        return tuple(out)

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
        """Answer decomposition (typed or sentence decomposer)."""
        return self._decomposer(question, answer)

    def _verify_claim(self, request: QAInput, claim: _AnswerClaim,
                      index: int, check_items: tuple[str, ...],
                      statements: tuple = ()) -> ClaimResult:
        if not request.evidence:
            return unresolved(request, claim, index, check_items,
                              "上游冻结context为空；无法支持或反驳answer")
        if claim.kind == "numeric":
            return verify_numeric(request, claim, index, check_items)
        if claim.kind == "quoted":
            return verify_quoted(request, claim, index, check_items)
        if claim.kind == "enum":
            return verify_enum(request, claim, index, check_items)
        if claim.kind == "identifier":
            return verify_identifier(request, claim, index, check_items)
        judge = (SemanticNliJudge(self.semantic_nli,
                                  self.nli_contra_threshold,
                                  self.nli_entail_threshold)
                 if self.semantic_nli is not None else None)
        return verify_semantic(request, claim, index, check_items,
                               tuple(statements), judge)

    def _expert_channels(self, request: QAInput,
                         statements: list) -> tuple[list[ClaimResult], list[str]]:
        """Run the L0/L1 expert channels on the frozen input.

        Each expert is deterministic and independently tested; a failing
        expert is surfaced as a diagnostic (never silently swallowed) while
        the remaining experts still contribute their ClaimResults.
        """
        structured = decompose_answer(request.answer, request.question)
        collected: list[ClaimResult] = []
        failures: list[str] = []
        for spec in _expert_registry(self.use_bge_experts):
            if self.expert_filter is not None and spec.name not in self.expert_filter:
                continue
            try:
                collected.extend(spec.runner(request, statements, structured))
            except Exception as exc:  # reported in diagnostics, not silent
                failures.append(
                    f"expert_{spec.name}_failed:{type(exc).__name__}")
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
        assertive_strict (M88): the ∀ semantics restricted to the
        assertive-claim subset (_is_assertive_claim) — non-propositional
        bare fragments cannot veto support; without an assertive claim
        the rule falls back to strict.
        assertive_ratio (M88): support ratio over the assertive and
        decidable claims (non-NIE or active-observation NIE) must reach
        _ASSERTIVE_SUPPORT_RATIO (τ) for support; a non-assertive or
        inability-NIE claim neither votes nor vetoes.
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
        if self.aggregation == "assertive_strict":
            assertive = [r for r in results if _is_assertive_claim(r)]
            if not assertive:
                assertive = list(results)  # no assertive claim: strict fallback
            if all(r.verdict == "support" for r in assertive):
                return "support", ["agg_assertive_strict_all_support"]
            return "not_in_evidence", ["agg_assertive_strict_blocked"]
        if self.aggregation == "assertive_ratio":
            decidable = [r for r in results
                         if _is_assertive_claim(r)
                         and (r.verdict != "not_in_evidence"
                              or _is_active_nie(r))]
            if not decidable:
                return "not_in_evidence", [
                    "agg_assertive_ratio_no_decidable_claim"]
            support_count = sum(1 for r in decidable
                                if r.verdict == "support")
            ratio = support_count / len(decidable)
            diagnostic = f"agg_assertive_ratio_{ratio:.2f}"
            if ratio >= _ASSERTIVE_SUPPORT_RATIO:
                return "support", [diagnostic]
            return "not_in_evidence", [diagnostic]
        if "not_in_evidence" in labels:
            return "not_in_evidence", []
        return "support", []