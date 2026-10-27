"""单元通道集成测试: 六通道可插拔+降级+增益快照."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.blackboard.hybrid_recall import CHANNELS, HybridRecaller  # noqa: E402

ABLATION = BASE / "data/gjb_438c/data_assets/evalsets/unit_channel_ablation.json"


def test_unit_channel_registered():
    """unit通道入CHANNELS表(鸭子调度自动生效)."""
    assert "unit" in CHANNELS
    assert len(CHANNELS) == 6


def test_unit_channel_degradation():
    """use_unit=False: 通道unavailable, 其余通道正常(recall仍可用)."""
    rec = HybridRecaller(use_dense=False, use_unit=False)
    r = rec.recall("接口", top_k=5, fusion="cascade")
    assert r["per_channel"]["unit"]["mode"] == "unavailable"
    assert isinstance(r["hits"], list)


def test_weights_cover_unit():
    from algorithms.blackboard.fusion import CALIBRATED_WEIGHTS
    assert set(CALIBRATED_WEIGHTS) == set(CHANNELS)
    assert CALIBRATED_WEIGHTS["unit"] == 0.85


@pytest.mark.skipif(not ABLATION.exists(),
                    reason="未跑(先跑 tools/eval_unit_channel.py)")
def test_unit_channel_gain_snapshot():
    """集成增益快照: 六通道R@10比五通道+5.9pts(生产管线收益锁定)."""
    d = json.loads(ABLATION.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["five_channel"]["Recall@10"] == pytest.approx(0.455, abs=1e-3)
    assert r["six_channel"]["Recall@10"] == pytest.approx(0.5139, abs=1e-3)
    assert r["six_channel"]["Recall@20"] == pytest.approx(0.6865, abs=1e-3)
    gain = r["six_channel"]["Recall@10"] - r["five_channel"]["Recall@10"]
    assert gain > 0.04
    # 单通道unit: 深而窄(MRR最高, 召回低于融合)
    assert r["unit_only"]["MRR@10"] > r["six_channel"]["MRR@10"]
    assert r["unit_only"]["Recall@10"] < r["six_channel"]["Recall@10"]
