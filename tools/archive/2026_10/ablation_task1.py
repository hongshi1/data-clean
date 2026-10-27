r"""Task 1 v4.1通道消融: 每个确定性通道的边际贡献.

配置:
  full      : numeric+quote+term+enum+nli (完整v4.1)
  no_numeric: 禁用numeric通道
  no_quote  : 禁用quote通道
  no_enum   : 禁用enum通道
  no_determ : 禁用全部确定性通道(=纯NLI, 即v3形态)

评测集: synth_s1全量5418 + image_pairs 2153 + clean130/md166金标
"""
from __future__ import annotations

import json
import sys
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


class AblatableChecker:
    """按禁用配置路由通道(复用ConsistencyChecker的通道实现)."""

    def __init__(self, disable: set[str]):
        from algorithms.consistency_check.consistency_checker import ConsistencyChecker
        self._c = ConsistencyChecker()
        self._disable = disable
        self._fns = {
            "numeric": self._c._check_numeric,
            "quote": self._c._check_quote,
            "term": self._c._check_term,
            "enum": self._c._check_enum,
        }
        from algorithms.consistency_check.consistency_checker import strip_negation
        self._strip = strip_negation

    def check(self, prem: str, hyp: str) -> str:
        from algorithms.consistency_check.consistency_checker import strip_negation
        p, h = strip_negation(prem), strip_negation(hyp)
        for name, fn in self._fns.items():
            if name in self._disable:
                continue
            r = fn(p, h)
            if r:
                return r.verdict
        r = self._c._check_nli(prem, hyp)
        return r.verdict


def main() -> None:
    # 评测集
    s1 = json.loads((BASE / "data/gjb_438c/synth_s1_pairs.json").read_text(encoding="utf-8"))["pairs"]
    img = json.loads((BASE / "data/gjb_438c/image_pairs.json").read_text(encoding="utf-8"))["pairs"]
    clean130 = json.loads((BASE / "data/gjb_438c/human_gold/gold_v2_clean_137.json").read_text(encoding="utf-8"))
    md_sc3 = json.loads((BASE / "data/gjb_438c/human_gold/md_test_sc3.json").read_text(encoding="utf-8"))
    md_047 = json.loads((BASE / "data/gjb_438c/human_gold/md_test_doc047.json").read_text(encoding="utf-8"))
    md166 = md_sc3 + [x for x in md_047 if x not in md_sc3]

    sets = {"synth_s1(5418)": s1, "image_pairs(2153)": img,
            "clean130": clean130, "md166": md166}

    configs = {
        "full(v4.1)": set(),
        "no_numeric": {"numeric"},
        "no_quote": {"quote"},
        "no_enum": {"enum"},
        "no_determ(=v3)": {"numeric", "quote", "term", "enum"},
    }

    results = {}
    print(f"{'配置':<16}", end="")
    for name in sets:
        print(f"{name:>18}", end="")
    print()
    for cfg_name, disable in configs.items():
        checker = AblatableChecker(disable)
        row = {}
        print(f"{cfg_name:<16}", end="")
        for set_name, pairs in sets.items():
            preds = [checker.check(p["premise"], p["hypothesis"]) for p in pairs]
            golds = [p["label"] for p in pairs]
            acc = sum(1 for a, b in zip(preds, golds) if a == b) / len(pairs)
            ba = bacc(preds, golds)
            # 单标签集报告acc, 混合集报告bAcc
            mixed = len(set(golds)) == 2
            key = round(ba, 3) if mixed else round(acc, 3)
            row[set_name] = {"bAcc": round(ba, 3), "acc": round(acc, 3), "mixed": mixed}
            print(f"{key:>18}", end="")
        results[cfg_name] = row
        print()

    # 保存
    sys.path.insert(0, str(BASE / "tools"))
    from run_utils import open_run
    run = open_run("task1_v4_1_ablation", {
        "配置": "full/no_numeric/no_quote/no_enum/no_determ(=纯NLI v3形态)",
        "指标": "混合标签集报bAcc, 单标签集报acc"})
    run.save_result(results)
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
