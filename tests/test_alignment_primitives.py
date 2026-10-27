import numpy as np
import pytest

from algorithms.context_linking.alignment import (
    StructuralCompatibility,
    fit_orthogonal_map,
    structural_score,
)


def test_procrustes_is_deterministic_and_normalizes_output() -> None:
    source = np.eye(3, dtype=np.float64)
    target = source[:, [1, 2, 0]]
    mapping = fit_orthogonal_map(source, target, ["b", "a", "c"], "source", "target")
    transformed = mapping.transform(source)

    assert mapping.anchor_ids == ("a", "b", "c")
    assert np.allclose(np.linalg.norm(transformed, axis=1), 1.0)
    assert mapping.anchor_hash


def test_procrustes_rejects_duplicate_or_insufficient_anchors() -> None:
    with pytest.raises(ValueError, match="at least two"):
        fit_orthogonal_map(np.ones((1, 2)), np.ones((1, 2)), ["a"], "a", "b")
    with pytest.raises(ValueError, match="unique"):
        fit_orthogonal_map(np.ones((2, 2)), np.ones((2, 2)), ["a", "a"], "a", "b")


def test_structural_gate_hard_veto_is_not_a_low_score_match() -> None:
    score, veto = structural_score(
        StructuralCompatibility(same_scope="incompatible", hard_veto=True)
    )

    assert veto is True
    assert score == float("-inf")
