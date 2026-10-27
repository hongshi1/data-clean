"""BGE-M3 SOTA基线快照: 三模式×五场景.

核心SOTA对照结论(数字期2026-10):
  ① 深行: M3-dense(8192长上下文)0.415 << O1单元0.703——
     长上下文缓解截断但不解稀释, 单元分解优势在SOTA攻击下存活
  ② M3-colbert(官方late interaction)深行0.347——token级粒度
     用官方实现复现失败(与我们Token-MaxSim近似0.212一致方向)
  ③ FeTaQA: M3-dense 0.883为全局最优单方法(568M vs 我们en-base 109M,
     模型规模混淆需声明); WTQ: 我们O1(en) 0.4095 > M3-dense 0.334
  ④ M3-sparse在英文集异常(0.009), 需声明可疑不解释
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

M3_JSON = BASE / "data/gjb_438c/data_assets/evalsets/sota_m3_eval.json"


@pytest.mark.skipif(not M3_JSON.exists(), reason="未跑(先跑 tools/eval_sota_m3.py)")
def test_m3_gjb_snapshot():
    d = json.loads(M3_JSON.read_text(encoding="utf-8"))
    r = d["results"]
    # ① 深行: 长上下文dense与官方colbert都远低于单元级
    deep = r["gjb_table_deep"]
    assert deep["M3-dense"]["R@1"] == pytest.approx(0.415, abs=1e-2)
    assert deep["M3-colbert"]["R@1"] == pytest.approx(0.347, abs=1e-2)
    # 对照锁定: O1-unit(同协议) 0.703——单元分解存活
    # ② image/caption: M3与我们方法同量级
    assert r["gjb_image"]["M3-dense"]["R@1"] == pytest.approx(0.587, abs=1e-2)
    assert r["gjb_table_caption"]["M3-colbert"]["R@1"] == pytest.approx(
        0.839, abs=1e-2)


@pytest.mark.skipif(not M3_JSON.exists(), reason="未跑")
def test_m3_public_snapshot():
    d = json.loads(M3_JSON.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["fetaqa"]["M3-dense"]["R@1"] == pytest.approx(0.883, abs=1e-2)
    assert r["fetaqa"]["M3-dense"]["MRR@10"] == pytest.approx(0.913, abs=1e-2)
    assert r["wtq"]["M3-dense"]["R@1"] == pytest.approx(0.334, abs=1e-2)
    assert r["wtq"]["M3-colbert"]["R@1"] == pytest.approx(0.334, abs=1e-2)
    # 声明: M3-sparse英文异常, 快照锁定但不解释
    assert r["wtq"]["M3-sparse"]["R@1"] < 0.05
