"""Stable contracts for the post-retrieval QA consistency module."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SourceType = Literal["text", "table", "figure", "trace", "rule", "other"]
Completeness = Literal["open", "closed", "unknown"]
Verdict = Literal["support", "refute", "not_in_evidence"]
RunStatus = Literal["ok", "partial"]


@dataclass(frozen=True)
class SourceRef:
    """Pointer to the upstream-frozen source material."""

    doc_id: str
    section: str = ""
    page: int | None = None
    block_id: str = ""
    row_id: str = ""
    region_id: str = ""


@dataclass(frozen=True)
class RetrievedEvidence:
    """One item from the upstream question-conditioned retrieved context."""

    evidence_id: str
    text: str
    source_type: SourceType
    source_ref: SourceRef
    scope_id: str
    completeness: Completeness = "unknown"
    completeness_proof: str = ""
    extraction_method: str = ""
    extraction_confidence: float | None = None


@dataclass(frozen=True)
class QAInput:
    """The consistency module input; this module never re-runs retrieval."""

    instance_id: str
    question: str
    answer: str
    context_freeze_id: str
    evidence: tuple[RetrievedEvidence, ...]


@dataclass(frozen=True)
class ClaimResult:
    claim_id: str
    claim_text: str
    verdict: Verdict
    check_item_candidates: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rationale: str
    method: str
    confidence: float
    #: answer内字符区间(断言级定位; 来自AnswerClaim.span, 组合claim可为None)
    span: tuple[int, int] | None = None


@dataclass(frozen=True)
class EvidenceLocalization:
    """一处证据侧定位: 语句级(statement_id) + 块/行/字段元数据."""

    evidence_id: str
    statement_id: str
    statement_text: str
    field_name: str
    row_index: int
    block_id: str
    section: str


@dataclass(frozen=True)
class InconsistencyLocalization:
    """一条不一致的完整定位报告(输出字段, 非分类).

    answer侧: claim_text + answer_span(best-effort文本定位);
    证据侧: 语句级evidence定位(块/行/字段);
    归因: 检测通道method + taxonomy check_item + rationale.
    根因(M92): root_cause两层分类(根因源×根因操作, 形如
    {"source": "answer", "operation": "value_substitution"}), 由
    algorithms.consistency.root_cause.classify_root_cause按
    method+rationale表驱动填充; 默认None保持向后兼容.
    """

    claim_id: str
    claim_text: str
    answer_span: tuple[int, int] | None
    check_item_candidates: tuple[str, ...]
    method: str
    confidence: float
    rationale: str
    evidence: tuple[EvidenceLocalization, ...]
    root_cause: dict[str, str] | None = None


@dataclass(frozen=True)
class VerificationResult:
    instance_id: str
    question: str
    answer: str
    verdict: Verdict
    status: RunStatus
    claim_results: tuple[ClaimResult, ...]
    evidence_chain: tuple[RetrievedEvidence, ...]
    considered_evidence_ids: tuple[str, ...]
    context_freeze_id: str
    context_hash: str
    context_integrity: Literal["complete", "partial", "unknown"]
    applicability: Literal["applicable", "uncertain"]
    rationale: str
    verifier_version: str = "qa_verifier_v1"
    diagnostics: tuple[str, ...] = field(default_factory=tuple)
    localizations: tuple[InconsistencyLocalization, ...] = field(
        default_factory=tuple)
