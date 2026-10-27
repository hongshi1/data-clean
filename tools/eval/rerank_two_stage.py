r"""两阶段评测: O1-unit召回 top-K + BGE-Reranker-v2-m3 重排.

针对L4(语体鸿沟)主瓶颈的免训练方案:
  Stage 1: O1-unit(IDF加权max-unit) — 召回top-K
  Stage 2: cross-encoder重排(直接建模query-doc交互, 无需训练对)

  "语义赢家"型失败(cos gap 0.02-0.07)正是cross-encoder强项.

用法: python tools/eval/rerank_two_stage.py [--topk 20]
"""
from __future__ import annotations

import argparse
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
PREFIX = "为这个句子生成表示以用于检索相关文章："


def o1_unit_topk(queries, pool, idx, k, bge, device):
    """Stage 1: O1-unit打分, 返回(top-k列表, 全部分数, 单元相似度, seg, 单元文本)."""
    raw_units = [[u for u in ([c["title"]] + c["units"]) if u]
                 for c in pool]
    unit_texts = [u for ru in raw_units for u in ru]
    seg = np.cumsum([0] + [len(ru) for ru in raw_units])
    n = len(pool)

    uvecs = bge.embed(unit_texts)
    U = np.stack([np.asarray(uvecs.get(u, [0.0] * 1024),
                             dtype=np.float32) for u in unit_texts])
    U = U / np.maximum(np.linalg.norm(U, axis=1, keepdims=True), 1e-8)

    dfc: dict[str, int] = {}
    for ru in raw_units:
        for u in set(ru):
            dfc[u] = dfc.get(u, 0) + 1
    idf = np.asarray(
        [np.log(1 + n / max(dfc.get(u, 1), 1)) for u in unit_texts],
        dtype=np.float32)

    Ut = torch.as_tensor(U, dtype=torch.float32).to(device)
    q_texts = [PREFIX + q["query"][:200] for q in queries]
    qvecs = bge.embed(q_texts)
    all_scores = []
    topk_lists = []
    all_usims = []  # 单元级相似度(全局矩阵太大→按查询存列)
    with torch.no_grad():
        for i, qt in enumerate(q_texts):
            v = qvecs.get(qt)
            if not v:
                all_scores.append(np.full(n, -1e9, dtype=np.float32))
                topk_lists.append([])
                all_usims.append(None)
                continue
            qn = torch.as_tensor(np.asarray(v, dtype=np.float32)).to(device)
            qn = qn / max(float(qn.norm()), 1e-8)
            sims_u = (Ut @ qn).cpu().numpy() * idf
            segmax = np.asarray(
                [sims_u[seg[j]:seg[j + 1]].max() if seg[j] < seg[j + 1]
                 else -1e9 for j in range(n)])
            all_scores.append(segmax)
            topk_lists.append(list(np.argsort(-segmax)[:k]))
            all_usims.append(sims_u)
    return topk_lists, all_scores, all_usims, seg, unit_texts


def rerank_stage(queries, pool, topk_lists, reranker, batch=16,
                 usims=None, seg=None, unit_texts=None, unit_topn=3,
                 blend=0.0, stage1_scores=None, docmode="unit"):
    """Stage 2: cross-encoder重排top-k.

    docmode=full: 全表序列化(已被证伪: 全表dump稀释目标行).
    docmode=unit: 每表取stage-1单元分最高的前unit_topn个单元拼接.
    docmode=unit-title: 标题+前unit_topn个单元(表级上下文).
    blend>0时最终分 = rerank分 + blend×标准化stage1分.
    """
    final_orders = []
    t0 = time.time()
    done = 0
    for qi, q in enumerate(queries):
        cand = topk_lists[qi]
        if not cand:
            final_orders.append([])
            continue
        doc_texts = []
        for ci in cand:
            if usims is not None and usims[qi] is not None:
                # 单元聚焦: 表内单元按stage-1分数取top-n
                s, e = int(seg[ci]), int(seg[ci + 1])
                uu = unit_texts[s:e]
                ss = usims[qi][s:e]
                top_u = [u for _, u in sorted(zip(ss, uu),
                                              reverse=True)[:unit_topn]]
                if docmode == "unit-title":
                    doc = pool[ci]["title"] + " ; " + " ; ".join(top_u)
                else:
                    doc = " ; ".join(top_u)
            else:
                c = pool[ci]
                doc = c["title"] + " ; " + " ; ".join(c["units"])
            doc_texts.append(doc[:2000])
        pairs = [(q["query"], d) for d in doc_texts]
        scores = []
        for b0 in range(0, len(pairs), batch):
            scores.extend(reranker.score(pairs[b0:b0 + batch]))
        if blend > 0 and stage1_scores is not None:
            base = [float(stage1_scores[qi][ci]) for ci in cand]
            s_min, s_max = min(base), max(base)
            rng = max(s_max - s_min, 1e-8)
            base_n = [(b - s_min) / rng for b in base]
            r_min, r_max = min(scores), max(scores)
            rrng = max(r_max - r_min, 1e-8)
            comb = [sc + blend * bn / rrng * abs(r_max)
                    for sc, bn in zip(scores, base_n)]
            order = sorted(range(len(cand)),
                           key=lambda j: (-comb[j], j))
        else:
            order = sorted(range(len(cand)),
                           key=lambda j: (-scores[j], j))
        final_orders.append([cand[j] for j in order])
        done += 1
        if done % 50 == 0:
            el = time.time() - t0
            print(f"  重排 {done}/{len(queries)} ({el:.0f}s)", flush=True)
    return final_orders


def metrics_from_orders(orders, golds, n):
    """从排序列表计算R@1/5/10与MRR@10(未入列表者按末尾计)."""
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
            # 未进top-k: 视为未命中(MRR按>10处理)
            continue
        if hit_rank == 1:
            r1 += 1
        if hit_rank <= 5:
            r5 += 1
        if hit_rank <= 10:
            r10 += 1
        if hit_rank <= 10:
            mrr += 1.0 / hit_rank
    total = len(orders)
    return {"R@1": r1 / total, "R@5": r5 / total, "R@10": r10 / total,
            "MRR@10": mrr / total}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=50,
                    help="召回深度(标准协议=50)")
    ap.add_argument("--docmode", choices=["full", "unit", "unit-title"],
                    default="unit")
    ap.add_argument("--unit-topn", type=int, default=2,
                    help="精排文档单元数(标准协议=2)")
    ap.add_argument("--blend", type=float, default=0.1,
                    help="召回分融合权重(标准协议=0.1)")
    ap.add_argument("--mcnemar", action="store_true",
                    help="输出与stage1的McNemar b/c统计")
    ap.add_argument("--dataset", default="gjb_ure_v3.json",
                    help="V3目录下的数据集文件名")
    ap.add_argument("--scene", default="table_deep_v3",
                    help="场景名(逗号分隔支持多场景联合)")
    ap.add_argument("--out", default=None,
                    help="结果JSON文件名(默认按场景自动: S1/S5/S6)")
    args = ap.parse_args()

    ds = json.loads((V3 / args.dataset).read_text(encoding="utf-8"))
    scenes = {s.strip() for s in args.scene.split(",") if s.strip()}
    queries = [q for q in ds["queries"]
               if q["scene"] in scenes and q["split"] == "eval"]
    pool = [c for c in ds["corpus"] if c["type"] == "table"]
    idx = {c["chunk_id"]: i for i, c in enumerate(pool)}
    n = len(pool)
    golds = [{idx[t] for t in q["expected"] if t in idx} for q in queries]
    print(f"两阶段评测: {len(queries)}q, 池{n}表, top-{args.topk}")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal(cache_path=None)
    bge.ensure()

    print("Stage 1: O1-unit召回...", flush=True)
    t0 = time.time()
    topk_lists, all_scores, usims, seg, unit_texts = o1_unit_topk(
        queries, pool, idx, args.topk, bge, device)
    # Stage-1指标(top-k截断后)
    m1 = metrics_from_orders(topk_lists, golds, n)
    print(f"  Stage1@{args.topk}: R@1={m1['R@1']:.3f} R@5={m1['R@5']:.3f} "
          f"MRR={m1['MRR@10']:.3f} ({time.time()-t0:.0f}s)")

    print("Stage 2: BGE-Reranker-v2-m3重排...", flush=True)
    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    mode = rr.ensure()
    print(f"  reranker mode: {mode}, docmode={args.docmode}")
    t0 = time.time()
    if args.docmode in ("unit", "unit-title"):
        orders = rerank_stage(queries, pool, topk_lists, rr,
                              usims=usims, seg=seg,
                              unit_texts=unit_texts,
                              unit_topn=args.unit_topn,
                              blend=args.blend,
                              stage1_scores=all_scores,
                              docmode=args.docmode)
    else:
        orders = rerank_stage(queries, pool, topk_lists, rr,
                              blend=args.blend,
                              stage1_scores=all_scores,
                              docmode=args.docmode)
    m2 = metrics_from_orders(orders, golds, n)
    print(f"  Stage2: R@1={m2['R@1']:.3f} R@5={m2['R@5']:.3f} "
          f"R@10={m2['R@10']:.3f} MRR={m2['MRR@10']:.3f} "
          f"({time.time()-t0:.0f}s)")
    print(f"  ΔR@1 = {m2['R@1'] - m1['R@1']:+.3f}")

    # McNemar: 两系统在R@1上的不一致对(总是计算, 按需打印)
    b_cnt = c_cnt = 0
    for qi, (o1, o2) in enumerate(zip(topk_lists, orders)):
        g = golds[qi]
        hit_s1 = 1 if (o1 and o1[0] in g) else 0
        hit_s2 = 1 if (o2 and o2[0] in g) else 0
        if hit_s2 > hit_s1:
            b_cnt += 1
        elif hit_s1 > hit_s2:
            c_cnt += 1
    if b_cnt + c_cnt > 0:
        z = (b_cnt - c_cnt) / ((b_cnt + c_cnt) ** 0.5)
        p = 0.5 * (1 + math.erf(z / 2 ** 0.5))
        p_one = 1 - p if p > 0.5 else p
    else:
        z, p_one = 0.0, 1.0
    if args.mcnemar:
        print(f"  McNemar(vs stage1): b={b_cnt} c={c_cnt} "
              f"z={z:.2f} p(one-sided)={p_one:.2e}")

    # 归档(目标文件按场景自动选择, 可用--out覆盖)
    scene_out = args.out
    if scene_out is None:
        if scenes == {"table_deep_v3"}:
            scene_out = "S1_deep_v3_all.json"
        elif scenes == {"table_deep_v4"}:
            scene_out = "S5_deep_v4_all.json"
        elif scenes == {"table_deep_v3", "table_deep_v4"}:
            scene_out = "S6_deep_v34_all.json"
        else:
            scene_out = f"rerank_{'-'.join(sorted(scenes))}.json"
    outp = (BASE / "data/gjb_438c/data_assets/evalsets/results/"
            / scene_out)
    d = json.loads(outp.read_text(encoding="utf-8"))
    key = (f"O1-unit+Rerank@{args.topk}"
           + (f"({args.docmode}{args.unit_topn})" if args.docmode != "full"
              else "(full)")
           + (f",b{args.blend}" if args.blend > 0 else ""))
    d["results"][key] = m2
    if args.mcnemar:
        d["protocol"]["rerank_significance"] = (
            f"O1+Rerank vs O1: McNemar b={b_cnt} c={c_cnt}, "
            f"p={p_one:.2e}(one-sided)")
    outp.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"→ 已写入{scene_out}: {key}")

    from run_utils import open_run
    handle = open_run("rerank_two_stage", {
        "stage1": "O1-unit fixed-serialization",
        "stage2": "BGE-Reranker-v2-m3 cross-encoder",
        "topk": args.topk, "n_queries": len(queries),
        "docmode": args.docmode, "unit_topn": args.unit_topn,
        "scenes": sorted(scenes), "dataset": args.dataset,
    })
    handle.save_result({"stage1_metrics": m1, "stage2_metrics": m2,
                        "mcnemar": {"b": b_cnt, "c": c_cnt,
                                    "p_one_sided": p_one
                                    if args.mcnemar else None}})
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
