"""Tests for tools/build_localization_gold_template.py (S7定位gold标注协议).

三层测试:
  1. 纯评分内核: overlap/PRF/AVeriTeC/SpanF1/κ/IAA 手算对照(合成fixture,
     无真实数据文件依赖);
  2. 模板生成: 真实数据(91 QA + 17违例)跑通, 字段完整性与初值校验(写tmp);
  3. canonical 17违例表: 与taxonomy v3/content_list的一致性锁定.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.build_localization_gold_template import (
    CANONICAL_DOC04_VIOLATIONS,
    DOC04_CONTENT_LIST,
    EXPECTED_QA_N,
    FROZEN_QA,
    SILVER_LABELS,
    TAXONOMY,
    build_template,
    build_violation_records,
    cohen_kappa,
    gold_claim_refs,
    inter_annotator_report,
    jaccard_ratio,
    localization_counts,
    normalize_refs,
    overlap_ratio,
    parse_block_refs,
    parse_gold_row,
    parse_gold_rows,
    read_jsonl,
    score_localization,
    span_char_f1,
    system_refs_from_row,
    validate_template_record,
    violation_evidence_index,
)


# ------------------------------------------------------------ 合成fixture工具

def gold_row(instance_id: str, verdict: str, refs: list[str],
             span: str = "", claim_verdict: str | None = None) -> dict:
    return {
        "schema": "s7_localization_gold_v1",
        "instance_id": instance_id,
        "task_type": "qa_verdict",
        "question": f"q-{instance_id}",
        "answer": f"a-{instance_id}",
        "gold_verdict": verdict,
        "claims": [{
            "claim_id": "c1",
            "claim_text": f"claim-{instance_id}",
            "claim_verdict": claim_verdict or verdict,
            "gold_evidence_refs": refs,
            "gold_span": span,
            "annotation_note": "",
        }],
    }


def system_row(instance_id: str, verdict: str, refs: list[str],
               span: str | None = None) -> dict:
    claim: dict = {
        "claim_id": "c1",
        "claim_text": f"claim-{instance_id}",
        "verdict": verdict,
        "evidence_refs": refs,
    }
    if span is not None:
        claim["span"] = span
    return {
        "instance_id": instance_id,
        "verdict": verdict,
        "evidence_refs": refs,
        "claims": [claim],
    }


# ------------------------------------------------------------ 纯函数: 定位集合

def test_normalize_refs_dedupe_and_strip() -> None:
    assert normalize_refs([" a ", "a", "b", "", None]) == ("a", "b")
    assert normalize_refs(None) == ()
    assert normalize_refs([]) == ()


def test_overlap_ratio_conventions() -> None:
    # gold非空: 覆盖率语义
    assert overlap_ratio(("a", "b", "c"), ("b", "c", "d")) == pytest.approx(2 / 3)
    assert overlap_ratio(("a",), ("a", "b", "c")) == 1.0     # 超集引用不扣分
    assert overlap_ratio(("a", "b"), ()) == 0.0              # 漏定位
    # gold为空(NIE无可定位证据): 系统也不引用=正确定位
    assert overlap_ratio((), ()) == 1.0
    assert overlap_ratio((), ("x",)) == 0.0                  # 无中生有的引用


def test_localization_counts() -> None:
    assert localization_counts(("a", "b"), ("b", "c")) == (1, 2, 2)
    assert localization_counts((), ()) == (0, 0, 0)


def test_jaccard_ratio_symmetry_and_empty() -> None:
    assert jaccard_ratio(("a", "b"), ("b", "c")) == pytest.approx(1 / 3)
    assert jaccard_ratio(("b", "c"), ("a", "b")) == pytest.approx(1 / 3)
    assert jaccard_ratio((), ()) == 1.0
    assert jaccard_ratio(("a",), ()) == 0.0


def test_system_refs_from_row_statement_suffix_normalized() -> None:
    row = {
        "instance_id": "X",
        "verdict": "support",
        "evidence_refs": ["ev-000043#s5", "ev-000043#s7", "ev-000049"],
    }
    assert system_refs_from_row(row) == ("ev-000043", "ev-000049")
    # 无行级refs时: 只取判定性claim(support/refute)的并集, NIE不取
    row2 = {
        "instance_id": "X",
        "verdict": "refute",
        "claims": [
            {"claim_id": "c1", "verdict": "refute",
             "evidence_refs": ["e1", "e2"]},
            {"claim_id": "c2", "verdict": "not_in_evidence",
             "evidence_refs": ["e3"]},
            {"claim_id": "c3", "verdict": "support",
             "evidence_refs": ["e2", "e4#s1"]},
        ],
    }
    assert system_refs_from_row(row2) == ("e1", "e2", "e4")


# ------------------------------------------------------------ 纯函数: span F1

def test_span_char_f1_hand_computed() -> None:
    # 完全一致→1.0; 空白不参与计数
    assert span_char_f1("系统提示连接失败", "系统提示连接失败") == 1.0
    assert span_char_f1("系统 提示", "系统提示") == 1.0
    # gold 8字符, pred 13字符, 公共8: P=8/13, R=1, F1=16/21
    value = span_char_f1("系统提示连接失败", "系统提示连接失败，用例结束")
    assert value == pytest.approx(16 / 21, abs=1e-9)
    # 部分重叠: gold="ABCDE", pred="CDEFG" 公共3: P=3/5, R=3/5, F1=0.6
    assert span_char_f1("ABCDE", "CDEFG") == pytest.approx(0.6)
    # 不相交/空
    assert span_char_f1("甲", "乙") == 0.0
    assert span_char_f1("", "abc") == 0.0
    assert span_char_f1("abc", "") == 0.0


# ------------------------------------------------------------ 纯函数: κ

def test_cohen_kappa_hand_computed() -> None:
    # 经典例: A=[a,a,b,b], B=[a,b,b,b]: po=0.75, pe=0.5, κ=0.5
    assert cohen_kappa(["a", "a", "b", "b"], ["a", "b", "b", "b"]) == pytest.approx(0.5)
    # 完全一致→1.0
    assert cohen_kappa(["x", "y", "z"], ["x", "y", "z"]) == 1.0
    # 双方同分布且完全一致(pe=1)→1.0
    assert cohen_kappa(["x", "x"], ["x", "x"]) == 1.0
    # 独立分布: po=1/4, pe=1/2 → κ=-0.5
    assert cohen_kappa(
        ["a", "a", "a", "b"], ["b", "a", "b", "a"]) == pytest.approx(-0.5)
    with pytest.raises(ValueError):
        cohen_kappa(["a"], ["a", "b"])
    with pytest.raises(ValueError):
        cohen_kappa([], [])


# ------------------------------------------------------------ 纯函数: gold解析

def test_parse_gold_row_validates_schema() -> None:
    row = gold_row("T1", "support", ["e1", "e2"])
    record = parse_gold_row(row)
    assert record.instance_id == "T1"
    assert gold_claim_refs(record) == ("e1", "e2")
    assert record.claims[0].claim_verdict == "support"

    with pytest.raises(ValueError, match="非法gold_verdict"):
        parse_gold_row(gold_row("T1", "maybe", []))
    with pytest.raises(ValueError, match="缺字段"):
        parse_gold_row({"instance_id": "T1"})
    with pytest.raises(ValueError, match="claims必须是非空列表"):
        parse_gold_row({**gold_row("T1", "support", []), "claims": []})
    with pytest.raises(ValueError, match="annotator_confidence"):
        parse_gold_row({**gold_row("T1", "support", []),
                        "annotator_confidence": 1.5})


def test_parse_gold_rows_rejects_duplicate_ids() -> None:
    rows = [gold_row("T1", "support", []), gold_row("T1", "refute", [])]
    with pytest.raises(ValueError, match="instance_id重复"):
        parse_gold_rows(rows)


# ------------------------------------------------------------ 评分内核fixture

def test_score_localization_hand_computed() -> None:
    gold = [
        gold_row("i1", "refute", ["e1", "e2"]),        # 判定对, overlap=1.0
        gold_row("i2", "support", ["e1", "e2", "e3", "e4"]),  # 判定对, overlap=0.5
        gold_row("i3", "support", ["e5"]),             # 判定错(系统refute), overlap=1.0
        gold_row("i4", "not_in_evidence", []),         # 判定对, 系统引用了块→overlap=0
    ]
    system = [
        system_row("i1", "refute", ["e1", "e2"]),
        system_row("i2", "support", ["e1", "e2", "e9"]),
        system_row("i3", "refute", ["e5"]),
        system_row("i4", "not_in_evidence", ["e7"]),
    ]
    metrics = score_localization(gold, system, threshold=0.5)
    assert metrics["n"] == 4
    assert metrics["verdict_accuracy"] == 0.75           # i1,i2,i4对
    # micro P: 交集2+2+1+0=5? i1:2, i2:2, i3:1, i4:0 → 5; sys总 2+3+1+1=7
    assert metrics["localization_intersection_total"] == 5
    assert metrics["localization_micro_precision"] == pytest.approx(5 / 7, abs=1e-4)
    # gold总: 2+4+1+0=7 → micro R=5/7
    assert metrics["localization_micro_recall"] == pytest.approx(5 / 7, abs=1e-4)
    # AVeriTeC(τ=0.5): i1(对∧1.0)✓, i2(对∧0.5)✓, i3(错)✗, i4(对∧0.0)✗ → 0.5
    assert metrics["averitec_score"] == 0.5
    assert metrics["averitec_by_threshold"]["tau_0.00"] == 0.75
    assert metrics["averitec_by_threshold"]["tau_0.75"] == 0.25
    assert metrics["averitec_by_threshold"]["tau_1.00"] == 0.25
    # 判定正确样本(i1,i2,i4)中定位达标率=2/3
    assert metrics["localization_pass_rate_given_verdict_correct"] == pytest.approx(2 / 3, abs=1e-4)
    assert metrics["n_verdict_correct"] == 3
    assert metrics["missing_system_ids"] == []
    assert metrics["unknown_system_ids"] == []
    # 分verdict报告
    assert metrics["by_gold_verdict"]["refute"]["n"] == 1
    assert metrics["by_gold_verdict"]["support"]["n"] == 2
    assert metrics["by_gold_verdict"]["not_in_evidence"]["n"] == 1


def test_score_localization_nie_correct_abstention_counts() -> None:
    """gold NIE且无定位 + 系统NIE且不引用 → 判定∧定位双对(AVeriTeC得分)."""
    gold = [gold_row("i1", "not_in_evidence", [])]
    system = [system_row("i1", "not_in_evidence", [])]
    metrics = score_localization(gold, system, threshold=0.5)
    assert metrics["averitec_score"] == 1.0
    assert metrics["localization_micro_precision"] is None  # sys侧无引用
    assert metrics["localization_micro_recall"] is None     # gold侧无定位


def test_score_localization_reports_unmatched_ids() -> None:
    gold = [gold_row("i1", "support", ["e1"]), gold_row("i2", "refute", ["e2"])]
    system = [system_row("i1", "support", ["e1"]),
              system_row("ghost", "support", ["e9"])]
    metrics = score_localization(gold, system)
    assert metrics["missing_system_ids"] == ["i2"]
    assert metrics["unknown_system_ids"] == ["ghost"]
    assert metrics["n"] == 1


def test_score_localization_span_metrics() -> None:
    gold = [gold_row("i1", "support", ["e1"], span="系统提示连接失败"),
            gold_row("i2", "support", ["e2"], span="被排除的span")]
    system = [system_row("i1", "support", ["e1"], span="系统提示连接失败，用例结束"),
              system_row("i2", "support", ["e2"], span="完全不同")]
    metrics = score_localization(gold, system)
    assert metrics["n_span_scored"] == 2
    # i1: 16/21≈0.7619; i2: 0 → 宏平均8/21
    assert metrics["span_f1_macro"] == pytest.approx(8 / 21, abs=1e-4)


def test_score_localization_invalid_system_verdict_raises() -> None:
    gold = [gold_row("i1", "support", [])]
    system = [{"instance_id": "i1", "verdict": "maybe", "claims": []}]
    with pytest.raises(ValueError, match="非法system verdict"):
        score_localization(gold, system)


def test_score_localization_no_match_raises() -> None:
    with pytest.raises(ValueError, match="无共同instance_id"):
        score_localization([gold_row("i1", "support", [])], [])


# ------------------------------------------------------------ IAA fixture

def test_inter_annotator_report_fixture() -> None:
    rows_a = [
        gold_row("i1", "refute", ["e1", "e2"], span="甲乙"),
        gold_row("i2", "support", ["e3"]),
        gold_row("i3", "not_in_evidence", []),          # A: 无定位
    ]
    rows_b = [
        gold_row("i1", "refute", ["e1", "e2"], span="甲乙"),  # 完全一致
        gold_row("i2", "refute", ["e3", "e4"]),         # verdict分歧, 定位部分一致
        gold_row("i3", "not_in_evidence", []),          # B: 无定位
    ]
    report = inter_annotator_report(rows_a, rows_b, threshold=0.5)
    assert report["n_common"] == 3
    # verdict: 2/3一致; κ: A三类各1/3, B=refute2/3+nie1/3 → pe=1/3, po=2/3 → κ=0.5
    assert report["verdict_raw_agreement"] == pytest.approx(2 / 3, abs=1e-3)
    assert report["verdict_kappa"] == pytest.approx(0.5, abs=1e-3)
    # 定位: 双方located=i1,i2; i1 Jaccard=1, i2: {e3}vs{e3,e4}=1/2 → 均值=0.75
    assert report["localization_kappa"] == 1.0
    assert report["n_both_located"] == 2
    assert report["localization_mean_jaccard"] == pytest.approx(0.75, abs=1e-3)
    assert report["localization_both_empty_refs"] == 1
    # span: 只有i1双方都标 → 一致率1.0
    assert report["n_span_compared"] == 1
    assert report["span_agreement_macro"] == 1.0


def test_inter_annotator_locatable_kappa_disagreement() -> None:
    rows_a = [gold_row("i1", "support", ["e1"]),
              gold_row("i2", "support", ["e2"])]
    rows_b = [gold_row("i1", "support", ["e1"]),
              gold_row("i2", "support", [])]  # B认为i2无定位(NIE倾向)
    report = inter_annotator_report(rows_a, rows_b)
    # located标签: A=[loc,loc], B=[loc,not_loc] → po=0.5, pe=0.5 → κ=0
    assert report["localization_kappa"] == pytest.approx(0.0)
    assert report["n_both_located"] == 1


# ------------------------------------------------------------ 模板生成(真实数据)

@pytest.fixture(scope="module")
def built_template(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out_dir = tmp_path_factory.mktemp("locgold")
    return build_template(
        template_path=out_dir / "annotation_template_v1.jsonl",
        system_path=out_dir / "system_output_v1.jsonl",
        meta_path=out_dir / "annotation_template_v1_metadata.json")


def test_build_template_real_data(built_template: dict) -> None:
    summary = built_template
    assert summary["n_qa"] == EXPECTED_QA_N == 91
    assert summary["n_violations"] == 17
    assert summary["n_total"] == 108
    # silver分布锁定(S=6/R=8/N=77)
    assert summary["silver_label_distribution"] == {
        "support": 6, "refute": 8, "not_in_evidence": 77}
    # canonical类别分布锁定
    assert summary["violation_category_distribution"] == {
        "identifier": 5, "enumeration": 4, "traceability": 3,
        "exception_template": 2, "document_name": 1,
        "function_coverage": 1, "qualification_coverage": 1}

    template = read_jsonl(Path(summary["template_path"]))
    system = read_jsonl(Path(summary["system_path"]))
    assert len(template) == 108
    assert len(system) == 91

    frozen = read_jsonl(FROZEN_QA)
    labels = read_jsonl(SILVER_LABELS)
    label_by_id = {row["instance_id"]: row for row in labels}
    problems: list[str] = []
    for record_row in template:
        record = parse_gold_row(record_row)
        problems.extend(validate_template_record(record))
        if record.task_type == "qa_verdict":
            frozen_row = next(r for r in frozen
                              if r["instance_id"] == record.instance_id)
            label_row = label_by_id[record.instance_id]
            # gold_verdict初值=silver final_verdict
            assert record.gold_verdict == label_row["final_verdict"]
            assert record.gold_verdict_init == label_row["final_verdict"]
            # silver claims初值 + gold定位留空
            assert len(record.claims) == len(label_row["claims"])
            for claim, silver in zip(record.claims, label_row["claims"]):
                assert claim.claim_verdict == silver["verdict"]
                assert claim.gold_evidence_refs == ()
                assert claim.gold_span == ""
                assert claim.gold_nie_consulted_refs == ()
            # evidence_index与冻结证据块一一对应(含SourceRef 6字段)
            assert [ev["evidence_id"] for ev in record.evidence_index] == \
                [ev["evidence_id"] for ev in frozen_row["evidence"]]
            for ev in record.evidence_index:
                assert set(ev["source_ref"]) == {
                    "doc_id", "section", "page", "block_id", "row_id",
                    "region_id"}
            # 系统预填=qa_module输出(判定性refs已归一到块级)
            prefill = record.system_prefill
            assert prefill is not None
            assert prefill["verdict"] in ("support", "refute",
                                          "not_in_evidence")
            for ref in prefill["evidence_refs"]:
                assert "#" not in ref
        else:
            assert record.task_type == "doc_violation"
            assert record.gold_verdict == "refute"
            assert record.question is None and record.answer is None
            # 违例位置预填gold定位且全部在evidence_index内
            refs = gold_claim_refs(record)
            assert refs
            known = {ev["evidence_id"] for ev in record.evidence_index}
            assert set(refs) <= known
            assert record.system_prefill is None
    assert not problems
    # 元数据lineage
    meta = json.loads(
        Path(summary["meta_path"]).read_text(encoding="utf-8"))
    assert meta["counts"] == {"qa": 91, "violations": 17, "total": 108}
    for key in ("frozen_qa", "silver_labels", "taxonomy",
                "doc04_content_list"):
        assert meta["inputs"][key]["sha256"]


def test_build_template_output_is_deterministic(built_template: dict,
                                                 tmp_path: Path) -> None:
    first = Path(built_template["template_path"]).read_bytes()
    build_template(
        template_path=tmp_path / "annotation_template_v1.jsonl",
        system_path=tmp_path / "system_output_v1.jsonl",
        meta_path=tmp_path / "annotation_template_v1_metadata.json")
    second = (tmp_path / "annotation_template_v1.jsonl").read_bytes()
    assert first == second


# ------------------------------------------------------------ canonical 17

def test_canonical_violations_table_integrity() -> None:
    assert len(CANONICAL_DOC04_VIOLATIONS) == 17
    ids = [v.violation_id for v in CANONICAL_DOC04_VIOLATIONS]
    assert len(set(ids)) == 17
    assert ids == [f"DOC04-VIO-{i:02d}" for i in range(1, 18)]
    categories: dict[str, int] = {}
    for violation in CANONICAL_DOC04_VIOLATIONS:
        categories[violation.category] = (
            categories.get(violation.category, 0) + 1)
        assert violation.blocks, f"{violation.violation_id}无块位置"
    assert categories == {
        "identifier": 5, "enumeration": 4, "traceability": 3,
        "exception_template": 2, "document_name": 1,
        "function_coverage": 1, "qualification_coverage": 1}


def test_canonical_violations_match_taxonomy_v3() -> None:
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    items = {item["id"]: item for item in taxonomy["items"]}
    # taxonomy声明的canonical计数必须锁定17
    assert taxonomy["doc04_summary"]["total_real_violations"] == 17
    n_matched = 0
    for violation in CANONICAL_DOC04_VIOLATIONS:
        if not violation.taxonomy_match:
            continue  # V15: taxonomy无记录(project_guide §2独有)
        n_matched += 1
        hits = [text for text in items[violation.item_id]["doc04_violations"]
                if violation.taxonomy_match in text]
        assert len(hits) == 1, (
            f"{violation.violation_id}: taxonomy_match须唯一定位")
        # taxonomy文本中的bXXX引用必须落在canonical块位置内
        parsed = set(parse_block_refs(hits[0]))
        assert parsed <= set(violation.blocks), (
            f"{violation.violation_id}: 文本引用{parsed}越出"
            f"{violation.blocks}")
    assert n_matched == 16  # 17中16条可在taxonomy定位, V15例外


def test_violation_evidence_snapshots_exist() -> None:
    blocks = json.loads(DOC04_CONTENT_LIST.read_text(encoding="utf-8"))
    assert len(blocks) == 411  # 04号解析块数(论文锁定数字)
    for violation in CANONICAL_DOC04_VIOLATIONS:
        evidence, refs = violation_evidence_index(violation, blocks)
        assert len(evidence) == len(violation.blocks)
        assert [ev["evidence_id"] for ev in evidence] == list(refs)
        for index, ev in zip(violation.blocks, evidence):
            assert ev["source_ref"]["block_id"] == f"block-{index:06d}"
            assert ev["text"].strip(), (
                f"{violation.violation_id}: b{index:03d}快照为空")
            assert ev["source_type"] in ("text", "table", "figure")


def test_build_violation_records_from_taxonomy() -> None:
    taxonomy = json.loads(TAXONOMY.read_text(encoding="utf-8"))
    blocks = json.loads(DOC04_CONTENT_LIST.read_text(encoding="utf-8"))
    records = build_violation_records(taxonomy, blocks)
    assert len(records) == 17
    v15 = next(r for r in records if r.instance_id == "DOC04-VIO-15")
    assert v15.taxonomy_ref is None
    assert "数据同步共享服务" in v15.claims[0].claim_text
    v17 = next(r for r in records if r.instance_id == "DOC04-VIO-17")
    assert v17.item_id == "GJB-01"
    assert v17.taxonomy_ref is not None
    for record in records:
        assert not validate_template_record(record)


def test_parse_block_refs_patterns() -> None:
    assert parse_block_refs("（b220/225）") == (220,)
    assert parse_block_refs("b192/222/227") == (192,)
    assert parse_block_refs("（b139 vs b140/145/150）") == (139, 140)
    assert parse_block_refs("无块引用") == ()
    assert parse_block_refs("b349/358两处") == (349,)
    # 4位数不被3位模式截断
    assert parse_block_refs("b1234") == ()
