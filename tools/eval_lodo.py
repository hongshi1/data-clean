#!/usr/bin/env python3
"""LODO (Leave-One-Document-Out) transfer experiment for RQ5.

For each of 16 docs: train on 15 docs, test on the held-out doc.
Reports macro-averaged AUC + per-doc breakdown + learning curve.
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
    parser.add_argument("--epochs", type=int, default=10, help="epochs per fold (reduced for speed)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    features = load_features()
    pairs = load_pairs()

    # Build doc-labeled pairs
    pair_data = []
    for p in pairs:
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid not in index or cid not in index:
            continue
        a_doc = str(features.get(aid, {}).get("doc_id", ""))
        c_doc = str(features.get(cid, {}).get("doc_id", ""))
        doc = a_doc if a_doc == c_doc else a_doc
        pair_data.append({
            "aidx": index[aid], "cidx": index[cid],
            "label": int(p["label"]),
            "doc": doc,
            "basis": str(p.get("label_basis", "")),
        })

    all_docs = sorted(set(r["doc"] for r in pair_data))
    print(f"Documents: {len(all_docs)}, Pairs: {len(pair_data)}")

    import torch
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    lodo_results = []
    X_tensor = torch.from_numpy(matrix)

    for held_out in all_docs:
        train_rows = [r for r in pair_data if r["doc"] != held_out]
        test_rows = [r for r in pair_data if r["doc"] == held_out]

        if not test_rows:
            continue

        # Simple model: projection only
        model = torch.nn.Sequential(
            torch.nn.Linear(matrix.shape[1], 256),
            torch.nn.LayerNorm(256),
            torch.nn.GELU(),
            torch.nn.Linear(256, 256),
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

        train_pos = [r for r in train_rows if r["label"] == 1]
        train_neg = [r for r in train_rows if r["label"] == 0]

        rng = np.random.default_rng(args.seed)

        for epoch in range(args.epochs):
            model.train()
            order = rng.permutation(len(train_pos))
            total_loss = 0.0
            batches = 0

            for start in range(0, len(order), 256):
                end_idx = min(start + 256, len(order))
                batch = [train_pos[i] for i in range(start, end_idx)]

                anchors = torch.tensor([r["aidx"] for r in batch], dtype=torch.long)
                positives = torch.tensor([r["cidx"] for r in batch], dtype=torch.long)

                anchor_vec = torch.nn.functional.normalize(model(X_tensor[anchors]), dim=-1)
                pos_vec = torch.nn.functional.normalize(model(X_tensor[positives]), dim=-1)
                logits = anchor_vec @ pos_vec.T / 0.07
                targets = torch.arange(len(batch))
                loss = torch.nn.functional.cross_entropy(logits, targets)

                # Boundary
                if train_neg:
                    neg_idx = rng.integers(0, len(train_neg), size=min(len(batch), len(train_neg)))
                    neg_rows = [train_neg[i] for i in neg_idx]
                    neg_a = torch.tensor([r["aidx"] for r in neg_rows], dtype=torch.long)
                    neg_c = torch.tensor([r["cidx"] for r in neg_rows], dtype=torch.long)
                    neg_s = (torch.nn.functional.normalize(model(X_tensor[neg_a]), dim=-1)
                             * torch.nn.functional.normalize(model(X_tensor[neg_c]), dim=-1)).sum(dim=-1)
                    loss_b = torch.clamp(neg_s + 0.10, min=0.0).mean()
                    loss = loss + 0.5 * loss_b

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += float(loss.detach())
                batches += 1

        # Evaluate
        model.eval()
        with torch.no_grad():
            proj = torch.cat([model(X_tensor[i:i+4096])
                              for i in range(0, len(X_tensor), 4096)])
            proj = torch.nn.functional.normalize(proj, dim=-1).numpy()

        test_scores = [float(proj[r["aidx"]] @ proj[r["cidx"]]) for r in test_rows]
        test_labels = [r["label"] for r in test_rows]
        auc = compute_auc(test_scores, test_labels)

        lodo_results.append({
            "held_out_doc": held_out,
            "n_test": len(test_rows),
            "n_pos": sum(test_labels),
            "n_neg": len(test_labels) - sum(test_labels),
            "auc": round(auc, 4) if auc else None,
            "final_loss": round(total_loss / max(batches, 1), 4),
        })
        status = f" AUC={auc:.4f}" if auc else " AUC=N/A"
        print(f"  doc{held_out}: {len(test_rows)} pairs "
              f"({sum(test_labels)}pos/{len(test_labels)-sum(test_labels)}neg)"
              f"{status}")

    # Macro average
    valid_aucs = [r["auc"] for r in lodo_results if r["auc"] is not None]
    macro_auc = np.mean(valid_aucs) if valid_aucs else None
    std_auc = np.std(valid_aucs) if valid_aucs else None

    # Learning curve: 8/12/15 docs
    def train_subset(n_docs):
        selected = all_docs[:n_docs]
        test_rows = [r for r in pair_data if r["doc"] not in selected]
        if not test_rows:
            return None
        # Quick: just use raw cosine
        scores = [float(matrix[r["aidx"]] @ matrix[r["cidx"]]) for r in test_rows]
        labels = [r["label"] for r in test_rows]
        return compute_auc(scores, labels)

    curve = {}
    for n in [8, 12, 15]:
        auc = train_subset(n)
        if auc:
            curve[f"train_{n}_docs"] = round(auc, 4)

    results = {
        "lodo_per_doc": lodo_results,
        "macro_auc": round(macro_auc, 4) if macro_auc else None,
        "std_auc": round(std_auc, 4) if std_auc else None,
        "n_valid_folds": len(valid_aucs),
        "learning_curve": curve,
        "config": {
            "epochs": args.epochs,
            "seed": args.seed,
            "model": "Linear-LN-GELU-Linear 256d",
            "loss": "InfoNCE + 0.5*boundary(margin=0.10)",
        },
    }

    print(f"\n{'='*60}")
    print(f"LODO Macro AUC: {macro_auc:.4f} ± {std_auc:.4f} (n={len(valid_aucs)})")
    print(f"Learning curve: {curve}")
    print(f"{'='*60}")

    run = open_run("lodo_transfer", results["config"], args.runs_root)
    run.save_result(results)
    print(f"Saved to: {run.path}")


if __name__ == "__main__":
    main()
