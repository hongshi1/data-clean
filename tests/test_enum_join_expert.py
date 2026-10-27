"""Tests for the enum join expert (L1, TERM-03)."""
from __future__ import annotations

import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.enum_join_expert import (  # noqa: E402
    METHOD,
    build_domain_registry,
    extract_enum_assertions,
    levenshtein,
    verify_enum_joins,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402

DOC_ID = "04数据统一访问服务软件需求规格说明-终稿"
QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
VIOLATION_SET = (BASE / "data/gjb_438c/localization_gold"
                 / "violation_evalset_v1.jsonl")

#: 表2形态（顶层能力表）：行主体/标识符/方式名称/运行状态
CAP_TABLE_TOP = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>SQL访问功能</p></td>"
    "<td><p>PZXQ-GN-SQLFW</p></td><td><p>提供原生SQL访问功能</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段</p><p>开发阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td><p>2</p></td><td><p>代码生成</p></td>"
    "<td><p>PZXQ-GN-DMSC</p></td><td><p>提供代码自动生成功能</p></td>"
    "<td><p>沿用</p></td><td><p>桌面</p></td>"
    "<td><p>开发阶段</p></td><td><p>4.1.1</p></td></tr>"
    "</tbody></table>"
)

#: 表3形态（SQL访问的子能力表，4行）：含需求描述内枚举与方式名称
CAP_TABLE_SUB = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td></td><td><p>数据库操作</p></td>"
    "<td><p>PZXQ-GN-SQLFW-SJKCZ</p></td>"
    "<td><p>数据库操作功能包括数据库初始化、数据库关闭功能</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段、开发阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td></td><td><p>修改数据</p></td>"
    "<td><p>PZXQ-GN-SQLFW-XGSJ</p></td>"
    "<td><p>修改数据功能包括删除数据记录、增加数据记录、修改数据记录功能</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段、开发阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td></td><td><p>查询数据</p></td>"
    "<td><p>PZXQ-GN-SQLFW-CXSJ</p></td>"
    "<td><p>查询数据功能包括数据查询、获取错误信息功能</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段、开发阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td></td><td><p>BLOB数据操作</p></td>"
    "<td><p>PZXQ-GN-SQLFW-BLOBSJCZ</p></td>"
    "<td><p>BLOB数据操作功能包括BLOB数据插入、BLOB数据查询功能</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面</p></td>"
    "<td><p>运行阶段、开发阶段</p></td><td><p>4.1.1</p></td></tr>"
    "</tbody></table>"
)

#: 表9形态（修改数据的子表，3行）：方式名称含错别字「平版」；
#: 行ID带XGSJ父段（3.2.1.2节标题形态），父绑定取自表3的修改数据行
CAP_TABLE_XGSJ = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td></td><td><p>删除数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-XGSJ-SJXG</p></td><td><p>支持删除数据记录</p></td>"
    "<td><p>沿用</p></td><td><p>桌面、平版、手持</p></td>"
    "<td><p>开发阶段、运行阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td></td><td><p>增加数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-XGSJ-ZXSW</p></td><td><p>支持增加数据记录</p></td>"
    "<td><p>沿用</p></td><td><p>桌面、平版、手持</p></td>"
    "<td><p>开发阶段、运行阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td></td><td><p>修改数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-XGSJ-TJSW</p></td><td><p>支持修改数据记录</p></td>"
    "<td><p>沿用</p></td><td><p>桌面、平版、手持</p></td>"
    "<td><p>开发阶段、运行阶段</p></td><td><p>4.1.1</p></td></tr>"
    "</tbody></table>"
)

#: 真实04文档表9形态：行ID只带SQLFW父段（与表3的行共用PZXQ-GN-SQLFW
#: 父前缀）——用于验证行聚合按块隔离，不跨表合并
CAP_TABLE_XGSJ_FLAT = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td></td><td><p>删除数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-SJXG</p></td><td><p>支持删除数据记录</p></td>"
    "<td><p>沿用</p></td><td><p>桌面、平版、手持</p></td>"
    "<td><p>开发阶段、运行阶段</p></td><td><p>4.1.1</p></td></tr>"
    "<tr><td></td><td><p>增加数据记录</p></td>"
    "<td><p>PZXQ-GN-SQLFW-ZXSW</p></td><td><p>支持增加数据记录</p></td>"
    "<td><p>沿用</p></td><td><p>桌面、平版、手持</p></td>"
    "<td><p>开发阶段、运行阶段</p></td><td><p>4.1.1</p></td></tr>"
    "</tbody></table>"
)

#: 表32形态（热点数据缓存的子表）：成员名与正文不一致（缓存更新vs缓存修改）
CAP_TABLE_RDSJHC = (
    "<table><thead><tr>"
    "<th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th>"
    "<th><p>运行状态</p></th><th><p>对应的任务书功能/性能</p></th>"
    "</tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>缓存添加</p></td>"
    "<td><p>PZXQ-GN-RDSJHC-HCTJ</p></td><td><p>支持将新的查询结果添加到缓存</p></td>"
    "<td><p>新研</p></td><td><p>桌面</p></td>"
    "<td><p>运行阶段</p></td><td><p>4.1.2</p></td></tr>"
    "<tr><td><p>2</p></td><td><p>缓存更新</p></td>"
    "<td><p>PZXQ-GN-RDSJHC-HCGX</p></td><td><p>支持更新缓存信息</p></td>"
    "<td><p>新研</p></td><td><p>桌面</p></td>"
    "<td><p>运行阶段</p></td><td><p>4.1.2</p></td></tr>"
    "<tr><td><p>3</p></td><td><p>缓存查询</p></td>"
    "<td><p>PZXQ-GN-RDSJHC-HCCX</p></td><td><p>支持查询缓存信息</p></td>"
    "<td><p>新研</p></td><td><p>桌面</p></td>"
    "<td><p>运行阶段</p></td><td><p>4.1.2</p></td></tr>"
    "</tbody></table>"
)

PROSE_SQLFW = ("SQL访问功能包括：数据库操作、修改数据、查询数据、逐行获取数据、"
               "BLOB数据操作功能，此功能在桌面版、平板版、手持版提供并使用，"
               "其功能用例如图3所示。")
PROSE_RDSJHC = "热点数据缓存包括缓存添加功能、缓存修改功能、缓存查询功能，其功能用例如图32所示。"
SECTION_RDSJHC = "3.2.3 热点数据缓存（PZXQ-GN-RDSJHC）"
GARBAGE_PROSE = "数据统一访问服务按照其功能需求，包含SQL访问、对象化访问、代码生成功能。"


def make_request(answer: str, *texts: str, question: str = "包括哪些功能？",
                 instance_id: str = "qa-enumjoin") -> QAInput:
    evidence = tuple(
        RetrievedEvidence(
            evidence_id=f"ev-{index:02d}",
            text=text,
            source_type="table" if "<table" in text else "text",
            source_ref=SourceRef(doc_id=DOC_ID, section=""),
            scope_id=f"{DOC_ID}:ev-{index:02d}",
            completeness="open",
        )
        for index, text in enumerate(texts, start=1)
    )
    return QAInput(
        instance_id=instance_id,
        question=question,
        answer=answer,
        context_freeze_id="frozen-enumjoin-1",
        evidence=evidence,
    )


def statements_of(*texts: str) -> list:
    return linearize_context(make_request("", *texts).evidence)


def refutes(results: list) -> list:
    return [r for r in results if r.verdict == "refute"]


def entry(registry: list, subject: str, source_field: str):
    return next(e for e in registry
                if e.subject == subject and e.source_field == source_field)


# ---------------------------------------------------------------- 基础工具

def test_levenshtein_basics() -> None:
    assert levenshtein("平板", "平板") == 0
    assert levenshtein("平版", "平板") == 1
    assert levenshtein("桌面", "平板") == 2
    assert levenshtein("手持", "平板") == 2
    assert levenshtein("开发阶段", "开发阶段") == 0
    assert levenshtein("缓存修改", "缓存更新") == 2
    assert levenshtein("桌面", "桌面版本") == 2
    assert levenshtein("abc", "") == 3


# ---------------------------------------------------------------- 注册表

def test_registry_field_entries_normalize_terminal_and_phase() -> None:
    registry = build_domain_registry(statements_of(CAP_TABLE_TOP))
    sqlfw = entry(registry, "SQL访问", "方式名称")
    assert sqlfw.members == ("平板", "桌面", "手持")
    assert sqlfw.statement_ids == ("ev-01#s3",)
    phase = entry(registry, "SQL访问", "运行状态")
    # 两个<p>块线性化为无分隔符的"运行阶段开发阶段"→按阶段词切分
    assert set(phase.members) == {"运行阶段", "开发阶段"}
    dmsc = entry(registry, "代码生成", "方式名称")
    assert dmsc.members == ("桌面",)
    assert entry(registry, "SQL访问", "需求重用").members == ("沿用",)


def test_registry_keeps_typo_member_and_strips_version_suffix() -> None:
    registry = build_domain_registry(
        statements_of(CAP_TABLE_XGSJ, CAP_TABLE_TOP))
    typo = entry(registry, "修改数据记录", "方式名称")
    # 错字"平版"保持原样（证据侧错字检测的输入）；"桌面版"→桌面
    assert set(typo.members) == {"桌面", "平版", "手持"}


def test_registry_prose_entries_and_garbage_subject_rejected() -> None:
    registry = build_domain_registry(statements_of(PROSE_SQLFW, GARBAGE_PROSE))
    prose = entry(registry, "SQL访问", "prose")
    assert prose.members == ("数据库操作", "修改数据", "查询数据",
                             "逐行获取数据", "BLOB数据操作")
    assert prose.statement_ids == ("ev-01#s0",)
    # "…按照其功能需求，包含…"是垃圾主体（按语功能词），不注册
    assert not [e for e in registry if e.source_field == "prose"
                and "按照" in e.subject]


def test_registry_row_enum_groups_rows_under_bound_parent() -> None:
    # 表2提供父绑定(PZXQ-GN-SQLFW→SQL访问)，表3的4行聚合成SQL访问的
    # 封闭能力行集合
    registry = build_domain_registry(statements_of(CAP_TABLE_TOP, CAP_TABLE_SUB))
    row_enum = entry(registry, "SQL访问", "row_enum")
    assert row_enum.members == ("数据库操作", "修改数据", "查询数据",
                                "BLOB数据操作")
    assert row_enum.statement_ids == ("ev-02#s0", "ev-02#s6", "ev-02#s12",
                                      "ev-02#s18")
    # 表9经表3的XGSJ绑定聚到修改数据名下
    registry9 = build_domain_registry(
        statements_of(CAP_TABLE_SUB, CAP_TABLE_XGSJ))
    xgsj = entry(registry9, "修改数据", "row_enum")
    assert xgsj.members == ("删除数据记录", "增加数据记录", "修改数据记录")
    # 无父绑定时（表2孤表）：顶层行不聚合（父ID未注册）
    alone = build_domain_registry(statements_of(CAP_TABLE_TOP))
    assert not [e for e in alone if e.source_field == "row_enum"]


def test_registry_row_enum_isolated_per_block() -> None:
    # 真实04文档表9的行ID与表3的行共用PZXQ-GN-SQLFW父前缀，但两表分属
    # 不同块→两个独立的row_enum条目，不跨表并成一个7成员封闭集合
    registry = build_domain_registry(
        statements_of(CAP_TABLE_TOP, CAP_TABLE_SUB, CAP_TABLE_XGSJ_FLAT))
    row_enums = [e for e in registry
                 if e.source_field == "row_enum" and e.subject == "SQL访问"]
    assert len(row_enums) == 2
    member_sets = {e.members for e in row_enums}
    assert ("数据库操作", "修改数据", "查询数据", "BLOB数据操作") in member_sets
    assert ("删除数据记录", "增加数据记录") in member_sets
    assert all(len(e.members) != 6 for e in row_enums)


def test_registry_section_title_binding_feeds_row_enum() -> None:
    # 节标题"3.2.3 热点数据缓存（PZXQ-GN-RDSJHC）"提供父绑定
    registry = build_domain_registry(
        statements_of(SECTION_RDSJHC, CAP_TABLE_RDSJHC))
    row_enum = entry(registry, "热点数据缓存", "row_enum")
    assert row_enum.members == ("缓存添加", "缓存更新", "缓存查询")


# ---------------------------------------------------------------- 声明提取

def test_extract_enum_assertions_include_forms() -> None:
    assertions = extract_enum_assertions(
        "SQL访问功能包括数据库操作、修改数据、查询数据、逐行获取数据、"
        "BLOB数据操作五项功能。", "SQL访问功能包括哪些功能？")
    assert len(assertions) == 1
    assertion = assertions[0]
    assert assertion.subjects == ("SQL访问",)
    # raw保留"五项功能"（claim_text与旧enum通道对齐），归一化成员剥离
    assert assertion.raw_members[-1] == "BLOB数据操作五项功能"
    assert assertion.members[-1] == "BLOB数据操作"
    assert assertion.kind == "functional"
    assert assertion.closed
    assert assertion.claim_text == ("数据库操作、修改数据、查询数据、"
                                    "逐行获取数据、BLOB数据操作五项功能")

    assertions = extract_enum_assertions(
        "修改数据功能的支持方式包括桌面、平板、手持。",
        "修改数据功能以哪些方式名称提供？")
    assert assertions[0].subjects == ("修改数据",)
    assert assertions[0].members == ("桌面", "平板", "手持")
    assert assertions[0].kind == "terminal"


def test_extract_enum_assertions_device_form_uses_question_subject() -> None:
    # 泛指anaphor（所有操作均…）→回退问题主题"SQL访问修改数据"
    assertions = extract_enum_assertions(
        "所有操作均支持在桌面、平版和平板设备上运行。",
        "SQL访问修改数据功能包括哪些操作")
    assert len(assertions) == 1
    assert assertions[0].raw_members == ("桌面", "平版", "平板")
    assert assertions[0].subjects[0] == "SQL访问修改数据"
    assert assertions[0].kind == "terminal"  # 平版是平板的距离1错字


def test_extract_enum_assertions_rejects_garbage() -> None:
    # markdown成员/单成员/"但不限于"开放引导/垃圾主体/泛指主体→整条拒绝
    assert extract_enum_assertions(
        "BLOB数据操作包括以下具体操作：\n1. **插入**：允许插入新数据。",
        "BLOB数据操作涉及哪些具体操作") == []
    assert extract_enum_assertions("该功能包括桌面、平板、手持。",
                                   "哪些功能？") == []
    assert extract_enum_assertions(
        "数据库连接需要提供的参数包括但不限于用户名、密码、IP地址。",
        "需要哪些参数？") == []
    assert extract_enum_assertions(
        "常见场景包括数据统计、库存管理、成绩评分和生成报告等。",
        "在什么场景下使用") == []
    assert extract_enum_assertions("修改数据包括删除数据记录。",
                                   "包括哪些操作") == []
    # 泛指句无问题主题可回退→无主体不提取
    assert extract_enum_assertions("这些操作均在桌面和平板上运行。",
                                   "用例是什么") == []


# ---------------------------------------------------------------- 三项检查

def test_check1_extra_member_refutes_s1qa074_shape() -> None:
    # BLOB数据操作方式名称注册为{平板、桌面}，answer多出手持
    request = make_request(
        "BLOB数据操作在桌面版、平板版和手持版上均可使用。",
        CAP_TABLE_SUB, question="BLOB数据操作涉及哪些具体操作")
    results = verify_enum_joins(request, statements_of(CAP_TABLE_SUB))
    fired = refutes(results)
    assert len(fired) == 1
    assert fired[0].claim_text == "桌面版、平板版、手持版"
    assert "手持" in fired[0].rationale
    assert "BLOB数据操作" in fired[0].rationale
    assert "ev-01#s21" in fired[0].evidence_refs


def test_check1_omission_and_answer_typo_refute_s1qa056_shape() -> None:
    # answer{桌面,平版,平板}：错字"平版"(→平板)+遗漏注册成员"手持"
    request = make_request(
        "所有操作均支持在桌面、平版和平板设备上运行。",
        CAP_TABLE_TOP, CAP_TABLE_SUB,
        question="SQL访问修改数据功能包括哪些操作")
    results = verify_enum_joins(
        request, statements_of(CAP_TABLE_TOP, CAP_TABLE_SUB))
    fired = refutes(results)
    assert len(fired) == 1
    assert "疑似错别字" in fired[0].rationale
    assert "平版" in fired[0].rationale and "平板" in fired[0].rationale
    assert "遗漏注册成员「手持」" in fired[0].rationale
    assert set(fired[0].evidence_refs) == {"ev-01#s3", "ev-02#s9"}


def test_check2_evidence_typo_refutes_vio09_shape() -> None:
    # 表9注册值"平版"是错字，answer声明正确值"平板"→证据侧错字
    request = make_request(
        "修改数据功能的支持方式包括桌面、平板、手持。",
        CAP_TABLE_SUB, CAP_TABLE_XGSJ,
        question="修改数据功能以哪些方式名称（终端形态）提供？")
    results = verify_enum_joins(
        request, statements_of(CAP_TABLE_SUB, CAP_TABLE_XGSJ))
    fired = refutes(results)
    assert len(fired) == 1
    assert "证据侧疑似错别字：平版→平板" in fired[0].rationale
    assert "ev-02#s15" in fired[0].evidence_refs


def test_check2_answer_typo_refutes_when_answer_introduces_typo() -> None:
    # 注册值为正确"平板"，answer写错字"平版"→answer侧错字
    request = make_request(
        "修改数据功能的支持方式包括桌面、平版、手持。", CAP_TABLE_SUB)
    results = verify_enum_joins(request, statements_of(CAP_TABLE_SUB))
    fired = refutes(results)
    assert len(fired) == 1
    assert "疑似错别字（应为「平板」）" in fired[0].rationale


def test_check1_cross_source_conflict_refutes_vio06_shape() -> None:
    # 正文5项 vs 表3能力行4行：answer成员逐行获取数据只见于正文侧
    texts = (CAP_TABLE_TOP, PROSE_SQLFW, CAP_TABLE_SUB)
    request = make_request(
        "SQL访问功能包括数据库操作、修改数据、查询数据、逐行获取数据、"
        "BLOB数据操作五项功能。", *texts, question="SQL访问功能包括哪些功能？")
    results = verify_enum_joins(request, statements_of(*texts))
    fired = refutes(results)
    assert len(fired) == 1
    assert "逐行获取数据" in fired[0].rationale
    assert "正文枚举" in fired[0].rationale and "能力表行" in fired[0].rationale
    assert set(fired[0].evidence_refs) == {
        "ev-02#s0", "ev-03#s0", "ev-03#s6", "ev-03#s12", "ev-03#s18"}


def test_check1_conflicting_member_name_refutes_vio07_shape() -> None:
    # 正文"缓存修改" vs 表32行"缓存更新"：同义成员名冲突
    texts = (SECTION_RDSJHC, PROSE_RDSJHC, CAP_TABLE_RDSJHC)
    request = make_request(
        "热点数据缓存包括缓存添加功能、缓存修改功能、缓存查询功能。",
        *texts, question="热点数据缓存包括哪些功能？")
    results = verify_enum_joins(request, statements_of(*texts))
    fired = refutes(results)
    assert len(fired) == 1
    assert "缓存修改" in fired[0].rationale
    assert "缓存更新" in fired[0].rationale
    assert set(fired[0].evidence_refs) == {
        "ev-02#s0", "ev-03#s0", "ev-03#s6", "ev-03#s12"}


def test_check3_open_enumeration_skips_extra_and_omission() -> None:
    # "包括…等"开放语义：不裁多出成员、不裁遗漏
    texts = (CAP_TABLE_TOP, CAP_TABLE_SUB)
    request = make_request(
        "修改数据功能包括删除数据记录、归档数据记录等。", *texts,
        question="修改数据功能包括哪些操作？")
    assert verify_enum_joins(request, statements_of(*texts)) == []


def test_unregistered_subject_and_consistent_set_emit_nothing() -> None:
    # 主体未注册→无仲裁对象，不产生claim
    request = make_request("缓存功能包括数据统计、库存管理、成绩评分。",
                            CAP_TABLE_TOP)
    assert verify_enum_joins(request, statements_of(CAP_TABLE_TOP)) == []
    # 集合完全一致→无冲突
    request = make_request(
        "修改数据功能的支持方式包括平板、桌面、手持。", CAP_TABLE_SUB)
    assert verify_enum_joins(request, statements_of(CAP_TABLE_SUB)) == []


def test_phase_members_consistent_no_conflict() -> None:
    request = make_request(
        "查询数据功能的运行状态分为开发阶段、运行阶段。", CAP_TABLE_SUB,
        question="查询数据功能的运行状态如何分类")
    assert verify_enum_joins(request, statements_of(CAP_TABLE_SUB)) == []


# ---------------------------------------------------------------- 真实数据

def load_row(path: Path, instance_id: str) -> dict:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["instance_id"] == instance_id:
                return row
    raise AssertionError(f"{instance_id} not found in {path}")


def test_real_s1qa_056_and_074_refute() -> None:
    for instance_id, expected_member in (
            ("S1QA-056", "手持"), ("S1QA-074", "手持")):
        row = load_row(QA_FROZEN, instance_id)
        request = request_from_dict(row)
        statements = linearize_context(request.evidence)
        results = verify_enum_joins(request, statements)
        fired = refutes(results)
        assert len(fired) == 1, instance_id
        assert fired[0].method == METHOD
        assert fired[0].check_item_candidates == ("TERM-03",)
        assert fired[0].confidence == 1.0
        assert expected_member in fired[0].rationale
        assert fired[0].evidence_refs


def test_real_violation_enum_triples_refute() -> None:
    expectations = {
        "DOC04-VIO-06": "逐行获取数据",
        "DOC04-VIO-07": "缓存修改",
        "DOC04-VIO-09": "平版",
    }
    for instance_id, keyword in expectations.items():
        row = load_row(VIOLATION_SET, instance_id)
        request = request_from_dict(row)
        statements = linearize_context(request.evidence)
        results = verify_enum_joins(request, statements)
        fired = refutes(results)
        assert len(fired) == 1, instance_id
        assert keyword in fired[0].rationale, instance_id
        # 定位refs命中该实例gold_evidence_refs（块级）
        gold_blocks = {ref.split("#", 1)[0] for ref in row["gold_evidence_refs"]}
        hit_blocks = {ref.split("#", 1)[0] for ref in fired[0].evidence_refs}
        assert hit_blocks & gold_blocks, instance_id


def test_registry_stats_on_doc04_frozen_blocks() -> None:
    # 04号真实数据（91QA+17违例的冻结证据块，按scope_id去重）上的
    # 注册表统计快照：81块/780语句→129条目/40主体
    blocks: dict[str, dict] = {}
    for path in (QA_FROZEN, VIOLATION_SET):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            for item in row["evidence"]:
                if "04数据统一访问" in item["scope_id"]:
                    blocks[item["scope_id"]] = item
    statements = []
    for item in blocks.values():
        evidence = RetrievedEvidence(
            evidence_id=item["evidence_id"], text=item["text"],
            source_type=item["source_type"],
            source_ref=SourceRef(**item["source_ref"]),
            scope_id=item["scope_id"])
        statements.extend(linearize_context((evidence,)))
    registry = build_domain_registry(statements)
    assert len(blocks) == 81
    assert len(statements) == 780
    assert len(registry) == 129
    subjects = {e.subject for e in registry}
    assert len(subjects) == 40
    assert {"SQL访问", "修改数据", "BLOB数据操作", "热点数据缓存"} <= subjects
    by_field: dict[str, int] = {}
    for item in registry:
        by_field[item.source_field] = by_field.get(item.source_field, 0) + 1
    assert by_field["方式名称"] >= 30
    assert by_field["row_enum"] >= 3
    assert by_field["prose"] >= 10


# ---------------------------------------------------------------- 模块集成

def test_module_refute_overrides_legacy_enum_support() -> None:
    # answer复现表9错字{桌面,平版,手持}：旧enum通道逐成员命中→support，
    # enum_join的refute在同claim文本上压制误support（refute>support）
    module = QAConsistencyModule(use_experts=True)
    request = make_request(
        "修改数据功能的支持方式包括桌面、平版、手持。",
        CAP_TABLE_SUB, CAP_TABLE_XGSJ,
        question="修改数据功能以哪些方式名称提供？")
    result = module.verify(request)
    assert result.verdict == "refute"
    fused = [claim for claim in result.claim_results
             if claim.claim_text == "桌面、平版、手持"]
    assert len(fused) == 1
    assert fused[0].verdict == "refute"
    assert fused[0].method == METHOD


def test_module_consistent_enum_answer_stays_supported() -> None:
    module = QAConsistencyModule(use_experts=True)
    request = make_request(
        "修改数据功能的支持方式包括平板、桌面、手持。", CAP_TABLE_SUB,
        question="修改数据功能以哪些方式名称提供？")
    result = module.verify(request)
    assert result.verdict == "support"
    assert not [claim for claim in result.claim_results
                if claim.method == METHOD]


def test_module_real_s1qa_074_end_to_end_refute() -> None:
    row = load_row(QA_FROZEN, "S1QA-074")
    module = QAConsistencyModule(use_experts=True)
    result = module.verify(request_from_dict(row))
    assert result.verdict == "refute"
    assert [claim for claim in result.claim_results
            if claim.method == METHOD]
