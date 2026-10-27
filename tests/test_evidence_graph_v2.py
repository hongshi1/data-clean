"""evidence_graph_v2: silver upgrade, union-find items, contract obligation checks."""

from __future__ import annotations

import hashlib
import json

from tools.build_evidence_graph_v2 import (
    build,
    duplicate_findings,
    numeric_findings,
    policy_statements,
    quality_contracts,
    silver_items,
    upgrade_links,
)


def _link(link_id, source, target, relation, evidence, status="candidate"):
    return {
        "link_id": link_id,
        "source_id": source,
        "target_id": target,
        "relation_type": relation,
        "direction": "directed",
        "score": 0.9,
        "evidence": evidence,
        "status": status,
        "quality_tier": "candidate",
        "method": "test_fixture",
    }


def _claim(claim_id, quantities):
    return {
        "claim_id": claim_id,
        "doc_id": "01",
        "section": "3.1",
        "raw_text": "claim text",
        "features": {"quantities": quantities, "requirement_ids": []},
    }


def _requirement(requirement_id, doc_id="01"):
    return {
        "requirement_id": requirement_id,
        "doc_id": doc_id,
        "section": "3.1",
        "raw_text": "requirement text",
        "features": {"requirement_ids": [requirement_id]},
    }


def test_silver_upgrade_only_for_shared_identifier_links():
    links = [
        _link(
            "L1",
            "requirements:R1",
            "claims:C1",
            "same_identity",
            ["same_doc", "shared_identifier"],
            status="accepted",
        ),
        _link("L2", "requirements:R1", "claims:C2", "same_identity", ["same_doc"]),
        _link(
            "L3",
            "requirements:R1",
            "claims:C3",
            "semantic_neighbor",
            ["same_doc", "shared_identifier"],
        ),
        _link("L4", "requirements:R2", "claims:C4", "candidate_alignment", ["section_and_lexical_overlap"]),
    ]

    upgraded = upgrade_links(links)
    by_id = {link["link_id"]: link for link in upgraded}

    assert by_id["L1"]["quality_tier"] == "silver"
    assert by_id["L1"]["label_basis"] == "explicit_identifier"
    for link_id in ("L2", "L3", "L4"):
        assert by_id[link_id]["quality_tier"] == "candidate"
        assert "label_basis" not in by_id[link_id]
    # v1 fields are preserved on the upgraded link
    assert by_id["L1"]["status"] == "accepted"
    assert by_id["L1"]["method"] == "test_fixture"
    assert by_id["L1"]["source_id"] == "requirements:R1"
    assert by_id["L1"]["evidence"] == ["same_doc", "shared_identifier"]
    # input rows are not mutated
    assert links[0]["quality_tier"] == "candidate"
    assert "label_basis" not in links[0]


def test_union_find_aggregates_three_nodes_two_edges():
    links = [
        _link("L1", "requirements:R1", "claims:C1", "same_identity", ["shared_identifier"]),
        _link("L2", "claims:C1", "claims:C2", "same_identity", ["shared_identifier"]),
        _link("L3", "requirements:R1", "claims:C2", "semantic_neighbor", ["same_doc"]),
        _link("L4", "requirements:R1", "claims:C9", "candidate_alignment", ["lexical_overlap"]),
    ]

    items = silver_items(links)

    assert len(items) == 1
    item = items[0]
    assert item["occurrence_ids"] == ["claims:C1", "claims:C2", "requirements:R1"]
    assert item["member_count"] == 3
    assert item["link_ids"] == ["L1", "L2"]
    assert item["completeness"] == "partial"
    assert item["quality_tier"] == "silver"
    assert item["aggregation_method"] == "silver_identifier_union"
    assert set(item) == {
        "item_id",
        "occurrence_ids",
        "member_count",
        "link_ids",
        "completeness",
        "quality_tier",
        "aggregation_method",
    }
    assert "claims:C9" not in item["occurrence_ids"]
    # deterministic item_id
    assert silver_items(links)[0]["item_id"] == item["item_id"]


def test_union_find_keeps_separate_components_apart():
    links = [
        _link("L1", "requirements:R1", "claims:C1", "same_identity", ["shared_identifier"]),
        _link("L2", "requirements:R2", "claims:C2", "same_identity", ["shared_identifier"]),
    ]

    items = silver_items(links)

    assert len(items) == 2
    assert all(item["member_count"] == 2 for item in items)
    assert items[0]["occurrence_ids"] != items[1]["occurrence_ids"]


def test_numeric_finding_insufficient_when_obligations_missing():
    claims = [
        _claim("C1", [{"value": 100, "unit_raw": "ms", "normalization_status": "candidate"}]),
        _claim("C2", [{"value": 200, "unit_raw": "ms", "normalization_status": "candidate"}]),
    ]
    links = [
        _link("L1", "requirements:R1", "claims:C1", "same_identity", ["shared_identifier"]),
        _link("L2", "requirements:R1", "claims:C2", "same_identity", ["shared_identifier"]),
    ]
    items = silver_items(links)

    findings = numeric_findings(claims, items)

    assert len(findings) == 1
    finding = findings[0]
    assert finding["finding_type"] == "candidate_numeric_conflict"
    assert finding["status"] == "insufficient"
    assert finding["status"] != "confirmed"
    obligations = finding["obligation_status"]
    assert obligations["same_identity"]["status"] == "satisfied"
    assert obligations["same_identity"]["evidence_refs"] == [items[0]["item_id"]]
    assert obligations["same_scope"] == {"status": "insufficient", "evidence_refs": []}
    assert obligations["value_parse"]["status"] == "satisfied"
    assert obligations["unit_normalization"]["status"] == "insufficient"
    assert finding["minimal_sufficient_evidence"] == []
    assert finding["quality_tier"] == "candidate"
    assert finding["target_refs"] == ["claims:C1", "claims:C2"]
    assert finding["evidence_refs"] == sorted({items[0]["item_id"], "claims:C1", "claims:C2"})


def test_numeric_finding_not_emitted_for_equal_values():
    claims = [
        _claim("C1", [{"value": 100, "unit_raw": "ms", "normalization_status": "candidate"}]),
        _claim("C2", [{"value": 100, "unit_raw": "ms", "normalization_status": "candidate"}]),
    ]
    links = [
        _link("L1", "requirements:R1", "claims:C1", "same_identity", ["shared_identifier"]),
        _link("L2", "requirements:R1", "claims:C2", "same_identity", ["shared_identifier"]),
    ]
    items = silver_items(links)

    assert numeric_findings(claims, items) == []


def test_duplicate_finding_obligations_satisfied_status_candidate():
    requirements = [
        _requirement("SYS-GN-001"),
        _requirement("SYS-GN-001"),
        _requirement("SYS-GN-002"),
    ]

    findings = duplicate_findings(requirements)

    assert len(findings) == 1
    finding = findings[0]
    assert finding["finding_type"] == "duplicate_explicit_requirement_id"
    assert finding["status"] == "candidate"
    assert set(finding["obligation_status"]) == {"same_document", "shared_explicit_id"}
    assert all(entry["status"] == "satisfied" for entry in finding["obligation_status"].values())
    # both rows carry the explicit id, occurrence-preserving refs keep the multiplicity
    assert finding["target_refs"] == ["requirements:SYS-GN-001", "requirements:SYS-GN-001"]
    assert finding["minimal_sufficient_evidence"] == finding["target_refs"]


def test_no_gold_fields_in_outputs():
    links = upgrade_links(
        [
            _link("L1", "requirements:R1", "claims:C1", "same_identity", ["shared_identifier"]),
            _link("L2", "requirements:R1", "claims:C2", "same_identity", ["shared_identifier"]),
        ]
    )
    items = silver_items(links)
    claims = [
        _claim("C1", [{"value": 1, "unit_raw": "", "normalization_status": "candidate"}]),
        _claim("C2", [{"value": 2, "unit_raw": "", "normalization_status": "candidate"}]),
    ]
    findings = numeric_findings(claims, items) + duplicate_findings(
        [_requirement("SYS-GN-001"), _requirement("SYS-GN-001")]
    )
    forbidden_keys = {"gold", "gold_label", "is_gold", "gold_status", "manual_label", "annotator"}
    forbidden_values = {"gold", "confirmed", "complete"}

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                assert key not in forbidden_keys
                if isinstance(value, str):
                    assert value not in forbidden_values
                walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    for row in links + items + findings + quality_contracts():
        walk(row)
    walk(policy_statements())
    for item in items:
        assert item["completeness"] == "partial"


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_end_to_end_build_with_tmp_paths(tmp_path):
    graph_dir = tmp_path / "evidence_graph_v1"
    corpus_dir = tmp_path / "structured_corpus_v1"
    output_dir = tmp_path / "evidence_graph_v2"
    graph_dir.mkdir()
    corpus_dir.mkdir()
    _write_jsonl(
        graph_dir / "candidate_links.jsonl",
        [
            _link(
                "L1",
                "requirements:SYS-GN-001",
                "claims:C1",
                "same_identity",
                ["same_doc", "shared_identifier"],
                status="accepted",
            ),
            _link(
                "L2",
                "requirements:SYS-GN-001",
                "claims:C2",
                "same_identity",
                ["same_doc", "shared_identifier"],
                status="accepted",
            ),
            _link("L3", "requirements:SYS-GN-002", "claims:C3", "semantic_neighbor", ["same_doc"]),
        ],
    )
    _write_jsonl(
        graph_dir / "findings.jsonl",
        [
            {
                "finding_id": "FND-old",
                "finding_type": "duplicate_explicit_requirement_id",
                "status": "candidate",
                "severity": "warning",
                "target_refs": [],
                "evidence_refs": [],
            }
        ],
    )
    _write_jsonl(
        corpus_dir / "requirements.jsonl",
        [
            _requirement("SYS-GN-001"),
            _requirement("SYS-GN-001"),
            _requirement("SYS-GN-002"),
        ],
    )
    _write_jsonl(
        corpus_dir / "claims.jsonl",
        [
            _claim("C1", [{"value": 100, "unit_raw": "ms", "normalization_status": "candidate"}]),
            _claim("C2", [{"value": 200, "unit_raw": "ms", "normalization_status": "candidate"}]),
            _claim("C3", []),
        ],
    )

    summary = build(graph_dir, corpus_dir, output_dir)

    counts = summary["counts"]
    assert counts["links_v2"] == 3
    assert counts["links_upgraded_to_silver"] == 2
    assert counts["items_v2"] == 1
    assert counts["findings_v2"] == 2
    assert counts["findings_by_type"]["duplicate_explicit_requirement_id"] == 1
    assert counts["findings_by_type"]["candidate_numeric_conflict"] == 1
    assert counts["findings_by_status"] == {"candidate": 1, "insufficient": 1}
    assert counts["input_findings_v1"] == 1
    assert summary["policy"]["silver_is_weak_supervision_not_gold"] is True
    assert len(summary["source_sha256"]) == 4

    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["files"]) == {"links_v2", "items_v2", "findings_v2", "quality_contracts_v2"}
    for name, digest in manifest["files"].items():
        assert _sha256(output_dir / f"{name}.jsonl") == digest

    links = _read_jsonl(output_dir / "links_v2.jsonl")
    silver = [link for link in links if link["quality_tier"] == "silver"]
    assert len(silver) == 2
    assert all(link["label_basis"] == "explicit_identifier" for link in silver)

    items = _read_jsonl(output_dir / "items_v2.jsonl")
    assert items[0]["occurrence_ids"] == ["claims:C1", "claims:C2", "requirements:SYS-GN-001"]
    assert items[0]["quality_tier"] == "silver"

    findings = _read_jsonl(output_dir / "findings_v2.jsonl")
    by_type = {finding["finding_type"]: finding for finding in findings}
    assert by_type["duplicate_explicit_requirement_id"]["status"] == "candidate"
    assert by_type["candidate_numeric_conflict"]["status"] == "insufficient"

    contracts = _read_jsonl(output_dir / "quality_contracts_v2.jsonl")
    assert {contract["quality_type"] for contract in contracts} == {
        "duplicate_explicit_requirement_id",
        "candidate_numeric_conflict",
    }


def test_build_raises_on_missing_inputs(tmp_path):
    graph_dir = tmp_path / "empty_graph"
    corpus_dir = tmp_path / "empty_corpus"
    graph_dir.mkdir()
    corpus_dir.mkdir()
    try:
        build(graph_dir, corpus_dir, tmp_path / "out")
    except FileNotFoundError as exc:
        assert "candidate_links.jsonl" in str(exc)
    else:
        raise AssertionError("build must raise FileNotFoundError when inputs are missing")
