"""D3学生评测: test-46(held-out) + violations-17(训练集内参考).

生成配置与训练分布精确一致(enable_thinking=False的generation
prompt = 训练目标的assistant前缀). 指标:
  - verdict质量(test-46 vs silver): acc/mF1/refute F1
    对照: 脚手架0.8047 | qwen3:8b零样本0.2874 | GLM-5.3(API)0.8747
  - 定位质量: span校验率(quote逐字) + issues数
  - 延迟
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
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from tools.d3_teacher_labels import _SPEC, _SYSTEM  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
OUT = BASE / "data/gjb_438c/distillation/d3_student_eval_v1.json"

_MODEL = None
_TOKENIZER = None


def _load():
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return _MODEL, _TOKENIZER
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    _TOKENIZER = AutoTokenizer.from_pretrained(
        str(BASE / "models/llm/qwen3-1.7b"))
    base_model = AutoModelForCausalLM.from_pretrained(
        str(BASE / "models/llm/qwen3-1.7b"), torch_dtype=torch.float16)
    _MODEL = PeftModel.from_pretrained(
        base_model, str(BASE / "models/llm/d3_student_v1"))
    _MODEL = _MODEL.merge_and_unload()
    if torch.cuda.is_available():
        _MODEL.to("cuda")
    _MODEL.eval()
    return _MODEL, _TOKENIZER


def _user_message(question: str, answer: str, evidences) -> str:
    lines = [f"【问题】{question}", "", "【待校验answer】", answer, "",
             "【证据】"]
    for index, text in enumerate(evidences, 1):
        cleaned = re.sub(r"\s+", " ", str(text)).strip()
        lines.append(f"ev-{index}: {cleaned[:800]}")
    lines += ["", _SPEC]
    return "\n".join(lines)


def _parse(content: str) -> dict:
    think = re.search(r"<think>.*?</think>", content, re.S)
    if think:
        content = content.replace(think.group(0), "")
    try:
        value = json.loads(content.strip())
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


def judge(question: str, answer: str, evidences) -> tuple[str, list[dict]]:
    import torch
    model, tokenizer = _load()
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _user_message(
            question, answer, evidences)}]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False)
    inputs = tokenizer(prompt, return_tensors="pt",
                       add_special_tokens=False)
    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}
    start = time.perf_counter()
    with torch.no_grad():
        output = model.generate(
            **inputs, max_new_tokens=512, do_sample=False,
            temperature=None, top_p=None, top_k=None,
            pad_token_id=tokenizer.eos_token_id)
    elapsed = time.perf_counter() - start
    new_ids = output[0][inputs["input_ids"].shape[1]:]
    content = tokenizer.decode(new_ids, skip_special_tokens=True)
    payload = _parse(content)
    verdict = re.sub(r"\s+", "_",
                     str(payload.get("verdict", ""))).strip().lower()
    if verdict not in ("support", "refute", "not_in_evidence"):
        verdict = "not_in_evidence"
    issues = payload.get("issues")
    if not isinstance(issues, list):
        issues = []
    return verdict, [i for i in issues if isinstance(i, dict)], elapsed


def _eval_corpus(records: list[dict], labels: dict[str, str],
                 tag: str) -> dict:
    y_true: list[str] = []
    y_pred: list[str] = []
    n_issues = 0
    n_span_ok = 0
    n_instances = 0
    latencies: list[float] = []
    sample_details: list[dict] = []
    for rec in records:
        answer = str(rec["answer"])
        evidences = [str(e["text"]) for e in rec["evidence"]]
        verdict, issues, elapsed = judge(
            str(rec["question"]), answer, evidences)
        latencies.append(elapsed)
        y_true.append(labels.get(str(rec["instance_id"]),
                                 "not_in_evidence"))
        y_pred.append(verdict)
        if issues:
            n_instances += 1
        for issue in issues:
            quote = str(issue.get("quote", ""))
            span = issue.get("span")
            ok = False
            if isinstance(span, list) and len(span) == 2:
                start, end = int(span[0]), int(span[1])
                ok = 0 <= start < end <= len(answer) \
                    and answer[start:end] == quote
            if not ok and quote:
                ok = answer.find(quote) >= 0
            n_issues += 1
            n_span_ok += bool(ok)
        sample_details.append({
            "instance_id": str(rec["instance_id"]),
            "verdict": verdict, "n_issues": len(issues)})
    m = classification_metrics(y_true, y_pred)
    print(f"[{tag}] acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
          f"refuteF1={m['per_class'].get('refute', {}).get('f1', 0):.3f} "
          f"| issues实例 {n_instances}/{len(records)} "
          f"span忠实 {n_span_ok}/{n_issues} "
          f"| 延迟{sum(latencies) / max(1, len(latencies)):.1f}s/例")
    return {"metrics": m, "n_issues": n_issues,
            "span_faithful": n_span_ok, "samples": sample_details,
            "mean_latency_s": round(
                sum(latencies) / max(1, len(latencies)), 2)}


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

    print("student: Qwen3-1.7B + LoRA(models/llm/d3_student_v1)")
    result = {
        "test46": _eval_corpus(
            test, silver, "test46(诚实, 训练未见)"),
        "violations17": _eval_corpus(
            vio, {str(r["instance_id"]): str(r["expected_verdict"])
                  for r in vio}, "violations17(训练集内参考)"),
        "baselines": {"scaffold_distilled_v1": 0.8047,
                      "qwen3_8b_zeroshot": 0.2874,
                      "glm53_api_reference": 0.8747},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
