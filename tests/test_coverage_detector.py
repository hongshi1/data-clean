"""coverage_detector确定性回归: 69号覆盖差异型检测(78号)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.coverage_detector import (  # noqa: E402
    compare_tables, detect_all, find_parallel_tables, table_scope_rows,
)


def _table(tid, doc, section, header, rows):
    return {"table_id": tid, "doc_id": doc, "section": section,
            "row_count": len(rows), "header_candidate": header,
            "rows": [header] + rows}


def test_table_scope_rows_extracts_scopes_and_fields():
    t = _table("T-1", "10", "3.9.1",
               ["设备名称", "CPU主频", "内存"],
               [["便携式计算机", "2.5GHz", "8GB"],
                ["轻量化服务器", "1.5GHz", "16GB"]])
    scopes = table_scope_rows(t)
    assert set(scopes) == {"便携式计算机", "轻量化服务器"}
    assert scopes["便携式计算机"] == {"CPU主频": "2.5GHz", "内存": "8GB"}


def test_index_columns_and_pure_digits_filtered():
    """序号列差异与纯数字值不构成不一致."""
    a = _table("T-A", "10", "3.9.1",
               ["序号", "设备名称", "内存"],
               [["1", "便携式计算机", "8GB"], ["2", "服务器", "16GB"]])
    b = _table("T-B", "10", "3.10.1",
               ["序号", "设备名称", "内存"],
               [["5", "便携式计算机", "8GB"], ["6", "服务器", "16GB"]])
    # 序号7vs3类噪声: 字段被索引列过滤
    findings = compare_tables(a, b, {"便携式计算机", "服务器"})
    assert findings == []


def test_value_conflict_detected():
    """同字段异值(非纯数字)→value_conflict(doc10主频2.2vs2.5式)."""
    a = _table("T-A", "10", "3.9.1", ["设备名称", "CPU主频"],
               [["便携式计算机（国产化）", "2.2GHz"]])
    b = _table("T-B", "10", "3.10.1", ["设备名称", "CPU主频"],
               [["便携式计算机（国产化）", "2.5GHz"]])
    findings = compare_tables(a, b, {"便携式计算机（国产化）"})
    assert len(findings) == 1
    assert findings[0]["type"] == "value_conflict"
    assert findings[0]["value_a"] == "2.2GHz"


def test_value_subset_gap_detected():
    """一表取值为另一表子集→覆盖不完整(doc10分辨率VGA vs DVI+VGA式)."""
    a = _table("T-A", "10", "3.9.1", ["设备名称", "显示分辨率"],
               [["便携式服务器", "1280×1024（VGA）"]])
    b = _table("T-B", "10", "3.10.1", ["设备名称", "显示分辨率"],
               [["便携式服务器", "1600×1200(DVI)、1280×1024（VGA）"]])
    findings = compare_tables(a, b, {"便携式服务器"})
    assert findings[0]["type"] == "value_subset_gap"


def test_coverage_diff_detected():
    """字段只在一张表→覆盖缺口."""
    a = _table("T-A", "10", "3.9.1", ["设备名称", "内存"],
               [["设备X", "8GB"]])
    b = _table("T-B", "10", "3.10.1", ["设备名称", "内存", "存储"],
               [["设备X", "8GB", "512GB"]])
    findings = compare_tables(a, b, {"设备X"})
    types = {f["type"] for f in findings}
    assert "coverage_diff" in types
    cov = next(f for f in findings if f["type"] == "coverage_diff")
    assert cov["field"] == "存储"


def test_parallel_pairing_needs_shared_field():
    """纯scope重合的异构表(无共享实质字段)不配对."""
    a = _table("T-A", "10", "3.9.1", ["设备名称", "CPU主频"],
               [["设备X", "2.0GHz"], ["设备Y", "2.0GHz"]])
    b = _table("T-B", "10", "3.11.3", ["设备名称", "质量措施"],
               [["设备X", "评审"], ["设备Y", "测试"]])
    pairs = find_parallel_tables([a, b])
    assert pairs == []


def test_detect_all_end_to_end():
    """端到端: doc12式标识不一致(name vs user_name)."""
    a = _table("T-A", "12", "3.4.1", ["数据项", "数据元素标识"],
               [["用户名", "name"], ["密码", "pwd"]])
    b = _table("T-B", "12", "3.5.1", ["数据项", "数据元素标识"],
               [["用户名", "user_name"], ["密码", "pwd"]])
    findings = detect_all([a, b])
    conflicts = [f for f in findings if f["type"] == "value_conflict"]
    assert any(f["scope"] == "用户名" and f["value_a"] == "name"
               and f["value_b"] == "user_name" for f in conflicts)
