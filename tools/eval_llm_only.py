"""LLM-only判决性实验: 本地qwen3:8b直推 vs 启发式脚手架.

回答"脚手架是否过拟合保险": 同一prompt(旧B2直推协议)、同一冻结
证据, 模型=本地Ollama qwen3:8b(推理零API合规). 对照:
  - 脚手架(distilled_v1管线): test46 mF1 0.8047 / violations 16/17
  - GLM-5.3直推(API参考): 全91 0.6105(B2, 不可直接比但量级参考)
  - 本地LLM直推: 本实验

响应磁盘缓存(data/gjb_438c/llm_cache_qwen/)保证可复现.
Ollama: http://localhost:11434, /api/chat, qwen3:8b(关thinking
加速; 失败回退generate).

用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
  python tools/eval_llm_only.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
CACHE = BASE / "data/gjb_438c/llm_cache_qwen/direct_v1.jsonl"
OLLAMA = "http://localhost:11434"
LABELS = ("support", "refute", "not_in_evidence")

_SYSTEM = (
    "你是GJB军事软件需求文档的一致性审查员。给定问题、待判定answer和全部证据，"
    "判定answer属于哪种：support（证据明确支持）/refute（证据明确矛盾）/"
    "not_in_evidence（证据无法判定）。判定规则："
    "1.开放世界：证据中没有≠文档中不存在。缺失的内容（子功能名、前置条件、"
    "效果性表述、解释性扩展）只能判not_in_evidence，绝不能作为refute的依据。"
    "2.锚定：把answer断言锚定到问题所点名对象的具体功能行/用例行，只有锚定行"
    "自身的值与answer断言冲突才refute；把主体换成另一个用例/功能行后发现的差异"
    "不是矛盾。"
    "3.值判定：answer真正断言的是值（参数、设备、阶段、标识符、产物）。"
    "锚定行的对应值与answer一致→support；给出不同的值→refute；"
    "没有该值→not_in_evidence。"
    "4.answer中的解释/效果性扩展（'这意味着''包括但不限于''确保/便于'引出的"
    "内容）本身无证据时判not_in_evidence。"
    "5.拿不准时一律判not_in_evidence。"
    "证据可能包含HTML表格，字段标签可能错位，判定以内容为准。只输出JSON。"
)
_SPEC = (
    '输出JSON：{"verdict": "support|refute|not_in_evidence", '
    '"evidence_refs": ["ev-1"], "rationale": "一句话理由", '
    '"confidence": 0.9}；support/refute必须在evidence_refs中引用证据编号，'
    "not_in_evidence时evidence_refs为[]。"
)
_RETRY = ("\n\n上一次输出无法解析。请严格只输出一个JSON对象，"
          "不要markdown代码块、不要任何多余文字。")

_cache: dict[str, str] | None = None


def _load_cache() -> dict[str, str]:
    global _cache
    if _cache is None:
        _cache = {}
        if CACHE.exists():
            for line in CACHE.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                    _cache[rec["k"]] = rec["content"]
                except (json.JSONDecodeError, KeyError):
                    continue
    return _cache


def _store(key: str, content: str) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"k": key, "content": content},
                           ensure_ascii=False) + "\n")
    _load_cache()[key] = content


def _call_qwen(prompt: str) -> str:
    body = json.dumps({
        "model": "qwen3:8b",
        "messages": [{"role": "system", "content": _SYSTEM},
                     {"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048},
        "think": False,
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA}/api/chat", data=body,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read())
    return str(payload.get("message", {}).get("content", ""))


def _parse_json(content: str) -> dict:
    try:
        value = json.loads(content)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.S)
        candidate = fenced.group(1) if fenced else content
        decoder = json.JSONDecoder()
        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                value, _end = decoder.raw_decode(candidate[index:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                pass
    return {}


def _build_prompt(question: str, answer: str, evidences) -> str:
    lines = [f"【问题】{question}", "", "【待判定answer】",
             str(answer).strip(), "", "【证据】"]
    for index, ev in enumerate(evidences, 1):
        text = re.sub(r"\s+", " ", str(ev["text"])).strip()
        lines.append(f"ev-{index}: {text}")
    lines += ["", _SPEC]
    return "\n".join(lines)


def judge(row: dict) -> str:
    request = build_qa_input(row)
    prompt = _build_prompt(request.question, request.answer,
                           [e.__dict__ for e in request.evidence]
                           if hasattr(request.evidence[0], "__dict__")
                           else [e for e in request.evidence])
    key = re.sub(r"\s+", "", prompt)[:80] + f"#{len(prompt)}"
    cached = _load_cache().get(key)
    if cached is not None:
        payload = _parse_json(cached)
    else:
        content = ""
        for suffix in ("", _RETRY):
            content = _call_qwen(prompt + suffix)
            payload = _parse_json(content)
            if payload.get("verdict"):
                break
        _store(key, content)
    verdict = re.sub(r"\s+", "_",
                     str(payload.get("verdict", ""))).strip().lower()
    return verdict if verdict in LABELS else "not_in_evidence"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    silver = load_silver_labels(SILVER)
    qa = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    dev_ids = set(split["dev"])
    test = [r for r in qa if r["instance_id"] not in dev_ids]
    if args.limit:
        test = test[:args.limit]
    vio = [json.loads(line) for line in
           VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        vio = vio[:args.limit]

    y_true: list[str] = []
    y_pred: list[str] = []
    started = time.time()
    for i, rec in enumerate(test, 1):
        verdict = judge(rec)
        y_true.append(silver.get(rec["instance_id"], "not_in_evidence"))
        y_pred.append(verdict)
        if i % 5 == 0:
            print(f"  test46 {i}/{len(test)} "
                  f"({time.time() - started:.0f}s)", flush=True)
    m = classification_metrics(y_true, y_pred)
    print(f"[test46] acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
          f"(n={len(y_pred)})")
    for cls, pm in m["per_class"].items():
        print(f"    {cls}: F1={pm['f1']:.3f}")

    y_true_v: list[str] = []
    y_pred_v: list[str] = []
    for rec in vio:
        y_true_v.append(str(rec["expected_verdict"]))
        y_pred_v.append(judge(rec))
    m_v = classification_metrics(y_true_v, y_pred_v)
    print(f"[violations17] acc={m_v['accuracy']:.4f} "
          f"refute检出={sum(1 for a, b in zip(y_true_v, y_pred_v) if a == b)}/17")
    out = {"test46": m, "violations17": m_v,
           "model": "qwen3:8b", "protocol": "B2-direct (cached)"}
    (BASE / "data/gjb_438c/distillation/llm_only_v1.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
