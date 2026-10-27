"""Auditable structural compatibility scoring for candidate links."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Compatibility = Literal["compatible", "unknown", "incompatible"]


@dataclass(frozen=True)
class StructuralCompatibility:
    """Decomposed structural evidence; it is not an identity gold label."""

    same_doc: Compatibility = "unknown"
    same_section: Compatibility = "unknown"
    same_role: Compatibility = "unknown"
    same_scope: Compatibility = "unknown"
    identifier_match: bool = False
    hard_veto: bool = False


def structural_score(features: StructuralCompatibility) -> tuple[float, bool]:
    """Return a deterministic score and whether identity is hard-vetoed."""

    if features.hard_veto:
        return float("-inf"), True
    weights = {
        "compatible": 1.0,
        "unknown": 0.0,
        "incompatible": -1.0,
    }
    score = (
        0.15 * weights[features.same_doc]
        + 0.15 * weights[features.same_section]
        + 0.25 * weights[features.same_role]
        + 0.30 * weights[features.same_scope]
        + (0.75 if features.identifier_match else 0.0)
    )
    return score, False
