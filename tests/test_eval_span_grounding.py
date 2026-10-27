"""Tests for tools/eval_span_grounding.py (49号协议span评估器).

纯逻辑测试: Wilson区间数学(手算对照+独立公式交叉验证)、verdict/span_type
归一、记录状态优先级、去重/冲突计数、类型分组、空输入与不足样本处理、
markdown渲染、导出JSON两种容器格式(合成数据, 无真实数据文件依赖).
"""

import json
import math
from pathlib import Path

import pytest

from tools.eval_span_grounding import (
    MIN_SAMPLE,
    SPAN_TYPES,
    TARGET_PRECISION,
    Z95,
    build_conclusion,
    dedup_records,
    evaluate,
    load_annotation_file,
    normalize_span_type,
    normalize_verdict,
    record_status,
    render_markdown,
    span_key,
    type_metrics,
    wilson_interval,
)


def make_record(
    span_text: str = "1920×1080",
    span_type: str = "quantity_unit",
    block_index: int = 3,
    verdict: str = "correct",
    ts: object = 100,
) -> dict:
    return {
        "span_text": span_text,
        "span_type": span_type,
        "block_index": block_index,
        "verdict": verdict,
        "ts": ts,
    }


# ------------------------------------------------------------ Wilson interval


@pytest.mark.parametrize(
    "k,n,expected",
    [
        (45, 50, (0.7864, 0.9565)),  # 手算: p=0.9, z=1.95996
        (25, 50, (0.3664, 0.6336)),  # p=0.5, 区间关于0.5对称
        (1, 1, (0.2065, 1.0)),  # 小样本上界钳到1
        (0, 10, (0.0, 0.2775)),  # 0命中时下界钳到0
        (50, 50, (0.9287, 1.0)),  # 全对: 下界<1(诚实)
        (0, 1, (0.0, 0.7935)),
        (5, 7, (0.3589, 0.9178)),
    ],
)
def test_wilson_known_hand_computed_values(k: int, n: int, expected: tuple) -> None:
    low, high = wilson_interval(k, n)
    assert low == pytest.approx(expected[0], abs=1e-3)
    assert high == pytest.approx(expected[1], abs=1e-3)


def test_wilson_matches_independent_formula_rearrangement() -> None:
    # 用另一种书写排列的公式独立交叉验证(非复制实现).
    for k, n in [(3, 7), (12, 40), (0, 3), (9, 9), (77, 101), (90, 100)]:
        z = 1.96
        p_hat = k / n
        denom = 1.0 + z**2 / n
        center = (p_hat + z**2 / (2.0 * n)) / denom
        half = (z / denom) * math.sqrt(p_hat * (1.0 - p_hat) / n + z**2 / (4.0 * n**2))
        expected = (max(0.0, center - half), min(1.0, center + half))
        got = wilson_interval(k, n, z=z)
        assert got is not None
        assert got[0] == pytest.approx(expected[0])
        assert got[1] == pytest.approx(expected[1])


def test_wilson_interval_contains_point_estimate() -> None:
    for k, n in [(7, 20), (19, 20), (1, 20), (10, 10)]:
        low, high = wilson_interval(k, n)
        assert low <= k / n <= high


def test_wilson_edge_and_error_cases() -> None:
    assert wilson_interval(0, 0) is None  # 无样本: 区间无定义, 不给假(0,0)
    with pytest.raises(ValueError):
        wilson_interval(3, 2)  # k > n
    with pytest.raises(ValueError):
        wilson_interval(-1, 5)  # k < 0
    with pytest.raises(ValueError):
        wilson_interval(1, -5)  # n < 0
    low, high = wilson_interval(0, 5)
    assert low == 0.0 and high > 0.0
    low, high = wilson_interval(5, 5)
    assert high == 1.0 and low < 1.0


def test_wilson_default_z_is_95_percent_two_sided() -> None:
    assert Z95 == pytest.approx(1.959963984540054)
    # z=1.96与默认z的区间差异<1e-3(手算口径一致性).
    a = wilson_interval(45, 50, z=1.96)
    b = wilson_interval(45, 50)
    assert a[0] == pytest.approx(b[0], abs=1e-3)
    assert a[1] == pytest.approx(b[1], abs=1e-3)


# ------------------------------------------------- normalization / validation


def test_normalize_verdict_tolerant_but_strict() -> None:
    assert normalize_verdict("correct") == "correct"
    assert normalize_verdict(" Correct ") == "correct"
    assert normalize_verdict("INCORRECT") == "incorrect"
    assert normalize_verdict("") == ""
    assert normalize_verdict(None) == ""
    assert normalize_verdict("maybe") == ""
    assert normalize_verdict("✓") == ""


def test_normalize_span_type_lowercase() -> None:
    assert normalize_span_type(" Predicate ") == "predicate"
    assert normalize_span_type(None) == ""
    assert normalize_span_type("Quantity_Unit") == "quantity_unit"


def test_record_status_priority_and_cases() -> None:
    assert record_status(make_record()) == "ok"
    assert record_status(make_record(verdict="maybe")) == "invalid_verdict"
    assert record_status(make_record(span_type="subject")) == "unknown_type"
    # verdict非法+类型未知: 先判verdict(优先级在类型之前).
    assert record_status(make_record(span_type="subject", verdict="maybe")) == "invalid_verdict"
    assert record_status(make_record(span_text="")) == "missing_field"
    assert record_status(make_record(span_text=None)) == "missing_field"
    assert record_status({"verdict": "correct"}) == "missing_field"
    assert record_status("not-a-dict") == "malformed"
    assert record_status([1, 2]) == "malformed"


# -------------------------------------------------------------------- dedup


def test_dedup_exact_duplicate_events_counted_once() -> None:
    first = make_record()
    twin = make_record()
    result = dedup_records([first, twin])
    assert len(result["kept"]) == 1
    assert result["n_duplicate_events"] == 1
    assert result["n_reannotated_keys"] == 0
    assert result["n_conflicting_keys"] == 0


def test_dedup_latest_ts_wins_on_verdict_conflict() -> None:
    early = make_record(verdict="incorrect", ts=100)
    late = make_record(verdict="correct", ts=200)
    result = dedup_records([early, late])
    assert len(result["kept"]) == 1
    assert result["kept"][0]["verdict"] == "correct"
    assert result["n_reannotated_keys"] == 1
    assert result["n_conflicting_keys"] == 1


def test_dedup_older_ts_arriving_later_is_dropped() -> None:
    late = make_record(verdict="correct", ts=200)
    early = make_record(verdict="incorrect", ts=100)
    result = dedup_records([late, early])
    assert result["kept"][0]["verdict"] == "correct"
    assert result["n_dropped"] == 1


def test_dedup_tie_ts_last_position_wins() -> None:
    a = make_record(verdict="incorrect", ts=None)
    b = make_record(verdict="correct", ts=None)
    result = dedup_records([a, b])
    assert result["kept"][0]["verdict"] == "correct"


def test_dedup_key_normalizes_type_and_block_index() -> None:
    # 大小写/空白归一后同键; 类型原文不同但归一相同 -> 同一span的重标.
    a = make_record(span_type=" Predicate ", block_index="7")
    b = make_record(span_type="predicate", block_index=7, verdict="incorrect")
    result = dedup_records([a, b])
    assert len(result["kept"]) == 1
    assert result["n_conflicting_keys"] == 1


def test_span_key_components() -> None:
    key = span_key(make_record(span_text="提供数据获取", span_type="Predicate", block_index=12))
    assert key == ("提供数据获取", "predicate", "12")
    assert span_key(make_record(block_index=None)) == ("1920×1080", "quantity_unit", "")


# ------------------------------------------------------------ type metrics


def test_type_metrics_counts_and_target_logic() -> None:
    records = [make_record(verdict="correct") for _ in range(4)]
    records.append(make_record(verdict="incorrect"))
    metrics = type_metrics(records, min_sample=5, target=0.7)
    assert metrics["n"] == 5
    assert metrics["n_correct"] == 4
    assert metrics["n_incorrect"] == 1
    assert metrics["precision"] == 0.8
    assert metrics["target_met"] is True
    assert metrics["sufficiency"] == "ok"
    assert metrics["ci95"] is not None
    assert metrics["ci95"][0] <= 0.8 <= metrics["ci95"][1]


def test_type_metrics_insufficient_and_empty() -> None:
    metrics = type_metrics([make_record()], min_sample=50)
    assert metrics["sufficiency"] == "insufficient"
    empty = type_metrics([])
    assert empty["n"] == 0
    assert empty["precision"] is None
    assert empty["ci95"] is None
    assert empty["sufficiency"] == "insufficient"
    assert empty["target_met"] is None
    assert empty["ci_lower_meets_target"] is None


def test_type_metrics_ci_lower_strong_target_semantics() -> None:
    # 49/50=0.98点估计达标, 但Wilson下界0.8950 < 0.90 -> 弱达标.
    records = [make_record(verdict="correct") for _ in range(49)]
    records.append(make_record(verdict="incorrect"))
    metrics = type_metrics(records, min_sample=50, target=0.90)
    assert metrics["precision"] == 0.98
    assert metrics["target_met"] is True
    assert metrics["ci_lower_meets_target"] is False


# ---------------------------------------------------------------- evaluate


def test_evaluate_groups_by_type_and_reports_hygiene() -> None:
    records = [
        make_record(span_type="identifier", span_text="JCYY-GN-01", verdict="correct"),
        make_record(span_type="identifier", span_text="JCYY-GN-02", verdict="incorrect"),
        make_record(span_type="quantity_unit", span_text="10Mbps", verdict="correct"),
        make_record(span_type="predicate", span_text="提供查询", verdict="correct"),
        make_record(span_type="modal", span_text="应", verdict="correct"),
        make_record(span_type="modal", span_text="宜", verdict="incorrect"),
        make_record(span_type="reference", span_text="见3.2.1", verdict="correct"),
        # 数据卫生: 未知类型/非法verdict/缺失字段/非dict.
        make_record(span_type="subject", span_text="主语", verdict="correct"),
        make_record(span_type="subject", span_text="主语2", verdict="correct"),
        make_record(span_type="negative", verdict="maybe"),
        make_record(span_type="negative", span_text="", verdict="correct"),
        "garbage",
    ]
    result = evaluate(records)
    assert result["n_records"] == 12
    assert result["record_status_counts"] == {
        "invalid_verdict": 1,
        "malformed": 1,
        "missing_field": 1,
        "ok": 7,
        "unknown_type": 2,
    }
    assert result["unknown_type_counts"] == {"subject": 2}
    assert result["n_evaluated"] == 7
    assert result["overall"]["n_correct"] == 5
    assert result["overall"]["n_incorrect"] == 2
    assert result["by_type"]["identifier"]["n"] == 2
    assert result["by_type"]["identifier"]["n_correct"] == 1
    assert result["by_type"]["modal"]["n_incorrect"] == 1
    # 六个协议类型全部出现在表中(未标注类型n=0, insufficient).
    assert list(result["by_type"].keys()) == list(SPAN_TYPES)
    assert result["by_type"]["negative"]["n"] == 0
    assert "negative" in result["insufficient_types"]
    assert "identifier" in result["insufficient_types"]


def test_evaluate_dedups_before_metrics() -> None:
    records = [
        make_record(span_type="predicate", span_text="提供传输", verdict="incorrect", ts=1),
        make_record(span_type="predicate", span_text="提供传输", verdict="correct", ts=2),
    ]
    result = evaluate(records)
    assert result["n_records"] == 2
    assert result["n_evaluated"] == 1
    assert result["by_type"]["predicate"]["n_correct"] == 1
    assert result["dedup"]["n_conflicting_keys"] == 1


def test_evaluate_empty_input() -> None:
    result = evaluate([])
    assert result["n_records"] == 0
    assert result["n_evaluated"] == 0
    assert result["overall"]["precision"] is None
    assert result["overall"]["ci95"] is None
    assert result["insufficient_types"] == list(SPAN_TYPES)
    assert "无有效标注" in result["conclusion"]
    markdown = render_markdown(result)
    assert "—" in markdown  # 空指标渲染为占位符而非崩溃


def test_evaluate_min_sample_threshold_flips_sufficiency() -> None:
    records = [make_record(span_type="predicate", span_text=f"提供功能{i}") for i in range(3)]
    strict = evaluate(records, min_sample=5)
    loose = evaluate(records, min_sample=3)
    assert strict["by_type"]["predicate"]["sufficiency"] == "insufficient"
    assert loose["by_type"]["predicate"]["sufficiency"] == "ok"
    assert MIN_SAMPLE == 50
    assert TARGET_PRECISION == 0.90


def test_build_conclusion_variants() -> None:
    empty = type_metrics([])
    text = build_conclusion(empty, {}, MIN_SAMPLE, TARGET_PRECISION)
    assert "无有效标注" in text
    ok_records = [make_record(span_type="identifier", span_text=f"ID-{i:03d}") for i in range(60)]
    metrics = type_metrics(ok_records)
    text = build_conclusion(metrics, {"identifier": metrics}, MIN_SAMPLE, TARGET_PRECISION)
    assert "1.0000" in text
    assert "强达标" in text  # 60/60的Wilson下界(约0.9398)超过0.90


# ------------------------------------------------------------ render / load


def test_render_markdown_table_structure() -> None:
    records = [
        make_record(span_type="identifier", span_text="ID-001", verdict="correct"),
        make_record(span_type="identifier", span_text="ID-002", verdict="correct"),
        make_record(span_type="predicate", span_text="提供查询", verdict="incorrect"),
    ]
    result = evaluate(records)
    markdown = render_markdown(result)
    assert "# Span Grounding 标注评估(49号协议)" in markdown
    assert "| span_type | n | correct | incorrect | precision | Wilson 95% CI |" in markdown
    assert "| identifier | 2 | 2 | 0 |" in markdown
    assert "insufficient" in markdown
    assert "去重后评估span: 3个" in markdown
    assert "指标边界" in markdown  # notes渲染


def test_load_annotation_file_accepts_both_containers(tmp_path: Path) -> None:
    as_list = tmp_path / "list.json"
    as_list.write_text(
        json.dumps([make_record()], ensure_ascii=False), encoding="utf-8"
    )
    assert load_annotation_file(as_list) == [make_record()]
    as_object = tmp_path / "object.json"
    as_object.write_text(
        json.dumps({"annotations": [make_record()]}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert load_annotation_file(as_object) == [make_record()]


def test_load_annotation_file_rejects_wrong_payload(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"spans": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="annotations"):
        load_annotation_file(bad)
    scalar = tmp_path / "scalar.json"
    scalar.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError, match="int"):
        load_annotation_file(scalar)
