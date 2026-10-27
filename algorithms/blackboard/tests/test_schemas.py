"""schemas单元测试: 指纹/枚举/序列化."""
from __future__ import annotations

import json

from algorithms.blackboard.schemas import (Channel, ConfSource, Epistemic,
                                            EvidenceItem, Provenance)


def _item(subject="table_structure", payload=None) -> EvidenceItem:
    return EvidenceItem(
        subject=subject, channel=Channel.KT, epistemic=Epistemic.FACT,
        confidence=1.0, conf_source=ConfSource.DETERMINISTIC,
        payload=payload or {"type": "capability", "nodes": []},
        provenance=Provenance(source="x.csv", locator="1_001"))


def test_fingerprint_stable_and_sensitive():
    a, b = _item(), _item()
    assert a.fingerprint() == b.fingerprint()
    c = _item(payload={"type": "interface", "nodes": []})
    assert a.fingerprint() != c.fingerprint()
    d = _item(subject="diagram_structure")
    assert a.fingerprint() != d.fingerprint()


def test_fingerprint_key_order_independent():
    a = _item(payload={"x": 1, "y": [2, 3]})
    b = _item(payload={"y": [2, 3], "x": 1})
    assert a.fingerprint() == b.fingerprint()


def test_brief_compact():
    it = _item(payload={"nodes": ["n" * 500]})
    brief = it.brief()
    assert set(brief) == {"subject", "channel", "epistemic", "confidence",
                          "conf_source", "payload_keys", "note"}
    json.dumps(brief, ensure_ascii=False)  # 可序列化


def test_channel_enum_values_unique():
    vals = [c.value for c in Channel]
    assert len(vals) == len(set(vals))
    assert Channel.ANCHOR.value == "anchor"
    assert Epistemic.HYPOTHESIS.value == "hypothesis"
