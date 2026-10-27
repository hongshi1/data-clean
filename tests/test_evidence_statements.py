"""Tests for deterministic evidence linearization."""
from __future__ import annotations

from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
    linearize_evidence,
)
from algorithms.consistency.qa_models import RetrievedEvidence, SourceRef  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402


def usecase_evidence() -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id="ev-1",
        text=("<table><tr><td><p>Use Case 名称：读取配置文件连接</p></td>"
              "<td colspan=\"2\"><p>Actors：应用软件</p></td></tr>"
              "<tr><td colspan=\"3\"><p>前置条件：数据库初始化成功</p></td></tr>"
              "<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>"
              "<td><p>动作约束（性能、可靠性、容错等）</p></td></tr>"
              "<tr><td><p>1.应用软件调用接口</p></td><td><p>2系统读取配置</p></td>"
              "<td><p>如果无法连接到服务端，提示连接错误</p></td></tr>"
              "<tr><td colspan=\"2\"><p>异常流E1：系统提示连接失败，用例结束</p></td>"
              "<td></td></tr></table>"),
        source_type="table",
        source_ref=SourceRef(doc_id="d", section="3.2.1", row_id="r3"),
        scope_id="d:3.2.1",
    )


def capability_evidence() -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id="ev-2",
        text=("<table><thead><tr><th><p>序号</p></th><th><p>Use case名称</p></th>"
              "<th><p>项目唯一标识符</p></th><th><p>需求描述</p></th>"
              "<th><p>方式名称</p></th></tr></thead><tbody>"
              "<tr><td><p>1</p></td><td><p>SQL访问功能</p></td>"
              "<td><p>PZXQ-GN-SQLFW</p></td>"
              "<td><p>提供原生SQL访问功能</p></td>"
              "<td><p>平板、桌面、手持</p></td></tr></tbody></table>"),
        source_type="table",
        source_ref=SourceRef(doc_id="d", section="3.2"),
        scope_id="d:3.2",
    )


def test_usecase_table_fields_are_linearized_with_scope() -> None:
    statements = linearize_evidence(usecase_evidence())
    texts = {s.text for s in statements}
    assert "前置条件：数据库初始化成功" in texts
    assert "异常流E1：系统提示连接失败，用例结束" in texts
    assert "读取配置文件连接Actor的动作：1.应用软件调用接口" in texts
    assert "读取配置文件连接动作约束：如果无法连接到服务端，提示连接错误" in texts
    scopes = {s.scope_key for s in statements}
    assert "读取配置文件连接" in scopes
    assert all(s.row_index > 0 for s in statements)
    assert all(s.statement_id.startswith("ev-1#s") for s in statements)


def test_capability_table_rows_become_keyed_statements() -> None:
    statements = linearize_evidence(capability_evidence())
    texts = {s.text for s in statements}
    assert "SQL访问功能的项目唯一标识符：PZXQ-GN-SQLFW" in texts
    assert "SQL访问功能的需求描述：提供原生SQL访问功能" in texts
    assert "SQL访问功能的方式名称：平板、桌面、手持" in texts
    assert all(s.scope_key == "SQL访问功能" for s in statements)


def test_text_evidence_splits_into_sentences() -> None:
    evidence = RetrievedEvidence(
        evidence_id="ev-3",
        text="SQL访问功能包括数据库操作、修改数据、查询数据功能。"
             "上述功能适用于桌面、平板、手持三种方式名称。",
        source_type="text",
        source_ref=SourceRef(doc_id="d", section="3.2"),
        scope_id="d:3.2",
    )
    statements = linearize_evidence(evidence)
    assert len(statements) == 2
    assert statements[0].text.startswith("SQL访问功能包括")
    assert statements[0].field_name == "sentence"


def test_real_frozen_evidence_linearizes_and_localizes() -> None:
    rows = [json_row for json_row in (
        json.loads(line) for line in
        (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
        .read_text(encoding="utf-8").splitlines() if line.strip())]
    request = request_from_dict(
        next(row for row in rows if row["instance_id"] == "S1QA-021"))
    statements = linearize_context(request.evidence)
    assert statements, "real use-case tables must linearize into statements"
    scoped = [s for s in statements if s.scope_key]
    assert len(scoped) / len(statements) > 0.3
    joined = " ".join(s.text for s in statements)
    assert "前置条件" in joined or "异常流" in joined
    assert all("#s" in s.statement_id for s in statements)


import json  # noqa: E402
