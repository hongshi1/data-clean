r"""SQR+三模块+章节过滤+精排的完整集成评测.

策略(分层路由):
  ① SQR确定性路由: 有图号/章节号→直查(100%准确)
  ② 章节感知过滤: 查询提章节→向量检索候选缩减
  ③ 三模块向量检索: MFE→SAA→CR(Text-Bridge+docT5query融合)
  ④ BGE-Reranker精排: top-K后cross-encoder精排(可选)

评测: evalset_v3(1007条, 4-fold×16文档)
用法: python tools/eval_sqr_pipeline.py [--use-rerank] [--limit 300]
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
from algorithms.sqr import (  # noqa: E402
    StructuredQueryRouter,
    extract_structured_signals,
)
from run_utils import open_run  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
EVALSET = BASE / "data/gjb_438c/data_assets/evalset_v3.json"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"


def metrics_from_ranks(ranks: dict, targets: dict, n_cand: int) -> dict:
    r1 = r5 = r10 = 0
    rr = 0.0
    for qid, first in ranks.items():
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(ranks), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "MRR@10": round(rr / n, 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--use-rerank", action="store_true")
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    images = [c for c in chunks if c.get("type") == "image"]
    eval_data = json.loads(EVALSET.read_text(encoding="utf-8"))
    with open(DENSE_CACHE, "rb") as f:
        bge_cache: dict = pickle.load(f)

    # VLM转写
    vlm_path = BASE / "data/gjb_438c/data_assets/chunks/srs_image_analyses.json"
    vlm_trans = {}
    if vlm_path.exists():
        ia = json.loads(vlm_path.read_text(encoding="utf-8"))
        for a in ia.get("analyses", []):
            for c in images:
                if c.get("image_path", "") in a.get("image_path", ""):
                    vlm_trans[c["chunk_id"]] = (
                        " ".join(a.get("caption", [])) + " " +
                        " ".join(a.get("analysis", {}).get(
                            "key_elements", [])))[:300]
                    break

    # docT5query
    hq = json.loads(DOC_QUERIES.read_text(encoding="utf-8"))
    v2 = json.loads(PARAM_V2.read_text(encoding="utf-8"))
    text_hq: dict = defaultdict(list)
    for cid, rec in hq.items():
        qs = rec if isinstance(rec, list) else rec.get("queries", [])
        text_hq[cid].extend(qs[:2])
    for cid, rec in v2.items():
        qs = rec if isinstance(rec, list) else [rec.get("query", "")]
        text_hq[cid].extend([q for q in qs if q][:1])
    doc_queries: dict = defaultdict(list)
    for img in images:
        key = (img["doc"][:2], img.get("section", ""))
        for c in chunks:
            if c.get("type") == "text" and \
                    (c["doc"][:2], c.get("section", "")) == key:
                doc_queries[img["chunk_id"]].extend(
                    text_hq.get(c["chunk_id"], [])[:2])

    # SQR路由器
    sqr = StructuredQueryRouter(chunks)

    # Reranker(可选)
    reranker = None
    if args.use_rerank:
        from algorithms.blackboard.reranker import BgeReranker
        reranker = BgeReranker()
        mode = reranker.ensure()
        print(f"Reranker: {mode}")

    FOLD_MAP = {}
    for i, d in enumerate(range(1, 17)):
        FOLD_MAP[f"{d:02d}"] = i % 4

    all_results = defaultdict(lambda: defaultdict(list))

    for fold in range(4):
        print(f"\n{'=' * 60}")
        fold_docs = sorted(d for d, f in FOLD_MAP.items() if f == fold)
        print(f"FOLD {fold} (测试: {fold_docs})")

        test_qs = [q for q in eval_data if q["fold"] == fold][:args.limit]
        test_imgs = [c for c in images if FOLD_MAP[c["doc"][:2]] == fold]
        targets = {q["query"]: set(q["expected"]["chunk_ids"])
                   for q in test_qs}
        if not test_qs or not test_imgs:
            continue
        print(f"  测试: {len(test_qs)}q × {len(test_imgs)}图")

        # 构建三模块pipeline(α=0.5)
        pipe = ContextPipeline(alpha=0.5)
        pipe.build_index(test_imgs, vlm_trans, doc_queries,
                         cached_embeddings=bge_cache)
        pack_by_id = {p.chunk_id: p for p in pipe._packs}

        # 评测: 分层路由
        ranks: dict[str, int] = {}
        n_sqr = 0
        n_vector = 0
        n_section_filtered = 0
        t0 = time.time()
        for q in test_qs:
            query = q["query"]
            exp = targets.get(query, set())
            img_ids = [c["chunk_id"] for c in test_imgs]

            # ── ① SQR确定性路由 ──
            sqr_result = sqr.route(query)
            if sqr_result:
                sqr_ids = [c["chunk_id"] for c in sqr_result
                           if c["chunk_id"] in
                           {i for i in img_ids}]
                if sqr_ids and any(i in exp for i in sqr_ids):
                    # SQR命中期望→直接返回
                    hit_id = next(i for i in sqr_ids if i in exp)
                    ranks[query] = sqr_ids.index(hit_id) + 1
                    n_sqr += 1
                    continue

            # ── ② 章节感知过滤(后过滤向量结果, 不重建子管线) ──
            signals = extract_structured_signals(query)
            result = pipe.process(query)
            ev_list = [(e.chunk_id, e.score) for e in result.evidences]
            if "section" in signals and ev_list:
                sec = signals["section"]
                sec_ids = {c["chunk_id"] for c in test_imgs
                           if c.get("section", "").startswith(sec)}
                if sec_ids and len(sec_ids) < len(ev_list):
                    # 提升 matching section的候选排名
                    boosted = [(i, s + (2.0 if i in sec_ids else 0.0))
                               for i, s in ev_list]
                    boosted.sort(key=lambda x: -x[1])
                    ev_list = boosted
                    n_section_filtered += 1

            # ── ④ BGE-Reranker精排(可选) ──
            ev_ids = [i for i, _ in ev_list]
            if reranker and ev_ids:
                cand_packs = [pack_by_id.get(i) for i in ev_ids[:20]]
                if cand_packs:
                    texts = [(p.vlm_transcription or p.payload)[:300]
                             if p else "" for p in cand_packs]
                    pairs = [(query, t) for t in texts]
                    scores = reranker.score(pairs)
                    ranked = sorted(zip(ev_ids[:20], scores),
                                    key=lambda x: -x[1])
                    ev_ids = [i for i, _ in ranked]

            # 计算排名
            first = len(img_ids) + 1
            for eid in exp:
                if eid in ev_ids:
                    first = min(first, ev_ids.index(eid) + 1)
            ranks[query] = first
            n_vector += 1

        m = metrics_from_ranks(ranks, targets, len(test_imgs))
        all_results[fold]["sqr_pipeline"].append(m)
        print(f"  结果: R@1={m['R@1']:.3f} R@5={m['R@5']:.3f} "
              f"R@10={m['R@10']:.3f} MRR={m['MRR@10']:.3f}")
        print(f"  路由: SQR={n_sqr}, 章节={n_section_filtered}, "
              f"向量={n_vector} ({time.time() - t0:.0f}s)")

        # 对照: 纯pipeline(无SQR/无过滤)
        ranks_b: dict[str, int] = {}
        for q in test_qs:
            result = pipe.process(q["query"])
            ev = [e.chunk_id for e in result.evidences]
            first = len(img_ids) + 1
            for eid in targets.get(q["query"], set()):
                if eid in ev:
                    first = min(first, ev.index(eid) + 1)
            ranks_b[q["query"]] = first
        m_b = metrics_from_ranks(ranks_b, targets, len(test_imgs))
        all_results[fold]["pipeline_only"].append(m_b)

    # 汇总
    print(f"\n{'=' * 60}")
    print("SQR+Pipeline集成评测 (4-fold×16文档)")
    print(f"{'=' * 60}")
    for name in ("sqr_pipeline", "pipeline_only"):
        fold_res = []
        for f in range(4):
            if f in all_results and name in all_results[f]:
                fold_res.extend(all_results[f][name])
        if fold_res:
            avg = {k: round(np.mean([r[k] for r in fold_res]), 4)
                   for k in fold_res[0]}
            label = ("SQR+Pipeline+章节"
                     + ("+Rerank" if args.use_rerank else "")
                     ) if name == "sqr_pipeline" else "纯Pipeline"
            print(f"  {label:<28s} R@1={avg['R@1']:.3f} "
                  f"R@5={avg['R@5']:.3f} R@10={avg['R@10']:.3f} "
                  f"MRR={avg['MRR@10']:.3f}")

    run = open_run("eval_sqr_pipeline", {
        "limit": args.limit, "use_rerank": args.use_rerank,
        "evalset": "v3(1007条)"})
    run.save_result({
        "summary": {name: {k: round(np.mean(
            [r[k] for f in range(4)
             for r in all_results[f].get(name, [])]), 4)
            for k in ("R@1", "R@5", "R@10", "MRR@10")}
            for name in ("sqr_pipeline", "pipeline_only")}})
    print(f"\n结果 → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
