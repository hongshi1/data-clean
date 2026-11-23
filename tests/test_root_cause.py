"""Root-cause attribution tests (M92): classify_root_cause + localization
contract (InconsistencyLocalization.root_cause filled by
_build_localizations; server contract passthrough covered by the field's
plain-dict shape)."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import (  # noqa: E402
    InconsistencyLocalization,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.root_cause import (  # noqa: E402
    CHANNEL_ROOT_CAUSE,
    NLI_DIFFERENCE_OPERATIONS,
    ROOT_CAUSE_OPERATION,
    ROOT_CAUSE_SOURCE,
    RATIONALE_REFINEMENTS,
    classify_root_cause,
)


def test_vocabulary_is_closed_and_disjoint() -> None:
    """13条NLI操作与4条结构操作构成封闭词表, 无重复无泄漏."""
    assert len(ROOT_CAUSE_OPERATION) == 17
    assert len(set(ROOT_CAUSE_OPERATION)) == 17
    assert set(ROOT_CAUSE_SOURCE) == {
        "answer", "document_internal", "document_gap", "recall_insufficient"}
    assert "semantic_unspecified" in ROOT_CAUSE_OPERATION
    assert "value_substitution" in NLI_DIFFERENCE_OPERATIONS


def test_channel_table_lookup_covers_all_values() -> None:
    """通道直查表只产合法根因; refine表的method前缀都在直查表内."""
    for cause in CHANNEL_ROOT_CAUSE.values():
        assert cause["source"] in ROOT_CAUSE_SOURCE
        assert cause["operation"] in ROOT_CAUSE_OPERATION
    for prefix, _pattern, cause in RATIONALE_REFINEMENTS:
        assert prefix in CHANNEL_ROOT_CAUSE, "refinement须锚定已知通道"
        assert cause["source"] in ROOT_CAUSE_SOURCE
        assert cause["operation"] in ROOT_CAUSE_OPERATION


def test_expert_channel_table_lookup() -> None:
    assert classify_root_cause("coverage_join", "覆盖比对") == {
        "source": "document_gap", "operation": "compliance_gap"}
    assert classify_root_cause("e1_template_match", "主题错位") == {
        "source": "document_internal",
        "operation": "exception_flow_mismatch"}
    assert classify_root_cause("trace_bidirectional_join", "正逆矛盾") == {
        "source": "document_internal", "operation": "relation_inversion"}
    assert classify_root_cause("id_join_registry", "subject-ID错配") == {
        "source": "answer", "operation": "value_substitution"}
    assert classify_root_cause("enum_join_registry", "枚举集合冲突") == {
        "source": "answer", "operation": "scope_leakage"}


def test_id_join_dual_registration_refinement() -> None:
    """rationale含双登记线索→文档侧注册表缺陷(而非answer值替换)."""
    refined = classify_root_cause(
        "id_join_registry",
        "ID双登记：X同时注册给主体A、主体B；answer声称持有该ID"
        "（TERM-07同ID双登记）")
    assert refined == {"source": "document_internal",
                       "operation": "dual_registration"}
    plain = classify_root_cause(
        "id_join_registry", "subject-ID错配：注册表登记为Y，与answer不符")
    assert plain == {"source": "answer",
                     "operation": "value_substitution"}


def test_enum_and_trace_rationale_refinements() -> None:
    typo = classify_root_cause(
        "enum_join_registry", "证据侧疑似错别字：平版→平板，值域不含该注册值")
    assert typo == {"source": "document_internal",
                    "operation": "value_substitution"}
    prose = classify_root_cause(
        "enum_join_registry",
        "answer成员「X」见于正文枚举{A,X}但不在能力表行{A}的封闭集合中")
    assert prose == {"source": "document_internal",
                     "operation": "scope_leakage"}
    row = classify_root_cause(
        "trace_bidirectional_join",
        "同行矛盾：row20映射非空，但跟踪说明列写「不追踪」（GJB-05）")
    assert row == {"source": "document_internal",
                   "operation": "negation_mismatch"}


def test_l0_entity_prefix_family() -> None:
    """l0_entity_detector:TERM-xx(含:warning后缀)按TERM码查操作表."""
    term07 = classify_root_cause("l0_entity_detector:TERM-07", "接口标识冲突")
    assert term07 == {"source": "answer", "operation": "value_substitution"}
    term02 = classify_root_cause(
        "l0_entity_detector:TERM-02:warning", "同名异义")
    assert term02 == {"source": "answer", "operation": "entity_substitution"}
    unknown_term = classify_root_cause(
        "l0_entity_detector:TERM-99", "未登记TERM码")
    assert unknown_term["operation"] == "entity_substitution"


def test_nli_residual_keyword_classifier() -> None:
    """nli_residual按rationale关键词→13条差异类型; 无线索→unspecified."""
    assert classify_root_cause(
        "nli_residual", "NLI残差判定：CONTRADICTION(p=0.87)，premise含5条"
    )["operation"] == "semantic_unspecified"
    assert classify_root_cause(
        "nli_residual", "answer把部分断言扩大为所有设备均支持")["operation"] \
        == "quantifier_scope_expansion"
    assert classify_root_cause(
        "nli_residual", "标识符与登记值不符，值被截断")["operation"] \
        == "value_substitution"
    assert classify_root_cause(
        "nli_residual", "文档禁止，answer声称允许，模态冲突")["operation"] \
        == "modal_conflict"
    # 13条差异类型的operation全部落在封闭词表内
    for operation in NLI_DIFFERENCE_OPERATIONS:
        cause = classify_root_cause(
            "nli_residual", f"占位rationale-{operation}")
        assert cause["operation"] in ROOT_CAUSE_OPERATION


def test_unknown_method_falls_back() -> None:
    assert classify_root_cause("mystery_channel", "whatever") == {
        "source": "answer", "operation": "semantic_unspecified"}
    assert classify_root_cause(
        "nli_residual_unavailable", "通道不可用") == {
        "source": "recall_insufficient", "operation": "semantic_unspecified"}


def test_result_dict_not_shared_with_tables() -> None:
    """返回新dict: 调用方改写不污染模块级声明表."""
    first = classify_root_cause("coverage_join", "x")
    first["source"] = "mutated"
    second = classify_root_cause("coverage_join", "x")
    assert second["source"] == "document_gap"
    assert CHANNEL_ROOT_CAUSE["coverage_join"]["source"] == "document_gap"


def _request(answer: str) -> QAInput:
    evidence = RetrievedEvidence(
        evidence_id="e1", text="数据库关闭的项目唯一标识符：ID-A",
        source_type="text",
        source_ref=SourceRef(doc_id="04", section="3.2",
                             block_id="block-000001"),
        scope_id="", completeness="open")
    return QAInput(instance_id="t-root", question="q", answer=answer,
                   evidence=(evidence,), context_freeze_id="test")


def test_localizations_carry_root_cause() -> None:
    """refute定位报告附带root_cause两层字段(向后兼容: 字段存在非None)."""
    module = QAConsistencyModule(use_experts=True)
    result = module.verify(_request("数据库关闭的项目唯一标识符为ID-B"))
    assert result.verdict == "refute"
    assert result.localizations
    for loc in result.localizations:
        assert isinstance(loc, InconsistencyLocalization)
        assert loc.root_cause is not None
        assert set(loc.root_cause) == {"source", "operation"}
        assert loc.root_cause["source"] in ROOT_CAUSE_SOURCE
        assert loc.root_cause["operation"] in ROOT_CAUSE_OPERATION


def test_support_localizations_stay_empty_and_field_optional() -> None:
    """非refute不产出定位; root_cause默认None保持向后兼容."""
    module = QAConsistencyModule(use_experts=True)
    ok = module.verify(_request("数据库关闭的项目唯一标识符为ID-A"))
    assert ok.verdict != "refute"
    assert ok.localizations == ()
    blank = InconsistencyLocalization(
        claim_id="c", claim_text="t", answer_span=None,
        check_item_candidates=(), method="m", confidence=1.0,
        rationale="r", evidence=())
    assert blank.root_cause is None
