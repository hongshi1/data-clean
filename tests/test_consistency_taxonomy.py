"""consistency_taxonomy_v2 冻结快照: 40项操作化映射.

锁定: 总量/ID序列/必填字段/枚举值/模块归属分布; scene1审计的
tentative_check_items必须是taxonomy ID(或PARAM泛型)的子集。
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TAX = json.loads(
    (BASE / "knowledge/consistency_taxonomy_v2.json").read_text(encoding="utf-8"))
ITEMS = TAX["items"]
IDS = [x["id"] for x in ITEMS]


def test_total_and_id_sequence() -> None:
    assert len(ITEMS) == 40
    expect = ([f"TERM-{i:02d}" for i in range(1, 9)]
              + [f"PARAM-{i:02d}" for i in range(1, 11)]
              + [f"LOGIC-{i:02d}" for i in range(1, 12)]
              + [f"GJB-{i:02d}" for i in range(1, 12)])
    assert IDS == expect


def test_required_fields_and_enums() -> None:
    for x in ITEMS:
        assert x["legacy_name"]
        assert x["module_assignment"] in ("main_B", "compliance_subtask",
                                          "needs_decision", "needs_data")
        assert x["task_subtype"] in ("B_fact_verification", "C_rule_compliance",
                                     "mixed")
        assert set(x["label_rules"]) == {"support", "refute", "not_in_evidence"}
        assert x["data_readiness"] in ("real_gold", "derived", "mutation",
                                       "needs_data", "none")
        assert x["method_readiness"] in ("not_started", "prototype", "validated")
        assert isinstance(x["benign_variants"], list) and x["benign_variants"]
        assert isinstance(x["baseline_ids"], list)


def test_module_assignment_distribution() -> None:
    from collections import Counter
    assert dict(Counter(x["module_assignment"] for x in ITEMS)) == {
        "main_B": 29, "compliance_subtask": 11}


def test_no_method_claimed_validated() -> None:
    """设计稿约束: 无一项method_readiness=validated."""
    assert all(x["method_readiness"] != "validated" for x in ITEMS)


def test_scene1_tentative_items_are_known_ids() -> None:
    audit = json.loads((BASE / "data/gjb_438c/scene1_qa_audit.json")
                       .read_text(encoding="utf-8"))
    known = set(IDS) | {"PARAM"}  # PARAM为接口/参数family的泛型占位
    for e in audit["entries"]:
        for c in e["tentative_check_items"]:
            assert c in known, (e["id"], c)


def test_gjb05_and_gjb11_mixed_split() -> None:
    """GJB-05具体追溯映射/GJB-11模式存在性可走B三态(mixed); 触发阈值归PARAM-09."""
    gjb05 = next(x for x in ITEMS if x["id"] == "GJB-05")
    gjb11 = next(x for x in ITEMS if x["id"] == "GJB-11")
    assert gjb05["task_subtype"] == "mixed"
    assert gjb11["task_subtype"] == "mixed"
    assert "PARAM-09" in gjb11["notes"]
