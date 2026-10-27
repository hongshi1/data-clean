"""两阶段检索(单元召回×cross-encoder重排)评测快照测试.

论文数字锁定: 对比矩阵B1/B2/O1/O2a/O2b, 三场景.
核心claim: ①单元召回抬升重排天花板(图R@10 0.902 vs 0.846);
②深行上全文重排被512-token窗口截断反噬, 单元片段重排修复.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

EVAL_JSON = BASE / "data/gjb_438c/data_assets/two_stage_eval.json"


@pytest.mark.skipif(not EVAL_JSON.exists(),
                    reason="评测未生成(先跑 tools/eval_two_stage.py)")
def test_two_stage_matrix_snapshot():
    """对比矩阵快照(top-10重排, 4-fold, 数字锁定期: 2026-09)."""
    d = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    r = d["results"]

    # ── 图: O2a最优, 单元召回抬天花板 ──
    img = r["image"]
    assert img["B1_dense"]["R@1"] == pytest.approx(0.515, abs=1e-3)
    assert img["B2_dense_rrF"]["R@1"] == pytest.approx(0.622, abs=1e-3)
    assert img["O1_unit"]["R@1"] == pytest.approx(0.619, abs=1e-3)
    assert img["O2a_unit_rrF"]["R@1"] == pytest.approx(0.663, abs=1e-3)
    assert img["O2a_unit_rrF"]["R@5"] == pytest.approx(0.887, abs=1e-3)
    assert img["O2a_unit_rrF"]["MRR@10"] == pytest.approx(0.758, abs=1e-3)
    # 天花板: 单元召回R@10高于dense
    assert img["O1_unit"]["R@10"] > img["B1_dense"]["R@10"] + 0.04
    # 重排收益: O2a > B2 (同重排器, 不同召回源)
    assert img["O2a_unit_rrF"]["R@1"] > img["B2_dense_rrF"]["R@1"]
    assert img["O2a_unit_rrF"]["MRR@10"] > img["B2_dense_rrF"]["MRR@10"]

    # ── 表caption: 重排有效, O2a≈B2 ──
    cap = r["table_caption"]
    assert cap["B2_dense_rrF"]["R@1"] == pytest.approx(0.867, abs=1e-3)
    assert cap["O2a_unit_rrF"]["R@1"] == pytest.approx(0.863, abs=1e-3)
    assert cap["O2a_unit_rrF"]["R@5"] == pytest.approx(0.953, abs=1e-3)

    # ── 表深行: 全文重排反噬, 片段重排修复 ──
    deep = r["table_deep"]
    assert deep["B1_dense"]["R@5"] == pytest.approx(0.330, abs=1e-2)
    # 全文重排降R@1 (窗口截断看不见深行)
    assert deep["O2a_unit_rrF"]["R@1"] < deep["O1_unit"]["R@1"]
    # 片段重排: R@5/MRR最优
    assert deep["O2b_unit_rrS"]["R@5"] == pytest.approx(0.970, abs=1e-3)
    assert deep["O2b_unit_rrS"]["R@5"] > deep["O1_unit"]["R@5"]
    assert deep["O2b_unit_rrS"]["MRR@10"] > deep["O1_unit"]["MRR@10"]
    # 深行基线差距量级
    assert deep["O2b_unit_rrS"]["R@5"] > deep["B2_dense_rrF"]["R@5"] + 0.5
