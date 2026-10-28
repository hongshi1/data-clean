"""序列对齐专家(L1组件, LOGIC-03事件时序).

级联架构L1符号验证层的序列比对专家: 从用例表主事件流(Actor的动作/
系统的动作列)提取编号步骤, 与answer声称的步骤顺序做对齐, 检测时序
不一致.

判定规则(LOGIC-03):
  support          answer步骤内容与证据步骤匹配且顺序一致
  refute           answer交换了证据中有编号的步骤(重排, 含偏差定位)
  not_in_evidence  answer含证据中没有的步骤(凭空捏造, 不判refute), 或
                   证据无用例主事件流编号步骤/无法定位用例scope

方法:
  方法1(确定性, 默认): 编号提取 + 字符重合argmax配对 + 证据编号位置
    单调性检查 —— answer声称顺序 vs 证据编号顺序(编号直接比对).
  方法2(进阶, 本地BGE可用时): 对确定性未覆盖的步骤用BGE嵌入余弦补配
    对, 并输出Needleman-Wunsch全局对齐(gap罚分-0.5)的对齐分数+逐对齐
    点. 判定仍由argmax配对+单调性驱动: NW全局对齐本身保序, 无法定位
    重排, 因此重排偏差定位用无约束argmax配对的交叉实现.

适用性门(G4 P1粒度治理, docs/srs_project/50_support_recall_analysis.md
§6): 序列通道只处理"事件时序"形态的answer——问题须是流程/步骤型
(含主事件流/步骤/流程/时序等指示词), 且编号项须构成事件流而非并列
枚举: 编号项含"失败/错误/异常"关键词占比≥0.5(异常类型枚举, 如
"1．连接检查 2．JSON解析失败"), 或编号项无时序连接词(然后/随后/之后
/接着/下一步…)且平均长度>40字符(带标签的长并列项, 如"1．数据库操作:
包括初始化、…")时跳过该实例——否则编号功能清单会被二次分解成
"1．"前缀claim, 否决L0/L3已验证的内容(S1QA-066/069/077).

已知文档违例(04号SRS):
  - b162/表28(数据插入)Actor列无编号: 以缺失编号按文档序推断(1)
  - 编号标点混用(1. / 2． / 3、): 由同一正则统一捕获
  无法推断编号的无编号主事件流段时序不可知, 不参与比对.

复用: evidence_statements.EvidenceStatement / answer_structure.
StructuredClaim / qa_models.ClaimResult; BGE走 algorithms.common.
bge_local(惰性加载; use_cache=False避免加载276MB共享缓存; eval+
no_grad同文本同向量, 确定性可复现). 本模块无LLM调用.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from algorithms.common.bge_local import BgeLocal
from algorithms.consistency.answer_structure import StructuredClaim
from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.qa_models import ClaimResult, QAInput, Verdict
from algorithms.consistency.rulepack import RulePack, default_rulepack

_CHECK_ITEM = "LOGIC-03"
#: NW对齐算法参数与异常流位置基准——"怎么比"的引擎能力, 留在源码
#: (docs/srs_project/64_rulepack_design.md §4配置化分层)
_GAP_PENALTY = -0.5
_EXCEPTION_BASE = 10_000.0


@dataclass(frozen=True)
class _SequenceConfig:
    """从rule pack编译的序列对齐配置(步骤模式+词表+窗口+阈值)."""

    step: re.Pattern[str]
    exception_field: re.Pattern[str]
    question_scope: re.Pattern[str]
    preamble: re.Pattern[str]
    punct: re.Pattern[str]
    flow_question: re.Pattern[str]
    substantive_step: re.Pattern[str]
    flow_fields: tuple[str, ...]
    failure_keywords: tuple[str, ...]
    temporal_connectors: tuple[str, ...]
    strip_chars: str
    min_step_chars: int
    parallel_item_avg_len: int
    pair_det: float
    pair_bge: float
    failure_keyword_ratio: float
    conf_det: float
    conf_bge: float


def _build_config(pack: RulePack) -> _SequenceConfig:
    return _SequenceConfig(
        step=pack.template("seq_step"),
        exception_field=pack.template("seq_exception_field"),
        question_scope=pack.template("seq_question_scope"),
        preamble=pack.template("seq_preamble"),
        punct=pack.template("seq_punct"),
        flow_question=pack.template("seq_flow_question"),
        substantive_step=pack.template("seq_substantive_step"),
        flow_fields=pack.vocabulary("seq_flow_fields"),
        failure_keywords=pack.vocabulary("seq_failure_keywords"),
        temporal_connectors=pack.vocabulary("seq_temporal_connectors"),
        strip_chars=str(pack.join_param("sequence", "strip_chars", "")),
        min_step_chars=int(pack.join_param("sequence", "min_step_chars", 8)),
        parallel_item_avg_len=int(
            pack.join_param("sequence", "parallel_item_avg_len", 40)),
        pair_det=pack.threshold("seq_pair_det"),
        pair_bge=pack.threshold("seq_pair_bge"),
        failure_keyword_ratio=pack.threshold("seq_failure_keyword_ratio"),
        conf_det=pack.threshold("seq_conf_det"),
        conf_bge=pack.threshold("seq_conf_bge"),
    )


_SEQ_CONFIG: _SequenceConfig | None = None
_SEQ_PACK: RulePack | None = None


def _cfg() -> _SequenceConfig:
    """惰性加载默认rule pack并编译序列配置(按pack身份缓存, import期零I/O)."""
    global _SEQ_CONFIG, _SEQ_PACK
    pack = default_rulepack()
    if _SEQ_CONFIG is None or _SEQ_PACK is not pack:
        _SEQ_PACK = pack
        _SEQ_CONFIG = _build_config(pack)
    return _SEQ_CONFIG



@dataclass(frozen=True)
class FlowStep:
    """用例主事件流中的一个证据时序单元(编号步骤或异常流)."""

    text: str
    field_name: str
    scope_key: str
    number: int | None
    position: float
    statement_id: str
    evidence_id: str


@dataclass(frozen=True)
class AnswerStep:
    """answer声称的一个步骤(编号+内容+answer内次序+关联claim)."""

    text: str
    number: int | None
    order: int
    claim_id: str


@dataclass(frozen=True)
class AlignmentPoint:
    """一个NW对齐点: answer步骤索引 ↔ 证据单元索引."""

    answer_index: int
    evidence_index: int
    similarity: float


@dataclass(frozen=True)
class SequenceAlignment:
    """Needleman-Wunsch全局对齐结果(方法2诊断输出)."""

    score: float
    pairs: tuple[AlignmentPoint, ...]
    channel: str


# ── 文本工具 ────────────────────────────────────────────


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _clean_step_text(text: str) -> str:
    """去markdown强调与首尾标点; 保留内部结构(『标签：内容』)."""
    cleaned = text.replace("**", "")
    return cleaned.strip().strip(_cfg().strip_chars).strip()


def char_jaccard(left: str, right: str) -> float:
    """字符集合Jaccard(去标点空白): 确定性词面重合度."""
    a = set(_cfg().punct.sub("", left))
    b = set(_cfg().punct.sub("", right))
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _argmax(scores: list[float]) -> int:
    best = 0
    for index in range(1, len(scores)):
        if scores[index] > scores[best]:
            best = index
    return best


# ── 证据侧: 用例主事件流步骤提取 ────────────────────────


def _is_flow_field(field_name: str) -> bool:
    return field_name in _cfg().flow_fields or bool(
        _cfg().exception_field.match(field_name))


def _cell_body(statement_text: str, field_name: str) -> str:
    """去掉scope+字段名前缀, 取单元格正文(兼容无scope前缀)."""
    index = statement_text.find(field_name)
    if index < 0:
        return statement_text
    body = statement_text[index + len(field_name):]
    return body.lstrip(_cfg().strip_chars).strip()


def _numbered_segments(body: str) -> tuple[list[tuple[int, str]], list[str]]:
    """切分编号段与无编号段; 编号标点混用(1./2．/3、)统一捕获."""
    numbered: list[tuple[int, str]] = []
    unnumbered: list[str] = []
    cursor = 0
    for match in _cfg().step.finditer(body):
        if match.start() > cursor:
            segment = _clean_step_text(body[cursor:match.start()])
            if len(segment) >= _cfg().min_step_chars:
                unnumbered.append(segment)
        content = _clean_step_text(match.group(2))
        if content:
            numbered.append((int(match.group(1)), content))
        cursor = match.end()
    trailing = _clean_step_text(body[cursor:])
    if len(trailing) >= _cfg().min_step_chars:
        unnumbered.append(trailing)
    return numbered, unnumbered


def _distinct_flow_scopes(statements: list[EvidenceStatement]) -> list[str]:
    return list(dict.fromkeys(
        statement.scope_key for statement in statements
        if _is_flow_field(statement.field_name) and statement.scope_key))


def _scope_overlap(scope_key: str, candidate: str) -> bool:
    key = _compact(scope_key).lower()
    if not key or not candidate:
        return False
    return key in candidate or candidate in key


def _flow_pool(statements: list[EvidenceStatement],
               scope: str | None) -> list[EvidenceStatement]:
    selected = [s for s in statements if _is_flow_field(s.field_name)]
    if scope is None:
        return selected
    return [s for s in selected if _scope_overlap(s.scope_key, scope)]


def extract_flow_steps(statements: list[EvidenceStatement],
                       scope: str | None = None) -> list[FlowStep]:
    """提取用例主事件流时序单元(编号步骤+异常流).

    Actor动作列与系统动作列的编号步骤合并后按编号排序(编号=文档声称
    时序); 无编号段按缺失编号推断(b162违例); 异常流行按行序追加在全部
    编号步骤之后. scope为None时不过滤scope.
    """
    numbered: list[tuple[int, str, EvidenceStatement]] = []
    unnumbered: list[tuple[str, EvidenceStatement]] = []
    exceptions: list[tuple[str, EvidenceStatement]] = []
    for statement in _flow_pool(statements, scope):
        if _cfg().exception_field.match(statement.field_name):
            body = _cell_body(statement.text, statement.field_name)
            if body:
                exceptions.append((body, statement))
            continue
        body = _cell_body(statement.text, statement.field_name)
        nums, unnums = _numbered_segments(body)
        numbered.extend((num, content, statement) for num, content in nums)
        unnumbered.extend((content, statement) for content in unnums)
    present = {num for num, _, _ in numbered}
    missing = [num for num in range(1, max(present, default=0) + 1)
               if num not in present]
    for index, (content, statement) in enumerate(unnumbered):
        if index < len(missing):
            numbered.append((missing[index], content, statement))
    numbered.sort(key=lambda item: (
        item[0], item[2].row_index, _cfg().flow_fields.index(item[2].field_name)))
    flow: list[FlowStep] = [
        FlowStep(text=content, field_name=statement.field_name,
                 scope_key=statement.scope_key, number=num,
                 position=float(num), statement_id=statement.statement_id,
                 evidence_id=statement.evidence_id)
        for num, content, statement in numbered
    ]
    for content, statement in sorted(exceptions,
                                     key=lambda item: item[1].row_index):
        flow.append(FlowStep(
            text=content, field_name=statement.field_name,
            scope_key=statement.scope_key, number=None,
            position=_EXCEPTION_BASE + statement.row_index,
            statement_id=statement.statement_id,
            evidence_id=statement.evidence_id))
    return flow


def resolve_flow_scope(question: str,
                       claims: list[StructuredClaim] | None,
                       statements: list[EvidenceStatement]) -> str | None:
    """定位目标用例scope: question名称 > claim scope_hint > 单一scope回退.

    多个用例scope且无候选命中时返回None(拒绝跨scope比对).
    """
    flow_scopes = _distinct_flow_scopes(statements)
    if not flow_scopes:
        return None
    candidates: list[str] = []
    match = _cfg().question_scope.search(question)
    if match:
        candidates.append(match.group("name"))
    candidates.extend(
        claim.scope_hint for claim in (claims or [])
        if claim.structure == "step" and claim.scope_hint)
    for candidate in candidates:
        hits = [scope for scope in flow_scopes
                if _scope_overlap(scope, _compact(candidate).lower())]
        if len(hits) == 1:
            return hits[0]
    if len(flow_scopes) == 1:
        return flow_scopes[0]
    return None


# ── answer侧: 步骤提取 ──────────────────────────────────


def _link_claim(content: str, claims: list[StructuredClaim] | None) -> str:
    target = _compact(content)
    for claim in claims or []:
        text = _compact(claim.text)
        if text and (text in target or target in text):
            return claim.claim_id
    return ""


def extract_answer_steps(answer: str,
                          claims: list[StructuredClaim] | None = None,
                          ) -> list[AnswerStep]:
    """提取answer声称的编号步骤(同证据正则); 无编号时回退
    structure="step"claims的出现序(过滤导语/结语, 且至少2条才构成序列)."""
    steps: list[AnswerStep] = []
    for match in _cfg().step.finditer(answer):
        content = _clean_step_text(match.group(2))
        if not content:
            continue
        steps.append(AnswerStep(
            text=content, number=int(match.group(1)), order=len(steps),
            claim_id=_link_claim(content, claims)))
    if steps:
        return steps
    fallback: list[AnswerStep] = []
    for claim in claims or []:
        if (claim.structure == "step"
                and len(claim.text) >= _cfg().min_step_chars
                and not _cfg().preamble.search(claim.text)):
            fallback.append(AnswerStep(
                text=claim.text, number=None, order=len(fallback),
                claim_id=claim.claim_id))
    return fallback if len(fallback) >= 2 else []


def is_sequence_applicable(question: str,
                           answer_steps: list[AnswerStep]) -> bool:
    """适用性门: answer编号项(结合question形态)是否构成事件时序.

    三条跳过规则(命中任一即判为并列枚举, 序列通道不适用):
    1. 问题非流程/步骤型(无主事件流/步骤/流程/时序等指示词)——
       "有什么特点/支持哪些操作/包括哪些内容"类问题的编号项是
       功能/特点清单(S1QA-066/069/077/053);
    2. 编号项含"失败/错误/异常"关键词占比≥0.5——异常类型枚举
       (如"1．连接检查 2．JSON解析失败 3．SQL执行失败");
    3. 编号项无时序连接词且平均长度>40字符——带标签的长并列项
       ("1．数据库操作：包括初始化、读取配置文件连接、…").
    真步骤序列(S1QA-024: 流程型问题+平均39字符+含异常项但占比1/3)
    不受影响.
    """
    if not answer_steps:
        return False
    if not _cfg().flow_question.search(question):
        return False
    texts = [step.text for step in answer_steps]
    failure_hits = sum(
        1 for text in texts
        if any(keyword in text for keyword in _cfg().failure_keywords))
    if failure_hits / len(texts) >= _cfg().failure_keyword_ratio:
        return False
    joined = "".join(texts)
    if not any(connector in joined
                for connector in _cfg().temporal_connectors):
        avg_len = sum(len(text) for text in texts) / len(texts)
        if avg_len > _cfg().parallel_item_avg_len:
            return False
    return True


# ── 序列对齐(Needleman-Wunsch) ──────────────────────────


def needleman_wunsch(similarity: list[list[float]],
                     gap: float = _GAP_PENALTY,
                     ) -> tuple[float, list[tuple[int, int]]]:
    """Needleman-Wunsch全局对齐(纯函数, 平局优先对角).

    返回(对齐总分, 对齐点[(answer行, 证据列)]按answer序).
    """
    rows = len(similarity)
    cols = len(similarity[0]) if rows else 0
    score: list[list[float]] = [[0.0] * (cols + 1) for _ in range(rows + 1)]
    for j in range(1, cols + 1):
        score[0][j] = j * gap
    for i in range(1, rows + 1):
        score[i][0] = i * gap
        for j in range(1, cols + 1):
            score[i][j] = max(
                score[i - 1][j - 1] + similarity[i - 1][j - 1],
                score[i - 1][j] + gap,
                score[i][j - 1] + gap,
            )
    pairs: list[tuple[int, int]] = []
    i, j = rows, cols
    while i > 0 and j > 0:
        if score[i][j] == score[i - 1][j - 1] + similarity[i - 1][j - 1]:
            pairs.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif score[i][j] == score[i - 1][j] + gap:
            i -= 1
        else:
            j -= 1
    pairs.reverse()
    return score[rows][cols], pairs


def align_sequences(answer_texts: list[str], flow_texts: list[str],
                    similarity: Callable[[str, str], float],
                    *, gap: float = _GAP_PENALTY, channel: str = "custom",
                    ) -> SequenceAlignment:
    """对齐answer步骤序列与证据步骤序列(方法2诊断入口)."""
    matrix = [[similarity(a, e) for e in flow_texts]
              for a in answer_texts]
    total, index_pairs = needleman_wunsch(matrix, gap)
    return SequenceAlignment(
        score=total,
        pairs=tuple(
            AlignmentPoint(answer_index=i, evidence_index=j,
                           similarity=matrix[i][j])
            for i, j in index_pairs),
        channel=channel)


# ── BGE通道 ─────────────────────────────────────────────


def _default_bge_client() -> BgeLocal | None:
    """惰性创建本地BGE客户端; 不可用返回None(显式降级, 不静默)."""
    client = BgeLocal(use_cache=False)
    if client.ensure() == "unavailable":
        return None
    return client


def _bge_cosine_matrix(client: BgeLocal, answer_texts: list[str],
                       flow_texts: list[str]) -> list[list[float]]:
    vectors = client.embed(list(dict.fromkeys(answer_texts + flow_texts)))
    rows: list[list[float]] = []
    for answer_text in answer_texts:
        va = vectors.get(answer_text) or []
        row: list[float] = []
        for flow_text in flow_texts:
            vb = vectors.get(flow_text) or []
            row.append(sum(x * y for x, y in zip(va, vb))
                       if va and vb else 0.0)
        rows.append(row)
    return rows


# ── 判定 ────────────────────────────────────────────────


def _unit_label(step: FlowStep) -> str:
    if step.number is not None:
        return f"第{step.number}步({step.field_name})"
    return f"{step.field_name}(主事件流后)"


def _claim_text(step: AnswerStep) -> str:
    if step.number is not None:
        return f"{step.number}．{step.text}"
    return step.text


def _result_claim_id(request: QAInput, step: AnswerStep, order: int) -> str:
    if step.claim_id:
        return f"{request.instance_id}-{step.claim_id}"
    return f"{request.instance_id}-seq{order + 1:02d}"


def _nie_result(request: QAInput, step: AnswerStep, order: int,
                rationale: str) -> ClaimResult:
    return ClaimResult(
        claim_id=_result_claim_id(request, step, order),
        claim_text=_claim_text(step),
        verdict="not_in_evidence",
        check_item_candidates=(_CHECK_ITEM,),
        evidence_refs=(),
        rationale=rationale,
        method="sequence_alignment",
        confidence=0.0,
    )


def _find_inversions(match: dict[int, int], flow_steps: list[FlowStep],
                     ) -> list[tuple[int, int]]:
    """answer序内证据位置严格下降的配对 = 重排偏差定位."""
    ordered = sorted(match)
    inversions: list[tuple[int, int]] = []
    for a in range(len(ordered)):
        for b in range(a + 1, len(ordered)):
            i, k = ordered[a], ordered[b]
            if flow_steps[match[i]].position > flow_steps[match[k]].position:
                inversions.append((i, k))
    return inversions


def verify_sequence(request: QAInput,
                    statements: list[EvidenceStatement],
                    claims: list[StructuredClaim] | None = None,
                    *,
                    bge: BgeLocal | None = None,
                    use_bge: bool = True) -> list[ClaimResult]:
    """校验answer步骤序列与用例表主事件流编号步骤的时序一致性.

    输出逐answer步骤的ClaimResult(method="sequence_alignment"); 聚合用
    aggregate_sequence_verdict(refute > not_in_evidence > support).

    非事件时序形态的实例(见is_sequence_applicable)不产生"凭空步骤"判定:
    链接到结构化claim的编号项仍输出保守NIE(该项内容未被本通道验证,
    但同文本的其他通道判定——含L3 support——在per-claim融合中可覆盖
    它); 未链接的表格残片(如"1.1 |"单元格)不输出任何claim.
    """
    answer_steps = extract_answer_steps(request.answer, claims)
    if not answer_steps:
        return []
    if not is_sequence_applicable(request.question, answer_steps):
        return [
            _nie_result(request, step, order,
                        "answer编号项为并列枚举(非事件流), 时序通道不适用; "
                        "该项内容未被本通道验证")
            for order, step in enumerate(answer_steps)
            if step.claim_id and _cfg().substantive_step.search(step.text)
        ]
    scope = resolve_flow_scope(request.question, claims, statements)
    flow_scopes = _distinct_flow_scopes(statements)
    if scope is None and len(flow_scopes) > 1:
        return [
            _nie_result(request, step, order,
                        f"冻结context含{len(flow_scopes)}个用例主事件流scope"
                        f"且无法从question/answer定位目标用例, 拒绝跨scope"
                        f"时序比对")
            for order, step in enumerate(answer_steps)
        ]
    flow_steps = extract_flow_steps(statements, scope)
    if not any(step.number is not None for step in flow_steps):
        return [
            _nie_result(request, step, order,
                        "证据无用例主事件流编号步骤, 时序不可核对")
            for order, step in enumerate(answer_steps)
        ]

    det_sim = [[char_jaccard(a.text, e.text) for e in flow_steps]
               for a in answer_steps]
    match: dict[int, tuple[int, str, float]] = {}
    for i in range(len(answer_steps)):
        j = _argmax(det_sim[i])
        if det_sim[i][j] >= _cfg().pair_det:
            match[i] = (j, "deterministic", det_sim[i][j])

    bge_sim: list[list[float]] | None = None
    bge_unavailable = False
    if use_bge and len(match) < len(answer_steps):
        client = bge if bge is not None else _default_bge_client()
        if client is None:
            bge_unavailable = True
        else:
            bge_sim = _bge_cosine_matrix(
                client, [a.text for a in answer_steps],
                [e.text for e in flow_steps])
            for i in range(len(answer_steps)):
                if i in match:
                    continue
                j = _argmax(bge_sim[i])
                if bge_sim[i][j] >= _cfg().pair_bge:
                    match[i] = (j, "bge", bge_sim[i][j])

    inversions = _find_inversions({i: j for i, (j, _, _) in match.items()},
                                  flow_steps)
    involved = {index for pair in inversions for index in pair}
    results: list[ClaimResult] = []
    for i, step in enumerate(answer_steps):
        if i not in match:
            best = max(det_sim[i]) if det_sim[i] else 0.0
            if bge_sim is not None:
                best = max(best, max(bge_sim[i]))
            note = "BGE通道不可用, " if bge_unavailable else ""
            results.append(_nie_result(
                request, step, i,
                f"answer步骤在主事件流证据中无匹配({note}最佳相似度"
                f"{best:.2f}低于配对阈值), 判凭空步骤"))
            continue
        j, channel, sim = match[i]
        target = flow_steps[j]
        confidence = (_cfg().conf_bge if channel == "bge"
                      else _cfg().conf_det)
        refs = (target.evidence_id,)
        if i in involved:
            pair = next(p for p in inversions if i in p)
            other = pair[0] if pair[1] == i else pair[1]
            other_target = flow_steps[match[other][0]]
            refs = tuple(sorted({target.evidence_id,
                                 other_target.evidence_id}))
            results.append(ClaimResult(
                claim_id=_result_claim_id(request, step, i),
                claim_text=_claim_text(step),
                verdict="refute",
                check_item_candidates=(_CHECK_ITEM,),
                evidence_refs=refs,
                rationale=(f"步骤时序与证据矛盾: answer步骤{i + 1}"
                           f"『{step.text[:16]}…』对应证据"
                           f"{_unit_label(target)}, answer步骤{other + 1}"
                           f"对应{_unit_label(other_target)}, 证据编号顺序"
                           f"与answer声称顺序颠倒; 匹配通道={channel}, "
                           f"相似度={sim:.2f}"),
                method="sequence_alignment",
                confidence=confidence,
            ))
            continue
        results.append(ClaimResult(
            claim_id=_result_claim_id(request, step, i),
            claim_text=_claim_text(step),
            verdict="support",
            check_item_candidates=(_CHECK_ITEM,),
            evidence_refs=refs,
            rationale=(f"answer步骤与证据{_unit_label(target)}内容匹配且"
                       f"时序位置一致(通道={channel}, "
                       f"相似度={sim:.2f})"),
            method="sequence_alignment",
            confidence=confidence,
        ))
    if bge_sim is not None:
        total, index_pairs = needleman_wunsch(bge_sim)
        alignment = SequenceAlignment(
            score=total,
            pairs=tuple(AlignmentPoint(answer_index=ai, evidence_index=ej,
                                       similarity=bge_sim[ai][ej])
                        for ai, ej in index_pairs),
            channel="bge")
        summary = "; ".join(
            f"{p.answer_index}↔{p.evidence_index}" for p in alignment.pairs)
        first = results[0]
        results[0] = ClaimResult(
            claim_id=first.claim_id, claim_text=first.claim_text,
            verdict=first.verdict,
            check_item_candidates=first.check_item_candidates,
            evidence_refs=first.evidence_refs,
            rationale=(f"{first.rationale}; BGE-NW全局对齐: 分数"
                       f"{alignment.score:.2f}, 对齐点{summary}"),
            method=first.method, confidence=first.confidence)
    return results


def aggregate_sequence_verdict(results: list[ClaimResult]) -> Verdict:
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
    "FlowStep",
    "AnswerStep",
    "AlignmentPoint",
    "SequenceAlignment",
    "char_jaccard",
    "extract_flow_steps",
    "resolve_flow_scope",
    "extract_answer_steps",
    "is_sequence_applicable",
    "needleman_wunsch",
    "align_sequences",
    "verify_sequence",
    "aggregate_sequence_verdict",
]
