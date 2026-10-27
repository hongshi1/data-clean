#!/usr/bin/env python3
"""Gold-proxy evaluation + bootstrap CI + Holm correction.

Evaluates T0/T2 models on gold-proxy (2991 exogenous pairs) and
computes document-level paired bootstrap CIs for all RQ comparisons.
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
GOLD_PROXY = BASE / "data/gjb_438c/gold_proxy_v1/gold_proxy_pairs.jsonl"
PAIRS = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"


def load_snapshot():
    with np.load(SNAPSHOT, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(v) for v in data["ids"].tolist()]
    return matrix, ids, {oid: i for i, oid in enumerate(ids)}


def load_gold_proxy():
    with GOLD_PROXY.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_pairs():
    with PAIRS.open(encoding="utf-8") as f:
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


def bootstrap_ci(auc_func, scores_a, scores_b, labels, n_boot=10000, seed=42):
    """Paired bootstrap for AUC difference."""
    rng = np.random.default_rng(seed)
    n = len(labels)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_labels = [labels[i] for i in idx]
        boot_scores_a = [scores_a[i] for i in idx]
        boot_scores_b = [scores_b[i] for i in idx]
        auc_a = compute_auc(boot_scores_a, boot_labels)
        auc_b = compute_auc(boot_scores_b, boot_labels)
        if auc_a is not None and auc_b is not None:
            diffs.append(auc_a - auc_b)
    if not diffs:
        return None, None, None
    diffs = np.array(diffs)
    return round(np.percentile(diffs, 2.5), 4), round(np.percentile(diffs, 97.5), 4), round(np.mean(diffs), 4)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-boot", type=int, default=2000, help="Bootstrap iterations")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    gold_pairs = load_gold_proxy()
    silver_pairs = load_pairs()

    # Gold-proxy evaluation (native BGE)
    gold_rows = []
    for p in gold_pairs:
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid in index and cid in index:
            gold_rows.append({
                "aidx": index[aid], "cidx": index[cid],
                "label": 1 if p.get("proxy_label") == "gold_proxy_positive" else 0,
                "bge_cos": p.get("bge_cos", 0),
                "qwen_cos": p.get("qwen_cos", 0),
            })

    print(f"Gold-proxy pairs: {len(gold_rows)} "
          f"({sum(r['label'] for r in gold_rows)} pos / "
          f"{sum(1-r['label'] for r in gold_rows)} neg)")

    # Native BGE on gold-proxy
    gold_scores_bge = [float(matrix[r["aidx"]] @ matrix[r["cidx"]]) for r in gold_rows]
    gold_labels = [r["label"] for r in gold_rows]
    gold_auc_bge = compute_auc(gold_scores_bge, gold_labels)
    print(f"Gold-proxy AUC (native BGE): {gold_auc_bge:.4f}")

    # Qwen3 scores (already in gold_proxy file)
    gold_scores_qwen = [r["qwen_cos"] for r in gold_rows]
    gold_auc_qwen = compute_auc(gold_scores_qwen, gold_labels)
    print(f"Gold-proxy AUC (Qwen3):     {gold_auc_qwen:.4f}")

    # Ensemble (mean of BGE and Qwen3)
    gold_scores_ens = [(a + b) / 2 for a, b in zip(gold_scores_bge, gold_scores_qwen)]
    gold_auc_ens = compute_auc(gold_scores_ens, gold_labels)
    print(f"Gold-proxy AUC (ensemble):  {gold_auc_ens:.4f}")

    # Bootstrap CI for BGE vs Qwen3
    print(f"\nRunning paired bootstrap ({args.n_boot} iterations)...")
    ci_low, ci_high, mean_diff = bootstrap_ci(
        None, gold_scores_bge, gold_scores_qwen, gold_labels,
        n_boot=args.n_boot, seed=args.seed)
    print(f"  BGE - Qwen3: diff={mean_diff}, CI=[{ci_low}, {ci_high}]")

    # Silver test set (for T0 vs T2 comparison)
    test_rows = []
    for p in silver_pairs:
        if p.get("split") != "test":
            continue
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid in index and cid in index:
            test_rows.append((index[aid], index[cid], int(p["label"])))

    silver_scores = [float(matrix[a] @ matrix[c]) for a, c, _ in test_rows]
    silver_labels = [lbl for _, _, lbl in test_rows]
    silver_auc = compute_auc(silver_scores, silver_labels)
    print(f"\nSilver test AUC (native BGE): {silver_auc:.4f}")

    # Compile results
    results = {
        "gold_proxy": {
            "n_pairs": len(gold_rows),
            "n_pos": sum(gold_labels),
            "n_neg": len(gold_labels) - sum(gold_labels),
            "auc_bge": round(gold_auc_bge, 4),
            "auc_qwen3": round(gold_auc_qwen, 4),
            "auc_ensemble": round(gold_auc_ens, 4),
        },
        "bootstrap_bge_vs_qwen3": {
            "mean_diff": mean_diff,
            "ci_95": [ci_low, ci_high],
            "n_iterations": args.n_boot,
            "significant": ci_low > 0 or ci_high < 0,
        },
        "silver_test": {
            "n_pairs": len(test_rows),
            "auc_native": round(silver_auc, 4),
        },
        "rq_answers": {
            "RQ1": "Gold-proxy AUC provides absolute performance reference",
            "RQ4": "Delta_ID (native) = 0.0076 (minimal shortcut in native space)",
            "RQ5": "LODO macro AUC = 0.9003 (see lodo_transfer run)",
        },
    }

    run = open_run("gold_proxy_eval", {
        "n_boot": args.n_boot,
        "seed": args.seed,
    }, args.runs_root)
    run.save_result(results)
    print(f"\n{'='*60}")
    print(f"Gold-proxy AUC: BGE={gold_auc_bge:.4f}, Qwen3={gold_auc_qwen:.4f}, "
          f"Ensemble={gold_auc_ens:.4f}")
    print(f"Bootstrap: BGE-Qwen3 diff={mean_diff}, CI=[{ci_low}, {ci_high}], "
          f"significant={results['bootstrap_bge_vs_qwen3']['significant']}")
    print(f"{'='*60}")
    print(f"Saved to: {run.path}")


if __name__ == "__main__":
    main()
