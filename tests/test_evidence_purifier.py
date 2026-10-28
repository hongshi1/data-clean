"""evidence_purifier收敛模块回归: 两种模式+DEQ门组合+配置护栏."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_purifier import (  # noqa: E402
    MODES,
    PurificationConfig,
    purify,
)

EV = [
    {"evidence_id": "ev-useful", "text": "BLOB数据插入功能的详细要求说明"},
    {"evidence_id": "ev-scope", "text": "数据库初始化配置参数详情"},
    {"evidence_id": "ev-ptr", "text": "系统备份恢复说明见表99所示。"},
]
Q = "BLOB数据插入能力的项目唯一标识符是什么？"
A = "BLOB数据插入能力的项目唯一标识符为PZXQ-GN-SQLFW-BLOBSJCR。"


def test_statement_mode_equals_subtract_behavior():
    """statement模式(默认): F1/F3删除+F2行级语句(71号场景).

    注: 无锚点块先命中F1(scope_mismatch)——与subtract核心的
    判序一致; 指针豁免路径见test_evidence_subtractor.
    """
    pack = purify(Q, A, EV)
    assert pack["mode"] == "statement"
    reasons = {r["evidence_id"]: r["reason_code"] for r in pack["removed"]}
    assert reasons.get("ev-scope") == "scope_mismatch"
    assert reasons.get("ev-ptr") == "scope_mismatch"  # 无锚点指针F1先行
    kept_ids = {k["evidence_id"] for k in pack["kept"]}
    assert kept_ids == {"ev-useful"}
    stmts = [s for k in pack["kept"] for s in k["statements"]]
    assert stmts and all(isinstance(s, str) for s in stmts)


def test_evidence_mode_keeps_original_text():
    """evidence模式: 只删块不改写(73号教训, 结构化消费方)."""
    pack = purify(Q, A, EV, PurificationConfig(mode="evidence"))
    assert pack["mode"] == "evidence"
    kept = pack["kept"]
    assert [k["evidence_id"] for k in kept] == ["ev-useful"]
    assert kept[0]["text"] == "BLOB数据插入功能的详细要求说明"  # 原文未改写
    assert pack["stats"]["n_removed"] == 2


def test_evidence_mode_id_exemption():
    """evidence模式ID豁免: 含PZXQ式ID的证据块不做scope删除."""
    ev = [
        {"evidence_id": "ev-id", "text": "3.2.1.4.1.2 BLOB数据操作-BLOB数据修改"
         "（PZXQ-GN-SQLFW-BLOBSJCZ-BLOBSJXG）"},
        {"evidence_id": "ev-scope", "text": "数据库初始化配置参数详情"},
    ]
    pack = purify(Q, A, ev, PurificationConfig(mode="evidence"))
    kept_ids = {k["evidence_id"] for k in pack["kept"]}
    assert kept_ids == {"ev-id"}  # ID豁免生效


def test_evidence_mode_deq_gate_composition():
    """evidence模式+DEQ门: 无锚点块被DEQ门删除, 台账记deq_gate."""
    ev = [
        {"evidence_id": "ev-d1", "text": "BLOB数据插入的完整处理流程",
         "source_type": "text",
         "source_ref": {"doc_id": "d", "section": "s", "page": 1,
                        "block_id": "b", "row_id": "", "region_id": ""},
         "scope_id": "d:b1"},
        {"evidence_id": "ev-d2", "text": "完全无关的另一个主题的说明内容",
         "source_type": "text",
         "source_ref": {"doc_id": "d", "section": "s", "page": 1,
                        "block_id": "b2", "row_id": "", "region_id": ""},
         "scope_id": "d:b2"},
    ]
    pack = purify(Q, A, ev, PurificationConfig(mode="evidence",
                                               use_deq_gate=True))
    reasons = {r["reason_code"] for r in pack["removed"]}
    stages = {r["stage"] for r in pack["removed"]}
    assert "deq_scope_mismatch" in reasons or "scope_mismatch" in reasons
    assert stages <= {"F1", "F3", "deq_gate"}


def test_fallback_guard_both_modes():
    """护栏: 两种模式在F1删光时都回退保留全部."""
    ev = [{"evidence_id": "x1", "text": "完全无关内容"}]
    for cfg in (PurificationConfig(), PurificationConfig(mode="evidence")):
        pack = purify(Q, A, ev, cfg)
        assert pack["stats"]["fallback"] is True
        assert len(pack["kept"]) == 1


def test_invalid_mode_rejected():
    with pytest.raises(ValueError, match="mode"):
        PurificationConfig(mode="rewrite")


def test_modes_exported():
    assert MODES == ("statement", "evidence")
