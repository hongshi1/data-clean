#!/usr/bin/env python3
"""Protocol #48 ablation matrix (B/C/D/A4 rows) on the balanced folds.

Seven configurations over identical balanced-fold train/dev/test pairs
(seed 42, ``--fold-map`` defaulting to the archived balance_folds
assignment), all reported on the test fold:

  A1-native             frozen BGE cosine from vectors.npz (no training)
  A3-projection         shared projection head, InfoNCE + identity boundary
                        (replicates the train_shared_projection training loop
                        verbatim, reproducing the archived balanced-fold run)
  A4-gate-clean         A3 score fused with the structural gate
                        (0.7*proj + 0.3*gate; identifier_match forced False)
  A4-gate-leak          same fusion with identifier_match enabled — oracle
                        upper bound: identifier overlap reproduces the silver
                        label definition (negatives are ID-disjoint), so this
                        row must never be the paper's main row
  B1-late-interaction   BGE token-level IDF-weighted MaxSim, test fold only
  C2-infonce-only       projection trained with boundary_weight=0
  C3-boundary-only      projection trained with the boundary term only
  D-calibration         temperature scaling of A3 scores (tau fit on dev NLL,
                        grid 0.05..5) with ECE/Brier before and after

Threshold protocol: dev-fold negative-score 95th percentile. B1 deviates by
design (only test-fold texts are token-encoded for scale control) and
calibrates its threshold on test negatives — flagged in the result notes.

Usage: python tools/eval_ablation_matrix.py [--epochs 20] [--limit N]
Output: markdown comparison table on stdout + runs protocol result.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = BASE / "data/gjb_438c/feature_snapshot_v1"
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
BGE_MODEL_DIR = BASE / "models/embedding/bge-large-zh-v1.5"

# Balanced doc->fold assignment produced by tools/balance_folds.py and used by
# the archived balanced-fold retrain (runs/train_shared_projection_3408ed57_*,
# dev AUC 0.8539 / test AUC 0.9193). 0=test 1=dev 2,3=train.
DEFAULT_FOLD_MAP = "01:1,02:2,03:3,04:3,05:3,06:0,07:1,08:2,09:2,10:1,11:3,12:0,13:0,14:3,15:3,16:1"

GATE_ALPHA = 0.7
ECE_BINS = 15
TAU_LO, TAU_HI = 0.05, 5.0
B1_IDF_TRAIN_SAMPLE = 5000
# Mirrors BgeLocal._MAX_LEN (embed_tokens default max_length).
B1_MAX_TOKENS = 256

# Archived balanced-fold reference used only as a reproduction audit trail.
A3_REFERENCE = {
    "run": "train_shared_projection_3408ed57_20261022_073000",
    "dev_auc": 0.8539,
    "test_auc": 0.9193,
    "test_false_merge_rate": 0.0193,
}

sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402
from train_shared_projection import (  # noqa: E402
    FOLD_TO_SPLIT,
    build_model,
    load_pairs,
    load_snapshot,
    parse_fold_map,
    sweep_threshold,
)

from algorithms.context_linking.alignment.late_interaction import (  # noqa: E402
    idf_weighted_maxsim,
)
from algorithms.context_linking.alignment.structural_gate import (  # noqa: E402
    StructuralCompatibility,
    structural_score,
)
from algorithms.common.bge_local import BgeLocal  # noqa: E402


def build_rows(
    pairs: list[dict[str, Any]],
    index: dict[str, int],
    fold_map: dict[str, int] | None,
) -> tuple[list[dict[str, Any]], int]:
    """Mirror train_shared_projection.pair_indices (same skip/fold logic)
    while keeping the source pair dict for gate features and texts."""

    rows: list[dict[str, Any]] = []
    missing = 0
    for pair in pairs:
        anchor_id = pair["anchor"]["occurrence_id"]
        candidate_id = pair["candidate"]["occurrence_id"]
        if anchor_id not in index or candidate_id not in index:
            missing += 1
            continue
        split = str(pair.get("split", "train"))
        if fold_map is not None:
            doc_id = str(pair["anchor"]["doc_id"])
            fold = fold_map.get(doc_id, pair.get("fold"))
            if fold is None:
                raise SystemExit(
                    f"pair {pair.get('pair_id', '?')} has no stored fold and "
                    f"doc {doc_id!r} is missing from the fold map"
                )
            split = FOLD_TO_SPLIT[int(fold)]
        rows.append(
            {
                "anchor": index[anchor_id],
                "candidate": index[candidate_id],
                "label": int(pair["label"]),
                "split": split,
                "pair": pair,
            }
        )
    return rows, missing


def rank_auc(scores: list[float], labels: list[int]) -> float:
    """Tie-corrected rank AUC, identical to train_shared_projection.evaluate."""

    positives = sum(labels)
    negatives = len(labels) - positives
    order = sorted(range(len(scores)), key=lambda position: scores[position])
    ranks = [0.0] * len(scores)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and scores[order[end + 1]] == scores[order[start]]:
            end += 1
        average_rank = (start + end) / 2.0 + 1.0
        for position in order[start : end + 1]:
            ranks[position] = average_rank
        start = end + 1
    rank_sum_pos = sum(
        ranks[position] for position, label in enumerate(labels) if label == 1
    )
    return (rank_sum_pos - positives * (positives + 1) / 2.0) / max(
        positives * negatives, 1
    )


def metrics_from_scores(
    scores: list[float], labels: list[int], threshold: float
) -> dict[str, Any]:
    """Same metric block as train_shared_projection.evaluate, from raw scores."""

    positives = sum(labels)
    negatives = len(labels) - positives
    predicted_positive = [1 if score >= threshold else 0 for score in scores]
    true_positive = sum(
        1 for predicted, label in zip(predicted_positive, labels) if predicted == 1 and label == 1
    )
    false_positive = sum(
        1 for predicted, label in zip(predicted_positive, labels) if predicted == 1 and label == 0
    )
    false_negative = sum(
        1 for predicted, label in zip(predicted_positive, labels) if predicted == 0 and label == 1
    )
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    false_merge = false_positive / max(negatives, 1)
    return {
        "n_pairs": len(labels),
        "auc": round(rank_auc(scores, labels), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_merge_rate": round(false_merge, 4),
        "threshold": threshold,
    }


# ── A4: structural gate fusion ───────────────────────────────────────────


def gate_features_from_pair(
    pair: dict[str, Any], use_identifier: bool
) -> StructuralCompatibility:
    """Structural gate features from a pair record.

    ``same_section=False`` maps to "unknown" (not "incompatible"):
    cross-section coreference is exactly what the linking task must find, so
    the absence of same-section evidence is not identity-disqualifying.
    ``identifier_match`` is only enabled for the A4-leak oracle variant —
    the silver negatives are defined by ID disjointness, so enabling it feeds
    the label to the gate (gold leakage).
    """

    features = pair.get("features", {})
    same_doc = str(pair["anchor"]["doc_id"]) == str(pair["candidate"]["doc_id"])
    same_section = bool(features.get("same_section", False))
    identifiers = features.get("shared_identifiers") or []
    return StructuralCompatibility(
        same_doc="compatible" if same_doc else "incompatible",
        same_section="compatible" if same_section else "unknown",
        same_role="unknown",
        same_scope="unknown",
        identifier_match=bool(identifiers) if use_identifier else False,
        hard_veto=False,
    )


def fuse_one(
    proj_score: float, features: StructuralCompatibility, alpha: float = GATE_ALPHA
) -> float:
    """score_final = alpha*proj_cos + (1-alpha)*structural_score; veto -> -inf."""

    gate_score, veto = structural_score(features)
    if veto:
        return float("-inf")
    return alpha * proj_score + (1.0 - alpha) * gate_score


def fused_scores(
    proj_scores: list[float],
    pairs: list[dict[str, Any]],
    alpha: float = GATE_ALPHA,
    use_identifier: bool = True,
) -> list[float]:
    return [
        fuse_one(score, gate_features_from_pair(pair, use_identifier), alpha)
        for score, pair in zip(proj_scores, pairs)
    ]


# ── D: calibration primitives ────────────────────────────────────────────


def _sigmoid(z: np.ndarray) -> np.ndarray:
    out = np.empty_like(z)
    positive = z >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-z[positive]))
    exp_z = np.exp(z[~positive])
    out[~positive] = exp_z / (1.0 + exp_z)
    return out


def temperature_probs(scores: list[float] | np.ndarray, tau: float) -> np.ndarray:
    """sigmoid(score / tau) — overflow-safe."""

    z = np.asarray(scores, dtype=np.float64) / float(tau)
    return _sigmoid(z)


def nll_of_tau(
    scores: list[float] | np.ndarray, labels: list[int] | np.ndarray, tau: float
) -> float:
    """Mean cross-entropy at temperature tau (stable logaddexp form)."""

    z = np.asarray(scores, dtype=np.float64) / float(tau)
    y = np.asarray(labels, dtype=np.float64)
    return float(np.mean(np.logaddexp(0.0, z) - y * z))


def fit_temperature(
    dev_scores: list[float], dev_labels: list[int], lo: float = TAU_LO, hi: float = TAU_HI
) -> tuple[float, float]:
    """Grid-search tau in [lo, hi] minimizing dev NLL (coarse + fine)."""

    coarse = np.linspace(lo, hi, 200)
    coarse_nll = [nll_of_tau(dev_scores, dev_labels, float(tau)) for tau in coarse]
    best_position = int(np.argmin(coarse_nll))
    step = float(coarse[1] - coarse[0])
    fine_lo = max(lo, float(coarse[best_position]) - step)
    fine_hi = min(hi, float(coarse[best_position]) + step)
    fine = np.linspace(fine_lo, fine_hi, 41)
    # tau=1 (identity) joins the candidates so a fitted temperature is never
    # worse than the uncalibrated scores on dev.
    candidates = [float(value) for value in fine] + [1.0]
    candidate_nll = [nll_of_tau(dev_scores, dev_labels, tau) for tau in candidates]
    best = int(np.argmin(candidate_nll))
    return round(candidates[best], 6), candidate_nll[best]


def expected_calibration_error(
    probs: list[float] | np.ndarray, labels: list[int] | np.ndarray, n_bins: int = ECE_BINS
) -> float:
    """ECE over n_bins equal-width bins on [0, 1]."""

    probabilities = np.asarray(probs, dtype=np.float64)
    targets = np.asarray(labels, dtype=np.float64)
    total = probabilities.size
    if total == 0:
        return 0.0
    indices = np.clip((probabilities * n_bins).astype(int), 0, n_bins - 1)
    error = 0.0
    for bin_index in range(n_bins):
        mask = indices == bin_index
        count = int(mask.sum())
        if count == 0:
            continue
        error += (count / total) * abs(
            float(probabilities[mask].mean()) - float(targets[mask].mean())
        )
    return float(error)


def brier_score(
    probs: list[float] | np.ndarray, labels: list[int] | np.ndarray
) -> float:
    probabilities = np.asarray(probs, dtype=np.float64)
    targets = np.asarray(labels, dtype=np.float64)
    if probabilities.size == 0:
        return 0.0
    return float(np.mean((probabilities - targets) ** 2))


# ── A3/C2/C3: projection-head training variants ──────────────────────────


def train_projection(
    torch: Any,
    matrix: np.ndarray,
    train_rows: list[dict[str, Any]],
    *,
    loss_mode: str,
    seed: int,
    epochs: int,
    batch_size: int,
    shared_dim: int,
    lr: float,
    temperature: float,
    boundary_margin: float,
    boundary_weight: float,
) -> tuple[Any, list[dict[str, float]]]:
    """Unified projection-head trainer for the A3/C2/C3 ablation variants.

    ``loss_mode="infonce_boundary"`` replicates the train_shared_projection
    training loop verbatim (same RNG stream and op order on CPU), so the A3
    row reproduces the archived balanced-fold run bit-for-bit.
    ``"infonce_only"`` drops the zero-weight boundary term together with its
    dead negative sampling (C2 = boundary_weight 0). ``"boundary_only"``
    iterates every training negative per epoch under the margin penalty and
    uses no InfoNCE and no positives (C3).
    """

    if loss_mode not in ("infonce_boundary", "infonce_only", "boundary_only"):
        raise ValueError(f"unknown loss_mode: {loss_mode!r}")
    model = build_model(torch, matrix.shape[1], shared_dim, seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    matrix_tensor = torch.from_numpy(matrix)

    def project(indices: Any) -> Any:
        vectors = matrix_tensor[indices]
        output = model(vectors)
        return torch.nn.functional.normalize(output, dim=-1)

    train_positive = [row for row in train_rows if row["label"] == 1]
    train_negative = [row for row in train_rows if row["label"] == 0]
    rng = np.random.default_rng(seed)
    history: list[dict[str, float]] = []
    for epoch in range(epochs):
        model.train()
        total_infonce = 0.0
        total_boundary = 0.0
        batches = 0
        if loss_mode in ("infonce_boundary", "infonce_only"):
            order = rng.permutation(len(train_positive))
            for start in range(0, len(order), batch_size):
                batch_rows = [train_positive[position] for position in order[start : start + batch_size]]
                anchors = torch.tensor([row["anchor"] for row in batch_rows], dtype=torch.long)
                positives = torch.tensor([row["candidate"] for row in batch_rows], dtype=torch.long)
                anchor_vectors = project(anchors)
                positive_vectors = project(positives)
                logits = anchor_vectors @ positive_vectors.T / temperature
                targets = torch.arange(len(batch_rows))
                loss_infonce = torch.nn.functional.cross_entropy(logits, targets)
                if loss_mode == "infonce_boundary" and train_negative:
                    sample_size = min(len(batch_rows), len(train_negative))
                    positions = rng.integers(0, len(train_negative), size=sample_size)
                    negative_rows = [train_negative[position] for position in positions]
                    negative_anchors = torch.tensor(
                        [row["anchor"] for row in negative_rows], dtype=torch.long
                    )
                    negative_candidates = torch.tensor(
                        [row["candidate"] for row in negative_rows], dtype=torch.long
                    )
                    negative_scores = (
                        project(negative_anchors) * project(negative_candidates)
                    ).sum(dim=-1)
                    loss_boundary = torch.clamp(
                        negative_scores + boundary_margin, min=0.0
                    ).mean()
                else:
                    loss_boundary = torch.tensor(0.0)
                loss = loss_infonce + boundary_weight * loss_boundary
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_infonce += float(loss_infonce.detach())
                total_boundary += float(loss_boundary.detach())
                batches += 1
        else:  # boundary_only: every training negative each epoch, no InfoNCE
            if not train_negative:
                raise SystemExit("boundary_only requires training negatives")
            order = rng.permutation(len(train_negative))
            for start in range(0, len(order), batch_size):
                batch_rows = [train_negative[position] for position in order[start : start + batch_size]]
                anchors = torch.tensor([row["anchor"] for row in batch_rows], dtype=torch.long)
                candidates = torch.tensor([row["candidate"] for row in batch_rows], dtype=torch.long)
                scores = (project(anchors) * project(candidates)).sum(dim=-1)
                loss = torch.clamp(scores + boundary_margin, min=0.0).mean()
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                total_boundary += float(loss.detach())
                batches += 1
        history.append(
            {
                "epoch": epoch + 1,
                "infonce": round(total_infonce / max(batches, 1), 4),
                "boundary": round(total_boundary / max(batches, 1), 4),
            }
        )
    return model, history


def projected_scores(
    torch: Any, model: Any, matrix: np.ndarray, rows: list[dict[str, Any]], batch: int = 4096
) -> list[float]:
    """Cosine of projected vectors per row (eval mode, full-matrix pass)."""

    model.eval()
    with torch.no_grad():
        projected = []
        for start in range(0, matrix.shape[0], batch):
            chunk = torch.from_numpy(matrix[start : start + batch])
            projected.append(model(chunk))
        projected = torch.cat(projected)
        projected = torch.nn.functional.normalize(projected, dim=-1).cpu().numpy()
    return [float(projected[row["anchor"]] @ projected[row["candidate"]]) for row in rows]


def native_scores(matrix: np.ndarray, rows: list[dict[str, Any]]) -> list[float]:
    return [float(matrix[row["anchor"]] @ matrix[row["candidate"]]) for row in rows]


# ── B1: token-level IDF-weighted MaxSim (test fold only) ─────────────────


def run_b1_late_interaction(
    test_rows: list[dict[str, Any]],
    train_rows: list[dict[str, Any]],
    model_dir: Path,
    seed: int,
    idf_train_sample: int = B1_IDF_TRAIN_SAMPLE,
) -> tuple[list[float], dict[str, Any]]:
    """IDF-weighted MaxSim scores on the test fold (training-free control).

    Scale control: only test-fold texts are token-encoded (unique texts;
    13696 sides deduplicate heavily). IDF document frequency is computed
    over the token sets of test texts plus a seeded sample of unique
    train-side texts (up to idf_train_sample). The threshold is therefore
    calibrated on test negatives (in-fold) — reported and flagged, since the
    dev fold is deliberately left untouched for this training-free control.
    """

    bge = BgeLocal(model_dir=model_dir, use_cache=False)
    mode = bge.ensure()
    # BgeLocal.ensure returns the torch device name ("cuda"|"cpu") or
    # "unavailable"; only the CUDA path is acceptable here.
    if mode != "cuda":
        raise SystemExit(
            "B1 requires CUDA BGE token encoding (no silent CPU fallback); "
            f"mode={mode!r}, last_error={bge.last_error!r}"
        )
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)

    def unique_texts(rows: list[dict[str, Any]]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for row in rows:
            for side in ("anchor", "candidate"):
                text = str(row["pair"][side]["text"])
                if text and text not in seen:
                    seen.add(text)
                    ordered.append(text)
        return ordered

    test_texts = unique_texts(test_rows)
    train_texts = unique_texts(train_rows)
    rng = np.random.default_rng(seed)
    if len(train_texts) > idf_train_sample:
        pick = rng.permutation(len(train_texts))[:idf_train_sample]
        train_sample = [train_texts[position] for position in pick]
    else:
        train_sample = list(train_texts)
    corpus = test_texts + train_sample

    token_cache: dict[str, list[int]] = {}

    def token_ids(text: str) -> list[int]:
        cached = token_cache.get(text)
        if cached is None:
            encoded = tokenizer(text, truncation=True, max_length=B1_MAX_TOKENS)
            cached = list(encoded["input_ids"])
            token_cache[text] = cached
        return cached

    document_frequency: dict[int, int] = {}
    for text in corpus:
        for token_id in set(token_ids(text)):
            document_frequency[token_id] = document_frequency.get(token_id, 0) + 1
    n_documents = len(corpus)

    def idf_of(token_id: int) -> float:
        # Smoothed idf; the +1 keeps every weight positive (CLS/SEP included).
        return math.log((n_documents + 1) / (document_frequency.get(token_id, 0) + 1)) + 1.0

    matrices = bge.embed_tokens(test_texts)
    scores: list[float] = []
    for row in test_rows:
        anchor_text = str(row["pair"]["anchor"]["text"])
        candidate_text = str(row["pair"]["candidate"]["text"])
        query = matrices.get(anchor_text)
        document = matrices.get(candidate_text)
        if query is None or document is None or len(query) == 0 or len(document) == 0:
            scores.append(0.0)
            continue
        idf = np.asarray([idf_of(token_id) for token_id in token_ids(anchor_text)], dtype=np.float64)
        scores.append(idf_weighted_maxsim(np.asarray(query), np.asarray(document), idf))

    stats = {
        "n_test_pairs": len(test_rows),
        "n_test_sides": 2 * len(test_rows),
        "n_unique_test_texts_encoded": len(test_texts),
        "idf_corpus_documents": n_documents,
        "idf_train_texts_available": len(train_texts),
        "idf_train_texts_sampled": len(train_sample),
        "idf_train_sample_target": idf_train_sample,
        "bge_mode": mode,
        "bge_device": str(bge.stats.get("device", "")),
        "bge_dim": int(bge.stats.get("dim", 0)),
        "token_max_length": B1_MAX_TOKENS,
        "score_direction": "anchor(query)->candidate(document), IDF-weighted MaxSim",
    }
    return scores, stats


# ── main: run the matrix ─────────────────────────────────────────────────

CONFIG_ORDER = [
    "A1-native",
    "A3-projection",
    "A4-projection-gate-clean",
    "A4-projection-gate-leak",
    "B1-late-interaction",
    "C2-infonce-only",
    "C3-boundary-only",
    "D-calibration",
]

CONFIG_DESCRIPTIONS = {
    "A1-native": "frozen BGE cosine, no training",
    "A3-projection": "InfoNCE + identity boundary (full loss)",
    "A4-projection-gate-clean": "A3 + structural gate, identifier forced False (paper main row)",
    "A4-projection-gate-leak": "A3 + gate with identifier_match (oracle, label leakage)",
    "B1-late-interaction": "BGE token-level IDF-weighted MaxSim (test only)",
    "C2-infonce-only": "projection trained with boundary_weight=0",
    "C3-boundary-only": "projection trained with boundary term only",
    "D-calibration": "A3 scores + temperature scaling (tau on dev NLL)",
}


def build_summary_markdown(configs: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    header = (
        "| config | AUC | F1 | precision | recall | false_merge_rate | threshold | extra |"
        "\n|---|---:|---:|---:|---:|---:|---:|---|"
    )
    lines = [header]
    summary_rows: list[dict[str, Any]] = []
    for name in CONFIG_ORDER:
        entry = configs.get(name)
        if entry is None:
            continue
        test = entry["test"]
        row = {
            "config": name,
            "auc": test["auc"],
            "f1": test["f1"],
            "precision": test["precision"],
            "recall": test["recall"],
            "false_merge_rate": test["false_merge_rate"],
            "threshold": test["threshold"],
            "n_pairs": test["n_pairs"],
            "description": CONFIG_DESCRIPTIONS[name],
        }
        extra = ""
        if name == "D-calibration":
            row["ece_before"] = entry["ece_before"]
            row["ece_after"] = entry["ece_after"]
            row["brier_before"] = entry["brier_before"]
            row["brier_after"] = entry["brier_after"]
            row["tau"] = entry["tau"]
            extra = (
                f"ECE {entry['ece_before']:.4f}->{entry['ece_after']:.4f}, "
                f"Brier {entry['brier_before']:.4f}->{entry['brier_after']:.4f}, "
                f"tau {entry['tau']}"
            )
        if name == "B1-late-interaction":
            extra = "threshold in-fold (test negatives); AUC comparable"
        if name == "A4-projection-gate-leak":
            extra = "oracle upper bound (identifier leak)"
        lines.append(
            f"| {name} | {test['auc']:.4f} | {test['f1']:.4f} | {test['precision']:.4f} "
            f"| {test['recall']:.4f} | {test['false_merge_rate']:.4f} "
            f"| {test['threshold']} | {extra} |"
        )
        summary_rows.append(row)
    return "\n".join(lines), summary_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--fold-map",
        type=str,
        default=DEFAULT_FOLD_MAP,
        help=(
            'doc->fold override "doc1:fold,doc2:fold"; default is the archived '
            "balance_folds assignment (0=test 1=dev 2,3=train); "
            "'stored' keeps the hash folds recorded in pairs.jsonl"
        ),
    )
    parser.add_argument("--snapshot-dir", type=Path, default=SNAPSHOT_DIR)
    parser.add_argument("--pairs", type=Path, default=PAIRS_PATH)
    parser.add_argument("--bge-model-dir", type=Path, default=BGE_MODEL_DIR)
    parser.add_argument("--limit", type=int, default=None, help="Cap rows (smoke)")
    parser.add_argument("--skip-b1", action="store_true", help="Skip GPU B1 row (smoke)")
    args = parser.parse_args()

    import torch

    fold_map = (
        None
        if args.fold_map.strip().lower() in ("stored", "none")
        else parse_fold_map(args.fold_map)
    )
    index, matrix, _ids = load_snapshot(args.snapshot_dir / "vectors.npz")
    pairs = load_pairs(args.pairs)
    rows, missing = build_rows(pairs, index, fold_map)
    train_rows = [row for row in rows if row["split"] == "train"]
    dev_rows = [row for row in rows if row["split"] == "dev"]
    test_rows = [row for row in rows if row["split"] == "test"]
    if args.limit:
        train_rows = train_rows[: args.limit]
        dev_rows = dev_rows[: max(args.limit // 4, 1)]
        test_rows = test_rows[: max(args.limit // 4, 1)]
    if not train_rows or not dev_rows or not test_rows:
        raise SystemExit("empty train/dev/test after fold mapping; check inputs")

    dev_labels = [row["label"] for row in dev_rows]
    test_labels = [row["label"] for row in test_rows]
    dev_pairs = [row["pair"] for row in dev_rows]
    test_pairs = [row["pair"] for row in test_rows]

    train_config = {
        "epochs": args.epochs,
        "batch_size": 256,
        "shared_dim": 256,
        "lr": 1e-4,
        "temperature": 0.07,
        "boundary_margin": 0.10,
        "boundary_weight": 0.5,
        "seed": args.seed,
        "device": "cpu (verbatim replication of train_shared_projection loop)",
    }
    config: dict[str, Any] = {
        "protocol": "48 ablation matrix (B/C/D/A4 rows) on balanced folds",
        "fold_map": fold_map,
        "fold_map_source": "tools/balance_folds.py archived assignment (default)",
        "snapshot": str(args.snapshot_dir),
        "pairs": str(args.pairs),
        "n_train": len(train_rows),
        "n_dev": len(dev_rows),
        "n_test": len(test_rows),
        "n_pairs_missing_vector": missing,
        "train_config": train_config,
        "gate": {
            "alpha": GATE_ALPHA,
            "fusion": "0.7*proj_cos + 0.3*structural_score, hard_veto -> -inf",
            "clean_variant": "identifier_match forced False",
            "same_section_false_maps_to": "unknown (cross-section coreference is legitimate)",
        },
        "threshold_rule": "dev negative-score 95th percentile (B1 exception: test, in-fold)",
        "limit": args.limit,
        "skip_b1": args.skip_b1,
        "reference_a3_run": A3_REFERENCE,
    }
    run = open_run("eval_ablation_matrix", config, RUNS_ROOT)
    configs: dict[str, Any] = {}

    # A1-native: frozen cosine, no training.
    a1_dev = native_scores(matrix, dev_rows)
    a1_test = native_scores(matrix, test_rows)
    a1_threshold = sweep_threshold(a1_dev, dev_labels)
    configs["A1-native"] = {
        "method": "frozen BGE cosine (vectors.npz), no training",
        "dev": metrics_from_scores(a1_dev, dev_labels, a1_threshold),
        "test": metrics_from_scores(a1_test, test_labels, a1_threshold),
    }

    # A3-projection: verbatim replication of the archived training loop.
    model_a3, history_a3 = train_projection(
        torch,
        matrix,
        train_rows,
        loss_mode="infonce_boundary",
        seed=args.seed,
        epochs=args.epochs,
        batch_size=train_config["batch_size"],
        shared_dim=train_config["shared_dim"],
        lr=train_config["lr"],
        temperature=train_config["temperature"],
        boundary_margin=train_config["boundary_margin"],
        boundary_weight=train_config["boundary_weight"],
    )
    a3_dev = projected_scores(torch, model_a3, matrix, dev_rows)
    a3_test = projected_scores(torch, model_a3, matrix, test_rows)
    a3_threshold = sweep_threshold(a3_dev, dev_labels)
    reference_check = {
        "archived_run": A3_REFERENCE["run"],
        "dev_auc_this": None,
        "test_auc_this": None,
        "dev_auc_archived": A3_REFERENCE["dev_auc"],
        "test_auc_archived": A3_REFERENCE["test_auc"],
    }
    configs["A3-projection"] = {
        "method": "shared projection head, InfoNCE + identity boundary",
        "loss": "infonce_plus_identity_boundary",
        "dev": metrics_from_scores(a3_dev, dev_labels, a3_threshold),
        "test": metrics_from_scores(a3_test, test_labels, a3_threshold),
        "history": history_a3,
    }
    reference_check["dev_auc_this"] = configs["A3-projection"]["dev"]["auc"]
    reference_check["test_auc_this"] = configs["A3-projection"]["test"]["auc"]
    reference_check["matches_archive"] = (
        args.limit is None
        and args.epochs == 20
        and reference_check["dev_auc_this"] == A3_REFERENCE["dev_auc"]
        and reference_check["test_auc_this"] == A3_REFERENCE["test_auc"]
    )

    # A4: A3 score + structural gate fusion (clean and leak variants).
    for name, use_identifier, role in (
        ("A4-projection-gate-clean", False, "paper main row"),
        ("A4-projection-gate-leak", True, "oracle upper bound (label leakage)"),
    ):
        fused_dev = fused_scores(a3_dev, dev_pairs, use_identifier=use_identifier)
        fused_test = fused_scores(a3_test, test_pairs, use_identifier=use_identifier)
        fused_threshold = sweep_threshold(fused_dev, dev_labels)
        configs[name] = {
            "method": "A3 projected cosine fused with structural gate "
            f"(alpha={GATE_ALPHA}); identifier_match={'enabled' if use_identifier else 'forced False'}",
            "role": role,
            "identifier_match_used": use_identifier,
            "dev": metrics_from_scores(fused_dev, dev_labels, fused_threshold),
            "test": metrics_from_scores(fused_test, test_labels, fused_threshold),
        }

    # C2: InfoNCE only (boundary_weight=0; dead negative sampling dropped).
    model_c2, history_c2 = train_projection(
        torch,
        matrix,
        train_rows,
        loss_mode="infonce_only",
        seed=args.seed,
        epochs=args.epochs,
        batch_size=train_config["batch_size"],
        shared_dim=train_config["shared_dim"],
        lr=train_config["lr"],
        temperature=train_config["temperature"],
        boundary_margin=train_config["boundary_margin"],
        boundary_weight=0.0,
    )
    c2_dev = projected_scores(torch, model_c2, matrix, dev_rows)
    c2_test = projected_scores(torch, model_c2, matrix, test_rows)
    c2_threshold = sweep_threshold(c2_dev, dev_labels)
    configs["C2-infonce-only"] = {
        "method": "shared projection head, InfoNCE only (boundary_weight=0)",
        "loss": "infonce_only",
        "dev": metrics_from_scores(c2_dev, dev_labels, c2_threshold),
        "test": metrics_from_scores(c2_test, test_labels, c2_threshold),
        "history": history_c2,
    }

    # C3: boundary only (no InfoNCE; negatives only, positives unused).
    model_c3, history_c3 = train_projection(
        torch,
        matrix,
        train_rows,
        loss_mode="boundary_only",
        seed=args.seed,
        epochs=args.epochs,
        batch_size=train_config["batch_size"],
        shared_dim=train_config["shared_dim"],
        lr=train_config["lr"],
        temperature=train_config["temperature"],
        boundary_margin=train_config["boundary_margin"],
        boundary_weight=1.0,
    )
    c3_dev = projected_scores(torch, model_c3, matrix, dev_rows)
    c3_test = projected_scores(torch, model_c3, matrix, test_rows)
    c3_threshold = sweep_threshold(c3_dev, dev_labels)
    configs["C3-boundary-only"] = {
        "method": "shared projection head, identity boundary term only "
        "(margin penalty on all train negatives per epoch; positives unused)",
        "loss": "boundary_only",
        "dev": metrics_from_scores(c3_dev, dev_labels, c3_threshold),
        "test": metrics_from_scores(c3_test, test_labels, c3_threshold),
        "history": history_c3,
    }

    # B1: token-level late interaction, test fold only.
    if not args.skip_b1:
        b1_scores, b1_stats = run_b1_late_interaction(
            test_rows, train_rows, args.bge_model_dir, args.seed
        )
        b1_threshold = sweep_threshold(b1_scores, test_labels)
        configs["B1-late-interaction"] = {
            "method": "BGE token-level IDF-weighted MaxSim (anchor->candidate)",
            "training": "none",
            "threshold_source": "test negative 95th percentile (in-fold; see notes)",
            "test": metrics_from_scores(b1_scores, test_labels, b1_threshold),
            **b1_stats,
        }

    # D: temperature-scaled calibration of A3 scores.
    tau, dev_nll_at_tau = fit_temperature(a3_dev, dev_labels)
    dev_nll_identity = nll_of_tau(a3_dev, dev_labels, 1.0)
    calibrated_dev = temperature_probs(a3_dev, tau)
    calibrated_test = temperature_probs(a3_test, tau)
    d_threshold = sweep_threshold(calibrated_dev.tolist(), dev_labels)
    probs_identity_test = temperature_probs(a3_test, 1.0)
    configs["D-calibration"] = {
        "method": "temperature scaling of A3 scores; tau fit on dev NLL "
        f"(grid {TAU_LO}..{TAU_HI}, coarse 200 + fine 41)",
        "base": "A3-projection",
        "tau": tau,
        "dev_nll_tau1": round(dev_nll_identity, 6),
        "dev_nll_tau": round(dev_nll_at_tau, 6),
        "ece_before": round(expected_calibration_error(probs_identity_test, test_labels), 4),
        "ece_after": round(expected_calibration_error(calibrated_test, test_labels), 4),
        "brier_before": round(brier_score(probs_identity_test, test_labels), 4),
        "brier_after": round(brier_score(calibrated_test, test_labels), 4),
        "test": metrics_from_scores(calibrated_test.tolist(), test_labels, d_threshold),
    }

    leak_test = configs["A4-projection-gate-leak"]["test"]
    clean_test = configs["A4-projection-gate-clean"]["test"]
    a4_delta = {
        "auc": round(leak_test["auc"] - clean_test["auc"], 4),
        "f1": round(leak_test["f1"] - clean_test["f1"], 4),
        "precision": round(leak_test["precision"] - clean_test["precision"], 4),
        "recall": round(leak_test["recall"] - clean_test["recall"], 4),
        "false_merge_rate": round(
            leak_test["false_merge_rate"] - clean_test["false_merge_rate"], 4
        ),
        "interpretation": (
            "gain attributable to identifier_match alone, i.e. the silver-label "
            "shortcut leaked into the gate (negatives are defined as ID-disjoint)"
        ),
    }

    summary_table, summary_rows = build_summary_markdown(configs)
    notes: dict[str, Any] = {
        "A4-leak": (
            "oracle upper bound: identifier_match coincides with the silver label "
            "by construction (negatives are ID-disjoint pairs); never the paper main row"
        ),
        "paper_main_row": "A4-projection-gate-clean",
        "B1_test_only": (
            "B1 encodes only test-fold texts (scale control, training-free method); "
            "threshold calibrated in-fold on test negatives, so its F1/precision/"
            "recall/false-merge are optimistic vs other rows; AUC is threshold-free "
            "and comparable; IDF df uses test texts + seeded train-text sample"
        ),
        "gate_feature_limits": (
            "same_doc is constant-true on this within-doc pair set (constant shift, "
            "no ranking effect); same_section=False mapped to unknown, not "
            "incompatible, because cross-section coreference is legitimate; "
            "same_role/same_scope default unknown — the clean gate carries almost "
            "no discriminative signal on this silver data"
        ),
        "threshold_protocol": "dev negative-score 95th percentile (B1 exception above)",
        "D_calibration": (
            "temperature scaling is a strictly monotonic remap: ranking metrics are "
            "unchanged (AUC identical by construction; F1 identical up to threshold "
            "rounding); only ECE/Brier move"
        ),
        "C3_boundary_only": (
            "boundary-only variant trains on negative pairs only (margin penalty); "
            "positives are unused, so no term pulls similar pairs together"
        ),
        "C2_infonce_only": (
            "boundary_weight=0; the dead negative sampling is dropped along with "
            "the zero-weight term (identical gradients, faster epochs)"
        ),
        "A3_reference_check": reference_check,
    }
    if args.epochs != 20:
        notes["epochs_reduced_for_runtime"] = args.epochs

    result = {
        "configs": configs,
        "summary_table": summary_table,
        "summary_rows": summary_rows,
        "a4_leak_vs_clean_delta": a4_delta,
        "notes": notes,
    }
    run.save_result(result)
    print(summary_table)
    print()
    print(f"A4 leak-vs-clean (identifier shortcut on the gate): {json.dumps(a4_delta, ensure_ascii=False)}")
    print(f"A3 reproduction check: {json.dumps(reference_check, ensure_ascii=False)}")
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
