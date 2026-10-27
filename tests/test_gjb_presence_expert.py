"""Tests for the GJB closed-list presence expert (L1, GJB-01~GJB-11)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.gjb_presence_expert import (  # noqa: E402
    CHECK_ITEMS,
    GJB_CHECKS,
    METHOD,
    audit_gjb_presence,
    verify_gjb_presence,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    Completeness,
    QAInput,
    RetrievedEvidence,
    SourceRef,
    SourceType,
)
from algorithms.consistency.qa_router import route_question  # noqa: E402

DOC_ID = "04数据统一访问服务软件需求规格说明-终稿"

SAFETY_TABLE = (
    "<table><tr><td>序号</td><td>安全性需求</td><td>详细说明</td></tr>"
    "<tr><td>1</td><td>故障检测与诊断</td>"
    "<td>系统自检，检测系统中的故障，阻止错误结果的影响</td></tr>"
    "<tr><td>2</td><td>数据库失败重连</td>"
    "<td>数据库连接失败时自动在3s内持续进行重连尝试</td></tr></table>"
)

SECURITY_TABLE = (
    "<table><tr><td>序号</td><td>保密性需求</td><td>详细说明</td></tr>"
    "<tr><td>1</td><td>身份认证</td>"
    "<td>用户使用时需输入正确的用户名和密码</td></tr>"
    "<tr><td>2</td><td>数据库访问控制</td>"
    "<td>在多个用户同时访问数据时，应避免冲突</td></tr></table>"
)

QUALITY_TABLE = (
    "<table><tr><td>序号</td><td>软件质量因素</td>"
    "<td>软件质量因素描述</td><td>要求程度</td><td>采取的措施</td></tr>"
    "<tr><td>1</td><td>可测试性</td><td>易于充分测试的能力</td>"
    "<td>提供量化指标</td><td>测试用例</td></tr></table>"
)

QUALIFICATION_TABLE = (
    "<table><tr><td>需求名称/标识</td><td>本文档的章节号</td>"
    "<td>合格性方法</td><td>合格性级别</td></tr>"
    "<tr><td>SQL访问</td><td>3.2.1</td><td>A、B、D</td><td>a、b</td></tr>"
    "</table>"
)

TRACE_TABLE = (
    "<table><thead><tr>"
    "<th><p><strong>软件研制任务书名称/标识</strong></p></th>"
    "<th><p><strong>软件研制任务书的章节号</strong></p></th>"
    "<th><p><strong>本文档的名称/标识</strong></p></th>"
    "<th><p><strong>本文档的章节号</strong></p></th>"
    "<th><p><strong>跟踪说明</strong></p></th></tr></thead><tbody>"
    "<tr><td><p>对象化数据访问</p></td><td><p>4.1.1 a)</p></td>"
    "<td><p>对象化访问</p></td><td><p>3.2.2</p></td><td></td></tr>"
    "</tbody></table>"
)

GJB_CLAUSE_TEXT = (
    "系统提供完整的审计日志记录功能，关键操作与参数修改均记录审计日志。"
    "设备掉电时应自动保存关键配置与任务状态，掉电恢复后继续运行。"
    "外部输入需进行输入校验，非法报文与越界参数应被拦截。"
    "软件升级前应校验升级包完整性，升级失败时自动回滚到原版本。"
    "系统定义了分级降级运行策略，故障时按级降级运行。"
    "告警信息包含时间戳、故障位置、故障等级与处置建议。"
)

CAPABILITY_TABLE = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>SQL访问功能</p></td>"
    "<td><p>PZXQ-GN-SQLFW</p></td>"
    "<td><p>提供原生SQL访问功能，提供数据库连接、关闭功能。</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段</p></td><td><p>4.1.1；4.2</p></td></tr>"
    "</tbody></table>"
)

STATE_TEXT = "3.1 要求的状态和方式：本软件只有一个运行状态。"


def _block(evidence_id: str, text: str, source_type: SourceType,
           completeness: Completeness = "open") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id,
        text=text,
        source_type=source_type,
        source_ref=SourceRef(doc_id=DOC_ID),
        scope_id=f"{DOC_ID}:{evidence_id}",
        completeness=completeness,
    )


def full_gjb_blocks(completeness: Completeness = "open",
                    ) -> list[RetrievedEvidence]:
    return [
        _block("ev-t1", SAFETY_TABLE, "table", completeness),
        _block("ev-t2", SECURITY_TABLE, "table", completeness),
        _block("ev-t3", QUALITY_TABLE, "table", completeness),
        _block("ev-t4", QUALIFICATION_TABLE, "table", completeness),
        _block("ev-t5", TRACE_TABLE, "table", completeness),
        _block("ev-t6", GJB_CLAUSE_TEXT, "text", completeness),
        _block("ev-t7", CAPABILITY_TABLE, "table", completeness),
    ]


def minimal_blocks(completeness: Completeness = "open",
                   ) -> list[RetrievedEvidence]:
    return [
        _block("ev-m1", CAPABILITY_TABLE, "table", completeness),
        _block("ev-m2", STATE_TEXT, "text", completeness),
    ]


def gjb_request(answer: str, blocks: list[RetrievedEvidence],
                question: str = "系统如何处理异常情况？") -> QAInput:
    return QAInput(
        instance_id="qa-gjb",
        question=question,
        answer=answer,
        context_freeze_id="frozen-gjb-1",
        evidence=tuple(blocks),
    )


def test_checklist_matches_taxonomy_and_rule_library() -> None:
    taxonomy = json.loads(
        (BASE / "knowledge/consistency_taxonomy_v3.json").read_text(
            encoding="utf-8"))
    taxonomy_gjb = {item["id"]: item["name"] for item in taxonomy["items"]
                    if str(item.get("id", "")).startswith("GJB")}
    assert set(taxonomy_gjb) == set(CHECK_ITEMS)
    rules = json.loads(
        (BASE / "knowledge/gjb_438c_rules_full.json").read_text(
            encoding="utf-8"))
    rule_ids = {rule["rule_id"] for rule in rules["rules"]}
    assert len(GJB_CHECKS) == 11
    for check in GJB_CHECKS:
        assert check.name == taxonomy_gjb[check.check_id]
        assert check.components
        assert check.answer_triggers
        assert check.rule_ids and set(check.rule_ids) <= rule_ids
        for component in check.components:
            assert component.table_keywords or component.pattern is not None


def test_audit_full_fixture_all_checks_present() -> None:
    blocks = full_gjb_blocks()
    audit = audit_gjb_presence(tuple(blocks),
                               linearize_context(tuple(blocks)))
    assert len(audit.checks) == 11
    assert all(audit.is_present for audit in audit.checks)
    assert audit.diagnostics() == ()
    by_id = audit.by_check_id()
    assert by_id["GJB-01"].evidence_refs == ("ev-t3", "ev-t4")
    assert by_id["GJB-01"].present == ("合格性规定", "质量因素")
    assert by_id["GJB-02"].evidence_refs == ("ev-t1",)
    assert by_id["GJB-03"].evidence_refs == ("ev-t2",)
    assert by_id["GJB-04"].evidence_refs == ("ev-t6",)
    assert by_id["GJB-05"].evidence_refs == ("ev-t5",)
    assert by_id["GJB-06"].evidence_refs == ("ev-t6",)
    assert by_id["GJB-07"].evidence_refs == ("ev-t1",)
    assert by_id["GJB-08"].evidence_refs == ("ev-t6",)
    assert by_id["GJB-09"].evidence_refs == ("ev-t6",)
    assert by_id["GJB-10"].evidence_refs == ("ev-t6",)
    assert by_id["GJB-11"].evidence_refs == ("ev-t6",)


def test_audit_minimal_fixture_all_checks_absent() -> None:
    blocks = minimal_blocks()
    audit = audit_gjb_presence(tuple(blocks))
    assert all(audit.is_absent for audit in audit.checks)
    assert all(audit.evidence_refs == () for audit in audit.checks)
    diagnostics = audit.diagnostics()
    assert len(diagnostics) == 11
    assert diagnostics[0].startswith("GJB-01")
    by_id = audit.by_check_id()
    assert by_id["GJB-04"].missing == ("审计日志条款",)
    assert by_id["GJB-08"].missing == ("掉电保护条款",)


def test_audit_reports_partial_component_state() -> None:
    blocks = [block for block in full_gjb_blocks()
              if block.evidence_id != "ev-t4"]
    audit = audit_gjb_presence(tuple(blocks))
    state = audit.by_check_id()["GJB-01"]
    assert state.present == ("质量因素",)
    assert state.missing == ("合格性规定",)
    assert not state.is_present
    assert not state.is_absent


def test_table_signature_matches_header_only_not_body() -> None:
    body_only_table = (
        "<table><tr><td>序号</td><td>说明</td></tr>"
        "<tr><td>1</td><td>本文档需求与任务书需求存在对应关系</td></tr>"
        "</table>"
    )
    blocks = [_block("ev-s1", body_only_table, "table")]
    audit = audit_gjb_presence(tuple(blocks))
    assert audit.by_check_id()["GJB-05"].is_absent
    with_header = [_block("ev-s2", TRACE_TABLE, "table")]
    assert audit_gjb_presence(tuple(with_header)).by_check_id()[
        "GJB-05"].is_present


def test_short_text_block_matched_via_raw_fallback() -> None:
    blocks = [_block("ev-s3", "提供自检。", "text")]
    audit = audit_gjb_presence(tuple(blocks))
    assert audit.by_check_id()["GJB-07"].is_present
    assert audit.by_check_id()["GJB-07"].evidence_refs == ("ev-s3",)


def test_answer_presence_claim_supported_with_refs() -> None:
    blocks = full_gjb_blocks()
    request = gjb_request("系统提供完整的审计日志记录功能。", blocks)
    results = verify_gjb_presence(request)
    assert len(results) == 1
    claim = results[0]
    assert claim.verdict == "support"
    assert claim.check_item_candidates == ("GJB-04",)
    assert claim.evidence_refs == ("ev-t6",)
    assert claim.method == METHOD
    assert claim.confidence == 0.9
    assert claim.claim_id == "qa-gjb-gjb01"
    assert claim.claim_text == "系统提供完整的审计日志记录功能。"
    assert "审计日志" in claim.rationale


def test_answer_presence_claim_missing_refuted() -> None:
    request = gjb_request("系统提供完整的审计日志记录功能。",
                          minimal_blocks())
    results = verify_gjb_presence(request)
    assert len(results) == 1
    claim = results[0]
    assert claim.verdict == "refute"
    assert claim.evidence_refs == ()
    assert claim.confidence == 0.9
    assert "封闭清单" in claim.rationale
    assert "审计日志条款" in claim.rationale


def test_answer_presence_claim_about_document_table() -> None:
    request = gjb_request("本文档包含合格性规定表，每条需求都注明了合格性方法。",
                          full_gjb_blocks())
    results = verify_gjb_presence(request)
    assert len(results) == 1
    claim = results[0]
    assert claim.check_item_candidates == ("GJB-01",)
    assert claim.verdict == "support"
    assert claim.evidence_refs == ("ev-t3", "ev-t4")


def test_answer_absence_claim_refuted_when_evidence_present() -> None:
    request = gjb_request("本文档没有掉电保护条款。", full_gjb_blocks())
    results = verify_gjb_presence(request)
    assert len(results) == 1
    claim = results[0]
    assert claim.verdict == "refute"
    assert claim.evidence_refs == ("ev-t6",)
    assert "与证据矛盾" in claim.rationale


def test_answer_absence_claim_nie_on_open_context() -> None:
    request = gjb_request("文档缺少掉电保护条款。", minimal_blocks())
    results = verify_gjb_presence(request)
    assert len(results) == 1
    claim = results[0]
    assert claim.verdict == "not_in_evidence"
    assert claim.confidence == 0.0
    assert claim.evidence_refs == ()
    assert "completeness非closed" in claim.rationale


def test_answer_absence_claim_supported_on_closed_context() -> None:
    request = gjb_request("文档缺少掉电保护条款。",
                          minimal_blocks(completeness="closed"))
    results = verify_gjb_presence(request)
    assert len(results) == 1
    assert results[0].verdict == "support"
    assert "completeness=closed" in results[0].rationale


def test_answer_without_gjb_content_returns_empty() -> None:
    request = gjb_request("系统响应时间为200ms，查询1000条数据的时间应小于1s。",
                          full_gjb_blocks())
    assert verify_gjb_presence(request) == []


def test_rhetorical_gjb_mention_without_assertion_returns_empty() -> None:
    answer = ("该用例能够有效检测和报告连接过程中的潜在问题，"
              "从而提高系统的整体可靠性和容错能力。")
    request = gjb_request(answer, minimal_blocks())
    assert verify_gjb_presence(request) == []


def test_question_routed_but_answer_silent_returns_empty() -> None:
    question = "软件的可测试性如何保证？"
    assert "GJB-01" in route_question(question)
    request = gjb_request("通过覆盖全部功能的测试用例来保证。",
                          full_gjb_blocks(), question=question)
    assert verify_gjb_presence(request) == []


def test_claims_deduped_per_check_and_polarity() -> None:
    answer = ("系统提供审计日志功能。文档还包含审计日志条款，记录参数修改。"
              "但系统缺少掉电保护条款。")
    request = gjb_request(answer, full_gjb_blocks())
    results = verify_gjb_presence(request)
    assert len(results) == 2
    by_check = {result.check_item_candidates[0]: result
                for result in results}
    assert set(by_check) == {"GJB-04", "GJB-08"}
    assert by_check["GJB-04"].verdict == "support"
    assert by_check["GJB-04"].claim_text == "系统提供审计日志功能。"
    assert by_check["GJB-08"].verdict == "refute"
    assert len({result.claim_id for result in results}) == 2


def test_negation_adjacency_detected_as_absence_claim() -> None:
    request = gjb_request("系统无掉电保护需求。", minimal_blocks())
    results = verify_gjb_presence(request)
    assert len(results) == 1
    assert results[0].verdict == "not_in_evidence"


def test_empty_evidence_presence_refuted_absence_nie() -> None:
    presence = gjb_request("系统提供审计日志记录功能。", [])
    results = verify_gjb_presence(presence)
    assert [result.verdict for result in results] == ["refute"]
    absence = gjb_request("文档缺少审计日志条款。", [])
    results = verify_gjb_presence(absence)
    assert [result.verdict for result in results] == ["not_in_evidence"]


def test_verify_is_deterministic() -> None:
    request = gjb_request(
        "系统提供审计日志功能，且具备掉电保护与降级运行能力。",
        full_gjb_blocks())
    first = verify_gjb_presence(request)
    second = verify_gjb_presence(request)
    assert first == second
    assert [result.verdict for result in first] == ["support", "support",
                                                    "support"]
    assert [result.check_item_candidates for result in first] == [
        ("GJB-04",), ("GJB-08",), ("GJB-11",)]


def doc04_evidence() -> tuple[RetrievedEvidence, ...]:
    paths = list((BASE / "data/gjb_438c/mineru_standard").glob(
        "04*/office/*_content_list.json"))
    assert len(paths) == 1
    items = json.loads(paths[0].read_text(encoding="utf-8"))
    blocks: list[RetrievedEvidence] = []
    for index, item in enumerate(items):
        if item.get("type") == "table":
            text = str(item.get("table_body", ""))
            source_type: SourceType = "table"
        elif item.get("type") == "text":
            text = str(item.get("text", ""))
            source_type = "text"
        else:
            continue
        if not text.strip():
            continue
        blocks.append(RetrievedEvidence(
            evidence_id=f"ev-item{index:03d}",
            text=text,
            source_type=source_type,
            source_ref=SourceRef(doc_id=DOC_ID),
            scope_id=f"{DOC_ID}:item{index:03d}",
            completeness="open",
        ))
    return tuple(blocks)


def test_real_doc04_audit_matches_taxonomy_annotations() -> None:
    blocks = doc04_evidence()
    assert len(blocks) > 300
    audit = audit_gjb_presence(blocks)
    present = {audit.check_id for audit in audit.checks if audit.is_present}
    absent = {audit.check_id for audit in audit.checks if audit.is_absent}
    assert present == {"GJB-01", "GJB-02", "GJB-03", "GJB-05", "GJB-07"}
    assert absent == {"GJB-04", "GJB-06", "GJB-08", "GJB-09", "GJB-10",
                      "GJB-11"}
    by_id = audit.by_check_id()
    assert "ev-item368" in by_id["GJB-01"].evidence_refs
    assert "ev-item404" in by_id["GJB-01"].evidence_refs
    assert by_id["GJB-02"].evidence_refs == ("ev-item341",)
    assert by_id["GJB-03"].evidence_refs == ("ev-item345",)
    assert by_id["GJB-07"].evidence_refs == ("ev-item341",)
    assert "ev-item407" in by_id["GJB-05"].evidence_refs
    assert "ev-item408" in by_id["GJB-05"].evidence_refs
    diagnostics = audit.diagnostics()
    assert len(diagnostics) == 6
    assert diagnostics[0].startswith("GJB-04")
    assert by_id["GJB-08"].missing == ("掉电保护条款",)
    assert by_id["GJB-10"].missing == ("升级安全条款",)


def test_real_doc04_answer_claims() -> None:
    blocks = doc04_evidence()

    supported = gjb_request("系统具备数据库失败重连与故障检测能力。",
                            list(blocks))
    results = verify_gjb_presence(supported)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].check_item_candidates == ("GJB-02",)
    assert results[0].evidence_refs == ("ev-item341",)

    refuted = gjb_request("本文档规定了掉电保护需求。", list(blocks))
    results = verify_gjb_presence(refuted)
    assert [result.verdict for result in results] == ["refute"]
    assert results[0].check_item_candidates == ("GJB-08",)

    upgrade = gjb_request("软件升级失败时，系统自动回滚到原版本。",
                          list(blocks))
    results = verify_gjb_presence(upgrade)
    assert [result.verdict for result in results] == ["refute"]
    assert results[0].check_item_candidates == ("GJB-10",)

    absent = gjb_request("文档缺少掉电保护条款。", list(blocks))
    results = verify_gjb_presence(absent)
    assert [result.verdict for result in results] == ["not_in_evidence"]


def load_frozen_rows() -> list[dict]:
    path = (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def frozen_request(row: dict, answer: str | None = None) -> QAInput:
    evidence = tuple(
        RetrievedEvidence(
            evidence_id=block["evidence_id"],
            text=block["text"],
            source_type=block["source_type"],
            source_ref=SourceRef(**block["source_ref"]),
            scope_id=block["scope_id"],
            completeness=block.get("completeness", "unknown"),
        ) for block in row["evidence"])
    return QAInput(
        instance_id=row["instance_id"],
        question=row["question"],
        answer=answer if answer is not None else row["answer"],
        context_freeze_id=row["context_freeze_id"],
        evidence=evidence,
    )


def test_real_frozen_scene1_emits_no_audit_noise() -> None:
    rows = load_frozen_rows()
    assert len(rows) == 91
    for row in rows:
        assert verify_gjb_presence(frozen_request(row)) == []


def test_real_frozen_s1qa086_trace_table_audit_and_claim() -> None:
    rows = load_frozen_rows()
    row = next(item for item in rows if item["instance_id"] == "S1QA-086")
    request = frozen_request(row)
    audit = audit_gjb_presence(request.evidence)
    present = {audit.check_id for audit in audit.checks if audit.is_present}
    assert present == {"GJB-05"}
    assert audit.by_check_id()["GJB-05"].evidence_refs == (
        "S1QA-086-ev-000408",)
    claiming = frozen_request(
        row, answer="本文档包含需求追溯表，需求可追踪到任务书。")
    results = verify_gjb_presence(claiming)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].check_item_candidates == ("GJB-05",)
    assert results[0].evidence_refs == ("S1QA-086-ev-000408",)


def test_real_frozen_s1qa001_overview_mention_is_not_a_clause() -> None:
    rows = load_frozen_rows()
    row = next(item for item in rows if item["instance_id"] == "S1QA-001")
    audit = audit_gjb_presence(frozen_request(row).evidence)
    assert audit.by_check_id()["GJB-04"].is_absent
    claiming = frozen_request(row, answer="系统提供访问审计以及日志记录功能。")
    results = verify_gjb_presence(claiming)
    assert [result.verdict for result in results] == ["refute"]
    assert results[0].check_item_candidates == ("GJB-04",)
