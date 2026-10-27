#!/usr/bin/env python3
"""Build a conservative evidence graph from ``structured_corpus_v1``.

The default path is deterministic and offline. ``--embedding`` optionally
adds local frozen-encoder candidates, but embedding similarity never confirms
identity by itself. The output is a candidate graph, not a gold annotation.
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
DEFAULT_OUTPUT = BASE / "data/gjb_438c/evidence_graph_v1"

_CJK = re.compile(r"[\u4e00-\u9fff]+")
_LATIN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:16]}"


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tokens(text: str) -> set[str]:
    result: set[str] = set()
    for segment in _CJK.findall(text or ""):
        result.update(segment[i : i + 2] for i in range(len(segment) - 1))
    result.update(token.lower() for token in _LATIN.findall(text or ""))
    return {token for token in result if token}


def overlap(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a | b), 1)


def normalize_name(value: str) -> str:
    return re.sub(r"[\s，。；：:、,./（）()\-_]", "", value or "").lower()


def ids(value: str) -> set[str]:
    return set(_ID_RE.findall(value or ""))


def load_corpus() -> dict[str, list[dict[str, Any]]]:
    names = (
        "requirements",
        "claims",
        "tables",
        "diagram_nodes",
        "diagram_edges",
        "diagrams",
    )
    return {name: read_jsonl(CORPUS / f"{name}.jsonl") for name in names}


def node_id(kind: str, row: dict[str, Any]) -> str:
    for key in ("requirement_id", "claim_id", "table_id", "node_id", "edge_id", "diagram_id"):
        if row.get(key):
            return f"{kind}:{row[key]}"
    return stable_id(kind, json.dumps(row, ensure_ascii=False, sort_keys=True))


def make_nodes(corpus: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for kind, rows in corpus.items():
        if kind == "diagram_edges":
            continue
        for row in rows:
            identifier = node_id(kind, row)
            if kind == "requirements":
                text = row.get("raw_text", "")
                node_type = "requirement"
            elif kind == "claims":
                text = row.get("raw_text", "")
                node_type = "claim"
            elif kind == "tables":
                text = row.get("caption_raw", "")
                node_type = "table"
            elif kind == "diagram_nodes":
                text = row.get("text_raw", "")
                node_type = "diagram_node"
            elif kind == "diagrams":
                text = row.get("source", "")
                node_type = "diagram"
            else:
                continue
            nodes.append(
                {
                    "node_id": identifier,
                    "node_type": node_type,
                    "doc_id": str(row.get("doc_id", "")),
                    "section": str(row.get("section", "")),
                    "text": text,
                    "raw_record_ref": identifier,
                    "quality_tier": "candidate",
                    "status": "active",
                }
            )
    return nodes


def requirement_candidates(
    requirements: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    tables: list[dict[str, Any]],
    diagram_nodes: list[dict[str, Any]],
    embedding: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    links: list[dict[str, Any]] = []
    embedding_stats: dict[str, Any] = {"enabled": embedding, "mode": "disabled", "covered": 0}
    embedder: Any = None
    if embedding:
        try:
            from algorithms.blackboard.embedding_channel import EmbeddingChannel

            embedder = EmbeddingChannel(prefer="local")
            embedding_stats["mode"] = embedder.ensure()
            embedding_stats["threshold"] = embedder.effective_th
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            embedding_stats["mode"] = "unavailable"
            embedding_stats["error"] = type(exc).__name__

    target_groups = [
        ("claim", claims, lambda row: row.get("raw_text", "")),
        ("table", tables, lambda row: row.get("caption_raw", "") + " " + " ".join(
            " | ".join(cell for cell in cells) for cells in row.get("rows", [])[:5]
        )),
        ("diagram_node", diagram_nodes, lambda row: row.get("text_raw", "")),
    ]
    for requirement in requirements:
        source_id = node_id("requirements", requirement)
        source_text = str(requirement.get("raw_text", ""))
        source_ids = ids(source_text)
        source_doc = str(requirement.get("doc_id", ""))
        source_section = str(requirement.get("section", ""))
        for target_kind, rows, text_fn in target_groups:
            scored: list[tuple[float, dict[str, Any], str, list[str]]] = []
            target_texts: list[str] = []
            for target in rows:
                target_doc = str(target.get("doc_id", ""))
                if target_doc != source_doc:
                    continue
                target_text = str(text_fn(target))
                target_ids = ids(target_text)
                exact_ids = sorted(source_ids & target_ids)
                lexical = overlap(source_text, target_text)
                section_bonus = 0.15 if source_section and source_section == str(target.get("section", "")) else 0.0
                identity_bonus = 0.7 if exact_ids else 0.0
                score = min(1.0, identity_bonus + section_bonus + lexical)
                evidence = ["same_doc"]
                relation = "semantic_neighbor"
                if exact_ids:
                    relation = "same_identity"
                    evidence.append("shared_identifier")
                elif lexical >= 0.32 and section_bonus:
                    relation = "candidate_alignment"
                    evidence.append("section_and_lexical_overlap")
                if score >= 0.28:
                    scored.append((score, target, relation, evidence))
                    target_texts.append(target_text)
            if embedder is not None and scored and target_texts:
                matches = embedder.match([source_text], target_texts)
                if matches:
                    embedding_stats["covered"] += 1
                    for _, index, value in matches:
                        score, target, relation, evidence = scored[index]
                        score = max(score, min(0.45, float(value) * 0.45))
                        if relation == "semantic_neighbor" and value >= embedder.effective_th:
                            evidence = evidence + ["frozen_embedding_candidate"]
                        scored[index] = (score, target, relation, evidence)
            for score, target, relation, evidence in sorted(scored, reverse=True, key=lambda item: item[0])[:10]:
                target_id = node_id(target_kind + "s", target)
                if relation == "same_identity" and "shared_identifier" not in evidence:
                    relation = "candidate_alignment"
                links.append(
                    {
                        "link_id": stable_id("LNK", source_id, target_id),
                        "source_id": source_id,
                        "target_id": target_id,
                        "relation_type": relation,
                        "direction": "directed",
                        "score": round(float(score), 6),
                        "evidence": evidence,
                        "status": "candidate" if relation != "same_identity" else "accepted",
                        "quality_tier": "candidate",
                        "method": "lexical_scope_gate_plus_optional_frozen_embedding",
                    }
                )
    return links, embedding_stats


def make_entities(requirements: list[dict[str, Any]], links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in requirements:
        identifier = row.get("requirement_id") or node_id("requirements", row)
        key = normalize_name(str(identifier))
        grouped[key].append(node_id("requirements", row))
    entities = []
    for key, occurrence_ids in sorted(grouped.items()):
        supporting = [link["link_id"] for link in links if link["source_id"] in occurrence_ids and link["status"] == "accepted"]
        entities.append(
            {
                "entity_candidate_id": stable_id("ENT", key),
                "entity_type": "requirement",
                "canonical_key": key,
                "occurrence_ids": sorted(set(occurrence_ids)),
                "supporting_link_ids": supporting,
                "quality_tier": "candidate",
                "status": "candidate",
            }
        )
    return entities


def make_items(entities: list[dict[str, Any]], links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    links_by_source: dict[str, list[str]] = defaultdict(list)
    for link in links:
        if link["status"] == "accepted":
            links_by_source[link["source_id"]].append(link["link_id"])
    return [
        {
            "item_id": stable_id("ITEM", entity["entity_candidate_id"]),
            "entity_candidate_id": entity["entity_candidate_id"],
            "occurrence_ids": entity["occurrence_ids"],
            "accepted_link_ids": sorted(set(entity["supporting_link_ids"])),
            "unresolved_link_ids": sorted(
                link["link_id"]
                for link in links
                if link["source_id"] in entity["occurrence_ids"] and link["status"] != "accepted"
            ),
            "completeness": "partial" if entity["supporting_link_ids"] else "open",
            "quality_tier": "candidate",
        }
        for entity in entities
    ]


def make_findings(
    requirements: list[dict[str, Any]], claims: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contracts = [
        {
            "quality_type": "duplicate_explicit_requirement_id",
            "target_schema": "RequirementSet",
            "evidence_obligations": ["same_document", "shared_explicit_id"],
            "validator": "deterministic_duplicate_id",
        },
        {
            "quality_type": "candidate_numeric_conflict",
            "target_schema": "ClaimPair",
            "evidence_obligations": ["same_identity", "same_scope", "value_parse", "unit_normalization"],
            "validator": "candidate_only_numeric_difference",
        },
    ]
    findings = []
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in requirements:
        for identifier in row.get("features", {}).get("requirement_ids", []):
            grouped[(str(row.get("doc_id", "")), identifier)].append(row)
    for (doc_id, identifier), rows in sorted(grouped.items()):
        if len(rows) > 1:
            refs = [node_id("requirements", row) for row in rows]
            findings.append(
                {
                    "finding_id": stable_id("FND", "duplicate", doc_id, identifier),
                    "finding_type": "duplicate_explicit_requirement_id",
                    "status": "candidate",
                    "severity": "warning",
                    "target_refs": refs,
                    "evidence_refs": refs,
                    "quality_contract": contracts[0],
                    "root_cause_candidates": ["source_defect", "parse_uncertainty"],
                    "quality_tier": "candidate",
                }
            )
    return findings, contracts


def build(output: Path, embedding: bool) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus()
    nodes = make_nodes(corpus)
    links, embedding_stats = requirement_candidates(
        corpus["requirements"],
        corpus["claims"],
        corpus["tables"],
        corpus["diagram_nodes"],
        embedding,
    )
    entities = make_entities(corpus["requirements"], links)
    items = make_items(entities, links)
    findings, contracts = make_findings(corpus["requirements"], corpus["claims"])
    files = {
        "nodes": write_jsonl(output / "nodes.jsonl", nodes),
        "candidate_links": write_jsonl(output / "candidate_links.jsonl", links),
        "entity_candidates": write_jsonl(output / "entity_candidates.jsonl", entities),
        "items": write_jsonl(output / "items.jsonl", items),
        "quality_contracts": write_jsonl(output / "quality_contracts.jsonl", contracts),
        "findings": write_jsonl(output / "findings.jsonl", findings),
    }
    summary = {
        "schema_version": "evidence_graph_v1",
        "method": "lexical_scope_gate_plus_optional_frozen_embedding",
        "source_corpus": str(CORPUS.relative_to(BASE)),
        "source_corpus_sha256": sha256(CORPUS / "summary.json"),
        "counts": files,
        "embedding": embedding_stats,
        "policy": {
            "candidate_is_not_gold": True,
            "embedding_cannot_confirm_identity": True,
            "geo_or_semantic_links_require_review": True,
            "findings_are_candidates": True,
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": summary["schema_version"],
        "files": {name: sha256(output / f"{name}.jsonl") for name in files},
        "summary_sha256": sha256(output / "summary.json"),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--embedding", action="store_true", help="Add local frozen-encoder candidates")
    args = parser.parse_args()
    summary = build(args.output.resolve(), args.embedding)
    print(json.dumps(summary["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
