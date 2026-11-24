"""Tests for tools/eval_span_faithfulness.py (99号Phase 0-E1, ALCE口径).

三层:
  1. 纯函数: citation P/R数学(完美/部分/空), answer侧字面忠实四态,
     ev-N解析, 锚点重叠, 汇总聚合(macro/micro分母口径);
  2. 数据契约: 17条gold_evidence_refs⊆证据id且非空, GOLD_ROOT_CAUSE
     全覆盖17实例;
  3. 集成: 确定性module(use_experts=True)跑DOC04-VIO-01 → 逐实例
     快照(verdict/cited块集/precision=0.5/recall=1.0/根因any-hit,
     citation块与eval_violations同口径可交叉核对).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_root_cause import GOLD_ROOT_CAUSE  # noqa: E402
from tools.eval_span_faithfulness import (  # noqa: E402
    aggregate_details,
    anchor_overlap,
    answer_side_check,
    block_ref,
    citation_pr,
    evaluate_instance_expert,
    evaluate_instance_student,
    expert_literal_checks,
    no_citation_pr,
    parse_ev_index,
    student_literal_checks,
)

EVALSET = (BASE / "data/gjb_438c/localization_gold"
           / "violation_evalset_v1.jsonl")
ROWS = read_jsonl(EVALSET)


# ------------------------------------------------------------ 纯函数: 引用


def test_block_ref_strips_statement_suffix() -> None:
    assert block_ref("DOC04-VIO-01-ev-000222#s7") == \
        "DOC04-VIO-01-ev-000222"
    assert block_ref("DOC04-VIO-01-ev-000222") == \
        "DOC04-VIO-01-ev-000222"


def test_parse_ev_index() -> None:
    assert parse_ev_index("ev-1", 5) == 0
    assert parse_ev_index("ev-5", 5) == 4
    assert parse_ev_index("ev-6", 5) is None       # 越界
    assert parse_ev_index("ev-0", 5) is None       # 1-based下界
    assert parse_ev_index("ev-x", 5) is None       # 非数字
    assert parse_ev_index("block-2", 5) is None    # 非ev前缀
    assert parse_ev_index("ev-01", 5) == 0         # 前导零容忍


def test_citation_pr_perfect_partial_and_empty() -> None:
    gold = {"b1", "b2", "b3"}
    perfect = citation_pr({"b1", "b2"}, gold)
    assert perfect["precision"] == 1.0
    assert perfect["recall"] == round(2 / 3, 4)
    assert perfect["hit_blocks"] == ["b1", "b2"]
    assert perfect["missed_gold_blocks"] == ["b3"]
    partial = citation_pr({"b2", "b9"}, gold)
    assert partial["precision"] == 0.5
    assert partial["recall"] == round(1 / 3, 4)
    assert partial["missed_gold_blocks"] == ["b1", "b3"]
    empty = citation_pr(set(), gold)
    assert empty["precision"] is None  # 无cited: 不给假0
    assert empty["recall"] == 0.0
    no_gold = citation_pr({"b1"}, set())
    assert no_gold["recall"] is None
    assert no_gold["precision"] == 0.0  # gold空: 无可命中, 空集交


def test_no_citation_pr_records_missed_gold() -> None:
    pr = no_citation_pr({"g1", "g2"})
    assert pr["precision"] is None
    assert pr["recall"] == 0.0
    assert pr["missed_gold_blocks"] == ["g1", "g2"]
    assert pr["n_gold"] == 2


# ------------------------------------------------------------ 纯函数: 字面


def test_answer_side_check_two_orthogonal_facts() -> None:
    answer = "参数为100ms且不低于10ms"
    exact = answer_side_check((0, 3), "参数为", answer)
    assert exact == {"status": "span_exact", "quote_in_answer": True,
                     "span_exact": True}
    # 区间错但文本在(学生路径典型形态: quote逐字, span偏移错)
    inexact = answer_side_check((0, 3), "100ms", answer)
    assert inexact["status"] == "span_inexact_text_found"
    assert inexact["quote_in_answer"] is True
    assert inexact["span_exact"] is False
    # 无span但文本在(expert e1/trace通道claim_text可寻的降级形态)
    missing = answer_side_check(None, "100ms", answer)
    assert missing["status"] == "span_missing_text_found"
    assert missing["quote_in_answer"] is True
    assert missing["span_exact"] is False
    # 文本不在answer(合成claim_text类通道): 字面不忠实的本体
    absent = answer_side_check(None, "200ms", answer)
    assert absent["status"] == "text_absent"
    assert absent["quote_in_answer"] is False
    absent_span = answer_side_check((0, 3), "参数不", answer)
    assert absent_span["status"] == "text_absent"
    assert absent_span["quote_in_answer"] is False
    # student的span是list(模型输出), 同口径
    assert answer_side_check([3, 8], "100ms", answer)["span_exact"] is True
    # span非二元组(None以外): 视为无span, 文本检查兜底
    assert answer_side_check([1], "100ms", answer)["status"] == \
        "span_missing_text_found"


def test_student_literal_checks() -> None:
    answer = "支持桌面、平板、手持三种终端"
    ok = student_literal_checks(
        {"quote": "平板", "span": [5, 7], "evidence_ref": "ev-2"},
        answer, 3)
    assert ok["answer_side"] == "span_exact"
    assert ok["span_exact"] is True
    assert ok["evidence_ref_ok"] is True
    assert ok["evidence_index"] == 1
    assert ok["literal_faithful"] is True
    # quote逐字但span区间错: 字面忠实成立, copy精度失败(分开计量)
    inexact = student_literal_checks(
        {"quote": "平板", "span": [6, 8], "evidence_ref": "ev-2"},
        answer, 3)
    assert inexact["answer_side"] == "span_inexact_text_found"
    assert inexact["quote_in_answer"] is True
    assert inexact["span_exact"] is False
    assert inexact["literal_faithful"] is True
    bad_ref = student_literal_checks(
        {"quote": "平板", "span": [5, 7], "evidence_ref": "ev-9"},
        answer, 3)
    assert bad_ref["evidence_index"] is None
    assert bad_ref["literal_faithful"] is False
    bad_quote = student_literal_checks(
        {"quote": "不存在的原文", "span": None, "evidence_ref": "ev-1"},
        answer, 3)
    assert bad_quote["answer_side"] == "text_absent"
    assert bad_quote["literal_faithful"] is False


def test_expert_literal_checks_on_synthetic_localization() -> None:
    from algorithms.consistency.qa_models import EvidenceLocalization

    answer = "标识符为PZXQ-GN-01"
    loc = SimpleNamespace(
        claim_id="c1", method="id_join_registry",
        claim_text="PZXQ-GN-01", answer_span=(4, 14),
        evidence=(EvidenceLocalization(
            evidence_id="ev-1", statement_id="ev-1#s3",
            statement_text="xx", field_name="", row_index=0,
            block_id="block-1", section="3.2"),))
    ok = expert_literal_checks(
        loc, answer, {"ev-1"}, {"ev-1#s3"})
    assert ok["answer_side"] == "span_exact"
    assert ok["span_exact"] is True
    assert ok["literal_faithful"] is True
    # 合成claim_text通道(e1/trace): claim_text非answer逐字→text_absent
    synthesized = SimpleNamespace(
        claim_id="c2", method="e1_template_match",
        claim_text="断言该用例E1内容与主题错位", answer_span=None,
        evidence=(EvidenceLocalization(
            evidence_id="ev-2", statement_id="ev-2",
            statement_text="xx", field_name="", row_index=-1,
            block_id="block-2", section="3.2"),))
    synth = expert_literal_checks(
        synthesized, answer, {"ev-2"}, set())
    assert synth["answer_side"] == "text_absent"
    assert synth["quote_in_answer"] is False
    assert synth["literal_faithful"] is False
    # 语句id不在语句集(语句级ref悬空) → 不忠实
    dangling = expert_literal_checks(
        loc, answer, {"ev-1"}, {"ev-1#s0"})
    assert dangling["evidence_refs_ok"] is False
    assert dangling["literal_faithful"] is False
    # 块id不在输入证据(块级ref幻觉) → 不忠实
    phantom = expert_literal_checks(
        loc, answer, {"ev-2"}, {"ev-1#s3"})
    assert phantom["evidence_refs"][0]["block_exists"] is False
    assert phantom["literal_faithful"] is False


def test_anchor_overlap_counts_cited_blocks_with_keyword() -> None:
    texts = {"b1": "登记为PZXQ-GN-LJCCSH", "b2": "无关文本", "b3": "见LJCPZ"}
    overlap = anchor_overlap({"b1", "b2", "b3"}, texts,
                             ["LJCCSH", "LJCPZ"])
    assert overlap["n_cited"] == 3
    assert overlap["n_cited_with_keyword"] == 2
    assert overlap["cited_with_keyword"] == ["b1", "b3"]
    empty = anchor_overlap({"b1"}, texts, [])
    assert empty["n_cited_with_keyword"] == 0


# ------------------------------------------------------------ 纯函数: 汇总


def _detail(instance_id: str, detected: bool, precision: float | None,
            recall: float | None, n_cited: int, n_gold: int,
            category: str = "identifier",
            op_hit: bool = True) -> dict:
    return {
        "instance_id": instance_id,
        "path": "expert",
        "violation_category": category,
        "detected": detected,
        "citation": {"n_cited": n_cited, "n_gold": n_gold,
                     "n_hit": 0, "precision": precision, "recall": recall,
                     "cited_blocks": [], "hit_blocks": [],
                     "missed_gold_blocks": []},
        "anchor_overlap": {"n_cited": n_cited,
                           "n_cited_with_keyword": 0},
        "literal": {"n_localizations": 2 if detected else 0,
                    "n_issues": 2 if detected else 0,
                    "n_answer_faithful": 1 if detected else 0,
                    "n_refs_ok": 2 if detected else 0,
                    "n_literal_faithful": 1 if detected else 0,
                    "answer_side_states": []},
        "root_cause": {"predicted_operations": ["value_substitution"],
                       "operation_any_hit": op_hit},
    }


def test_aggregate_macro_micro_denominators() -> None:
    details = [
        _detail("i1", True, 1.0, 1.0, 4, 4),
        _detail("i2", True, 0.5, 0.5, 4, 4),
        _detail("i3", True, None, 0.0, 0, 4, op_hit=False),
        _detail("i4", False, None, 0.0, 0, 4, "enumeration"),
    ]
    summary = aggregate_details(details, "localization")
    assert summary["n_detected"] == 3
    citation = summary["citation"]
    # macroP分母=有cited的refute实例(i1,i2): (1.0+0.5)/2
    assert citation["macro_precision"] == 0.75
    # macroR(detected)= (1.0+0.5+0.0)/3
    assert citation["macro_recall_detected"] == round(1.5 / 3, 4)
    # macroR(all) = (1.0+0.5+0.0+0.0)/4
    assert citation["macro_recall_all"] == round(1.5 / 4, 4)
    # micro: 块池化(仅detected) cited=8, gold=12, hit=0(合成占位)
    assert citation["micro_counts"] == {"cited_blocks": 8,
                                        "gold_blocks": 12, "hit_blocks": 0}
    assert citation["micro_precision"] == 0.0
    assert citation["micro_recall"] == 0.0
    assert summary["undetected_ids"] == ["i4"]
    # 根因: expert路径无rule_id → 非适用键为None
    assert summary["root_cause"]["operation_any_hit_fraction"] == "2/3"
    assert summary["root_cause"]["rule_id_any_hit"] is None
    assert summary["by_category"]["enumeration"]["n"] == 1
    assert summary["by_category"]["enumeration"]["n_rule_id_any_hit"] is None


def test_aggregate_student_path_uses_issue_unit_and_rule_id() -> None:
    details = [
        _detail("i1", True, 1.0, 1.0, 2, 2, "traceability"),
    ]
    for detail in details:
        detail["root_cause"] = {"predicted_rule_ids": ["GJB-05"],
                                "rule_id_any_hit": True}
    summary = aggregate_details(details, "issue")
    assert summary["literal"]["unit"] == "issue"
    assert summary["literal"]["n_units"] == 2
    assert summary["root_cause"]["rule_id_any_hit_fraction"] == "1/1"
    assert summary["root_cause"]["operation_any_hit"] is None
    assert summary["by_category"]["traceability"]["n_rule_id_any_hit"] == 1


# ------------------------------------------------------------ 数据契约


def test_gold_anchor_fields_complete_on_17() -> None:
    assert len(ROWS) == 17
    for row in ROWS:
        ids = {str(item["evidence_id"]) for item in row["evidence"]}
        gold = {str(ref) for ref in row["gold_evidence_refs"]}
        assert gold, f"{row['instance_id']}缺gold_evidence_refs"
        assert gold <= ids, \
            f"{row['instance_id']}gold定位超出证据集: {sorted(gold - ids)}"
        assert row["target_keywords"], \
            f"{row['instance_id']}缺target_keywords"


def test_gold_root_cause_covers_all_instances() -> None:
    ids = {row["instance_id"] for row in ROWS}
    assert set(GOLD_ROOT_CAUSE) == ids
    for cause in GOLD_ROOT_CAUSE.values():
        assert cause["source"] in ("answer", "document_internal",
                                   "document_gap", "recall_insufficient")
        assert cause["operation"]


# ------------------------------------------------------------ 集成快照


def test_expert_eval_on_vio01_deterministic_snapshot() -> None:
    """DOC04-VIO-01: refute, 4 cited块(2命中gold), P=0.5 R=1.0,
    根因any-hit; 字面忠实修复(E1弱点#1)后e1d01定位claim_text锚定
    answer逐字引用(用例名/提示文本最小覆盖span)→两条定位均span_exact
    (修复前e1定位为合成断言text_absent, 13/23=0.5652的损失成分)."""
    row = ROWS[0]
    assert row["instance_id"] == "DOC04-VIO-01"
    module = QAConsistencyModule(use_experts=True)
    detail = evaluate_instance_expert(row, module.verify(
        build_qa_input(row)))
    assert detail["predicted_verdict"] == "refute"
    assert detail["detected"] is True
    assert detail["citation"]["cited_blocks"] == [
        "DOC04-VIO-01-ev-000219", "DOC04-VIO-01-ev-000220",
        "DOC04-VIO-01-ev-000222", "DOC04-VIO-01-ev-000225"]
    assert detail["citation"]["n_cited"] == 4
    assert detail["citation"]["n_gold"] == 2
    assert detail["citation"]["n_hit"] == 2
    assert detail["citation"]["precision"] == 0.5
    assert detail["citation"]["recall"] == 1.0
    assert detail["root_cause"]["gold"]["operation"] == \
        "dual_registration"
    assert "dual_registration" in detail["root_cause"][
        "predicted_operations"]
    assert detail["root_cause"]["operation_any_hit"] is True
    # 字面忠实(修复后): id_join定位span精确; e1d01定位claim_text=
    # answer[0:14]『连接池配置用例和连接池初始化』逐字引用→span_exact
    assert detail["literal"]["n_localizations"] == 2
    assert detail["literal"]["answer_side_states"] == \
        ["span_exact", "span_exact"]
    assert detail["literal"]["n_answer_faithful"] == 2
    assert detail["literal"]["n_span_exact"] == 2
    assert detail["literal"]["n_literal_faithful"] == 2
    assert detail["literal"]["n_refs_ok"] == 2
    # 锚点重叠: 4个cited块中3个含target_keywords(LJCCSH/LJCPZ)
    assert detail["anchor_overlap"]["n_cited_with_keyword"] == 3
    # 确定性: 复跑同结果(真实推理可复现)
    again = evaluate_instance_expert(row, module.verify(
        build_qa_input(row)))
    assert again["citation"] == detail["citation"]
    assert again["root_cause"] == detail["root_cause"]


def test_student_eval_synthetic_issue_mapping() -> None:
    """student路径: ev-N→块id映射, quote/span/rule_id三检查(合成数据).

    instance_id用真实ID(根因gold锚GOLD_ROOT_CAUSE按实例id索引)."""
    row = {
        "instance_id": "DOC04-VIO-01",
        "violation_category": "identifier",
        "item_id": "TERM-07",
        "expected_verdict": "refute",
        "answer": "标识符为PZXQ-GN-01",
        "evidence": [
            {"evidence_id": "ev-1", "text": "t1"},
            {"evidence_id": "ev-2", "text": "t2"},
        ],
        "gold_evidence_refs": ["ev-2"],
        "target_keywords": ["PZXQ"],
    }
    issues = [{"quote": "PZXQ-GN-01", "span": [4, 14],
               "rule_id": "TERM-07", "evidence_ref": "ev-2"}]
    detail = evaluate_instance_student(row, "refute", issues)
    assert detail["detected"] is True
    assert detail["citation"]["cited_blocks"] == ["ev-2"]
    assert detail["citation"]["precision"] == 1.0
    assert detail["citation"]["recall"] == 1.0
    assert detail["literal"]["n_literal_faithful"] == 1
    assert detail["root_cause"]["rule_id_any_hit"] is True
    # rule_id错→any-hit False
    wrong = evaluate_instance_student(
        row, "refute", [dict(issues[0], rule_id="TERM-03")])
    assert wrong["root_cause"]["rule_id_any_hit"] is False
    # 非refute: 无violations可评, recall=0(该引未引)
    undetected = evaluate_instance_student(row, "not_in_evidence", [])
    assert undetected["citation"]["precision"] is None
    assert undetected["citation"]["recall"] == 0.0
