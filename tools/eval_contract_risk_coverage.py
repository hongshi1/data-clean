#!/usr/bin/env python3
r"""Pre-registered E-matrix contrast experiment #48: E0 (forced similarity
classification) vs E3 (QualityContract evidence obligations + abstention).

RQ8: for confirming a same-identity relation, what does gating the verdict on
evidence obligations buy in confirmed precision, and at what abstention cost?

Design (self-contained; the train_shared_projection runs archived no per-pair
scores, so the relation score here is NATIVE frozen-BGE cosine — the E0/E3
contrast isolates the gating POLICY, not the projection quality):
  1. fold map: latest train_shared_projection run's config.fold_map
     (balanced doc->fold assignment; 0=test 1=dev 2/3=train); fallback
     fold = int(sha1('doc:<doc_id>')[:12], 16) % 4.
  2. tau = 95th percentile of dev-split NEGATIVE pair scores (mirrors
     train_shared_projection.sweep_threshold; train fold unused for tau).
  3. E0 forced: every test pair gets a verdict; s >= tau -> same_identity.
  4. E3 contract: confirming same_identity additionally requires the
     obligation set {identity_evidence, scope_evidence, value_parse}:
       identity_evidence: pair's shared_identifiers non-empty (explicit
                          ID co-reference)
       scope_evidence:    features.same_section, OR both texts cite the
                          identical section-number set r"3\.\d+(\.\d+)*"
       value_parse:       either text contains a number r"\d+(\.\d+)?"
     s >= tau AND all obligations -> confirmed_same
     s >= tau AND any missing     -> abstain (unsupported)
     s < tau                      -> rejected
  5. risk-coverage sweep over dev-negative score quantiles; selective risk =
     (confirmed FP + rejected FN) / committed decisions; E0 coverage is 1.
  6. findings cross-check: for the candidate_numeric_conflict findings of
     evidence_graph_v2 (structural-line contract gating, status=insufficient),
     how many would a similarity-only E0 have confirmed (claim-pair BGE
     cos >= tau) — i.e. misconfirmations the structural gating already saved.

Usage: python tools/eval_contract_risk_coverage.py
Output: printed markdown tables + runs protocol result.json.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

BASE = Path(__file__).resolve().parent.parent
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
SNAPSHOT_DIR = BASE / "data/gjb_438c/feature_snapshot_v1"
FINDINGS_PATH = BASE / "data/gjb_438c/evidence_graph_v2/findings_v2.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"

FOLD_TO_SPLIT = {0: "test", 1: "dev", 2: "train", 3: "train"}
SECTION_PATTERN = re.compile(r"3\.\d+(\.\d+)*")
NUMBER_PATTERN = re.compile(r"\d+(\.\d+)?")
OBLIGATION_IDS = ("identity_evidence", "scope_evidence", "value_parse")
PRIMARY_Q = 0.95
SWEEP_QUANTILES = (0.50, 0.70, 0.80, 0.90, 0.95, 0.975, 0.99)
RUN_TIMESTAMP = re.compile(r"_(\d{8}_\d{6})$")

sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402


# --------------------------------------------------------------------------
# Pure obligation / decision logic (unit-tested; no I/O, no globals touched).
# --------------------------------------------------------------------------


def extract_sections(text: str) -> set[str]:
    """Section-number citations present in a text, e.g. '3.2.1' in '见3.2.1节'."""

    return {match.group(0) for match in SECTION_PATTERN.finditer(text)}


def identity_evidence(pair: dict[str, Any]) -> bool:
    """Obligation identity_evidence: explicit identifier co-reference."""

    shared = pair.get("features", {}).get("shared_identifiers", [])
    return bool(shared)


def scope_evidence(pair: dict[str, Any]) -> bool:
    """Obligation scope_evidence: same section, or identical section citations."""

    if pair.get("features", {}).get("same_section") is True:
        return True
    anchor_sections = extract_sections(str(pair["anchor"]["text"]))
    candidate_sections = extract_sections(str(pair["candidate"]["text"]))
    return bool(anchor_sections) and anchor_sections == candidate_sections


def value_parse_evidence(pair: dict[str, Any]) -> bool:
    """Obligation value_parse: at least one side carries a numeric token."""

    return bool(
        NUMBER_PATTERN.search(str(pair["anchor"]["text"]))
        or NUMBER_PATTERN.search(str(pair["candidate"]["text"]))
    )


def obligation_status(pair: dict[str, Any]) -> dict[str, bool]:
    """The three E3 obligations for one pair."""

    return {
        "identity_evidence": identity_evidence(pair),
        "scope_evidence": scope_evidence(pair),
        "value_parse": value_parse_evidence(pair),
    }


def e0_predict(score: float, tau: float) -> int:
    """E0 forced verdict: 1 = same_identity, 0 = not (no abstention)."""

    return 1 if score >= tau else 0


def contract_decision(score: float, tau: float, obligations: dict[str, bool]) -> str:
    """E3 verdict: rejected / abstain / confirmed_same."""

    if score < tau:
        return "rejected"
    if all(obligations.get(key, False) for key in OBLIGATION_IDS):
        return "confirmed_same"
    return "abstain"


# --------------------------------------------------------------------------
# Pure threshold / metrics logic (unit-tested on synthetic distributions).
# --------------------------------------------------------------------------


def percentile(sorted_values: list[float], q: float) -> float:
    """Order-statistic percentile on a pre-sorted list (mirrors
    train_shared_projection.sweep_threshold: ceil(q*n)-1, clamped)."""

    if not sorted_values:
        return 0.0
    position = min(int(math.ceil(q * len(sorted_values))) - 1, len(sorted_values) - 1)
    return sorted_values[max(position, 0)]


def dev_negative_threshold(
    scores: list[float], labels: list[int], q: float = PRIMARY_Q
) -> float:
    """tau = q-quantile of the dev NEGATIVE score distribution (4-decimal round)."""

    negatives = sorted(score for score, label in zip(scores, labels) if label == 0)
    return round(percentile(negatives, q), 4)


def forced_classification_metrics(
    scores: list[float], labels: list[int], tau: float
) -> dict[str, Any]:
    """E0 metrics on a labeled score list: every pair is force-classified."""

    tp = fp = fn = tn = 0
    for score, label in zip(scores, labels):
        if score >= tau:
            if label == 1:
                tp += 1
            else:
                fp += 1
        elif label == 1:
            fn += 1
        else:
            tn += 1
    n_pairs = len(labels)
    n_pos = tp + fn
    n_neg = fp + tn
    return {
        "n_pairs": n_pairs,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(tp / max(tp + fp, 1), 4),
        "recall": round(tp / max(n_pos, 1), 4),
        "false_merge_rate": round(fp / max(n_neg, 1), 4),
        "error_rate": round((fp + fn) / max(n_pairs, 1), 4),
        "coverage": 1.0,
        "threshold": tau,
    }


def _combo_counts(counter: Counter[tuple[str, ...]]) -> dict[str, int]:
    return {"+".join(sorted(key)): int(count) for key, count in sorted(counter.items())}


def contract_gated_metrics(
    scores: list[float],
    labels: list[int],
    obligations_list: list[dict[str, bool]],
    tau: float,
) -> dict[str, Any]:
    """E3 metrics: confirmed precision / abstention / saved high-risk FPs.

    saved_high_risk_fp counts E0 false positives (s >= tau, label 0) that E3
    abstains on instead of confirming — the misconfirmations the contract
    saves. selective_risk = (confirmed FP + rejected FN) / committed pairs.
    """

    confirmed_tp = confirmed_fp = abstained = rejected_pos = rejected_neg = 0
    e0_fp = saved_fp = 0
    missing_all: Counter[tuple[str, ...]] = Counter()
    missing_pos: Counter[tuple[str, ...]] = Counter()
    missing_neg: Counter[tuple[str, ...]] = Counter()
    for score, label, obligations in zip(scores, labels, obligations_list):
        if score >= tau and label == 0:
            e0_fp += 1
        decision = contract_decision(score, tau, obligations)
        if decision == "confirmed_same":
            if label == 1:
                confirmed_tp += 1
            else:
                confirmed_fp += 1
        elif decision == "abstain":
            abstained += 1
            missing = tuple(key for key in OBLIGATION_IDS if not obligations.get(key, False))
            missing_all[missing] += 1
            if label == 1:
                missing_pos[missing] += 1
            else:
                missing_neg[missing] += 1
            if score >= tau and label == 0:
                saved_fp += 1
        elif label == 1:
            rejected_pos += 1
        else:
            rejected_neg += 1
    n_pairs = len(labels)
    n_pos = sum(labels)
    n_neg = n_pairs - n_pos
    committed = n_pairs - abstained
    return {
        "n_pairs": n_pairs,
        "n_pos": n_pos,
        "n_neg": n_neg,
        "n_confirmed": confirmed_tp + confirmed_fp,
        "confirmed_tp": confirmed_tp,
        "confirmed_fp": confirmed_fp,
        "confirmed_precision": round(confirmed_tp / max(confirmed_tp + confirmed_fp, 1), 4),
        "confirmed_recall": round(confirmed_tp / max(n_pos, 1), 4),
        "false_merge_rate": round(confirmed_fp / max(n_neg, 1), 4),
        "n_abstain": abstained,
        "abstention_rate": round(abstained / max(n_pairs, 1), 4),
        "n_rejected": rejected_pos + rejected_neg,
        "rejected_pos": rejected_pos,
        "rejected_neg": rejected_neg,
        "coverage": round(committed / max(n_pairs, 1), 4),
        "selective_risk": round((confirmed_fp + rejected_pos) / max(committed, 1), 4),
        "e0_fp": e0_fp,
        "saved_high_risk_fp": saved_fp,
        "saved_rate": round(saved_fp / max(e0_fp, 1), 4),
        "residual_fp": confirmed_fp,
        "abstain_missing_obligations": _combo_counts(missing_all),
        "abstain_missing_obligations_pos": _combo_counts(missing_pos),
        "abstain_missing_obligations_neg": _combo_counts(missing_neg),
    }


def risk_coverage_points(
    scores: list[float],
    labels: list[int],
    obligations_list: list[dict[str, bool]],
    quantile_taus: list[tuple[float, float]],
) -> list[dict[str, Any]]:
    """Risk-coverage rows: E0 full-coverage risk vs E3 selective risk per tau."""

    rows: list[dict[str, Any]] = []
    for q, tau in quantile_taus:
        e0 = forced_classification_metrics(scores, labels, tau)
        e3 = contract_gated_metrics(scores, labels, obligations_list, tau)
        rows.append(
            {
                "q": q,
                "tau": tau,
                "E0": {
                    "coverage": 1.0,
                    "precision": e0["precision"],
                    "recall": e0["recall"],
                    "error_rate": e0["error_rate"],
                    "fp": e0["fp"],
                    "fn": e0["fn"],
                },
                "E3": {
                    "coverage": e3["coverage"],
                    "abstention_rate": e3["abstention_rate"],
                    "confirmed_precision": e3["confirmed_precision"],
                    "selective_risk": e3["selective_risk"],
                    "n_confirmed": e3["n_confirmed"],
                    "n_abstain": e3["n_abstain"],
                },
            }
        )
    return rows


def resolve_claim_vector_id(ref: str) -> str:
    """Map an evidence-graph claim ref ('claims:CLM-x') to snapshot vector id."""

    if ref.startswith("claims:"):
        return "claim:" + ref[len("claims:") :]
    return ref


def sha1_fold(doc_id: str) -> int:
    """Fallback fold rule: int(sha1('doc:<doc_id>')[:12], 16) % 4."""

    return int(hashlib.sha1(f"doc:{doc_id}".encode("utf-8")).hexdigest()[:12], 16) % 4


def pair_split(pair: dict[str, Any], fold_map: dict[str, int] | None) -> str:
    """Split of a pair under the balanced fold map (fallback: sha1 doc hash)."""

    doc_id = str(pair["anchor"]["doc_id"])
    if fold_map is None:
        return FOLD_TO_SPLIT[sha1_fold(doc_id)]
    fold = fold_map.get(doc_id)
    if fold is None:
        fold = sha1_fold(doc_id)
    return FOLD_TO_SPLIT[int(fold)]


# --------------------------------------------------------------------------
# I/O helpers (only invoked from main(); module import stays I/O-free).
# --------------------------------------------------------------------------


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_unit_matrix(path: Path) -> tuple[dict[str, int], np.ndarray]:
    """Row-normalized snapshot vectors + occurrence-id row index."""

    with np.load(path, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(value) for value in data["ids"].tolist()]
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    unit = matrix / np.maximum(norms, 1e-12)
    return {occurrence_id: position for position, occurrence_id in enumerate(ids)}, unit


def latest_train_run_fold_map(runs_root: Path) -> tuple[dict[str, int] | None, str]:
    """fold_map of the newest train_shared_projection run (None -> fallback)."""

    candidates: list[tuple[str, Path]] = []
    for path in runs_root.glob("train_shared_projection_*"):
        if not path.is_dir():
            continue
        match = RUN_TIMESTAMP.search(path.name)
        if match:
            candidates.append((match.group(1), path))
    if not candidates:
        return None, "no train_shared_projection run found (sha1 doc-hash fallback)"
    latest_stamp, latest_path = max(candidates, key=lambda item: (item[0], item[1].name))
    config_path = latest_path / "config.json"
    if not config_path.exists():
        return None, f"{latest_path.name} (no config.json; sha1 fallback)"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    fold_map = (config.get("config") or {}).get("fold_map")
    if not fold_map:
        return None, f"{latest_path.name} (no fold_map; sha1 fallback)"
    declared = {str(doc): int(fold) for doc, fold in fold_map.items()}
    return declared, f"{latest_path.name} (timestamp {latest_stamp})"


def findings_e0_confirmation(
    findings: list[dict[str, Any]],
    index: dict[str, int],
    unit_matrix: np.ndarray,
    tau: float,
) -> dict[str, Any]:
    """Numeric-insufficient findings an E0 similarity rule would confirm.

    Each candidate_numeric_conflict finding pairs two claims (target_refs,
    'claims:CLM-x'); the structural contract line already gated them to
    status=insufficient. We simulate the E0 alternative: BGE cos >= tau would
    confirm same-identity (and hence the conflict). The count is the number of
    potential misconfirmations the structural gating already saved.
    """

    total = two_refs = resolvable = confirmed = 0
    score_sum = 0.0
    for finding in findings:
        if finding.get("finding_type") != "candidate_numeric_conflict":
            continue
        total += 1
        refs = [str(ref) for ref in finding.get("target_refs", [])]
        if len(refs) != 2:
            continue
        two_refs += 1
        vector_ids = [resolve_claim_vector_id(ref) for ref in refs]
        if any(vector_id not in index for vector_id in vector_ids):
            continue
        resolvable += 1
        score = float(
            unit_matrix[index[vector_ids[0]]] @ unit_matrix[index[vector_ids[1]]]
        )
        score_sum += score
        if score >= tau:
            confirmed += 1
    return {
        "n_numeric_insufficient_findings": total,
        "n_two_claim_refs": two_refs,
        "n_resolvable_vectors": resolvable,
        "n_e0_similarity_would_confirm": confirmed,
        "e0_confirm_rate": round(confirmed / max(resolvable, 1), 4),
        "mean_claim_pair_cos": round(score_sum / max(resolvable, 1), 4),
    }


# --------------------------------------------------------------------------
# Experiment driver.
# --------------------------------------------------------------------------


def main() -> None:
    pairs = load_jsonl(PAIRS_PATH)
    index, unit_matrix = load_unit_matrix(SNAPSHOT_DIR / "vectors.npz")
    fold_map, fold_map_source = latest_train_run_fold_map(RUNS_ROOT)

    dev_scores: list[float] = []
    dev_labels: list[int] = []
    test_scores: list[float] = []
    test_labels: list[int] = []
    test_obligations: list[dict[str, bool]] = []
    skipped_missing_vector = 0
    split_counts: Counter[str] = Counter()

    for pair in pairs:
        anchor_id = str(pair["anchor"]["occurrence_id"])
        candidate_id = str(pair["candidate"]["occurrence_id"])
        if anchor_id not in index or candidate_id not in index:
            skipped_missing_vector += 1
            continue
        split = pair_split(pair, fold_map)
        split_counts[split] += 1
        label = int(pair["label"])
        score = float(unit_matrix[index[anchor_id]] @ unit_matrix[index[candidate_id]])
        if split == "dev":
            dev_scores.append(score)
            dev_labels.append(label)
        elif split == "test":
            test_scores.append(score)
            test_labels.append(label)
            test_obligations.append(obligation_status(pair))

    tau = dev_negative_threshold(dev_scores, dev_labels)
    e0 = forced_classification_metrics(test_scores, test_labels, tau)
    e3 = contract_gated_metrics(test_scores, test_labels, test_obligations, tau)
    quantile_taus = [
        (q, dev_negative_threshold(dev_scores, dev_labels, q)) for q in SWEEP_QUANTILES
    ]
    risk_coverage = risk_coverage_points(
        test_scores, test_labels, test_obligations, quantile_taus
    )

    findings = load_jsonl(FINDINGS_PATH)
    findings_check = findings_e0_confirmation(findings, index, unit_matrix, tau)

    precision_gain = round(
        float(e3["confirmed_precision"]) - float(e0["precision"]), 4
    )
    conclusion = (
        f"E3 vs E0 on the test fold: confirmed precision "
        f"{e0['precision']} -> {e3['confirmed_precision']} "
        f"(delta {precision_gain:+.4f}), at the cost of abstaining on "
        f"{e3['abstention_rate']} of test pairs ({e3['n_abstain']}/{e3['n_pairs']}); "
        f"{e3['saved_high_risk_fp']}/{e3['e0_fp']} E0 false positives "
        f"({e3['saved_rate']:.2%}) are converted from confirmed merges into "
        f"abstentions. Silver-label caveat: the identity_evidence obligation "
        f"nearly reconstructs the positive/negative construction, so the "
        f"precision gain is an upper bound tied to this labeling."
    )

    result = {
        "protocol": (
            "pre-registered E-matrix #48: E0 forced similarity classification "
            "vs E3 QualityContract obligation gating + abstention, native "
            "frozen-BGE cosine relation score"
        ),
        "rq": (
            "RQ8: relation-score-only confirmation vs obligation-checked "
            "confirmation with abstention — confirmed precision gain vs "
            "abstention cost"
        ),
        "n_pairs_total": len(pairs),
        "skipped_missing_vector": skipped_missing_vector,
        "split_pair_counts": dict(sorted(split_counts.items())),
        "fold_map_source": fold_map_source,
        "fold_map": fold_map,
        "relation_score": "native BGE cosine (feature_snapshot_v1, no projection)",
        "dev_threshold": {
            "rule": "95th percentile of dev-split negative pair scores",
            "q": PRIMARY_Q,
            "tau": tau,
            "n_dev_pairs": len(dev_scores),
            "n_dev_neg": sum(1 for label in dev_labels if label == 0),
        },
        "E0_forced": e0,
        "E3_contract": e3,
        "E3_vs_E0": {
            "confirmed_precision_gain": precision_gain,
            "abstention_cost_rate": e3["abstention_rate"],
            "saved_high_risk_fp": e3["saved_high_risk_fp"],
            "saved_rate": e3["saved_rate"],
            "residual_fp": e3["residual_fp"],
        },
        "risk_coverage": risk_coverage,
        "findings_validation": findings_check,
        "notes": [
            (
                "义务-标签相关性(诚实声明): training_pairs_v1的全部正例来自"
                " explicit_identifier(共享显式ID), 全部负例来自"
                " sibling_distinct_identifier(ID不相交)。identity_evidence义务"
                "(shared_identifiers非空)因此在该数据集上近乎完美地区分正负例"
                "——这既是E3契约设计的本意(确认same_identity需要身份证据), "
                "也意味着confirmed precision的提升幅度与银标签构造方式纠缠, "
                "是门控策略在该标注上的上界, 不能直接外推到金标数据。"
            ),
            (
                "关系分数局限: 最近的train_shared_projection run未保存逐pair分数, "
                "故本实验用BGE原生余弦自包含重算。E0与E3共享同一分数, 对照隔离的"
                "是判定策略(门控+弃权 vs 强制分类), 不反映训练投影的质量差异。"
            ),
            (
                "阈值口径: tau = dev fold负例分数的95%分位(与"
                " train_shared_projection.sweep_threshold同一算法, ceil(q*n)-1"
                "顺序统计量, 保留4位小数); train fold未参与阈值估计。"
            ),
            (
                "selective risk定义: 提交决策(confirmed或rejected)上的0-1损失, "
                "=(confirmed FP + rejected FN)/提交数; E0覆盖率为1, 其risk即"
                "全量错误率。risk-coverage扫描tau取dev负例分位数"
                f" {list(SWEEP_QUANTILES)}。"
            ),
            (
                "findings验证为模拟口径: 以claim对BGE cos>=tau模拟E0相似度法"
                "会把多少条结构线已判为insufficient的numeric冲突候选'误确认', "
                "计数是实例级佐证而非fold级精度测量(claim对来自结构证据图, "
                "不在pair test fold内)。"
            ),
            (
                f"fold映射来源: {fold_map_source}; 无fold_map时回退"
                " sha1(doc)%4。"
            ),
        ],
        "conclusion": conclusion,
    }

    run = open_run(
        "eval_contract_risk_coverage",
        {
            "pairs": str(PAIRS_PATH),
            "snapshot": str(SNAPSHOT_DIR),
            "findings": str(FINDINGS_PATH),
            "fold_map": fold_map,
            "fold_map_source": fold_map_source,
            "primary_q": PRIMARY_Q,
            "sweep_quantiles": list(SWEEP_QUANTILES),
            "obligations": {
                "identity_evidence": "shared_identifiers non-empty",
                "scope_evidence": "same_section or identical section-number sets",
                "value_parse": "numeric token in either text",
            },
            "relation_score": "native BGE cosine",
        },
        RUNS_ROOT,
    )
    run.save_result(result)

    print("# E48: E0 forced classification vs E3 contract+abstention (test fold)")
    print(f"relation score: native BGE cosine; fold map: {fold_map_source}")
    print(
        f"tau = {tau} (dev-negative P{int(PRIMARY_Q * 100)}; "
        f"{result['dev_threshold']['n_dev_neg']} dev negatives)"
    )
    print(
        f"test fold: {e0['n_pairs']} pairs "
        f"({e0['n_pos']} pos / {e0['n_neg']} neg); "
        f"skipped pairs without vectors: {skipped_missing_vector}"
    )
    print()
    print("| metric | E0 forced | E3 contract |")
    print("|---|---|---|")
    print("| decision policy | s >= tau | s >= tau AND all obligations |")
    print(
        f"| precision (confirmed same) | {e0['precision']} | "
        f"{e3['confirmed_precision']} |"
    )
    print(
        f"| recall (confirmed, of all positives) | {e0['recall']} | "
        f"{e3['confirmed_recall']} |"
    )
    print(
        f"| false_merge_rate (FP / negatives) | {e0['false_merge_rate']} | "
        f"{e3['false_merge_rate']} |"
    )
    print(f"| abstention rate | 0.0 | {e3['abstention_rate']} |")
    print(f"| coverage | 1.0 | {e3['coverage']} |")
    print(
        f"| selective risk (error on committed) | {e0['error_rate']} | "
        f"{e3['selective_risk']} |"
    )
    print(
        f"| high-risk FP saved by contract | - | "
        f"{e3['saved_high_risk_fp']}/{e3['e0_fp']} ({e3['saved_rate']:.2%}) |"
    )
    print()
    print("## risk-coverage sweep (tau = dev-negative quantile)")
    print("| q | tau | E0 err (cov=1.0) | E3 coverage | E3 abstain | E3 conf-P | E3 sel-risk |")
    print("|---|---|---|---|---|---|---|")
    for row in risk_coverage:
        print(
            f"| {row['q']} | {row['tau']} | {row['E0']['error_rate']} | "
            f"{row['E3']['coverage']} | {row['E3']['abstention_rate']} | "
            f"{row['E3']['confirmed_precision']} | {row['E3']['selective_risk']} |"
        )
    print()
    print("## findings cross-check (evidence_graph_v2, structural contract gating)")
    fv = findings_check
    print(
        f"{fv['n_numeric_insufficient_findings']} numeric-insufficient findings; "
        f"{fv['n_resolvable_vectors']} with resolvable claim vectors; "
        f"{fv['n_e0_similarity_would_confirm']} would be E0-confirmed "
        f"(cos >= tau, rate {fv['e0_confirm_rate']:.2%}, "
        f"mean pair cos {fv['mean_claim_pair_cos']}) -> saved as insufficient"
    )
    print()
    print(conclusion)
    print()
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
