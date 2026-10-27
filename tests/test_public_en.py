"""英文编码器公开集评测快照(外部效度修复后的诚实数字)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

EN_JSON = BASE / "data/gjb_438c/data_assets/evalsets/public_en_eval.json"


@pytest.mark.skipif(not EN_JSON.exists(), reason="未跑(先跑 tools/eval_public_en.py)")
def test_en_wtq_snapshot():
    """WTQ(en): O1-unit反超BM25——增益非语言错配伪影."""
    d = json.loads(EN_JSON.read_text(encoding="utf-8"))
    w = d["results"]["wtq"]
    assert w["B1-dense"]["R@1"] == pytest.approx(0.3325, abs=1e-3)
    assert w["O1-unit"]["R@1"] == pytest.approx(0.4095, abs=1e-3)
    assert w["O1-unit"]["R@5"] == pytest.approx(0.5875, abs=1e-3)
    assert w["O1-unit"]["MRR@10"] == pytest.approx(0.4877, abs=1e-3)
    assert w["O1-unit"]["R@1"] > w["BM25-doc"]["R@1"] + 0.10
    # ROUTE增益不外推: en下纯O1>ROUTE4
    assert w["O1-unit"]["R@1"] > w["ROUTE4"]["R@1"]


@pytest.mark.skipif(not EN_JSON.exists(), reason="未跑")
def test_en_fetaqa_snapshot():
    """FeTaQA(en): O1最优; RowHit(段偏移修复后)≈BM25-unit."""
    d = json.loads(EN_JSON.read_text(encoding="utf-8"))
    f = d["results"]["fetaqa"]
    assert f["O1-unit"]["R@1"] == pytest.approx(0.856, abs=1e-3)
    assert f["O1-unit"]["MRR@10"] == pytest.approx(0.891, abs=1e-3)
    assert f["O1-unit"]["R@1"] > f["BM25-unit"]["R@1"] + 0.05
    assert f["O1-unit"]["RowHit@1"] == pytest.approx(0.774, abs=1e-3)
    assert f["BM25-unit"]["RowHit@1"] == pytest.approx(0.782, abs=1e-3)
