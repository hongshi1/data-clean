#!/usr/bin/env python3
r"""B2/B4 late-interaction variants on the B1 protocol (ablation continuation).

The archived B1 row of tools/eval_ablation_matrix.py (BGE token-level
IDF-weighted MaxSim, test AUC 0.8479) stored no per-pair scores, so this
script recomputes the whole B-family self-contained on the identical balanced
test fold (fold map = the archived balance_folds assignment, 0=test 1=dev
2,3=train; 6848 test pairs) and only re-encodes the unique test-fold texts
(the same 646-text dedup as run_b1_late_interaction — same iteration order,
same IDF corpus of test texts + unique train texts, same tokenizer settings):

  B1-idf-max      reproduction control: IDF-weighted MaxSim
                  (score = sum_i w_i * max_j cos(q_i, d_j) / sum_i w_i)
  B2-topk3        doc-side max -> mean of the top-3 similarities, IDF kept
  B2-topk5        doc-side max -> mean of the top-5 similarities, IDF kept
  B2-noidf        IDF dropped (w = 1), original max aggregation
  B4-gate         best B-variant score min-max normalized, fused with the
                  structural gate (0.7*B + 0.3*structural_score; the gate
                  reuses algorithms/context_linking/alignment/structural_gate.py
                  via eval_ablation_matrix.gate_features_from_pair with
                  identifier_match forced False — the silver positives are
                  ID-sharing pairs, so identifier_match would leak the label)

Threshold protocol: every row calibrates its threshold in-fold on its own
test negatives (95th percentile) — identical to the B1 convention, so the
rows stay comparable with each other while F1/precision/recall remain
optimistic vs the A-rows (AUC is threshold-free and comparable).

Pre-registered interpretation rules against the archived references
(B1 0.8479 / A1 0.8774 / A4-clean 0.9114):
  |dAUC(B2, B1)| < 0.005  -> token-level aggregation does not adapt
  dAUC(B2, B1) <= +0.01   -> single-point noise band (no dev error bar in B)
  B4 < A4-clean            -> gate gain is orthogonal to the representation

Usage: python tools/eval_late_interaction_variants.py [--seed 42] [--limit N]
Output: markdown comparison table on stdout + runs protocol result.json.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
BGE_MODEL_DIR = BASE / "models/embedding/bge-large-zh-v1.5"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

GATE_ALPHA = 0.7
TOPK_VARIANTS = (3, 5)

# Archived eval_ablation_matrix references (run aacbb70e_20261022_080237).
ARCHIVED_REFS = {
    "B1_late_interaction": 0.8479,
    "A1_native": 0.8774,
    "A3_projection": 0.9193,
    "A4_projection_gate_clean": 0.9114,
    "A4_projection_gate_clean_f1": 0.5853,
    "B1_f1": 0.6924,
    "A4_projection_gate_clean_fm": 0.0164,
    "B1_fm": 0.0499,
}

sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402
from eval_ablation_matrix import (  # noqa: E402
    B1_IDF_TRAIN_SAMPLE,
    B1_MAX_TOKENS,
    DEFAULT_FOLD_MAP,
    build_rows,
    fuse_one,
    gate_features_from_pair,
    metrics_from_scores,
    parse_fold_map,
)
from train_shared_projection import load_pairs, load_snapshot, sweep_threshold  # noqa: E402
from algorithms.context_linking.alignment.late_interaction import (  # noqa: E402
    idf_weighted_maxsim,
)
from algorithms.common.bge_local import BgeLocal  # noqa: E402


# ── pure scoring primitives (unit-tested on synthetic token matrices) ─────


def _unit_rows(matrix: np.ndarray | list[list[float]]) -> np.ndarray:
    """Row-normalize a token matrix (same math as late_interaction)."""

    values = np.asarray(matrix, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("token matrices must be two-dimensional")
    if values.shape[0] == 0:
        return values
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    return values / np.maximum(norms, 1e-12)


def topk_weighted_maxsim(
    query_tokens: np.ndarray | list[list[float]],
    doc_tokens: np.ndarray | list[list[float]],
    idf: np.ndarray | list[float] | None,
    k: int,
) -> float:
    """IDF-weighted MaxSim with the doc-side max relaxed to a top-k mean.

    score = sum_i w_i * mean(top-k_j cos(q_i, d_j)) / sum_i w_i, where the
    mean runs over the k largest similarities (all of them when the doc side
    has fewer than k tokens); idf=None gives unweighted (w = 1). With k = 1
    this is exactly idf_weighted_maxsim.
    """

    if k < 1:
        raise ValueError("k must be a positive integer")
    if len(query_tokens) == 0 or len(doc_tokens) == 0:
        return 0.0
    query = _unit_rows(query_tokens)
    doc = _unit_rows(doc_tokens)
    if query.shape[0] == 0 or doc.shape[0] == 0:
        return 0.0
    if query.shape[1] != doc.shape[1]:
        raise ValueError("query and doc token dimensions must match")
    if idf is None:
        weights = np.ones(query.shape[0], dtype=np.float64)
    else:
        weights = np.asarray(idf, dtype=np.float64)
        if weights.ndim != 1 or weights.shape[0] != query.shape[0]:
            raise ValueError("idf must be a 1-D array matching the query token count")
    total = float(weights.sum())
    if total <= 0.0:
        return 0.0
    similarities = query @ doc.T
    take = min(k, similarities.shape[1])
    if take == similarities.shape[1]:
        top = similarities
    else:
        top = np.partition(similarities, -take, axis=1)[:, -take:]
    aggregated = top.mean(axis=1)
    return float((weights * aggregated).sum() / total)


def minmax_normalize(scores: list[float] | np.ndarray) -> np.ndarray:
    """Map scores to [0, 1]; a constant input maps to the 0.5 midpoint."""

    values = np.asarray(scores, dtype=np.float64)
    if values.size == 0:
        raise ValueError("minmax_normalize needs a non-empty score list")
    low = float(values.min())
    high = float(values.max())
    if high <= low:
        return np.full(values.shape, 0.5, dtype=np.float64)
    return (values - low) / (high - low)


def fuse_gate_scores(
    scores: list[float] | np.ndarray,
    pairs: list[dict[str, Any]],
    alpha: float = GATE_ALPHA,
) -> list[float]:
    """Min-max normalize, then fuse with the clean structural gate.

    identifier_match is forced False (leak prevention: silver positives are
    exactly the ID-sharing pairs, so identifier evidence would hand the gate
    the label).
    """

    normalized = minmax_normalize(scores)
    if len(pairs) != normalized.size:
        raise ValueError("scores and pairs must align")
    return [
        fuse_one(float(value), gate_features_from_pair(pair, use_identifier=False), alpha)
        for value, pair in zip(normalized, pairs)
    ]


def judge_variants(
    b1_auc: float,
    b2_best_name: str,
    b2_best_auc: float,
    b4_base_name: str,
    b4_base_auc: float,
    b4_auc: float,
    a4_clean_auc: float,
    a3_auc: float,
) -> dict[str, Any]:
    """Pre-registered interpretation rules (thresholds fixed before running)."""

    delta_b2 = b2_best_auc - b1_auc
    if abs(delta_b2) < 0.005:
        b2_rule = (
            "token不适配: |dAUC| < 0.005 — top-k聚合/去IDF不动ranking, "
            "token级信号对该任务无增益"
        )
    elif delta_b2 > 0.01:
        b2_rule = (
            "dAUC > +0.01: 超出预注册噪声带 — 但B协议为单test点+in-fold阈值, "
            "仍按单点估计对待, 需重采样验证"
        )
    elif delta_b2 > 0:
        b2_rule = (
            "单点噪声范围: +0.005 < dAUC <= +0.01 — B协议无dev误差棒, "
            "不足以宣称改进"
        )
    else:
        b2_rule = (
            "聚合松弛有害: dAUC = {:+.4f} — doc侧max→top-k均值/去IDF损害ranking: "
            "max捕获的是单个最匹配token的精确证据, top-k均值把它与弱匹配平均掉".format(
                delta_b2
            )
        )
    gate_gain_b = b4_auc - b4_base_auc
    gate_gain_a = a4_clean_auc - a3_auc
    if b4_auc < a4_clean_auc:
        b4_rule = (
            "B4 < A4-clean → 门控增益与表征正交: 门控叠加在B表征上不改变"
            "B<A的表征差距 (gate增益 B {:+.4f} vs A {:+.4f}); 表征质量主导".format(
                gate_gain_b, gate_gain_a
            )
        )
    else:
        b4_rule = (
            "B4 >= A4-clean → B表征+门控追平A4: 门控增益不与表征正交 "
            "(gate增益 B {:+.4f} vs A {:+.4f})".format(gate_gain_b, gate_gain_a)
        )
    return {
        "b2_vs_b1": {
            "best_b2_variant": b2_best_name,
            "delta_auc": round(delta_b2, 4),
            "rule": b2_rule,
        },
        "b4_vs_references": {
            "b4_base": b4_base_name,
            "b4_auc": round(b4_auc, 4),
            "a4_clean_auc": a4_clean_auc,
            "gate_gain_on_b": round(gate_gain_b, 4),
            "gate_gain_on_a_archived": round(gate_gain_a, 4),
            "rule": b4_rule,
        },
        "b_family_vs_a_family": {
            "best_b_auc": round(max(b1_auc, b2_best_auc, b4_auc), 4),
            "a1_native": ARCHIVED_REFS["A1_native"],
            "gap_to_a1": round(max(b1_auc, b2_best_auc, b4_auc) - ARCHIVED_REFS["A1_native"], 4),
        },
    }


# ── B1 protocol machinery (mirrors run_b1_late_interaction verbatim) ──────


def unique_texts(rows: list[dict[str, Any]]) -> list[str]:
    """Order-preserving dedup of anchor/candidate texts (same as B1)."""

    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        for side in ("anchor", "candidate"):
            text = str(row["pair"][side]["text"])
            if text and text not in seen:
                seen.add(text)
                ordered.append(text)
    return ordered


def encode_and_idf(
    bge: BgeLocal,
    model_dir: Path,
    test_rows: list[dict[str, Any]],
    train_rows: list[dict[str, Any]],
    seed: int,
) -> tuple[dict[str, Any], dict[str, list[int]], Any, dict[str, Any]]:
    """Token matrices + IDF over the B1 corpus (verbatim B1 scale control).

    Returns (matrices, token_ids cache, idf function, stats).
    """

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), local_files_only=True)

    test_texts = unique_texts(test_rows)
    train_texts = unique_texts(train_rows)
    rng = np.random.default_rng(seed)
    if len(train_texts) > B1_IDF_TRAIN_SAMPLE:
        pick = rng.permutation(len(train_texts))[:B1_IDF_TRAIN_SAMPLE]
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
        return math.log((n_documents + 1) / (document_frequency.get(token_id, 0) + 1)) + 1.0

    matrices = bge.embed_tokens(test_texts)
    stats = {
        "n_test_pairs": len(test_rows),
        "n_test_sides": 2 * len(test_rows),
        "n_unique_test_texts_encoded": len(test_texts),
        "idf_corpus_documents": n_documents,
        "idf_train_texts_available": len(train_texts),
        "idf_train_texts_sampled": len(train_sample),
        "idf_train_sample_target": B1_IDF_TRAIN_SAMPLE,
        "token_max_length": B1_MAX_TOKENS,
        "bge_mode": bge.mode,
        "bge_device": str(bge.stats.get("device", "")),
        "bge_dim": int(bge.stats.get("dim", 0)),
    }
    return matrices, token_cache, idf_of, stats


def score_rows(
    rows: list[dict[str, Any]],
    matrices: dict[str, Any],
    token_ids: dict[str, list[int]],
    idf_of: Any,
    mode: str,
    k: int = 1,
) -> list[float]:
    """Score every test pair under one aggregation mode.

    Modes: "max_idf" (B1), "topk_idf" (B2 top-k, IDF kept), "max_noidf"
    (B2 no-IDF, original max aggregation — isolates the IDF contribution).
    """

    scores: list[float] = []
    for row in rows:
        anchor_text = str(row["pair"]["anchor"]["text"])
        candidate_text = str(row["pair"]["candidate"]["text"])
        query = matrices.get(anchor_text)
        document = matrices.get(candidate_text)
        if query is None or document is None or len(query) == 0 or len(document) == 0:
            scores.append(0.0)
            continue
        anchor_token_ids = token_ids[anchor_text]
        if mode == "max_idf":
            idf = np.asarray([idf_of(token_id) for token_id in anchor_token_ids], dtype=np.float64)
            scores.append(idf_weighted_maxsim(np.asarray(query), np.asarray(document), idf))
        elif mode == "topk_idf":
            idf = np.asarray([idf_of(token_id) for token_id in anchor_token_ids], dtype=np.float64)
            scores.append(
                topk_weighted_maxsim(np.asarray(query), np.asarray(document), idf, k)
            )
        elif mode == "max_noidf":
            scores.append(idf_weighted_maxsim(np.asarray(query), np.asarray(document), None))
        else:
            raise ValueError(f"unknown scoring mode: {mode!r}")
    return scores


# ── main ───────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fold-map", type=str, default=DEFAULT_FOLD_MAP)
    parser.add_argument("--bge-model-dir", type=Path, default=BGE_MODEL_DIR)
    parser.add_argument("--limit", type=int, default=None, help="Cap test rows (smoke)")
    args = parser.parse_args()

    fold_map = parse_fold_map(args.fold_map)
    index, matrix, _ids = load_snapshot(BASE / "data/gjb_438c/feature_snapshot_v1/vectors.npz")
    pairs = load_pairs(BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl")
    rows, _missing = build_rows(pairs, index, fold_map)
    train_rows = [row for row in rows if row["split"] == "train"]
    test_rows = [row for row in rows if row["split"] == "test"]
    if args.limit:
        train_rows = train_rows[: args.limit]
        test_rows = test_rows[: max(args.limit // 4, 1)]
    if not train_rows or not test_rows:
        raise SystemExit("empty train/test after fold mapping; check inputs")
    test_labels = [row["label"] for row in test_rows]
    test_pairs = [row["pair"] for row in test_rows]

    bge = BgeLocal(model_dir=args.bge_model_dir, use_cache=False)
    mode = bge.ensure()
    if mode != "cuda":
        raise SystemExit(
            "B-family token encoding requires CUDA (no silent CPU fallback); "
            f"mode={mode!r}, last_error={bge.last_error!r}"
        )

    matrices, token_cache, idf_of, encode_stats = encode_and_idf(
        bge, args.bge_model_dir, test_rows, train_rows, args.seed
    )

    # B1 reproduction control + B2 variants, all in one scoring pass family.
    rows_out: dict[str, dict[str, Any]] = {}
    variant_scores: dict[str, list[float]] = {}

    def register(name: str, scores: list[float], description: str, extra: dict[str, Any] | None = None) -> float:
        threshold = sweep_threshold(scores, test_labels)
        metrics = metrics_from_scores(scores, test_labels, threshold)
        rows_out[name] = {
            "method": description,
            "threshold_source": "in-fold test negatives 95th percentile (B1 convention)",
            "test": metrics,
            **(extra or {}),
        }
        return float(metrics["auc"])

    b1_scores = score_rows(test_rows, matrices, token_cache, idf_of, "max_idf")
    variant_scores["B1-idf-maxsim"] = b1_scores
    b1_auc = register(
        "B1-idf-maxsim",
        b1_scores,
        "IDF-weighted MaxSim (B1 protocol reproduction)",
    )

    for k in TOPK_VARIANTS:
        scores = score_rows(test_rows, matrices, token_cache, idf_of, "topk_idf", k)
        name = f"B2-topk{k}"
        variant_scores[name] = scores
        register(
            name,
            scores,
            f"IDF-weighted MaxSim, doc-side max -> top-{k} mean",
            {"k": k},
        )
    noidf_scores = score_rows(test_rows, matrices, token_cache, idf_of, "max_noidf")
    variant_scores["B2-noidf"] = noidf_scores
    register(
        "B2-noidf",
        noidf_scores,
        "MaxSim without IDF (w = 1), original max aggregation",
        {"idf": "none"},
    )

    # B4: best B-variant by test AUC (in-fold selection — flagged: the whole
    # B-family protocol is test-only with no dev error bar).
    aucs = {name: float(rows_out[name]["test"]["auc"]) for name in rows_out}
    best_b_name = max(variant_scores, key=lambda name: aucs[name])
    best_b_scores = variant_scores[best_b_name]
    best_b_auc = aucs[best_b_name]
    b2_best_name = max((name for name in aucs if name != "B1-idf-maxsim"), key=lambda name: aucs[name])

    fused = fuse_gate_scores(best_b_scores, test_pairs, GATE_ALPHA)
    b4_auc = register(
        "B4-gate",
        fused,
        f"best B variant ({best_b_name}) min-max normalized + structural gate "
        f"(alpha={GATE_ALPHA}, identifier_match forced False)",
        {"base_variant": best_b_name, "gate_alpha": GATE_ALPHA, "identifier_match": False},
    )

    verdict = judge_variants(
        b1_auc,
        b2_best_name,
        aucs[b2_best_name],
        best_b_name,
        best_b_auc,
        b4_auc,
        ARCHIVED_REFS["A4_projection_gate_clean"],
        ARCHIVED_REFS["A3_projection"],
    )
    reproduction = {
        "archived_run": "eval_ablation_matrix_aacbb70e_20261022_080237",
        "b1_auc_this": rows_out["B1-idf-maxsim"]["test"]["auc"],
        "b1_auc_archived": ARCHIVED_REFS["B1_late_interaction"],
        "delta": round(b1_auc - ARCHIVED_REFS["B1_late_interaction"], 4),
        "n_unique_test_texts_this": encode_stats["n_unique_test_texts_encoded"],
        "n_unique_test_texts_archived": 646,
        "idf_corpus_this": encode_stats["idf_corpus_documents"],
        "idf_corpus_archived": 2425,
    }

    config = {
        "protocol": "B2/B4 late-interaction variants on the B1 protocol",
        "fold_map": fold_map,
        "fold_map_source": "tools/eval_ablation_matrix.py DEFAULT_FOLD_MAP (balanced folds)",
        "seed": args.seed,
        "topk_variants": list(TOPK_VARIANTS),
        "gate_alpha": GATE_ALPHA,
        "gate_identifier_match": False,
        "threshold_rule": "in-fold test negatives 95th percentile (B1 convention)",
        "archived_refs": ARCHIVED_REFS,
        "limit": args.limit,
    }
    run = open_run("eval_late_interaction_variants", config, RUNS_ROOT)

    result = {
        "rows": rows_out,
        "encode_stats": encode_stats,
        "reproduction_check": reproduction,
        "verdict": verdict,
        "notes": [
            (
                "B协议口径: 只编码test fold文本(646条去重, 与B1同法同序), 阈值in-fold于"
                "各自test负例95%分位 — 行间可比, 但F1/precision/recall相对A行乐观; "
                "AUC无阈值, 跨行可比"
            ),
            (
                "B4基变体按test AUC在B族内选择(in-fold选择, 已标注): B协议无dev误差棒, "
                "选择本身也是单点估计的一部分"
            ),
            (
                "B2-noidf保留max聚合仅去掉IDF — 与B2-topk(k隔离聚合方式)互补, "
                "两者合起来分离'聚合方式'与'IDF权重'两个因子"
            ),
            (
                "门控防泄漏: identifier_match强制False(silver正例=共享ID对, 开启即喂标签); "
                "same_section=False映射unknown(跨章节共指合法), same_doc恒compatible"
                "(库内pair), 门控判别信号只剩same_section一项"
            ),
        ],
    }
    run.save_result(result)

    # ── terminal markdown ────────────────────────────────────────────────
    print("# B2/B4 后期交互变体 vs B1协议 (test fold, balanced folds)")
    print(
        f"test {len(test_rows)} pairs / {encode_stats['n_unique_test_texts_encoded']} unique texts encoded; "
        f"B1 reproduction AUC {b1_auc:.4f} vs archived {ARCHIVED_REFS['B1_late_interaction']} "
        f"(delta {reproduction['delta']:+.4f})"
    )
    print()
    print("| row | AUC | F1 | precision | recall | false_merge_rate | threshold |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for name in ("B1-idf-maxsim", "B2-topk3", "B2-topk5", "B2-noidf", "B4-gate"):
        metrics = rows_out[name]["test"]
        print(
            f"| {name} | {metrics['auc']:.4f} | {metrics['f1']:.4f} | {metrics['precision']:.4f} "
            f"| {metrics['recall']:.4f} | {metrics['false_merge_rate']:.4f} | {metrics['threshold']} |"
        )
    print(
        f"| ref A1-native (archived) | {ARCHIVED_REFS['A1_native']:.4f} | | | | | |"
    )
    print(
        f"| ref A4-gate-clean (archived) | {ARCHIVED_REFS['A4_projection_gate_clean']:.4f} "
        f"| {ARCHIVED_REFS['A4_projection_gate_clean_f1']:.4f} | | | "
        f"{ARCHIVED_REFS['A4_projection_gate_clean_fm']:.4f} | |"
    )
    print()
    print("## 判读 (pre-registered rules)")
    print(f"- B2 vs B1: best {b2_best_name}, {verdict['b2_vs_b1']['rule']}")
    print(f"- B4 vs A4-clean: {verdict['b4_vs_references']['rule']}")
    print(
        f"- B族最好 {verdict['b_family_vs_a_family']['best_b_auc']:.4f} vs A1-native "
        f"{ARCHIVED_REFS['A1_native']:.4f} "
        f"(gap {verdict['b_family_vs_a_family']['gap_to_a1']:+.4f})"
    )
    print()
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
