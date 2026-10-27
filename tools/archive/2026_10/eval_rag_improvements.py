r"""RAG改进评测: docT5query索引 + HyDE查询改写 + 重排.

解决的核心问题: 问句型query与答案型文档在BGE空间的语义鸿沟
  query: "图4在哪章节"(问句向量) vs 候选: "3.2.1节定义了..."(答案向量)
  → 问句↔答案在BGE空间距离远 → 检索失败

三个RAG方法(按机制分工):
  M1 docT5query索引: 文档侧改造 — 给每个chunk预生成"假想查询"入索引,
    检索时query匹配假想查询(问句↔问句同类匹配)
  M2 HyDE: 查询侧改造 — LLM生成"假想答案", 用假想答案向量检索
    (答案↔答案同类匹配)
  M3 重排: 排序侧增强 — 交叉编码器对top-50精细打分

评测: 4-fold×16文档×673条(修复后协议, param_v2+user_sim为主)

用法: python tools/eval_rag_improvements.py [--limit 200]
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

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
EVALSET_V2 = BASE / "data/gjb_438c/data_assets/evalset_v2.json"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"


def metrics_from_scores(scores: dict, targets: dict, ids: list) -> dict:
    r1 = r5 = r10 = 0
    rr = 0.0
    for qid, mix in scores.items():
        order = np.argsort(-mix)
        rank = {ids[i]: k + 1 for k, i in enumerate(order)}
        first = min((rank[t] for t in targets[qid] if t in rank),
                    default=len(ids) + 1)
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(scores), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "MRR@10": round(rr / n, 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200,
                    help="评测查询数(每fold)")
    ap.add_argument("--skip-hyde", action="store_true",
                    help="跳过HyDE(LLM调用耗时)")
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    images = [c for c in chunks if c.get("type") == "image"]
    texts = [c for c in chunks if c.get("type") == "text" and c.get("text")]
    with open(DENSE_CACHE, "rb") as f:
        bge: dict[str, list[float]] = pickle.load(f)

    # 假想查询索引: text chunk的假想查询 → 按章节归属到同章节的图
    hq = json.loads(DOC_QUERIES.read_text(encoding="utf-8"))
    v2 = json.loads(PARAM_V2.read_text(encoding="utf-8")) \
        if PARAM_V2.exists() else {}
    # 构建text chunk→假想查询列表
    text_hq: dict[str, list[str]] = defaultdict(list)
    for cid, rec in hq.items():
        qs = rec if isinstance(rec, list) else rec.get("queries", [])
        text_hq[cid].extend(qs[:2])
    for cid, rec in v2.items():
        qs = rec if isinstance(rec, list) else [rec.get("query", "")]
        text_hq[cid].extend([q for q in qs if q][:1])
    # 按章节把text chunk的假想查询映射到同章节的image
    img_queries: dict[str, list[str]] = defaultdict(list)
    for img in images:
        key = (img["doc"][:2], img.get("section", ""))
        for t in texts:
            if (t["doc"][:2], t.get("section", "")) == key:
                img_queries[img["chunk_id"]].extend(
                    text_hq.get(t["chunk_id"], [])[:2])
    print(f"docT5query索引: {len(img_queries)}图"
          f"×{sum(len(v) for v in img_queries.values())}查询")

    # 4-fold
    FOLD_MAP = {}
    for i, d in enumerate(range(1, 17)):
        FOLD_MAP[f"{d:02d}"] = i % 4
    eval_data = json.loads(EVALSET_V2.read_text(encoding="utf-8"))

    # BGE在线编码(query需要编码——不是从缓存取, 因为query是新文本)
    from algorithms.common.bge_local import BgeLocal
    bge_model = BgeLocal(cache_path=None)
    mode = bge_model.ensure()
    print(f"BGE(在线编码): {mode}")

    all_results = defaultdict(lambda: defaultdict(list))

    for fold in range(4):
        print(f"\n{'='*60}")
        fold_docs = sorted(d for d, f in FOLD_MAP.items() if f == fold)
        print(f"FOLD {fold} (测试: {fold_docs})")
        print(f"{'='*60}")

        test_qs = [q for q in eval_data if q["fold"] == fold][:args.limit]
        test_images = [c for c in images if FOLD_MAP[c["doc"][:2]] == fold]
        ids = [c["chunk_id"] for c in test_images]
        targets = {q["query"]: set(q["expected"]["chunk_ids"])
                   for q in test_qs}
        print(f"测试: {len(test_qs)}q × {len(test_images)}图")
        if not test_qs or not test_images:
            continue

        # ═══ 基线: Text-Bridge(query BGE vs image VLM转写BGE) ═══
        mat_vlm = np.stack([np.asarray(bge.get(
            c["chunk_id"], [0.0] * 1024), dtype=np.float32)
            for c in test_images])
        mn = mat_vlm / np.maximum(
            np.linalg.norm(mat_vlm, axis=1, keepdims=True), 1e-8)
        bridge_scores: dict[str, np.ndarray] = {}
        t0 = time.time()
        query_texts = [q["query"] for q in test_qs]
        q_vecs = bge_model.embed(query_texts)
        for q, vec in zip(query_texts, q_vecs.values()):
            v = np.asarray(vec, dtype=np.float32)
            if np.linalg.norm(v) < 1e-8:
                continue
            bridge_scores[q] = mn @ (v / np.linalg.norm(v))
        R = all_results[fold]
        R["baseline_bridge"].append(metrics_from_scores(
            bridge_scores, targets, ids))
        print(f"  baseline: {time.time() - t0:.1f}s")

        # ═══ M1: docT5query索引(query BGE vs image假想查询BGE) ═══
        dq_scores: dict[str, np.ndarray] = {}
        t0 = time.time()
        # 批量编码所有测试图的假想查询
        hq_texts = []
        hq_map = []  # (image_idx, query_text)
        for i, c in enumerate(test_images):
            for q in img_queries.get(c["chunk_id"], []):
                hq_texts.append(q)
                hq_map.append(i)
        if hq_texts:
            hq_vecs = bge_model.embed(hq_texts)
            # 构建分数: 每张图取其假想查询与query的最高cos
            dq_scores: dict[str, np.ndarray] = {}
            hq_mat = np.stack([np.asarray(hq_vecs.get(
                t, [0.0] * 1024), dtype=np.float32) for t in hq_texts])
            hq_mat = hq_mat / np.maximum(
                np.linalg.norm(hq_mat, axis=1, keepdims=True), 1e-8)
            for q in query_texts:
                v = q_vecs.get(q)
                if not v or np.linalg.norm(v) < 1e-8:
                    continue
                vn = np.asarray(v, dtype=np.float32)
                vn = vn / np.linalg.norm(vn)
                sims = hq_mat @ vn  # (n_hq,)
                # 按图聚合取max
                per_img = np.full(len(test_images), -1.0)
                for hi, img_idx in enumerate(hq_map):
                    if sims[hi] > per_img[img_idx]:
                        per_img[img_idx] = sims[hi]
                dq_scores[q] = per_img
            R["M1_doct5query"].append(metrics_from_scores(
                dq_scores, targets, ids))
            print(f"  M1 docT5query: {time.time() - t0:.1f}s")
        else:
            print("  M1: 无假想查询索引(跳过)")

        # ═══ M2: HyDE(LLM生成假想答案→用假想答案向量检索) ═══
        if not args.skip_hyde:
            from algorithms.common.llm_client import llm_chat
            t0 = time.time()
            hyde_scores: dict[str, np.ndarray] = {}
            n_llm = 0
            for q in test_qs[:min(50, len(test_qs))]:  # 前50条(控制LLM成本)
                query = q["query"]
                if query not in bridge_scores:
                    continue
                # HyDE prompt: 生成假想答案
                prompt = (f"请根据以下问题, 写出一段可能的文档内容作为答案"
                          f"(50-100字, 模拟GJB需求文档的写作风格):\n{query}")
                try:
                    ans, _ = llm_chat(prompt, cache=True, prefer="glm")
                    n_llm += 1
                except (RuntimeError, OSError):
                    ans = query  # LLM失败则退化为原始query
                # 用假想答案的BGE向量检索
                av = bge_model.embed([ans[:300]])
                av = np.asarray(av.get(ans[:300], [0.0] * 1024),
                                dtype=np.float32)
                if np.linalg.norm(av) < 1e-8:
                    hyde_scores[query] = bridge_scores[query]
                    continue
                an = av / np.linalg.norm(av)
                hyde_scores[query] = mn @ an
            # 只评有HyDE结果的
            hyde_targets = {q: targets[q] for q in hyde_scores
                            if q in targets}
            if hyde_scores:
                R["M2_hyde"].append(metrics_from_scores(
                    hyde_scores, hyde_targets, ids))
            print(f"  M2 HyDE: {time.time() - t0:.1f}s ({n_llm}次LLM)")

        # ═══ M1+基线融合: docT5query与Text-Bridge互补 ═══
        if dq_scores:
            fused: dict[str, np.ndarray] = {}
            for q in query_texts:
                if q not in bridge_scores:
                    continue
                bs = bridge_scores[q]
                ds = dq_scores.get(q, np.zeros_like(bs))
                # z-score融合
                zs_b = (bs - bs.mean()) / (bs.std() if bs.std() > 1e-8 else 1)
                zs_d = (ds - ds.mean()) / (ds.std() if ds.std() > 1e-8 else 1)
                fused[q] = 0.5 * zs_b + 0.5 * zs_d
            R["M1_baseline_fusion"].append(metrics_from_scores(
                fused, targets, ids))
            print("  M1+baseline融合: done")

    # ═══ 汇总 ═══
    print(f"\n{'='*60}")
    print(f"RAG改进评测汇总 (4-fold, {args.limit}q/fold)")
    print(f"{'='*60}")
    order = ["baseline_bridge", "M1_doct5query", "M2_hyde",
             "M1_baseline_fusion"]
    labels = {"baseline_bridge": "Text-Bridge(基线)",
              "M1_doct5query": "M1 docT5query",
              "M2_hyde": "M2 HyDE",
              "M1_baseline_fusion": "M1+基线融合"}
    print(f"  {'方法':<24s} R@1    R@5    R@10   MRR@10")
    final = {}
    for k in order:
        fold_res = []
        for f in range(4):
            if f in all_results and k in all_results[f]:
                fold_res.extend(all_results[f][k])
        if not fold_res:
            continue
        avg = {m: round(np.mean([r[m] for r in fold_res]), 4)
               for m in fold_res[0]}
        final[k] = avg
        print(f"  {labels.get(k, k):<24s} {avg['R@1']:.3f}  {avg['R@5']:.3f}  "
              f"{avg['R@10']:.3f}  {avg['MRR@10']:.3f}")

    out = BASE / "data/gjb_438c/trimodal/rag_improvements_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "protocol": f"4-fold, {args.limit}q/fold, 16 docs",
        "results": final}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
