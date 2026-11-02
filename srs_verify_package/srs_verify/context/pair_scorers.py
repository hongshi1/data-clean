"""配对打分器族: score(pair)∈[0,1]统一接口的多种打分策略.

对应文档: 68号(打分策略调研与对比实验).
文献映射: 每个打分器对应一个经典打分家族(见各docstring).
设计: 纯函数; BGE/NLI重依赖经工厂注入(模块顶层零I/O/零重依赖).
简化原则(68号): 决策规则退化为"打分+阈值", 级联退化为"代价预算" —
  选择打分器的依据是成本, 而不是各层私有决策逻辑.
"""
from __future__ import annotations

import difflib
import re
from typing import Callable, Mapping, Sequence

# 数字串→占位符(模板掩码: 只留结构, 不留值)
_DIGIT_RUN = re.compile(r"\d+(?:\.\d+)?")
# 全角→半角+空白归零(模板归一)
_FW = str.maketrans("（）；：，。｜", "();:,.|")
# 标点剥离(模板/词法比较只留结构, 不留标点)
_PUNCT = re.compile(r"[()();:,.|，。；：、！？!?\"'‘’""—]")


def normalize_context(text: str) -> str:
    """上下文归一: 全角→半角, 去空白去标点 — 供词法/模板比较."""
    return _PUNCT.sub("", re.sub(r"\s+", "", text.translate(_FW)))


def mask_digits(text: str) -> str:
    """数字串掩码: '不小于2.5GHz'→'不小于_GHz' — 复制粘贴漂移信号."""
    return _DIGIT_RUN.sub("_", normalize_context(text))


def char_bigrams(text: str) -> set[str]:
    """字符二元组集合(中文无分词依赖的词法特征)."""
    s = normalize_context(text)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def score_lexical_jaccard(left: str, right: str) -> float:
    """词法Jaccard: 字符二元组重叠率.

    文献家族: 经典串相似度度量对比(Cohen et al. 2003的name-matching家族;
    Jaccard/Jaro-Winkler/编辑距离同族 — 本文取对中文鲁棒的bigram-Jaccard).
    """
    a, b = char_bigrams(left), char_bigrams(right)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def score_template_mask(left: str, right: str) -> float:
    """数字掩码模板相似度: 值挖掉后句式还相同吗.

    信号: 复制粘贴漂移(同模板改值) — SRS不一致的高发成因;
    doc02案例: "首屏不小于_秒，响应不小于_秒"两处模板完全一致→值差即漂移嫌疑.
    文献家族: 归一化编辑距离/最长公共子串(结构相似而非词面相似).
    """
    a, b = mask_digits(left), mask_digits(right)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def score_rule_scope(decision: str) -> float:
    """S1规则基线: 作用域线索相等=1.0/未知=0.5/相异=0.0.

    文献家族: Fellegi-Sunter(1969)固定比较规则(66号3.2节三支决策).
    """
    return {"conflict_same_scope": 1.0,
            "conflict_scope_unknown": 0.5,
            "conflict_scope_diff": 0.0}.get(decision, 0.0)


def _section_tuple(section: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", str(section))
    return tuple(int(x) for x in parts) if parts else ()


def score_section_proximity(left_sec: str, right_sec: str) -> float:
    """章节邻近度: 1/(1+层级加权距离).

    信号: 同节≈强嫌疑(同表格/同需求内异值), 跨章≈漂移或异域;
    文献家族: 层级距离/路径相似度(ER中的blocking键邻接性).
    """
    a, b = _section_tuple(left_sec), _section_tuple(right_sec)
    if not a or not b:
        return 0.0
    depth = max(len(a), len(b))
    dist = 0.0
    for i in range(depth):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        dist += abs(x - y) / (10 ** i)
    return 1.0 / (1.0 + dist)


def make_bge_scorer(
        embeddings: Mapping[str, Sequence[float]],
) -> Callable[[str, str], float]:
    """BGE余弦打分器(工厂: 注入预计算的上下文向量).

    文献家族: 句向量语义相似(Reimers & Gurevych 2019 SBERT系;
    本文BGE-large-zh本地GPU, 通道入口见AGENTS.md).
    """

    def _cos(u: Sequence[float], v: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(u, v))
        nu = sum(x * x for x in u) ** 0.5
        nv = sum(x * y for x, y in zip(v, v)) ** 0.5
        if nu == 0 or nv == 0:
            return 0.0
        return max(-1.0, min(1.0, dot / (nu * nv)))

    def score(left: str, right: str) -> float:
        u = embeddings.get(left)
        v = embeddings.get(right)
        if u is None or v is None:
            return 0.0
        return _cos(u, v)

    return score


def make_nli_scorer(
        predict: Callable[[list[tuple[str, str]]], list[dict]],
) -> Callable[[str, str], float]:
    """NLI矛盾概率打分器(工厂: 注入NliLocal.predict).

    文献家族: NLI-as-scorer(FEVER的RTE判定通道; 64号定位为S3残差信号,
    与检测层输入元组不同, 此处作选择层打分对照).
    双向取max: 矛盾不依赖先后次序.
    """
    cache: dict[tuple[str, str], float] = {}

    def score(left: str, right: str) -> float:
        key = (left, right)
        if key in cache:
            return cache[key]
        probs = predict([(left, right), (right, left)])
        value = max(p.get("p_contra", 0.0) for p in probs)
        cache[key] = value
        return value

    return score


def score_combined(features: Mapping[str, float],
                   weights: Mapping[str, float] | None = None) -> float:
    """线性组合: Σ wᵢ·sᵢ / Σ wᵢ (缺项跳过).

    文献家族: 加权线性融合(Fellegi-Sunter似然比的简化型;
    各信号量纲已归一到[0,1]故免z-score).
    """
    if weights is None:
        weights = {k: 1.0 for k in features}
    num = sum(weights[k] * v for k, v in features.items() if k in weights)
    den = sum(weights[k] for k in features if k in weights)
    return num / den if den else 0.0
