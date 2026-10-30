"""HTTP contract + e2e smoke tests for the frozen-QA convenience verify endpoints."""
from __future__ import annotations

import server.main as server_main
from fastapi.testclient import TestClient

from server.main import FROZEN_QA, app

client = TestClient(app)

#: fast档纯确定性专家通道, 以下三例覆盖三态且与silver一致(冒烟锚点)
SUPPORT_ID = "S1QA-021"
NIE_ID = "S1QA-001"
REFUTE_ID = "S1QA-056"


def test_qa_list_returns_all_frozen_items() -> None:
    response = client.get("/api/verify/qa_list")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == len(FROZEN_QA) == 91
    first = items[0]
    assert set(first) == {
        "instance_id", "question", "answer", "scene", "silver_verdict"}
    assert first["scene"] == "srs_scene1"
    assert all(len(it["question"]) <= 80 for it in items)
    assert all(len(it["answer"]) <= 80 for it in items)
    assert {it["silver_verdict"] for it in items} <= {
        "support", "refute", "not_in_evidence"}


def test_verify_by_id_three_way_verdicts() -> None:
    for instance_id, expected in [
        (SUPPORT_ID, "support"),
        (NIE_ID, "not_in_evidence"),
        (REFUTE_ID, "refute"),
    ]:
        response = client.post(
            f"/api/verify_qa/{instance_id}", json={"preset": "fast"})

        assert response.status_code == 200, instance_id
        body = response.json()
        assert body["instance_id"] == instance_id
        assert body["verdict"] == expected, instance_id
        assert body["question"]
        assert body["answer"]
        assert isinstance(body["evidence"], list) and body["evidence"]
        assert body["evidence"][0]["evidence_id"].startswith(
            f"{instance_id}-ev-")
        assert body["silver_verdict"] in {
            "support", "refute", "not_in_evidence"}
        assert body["latency_ms"] >= 0
        assert isinstance(body["claim_results"], list)


def test_verify_by_id_s1qa_056_e2e_smoke() -> None:
    response = client.post("/api/verify_qa/S1QA-056", json={"preset": "fast"})

    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "refute"
    assert body["silver_verdict"] == "refute"
    assert any(claim["verdict"] == "refute"
               for claim in body["claim_results"])
    refute_claims = [c for c in body["claim_results"] if c["verdict"] == "refute"]
    assert all(c["evidence_refs"] for c in refute_claims)
    evidence_ids = {ev["evidence_id"] for ev in body["evidence"]}
    referenced = {
        ref.split("#")[0]
        for c in body["claim_results"]
        for ref in c["evidence_refs"]
    }
    assert referenced <= evidence_ids


def test_verify_by_id_unknown_instance_returns_404() -> None:
    response = client.post("/api/verify_qa/S1QA-999", json={})

    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]


def test_verify_by_id_rejects_unknown_preset() -> None:
    response = client.post(
        "/api/verify_qa/S1QA-001", json={"preset": "turbo"})

    assert response.status_code == 422


def test_verify_by_id_forwards_preset_and_scene(monkeypatch) -> None:
    captured: dict[tuple[str, str], object] = {}

    def spy_get_verifier(preset: str, scene: str):
        captured["args"] = (preset, scene)
        return server_main.QA_VERIFIER

    monkeypatch.setattr(server_main, "_get_verifier", spy_get_verifier)
    response = client.post(
        "/api/verify_qa/S1QA-001",
        json={"preset": "standard", "scene": "srs_scene1"})

    assert response.status_code == 200
    assert captured["args"] == ("standard", "srs_scene1")

    response_default = client.post("/api/verify_qa/S1QA-001", json={})
    assert response_default.status_code == 200
    assert captured["args"] == ("fast", "srs_scene1")
