r"""MMQA Suite-S评测: 构造真值(40项注入)上的NLI表现·分通道报告.

核心问题: 通道分流(NLI能力边界前置)是否被构造性真值证实?
  预期: nli-strong通道(参数/枚举/计数) 矛盾检出高;
        lexical/syntax通道 矛同检出低(NLI判不了 → 归对应通道职责).
每条mutation的claim对 → mDeBERTa双向 → sym_contra与expected比对.

用法: python tools/mmqa_eval.py [--model mdeberta] [--split test]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.consistency.nli_local import NliLocal  # noqa: E402
from run_utils import open_run  # noqa: E402

MMQA = BASE / "data/gjb_438c/mmqa"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mdeberta",
                    choices=["mdeberta", "erlangshen"])
    ap.add_argument("--split", default="all",
                    choices=["all", "train", "dev", "test"])
    ap.add_argument("--channel", default="all")
    args = ap.parse_args()

    mutations = [json.loads(line) for line in
                 (MMQA / "mutations.jsonl").read_text(
                     encoding="utf-8").strip().splitlines()]
    sel = [m for m in mutations if m.get("n_claims", 0) > 0
           and (args.split == "all" or m["split"] == args.split)
           and (args.channel == "all" or m["channel"] == args.channel)]
    print(f"评测: {len(sel)}条mutation({args.split}/{args.channel})")

    # claim对展开
    pairs: list[tuple[str, str]] = []
    owner: list[int] = []
    for i, m in enumerate(sel):
        for c in m.get("claims", []):
            pairs.append((c["premise"], c["hypothesis"]))
            owner.append(i)

    nli = NliLocal(args.model)
    mode = nli.ensure()
    if mode == "unavailable":
        print(f"SKIP: {nli.last_error}")
        return
    verdicts = nli.predict_bidirectional(pairs)
    print(f"NLI推理: {mode}, {len(pairs)}条claim, "
          f"{nli.stats['infer_ms']}ms\n")

    # 回写mutation级信号
    for i, m in enumerate(sel):
        m["nli"] = {"sym": False, "best_score": 0.0}
    for v, i in zip(verdicts, owner):
        m = sel[i]
        m["nli"]["sym"] = m["nli"]["sym"] or v["sym_contra"]
        m["nli"]["best_score"] = max(m["nli"]["best_score"],
                                     v["contra_score"])

    # 分通道成绩(expected全为inconsistent → 检出率=recall)
    by_channel: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"n": 0, "sym": 0, "score_sum": 0.0})
    by_item: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "sym": 0})
    for m in sel:
        ch = m["channel"]
        d = by_channel[ch]
        d["n"] += 1
        d["sym"] += m["nli"]["sym"]
        d["score_sum"] += m["nli"]["best_score"]
        di = by_item[m["check_item"]]
        di["n"] += 1
        di["sym"] += m["nli"]["sym"]

    print("══ 分通道(构造真值, expected=inconsistent, 检出率=recall) ══")
    print(f"{'通道':<12} {'n':>5} {'sym检出':>8} {'recall':>8} {'avg分':>7}")
    for ch, d in sorted(by_channel.items()):
        print(f"{ch:<12} {d['n']:>5} {d['sym']:>8} "
              f"{d['sym']/d['n']:>8.1%} {d['score_sum']/d['n']:>7.3f}")

    print("\n══ 分check_item ══")
    for item, d in sorted(by_item.items()):
        print(f"  {item}: {d['sym']}/{d['n']} ({d['sym']/d['n']:.0%})")

    run = open_run("mmqa_eval", {"model": args.model, "split": args.split,
                                  "channel": args.channel})
    run.save_result({
        "by_channel": {k: dict(v) for k, v in by_channel.items()},
        "by_item": {k: dict(v) for k, v in by_item.items()},
        "n_mutations": len(sel), "n_claims": len(pairs),
        "nli_stats": dict(nli.stats),
        "per_mutation": [{"mutation_id": m["mutation_id"],
                          "channel": m["channel"], "sym": m["nli"]["sym"],
                          "score": round(m["nli"]["best_score"], 4)}
                         for m in sel]})
    print(f"\nresult → {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
