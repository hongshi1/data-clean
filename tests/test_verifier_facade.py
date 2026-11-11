"""CascadeVerifier门面回归: 极简证据输入/purify选项/三态输出(77号)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.verifier import (  # noqa: E402
    PRESETS,
    SCENES,
    CascadeVerifier,
    _normalize_evidence,
)

# fast档(纯专家通道, 零模型加载)保证测试确定性
EV_ID = [{
    "evidence_id": "ev-1", "text": "3.2.5.1 连接池管理-连接池配置"
    "（PZXQ-GN-LJCGL-LJCPZ）",
    "source_type": "text",
    "source_ref": {"doc_id": "d", "section": "s", "page": 1,
                   "block_id": "b", "row_id": "", "region_id": ""},
    "scope_id": "d:b1",
}]


def test_minimal_evidence_normalization():
    """极简输入{text}自动补全冻结格式必填字段."""
    blocks = _normalize_evidence([{"text": "连接池配置 PZXQ-LJCPZ"}], 7)
    assert len(blocks) == 1
    b = blocks[0]
    assert b["evidence_id"] == "facade-7-ev-000"
    assert b["source_type"] == "text"
    assert b["source_ref"]["doc_id"] == "facade"
    assert b["scope_id"] == "facade:7"
    assert b["text"] == "连接池配置 PZXQ-LJCPZ"


def test_full_format_passes_through():
    """完整格式原样通过(用户字段不覆盖)."""
    blocks = _normalize_evidence(EV_ID, 1)
    assert blocks == EV_ID


def test_missing_text_raises():
    with pytest.raises(ValueError, match="text"):
        _normalize_evidence([{"evidence_id": "x"}], 1)


def test_fast_preset_minimal_input_verify():
    """三行代码可用: 极简evidence → 三态判定(fast档确定性)."""
    v = CascadeVerifier(preset="fast")
    r = v.verify(
        question="连接池配置用例的项目唯一标识符是什么？",
        answer="PZXQ-GN-LJCGL-LJCPZ",
        evidence=[{"text": "3.2.5.1 连接池管理-连接池配置"
                          "（PZXQ-GN-LJCGL-LJCPZ）"}])
    assert r.verdict in ("support", "refute", "not_in_evidence")
    assert r.verdict == "support"  # ID在证据中出现


def test_purify_option_wired():
    """purify=True → 引擎带use_subtractor(证据提纯生效)."""
    v = CascadeVerifier(preset="fast", purify=True)
    engine = v._engine_instance  # noqa: SLF001 — 显式触发构造
    assert engine.use_subtractor is True
    v2 = CascadeVerifier(preset="fast")
    assert v2._engine_instance.use_subtractor is False  # noqa: SLF001


def test_invalid_preset_scene_rejected():
    with pytest.raises(ValueError, match="preset"):
        CascadeVerifier(preset="ultra")
    with pytest.raises(ValueError, match="scene"):
        CascadeVerifier(scene="nope")


def test_presets_scenes_exported():
    assert set(PRESETS) == {"fast", "standard", "crossdoc"}  # v3: crossdoc档(域自适应)
    assert "srs_scene1" in SCENES
