r"""图文对齐四配置完整实验: 注意力模块增益验证.

四配置(双模态评测集: 100文本query×41图, doc13-16防泄漏, 同章节金标):
  C1 Text-Bridge      VLM转写→BGE同空间直比(零训练上界)
  C2 MLP投影头        CLIP+VLM拼接→MLP投影(对比学习基线)
  C3 原型注意力投影头  +k-means原型跨模态注意力(本实验的核心增量)
  C4 C3+训练增强      配对扩容(每图配5文本)+epoch加倍

指标: R@1/R@5/R@10/MRR@10 — 完整学术表格.

用法: python tools/eval_proto_attention.py [--epochs 60]
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

from algorithms.context_association.trimodal import PairSample, TrainConfig  # noqa: E402
from algorithms.context_association.trimodal.clip_encoder import ChineseClipEncoder  # noqa: E402
from algorithms.context_association.trimodal.proto_attention import (  # noqa: E402
    ProtoAttentionProjector,
    kmeans_prototypes,
)
from algorithms.context_association.trimodal import TrimodalContrastiveTrainer  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
TRAIN_DOCS = 12
IMG_DIM = 512 + 1024


def load_corpus():
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    texts = [c for c in chunks if c.get("type") == "text" and c.get("text")]
    images = [c for c in chunks if c.get("type") == "image"]
    return texts, images


def image_full_path(c: dict) -> Path | None:
    p = Path("data/gjb_438c/mineru_standard") / c["doc"] / "office" / \
        c.get("image_path", "")
    return p if p.is_file() else None


def metrics(q_vecs: dict[str, np.ndarray], targets: dict[str, set[str]],
            mat: np.ndarray, ids: list[str]) -> dict[str, float]:
    m = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
    r1 = r5 = r10 = 0
    rr = 0.0
    for qid, v in q_vecs.items():
        vn = v / max(np.linalg.norm(v), 1e-8)
        order = np.argsort(-(m @ vn))
        rank = {ids[i]: k + 1 for k, i in enumerate(order)}
        first = min((rank[t] for t in targets[qid] if t in rank),
                    default=len(ids) + 1)
        r1 += first <= 1
        r5 += first <= 5
        r10 += first <= 10
        rr += 1.0 / first if first <= 10 else 0.0
    n = max(len(q_vecs), 1)
    return {"R@1": round(r1 / n, 4), "R@5": round(r5 / n, 4),
            "R@10": round(r10 / n, 4), "MRR@10": round(rr / n, 4)}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=60)
    args = ap.parse_args()

    texts, images = load_corpus()
    with open(DENSE_CACHE, "rb") as f:
        bge: dict[str, list[float]] = pickle.load(f)

    clip = ChineseClipEncoder()
    mode = clip.ensure()
    print(f"CLIP: {mode}(缓存{len(clip._img_cache)})")
    img_vecs: dict[str, list[float]] = {}
    for c in images:
        p = image_full_path(c)
        if p is not None:
            img_vecs[c["chunk_id"]] = clip.image_embed_cached(str(p))
    clip.save_cache()
    images = [c for c in images if c["chunk_id"] in img_vecs]

    # 图像特征(拼接CLIP+VLM-BGE)与文本特征
    img_feat = {cid: np.concatenate([
        np.asarray(img_vecs[cid], dtype=np.float32),
        np.asarray(bge[cid], dtype=np.float32)])
        for cid in img_vecs}
    text_by_key: dict[tuple, list[dict]] = defaultdict(list)
    for c in texts:
        if c["chunk_id"] in bge:
            text_by_key[(c["doc"], c.get("section", ""))].append(c)
    # 配对: 标准版每图3文本 / 增强版每图5文本
    pairs_std, pairs_aug = [], []
    for c in images:
        cand = text_by_key.get((c["doc"], c.get("section", "")), [])
        for t in cand[:3]:
            pairs_std.append((t["chunk_id"], c["chunk_id"]))
        for t in cand[:5]:
            pairs_aug.append((t["chunk_id"], c["chunk_id"]))
    tr_std = [p for p in pairs_std if int(p[1].split("_")[0][:2]) <= TRAIN_DOCS]
    tr_aug = [p for p in pairs_aug if int(p[1].split("_")[0][:2]) <= TRAIN_DOCS]
    print(f"配对: 标准{len(pairs_std)}(训{len(tr_std)}) / "
          f"增强{len(pairs_aug)}(训{len(tr_aug)})")

    # 评测集
    test_texts = [t for t in texts if int(t["doc"][:2]) > TRAIN_DOCS
                  and t["chunk_id"] in bge]
    test_images = [c for c in images if int(c["doc"][:2]) > TRAIN_DOCS]
    targets: dict[str, set[str]] = {}
    for t in test_texts:
        key = (t["doc"], t.get("section", ""))
        targets[t["chunk_id"]] = {c["chunk_id"] for c in images
                                  if (c["doc"], c.get("section", "")) == key}
    test_texts = [t for t in test_texts if targets[t["chunk_id"]]]
    ids = [c["chunk_id"] for c in test_images]
    print(f"评测: {len(test_texts)}query × {len(test_images)}图")

    def t_feats(pairs):
        out = {}
        for a, b in pairs:
            if a not in out:
                out[a] = np.asarray(bge[a], dtype=np.float32)
            if b not in out:
                out[b] = img_feat[b]
        return out

    # ═══ C1: Text-Bridge ═══
    q_bge = {t["chunk_id"]: np.asarray(bge[t["chunk_id"]], dtype=np.float32)
             for t in test_texts}
    mat_vlm = np.stack([np.asarray(bge[c["chunk_id"]], dtype=np.float32)
                        for c in test_images])
    c1 = metrics(q_bge, targets, mat_vlm, ids)

    # ═══ C2: MLP投影头(复现) ═══
    t0 = time.time()
    cfg = TrainConfig(shared_dim=256, lr=1e-3, epochs=args.epochs,
                      batch_size=48, temperature=0.07)
    tp = TrimodalContrastiveTrainer({"text": 1024, "image": IMG_DIM}, cfg)
    f2 = t_feats(tr_std)
    mods = {k: ("image" if k in img_feat else "text") for k in f2}
    tp.train(f2, mods, [PairSample("text-image", a, b, confidence=0.7)
                        for a, b in tr_std])
    q2 = {t["chunk_id"]: tp.projector.forward_numpy(
        "text", np.asarray(bge[t["chunk_id"]], dtype=np.float32))
        for t in test_texts}
    m2 = np.stack([tp.projector.forward_numpy("image", img_feat[c["chunk_id"]])
                   for c in test_images])
    c2 = metrics(q2, targets, m2, ids)
    print(f"C2训练{time.time() - t0:.0f}s")

    # ═══ C3: 原型注意力投影头 ═══
    t0 = time.time()
    proto = kmeans_prototypes(
        np.stack([img_feat[cid] for cid in img_feat]), k=64)
    pa = ProtoAttentionProjector(
        {"text": 1024, "image": IMG_DIM}, proto, shared_dim=256)
    f3 = t_feats(tr_std)
    pa.fit({k: v for k, v in f3.items() if k not in img_feat},
           {k: v for k, v in f3.items() if k in img_feat}, tr_std,
           epochs=args.epochs)
    q3 = {t["chunk_id"]: pa.forward_numpy(
        "text", np.asarray(bge[t["chunk_id"]], dtype=np.float32))
        for t in test_texts}
    m3 = np.stack([pa.forward_numpy("image", img_feat[c["chunk_id"]])
                   for c in test_images])
    c3 = metrics(q3, targets, m3, ids)
    print(f"C3训练{time.time() - t0:.0f}s | loss {pa.history[0]:.3f}"
          f"→{pa.history[-1]:.3f}")

    # ═══ C4: C3+训练增强(5文本/图+epoch加倍) ═══
    t0 = time.time()
    pa4 = ProtoAttentionProjector(
        {"text": 1024, "image": IMG_DIM}, proto, shared_dim=256)
    f4 = t_feats(tr_aug)
    pa4.fit({k: v for k, v in f4.items() if k not in img_feat},
            {k: v for k, v in f4.items() if k in img_feat}, tr_aug,
            epochs=args.epochs * 2)
    q4 = {t["chunk_id"]: pa4.forward_numpy(
        "text", np.asarray(bge[t["chunk_id"]], dtype=np.float32))
        for t in test_texts}
    m4 = np.stack([pa4.forward_numpy("image", img_feat[c["chunk_id"]])
                   for c in test_images])
    c4 = metrics(q4, targets, m4, ids)
    print(f"C4训练{time.time() - t0:.0f}s")

    # ═══ C2b: MLP投影头+训练增强(与C4同数据同epoch——分离注意力贡献) ═══
    t0 = time.time()
    cfg2b = TrainConfig(shared_dim=256, lr=1e-3, epochs=args.epochs * 2,
                        batch_size=48, temperature=0.07)
    tp2b = TrimodalContrastiveTrainer(
        {"text": 1024, "image": IMG_DIM}, cfg2b)
    f2b = t_feats(tr_aug)
    mods2b = {k: ("image" if k in img_feat else "text") for k in f2b}
    tp2b.train(f2b, mods2b, [PairSample("text-image", a, b, confidence=0.7)
                             for a, b in tr_aug])
    q2b = {t["chunk_id"]: tp2b.projector.forward_numpy(
        "text", np.asarray(bge[t["chunk_id"]], dtype=np.float32))
        for t in test_texts}
    m2b = np.stack([tp2b.projector.forward_numpy(
        "image", img_feat[c["chunk_id"]]) for c in test_images])
    c2b = metrics(q2b, targets, m2b, ids)
    print(f"C2b(MLP+增强)训练{time.time() - t0:.0f}s")

    print("\n══ 图文对齐五配置完整实验 ══")
    print(f"  {'配置':<30s} R@1    R@5    R@10   MRR@10")
    for name, m in (("C1 Text-Bridge", c1), ("C2 MLP投影头", c2),
                    ("C2b MLP+训练增强", c2b), ("C3 原型注意力", c3),
                    ("C4 原型注意力+增强", c4)):
        print(f"  {name:<30s} {m['R@1']:.3f}  {m['R@5']:.3f}  "
              f"{m['R@10']:.3f}  {m['MRR@10']:.3f}")

    out = BASE / "data/gjb_438c/trimodal/proto_attention_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "config": {"epochs": args.epochs, "n_pairs_std": len(tr_std),
                   "n_pairs_aug": len(tr_aug), "n_proto": 64,
                   "test": f"{len(test_texts)}q×{len(test_images)}img"},
        "results": {"C1_text_bridge": c1, "C2_mlp": c2,
                    "C2b_mlp_aug": c2b,
                    "C3_proto_attention": c3, "C4_augmented": c4},
        "loss_history_c3": [round(x, 4) for x in pa.history]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果 → {out}")


if __name__ == "__main__":
    main()
