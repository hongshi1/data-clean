"""κ_T编译器同步测试: vendored版 vs tools live版 在全部真实表格上逐字节一致.

这是"双实现漂移"的防线: 修改任一侧后必须跑本测试.
依赖requests(live版m1的顶层import), 无依赖时跳过.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from algorithms.blackboard.evidence_store import PAIR_ROOT
from algorithms.blackboard.kt_compilers import (compile_capability_table,
                                                compile_interface_table,
                                                compile_subfunction_table,
                                                compile_usecase_table)

BASE = Path(__file__).resolve().parents[3]
TOOLS = BASE / "tools"

pytestmark = pytest.mark.skipif(
    not PAIR_ROOT.exists() or not (TOOLS / "m1_compare_engine.py").exists(),
    reason="真实pair_dataset或tools缺失")


def _live_modules():
    sys.path.insert(0, str(TOOLS))
    try:
        import m1_compare_engine as m1
        import m16_scene_tier1 as m16
    except Exception as e:  # requests缺失等
        pytest.skip(f"live模块导入失败: {e}")
    return m1, m16


def _compare(vendored: dict, live: dict, strip_keys: tuple[str, ...] = ()) -> None:
    v = {k: v for k, v in vendored.items() if k not in strip_keys}
    assert json.dumps(v, ensure_ascii=False, sort_keys=True) == \
        json.dumps(live, ensure_ascii=False, sort_keys=True), \
        f"vendored与live输出不一致: keys={sorted(v)}"


def _tables(scene: str) -> list[Path]:
    d = PAIR_ROOT / scene
    if not d.exists():
        return []
    return sorted((pd / "table.csv") for pd in d.iterdir()
                  if (pd / "table.csv").exists())


def test_capability_sync():
    _, m16 = _live_modules()
    paths = _tables("sc1_usecase_capability") + _tables("sc4_flowchart_capability")
    assert paths, "sc1/sc4表格缺失"
    for p in paths[:200]:
        _compare(compile_capability_table(p), m16.compile_capability_table(p))


def test_interface_sync():
    _, m16 = _live_modules()
    for p in _tables("sc3_interface_interface"):
        _compare(compile_interface_table(p), m16.compile_interface_table(p))


def test_subfunction_sync():
    _, m16 = _live_modules()
    for p in _tables("sc5_function_capability"):
        _compare(compile_subfunction_table(p), m16.compile_subfunction_table(p))


def test_usecase_sync():
    m1, _ = _live_modules()
    paths = _tables("sc2_flowchart_usecase") + _tables("sc7_usecase_usecase")
    assert paths
    for p in paths[:200]:
        # vendored版多了"type"字段(路由用), live版无 → 剥离后比较
        _compare(compile_usecase_table(p), m1.compile_usecase_table(p),
                 strip_keys=("type",))
