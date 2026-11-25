"""场景五声明-观测核验API接线测试(app.py: verify_qa/verify_dataset的模块层内核).

路由为薄封装(不启服务器): 本文件直接调app.py模块层helper
(_kg_verify_by_id/_kg_verify_summary, 数据来自claim_verify.run_dataset的模块级缓存).

冻结数字(2026-11-24基线, 与tests/test_claim_verify.py同源):
  counts: support×3 / refute×12 / NIE×29
  reasons(细化): no_object_channel×9 / no_ppe_detection×7 / temporal×7 / answer_unverifiable×4 / no_person_target×1 / ambiguous×1
  数字变更须有意为之(数据集qa_dataset.jsonl受MANIFEST保护;
  裁决口径变更须同步tests/test_claim_verify.py的快照).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1] / "deploy" / "nkuDataProject" / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import app  # noqa: E402 — 导入触发DB探活(失败被app内部捕获, 不影响模块层helper)

_DATASET = _BACKEND.parent / "data" / "kg_supervision" / "qa_dataset.jsonl"

pytestmark = pytest.mark.skipif(not _DATASET.exists(), reason="内置数据集缺失")


def test_verify_by_id_refute_with_facts() -> None:
    """qa_id=0(ppe_001): 声明"右侧人员未佩戴" vs 真实观测Hardhat佩戴 → refute."""
    r = app._kg_verify_by_id(0)
    assert r is not None
    assert r["verdict"] == "refute"
    assert r["nie_reason"] is None
    assert r["facts"], "refute须携带per-fact证据链"
    f = r["facts"][0]
    assert {"claim", "grounded_chunk", "observation", "fact_verdict", "reason"} <= set(f)
    assert f["claim"] == "画面中右侧人员未佩戴安全帽"
    assert f["grounded_chunk"] == "人员#3(画面右侧, 横向90%处)"
    assert f["fact_verdict"] == "refute"


def test_verify_by_id_support() -> None:
    """qa_id=7(ppe_001): 声明"全员佩戴"且观测无未佩戴记录 → support."""
    r = app._kg_verify_by_id(7)
    assert r is not None
    assert r["verdict"] == "support"
    assert r["nie_reason"] is None
    assert r["facts"][0]["fact_verdict"] == "support"


def test_verify_by_id_sleep_nie_temporal() -> None:
    """睡岗qa(22-27, question含"睡岗"): 时序型判定对象, 单帧观测不可证 → NIE(temporal)."""
    for qa_id in range(22, 28):
        r = app._kg_verify_by_id(qa_id)
        assert r is not None
        assert r["verdict"] == "NIE"
        assert r["nie_reason"] == "temporal"
        assert r["facts"][0]["reason_tag"] == "temporal"


def test_verify_by_id_out_of_range() -> None:
    """越界qa_id → 模块层返回None(路由据此返回400; HTTP层不在此测)."""
    assert app._kg_verify_by_id(-1) is None
    assert app._kg_verify_by_id(44) is None
    assert app._kg_verify_by_id(9999) is None


def test_verify_dataset_summary_frozen() -> None:
    """全量聚合冻结: 44条items(qa_id=0..43)+counts+reasons(数字变更须有意为之)."""
    d = app._kg_verify_summary()
    assert len(d["items"]) == 44
    assert d["counts"] == {"support": 3, "refute": 12, "NIE": 29}
    assert d["reasons"] == {"no_object_channel": 9, "no_ppe_detection": 7,
                            "temporal": 7, "answer_unverifiable": 4,
                            "no_person_target": 1, "ambiguous": 1}
    assert [x["qa_id"] for x in d["items"]] == list(range(44))
    assert d["items"][0] == {"qa_id": 0, "verdict": "refute", "nie_reason": None}
    # items与逐条核验同源(同一模块级缓存): 抽查两条口径一致
    assert app._kg_verify_by_id(7)["verdict"] == d["items"][7]["verdict"] == "support"
    assert app._kg_verify_by_id(22)["nie_reason"] == d["items"][22]["nie_reason"]
