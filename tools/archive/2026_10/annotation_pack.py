r"""人工裁决回填工具(P3·金标升级): 机器意见辅助标注包生成 + 回填解析.

资产(被遗忘的待办, 资产地图§5):
  1. anchor_sc2/adjudication/adjudication_tasks.json — 86条人工裁决任务
     (label全空; M15分层抽样: EXC/STEP/ACTOR/DIAGRAM_EXTRA各20+ORDER/UC各3)
  2. srs_qa_v3/human_annotation/ — 100条双标注者任务(answer_key已备)

设计: 机器意见辅助 — 每条86任务预跑NLI复核信号(sym_contra), 人工
      只需在参考意见下做三分类(real_bug/benign_variation/compiler_bug),
      大幅降低认知负担; CSV标注包(Excel可填) + 回填解析器.

用法:
  python tools/annotation_pack.py pack    # 生成标注包(带机器意见)
  python tools/annotation_pack.py fill --file 填好的.csv  # 回填→金标+对比报告
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

TASKS86 = BASE / "data/gjb_438c/anchor_sc2/adjudication/adjudication_tasks.json"
OUT_DIR = BASE / "data/gjb_438c/human_gold"
LABELS = ["real_bug", "benign_variation", "compiler_bug", "unsure"]


def machine_opinion(nli_model) -> dict[str, dict]:
    """86任务 → NLI复核信号(分歧驱动声明+双向推理).

    信号语义: sym_contra=True → NLI认为内容真不一致(倾向非compiler);
    False → 内容可能一致(倾向compiler_bug/词法误报).
    """
    from algorithms.consistency_check.nli_discrepancy_review import (
        PairContext,
        build_claims_for_discrepancy,
    )
    ctx = PairContext(BASE / "data/gjb_438c/pair_dataset")
    tasks = json.loads(TASKS86.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    pairs: list[tuple[str, str]] = []
    keys: list[str] = []
    for t in tasks:
        disc = {"dtype": t.get("dtype", ""), "evidence": t.get("evidence", ""),
                "table_side": t.get("table_side") or {}}
        _, claim = build_claims_for_discrepancy(
            BASE / "data/gjb_438c/pair_dataset", t["pair_key"], disc, ctx)
        if claim is None:
            out[t["task_id"]] = {"sym": None, "score": None, "nli": "n/a"}
            continue
        pairs.append((claim.premise, claim.hypothesis))
        keys.append(t["task_id"])
    if pairs:
        verdicts = nli_model.predict_bidirectional(pairs)
        for k, v in zip(keys, verdicts):
            out[k] = {"sym": v["sym_contra"],
                      "score": round(v["contra_score"], 3),
                      "nli": "矛盾" if v["sym_contra"] else "非矛盾"}
    for t in tasks:
        out.setdefault(t["task_id"], {"sym": None, "score": None, "nli": "n/a"})
    return out


def cmd_pack() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    tasks = json.loads(TASKS86.read_text(encoding="utf-8"))
    print("86条裁决任务加载 | 生成机器意见(NLI双向)...")
    from algorithms.consistency_check.nli_local import NliLocal
    nli = NliLocal("mdeberta")
    mode = nli.ensure()
    if mode == "unavailable":
        print(f"NLI不可用({nli.last_error}), 生成无意见包")
        opinions = {t["task_id"]: {"sym": None, "score": None, "nli": "n/a"}
                    for t in tasks}
    else:
        opinions = machine_opinion(nli)
        n_sym = sum(1 for o in opinions.values() if o["sym"])
        print(f"机器意见: {n_sym}/{sum(1 for o in opinions.values() if o['sym'] is not None)}"
              f" 条sym_contra | 推理{nli.stats['infer_ms']}ms")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "annotation_pack_86.csv"
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "pair", "dtype", "分歧证据",
                    "表格侧", "图侧", "上下文",
                    "机器意见(NLI)", "矛盾分",
                    "人工标签(real_bug/benign_variation/compiler_bug/unsure)",
                    "备注"])
        for t in tasks:
            o = opinions.get(t["task_id"], {})
            ctx_txt = (f"{t.get('uc_name', '')} | {t.get('image_caption', '')} "
                       f"vs {t.get('table_caption', '')} | "
                       f"表{t.get('n_table_steps', '?')}步/图{t.get('n_diag_nodes', '?')}节点"
                       f"/匹配{t.get('n_matched', '?')} | match_score={t.get('match_score', '')}")
            w.writerow([t["task_id"], t["pair_key"], t.get("dtype", ""),
                        t.get("evidence", "")[:100],
                        json.dumps(t.get("table_side") or {}, ensure_ascii=False)[:80],
                        json.dumps(t.get("diag_side") or {}, ensure_ascii=False)[:80],
                        ctx_txt[:120],
                        o.get("nli", "n/a"), o.get("score", ""),
                        "", ""])
    print(f"标注包 → {csv_path}")
    print("  填写'人工标签'列(四选一)后运行:")
    print(f"  python tools/annotation_pack.py fill --file {csv_path}")

    # 100条双标注任务(答案键已备, 直接拷贝为对照包)
    ha = BASE / "data/gjb_438c/data_assets/srs_qa_v3/human_annotation"
    if (ha / "annotation_task.csv").exists():
        dst = OUT_DIR / "annotation_task_100.csv"
        dst.write_bytes((ha / "annotation_task.csv").read_bytes())
        print(f"双标注任务(100条) → {dst} (answer_key在原目录, 标注后统计一致性)")


def cmd_fill(path: Path) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    filled = [r for r in rows if r.get("人工标签(real_bug/benign_variation/compiler_bug/unsure)",
                                       "").strip()]
    print(f"回填: {len(filled)}/{len(rows)}条已标注")
    if not filled:
        print("无标注, 退出")
        return
    gold = {}
    from collections import Counter
    dist = Counter()
    for r in filled:
        label = r["人工标签(real_bug/benign_variation/compiler_bug/unsure)"].strip()
        if label not in LABELS:
            print(f"  ⚠ 非法标签: {r['task_id']}={label!r}(跳过)")
            continue
        gold[r["task_id"]] = {"label": label, "pair": r.get("pair", ""),
                              "note": r.get("备注", "").strip()}
        dist[label] += 1
    out = OUT_DIR / "human_gold_86.json"
    out.write_text(json.dumps({"n": len(gold), "dist": dict(dist),
                               "labels": gold, "source": str(path),
                               "date": "2026-09-16"},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"金标 → {out} | 分布: {dict(dist)}")

    # 与664银标对比(标注升级报告)
    fa = BASE / "data/gjb_438c/anchor_v2/final_adjudication.json"
    if fa.exists():
        silver = json.loads(fa.read_text(encoding="utf-8"))["final_labels"]
        overlap = [(k, gold[k]["label"], silver[k]["label"])
                   for k in gold if k in silver]
        if overlap:
            agree = sum(1 for _, g, s in overlap if g == s)
            print(f"\n与664银标对比: 重叠{len(overlap)}条, 一致{agree}"
                  f"({agree/len(overlap):.0%})")
            for k, g, s in overlap:
                if g != s:
                    print(f"  分歧: {k} 人工={g} 银标={s}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("pack")
    fp = sub.add_parser("fill")
    fp.add_argument("--file", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "pack":
        cmd_pack()
    elif args.cmd == "fill":
        cmd_fill(args.file)


if __name__ == "__main__":
    main()
