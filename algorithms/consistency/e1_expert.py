"""E1异常流模板专家(L1组件, LOGIC-02异常处置策略).

级联架构L1符号验证层的异常处置比对专家: 从用例表的异常流行(field_name含
"异常流")提取E1~En模板(提示内容+处置), 与answer声称的异常处置比对.

真实数据形态(04号SRS):
  - 标准行: "异常流E1：系统提示连接失败，用例结束。"(表6读取配置文件连接)
  - 多条挤压: block-000207(模型制作)同一单元格挤入E1~E4四条, 以"。"分隔
  - 无提示: "异常流E1：用例结束" → prompt=None
  - 主事件流单元格内的"执行异常流E1"引用不属于异常流行, 不在本专家范围

判定规则(LOGIC-02):
  support          answer提示内容与E1模板prompt匹配(exact/substring/keyword),
                   或answer处置声称与E1模板处置一致(结束对结束)
  refute           answer提示内容与scope用例的E1模板prompt不匹配, 或answer
                   声称继续/恢复而E1模板处置为"用例结束"(处置语义矛盾)
  not_in_evidence  scope用例无证据用例表, 或用例表无异常流行, 或E1行未声明
                   提示内容/处置使声称无法核对

证据侧文档违例检测(与answer无关): E1提示内容关键词与所在用例主题(用例名+
主事件流/动作约束文本)无重合 → 主题错位(疑似跨用例复制), refute.

关键词宽容匹配: 双边去掉通用词(系统/用户/提示/失败/错误等)后取字符二元组
求交集——"连接错误"与"连接失败"经"连接"重合 → keyword匹配(S1QA-021锚点,
silver=support); "连接错误"与"获取失败"无重合 → no匹配(S1QA-028锚点,
silver=refute). scope定位失败(question/claim均无法唯一命中用例名)时按
any-match语义与全部模板比对(检索已是question条件化的).

复用: evidence_statements.EvidenceStatement / answer_structure.
StructuredClaim / qa_models.ClaimResult. 本层完全确定性: 无模型调用、无
文件读取、import期零I/O. 模板正则/词表/阈值取自rule pack
(config/rulepacks/srs_gjb_v1.json, 见docs/srs_project/64_rulepack_design.md),
经_cfg()惰性编译——配置内容与迁移前源码逐字一致(行为保持).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal

from algorithms.consistency.answer_structure import (
    StructuredClaim,
    decompose_answer,
)
from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.qa_models import ClaimResult, QAInput, Verdict
from algorithms.consistency.rulepack import RulePack, default_rulepack

METHOD = "e1_template_match"
CHECK_ITEMS: tuple[str, ...] = ("LOGIC-02",)

PromptMatchType = Literal["exact", "substring", "keyword", "no"]
EndingKind = Literal["end", "continue"]


@dataclass(frozen=True)
class _E1Config:
    """从rule pack编译的E1专家配置(模板正则+词表+字符集+阈值)."""

    entry_head: re.Pattern[str]
    entry_parse: re.Pattern[str]
    exception_claim: re.Pattern[str]
    claimed_e_id: re.Pattern[str]
    answer_prompt_quoted: re.Pattern[str]
    answer_prompt_plain: re.Pattern[str]
    prompt_connective: re.Pattern[str]
    generic_prompt_text: re.Pattern[str]
    prompt_q: re.Pattern[str]
    evidence_prompt_verb: re.Pattern[str]
    evidence_trigger: re.Pattern[str]
    continue_claim: re.Pattern[str]
    end_claim: re.Pattern[str]
    ending_only: re.Pattern[str]
    continue_words: re.Pattern[str]
    e1_assertion: re.Pattern[str]
    exception_q: re.Pattern[str]
    punct: re.Pattern[str]
    end_words: re.Pattern[str]
    generic_words: re.Pattern[str]
    invalid_prompt_words: re.Pattern[str]
    flow_fields: tuple[str, ...]
    trim_edges: str
    conf_exact: float
    conf_substring: float
    conf_keyword: float
    conf_ending: float
    conf_refute_prompt: float
    conf_refute_ending: float
    conf_topic: float


def _build_config(pack: RulePack) -> _E1Config:
    return _E1Config(
        entry_head=pack.template("e1_entry_head"),
        entry_parse=pack.template("e1_entry_parse"),
        exception_claim=pack.template("e1_exception_claim"),
        claimed_e_id=pack.template("e1_claimed_e_id"),
        answer_prompt_quoted=pack.template("e1_answer_prompt_quoted"),
        answer_prompt_plain=pack.template("e1_answer_prompt_plain"),
        prompt_connective=pack.template("e1_prompt_connective"),
        generic_prompt_text=pack.template("e1_generic_prompt_text"),
        prompt_q=pack.template("e1_prompt_q"),
        evidence_prompt_verb=pack.template("e1_evidence_prompt_verb"),
        evidence_trigger=pack.template("e1_evidence_trigger"),
        continue_claim=pack.template("e1_continue_claim"),
        end_claim=pack.template("e1_end_claim"),
        ending_only=pack.template("e1_ending_only"),
        continue_words=pack.template("e1_continue_words"),
        e1_assertion=pack.template("e1_e1_assertion"),
        exception_q=pack.template("e1_exception_q"),
        punct=pack.template("e1_punct"),
        end_words=pack.vocabulary_regex("e1_end_words"),
        generic_words=pack.vocabulary_regex("e1_generic_words"),
        invalid_prompt_words=pack.vocabulary_regex("e1_invalid_prompt_words"),
        flow_fields=pack.vocabulary("e1_flow_fields"),
        trim_edges=str(pack.join_param("e1", "trim_edges", "")),
        conf_exact=pack.threshold("e1_conf_exact"),
        conf_substring=pack.threshold("e1_conf_substring"),
        conf_keyword=pack.threshold("e1_conf_keyword"),
        conf_ending=pack.threshold("e1_conf_ending"),
        conf_refute_prompt=pack.threshold("e1_conf_refute_prompt"),
        conf_refute_ending=pack.threshold("e1_conf_refute_ending"),
        conf_topic=pack.threshold("e1_conf_topic"),
    )


_E1_CONFIG: _E1Config | None = None


def _cfg() -> _E1Config:
    """惰性加载默认rule pack并编译E1配置(模块级缓存, import期零I/O)."""
    global _E1_CONFIG
    if _E1_CONFIG is None:
        _E1_CONFIG = _build_config(default_rulepack())
    return _E1_CONFIG


@dataclass(frozen=True)
class E1Template:
    """用例表异常流行中的一条模板(提示内容+处置), 带行级定位."""

    use_case_name: str
    evidence_ref: str
    evidence_id: str
    e1_id: str
    prompt: str | None
    ending: str | None
    raw_text: str


@dataclass(frozen=True)
class PromptMatch:
    """answer提示声称与E1模板prompt的比对结果."""

    match_type: PromptMatchType
    score: float


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _entry_chunks(text: str) -> list[str]:
    heads = list(_cfg().entry_head.finditer(text))
    if not heads:
        return []
    bounds = [match.start() for match in heads] + [len(text)]
    return [text[start:stop]
            for start, stop in zip(bounds, bounds[1:])]


def _template_from_chunk(chunk: str, statement: EvidenceStatement,
                         order: int) -> E1Template:
    parse = _cfg().entry_parse.search(chunk)
    e1_id = parse.group("id") if parse else ""
    prompt = (parse.group("prompt").strip() if parse
              and parse.group("prompt") else "")
    ending = (parse.group("ending").strip() if parse
              and parse.group("ending") else "")
    if prompt and _cfg().ending_only.match(prompt):
        ending = ending or prompt
        prompt = ""
    return E1Template(
        use_case_name=statement.scope_key,
        evidence_ref=f"{statement.statement_id}#{e1_id or order}",
        evidence_id=statement.evidence_id,
        e1_id=e1_id,
        prompt=prompt or None,
        ending=ending or None,
        raw_text=chunk.strip(),
    )


def extract_e1_templates(
        statements: list[EvidenceStatement]) -> list[E1Template]:
    """从field_name含"异常流"的语句提取E1~En模板.

    单元格内多条挤压(b207: E1~E4以"。"挤在同一单元格)按E条目头切分后
    逐条解析; 无"："的异常流引用(如"异常流E1；")不构成模板.
    """
    templates: list[E1Template] = []
    for statement in statements:
        if "异常流" not in statement.field_name:
            continue
        for order, chunk in enumerate(_entry_chunks(statement.text)):
            if _cfg().entry_parse.search(chunk):
                templates.append(
                    _template_from_chunk(chunk, statement, order))
    return templates


def _keywords(text: str) -> frozenset[str]:
    cleaned = _cfg().punct.sub("", _cfg().generic_words.sub("", text))
    return frozenset(cleaned[i:i + 2] for i in range(len(cleaned) - 1))


def _norm_prompt(text: str) -> str:
    return text.strip().strip(_cfg().trim_edges)


def compare_prompts(answer_prompt: str,
                    evidence_prompt: str) -> PromptMatch:
    """比对answer声称的提示内容与E1模板prompt.

    依次尝试精确/子串/关键词(去通用词后字符二元组交集)三级匹配; 皆不
    命中返回no. score: exact=1.0, substring=长度比, keyword=Jaccard.
    """
    answer = _norm_prompt(answer_prompt)
    evidence = _norm_prompt(evidence_prompt)
    if not answer or not evidence:
        return PromptMatch("no", 0.0)
    if answer == evidence:
        return PromptMatch("exact", _cfg().conf_exact)
    answer_c, evidence_c = _compact(answer), _compact(evidence)
    if answer_c in evidence_c or evidence_c in answer_c:
        shorter, longer = sorted((len(answer_c), len(evidence_c)))
        return PromptMatch("substring", shorter / longer)
    answer_kw, evidence_kw = _keywords(answer), _keywords(evidence)
    if answer_kw and evidence_kw and answer_kw & evidence_kw:
        union = answer_kw | evidence_kw
        return PromptMatch("keyword", len(answer_kw & evidence_kw) / len(union))
    return PromptMatch("no", 0.0)


def ending_kind(ending: str | None) -> EndingKind | None:
    """把E1/answer的处置文本归类为end/continue(无法归类返回None)."""
    if not ending:
        return None
    if _cfg().continue_words.search(ending):
        return "continue"
    if _cfg().end_words.search(ending):
        return "end"
    return None


def extract_prompt_claims(text: str) -> list[str]:
    """提取answer声称的提示内容(锚定提示/显示等动词, 不取检测条件).

    引号形式(“提示X”/“提示信息：“X””)整段取引号内容; 无引号取动词后的
    短语, 并在"并/然后+处置动词"连接处截断(避免把处置声称混入提示内容).
    通用名词短语("错误信息"/"信息"等无具体内容的宾语)不构成可核对的
    提示声称, 一律丢弃.
    """
    prompts: list[str] = []
    for match in _cfg().answer_prompt_quoted.finditer(text):
        quoted = _norm_prompt(match.group("quoted"))
        if (quoted and not _cfg().generic_prompt_text.match(quoted)
                and not _cfg().invalid_prompt_words.search(quoted)):
            prompts.append(quoted)
    if prompts:
        return prompts
    for match in _cfg().answer_prompt_plain.finditer(text):
        plain = _cfg().prompt_connective.sub("", match.group("plain"))
        plain = _norm_prompt(plain)
        if (plain and not _cfg().generic_prompt_text.match(plain)
                and not _cfg().invalid_prompt_words.search(plain)):
            prompts.append(plain)
    return prompts


def extract_ending_claim(text: str) -> EndingKind | None:
    """提取answer的处置声称(继续/恢复优先于结束/终止).

    处置动词必须与用例名词邻接(结束用例/用例结束/终止当前的事件流);
    "继续尝试"/"重启应用软件"/"重新输入参数"等用户行为动词串不是E1处置
    声称, 不参与处置比对.
    """
    if _cfg().continue_claim.search(text):
        return "continue"
    if _cfg().end_claim.search(text):
        return "end"
    return None


def _distinct_scope_keys(statements: list[EvidenceStatement]) -> list[str]:
    return list(dict.fromkeys(
        statement.scope_key for statement in statements
        if statement.scope_key))


def _scope_hits(candidate: str, scope_keys: list[str]) -> list[str]:
    compact_candidate = _compact(candidate)
    if not compact_candidate:
        return []
    return [key for key in scope_keys
            if _compact(candidate) in _compact(key)
            or _compact(key) in compact_candidate]


def resolve_e1_scope(question: str,
                     claims: list[StructuredClaim] | None,
                     statements: list[EvidenceStatement]) -> str | None:
    """定位目标用例scope: question用例名 > claim scope_hint; 多命中/零命中
    返回None(拒绝跨scope硬比对, 调用方回退any-match全模板)."""
    scope_keys = _distinct_scope_keys(statements)
    if not scope_keys:
        return None
    hits = _scope_hits(question, scope_keys)
    if len(hits) == 1:
        return hits[0]
    for claim in claims or []:
        if claim.scope_hint:
            hint_hits = _scope_hits(claim.scope_hint, scope_keys)
            if len(hint_hits) == 1:
                return hint_hits[0]
    return None


def _topic_pool(statements: list[EvidenceStatement],
                use_case_name: str) -> str:
    parts = [use_case_name]
    parts.extend(
        statement.text for statement in statements
        if _compact(statement.scope_key) == _compact(use_case_name)
        and statement.field_name in _cfg().flow_fields)
    return " ".join(parts)


def check_e1_topic_mismatch(
        statements: list[EvidenceStatement],
        templates: list[E1Template] | None = None) -> list[ClaimResult]:
    """证据侧检查: E1提示关键词与所在用例主题词无重合 → 主题错位refute.

    主题词池 = 用例名 + 该scope的主事件流(Actor的动作/系统的动作/动作
    约束)文本; 真实锚点: 二维数组输出E1"获取失败"命中其主事件流"如果
    获取失败"→不误报, 构造锚点: 缓存更新用例的E1"系统提示初始化"→
    主题错位可检测.
    """
    if templates is None:
        templates = extract_e1_templates(statements)
    results: list[ClaimResult] = []
    for template in templates:
        if not template.prompt:
            continue
        pool = _keywords(_topic_pool(statements, template.use_case_name))
        prompt_kw = _keywords(template.prompt)
        if prompt_kw and pool and not prompt_kw & pool:
            results.append(ClaimResult(
                claim_id="",
                claim_text=(f"用例{template.use_case_name}的{template.e1_id}"
                            f"提示内容与该用例主题一致"),
                verdict="refute",
                check_item_candidates=CHECK_ITEMS,
                evidence_refs=(template.evidence_id,),
                rationale=(f"主题错位：用例{template.use_case_name}的"
                           f"{template.e1_id}为『{template.raw_text}』，提示"
                           f"关键词{sorted(prompt_kw)}未出现在该用例主题词"
                           f"（用例名+主事件流）中，疑似从其他用例复制"
                           f"（LOGIC-02）"),
                method=METHOD,
                confidence=_cfg().conf_topic,
            ))
    return results


def _claimed_e_id(text: str) -> str:
    match = _cfg().claimed_e_id.search(text)
    return match.group(1) if match else ""


def _candidate_templates(claim_text: str,
                         templates: list[E1Template]) -> list[E1Template]:
    claimed = _claimed_e_id(claim_text)
    if claimed:
        preferred = [t for t in templates if t.e1_id == claimed]
        if preferred:
            return preferred
    return templates


def _result(request: QAInput, claim: StructuredClaim, verdict: Verdict,
            rationale: str, refs: tuple[str, ...],
            confidence: float) -> ClaimResult:
    return ClaimResult(
        claim_id=f"{request.instance_id}-{claim.claim_id}",
        claim_text=claim.text,
        verdict=verdict,
        check_item_candidates=CHECK_ITEMS,
        evidence_refs=refs,
        rationale=rationale,
        method=METHOD,
        confidence=confidence,
    )


def _nie_result(request: QAInput, claim: StructuredClaim,
                rationale: str) -> ClaimResult:
    return _result(request, claim, "not_in_evidence", rationale, (), 0.0)


def _judge_prompt(prompt_text: str, candidates: list[E1Template],
                  span_context: tuple[tuple[str, str], ...] = (),
                  trigger_context: tuple[tuple[str, str], ...] = (),
                  strict: bool = True,
                  unscoped: bool = False,
                  ) -> tuple[Verdict, str, tuple[str, ...], float]:
    """judge a claimed prompt text against E1 templates.

    ``strict`` (exception-focused claim/question, scope resolved): any
    mismatch with the scope-resolved E1 prompt refutes. Non-strict (passing
    mention inside a main-flow step): when the claimed text is still a
    documented prompt elsewhere in the evidence (cross-use-case reference),
    downgrade the mismatch to not_in_evidence instead of refuting.
    ``unscoped`` (any-match): a mismatch is never decisive -> NIE.
    """
    comparable = [t for t in candidates if t.prompt]
    if not comparable:
        return ("not_in_evidence",
                f"scope用例的E1行均未声明提示内容，answer的提示声称"
                f"『{prompt_text}』无法核对",
                tuple(dict.fromkeys(t.evidence_id for t in candidates)),
                0.0)
    matches = [(template, compare_prompts(prompt_text, template.prompt or ""))
               for template in comparable]
    best_template, best = max(matches, key=lambda item: item[1].score)
    if best.match_type == "no":
        if unscoped:
            return ("not_in_evidence",
                    (f"提示内容与证据E1不一致(『{prompt_text}』未匹配任何"
                     f"异常流prompt)，但answer未锚定具体用例，比对可能跨"
                     f"用例，无法据此反驳"),
                    tuple(dict.fromkeys(t.evidence_id for t in comparable)),
                    0.0)
        if not strict:
            claimed = _compact(prompt_text)
            in_prompt = any(
                claimed in span or span in claimed
                for span, _ in span_context if span)
            if in_prompt:
                return ("not_in_evidence",
                        (f"提示内容与scope用例E1不一致"
                         f"(『{prompt_text}』vs『{best_template.prompt}』)，"
                         f"但『{prompt_text}』是文档中其他位置声明的提示文本"
                         f"(疑似跨用例引用)，无法据此反驳"),
                        tuple(dict.fromkeys(
                            t.evidence_id for t in comparable)),
                        0.0)
        return ("refute",
                (f"提示内容矛盾：answer声称E1提示『{prompt_text}』，"
                 f"scope用例的E1模板prompt为"
                 f"『{best_template.prompt}』(关键词无重合，LOGIC-02)"),
                tuple(dict.fromkeys(t.evidence_id for t in comparable)),
                _cfg().conf_refute_prompt)
    refs = tuple(dict.fromkeys(
        t.evidence_id for t, match in matches if match.match_type != "no"))
    return ("support",
            (f"提示内容匹配：answer声称『{prompt_text}』与"
             f"{best_template.use_case_name}的{best_template.e1_id}prompt"
             f"『{best_template.prompt}』{best.match_type}匹配"
             f"(score={best.score:.2f})"),
            refs,
            {"exact": _cfg().conf_exact, "substring": _cfg().conf_substring,
             "keyword": _cfg().conf_keyword}[best.match_type])


def _judge_ending(kind: EndingKind,
                  candidates: list[E1Template],
                  unscoped: bool = False,
                  ) -> tuple[Verdict, str, tuple[str, ...], float]:
    kinds = {ending_kind(t.ending) for t in candidates}
    kinds.discard(None)
    if not kinds:
        return ("not_in_evidence",
                "scope用例的E1行未声明处置(结束/继续)，处置声称无法核对",
                tuple(dict.fromkeys(t.evidence_id for t in candidates)),
                0.0)
    if kind in kinds:
        matched = [t for t in candidates if ending_kind(t.ending) == kind]
        return ("support",
                (f"处置声称一致：answer声称异常后"
                 f"{'结束/终止用例' if kind == 'end' else '继续/恢复'}，与E1模板"
                 f"处置『{matched[0].ending}』一致"),
                tuple(dict.fromkeys(t.evidence_id for t in matched)),
                _cfg().conf_ending)
    opposite = [t for t in candidates if ending_kind(t.ending) not in
                (None, kind)]
    if unscoped:
        return ("not_in_evidence",
                (f"处置声称与证据E1不一致(answer声称"
                 f"{'继续/恢复' if kind == 'continue' else '结束'}，E1模板处置"
                 f"为『{opposite[0].ending}』)，但answer未锚定具体用例，"
                 f"比对可能跨用例，无法据此反驳"),
                tuple(dict.fromkeys(t.evidence_id for t in opposite)),
                0.0)
    return ("refute",
            (f"处置语义矛盾：answer声称异常后"
             f"{'继续/恢复用例' if kind == 'continue' else '结束用例'}，但"
             f"E1模板处置为『{opposite[0].ending}』"
             f"(LOGIC-02异常处置策略)"),
            tuple(dict.fromkeys(t.evidence_id for t in opposite)),
            _cfg().conf_refute_ending)


def _evidence_span_context(
        statements: list[EvidenceStatement],
) -> tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]:
    """collect prompt-text spans and trigger-condition spans from evidence.

    Returns ((prompt_span, evidence_id), ...) and ((trigger_span,
    evidence_id), ...) with compacted text for substring checks.
    """
    prompts: list[tuple[str, str]] = []
    triggers: list[tuple[str, str]] = []
    for statement in statements:
        for match in _cfg().evidence_prompt_verb.finditer(statement.text):
            span = _compact(match.group("span"))
            if span:
                prompts.append((span, statement.evidence_id))
        for match in _cfg().evidence_trigger.finditer(statement.text):
            span = _compact(match.group("span"))
            if span:
                triggers.append((span, statement.evidence_id))
    return tuple(prompts), tuple(triggers)


def _trigger_swap_part(
        prompt_text: str,
        span_context: tuple[tuple[str, str], ...],
        trigger_context: tuple[tuple[str, str], ...],
) -> tuple[Verdict, str, tuple[str, ...], float] | None:
    """trigger/prompt swap: claimed prompt only ever appears as a condition.

    When the claimed prompt text appears in evidence inside a condition
    clause ("如果X，提示Y") and never as actual prompt text, the answer has
    mischaracterized a trigger condition as a system message -> refute part
    that takes precedence over weak keyword matching (S1QA-016).
    """
    claimed = _compact(prompt_text)
    if not claimed:
        return None
    in_prompt = any(
        claimed in span or span in claimed
        for span, _ in span_context if span)
    if in_prompt:
        return None
    hit_triggers = [
        (span, ref) for span, ref in trigger_context
        if span and claimed in span]
    if not hit_triggers:
        return None
    return ("refute",
            (f"触发条件与提示内容混淆：answer声称系统提示『{prompt_text}』，"
             f"但该文本在证据中仅作为触发条件出现（『如果{prompt_text}，"
             f"提示<其他内容>』式子句），并非系统实际返回的提示内容(LOGIC-02)"),
            tuple(dict.fromkeys(ref for _, ref in hit_triggers)),
            _cfg().conf_refute_prompt)


def _judge_claim(request: QAInput, claim: StructuredClaim,
                 templates: list[E1Template],
                 statements: list[EvidenceStatement],
                 scope: str | None) -> ClaimResult | None:
    prompts = extract_prompt_claims(claim.text)
    ending = extract_ending_claim(claim.text)
    if not prompts and ending is None:
        return None
    span_context, trigger_context = _evidence_span_context(statements)
    if scope is not None:
        unscoped = False
        scoped = [t for t in templates
                  if _compact(t.use_case_name) == _compact(scope)]
        if not scoped:
            scope_present = any(
                _compact(s.scope_key) == _compact(scope) for s in statements)
            reason = ("scope用例的用例表无异常流行"
                      if scope_present else "冻结证据无scope用例的用例表")
            return _nie_result(
                request, claim,
                f"{reason}，answer的异常处置声称无法核对（用例{scope}）")
    else:
        # scope unresolved: the question is condition-focused (no use-case
        # anchor); any-match is legitimate because retrieval was
        # question-conditioned, but a mismatch is NOT decisive (it may be a
        # cross-use-case comparison) -> mismatch downgrades to NIE.
        unscoped = True
        scoped = templates
    if not scoped:
        return _nie_result(
            request, claim, "冻结证据中无任何异常流E1行，异常处置声称无法核对")
    candidates = _candidate_templates(claim.text, scoped)
    exception_focused = bool(
        _cfg().e1_assertion.search(claim.text)
        or _cfg().exception_q.search(request.question))

    parts: list[tuple[Verdict, str, tuple[str, ...], float]] = []
    if prompts:
        # trigger/prompt swap takes precedence over weak keyword matching,
        # but only when the question asks for the prompt text itself: then
        # answering with a condition-clause text is a decisive contradiction
        # (S1QA-016). For exception-kind/flow questions the same wording is
        # an embedded detail graded leniently (S1QA-052 silver=NIE).
        if _cfg().prompt_q.search(request.question):
            swap = _trigger_swap_part(
                prompts[0], span_context, trigger_context)
            if swap is not None:
                parts.append(swap)
        parts.append(_judge_prompt(
            prompts[0], candidates, span_context, trigger_context,
            strict=exception_focused and not unscoped,
            unscoped=unscoped))
    if ending is not None:
        parts.append(_judge_ending(ending, candidates, unscoped=unscoped))
    if not parts:
        return None
    verdicts = {part[0] for part in parts}
    if "refute" in verdicts:
        verdict: Verdict = "refute"
    elif "support" in verdicts:
        verdict = "support"
    else:
        verdict = "not_in_evidence"
    rationale = "；".join(part[1] for part in parts)
    refs = tuple(dict.fromkeys(
        ref for part in parts for ref in part[2]))
    confidence = max(part[3] for part in parts)
    return _result(request, claim, verdict, rationale, refs, confidence)


def verify_e1_consistency(
        request: QAInput,
        statements: list[EvidenceStatement],
        claims: list[StructuredClaim] | None = None,
) -> list[ClaimResult]:
    """校验answer的异常处置声称与用例表E1模板的一致性(LOGIC-02).

    输出: 证据侧主题错位检查(method="e1_template_match", claim_id=e1d*)
    + answer侧逐claim结果(claim_id={instance}-{claim_id}); 聚合用
    aggregate_e1_verdict(refute > not_in_evidence > support). 无异常声称
    且无文档违例时返回[].
    """
    structured = (claims if claims is not None
                  else decompose_answer(request.answer, request.question))
    templates = extract_e1_templates(statements)
    doc_results = check_e1_topic_mismatch(statements, templates)
    results: list[ClaimResult] = [
        replace(claim, claim_id=f"{request.instance_id}-e1d{index:02d}")
        for index, claim in enumerate(doc_results, start=1)]
    if not structured:
        return results
    scope = resolve_e1_scope(request.question, structured, statements)
    for claim in structured:
        if not _cfg().exception_claim.search(claim.text):
            continue
        result = _judge_claim(request, claim, templates, statements, scope)
        if result is not None:
            results.append(result)
    return results


def aggregate_e1_verdict(results: list[ClaimResult]) -> Verdict:
    """聚合同qa_module语义: refute > not_in_evidence > support; 空结果NIE."""
    if not results:
        return "not_in_evidence"
    labels = {result.verdict for result in results}
    if "refute" in labels:
        return "refute"
    if "not_in_evidence" in labels:
        return "not_in_evidence"
    return "support"


__all__ = [
    "CHECK_ITEMS",
    "METHOD",
    "E1Template",
    "PromptMatch",
    "aggregate_e1_verdict",
    "check_e1_topic_mismatch",
    "compare_prompts",
    "ending_kind",
    "extract_e1_templates",
    "extract_ending_claim",
    "extract_prompt_claims",
    "resolve_e1_scope",
    "verify_e1_consistency",
]
