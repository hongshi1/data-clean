r"""综合召回实验v2: 零训练方法×学习模型×注意力融合(完整矩阵).

关键创新点: 用docT5query假想查询作MLP的训练数据
  原训练: (同章节text, image)共现对——弱代理(章节内文本未必描述图)
  新训练: (假想查询文本, 同章节image)对——真实问句→图配对
         (LLM读文本生成的问题, 与图的关系更直接)

完整方法矩阵:
  零训练(BGE空间):
    B1 baseline      query BGE vs 图VLM转写 BGE
    B2 docT5query    query BGE vs 图假想查询 BGE
    B3 HyDE          假想答案 BGE vs 图VLM转写 BGE
    B4 HyDE+dq       假想答案 BGE vs 图假想查询 BGE
  学习模型(docT5query训练对):
    L1 MLP           MLP投影头, 问句→图训练
    L2 原型注意力    原型注意力投影头, 同训练对
  融合:
    F1 dq+HyDE       两路同型匹配的z-score融合
    F2 注意力门控    查询自适应α融合(最优零训练+最优学习)

评测: 4-fold×16文档×~170q/fold(修复后协议)

用法: python tools/eval_recall_v3.py [--limit 170] [--epochs 40]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.trimodal import TrainConfig  # noqa: E402
from algorithms.trimodal import TrimodalContrastiveTrainer  # noqa: E402
from algorithms.trimodal.clip_encoder import ChineseClipEncoder  # noqa: E402
from algorithms.trimodal.gating import QueryGatingFusion  # noqa: E402
from algorithms.trimodal.proto_attention import (  # noqa: E402
    ProtoAttentionProjector,
    kmeans_prototypes,
)

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
EVALSET_V2 = BASE / "data/gjb_438c/data_assets/evalset_v2.json"
DOC_QUERIES = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries.json"
PARAM_V2 = BASE / "data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json"
IMG_DIM = 512 + 1024


def metrics_from_scores(scores: dict, targets: dict, ids: list) -> dict:
    r1 = r5 = r10 = r20 = 0
    rr = 0.0
    for qid, mix in scores.items():
        order = np.argsort(-mix)
        rank = {ids[i]: k + 1 for k, i in enumerate(order)}
        first = min((rank[t] for t in targets[qid] if t in rank),
                    default=len(ids) + 1)
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        r20 += first <= 20
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(scores), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "R@20": round(r20 / n, 4),
            "MRR@10": round(rr / n, 4)}


def zscore_col(x: np.ndarray) -> np.ndarray:
    s = (x - x.mean()) / (x.std() if x.std() > 1e-8 else 1.0)
    return s


def query_features(query: str) -> np.ndarray:
    q = (query or "").strip()
    chars = [c for c in q if not c.isspace()]
    n = len(chars)
    cjk = sum(1 for c in chars if "\u4e00" <= c <= "\u9fff")
    entity_ness = min(n / 12.0, 1.0) * (cjk / n if n else 0.0)
    fig_tab = 1.0 if any(k in q for k in ("图", "表", "曲线", "截图")) else 0.0
    has_id = 1.0 if any(c.isupper() and c != " " for c in q[:20]) else 0.0
    return np.array([entity_ness, fig_tab, has_id])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=170)
    ap.add_argument("--epochs", type=int, default=40)
    args = ap.parse_args()

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    images = [c for c in chunks if c.get("type") == "image"]
    texts = [c for c in chunks if c.get("type") == "text" and c.get("text")]
    with open(DENSE_CACHE, "rb") as f:
        bge: dict[str, list[float]] = pickle.load(f)

    # docT5query数据(作索引+作训练对)
    hq = json.loads(DOC_QUERIES.read_text(encoding="utf-8"))
    v2 = json.loads(PARAM_V2.read_text(encoding="utf-8"))
    text_hq: dict[str, list[str]] = defaultdict(list)
    for cid, rec in hq.items():
        qs = rec if isinstance(rec, list) else rec.get("queries", [])
        text_hq[cid].extend(qs[:2])
    for cid, rec in v2.items():
        qs = rec if isinstance(rec, list) else [rec.get("query", "")]
        text_hq[cid].extend([q for q in qs if q][:1])

    # CLIP
    clip = ChineseClipEncoder()
    clip.ensure()
    img_vecs = {}
    for c in images:
        p = Path("data/gjb_438c/mineru_standard") / c["doc"] / "office" / \
            c.get("image_path", "")
        if p.is_file():
            img_vecs[c["chunk_id"]] = clip.image_embed_cached(str(p))
    clip.save_cache()
    images = [c for c in images if c["chunk_id"] in img_vecs]
    img_feat = {cid: np.concatenate([
        np.asarray(img_vecs[cid], dtype=np.float32),
        np.asarray(bge[cid], dtype=np.float32)]) for cid in img_vecs}

    from algorithms.common.bge_local import BgeLocal
    bge_model = BgeLocal(cache_path=None)
    bge_model.ensure()

    # 4-fold
    FOLD_MAP = {}
    for i, d in enumerate(range(1, 17)):
        FOLD_MAP[f"{d:02d}"] = i % 4
    eval_data = json.loads(EVALSET_V2.read_text(encoding="utf-8"))

    all_results = defaultdict(lambda: defaultdict(list))

    for fold in range(4):
        print(f"\n{'='*60}")
        print(f"FOLD {fold}")
        print(f"{'='*60}")
        test_qs = [q for q in eval_data if q["fold"] == fold][:args.limit]
        train_docs = {d for d, f in FOLD_MAP.items() if f != fold}
        test_imgs = [c for c in images if FOLD_MAP[c["doc"][:2]] == fold]
        ids = [c["chunk_id"] for c in test_imgs]
        targets = {q["query"]: set(q["expected"]["chunk_ids"])
                   for q in test_qs}
        if not test_qs or not test_imgs:
            continue
        print(f"测试: {len(test_qs)}q × {len(test_imgs)}图")

        # ═══ 离线矩阵: 图VLM转写 + 图假想查询 ═══
        mat_vlm = np.stack([np.asarray(bge.get(
            c["chunk_id"], [0.0] * 1024), dtype=np.float32)
            for c in test_imgs])
        mn_vlm = mat_vlm / np.maximum(
            np.linalg.norm(mat_vlm, axis=1, keepdims=True), 1e-8)
        # 图假想查询(同章节text chunk的hq)
        img_hq: dict[str, list[str]] = defaultdict(list)
        for img in test_imgs:
            key = (img["doc"][:2], img.get("section", ""))
            for t in texts:
                if (t["doc"][:2], t.get("section", "")) == key:
                    img_hq[img["chunk_id"]].extend(
                        text_hq.get(t["chunk_id"], [])[:2])
        hq_texts, hq_map = [], []
        for i, c in enumerate(test_imgs):
            for q in img_hq.get(c["chunk_id"], []):
                hq_texts.append(q)
                hq_map.append(i)
        mn_hq = None
        if hq_texts:
            hq_vecs = bge_model.embed(hq_texts)
            hq_mat = np.stack([np.asarray(hq_vecs.get(
                t, [0.0] * 1024), dtype=np.float32) for t in hq_texts])
            mn_hq = hq_mat / np.maximum(
                np.linalg.norm(hq_mat, axis=1, keepdims=True), 1e-8)

        # ═══ 查询侧向量 ═══
        query_texts = [q["query"] for q in test_qs]
        q_vecs = bge_model.embed(query_texts)
        qv_map = {q: np.asarray(v, dtype=np.float32)
                  for q, v in zip(query_texts, q_vecs.values())}

        # HyDE(缓存友好)
        from algorithms.common.llm_client import llm_chat
        hyde_map: dict[str, np.ndarray] = {}
        n_hyde = min(50, len(query_texts))
        for q in query_texts[:n_hyde]:
            prompt = (f"请根据以下问题, 写出一段可能的文档内容作为答案"
                      f"(50-100字, 模拟GJB需求文档的写作风格):\n{q}")
            try:
                ans, _ = llm_chat(prompt, cache=True, prefer="glm")
            except (RuntimeError, OSError):
                ans = q
            av = bge_model.embed([ans[:300]])
            av = np.asarray(av.get(ans[:300], [0.0] * 1024),
                            dtype=np.float32)
            if np.linalg.norm(av) >= 1e-8:
                hyde_map[q] = av / np.linalg.norm(av)

        # ═══ B1 baseline: query vs VLM转写 ═══
        R = all_results[fold]
        s1 = {}
        for q in query_texts:
            v = qv_map.get(q)
            if v is None or np.linalg.norm(v) < 1e-8:
                continue
            s1[q] = mn_vlm @ (v / np.linalg.norm(v))
        R["B1_baseline"].append(metrics_from_scores(s1, targets, ids))

        # ═══ B2 docT5query: query vs 图假想查询 ═══
        if mn_hq is not None:
            s2 = {}
            for q in query_texts:
                v = qv_map.get(q)
                if v is None or np.linalg.norm(v) < 1e-8:
                    continue
                sims = mn_hq @ (v / np.linalg.norm(v))
                per_img = np.full(len(test_imgs), -1.0)
                for hi, img_idx in enumerate(hq_map):
                    if sims[hi] > per_img[img_idx]:
                        per_img[img_idx] = sims[hi]
                s2[q] = per_img
            R["B2_doct5query"].append(metrics_from_scores(s2, targets, ids))

        # ═══ B3 HyDE: 假想答案 vs VLM转写 ═══
        s3 = {}
        for q in query_texts:
            hv = hyde_map.get(q)
            if hv is None:
                hv = qv_map.get(q)
                if hv is None or np.linalg.norm(hv) < 1e-8:
                    continue
                hv = hv / np.linalg.norm(hv)
            s3[q] = mn_vlm @ hv
        R["B3_hyde"].append(metrics_from_scores(s3, targets, ids))

        # ═══ B4 HyDE+dq: 假想答案 vs 图假想查询 ═══
        if mn_hq is not None:
            s4 = {}
            for q in query_texts:
                hv = hyde_map.get(q)
                if hv is None:
                    hv = qv_map.get(q)
                    if hv is None or np.linalg.norm(hv) < 1e-8:
                        continue
                    hv = hv / np.linalg.norm(hv)
                sims = mn_hq @ hv
                per_img = np.full(len(test_imgs), -1.0)
                for hi, img_idx in enumerate(hq_map):
                    if sims[hi] > per_img[img_idx]:
                        per_img[img_idx] = sims[hi]
                s4[q] = per_img
            R["B4_hyde_dq"].append(metrics_from_scores(s4, targets, ids))

        # ═══ 学习模型: docT5query训练对 ═══
        # 训练对: (假想查询文本, 同章节图)
        train_pairs = []
        for t in texts:
            if t["doc"][:2] not in train_docs:
                continue
            key = (t["doc"][:2], t.get("section", ""))
            sec_imgs = [c for c in images if c["doc"][:2] == key[0]
                        and c.get("section", "") == key[1]]
            for q in text_hq.get(t["chunk_id"], [])[:2]:
                for img in sec_imgs[:1]:
                    train_pairs.append((q, img["chunk_id"]))
        print(f"  docT5query训练对: {len(train_pairs)}")

        if len(train_pairs) >= 100:
            # 训练特征
            tr_feats = {}
            for q, iid in train_pairs:
                if q not in tr_feats and q in qv_map:
                    tr_feats[q] = qv_map[q]
                if iid not in tr_feats:
                    tr_feats[iid] = img_feat[iid]
            tr_mods = {k: ("image" if k in img_feat else "text")
                       for k in tr_feats}
            tr_pairs_ok = [(a, b) for a, b in train_pairs
                           if a in tr_feats and b in tr_feats]

            # L1: MLP(docT5query训练)
            cfg = TrainConfig(shared_dim=256, lr=1e-3, epochs=args.epochs,
                              batch_size=48, temperature=0.07)
            tp = TrimodalContrastiveTrainer(
                {"text": 1024, "image": IMG_DIM}, cfg)
            from algorithms.trimodal import PairSample
            tp.train(tr_feats, tr_mods,
                     [PairSample("text-image", a, b, confidence=0.9)
                      for a, b in tr_pairs_ok])
            sL1 = {}
            for q in query_texts:
                v = qv_map.get(q)
                if v is None:
                    continue
                zv = tp.projector.forward_numpy("text", v)
                mp = np.stack([tp.projector.forward_numpy(
                    "image", img_feat[c["chunk_id"]]) for c in test_imgs])
                mpn = mp / np.maximum(
                    np.linalg.norm(mp, axis=1, keepdims=True), 1e-8)
                sL1[q] = mpn @ (zv / np.linalg.norm(zv))
            R["L1_mlp_dq"].append(metrics_from_scores(sL1, targets, ids))
            print("  L1 MLP(dq训练): done")

            # L2: 原型注意力(docT5query训练)
            proto = kmeans_prototypes(
                np.stack([img_feat[iid] for iid in img_feat]), k=32)
            pa = ProtoAttentionProjector(
                {"text": 1024, "image": IMG_DIM}, proto, shared_dim=256)
            pa.fit({k: v for k, v in tr_feats.items() if k not in img_feat},
                   {k: v for k, v in tr_feats.items() if k in img_feat},
                   tr_pairs_ok, epochs=args.epochs)
            sL2 = {}
            for q in query_texts:
                v = qv_map.get(q)
                if v is None:
                    continue
                zv = pa.forward_numpy("text", v)
                mp = np.stack([pa.forward_numpy(
                    "image", img_feat[c["chunk_id"]]) for c in test_imgs])
                mpn = mp / np.maximum(
                    np.linalg.norm(mp, axis=1, keepdims=True), 1e-8)
                sL2[q] = mpn @ (zv / np.linalg.norm(zv))
            R["L2_proto_dq"].append(metrics_from_scores(sL2, targets, ids))
            print("  L2 原型注意力(dq训练): done")
        else:
            print("  (训练对不足, 跳过学习模型)")
            sL1 = {}
            sL2 = {}

        # ═══ F1: dq+HyDE融合(两路同型匹配) ═══
        if "B2_doct5query" in R and s2 and s3:
            fused = {}
            for q in query_texts:
                if q not in s2 or q not in s3:
                    continue
                fused[q] = 0.5 * zscore_col(s2[q]) + 0.5 * zscore_col(s3[q])
            R["F1_dq_hyde"].append(metrics_from_scores(fused, targets, ids))

        # ═══ F2: 注意力门控融合(最优零训练+最优学习) ═══
        best_zero = s2 if s2 else s1
        best_learn = sL1 if sL1 else (sL2 if sL2 else best_zero)
        if best_learn is not best_zero:
            gate = QueryGatingFusion()
            qfeats = np.stack([query_features(q) for q in query_texts
                               if q in best_zero and q in best_learn])
            zero_hits = np.array([1.0 if any(
                ids[i] in targets[q] for i in np.argsort(-best_zero[q])[:5])
                else 0.0 for q in query_texts
                if q in best_zero and q in best_learn])
            learn_hits = np.array([1.0 if any(
                ids[i] in targets[q] for i in np.argsort(-best_learn[q])[:5])
                else 0.0 for q in query_texts
                if q in best_zero and q in best_learn])
            if len(qfeats) >= 10:
                n_tr = len(qfeats) // 2
                gate.fit(qfeats[:n_tr], zero_hits[:n_tr], learn_hits[:n_tr])
                alphas = gate.predict(
                    qfeats[n_tr:],
                    np.array([best_zero[q].max() for q in query_texts
                              if q in best_zero and q in best_learn][n_tr:]),
                    np.array([best_learn[q].max() for q in query_texts
                              if q in best_zero and q in best_learn][n_tr:]))
                fused = {}
                qi = 0
                for q in query_texts:
                    if q not in best_zero or q not in best_learn:
                        continue
                    if qi >= n_tr and qi - n_tr < len(alphas):
                        a = float(alphas[qi - n_tr])
                    else:
                        a = 0.5
                    fused[q] = a * zscore_col(best_zero[q]) + \
                        (1 - a) * zscore_col(best_learn[q])
                    qi += 1
                R["F2_gated"].append(metrics_from_scores(fused, targets, ids))
                print("  F2 门控融合: done")

    # ═══ 汇总 ═══
    print(f"\n{'='*60}")
    print("综合召回实验汇总 (4-fold×16文档)")
    print(f"{'='*60}")
    order = ["B1_baseline", "B2_doct5query", "B3_hyde", "B4_hyde_dq",
             "L1_mlp_dq", "L2_proto_dq", "F1_dq_hyde", "F2_gated"]
    labels = {"B1_baseline": "B1 Text-Bridge(基线)",
              "B2_doct5query": "B2 docT5query",
              "B3_hyde": "B3 HyDE",
              "B4_hyde_dq": "B4 HyDE+docT5query",
              "L1_mlp_dq": "L1 MLP(dq训练)",
              "L2_proto_dq": "L2 原型注意力(dq训练)",
              "F1_dq_hyde": "F1 dq+HyDE融合",
              "F2_gated": "F2 注意力门控"}
    print(f"  {'方法':<26s} R@1    R@5    R@10   R@20   MRR@10")
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
        print(f"  {labels.get(k, k):<26s} {avg['R@1']:.3f}  {avg['R@5']:.3f}  "
              f"{avg['R@10']:.3f}  {avg['R@20']:.3f}  {avg['MRR@10']:.3f}")

    out = BASE / "data/gjb_438c/trimodal/recall_v3_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "protocol": "4-fold, 16 docs, evalset_v2",
        "results": final}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
