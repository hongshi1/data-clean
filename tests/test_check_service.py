"""check_service契约测试(新版接口契约: scene路由+三态样本+violations报告)."""
from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parents[1]

import server.main as server_main  # noqa: E402
from server.check_service import (  # noqa: E402
    DATASETS_DIR,
    KNOWLEDGE_DIR,
)

client = TestClient(server_main.app)

#: violations-17两条真实样本(violation_evalset_v1: VIO-02=TERM-07真实违例)
VIO_PAIRS = [
    {"sample_id": "DOC04-VIO-02",
     "question": "数据库关闭用例的项目唯一标识符是什么？",
     "answer": "数据库关闭能力的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。",
     "source": "04数据统一访问服务软件需求规格说明"},
    {"sample_id": "DOC04-VIO-06",
     "question": "SQL访问功能包括哪些子功能？",
     "answer": "SQL访问功能包括数据库操作、修改数据、查询数据、逐行获取数据、BLOB数据操作功能。",
     "source": "04数据统一访问"},
]


def _wait_done(check_id: str, timeout: float = 300.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/api/check-status/{check_id}")
        assert response.status_code == 200
        payload = response.json()
        if not payload["ok"]:
            return payload
        status = payload["data"]["status"]
        if status in ("done", "error"):
            return payload["data"]
        time.sleep(1.0)
    pytest.fail(f"check未完成: {check_id}")


def test_start_check_contract() -> None:
    response = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] in ("queued", "running")
    assert data["check_id"].startswith("chk-")
    assert "version" in data["rules_snapshot"]
    assert isinstance(data["rules_snapshot"]["n_rules"], int)
    assert data["rules_snapshot"]["n_rules"] >= 1
    _wait_done(data["check_id"])


def test_check_report_contract() -> None:
    start = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS}).json()["data"]
    final = _wait_done(start["check_id"])
    assert final["status"] == "done"
    report = client.get(
        f"/api/check-reports/{start['check_id']}").json()["data"]["report"]
    assert report["check_id"] == start["check_id"]
    assert report["rules_snapshot"]["version"] == \
        start["rules_snapshot"]["version"]
    assert "run_at" in report
    summary = report["summary"]
    assert summary["total"] == 2
    assert summary["inconsistent"] >= 1  # VIO-02是注入违例
    assert summary["consistent"] + summary["inconsistent"] \
        + summary["undetermined"] == summary["total"]
    for legacy in ("pass", "warn", "fail"):
        assert legacy not in summary
    sample = next(s for s in report["samples"]
                  if s["sample_id"] == "DOC04-VIO-02")
    # 三态样本契约: consistency_result三值+violations, 无旧status/issues/error
    assert sample["consistency_result"] == "inconsistent"
    assert sample["question"] == VIO_PAIRS[0]["question"]
    assert sample["answer"] == VIO_PAIRS[0]["answer"]
    assert sample["source"] == VIO_PAIRS[0]["source"]
    assert "status" not in sample
    assert "issues" not in sample
    assert "error" not in sample
    violations = sample["violations"]
    assert violations
    for v in violations:
        assert set(v) >= {"item_id", "item_name", "description",
                          "affected_answer"}
        assert v["description"]
        assert v["affected_answer"]
    term07 = next(v for v in violations if v["item_id"] == "TERM-07")
    assert term07["item_name"] == "信号、接口命名一致性校验"
    assert "PZXQ" in term07["affected_answer"]


def test_status_running_progress_and_done_summary(monkeypatch) -> None:
    import server.check_service as cs

    def fake_execute(check_id: str, scene: str,
                     qa_pairs: list) -> None:
        task = cs._TASKS[check_id]
        task["status"] = "running"
        task["progress"] = {"total": len(qa_pairs), "completed": 1}
        cs._persist(check_id)
        time.sleep(1.0)
        task["progress"] = {"total": len(qa_pairs), "completed": 2}
        task["report"] = {
            "check_id": check_id, "run_at": "t",
            "rules_snapshot": task["snapshot"],
            "summary": {"total": len(qa_pairs), "consistent": 2,
                        "inconsistent": 0, "undetermined": 0},
            "samples": [],
        }
        task["status"] = "done"
        cs._persist(check_id)

    monkeypatch.setattr(cs, "execute_check", fake_execute)
    start = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS}).json()["data"]
    deadline = time.time() + 10.0
    running = None
    while time.time() < deadline:
        running = client.get(
            f"/api/check-status/{start['check_id']}").json()["data"]
        if running["status"] == "running":
            break
        time.sleep(0.1)
    assert running is not None and running["status"] == "running"
    assert running["check_id"] == start["check_id"]
    assert running["progress"] == {"total": 2, "completed": 1}
    final = _wait_done(start["check_id"])
    assert final["summary"] == {"total": 2, "consistent": 2,
                                "inconsistent": 0, "undetermined": 0}


def test_error_semantics() -> None:
    # 404: scene未接入(scene2合法枚举但未接入)
    response = client.post("/api/check", json={
        "scene": "scene2", "qa_pairs": VIO_PAIRS})
    assert response.status_code == 404
    # 400: qa_pairs为空
    response = client.post("/api/check", json={"scene": "scene1",
                                               "qa_pairs": []})
    assert response.status_code == 400
    # 400: source缺失(字符串契约)
    response = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": [
            {"sample_id": "x", "question": "q", "answer": "a", "source": ""}]})
    assert response.status_code == 400
    # 404: check_id不存在
    assert client.get("/api/check-status/chk-nope").status_code == 404
    assert client.get("/api/check-reports/chk-nope").status_code == 404


def test_doc_unresolvable_is_undetermined_not_error() -> None:
    # doc解析失败→该样本undetermined+诊断说明, 不触发任务error(异常≠数据有问题)
    pairs = [{"sample_id": "bad-doc", "question": "q", "answer": "a",
              "source": "不存在的文档xx"}]
    start = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": pairs}).json()["data"]
    final = _wait_done(start["check_id"])
    assert final["status"] == "done"
    report = client.get(
        f"/api/check-reports/{start['check_id']}").json()["data"]["report"]
    sample = report["samples"][0]
    assert sample["consistency_result"] == "undetermined"
    assert sample["violations"] == []
    assert sample["diagnostics"]
    assert report["summary"] == {"total": 1, "consistent": 0,
                                 "inconsistent": 0, "undetermined": 1}


def test_timeout_error_code(monkeypatch) -> None:
    import server.check_service as cs

    release = threading.Event()

    def stuck_engine() -> dict:
        release.wait(timeout=30.0)
        return {}

    monkeypatch.setattr(cs, "CHECK_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(cs, "get_engine", stuck_engine)
    start = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": [
            {"sample_id": "stuck", "question": "q", "answer": "a",
             "source": "04数据统一访问"}]}).json()["data"]
    deadline = time.time() + 15.0
    payload = None
    while time.time() < deadline:
        payload = client.get(
            f"/api/check-status/{start['check_id']}").json()
        if not payload.get("ok"):
            break
        time.sleep(0.2)
    assert payload == {"ok": False,
                       "error": {"code": "ENGINE_TIMEOUT",
                                 "message": "校验引擎执行超时"}}
    # 报告接口同样透出任务级error信封
    report = client.get(f"/api/check-reports/{start['check_id']}")
    assert report.json() == payload
    release.set()


def test_expert_knowledge_sync_and_scene_guard() -> None:
    # scene不一致 → 400
    response = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": {"scene": "scene2"}})
    assert response.status_code == 400
    # 提交期校验: 非法rulepack → 400, 不落库
    response = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": {"scene": "scene1",
                             "rulepack": {"rules": []}}})
    assert response.status_code == 400
    assert not (KNOWLEDGE_DIR / "scene1" / "rulepack.json").exists() or \
        _cleanup_knowledge()
    # 幂等同步: 提交两次合法知识, 不报错, 版本更新
    builtin = json.loads(
        (BASE / "config/rulepacks/srs_gjb_v1.json")
        .read_text(encoding="utf-8"))
    builtin["pack_id"] = "synced_test_pack"
    knowledge = {"scene": "scene1", "rulepack": builtin}
    first = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": knowledge}).json()["data"]
    second = client.post("/api/check", json={
        "scene": "scene1", "qa_pairs": VIO_PAIRS,
        "expert_knowledge": knowledge}).json()["data"]
    assert (KNOWLEDGE_DIR / "scene1" / "rulepack.json").exists()
    _wait_done(second["check_id"])
    _wait_done(first["check_id"])
    # 快照绑定: 第一个check的快照版本在发起时捕获
    assert first["rules_snapshot"]["version"].startswith("rules-")
    _cleanup_knowledge()


def _cleanup_knowledge() -> bool:
    if (KNOWLEDGE_DIR / "scene1").exists():
        shutil.rmtree(KNOWLEDGE_DIR / "scene1")
    return True


def test_dataset_level_check() -> None:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    (DATASETS_DIR / "ds_test.json").write_text(
        json.dumps({"scene": "scene1", "qa_pairs": VIO_PAIRS},
                   ensure_ascii=False), encoding="utf-8")
    start = client.post("/api/datasets/ds_test/check").json()["data"]
    assert start["check_id"].startswith("chk-")
    assert "rules_snapshot" in start
    _wait_done(start["check_id"])
    status = client.get("/api/datasets/ds_test/check-status").json()["data"]
    assert status["status"] == "done"
    assert status["summary"]["total"] == 2
    assert status["summary"]["inconsistent"] >= 1
    report = client.get(
        f"/api/check-reports/{start['check_id']}").json()["data"]["report"]
    assert report["summary"]["total"] == 2
    assert client.get("/api/datasets/nope/check-status").status_code == 404
    assert client.post("/api/datasets/nope/check").status_code == 404
