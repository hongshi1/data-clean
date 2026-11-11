"""v3域自适应档位契约测试.

standard=域内档(typed+strict, 默认模型distilled_v1@gate0.8),
crossdoc=跨文档档(sentence+dominant_70), refactor_matrix_v1实测.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_claims import (  # noqa: E402
    decompose_claims_sentences,
)
from algorithms.consistency.nli_residual import (  # noqa: E402
    DEFAULT_GATE,
    DEFAULT_MODEL_KEY,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.verifier import PRESETS  # noqa: E402


def test_crossdoc_preset_wiring() -> None:
    preset = PRESETS["crossdoc"]
    assert preset["decomposer"] == "sentence"
    assert preset["aggregation"] == "dominant_70"
    assert preset["use_nli_residual"] is True
    assert preset["use_experts"] is True


def test_standard_preset_keeps_in_domain_semantics() -> None:
    preset = PRESETS["standard"]
    assert "decomposer" not in preset  # 默认typed
    assert "aggregation" not in preset  # 默认strict


def test_decomposer_param_dispatch() -> None:
    typed_mod = QAConsistencyModule(use_experts=True)
    assert typed_mod._decomposer.__name__ == "decompose_claims"
    sent_mod = QAConsistencyModule(use_experts=True, decomposer="sentence")
    assert (sent_mod._decomposer.__name__
            == "decompose_claims_sentences")


def test_decomposer_invalid_rejected() -> None:
    with pytest.raises(ValueError, match="decomposer"):
        QAConsistencyModule(use_experts=True, decomposer="regex99")


def test_sentence_decomposer_list_item_grouping() -> None:
    answer = ("功能包括：\n1. **添加**：插入数据。\n2. **删除**：删除数据。\n"
              "以上操作均支持。")
    claims = decompose_claims_sentences("q", answer)
    texts = [c.text for c in claims]
    # 编号项与其描述保持一条claim(续行并入)
    assert any("添加" in t and "插入数据" in t for t in texts)
    assert any("删除" in t and "删除数据" in t for t in texts)
    assert all(c.kind == "semantic" for c in claims)


def test_sentence_decomposer_plain_sentences() -> None:
    claims = decompose_claims_sentences("q", "第一句。第二句！第三句？")
    assert len(claims) == 3
    assert claims[0].text == "第一句。"
    assert claims[2].text == "第三句？"


def test_sentence_decomposer_decimal_not_list_item() -> None:
    claims = decompose_claims_sentences("q", "频率为1.5GHz。")
    assert len(claims) == 1
    assert "1.5GHz" in claims[0].text


def test_defaults_promoted_to_paper_config() -> None:
    assert DEFAULT_MODEL_KEY == "distilled_v1"
    assert DEFAULT_GATE == 0.8
