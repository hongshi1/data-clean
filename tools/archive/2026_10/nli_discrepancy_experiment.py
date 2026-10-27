r"""分歧驱动NLI复核实验: 664条裁决分歧上的条目级评测.

与pair级实验(nli_pair_experiment.py)的本质区别:
  评测单元 = 分歧条目(与M7/M17/M22裁决标签同粒度),
  NLI角色 = 分歧复核器(语义级存在性核对), 非独立检测器.

任务:
  任务1 误报复核: compiler_bug(内容实际一致) vs 真差异(real+benign)
       — NLI矛盾信号应区分两者(本地免费可复现, 替代部分LLM裁决)
  任务2 bug判定: real_bug vs benign(合理差异) — 分dtype诚实报告
       (Actor省略/粒度惯例需要领域知识, NLI理论上限受限)

数据链路:
  final_adjudication.json (664条最终标签, key=pair_NN)
    ⋈ scene_adjudication.json (sc1/3/4/5分歧内容, 285条)
    ⋈ anchor_sc2/llm_adjudication.json (sc2分歧内容, 417条)

用法: python tools/nli_discrepancy_experiment.py [--model mdeberta] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

from algorithms.consistency_check.nli_local import NliLocal  # noqa: E402
from algorithms.consistency_check.nli_discrepancy_review import (  # noqa: E402
    PairContext,
    build_claims_for_discrepancy,
)
from run_utils import open_run  # noqa: E402

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
FINAL_PATH = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
SCENE_ADJ_PATH = BASE / "data/gjb_438c/anchor_v2/scene_adjudication.json"
SC2_ADJ_PATH = BASE / "data/gjb_438c/anchor_sc2/llm_adjudication.json"


def load_items() -> list[dict[str, Any]]:
    """664条最终标签 ⋈ 分歧内容 → 评测条目列表."""
    final = json.loads(FINAL_PATH.read_text(encoding="utf-8"))["final_labels"]
    src: dict[str, dict[str, Any]] = {}
    for p in (SCENE_ADJ_PATH, SC2_ADJ_PATH):
        src.update(json.loads(p.read_text(encoding="utf-8")))
    items = []
    for key, meta in final.items():
        disc = src.get(key)
        if disc is None:
            continue
        items.append({
            "key": key, "pair": meta["pair"], "label": meta["label"],
            "dtype": disc.get("dtype", ""), "evidence": disc.get("evidence", ""),
            "kimi": disc.get("kimi", {}).get("label", ""),
            "glm": disc.get("glm", {}).get("label", ""),
            "disc": {"dtype": disc.get("dtype", ""),
                     "evidence": disc.get("evidence", "")},
        })
    return items


def auc(scores: list[float], labels: list[int]) -> float:
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return 0.5
    ranks = sorted((s, i) for i, s in enumerate(scores))
    rank_of = [0.0] * len(scores)
    i = 0
    while i < len(ranks):
        j = i
        while j < len(ranks) and ranks[j][0] == ranks[i][0]:
            j += 1
        avg = (i + j + 1) / 2.0
        for k in range(i, j):
            rank_of[ranks[k][1]] = avg
        i = j
    r_pos = sum(rank_of[i] for i, y in enumerate(labels) if y == 1)
    return (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mdeberta",
                    choices=["mdeberta", "erlangshen"])
    ap.add_argument("--template", default="closed", choices=["closed", "plain"])
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    items = load_items()
    run = open_run("nli_discrepancy_experiment", {
        "model": args.model, "template": args.template, "limit": args.limit})
    print(f"runs dir: {run.path}")
    print(f"评测条目: {len(items)} "
          f"({dict(Counter(i['label'] for i in items))})")

    ctx = PairContext(PAIR_ROOT)
    claims: list[Any] = []
    claim_order: list[int] = []
    t0 = time.time()
    for idx, it in enumerate(items):
        if args.limit and idx >= args.limit:
            break
        scene, claim = build_claims_for_discrepancy(
            PAIR_ROOT, it["pair"], it["disc"], ctx, template=args.template)
        if claim is None:
            continue
        claim_order.append(idx)
        claims.append((claim.premise, claim.hypothesis))
    print(f"声明构造: {len(claims)}/{len(items)} "
          f"({len(claims)/len(items):.1%}), {time.time()-t0:.1f}s")

    nli = NliLocal(args.model)
    mode = nli.ensure()
    if mode == "unavailable":
        print(f"SKIP: {nli.last_error}")
        return
    verdicts = nli.predict_bidirectional(claims)
    vmap = dict(zip(claim_order, verdicts))
    print(f"NLI推理: {mode}, infer={nli.stats['infer_ms']}ms\n")

    # 逐条目信号
    records: list[dict[str, Any]] = []
    for idx, it in enumerate(items):
        if args.limit and idx >= args.limit:
            break
        rec = {"key": it["key"], "pair": it["pair"], "label": it["label"],
               "dtype": it["dtype"], "evidence": it["evidence"],
               "kimi": it["kimi"], "glm": it["glm"]}
        v = vmap.get(idx)
        if v is not None:
            rec.update({
                "sym_contra": v["sym_contra"],
                "score": round(v["contra_score"], 4),
                "fwd_label": v["fwd"]["label"],
                "fwd_contra": round(v["fwd"]["p_contra"], 4),
                "rev_contra": round(v["rev"]["p_contra"], 4)})
        else:
            rec.update({"sym_contra": False, "score": 0.0,
                        "fwd_label": "no_claim", "fwd_contra": 0.0,
                        "rev_contra": 0.0})
        records.append(rec)

    # ══ 任务1: 误报复核 (compiler=负, 真差异=正) ══
    t1 = [r for r in records if r["fwd_label"] != "no_claim"]
    y1 = [0 if r["label"] == "compiler_bug" else 1 for r in t1]
    s1 = [r["score"] for r in t1]
    f1_flag = [r["sym_contra"] for r in t1]
    tp = sum(1 for y, f in zip(y1, f1_flag) if y == 1 and f)
    fp = sum(1 for y, f in zip(y1, f1_flag) if y == 0 and f)
    fn = sum(1 for y, f in zip(y1, f1_flag) if y == 1 and not f)
    tn = sum(1 for y, f in zip(y1, f1_flag) if y == 0 and not f)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec_ = tp / (tp + fn) if tp + fn else 0.0
    f1s = 2 * prec * rec_ / (prec + rec_) if prec + rec_ else 0.0
    print("══ 任务1: 误报复核 (sym_contra→真差异) ══")
    print(f"  n={len(t1)} (compiler={sum(1 for y in y1 if y == 0)}, "
          f"真差异={sum(y1)})")
    print(f"  P={prec:.3f} R={rec_:.3f} F1={f1s:.3f} "
          f"(tp={tp} fp={fp} fn={fn} tn={tn})")
    print(f"  AUC(score)={auc(s1, y1):.3f}")
    # compiler的复核正确率(判非矛盾)
    comp_ok = sum(1 for r, y in zip(t1, y1) if y == 0 and not r["sym_contra"])
    print(f"  compiler误报正确消化: {comp_ok}/{sum(1 for y in y1 if y == 0)}")

    # ══ 任务2: bug判定 (real=正, benign=负, 排除compiler) ══
    t2 = [r for r in t1 if r["label"] in ("real_bug", "benign_variation")]
    y2 = [1 if r["label"] == "real_bug" else 0 for r in t2]
    s2 = [r["score"] for r in t2]
    print("\n══ 任务2: bug判定 (real vs benign) ══")
    print(f"  总体 AUC={auc(s2, y2):.3f} (n={len(t2)}, real={sum(y2)})")
    by_dtype: dict[str, list] = defaultdict(list)
    for r, y in zip(t2, y2):
        by_dtype[r["dtype"]].append((r["score"], y))
    for dt, pairs in sorted(by_dtype.items()):
        ss, yy = zip(*pairs)
        n_real = sum(yy)
        print(f"  [{dt}] n={len(ss)} real={n_real} AUC={auc(list(ss), list(yy)):.3f}")

    # ══ 对照: NLI与双LLM的一致率 ══
    print("\n══ NLI vs 双LLM 裁决一致率(第三方裁判视角) ══")
    for llm in ("kimi", "glm"):
        both = [r for r in t1 if r[llm]]
        agree = sum(1 for r in both if r[llm] == r["label"])
        print(f"  {llm} vs final: {agree}/{len(both)} = {agree/len(both):.1%}")
    llm_agree = sum(1 for r in t1 if r["kimi"] and r["kimi"] == r["glm"])
    print(f"  kimi vs glm (双LLM一致率): {llm_agree}/{len(t1)} = "
          f"{llm_agree/len(t1):.1%}  ← M17基线38%")

    # ══ 定性样本 ══
    print("\n══ 定性: compiler被正确消化的样本(判非矛盾) ══")
    for r in [r for r in t1 if r["label"] == "compiler_bug"
              and not r["sym_contra"]][:4]:
        print(f"  ✓ {r['key']} [{r['dtype']}] score={r['score']}")
        print(f"    {r['evidence'][:70]}")
    print("\n══ 定性: 真差异高矛盾分样本 ══")
    for r in sorted((r for r in t1 if r["label"] != "compiler_bug"),
                    key=lambda r: -r["score"])[:4]:
        print(f"  [{r['score']:.2f}] {r['key']} [{r['dtype']}] "
              f"label={r['label']}")
        print(f"    {r['evidence'][:70]}")

    run.save_result({"records": records, "summary": {
        "task1": {"n": len(t1), "precision": round(prec, 4),
                  "recall": round(rec_, 4), "f1": round(f1s, 4),
                  "auc": round(auc(s1, y1), 4),
                  "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}},
        "task2": {"n": len(t2), "auc": round(auc(s2, y2), 4),
                  "by_dtype": {dt: round(auc([s for s, _ in v],
                                              [y for _, y in v]), 4)
                               for dt, v in sorted(by_dtype.items())}},
        "nli_stats": dict(nli.stats)}})
    run.log(model=args.model, template=args.template, n_items=len(items),
            n_claims=len(claims))
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
