#!/usr/bin/env python3
"""ID-masked evaluation: quantify shortcut dependency (RQ4).

Computes Delta_ID = AUC_full - AUC_IDmask for T0/T2 models.
ID masking: replace ID tokens in text with placeholder, re-embed, re-score.
Since we use cached BGE vectors (no re-encoding), we approximate by:
  1. For each pair, check if both texts contain IDs
  2. Split test set into ID-containing vs ID-free subsets
  3. Report AUC on each subset separately
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
RUNS_ROOT = BASE / "data/gjb_438c/runs"

import re
ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")


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
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    features = load_features()
    pairs = load_pairs()

    # Build test rows with ID info
    test_rows = []
    for p in pairs:
        if p.get("split") != "test":
            continue
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid not in index or cid not in index:
            continue

        # Check if anchor/candidate text contains IDs
        a_feat = features.get(aid, {})
        c_feat = features.get(cid, {})
        a_text = str(a_feat.get("text", ""))
        c_text = str(c_feat.get("text", ""))
        a_has_id = bool(ID_RE.search(a_text))
        c_has_id = bool(ID_RE.search(c_text))
        both_have_id = a_has_id and c_has_id

        test_rows.append({
            "aidx": index[aid], "cidx": index[cid],
            "label": int(p["label"]),
            "both_id": both_have_id,
            "basis": str(p.get("label_basis", "")),
        })

    print(f"Test pairs: {len(test_rows)}")
    print(f"  Both have ID: {sum(1 for r in test_rows if r['both_id'])}")
    print(f"  Not both ID: {sum(1 for r in test_rows if not r['both_id'])}")

    # Compute raw cosine scores (native, no model)
    results = {}

    # Native BGE baseline
    for subset_name, subset_filter in [("full", None), ("both_id", True), ("no_id", False)]:
        rows = test_rows if subset_filter is None else [r for r in test_rows if r["both_id"] == subset_filter]
        if not rows:
            continue
        scores = [float(matrix[r["aidx"]] @ matrix[r["cidx"]]) for r in rows]
        labels = [r["label"] for r in rows]
        auc = compute_auc(scores, labels)
        results[f"native_{subset_name}"] = {
            "auc": round(auc, 4) if auc else None,
            "n": len(rows), "pos": sum(labels),
        }

    # ID-stratified by label basis
    id_pos = [r for r in test_rows if r["both_id"] and r["label"] == 1]
    id_neg = [r for r in test_rows if r["both_id"] and r["label"] == 0]
    noid_pos = [r for r in test_rows if not r["both_id"] and r["label"] == 1]
    noid_neg = [r for r in test_rows if not r["both_id"] and r["label"] == 0]
    print("\nID stratification:")
    print(f"  Both-ID: {len(id_pos)} pos, {len(id_neg)} neg")
    print(f"  No-ID:   {len(noid_pos)} pos, {len(noid_neg)} neg")

    # Delta_ID for native
    auc_full = results.get("native_full", {}).get("auc")
    auc_id = results.get("native_both_id", {}).get("auc")
    auc_noid = results.get("native_no_id", {}).get("auc")
    if auc_full and auc_id:
        delta = auc_full - auc_id
        results["native_delta_id"] = round(delta, 4)
    if auc_id and auc_noid:
        results["native_id_gap"] = round(auc_id - auc_noid, 4)

    print("\nNative BGE results:")
    print(f"  AUC full:    {auc_full}")
    print(f"  AUC both-ID: {auc_id}")
    print(f"  AUC no-ID:   {auc_noid}")
    print(f"  Delta_ID:    {results.get('native_delta_id')}")
    print(f"  ID gap:      {results.get('native_id_gap')}")

    # Save
    run = open_run("id_masked_eval", {
        "description": "ID stratification for shortcut dependency quantification",
        "test_pairs": len(test_rows),
    }, args.runs_root)
    run.save_result(results)
    print(f"\nSaved to: {run.path}")


if __name__ == "__main__":
    main()
