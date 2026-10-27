#!/usr/bin/env python3
"""Build silver training pairs for occurrence linking from structured_corpus_v1.

Silver positives (label=1, basis="explicit_identifier") pair two objects of
different kinds in the same document that share at least one explicit
identifier (P1 anchors). Deterministic negatives (label=0,
basis="sibling_distinct_identifier") pair same-kind siblings whose explicit
identifier sets are provably distinct. Every pair whose identity cannot be
decided from identifiers (same normalized name, shared same-kind identifier,
or a cross-document combination) is written to ``excluded.jsonl`` instead of
receiving a label. No human labels are produced (quality_tier="silver").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

CORPUS = BASE / "data/gjb_438c/structured_corpus_v1"
DEFAULT_OUT = BASE / "data/gjb_438c/training_pairs_v1"

ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
_WS_RE = re.compile(r"[\s，。；：:、,./（）()\-_]")
KINDS = ("claim", "diagram_node", "requirement", "table_row")
SPLIT_MAP = {0: "test", 1: "dev", 2: "train", 3: "train"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"


def fold_for(doc_id: str) -> int:
    return int(hashlib.sha1(f"doc:{doc_id}".encode("utf-8")).hexdigest()[:12], 16) % 4


def ids_of(text: str) -> set[str]:
    return set(ID_RE.findall(text or ""))


def normalized_name(text: str) -> str:
    return _WS_RE.sub("", text or "").lower()


def _unique_id(counter: Counter[str], base: str) -> str:
    seen = counter[base]
    counter[base] += 1
    return base if seen == 0 else f"{base}#{seen + 1}"


def collect_objects(corpus: Path) -> list[dict[str, Any]]:
    """Collect linkable occurrence objects (no empty texts)."""
    claims = read_jsonl(corpus / "claims.jsonl")
    requirements = read_jsonl(corpus / "requirements.jsonl")
    nodes = read_jsonl(corpus / "diagram_nodes.jsonl")
    diagrams = read_jsonl(corpus / "diagrams.jsonl")
    tables = read_jsonl(corpus / "tables.jsonl")
    diagram_docs = {str(row.get("diagram_id", "")): str(row.get("doc_id", "")) for row in diagrams}

    objects: list[dict[str, Any]] = []
    counter: Counter[str] = Counter()

    def add(occurrence_id: str, kind: str, doc_id: str, section: str, text: str, **extra: Any) -> None:
        text = str(text)
        if not text.strip():
            return
        objects.append(
            {
                "occurrence_id": _unique_id(counter, occurrence_id),
                "kind": kind,
                "doc_id": str(doc_id),
                "section": str(section),
                "text": text,
                "ids": ids_of(text),
                **extra,
            }
        )

    for row in claims:
        add(f"claim:{row.get('claim_id', '')}", "claim", row.get("doc_id", ""), row.get("section", ""), row.get("raw_text", ""))
    for row in requirements:
        add(
            f"requirement:{row.get('requirement_id', '')}",
            "requirement",
            row.get("doc_id", ""),
            row.get("section", ""),
            row.get("raw_text", ""),
        )
    for row in nodes:
        add(
            f"diagram_node:{row.get('node_id', '')}",
            "diagram_node",
            diagram_docs.get(str(row.get("diagram_id", "")), ""),
            "",
            row.get("text_raw", ""),
            diagram_id=str(row.get("diagram_id", "")),
            type_candidate=str(row.get("type_candidate", "")),
        )
    for row in tables:
        table_id = str(row.get("table_id", ""))
        # thead-aware: data rows start after header rows (C8); default 1
        # keeps the legacy rows[1:] heuristic for corpora without the field
        header_row_count = int(row.get("header_row_count", 1))
        for index, cells in enumerate(row.get("rows", [])[header_row_count:], start=header_row_count):
            add(
                f"table_row:{table_id}:row={index}",
                "table_row",
                row.get("doc_id", ""),
                row.get("section", ""),
                " | ".join(str(cell) for cell in cells),
                table_id=table_id,
                row_index=index,
            )
    return objects


def endpoint(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "occurrence_id": obj["occurrence_id"],
        "kind": obj["kind"],
        "doc_id": obj["doc_id"],
        "section": obj["section"],
        "text": obj["text"],
    }


def pair_record(
    left: dict[str, Any],
    right: dict[str, Any],
    label: int,
    basis: str,
    generator: str,
    shared: set[str],
) -> dict[str, Any]:
    anchor, candidate = sorted((left, right), key=lambda obj: obj["occurrence_id"])
    fold = fold_for(anchor["doc_id"])
    return {
        "pair_id": stable_id("PAIR", anchor["occurrence_id"], candidate["occurrence_id"], basis),
        "anchor": endpoint(anchor),
        "candidate": endpoint(candidate),
        "label": label,
        "label_basis": basis,
        "generator": generator,
        "split": SPLIT_MAP[fold],
        "fold": fold,
        "quality_tier": "silver",
        "features": {
            "shared_identifiers": sorted(shared),
            "same_section": bool(anchor["section"]) and anchor["section"] == candidate["section"],
            "kind_pair": "+".join(sorted((anchor["kind"], candidate["kind"]))),
        },
    }


def excluded_record(
    left: dict[str, Any],
    right: dict[str, Any],
    generator: str,
    reason: str,
    note: str,
) -> dict[str, Any]:
    anchor, candidate = sorted((left, right), key=lambda obj: obj["occurrence_id"])
    return {
        "pair_id": stable_id("EXCL", anchor["occurrence_id"], candidate["occurrence_id"], reason),
        "anchor_id": anchor["occurrence_id"],
        "candidate_id": candidate["occurrence_id"],
        "anchor_kind": anchor["kind"],
        "candidate_kind": candidate["kind"],
        "doc_ids": sorted({anchor["doc_id"], candidate["doc_id"]}),
        "generator": generator,
        "reason": reason,
        "note": note,
    }


def sibling_outcome(
    left: dict[str, Any],
    right: dict[str, Any],
    require_distinct_ids: bool,
    raw_text_must_differ: bool = False,
) -> tuple[str, str]:
    """Decide ("negative"|"excluded"|"", reason_or_note) for a same-kind sibling pair.

    Priority: shared identifiers make identity ambiguous (excluded); disjoint
    non-empty identifier sets prove distinctness (negative); otherwise a shared
    normalized name without identifier distinction is excluded, and kind-specific
    rules decide whether the pair is a confident negative or simply unlabelled.
    """
    if left["ids"] & right["ids"]:
        return "excluded", "shared_identifier"
    if left["ids"] and right["ids"]:
        if raw_text_must_differ and left["text"] == right["text"]:
            return "", ""
        return "negative", ""
    if left["text"] == right["text"] or normalized_name(left["text"]) == normalized_name(right["text"]):
        return "excluded", "same_normalized_name_no_identifier"
    if require_distinct_ids:
        return "", ""
    return "negative", ""


def build(corpus: Path, out: Path) -> dict[str, Any]:
    corpus = corpus.resolve()
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    objects = collect_objects(corpus)
    by_doc_kind: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for obj in objects:
        by_doc_kind[(obj["doc_id"], obj["kind"])].append(obj)

    pairs: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    counts: Counter[str] = Counter()

    def emit(left: dict[str, Any], right: dict[str, Any]) -> bool:
        key = tuple(sorted((left["occurrence_id"], right["occurrence_id"])))
        if key in seen_pairs:
            return False
        seen_pairs.add(key)
        return True

    # ── silver positives: explicit identifier shared across kinds, same doc ──
    docs = sorted({doc for doc, _ in by_doc_kind})
    for doc in docs:
        for index, kind_a in enumerate(KINDS):
            for kind_b in KINDS[index + 1 :]:
                group_a = by_doc_kind.get((doc, kind_a), [])
                group_b = by_doc_kind.get((doc, kind_b), [])
                for left in group_a:
                    for right in group_b:
                        shared = left["ids"] & right["ids"]
                        if not shared or not emit(left, right):
                            continue
                        pairs.append(pair_record(left, right, 1, "explicit_identifier", "cross_kind_shared_identifier", shared))
                        counts["positive"] += 1

    # ── deterministic negatives: same-table adjacent data rows ──
    tables: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for obj in objects:
        if obj["kind"] == "table_row":
            tables[obj["table_id"]].append(obj)
    for table_rows in tables.values():
        table_rows.sort(key=lambda obj: obj["row_index"])
        for left, right in zip(table_rows, table_rows[1:]):
            if right["row_index"] - left["row_index"] != 1:
                continue
            outcome, note = sibling_outcome(left, right, require_distinct_ids=True)
            if outcome == "negative" and emit(left, right):
                pairs.append(pair_record(left, right, 0, "sibling_distinct_identifier", "same_table_adjacent_rows", set()))
                counts["negative"] += 1
            elif outcome == "excluded":
                excluded.append(excluded_record(left, right, "same_table_adjacent_rows", "unknown_identity", note))
                counts["excluded_unknown_identity"] += 1

    # ── deterministic negatives: sibling nodes in the same diagram ──
    diagram_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for obj in objects:
        if obj["kind"] == "diagram_node":
            diagram_groups[(obj["diagram_id"], obj["type_candidate"])].append(obj)
    for group in diagram_groups.values():
        group.sort(key=lambda obj: obj["occurrence_id"])
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                outcome, note = sibling_outcome(left, right, require_distinct_ids=False, raw_text_must_differ=True)
                if outcome == "negative" and emit(left, right):
                    pairs.append(pair_record(left, right, 0, "sibling_distinct_identifier", "same_diagram_sibling_nodes", set()))
                    counts["negative"] += 1
                elif outcome == "excluded":
                    excluded.append(excluded_record(left, right, "same_diagram_sibling_nodes", "unknown_identity", note))
                    counts["excluded_unknown_identity"] += 1

    # ── deterministic negatives: requirements in the same doc and section ──
    req_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for obj in objects:
        if obj["kind"] == "requirement":
            req_groups[(obj["doc_id"], obj["section"])].append(obj)
    for group in req_groups.values():
        group.sort(key=lambda obj: obj["occurrence_id"])
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                outcome, note = sibling_outcome(left, right, require_distinct_ids=True)
                if outcome == "negative" and emit(left, right):
                    pairs.append(pair_record(left, right, 0, "sibling_distinct_identifier", "same_section_requirements", set()))
                    counts["negative"] += 1
                elif outcome == "excluded":
                    excluded.append(excluded_record(left, right, "same_section_requirements", "unknown_identity", note))
                    counts["excluded_unknown_identity"] += 1

    # ── defensive guards: cross-document pairs are never trainable ──
    kept_pairs: list[dict[str, Any]] = []
    for row in pairs:
        if row["anchor"]["doc_id"] != row["candidate"]["doc_id"]:
            excluded.append(
                {
                    "pair_id": stable_id("EXCL", row["anchor"]["occurrence_id"], row["candidate"]["occurrence_id"], "cross_doc"),
                    "anchor_id": row["anchor"]["occurrence_id"],
                    "candidate_id": row["candidate"]["occurrence_id"],
                    "anchor_kind": row["anchor"]["kind"],
                    "candidate_kind": row["candidate"]["kind"],
                    "doc_ids": sorted({row["anchor"]["doc_id"], row["candidate"]["doc_id"]}),
                    "generator": row["generator"],
                    "reason": "cross_doc",
                    "note": "pair endpoints live in different documents",
                }
            )
            counts["excluded_cross_doc"] += 1
            continue
        kept_pairs.append(row)
    pairs = kept_pairs

    pairs.sort(key=lambda row: row["pair_id"])
    excluded.sort(key=lambda row: row["pair_id"])
    split_counts = Counter(row["split"] for row in pairs)
    manifest_path = corpus / "manifest.json"
    summary = {
        "schema_version": "training_pairs_v1",
        "counts": {
            "objects": len(objects),
            "object_by_kind": dict(sorted(Counter(obj["kind"] for obj in objects).items())),
            "pairs": len(pairs),
            "positive": sum(1 for row in pairs if row["label"] == 1),
            "negative": sum(1 for row in pairs if row["label"] == 0),
            "split_train": split_counts.get("train", 0),
            "split_dev": split_counts.get("dev", 0),
            "split_test": split_counts.get("test", 0),
            "excluded": len(excluded),
            "excluded_unknown_identity": counts["excluded_unknown_identity"],
            "excluded_cross_doc": counts["excluded_cross_doc"],
            "by_label_basis": dict(sorted(Counter(row["label_basis"] for row in pairs).items())),
            "by_kind_pair": dict(sorted(Counter(row["features"]["kind_pair"] for row in pairs).items())),
        },
        "fold_rule": "fold=int(sha1(f'doc:{doc_id}')[:12],16)%4; 0=test 1=dev 2=train 3=train",
        "policy": {
            "quality_tier": "silver",
            "no_human_labels": True,
            "positive_requires_shared_identifier_and_distinct_kinds": True,
            "negative_requires_distinct_identifier_sets": True,
            "diagram_sibling_negative_requires_different_text": True,
            "same_normalized_name_without_identifier_distinction_excluded": True,
            "same_kind_shared_identifier_excluded": True,
            "cross_document_pairs_excluded": True,
        },
        "source_corpus": str(corpus.relative_to(BASE)) if corpus.is_relative_to(BASE) else str(corpus),
        "source_manifest_sha256": sha256_file(manifest_path) if manifest_path.exists() else None,
    }
    files = {
        "pairs": write_jsonl(out / "pairs.jsonl", pairs),
        "excluded": write_jsonl(out / "excluded.jsonl", excluded),
    }
    summary["counts"].update(files)
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": "training_pairs_v1",
        "files": {
            name: sha256_file(out / name)
            for name in ("pairs.jsonl", "excluded.jsonl", "summary.json")
        },
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.corpus, args.output), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
