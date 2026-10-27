"""eval_lib契约测试 (Wave 8-H1评测基础设施去重).

覆盖:
  - build_qa_input字段映射(含SourceRef六字段/默认值/必填契约)
  - classification_metrics与手工计算逐字段一致(小fixture)
  - 混淆矩阵格式兼容("pred|gold"非零键, LABELS迭代序)
  - load函数错误处理(坏行/缺字段/重复id/非法verdict→可读报错)
  - 冻结数字锁定: 91QA基线confusion的macro_f1=0.7212/accuracy=0.9121
    (与tools/eval_qa_module_vs_silver.py的既有输出逐位一致)
  - evaluate_module公共骨架(缺标签不进分母/module_kwargs转发/全缺报错)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    LABELS,
    QA_FROZEN,
    SILVER,
    accuracy,
    build_qa_input,
    classification_metrics,
    confusion_dict,
    confusion_matrix,
    confusion_of,
    evaluate_module,
    iter_qa_inputs,
    label_verdict,
    load_frozen_qa,
    load_silver_labels,
    macro_f1,
    macro_f1_raw,
    per_class_metrics,
    prf,
    read_jsonl,
    run_module_corpus,
    score_outcomes,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    VerificationResult,
)
from tools.build_answer_mutation_candidates import (  # noqa: E402
    request_from_dict,
)


# ------------------------------------------------------------ fixture

def make_record(iid: str = "qa-1", *, full_source_ref: bool = False,
                completeness: str | None = "open") -> dict:
    source_ref = {"doc_id": "doc-1", "section": "3.2.1", "page": 1,
                  "block_id": "b-1"}
    if full_source_ref:
        source_ref.update({"row_id": "r-9", "region_id": "reg-9"})
    evidence = {
        "evidence_id": "ev-1",
        "text": "响应时间为200ms。",
        "source_type": "text",
        "source_ref": source_ref,
        "scope_id": "doc-1:3.2.1",
        "completeness_proof": "scope limited to retrieved paragraph",
        "extraction_method": "manual_freeze",
        "extraction_confidence": 1.0,
    }
    if completeness is not None:
        evidence["completeness"] = completeness
    return {
        "instance_id": iid,
        "question": "响应时间是多少？",
        "answer": "响应时间为200ms。",
        "context_freeze_id": "freeze-abc",
        "evidence": [evidence],
    }


class StubModule:
    """verify()按instance_id查表; 记录module_kwargs供转发断言."""

    def __init__(self, verdict_of: dict[str, str]) -> None:
        self.verdict_of = verdict_of
        self.seen_kwargs: list[dict] = []

    def verify(self, request, **kwargs) -> VerificationResult:
        self.seen_kwargs.append(dict(kwargs))
        verdict = self.verdict_of[request.instance_id]
        claim = ClaimResult(
            claim_id="c1", claim_text=request.answer, verdict=verdict,
            check_item_candidates=(), evidence_refs=("ev-1",),
            rationale="stub", method="stub_method", confidence=1.0)
        return VerificationResult(
            instance_id=request.instance_id, question=request.question,
            answer=request.answer, verdict=verdict, status="ok",
            claim_results=(claim,), evidence_chain=(),
            considered_evidence_ids=(), context_freeze_id="freeze-abc",
            context_hash="h", context_integrity="unknown",
            applicability="applicable", rationale="stub")


# ------------------------------------------------------------ build_qa_input

def test_build_qa_input_maps_required_fields() -> None:
    request = build_qa_input(make_record())
    evidence = request.evidence[0]
    assert request.instance_id == "qa-1"
    assert request.question == "响应时间是多少？"
    assert request.answer == "响应时间为200ms。"
    assert request.context_freeze_id == "freeze-abc"
    assert evidence.evidence_id == "ev-1"
    assert evidence.text == "响应时间为200ms。"
    assert evidence.source_type == "text"
    assert evidence.scope_id == "doc-1:3.2.1"
    assert evidence.completeness == "open"
    assert evidence.completeness_proof == "scope limited to retrieved paragraph"
    assert evidence.extraction_method == "manual_freeze"
    assert evidence.extraction_confidence == 1.0


def test_build_qa_input_source_ref_six_fields() -> None:
    request = build_qa_input(make_record(full_source_ref=True))
    sr = request.evidence[0].source_ref
    assert (sr.doc_id, sr.section, sr.page, sr.block_id,
            sr.row_id, sr.region_id) == ("doc-1", "3.2.1", 1, "b-1",
                                         "r-9", "reg-9")
    # 六字段中的row_id/region_id缺省时用dataclass默认值
    default_sr = build_qa_input(make_record()).evidence[0].source_ref
    assert (default_sr.row_id, default_sr.region_id) == ("", "")


def test_build_qa_input_defaults_and_coercions() -> None:
    record = make_record(completeness=None)
    record["instance_id"] = 7          # 非str→str()
    evidence = build_qa_input(record).evidence[0]
    assert evidence.completeness == "unknown"      # 缺省契约
    assert build_qa_input(record).instance_id == "7"


@pytest.mark.parametrize("field", ["source_ref", "scope_id", "source_type",
                                   "evidence_id", "text"])
def test_build_qa_input_requires_frozen_context_fields(field: str) -> None:
    broken = make_record()
    del broken["evidence"][0][field]
    with pytest.raises((KeyError, TypeError)):
        build_qa_input(broken)


def test_request_from_dict_delegates_to_build_qa_input() -> None:
    assert request_from_dict(make_record()) == build_qa_input(make_record())
    assert request_from_dict(make_record(full_source_ref=True)) == \
        build_qa_input(make_record(full_source_ref=True))


def test_iter_qa_inputs_preserves_order() -> None:
    records = [make_record("qa-a"), make_record("qa-b"), make_record("qa-c")]
    assert [r.instance_id for r in iter_qa_inputs(records)] == \
        ["qa-a", "qa-b", "qa-c"]


# ------------------------------------------------------------ metrics

HAND_CONFUSION = Counter({("support", "support"): 1,
                          ("support", "not_in_evidence"): 1,
                          ("refute", "support"): 1,
                          ("refute", "refute"): 1,
                          ("not_in_evidence", "refute"): 1,
                          ("not_in_evidence", "not_in_evidence"): 3})


def test_prf_hand_computed() -> None:
    # support: tp=1 fp=1 fn=1; refute: tp=1 fp=1 fn=1; nie: tp=3 fp=1 fn=1
    assert prf(HAND_CONFUSION, "support") == (0.5, 0.5, 0.5)
    assert prf(HAND_CONFUSION, "refute") == (0.5, 0.5, 0.5)
    assert prf(HAND_CONFUSION, "not_in_evidence") == (0.75, 0.75, 0.75)


def test_classification_metrics_hand_computed() -> None:
    y_true = ["support", "support", "refute", "refute", "not_in_evidence",
              "not_in_evidence", "not_in_evidence", "not_in_evidence"]
    y_pred = ["support", "refute", "refute", "not_in_evidence",
              "not_in_evidence", "not_in_evidence", "not_in_evidence",
              "support"]
    metrics = classification_metrics(y_true, y_pred)
    assert metrics["accuracy"] == 0.625                 # 5/8
    assert metrics["macro_f1"] == round((0.5 + 0.5 + 0.75) / 3, 4)  # 0.5833
    assert metrics["per_class"] == {
        "support": {"precision": 0.5, "recall": 0.5, "f1": 0.5},
        "refute": {"precision": 0.5, "recall": 0.5, "f1": 0.5},
        "not_in_evidence": {"precision": 0.75, "recall": 0.75, "f1": 0.75},
    }
    assert metrics["confusion"] == {
        "support|support": 1, "support|not_in_evidence": 1,
        "refute|support": 1, "refute|refute": 1,
        "not_in_evidence|refute": 1, "not_in_evidence|not_in_evidence": 3,
    }


def test_confusion_dict_format_pred_gold_keys() -> None:
    # "pred|gold"键, 非零格, LABELS迭代序(与既有eval工具输出逐字段一致)
    out = confusion_dict(HAND_CONFUSION)
    assert list(out) == ["support|support", "support|not_in_evidence",
                         "refute|support", "refute|refute",
                         "not_in_evidence|refute",
                         "not_in_evidence|not_in_evidence"]
    assert sum(out.values()) == 8


def test_confusion_matrix_from_lists() -> None:
    y_true = ["support", "refute", "refute"]
    y_pred = ["support", "refute", "support"]
    assert confusion_matrix(y_true, y_pred) == {
        "support|support": 1, "refute|refute": 1, "support|refute": 1}


def test_confusion_of_rejects_length_mismatch_and_bad_verdicts() -> None:
    with pytest.raises(ValueError, match="长度不一致"):
        confusion_of(["support"], ["support", "refute"])
    with pytest.raises(ValueError, match="三态契约"):
        confusion_of(["support", "weird"], ["support", "refute"])


def test_macro_f1_uses_unrounded_per_class_mean() -> None:
    """权威定义: macro_f1 = round(未取整per-class F1的均值, 4)."""
    confusion = Counter({("support", "support"): 11,
                         ("refute", "refute"): 21,
                         ("not_in_evidence", "refute"): 3,
                         ("not_in_evidence", "not_in_evidence"): 56})
    raw = macro_f1_raw(confusion)
    assert macro_f1(confusion) == round(raw, 4)
    assert macro_f1(confusion) == round(sum(prf(confusion, label)[2]
                                            for label in LABELS) / 3, 4)
    per = per_class_metrics(confusion)
    assert per["refute"]["f1"] == round(prf(confusion, "refute")[2], 4)


def test_accuracy_rounds_to_four_decimals() -> None:
    assert accuracy(HAND_CONFUSION, 8) == 0.625
    assert accuracy(Counter({("support", "support"): 83}), 91) == 0.9121


def test_macro_f1_zero_division_free() -> None:
    empty = Counter()
    assert macro_f1(empty) == 0.0
    assert per_class_metrics(empty) == {
        label: {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        for label in LABELS}
    with pytest.raises(ValueError, match="分母"):
        classification_metrics([], [])


# ------------------------------------------------------------ 冻结数字锁定

def test_frozen_91qa_baseline_numbers() -> None:
    """eval_qa_module_vs_silver既有91QA基线: acc=0.9121/macroF1=0.7212."""
    confusion = Counter({
        ("support", "support"): 2,
        ("support", "not_in_evidence"): 1,
        ("refute", "refute"): 5,
        ("not_in_evidence", "support"): 4,
        ("not_in_evidence", "refute"): 3,
        ("not_in_evidence", "not_in_evidence"): 76,
    })
    assert accuracy(confusion, 91) == 0.9121
    assert macro_f1(confusion) == 0.7212
    # 直接由confusion重建列表再走classification_metrics, 数字必须一致
    preds: list[str] = []
    golds: list[str] = []
    for (pred, gold), count in confusion.items():
        preds.extend([pred] * count)
        golds.extend([gold] * count)
    metrics = classification_metrics(golds, preds)
    assert metrics["accuracy"] == 0.9121
    assert metrics["macro_f1"] == 0.7212
    assert metrics["confusion"]["not_in_evidence|not_in_evidence"] == 76
    assert "refute|support" not in metrics["confusion"]  # 零格不出现


# ------------------------------------------------------------ loading

def test_read_jsonl_skips_blank_lines(tmp_path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a": 1}\n\n{"a": 2}\n', encoding="utf-8")
    assert read_jsonl(path) == [{"a": 1}, {"a": 2}]


def test_read_jsonl_bad_line_raises_readable_error(tmp_path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_jsonl(path)


def test_load_frozen_qa_schema_errors(tmp_path) -> None:
    good = make_record()
    # 行缺字段
    missing_row = dict(good)
    del missing_row["question"]
    p1 = tmp_path / "missing_row.jsonl"
    p1.write_text(json.dumps(missing_row, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    with pytest.raises(ValueError, match="缺字段.*question"):
        load_frozen_qa(p1)
    # 证据缺字段
    missing_ev = json.loads(json.dumps(good, ensure_ascii=False))
    del missing_ev["evidence"][0]["scope_id"]
    p2 = tmp_path / "missing_ev.jsonl"
    p2.write_text(json.dumps(missing_ev, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    with pytest.raises(ValueError, match="evidence\\[0\\]缺字段.*scope_id"):
        load_frozen_qa(p2)
    # source_ref非对象
    bad_sr = json.loads(json.dumps(good, ensure_ascii=False))
    bad_sr["evidence"][0]["source_ref"] = "doc-1"
    p3 = tmp_path / "bad_sr.jsonl"
    p3.write_text(json.dumps(bad_sr, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    with pytest.raises(ValueError, match="source_ref不是对象"):
        load_frozen_qa(p3)
    # instance_id重复
    p4 = tmp_path / "dup.jsonl"
    p4.write_text(json.dumps(good, ensure_ascii=False) + "\n"
                  + json.dumps(make_record("qa-2"), ensure_ascii=False) + "\n"
                  + json.dumps(good, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    with pytest.raises(ValueError, match="instance_id重复: qa-1"):
        load_frozen_qa(p4)
    # 正常行照常通过
    p5 = tmp_path / "ok.jsonl"
    p5.write_text(json.dumps(good, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    assert load_frozen_qa(p5) == [good]


def test_load_silver_labels_errors(tmp_path) -> None:
    def write(name: str, rows: list[dict]) -> Path:
        path = tmp_path / name
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n"
                                for r in rows), encoding="utf-8")
        return path

    good = {"instance_id": "qa-1", "final_verdict": "support"}
    # 非法verdict
    with pytest.raises(ValueError, match="标签verdict非法"):
        load_silver_labels(write("bad_verdict.jsonl",
                                 [{**good, "final_verdict": "weird"}]))
    # 缺verdict
    with pytest.raises(ValueError, match="标签verdict非法: None"):
        load_silver_labels(write("no_verdict.jsonl",
                                 [{"instance_id": "qa-1"}]))
    # 缺instance_id
    with pytest.raises(ValueError, match="缺instance_id"):
        load_silver_labels(write("no_id.jsonl",
                                 [{"final_verdict": "support"}]))
    # 重复id
    with pytest.raises(ValueError, match="instance_id重复: qa-1"):
        load_silver_labels(write("dup.jsonl", [good, good]))
    # verdict_keys回退: final_verdict缺→gold_verdict
    fallback = {"instance_id": "qa-1", "gold_verdict": "refute"}
    labels = load_silver_labels(write("fallback.jsonl", [fallback]),
                                verdict_keys=("final_verdict", "gold_verdict"))
    assert labels == {"qa-1": "refute"}


def test_label_verdict_precedence_and_validation() -> None:
    assert label_verdict({"final_verdict": "refute"}, "X") == "refute"
    assert label_verdict({"gold_verdict": "support"}, "X") == "support"
    assert label_verdict({"final_verdict": "refute",
                          "gold_verdict": "support"}, "X") == "refute"
    with pytest.raises(ValueError, match="标签verdict非法"):
        label_verdict({"final_verdict": "unknown"}, "X")
    with pytest.raises(ValueError, match="标签verdict非法"):
        label_verdict({}, "X")


@pytest.mark.skipif(not (QA_FROZEN.exists() and SILVER.exists()),
                    reason="冻结语料/silver标签资产不在本检出中")
def test_real_assets_load_and_match_frozen_numbers() -> None:
    rows = load_frozen_qa()
    labels = load_silver_labels()
    assert len(rows) == 91
    assert len(labels) == 91
    assert {v for v in labels.values()} <= set(LABELS)
    assert Counter(labels.values()) == {
        "support": 6, "refute": 8, "not_in_evidence": 77}
    # 真实行经build_qa_input与request_from_dict逐字段一致(权威映射回归)
    for row in rows[:5]:
        assert request_from_dict(row) == build_qa_input(row)


# ------------------------------------------------------------ run/score

def test_run_module_corpus_outcome_schema() -> None:
    long_rationale = "r" * 250
    claim = ClaimResult(claim_id="c1", claim_text="t", verdict="support",
                        check_item_candidates=(), evidence_refs=("ev-1",),
                        rationale=long_rationale, method="m",
                        confidence=0.5)

    class OneClaimModule(StubModule):
        def verify(self, request, **kwargs) -> VerificationResult:
            return VerificationResult(
                instance_id=request.instance_id, question=request.question,
                answer=request.answer, verdict="support", status="partial",
                claim_results=(claim,), evidence_chain=(),
                considered_evidence_ids=(), context_freeze_id="f",
                context_hash="h", context_integrity="unknown",
                applicability="applicable", rationale="r",
                diagnostics=("d1",))

    outcomes = run_module_corpus(OneClaimModule({}), [make_record()])
    entry = outcomes["qa-1"]
    assert entry["verdict"] == "support"
    assert entry["status"] == "partial"
    assert entry["diagnostics"] == ["d1"]
    assert entry["claims"][0]["rationale"] == "r" * 200   # 截断200契约
    assert entry["claims"][0]["evidence_refs"] == ["ev-1"]


def test_score_outcomes_aggregates_methods() -> None:
    outcomes = {
        "qa-1": {"verdict": "support",
                 "claims": [{"method": "a"}, {"method": "b"}]},
        "qa-2": {"verdict": "refute", "claims": [{"method": "a"}]},
    }
    records = [make_record("qa-1"), make_record("qa-2")]
    labels = {"qa-1": "support", "qa-2": "support"}
    score = score_outcomes(outcomes, records, labels)
    assert score["claim_methods"] == {"a": 2, "b": 1}
    assert score["confusion[predicted, silver]"] == {
        "support|support": 1, "refute|support": 1}
    assert score["per_class"]["support"]["recall"] == 0.5


def test_evaluate_module_skeleton() -> None:
    records = [make_record("qa-1"), make_record("qa-2"), make_record("qa-3")]
    labels = {"qa-1": "support", "qa-2": "support"}     # qa-3缺标签
    module = StubModule({"qa-1": "support", "qa-2": "refute",
                         "qa-3": "support"})
    result = evaluate_module(module, records, labels, note="kw")
    assert result.n == 3
    assert result.n_evaluated == 2
    assert result.missing_labels == ["qa-3"]
    assert result.metrics["accuracy"] == 0.5            # 1/2, qa-3不进分母
    # support f1=0.6667(P=1,R=0.5), refute/nie无预测无金标 → f1=0
    assert result.metrics["macro_f1"] == round((2 / 3) / 3, 4)
    assert dict(result.methods) == {"stub_method": 2}   # 缺标签行不计
    assert dict(result.statuses) == {"ok": 2}
    assert result.per_row[2]["label"] is None           # 但保留预测明细
    assert result.per_row[2]["predicted"] == "support"
    assert module.seen_kwargs == [{"note": "kw"}, {"note": "kw"},
                                  {"note": "kw"}]       # kwargs转发给verify


def test_evaluate_module_all_missing_labels_raises() -> None:
    module = StubModule({"qa-1": "support"})
    with pytest.raises(ValueError, match="无共同instance_id"):
        evaluate_module(module, [make_record()], {})
