"""D3教师标注: GLM-5.3直产完整任务标签(不经脚手架claim管线).

教师输入 (Q, A, 证据ev-N) → 输出:
  {verdict, issues: [{quote(answer逐字引用), span[起,止],
    rule_id(40项taxonomy), evidence_ref(ev-N), explanation}]}

关键设计(回应"claim可能是错误的"):
  - 断言单元由教师自己分解(LLM原子化), quote必须逐字取自answer
  - span后验校验: answer[s:e]==quote, 否则find()定位, 再失败→
    span置null(quote保留, 标记不忠实)
  - rule_id对齐40项taxonomy(prompt内嵌条目表)
  - 训练语料: dev-45 + violations-17 + crossdoc-150 = 212
    (test-46保持held-out, D1/D2同一诚实契约)

产物: data/gjb_438c/distillation/d3_teacher_labels_v1.jsonl
用法: $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
      python tools/d3_teacher_labels.py [--limit N]
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
OUT = BASE / "data/gjb_438c/distillation/d3_teacher_labels_v1.jsonl"
VERDICTS = ("support", "refute", "not_in_evidence")

_TAX = json.loads(
    (BASE / "knowledge/consistency_taxonomy_v3.json")
    .read_text(encoding="utf-8"))["items"]
_TAX_LIST = "；".join(f"{it['id']}={it['name']}" for it in _TAX)
_TAX_IDS = {str(it["id"]) for it in _TAX}

_SYSTEM = (
    "你是GJB军事软件需求文档的一致性校验员。给定问题、待校验answer和全部证据，"
    "完成两件事：\n"
    "一、总体判定：support（证据明确支持）/refute（存在明确矛盾）/"
    "not_in_evidence（证据无法判定）。\n"
    "二、不一致定位（仅refute时）：把answer自己分解为原子断言，"
    "找出其中与证据矛盾的断言。\n"
    "判定规则：\n"
    "1.开放世界：证据中没有≠文档中不存在。缺失内容（子功能名、前置条件、"
    "效果性表述、解释性扩展）只能判not_in_evidence，不能作为refute依据。\n"
    "2.锚定：把断言锚定到问题点名对象的具体功能行/用例行，只有锚定行自身的"
    "值与断言冲突才refute。\n"
    "3.值判定：answer断言的是值（参数、设备、阶段、标识符、产物）。"
    "锚定行一致→support；不同值→refute；没有该值→not_in_evidence。\n"
    "4.拿不准一律not_in_evidence。\n"
    "5.issues里的quote必须逐字取自answer原文（不允许改写/拼接），"
    "span是quote在answer中的字符区间[start,end)。\n"
    "6.evidence_ref引用矛盾所在的证据编号ev-N。\n"
    "7.证据可能含HTML表格，字段标签可能错位，以内容为准。只输出JSON。"
)
_SPEC = (
    '输出JSON：{"verdict": "support|refute|not_in_evidence", '
    '"issues": [{"quote": "answer原文片段(逐字)", "span": [起始, 结束], '
    '"rule_id": "TERM-01等40项之一", "evidence_ref": "ev-1", '
    '"explanation": "一句话冲突说明"}]}；'
    f"rule_id只能取这40项之一：{_TAX_LIST}；"
    "not_in_evidence/support时issues为[]。"
)
_RETRY = ("\n\n上一次输出无法解析。请严格只输出一个JSON对象，"
          "不要markdown代码块。quote必须逐字取自answer。")


def _build_prompt(question: str, answer: str, evidences) -> str:
    lines = [f"【问题】{question}", "", "【待校验answer】", answer, "",
             "【证据】"]
    for index, ev in enumerate(evidences, 1):
        text = re.sub(r"\s+", " ", str(ev["text"])).strip()
        lines.append(f"ev-{index}: {text[:800]}")
    lines += ["", _SPEC]
    return "\n".join(lines)


def _validate_span(answer: str, issue: dict) -> dict:
    """span后验校验: 不忠实则find()修复, 再失败置null(标记)."""
    quote = str(issue.get("quote", ""))
    span = issue.get("span")
    ok = False
    if isinstance(span, list) and len(span) == 2:
        start, end = int(span[0]), int(span[1])
        ok = (0 <= start < end <= len(answer)
              and answer[start:end] == quote)
    if not ok and quote:
        pos = answer.find(quote)
        if pos >= 0:
            span = [pos, pos + len(quote)]
            ok = True
    issue["span"] = span if ok else None
    issue["span_verified"] = ok
    return issue


def _normalize_issues(answer: str, payload: dict) -> list[dict]:
    raw = payload.get("issues")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote", "")).strip()
        if not quote:
            continue
        rule_id = str(item.get("rule_id", "")).strip()
        if rule_id not in _TAX_IDS:
            matched = [t for t in _TAX_IDS if rule_id.startswith(t[:5])]
            rule_id = matched[0] if matched else "TERM-01"
        out.append(_validate_span(answer, {
            "quote": quote,
            "span": item.get("span"),
            "rule_id": rule_id,
            "evidence_ref": str(item.get("evidence_ref", "")),
            "explanation": str(item.get("explanation", ""))[:200],
        }))
    return out


def label_one(rec: dict, corpus: str) -> dict | None:
    request = build_qa_input(rec)
    evidences = [{"text": ev.text} for ev in request.evidence]
    prompt = _build_prompt(request.question, request.answer, evidences)
    answer = str(request.answer)
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
        verdict = re.sub(r"\s+", "_",
                         str(payload.get("verdict", ""))).strip().lower()
        if verdict in VERDICTS:
            return {
                "corpus": corpus,
                "instance_id": str(rec["instance_id"]),
                "question": str(request.question),
                "answer": answer,
                "evidence": [str(ev["text"])[:800] for ev in evidences],
                "verdict": verdict,
                "issues": _normalize_issues(answer, payload),
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
        ("qa91-dev", [r for r in load_frozen_qa()
                      if r["instance_id"] in dev_ids]),
        ("violations", read_jsonl(VIO)),
        ("d3train", read_jsonl(
            BASE / "data/gjb_438c/distillation"
            / "d3_train_instances_v1.jsonl")),
    ]
    for doc in ("05", "06", "07", "08", "10"):
        corpora.append(("crossdoc", read_jsonl(
            BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}"
            f"_evalset_v1.jsonl")))
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
                verified = sum(1 for i in row["issues"]
                               if i["span_verified"])
                print(f"[{corpus}] {row['instance_id']} "
                      f"{row['verdict']:16s} issues={len(row['issues'])} "
                      f"(span校验{verified}/{len(row['issues'])}) "
                      f"({time.time() - started:.0f}s)", flush=True)
    print(f"新增{n_new}条 → {OUT}")


if __name__ == "__main__":
    main()
