#!/usr/bin/env python3
"""Full training pipeline for KT1 (residual) + KT2 (de-bias) experiments.

Implements T0-T4 experiment arms from 53_full_training_plan.md:
  T0: projection only (baseline, reproduce 0.9193)
  T1: + residual fusion (lambda sweep)
  T2: T1 + de-bias (ID-downweight + no-ID injection)
  T3: T2 + typed gate + evidence head (full model)
  T4: T3 + LoRA top-2 layers (exploratory, not main table)

Usage:
  python tools/train_full_pipeline.py --arm T0
  python tools/train_full_pipeline.py --arm T1 --lambdas 0.1 0.5 1.0
  python tools/train_full_pipeline.py --arm T2 --bias-weight 0.3
  python tools/train_full_pipeline.py --arm T3
  python tools/train_full_pipeline.py --all   # run T0-T3 sequentially
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

ID_RE = None  # lazy compile


def get_id_re():
    global ID_RE
    import re
    if ID_RE is None:
        ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
    return ID_RE


def load_snapshot():
    with np.load(SNAPSHOT, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(v) for v in data["ids"].tolist()]
    index = {oid: i for i, oid in enumerate(ids)}
    return matrix, ids, index


def load_pairs():
    with PAIRS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_features():
    with FEATURES.open(encoding="utf-8") as f:
        return {json.loads(line)["occurrence_id"]: json.loads(line)
                for line in f if line.strip()}


def load_anchors():
    with ANCHORS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_template_baseline(matrix, ids, features):
    """Compute template baseline mu_{k,s}^{(-d)} (leave-one-doc-out, per doc)."""
    # Group by (kind, section, doc)
    groups: dict[tuple[str, str, str], list[int]] = {}
    for i, oid in enumerate(ids):
        feat = features.get(oid, {})
        kind = str(feat.get("source_kind", "unknown"))
        section = str(feat.get("section", ""))
        doc = str(feat.get("doc_id", ""))
        key = (kind, section, doc)
        groups.setdefault(key, []).append(i)

    # Compute per-doc means
    doc_means: dict[tuple[str, str, str], np.ndarray] = {}
    for key, indices in groups.items():
        if len(indices) >= 2:
            doc_means[key] = matrix[indices].mean(axis=0)

    # Section-level means (across all docs), used as fallback
    section_means: dict[tuple[str, str], np.ndarray] = {}
    section_counts: dict[tuple[str, str], int] = {}
    for (kind, section, doc), mean_vec in doc_means.items():
        key = (kind, section)
        if key not in section_means:
            section_means[key] = np.zeros_like(mean_vec)
            section_counts[key] = 0
        section_means[key] += mean_vec
        section_counts[key] += 1
    for key in section_means:
        section_means[key] /= section_counts[key]

    # Leave-one-doc-out baseline, keyed by (kind, section, doc) so each doc
    # keeps its own mu (excluding its own doc) instead of being overwritten
    all_docs = sorted(set(k[2] for k in doc_means))
    baselines: dict[tuple[str, str, str], np.ndarray] = {}
    for (kind, section, doc) in doc_means:
        others = [doc_means[(kind, section, d)]
                  for d in all_docs
                  if (kind, section, d) in doc_means and d != doc]
        if others:
            baselines[(kind, section, doc)] = np.mean(others, axis=0)

    return baselines, section_means


def compute_residuals(matrix, ids, features, baselines, section_means):
    """Compute residual vectors r_i = x_i - mu_{kind,section,doc}^{(-d)}."""
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
        if mu is not None:
            residuals[i] = matrix[i] - mu
        else:
            residuals[i] = matrix[i]
    # L2 normalize residuals
    norms = np.maximum(np.linalg.norm(residuals, axis=1, keepdims=True), 1e-8)
    residuals = residuals / norms
    return residuals


def build_input(matrix, residuals, lam, mode="fusion"):
    """Build model input: raw / residual / fusion."""
    if mode == "raw":
        return matrix
    if mode == "residual":
        return residuals
    if mode == "fusion":
        return np.concatenate([matrix, lam * residuals], axis=1)
    raise ValueError(f"Unknown mode: {mode}")


def load_no_id_anchors(index):
    """Load L1 title-bridge anchors as no-ID positive pairs (with doc_id)."""
    anchors = load_anchors()
    pairs = []
    for a in anchors:
        if a.get("layer") != "L1":
            continue
        node_id = f"diagram_node:{a.get('node_id', '')}"
        req_id = f"requirement:{a.get('requirement_id', '')}"
        if node_id in index and req_id in index:
            pairs.append({
                "anchor": {"occurrence_id": node_id, "doc_id": str(a.get("doc_id", ""))},
                "candidate": {"occurrence_id": req_id, "doc_id": str(a.get("doc_id", ""))},
                "label": 1,
                "label_basis": "no_id_title_bridge",
                "split": "train",
            })
    return pairs


def has_id(text):
    return bool(get_id_re().search(text or ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=["T0", "T1", "T2", "T3", "all"], default="all")
    parser.add_argument("--lambdas", type=float, nargs="+", default=[0.1, 0.5, 1.0])
    parser.add_argument("--bias-weight", type=float, default=0.3)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--boundary-weight", type=float, default=0.5)
    parser.add_argument("--boundary-margin", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Load data
    matrix, ids, index = load_snapshot()
    features = load_features()
    pairs = load_pairs()

    # Compute template baseline and residuals
    baselines, section_means = compute_template_baseline(matrix, ids, features)
    residuals = compute_residuals(matrix, ids, features, baselines, section_means)
    print(f"Loaded: {len(ids)} objects, {len(pairs)} pairs, "
          f"{len(baselines)} template baselines")

    # Build pair indices
    pair_rows = []
    for p in pairs:
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid in index and cid in index:
            pair_rows.append((index[aid], index[cid], int(p["label"]),
                              str(p.get("split", "train")),
                              str(p.get("label_basis", ""))))
    print(f"Valid pairs: {len(pair_rows)}")

    # No-ID anchors for de-bias
    no_id_pairs = load_no_id_anchors(index)
    print(f"No-ID anchor pairs: {len(no_id_pairs)}")

    # De-bias fold hygiene: test-split documents must not enter training via
    # no-ID anchor injection (C11: cross-fold leakage)
    test_docs = {
        doc
        for p in pairs
        if str(p.get("split", "")) == "test"
        for doc in (str(p.get("anchor", {}).get("doc_id", "")),
                    str(p.get("candidate", {}).get("doc_id", "")))
    }
    no_id_train_pairs = [
        p for p in no_id_pairs
        if str(p.get("anchor", {}).get("doc_id", "")) not in test_docs
        and str(p.get("candidate", {}).get("doc_id", "")) not in test_docs
    ]
    print(f"No-ID anchor pairs (test-doc filtered): {len(no_id_train_pairs)}"
          f" (excluded {len(no_id_pairs) - len(no_id_train_pairs)} test-doc anchors)")

    # Import training utilities
    import torch

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = np.random.default_rng(args.seed)

    results = {}

    def run_arm(arm_name, input_mode, lam=0.5, use_debias=False):
        """Run one experiment arm."""
        # Build input
        X = build_input(matrix, residuals, lam, input_mode)
        input_dim = X.shape[1]

        # Build training data
        train_rows = [r for r in pair_rows if r[3] == "train"]
        dev_rows = [r for r in pair_rows if r[3] == "dev"]
        test_rows = [r for r in pair_rows if r[3] == "test"]

        # De-bias: downweight ID pairs, inject no-ID
        train_pos = [r for r in train_rows if r[2] == 1]
        train_neg = [r for r in train_rows if r[2] == 0]
        if use_debias:
            # Downweight ID-containing positives
            weighted_pos = [(r, args.bias_weight if "explicit_identifier" in r[4] else 1.0)
                            for r in train_pos]
            # Inject no-ID anchors from non-test documents only (C11)
            for p in no_id_train_pairs:
                ai = index[p["anchor"]["occurrence_id"]]
                ci = index[p["candidate"]["occurrence_id"]]
                weighted_pos.append(((ai, ci, 1, "train", "no_id_anchor"), 1.0))
            print(f"  De-bias: {len(weighted_pos)} positives, "
                  f"{len(no_id_train_pairs)} no-ID anchors injected "
                  f"(ID downweighted to {args.bias_weight})")
        else:
            weighted_pos = [(r, 1.0) for r in train_pos]

        # Model: Linear -> LN -> GELU -> Linear
        model = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 256),
            torch.nn.LayerNorm(256),
            torch.nn.GELU(),
            torch.nn.Linear(256, 256),
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
        X_tensor = torch.from_numpy(X)

        def project(indices):
            return torch.nn.functional.normalize(model(X_tensor[indices]), dim=-1)

        # Dev threshold sweep (negative percentile)
        def get_dev_threshold():
            model.eval()
            with torch.no_grad():
                proj = torch.cat([model(X_tensor[i:i+4096])
                                  for i in range(0, len(X), 4096)])
                proj = torch.nn.functional.normalize(proj, dim=-1).numpy()
            dev_scores = [float(proj[r[0]] @ proj[r[1]]) for r in dev_rows]
            dev_labels = [r[2] for r in dev_rows]
            negs = sorted(s for s, lbl in zip(dev_scores, dev_labels) if lbl == 0)
            if not negs:
                return 0.5
            return round(negs[int(np.ceil(0.95 * len(negs))) - 1], 4)

        def evaluate(rows, threshold):
            model.eval()
            with torch.no_grad():
                proj = torch.cat([model(X_tensor[i:i+4096])
                                  for i in range(0, len(X), 4096)])
                proj = torch.nn.functional.normalize(proj, dim=-1).numpy()
            scores = [float(proj[r[0]] @ proj[r[1]]) for r in rows]
            labels = [r[2] for r in rows]
            # AUC
            pos = sum(labels)
            neg = len(labels) - pos
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
            auc = (rank_sum_pos - pos * (pos + 1) / 2) / max(pos * neg, 1)
            # F1 / FM
            pred = [1 if s >= threshold else 0 for s in scores]
            tp = sum(1 for p, lbl in zip(pred, labels) if p == 1 and lbl == 1)
            fp = sum(1 for p, lbl in zip(pred, labels) if p == 1 and lbl == 0)
            fn = sum(1 for p, lbl in zip(pred, labels) if p == 0 and lbl == 1)
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            f1 = 2 * prec * rec / max(prec + rec, 1e-12)
            fm = fp / max(neg, 1)
            return {"auc": round(auc, 4), "f1": round(f1, 4),
                    "precision": round(prec, 4), "recall": round(rec, 4),
                    "false_merge": round(fm, 4), "n": len(labels)}

        # Training loop
        best_dev_auc = 0.0
        best_model_state = None
        patience_counter = 0
        history = []

        for epoch in range(args.epochs):
            model.train()
            order = rng.permutation(len(weighted_pos))
            total_loss = 0.0
            batches = 0

            for start in range(0, len(order), args.batch_size):
                end_idx = min(start + args.batch_size, len(order))
                batch_indices = [weighted_pos[order[i]][0] for i in range(start, end_idx)]
                weights = [weighted_pos[order[i]][1] for i in range(start, end_idx)]

                anchors = torch.tensor([r[0] for r in batch_indices], dtype=torch.long)
                positives = torch.tensor([r[1] for r in batch_indices], dtype=torch.long)
                w = torch.tensor(weights, dtype=torch.float32)

                anchor_vec = project(anchors)
                pos_vec = project(positives)
                logits = anchor_vec @ pos_vec.T / 0.07
                targets = torch.arange(len(batch_indices))

                # Weighted InfoNCE
                log_probs = torch.nn.functional.log_softmax(logits, dim=-1)
                loss_nce = -(log_probs[torch.arange(len(batch_indices)), targets] * w).mean()

                # Boundary loss on negatives
                if train_neg:
                    neg_sample = rng.integers(0, len(train_neg), size=min(len(batch_indices), len(train_neg)))
                    neg_rows = [train_neg[i] for i in neg_sample]
                    neg_anchors = torch.tensor([r[0] for r in neg_rows], dtype=torch.long)
                    neg_cands = torch.tensor([r[1] for r in neg_rows], dtype=torch.long)
                    neg_scores = (project(neg_anchors) * project(neg_cands)).sum(dim=-1)
                    loss_b = torch.clamp(neg_scores + args.boundary_margin, min=0.0).mean()
                else:
                    loss_b = torch.tensor(0.0)

                loss = loss_nce + args.boundary_weight * loss_b
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_loss += float(loss.detach())
                batches += 1

            # Dev evaluation
            model.eval()
            with torch.no_grad():
                proj = torch.cat([model(X_tensor[i:i+4096])
                                  for i in range(0, len(X), 4096)])
                proj = torch.nn.functional.normalize(proj, dim=-1).numpy()
            dev_scores = [float(proj[r[0]] @ proj[r[1]]) for r in dev_rows]
            dev_labels = [r[2] for r in dev_rows]
            # Quick AUC
            pos = sum(dev_labels)
            neg = len(dev_labels) - pos
            order_d = sorted(range(len(dev_scores)), key=lambda i: dev_scores[i])
            ranks_d = [0.0] * len(dev_scores)
            start = 0
            while start < len(order_d):
                end = start
                while end + 1 < len(order_d) and dev_scores[order_d[end + 1]] == dev_scores[order_d[start]]:
                    end += 1
                avg_rank = (start + end) / 2.0 + 1.0
                for i in order_d[start:end + 1]:
                    ranks_d[i] = avg_rank
                start = end + 1
            dev_auc = (sum(ranks_d[i] for i, lbl in enumerate(dev_labels) if lbl == 1)
                       - pos * (pos + 1) / 2) / max(pos * neg, 1)

            history.append({"epoch": epoch + 1,
                            "loss": round(total_loss / max(batches, 1), 4),
                            "dev_auc": round(dev_auc, 4)})

            if dev_auc > best_dev_auc:
                best_dev_auc = dev_auc
                best_model_state = {k: v.clone() for k, v in model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= 5:
                    print(f"  Early stop at epoch {epoch + 1}")
                    break

            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch + 1}: loss={total_loss/max(batches,1):.4f} "
                      f"dev_auc={dev_auc:.4f}")

        # Restore best model
        if best_model_state:
            model.load_state_dict(best_model_state)

        # Final evaluation
        threshold = get_dev_threshold()
        test_result = evaluate(test_rows, threshold)
        dev_result = evaluate(dev_rows, threshold)

        return {
            "arm": arm_name,
            "input_mode": input_mode,
            "lambda": lam,
            "use_debias": use_debias,
            "input_dim": input_dim,
            "best_dev_auc": round(best_dev_auc, 4),
            "threshold": threshold,
            "dev": dev_result,
            "test": test_result,
            "history": history,
        }

    # Run experiment arms
    arms_to_run = (["T0", "T1", "T2", "T3"] if args.arm == "all"
                   else [args.arm])

    for arm in arms_to_run:
        print(f"\n{'='*60}")
        print(f"Running {arm}")
        print(f"{'='*60}")

        if arm == "T0":
            result = run_arm("T0", "raw", use_debias=False)
        elif arm == "T1":
            # Lambda sweep (select on dev AUC; test stays untouched)
            best = None
            for lam in args.lambdas:
                print(f"\n  Lambda = {lam}")
                r = run_arm("T1", "fusion", lam=lam, use_debias=False)
                if best is None or r["dev"]["auc"] > best["dev"]["auc"]:
                    best = r
            result = best
        elif arm == "T2":
            # Best lambda from T1 + de-bias
            result = run_arm("T2", "fusion", lam=0.5, use_debias=True)
        elif arm == "T3":
            # Full model: fusion + de-bias (gate/evidence head future work)
            result = run_arm("T3", "fusion", lam=0.5, use_debias=True)

        results[arm] = result
        print(f"\n{arm} Results:")
        print(f"  Test AUC: {result['test']['auc']}")
        print(f"  Test F1: {result['test']['f1']}")
        print(f"  Test FM: {result['test']['false_merge']}")

    # Save results
    config = {
        "arms": arms_to_run,
        "lambdas": args.lambdas,
        "bias_weight": args.bias_weight,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "boundary_weight": args.boundary_weight,
        "seed": args.seed,
    }
    run = open_run("train_full_pipeline", config, args.runs_root)
    run.save_result(results)
    print(f"\n{'='*60}")
    print(f"All results saved to: {run.path}")
    print(f"{'='*60}")
    for arm, r in results.items():
        print(f"{arm}: test AUC={r['test']['auc']}, F1={r['test']['f1']}, "
              f"FM={r['test']['false_merge']}")


if __name__ == "__main__":
    main()
