"""DuRetrieval-URE(中文文本模态负对照)快照."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

DURET_URE = BASE / "data/gjb_438c/data_assets/evalsets/duret_ure.json"
DURET_EVAL = BASE / "data/gjb_438c/data_assets/evalsets/duret_eval.json"


@pytest.mark.skipif(not DURET_URE.exists(), reason="未构建")
def test_duret_ure_schema():
    """统一形态遵从: 字段与GJB-URE/WTQ/FeTaQA完全一致."""
    ds = json.loads(DURET_URE.read_text(encoding="utf-8"))
    assert ds["meta"]["name"] == "DuRetrieval-URE"
    assert ds["meta"]["language"] == "zh"
    assert len(ds["corpus"]) == 10000
    assert len(ds["queries"]) == 2000
    c = ds["corpus"][0]
    for field in ("doc", "chunk_id", "type", "scene", "title",
                  "units", "n_units", "fold"):
        assert field in c, f"corpus缺字段: {field}"
    # 文本模态: type=text, scene=prose, 单元=句子
    assert all(c["type"] == "text" for c in ds["corpus"][:50])
    assert all(c["scene"] == "prose" for c in ds["corpus"][:50])
    # 引用完整性
    ids = {c["chunk_id"] for c in ds["corpus"]}
    assert all(q["expected"][0] in ids for q in ds["queries"][:200])
    # 真实查询来源(非合成)
    assert all(q["source"] == "duret_real" for q in ds["queries"][:100])


@pytest.mark.skipif(not DURET_EVAL.exists(), reason="未评测")
def test_duret_negative_control():
    """负对照: 短文本场景dense>unit——单元分解优势条件=内容超窗口.

    DuRetrieval段落~100-200字符: 无截断/无稀释→整段dense最优
    (0.965 vs 0.950). 这是方法适用边界的诚实定义, 非缺陷.
    """
    d = json.loads(DURET_EVAL.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["B1-dense"]["R@1"] == pytest.approx(0.879, abs=1e-2)
    assert r["O1-unit"]["R@1"] == pytest.approx(0.837, abs=1e-2)
    assert r["B1-dense"]["R@1"] > r["O1-unit"]["R@1"]
    # BM25来自采样池(10K)口径(全量池未跑BM25, 数字仅供对照)
    assert r["BM25-doc"]["R@1"] == pytest.approx(0.836, abs=1e-2)
