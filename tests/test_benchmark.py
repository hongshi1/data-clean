"""统一Benchmark测试: 构建质量与schema完整性(确定性)."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
BENCH = BASE / "data/gjb_438c/benchmark.jsonl"
STATS = BASE / "data/gjb_438c/benchmark_stats.json"

pytestmark = pytest.mark.skipif(not BENCH.exists(), reason="benchmark未构建")

REQUIRED_FIELDS = {"id", "premise", "hypothesis", "label", "check_item",
                   "channel", "tier", "source_asset", "split"}
VALID_LABELS = {"consistent", "inconsistent"}
VALID_TIERS = {"L1_constructed", "L3_silver", "L4_positive"}


def _items() -> list[dict]:
    return [json.loads(line) for line in
            BENCH.read_text(encoding="utf-8").strip().splitlines()]


def test_schema_complete():
    for it in _items():
        assert REQUIRED_FIELDS <= set(it), f"{it['id']}缺字段"


def test_label_valid():
    for it in _items():
        assert it["label"] in VALID_LABELS, f"{it['id']}非法label: {it['label']}"


def test_tier_valid():
    for it in _items():
        assert it["tier"] in VALID_TIERS, f"{it['id']}非法tier: {it['tier']}"


def test_no_duplicate():
    keys = [(it["premise"] + "|" + it["hypothesis"]) for it in _items()]
    assert len(keys) == len(set(keys)), "存在重复声明对"


def test_positive_identity_count_consistent():
    """恒等正例质量门: P和H的计数必须匹配(防伪正例)."""
    bad = 0
    for it in _items():
        if it["check_item"] != "P0_IDENTITY":
            continue
        pm = re.search(r'共(\d+)项', it["premise"])
        hm = re.search(r'共(\d+)个', it["hypothesis"])
        if pm and hm and pm.group(1) != hm.group(1):
            bad += 1
    assert bad == 0, f"{bad}条P0_IDENTITY计数不匹配(伪正例)"


def test_stats_snapshot():
    """快照: 总量与分布(防重生成漂移)."""
    s = json.loads(STATS.read_text(encoding="utf-8"))
    assert s["total"] == 1303
    assert s["label"]["inconsistent"] == 1026
    assert s["label"]["consistent"] == 277
    assert s["tier"]["L1_constructed"] == 657
    assert s["tier"]["L3_silver"] == 498
    assert s["tier"]["L4_positive"] == 148
    assert s["dedup_removed"] == 1032
