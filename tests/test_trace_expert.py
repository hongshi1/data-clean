"""Tests for the GJB-05 trace table bidirectional join expert (L1)."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.trace_expert import (  # noqa: E402
    METHOD,
    load_doc_sections,
    parse_trace_tables,
    sections_from_content_list,
    verify_trace,
)

DOC_ID = "04数据统一访问服务软件需求规格说明-终稿"

FORWARD_TABLE = (
    "<table><thead><tr>"
    "<th><p><strong>软件研制任务书名称/标识</strong></p></th>"
    "<th><p><strong>软件研制任务书的章节号</strong></p></th>"
    "<th><p><strong>本文档的名称/标识</strong></p></th>"
    "<th><p><strong>本文档的章节号</strong></p></th>"
    "<th><p><strong>跟踪说明</strong></p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>对象化数据访问</p></td><td><p>4.1.1 a)</p></td>"
    "<td><p>对象化访问</p></td><td><p>3.2.2</p></td><td></td></tr>"
    "<tr><td><p>原生SQL访问</p></td><td><p>4.1.1 b）</p></td>"
    "<td><p>SQL访问</p></td><td><p>3.2.1</p></td><td></td></tr>"
    "<tr><td><p>代码生成</p></td><td><p>4.1.1 c)</p></td>"
    "<td><p>代码生成</p></td><td><p>3.2.4</p></td><td></td></tr>"
    "<tr><td><p>访问审计及日志记录</p></td><td><p>4.1.2 d)</p></td>"
    "<td><p>获取错误信息</p></td><td><p>3.2.1.7</p></td><td></td></tr>"
    "<tr><td><p>接口</p></td><td><p>4.5</p></td>"
    "<td><p>CSCI外部接口需求、CSCI内部接口需求</p></td>"
    "<td><p>3.3、3.4</p></td><td><p>不追踪</p></td></tr>"
    "<tr><td><p>性能</p></td><td><p>4.2</p></td><td></td><td></td>"
    "<td><p>不追踪</p></td></tr>"
    "</tbody></table>"
)

REVERSE_TABLE = (
    "<table><thead><tr>"
    "<th><p><strong>本文档名称/标识</strong></p></th>"
    "<th><p><strong>本文档的章节号</strong></p></th>"
    "<th><p><strong>软件研制任务书名称/标识</strong></p></th>"
    "<th><p><strong>软件研制任务书的章节号</strong></p></th>"
    "<th><p><strong>跟踪说明</strong></p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>对象化访问</p></td><td><p>3.2.2</p></td>"
    "<td><p>对象化数据访问</p></td><td><p>4.1.1 a)</p></td><td></td></tr>"
    "<tr><td><p>代码生成</p></td><td><p>3.2.4</p></td>"
    "<td><p>对象化数据访问</p></td><td><p>4.1.1 a)</p></td><td></td></tr>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td>"
    "<td><p>原生SQL访问</p></td><td><p>4.1.1 b)</p></td><td></td></tr>"
    "</tbody></table>"
)

DOC_SECTIONS = frozenset({
    "1", "3", "3.2", "3.2.1", "3.2.1.1", "3.2.1.3.1.2", "3.2.2", "3.2.3",
    "3.2.4", "3.2.5", "3.2.6", "3.3", "3.4", "3.9", "3.10",
})


def trace_request(answer: str, forward: str = FORWARD_TABLE,
                  reverse: str = REVERSE_TABLE) -> QAInput:
    evidence = []
    for evidence_id, text, block in (
            ("ev-b407", forward, "block-000407"),
            ("ev-b408", reverse, "block-000408")):
        if text:
            evidence.append(RetrievedEvidence(
                evidence_id=evidence_id,
                text=text,
                source_type="table",
                source_ref=SourceRef(doc_id=DOC_ID, section="5 需求可追踪性",
                                     block_id=block),
                scope_id=f"{DOC_ID}:{block}",
                completeness="open",
            ))
    return QAInput(
        instance_id="qa-trace",
        question="代码生成功能对应任务书的哪个章节？",
        answer=answer,
        context_freeze_id="frozen-trace-1",
        evidence=tuple(evidence),
    )


def by_claim_prefix(results, prefix: str):
    return [r for r in results if r.claim_text.startswith(prefix)]


def test_bidirectional_contradiction_is_detected() -> None:
    results = verify_trace(trace_request("该问题与追踪无关。"), DOC_SECTIONS)
    contradictions = by_claim_prefix(results, "表81与表82对本文档章节")
    assert len(contradictions) == 1
    claim = contradictions[0]
    assert claim.verdict == "refute"
    assert "3.2.4" in claim.claim_text
    assert "4.1.1 c)" in claim.rationale
    assert "4.1.1 a)" in claim.rationale
    assert claim.method == METHOD
    assert claim.check_item_candidates == ("GJB-05",)
    assert claim.evidence_refs == ("ev-b407", "ev-b408")
    assert claim.confidence == 1.0
    assert claim.claim_id.startswith("qa-trace-")


def test_consistent_anchors_and_paren_width_do_not_fire() -> None:
    results = verify_trace(trace_request("该问题与追踪无关。"), DOC_SECTIONS)
    contradictions = by_claim_prefix(results, "表81与表82对本文档章节")
    assert [c.claim_text for c in contradictions] == [
        "表81与表82对本文档章节3.2.4的任务书追踪映射一致"]
    rationale = contradictions[0].rationale
    assert "3.2.1" not in rationale and "3.2.2" not in rationale


def test_anchor_validity_missing_section_is_refuted() -> None:
    results = verify_trace(trace_request("该问题与追踪无关。"), DOC_SECTIONS)
    anchors = [r for r in results if "存在" in r.claim_text
               and r.claim_text.startswith("表81")]
    assert len(anchors) == 1
    claim = anchors[0]
    assert claim.verdict == "refute"
    assert "3.2.1.7" in claim.claim_text
    assert "row4" in claim.rationale
    assert "获取错误信息" in claim.rationale
    assert claim.evidence_refs == ("ev-b407",)
    assert claim.confidence == 0.95


def test_same_row_contradiction_is_refuted() -> None:
    results = verify_trace(trace_request("该问题与追踪无关。"), DOC_SECTIONS)
    same_row = [r for r in results if "自洽" in r.claim_text]
    assert len(same_row) == 1
    claim = same_row[0]
    assert claim.verdict == "refute"
    assert "不追踪" in claim.claim_text
    assert "row5" in claim.rationale
    assert "4.5" in claim.rationale
    assert "3.3" in claim.rationale and "3.4" in claim.rationale
    assert claim.evidence_refs == ("ev-b407",)


def test_evidence_without_trace_tables_returns_empty() -> None:
    request = QAInput(
        instance_id="qa-no-table",
        question="系统的运行状态有哪些？",
        answer="系统只有一个运行状态。",
        context_freeze_id="frozen-2",
        evidence=(RetrievedEvidence(
            evidence_id="e1",
            text="3.1 要求的状态和方式：本软件只有一个运行状态。",
            source_type="text",
            source_ref=SourceRef(doc_id=DOC_ID, section="3.1"),
            scope_id=f"{DOC_ID}:3.1",
        ),),
    )
    assert verify_trace(request, DOC_SECTIONS) == []
    assert verify_trace(request) == []


def test_answer_trace_claim_refuted_under_bidirectional_contradiction() -> None:
    for answer in ("代码生成（3.2.4）对应任务书4.1.1 c)。",
                   "代码生成（3.2.4）对应任务书4.1.1 a)。"):
        results = verify_trace(trace_request(answer), DOC_SECTIONS)
        answer_claims = by_claim_prefix(results, "代码生成")
        assert len(answer_claims) == 1
        claim = answer_claims[0]
        assert claim.verdict == "refute"
        assert "无论answer取哪一侧" in claim.rationale
        assert claim.method == METHOD


def test_answer_trace_claim_supported_when_both_tables_agree() -> None:
    results = verify_trace(
        trace_request("对象化访问（3.2.2）对应任务书4.1.1 a)。"), DOC_SECTIONS)
    answer_claims = by_claim_prefix(results, "对象化访问")
    assert len(answer_claims) == 1
    assert answer_claims[0].verdict == "support"
    assert answer_claims[0].confidence == 1.0


def test_answer_trace_claim_support_survives_paren_width_variance() -> None:
    results = verify_trace(
        trace_request("SQL访问（3.2.1）对应任务书4.1.1 b)。"), DOC_SECTIONS)
    answer_claims = by_claim_prefix(results, "SQL访问")
    assert len(answer_claims) == 1
    assert answer_claims[0].verdict == "support"


def test_answer_trace_claim_refuted_when_tables_agree_on_other_target() -> None:
    results = verify_trace(
        trace_request("对象化访问（3.2.2）对应任务书4.1.2 b)。"), DOC_SECTIONS)
    answer_claims = by_claim_prefix(results, "对象化访问")
    assert len(answer_claims) == 1
    assert answer_claims[0].verdict == "refute"
    assert "4.1.1 a)" in answer_claims[0].rationale


def test_answer_without_trace_relation_adds_no_claims() -> None:
    results = verify_trace(trace_request("系统响应时间为200ms。"), DOC_SECTIONS)
    assert len(results) == 3
    assert all(r.claim_id for r in results)
    assert len({r.claim_id for r in results}) == 3


def test_single_table_evidence_degrades_gracefully() -> None:
    request = trace_request("该问题与追踪无关。", reverse="")
    results = verify_trace(request, DOC_SECTIONS)
    assert by_claim_prefix(results, "表81与表82对本文档章节") == []
    assert len(results) == 2
    partial = trace_request("代码生成（3.2.4）对应任务书4.1.1 a)。", reverse="")
    results = verify_trace(partial, DOC_SECTIONS)
    answer_claims = by_claim_prefix(results, "代码生成")
    assert len(answer_claims) == 1
    assert answer_claims[0].verdict == "not_in_evidence"


def test_parse_trace_tables_normalizes_and_localizes() -> None:
    tables = parse_trace_tables(trace_request("无关。").evidence)
    forward = {m.row_index: m for m in tables.forward}
    assert forward[2].tb_section == "4.1.1 b)"
    assert forward[3].doc_section == "3.2.4"
    assert forward[5].note == "不追踪"
    assert len(tables.forward) == 6  # row5 (3.3、3.4) explodes into two pairs
    assert all(m.direction == "forward" for m in tables.forward)
    assert all(m.direction == "reverse" for m in tables.reverse)
    assert all(m.evidence_id in ("ev-b407", "ev-b408")
               for m in tables.all_mappings)


def real_trace_fixture() -> tuple[QAInput, frozenset[str]]:
    paths = list((BASE / "data/gjb_438c/mineru_standard").glob(
        "04*/office/*_content_list.json"))
    assert len(paths) == 1
    items = json.loads(paths[0].read_text(encoding="utf-8"))
    sections = load_doc_sections(paths[0])
    evidence = tuple(
        RetrievedEvidence(
            evidence_id=f"ev-item{index:03d}",
            text=item["table_body"],
            source_type="table",
            source_ref=SourceRef(
                doc_id=DOC_ID, section="5 需求可追踪性",
                block_id=f"block-{index:06d}"),
            scope_id=f"{DOC_ID}:block-{index:06d}",
            completeness="open",
        )
        for index, item in enumerate(items)
        if item.get("type") == "table"
    )
    request = QAInput(
        instance_id="S1QA-trace",
        question="代码生成功能对应任务书的哪个章节？",
        answer="代码生成功能（3.2.4）对应任务书4.1.1 c)。",
        context_freeze_id="frozen-real-trace",
        evidence=evidence,
    )
    return request, sections


def test_real_doc04_sections_extracted_from_content_list() -> None:
    request, sections = real_trace_fixture()
    assert "3.2.1.3.1.2" in sections
    assert "3.2.1.7" not in sections
    assert len(sections) >= 90
    items = json.loads(list((BASE / "data/gjb_438c/mineru_standard").glob(
        "04*/office/*_content_list.json"))[0].read_text(encoding="utf-8"))
    assert sections == sections_from_content_list(items)


def test_real_doc04_trace_tables_yield_three_known_violations() -> None:
    request, sections = real_trace_fixture()
    results = verify_trace(request, sections)
    contradictions = by_claim_prefix(results, "表81与表82对本文档章节")
    assert len(contradictions) == 1
    claim = contradictions[0]
    assert "3.2.4" in claim.claim_text
    assert "row11" in claim.rationale and "row12" in claim.rationale
    assert "4.1.1 c)" in claim.rationale and "4.1.1 a)" in claim.rationale
    assert claim.evidence_refs == ("ev-item407", "ev-item408")

    anchors = [r for r in results if "存在" in r.claim_text
               and r.claim_text.startswith("表81")]
    assert len(anchors) == 1
    assert "3.2.1.7" in anchors[0].claim_text
    assert "row16" in anchors[0].rationale

    same_row = [r for r in results if "自洽" in r.claim_text]
    assert len(same_row) == 1
    assert "row20" in same_row[0].rationale
    assert "不追踪" in same_row[0].rationale
    assert "接口" in same_row[0].rationale

    answer_claims = by_claim_prefix(results, "代码生成")
    assert len(answer_claims) == 1
    assert answer_claims[0].verdict == "refute"
    assert all(r.method == METHOD for r in results)


def test_real_doc04_consistent_anchor_supported_answer() -> None:
    request, sections = real_trace_fixture()
    request = replace(request, answer="对象化访问（3.2.2）对应任务书4.1.1 a)。")
    results = verify_trace(request, sections)
    answer_claims = by_claim_prefix(results, "对象化访问")
    assert len(answer_claims) == 1
    assert answer_claims[0].verdict == "support"
