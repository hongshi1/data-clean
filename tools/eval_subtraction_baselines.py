#!/usr/bin/env python3
"""减法模块基线对比: 七方法×四指标 + 图表1.

对应文档: 72号(方法详解与基线对比).
回答: 不同方法(排序截断/随机删/只归一/三级减法/oracle)的效果差在哪.

方法:
  B0-raw        无模块(原始整块直入)         — 现状基线
  B0-norm       仅粒度归一(不减法)           — 粒度消融
  B1-topk3-raw  BGE相似度top-3截断(原始)     — 通用RAG"排序式减法"
  B1-topk3-norm BGE top-3截断+粒度归一       — 排序式减法+粒度
  B5-rand3-norm 随机删3块+归一(seed=42)      — 压缩伪效应对照
  B3-ours       三级过滤减法模块(本文)       — F1+F2+F3
  B4-oracle     gold直选+归一                — 选择上限

指标(按"成功率改变×gold误删"框架):
  检出成功率      17个已知违例中NLI判出"不一致"的比例(τ=0.5)
                 — 相对B0-raw的Δ即"成功率的改变"
  误删定位gold    35个定位gold证据引用(违例位置块)中被删数(0=安全);
                 注: 定位金标≠反驳金标, 见73号审计
  证据压缩        保留块数(97块总量)
  伪矛盾率(swap)  池×异项答案触发refute — NLI自身scope盲区的注脚指标
用法: python tools/eval_subtraction_baselines.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import torch  # noqa: E402,F401 (加载顺序约束, 见68号)

from algorithms.consistency.evidence_subtractor import (  # noqa: E402
    normalize_granularity, subtract,
)

VIO_PATH = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
OUT_JSON = BASE / "data/gjb_438c/localization_gold/subtraction_baselines_v1.json"
OUT_FIG = BASE / "docs/srs_project/fig71_baselines.png"
TAU = 0.5
N_SWAP = 5


def load_instances() -> list[dict]:
    return [json.loads(line) for line in VIO_PATH.open(encoding="utf-8")]


def build_premises(method: str, ins: dict, rng: random.Random) -> tuple[list[str], set[str]]:
    """按方法构造premises与选中的块ID集(供gold保留率计算)."""
    ev = ins["evidence"]
    answer = ins["answer"]
    question = ins["question"]
    if method == "B0-raw":
        return [str(e.get("text", "")) for e in ev], {e["evidence_id"] for e in ev}
    if method == "B0-norm":
        stmts, ids = [], set()
        for e in ev:
            norm = normalize_granularity(str(e.get("text", "")))
            if norm["statements"]:
                stmts.extend(norm["statements"])
                ids.add(e["evidence_id"])
        return stmts, ids
    if method in ("B1-topk3-raw", "B1-topk3-norm"):
        sims = _bge_rank(question, answer, ev)
        top = sorted(range(len(ev)), key=lambda i: -sims[i])[:3]
        picked = [ev[i] for i in top]
        if method.endswith("raw"):
            return ([str(e.get("text", "")) for e in picked],
                    {e["evidence_id"] for e in picked})
        stmts, ids = [], set()
        for e in picked:
            norm = normalize_granularity(str(e.get("text", "")))
            if norm["statements"]:
                stmts.extend(norm["statements"])
                ids.add(e["evidence_id"])
        return stmts, ids
    if method == "B5-rand3-norm":
        picked = rng.sample(ev, min(3, len(ev)))
        stmts, ids = [], set()
        for e in picked:
            norm = normalize_granularity(str(e.get("text", "")))
            if norm["statements"]:
                stmts.extend(norm["statements"])
                ids.add(e["evidence_id"])
        return stmts, ids
    if method == "B3-ours":
        pack = subtract(question, answer, ev)
        stmts = [s for k in pack["kept"] for s in k["statements"]]
        return stmts, {k["evidence_id"] for k in pack["kept"]}
    if method == "B4-oracle":
        golds = set(ins["gold_evidence_refs"])
        stmts, ids = [], set()
        for e in ev:
            if e["evidence_id"] not in golds:
                continue
            norm = normalize_granularity(str(e.get("text", "")))
            if norm["statements"]:
                stmts.extend(norm["statements"])
                ids.add(e["evidence_id"])
        return stmts, ids
    raise ValueError(f"unknown method: {method}")


_BGE_CACHE: dict = {}


def _bge_rank(question: str, answer: str, ev: list[dict]) -> list[float]:
    """BGE相似度排序(问题+答案 vs 各证据块), 结果缓存."""
    from algorithms.common.bge_local import BgeLocal
    global _BGE_CACHE
    if "model" not in _BGE_CACHE:
        bge = BgeLocal()
        if bge.ensure() not in ("cuda", "gpu", "cpu"):
            raise RuntimeError(f"BGE不可用: {bge.last_error}")
        _BGE_CACHE["model"] = bge
    bge = _BGE_CACHE["model"]
    qa = f"{question} {answer}"
    texts = [qa] + [str(e.get("text", "")) for e in ev]
    key = tuple(texts)
    if key not in _BGE_CACHE:
        emb = {}
        for i in range(0, len(texts), 8):
            emb.update(bge.embed(texts[i:i + 8]))
        _BGE_CACHE[key] = emb
    emb = _BGE_CACHE[key]
    qv = emb[qa]

    def cos(u, v):
        dot = sum(a * b for a, b in zip(u, v))
        nu = sum(a * a for a in u) ** 0.5
        nv = sum(a * a for a in v) ** 0.5
        return dot / (nu * nv) if nu and nv else 0.0
    return [cos(qv, emb[t]) for t in texts[1:]]


def main() -> int:
    instances = load_instances()
    n = len(instances)
    print(f"实例: {n}条(全期望refute), τ={TAU}, swap目标/实例={N_SWAP}")

    from algorithms.consistency.nli_local import NliLocal
    nli = NliLocal("mdeberta")
    if nli.ensure() not in ("cuda", "gpu", "cpu"):
        print(f"NLI不可用: {nli.last_error}")
        return 1

    # swap目标: 每实例取5个异检测项实例的答案(文件序, 确定性)
    swap_targets: list[list[int]] = []
    for i, ins in enumerate(instances):
        cands = [j for j, other in enumerate(instances)
                 if j != i and other["item_id"] != ins["item_id"]]
        swap_targets.append(cands[:N_SWAP])
    n_swaps = sum(len(t) for t in swap_targets)

    methods = ["B0-raw", "B0-norm", "B1-topk3-raw", "B1-topk3-norm",
               "B5-rand3-norm", "B3-ours", "B4-oracle"]
    results: dict[str, dict] = {}

    for method in methods:
        rng = random.Random(42)
        pools: list[list[str]] = []
        kept_ids: list[set[str]] = []
        for ins in instances:
            stmts, ids = build_premises(method, ins, rng)
            pools.append(stmts)
            kept_ids.append(ids)

        # recall: pool_i vs 自己的answer
        pairs = []
        index = []  # (instance_idx, is_swap, swap_j)
        for i, ins in enumerate(instances):
            for p in pools[i]:
                pairs.append((p, ins["answer"]))
                index.append((i, False, -1))
        # swap误报: pool_i vs 他人answer
        for i, targets in enumerate(swap_targets):
            for j in targets:
                for p in pools[i]:
                    pairs.append((p, instances[j]["answer"]))
                    index.append((i, True, j))
        t0 = time.perf_counter()
        probs = nli.predict(pairs)
        dt = time.perf_counter() - t0

        # 实例级聚合
        own_contra: list[float] = [0.0] * n
        swap_contra: dict[tuple[int, int], float] = {}
        for (i, is_swap, j), pr in zip(index, probs):
            c = pr.get("p_contra", 0.0)
            if not is_swap:
                own_contra[i] = max(own_contra[i], c)
            else:
                k = (i, j)
                swap_contra[k] = max(swap_contra.get(k, 0.0), c)

        n_refute = sum(1 for c in own_contra if c > TAU)
        n_fp = sum(1 for c in swap_contra.values() if c > TAU)
        gold_keep = sum(len(set(instances[i]["gold_evidence_refs"]) & kept_ids[i])
                        for i in range(n))
        gold_all = sum(len(ins["gold_evidence_refs"]) for ins in instances)
        gold_deleted = gold_all - gold_keep
        results[method] = {
            "success_rate": f"{n_refute}/{n}",
            "success_rate_pct": round(100 * n_refute / n, 1),
            "delta_success_pct": round(100 * n_refute / n
                                       - results["B0-raw"]["success_rate_pct"], 1)
            if "B0-raw" in results else 0.0,
            "valid_evidence_deleted": f"{gold_deleted}/{gold_all}",
            "gold_deleted_note": "定位gold(违例位置块)被删数; 定位金标≠反驳金标",
            "gold_retention_pct": round(100 * gold_keep / gold_all, 1),
            "blocks_kept": sum(len(ids) for ids in kept_ids),
            "swap_fp_pct": round(100 * n_fp / max(n_swaps, 1), 1),
            "stmts_per_inst": round(sum(len(p) for p in pools) / n, 1),
            "nli_pairs": len(pairs),
            "nli_s": round(dt, 1),
            "per_inst_contra": [round(c, 3) for c in own_contra],
        }
        print(f"{method:<15} 成功率={results[method]['success_rate']} "
              f"({results[method]['success_rate_pct']:4.1f}%)  "
              f"Δ={results[method]['delta_success_pct']:+5.1f}pt  "
              f"误删定位gold={gold_deleted}/{gold_all}  "
              f"保留块={results[method]['blocks_kept']}  "
              f"伪矛盾率={results[method]['swap_fp_pct']:4.1f}%")

    # ── 图表1: 双指标条形图 ─────────────────────────────
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    labels = {"B0-raw": "无模块\n(原始整块)", "B0-norm": "仅粒度归一\n(不减法)",
              "B1-topk3-raw": "BGE截断\n(原始)", "B1-topk3-norm": "BGE截断\n+归一",
              "B5-rand3-norm": "随机删\n@同压缩", "B3-ours": "减法模块\n(本文)",
              "B4-oracle": "gold直选\n(上限)"}
    xs = [labels[m] for m in methods]
    recall = [results[m]["success_rate_pct"] for m in methods]
    gold_del = [int(results[m]["valid_evidence_deleted"].split("/")[0])
                for m in methods]
    blocks = [results[m]["blocks_kept"] for m in methods]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    xpos = list(range(len(methods)))
    w = 0.38
    ax.bar([x - w / 2 for x in xpos], recall, w,
           color="#2e7dd1", label="检出成功率%(越高越好)")
    ax.bar([x + w / 2 for x in xpos], gold_del, w,
           color="#d95f02", label="误删定位gold数/35(越低越好)")
    for x, r, d, bk in zip(xpos, recall, gold_del, blocks):
        ax.text(x - w / 2, r + 1.5, f"{r:.0f}%", ha="center", fontsize=9)
        ax.text(x + w / 2, d + 0.6, f"{d}个", ha="center", fontsize=9)
        ax.text(x, -11.5, f"保留{bk}块", ha="center", fontsize=8,
                color="#444444")
    ax.set_xticks(xpos, xs, fontsize=9)
    ax.set_ylim(-16, 105)
    ax.set_ylabel("检出成功率 (%) / 误删有效证据 (个)")
    ax.set_title("图表1 证据减法模块 vs 六基线: 一致性校验成功率与有效证据误删 "
                 "(17真实违例, τ=0.5)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=150)
    print(f"\n图表已保存: {OUT_FIG}")

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"结果已写入: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
