"""Atomizer v1确定性回归: 65号实证案例(doc02响应时间/doc14行号噪声/单位换算)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_linking.atomizer import (  # noqa: E402
    atomize_claim, block_by_param, compare_atoms, pair_groups,
)

SURFACE = {"响应时间": "response_time", "恢复时间": "recovery_time"}


def _claim(text, quantities, section="1.8.2.1", doc="02"):
    return {
        "claim_id": "CLM-test-" + section.replace(".", ""),
        "doc_id": doc, "section": section, "raw_text": text,
        "features": {"quantities": quantities},
    }


def test_doc02_same_scope_conflict():
    """doc02真实案例: 用户响应时间3s(1.8.2) vs 5s(1.8.5) → 同作用域冲突候选."""
    a = _claim("支持首屏加载时间不小于2秒，用户响应时间不小于3秒。",
               [{"value": 2, "raw": "2", "unit_raw": "秒"},
                {"value": 3, "raw": "3", "unit_raw": "秒"}],
               section="1.8.2.1")
    b = _claim("支持首屏加载时间不小于3秒，用户响应时间不小于5秒；",
               [{"value": 3, "raw": "3", "unit_raw": "秒"},
                {"value": 5, "raw": "5", "unit_raw": "秒"}],
               section="1.8.5.1.1")
    atoms_a = atomize_claim(a, SURFACE)
    atoms_b = atomize_claim(b, SURFACE)
    assert len(atoms_a) == 1 and len(atoms_b) == 1
    fa, fb = atoms_a[0], atoms_b[0]
    assert fa.param == fb.param == "response_time"
    assert fa.value == 3.0 and fb.value == 5.0
    assert fa.operator == "≥" and fb.operator == "≥"
    assert fa.scope_hint == fb.scope_hint == "用户"
    pair = compare_atoms(fa, fb)
    assert pair.decision == "conflict_same_scope"
    assert pair.gap == 2000.0  # 秒→ms基单位差
    assert not pair.same_section


def test_doc14_row_number_noise_excluded():
    """doc14真实案例: 行号12在前被距离过滤, 取MTTR 0.5小时且操作符≤."""
    c = _claim(
        "12 | 易恢复性 | 当软件模块运行发生错误时，可查看错误提示，"
        "软件运行异常中止情况下，软件应能重新启动运行 | "
        "平均失效恢复时间（MTTR）：不大于0.5小时 | 组件化设计，",
        [{"value": 12, "raw": "12"}, {"value": 0.5, "raw": "0.5",
                                      "unit_raw": "小时"}],
        section="3.11", doc="14")
    atoms = atomize_claim(c, SURFACE)
    assert len(atoms) == 1
    a = atoms[0]
    assert a.value == 0.5 and a.unit == "小时"
    assert a.operator == "≤"
    assert a.quantity_hygiene == "unit_ok"


def test_reference_number_skipped():
    """引用编号非取值: "见表10"的10不附着为参数值."""
    c = _claim("数据归集功能的响应时间要求见表10。",
               [{"value": 10, "raw": "10"}])
    atoms = atomize_claim(c, SURFACE)
    assert atoms == []


def test_unit_conversion_redundant():
    """同族单位换算后等值→冗余: 200ms vs 0.2秒."""
    a = _claim("响应时间不大于200ms。", [{"value": 200, "raw": "200",
                                         "unit_raw": "ms"}])
    b = _claim("响应时间不大于0.2秒。", [{"value": 0.2, "raw": "0.2",
                                         "unit_raw": "秒"}])
    fa, fb = atomize_claim(a, SURFACE)[0], atomize_claim(b, SURFACE)[0]
    pair = compare_atoms(fa, fb)
    assert pair.decision == "redundant"


def test_scope_hint_prefix():
    """作用域线索: 参数复合词前缀修饰(用户/平均失效)."""
    a = atomize_claim(_claim("用户响应时间不大于3秒。",
                             [{"value": 3, "raw": "3", "unit_raw": "秒"}]),
                      SURFACE)[0]
    b = atomize_claim(
        _claim("平均失效恢复时间不大于0.5小时。",
               [{"value": 0.5, "raw": "0.5", "unit_raw": "小时"}]),
        SURFACE)[0]
    assert a.scope_hint == "用户"
    assert b.scope_hint == "平均失效"


def test_blocking_same_doc_only():
    """blocking按(文档,参数)分组: 跨文档同参不配对."""
    atoms = [
        atomize_claim(_claim("响应时间不大于3秒。",
                             [{"value": 3, "raw": "3", "unit_raw": "秒"}],
                             doc="02"), SURFACE)[0],
        atomize_claim(_claim("响应时间不大于5秒。",
                             [{"value": 5, "raw": "5", "unit_raw": "秒"}],
                             doc="03"), SURFACE)[0],
    ]
    groups = block_by_param(atoms)
    assert len(groups) == 2
    pairs = pair_groups(groups)
    assert pairs == []


def test_scope_diff_labeled():
    """作用域线索不同→弱候选(合理差异嫌疑, 需S2/S3确认)."""
    a = atomize_claim(_claim("服务器响应时间不大于3秒。",
                             [{"value": 3, "raw": "3", "unit_raw": "秒"}]),
                      SURFACE)[0]
    b = atomize_claim(_claim("客户端响应时间不大于5秒。",
                             [{"value": 5, "raw": "5", "unit_raw": "秒"}]),
                      SURFACE)[0]
    assert a.scope_hint == "服务器" and b.scope_hint == "客户端"
    pair = compare_atoms(a, b)
    assert pair.decision == "conflict_scope_diff"


def test_table_row_scope_is_row_header():
    """表格行claim作用域=行首单元格: 配置档位表不同行=不同设备=合理差异."""
    row_a = _claim(
        "| 轻量化服务器 | 处理器：16核 CPU主频：不低于1.5GHz |",
        [{"value": 1.5, "raw": "1.5", "unit_raw": "GHz"}],
        section="1.16.1")
    row_b = _claim(
        "| 便携式计算机 | 处理器：i7双核 CPU主频：不低于2.5GHz |",
        [{"value": 2.5, "raw": "2.5", "unit_raw": "GHz"}],
        section="1.16.1")
    surface = {"主频": "clock_frequency"}
    a = atomize_claim(row_a, surface)[0]
    b = atomize_claim(row_b, surface)[0]
    assert a.scope_hint == "轻量化服务器"
    assert b.scope_hint == "便携式计算机"
    pair = compare_atoms(a, b)
    assert pair.decision == "conflict_scope_diff"


def test_numbered_table_row_scope_skips_row_number():
    """带行号的表格行: 行号被跳过, 作用域仍取设备名单元格."""
    row = _claim(
        "1 | 轻量化服务器 | 处理器：16核 CPU主频：不低于1.5GHz |",
        [{"value": 1.5, "raw": "1.5", "unit_raw": "GHz"}],
        section="1.17.1")
    surface = {"主频": "clock_frequency"}
    a = atomize_claim(row, surface)[0]
    assert a.scope_hint == "轻量化服务器"


def test_weak_mention_dedup_same_claim():
    """同claim同参数多次出现: 保留带操作符的强命中(10吋弱命中被弃)."""
    c = _claim(
        "携行作业设备 显示分辨率：10吋 分辨率不低于1920×1080。",
        [{"value": 10, "raw": "10", "unit_raw": "吋"},
         {"value": 1920, "raw": "1920"}],
        section="1.16.1")
    surface = {"分辨率": "resolution"}
    atoms = atomize_claim(c, surface)
    assert len(atoms) == 1
    assert atoms[0].value == 1920 and atoms[0].operator == "≥"


def test_operator_raw_slot_used():
    """真实语料raw含操作符("不小于2秒"): between为空时用operator_raw兜底."""
    c = _claim(
        "|  | 支持首屏加载时间不小于2秒，用户响应时间不小于3秒。",
        [{"value": 2, "raw": "不小于2秒", "unit_raw": "秒",
          "operator_raw": "不小于"},
         {"value": 3, "raw": "不小于3秒", "unit_raw": "秒",
          "operator_raw": "不小于"}],
        section="1.8.2.1")
    surface = {"响应时间": "response_time"}
    atoms = atomize_claim(c, surface)
    assert len(atoms) == 1
    a = atoms[0]
    assert a.value == 3.0 and a.operator == "≥" and a.unit == "秒"
    # 单元格行(仅1个实质单元格)无行头标签 → 走局部窗口
    assert a.scope_hint == "用户"
