"""Minimal HTTP contract tests for the server QA verification endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from server.main import app


client = TestClient(app)


def _payload() -> dict:
    return {
        "instance_id": "api-qa-1",
        "question": "系统响应时间要求是多少？",
        "answer": "响应时间为200ms。",
        "context_freeze_id": "frozen-api-context-1",
        "evidence": [
            {
                "evidence_id": "e1",
                "text": "响应时间为200ms。",
                "source_type": "text",
                "source_ref": {
                    "doc_id": "doc01",
                    "section": "3.2.1",
                    "page": 3,
                },
                "scope_id": "doc01:3.2.1",
                "completeness": "open",
            }
        ],
    }


def test_verify_api_returns_serializable_verification_result() -> None:
    response = client.post("/api/verify", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["instance_id"] == "api-qa-1"
    assert body["question"] == _payload()["question"]
    assert body["answer"] == _payload()["answer"]
    assert body["verdict"] == "support"
    assert body["context_freeze_id"] == "frozen-api-context-1"
    assert body["considered_evidence_ids"] == ["e1"]
    assert body["evidence_chain"][0]["source_ref"]["section"] == "3.2.1"
    assert len(body["context_hash"]) == 64


def test_verify_api_requires_frozen_context_fields() -> None:
    payload = _payload()
    del payload["context_freeze_id"]

    response = client.post("/api/verify", json=payload)

    assert response.status_code == 422


def test_legacy_check_api_is_explicitly_disabled() -> None:
    response = client.post("/api/check/01")

    assert response.status_code == 410
