"""Z3数值约束专家（L1区间算术+数值聚合，设计§6.3）的契约测试。"""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import EvidenceStatement  # noqa: E402
from algorithms.consistency.numeric_z3_expert import (  # noqa: E402
    CHECK_ITEMS_AGGREGATE,
    CHECK_ITEMS_INTERVAL,
    METHOD,
    Z3_TIMEOUT_MS,
    extract_numeric_claims,
    extract_numeric_facts,
    normalize_numeric,
    verify_numeric_constraints,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402


def statement(text: str, evidence_id: str = "e1", field: str = "sentence",
              scope: str = "") -> EvidenceStatement:
    return EvidenceStatement(
        statement_id=f"{evidence_id}#s0", evidence_id=evidence_id, text=text,
        field_name=field, scope_key=scope, row_index=1)


def make_request(answer: str, question: str = "系统响应时间要求是多少？",
                 evidence_id: str = "e1") -> QAInput:
    return QAInput(
        instance_id="qa-numz3",
        question=question,
        answer=answer,
        context_freeze_id="freeze-numz3",
        evidence=(RetrievedEvidence(
            evidence_id=evidence_id, text="数值约束证据占位。",
            source_type="text", source_ref=SourceRef(doc_id="doc04",
                                                     section="3.3"),
            scope_id="doc04:3.3"),),
    )


# ── 数值事实抽取 ──────────────────────────────────────────


def test_field_style_facts_from_data_table_statements() -> None:
    facts = extract_numeric_facts([
        statement("数据同步时延的最大差：100ms", field="最大差",
                  scope="数据同步时延"),
        statement("XX参数的最小差：5ms", field="最小差", scope="XX参数"),
        statement("YY参数的精度：0.5ms", field="精度", scope="YY参数"),
    ])
    by_subject = {fact.subject: fact for fact in facts}
    assert by_subject["数据同步时延"].op == "le"
    assert by_subject["数据同步时延"].raw_value == "100"
    assert by_subject["数据同步时延"].unit == "ms"
    assert by_subject["数据同步时延"].family == "time"
    assert by_subject["数据同步时延"].value == 0.1
    assert by_subject["XX参数"].op == "ge"
    assert by_subject["XX参数"].value == 0.005
    assert by_subject["YY参数"].op == "eq"
    assert by_subject["YY参数"].value == 0.0005
    # 字段类标记：同一数据项的最大值/最小值/精度是三个不同的量
    assert by_subject["数据同步时延"].field_class == "max"
    assert by_subject["XX参数"].field_class == "min"
    assert by_subject["YY参数"].field_class == "precision"
    assert by_subject["数据同步时延"].subject == "数据同步时延"


def test_prose_facts_cover_colon_table_cells() -> None:
    facts = extract_numeric_facts([
        statement("内存：不小于16GB", field="cell"),
        statement("数据源切换时间不超过2s。"),
    ])
    by_subject = {fact.subject: fact for fact in facts}
    assert by_subject["内存"].op == "ge"
    assert by_subject["内存"].family == "storage"
    assert by_subject["内存"].value == 16 * 1073741824
    assert by_subject["数据源切换时间"].op == "le"
    assert by_subject["数据源切换时间"].family == "time"
    assert by_subject["数据源切换时间"].value == 2.0


def test_unit_declaration_resolves_family_of_unitless_fact() -> None:
    facts = extract_numeric_facts([
        statement("响应时间的单位：ms", field="单位", scope="响应时间"),
        statement("响应时间的最大差：100", field="最大差", scope="响应时间"),
    ])
    assert len(facts) == 1
    assert facts[0].family == "time"
    assert facts[0].value == 0.1


def test_statements_without_subject_are_dropped() -> None:
    facts = extract_numeric_facts([statement("不超过200ms。")])
    assert facts == []


# ── answer数值声明抽取与单位归一 ─────────────────────────


def test_extract_numeric_claims_shapes_and_aggregate_flag() -> None:
    claims = extract_numeric_claims("响应时间不超过50ms。", "响应时间要求是多少？")
    assert len(claims) == 1
    assert claims[0].subject == "响应时间"
    assert claims[0].op == "le"
    assert claims[0].value == "50"
    assert claims[0].unit == "ms"
    assert claims[0].claim_text == "响应时间 不超过50ms"
    assert claims[0].aggregate is False

    aggregate = extract_numeric_claims(
        "总处理时间不超过100ms。", "系统总处理时间要求是多少？")
    assert aggregate[0].aggregate is True

    enumerated = extract_numeric_claims("三者之和不超过100ms。")
    assert enumerated[0].aggregate is True


def test_normalize_numeric_unit_families() -> None:
    assert normalize_numeric("1000", "ms").canonical_value == \
        normalize_numeric("1", "s").canonical_value
    assert normalize_numeric("2", "GB").canonical_value == 2 * 1073741824
    assert normalize_numeric("5", "").family == "count"
    assert normalize_numeric("100", "px").family == "raw:px"
    assert normalize_numeric("3", "分钟").canonical_value == 180.0
    assert normalize_numeric("abc", "ms") is None


# ── 单参数区间三态判定 ────────────────────────────────────


def test_interval_support_answer_within_documented_bound() -> None:
    results = verify_numeric_constraints(
        make_request("响应时间不超过50ms。"), [statement(
            "响应时间的最大差：100ms", field="最大差")])
    assert len(results) == 1
    assert results[0].verdict == "support"
    assert results[0].method == METHOD
    assert results[0].check_item_candidates == CHECK_ITEMS_INTERVAL
    assert results[0].evidence_refs == ("e1",)


def test_interval_refute_disjoint_with_unsat_core_and_smtlib() -> None:
    evidence = statement("响应时间的最大差：100ms", field="最大差")
    results = verify_numeric_constraints(
        make_request("响应时间至少150ms。"), [evidence])
    assert len(results) == 1
    assert results[0].verdict == "refute"
    assert results[0].confidence == 1.0
    assert "unsat core：" in results[0].rationale
    assert "ans(响应时间≥150ms)" in results[0].rationale
    assert "ev0(响应时间≤100ms)" in results[0].rationale
    assert "SMT-LIB：" in results[0].rationale
    assert "(check-sat)" in results[0].rationale


def test_interval_weaker_bound_is_nie_by_interval_semantics() -> None:
    evidence = statement("响应时间的最大差：100ms", field="最大差")
    results = verify_numeric_constraints(
        make_request("响应时间不超过200ms。"), [evidence])
    assert len(results) == 1
    assert results[0].verdict == "not_in_evidence"
    assert "部分重叠" in results[0].rationale


def test_interval_unit_conversion_support() -> None:
    evidence = statement("响应时间为1s。")
    results = verify_numeric_constraints(
        make_request("响应时间为1000ms。"), [evidence])
    assert results[0].verdict == "support"


def test_interval_context_internal_conflict_is_nie_not_arbitrated() -> None:
    evidence = [
        statement("响应时间不超过100ms。", evidence_id="e1"),
        statement("响应时间不小于200ms。", evidence_id="e2"),
    ]
    results = verify_numeric_constraints(
        make_request("响应时间不超过50ms。"), evidence)
    assert len(results) == 1
    assert results[0].verdict == "not_in_evidence"
    assert "context内部数值矛盾" in results[0].rationale
    assert "unsat core：" in results[0].rationale


def test_interval_cross_family_facts_are_not_joined() -> None:
    evidence = statement("内存不小于16GB。")
    results = verify_numeric_constraints(
        make_request("响应时间不超过50ms。", question="响应时间要求是多少？"),
        [evidence])
    assert results == []


def test_no_numeric_facts_returns_empty() -> None:
    results = verify_numeric_constraints(
        make_request("响应时间不超过50ms。"),
        [statement("系统提供数据查询功能。")])
    assert results == []


# ── 字段类join键（C06QA-008修复：max/min/精度不跨字段误join） ──


def test_claim_field_qualifier_split() -> None:
    """answer主体字段限定词→(核心主体, 字段类)；裸"上限"是数据项名
    的一部分（告警上限），不剥离。"""
    from algorithms.consistency.numeric_z3_expert import (
        _split_field_qualifier)
    assert _split_field_qualifier("最大连接数的最大值") == (
        "最大连接数", "max")
    assert _split_field_qualifier("内存占用状态") == ("内存占用状态", "")
    assert _split_field_qualifier("响应时间的下限") == ("响应时间", "min")
    assert _split_field_qualifier("告警上限") == ("告警上限", "")


def test_qualified_max_claim_isolated_from_min_and_precision() -> None:
    """C06QA-008真实形态（06号表97）：answer"X的最大值为200"的eq声明
    只与最大值行(le 200)比对，不再误join最小值(ge 0)与精度(eq 1)行
    ——修复前三行池进同一Z3变量，eq200∧eq1撞UNSAT伪refute。"""
    evidence = [
        statement("最大连接数的最大值：200", field="最大值",
                  scope="最大连接数"),
        statement("最大连接数的最小值：0", field="最小值",
                  scope="最大连接数"),
        statement("最大连接数的精度：1", field="精度", scope="最大连接数"),
    ]
    request = make_request(
        "最大连接数的最大值为200，该数据项的取值不能超过此限值。",
        question="最大连接数的最大值是多少？")
    results = verify_numeric_constraints(request, evidence)
    assert len(results) == 1
    assert results[0].verdict == "support"
    assert "ev0(最大连接数≤200)" in results[0].rationale


def test_unqualified_value_claim_isolated_from_precision_fact() -> None:
    """无限定eq声明（"X为200"，值本身）与max/min事实比对（值域包含
    →support），不与精度行(eq 1)误join。"""
    evidence = [
        statement("最大连接数的最大值：200", field="最大值",
                  scope="最大连接数"),
        statement("最大连接数的最小值：0", field="最小值",
                  scope="最大连接数"),
        statement("最大连接数的精度：1", field="精度", scope="最大连接数"),
    ]
    request = make_request("最大连接数为200。", question="最大连接数是多少？")
    results = verify_numeric_constraints(request, evidence)
    assert len(results) == 1
    assert results[0].verdict == "support"


def test_qualified_min_claim_joins_min_fact_only() -> None:
    """限定min声明（"X的最小值不小于1"）只与最小值行(ge 0)比对：
    answer下界强于文档下界→support（子集语义）；最大值行(le 200)
    不进同一Z3问题（evidence_refs仅含最小值行所在证据块）。"""
    evidence = [
        statement("最大连接数的最大值：200", field="最大值",
                  scope="最大连接数", evidence_id="e-max"),
        statement("最大连接数的最小值：0", field="最小值",
                  scope="最大连接数", evidence_id="e-min"),
    ]
    request = make_request(
        "最大连接数的最小值不小于1。", question="最大连接数的最小值是多少？")
    results = verify_numeric_constraints(request, evidence)
    assert len(results) == 1
    assert results[0].verdict == "support"
    assert results[0].evidence_refs == ("e-min",)
    assert "最大连接数≥0" in results[0].rationale
    assert "最大连接数≤200" not in results[0].rationale


def test_qualified_min_upper_claim_refutes_against_min_fact() -> None:
    """限定min声明与最小值行的反向矛盾：声称"最小值至多1ms"(le)与
    文档最小值ge 5ms无交集→refute（仅最小值行参与，unsat core可溯源）。"""
    evidence = [
        statement("数据同步时延的最大差：100ms", field="最大差",
                  scope="数据同步时延", evidence_id="e-max"),
        statement("数据同步时延的最小差：5ms", field="最小差",
                  scope="数据同步时延", evidence_id="e-min"),
    ]
    request = make_request(
        "数据同步时延的最小值至多1ms。",
        question="数据同步时延的最小值是多少？")
    results = verify_numeric_constraints(request, evidence)
    assert len(results) == 1
    assert results[0].verdict == "refute"
    assert results[0].evidence_refs == ("e-min",)


def test_precision_claim_joins_precision_fact_only() -> None:
    """"X的精度"式声明（的-前缀限定）与精度行同类比对：值一致support。"""
    evidence = [
        statement("CPU占用状态的精度：1", field="精度", scope="CPU占用状态"),
        statement("CPU占用状态的最大值：100", field="最大值",
                  scope="CPU占用状态"),
    ]
    request = make_request(
        "CPU占用状态的精度为1。", question="CPU占用状态的精度是多少？")
    results = verify_numeric_constraints(request, evidence)
    assert len(results) == 1
    assert results[0].verdict == "support"


def test_bare_upper_limit_name_is_not_stripped() -> None:
    """数据项名以"上限"结尾（告警上限）：裸形不剥离字段限定词，
    声明与算子式事实同量纲（值本身）正常join。"""
    evidence = [statement("告警上限不超过3条。")]
    request = make_request("告警上限不超过3条。",
                           question="告警上限是多少？")
    results = verify_numeric_constraints(request, evidence)
    assert len(results) == 1
    assert results[0].verdict == "support"


# ── 跨参数聚合检查（PARAM-01/05，合成能力证明） ───────────


def component_statements() -> list[EvidenceStatement]:
    return [
        statement("A阶段的处理时间为30ms。", evidence_id="e1"),
        statement("B阶段的处理时间为40ms。", evidence_id="e2"),
        statement("C阶段的处理时间为50ms。", evidence_id="e3"),
    ]


def test_aggregate_refute_sum_exceeds_bound() -> None:
    results = verify_numeric_constraints(
        make_request("总处理时间不超过100ms。"), component_statements())
    assert len(results) == 1
    assert results[0].verdict == "refute"
    assert results[0].check_item_candidates == CHECK_ITEMS_AGGREGATE
    assert set(results[0].evidence_refs) == {"e1", "e2", "e3"}
    assert "unsat core：" in results[0].rationale
    for name in ("comp0_", "comp1_", "comp2_"):
        assert name in results[0].rationale
    assert "agg(Σ(总处理时间≤100ms))" in results[0].rationale


def test_aggregate_support_entailed_sum() -> None:
    results = verify_numeric_constraints(
        make_request("总处理时间不超过200ms。"), component_statements())
    assert len(results) == 1
    assert results[0].verdict == "support"


def test_aggregate_lower_bound_components_refute() -> None:
    evidence = [
        statement("A阶段耗时至少30ms。", evidence_id="e1"),
        statement("B阶段耗时至少40ms。", evidence_id="e2"),
        statement("C阶段耗时至少50ms。", evidence_id="e3"),
    ]
    results = verify_numeric_constraints(
        make_request("总耗时不超过100ms。"), evidence)
    assert len(results) == 1
    assert results[0].verdict == "refute"


def test_aggregate_requires_two_distinct_components() -> None:
    single = [statement("A阶段的处理时间为30ms。", evidence_id="e1")]
    results = verify_numeric_constraints(
        make_request("总处理时间不超过100ms。"), single)
    assert results == []


def test_aggregate_component_facts_match_answer_family_only() -> None:
    mixed = component_statements() + [statement("内存不小于16GB。",
                                                evidence_id="e4")]
    results = verify_numeric_constraints(
        make_request("总处理时间不超过100ms。"), mixed)
    assert len(results) == 1
    assert set(results[0].evidence_refs) == {"e1", "e2", "e3"}


# ── 与qa_module数值通道的集成与融合 ───────────────────────


def test_expert_channel_registered_and_detects_field_form_evidence() -> None:
    """字段式证据（"最大差：100ms"）旧数值通道读不出算子式声明，
    本专家补上refute；expert_filter可单独 gated 本专家。"""
    request = QAInput(
        instance_id="qa-numz3-module",
        question="系统响应时间要求是多少？",
        answer="响应时间至少150ms。",
        context_freeze_id="freeze-numz3-module",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="响应时间的最大差：100ms",
            source_type="table", source_ref=SourceRef(doc_id="doc04",
                                                      section="3.3.1"),
            scope_id="doc04:3.3.1"),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "refute"
    fused = [claim for claim in result.claim_results
             if claim.claim_text == "响应时间 至少150ms"]
    assert len(fused) == 1
    assert fused[0].verdict == "refute"
    assert fused[0].method == METHOD

    filtered = QAConsistencyModule(
        expert_filter=("numeric_z3",)).verify(request)
    assert filtered.verdict == "refute"
    assert all(claim.method == METHOD for claim in filtered.claim_results)


def test_module_fusion_support_wins_over_expert_nie() -> None:
    """answer弱于文档界（≤200 vs 文档≤100）：专家按严格区间语义NIE，
    旧通道判support，per-claim融合取support。"""
    request = QAInput(
        instance_id="qa-numz3-fusion",
        question="系统响应时间要求是多少？",
        answer="响应时间不超过200ms。",
        context_freeze_id="freeze-numz3-fusion",
        evidence=(RetrievedEvidence(
            evidence_id="e1", text="响应时间不超过100ms。",
            source_type="text", source_ref=SourceRef(doc_id="doc04",
                                                     section="3.3.1"),
            scope_id="doc04:3.3.1"),),
    )
    result = QAConsistencyModule().verify(request)
    assert result.verdict == "support"


def test_z3_timeout_is_configured() -> None:
    assert Z3_TIMEOUT_MS == 500
