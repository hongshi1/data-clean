#!/usr/bin/env python3
"""P4a: Harder task — same-entity different-value conflict detection.

The current silver task (same-ID vs different-ID) is trivially separable.
This defines a harder task: pairs that share an entity (same section/similar
context) but have DIFFERENT parameter values — the actual consistency checking
task that direction B needs.

Uses Claim-level data from structured_corpus to find value conflicts.
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
FEATURES = BASE / "data/gjb_438c/feature_snapshot_v1/features.jsonl"
CLAIMS = BASE / "data/gjb_438c/structured_corpus_v1/claims.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

import re
ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
NUM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(ms|s|秒|分钟|KB|MB|GB|TB|%|次|个|路|字节)?")


def load_snapshot():
    with np.load(SNAPSHOT, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(v) for v in data["ids"].tolist()]
    return matrix, ids, {oid: i for i, oid in enumerate(ids)}


def load_features():
    with FEATURES.open(encoding="utf-8") as f:
        return {json.loads(line)["occurrence_id"]: json.loads(line)
                for line in f if line.strip()}


def load_claims():
    with CLAIMS.open(encoding="utf-8") as f:
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


def find_value_conflicts(claims, features):
    """Find pairs of claims that describe the same parameter but have different values."""
    # Group claims by (doc_id, predicate/param) — same parameter
    param_groups = {}
    for c in claims:
        feats = c.get("features", {})
        param = ""
        # Try to extract parameter from features
        for q in feats.get("quantities", []):
            # Use surrounding text as parameter hint
            param = str(q.get("raw", ""))[:30]
            break
        if not param:
            # Use claim text first 20 chars as key
            param = c.get("raw_text", "")[:20]

        doc = str(c.get("doc_id", ""))

        key = (doc, param[:20])  # loose grouping
        param_groups.setdefault(key, []).append(c)

    # Find conflicts: same key, different values
    conflicts = []
    for key, group in param_groups.items():
        if len(group) < 2:
            continue

        # Extract numeric values from each claim
        values = []
        for c in group:
            text = c.get("raw_text", "")
            nums = NUM_RE.findall(text)
            if nums:
                val = float(nums[0][0])
                unit = nums[0][1] or ""
                values.append((c, val, unit))

        if len(values) < 2:
            continue

        # Check for value differences
        base_val = values[0][1]
        base_unit = values[0][2]
        for c, val, unit in values[1:]:
            if abs(val - base_val) > 0.01 and (unit == base_unit or not unit or not base_unit):
                # Different value for same parameter → potential conflict
                conflicts.append({
                    "claim_a": values[0][0],
                    "claim_b": c,
                    "param_hint": key[1],
                    "val_a": base_val, "unit_a": base_unit,
                    "val_b": val, "unit_b": unit,
                    "doc": key[0],
                })

    return conflicts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    features = load_features()
    claims = load_claims()

    print(f"Loaded: {len(ids)} objects, {len(claims)} claims")

    # Find value conflicts
    print("\n--- Finding value conflicts ---")
    conflicts = find_value_conflicts(claims, features)
    print(f"Potential value conflicts: {len(conflicts)}")

    # Show examples
    for c in conflicts[:5]:
        print(f"  doc{c['doc']} [{c['param_hint']}]: "
              f"{c['val_a']}{c['unit_a']} vs {c['val_b']}{c['unit_b']}")

    # Build evaluation pairs: conflict vs consistent
    # Positive (conflict): different values for same parameter
    # Negative (consistent): same values for same parameter

    # Build all pairs within param groups
    eval_pairs = []
    for key, group in param_groups.items() if (param_groups := {}) else []:
        pass

    # Rebuild with different approach: pair claims within same doc+section
    section_groups = {}
    for c in claims:
        doc = str(c.get("doc_id", ""))
        section = str(c.get("section", ""))
        key = (doc, section)
        section_groups.setdefault(key, []).append(c)

    eval_pairs = []
    for key, group in section_groups.items():
        if len(group) < 2:
            continue
        # Pair all claims within same section
        for i in range(len(group)):
            for j in range(i + 1, min(i + 5, len(group))):
                a, b = group[i], group[j]

                # Check if they have different values
                a_text = a.get("raw_text", "")
                b_text = b.get("raw_text", "")
                a_nums = NUM_RE.findall(a_text)
                b_nums = NUM_RE.findall(b_text)

                if a_nums and b_nums:
                    a_val = float(a_nums[0][0])
                    b_val = float(b_nums[0][0])
                    a_unit = a_nums[0][1] or ""
                    b_unit = b_nums[0][1] or ""

                    if abs(a_val - b_val) > 0.01:
                        # Different values → potential conflict
                        eval_pairs.append({
                            "a_id": a.get("claim_id", ""),
                            "b_id": b.get("claim_id", ""),
                            "a_text": a_text[:60],
                            "b_text": b_text[:60],
                            "val_a": a_val, "val_b": b_val,
                            "unit_a": a_unit, "unit_b": b_unit,
                            "label": 1,  # conflict
                            "doc": key[0], "section": key[1],
                        })
                    else:
                        # Same values → consistent
                        eval_pairs.append({
                            "a_id": a.get("claim_id", ""),
                            "b_id": b.get("claim_id", ""),
                            "a_text": a_text[:60],
                            "b_text": b_text[:60],
                            "val_a": a_val, "val_b": b_val,
                            "unit_a": a_unit, "unit_b": b_unit,
                            "label": 0,  # consistent
                            "doc": key[0], "section": key[1],
                        })

    print(f"\nEvaluation pairs (same-section value comparison): {len(eval_pairs)}")
    print(f"  Conflicts (different values): {sum(1 for p in eval_pairs if p['label']==1)}")
    print(f"  Consistent (same values): {sum(1 for p in eval_pairs if p['label']==0)}")

    # Evaluate with embedding similarity
    if eval_pairs:
        scores = []
        labels = []
        valid = 0
        for p in eval_pairs:
            a_idx = index.get(p["a_id"])
            b_idx = index.get(p["b_id"])
            if a_idx is not None and b_idx is not None:
                sim = float(matrix[a_idx] @ matrix[b_idx])
                scores.append(sim)
                labels.append(p["label"])
                valid += 1

        if valid > 10:
            auc = compute_auc(scores, labels)
            print("\nEmbedding similarity for conflict detection:")
            print(f"  Valid pairs: {valid}")
            print(f"  AUC: {auc}")
            print(f"  → {'Task is discriminative' if auc and 0.4 < auc < 0.9 else 'Task may be too easy or too hard'}")

            # Conflict examples with embedding scores
            conflict_scores = [s for s, lbl in zip(scores, labels) if lbl == 1]
            consistent_scores = [s for s, lbl in zip(scores, labels) if lbl == 0]
            print(f"  Conflict sim: mean={np.mean(conflict_scores):.4f}")
            print(f"  Consistent sim: mean={np.mean(consistent_scores):.4f}")
            print(f"  Separation: {np.mean(consistent_scores) - np.mean(conflict_scores):.4f}")

            results = {
                "n_pairs": valid,
                "n_conflicts": sum(labels),
                "n_consistent": valid - sum(labels),
                "auc": round(auc, 4) if auc else None,
                "conflict_sim_mean": round(np.mean(conflict_scores), 4),
                "consistent_sim_mean": round(np.mean(consistent_scores), 4),
                "task_difficulty": "discriminative" if auc and 0.4 < auc < 0.9 else "trivial_or_impossible",
            }
        else:
            print("  Not enough valid pairs for evaluation")
            results = {"error": "insufficient_pairs", "n_valid": valid}
    else:
        results = {"error": "no_pairs"}

    run = open_run("harder_task_eval", {"description": "Same-entity different-value conflict detection"}, args.runs_root)
    run.save_result(results)
    print(f"\nSaved to: {run.path}")


if __name__ == "__main__":
    main()
