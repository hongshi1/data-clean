"""Deterministic orthogonal alignment between frozen embedding spaces."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ProcrustesMap:
    """A reproducible centered orthogonal map fitted on ordered anchors."""

    source_name: str
    target_name: str
    source_mean: tuple[float, ...]
    target_mean: tuple[float, ...]
    rotation: tuple[tuple[float, ...], ...]
    anchor_ids: tuple[str, ...]
    anchor_hash: str

    @property
    def dimension(self) -> int:
        return len(self.source_mean)

    def transform(self, vectors: np.ndarray) -> np.ndarray:
        values = np.asarray(vectors, dtype=np.float64)
        if values.ndim != 2 or values.shape[1] != self.dimension:
            raise ValueError("vectors must have shape (n, fitted_dimension)")
        mean = np.asarray(self.source_mean, dtype=np.float64)
        rotation = np.asarray(self.rotation, dtype=np.float64)
        transformed = (values - mean) @ rotation
        norms = np.linalg.norm(transformed, axis=1, keepdims=True)
        return transformed / np.maximum(norms, 1e-12)


def fit_orthogonal_map(
    source: np.ndarray,
    target: np.ndarray,
    anchor_ids: list[str] | tuple[str, ...],
    source_name: str,
    target_name: str,
) -> ProcrustesMap:
    """Fit a centered, orthogonal Procrustes map without randomness.

    Anchor order is made deterministic by sorting ``anchor_ids``. Duplicate
    IDs and mismatched dimensions are rejected instead of silently repaired.
    """

    source_array = np.asarray(source, dtype=np.float64)
    target_array = np.asarray(target, dtype=np.float64)
    ids = tuple(anchor_ids)
    if source_array.ndim != 2 or target_array.ndim != 2:
        raise ValueError("source and target must be two-dimensional")
    if source_array.shape != target_array.shape:
        raise ValueError("source and target must have the same shape")
    if source_array.shape[0] < 2:
        raise ValueError("at least two anchors are required")
    if len(ids) != source_array.shape[0] or len(set(ids)) != len(ids):
        raise ValueError("anchor_ids must be unique and match the row count")
    order = np.argsort(np.asarray(ids, dtype=object), kind="stable")
    source_ordered = source_array[order]
    target_ordered = target_array[order]
    ids_ordered = tuple(ids[index] for index in order)
    source_mean = source_ordered.mean(axis=0)
    target_mean = target_ordered.mean(axis=0)
    source_centered = source_ordered - source_mean
    target_centered = target_ordered - target_mean
    cross_covariance = source_centered.T @ target_centered
    left, _, right_transposed = np.linalg.svd(cross_covariance, full_matrices=False)
    rotation = left @ right_transposed
    anchor_hash = hashlib.sha256("\n".join(ids_ordered).encode("utf-8")).hexdigest()
    return ProcrustesMap(
        source_name=source_name,
        target_name=target_name,
        source_mean=tuple(float(value) for value in source_mean),
        target_mean=tuple(float(value) for value in target_mean),
        rotation=tuple(tuple(float(value) for value in row) for row in rotation),
        anchor_ids=ids_ordered,
        anchor_hash=anchor_hash,
    )
