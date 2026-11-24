"""P1-v2 Step 1 tests: 字段claim标签构造确定性快照 + 混合路由 + 字面契约.

covers tools/build_segmenter_field_labels.py (103号规格Step 1):
- field_label_claims: 各kind确定性claim集(主语归位/重复ID逐次归属/
  enum原文分隔符span/问句门控裸值不归位);
- 路由逻辑: typed命中→field_distill(A_regex标签), 纯叙事→teacher_atom
  (教师claims原样保留+label_source标记);
- 字面契约: 全部in_answer claim满足answer[find_span]==text;
- trainer消费契约: char_labels_from_claims可构造且decode恢复span;
- 输出协议: jsonl+trainer JSON落盘, 已存在不覆盖写(SystemExit);
- 对齐防御: match序列与decompose_claims漂移→显式ValueError(不静默).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from tools import build_segmenter_field_labels as bsf  # noqa: E402
from tools.build_segmenter_field_labels import (  # noqa: E402
    _locate_enum_items,
    build_mixed_labels,
    convert_instance,
    field_label_claims,
    identifier_coverage,
    rehome_start,
    write_outputs,
)
from algorithms.consistency.claim_segmenter_local import (  # noqa: E402
    char_labels_from_claims,
    decode_char_labels,
)

QUESTION_NUMERIC = "接口的时延和内存要求是什么？"
ANSWER_NUMERIC = "接口时延不大于100ms，内存占用不超过512MB。"
ANSWER_ID_DUP = "接口AB-1与接口AB-1均可用。"
ANSWER_ID_CONNECTOR = "系统标识符为PZXQ-GN-SQLFW-SJXG。"
QUESTION_BARE = "时延是多少？"
ANSWER_BARE = "100ms。"
ANSWER_ENUM_COMMA = "功能包括数据插入，数据删除，数据查询。"
ANSWER_QUOTED = "不支持「远程访问」功能。"
ANSWER_NARRATIVE = "该系统采用模块化设计。"

FIELD_RECORD_KEYS = {"instance_id", "question", "answer", "source",
                     "label_source", "claims", "llm_status", "llm_model",
                     "llm_calls"}


def _claims_snapshot(question: str, answer: str) -> list[dict]:
    return [{k: v for k, v in c.items() if k != "fused"}
            for c in field_label_claims(question, answer)]


# ── 确定性快照: 固定输入answer → 确定性claim集 ──────────────────────────────


def test_numeric_claims_snapshot_with_subject_rehoming() -> None:
    """数值claim: match区间+紧邻主语归位, 文本=answer逐字."""
    claims = _claims_snapshot(QUESTION_NUMERIC, ANSWER_NUMERIC)
    assert claims == [
        {"text": "接口时延不大于100ms", "type": "numeric", "in_answer": True,
         "find_span": [0, 12], "attr": "接口时延", "operator": "不大于",
         "value": "100", "unit": "ms", "field_span": [4, 12],
         "subject_rehomed": True},
        {"text": "内存占用不超过512MB", "type": "numeric", "in_answer": True,
         "find_span": [13, 25], "attr": "内存占用", "operator": "不超过",
         "value": "512", "unit": "MB", "field_span": [17, 25],
         "subject_rehomed": True},
    ]


def test_identifier_duplicate_string_per_occurrence_attribution() -> None:
    """重复ID: decompose的find()折叠到首现位置, 标签按finditer逐次归属.

    两处AB-1都被claim span覆盖(字段覆盖的字面修复).
    """
    claims = _claims_snapshot("哪些接口可用？", ANSWER_ID_DUP)
    assert claims == [
        {"text": "接口AB-1", "type": "identifier", "in_answer": True,
         "find_span": [0, 6], "attr": "接口", "field_span": [2, 6],
         "subject_rehomed": True},
        {"text": "与接口AB-1", "type": "identifier", "in_answer": True,
         "find_span": [6, 13], "attr": "与接口", "field_span": [9, 13],
         "subject_rehomed": True},
    ]
    # 两处ID出现均在claim span内(覆盖修复的直接证据)
    id_spans = [(m.start(), m.end())
                for m in re.finditer(r"[A-Z]{2,8}(?:-[A-Z0-9]{1,12})+",
                                     ANSWER_ID_DUP)]
    assert id_spans == [(2, 6), (9, 13)]
    label_spans = [tuple(c["find_span"]) for c in claims]
    assert all(any(ls <= s and e <= le for ls, le in label_spans)
               for s, e in id_spans)


def test_identifier_rehome_via_connector_word() -> None:
    """主语与ID之间的连接词'为'允许归位(命题单元=主语+系词+字段)."""
    claims = _claims_snapshot("系统标识符是什么？", ANSWER_ID_CONNECTOR)
    assert claims == [
        {"text": "系统标识符为PZXQ-GN-SQLFW-SJXG", "type": "identifier",
         "in_answer": True, "find_span": [0, 24], "attr": "系统标识符",
         "field_span": [6, 24], "subject_rehomed": True},
    ]


def test_bare_numeric_no_rehome_when_subject_not_in_answer() -> None:
    """问句门控裸值: 主语来自question(answer内不存在)→不归位, span=字段."""
    claims = _claims_snapshot(QUESTION_BARE, ANSWER_BARE)
    assert claims == [
        {"text": "100ms", "type": "numeric", "in_answer": True,
         "find_span": [0, 5], "attr": "时延", "operator": "为",
         "value": "100", "unit": "ms", "field_span": [0, 5],
         "subject_rehomed": False},
    ]


def test_enum_span_verbatim_with_original_separators() -> None:
    """enum claim: 构造文本用'、'而answer用'，'→span=原文区间(逐字)."""
    claims = _claims_snapshot("该功能包括哪些操作？", ANSWER_ENUM_COMMA)
    assert claims == [
        {"text": "数据插入，数据删除，数据查询", "type": "enum",
         "in_answer": True, "find_span": [4, 18],
         "items": ["数据插入", "数据删除", "数据查询"],
         "field_span": [4, 18], "subject_rehomed": False},
    ]


def test_quoted_claim_verbatim_span() -> None:
    claims = _claims_snapshot("是否支持远程访问？", ANSWER_QUOTED)
    assert claims == [
        {"text": "远程访问", "type": "quoted", "in_answer": True,
         "find_span": [4, 8], "negative": True, "field_span": [4, 8],
         "subject_rehomed": False},
    ]


def test_narrative_answer_has_no_field_claims() -> None:
    """纯叙事answer: 无typed命中→field_label_claims返回空(路由teacher)."""
    assert field_label_claims("系统采用什么设计？",
                              ANSWER_NARRATIVE) == []


def test_field_label_claims_deterministic() -> None:
    first = field_label_claims(QUESTION_NUMERIC, ANSWER_NUMERIC)
    second = field_label_claims(QUESTION_NUMERIC, ANSWER_NUMERIC)
    assert first == second


# ── rehome_start边界 ──────────────────────────────────────────────────────────


def test_rehome_start_edges() -> None:
    answer = "内存占用不大于100ms"
    # 主语"内存"与match间隔"占用"(非连接词)→不归位
    assert rehome_start(answer, 4, "内存") == 4
    # 空主语→不归位
    assert rehome_start("abc", 3, "") == 3
    # 句读分隔符"，"不延伸(打断命题连续性)
    assert rehome_start("标识符，PZXQ", 4, "标识符") == 4
    # 严格邻接
    assert rehome_start("时延不大于", 2, "时延") == 0


# ── 混合分层路由逻辑 ─────────────────────────────────────────────────────────


def _teacher_record() -> dict:
    return {"instance_id": "T-NAR-1", "question": "系统采用什么设计？",
            "answer": ANSWER_NARRATIVE, "source": "synthetic",
            "claims": [{"text": "该系统采用模块化设计", "type": "semantic",
                        "in_answer": True, "find_span": [0, 10],
                        "teacher_span": [0, 10],
                        "teacher_span_exact": True, "fused": True}],
            "llm_status": "ok", "llm_model": "glm-5.3",
            "llm_cache_hit": True, "llm_calls": 1}


def test_route_typed_instance_to_field_distill() -> None:
    rec = {"instance_id": "T-FLD-1", "question": QUESTION_NUMERIC,
           "answer": ANSWER_NUMERIC, "source": "synthetic",
           "claims": [{"text": "叙事原子", "type": "semantic",
                       "in_answer": True, "find_span": [0, 4],
                       "teacher_span": [0, 4],
                       "teacher_span_exact": True, "fused": False}],
           "llm_status": "ok", "llm_model": "glm-5.3"}
    out = convert_instance(rec)
    assert out["label_source"] == "field_distill"
    assert FIELD_RECORD_KEYS <= set(out)
    assert out["llm_status"] == "ok"
    assert out["source"] == "synthetic"  # 语料来源字段保留(v2口径)
    assert all(c["type"] in bsf.TYPED_KINDS for c in out["claims"])
    assert out["llm_model"] == "deterministic:answer_claims.decompose_claims"


def test_route_narrative_instance_keeps_teacher_claims_verbatim() -> None:
    rec = _teacher_record()
    out = convert_instance(rec)
    assert out["label_source"] == "teacher_atom"
    assert out["claims"] == rec["claims"]  # 教师原子标签原样保留
    assert out["llm_model"] == rec["llm_model"]
    assert "route_note" not in out


def test_build_mixed_labels_routes_each_instance() -> None:
    records = [
        {"instance_id": "T-FLD-1", "question": QUESTION_NUMERIC,
         "answer": ANSWER_NUMERIC, "source": "synthetic",
         "claims": [], "llm_status": "ok"},
        _teacher_record(),
    ]
    out = build_mixed_labels(records)
    assert [r["label_source"] for r in out] == ["field_distill",
                                                "teacher_atom"]
    assert [r["instance_id"] for r in out] == ["T-FLD-1", "T-NAR-1"]


# ── 字面契约(trainer/下游消费的字面保证) ────────────────────────────────────


@pytest.mark.parametrize("question,answer", [
    (QUESTION_NUMERIC, ANSWER_NUMERIC),
    ("哪些接口可用？", ANSWER_ID_DUP),
    ("系统标识符是什么？", ANSWER_ID_CONNECTOR),
    (QUESTION_BARE, ANSWER_BARE),
    ("该功能包括哪些操作？", ANSWER_ENUM_COMMA),
    ("是否支持远程访问？", ANSWER_QUOTED),
    ("混合字段: 接口时延不大于50ms，标识为PZXQ-GN-SQLFW。",
     "接口时延不大于50ms，标识为PZXQ-GN-SQLFW。"),
])
def test_literal_contract_answer_span_equals_text(question: str,
                                                  answer: str) -> None:
    """全部claim: span在answer坐标内且answer[span]==text(逐字)."""
    for claim in field_label_claims(question, answer):
        assert claim["in_answer"] is True
        start, end = claim["find_span"]
        assert 0 <= start < end <= len(answer)
        assert answer[start:end] == claim["text"]


def test_char_label_roundtrip_trainer_contract() -> None:
    """claim span→B/I/O字符标签→解码span可恢复(trainer特征构造契约)."""
    claims = field_label_claims(QUESTION_NUMERIC, ANSWER_NUMERIC)
    spans = [tuple(c["find_span"]) for c in claims]
    labels = char_labels_from_claims(ANSWER_NUMERIC, spans)
    assert decode_char_labels(labels) == spans


# ── 辅助函数单测 ──────────────────────────────────────────────────────────────


def test_locate_enum_items_failure_returns_none() -> None:
    assert _locate_enum_items("无关文本", ["不存在项", "另一项"]) is None


def test_identifier_coverage_metric() -> None:
    answer = "接口AB-1与接口AB-1均可用。"
    assert identifier_coverage(answer, [(0, 6)]) == (1, 2)
    assert identifier_coverage(answer, [(0, 6), (6, 13)]) == (2, 2)
    assert identifier_coverage(answer, []) == (0, 2)


# ── 对齐防御: 漂移显式抛错(不静默错位) ──────────────────────────────────────


def test_alignment_drift_raises_value_error(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """镜像match序列与decompose_claims漂移→ValueError(防御性契约)."""
    monkeypatch.setattr(
        bsf, "_NUMERIC_PREFIX",
        re.compile(r"(?P<op>不大于)(?P<value>\d+)(?P<unit>ms)?"))
    with pytest.raises(ValueError, match="numeric对齐漂移"):
        field_label_claims(QUESTION_NUMERIC, ANSWER_NUMERIC)


# ── 输出协议: jsonl+trainer JSON, 不覆盖写 ─────────────────────────────────


def test_write_outputs_and_no_overwrite(tmp_path: Path) -> None:
    records = build_mixed_labels([
        {"instance_id": "T-FLD-1", "question": QUESTION_NUMERIC,
         "answer": ANSWER_NUMERIC, "source": "synthetic",
         "claims": [], "llm_status": "ok"},
        _teacher_record(),
    ])
    meta = {"n_field_distill": 1, "n_teacher_atom": 1}
    out_jsonl = tmp_path / "labels.jsonl"
    out_json = tmp_path / "train.json"
    write_outputs(records, meta, out_jsonl, out_json, force=False)

    lines = out_jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert [json.loads(line)["instance_id"] for line in lines] == [
        "T-FLD-1", "T-NAR-1"]

    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert set(doc) == {"meta", "answers"}
    assert doc["answers"] == records
    assert doc["meta"]["n_field_distill"] == 1
    # trainer消费契约(load_train_answers过滤字段)
    assert all(rec.get("llm_status") == "ok" for rec in doc["answers"])
    # eval_claim_recognition.load_gold按source过滤兼容(语料来源字段保留)
    assert [rec for rec in doc["answers"]
            if rec.get("source") == "synthetic"] == records

    # 不覆盖写: 已存在→SystemExit; --force→覆盖
    with pytest.raises(SystemExit, match="不覆盖写"):
        write_outputs(records, meta, out_jsonl, out_json, force=False)
    write_outputs(records, meta, out_jsonl, out_json, force=True)


# ── 统计与自检 ────────────────────────────────────────────────────────────────


def test_compute_stats_on_synthetic_corpus() -> None:
    from tools.build_segmenter_field_labels import compute_stats
    train_records = [
        {"instance_id": "T-FLD-1", "question": QUESTION_NUMERIC,
         "answer": ANSWER_NUMERIC, "source": "synthetic",
         "claims": [{"text": "接口时延不大于100ms", "type": "semantic",
                     "in_answer": True, "find_span": [0, 12]}],
         "llm_status": "ok"},
    ]
    label_records = build_mixed_labels(train_records)
    stats = compute_stats(train_records, label_records)
    assert stats["n_answers_total"] == 1
    assert stats["n_field_distill"] == 1
    assert stats["n_teacher_atom"] == 0
    assert stats["claims"]["field_distill"]["n_claims"] == 2
    assert stats["claims"]["field_distill"]["kinds"] == {"numeric": 2}
    assert stats["literal_contract"]["n_violations"] == 0
    # 数值only实例: 无ID→coverage块total=0(rate=None)
    cov = stats["identifier_span_coverage"]["field_distill_labels"]
    assert cov["total"] == 0 and cov["rate"] is None


def test_compute_stats_id_coverage_blocks() -> None:
    from tools.build_segmenter_field_labels import compute_stats
    answer = ANSWER_ID_CONNECTOR
    train_records = [
        {"instance_id": "T-ID-1", "question": "系统标识符是什么？",
         "answer": answer, "source": "synthetic",
         # 教师侧: 叙事claim不含ID span(字段层缺口的最小复现)
         "claims": [{"text": "系统标识符", "type": "semantic",
                     "in_answer": True, "find_span": [0, 5]}],
         "llm_status": "ok"},
    ]
    label_records = build_mixed_labels(train_records)
    stats = compute_stats(train_records, label_records)
    cov = stats["identifier_span_coverage"]
    assert cov["field_distill_labels"]["total"] == 1
    assert cov["field_distill_labels"]["covered"] == 1
    assert cov["field_distill_labels"]["rate"] == 1.0
    assert cov["teacher_labels_same_instances"]["covered"] == 0
    assert cov["teacher_labels_same_instances"]["rate"] == 0.0


def test_self_check_samples_literal_audit() -> None:
    from tools.build_segmenter_field_labels import _self_check_samples
    records = build_mixed_labels([
        {"instance_id": "T-FLD-1", "question": QUESTION_NUMERIC,
         "answer": ANSWER_NUMERIC, "source": "synthetic",
         "claims": [], "llm_status": "ok"},
        _teacher_record(),
    ])
    samples = _self_check_samples(records, n=5)
    assert len(samples) == 1
    sample = samples[0]
    assert sample["instance_id"] == "T-FLD-1"
    assert sample["all_verbatim"] is True
    assert len(sample["claims"]) == 2
    for audit in sample["claims"]:
        assert audit["verbatim"] is True
        start, end = audit["find_span"]
        assert sample["answer"][start:end] == audit["text"]
