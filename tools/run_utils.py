"""runs协议: 实验产出的统一落盘约定 (可追溯/可复现/不覆盖).

规则:
  每次实验 → data/gjb_438c/runs/<脚本名>_<config哈希>_<时间戳>/
    config.json   = {script, git_sha, config, config_hash, opened_at}
    result.json   = save_result(obj)写入
    log.jsonl     = log(**event)逐行追加

与blackboard的 state.json/decision_log.jsonl 同一哲学的推广:
  复现 = 同config重跑; 审计 = config.json里的git_sha + 时间戳.

用法:
  from run_utils import open_run
  run = open_run("m16_scene_tier1", {"scene": "sc1"})
  run.save_result(results)
  run.log(pair_id="1_001", n_disc=5)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
RUNS_ROOT = BASE / "data/gjb_438c/runs"


def _git_sha() -> str:
    """当前代码版本(无法获取时'nogit'). 复现的第一要素: 知道跑的是哪版代码."""
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=BASE, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "nogit"
    except Exception:
        return "nogit"


class RunHandle:
    """一次实验运行的手柄: 落盘路径+配置+日志."""

    def __init__(self, path: Path, meta: dict[str, Any]) -> None:
        self.path = path
        self.meta = meta

    def save_result(self, obj: Any) -> Path:
        p = self.path / "result.json"
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str),
                     encoding="utf-8")
        return p

    def log(self, **event: Any) -> None:
        event.setdefault("ts", round(time.time(), 1))
        with open(self.path / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    def write_text(self, name: str, text: str) -> Path:
        p = self.path / name
        p.write_text(text, encoding="utf-8")
        return p


def open_run(script_name: str, config: dict[str, Any] | None = None,
             root: Path | None = None) -> RunHandle:
    """开启一次运行: 建目录 + 写config.json(含git sha与config哈希)."""
    config = config or {}
    canon = json.dumps(config, ensure_ascii=False, sort_keys=True)
    chash = hashlib.sha1(canon.encode("utf-8")).hexdigest()[:8]
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"{script_name}_{chash}_{stamp}"
    path = (root or RUNS_ROOT) / base_name
    n = 1
    while path.exists():                       # 同秒多次运行不覆盖
        path = (root or RUNS_ROOT) / f"{base_name}_{n}"
        n += 1
    path.mkdir(parents=True, exist_ok=True)
    meta = {
        "script": script_name,
        "git_sha": _git_sha(),
        "config": config,
        "config_hash": chash,
        "opened_at": round(time.time(), 1),
    }
    (path / "config.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return RunHandle(path, meta)
