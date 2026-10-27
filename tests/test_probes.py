"""P0冻结探针集快照回归: schema/配比/冻结声明/确定性(重建与冻结文件逐条一致)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
PROBE_DIR = BASE / "data/gjb_438c/probes"
BASELINE = BASE / "data/gjb_438c/runs/probe_baseline.json"

pytestmark = pytest.mark.skipif(
    not PROBE_DIR.exists(), reason="探针未构建(先跑 python tools/build_probes.py)")

EXPECTED = {
    "paws_shortcut_probe.json": ("paws_shortcut", {"consistent": 100, "inconsistent": 100}),
    "feverous_table_probe.json": ("feverous_table", {"consistent": 100, "inconsistent": 100}),
    "ocnli_contradiction_probe.json": ("ocnli_contradiction", {"inconsistent": 200}),
}


def _load(fname: str) -> dict:
    return json.loads((PROBE_DIR / fname).read_text(encoding="utf-8"))


def test_schema_and_balance():
    for fname, (ptype, dist) in EXPECTED.items():
        doc = _load(fname)
        items = doc["items"]
        assert doc["meta"]["probe_type"] == ptype
        assert doc["meta"]["frozen"] is True
        assert doc["meta"]["freeze_declaration"]
        assert doc["meta"]["n_items"] == len(items)
        got: dict[str, int] = {}
        for it in items:
            assert set(it) == {"id", "premise", "hypothesis", "label", "probe_type"}
            assert it["probe_type"] == ptype
            assert it["label"] in ("consistent", "inconsistent")
            assert it["premise"] and it["hypothesis"]
            got[it["label"]] = got.get(it["label"], 0) + 1
        assert got == dist


def test_rebuild_is_deterministic():
    sys.path.insert(0, str(BASE / "tools"))
    from build_probes import build_feverous, build_ocnli, build_paws

    rebuilds = {"paws_shortcut_probe.json": build_paws,
                "feverous_table_probe.json": build_feverous,
                "ocnli_contradiction_probe.json": build_ocnli}
    for fname, fn in rebuilds.items():
        frozen = _load(fname)["items"]
        assert fn() == frozen, (
            f"{fname}重建结果与冻结文件不一致(选样逻辑变动须显式重建+同步快照)")


def test_baseline_result_structure():
    if not BASELINE.exists():
        pytest.skip("probe_baseline未生成(先跑 python tools/probe_eval.py)")
    doc = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert set(doc["probes"]) == {"paws_shortcut", "feverous_table", "ocnli_contradiction"}
    for name, p in doc["probes"].items():
        m = p["metrics"]
        assert m["n"] == 200 and m["tp"] + m["fn"] + m["tn"] + m["fp"] == 200
        assert p["shortcut_score"]["value"] is not None
        assert len(p["rows"]) == 200
