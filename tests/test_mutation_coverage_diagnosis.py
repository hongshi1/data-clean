"""Read-only coverage snapshot for the frozen Scene1 answer asset."""
from __future__ import annotations

import json
import re
from pathlib import Path

from algorithms.consistency.qa_router import route_question
from tools.build_answer_mutation_candidates import build_candidates, request_from_dict


BASE = Path(__file__).resolve().parents[1]
INPUT = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"


def _rows() -> list[dict]:
    return [
        json.loads(line)
        for line in INPUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_scene1_builder_has_proof_backed_term07_candidates() -> None:
    requests = [request_from_dict(row) for row in _rows()]
    candidates, counts = build_candidates(requests)

    assert len(requests) == 91
    assert sum(len(request.evidence) for request in requests) == 574
    # TERM-07 interface-identifier conflicts are the first proof-backed
    # candidates generated on the real frozen asset; every other family
    # still safely rejects open-scope evidence.
    assert len(candidates) == 3
    assert {row["operator_id"] for row in candidates} == {
        "ANSWER-TERM-07-INTERFACE-CONFLICT-V1"}
    assert all(row["gold_private"]["candidate"] == "refute" for row in candidates)
    assert len({row["model_input"]["instance_id"] for row in candidates}) == 3
    assert counts["term08_not_applicable"] == 574
    assert counts["logic04_not_applicable"] == 574
    assert counts["no_safe_numeric_operator"] == 574
    assert counts["term07_not_applicable"] == 570
    assert not any(key.startswith("ANSWER-STRUCT-") for key in counts)


def test_scene1_morphology_and_router_snapshot() -> None:
    rows = _rows()
    assert sum(any(char.isdigit() for char in row["answer"]) for row in rows) == 70
    units = ("ms", chr(0x6beb) + chr(0x79d2), chr(0x5206) + chr(0x949f), chr(0x79d2),
             "GB", "MB", "KB", chr(0x5b57) + chr(0x8282))
    assert sum(
        any(unit in row["answer"] for unit in units)
        for row in rows
    ) == 6
    equality_tokens = (chr(0x4e3a), chr(0x7b49) + chr(0x4e8e))
    assert sum(
        any(token in row["answer"] for token in equality_tokens)
        and any(char.isdigit() for char in row["answer"])
        for row in rows
    ) == 22
    assert sum(
        (chr(0x300c) in row["answer"] and chr(0x300d) in row["answer"])
        or (chr(0x201c) in row["answer"] and chr(0x201d) in row["answer"])
        for row in rows
    ) == 13
    assert sum(
        any(token in row["answer"] for token in (chr(0x5411), chr(0x53d1) + chr(0x9001) + chr(0x81f3), chr(0x4f20) + chr(0x8f93) + chr(0x81f3)))
        for row in rows
    ) == 11
    assert sum(bool(re.search(r"[A-Z][A-Z0-9-]{1,15}", row["answer"])) for row in rows) == 74
    assert sum(not route_question(row["question"]) for row in rows) == 48
