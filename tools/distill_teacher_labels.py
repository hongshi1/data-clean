"""Distillation teacher labeling (offline, training-time only).

Runs the deterministic fast tier on each corpus instance, extracts the
residual claims, rebuilds the pre-M66 L3 prompt byte-for-byte (vendored
from algorithms/consistency/llm_residual.py @ fab50c40^) and asks the
GLM-5.3 teacher for claim-level three-way verdicts — hitting the
historical disk cache wherever the same prompt ran before (zero new API
calls for the 91QA corpus).

For each labeled claim the record also stores the student-side premise
(algorithms.consistency.nli_training.residual_premise — the exact input
the local NLI channel sees at inference) plus a coverage flag: whether
the teacher's cited statements appear in that premise.

Output: data/gjb_438c/distillation/teacher_labels_v1.jsonl
  {corpus, instance_id, split, claim_id, claim_text, premise,
   teacher_verdict, teacher_confidence, teacher_refs, teacher_rationale,
   premise_covered, cache_hit, ts}

Training-time tool only — never imported by algorithms/.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from algorithms.consistency.eval_lib import build_qa_input, load_frozen_qa
from algorithms.consistency.nli_training import residual_premise
from algorithms.consistency.qa_module import QAConsistencyModule
from algorithms.consistency.evidence_statements import (
    linearize_context,
)
from tools.llm_teacher import llm_json_teacher

# ═══════════════════════════════════════════════════════════════
# Vendored pre-M66 L3 prompt construction (byte-identical, cache keys
# depend on it) — from algorithms/consistency/llm_residual.py
# ═══════════════════════════════════════════════════════════════

_STATEMENT_CAP = 60
_STATEMENT_TRUNC = 160
_CLAIM_CHUNK = 10

_SYSTEM = (
    "你是GJB军事软件需求文档的一致性审查员。给定证据语句列表，判定answer声明属于哪种："
    "support（证据明确支持）/refute（证据明确矛盾）/not_in_evidence（证据无法判定）。"
    "判定规则："
    "1.开放世界：证据中没有≠文档中不存在。缺失的内容（子功能名、前置条件、"
    "效果性表述、解释性扩展）只能判not_in_evidence，绝不能作为refute的依据。"
    "2.锚定：把声明主体锚定到问题所点名对象的具体功能行/用例行"
    "（如问题问“对BLOB数据进行X操作的功能”，锚定BLOB数据操作行——按问题主体"
    "的对象名锚定，而不是按操作名去找名称相似的另一功能行）。"
    "只有锚定行自身的值与声明冲突才refute。设备/方式名称列是精确集合："
    "同一功能的设备集合不同（如多出或缺少'手持'）→refute；参数值、标识符、"
    "产物类型不同→refute（'数据对象'与'目标语言代码'是不同产物）。"
    "上层功能的概括描述与其子功能行的值冲突时，以子功能行为准。"
    "全称断言（所有…都）被具体反例直接矛盾→refute。"
    "把主体换成另一个用例/功能行后发现的差异、或证据中没有主体自身的行"
    "（例如该用例的前置条件行不存在），都不是矛盾→not_in_evidence。"
    "3.值判定：answer真正断言的是值（沿用哪些设备、适用哪些阶段、包括哪些操作、"
    "产物是什么），不是问题中已点名对象的存在性。锚定行的对应值与声明一致→"
    "support；锚定行给出不同的值→refute；锚定行没有该值→not_in_evidence。"
    "问题点名的子功能名未在锚定行逐字出现不阻止support"
    "（功能'包括'列表是非穷尽的，近义子操作视为同一：修改≈更新/删除记录、"
    "添加≈插入）；声明点名的接口/用例名称未在证据中逐字出现→"
    "（问题预设的主体名除外）→not_in_evidence。"
    "4.解释/效果性扩展（'这意味着''包括但不限于''确保/保证/提高/优化/便于'"
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

_EXTRA_PAYLOAD = {
    "response_contract": "json_final_content_v2",
    "reasoning_effort": "low",
}
_VERDICTS = ("support", "refute", "not_in_evidence")


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _bigrams(text: str) -> frozenset[str]:
    return frozenset(text[i:i + 2] for i in range(len(text) - 1))


def _dedupe_statements(statements):
    seen: set[str] = set()
    unique = []
    for statement in statements:
        key = _compact(statement.text)
        if key and key not in seen:
            seen.add(key)
            unique.append(statement)
    return unique


def _select_statements(claims_text: str, statements):
    """Pick ≤30 statements, grouped by logical table row (vendored L3)."""
    joint = _compact(claims_text)
    claim_grams = _bigrams(joint)
    rows: dict[tuple[str, int], list] = {}
    order: list[tuple[str, int]] = []
    position: dict[tuple[str, int], int] = {}
    for statement in _dedupe_statements(statements):
        key = (statement.evidence_id, statement.row_index)
        if key not in rows:
            position[key] = len(order)
            order.append(key)
        rows.setdefault(key, []).append(statement)

    def row_rank(key):
        row = rows[key]
        scope = 0 if any(s.scope_key and s.scope_key in joint
                         for s in row) else 1
        subject = _compact((row[0].scope_key or "") + row[0].text)
        subject_overlap = len(_bigrams(subject) & claim_grams)
        union_overlap = len(
            set().union(*(_bigrams(_compact(s.text)) & claim_grams
                          for s in row)))
        return (scope, -subject_overlap, -union_overlap, position[key])

    selected = []
    for key in sorted(order, key=row_rank):
        if len(selected) >= _STATEMENT_CAP:
            break
        selected.extend(rows[key])
    return selected[:_STATEMENT_CAP]


def _build_prompt(question: str, claims, statements) -> str:
    lines = [f"【问题】{question}", "", "【待判定声明】（对每条独立判定）"]
    lines += [f"c{i}: {claim.claim_text}"
              for i, claim in enumerate(claims, 1)]
    lines += ["", "（声明是对answer的分解；问题中已点名的功能/对象是存在性预设，"
              "answer断言的是它们的值——设备、阶段、参数、产物。）"]
    lines += ["", "【证据语句】"]
    for i, statement in enumerate(statements, 1):
        text = re.sub(r"\s+", " ", statement.text).strip()
        lines.append(f"ev-{i}: {text[:_STATEMENT_TRUNC]}")
    lines += ["", _JSON_SPEC]
    return "\n".join(lines)


def _parse_entries(payload: dict, n_claims: int):
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
        if verdict not in _VERDICTS:
            verdict = "not_in_evidence"
        refs = item.get("evidence_refs")
        if not isinstance(refs, list):
            refs = []
        try:
            confidence = min(1.0, max(0.0,
                                      float(item.get("confidence", 0.0))))
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


# ═══════════════════════════════════════════════════════════════
# Corpus loading
# ═══════════════════════════════════════════════════════════════

BASE = Path(__file__).resolve().parents[1]
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
OUT_DIR = BASE / "data/gjb_438c/distillation"


def load_corpora() -> list[tuple[str, str, dict]]:
    """(corpus, split, record) triples; split∈dev/test/train_only."""
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    out: list[tuple[str, str, dict]] = []
    for rec in load_frozen_qa():
        iid = rec["instance_id"]
        out.append(("qa91", "dev" if iid in dev_ids else "test", rec))
    vio_path = (BASE / "data/gjb_438c/localization_gold"
                / "violation_evalset_v1.jsonl")
    for line in vio_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(("violations", "train_only", json.loads(line)))
    for doc in ("05", "06", "07", "08", "10"):
        cd = (BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}"
              f"_evalset_v1.jsonl")
        for line in cd.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(("crossdoc", "train_only", json.loads(line)))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpora", nargs="*",
                        default=["qa91"],
                        help="qa91 / violations / crossdoc")
    parser.add_argument("--out", default="teacher_labels_v1.jsonl")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / args.out
    mod = QAConsistencyModule(use_experts=True)

    n_hit = n_miss = 0
    n_claims = 0
    verdict_counts: dict[str, int] = {}
    coverage_hit = coverage_total = 0
    t0 = time.time()

    with open(out_path, "w", encoding="utf-8") as fout:
        for corpus, split_tag, rec in load_corpora():
            if corpus not in args.corpora:
                continue
            req = build_qa_input(rec)
            res = mod.verify(req)
            residual = [r for r in res.claim_results
                        if r.method in ("semantic_unresolved",
                                        "conservative_unresolved")]
            if not residual or not req.evidence:
                continue
            statements = linearize_context(req.evidence)
            if not statements:
                continue
            # dedupe residual by compact claim text (as old L3 did)
            unique: list = []
            seen: set[str] = set()
            for r in residual:
                key = _compact(r.claim_text)
                if key and key not in seen:
                    seen.add(key)
                    unique.append(r)
            for start in range(0, len(unique), _CLAIM_CHUNK):
                chunk = unique[start:start + _CLAIM_CHUNK]
                selected = _select_statements(
                    "".join(c.claim_text for c in chunk), statements)
                prompt = _build_prompt(req.question, chunk, selected)
                entries = None
                cache_hit = False
                for suffix in ("", _RETRY_SUFFIX):
                    payload, _model, hit = llm_json_teacher(
                        prompt + suffix, _SYSTEM,
                        max_tokens=16000, temperature=0.1,
                        extra_payload=_EXTRA_PAYLOAD)
                    if hit:
                        n_hit += 1
                        cache_hit = True
                    else:
                        n_miss += 1
                    entries = _parse_entries(payload, len(chunk))
                    if entries is not None:
                        break
                if entries is None:
                    continue  # unparseable even after retry; skip claims
                for index, claim in enumerate(chunk):
                    entry = entries.get(index)
                    if entry is None:
                        continue
                    verdict = entry["verdict"]
                    # premise exactly as the student NLI channel builds it
                    premise, picks = residual_premise(
                        claim.claim_text, req.question, statements)
                    pick_texts = {_compact(text) for _, text in picks}
                    ref_texts: set[str] = set()
                    for ref in entry["evidence_refs"]:
                        m = re.fullmatch(r"(?:ev[-_ ]?)?(\d+)",
                                         str(ref).strip(), re.IGNORECASE)
                        if m and 1 <= int(m.group(1)) <= len(selected):
                            ref_texts.add(
                                _compact(selected[int(m.group(1)) - 1].text))
                    covered = (not ref_texts) or bool(ref_texts & pick_texts)
                    if verdict in ("support", "refute"):
                        coverage_total += 1
                        if covered:
                            coverage_hit += 1
                    n_claims += 1
                    verdict_counts[verdict] = (
                        verdict_counts.get(verdict, 0) + 1)
                    fout.write(json.dumps({
                        "corpus": corpus,
                        "instance_id": rec["instance_id"],
                        "split": split_tag,
                        "claim_id": claim.claim_id,
                        "claim_text": claim.claim_text,
                        "premise": premise,
                        "teacher_verdict": verdict,
                        "teacher_confidence": entry["confidence"],
                        "teacher_refs": entry["evidence_refs"],
                        "teacher_rationale": entry["rationale"],
                        "premise_covered": covered,
                        "cache_hit": cache_hit,
                        "ts": round(time.time(), 1),
                    }, ensure_ascii=False) + "\n")
                    fout.flush()

    print(f"claims labeled: {n_claims}")
    print(f"verdicts: {verdict_counts}")
    print(f"cache: hit={n_hit} miss={n_miss} "
          f"({n_hit / max(1, n_hit + n_miss) * 100:.0f}% hit)")
    print(f"premise coverage (support/refute): "
          f"{coverage_hit}/{coverage_total}")
    print(f"elapsed: {time.time() - t0:.0f}s → {out_path}")


if __name__ == "__main__":
    main()
