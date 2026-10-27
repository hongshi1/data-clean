#!/usr/bin/env python3
"""Build P1/P2 alignment candidates and hard-negative annotation packages.

This tool creates annotation candidates only. It never writes gold labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / "data/gjb_438c/structured_corpus_v1"
DEFAULT_OUT = BASE / "data/gjb_438c/alignment_annotation_v1"
ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def hash_int(value: str) -> int:
    return int(hashlib.sha1(value.encode("utf-8")).hexdigest()[:12], 16)


def doc_id(row: dict[str, Any]) -> str:
    return str(row.get("doc_id", ""))


def text_of(kind: str, row: dict[str, Any]) -> str:
    if kind == "claim":
        return str(row.get("raw_text", ""))
    if kind == "table_row":
        return " | ".join(row.get("cells", []))
    return str(row.get("text_raw", ""))


def ids(text: str) -> set[str]:
    return set(ID_RE.findall(text))


def grams(text: str) -> set[str]:
    result: set[str] = set()
    for segment in CJK_RE.findall(text):
        result.update(segment[index : index + 2] for index in range(len(segment) - 1))
    return result


def row_objects(tables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for table in tables:
        table_id = str(table.get("table_id", ""))
        for index, cells in enumerate(table.get("rows", [])[1:], start=1):
            rows.append(
                {
                    "occurrence_id": f"table_row:{table_id}:row={index}",
                    "doc_id": str(table.get("doc_id", "")),
                    "section": str(table.get("section", "")),
                    "table_id": table_id,
                    "row_index": index,
                    "cells": [str(cell) for cell in cells],
                    "raw_text": " | ".join(str(cell) for cell in cells),
                    "source_ref": {"table_id": table_id, "row_index": index},
                }
            )
    return rows


def node_objects(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "occurrence_id": f"diagram_node:{row['node_id']}",
            "doc_id": "",
            "section": "",
            "diagram_id": row.get("diagram_id", ""),
            "source_node_id": row.get("source_node_id", ""),
            "raw_text": str(row.get("text_raw", "")),
            "source_ref": {"diagram_id": row.get("diagram_id", ""), "node_id": row.get("node_id", "")},
            "row": row,
        }
        for row in nodes
    ]


def candidate(source: dict[str, Any], target: dict[str, Any], tier: str, generator: str, features: dict[str, Any]) -> dict[str, Any]:
    source_text = str(source.get("raw_text", ""))
    target_text = str(target.get("raw_text", ""))
    return {
        "example_id": "ALIGN-" + hashlib.sha1(
            f"{source['occurrence_id']}|{target['occurrence_id']}|{generator}".encode("utf-8")
        ).hexdigest()[:16],
        "tier": tier,
        "task": "occurrence_pair_link",
        "source": {
            "asset_type": source["asset_type"],
            "asset_id": source["occurrence_id"],
            "doc_id": source.get("doc_id", ""),
            "section": source.get("section", ""),
            "source_ref": source.get("source_ref", {}),
            "text_snapshot": source_text,
        },
        "target": {
            "asset_type": target["asset_type"],
            "asset_id": target["occurrence_id"],
            "doc_id": target.get("doc_id", ""),
            "section": target.get("section", ""),
            "source_ref": target.get("source_ref", {}),
            "text_snapshot": target_text,
        },
        "candidate_provenance": {
            "generator": generator,
            "features": features,
            "gold_relation": None,
            "gold_status": "pending",
        },
        "annotators": [],
        "adjudication": {"status": "pending", "final_relation": None},
        "split_group": f"doc-{source.get('doc_id') or target.get('doc_id')}",
        "split": None,
    }


def build(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    claims_raw = read_jsonl(CORPUS / "claims.jsonl")
    tables = read_jsonl(CORPUS / "tables.jsonl")
    nodes_raw = read_jsonl(CORPUS / "diagram_nodes.jsonl")
    diagrams = read_jsonl(CORPUS / "diagrams.jsonl")
    diagram_docs = {str(row.get("diagram_id", "")): str(row.get("doc_id", "")) for row in diagrams}
    claims = [
        {**row, "occurrence_id": f"claim:{row['claim_id']}", "asset_type": "claim", "doc_id": row.get("doc_id", "")}
        for row in claims_raw
    ]
    rows = [{**row, "asset_type": "table_row"} for row in row_objects(tables)]
    nodes = [
        {
            **row,
            "asset_type": "diagram_node",
            "doc_id": diagram_docs.get(str(row.get("diagram_id", "")), ""),
        }
        for row in node_objects(nodes_raw)
    ]
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in claims:
        by_doc[doc_id(row)].append(row)
    for row in rows:
        by_doc[doc_id(row)].append(row)
    for row in nodes:
        by_doc[doc_id(row)].append(row)

    candidates: list[dict[str, Any]] = []
    counts = defaultdict(int)
    for claim_row in claims:
        claim_ids = ids(text_of("claim", claim_row))
        for target in by_doc.get(doc_id(claim_row), []):
            if target["asset_type"] == "claim":
                continue
            target_text = text_of(target["asset_type"], target)
            target_ids = ids(target_text)
            shared = sorted(claim_ids & target_ids)
            overlap = len(grams(text_of("claim", claim_row)) & grams(target_text))
            same_section = bool(claim_row.get("section")) and claim_row.get("section") == target.get("section")
            if shared:
                candidates.append(
                    candidate(
                        claim_row,
                        target,
                        "P1",
                        "explicit_identifier_candidate",
                        {"shared_identifiers": shared, "same_section": same_section},
                    )
                )
                counts["p1_explicit_identifier"] += 1
            elif overlap >= 2 and (same_section or target["asset_type"] == "diagram_node"):
                candidates.append(
                    candidate(
                        claim_row,
                        target,
                        "P2",
                        "semantic_structure_candidate",
                        {"cjk_bigram_overlap": overlap, "same_section": same_section},
                    )
                )
                counts["p2_semantic_structure"] += 1

    # Same-table sibling candidates are intentionally pending annotations.
    for table in tables:
        table_rows = row_objects([table])
        for left_index, left in enumerate(table_rows):
            for right in table_rows[left_index + 1 :]:
                if left["row_index"] + 1 != right["row_index"]:
                    continue
                if len(grams(left["raw_text"]) & grams(right["raw_text"])) < 2:
                    continue
                left["asset_type"] = right["asset_type"] = "table_row"
                candidates.append(
                    candidate(
                        left,
                        right,
                        "P2",
                        "same_table_sibling_candidate",
                        {"table_id": table.get("table_id", ""), "adjacent": True},
                    )
                )
                counts["p2_same_table_sibling"] += 1

    # Stable document folds; no labels are assigned by this script.
    for row in candidates:
        group = row["split_group"]
        row["split"] = {"fold": hash_int(group) % 4, "group": group}
    candidates.sort(key=lambda row: row["example_id"])
    files = {"alignment_candidates": write_jsonl(out / "alignment_candidates.jsonl", candidates)}
    summary = {
        "schema_version": "alignment_annotation_v1",
        "counts": {**files, **dict(counts)},
        "source_corpus": str(CORPUS.relative_to(BASE)),
        "source_manifest": str((CORPUS / "manifest.json").relative_to(BASE)),
        "policy": {
            "automatic_labels": False,
            "unknown_is_not_negative": True,
            "candidate_is_not_gold": True,
            "split_before_annotation": True,
            "p1_requires_explicit_identifier": True,
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "schema_version": summary["schema_version"],
        "files": {name: hashlib.sha256((out / f"{name}.jsonl").read_bytes()).hexdigest() for name in files},
        "summary_sha256": hashlib.sha256((out / "summary.json").read_bytes()).hexdigest(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve()), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
