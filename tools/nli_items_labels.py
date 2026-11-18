"""NLI级条目开发: D3教师标注升级为结构化解释协议(v2格式).

按调研(场景一可解释性2024-2026)落地:
  1. 三态细分: CONTRADICTED/UNSUPPORTED/INCOMPLETE(NIE拆开)
  2. RLSeek硬约束: 判CONTRADICTED必须携带evidence_quote
     (证据侧逐字引用), 无quote自动降级UNSUPPORTED
  3. NLI级条目: difference_type对齐knowledge/nli_difference_
     taxonomy.json的13条语义差异条目
  4. 结构化解释协议: claim_span+evidence_span+difference_type+
     missing_condition+reason

试点语料: violations-17(构造category做根因gold)+dev-45.
产物: data/gjb_438c/distillation/nli_items_labels_v1.jsonl
用法: $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
      python tools/nli_items_labels.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    load_frozen_qa,
    read_jsonl,
)
from tools.llm_teacher import llm_json_teacher  # noqa: E402

SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
OUT = BASE / "data/gjb_438c/distillation/nli_items_labels_v1.jsonl"

_TAX = json.loads(
    (BASE / "knowledge/nli_difference_taxonomy.json")
    .read_text(encoding="utf-8"))["items"]
_DIFF_LIST = "；".join(f"{it['difference_type']}={it['name']}"
                       for it in _TAX)
_DIFF_IDS = {str(it["difference_type"]) for it in _TAX}

_SYSTEM = (
    "你是GJB军事软件需求文档的一致性校验员。给定问题、待校验answer和全部证据，"
    "按结构化协议输出判定与定位。\n"
    "【三态(严格区分, 不可混用)】\n"
    "CONTRADICTED: 存在可定位反证——必须有evidence_quote(证据原文逐字引用),"
    "无quote不得判此态\n"
    "UNSUPPORTED: 当前证据不能证明该声明(证据缺失≠矛盾, 开放世界: 证据中没有"
    "≠文档中不存在)\n"
    "INCOMPLETE: answer遗漏了question明确要求的必要信息, 但已答部分无错误事实\n"
    "【判定规则】\n"
    "1.锚定: 把answer断言锚定到question点名对象的具体功能行/用例行, 只有锚定行"
    "自身的值与断言冲突才CONTRADICTED\n"
    "2.值判定: answer断言的是值(参数/设备/阶段/标识符/产物/条件), 锚定行一致→"
    "标注各断言为verified; 不同值→CONTRADICTED; 没有该值→UNSUPPORTED\n"
    "3.解释性扩展('这意味着''包括但不限于''确保')本身无证据→UNSUPPORTED\n"
    "4.拿不准一律UNSUPPORTED\n"
    "【difference_type(仅CONTRADICTED的finding需要, 从13条NLI条目中选)】\n"
    f"{_DIFF_LIST}\n"
    "【quote硬约束】claim_quote必须逐字取自answer; evidence_quote必须逐字取自"
    "证据语句。改写/拼接的quote视为无效。\n"
    "证据可能含HTML表格, 字段标签可能错位, 以内容为准。只输出JSON。"
)
_SPEC = (
    '输出JSON：{"verdict": "CONTRADICTED|UNSUPPORTED|INCOMPLETE", '
    '"findings": [{"claim_quote": "answer原文片段(逐字)", '
    '"claim_span": [起,止], '
    '"evidence_quote": "证据原文片段(逐字, CONTRADICTED必填)", '
    '"evidence_ref": "ev-N", '
    '"difference_type": "precondition_weakening等13条之一", '
    '"missing_condition": "被遗漏/错配的具体条件(条件类差异时填)", '
    '"reason": "一句话: answer声称X, 证据ev-N规定Y, 差异是Z"}]}; '
    "UNSUPPORTED/INCOMPLETE时findings为[]。"
)
_RETRY = ("\n\n上一次输出无法解析。只输出一个JSON对象。quote必须逐字。"
          "CONTRADICTED必须有evidence_quote。")


def _build_prompt(question: str, answer: str, evidences) -> str:
    lines = [f"【问题】{question}", "", "【待校验answer】", answer, "",
             "【证据】"]
    for index, ev in enumerate(evidences, 1):
        text = re.sub(r"\s+", " ", str(ev)).strip()
        lines.append(f"ev-{index}: {text[:700]}")
    lines += ["", _SPEC]
    return "\n".join(lines)


def _validate_quotes(answer: str, evidences: list[str],
                     finding: dict) -> dict:
    """quote后验校验: claim逐字于answer, evidence逐字于证据."""
    claim = str(finding.get("claim_quote", ""))
    claim_ok = bool(claim) and claim in answer
    ev_quote = str(finding.get("evidence_quote", ""))
    ev_ok = bool(ev_quote) and any(
        ev_quote[:40] in ev or ev_quote in ev for ev in evidences)
    finding["claim_quote_verified"] = claim_ok
    finding["evidence_quote_verified"] = ev_ok
    if not ev_ok:
        finding["downgraded"] = "UNSUPPORTED(证据quote无效)"
    return finding


def _normalize(answer: str, evidences: list[str],
               payload: dict) -> dict:
    verdict = re.sub(r"\s+", "_",
                     str(payload.get("verdict", ""))).strip().upper()
    if verdict not in ("CONTRADICTED", "UNSUPPORTED", "INCOMPLETE"):
        verdict = "UNSUPPORTED"
    findings = []
    raw = payload.get("findings")
    if verdict == "CONTRADICTED" and isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            claim = str(item.get("claim_quote", "")).strip()
            ev_quote = str(item.get("evidence_quote", "")).strip()
            if not claim:
                continue
            diff = str(item.get("difference_type", "")).strip()
            if diff not in _DIFF_IDS:
                diff = "value_substitution"
            finding = {
                "claim_quote": claim,
                "claim_span": item.get("claim_span"),
                "evidence_quote": ev_quote,
                "evidence_ref": str(item.get("evidence_ref", "")),
                "difference_type": diff,
                "missing_condition": str(
                    item.get("missing_condition", ""))[:100],
                "reason": str(item.get("reason", ""))[:200],
            }
            findings.append(_validate_quotes(
                answer, evidences, finding))
    # 硬约束: 无有效evidence_quote的CONTRADICTED降级
    if verdict == "CONTRADICTED" and not any(
            f.get("evidence_quote_verified") for f in findings):
        verdict = "UNSUPPORTED"
    return {"verdict": verdict, "findings": findings}


def label_one(rec: dict, corpus: str) -> dict | None:
    request = build_qa_input(rec)
    evidences = [ev.text for ev in request.evidence]
    answer = str(request.answer)
    prompt = _build_prompt(request.question, answer, evidences)
    for suffix in ("", _RETRY):
        try:
            payload, _model, _hit = llm_json_teacher(
                prompt + suffix, _SYSTEM,
                max_tokens=16000, temperature=0.1,
                extra_payload={"response_contract": "json_final_content_v2",
                               "reasoning_effort": "low"})
        except (RuntimeError, OSError) as exc:
            print(f"  ERROR {rec['instance_id']}: {exc}", flush=True)
            return None
        if str(payload.get("verdict", "")):
            normalized = _normalize(answer, evidences, payload)
            return {
                "corpus": corpus,
                "instance_id": str(rec["instance_id"]),
                "question": str(request.question),
                "answer": answer,
                "evidence": [str(ev)[:700] for ev in evidences],
                "verdict": normalized["verdict"],
                "findings": normalized["findings"],
                "orig_label": str(rec.get("expected_verdict",
                                           rec.get("sound_label", ""))),
            }
    return None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    corpora: list[tuple[str, list[dict]]] = [
        ("violations", read_jsonl(VIO)),
        ("qa91-dev", [r for r in load_frozen_qa()
                      if r["instance_id"] in dev_ids]),
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    done_ids: set[str] = set()
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done_ids.add(json.loads(line)["instance_id"])
    n_new = 0
    started = time.time()
    with open(OUT, "a", encoding="utf-8") as fout:
        for corpus, records in corpora:
            for rec in records:
                if str(rec["instance_id"]) in done_ids:
                    continue
                if args.limit and n_new >= args.limit:
                    return
                row = label_one(rec, corpus)
                if row is None:
                    continue
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                fout.flush()
                n_new += 1
                n_ev_ok = sum(1 for f in row["findings"]
                              if f.get("evidence_quote_verified"))
                print(f"[{corpus}] {row['instance_id']} "
                      f"{row['verdict']:14s} "
                      f"findings={len(row['findings'])}"
                      f"(ev_quote✓{n_ev_ok}) "
                      f"({time.time() - started:.0f}s)", flush=True)
    print(f"新增{n_new} → {OUT}")


if __name__ == "__main__":
    main()
