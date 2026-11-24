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
_ADAPTER = str(BASE / "models/llm/d3_student_v1")
#: X1约束解码总开关(main的--constrained置True; judge缺省走False)
_CONSTRAINED = False


def _load():
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return _MODEL, _TOKENIZER
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    _TOKENIZER = AutoTokenizer.from_pretrained(
        str(BASE / "models/llm/qwen3-1.7b"))
    adapter_path = BASE / _ADAPTER
    if (adapter_path / "adapter_config.json").exists():
        from peft import PeftModel
        base_model = AutoModelForCausalLM.from_pretrained(
            str(BASE / "models/llm/qwen3-1.7b"), torch_dtype=torch.float16)
        _MODEL = PeftModel.from_pretrained(base_model, str(adapter_path))
        _MODEL = _MODEL.merge_and_unload()
    else:
        # 已合并的完整模型(如OOM抢救产物)
        _MODEL = AutoModelForCausalLM.from_pretrained(
            str(adapter_path), torch_dtype=torch.float16)
    if torch.cuda.is_available():
        _MODEL.to("cuda")
    _MODEL.eval()
    return _MODEL, _TOKENIZER


def _user_message(question: str, answer: str, evidences,
                  evidence_budget: int = 1200) -> str:
    lines = [f"【问题】{question}", "", "【待校验answer】", answer, "",
             "【证据】"]
    used = 0
    for index, text in enumerate(evidences, 1):
        cleaned = re.sub(r"\s+", " ", str(text)).strip()
        if used >= evidence_budget:
            break
        remaining = evidence_budget - used
        if len(cleaned) > remaining:
            cleaned = cleaned[:remaining]
        used += len(cleaned)
        lines.append(f"ev-{index}: {cleaned}")
    lines += ["", _SPEC]
    return "\n".join(lines)


def _parse(content: str, trace: dict | None = None) -> dict:
    """三级JSON抢救(direct→fenced→raw_decode扫描), 失败返回{}.

    trace非None时记录实际走到的抢救层级(X1 Step A的parse_fail计量,
    不改变任何返回值): direct/think_stripped(取决于think剥离)/
    fenced/raw_scan/parsed_non_dict/fail.
    """
    stage = "direct"
    think = re.search(r"<think>.*?</think>", content, re.S)
    if think:
        content = content.replace(think.group(0), "")
        stage = "think_stripped"
    try:
        value = json.loads(content.strip())
        if isinstance(value, dict):
            if trace is not None:
                trace["stage"] = stage
            return value
        if trace is not None:
            trace["stage"] = "parsed_non_dict"
        return {}
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
                    if trace is not None:
                        trace["stage"] = "fenced" if fenced else "raw_scan"
                    return value
            except json.JSONDecodeError:
                pass
    if trace is not None:
        trace["stage"] = "fail"
    return {}


#: judge逐调用trace(X1 Step A/C的parse_fail计量; 与instance按序配对)
JUDGE_TRACE: list[dict] = []


def judge(question: str, answer: str, evidences,
          constrained: bool | None = None,
          ) -> tuple[str, list[dict], float]:
    """贪心解码judge. 返回(verdict, issues, elapsed).

    constrained=True走X1约束解码(algorithms/consistency/
    d3_constrained.constrained_generate); 默认None取全局_CONSTRAINED
    (缺省False=既有无约束路径, 行为与返回值逐位不变).
    结构未完成时constrained路径返回空串verdict(显式无效,
    不默认NIE)——由X1评测按parse_fail行单独计量.
    """
    import torch
    use_constrained = _CONSTRAINED if constrained is None else constrained
    model, tokenizer = _load()
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": _user_message(
            question, answer, evidences)}]
    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False)
    trace: dict = {"constrained": bool(use_constrained)}
    if use_constrained:
        from algorithms.consistency.d3_constrained import (  # noqa: PLC0415
            constrained_generate)
        result = constrained_generate(
            model, tokenizer, prompt, str(answer), list(evidences))
        trace.update(
            stage="constrained",
            parse_fail=result["parse_fail"],
            constraint_log=result["constraint_log"],
            content_chars=len(result["content"]),
            content_head=result["content"][:80],
            verdict=result["verdict"] or "",
            n_issues=len(result["issues"]))
        JUDGE_TRACE.append(trace)
        return result["verdict"] or "", result["issues"], result["elapsed_s"]
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
    payload = _parse(content, trace)
    verdict = re.sub(r"\s+", "_",
                     str(payload.get("verdict", ""))).strip().lower()
    defaulted = verdict not in ("support", "refute", "not_in_evidence")
    if defaulted:
        verdict = "not_in_evidence"
    issues = payload.get("issues")
    issues_missing = not isinstance(issues, list)
    if issues_missing:
        issues = []
    trace.update(
        verdict_raw=str(payload.get("verdict", "")),
        verdict=verdict,
        verdict_defaulted=defaulted,
        issues_missing=issues_missing,
        n_issues=len(issues),
        content_chars=len(content),
        content_head=content[:80])
    JUDGE_TRACE.append(trace)
    return verdict, [i for i in issues if isinstance(i, dict)], elapsed


def _eval_corpus(records: list[dict], labels: dict[str, str],
                 tag: str) -> dict:
    y_true: list[str] = []
    y_pred: list[str] = []
    n_issues = 0
    n_span_ok = 0
    n_instances = 0
    n_parse_fail = 0
    latencies: list[float] = []
    sample_details: list[dict] = []
    for rec in records:
        answer = str(rec["answer"])
        evidences = [str(e["text"]) for e in rec["evidence"]]
        verdict, issues, elapsed = judge(
            str(rec["question"]), answer, evidences)
        latencies.append(elapsed)
        if verdict == "":
            # X1约束路径结构未完成(空串=显式无效, 不默认NIE):
            # 不进分类指标, 单独计数
            n_parse_fail += 1
            sample_details.append({
                "instance_id": str(rec["instance_id"]),
                "verdict": "", "n_issues": 0, "parse_fail": True})
            continue
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
        sample = {
            "instance_id": str(rec["instance_id"]),
            "verdict": verdict, "n_issues": len(issues)}
        if _CONSTRAINED:
            sample["parse_fail"] = False
        sample_details.append(sample)
    m = classification_metrics(y_true, y_pred)
    parse_note = f" parse_fail {n_parse_fail}/{len(records)}" \
        if n_parse_fail else ""
    print(f"[{tag}] acc={m['accuracy']:.4f} mF1={m['macro_f1']:.4f} "
          f"refuteF1={m['per_class'].get('refute', {}).get('f1', 0):.3f} "
          f"| issues实例 {n_instances}/{len(records)} "
          f"span忠实 {n_span_ok}/{n_issues} "
          f"| 延迟{sum(latencies) / max(1, len(latencies)):.1f}s/例"
          f"{parse_note}")
    out = {"metrics": m, "n_issues": n_issues,
           "span_faithful": n_span_ok, "samples": sample_details,
           "mean_latency_s": round(
               sum(latencies) / max(1, len(latencies)), 2)}
    if _CONSTRAINED:
        out["n_parse_fail"] = n_parse_fail
    return out


def _trace_summary() -> dict:
    """JUDGE_TRACE聚合(X1的parse_fail/约束干预统计; 供constrained模式)."""
    from collections import Counter
    stages = Counter(t.get("stage", "?") for t in JUDGE_TRACE)
    return {
        "n": len(JUDGE_TRACE),
        "stage_counts": dict(stages),
        "parse_fail": sum(bool(t.get("parse_fail")) for t in JUDGE_TRACE),
        "verdict_defaulted": sum(
            bool(t.get("verdict_defaulted")) for t in JUDGE_TRACE),
        "issues_missing": sum(
            bool(t.get("issues_missing")) for t in JUDGE_TRACE),
        "interventions": sum(
            (t.get("constraint_log") or {}).get("interventions", 0)
            for t in JUDGE_TRACE),
        "steps": sum((t.get("constraint_log") or {}).get("steps", 0)
                     for t in JUDGE_TRACE),
        "n_new_tokens": sum(
            (t.get("constraint_log") or {}).get("n_new_tokens", 0)
            for t in JUDGE_TRACE),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--adapter", default="models/llm/d3_student_v1")
    parser.add_argument("--constrained", action="store_true",
                        help="X1约束解码(algorithms/consistency/"
                             "d3_constrained); 输出改写"
                             "d3_student_eval_x1_constrained.json, "
                             "既有论文数字文件不动")
    args = parser.parse_args()

    global _ADAPTER, _CONSTRAINED
    _ADAPTER = str(BASE / args.adapter)
    _CONSTRAINED = bool(args.constrained)
    JUDGE_TRACE.clear()

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

    mode = "X1约束解码" if args.constrained else "无约束(既有路径)"
    print(f"student: Qwen3-1.7B + LoRA({args.adapter}) [{mode}]")
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
    out_path = OUT
    if args.constrained:
        result["constrained"] = True
        result["parse_trace"] = _trace_summary()
        out_path = (BASE / "data/gjb_438c/distillation"
                    / "d3_student_eval_x1_constrained.json")
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"→ {out_path}")


if __name__ == "__main__":
    main()
