"""Shared domain objects for the multimodal data-quality pipeline.

This package contains contracts only. It intentionally has no file, model, or
network I/O and does not import either the A or B workflow.
"""

from .models import (
    CandidateLink,
    Claim,
    EntityCandidate,
    Event,
    Item,
    ObservationAlignment,
    Occurrence,
    ParserObservation,
    QualityContract,
    QualityHypothesis,
    SourceRef,
    SourceVersion,
    Value,
)

__all__ = [
    "CandidateLink",
    "Claim",
    "EntityCandidate",
    "Event",
    "Item",
    "ObservationAlignment",
    "Occurrence",
    "ParserObservation",
    "QualityContract",
    "QualityHypothesis",
    "SourceRef",
    "SourceVersion",
    "Value",
]
