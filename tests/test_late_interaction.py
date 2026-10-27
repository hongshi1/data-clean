import numpy as np
import pytest

from algorithms.context_linking.alignment import bigram_tokens, idf_weighted_maxsim
from algorithms.context_linking.evidence_recall.heads import tokenize


def _normalized(rows: list[list[float]]) -> np.ndarray:
    matrix = np.asarray(rows, dtype=np.float64)
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def test_self_similarity_is_one() -> None:
    matrix = _normalized(np.arange(40, dtype=np.float64).reshape(5, 8) + 1.0)
    assert idf_weighted_maxsim(matrix, matrix, None) == pytest.approx(1.0, abs=1e-9)
    idf = np.asarray([0.5, 2.0, 1.0, 3.0, 1.5])
    assert idf_weighted_maxsim(matrix, matrix, idf) == pytest.approx(1.0, abs=1e-9)


def test_orthogonal_tokens_score_zero() -> None:
    query = _normalized([[1.0, 0.0]])
    doc = _normalized([[0.0, 1.0]])
    assert idf_weighted_maxsim(query, doc, None) == pytest.approx(0.0, abs=1e-12)


def test_idf_weights_change_result() -> None:
    query = _normalized([[1.0, 0.0], [0.0, 1.0]])
    doc = _normalized([[1.0, 0.0]])
    uniform = idf_weighted_maxsim(query, doc, None)
    weighted = idf_weighted_maxsim(query, doc, np.asarray([3.0, 1.0]))
    assert uniform == pytest.approx(0.5, abs=1e-12)
    assert weighted == pytest.approx(0.75, abs=1e-12)
    assert weighted > uniform


def test_empty_doc_returns_zero() -> None:
    query = _normalized([[1.0, 0.0]])
    empty = np.zeros((0, 2), dtype=np.float64)
    assert idf_weighted_maxsim(query, empty, None) == 0.0
    assert idf_weighted_maxsim(empty, query, None) == 0.0


def test_no_idf_is_mean_not_sum() -> None:
    query = _normalized([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    doc = _normalized([[1.0, 0.0]])
    # mean MaxSim = (3*1 + 0)/4 = 0.75; a raw sum would leave the scale at 3.0.
    assert idf_weighted_maxsim(query, doc, None) == pytest.approx(0.75, abs=1e-12)


def test_input_validation() -> None:
    query = _normalized([[1.0, 0.0]])
    mismatched = _normalized([[0.0, 1.0, 0.0]])
    with pytest.raises(ValueError):
        idf_weighted_maxsim(query, mismatched, None)
    square = _normalized([[1.0, 0.0], [0.0, 1.0]])
    with pytest.raises(ValueError):
        idf_weighted_maxsim(square, square, np.asarray([1.0]))


def test_bigram_tokens_matches_reference_tokenizer() -> None:
    text = "数据获取转换服务TESTSYS-GN-01接口"
    assert bigram_tokens(text) == tokenize(text)
    assert bigram_tokens("") == []
