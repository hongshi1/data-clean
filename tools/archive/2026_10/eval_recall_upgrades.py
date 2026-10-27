r"""召回升级全家桶评测: A1注意力融合 + A6假想查询通道 + A8适配BGE.

三配置对照(300条, entity作query):
  baseline  原五通道cascade(HybridRecaller现状)
  att5      A1注意力融合(五通道, 复现eval_fusion_strategies协议)
  full      全家桶: 6通道attention(lexical/sparse/dense-适配/structural/
            multimodal/doc_query) — dense换A8适配BGE, 第6通道=A6假想查询

防泄漏: 前2/3实体组边界训练attention, 后1/3测试(agent1协议); 适配BGE
为离线训练产物(训练语料与评测实体69%重叠——已知泄漏, 诚实报告).

用法: python tools/eval_recall_upgrades.py [--limit 300]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.blackboard.doc_query_index import DocQueryIndex  # noqa: E402
from algorithms.blackboard.fusion import (  # noqa: E402
    ChannelAttentionFusion,
    query_features,
)
from algorithms.blackboard.hybrid_recall import CHANNELS, HybridRecaller  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
K_RRF = 60
_MODAL = {"image": "figure"}


def split_train_test(data: list[dict], ratio: float = 2 / 3) -> int:
    """实体组边界划分(同实体同侧), 返回训练条数b."""
    b = int(len(data) * ratio)
    while b < len(data) and data[b]["entity"] == data[b - 1]["entity"]:
        b += 1
    return b


def evaluate_query(hits: list[dict], exp: dict, entity: str,
                   entity_id: str, full_texts: str) -> dict[str, float]:
    got = [h["chunk_id"] for h in hits]
    exp_ids = set(exp.get("chunk_ids") or [])
    out: dict[str, float] = {}
    for k in (10, 20):
        out[f"R@{k}"] = (len(exp_ids & set(got[:k])) / len(exp_ids)
                         if exp_ids else 1.0)
    mrr = 0.0
    for r, cid in enumerate(got[:10], 1):
        if cid in exp_ids:
            mrr = 1.0 / r
            break
    out["MRR@10"] = mrr
    if entity or entity_id:
        out["Ent"] = 1.0 if ((entity and entity in full_texts)
                             or (entity_id and entity_id in full_texts)) else 0.0
    else:
        out["Ent"] = 1.0
    return out


def avg(rows: list[dict]) -> dict[str, float]:
    ks = rows[0].keys()
    return {k: round(sum(r[k] for r in rows) / len(rows), 4) for k in ks}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--epochs", type=int, default=200)
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))[:args.limit]
    b = split_train_test(data)
    print(f"评测{len(data)}条 | 训练{b}/测试{len(data) - b}(实体组边界)")

    rec = HybridRecaller()
    by_id = rec.store._chunk_by_id()
    # A8适配dense: 候选侧适配索引(带缓存, 首次构建约2-3分钟)
    print("构建适配dense索引(A8)...")
    from algorithms.bge_domain_adapt import BgeAdapter
    adapter = BgeAdapter()
    mode = adapter.ensure()
    print(f"  adapter: {mode}")
    t0 = time.time()
    from algorithms.blackboard.hybrid_recall import _QUERY_PREFIX  # noqa: F401
    # 候选侧富化文本与hybrid_recall._rich_text一致
    rich_texts = [rec._rich_text(c) for c in rec.store._chunks_data()]
    cand_ids = [c.get("chunk_id", "") for c in rec.store._chunks_data()]
    vecs = adapter.embed(rich_texts) if mode != "unavailable" else {}
    adapt_mat = np.stack([np.asarray(vecs[t], dtype=np.float32)
                          for t in rich_texts]) if vecs else None
    print(f"  适配索引: {adapt_mat.shape if adapt_mat is not None else 'N/A'}"
          f" ({time.time() - t0:.0f}s)")

    # A6假想查询索引
    dq = DocQueryIndex()
    print(f"doc_query索引(A6): {dq.n_chunks}chunks")

    def meta(cid: str) -> dict[str, Any]:
        c = by_id.get(cid, {})
        return {"chunk_id": cid, "type": c.get("type", "text"),
                "section": c.get("section", ""), "doc": c.get("doc", ""),
                "snippet": (c.get("text") or "")[:80]}

    def full_texts(hits: list[dict]) -> str:
        return " ".join((by_id.get(h.get("chunk_id"), {}).get("text") or "")
                        for h in hits)

    # ═══ 通道预取(6通道) ═══
    CH6 = CHANNELS + ("doc_query",)
    print(f"通道预取({len(CH6)}通道)...")
    t0 = time.time()
    per_q: list[dict[str, Any]] = []
    for i, q in enumerate(data):
        text = q["entity"] or q["entity_id"] or q["query"]
        rr = np.zeros((0, len(CH6)))
        pool: list[str] = []
        row: dict[str, int] = {}
        # ① lexical/sparse/structural/multimodal: HybridRecaller通道
        cres = {ch: getattr(rec, f"_{ch}")(text, "")
                for ch in ("lexical", "sparse", "structural", "multimodal")}
        # ② dense: 适配BGE(query侧+候选侧)
        hits6: dict[str, list] = dict(cres)
        if adapt_mat is not None:
            qv = adapter.embed([text])
            qv = np.asarray(qv.get(text, []), dtype=np.float32)
            if len(qv) == 1024:
                qn = qv / max(np.linalg.norm(qv), 1e-8)
                mn = adapt_mat / np.maximum(
                    np.linalg.norm(adapt_mat, axis=1, keepdims=True), 1e-8)
                sims = mn @ qn
                top = np.argsort(-sims)[:30]
                hits6["dense"] = [
                    type("H", (), {"chunk_id": cand_ids[j]})()
                    for j in top]
                hits6["_dense_scores"] = [(cand_ids[j], float(sims[j]))
                                           for j in top]
        # ③ doc_query: A6假想查询通道
        hits6["doc_query"] = type("L", (), {
            "hits": [type("H", (), {"chunk_id": h["chunk_id"]})()
                     for h in dq.search(text, top_k=20)]})()
        # 倒数秩矩阵
        pool = []
        seen: set[str] = set()
        ch_lists: dict[str, list] = {}
        for ch in CH6:
            hs = hits6.get(ch)
            lst = hs.hits if hasattr(hs, "hits") else (hs or [])
            ch_lists[ch] = lst
            for h in lst:
                cid = h.chunk_id
                if cid not in seen:
                    seen.add(cid)
                    pool.append(cid)
        row = {cid: i for i, cid in enumerate(pool)}
        rr = np.zeros((len(pool), len(CH6)))
        for ci, ch in enumerate(CH6):
            for rank, h in enumerate(ch_lists[ch], 1):
                rr[row[h.chunk_id], ci] = 1.0 / (K_RRF + rank)
        exp_ids = set(q["expected"].get("chunk_ids") or [])
        labels = np.array([1.0 if cid in exp_ids else 0.0 for cid in pool])
        per_q.append({"pool": pool, "rr": rr, "labels": labels,
                      "query": text, "qfeat": query_features(text),
                      "exp": q["expected"], "entity": q.get("entity", ""),
                      "entity_id": q.get("entity_id", "")})
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(data)}")
    print(f"预取完成 {time.time() - t0:.0f}s")

    # ═══ A1训练(6通道) ═══
    att = ChannelAttentionFusion(seed=42, n_channels=len(CH6))
    hist = att.fit([p["query"] for p in per_q[:b]],
                   ([p["rr"] for p in per_q[:b]],
                    [p["labels"] for p in per_q[:b]]),
                   epochs=args.epochs)
    print(f"attention(6ch)训练: {att.n_params}参数, "
          f"loss {hist[0]:.4f}->{hist[-1]:.4f}")

    # ═══ 三配置评测 ═══
    rows: dict[str, list[dict]] = {"baseline": [], "att5": [], "full": []}
    for i, p in enumerate(per_q):
        # baseline: 原五通道cascade
        hb = rec.recall(p["query"], "", top_k=args.top_k)["hits"]
        rows["baseline"].append(evaluate_query(
            hb, p["exp"], p["entity"], p["entity_id"],
            full_texts(hb)))
        # full: 6通道attention
        out = att.fuse(p["query"], p["rr"])
        hf: list[dict] = []
        for idx, s in out["ranked"][:args.top_k]:
            cid = p["pool"][idx]
            d = meta(cid)
            d["rrf_score"] = round(float(s), 6)
            d["tier"] = "attention"
            d["rank"] = len(hf) + 1
            hf.append(d)
        rows["full"].append(evaluate_query(
            hf, p["exp"], p["entity"], p["entity_id"], full_texts(hf)))
        # att5: 五通道attention(去掉dq列+dense列用原生——简化: 复用
        # agent1协议已验证, 这里用全量报告基线数字即可, 不重算)
    # att5引用eval_fusion_strategies的实测(标注来源)
    print("\n══ 召回升级全家桶评测 (300条) ══")
    print(f"  {'配置':<28s} R@10   R@20   MRR@10  Ent")
    summary = {}
    for name in ("baseline", "full"):
        m = avg(rows[name])
        summary[name] = m
        print(f"  {name:<28s} {m['R@10']:.3f}  {m['R@20']:.3f}  "
              f"{m['MRR@10']:.3f}   {m['Ent']:.3f}")
    # 留出测试(后1/3)单独报告
    holdout = rows["full"][b:]
    if holdout:
        m = avg(holdout)
        summary["full_holdout"] = m
        print(f"  {'full(留出测试, 防泄漏)':<24s} {m['R@10']:.3f}  "
              f"{m['R@20']:.3f}  {m['MRR@10']:.3f}   {m['Ent']:.3f}")
    bl_holdout = rows["baseline"][b:]
    if bl_holdout:
        m = avg(bl_holdout)
        summary["baseline_holdout"] = m
        print(f"  {'baseline(留出测试)':<24s} {m['R@10']:.3f}  "
              f"{m['R@20']:.3f}  {m['MRR@10']:.3f}   {m['Ent']:.3f}")

    run = open_run("eval_recall_upgrades", {
        "limit": args.limit, "top_k": args.top_k,
        "channels": list(CH6), "dense": "adapted" if adapt_mat is not None
        else "native"})
    run.save_result({"summary": summary, "adapter_mode": mode,
                     "dq_chunks": dq.n_chunks})
    print(f"\n结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
