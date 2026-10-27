"""QA benchmark统一评测器与B0/B2/B3 baseline的回归测试.

fixture: 10条手写带gold标签样本(4个doc), 覆盖:
  macro-F1手算对拍 / citation precision / 分组split无泄漏 /
  invalid预测不移出分母 / check_item分层与route_question回退 /
  B0多数类 / B2词法阈值三态 / B3数值区间比对 / runs协议落盘.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from tools.eval.qa_benchmark import (  # noqa: E402
    B0Majority,
    B2Lexical,
    B3RuleNumeric,
    Prediction,
    QAExample,
    VERDICT_CLASSES,
    build_labeled_examples,
    compute_label_metrics,
    evaluate_by_check_item,
    evaluate_predictions,
    load_frozen_rows,
    load_silver_labels,
    make_group_splits,
    resolve_check_items,
    run_benchmark,
)
from tools.eval import qa_benchmark as qab  # noqa: E402

REAL_FROZEN = qab.DEFAULT_FROZEN
REAL_LABELS = qab.DEFAULT_LABELS

pytestmark_real = pytest.mark.skipif(
    not REAL_FROZEN.exists() or not REAL_LABELS.exists(),
    reason="真实冻结集/silver标签不存在",
)


def _ev(eid: str, text: str, doc: str, section: str) -> dict:
    return {
        "evidence_id": eid,
        "text": text,
        "source_type": "text",
        "source_ref": {"doc_id": doc, "section": section, "block_id": "block-000001",
                       "page": 1},
    }


def _row(iid: str, question: str, answer: str, doc: str, section: str,
         evidence: list[dict], label: str | None = None) -> QAExample:
    return QAExample(
        instance_id=iid, question=question, answer=answer,
        context_freeze_id="fixture-frozen-v1",
        evidence=tuple(
            qab.EvidenceView(
                evidence_id=e["evidence_id"], text=e["text"],
                doc_id=e["source_ref"]["doc_id"], section=e["source_ref"]["section"],
            ) for e in evidence
        ),
        label=label,
    )


def fixture_rows() -> list[QAExample]:
    """10条手写样本, 4个doc; 标签分布 support=4 / refute=3 / not_in_evidence=3."""
    return [
        _row("FIX-01", "系统响应时间要求是多少", "系统响应时间不超过500ms",
             "doc-甲", "3.1",
             [_ev("FIX-01-ev1", "性能需求：系统响应时间不超过500ms。", "doc-甲", "3.1")],
             "support"),
        _row("FIX-02", "系统响应时间要求是多少", "系统响应时间不超过300ms",
             "doc-甲", "3.1",
             [_ev("FIX-02-ev1", "性能需求：系统响应时间不小于500ms。", "doc-甲", "3.1")],
             "refute"),
        _row("FIX-03", "系统支持哪些数据导出格式", "系统支持将查询结果导出为PDF和Excel文件",
             "doc-甲", "3.2",
             [_ev("FIX-03-ev1", "数据导出：支持将查询结果导出为PDF文件。", "doc-甲", "3.2")],
             "not_in_evidence"),
        _row("FIX-04", "数据库并发连接数是多少", "数据库并发连接数为100个",
             "doc-乙", "3.1",
             [_ev("FIX-04-ev1", "数据库并发连接数为100个。", "doc-乙", "3.1")],
             "support"),
        _row("FIX-05", "数据保存期限要求是多少", "数据保存期限不超过30天",
             "doc-乙", "3.2",
             [_ev("FIX-05-ev1", "存储要求：数据保存期限不少于90天。", "doc-乙", "3.2")],
             "refute"),
        _row("FIX-06", "系统如何处理用户权限校验", "系统在每次操作前执行三级权限校验并记录审计日志",
             "doc-乙", "3.2",
             [_ev("FIX-06-ev1", "权限管理：用户登录时进行身份认证。", "doc-乙", "3.2")],
             "not_in_evidence"),
        _row("FIX-07", "系统支持几种数据输出方式", "系统支持两种数据输出方式：文本输出和图表输出",
             "doc-丙", "3.1",
             [_ev("FIX-07-ev1", "输出配置：支持文本输出与图表输出，共两种。", "doc-丙", "3.1")],
             "support"),
        _row("FIX-08", "消息重试次数上限是多少", "消息重试次数最多2次",
             "doc-丙", "3.2",
             [_ev("FIX-08-ev1", "可靠性：消息失败后重试，消息重试次数上限为3次。", "doc-丙", "3.2")],
             "refute"),
        _row("FIX-09", "缓存容量上限是多少", "缓存容量不超过2GB",
             "doc-丁", "3.1",
             [_ev("FIX-09-ev1", "缓存配置：缓存容量上限为2048MB。", "doc-丁", "3.1")],
             "support"),
        _row("FIX-10", "部署环境有什么要求", "系统需部署于国产化信创服务器环境",
             "doc-丁", "3.2",
             [_ev("FIX-10-ev1", "运行环境：支持主流服务器操作系统。", "doc-丁", "3.2")],
             "not_in_evidence"),
    ]


# ═════════════════ 指标正确性 (手算对拍) ═════════════════


def test_macro_f1_matches_hand_computation() -> None:
    gold = ["support"] * 4 + ["refute"] * 3 + ["not_in_evidence"] * 3
    verdicts = ["support", "support", "support", "refute",
                "refute", "refute", "not_in_evidence",
                "not_in_evidence", "not_in_evidence", "support"]
    metrics = compute_label_metrics(gold, verdicts)
    assert metrics["n"] == 10
    assert metrics["accuracy"] == pytest.approx(0.7)
    assert metrics["macro_f1"] == pytest.approx(25 / 36)
    assert metrics["per_class"]["support"]["f1"] == pytest.approx(0.75)
    assert metrics["per_class"]["support"]["precision"] == pytest.approx(0.75)
    assert metrics["per_class"]["refute"]["f1"] == pytest.approx(2 / 3)
    assert metrics["per_class"]["refute"]["support"] == 3
    assert metrics["per_class"]["not_in_evidence"]["f1"] == pytest.approx(2 / 3)
    matrix = metrics["confusion_matrix"]["matrix"]
    assert matrix[0] == [3, 1, 0]
    assert matrix[1] == [0, 2, 1]
    assert matrix[2] == [1, 0, 2]


def test_invalid_predictions_stay_in_denominators() -> None:
    metrics = compute_label_metrics(
        ["support", "support"], ["support", "banana"])
    assert metrics["n_invalid"] == 1
    assert metrics["accuracy"] == pytest.approx(0.5)
    assert metrics["per_class"]["support"]["support"] == 2      # recall分母保留
    assert metrics["per_class"]["support"]["recall"] == pytest.approx(0.5)
    assert metrics["per_class"]["support"]["predicted"] == 1
    assert metrics["confusion_matrix"]["invalid_by_gold"]["support"] == 1


def test_evaluate_predictions_citation_precision_and_alignment() -> None:
    rows = [r for r in fixture_rows() if r.instance_id in ("FIX-01", "FIX-02")]
    preds = [
        Prediction("FIX-01", "support", ("FIX-01-ev1",)),
        Prediction("FIX-02", "refute", ("FIX-02-ev1", "FIX-99-ev9")),
    ]
    metrics = evaluate_predictions(rows, preds)
    assert metrics["citation"]["n_citations"] == 3
    assert metrics["citation"]["n_valid"] == 2
    assert metrics["citation"]["precision"] == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        evaluate_predictions(rows, [preds[0], preds[0]])       # instance_id错位
    with pytest.raises(ValueError):
        evaluate_predictions([rows[0]], [])                    # 长度不一致


def test_evaluate_predictions_invalid_ids_recorded() -> None:
    rows = [r for r in fixture_rows() if r.instance_id in ("FIX-04", "FIX-06")]
    preds = [
        Prediction("FIX-04", "支持", (), True, "非法verdict"),
        Prediction("FIX-06", None, (), True, "abstain"),
    ]
    metrics = evaluate_predictions(rows, preds)
    assert metrics["n_invalid"] == 2
    assert set(metrics["invalid_instance_ids"]) == {"FIX-04", "FIX-06"}
    assert metrics["n_abstain"] == 2
    assert metrics["n"] == 2                                     # 分母未缩小
    assert metrics["accuracy"] == 0.0


def test_evaluate_by_check_item_stratification() -> None:
    rows = [r for r in fixture_rows() if r.instance_id in ("FIX-01", "FIX-02")]
    rows = [
        replace(r, check_items=("参数A", "参数B"))
        if r.instance_id == "FIX-01" else replace(r, check_items=("参数B",))
        for r in rows
    ]
    preds = [Prediction("FIX-01", "support", ("FIX-01-ev1",)),
             Prediction("FIX-02", "refute", ("FIX-02-ev1",))]
    strata = evaluate_by_check_item(rows, preds)
    assert set(strata) == {"参数A", "参数B"}
    assert strata["参数A"]["n"] == 1
    assert strata["参数B"]["n"] == 2
    assert strata["参数B"]["macro_f1"] == pytest.approx(2 / 3)   # 两类各命中1/1


# ═════════════════ 分组split无泄漏 ═════════════════


def test_group_split_no_doc_leakage_and_deterministic() -> None:
    rows = fixture_rows()
    split_a, info_a = make_group_splits(rows, seed=7)
    split_b, _ = make_group_splits(rows, seed=7)
    assert split_a == split_b                                    # 固定seed可复现
    assert info_a["mode"] == "doc"                               # 4个doc → doc级分组
    assert sum(info_a["sizes"].values()) == len(rows)
    for phase in ("train", "dev", "test"):
        assert info_a["sizes"][phase] > 0
    doc_phase = {}
    for row in rows:
        phase = split_a[row.instance_id]
        doc = row.evidence[0].doc_id
        doc_phase.setdefault(doc, set()).add(phase)
    assert all(len(phases) == 1 for phases in doc_phase.values())  # 同doc不跨split
    split_c, _ = make_group_splits(rows, seed=99)
    doc_phase_c = {}
    for row in rows:
        doc_phase_c.setdefault(row.evidence[0].doc_id, set()).add(split_c[row.instance_id])
    assert all(len(phases) == 1 for phases in doc_phase_c.values())


def test_group_split_section_fallback_single_doc() -> None:
    rows = []
    for r in fixture_rows():
        origin = r.evidence[0].doc_id                         # 原doc名作为section前缀
        rows.append(replace(r, evidence=tuple(
            qab.EvidenceView(e.evidence_id, e.text, "同一doc", f"{origin}-{e.section}")
            for e in r.evidence)))
    row_split, info = make_group_splits(rows, seed=7)
    assert info["mode"] == "section"                            # 单doc → section回退
    section_phase = {}
    for row in rows:
        section_phase.setdefault(row.evidence[0].section, set()).add(row_split[row.instance_id])
    assert all(len(phases) == 1 for phases in section_phase.values())  # 同section不跨split
    assert sum(info["sizes"].values()) == 10


# ═════════════════ check_item解析 ═════════════════


def test_resolve_check_items_silver_first_then_router_fallback() -> None:
    row = fixture_rows()[0]
    silver = {"claims": [{"check_items": ["检查甲", "检查乙"]},
                         {"check_items": ["检查甲"]}]}
    assert resolve_check_items(row, silver) == ("检查甲", "检查乙")
    routed = resolve_check_items(row, None)                     # 回退route_question
    assert "PARAM-01" in routed                                 # "响应时间" → PARAM-01
    unrouted = resolve_check_items(
        QAExample("X", "随便的问题", "随便的答案", "cfid", ()), None)
    assert unrouted == ("<unrouted>",)


# ═════════════════ B0 / B2 / B3 输出合法性 ═════════════════


def _views(rows: list[QAExample]) -> list[QAExample]:
    return [replace(r, label=None, check_items=()) for r in rows]


def test_b0_majority_train_prior() -> None:
    rows = fixture_rows()
    train = [rows[2], rows[5], rows[9], rows[0]]              # 3×nie + 1×support
    b0 = B0Majority(train)
    assert b0.majority == "not_in_evidence"
    preds = b0.predict(_views(rows), dev_rows=[])
    assert len(preds) == len(rows)
    assert all(p.verdict in VERDICT_CLASSES for p in preds)
    assert {p.verdict for p in preds} == {"not_in_evidence"}
    assert b0.prior["support"] == pytest.approx(0.25)


def test_b0_majority_tie_break_deterministic() -> None:
    rows = fixture_rows()
    b0 = B0Majority([rows[0], rows[2]])                       # support与nie各1票
    assert b0.majority == "not_in_evidence"                   # 平票→类名字典序


def test_b2_lexical_three_way_mapping() -> None:
    rows = {r.instance_id: r for r in fixture_rows()}
    b2 = B2Lexical(support_threshold=0.5)
    targets = [rows["FIX-01"], rows["FIX-02"], rows["FIX-06"]]
    preds = {p.instance_id: p for p in b2.predict(_views(targets), dev_rows=[])}
    assert set(preds) == {"FIX-01", "FIX-02", "FIX-06"}
    assert preds["FIX-01"].verdict == "support"               # 高重叠→support
    assert preds["FIX-01"].cited_evidence_ids == ("FIX-01-ev1",)
    assert preds["FIX-02"].verdict == "refute"                # 数值冲突(300ms↔500ms)→refute
    assert "FIX-02-ev1" in preds["FIX-02"].cited_evidence_ids
    assert preds["FIX-06"].verdict == "not_in_evidence"       # 低重叠→NIE
    assert preds["FIX-06"].cited_evidence_ids == ()


def test_b2_lexical_tunes_threshold_on_dev() -> None:
    rows = fixture_rows()
    split, _ = make_group_splits(rows, seed=7)
    dev = [r for r in rows if split[r.instance_id] == "dev"]
    b2 = B2Lexical()
    preds = b2.predict(_views(rows), dev_rows=dev)
    assert len(preds) == len(rows)
    assert all(p.verdict in VERDICT_CLASSES for p in preds)
    assert b2.support_threshold is not None
    assert 0.05 <= b2.support_threshold <= 0.9


def test_b3_rule_numeric_interval_semantics() -> None:
    rows = {r.instance_id: r for r in fixture_rows()}
    b3 = B3RuleNumeric()
    targets = ["FIX-01", "FIX-02", "FIX-04", "FIX-05", "FIX-06", "FIX-08", "FIX-09"]
    preds = {p.instance_id: p for p in
             b3.predict(_views([rows[t] for t in targets]), dev_rows=[])}
    assert preds["FIX-01"].verdict == "support"               # le500 ≡ le500 蕴含
    assert preds["FIX-01"].cited_evidence_ids == ("FIX-01-ev1",)
    assert preds["FIX-02"].verdict == "refute"                # le300 ⊥ ge500 互斥
    assert preds["FIX-04"].verdict == "support"               # eq100 ≡ eq100
    assert preds["FIX-05"].verdict == "refute"                # le30天 ⊥ ge90天 (单位归一)
    assert preds["FIX-06"].verdict == "not_in_evidence"       # 无数值claim
    assert preds["FIX-08"].verdict == "refute"                # le2 ⊥ eq3 (subject对齐)
    assert preds["FIX-09"].verdict == "support"               # 2GB == 2048MB 蕴含
    assert preds["FIX-09"].cited_evidence_ids == ("FIX-09-ev1",)


def test_b3_subject_mismatch_is_not_evidence() -> None:
    b3 = B3RuleNumeric()
    row = QAExample(
        "FIX-SUB", "缓存容量上限是多少", "日志保留期限不少于30天", "cfid",
        (qab.EvidenceView("FIX-SUB-ev1", "缓存容量不超过100GB。", "doc", "3.1"),))
    preds = b3.predict([row], dev_rows=[])
    assert preds[0].verdict == "not_in_evidence"              # subject不同→不对齐


# ═════════════════ runs协议 + 端到端 ═════════════════


def _write_fixture_files(tmp_path: Path) -> tuple[Path, Path]:
    rows = fixture_rows()
    frozen_records = [
        {
            "instance_id": r.instance_id, "question": r.question, "answer": r.answer,
            "context_freeze_id": r.context_freeze_id,
            "evidence": [{
                "evidence_id": e.evidence_id, "text": e.text, "source_type": "text",
                "source_ref": {"doc_id": e.doc_id, "section": e.section,
                               "block_id": "block-000001", "page": 1},
            } for e in r.evidence],
        } for r in rows
    ]
    label_records = [
        {"instance_id": r.instance_id, "final_verdict": r.label,
         "claims": [{"claim_id": "c1", "claim_text": r.answer[:10],
                     "verdict": r.label, "check_items": [f"检查-{r.instance_id}"],
                     "evidence_refs": [], "rationale": "", "confidence": 0.9}]}
        for r in rows
    ]
    frozen_path = tmp_path / "frozen.jsonl"
    labels_path = tmp_path / "labels.jsonl"
    frozen_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in frozen_records) + "\n",
        encoding="utf-8")
    labels_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in label_records) + "\n",
        encoding="utf-8")
    return frozen_path, labels_path


def test_run_benchmark_end_to_end_runs_protocol(tmp_path: Path) -> None:
    frozen_path, labels_path = _write_fixture_files(tmp_path)
    loaded = load_frozen_rows(frozen_path)
    assert [r.instance_id for r in loaded] == [f"FIX-{i:02d}" for i in range(1, 11)]
    labels = load_silver_labels(labels_path)
    labeled, n_unlabeled = build_labeled_examples(loaded, labels)
    assert n_unlabeled == 0
    assert labeled[0].check_items == ("检查-FIX-01",)          # silver claims优先

    result, run_path = run_benchmark(
        frozen_path=frozen_path, labels_path=labels_path, seed=7,
        out_root=tmp_path / "runs")
    assert (run_path / "config.json").exists()
    assert (run_path / "result.json").exists()
    assert (run_path / "metrics_table.md").exists()
    cfg = json.loads((run_path / "config.json").read_text(encoding="utf-8"))
    assert cfg["script"] == "qa_benchmark"
    assert cfg["config"]["seed"] == 7
    assert set(result["baselines"]) == {"B0_majority", "B2_lexical", "B3_rule_numeric"}
    for entry in result["baselines"].values():
        m = entry["metrics"]
        assert 0.0 <= m["macro_f1"] <= 1.0
        assert 0.0 <= m["accuracy"] <= 1.0
        assert m["n_invalid"] == 0
        assert set(m["per_class"]) == set(VERDICT_CLASSES)
        assert entry["by_check_item"]
    assert "silver" in result["labels"]["source"]
    assert result["labels"]["is_gold"] is False
    report = (run_path / "metrics_table.md").read_text(encoding="utf-8")
    assert "B2_lexical" in report and "macro_f1" in report


# ═════════════════ 真实数据集成 (结构断言, 不锁silver数字) ═════════════════


@pytestmark_real
def test_real_frozen_split_invariants() -> None:
    rows = load_frozen_rows(REAL_FROZEN)
    labels = load_silver_labels(REAL_LABELS)
    labeled, n_unlabeled = build_labeled_examples(rows, labels)
    assert len(rows) == 91
    assert n_unlabeled == 0
    split_a, info = make_group_splits(labeled, seed=qab.DEFAULT_SEED)
    split_b, _ = make_group_splits(labeled, seed=qab.DEFAULT_SEED)
    assert split_a == split_b                                # 固定seed可复现
    assert info["mode"] == "section"                         # 单doc → section回退
    assert sum(info["sizes"].values()) == 91
    group_of = {}
    for row in labeled:
        group_of.setdefault(
            f"{row.evidence[0].doc_id}::{row.evidence[0].section}" if row.evidence
            else "<no-evidence>", set()).add(split_a[row.instance_id])
    assert all(len(phases) == 1 for phases in group_of.values())   # 组不跨split


@pytestmark_real
def test_real_baselines_output_valid(tmp_path: Path) -> None:
    result, run_path = run_benchmark(out_root=tmp_path / "runs")
    assert result["frozen"]["n_rows"] == 91
    assert result["n_unlabeled"] == 0
    eval_n = result["n_eval_rows"]
    assert eval_n == result["split"]["sizes"]["test"]
    assert eval_n > 0
    for name, entry in result["baselines"].items():
        m = entry["metrics"]
        assert m["n"] == eval_n
        assert m["n_invalid"] == 0
        assert 0.0 <= m["macro_f1"] <= 1.0
        if m["citation"]["n_citations"]:
            assert 0.0 <= m["citation"]["precision"] <= 1.0
        assert entry["by_check_item"]
    for pred_cls in VERDICT_CLASSES:
        assert pred_cls in result["baselines"]["B0_majority"]["metrics"]["per_class"]
