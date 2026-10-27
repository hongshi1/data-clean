"""AEE question恢复审计快照: 重放映射+恢复率.

锁定: 总量/恢复状态分布/schema/占位符回填/与AEE文件ID对齐。
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REC = json.loads(
    (BASE / "data/gjb_438c/aee_question_recovery.json").read_text(encoding="utf-8"))
E = REC["entries"]
AEE = json.loads(
    (BASE / "data/gjb_438c/answer_evidence_evalset_v1.json")
    .read_text(encoding="utf-8"))["entries"]


def test_total_and_summary() -> None:
    assert len(E) == 1443
    assert REC["meta"]["summary"] == {
        "family_no_question": 574,
        "recovered": 868,
        "recovered_synthetic_question": 1,
    }


def test_schema() -> None:
    for e in E:
        assert e["recovery_status"] in ("recovered", "recovered_synthetic_question",
                                        "family_no_question")
        assert e["answer_match"] is True
        if e["recovery_status"] == "family_no_question":
            assert e["question"] is None
            assert e["question_reconstructed"] is None
        else:
            assert e["question"]
            assert e["question_style"] in ("alpaca_instruction",
                                           "hypothesis_template")


def test_aee_ids_align_in_order() -> None:
    assert [e["aee_id"] for e in E] == [a["id"] for a in AEE]


def test_placeholders_filled_in_reconstruction() -> None:
    """A1/C1族question_reconstructed不得残留{table}/{image}占位符."""
    for e in E:
        qr = e["question_reconstructed"]
        if qr:
            assert "{table}" not in qr and "{image}" not in qr, e["aee_id"]


def test_provenance_consistent_with_aee() -> None:
    for e, a in zip(E, AEE, strict=True):
        assert e["provenance"] == a["provenance"]


def test_c1_single_synthetic_entry() -> None:
    c1 = [e for e in E if e["recovery_status"] == "recovered_synthetic_question"]
    assert len(c1) == 1
    assert c1[0]["provenance"] == "qa_alpaca/C1"
    assert c1[0]["question_style"] == "hypothesis_template"
    assert "假设" in c1[0]["question"]


def test_family_count_matches_aee() -> None:
    fam_rec = sum(1 for e in E if e["recovery_status"] == "family_no_question")
    fam_aee = sum(1 for a in AEE if a["provenance"].startswith("family/"))
    assert fam_rec == fam_aee == 574
