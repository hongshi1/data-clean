"""Tests for the coverage completeness expert (L1, GJB-01/04/06)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.coverage_expert import (  # noqa: E402
    CHECK_ITEMS,
    CoverageMap,
    METHOD,
    build_coverage_map,
    extract_coverage_claims,
    verify_coverage,
)
from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.gjb_presence_expert import GJB_CHECKS  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    Completeness,
    QAInput,
    RetrievedEvidence,
    SourceRef,
    SourceType,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

DOC_ID = "04数据统一访问服务软件需求规格说明-终稿"

QUALIFICATION_TABLE = (
    "<table><tr><td><p>需求名称/标识</p></td><td><p>本文档的章节号</p></td>"
    "<td><p>合格性方法</p></td><td><p>合格性级别</p></td></tr>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr>"
    "<tr><td><p>对象化访问</p></td><td><p>3.2.2</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr>"
    "<tr><td><p>热点数据缓存</p></td><td><p>3.2.3</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr>"
    "<tr><td><p>代码生成</p></td><td><p>3.2.4</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr>"
    "<tr><td><p>连接池管理</p></td><td><p>3.2.5</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr>"
    "<tr><td><p>数据源适配</p></td><td><p>3.2.6</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr></table>"
    "表80 合格性规定"
)

QUALIFICATION_PARTIAL = (
    "<table><tr><td><p>需求名称/标识</p></td><td><p>本文档的章节号</p></td>"
    "<td><p>合格性方法</p></td><td><p>合格性级别</p></td></tr>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr>"
    "<tr><td><p>热点数据缓存</p></td><td><p>3.2.2</p></td>"
    "<td><p>无</p></td><td><p>a、b</p></td></tr></table>"
)

QUALIFICATION_ONE_ROW = (
    "<table><tr><td><p>需求名称/标识</p></td><td><p>本文档的章节号</p></td>"
    "<td><p>合格性方法</p></td><td><p>合格性级别</p></td></tr>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td>"
    "<td><p>A、B、D</p></td><td><p>a、b</p></td></tr></table>"
)

QUALITY_TABLE = (
    "<table><tr><td><p>序号</p></td><td><p>软件质量因素</p></td>"
    "<td><p>软件质量因素描述</p></td><td><p>要求程度</p></td>"
    "<td><p>采取的措施</p></td></tr>"
    "<tr><td><p>1</p></td><td><p>功能性</p></td>"
    "<td><p>实现全部所需功能的能力</p></td><td><p>符合3.2节要求</p></td>"
    "<td><p>软件设计</p></td></tr>"
    "<tr><td><p>7</p></td><td><p>可测试性</p></td>"
    "<td><p>易于充分测试的能力</p></td>"
    "<td><p>可仿真环境下完成主要功能验证</p></td>"
    "<td><p>依靠操作系统和仿真网络</p></td></tr></table>"
    "表73 数据统一访问服务服务软件质量要求与措施表"
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
    "<tr><td><p>2</p></td><td><p>热点数据缓存功能</p></td>"
    "<td><p>PZXQ-GN-RDSJC</p></td>"
    "<td><p>提供热点数据缓存功能。</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段</p></td><td><p>4.1.2</p></td></tr>"
    "</tbody></table>"
)

AUDIT_LOG_CLAUSE = (
    "系统提供完整的审计日志记录功能，关键操作与参数修改均记录审计日志。"
)

ALARM_FULL_CLAUSE = (
    "异常流E1：系统提示获取失败，报警信息包含时间戳、故障位置、"
    "故障等级与处置建议。"
)

ALARM_BARE_CLAUSE = "异常流E1：系统提示获取失败，用例结束。"

SECTION_3_3 = "3.3 CSCI外部接口需求"
SECTION_3_4 = "3.4 CSCI内部接口需求"


def _block(evidence_id: str, text: str, source_type: SourceType,
           section: str = "", completeness: Completeness = "open",
           ) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id,
        text=text,
        source_type=source_type,
        source_ref=SourceRef(doc_id=DOC_ID, section=section),
        scope_id=f"{DOC_ID}:{evidence_id}",
        completeness=completeness,
    )


def vio17_blocks() -> list[RetrievedEvidence]:
    """VIO-17形态证据：质量因素表+6行合格性表(3.2.1~3.2.6)+3.3/3.4标题。

    含表73使gjb_presence对GJB-01判present/support——复现真实VIO-17的
    对抗形态（旧系统仅凭表存在性判support，本专家以覆盖缺口推翻）。
    """
    return [
        _block("ev-368", QUALITY_TABLE, "table",
               section="表73 数据统一访问服务服务软件质量要求与措施表"),
        _block("ev-404", QUALIFICATION_TABLE, "table",
               section="表80 合格性规定"),
        _block("ev-262", SECTION_3_3, "text", section=SECTION_3_3),
        _block("ev-280", SECTION_3_4, "text", section=SECTION_3_4),
    ]


def coverage_request(answer: str, blocks: list[RetrievedEvidence],
                     question: str = "需求是否都有合格性方法？",
                     instance_id: str = "qa-cov",
                     ) -> QAInput:
    return QAInput(
        instance_id=instance_id,
        question=question,
        answer=answer,
        context_freeze_id="frozen-cov-1",
        evidence=tuple(blocks),
    )


def test_check_items_match_taxonomy_and_gjb_checks() -> None:
    taxonomy = json.loads(
        (BASE / "knowledge/consistency_taxonomy_v3.json").read_text(
            encoding="utf-8"))
    taxonomy_ids = {item["id"] for item in taxonomy["items"]
                    if str(item.get("id", "")).startswith("GJB")}
    gjb_ids = {check.check_id for check in GJB_CHECKS}
    assert CHECK_ITEMS == ("GJB-01", "GJB-04", "GJB-06")
    assert set(CHECK_ITEMS) <= taxonomy_ids
    assert set(CHECK_ITEMS) <= gjb_ids


def test_build_coverage_map_extracts_qualification_rows() -> None:
    blocks = [_block("ev-404", QUALIFICATION_TABLE, "table")]
    coverage = build_coverage_map(tuple(blocks))
    assert [(row.name, row.section, row.method) for row in coverage.qual_rows] == [
        ("SQL访问", (3, 2, 1), "A、B、D"),
        ("对象化访问", (3, 2, 2), "A、B、D"),
        ("热点数据缓存", (3, 2, 3), "A、B、D"),
        ("代码生成", (3, 2, 4), "A、B、D"),
        ("连接池管理", (3, 2, 5), "A、B、D"),
        ("数据源适配", (3, 2, 6), "A、B、D"),
    ]
    assert coverage.qualification_evidence_ids == ("ev-404",)


def test_build_coverage_map_registers_heading_and_source_ref_sections() -> None:
    blocks = [
        _block("ev-262", SECTION_3_3, "text", section=SECTION_3_3),
        _block("ev-301", "正文描述段落内容较长，用于证明普通句子不会登记"
                         "为章节，即使句中提到3.2节也不会误登记。", "text",
               section="3.2 CSCI能力需求"),
        _block("ev-404", QUALIFICATION_TABLE, "table",
               section="表80 合格性规定"),
    ]
    coverage = build_coverage_map(tuple(blocks))
    by_section = {fact.section: fact for fact in coverage.sections}
    assert by_section[(3, 3)].title == "CSCI外部接口需求"
    assert by_section[(3, 3)].evidence_ids == ("ev-262",)
    assert by_section[(3, 2)].title == "CSCI能力需求"
    assert by_section[(3, 2)].evidence_ids == ("ev-301",)
    assert (3, 2, 1) in by_section
    assert by_section[(3, 2, 1)].evidence_ids == ("ev-404",)
    assert (3, 1) not in by_section


def test_build_coverage_map_extracts_capability_items() -> None:
    blocks = [_block("ev-cap", CAPABILITY_TABLE, "table")]
    coverage = build_coverage_map(tuple(blocks))
    assert [(item.name, item.identifier) for item in coverage.capabilities] == [
        ("SQL访问功能", "PZXQ-GN-SQLFW"),
        ("热点数据缓存功能", "PZXQ-GN-RDSJC"),
    ]


def test_empty_method_row_is_known_section_not_coverage() -> None:
    """合格性方法列为「无」：章节已知但未覆盖（VIO-17缺行变体）。"""
    blocks = [_block("ev-q", QUALIFICATION_PARTIAL, "table")]
    coverage = build_coverage_map(tuple(blocks))
    assert [row.section for row in coverage.qual_rows] == [(3, 2, 1)]
    assert coverage.is_covered((3, 2, 1))
    assert not coverage.is_covered((3, 2, 2))
    assert (3, 2, 2) in {fact.section for fact in coverage.sections}


def test_container_section_covered_via_descendant_rows() -> None:
    """路径重叠：子节3.2.1有行→容器3.2不判缺口；兄弟3.3仍判缺口。"""
    blocks = vio17_blocks() + [
        _block("ev-201", "3.2 CSCI能力需求", "text")]
    coverage = build_coverage_map(tuple(blocks))
    assert coverage.is_covered((3, 2))
    assert coverage.is_covered((3, 2, 1))
    assert coverage.is_covered((3, 2, 1, 1))
    assert not coverage.is_covered((3, 3))
    assert not coverage.is_covered((3, 4))


def test_vio17_range_claim_refuted_with_gaps() -> None:
    blocks = vio17_blocks()
    request = coverage_request(
        "本文档3.1至3.17章节的全部需求均规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert len(results) == 1
    claim = results[0]
    assert claim.verdict == "refute"
    assert claim.method == METHOD
    assert claim.check_item_candidates == ("GJB-01",)
    assert claim.confidence == 0.9
    assert claim.claim_id == "qa-cov-cov01"
    assert claim.evidence_refs == ("ev-262", "ev-280", "ev-404")
    assert "3.3 CSCI外部接口需求" in claim.rationale
    assert "3.4 CSCI内部接口需求" in claim.rationale
    assert "覆盖缺口2项" in claim.rationale
    assert "3.2.1、3.2.2、3.2.3、3.2.4、3.2.5、3.2.6" in claim.rationale


def test_range_claim_supported_when_fully_covered() -> None:
    blocks = [_block("ev-q", QUALIFICATION_TABLE, "table")]
    request = coverage_request(
        "3.2.1至3.2.6章节的全部需求均规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].evidence_refs == ("ev-q",)
    assert "无覆盖缺口" in results[0].rationale


def test_range_claim_nie_without_qualification_rows() -> None:
    blocks = [_block("ev-h", SECTION_3_3, "text")]
    request = coverage_request(
        "3.1至3.17章节的全部需求均规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["not_in_evidence"]
    assert results[0].confidence == 0.0
    assert "不含任何合格性行" in results[0].rationale


def test_range_claim_nie_when_scope_derives_no_known_sections() -> None:
    blocks = [_block("ev-q", QUALIFICATION_TABLE, "table")]
    request = coverage_request(
        "4.1至4.9章节的全部需求均规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["not_in_evidence"]
    assert "无法比对覆盖缺口" in results[0].rationale


def test_reversed_range_is_not_a_claim() -> None:
    assert extract_coverage_claims(
        "3.17至3.1章节的需求均规定了合格性方法。") == []


def test_universal_claim_refuted_with_gap() -> None:
    blocks = [_block("ev-q", QUALIFICATION_ONE_ROW, "table"),
              _block("ev-h", SECTION_3_3, "text")]
    request = coverage_request("所有需求都规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["refute"]
    assert "覆盖缺口1项" in results[0].rationale
    assert "3.3 CSCI外部接口需求" in results[0].rationale


def test_universal_claim_supported_without_gaps() -> None:
    blocks = [_block("ev-q", QUALIFICATION_TABLE, "table")]
    request = coverage_request("所有需求都规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["support"]


def test_precise_claim_supported_by_qualification_row() -> None:
    blocks = [_block("ev-q", QUALIFICATION_TABLE, "table")]
    request = coverage_request(
        "SQL访问功能规定了合格性方法。", blocks,
        question="SQL访问有合格性方法吗？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].evidence_refs == ("ev-q",)
    assert "SQL访问@3.2.1" in results[0].rationale


def test_precise_claim_refuted_when_capability_lacks_row() -> None:
    blocks = [_block("ev-q", QUALIFICATION_ONE_ROW, "table"),
              _block("ev-cap", CAPABILITY_TABLE, "table")]
    request = coverage_request(
        "热点数据缓存功能有合格性规定。", blocks,
        question="热点数据缓存有合格性方法吗？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["refute"]
    assert results[0].evidence_refs == ("ev-cap", "ev-q")
    assert "能力清单含[热点数据缓存功能]" in results[0].rationale


def test_precise_claim_nie_when_subject_unknown() -> None:
    blocks = [_block("ev-q", QUALIFICATION_TABLE, "table"),
              _block("ev-cap", CAPABILITY_TABLE, "table")]
    request = coverage_request(
        "数据同步功能有合格性规定。", blocks,
        question="数据同步有合格性方法吗？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["not_in_evidence"]
    assert "不在冻结证据合格性行/能力清单" in results[0].rationale


def test_precise_claim_matches_identifier_subject() -> None:
    """标识符主体经能力清单间接解析到合格性行（覆盖join）。"""
    blocks = [_block("ev-q", QUALIFICATION_TABLE, "table"),
              _block("ev-cap", CAPABILITY_TABLE, "table")]
    request = coverage_request(
        "PZXQ-GN-RDSJC需求规定了合格性方法。", blocks)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].evidence_refs == ("ev-q",)


def test_generic_subject_is_not_a_precise_claim() -> None:
    assert extract_coverage_claims("本文档有合格性规定。") == []
    assert extract_coverage_claims("该系统提供了合格性规定。") == []


def test_negative_coverage_claim_is_not_extracted() -> None:
    assert extract_coverage_claims("部分需求没有规定合格性方法。") == []
    assert extract_coverage_claims("3.3章节的需求未包含合格性方法。") == []


def test_gjb04_clause_claim_refuted_when_clause_missing() -> None:
    request = coverage_request(
        "系统提供审计日志功能。", [_block("ev-q", QUALIFICATION_TABLE, "table")],
        question="系统提供审计日志吗？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["refute"]
    assert results[0].check_item_candidates == ("GJB-04",)
    assert results[0].method == METHOD


def test_gjb04_clause_claim_supported_when_clause_present() -> None:
    request = coverage_request(
        "系统提供审计日志功能。",
        [_block("ev-a", AUDIT_LOG_CLAUSE, "text")],
        question="系统提供审计日志吗？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].check_item_candidates == ("GJB-04",)
    assert results[0].evidence_refs == ("ev-a",)


def test_gjb06_element_claim_supported_when_elements_present() -> None:
    request = coverage_request(
        "报警信息包含时间戳、故障位置、故障等级与处置建议。",
        [_block("ev-al", ALARM_FULL_CLAUSE, "table")],
        question="报警信息包含哪些要素？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["support"]
    assert results[0].check_item_candidates == ("GJB-06",)
    assert results[0].evidence_refs == ("ev-al",)


def test_gjb06_element_claim_refuted_when_elements_missing() -> None:
    """taxonomy GJB-06原始例的深化：E1仅提示文本→逐要素缺口。"""
    request = coverage_request(
        "报警信息包含时间戳、故障位置、故障等级与处置建议。",
        [_block("ev-al", ALARM_BARE_CLAUSE, "table")],
        question="报警信息包含哪些要素？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["refute"]
    assert results[0].check_item_candidates == ("GJB-06",)
    assert "缺失要素[时间戳、位置、等级、处置建议]" in results[0].rationale
    assert results[0].evidence_refs == ("ev-al",)


def test_gjb06_falls_back_to_clause_audit_without_alarm_statements() -> None:
    request = coverage_request(
        "报警信息包含时间戳、故障位置、故障等级与处置建议。",
        [_block("ev-q", QUALIFICATION_TABLE, "table")],
        question="报警信息包含哪些要素？")
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["refute"]
    assert "封闭清单" in results[0].rationale


def test_answer_without_coverage_claims_returns_empty() -> None:
    request = coverage_request(
        "系统响应时间为200ms，查询1000条数据的时间应小于1s。",
        vio17_blocks())
    assert verify_coverage(request) == []


def test_empty_evidence_returns_empty() -> None:
    request = coverage_request("所有需求都规定了合格性方法。", [])
    assert verify_coverage(request) == []


def test_verify_is_deterministic() -> None:
    request = coverage_request(
        "本文档3.1至3.17章节的全部需求均规定了合格性方法。",
        vio17_blocks())
    first = verify_coverage(request)
    second = verify_coverage(request)
    assert first == second
    statements = linearize_context(tuple(vio17_blocks()))
    assert verify_coverage(request, statements) == first


def test_statements_equivalent_to_derived_linearization() -> None:
    blocks = vio17_blocks()
    explicit = build_coverage_map(tuple(blocks),
                                  linearize_context(tuple(blocks)))
    derived = build_coverage_map(tuple(blocks))
    assert explicit == derived


def test_module_integration_refutes_vio17_replica() -> None:
    request = coverage_request(
        "本文档3.1至3.17章节的全部需求均规定了合格性方法。",
        vio17_blocks(), instance_id="qa-vio17-replica")
    module = QAConsistencyModule(use_experts=True)
    result = module.verify(request)
    assert result.verdict == "refute"
    refute = [claim for claim in result.claim_results
              if claim.verdict == "refute" and claim.method == METHOD]
    assert refute
    assert "GJB-01" in refute[0].check_item_candidates


def load_violation_rows() -> list[dict]:
    path = (BASE / "data/gjb_438c/localization_gold"
            / "violation_evalset_v1.jsonl")
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def violation_request(row: dict) -> QAInput:
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
        answer=row["answer"],
        context_freeze_id=row["context_freeze_id"],
        evidence=evidence,
    )


def test_real_vio17_instance_refuted_with_gap_discovery() -> None:
    rows = load_violation_rows()
    row = next(item for item in rows
               if item["instance_id"] == "DOC04-VIO-17")
    request = violation_request(row)
    results = verify_coverage(request)
    assert [result.verdict for result in results] == ["refute"]
    claim = results[0]
    assert claim.method == METHOD
    assert "DOC04-VIO-17-ev-000404" in claim.evidence_refs
    assert "DOC04-VIO-17-ev-000262" in claim.evidence_refs
    assert "DOC04-VIO-17-ev-000280" in claim.evidence_refs
    assert "3.3 CSCI外部接口需求" in claim.rationale
    assert "3.4 CSCI内部接口需求" in claim.rationale


def load_frozen_rows() -> list[dict]:
    path = (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_real_frozen_scene1_emits_no_coverage_noise() -> None:
    rows = load_frozen_rows()
    assert len(rows) == 91
    for row in rows:
        request = violation_request(row)
        assert verify_coverage(request) == []


def test_coverage_map_is_public_contract() -> None:
    blocks = vio17_blocks()
    coverage = build_coverage_map(tuple(blocks))
    assert isinstance(coverage, CoverageMap)
    assert coverage.qual_rows
    assert coverage.sections
    assert coverage.capabilities == ()
