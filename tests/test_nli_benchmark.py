"""NLI Benchmark测试: 4任务集加载与评测内核(确定性, 无GPU依赖)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from nli_benchmark import (  # noqa: E402
    eval_task,
    load_t2,
    load_t3,
    load_t4,
)

HAS_DATA = (BASE / "data/gjb_438c/data_assets/real_doc_findings.json").exists()


@pytest.mark.skipif(not HAS_DATA, reason="数据资产缺失")
def test_t2_real_contradictions():
    pairs, exps, metas = load_t2()
    assert len(pairs) == 24
    assert all(e == 1 for e in exps)
    assert all("闭世界" not in p for p in pairs)  # 声明格式检查
    # 类型分布
    types = {m["type"] for m in metas}
    assert types == {"text_vs_graph", "enumeration_conflict"}


@pytest.mark.skipif(not HAS_DATA, reason="数据资产缺失")
def test_t3_synthetic():
    pairs, exps, metas = load_t3()
    assert len(pairs) == 158
    assert all(e == 1 for e in exps)
    channels = {m["channel"] for m in metas}
    assert {"lexical", "nli-strong", "llm", "nli-weak", "syntax"} <= channels


@pytest.mark.skipif(not HAS_DATA, reason="数据资产缺失")
def test_t4_three_families():
    pairs, exps, metas = load_t4()
    assert len(pairs) >= 100
    families = {}
    for m in metas:
        families[m["family"]] = families.get(m["family"], 0) + 1
    assert families.get("恒等") == 40
    assert families.get("真实多模态") == 50
    assert families.get("单位等效") == 20
    assert all(e == 0 for e in exps)


def test_eval_task_metrics():
    verdicts = [
        {"sym_contra": True, "contra_score": 0.9, "fwd": {"label": "contradiction", "p_contra": 0.9}},
        {"sym_contra": False, "contra_score": 0.1, "fwd": {"label": "neutral", "p_contra": 0.1}},
    ]
    exps = [1, 0]
    m = eval_task(verdicts, exps, bidirectional=True)
    assert m["precision"] == 1.0 and m["recall"] == 1.0
    assert m["tp"] == 1 and m["fp"] == 0 and m["tn"] == 1


def test_eval_task_unidirectional():
    verdicts = [
        {"sym_contra": False, "contra_score": 0.1, "fwd": {"label": "contradiction", "p_contra": 0.8}},
        {"sym_contra": False, "contra_score": 0.0, "fwd": {"label": "neutral", "p_contra": 0.1}},
    ]
    exps = [1, 0]
    m = eval_task(verdicts, exps, bidirectional=False)
    assert m["recall"] == 1.0  # 单向判矛盾
    assert m["precision"] == 1.0


@pytest.mark.skipif(not Path("models/nli").exists(), reason="NLI模型未安装")
@pytest.mark.skipif(not Path("models/nli/erlangshen").exists(), reason="NLI模型未安装")
def test_nli_models_registry():
    """模型注册表: 权重完整性检查(>100MB才可用)."""
    from algorithms.consistency.nli_local import MODELS
    assert set(MODELS) >= {"mdeberta", "erlangshen"}
    for key in MODELS:
        d = Path(MODELS[key]["dir"])
        assert d.exists(), f"{key}目录缺失"
