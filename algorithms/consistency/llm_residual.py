"""L3 LLM residual verification channel (C1 residual principle).

Only claims the deterministic L0/L1/L2 channels left unresolved
(``semantic_unresolved`` / ``conservative_unresolved`` NIE results) enter the
LLM; already-decided claims never do. The residual claims of one QA instance
are batched into one focused prompt (question + numbered claims + numbered
evidence statements, scope-matched statements first), so a 91-QA corpus stays
far under the <=200-call budget while every claim still gets its own verdict,
evidence citation and rationale. All calls go through ``llm_json(cache=True)``
for reproducibility; a failed call is retried once and then degrades to a
conservative NIE whose method records the failure (nothing is swallowed).

The module is stateless and pure: no module-level mutable state, no I/O at
import time (``llm_client`` is imported lazily because ``ai_config`` reads
``.env`` at import).
"""
from __future__ import annotations

import re

from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.qa_models import ClaimResult, QAInput

RESIDUAL_METHODS = ("semantic_unresolved", "conservative_unresolved")
VERDICTS = ("support", "refute", "not_in_evidence")

_STATEMENT_CAP = 30
_STATEMENT_TRUNC = 120
_CLAIM_CHUNK = 10
REFUTE_CONFIDENCE_GATE = 0.8

_SYSTEM = (
    "你是GJB军事软件需求文档的一致性审查员。给定证据语句列表，判定answer声明属于哪种："
    "support（证据明确支持）/refute（证据明确矛盾）/not_in_evidence（证据无法判定）。"
    "判定规则："
    "1.开放世界：证据中没有≠文档中不存在。缺失的内容（子功能名、前置条件、"
    "效果性表述、解释性扩展）只能判not_in_evidence，绝不能作为refute的依据。"
    "2.锚定：把声明主体锚定到问题所点名对象的具体功能行/用例行"
    "（如问题问'对BLOB数据进行X操作的功能'，锚定BLOB数据操作行——按问题主体"
    "的对象名锚定，而不是按操作名去找名称相似的另一功能行），"
    "只有锚定行自身的值与声明冲突才refute。设备/方式名称列是精确集合，"
    "同一功能的设备集合不同（如多出或缺少'手持'）→refute；参数值、标识符、"
    "产物类型不同→refute（'数据对象'与'目标语言代码'是不同产物）。"
    "上层功能的概括描述与其子功能行的值冲突时，以子功能行为准。"
    "全称断言（所有/均/都）被具体反例直接矛盾→refute。"
    "把主体换成另一个用例/功能行后发现的差异、或证据中没有主体自身的行"
    "（例如该用例的前置条件行不存在），都不是矛盾→not_in_evidence。"
    "3.值判定：answer真正断言的是值（沿用哪些设备、适用哪些阶段、包括哪些操作、"
    "产物是什么），不是问题中已点名对象的存在性。锚定行的对应值与声明一致→"
    "support；锚定行给出不同的值→refute；锚定行没有该值→not_in_evidence。"
    "问题点名的子功能名未在锚定行逐字出现不阻止support"
    "（功能'包括'列表是非穷尽的，近义子操作视为同一：修改≈更新/删除记录、"
    "添加≈插入）；声明点名的接口/用例名称未在证据中逐字出现时"
    "（问题预设的主体名除外）→not_in_evidence。"
    "4.解释性/效果性扩展（'这意味着''包括但不限于''确保/保证/提高/优化/便于'"
    "引出的内容）本身无证据时判not_in_evidence：不得因锚定值一致而连带support，"
    "也不得因扩展内容与锚定值不同而refute。"
    "5.拿不准时一律判not_in_evidence。"
    "判定必须引用证据编号(ev-N)。只输出JSON。"
    "证据语句由表格线性化生成，字段标签可能错位，判定以语句内容为准。"
)

_RETRY_SUFFIX = (
    "\n\n上一次输出无法解析。请严格只输出一个JSON对象，"
    "不要markdown代码块、不要任何多余文字。"
)

_JSON_SPEC = (
    '输出JSON：{"claims": [{"claim_id": "c1", '
    '"verdict": "support|refute|not_in_evidence", '
    '"evidence_refs": ["ev-1"], "rationale": "一句话理由", "confidence": 0.9}]}；'
    "对每条待判定声明各输出一项；support/refute必须在evidence_refs中引用证据编号，"
    "not_in_evidence时evidence_refs为[]。"
)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _bigrams(text: str) -> frozenset[str]:
    return frozenset(text[i:i + 2] for i in range(len(text) - 1))


def _dedupe_statements(
        statements: list[EvidenceStatement]) -> list[EvidenceStatement]:
    seen: set[str] = set()
    unique: list[EvidenceStatement] = []
    for statement in statements:
        key = _compact(statement.text)
        if key and key not in seen:
            seen.add(key)
            unique.append(statement)
    return unique


def _select_statements(
        claims_text: str,
        statements: list[EvidenceStatement]) -> list[EvidenceStatement]:
    """Pick ≤30 statements, grouped by logical table row.

    Statements linearized from the same source row (evidence_id + row_index)
    are one fact unit: capability rows are column-shifted by the deterministic
    linearizer, so the row's subject and its device/stage values live in
    different statements — selecting fragments loses the fact. Rows are
    ranked by scope match, then by subject overlap (the row's scope key plus
    its first, subject-bearing statement) so a row about the claim's subject
    outranks rows that merely repeat generic stage/device values.
    """
    joint = _compact(claims_text)
    claim_grams = _bigrams(joint)
    rows: dict[tuple[str, int], list[EvidenceStatement]] = {}
    order: list[tuple[str, int]] = []
    position: dict[tuple[str, int], int] = {}
    for statement in _dedupe_statements(statements):
        key = (statement.evidence_id, statement.row_index)
        if key not in rows:
            position[key] = len(order)
            order.append(key)
        rows.setdefault(key, []).append(statement)

    def row_rank(key: tuple[str, int]) -> tuple[int, int, int, int]:
        row = rows[key]
        scope = 0 if any(s.scope_key and s.scope_key in joint
                         for s in row) else 1
        subject = _compact((row[0].scope_key or "") + row[0].text)
        subject_overlap = len(_bigrams(subject) & claim_grams)
        union_overlap = len(
            set().union(*(_bigrams(_compact(s.text)) & claim_grams
                          for s in row)))
        return (scope, -subject_overlap, -union_overlap, position[key])

    selected: list[EvidenceStatement] = []
    for key in sorted(order, key=row_rank):
        if len(selected) >= _STATEMENT_CAP:
            break
        selected.extend(rows[key])
    return selected[:_STATEMENT_CAP]


def _build_prompt(question: str, claims: list[ClaimResult],
                  statements: list[EvidenceStatement]) -> str:
    lines = [f"【问题】{question}", "", "【待判定声明】（对每条独立判定）"]
    lines += [f"c{i}: {claim.claim_text}" for i, claim in enumerate(claims, 1)]
    lines += ["", "（声明是对answer的分解；问题中已点名的功能/对象是存在性预设，"
              "answer断言的是它们的值——设备、阶段、参数、产物。）"]
    lines += ["", "【证据语句】"]
    for i, statement in enumerate(statements, 1):
        text = re.sub(r"\s+", " ", statement.text).strip()
        lines.append(f"ev-{i}: {text[:_STATEMENT_TRUNC]}")
    lines += ["", _JSON_SPEC]
    return "\n".join(lines)


def _call_llm(prompt: str) -> dict:
    """One cached JSON call; imported lazily (ai_config reads .env at import).

    Same model (glm-5.3) and JSON contract as the silver-label review runs,
    but with ``reasoning_effort: low`` — the review pipeline's proven fallback
    mode. Full thinking mode burns the whole token budget on reasoning and
    truncates the visible content to fragmentary prose before any JSON.
    """
    from algorithms.common.llm_client import llm_json

    payload, _model = llm_json(
        prompt, system=_SYSTEM, prefer="glm", cache=True,
        allow_fallback=False, model_override="glm-5.3",
        max_tokens=16000, timeout=300,
        extra_payload={
            "response_contract": "json_final_content_v2",
            "reasoning_effort": "low",
        })
    return payload if isinstance(payload, dict) else {}


def _parse_entries(payload: dict,
                   n_claims: int) -> dict[int, dict] | None:
    entries = payload.get("claims")
    if not isinstance(entries, list):
        return None
    parsed: dict[int, dict] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        match = re.search(r"(\d+)", str(item.get("claim_id", "")))
        if not match:
            continue
        index = int(match.group(1)) - 1
        if not 0 <= index < n_claims or index in parsed:
            continue
        verdict = re.sub(r"\s+", "_",
                         str(item.get("verdict", "")).strip().lower())
        if verdict not in VERDICTS:
            verdict = "not_in_evidence"
        refs = item.get("evidence_refs")
        if not isinstance(refs, list):
            refs = []
        try:
            confidence = min(1.0, max(0.0, float(item.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        parsed[index] = {
            "verdict": verdict,
            "evidence_refs": [str(ref) for ref in refs
                              if isinstance(ref, (str, int))],
            "rationale": str(item.get("rationale", "")).strip(),
            "confidence": confidence,
        }
    return parsed or None


def _judge_chunk(prompt: str,
                 n_claims: int) -> tuple[dict[int, dict] | None, str]:
    """One cached LLM call, one stricter retry; failures are reported."""
    note = ""
    for suffix in ("", _RETRY_SUFFIX):
        try:
            payload = _call_llm(prompt + suffix)
        except Exception as exc:  # retried once, then NIE; never silent
            note = f"{type(exc).__name__}: {exc}"
            continue
        entries = _parse_entries(payload, n_claims)
        if entries is not None:
            return entries, note
        note = "LLM输出无法解析为按claim_id索引的JSON"
    return None, note


def _map_evidence_refs(raw_refs: list[str],
                       selected: list[EvidenceStatement],
                       statement_ids: dict[str, str],
                       evidence_ids: frozenset[str]) -> tuple[str, ...]:
    """Map ev-N / statement_id / evidence_id refs to real evidence ids."""
    mapped: set[str] = set()
    for ref in raw_refs:
        text = str(ref).strip()
        if text in evidence_ids:
            mapped.add(text)
            continue
        if text in statement_ids:
            mapped.add(statement_ids[text])
            continue
        match = re.fullmatch(r"(?:ev[-_ ]?)?(\d+)", text, re.IGNORECASE)
        if match:
            index = int(match.group(1))
            if 1 <= index <= len(selected):
                mapped.add(selected[index - 1].evidence_id)
    return tuple(sorted(mapped))


def _build_results(chunk: list[ClaimResult],
                   entries: dict[int, dict] | None,
                   selected: list[EvidenceStatement],
                   evidence_ids: frozenset[str],
                   refute_gate: float,
                   failure_note: str) -> list[ClaimResult]:
    statement_ids = {s.statement_id: s.evidence_id for s in selected}
    results: list[ClaimResult] = []
    for index, residual in enumerate(chunk):
        if entries is None:
            results.append(ClaimResult(
                claim_id=residual.claim_id,
                claim_text=residual.claim_text,
                verdict="not_in_evidence",
                check_item_candidates=residual.check_item_candidates,
                evidence_refs=(),
                rationale=(f"LLM残差通道失败(重试1次后保守NIE)：{failure_note}"),
                method="llm_residual_failed",
                confidence=0.0,
            ))
            continue
        if index not in entries:
            results.append(ClaimResult(
                claim_id=residual.claim_id,
                claim_text=residual.claim_text,
                verdict="not_in_evidence",
                check_item_candidates=residual.check_item_candidates,
                evidence_refs=(),
                rationale="LLM输出未覆盖该声明，保守NIE",
                method="llm_residual",
                confidence=0.0,
            ))
            continue
        entry = entries[index]
        verdict = entry["verdict"]
        refs = _map_evidence_refs(entry["evidence_refs"], selected,
                                  statement_ids, evidence_ids)
        notes: list[str] = []
        if verdict in ("support", "refute") and not refs:
            notes.append("未引用有效证据编号，降级为not_in_evidence")
            verdict = "not_in_evidence"
        if verdict == "refute" and entry["confidence"] < refute_gate:
            notes.append(
                f"confidence {entry['confidence']:.2f}低于refute门控"
                f"{refute_gate:.2f}，保守降级为not_in_evidence")
            verdict = "not_in_evidence"
        rationale = "LLM残差判定：" + (entry["rationale"] or "无理由")
        if notes:
            rationale += "（" + "；".join(notes) + "）"
        results.append(ClaimResult(
            claim_id=residual.claim_id,
            claim_text=residual.claim_text,
            verdict=verdict,
            check_item_candidates=residual.check_item_candidates,
            evidence_refs=refs,
            rationale=rationale,
            method="llm_residual",
            confidence=entry["confidence"],
        ))
    return results


def verify_residual_claims(
    request: QAInput,
    residual_results: list[ClaimResult],
    statements: list[EvidenceStatement],
    *,
    refute_gate: float = REFUTE_CONFIDENCE_GATE,
) -> list[ClaimResult]:
    """Judge the residual claims with one batched, cached LLM call.

    Only unresolved claims (method semantic_unresolved/conservative_unresolved
    with NIE verdicts) belong in ``residual_results`` — the C1 residual
    principle: L0/L1-decided claims never enter the LLM. The S5 cascade also
    routes L2 NLI refute candidates here for an L3 re-check (escalated
    ``nli_residual`` ClaimResults): only claim ids/texts are read, so the
    escalated claims reuse the same batched prompt path. Returned results
    reuse the residual claim ids and claim texts, so the caller's per-claim
    fusion lets an LLM support/refute replace the unresolved NIE.
    """
    if not residual_results or not statements:
        return []
    unique: list[ClaimResult] = []
    seen: set[str] = set()
    for result in residual_results:
        key = _compact(result.claim_text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    evidence_ids = frozenset(ev.evidence_id for ev in request.evidence)
    results: list[ClaimResult] = []
    for start in range(0, len(unique), _CLAIM_CHUNK):
        chunk = unique[start:start + _CLAIM_CHUNK]
        selected = _select_statements("".join(c.claim_text for c in chunk),
                                      statements)
        prompt = _build_prompt(request.question, chunk, selected)
        entries, note = _judge_chunk(prompt, len(chunk))
        results.extend(_build_results(chunk, entries, selected, evidence_ids,
                                      refute_gate, note))
    return results


__all__ = ["RESIDUAL_METHODS", "REFUTE_CONFIDENCE_GATE", "verify_residual_claims"]
