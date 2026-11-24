"""Contract tests for the claim→typed bridge (99号方案P1, M119).

Covers:
- bridge_from_segments: per-segment typed extraction (numeric/quoted/enum/
  identifier) with answer-coordinate subject resolution and span offsets;
  semantic fallback for segments without typed fields; determinism snapshot.
- bridge_decompose_claims: no-segment fallback to the typed regex decomposer.
- qa_module decomposer="distilled_typed" registration (default unchanged).
- tools.claim_segmenter re-export shim (backward-compat surface).
- migrated pure label functions (char_labels_from_claims/decode_char_labels).
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency import claim_typed_bridge  # noqa: E402
from algorithms.consistency.answer_claims import (  # noqa: E402
    decompose_claims,
)
from algorithms.consistency.claim_typed_bridge import (  # noqa: E402
    bridge_decompose_claims,
    bridge_from_segments,
)
from algorithms.consistency.claim_segmenter_local import (  # noqa: E402
    char_labels_from_claims,
    decode_char_labels,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import (  # noqa: E402
    QAConsistencyModule,
    decompose_claims as qa_default_decompose,
)


ANSWER_MIXED = "响应时间 不大于50ms，接口标识为PZXQ-GN-SQLFW-SJXG。"
SEGMENTS_MIXED = [
    {"text": "响应时间 不大于50ms", "span": [0, 12]},
    {"text": "接口标识为PZXQ-GN-SQLFW-SJXG", "span": [13, 38]},
]


def _dump(claims: list) -> list[tuple[str, str, tuple[int, int] | None]]:
    return [(c.kind, c.text, tuple(c.span) if c.span else None)
            for c in claims]


# ── bridge_from_segments: typed extraction at claim granularity ────────────


def test_numeric_claim_from_segment_with_answer_level_attr() -> None:
    claims = bridge_from_segments("系统响应时间要求是多少？", ANSWER_MIXED,
                                  SEGMENTS_MIXED)
    numeric = [c for c in claims if c.kind == "numeric"]
    assert len(numeric) == 1
    claim = numeric[0]
    # attr在answer坐标系解析(与typed正则管线同口径), 构造文本带空格
    assert (claim.attr, claim.operator, claim.value, claim.unit) == (
        "响应时间", "不大于", "50", "ms")
    assert claim.text == "响应时间 不大于50ms"
    assert claim.span == (0, 12)
    assert ANSWER_MIXED[claim.span[0]:claim.span[1]] == claim.text


def test_identifier_claim_from_segment_with_answer_level_subject() -> None:
    claims = bridge_from_segments("系统响应时间要求是多少？", ANSWER_MIXED,
                                  SEGMENTS_MIXED)
    identifiers = [c for c in claims if c.kind == "identifier"]
    assert len(identifiers) == 1
    claim = identifiers[0]
    # span平移到answer坐标(基=segment span[0]); 主语取answer级24字符前缀
    assert claim.text == "PZXQ-GN-SQLFW-SJXG"
    assert claim.attr == "接口标识"
    assert claim.span == (18, 36)
    assert ANSWER_MIXED[claim.span[0]:claim.span[1]] == claim.text


def test_mixed_segment_emits_both_numeric_and_identifier() -> None:
    """一个segment同时含数值与标识符 → 两类typed claim都产出."""
    answer = "时延不大于50ms且接口为PZXQ-GN-SQLFW-SJXG"
    segment = [{"text": answer, "span": [0, len(answer)]}]
    claims = bridge_from_segments("接口时延是多少？", answer, segment)
    kinds = {c.kind for c in claims}
    assert {"numeric", "identifier"} <= kinds


def test_quoted_claim_negative_prefix_resolved_in_answer_coordinates() -> None:
    answer = "不支持「远程访问」功能"
    segment = [{"text": answer, "span": [0, len(answer)]}]
    claims = bridge_from_segments("功能是否支持远程访问？", answer, segment)
    assert len(claims) == 1
    claim = claims[0]
    assert claim.kind == "quoted"
    assert claim.text == "远程访问"
    assert claim.negative is True  # answer级12字符前缀命中"不支持"
    assert claim.span == (4, 8)
    assert answer[claim.span[0]:claim.span[1]] == claim.text


def test_enum_claim_extracted_inside_segment() -> None:
    answer = "包括数据插入、数据删除、数据查询"
    segment = [{"text": answer, "span": [0, len(answer)]}]
    claims = bridge_from_segments("该功能包括哪些操作？", answer, segment)
    assert len(claims) == 1
    claim = claims[0]
    assert claim.kind == "enum"
    assert claim.text == "数据插入、数据删除、数据查询"
    assert claim.span == (2, 16)


def test_bare_numeric_segment_binds_question_subject() -> None:
    """裸数值segment(切分器可能切出) → 问句主语补全(镜像decompose_claims)."""
    answer = "200ms"
    segment = [{"text": "200ms", "span": [0, 5]}]
    claims = bridge_from_segments("系统响应时间要求是多少？", answer, segment)
    assert len(claims) == 1
    claim = claims[0]
    assert claim.kind == "numeric"
    assert (claim.attr, claim.operator, claim.value, claim.unit) == (
        "响应时间", "为", "200", "ms")
    assert claim.text == "响应时间 为200ms"


def test_segment_without_typed_fields_falls_back_to_semantic() -> None:
    answer = "该功能提供对查询结果的数据缓存"
    segment = [{"text": answer, "span": [0, len(answer)]}]
    claims = bridge_from_segments("热点数据缓存功能有什么特点", answer, segment)
    assert len(claims) == 1
    claim = claims[0]
    assert claim.kind == "semantic"
    assert claim.text == answer
    assert claim.span == (0, len(answer))


def test_segment_without_span_recovers_via_find() -> None:
    """span缺失: answer.find恢复(与AnswerClaim.span回退约定同口径)."""
    claims = bridge_from_segments("q？", "任意叙事片段无区间",
                                  [{"text": "任意叙事片段无区间"}])
    assert len(claims) == 1
    assert claims[0].kind == "semantic"
    assert claims[0].span == (0, 9)


def test_segment_without_span_unfindable_keeps_text_only() -> None:
    """span缺失且find不可恢复: 保守只出text形式semantic(坐标未知不冒险)."""
    claims = bridge_from_segments("q？", "另一段答案文本",
                                  [{"text": "不在此答案中的片段"}])
    assert len(claims) == 1
    assert claims[0].kind == "semantic"
    assert claims[0].span is None


def test_bridge_from_segments_determinism_snapshot() -> None:
    """确定性快照: 固定answer+segments → 完整claim序列逐字段稳定."""
    claims = bridge_from_segments(
        "系统响应时间要求是多少？", ANSWER_MIXED, SEGMENTS_MIXED)
    assert _dump(claims) == [
        ("numeric", "响应时间 不大于50ms", (0, 12)),
        ("identifier", "PZXQ-GN-SQLFW-SJXG", (18, 36)),
    ]
    # 重复调用逐字段一致(纯函数, 无隐藏状态)
    again = bridge_from_segments(
        "系统响应时间要求是多少？", ANSWER_MIXED, SEGMENTS_MIXED)
    assert _dump(again) == _dump(claims)


def test_empty_segments_yield_no_claims() -> None:
    assert bridge_from_segments("q？", "answer", []) == []


# ── bridge_decompose_claims: fallback + monkeypatched segmenter ────────────


def test_bridge_decompose_falls_back_to_typed_regex_without_segments(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(claim_typed_bridge, "segment_claims",
                        lambda answer, model_path, boundary_gate: [])
    question = "接口的标识符是什么？"
    answer = "接口标识为PZXQ-GN-SQLFW-SJXG"
    claims = bridge_decompose_claims(question, answer)
    assert _dump(claims) == _dump(decompose_claims(question, answer))


def test_bridge_decompose_uses_segmenter_output(
        monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_segment(answer: str, model_path: str,
                     boundary_gate: float) -> list[dict]:
        assert model_path == claim_typed_bridge.BRIDGE_SEGMENTER_PATH
        assert boundary_gate == claim_typed_bridge.BRIDGE_BOUNDARY_GATE
        return [{"text": answer, "span": [0, len(answer)]}]

    monkeypatch.setattr(claim_typed_bridge, "segment_claims", fake_segment)
    claims = bridge_decompose_claims("q？", "标识符PZXQ-GN-SQLFW-SJXG")
    assert [c.kind for c in claims] == ["identifier"]


# ── qa_module decomposer registration ──────────────────────────────────────


def _request(answer: str, evidence_text: str) -> QAInput:
    return QAInput(
        instance_id="qa-bridge",
        question="接口的标识符是什么？",
        answer=answer,
        context_freeze_id="frozen-bridge-1",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text=evidence_text,
            source_type="text",
            source_ref=SourceRef(doc_id="doc01", section="3.2.1", page=3),
            scope_id="doc01:3.2.1",
            completeness="open",
        ),),
    )


def test_distilled_typed_decomposer_routes_typed_channel(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """桥接claim含标识符 → identifier通道接管(子claim级证据对齐=SAE)."""
    answer = "接口标识为PZXQ-GN-SQLFW-SJXG"
    monkeypatch.setattr(
        claim_typed_bridge, "segment_claims",
        lambda a, model_path, boundary_gate: [
            {"text": a, "span": [0, len(a)]}])
    module = QAConsistencyModule(decomposer="distilled_typed")
    result = module.verify(_request(answer, "接口标识为PZXQ-GN-SQLFW-SJXG。"))
    assert result.verdict == "support"
    assert result.claim_results[0].method == "identifier_exact_match"


def test_distilled_typed_decomposer_semantic_fallback(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """未命中typed字段的claim走verify_semantic既有路径(精确匹配)."""
    answer = "该功能提供对查询结果的数据缓存"
    monkeypatch.setattr(
        claim_typed_bridge, "segment_claims",
        lambda a, model_path, boundary_gate: [
            {"text": a, "span": [0, len(a)]}])
    module = QAConsistencyModule(decomposer="distilled_typed")
    result = module.verify(_request(answer, "该功能提供对查询结果的数据缓存"))
    assert result.verdict == "support"
    assert result.claim_results[0].method in ("exact_statement",
                                              "statement_exact")


def test_default_decomposer_unchanged() -> None:
    """默认"typed": 现有论文数字路径完全不变(硬规则)."""
    module = QAConsistencyModule()
    assert module._decomposer is qa_default_decompose
    module2 = QAConsistencyModule(decomposer="sentence")
    assert module2._decomposer is not qa_default_decompose


def test_invalid_decomposer_rejected() -> None:
    with pytest.raises(ValueError, match="distilled_typed"):
        QAConsistencyModule(decomposer="distilled")


# ── tools re-export shim + migrated pure functions ─────────────────────────


def test_tools_claim_segmenter_reexports_algorithms_core() -> None:
    import tools.claim_segmenter as shim

    assert shim.segment_claims is (
        claim_typed_bridge.segment_claims)
    assert shim.MODEL_PATH == "models/segmenter/claim_segmenter_v1"
    for name in ("char_labels_from_claims", "decode_char_labels",
                 "distilled_decompose_claims", "load_status",
                 "segment_claims", "LABELS", "LABEL_B"):
        assert hasattr(shim, name)


def test_char_label_roundtrip() -> None:
    answer = "AB是CD"
    spans = [(0, 2), (2, 4)]
    labels = char_labels_from_claims(answer, spans)
    assert labels == ["B", "I", "B", "I", "O"]
    assert decode_char_labels(labels) == spans
