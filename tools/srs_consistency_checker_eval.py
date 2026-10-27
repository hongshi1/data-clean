"""ConsistencyChecker(六族集成路由) vs v12直接NLI — 296条真实金标评测.

评测集: gold_v2_clean_137(130) + md_test_sc3(148) + md_test_doc047(18) = 296条
指标: 总体bAcc / 分集bAcc / 各族bAcc / 路由准确率 / 与v12直接NLI对比
输出: data/gjb_438c/runs/consistency_checker_eval.json
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GOLD_DIR = ROOT / "data/gjb_438c/human_gold"
OUT_PATH = ROOT / "data/gjb_438c/runs/consistency_checker_eval.json"
MODEL_DIR = ROOT / "models/nli/roberta-v12-anchor"

GOLD_FILES = [
    ("gold_v2_clean_137.json", "clean130"),
    ("md_test_sc3.json", "md166_sc3"),
    ("md_test_doc047.json", "md166_doc047"),
]

FAMILY_B = {"ORDER_CONFLICT", "LOGIC-01", "LOGIC-03"}
FAMILY_C = {"TABLE_ITEM_MISSING", "STEP_MISSING", "ACTOR_MISSING", "EXC_MISSING",
            "COMPONENT_MISSING", "DIAGRAM_EXTRA", "DIAGRAM_EXTRA_COUNT",
            "UC_NAME_MISMATCH", "LOGIC-05"}


def gold_family(etype: str) -> str:
    if etype in FAMILY_B:
        return "B"
    if etype in FAMILY_C:
        return "C"
    if etype.startswith("PARAM"):
        return "A"
    if etype.startswith("TERM"):
        return "D"
    if etype.startswith("GJB"):
        return "E"
    return "F"


def bacc_details(labels: list[str], preds: list[str]) -> dict:
    tp = sum(1 for lb, p in zip(labels, preds) if lb == "inconsistent" and p == "inconsistent")
    fn = sum(1 for lb, p in zip(labels, preds) if lb == "inconsistent" and p == "consistent")
    tn = sum(1 for lb, p in zip(labels, preds) if lb == "consistent" and p == "consistent")
    fp = sum(1 for lb, p in zip(labels, preds) if lb == "consistent" and p == "inconsistent")
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    return {
        "n": len(labels),
        "pos": tp + fn, "neg": tn + fp,
        "tp": tp, "fn": fn, "tn": tn, "fp": fp,
        "tpr": round(tpr, 4), "tnr": round(tnr, 4),
        "bacc": round((tpr + tnr) / 2, 4),
        "acc": round((tp + tn) / len(labels), 4) if labels else 0.0,
    }


def load_gold() -> list[dict]:
    data = []
    for fname, tag in GOLD_FILES:
        with open(GOLD_DIR / fname, encoding="utf-8") as fh:
            items = json.load(fh)
        for it in items:
            it["dataset_tag"] = tag
        data.extend(items)
    return data


def run_checker(data: list[dict]) -> list[dict]:
    from algorithms.consistency.checker import ConsistencyChecker
    ck = ConsistencyChecker()
    out = []
    for it in data:
        r = ck.check(it["premise"], it["hypothesis"])
        out.append({
            "id": it["id"], "label": it["label"], "gold_family": gold_family(it["type"]),
            "gold_type": it["type"], "dataset_tag": it["dataset_tag"],
            "pred": r.verdict, "routed_family": r.family, "solver": r.solver,
            "pred_type": r.type, "confidence": round(r.confidence, 3),
            "evidence": r.evidence,
        })
    return out


def run_v12(data: list[dict], batch_size: int = 32) -> list[dict]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(MODEL_DIR), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(MODEL_DIR), local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    preds, probs = [], []
    pairs = [(it["premise"], it["hypothesis"]) for it in data]
    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i + batch_size]
        enc = tok([p for p, _ in batch], [h for _, h in batch], padding=True,
                  truncation=True, max_length=128, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
        pr = torch.softmax(logits, dim=-1).cpu().tolist()
        probs.extend(round(p[1], 4) for p in pr)
        preds.extend("inconsistent" if p[1] >= 0.5 else "consistent" for p in pr)
    return [{"id": it["id"], "pred": p, "prob_inc": pr}
            for it, p, pr in zip(data, preds, probs)]


def group_stats(rows: list[dict], key_fn) -> dict:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(key_fn(r), []).append(r)
    return {k: bacc_details([r["label"] for r in v], [r["pred"] for r in v])
            for k, v in sorted(groups.items())}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = load_gold()
    print(f"金标总数: {len(data)}  (clean130={sum(1 for d in data if d['dataset_tag'] == 'clean130')}, "
          f"md166={sum(1 for d in data if d['dataset_tag'] != 'clean130')})")

    rows = run_checker(data)
    v12 = run_v12(data)
    for r, v in zip(rows, v12):
        r["v12_pred"] = v["pred"]
        r["v12_prob_inc"] = v["prob_inc"]

    labels = [r["label"] for r in rows]
    ck_preds = [r["pred"] for r in rows]
    v12_preds = [r["v12_pred"] for r in rows]

    ck_overall = bacc_details(labels, ck_preds)
    v12_overall = bacc_details(labels, v12_preds)

    per_dataset = {}
    for tag in ["clean130", "md166_sc3", "md166_doc047"]:
        sub = [r for r in rows if r["dataset_tag"] == tag]
        per_dataset[tag] = {
            "checker": bacc_details([r["label"] for r in sub], [r["pred"] for r in sub]),
            "v12": bacc_details([r["label"] for r in sub], [r["v12_pred"] for r in sub]),
        }
    md_sub = [r for r in rows if r["dataset_tag"] != "clean130"]
    per_dataset["md166_total"] = {
        "checker": bacc_details([r["label"] for r in md_sub], [r["pred"] for r in md_sub]),
        "v12": bacc_details([r["label"] for r in md_sub], [r["v12_pred"] for r in md_sub]),
    }

    per_gold_family_ck = group_stats(rows, lambda r: r["gold_family"])
    per_gold_family_v12 = group_stats(
        [{**r, "pred": r["v12_pred"]} for r in rows], lambda r: r["gold_family"])
    per_gold_type_ck = group_stats(rows, lambda r: r["gold_type"])
    per_gold_type_v12 = group_stats(
        [{**r, "pred": r["v12_pred"]} for r in rows], lambda r: r["gold_type"])
    per_routed_family = group_stats(rows, lambda r: r["routed_family"])

    route_confusion: dict[str, Counter] = {}
    for r in rows:
        route_confusion.setdefault(r["gold_family"], Counter())[r["routed_family"]] += 1
    route_correct = sum(1 for r in rows if r["routed_family"] == r["gold_family"])
    routing = {
        "accuracy": round(route_correct / len(rows), 4),
        "confusion": {g: dict(sorted(c.items())) for g, c in sorted(route_confusion.items())},
        "routed_distribution": dict(sorted(Counter(r["routed_family"] for r in rows).items())),
    }
    route_acc_by_type = group_stats(
        [{**r, "pred": "inconsistent" if r["routed_family"] == r["gold_family"] else "consistent"}
         for r in rows], lambda r: r["gold_type"])
    routing["route_acc_by_gold_type"] = {
        k: {"n": v["n"], "route_acc": v["tpr"]} for k, v in route_acc_by_type.items()}

    gained = [r for r in rows if r["pred"] != r["v12_pred"] and r["pred"] == r["label"]]
    lost = [r for r in rows if r["pred"] != r["v12_pred"] and r["pred"] != r["label"]]
    flip = {
        "n_diff": sum(1 for r in rows if r["pred"] != r["v12_pred"]),
        "gained": len(gained), "lost": len(lost),
        "net": len(gained) - len(lost),
        "gained_by_routed_family": dict(sorted(Counter(r["routed_family"] for r in gained).items())),
        "lost_by_routed_family": dict(sorted(Counter(r["routed_family"] for r in lost).items())),
        "lost_examples": [
            {"id": r["id"], "gold_type": r["gold_type"], "routed": r["routed_family"],
             "solver": r["solver"], "gold": r["label"], "checker": r["pred"],
             "v12": r["v12_pred"], "evidence": r["evidence"]}
            for r in lost[:10]],
        "gained_examples": [
            {"id": r["id"], "gold_type": r["gold_type"], "routed": r["routed_family"],
             "solver": r["solver"], "gold": r["label"], "checker": r["pred"], "v12": r["v12_pred"]}
            for r in gained[:10]],
    }

    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        sha = "unknown"

    result = {
        "meta": {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "git_sha": sha,
            "n_total": len(rows),
            "files": {f: t for f, t in GOLD_FILES},
            "label_dist": dict(sorted(Counter(labels).items())),
            "gold_type_dist": dict(sorted(Counter(r["gold_type"] for r in rows).items())),
            "positive_class": "inconsistent",
        },
        "overall": {
            "checker": ck_overall, "v12_direct_nli": v12_overall,
            "delta_bacc": round(ck_overall["bacc"] - v12_overall["bacc"], 4),
        },
        "per_dataset": per_dataset,
        "per_gold_family": {"checker": per_gold_family_ck, "v12": per_gold_family_v12},
        "per_gold_type": {"checker": per_gold_type_ck, "v12": per_gold_type_v12},
        "per_routed_family": per_routed_family,
        "routing": routing,
        "flip_analysis_checker_vs_v12": flip,
        "rows": rows,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(f"\n[总体] checker bAcc={ck_overall['bacc']:.4f} (tpr={ck_overall['tpr']}, tnr={ck_overall['tnr']})  "
          f"v12 bAcc={v12_overall['bacc']:.4f} (tpr={v12_overall['tpr']}, tnr={v12_overall['tnr']})  "
          f"delta={result['overall']['delta_bacc']:+.4f}")
    print(f"[分集] clean130: ck={per_dataset['clean130']['checker']['bacc']:.4f} v12={per_dataset['clean130']['v12']['bacc']:.4f} | "
          f"md166: ck={per_dataset['md166_total']['checker']['bacc']:.4f} v12={per_dataset['md166_total']['v12']['bacc']:.4f}")
    print(f"[路由] accuracy={routing['accuracy']:.4f}  routed_dist={routing['routed_distribution']}  "
          f"confusion={routing['confusion']}")
    print("[按金标族] checker:", {k: v["bacc"] for k, v in per_gold_family_ck.items()},
          " v12:", {k: v["bacc"] for k, v in per_gold_family_v12.items()})
    print("[按路由族] n/acc:", {k: (v["n"], v["acc"]) for k, v in per_routed_family.items()})
    print(f"[翻转] diff={flip['n_diff']} gained={flip['gained']} lost={flip['lost']} net={flip['net']:+d}")
    print(f"\n已保存: {OUT_PATH}")


if __name__ == "__main__":
    main()
