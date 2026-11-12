"""InconsistencyLocalization contract tests (M84)."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import QAInput  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.verifier import CascadeVerifier  # noqa: E402


def request(iid: str, answer: str, evidences) -> QAInput:
    return QAInput(
        instance_id=iid, question="q", answer=answer,
        evidence=tuple(evidences), context_freeze_id="test")


def evidences() -> list[RetrievedEvidence]:
    return [
        RetrievedEvidence(
            evidence_id="e1", text="数据库关闭的项目唯一标识符：ID-A",
            source_type="text",
            source_ref=SourceRef(doc_id="04", section="3.2",
                                 block_id="block-000001"),
            scope_id="", completeness="open"),
        RetrievedEvidence(
            evidence_id="e2",
            text="<table><tr><td><p>方式名称</p></td><td><p>桌面</p></td></tr></table>",
            source_type="table",
            source_ref=SourceRef(doc_id="04", section="3.2",
                                 block_id="block-000002"),
            scope_id="", completeness="open"),
    ]


def test_refute_produces_localizations_with_evidence() -> None:
    module = QAConsistencyModule(use_experts=True)
    answer = "数据库关闭的项目唯一标识符为ID-B"
    result = module.verify(request("t1", answer, evidences()))
    assert result.verdict == "refute"
    assert result.localizations, "refute必须产出定位报告"
    for loc in result.localizations:
        assert loc.claim_text
        assert loc.answer_span is not None, "answer内文本命中应有span"
        start, end = loc.answer_span
        assert answer[start:end] == loc.claim_text
        assert loc.evidence, "ID冲突refute应有证据定位"
        for ev_loc in loc.evidence:
            assert ev_loc.block_id == "block-000001"
            assert "ID-A" in ev_loc.statement_text
            assert ev_loc.evidence_id in ("e1", "e2")


def test_support_and_nie_produce_no_localizations() -> None:
    module = QAConsistencyModule(use_experts=True)
    ok = module.verify(request(
        "t2", "数据库关闭的项目唯一标识符为ID-A", evidences()))
    nie = module.verify(request("t3", "随便一句无关话", evidences()))
    assert ok.localizations == ()
    assert nie.localizations == ()


def test_facade_exposes_localizations() -> None:
    verifier = CascadeVerifier(preset="fast", scene="srs_scene1")
    result = verifier.verify(
        "数据库关闭的标识符是什么", "数据库关闭的项目唯一标识符为ID-B",
        [{"text": "数据库关闭的项目唯一标识符：ID-A"}])
    assert result.verdict == "refute"
    assert result.localizations, "facade必须透出定位字段"
    loc = result.localizations[0]
    assert hasattr(loc, "claim_text")
    assert hasattr(loc, "evidence")
