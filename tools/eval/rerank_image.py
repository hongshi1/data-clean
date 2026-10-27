r"""图片场景两阶段: Token-MaxSim召回 + BGE-Reranker重排.

验证单元聚焦重排在图片场景的稳健性(表格场景已+6.5pt).

  Stage 1: Token-MaxSim(图片场景冠军, S4 R@1=0.633) — 召回top-K
  Stage 2: cross-encoder重排, doc = 图片标题+单元(VLM元素, 天然短文档)

用法: python tools/eval/rerank_image.py [--topk 50] [--blend 0.0]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"


def metrics_from_orders(orders, golds):
    r1 = r5 = r10 = mrr = 0.0
    for order, g in zip(orders, golds):
        if not g:
            continue
        hit_rank = None
        for rank, ci in enumerate(order, 1):
            if ci in g:
                hit_rank = rank
                break
        if hit_rank is None:
            continue
        if hit_rank == 1:
            r1 += 1
        if hit_rank <= 5:
            r5 += 1
        if hit_rank <= 10:
            r10 += 1
            mrr += 1.0 / hit_rank
    total = len(orders)
    return {"R@1": r1 / total, "R@5": r5 / total, "R@10": r10 / total,
            "MRR@10": mrr / total}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=50)
    ap.add_argument("--blend", type=float, default=0.0)
    ap.add_argument("--doc-units", type=int, default=10,
                    help="rerank文档最多包含的单元数")
    args = ap.parse_args()

    ds = json.loads((V3 / "gjb_ure_v3.json").read_text(encoding="utf-8"))
    queries = [q for q in ds["queries"]
               if q.get("scene") == "image" and q.get("split") == "eval"]
    pool = [c for c in ds["corpus"] if c["type"] == "image"]
    idx = {c["chunk_id"]: i for i, c in enumerate(pool)}
    n = len(pool)
    golds = [{idx[t] for t in q["expected"] if t in idx} for q in queries]
    print(f"图片两阶段: {len(queries)}q, 池{n}图, top-{args.topk}, "
          f"blend={args.blend}")

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    print("Stage 1: Token-MaxSim召回...", flush=True)
    t0 = time.time()
    from eval_token_maxsim import TokenMaxSim
    tms = TokenMaxSim(bge)
    tms.build([(c["title"] + " " + " ".join(c["units"])) for c in pool])

    topk_lists = []
    stage1_scores = []
    for q in queries:
        s = tms.score(q["query"])
        stage1_scores.append(s)
        topk_lists.append(list(np.argsort(-s)[:args.topk]))
    orders_s1 = [list(np.argsort(-s)[:10]) for s in stage1_scores]
    m1 = metrics_from_orders(orders_s1, golds)
    print(f"  Stage1: R@1={m1['R@1']:.3f} R@5={m1['R@5']:.3f} "
          f"R@10={m1['R@10']:.3f} MRR={m1['MRR@10']:.3f} "
          f"({time.time()-t0:.0f}s)")

    print("Stage 2: BGE-Reranker-v2-m3重排...", flush=True)
    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    mode = rr.ensure()
    print(f"  reranker mode: {mode}")
    t0 = time.time()
    final_orders = []
    batch = 16
    for qi, q in enumerate(queries):
        cand = topk_lists[qi]
        if not cand:
            final_orders.append([])
            continue
        doc_texts = []
        for ci in cand:
            c = pool[ci]
            units = c["units"][:args.doc_units]
            doc = c["title"] + " ; " + " ; ".join(units)
            doc_texts.append(doc[:2000])
        pairs = [(q["query"], d) for d in doc_texts]
        scores = []
        for b0 in range(0, len(pairs), batch):
            scores.extend(rr.score(pairs[b0:b0 + batch]))
        if args.blend > 0:
            base = [float(stage1_scores[qi][ci]) for ci in cand]
            bmin, bmax = min(base), max(base)
            brng = max(bmax - bmin, 1e-8)
            base_n = [(b - bmin) / brng for b in base]
            rmin, rmax = min(scores), max(scores)
            rrng = max(rmax - rmin, 1e-8)
            comb = [sc + args.blend * bn / rrng * abs(rmax)
                    for sc, bn in zip(scores, base_n)]
            order = sorted(range(len(cand)),
                           key=lambda j: (-comb[j], j))
        else:
            order = sorted(range(len(cand)),
                           key=lambda j: (-scores[j], j))
        final_orders.append([cand[j] for j in order])
        if (qi + 1) % 200 == 0:
            print(f"  重排 {qi+1}/{len(queries)} ({time.time()-t0:.0f}s)",
                  flush=True)
    m2 = metrics_from_orders(final_orders, golds)
    print(f"  Stage2: R@1={m2['R@1']:.3f} R@5={m2['R@5']:.3f} "
          f"R@10={m2['R@10']:.3f} MRR={m2['MRR@10']:.3f} "
          f"({time.time()-t0:.0f}s)")
    print(f"  ΔR@1 = {m2['R@1'] - m1['R@1']:+.3f}")

    # McNemar(R@1)
    b_cnt = c_cnt = 0
    for qi, (o1, o2) in enumerate(zip(orders_s1, final_orders)):
        g = golds[qi]
        h1 = 1 if (o1 and o1[0] in g) else 0
        h2 = 1 if (o2 and o2[0] in g) else 0
        if h2 > h1:
            b_cnt += 1
        elif h1 > h2:
            c_cnt += 1
    if b_cnt + c_cnt > 0:
        z = (b_cnt - c_cnt) / ((b_cnt + c_cnt) ** 0.5)
        p = 0.5 * (1 + math.erf(z / 2 ** 0.5))
        p_one = 1 - p if p > 0.5 else p
    else:
        z, p_one = 0.0, 1.0
    print(f"  McNemar(vs stage1): b={b_cnt} c={c_cnt} z={z:.2f} "
          f"p(one-sided)={p_one:.2e}")

    # 归档(stage1=Token-MaxSim也写入, 恢复S4基线行)
    outp = (BASE / "data/gjb_438c/data_assets/evalsets/results/"
            "S4_image_all.json")
    d = json.loads(outp.read_text(encoding="utf-8"))
    d["results"]["Token-MaxSim"] = m1
    key = (f"Token-MaxSim+Rerank@{args.topk}"
           + (f"(b{args.blend})" if args.blend > 0 else ""))
    d["results"][key] = m2
    d["protocol"]["rerank_significance"] = (
        f"TMS+Rerank vs TMS: McNemar b={b_cnt} c={c_cnt}, "
        f"p={p_one:.2e}(one-sided)")
    outp.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"→ 已写入S4结果: Token-MaxSim + {key}")

    from run_utils import open_run
    handle = open_run("rerank_image", {
        "stage1": "Token-MaxSim (BGE token late interaction)",
        "stage2": "BGE-Reranker-v2-m3 cross-encoder",
        "topk": args.topk, "blend": args.blend,
        "doc_units": args.doc_units,
        "n_queries": len(queries), "query_set_hash": "10be34d928f5f99d",
    })
    handle.save_result({"stage1_metrics": m1, "stage2_metrics": m2,
                        "mcnemar": {"b": b_cnt, "c": c_cnt,
                                    "p_one_sided": p_one}})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
