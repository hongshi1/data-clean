r"""本地LLM基线: Qwen2.5-1.5B(base)生成式few-shot检测 — 纯本地替代GLM-5参考行.

用法: python tools/local_llm_baseline.py [bench|md|clean]
产出: data/gjb_438c/runs/local_llm_baseline.json (累积)
"""
from __future__ import annotations

import gc
import json
import random
import sys
from pathlib import Path

import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

MODEL_DIR = str(BASE / "models/nli/Qwen2.5-1.5B")
OUT = BASE / "data/gjb_438c/runs/local_llm_baseline.json"

FEWSHOT = """判断两段SRS需求陈述是否一致。规则: 参数数值/执行顺序/术语指代/组成范围矛盾, 或缺失关键内容 → 不一致; 画法粒度差异/异常流不上图等惯例 → 一致。

陈述1: 系统响应时间应不大于2s。
陈述2: 系统响应时间应不大于5s。
判断: 不一致

陈述1: 表格规定用例包含步骤「用户确认操作」。
陈述2: 流程图中没有与该步骤对应的节点。
判断: 一致

陈述1: 数据缓存周期为30s。
陈述2: 数据缓存周期为60s。
判断: 不一致

陈述1: 表格规定异常流E1「连接失败时提示用户」。
陈述2: 流程图中没有该异常分支。
判断: 一致

陈述1: {p}
陈述2: {h}
判断: """


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "bench"
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from run_benchmark_suite import prf, load_sample

    tok = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, local_files_only=True, torch_dtype=torch.bfloat16,
        device_map="auto")
    model.eval()

    def infer(pairs: list[tuple[str, str]], tok: object = tok, model: object = model) -> list[str]:
        preds = []
        for p, h in pairs:
            prompt = FEWSHOT.format(p=p[:150], h=h[:150])
            inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=900).to(model.device)
            with torch.no_grad():
                out = model.generate(**inputs, max_new_tokens=8, do_sample=False,
                                     pad_token_id=tok.eos_token_id)
            text = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            preds.append("inconsistent" if "不一致" in text else "consistent")
        return preds

    if which == "bench":
        data = load_sample("gjb_bench_test")
        random.Random(42).shuffle(data)
        data = data[:100]
        pairs = [(x["premise"], x["hypothesis"]) for x in data]
        ys = [x["label"] for x in data]
    elif which == "md":
        md = json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8"))
        random.Random(42).shuffle(md)
        data = md[:60]
        pairs = [(x["premise"], x["hypothesis"]) for x in data]
        ys = [x["label"] for x in data]
    elif which == "clean":
        cl = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
        random.Random(42).shuffle(cl)
        data = cl[:60]
        pairs = [(x["premise"], x["hypothesis"]) for x in data]
        ys = [x["label"] for x in data]
    else:
        raise SystemExit(f"未知: {which}")

    print(f"Qwen2.5-1.5B本地LLM @ {which}: {len(data)}条")
    preds = infer(pairs)
    m = prf(ys, preds)
    print(f"F1={m['F1']} P={m['P']} R={m['R']}")

    results = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    results[which] = {"n": len(data), "model": "Qwen2.5-1.5B-fewshot", **m}
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved → {OUT}")
    del model
    gc.collect()
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
