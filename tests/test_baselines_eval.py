"""对比基线评测快照: BM25(文档/单元级)+dense+单元+多通道路由.

锁定声明(数字期2026-10):
  ① BM25-doc是被忽略的强基线(GJB image 0.654 > O1语义单元0.619)
  ② 深行: O1单元R@1最优(0.748, 语义消歧), BM25-unit R@5最优(0.949, 词面并列)
  ③ ROUTE4(四通道max-z路由)在4/5场景×数据集组合最优(FeTaQA反超最强单通道)
  ④ FeTaQA RowHit@1(段偏移修复后): O1 0.691 vs BM25-unit 0.782
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

BASE_JSON = BASE / "data/gjb_438c/data_assets/evalsets/baselines_eval.json"
FETAQA = BASE / "data/gjb_438c/data_assets/evalsets/fetaqa_ure.json"


@pytest.mark.skipif(not BASE_JSON.exists(), reason="未跑(先跑 tools/eval_baselines.py)")
def test_gjb_baselines_snapshot():
    d = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    g = d["gjb"]
    # ① BM25-doc强基线: image上超过O1语义单元(0.619锁定)
    assert g["image|BM25-doc"]["R@1"] == pytest.approx(0.654, abs=1e-3)
    # ② 深行: dense崩塌(截断盲区在该协议下复现), BM25-unit R@5最强
    assert g["table_deep|B1-dense"]["R@5"] == pytest.approx(0.441, abs=1e-2)
    assert g["table_deep|BM25-unit"]["R@5"] == pytest.approx(0.949, abs=1e-3)
    assert g["table_deep|ROUTE4"]["R@5"] == pytest.approx(0.949, abs=1e-3)
    assert g["table_deep|ROUTE4"]["R@1"] == pytest.approx(0.729, abs=1e-3)
    # ③ caption: ROUTE4最优
    assert g["table_caption|ROUTE4"]["R@1"] == pytest.approx(0.808, abs=1e-3)
    # image: ROUTE3 R@1最优 / ROUTE4 R@5最优
    assert g["image|ROUTE3"]["R@1"] == pytest.approx(0.657, abs=1e-3)
    assert g["image|ROUTE4"]["R@5"] == pytest.approx(0.861, abs=1e-3)


@pytest.mark.skipif(not BASE_JSON.exists(), reason="未跑")
def test_public_baselines_snapshot():
    d = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    w = d["wtq"]
    # WTQ: ROUTE4最优(英文词面BM25为主力, 路由增益)
    assert w["BM25-doc"]["R@1"] == pytest.approx(0.281, abs=1e-3)
    assert w["ROUTE4"]["R@1"] == pytest.approx(0.297, abs=1e-3)
    assert w["ROUTE4"]["MRR@10"] == pytest.approx(0.364, abs=1e-3)
    f = d["fetaqa"]
    # FeTaQA: ROUTE4反超最强单通道BM25-unit
    assert f["BM25-unit"]["R@1"] == pytest.approx(0.788, abs=1e-3)
    assert f["ROUTE4"]["R@1"] == pytest.approx(0.802, abs=1e-3)
    assert f["ROUTE4"]["MRR@10"] == pytest.approx(0.853, abs=1e-3)
    # RowHit@1(单元级命中精度)
    assert f["O1-unit"]["RowHit@1"] == pytest.approx(0.691, abs=1e-3)
    assert f["BM25-unit"]["RowHit@1"] == pytest.approx(0.782, abs=1e-3)


@pytest.mark.skipif(not FETAQA.exists(), reason="未转换(先跑convert_public_dataset.py)")
def test_fetaqa_ure_snapshot():
    ds = json.loads(FETAQA.read_text(encoding="utf-8"))
    assert ds["meta"]["name"] == "FeTaQA-URE"
    assert len(ds["corpus"]) == 2003
    assert len(ds["queries"]) == 2003
    ids = {c["chunk_id"] for c in ds["corpus"]}
    assert all(q["expected"][0] in ids for q in ds["queries"][:200])
    # 行级gold存在(供RowHit评测)
    n_gold = sum(1 for q in ds["queries"] if q.get("gold_rows"))
    assert n_gold > 1800
    assert all(q["fold"] in (0, 1, 2, 3) for q in ds["queries"])
