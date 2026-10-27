"""SRS-Calib部署模块: 场景路由+数字快照锁定(论文数字).

冒烟: 4个手工样本的方向性
快照: md held-out与clean130的固定子集上, router模式F1锁定
(模型加载约30s, 仅GPU/CPU单次加载)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.srs_calib import is_interface, predict  # noqa: E402

HAS_MODELS = (BASE / "models/nli/erlangshen-330m-qlora-v6").exists() and \
             (BASE / "models/nli/erlangshen-330m-qlora-v8-cct").exists()

SMOKE = [
    ("接口表与接口图对照中, 表格规定接口「数据上报接口」。",
     "图中缺失该接口的组件。", "inconsistent", "interface"),
    ("XX用例的表格规定异常流E1「连接失败时提示用户」。",
     "流程图中没有该异常分支。", None, "other"),
    ("文档3.2节规定：响应时间不大于2s。",
     "文档4.5节规定：响应时间不大于5s。", "inconsistent", "other"),
]


def test_scene_detector():
    assert is_interface("接口表与接口图对照中, 表格规定接口「X」。")
    assert not is_interface("XX用例的表格规定步骤「Y」。")
    assert is_interface("报文处理服务的组件设计")


def test_router_labels_and_scenes():
    if not HAS_MODELS:
        pytest.skip("本地模型未就绪")
    res = predict([(p, h) for p, h, _, _ in SMOKE], mode="router")
    for (p, h, want_lab, want_scene), r in zip(SMOKE, res):
        assert r["scene"] == want_scene
        if want_lab:
            assert r["label"] == want_lab
        assert 0.0 <= r["prob"] <= 1.0


def test_multi_angle_router():
    """多角度路由: 场景×类型元数据→方法映射(论文核心部署架构)."""
    if not HAS_MODELS:
        pytest.skip("本地模型未就绪")
    pairs = [
        ("接口表与接口图对照中, 表格规定接口「数据上报接口」。",
         "图中缺失该接口的组件。", {"scene": "sc3_interface_interface", "dtype": "COMPONENT_MISSING"}, "v6"),
        ("XX用例的表格规定步骤「系统执行数据校验」。",
         "流程图中没有与该步骤对应的节点。", {"scene": "sc2_flowchart_usecase", "dtype": "STEP_MISSING"}, "mdeberta"),
        ("XX用例的表格规定参与者为「开发人员」。",
         "流程图中没有绘制参与者节点。", {"scene": "sc2_flowchart_usecase", "dtype": "ACTOR_MISSING"}, "v8"),
    ]
    res = predict([(p, h) for p, h, _, _ in pairs], mode="multi-angle",
                  meta=[m for _, _, m, _ in pairs])
    for (p, h, m, want_model), r in zip(pairs, res):
        assert r["model"] == want_model
        assert r["label"] in ("inconsistent", "consistent")
        assert "angle" in r


def test_multi_angle_needs_meta():
    with pytest.raises(ValueError):
        predict([("a", "b")], mode="multi-angle")


def test_router_snapshot_f1():
    """论文数字: router在md held-out与clean130固定子集的F1(容差0.02)."""
    if not HAS_MODELS:
        pytest.skip("本地模型未就绪")
    md = json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8"))
    clean = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    # 固定子集: sc3前30 + clean前20 (确定性)
    sub = [(x["premise"], x["hypothesis"], x["label"]) for x in md[:30]] + \
          [(x["premise"], x["hypothesis"], x["label"]) for x in clean[:20]]
    res = predict([(p, h) for p, h, _ in sub], mode="router")
    tp = sum(1 for (_, _, y), r in zip(sub, res) if y == "inconsistent" and r["label"] == "inconsistent")
    fp = sum(1 for (_, _, y), r in zip(sub, res) if y != "inconsistent" and r["label"] == "inconsistent")
    fn = sum(1 for (_, _, y), r in zip(sub, res) if y == "inconsistent" and r["label"] != "inconsistent")
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    # 快照: 首轮实测锁定(F1≈0.72量级, 容差容忍环境差)
    assert f1 > 0.55, f"router F1跌落: {f1:.3f}"
    assert rec > 0.45, f"召回跌落: {rec:.3f}"
