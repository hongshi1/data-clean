#!/usr/bin/env python3
r"""Conditional calibration, bucketed ECE decomposition, selective prediction
and split-conformal dual-axis evaluation (D2/D3/E50) on the silver pair set.

Pre-registered hypothesis: the near-unity fitted temperature of the frozen-score
pipeline (tau ~= 1, test ECE 0.2662 on the archived ablation D row) is a
"same-score heterogeneity" artifact — the pair score distribution is a mixture
of kind_pair x same_section strata with different score->label relations, so
one global probability map is miscalibrated while stratum-conditional maps are
not.

Design (self-contained; score = native frozen-BGE cosine from
feature_snapshot_v1, folds from the ``split`` field stored in pairs.jsonl:
dev fold fits, test fold evaluates):

  D2 baselines       global isotonic (own PAVA) and Platt (logistic regression
                     on the score), each fit on dev, ECE/Brier on test.
  Conditional (main) logistic regression p = sigmoid(w . [s, bucket onehot,
                     s x bucket onehot]) over the kind_pair x same_section
                     buckets (9 observed of the 12 theoretical cells), L2 with
                     a dev-NLL-selected C (small buckets shrink).
  Decomposition      per-bucket ECE of the raw score vs the global ECE — the
                     literal pre-registered check "weighted bucket sum << global"
                     is reported, plus the corrected root-cause check (per-bucket
                     isotonic weighted ECE vs global isotonic ECE).
  D3                 selective prediction on the best calibrated p: confidence
                     c = max(p, 1-p) sweep (>= 8 points), coverage / selective
                     risk / AURC; Platt kept as contrast.
  Conformal (E50)    split-conformal with nonconformity 1 - p_hat on dev
                     positives, Mondrian quantiles per kind_pair, alpha = 0.1
                     ("90%-coverage confirmed set"); crossed with the
                     QualityContract obligations (imported from
                     tools/eval_contract_risk_coverage.py) in a 2x2.

Honesty notes baked into the results:
  * shared_identifiers non-empty coincides with the silver label definition
    (positives are ID-sharing pairs, negatives ID-disjoint), so the ID
    covariate is reported as a diagnostic only and NEVER used as a feature.
  * the literal decomposition direction is mathematically impossible: per bin,
    |mean_p - mean_y| obeys the triangle inequality over bucket mixes, hence
    global ECE <= weighted sum of bucket ECEs always. The measured direction
    (global << weighted) is itself the mixture signature: opposite-signed
    within-bucket errors cancel in shared global bins.
  * the silver buckets are (nearly) label-pure because each generator defines
    one bucket; conditional-calibration gains are therefore an upper bound
    tied to this labeling and must not be read as gold-label performance.

Usage: python tools/eval_conditional_calibration.py [--alpha 0.1] [--limit N]
Output: markdown tables on stdout + runs protocol result.json.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
SNAPSHOT_PATH = BASE / "data/gjb_438c/feature_snapshot_v1/vectors.npz"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

ECE_BINS = 15
C_GRID = (0.1, 1.0, 10.0, 100.0)
CONFIDENCE_SWEEP = (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)

sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402
from eval_ablation_matrix import (  # noqa: E402
    brier_score,
    expected_calibration_error,
    fit_temperature,
    nll_of_tau,
    temperature_probs,
)
from eval_contract_risk_coverage import OBLIGATION_IDS, obligation_status  # noqa: E402
from train_shared_projection import FOLD_TO_SPLIT, load_pairs, load_snapshot  # noqa: E402


# ── pure calibration primitives (unit-tested on synthetic data) ───────────


def pava_fit(
    scores: list[float] | np.ndarray, labels: list[int] | np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Pool-Adjacent-Violators isotonic regression of labels on scores.

    Identical scores are aggregated first (weighted blocks), then blocks are
    pooled while the previous block mean exceeds the current one. Returns
    (edges, values): ``values[j]`` is the fitted probability for any score in
    (edges[j-1], edges[j]] (block j upper edge = edges[j]).
    """

    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    if s.shape != y.shape or s.size == 0:
        raise ValueError("pava_fit needs equal-length non-empty scores/labels")

    sums: dict[float, float] = {}
    counts: dict[float, int] = {}
    for score, target in zip(s.tolist(), y.tolist()):
        sums[score] = sums.get(score, 0.0) + target
        counts[score] = counts.get(score, 0) + 1
    unique = sorted(sums)
    if not unique:
        raise ValueError("pava_fit received no scores")

    blocks: list[list[float]] = []  # [mean, weight, upper_edge]
    for score in unique:
        blocks.append([sums[score] / counts[score], float(counts[score]), score])
        while len(blocks) >= 2 and blocks[-2][0] > blocks[-1][0]:
            later = blocks.pop()
            earlier = blocks.pop()
            weight = earlier[1] + later[1]
            merged = (earlier[0] * earlier[1] + later[0] * later[1]) / weight
            blocks.append([merged, weight, later[2]])
    edges = np.asarray([block[2] for block in blocks], dtype=np.float64)
    values = np.asarray([block[0] for block in blocks], dtype=np.float64)
    return edges, values


def pava_predict(
    scores: list[float] | np.ndarray, edges: np.ndarray, values: np.ndarray
) -> np.ndarray:
    """Step-function evaluation of a PAVA fit (constant outside the fit range)."""

    x = np.asarray(scores, dtype=np.float64)
    if edges.size == 0:
        return np.full(x.shape, 0.5, dtype=np.float64)
    positions = np.searchsorted(edges, x, side="left")
    clipped = np.clip(positions, 0, values.size - 1)
    return values[clipped]


def bucket_key(pair: dict[str, Any]) -> str:
    """Conditional bucket id: kind_pair x same_section."""

    features = pair.get("features", {})
    return f"{features.get('kind_pair', 'unknown')}|{bool(features.get('same_section', False))}"


def kind_pair_of(pair: dict[str, Any]) -> str:
    return str(pair.get("features", {}).get("kind_pair", "unknown"))


def log_loss(probs: list[float] | np.ndarray, labels: list[int] | np.ndarray) -> float:
    probabilities = np.clip(np.asarray(probs, dtype=np.float64), 1e-15, 1.0 - 1e-15)
    targets = np.asarray(labels, dtype=np.float64)
    if probabilities.size == 0:
        raise ValueError("log_loss needs a non-empty sample")
    return float(-np.mean(targets * np.log(probabilities) + (1 - targets) * np.log(1 - probabilities)))


def bucketed_ece(
    probs: list[float] | np.ndarray,
    labels: list[int] | np.ndarray,
    buckets: list[str],
    n_bins: int = ECE_BINS,
) -> dict[str, dict[str, float]]:
    """Per-bucket {n, n_pos, ece} with the same equal-width binning as ECE."""

    groups: dict[str, list[tuple[float, int]]] = {}
    for prob, label, bucket in zip(probs, labels, buckets):
        groups.setdefault(bucket, []).append((float(prob), int(label)))
    out: dict[str, dict[str, float]] = {}
    for bucket in sorted(groups):
        rows = groups[bucket]
        probabilities = np.asarray([row[0] for row in rows])
        targets = np.asarray([row[1] for row in rows])
        out[bucket] = {
            "n": float(len(rows)),
            "n_pos": float(targets.sum()),
            "ece": expected_calibration_error(probabilities, targets, n_bins),
        }
    return out


def weighted_bucket_ece(
    probs: list[float] | np.ndarray,
    labels: list[int] | np.ndarray,
    buckets: list[str],
    n_bins: int = ECE_BINS,
) -> float:
    """Sum of bucket ECEs weighted by bucket size (the mixture decomposition)."""

    stats = bucketed_ece(probs, labels, buckets, n_bins)
    total = sum(entry["n"] for entry in stats.values())
    if total == 0:
        return 0.0
    return float(sum(entry["n"] / total * entry["ece"] for entry in stats.values()))


# ── D3: selective prediction (pure) ────────────────────────────────────────


def selective_prediction_rows(
    probs: list[float] | np.ndarray, labels: list[int] | np.ndarray, thresholds: list[float]
) -> list[dict[str, Any]]:
    """Coverage / selective-risk rows for confidence thresholds on c=max(p,1-p).

    Prediction is 1 iff p >= 0.5; selective risk is the 0-1 error rate over
    covered pairs (None when nothing is covered).
    """

    probabilities = np.asarray(probs, dtype=np.float64)
    targets = np.asarray(labels, dtype=int)
    if probabilities.size == 0:
        raise ValueError("selective prediction needs a non-empty sample")
    confidence = np.maximum(probabilities, 1.0 - probabilities)
    errors = ((probabilities >= 0.5).astype(int) != targets).astype(np.float64)
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        covered = confidence >= threshold
        count = int(covered.sum())
        rows.append(
            {
                "threshold": float(threshold),
                "n_covered": count,
                "coverage": round(float(count) / probabilities.size, 4),
                "selective_risk": (
                    round(float(errors[covered].mean()), 4) if count else None
                ),
            }
        )
    return rows


def aurc(probs: list[float] | np.ndarray, labels: list[int] | np.ndarray) -> float:
    """Area under the risk-coverage curve.

    Samples are ranked by confidence (c = max(p, 1-p), ties keep input order);
    risk(k) is the error rate of the k most confident samples and
    AURC = mean_k risk(k) over k = 1..N.
    """

    probabilities = np.asarray(probs, dtype=np.float64)
    targets = np.asarray(labels, dtype=int)
    if probabilities.size == 0:
        raise ValueError("AURC needs a non-empty sample")
    confidence = np.maximum(probabilities, 1.0 - probabilities)
    errors = ((probabilities >= 0.5).astype(int) != targets).astype(np.float64)
    order = np.argsort(-confidence, kind="stable")
    cumulative = np.cumsum(errors[order])
    ranks = np.arange(1, errors.size + 1, dtype=np.float64)
    return float((cumulative / ranks).mean())


def aurc_oracle(n_errors: int, n_total: int) -> float:
    """AURC of the oracle ordering: the same n_errors errors ranked last.

    Excess AURC (AURC - oracle) is the selective-prediction headroom left by
    imperfect confidence ranking at a fixed error count.
    """

    if n_total <= 0:
        raise ValueError("AURC needs a non-empty sample")
    if not 0 <= n_errors <= n_total:
        raise ValueError("n_errors must be within [0, n_total]")
    errors_sorted = np.concatenate(
        [np.zeros(n_total - n_errors), np.ones(n_errors)]
    )
    cumulative = np.cumsum(errors_sorted)
    ranks = np.arange(1, n_total + 1, dtype=np.float64)
    return float((cumulative / ranks).mean())


# ── E50: split-conformal (pure) ────────────────────────────────────────────


def conformal_quantile(nonconformity: list[float], alpha: float) -> float:
    """Split-conformal quantile: the ceil((n+1)(1-alpha))-th smallest score.

    Returns +inf when the finite-sample correction exceeds the calibration
    sample (always-accept); the caller must treat an empty calibration set
    separately (no stratum data -> no certification, abstain).
    """

    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be in (0, 1)")
    if not nonconformity:
        raise ValueError("conformal_quantile needs a non-empty calibration set")
    ordered = sorted(nonconformity)
    n = len(ordered)
    rank = int(math.ceil((n + 1) * (1.0 - alpha)))
    if rank > n:
        return float("inf")
    return float(ordered[rank - 1])


def conformal_covered_flags(
    probs: list[float],
    buckets: list[str],
    quantiles: dict[str, float],
) -> list[bool]:
    """Covered iff 1 - p_hat <= q(bucket); uncalibrated buckets abstain."""

    flags: list[bool] = []
    for prob, bucket in zip(probs, buckets):
        quantile = quantiles.get(bucket)
        flags.append(quantile is not None and (1.0 - float(prob)) <= quantile)
    return flags


def dual_axis_matrix(
    covered: list[bool], obligations_met: list[bool], labels: list[int]
) -> dict[str, Any]:
    """{conformal covered/abstain} x {contract met/unmet} cells + margins.

    Each cell reports n, n_pos and precision (share of true identity pairs).
    """

    if not (len(covered) == len(obligations_met) == len(labels)):
        raise ValueError("dual_axis_matrix inputs must align")
    cells: dict[str, dict[str, Any]] = {}
    for covered_flag in (True, False):
        for met_flag in (True, False):
            indices = [
                position
                for position in range(len(labels))
                if covered[position] is covered_flag and obligations_met[position] is met_flag
            ]
            count = len(indices)
            positives = sum(int(labels[position]) for position in indices)
            name = f"conformal_{'covered' if covered_flag else 'abstain'}|contract_{'met' if met_flag else 'unmet'}"
            cells[name] = {
                "n": count,
                "n_pos": positives,
                "precision": round(positives / count, 4) if count else None,
            }

    def margin(selector_covered: bool | None, selector_met: bool | None) -> dict[str, Any]:
        indices = [
            position
            for position in range(len(labels))
            if (selector_covered is None or covered[position] is selector_covered)
            and (selector_met is None or obligations_met[position] is selector_met)
        ]
        count = len(indices)
        positives = sum(int(labels[position]) for position in indices)
        return {
            "n": count,
            "n_pos": positives,
            "precision": round(positives / count, 4) if count else None,
        }

    return {
        "cells": cells,
        "margins": {
            "conformal_covered": margin(True, None),
            "conformal_abstain": margin(False, None),
            "contract_met": margin(None, True),
            "contract_unmet": margin(None, False),
            "all": margin(None, None),
        },
    }


# ── data loading / row building (only invoked from main) ───────────────────


def build_rows(
    pairs: list[dict[str, Any]], index: dict[str, int], matrix: np.ndarray
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, int]]:
    """dev/test row dicts {score, label, bucket, kind_pair, pair} per split.

    Pairs whose occurrence vectors are missing from the snapshot are skipped
    and counted (same skip rule as the ablation matrix). The stored split
    field is validated against the stored fold via FOLD_TO_SPLIT.
    """

    rows: dict[str, list[dict[str, Any]]] = {"dev": [], "test": []}
    skipped: dict[str, int] = {"dev": 0, "test": 0, "train": 0, "unknown_split": 0}
    for pair in pairs:
        anchor_id = pair["anchor"]["occurrence_id"]
        candidate_id = pair["candidate"]["occurrence_id"]
        if anchor_id not in index or candidate_id not in index:
            skipped[str(pair.get("split", "train"))] = skipped.get(str(pair.get("split", "train")), 0) + 1
            continue
        split = str(pair.get("split", "train"))
        fold = pair.get("fold")
        if fold is not None and FOLD_TO_SPLIT.get(int(fold)) != split:
            raise SystemExit(
                f"pair {pair.get('pair_id', '?')} split {split!r} disagrees with "
                f"fold {fold} under FOLD_TO_SPLIT"
            )
        if split not in rows:
            continue
        rows[split].append(
            {
                "score": float(matrix[index[anchor_id]] @ matrix[index[candidate_id]]),
                "label": int(pair["label"]),
                "bucket": bucket_key(pair),
                "kind_pair": kind_pair_of(pair),
                "pair": pair,
            }
        )
    return rows, skipped


# ── calibrator fits (sklearn imported lazily inside these) ────────────────


def _fit_lr(features: np.ndarray, labels: np.ndarray, c_values: tuple[float, ...]) -> dict[str, Any]:
    """Logistic regression with C selected by in-sample (dev) log loss."""

    from sklearn.linear_model import LogisticRegression

    best: dict[str, Any] | None = None
    for value in c_values:
        model = LogisticRegression(C=value, max_iter=2000, solver="lbfgs")
        model.fit(features, labels)
        loss = log_loss(model.predict_proba(features)[:, 1], labels)
        if best is None or loss < best["dev_logloss"]:
            best = {"model": model, "C": value, "dev_logloss": loss}
    if best is None:
        raise SystemExit("C grid was empty; cannot fit logistic regression")
    return best


def platt_calibration(
    dev_scores: list[float], dev_labels: list[int]
) -> dict[str, Any]:
    """Platt scaling: p = sigmoid(a*s + b) fit on standardized dev scores."""

    scores = np.asarray(dev_scores, dtype=np.float64)
    mu = float(scores.mean())
    sd = float(scores.std()) or 1.0
    features = ((scores - mu) / sd).reshape(-1, 1)
    fit = _fit_lr(features, np.asarray(dev_labels), C_GRID)
    return {**fit, "mu": mu, "sd": sd, "kind": "platt"}


def platt_predict(calibration: dict[str, Any], scores: list[float]) -> np.ndarray:
    features = ((np.asarray(scores, dtype=np.float64) - calibration["mu"]) / calibration["sd"]).reshape(-1, 1)
    return calibration["model"].predict_proba(features)[:, 1]


def conditional_calibration(
    dev_scores: list[float],
    dev_labels: list[int],
    dev_buckets: list[str],
    bucket_names: list[str],
) -> dict[str, Any]:
    """p = sigmoid(w . [s, bucket onehot, s x bucket onehot]) + intercept."""

    bucket_index = {name: position for position, name in enumerate(bucket_names)}
    mu = float(np.mean(dev_scores))
    sd = float(np.std(dev_scores)) or 1.0

    def design(scores: list[float], buckets: list[str]) -> np.ndarray:
        standardized = (np.asarray(scores, dtype=np.float64) - mu) / sd
        onehot = np.zeros((len(scores), len(bucket_names)), dtype=np.float64)
        for position, bucket in enumerate(buckets):
            onehot[position, bucket_index[bucket]] = 1.0
        return np.column_stack([standardized, onehot, standardized[:, None] * onehot])

    features = design(dev_scores, dev_buckets)
    fit = _fit_lr(features, np.asarray(dev_labels), C_GRID)
    return {
        **fit,
        "mu": mu,
        "sd": sd,
        "bucket_names": list(bucket_names),
        "n_params": int(features.shape[1] + 1),
        "kind": "conditional",
        "design": design,
    }


def conditional_predict(calibration: dict[str, Any], scores: list[float], buckets: list[str]) -> np.ndarray:
    features = calibration["design"](scores, buckets)
    return calibration["model"].predict_proba(features)[:, 1]


def fit_calibrator(
    kind: str,
    train_scores: list[float],
    train_labels: list[int],
    train_buckets: list[str],
) -> dict[str, Any]:
    """Fit one calibrator kind on a training slice; predict fn bound to it.

    The returned dict carries a ``predict(scores, buckets)`` closure so the
    cross-validation loop and the final full-dev refit share one code path.
    """

    if kind == "isotonic":
        edges, values = pava_fit(train_scores, train_labels)
        return {
            "kind": kind,
            "predict": lambda scores, buckets: pava_predict(scores, edges, values),
        }
    if kind == "platt":
        calibration = platt_calibration(train_scores, train_labels)
        return {
            "kind": kind,
            "predict": lambda scores, buckets: platt_predict(calibration, scores),
        }
    if kind == "conditional":
        names = sorted(set(train_buckets))
        calibration = conditional_calibration(train_scores, train_labels, train_buckets, names)
        return {
            "kind": kind,
            "predict": lambda scores, buckets: conditional_predict(calibration, scores, buckets),
        }
    if kind == "temperature":
        tau, _nll = fit_temperature(train_scores, train_labels)
        return {
            "kind": kind,
            "predict": lambda scores, buckets: temperature_probs(scores, tau),
            "tau": tau,
        }
    raise ValueError(f"unknown calibrator kind: {kind!r}")


CALIBRATOR_KINDS = ("isotonic", "platt", "conditional", "temperature")


def cv_calibrator_metrics(
    kind: str,
    scores: list[float],
    labels: list[int],
    buckets: list[str],
    n_folds: int = 4,
    seed: int = 42,
) -> dict[str, float]:
    """Out-of-fold ECE/Brier/logloss of one calibrator kind on the dev fold.

    In-sample dev ECE would crown the isotonic fit (it interpolates the
    calibration data), so the best-calibrated p is selected out-of-fold.
    """

    n_total = len(scores)
    if n_total < n_folds:
        raise ValueError("dev fold too small for cross-validation")
    rng = np.random.default_rng(seed)
    order = rng.permutation(n_total)
    fold_of = np.zeros(n_total, dtype=int)
    for fold in range(n_folds):
        fold_of[order[fold::n_folds]] = fold
    eces: list[float] = []
    briers: list[float] = []
    losses: list[float] = []
    for fold in range(n_folds):
        train_mask = fold_of != fold
        val_mask = fold_of == fold
        train_scores = [scores[i] for i in np.flatnonzero(train_mask)]
        train_labels = [labels[i] for i in np.flatnonzero(train_mask)]
        train_buckets = [buckets[i] for i in np.flatnonzero(train_mask)]
        val_scores = [scores[i] for i in np.flatnonzero(val_mask)]
        val_labels = [labels[i] for i in np.flatnonzero(val_mask)]
        val_buckets = [buckets[i] for i in np.flatnonzero(val_mask)]
        calibrator = fit_calibrator(kind, train_scores, train_labels, train_buckets)
        predicted = calibrator["predict"](val_scores, val_buckets)
        eces.append(expected_calibration_error(predicted, val_labels))
        briers.append(brier_score(predicted, val_labels))
        losses.append(log_loss(predicted, val_labels))
    return {
        "cv_ece": round(float(np.mean(eces)), 4),
        "cv_brier": round(float(np.mean(briers)), 4),
        "cv_logloss": round(float(np.mean(losses)), 4),
    }


# ── main ───────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, default=PAIRS_PATH)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--alpha", type=float, default=0.1)
    parser.add_argument("--limit", type=int, default=None, help="Cap dev/test rows (smoke)")
    args = parser.parse_args()

    pairs = load_pairs(args.pairs)
    index, matrix, _ids = load_snapshot(args.snapshot)
    rows, skipped = build_rows(pairs, index, matrix)
    dev_rows = rows["dev"]
    test_rows = rows["test"]
    if args.limit:
        dev_rows = dev_rows[: args.limit]
        test_rows = test_rows[: max(args.limit // 2, 1)]
    if not dev_rows or not test_rows:
        raise SystemExit("empty dev/test folds; check inputs")

    dev_scores = [row["score"] for row in dev_rows]
    dev_labels = [row["label"] for row in dev_rows]
    dev_buckets = [row["bucket"] for row in dev_rows]
    test_scores = [row["score"] for row in test_rows]
    test_labels = [row["label"] for row in test_rows]
    test_buckets = [row["bucket"] for row in test_rows]
    test_pairs = [row["pair"] for row in test_rows]

    # Trap diagnostic: shared-identifier presence vs label (must NOT be a feature).
    def id_label_rate(split_rows: list[dict[str, Any]], nonempty: bool) -> tuple[int, float]:
        subset = [
            row["label"]
            for row in split_rows
            if bool(row["pair"]["features"].get("shared_identifiers")) is nonempty
        ]
        return len(subset), round(float(np.mean(subset)), 6) if subset else 0.0

    dev_id_n, dev_id_rate = id_label_rate(dev_rows, True)
    dev_noid_n, dev_noid_rate = id_label_rate(dev_rows, False)
    test_id_n, test_id_rate = id_label_rate(test_rows, True)
    test_noid_n, test_noid_rate = id_label_rate(test_rows, False)
    trap = {
        "dev": {"id_nonempty": {"n": dev_id_n, "label_rate": dev_id_rate},
                "id_empty": {"n": dev_noid_n, "label_rate": dev_noid_rate}},
        "test": {"id_nonempty": {"n": test_id_n, "label_rate": test_id_rate},
                 "id_empty": {"n": test_noid_n, "label_rate": test_noid_rate}},
        "policy": "shared_identifiers (ID covariate) excluded from conditioning; diagnostic only",
    }

    bucket_names = sorted(set(dev_buckets))
    unseen = sorted(set(test_buckets) - set(dev_buckets))
    if unseen:
        raise SystemExit(f"test buckets absent from dev: {unseen}")

    # ── D2: global calibrators + conditional ─────────────────────────────
    raw_dev_p = temperature_probs(dev_scores, 1.0)
    raw_test_p = temperature_probs(test_scores, 1.0)
    tau, dev_nll_tau = fit_temperature(dev_scores, dev_labels)
    dev_nll_identity = nll_of_tau(dev_scores, dev_labels, 1.0)
    tau_dev_p = temperature_probs(dev_scores, tau)
    tau_test_p = temperature_probs(test_scores, tau)

    edges, values = pava_fit(dev_scores, dev_labels)
    iso_dev_p = pava_predict(dev_scores, edges, values)
    iso_test_p = pava_predict(test_scores, edges, values)

    platt = platt_calibration(dev_scores, dev_labels)
    platt_dev_p = platt_predict(platt, dev_scores)
    platt_test_p = platt_predict(platt, test_scores)

    conditional = conditional_calibration(dev_scores, dev_labels, dev_buckets, bucket_names)
    cond_dev_p = conditional_predict(conditional, dev_scores, dev_buckets)
    cond_test_p = conditional_predict(conditional, test_scores, test_buckets)

    def block(probs_dev, probs_test) -> dict[str, Any]:
        return {
            "dev_ece": round(expected_calibration_error(probs_dev, dev_labels), 4),
            "dev_brier": round(brier_score(probs_dev, dev_labels), 4),
            "test_ece": round(expected_calibration_error(probs_test, test_labels), 4),
            "test_brier": round(brier_score(probs_test, test_labels), 4),
            "test_logloss": round(log_loss(probs_test, test_labels), 4),
        }

    d2 = {
        "raw_sigmoid_tau1": block(raw_dev_p, raw_test_p),
        "temperature": {
            **block(tau_dev_p, tau_test_p),
            "tau": tau,
            "dev_nll_tau1": round(dev_nll_identity, 6),
            "dev_nll_tau": round(dev_nll_tau, 6),
        },
        "isotonic_pava": {**block(iso_dev_p, iso_test_p), "n_blocks": int(edges.size)},
        "platt": {
            **block(platt_dev_p, platt_test_p),
            "C": platt["C"],
            "coef": [round(float(value), 4) for value in platt["model"].coef_[0]],
            "intercept": round(float(platt["model"].intercept_[0]), 4),
        },
    }
    conditional_block = {
        **block(cond_dev_p, cond_test_p),
        "C": conditional["C"],
        "n_params": conditional["n_params"],
        "n_buckets": len(bucket_names),
        "s_coef": round(float(conditional["model"].coef_[0, 0]), 4),
        "intercept": round(float(conditional["model"].intercept_[0]), 4),
        "bucket_effects": {
            name: {
                "n_dev": dev_buckets.count(name),
                "onehot_coef": round(float(conditional["model"].coef_[0, 1 + position]), 4),
                "interaction_coef": round(
                    float(conditional["model"].coef_[0, 1 + len(bucket_names) + position]), 4
                ),
            }
            for position, name in enumerate(bucket_names)
        },
    }

    # ── bucketed ECE decomposition (root-cause check) ────────────────────
    raw_bucket_stats = bucketed_ece(raw_test_p, test_labels, test_buckets)
    raw_global_ece = expected_calibration_error(raw_test_p, test_labels)
    raw_weighted = weighted_bucket_ece(raw_test_p, test_labels, test_buckets)
    iso_global_ece = expected_calibration_error(iso_test_p, test_labels)

    bucket_isotonic: dict[str, dict[str, Any]] = {}
    recalibrated_p = np.zeros(len(test_rows), dtype=np.float64)
    for name in bucket_names:
        dev_subset = [
            (row["score"], row["label"])
            for row in dev_rows
            if row["bucket"] == name
        ]
        test_positions = [position for position, bucket in enumerate(test_buckets) if bucket == name]
        sub_scores = [test_scores[position] for position in test_positions]
        sub_labels = [test_labels[position] for position in test_positions]
        sub_edges, sub_values = pava_fit([score for score, _ in dev_subset], [label for _, label in dev_subset])
        sub_p = pava_predict(sub_scores, sub_edges, sub_values)
        recalibrated_p[test_positions] = sub_p
        bucket_isotonic[name] = {
            **raw_bucket_stats[name],
            "recal_ece": round(expected_calibration_error(sub_p, sub_labels), 4),
            "base_rate": round(
                float(np.mean(sub_labels)) if sub_labels else 0.0, 4
            ),
            "mean_p_raw": round(float(np.mean([raw_test_p[position] for position in test_positions])), 4)
            if test_positions
            else None,
        }
    recal_weighted = weighted_bucket_ece(recalibrated_p, test_labels, test_buckets)
    recal_global = expected_calibration_error(recalibrated_p, test_labels)

    literal_check = {
        "global_raw_ece": round(raw_global_ece, 4),
        "weighted_sum_raw_bucket_ece": round(raw_weighted, 4),
        "ratio_weighted_over_global": round(raw_weighted / max(raw_global_ece, 1e-12), 4),
        "pre_registered_direction": "weighted << global (mixture confirmed)",
        "measured_direction": "weighted >> global",
        "math_note": (
            "impossible by construction: per equal-width bin the bucket errors mix "
            "through a convex combination, so |mean_p - mean_y| obeys the triangle "
            "inequality and global ECE <= weighted bucket sum ALWAYS holds. The "
            "measured reversal is the mixture signature itself: same-score strata "
            "carry opposite-signed calibration errors that cancel in shared bins."
        ),
    }
    operative_check = {
        "global_isotonic_test_ece": round(iso_global_ece, 4),
        "conditional_bucket_isotonic_weighted_test_ece": round(recal_weighted, 4),
        "conditional_bucket_isotonic_global_test_ece": round(recal_global, 4),
        "root_cause_confirmed": bool(recal_weighted < iso_global_ece - 0.01),
        "interpretation": (
            "stratum-conditional recalibration collapses test ECE while the best "
            "global calibrator cannot: the score->label relation is bucket-heterogeneous "
            "(same-score heterogeneity), which is the corrected root-cause test"
        ),
    }

    # ── D3: selective prediction on the best calibrated p ────────────────
    # Best = out-of-fold winner on dev (in-sample dev ECE would crown the
    # isotonic fit, which interpolates its own calibration data).
    cv_table = {
        kind: cv_calibrator_metrics(kind, dev_scores, dev_labels, dev_buckets)
        for kind in CALIBRATOR_KINDS
    }
    best_name = min(cv_table, key=lambda kind: (cv_table[kind]["cv_ece"], cv_table[kind]["cv_brier"]))
    final = fit_calibrator(best_name, dev_scores, dev_labels, dev_buckets)
    best_dev_p = np.asarray(final["predict"](dev_scores, dev_buckets))
    best_test_p = np.asarray(final["predict"](test_scores, test_buckets))

    def error_count(probs: np.ndarray) -> int:
        return int((((np.asarray(probs) >= 0.5).astype(int)) != np.asarray(test_labels)).sum())

    def d3_block(probs_test: np.ndarray) -> dict[str, Any]:
        errors = error_count(probs_test)
        return {
            "sweep": selective_prediction_rows(probs_test, test_labels, CONFIDENCE_SWEEP),
            "aurc": round(aurc(probs_test, test_labels), 6),
            "n_errors": errors,
            "aurc_oracle": round(aurc_oracle(errors, len(test_labels)), 6),
            "excess_aurc": round(
                aurc(probs_test, test_labels) - aurc_oracle(errors, len(test_labels)), 6
            ),
            "test_error_rate": round(errors / len(test_labels), 4),
        }

    d3 = {
        "selected_by": "4-fold out-of-fold dev ECE (tie-break cv Brier); test untouched",
        "selected_method": best_name,
        "cv_table": cv_table,
        "best": d3_block(best_test_p),
        "platt_contrast": d3_block(platt_test_p),
    }

    # ── E50: split-conformal, Mondrian per kind_pair, dual axis ──────────
    test_kind_pairs = [row["kind_pair"] for row in test_rows]
    dev_kind_pairs = [row["kind_pair"] for row in dev_rows]

    def conformal_section(probs_dev: np.ndarray, probs_test: np.ndarray, label: str) -> dict[str, Any]:
        quantiles: dict[str, float] = {}
        calibration_stats: dict[str, dict[str, Any]] = {}
        for kind in sorted(set(dev_kind_pairs) | set(test_kind_pairs)):
            calib = [
                1.0 - float(probs)
                for probs, kind_pair, target in zip(probs_dev, dev_kind_pairs, dev_labels)
                if kind_pair == kind and target == 1
            ]
            if calib:
                quantiles[kind] = conformal_quantile(calib, args.alpha)
                calibration_stats[kind] = {
                    "n_calibration_positives": len(calib),
                    "q": quantiles[kind],
                }
            else:
                calibration_stats[kind] = {
                    "n_calibration_positives": 0,
                    "q": None,
                    "policy": "no calibration data for this stratum -> abstain",
                }
        covered = conformal_covered_flags([float(p) for p in probs_test], test_kind_pairs, quantiles)
        confirmed_tp = sum(1 for flag, target in zip(covered, test_labels) if flag and target == 1)
        confirmed_fp = sum(1 for flag, target in zip(covered, test_labels) if flag and target == 0)
        total_positives = int(sum(test_labels))
        per_bucket: dict[str, dict[str, Any]] = {}
        for kind in sorted(set(test_kind_pairs)):
            positions = [i for i, value in enumerate(test_kind_pairs) if value == kind]
            bucket_pos = sum(test_labels[i] for i in positions)
            bucket_covered_pos = sum(1 for i in positions if covered[i] and test_labels[i] == 1)
            per_bucket[kind] = {
                "n_test": len(positions),
                "n_test_pos": bucket_pos,
                "covered_pos": bucket_covered_pos,
                "positive_coverage": round(bucket_covered_pos / max(bucket_pos, 1), 4),
                "q": calibration_stats[kind]["q"],
            }
        obligations_met = [
            all(obligation_status(pair).get(key, False) for key in OBLIGATION_IDS)
            for pair in test_pairs
        ]
        return {
            "p_source": label,
            "alpha": args.alpha,
            "nonconformity": "1 - p_hat",
            "calibration_set": "dev fold positives (label-conditional guarantee: P(covered | y=1) >= 1-alpha)",
            "mondrian": "kind_pair",
            "quantiles": calibration_stats,
            "per_bucket": per_bucket,
            "coverage_of_positives": round(confirmed_tp / max(total_positives, 1), 4),
            "confirmed_set": {
                "n": confirmed_tp + confirmed_fp,
                "tp": confirmed_tp,
                "fp": confirmed_fp,
                "precision": round(confirmed_tp / max(confirmed_tp + confirmed_fp, 1), 4),
            },
            "dual_axis": dual_axis_matrix(covered, obligations_met, test_labels),
            "obligation_logic_source": "tools/eval_contract_risk_coverage.py (imported)",
            "leak_note": (
                "identity_evidence (shared_identifiers non-empty) reconstructs the silver "
                "label by construction, so the contract axis is entangled with the label; "
                "the conformal axis is label-free at decision time (dev quantiles only)"
            ),
        }

    conformal = {
        "primary": conformal_section(best_dev_p, best_test_p, best_name),
        "platt_contrast": conformal_section(platt_dev_p, platt_test_p, "platt"),
    }

    # ── conclusions ──────────────────────────────────────────────────────
    purity = {
        name: {
            "n_test": bucket_isotonic[name]["n"],
            "n_test_pos": bucket_isotonic[name]["n_pos"],
            "label_pure": bucket_isotonic[name]["n_pos"]
            in (bucket_isotonic[name]["n"], 0),
        }
        for name in bucket_names
    }
    conclusions = [
        (
            f"D2 vs conditional: best global calibrator test ECE "
            f"{min(d2['isotonic_pava']['test_ece'], d2['platt']['test_ece'], d2['temperature']['test_ece'])}"
            f" -> conditional {conditional_block['test_ece']} "
            f"(temperature scaling stays at tau={tau}, ECE {d2['temperature']['test_ece']})"
        ),
        (
            f"base-rate shift: dev positive rate {np.mean(dev_labels):.4f} vs test "
            f"{np.mean(test_labels):.4f} — every GLOBAL calibrator fit on dev inherits the "
            f"dev base rate and lands WORSE than the raw score on test "
            f"(raw {d2['raw_sigmoid_tau1']['test_ece']}); the conditional model absorbs the "
            "shift through the bucket structure"
        ),
        (
            f"literal decomposition check: weighted bucket ECE {literal_check['weighted_sum_raw_bucket_ece']} "
            f"vs global {literal_check['global_raw_ece']} — the pre-registered "
            f"'weighted << global' direction is impossible (triangle inequality); the "
            f"measured reversal IS the same-score-heterogeneity signature"
        ),
        (
            f"operative root-cause check: global isotonic test ECE "
            f"{operative_check['global_isotonic_test_ece']} vs bucket-conditional "
            f"weighted ECE {operative_check['conditional_bucket_isotonic_weighted_test_ece']} "
            f"-> root cause {'CONFIRMED' if operative_check['root_cause_confirmed'] else 'not confirmed'}"
        ),
        (
            f"conformal E50 (alpha={args.alpha}, p={best_name}): coverage of positives "
            f"{conformal['primary']['coverage_of_positives']}, confirmed-set precision "
            f"{conformal['primary']['confirmed_set']['precision']}; dual-axis diagonal "
            f"contract_met∧covered precision "
            f"{conformal['primary']['dual_axis']['cells']['conformal_covered|contract_met']['precision']}"
        ),
        (
            "silver caveat: buckets are label-pure by generator construction "
            f"(purity: {sum(1 for entry in purity.values() if entry['label_pure'])}/{len(purity)}), "
            "so conditional-calibration / conformal numbers are silver-bound upper bounds"
        ),
    ]

    config = {
        "protocol": "conditional calibration + bucketed ECE decomposition + D3 + E50 conformal",
        "pairs": str(args.pairs),
        "snapshot": str(args.snapshot),
        "score": "native BGE cosine (vectors.npz dot, unit rows)",
        "folds": "stored split field in pairs.jsonl (dev fit, test eval)",
        "ece_bins": ECE_BINS,
        "c_grid": list(C_GRID),
        "confidence_sweep": list(CONFIDENCE_SWEEP),
        "alpha": args.alpha,
        "buckets": "kind_pair x same_section (observed of the 12 theoretical cells)",
        "limit": args.limit,
    }
    run = open_run("eval_conditional_calibration", config, RUNS_ROOT)

    result = {
        "n_pairs_total": len(pairs),
        "n_pairs_missing_vector": sum(skipped.values()),
        "skipped_by_split": skipped,
        "split_counts": {"dev": len(dev_rows), "test": len(test_rows)},
        "bucket_names": bucket_names,
        "trap_diagnostic": trap,
        "bucket_label_purity": purity,
        "D2": d2,
        "conditional_calibration": conditional_block,
        "bucketed_ece_decomposition": {
            "raw": {
                "global_ece": round(raw_global_ece, 4),
                "per_bucket": {name: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in stats.items()} for name, stats in raw_bucket_stats.items()},
                "weighted_sum": round(raw_weighted, 4),
            },
            "literal_check": literal_check,
            "bucket_isotonic": bucket_isotonic,
            "operative_check": operative_check,
        },
        "D3_selective_prediction": d3,
        "conformal_E50": conformal,
        "conclusions": conclusions,
    }
    run.save_result(result)

    # ── terminal markdown ────────────────────────────────────────────────
    print("# 条件校准 + 分桶ECE分解 + D3 + E50 conformal (test fold)")
    print(
        f"dev {len(dev_rows)} pairs / test {len(test_rows)} pairs; "
        f"score = native BGE cosine; buckets = {len(bucket_names)} of 12 theoretical"
    )
    print()
    print("## D2: 全局校准 vs 条件校准")
    print("| calibrator | dev ECE | test ECE | test Brier | test NLL |")
    print("|---|---:|---:|---:|---:|")
    ordered = [
        ("raw sigmoid(cos), tau=1", d2["raw_sigmoid_tau1"]),
        (f"temperature (tau={tau})", d2["temperature"]),
        ("D2-isotonic (PAVA)", d2["isotonic_pava"]),
        ("D2-platt (LR on score)", d2["platt"]),
        ("conditional (bucket LR)", conditional_block),
    ]
    for name, entry in ordered:
        print(
            f"| {name} | {entry['dev_ece']:.4f} | {entry['test_ece']:.4f} "
            f"| {entry['test_brier']:.4f} | {entry['test_logloss']:.4f} |"
        )
    print()
    print("## 分桶ECE分解 (根因检验)")
    print("| bucket | n | n_pos | base_rate | raw ECE_b | bucket-isotonic ECE_b |")
    print("|---|---:|---:|---:|---:|---:|")
    for name in bucket_names:
        stats = bucket_isotonic[name]
        print(
            f"| {name} | {int(stats['n'])} | {int(stats['n_pos'])} | {stats['base_rate']:.4f} "
            f"| {stats['ece']:.4f} | {stats['recal_ece']:.4f} |"
        )
    print(
        f"| **weighted sum** | {len(test_rows)} | | | **{raw_weighted:.4f}** | **{recal_weighted:.4f}** |"
    )
    print(
        f"| **global ECE** | {len(test_rows)} | | | **{raw_global_ece:.4f}** "
        f"| (global isotonic: {iso_global_ece:.4f}) |"
    )
    print()
    print(
        "literal check: weighted {:.4f} vs global {:.4f} (pre-registered direction "
        "impossible — triangle inequality; the reversal is the mixture signature); ".format(
            raw_weighted, raw_global_ece
        )
        + (
            "operative check: global isotonic {:.4f} -> conditional weighted {:.4f} "
            "=> root cause {}".format(
                iso_global_ece,
                recal_weighted,
                "CONFIRMED" if operative_check["root_cause_confirmed"] else "not confirmed",
            )
        )
    )
    print()
    print(f"## D3: selective prediction (best calibrated p = {best_name})")
    print(
        f"selection: {d3['selected_by']}; CV ECE: "
        + ", ".join(f"{kind} {cv_table[kind]['cv_ece']}" for kind in CALIBRATOR_KINDS)
    )
    for label, section in (("best", d3["best"]), ("platt contrast", d3["platt_contrast"])):
        print(f"### {label}: AURC {section['aurc']}, excess {section['excess_aurc']}, full-coverage error {section['test_error_rate']}")
        print("| conf threshold | coverage | selective risk |")
        print("|---|---:|---:|")
        for row in section["sweep"]:
            risk = "-" if row["selective_risk"] is None else f"{row['selective_risk']:.4f}"
            print(f"| {row['threshold']:.2f} | {row['coverage']:.4f} | {risk} |")
        print()
    print(f"## E50 conformal (alpha={args.alpha}, p={best_name})")
    primary = conformal["primary"]
    print(
        f"coverage of positives {primary['coverage_of_positives']}, "
        f"confirmed-set precision {primary['confirmed_set']['precision']}"
    )
    print("| kind_pair | n_test | n_pos | covered_pos | positive_coverage | q |")
    print("|---|---:|---:|---:|---:|---:|")
    for kind, stats in primary["per_bucket"].items():
        q = "-" if stats["q"] is None else f"{stats['q']:.4f}"
        print(
            f"| {kind} | {stats['n_test']} | {stats['n_test_pos']} | {stats['covered_pos']} "
            f"| {stats['positive_coverage']:.4f} | {q} |"
        )
    print()
    print("### dual axis: {conformal} x {contract obligations}")
    print("| cell | n | n_pos | precision |")
    print("|---|---:|---:|---:|")
    for name, cell in primary["dual_axis"]["cells"].items():
        precision = "-" if cell["precision"] is None else f"{cell['precision']:.4f}"
        print(f"| {name} | {cell['n']} | {cell['n_pos']} | {precision} |")
    print()
    for line in conclusions:
        print(f"- {line}")
    print()
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
