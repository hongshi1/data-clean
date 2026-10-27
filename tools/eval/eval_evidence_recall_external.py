r"""evidence_recall框架在4个外部数据集上的评测(语言匹配协议).

数据集(全URE格式, V3/):
  WTQ (en, 2100表, 2000q采样seed42)      ↔ 锁定O1=0.4095, +Rerank=0.4395
  FeTaQA (en, 2003表, 2000q采样)         ↔ 锁定O1=0.856, +Rerank=0.840
  DuRetrieval (zh, 10K池, 2000q)         ↔ 锁定O1=0.837; 重排=新数字
  PURE-MMQA (en, 1128块全池, 180q)       ↔ 锁定O1=0.283; rrF参考0.325

协议: 语言匹配编码器(en=bge-base-en-v1.5+EN前缀, zh=bge-large-zh+zh前缀);
recall=SemanticUnitHead(O1-unit数学); rerank=UnitFocusedRerank(unit2,b0.1).

用法: python tools/eval/eval_evidence_recall_external.py
产出: results/S8_evidence_recall_external.json + runs归档
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
EN_MODEL = BASE / "models/embedding/bge-base-en-v1.5"
EN_CACHE = BASE / "data/gjb_438c/blackboard/bge_cache_en.pkl"
EN_PREFIX = "Represent this sentence for searching relevant passages: "

DATASETS = [
    ("wtq", "wtq_ure.json", "en", 2000, "table",
     {"recall_R@1": 0.4095, "rerank_R@1": 0.4395}),
    ("fetaqa", "fetaqa_ure.json", "en", 2000, "table",
     {"recall_R@1": 0.856, "rerank_R@1": 0.840}),
    ("duret", "duret_ure.json", "zh", 2000, "table",
     {"recall_R@1": 0.837}),
    ("pure", "pure_mmqa_ure.json", "en", 180, "all",
     {"recall_R@1": 0.283, "rerank_R@1(rrF参考)": 0.325}),
]


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
    ap.add_argument("--only", default=None,
                    help="只跑指定数据集(逗号分隔)")
    args = ap.parse_args()
    only = ({s.strip() for s in args.only.split(",")}
            if args.only else None)

    from algorithms.context_linking.evidence_recall import (
        EvidenceStore,
        MultiHeadRecall,
        UnitFocusedRerank,
    )
    from algorithms.common import bge_local

    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    mode = rr.ensure()
    print(f"精排器: {mode}")

    # 编码器(按语言惰性加载复用)
    enc_cache: dict[str, object] = {}

    def encoder_for(lang: str):
        if lang not in enc_cache:
            if lang == "en":
                enc_cache[lang] = bge_local.BgeLocal(
                    model_dir=EN_MODEL, cache_path=EN_CACHE)
            else:
                enc_cache[lang] = bge_local.BgeLocal(cache_path=None)
            enc_cache[lang].ensure()
        return enc_cache[lang]

    report = {}
    for name, fname, lang, n_q, pool, ref in DATASETS:
        if only and name not in only:
            continue
        ds = json.loads((V3 / fname).read_text(encoding="utf-8"))
        corpus = ds["corpus"]
        queries = ds["queries"]
        rng = np.random.default_rng(42)
        sel = rng.permutation(len(queries))[:n_q] if n_q < len(queries) \
            else list(range(len(queries)))
        qs = [queries[i] for i in sel]
        golds = [set(q["expected"]) for q in qs]
        print(f"\n[{name}] {len(corpus)}corpus {len(qs)}q lang={lang} "
              f"pool={pool}", flush=True)

        t0 = time.time()
        enc = encoder_for(lang)
        prefix = EN_PREFIX if lang == "en" else None
        store = EvidenceStore.from_ure(corpus)
        if prefix is not None:
            rc = MultiHeadRecall(store, enc, prefix=prefix)
        else:
            rc = MultiHeadRecall(store, enc)
        stage2 = UnitFocusedRerank(reranker=rr, unit_topn=2, blend=0.1)
        print(f"  物证库+多头构建: {store.n_owners}owner "
              f"{store.n_units}单元 ({time.time()-t0:.0f}s)", flush=True)

        t0 = time.time()
        recall_orders, rerank_orders = [], []
        recall_hits1, rerank_hits1 = [], []
        for qi, q in enumerate(qs):
            r50 = rc.recall(q["query"], pool=pool, topk=50)
            recall_orders.append([h.owner for h in r50.hits[:10]])
            recall_hits1.append(
                1 if (r50.hits and r50.hits[0].owner in golds[qi]) else 0)
            rr_hits = stage2.rerank(q["query"], r50, store)[:10]
            rerank_orders.append([h.owner for h in rr_hits])
            rerank_hits1.append(
                1 if (rr_hits and rr_hits[0].owner in golds[qi]) else 0)
            if (qi + 1) % 200 == 0:
                print(f"  {qi+1}/{len(qs)} ({time.time()-t0:.0f}s)",
                      flush=True)

        entry = {
            "n_queries": len(qs), "language": lang, "pool": pool,
            "recall": metrics_from_orders(recall_orders, golds),
            "rerank": metrics_from_orders(rerank_orders, golds),
            "mcnemar": mcnemar(recall_hits1, rerank_hits1),
        }
        print(f"  recall: R@1={entry['recall']['R@1']:.4f} "
              f"R@5={entry['recall']['R@5']:.4f} "
              f"MRR={entry['recall']['MRR@10']:.4f}")
        print(f"  rerank: R@1={entry['rerank']['R@1']:.4f} "
              f"R@5={entry['rerank']['R@5']:.4f} "
              f"MRR={entry['rerank']['MRR@10']:.4f} "
              f"(p={entry['mcnemar']['p_one_sided']:.1e})")
        checks = {}
        for key, val in ref.items():
            got = (entry["rerank"]["R@1"] if "rerank" in key
                   else entry["recall"]["R@1"])
            checks[key] = {"locked": val,
                           "framework": round(got, 4),
                           "delta": round(got - val, 4)}
        entry["locked_check"] = checks
        report[name] = entry

    outp = RESULTS / "S8_evidence_recall_external.json"
    outp.write_text(json.dumps({
        "protocol": ("evidence_recall框架×4外部数据集(语言匹配协议): "
                     "en=bge-base-en-v1.5+EN前缀, zh=bge-large-zh; "
                     "recall=O1-unit数学, rerank=unit2+b0.1+top50; "
                     "采样seed42"),
        "results": report,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {outp}")

    from run_utils import open_run
    handle = open_run("eval_evidence_recall_external", {
        "framework": "algorithms.context_linking.evidence_recall",
        "datasets": [d[0] for d in DATASETS if not only or d[0] in only],
        "rerank": "unit_topn=2, blend=0.1, topk=50",
    })
    handle.save_result(report)
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
