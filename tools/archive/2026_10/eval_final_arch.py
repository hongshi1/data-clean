"""最终架构评测: 前置Z3确定性求解 + 主路径v11(证据条件LoRA SFT).

架构: PARAM数值类→Z3(unsat证明,短路) → 其余→v11判定
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

PD = BASE / "data/gjb_438c/pair_dataset_canonical"
MODEL = str(BASE / "models/nli/qwen1.5b-sft-v11")
SYSTEM = "你是SRS需求文档一致性审查员。基于证据判断两处描述是否一致，只回答\"不一致\"或\"一致\"。"
PROMPT = """你是SRS需求文档一致性审查员。基于以下证据判断两处描述是否一致。

[证据] 表格: {table}
图: {diagram}
[陈述1] {p}
[陈述2] {h}
这两处描述是否一致? 只回答"不一致"或"一致"。"""


def prf(ys, ps):
    tp = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p == "inconsistent")
    fp = sum(1 for y, p in zip(ys, ps) if y != "inconsistent" and p == "inconsistent")
    fn = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p != "inconsistent")
    prec = tp / (tp + fp) if tp + fp else 0
    rec = tp / (tp + fn) if tp + fn else 0
    return {"P": round(prec, 3), "R": round(rec, 3),
            "F1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0}


def main() -> None:
    test = [json.loads(line) for line in open(PD / "test.jsonl", encoding="utf-8")]
    srs = [x for x in test if x["source"].startswith("srs")]
    exp = [json.loads(line) for line in open(PD / "expanded_mutations.jsonl", encoding="utf-8")]
    exp_test = [x for x in exp if x["split"] == "test" and x["pair"]["premise"] != x["pair"]["hypothesis"]]
    random.Random(42).shuffle(exp_test)
    items = srs + exp_test[:300]
    ys = [x["label"] for x in items]
    print(f"评测集: {len(items)}条 (canonical {len(srs)} + expanded 300)")

    from algorithms.consistency_check.srs_verifier import SrsVerifier
    ver = SrsVerifier()

    # ── 前置Z3: 数值型交给求解器 ──
    z3_solved = {}
    n_z3 = 0
    for i, x in enumerate(items):
        p, h = x["pair"]["premise"], x["pair"]["hypothesis"]
        if x["angle"]["type"].startswith("PARAM"):
            r = ver.solve_z3_param(p, h)
            if r:
                z3_solved[i] = r["verdict"]
                n_z3 += 1
    print(f"前置Z3解决: {n_z3}条(PARAM类)")

    # ── 主路径: v11处理其余 ──
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL, local_files_only=True,
                                                 torch_dtype=torch.float16, device_map="auto")
    model.eval()
    preds = [None] * len(items)
    rest = [i for i in range(len(items)) if i not in z3_solved]
    for i in rest:
        x = items[i]
        ctx = x.get("context") or {}
        user = PROMPT.format(table=str(ctx.get("table", ""))[:400] or "(无)",
                             diagram=str(ctx.get("diagram", ""))[:300] or "(无)",
                             p=x["pair"]["premise"][:180], h=x["pair"]["hypothesis"][:180])
        msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=768).to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=4, do_sample=False,
                                 pad_token_id=tok.eos_token_id)
        gen = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        preds[i] = "inconsistent" if "不一致" in gen else "consistent"
    for i, v in z3_solved.items():
        preds[i] = v

    m = prf(ys, preds)
    n_flag = sum(1 for p in preds if p == "inconsistent")
    print(f"\n最终架构(Z3前置+v11主路径): F1={m['F1']} P={m['P']} R={m['R']} 报警{n_flag}/{len(items)}")

    # 对照: 纯v11(无前置)
    m_v11_only = prf(ys, [p if i not in z3_solved else "inconsistent" for i, p in enumerate(preds)])
    print(f"(纯v11对照: F1≈{m_v11_only['F1']})")

    # Z3通道的正确率
    if z3_solved:
        z3_correct = sum(1 for i, v in z3_solved.items() if v == ys[i])
        print(f"Z3通道正确率: {z3_correct}/{len(z3_solved)}")

    from run_utils import open_run
    run = open_run("final_architecture_eval", {"arch": "Z3前置+V11主路径", "n": len(items)})
    run.save_result({"final": m, "z3_solved": n_z3})
    print(f"saved → {run.path}")


if __name__ == "__main__":
    main()
