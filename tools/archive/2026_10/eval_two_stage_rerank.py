r"""两阶段检索评测(召回→重排): "rerank增益取决于召回质量"的实证.

业界标准两阶段管线: 第一阶段召回(高吞吐粗排, 保底候选集) → 第二阶段
cross-encoder重排(低吞吐精排, 攻排序质量). 本实验固定重排器
(bge-reranker-v2-m3), 只切换第一阶段召回源, 对照重排增益:

  配置①  lexical强召回top-50 → 无重排 → top-20  (实体精确命中=排序天花板)
  配置②  lexical强召回top-50 → bge-rerank → top-20  (预期增益≈0: 无工作面)
  配置③  dense弱召回top-50   → 无重排 → top-20  (BGE余弦排序有误差)
  配置④  dense弱召回top-50   → bge-rerank → top-20  (预期显著增益: 工作面)

协议:
  数据    retrieval_evalset 300条(entity作query), 金标=expected.chunk_ids
  召回A   HybridRecaller._lexical(精确子串+双关键词, 文档稳定序, 分全1.0)
  召回B   BGE-large-zh原生余弦(dense_index.pkl缓存5231条chunk向量;
          query侧BgeLocal.embed+BGE检索指令前缀, 打分与_dense同口径)
  重排    BgeReranker.score([(query, chunk富化文本)])×全部top-50候选 →
          按分取top-20(无事实位保护——纯两阶段管线, 区别于hybrid_recall
          内嵌的保序级联rerank, 本实验对照的是业界标准形态)
  指标    R@10 / R@20 / MRR@10(eval_hybrid_recall.evaluate_query同口径)
  翻转    配置②④中重排把chunk从召回>top_k名提进重排top-10的案例数
          (重排价值的直接证据; 案例=(实体,chunk)对去重——评测集同一实体
          3条问句变体行在entity作query下完全重复, raw行级计数并存result)
          另计top-1破坏(重排风险, MRR饱和时的工作面)
  落盘    runs协议open_run → result.json(汇总+增益+翻转+逐query+耗时)

用法: python tools/eval_two_stage_rerank.py [--limit 300] [--top-k0 50] [--top-k 20]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.blackboard.hybrid_recall import (  # noqa: E402
    _QUERY_PREFIX,
    HybridRecaller,
)
from algorithms.blackboard.reranker import BgeReranker  # noqa: E402
from eval_hybrid_recall import avg_metrics, evaluate_query, fmt_table  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
CONFIGS = ("lex_plain", "lex_rerank", "dense_plain", "dense_rerank")
RERANK_CFGS = ("lex_rerank", "dense_rerank")
METRICS = ("recall@10", "recall@20", "mrr@10")
LABELS = {"lex_plain": "① lexical→无重排", "lex_rerank": "② lexical→rerank",
          "dense_plain": "③ dense→无重排", "dense_rerank": "④ dense→rerank"}


def _hit(cid: str, score: float, rank: int,
         by_id: dict[str, dict]) -> dict[str, Any]:
    """候选条目(统一schema; recall_rank=第一阶段名次)."""
    c = by_id.get(cid, {})
    return {"chunk_id": cid, "type": c.get("type", "text"),
            "section": c.get("section", ""), "doc": c.get("doc", ""),
            "snippet": (c.get("text") or "")[:80],
            "recall_score": round(score, 4), "recall_rank": rank}


def lexical_recall(rec: HybridRecaller, query: str, k0: int,
                   by_id: dict[str, dict]) -> list[dict[str, Any]]:
    """召回源A: lexical通道top-k0(精确命中分全1.0, 文档稳定序)."""
    hits = rec._lexical(query, "").hits[:k0]
    return [_hit(h.chunk_id, h.score, i, by_id) for i, h in enumerate(hits, 1)]


def dense_recall(rec: HybridRecaller, query: str, k0: int,
                 by_id: dict[str, dict]) -> list[dict[str, Any]]:
    """召回源B: BGE原生余弦top-k0(复用_ensure_dense索引, 同_dense打分口径)."""
    qtext = _QUERY_PREFIX + query[:200]
    q = rec._bge.embed([qtext]).get(qtext)
    if not q:
        raise RuntimeError(f"dense query embedding failed: {query!r}")
    scored = [(sum(a * b for a, b in zip(q, rec._dense_vecs[cid])), cid)
              for cid in rec._dense_ids]
    scored.sort(key=lambda x: -x[0])
    return [_hit(cid, s, i, by_id) for i, (s, cid) in enumerate(scored[:k0], 1)]


def plain_stage(cands: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """无重排对照: 召回序即最终序(截断top_k)."""
    return [{**h, "rank": h["recall_rank"]} for h in cands[:top_k]]


def rerank_stage(rr: BgeReranker, rec: HybridRecaller, query: str,
                 cands: list[dict[str, Any]],
                 top_k: int) -> list[dict[str, Any]]:
    """第二阶段: cross-encoder对(query, chunk富化文本)全部候选打分, 按分取top_k."""
    by_id = rec.store._chunk_by_id()
    pairs = [(query, rec._rich_text(by_id.get(h["chunk_id"], {}))[:400])
             for h in cands]
    scores = rr.score(pairs)
    ranked = sorted(zip(cands, scores), key=lambda x: -x[1])
    out: list[dict[str, Any]] = []
    for h, s in ranked[:top_k]:
        out.append({**h, "rerank_score": round(float(s), 4),
                    "rank": len(out) + 1})
    return out


def flip_record(cands: list[dict[str, Any]], final: list[dict[str, Any]],
                exp_ids: set[str], top_k: int, q_id: str,
                query: str) -> dict[str, Any]:
    """单query重排翻转: 召回>top_k名 → 重排top-10(价值) + top-1破坏(风险)."""
    into10 = [{"query": query, "q_id": q_id, "chunk_id": h["chunk_id"],
               "section": h.get("section", ""), "doc": h.get("doc", ""),
               "recall_rank": h["recall_rank"], "rerank_rank": h["rank"],
               "rerank_score": h.get("rerank_score"),
               "gold": h["chunk_id"] in exp_ids}
              for h in final[:10] if h["recall_rank"] > top_k]
    into_k = [h["chunk_id"] for h in final[:top_k] if h["recall_rank"] > top_k]
    return {"q_id": q_id, "query": query, "into10": into10,
            "into_k": into_k,
            "gold_into_k": [c for c in into_k if c in exp_ids],
            "top1_break": bool(cands and final
                               and cands[0]["chunk_id"] in exp_ids
                               and final[0]["chunk_id"] not in exp_ids)}


def agg_flips(records: list[dict[str, Any]]) -> dict[str, Any]:
    """跨query翻转聚合: 案例=唯一(entity,chunk)对去重口径.

    评测集同一实体含3条问句变体行, entity作query时行间完全重复 →
    案例数按(entity,chunk)去重; *_raw保留300行原始计数备审计.
    """
    into10 = [f for r in records for f in r["into10"]]
    uniq10 = {(f["q_id"], f["chunk_id"]): f for f in into10}
    gold10 = [f for f in uniq10.values() if f["gold"]]
    rescued = {(r["q_id"], c) for r in records for c in r["into_k"]}
    gold_resc = {(r["q_id"], c) for r in records for c in r["gold_into_k"]}
    return {"n_flip_into10": len(uniq10),
            "n_flip_into10_raw": len(into10),
            "n_gold_flip_into10": len(gold10),
            "n_gold_flip_into10_raw": sum(1 for f in into10 if f["gold"]),
            "n_entities_with_flip": len({f["q_id"] for f in uniq10.values()}),
            "n_rescued_into_topk": len(rescued),
            "n_gold_rescued_into_topk": len(gold_resc),
            "n_top1_break": len({r["q_id"] for r in records if r["top1_break"]}),
            "n_top1_break_raw": sum(1 for r in records if r["top1_break"]),
            "gold_flip_examples": [
                {k: f[k] for k in ("q_id", "query", "chunk_id", "section",
                                   "doc", "recall_rank", "rerank_rank",
                                   "rerank_score")}
                for f in gold10[:10]]}


def _delta(v: float) -> str:
    return f"{v:+.3f}"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--top-k0", type=int, default=50, help="第一阶段召回深度")
    ap.add_argument("--top-k", type=int, default=20, help="第二阶段产出深度")
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))[:args.limit]
    rec = HybridRecaller()
    by_id = rec.store._chunk_by_id()
    rr = BgeReranker()
    if rr.ensure() == "unavailable":
        print(f"错误: 重排器不可用: {rr.last_error}")
        return 2
    if rec._ensure_dense() != "ok" or rec._bge is None:
        print("错误: dense召回源不可用(BGE模型/索引加载失败)")
        return 2
    print(f"两阶段评测: n={len(data)} | 召回top-{args.top_k0} → 产出top-"
          f"{args.top_k} | 重排器={rr.mode} | dense索引={len(rec._dense_vecs)}条")

    def _texts(hits: list[dict[str, Any]]) -> str:
        return " ".join((by_id.get(h.get("chunk_id"), {}).get("text") or "")
                        for h in hits)

    rows: dict[str, list[dict[str, float]]] = {c: [] for c in CONFIGS}
    flip_recs: dict[str, list[dict[str, Any]]] = {c: [] for c in RERANK_CFGS}
    wall = {"lexical_recall_s": 0.0, "dense_recall_s": 0.0,
            "rerank_lex_s": 0.0, "rerank_dense_s": 0.0}
    infer_ms = {"lex_rerank": 0.0, "dense_rerank": 0.0}
    t_all = time.time()

    for i, q in enumerate(data):
        query = q["entity"] or q["entity_id"] or q["query"]
        exp_ids = set(q["expected"].get("chunk_ids") or [])
        t = time.time()
        lex = lexical_recall(rec, query, args.top_k0, by_id)
        wall["lexical_recall_s"] += time.time() - t
        t = time.time()
        den = dense_recall(rec, query, args.top_k0, by_id)
        wall["dense_recall_s"] += time.time() - t

        finals: dict[str, list[dict[str, Any]]] = {
            "lex_plain": plain_stage(lex, args.top_k),
            "dense_plain": plain_stage(den, args.top_k),
        }
        cands_by = {"lex_rerank": lex, "dense_rerank": den}
        for cfg in RERANK_CFGS:
            ms0 = rr.stats["infer_ms"]
            t = time.time()
            finals[cfg] = rerank_stage(rr, rec, query, cands_by[cfg],
                                       args.top_k)
            key = "rerank_lex_s" if cfg == "lex_rerank" else "rerank_dense_s"
            wall[key] += time.time() - t
            infer_ms[cfg] += rr.stats["infer_ms"] - ms0

        for cfg in CONFIGS:
            rows[cfg].append(evaluate_query(finals[cfg], q["expected"],
                                            q.get("entity", ""),
                                            q.get("entity_id", ""),
                                            _texts(finals[cfg])))
        for cfg in RERANK_CFGS:
            flip_recs[cfg].append(flip_record(cands_by[cfg], finals[cfg],
                                              exp_ids, args.top_k, q["id"],
                                              query))
        if (i + 1) % 50 == 0:
            print(f"  进度 {i + 1}/{len(data)}")

    summary = {c: avg_metrics(rows[c]) for c in CONFIGS}
    delta = {src: {m: round(summary[f"{src}_rerank"][m]
                            - summary[f"{src}_plain"][m], 4)
                   for m in METRICS}
             for src in ("lex", "dense")}
    flips = {c: agg_flips(flip_recs[c]) for c in RERANK_CFGS}
    total_s = round(time.time() - t_all, 1)

    print(f"\n══ 主表(n={len(data)}) ══")
    print(fmt_table(["配置", "R@10", "R@20", "MRR@10"],
                    [[LABELS[c]] + [f"{summary[c].get(m, 0):.3f}"
                                    for m in METRICS] for c in CONFIGS]))
    print("\n══ 重排增益(Δ = rerank − 无重排) ══")
    print(fmt_table(["召回源", "ΔR@10", "ΔR@20", "ΔMRR@10"],
                    [["lexical(强召回)"] + [_delta(delta["lex"][m])
                                            for m in METRICS],
                     ["dense(弱召回)"] + [_delta(delta["dense"][m])
                                          for m in METRICS]]))

    print(f"\n══ 重排翻转分析(召回>{args.top_k}名 → 重排top-10; 案例=(实体,chunk)去重) ══")
    print(fmt_table(["配置", ">20→≤10案例", "其中gold", "涉及实体",
                     "救回入top-20", "top-1破坏"],
                    [[LABELS[c]] + [str(flips[c][k]) for k in
                                    ("n_flip_into10", "n_gold_flip_into10",
                                     "n_entities_with_flip",
                                     "n_rescued_into_topk", "n_top1_break")]
                     for c in RERANK_CFGS]))
    gold_ex = flips["dense_rerank"]["gold_flip_examples"][:5]
    if gold_ex:
        print("配置④ gold翻转示例(重排价值直接证据):")
        for e in gold_ex:
            print(f"  {e['q_id']} «{e['query'][:18]}» {e['chunk_id']}"
                  f" §{e['section']} 召回#{e['recall_rank']}"
                  f"→重排#{e['rerank_rank']} score={e['rerank_score']}")

    print(f"\n耗时: lexical召回{wall['lexical_recall_s']:.1f}s | dense召回"
          f"{wall['dense_recall_s']:.1f}s | 重排墙钟 ②{wall['rerank_lex_s']:.1f}s"
          f" / ④{wall['rerank_dense_s']:.1f}s (GPU推理 ②"
          f"{infer_ms['lex_rerank']:.0f}ms / ④"
          f"{infer_ms['dense_rerank']:.0f}ms, 共{rr.stats['n_pairs']}对"
          f" {rr.stats['n_batches']}batch) | 总{total_s}s")

    dl = delta["lex"]["recall@10"]
    dd = delta["dense"]["recall@10"]
    print(f"结论: lexical源ΔR@10={dl:+.3f}(精确命中=排序天花板, 重排无工作面); "
          f"dense源ΔR@10={dd:+.3f}(召回排序缺口=重排工作面) — "
          f"rerank增益取决于召回质量")

    run = open_run("eval_two_stage_rerank", {
        "limit": args.limit, "top_k0": args.top_k0, "top_k": args.top_k,
        "rerank_model": "bge-reranker-v2-m3(local)", "rerank_device": rr.mode,
        "dense_index_n": len(rec._dense_vecs),
        "protocol": "entity作query; 金标=expected.chunk_ids; "
                    "指标口径同eval_hybrid_recall; rerank作用于全部top-k0候选"})
    run.log(event="eval_done", n_queries=len(data), total_s=total_s,
            rerank_pairs=rr.stats["n_pairs"])
    run.save_result({
        "summary": summary, "delta": delta, "flips": flips,
        "timing": {"lexical_recall_s": round(wall["lexical_recall_s"], 1),
                   "dense_recall_s": round(wall["dense_recall_s"], 1),
                   "rerank_lex_wall_s": round(wall["rerank_lex_s"], 1),
                   "rerank_dense_wall_s": round(wall["rerank_dense_s"], 1),
                   "rerank_lex_infer_ms": round(infer_ms["lex_rerank"], 1),
                   "rerank_dense_infer_ms": round(infer_ms["dense_rerank"], 1),
                   "rerank_pairs": rr.stats["n_pairs"],
                   "rerank_batches": rr.stats["n_batches"],
                   "rerank_device": rr.mode, "total_s": total_s},
        "per_query": rows, "flip_records": flip_recs,
        "labels": LABELS})
    print(f"\n结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
