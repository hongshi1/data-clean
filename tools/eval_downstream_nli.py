#!/usr/bin/env python3
"""端到端评测: 打分/筛选层介入前后, 下游NLI裁决的查准查全对比.

对应文档: 69号(下游NLI裁决的端到端评测 — 回答"提点还是掉点").
问题: 筛选层(打分+门控)对最终NLI一致性检测的价值:
  - 提点 = 精度提升(滤掉NLI的假阳性)
  - 掉点 = 召回损失(滤掉了真冲突)
  - 成本 = NLI调用量节省
管线:
  B0-report_all   全报不筛选(无NLI)            — 精度下限锚点
  B1-nli_only     NLI直判全部候选              — 无筛选层的基线
  P1-rule_gate    规则门控→NLI(门内才调用)      — 0.02ms换60ms/对
  P2-fusion_rank  廉价融合排序topK→NLI          — 预算控制
  P3-nli_veto     NLI直判+规则否决              — 反向门控
  P4-full_fusion  全融合(含NLI)阈值             — 68号combined
指标: smell视图(T+NR为正)主报 + strict视图(T为正)副报;
     阈值扫描取best-F1工作点 + 固定τ=0.5工作点; TP/FP/FN计数.
用法: python tools/eval_downstream_nli.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

# 顺序约束: torch先于numpy链(Windows OpenMP冲突, 见68号文档)
import torch  # noqa: E402,F401

from algorithms.context_linking.pair_scorers import (  # noqa: E402
    make_bge_scorer, make_nli_scorer, score_combined,
    score_lexical_jaccard, score_rule_scope, score_section_proximity,
    score_template_mask,
)

PAIRS_PATH = BASE / "data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl"
LABELS_PATH = BASE / "data/gjb_438c/atom_candidates_v1/labels_v1.jsonl"
OUT_PATH = BASE / "data/gjb_438c/atom_candidates_v1/downstream_nli_eval_v1.json"


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def evaluate(pred: list[int], gold: list[int]) -> dict:
    tp = sum(1 for y, g in zip(pred, gold) if y == 1 and g == 1)
    fp = sum(1 for y, g in zip(pred, gold) if y == 1 and g == 0)
    fn = sum(1 for y, g in zip(pred, gold) if y == 0 and g == 1)
    p, r, f = prf(tp, fp, fn)
    return {"precision": round(p, 4), "recall": round(r, 4),
            "f1": round(f, 4), "tp": tp, "fp": fp, "fn": fn}


def sweep_best_f1(scores: list[float], gold: list[int],
                  gate: list[bool] | None = None) -> dict:
    """阈值扫描取best-F1; gate=False的对不参与(自动判负)."""
    cands = [0.0, 0.05] + [round(x * 0.05, 2) for x in range(1, 20)]
    best = {"f1": -1.0}
    for tau in cands:
        pred = []
        for i, s in enumerate(scores):
            if gate is not None and not gate[i]:
                pred.append(0)
            else:
                pred.append(1 if s > tau else 0)
        ev = evaluate(pred, gold)
        if ev["f1"] > best["f1"]:
            best = {"tau": tau, **ev}
    return best


def main() -> int:
    pairs = [json.loads(line) for line in PAIRS_PATH.open(encoding="utf-8")]
    labels = {r["pair_id"]: r["label"] for r
              in (json.loads(line) for line in LABELS_PATH.open(encoding="utf-8"))}
    for p in pairs:
        p["label"] = labels[p["pair_id"]]
    n = len(pairs)

    gold_smell = [1 if p["label"] in ("true_conflict", "needs_review") else 0
                  for p in pairs]
    gold_strict = [1 if p["label"] == "true_conflict"
                   else (0 if p["label"] == "legit_variance" else -1)
                   for p in pairs]

    # ── 信号预计算 ─────────────────────────────────────
    rule = [score_rule_scope(p["decision"]) for p in pairs]
    templ = [score_template_mask(p["left"]["context"], p["right"]["context"])
             for p in pairs]
    _ = [score_lexical_jaccard(p["left"]["context"], p["right"]["context"])
         for p in pairs]
    _ = [score_section_proximity(p["left"]["section"], p["right"]["section"])
         for p in pairs]

    from algorithms.common.bge_local import BgeLocal
    bge = BgeLocal()
    bge_ok = bge.ensure() in ("cuda", "gpu", "cpu")
    if bge_ok:
        ctxs = sorted({p[k]["context"] for p in pairs
                       for k in ("left", "right")})
        emb: dict = {}
        for i in range(0, len(ctxs), 8):
            emb.update(bge.embed(ctxs[i:i + 8]))
        bsc = make_bge_scorer(emb)
        bge_s = [bsc(p["left"]["context"], p["right"]["context"])
                 for p in pairs]
    else:
        print(f"BGE不可用: {bge.last_error}")
        bge_s = [0.0] * n

    from algorithms.consistency.nli_local import NliLocal
    nli = NliLocal("mdeberta")
    nli_ok = nli.ensure() in ("cuda", "gpu", "cpu")
    if nli_ok:
        nsc = make_nli_scorer(nli.predict)
        nli_s = [nsc(p["left"]["context"], p["right"]["context"])
                 for p in pairs]
    else:
        print(f"NLI不可用: {nli.last_error}")
        nli_s = [0.0] * n

    cheap = [score_combined({"rule": rule[i], "template": templ[i],
                             "bge": bge_s[i]}) for i in range(n)]
    full = [score_combined({"rule": rule[i], "template": templ[i],
                            "bge": bge_s[i], "nli": nli_s[i]})
            for i in range(n)]

    # ── 管线定义与评测 ─────────────────────────────────
    gate_rule = [r >= 0.5 for r in rule]           # strong+unknown进NLI
    gate_strict = [r == 1.0 for r in rule]          # 仅strong

    results: dict[str, dict] = {}

    # B0: 全报不筛选(精度下限锚点, 零NLI成本)
    results["B0-report_all"] = {
        "smell": evaluate([1] * n, gold_smell),
        "nli_calls": 0, "desc": "全报不筛选(锚点)"}

    # B1: NLI直判全部(无筛选层基线)
    results["B1-nli_only"] = {
        "smell": sweep_best_f1(nli_s, gold_smell),
        "fixed_0.5": evaluate([1 if s > 0.5 else 0 for s in nli_s], gold_smell),
        "nli_calls": n, "desc": "NLI直判全部候选(基线)"}

    # P1: 规则门控→NLI(门内才调用)
    results["P1-rule_gate"] = {
        "smell": sweep_best_f1(nli_s, gold_smell, gate=gate_rule),
        "fixed_0.5": evaluate(
            [1 if (g and s > 0.5) else 0
             for g, s in zip(gate_rule, nli_s)], gold_smell),
        "nli_calls": sum(gate_rule), "desc": "规则门(≥0.5)→NLI"}

    # P2: 廉价融合排序topK→NLI
    order = sorted(range(n), key=lambda i: -cheap[i])
    for k in (6, 12, 24):
        sel = [i in set(order[:k]) for i in range(n)]
        results[f"P2-fusion_rank@{k}"] = {
            "smell": sweep_best_f1(nli_s, gold_smell, gate=sel),
            "fixed_0.5": evaluate(
                [1 if (g and s > 0.5) else 0
                 for g, s in zip(sel, nli_s)], gold_smell),
            "nli_calls": k, "desc": f"廉价融合top-{k}→NLI"}

    # P3: NLI直判+强规则否决(反向门控)
    results["P3-nli_veto"] = {
        "smell": sweep_best_f1(nli_s, gold_smell, gate=gate_strict),
        "fixed_0.5": evaluate(
            [1 if (g and s > 0.5) else 0
             for g, s in zip(gate_strict, nli_s)], gold_smell),
        "nli_calls": n, "desc": "NLI全判+同作用域否决"}

    # P4: 全融合阈值(含NLI)
    results["P4-full_fusion"] = {
        "smell": sweep_best_f1(full, gold_smell),
        "fixed_0.5": evaluate([1 if s > 0.5 else 0 for s in full], gold_smell),
        "nli_calls": n, "desc": "全融合(r+t+b+n)阈值"}

    # ── 输出对比表 ────────────────────────────────────
    base = results["B1-nli_only"]["smell"]
    print(f"\n端到端评测(smell视图: 正=真冲突+需澄清{sum(gold_smell)}例, "
          f"负=合理差异+抽取错误{len(pairs) - sum(gold_smell)}例)")
    print(f"\n{'管线':<20} {'P':>6} {'R':>6} {'F1':>6} {'TP':>4} {'FP':>4} "
          f"{'FN':>4} {'NLI调用':>7} {'ΔF1':>7} {'判定':>6}  τ*")
    print("-" * 88)
    for name, r in results.items():
        s = r["smell"]
        d_f1 = s["f1"] - base["f1"] if "tau" in s and name != "B1-nli_only" else 0.0
        verdict = "提点" if d_f1 > 0.005 else ("掉点" if d_f1 < -0.005 else "持平")
        tau_s = f"{s.get('tau', '-')}"
        print(f"{name:<20} {s['precision']:>6.3f} {s['recall']:>6.3f} "
              f"{s['f1']:>6.3f} {s['tp']:>4} {s['fp']:>4} {s['fn']:>4} "
              f"{r['nli_calls']:>7} {d_f1:>+7.3f} {verdict:>6}  {tau_s}")

    print("\n固定工作点(τ=0.5)对比:")
    print(f"{'管线':<20} {'P':>6} {'R':>6} {'F1':>6} {'FP':>4} {'FN':>4}")
    for name, r in results.items():
        if "fixed_0.5" not in r:
            continue
        f = r["fixed_0.5"]
        print(f"{name:<20} {f['precision']:>6.3f} {f['recall']:>6.3f} "
              f"{f['f1']:>6.3f} {f['fp']:>4} {f['fn']:>4}")

    # strict视图副报(1正例, 仅方向参考)
    strict_pairs = [i for i, g in enumerate(gold_strict) if g >= 0]
    gs = [gold_strict[i] for i in strict_pairs]
    print(f"\nstrict视图(真冲突vs合理差异, {len(strict_pairs)}对, "
          f"正例{sum(gs)}):")
    for name, (scores, gate) in {
        "B1-nli_only": (nli_s, None),
        "P1-rule_gate": (nli_s, gate_rule),
        "P3-nli_veto": (nli_s, gate_strict),
        "P4-full_fusion": (full, None),
    }.items():
        ss = [scores[i] for i in strict_pairs]
        gg = [gate[i] if gate else True for i in strict_pairs]
        pred = [1 if (g and s > 0.5) else 0 for s, g in zip(ss, gg)]
        ev = evaluate(pred, gs)
        print(f"  {name:<20} P={ev['precision']:.3f} R={ev['recall']:.3f} "
              f"TP={ev['tp']} FP={ev['fp']} FN={ev['fn']} (τ=0.5)")

    OUT_PATH.write_text(json.dumps({
        "n_pairs": n, "results": results,
        "nli_calls_saved": {
            k: n - r["nli_calls"] for k, r in results.items()},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
