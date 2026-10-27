"""Tests for S7人工gold标注工作台 (build_annotation_sheet /
collect_gold_annotation / finalize_gold / eval --labels切换).

覆盖(任务4):
  1. 视图生成: 小fixture验证markdown/TSV字段完整 + 短编号解析 + 覆盖保护;
  2. 回收校验: happy path(超集字段/一致率) + 4类非法输入逐条报错 +
     partial/JSONL模式/结构错误;
  3. κ计算: 手工构造两份标注, 手算对照verdictκ/定位κ/Jaccard/span F1 +
     分歧清单;
  4. gold导出与--labels切换: is_gold/silver兼容字段 + 协议终检 +
     eval标签加载函数与CLI参数.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from tools.build_annotation_sheet import (  # noqa: E402
    INSTANCE_ROW_ID,
    TSV_COLUMNS,
    build_sheet,
    evidence_number,
    main as sheet_main,
    match_system_claim,
    parse_verdict_token,
    resolve_evidence_ref,
)
from tools.build_localization_gold_template import (  # noqa: E402
    read_jsonl,
    write_jsonl,
)
from tools.collect_gold_annotation import (  # noqa: E402
    check_claim_gold,
    collect,
    read_form_tsv,
    ref_tokens,
    span_matches_refs,
    validate_gold_row,
)
from tools.eval_qa_module_vs_silver import (  # noqa: E402
    LABELS,
    build_parser,
    label_verdict,
    load_labels,
)
from tools.finalize_gold import (  # noqa: E402
    disagreement_entries,
    export_row,
    run_export,
    run_kappa,
)


# ------------------------------------------------------------ 合成fixture
def make_evidence(evidence_id: str, text: str, source_type: str = "text"
                  ) -> dict:
    return {
        "evidence_id": evidence_id,
        "text": text,
        "source_type": source_type,
        "source_ref": {"doc_id": "doc-fixture", "section": "3.2.1",
                       "page": 1, "block_id": "block-fixture",
                       "row_id": "", "region_id": ""},
        "scope_id": "doc-fixture",
        "completeness": "open",
        "completeness_proof": "fixture",
    }


FX_EVIDENCE = [
    make_evidence("FX-001-ev-000001", "系统提示连接失败，用例结束。"),
    make_evidence("FX-001-ev-000002", "系统支持热插拔与双机热备两种连接方式。"),
    make_evidence(
        "FX-001-ev-000003",
        "<table><thead><tr><th>参数</th></tr></thead>"
        "<tbody><tr><td>连接超时</td></tr></tbody></table>",
        source_type="table"),
]

FX_SYSTEM_CLAIMS = [{
    "claim_id": "FX-001-sc01",
    "claim_text": "系统支持热插拔与双机热备两种连接方式。",
    "method": "fixture",
    "confidence": 0.9,
    "system_suggest_verdict": "support",
    "system_suggest_refs": ["FX-001-ev-000002"],
    "system_suggest_rationale": "fixture",
    "llm_suggest_span": "系统支持热插拔与双机热备两种连接方式。",
    "llm_suggest_span_verified": True,
}]


def make_qa_row() -> dict:
    return {
        "schema": "s7_localization_gold_v1",
        "instance_id": "FX-001",
        "task_type": "qa_verdict",
        "question": "系统支持哪些连接方式？",
        "answer": "系统支持热插拔与双机热备两种连接方式。",
        "gold_verdict": "not_in_evidence",
        "gold_verdict_init": "not_in_evidence",
        "gold_verdict_init_source": "fixture_silver",
        "annotation_status": "pending",
        "pre_annotation_status": "pre_annotated",
        "system_suggest_verdict": "not_in_evidence",
        "system_suggest_refs": [],
        "system_suggest_claims": FX_SYSTEM_CLAIMS,
        "claims": [
            {"claim_id": "c1",
             "claim_text": "系统在无法连接到服务端时提示连接错误。",
             "claim_verdict": "not_in_evidence",
             "gold_evidence_refs": [], "gold_span": "",
             "gold_nie_consulted_refs": [], "annotation_note": "",
             "silver_hint": {"verdict": "not_in_evidence",
                             "evidence_refs": [], "confidence": 0.9}},
            {"claim_id": "c2",
             "claim_text": "系统支持热插拔与双机热备两种连接方式。",
             "claim_verdict": "not_in_evidence",
             "gold_evidence_refs": [], "gold_span": "",
             "gold_nie_consulted_refs": [], "annotation_note": "",
             "silver_hint": {"verdict": "not_in_evidence",
                             "evidence_refs": [], "confidence": 0.9}},
        ],
        "annotator": None,
        "annotator_confidence": None,
        "round": 1,
        "category": "",
        "item_id": "",
        "taxonomy_ref": None,
        "violation_text": None,
        "context_freeze_id": "frozen-FX-001",
        "evidence_index": FX_EVIDENCE,
        "system_prefill": None,
    }


VIO_EVIDENCE = [
    make_evidence("DOC04-VIO-01-ev-000220",
                  "3.2.5.1 连接池管理-连接池配置（PZXQ-GN-LJCGL-LJCCSH）"),
    make_evidence("DOC04-VIO-01-ev-000225",
                  "3.2.5.2 连接池管理-连接池初始化（PZXQ-GN-LJCGL-LJCCSH）"),
]


def make_violation_row() -> dict:
    return {
        "schema": "s7_localization_gold_v1",
        "instance_id": "DOC04-VIO-01",
        "task_type": "doc_violation",
        "question": None,
        "answer": None,
        "gold_verdict": "refute",
        "gold_verdict_init": "refute",
        "gold_verdict_init_source": "fixture",
        "annotation_status": "pending",
        "pre_annotation_status": "skipped",
        "system_suggest_verdict": None,
        "system_suggest_refs": None,
        "system_suggest_claims": None,
        "claims": [{
            "claim_id": "c1",
            "claim_text": "连接池配置/初始化同ID PZXQ-GN-LJCGL-LJCCSH",
            "claim_verdict": "refute",
            "gold_evidence_refs": ["DOC04-VIO-01-ev-000220",
                                   "DOC04-VIO-01-ev-000225"],
            "gold_span": "",
            "gold_nie_consulted_refs": [],
            "annotation_note": "",
            "silver_hint": None,
        }],
        "annotator": None,
        "annotator_confidence": None,
        "round": 1,
        "category": "identifier",
        "item_id": "TERM-07",
        "taxonomy_ref": "knowledge/consistency_taxonomy_v3.json::fixture",
        "violation_text": "连接池配置/初始化同ID PZXQ-GN-LJCGL-LJCCSH",
        "context_freeze_id": None,
        "evidence_index": VIO_EVIDENCE,
        "system_prefill": None,
    }


def fixture_rows() -> list[dict]:
    return [make_qa_row(), make_violation_row()]


def write_fixture_pre(path: Path) -> Path:
    write_jsonl(path, fixture_rows())
    return path


def form_row(instance_id: str, claim_id: str, **gold: str) -> dict:
    row = {column: "" for column in TSV_COLUMNS}
    row["instance_id"] = instance_id
    row["claim_id"] = claim_id
    row.update(gold)
    return row


def write_form_tsv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(TSV_COLUMNS)
        for row in rows:
            writer.writerow([row.get(column, "") for column in TSV_COLUMNS])
    return path


def happy_form_rows() -> list[dict]:
    return [
        form_row("FX-001", INSTANCE_ROW_ID, gold_verdict="NIE"),
        form_row("FX-001", "c1", gold_verdict="nie"),
        form_row("FX-001", "c2", gold_verdict="support", gold_refs="2",
                 gold_span="系统支持热插拔与双机热备两种连接方式",
                 note="ev2整句支撑"),
        form_row("DOC04-VIO-01", INSTANCE_ROW_ID, gold_verdict="R"),
        form_row("DOC04-VIO-01", "c1", gold_verdict="refute",
                 gold_refs="220,225",
                 gold_span="3.2.5.1 连接池管理-连接池配置"
                 "（PZXQ-GN-LJCGL-LJCCSH）；3.2.5.2 连接池管理-连接池初始化"
                 "（PZXQ-GN-LJCGL-LJCCSH）"),
    ]


# ------------------------------------------------------------ 视图生成
def test_build_sheet_markdown_fields() -> None:
    doc = build_sheet(fixture_rows())
    markdown = doc.markdown
    assert "# 证据定位Gold标注工作台" in markdown
    assert "标注速查指南" in markdown
    assert "## FX-001 (silver=NIE, system=NIE)" in markdown
    assert "## DOC04-VIO-01 (silver=R, system=—" in markdown
    assert "系统在无法连接到服务端时提示连接错误。" in markdown
    assert "FX-001-ev-000001" in markdown
    assert "预填:220,225" in markdown
    assert "| ____ |" in markdown
    # claim表: silver/系统建议/LLM span建议三列均有内容
    assert "| c2 |" in markdown
    assert "S[2]" in markdown
    assert "系统支持热插拔与双机热备两种连接方式" in markdown
    stats = doc.stats
    assert stats["n_instances"] == 2
    assert stats["n_claims"] == 3
    assert stats["n_claim_system_matched"] == 1


def test_build_sheet_tsv_structure() -> None:
    doc = build_sheet(fixture_rows())
    table = list(csv.reader(io.StringIO(doc.tsv), delimiter="\t"))
    assert table[0] == list(TSV_COLUMNS)
    body = table[1:]
    assert len(body) == 5  # 2×INSTANCE + 3×claim行
    header_index = {name: i for i, name in enumerate(TSV_COLUMNS)}
    gold_columns = [header_index[column] for column in
                    ("gold_verdict", "gold_refs", "gold_nie_refs",
                     "gold_span", "note")]
    for row in body:
        assert all(row[column] == "" for column in gold_columns)
    instance_rows = [row for row in body
                     if row[header_index["claim_id"]] == INSTANCE_ROW_ID]
    assert [row[header_index["instance_id"]] for row in instance_rows] == [
        "FX-001", "DOC04-VIO-01"]
    fx_rows = [row for row in body
               if row[header_index["instance_id"]] == "FX-001"]
    for row in fx_rows:
        assert row[header_index["evidence_ids"]] == "1,2,3"
    c2 = [row for row in fx_rows
          if row[header_index["claim_id"]] == "c2"][0]
    assert c2[header_index["system_suggest"]] == "S[2]"
    assert c2[header_index["llm_span"]] == "系统支持热插拔与双机热备两种连接方式。"


def test_sheet_main_writes_files_and_guards_filled_tsv(
        tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    md_path = tmp_path / "sheet.md"
    tsv_path = tmp_path / "form.tsv"
    sheet_main(["--pre", str(pre), "--md", str(md_path), "--tsv", str(tsv_path)])
    assert md_path.exists() and tsv_path.exists()
    capsys.readouterr()
    # 模拟人工填写INSTANCE行后重跑: 拒绝覆盖
    rows = list(csv.reader(io.StringIO(tsv_path.read_text(encoding="utf-8")),
                           delimiter="\t"))
    rows[1][list(TSV_COLUMNS).index("gold_verdict")] = "NIE"
    with tsv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerows(rows)
    with pytest.raises(SystemExit, match="拒绝覆盖"):
        sheet_main(["--pre", str(pre), "--md", str(md_path),
                    "--tsv", str(tsv_path)])
    sheet_main(["--pre", str(pre), "--md", str(md_path),
                "--tsv", str(tsv_path), "--force"])
    fresh = list(csv.reader(io.StringIO(tsv_path.read_text(encoding="utf-8")),
                            delimiter="\t"))
    assert fresh[1][list(TSV_COLUMNS).index("gold_verdict")] == ""


# ------------------------------------------------------------ 纯函数内核
def test_parse_verdict_token() -> None:
    assert parse_verdict_token("support") == "support"
    assert parse_verdict_token(" S ") == "support"
    assert parse_verdict_token("R") == "refute"
    assert parse_verdict_token("nie") == "not_in_evidence"
    assert parse_verdict_token("支持") == "support"
    assert parse_verdict_token("反驳") == "refute"
    assert parse_verdict_token("无证据") == "not_in_evidence"
    assert parse_verdict_token("") is None
    assert parse_verdict_token(None) is None
    assert parse_verdict_token("maybe") is None


def test_evidence_number_and_resolve_ref() -> None:
    ids = ["FX-001-ev-000001", "FX-001-ev-000002", "FX-001-ev-000003"]
    assert evidence_number("FX-001-ev-000043") == "43"
    assert resolve_evidence_ref("FX-001-ev-000002", ids) == "FX-001-ev-000002"
    assert resolve_evidence_ref("2", ids) == "FX-001-ev-000002"
    assert resolve_evidence_ref("ev-000001", ids) == "FX-001-ev-000001"
    assert resolve_evidence_ref("ev3", ids) == "FX-001-ev-000003"
    assert resolve_evidence_ref("0002", ids) == "FX-001-ev-000002"
    assert resolve_evidence_ref("FX-001-ev-000001#s5", ids) == (
        "FX-001-ev-000001")
    assert resolve_evidence_ref("9", ids) is None
    assert resolve_evidence_ref("abc", ids) is None


def test_match_system_claim_threshold() -> None:
    matched, ratio = match_system_claim(
        "系统支持热插拔与双机热备两种连接方式。", FX_SYSTEM_CLAIMS)
    assert matched is not None and ratio == pytest.approx(1.0)
    matched, _ = match_system_claim("完全无关的声明。", FX_SYSTEM_CLAIMS)
    assert matched is None


def test_ref_tokens() -> None:
    assert ref_tokens(None) == []
    assert ref_tokens("43, 49；54") == ["43", "49", "54"]
    assert ref_tokens(["a", None, "b"]) == ["a", "b"]


def test_span_matches_refs_table_and_conflict_pair() -> None:
    texts = [FX_EVIDENCE[2]["text"], VIO_EVIDENCE[0]["text"],
             VIO_EVIDENCE[1]["text"]]
    # 表格块: 去标签行文本是合法span(协议§4.2)
    assert span_matches_refs("连接超时", [FX_EVIDENCE[2]["text"]])
    assert not span_matches_refs("连接超时", [FX_EVIDENCE[0]["text"]])
    # refute冲突对: ；分隔两段各命中一块
    assert span_matches_refs(
        VIO_EVIDENCE[0]["text"] + "；" + VIO_EVIDENCE[1]["text"],
        [VIO_EVIDENCE[0]["text"], VIO_EVIDENCE[1]["text"]])
    assert not span_matches_refs("不存在的句子", texts)
    assert not span_matches_refs("", texts)
    assert not span_matches_refs("任意", [])


# ------------------------------------------------------------ 回收校验
def test_collect_happy_path(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    tsv = write_form_tsv(tmp_path / "form.tsv", happy_form_rows())
    out = tmp_path / "gold_v1.jsonl"
    stats = collect(pre_path=pre, tsv_path=tsv, out_path=out,
                    annotator="测试员")
    assert stats["errors"] == []
    assert stats["progress"]["completed"] == 2
    assert stats["progress"]["total"] == 2
    gold_rows = read_jsonl(out)
    assert [row["instance_id"] for row in gold_rows] == [
        "FX-001", "DOC04-VIO-01"]
    qa = gold_rows[0]
    # silver标签文件的兼容超集: 外层字段名一致 + final_verdict可直接评测
    assert qa["status"] == "final_human_gold"
    assert qa["final_verdict"] == "not_in_evidence"
    assert qa["final_model"] == "human"
    assert qa["annotation_status"] == "completed"
    assert qa["annotator"] == "测试员"
    c1, c2 = qa["claims"]
    assert c1["claim_verdict"] == "not_in_evidence"
    assert c2["claim_verdict"] == "support"
    assert c2["verdict"] == "support"
    assert c2["evidence_refs"] == ["FX-001-ev-000002"]
    assert c2["gold_evidence_refs"] == ["FX-001-ev-000002"]
    assert c2["gold_span"] == "系统支持热插拔与双机热备两种连接方式"
    assert c2["annotation_note"] == "ev2整句支撑"
    violation = gold_rows[1]
    assert violation["final_verdict"] == "refute"
    assert violation["claims"][0]["gold_evidence_refs"] == [
        "DOC04-VIO-01-ev-000220", "DOC04-VIO-01-ev-000225"]
    # 一致率统计(预标注质量测量)
    assert stats["agreement"]["instance_vs_silver"] == {
        "n": 2, "hits": 2, "rate": 1.0}
    assert stats["agreement"]["instance_vs_system_suggest"] == {
        "n": 1, "hits": 1, "rate": 1.0}
    assert stats["agreement"]["claim_vs_silver"]["n"] == 3
    assert stats["agreement"]["claim_vs_silver"]["hits"] == 2
    assert stats["agreement"]["claim_vs_system_suggest"] == {
        "n": 1, "hits": 1, "rate": 1.0}
    assert (tmp_path / "gold_v1_stats.json").exists()


def _collect_single_error(tmp_path: Path, bad_rows: list[dict],
                          expected_message: str) -> dict:
    """单实例+单坏填法(坏填在c2行): 断言该实例被剔除且错误逐条可见."""
    rows = [make_qa_row()]
    pre = write_jsonl(tmp_path / "pre.jsonl", rows)
    filled = [
        form_row("FX-001", INSTANCE_ROW_ID, gold_verdict="NIE"),
        form_row("FX-001", "c1", gold_verdict="nie"),
    ] + bad_rows
    tsv = write_form_tsv(tmp_path / "form.tsv", filled)
    out = tmp_path / "gold_v1.jsonl"
    stats = collect(pre_path=pre, tsv_path=tsv, out_path=out)
    assert stats["progress"]["completed"] == 0
    assert stats["progress"]["error_excluded"] == ["FX-001"]
    assert not out.exists()
    assert any(expected_message in error for error in stats["errors"]), (
        stats["errors"])
    return stats


def test_collect_rejects_bad_verdict(tmp_path: Path) -> None:
    stats = _collect_single_error(
        tmp_path,
        [form_row("FX-001", "c2", gold_verdict="maybe", gold_refs="2")],
        "FX-001/c2: 非法gold_verdict 'maybe'")
    assert any("support/refute/not_in_evidence" in error
               for error in stats["errors"])


def test_collect_rejects_unknown_evidence_ref(tmp_path: Path) -> None:
    _collect_single_error(
        tmp_path,
        [form_row("FX-001", "c2", gold_verdict="support", gold_refs="9")],
        "FX-001/c2: 引用的evidence_id必须在实例的evidence列表中")


def test_collect_rejects_nie_with_refs(tmp_path: Path) -> None:
    _collect_single_error(
        tmp_path,
        [form_row("FX-001", "c2", gold_verdict="nie", gold_refs="2")],
        "NIE的gold_evidence_refs必须留空")


def test_collect_rejects_nonsubstring_span(tmp_path: Path) -> None:
    _collect_single_error(
        tmp_path,
        [form_row("FX-001", "c2", gold_verdict="support", gold_refs="2",
                  gold_span="这句根本不在证据块里")],
        "gold_span不是所引证据块文本的子串")


def test_collect_partial_and_instance_row_rules(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    filled = [
        form_row("FX-001", INSTANCE_ROW_ID, gold_verdict="NIE"),
        form_row("FX-001", "c1", gold_verdict="nie"),
        # 两实例都只填了部分verdict → partial(缺c2/缺c1)
        form_row("DOC04-VIO-01", INSTANCE_ROW_ID, gold_verdict="R",
                 note="实例行不应有note"),
    ]
    tsv = write_form_tsv(tmp_path / "form.tsv", filled)
    stats = collect(pre_path=pre, tsv_path=tsv,
                    out_path=tmp_path / "gold_v1.jsonl")
    assert stats["errors"] == []
    assert stats["progress"]["completed"] == 0
    assert stats["progress"]["partial"] == ["FX-001", "DOC04-VIO-01"]
    assert stats["progress"]["pending"] == 0
    assert stats["progress"]["partial_detail"] == [
        {"instance_id": "FX-001", "missing_verdict_cells": ["c2"]},
        {"instance_id": "DOC04-VIO-01", "missing_verdict_cells": ["c1"]}]
    assert any("INSTANCE行的note无对应字段" in warning
               for warning in stats["warnings"])


def test_collect_instance_row_with_refs_is_error(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    filled = [
        form_row("FX-001", INSTANCE_ROW_ID, gold_verdict="NIE",
                 gold_refs="2"),
        form_row("FX-001", "c1", gold_verdict="nie"),
        form_row("FX-001", "c2", gold_verdict="nie"),
    ]
    tsv = write_form_tsv(tmp_path / "form.tsv", filled)
    stats = collect(pre_path=pre, tsv_path=tsv,
                    out_path=tmp_path / "gold_v1.jsonl")
    assert any("INSTANCE行只填gold_verdict" in error
               for error in stats["errors"])
    assert stats["progress"]["completed"] == 0


def test_collect_structural_errors(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    filled = [
        form_row("FX-001", INSTANCE_ROW_ID, gold_verdict="NIE"),
        form_row("FX-001", "c1", gold_verdict="nie"),
        form_row("FX-001", "c2", gold_verdict="nie"),
        form_row("FX-001", "c9", gold_verdict="nie"),        # 未知claim_id
        form_row("FX-404", INSTANCE_ROW_ID, gold_verdict="NIE"),  # 未知实例
    ]
    tsv = write_form_tsv(tmp_path / "form.tsv", filled)
    stats = collect(pre_path=pre, tsv_path=tsv,
                    out_path=tmp_path / "gold_v1.jsonl")
    assert any("未知claim_id" in error for error in stats["errors"])
    assert any("未知instance_id: FX-404" in error
               for error in stats["errors"])
    # 结构错误逐条报错但不牵连无关实例: FX-001本身完整且零错误 → 照常回收
    assert stats["progress"]["completed"] == 1
    assert stats["progress"]["error_excluded"] == []
    # 表头缺列: 直接可读报错
    bad = tmp_path / "bad.tsv"
    bad.write_text("instance_id\tclaim_id\nFX-001\tc1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="TSV表头缺列"):
        read_form_tsv(bad)


def test_collect_jsonl_mode(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    filled = [make_qa_row(), make_violation_row()]
    for row in filled:
        row["annotation_status"] = "completed"
    qa = filled[0]
    qa["claims"][1]["claim_verdict"] = "support"
    qa["claims"][1]["gold_evidence_refs"] = ["FX-001-ev-000002"]
    source = write_jsonl(tmp_path / "filled.jsonl", filled)
    out = tmp_path / "gold_v1.jsonl"
    stats = collect(pre_path=pre, in_jsonl_path=source, out_path=out)
    assert stats["errors"] == []
    assert stats["progress"]["completed"] == 2
    assert read_jsonl(out)[0]["claims"][1]["verdict"] == "support"
    # annotation_status≠completed → pending不回收(不在标注输入中的实例同计pending)
    pending = [make_qa_row()]
    pending[0]["claims"][1]["claim_verdict"] = "support"
    source2 = write_jsonl(tmp_path / "pending.jsonl", pending)
    stats2 = collect(pre_path=write_fixture_pre(tmp_path / "pre2.jsonl"),
                     in_jsonl_path=source2, out_path=tmp_path / "g2.jsonl")
    assert stats2["progress"]["completed"] == 0
    assert stats2["progress"]["pending"] == 2


def test_collect_guards_paths(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    tsv = write_form_tsv(tmp_path / "form.tsv", happy_form_rows())
    with pytest.raises(ValueError, match="不得指向pre_annotated"):
        collect(pre_path=pre, tsv_path=tsv, out_path=pre)
    with pytest.raises(ValueError, match="必须且只能提供一个输入"):
        collect(pre_path=pre, tsv_path=tsv, in_jsonl_path=tsv,
                out_path=tmp_path / "out.jsonl")


def test_check_claim_gold_warning_cases() -> None:
    ids = ["FX-001-ev-000001", "FX-001-ev-000002"]
    texts = {"FX-001-ev-000002": FX_EVIDENCE[1]["text"]}
    check = check_claim_gold(
        "FX-001", "c1", "support", "", "", "", "", ids, texts)
    assert check.errors == ()
    assert check.warnings and "gold_refs为空" in check.warnings[0]
    check = check_claim_gold(
        "FX-001", "c1", "nie", "", "1", "", "", ids, texts)
    assert check.errors == ()
    assert check.nie_refs == ("FX-001-ev-000001",)


def test_validate_gold_row_rejects_inconsistent_compat_fields() -> None:
    row = make_qa_row()
    row["annotation_status"] = "completed"
    row["final_verdict"] = "refute"  # 与gold_verdict不一致
    errors = validate_gold_row(row)
    assert any("final_verdict" in error for error in errors)
    row2 = make_qa_row()
    row2["annotation_status"] = "completed"
    row2["claims"][1]["claim_verdict"] = "not_in_evidence"
    row2["claims"][1]["gold_evidence_refs"] = ["FX-001-ev-000001"]
    errors2 = validate_gold_row(row2)
    assert any("NIE的gold_evidence_refs必须留空" in error
               for error in errors2)


# ------------------------------------------------------------ κ与分歧清单
def gold_annotation_row(instance_id: str, verdict: str, refs: list[str],
                        span: str = "") -> dict:
    return {
        "schema": "s7_localization_gold_v1",
        "instance_id": instance_id,
        "task_type": "qa_verdict",
        "gold_verdict": verdict,
        "annotation_status": "completed",
        "claims": [{
            "claim_id": "c1",
            "claim_text": f"claim-{instance_id}",
            "claim_verdict": verdict,
            "gold_evidence_refs": refs,
            "gold_span": span,
            "annotation_note": "",
        }],
    }


def test_kappa_hand_computed(tmp_path: Path) -> None:
    """手算fixture: verdictκ=0.6, 定位κ=0.5, Jaccard均值=0.75, span F1=0.8.

    verdict: A=[s,r,nie,s], B=[s,r,r,s]: observed=3/4, expected=0.375
    → κ=(0.75-0.375)/0.625=0.6;
    refs: i1双方{e1,e2}(J=1), i2 A{e1}/B{e1,e3}(J=0.5), i3 A∅/B{e1},
    i4双方∅; loc标签A=[L,L,NL,NL](p=.5/.5), B=[L,L,L,NL](p=.75/.25)
    → expected=0.5, observed=0.75 → κ=0.5;
    span仅i1双方都填("甲乙" vs "甲乙丙") → char-F1=0.8.
    """
    rows_a = [
        gold_annotation_row("i1", "support", ["e1", "e2"], span="甲乙"),
        gold_annotation_row("i2", "refute", ["e1"]),
        gold_annotation_row("i3", "not_in_evidence", []),
        gold_annotation_row("i4", "support", []),
    ]
    rows_b = [
        gold_annotation_row("i1", "support", ["e1", "e2"], span="甲乙丙"),
        gold_annotation_row("i2", "refute", ["e1", "e3"]),
        gold_annotation_row("i3", "refute", ["e1"]),
        gold_annotation_row("i4", "support", []),
    ]
    path_a = write_jsonl(tmp_path / "a.jsonl", rows_a)
    path_b = write_jsonl(tmp_path / "b.jsonl", rows_b)
    report, entries, list_path = run_kappa(
        path_a, path_b, arbitration_path=tmp_path / "arb.json")
    assert report["n_common"] == 4
    assert report["verdict_kappa"] == pytest.approx(0.6)
    assert report["verdict_raw_agreement"] == pytest.approx(0.75)
    assert report["localization_kappa"] == pytest.approx(0.5)
    assert report["localization_mean_jaccard"] == pytest.approx(0.75)
    assert report["n_both_located"] == 2
    assert report["span_agreement_macro"] == pytest.approx(0.8)
    assert report["n_span_compared"] == 1
    # 分歧清单: i1(span), i2(refs), i3(verdict+refs); i4完全一致
    assert [entry["instance_id"] for entry in entries] == ["i1", "i2", "i3"]
    by_id = {entry["instance_id"]: entry for entry in entries}
    assert by_id["i1"]["diff_kinds"] == ["span"]
    assert by_id["i2"]["diff_kinds"] == ["refs"]
    assert by_id["i2"]["jaccard"] == pytest.approx(0.5)
    assert by_id["i3"]["diff_kinds"] == ["verdict", "refs"]
    assert by_id["i3"]["jaccard"] == pytest.approx(0.0)
    saved = json.loads(list_path.read_text(encoding="utf-8"))
    assert saved["n_disagreements"] == 3
    assert report["n_disagreements"] == 3


def test_disagreement_entries_only_common() -> None:
    rows_a = [gold_annotation_row("x", "support", ["e1"])]
    rows_b = [gold_annotation_row("x", "support", ["e1"]),
              gold_annotation_row("y", "refute", ["e2"])]
    entries = disagreement_entries(rows_a, rows_b)
    assert entries == []  # x完全一致; y只在B侧(κ报告的only_in_b负责)


# ------------------------------------------------------------ 导出与--labels
def test_run_export_and_eval_label_loading(tmp_path: Path) -> None:
    pre = write_fixture_pre(tmp_path / "pre.jsonl")
    tsv = write_form_tsv(tmp_path / "form.tsv", happy_form_rows())
    gold_path = tmp_path / "gold_v1.jsonl"
    collect(pre_path=pre, tsv_path=tsv, out_path=gold_path)
    out = tmp_path / "scene1_gold_v1.jsonl"
    summary = run_export(gold_path, out)
    assert summary["n_exported"] == 2
    assert summary["verdict_distribution"] == {
        "not_in_evidence": 1, "refute": 1}
    exported = read_jsonl(out)
    assert all(row["is_gold"] is True for row in exported)
    assert exported[0]["final_verdict"] == "not_in_evidence"
    assert exported[0]["claims"][1]["verdict"] == "support"
    assert exported[0]["claims"][1]["evidence_refs"] == ["FX-001-ev-000002"]
    # 评测工具标签加载(silver与gold同构: final_verdict)
    labels = load_labels(out)
    assert set(labels) == {"FX-001", "DOC04-VIO-01"}
    assert label_verdict(labels["FX-001"], "FX-001") == "not_in_evidence"
    assert label_verdict(labels["DOC04-VIO-01"], "DOC04-VIO-01") == "refute"


def test_run_export_rejects_invalid_gold(tmp_path: Path) -> None:
    row = make_qa_row()
    row["annotation_status"] = "completed"
    row["claims"][1]["claim_verdict"] = "not_in_evidence"
    row["claims"][1]["gold_evidence_refs"] = ["FX-001-ev-000001"]
    gold_path = write_jsonl(tmp_path / "bad_gold.jsonl", [row])
    with pytest.raises(ValueError, match="NIE的gold_evidence_refs必须留空"):
        run_export(gold_path, tmp_path / "out.jsonl")
    assert not (tmp_path / "out.jsonl").exists()
    # annotation_status≠completed → 拒绝导出
    row2 = make_qa_row()
    row2["claims"][1]["claim_verdict"] = "support"
    row2["claims"][1]["gold_evidence_refs"] = ["FX-001-ev-000002"]
    gold_path2 = write_jsonl(tmp_path / "pending_gold.jsonl", [row2])
    with pytest.raises(ValueError, match="completed"):
        run_export(gold_path2, tmp_path / "out2.jsonl")


def test_run_export_guards_paths(tmp_path: Path) -> None:
    row = make_qa_row()
    row["annotation_status"] = "completed"
    gold_path = write_jsonl(tmp_path / "gold.jsonl", [row])
    with pytest.raises(ValueError, match="不得与gold输入路径相同"):
        run_export(gold_path, gold_path)


def test_export_row_patches_silver_compat_fields() -> None:
    row = gold_annotation_row("z", "support", ["e1"], span="甲")
    exported = export_row(row)
    assert exported["is_gold"] is True
    assert exported["final_verdict"] == "support"
    assert exported["final_model"] == "human"
    assert exported["status"] == "final_human_gold"
    assert exported["claims"][0]["verdict"] == "support"
    assert exported["claims"][0]["evidence_refs"] == ["e1"]
    # 已有值不被覆盖(setdefault语义)
    row2 = dict(row, final_verdict="support", final_model="human-B")
    exported2 = export_row(row2)
    assert exported2["final_model"] == "human-B"


def test_eval_label_verdict_and_missing() -> None:
    assert label_verdict({"final_verdict": "refute"}, "X") == "refute"
    assert label_verdict({"gold_verdict": "support"}, "X") == "support"
    with pytest.raises(ValueError, match="X.*verdict非法"):
        label_verdict({"final_verdict": "unknown"}, "X")
    with pytest.raises(ValueError, match="verdict非法"):
        label_verdict({}, "X")


def test_eval_build_parser_labels_switch() -> None:
    parser = build_parser()
    assert parser.parse_args([]).labels == "silver"   # 默认silver不变
    assert parser.parse_args(["--labels", "gold"]).labels == "gold"
    with pytest.raises(SystemExit):
        parser.parse_args(["--labels", "bronze"])


def test_load_labels_rejects_duplicates_and_missing_id(
        tmp_path: Path) -> None:
    duplicate = write_jsonl(tmp_path / "dup.jsonl", [
        {"instance_id": "a", "final_verdict": "support"},
        {"instance_id": "a", "final_verdict": "refute"}])
    with pytest.raises(ValueError, match="instance_id重复"):
        load_labels(duplicate)
    missing = write_jsonl(tmp_path / "missing.jsonl",
                          [{"final_verdict": "support"}])
    with pytest.raises(ValueError, match="缺instance_id"):
        load_labels(missing)


def test_load_labels_real_silver_file() -> None:
    """真实silver标签文件与load_labels兼容(评测回归的根基)."""
    if not LABELS.exists():
        pytest.skip("silver标签文件不存在")
    labels = load_labels(LABELS)
    assert len(labels) == 91
    assert all(label_verdict(row, iid) in
               ("support", "refute", "not_in_evidence")
               for iid, row in labels.items())
