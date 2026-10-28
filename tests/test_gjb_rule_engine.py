"""Tests for the GJB rule-library-driven template rule engine (L1).

覆盖：编译器字段/确定性、manual诚实标记、文档审计裁决、answer侧
校验(support/refute/NIE)、真实04号冒烟(taxonomy一致性)、覆盖率统计、
91QA零噪音、规则簇映射合法性。
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import (  # noqa: E402
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.gjb_rule_engine import (  # noqa: E402
    CHECK_ITEMS,
    METHOD,
    aggregate_clusters,
    audit_document,
    compile_library,
    compile_rule,
    default_checks,
    load_rule_library,
    rule_clusters,
    verify_gjb_rules,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    Completeness,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)

DOC_ID = "04数据统一访问服务软件需求规格说明-终稿"


def _statement(evidence_id: str, text: str) -> EvidenceStatement:
    return EvidenceStatement(
        statement_id=f"{evidence_id}#s0", evidence_id=evidence_id,
        text=text, field_name="sentence", scope_key="", row_index=1)


def _block(evidence_id: str, text: str,
           completeness: Completeness = "open") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id, text=text, source_type="text",
        source_ref=SourceRef(doc_id=DOC_ID),
        scope_id=f"{DOC_ID}:{evidence_id}", completeness=completeness)


def _request(answer: str, blocks: list[RetrievedEvidence],
             question: str = "文档的GJB合规状态如何？") -> QAInput:
    return QAInput(
        instance_id="qa-gjr", question=question, answer=answer,
        context_freeze_id="frozen-gjr-1", evidence=tuple(blocks))


def library_checks() -> tuple:
    return compile_library(load_rule_library())


# ═══════════════ 编译器 ═══════════════

def test_compile_content_rule_extracts_patterns() -> None:
    rule = {
        "rule_id": "GJB-RULE-041", "type": "content", "source": "附录J 3.2.X",
        "modality": "MUST", "applies_to": ["SRS"],
        "description": "能力需求适当时应包括异常条件、非许可条件或超限"
                       "条件下所需的行为，错误处理需求，以及为保证在紧急"
                       "时刻运行的连续性而引入到CSCI中的规定。",
        "original_text": "原文",
    }
    check = compile_rule(rule)
    assert check.rule_id == "GJB-RULE-041"
    assert check.check_type == "content"
    assert check.source_anchor == "附录J 3.2.X"
    assert check.cluster in {"GJB-02", "GJB-06", "GJB-08", "GJB-09"}
    assert check.requirement and "应包括" in check.requirement
    assert "异常条件" in check.patterns
    assert "错误处理" in check.patterns
    assert "连续性" in check.patterns


def test_compile_structure_rule_quantified() -> None:
    rule = {
        "rule_id": "GJB-RULE-036", "type": "structure", "source": "附录J 3",
        "applies_to": ["SRS"],
        "description": "每条CSCI需求应指定项目唯一的标识符以便测试和追踪。",
    }
    check = compile_rule(rule)
    assert check.check_type == "structure"
    assert check.quantified is True
    assert "标识符" in check.patterns


def test_compile_format_rule_enumeration() -> None:
    rule = {
        "rule_id": "GJB-RULE-035", "type": "format", "source": "附录J 2",
        "applies_to": ["SRS"],
        "description": "引用文档应列出引用文档的编号、标题、编写单位、"
                       "修订版及日期。",
    }
    check = compile_rule(rule)
    assert check.check_type == "format"
    assert "编写单位" in check.patterns
    assert "修订版" in check.patterns


def test_compile_parameter_rule_from_rule_library() -> None:
    checks = {c.rule_id: c for c in library_checks()}
    rule40 = checks["GJB-RULE-040"]
    assert rule40.check_type == "parameter"
    assert "响应时间" in rule40.patterns
    assert "精度" in rule40.patterns
    rule50 = checks["GJB-RULE-050"]
    assert rule50.check_type == "parameter"
    assert "范围" in rule50.patterns


def test_uncompilable_cross_document_rule_is_manual() -> None:
    rule = {
        "rule_id": "GJB-RULE-094", "type": "content", "source": "附录F 3",
        "applies_to": ["SRS"],
        "description": "SSS每条系统需求必须指定项目唯一标识符以便测试和"
                       "追踪。",
    }
    check = compile_rule(rule)
    assert check.check_type == "manual"
    assert check.patterns == ()
    assert "跨文档" in check.compile_note


def test_uncompilable_abstract_rule_is_manual() -> None:
    rule = {
        "rule_id": "GJB-RULE-999", "type": "content", "source": "附录J 3",
        "applies_to": ["SRS"],
        "description": "SRS应描述对CSCI的需求，以及确保满足每个需求所用"
                       "的方法。",
    }
    check = compile_rule(rule)
    assert check.check_type == "manual"
    assert check.compile_note


def test_compile_is_deterministic() -> None:
    rules = load_rule_library()
    first = compile_library(rules)
    second = compile_library(rules)
    assert first == second


def test_compilation_coverage_reported_honestly() -> None:
    checks = library_checks()
    assert len(checks) == 87
    manual = [c for c in checks if c.check_type == "manual"]
    compilable = [c for c in checks if c.check_type != "manual"]
    assert len(manual) >= 20
    assert len(compilable) >= 50
    assert all(c.patterns for c in compilable)
    types = {c.check_type for c in compilable}
    assert types <= {"content", "structure", "interface", "format",
                     "parameter"}


def test_cluster_mapping_rules_exist_and_cover_taxonomy() -> None:
    """簇映射已外置到rule pack(gjb.rule_clusters段, 带映射理由): 覆盖
    taxonomy全部GJB项, 引用的规则号都在规则库中, 每簇有非空理由。"""
    taxonomy = json.loads(
        (BASE / "knowledge/consistency_taxonomy_v3.json").read_text(
            encoding="utf-8"))
    taxonomy_ids = {item["id"] for item in taxonomy["items"]
                    if str(item.get("id", "")).startswith("GJB")}
    rule_ids = {rule["rule_id"] for rule in load_rule_library()}
    clusters = rule_clusters()
    assert {cluster for cluster, _, _ in clusters} == taxonomy_ids
    for _, rule_ids_for_cluster, reason in clusters:
        assert rule_ids_for_cluster
        assert set(rule_ids_for_cluster) <= rule_ids
        assert reason


# ═══════════════ 文档审计 ═══════════════

def test_audit_satisfied_when_all_patterns_hit() -> None:
    check = compile_rule({
        "rule_id": "GJB-RULE-065", "type": "content", "source": "附录J 3.10",
        "applies_to": ["SRS"],
        "description": "其他质量特性应指明质量特性需求，其中包括：可靠性"
                       "、测试性、维护性等。",
    })
    statements = [
        _statement("ev-1", "可靠性：连续运行时间不低于72小时。"),
        _statement("ev-1", "测试性：提供量化指标。"),
        _statement("ev-1", "维护性：模块化设计。"),
        _statement("ev-1", "质量特性：见表73软件质量要求与措施。"),
    ]
    results = audit_document(statements, [check])
    assert results[0].verdict == "satisfied"
    assert results[0].matched and not results[0].missed
    assert results[0].evidence_refs == ("ev-1",)


def test_audit_violated_when_no_pattern_hit() -> None:
    check = compile_rule({
        "rule_id": "GJB-RULE-041", "type": "content", "source": "附录J 3.2.X",
        "applies_to": ["SRS"],
        "description": "能力需求适当时应包括异常条件、非许可条件下所需的"
                       "行为，错误处理需求。",
    })
    statements = [_statement("ev-1", "系统提供数据库连接与关闭功能。")]
    results = audit_document(statements, [check])
    assert results[0].verdict == "violated"
    assert results[0].matched == ()
    assert set(results[0].missed) == set(check.patterns)


def test_audit_partial_when_some_patterns_hit() -> None:
    check = compile_rule({
        "rule_id": "GJB-RULE-062", "type": "content", "source": "附录J 3.7",
        "applies_to": ["SRS"],
        "description": "保密性需求应指明保密性需求，包括：保密性环境、"
                       "保密性风险、安全措施等。",
    })
    statements = [
        _statement("ev-2", "保密性：用户使用时需输入正确的用户名和密码。"),
    ]
    results = audit_document(statements, [check])
    assert results[0].verdict == "partial"
    assert "保密性" in results[0].matched
    assert "安全措施" in results[0].missed


def test_audit_quantified_rule_capped_at_partial() -> None:
    check = compile_rule({
        "rule_id": "GJB-RULE-037", "type": "content", "source": "附录J 3",
        "applies_to": ["SRS"],
        "description": "每条需求应注明所采用的合格性方法。",
    })
    statements = [_statement("ev-3", "合格性方法：演示、测试。")]
    results = audit_document(statements, [check])
    assert results[0].verdict == "partial"
    assert "量词" in results[0].rationale


def test_audit_manual_check_reports_note() -> None:
    check = compile_rule({
        "rule_id": "GJB-RULE-094", "type": "content", "source": "附录F 3",
        "applies_to": ["SRS"],
        "description": "SSS每条系统需求必须指定项目唯一标识符。",
    })
    results = audit_document([_statement("ev-4", "任意内容")], [check])
    assert results[0].verdict == "manual"
    assert results[0].patterns == ()


def test_cluster_aggregation_best_of() -> None:
    checks = library_checks()
    by_id = {c.rule_id: c for c in checks}
    statements = [_statement("ev-5", "安全性和保密性需求存在。")]
    results = audit_document(statements, [by_id["GJB-RULE-063"]])
    audits = aggregate_clusters(results)
    assert audits["GJB-07"].verdict == "partial"
    assert audits["GJB-02"].verdict == "partial"


# ═══════════════ answer侧校验 ═══════════════

def test_answer_presence_claim_refuted_when_cluster_violated() -> None:
    blocks = [_block("ev-a1", "系统提供数据库连接与关闭功能。")]
    request = _request("本文档规定了掉电场景下的错误处理需求。", blocks)
    results = verify_gjb_rules(request, library=library_checks())
    refutes = [r for r in results if r.check_item_candidates == ("GJB-09",)]
    assert refutes and refutes[0].verdict == "refute"
    assert refutes[0].method == METHOD
    assert refutes[0].confidence == 0.9
    assert "GJB-RULE-041" in refutes[0].rationale
    assert "附录J" in refutes[0].rationale


def test_answer_presence_claim_supported_when_cluster_content_exists() -> None:
    blocks = [
        _block("ev-a2", "第4章合格性规定：每条需求注明合格性方法，见表80。"),
    ]
    request = _request("本文档的需求均规定了合格性方法。", blocks)
    results = verify_gjb_rules(request, library=library_checks())
    assert results
    supported = [r for r in results if r.verdict == "support"]
    assert supported
    assert any(r.check_item_candidates == ("GJB-01",) for r in supported)
    assert supported[0].evidence_refs


def test_answer_absence_claim_nie_on_open_context() -> None:
    blocks = [_block("ev-a3", "系统提供数据库连接与关闭功能。")]
    request = _request("文档缺少错误处理条款。", blocks)
    results = verify_gjb_rules(request, library=library_checks())
    nie = [r for r in results if r.check_item_candidates == ("GJB-09",)]
    assert nie and nie[0].verdict == "not_in_evidence"
    assert nie[0].confidence == 0.0


def test_answer_absence_claim_supported_on_closed_context() -> None:
    blocks = [_block("ev-a4", "系统提供数据库连接与关闭功能。",
                     completeness="closed")]
    request = _request("文档缺少错误处理条款。", blocks)
    results = verify_gjb_rules(request, library=library_checks())
    closed = [r for r in results if r.check_item_candidates == ("GJB-09",)]
    assert closed and closed[0].verdict == "support"


def test_answer_without_gjb_content_returns_empty() -> None:
    blocks = [_block("ev-a5", "系统响应时间为200ms。")]
    request = _request("查询结果以二维数组形式返回。", blocks)
    assert verify_gjb_rules(request, library=library_checks()) == []


def test_answer_rhetorical_quality_mention_is_not_claim() -> None:
    blocks = [_block("ev-a6", "用例主事件流描述正常路径。")]
    request = _request("这些步骤确保了过程的正确性和可靠性，符合用例的"
                       "要求。", blocks)
    assert verify_gjb_rules(request, library=library_checks()) == []


def test_verify_is_deterministic() -> None:
    blocks = [
        _block("ev-a7", "第4章规定了合格性验证方法。"),
        _block("ev-a8", "系统提供数据库连接与关闭功能。"),
    ]
    request = _request("本文档规定了合格性方法，还规定了掉电场景的错误"
                       "处理需求。", blocks)
    first = verify_gjb_rules(request, library=library_checks())
    second = verify_gjb_rules(request, library=library_checks())
    assert first == second


# ═══════════════ 真实04号冒烟 ═══════════════

def doc04_statements() -> list[EvidenceStatement]:
    paths = list((BASE / "data/gjb_438c/mineru_standard").glob(
        "04*/office/*_content_list.json"))
    assert len(paths) == 1
    items = json.loads(paths[0].read_text(encoding="utf-8"))
    blocks: list[RetrievedEvidence] = []
    for index, item in enumerate(items):
        kind = str(item.get("type", ""))
        if kind == "table":
            body = str(item.get("table_body") or "")
            caption = item.get("table_caption") or []
            text = body + (f"\n{caption[0]}" if caption else "")
            source_type = "table"
        elif kind == "text":
            text = str(item.get("text") or "")
            source_type = "text"
        else:
            continue
        if not text.strip():
            continue
        blocks.append(RetrievedEvidence(
            evidence_id=f"ev-b{index:03d}", text=text,
            source_type=source_type, source_ref=SourceRef(doc_id=DOC_ID),
            scope_id=f"{DOC_ID}:b{index:03d}", completeness="open"))
    return linearize_context(tuple(blocks))


def test_real_doc04_audit_matches_taxonomy() -> None:
    statements = doc04_statements()
    assert len(statements) > 1000
    results = audit_document(statements, library_checks())
    audits = aggregate_clusters(results)
    verdicts = {c: audits[c].verdict for c in CHECK_ITEMS}
    assert verdicts["GJB-08"] == "violated"
    assert verdicts["GJB-06"] == "violated"
    assert verdicts["GJB-09"] == "violated"
    assert verdicts["GJB-01"] == "partial"
    assert verdicts["GJB-05"] == "partial"
    assert "可追踪性" in audits["GJB-05"].matched_patterns
    assert "合格性方法" in audits["GJB-01"].matched_patterns
    assert "降级" in audits["GJB-11"].missed_patterns
    assert "ev-b404" in audits["GJB-01"].evidence_refs


def test_real_doc04_answer_claims() -> None:
    blocks = [
        _block("ev-b405", "5 需求可追踪性"),
        _block("ev-b406", "本文档的追踪性见表81和表82。"),
    ]
    supported = _request("本文档规定了需求可追踪性需求。", blocks)
    results = verify_gjb_rules(supported, library=library_checks())
    assert results and results[0].verdict == "support"

    traceless = [_block("ev-b024", "CSCI能力需求包含六项功能。")]
    refuted = _request("本文档规定了掉电场景的错误处理需求。", traceless)
    results = verify_gjb_rules(refuted, library=library_checks())
    assert results and results[0].verdict == "refute"


def test_real_frozen_scene1_emits_no_audit_noise() -> None:
    rows = [json.loads(line) for line in
            (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
            .read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 91
    checks = library_checks()
    for row in rows:
        evidence = tuple(
            RetrievedEvidence(
                evidence_id=block["evidence_id"], text=block["text"],
                source_type=block["source_type"],
                source_ref=SourceRef(**block["source_ref"]),
                scope_id=block["scope_id"],
                completeness=block.get("completeness", "unknown"))
            for block in row["evidence"])
        request = QAInput(
            instance_id=row["instance_id"], question=row["question"],
            answer=row["answer"],
            context_freeze_id=row["context_freeze_id"], evidence=evidence)
        assert verify_gjb_rules(request, library=checks) == []


def test_default_checks_cached_and_stable() -> None:
    first = default_checks()
    second = default_checks()
    assert first is second
    assert len(first) == 87
