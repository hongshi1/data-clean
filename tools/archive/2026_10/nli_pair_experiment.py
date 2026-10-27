r"""pair级NLI不一致性检测实验: 366对全量 × 声明模板 × 双模型.

方法: nli_pair_claims把pair(表格/正文/图锚点)编译成闭世界声明对
      → nli_local双向NLI推理 → pair级矛盾分 → final_adjudication金标评测.

评测:
  - 金标: anchor_v2/final_adjudication.json (664条M7/M17/M22裁决,
    按pair聚合: real_bug=正, benign_variation/compiler_bug=负)
  - AUC(rank-based): pair分 = max(min(p_contra_fwd, p_contra_rev))
  - 消融: 模板(closed vs plain) × 模型(mdeberta vs erlangshen)
  - 分通道: enum/aggregate/text 各自的pair分AUC(通道价值分析)

用法: python tools/nli_pair_experiment.py [--model mdeberta] [--limit N]
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

from algorithms.consistency_check.nli_local import NliLocal  # noqa: E402
from algorithms.consistency_check.nli_pair_claims import load_pair_claims  # noqa: E402
from run_utils import open_run  # noqa: E402

PAIR_ROOT = BASE / "data/gjb_438c/pair_dataset"
GOLD_PATH = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
SCENES = ["sc1_usecase_capability", "sc2_flowchart_usecase",
          "sc3_interface_interface", "sc4_flowchart_capability",
          "sc5_function_capability", "sc7_usecase_usecase",
          "sc8_pure_image"]


def load_gold() -> dict[str, str]:
    """裁决金标: pair_id → real_bug | benign (benign_variation/compiler_bug)."""
    d = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for v in d["final_labels"].values():
        pid = v.get("pair", "")
        if v.get("label") == "real_bug":
            out[pid] = "real_bug"
        elif pid not in out:
            out[pid] = "benign"
    return out


def auc(scores: list[float], labels: list[int]) -> float:
    """rank-based AUC (Mann-Whitney). 空侧返回0.5."""
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    if not pos or not neg:
        return 0.5
    ranks = sorted((s, i) for i, s in enumerate(scores))
    rank_of = [0.0] * len(scores)
    i = 0
    while i < len(ranks):  # 并列取平均秩
        j = i
        while j < len(ranks) and ranks[j][0] == ranks[i][0]:
            j += 1
        avg = (i + j + 1) / 2.0
        for k in range(i, j):
            rank_of[ranks[k][1]] = avg
        i = j
    r_pos = sum(rank_of[i] for i, y in enumerate(labels) if y == 1)
    return (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def run_config(model: str, template: str, limit: int | None,
               nli: NliLocal) -> dict[str, Any]:
    """一套(model, template)配置: 全量声明构造+推理+pair级评分."""
    pair_results: dict[str, Any] = {}
    n_claims = 0
    t0 = time.time()
    for scene in SCENES:
        sdir = PAIR_ROOT / scene
        if not sdir.is_dir():
            continue
        pairs = sorted(p for p in sdir.iterdir() if (p / "table.csv").exists()
                       or (p / "meta.json").exists())
        for pdir in pairs:
            if limit and len(pair_results) >= limit:
                break
            pid, claims = load_pair_claims(pdir, template=template)
            if not claims:
                pair_results[pid] = {"scene": scene, "n_claims": 0,
                                     "max_score": 0.0, "sym_count": 0,
                                     "claims": []}
                continue
            verdicts = nli.predict_bidirectional(
                [(c.premise, c.hypothesis) for c in claims])
            cl: list[dict[str, Any]] = []
            for c, v in zip(claims, verdicts):
                cl.append({
                    "why": c.why, "entity": c.entity,
                    "premise": c.premise, "hypothesis": c.hypothesis,
                    "fwd_label": v["fwd"]["label"],
                    "rev_label": v["rev"]["label"],
                    "fwd_contra": round(v["fwd"]["p_contra"], 4),
                    "rev_contra": round(v["rev"]["p_contra"], 4),
                    "score": round(v["contra_score"], 4),
                    "sym_contra": v["sym_contra"]})
            n_claims += len(cl)
            pair_results[pid] = {
                "scene": scene, "n_claims": len(cl),
                "max_score": max(c["score"] for c in cl),
                "sym_count": sum(1 for c in cl if c["sym_contra"]),
                "claims": cl}
    return {"pairs": pair_results, "n_claims": n_claims,
            "elapsed_s": round(time.time() - t0, 1),
            "stats": dict(nli.stats)}


def evaluate(pair_results: dict[str, Any], gold: dict[str, str]) -> dict[str, Any]:
    """金标评测: AUC + sym_contra工作点 + 分通道/分场景."""
    adj: list[tuple[str, str, dict[str, Any]]] = [
        (pid, lab, pr) for pid, lab in gold.items()
        if (pr := pair_results["pairs"].get(pid))]
    if not adj:
        return {"n_adjudicated": 0}
    labels = [1 if lab == "real_bug" else 0 for _, lab, _ in adj]
    scores = [pr["max_score"] for _, _, pr in adj]
    sym_flags = [pr["sym_count"] > 0 for _, _, pr in adj]

    tp = sum(1 for y, f in zip(labels, sym_flags) if y == 1 and f)
    fp = sum(1 for y, f in zip(labels, sym_flags) if y == 0 and f)
    fn = sum(1 for y, f in zip(labels, sym_flags) if y == 1 and not f)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0

    # 分通道: 只用该why的声明算pair分
    per_why: dict[str, dict[str, Any]] = {}
    for why in ("enum", "aggregate", "text"):
        s, y = [], []
        for _, lab, pr in adj:
            ws = [c["score"] for c in pr["claims"] if c["why"] == why]
            if ws:
                s.append(max(ws))
                y.append(1 if lab == "real_bug" else 0)
        per_why[why] = {"n_pairs": len(s),
                        "auc": auc(s, y) if s else None}
    per_scene: dict[str, dict[str, int]] = {}
    for pid, lab, pr in adj:
        sc = pr["scene"]
        d = per_scene.setdefault(sc, {"n": 0, "pos": 0, "sym_flag": 0})
        d["n"] += 1
        d["pos"] += lab == "real_bug"
        d["sym_flag"] += pr["sym_count"] > 0
    return {
        "n_adjudicated": len(adj), "n_real_bug": sum(labels),
        "auc_max_score": round(auc(scores, labels), 4),
        "sym_op": {"tp": tp, "fp": fp, "fn": fn,
                   "precision": round(prec, 4), "recall": round(rec, 4),
                   "f1": round(f1, 4)},
        "per_why": per_why, "per_scene": per_scene}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mdeberta",
                    choices=["mdeberta", "erlangshen"])
    ap.add_argument("--template", default="closed", choices=["closed", "plain"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--both-models", action="store_true",
                    help="模板消融+双模型一次跑完(4配置)")
    args = ap.parse_args()

    gold = load_gold()
    configs = ([("mdeberta", "closed"), ("mdeberta", "plain"),
                ("erlangshen", "closed"), ("erlangshen", "plain")]
               if args.both_models
               else [(args.model, args.template)])

    run = open_run("nli_pair_experiment", {
        "configs": [list(c) for c in configs], "limit": args.limit})
    print(f"runs dir: {run.path}")
    print(f"gold pairs: {len(gold)} "
          f"(real_bug={sum(1 for v in gold.values() if v == 'real_bug')})")

    all_results: dict[str, Any] = {}
    for model, template in configs:
        nli = NliLocal(model)
        mode = nli.ensure()
        print(f"\n==== [{model}/{template}] device={mode} ====")
        if mode == "unavailable":
            print(f"  SKIP: {nli.last_error}")
            continue
        res = run_config(model, template, args.limit, nli)
        ev = evaluate(res, gold)
        all_results[f"{model}/{template}"] = {"eval": ev, **res}
        run.log(model=model, template=template, n_claims=res["n_claims"],
                eval=ev)
        print(f"  pairs={len(res['pairs'])} claims={res['n_claims']} "
              f"elapsed={res['elapsed_s']}s infer={res['stats']['infer_ms']}ms")
        if ev.get("n_adjudicated"):
            print(f"  AUC(max_score)={ev['auc_max_score']} "
                  f"on {ev['n_adjudicated']} adjudicated "
                  f"({ev['n_real_bug']} real_bug)")
            op = ev["sym_op"]
            print(f"  sym_contra工作点: P={op['precision']} R={op['recall']} "
                  f"F1={op['f1']} (tp={op['tp']} fp={op['fp']} fn={op['fn']})")
            for why, d in ev["per_why"].items():
                if d["auc"] is not None:
                    print(f"  per-why[{why}]: n={d['n_pairs']} auc={d['auc']}")
            for sc, d in sorted(ev["per_scene"].items()):
                print(f"  scene[{sc}]: n={d['n']} pos={d['pos']} "
                      f"sym_flag={d['sym_flag']}")

    run.save_result(all_results)
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
