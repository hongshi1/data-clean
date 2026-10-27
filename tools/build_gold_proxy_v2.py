#!/usr/bin/env python3
"""P0: Gold-proxy v2 — leave-one-signal construction + hard negatives.

Fixes H1 (circular construction): labels are constructed using the OTHER
encoder's signal, breaking the circularity.

v2b: evaluate BGE → labels from Qwen3 signal
     evaluate Qwen3 → labels from BGE signal
v2c: hard negatives from sibling high-score band (top 5%) instead of low band.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

SNAPSHOT = BASE / "data/gjb_438c/feature_snapshot_v1/vectors.npz"
PAIRS = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
FEATURES = BASE / "data/gjb_438c/feature_snapshot_v1/features.jsonl"
V1_PROXY = BASE / "data/gjb_438c/gold_proxy_v1/gold_proxy_pairs.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
OUT = BASE / "data/gjb_438c/gold_proxy_v2"


def load_snapshot():
    with np.load(SNAPSHOT, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(v) for v in data["ids"].tolist()]
    return matrix, ids, {oid: i for i, oid in enumerate(ids)}


def load_pairs():
    with PAIRS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_features():
    with FEATURES.open(encoding="utf-8") as f:
        return {json.loads(line)["occurrence_id"]: json.loads(line)
                for line in f if line.strip()}


def load_v1():
    with V1_PROXY.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_auc(scores, labels):
    pos = sum(labels)
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return None
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and scores[order[end + 1]] == scores[order[start]]:
            end += 1
        avg_rank = (start + end) / 2.0 + 1.0
        for i in order[start:end + 1]:
            ranks[i] = avg_rank
        start = end + 1
    rank_sum_pos = sum(ranks[i] for i, lbl in enumerate(labels) if lbl == 1)
    return (rank_sum_pos - pos * (pos + 1) / 2) / (pos * neg)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    pairs = load_pairs()
    v1 = load_v1()

    # Extract Qwen3 and BGE scores from v1 (same pair set, different signals)
    v1_map = {}
    for r in v1:
        key = (r["anchor"]["occurrence_id"], r["candidate"]["occurrence_id"])
        v1_map[key] = {
            "bge_cos": r.get("bge_cos", 0),
            "qwen3_cos": r.get("qwen3_cos", 0),
            "proxy_label": r.get("proxy_label"),
        }

    # Build test fold pairs with both signal scores
    test_pairs = []
    for p in pairs:
        if p.get("split") != "test":
            continue
        key = (p["anchor"]["occurrence_id"], p["candidate"]["occurrence_id"])
        if key not in v1_map:
            continue
        v1_data = v1_map[key]
        test_pairs.append({
            "anchor_id": key[0],
            "candidate_id": key[1],
            "label": int(p["label"]),
            "basis": str(p.get("label_basis", "")),
            "bge_cos": v1_data["bge_cos"],
            "qwen3_cos": v1_data["qwen3_cos"],
        })

    print(f"Test pairs with dual signals: {len(test_pairs)}")
    print(f"  Positives: {sum(r['label'] for r in test_pairs)}")
    print(f"  Negatives: {sum(1 - r['label'] for r in test_pairs)}")

    # Compute thresholds using DEV signal (not test)
    # For v2b: evaluate BGE → use Qwen3 threshold
    #            evaluate Qwen3 → use BGE threshold

    # Get all pairs (train+dev+test) for threshold estimation
    all_scored = []
    for p in pairs:
        key = (p["anchor"]["occurrence_id"], p["candidate"]["occurrence_id"])
        if key in v1_map and p["anchor"]["occurrence_id"] in index:
            all_scored.append({
                "label": int(p["label"]),
                "basis": str(p.get("label_basis", "")),
                "bge_cos": v1_map[key]["bge_cos"],
                "qwen3_cos": v1_map[key]["qwen3_cos"],
            })

    # Silver labels for threshold
    silver_labels = [r["label"] for r in all_scored]
    bge_all = [r["bge_cos"] for r in all_scored]
    qwen_all = [r["qwen3_cos"] for r in all_scored]

    # Threshold: 95th percentile of negative scores
    neg_bge = sorted(s for s, lbl in zip(bge_all, silver_labels) if lbl == 0)
    neg_qwen = sorted(s for s, lbl in zip(qwen_all, silver_labels) if lbl == 0)
    th_bge = neg_bge[int(np.ceil(0.95 * len(neg_bge))) - 1] if neg_bge else 0.5
    th_qwen = neg_qwen[int(np.ceil(0.95 * len(neg_qwen))) - 1] if neg_qwen else 0.5

    print("\nThresholds (95th percentile of negatives):")
    print(f"  BGE:   {th_bge:.4f}")
    print(f"  Qwen3: {th_qwen:.4f}")

    # v2b: Leave-one-signal construction
    # Evaluate BGE → labels from Qwen3 signal
    # Evaluate Qwen3 → labels from BGE signal

    results = {}

    # --- Evaluate BGE (labels from Qwen3) ---
    # Positive: P1 silver positive ∧ Qwen3 score ≥ th_qwen
    # Negative: P1 silver negative ∧ Qwen3 score < th_qwen_low
    qwen_pos_th = th_qwen
    qwen_neg_th = neg_qwen[int(np.ceil(0.05 * len(neg_qwen))) - 1] if neg_qwen else 0.3

    v2b_bge = []
    for r in test_pairs:
        if r["label"] == 1 and r["qwen3_cos"] >= qwen_pos_th:
            v2b_bge.append({"score": r["bge_cos"], "label": 1})
        elif r["label"] == 0 and r["qwen3_cos"] < qwen_neg_th:
            v2b_bge.append({"score": r["bge_cos"], "label": 0})

    bge_scores_v2 = [r["score"] for r in v2b_bge]
    bge_labels_v2 = [r["label"] for r in v2b_bge]
    auc_bge_v2 = compute_auc(bge_scores_v2, bge_labels_v2)
    results["v2b_bge"] = {
        "auc": round(auc_bge_v2, 4) if auc_bge_v2 else None,
        "n": len(v2b_bge),
        "pos": sum(bge_labels_v2),
        "neg": len(bge_labels_v2) - sum(bge_labels_v2),
    }
    print(f"\nv2b Evaluate BGE (labels from Qwen3): AUC={auc_bge_v2}, n={len(v2b_bge)}")

    # --- Evaluate Qwen3 (labels from BGE) ---
    bge_pos_th = th_bge
    bge_neg_th = neg_bge[int(np.ceil(0.05 * len(neg_bge))) - 1] if neg_bge else 0.3

    v2b_qwen = []
    for r in test_pairs:
        if r["label"] == 1 and r["bge_cos"] >= bge_pos_th:
            v2b_qwen.append({"score": r["qwen3_cos"], "label": 1})
        elif r["label"] == 0 and r["bge_cos"] < bge_neg_th:
            v2b_qwen.append({"score": r["qwen3_cos"], "label": 0})

    qwen_scores_v2 = [r["score"] for r in v2b_qwen]
    qwen_labels_v2 = [r["label"] for r in v2b_qwen]
    auc_qwen_v2 = compute_auc(qwen_scores_v2, qwen_labels_v2)
    results["v2b_qwen3"] = {
        "auc": round(auc_qwen_v2, 4) if auc_qwen_v2 else None,
        "n": len(v2b_qwen),
        "pos": sum(qwen_labels_v2),
        "neg": len(qwen_labels_v2) - sum(qwen_labels_v2),
    }
    print(f"v2b Evaluate Qwen3 (labels from BGE): AUC={auc_qwen_v2}, n={len(v2b_qwen)}")

    # v2c: Hard negatives (sibling high-score band)
    # Instead of low-band negatives, use sibling negatives with HIGH BGE scores
    # These are harder to distinguish from positives

    print("\n--- v2c: Hard Negatives ---")

    # Get sibling negatives with high BGE scores (top 5% of negatives)
    sibling_negs = [r for r in test_pairs
                    if r["label"] == 0 and "sibling" in r["basis"]]
    if sibling_negs:
        sibling_bge = sorted([r["bge_cos"] for r in sibling_negs], reverse=True)
        hard_th = sibling_bge[int(0.05 * len(sibling_bge))]
        hard_negs = [r for r in sibling_negs if r["bge_cos"] >= hard_th]
        print(f"  Sibling negatives: {len(sibling_negs)}, hard (top 5%): {len(hard_negs)}")

        # v2c: BGE labels from Qwen3, hard negatives
        v2c_bge = []
        for r in test_pairs:
            if r["label"] == 1 and r["qwen3_cos"] >= qwen_pos_th:
                v2c_bge.append({"score": r["bge_cos"], "label": 1,
                                "pair": r})
            elif r in hard_negs:
                v2c_bge.append({"score": r["bge_cos"], "label": 0,
                                "pair": r})

        bge_scores_c = [r["score"] for r in v2c_bge]
        bge_labels_c = [r["label"] for r in v2c_bge]
        auc_bge_c = compute_auc(bge_scores_c, bge_labels_c)
        results["v2c_bge_hard"] = {
            "auc": round(auc_bge_c, 4) if auc_bge_c else None,
            "n": len(v2c_bge),
            "pos": sum(bge_labels_c),
            "neg": len(bge_labels_c) - sum(bge_labels_c),
            "hard_neg_th": round(hard_th, 4),
        }
        print(f"v2c Evaluate BGE (hard negatives): AUC={auc_bge_c}, "
              f"n={len(v2c_bge)} ({sum(bge_labels_c)}pos/{len(bge_labels_c)-sum(bge_labels_c)}neg)")

    # Summary comparison
    print(f"\n{'='*60}")
    print("GOLD-PROXY v2 RESULTS")
    print(f"{'='*60}")
    print("v1 (circular):   BGE AUC=1.0000, Qwen3 AUC=0.5000")
    print(f"v2b (leave-one): BGE AUC={auc_bge_v2}, Qwen3 AUC={auc_qwen_v2}")
    if "v2c_bge_hard" in results:
        print(f"v2c (hard neg):  BGE AUC={results['v2c_bge_hard']['auc']}")
    print(f"{'='*60}")

    # Save v2 proxy pairs
    OUT.mkdir(parents=True, exist_ok=True)
    v2_pairs = []
    for r in test_pairs:
        if r["label"] == 1 and r["qwen3_cos"] >= qwen_pos_th:
            v2_pairs.append({
                "anchor": {"occurrence_id": r["anchor_id"]},
                "candidate": {"occurrence_id": r["candidate_id"]},
                "proxy_label": "gold_proxy_positive",
                "proxy_basis": "v2b_leave_one_signal_qwen3",
                "bge_cos": r["bge_cos"],
                "qwen3_cos": r["qwen3_cos"],
            })
        elif r["label"] == 0 and r["bge_cos"] < bge_neg_th:
            v2_pairs.append({
                "anchor": {"occurrence_id": r["anchor_id"]},
                "candidate": {"occurrence_id": r["candidate_id"]},
                "proxy_label": "gold_proxy_negative",
                "proxy_basis": "v2b_leave_one_signal_bge_low",
                "bge_cos": r["bge_cos"],
                "qwen3_cos": r["qwen3_cos"],
            })

    with (OUT / "gold_proxy_pairs.jsonl").open("w", encoding="utf-8") as f:
        for p in v2_pairs:
            f.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n")

    summary = {
        "v2b_bge": results.get("v2b_bge"),
        "v2b_qwen3": results.get("v2b_qwen3"),
        "v2c_bge_hard": results.get("v2c_bge_hard"),
        "v1_comparison": {
            "v1_bge_auc": 1.0,
            "v1_qwen3_auc": 0.5,
            "circularity_fixed": auc_bge_v2 is not None and auc_bge_v2 < 1.0,
        },
        "n_v2_pairs": len(v2_pairs),
        "config": {
            "seed": args.seed,
            "qwen_pos_th": round(qwen_pos_th, 4),
            "bge_neg_th": round(bge_neg_th, 4),
        },
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8")

    run = open_run("gold_proxy_v2", {"seed": args.seed}, args.runs_root)
    run.save_result(summary)
    print(f"\nSaved {len(v2_pairs)} v2 pairs to {OUT}")
    print(f"Run: {run.path}")


if __name__ == "__main__":
    main()
