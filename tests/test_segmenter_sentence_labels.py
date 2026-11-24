"""P1-v4 sentence-mode label tests (narrative instances get A_regex claims)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.build_segmenter_field_labels import (  # noqa: E402
    build_mixed_labels,
    sentence_label_claims,
)

#: 纯叙事实例(v2训练语料风格): 无typed字段命中
_NARRATIVE_RECORD = {
    "instance_id": "TEST-NARR-01",
    "question": "系统的容错能力怎么样？",
    "answer": "系统具备完善的故障隔离机制，异常发生时能够自动切换到备用节点，保障业务连续性。",
    "source": "dev45",
    "claims": [{"text": "旧教师原子", "type": "semantic",
                "in_answer": False, "find_span": None}],
    "llm_status": "ok",
}

#: 含typed字段实例: 数值声明
_NUMERIC_RECORD = {
    "instance_id": "TEST-NUM-01",
    "question": "响应时间要求是什么？",
    "answer": "数据库查询响应时间不大于100ms。",
    "source": "dev45",
    "claims": [],
    "llm_status": "ok",
}


def test_sentence_mode_routes_all_to_a_regex_full() -> None:
    out = build_mixed_labels([dict(_NARRATIVE_RECORD)],
                             narrative_source="sentence")
    assert len(out) == 1
    rec = out[0]
    assert rec["label_source"] == "a_regex_full"
    assert rec["llm_status"] == "ok"
    # 叙事实例获得句级claim(A_regex语义claim, 非教师原子)
    assert rec["claims"], "narrative instance must get sentence claims"
    assert all(c["type"] == "semantic" for c in rec["claims"])
    # 字面契约
    for c in rec["claims"]:
        if c["in_answer"]:
            s, e = c["find_span"]
            assert rec["answer"][s:e] == c["text"]


def test_sentence_mode_keeps_typed_rehoming() -> None:
    rec = build_mixed_labels([dict(_NUMERIC_RECORD)],
                             narrative_source="sentence")[0]
    assert rec["label_source"] == "a_regex_full"
    kinds = {c["type"] for c in rec["claims"]}
    assert "numeric" in kinds, f"typed claims must survive: {kinds}"
    for c in rec["claims"]:
        if c["in_answer"] and c["type"] == "numeric":
            s, e = c["find_span"]
            assert rec["answer"][s:e] == c["text"]


def test_default_mode_unchanged_teacher_atom() -> None:
    out = build_mixed_labels([dict(_NARRATIVE_RECORD)])
    assert out[0]["label_source"] == "teacher_atom"
    assert out[0]["claims"][0]["text"] == "旧教师原子"


def test_sentence_label_claims_literal_contract() -> None:
    claims = sentence_label_claims(
        _NARRATIVE_RECORD["question"], _NARRATIVE_RECORD["answer"])
    assert claims
    for c in claims:
        if c["in_answer"]:
            s, e = c["find_span"]
            assert _NARRATIVE_RECORD["answer"][s:e] == c["text"]
