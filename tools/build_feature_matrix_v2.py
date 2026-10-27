#!/usr/bin/env python3
"""Build feature matrix v2: fill the sentence/table cells missing in v1.

Supplements tools/build_feature_matrix.py (v1) without modifying it:

    1. sentence char spans      text_claim raw_text located in the original
                                content_list blocks -> {block_idx, start, end};
                                whitespace-normalized fallback; unlocated as-is
    2. negation positions       word + char position per sentence
    3. condition extraction     当X时 / 若X则 / 如果X则 / 在X(情况|条件)下
    4. figure/table references  "图N/表N" resolved to image/table ids via
                                caption prefix matching
    5. multi-level header tree  rowspan/colspan header cells expanded into a
                                nested parent->children tree
    6. cell coordinates         cell_id "{table_id}:r{row}c{col}" grid cells
    7. scope entity candidates  dictionary-style 模块/服务/接口/分系统 suffix
                                pattern with shallow-prefix stripping

Inputs (read-only):
    data/gjb_438c/structured_corpus_v1/{documents,sections,claims,tables,
    images,observations}.jsonl
    data/gjb_438c/mineru_standard/<doc>/office/*_content_list.json

Outputs (data/gjb_438c/feature_matrix_v2):
    sentences.jsonl / tables_v2.jsonl / references_resolved.jsonl /
    summary.json / manifest.json

Usage:
    python tools/build_feature_matrix_v2.py
    python tools/build_feature_matrix_v2.py --limit 2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.build_feature_matrix import (
        caption_key,
        grid_from_rows,
        parse_grid_table,
        reference_key,
    )
except ImportError:
    from build_feature_matrix import (
        caption_key,
        grid_from_rows,
        parse_grid_table,
        reference_key,
    )

BASE = Path(__file__).resolve().parent.parent
CORPUS_DIR = BASE / "data/gjb_438c/structured_corpus_v1"
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/feature_matrix_v2"
SCHEMA_VERSION = "feature_matrix_v2"

NEGATION_WORDS: tuple[str, ...] = (
    "不得",
    "不能",
    "禁止",
    "不允许",
    "无法",
    "除外",
    "不应",
    "严禁",
)

CONDITION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("当…时", re.compile(r"当(.{2,30}?)时")),
    ("若…则", re.compile(r"若(.{2,30}?)则")),
    ("如果…则", re.compile(r"如果(.{2,30}?)则")),
    ("在…下", re.compile(r"在.{2,30}?(情况|条件)下")),
)

SCOPE_ENTITY_RE = re.compile(r"([\u4e00-\u9fff]{2,10})(模块|服务|接口|分系统)")
SCOPE_HEAD_STRIP_WORDS: tuple[str, ...] = (
    "其中", "其他", "其它", "另外", "任何", "任意", "所有", "相应",
    "各个", "每个", "某个", "上述", "下述", "以下", "提供", "支持",
    "基于", "通过", "使用", "利用", "包括", "需要", "要求", "针对",
    "关于", "实现", "进行", "直接", "间接", "加载", "完成",
)
SCOPE_HEAD_STRIP_CHARS = "与和或及对由从被将在把为其该本某各每就还又也都而并之"
SCOPE_TAIL_STRIP_CHARS = "的了"
SCOPE_HEAD_STRIP_ORDERED: tuple[str, ...] = tuple(
    sorted(SCOPE_HEAD_STRIP_WORDS, key=len, reverse=True)
)

THEAD_RE = re.compile(r"<thead>(.*?)</thead>", re.S)
TR_RE = re.compile(r"<tr\b")


# ---------------------------------------------------------------------------
# pure feature extractors (testable on synthetic data)
# ---------------------------------------------------------------------------


def collapse_with_map(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace runs to single spaces, keeping original offsets.

    Returns (normalized_text, positions) where positions[i] is the index in
    the original text of the i-th normalized character.
    """
    out: list[str] = []
    positions: list[int] = []
    prev_space = True
    for index, char in enumerate(text):
        if char.isspace():
            if prev_space:
                continue
            out.append(" ")
            positions.append(index)
            prev_space = True
        else:
            out.append(char)
            positions.append(index)
            prev_space = False
    while out and out[-1] == " ":
        out.pop()
        positions.pop()
    return "".join(out), positions


def find_sentence_span(
    blocks: list[tuple[int, str]],
    raw_text: str,
    preferred_block: int | None = None,
) -> dict[str, Any]:
    """Locate raw_text inside the original blocks.

    blocks: (block_idx, block_text) pairs in content-list order. The block
    pinned by the claim's source observation is searched first. Exact find
    wins over the whitespace-normalized fallback. Span end is exclusive.
    """
    order = list(range(len(blocks)))
    if preferred_block is not None:
        order.sort(key=lambda i: 0 if blocks[i][0] == preferred_block else 1)
    for i in order:
        block_idx, block_text = blocks[i]
        pos = block_text.find(raw_text)
        if pos >= 0:
            return {
                "block_idx": block_idx,
                "start": pos,
                "end": pos + len(raw_text),
                "status": "located",
            }
    for i in order:
        block_idx, block_text = blocks[i]
        normalized, positions = collapse_with_map(block_text)
        pos = normalized.find(raw_text)
        if pos >= 0 and pos + len(raw_text) <= len(positions):
            return {
                "block_idx": block_idx,
                "start": positions[pos],
                "end": positions[pos + len(raw_text) - 1] + 1,
                "status": "located_normalized",
            }
    return {"block_idx": None, "start": None, "end": None, "status": "unlocated"}


def find_negations(text: str) -> list[dict[str, Any]]:
    """Negation word hits with char positions, sorted by position."""
    hits: list[dict[str, Any]] = []
    for word in NEGATION_WORDS:
        for match in re.finditer(re.escape(word), text):
            hits.append({"word": word, "pos": match.start()})
    hits.sort(key=lambda item: (item["pos"], item["word"]))
    return hits


def find_conditions(text: str) -> list[dict[str, Any]]:
    """Condition clause hits: {pattern, raw, cond_text, pos}."""
    hits: list[dict[str, Any]] = []
    for name, pattern in CONDITION_PATTERNS:
        for match in pattern.finditer(text):
            if name == "在…下":
                cond_text = match.group(0)[1:-1]
            else:
                cond_text = match.group(1)
            hits.append(
                {
                    "pattern": name,
                    "raw": match.group(0),
                    "cond_text": cond_text,
                    "pos": match.start(),
                }
            )
    hits.sort(key=lambda item: (item["pos"], item["raw"]))
    return hits


def _normalize_scope_prefix(prefix: str) -> str:
    """Strip shallow function words/chars from the head and possessive tail."""
    text = prefix
    changed = True
    while changed and text:
        changed = False
        for word in SCOPE_HEAD_STRIP_ORDERED:
            if text.startswith(word):
                text = text[len(word) :]
                changed = True
                break
        if text and text[0] in SCOPE_HEAD_STRIP_CHARS:
            text = text[1:]
            changed = True
    while text and text[-1] in SCOPE_TAIL_STRIP_CHARS:
        text = text[:-1]
    return text


def find_scope_entities(text: str) -> list[dict[str, Any]]:
    """Entity candidates from the XX模块/XX服务/XX接口/XX分系统 pattern."""
    out: list[dict[str, Any]] = []
    for match in SCOPE_ENTITY_RE.finditer(text):
        prefix = _normalize_scope_prefix(match.group(1))
        if len(prefix) < 2:
            continue
        out.append(
            {
                "raw": match.group(0),
                "entity": prefix + match.group(2),
                "pos": match.start(),
            }
        )
    return out


def build_sentence_row(
    claim: dict[str, Any],
    blocks: list[tuple[int, str]],
    obs_block: dict[str, int | None],
) -> dict[str, Any]:
    """Compose the sentences.jsonl row for one text_claim."""
    text = str(claim.get("raw_text", ""))
    preferred: int | None = None
    obs_ids = claim.get("source_observation_ids") or []
    if obs_ids:
        pinned = obs_block.get(str(obs_ids[0]))
        if isinstance(pinned, int):
            preferred = pinned
    span = find_sentence_span(blocks, text, preferred)
    negations = find_negations(text)
    conditions = find_conditions(text)
    scope_entity = find_scope_entities(text)
    return {
        "claim_id": str(claim.get("claim_id", "")),
        "doc_id": str(claim.get("doc_id", "")),
        "section": str(claim.get("section", "")),
        "text": text,
        "span": {
            "block_idx": span["block_idx"],
            "start": span["start"],
            "end": span["end"],
        },
        "span_status": str(span["status"]),
        "negations": negations,
        "conditions": conditions,
        "has_condition": bool(conditions),
        "scope_candidate": str(claim.get("section", "")),
        "scope_entity": scope_entity,
    }


# ---------------------------------------------------------------------------
# table structure features
# ---------------------------------------------------------------------------


def count_thead_rows(html_body: str) -> int:
    """Number of <tr> rows inside <thead>; 0 when no thead is present."""
    match = THEAD_RE.search(html_body or "")
    if match is None:
        return 0
    return len(TR_RE.findall(match.group(1)))


def _header_node(cell: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": str(cell.get("text", "")),
        "rowspan": int(cell.get("rowspan", 1)),
        "colspan": int(cell.get("colspan", 1)),
        "children": [],
    }


def build_header_tree(grid: dict[str, Any], thead_rows: int) -> dict[str, Any]:
    """Expand merged header cells into a nested parent->children tree.

    Header region = thead rows (first grid row when no thead), extended by
    rowspans starting inside it. Nested expansion only happens when the
    header region both contains merged cells and spans >1 row; otherwise the
    tree stays single-level (flat first-row cells with merge info).
    """
    occupied = grid["occupied"]
    cells = grid["cells"]
    n_cols = int(grid["n_cols"])
    header_rows = max(thead_rows, 1)
    header_cells = [cell for cell in cells if cell["row"] < header_rows]
    depth = max(
        [header_rows] + [cell["row"] + cell["rowspan"] for cell in header_cells]
    )
    has_merge = any(
        cell["rowspan"] > 1 or cell["colspan"] > 1 for cell in header_cells
    )
    if depth <= 1 or not has_merge:
        nodes: list[dict[str, Any]] = []
        seen: set[int] = set()
        for col in range(n_cols):
            cell = occupied.get((0, col))
            if cell is None or id(cell) in seen:
                continue
            seen.add(id(cell))
            nodes.append(_header_node(cell))
        return {"levels": 1, "multi_level": False, "nodes": nodes}
    node_by_cell: dict[int, dict[str, Any]] = {}
    roots: list[dict[str, Any]] = []
    max_depth = 1
    for col in range(n_cols):
        path: list[dict[str, Any]] = []
        prev: dict[str, Any] | None = None
        for row in range(depth):
            cell = occupied.get((row, col))
            if cell is None:
                prev = None
                continue
            if cell is prev:
                continue
            path.append(cell)
            prev = cell
        max_depth = max(max_depth, len(path))
        children = roots
        for cell in path:
            node = node_by_cell.get(id(cell))
            if node is None:
                node = _header_node(cell)
                node_by_cell[id(cell)] = node
                children.append(node)
            children = node["children"]
    return {"levels": max_depth, "multi_level": True, "nodes": roots}


def build_table_cells(table_id: str, grid: dict[str, Any]) -> list[dict[str, Any]]:
    """Grid origin cells with coordinate ids: {table_id}:r{row}c{col}."""
    cells = [
        {
            "cell_id": f"{table_id}:r{cell['row']}c{cell['col']}",
            "row": int(cell["row"]),
            "col": int(cell["col"]),
            "text": str(cell.get("text", "")),
            "is_merged_origin": bool(cell["rowspan"] > 1 or cell["colspan"] > 1),
            "rowspan": int(cell["rowspan"]),
            "colspan": int(cell["colspan"]),
        }
        for cell in grid["cells"]
    ]
    cells.sort(key=lambda item: (item["row"], item["col"]))
    return cells


def build_table_row_v2(table: dict[str, Any], html_body: str) -> dict[str, Any]:
    """Compose the tables_v2.jsonl row for one table."""
    rows = table.get("rows") or []
    source = "content_list_html"
    if html_body:
        grid = parse_grid_table(html_body)
        if not grid["cells"]:
            grid = grid_from_rows(rows)
            source = "rows_fallback"
    else:
        grid = grid_from_rows(rows)
        source = "rows_fallback"
    thead_rows = count_thead_rows(html_body)
    tree = build_header_tree(grid, thead_rows)
    cells = build_table_cells(str(table.get("table_id", "")), grid)
    return {
        "table_id": str(table.get("table_id", "")),
        "doc_id": str(table.get("doc_id", "")),
        "section": str(table.get("section", "")),
        "caption_raw": str(table.get("caption_raw", "")),
        "page": table.get("page"),
        "n_rows": int(grid["n_rows"]),
        "n_cols": int(grid["n_cols"]),
        "source": source,
        "thead_rows": thead_rows,
        "header_levels": int(tree["levels"]),
        "multi_level_header": bool(tree["multi_level"]),
        "header_tree": tree,
        "n_cells": len(cells),
        "cells": cells,
    }


# ---------------------------------------------------------------------------
# reference resolution
# ---------------------------------------------------------------------------


def build_caption_index(
    images: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    doc_set: set[str],
) -> tuple[dict[tuple[str, str, str], str], int]:
    """Index (doc_id, 图/表, number) -> target id via caption prefix keys."""
    index: dict[tuple[str, str, str], str] = {}
    duplicates = 0
    for row in images:
        doc_id = str(row.get("doc_id", ""))
        if doc_id not in doc_set:
            continue
        key = caption_key(str(row.get("caption_raw", "")))
        if key is None:
            continue
        slot = (doc_id, key[0], key[1])
        if slot in index:
            duplicates += 1
        else:
            index[slot] = str(row.get("image_id", ""))
    for row in tables:
        doc_id = str(row.get("doc_id", ""))
        if doc_id not in doc_set:
            continue
        key = caption_key(str(row.get("caption_raw", "")))
        if key is None:
            continue
        slot = (doc_id, key[0], key[1])
        if slot in index:
            duplicates += 1
        else:
            index[slot] = str(row.get("table_id", ""))
    return index, duplicates


def resolve_reference(
    ref: str, doc_id: str, index: dict[tuple[str, str, str], str]
) -> dict[str, Any]:
    """Resolve one 图N/表N reference against the caption index."""
    key = reference_key(ref)
    target = None
    if key is not None:
        target = index.get((doc_id, key[0], key[1]))
    return {
        "ref": ref,
        "target_id": target,
        "status": "resolved" if target else "unresolved",
    }


# ---------------------------------------------------------------------------
# build pipeline
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tracked_jsonl(path: Path, inputs: dict[str, str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    inputs[str(path.relative_to(BASE))] = sha256_file(path)
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _tracked_json(path: Path, default: Any, inputs: dict[str, str]) -> Any:
    if not path.exists():
        return default
    inputs[str(path.relative_to(BASE))] = sha256_file(path)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def _resolve_content_path(doc: dict[str, Any], doc_name: str) -> Path:
    rel = str((doc.get("asset") or {}).get("content_list") or "")
    if rel:
        return BASE / rel
    return MINERU_DIR / doc_name / "office" / f"{doc_name}_content_list.json"


def _group_by_doc(
    rows: list[dict[str, Any]], doc_set: set[str]
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        doc_id = str(row.get("doc_id", ""))
        if doc_id in doc_set:
            grouped.setdefault(doc_id, []).append(row)
    return grouped


def build(output: Path, limit: int | None = None) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    inputs: dict[str, str] = {}
    documents = _tracked_jsonl(CORPUS_DIR / "documents.jsonl", inputs)
    sections = _tracked_jsonl(CORPUS_DIR / "sections.jsonl", inputs)
    claims = _tracked_jsonl(CORPUS_DIR / "claims.jsonl", inputs)
    tables = _tracked_jsonl(CORPUS_DIR / "tables.jsonl", inputs)
    images = _tracked_jsonl(CORPUS_DIR / "images.jsonl", inputs)
    observations = _tracked_jsonl(CORPUS_DIR / "observations.jsonl", inputs)

    doc_order = [str(doc.get("doc_id", "")) for doc in documents]
    if limit is not None:
        doc_order = doc_order[: max(0, limit)]
    doc_set = set(doc_order)
    documents_by_id = {str(doc.get("doc_id", "")): doc for doc in documents}
    doc_name_by_id = {str(doc.get("doc_id", "")): str(doc.get("doc_name", "")) for doc in documents}

    obs_block: dict[str, int | None] = {}
    for row in observations:
        source_ref = row.get("source_ref") or {}
        item_index = source_ref.get("item_index")
        obs_block[str(row.get("observation_id", ""))] = (
            item_index if isinstance(item_index, int) else None
        )

    claims_by_doc = _group_by_doc(claims, doc_set)
    tables_by_doc = _group_by_doc(tables, doc_set)
    caption_index, ambiguous_keys = build_caption_index(images, tables, doc_set)

    n_sections_by_doc: dict[str, int] = {}
    for row in sections:
        doc_id = str((row.get("source_ref") or {}).get("doc_id", ""))
        if doc_id in doc_set:
            n_sections_by_doc[doc_id] = n_sections_by_doc.get(doc_id, 0) + 1

    sentence_rows: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []

    for doc_id in doc_order:
        doc_name = doc_name_by_id.get(doc_id, "")
        content = _tracked_json(
            _resolve_content_path(documents_by_id.get(doc_id, {}), doc_name), [], inputs
        )
        blocks = [
            (item_index, str(block.get("text", "")))
            for item_index, block in enumerate(content)
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        bodies = [
            str(block.get("table_body", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "table"
        ]
        for claim in claims_by_doc.get(doc_id, []):
            if claim.get("kind") != "text_claim":
                continue
            sentence_rows.append(build_sentence_row(claim, blocks, obs_block))
        doc_tables = tables_by_doc.get(doc_id, [])
        for table_index, table in enumerate(doc_tables):
            body = bodies[table_index] if table_index < len(bodies) else ""
            table_rows.append(build_table_row_v2(table, body))
        for claim in claims_by_doc.get(doc_id, []):
            claim_id = str(claim.get("claim_id", ""))
            for ref in (claim.get("features") or {}).get("references") or []:
                resolved = resolve_reference(str(ref), doc_id, caption_index)
                reference_rows.append(
                    {
                        "claim_id": claim_id,
                        "doc_id": doc_id,
                        "ref": resolved["ref"],
                        "target_id": resolved["target_id"],
                        "status": resolved["status"],
                    }
                )

    files = {
        "sentences": write_jsonl(output / "sentences.jsonl", sentence_rows),
        "tables_v2": write_jsonl(output / "tables_v2.jsonl", table_rows),
        "references_resolved": write_jsonl(
            output / "references_resolved.jsonl", reference_rows
        ),
    }

    n_sentences = len(sentence_rows)
    span_status_counts = Counter(row["span_status"] for row in sentence_rows)
    located = span_status_counts["located"] + span_status_counts["located_normalized"]
    negation_by_word = Counter(
        item["word"] for row in sentence_rows for item in row["negations"]
    )
    condition_by_pattern = Counter(
        item["pattern"] for row in sentence_rows for item in row["conditions"]
    )
    scope_entities = {
        item["entity"] for row in sentence_rows for item in row["scope_entity"]
    }
    ref_status = Counter(row["status"] for row in reference_rows)
    ref_by_kind = Counter(
        key[0]
        for key in (
            reference_key(str(row["ref"])) for row in reference_rows
        )
        if key is not None
    )
    levels_distribution = Counter(row["header_levels"] for row in table_rows)
    source_counts = Counter(row["source"] for row in table_rows)
    total_cells = sum(row["n_cells"] for row in table_rows)
    merged_origin_cells = sum(
        1 for row in table_rows for cell in row["cells"] if cell["is_merged_origin"]
    )
    n_references = len(reference_rows)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "builder": "tools/build_feature_matrix_v2.py",
        "counts": {
            "documents": len(doc_order),
            "sections": sum(n_sections_by_doc.values()),
            "sentences": n_sentences,
            "tables_v2": len(table_rows),
            "references_resolved": n_references,
            **files,
        },
        "span_stats": {
            "n_sentences": n_sentences,
            "located": span_status_counts["located"],
            "located_normalized": span_status_counts["located_normalized"],
            "unlocated": span_status_counts["unlocated"],
            "span_location_rate": round(located / n_sentences, 4) if n_sentences else 0.0,
        },
        "negation_stats": {
            "n_hits": sum(negation_by_word.values()),
            "n_sentences_with_negation": sum(
                1 for row in sentence_rows if row["negations"]
            ),
            "by_word": dict(sorted(negation_by_word.items())),
        },
        "condition_stats": {
            "n_hits": sum(condition_by_pattern.values()),
            "n_sentences_with_condition": sum(
                1 for row in sentence_rows if row["has_condition"]
            ),
            "condition_hit_rate": round(
                sum(1 for row in sentence_rows if row["has_condition"]) / n_sentences, 4
            )
            if n_sentences
            else 0.0,
            "by_pattern": dict(sorted(condition_by_pattern.items())),
        },
        "scope_stats": {
            "n_hits": sum(len(row["scope_entity"]) for row in sentence_rows),
            "n_sentences_with_scope_entity": sum(
                1 for row in sentence_rows if row["scope_entity"]
            ),
            "n_distinct_entities": len(scope_entities),
        },
        "reference_stats": {
            "n_references": n_references,
            "resolved": ref_status["resolved"],
            "unresolved": ref_status["unresolved"],
            "resolution_rate": round(ref_status["resolved"] / n_references, 4)
            if n_references
            else 0.0,
            "by_kind": dict(sorted(ref_by_kind.items())),
            "ambiguous_caption_keys": ambiguous_keys,
        },
        "table_stats": {
            "n_tables": len(table_rows),
            "source_counts": dict(sorted(source_counts.items())),
            "multi_level_header_tables": sum(
                1 for row in table_rows if row["multi_level_header"]
            ),
            "header_levels_distribution": {
                str(level): count
                for level, count in sorted(levels_distribution.items())
            },
            "total_cells": total_cells,
            "avg_cells_per_table": round(total_cells / len(table_rows), 4)
            if table_rows
            else 0.0,
            "merged_origin_cells": merged_origin_cells,
        },
        "input_assets": dict(sorted(inputs.items())),
        "policy": {
            "span_is_candidate_not_gold": True,
            "scope_entity_is_dictionary_heuristic": True,
            "header_tree_is_structural_expansion": True,
            "reference_resolution_requires_caption_prefix_match": True,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "files": {name: sha256_file(output / f"{name}.jsonl") for name in files},
        "summary_sha256": sha256_file(output / "summary.json"),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    summary = build(args.output.resolve(), args.limit)
    print(
        json.dumps(
            {
                "counts": summary["counts"],
                "span_stats": summary["span_stats"],
                "condition_stats": summary["condition_stats"],
                "reference_stats": summary["reference_stats"],
                "table_stats": summary["table_stats"],
                "scope_stats": summary["scope_stats"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
