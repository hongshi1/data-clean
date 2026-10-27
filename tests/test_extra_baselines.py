"""深行v2补充基线快照: HyDE/E5/单元格粒度.

结论(数字期2026-10):
  ① HyDE(经典零样本): HyDE-unit 0.181 < O1 0.329——假设文档在
     精确事实查询上幻觉具体值, 不敌真实查询向量
  ② E5(MTEB标准编码器): 域失效(dense 0.032), 但E5-unit 0.226
     ——单元分解对任意编码器一致提升(bge-zh 0.329/e5 0.226),
     机制跨编码器证据
  ③ 单元格粒度(0.052)失败——比行粒度细反而丢上下文,
     行=正确的结构粒度
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

EXTRA = BASE / "data/gjb_438c/data_assets/evalsets/deep_v2_extra_baselines.json"


@pytest.mark.skipif(not EXTRA.exists(), reason="未跑(补充基线)")
def test_extra_baselines_snapshot():
    d = json.loads(EXTRA.read_text(encoding="utf-8"))
    r = d["results"]
    # ① HyDE不敌O1
    assert r["HyDE-dense"]["R@1"] == pytest.approx(0.084, abs=1e-2)
    assert r["HyDE-unit"]["R@1"] == pytest.approx(0.181, abs=1e-2)
    assert r["HyDE-unit"]["R@1"] < r["O1-unit(对照)"]["R@1"]
    # ② E5域失效但单元分解救回(+19.4)
    assert r["E5-dense"]["R@1"] == pytest.approx(0.032, abs=1e-2)
    assert r["E5-unit"]["R@1"] == pytest.approx(0.226, abs=1e-2)
    assert r["E5-unit"]["R@1"] > r["E5-dense"]["R@1"] + 0.15
    # ③ 单元格粒度失败(比行细丢上下文)
    assert r["Cell-BM25"]["R@1"] == pytest.approx(0.052, abs=1e-2)
    assert r["Cell-BM25"]["R@1"] < r["O1-unit(对照)"]["R@1"] / 4
    # O1对照复现
    assert r["O1-unit(对照)"]["R@1"] == pytest.approx(0.329, abs=1e-2)
