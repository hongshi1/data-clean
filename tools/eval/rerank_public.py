r"""公开数据集两阶段: O1-unit召回 + BGE-Reranker重排(外部效度).

验证GJB场景的单元聚焦重排(unit2)在英文公开数据集是否复现:
  Stage 1: O1-unit(bge-base-en-v1.5, 语言匹配协议, 同eval_public_en.py)
  Stage 2: BGE-Reranker-v2-m3, doc=stage-1单元分top-2拼接

用法: python tools/eval/rerank_public.py [--n-queries 2000] [--topk 50]
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


def run_dataset(path: Path, label: str, bge, rr, n_queries, topk,
                unit_topn=2):
    ds = json.loads(path.read_text(encoding="utf-8"))
    corpus = ds["corpus"]
    queries = ds["queries"]
    rng = np.random.default_rng(42)
    sel = rng.permutation(len(queries))[:n_queries]
    sel_qs = [queries[i] for i in sel]
    ids = [c["chunk_id"] for c in corpus]
    idx = {cid: i for i, cid in enumerate(ids)}
    n = len(corpus)
    print(f"\n[{label}] {n}候选×{len(sel_qs)}查询, top-{topk}, unit{unit_topn}")

    raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                 for c in corpus]
    unit_texts = [u for ru in raw_units for u in ru]
    seg = np.cumsum([0] + [len(ru) for ru in raw_units])

    vecs = bge.embed(unit_texts)
    U = np.stack([np.asarray(vecs.get(u, [0.0] * 768), dtype=np.float32)
                  for u in unit_texts]).T
    U = U / np.maximum(np.linalg.norm(U, axis=0, keepdims=True), 1e-8)
    df: dict[str, int] = {}
    for ru in raw_units:
        for u in set(ru):
            df[u] = df.get(u, 0) + 1
    idf_u = np.asarray(
        [np.log(1 + n / max(df.get(u, 1), 1)) for u in unit_texts],
        dtype=np.float32)

    q_texts = [q["query"] for q in sel_qs]
    qvecs = bge.embed([EN_PREFIX + q[:200] for q in q_texts])
    Q = np.stack([np.asarray(qvecs.get(EN_PREFIX + q[:200],
                                       [0.0] * 768), dtype=np.float32)
                  for q in q_texts])
    Q = Q / np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-8)
    sims_u = (Q @ U) * idf_u[None, :]

    def seg_max_row(qi):
        out = np.full(n, -1e9, dtype=np.float32)
        for i in range(n):
            out[i] = sims_u[qi][seg[i]:seg[i + 1]].max()
        return out

    t0 = time.time()
    topk_lists, stage1_scores = [], []
    for qi in range(len(sel_qs)):
        s = seg_max_row(qi)
        stage1_scores.append(s)
        topk_lists.append(list(np.argsort(-s)[:topk]))
    orders_s1 = [list(np.argsort(-s)[:10]) for s in stage1_scores]
    golds = [{idx[t] for t in q["expected"] if t in idx} for q in sel_qs]
    m1 = metrics_from_orders(orders_s1, golds)
    print(f"  Stage1: R@1={m1['R@1']:.4f} R@5={m1['R@5']:.4f} "
          f"R@10={m1['R@10']:.4f} MRR={m1['MRR@10']:.4f} "
          f"({time.time()-t0:.0f}s)")

    t0 = time.time()
    final_orders = []
    batch = 16
    for qi, q in enumerate(sel_qs):
        cand = topk_lists[qi]
        if not cand:
            final_orders.append([])
            continue
        doc_texts = []
        for ci in cand:
            s, e = int(seg[ci]), int(seg[ci + 1])
            uu = unit_texts[s:e]
            ss = sims_u[qi][s:e]
            top_u = [u for _, u in sorted(zip(ss, uu),
                                          reverse=True)[:unit_topn]]
            doc_texts.append(" ; ".join(top_u)[:2000])
        pairs = [(q["query"], d) for d in doc_texts]
        scores = []
        for b0 in range(0, len(pairs), batch):
            scores.extend(rr.score(pairs[b0:b0 + batch]))
        order = sorted(range(len(cand)), key=lambda j: (-scores[j], j))
        final_orders.append([cand[j] for j in order])
        if (qi + 1) % 500 == 0:
            print(f"  重排 {qi+1}/{len(sel_qs)} ({time.time()-t0:.0f}s)",
                  flush=True)
    m2 = metrics_from_orders(final_orders, golds)
    print(f"  Stage2: R@1={m2['R@1']:.4f} R@5={m2['R@5']:.4f} "
          f"R@10={m2['R@10']:.4f} MRR={m2['MRR@10']:.4f} "
          f"({time.time()-t0:.0f}s)")
    print(f"  ΔR@1 = {m2['R@1'] - m1['R@1']:+.4f}")

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
          f"p={p_one:.2e}")
    return {"stage1": m1, "stage2": m2,
            "mcnemar": {"b": b_cnt, "c": c_cnt, "p_one_sided": p_one}}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-queries", type=int, default=2000)
    ap.add_argument("--topk", type=int, default=50)
    args = ap.parse_args()
    if not (EN_MODEL / "config.json").exists():
        print(f"英文模型缺失: {EN_MODEL}")
        sys.exit(1)

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(model_dir=EN_MODEL, cache_path=EN_CACHE)
    bge.ensure()

    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    print(f"reranker mode: {rr.ensure()}")

    fetaqa = run_dataset(V3 / "fetaqa_ure.json", "FeTaQA", bge, rr,
                         args.n_queries, args.topk)
    wtq = run_dataset(V3 / "wtq_ure.json", "WTQ", bge, rr,
                      args.n_queries, args.topk)

    outp = RESULTS / "public_rerank.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps({
        "protocol": (f"两阶段: O1-unit(bge-base-en)召回top-{args.topk} + "
                     "BGE-Reranker-v2-m3重排(doc=单元top2); "
                     f"{args.n_queries}q采样(seed42), 语言匹配协议"),
        "results": {"fetaqa": fetaqa, "wtq": wtq},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {outp}")

    from run_utils import open_run
    handle = open_run("rerank_public", {
        "stage1": "O1-unit bge-base-en-v1.5",
        "stage2": "BGE-Reranker-v2-m3 unit-top2",
        "topk": args.topk, "n_queries": args.n_queries,
    })
    handle.save_result({"fetaqa": fetaqa, "wtq": wtq})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
