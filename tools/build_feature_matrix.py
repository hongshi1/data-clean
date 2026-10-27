#!/usr/bin/env python3
"""Build the seven-class structural feature matrix from the structured corpus.

Inputs (read-only):
    data/gjb_438c/structured_corpus_v1/*.jsonl        (sections/requirements/claims/
                                                       tables/images/diagrams/diagram_nodes)
    data/gjb_438c/mineru_standard/<doc>/office/*_content_list.json
                                                      (table_body HTML with colspan/rowspan,
                                                       matched to tables.jsonl by table order)
    data/gjb_438c/anchor_v3/anchors_v3.json           (visio structures)
    data/gjb_438c/anchor_v2/scene_models.json         (diagram type semantics)
    knowledge/srs_kb.json                             (param/unit dictionaries)
    data/gjb_438c/evidence_graph_v2/links_v2.jsonl    (alignment links, passed through)

Outputs (data/gjb_438c/feature_matrix_v1):
    document_features / text_features / table_features / visio_features /
    diagram_semantic_features / claim_slot_features / quality_features /
    alignment_features (.jsonl) + summary.json + manifest.json

Usage:
    python tools/build_feature_matrix.py
    python tools/build_feature_matrix.py --output data/gjb_438c/feature_matrix_v1
    python tools/build_feature_matrix.py --limit 2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.build_structured_corpus import clean_text, stable_id
except ImportError:
    from build_structured_corpus import clean_text, stable_id

BASE = Path(__file__).resolve().parent.parent
CORPUS_DIR = BASE / "data/gjb_438c/structured_corpus_v1"
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
ANCHOR_V3_PATH = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
SCENE_MODELS_PATH = BASE / "data/gjb_438c/anchor_v2/scene_models.json"
KB_PATH = BASE / "knowledge/srs_kb.json"
LINKS_V2_PATH = BASE / "data/gjb_438c/evidence_graph_v2/links_v2.jsonl"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/feature_matrix_v1"
SCHEMA_VERSION = "feature_matrix_v1"

REQ_ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
USECASE_ROW_RE = re.compile(r"Actor|概述|前置|主事件流|异常流|后置")
REF_KIND_RE = re.compile(r"([图表])\s*(\d+(?:[-－]\d+)?)")
CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9·．\-/]*")
SUBJECT_SPLIT_RE = re.compile(r"[，。、；：,;:！？!?\s()（）\[\]【】]+")
SUBJECT_STRIP_CHARS = "的了之其应当必须须需可不宜将和与及"

DASH_VALUES = {"—", "-", "－", "–", "―"}

OPERATOR_CANON: dict[str, str] = {
    "不超过": "<=",
    "不大于": "<=",
    "小于等于": "<=",
    "至多": "<=",
    "最多": "<=",
    "≤": "<=",
    "<=": "<=",
    "不小于": ">=",
    "不低于": ">=",
    "大于等于": ">=",
    "至少": ">=",
    "≥": ">=",
    ">=": ">=",
    "小于": "<",
    "大于": ">",
    "等于": "=",
    "=": "=",
    "<": "<",
    ">": ">",
}

CN_UNIT_ALIASES: dict[str, str] = {
    "毫秒": "time",
    "微秒": "time",
    "纳秒": "time",
    "秒": "time",
    "分钟": "time",
    "小时": "time",
    "字节": "storage",
    "比特": "storage",
    "赫兹": "frequency",
    "千赫": "frequency",
    "兆赫": "frequency",
}

TYPE_SPECIFIC_FIELDS: dict[str, tuple[str, ...]] = {
    "flowchart": ("direction", "steps", "main_path", "decisions", "exception_flows"),
    "usecase_diagram": (
        "boundaries",
        "usecases",
        "primary_actors",
        "external_systems",
        "associations",
        "uc_relations",
    ),
    "interface_diagram": ("systems", "interfaces", "connections"),
}

SLOT_FIELDS: tuple[str, ...] = (
    "subject_candidate",
    "predicate_candidate",
    "operator",
    "object_value",
    "unit_raw",
    "scope_candidate",
)


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


def _span_value(raw: str | None) -> int:
    try:
        value = int(str(raw or "1").strip())
    except ValueError:
        return 1
    return value if value > 1 else 1


class GridTableParser(HTMLParser):
    """HTML table parser that preserves rowspan/colspan grid coordinates.

    Rows without any td/th are skipped, matching the row semantics of
    tools/build_structured_corpus.py, so grid row indices stay aligned with
    the rows stored in tables.jsonl.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[dict[str, Any]] = []
        self.occupied: dict[tuple[int, int], dict[str, Any]] = {}
        self.n_rows = 0
        self.n_cols = 0
        self._row: int | None = None
        self._col = 0
        self._cell: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = None
            self._col = 0
        elif tag in {"td", "th"} and self._cell is None:
            if self._row is None:
                self._row = self.n_rows
                self.n_rows += 1
            while (self._row, self._col) in self.occupied:
                self._col += 1
            attr_map = {key.lower(): value for key, value in attrs}
            self._cell = {
                "row": self._row,
                "col": self._col,
                "rowspan": _span_value(attr_map.get("rowspan")),
                "colspan": _span_value(attr_map.get("colspan")),
                "parts": [],
            }

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None:
            cell = self._cell
            cell["text"] = clean_text(" ".join(cell.pop("parts")))
            self.cells.append(cell)
            for delta_row in range(cell["rowspan"]):
                for delta_col in range(cell["colspan"]):
                    self.occupied[(cell["row"] + delta_row, cell["col"] + delta_col)] = cell
            self.n_cols = max(self.n_cols, cell["col"] + cell["colspan"])
            self._col += cell["colspan"]
            self._cell = None


def parse_grid_table(html_body: str) -> dict[str, Any]:
    parser = GridTableParser()
    parser.feed(html_body or "")
    return {
        "cells": parser.cells,
        "occupied": parser.occupied,
        "n_rows": parser.n_rows,
        "n_cols": parser.n_cols,
    }


def grid_from_rows(rows: list[list[str]]) -> dict[str, Any]:
    """Fallback grid without merge info, built from plain ragged rows."""
    cells: list[dict[str, Any]] = []
    occupied: dict[tuple[int, int], dict[str, Any]] = {}
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            cell = {
                "row": row_index,
                "col": col_index,
                "rowspan": 1,
                "colspan": 1,
                "text": clean_text(value),
            }
            cells.append(cell)
            occupied[(row_index, col_index)] = cell
    return {
        "cells": cells,
        "occupied": occupied,
        "n_rows": len(rows),
        "n_cols": max((len(row) for row in rows), default=0),
    }


def merged_cells(grid: dict[str, Any]) -> list[dict[str, Any]]:
    out = [
        {
            "row_index": cell["row"],
            "col_index": cell["col"],
            "rowspan": cell["rowspan"],
            "colspan": cell["colspan"],
        }
        for cell in grid["cells"]
        if cell["rowspan"] > 1 or cell["colspan"] > 1
    ]
    out.sort(key=lambda item: (item["row_index"], item["col_index"]))
    return out


def classify_empty_text(text: str) -> str | None:
    value = (text or "").strip()
    if value == "":
        return "empty"
    if value in DASH_VALUES:
        return "dash"
    return None


def build_empty_cells(grid: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row_index in range(grid["n_rows"]):
        for col_index in range(grid["n_cols"]):
            cell = grid["occupied"].get((row_index, col_index))
            if cell is None:
                out.append({"row_index": row_index, "col_index": col_index, "state": "empty"})
            elif (cell["row"], cell["col"]) != (row_index, col_index):
                out.append(
                    {"row_index": row_index, "col_index": col_index, "state": "inherit_candidate"}
                )
            else:
                state = classify_empty_text(str(cell.get("text", "")))
                if state:
                    out.append({"row_index": row_index, "col_index": col_index, "state": state})
    return out


def classify_row_role(first_column_text: str) -> str:
    text = clean_text(first_column_text)
    if REQ_ID_RE.search(text):
        return "requirement_row"
    if text and text.isdigit():
        return "index_row"
    if USECASE_ROW_RE.search(text):
        return "usecase_section_row"
    return "data_row"


def build_row_roles(grid: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row_index in range(grid["n_rows"]):
        cell = grid["occupied"].get((row_index, 0))
        first = str(cell.get("text", "")) if cell else ""
        out.append({"row_index": row_index, "role_candidate": classify_row_role(first)})
    return out


def scan_requirement_id_cells(grid: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cell in grid["cells"]:
        for match in REQ_ID_RE.finditer(str(cell.get("text", ""))):
            out.append(
                {"row_index": cell["row"], "col_index": cell["col"], "value": match.group(0)}
            )
    return out


def build_param_index(param_dictionary: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key, spec in (param_dictionary or {}).items():
        if not isinstance(spec, dict):
            continue
        canonical = str(spec.get("canonical_cn") or "")
        synonyms = {canonical}
        for synonym in spec.get("synonyms_cn") or []:
            synonyms.add(str(synonym))
        for synonym in sorted(synonym for synonym in synonyms if synonym):
            entries.append(
                {
                    "synonym": synonym,
                    "predicate_key": str(key),
                    "canonical_cn": canonical,
                    "default_unit": str(spec.get("default_unit") or ""),
                }
            )
    entries.sort(key=lambda entry: (-len(entry["synonym"]), entry["predicate_key"], entry["synonym"]))
    return entries


def match_predicate(text: str, param_index: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for entry in param_index:
        position = text.find(entry["synonym"])
        if position < 0:
            continue
        candidate = {**entry, "position": position}
        if best is None or (-len(candidate["synonym"]), candidate["position"]) < (
            -len(best["synonym"]),
            best["position"],
        ):
            best = candidate
    return best


def scan_parameter_cells(
    grid: dict[str, Any], param_index: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for cell in grid["cells"]:
        hit = match_predicate(str(cell.get("text", "")), param_index)
        if hit:
            out.append(
                {
                    "row_index": cell["row"],
                    "col_index": cell["col"],
                    "value": hit["synonym"],
                    "predicate_key": hit["predicate_key"],
                }
            )
    return out


def normalize_operator(operator_raw: str) -> str:
    return OPERATOR_CANON.get((operator_raw or "").strip(), "")


def build_unit_families(unit_dictionary: dict[str, Any]) -> dict[str, str]:
    families: dict[str, str] = {}
    for family, spec in (unit_dictionary or {}).items():
        if not isinstance(spec, dict):
            continue
        units = list(spec.get("units") or [])
        units.extend((spec.get("conversions") or {}).keys())
        for unit in units:
            families[str(unit).strip().lower()] = str(family)
    for cn_unit, family in CN_UNIT_ALIASES.items():
        families.setdefault(cn_unit, family)
    return families


def units_convertible(unit_raw: str, unit_canonical: str, families: dict[str, str]) -> bool:
    raw = (unit_raw or "").strip()
    canonical = (unit_canonical or "").strip()
    if not raw or not canonical:
        return False
    if raw.lower() == canonical.lower():
        return True
    raw_family = families.get(raw) or families.get(raw.lower())
    canonical_family = families.get(canonical) or families.get(canonical.lower())
    return bool(raw_family and canonical_family and raw_family == canonical_family)


def nearest_subject_before(text: str, position: int | None) -> str:
    if position is None or position <= 0:
        return ""
    prefix = text[:position].strip()
    if not prefix:
        return ""
    segments = [segment for segment in SUBJECT_SPLIT_RE.split(prefix) if segment]
    tail = segments[-1] if segments else ""
    tail = tail.rstrip(SUBJECT_STRIP_CHARS)
    matches = CJK_RUN_RE.findall(tail)
    if not matches:
        return ""
    phrase = matches[-1]
    return phrase if len(phrase) >= 2 else ""


def subject_from_row_cells(row_cells: list[str]) -> str:
    cleaned = [clean_text(cell) for cell in row_cells[:2]]
    for cell in cleaned:
        if cell and cell not in DASH_VALUES and re.search(r"[\u4e00-\u9fff]", cell):
            return cell
    for cell in cleaned:
        if cell and cell not in DASH_VALUES:
            return cell
    return ""


def select_quantity(
    quantities: list[dict[str, Any]], raw_text: str, position: int | None
) -> dict[str, Any] | None:
    if not quantities:
        return None
    if position is not None:
        tail = raw_text[position:]
        candidates = []
        for quantity in quantities:
            probes = [str(quantity.get("raw") or ""), str(quantity.get("value") or "")]
            if any(probe and probe in tail for probe in probes):
                candidates.append(quantity)
        for quantity in candidates:
            if str(quantity.get("operator_raw") or "").strip() or str(
                quantity.get("unit_raw")
            ).strip():
                return quantity
        if candidates:
            return candidates[0]
    return quantities[0]


def build_claim_slot_row(
    claim: dict[str, Any],
    param_index: list[dict[str, Any]],
    unit_families: dict[str, str],
    section_title: str,
    row_cells: list[str],
) -> dict[str, Any]:
    raw_text = str(claim.get("raw_text", ""))
    features = claim.get("features") or {}
    quantities = [item for item in (features.get("quantities") or []) if isinstance(item, dict)]
    predicate = match_predicate(raw_text, param_index)
    position = predicate["position"] if predicate else None
    subject = nearest_subject_before(raw_text, position)
    if not subject and row_cells:
        subject = subject_from_row_cells(row_cells)
    if not subject:
        subject = clean_text(section_title or "")
    quantity = select_quantity(quantities, raw_text, position)
    scope = str(claim.get("section") or "")
    row: dict[str, Any] = {
        "claim_id": str(claim.get("claim_id", "")),
        "doc_id": str(claim.get("doc_id", "")),
        "section": scope,
        "kind": str(claim.get("kind", "")),
        "raw_text": raw_text,
        "subject_candidate": subject,
        "predicate_candidate": str(predicate["canonical_cn"]) if predicate else "",
        "predicate_key": str(predicate["predicate_key"]) if predicate else "",
        "operator": normalize_operator(str(quantity.get("operator_raw") or "")) if quantity else "",
        "object_value": quantity.get("value") if quantity else None,
        "unit_raw": str(quantity.get("unit_raw") or "") if quantity else "",
        "unit_canonical": str(predicate["default_unit"]) if predicate else "",
        "scope_candidate": scope,
    }
    row["unit_convertible"] = units_convertible(
        row["unit_raw"], row["unit_canonical"], unit_families
    )
    filled = []
    for field in SLOT_FIELDS:
        value = row[field]
        if field == "object_value":
            if value is not None:
                filled.append(field)
        elif str(value).strip():
            filled.append(field)
    rate = len(filled) / len(SLOT_FIELDS)
    row["slot_fill_fields"] = filled
    row["slot_fill_rate"] = round(rate, 4)
    row["parse_status"] = "parsed" if rate >= 0.5 else "partial"
    return row


def reference_key(reference_text: str) -> tuple[str, str] | None:
    match = REF_KIND_RE.search(reference_text or "")
    if not match:
        return None
    return match.group(1), match.group(2).replace("－", "-")


def caption_key(caption: str) -> tuple[str, str] | None:
    match = REF_KIND_RE.match(clean_text(caption))
    if not match:
        return None
    return match.group(1), match.group(2).replace("－", "-")


def build_table_feature_row(
    table: dict[str, Any],
    grid: dict[str, Any],
    param_index: list[dict[str, Any]],
    prev_header: list[str] | None,
) -> dict[str, Any]:
    header = table.get("header_candidate") or []
    continuation = bool(header and prev_header is not None and header == prev_header)
    return {
        "table_id": str(table.get("table_id", "")),
        "doc_id": str(table.get("doc_id", "")),
        "section": str(table.get("section", "")),
        "caption": str(table.get("caption_raw", "")),
        "n_rows": int(table.get("row_count") or 0),
        "n_cols": int(table.get("column_count") or 0),
        "header_candidate": header,
        "merged_cells": merged_cells(grid),
        "empty_cells": build_empty_cells(grid),
        "row_roles": build_row_roles(grid),
        "continuation_candidate": continuation,
        "requirement_id_cells": scan_requirement_id_cells(grid),
        "parameter_cells": scan_parameter_cells(grid, param_index),
    }


def build_visio_feature_row(
    doc_id: str, structure: dict[str, Any], dgm_index: dict[tuple[str, str], str]
) -> dict[str, Any]:
    embed_index = str(structure.get("embed_index", ""))
    diagram_id = dgm_index.get((doc_id, embed_index)) or stable_id("DGM", doc_id, embed_index)
    nodes = [node for node in structure.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in structure.get("edges", []) if isinstance(edge, dict)]
    node_id_map = {
        str(node.get("id", "")): stable_id("NOD", diagram_id, node.get("id", ""))
        for node in nodes
    }
    edges_by_via = dict(Counter(str(edge.get("via", "unknown")) for edge in edges))
    dangling = sum(
        1
        for edge in edges
        if str(edge.get("src", "")) not in node_id_map or str(edge.get("dst", "")) not in node_id_map
    )
    page = structure.get("page") or {}
    row: dict[str, Any] = {
        "diagram_id": diagram_id,
        "doc_id": doc_id,
        "embed_index": embed_index,
        "page_w": page.get("w"),
        "page_h": page.get("h"),
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "node_type_distribution": dict(Counter(str(node.get("type", "unknown")) for node in nodes)),
        "edges_by_via": edges_by_via,
        "dangling_ends": dangling,
        "n_geo": edges_by_via.get("geo", 0),
        "n_glued": edges_by_via.get("glued", 0),
        "nodes": [
            {
                "node_id": node_id_map.get(str(node.get("id", "")), str(node.get("id", ""))),
                "text": str(node.get("text", "")),
                "type": str(node.get("type", "unknown")),
                "geometry": {
                    "cx": node.get("cx"),
                    "cy": node.get("cy"),
                    "w": node.get("w"),
                    "h": node.get("h"),
                },
            }
            for node in nodes
        ],
        "edges": [
            {
                "edge_id": stable_id("EDG", diagram_id, edge.get("connector_id", index)),
                "src": node_id_map.get(str(edge.get("src", "")), str(edge.get("src", ""))),
                "dst": node_id_map.get(str(edge.get("dst", "")), str(edge.get("dst", ""))),
                "label": str(edge.get("label", "")),
                "via": str(edge.get("via", "unknown")),
                "connector_id": str(edge.get("connector_id", "")),
            }
            for index, edge in enumerate(edges)
        ],
    }
    begin_arrows = Counter(
        str(edge.get("begin_arrow")) for edge in edges if "begin_arrow" in edge
    )
    end_arrows = Counter(str(edge.get("end_arrow")) for edge in edges if "end_arrow" in edge)
    if begin_arrows or end_arrows:
        row["arrow_info"] = {
            "begin_arrow": dict(begin_arrows),
            "end_arrow": dict(end_arrows),
        }
    return row


def build_semantic_feature_row(
    doc_id: str,
    model_index: int,
    model: dict[str, Any],
    diagram_id_matched: str | None,
) -> dict[str, Any]:
    diagram_type = str(model.get("diagram_type", ""))
    classify = model.get("_classify") or {}
    type_specific = {
        field: model[field]
        for field in TYPE_SPECIFIC_FIELDS.get(diagram_type, ())
        if field in model
    }
    return {
        "doc_id": doc_id,
        "model_index": model_index,
        "diagram_type": diagram_type,
        "confidence": classify.get("confidence"),
        "root": model.get("root", ""),
        "levels": model.get("levels", []),
        "orphans_count": len(model.get("orphans") or []),
        "diagram_id_matched": diagram_id_matched,
        "type_specific": type_specific,
    }


def _group_by_doc(rows: list[dict[str, Any]], doc_set: set[str]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        doc_id = str(row.get("doc_id", ""))
        if doc_id in doc_set:
            grouped.setdefault(doc_id, []).append(row)
    return grouped


def _group_sections_by_doc(
    rows: list[dict[str, Any]], doc_set: set[str]
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        doc_id = str((row.get("source_ref") or {}).get("doc_id", ""))
        if doc_id in doc_set:
            grouped.setdefault(doc_id, []).append(row)
    return grouped


def _header_missing(header_candidate: Any) -> bool:
    if not header_candidate:
        return True
    return all(not str(cell).strip() for cell in header_candidate)


def _resolve_content_path(doc: dict[str, Any], doc_name: str) -> Path:
    rel = str((doc.get("asset") or {}).get("content_list") or "")
    if rel:
        return BASE / rel
    return MINERU_DIR / doc_name / "office" / f"{doc_name}_content_list.json"


def build(output: Path, limit: int | None = None) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    inputs: dict[str, str] = {}
    documents = _tracked_jsonl(CORPUS_DIR / "documents.jsonl", inputs)
    sections = _tracked_jsonl(CORPUS_DIR / "sections.jsonl", inputs)
    requirements = _tracked_jsonl(CORPUS_DIR / "requirements.jsonl", inputs)
    claims = _tracked_jsonl(CORPUS_DIR / "claims.jsonl", inputs)
    tables = _tracked_jsonl(CORPUS_DIR / "tables.jsonl", inputs)
    images = _tracked_jsonl(CORPUS_DIR / "images.jsonl", inputs)
    diagrams = _tracked_jsonl(CORPUS_DIR / "diagrams.jsonl", inputs)
    diagram_nodes = _tracked_jsonl(CORPUS_DIR / "diagram_nodes.jsonl", inputs)
    anchors = _tracked_json(ANCHOR_V3_PATH, {}, inputs)
    scene_models = _tracked_json(SCENE_MODELS_PATH, {}, inputs)
    kb = _tracked_json(KB_PATH, {}, inputs)
    links = _tracked_jsonl(LINKS_V2_PATH, inputs)

    doc_order = [str(doc.get("doc_id", "")) for doc in documents]
    if limit is not None:
        doc_order = doc_order[: max(0, limit)]
    doc_set = set(doc_order)
    doc_name_by_id = {str(doc.get("doc_id", "")): str(doc.get("doc_name", "")) for doc in documents}

    sections_by_doc = _group_sections_by_doc(sections, doc_set)
    requirements_by_doc = _group_by_doc(requirements, doc_set)
    claims_by_doc = _group_by_doc(claims, doc_set)
    tables_by_doc = _group_by_doc(tables, doc_set)
    images_by_doc = _group_by_doc(images, doc_set)
    diagrams_by_doc = _group_by_doc(diagrams, doc_set)

    dgm_index: dict[tuple[str, str], str] = {}
    dgm_ids_by_doc: dict[str, list[str]] = {}
    for diagram in diagrams:
        doc_id = str(diagram.get("doc_id", ""))
        diagram_id = str(diagram.get("diagram_id", ""))
        dgm_index[(doc_id, str(diagram.get("embed_index", "")))] = diagram_id
        if doc_id in doc_set:
            dgm_ids_by_doc.setdefault(doc_id, []).append(diagram_id)

    nodes_by_doc: dict[str, list[dict[str, Any]]] = {}
    dgm_doc = {str(diagram.get("diagram_id", "")): str(diagram.get("doc_id", "")) for diagram in diagrams}
    for node in diagram_nodes:
        doc_id = dgm_doc.get(str(node.get("diagram_id", "")), "")
        if doc_id in doc_set:
            nodes_by_doc.setdefault(doc_id, []).append(node)

    table_by_id = {str(table.get("table_id", "")): table for table in tables}
    section_title: dict[tuple[str, str], str] = {}
    for row in sections:
        doc_id = str((row.get("source_ref") or {}).get("doc_id", ""))
        section_title[(doc_id, str(row.get("section_id", "")))] = str(row.get("title", ""))

    html_bodies_by_doc: dict[str, list[str]] = {}
    for doc in documents:
        doc_id = str(doc.get("doc_id", ""))
        if doc_id not in doc_set:
            continue
        doc_name = doc_name_by_id.get(doc_id, "")
        content = _tracked_json(_resolve_content_path(doc, doc_name), [], inputs)
        html_bodies_by_doc[doc_id] = [
            str(block.get("table_body", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "table"
        ]

    param_index = build_param_index(kb.get("param_dictionary") or {})
    unit_families = build_unit_families(kb.get("unit_dictionary") or {})

    document_rows: list[dict[str, Any]] = []
    text_rows: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    visio_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []

    for doc_id in doc_order:
        doc_name = doc_name_by_id.get(doc_id, "")
        doc_claims = claims_by_doc.get(doc_id, [])
        doc_tables = tables_by_doc.get(doc_id, [])
        doc_requirements = requirements_by_doc.get(doc_id, [])
        explicit = [
            row
            for row in doc_requirements
            if row.get("identifier_kind") != "synthetic_section"
        ]
        synthetic = [
            row for row in doc_requirements if row.get("identifier_kind") == "synthetic_section"
        ]
        claims_with_ids = [
            claim for claim in doc_claims if (claim.get("features") or {}).get("requirement_ids")
        ]
        document_rows.append(
            {
                "doc_id": doc_id,
                "doc_name": doc_name,
                "n_sections": len(sections_by_doc.get(doc_id, [])),
                "n_requirements_explicit": len(explicit),
                "n_requirements_synthetic": len(synthetic),
                "n_claims": len(doc_claims),
                "n_tables": len(doc_tables),
                "n_images": len(images_by_doc.get(doc_id, [])),
                "n_diagrams": len(diagrams_by_doc.get(doc_id, [])),
                "n_table_rows": sum(int(table.get("row_count") or 0) for table in doc_tables),
                "requirement_id_density": round(len(claims_with_ids) / len(doc_claims), 4)
                if doc_claims
                else 0.0,
            }
        )

        n_text_claims = 0
        for claim in doc_claims:
            if claim.get("kind") != "text_claim":
                continue
            n_text_claims += 1
            features = claim.get("features") or {}
            text_rows.append(
                {
                    "sentence_id": str(claim.get("claim_id", "")),
                    "doc_id": doc_id,
                    "section": str(claim.get("section", "")),
                    "text": str(claim.get("raw_text", "")),
                    "requirement_ids": features.get("requirement_ids", []),
                    "modal_words": features.get("modal_words", []),
                    "negative": bool(features.get("negative", False)),
                    "quantities": features.get("quantities", []),
                    "references": features.get("references", []),
                    "sentence_length": len(str(claim.get("raw_text", ""))),
                }
            )

        bodies = html_bodies_by_doc.get(doc_id, [])
        prev_header: list[str] | None = None
        for table_index, table in enumerate(doc_tables):
            body = bodies[table_index] if table_index < len(bodies) else ""
            grid = parse_grid_table(body) if body else grid_from_rows(table.get("rows") or [])
            if body and not grid["cells"]:
                grid = grid_from_rows(table.get("rows") or [])
            table_rows.append(build_table_feature_row(table, grid, param_index, prev_header))
            header = table.get("header_candidate") or []
            if header:
                prev_header = header

        doc_slot_rows: list[dict[str, Any]] = []
        for claim in doc_claims:
            source_ref = claim.get("source_ref") or {}
            row_cells: list[str] = []
            table = table_by_id.get(str(source_ref.get("table_id", "")))
            if table is not None:
                table_rows_raw = table.get("rows") or []
                row_index = source_ref.get("row_index")
                if isinstance(row_index, int) and 0 <= row_index < len(table_rows_raw):
                    row_cells = [str(cell) for cell in table_rows_raw[row_index]]
            title = section_title.get((doc_id, str(claim.get("section", ""))), "")
            doc_slot_rows.append(
                build_claim_slot_row(claim, param_index, unit_families, title, row_cells)
            )
        claim_rows.extend(doc_slot_rows)

        nodes = nodes_by_doc.get(doc_id, [])
        empty_nodes = sum(1 for node in nodes if not str(node.get("text_raw", "")).strip())
        structures = (anchors.get(doc_name) or {}).get("structures", [])
        n_edges_doc = 0
        dangling_edges = 0
        geo_edges = 0
        for structure in structures:
            node_ids = {str(node.get("id", "")) for node in structure.get("nodes", [])}
            for edge in structure.get("edges", []):
                n_edges_doc += 1
                if (
                    str(edge.get("src", "")) not in node_ids
                    or str(edge.get("dst", "")) not in node_ids
                ):
                    dangling_edges += 1
                if str(edge.get("via", "")) == "geo":
                    geo_edges += 1
        n_quantities = 0
        n_quantities_with_unit = 0
        for claim in doc_claims:
            for quantity in (claim.get("features") or {}).get("quantities") or []:
                n_quantities += 1
                if str(quantity.get("unit_raw", "")).strip():
                    n_quantities_with_unit += 1
        caption_keys: set[tuple[str, str]] = set()
        for image in images_by_doc.get(doc_id, []):
            key = caption_key(str(image.get("caption_raw", "")))
            if key is not None:
                caption_keys.add(key)
        for table in doc_tables:
            key = caption_key(str(table.get("caption_raw", "")))
            if key is not None:
                caption_keys.add(key)
        n_references = 0
        n_references_resolved = 0
        for claim in doc_claims:
            for reference in (claim.get("features") or {}).get("references") or []:
                n_references += 1
                key = reference_key(str(reference))
                if key is not None and key in caption_keys:
                    n_references_resolved += 1
        n_header_missing = sum(
            1 for table in doc_tables if _header_missing(table.get("header_candidate"))
        )
        slot_rates = [len(row["slot_fill_fields"]) / 6 for row in doc_slot_rows]
        quality_rows.append(
            {
                "doc_id": doc_id,
                "empty_text_node_rate": round(empty_nodes / len(nodes), 4) if nodes else 0.0,
                "dangling_edge_rate": round(dangling_edges / n_edges_doc, 4)
                if n_edges_doc
                else 0.0,
                "geo_edge_rate": round(geo_edges / n_edges_doc, 4) if n_edges_doc else 0.0,
                "unit_completeness": round(n_quantities_with_unit / n_quantities, 4)
                if n_quantities
                else 1.0,
                "reference_resolution_rate": round(n_references_resolved / n_references, 4)
                if n_references
                else 1.0,
                "table_header_missing_rate": round(n_header_missing / len(doc_tables), 4)
                if doc_tables
                else 0.0,
                "claim_slot_fill_rate_avg": round(sum(slot_rates) / len(slot_rates), 4)
                if slot_rates
                else 0.0,
                "text_claim_ratio": round(n_text_claims / len(doc_claims), 4)
                if doc_claims
                else 0.0,
            }
        )

        for structure in (anchors.get(doc_name) or {}).get("structures", []):
            visio_rows.append(build_visio_feature_row(doc_id, structure, dgm_index))

        models = (scene_models.get(doc_name) or {}).get("models", [])
        dgm_ids = dgm_ids_by_doc.get(doc_id, [])
        counts_match = len(models) == len(dgm_ids)
        for model_index, model in enumerate(models):
            diagram_id_matched = (
                dgm_ids[model_index] if counts_match and model_index < len(dgm_ids) else None
            )
            semantic_rows.append(
                build_semantic_feature_row(doc_id, model_index, model, diagram_id_matched)
            )

    alignment_rows = [
        {
            "link_id": str(link.get("link_id", "")),
            "source_id": str(link.get("source_id", "")),
            "target_id": str(link.get("target_id", "")),
            "relation_type": str(link.get("relation_type", "")),
            "status": str(link.get("status", "")),
            "quality_tier": str(link.get("quality_tier", "")),
            "evidence": link.get("evidence", []),
            "score": link.get("score"),
        }
        for link in links
    ]

    files = {
        "document_features": write_jsonl(output / "document_features.jsonl", document_rows),
        "text_features": write_jsonl(output / "text_features.jsonl", text_rows),
        "table_features": write_jsonl(output / "table_features.jsonl", table_rows),
        "visio_features": write_jsonl(output / "visio_features.jsonl", visio_rows),
        "diagram_semantic_features": write_jsonl(
            output / "diagram_semantic_features.jsonl", semantic_rows
        ),
        "claim_slot_features": write_jsonl(output / "claim_slot_features.jsonl", claim_rows),
        "quality_features": write_jsonl(output / "quality_features.jsonl", quality_rows),
        "alignment_features": write_jsonl(output / "alignment_features.jsonl", alignment_rows),
    }

    slot_rates_all = [len(row["slot_fill_fields"]) / 6 for row in claim_rows]
    predicate_hits = sum(1 for row in claim_rows if row["predicate_candidate"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "builder": "tools/build_feature_matrix.py",
        "counts": {**files, "documents": len(doc_order)},
        "claim_slot_stats": {
            "n_claims": len(claim_rows),
            "avg_slot_fill_rate": round(sum(slot_rates_all) / len(slot_rates_all), 4)
            if slot_rates_all
            else 0.0,
            "predicate_hit_rate": round(predicate_hits / len(claim_rows), 4)
            if claim_rows
            else 0.0,
            "parsed": sum(1 for row in claim_rows if row["parse_status"] == "parsed"),
            "partial": sum(1 for row in claim_rows if row["parse_status"] == "partial"),
        },
        "input_assets": dict(sorted(inputs.items())),
        "policy": {
            "quality_signals_are_risk_not_defects": True,
            "slot_fill_is_candidate_not_gold": True,
            "diagram_semantic_alignment_may_be_unmatched": True,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "files": {name: sha256_file(output / f"{name}.jsonl") for name in files},
        "summary_sha256": sha256_file(output / "summary.json"),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
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
            {"counts": summary["counts"], "claim_slot_stats": summary["claim_slot_stats"]},
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
