#!/usr/bin/env python3
"""Build ``evidence_graph_v2`` from ``evidence_graph_v1`` + ``structured_corpus_v1``.

Pipeline (deterministic, offline):
1. Upgrade v1 identity links whose evidence contains ``shared_identifier`` to
   ``quality_tier="silver"`` with ``label_basis="explicit_identifier"``; every
   other link keeps the v1 candidate tier and all v1 fields.
2. Aggregate silver link endpoints into silver items via union-find
   (``aggregation_method="silver_identifier_union"``).
3. Rebuild findings under a QualityContract obligation checker: each contract
   lists obligations, each obligation is judged from deterministic evidence,
   and any missing obligation downgrades the finding status to
   ``insufficient``.

Silver labels are weak supervision derived from explicit identifiers, never
gold: items stay ``completeness="partial"`` and findings never reach a
``confirmed`` status.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.build_evidence_graph import node_id, read_jsonl, sha256, stable_id, write_jsonl

DEFAULT_INPUT = BASE / "data/gjb_438c/evidence_graph_v1"
DEFAULT_OUTPUT = BASE / "data/gjb_438c/evidence_graph_v2"
CORPUS = BASE / "data/gjb_438c/structured_corpus_v1"

SCHEMA_VERSION = "evidence_graph_v2"
DUPLICATE_CONTRACT = "duplicate_explicit_requirement_id"
NUMERIC_CONTRACT = "candidate_numeric_conflict"
SILVER_LABEL_BASIS = "explicit_identifier"
DUPLICATE_ROOT_CAUSES = ["source_defect", "parse_uncertainty"]
NUMERIC_ROOT_CAUSES = ["source_defect", "parse_uncertainty", "scope_difference"]


class UnionFind:
    """Deterministic union-find over string node ids."""

    def __init__(self) -> None:
        self._parent: dict[str, str] = {}

    def find(self, node: str) -> str:
        if node not in self._parent:
            self._parent[node] = node
        root = node
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[node] != root:
            self._parent[node], node = root, self._parent[node]
        return root

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if left_root > right_root:
            left_root, right_root = right_root, left_root
        self._parent[right_root] = left_root

    def components(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for node in self._parent:
            grouped[self.find(node)].append(node)
        return {root: sorted(members) for root, members in grouped.items()}


def is_silver_link(link: dict[str, Any]) -> bool:
    """A link is silver only if identity is backed by a shared explicit identifier."""
    evidence = link.get("evidence")
    return (
        link.get("relation_type") == "same_identity"
        and isinstance(evidence, list)
        and "shared_identifier" in evidence
    )


def upgrade_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy all v1 links, upgrading explicit-identifier identity links to silver."""
    upgraded: list[dict[str, Any]] = []
    for link in links:
        row = dict(link)
        if is_silver_link(link):
            row["quality_tier"] = "silver"
            row["label_basis"] = SILVER_LABEL_BASIS
        upgraded.append(row)
    return upgraded


def silver_items(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate silver link endpoints into items via union-find."""
    silver = [link for link in links if is_silver_link(link)]
    union_find = UnionFind()
    for link in silver:
        source = str(link.get("source_id", ""))
        target = str(link.get("target_id", ""))
        if source and target and source != target:
            union_find.union(source, target)
    link_ids_by_root: dict[str, list[str]] = defaultdict(list)
    for link in silver:
        source = str(link.get("source_id", ""))
        if source:
            link_ids_by_root[union_find.find(source)].append(str(link.get("link_id", "")))
    items: list[dict[str, Any]] = []
    for root, members in union_find.components().items():
        occurrence_ids = sorted(members)
        link_ids = sorted(set(link_ids_by_root.get(root, [])))
        items.append(
            {
                "item_id": stable_id("ITEM", *occurrence_ids),
                "occurrence_ids": occurrence_ids,
                "member_count": len(occurrence_ids),
                "link_ids": link_ids,
                "completeness": "partial",
                "quality_tier": "silver",
                "aggregation_method": "silver_identifier_union",
            }
        )
    items.sort(key=lambda item: item["item_id"])
    return items


def _parsed_quantities(claim: dict[str, Any]) -> list[dict[str, Any]]:
    quantities = (claim.get("features") or {}).get("quantities") or []
    return [q for q in quantities if isinstance(q, dict) and q.get("value") is not None]


def _quantity_key(quantity: dict[str, Any]) -> tuple[str, str, str]:
    value = quantity.get("value")
    unit = str(quantity.get("unit_raw") or "")
    return (type(value).__name__, json.dumps(value, sort_keys=True), unit)


def quantity_fingerprint(claim: dict[str, Any]) -> tuple[tuple[str, str, str], ...]:
    """Deterministic fingerprint of a claim's parsed quantities (value + unit)."""
    return tuple(sorted(_quantity_key(quantity) for quantity in _parsed_quantities(claim)))


def finding_status(obligations: dict[str, dict[str, Any]]) -> str:
    """All obligations satisfied -> candidate; any missing -> insufficient.

    ``confirmed`` is unreachable by design: silver is weak supervision, not gold.
    """
    for entry in obligations.values():
        if entry.get("status") != "satisfied":
            return "insufficient"
    return "candidate"


def judge_duplicate_obligations(
    doc_id: str,
    identifier: str,
    rows: list[dict[str, Any]],
    refs: list[str],
) -> dict[str, dict[str, Any]]:
    same_document = bool(doc_id) and all(str(row.get("doc_id", "")) == doc_id for row in rows)
    shared_explicit_id = all(
        identifier in ((row.get("features") or {}).get("requirement_ids") or []) for row in rows
    )
    return {
        "same_document": {
            "status": "satisfied" if same_document else "insufficient",
            "evidence_refs": refs if same_document else [],
        },
        "shared_explicit_id": {
            "status": "satisfied" if shared_explicit_id else "insufficient",
            "evidence_refs": refs if shared_explicit_id else [],
        },
    }


def duplicate_findings(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic duplicate explicit requirement id findings with obligation checks."""
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(requirements):
        for identifier in (row.get("features") or {}).get("requirement_ids") or []:
            grouped[(str(row.get("doc_id", "")), str(identifier))].append(index)
    findings: list[dict[str, Any]] = []
    for (doc_id, identifier), indexes in sorted(grouped.items()):
        rows = [requirements[index] for index in dict.fromkeys(indexes)]
        if len(rows) < 2:
            continue
        refs = sorted(node_id("requirements", row) for row in rows)
        obligations = judge_duplicate_obligations(doc_id, identifier, rows, refs)
        findings.append(
            {
                "finding_id": stable_id("FND", "duplicate", doc_id, identifier),
                "finding_type": DUPLICATE_CONTRACT,
                "status": finding_status(obligations),
                "severity": "warning",
                "target_refs": refs,
                "evidence_refs": refs,
                "minimal_sufficient_evidence": refs,
                "obligation_status": obligations,
                "root_cause_candidates": DUPLICATE_ROOT_CAUSES,
                "quality_tier": "candidate",
            }
        )
    findings.sort(key=lambda row: row["finding_id"])
    return findings


def judge_numeric_obligations(
    left_ref: str,
    right_ref: str,
    left_row: dict[str, Any],
    right_row: dict[str, Any],
    item_id: str,
    link_ids: list[str],
) -> dict[str, dict[str, Any]]:
    claim_pair_refs = [left_ref, right_ref]
    left_fp = quantity_fingerprint(left_row)
    right_fp = quantity_fingerprint(right_row)
    quantities = _parsed_quantities(left_row) + _parsed_quantities(right_row)
    units_confirmed = bool(quantities) and all(
        quantity.get("normalization_status") == "confirmed" for quantity in quantities
    )
    value_parse_ok = bool(left_fp) and bool(right_fp)
    # the silver item is the identity evidence: finding -> item_id -> item.link_ids
    same_identity_ok = bool(item_id) and bool(link_ids)
    return {
        "same_identity": {
            "status": "satisfied" if same_identity_ok else "insufficient",
            "evidence_refs": [item_id] if same_identity_ok else [],
        },
        "same_scope": {"status": "insufficient", "evidence_refs": []},
        "value_parse": {
            "status": "satisfied" if value_parse_ok else "insufficient",
            "evidence_refs": claim_pair_refs if value_parse_ok else [],
        },
        "unit_normalization": {
            "status": "satisfied" if units_confirmed else "insufficient",
            "evidence_refs": claim_pair_refs if units_confirmed else [],
        },
    }


def numeric_findings(claims: list[dict[str, Any]], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Candidate numeric conflicts: claim pairs in one silver item with differing values.

    same_scope evidence does not exist yet, so every finding of this type is
    downgraded to ``insufficient`` and can never be confirmed here.
    """
    claims_by_node = {node_id("claims", row): row for row in claims}
    findings: list[dict[str, Any]] = []
    for item in items:
        claim_refs = [ref for ref in item["occurrence_ids"] if ref.startswith("claims:")]
        item_id = str(item.get("item_id", ""))
        link_ids = sorted(item.get("link_ids") or [])
        for left in range(len(claim_refs)):
            for right in range(left + 1, len(claim_refs)):
                left_ref, right_ref = claim_refs[left], claim_refs[right]
                left_row = claims_by_node.get(left_ref)
                right_row = claims_by_node.get(right_ref)
                if left_row is None or right_row is None:
                    continue
                left_fp = quantity_fingerprint(left_row)
                right_fp = quantity_fingerprint(right_row)
                if not left_fp or not right_fp or left_fp == right_fp:
                    continue
                obligations = judge_numeric_obligations(
                    left_ref, right_ref, left_row, right_row, item_id, link_ids
                )
                claim_pair_refs = [left_ref, right_ref]
                findings.append(
                    {
                        "finding_id": stable_id("FND", "numeric", left_ref, right_ref),
                        "finding_type": NUMERIC_CONTRACT,
                        "status": finding_status(obligations),
                        "severity": "warning",
                        "target_refs": claim_pair_refs,
                        "evidence_refs": sorted({item_id, left_ref, right_ref}),
                        "minimal_sufficient_evidence": [],
                        "obligation_status": obligations,
                        "root_cause_candidates": NUMERIC_ROOT_CAUSES,
                        "quality_tier": "candidate",
                    }
                )
    findings.sort(key=lambda row: row["finding_id"])
    return findings


def quality_contracts() -> list[dict[str, Any]]:
    """QualityContract definitions: obligations and how each is judged."""
    return [
        {
            "quality_type": DUPLICATE_CONTRACT,
            "target_schema": "RequirementSet",
            "validator": "deterministic_duplicate_id",
            "obligations": [
                {
                    "obligation_id": "same_document",
                    "check": "all_requirement_rows_share_doc_id",
                    "evidence_source": "structured_corpus_v1/requirements.jsonl",
                    "deterministic": True,
                },
                {
                    "obligation_id": "shared_explicit_id",
                    "check": "explicit_id_listed_in_every_row_features",
                    "evidence_source": "structured_corpus_v1/requirements.jsonl",
                    "deterministic": True,
                },
            ],
            "confirmation_rule": "all_obligations_satisfied",
            "allowed_finding_status": ["candidate", "insufficient"],
        },
        {
            "quality_type": NUMERIC_CONTRACT,
            "target_schema": "ClaimPair",
            "validator": "candidate_only_numeric_difference",
            "obligations": [
                {
                    "obligation_id": "same_identity",
                    "check": "claims_share_silver_identity_item",
                    "evidence_source": "evidence_graph_v2/links_v2.jsonl",
                    "deterministic": True,
                },
                {
                    "obligation_id": "same_scope",
                    "check": "claims_describe_same_parameter_scope",
                    "evidence_source": None,
                    "deterministic": False,
                },
                {
                    "obligation_id": "value_parse",
                    "check": "both_claims_have_parsed_quantities",
                    "evidence_source": "structured_corpus_v1/claims.jsonl",
                    "deterministic": True,
                },
                {
                    "obligation_id": "unit_normalization",
                    "check": "quantity_units_confirmed_normalized",
                    "evidence_source": "structured_corpus_v1/claims.jsonl",
                    "deterministic": True,
                },
            ],
            "confirmation_rule": "all_obligations_satisfied",
            "allowed_finding_status": ["candidate", "insufficient"],
        },
    ]


def policy_statements() -> dict[str, bool]:
    return {
        "silver_is_weak_supervision_not_gold": True,
        "silver_requires_shared_explicit_identifier": True,
        "silver_items_completeness_capped_at_partial": True,
        "numeric_conflict_requires_scope_evidence_before_confirmation": True,
        "obligation_missing_downgrades_status_to_insufficient": True,
        "findings_max_status_is_candidate": True,
    }


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(BASE))
    except ValueError:
        return str(path)


def build(graph_dir: Path, corpus_dir: Path, output: Path) -> dict[str, Any]:
    input_files = [
        ("evidence_graph_v1/candidate_links.jsonl", graph_dir / "candidate_links.jsonl"),
        ("evidence_graph_v1/findings.jsonl", graph_dir / "findings.jsonl"),
        ("structured_corpus_v1/requirements.jsonl", corpus_dir / "requirements.jsonl"),
        ("structured_corpus_v1/claims.jsonl", corpus_dir / "claims.jsonl"),
    ]
    missing = [label for label, path in input_files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing required inputs: {missing}")

    links_v1 = read_jsonl(graph_dir / "candidate_links.jsonl")
    findings_v1 = read_jsonl(graph_dir / "findings.jsonl")
    requirements = read_jsonl(corpus_dir / "requirements.jsonl")
    claims = read_jsonl(corpus_dir / "claims.jsonl")

    links = upgrade_links(links_v1)
    items = silver_items(links)
    duplicate_rows = duplicate_findings(requirements)
    numeric_rows = numeric_findings(claims, items)
    findings = sorted(duplicate_rows + numeric_rows, key=lambda row: row["finding_id"])
    contracts = quality_contracts()

    output.mkdir(parents=True, exist_ok=True)
    files = {
        "links_v2": write_jsonl(output / "links_v2.jsonl", links),
        "items_v2": write_jsonl(output / "items_v2.jsonl", items),
        "findings_v2": write_jsonl(output / "findings_v2.jsonl", findings),
        "quality_contracts_v2": write_jsonl(output / "quality_contracts_v2.jsonl", contracts),
    }
    status_counts: dict[str, int] = defaultdict(int)
    for finding in findings:
        status_counts[finding["status"]] += 1
    summary = {
        "schema_version": SCHEMA_VERSION,
        "method": "explicit_identifier_silver_upgrade_union_find_and_contract_obligations",
        "sources": {
            "evidence_graph_v1": _display(graph_dir),
            "structured_corpus_v1": _display(corpus_dir),
        },
        "source_sha256": {label: sha256(path) for label, path in input_files},
        "counts": {
            **files,
            "links_upgraded_to_silver": sum(1 for link in links if link.get("quality_tier") == "silver"),
            "findings_by_type": {
                DUPLICATE_CONTRACT: len(duplicate_rows),
                NUMERIC_CONTRACT: len(numeric_rows),
            },
            "findings_by_status": dict(status_counts),
            "input_links_v1": len(links_v1),
            "input_findings_v1": len(findings_v1),
            "input_requirements": len(requirements),
            "input_claims": len(claims),
        },
        "policy": policy_statements(),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "files": {name: sha256(output / f"{name}.jsonl") for name in files},
        "summary_sha256": sha256(output / "summary.json"),
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="evidence_graph_v1 directory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output directory")
    args = parser.parse_args()
    summary = build(args.input.resolve(), CORPUS, args.output.resolve())
    print(json.dumps(summary["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
