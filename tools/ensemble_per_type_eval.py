r"""集成方法逐类型评测 — ensemble_v16(b_wavg_bacc) vs 单模型 在39种不一致类型上.

数据构建(复用tools/per_type_eval.py逻辑):
  真实金标296(clean130+md166, 唯一有consistent样本的真实类型=结构类8种)
  + canonical test srs_mutation + expanded_mutations test(变异, inconsistent)
  + 对称构造一致对(tools/symmetric_construction.py make_consistent, seed=42)
  → 39种类型, 共3062条(真实296 + 变异1383 + 对称1383)

方法:
  集成 = ensemble_v16_results.json保存的b_wavg_bacc权重(概率加权, 阈值0.5)
  单模型 = v12 / v13 (任务指定对比) + v15 / SVM (成员参考)
  模型路径/max_length/概率定义 = tools/ensemble_v16.py已保存配置
  SVM = ensemble_v16.train_svm()重训(去污染canonical train: 排除doc02锚点+train变异)

注意: v16权重在clean130+md166(本评测真实金标子集)上事后拟合 — 无独立验证集,
  逐类型解读需谨慎(选择偏差沿v16原始标注)。

输出: data/gjb_438c/runs/ensemble_per_type.json (+ runs协议归档)
用法: python tools/ensemble_per_type_eval.py
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))

HG = BASE / "data/gjb_438c/human_gold"
PD = BASE / "data/gjb_438c/pair_dataset_canonical"
V16_RESULTS = BASE / "data/gjb_438c/runs/ensemble_v16_results.json"
OUT_FIXED = BASE / "data/gjb_438c/runs/ensemble_per_type.json"

SINGLE_REPORT = ("v12", "v13")          # 任务指定的对比单模型
MEMBERS = ("v12", "v15", "v13", "svm")  # 全体成员(参考列)


def norm_label(x: dict[str, Any]) -> str:
    lab = x["label"]
    return lab if isinstance(lab, str) else ("inconsistent" if lab == 1 else "consistent")


def build_eval_data() -> tuple[list[dict[str, str]], dict[str, int]]:
    """per_type_eval.py的数据构建逻辑(顺序/rng严格复刻, 保证对称对可复现)."""
    import random

    from tools.symmetric_construction import make_consistent

    clean = json.loads((HG / "gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md = (json.loads((HG / "md_test_doc047.json").read_text(encoding="utf-8"))
          + json.loads((HG / "md_test_sc3.json").read_text(encoding="utf-8")))
    test = [json.loads(line) for line in open(PD / "test.jsonl", encoding="utf-8")]
    srs_mut = [x for x in test if x["source"] == "srs_mutation"]
    exp = [json.loads(line) for line in open(PD / "expanded_mutations.jsonl", encoding="utf-8")]
    exp_te = [x for x in exp
              if x["split"] == "test" and x["pair"]["premise"] != x["pair"]["hypothesis"]]

    rng = random.Random(42)
    symmetric: list[dict[str, str]] = []
    for x in srs_mut + exp_te:
        hc = make_consistent(x["pair"]["premise"], x["pair"]["hypothesis"], rng)
        if hc != x["pair"]["premise"] and len(hc) >= 8:
            symmetric.append({"premise": x["pair"]["premise"], "hypothesis": hc,
                              "label": "consistent", "type": x["angle"]["type"],
                              "origin": "symmetric"})

    combined: list[dict[str, str]] = []
    for x in clean + md:
        combined.append({"premise": x["premise"], "hypothesis": x["hypothesis"],
                         "label": norm_label(x), "type": str(x.get("type", x.get("dtype", "?"))),
                         "origin": "real"})
    for x in srs_mut + exp_te:
        combined.append({"premise": x["pair"]["premise"], "hypothesis": x["pair"]["hypothesis"],
                         "label": "inconsistent", "type": str(x["angle"]["type"]),
                         "origin": "mutation"})
    combined.extend(symmetric)
    counts = {"real": sum(1 for x in combined if x["origin"] == "real"),
              "mutation": sum(1 for x in combined if x["origin"] == "mutation"),
              "symmetric": len(symmetric)}
    return combined, counts


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    from ensemble_v16 import (MODEL_DIRS, hard_label, metrics, nli_probs, svm_probs,
                              train_svm, weighted_p)

    t0 = time.time()
    bar = "=" * 78
    print(bar)
    print("集成(b_wavg_bacc) vs 单模型 — 逐不一致类型评测 (39类型, 真实+变异+对称)")
    print(bar)

    # ── [1/4] v16保存的集成配置 ──
    v16 = json.loads(V16_RESULTS.read_text(encoding="utf-8"))
    strategy = v16["best"]["strategy"]
    if strategy != "b_wavg_bacc":
        print(f"⚠ v16最优策略={strategy}, 任务指定b_wavg_bacc — 采用b_wavg_bacc")
    w = {m: float(v16["weights"]["b_wavg_bacc"][m]) for m in MEMBERS}
    print("[1/4] 集成配置(v16保存): b_wavg_bacc 权重 "
          + " ".join(f"{m}={w[m]:.4f}" for m in MEMBERS))

    # ── [2/4] 评测数据 ──
    combined, counts = build_eval_data()
    by_type: dict[str, list[dict[str, str]]] = defaultdict(list)
    for x in combined:
        by_type[x["type"]].append(x)
    print(f"[2/4] 评测数据: 真实{counts['real']} + 变异{counts['mutation']}"
          f" + 对称{counts['symmetric']} = {len(combined)}条, {len(by_type)}种类型")

    # ── [3/4] 模型概率(路径/max_length沿用v16配置; SVM重训) ──
    probs: dict[str, list[float]] = {}
    for tag, (rel, maxlen) in MODEL_DIRS.items():
        probs[tag] = nli_probs(rel, maxlen, combined)
        print(f"[3/4] {tag}: {rel} (max_len={maxlen}) ✓ {time.time() - t0:.0f}s")
    vec, svm, n_svm = train_svm()
    probs["svm"] = svm_probs(vec, svm, combined)
    print(f"[3/4] svm: 去污染{n_svm}条重训(锚点+去污染配方) ✓ {time.time() - t0:.0f}s")

    rows = [{"type": x["type"], "label": x["label"], "origin": x["origin"],
             "p": {m: probs[m][i] for m in MEMBERS}} for i, x in enumerate(combined)]
    ens_p = [weighted_p(r["p"], w) for r in rows]
    preds: dict[str, list[str]] = {m: [hard_label(r["p"][m]) for r in rows] for m in MEMBERS}
    preds["ens"] = [hard_label(p) for p in ens_p]

    # ── [4/4] 逐类型对比 ──
    ys_all = [r["label"] for r in rows]
    pooled = {"ens": metrics(ys_all, preds["ens"])}
    pooled.update({m: metrics(ys_all, preds[m]) for m in MEMBERS})

    per_type: dict[str, Any] = {}
    ens_cell: dict[str, float] = {}
    v12_cell: dict[str, float] = {}
    v13_cell: dict[str, float] = {}
    for typ in sorted(by_type):
        grp = [r for r in rows if r["type"] == typ]
        ys = [r["label"] for r in grp]
        idx = [i for i, r in enumerate(rows) if r["type"] == typ]
        entry: dict[str, Any] = {"n": len(grp), "n_pos": ys.count("inconsistent"),
                                 "n_neg": ys.count("consistent"),
                                 "ens": metrics(ys, [preds["ens"][i] for i in idx])}
        for m in MEMBERS:
            entry[m] = metrics(ys, [preds[m][i] for i in idx])
        best_single = max(SINGLE_REPORT, key=lambda m: entry[m]["bAcc"])
        entry["best_single"] = {"model": best_single, "bAcc": entry[best_single]["bAcc"]}
        entry["delta_vs_best_single"] = round(entry["ens"]["bAcc"]
                                              - entry[best_single]["bAcc"], 4)
        per_type[typ] = entry
        ens_cell[typ] = entry["ens"]["bAcc"]
        v12_cell[typ] = entry["v12"]["bAcc"]
        v13_cell[typ] = entry["v13"]["bAcc"]

    # ── 对比表 ──
    hdr = (f"  {'类型':<20} {'n(pos+neg)':>11} | {'ens':>6} {'v12':>6} {'v13':>6}"
           f" {'v15':>6} {'svm':>6} | {'best_single':>11} {'Δ':>7}")
    print(f"\n[4/4] 逐类型bAcc (n={len(rows)}, 39类型, 阈值0.5):")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for typ in sorted(per_type, key=lambda t: -per_type[t]["n"]):
        e = per_type[typ]
        print(f"  {typ:<20} {e['n']:>5}({e['n_pos']}+{e['n_neg']}) |"
              f" {e['ens']['bAcc']:>6.3f} {e['v12']['bAcc']:>6.3f} {e['v13']['bAcc']:>6.3f}"
              f" {e['v15']['bAcc']:>6.3f} {e['svm']['bAcc']:>6.3f} |"
              f" {e['best_single']['model'] + '(' + format(e['best_single']['bAcc'], '.3f') + ')':>11}"
              f" {e['delta_vs_best_single']:>+7.3f}")

    print(f"\n  合并全部{len(rows)}条: ens={pooled['ens']['bAcc']:.4f}"
          f" v12={pooled['v12']['bAcc']:.4f} v13={pooled['v13']['bAcc']:.4f}"
          f" v15={pooled['v15']['bAcc']:.4f} svm={pooled['svm']['bAcc']:.4f}")

    macro = {k: round(sum(v.values()) / len(v), 4) for k, v in
             (("ens", ens_cell), ("v12", v12_cell), ("v13", v13_cell))}
    wins = {m: {"win": sum(1 for t in ens_cell if ens_cell[t] > {"v12": v12_cell, "v13": v13_cell}[m][t]),
                "tie": sum(1 for t in ens_cell if ens_cell[t] == {"v12": v12_cell, "v13": v13_cell}[m][t]),
                "loss": sum(1 for t in ens_cell if ens_cell[t] < {"v12": v12_cell, "v13": v13_cell}[m][t])}
            for m in SINGLE_REPORT}
    bs = {t: max(v12_cell[t], v13_cell[t]) for t in ens_cell}
    wins["best_single(v12,v13)"] = {
        "win": sum(1 for t in ens_cell if ens_cell[t] > bs[t]),
        "tie": sum(1 for t in ens_cell if ens_cell[t] == bs[t]),
        "loss": sum(1 for t in ens_cell if ens_cell[t] < bs[t])}
    print(f"\n  宏平均(39类型等权): ens={macro['ens']:.4f} v12={macro['v12']:.4f}"
          f" v13={macro['v13']:.4f}")
    for k, v in wins.items():
        print(f"  ens vs {k:<20} 胜{v['win']}/平{v['tie']}/负{v['loss']} (共39类型)")

    ens_best_types = sorted(ens_cell, key=lambda t: -ens_cell[t])[:5]
    ens_worst_types = sorted(ens_cell, key=lambda t: ens_cell[t])[:5]
    print("\n  ens最强5类型: " + ", ".join(f"{t}={ens_cell[t]:.3f}" for t in ens_best_types))
    print("  ens最弱5类型: " + ", ".join(f"{t}={ens_cell[t]:.3f}" for t in ens_worst_types))
    small = [t for t in per_type if per_type[t]["n"] < 6]
    print(f"\n  ⚠ 小样本类型(n<6)共{len(small)}种: {', '.join(small)} — bAcc粒度粗, 解读谨慎")

    # ── 落盘 ──
    result: dict[str, Any] = {
        "tag": "ensemble_per_type",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ensemble_config": {
            "source": "data/gjb_438c/runs/ensemble_v16_results.json",
            "strategy": "b_wavg_bacc",
            "weights": {m: round(w[m], 4) for m in MEMBERS},
            "weights_basis": v16["weights"]["basis"],
            "models": {m: v16["models"][m]["path"] if "path" in v16["models"][m]
                       else "retrain" for m in MEMBERS},
            "max_length": {m: v16["models"][m].get("max_length") for m in MEMBERS},
            "svm_recipe": ("ensemble_v16.train_svm()重训: canonical train(srs_anchor排除doc02)"
                           f"+train变异 = 去污染{n_svm}条, TF-IDF(20k,1-2)+LinearSVC(balanced)"),
            "threshold": 0.5,
        },
        "data": {"construction": ("per_type_eval.py逻辑: gold_v2_clean_137 + md_test_doc047"
                                  "+md_test_sc3(真实金标) + test.jsonl srs_mutation"
                                  "+expanded_mutations test(变异) + make_consistent(seed=42)"
                                  "(对称一致对)"),
                 "counts": counts, "n_total": len(rows), "n_types": len(per_type),
                 "note": "真实金标仅结构类8种有两类样本; 其余类型靠变异(inconsistent)"
                         "+对称构造(consistent)补齐"},
        "pooled": pooled,
        "macro_bAcc": macro,
        "wins_ens_vs": wins,
        "per_type": per_type,
        "notes": [
            "v16权重在clean130+md166(本评测真实金标子集)上事后拟合, 无独立验证集 — 选择偏差沿v16标注",
            "小样本类型(n<6)12种: bAcc步长0.25~0.5, 单类型结论不稳, 以宏平均+大样本类型为主",
            "对称一致对由差异回退+表面变换生成: 内容一致但表面不同, 非人工金标",
            "单模型列v15/svm为集成成员参考; 任务指定对比 = ens vs v12 vs v13",
        ],
    }
    OUT_FIXED.parent.mkdir(parents=True, exist_ok=True)
    OUT_FIXED.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  输出 → {OUT_FIXED}")

    from run_utils import open_run
    run = open_run("ensemble_per_type", {
        "strategy": "b_wavg_bacc", "weights": {m: round(w[m], 4) for m in MEMBERS},
        "models": {m: MODEL_DIRS.get(m, ("retrain-svm", 0))[0] for m in MEMBERS},
        "data": ["real296", "srs_mutation", "expanded_test", "symmetric"],
        "compare": ["ens", "v12", "v13"],
    })
    run.save_result(result)
    run.log(stage="done", n=len(rows), n_types=len(per_type),
            macro_ens=macro["ens"], macro_v12=macro["v12"], macro_v13=macro["v13"],
            pooled_ens=pooled["ens"]["bAcc"], seconds=round(time.time() - t0, 1))
    print(f"  runs归档 → {run.path}")
    print(f"  耗时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
