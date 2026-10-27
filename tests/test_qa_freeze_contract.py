"""Audit frozen-context contracts without rewriting the QA data assets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_answer_mutation_candidates import (
    build_candidates,
    request_from_dict,
    split_candidate_records,
)

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data/gjb_438c"


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_scene1_ninety_one_rows_are_legacy_audit_not_frozen_context() -> None:
    audit = _load("scene1_qa_audit.json")
    assert len(audit["entries"]) == audit["meta"]["total"] == 91
    assert audit["meta"]["source_qa"]
    assert audit["meta"]["source_srs"]
    assert all("evidence_hits" in row for row in audit["entries"])

    # These hits are block indices/captions, not source_ref + frozen evidence.
    assert not {"context_freeze_id", "source_sha256", "lineage"} & audit["meta"].keys()
    assert all(
        not {"source_ref", "scope_id", "completeness", "completeness_proof"}
        & hit.keys()
        for row in audit["entries"]
        for hit in row["evidence_hits"]
    )


def test_aee_and_recovery_assets_have_no_frozen_context_lineage() -> None:
    aee = _load("answer_evidence_evalset_v1.json")
    recovery = _load("aee_question_recovery.json")
    assert len(aee["entries"]) == recovery["meta"]["total"] == 1443
    assert [row["aee_id"] for row in recovery["entries"]] == [
        row["id"] for row in aee["entries"]
    ]
    assert all(row["answer_match"] for row in recovery["entries"])

    # anchor is a citation hint, but not the QAInput source_ref/scope contract.
    assert all("anchor" in row["evidence"][0] for row in aee["entries"])
    assert not {"context_freeze_id", "source_sha256", "lineage"} & aee["meta"].keys()
    assert not {"source_sha256", "lineage"} & recovery["meta"].keys()
    assert all("source_ref" not in row["evidence"][0] for row in aee["entries"])
    assert all("source_ref" not in row for row in recovery["entries"])


def test_frozen_input_requires_scope_completeness_and_source_ref() -> None:
    valid = {
        "instance_id": "qa-1",
        "question": "响应时间是多少？",
        "answer": "响应时间为200ms。",
        "context_freeze_id": "freeze-abc",
        "evidence": [{
            "evidence_id": "ev-1",
            "text": "响应时间为200ms。",
            "source_type": "text",
            "source_ref": {"doc_id": "doc-1", "section": "3.2.1"},
            "scope_id": "doc-1:3.2.1",
            "completeness": "open",
            "completeness_proof": "scope limited to retrieved paragraph",
            "extraction_method": "manual_freeze",
            "extraction_confidence": 1.0,
        }],
    }
    request = request_from_dict(valid)
    evidence = request.evidence[0]
    assert request.context_freeze_id
    assert evidence.source_ref.doc_id and evidence.scope_id
    assert evidence.completeness in ("open", "closed", "unknown")
    assert evidence.completeness != "closed" or evidence.completeness_proof.strip()

    for field in ("source_ref", "scope_id", "completeness"):
        broken = json.loads(json.dumps(valid))
        del broken["evidence"][0][field]
        if field == "completeness":
            # Builder silently substitutes unknown instead of enforcing presence.
            assert request_from_dict(broken).evidence[0].completeness == "unknown"
            continue
        try:
            request_from_dict(broken)
        except (KeyError, TypeError, ValueError):
            continue
        raise AssertionError(f"missing required frozen-context field accepted: {field}")


def test_candidate_private_split_and_hash_lineage() -> None:
    request = request_from_dict({
        "instance_id": "qa-1",
        "question": "响应时间是多少？",
        "answer": "响应时间为200ms。",
        "context_freeze_id": "freeze-abc",
        "evidence": [{
            "evidence_id": "ev-1", "text": "响应时间为200ms。", "source_type": "text",
            "source_ref": {"doc_id": "doc-1", "section": "3.2"},
            "scope_id": "doc-1:3.2", "completeness": "open",
            "completeness_proof": "bounded paragraph",
        }],
    })
    rows, _ = build_candidates([request])
    assert rows
    model_rows, private_rows = split_candidate_records(rows)
    assert len(model_rows) == len(private_rows)
    assert all("gold_private" not in row and "operator_id" not in row for row in model_rows)
    assert all("gold_private" in row and "mutation_private" in row for row in private_rows)

    for row in rows:
        private = row["mutation_private"]
        assert len(private["question_sha256"]) == 64
        assert len(private["context_sha256"]) == 64
        assert private["context_refs"]
        assert row["model_input"]["context_freeze_id"] == request.context_freeze_id

    model_rows, private_rows = split_candidate_records(rows)
    assert all(not {"input_sha256", "builder_version", "operator_registry_version", "git_sha"}
               & row.keys() for row in model_rows)
    assert all(row["input_sha256"] == "unknown" for row in private_rows)
    assert all(row["builder_version"] == "answer_mutation_candidates_v1"
               for row in private_rows)
    assert all(row["operator_registry_version"] == "answer_mutation_operators_v1"
               for row in private_rows)
    assert all(row["git_sha"] == "unknown" for row in private_rows)
    assert rows[0]["mutation_private"]["question_sha256"] == hashlib.sha256(
        request.question.encode("utf-8")
    ).hexdigest()
