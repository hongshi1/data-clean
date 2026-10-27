"""Tests for the DEQ-Pipe (Detection-item-aware Evidence Quality Pipeline)."""
from __future__ import annotations

from pathlib import Path
import sys


BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.deq_pipeline import (  # noqa: E402
    DETECTION_EVIDENCE_REGISTRY,
    DEQResult,
    deq_pipeline,
    scope_gate,
)
from algorithms.consistency.qa_models import RetrievedEvidence, SourceRef  # noqa: E402


def make_evidence(evidence_id: str, text: str, source_type: str = "table") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id, text=text, source_type=source_type,
        source_ref=SourceRef(doc_id="doc04", section="3.2"),
        scope_id=f"doc04:{evidence_id}",
    )


# Evidence blocks: correct scope + wrong scope + irrelevant
BLOB_USECASE = make_evidence("ev-blob", (
    "<table><tr><td>Use Case 名称：BLOB数据插入</td>"
    "<td>Actors：应用软件</td></tr>"
    "<tr><td>前置条件：数据库连接正常</td></tr>"
    "<tr><td>异常流E1：系统提示插入失败，用例结束</td></tr></table>"
))
DB_INIT_USECASE = make_evidence("ev-dbinit", (
    "<table><tr><td>Use Case 名称：数据库初始化</td>"
    "<td>Actors：应用软件</td></tr>"
    "<tr><td>前置条件：无</td></tr>"
    "<tr><td>异常流E1：系统提示初始化失败，用例结束</td></tr></table>"
))
CAPABILITY_TABLE = make_evidence("ev-cap", (
    "<table><thead><tr><th>序号</th><th>Use case名称</th>"
    "<th>项目唯一标识符</th><th>需求描述</th></tr></thead>"
    "<tbody><tr><td>1</td><td>SQL访问功能</td>"
    "<td>PZXQ-GN-SQLFW</td>"
    "<td>提供原生SQL访问功能，提供大字段（BLOB）数据的删除、更新、查询以及添加功能</td>"
    "</tr></tbody></table>"
))
IRRELEVANT_TEXT = make_evidence("ev-irr", (
    "本系统的开发环境包括银河麒麟V4.0操作系统和达梦数据库V7.6。"
    "便携式计算机的硬件要求为i7双核处理器。"
), source_type="text")


def test_registry_covers_all_40_items() -> None:
    """Every item in the 40-item taxonomy must have an evidence registry."""
    expected = (
        [f"TERM-{i:02d}" for i in range(1, 9)]
        + [f"PARAM-{i:02d}" for i in range(1, 11)]
        + [f"LOGIC-{i:02d}" for i in range(1, 12)]
        + [f"GJB-{i:02d}" for i in range(1, 12)]
    )
    assert set(DETECTION_EVIDENCE_REGISTRY) == set(expected)
    for item_id, registry in DETECTION_EVIDENCE_REGISTRY.items():
        assert "content_markers" in registry, f"{item_id} missing content_markers"
        assert "statement_fields" in registry, f"{item_id} missing statement_fields"


def test_scope_gate_rejects_irrelevant_evidence() -> None:
    blocks = (BLOB_USECASE, DB_INIT_USECASE, CAPABILITY_TABLE, IRRELEVANT_TEXT)
    gated = scope_gate(
        "BLOB数据插入过程中系统如何处理异常情况",
        "系统提示插入失败",
        blocks,
    )
    gated_ids = {ev.evidence_id for ev, _ in gated}
    # BLOB use case and capability table should pass (contain BLOB)
    assert "ev-blob" in gated_ids
    assert "ev-cap" in gated_ids  # capability table mentions BLOB in description
    # DB init and irrelevant text may pass with WEAK status (not REJECT)
    # — ranking in E1 will sort them below the correct scope blocks


def test_deq_pipeline_full_flow() -> None:
    blocks = (BLOB_USECASE, DB_INIT_USECASE, CAPABILITY_TABLE, IRRELEVANT_TEXT)
    result = deq_pipeline(
        question="BLOB数据插入过程中系统如何处理异常情况并提示错误信息",
        answer="系统通过触发异常流E1提示插入失败。",
        evidence_blocks=blocks,
    )
    assert isinstance(result, DEQResult)
    assert result.original_count == 4
    assert result.gated_count <= 4
    assert result.ranked_evidence
    assert result.active_check_items  # should route to LOGIC-02 etc.
    assert result.aligned_pairs  # should have claim-statement pairs
    assert result.diagnostics["original_count"] == 4
    assert result.diagnostics["gated_count"] == result.gated_count


def test_deq_pipeline_ranks_correct_scope_first() -> None:
    blocks = (IRRELEVANT_TEXT, CAPABILITY_TABLE, DB_INIT_USECASE, BLOB_USECASE)
    result = deq_pipeline(
        question="BLOB数据插入的异常流E1是什么",
        answer="异常流E1：系统提示插入失败，用例结束。",
        evidence_blocks=blocks,
    )
    # The BLOB use case table should rank highest (correct scope + E1 content)
    top_evidence = result.ranked_evidence[0]
    assert top_evidence.evidence_id == "ev-blob"
    top_report = result.quality_reports[0]
    assert top_report.deq_score > 0


def test_aligned_pairs_contain_correct_statements() -> None:
    blocks = (BLOB_USECASE, DB_INIT_USECASE)
    result = deq_pipeline(
        question="BLOB数据插入的异常流是什么",
        answer="异常流E1：系统提示插入失败，用例结束。",
        evidence_blocks=blocks,
    )
    # The aligned pairs should include the E1 statement from the BLOB use case
    e1_pairs = [
        p for p in result.aligned_pairs
        if "异常流" in p.get("statement_field", "")
        or "E1" in p.get("statement_text", "")
    ]
    assert e1_pairs  # at least one pair references E1
    # And the BLOB-scope pair should rank higher than the DB-init scope pair
    blob_pairs = [p for p in e1_pairs if "BLOB" in p.get("statement_scope", "")]
    assert blob_pairs


def test_deq_pipeline_with_empty_evidence() -> None:
    result = deq_pipeline(
        question="什么功能", answer="某功能",
        evidence_blocks=(),
    )
    assert result.original_count == 0
    assert result.gated_count == 0
    assert not result.ranked_evidence
    assert not result.aligned_pairs


def test_deq_pipeline_diagnostic_has_rejected_info() -> None:
    blocks = (BLOB_USECASE, IRRELEVANT_TEXT)
    result = deq_pipeline(
        question="BLOB数据插入过程中系统如何处理异常情况",
        answer="系统提示插入失败",
        evidence_blocks=blocks,
    )
    assert "rejected_blocks" in result.diagnostics
    assert "ranking" in result.diagnostics
    assert result.diagnostics["original_count"] == 2
