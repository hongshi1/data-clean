r"""LoRA微调BGE检索评测: 原生BGE vs LoRA微调, dense单通道R@K/MRR@10.

口径(与eval_hybrid_recall single:dense / eval_bge_adapt同候选池同query源):
  - 候选池: 5231 chunks的_rich_text富化文本(图片chunk=caption+VLM
    key_elements, 复用HybridRecaller._rich_text);
  - query: q["entity"] or entity_id or query, 截200字;
  - 对称口径(主对比): query侧无BGE指令前缀 —— LoRA训练为对称用法
    (query/passage同编码器无前缀), 故主对比=双侧无前缀;
    附native+前缀行核验已知基线(0.3888/0.4757, 前缀+entity口径,
    eval_hybrid_recall single:dense);
  - 指标: Recall@10/@20(期望chunk_ids), MRR@10(首个命中倒数排名).

防泄漏(如实报告, 训练query源=eval前2/3+假想查询):
  - 训练query源与评测300条的entity/entity_id/问句文本重叠率
    (逐对子串匹配, 同eval_bge_adapt.leakage_stats口径);
  - 分区域分层指标: 前2/3(=训练query源区, 默认0..199) vs
    尾1/3(留出区) —— 重叠区指标提升需对照留出区解读.

结果落盘runs协议(config+git_sha+result).

用法:
  python tools/eval_lora_retriever.py [--data triples.json] [--limit 300]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.bge_lora_retriever import (  # noqa: E402
    DEFAULT_ADAPTER_DIR,
    DEFAULT_TRIPLES_PATH,
    BgeLoRATrainer,
    normalize_triples,
    resolve_triples,
)
from algorithms.common.bge_local import BgeLocal  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："  # 同hybrid_recall._QUERY_PREFIX
K_LIST = (10, 20)
_EPS = 1e-12
_KEYS = ("R@10", "R@20", "MRR@10")


def dense_metrics(embed_fn: Callable[[list[str]], dict[str, list[float]]],
                  rich: list[str], ids: list[str],
                  queries: list[dict[str, Any]],
                  prefix: str = "") -> tuple[dict[str, Any],
                                             list[dict[str, float]]]:
    """dense单通道指标: query向量↔chunk富化向量cos排序R@K + MRR@10.

    返回 (聚合指标, 逐query行) —— 逐query行供分区域聚合(防泄漏分层).
    """
    doc_vecs = embed_fn(rich)
    D = np.asarray([doc_vecs[t] for t in rich], dtype=np.float32)
    D = D / np.clip(np.linalg.norm(D, axis=1, keepdims=True), _EPS, None)
    q_texts = [prefix + (q["entity"] or q["entity_id"] or q["query"])[:200]
               for q in queries]
    q_vecs = embed_fn(q_texts)
    rows: list[dict[str, float]] = []
    for q, qt in zip(queries, q_texts):
        exp = set(q["expected"].get("chunk_ids") or [])
        v = q_vecs.get(qt)
        if not v:
            rows.append({"R@10": 0.0, "R@20": 0.0, "MRR@10": 0.0})
            continue
        v = np.asarray(v, dtype=np.float32)
        v = v / max(float(np.linalg.norm(v)), _EPS)
        order = np.argsort(-(D @ v))
        got = [ids[i] for i in order[:K_LIST[-1]]]
        mrr = 0.0
        for rank, cid in enumerate(got[:10], 1):
            if cid in exp:
                mrr = 1.0 / rank
                break
        rows.append({
            f"R@{K_LIST[0]}": (len(exp & set(got[:10])) / len(exp)
                               if exp else 1.0),
            f"R@{K_LIST[1]}": (len(exp & set(got[:20])) / len(exp)
                               if exp else 1.0),
            "MRR@10": mrr})
    return agg_rows(rows), rows


def agg_rows(rows: list[dict[str, float]]) -> dict[str, Any]:
    if not rows:
        return {k: None for k in _KEYS} | {"n": 0}
    return {k: round(float(np.mean([r[k] for r in rows])), 4)
            for k in _KEYS} | {"n": len(rows)}


def leakage_stats(queries: list[dict[str, Any]],
                  data: list[tuple[str, str, list[str]]],
                  split_at: int) -> dict[str, Any]:
    """防泄漏: 评测entity/entity_id/问句与训练query源及训练语料的重叠.

    口径同eval_bge_adapt.leakage_stats(子串匹配), 按区域(前2/3训练源区
    vs尾1/3留出区)分层报告.
    """
    train_q = [q for q, _, _ in data]
    train_pass = [x for _, p, negs in data for x in [p, *negs]]
    n = len(queries)

    def _rates(sub: list[dict[str, Any]]) -> dict[str, Any]:
        ent = eid = qt = entp = 0
        for q in sub:
            e, i, t = (q.get("entity", ""), q.get("entity_id", ""),
                       q.get("query", ""))
            if e and any(e in x for x in train_q):
                ent += 1
            if i and any(i in x for x in train_q):
                eid += 1
            if t and any(t in x for x in train_q):
                qt += 1
            if e and any(e in x for x in train_pass):
                entp += 1
        m = max(len(sub), 1)
        return {"n": len(sub), "entity_overlap": ent,
                "entity_overlap_rate": round(ent / m, 4),
                "entity_id_overlap_rate": round(eid / m, 4),
                "query_text_overlap_rate": round(qt / m, 4),
                "entity_in_train_passage_rate": round(entp / m, 4)}

    return {"n_train_queries": len(train_q),
            "n_train_passages": len(train_pass),
            "overall": _rates(queries),
            "by_region": {"first_2_3(train_source)": _rates(
                queries[:split_at]),
                "last_1_3(held_out)": _rates(queries[split_at:])}} \
        if n else {"n_train_queries": len(train_q)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="LoRA微调BGE检索评测")
    ap.add_argument("--data", type=Path, default=DEFAULT_TRIPLES_PATH,
                    help="训练triples.json(防泄漏统计用; 缺失则跳过)")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--adapter-dir", type=Path, default=DEFAULT_ADAPTER_DIR)
    ap.add_argument("--split-at", type=int, default=200,
                    help="训练query源区分界(默认200=eval前2/3)")
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))
    queries = (data[:args.limit] if isinstance(data, list)
               else data.get("queries", [])[:args.limit])

    from algorithms.blackboard.hybrid_recall import HybridRecaller
    rec = HybridRecaller(use_dense=False)
    chunks = rec.store._chunks_data()
    rich = [rec._rich_text(c) for c in chunks]
    ids = [c.get("chunk_id", "") for c in chunks]
    print(f"候选池: {len(rich)} chunks | 评测query: {len(queries)}条 | "
          f"区域分界@{args.split_at}(前2/3=训练query源区)")

    # ── 原生BGE: 对称口径(无前缀, 主对比) + 前缀参照(核验已知基线) ──
    native = BgeLocal()
    t0 = time.time()
    nat_np, nat_rows = dense_metrics(native.embed, rich, ids, queries)
    nat_pf, _ = dense_metrics(native.embed, rich, ids, queries,
                              prefix=QUERY_PREFIX)
    print(f"原生BGE(无前缀): {nat_np} | (+前缀参照): {nat_pf} "
          f"({time.time() - t0:.0f}s)")

    # ── LoRA微调后(对称口径) ──
    import torch
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    tr = BgeLoRATrainer(adapter_dir=args.adapter_dir)
    mode = tr.ensure()
    if mode == "unavailable":
        print(f"LoRA adapter不可用: {tr.last_error}")
        return 1
    t1 = time.time()
    lora_np, lora_rows = dense_metrics(tr.embed, rich, ids, queries)
    gpu_gb = (round(torch.cuda.max_memory_allocated() / 2**30, 2)
              if torch.cuda.is_available() else 0.0)
    print(f"LoRA微调(无前缀): {lora_np} ({time.time() - t1:.0f}s, "
          f"显存峰值{gpu_gb}GB)")

    # ── 分区域(防泄漏分层) ──
    sa = min(max(args.split_at, 0), len(queries))
    by_region = {
        "first_2_3(train_source)": {
            "native": agg_rows(nat_rows[:sa]),
            "lora": agg_rows(lora_rows[:sa])},
        "last_1_3(held_out)": {
            "native": agg_rows(nat_rows[sa:]),
            "lora": agg_rows(lora_rows[sa:])},
    }

    # ── 防泄漏: 训练query源与评测集的重叠(如实报告) ──
    leak: dict[str, Any] = {"reported": False}
    if args.data.exists():
        raw = json.loads(args.data.read_text(encoding="utf-8"))
        resolved, rstat = resolve_triples(raw if isinstance(raw, list)
                                          else [])
        data_norm, dstat = normalize_triples(resolved)
        leak = leakage_stats(queries, data_norm, sa) \
            | {"reported": True, "data_stat": dstat,
               "resolve_stat": rstat, "source": str(args.data)}
        o = leak["overall"]
        print(f"防泄漏: 训练query {leak['n_train_queries']}条 → "
              f"entity重叠率={o['entity_overlap_rate']:.2%} "
              f"({o['entity_overlap']}/{o['n']}), "
              f"entity_id重叠率={o['entity_id_overlap_rate']:.2%}, "
              f"问句文本重叠率={o['query_text_overlap_rate']:.2%}")
        for reg, st in leak["by_region"].items():
            print(f"  {reg}: entity重叠率={st['entity_overlap_rate']:.2%} "
                  f"(n={st['n']})")
    else:
        print(f"防泄漏: 训练数据不可用({args.data}), 跳过重叠统计")

    # ── 汇总 + runs协议落盘 ──
    run = open_run("eval_lora_retriever", {
        "limit": args.limit, "adapter_dir": str(args.adapter_dir),
        "split_at": args.split_at, "data": str(args.data),
        "protocol": "对称口径(query无前缀); 候选=rich_text; "
                    "query=entity/entity_id/query截200"})
    result = {
        "native_bge_noprefix": nat_np,
        "native_bge_prefix_ref": nat_pf,
        "lora_bge_noprefix": lora_np,
        "delta_vs_native_symmetric": {
            k: round(lora_np[k] - nat_np[k], 4) for k in _KEYS},
        "by_region": by_region,
        "leakage": leak,
        "adapter_meta": tr.meta,
        "adapter_stats": {k: tr.stats[k] for k in
                          ("device", "dim", "n_embed_calls",
                           "n_cache_hits", "n_cache_texts", "embed_ms")},
        "gpu_mem_gb": gpu_gb,
        "chunks": len(rich), "native_stats": native.stats,
    }
    run.save_result(result)

    print("=" * 64)
    print(f"{'配置':<28} {'R@10':>8} {'R@20':>8} {'MRR@10':>8}")
    print(f"{'原生BGE(无前缀·对称)':<26} {nat_np['R@10']:>8.4f} "
          f"{nat_np['R@20']:>8.4f} {nat_np['MRR@10']:>8.4f}")
    print(f"{'原生BGE(+前缀·官方参照)':<25} {nat_pf['R@10']:>8.4f} "
          f"{nat_pf['R@20']:>8.4f} {nat_pf['MRR@10']:>8.4f}")
    print(f"{'LoRA微调(无前缀·对称)':<26} {lora_np['R@10']:>8.4f} "
          f"{lora_np['R@20']:>8.4f} {lora_np['MRR@10']:>8.4f}")
    d = result["delta_vs_native_symmetric"]
    print(f"{'Δ(LoRA−原生对称)':<27} {d['R@10']:>+8.4f} "
          f"{d['R@20']:>+8.4f} {d['MRR@10']:>+8.4f}")
    print("-" * 64)
    print(f"{'分区域(防泄漏视角)':<28} {'R@10':>8} {'R@20':>8} {'MRR@10':>8}")

    def _fmt(m: dict[str, Any], k: str) -> str:
        return f"{m[k]:>8.4f}" if m[k] is not None else f"{'-':>8}"

    for reg, mm in by_region.items():
        for tag, m in (("原生", mm["native"]), ("LoRA", mm["lora"])):
            print(f"{reg + '·' + tag:<28} {_fmt(m, 'R@10')} "
                  f"{_fmt(m, 'R@20')} {_fmt(m, 'MRR@10')}")
    print(f"结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
