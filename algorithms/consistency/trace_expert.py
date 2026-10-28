"""GJB-05需求可追溯性追踪表join专家（L1确定性组件）。

GJB 438C附录J第5条要求需求可追踪性双向描述：表81(正向，任务书→本文档)与
表82(逆向，本文档→任务书)互为镜像。本专家把冻结evidence中的两张HTML追踪表
解析为规范化映射对，执行三项确定性检查并核验answer中的追溯关系声明：

1. 正逆矛盾：同一本文档锚点在两表中的任务书目标集合不一致
   （04号SRS：表81 row11代码生成3.2.4←任务书4.1.1 c) vs
     表82 row12代码生成3.2.4→任务书4.1.1 a)）。
2. 锚点有效性：映射指向的本文档章节号在文档章节清单中不存在
   （04号SRS：表81 row16指向不存在的3.2.1.7，获取错误信息实际位于3.2.1.3.1.2）。
3. 同行矛盾：行内映射非空但跟踪说明列写「不追踪」
   （04号SRS：表81 row20「接口 4.5→3.3、3.4」+「不追踪」）。

answer校验：当answer声称某需求与任务书的追溯关系时，检查表81和表82是否都
支持该关系；若正逆矛盾，无论answer取哪一侧都有一半证据反对 → refute。

本层完全确定性：无模型调用、无检索、无文件读取（章节清单由调用方从
content_list.json提取后传入）。行解析复用evidence_statements的
``_table_rows``/``_strip_tags``；空单元格在该解析中被剔除，故按列数对齐行语义。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path
from typing import Iterable

from algorithms.consistency.evidence_statements import _strip_tags, _table_rows
from algorithms.consistency.qa_models import (
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    Verdict,
)
from algorithms.consistency.rulepack import RulePack, default_rulepack

METHOD = "trace_bidirectional_join"
CHECK_ITEMS: tuple[str, ...] = ("GJB-05",)


@dataclass(frozen=True)
class _TraceConfig:
    """从rule pack编译的追踪表join配置(方向标记+词表+窗口+模式)."""

    direction_markers: tuple[str, ...]
    non_track_notes: frozenset[str]
    note_column_count: int
    max_answer_pairs: int
    section_split: re.Pattern[str]
    segment_split: re.Pattern[str]
    relation_words: re.Pattern[str]
    trace_relation_words: re.Pattern[str]
    section_token: re.Pattern[str]
    taskbook_section: re.Pattern[str]
    heading_number: re.Pattern[str]


def _build_config(pack: RulePack) -> _TraceConfig:
    trace = pack.table_spec("trace_table")
    return _TraceConfig(
        direction_markers=trace.direction_markers,
        non_track_notes=frozenset(pack.vocabulary("trace_non_track_notes")),
        note_column_count=int(
            pack.join_param("trace", "note_column_count", 5)),
        max_answer_pairs=int(pack.join_param("trace", "max_answer_pairs", 4)),
        section_split=pack.template("trace_section_split"),
        segment_split=pack.template("trace_segment_split"),
        relation_words=pack.template("trace_relation_words"),
        trace_relation_words=pack.template("trace_trace_relation_words"),
        section_token=pack.template("trace_section_token"),
        taskbook_section=pack.template("trace_taskbook_section"),
        heading_number=pack.template("trace_heading_number"),
    )


_TRACE_CONFIG: _TraceConfig | None = None


def _cfg() -> _TraceConfig:
    """惰性加载默认rule pack并编译追踪join配置(模块级缓存, import期零I/O)."""
    global _TRACE_CONFIG
    if _TRACE_CONFIG is None:
        _TRACE_CONFIG = _build_config(default_rulepack())
    return _TRACE_CONFIG



@dataclass(frozen=True)
class TraceMapping:
    """One exploded trace pair: taskbook anchor -> document anchor.

    多值单元格（如「3.9、3.10」「4.1.1 c）」）按顿号/逗号拆分并展开为
    单锚点映射；章节号统一归一（全角括号→半角、空白折叠）。
    """

    tb_name: str
    tb_section: str
    doc_name: str
    doc_section: str
    note: str
    direction: str      # "forward"(表81) / "reverse"(表82)
    evidence_id: str
    row_index: int      # 1-based data row number (header excluded)


@dataclass(frozen=True)
class TraceTables:
    """Parsed bidirectional trace tables from the frozen evidence."""

    forward: tuple[TraceMapping, ...]
    reverse: tuple[TraceMapping, ...]

    @property
    def all_mappings(self) -> tuple[TraceMapping, ...]:
        return self.forward + self.reverse


def _norm_section(token: str) -> str:
    token = token.strip().replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", " ", token).strip()


def _norm_note(cell: str) -> str:
    return re.sub(r"\s+", "", cell)


def _is_non_track(note: str) -> bool:
    return _norm_note(note) in _cfg().non_track_notes


def _table_direction(header_text: str) -> str | None:
    first, second = _cfg().direction_markers[:2]
    if first not in header_text or second not in header_text:
        return None
    if header_text.find(first) < header_text.find(second):
        return "forward"
    return "reverse"


def _classify_row(cells: list[str],
                  ) -> tuple[str, str, str, str, str] | None:
    """Classify one empty-cell-dropped row into (c0, c1, c2, c3, note).

    ``_table_rows`` removes empty cells, so column alignment degrades to
    cell-count heuristics: 5 cells = full mapping + note column;
    4 cells = full mapping with empty note; 3 cells with a trailing
    non-tracking marker = source-only untracked row.
    """
    n = len(cells)
    if n == 0:
        return None
    if n >= _cfg().note_column_count:
        return cells[0], cells[1], cells[2], cells[3], cells[4]
    if n == 4:
        if _is_non_track(cells[3]):
            return cells[0], cells[1], cells[2], "", cells[3]
        return cells[0], cells[1], cells[2], cells[3], ""
    if n == 3:
        if _is_non_track(cells[2]):
            return cells[0], cells[1], "", "", cells[2]
        return cells[0], cells[1], cells[2], "", ""
    if n == 2:
        return cells[0], cells[1], "", "", ""
    return cells[0], "", "", "", ""


def _pair_side(name_cell: str,
               section_cell: str) -> tuple[tuple[str, str], ...]:
    """Explode one side's (name, section) cell pair into single anchors."""
    sections = tuple(
        _norm_section(part) for part in _cfg().section_split.split(
            section_cell))
    sections = tuple(section for section in sections if section)
    if not sections:
        return ()
    names = tuple(name.strip()
                   for name in _cfg().section_split.split(name_cell)
                   if name.strip())
    if len(names) == len(sections):
        return tuple(zip(names, sections))
    whole = name_cell.strip()
    return tuple((whole, section) for section in sections)


def _explode_row(classified: tuple[str, str, str, str, str], direction: str,
                 evidence_id: str, row_index: int) -> tuple[TraceMapping, ...]:
    c0, c1, c2, c3, note = classified
    if direction == "forward":
        tb_side, doc_side = _pair_side(c0, c1), _pair_side(c2, c3)
    else:
        tb_side, doc_side = _pair_side(c2, c3), _pair_side(c0, c1)
    return tuple(
        TraceMapping(tb_name=tb_name, tb_section=tb_section,
                     doc_name=doc_name, doc_section=doc_section, note=note,
                     direction=direction, evidence_id=evidence_id,
                     row_index=row_index)
        for (tb_name, tb_section), (doc_name, doc_section)
        in product(tb_side, doc_side))


def parse_trace_tables(
        evidence: Iterable[RetrievedEvidence]) -> TraceTables:
    """Parse 表81(正向)/表82(逆向) trace tables from frozen evidence.

    Tables are identified by their header signature (任务书 before 本文档
    = forward; 本文档 before 任务书 = reverse); non-trace tables are skipped.
    """
    forward: list[TraceMapping] = []
    reverse: list[TraceMapping] = []
    for block in evidence:
        if "<table" not in block.text:
            continue
        rows = _table_rows(block.text)
        if not rows:
            continue
        direction = _table_direction(_strip_tags("；".join(rows[0])))
        if direction is None:
            continue
        for row_index, cells in enumerate(rows[1:], start=1):
            classified = _classify_row(cells)
            if classified is None:
                continue
            mappings = _explode_row(classified, direction,
                                    block.evidence_id, row_index)
            if direction == "forward":
                forward.extend(mappings)
            else:
                reverse.extend(mappings)
    return TraceTables(forward=tuple(forward), reverse=tuple(reverse))


def sections_from_content_list(
        items: Iterable[dict]) -> frozenset[str]:
    """Extract every section number from MinerU content_list.json items."""
    sections: set[str] = set()
    for item in items:
        if item.get("type") != "text" or item.get("text_level") is None:
            continue
        match = _cfg().heading_number.match(str(item.get("text", "")))
        if match:
            sections.add(match.group(1))
    return frozenset(sections)


def load_doc_sections(content_list_path: str | Path) -> frozenset[str]:
    """Load the section-number inventory from a content_list.json file."""
    with open(content_list_path, encoding="utf-8") as handle:
        items = json.load(handle)
    return sections_from_content_list(items)


def _row_desc(mapping: TraceMapping) -> str:
    side = "表81" if mapping.direction == "forward" else "表82"
    return (f"{side} row{mapping.row_index}"
            f"({mapping.tb_name}@{mapping.tb_section}"
            f"→{mapping.doc_name}@{mapping.doc_section})")


def _tracked_targets(rows: tuple[TraceMapping, ...],
                     ) -> dict[str, set[str]]:
    """Map doc anchor -> taskbook section set for rows asserting a trace."""
    targets: dict[str, set[str]] = {}
    for mapping in rows:
        if (mapping.tb_section and mapping.doc_section
                and not _is_non_track(mapping.note)):
            targets.setdefault(mapping.doc_section, set()).add(
                mapping.tb_section)
    return targets


def _rows_at(rows: tuple[TraceMapping, ...],
             doc_section: str) -> tuple[TraceMapping, ...]:
    return tuple(m for m in rows
                 if m.doc_section == doc_section and m.tb_section
                 and not _is_non_track(m.note))


def _check_bidirectional(tables: TraceTables) -> list[ClaimResult]:
    forward = _tracked_targets(tables.forward)
    reverse = _tracked_targets(tables.reverse)
    if not forward or not reverse:
        return []
    claims: list[ClaimResult] = []
    for doc_section in sorted(set(forward) & set(reverse)):
        if forward[doc_section] == reverse[doc_section]:
            continue
        fwd_rows = _rows_at(tables.forward, doc_section)
        rev_rows = _rows_at(tables.reverse, doc_section)
        refs = tuple(sorted({m.evidence_id
                             for m in fwd_rows + rev_rows}))
        fwd_desc = "；".join(_row_desc(m) for m in fwd_rows)
        rev_desc = "；".join(_row_desc(m) for m in rev_rows)
        claims.append(ClaimResult(
            claim_id="",
            claim_text=(f"表81与表82对本文档章节{doc_section}的任务书"
                        f"追踪映射一致"),
            verdict="refute",
            check_item_candidates=CHECK_ITEMS,
            evidence_refs=refs,
            rationale=(f"正逆矛盾：{fwd_desc}；{rev_desc}——同一本文档锚点"
                       f"{doc_section}正向指向任务书"
                       f"{sorted(forward[doc_section])}、逆向指向任务书"
                       f"{sorted(reverse[doc_section])}，双向映射不一致"
                       f"（GJB-05）"),
            method=METHOD,
            confidence=1.0,
        ))
    return claims


def _check_anchors(mappings: tuple[TraceMapping, ...],
                   doc_sections: frozenset[str]) -> list[ClaimResult]:
    claims: list[ClaimResult] = []
    seen: set[tuple[str, int, str]] = set()
    for mapping in sorted(mappings, key=lambda m: (m.evidence_id,
                                                   m.row_index)):
        if (not mapping.doc_section or _is_non_track(mapping.note)
                or mapping.doc_section in doc_sections):
            continue
        key = (mapping.evidence_id, mapping.row_index, mapping.doc_section)
        if key in seen:
            continue
        seen.add(key)
        claims.append(ClaimResult(
            claim_id="",
            claim_text=(f"{_row_desc(mapping).split('(')[0]}指向的本文档"
                        f"章节{mapping.doc_section}存在"),
            verdict="refute",
            check_item_candidates=CHECK_ITEMS,
            evidence_refs=(mapping.evidence_id,),
            rationale=(f"锚点失效：{_row_desc(mapping)}，但文档章节清单中"
                       f"不存在章节{mapping.doc_section}"
                       f"（GJB-05追踪锚点无效）"),
            method=METHOD,
            confidence=0.95,
        ))
    return claims


def _check_same_row(mappings: tuple[TraceMapping, ...]) -> list[ClaimResult]:
    rows: dict[tuple[str, str, int], list[TraceMapping]] = {}
    for mapping in mappings:
        if not _is_non_track(mapping.note):
            continue
        key = (mapping.evidence_id, mapping.row_index, mapping.direction)
        rows.setdefault(key, []).append(mapping)
    claims: list[ClaimResult] = []
    for key in sorted(rows):
        group = rows[key]
        note = group[0].note
        desc = "；".join(_row_desc(mapping) for mapping in group)
        claims.append(ClaimResult(
            claim_id="",
            claim_text=(f"{_row_desc(group[0]).split('(')[0]}的追踪映射与"
                        f"跟踪说明「{note}」自洽"),
            verdict="refute",
            check_item_candidates=CHECK_ITEMS,
            evidence_refs=(group[0].evidence_id,),
            rationale=(f"同行矛盾：{desc}映射非空，"
                       f"但跟踪说明列写「{note}」"
                       f"——同一行内映射与声明矛盾（GJB-05）"),
            method=METHOD,
            confidence=1.0,
        ))
    return claims


def _section_tokens(segment: str) -> list[str]:
    return [_norm_section(token)
            for token in _cfg().section_token.findall(segment)]


def _resolve_anchors(segment: str, tokens: list[str],
                     own_anchors: frozenset[str],
                     other_anchors: frozenset[str],
                     sections_by_name: dict[str, set[str]]) -> set[str]:
    hits = {token for token in tokens
            if token in own_anchors and token not in other_anchors}
    if not hits:
        hits = {section for name, sections in sections_by_name.items()
                if len(name) >= 2 and name in segment
                for section in sections}
    return hits


def _answer_trace_pairs(answer: str, tables: TraceTables,
                        ) -> list[tuple[str, str, str]]:
    """Extract (doc_section, tb_section, segment) trace claims from the answer."""
    mappings = tables.all_mappings
    doc_anchors = frozenset(m.doc_section for m in mappings if m.doc_section)
    tb_anchors = frozenset(m.tb_section for m in mappings if m.tb_section)
    doc_names: dict[str, set[str]] = {}
    tb_names: dict[str, set[str]] = {}
    for mapping in mappings:
        if mapping.doc_name and mapping.doc_section:
            doc_names.setdefault(mapping.doc_name, set()).add(
                mapping.doc_section)
        if mapping.tb_name and mapping.tb_section:
            tb_names.setdefault(mapping.tb_name, set()).add(
                mapping.tb_section)
    pairs: list[tuple[str, str, str]] = []
    for raw_segment in _cfg().segment_split.split(answer):
        segment = raw_segment.strip()
        if not segment or not _cfg().relation_words.search(segment):
            continue
        if "任务书" not in segment and not _cfg().trace_relation_words.search(
                segment):
            continue
        tokens = _section_tokens(segment)
        doc_hits = _resolve_anchors(segment, tokens, doc_anchors, tb_anchors,
                                    doc_names)
        tb_hits = {token for token in tokens
                   if token in tb_anchors and token not in doc_anchors}
        tb_hits |= {token for token in tokens
                    if _cfg().taskbook_section.match(token)
                    and token not in doc_anchors}
        if not tb_hits:
            tb_hits = _resolve_anchors(segment, tokens, tb_anchors,
                                        doc_anchors, tb_names)
        if not doc_hits or not tb_hits:
            continue
        if len(doc_hits) * len(tb_hits) > _cfg().max_answer_pairs:
            continue
        for doc_section, tb_section in product(sorted(doc_hits),
                                               sorted(tb_hits)):
            pairs.append((doc_section, tb_section, segment))
    return pairs


def _check_answer_claims(answer: str, tables: TraceTables,
                         ) -> list[ClaimResult]:
    if not answer.strip() or not tables.all_mappings:
        return []
    forward = _tracked_targets(tables.forward)
    reverse = _tracked_targets(tables.reverse)
    claims: list[ClaimResult] = []
    for doc_section, tb_section, segment in _answer_trace_pairs(
            answer, tables):
        refs = tuple(sorted({m.evidence_id
                             for m in _rows_at(tables.forward, doc_section)
                             + _rows_at(tables.reverse, doc_section)}))
        fwd_set = forward.get(doc_section)
        rev_set = reverse.get(doc_section)
        if fwd_set and rev_set and fwd_set != rev_set:
            verdict: Verdict = "refute"
            rationale = (f"正逆矛盾：本文档{doc_section}在表81中追踪至任务书"
                         f"{sorted(fwd_set)}、在表82中追踪至任务书"
                         f"{sorted(rev_set)}；无论answer取哪一侧，"
                         f"另一半证据都反对该追溯关系（GJB-05）")
            confidence = 1.0
        elif fwd_set and rev_set:
            if tb_section in fwd_set:
                verdict = "support"
                rationale = (f"表81与表82均支持本文档{doc_section}→"
                             f"任务书{tb_section}的追溯关系（GJB-05）")
                confidence = 1.0
            else:
                verdict = "refute"
                rationale = (f"表81与表82一致指向本文档{doc_section}→"
                             f"任务书{sorted(fwd_set)}，"
                             f"与answer声称的任务书{tb_section}不符（GJB-05）")
                confidence = 1.0
        else:
            verdict = "not_in_evidence"
            rationale = (f"冻结证据中本文档{doc_section}缺少双向追踪支持"
                         f"（正向{'有' if fwd_set else '无'}映射、"
                         f"逆向{'有' if rev_set else '无'}映射），"
                         f"无法确认表81和表82都支持该追溯关系")
            confidence = 0.0
        claims.append(ClaimResult(
            claim_id="",
            claim_text=segment,
            verdict=verdict,
            check_item_candidates=CHECK_ITEMS,
            evidence_refs=refs,
            rationale=rationale,
            method=METHOD,
            confidence=confidence,
        ))
    return claims


def verify_trace(request: QAInput,
                 doc_sections: Iterable[str] | None = None,
                 ) -> list[ClaimResult]:
    """Run the GJB-05 bidirectional trace join checks on a frozen QA input.

    ``doc_sections`` is the document's section-number inventory (see
    ``load_doc_sections``); when omitted the anchor-validity check is
    skipped. Returns deterministic ClaimResults with
    method="trace_bidirectional_join"; returns [] when the evidence holds
    no recognizable trace table.
    """
    tables = parse_trace_tables(request.evidence)
    if not tables.all_mappings:
        return []
    claims: list[ClaimResult] = []
    claims.extend(_check_bidirectional(tables))
    if doc_sections is not None:
        claims.extend(_check_anchors(tables.all_mappings,
                                     frozenset(doc_sections)))
    claims.extend(_check_same_row(tables.all_mappings))
    claims.extend(_check_answer_claims(request.answer, tables))
    return [
        replace(claim, claim_id=f"{request.instance_id}-trace{index:02d}")
        for index, claim in enumerate(claims, start=1)
    ]


__all__ = [
    "CHECK_ITEMS",
    "METHOD",
    "TraceMapping",
    "TraceTables",
    "load_doc_sections",
    "parse_trace_tables",
    "sections_from_content_list",
    "verify_trace",
]
