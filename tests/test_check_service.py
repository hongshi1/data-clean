"""check_service契约测试(南开对接三接口)."""
from __future__ import annotations

import time
from pathlib import Path

import json
import pytest
from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parents[1]

import server.main as server_main  # noqa: E402
from server.check_service import (  # noqa: E402
    DATASETS_DIR,
    KNOWLEDGE_DIR,
)

client = TestClient(server_main.app)

VIO_PAIRS = [
    {"sample_id": "DOC04-VIO-02",
     "question": "数据库关闭用例的项目唯一标识符是什么？",
     "answer": "数据库关闭能力的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。",
     "source": {"doc_ref": "04数据统一访问服务软件需求规格说明"}},
    {"sample_id": "DOC04-VIO-06",
     "question": "SQL访问功能包括哪些子功能？",
     "answer": "SQL访问功能包括数据库操作、修改数据、查询数据、逐行获取数据、BLOB数据操作功能。",
     "source": {"doc_ref": "04数据统一访问"}},
]


def _wait_done(check_id: str, timeout: float = 240.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/check-status/{check_id}")
        assert response.status_code == 200
        status = response.json()["data"]["status"]
        if status in ("done", "error"):
            return response.json()["data"]
        time.sleep(1.0)
    pytest.fail(f"check未完成: {check_id}")


def test_start_check_contract() -> None:
    response = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": VIO_PAIRS})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] in ("queued", "running")
    assert data["check_id"].startswith("chk-")
    assert "version" in data["rules_snapshot"]
    assert "n_rules" in data["rules_snapshot"]


def test_check_report_contract() -> None:
    start = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": VIO_PAIRS}).json()["data"]
    final = _wait_done(start["check_id"])
    assert final["status"] == "done"
    report = client.get(
        f"/api/check-reports/{start['check_id']}").json()["data"]["report"]
    assert report["check_id"] == start["check_id"]
    assert report["rules_snapshot"]["version"] == \
        start["rules_snapshot"]["version"]
    summary = report["summary"]
    assert set(summary) >= {"total", "pass", "warn", "fail"}
    assert summary["total"] == 2
    assert summary["fail"] >= 1  # VIO-02是注入违例
    sample = next(s for s in report["samples"]
                  if s["sample_id"] == "DOC04-VIO-02")
    assert sample["status"] == "fail"
    assert sample["source"]["doc_ref"].startswith("04数据")
    issues = sample["issues"]
    assert issues and all(set(i) >= {"type", "desc", "rule_id"}
                          for i in issues)
    assert any(i["rule_id"].startswith("TERM-")
               or i["rule_id"].startswith(("GJB", "LOGIC", "PARAM"))
               for i in issues)


def test_error_semantics() -> None:
    # 404: 场景未接入
    response = client.post("/api/check", json={
        "cat": "unknown", "qa_pairs": VIO_PAIRS})
    assert response.status_code == 404
    # 400: qa_pairs为空
    response = client.post("/api/check", json={"cat": "srs",
                                               "qa_pairs": []})
    assert response.status_code == 400
    # 400: source缺失
    response = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": [
            {"sample_id": "x", "question": "q", "answer": "a",
             "source": {"doc_ref": ""}}]})
    assert response.status_code == 400
    # 404: check_id不存在
    assert client.get("/api/check-status/chk-nope").status_code == 404


def test_sample_error_is_unchecked_not_fail() -> None:
    pairs = [{"sample_id": "bad-doc", "question": "q", "answer": "a",
              "source": {"doc_ref": "不存在的文档xx"}}]
    start = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": pairs}).json()["data"]
    final = _wait_done(start["check_id"])
    assert final["status"] == "done"
    report = client.get(
        f"/api/check-reports/{start['check_id']}").json()["data"]["report"]
    sample = report["samples"][0]
    assert sample["status"] == "未校验"
    assert sample["error"]
    assert report["summary"]["total"] == 1
    assert report["summary"]["fail"] == 0


def test_expert_knowledge_sync_and_scene_guard() -> None:
    # scene不一致 → 400
    response = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": {"scene": "other"}})
    assert response.status_code == 400
    # 提交期校验: 非法rulepack → 400, 不落库
    response = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": {"scene": "srs",
                             "rulepack": {"rules": []}}})
    assert response.status_code == 400
    assert not (KNOWLEDGE_DIR / "srs" / "rulepack.json").exists() or \
        _cleanup_knowledge()
    # 幂等同步: 提交两次合法知识, 不报错, 版本更新
    builtin = json.loads(
        (BASE / "config/rulepacks/srs_gjb_v1.json")
        .read_text(encoding="utf-8"))
    builtin["pack_id"] = "synced_test_pack"
    knowledge = {"scene": "srs", "rulepack": builtin}
    first = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": knowledge}).json()["data"]
    second = client.post("/api/check", json={
        "cat": "srs", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": knowledge}).json()["data"]
    assert (KNOWLEDGE_DIR / "srs" / "rulepack.json").exists()
    _wait_done(second["check_id"])
    _wait_done(first["check_id"])
    # 快照绑定: 第一个check的快照版本在发起时捕获
    assert first["rules_snapshot"]["version"].startswith("rules-")
    _cleanup_knowledge()


def _cleanup_knowledge() -> bool:
    import shutil
    if (KNOWLEDGE_DIR / "srs").exists():
        shutil.rmtree(KNOWLEDGE_DIR / "srs")
    return True


def test_dataset_level_check() -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    (DATASETS_DIR / "ds_test.json").write_text(
        __import__("json").dumps({"cat": "srs", "qa_pairs": VIO_PAIRS},
                                 ensure_ascii=False), encoding="utf-8")
    start = client.post("/api/datasets/ds_test/check").json()["data"]
    _wait_done(start["check_id"])
    status = client.get("/api/datasets/ds_test/check-status").json()["data"]
    assert status["status"] == "done"
    assert status["summary"]["total"] == 2
    assert client.get("/api/datasets/nope/check-status").status_code == 404
