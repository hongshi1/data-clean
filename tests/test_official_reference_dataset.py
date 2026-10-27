"""Contract tests for the scene-1 official reference dataset."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data/gjb_438c/qa_frozen/scene1_official_reference_v1.jsonl"
META = BASE / "data/gjb_438c/qa_frozen/scene1_official_reference_v1_metadata.json"
SOURCE_QA = (BASE / "docs/doc11/场景1-软件需求规格辅助生成场景补发数据"
             / "高质量问答对（配套样例数据中：04数据统一访问服务软件需求规格说明）.json")


def _rows() -> list[dict]:
    return [json.loads(line) for line in OUT.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def test_official_reference_preserves_alpaca_fields_verbatim() -> None:
    source = json.loads(SOURCE_QA.read_text(encoding="utf-8"))
    rows = _rows()
    assert len(rows) == len(source) == 91
    for record, official in zip(rows, source):
        alpaca = record["official_alpaca"]
        assert alpaca["instruction"] == official["instruction"]
        assert alpaca["output"] == official["output"]
        assert alpaca["input"] == official.get("input", "")
        assert alpaca["system"] == official.get("system", "")


def test_official_reference_integrates_evidence_and_statements() -> None:
    rows = _rows()
    assert all(record["context_freeze_id"] for record in rows)
    assert sum(len(record["evidence"]) for record in rows) == 574
    assert all(record["linearized_statements"] for record in rows if record["evidence"])
    statement_ids = [statement["statement_id"]
                     for record in rows
                     for statement in record["linearized_statements"]]
    assert len(statement_ids) == len(set(statement_ids))
    for record in rows:
        evidence_ids = {item["evidence_id"] for item in record["evidence"]}
        for statement in record["linearized_statements"]:
            assert statement["evidence_id"] in evidence_ids


def test_official_reference_carries_silver_not_gold() -> None:
    rows = _rows()
    verdicts = {record["silver_label"]["final_verdict"] for record in rows}
    assert verdicts <= {"support", "refute", "not_in_evidence"}
    assert all(record["silver_label"]["is_gold"] is False for record in rows)
    assert all(record["silver_label"]["final_model"] == "glm-5.3" for record in rows)
    assert sum(1 for record in rows
               if record["silver_label"]["final_verdict"] == "refute") == 8


def test_metadata_records_official_package_and_lineage() -> None:
    meta = json.loads(META.read_text(encoding="utf-8"))
    assert meta["n_rows"] == 91
    assert meta["statement_total"] == 6758
    assert meta["silver_verdicts"] == {"support": 6, "refute": 8,
                                       "not_in_evidence": 77}
    package = meta["official_package"]
    assert package["files"], "official package file hashes must be recorded"
    assert all(entry["sha256"] for entry in package["files"])
    assert meta["input_artifacts"]["source_qa_sha256"]
    assert meta["input_artifacts"]["frozen_sha256"]
    assert meta["input_artifacts"]["labels_sha256"]
    assert meta["field_semantics"]["input/system"].startswith("0/91")
