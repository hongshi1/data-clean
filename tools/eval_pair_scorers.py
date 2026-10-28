#!/usr/bin/env python3
"""打分策略对比实验: 六种打分器在48对人工标注集上的评测.

对应文档: 68号(打分方式调研+案例深读+对比实验).
打分器: rule_scope(FS固定规则) / lexical_jaccard(词法) / template_mask(模板漂移)
        / section_proximity(章节邻近) / bge_cosine(语义) / nli_contra(NLI矛盾)
        / combined(线性融合)
指标: AUC-strict(真冲突vs合理差异) / AUC-smell(真+需澄清vs其余) / P@7
用法: python tools/eval_pair_scorers.py [--skip-nli] [--skip-bge]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

# 顺序约束: torch必须先于algorithms.context_linking的numpy链加载,
# 否则Windows下OpenMP运行时(libiomp5md.dll)冲突→CUDA推理静默崩溃.
import torch  # noqa: E402,F401  (加载顺序修复, 见68号文档)

from algorithms.context_linking.pair_scorers import (  # noqa: E402
    make_bge_scorer, make_nli_scorer, score_combined,
    score_lexical_jaccard, score_rule_scope, score_section_proximity,
    score_template_mask,
)

PAIRS_PATH = BASE / "data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl"
LABELS_PATH = BASE / "data/gjb_438c/atom_candidates_v1/labels_v1.jsonl"


def rank_auc(scores: list[float], labels01: list[int]) -> float:
    """秩AUC(Mann-Whitney U, 含并列校正)."""
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1  # 1-indexed平均秩
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    pos = [r for r, y in zip(ranks, labels01) if y == 1]
    neg = [r for r, y in zip(ranks, labels01) if y == 0]
    if not pos or not neg:
        return float("nan")
    u = sum(pos) - len(pos) * (len(pos) + 1) / 2
    return u / (len(pos) * len(neg))


def precision_at_k(scores: list[float], labels01: list[int], k: int) -> float:
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    top = order[:k]
    hits = sum(1 for i in top if labels01[i] == 1)
    return hits / max(k, 1)


def _ensure_with_retry(client, attempts: int = 3, wait_s: float = 2.0) -> str:
    """ensure带重试: 并行会话的GPU争用导致偶发加载失败, 显式打印错误.

    注意: 成功时返回"cuda"(BgeLocal/NliLocal以_device为mode), 不是"gpu".
    """
    import time as _t
    mode = client.ensure()
    for i in range(attempts - 1):
        if mode in ("cuda", "gpu", "cpu"):
            return mode
        print(f"ensure失败({getattr(client, 'model_key', 'model')}): "
              f"{client.last_error} — 重试{i + 1}/{attempts - 1}")
        _t.sleep(wait_s)
        client._ready = False  # noqa: SLF001 — 重置以重走加载
        mode = client.ensure()
    return mode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-nli", action="store_true")
    ap.add_argument("--skip-bge", action="store_true")
    args = ap.parse_args()

    pairs = [json.loads(line) for line in PAIRS_PATH.open(encoding="utf-8")]
    labels = {r["pair_id"]: r["label"] for r
              in (json.loads(line) for line in LABELS_PATH.open(encoding="utf-8"))}
    for p in pairs:
        p["label"] = labels[p["pair_id"]]

    # ── 廉价打分器(纯函数) ──────────────────────────────
    n = len(pairs)
    t0 = time.perf_counter()
    runs: dict[str, list[float]] = {
        "rule_scope": [score_rule_scope(p["decision"]) for p in pairs],
        "lexical_jaccard": [score_lexical_jaccard(
            p["left"]["context"], p["right"]["context"]) for p in pairs],
        "template_mask": [score_template_mask(
            p["left"]["context"], p["right"]["context"]) for p in pairs],
        "section_proximity": [score_section_proximity(
            p["left"]["section"], p["right"]["section"]) for p in pairs],
    }
    cheap_ms = (time.perf_counter() - t0) / n * 1000

    # ── BGE(预计算上下文向量; 小批量嵌入规避批处理不稳定) ──
    bge_ms = float("nan")
    if not args.skip_bge:
        from algorithms.common.bge_local import BgeLocal
        ctxs = sorted({p[k]["context"] for p in pairs for k in ("left", "right")})
        bge = BgeLocal()
        if _ensure_with_retry(bge) in ("cuda", "gpu", "cpu"):
            t0 = time.perf_counter()
            emb: dict = {}
            for i in range(0, len(ctxs), 8):
                emb.update(bge.embed(ctxs[i:i + 8]))
            sc = make_bge_scorer(emb)
            runs["bge_cosine"] = [sc(p["left"]["context"], p["right"]["context"])
                                  for p in pairs]
            bge_ms = (time.perf_counter() - t0) / n * 1000
        else:
            print(f"BGE不可用: {bge.last_error}")

    # ── NLI(双向矛盾概率) ──────────────────────────────
    nli_ms = float("nan")
    if not args.skip_nli:
        from algorithms.consistency.nli_local import NliLocal
        nli = NliLocal("mdeberta")
        if _ensure_with_retry(nli) in ("cuda", "gpu", "cpu"):
            t0 = time.perf_counter()
            sc = make_nli_scorer(nli.predict)
            runs["nli_contra"] = [sc(p["left"]["context"], p["right"]["context"])
                                  for p in pairs]
            nli_ms = (time.perf_counter() - t0) / n * 1000
        else:
            print(f"NLI不可用: {nli.last_error}")

    # ── 融合(全部可用信号等权) ─────────────────────────
    runs["combined"] = [score_combined({
        "rule": runs["rule_scope"][i], "template": runs["template_mask"][i],
        "bge": runs.get("bge_cosine", [0.0] * n)[i],
        "nli": runs.get("nli_contra", [0.0] * n)[i]}) for i in range(n)]

    # ── 指标 ───────────────────────────────────────────
    strict = [1 if p["label"] == "true_conflict" else 0
              if p["label"] == "legit_variance" else -1 for p in pairs]
    smell = [1 if p["label"] in ("true_conflict", "needs_review")
             else 0 for p in pairs]

    print(f"\n标注集: {n}对 = "
          f"T+{smell.count(1) - 1}NR vs L{strict.count(0)}+E{smell.count(0) - strict.count(0)}")
    print(f"\n{'打分器':<18} {'AUC-strict':>10} {'AUC-smell':>10} "
          f"{'P@7':>6} {'ms/对':>8}")
    print("-" * 58)
    results: dict[str, dict] = {}
    for name, scores in runs.items():
        si = [s for s, y in zip(scores, strict) if y >= 0]
        sy = [y for y in strict if y >= 0]
        auc_s = rank_auc(si, sy)
        auc_w = rank_auc(scores, smell)
        p7 = precision_at_k(scores, smell, 7)
        cost = {"rule_scope": cheap_ms / 4, "lexical_jaccard": cheap_ms / 4,
                "template_mask": cheap_ms / 4, "section_proximity": cheap_ms / 4,
                "bge_cosine": bge_ms, "nli_contra": nli_ms,
                "combined": (cheap_ms + bge_ms + nli_ms) if nli_ms == nli_ms else float("nan")
                }.get(name, cheap_ms)
        cost_s = f"{cost:.3f}" if cost == cost else "n/a"
        print(f"{name:<18} {auc_s:>10.3f} {auc_w:>10.3f} {p7:>6.3f} {cost_s:>8}")
        results[name] = {"auc_strict": round(auc_s, 4), "auc_smell": round(auc_w, 4),
                         "p_at_7": round(p7, 4)}

    # ── 各标签类的均值画像 ─────────────────────────────
    print("\n各标签类得分画像(均值):")
    classes = ["true_conflict", "needs_review", "legit_variance", "extraction_error"]
    print(f"{'打分器':<18}" + "".join(f"{c[:12]:>14}" for c in classes))
    for name, scores in runs.items():
        row = [f"{sum(s for s, p in zip(scores, pairs) if p['label'] == c) / max(sum(1 for p in pairs if p['label'] == c), 1):.3f}"
               for c in classes]
        print(f"{name:<18}" + "".join(f"{v:>14}" for v in row))

    out = BASE / "data/gjb_438c/atom_candidates_v1/scorer_eval_v1.json"
    out.write_text(json.dumps({
        "n_pairs": n, "label_dist": {
            c: sum(1 for p in pairs if p["label"] == c) for c in classes},
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
