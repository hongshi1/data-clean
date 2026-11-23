"""Recall analysis API v2: query → fine-grained entity highlighting + BM25.

二次拆分: 不把整句当一个实体, 而是在词边界处切分,
每个子词标注语义角色(功能名/概念/动词/标识符/领域术语).
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

BASE = Path(__file__).resolve().parents[1]
router = APIRouter()

# ── 二次拆分: 词表+正则 ──────────────────────────────────────────────

#: 功能名词缀(实体右边界): 遇到这些词, 前面的部分是功能名/操作名
_FUNCTION_SUFFIXES = (
    "功能", "操作", "接口", "服务", "管理", "模块", "系统", "组件",
    "流程", "用例", "工具", "平台", "框架", "协议", "通道", "端口",
)

#: 概念词(独立实体): 常见的需求领域概念
_CONCEPT_WORDS = (
    "功能", "操作", "接口", "数据", "参数", "标识符", "名称",
    "设备", "阶段", "方式", "类型", "版本", "路径", "格式",
    "时间", "周期", "频率", "阈值", "容量", "精度", "误差",
    "权限", "角色", "状态", "模式", "分支", "场景",
)

#: 动词/关系词(独立实体): 查询中的行为词
_VERB_WORDS = (
    "包含", "包括", "支持", "提供", "使用", "需要", "要求",
    "是什么", "有哪些", "哪些", "怎么", "如何", "分别",
    "是什么", "为", "是", "有", "在", "对", "向", "从",
)

#: 领域术语(精确匹配)
_DOMAIN_TERMS = (
    "SQL", "BLOB", "JSON", "XML", "HTTP", "TCP", "UDP",
    "INT", "STRING", "FLOAT", "CPU", "GPU", "API",
    "PZXQ", "GJB",
)

_COLORS = {
    "function": ("#6366f1", "功能名"),
    "concept": ("#059669", "概念"),
    "verb": ("#d97706", "动词/疑问"),
    "domain": ("#0891b2", "领域术语"),
    "id": ("#7c3aed", "标识符"),
    "other": ("#64748b", "其他"),
}


def _fine_grained_split(text: str) -> list[dict]:
    """查询文本 → 高亮标注的子实体列表(带位置和颜色).

    策略(声明式, 无if-else链):
    1. PZXQ-ID正则精确匹配;
    2. 领域术语精确匹配;
    3. 功能名: 最长匹配到功能后缀的连续词块;
    4. 概念词/动词: 词典直查;
    5. 剩余中文: 2字滑窗(供BM25消费).
    """
    results: list[dict] = []
    used: list[tuple[int, int]] = []  # 已占用的区间

    def _add(start: int, end: int, etype: str, surface: str) -> None:
        color, label = _COLORS.get(etype, _COLORS["other"])
        results.append({
            "start": start, "end": end, "text": surface,
            "type": etype, "label": label, "color": color,
        })
        used.append((start, end))

    def _is_free(start: int, end: int) -> bool:
        return not any(s < end and start < e for s, e in used)

    # 1. PZXQ-ID
    for m in re.finditer(r"PZXQ-[A-Z0-9-]+", text):
        if _is_free(m.start(), m.end()):
            _add(m.start(), m.end(), "id", m.group())

    # 2. 领域术语
    for term in _DOMAIN_TERMS:
        for m in re.finditer(re.escape(term), text, re.IGNORECASE):
            if _is_free(m.start(), m.end()):
                _add(m.start(), m.end(), "domain", m.group())

    # 3. 功能名: 匹配"名词短语+功能后缀"的最长块
    for suffix in _FUNCTION_SUFFIXES:
        pattern = r"[\u4e00-\u9fff]{2,12}" + re.escape(suffix)
        for m in re.finditer(pattern, text):
            if _is_free(m.start(), m.end()):
                _add(m.start(), m.end(), "function", m.group())

    # 4. 概念词(未被功能名覆盖的)
    for word in _CONCEPT_WORDS:
        pos = 0
        while True:
            idx = text.find(word, pos)
            if idx < 0:
                break
            if _is_free(idx, idx + len(word)):
                _add(idx, idx + len(word), "concept", word)
            pos = idx + len(word)

    # 5. 动词/疑问词
    for word in _VERB_WORDS:
        pos = 0
        while True:
            idx = text.find(word, pos)
            if idx < 0:
                break
            if _is_free(idx, idx + len(word)):
                _add(idx, idx + len(word), "verb", word)
            pos = idx + len(word)

    # 按位置排序
    results.sort(key=lambda x: x["start"])
    return results


def _bm25_tokens(text: str) -> list[str]:
    """CJK 2字滑窗 + ASCII token."""
    tokens = []
    for m in re.finditer(r"[A-Za-z0-9]+", text):
        tokens.append(m.group().lower())
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
    for i in range(len(cjk) - 1):
        tokens.append(cjk[i:i + 2])
    return tokens


@router.post("/api/recall-analysis")
def recall_analysis(body: dict) -> dict:
    """POST /api/recall-analysis: query → 细粒度实体标注 + BM25 token.

    返回 {entities(带高亮位置和颜色), bm25(摘要), query}.
    """
    text = str(body.get("text", "")).strip()
    if not text:
        return {"ok": True, "data": {"entities": [], "bm25": {},
                                     "query": ""}}

    entities = _fine_grained_split(text)
    tokens = _bm25_tokens(text)
    # BM25只返回摘要(不逐个列出)
    unique_tokens = list(dict.fromkeys(tokens))
    bm25_summary = {
        "total": len(tokens),
        "unique": len(unique_tokens),
        "sample": unique_tokens[:6],  # 只展示前6个做参考
    }
    return {"ok": True, "data": {
        "entities": entities,
        "bm25": bm25_summary,
        "query": text,
    }}
