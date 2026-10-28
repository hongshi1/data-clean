#!/usr/bin/env python3
"""有无减法模块的NLI裁决对比实验(A/B).

对应文档: 70号. 回答: 减法模块让下游NLI三态裁决提点还是掉点?

设计:
  B0(无模块): NLI直接吃原始证据块文本(含表格HTML整块) — 现状基线,
              即SumMaC诊断的"文档级直入"失败模式
  B3(有模块): evidence_subtractor三级过滤+粒度归一 → NLI只吃句/行级语句

  每实例: premise=证据(块/语句), hypothesis=answer
         实例verdict = refute若max p_contra > τ, 否则neutral/support
  金标: violation_evalset_v1的17实例(全部期望refute, 带gold_evidence_refs)
  指标: refute查全率 | gold证据保留率 | 删除分布 | p_contra分布
用法: python tools/eval_subtraction_nli.py [--tau 0.5]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

# 顺序约束: torch先于numpy链(Windows OpenMP, 见68号)
import torch  # noqa: E402,F401

from algorithms.consistency.evidence_subtractor import subtract  # noqa: E402

VIO_PATH = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
OUT_PATH = BASE / "data/gjb_438c/localization_gold/subtraction_ab_v1.json"


def load_instances() -> list[dict]:
    rows = [json.loads(line) for line in VIO_PATH.open(encoding="utf-8")]
    return rows


def nli_judge(nli, premises: list[str], answer: str) -> tuple[float, str]:
    """NLI: premise=证据语句, hypothesis=answer → (max p_contra, 极性)."""
    if not premises:
        return 0.0, "no_evidence"
    probs = nli.predict([(p, answer) for p in premises])
    max_contra = max(p.get("p_contra", 0.0) for p in probs)
    max_entail = max(p.get("p_entail", 0.0) for p in probs)
    polarity = "contra" if max_contra >= max_entail else "entail"
    return max_contra, polarity


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tau", type=float, default=0.5)
    args = ap.parse_args()

    from algorithms.consistency.nli_local import NliLocal
    nli = NliLocal("mdeberta")
    mode = nli.ensure()
    if mode not in ("cuda", "gpu", "cpu"):
        print(f"NLI不可用: {nli.last_error}")
        return 1
    print(f"NLI: {mode}")

    instances = load_instances()
    print(f"违例实例: {len(instances)}条(全部期望refute), τ={args.tau}")

    report: list[dict] = []
    n_refute_b0 = n_refute_b3 = 0
    n_gold_keep = n_gold_all = 0
    reason_stat: dict[str, int] = {}
    t_b0 = t_b3 = 0.0

    for ins in instances:
        ev = ins["evidence"]
        answer = ins["answer"]
        question = ins["question"]
        gold_ids = set(ins["gold_evidence_refs"])

        # ── B0: 无模块, 原始块直入NLI ──
        t0 = time.perf_counter()
        c0, pol0 = nli_judge(nli, [str(e.get("text", "")) for e in ev], answer)
        t_b0 += time.perf_counter() - t0
        v0 = "refute" if c0 > args.tau else ("neutral")

        # ── B3: 减法模块 ──
        t0 = time.perf_counter()
        pack = subtract(question, answer, ev)
        premises = [s for k in pack["kept"] for s in k["statements"]]
        c3, pol3 = nli_judge(nli, premises, answer)
        t_b3 += time.perf_counter() - t0
        v3 = "refute" if c3 > args.tau else ("neutral")

        kept_ids = {k["evidence_id"] for k in pack["kept"]}
        gold_kept = gold_ids & kept_ids
        n_refute_b0 += v0 == "refute"
        n_refute_b3 += v3 == "refute"
        n_gold_keep += len(gold_kept)
        n_gold_all += len(gold_ids)
        for r in pack["removed"]:
            reason_stat[r["reason_code"]] = reason_stat.get(
                r["reason_code"], 0) + 1

        report.append({
            "instance_id": ins["instance_id"], "item_id": ins["item_id"],
            "expected": ins["expected_verdict"],
            "B0": {"verdict": v0, "max_p_contra": round(c0, 4),
                   "polarity": pol0},
            "B3": {"verdict": v3, "max_p_contra": round(c3, 4),
                   "polarity": pol3},
            "gold_kept": f"{len(gold_kept)}/{len(gold_ids)}",
            "removed": [r["reason_code"] for r in pack["removed"]],
            "n_statements": pack["stats"]["n_statements"],
        })

    n = len(instances)
    print(f"\n{'实例':<16} {'检测项':<9} {'B0':>8} {'B3':>8} "
          f"{'c0':>6} {'c3':>6} {'gold':>7} {'删除原因'}")
    print("-" * 78)
    for r in report:
        print(f"{r['instance_id']:<16} {r['item_id']:<9} "
              f"{r['B0']['verdict']:>8} {r['B3']['verdict']:>8} "
              f"{r['B0']['max_p_contra']:>6.3f} {r['B3']['max_p_contra']:>6.3f} "
              f"{r['gold_kept']:>7} {','.join(r['removed']) or '-'}")

    print(f"\n=== 汇总(τ={args.tau}) ===")
    print(f"refute查全: B0={n_refute_b0}/{n}  B3={n_refute_b3}/{n}  "
          f"Δ={n_refute_b3 - n_refute_b0:+d}")
    print(f"gold证据保留: {n_gold_keep}/{n_gold_all} "
          f"({100 * n_gold_keep / max(n_gold_all, 1):.1f}%)")
    print(f"删除分布: {reason_stat}")
    print(f"NLI总耗时: B0={t_b0:.1f}s  B3(含减法)={t_b3:.1f}s")

    OUT_PATH.write_text(json.dumps({
        "tau": args.tau, "n_instances": n,
        "refute_recall": {"B0": n_refute_b0, "B3": n_refute_b3},
        "gold_retention": f"{n_gold_keep}/{n_gold_all}",
        "removal_by_reason": reason_stat,
        "per_instance": report,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"结果已写入: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
