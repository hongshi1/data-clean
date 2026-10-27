"""violation_evalset_v1(17真实违例转化集, 设计§6.5 real_observed)测试.

三层:
  1. 17条实例完整性(字段/证据数/verdict合法/gold定位⊆证据);
  2. 手工验证answer确实断言违例内容(≥3条, 逐条对照证据块原文);
  3. 评测内核能在小fixture上跑通(run_module+score_outcomes, 纯确定性
     配置, 无LLM/NLI依赖).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_violations import read_jsonl, run_module, score_outcomes  # noqa: E402

EVALSET = (BASE / "data/gjb_438c/localization_gold"
           / "violation_evalset_v1.jsonl")
TEMPLATE = (BASE / "data/gjb_438c/localization_gold"
            / "annotation_template_v1.jsonl")
VERDICTS = ("support", "refute", "not_in_evidence")

ROWS = read_jsonl(EVALSET)
BY_ID = {row["instance_id"]: row for row in ROWS}


def _evidence_text(row: dict, block_number: int) -> str:
    evidence_id = f"{row['instance_id']}-ev-{block_number:06d}"
    for item in row["evidence"]:
        if item["evidence_id"] == evidence_id:
            return str(item["text"])
    raise AssertionError(f"{row['instance_id']}: 证据{evidence_id}不存在")


# ------------------------------------------------------------ 完整性
def test_17_instances_schema_complete() -> None:
    assert len(ROWS) == 17
    assert len(BY_ID) == 17
    for row in ROWS:
        for field in ("instance_id", "question", "answer",
                      "expected_verdict", "answer_pattern",
                      "rationale_for_expectation", "violation_desc",
                      "violation_category", "item_id", "context_freeze_id",
                      "evidence", "gold_evidence_refs", "target_keywords"):
            assert row.get(field), f"{row['instance_id']}缺{field}"
        assert row["expected_verdict"] in VERDICTS
        assert 3 <= len(row["evidence"]) <= 8
        assert all(str(item["text"]).strip() for item in row["evidence"])
        ids = [item["evidence_id"] for item in row["evidence"]]
        assert len(set(ids)) == len(ids)
        for item in row["evidence"]:
            assert item["completeness"] == "open"
            assert item["source_ref"]["doc_id"]
            assert item["source_ref"]["block_id"].startswith("block-")
            assert item["evidence_id"].endswith(
                item["source_ref"]["block_id"].replace("block-", "ev-"))


def test_expected_verdicts_and_patterns() -> None:
    assert all(row["expected_verdict"] == "refute" for row in ROWS)
    patterns = [row["answer_pattern"] for row in ROWS]
    assert patterns.count("assert_violation_content") == 14
    assert patterns.count("assert_expected_content") == 3
    for row in ROWS:
        assert len(row["rationale_for_expectation"]) >= 60, (
            f"{row['instance_id']}期望verdict理由过短(效度基础)")


def test_gold_refs_covered_and_match_template() -> None:
    template = [json.loads(line) for line in
                TEMPLATE.read_text(encoding="utf-8").splitlines()
                if line.strip()]
    template_violations = {
        str(row["instance_id"]): row for row in template
        if str(row.get("instance_id", "")).startswith("DOC04-VIO-")}
    assert set(template_violations) == set(BY_ID)
    for row in ROWS:
        template_row = template_violations[row["instance_id"]]
        template_refs = sorted({
            ref for claim in template_row["claims"]
            for ref in claim["gold_evidence_refs"]})
        assert row["gold_evidence_refs"] == template_refs, (
            f"{row['instance_id']}gold定位与模板不一致")
        evidence_ids = {item["evidence_id"] for item in row["evidence"]}
        assert set(row["gold_evidence_refs"]) <= evidence_ids


# ------------------------------------------------------------ 手工验证
def test_vio01_answer_asserts_shared_id_violation() -> None:
    """VIO-01: answer断言两用例共用同ID(违例内容), 证据含冲突的表39登记."""
    row = BY_ID["DOC04-VIO-01"]
    assert "均为PZXQ-GN-LJCGL-LJCCSH" in row["answer"]
    title_config = _evidence_text(row, 220)
    title_init = _evidence_text(row, 225)
    capability = _evidence_text(row, 219)
    assert "PZXQ-GN-LJCGL-LJCCSH" in title_config
    assert "PZXQ-GN-LJCGL-LJCCSH" in title_init
    # 表39: 连接池配置的正确登记是LJCPZ, 连接池初始化才是LJCCSH
    assert "PZXQ-GN-LJCGL-LJCPZ" in capability
    assert "连接池配置" in capability


def test_vio10_answer_asserts_forward_side_against_reverse_table() -> None:
    """VIO-10: answer断言正向侧4.1.1 c), 逆向表写4.1.1 a)——正逆矛盾."""
    row = BY_ID["DOC04-VIO-10"]
    assert "4.1.1 c)" in row["answer"]
    forward = _evidence_text(row, 407).replace("）", ")")
    reverse = _evidence_text(row, 408).replace("）", ")")
    assert "4.1.1 c)" in forward and "3.2.4" in forward
    assert "4.1.1 a)" in reverse and "3.2.4" in reverse


def test_vio13_answer_asserts_defective_e1_content() -> None:
    """VIO-13特殊case: answer断言文档真实但有缺陷的E1内容(主题错位)."""
    row = BY_ID["DOC04-VIO-13"]
    assert "系统提示初始化" in row["answer"]
    use_case = _evidence_text(row, 192)
    assert "Use Case 名称：缓存更新" in use_case
    assert "异常流E1：系统提示初始化" in use_case


def test_vio15_answer_asserts_wrong_document_name() -> None:
    """VIO-15: answer断言误写文档名, 证据同时含正确名."""
    row = BY_ID["DOC04-VIO-15"]
    assert "数据同步共享服务" in row["answer"]
    wrong = _evidence_text(row, 348)
    correct = _evidence_text(row, 367)
    assert "数据同步共享服务" in wrong
    assert "数据统一访问服务" in correct
    assert "数据统一访问服务" not in wrong


def test_vio16_answer_asserts_claimed_but_missing_function() -> None:
    """VIO-16: answer断言声称存在但3.2/表2无对应的能力(功能声明缺失)."""
    row = BY_ID["DOC04-VIO-16"]
    assert "提供访问审计以及日志记录功能" in row["answer"]
    claim_source = _evidence_text(row, 11)
    capability = _evidence_text(row, 30)
    requirements = _evidence_text(row, 24)
    assert "访问审计以及日志记录" in claim_source
    for text in (capability, requirements):
        assert "审计" not in text, "3.2/表2出现审计字样则违例前提不成立"


# ------------------------------------------------------------ 评测内核
def test_eval_runner_on_small_fixture(tmp_path: Path) -> None:
    """小fixture(2条)跑通评测内核: 纯确定性配置, 无LLM/NLI依赖."""
    subset = [BY_ID["DOC04-VIO-13"], BY_ID["DOC04-VIO-16"]]
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in subset),
        encoding="utf-8")
    rows = read_jsonl(fixture)
    assert len(rows) == 2
    module = QAConsistencyModule(use_experts=True)
    outcomes = run_module(module, rows)
    assert set(outcomes) == {"DOC04-VIO-13", "DOC04-VIO-16"}
    for outcome in outcomes.values():
        assert outcome["verdict"] in VERDICTS
        assert isinstance(outcome["claims"], list)
        assert all("method" in claim for claim in outcome["claims"])
    score = score_outcomes(outcomes, rows)
    assert score["n"] == 2
    assert score["n_expected_refute"] == 2
    # 两条均为L1专家可检出违例(主题错位/GJB-04缺失), 确定性配置即refute
    assert score["n_detected"] == 2
    assert score["detection_rate"] == 1.0
    assert score["false_positives"] == 0
    assert score["refute_channels"]
    for detail in score["details"]:
        assert detail["gold_refs"]
        assert detail["localization_recall"] is not None


def test_block_ref_strips_statement_suffix() -> None:
    from tools.eval_violations import _block_ref
    assert _block_ref("X-ev-000222#s7") == "X-ev-000222"
    assert _block_ref("X-ev-000222") == "X-ev-000222"
