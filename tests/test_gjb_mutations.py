"""GJB-01..GJB-11 answer-only B-fact-verification mutation operators."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_mutations import AnswerMutationProposal  # noqa: E402
from algorithms.consistency.gjb_mutations import (  # noqa: E402
    GJB_OPERATOR_STATUS,
    propose_gjb01_quantifier_fabrication,
    propose_gjb02_fault_tolerance_exclusion,
    propose_gjb03_access_control_exclusion,
    propose_gjb04_audit_field_exclusion,
    propose_gjb05_trace_conflict,
    propose_gjb05_trace_match,
    propose_gjb06_alarm_element_exclusion,
    propose_gjb07_self_check_exclusion,
    propose_gjb08_power_loss_exclusion,
    propose_gjb09_input_validation_exclusion,
    propose_gjb10_rollback_fabrication,
    propose_gjb11_degraded_mode_exclusion,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402


def ev(evidence_id: str, text: str, *, source_type: str = "text",
       completeness: str = "closed", proof: str = "条款封闭枚举证明",
       scope_id: str = "doc01:3.2", section: str = "3.2",
       doc_id: str = "doc01") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id, text=text, source_type=source_type,
        source_ref=SourceRef(doc_id=doc_id, section=section), scope_id=scope_id,
        completeness=completeness, completeness_proof=proof)


def make_input(instance_id: str, question: str, answer: str,
               evidence: tuple[RetrievedEvidence, ...]) -> QAInput:
    return QAInput(
        instance_id=instance_id, question=question, answer=answer,
        context_freeze_id=f"freeze-{instance_id}", evidence=evidence)


def assert_frozen_fields(proposal: AnswerMutationProposal, request: QAInput,
                         refs: tuple[SourceRef, ...]) -> None:
    assert proposal.target == "answer"
    assert proposal.question == request.question
    assert proposal.answer_before == request.answer
    assert proposal.context_freeze_id == request.context_freeze_id
    assert proposal.context_hash and proposal.question_hash
    assert proposal.context_refs == refs
    assert proposal.proof and proposal.requires_manual_review is False


def make_gjb01_request(*, completeness: str = "closed",
                       proof: str = "SRS-3.2.1-01需求条款全文冻结",
                       requirement_text: str = "系统应及时完成数据回传，确保业务连续。",
                       question: str = "需求SRS-3.2.1-01的可测试性判据是什么？",
                       rule_source_type: str = "rule") -> QAInput:
    return make_input("qa-gjb01", question, "需求SRS-3.2.1-01要求及时完成数据回传。", (
        ev("e-req", requirement_text, completeness=completeness, proof=proof,
           scope_id="doc01:SRS-3.2.1-01", section="3.2.1"),
        ev("e-rule", "GJB-01：需求应可测试，验收判据应为可测量的量化指标。",
           source_type=rule_source_type, completeness="unknown", proof="",
           scope_id="gjb438c:GJB-01", section="GJB-01", doc_id="GJB-438C"),
    ))


def make_gjb02_request(*, completeness: str = "closed",
                       proof: str = "3.2.2节容错机制需求条款封闭枚举",
                       evidence_text: str = "系统故障容错机制包括：故障检测、故障隔离、自动恢复三种。",
                       question: str = "系统提供哪些故障容错机制？",
                       answer: str = "系统故障容错机制包括故障检测、故障隔离。",
                       scope_id: str = "doc01:3.2.2", section: str = "3.2.2") -> QAInput:
    return make_input(
        "qa-gjb02", question, answer,
        (ev("e-ft", evidence_text, completeness=completeness, proof=proof,
            scope_id=scope_id, section=section),))


def make_gjb05_request(*, question: str = "需求SRS-3.2.1-01映射到哪个测试项？",
                       answer: str = "需求SRS-3.2.1-01映射到测试项T-01。",
                       evidence_text: str = "需求追溯表：SRS-3.2.1-01→测试项T-01；"
                                            "SRS-3.2.1-02→测试项T-02。") -> QAInput:
    return make_input(
        "qa-gjb05", question, answer,
        (ev("e-trace", evidence_text, source_type="trace", completeness="unknown",
            proof="", scope_id="doc01:5.1", section="5.1"),))


def make_gjb10_request(*, evidence_text: str = "软件版本升级失败后重新执行升级，不支持回滚。",
                       question: str = "软件版本升级失败后如何处理？",
                       answer: str = "软件版本升级失败后重新执行升级。") -> QAInput:
    return make_input(
        "qa-gjb10", question, answer,
        (ev("e-upg", evidence_text, completeness="unknown", proof="",
            scope_id="doc01:3.4", section="3.4"),))


def test_gjb01_fabricated_quantifier_is_refuted_by_closed_qualitative_text() -> None:
    request = make_gjb01_request()
    proposal = propose_gjb01_quantifier_fabrication(
        request, evidence_id="e-req", rule_evidence_id="e-rule",
        requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过200ms")
    assert proposal.operator_id == "ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1"
    assert proposal.check_item == "GJB-01"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "closed_requirement_text_quantifier_absence"
    assert proposal.answer_after == (
        "需求SRS-3.2.1-01要求及时完成数据回传，量化判据为完成时间不超过200ms。")
    assert_frozen_fields(
        proposal, request,
        (request.evidence[0].source_ref, request.evidence[1].source_ref))


@pytest.mark.parametrize("completeness,proof", [
    ("open", "有证明"), ("unknown", "有证明"), ("closed", ""),
])
def test_gjb01_rejects_open_or_unproved_requirement_text(
        completeness: str, proof: str) -> None:
    request = make_gjb01_request(completeness=completeness, proof=proof)
    with pytest.raises(ValueError, match="manual review"):
        propose_gjb01_quantifier_fabrication(
            request, evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过200ms")


def test_gjb01_rejects_requirement_with_quantitative_indicator() -> None:
    request = make_gjb01_request(requirement_text="系统应在200ms内完成数据回传。")
    with pytest.raises(ValueError, match="quantitative indicator"):
        propose_gjb01_quantifier_fabrication(
            request, evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过300ms")


def test_gjb01_rejects_requirement_without_explicit_qualitative_statement() -> None:
    request = make_gjb01_request(requirement_text="系统应完成数据回传并上报结果。")
    with pytest.raises(ValueError, match="qualitative statement"):
        propose_gjb01_quantifier_fabrication(
            request, evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过200ms")


def test_gjb01_rejects_rule_evidence_not_typed_as_rule() -> None:
    request = make_gjb01_request(rule_source_type="text")
    with pytest.raises(ValueError, match="source_type"):
        propose_gjb01_quantifier_fabrication(
            request, evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过200ms")


def test_gjb01_rejects_question_not_mentioning_the_requirement() -> None:
    request = make_gjb01_request(question="系统的可测试性判据是什么？")
    with pytest.raises(ValueError, match="question does not mention"):
        propose_gjb01_quantifier_fabrication(
            request, evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过200ms")


def test_gjb01_rejects_non_quantified_criterion_claim() -> None:
    request = make_gjb01_request()
    with pytest.raises(ValueError, match="numeric quantifier"):
        propose_gjb01_quantifier_fabrication(
            request, evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间足够短")


def test_gjb02_fault_tolerance_exclusion_is_refuted_by_closed_list() -> None:
    request = make_gjb02_request()
    proposal = propose_gjb02_fault_tolerance_exclusion(
        request, evidence_id="e-ft", term="手动切换")
    assert proposal.operator_id == "ANSWER-GJB-02-FT-EXCLUSION-V1"
    assert proposal.check_item == "GJB-02"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "closed_list_exclusion"
    assert proposal.answer_after == "系统故障容错机制包括故障检测、故障隔离、手动切换。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


@pytest.mark.parametrize("completeness,proof", [
    ("open", "有证明"), ("unknown", "有证明"), ("closed", ""),
])
def test_gjb02_open_or_unproved_evidence_never_refutes(
        completeness: str, proof: str) -> None:
    request = make_gjb02_request(completeness=completeness, proof=proof)
    with pytest.raises(ValueError, match="manual review"):
        propose_gjb02_fault_tolerance_exclusion(
            request, evidence_id="e-ft", term="手动切换")


def test_gjb02_rejects_term_present_in_evidence_text() -> None:
    request = make_gjb02_request()
    with pytest.raises(ValueError, match="unproven"):
        propose_gjb02_fault_tolerance_exclusion(
            request, evidence_id="e-ft", term="自动恢复")


def test_gjb02_rejects_term_already_present_in_answer() -> None:
    request = make_gjb02_request(
        answer="系统故障容错机制包括故障检测、故障隔离、手动切换。")
    with pytest.raises(ValueError, match="already present"):
        propose_gjb02_fault_tolerance_exclusion(
            request, evidence_id="e-ft", term="手动切换")


def test_gjb02_rejects_question_from_another_subject_domain() -> None:
    request = make_gjb02_request(question="系统支持哪些降级运行模式？")
    with pytest.raises(ValueError, match="subject domain"):
        propose_gjb02_fault_tolerance_exclusion(
            request, evidence_id="e-ft", term="手动切换")


def test_gjb02_rejects_answer_without_enumeration_claim() -> None:
    request = make_gjb02_request(answer="系统具备完善的故障处理能力。")
    with pytest.raises(ValueError, match="enumeration claim"):
        propose_gjb02_fault_tolerance_exclusion(
            request, evidence_id="e-ft", term="手动切换")


def test_gjb02_rejects_evidence_from_another_subject_domain() -> None:
    request = make_input(
        "qa-gjb02-x", "系统提供哪些故障容错机制？",
        "系统故障容错机制包括故障检测、故障隔离。",
        (ev("e-alarm-x", "报警要素包括：报警级别、报警时间、报警内容。",
            scope_id="doc01:3.7", section="3.7"),))
    with pytest.raises(ValueError, match="subject domain"):
        propose_gjb02_fault_tolerance_exclusion(
            request, evidence_id="e-alarm-x", term="手动切换")


def test_gjb03_access_control_exclusion_is_refuted_by_closed_list() -> None:
    request = make_input(
        "qa-gjb03", "系统实现了哪些权限控制？",
        "系统访问控制包括身份鉴别、权限校验。",
        (ev("e-acl", "系统权限控制仅包括：身份鉴别、权限校验、访问审计。",
            scope_id="doc01:3.6", section="3.6"),))
    proposal = propose_gjb03_access_control_exclusion(
        request, evidence_id="e-acl", term="强制访问控制")
    assert proposal.operator_id == "ANSWER-GJB-03-ACL-EXCLUSION-V1"
    assert proposal.check_item == "GJB-03"
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "系统访问控制包括身份鉴别、权限校验、强制访问控制。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))
    with pytest.raises(ValueError, match="unproven"):
        propose_gjb03_access_control_exclusion(
            request, evidence_id="e-acl", term="访问审计")


def test_gjb04_audit_field_exclusion_is_refuted_by_closed_field_list() -> None:
    request = make_input(
        "qa-gjb04", "审计日志记录哪些事件？",
        "审计日志记录用户登录、权限变更。",
        (ev("e-audit", "审计日志记录内容仅包括以下字段：用户登录、权限变更、配置修改。",
            proof="审计日志字段封闭枚举（表头全量列导出）",
            scope_id="doc01:4.2", section="4.2"),))
    proposal = propose_gjb04_audit_field_exclusion(
        request, evidence_id="e-audit", term="数据删除")
    assert proposal.operator_id == "ANSWER-GJB-04-AUDIT-EXCLUSION-V1"
    assert proposal.check_item == "GJB-04"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "closed_list_exclusion"
    assert proposal.answer_after == "审计日志记录用户登录、权限变更、数据删除。"
    assert "配置修改" in proposal.proof
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))
    with pytest.raises(ValueError, match="unproven"):
        propose_gjb04_audit_field_exclusion(
            request, evidence_id="e-audit", term="配置修改")


def test_gjb05_trace_conflict_redirects_explicit_mapping() -> None:
    request = make_gjb05_request()
    proposal = propose_gjb05_trace_conflict(
        request, evidence_id="e-trace", requirement_id="SRS-3.2.1-01",
        mutated_test_id="T-02")
    assert proposal.operator_id == "ANSWER-GJB-05-TRACE-CONFLICT-V1"
    assert proposal.check_item == "GJB-05"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "explicit_trace_mapping_conflict"
    assert proposal.answer_after == "需求SRS-3.2.1-01映射到测试项T-02。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


def test_gjb05_trace_match_is_support_control() -> None:
    request = make_gjb05_request()
    proposal = propose_gjb05_trace_match(
        request, evidence_id="e-trace", requirement_id="SRS-3.2.1-01")
    assert proposal.operator_id == "ANSWER-GJB-05-TRACE-MATCH-V1"
    assert proposal.check_item == "GJB-05"
    assert proposal.gold_candidate == "support"
    assert proposal.proof_kind == "explicit_trace_mapping_match"
    assert proposal.answer_after == request.answer
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


def test_gjb05_rejects_source_answer_contradicting_the_trace_table() -> None:
    request = make_gjb05_request(answer="需求SRS-3.2.1-01映射到测试项T-02。")
    with pytest.raises(ValueError, match="source answer"):
        propose_gjb05_trace_conflict(
            request, evidence_id="e-trace", requirement_id="SRS-3.2.1-01",
            mutated_test_id="T-03")


def test_gjb05_rejects_mutation_equal_to_evidenced_mapping() -> None:
    request = make_gjb05_request()
    with pytest.raises(ValueError, match="differ from the evidenced mapping"):
        propose_gjb05_trace_conflict(
            request, evidence_id="e-trace", requirement_id="SRS-3.2.1-01",
            mutated_test_id="T-01")


@pytest.mark.parametrize("mutated_test_id", ["9项", "测试项T-9", ""])
def test_gjb05_rejects_invalid_mutated_test_id(mutated_test_id: str) -> None:
    request = make_gjb05_request()
    with pytest.raises(ValueError, match="test-item identifier"):
        propose_gjb05_trace_conflict(
            request, evidence_id="e-trace", requirement_id="SRS-3.2.1-01",
            mutated_test_id=mutated_test_id)


def test_gjb05_rejects_question_and_evidence_without_the_requirement() -> None:
    request = make_gjb05_request(question="系统包含哪些测试项？")
    with pytest.raises(ValueError, match="question does not mention"):
        propose_gjb05_trace_conflict(
            request, evidence_id="e-trace", requirement_id="SRS-3.2.1-01",
            mutated_test_id="T-02")
    other = make_gjb05_request(
        evidence_text="需求追溯表：SRS-3.2.1-03→测试项T-01；SRS-3.2.1-02→测试项T-02。")
    with pytest.raises(ValueError, match="mapping"):
        propose_gjb05_trace_match(
            other, evidence_id="e-trace", requirement_id="SRS-3.2.1-01")


def test_gjb06_alarm_element_exclusion_is_refuted_by_closed_list() -> None:
    request = make_input(
        "qa-gjb06", "报警信息包含哪些报警要素？",
        "报警信息包括报警级别、报警时间。",
        (ev("e-alarm", "报警要素包括：报警级别、报警时间、报警内容、报警位置。",
            scope_id="doc01:3.7", section="3.7"),))
    proposal = propose_gjb06_alarm_element_exclusion(
        request, evidence_id="e-alarm", term="处置措施")
    assert proposal.operator_id == "ANSWER-GJB-06-ALARM-EXCLUSION-V1"
    assert proposal.check_item == "GJB-06"
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "报警信息包括报警级别、报警时间、处置措施。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


@pytest.mark.parametrize("completeness", ["open", "unknown"])
def test_gjb06_open_alarm_evidence_never_refutes(completeness: str) -> None:
    request = make_input(
        "qa-gjb06-open", "报警信息包含哪些报警要素？",
        "报警信息包括报警级别、报警时间。",
        (ev("e-alarm", "报警要素包括：报警级别、报警时间、报警内容、报警位置。",
            completeness=completeness, scope_id="doc01:3.7", section="3.7"),))
    with pytest.raises(ValueError, match="manual review"):
        propose_gjb06_alarm_element_exclusion(
            request, evidence_id="e-alarm", term="处置措施")


def test_gjb07_self_check_exclusion_is_refuted_by_closed_list() -> None:
    request = make_input(
        "qa-gjb07", "软件自检包括哪些机制？",
        "软件自检机制包括内存自检。",
        (ev("e-selftest", "软件自检机制包括：内存自检、程序校验、看门狗监测。",
            scope_id="doc01:3.3", section="3.3"),))
    proposal = propose_gjb07_self_check_exclusion(
        request, evidence_id="e-selftest", term="磁盘坏道扫描")
    assert proposal.operator_id == "ANSWER-GJB-07-SELFTEST-EXCLUSION-V1"
    assert proposal.check_item == "GJB-07"
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "软件自检机制包括内存自检、磁盘坏道扫描。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


def test_gjb08_power_loss_exclusion_is_refuted_by_closed_list() -> None:
    request = make_input(
        "qa-gjb08", "掉电保护机制保护哪些数据？",
        "掉电保护的数据包括参数配置数据。",
        (ev("e-power", "掉电保护数据仅包括：参数配置数据、任务现场数据。",
            scope_id="doc01:3.5", section="3.5"),))
    proposal = propose_gjb08_power_loss_exclusion(
        request, evidence_id="e-power", term="历史日志数据")
    assert proposal.operator_id == "ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1"
    assert proposal.check_item == "GJB-08"
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "掉电保护的数据包括参数配置数据、历史日志数据。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


def test_gjb08_rejects_open_ended_list_terminated_with_deng() -> None:
    request = make_input(
        "qa-gjb08-deng", "掉电保护机制保护哪些数据？",
        "掉电保护的数据包括参数配置数据。",
        (ev("e-power", "掉电保护数据包括：参数配置数据、任务现场数据等。",
            scope_id="doc01:3.5", section="3.5"),))
    with pytest.raises(ValueError, match="list is open"):
        propose_gjb08_power_loss_exclusion(
            request, evidence_id="e-power", term="历史日志数据")


def test_gjb09_input_validation_exclusion_is_refuted_by_closed_list() -> None:
    request = make_input(
        "qa-gjb09", "系统对输入数据采取哪些校验？",
        "输入数据校验包括格式校验。",
        (ev("e-input", "输入数据校验仅包括以下类型：格式校验、范围校验。",
            scope_id="doc01:3.9", section="3.9"),))
    proposal = propose_gjb09_input_validation_exclusion(
        request, evidence_id="e-input", term="语义校验")
    assert proposal.operator_id == "ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1"
    assert proposal.check_item == "GJB-09"
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "输入数据校验包括格式校验、语义校验。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))
    with pytest.raises(ValueError, match="unproven"):
        propose_gjb09_input_validation_exclusion(
            request, evidence_id="e-input", term="范围校验")


def test_gjb10_rollback_fabrication_is_refuted_by_explicit_negation() -> None:
    request = make_gjb10_request()
    proposal = propose_gjb10_rollback_fabrication(
        request, evidence_id="e-upg", term="回滚")
    assert proposal.operator_id == "ANSWER-GJB-10-ROLLBACK-CONFLICT-V1"
    assert proposal.check_item == "GJB-10"
    assert proposal.gold_candidate == "refute"
    assert proposal.proof_kind == "explicit_negation_conflict"
    assert proposal.answer_after == "软件版本升级失败后重新执行升级，并支持回滚。"
    assert "不支持" in proposal.proof
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


def test_gjb10_rejects_evidence_that_does_not_negate_rollback() -> None:
    request = make_gjb10_request(
        evidence_text="软件版本升级失败后自动回滚至升级前版本。")
    with pytest.raises(ValueError, match="explicitly negate"):
        propose_gjb10_rollback_fabrication(request, evidence_id="e-upg", term="回滚")


def test_gjb10_rejects_term_absent_from_evidence() -> None:
    request = make_gjb10_request()
    with pytest.raises(ValueError, match="does not mention"):
        propose_gjb10_rollback_fabrication(request, evidence_id="e-upg", term="热备切换")


def test_gjb10_rejects_answer_already_claiming_the_term() -> None:
    request = make_gjb10_request(
        answer="软件版本升级失败后重新执行升级并支持回滚。")
    with pytest.raises(ValueError, match="already present"):
        propose_gjb10_rollback_fabrication(request, evidence_id="e-upg", term="回滚")


def test_gjb10_rejects_question_from_another_subject_domain() -> None:
    request = make_gjb10_request(question="系统如何处理通信故障？")
    with pytest.raises(ValueError, match="subject domain"):
        propose_gjb10_rollback_fabrication(request, evidence_id="e-upg", term="回滚")


def test_gjb11_degraded_mode_exclusion_is_refuted_by_closed_list() -> None:
    request = make_input(
        "qa-gjb11", "系统支持哪些降级运行模式？",
        "系统降级运行模式包括功能降级模式。",
        (ev("e-degrade", "降级运行模式仅包括：功能降级模式、性能降级模式。",
            scope_id="doc01:3.10", section="3.10"),))
    proposal = propose_gjb11_degraded_mode_exclusion(
        request, evidence_id="e-degrade", term="静默降级模式")
    assert proposal.operator_id == "ANSWER-GJB-11-DEGRADE-EXCLUSION-V1"
    assert proposal.check_item == "GJB-11"
    assert proposal.gold_candidate == "refute"
    assert proposal.answer_after == "系统降级运行模式包括功能降级模式、静默降级模式。"
    assert_frozen_fields(proposal, request, (request.evidence[0].source_ref,))


def test_gjb11_rejects_evidence_without_explicit_enumeration_marker() -> None:
    request = make_input(
        "qa-gjb11-x", "系统支持哪些降级运行模式？",
        "系统降级运行模式包括功能降级模式。",
        (ev("e-degrade", "系统支持功能降级和性能降级。",
            scope_id="doc01:3.10", section="3.10"),))
    with pytest.raises(ValueError, match="enumeration marker"):
        propose_gjb11_degraded_mode_exclusion(
            request, evidence_id="e-degrade", term="静默降级模式")


def test_context_and_question_hashes_are_deterministic_across_mutations() -> None:
    request = make_gjb02_request()
    first = propose_gjb02_fault_tolerance_exclusion(
        request, evidence_id="e-ft", term="手动切换")
    second = propose_gjb02_fault_tolerance_exclusion(
        request, evidence_id="e-ft", term="双机热备切换")
    assert first.context_hash == second.context_hash
    assert first.question_hash == second.question_hash
    assert first.answer_after != second.answer_after


def test_operator_registry_lists_all_gjb_operators() -> None:
    expected = {
        "ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1",
        "ANSWER-GJB-02-FT-EXCLUSION-V1",
        "ANSWER-GJB-03-ACL-EXCLUSION-V1",
        "ANSWER-GJB-04-AUDIT-EXCLUSION-V1",
        "ANSWER-GJB-05-TRACE-CONFLICT-V1",
        "ANSWER-GJB-05-TRACE-MATCH-V1",
        "ANSWER-GJB-06-ALARM-EXCLUSION-V1",
        "ANSWER-GJB-07-SELFTEST-EXCLUSION-V1",
        "ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1",
        "ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1",
        "ANSWER-GJB-10-ROLLBACK-CONFLICT-V1",
        "ANSWER-GJB-11-DEGRADE-EXCLUSION-V1",
    }
    assert set(GJB_OPERATOR_STATUS) == expected
    assert set(GJB_OPERATOR_STATUS.values()) == {"deterministic_prototype"}


def test_every_gjb_check_item_is_covered_by_at_least_one_operator() -> None:
    covered: dict[str, str] = {}
    cases = [
        ("GJB-01", propose_gjb01_quantifier_fabrication, make_gjb01_request(), dict(
            evidence_id="e-req", rule_evidence_id="e-rule",
            requirement_id="SRS-3.2.1-01", criterion_claim="完成时间不超过200ms")),
        ("GJB-02", propose_gjb02_fault_tolerance_exclusion, make_gjb02_request(), dict(
            evidence_id="e-ft", term="手动切换")),
        ("GJB-03", propose_gjb03_access_control_exclusion, make_input(
            "qa-c03", "系统实现了哪些权限控制？", "系统访问控制包括身份鉴别、权限校验。",
            (ev("e-acl", "系统权限控制仅包括：身份鉴别、权限校验、访问审计。",
                scope_id="doc01:3.6", section="3.6"),)),
         dict(evidence_id="e-acl", term="强制访问控制")),
        ("GJB-04", propose_gjb04_audit_field_exclusion, make_input(
            "qa-c04", "审计日志记录哪些事件？", "审计日志记录用户登录、权限变更。",
            (ev("e-audit", "审计日志记录内容仅包括以下字段：用户登录、权限变更、配置修改。",
                scope_id="doc01:4.2", section="4.2"),)),
         dict(evidence_id="e-audit", term="数据删除")),
        ("GJB-05", propose_gjb05_trace_conflict, make_gjb05_request(), dict(
            evidence_id="e-trace", requirement_id="SRS-3.2.1-01",
            mutated_test_id="T-02")),
        ("GJB-06", propose_gjb06_alarm_element_exclusion, make_input(
            "qa-c06", "报警信息包含哪些报警要素？", "报警信息包括报警级别、报警时间。",
            (ev("e-alarm", "报警要素包括：报警级别、报警时间、报警内容、报警位置。",
                scope_id="doc01:3.7", section="3.7"),)),
         dict(evidence_id="e-alarm", term="处置措施")),
        ("GJB-07", propose_gjb07_self_check_exclusion, make_input(
            "qa-c07", "软件自检包括哪些机制？", "软件自检机制包括内存自检。",
            (ev("e-selftest", "软件自检机制包括：内存自检、程序校验、看门狗监测。",
                scope_id="doc01:3.3", section="3.3"),)),
         dict(evidence_id="e-selftest", term="磁盘坏道扫描")),
        ("GJB-08", propose_gjb08_power_loss_exclusion, make_input(
            "qa-c08", "掉电保护机制保护哪些数据？", "掉电保护的数据包括参数配置数据。",
            (ev("e-power", "掉电保护数据仅包括：参数配置数据、任务现场数据。",
                scope_id="doc01:3.5", section="3.5"),)),
         dict(evidence_id="e-power", term="历史日志数据")),
        ("GJB-09", propose_gjb09_input_validation_exclusion, make_input(
            "qa-c09", "系统对输入数据采取哪些校验？", "输入数据校验包括格式校验。",
            (ev("e-input", "输入数据校验仅包括以下类型：格式校验、范围校验。",
                scope_id="doc01:3.9", section="3.9"),)),
         dict(evidence_id="e-input", term="语义校验")),
        ("GJB-10", propose_gjb10_rollback_fabrication, make_gjb10_request(), dict(
            evidence_id="e-upg", term="回滚")),
        ("GJB-11", propose_gjb11_degraded_mode_exclusion, make_input(
            "qa-c11", "系统支持哪些降级运行模式？", "系统降级运行模式包括功能降级模式。",
            (ev("e-degrade", "降级运行模式仅包括：功能降级模式、性能降级模式。",
                scope_id="doc01:3.10", section="3.10"),)),
         dict(evidence_id="e-degrade", term="静默降级模式")),
    ]
    for check_item, operator, request, kwargs in cases:
        proposal = operator(request, **kwargs)
        assert proposal.check_item == check_item, check_item
        assert proposal.operator_id in GJB_OPERATOR_STATUS, check_item
        assert proposal.gold_candidate in ("support", "refute"), check_item
        assert proposal.proof, check_item
        covered[check_item] = proposal.operator_id
    assert set(covered) == {f"GJB-{i:02d}" for i in range(1, 12)}
