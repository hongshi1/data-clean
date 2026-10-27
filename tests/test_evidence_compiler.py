"""Tests for the S1 evidence compiler (typed table schemas + focused views)."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_structure import StructuredClaim  # noqa: E402
from algorithms.consistency.evidence_compiler import (  # noqa: E402
    claim_type,
    compile_and_focus,
    compile_evidence,
    focus_views,
    load_content_list_evidence,
    load_figure_evidence,
    parse_mermaid,
)
from algorithms.consistency.qa_models import RetrievedEvidence, SourceRef  # noqa: E402


def make_claim(text: str, hint: str = "", structure: str = "sentence",
               claim_id: str = "ac01") -> StructuredClaim:
    return StructuredClaim(text=text, scope_hint=hint, structure=structure,
                           claim_id=claim_id)


def make_evidence(evidence_id: str, text: str, source_type: str = "table",
                  section: str = "3.2") -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id=evidence_id,
        text=text,
        source_type=source_type,
        source_ref=SourceRef(doc_id="d", section=section, block_id=evidence_id),
        scope_id=f"d:{evidence_id}",
    )


CAPABILITY_HTML = (
    "<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
    "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
    "<th><p>需求重用</p></th><th><p>方式名称</p></th><th><p>运行状态</p></th>"
    "<th><p>对应的任务书功能/性能</p></th></tr></thead><tbody>"
    "<tr><td><p>1</p></td><td><p>SQL访问功能</p></td>"
    "<td><p>PZXQ-GN-SQLFW</p></td><td><p>提供原生SQL访问功能</p></td>"
    "<td><p>沿用</p></td><td><p>平板、桌面、手持</p></td>"
    "<td><p>运行阶段</p></td><td><p>4.1.1</p></td></tr></tbody></table>"
)

USE_CASE_HTML = (
    "<table><tr><td><p>Use Case 名称：查询数据</p></td>"
    "<td colspan=\"2\"><p>Actors：应用软件</p></td></tr>"
    "<tr><td colspan=\"3\"><p>概述：描述查询数据的过程；</p></td></tr>"
    "<tr><td colspan=\"3\"><p>前置条件：数据库连接正常。</p></td></tr>"
    "<tr><td colspan=\"3\"><p>主事件流</p></td></tr>"
    "<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>"
    "<td><p>动作约束（性能、可靠性、容错等）</p></td></tr>"
    "<tr><td><p>1.应用软件提交查询请求</p></td>"
    "<td><p>2.系统执行查询并返回结果集</p></td>"
    "<td><p>在5s内返回结果</p></td></tr>"
    "<tr><td colspan=\"2\"><p>异常流E1：查询失败，用例结束。</p></td></tr>"
    "<tr><td colspan=\"3\"><p>后置条件：无。</p></td></tr></table>"
)

INTERFACE_HTML = (
    "<table><tr><td><p>序号</p></td><td><p>接口需求名称</p></td>"
    "<td><p>接口需求标识</p></td><td><p>接口类型</p></td>"
    "<td><p>发送方</p></td><td><p>接收方</p></td><td><p>接口内容</p></td>"
    "<td><p>接口优先级</p></td></tr>"
    "<tr><td rowspan=\"2\"><p>1</p></td>"
    "<td rowspan=\"2\"><p>数据统一访问服务与应用软件接口</p></td>"
    "<td rowspan=\"2\"><p>PZXQ-JK-SJTYFW-YYRJ</p></td>"
    "<td rowspan=\"2\"><p>API接口</p></td><td><p>本系统</p></td>"
    "<td><p>应用软件</p></td><td><p>数据查询信息</p></td>"
    "<td rowspan=\"2\"><p>中</p></td></tr>"
    "<tr><td><p>应用软件</p></td><td><p>本系统</p></td>"
    "<td><p>删除数据记录信息</p></td></tr></table>"
)

VALUE_DOMAIN_HTML = (
    "<table><tr><td><p>序号</p></td><td><p>数据项</p></td>"
    "<td><p>最大差</p></td><td><p>最小差</p></td><td><p>精度</p></td>"
    "<td><p>单位</p></td></tr>"
    "<tr><td></td><td><p>查询状态</p></td><td><p>1</p></td><td><p>0</p></td>"
    "<td><p>1</p></td><td><p>字符</p></td></tr>"
    "<tr><td></td><td><p>数据内容</p></td><td><p>2097152</p></td><td><p>0</p></td>"
    "<td><p>1</p></td><td><p>字符</p></td></tr></table>"
)

TRACE_FORWARD_HTML = (
    "<table><thead><tr><th><p><strong>软件研制任务书名称/标识</strong></p></th>"
    "<th><p><strong>软件研制任务书的章节号</strong></p></th>"
    "<th><p><strong>本文档的名称/标识</strong></p></th>"
    "<th><p><strong>本文档的章节号</strong></p></th>"
    "<th><p><strong>跟踪说明</strong></p></th></tr></thead><tbody>"
    "<tr><td><p>原生SQL访问</p></td><td><p>4.1.1 b）</p></td>"
    "<td><p>SQL访问</p></td><td><p>3.2.1</p></td><td></td></tr></tbody></table>"
)

TRACE_REVERSE_HTML = (
    "<table><thead><tr><th><p>本文档名称/标识</p></th><th><p>本文档章节号</p></th>"
    "<th><p>任务书名称/标识</p></th><th><p>任务书章节号</p></th>"
    "<th><p>跟踪说明</p></p></th></tr></thead><tbody>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td>"
    "<td><p>原生SQL访问</p></td><td><p>4.1.1 b）</p></td><td></td></tr></tbody></table>"
)

QUALIFICATION_HTML = (
    "<table><tr><td><p>需求名称/标识</p></td><td><p>本文档的章节号</p></td>"
    "<td><p>合格性方法</p></td><td><p>合格性级别</p></td></tr>"
    "<tr><td><p>SQL访问</p></td><td><p>3.2.1</p></td><td><p>A、B、D</p></td>"
    "<td><p>a、b</p></td></tr></table>"
)


def test_claim_type_classification() -> None:
    assert claim_type(make_claim("该接口的标识为PZXQ-GN-SQLFW")) == "identifier"
    assert claim_type(make_claim("连接失败时执行异常流E1")) == "exception"
    assert claim_type(make_claim("数据内容最大2097152字符")) == "numeric"
    assert claim_type(make_claim("应用软件提交查询请求", structure="step")) == "step"
    assert claim_type(make_claim("支持平板、桌面、手持三种方式")) == "enumeration"
    assert claim_type(make_claim("系统由多个相互独立的模块组成")) == "generic"


def test_parse_mermaid_shapes_and_arrows() -> None:
    code = (
        "flowchart TD\n"
        "    N1[\"开始\"]\n"
        "    N2{\"选择\"}\n"
        "    N3([\"结束\"])\n"
        "    N4(\"数据\")\n"
        "    N1 -->|\"是\"| N2\n"
        "    N2 --- N3\n"
        "    N2 -.-> N4\n"
    )
    nodes, edges = parse_mermaid(code)
    shapes = {node.node_id: node.shape for node in nodes}
    assert shapes == {
        "N1": "process", "N2": "decision", "N3": "terminal", "N4": "data",
    }
    assert [(edge.src_id, edge.dst_id, edge.label, edge.directed) for edge in edges] == [
        ("N1", "N2", "是", True),
        ("N2", "N3", "", False),
        ("N2", "N4", "", True),
    ]


def test_six_table_kinds_recognized_from_synthetic_html() -> None:
    evidence = (
        make_evidence("ev-cap", CAPABILITY_HTML),
        make_evidence("ev-uc", USE_CASE_HTML),
        make_evidence("ev-itf", INTERFACE_HTML),
        make_evidence("ev-vd", VALUE_DOMAIN_HTML),
        make_evidence("ev-tr-f", TRACE_FORWARD_HTML),
        make_evidence("ev-tr-r", TRACE_REVERSE_HTML),
        make_evidence("ev-qual", QUALIFICATION_HTML),
    )
    schema = compile_evidence(evidence)
    counts = schema.kind_counts()
    assert counts == {
        "capability_table": 1,
        "use_case_table": 1,
        "interface_table": 1,
        "value_domain_table": 1,
        "trace_table": 2,
        "qualification_table": 1,
    }
    capability = schema.tables_of_kind("capability_table")[0]
    assert capability.columns == (
        "序号", "Use case名称", "项目唯一标识符", "需求描述",
        "需求重用", "方式名称", "运行状态", "对应任务书",
    )
    assert ("项目唯一标识符", "PZXQ-GN-SQLFW") in capability.rows[0].cells

    use_case = schema.tables_of_kind("use_case_table")[0]
    fields = {row.field for row in use_case.rows}
    assert {
        "Use Case名称", "Actors", "概述", "前置条件",
        "主事件流", "异常流E1", "后置条件",
    } <= fields
    flow = next(row for row in use_case.rows if row.field == "主事件流")
    assert [column for column, _value in flow.cells] == [
        "Actor动作", "系统动作", "动作约束",
    ]

    value_domain = schema.tables_of_kind("value_domain_table")[0]
    assert value_domain.columns == (
        "序号", "数据项", "最大值", "最小值", "精度", "单位",
    )
    data_row = next(row for row in value_domain.rows if row.key == "数据内容")
    assert ("最大值", "2097152") in data_row.cells

    forward, reverse = schema.tables_of_kind("trace_table")
    assert (forward.direction, reverse.direction) == ("forward", "reverse")

    qualification = schema.tables_of_kind("qualification_table")[0]
    assert ("合格性方法", "A、B、D") in qualification.rows[0].cells


def test_interface_rowspan_continuation_reconstructed() -> None:
    schema = compile_evidence((make_evidence("ev-itf", INTERFACE_HTML),))
    table = schema.tables_of_kind("interface_table")[0]
    continuation = next(
        row for row in table.rows
        if ("接口内容", "删除数据记录信息") in row.cells
    )
    assert continuation.key == "数据统一访问服务与应用软件接口"
    assert ("序号", "1") in continuation.cells
    assert ("接口需求标识", "PZXQ-JK-SJTYFW-YYRJ") in continuation.cells
    assert ("发送方", "应用软件") in continuation.cells
    assert ("接收方", "本系统") in continuation.cells
    assert ("接口优先级", "中") in continuation.cells


def test_synthetic_focused_views_route_by_claim_type() -> None:
    evidence = (
        make_evidence("ev-cap", CAPABILITY_HTML),
        make_evidence("ev-uc", USE_CASE_HTML),
        make_evidence("ev-vd", VALUE_DOMAIN_HTML),
        make_evidence("ev-tr-f", TRACE_FORWARD_HTML),
        make_evidence("ev-qual", QUALIFICATION_HTML),
        make_evidence(
            "ev-text",
            "查询数据功能支持多种输出形式。"
            "查询结果能够以逐行获取、二维数据组、json格式、sql文件四种形式返回。",
            source_type="text",
        ),
    )
    claims = [
        make_claim("数据内容的数据项最大值为2097152字符", "数据内容", "sentence", "ac-n"),
        make_claim("SQL访问功能的项目唯一标识符为PZXQ-GN-SQLFW", "SQL访问功能",
                   "sentence", "ac-i"),
        make_claim("SQL访问功能适用于平板、桌面、手持三种方式", "SQL访问",
                   "sentence", "ac-e"),
        make_claim("连接失败时系统执行异常流E1并提示错误", "查询数据", "sentence", "ac-x"),
        make_claim("应用软件提交查询请求", "查询数据", "step", "ac-s"),
        make_claim("SQL访问章节映射到任务书4.1.1章节", "SQL访问", "sentence", "ac-t"),
        make_claim("SQL访问的合格性方法为A、B、D", "SQL访问", "sentence", "ac-q"),
        make_claim("查询结果以逐行获取、二维数组、json格式、sql文件四种形式返回",
                   "查询数据", "sentence", "ac-en"),
    ]
    schema, views = compile_and_focus(evidence, claims)
    by_claim = {
        claim_id: [view for view in views if view.claim_id == claim_id]
        for claim_id in ("ac-n", "ac-i", "ac-e", "ac-x", "ac-s", "ac-t", "ac-q", "ac-en")
    }

    numeric = next(v for v in by_claim["ac-n"] if v.table_kind == "value_domain_table")
    assert numeric.row_keys == ("数据内容",)
    assert set(numeric.columns) == {"数据项", "最大值", "最小值", "精度", "单位"}
    assert ("最大值", "2097152") in numeric.cells
    assert ("单位", "字符") in numeric.cells

    identifier = next(
        v for v in by_claim["ac-i"] if v.table_kind == "capability_table")
    assert identifier.row_keys == ("SQL访问功能",)
    assert set(identifier.columns) == {"Use case名称", "项目唯一标识符"}
    assert ("项目唯一标识符", "PZXQ-GN-SQLFW") in identifier.cells

    enumeration = next(
        v for v in by_claim["ac-e"] if v.table_kind == "capability_table")
    assert ("方式名称", "平板、桌面、手持") in enumeration.cells
    assert "方式名称" in enumeration.columns

    exception = next(
        v for v in by_claim["ac-x"] if v.table_kind == "use_case_table")
    assert exception.row_keys == ("查询数据",)
    assert exception.columns == ("异常流E1",)
    assert ("异常流E1", "查询失败，用例结束。") in exception.cells

    step = next(v for v in by_claim["ac-s"] if v.table_kind == "use_case_table")
    assert step.row_keys == ("查询数据",)
    assert step.columns == ("Actor动作", "系统动作", "动作约束")
    assert ("Actor动作", "1.应用软件提交查询请求") in step.cells
    assert ("动作约束", "在5s内返回结果") in step.cells

    trace = next(v for v in by_claim["ac-t"] if v.table_kind == "trace_table")
    assert ("本文档章节号", "3.2.1") in trace.cells
    assert ("任务书章节号", "4.1.1 b）") in trace.cells
    assert trace.columns == schema.tables_of_kind("trace_table")[0].columns

    qualification = next(
        v for v in by_claim["ac-q"] if v.table_kind == "qualification_table")
    assert qualification.row_keys == ("SQL访问",)
    assert ("合格性方法", "A、B、D") in qualification.cells
    assert ("章节号", "3.2.1") in qualification.cells

    text_views = [v for v in by_claim["ac-en"] if v.evidence_kind == "text"]
    assert text_views
    statements = [s for v in text_views for s in v.statements]
    assert any("四种形式返回" in s for s in statements)
    assert all("多种输出形式" not in s for s in statements)


def test_doc04_real_schema_compiles_six_table_kinds() -> None:
    evidence = load_content_list_evidence("04*")
    table_blocks = [b for b in evidence if b.source_type == "table"]
    assert len(evidence) == 360
    assert len(table_blocks) == 82
    schema = compile_evidence(evidence)
    assert len(schema.tables) == 82
    assert len(schema.texts) == 278
    assert schema.kind_counts() == {
        "capability_table": 11,
        "use_case_table": 35,
        "interface_table": 2,
        "value_domain_table": 5,
        "trace_table": 2,
        "qualification_table": 1,
        "generic_table": 26,
    }

    capability = next(
        t for t in schema.tables_of_kind("capability_table")
        if any(row.key == "SQL访问功能" for row in t.rows)
    )
    cap_row = next(row for row in capability.rows if row.key == "SQL访问功能")
    assert ("项目唯一标识符", "PZXQ-GN-SQLFW") in cap_row.cells
    assert ("方式名称", "平板、桌面、手持") in cap_row.cells
    assert "对应任务书" in capability.columns

    use_case = next(
        t for t in schema.tables_of_kind("use_case_table")
        if any(row.key == "数据库初始化" for row in t.rows)
    )
    fields = {row.field for row in use_case.rows if row.key == "数据库初始化"}
    assert {
        "Use Case名称", "Actors", "概述", "前置条件",
        "主事件流", "异常流E1", "后置条件",
    } <= fields
    flow = next(
        row for row in use_case.rows
        if row.key == "数据库初始化" and row.field == "主事件流"
    )
    assert [column for column, _value in flow.cells] == [
        "Actor动作", "系统动作", "动作约束",
    ]
    assert "应用软件调用数据库初始化接口" in flow.cells[0][1]

    interface = next(
        t for t in schema.tables_of_kind("interface_table")
        if "外部接口" in t.caption
    )
    continuation = next(
        row for row in interface.rows
        if ("接口内容", "删除数据记录信息") in row.cells
    )
    assert continuation.key == "数据统一访问服务与应用软件接口"
    assert ("发送方", "应用软件") in continuation.cells
    assert ("接口优先级", "中") in continuation.cells

    directions = sorted(
        t.direction for t in schema.tables_of_kind("trace_table"))
    assert directions == ["forward", "reverse"]

    value_domain = next(
        t for t in schema.tables_of_kind("value_domain_table")
        if any(row.key == "数据内容" for row in t.rows)
    )
    data_row = next(row for row in value_domain.rows if row.key == "数据内容")
    assert ("最大值", "2097152") in data_row.cells
    assert ("单位", "字符") in data_row.cells

    qualification = schema.tables_of_kind("qualification_table")[0]
    qual_row = next(
        row for row in qualification.rows if row.key == "SQL访问")
    assert ("章节号", "3.2.1") in qual_row.cells
    assert ("合格性方法", "A、B、D") in qual_row.cells


def test_doc04_real_focused_views_route_by_claim_type() -> None:
    schema = compile_evidence(load_content_list_evidence("04*"))
    claims = [
        make_claim("数据内容的数据项最大值为2097152字符", "数据内容", "sentence", "ac-n"),
        make_claim("SQL访问功能的项目唯一标识符为PZXQ-GN-SQLFW", "SQL访问功能",
                   "sentence", "ac-i"),
        make_claim("SQL访问功能适用于平板、桌面、手持三种方式", "SQL访问",
                   "sentence", "ac-e"),
        make_claim("连接失败时系统执行异常流E1并提示错误", "数据库初始化",
                   "sentence", "ac-x"),
        make_claim("应用软件调用数据库初始化接口输入相关参数", "数据库初始化",
                   "step", "ac-s"),
        make_claim("SQL访问与代码生成接口的接口需求标识为PZXQ-NBJK-SQLFW-DMSC",
                   "SQL访问与代码生成", "sentence", "ac-ii"),
    ]
    views = focus_views(schema, claims)
    assert views

    numeric = next(
        v for v in views
        if v.claim_id == "ac-n" and v.table_kind == "value_domain_table")
    assert numeric.row_keys == ("数据内容",)
    assert set(numeric.columns) == {"数据项", "最大值", "最小值", "精度", "单位"}
    assert ("最大值", "2097152") in numeric.cells

    identifier = next(
        v for v in views
        if v.claim_id == "ac-i" and v.table_kind == "capability_table")
    assert identifier.row_keys == ("SQL访问功能",)
    assert ("项目唯一标识符", "PZXQ-GN-SQLFW") in identifier.cells

    enumeration = next(
        v for v in views
        if v.claim_id == "ac-e" and v.table_kind == "capability_table")
    assert ("方式名称", "平板、桌面、手持") in enumeration.cells
    text_views = [
        v for v in views
        if v.claim_id == "ac-e" and v.evidence_kind == "text"
    ]
    assert text_views
    assert any(
        "、" in sentence for v in text_views for sentence in v.statements
    )

    exception = next(
        v for v in views
        if v.claim_id == "ac-x" and v.table_kind == "use_case_table")
    assert exception.row_keys == ("数据库初始化",)
    assert ("异常流E1", "系统提示初始化失败，用例结束。") in exception.cells

    step = next(
        v for v in views
        if v.claim_id == "ac-s" and v.table_kind == "use_case_table")
    assert step.row_keys == ("数据库初始化",)
    assert step.columns == ("Actor动作", "系统动作", "动作约束")
    assert any(
        "应用软件调用数据库初始化接口" in value for _column, value in step.cells
    )

    interface = next(
        v for v in views
        if v.claim_id == "ac-ii" and v.table_kind == "interface_table")
    assert interface.row_keys == ("SQL访问与代码生成接口",)
    assert ("接口需求标识", "PZXQ-NBJK-SQLFW-DMSC") in interface.cells


def test_doc04_figure_evidence_ingested_from_mermaid_export() -> None:
    blocks = load_figure_evidence("04")
    assert len(blocks) == 64
    assert all(block.source_type == "figure" for block in blocks)
    assert all(block.text.startswith("flowchart") for block in blocks)

    schema, views = compile_and_focus(blocks, [
        make_claim("数据统一访问服务软件包含SQL访问、对象化访问、代码生成功能",
                   claim_id="ac-f"),
    ])
    assert len(schema.figures) == 64
    first = schema.figures[0]
    assert first.diagram_type == "flowchart"
    assert {node.label for node in first.nodes} >= {
        "数据统一访问服务软件", "SQL访问", "对象化访问",
    }
    assert all(edge.directed for edge in first.edges)
    assert any(edge.label == "1" for edge in first.edges)

    all_labels = {
        node.label for graph in schema.figures for node in graph.nodes
    }
    assert "连接池管理" in all_labels

    figure_view = next(
        v for v in views if v.evidence_id == "04-fig-000")
    assert {"SQL访问", "对象化访问", "代码生成"} <= set(figure_view.node_labels)
    assert any("SQL访问" in edge for edge in figure_view.figure_edges)
    assert all(v.evidence_kind == "figure" for v in views)
