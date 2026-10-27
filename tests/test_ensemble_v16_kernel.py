"""v16集成确定性内核回归: sigmoid/聚合/投票/路由/权重/指标 — 纯函数, 无I/O无GPU."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "tools"))

pytest.importorskip("ensemble_v16", reason="ensemble_v16.py已归档")

from ensemble_v16 import (  # noqa: E402
    MODELS,
    bacc_weights,
    excess_weights,
    hard_label,
    mean_p,
    median_p,
    metrics,
    route_label,
    sigmoid,
    vote_label,
    weighted_p,
)


def test_sigmoid_range():
    assert sigmoid(0.0) == 0.5
    assert sigmoid(-800.0) < 1e-20  # clamp防溢出
    assert sigmoid(800.0) > 1.0 - 1e-12
    assert 0.0 < sigmoid(-2.0) < 0.5 < sigmoid(2.0) < 1.0


def test_metrics_full_and_degenerate():
    m = metrics(["inconsistent", "consistent", "inconsistent"],
                ["inconsistent", "consistent", "consistent"])
    assert m["bAcc"] == 0.75
    assert m["TPR"] == 0.5 and m["TNR"] == 1.0
    assert m["P"] == 1.0 and m["F1"] == 0.6667
    # 无正例→tpr=0, 无负例→tnr=1 (仓库惯例: 单边指标退化)
    d = metrics(["consistent"], ["consistent"])
    assert d["bAcc"] == 0.5


def test_aggregations():
    row = {"v12": 0.9, "v15": 0.8, "v13": 0.1, "svm": 0.85}
    assert abs(mean_p(row) - 0.6625) < 1e-12
    assert abs(median_p(row) - 0.825) < 1e-12  # 排序后中间两个(0.8+0.85)/2
    assert hard_label(0.5001) == "inconsistent"
    assert hard_label(0.5) == "consistent"  # 阈值严格大于


def test_weighted_p():
    row = {"v12": 0.8, "v15": 0.4, "v13": 0.0, "svm": 0.4}
    w = {"v12": 0.4, "v15": 0.3, "v13": 0.1, "svm": 0.2}
    assert abs(weighted_p(row, w) - 0.52) < 1e-12
    z = {m: 0.0 for m in MODELS}  # 全零权重→退化均值
    assert abs(weighted_p(row, z) - mean_p(row)) < 1e-12


def test_vote_majority_and_tiebreak():
    maj = {"v12": 0.9, "v15": 0.9, "v13": 0.1, "svm": 0.9}
    assert vote_label(maj) == "inconsistent"  # 3/4
    low = {"v12": 0.9, "v15": 0.1, "v13": 0.1, "svm": 0.1}
    assert vote_label(low) == "consistent"  # 1/4
    tie_hi = {"v12": 0.9, "v15": 0.9, "v13": 0.2, "svm": 0.1}  # 2-2, 均值0.525
    assert vote_label(tie_hi) == "inconsistent"
    tie_lo = {"v12": 0.1, "v15": 0.1, "v13": 0.8, "svm": 0.2}  # 2-2, 均值0.3
    assert vote_label(tie_lo) == "consistent"


def test_route():
    r_struct = {"v12": 0.9, "v15": 0.1, "v13": 0.1, "svm": 0.1}
    assert route_label(r_struct, "STEP_MISSING") == "inconsistent"  # 结构类→v12
    assert route_label(r_struct, "ACTOR_MISSING") == "inconsistent"
    r_comp = {"v12": 0.1, "v15": 0.1, "v13": 0.9, "svm": 0.1}
    assert route_label(r_comp, "TABLE_ITEM_MISSING") == "inconsistent"  # 合规类→v13
    r_def = {"v12": 0.1, "v15": 0.9, "v13": 0.1, "svm": 0.9}
    assert route_label(r_def, "UNKNOWN_TYPE") == "inconsistent"  # 默认→(svm+v15)/2=0.9
    r_def2 = {"v12": 0.9, "v15": 0.1, "v13": 0.9, "svm": 0.1}
    assert route_label(r_def2, "UNKNOWN_TYPE") == "consistent"  # 默认均值0.1


def test_weights():
    bacc = {"v12": 0.94, "v15": 0.90, "v13": 0.65, "svm": 0.87}
    w = bacc_weights(bacc)
    assert abs(sum(w.values()) - 1.0) < 1e-12
    assert w["v12"] > w["v13"]
    we = excess_weights(bacc)
    assert abs(sum(we.values()) - 1.0) < 1e-12
    assert we["v13"] < w["v13"]  # 超额加权更狠地压弱成员
    we_zero = excess_weights({m: 0.5 for m in MODELS})
    assert all(v == 0.25 for v in we_zero.values())  # 全随机→均匀退化
    we_clip = excess_weights({m: 0.4 for m in MODELS})
    assert all(v == 0.25 for v in we_clip.values())  # 全负超额→clip后均匀退化
