r"""效率基准(T7): 构建时间/查询延迟p50/p95/参数量/显存.

方法: BM25-doc / BM25-unit / O1-unit / O1+Rerank / Token-MaxSim
场景: GJB表池(1207表/13402单元), 100查询样本(确定性前100)

用法: python tools/eval/efficiency_benchmark.py
产出: results/_efficiency.json + runs归档
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

V3 = BASE / "data/gjb_438c/data_assets/evalsets/V3"
RESULTS = BASE / "data/gjb_438c/data_assets/evalsets/results"


def pct(v: list[float], q: float) -> float:
    s = sorted(v)
    return s[int(q * (len(s) - 1))]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ds = json.loads((V3 / "gjb_ure_v4.json").read_text(encoding="utf-8"))
    pool = [c for c in ds["corpus"] if c["type"] == "table"]
    queries = [q for q in ds["queries"]
               if q["scene"] in ("table_deep_v3", "table_deep_v4")
               and q["split"] == "eval"][:100]
    print(f"效率基准: {len(pool)}表, {len(queries)}查询样本")

    from algorithms.context_linking import make_baseline
    from algorithms.context_linking.evidence_recall import (
        EvidenceStore,
        MultiHeadRecall,
        UnitFocusedRerank,
    )
    from algorithms.common import bge_local

    results = {}

    def bench(name, build_fn, query_fn, params, note=""):
        t0 = time.time()
        obj = build_fn()
        build_s = time.time() - t0
        lats = []
        for q in queries:
            t1 = time.perf_counter()
            query_fn(obj, q["query"])
            lats.append((time.perf_counter() - t1) * 1000)
        results[name] = {
            "build_s": round(build_s, 2),
            "latency_p50_ms": round(pct(lats, 0.5), 1),
            "latency_p95_ms": round(pct(lats, 0.95), 1),
            "params": params, "note": note,
        }
        r = results[name]
        print(f"  {name:<14s} build={r['build_s']:>7.1f}s "
              f"p50={r['latency_p50_ms']:>8.1f}ms "
              f"p95={r['latency_p95_ms']:>8.1f}ms  {note}")

    # 词面系(CPU)
    store = EvidenceStore.from_ure(pool)
    bench("BM25-doc", lambda: make_baseline("BM25-doc", store),
          lambda h, q: h.score_query(q), 0, "纯CPU倒排索引")
    bench("BM25-unit", lambda: make_baseline("BM25-unit", store),
          lambda h, q: h.score_query(q), 0, "单元级倒排(13402单元)")

    # 语义系(GPU)
    enc = bge_local.BgeLocal(cache_path=None)
    enc.ensure()
    import torch
    torch.cuda.reset_peak_memory_stats() if torch.cuda.is_available() \
        else None
    bench("O1-unit", lambda: MultiHeadRecall(store, enc),
          lambda rc, q: rc.recall(q, pool="table", topk=50),
          326_000_000, "BGE-large-zh冻结+13K单元矩阵")

    # 两阶段
    from algorithms.blackboard.reranker import BgeReranker
    rr = BgeReranker()
    rr.ensure()
    rc = MultiHeadRecall(store, enc)
    s2 = UnitFocusedRerank(reranker=rr, unit_topn=2, blend=0.1)

    def two_stage(_rc, q):
        r50 = _rc.recall(q, pool="table", topk=50)
        return s2.rerank(q, r50, store)

    lats = []
    for q in queries:
        t1 = time.perf_counter()
        two_stage(rc, q["query"])
        lats.append((time.perf_counter() - t1) * 1000)
    mem_gb = (torch.cuda.max_memory_allocated() / 1e9
              if torch.cuda.is_available() else 0.0)
    results["O1+Rerank"] = {
        "build_s": results["O1-unit"]["build_s"],
        "latency_p50_ms": round(pct(lats, 0.5), 1),
        "latency_p95_ms": round(pct(lats, 0.95), 1),
        "params": 326_000_000 + 568_000_000,
        "note": f"BGE召回+Reranker-v2-m3精排(50对), 峰值显存{mem_gb:.1f}GB",
    }
    r = results["O1+Rerank"]
    print(f"  {'O1+Rerank':<14s} build={r['build_s']:>7.1f}s "
          f"p50={r['latency_p50_ms']:>8.1f}ms "
          f"p95={r['latency_p95_ms']:>8.1f}ms  {r['note']}")

    out = {
        "protocol": ("效率基准: GJB表池1207/13402单元, 100查询样本, "
                     "GPU=RTX4060-8GB; 参数量=冻结模型参数(非训练)"),
        "results": results,
        "context": {
            "gjb_build_from_S7": "1586owner/19492单元 92s",
            "wtq_build_from_S8": "2100owner/42394单元 10s",
            "duret_build_from_S8": "10000owner/81225单元 1715s",
        },
    }
    (RESULTS / "_efficiency.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {RESULTS / '_efficiency.json'}")

    from run_utils import open_run
    handle = open_run("efficiency_benchmark", {
        "pool": "GJB tables 1207", "n_queries": len(queries)})
    handle.save_result(results)
    print(f"run saved: {handle.path}")


if __name__ == "__main__":
    main()
