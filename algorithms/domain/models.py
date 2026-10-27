"""I/O-free domain contracts for source-aware multimodal quality analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceType = Literal[
    "text_fragment",
    "table_row",
    "image_element",
    "temporal_event",
]
ParseStatus = Literal["parsed", "partial", "ambiguous", "unparsed"]
LinkRelation = Literal[
    "same_identity",
    "explicit_reference",
    "structural_membership",
    "semantic_neighbor",
    "field_alignment",
]
LinkStatus = Literal["candidate", "accepted", "rejected", "ambiguous"]
AlignmentStatus = Literal[
    "candidate", "accepted", "rejected", "ambiguous", "unmatched"
]
Completeness = Literal["complete", "partial", "open", "unknown", "ambiguous"]
ObservationModality = Literal[
    "text",
    "table",
    "image",
    "diagram_node",
    "diagram_edge",
    "temporal_event",
]
MethodKind = Literal["deterministic", "heuristic", "calibrated", "llm", "vlm"]


@dataclass(frozen=True)
class SourceVersion:
    """Immutable identity of an input or derived source version."""

    source_id: str
    version_id: str
    content_hash: str
    parent_version: str | None = None
    parser_id: str = ""
    parser_version: str = ""
    valid_time: str = ""


@dataclass(frozen=True)
class SourceRef:
    """A precise pointer into a document, image, table, or stream."""

    source_version_id: str
    source_type: SourceType
    section: str = ""
    page: int | None = None
    block_id: str = ""
    table_id: str = ""
    row_id: str = ""
    cell_id: str = ""
    node_id: str = ""
    region_id: str = ""
    event_index: int | None = None
    timestamp: str = ""
    raw_asset_ref: str = ""


@dataclass(frozen=True)
class ParserObservation:
    """Loss-minimizing parser output before semantic normalization."""

    observation_id: str
    source_version_id: str
    modality: ObservationModality
    raw_payload_json: str
    locator: SourceRef
    status: ParseStatus = "parsed"
    method_kind: MethodKind = "deterministic"
    method_id: str = ""
    confidence: float | None = None
    parent_observation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ObservationAlignment:
    """Candidate correspondence between parser observations of source content."""

    source_observation_id: str
    target_observation_id: str
    alignment_type: str
    evidence_refs: tuple[str, ...] = ()
    features_json: str = "{}"
    status: AlignmentStatus = "candidate"
    confidence: float | None = None


@dataclass(frozen=True)
class Value:
    """Original and normalized value, with explicit missingness semantics."""

    raw_text: str
    typed_value: str | int | float | bool | None = None
    unit: str = ""
    precision: str = ""
    interval: tuple[float, float] | None = None
    missingness: Literal["present", "missing", "unknown", "not_applicable"] = "present"


@dataclass(frozen=True)
class Occurrence:
    """One observed mention or event; occurrences are never merged implicitly."""

    occurrence_id: str
    source_ref: SourceRef
    raw_value: str
    normalized_value: str = ""
    parse_status: ParseStatus = "parsed"
    extraction_method: str = ""
    extraction_confidence: float | None = None


@dataclass(frozen=True)
class EntityCandidate:
    """A parser candidate, not an identity decision or a final Item."""

    candidate_id: str
    entity_type: str
    canonical_name: str = ""
    aliases: tuple[str, ...] = ()
    scope: str = ""
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class Claim:
    """An atomic fact linked back to one or more source occurrences."""

    claim_id: str
    subject: str
    predicate: str
    object_value: str = ""
    value: Value | None = None
    operator: str = ""
    unit: str = ""
    condition: str = ""
    scope: str = ""
    valid_time: str = ""
    occurrence_refs: tuple[str, ...] = ()
    source_spans: tuple[str, ...] = ()
    parse_status: ParseStatus = "parsed"


@dataclass(frozen=True)
class Event:
    """A temporal observation with event and observation time kept separate."""

    event_id: str
    event_type: str
    event_time: str
    observation_time: str = ""
    sequence_id: str = ""
    claim_refs: tuple[str, ...] = ()
    sampling_window: str = ""
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateLink:
    """Typed, directed, and reversible link hypothesis between occurrences."""

    source_occurrence: str
    target_occurrence: str
    relation: LinkRelation
    confidence: float
    evidence_refs: tuple[str, ...] = ()
    status: LinkStatus = "candidate"
    direction: Literal["directed", "symmetric"] = "directed"


@dataclass(frozen=True)
class Item:
    """Task-level aggregation, produced only after link decisions."""

    item_id: str
    entity_key: str = ""
    semantic_role: str = ""
    occurrence_refs: tuple[str, ...] = ()
    accepted_links: tuple[CandidateLink, ...] = ()
    unresolved_links: tuple[CandidateLink, ...] = ()
    completeness: Completeness = "unknown"


@dataclass(frozen=True)
class QualityContract:
    """Declarative quality-check contract consumed by a validator."""

    quality_type: str
    target_schema: str
    preconditions: tuple[str, ...] = ()
    evidence_obligations: tuple[str, ...] = ()
    counterevidence_conditions: tuple[str, ...] = ()
    validator: str = ""
    abstain_policy: str = ""
    output_schema: str = ""


@dataclass(frozen=True)
class QualityHypothesis:
    """A testable quality hypothesis and its current evidence state."""

    hypothesis_id: str
    quality_type: str
    target_refs: tuple[str, ...] = ()
    obligation_status: tuple[tuple[str, bool], ...] = ()
    counterevidence_refs: tuple[str, ...] = ()
    validator: str = ""
    status: Literal["open", "supported", "refuted", "insufficient", "ambiguous"] = "open"
    confidence: float | None = None
