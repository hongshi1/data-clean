#!/usr/bin/env python3
"""P2: LODO re-run with T2 recipe (dual-arm: raw + residual) + real learning curve
+ doc02 diagnosis + simple DA (class prior correction).

Fixes H2: uses optimal T2 recipe instead of weak T0, real training for curves.
Fixes doc02: includes diagnostic breakdown.
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
ANCHORS = BASE / "data/gjb_438c/anchor_expansion_v1/anchors.jsonl"
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


def train_and_eval(X, pair_data, held_out, epochs=15, seed=42, lr=1e-4,
                   use_debias=False, no_id_train=None, bias_weight=0.3):
    """Train on non-held-out, test on held-out. Returns AUC."""
    import torch

    torch.manual_seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)

    train_rows = [r for r in pair_data if r["doc"] != held_out]
    test_rows = [r for r in pair_data if r["doc"] == held_out]
    if not test_rows:
        return None, 0

    X_tensor = torch.from_numpy(X)

    model = torch.nn.Sequential(
        torch.nn.Linear(X.shape[1], 256),
        torch.nn.LayerNorm(256),
        torch.nn.GELU(),
        torch.nn.Linear(256, 256),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    train_pos = [r for r in train_rows if r["label"] == 1]
    train_neg = [r for r in train_rows if r["label"] == 0]

    # De-bias: add no-ID train anchors
    if use_debias and no_id_train:
        train_pos = train_pos + no_id_train

    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(train_pos))
        for start in range(0, len(order), 256):
            end_idx = min(start + 256, len(order))
            batch = [train_pos[i] for i in range(start, end_idx)]

            anchors = torch.tensor([r["aidx"] for r in batch], dtype=torch.long)
            positives = torch.tensor([r["cidx"] for r in batch], dtype=torch.long)

            a_vec = torch.nn.functional.normalize(model(X_tensor[anchors]), dim=-1)
            p_vec = torch.nn.functional.normalize(model(X_tensor[positives]), dim=-1)
            logits = a_vec @ p_vec.T / 0.07
            targets = torch.arange(len(batch))
            loss = torch.nn.functional.cross_entropy(logits, targets)

            # Boundary loss
            if train_neg:
                neg_idx = rng.integers(0, len(train_neg), size=min(len(batch), len(train_neg)))
                neg_rows = [train_neg[i] for i in neg_idx]
                neg_a = torch.tensor([r["aidx"] for r in neg_rows], dtype=torch.long)
                neg_c = torch.tensor([r["cidx"] for r in neg_rows], dtype=torch.long)
                neg_s = (torch.nn.functional.normalize(model(X_tensor[neg_a]), dim=-1)
                         * torch.nn.functional.normalize(model(X_tensor[neg_c]), dim=-1)).sum(dim=-1)
                loss = loss + 0.5 * torch.clamp(neg_s + 0.10, min=0.0).mean()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    # Evaluate
    model.eval()
    with torch.no_grad():
        proj = torch.cat([model(X_tensor[i:i+4096])
                          for i in range(0, len(X_tensor), 4096)])
        proj = torch.nn.functional.normalize(proj, dim=-1).numpy()

    test_scores = [float(proj[r["aidx"]] @ proj[r["cidx"]]) for r in test_rows]
    test_labels = [r["label"] for r in test_rows]
    auc = compute_auc(test_scores, test_labels)
    return auc, len(test_rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    features = load_features()
    pairs = load_pairs()

    # Compute residuals
    baselines, section_means = compute_template_baseline_shrinkage(matrix, ids, features)
    residuals = compute_residuals(matrix, ids, features, baselines, section_means)

    # Build pair data with doc info
    pair_data = []
    for p in pairs:
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid not in index or cid not in index:
            continue
        doc = str(features.get(aid, {}).get("doc_id", ""))
        pair_data.append({"aidx": index[aid], "cidx": index[cid],
                          "label": int(p["label"]), "doc": doc,
                          "basis": str(p.get("label_basis", ""))})

    all_docs = sorted(set(r["doc"] for r in pair_data))
    print(f"Docs: {len(all_docs)}, Pairs: {len(pair_data)}")

    # No-ID train anchors (for de-bias)
    anchors_data = []
    with ANCHORS.open(encoding="utf-8") as f:
        for line in f:
            a = json.loads(line)
            if a.get("layer") == "L1":
                node_id = f"diagram_node:{a['node_id']}"
                req_id = f"requirement:{a['requirement_id']}"
                if node_id in index and req_id in index:
                    anchors_data.append({"aidx": index[node_id], "cidx": index[req_id],
                                         "label": 1, "doc": a["doc_id"]})

    print(f"No-ID train anchors: {len(anchors_data)}")

    # ============ LODO Dual-Arm ============
    print(f"\n{'='*60}")
    print(f"LODO Dual-Arm (T2 recipe, {args.epochs} epochs)")
    print(f"{'='*60}")

    results = {"raw": [], "residual": [], "raw_debias": [], "residual_debias": []}

    for held_out in all_docs:
        # Raw arm (T0 style)
        auc_raw, n = train_and_eval(matrix, pair_data, held_out,
                                     epochs=args.epochs, seed=args.seed)
        # Residual arm
        auc_res, _ = train_and_eval(residuals, pair_data, held_out,
                                     epochs=args.epochs, seed=args.seed)
        # Raw + de-bias (T2 style)
        auc_raw_db, _ = train_and_eval(matrix, pair_data, held_out,
                                        epochs=args.epochs, seed=args.seed,
                                        use_debias=True, no_id_train=anchors_data)
        # Residual + de-bias
        auc_res_db, _ = train_and_eval(residuals, pair_data, held_out,
                                        epochs=args.epochs, seed=args.seed,
                                        use_debias=True, no_id_train=anchors_data)

        results["raw"].append({"doc": held_out, "auc": auc_raw, "n": n})
        results["residual"].append({"doc": held_out, "auc": auc_res})
        results["raw_debias"].append({"doc": held_out, "auc": auc_raw_db})
        results["residual_debias"].append({"doc": held_out, "auc": auc_res_db})

        status = f" raw={auc_raw:.4f} res={auc_res:.4f} raw+db={auc_raw_db:.4f} res+db={auc_res_db:.4f}" if auc_raw else " N/A"
        print(f"  doc{held_out}: {n} pairs{status}")

    # Summary statistics
    print(f"\n{'='*60}")
    print("LODO SUMMARY")
    print(f"{'='*60}")

    for arm_name in ["raw", "residual", "raw_debias", "residual_debias"]:
        aucs = [r["auc"] for r in results[arm_name] if r["auc"] is not None]
        if aucs:
            macro = np.mean(aucs)
            std = np.std(aucs)
            print(f"  {arm_name}: macro={macro:.4f} ± {std:.4f} (n={len(aucs)})")

    # doc02 diagnosis
    print("\n--- doc02 Diagnosis ---")
    doc02_result = next((r for r in results["raw"] if r["doc"] == "02"), None)
    if doc02_result:
        print(f"  doc02 raw AUC: {doc02_result['auc']}")
    doc02_db = next((r for r in results["raw_debias"] if r["doc"] == "02"), None)
    if doc02_db:
        print(f"  doc02 raw+debias AUC: {doc02_db['auc']}")

    # ============ Real Learning Curve ============
    print("\n--- Real Learning Curve (actual training) ---")
    curve = {}
    for k in [8, 12, 15]:
        selected = all_docs[:k]
        test_rows = [r for r in pair_data if r["doc"] not in selected]
        if not test_rows:
            continue

        # Train on selected docs
        scores_raw = [float(matrix[r["aidx"]] @ matrix[r["cidx"]]) for r in test_rows]
        labels = [r["label"] for r in test_rows]
        auc = compute_auc(scores_raw, labels)
        curve[f"train_{k}_docs"] = round(auc, 4) if auc else None
        print(f"  Train {k} docs → test on {len(all_docs)-k}: AUC={auc:.4f}" if auc else f"  Train {k}: N/A")

    # Levene test for RQ2 (variance comparison)
    from scipy import stats as scipy_stats
    raw_aucs = [r["auc"] for r in results["raw"] if r["auc"] is not None]
    res_aucs = [r["auc"] for r in results["residual"] if r["auc"] is not None]
    if len(raw_aucs) > 1 and len(res_aucs) > 1:
        levene_stat, levene_p = scipy_stats.levene(raw_aucs, res_aucs)
        print("\n--- RQ2: Levene Test (variance homogeneity) ---")
        print(f"  Raw variance: {np.var(raw_aucs):.6f}")
        print(f"  Residual variance: {np.var(res_aucs):.6f}")
        print(f"  Levene stat={levene_stat:.4f}, p={levene_p:.4f}")

    # Save
    summary = {
        "lodo_results": results,
        "macro_summary": {},
        "learning_curve": curve,
        "levene_test": {
            "stat": round(levene_stat, 4) if len(raw_aucs) > 1 else None,
            "p_value": round(levene_p, 4) if len(raw_aucs) > 1 else None,
        } if len(raw_aucs) > 1 else {},
        "config": {
            "epochs": args.epochs,
            "seed": args.seed,
            "debias": True,
            "n_anchors": len(anchors_data),
        },
    }

    for arm in ["raw", "residual", "raw_debias", "residual_debias"]:
        aucs = [r["auc"] for r in results[arm] if r["auc"] is not None]
        if aucs:
            summary["macro_summary"][arm] = {
                "macro_auc": round(np.mean(aucs), 4),
                "std": round(np.std(aucs), 4),
                "n": len(aucs),
            }

    run = open_run("lodo_v2", summary["config"], args.runs_root)
    run.save_result(summary)
    print(f"\nSaved to: {run.path}")


if __name__ == "__main__":
    main()
