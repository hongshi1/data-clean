#!/usr/bin/env python3
"""Build the source-aware structured corpus used by the research agent.

The builder is deliberately deterministic and offline. It preserves parser
observations instead of pretending that heuristic normalization is gold.

Usage:
    python tools/build_structured_corpus.py
    python tools/build_structured_corpus.py --output data/gjb_438c/structured_corpus_v1
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

BASE = Path(__file__).resolve().parent.parent
MINERU_DIR = BASE / "data/gjb_438c/mineru_standard"
TEXTUTIL_DIR = BASE / "data/gjb_438c/dual_source"
ANCHOR_PATH = BASE / "data/gjb_438c/anchor_v3/anchors_v3.json"
QA_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_final.json"
FROZEN_QA_PATH = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
TRAIN_PATH = BASE / "data/gjb_438c/pair_dataset_canonical/train.jsonl"
KNOWLEDGE_DIR = BASE / "knowledge"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/structured_corpus_v1"

SECTION_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+?)\s*$")
REQ_ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
NUMBER_RE = re.compile(
    r"(?P<operator>不超过|不大于|不低于|不小于|至少|至多|最多|大于等于|小于等于|≤|≥|<=|>=|=|等于)?\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>ms|毫秒|秒|分钟|小时|KB|MB|GB|TB|字节|Hz|MHz|GHz|%|次|个|条|路)?"
)
MODALITY_RE = re.compile(r"应当|应该|应|必须|不得|禁止|可以|可|宜|允许")
REFERENCE_RE = re.compile(r"(?:如图|见图|图|如表|见表|表|参见)\s*[A-Za-z]?\s*\d+(?:[-－]\d+)?")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？；;])\s*|\n+", text) if part.strip()]


def parse_section(text: str) -> tuple[str, str] | None:
    match = SECTION_RE.match(clean_text(text))
    return (match.group(1), match.group(2)) if match else None


def section_parent(section_id: str) -> str | None:
    parts = section_id.split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else None


def extract_features(text: str) -> dict[str, Any]:
    normalized = clean_text(text)
    quantities = []
    for match in NUMBER_RE.finditer(normalized):
        value = float(match.group("value"))
        quantities.append(
            {
                "raw": match.group(0).strip(),
                "operator_raw": match.group("operator") or "",
                "value": int(value) if value.is_integer() else value,
                "unit_raw": match.group("unit") or "",
                "normalization_status": "candidate",
            }
        )
    return {
        "requirement_ids": sorted(set(REQ_ID_RE.findall(normalized))),
        "quantities": quantities,
        "modal_words": sorted(set(MODALITY_RE.findall(normalized))),
        "references": sorted(set(REFERENCE_RE.findall(normalized))),
        "negative": any(word in normalized for word in ("不得", "禁止", "不能")),
    }


class TableParser(HTMLParser):
    """Small loss-minimizing HTML table parser for MinerU table_body.

    Tracks ``<thead>`` so consumers know where data rows actually start
    instead of assuming ``rows[0]`` is always the (single) header row.
    """

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.header_row_count: int = 0
        self._row: list[str] = []
        self._cell: list[str] = []
        self._in_cell = False
        self._saw_thead = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"}:
            self._cell = []
            self._in_cell = True
        elif tag == "thead":
            self._saw_thead = True

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._row.append(clean_text(" ".join(self._cell)))
            self._in_cell = False
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
        elif tag == "thead":
            # Data rows start where </thead> ends
            self.header_row_count = len(self.rows)

    def data_start(self) -> int:
        """Index of the first data row.

        With a ``<thead>``: right after it ends. Without one: 1 (first row
        assumed to be the header), or 0 when the table has no rows.
        """
        if self._saw_thead:
            return self.header_row_count
        return 1 if self.rows else 0


def parse_html_table(value: str) -> tuple[list[list[str]], int]:
    """Parse an HTML table into (rows, data_start_index).

    data_start_index is the number of leading header rows: rows inside
    ``<thead>`` when present (data rows start where ``</thead>`` ends),
    else 1 (first row assumed to be the header), else 0 for empty tables.
    """
    parser = TableParser()
    parser.feed(value or "")
    return parser.rows, parser.data_start()


class TextutilParser(HTMLParser):
    """Collect textutil HTML observations without imposing a new schema."""

    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.table_count = 0
        self.image_count = 0
        self._heading_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_depth = int(tag[1])
        elif tag == "table":
            self.table_count += 1
        elif tag == "img":
            self.image_count += 1

    def handle_data(self, data: str) -> None:
        value = clean_text(data)
        if not value:
            return
        self.text_parts.append(value)
        if self._heading_depth:
            self.headings.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_depth = 0


def build_textutil() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(TEXTUTIL_DIR.glob("*.html")):
        parser = TextutilParser()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        doc_id = doc_id_from_name(path.name)
        text = " ".join(parser.text_parts)
        rows.append(
            {
                "observation_id": stable_id("OBS", doc_id, "textutil", path.name),
                "doc_id": doc_id,
                "doc_name": path.stem,
                "modality": "textutil_html",
                "source_ref": {"path": str(path.relative_to(BASE))},
                "source_sha256": sha256_file(path),
                "raw_features": {
                    "text_chars": len(text),
                    "heading_count": len(parser.headings),
                    "table_count": parser.table_count,
                    "image_count": parser.image_count,
                    "heading_samples": parser.headings[:20],
                },
                "status": "observed",
                "method": "textutil_html_asset",
            }
        )
    return rows


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def doc_id_from_name(name: str) -> str:
    match = re.match(r"(\d{2})", name)
    return match.group(1) if match else name


@dataclass
class DocumentBuild:
    document: dict[str, Any]
    observations: list[dict[str, Any]]
    sections: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    images: list[dict[str, Any]]
    claims: list[dict[str, Any]]


def build_document(doc_dir: Path) -> DocumentBuild:
    doc_name = doc_dir.name
    doc_id = doc_id_from_name(doc_name)
    office = doc_dir / "office"
    content_path = office / f"{doc_name}_content_list.json"
    content = load_json(content_path, [])
    source_hash = sha256_file(content_path) if content_path.exists() else ""
    observations: list[dict[str, Any]] = []
    sections: dict[str, dict[str, Any]] = {}
    requirements: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    current_section = ""
    block_index = 0
    table_index = 0
    image_index = 0

    for item_index, item in enumerate(content):
        item_type = str(item.get("type", "unknown"))
        page = item.get("page_idx")
        raw_text = clean_text(item.get("text", ""))
        parsed = parse_section(raw_text) if item_type == "text" else None
        if parsed and item.get("text_level", 0):
            current_section, title = parsed
            sections.setdefault(
                current_section,
                {
                    "section_id": current_section,
                    "parent_section_id": section_parent(current_section),
                    "title": title,
                    "source_ref": {
                        "doc_id": doc_id,
                        "page": page,
                        "item_index": item_index,
                    },
                    "status": "observed",
                    "content_fragments": [],
                },
            )
            req_ids = sorted(set(REQ_ID_RE.findall(title)))
            if req_ids:
                sections[current_section]["requirement_ids"] = req_ids
            continue

        if item_type == "text" and raw_text and current_section:
            sections.setdefault(current_section, {"content_fragments": []})
            sections[current_section].setdefault("content_fragments", []).append(raw_text)
            block_id = stable_id("OBS", doc_id, "text", item_index)
            features = extract_features(raw_text)
            observation = {
                "observation_id": block_id,
                "doc_id": doc_id,
                "modality": "text",
                "raw_payload": {"text": item.get("text", ""), "anchor": item.get("anchor", "")},
                "source_ref": {
                    "doc_id": doc_id,
                    "section": current_section,
                    "page": page,
                    "block_id": block_id,
                    "item_index": item_index,
                },
                "status": "observed",
                "method": "mineru_content_list",
                "features": features,
            }
            observations.append(observation)
            for sentence_index, sentence in enumerate(split_sentences(raw_text)):
                sentence_features = extract_features(sentence)
                if (
                    not sentence_features["requirement_ids"]
                    and not sentence_features["quantities"]
                    and not sentence_features["modal_words"]
                ):
                    continue
                claim_id = stable_id("CLM", doc_id, block_id, sentence_index)
                claims.append(
                    {
                        "claim_id": claim_id,
                        "doc_id": doc_id,
                        "kind": "text_claim",
                        "raw_text": sentence,
                        "subject_candidate": "",
                        "predicate_candidate": "",
                        "source_observation_ids": [block_id],
                        "section": current_section,
                        "features": sentence_features,
                        "parse_status": "candidate",
                    }
                )
            for req_id in features["requirement_ids"]:
                requirements.append(
                    {
                        "requirement_id": req_id,
                        "doc_id": doc_id,
                        "section": current_section,
                        "title": sections.get(current_section, {}).get("title", ""),
                        "raw_text": raw_text,
                        "source_observation_id": block_id,
                        "parse_status": "candidate",
                        "features": features,
                    }
                )
            block_index += 1

        elif item_type == "table":
            table_id = f"T-{doc_id}-{table_index:04d}"
            caption = " ".join(str(x) for x in item.get("table_caption", []) or [])
            rows, header_row_count = parse_html_table(str(item.get("table_body", "")))
            table = {
                "table_id": table_id,
                "doc_id": doc_id,
                "section": current_section,
                "page": page,
                "caption_raw": caption,
                "rows": rows,
                "header_row_count": header_row_count,
                "header_candidate": rows[0] if header_row_count else [],
                "row_count": len(rows),
                "column_count": max((len(row) for row in rows), default=0),
                "source_ref": {"doc_id": doc_id, "page": page, "table_id": table_id},
                "parse_status": "parsed" if rows else "partial",
            }
            tables.append(table)
            observation_id = stable_id("OBS", doc_id, "table", table_id)
            observations.append(
                {
                    "observation_id": observation_id,
                    "doc_id": doc_id,
                    "modality": "table",
                    "raw_payload": {"caption": caption, "table_body": item.get("table_body", "")},
                    "source_ref": table["source_ref"],
                    "status": table["parse_status"],
                    "method": "mineru_content_list_html",
                    "features": {"caption": caption, "row_count": len(rows)},
                }
            )
            for row_index, row in enumerate(rows):
                row_text = " | ".join(row)
                row_features = extract_features(row_text)
                for sentence_index, sentence in enumerate(split_sentences(row_text)):
                    sentence_features = extract_features(sentence)
                    if not sentence_features["requirement_ids"] and not sentence_features["quantities"]:
                        continue
                    claims.append(
                        {
                            "claim_id": stable_id("CLM", doc_id, table_id, row_index, sentence_index),
                            "doc_id": doc_id,
                            "kind": "table_claim",
                            "raw_text": sentence,
                            "source_observation_ids": [observation_id],
                            "source_ref": {"table_id": table_id, "row_index": row_index},
                            "section": current_section,
                            "features": sentence_features,
                            "parse_status": "candidate",
                        }
                    )
                if row_features["requirement_ids"]:
                    requirements.append(
                        {
                            "requirement_id": row_features["requirement_ids"][0],
                            "doc_id": doc_id,
                            "section": current_section,
                            "title": row[1] if len(row) > 1 else "",
                            "raw_text": row_text,
                            "source_observation_id": observation_id,
                            "source_ref": {"table_id": table_id, "row_index": row_index},
                            "parse_status": "candidate",
                            "features": row_features,
                        }
                    )
            table_index += 1

        elif item_type == "image":
            image_id = f"IMG-{doc_id}-{image_index:04d}"
            caption = " ".join(str(x) for x in item.get("image_caption", []) or [])
            image = {
                "image_id": image_id,
                "doc_id": doc_id,
                "section": current_section,
                "page": page,
                "path": item.get("img_path", ""),
                "caption_raw": caption,
                "source_ref": {"doc_id": doc_id, "page": page, "image_id": image_id},
                "parse_status": "observed",
            }
            images.append(image)
            observations.append(
                {
                    "observation_id": stable_id("OBS", doc_id, "image", image_id),
                    "doc_id": doc_id,
                    "modality": "image",
                    "raw_payload": {"path": image["path"], "caption": caption},
                    "source_ref": image["source_ref"],
                    "status": "observed",
                    "method": "mineru_content_list_image",
                    "features": extract_features(caption),
                }
            )
            image_index += 1

    for section_id, section in sections.items():
        content = "\n".join(section.pop("content_fragments", []))
        if not section_id.startswith("3") or not content and not section.get("title"):
            continue
        synthetic_id = f"REQ-{section_id}"
        requirements.append(
            {
                "requirement_id": synthetic_id,
                "identifier_kind": "synthetic_section",
                "doc_id": doc_id,
                "section": section_id,
                "title": section.get("title", ""),
                "raw_text": content,
                "source_ref": section.get("source_ref", {}),
                "parse_status": "candidate",
                "features": extract_features(content),
            }
        )

    document = {
        "doc_id": doc_id,
        "doc_name": doc_name,
        "asset": {
            "content_list": str(content_path.relative_to(BASE)),
            "content_list_sha256": source_hash,
            "parser": "mineru_content_list",
        },
        "counts": {
            "sections": len(sections),
            "requirements": len(requirements),
            "tables": len(tables),
            "images": len(images),
            "observations": len(observations),
            "claims": len(claims),
        },
        "parse_status": "parsed" if content_path.exists() else "unparsed",
    }
    return DocumentBuild(document, observations, list(sections.values()), requirements, tables, images, claims)


def build_visio(anchor_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    anchors = load_json(anchor_path, {})
    diagrams: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for doc_name, payload in anchors.items():
        doc_id = doc_id_from_name(doc_name)
        for diagram_index, structure in enumerate(payload.get("structures", [])):
            diagram_id = stable_id("DGM", doc_id, structure.get("embed_index", diagram_index))
            diagram = {
                "diagram_id": diagram_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "source": structure.get("source", ""),
                "embed_index": structure.get("embed_index", ""),
                "page": structure.get("page", {}),
                "meta": structure.get("meta", {}),
                "alignment_status": "unmatched",
                "parse_status": "observed",
            }
            diagrams.append(diagram)
            for node in structure.get("nodes", []):
                node_id = stable_id("NOD", diagram_id, node.get("id", ""))
                nodes.append(
                    {
                        "node_id": node_id,
                        "diagram_id": diagram_id,
                        "source_node_id": str(node.get("id", "")),
                        "text_raw": node.get("text", ""),
                        "type_candidate": node.get("type", "unknown"),
                        "geometry": {
                            key: node.get(key)
                            for key in ("bbox", "cx", "cy", "w", "h", "rx", "ry")
                            if key in node
                        },
                        "features": extract_features(str(node.get("text", ""))),
                        "parse_status": "observed",
                    }
                )
            for edge_index, edge in enumerate(structure.get("edges", [])):
                edges.append(
                    {
                        "edge_id": stable_id("EDG", diagram_id, edge.get("connector_id", edge_index)),
                        "diagram_id": diagram_id,
                        "source_node_id": str(edge.get("src", "")),
                        "target_node_id": str(edge.get("dst", "")),
                        "connector_id": str(edge.get("connector_id", "")),
                        "label_raw": edge.get("label", ""),
                        "via": edge.get("via", "unknown"),
                        "direction_status": "candidate",
                        "raw": edge,
                        "parse_status": "observed",
                    }
                )
    return diagrams, nodes, {"edges": edges, "source_sha256": sha256_file(anchor_path) if anchor_path.exists() else ""}


def build_qa(output: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    qa_rows = load_json(QA_PATH, [])
    structured = []
    claim_count = 0
    for row in qa_rows if isinstance(qa_rows, list) else []:
        question = clean_text(row.get("question", ""))
        answer = clean_text(row.get("answer", ""))
        claims = []
        for index, sentence in enumerate(split_sentences(answer)):
            claim = {
                "claim_id": stable_id("QCLM", row.get("id", ""), index),
                "raw_text": sentence,
                "features": extract_features(sentence),
                "parse_status": "candidate",
            }
            claims.append(claim)
            claim_count += 1
        structured.append(
            {
                "qa_id": row.get("id", ""),
                "doc_id": doc_id_from_name(str(row.get("doc", ""))),
                "doc_name": row.get("doc", ""),
                "pair_id": row.get("pair_id", ""),
                "section": row.get("section", ""),
                "question": question,
                "answer": answer,
                "question_features": extract_features(question),
                "answer_claims": claims,
                "source": row.get("source", ""),
                "evidence_raw": row.get("evidence", ""),
                "image_ref": row.get("image_path", ""),
                "image_caption": row.get("image_caption", ""),
                "table_caption": row.get("table_caption", ""),
                "parse_status": "parsed",
            }
        )

    frozen_rows = 0
    if FROZEN_QA_PATH.exists():
        with FROZEN_QA_PATH.open(encoding="utf-8") as handle:
            frozen_rows = sum(1 for line in handle if line.strip())
    train_rows = 0
    if TRAIN_PATH.exists():
        with TRAIN_PATH.open(encoding="utf-8") as handle:
            train_rows = sum(1 for line in handle if line.strip())
    return structured, {
        "qa_rows": len(structured),
        "qa_answer_claims": claim_count,
        "frozen_qa_rows": frozen_rows,
        "canonical_train_rows": train_rows,
    }


def build_frozen_qa() -> list[dict[str, Any]]:
    rows = []
    if not FROZEN_QA_PATH.exists():
        return rows
    with FROZEN_QA_PATH.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            raw = json.loads(line)
            evidence = []
            for item in raw.get("evidence", []):
                evidence.append(
                    {
                        "evidence_id": item.get("evidence_id", ""),
                        "text": item.get("text", ""),
                        "source_type": item.get("source_type", "unknown"),
                        "source_ref": item.get("source_ref", {}),
                        "scope_id": item.get("scope_id", ""),
                        "completeness": item.get("completeness", "unknown"),
                    }
                )
            rows.append(
                {
                    "frozen_qa_id": f"FQA-{index + 1:04d}",
                    "context_freeze_id": raw.get("context_freeze_id", ""),
                    "answer": raw.get("answer", ""),
                    "answer_claims": [
                        {
                            "claim_id": stable_id("FCLM", index, claim_index),
                            "raw_text": sentence,
                            "features": extract_features(sentence),
                            "parse_status": "candidate",
                        }
                        for claim_index, sentence in enumerate(
                            split_sentences(str(raw.get("answer", "")))
                        )
                    ],
                    "evidence": evidence,
                    "evidence_count": len(evidence),
                    "parse_status": "parsed",
                }
            )
    return rows


def build_training_pairs() -> list[dict[str, Any]]:
    rows = []
    if not TRAIN_PATH.exists():
        return rows
    with TRAIN_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                {
                    "pair_id": raw.get("id", ""),
                    "premise": raw.get("pair", {}).get("premise", ""),
                    "hypothesis": raw.get("pair", {}).get("hypothesis", ""),
                    "label": raw.get("label", ""),
                    "angle": raw.get("angle", {}),
                    "provenance": raw.get("provenance", {}),
                    "split": raw.get("split", ""),
                    "parse_status": "parsed",
                }
            )
    return rows


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    documents: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    for doc_dir in sorted(path for path in MINERU_DIR.iterdir() if path.is_dir()):
        result = build_document(doc_dir)
        documents.append(result.document)
        observations.extend(result.observations)
        sections.extend(result.sections)
        requirements.extend(result.requirements)
        tables.extend(result.tables)
        images.extend(result.images)
        claims.extend(result.claims)

    diagrams, diagram_nodes, edge_bundle = build_visio(ANCHOR_PATH)
    qa_rows, qa_counts = build_qa(output)
    textutil_rows = build_textutil()
    frozen_qa_rows = build_frozen_qa()
    training_pairs = build_training_pairs()
    files = {
        "documents": write_jsonl(output / "documents.jsonl", documents),
        "sections": write_jsonl(output / "sections.jsonl", sections),
        "requirements": write_jsonl(output / "requirements.jsonl", requirements),
        "observations": write_jsonl(output / "observations.jsonl", observations),
        "tables": write_jsonl(output / "tables.jsonl", tables),
        "images": write_jsonl(output / "images.jsonl", images),
        "claims": write_jsonl(output / "claims.jsonl", claims),
        "diagrams": write_jsonl(output / "diagrams.jsonl", diagrams),
        "diagram_nodes": write_jsonl(output / "diagram_nodes.jsonl", diagram_nodes),
        "diagram_edges": write_jsonl(output / "diagram_edges.jsonl", edge_bundle["edges"]),
        "qa": write_jsonl(output / "qa.jsonl", qa_rows),
        "textutil_observations": write_jsonl(output / "textutil_observations.jsonl", textutil_rows),
        "frozen_qa": write_jsonl(output / "frozen_qa.jsonl", frozen_qa_rows),
        "training_pairs": write_jsonl(output / "training_pairs.jsonl", training_pairs),
    }
    knowledge = {}
    for path in sorted(KNOWLEDGE_DIR.glob("*.json")):
        knowledge[path.name] = sha256_file(path)
    summary = {
        "schema_version": "structured_corpus_v1",
        "builder": "tools/build_structured_corpus.py",
        "source_assets": {
            "mineru_dir": str(MINERU_DIR.relative_to(BASE)),
            "textutil_dir": str(TEXTUTIL_DIR.relative_to(BASE)),
            "anchor_path": str(ANCHOR_PATH.relative_to(BASE)),
            "anchor_sha256": edge_bundle["source_sha256"],
            "qa_path": str(QA_PATH.relative_to(BASE)),
        },
        "counts": {
            **files,
            "documents_with_mineru": len(documents),
            "visio_diagrams": len(diagrams),
            "visio_nodes": len(diagram_nodes),
            "visio_edges": len(edge_bundle["edges"]),
            "textutil_documents": len(textutil_rows),
            "frozen_qa_structured": len(frozen_qa_rows),
            "training_pairs_structured": len(training_pairs),
            **qa_counts,
        },
        "knowledge_hashes": knowledge,
        "status_policy": {
            "candidate_is_not_gold": True,
            "unmatched_figure_alignment_is_preserved": True,
            "visio_geo_edges_require_review": True,
            "qa_answer_claims_are_structural_candidates": True,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": summary["schema_version"],
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
    args = parser.parse_args()
    summary = build(args.output.resolve())
    print(json.dumps(summary["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
