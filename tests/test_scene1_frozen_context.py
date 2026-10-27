"""Regression tests for the deterministic scene 1 frozen QA asset."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.build_scene1_frozen_context import DEFAULT_OUT, build, item_text

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data/gjb_438c"


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_frozen_asset_has_91_qa_inputs_and_required_contract() -> None:
    rows = _rows(DEFAULT_OUT)
    assert len(rows) == 91
    assert [row["instance_id"] for row in rows] == [f"S1QA-{i:03d}" for i in range(1, 92)]
    for row in rows:
        assert set(row) == {"instance_id", "question", "answer", "context_freeze_id", "evidence"}
        assert row["context_freeze_id"]
        for evidence in row["evidence"]:
            assert {"evidence_id", "text", "source_type", "source_ref", "scope_id", "completeness", "completeness_proof"} <= evidence.keys()
            assert evidence["text"]
            assert evidence["source_ref"]["block_id"].startswith("block-")
            assert evidence["scope_id"]
            assert evidence["completeness"] in {"open", "unknown"}
            assert evidence["completeness"] != "closed"


def test_frozen_evidence_points_to_exact_source_blocks() -> None:
    rows = _rows(DEFAULT_OUT)
    audit = json.loads((DATA / "scene1_qa_audit.json").read_text(encoding="utf-8"))
    source = json.loads((BASE / audit["meta"]["source_srs"]).read_text(encoding="utf-8"))
    for row, original in zip(rows, audit["entries"], strict=True):
        expected = {f"block-{hit['idx']:06d}" for hit in original["evidence_hits"]}
        actual = {evidence["source_ref"]["block_id"] for evidence in row["evidence"]}
        assert actual <= expected
        for evidence in row["evidence"]:
            index = int(evidence["source_ref"]["block_id"].removeprefix("block-"))
            item = source[index]
            assert evidence["text"] == item_text(item)


def test_build_is_deterministic_and_does_not_modify_audit(tmp_path: Path) -> None:
    audit_path = DATA / "scene1_qa_audit.json"
    before = hashlib.sha256(audit_path.read_bytes()).hexdigest()
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first_meta = build(audit_path, first)
    second_meta = build(audit_path, second)
    assert first.read_bytes() == second.read_bytes()
    assert {key: value for key, value in first_meta.items() if key != "output"} == {
        key: value for key, value in second_meta.items() if key != "output"
    }
    assert hashlib.sha256(audit_path.read_bytes()).hexdigest() == before
