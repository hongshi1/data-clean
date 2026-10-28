#!/usr/bin/env python3
"""减法模块接入一致性校验管线(QAConsistencyModule)的对比实验.

对应文档: 73号. 回答: 在真实一致性校验系统中, 证据减法模块
有无/与现有deq管线的效果对比.

管线: QAInput(question, answer, evidence) → [证据过滤层] → L1专家
      → L2 NLI残差 → 三态裁决(support/refute/not_in_evidence)

三种配置(同一NLI/同一阈值/同一标签, 只换证据过滤层):
  RAW         无过滤(原始证据直入)          — 现状基线
  DEQ         现有deq管线(E0 scope+E1打分)  — 既有方法(软排序)
  SUBTRACTOR  本文减法模块(F1+F2+F3)        — 硬否决+粒度归一

评测集(108实例, 三态标签):
  91条冻结QA — silver标签(GLM-5.3复核, 非人工gold, 披露)
  17条真实违例 — 设计gold(全部期望refute, 源文档已验证)

指标: 三态混淆矩阵 → accuracy / macro-F1 / 各类P/R/F1;
     违例子集单报refute查全(设计金标部分).
图表: docs/srs_project/fig73_qa_module.png (图表1)
用法: python tools/eval_subtractor_qa.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import torch  # noqa: E402,F401 (加载顺序约束, 见68号)

from algorithms.consistency.eval_lib import (  # noqa: E402
    accuracy as lib_accuracy,
    build_qa_input,
    evaluate_module,
    load_frozen_qa,
    load_silver_labels,
    macro_f1,
    per_class_metrics,
)
from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

VIO_PATH = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
SILVER_PATH = (BASE / "data/gjb_438c/runs"
               / "review_qa_with_glm53_582b51e5_20261021_145212"
               / "final_labels.jsonl")
OUT_JSON = BASE / "data/gjb_438c/localization_gold/subtractor_qa_eval_v1.json"
OUT_FIG = BASE / "docs/srs_project/fig73_qa_module.png"


def load_violation_records() -> list[dict]:
    rows = [json.loads(line) for line in VIO_PATH.open(encoding="utf-8")]
    for r in rows:
        r["context_freeze_id"] = r.get("context_freeze_id", "doc04-viol")
    return rows


def subset_confusion(per_row: list[dict], ids: set[str]) -> Counter:
    conf: Counter = Counter()
    for row in per_row:
        if row["instance_id"] in ids and row["label"] is not None:
            conf[(row["predicted"], row["label"])] += 1
    return conf


def purification_stats(records: list[dict], mode: str) -> dict:
    """提纯统计(与管线同款过滤的离线计量): 块/语句的输入→保留.

    mode: raw(全量) | deq(E0门控后) | sub(F1+F3删除后, 与qa_module
    use_subtractor分支同参数: 只删块, max_statements=∞)
    """
    from dataclasses import asdict

    from algorithms.consistency.evidence_subtractor import subtract
    blocks_in = blocks_out = stmts_in = stmts_out = 0
    for rec in records:
        evs = build_qa_input(rec).evidence
        blocks_in += len(evs)
        stmts_in += len(linearize_context(evs))
        if mode == "deq":
            from algorithms.consistency.deq_pipeline import deq_pipeline
            kept = deq_pipeline(rec["question"], rec["answer"],
                                evs).ranked_evidence
        elif mode == "sub":
            pack = subtract(rec["question"], rec["answer"],
                            [asdict(ev) for ev in evs],
                            max_statements=10 ** 9)
            ids = {k["evidence_id"] for k in pack["kept"]}
            kept = tuple(ev for ev in evs if ev.evidence_id in ids)
        else:
            kept = evs
        blocks_out += len(kept)
        stmts_out += len(linearize_context(kept))
    return {"blocks_in": blocks_in, "blocks_out": blocks_out,
            "stmts_in": stmts_in, "stmts_out": stmts_out}


def main() -> int:
    from algorithms.consistency.nli_local import NliLocal
    client = NliLocal("mdeberta")
    if client.ensure() not in ("cuda", "gpu", "cpu"):
        print(f"NLI不可用: {client.last_error}")
        return 1

    def semantic_nli(pairs):
        return client.predict(pairs)

    qa_records = load_frozen_qa()
    vio_records = load_violation_records()
    records = qa_records + vio_records
    silver = load_silver_labels(SILVER_PATH,
                                verdict_keys=("final_verdict",))
    labels = dict(silver)
    for r in vio_records:
        labels[r["instance_id"]] = r["expected_verdict"]
    vio_ids = {r["instance_id"] for r in vio_records}
    print(f"评测集: {len(qa_records)}QA(silver标签) + "
          f"{len(vio_records)}违例(设计gold=refute)")

    configs = {
        "RAW": dict(use_deq=False, use_subtractor=False),
        "DEQ": dict(use_deq=True, use_subtractor=False),
        "SUBTRACTOR": dict(use_deq=False, use_subtractor=True),
    }
    results: dict[str, dict] = {}
    mode_map = {"RAW": "raw", "DEQ": "deq", "SUBTRACTOR": "sub"}
    for name, kw in configs.items():
        module = QAConsistencyModule(semantic_nli=semantic_nli, **kw)
        outcome = evaluate_module(module, records, labels)
        conf = outcome.confusion
        n_eval = outcome.n_evaluated
        vio_conf = subset_confusion(outcome.per_row, vio_ids)
        vio_recall = (vio_conf[("refute", "refute")]
                      / sum(v for (_p, g), v in vio_conf.items()
                            if g == "refute"))
        pur = purification_stats(records, mode_map[name])
        results[name] = {
            "accuracy": round(lib_accuracy(conf, n_eval), 4),
            "macro_f1": macro_f1(conf),
            "per_class": per_class_metrics(conf),
            "violation_refute_recall": round(vio_recall, 4),
            "purification": {
                "blocks": f"{pur['blocks_out']}/{pur['blocks_in']}",
                "blocks_pct": round(100 * (1 - pur["blocks_out"]
                                           / max(pur["blocks_in"], 1)), 1),
                "statements": f"{pur['stmts_out']}/{pur['stmts_in']}",
                "stmts_pct": round(100 * (1 - pur["stmts_out"]
                                          / max(pur["stmts_in"], 1)), 1),
            },
            "confusion": {f"{p}|{g}": v for (p, g), v in conf.items()},
            "n_removed_diag": sum(
                1 for row in outcome.per_row
                if any(d.startswith("subtractor_removed")
                       for d in row["diagnostics"])),
            "deq_filtered_diag": sum(
                1 for row in outcome.per_row
                if any(d.startswith("deq_filtered")
                       for d in row["diagnostics"])),
        }
        pc = results[name]["per_class"]
        pu = results[name]["purification"]
        print(f"\n[{name}] acc={results[name]['accuracy']} "
              f"macroF1={results[name]['macro_f1']} "
              f"违例refute查全={results[name]['violation_refute_recall']}")
        print(f"    提纯: 块 {pu['blocks']} (-{pu['blocks_pct']}%)  "
              f"语句 {pu['statements']} (-{pu['stmts_pct']}%)")
        for cls in ("support", "refute", "not_in_evidence"):
            m = pc[cls]
            print(f"    {cls:<16} P={m['precision']:.3f} "
                  f"R={m['recall']:.3f} F1={m['f1']:.3f}")
        print(f"    confusion: {results[name]['confusion']}")

    # ── 图表1: 提纯率×精度保持 ────────────────────────
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    names = list(configs)
    xpos = list(range(len(names)))
    w = 0.35
    fig, ax = plt.subplots(figsize=(10, 5.8))
    stmts_pur = [results[n]["purification"]["stmts_pct"] for n in names]
    blocks_pur = [results[n]["purification"]["blocks_pct"] for n in names]
    accs = [100 * results[n]["accuracy"] for n in names]
    ax.bar([x - w / 2 for x in xpos], blocks_pur, w,
           color="#66bb6a", label="证据块提纯率%(删掉的)")
    ax.bar([x + w / 2 for x in xpos], stmts_pur, w,
           color="#42a5f5", label="语句提纯率%(删掉的)")
    for x, bp, sp, acc in zip(xpos, blocks_pur, stmts_pur, accs):
        ax.text(x - w / 2, bp + 0.8, f"{bp:.1f}%", ha="center", fontsize=9)
        ax.text(x + w / 2, sp + 0.8, f"{sp:.1f}%", ha="center", fontsize=9)
        ax.text(x, -8.5, f"准确率 {acc:.1f}%\n违例查全 "
                f"{100 * results[names[x]]['violation_refute_recall']:.0f}%",
                ha="center", fontsize=9, color="#333333")
    ax.set_xticks(xpos, names, fontsize=11)
    ax.set_ylim(-16, 105)
    ax.set_ylabel("提纯率 (%)")
    ax.set_title("图表1 证据提纯模块: 删掉的证据量 × 精度保持 "
                 "(108实例: 91QA+17真实违例, RAW=不过滤基线)")
    ax.legend(fontsize=10, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG, dpi=150)
    print(f"\n图表已保存: {OUT_FIG}")

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"结果已写入: {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
