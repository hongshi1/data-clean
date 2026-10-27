r"""重排分析套件: blend敏感性 + per-query dump + bootstrap CI (一次计算).

关键效率: rerank分数与blend无关(只影响融合), 故一遍重排
产出全部blend网格; per-query命中旗标顺带dump(失败类型学+
bootstrap置信区间的原料).

场景: GJB联合438q(v3+v4, 主数字场景)
blend网格: {0, 0.05, 0.1, 0.2, 0.3}(0.1=标定值)

用法: python tools/eval/rerank_analysis_suite.py
产出: results/_blend_sweep.json, results/_per_query_dump.json, runs归档
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"
PREFIX = "为这个句子生成表示以用于检索相关文章："
BLENDS = [0.0, 0.05, 0.1, 0.2, 0.3]


def metrics_from_hitlists(hit1: list, hit5: list, hit10: list,
                          rr10: list, n: int) -> dict:
    return {"R@1": sum(hit1) / n, "R@5": sum(hit5) / n,
            "R@10": sum(hit10) / n, "MRR@10": sum(rr10) / n}


def rank_stats(order: list, gold: set) -> tuple:
    rank = next((r for r, o in enumerate(order, 1) if o in gold), None)
    h1 = 1 if rank == 1 else 0
    h5 = 1 if rank is not None and rank <= 5 else 0
    h10 = 1 if rank is not None and rank <= 10 else 0
    rr = (1.0 / rank) if (rank is not None and rank <= 10) else 0.0
    return h1, h5, h10, rr, rank


def bootstrap_ci(hits: list, n_boot: int = 2000, seed: int = 42) -> list:
    """R@1的95%百分位bootstrap CI(确定性seed)."""
    a = np.asarray(hits, dtype=np.float32)
    rng = np.random.default_rng(seed)
    n = len(a)
    boots = [float(a[rng.integers(0, n, n)].mean())
             for _ in range(n_boot)]
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot)]
    return [round(lo, 4), round(hi, 4)]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    corpus = ds["corpus"]
    queries = [q for q in ds["queries"]
               if q["scene"] in ("table_deep_v3", "table_deep_v4")
               and q["split"] == "eval"]
    pool = [c for c in corpus if c["type"] == "table"]
    n = len(pool)
    print(f"重排分析套件: {len(queries)}q × {n}表, blends={BLENDS}")

    from algorithms.context_linking.evidence_recall import (
        EvidenceStore,
        MultiHeadRecall,
    )
    from algorithms.common import bge_local

    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    store = EvidenceStore.from_ure(pool)
    rc = MultiHeadRecall(store, enc)
    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    rr.ensure()

    # 逐查询: 召回top50 + 重排原始分(与blend无关) 一次计算
    t0 = time.time()
    per_q = []
    blend_hits = {b: {"h1": [], "h5": [], "h10": [], "rr": []}
                  for b in BLENDS}
    for qi, q in enumerate(queries):
        golds = set(q["expected"])
        r50 = rc.recall(q["query"], pool="table", topk=50)
        # 重排原始分
        hits = r50.hits
        docs = [" ; ".join(h.best_units)[:2000] for h in hits]
        pairs = [(q["query"], d) for d in docs]
        scores = []
        for b0 in range(0, len(pairs), 16):
            scores.extend(rr.score(pairs[b0:b0 + 16]))
        base = np.asarray([h.score for h in hits], dtype=np.float32)
        # stage1序: 全top-50内rank(供dump与失败分桶)
        s1_order50 = [h.owner for h in hits]
        s1_rank50 = next((r for r, o in enumerate(s1_order50, 1)
                          if o in golds), None)
        s1_order10 = s1_order50[:10]
        s1_h = rank_stats(s1_order10, golds)
        per_q.append({
            "query": q["query"], "scene": q["scene"],
            "overlap": q.get("overlap", 0.0),
            "gold": sorted(golds),
            "stage1_rank50": s1_rank50,
            "stage1_hit1": s1_h[0],
        })
        r = np.asarray(scores, dtype=np.float32)
        rmin, rmax = float(r.min()), float(r.max())
        rrng = max(rmax - rmin, 1e-8)
        bmin, bmax = float(base.min()), float(base.max())
        brng = max(bmax - bmin, 1e-8)
        base_n = (base - bmin) / brng
        for b in BLENDS:
            comb = r + b * (base_n / rrng) * abs(rmax)
            order = sorted(range(len(hits)),
                           key=lambda j: (-float(comb[j]), j))
            final = [hits[j].owner for j in order[:10]]
            h1, h5, h10, rrv, rank = rank_stats(final, golds)
            blend_hits[b]["h1"].append(h1)
            blend_hits[b]["h5"].append(h5)
            blend_hits[b]["h10"].append(h10)
            blend_hits[b]["rr"].append(rrv)
            if b == 0.1:
                per_q[-1]["stage2_rank"] = rank
                per_q[-1]["stage2_hit1"] = h1
        if (qi + 1) % 100 == 0:
            print(f"  {qi+1}/{len(queries)} ({time.time()-t0:.0f}s)",
                  flush=True)

    n_q = len(queries)
    sweep = {}
    print("\n=== blend敏感性(T6) ===")
    print(f"{'blend':>6s} {'R@1':>7s} {'R@5':>7s} {'MRR':>7s}")
    for b in BLENDS:
        h = blend_hits[b]
        m = metrics_from_hitlists(h["h1"], h["h5"], h["h10"], h["rr"], n_q)
        sweep[str(b)] = m
        print(f"{b:>6.2f} {m['R@1']:>7.3f} {m['R@5']:>7.3f} "
              f"{m['MRR@10']:>7.3f}")
    (RESULTS / "_blend_sweep.json").write_text(json.dumps({
        "protocol": ("blend敏感性: GJB联合438q, unit2/top50, "
                     "一遍重排×5融合权重(重排分与blend无关)"),
        "sweep": sweep,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # bootstrap CI
    h11 = blend_hits[0.1]["h1"]
    ci = {"O1+Rerank(b0.1)": bootstrap_ci(h11),
          "O1-unit(召回)": bootstrap_ci(
              [p["stage1_hit1"] for p in per_q])}
    # 失败类型学分桶(rank基于top-50全列表)
    recall_fail = sum(1 for p in per_q if p["stage1_rank50"] is None
                      or p["stage1_rank50"] > 50)
    edge_11_50 = sum(1 for p in per_q
                     if p["stage1_rank50"] and 10 < p["stage1_rank50"]
                     <= 50)
    prec_fail = sum(1 for p in per_q
                    if p["stage1_rank50"] and 1 < p["stage1_rank50"] <= 10
                    and not p.get("stage2_hit1"))
    rescued = sum(1 for p in per_q
                  if not p["stage1_hit1"] and p.get("stage2_hit1"))
    damaged = sum(1 for p in per_q
                  if p["stage1_hit1"] and not p.get("stage2_hit1"))

    (RESULTS / "_per_query_dump.json").write_text(json.dumps({
        "protocol": ("per-query dump: stage1(top-50 rank)/stage2(blend=0.1)"
                     " gold rank与命中旗标; 失败类型学分桶+bootstrap原料"),
        "failure_taxonomy": {
            "召回失败(gold∉top50)": recall_fail,
            "召回边缘(rank11-50, 重排可及)": edge_11_50,
            "精度失败(rank2-10, 重排未救)": prec_fail,
            "重排救回(stage1非首→stage2首)": rescued,
            "重排致损(stage1首→stage2非首)": damaged,
        },
        "bootstrap_ci": ci,
        "per_query": per_q,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== 失败类型学(T9) ===")
    print(f"  召回失败(∉top50): {recall_fail} | 召回边缘(11-50): "
          f"{edge_11_50}")
    print(f"  精度失败(2-10未救): {prec_fail}")
    print(f"  重排救回: {rescued} | 重排致损: {damaged}")
    print(f"  bootstrap95%CI: O1+Rerank={ci['O1+Rerank(b0.1)']} "
          f"O1召回={ci['O1-unit(召回)']}")
    print("\n→ _blend_sweep.json, _per_query_dump.json")

    from run_utils import open_run
    handle = open_run("rerank_analysis_suite", {
        "scene": "combined 438q", "blends": BLENDS,
        "rerank": "unit2, top50", "dump": "per_query",
    })
    handle.save_result({"sweep": sweep,
                        "failure_taxonomy": {
                            "recall_fail": recall_fail,
                            "prec_fail": prec_fail,
                            "rescued": rescued, "damaged": damaged},
                        "bootstrap_ci": ci})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
