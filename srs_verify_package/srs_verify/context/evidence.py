"""证据单元与物证库(URE语料→勘验证据模型).

勘验对应: EvidenceUnit=物证袋(单行检材/单个图元素),
EvidenceStore=物证库(全语料证据, 按owner分袋).

设计: 纯数据结构+从已加载数据构建(模块顶层零I/O).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EvidenceUnit:
    """一个证据单元(物证袋).

    text:   序列化文本(表行="表头=值"配对; 图元素=VLM描述)
    kind:   "table_row" | "image_element"
    owner:  所属语料块chunk_id(证据归属)
    title:  所属块标题(表题/图题)
    """

    text: str
    kind: str
    owner: str
    title: str


@dataclass(frozen=True)
class EvidenceHit:
    """一次检索命中(排序证据)."""

    owner: str
    kind: str
    title: str
    score: float
    head: str            # 评分头来源(semantic_unit/lexical/...)
    best_units: tuple[str, ...]  # 命中最强单元(精排文档来源)


def _units_of_chunk(chunk: dict) -> list[str]:
    """块→证据单元文本列表(title参与IDF统计, 与统一评测协议一致)."""
    return [u for u in ([chunk.get("title", "")] + chunk.get("units", []))
            if u]


class EvidenceStore:
    """物证库: 证据单元按owner聚集, 提供分段索引."""

    def __init__(self, units: list[EvidenceUnit],
                 owner_titles: dict[str, str],
                 owner_kinds: dict[str, str]) -> None:
        # 按owner稳定排序, 保证分段索引与确定性
        self.units = sorted(units, key=lambda u: (u.owner, u.text))
        self.owner_titles = owner_titles
        self.owner_kinds = owner_kinds
        # owner分段: units已按owner排序 → 连续段
        self.owners: list[str] = []
        self.segments: dict[str, tuple[int, int]] = {}
        start = 0
        for i, u in enumerate(self.units):
            if u.owner != self.units[start].owner:
                self.owners.append(self.units[start].owner)
                self.segments[self.units[start].owner] = (start, i)
                start = i
        self.owners.append(self.units[start].owner)
        self.segments[self.units[start].owner] = (start, len(self.units))

    @classmethod
    def from_ure(cls, corpus: Iterable[dict]) -> "EvidenceStore":
        """从URE语料列表构建(无I/O, 输入为已加载数据)."""
        units: list[EvidenceUnit] = []
        titles: dict[str, str] = {}
        kinds: dict[str, str] = {}
        for chunk in corpus:
            cid = chunk.get("chunk_id", "")
            ctype = chunk.get("type", "table")
            kind = "image_element" if ctype == "image" else "table_row"
            titles[cid] = chunk.get("title", "")
            kinds[cid] = kind
            for u in _units_of_chunk(chunk):
                units.append(EvidenceUnit(text=u, kind=kind, owner=cid,
                                          title=titles[cid]))
        return cls(units, titles, kinds)

    @property
    def n_units(self) -> int:
        return len(self.units)

    @property
    def n_owners(self) -> int:
        return len(self.owners)

    def unit_texts(self) -> list[str]:
        return [u.text for u in self.units]

    def units_of(self, owner: str) -> list[EvidenceUnit]:
        seg = self.segments.get(owner)
        return self.units[seg[0]:seg[1]] if seg else []

    def pool(self, kind: str) -> list[str]:
        """按证据类型筛选owner(场景路由用)."""
        return [o for o in self.owners if self.owner_kinds.get(o) == kind]

    def idf(self) -> dict[str, float]:
        """单元级IDF原始比值N/df(log(1+x)在评分头内施加 — 冻结统计投影)."""
        df: dict[str, int] = {}
        for owner in self.owners:
            for u in {x.text for x in self.units_of(owner)}:
                df[u] = df.get(u, 0) + 1
        n = max(self.n_owners, 1)
        return {u: (n / max(d, 1)) for u, d in df.items()}
