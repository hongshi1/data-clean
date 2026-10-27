"""三模块上下文关联系统端到端评测(1055条评测集×4-fold×16文档).

架构: ContextPipeline = MFE(特征提取) → SAA(自注意力关联) → CR(上下文重建)

评测: evalset_v2(1055条, user_sim 105 + param_v2 650 + legacy 300)
  4-fold文档交叉验证; 每fold训练侧/测试侧严格分离.

用法: python tools/eval_context_pipeline.py [--alpha 0.5] [--limit 200]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.context_pipeline import ContextPipeline  # noqa: E402
from run_utils import open_run  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
EVALSET = BASE / "data/gjb_438c/data_assets/evalset_v3.json"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"


def metrics_from_ranks(ranks: dict[str, int], targets: dict[str, set],
                       n_candidates: int) -> dict:
    r1 = r5 = r10 = r20 = 0
    rr = 0.0
    for qid, first in ranks.items():
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        r20 += first <= 20
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(ranks), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "R@20": round(r20 / n, 4),
            "MRR@10": round(rr / n, 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--alpha", type=float, default=0.5)
    ap.add_argument("--limit", type=int, default=300,
                    help="每fold评测条数")
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    images = [c for c in chunks if c.get("type") == "image"]
    eval_data = json.loads(EVALSET.read_text(encoding="utf-8"))

    # VLM转写(图像→文字): 用srs_image_analyses的key_elements
    vlm_path = BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"
    vlm_trans = {}
    if vlm_path.exists():
        img_analyses = json.loads(vlm_path.read_text(encoding="utf-8"))
        analyses = img_analyses.get("analyses", [])
        for a in analyses:
            img_path = a.get("image_path", "")
            key_elements = a.get("analysis", {}).get("key_elements", [])
            caption = " ".join(a.get("caption", []))
            # 从image_path推断chunk_id
            for c in images:
                if c.get("image_path", "") in img_path:
                    vlm_trans[c["chunk_id"]] = (
                        caption + " " + " ".join(key_elements))[:300]
                    break
    # BGE缓存(预计算的嵌入向量)
    with open(DENSE_CACHE, "rb") as f:
        bge_cache: dict[str, list[float]] = pickle.load(f)

    # 假想查询→通过章节归属映射到同章节的图片
    hq = json.loads(DOC_QUERIES.read_text(encoding="utf-8"))
    v2 = json.loads(PARAM_V2.read_text(encoding="utf-8"))
    text_hq: dict[str, list[str]] = defaultdict(list)
    for cid, rec in hq.items():
        qs = rec if isinstance(rec, list) else rec.get("queries", [])
        text_hq[cid].extend(qs[:2])
    for cid, rec in v2.items():
        qs = rec if isinstance(rec, list) else [rec.get("query", "")]
        text_hq[cid].extend([q for q in qs if q][:1])
    # chunk_id→text chunk的章节映射, 然后把text的假想查询传给同章节的image
    doc_queries: dict[str, list[str]] = defaultdict(list)
    for img in images:
        key = (img["doc"][:2], img.get("section", ""))
        for c in chunks:
            if c.get("type") == "text" and \
                    (c["doc"][:2], c.get("section", "")) == key:
                doc_queries[img["chunk_id"]].extend(
                    text_hq.get(c["chunk_id"], [])[:2])

    FOLD_MAP = {}
    for i, d in enumerate(range(1, 17)):
        FOLD_MAP[f"{d:02d}"] = i % 4

    all_results = defaultdict(lambda: defaultdict(list))

    for fold in range(4):
        print(f"\n{'=' * 60}")
        fold_docs = sorted(d for d, f in FOLD_MAP.items() if f == fold)
        print(f"FOLD {fold} (测试: {fold_docs})")
        print(f"{'=' * 60}")

        test_qs = [q for q in eval_data if q["fold"] == fold][:args.limit]
        test_imgs = [c for c in images if FOLD_MAP[c["doc"][:2]] == fold]
        targets = {q["query"]: set(q["expected"]["chunk_ids"])
                   for q in test_qs}
        if not test_qs or not test_imgs:
            continue
        print(f"  测试: {len(test_qs)}q × {len(test_imgs)}图")

        # α选择: 在该fold的前2/3查询上选最优α, 后1/3验证(P5修复)
        n_total = len(test_qs)
        n_train = int(n_total * 2 / 3)
        # 实体组边界对齐
        while n_train < n_total and test_qs[n_train].get("entity") == \
                test_qs[n_train - 1].get("entity"):
            n_train += 1
        train_qs = test_qs[:n_train]
        val_qs = test_qs[n_train:]
        if not val_qs:
            val_qs = test_qs[-max(1, n_total // 10):]

        # 在训练段选α
        best_alpha = args.alpha
        best_score = -1
        for a_try in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
            pipe_t = ContextPipeline(alpha=a_try)
            pipe_t.build_index(test_imgs, vlm_trans, doc_queries,
                               cached_embeddings=bge_cache)
            ranks_t: dict[str, int] = {}
            for q in train_qs[:min(50, len(train_qs))]:
                res = pipe_t.process(q["query"])
                ev = [e.chunk_id for e in res.evidences]
                first = len(test_imgs) + 1
                for eid in targets.get(q["query"], set()):
                    if eid in ev:
                        first = min(first, ev.index(eid) + 1)
                ranks_t[q["query"]] = first
            hit5 = sum(1 for f in ranks_t.values() if f <= 5)
            sc = hit5 / max(len(ranks_t), 1)
            if sc > best_score:
                best_score = sc
                best_alpha = a_try
        print(f"  fold{fold}最优α={best_alpha}(train R@5={best_score:.3f})")

        # 用选定α在验证段评测
        pipe = ContextPipeline(alpha=best_alpha)
        n = pipe.build_index(test_imgs, vlm_trans, doc_queries,
                             cached_embeddings=bge_cache)
        ranks: dict[str, int] = {}
        t0 = time.time()
        for q in val_qs:
            result = pipe.process(q["query"])
            # 找期望chunk在结果中的排名
            ev_ids = [e.chunk_id for e in result.evidences]
            first = n + 1
            for exp_id in targets.get(q["query"], set()):
                if exp_id in ev_ids:
                    first = min(first, ev_ids.index(exp_id) + 1)
            ranks[q["query"]] = first
        m = metrics_from_ranks(ranks, targets, len(test_imgs))
        all_results[fold]["pipeline"].append(m)
        print(f"  val({len(val_qs)}q): R@5={m['R@5']:.3f} "
              f"R@10={m['R@10']:.3f} MRR={m['MRR@10']:.3f} "
              f"({time.time() - t0:.0f}s)")

        # 对照: 纯Text-Bridge(在相同验证段)
        pipe_b = ContextPipeline(alpha=1.0)  # alpha=1.0 → 纯bridge
        pipe_b.build_index(test_imgs, vlm_trans, doc_queries,
                           cached_embeddings=bge_cache)
        ranks_b: dict[str, int] = {}
        for q in val_qs:
            result = pipe_b.process(q["query"])
            ev_ids = [e.chunk_id for e in result.evidences]
            first = n + 1
            for exp_id in targets.get(q["query"], set()):
                if exp_id in ev_ids:
                    first = min(first, ev_ids.index(exp_id) + 1)
            ranks_b[q["query"]] = first
        m_b = metrics_from_ranks(ranks_b, targets, len(test_imgs))
        all_results[fold]["bridge_only"].append(m_b)

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"三模块流水线评测 (4-fold×16文档×{args.limit}q/fold)")
    print(f"{'=' * 60}")
    for name in ("pipeline", "bridge_only"):
        fold_res = []
        for f in range(4):
            if f in all_results and name in all_results[f]:
                fold_res.extend(all_results[f][name])
        if fold_res:
            avg = {k: round(np.mean([r[k] for r in fold_res]), 4)
                   for k in fold_res[0]}
            label = f"三模块(α={args.alpha})" if name == "pipeline" else "纯Text-Bridge"
            print(f"  {label:<20s} R@1={avg['R@1']:.3f} R@5={avg['R@5']:.3f} "
                  f"R@10={avg['R@10']:.3f} R@20={avg['R@20']:.3f} "
                  f"MRR={avg['MRR@10']:.3f}")

    run = open_run("eval_context_pipeline", {
        "alpha": args.alpha, "limit": args.limit,
        "evalset": "v2(1055条)"})
    run.save_result({
        "summary": {name: {k: round(np.mean([r[k] for r in
                        all_results[f][name]]), 4)
                    for k in all_results[f][name][0]}
                    for f in range(4) for name in ("pipeline", "bridge_only")
                    if f in all_results and name in all_results[f]},
        "config": {"alpha": args.alpha, "top_k": 20}})
    print(f"\n结果 → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
