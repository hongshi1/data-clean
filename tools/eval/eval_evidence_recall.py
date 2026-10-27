r"""evidence_recall框架在真实GJB-URE-v4上的端到端验证实验.

验证目标: 新框架(algorithms.context_linking.evidence_recall,
多头冻结投影+场景路由召回+单元聚焦精排)在真实16文档数据上
复现已锁定协议数字:
  recall(SemanticUnitHead)  ↔ S1/S5/S6的O1-unit
  recall+rerank             ↔ S1/S5/S6的O1-unit+Rerank(top50,unit2,b0.1)
  image词面头               ↔ S4的BM25-doc

场景: table_deep_v3(262q) / table_deep_v4(176q) / 联合438q / image(899q)
统计: R@1/R@5/R@10/MRR@10 + McNemar(精排vs召回)

用法: python tools/eval/eval_evidence_recall.py [--skip-image]
产出: results/S7_evidence_recall_all.json + runs归档
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
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"

# 锁定协议参考值(对照)
LOCKED = {
    "table_deep_v3": {"recall_R@1": 0.340, "rerank_R@1": 0.405},
    "table_deep_v4": {"recall_R@1": 0.403, "rerank_R@1": 0.608},
    "combined": {"recall_R@1": 0.365, "rerank_R@1": 0.486},
    "image": {"lexical_R@1": 0.685},
}


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-image", action="store_true")
    args = ap.parse_args()

    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    corpus = ds["corpus"]
    queries = ds["queries"]
    print(f"数据: gjb_ure_v4 ({len(corpus)}corpus, "
          f"{len(queries)}queries)")

    from algorithms.context_linking.evidence_recall import (
        EvidenceRecallPipeline,
        MultiHeadRecall,
        UnitFocusedRerank,
    )
    from algorithms.common import bge_local

    t0 = time.time()
    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    pipe = EvidenceRecallPipeline(corpus, encoder=enc,
                                  auto_reranker=False)
    store = pipe.store
    rc = MultiHeadRecall(store, enc)
    print(f"物证库+多头构建: {store.n_owners}owner {store.n_units}单元 "
          f"({time.time()-t0:.0f}s)", flush=True)

    # 真实精排器(惰性加载一次)
    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    mode = rr.ensure()
    print(f"精排器: {mode}", flush=True)
    stage2 = UnitFocusedRerank(reranker=rr, unit_topn=2, blend=0.1)

    scenes = [
        ("table_deep_v3", {"table_deep_v3"}, "table", True),
        ("table_deep_v4", {"table_deep_v4"}, "table", True),
        ("combined", {"table_deep_v3", "table_deep_v4"}, "table", True),
    ]
    if not args.skip_image:
        scenes.append(("image", {"image"}, "image", False))

    report = {}
    for name, scene_set, pool, with_rerank in scenes:
        qs = [q for q in queries
              if q["scene"] in scene_set and q["split"] == "eval"]
        golds = [set(q["expected"]) for q in qs]
        print(f"\n[{name}] {len(qs)}q pool={pool}", flush=True)
        t0 = time.time()
        recall_orders, rerank_orders = [], []
        recall_hits1, rerank_hits1 = [], []
        for qi, q in enumerate(qs):
            r50 = rc.recall(q["query"], pool=pool, topk=50)
            recall_orders.append([h.owner for h in r50.hits[:10]])
            recall_hits1.append(1 if (r50.hits
                                      and r50.hits[0].owner in golds[qi])
                                else 0)
            if with_rerank:
                rr_hits = stage2.rerank(q["query"], r50, store)[:10]
                rerank_orders.append([h.owner for h in rr_hits])
                rerank_hits1.append(1 if (rr_hits
                                          and rr_hits[0].owner in golds[qi])
                                    else 0)
            if (qi + 1) % 100 == 0:
                print(f"  {qi+1}/{len(qs)} ({time.time()-t0:.0f}s)",
                      flush=True)
        entry = {"n_queries": len(qs)}
        entry["recall"] = metrics_from_orders(recall_orders, golds)
        print(f"  recall: R@1={entry['recall']['R@1']:.3f} "
              f"R@5={entry['recall']['R@5']:.3f} "
              f"MRR={entry['recall']['MRR@10']:.3f}")
        if with_rerank:
            entry["rerank"] = metrics_from_orders(rerank_orders, golds)
            entry["mcnemar"] = mcnemar(recall_hits1, rerank_hits1)
            print(f"  rerank: R@1={entry['rerank']['R@1']:.3f} "
                  f"R@5={entry['rerank']['R@5']:.3f} "
                  f"MRR={entry['rerank']['MRR@10']:.3f} "
                  f"(p={entry['mcnemar']['p_one_sided']:.1e})")
        if name == "image":
            # 词面头单独报告(对照S4的BM25-doc)
            lex_orders = []
            for q in qs:
                raw, keep = rc.score_all(q["query"], "image")
                order = np.argsort(-np.where(keep, raw["lexical"], -np.inf))
                lex_orders.append([store.owners[int(i)]
                                   for i in order[:10]])
            entry["lexical_only"] = metrics_from_orders(lex_orders, golds)
            print(f"  lexical_only: "
                  f"R@1={entry['lexical_only']['R@1']:.3f}")
        # 与锁定值对照
        ref = LOCKED.get(name, {})
        checks = {}
        for key, val in ref.items():
            got = (entry.get("rerank", {}).get("R@1")
                   if "rerank" in key else
                   entry.get("lexical_only", {}).get("R@1")
                   if "lexical" in key else entry["recall"]["R@1"])
            checks[key] = {"locked": val, "framework": round(got, 3),
                           "delta": round(got - val, 4)}
        entry["locked_check"] = checks
        report[name] = entry

    outp = RESULTS / "S7_evidence_recall_all.json"
    outp.write_text(json.dumps({
        "protocol": ("evidence_recall框架端到端验证: 多头冻结投影"
                     "(SemanticUnitHead+LexicalHead)+场景路由召回"
                     "+UnitFocusedRerank(top50,unit2,b0.1); "
                     "数据gjb_ure_v4; 锁定值对照见locked_check"),
        "results": report,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {outp}")

    from run_utils import open_run
    handle = open_run("eval_evidence_recall", {
        "framework": "algorithms.context_linking.evidence_recall",
        "dataset": "gjb_ure_v4.json",
        "rerank": "unit_topn=2, blend=0.1, topk=50",
    })
    handle.save_result(report)
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
