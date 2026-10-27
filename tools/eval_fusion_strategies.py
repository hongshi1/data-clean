r"""融合策略四档评测: cascade(现状) vs rrf等权 vs A5校准加权 vs A1注意力.

协议:
  数据    retrieval_evalset 300条(entity作query), 金标=expected.chunk_ids
  通道    HybridRecaller五通道(每query预取一次, 四档共享同一通道输出,
          融合层是唯一变量; cascade由recall内部重跑, 确定性一致)
  四档    cascade:      HybridRecaller.recall(fusion="cascade")(现状基线)
          rrf_equal:    等权RRF(标准Cormack RRF, 权重全1)
          rrf_weighted: A5·CALIBRATED_WEIGHTS加权RRF
          attention:    A1·ChannelAttentionFusion(查询自适应α)
  防泄漏  前2/3条训练attention, 边界后移至实体组边界(同一实体的全部
          条目不跨train/test, 训练/测试实体零重叠), 后1/3条留出测试;
          静态三档无需训练. 输出全量与留出两张表(留出表为公平对比).
  指标    R@10 / R@20 / MRR@10(eval_hybrid_recall.evaluate_query同口径)
  落盘    runs协议open_run → result.json(汇总+逐query+α统计)

用法: python tools/eval_fusion_strategies.py [--limit 300] [--no-dense]
      [--epochs 200] [--top-k 20] [--seed 42]
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

from algorithms.blackboard.fusion import (  # noqa: E402
    CALIBRATED_WEIGHTS,
    ChannelAttentionFusion,
    query_features,
    rrf_weighted,
)
from algorithms.blackboard.hybrid_recall import CHANNELS, HybridRecaller  # noqa: E402
from eval_hybrid_recall import avg_metrics, evaluate_query, fmt_table  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
K_RRF = 60
STRATEGIES = ("cascade", "rrf_equal", "rrf_weighted", "attention")
LABELS = {"cascade": "cascade(现状)", "rrf_equal": "rrf等权",
          "rrf_weighted": "A5·校准加权RRF", "attention": "A1·注意力融合"}


def split_train_test(data: list[dict]) -> int:
    """前2/3为训练边界, 后移至实体组边界(同id条目不跨侧 → 实体零重叠)."""
    b = round(len(data) * 2 / 3)
    while 0 < b < len(data) and data[b]["id"] == data[b - 1]["id"]:
        b += 1
    return min(b, len(data))


def build_channel_data(rec: HybridRecaller, query: str) -> dict[str, Any]:
    """五通道直调(_lexical/_sparse/_dense/_structural/_multimodal).

    返回 {cres: 通道ChannelResult, pool: 候选并集(稳定序),
    rr: (m, 5)候选×通道倒数秩矩阵(未召回=0)}.
    """
    cres = {ch: getattr(rec, f"_{ch}")(query, "") for ch in CHANNELS}
    pool: list[str] = []
    seen: set[str] = set()
    for ch in CHANNELS:
        for h in cres[ch].hits:
            if h.chunk_id not in seen:
                seen.add(h.chunk_id)
                pool.append(h.chunk_id)
    rr = np.zeros((len(pool), len(CHANNELS)), dtype=float)
    row = {cid: i for i, cid in enumerate(pool)}
    for ci, ch in enumerate(CHANNELS):
        for rank, h in enumerate(cres[ch].hits, 1):
            rr[row[h.chunk_id], ci] = 1.0 / (K_RRF + rank)
    return {"cres": cres, "pool": pool, "rr": rr}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--no-dense", action="store_true")
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--epochs", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))[:args.limit]
    b = split_train_test(data)
    train_ids = {q["id"] for q in data[:b]}
    test_ids = {q["id"] for q in data[b:]}
    print(f"评测集{len(data)}条 | 防泄漏划分: 训练{b}条({len(train_ids)}实体) / "
          f"测试{len(data) - b}条({len(test_ids)}实体), "
          f"实体重叠{len(train_ids & test_ids)}")

    rec = HybridRecaller(use_dense=not args.no_dense)
    by_id = rec.store._chunk_by_id()

    def meta(cid: str) -> dict[str, Any] | None:
        c = by_id.get(cid)
        if c is None:
            return None
        return {"type": c.get("type", "text"), "section": c.get("section", ""),
                "doc": c.get("doc", ""), "snippet": (c.get("text") or "")[:80]}

    def full_texts(hits: list[dict[str, Any]]) -> str:
        return " ".join((by_id.get(h.get("chunk_id"), {}).get("text") or "")
                        for h in hits)

    # ① 五通道预取(四档共享同一通道输出, 融合层是唯一变量)
    t0 = time.time()
    per_q: list[dict[str, Any]] = []
    for i, q in enumerate(data):
        text = q["entity"] or q["entity_id"] or q["query"]
        cd = build_channel_data(rec, text)
        exp_ids = set(q["expected"].get("chunk_ids") or [])
        cd["labels"] = np.array([1.0 if cid in exp_ids else 0.0
                                 for cid in cd["pool"]])
        cd["query"] = text
        cd["qfeat"] = query_features(text)
        per_q.append(cd)
        if (i + 1) % 100 == 0:
            print(f"  通道预取 {i + 1}/{len(data)}")
    print(f"通道预取完成 {time.time() - t0:.1f}s")

    # ② attention训练: 训练侧(前b条)期望chunk标签; 无正例query被损失掩码跳过
    att = ChannelAttentionFusion(seed=args.seed)
    hist = att.fit([p["query"] for p in per_q[:b]],
                   ([p["rr"] for p in per_q[:b]],
                    [p["labels"] for p in per_q[:b]]),
                   epochs=args.epochs)
    print(f"attention训练: {att.n_params}参数, epochs={args.epochs}, "
          f"loss {hist[0]:.4f} → {hist[-1]:.4f}")

    # ③ 四档评测(全量; cascade用recall现状实现, 其余三档消费预取通道输出)
    rows: dict[str, list[dict[str, float]]] = {s: [] for s in STRATEGIES}
    alpha_log: list[dict[str, Any]] = []
    t1 = time.time()
    for i, q in enumerate(data):
        p = per_q[i]
        hits_map: dict[str, list[dict[str, Any]]] = {}
        hits_map["cascade"] = rec.recall(p["query"], "", top_k=args.top_k,
                                         fusion="cascade")["hits"]
        hits_map["rrf_equal"] = rrf_weighted(
            p["cres"], k_rrf=K_RRF, weights={c: 1.0 for c in CHANNELS},
            top_k=args.top_k, meta_fn=meta)
        hits_map["rrf_weighted"] = rrf_weighted(
            p["cres"], k_rrf=K_RRF, weights=CALIBRATED_WEIGHTS,
            top_k=args.top_k, meta_fn=meta)
        out = att.fuse(p["query"], p["rr"])
        att_hits: list[dict[str, Any]] = []
        for idx, s in out["ranked"][:args.top_k]:
            cid = p["pool"][idx]
            m = meta(cid)
            if m is None:
                continue
            d = {"chunk_id": cid, "rrf_score": round(s, 6), "tier": "attention",
                 "channels": [ch for ci, ch in enumerate(CHANNELS)
                              if p["rr"][idx, ci] > 0], "rank": 0}
            d.update(m)
            d["rank"] = len(att_hits) + 1
            att_hits.append(d)
        hits_map["attention"] = att_hits
        alpha_log.append({"alpha": out["alpha"], "qfeat": p["qfeat"].tolist()})
        for s in STRATEGIES:
            rows[s].append(evaluate_query(hits_map[s], q["expected"],
                                          q.get("entity", ""),
                                          q.get("entity_id", ""),
                                          full_texts(hits_map[s])))
        if (i + 1) % 100 == 0:
            print(f"  融合评测 {i + 1}/{len(data)}")
    elapsed = round(time.time() - t1, 1)

    # ══ 汇总表 ══
    def summarize(idxs: range) -> dict[str, dict[str, float]]:
        return {s: avg_metrics([rows[s][i] for i in idxs])
                for s in STRATEGIES} if len(idxs) else {s: {} for s in STRATEGIES}

    sum_full = summarize(range(len(data)))
    sum_test = summarize(range(b, len(data)))

    def table(summ: dict[str, dict[str, float]]) -> str:
        trows = []
        for s in STRATEGIES:
            m = summ[s] or {"recall@10": 0.0, "recall@20": 0.0, "mrr@10": 0.0}
            trows.append([LABELS[s], f"{m.get('recall@10', 0):.3f}",
                          f"{m.get('recall@20', 0):.3f}",
                          f"{m.get('mrr@10', 0):.3f}"])
        return fmt_table(["融合策略", "R@10", "R@20", "MRR@10"], trows)

    print(f"\n══ 全量{len(data)}条(attention含训练内样本, in-sample) ══")
    print(table(sum_full))
    if len(data) > b:
        print(f"\n══ 留出测试{len(data) - b}条(防泄漏: 训练/测试实体零重叠) ══")
        print(table(sum_test))

    # ══ attention α分析(查询自适应是否生效) ══
    def _alpha_mean(sel: list[dict[str, Any]]) -> dict[str, float]:
        out_m: dict[str, float] = {}
        for ch in CHANNELS:
            v = [a["alpha"][ch] for a in sel if ch in a["alpha"]]
            if v:
                out_m[ch] = round(float(np.mean(v)), 4)
        return out_m

    id_sel = [a for a in alpha_log if len(a["qfeat"]) == 3 and a["qfeat"][2] > 0.5]
    txt_sel = [a for a in alpha_log if len(a["qfeat"]) == 3 and a["qfeat"][2] <= 0.5]
    print(f"\nattention通道权重α均值(全量): {_alpha_mean(alpha_log)}")
    print(f"  含ID查询(n={len(id_sel)}): {_alpha_mean(id_sel)}")
    print(f"  纯文本实体查询(n={len(txt_sel)}): {_alpha_mean(txt_sel)}")
    print(f"耗时: 预取+训练+评测 {round(time.time() - t0, 1)}s | dense缓存"
          f" {rec.stats.get('dense_cache_hits', 0)}条")

    # ══ runs协议落盘 ══
    run = open_run("eval_fusion_strategies", {
        "limit": args.limit, "top_k": args.top_k, "epochs": args.epochs,
        "seed": args.seed, "use_dense": not args.no_dense, "k_rrf": K_RRF,
        "weights": dict(CALIBRATED_WEIGHTS),
        "split": {"protocol": "前2/3训练attention, 实体组边界对齐(零重叠)",
                  "train_n": b, "test_n": len(data) - b}})
    run.log(event="train_done", n_params=att.n_params,
            loss_first=round(hist[0], 4), loss_last=round(hist[-1], 4))
    run.log(event="eval_done", n_queries=len(data), elapsed_s=elapsed)
    run.save_result({
        "summary_full": sum_full, "summary_test": sum_test,
        "attention": {"n_params": att.n_params,
                      "loss_first": round(hist[0], 4),
                      "loss_last": round(hist[-1], 4),
                      "alpha_mean_all": _alpha_mean(alpha_log),
                      "alpha_mean_id": _alpha_mean(id_sel),
                      "alpha_mean_text": _alpha_mean(txt_sel)},
        "dense_stats": rec.stats, "elapsed_s": elapsed,
        "per_query": rows})
    print(f"\n结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
