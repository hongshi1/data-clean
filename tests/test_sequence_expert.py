"""序列对齐专家(L1组件, LOGIC-03事件时序)契约测试.

真实锚点: S1QA-024(04号SRS表16二维数组输出用例, 官方冻结context);
已知违例: 表28数据插入Actor列无编号(b162). BGE测试在本机模型缺失或
torch不可用时跳过(保持套件可移植), 其余全部确定性.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import replace
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.common.bge_local import BASE as BGE_BASE, BgeLocal  # noqa: E402
from algorithms.consistency.answer_structure import (  # noqa: E402
    StructuredClaim,
    decompose_answer,
)
from algorithms.consistency.evidence_statements import linearize_context  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from algorithms.consistency.sequence_expert import (  # noqa: E402
    aggregate_sequence_verdict,
    align_sequences,
    char_jaccard,
    extract_answer_steps,
    extract_flow_steps,
    is_sequence_applicable,
    needleman_wunsch,
    resolve_flow_scope,
    verify_sequence,
)
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
USECASE_TABLE_EV = "S1QA-024-ev-000101"
_MODEL_DIR = BGE_BASE / "models" / "embedding" / "bge-large-zh-v1.5"
requires_bge = pytest.mark.skipif(
    not (_MODEL_DIR / "config.json").exists()
    or importlib.util.find_spec("torch") is None,
    reason="本地bge模型或torch不可用")

# 表28 数据插入用例描述(04号SRS真实HTML形态; b162已知违例:
# Actor列首段无编号, 系统列用全角句点"2．/3．")
B162_TABLE_HTML = (
    '<table><tr><td><p>Use Case 名称：数据插入</p></td>'
    '<td colspan="2"><p>Actors：应用软件、数据库</p></td></tr>'
    '<tr><td colspan="3"><p>概述：本用例是对象化访问的扩展用例，'
    '描述数据插入的过程；</p></td></tr>'
    '<tr><td colspan="3"><p>前置条件：数据库连接正常。</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p><p>（性能、可靠性、容错等）</p></td></tr>'
    '<tr><td><p>应用软件调用对象化数据插入接口并输入相应参数，'
    '如要插入数据的类；</p><p>4.数据库完成数据插入操作。</p></td>'
    '<td><p>2．将类转换成sql语句；</p>'
    '<p>3．调用数据库句柄执行sql语句。</p></td>'
    '<td><p>每个BLOB数据大小应不大于65535字节。</p></td></tr>'
    '<tr><td colspan="2"><p>异常流E1：系统提示插入失败，用例结束。</p>'
    '</td><td></td></tr>'
    '<tr><td colspan="2"><p>后置条件：无。</p></td><td></td></tr></table>')


def _load_frozen(instance_id: str) -> QAInput:
    rows = [json.loads(line) for line in
            FROZEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    return request_from_dict(
        next(row for row in rows if row["instance_id"] == instance_id))


def _b162_statements() -> list:
    evidence = RetrievedEvidence(
        "ev-b162", B162_TABLE_HTML, "table",
        SourceRef("04数据统一访问服务软件需求规格说明-终稿",
                  section="3.2.2.1"),
        "scope-b162")
    return linearize_context((evidence,))


# ── 证据侧提取(真实S1QA-024 + b162违例) ──────────────────


def test_extract_flow_steps_real_usecase_table() -> None:
    request = _load_frozen("S1QA-024")
    statements = linearize_context(request.evidence)
    scope = resolve_flow_scope(request.question, [], statements)
    assert scope == "二维数组输出"
    steps = extract_flow_steps(statements, scope)
    numbered = [s for s in steps if s.number is not None]
    assert [s.number for s in numbered] == [1, 2]
    assert numbered[0].field_name == "Actor的动作"
    assert "调用通过二维数据获取数据的接口" in numbered[0].text
    assert numbered[1].field_name == "系统的动作"
    assert "将查询结果组织到二维数组中返回" in numbered[1].text
    exception = [s for s in steps if s.field_name == "异常流E1"]
    assert len(exception) == 1
    # 异常流定位在全部编号步骤之后(文档序: 主事件流后)
    assert exception[0].position > max(s.position for s in numbered)
    assert exception[0].evidence_id == USECASE_TABLE_EV


def test_b162_unnumbered_actor_step_infers_missing_number() -> None:
    """已知违例: Actor列无编号段按缺失编号推断为第1步; 全角句点混排可解析."""
    steps = extract_flow_steps(_b162_statements(), "数据插入")
    numbered = [s for s in steps if s.number is not None]
    assert [s.number for s in numbered] == [1, 2, 3, 4]
    assert "应用软件调用对象化数据插入接口" in numbered[0].text
    assert numbered[0].field_name == "Actor的动作"
    assert numbered[1].text == "将类转换成sql语句"
    assert numbered[2].text == "调用数据库句柄执行sql语句"
    assert numbered[3].text == "数据库完成数据插入操作"
    assert any(s.field_name == "异常流E1" for s in steps)


def test_resolve_flow_scope_single_scope_fallback() -> None:
    statements = _b162_statements()
    # question无名称时回退唯一用例scope
    assert resolve_flow_scope("主事件流包括哪些步骤？", [], statements) \
        == "数据插入"


# ── answer侧提取 ─────────────────────────────────────────


def test_extract_answer_steps_links_structured_claims() -> None:
    answer = ("二维数组输出的主事件流包括以下具体操作：\n\n"
              "1. **调用二维数据获取数据接口**：应用软件通过相关参数"
              "（如数据库句柄）调用该接口。\n"
              "2. **组织查询结果为二维数组**：将收集到的数据按照每条记录"
              "的字段数作为列数，记录数作为行数，返回给系统。\n"
              "3. **处理失败情况**：在数据获取失败时，执行异常流E1，"
              "提示连接错误并结束用例。\n\n"
              "这些操作确保了二维数组输出过程的有效性和可靠性。")
    claims = decompose_answer(answer, "二维数组输出的主事件流包括哪些具体操作？")
    steps = extract_answer_steps(answer, claims)
    assert [s.number for s in steps] == [1, 2, 3]
    assert steps[0].claim_id == "ac02"  # ac01=导语, 不入步骤
    assert steps[1].claim_id == "ac03"
    assert steps[2].claim_id == "ac04"
    assert "调用二维数据获取数据接口" in steps[0].text


def test_extract_answer_steps_fallback_to_step_claims() -> None:
    """无编号answer回退step claims出现序; 导语/结语过滤; 单条不成序列."""
    claims = [
        StructuredClaim(text="数据插入的主事件流包括以下操作",
                        scope_hint="数据插入", structure="step",
                        claim_id="ac01"),
        StructuredClaim(text="应用软件调用对象化数据插入接口并输入参数",
                        scope_hint="", structure="step", claim_id="ac02"),
        StructuredClaim(text="系统将类转换成sql语句", scope_hint="",
                        structure="step", claim_id="ac03"),
        StructuredClaim(text="这些操作确保插入有效", scope_hint="",
                        structure="step", claim_id="ac04"),
    ]
    steps = extract_answer_steps("主事件流无编号描述。", claims)
    assert [s.text for s in steps] == [
        "应用软件调用对象化数据插入接口并输入参数", "系统将类转换成sql语句"]
    assert [s.claim_id for s in steps] == ["ac02", "ac03"]
    assert all(s.number is None for s in steps)
    # 仅剩单条step claim(非序列)时回退失效
    assert extract_answer_steps(
        "该用例包含两个步骤。",
        [StructuredClaim(text="该用例包含两个步骤", scope_hint="",
                         structure="step", claim_id="ac01")]) == []


def test_answer_without_steps_returns_empty() -> None:
    request = _load_frozen("S1QA-024")
    statements = linearize_context(request.evidence)
    request2 = replace(request, answer="该用例包含两个步骤。")
    assert verify_sequence(request2, statements, None, use_bge=False) == []


# ── 适用性门: 并列枚举不做二次分解(G4 P1粒度治理) ──────────


def _steps_of(answer: str, question: str) -> list:
    claims = decompose_answer(answer, question)
    return extract_answer_steps(answer, claims)


FEATURE_LIST_ANSWER = (
    "热点数据缓存功能有以下特点：\n\n"
    "1. **查询结果缓存**：提供对查询结果的数据缓存功能，"
    "支持将数据库返回的结果集中缓存在内存中。\n"
    "2. **可配置的缓存大小**：允许用户根据需求自行配置缓存容量，"
    "以调节内存使用和性能表现。\n"
    "3. **动态刷新机制**：在发生数据修改操作后，后续进行查询时，"
    "系统会自动从数据库中获取最新数据并更新缓存内容。")


def _crud_answer() -> str:
    return ("对象化访问功能支持以下操作：\n\n"
            "1. **添加**：向数据库中插入数据。\n"
            "2. **删除**：从数据库中删除已存在的数据。\n"
            "3. **修改**：对数据库中的数据进行更新或修改。\n"
            "4. **查询**：根据特定条件检索数据库中的数据。")


def test_gate_non_flow_question_feature_list_is_not_sequence() -> None:
    """S1QA-066: "有什么特点"是功能清单非事件流 → 门关闭."""
    steps = _steps_of(FEATURE_LIST_ANSWER, "热点数据缓存功能有什么特点")
    assert len(steps) == 3
    assert not is_sequence_applicable("热点数据缓存功能有什么特点", steps)


def test_gate_non_flow_question_short_crud_list_is_not_sequence() -> None:
    """S1QA-069: "支持哪些操作"的短并列项(添加/删除/修改/查询) → 门关闭."""
    steps = _steps_of(_crud_answer(), "对象化访问功能支持哪些操作")
    assert len(steps) == 4
    assert not is_sequence_applicable("对象化访问功能支持哪些操作", steps)


def test_gate_exception_type_enumeration_is_not_sequence() -> None:
    """S1QA-001: 失败/错误/异常关键词占比≥0.5的编号项是异常类型枚举."""
    answer = ("BLOB数据插入的异常处理包括：\n\n"
              "1. 连接检查。\n2. JSON解析失败。\n"
              "3. SQL执行失败。\n4. 资源释放与错误报告。")
    steps = _steps_of(answer, "描述BLOB数据插入的主要步骤。")
    assert len(steps) == 4
    assert not is_sequence_applicable("描述BLOB数据插入的主要步骤。", steps)


def test_gate_real_usecase_steps_stay_applicable() -> None:
    """S1QA-024锚点: 真主事件流步骤(流程型问题, 平均39字符, 异常项占比1/3) → 门打开."""
    request = _load_frozen("S1QA-024")
    claims = decompose_answer(request.answer, request.question)
    steps = extract_answer_steps(request.answer, claims)
    assert len(steps) == 3
    assert is_sequence_applicable(request.question, steps)


def test_gate_parallel_enum_emits_conservative_nie_not_fabricated_steps() -> None:
    """门关闭时: 链接到结构化claim的编号项输出保守NIE(可被同文本判定融合),
    不产生"凭空步骤"判决; 未链接的表格残片不产生任何claim."""
    request = QAInput(
        instance_id="qa-gate-enum",
        question="热点数据缓存功能有什么特点",
        answer=FEATURE_LIST_ANSWER,
        context_freeze_id="freeze-gate-enum",
        evidence=(RetrievedEvidence(
            "ev-gate", "热点数据缓存支持查询结果缓存。", "text",
            SourceRef("04数据统一访问服务软件需求规格说明-终稿", section="3.2"),
            "scope-gate"),),
    )
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    results = verify_sequence(request, statements, claims, use_bge=False)
    assert results, "linked steps must keep a conservative NIE claim"
    assert all(r.verdict == "not_in_evidence" for r in results)
    assert all(r.method == "sequence_alignment" for r in results)
    assert all("时序通道不适用" in r.rationale for r in results)
    assert all("凭空步骤" not in r.rationale for r in results)
    assert all("时序不可核对" not in r.rationale for r in results)


def test_gate_table_cell_fragments_emit_nothing() -> None:
    """S1QA-053: markdown表格行("4.1.1 |")是残片——门关闭且无实质内容 → 无claim."""
    answer = ("修改数据记录的功能标识表中包含以下内容：\n\n"
              "| 1 | 删除数据记录 | PZXQ-GN-SQLFW-SJXG | 4.1.1 |\n"
              "| 2 | 增加数据记录 | PZXQ-GN-SQLFW-ZXSW | 4.1.1 |\n"
              "| 3 | 修改数据记录 | PZXQ-GN-SQLFW-TJSW | 4.1.1 |")
    request = QAInput(
        instance_id="qa-gate-frag",
        question="修改数据记录的功能标识表中包含哪些内容？",
        answer=answer,
        context_freeze_id="freeze-gate-frag",
        evidence=(RetrievedEvidence(
            "ev-frag", "修改数据记录功能见表。", "text",
            SourceRef("04数据统一访问服务软件需求规格说明-终稿", section="3.2"),
            "scope-frag"),),
    )
    statements = linearize_context(request.evidence)
    claims = decompose_answer(answer, request.question)
    steps = extract_answer_steps(answer, claims)
    assert not is_sequence_applicable(request.question, steps)
    results = verify_sequence(request, statements, claims, use_bge=False)
    assert results == []


def test_module_s1qa_066_no_prefixed_sequence_claim_survives() -> None:
    """端到端: 066的answer编号项在融合后不残留"1．"前缀claim(重复claim不再产生)."""
    from algorithms.consistency.qa_module import QAConsistencyModule

    request = _load_frozen("S1QA-066")
    result = QAConsistencyModule(use_experts=True).verify(request)
    prefix_re = re.compile(r"^\s*[\d一二三四五六七八九十]+[．.、,，]")
    prefixed = [c for c in result.claim_results
                if prefix_re.match(c.claim_text)]
    assert prefixed == []
    assert result.verdict == "not_in_evidence"


def test_module_s1qa_069_no_prefixed_sequence_claim_survives() -> None:
    from algorithms.consistency.qa_module import QAConsistencyModule

    request = _load_frozen("S1QA-069")
    result = QAConsistencyModule(use_experts=True).verify(request)
    prefix_re = re.compile(r"^\s*[\d一二三四五六七八九十]+[．.、,，]")
    prefixed = [c for c in result.claim_results
                if prefix_re.match(c.claim_text)]
    assert prefixed == []


# ── 判定: S1QA-024 support(官方冻结anchor) ────────────────


def test_s1qa_024_real_answer_steps_match_main_event_flow() -> None:
    request = _load_frozen("S1QA-024")
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    results = verify_sequence(request, statements, claims, use_bge=False)
    assert len(results) == 3
    assert aggregate_sequence_verdict(results) == "support"
    assert all(r.verdict == "support" for r in results)
    assert all(r.method == "sequence_alignment" for r in results)
    assert all(r.check_item_candidates == ("LOGIC-03",) for r in results)
    assert all(r.evidence_refs == (USECASE_TABLE_EV,) for r in results)
    assert all(r.confidence == 0.9 for r in results)
    assert [r.claim_id for r in results] == [
        "S1QA-024-ac02", "S1QA-024-ac03", "S1QA-024-ac04"]
    assert "第1步" in results[0].rationale
    assert "异常流E1" in results[2].rationale


def test_swapped_step_order_is_refute_with_deviation() -> None:
    request = _load_frozen("S1QA-024")
    statements = linearize_context(request.evidence)
    swapped = (
        "二维数组输出的主事件流包括以下具体操作：\n\n"
        "1. **组织查询结果为二维数组**：将收集到的数据按照每条记录"
        "的字段数作为列数，记录数作为行数，返回给系统。\n"
        "2. **调用二维数据获取数据接口**：应用软件通过相关参数"
        "（如数据库句柄）调用该接口。\n"
        "3. **处理失败情况**：在数据获取失败时，执行异常流E1，"
        "提示连接错误并结束用例。")
    request2 = replace(request, answer=swapped)
    claims = decompose_answer(swapped, request.question)
    results = verify_sequence(request2, statements, claims, use_bge=False)
    assert aggregate_sequence_verdict(results) == "refute"
    # 偏差定位: 被交换的两个步骤refute并互相指认, 第三步不受影响
    refutes = [r for r in results if r.verdict == "refute"]
    assert len(refutes) == 2
    assert results[2].verdict == "support"
    first = refutes[0]
    assert "answer步骤1" in first.rationale and "answer步骤2" in first.rationale
    assert "第2步" in first.rationale and "第1步" in first.rationale
    assert set(first.evidence_refs) == {USECASE_TABLE_EV}


def test_fabricated_step_in_matched_answer_is_nie() -> None:
    """answer含证据中没有的步骤 → 该步骤NIE(凭空捏造, 不判refute)."""
    statements = _b162_statements()
    answer = ("数据插入的主事件流包括：\n\n"
              "1. 应用软件调用对象化数据插入接口并输入相应参数，"
              "如要插入数据的类。\n"
              "2. 将类转换成sql语句。\n"
              "3. 应用软件向运维平台发送告警短信通知管理员。\n"
              "4. 数据库完成数据插入操作。")
    request = QAInput(
        instance_id="qa-b162-fabricated",
        question="数据插入的主事件流包括哪些步骤？",
        answer=answer,
        context_freeze_id="freeze-b162",
        evidence=(RetrievedEvidence(
            "ev-b162", B162_TABLE_HTML, "table",
            SourceRef("04数据统一访问服务软件需求规格说明-终稿",
                      section="3.2.2.1"),
            "scope-b162"),),
    )
    claims = decompose_answer(answer, request.question)
    results = verify_sequence(request, statements, claims, use_bge=False)
    assert [r.verdict for r in results] == [
        "support", "support", "not_in_evidence", "support"]
    assert aggregate_sequence_verdict(results) == "not_in_evidence"
    assert "凭空步骤" in results[2].rationale


def test_b162_correct_order_answer_supports() -> None:
    statements = _b162_statements()
    answer = ("数据插入的主事件流包括：\n\n"
              "1. 应用软件调用对象化数据插入接口并输入相应参数，"
              "如要插入数据的类。\n"
              "2. 将类转换成sql语句。\n"
              "3. 调用数据库句柄执行sql语句。\n"
              "4. 数据库完成数据插入操作。")
    request = QAInput(
        instance_id="qa-b162-support",
        question="数据插入的主事件流包括哪些步骤？",
        answer=answer,
        context_freeze_id="freeze-b162",
        evidence=(RetrievedEvidence(
            "ev-b162", B162_TABLE_HTML, "table",
            SourceRef("04数据统一访问服务软件需求规格说明-终稿",
                      section="3.2.2.1"),
            "scope-b162"),),
    )
    claims = decompose_answer(answer, request.question)
    results = verify_sequence(request, statements, claims, use_bge=False)
    assert all(r.verdict == "support" for r in results)
    assert aggregate_sequence_verdict(results) == "support"


# ── 判定: NIE(证据无编号步骤 / scope不可定位) ─────────────


def test_blob_insert_without_usecase_table_is_nie() -> None:
    """BLOB插入answer编造步骤, 冻结证据无用例表 → 每步NIE."""
    answer = ("BLOB数据插入的主事件流如下：\n\n"
              "1. 应用软件调用插入BLOB数据接口输入相关参数，"
              "如执行sql语句、插入blob数据数组。\n"
              "2. 系统将sql语句、blob数据数组组织成json格式传输到服务端执行。\n"
              "3. 若解析失败则执行异常流E1返回错误信息。")
    request = QAInput(
        instance_id="qa-blob-nie",
        question="BLOB数据插入的主事件流包括哪些步骤？",
        answer=answer,
        context_freeze_id="freeze-blob",
        evidence=(
            RetrievedEvidence(
                "ev-blob-1",
                "3.2.1.4.1.1 BLOB数据操作-BLOB数据插入"
                "（PZXQ-GN-SQLFW-BLOBSJCZ-BLOBSJCR）",
                "text",
                SourceRef("04数据统一访问服务软件需求规格说明-终稿",
                          section="3.2.1.4.1.1"),
                "scope-blob-1"),
            RetrievedEvidence(
                "ev-blob-2", "BLOB数据插入流程图如图 24所示：",
                "text",
                SourceRef("04数据统一访问服务软件需求规格说明-终稿",
                          section="3.2.1.4.1.1"),
                "scope-blob-2"),
        ),
    )
    statements = linearize_context(request.evidence)
    claims = decompose_answer(answer, request.question)
    results = verify_sequence(request, statements, claims, use_bge=False)
    assert len(results) == 3
    assert all(r.verdict == "not_in_evidence" for r in results)
    assert aggregate_sequence_verdict(results) == "not_in_evidence"
    assert all("主事件流编号步骤" in r.rationale for r in results)
    assert all(r.evidence_refs == () for r in results)


def test_multi_scope_without_question_name_is_nie() -> None:
    """S1QA-024冻结context含3个用例scope, question未指名 → 拒绝跨scope比对."""
    request = _load_frozen("S1QA-024")
    statements = linearize_context(request.evidence)
    ambiguous = replace(
        request,
        question="主事件流的第一步是什么？",
        answer="主事件流按顺序为：\n1. 应用软件调用接口输入参数。\n"
               "2. 系统组织结果返回。")
    claims = decompose_answer(ambiguous.answer, ambiguous.question)
    results = verify_sequence(ambiguous, statements, claims, use_bge=False)
    assert all(r.verdict == "not_in_evidence" for r in results)
    assert all("scope" in r.rationale for r in results)


# ── Needleman-Wunsch(纯函数, 无模型) ──────────────────────


def test_needleman_wunsch_identity_prefers_diagonal() -> None:
    score, pairs = needleman_wunsch([[1.0, 0.0], [0.0, 1.0]], gap=-0.5)
    assert pairs == [(0, 0), (1, 1)]
    assert score == pytest.approx(2.0)


def test_needleman_wunsch_gap_beats_weak_match() -> None:
    # answer两步 vs 证据一步: 对齐强匹配步并gap弱匹配步
    score, pairs = needleman_wunsch([[0.1], [0.9]], gap=-0.5)
    assert pairs == [(1, 0)]
    assert score == pytest.approx(0.4)


def test_needleman_wunsch_empty_inputs() -> None:
    assert needleman_wunsch([], gap=-0.5) == (0.0, [])
    score, pairs = needleman_wunsch([[], []], gap=-0.5)
    assert score == pytest.approx(-1.0)
    assert pairs == []


def test_align_sequences_reports_pairs_and_channel() -> None:
    answer = ["步骤甲", "步骤乙"]
    flow = ["步骤甲", "步骤乙", "步骤丙"]
    alignment = align_sequences(
        answer, flow, lambda a, e: 1.0 if a == e else 0.0,
        channel="unit-test")
    assert alignment.channel == "unit-test"
    assert [(p.answer_index, p.evidence_index) for p in alignment.pairs] == [
        (0, 0), (1, 1)]
    assert all(p.similarity == 1.0 for p in alignment.pairs)
    # 2对齐点+1个证据gap: 1.0 + 1.0 - 0.5 = 1.5
    assert alignment.score == pytest.approx(1.5)


def test_char_jaccard_normalization() -> None:
    assert char_jaccard("应用软件调用接口。", "应用软件调用接口") == 1.0
    assert char_jaccard("将类转换成sql语句", "调用数据库句柄执行sql语句") > 0.0
    assert char_jaccard("", "非空") == 0.0


# ── 聚合 ─────────────────────────────────────────────────


def test_aggregate_sequence_verdict_priority() -> None:
    def result(verdict: str) -> ClaimResult:
        return ClaimResult("c", "t", verdict, ("LOGIC-03",), (), "r",
                           "sequence_alignment", 0.9)

    assert aggregate_sequence_verdict(
        [result("support"), result("refute")]) == "refute"
    assert aggregate_sequence_verdict(
        [result("support"), result("not_in_evidence")]) == "not_in_evidence"
    assert aggregate_sequence_verdict([result("support")]) == "support"
    assert aggregate_sequence_verdict([]) == "not_in_evidence"


# ── 方法2: BGE嵌入 + NW全局对齐(需本地模型) ───────────────


@pytest.fixture(scope="module")
def bge_client() -> BgeLocal:
    client = BgeLocal(use_cache=False)
    mode = client.ensure()
    assert mode in ("cpu", "cuda"), f"bge不可用: {client.last_error}"
    return client


@requires_bge
def test_bge_alignment_paraphrased_steps_support(bge_client: BgeLocal) -> None:
    """answer改写步骤文本(词面重合低于确定性阈值)但语义相同 → support."""
    request = _load_frozen("S1QA-024")
    statements = linearize_context(request.evidence)
    paraphrased = (
        "二维数组输出的主事件流如下：\n\n"
        "1. 客户端程序使用取数界面传入句柄等参数发起调用。\n"
        "2. 服务端把结果数据按列字段与行记录组织成矩阵返回。\n"
        "3. 若取数不成功则转入E1流程并给出连接错误提示后终止。")
    request2 = replace(request, answer=paraphrased)
    claims = decompose_answer(paraphrased, request.question)
    # 词面重合不足以确定性配对(改写检验)
    flow = extract_flow_steps(
        statements, resolve_flow_scope(request.question, claims, statements))
    assert all(
        char_jaccard(step.text, unit.text) < 0.28
        for step in extract_answer_steps(paraphrased, claims)
        for unit in flow)
    results = verify_sequence(request2, statements, claims, bge=bge_client)
    assert len(results) == 3
    assert all(r.verdict == "support" for r in results)
    assert aggregate_sequence_verdict(results) == "support"
    assert all(r.confidence == 0.8 for r in results)
    assert all("通道=bge" in r.rationale for r in results)
    # NW全局对齐诊断: 分数 + 逐对齐点挂在首个结果
    assert "NW全局对齐" in results[0].rationale
    assert "↔" in results[0].rationale
