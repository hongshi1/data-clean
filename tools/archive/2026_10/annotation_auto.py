r"""机器标注86条裁决任务(自动完成P3·免人工): 多信号融合+诚实分层.

设计(基于已实证的通道能力边界):
  - compiler刀(NLI可判): sym_contra=False → 内容可能一致 → compiler_bug候选
    (L1构造真值背书: NLI对"图里其实有"判非矛盾)
  - real vs benign刀(NLI判不了, 需惯例知识): 机器诚实留unsure
    — 除非LOGIC结构信号可判(ORDER_CONFLICT的边方向是确定性可比的)

信号融合(全部确定性/已校准):
  NLI sym_contra + match_score + dtype语义 → 带置信的标注

产出: human_gold/machine_gold_86.json + 与664银标对比报告
用法: python tools/annotation_auto.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

TASKS86 = BASE / "data/gjb_438c/anchor_sc2/adjudication/adjudication_tasks.json"
SILVER = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
OUT_DIR = BASE / "data/gjb_438c/human_gold"


def auto_annotate() -> dict:
    from algorithms.consistency_check.nli_local import NliLocal
    from algorithms.consistency_check.nli_discrepancy_review import (
        PairContext,
        build_claims_for_discrepancy,
    )
    tasks = json.loads(TASKS86.read_text(encoding="utf-8"))
    ctx = PairContext(BASE / "data/gjb_438c/pair_dataset")

    pairs, keys = [], []
    for t in tasks:
        disc = {"dtype": t.get("dtype", ""), "evidence": t.get("evidence", ""),
                "table_side": t.get("table_side") or {}}
        _, claim = build_claims_for_discrepancy(
            BASE / "data/gjb_438c/pair_dataset", t["pair_key"], disc, ctx)
        if claim is not None:
            pairs.append((claim.premise, claim.hypothesis))
            keys.append(t["task_id"])

    nli = NliLocal("mdeberta")
    if nli.ensure() == "unavailable":
        print(f"NLI不可用: {nli.last_error}")
        return {}
    verdicts = nli.predict_bidirectional(pairs)
    nli_map = {k: v for k, v in zip(keys, verdicts)}

    out: dict[str, dict] = {}
    for t in tasks:
        tid = t["task_id"]
        dtype = t.get("dtype", "")
        v = nli_map.get(tid)
        sym = v["sym_contra"] if v else None
        score = round(v["contra_score"], 3) if v else None
        ms = t.get("match_score", 0) or 0

        # ── 融合规则(确定性, 按能力边界) ──
        if dtype in ("ORDER_CONFLICT", "UC_NAME_MISMATCH"):
            label, why = "unsure", "NLI不适用该类型(结构/名称域)"
            conf = "low"
        elif sym is None:
            label, why = "unsure", "声明不可构造"
            conf = "low"
        elif not sym and score is not None and score < 0.3:
            # NLI双向非矛盾+低矛盾分 → 内容大概率一致 → 引擎误报
            label, why = "compiler_bug", f"NLI非矛盾(分{score})→图里可能有"
            conf = "medium"
        elif sym and score is not None and score >= 0.5:
            # 双向强矛盾 → 内容真不一致(real/benign机器判不了)
            label, why = "unsure", f"NLI强矛盾(分{score})→真差异, 但real/benign需惯例知识"
            conf = "low"
        else:
            label, why = "unsure", f"中间区(分{score})→送人工"
            conf = "low"
        out[tid] = {"label": label, "pair": t["pair_key"], "dtype": dtype,
                    "nli_sym": sym, "nli_score": score, "match_score": ms,
                    "confidence": conf, "why": why}
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    gold = auto_annotate()
    if not gold:
        return
    from collections import Counter
    dist = Counter(g["label"] for g in gold.values())
    print(f"机器标注: {len(gold)}条 | 分布: {dict(dist)}")
    n_compiler = dist.get("compiler_bug", 0)
    print(f"  自动标注: {n_compiler}条compiler_bug(NLI能力域内)")
    print(f"  诚实unsure: {sum(v for k, v in dist.items() if k == 'unsure')}"
          f"条(real/benign需人工或LLM裁决)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "machine_gold_86.json"
    out.write_text(json.dumps({"n": len(gold), "dist": dict(dist),
                               "labels": gold,
                               "protocol": "NLI双向sym(构造真值背书的compiler刀)"
                                           "+诚实分层(unsure留给人工/LLM)",
                               "date": "2026-09-16"},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"机器金标 → {out}")

    # 与664银标对比
    silver = json.loads(SILVER.read_text(encoding="utf-8"))["final_labels"]
    overlap = [(k, gold[k]["label"], silver[k]["label"])
               for k in gold if k in silver]
    if overlap:
        agree = sum(1 for _, g, s in overlap if g == s)
        # compiler刀的一致性(机器判compiler vs 银标compiler)
        comp_agree = sum(1 for _, g, s in overlap
                         if g == "compiler_bug" and s == "compiler_bug")
        comp_machine = sum(1 for _, g, _ in overlap if g == "compiler_bug")
        print(f"\n与664银标对比: 重叠{len(overlap)}条")
        print(f"  整体一致: {agree}/{len(overlap)} ({agree/len(overlap):.0%})")
        if comp_machine:
            print(f"  compiler刀: 机器判compiler {comp_machine}条中"
                  f"{comp_agree}条与银标一致"
                  f"({comp_agree/comp_machine:.0%})")
        for k, g, s in overlap:
            if g != s:
                print(f"  分歧: {k} 机器={g} 银标={s}")


if __name__ == "__main__":
    main()
