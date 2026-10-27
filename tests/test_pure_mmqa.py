"""PURE-MMQA-URE(SRS域外部数据集)快照: Zenodo语料解封后的全量转换."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

PURE_URE = BASE / "data/gjb_438c/data_assets/evalsets/pure_mmqa_ure.json"
PURE_EVAL = BASE / "data/gjb_438c/data_assets/evalsets/pure_mmqa_eval.json"


@pytest.mark.skipif(not PURE_URE.exists(), reason="未构建")
def test_pure_ure_schema():
    """统一形态遵从+全量规模: 10文档/1122块/166查询."""
    ds = json.loads(PURE_URE.read_text(encoding="utf-8"))
    assert ds["meta"]["name"] == "PURE-MMQA-URE"
    assert ds["meta"]["version"] == "2.0-full"
    assert ds["meta"]["language"] == "en"
    assert len(ds["corpus"]) == 1128
    assert len(ds["queries"]) >= 180
    n_docs = len({c["doc"] for c in ds["corpus"]})
    assert n_docs == 10
    for c in ds["corpus"][:20]:
        for field in ("doc", "chunk_id", "type", "scene", "title",
                      "units", "n_units", "fold"):
            assert field in c
    ids = {c["chunk_id"] for c in ds["corpus"]}
    assert all(q["expected"][0] in ids for q in ds["queries"][:100])
    assert all(q["source"] == "pure_mmqa_real" for q in ds["queries"][:50])
    types = Counter(q["type"] for q in ds["queries"])
    assert types["text_only"] >= 110
    assert types.get("multimodal", 0) + types.get("figure", 0) >= 50


@pytest.mark.skipif(not PURE_EVAL.exists(), reason="未评测")
def test_pure_eval_snapshot():
    """SRS域外部效度快照: R@5最优; text_only子集unit最优(0.333)."""
    d = json.loads(PURE_EVAL.read_text(encoding="utf-8"))
    r = d["results"]
    assert r["BM25-doc"]["R@1"] == pytest.approx(0.319, abs=1e-2)
    assert r["B1-dense"]["R@1"] == pytest.approx(0.319, abs=1e-2)
    assert r["O1-unit"]["R@1"] == pytest.approx(0.283, abs=1e-2)
    assert r["O1-unit"]["R@5"] == pytest.approx(0.554, abs=1e-2)
    assert r["O1-unit"]["R@5"] > r["B1-dense"]["R@5"] + 0.05
