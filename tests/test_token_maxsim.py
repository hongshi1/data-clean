"""token级MaxSim(ColBERT式)对照实验快照: 粒度-窗口权衡.

核心受控结论(同一BGE骨干):
  ① 短内容(表caption): token级0.807最优——窗口不构成约束时
     token粒度匹配面更大
  ② 长内容(深行): token级崩塌至0.212——继承512 token窗口
     (与dense同款截断盲区); 单元级0.703(结构分解移除窗口限制)
  ③ ROUTE4/5在全部场景≈最优——多通道路由吸收各粒度优势
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

EVAL_JSON = BASE / "data/gjb_438c/data_assets/evalsets/token_maxsim_eval.json"


@pytest.mark.skipif(not EVAL_JSON.exists(),
                    reason="未跑(先跑 tools/eval_token_maxsim.py)")
def test_granularity_window_tradeoff():
    d = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    r = d["results"]
    # ① 短内容: token级最优单通道(caption)
    cap = r["gjb_table_caption"]
    assert cap["Token-MaxSim"]["R@1"] == pytest.approx(0.807, abs=1e-3)
    assert cap["Token-MaxSim"]["R@1"] > cap["BM25-doc"]["R@1"]
    assert cap["Token-MaxSim"]["R@1"] > cap["O1-unit"]["R@1"]
    # ② 长内容: token级窗口崩塌(深行), 单元级存活
    deep = r["gjb_table_deep"]
    assert deep["Token-MaxSim"]["R@1"] == pytest.approx(0.212, abs=1e-2)
    assert deep["O1-unit"]["R@1"] == pytest.approx(0.703, abs=1e-2)
    assert deep["O1-unit"]["R@1"] > deep["Token-MaxSim"]["R@1"] + 0.4
    # ③ 路由: 全场景≈最优
    for scene in ("gjb_image", "gjb_table_deep", "gjb_table_caption",
                  "wtq", "fetaqa"):
        res = r[scene]
        assert "ROUTE5" in res
        # ROUTE5不低于最优单通道-0.5pt(R@1)——路由吸收各通道优势
        best_single = max(res[k]["R@1"] for k in
                          ("BM25-doc", "BM25-unit", "B1-dense",
                           "O1-unit", "Token-MaxSim"))
        assert res["ROUTE5"]["R@1"] >= best_single - 0.005, scene


@pytest.mark.skipif(not EVAL_JSON.exists(), reason="未跑")
def test_public_token_numbers():
    d = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["wtq"]["Token-MaxSim"]["R@1"] == pytest.approx(0.241, abs=1e-3)
    assert r["fetaqa"]["Token-MaxSim"]["R@1"] == pytest.approx(0.681, abs=1e-3)
    assert r["fetaqa"]["ROUTE5"]["R@1"] == pytest.approx(0.807, abs=1e-3)
    assert r["wtq"]["ROUTE5"]["R@1"] == pytest.approx(0.300, abs=1e-3)
