"""Tests for the L0 entity detection layer (TERM-family term conflicts)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_structure import decompose_answer  # noqa: E402
from algorithms.consistency.entity_detector import (  # noqa: E402
    build_document_lexicon,
    detect_term_conflicts,
    extract_entities,
    link_entities,
)
from algorithms.consistency.evidence_statements import (  # noqa: E402
    EvidenceStatement,
    linearize_context,
)
from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402


def statement(sid: str, text: str, field_name: str = "sentence",
              scope_key: str = "") -> EvidenceStatement:
    return EvidenceStatement(
        statement_id=sid, evidence_id=sid.split("#")[0], text=text,
        field_name=field_name, scope_key=scope_key, row_index=1)


def lexicon_statements() -> list[EvidenceStatement]:
    return [
        statement("ev1#s0", "SQL访问功能的项目唯一标识符：PZXQ-GN-SQLFW", "标识符"),
        statement("ev1#s1", "BLOB数据操作的项目唯一标识符：PZXQ-GN-SQLFW-BLOBSJCZ", "标识符"),
        statement("ev1#s2", "BLOB数据操作的方式名称：平板、桌面、手持", "方式名称",
                  "BLOB数据操作"),
        statement("ev1#s3", "BLOB数据操作的运行状态：运行阶段、开发阶段", "运行状态",
                  "BLOB数据操作"),
        statement("ev1#s4", "Use Case 名称：插入数据", "Use Case 名称", "插入数据"),
        statement("ev1#s5", "支持大字段（BLOB）存储，本地数据库（sqlite3）"
                           "与服务器数据库（达梦数据库V7.6）之间切换"),
    ]


def make_request(question: str, answer: str) -> QAInput:
    return QAInput(
        instance_id="t-l0", question=question, answer=answer,
        context_freeze_id="t-frozen",
        evidence=(RetrievedEvidence(
            evidence_id="ev1", text=answer, source_type="text",
            source_ref=SourceRef(doc_id="d", section="3.2"),
            scope_id="d:3.2"),),
    )


def test_extract_domain_terms_pzxq_and_mixed() -> None:
    text = "系统通过SQL语句访问BLOB、JSON，并调用接口PZXQ-GN-SQLFW-BLOBSJCZ。"
    found = {(e.surface, e.kind) for e in extract_entities(text)}
    assert ("SQL", "domain_term") in found
    assert ("BLOB", "domain_term") in found
    assert ("JSON", "domain_term") in found
    assert ("PZXQ-GN-SQLFW-BLOBSJCZ", "pzxq_id") in found
    assert ("SQL语句访问", "mixed") in found


def test_extract_chinese_runs_with_stopword_filter() -> None:
    assert extract_entities("系统。数据。信息。接口。") == []
    surfaces = {e.surface for e in extract_entities("数据插入、缓存更新")}
    assert surfaces == {"数据插入", "缓存更新"}


def test_extract_quoted_terms() -> None:
    surfaces = {(e.surface, e.kind) for e in extract_entities("「大字段」采用『ORM』方式")}
    assert ("大字段", "quoted") in surfaces
    assert ("ORM", "quoted") in surfaces


def test_build_document_lexicon_from_statements() -> None:
    lexicon = build_document_lexicon(lexicon_statements())
    assert "SQL访问功能" in lexicon.capability_names
    assert "BLOB数据操作" in lexicon.usecase_names
    assert "插入数据" in lexicon.usecase_names
    assert "PZXQ-GN-SQLFW-BLOBSJCZ" in lexicon.interface_ids
    assert {"平板", "桌面", "手持"} <= set(lexicon.mode_values)
    assert {"运行阶段", "开发阶段"} <= set(lexicon.status_values)
    assert "sqlite3" in lexicon.database_names
    assert "达梦V7.6" in lexicon.database_names
    assert any(p.surface == "大字段" and p.target == "BLOB"
               for p in lexicon.alias_pairs)


def test_link_entities_exact_alias_prefix_nil() -> None:
    lexicon = build_document_lexicon(lexicon_statements())
    text = "支持BLOB。术语：大字段、桌面、内存条。"
    links = {r.entity.surface: r for r in link_entities(extract_entities(text), lexicon)}
    assert links["BLOB"].link_type == "prefix"
    assert links["BLOB"].target == "BLOB数据操作"
    assert links["大字段"].link_type == "alias"
    assert links["大字段"].target == "BLOB"
    assert links["桌面"].link_type == "exact"
    assert links["内存条"].link_type == "nil"


def test_term05_support_on_reordered_usecase_name() -> None:
    stmts = [
        statement("ev2#s0", "Use Case 名称：插入数据", "Use Case 名称", "插入数据"),
        statement("ev2#s1", "系统提供插入数据功能，用于BLOB数据的写入", "sentence",
                  "插入数据"),
    ]
    request = make_request("BLOB数据插入如何执行", "系统调用数据插入指令完成数据的写入。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term05 = [r for r in results if "TERM-05" in r.check_item_candidates]
    assert len(term05) == 1
    assert term05[0].verdict == "support"
    assert "插入数据" in term05[0].rationale


def test_term05_refute_on_different_usecase() -> None:
    stmts = [
        statement("ev2#s0", "Use Case 名称：插入数据", "Use Case 名称", "插入数据"),
        statement("ev2#s1", "系统提供插入数据功能，用于BLOB数据的写入", "sentence",
                  "插入数据"),
    ]
    request = make_request("BLOB数据插入如何执行", "系统调用数据删除指令完成数据的写入。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term05 = [r for r in results if "TERM-05" in r.check_item_candidates]
    assert len(term05) == 1
    assert term05[0].verdict == "refute"
    assert "数据删除" in term05[0].rationale


def test_term07_interface_id_conflict_and_support() -> None:
    stmts = [statement("ev3#s0", "数据统一访问接口的项目唯一标识符：PZXQ-DBS-01",
                       "标识符", "数据统一访问接口")]
    request = make_request("数据统一访问走哪个接口",
                           "系统通过接口PZXQ-DBS-02完成数据统一访问。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term07 = [r for r in results if "TERM-07" in r.check_item_candidates]
    assert len(term07) == 1
    assert term07[0].verdict == "refute"
    assert "PZXQ-DBS-01" in term07[0].rationale

    request_ok = make_request("数据统一访问走哪个接口",
                              "系统通过接口PZXQ-DBS-01完成数据统一访问。")
    results_ok = detect_term_conflicts(
        request_ok, stmts, decompose_answer(request_ok.answer, request_ok.question))
    term07_ok = [r for r in results_ok if "TERM-07" in r.check_item_candidates]
    assert len(term07_ok) == 1
    assert term07_ok[0].verdict == "support"


def test_term01_synonym_warning() -> None:
    stmts = [
        statement("ev4#s0", "大字段（BLOB）用于存储二进制数据流"),
        statement("ev4#s1", "提供BLOB数据的插入、删除、修改与查询", "需求描述",
                  "BLOB数据操作"),
    ]
    request = make_request("系统如何存储大字段", "系统将大字段写入数据库完成存储。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term01 = [r for r in results if "TERM-01" in r.check_item_candidates]
    assert len(term01) == 1
    assert term01[0].verdict == "support"
    assert term01[0].method.endswith(":warning")
    assert "大字段" in term01[0].rationale and "BLOB" in term01[0].rationale


def test_term08_abbreviation_warning() -> None:
    stmts = [
        statement("ev5#s0", "异常处理流程：E1(异常流)发生时系统回滚事务并返回错误信息"),
        statement("ev5#s1", "异常流结束后系统释放占用的资源"),
    ]
    request = make_request("系统如何处理异常流", "系统触发E1并回滚当前事务。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term08 = [r for r in results if "TERM-08" in r.check_item_candidates]
    assert len(term08) == 1
    assert term08[0].verdict == "support"
    assert term08[0].method.endswith(":warning")


def test_term02_definition_swap_refute() -> None:
    stmts = [statement("ev6#s0", "系统术语：大字段（BLOB）、对象关系映射（ORM）")]
    request = make_request("大字段指什么", "系统使用大字段（ORM）完成对象存储。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term02 = [r for r in results if "TERM-02" in r.check_item_candidates]
    assert len(term02) == 1
    assert term02[0].verdict == "refute"
    assert "对象关系映射" in term02[0].rationale


def test_term07_sibling_row_id_not_refuted_when_verbatim_in_evidence() -> None:
    """S1QA-053 claim#4: claim的ID在scope外但证据全文逐字存在(同标识表的
    兄弟行) → support——ID真实存在, 主体绑定归id_join仲裁; 旧逻辑把scope
    包含式拉入的父级行同族ID当成"answer使用假标识"误refute."""
    stmts = [
        statement("evA#s0", "删除数据记录的项目唯一标识符：PZXQ-GN-SQLFW-SJXG",
                  "标识符", "删除数据记录"),
        statement("evA#s1", "增加数据记录的项目唯一标识符：PZXQ-GN-SQLFW-ZXSW",
                  "标识符", "增加数据记录"),
        statement("evA#s2", "修改数据记录的项目唯一标识符：PZXQ-GN-SQLFW-TJSW",
                  "标识符", "修改数据记录"),
        statement("evB#s0", "修改数据的项目唯一标识符：PZXQ-GN-SQLFW-XGSJ",
                  "标识符", "修改数据"),
    ]
    request = make_request(
        "修改数据记录的功能标识表中包含哪些内容？",
        "修改数据记录的功能标识表中包含以下内容："
        "| 1 | 删除数据记录 | PZXQ-GN-SQLFW-SJXG | 支持删除数据记录 |"
        "| 3 | 修改数据记录 | PZXQ-GN-SQLFW-TJSW | 支持修改数据记录 |")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term07 = [r for r in results if "TERM-07" in r.check_item_candidates]
    assert term07, "the table claim carries PZXQ ids and must be checked"
    assert all(r.verdict != "refute" for r in term07)
    sjxg = [r for r in term07 if "PZXQ-GN-SQLFW-SJXG" in r.rationale]
    assert sjxg and sjxg[0].verdict == "support"
    assert sjxg[0].evidence_refs == ("evA#s0",)


def test_term07_fabricated_id_outside_evidence_still_refutes() -> None:
    """护栏不吞真错配: ID在证据全文不存在而scope侧有同族ID → 仍refute."""
    stmts = [statement("evC#s0", "数据库关闭的项目唯一标识符：PZXQ-GN-SJKCZ-SJKGBGN",
                       "标识符", "数据库关闭")]
    request = make_request(
        "数据库关闭的项目唯一标识符是什么？",
        "数据库关闭的项目唯一标识符为PZXQ-GN-SJKCZ-SJKGB。")
    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, stmts, claims)
    term07 = [r for r in results if "TERM-07" in r.check_item_candidates]
    assert term07 and term07[0].verdict == "refute"
    assert "PZXQ-GN-SJKCZ-SJKGBGN" in term07[0].rationale


def test_real_frozen_s1qa_001_lexicon_and_detection() -> None:
    path = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    request = request_from_dict(row)
    statements = linearize_context(request.evidence)
    assert statements

    lexicon = build_document_lexicon(statements)
    assert "SQL访问功能" in lexicon.capability_names
    assert "BLOB数据操作" in lexicon.usecase_names
    assert "数据库连接" in lexicon.usecase_names
    assert "PZXQ-GN-SQLFW-BLOBSJCZ" in lexicon.interface_ids
    assert "sqlite3" in lexicon.database_names
    assert {"桌面", "平板", "手持"} <= set(lexicon.mode_values)
    assert "运行阶段" in lexicon.status_values

    entities = extract_entities("系统执行BLOB数据插入操作")
    links = {r.entity.surface: r for r in link_entities(entities, lexicon)}
    assert links["BLOB数据插入操作"].link_type == "prefix"
    assert links["BLOB数据插入操作"].target == "BLOB数据插入"

    claims = decompose_answer(request.answer, request.question)
    results = detect_term_conflicts(request, statements, claims)
    assert all(r.verdict in {"support", "refute", "not_in_evidence"} for r in results)
    assert all(r.claim_id.startswith("ac") for r in results)
    assert all(r.method.startswith("l0_entity_detector:") for r in results)
    assert all(r.evidence_refs or r.verdict != "support" or ":warning" in r.method
               for r in results)
