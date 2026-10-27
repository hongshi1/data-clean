"""Audit snapshot: old pair mutations are not silently treated as QA answer ops."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
AUDIT = json.loads(
    (BASE / "data/gjb_438c/legacy_answer_mutation_audit.json")
    .read_text(encoding="utf-8"))


def test_audit_rows_and_migration_statuses() -> None:
    rows = AUDIT["operators"]
    assert len(rows) == 17
    assert all(r["reason"] and r["old_input_contract"] for r in rows)
    assert sum(r["status"] == "deterministic_prototype" for r in rows) == 3
    assert sum(r["status"] == "manual_review_candidate" for r in rows) == 1
    assert all(r["status"].startswith("quarantined")
               for r in rows if r["source"] != "answer_mutations")


def test_pair_mutation_not_misclassified_as_answer_mutation() -> None:
    rows = AUDIT["operators"]
    for row in rows:
        if row["source"] in ("qa_mutation_ops", "mmqa.MutationEngine40",
                             "mutation_v2", "gen_injected_qa"):
            assert row["status"].startswith("quarantined")
