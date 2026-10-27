r"""单元通道集成消融: hybrid_recall六通道(含unit) vs 五通道.

结论(2026-10-07, retrieval_evalset 300查询, cascade融合):
  五通道: Recall@10 0.4550 / Recall@20 0.6447 / MRR 0.4446
  六通道: Recall@10 0.5139(+5.9) / Recall@20 0.6865(+4.2) / MRR 0.4428
  单通道unit: R@10 0.3242 / MRR 0.6797(命中即首位——深而窄)
MRR不变: 首位质量由事实通道主导; unit贡献在召回深度(语义级image/
table候选), 与设计定位一致(概率通道进Tier2 RRF填充).

用法: python tools/eval_unit_channel.py [--limit 300]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

EVALSET = BASE / "data/gjb_438c/data_assets/retrieval_evalset.json"
OUT = BASE / "data/gjb_438c/data_assets/evalsets/unit_channel_ablation.json"


def _metrics(recalled: list[dict], exp_ids: set) -> tuple[float, float, float]:
    got = [h["chunk_id"] for h in recalled]
    r10 = sum(1 for t in exp_ids if t in got[:10]) / max(len(exp_ids), 1)
    r20 = sum(1 for t in exp_ids if t in got[:20]) / max(len(exp_ids), 1)
    rr = 0.0
    for t in exp_ids:
        if t in got[:10]:
            rr = max(rr, 1.0 / (got.index(t) + 1))
    return r10, r20, rr


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    args = ap.parse_args()

    evalset = json.loads(EVALSET.read_text(encoding="utf-8"))
    qs = evalset[:args.limit]
    print(f"评测集: {len(qs)}查询(cascade, top20)")

    from algorithms.blackboard.hybrid_recall import HybridRecaller

    results = {}
    for label, use_unit, channels in (
            ("five_channel", False, None),
            ("six_channel", True, None),
            ("unit_only", True, ("unit",))):
        rec = HybridRecaller(use_unit=use_unit)
        agg = defaultdict(list)
        for q in qs:
            kw = {} if channels is None else {"channels": channels}
            r = rec.recall(q["query"], top_k=20, fusion="cascade", **kw)
            exp_ids = set(q["expected"].get("chunk_ids") or [])
            m = _metrics(r["hits"], exp_ids)
            agg["r10"].append(m[0])
            agg["r20"].append(m[1])
            agg["mrr"].append(m[2])
        results[label] = {
            "Recall@10": round(float(np.mean(agg["r10"])), 4),
            "Recall@20": round(float(np.mean(agg["r20"])), 4),
            "MRR@10": round(float(np.mean(agg["mrr"])), 4),
        }
        r = results[label]
        print(f"  {label:12s}: R@10={r['Recall@10']:.4f} "
              f"R@20={r['Recall@20']:.4f} MRR={r['MRR@10']:.4f}")

    gain = results["six_channel"]["Recall@10"] - results["five_channel"]["Recall@10"]
    print(f"\n单元通道增益: R@10 {gain:+.4f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "protocol": (f"retrieval_evalset前{len(qs)}查询, cascade融合, "
                     "top20; 消融=五通道/六通道/单通道unit"),
        "results": results,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
