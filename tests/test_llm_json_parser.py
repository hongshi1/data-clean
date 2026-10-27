"""JSON extraction tests for nested LLM annotation payloads."""
from __future__ import annotations

from algorithms.common.llm_client import _parse_json


def test_parse_json_preserves_nested_objects_and_arrays() -> None:
    source = '{"claims":[{"claim_id":"c1","diagnostics":{"scope":"open"}}],"ok":true}'
    assert _parse_json(source) == {
        "claims": [{"claim_id": "c1", "diagnostics": {"scope": "open"}}],
        "ok": True,
    }


def test_parse_json_extracts_nested_payload_from_fence() -> None:
    source = 'prefix\n```json\n{"outer":{"inner":[1,2]}}\n```\nsuffix'
    assert _parse_json(source) == {"outer": {"inner": [1, 2]}}
