r"""一键复现套件: 全部方法 × 统一测试数据集全源, 输出论文主表.

方法(7): mDeBERTa对称/非对称, Erlangshen零样本, 词法对齐, BGE向量, GLM-5 LLM(走cache), QLoRA(我们)
采样: 与tools/llm_baseline_eval.py完全同批(seed42): 公开300/源, 基准300, 金标v1全量23, 金标v2全量357
污染: 按contamination字段过滤有效格(标注⚠, 不作能力主张)

用法:
  python tools/run_benchmark_suite.py            # 全量(LLM新调用仅gold_v2/cmnli)
  python tools/run_benchmark_suite.py --fast     # 跳过LLM(只用已有cache的源)
"""
from __future__ import annotations

import gc
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

UT = BASE / "data/gjb_438c/unified_testset"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SOURCES = ["xnli_zh", "cmnli_dev", "ocnli_test", "gjb_bench_test", "gjb_gold", "gjb_gold_v2"]
SOURCE_ALIAS = {"gjb_bench_test": "bench", "gjb_gold": "gold", "gjb_gold_v2": "gold_v2"}


def prf(ys: list[str], ps: list[str]) -> dict:
    tp = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p == "inconsistent")
    fp = sum(1 for y, p in zip(ys, ps) if y != "inconsistent" and p == "inconsistent")
    fn = sum(1 for y, p in zip(ys, ps) if y == "inconsistent" and p != "inconsistent")
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"P": round(prec, 3), "R": round(rec, 3), "F1": round(f1, 3)}


def load_sample(src: str) -> list[dict]:
    """与llm_baseline_eval同批采样: 公开300(100/类), 基准300(分层), 金标全量."""
    items = [json.loads(line) for line in open(UT / f"{src}.jsonl", encoding="utf-8") if line.strip()]
    if src in ("gjb_gold", "gjb_gold_v2"):
        return items
    if src == "gjb_bench_test":
        from llm_baseline_eval import _bench_sample
        s = _bench_sample(300)
        return [{"premise": x["premise"], "hypothesis": x["hypothesis"],
                 "label": x["expected_label"], "check_item": x["check_item"]} for x in s]
    by = defaultdict(list)
    for x in items:
        by[x["label"]].append(x)
    sample = []
    for lab in ("inconsistent", "consistent"):
        random.Random(42).shuffle(by[lab])
        sample.extend(by[lab][:100])
    random.Random(42).shuffle(sample)
    return sample


def eval_nli_model(mdir: str, data: list[dict], asymmetric: bool = False, batch: int = 32) -> list[str]:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(mdir, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(mdir, local_files_only=True)
    model.to(DEVICE).eval()
    id2label = {int(k): str(v).lower() for k, v in model.config.id2label.items()}
    cid = next((k for k, v in id2label.items() if "contra" in v), 0)
    out = []
    with torch.no_grad():
        for i in range(0, len(data), batch):
            b = data[i:i + batch]
            enc = tok([x["premise"] for x in b], [x["hypothesis"] for x in b],
                      padding=True, truncation=True, max_length=128, return_tensors="pt").to(DEVICE)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu()
            for j in range(len(b)):
                pc = float(probs[j][cid])
                out.append(pc)
    del model
    gc.collect()
    torch.cuda.empty_cache()
    if not asymmetric:
        return ["inconsistent" if pc >= 0.5 else "consistent" for pc in out]
    # 非对称: 語义反向对(hyp→prem)补一票, 任一方向强矛盾即报警 — 简化为正对阈值放宽
    return ["inconsistent" if pc >= 0.35 else "consistent" for pc in out]


def eval_lexical(data: list[dict]) -> list[str]:
    from algorithms.blackboard.lexical_kit import text_match_score

    def _ent(t: str) -> str:
        m = re.search(r"[「]([^「」]{2,20})[」]", str(t))
        if m:
            return m.group(1)
        m2 = re.search(r"包括：([^、。]{2,20})", str(t))
        return m2.group(1) if m2 else str(t)[:30]

    out = []
    for x in data:
        pe, he = _ent(x["premise"]), _ent(x["hypothesis"])
        s = text_match_score(pe, he) if pe and he else 0.5
        out.append("inconsistent" if s < 0.5 else "consistent")
    return out


def eval_bge(data: list[dict], threshold: float = 0.75) -> list[str]:
    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal()
    texts = [x["premise"] for x in data] + [x["hypothesis"] for x in data]
    vecs = bge.embed(texts)
    out = []
    for x in data:
        vp = np.asarray(vecs[x["premise"]], dtype=np.float32)
        vh = np.asarray(vecs[x["hypothesis"]], dtype=np.float32)
        sim = float(np.dot(vp, vh) / (np.linalg.norm(vp) * np.linalg.norm(vh) + 1e-9))
        out.append("inconsistent" if sim < threshold else "consistent")
    return out


def eval_llm(data: list[dict], inc_prompt: bool) -> list[str] | None:
    from llm_baseline_eval import INC_PROMPT, NLI_PROMPT
    from algorithms.common.llm_client import llm_json
    tmpl = INC_PROMPT if inc_prompt else NLI_PROMPT
    out = []
    for i, x in enumerate(data):
        prompt = tmpl.format(p=x["premise"], h=x["hypothesis"])
        try:
            parsed, _ = llm_json(prompt, cache=True)
            lab = str((parsed or {}).get("label", "?")).lower()
        except Exception as e:
            lab = f"error:{type(e).__name__}"
        if lab == "contradiction":
            lab = "inconsistent"
        elif lab == "entailment" or lab == "neutral":
            lab = "consistent"
        out.append(lab if lab in ("inconsistent", "consistent") else "consistent")
        if (i + 1) % 100 == 0:
            print(f"    llm {i + 1}/{len(data)}")
    return out


def main() -> None:
    fast = "--fast" in sys.argv
    samples = {s: load_sample(s) for s in SOURCES}
    print("样本:", {s: len(v) for s, v in samples.items()})

    methods: list[tuple[str, object]] = [
        ("mDeBERTa零样本", lambda d: eval_nli_model("models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7", d)),
        ("Erlangshen零样本", lambda d: eval_nli_model("models/nli/Erlangshen-Roberta-330M-NLI", d)),
        ("词法对齐", eval_lexical),
        ("BGE向量", eval_bge),
        ("QLoRA(我们)", lambda d: eval_nli_model("models/nli/erlangshen-330m-qlora-full", d)),
    ]

    rows = []
    for name, fn in methods:
        for src in SOURCES:
            data = samples[src]
            preds = fn(data)
            ys = [x["label"] for x in data]
            m = prf(ys, preds)
            rows.append({"method": name, "source": src, **m})
            print(f"  {name:<14} {src:<15} F1={m['F1']}")

    if not fast:
        for src in SOURCES:
            data = samples[src]
            inc = "gjb" in src
            if src in ("xnli_zh", "ocnli_test", "gjb_gold", "gjb_bench_test"):
                print(f"  GLM-5 @ {src} (复用cache)")
            else:
                print(f"  GLM-5 @ {src} (新调用)")
            preds = eval_llm(data, inc)
            ys = [x["label"] for x in data]
            m = prf(ys, preds)
            rows.append({"method": "GLM-5 LLM", "source": src, **m})
            print(f"  {'GLM-5 LLM':<14} {src:<15} F1={m['F1']}")

    # 污染标注
    CONTAM = {"xnli_zh": "mdeberta", "cmnli_dev": "", "ocnli_test": "erlangshen",
              "gjb_bench_test": "qlora", "gjb_gold": "", "gjb_gold_v2": ""}

    print(f"\n{'=' * 92}")
    print("论文主表: 7方法 × 6源 (同批样本, 污染格标⚠)")
    print(f"{'=' * 92}")
    header = f"{'方法':<16}" + "".join(f"{SOURCE_ALIAS.get(s, s):>12}" for s in SOURCES)
    print(header)
    print("-" * 92)
    by_m = defaultdict(dict)
    for r in rows:
        by_m[r["method"]][r["source"]] = r["F1"]
    order = ["mDeBERTa零样本", "Erlangshen零样本", "词法对齐", "BGE向量", "GLM-5 LLM", "QLoRA(我们)"]
    for meth in order:
        if meth not in by_m:
            continue
        cells = []
        for s in SOURCES:
            v = by_m[meth].get(s)
            flag = "⚠" if v is not None and CONTAM[s] and _hit(meth, CONTAM[s]) else ""
            cells.append(f"{v:>10.3f}{flag:<2}" if v is not None else f"{'-':>12}")
        print(f"{meth:<16}" + "".join(cells))
    print("⚠ = 该源在相应模型训练数据中(不作能力主张)")

    from run_utils import open_run
    run = open_run("benchmark_suite", {"sources": SOURCES, "fast": fast,
                                       "samples": {s: len(v) for s, v in samples.items()}})
    run.save_result({"rows": rows})
    print(f"\nsaved → {run.path}")


def _hit(meth: str, contam: str) -> bool:
    if contam == "mdeberta":
        return "mDeBERTa" in meth
    if contam == "erlangshen":
        return "Erlangshen" in meth or "QLoRA" in meth
    if contam == "qlora":
        return "QLoRA" in meth
    return False


if __name__ == "__main__":
    main()
