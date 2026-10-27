r"""LEGACY migration baseline for ``answer_evidence_evalset_v1``.

This evaluator calls the old string-level ``Verifier`` adapter, not the new
``QAConsistencyModule``. Its score is migration-only and must not be reported
as the current QA consistency module result.

It reports macro-F1, 3bAcc and accuracy; this is not a frozen benchmark protocol.
运行配置绑定实际数据SHA/数量/标签，Verifier异常直接使运行失败。
"""
from __future__ import annotations

import json
import hashlib
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
sys.stdout.reconfigure(encoding="utf-8")

LABELS = ["support", "refute", "not_in_evidence"]


def f1(preds: list[str], golds: list[str], pos: str) -> float:
    tp = sum(1 for p, g in zip(preds, golds) if p == g == pos)
    fp = sum(1 for p, g in zip(preds, golds) if p == pos and g != pos)
    fn = sum(1 for p, g in zip(preds, golds) if p != pos and g == pos)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def macro_f1(preds: list[str], golds: list[str]) -> dict:
    f1s = {lab: f1(preds, golds, lab) for lab in LABELS}
    return {"macro_f1": round(sum(f1s.values()) / 3, 3),
            "F1_support": round(f1s["support"], 3),
            "F1_refute": round(f1s["refute"], 3),
            "F1_NIE": round(f1s["not_in_evidence"], 3)}


def three_bacc(preds: list[str], golds: list[str]) -> float:
    recalls = []
    for lab in LABELS:
        n = golds.count(lab)
        if n:
            recalls.append(sum(1 for p, g in zip(preds, golds) if p == g == lab) / n)
    return sum(recalls) / len(recalls) if recalls else 0.0


def dataset_fingerprint(path: Path, entries: list[dict]) -> dict[str, object]:
    """Bind a result to the exact evaluated snapshot and observed label counts."""
    labels = Counter(e["gold"]["label"] for e in entries)
    return {
        "path": path.relative_to(BASE).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "n": len(entries),
        "labels": dict(sorted(labels.items())),
    }


def main() -> None:
    from algorithms.consistency.verify import Evidence, Verifier

    t0 = time.time()
    data_path = BASE / "data/gjb_438c/answer_evidence_evalset_v1.json"
    data = json.loads(data_path.read_text(encoding="utf-8"))["entries"]
    fingerprint = dataset_fingerprint(data_path, data)
    print(f"评测: {len(data)}条")

    v = Verifier()
    preds, golds = [], []
    by_combo = defaultdict(lambda: ([], []))
    by_conf = defaultdict(lambda: ([], []))
    for e in data:
        evs = []
        for ev in e["evidence"]:
            evs.append(Evidence(type=ev["evidence_type"], claims=ev["claims"],
                                source_ref=ev.get("eid", ""), exhaustive=ev.get("exhaustive")))
        r = v.verify_multi(e["answer"]["text"], evs)
        pred = r.verdict
        gold = e["gold"]["label"]
        preds.append(pred)
        golds.append(gold)
        by_combo[e["modality_combo"]][0].append(pred)
        by_combo[e["modality_combo"]][1].append(gold)
        by_conf[e["gold"]["confidence"]][0].append(pred)
        by_conf[e["gold"]["confidence"]][1].append(gold)

    print(f"verify完成 ({time.time() - t0:.0f}s)")
    print(f"预测分布: {dict(Counter(preds))}")
    print(f"金标分布: {dict(Counter(golds))}")

    overall = macro_f1(preds, golds)
    acc = sum(1 for p, g in zip(preds, golds) if p == g) / len(golds)
    print("\n═══ 总体 ═══")
    print(f"macro-F1 = {overall['macro_f1']} | 3bAcc = {three_bacc(preds, golds):.3f} | acc = {acc:.3f}")
    print(f"F1分解: S={overall['F1_support']} R={overall['F1_refute']} N={overall['F1_NIE']}")

    print("\n═══ 分模态组合 ═══")
    table = {}
    for combo in sorted(by_combo, key=lambda c: -len(by_combo[c][1])):
        ps, gs = by_combo[combo]
        m = macro_f1(ps, gs)
        a = sum(1 for p, g in zip(ps, gs) if p == g) / len(gs)
        table[combo] = {"n": len(gs), "macro_f1": m["macro_f1"], "acc": round(a, 3)}
        print(f"  {combo:<20} n={len(gs):<4} macro-F1={m['macro_f1']:.3f} acc={a:.3f}")

    print("\n═══ 分置信 ═══")
    for conf in ("real", "semi_real", "synth"):
        if conf in by_conf:
            ps, gs = by_conf[conf]
            m = macro_f1(ps, gs)
            a = sum(1 for p, g in zip(ps, gs) if p == g) / len(gs)
            print(f"  {conf:<10} n={len(gs):<4} macro-F1={m['macro_f1']:.3f} acc={a:.3f}")

    # 保存
    from run_utils import open_run
    run = open_run("aee_evalset_baseline", {
        "数据集": fingerprint,
        "方法": "verify()接口(我方)",
        "指标": "macro-F1三态+3bAcc诊断"})
    run.save_result({"overall": overall, "acc": round(acc, 3),
                     "3bAcc": round(three_bacc(preds, golds), 3),
                     "by_combo": table, "pred_dist": dict(Counter(preds))})
    print(f"\nsaved → {run.path}")


if __name__ == "__main__":
    main()
