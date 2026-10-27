"""mutation_injection_evalset_v1(变异注入漏检率矩阵, 设计§6.5 robustness)测试.

三层:
  1. 注入集构建: 小fixture(5 QA)验证两级算子执行/变异有效性守卫(恒等
     变异跳过并计数)/support对照排除/去重/字段完整;
  2. 评测逻辑: stub系统输出(mock verify)验证族级矩阵/算子级全表/
     漏检原因统计/漏检抽样/能力缺口计算正确;
  3. 真实evalset(存在时): schema/守卫/算子注册表一致性.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    VerificationResult,
)
from tools.build_mutation_injection_eval import (  # noqa: E402
    FAMILIES,
    OPERATORS,
    OPERATORS_BY_ID,
    build_injections,
)
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.eval_mutation_detection import (  # noqa: E402
    capability_gaps,
    family_matrix,
    load_rows,
    miss_reason_stats,
    operator_table,
    run_module,
    sample_misses,
)

EVALSET = BASE / "data/gjb_438c/mutation_injection_evalset_v1.jsonl"
REQUIRED_FIELDS = (
    "instance_id", "source_instance_id", "operator_name", "operator_family",
    "check_item", "mode", "question", "answer", "mutated_answer",
    "original_answer", "expected_verdict", "mutation_rationale",
    "context_freeze_id", "evidence",
)
SUPPORT_CONTROL_OPS = {
    op.operator_id for op in OPERATORS if not op.refute_semantics}


def _ev(evidence_id: str, text: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "text": text,
        "source_type": "text",
        "source_ref": {"doc_id": "fixture-doc", "section": "3.2",
                       "page": 1, "block_id": f"block-{evidence_id[-4:]}",
                       "row_id": "", "region_id": ""},
        "scope_id": f"fixture-doc:{evidence_id}",
        "completeness": "open",
        "completeness_proof": "fixture: open scope, no exhaustiveness claim.",
        "extraction_method": "fixture",
        "extraction_confidence": 1.0,
    }


def _qa_row(instance_id: str, question: str, answer: str,
            evidences: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "instance_id": instance_id,
        "question": question,
        "answer": answer,
        "context_freeze_id": "fixture-frozen-v1",
        "evidence": [_ev(eid, text) for eid, text in evidences],
    }


FIXTURE_ROWS = [
    # 标识符冲突 + 枚举删元(grounded成员) + 枚举注入
    _qa_row(
        "FX-QA-001",
        "数据库操作功能包括哪些功能？用例的项目唯一标识符是什么？",
        "数据库操作功能包括数据库初始化、数据库连接、数据库关闭三项功能，"
        "用例的项目唯一标识符为PZXQ-GN-SJKCZ-SJKCSH。",
        [("FX-QA-001-ev-0001",
          "数据库操作功能包括：数据库初始化、数据库连接、数据库关闭。"),
         ("FX-QA-001-ev-0002",
          "数据库初始化用例的项目唯一标识符为PZXQ-GN-SJKCZ-SJKCSH；"
          "数据库连接用例的项目唯一标识符为PZXQ-GN-SJKCZ-SJKLJ。")]),
    # 数值变异(BASE NUM-EQ / PARAM-06 / PARAM-01)
    _qa_row(
        "FX-QA-002",
        "数据查询的时间限制是多少？",
        "数据查询的时间限制为1秒。",
        [("FX-QA-002-ev-0001", "查询数据的时间限制为1秒。")]),
    # E1结果错配 + 时序倒置
    _qa_row(
        "FX-QA-003",
        "获取错误信息时系统如何处理？",
        "当获取错误信息发生异常时，系统先检测连接，然后提示错误信息并"
        "执行异常流E1：系统提示初始化。",
        [("FX-QA-003-ev-0001",
          "获取错误信息用例异常流E1：系统提示错误。"
          "查询数据用例异常流E1：系统提示初始化。")]),
    # 数值恒等(support对照): 触发变异有效性守卫(同answer跳过并计数)
    _qa_row(
        "FX-QA-004",
        "系统响应时间要求是多少？",
        "系统响应时间为100ms。",
        [("FX-QA-004-ev-0001", "系统响应时间为100ms。")]),
    # GJB域外术语注入(输入校验域)
    _qa_row(
        "FX-QA-005",
        "系统输入校验包括哪些校验类型？",
        "系统输入校验包括格式校验、范围校验两类。",
        [("FX-QA-005-ev-0001", "输入校验包括格式校验、范围校验。")]),
]


# ------------------------------------------------------------ 注入集构建
def test_build_injections_fixture_schema_and_guards() -> None:
    requests = [request_from_dict(row) for row in FIXTURE_ROWS]
    instances, report = build_injections(requests)

    assert instances, "fixture应产出注入实例"
    seen: set[tuple[str, str, str]] = set()
    for row in instances:
        for field in REQUIRED_FIELDS:
            assert row.get(field) is not None, f"{row['instance_id']}缺{field}"
            if field not in ("evidence",):
                assert str(row[field]).strip(), f"{row['instance_id']}空{field}"
        assert row["expected_verdict"] == "refute"
        assert row["mutated_answer"] == row["answer"]
        assert row["mutated_answer"] != row["original_answer"]  # 有效性守卫
        assert row["operator_name"] in OPERATORS_BY_ID
        assert row["operator_family"] in FAMILIES
        assert row["mode"] in ("library_proof", "adaptive")
        key = (row["source_instance_id"], row["operator_name"],
               row["mutated_answer"])
        assert key not in seen, "去重失败"
        seen.add(key)
        assert row["operator_name"] not in SUPPORT_CONTROL_OPS, \
            "support对照算子不得进入注入集"
    # 恒等变异守卫: FX-QA-004触发propose_numeric_identity(answer不变)
    assert report["stats"].get("noop_mutations_skipped", 0) >= 1
    identity_stats = report["operator_stats"]["ANSWER-NUM-IDENTITY-V1"]
    assert identity_stats["noop_skipped"] >= 1
    assert identity_stats["injected"] == 0


def test_build_injections_fixture_family_coverage() -> None:
    requests = [request_from_dict(row) for row in FIXTURE_ROWS]
    instances, report = build_injections(requests)
    by_op: dict[str, list[dict[str, Any]]] = {}
    for row in instances:
        by_op.setdefault(row["operator_name"], []).append(row)

    # TERM-07标识符替换: 换成evidence登记的另一标识
    term07 = by_op.get("ANSWER-TERM-07-INTERFACE-CONFLICT-V1", [])
    assert term07, "FX-QA-001应产出标识符冲突注入"
    assert any("PZXQ-GN-SJKCZ-SJKLJ" in r["mutated_answer"] for r in term07)

    # STRUCT枚举删元: grounded成员被删除
    removes = by_op.get("ANSWER-STRUCT-CLOSED-LIST-REMOVE-V1", [])
    assert removes
    assert any("数据库连接" not in r["mutated_answer"] for r in removes)

    # BASE/PARAM数值变异: "为1秒"声明被改写
    numeric_ops = ("ANSWER-NUM-EQ-CONFLICT-V1",
                   "ANSWER-PARAM-06-OUT-OF-RANGE-V1",
                   "ANSWER-PARAM-01-TIME-CONFLICT-V1")
    for op in numeric_ops:
        assert by_op.get(op), f"{op}应在FX-QA-002上适用"
    for op in numeric_ops:
        assert all("为1秒" not in r["mutated_answer"] for r in by_op[op])

    # STRUCT异常流结果错配 + LOGIC时序倒置
    assert by_op.get("ANSWER-STRUCT-EXCEPTION-OUTCOME-SWAP-V1")
    assert any("系统提示错误" in r["mutated_answer"]
               for r in by_op["ANSWER-STRUCT-EXCEPTION-OUTCOME-SWAP-V1"])
    orders = by_op.get("ANSWER-LOGIC-03-ORDER-SWAP-V1", [])
    assert orders, "FX-QA-003应产出台时序倒置注入"
    for r in orders:
        assert r["mutated_answer"].index("提示错误信息") < \
            r["mutated_answer"].index("检测连接")

    # GJB域外术语注入(校验域)
    gjb09 = by_op.get("ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1", [])
    assert gjb09, "FX-QA-005应产出GJB-09域外术语注入"
    assert any("正则表达式校验" in r["mutated_answer"] for r in gjb09)

    # strict层在恒等数值QA上发出sound refute(NUM-EQ-CONFLICT)
    assert report["operator_stats"]["ANSWER-NUM-EQ-CONFLICT-V1"][
        "strict_proposals"] >= 1
    modes = {r["mode"] for r in instances}
    assert "library_proof" in modes and "adaptive" in modes


def test_build_injections_deterministic() -> None:
    requests = [request_from_dict(row) for row in FIXTURE_ROWS]
    first, _ = build_injections(requests)
    second, _ = build_injections(requests)
    assert first == second, "构建必须确定性可复现(seed=42)"


# ------------------------------------------------------------ 评测逻辑(mock)
class _StubModule:
    """脚本化被测系统: instance_id → (verdict, [(claim_verdict, method)])."""

    def __init__(self, script: dict[str, tuple[str, list[tuple[str, str]]]]):
        self.script = script

    def verify(self, request: QAInput) -> VerificationResult:
        verdict, claims = self.script[request.instance_id]
        results = tuple(
            ClaimResult(
                claim_id=f"{request.instance_id}-c{i:02d}",
                claim_text=f"claim-{i}",
                verdict=claim_verdict,
                check_item_candidates=("TERM-03",),
                evidence_refs=("ev-0001",) if claim_verdict != "refute" else (),
                rationale="stub",
                method=method,
                confidence=1.0,
            )
            for i, (claim_verdict, method) in enumerate(claims, 1))
        return VerificationResult(
            instance_id=request.instance_id,
            question=request.question,
            answer=request.answer,
            verdict=verdict,
            status="ok",
            claim_results=results,
            evidence_chain=(),
            considered_evidence_ids=("ev-0001",),
            context_freeze_id=request.context_freeze_id,
            context_hash="stub",
            context_integrity="unknown",
            applicability="applicable",
            rationale="stub",
        )


def _mock_rows() -> list[dict[str, Any]]:
    rows = []
    for i in range(6):
        rows.append(_mock_row(f"MKJ-{i + 1:03d}", "STRUCT"))
    for i in range(6):
        rows.append(_mock_row(f"MKJ-{7 + i:03d}", "LOGIC"))
    for i in range(6):
        rows.append(_mock_row(f"MKJ-{13 + i:03d}", "BASE"))
    for i in range(2):
        rows.append(_mock_row(f"MKJ-{19 + i:03d}", "TERM"))
    return rows


def _mock_row(instance_id: str, family: str) -> dict[str, Any]:
    return {
        "instance_id": instance_id,
        "source_instance_id": f"SRC-{instance_id}",
        "operator_name": {
            "STRUCT": "ANSWER-STRUCT-STEP-REORDER-V1",
            "TERM": "ANSWER-TERM-07-INTERFACE-CONFLICT-V1",
            "BASE": "ANSWER-NUM-EQ-CONFLICT-V1",
            "LOGIC": "ANSWER-LOGIC-02-EXCEPTION-SWAP-V1",
        }[family],
        "operator_family": family,
        "check_item": "LOGIC-05",
        "mode": "adaptive",
        "question": "fixture问题",
        "answer": "变异后answer",
        "mutated_answer": "变异后answer",
        "original_answer": "原始answer",
        "expected_verdict": "refute",
        "mutation_rationale": "fixture变异说明",
        "context_freeze_id": "fixture-frozen-v1",
        "evidence": [_ev(f"{instance_id}-ev-0001", "fixture证据")],
    }


def _mock_script(rows: list[dict[str, Any]]) -> dict:
    script: dict[str, tuple[str, list[tuple[str, str]]]] = {}
    plan = {
        # STRUCT 6条: 3检出(2 sequence + 1 e1), 3 NIE漏检
        "MKJ-001": ("refute", [("refute", "sequence_alignment")]),
        "MKJ-002": ("refute", [("refute", "sequence_alignment")]),
        "MKJ-003": ("refute", [("refute", "e1_template_match")]),
        "MKJ-004": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        "MKJ-005": ("not_in_evidence",
                    [("not_in_evidence", "conservative_unresolved")]),
        "MKJ-006": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        # LOGIC 6条: 全部NIE漏检(能力缺口榜首)
        "MKJ-007": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        "MKJ-008": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        "MKJ-009": ("not_in_evidence",
                    [("not_in_evidence", "conservative_unresolved")]),
        "MKJ-010": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        "MKJ-011": ("not_in_evidence",
                    [("not_in_evidence", "conservative_unresolved")]),
        "MKJ-012": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        # BASE 6条: 1检出(per_claim数值通道), 5 NIE漏检
        "MKJ-013": ("refute", [("refute", "numeric_interval")]),
        "MKJ-014": ("not_in_evidence",
                    [("not_in_evidence", "conservative_unresolved")]),
        "MKJ-015": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        "MKJ-016": ("not_in_evidence",
                    [("not_in_evidence", "conservative_unresolved")]),
        "MKJ-017": ("not_in_evidence",
                    [("not_in_evidence", "semantic_unresolved")]),
        "MKJ-018": ("not_in_evidence",
                    [("not_in_evidence", "conservative_unresolved")]),
        # TERM 2条: 1检出(id_join), 1误support漏检
        "MKJ-019": ("refute", [("refute", "id_join_registry")]),
        "MKJ-020": ("support", [("support", "identifier_exact_match")]),
    }
    for row in rows:
        script[row["instance_id"]] = plan[row["instance_id"]]
    return script


def test_run_module_and_family_matrix_with_stub() -> None:
    rows = _mock_rows()
    module = _StubModule(_mock_script(rows))
    records = run_module(module, rows)
    assert len(records) == 20
    assert all(r["detected"] == (r["predicted_verdict"] == "refute")
               for r in records)
    det = [r for r in records if r["detected"]]
    assert {r["refute_channels"][0] for r in det} == {
        "sequence_L1", "e1_L1", "per_claim", "id_join_L1"}

    matrix = family_matrix(records)
    struct = matrix["STRUCT"]
    assert struct["n_injected"] == 6
    assert struct["n_detected"] == 3
    assert struct["detection_rate"] == 0.5
    assert struct["miss_rate"] == 0.5
    assert struct["main_detection_channel"] == "sequence_L1"
    assert struct["miss_kind_counts"] == {"nie": 3}
    logic = matrix["LOGIC"]
    assert logic["n_injected"] == 6 and logic["n_detected"] == 0
    assert logic["detection_rate"] == 0.0
    assert logic["main_detection_channel"] == ""
    base = matrix["BASE"]
    assert base["n_detected"] == 1
    assert base["main_detection_channel"] == "per_claim"
    term = matrix["TERM"]
    assert term["n_injected"] == 2 and term["n_detected"] == 1
    assert term["miss_kind_counts"] == {"support": 1}
    overall = matrix["OVERALL"]
    assert overall["n_injected"] == 20
    assert overall["n_detected"] == 5
    assert overall["detection_rate"] == 0.25
    assert overall["miss_kind_counts"] == {"nie": 14, "support": 1}


def test_operator_table_covers_full_registry() -> None:
    rows = _mock_rows()
    module = _StubModule(_mock_script(rows))
    records = run_module(module, rows)
    table = operator_table(records)
    assert len(table) == len(OPERATORS)  # 全表(含0注入行与support对照行)
    by_op = {entry["operator"]: entry for entry in table}
    struct = by_op["ANSWER-STRUCT-STEP-REORDER-V1"]
    assert struct["n_injected"] == 6
    assert struct["n_detected"] == 3
    assert struct["detection_rate"] == 0.5
    assert by_op["ANSWER-TERM-07-INTERFACE-CONFLICT-V1"]["n_detected"] == 1
    support_row = by_op["ANSWER-NUM-IDENTITY-V1"]
    assert support_row["n_injected"] == 0
    assert support_row["refute_semantics"] is False


def test_miss_reasons_and_sampling_with_stub() -> None:
    rows = _mock_rows()
    module = _StubModule(_mock_script(rows))
    records = run_module(module, rows)
    reasons = miss_reason_stats(records)
    assert reasons["n_missed"] == 15
    assert reasons["miss_kinds"] == {"nie": 14, "support": 1}
    assert "semantic_unresolved" in reasons["nie_causing_methods"]
    assert "conservative_unresolved" in reasons["nie_causing_methods"]
    assert "identifier_exact_match" in reasons["false_support_causing_methods"]

    samples = sample_misses(records, k=2, seed=42)
    assert len(samples) == 2
    assert all(
        all("method" in c for c in s["deciding_claims"]) or
        not s["deciding_claims"] for s in samples)
    again = sample_misses(records, k=2, seed=42)
    assert [s["instance_id"] for s in samples] == \
        [s["instance_id"] for s in again]  # 确定性抽样
    kinds = {s["miss_kind"].startswith(("NIE", "误support")) for s in samples}
    assert kinds

    gaps = capability_gaps(family_matrix(records))
    assert len(gaps) == 3, "n>=5的族恰好3个, 应全部进入缺口清单"
    assert gaps[0]["family"] == "LOGIC"
    assert gaps[1]["family"] == "BASE"
    assert "检出率" in gaps[0]["gap_statement"]
    assert [g["detection_rate"] for g in gaps] == [0.0, 0.1667, 0.5]


# ------------------------------------------------------------ 真实evalset
@pytest.mark.skipif(not EVALSET.exists(), reason="注入评测集未构建")
def test_real_evalset_schema_and_guards() -> None:
    rows = load_rows(EVALSET)
    assert len(rows) >= 100, "真实注入集规模过小"
    ids = [r["instance_id"] for r in rows]
    assert len(set(ids)) == len(ids)
    for row in rows:
        assert row["schema"] == "mutation_injection_evalset_v1"
        assert row["expected_verdict"] == "refute"
        assert row["mutated_answer"] != row["original_answer"]
        assert row["mutated_answer"] == row["answer"]
        assert row["operator_name"] in OPERATORS_BY_ID
        assert row["operator_family"] in FAMILIES
        assert row["operator_name"] not in SUPPORT_CONTROL_OPS
        assert row["mode"] in ("library_proof", "adaptive")
    families = {row["operator_family"] for row in rows}
    assert len(families) >= 5
    # request_from_dict兼容(evidence字段完整)
    request = request_from_dict(rows[0])
    assert request.instance_id == rows[0]["instance_id"]
    assert request.evidence
