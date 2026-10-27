"""runs协议单元测试: config哈希/git sha/落盘/日志."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))
from run_utils import RunHandle, open_run  # noqa: E402


def test_open_run_creates_config(tmp_path: Path):
    run = open_run("test_script", {"scene": "sc1", "limit": 5}, root=tmp_path)
    assert run.path.exists()
    cfg = json.loads((run.path / "config.json").read_text(encoding="utf-8"))
    assert cfg["script"] == "test_script"
    assert cfg["config"] == {"scene": "sc1", "limit": 5}
    assert len(cfg["config_hash"]) == 8
    assert cfg["git_sha"]  # nogit也算有值


def test_same_config_same_hash_different_dirs(tmp_path: Path):
    r1 = open_run("s", {"a": 1}, root=tmp_path)
    r2 = open_run("s", {"a": 1}, root=tmp_path)
    assert r1.path != r2.path            # 时间戳区分, 不覆盖
    h1 = json.loads((r1.path / "config.json").read_text(encoding="utf-8"))["config_hash"]
    h2 = json.loads((r2.path / "config.json").read_text(encoding="utf-8"))["config_hash"]
    assert h1 == h2                      # 同config同哈希(可复现性)


def test_result_and_log(tmp_path: Path):
    run = open_run("s", {}, root=tmp_path)
    p = run.save_result({"n": 42, "中文": "值"})
    assert p.exists()
    assert json.loads(p.read_text(encoding="utf-8"))["n"] == 42
    run.log(pair_id="1_001", n_disc=5)
    run.log(pair_id="2_001", n_disc=4)
    lines = (run.path / "log.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["pair_id"] == "1_001" and "ts" in rec


def test_handle_is_dataclass_like(tmp_path: Path):
    run = open_run("s", None, root=tmp_path)
    assert isinstance(run, RunHandle)
    assert run.meta["config"] == {}
