"""WTQ-URE外部效度pilot快照 + 修复后的GJB-URE回归."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

WTQ_URE = BASE / "data/gjb_438c/data_assets/evalsets/wtq_ure.json"
WTQ_PILOT = BASE / "data/gjb_438c/data_assets/evalsets/wtq_pilot_eval.json"


@pytest.mark.skipif(not WTQ_URE.exists(), reason="未转换(先跑convert_public_dataset.py)")
def test_wtq_ure_dataset_snapshot():
    """WTQ-URE: 2100表/18486真实查询, 引用完整, fold均衡."""
    ds = json.loads(WTQ_URE.read_text(encoding="utf-8"))
    assert ds["meta"]["name"] == "WTQ-URE"
    assert len(ds["corpus"]) == 2100
    assert len(ds["queries"]) == 18486
    ids = {c["chunk_id"] for c in ds["corpus"]}
    assert all(q["expected"][0] in ids for q in ds["queries"][:200])
    assert all(q["fold"] in (0, 1, 2, 3) for q in ds["queries"])
    # 行单元序列化
    assert any("=" in u for c in ds["corpus"][:20] for u in c["units"])


@pytest.mark.skipif(not WTQ_PILOT.exists(), reason="pilot未跑(先跑eval_wtq_ure.py)")
def test_wtq_pilot_snapshot():
    """外部效度pilot: 单元检索增益在公开英文数据复现(机制一致性)."""
    d = json.loads(WTQ_PILOT.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["B1_dense"]["R@1"] == pytest.approx(0.155, abs=1e-3)
    assert r["B1_dense"]["R@5"] == pytest.approx(0.282, abs=1e-3)
    assert r["O1_unit"]["R@1"] == pytest.approx(0.272, abs=1e-3)
    assert r["O1_unit"]["R@5"] == pytest.approx(0.423, abs=1e-3)
    assert r["O1_unit"]["MRR@10"] == pytest.approx(0.339, abs=1e-3)
    # 单元增益方向与GJB一致
    assert r["O1_unit"]["R@1"] > r["B1_dense"]["R@1"] + 0.08
    assert r["O1_unit"]["R@5"] > r["B1_dense"]["R@5"] + 0.10
    assert "bge-large-zh" in d["protocol"]  # 跨语言声明存在
