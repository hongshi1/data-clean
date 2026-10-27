"""K1 实体消解: 领域词典NER + 别名归一(真实实现).

词典: knowledge/entity_lexicon.json (GLM从训练语料挖掘+srs_kb种子, 冻结资产)
识别: 最长匹配词典扫描(maximum forward matching, 经典词典NER)
归一: 别名→canonical 映射, 用于参数对齐与术语一致性判定
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent


class EntityLexer:
    """基于领域词典的实体识别与归一.

    用法:
        lexer = EntityLexer()
        lexer.align("响应延迟", "响应时间")  → True(同指canonical)
        lexer.recognize("可用空间不少于200G") → [Entity(canonical=...)]
        lexer.normalize("采集") → "获取"(若词典收录)
    """

    def __init__(self, lexicon_path: Path | None = None, use_cache: bool = True):
        self._path = lexicon_path or BASE / "knowledge/entity_lexicon.json"
        self._alias2canon: dict[str, str] = {}
        self._canon_type: dict[str, str] = {}
        self._sorted_terms: list[str] = []
        if self._path.exists() and use_cache:
            self._load()

    def _load(self) -> None:
        lex = json.loads(self._path.read_text(encoding="utf-8"))
        for e in lex.get("entities", []):
            canon = str(e.get("canonical", "")).strip()
            if not canon:
                continue
            self._canon_type.setdefault(canon, str(e.get("type", "param")))
            self._alias2canon[canon] = canon
            for a in e.get("aliases", []):
                a = str(a).strip()
                if a:
                    self._alias2canon.setdefault(a, canon)
        # 最长优先(匹配扫描用)
        self._sorted_terms = sorted(self._alias2canon.keys(), key=len, reverse=True)

    # ── 归一: 任意表面串 → canonical(未收录返回原串) ──
    def normalize(self, term: str) -> str:
        t = str(term).strip()
        if t in self._alias2canon:
            return self._alias2canon[t]
        # 子串包含回退: 词典条目是term的子串 → 用词典canonical
        for entry in self._sorted_terms:
            if len(entry) >= 2 and entry in t:
                return self._alias2canon[entry]
        return t

    # ── 对齐: 两个表面串是否同指(归一后相等) ──
    def align(self, a: str, b: str) -> bool:
        if not a or not b:
            return True
        if a == b or a in b or b in a:
            return True
        return self.normalize(a) == self.normalize(b)

    # ── 识别: 文本中的全部词典实体(最长匹配) ──
    def recognize(self, text: str) -> list[dict]:
        found: list[dict] = []
        t = str(text)
        i = 0
        while i < len(t):
            matched = False
            for term in self._sorted_terms:
                if len(term) < 2:
                    continue
                if t.startswith(term, i):
                    canon = self._alias2canon[term]
                    found.append({"surface": term, "canonical": canon,
                                  "type": self._canon_type.get(canon, "?"),
                                  "start": i})
                    i += len(term)
                    matched = True
                    break
            if not matched:
                i += 1
        # 去重(同canonical多surface)
        seen: set[str] = set()
        out = []
        for e in found:
            if e["canonical"] not in seen:
                seen.add(e["canonical"])
                out.append(e)
        return out

    def stats(self) -> dict:
        return {"entities": len(self._canon_type), "alias_entries": len(self._alias2canon)}


# 模块级惰性单例(避免import期I/O)
_LEXER: EntityLexer | None = None


def get_lexer() -> EntityLexer:
    global _LEXER  # noqa: PLW0603
    if _LEXER is None:
        _LEXER = EntityLexer()
    return _LEXER
