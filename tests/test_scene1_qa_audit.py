"""场景1高质量QA(对方提供)适配审计快照: 91条 ↔ 04号SRS证据定位.

锁定:
  - 总量与family/triage分布
  - schema: 审计字段完备且gold_verdict留空(不冒充gold)
  - 代表性锚点(65535/异常流E1)可定位
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
AUDIT = BASE / "data/gjb_438c/scene1_qa_audit.json"
D = json.loads(AUDIT.read_text(encoding="utf-8"))
E = D["entries"]


def test_total() -> None:
    assert len(E) == 91


def test_triage_distribution() -> None:
    from collections import Counter
    triage = Counter(e["triage"] for e in E)
    assert dict(triage) == {"locatable": 90, "weak": 1}


def test_family_distribution() -> None:
    from collections import Counter
    fams = Counter(e["family"] for e in E)
    assert dict(fams) == {
        "主事件流/步骤": 9, "其他": 11, "前置条件": 7, "功能/支持": 21,
        "参与者": 1, "异常/错误": 19, "接口/参数": 15, "状态/阶段/设备": 6,
        "规则/一致性": 2,
    }


def test_schema_and_no_gold() -> None:
    """审计资产不含gold判定: gold_verdict全None, 留给M3人工双标."""
    for e in E:
        assert e["id"].startswith("S1QA-")
        assert e["question"]
        assert e["answer"]
        assert e["family"]
        assert isinstance(e["tentative_check_items"], list)
        assert isinstance(e["evidence_hits"], list)
        assert e["triage"] in ("locatable", "weak", "unlocatable")
        assert e["gold_verdict"] is None


def test_numeric_anchor_locatable() -> None:
    """65535(唯一数值约束)须可定位到04号SRS."""
    hits = [e for e in E if "65535" in e["strong_anchors"]]
    assert len(hits) >= 2
    assert all(e["triage"] == "locatable" for e in hits)


def test_exception_flow_anchor() -> None:
    """异常流E1锚点命中(S1QA-001首条即含)."""
    e1 = [e for e in E if "E1" in e["strong_anchors"]]
    assert len(e1) >= 10
    assert e1[0]["tentative_check_items"] == ["LOGIC-02"]


def test_provenance_sources_exist() -> None:
    qa_path = BASE / D["meta"]["source_qa"]
    srs_path = BASE / D["meta"]["source_srs"]
    assert qa_path.exists()
    assert srs_path.exists()
