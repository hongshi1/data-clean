"""E1异常流模板专家(L1组件, LOGIC-02异常处置策略)契约测试.

真实锚点(官方冻结context + GLM-5.3 silver标签):
  - S1QA-021(silver=support): answer提示"连接错误"与读取配置文件连接/
    数据库连接的E1"系统提示连接失败"经关键词"连接"重合 → keyword匹配
  - S1QA-028(silver=refute): answer声称E1提示"连接错误", 二维数组输出的
    E1实际为"系统提示获取失败" → 关键词无重合 → refute
  - b207(04号SRS block-000207, 模型制作): 4条E1~E4挤在同一单元格,
    以"。"分隔, 分条解析; answer按E编号定位模板比对

构造锚点: 缓存更新用例E1"系统提示初始化"(主题错位, 疑似从数据库初始化
复制) → 证据侧主题错位refute; 缓存更新无E1行 → NIE.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.answer_structure import decompose_answer  # noqa: E402
from algorithms.consistency.e1_expert import (  # noqa: E402
    E1Template,
    PromptMatch,
    aggregate_e1_verdict,
    check_e1_topic_mismatch,
    compare_prompts,
    ending_kind,
    extract_e1_templates,
    extract_ending_claim,
    extract_prompt_claims,
    resolve_e1_scope,
    verify_e1_consistency,
)
from algorithms.consistency.evidence_statements import linearize_context  # noqa: E402
from algorithms.consistency.qa_models import (  # noqa: E402
    ClaimResult,
    QAInput,
    RetrievedEvidence,
    SourceRef,
)
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
DOC04 = "04数据统一访问服务软件需求规格说明-终稿"
S1QA021_E1_EV = ("S1QA-021-ev-000049", "S1QA-021-ev-000054")
S1QA028_E1_EV = "S1QA-028-ev-000101"

B207_TABLE_HTML = (
    '<table><tr><td><p>Use Case 名称：模型制作</p></td>'
    '<td colspan="2"><p>Actors：用户</p></td></tr>'
    '<tr><td colspan="3"><p>概述：本用例是代码生成的扩展用例，'
    '描述模型制作的过程；</p></td></tr>'
    '<tr><td colspan="3"><p>前置条件：数据库连接正常。</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p><p>（性能、可靠性、容错等）</p></td></tr>'
    '<tr><td><p>1、用户打开集成开发工具，点击数据开发按钮；</p>'
    '<p>3、用户在展示的列表中选择先选择分类域，再从分类域中勾选需要的表。</p>'
    '<p>5、用户在表下选择需要的字段，生成模型。</p></td>'
    '<td><p>2、系统连接到元数据库，如果连接失败，执行异常流E1。'
    '获取到所有表名及其分类域,如果获取失败，则执行异常流E2。'
    '将获取到的数据按分类域组织成二级列表，返回到前端页面。</p>'
    '<p>4、系统根据用户选择的表，从元数据库中查询表下所有字段，'
    '若查询失败，则执行异常流E3.将获取到的数据组织成列表形式，'
    '返回到前端页面。</p>'
    '<p>6．系统判断用户生成的模型中，有没有重复的字段，'
    '有重复的字段名称，则执行异常流E4。</p></td>'
    '<td><p>如果无法连接到服务端，提示连接错误。</p></td></tr>'
    '<tr><td colspan="2"><p>异常流E1：系统提示连接数据库异常，用例结束。</p>'
    '<p>异常流E2：系统提示获取信息失败，用例结束。</p>'
    '<p>异常流E3：系统提示查询字段失败，用例结束。</p>'
    '<p>异常流E4：系统提示有重复性的字段，用例结束。</p></td>'
    '<td></td></tr>'
    '<tr><td colspan="2"><p>后置条件：无。</p></td>'
    '<td></td></tr></table>')

CACHE_UPDATE_TABLE_HTML = (
    '<table><tr><td><p>Use Case 名称：缓存更新</p></td>'
    '<td colspan="2"><p>Actors：应用软件</p></td></tr>'
    '<tr><td colspan="3"><p>概述：本用例是缓存服务的扩展用例，'
    '描述缓存更新的过程；</p></td></tr>'
    '<tr><td colspan="3"><p>前置条件：缓存服务正常。</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p><p>（性能、可靠性、容错等）</p></td></tr>'
    '<tr><td><p>1.应用软件调用缓存更新接口输入缓存键值；</p></td>'
    '<td><p>2．系统校验缓存条目并刷新缓存数据，'
    '校验失败则执行异常流E1；</p></td>'
    '<td><p>缓存更新应在100ms内完成。</p></td></tr>'
    '<tr><td colspan="2"><p>异常流E1：系统提示初始化，用例结束。</p></td>'
    '<td></td></tr>'
    '<tr><td colspan="2"><p>后置条件：无。</p></td>'
    '<td></td></tr></table>')

CACHE_UPDATE_NO_E1_HTML = (
    '<table><tr><td><p>Use Case 名称：缓存更新</p></td>'
    '<td colspan="2"><p>Actors：应用软件</p></td></tr>'
    '<tr><td colspan="3"><p>概述：本用例是缓存服务的扩展用例，'
    '描述缓存更新的过程；</p></td></tr>'
    '<tr><td colspan="3"><p>前置条件：缓存服务正常。</p></td></tr>'
    '<tr><td colspan="3"><p>主事件流</p></td></tr>'
    '<tr><td><p>Actor的动作</p></td><td><p>系统的动作</p></td>'
    '<td><p>动作约束</p><p>（性能、可靠性、容错等）</p></td></tr>'
    '<tr><td><p>1.应用软件调用缓存更新接口输入缓存键值；</p></td>'
    '<td><p>2．系统校验缓存条目并刷新缓存数据，'
    '校验失败则返回校验错误码；</p></td>'
    '<td><p>缓存更新应在100ms内完成。</p></td></tr>'
    '<tr><td colspan="2"><p>后置条件：无。</p></td>'
    '<td></td></tr></table>')


def _load_frozen(instance_id: str) -> QAInput:
    rows = [json.loads(line) for line in
            FROZEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    return request_from_dict(
        next(row for row in rows if row["instance_id"] == instance_id))


def _statements(table_html: str, evidence_id: str,
                section: str = "3.2.1.1.1.1") -> list:
    evidence = RetrievedEvidence(
        evidence_id, table_html, "table",
        SourceRef(DOC04, section=section), f"scope-{evidence_id}")
    return linearize_context((evidence,))


def _request(instance_id: str, question: str, answer: str,
             table_html: str, evidence_id: str,
             section: str = "3.2.1.1.1.1") -> QAInput:
    return QAInput(
        instance_id=instance_id, question=question, answer=answer,
        context_freeze_id=f"freeze-{instance_id}",
        evidence=(RetrievedEvidence(
            evidence_id, table_html, "table",
            SourceRef(DOC04, section=section),
            f"scope-{evidence_id}"),),
    )


# ── 证据侧提取(真实S1QA-021 + b207违例) ──────────────────


def test_extract_e1_templates_real_s1qa_021() -> None:
    request = _load_frozen("S1QA-021")
    statements = linearize_context(request.evidence)
    templates = extract_e1_templates(statements)
    assert [(t.use_case_name, t.e1_id) for t in templates] == [
        ("数据库初始化", "E1"), ("读取配置文件连接", "E1"),
        ("数据库连接", "E1")]
    by_case = {t.use_case_name: t for t in templates}
    assert by_case["数据库初始化"].prompt == "初始化失败"
    assert by_case["数据库初始化"].ending == "用例结束。"
    assert by_case["读取配置文件连接"].prompt == "连接失败"
    assert by_case["数据库连接"].prompt == "连接失败"
    assert all(t.evidence_id == t.evidence_ref.split("#")[0]
               for t in templates)
    assert "异常流E1：系统提示连接失败，用例结束。" \
        in by_case["数据库连接"].raw_text


def test_extract_e1_templates_b207_squeezed_cell() -> None:
    """b207真实违例: E1~E4四条挤在同一单元格, 分条解析为4个模板."""
    statements = _statements(B207_TABLE_HTML, "ev-b207", "3.2.3.1")
    templates = extract_e1_templates(statements)
    assert [t.e1_id for t in templates] == ["E1", "E2", "E3", "E4"]
    assert all(t.use_case_name == "模型制作" for t in templates)
    assert [t.prompt for t in templates] == [
        "连接数据库异常", "获取信息失败", "查询字段失败", "有重复性的字段"]
    assert all(t.ending == "用例结束。" for t in templates)
    # 主题错位检查在真实b207上不误报(提示词均命中主事件流主题)
    assert check_e1_topic_mismatch(statements, templates) == []


def test_extract_e1_template_without_prompt() -> None:
    """无提示形态: '异常流E1：用例结束' → prompt=None, ending=用例结束."""
    html = ('<table><tr><td><p>Use Case 名称：数据下载</p></td></tr>'
            '<tr><td><p>主事件流</p></td></tr>'
            '<tr><td><p>异常流E1：用例结束。</p></td></tr></table>')
    statements = _statements(html, "ev-no-prompt", "3.2.1.4.1.1")
    templates = extract_e1_templates(statements)
    assert len(templates) == 1
    template = templates[0]
    assert template.e1_id == "E1"
    assert template.prompt is None
    assert template.ending == "用例结束"


def test_flow_cell_e_reference_is_not_template() -> None:
    """主事件流单元格内的'执行异常流E1'引用不构成E1模板(field不含异常流)."""
    statements = _statements(B207_TABLE_HTML, "ev-b207", "3.2.3.1")
    flow_refs = [s for s in statements if "执行异常流" in s.text]
    assert flow_refs
    assert all("异常流" not in s.field_name for s in flow_refs)
    assert len(extract_e1_templates(statements)) == 4


# ── 提示内容比对 ─────────────────────────────────────────


def test_compare_prompts_four_levels() -> None:
    assert compare_prompts("获取失败", "获取失败") == PromptMatch("exact", 1.0)
    substring = compare_prompts("提示获取失败", "获取失败")
    assert substring.match_type == "substring"
    assert 0.0 < substring.score < 1.0
    keyword = compare_prompts("连接错误", "连接失败")
    assert keyword.match_type == "keyword"
    assert keyword.score > 0.0
    no = compare_prompts("连接错误", "获取失败")
    assert no == PromptMatch("no", 0.0)
    assert compare_prompts("失败", "错误").match_type == "no"
    assert compare_prompts("", "连接失败").match_type == "no"


def test_extract_prompt_claims_quoted_plain_and_connective() -> None:
    quoted = extract_prompt_claims(
        "系统触发异常流E1，并显示“无法连接到服务端，提示连接错误。”")
    assert quoted == ["无法连接到服务端，提示连接错误"]
    plain = extract_prompt_claims(
        "系统检测到无法获取数据，并向用户提示连接错误。")
    assert plain == ["连接错误"]
    cut = extract_prompt_claims("系统显示连接错误并终止流程。")
    assert cut == ["连接错误"]
    assert extract_prompt_claims("系统调用接口输入参数") == []


def test_extract_prompt_claims_truncated_closing_quote() -> None:
    """decompose_answer的句尾清理会剥掉"。”": 闭引号缺失时引号内容仍可提取."""
    claim = ("如果无法连接到服务端，系统会触发异常流E1，"
             "并显示“无法连接到服务端，提示连接错误")
    assert extract_prompt_claims(claim) == ["无法连接到服务端，提示连接错误"]


def test_extract_ending_claim_kinds() -> None:
    assert extract_ending_claim("用例结束，没有进一步的处理步骤") == "end"
    assert extract_ending_claim("系统显示连接错误并终止流程") == "end"
    assert extract_ending_claim("随后用例恢复正常继续执行") == "continue"
    assert extract_ending_claim("系统提示连接错误") is None
    assert ending_kind("用例结束。") == "end"
    assert ending_kind("返回错误码") is None


# ── 判定: S1QA-021 support(官方冻结anchor, silver=support) ─


def test_s1qa_021_keyword_match_supports() -> None:
    request = _load_frozen("S1QA-021")
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    results = verify_e1_consistency(request, statements, claims)
    assert len(results) == 1
    result = results[0]
    assert result.verdict == "support"
    assert aggregate_e1_verdict(results) == "support"
    assert result.claim_id == "S1QA-021-ac01"
    assert result.method == "e1_template_match"
    assert result.check_item_candidates == ("LOGIC-02",)
    assert result.evidence_refs == S1QA021_E1_EV
    assert result.confidence == 0.75
    assert "keyword" in result.rationale
    assert "连接失败" in result.rationale
    assert "读取配置文件连接" in result.rationale


def test_s1qa_021_scope_unresolved_uses_any_match() -> None:
    """question未指名用例且3个用例scope → any-match语义与全部模板比对."""
    request = _load_frozen("S1QA-021")
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    assert resolve_e1_scope(request.question, claims, statements) is None
    templates = extract_e1_templates(statements)
    assert len(templates) == 3


# ── 判定: S1QA-028 refute(官方冻结anchor, silver=refute) ──


def test_s1qa_028_prompt_mismatch_refutes() -> None:
    request = _load_frozen("S1QA-028")
    statements = linearize_context(request.evidence)
    claims = decompose_answer(request.answer, request.question)
    assert resolve_e1_scope(request.question, claims, statements) \
        == "二维数组输出"
    results = verify_e1_consistency(request, statements, claims)
    assert {r.claim_id for r in results} == {
        "S1QA-028-ac02", "S1QA-028-ac03", "S1QA-028-ac04"}
    by_id = {r.claim_id: r for r in results}
    assert by_id["S1QA-028-ac02"].verdict == "refute"
    assert by_id["S1QA-028-ac02"].evidence_refs == (S1QA028_E1_EV,)
    assert "获取失败" in by_id["S1QA-028-ac02"].rationale
    assert "连接错误" in by_id["S1QA-028-ac02"].rationale
    assert by_id["S1QA-028-ac03"].verdict == "support"
    assert by_id["S1QA-028-ac04"].verdict == "refute"
    assert aggregate_e1_verdict(results) == "refute"
    assert all(r.method == "e1_template_match" for r in results)
    assert all(r.check_item_candidates == ("LOGIC-02",) for r in results)


# ── 判定: b207 answer按E编号定位模板 ─────────────────────


def test_b207_answer_e2_exact_match_supports() -> None:
    answer = ("模型制作过程中如果获取信息失败，会执行异常流E2："
              "系统提示获取信息失败，用例结束。")
    request = _request("qa-b207-e2", "模型制作获取信息失败时有什么提示",
                       answer, B207_TABLE_HTML, "ev-b207", "3.2.3.1")
    statements = _statements(B207_TABLE_HTML, "ev-b207", "3.2.3.1")
    claims = decompose_answer(request.answer, request.question)
    results = verify_e1_consistency(request, statements, claims)
    assert len(results) == 1
    assert results[0].verdict == "support"
    assert results[0].evidence_refs == ("ev-b207",)
    assert "exact" in results[0].rationale
    assert aggregate_e1_verdict(results) == "support"


def test_b207_answer_wrong_prompt_for_e2_refutes() -> None:
    """answer把E3的内容安到E2头上: E编号定位后与E2模板比对 → refute."""
    answer = ("模型制作过程中如果获取信息失败，会执行异常流E2："
              "系统提示查询字段失败，用例结束。")
    request = _request("qa-b207-e2x", "模型制作获取信息失败时有什么提示",
                       answer, B207_TABLE_HTML, "ev-b207", "3.2.3.1")
    statements = _statements(B207_TABLE_HTML, "ev-b207", "3.2.3.1")
    claims = decompose_answer(request.answer, request.question)
    results = verify_e1_consistency(request, statements, claims)
    assert len(results) == 1
    assert results[0].verdict == "refute"
    assert "获取信息失败" in results[0].rationale
    assert "查询字段失败" in results[0].rationale
    assert aggregate_e1_verdict(results) == "refute"


# ── 判定: 处置语义矛盾(继续/恢复 vs 用例结束) ─────────────


def test_continue_claim_vs_end_template_refutes() -> None:
    cache_query_html = B207_TABLE_HTML.replace("模型制作", "数据缓存查询")
    answer = "数据缓存查询失败时系统提示查询失败，随后用例恢复正常继续执行。"
    request = _request("qa-continue", "数据缓存查询失败时如何处置",
                       answer, cache_query_html, "ev-continue", "3.2.1.1.1.1")
    statements = _statements(cache_query_html, "ev-continue", "3.2.1.1.1.1")
    claims = decompose_answer(request.answer, request.question)
    results = verify_e1_consistency(request, statements, claims)
    assert len(results) == 1
    result = results[0]
    assert result.verdict == "refute"
    assert "处置语义矛盾" in result.rationale
    assert "用例结束" in result.rationale
    assert result.evidence_refs == ("ev-continue",)


# ── 判定: NIE(scope用例无E1行) ───────────────────────────


def test_scope_usecase_without_e1_row_is_nie() -> None:
    answer = "缓存更新失败时，系统会提示缓存数据失效。"
    request = _request("qa-no-e1", "缓存更新失败时如何处置",
                       answer, CACHE_UPDATE_NO_E1_HTML, "ev-no-e1")
    statements = _statements(CACHE_UPDATE_NO_E1_HTML, "ev-no-e1")
    claims = decompose_answer(request.answer, request.question)
    results = verify_e1_consistency(request, statements, claims)
    assert len(results) == 1
    result = results[0]
    assert result.verdict == "not_in_evidence"
    assert "无异常流行" in result.rationale
    assert "缓存更新" in result.rationale
    assert result.evidence_refs == ()


def test_no_exception_claim_answer_returns_empty() -> None:
    answer = "缓存更新接口的输入参数包括缓存键值和过期时间。"
    request = _request("qa-plain", "缓存更新接口的输入参数是什么",
                       answer, CACHE_UPDATE_NO_E1_HTML, "ev-plain")
    statements = _statements(CACHE_UPDATE_NO_E1_HTML, "ev-plain")
    results = verify_e1_consistency(request, statements)
    assert results == []


# ── 证据侧: 主题错位(构造: 缓存更新的E1提示"初始化") ──────


def test_topic_mismatch_constructed_case_is_refute() -> None:
    """E1='系统提示初始化'但用例主题是'缓存更新' → 主题错位可检测."""
    statements = _statements(CACHE_UPDATE_TABLE_HTML, "ev-topic")
    results = check_e1_topic_mismatch(statements)
    assert len(results) == 1
    result = results[0]
    assert result.verdict == "refute"
    assert "主题错位" in result.rationale
    assert "缓存更新" in result.rationale
    assert "疑似从其他用例复制" in result.rationale
    assert result.evidence_refs == ("ev-topic",)
    assert result.check_item_candidates == ("LOGIC-02",)


def test_topic_mismatch_claim_anchored_to_answer_verbatim() -> None:
    """字面忠实修复(E1弱点#1): 主题错位refute锚定answer逐字引用+span.

    answer提及用例名与E1提示文本时, claim_text=answer[start:end](用例名/
    提示文本的最小覆盖span, 字面契约answer[span]==text); 原合成断言移入
    rationale; 判定字段(verdict/method/confidence/refs)与无answer调用
    完全一致——锚定只改定位文本, 不动判定逻辑.
    """
    statements = _statements(CACHE_UPDATE_TABLE_HTML, "ev-topic")
    answer = "缓存更新发生异常时，系统会提示初始化并结束用例。"
    results = check_e1_topic_mismatch(statements, answer=answer)
    assert len(results) == 1
    result = results[0]
    assert result.verdict == "refute"
    assert result.span == (0, 18)
    assert answer[0:18] == result.claim_text  # 字面契约
    assert result.claim_text == "缓存更新发生异常时，系统会提示初始化"
    bare = check_e1_topic_mismatch(statements)[0]
    assert (result.verdict, result.method, result.confidence,
            result.evidence_refs, result.check_item_candidates) == \
        (bare.verdict, bare.method, bare.confidence,
         bare.evidence_refs, bare.check_item_candidates)
    # 合成断言移入rationale(信息不丢弃)+原主题错位描述保留
    assert "主题错位" in result.rationale
    assert "疑似从其他用例复制" in result.rationale
    assert bare.claim_text in result.rationale


def test_topic_mismatch_answer_without_relation_keeps_synthesis() -> None:
    """answer无关联文本(用例名/提示文本均不在answer中)→保持合成断言."""
    statements = _statements(CACHE_UPDATE_TABLE_HTML, "ev-topic")
    results = check_e1_topic_mismatch(
        statements, answer="数据库连接的端口号是多少。")
    assert len(results) == 1
    assert results[0].span is None
    assert results[0].claim_text == \
        "用例缓存更新的E1提示内容与该用例主题一致"


def test_topic_mismatch_real_frozen_evidence_clean() -> None:
    """真实S1QA-021/028证据的主题检查零误报(提示词均命中用例主题)."""
    for instance_id in ("S1QA-021", "S1QA-028"):
        request = _load_frozen(instance_id)
        statements = linearize_context(request.evidence)
        assert check_e1_topic_mismatch(statements) == []


def test_promptless_template_skips_topic_check() -> None:
    """E1行无提示内容(prompt=None)时不参与主题错位检查."""
    html = ('<table><tr><td><p>Use Case 名称：数据下载</p></td></tr>'
            '<tr><td><p>主事件流</p></td></tr>'
            '<tr><td><p>异常流E1：用例结束。</p></td></tr></table>')
    statements = _statements(html, "ev-noprompt", "3.2.1.4.1.1")
    templates = extract_e1_templates(statements)
    assert len(templates) == 1
    assert templates[0].prompt is None
    assert check_e1_topic_mismatch(statements, templates) == []


# ── 模板形态与聚合 ───────────────────────────────────────


def test_e1_template_dataclass_fields() -> None:
    template = E1Template(
        use_case_name="数据库连接", evidence_ref="ev#s7#E1",
        evidence_id="ev", e1_id="E1", prompt="连接失败",
        ending="用例结束。", raw_text="异常流E1：系统提示连接失败，用例结束。")
    assert template.prompt == "连接失败"
    assert ending_kind(template.ending) == "end"


def test_aggregate_e1_verdict_priority() -> None:
    def result(verdict: str) -> ClaimResult:
        return ClaimResult("c", "t", verdict, ("LOGIC-02",), (), "r",
                           "e1_template_match", 0.9)

    assert aggregate_e1_verdict(
        [result("support"), result("refute")]) == "refute"
    assert aggregate_e1_verdict(
        [result("support"), result("not_in_evidence")]) == "not_in_evidence"
    assert aggregate_e1_verdict([result("support")]) == "support"
    assert aggregate_e1_verdict([]) == "not_in_evidence"


def test_mutated_answer_changes_verdict() -> None:
    """同一question下, 把提示声称改为与E1一致 → 由refute翻support."""
    request = _load_frozen("S1QA-028")
    statements = linearize_context(request.evidence)
    corrected = replace(
        request,
        answer=("如果在二维数组输出过程中发生错误，系统会触发异常流E1，"
                "系统提示获取失败，用例结束。"))
    claims = decompose_answer(corrected.answer, corrected.question)
    results = verify_e1_consistency(corrected, statements, claims)
    assert len(results) == 1
    assert results[0].verdict == "support"
    assert aggregate_e1_verdict(results) == "support"
