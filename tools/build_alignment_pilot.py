#!/usr/bin/env python3
"""Materialize a stratified, double-annotation-ready alignment pilot.

The input candidates are not labels. This tool samples P1/P2 candidates,
adds hard-negative candidate pairs, and writes annotation rows with gold
fields left null.
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
CANDIDATES = BASE / "data/gjb_438c/alignment_annotation_v1/alignment_candidates.jsonl"
DEFAULT_OUT = BASE / "data/gjb_438c/alignment_pilot_v1"
ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def stable_rank(value: str) -> int:
    return int(hashlib.sha1(value.encode("utf-8")).hexdigest()[:12], 16)


def identifiers(text: str) -> set[str]:
    return set(ID_RE.findall(text or ""))


def normalize(text: str) -> str:
    return re.sub(r"\s+|[，。；：:、,./（）()\-_]", "", text or "").lower()


def fold_for(doc_id: str) -> int:
    return stable_rank(f"doc:{doc_id}") % 4


def split_name(fold: int) -> str:
    return ("test", "dev", "train", "train")[fold]


def set_pilot_fields(row: dict[str, Any], kind: str, difficulty: str) -> dict[str, Any]:
    result = dict(row)
    doc_id = str(result["source"].get("doc_id") or result["target"].get("doc_id") or "")
    fold = fold_for(doc_id)
    result["hard_negative_type"] = kind
    result["difficulty"] = difficulty
    result["gold"] = {
        "relation": None,
        "alignment": None,
        "unknown_reason": None,
        "confidence": None,
    }
    result["annotators"] = []
    result["adjudication"] = {"status": "pending", "final_relation": None}
    result["split"] = {"fold": fold, "name": split_name(fold), "document_group": f"doc-{doc_id}"}
    result["status"] = "pending_annotation"
    return result


def rows_by_asset(rows: list[dict[str, Any]], asset_type: str) -> list[dict[str, Any]]:
    return [
        {
            "occurrence_id": row["source"]["asset_id"],
            "asset_type": asset_type,
            "doc_id": str(row["source"].get("doc_id", "")),
            "section": str(row["source"].get("section", "")),
            "text": str(row["source"].get("text_snapshot", "")),
            "source_ref": row["source"].get("source_ref", {}),
        }
        for row in rows
        if row["source"]["asset_type"] == asset_type
    ]


def hard_negative_rows(corpus: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    claims = corpus["claims"]
    tables = corpus["tables"]
    nodes = corpus["diagram_nodes"]

    # Same-name candidates are intentionally pending; equal surface form is not
    # enough to assign a negative label.
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in claims:
        name = normalize(str(row.get("raw_text", "")))
        if len(name) >= 4:
            by_name[name].append({"id": f"claim:{row['claim_id']}", "doc": row.get("doc_id", ""), "text": row.get("raw_text", "")})
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        for left_index, left in enumerate(group):
            for right in group[left_index + 1 : left_index + 4]:
                if left["doc"] != right["doc"]:
                    continue
                out.append(
                    {
                        "example_id": f"HN-NAME-{stable_rank(left['id'] + right['id'])}",
                        "tier": "P2",
                        "task": "occurrence_pair_link",
                        "hard_negative_type": "same_name_polysemy",
                        "difficulty": "L2",
                        "source": {"asset_type": "claim", "asset_id": left["id"], "doc_id": left["doc"], "text_snapshot": left["text"]},
                        "target": {"asset_type": "claim", "asset_id": right["id"], "doc_id": right["doc"], "text_snapshot": right["text"]},
                        "candidate_provenance": {"generator": "same_name_polysemy", "blocking_key": name},
                        "gold": {"relation": None, "alignment": None, "unknown_reason": None, "confidence": None},
                        "adjudication": {"status": "pending", "final_relation": None},
                    }
                )

    # Same-table sibling rows: only adjacent rows with a shared lexical signal.
    for table in tables:
        rows = table.get("rows", [])[1:]
        for index in range(len(rows) - 1):
            left, right = rows[index], rows[index + 1]
            left_text, right_text = " | ".join(left), " | ".join(right)
            shared = normalize(left_text)[:8] == normalize(right_text)[:8] or bool(identifiers(left_text) & identifiers(right_text))
            if not shared:
                continue
            doc = str(table.get("doc_id", ""))
            out.append(
                {
                    "example_id": f"HN-TABLE-{stable_rank(str(table.get('table_id')) + str(index))}",
                    "tier": "P2",
                    "task": "occurrence_pair_link",
                    "hard_negative_type": "same_table_sibling_row",
                    "difficulty": "L3",
                    "source": {"asset_type": "table_row", "asset_id": f"table_row:{table.get('table_id')}:row={index + 1}", "doc_id": doc, "source_ref": {"table_id": table.get("table_id"), "row_index": index + 1}, "text_snapshot": left_text},
                    "target": {"asset_type": "table_row", "asset_id": f"table_row:{table.get('table_id')}:row={index + 2}", "doc_id": doc, "source_ref": {"table_id": table.get("table_id"), "row_index": index + 2}, "text_snapshot": right_text},
                    "candidate_provenance": {"generator": "same_table_sibling_row", "table_id": table.get("table_id"), "adjacent": True},
                    "gold": {"relation": None, "alignment": None, "unknown_reason": None, "confidence": None},
                    "adjudication": {"status": "pending", "final_relation": None},
                }
            )

    # Same-diagram siblings: same diagram and same type, but distinct IDs.
    nodes_by_diagram: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in nodes:
        nodes_by_diagram[str(node.get("diagram_id", ""))].append(node)
    for diagram_id, group in nodes_by_diagram.items():
        for index, left in enumerate(group):
            for right in group[index + 1 : index + 4]:
                if left.get("type_candidate") != right.get("type_candidate"):
                    continue
                if not str(left.get("text_raw", "")).strip() or not str(right.get("text_raw", "")).strip():
                    continue
                out.append(
                    {
                        "example_id": f"HN-DIAGRAM-{stable_rank(str(left['node_id']) + str(right['node_id']))}",
                        "tier": "P2",
                        "task": "occurrence_pair_link",
                        "hard_negative_type": "same_diagram_sibling_node",
                        "difficulty": "L3",
                        "source": {"asset_type": "diagram_node", "asset_id": f"diagram_node:{left['node_id']}", "doc_id": "", "source_ref": {"diagram_id": diagram_id, "node_id": left["node_id"]}, "text_snapshot": left.get("text_raw", "")},
                        "target": {"asset_type": "diagram_node", "asset_id": f"diagram_node:{right['node_id']}", "doc_id": "", "source_ref": {"diagram_id": diagram_id, "node_id": right["node_id"]}, "text_snapshot": right.get("text_raw", "")},
                        "candidate_provenance": {"generator": "same_diagram_sibling_node", "diagram_id": diagram_id, "type": left.get("type_candidate")},
                        "gold": {"relation": None, "alignment": None, "unknown_reason": None, "confidence": None},
                        "adjudication": {"status": "pending", "final_relation": None},
                    }
                )
    return out


def build(output: Path, target_per_stratum: int) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    candidates = read_jsonl(CANDIDATES)
    corpus = {
        "claims": read_jsonl(CORPUS / "claims.jsonl"),
        "tables": read_jsonl(CORPUS / "tables.jsonl"),
        "diagram_nodes": read_jsonl(CORPUS / "diagram_nodes.jsonl"),
        "diagrams": read_jsonl(CORPUS / "diagrams.jsonl"),
    }
    candidates = [set_pilot_fields(row, "alignment", "L1" if row.get("tier") == "P1" else "L2") for row in candidates]
    by_stratum: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        source_type = row["source"]["asset_type"]
        target_type = row["target"]["asset_type"]
        doc = str(row["source"].get("doc_id") or row["target"].get("doc_id") or "")
        by_stratum[(f"{source_type}-{target_type}", doc)].append(row)
    sampled: list[dict[str, Any]] = []
    for key, rows in sorted(by_stratum.items()):
        rows.sort(key=lambda row: stable_rank(row["example_id"]))
        sampled.extend(rows[:target_per_stratum])
    hard = hard_negative_rows(corpus)
    diagram_docs = {
        str(row.get("diagram_id", "")): str(row.get("doc_id", ""))
        for row in corpus["diagrams"]
    }
    for row in hard:
        diagram_id = str(row["source"].get("source_ref", {}).get("diagram_id", ""))
        doc = str(row["source"].get("doc_id") or row["target"].get("doc_id") or diagram_docs.get(diagram_id, ""))
        row["source"]["doc_id"] = doc
        row["target"]["doc_id"] = doc
        row["split"] = {"fold": fold_for(doc), "name": split_name(fold_for(doc)), "document_group": f"doc-{doc}"}
    # Diagram nodes lack doc_id in the source table; they stay in the pilot but
    # are marked for diagram-level split resolution through diagram_id.
    hard.sort(key=lambda row: stable_rank(row["example_id"]))
    sampled.extend(hard[: target_per_stratum * 4])
    sampled.sort(key=lambda row: row["example_id"])
    count = write_jsonl(output / "pilot_annotation.jsonl", sampled)
    summary = {
        "schema_version": "alignment_pilot_v1",
        "count": count,
        "source_candidates": len(candidates),
        "hard_negative_candidates": len(hard),
        "target_per_stratum": target_per_stratum,
        "gold_labels_written": False,
        "unknown_is_not_negative": True,
        "candidate_is_not_gold": True,
        "split_policy": "document_hash_fold_v1",
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--target-per-stratum", type=int, default=40)
    args = parser.parse_args()
    print(json.dumps(build(args.output.resolve(), args.target_per_stratum), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
