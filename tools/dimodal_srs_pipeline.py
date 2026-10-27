r"""双模态(文本+图像)对齐管线 — SRS真实数据端到端.

数据(全部现有资产):
  文本侧: srs_chunks.json的text条目 → BGE-large-zh native(1024维)
          (dense_index.pkl磁盘缓存已建, 直接复用)
  图像侧: image条目(mineru_standard图片) → Chinese-CLIP native(512维)
          (clip_image_index.pkl磁盘缓存, 381张一次性)
  配对:   同(doc, section)的text↔image共现对(章节级正样本,
          置信0.7 — 文档§4.2 same_source级)
  划分:   按文档分块防泄漏(doc 01-12训练 / 13-16测试)

评测三配置(§8.4 B系消融的图文版):
  B0 CLIP原生zero-shot: query文本→CLIP文本编码 vs CLIP图像嵌入
     (检验"冻结底座自然对齐"——CLIP自带图文先验的强度)
  B1 VLM文本桥: query BGE vs 图像的key_elements富化文本BGE
     (现有multimodal通道方案 — 零训练基线)
  B2 投影头训练后: query BGE→proj vs 图像CLIP→proj
     (本文方法 — 学习的图文对齐)

用法: python tools/dimodal_srs_pipeline.py [--epochs 30] [--limit-docs N]
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

from algorithms.trimodal import (  # noqa: E402
    PairSample,
    TrainConfig,
    TrimodalContrastiveTrainer,
)
from algorithms.trimodal.clip_encoder import ChineseClipEncoder  # noqa: E402

CHUNKS = BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json"
DENSE_CACHE = BASE / "data/gjb_438c/blackboard/dense_index.pkl"
TRAIN_DOCS = 12   # doc序号≤12训练, 其余测试(防泄漏: 文档级分块)


def load_corpus() -> tuple[list[dict], list[dict]]:
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    texts = [c for c in chunks if c.get("type") == "text" and c.get("text")]
    images = [c for c in chunks if c.get("type") == "image"]
    return texts, images


def image_full_path(c: dict) -> Path | None:
    p = Path("data/gjb_438c/mineru_standard") / c["doc"] / "office" / \
        c.get("image_path", "")
    return p if p.is_file() else None


def retrieval_metrics(q_vecs: dict[str, np.ndarray],
                      targets: dict[str, set[str]],
                      mat: np.ndarray, ids: list[str],
                      ks: tuple[int, ...] = (1, 5, 10)) -> dict[str, float]:
    """R@1/R@5/R@10 + MRR@10(首个期望命中项的倒数排名, top10外计0)."""
    m = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-8)
    recs = {k: 0 for k in ks}
    rr_sum = 0.0
    for qid, v in q_vecs.items():
        vn = v / max(np.linalg.norm(v), 1e-8)
        order = np.argsort(-(m @ vn))
        rank_of = {ids[i]: r + 1 for r, i in enumerate(order)}
        first = min((rank_of[t] for t in targets[qid] if t in rank_of),
                    default=len(ids) + 1)
        for k in ks:
            if first <= k:
                recs[k] += 1
        if first <= 10:
            rr_sum += 1.0 / first
    n = max(len(q_vecs), 1)
    out = {f"R@{k}": round(recs[k] / n, 4) for k in ks}
    out["MRR@10"] = round(rr_sum / n, 4)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=120)
    ap.add_argument("--shared-dim", type=int, default=256)
    args = ap.parse_args()

    texts, images = load_corpus()
    print(f"语料: {len(texts)}文本chunk / {len(images)}图片chunk")

    # ═══ native特征 ═══
    with open(DENSE_CACHE, "rb") as f:
        bge_index: dict[str, list[float]] = pickle.load(f)
    print(f"BGE缓存: {len(bge_index)}条")

    clip = ChineseClipEncoder()
    mode = clip.ensure()
    print(f"CLIP: {mode} (缓存{len(clip._img_cache)}图)")
    img_vecs: dict[str, list[float]] = {}
    for c in images:
        p = image_full_path(c)
        if p is None:
            continue
        img_vecs[c["chunk_id"]] = clip.image_embed_cached(str(p))
    clip.save_cache()
    images = [c for c in images if c["chunk_id"] in img_vecs]
    print(f"CLIP编码: {len(images)}图完成")

    # ═══ 配对(同doc+section)与划分 ═══
    text_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in texts:
        if c["chunk_id"] in bge_index:
            text_by_key[(c["doc"], c.get("section", ""))].append(c)
    pairs: list[PairSample] = []
    for c in images:
        for t in text_by_key.get((c["doc"], c.get("section", "")), [])[:3]:
            pairs.append(PairSample(
                "text-image", t["chunk_id"], c["chunk_id"],
                level="weak", confidence=0.7))
    train_pairs = [p for p in pairs
                   if int(p.b_id.split("_")[0][:2]) <= TRAIN_DOCS]
    print(f"配对: {len(pairs)}对(同章节共现) | 训练{len(train_pairs)}对"
          f"(doc≤{TRAIN_DOCS})")

    # ═══ 投影头训练(B2) ═══
    train_feats: dict[str, np.ndarray] = {}
    mods: dict[str, str] = {}
    for p in train_pairs:
        for iid, is_img in ((p.a_id, False), (p.b_id, True)):
            if iid in train_feats:
                continue
            if is_img:
                train_feats[iid] = np.asarray(img_vecs[iid], dtype=np.float32)
                mods[iid] = "image"
            elif iid in bge_index:
                train_feats[iid] = np.asarray(bge_index[iid], dtype=np.float32)
                mods[iid] = "text"
    t0 = time.time()
    cfg = TrainConfig(shared_dim=args.shared_dim, lr=1e-3,
                      epochs=args.epochs, batch_size=48, temperature=0.07)
    # 投影头: 图像侧=CLIP视觉+VLM转写拼接(融合两信号)
    # (动机: B1证明GJB图语义在图内文字, CLIP视觉弱——融合互补)
    img_dim = 512 + 1024
    img_feat = {cid: np.concatenate([
        np.asarray(img_vecs[cid], dtype=np.float32),
        np.asarray(bge_index[cid], dtype=np.float32)])
        for cid in img_vecs}
    trainer = TrimodalContrastiveTrainer(
        {"text": 1024, "image": img_dim}, cfg)
    trainer.train(
        {**{p.a_id: np.asarray(bge_index[p.a_id], dtype=np.float32)
            for p in train_pairs},
         **{p.b_id: img_feat[p.b_id] for p in train_pairs}},
        {**{p.a_id: "text" for p in train_pairs},
         **{p.b_id: "image" for p in train_pairs}},
        train_pairs)
    print(f"投影头训练(CLIP+VLM融合): {time.time() - t0:.1f}s, "
          f"{len(train_pairs)}对, {cfg.epochs}epochs")

    # ═══ 评测集(test文档的text query → image目标) ═══
    test_texts = [c for c in texts
                  if int(c["doc"][:2]) > TRAIN_DOCS
                  and c["chunk_id"] in bge_index]
    test_images = [c for c in images if int(c["doc"][:2]) > TRAIN_DOCS]
    targets: dict[str, set[str]] = {}
    for t in test_texts:
        key = (t["doc"], t.get("section", ""))
        targets[t["chunk_id"]] = {c["chunk_id"] for c in images
                                  if (c["doc"], c.get("section", "")) == key}
    test_texts = [t for t in test_texts if targets[t["chunk_id"]]]
    print(f"评测: {len(test_texts)}文本query × {len(test_images)}图"
          f"(test=doc{TRAIN_DOCS + 1:02d}-16)")

    if not test_texts or not test_images:
        print("测试集为空, 退出")
        return

    # 三个方法的query与候选表示
    q_clip = {t["chunk_id"]: np.asarray(v, dtype=np.float32) for t, v in
              zip(test_texts, clip.text_embed([t["text"][:60]
                                               for t in test_texts]))}
    q_bge = {t["chunk_id"]: np.asarray(bge_index[t["chunk_id"]],
                                       dtype=np.float32)
             for t in test_texts}
    mat_clip = np.stack([np.asarray(img_vecs[c["chunk_id"]],
                                    dtype=np.float32) for c in test_images])
    mat_vlm = np.stack([np.asarray(bge_index[c["chunk_id"]],
                                   dtype=np.float32) for c in test_images])
    ids_clip = [c["chunk_id"] for c in test_images]
    m_clip = retrieval_metrics(q_clip, targets, mat_clip, ids_clip)
    m_vlm = retrieval_metrics(q_bge, targets, mat_vlm, ids_clip)
    q_proj = {t["chunk_id"]: trainer.projector.forward_numpy(
        "text", np.asarray(bge_index[t["chunk_id"]], dtype=np.float32))
        for t in test_texts}
    img_proj = np.stack([trainer.projector.forward_numpy(
        "image", img_feat[c["chunk_id"]]) for c in test_images])
    m_proj = retrieval_metrics(q_proj, targets, img_proj, ids_clip)

    print("\n══ T→I 检索指标 (三方法 × 四指标) ══")
    print(f"  {'Method':<22s} R@1    R@5    R@10   MRR@10")
    for name, m in (("CLIP (zero-shot)", m_clip),
                    ("Text-Bridge", m_vlm),
                    ("Projection Head", m_proj)):
        print(f"  {name:<22s} {m['R@1']:.3f}  {m['R@5']:.3f}  "
              f"{m['R@10']:.3f}  {m['MRR@10']:.3f}")

    result = {
        "config": {"epochs": args.epochs, "shared_dim": args.shared_dim,
                   "train_docs": TRAIN_DOCS, "n_pairs": len(train_pairs)},
        "T2I": {"clip_zeroshot": m_clip, "text_bridge": m_vlm,
                "projection_head": m_proj},
        "clip_stats": dict(clip.stats),
    }
    out = BASE / "data/gjb_438c/trimodal/dimodal_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n结果 → {out}")


if __name__ == "__main__":
    main()
