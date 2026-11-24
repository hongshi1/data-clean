"""tests for tools/e5_explanation_gate.py (机械检查/评分解析/权重表/装配)."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE), str(BASE / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from e5_explanation_gate import (  # noqa: E402
    LOW_QUALITY_WEIGHT,
    VERDICT_BASE_WEIGHTS,
    build_gated_rows,
    build_gate_prompt,
    build_report,
    gate_entry,
    load_union,
    mechanical_check,
    parse_scores,
    row_weight,
)

_ANSWER = ("布局控制功能仅在桌面、手持设备上使用，不支持平板设备。"
           "综上，用户在桌面、手持终端上均可以使用该功能。")


def _issue(quote: str, span: list[int] | None, ref: str = "ev-1",
           rule: str = "TERM-03") -> dict:
    return {"quote": quote, "span": span, "rule_id": rule,
            "evidence_ref": ref, "explanation": "证据含平板，answer否认。",
            "span_verified": True}


def _entry(issues: list[dict], verdict: str = "refute") -> dict:
    return {"corpus": "test", "instance_id": "T-001",
            "question": "布局控制功能支持在哪些设备上使用？",
            "answer": _ANSWER,
            "evidence": ["<table><tr><td>平板、桌面、手持</td></tr></table>"],
            "verdict": verdict, "issues": issues}


def _fake_teacher(payload: dict, hits: bool = True):
    def fn(prompt: str, system: str, **_kw) -> tuple[dict, str, bool]:
        return payload, "glm-5.3-test", hits
    return fn


# ── 机械检查 ─────────────────────────────────────────────────

def test_mechanical_check_pass():
    issue = _issue("不支持平板设备", [19, 26])
    ok, reason = mechanical_check(_ANSWER, issue, 1)
    assert ok and reason == ""


def test_mechanical_check_quote_not_in_answer():
    issue = _issue("不在证据里的引用", [0, 7])
    ok, reason = mechanical_check(_ANSWER, issue, 1)
    assert not ok and reason == "mechanical_fail:quote_not_in_answer"


def test_mechanical_check_span_invalid():
    issue = _issue("不支持平板设备", [999, 1005])
    ok, reason = mechanical_check(_ANSWER, issue, 1)
    assert not ok and reason == "mechanical_fail:span_invalid"
    issue2 = _issue("不支持平板设备", None)
    ok2, reason2 = mechanical_check(_ANSWER, issue2, 1)
    assert not ok2 and reason2 == "mechanical_fail:span_invalid"


def test_mechanical_check_evidence_ref_out_of_range():
    issue = _issue("不支持平板设备", [19, 26], ref="ev-9")
    ok, reason = mechanical_check(_ANSWER, issue, 1)
    assert not ok and reason == "mechanical_fail:evidence_ref_out_of_range"
    issue2 = _issue("不支持平板设备", [19, 26], ref="nonsense")
    ok2, reason2 = mechanical_check(_ANSWER, issue2, 1)
    assert not ok2 and reason2 == "mechanical_fail:evidence_ref_unparseable"


# ── 教师payload解析 ──────────────────────────────────────────

def test_parse_scores_valid():
    payload = {"scores": [
        {"idx": 0, "faithful": 3, "truthful": 2, "useful": 3, "reason": "ok"},
        {"idx": 1, "faithful": 1, "truthful": 3, "useful": 2, "reason": "差"},
    ]}
    out = parse_scores(payload)
    assert [s["idx"] for s in out] == [0, 1]
    assert out[0]["faithful"] == 3 and out[1]["truthful"] == 3


def test_parse_scores_drops_invalid():
    payload = {"scores": [
        {"idx": 0, "faithful": 5, "truthful": 2, "useful": 3},   # 越界
        {"idx": 1, "faithful": "x", "truthful": 2, "useful": 3},  # 类型错
        "not-a-dict",
        {"idx": 2, "faithful": 2, "truthful": 2, "useful": 1},
    ]}
    out = parse_scores(payload)
    assert [s["idx"] for s in out] == [2]
    assert parse_scores({}) == []
    assert parse_scores({"scores": "nope"}) == []


# ── gate_entry: 机械+教师协同 ─────────────────────────────────

def test_gate_entry_mechanical_fail_not_sent_to_teacher():
    entry = _entry([_issue("不存在于answer的引用", [0, 10])])
    stats: Counter = Counter()
    calls: list[str] = []

    def teacher(prompt: str, system: str, **_kw) -> tuple[dict, str, bool]:
        calls.append(prompt)
        return {}, "m", True

    out = gate_entry(entry, teacher, stats)
    assert calls == []                                   # 不送教师
    q = out["issues"][0]["quality"]
    assert q["faithful"] == 1 and q["truthful"] is None
    assert q["scored_by"] == "mechanical"
    assert stats["mechanical_fail_issues"] == 1
    assert stats["entries_all_mechanical_fail"] == 1


def test_gate_entry_teacher_scores_applied():
    entry = _entry([_issue("不支持平板设备", [19, 26])])
    stats: Counter = Counter()
    payload = {"scores": [{"idx": 0, "faithful": 3, "truthful": 2,
                           "useful": 3, "reason": "点名平板"}]}
    out = gate_entry(entry, _fake_teacher(payload), stats)
    q = out["issues"][0]["quality"]
    assert q == {"faithful": 3, "truthful": 2, "useful": 3,
                 "gate_reason": "点名平板", "scored_by": "teacher"}
    assert stats["entries_sent_to_teacher"] == 1


def test_gate_entry_teacher_parse_fail_marks_nulls():
    entry = _entry([_issue("不支持平板设备", [19, 26])])
    stats: Counter = Counter()
    out = gate_entry(entry, _fake_teacher({}), stats)    # 两次都解析失败
    q = out["issues"][0]["quality"]
    assert q["faithful"] is None and q["scored_by"] == "teacher_parse_fail"
    assert stats["retry_calls"] == 1                     # 一次重试
    assert stats["teacher_parse_fail_entries"] == 1


def test_call_teacher_network_retry_then_success(monkeypatch):
    import e5_explanation_gate
    monkeypatch.setattr(e5_explanation_gate, "_NET_RETRY_DELAYS", (0, 0, 0, 0))
    entry = _entry([_issue("不支持平板设备", [19, 26])])
    stats: Counter = Counter()
    payload = {"scores": [{"idx": 0, "faithful": 3, "truthful": 3,
                           "useful": 3, "reason": "ok"}]}
    attempts: list[int] = []

    def flaky(prompt: str, system: str, **_kw) -> tuple[dict, str, bool]:
        attempts.append(1)
        if len(attempts) < 3:
            raise OSError("ssl handshake timed out")
        return payload, "glm-5.3-test", True

    out = gate_entry(entry, flaky, stats)
    assert out["issues"][0]["quality"]["scored_by"] == "teacher"
    assert stats["network_errors"] == 2
    assert stats["entries_network_failed"] == 0


def test_call_teacher_raises_teacher_unavailable_when_exhausted(monkeypatch):
    import e5_explanation_gate
    monkeypatch.setattr(e5_explanation_gate, "_NET_RETRY_DELAYS", (0, 0, 0, 0))
    from e5_explanation_gate import TeacherUnavailable

    entry = _entry([_issue("不支持平板设备", [19, 26])])
    stats: Counter = Counter()

    def dead(prompt: str, system: str, **_kw) -> tuple[dict, str, bool]:
        raise OSError("connection refused")

    try:
        gate_entry(entry, dead, stats)
        raised = False
    except TeacherUnavailable:
        raised = True
    assert raised
    assert stats["network_errors"] == 8        # 2后缀×4退避


def test_gate_entry_mixed_issues():
    entry = _entry([
        _issue("不存在于answer的引用", [0, 10]),          # 机械失败
        _issue("不支持平板设备", [19, 26]),               # 送教师
    ])
    stats: Counter = Counter()
    payload = {"scores": [{"idx": 0, "faithful": 2, "truthful": 3,
                           "useful": 2, "reason": "ok"}]}
    out = gate_entry(entry, _fake_teacher(payload), stats)
    assert out["issues"][0]["quality"]["scored_by"] == "mechanical"
    assert out["issues"][1]["quality"]["scored_by"] == "teacher"


def test_gate_prompt_contains_all_parts():
    entry = _entry([_issue("不支持平板设备", [19, 26])])
    prompt = build_gate_prompt(entry, [0])
    for part in ("【问题】", "【待校验answer】", "ev-1:", "【教师判定】refute",
                 "issue 0:", "quote:", "explanation:", "平板、桌面、手持"):
        assert part in prompt


# ── verdict采样权重表 ─────────────────────────────────────────

def _quality(faithful, truthful, useful=3):
    return {"faithful": faithful, "truthful": truthful, "useful": useful,
            "gate_reason": "", "scored_by": "teacher"}


def test_row_weight_refute_low_score_downweighted():
    issues = [{"quality": _quality(1, 3)}, {"quality": _quality(3, 3)}]
    w, low = row_weight("refute", issues)
    assert w == LOW_QUALITY_WEIGHT and low is True


def test_row_weight_truthful_low_also_downweights():
    issues = [{"quality": _quality(3, 1)}]
    w, low = row_weight("refute", issues)
    assert w == LOW_QUALITY_WEIGHT and low is True


def test_row_weight_high_scores_not_downweighted():
    issues = [{"quality": _quality(3, 3)}, {"quality": _quality(2, 2)}]
    w, low = row_weight("refute", issues)
    assert w == 1.0 and low is False


def test_row_weight_null_scores_not_treated_as_low():
    issues = [{"quality": {"faithful": None, "truthful": None, "useful": None,
                           "gate_reason": "teacher_no_valid_score",
                           "scored_by": "teacher_parse_fail"}}]
    w, low = row_weight("refute", issues)
    assert w == 1.0 and low is False


def test_row_weight_support_never_downweighted():
    w, low = row_weight("support", [{"quality": _quality(1, 1)}])
    assert w == VERDICT_BASE_WEIGHTS["support"] and low is False


# ── 合并去重 + gated装配 ──────────────────────────────────────

def test_load_union_v3f_priority(tmp_path: Path):
    teacher_rows = [
        {"instance_id": "A", "verdict": "refute", "issues": [],
         "question": "q", "answer": "a", "evidence": []},
        {"instance_id": "B", "verdict": "refute", "issues": ["x"],
         "question": "q", "answer": "teacher-answer", "evidence": []},
    ]
    v3f_rows = [
        {"instance_id": "B", "verdict": "refute", "issues": ["x"],
         "question": "q", "answer": "v3f-answer", "evidence": []},
        {"instance_id": "C", "verdict": "support", "issues": [],
         "question": "q", "answer": "a", "evidence": []},
    ]
    tp = tmp_path / "teacher.jsonl"
    vp = tmp_path / "v3f.jsonl"
    tp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                          for r in teacher_rows), encoding="utf-8")
    vp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                          for r in v3f_rows), encoding="utf-8")
    entries = load_union(vp, tp)
    assert [e["instance_id"] for e in entries] == ["B"]   # 只有带issues的
    assert entries[0]["answer"] == "v3f-answer"           # v3f优先
    assert [e["instance_id"] for e in entries] == sorted(
        {e["instance_id"] for e in entries})              # 确定序


def test_build_gated_rows_preserves_order_and_fields():
    v3f_rows = [
        {"instance_id": "R1", "verdict": "refute", "issues": ["x"],
         "question": "q", "answer": "a", "evidence": [], "corpus": "c"},
        {"instance_id": "S1", "verdict": "support", "issues": [],
         "question": "q", "answer": "a", "evidence": [], "corpus": "c"},
    ]
    scored = {"R1": {"verdict": "refute",
                     "issues": [{"quality": _quality(1, 3)}]}}
    out = build_gated_rows(v3f_rows, scored)
    assert [r["instance_id"] for r in out] == ["R1", "S1"]
    assert out[0]["corpus"] == "c" and out[0]["answer"] == "a"  # 原字段保留
    assert out[0]["sample_weight"] == LOW_QUALITY_WEIGHT
    assert out[0]["downweight"] is True
    assert out[1]["sample_weight"] == 1.0 and out[1]["downweight"] is False


def test_build_report_distributions_and_findings():
    scored = {"R1": {"verdict": "refute", "issues": [
        {"quality": _quality(1, 3)},
        {"quality": {"faithful": None, "truthful": None, "useful": None,
                     "gate_reason": "teacher_no_valid_score",
                     "scored_by": "teacher_parse_fail"}},
        {"quality": {"faithful": 1, "truthful": None, "useful": None,
                     "gate_reason": "mechanical_fail:quote_not_in_answer",
                     "scored_by": "mechanical"}},
    ]}}
    gated_rows = [{"verdict": "refute", "issues": [{"quality": _quality(1, 3)}],
                   "sample_weight": LOW_QUALITY_WEIGHT, "downweight": True}]
    stats: Counter = Counter({"llm_requests": 3, "cache_hits": 1,
                              "mechanical_fail_issues": 1})
    report = build_report(scored, stats, gated_rows, v3f_only=1,
                          teacher_only=0)
    dist = report["score_distribution_all_union_issues"]
    assert dist["faithful"] == {"1": 2, "null": 1}
    assert dist["truthful"] == {"3": 1, "null": 2}
    assert report["gated_file"]["downweighted_rows"] == 1
    assert report["teacher"]["cache_hit_rate"] == 0.25
    problems = {f["problem"] for f in report["data_quality_findings"]}
    assert "mechanical_fail:quote_not_in_answer" in problems
    assert "teacher_no_valid_score" in problems


@pytest.mark.parametrize("verdict,expected", [
    ("support", 1.0), ("refute", 1.0), ("not_in_evidence", 1.0)])
def test_verdict_base_weights_table(verdict, expected):
    assert VERDICT_BASE_WEIGHTS[verdict] == expected
