"""覆盖差异型检测器: 平行表格的行级覆盖/取值比对(69号类型学补全).

背景(69号发现4): 不一致分两型——值矛盾型(NLI可判)与覆盖差异型
(需表结构对齐+集合关系). 本模块检测后者:
  平行表 = 不同章节但共享行scope键(设备/条目名)的表对
  每个共享scope行比较: ①字段覆盖集差异 ②同字段取值(含子集关系)

输出finding类型:
  coverage_diff       字段只在一张表出现(覆盖缺口)
  value_subset_gap    同字段, 一表取值为另一表的子集(覆盖不完整)
  value_conflict      同字段, 取值互斥(非子集关系)

设计: 纯函数(表格已结构化为rows=单元格列表); 模块顶层零I/O.
"""
from __future__ import annotations

import re
from typing import Mapping, Sequence

# 值归一(比较用): 去空白与全半角标点
_NORM = re.compile(r"[\s，。；、：:（）()\[\]「」\"'·-]+")
# 枚举分隔符(子集判定: 长侧须为多项列表, 如"1600(DVI)、1280(VGA)")
_LIST_SEP = re.compile(r"[、,;；]")

# 索引/编号类列: 行号与章节号在平行表间天然不同, 不构成不一致
_INDEX_FIELDS = {"序号", "编号", "No", "No.", "no", "章节号",
                 "本文档的章节号", "页码", "页", "表号", "行号"}


def _norm_value(v: str) -> str:
    return _NORM.sub("", str(v))


def table_scope_rows(table: Mapping) -> dict[str, dict[str, str]]:
    """表格→{scope键: {字段: 值}}.

    scope键=行内首个非纯数字单元格(设备/条目名, 与atomizer行头约定
    一致); 字段=表头列(跳过scope列)与单元格配对; 空值跳过.
    """
    rows = table.get("rows") or []
    if len(rows) < 2:
        return {}
    header = [str(c) for c in (table.get("header_candidate")
                                or rows[0])]
    out: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        cells = [str(c).strip() for c in row]
        if not cells:
            continue
        scope = next((c for c in cells if c and not c.isdigit()), "")
        if not scope:
            continue
        fields: dict[str, str] = {}
        for i, cell in enumerate(cells):
            if i >= len(header) or i == cells.index(scope):
                continue
            if cell and header[i]:
                fields[header[i]] = cell
        out.setdefault(scope, {}).update(fields)
    return out


def find_parallel_tables(tables: Sequence[Mapping],
                         min_shared: int = 2,
                         ) -> list[tuple[Mapping, Mapping, set[str]]]:
    """同文档内找平行表对: 不同章节且共享≥min_shared个scope键.

    附加条件(降噪): 共享scope行上还须共享≥1个实质字段名
    (排除索引列)——纯scope重合的异构表(如运行环境表vs质量表)不配对.
    """
    by_doc: dict[str, list[Mapping]] = {}
    for t in tables:
        if (t.get("row_count") or 0) >= 2:
            by_doc.setdefault(str(t.get("doc_id", "")), []).append(t)
    pairs: list[tuple[Mapping, Mapping, set[str]]] = []
    cache: dict[int, dict[str, dict[str, str]]] = {}
    for tabs in by_doc.values():
        for i in range(len(tabs)):
            for j in range(i + 1, len(tabs)):
                a, b = tabs[i], tabs[j]
                if a.get("section") == b.get("section"):
                    continue
                if id(a) not in cache:
                    cache[id(a)] = table_scope_rows(a)
                if id(b) not in cache:
                    cache[id(b)] = table_scope_rows(b)
                ka, kb = cache[id(a)], cache[id(b)]
                shared = set(ka) & set(kb)
                if len(shared) < min_shared:
                    continue
                shared_fields = {
                    f for s in shared
                    for f in set(ka[s]) & set(kb[s])
                    if f not in _INDEX_FIELDS}
                if not shared_fields:
                    continue
                pairs.append((a, b, shared))
    return pairs


def compare_tables(a: Mapping, b: Mapping,
                   shared: set[str]) -> list[dict]:
    """一对平行表→覆盖/取值findings(仅共享scope行, 索引列/纯数字值跳过)."""
    ra, rb = table_scope_rows(a), table_scope_rows(b)
    findings: list[dict] = []
    for scope in sorted(shared):
        fa, fb = ra[scope], rb[scope]
        # ① 字段覆盖集差异(索引类字段不构成覆盖不一致)
        for field in sorted(set(fa) - set(fb)):
            if field in _INDEX_FIELDS:
                continue
            findings.append(_finding(a, b, scope, field, "coverage_diff",
                                     fa[field], ""))
        for field in sorted(set(fb) - set(fa)):
            if field in _INDEX_FIELDS:
                continue
            findings.append(_finding(a, b, scope, field, "coverage_diff",
                                     "", fb[field]))
        # ② 同字段取值比较(纯数字双侧=行数/计数类, 跳过)
        for field in sorted(set(fa) & set(fb)):
            if field in _INDEX_FIELDS:
                continue
            va, vb = _norm_value(fa[field]), _norm_value(fb[field])
            if va == vb:
                continue
            if va.isdigit() and vb.isdigit():
                continue
            # 子集=长侧为多项枚举且包含短侧(如"1600(DVI)、1280(VGA)"⊇"1280(VGA)");
            # 枚举分隔符检查在原始文本上(归一化会剥离、,;); 无分隔符的包含
            # (如name⊂user_name)是标识差异, 判value_conflict
            subset = ((va in vb and _LIST_SEP.search(fb[field]))
                      or (vb in va and _LIST_SEP.search(fa[field])))
            gap_type = "value_subset_gap" if subset else "value_conflict"
            findings.append(_finding(a, b, scope, field, gap_type,
                                     fa[field], fb[field]))
    return findings


def _finding(a: Mapping, b: Mapping, scope: str, field: str,
             ftype: str, va: str, vb: str) -> dict:
    return {
        "doc_id": str(a.get("doc_id", "")),
        "table_a": str(a.get("table_id", "")),
        "table_b": str(b.get("table_id", "")),
        "section_a": str(a.get("section", "")),
        "section_b": str(b.get("section", "")),
        "scope": scope[:24], "field": field[:24], "type": ftype,
        "value_a": va[:80], "value_b": vb[:80],
    }


def detect_all(tables: Sequence[Mapping]) -> list[dict]:
    """全量表→全部findings(平行表对×共享scope行比较)."""
    findings: list[dict] = []
    for a, b, shared in find_parallel_tables(tables):
        findings.extend(compare_tables(a, b, shared))
    return findings


__all__ = ["table_scope_rows", "find_parallel_tables",
           "compare_tables", "detect_all"]
