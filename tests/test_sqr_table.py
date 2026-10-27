"""SQR表号路由测试(集成遗留快赢)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.sqr import StructuredQueryRouter, extract_structured_signals  # noqa: E402


def test_table_num_signal():
    """表号信号提取(已有, 回归)."""
    s = extract_structured_signals("表2的所有能力标识在哪")
    assert s.get("table_num") == 2


def test_table_num_routing():
    """表号直查: 表号查询直接路由到表chunk, 不走向量."""
    chunks = [
        {"chunk_id": "a_I001", "type": "image", "image_path": "images/fig_001.png",
         "section": "3.2"},
        {"chunk_id": "a_T002", "type": "table", "table_caption": "表2 联合研制开发服务说明",
         "section": "3.1"},
        {"chunk_id": "a_T003", "type": "table", "table_caption": "表3 性能指标",
         "section": "3.3"},
    ]
    router = StructuredQueryRouter(chunks)
    res = router.route("表2的所有能力标识在哪定义")
    assert res is not None
    assert len(res) == 1
    assert res[0]["chunk_id"] == "a_T002"


def test_table_num_no_match():
    """表号无匹配→None(走向量)."""
    chunks = [
        {"chunk_id": "a_I001", "type": "image", "image_path": "images/fig_001.png",
         "section": "3.2"},
    ]
    router = StructuredQueryRouter(chunks)
    res = router.route("表99的内容")
    assert res is None


def test_fig_routing_still_works():
    """图号路由回归(不因新代码破坏)."""
    chunks = [
        {"chunk_id": "a_I005", "type": "image", "image_path": "images/fig_005.png",
         "section": "3.2"},
    ]
    router = StructuredQueryRouter(chunks)
    res = router.route("图5的内容")
    assert res is not None
    assert res[0]["chunk_id"] == "a_I005"
