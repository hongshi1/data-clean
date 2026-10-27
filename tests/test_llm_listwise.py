"""LLMListwiseRerank测试: 解析容错/截断/回退(全确定性, 注入fake llm_fn)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_linking.baselines import LLMListwiseRerank


def _mk(llm_out: str, max_docs: int = 20):
    def llm_fn(query: str, docs: str) -> str:
        _ = query, docs
        return llm_out
    return LLMListwiseRerank(llm_fn, max_docs=max_docs)


def test_rank_normal_permutation():
    r = _mk("3,1,2")
    order = r.rank("q", ["a", "b", "c"])
    assert order == [2, 0, 1]


def test_rank_parse_garbage_fallback():
    """输出无数字 → 原序回退."""
    r = _mk("抱歉我无法排序")
    assert r.rank("q", ["a", "b", "c"]) == [0, 1, 2]


def test_rank_out_of_range_and_dup():
    """越界/重复编号剔除, 未提及者按原序续尾."""
    r = _mk("9,2,2,1")
    order = r.rank("q", ["a", "b", "c", "d"])
    assert order == [1, 0, 2, 3]


def test_rank_truncation_and_tail():
    """超过max_docs截断, 尾部按原序续."""
    r = _mk("2,1", max_docs=2)
    docs = [f"d{i}" for i in range(5)]
    order = r.rank("q", docs)
    assert order == [1, 0, 2, 3, 4]


def test_rank_empty():
    assert _mk("1").rank("q", []) == []


def test_prompt_contains_query_and_docs():
    captured = {}

    def llm_fn(query: str, docs: str) -> str:
        captured["q"], captured["d"] = query, docs
        return "1"
    r = LLMListwiseRerank(llm_fn)
    r.rank("接口数据一览表", ["GJB 438B", "合格性"])
    assert captured["q"] == "接口数据一览表"
    assert "GJB 438B" in captured["d"]


def test_rank_docs_returns_strings():
    r = _mk("2,1")
    assert r.rank_docs("q", ["x", "y"]) == ["y", "x"]
