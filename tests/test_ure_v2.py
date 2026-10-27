"""GJB-URE-v2与深行v2决定性实验快照."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

URE_V2 = BASE / "data/gjb_438c/data_assets/evalsets/gjb_ure_v2.json"
DEEP_V2_EVAL = BASE / "data/gjb_438c/data_assets/evalsets/deep_v2_eval.json"
DEEP_V2_Q = BASE / "data/gjb_438c/data_assets/evalsets/deep_row_queries_v2.json"


@pytest.mark.skipif(not URE_V2.exists(), reason="未构建(先跑 tools/build_ure_dataset.py)")
class TestUreV2:
    def test_snapshot(self):
        ds = json.loads(URE_V2.read_text(encoding="utf-8"))
        assert ds["meta"]["name"] == "GJB-URE-v2"
        assert ds["meta"]["version"] == "2.0"
        eval_q = [q for q in ds["queries"] if q["split"] == "eval"]
        scenes = Counter(q["scene"] for q in eval_q)
        assert scenes == {"image": 1007, "table_deep": 118,
                          "table_deep_v2": 262}
        # overlap标注: 全部eval查询携带泄漏协变量
        assert all("overlap" in q for q in eval_q)
        # v2深行查询反拷贝: overlap显著低于v1
        v1 = [q["overlap"] for q in eval_q if q["scene"] == "table_deep"]
        v2 = [q["overlap"] for q in eval_q if q["scene"] == "table_deep_v2"]
        assert np.mean(v2) < 0.15
        assert np.mean(v1) > 0.45
        assert np.mean(v1) / np.mean(v2) > 2.5
        # 4折全覆盖(重平衡后)
        v2_folds = {q["fold"] for q in eval_q if q["scene"] == "table_deep_v2"}
        assert v2_folds == {0, 1, 2, 3}

    def test_train_unchanged(self):
        ds = json.loads(URE_V2.read_text(encoding="utf-8"))
        train_q = [q for q in ds["queries"] if q["split"] == "train"]
        assert len(train_q) == 2008


@pytest.mark.skipif(not DEEP_V2_EVAL.exists(), reason="未跑(深行v2实验)")
def test_deep_v2_decisive():
    """决定性实验: 反拷贝深行查询(155条, 4折)全方法对比+救援实验.

    结论: ①O1-unit全方法第一(0.329/0.600, +12.9 R@1 over M3-dense)
    ——干净数据上单元优势更明确; ②重排不救援(O1+rrF 0.271<0.329,
    cross-encoder同样做不好语义行匹配); ③BM25在语义查询上近废(0.090)
    ——v1的0.70+确系词面泄漏虚高.
    """
    d = json.loads(DEEP_V2_EVAL.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["O1-unit"]["R@1"] == pytest.approx(0.329, abs=1e-2)
    assert r["O1-unit"]["R@5"] == pytest.approx(0.600, abs=1e-2)
    assert r["O1-unit"]["MRR@10"] == pytest.approx(0.441, abs=1e-2)
    assert r["M3-dense"]["R@1"] == pytest.approx(0.200, abs=1e-2)
    assert r["B1-dense"]["R@1"] == pytest.approx(0.116, abs=1e-2)
    # O1第一名
    assert r["O1-unit"]["R@1"] > r["M3-dense"]["R@1"] + 0.10
    assert r["O1-unit"]["R@1"] > r["ROUTE(O1+M3)"]["R@1"]
    # 重排不救援(关键负结果)
    assert r["O1+rrF"]["R@1"] < r["O1-unit"]["R@1"]
    # BM25词面在语义查询上失效
    assert r["BM25-doc"]["R@1"] < 0.15


@pytest.mark.skipif(not DEEP_V2_Q.exists(), reason="v2查询未生成")
def test_deep_v2_queries_quality():
    qs = json.loads(DEEP_V2_Q.read_text(encoding="utf-8"))
    assert len(qs) == 262
    assert all(q["overlap"] < 0.5 for q in qs)
    assert np.mean([q["overlap"] for q in qs]) < 0.2
