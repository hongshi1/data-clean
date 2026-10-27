r"""Qwen3-Reranker×单元聚焦重排评测(层1: 2025精排器vs BGE-Reranker).

协议与锁定cross-encoder重排完全一致(top50/unit2/blend0.1),
仅替换精排器: BGE-Reranker-v2-m3(2024) → Qwen3-Reranker-0.6B(2025).
对照: 锁定O1+Rerank(BGE-RR)=0.4863.

模板: 官方judge范式(冒烟验证: 相关0.9996 vs 无关0.0001).

用法: python tools/eval/eval_qwen3_reranker.py
产出: results/S11_qwen3_reranker.json + runs归档
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
MODEL_DIR = BASE / "models/reranker/qwen3-reranker-0.6b"
INSTRUCTION = ("Given a query, retrieve relevant passages that "
               "answer the query")
PREFIX = ("<|im_start|>system\nJudge whether the Document meets the "
          "requirements based on the Query and the Instruct provided. "
          'Note that the answer can only be "yes" or "no".<|im_end|>')
SUFFIX = "<|im_end|>\n<|im_start|>assistant\n"


class Qwen3Reranker:
    """Qwen3-Reranker: P(yes)/(P(yes)+P(no))相关性分."""

    name = "qwen3_reranker"

    def __init__(self, model_dir: Path) -> None:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(str(model_dir),
                                                  padding_side="left")
        self.model = (AutoModelForCausalLM.from_pretrained(
            str(model_dir), torch_dtype=torch.bfloat16).cuda().eval())
        yes_id = self.tok.encode("yes", add_special_tokens=False)[0]
        no_id = self.tok.encode("no", add_special_tokens=False)[0]
        self.yes_id, self.no_id = yes_id, no_id

    def score(self, pairs: list[tuple[str, str]]) -> list[float]:
        out = []
        for query, doc in pairs:
            doc = doc[:1500]
            text = (PREFIX + f"\n<|im_start|>user\n<Instruct>: "
                    f"{INSTRUCTION}\n\n<Query>: {query[:500]}\n\n"
                    f"<Document>: {doc}" + SUFFIX)
            enc = self.tok(text, return_tensors="pt", truncation=True,
                           max_length=2048).to("cuda")
            with torch.no_grad():
                logits = self.model(**enc).logits[0, -1]
            lps = torch.log_softmax(logits.float(), dim=-1)
            py = math.exp(float(lps[self.yes_id]))
            pn = math.exp(float(lps[self.no_id]))
            out.append(py / (py + pn) if (py + pn) > 0 else 0.0)
        return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    if not (MODEL_DIR / "config.json").exists():
        print(f"模型缺失: {MODEL_DIR}")
        sys.exit(1)
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    pool = [c for c in ds["corpus"] if c["type"] == "table"]
    queries = [q for q in ds["queries"]
               if q["scene"] in ("table_deep_v3", "table_deep_v4")
               and q["split"] == "eval"]
    golds = [set(q["expected"]) for q in queries]
    print(f"Qwen3-Reranker评测: {len(queries)}q, top50/unit2/blend0.1")

    from algorithms.context_linking.evidence_recall import (
        EvidenceStore,
        MultiHeadRecall,
    )
    from algorithms.common import bge_local

    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    store = EvidenceStore.from_ure(pool)
    rc = MultiHeadRecall(store, enc)
    rr = Qwen3Reranker(MODEL_DIR)

    s1_orders, s2_orders = [], []
    s1_h1, s2_h1 = [], []
    t0 = time.time()
    for qi, q in enumerate(queries):
        r50 = rc.recall(q["query"], pool="table", topk=50)
        hits = r50.hits
        s1_orders.append([h.owner for h in hits[:10]])
        s1_h1.append(1 if hits and hits[0].owner in golds[qi] else 0)
        docs = [" ; ".join(h.best_units)[:1500] for h in hits]
        pairs = [(q["query"], d) for d in docs]
        scores = rr.score(pairs)
        # 融合(与锁定协议同式): rerank + 0.1×标准化stage1
        base = np.asarray([h.score for h in hits], dtype=np.float32)
        bmin, bmax = float(base.min()), float(base.max())
        brng = max(bmax - bmin, 1e-8)
        base_n = (base - bmin) / brng
        r = np.asarray(scores, dtype=np.float32)
        rmin, rmax = float(r.min()), float(r.max())
        rrng = max(rmax - rmin, 1e-8)
        comb = r + 0.1 * (base_n / rrng) * abs(rmax)
        order = sorted(range(len(hits)),
                       key=lambda j: (-float(comb[j]), j))
        final = [hits[j].owner for j in order[:10]]
        s2_orders.append(final)
        s2_h1.append(1 if final and final[0] in golds[qi] else 0)
        if (qi + 1) % 50 == 0:
            el = time.time() - t0
            print(f"  {qi+1}/{len(queries)} ({el:.0f}s)", flush=True)

    def metrics(orders: list[list[str]]) -> dict:
        r1 = r5 = mrr = 0.0
        for order, g in zip(orders, golds):
            rank = next((i for i, o in enumerate(order, 1) if o in g),
                        None)
            if rank == 1:
                r1 += 1
            if rank is not None and rank <= 5:
                r5 += 1
            if rank is not None and rank <= 10:
                mrr += 1.0 / rank
        m = len(orders)
        return {"R@1": r1 / m, "R@5": r5 / m, "MRR@10": mrr / m}

    m1 = metrics(s1_orders)
    m2 = metrics(s2_orders)
    b = sum(1 for a, x in zip(s1_h1, s2_h1) if x and not a)
    c = sum(1 for a, x in zip(s1_h1, s2_h1) if a and not x)
    z = (b - c) / ((b + c) ** 0.5) if b + c else 0.0
    p = 0.5 * (1 + math.erf(z / 2 ** 0.5)) if b + c else 1.0
    p_one = 1 - p if p > 0.5 else p

    print(f"\nstage1(O1-unit):    R@1={m1['R@1']:.4f} "
          f"R@5={m1['R@5']:.4f} MRR={m1['MRR@10']:.4f}")
    print(f"Qwen3-Rerank:       R@1={m2['R@1']:.4f} "
          f"R@5={m2['R@5']:.4f} MRR={m2['MRR@10']:.4f} "
          f"(p={p_one:.1e}, b={b} c={c})")
    print("参照BGE-Reranker(锁定): R@1=0.4863, b=77 c=24")

    outp = RESULTS / "S11_qwen3_reranker.json"
    outp.write_text(json.dumps({
        "protocol": ("Qwen3-Reranker-0.6B单元聚焦重排: 同锁定协议"
                     "(top50/unit2/blend0.1), 仅换精排器(2025 vs 2024)"),
        "stage1": m1, "stage2": m2,
        "mcnemar": {"b": b, "c": c, "p_one_sided": p_one},
        "reference_bge_rr": {"R@1": 0.4863, "b": 77, "c": 24},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {outp}")

    from run_utils import open_run
    handle = open_run("eval_qwen3_reranker", {
        "reranker": "Qwen3-Reranker-0.6B", "scene": "combined 438q",
        "protocol": "top50/unit2/blend0.1"})
    handle.save_result({"stage1": m1, "stage2": m2, "mcnemar": {
        "b": b, "c": c, "p_one_sided": p_one}})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
