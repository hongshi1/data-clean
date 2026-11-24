"""数据资产MANIFEST验证: 金标数据被悄悄重生成时报警."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

MANIFEST = BASE / "data/gjb_438c/MANIFEST.json"

pytestmark = pytest.mark.skipif(
    not MANIFEST.exists() or not (BASE / "data/gjb_438c/anchor_v2").exists(),
    reason="MANIFEST未构建(先跑 python tools/build_data_manifest.py)")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_assets_intact():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    for rel, rec in manifest["assets"].items():
        p = BASE / "data/gjb_438c" / rel
        if not p.exists():
            problems.append(f"缺失: {rel}")
            continue
        digest = _sha256(p)
        if digest != rec["sha256"]:
            problems.append(f"内容变动: {rel}")
    assert not problems, (
        "金标资产与MANIFEST不一致(有意重生成请重跑 tools/build_data_manifest.py "
        f"并同步快照测试): {problems}")


def test_pair_dataset_structure():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pd = BASE / "data/gjb_438c/pair_dataset"
    h = hashlib.sha256()
    n = 0
    for scene_dir in sorted(pd.iterdir()):
        if scene_dir.is_dir():
            for pair_dir in sorted(scene_dir.iterdir()):
                meta_p = pair_dir / "meta.json"
                if meta_p.exists():
                    n += 1
                    h.update(meta_p.read_bytes())
    got = {"n_pairs": n, "meta_sha256": h.hexdigest()}
    assert got["n_pairs"] == manifest["pair_dataset"]["n_pairs"]
    assert got["meta_sha256"] == manifest["pair_dataset"]["meta_sha256"]


def test_root_assets_intact():
    """仓库根规则资产(E7 claim_channels外置JSON等)与MANIFEST一致.

    键为仓库根相对路径(区别于data/gjb_438c相对的assets).
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    for rel, rec in manifest.get("root_assets", {}).items():
        p = BASE / rel
        if not p.exists():
            problems.append(f"缺失: {rel}")
            continue
        digest = _sha256(p)
        if digest != rec["sha256"]:
            problems.append(f"内容变动: {rel}")
    assert not problems, (
        "仓库根规则资产与MANIFEST不一致(有意修改请重跑 "
        f"tools/build_data_manifest.py 并同步快照测试): {problems}")
