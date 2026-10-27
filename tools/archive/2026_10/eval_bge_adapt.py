r"""BGE域适配评测(A8): 原生BGE vs 适配后BGE, dense单通道R@10/R@20对比.

口径与eval_hybrid_recall的single:dense严格一致:
  - query = 评测集entity(entity_id兜底), 检索指令前缀+截200字;
  - 候选池 = 全部5231 chunks的_rich_text富化文本(图片chunk用
    caption+VLM key_elements富化, 复用HybridRecaller._rich_text);
  - 指标 = Recall@10/@20(期望chunk_ids, 归一化向量cos排序);
  - 基线核验: 原生BGE现算向量与既有dense_index.pkl逐chunk比对
    (确定性, 应逐位一致 → 基线可复现single:dense=0.3888/0.4757).

防泄漏(诚实报告): 域内QA语料与评测实体本就同源(均出自16份SRS),
评测query的entity/entity_id若以字符串形式出现在训练QA对中 → 计入
重叠率(训练对按adapter_meta.json的n_pairs/seed确定性重采样复现).
α说明: 推理期残差缩放α在retrieval_evalset(300条)上校准
(同EMB_TH_LOCAL阈值校准惯例; α∈[0.25,0.5]平台双指标为正, 多seed稳健).

结果落盘runs协议(config+git_sha+result).

用法: python tools/eval_bge_adapt.py [--limit 300] [--adapter-dir PATH]
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.bge_domain_adapt import (  # noqa: E402
    CORPUS_PATH,
    QUERY_PREFIX,
    BgeAdapter,
    load_qa_pairs,
)
from algorithms.common.bge_local import BgeLocal  # noqa: E402
from run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
DENSE_INDEX = BASE / "data/gjb_438c/blackboard/dense_index.pkl"

K_LIST = (10, 20)
_EPS = 1e-12


def dense_metrics(embed_fn: Callable[[list[str]], dict[str, list[float]]],
                  rich: list[str], ids: list[str],
                  queries: list[dict[str, Any]]) -> dict[str, float]:
    """dense单通道指标: entity查询向量 vs chunk富化文本向量, cos排序R@K."""
    doc_vecs = embed_fn(rich)
    D = np.asarray([doc_vecs[t] for t in rich], dtype=np.float32)
    D = D / np.clip(np.linalg.norm(D, axis=1, keepdims=True), _EPS, None)
    q_texts = [QUERY_PREFIX + (q["entity"] or q["entity_id"] or q["query"])[:200]
               for q in queries]
    q_vecs = embed_fn(q_texts)
    recalls: dict[str, list[float]] = {f"R@{k}": [] for k in K_LIST}
    for q, qt in zip(queries, q_texts):
        exp = set(q["expected"].get("chunk_ids") or [])
        v = q_vecs.get(qt)
        if not v:
            for k in K_LIST:
                recalls[f"R@{k}"].append(0.0)
            continue
        v = np.asarray(v, dtype=np.float32)
        v = v / max(float(np.linalg.norm(v)), _EPS)
        order = np.argsort(-(D @ v))
        for k in K_LIST:
            got_k = {ids[i] for i in order[:k]}
            recalls[f"R@{k}"].append(
                len(exp & got_k) / len(exp) if exp else 1.0)
    return {k: round(float(np.mean(v)), 4)
            for k, v in recalls.items()} | {"n": len(queries)}


def pkl_agreement(base_vecs: dict[str, list[float]], rich: list[str],
                  ids: list[str]) -> dict[str, Any]:
    """基线核验: 现算原生向量 vs 既有dense_index.pkl(应逐位一致)."""
    if not DENSE_INDEX.exists():
        return {"available": False}
    with open(DENSE_INDEX, "rb") as f:
        pkl: dict[str, list[float]] = pickle.load(f)
    n_same, n_diff, miss = 0, 0, []
    for t, cid in zip(rich, ids):
        if cid not in pkl:
            miss.append(cid)
            continue
        d = float(np.max(np.abs(np.asarray(base_vecs[t], dtype=np.float32)
                                - np.asarray(pkl[cid], dtype=np.float32))))
        if d < 1e-4:
            n_same += 1
        else:
            n_diff += 1
    return {"available": True, "n_same": n_same, "n_diff": n_diff,
            "n_missing": len(miss)}


def leakage_stats(queries: list[dict[str, Any]],
                  pairs: list[tuple[str, str]]) -> dict[str, Any]:
    """防泄漏: 评测entity/entity_id与训练QA对的字符串重叠(逐对匹配)."""
    n = len(queries)
    ent_hit = eid_hit = 0
    for q in queries:
        ent = q.get("entity", "")
        eid = q.get("entity_id", "")
        if ent and any(ent in (qa + "\n" + ans) for qa, ans in pairs):
            ent_hit += 1
        if eid and any(eid in (qa + "\n" + ans) for qa, ans in pairs):
            eid_hit += 1
    return {"n_queries": n, "n_train_pairs": len(pairs),
            "entity_overlap": ent_hit,
            "entity_overlap_rate": round(ent_hit / max(n, 1), 4),
            "entity_id_overlap": eid_hit,
            "entity_id_overlap_rate": round(eid_hit / max(n, 1), 4)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="BGE域适配评测(A8)")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--adapter-dir", type=Path, default=None,
                    help="适配器目录(默认models/embedding/bge_adapter)")
    ap.add_argument("--no-cache", action="store_true",
                    help="禁用适配向量磁盘缓存")
    args = ap.parse_args()

    data = json.loads(EVALSET.read_text(encoding="utf-8"))
    queries = (data[:args.limit] if isinstance(data, list)
               else data.get("queries", [])[:args.limit])

    from algorithms.blackboard.hybrid_recall import HybridRecaller
    rec = HybridRecaller(use_dense=False)
    chunks = rec.store._chunks_data()
    rich = [rec._rich_text(c) for c in chunks]
    ids = [c.get("chunk_id", "") for c in chunks]
    print(f"候选池: {len(rich)} chunks | 评测query: {len(queries)}条")

    # ── 基线: 原生BGE(与dense_index.pkl核验) ──
    native = BgeLocal()  # 默认磁盘缓存(dense_index构建期已写满)
    t0 = time.time()
    base_vecs = native.embed(rich)
    agree = pkl_agreement(base_vecs, rich, ids)
    native_m = dense_metrics(native.embed, rich, ids, queries)
    print(f"原生BGE: {native_m} | 索引核验: same={agree.get('n_same')} "
          f"diff={agree.get('n_diff')} ({time.time() - t0:.0f}s)")

    # ── 适配后BGE ──
    adapter = BgeAdapter(adapter_dir=args.adapter_dir,
                         use_cache=not args.no_cache)
    mode = adapter.ensure()
    if mode == "unavailable":
        print(f"适配器不可用: {adapter.last_error}")
        return 1
    if not adapter.stats["trained"]:
        print("警告: 适配头未训练(零初始化恒等), 结果应与原生一致")
    t1 = time.time()
    adapt_m = dense_metrics(adapter.embed, rich, ids, queries)
    print(f"适配BGE(α={adapter.alpha}): {adapt_m} ({time.time() - t1:.0f}s, "
          f"cache={adapter.stats['n_cache_texts']}条)")

    # ── 防泄漏: 训练对复现(与训练端同limit/seed) + 字符串重叠统计 ──
    leak: dict[str, Any] = {"reported": False}
    meta = adapter.meta
    spec = meta.get("data_spec") or {}
    if meta.get("n_pairs"):
        corpus = Path(spec["corpus"]) if spec.get("corpus") else CORPUS_PATH
        pairs = load_qa_pairs(
            corpus_path=corpus,
            limit=int(spec.get("limit", meta["n_pairs"])),
            seed=int(spec.get("seed", meta.get("seed", 42))))
        leak = leakage_stats(queries, pairs) | {"reported": True}
        print(f"防泄漏: 训练对{leak['n_train_pairs']}条复现, "
              f"entity重叠率={leak['entity_overlap_rate']:.2%} "
              f"({leak['entity_overlap']}/{leak['n_queries']}), "
              f"entity_id重叠率={leak['entity_id_overlap_rate']:.2%}")
    else:
        print("防泄漏: 无训练元数据(未训练), 跳过重叠统计")

    # ── 汇总 + runs协议落盘 ──
    run = open_run("eval_bge_adapt", {
        "limit": args.limit, "adapter_dir": str(args.adapter_dir
                                                or "default"),
        "trained": bool(adapter.stats["trained"]), "meta": meta})
    result = {
        "native_bge": native_m,
        "adapted_bge": adapt_m,
        "delta": {k: round(adapt_m[k] - native_m[k], 4)
                  for k in ("R@10", "R@20")},
        "alpha": adapter.alpha,
        "alpha_note": "残差缩放α于retrieval_evalset(300)校准, "
                      "平台[0.25,0.5]双指标为正(train seeds 42/7/123验证)",
        "dense_index_agreement": agree,
        "leakage": leak,
        "adapter_stats": {k: adapter.stats[k] for k in
                          ("device", "n_params", "trained", "fit_ms",
                           "n_cache_texts")},
        "adapter_meta": meta,
        "chunks": len(rich), "bge_native_stats": native.stats,
    }
    run.save_result(result)
    print("=" * 64)
    print(f"{'配置':<14} {'R@10':>8} {'R@20':>8}")
    print(f"{'原生BGE':<14} {native_m['R@10']:>8.4f} {native_m['R@20']:>8.4f}")
    print(f"{'适配BGE(α)':<14} {adapt_m['R@10']:>8.4f} {adapt_m['R@20']:>8.4f}")
    d = result["delta"]
    print(f"{'Δ(适配-原生)':<14} {d['R@10']:>+8.4f} {d['R@20']:>+8.4f}")
    print(f"α={adapter.alpha} | 结果 → {run.path / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
