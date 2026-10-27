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
