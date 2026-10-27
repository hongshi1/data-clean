"""Deterministic cross-space alignment primitives for direction A."""

from .late_interaction import bigram_tokens, idf_weighted_maxsim
from .procrustes import ProcrustesMap, fit_orthogonal_map
from .structural_gate import StructuralCompatibility, structural_score

__all__ = [
    "ProcrustesMap",
    "StructuralCompatibility",
    "bigram_tokens",
    "fit_orthogonal_map",
    "idf_weighted_maxsim",
    "structural_score",
]
