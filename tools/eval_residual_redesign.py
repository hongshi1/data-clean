#!/usr/bin/env python3
"""P1: Anchor test-set construction + residual redesign.

R0: No-ID test set from L1 anchors only (D2 adjudication: L2 excluded).
R1: Template baseline with shrinkage estimation (D1 fixed: LODO keyed by doc).
R2: Pure residual arm + whitening + regularization.
R3: Evaluate on no-ID test + LODO + cross-modal.

D2 adjudication (2026-10-27): L2 fuzzy anchors are NOT usable as positives
(20-sample stratified audit: ~15-30% true positives, bge_cos arm ~0-20%;
calibrated P=0.9505 was measured against random easy negatives) and NOT usable
as verified negatives (lexical arm contains true title-with-ID-suffix matches).
Decision: option C — L2 excluded entirely. Positives = L1 title-bridge pairs
(no shared ID, unambiguous title). Negatives = deterministic L1 mismatches
(same doc, node L1-anchored to req A paired with title-distinct L1-anchored
req B, no substring title relation, no shared ID).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

SNAPSHOT = BASE / "data/gjb_438c/feature_snapshot_v1/vectors.npz"
PAIRS = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
FEATURES = BASE / "data/gjb_438c/feature_snapshot_v1/features.jsonl"
ANCHORS = BASE / "data/gjb_438c/anchor_expansion_v1/anchors.jsonl"
REQS_CORPUS = BASE / "data/gjb_438c/structured_corpus_v1/requirements.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

import re
ID_RE = re.compile(r"\b[A-Z]{3,}(?:-[A-Z0-9]{2,}){2,}\b")
WS_RE = re.compile(r"\s+")


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


def load_anchors():
    with ANCHORS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_template_baseline_shrinkage(matrix, ids, features, alpha=5.0):
    """Template baseline with shrinkage: mu_cell = n/(n+alpha)*mean + alpha/(n+alpha)*mu_section."""
    groups: dict[tuple, list[int]] = {}
    for i, oid in enumerate(ids):
        feat = features.get(oid, {})
        kind = str(feat.get("source_kind", "unknown"))
        section = str(feat.get("section", ""))
        doc = str(feat.get("doc_id", ""))
        groups.setdefault((kind, section, doc), []).append(i)

    # Per-doc means
    doc_means: dict[tuple, np.ndarray] = {}
    for key, indices in groups.items():
        if len(indices) >= 2:
            doc_means[key] = matrix[indices].mean(axis=0)

    # Section-level means (across all docs)
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

    # Leave-one-doc-out with shrinkage
    all_docs = sorted(set(k[2] for k in doc_means))
    baselines: dict[tuple, np.ndarray] = {}

    # Count per (kind, section) how many docs have data
    doc_count_per_cell: dict[tuple, int] = {}
    for (kind, section, doc) in doc_means:
        key = (kind, section)
        doc_count_per_cell[key] = doc_count_per_cell.get(key, 0) + 1

    for (kind, section, doc), mean_vec in doc_means.items():
        # Leave-one-doc-out, keyed by (kind, section, doc) so each doc keeps
        # its own mu instead of being overwritten by later docs
        others = [doc_means[(kind, section, d)] for d in all_docs
                  if (kind, section, d) in doc_means and d != doc]
        if not others:
            # No other doc → use section mean
            mu = section_means.get((kind, section), np.zeros_like(mean_vec))
        else:
            lodo_mean = np.mean(others, axis=0)
            n = len(others)
            # Shrinkage: n/(n+alpha) * lodo_mean + alpha/(n+alpha) * section_mean
            mu = (n / (n + alpha)) * lodo_mean + (alpha / (n + alpha)) * section_means.get((kind, section), np.zeros_like(mean_vec))
        baselines[(kind, section, doc)] = mu

    return baselines, section_means, doc_count_per_cell


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


def load_req_titles():
    """Title maps from requirements corpus.

    A requirement entity may appear in multiple rows (3.1 summary + 3.2 detail),
    so titles are aggregated per (doc, rid). Returns:
      titles_by_rid: (doc, rid) -> set of normalized titles
      rids_by_title: (doc, title) -> set of distinct requirement ids
    """
    titles_by_rid: dict[tuple, set] = defaultdict(set)
    rids_by_title: dict[tuple, set] = defaultdict(set)
    with REQS_CORPUS.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            doc = str(row["doc_id"])
            rid = str(row["requirement_id"])
            title_norm = WS_RE.sub("", str(row.get("title") or ""))
            if not title_norm:
                continue
            titles_by_rid[(doc, rid)].add(title_norm)
            rids_by_title[(doc, title_norm)].add(rid)
    return titles_by_rid, rids_by_title


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alpha", type=float, default=5.0, help="Shrinkage parameter")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    matrix, ids, index = load_snapshot()
    features = load_features()
    pairs = load_pairs()
    anchors = load_anchors()
    titles_by_rid, rids_by_title = load_req_titles()

    print(f"Loaded: {len(ids)} objects, {len(pairs)} pairs, {len(anchors)} anchors")

    # ============ R0: No-ID test set (L1 only, L2 excluded per D2) ============
    print("\n--- R0: No-ID test set construction ---")

    l1_anchors = [a for a in anchors if a.get("layer") == "L1"]
    l2_anchors = [a for a in anchors if a.get("layer") == "L2"]
    l2_multi = sum(1 for a in l2_anchors if a.get("match_confidence") == "multi_match")
    print(f"L1 anchors: {len(l1_anchors)}; L2 excluded: {len(l2_anchors)} "
          f"(multi_match {l2_multi / max(len(l2_anchors), 1):.1%}, "
          f"D2 adjudication: neither reliable positive nor verified negative)")

    all_docs = sorted(set(a["doc_id"] for a in l1_anchors))
    rng = np.random.default_rng(args.seed)
    doc_order = rng.permutation(len(all_docs))
    n_test_docs = max(3, len(all_docs) // 3)
    test_docs = set(all_docs[i] for i in doc_order[:n_test_docs])

    # L1-anchored requirements per doc = deterministic negative pool
    l1_reqs_by_doc: dict[str, set] = defaultdict(set)
    for a in l1_anchors:
        l1_reqs_by_doc[a["doc_id"]].add(a["requirement_id"])

    def pair_texts(node_key: str, req_key: str) -> tuple[str, str]:
        node_text = features.get(node_key, {}).get("text", "")
        req_text = features.get(req_key, {}).get("text", "")
        return node_text, req_text

    def has_shared_id(node_key: str, req_key: str) -> bool:
        node_text, req_text = pair_texts(node_key, req_key)
        return bool(set(ID_RE.findall(node_text)) & set(ID_RE.findall(req_text)))

    def make_pair(anchor_row: dict, req_id: str, label: int, basis: str) -> dict | None:
        node_key = f"diagram_node:{anchor_row['node_id']}"
        req_key = f"requirement:{req_id}"
        if node_key not in index or req_key not in index:
            return None
        if has_shared_id(node_key, req_key):
            return None
        return {
            "aidx": index[node_key], "cidx": index[req_key],
            "label": label, "basis": basis, "doc": anchor_row["doc_id"],
        }

    # Positives: L1 title-bridge, unambiguous title (no other requirement id
    # in the same doc shares the bridged title)
    no_id_test: list[dict] = []
    no_id_train: list[dict] = []
    test_anchor_rows: list[dict] = []
    skipped_ambiguous = 0
    for a in l1_anchors:
        ev_title = WS_RE.sub("", str(a["evidence"].get("requirement_title") or ""))
        if ev_title and len(rids_by_title.get((a["doc_id"], ev_title), ())) > 1:
            skipped_ambiguous += 1
            continue
        pair = make_pair(a, a["requirement_id"], 1, "l1_title_bridge")
        if pair is None:
            continue
        if a["doc_id"] in test_docs:
            no_id_test.append(pair)
            test_anchor_rows.append(a)
        else:
            no_id_train.append(pair)

    # Negatives: same-doc L1 mismatch — node anchored to A paired with req B,
    # B title-distinct from all of A's titles (no equality, no substring relation)
    def eligible_negatives(anchor_row: dict) -> list[str]:
        doc = anchor_row["doc_id"]
        a_titles = titles_by_rid.get((doc, anchor_row["requirement_id"]), set())
        out: list[str] = []
        for b in l1_reqs_by_doc[doc]:
            if b == anchor_row["requirement_id"]:
                continue
            b_titles = titles_by_rid.get((doc, b), set())
            if not b_titles or not a_titles:
                continue
            distinct = all(
                tb != ta and tb not in ta and ta not in tb
                for tb in b_titles for ta in a_titles
            )
            if distinct:
                out.append(b)
        return out

    print(f"  No-ID test docs ({len(test_docs)}): {sorted(test_docs)}")
    print(f"  No-ID test positives: {len(no_id_test)} "
          f"({skipped_ambiguous} ambiguous-title pairs excluded)")
    print(f"  No-ID train positives: {len(no_id_train)}")

    hard_neg_test: list[dict] = []
    for a in test_anchor_rows:
        pool = eligible_negatives(a)
        if not pool:
            continue
        b = pool[int(rng.integers(len(pool)))]
        pair = make_pair(a, b, 0, "l1_mismatch_negative")
        if pair is not None:
            hard_neg_test.append(pair)

    print(f"  L1 mismatch negatives (test): {len(hard_neg_test)}")
    l2_stats = {
        "l2_total": len(l2_anchors),
        "l2_multi_match": l2_multi,
        "l2_multi_match_rate": round(l2_multi / max(len(l2_anchors), 1), 4),
    }

    # ============ R1: Template baseline with shrinkage ============
    print(f"\n--- R1: Template baseline (shrinkage alpha={args.alpha}) ---")

    baselines, section_means, cell_counts = compute_template_baseline_shrinkage(
        matrix, ids, features, alpha=args.alpha)
    print(f"Template baselines: {len(baselines)} doc-level LODO cells")
    print(f"Cell coverage: min={min(cell_counts.values())}, max={max(cell_counts.values())}, "
          f"median={int(np.median(list(cell_counts.values())))}")

    # Compute residuals: each object uses its own doc's LODO baseline
    residuals = np.zeros_like(matrix)
    coverage = 0
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
            coverage += 1
        else:
            residuals[i] = matrix[i]

    # L2 normalize
    norms = np.maximum(np.linalg.norm(residuals, axis=1, keepdims=True), 1e-8)
    residuals = residuals / norms
    print(f"Residual coverage: {coverage}/{len(ids)} = {coverage/len(ids):.1%}")

    # ============ R2: Pure residual arm evaluation ============
    print("\n--- R2: Residual vs Raw on no-ID test ---")

    # Deterministic L1 test set: positives + 1:1 mismatched negatives
    test_eval = no_id_test + hard_neg_test

    if test_eval:
        # Raw scores
        raw_scores = [float(matrix[r["aidx"]] @ matrix[r["cidx"]]) for r in test_eval]
        raw_labels = [r["label"] for r in test_eval]
        raw_auc = compute_auc(raw_scores, raw_labels)

        # Residual scores
        res_scores = [float(residuals[r["aidx"]] @ residuals[r["cidx"]]) for r in test_eval]
        res_auc = compute_auc(res_scores, raw_labels)

        # Fusion (λ=0.5)
        fus_scores = [float((matrix[r["aidx"]] @ matrix[r["cidx"]]) * 0.5
                            + (residuals[r["aidx"]] @ residuals[r["cidx"]]) * 0.5)
                      for r in test_eval]
        fus_auc = compute_auc(fus_scores, raw_labels)

        print(f"No-ID test set: {len(test_eval)} pairs "
              f"({sum(raw_labels)} pos, {len(raw_labels)-sum(raw_labels)} neg)")
        print(f"  Raw AUC:       {raw_auc}")
        print(f"  Residual AUC:  {res_auc}")
        print(f"  Fusion AUC:    {fus_auc}")

        results = {
            "no_id_test": {
                "n": len(test_eval),
                "n_pos": sum(raw_labels),
                "n_neg": len(raw_labels) - sum(raw_labels),
                "positive_basis": "l1_title_bridge",
                "negative_basis": "l1_mismatch_negative",
                "l2_excluded": "D2 adjudication: ~15-30% true positives in 20-sample "
                               "stratified audit; bge_cos arm is near-pure different-entity "
                               "(parent/child, steps, actors); lexical arm contains "
                               "title-with-ID-suffix L1 misses",
                "auc_raw": round(raw_auc, 4) if raw_auc else None,
                "auc_residual": round(res_auc, 4) if res_auc else None,
                "auc_fusion": round(fus_auc, 4) if fus_auc else None,
            },
            "l2_stats": l2_stats,
            "test_docs": sorted(test_docs),
            "template_baselines": len(baselines),
            "residual_coverage": round(coverage / len(ids), 4),
        }
    else:
        print("  No valid no-ID test pairs found")
        results = {"error": "no_id_test_empty"}

    # Silver test for comparison
    silver_test = [p for p in pairs if p.get("split") == "test"]
    silver_rows = []
    for p in silver_test:
        aid = p["anchor"]["occurrence_id"]
        cid = p["candidate"]["occurrence_id"]
        if aid in index and cid in index:
            silver_rows.append({"aidx": index[aid], "cidx": index[cid],
                               "label": int(p["label"])})

    if silver_rows:
        silver_raw = [float(matrix[r["aidx"]] @ matrix[r["cidx"]]) for r in silver_rows]
        silver_labels = [r["label"] for r in silver_rows]
        silver_auc = compute_auc(silver_raw, silver_labels)
        print(f"\nSilver test (ID-separable): {len(silver_rows)} pairs, "
              f"raw AUC={silver_auc}")
        results["silver_test_auc"] = round(silver_auc, 4)

    # Save
    run = open_run("residual_redesign", {
        "alpha": args.alpha,
        "seed": args.seed,
        "n_test_docs": len(test_docs),
    }, args.runs_root)
    run.save_result(results)
    print(f"\n{'='*60}")
    print(f"R0-R3 Results saved to: {run.path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
