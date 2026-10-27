r"""LLM列表级重排评测(RQ2: listwise vs pointwise交互侧对照).

科研问题: 残余90条精度失败源于pointwise逐对绝对打分;
列表级相对判别(一次看全候选)能否救回?

协议:
  Stage1: O1-unit召回top-20(K=20, 列表级上下文限制)
  Stage2: LLMListwiseRerank(glm, cache=True) — doc=表内top-2单元拼接
  对照: stage1(O1-unit) + 锁定的cross-encoder精排(0.486@top50)

用法: python tools/eval/eval_llm_listwise.py
产出: results/S9_llm_listwise.json + runs归档
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"

TOPK = 20


def metrics_from_orders(orders: list[list[str]],
                        golds: list[set]) -> dict:
    r1 = r5 = r10 = mrr = 0.0
    for order, g in zip(orders, golds):
        if not g:
            continue
        rank = None
        for i, owner in enumerate(order, 1):
            if owner in g:
                rank = i
                break
        if rank is None:
            continue
        if rank == 1:
            r1 += 1
        if rank <= 5:
            r5 += 1
        if rank <= 10:
            r10 += 1
            mrr += 1.0 / rank
    n = len(orders)
    return {"R@1": r1 / n, "R@5": r5 / n, "R@10": r10 / n,
            "MRR@10": mrr / n}


def mcnemar(hit_a: list, hit_b: list) -> dict:
    b = sum(1 for a, x in zip(hit_a, hit_b) if x and not a)
    c = sum(1 for a, x in zip(hit_a, hit_b) if a and not x)
    if b + c > 0:
        z = (b - c) / ((b + c) ** 0.5)
        p = 0.5 * (1 + math.erf(z / 2 ** 0.5))
        p_one = 1 - p if p > 0.5 else p
    else:
        z, p_one = 0.0, 1.0
    return {"b": b, "c": c, "p_one_sided": p_one}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    pool = [c for c in ds["corpus"] if c["type"] == "table"]
    queries = [q for q in ds["queries"]
               if q["scene"] in ("table_deep_v3", "table_deep_v4")
               and q["split"] == "eval"]
    golds = [set(q["expected"]) for q in queries]
    print(f"LLM列表级重排: {len(queries)}q, top-{TOPK}, glm缓存")

    from algorithms.context_linking.evidence_recall import (
        EvidenceStore,
        MultiHeadRecall,
    )
    from algorithms.context_linking.baselines import LLMListwiseRerank
    from algorithms.common import bge_local
    from algorithms.common.llm_client import llm_chat

    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    store = EvidenceStore.from_ure(pool)
    rc = MultiHeadRecall(store, enc)

    def llm_fn(query: str, _docs: str) -> str:
        """容错调用: GLM偶发空内容(审核边界)→重试一次→空串(回退原序)."""
        prompt = _prompt(query, _docs)
        for temp in (0.1, 0.7):
            try:
                ans, _ = llm_chat(prompt, cache=(temp == 0.1),
                                  prefer="glm", temperature=temp)
                if ans and ans.strip():
                    return ans
            except (RuntimeError, OSError):
                continue
        return ""

    # prompt构造放外面以便缓存键稳定
    def _prompt(query: str, docs: str) -> str:
        items = docs.split(" ; ")
        lines = [f"{i}. {d[:150]}" for i, d in enumerate(items, 1)]
        return ("你是文档检索评测的排序器。给定查询和候选证据列表，"
                "按与查询的相关性从高到低排列候选编号。\n\n"
                f"查询: {query}\n\n候选证据:\n" + "\n".join(lines) +
                "\n\n只输出逗号分隔的编号序列(从最相关到最不相关)，"
                "例如: 3,1,2,4,5")

    lw = LLMListwiseRerank(llm_fn, max_docs=TOPK)

    s1_orders, s2_orders = [], []
    s1_h1, s2_h1 = [], []
    t0 = time.time()
    for qi, q in enumerate(queries):
        r = rc.recall(q["query"], pool="table", topk=TOPK)
        cand_owners = [h.owner for h in r.hits]
        docs = [" ; ".join(h.best_units) for h in r.hits]
        s1_orders.append(cand_owners[:10])
        s1_h1.append(1 if cand_owners and cand_owners[0] in golds[qi]
                     else 0)
        order = lw.rank(q["query"], docs)
        final = [cand_owners[i] for i in order[:10]]
        s2_orders.append(final)
        s2_h1.append(1 if final and final[0] in golds[qi] else 0)
        if (qi + 1) % 50 == 0:
            el = time.time() - t0
            print(f"  {qi+1}/{len(queries)} ({el:.0f}s, "
                  f"{el/(qi+1):.1f}s/q)", flush=True)

    m1 = metrics_from_orders(s1_orders, golds)
    m2 = metrics_from_orders(s2_orders, golds)
    mc = mcnemar(s1_h1, s2_h1)
    print(f"\nstage1(O1-unit@{TOPK}): R@1={m1['R@1']:.4f} "
          f"R@5={m1['R@5']:.4f} MRR={m1['MRR@10']:.4f}")
    print(f"stage2(LLM列表级):      R@1={m2['R@1']:.4f} "
          f"R@5={m2['R@5']:.4f} MRR={m2['MRR@10']:.4f} "
          f"(p={mc['p_one_sided']:.1e}, b={mc['b']} c={mc['c']})")
    print("参照cross-encoder(pointwise@50): R@1=0.4863 (锁定)")

    outp = RESULTS / "S9_llm_listwise.json"
    outp.write_text(json.dumps({
        "protocol": (f"LLM列表级重排: glm(cache=True), K={TOPK}, "
                     "doc=单元top2; stage1=O1-unit@同K; "
                     "对照=pointwise cross-encoder@50"),
        "stage1": m1, "stage2": m2, "mcnemar": mc,
        "reference": {"pointwise_ce_R@1": 0.4863, "note":
                      "K=20上限低于CE的top50; 列表vs逐对为对照轴"},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {outp}")

    from run_utils import open_run
    handle = open_run("eval_llm_listwise", {
        "scene": "combined 438q", "K": TOPK,
        "llm": "glm cached", "stage1": "O1-unit"})
    handle.save_result({"stage1": m1, "stage2": m2, "mcnemar": mc})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
