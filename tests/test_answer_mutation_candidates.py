"""Candidate builder contract: proof/private metadata is separated."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402
from tools.build_answer_mutation_candidates import (  # noqa: E402
    BUILDER_VERSION,
    OPERATOR_REGISTRY_VERSION,
    build_candidates,
    main,
    sha256_file,
    split_candidate_records,
)


def test_candidate_builder_keeps_question_context_immutable() -> None:
    request = QAInput(
        instance_id="candidate-1",
        question="系统响应时间是多少？",
        answer="响应时间为200ms。",
        context_freeze_id="freeze-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="响应时间为200ms。", source_type="text",
            source_ref=SourceRef(doc_id="d1", section="3.2.1"),
            scope_id="d1:3.2.1"),),
    )
    rows, counts = build_candidates([request])
    assert {row["operator_id"] for row in rows} >= {
        "ANSWER-NUM-IDENTITY-V1", "ANSWER-NUM-EQ-CONFLICT-V1"
    }
    for row in rows:
        assert row["model_input"]["question"] == request.question
        assert row["model_input"]["context_freeze_id"] == request.context_freeze_id
        assert row["mutation_private"]["context_refs"]
        assert "gold_candidate" not in row["model_input"]
    assert counts["ANSWER-NUM-IDENTITY-V1"] == 1

    model_rows, private_rows = split_candidate_records(rows)
    assert len(model_rows) == len(private_rows) == len(rows)
    assert all(set(row) == {
        "candidate_id", "instance_id", "question", "answer", "context_freeze_id",
        "retrieved_context",
    } for row in model_rows)
    assert all("gold_private" not in row and "operator_id" not in row
               and "check_item" not in row for row in model_rows)
    assert [row["candidate_id"] for row in model_rows] == [
        row["candidate_id"] for row in private_rows]


def test_candidate_builder_emits_proof_backed_new_operator_candidates() -> None:
    requests = [
        QAInput(
            instance_id="term08", question="HTTP的全称是什么？", answer="「HTTP」是协议。",
            context_freeze_id="freeze", evidence=(RetrievedEvidence(
                evidence_id="et", text="HTTP（超文本传输协议）用于传输。", source_type="text",
                source_ref=SourceRef(doc_id="d", section="3.1"), scope_id="d:3.1"),)),
        QAInput(
            instance_id="logic04", question="A向哪里发送数据？", answer="A向B发送数据。",
            context_freeze_id="freeze", evidence=(RetrievedEvidence(
                evidence_id="el", text="A向B发送数据。", source_type="text",
                source_ref=SourceRef(doc_id="d", section="3.2"), scope_id="d:3.2"),)),
    ]
    rows, _counts = build_candidates(requests)
    new_rows = [row for row in rows if row["operator_id"] in {
        "ANSWER-TERM-08-EXPANSION-V1", "ANSWER-LOGIC-04-REVERSED-FLOW-V1"}]
    assert {row["operator_id"] for row in new_rows} == {
        "ANSWER-TERM-08-EXPANSION-V1", "ANSWER-LOGIC-04-REVERSED-FLOW-V1"}
    assert all(row["gold_private"]["candidate"] in {"support", "refute"}
                and row["gold_private"]["proof"]
                and not row["gold_private"]["requires_manual_review"] for row in new_rows)


def _structural_request(*, completeness: str, answer: str) -> QAInput:
    return QAInput(
        instance_id="structural-fixture",
        question="节点清单有哪些？请列出节点。哪些节点？",
        answer=answer,
        context_freeze_id="freeze-structural",
        evidence=(RetrievedEvidence(
            evidence_id="closed-list",
            text="节点清单为：甲、乙、丙。",
            source_type="text",
            source_ref=SourceRef(doc_id="d-struct", section="3.4"),
            scope_id="d-struct:3.4",
            completeness=completeness,
            completeness_proof="本条明确列出全部节点。" if completeness == "closed" else "",
        ),),
    )


def test_structural_builder_add_candidate_is_support_and_open_scope_is_rejected() -> None:
    request = _structural_request(completeness="closed", answer="节点清单为：甲、乙。")
    rows, counts = build_candidates([request])
    structural = [row for row in rows if row["operator_id"].startswith("ANSWER-STRUCT-")]
    assert len(structural) == 1
    assert structural[0]["operator_id"] == "ANSWER-STRUCT-CLOSED-LIST-ADD-SUPPORT-V2"
    assert structural[0]["gold_private"]["candidate"] == "support"
    assert structural[0]["model_input"]["answer"] == "节点清单为：甲、乙、丙。"
    assert counts["ANSWER-STRUCT-CLOSED-LIST-ADD-SUPPORT-V2"] == 1

    open_rows, open_counts = build_candidates([
        _structural_request(completeness="open", answer="节点清单为：甲、乙。")
    ])
    assert not any(row["operator_id"].startswith("ANSWER-STRUCT-") for row in open_rows)
    assert open_counts["struct_list_add_not_applicable"] == 1


def test_structural_builder_remove_candidate_is_refute() -> None:
    rows, _counts = build_candidates([_structural_request(
        completeness="closed", answer="节点清单为：甲、乙、丙。")])
    structural = [row for row in rows if row["operator_id"].startswith("ANSWER-STRUCT-")]
    assert len(structural) == 3
    assert {row["operator_id"] for row in structural} == {
        "ANSWER-STRUCT-CLOSED-LIST-REMOVE-V1"
    }
    assert {row["gold_private"]["candidate"] for row in structural} == {"refute"}


def test_lineage_metadata_is_private_and_reproducible() -> None:
    request = QAInput(
        instance_id="lineage-1", question="系统响应时间是多少？", answer="响应时间为200ms。",
        context_freeze_id="freeze", evidence=(RetrievedEvidence(
            evidence_id="e1", text="响应时间为200ms。", source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.2"), scope_id="d:3.2"),),
    )
    rows, _ = build_candidates([request])
    model_rows, private_rows = split_candidate_records(
        rows,
        input_sha256="a" * 64,
        builder_version=BUILDER_VERSION,
        operator_registry_version=OPERATOR_REGISTRY_VERSION,
        git_sha="b" * 40,
    )

    assert all(row["input_sha256"] == "a" * 64 for row in private_rows)
    assert all(row["builder_version"] == BUILDER_VERSION for row in private_rows)
    assert all(row["operator_registry_version"] == OPERATOR_REGISTRY_VERSION
               for row in private_rows)
    assert all(row["git_sha"] == "b" * 40 for row in private_rows)
    assert all(not {"input_sha256", "builder_version", "operator_registry_version", "git_sha"}
               & row.keys() for row in model_rows)


def test_cli_records_input_hash_and_identity_only_in_lineage(tmp_path, monkeypatch) -> None:
    input_path = tmp_path / "input.jsonl"
    model_path = tmp_path / "model.jsonl"
    lineage_path = tmp_path / "lineage.jsonl"
    input_path.write_text(json.dumps({
        "instance_id": "cli-1",
        "question": "系统响应时间是多少？",
        "answer": "响应时间为200ms。",
        "context_freeze_id": "freeze",
        "evidence": [{
            "evidence_id": "e1", "text": "响应时间为200ms。", "source_type": "text",
            "source_ref": {"doc_id": "d", "section": "3.2"}, "scope_id": "d:3.2",
        }],
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "build_answer_mutation_candidates",
        "--input", str(input_path), "--model-output", str(model_path),
        "--lineage-output", str(lineage_path), "--git-sha", "test-git-sha",
    ])

    main()

    model_rows = [json.loads(line) for line in model_path.read_text(encoding="utf-8").splitlines()]
    private_rows = [json.loads(line) for line in lineage_path.read_text(encoding="utf-8").splitlines()]
    assert model_rows and private_rows
    expected_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    assert all(row["input_sha256"] == expected_hash for row in private_rows)
    assert all(row["builder_version"] == BUILDER_VERSION for row in private_rows)
    assert all(row["operator_registry_version"] == OPERATOR_REGISTRY_VERSION
               for row in private_rows)
    assert all(row["git_sha"] == "test-git-sha" for row in private_rows)
    assert all(not {"input_sha256", "builder_version", "operator_registry_version", "git_sha"}
               & row.keys() for row in model_rows)
    assert sha256_file(input_path) == expected_hash
