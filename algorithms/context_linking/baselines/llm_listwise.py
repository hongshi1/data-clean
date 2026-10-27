"""LLM列表级重排baseline(LLM-as-Reranker, 2025年主流范式).

科研动机(RQ2): 残余90条精度失败源于pointwise cross-encoder的
逐对绝对打分; 列表级相对判别(一次看全候选)是免训练的替代路径.
对比: cross-encoder(pointwise) vs LLM(listwise) — 两种交互侧方案.

协议: llm_fn注入(调用方负责缓存, 如algorithms.llm_client的
cache=True); 输出解析失败时回退原序(确定性).
"""
from __future__ import annotations

import re
from typing import Callable

PromptFn = Callable[[str, str], str]


class LLMListwiseRerank:
    """列表级重排: query+编号候选列表 → LLM输出全序.

    rank()返回docs的索引按相关性降序; 解析容错:
    提取数字序列→越界/重复剔除→未提及者按原序续尾.
    """

    name = "llm_listwise"

    def __init__(self, llm_fn: PromptFn, max_docs: int = 20) -> None:
        self._llm = llm_fn
        self._max_docs = max_docs

    def _prompt(self, query: str, docs: list[str]) -> str:
        lines = [f"{i}. {d[:150]}" for i, d in enumerate(docs, 1)]
        return (
            "你是文档检索评测的排序器。给定查询和候选证据列表，"
            "按与查询的相关性从高到低排列候选编号。\n\n"
            f"查询: {query}\n\n候选证据:\n" + "\n".join(lines) +
            "\n\n只输出逗号分隔的编号序列(从最相关到最不相关)，"
            "例如: 3,1,2,4,5")

    def rank(self, query: str, docs: list[str]) -> list[int]:
        """docs→索引列表(按相关性降序). 截断到max_docs, 余者续尾."""
        k = min(len(docs), self._max_docs)
        head = docs[:k]
        if k == 0:
            return []
        out = self._llm(query, " ; ".join(head))
        nums = [int(x) for x in re.findall(r"\d+", out or "")]
        seen: set[int] = set()
        order: list[int] = []
        for num in nums:
            idx = num - 1
            if 0 <= idx < k and idx not in seen:
                order.append(idx)
                seen.add(idx)
        order.extend(i for i in range(k) if i not in seen)
        order.extend(range(k, len(docs)))
        return order

    def rank_docs(self, query: str, docs: list[str]) -> list[str]:
        return [docs[i] for i in self.rank(query, docs)]
