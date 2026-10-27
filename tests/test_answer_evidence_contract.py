"""锁定一致性校验的任务边界: answer vs SRS证据，而非模态互比。"""
from __future__ import annotations

import json
from pathlib import Path


BASE = Path(__file__).resolve().parent.parent


def test_evalset_is_answer_against_single_evidence_source() -> None:
    data = json.loads(
        (BASE / "data/gjb_438c/answer_evidence_evalset_v1.json").read_text(
            encoding="utf-8"
        )
    )
    for entry in data["entries"]:
        assert len(entry["evidence"]) == 1
        assert "+" not in entry["modality_combo"]
        assert entry["answer"]["text"]
        assert entry["evidence"][0]["claims"]


def test_cross_modal_family_c_is_quarantined() -> None:
    data = json.loads(
        (BASE / "data/gjb_438c/answer_evidence_evalset_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert not any(
        entry["provenance"] == "family/gold_frozen"
        and entry["answer"]["origin"] == "figure"
        for entry in data["entries"]
    )
