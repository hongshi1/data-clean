r"""Task 1 v4评测: 冻结金标(clean130/md166) + synth_s1失败族 + image_pairs.

v3基线(审计复现):
  clean130=0.700  md166=0.940
  synth_s1抽样300: acc=0.557 (PARAM-02=0.000, TERM-02=0.000, ENUM-02=0.171)
  image_pairs: acc=0.48-0.60, 一致对误报FP=84/200
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")


def bacc(preds: list[str], golds: list[str]) -> float:
    tp = sum(1 for p, g in zip(preds, golds) if p == g == "inconsistent")
    tn = sum(1 for p, g in zip(preds, golds) if p == g == "consistent")
    n_pos = sum(1 for g in golds if g == "inconsistent")
    n_neg = sum(1 for g in golds if g == "consistent")
    tpr = tp / n_pos if n_pos else 0.0
    tnr = tn / n_neg if n_neg else 0.0
    return (tpr + tnr) / 2


def evaluate(checker, name: str, pairs: list[dict], bucket_key: str | None = None) -> dict:
    preds, golds = [], []
    for p in pairs:
        r = checker.check(p["premise"], p["hypothesis"])
        preds.append(r.verdict)
        golds.append(p["label"])
    acc = bacc(preds, golds)
    plain = sum(1 for a, b in zip(preds, golds) if a == b) / len(pairs)

    out = {"name": name, "n": len(pairs), "bAcc": round(acc, 3), "acc": round(plain, 3)}
    if bucket_key:
        buckets = defaultdict(list)
        for p, pr, g in zip(pairs, preds, golds):
            buckets[str(p.get(bucket_key, "?"))].append((pr, g))
        bstats = {}
        for k, items in sorted(buckets.items()):
            bp = [x[0] for x in items]
            bg = [x[1] for x in items]
            bstats[k] = {"n": len(items), "bAcc": round(bacc(bp, bg), 3)}
        out["buckets"] = bstats
    return out


def main() -> None:
    from algorithms.consistency_check.consistency_checker import ConsistencyChecker

    checker = ConsistencyChecker()

    # 1. 冻结金标
    clean130 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    r1 = evaluate(checker, "clean130", clean130)
    print(f"clean130: bAcc={r1['bAcc']} (v3基线=0.700)")

    md_047 = json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
    md_sc3 = json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8"))
    md166 = md_047 + md_sc3  # 官方协议: 直接拼接(n=166, 与run.py cmd_eval一致)
    r2 = evaluate(checker, "md166", md166)
    print(f"md166: bAcc={r2['bAcc']} (v3基线=0.940)")

    # 2. synth_s1: v3失败族 + 抽样
    s1 = json.loads((BASE / "data/gjb_438c/synth_s1_pairs.json").read_text(encoding="utf-8"))["pairs"]
    # 失败族全量
    failed_types = ["PARAM-02", "PARAM-03", "TERM-02", "ENUM-02"]
    for ft in failed_types:
        sub = [p for p in s1 if p.get("type") == ft]
        if sub:
            # 每族最多200
            sub = sub[:200]
            rf = evaluate(checker, f"s1_{ft}", sub)
            print(f"synth_s1[{ft}]: bAcc={rf['bAcc']} n={rf['n']}")

    # 全量分type评测
    r3 = evaluate(checker, "synth_s1_all", s1[:1500], bucket_key="type")
    print(f"\nsynth_s1抽样1500: bAcc={r3['bAcc']}")
    for t, st in sorted(r3.get("buckets", {}).items()):
        print(f"  {t}: n={st['n']} bAcc={st['bAcc']}")

    # 3. image_pairs v2
    ip = json.loads((BASE / "data/gjb_438c/image_pairs.json").read_text(encoding="utf-8"))["pairs"]
    r4 = evaluate(checker, "image_pairs", ip, bucket_key="method")
    print(f"\nimage_pairs v2: bAcc={r4['bAcc']} n={r4['n']}")
    for m, st in sorted(r4.get("buckets", {}).items()):
        print(f"  {m}: n={st['n']} bAcc={st['bAcc']}")

    # 4. 通道分布(路由分析)
    channels = Counter()
    for p in (clean130 + md166):
        r = checker.check(p["premise"], p["hypothesis"])
        channels[r.channel] += 1
    print(f"\n金标路由分布: {dict(channels)} (v3: 全部走nli)")

    # 5. 保存run
    sys.path.insert(0, str(BASE / "tools"))
    from run_utils import open_run
    run = open_run("task1_v4_eval", {
        "v4": "5通道κD条件化(numeric/term/enum/verify/nli)",
        "基线": "v3: clean130=0.700, md166=0.940, s1 PARAM-02/TERM-02=0.000"})
    run.save_result({
        "clean130": r1, "md166": r2, "synth_s1": r3, "image_pairs": r4,
        "gold_routing": dict(channels)})
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
