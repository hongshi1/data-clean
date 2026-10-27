#!/usr/bin/env python3
"""P4b: Cross-modal G2 + residual replication experiment.

Evaluates whether residual representation improves cross-modal retrieval
(the scenario where 52号 predicted maximum residual gain).
Uses the crossmodal Procrustes framework with both raw and residual arms.
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
RUNS_ROOT = BASE / "data/gjb_438c/runs"


def load_snapshot():
    with np.load(SNAPSHOT, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(v) for v in data["ids"].tolist()]
    return matrix, ids, {oid: i for i, oid in enumerate(ids)}


def load_features():
    with FEATURES.open(encoding="utf-8") as f:
        return {json.loads(line)["occurrence_id"]: json.loads(line)
                for line in f if line.strip()}


def compute_template_baseline_shrinkage(matrix, ids, features, alpha=5.0):
    groups: dict[tuple, list[int]] = {}
    for i, oid in enumerate(ids):
        feat = features.get(oid, {})
        kind = str(feat.get("source_kind", "unknown"))
        section = str(feat.get("section", ""))
        doc = str(feat.get("doc_id", ""))
        groups.setdefault((kind, section, doc), []).append(i)

    doc_means: dict[tuple, np.ndarray] = {}
    for key, indices in groups.items():
        if len(indices) >= 2:
            doc_means[key] = matrix[indices].mean(axis=0)

    section_means: dict[tuple, np.ndarray] = {}
    section_counts: dict[tuple, int] = {}
    for (kind, section, doc), mean_vec in doc_means.items():
        key = (kind, section)
        if key not in section_means:
            section_means[key] = np.zeros_like(mean_vec)
            section_counts[key] = 0
        section_means[key] += mean_vec
        section_counts[key] += 1
    for key in section_means:
        section_means[key] /= section_counts[key]

    all_docs = sorted(set(k[2] for k in doc_means))
    baselines: dict[tuple, np.ndarray] = {}
    for (kind, section, doc), mean_vec in doc_means.items():
        # Leave-one-doc-out, keyed by (kind, section, doc) so each doc keeps
        # its own mu instead of being overwritten by later docs
        others = [doc_means[(kind, section, d)] for d in all_docs
                  if (kind, section, d) in doc_means and d != doc]
        if not others:
            mu = section_means.get((kind, section), np.zeros_like(mean_vec))
        else:
            lodo_mean = np.mean(others, axis=0)
            n = len(others)
            mu = (n / (n + alpha)) * lodo_mean + (alpha / (n + alpha)) * section_means.get((kind, section), np.zeros_like(mean_vec))
        baselines[(kind, section, doc)] = mu
    return baselines, section_means


def compute_residuals(matrix, ids, features, baselines, section_means):
    residuals = np.zeros_like(matrix)
    for i, oid in enumerate(ids):
        feat = features.get(oid, {})
        kind = str(feat.get("source_kind", "unknown"))
        section = str(feat.get("section", ""))
        doc = str(feat.get("doc_id", ""))
        mu = baselines.get((kind, section, doc))
        if mu is None:
            # No LODO baseline for this doc's cell → fallback to section mean
            mu = section_means.get((kind, section))
        residuals[i] = matrix[i] - mu if mu is not None else matrix[i]
    norms = np.maximum(np.linalg.norm(residuals, axis=1, keepdims=True), 1e-8)
    return residuals / norms


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

    # Compute residuals
    baselines, section_means = compute_template_baseline_shrinkage(matrix, ids, features)
    residuals = compute_residuals(matrix, ids, features, baselines, section_means)

    # Build cross-modal pairs: text claims ↔ diagram nodes
    text_ids = [oid for oid in ids if oid.startswith("claim:")]
    node_ids = [oid for oid in ids if oid.startswith("diagram_node:")]
    row_ids = [oid for oid in ids if oid.startswith("table_row:")]

    print(f"Objects: {len(text_ids)} claims, {len(node_ids)} diagram nodes, {len(row_ids)} table rows")

    # Build positive pairs: same doc, text and node in nearby sections
    # Use L1 title-bridge anchors as gold
    anchors = []
    anchor_path = BASE / "data/gjb_438c/anchor_expansion_v1/anchors.jsonl"
    with anchor_path.open(encoding="utf-8") as f:
        for line in f:
            a = json.loads(line)
            if a.get("layer") == "L1":
                node_id = f"diagram_node:{a['node_id']}"
                req_id = f"requirement:{a['requirement_id']}"
                if node_id in index and req_id in index:
                    anchors.append((index[node_id], index[req_id], a["doc_id"]))

    print(f"L1 anchor pairs (gold): {len(anchors)}")

    if not anchors:
        print("No anchors — cannot build cross-modal evaluation")
        return

    # Build evaluation: for each anchor pair, score against random negatives
    all_node_indices = [index[oid] for oid in node_ids if oid in index]

    results = {}
    rng = np.random.default_rng(42)

    for rep_name, rep_matrix in [("raw", matrix), ("residual", residuals),
                                  ("fusion", (matrix + residuals) / 2)]:
        scores = []
        labels = []

        for node_idx, req_idx, doc in anchors:
            # Positive: actual pair
            scores.append(float(rep_matrix[node_idx] @ rep_matrix[req_idx]))
            labels.append(1)

            # Negative: random node from same or different doc
            neg_idx = all_node_indices[rng.integers(0, len(all_node_indices))]
            if neg_idx != node_idx:
                scores.append(float(rep_matrix[node_idx] @ rep_matrix[neg_idx]))
                labels.append(0)

        auc = compute_auc(scores, labels)
        results[rep_name] = {
            "auc": round(auc, 4) if auc else None,
            "n": len(scores),
            "pos": sum(labels),
            "neg": len(labels) - sum(labels),
        }
        print(f"\n{rep_name} cross-modal AUC: {auc}")

    # Also evaluate claim ↔ table_row cross-modal
    # Build positive pairs: same doc, claim in same section as table row
    cross_pairs = []
    for i, oid in enumerate(ids):
        if not oid.startswith("claim:"):
            continue
        feat = features.get(oid, {})
        doc = str(feat.get("doc_id", ""))
        section = str(feat.get("section", ""))
        if not doc or not section:
            continue

        # Find table rows in same doc+section
        for j, oid2 in enumerate(ids):
            if not oid2.startswith("table_row:") or i == j:
                continue
            feat2 = features.get(oid2, {})
            if str(feat2.get("doc_id", "")) == doc and str(feat2.get("section", "")) == section:
                cross_pairs.append((i, j, doc))
                break  # one per claim

    if cross_pairs:
        print(f"\nClaim ↔ Table Row pairs: {len(cross_pairs)}")

        for rep_name, rep_matrix in [("raw", matrix), ("residual", residuals)]:
            scores = []
            labels = []
            all_row_indices = [index[oid] for oid in row_ids if oid in index]

            for ci, ri, doc in cross_pairs:
                scores.append(float(rep_matrix[ci] @ rep_matrix[ri]))
                labels.append(1)
                neg_ri = all_row_indices[rng.integers(0, len(all_row_indices))]
                scores.append(float(rep_matrix[ci] @ rep_matrix[neg_ri]))
                labels.append(0)

            auc = compute_auc(scores, labels)
            results[f"claim_row_{rep_name}"] = {
                "auc": round(auc, 4) if auc else None,
                "n": len(scores),
            }
            print(f"  {rep_name} claim↔row AUC: {auc}")

    # Summary
    print(f"\n{'='*60}")
    print("CROSS-MODAL RESIDUAL REPLICATION RESULTS")
    print(f"{'='*60}")
    for name, r in results.items():
        print(f"  {name}: AUC={r['auc']}")

    # Save
    run = open_run("crossmodal_residual", {
        "n_anchors": len(anchors),
        "n_cross_pairs": len(cross_pairs) if cross_pairs else 0,
    }, args.runs_root)
    run.save_result(results)
    print(f"\nSaved to: {run.path}")


if __name__ == "__main__":
    main()
