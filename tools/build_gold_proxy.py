#!/usr/bin/env python3
r"""多信号一致性gold-proxy评测集构建(triple consensus).

信号族:
  1. P1确定性规则(定义层): label_basis="explicit_identifier"显式ID正例 /
     "sibling_distinct_identifier" sibling负例(training_pairs_v1);
  2. BGE表征族: feature_snapshot_v1/vectors.npz native余弦(冻结快照);
  3. Qwen3表征族: models/embedding/qwen3-embedding-0.6b现场独立编码
     (pair两端均为文档性质, 双侧走embed_docs; 输入文本与BGE快照完全一致
     ——同一份200字符截断文本, 保证编码器间分歧只反映编码器差异).

升级规则(θ按编码器独立校准, 均在dev fold上):
  gold_proxy_positive: P1正例 ∧ bge_cos>=θ_bge ∧ qwen3_cos>=θ_qwen
    (θ = dev负例分数95%分位, nearest-rank)
  gold_proxy_negative: sibling负例 ∧ bge_cos<θ_bge_low ∧ qwen3_cos<θ_qwen_low
    (θ_low = dev正例分数5%分位)
  其余 → review_queue(分歧样本: 一高一低/双中间带, 按|bge_cos-qwen3_cos|
  降序取前REVIEW_TOP_N条落盘).

防泄漏铁律: gold-proxy只从test fold pair构建. fold_map读取最近
train_shared_projection run的config.json并确认test doc集合={06,12,13};
dev fold仅用于θ校准, train fold不参与任何环节; 输出逐条标注
exogenous_evaluation_only=true, 永不进入训练/校准split.

用法: python tools/build_gold_proxy.py
产出: data/gjb_438c/gold_proxy_v1/{gold_proxy_pairs.jsonl, review_queue.jsonl,
summary.json, manifest.json} + runs协议归档.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402
PAIRS_PATH = BASE / "data/gjb_438c/training_pairs_v1/pairs.jsonl"
SNAPSHOT_DIR = BASE / "data/gjb_438c/feature_snapshot_v1"
QWEN_MODEL_DIR = BASE / "models/embedding/qwen3-embedding-0.6b"
RUNS_ROOT = BASE / "data/gjb_438c/runs"
OUT_DIR = BASE / "data/gjb_438c/gold_proxy_v1"

FOLD_TO_SPLIT = {0: "test", 1: "dev", 2: "train", 3: "train"}
EXPECTED_TEST_DOCS = {"06", "12", "13"}
P1_POSITIVE_BASIS = "explicit_identifier"
SIBLING_NEGATIVE_BASIS = "sibling_distinct_identifier"
POSITIVE_LABEL = "gold_proxy_positive"
NEGATIVE_LABEL = "gold_proxy_negative"
REVIEW_LABEL = "review"
PROXY_BASIS = "triple_consensus"
PRIMARY_Q = 0.95
LOW_Q = 0.05
REVIEW_TOP_N = 200
RUN_STAMP_RE = re.compile(r"_(\d{8}_\d{6})(?:_\d+)?$")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return len(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rule_label(pair: dict[str, Any]) -> int:
    basis = str(pair.get("label_basis", ""))
    if basis == P1_POSITIVE_BASIS:
        return 1
    if basis == SIBLING_NEGATIVE_BASIS:
        return 0
    raise ValueError(f"unknown label_basis: {basis!r}")


def load_fold_map(runs_root: Path) -> tuple[dict[str, int], str]:
    """最近train_shared_projection run的fold_map(按目录名时间戳新→旧).

    只接受带合法fold_map的config; 全部缺失则显式退出(fold来源不可回退猜测).
    """
    candidates: list[tuple[str, Path]] = []
    if not runs_root.exists():
        raise SystemExit(f"runs目录缺失: {runs_root}")
    for path in sorted(runs_root.iterdir()):
        if not path.is_dir() or not path.name.startswith("train_shared_projection_"):
            continue
        config_path = path / "config.json"
        if not config_path.exists():
            continue
        match = RUN_STAMP_RE.search(path.name)
        stamp = match.group(1) if match else "00000000_000000"
        candidates.append((stamp, config_path))
    for _, config_path in sorted(candidates, reverse=True):
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        fold_map = (config.get("config") or {}).get("fold_map")
        if isinstance(fold_map, dict) and fold_map:
            return {str(doc): int(fold) for doc, fold in fold_map.items()}, str(config_path)
    raise SystemExit(f"no fold_map in any train_shared_projection run under {runs_root}")


def split_of_pair(pair: dict[str, Any], fold_map: dict[str, int]) -> str:
    doc_id = str(pair["anchor"]["doc_id"])
    fold = fold_map.get(doc_id)
    if fold is None:
        raise SystemExit(f"doc {doc_id!r} missing from fold_map")
    return FOLD_TO_SPLIT[int(fold)]


def nearest_rank_percentile(values: Sequence[float], q: float) -> float:
    """nearest-rank分位: 升序第ceil(q*n)个值(与train_shared_projection阈值约定一致)."""
    if not values:
        raise ValueError("percentile of an empty score list")
    if not 0.0 < q < 1.0:
        raise ValueError(f"q must be in (0, 1), got {q}")
    ordered = sorted(values)
    position = min(int(math.ceil(q * len(ordered))) - 1, len(ordered) - 1)
    return float(ordered[max(position, 0)])


def calibrate_thresholds(dev_pos_scores: Sequence[float],
                         dev_neg_scores: Sequence[float]) -> dict[str, float]:
    """单编码器阈值: θ=dev负例95%分位, θ_low=dev正例5%分位."""
    return {
        "theta": nearest_rank_percentile(dev_neg_scores, PRIMARY_Q),
        "theta_low": nearest_rank_percentile(dev_pos_scores, LOW_Q),
    }


def classify_pair(rule: int, bge_cos: float, qwen3_cos: float,
                  bge_thresholds: dict[str, float],
                  qwen3_thresholds: dict[str, float]) -> tuple[str, str]:
    """升级规则裁决; 返回(proxy_label, review_type), 已裁决样本review_type为空串."""
    if rule not in (0, 1):
        raise ValueError(f"rule must be 0 or 1, got {rule}")
    if rule == 1:
        bge_high = bge_cos >= bge_thresholds["theta"]
        qwen_high = qwen3_cos >= qwen3_thresholds["theta"]
        if bge_high and qwen_high:
            return POSITIVE_LABEL, ""
        if bge_high:
            return REVIEW_LABEL, "pos_bge_high_qwen_low"
        if qwen_high:
            return REVIEW_LABEL, "pos_bge_low_qwen_high"
        return REVIEW_LABEL, "pos_both_below_theta"
    bge_low = bge_cos < bge_thresholds["theta_low"]
    qwen_low = qwen3_cos < qwen3_thresholds["theta_low"]
    if bge_low and qwen_low:
        return NEGATIVE_LABEL, ""
    if bge_low:
        return REVIEW_LABEL, "neg_bge_low_qwen_high"
    if qwen_low:
        return REVIEW_LABEL, "neg_bge_high_qwen_low"
    return REVIEW_LABEL, "neg_both_above_theta_low"


def build_review_queue(review_rows: list[dict[str, Any]],
                       top_n: int = REVIEW_TOP_N) -> list[dict[str, Any]]:
    """分歧样本排序: |bge_cos-qwen3_cos|降序, 并列按pair_id升序; 取前top_n."""
    ordered = sorted(review_rows, key=lambda row: (-row["score_gap"], row["pair_id"]))
    return ordered[:top_n]


def rank_auc(scores: Sequence[float], labels: Sequence[int]) -> float:
    """秩AUC: P(正例分数>负例分数), 并列取平均秩(与train_shared_projection一致)."""
    if len(scores) != len(labels):
        raise ValueError("scores and labels length mismatch")
    positives = sum(1 for label in labels if label == 1)
    negatives = sum(1 for label in labels if label == 0)
    if positives == 0 or negatives == 0:
        raise ValueError("rank_auc needs at least one positive and one negative")
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
    rank_sum_pos = sum(ranks[position] for position, label in enumerate(labels) if label == 1)
    return (rank_sum_pos - positives * (positives + 1) / 2.0) / max(positives * negatives, 1)


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda position: values[position])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        average_rank = (start + end) / 2.0 + 1.0
        for position in order[start : end + 1]:
            ranks[position] = average_rank
        start = end + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman秩相关(并列取平均秩); 双编码器分数一致性度量."""
    if len(x) != len(y) or not x:
        raise ValueError("spearman needs two non-empty equal-length sequences")
    rx = _average_ranks(x)
    ry = _average_ranks(y)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0.0 or vy == 0.0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def high_pattern_counts(bge_scores: Sequence[float], qwen3_scores: Sequence[float],
                        bge_theta: float, qwen3_theta: float) -> dict[str, int]:
    """双编码器'≥θ'通过模式计数: {both, bge_only, qwen3_only, neither}."""
    counts = Counter()
    for bge_cos, qwen_cos in zip(bge_scores, qwen3_scores):
        pattern = ("b" if bge_cos >= bge_theta else "_") + ("q" if qwen_cos >= qwen3_theta else "_")
        counts[{"bq": "both", "b_": "bge_only", "_q": "qwen3_only", "__": "neither"}[pattern]] += 1
    return {key: counts[key] for key in ("both", "bge_only", "qwen3_only", "neither")}


def low_pattern_counts(bge_scores: Sequence[float], qwen3_scores: Sequence[float],
                       bge_theta_low: float, qwen3_theta_low: float) -> dict[str, int]:
    """双编码器'<θ_low'模式计数: {both_low, bge_only_low, qwen3_only_low, neither_low}."""
    counts = Counter()
    for bge_cos, qwen_cos in zip(bge_scores, qwen3_scores):
        pattern = ("b" if bge_cos < bge_theta_low else "_") + ("q" if qwen_cos < qwen3_theta_low else "_")
        mapping = {"bq": "both_low", "b_": "bge_only_low", "_q": "qwen3_only_low", "__": "neither_low"}
        counts[mapping[pattern]] += 1
    return {key: counts[key] for key in ("both_low", "bge_only_low", "qwen3_only_low", "neither_low")}


def load_snapshot_vectors(path: Path) -> tuple[dict[str, int], Any]:
    """npz快照→(occurrence_id→行号, L2归一矩阵); 幂等归一防御非单位范数."""
    import numpy as np

    with np.load(path, allow_pickle=False) as data:
        matrix = data["matrix"].astype(np.float32)
        ids = [str(value) for value in data["ids"].tolist()]
    index = {occurrence_id: position for position, occurrence_id in enumerate(ids)}
    if len(index) != len(ids):
        raise SystemExit(f"duplicate occurrence_id in snapshot: {path}")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    return index, matrix / norms


def pair_scores(pairs: Sequence[dict[str, Any]], index: dict[str, int],
                matrix: Any) -> tuple[list[tuple[dict[str, Any], float]], int]:
    """逐pair余弦; 端点缺失于快照的pair跳过并计数(不静默参与)."""
    rows: list[tuple[dict[str, Any], float]] = []
    missing = 0
    for pair in pairs:
        anchor_row = index.get(str(pair["anchor"]["occurrence_id"]))
        candidate_row = index.get(str(pair["candidate"]["occurrence_id"]))
        if anchor_row is None or candidate_row is None:
            missing += 1
            continue
        rows.append((pair, float(matrix[anchor_row] @ matrix[candidate_row])))
    return rows, missing


def encode_qwen3(texts: list[str]) -> Any:
    """Qwen3-Embedding-0.6b现场编码(文档侧协议embed_docs); GPU/模型失败显式退出."""
    eval_dir = str(BASE / "tools" / "eval")
    if eval_dir not in sys.path:
        sys.path.insert(0, eval_dir)
    try:
        import torch
        from eval_qwen3_backbone import Qwen3Encoder
    except ImportError as exc:
        raise SystemExit(f"Qwen3编码依赖不可用: {exc}") from None
    if not (QWEN_MODEL_DIR / "config.json").exists():
        raise SystemExit(f"Qwen3模型缺失: {QWEN_MODEL_DIR}")
    if not torch.cuda.is_available():
        raise SystemExit("GPU不可用: Qwen3现场编码需要CUDA(显式退出, 不降级CPU)")
    try:
        encoder = Qwen3Encoder(QWEN_MODEL_DIR)
        return encoder.embed_docs(texts)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Qwen3编码失败(GPU显式退出): {exc}") from None


def gold_row(classified: dict[str, Any]) -> dict[str, Any]:
    pair = classified["pair"]
    return {
        "pair_id": pair["pair_id"],
        "anchor": pair["anchor"],
        "candidate": pair["candidate"],
        "proxy_label": classified["proxy_label"],
        "label": classified["rule"],
        "proxy_basis": PROXY_BASIS,
        "bge_cos": classified["bge_cos"],
        "qwen3_cos": classified["qwen_cos"],
        "quality_tier": "gold_proxy",
        "split": "test",
        "exogenous_evaluation_only": True,
    }


def review_row(classified: dict[str, Any]) -> dict[str, Any]:
    pair = classified["pair"]
    return {
        "pair_id": pair["pair_id"],
        "anchor": pair["anchor"],
        "candidate": pair["candidate"],
        "rule_label": classified["rule"],
        "rule_basis": pair["label_basis"],
        "proxy_label": REVIEW_LABEL,
        "review_type": classified["review_type"],
        "bge_cos": classified["bge_cos"],
        "qwen3_cos": classified["qwen_cos"],
        "score_gap": abs(classified["bge_cos"] - classified["qwen_cos"]),
        "quality_tier": "review_queue",
        "split": "test",
        "exogenous_evaluation_only": True,
    }


def verify_written_gold(path: Path, bge_thresholds: dict[str, float],
                        qwen3_thresholds: dict[str, float]) -> dict[str, Any]:
    """落盘资产复核: 每条gold行必须满足其三信号共识规则(写后读回验证)."""
    rows = read_jsonl(path)
    violations: list[str] = []
    consistent_positives = 0
    for row in rows:
        ok = (
            row["proxy_label"] in (POSITIVE_LABEL, NEGATIVE_LABEL)
            and row["split"] == "test"
            and row["exogenous_evaluation_only"] is True
        )
        if row["proxy_label"] == POSITIVE_LABEL:
            rule_ok = (
                row["bge_cos"] >= bge_thresholds["theta"]
                and row["qwen3_cos"] >= qwen3_thresholds["theta"]
            )
            if rule_ok:
                consistent_positives += 1
        else:
            rule_ok = (
                row["bge_cos"] < bge_thresholds["theta_low"]
                and row["qwen3_cos"] < qwen3_thresholds["theta_low"]
            )
        if not ok or not rule_ok:
            violations.append(row["pair_id"])
    n_pos = sum(1 for row in rows if row["proxy_label"] == POSITIVE_LABEL)
    return {
        "n_rows": len(rows),
        "n_gold_proxy_positive": n_pos,
        "gold_proxy_positive_consistency": (
            round(consistent_positives / n_pos, 6) if n_pos else None
        ),
        "violations": violations,
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    fold_map, fold_map_source = load_fold_map(RUNS_ROOT)
    test_docs = {doc for doc, fold in fold_map.items() if FOLD_TO_SPLIT[int(fold)] == "test"}
    if test_docs != EXPECTED_TEST_DOCS:
        raise SystemExit(
            f"fold_map确认失败: test docs {sorted(test_docs)} != 预期 {sorted(EXPECTED_TEST_DOCS)}"
            f" (来源: {fold_map_source})"
        )
    print(f"fold_map: {fold_map_source}")
    print(f"test fold docs: {','.join(sorted(test_docs))} (确认=06/12/13)")

    pairs = read_jsonl(PAIRS_PATH)
    basis_violations: list[str] = []
    for pair in pairs:
        try:
            expected = rule_label(pair)
        except ValueError:
            basis_violations.append(f"{pair.get('pair_id', '?')}:{pair.get('label_basis')!r}")
            continue
        if int(pair.get("label", -1)) != expected:
            basis_violations.append(f"{pair.get('pair_id', '?')}:label!=basis")
    if basis_violations:
        raise SystemExit(
            f"label_basis契约违反: {basis_violations[:5]} (共{len(basis_violations)}条)"
        )

    dev_pairs = [pair for pair in pairs if split_of_pair(pair, fold_map) == "dev"]
    test_pairs = [pair for pair in pairs if split_of_pair(pair, fold_map) == "test"]
    if not dev_pairs or not test_pairs:
        raise SystemExit(
            f"dev/test fold为空: dev={len(dev_pairs)} test={len(test_pairs)} (fold_map来源{fold_map_source})"
        )
    print(f"pairs: total={len(pairs)} dev={len(dev_pairs)} test={len(test_pairs)}")

    index_bge, matrix_bge = load_snapshot_vectors(SNAPSHOT_DIR / "vectors.npz")
    snapshot_texts = {
        str(row["occurrence_id"]): str(row["text"])
        for row in read_jsonl(SNAPSHOT_DIR / "features.jsonl")
    }
    dev_bge, dev_missing = pair_scores(dev_pairs, index_bge, matrix_bge)
    test_bge, test_missing = pair_scores(test_pairs, index_bge, matrix_bge)
    if not dev_bge or not test_bge:
        raise SystemExit("快照端点缺失过多: dev/test可用pair为空")
    print(
        f"BGE native cos: dev={len(dev_bge)}(缺端点{dev_missing}) "
        f"test={len(test_bge)}(缺端点{test_missing})"
    )

    endpoint_ids = sorted(
        {endpoint for pair, _ in dev_bge + test_bge for endpoint in (
            str(pair["anchor"]["occurrence_id"]), str(pair["candidate"]["occurrence_id"])
        )}
    )
    absent = [occ for occ in endpoint_ids if occ not in snapshot_texts]
    if absent:
        raise SystemExit(f"快照features.jsonl缺端点文本: {absent[:5]} (共{len(absent)}条)")
    endpoint_texts = [snapshot_texts[occ] for occ in endpoint_ids]
    print(f"Qwen3现场编码: {len(endpoint_texts)}条唯一端点文本(与BGE快照同输入, 200字符截断)")
    qwen_matrix = encode_qwen3(endpoint_texts)
    index_qwen = {occ: position for position, occ in enumerate(endpoint_ids)}

    dev_qwen, _ = pair_scores([pair for pair, _ in dev_bge], index_qwen, qwen_matrix)
    test_qwen, _ = pair_scores([pair for pair, _ in test_bge], index_qwen, qwen_matrix)

    dev_pos_bge = [score for pair, score in dev_bge if rule_label(pair) == 1]
    dev_neg_bge = [score for pair, score in dev_bge if rule_label(pair) == 0]
    dev_pos_qwen = [score for pair, score in dev_qwen if rule_label(pair) == 1]
    dev_neg_qwen = [score for pair, score in dev_qwen if rule_label(pair) == 0]
    bge_thresholds = calibrate_thresholds(dev_pos_bge, dev_neg_bge)
    qwen3_thresholds = calibrate_thresholds(dev_pos_qwen, dev_neg_qwen)
    for name, thresholds in (("bge", bge_thresholds), ("qwen3", qwen3_thresholds)):
        if not thresholds["theta_low"] < thresholds["theta"]:
            raise SystemExit(
                f"编码器{name}阈值带退化: theta_low({thresholds['theta_low']})"
                f" >= theta({thresholds['theta']}) — 无分离中间带"
            )
    print(
        "θ校准(dev fold): BGE θ={:.4f} θ_low={:.4f} | Qwen3 θ={:.4f} θ_low={:.4f}".format(
            bge_thresholds["theta"], bge_thresholds["theta_low"],
            qwen3_thresholds["theta"], qwen3_thresholds["theta_low"],
        )
    )

    classified: list[dict[str, Any]] = []
    for (pair, bge_cos), (_, qwen_cos) in zip(test_bge, test_qwen):
        rule = rule_label(pair)
        proxy_label, review_type = classify_pair(
            rule, bge_cos, qwen_cos, bge_thresholds, qwen3_thresholds
        )
        classified.append(
            {
                "pair": pair,
                "rule": rule,
                "bge_cos": bge_cos,
                "qwen_cos": qwen_cos,
                "proxy_label": proxy_label,
                "review_type": review_type,
            }
        )

    leakage = [
        classified_row["pair"]["pair_id"]
        for classified_row in classified
        if split_of_pair(classified_row["pair"], fold_map) != "test"
        or str(classified_row["pair"]["candidate"]["doc_id"]) not in test_docs
    ]
    if leakage:
        raise SystemExit(f"防泄漏铁律违反(非test fold pair混入): {leakage[:5]}")

    gold_rows = sorted(
        (gold_row(item) for item in classified if item["proxy_label"] != REVIEW_LABEL),
        key=lambda row: row["pair_id"],
    )
    review_rows = [review_row(item) for item in classified if item["proxy_label"] == REVIEW_LABEL]
    review_top = build_review_queue(review_rows, REVIEW_TOP_N)

    out_dir = OUT_DIR
    if out_dir.exists():
        print(f"注意: 重建已存在的资产目录 {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    n_gold = write_jsonl(out_dir / "gold_proxy_pairs.jsonl", gold_rows)
    n_review = write_jsonl(out_dir / "review_queue.jsonl", review_top)

    rule_pos = [item for item in classified if item["rule"] == 1]
    rule_neg = [item for item in classified if item["rule"] == 0]
    pos_patterns = high_pattern_counts(
        [item["bge_cos"] for item in rule_pos], [item["qwen_cos"] for item in rule_pos],
        bge_thresholds["theta"], qwen3_thresholds["theta"],
    )
    neg_patterns = low_pattern_counts(
        [item["bge_cos"] for item in rule_neg], [item["qwen_cos"] for item in rule_neg],
        bge_thresholds["theta_low"], qwen3_thresholds["theta_low"],
    )
    n_pos = len(rule_pos)
    n_neg = len(rule_neg)
    agreement_pos = (pos_patterns["both"] + pos_patterns["neither"]) / max(n_pos, 1)
    agreement_neg = (neg_patterns["both_low"] + neg_patterns["neither_low"]) / max(n_neg, 1)
    spear = spearman(
        [item["bge_cos"] for item in classified], [item["qwen_cos"] for item in classified]
    )
    aucs = {
        "bge": {
            "dev": round(rank_auc([s for _, s in dev_bge], [rule_label(p) for p, _ in dev_bge]), 4),
            "test": round(
                rank_auc([item["bge_cos"] for item in classified], [item["rule"] for item in classified]), 4
            ),
        },
        "qwen3": {
            "dev": round(rank_auc([s for _, s in dev_qwen], [rule_label(p) for p, _ in dev_qwen]), 4),
            "test": round(
                rank_auc([item["qwen_cos"] for item in classified], [item["rule"] for item in classified]), 4
            ),
        },
    }

    review_types_all = Counter(item["review_type"] for item in classified
                               if item["proxy_label"] == REVIEW_LABEL)
    review_types_top = Counter(row["review_type"] for row in review_top)
    gaps = sorted(row["score_gap"] for row in review_rows)
    n_gold_pos = sum(1 for row in gold_rows if row["proxy_label"] == POSITIVE_LABEL)
    n_gold_neg = sum(1 for row in gold_rows if row["proxy_label"] == NEGATIVE_LABEL)

    summary = {
        "schema_version": "gold_proxy_v1",
        "exogenous_evaluation_only": True,
        "fold_map": {doc: fold for doc, fold in sorted(fold_map.items())},
        "fold_map_source": fold_map_source,
        "test_docs": sorted(test_docs),
        "thresholds": {
            "bge": {
                "theta": bge_thresholds["theta"],
                "theta_low": bge_thresholds["theta_low"],
                "theta_rule": "dev fold负例95%分位(nearest-rank)",
                "theta_low_rule": "dev fold正例5%分位(nearest-rank)",
                "n_dev_pos": len(dev_pos_bge),
                "n_dev_neg": len(dev_neg_bge),
            },
            "qwen3": {
                "theta": qwen3_thresholds["theta"],
                "theta_low": qwen3_thresholds["theta_low"],
                "theta_rule": "dev fold负例95%分位(nearest-rank)",
                "theta_low_rule": "dev fold正例5%分位(nearest-rank)",
                "n_dev_pos": len(dev_pos_qwen),
                "n_dev_neg": len(dev_neg_qwen),
            },
        },
        "test_stats": {
            "n_pairs_total": len(test_pairs),
            "n_pairs_scored": len(classified),
            "n_rule_positive": n_pos,
            "n_rule_negative": n_neg,
            "rule_positive_ratio": round(n_pos / max(len(classified), 1), 4),
            "missing_endpoints": test_missing,
        },
        "counts": {
            "gold_proxy_positive": n_gold_pos,
            "gold_proxy_negative": n_gold_neg,
            "review_total": len(review_rows),
            "review_written": n_review,
            "gold_proxy_pairs_file": n_gold,
        },
        "auc_vs_rule_labels": aucs,
        "agreement": {
            "dual_encoder_on_rule_positives": {
                **pos_patterns,
                "agreement_rate": round(agreement_pos, 4),
            },
            "dual_encoder_on_rule_negatives": {
                **neg_patterns,
                "agreement_rate": round(agreement_neg, 4),
            },
            "spearman_bge_qwen3_test": round(spear, 4),
        },
        "review_type_distribution": {
            "all_review": dict(sorted(review_types_all.items())),
            "written_top_n": dict(sorted(review_types_top.items())),
        },
        "review_score_gap_stats": {
            "mean": round(sum(gaps) / max(len(gaps), 1), 4),
            "median": round(gaps[len(gaps) // 2] if gaps else 0.0, 4),
            "max": round(gaps[-1] if gaps else 0.0, 4),
        },
        "policy": {
            "exogenous_only": True,
            "silver_bound_not_gold": True,
            "no_identifier_positive_limit": (
                "gold_proxy正例必须为P1显式ID正例——无共享显式ID的正例在本构造下为0条"
                "(覆盖率局限: 无ID同指pair只能落入review_queue)"
            ),
            "threshold_calibration_split": "dev(θ与θ_low仅用dev fold校准)",
            "gold_pairs_source_split": "test(防泄漏: 永不进入训练/校准split)",
            "qwen3_input_parity": "Qwen3输入=feature_snapshot_v1同款200字符截断文本(编码器间分歧只反映编码器差异)",
            "review_queue_top_n": REVIEW_TOP_N,
        },
        "inputs": {
            "pairs": str(PAIRS_PATH),
            "pairs_sha256": sha256_file(PAIRS_PATH),
            "snapshot_dir": str(SNAPSHOT_DIR),
            "vectors_sha256": sha256_file(SNAPSHOT_DIR / "vectors.npz"),
            "features_sha256": sha256_file(SNAPSHOT_DIR / "features.jsonl"),
            "qwen3_model_dir": str(QWEN_MODEL_DIR),
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = {
        "schema_version": "gold_proxy_v1",
        "files": {
            name: sha256_file(out_dir / name)
            for name in ("gold_proxy_pairs.jsonl", "review_queue.jsonl", "summary.json")
        },
        "exogenous_evaluation_only": True,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )

    verification = verify_written_gold(
        out_dir / "gold_proxy_pairs.jsonl", bge_thresholds, qwen3_thresholds
    )
    if verification["violations"]:
        raise SystemExit(f"落盘复核失败(共识规则/防泄漏标注违反): {verification['violations'][:5]}")

    print("\n=== 验证实验: gold_proxy正例双编码器一致率(落盘复核) ===")
    print(
        "gold_proxy_positive: n={} 双编码器一致率={}".format(
            verification["n_gold_proxy_positive"], verification["gold_proxy_positive_consistency"]
        )
    )
    print(
        "双编码器阈值分歧率: P1正例agreement={:.4f} sibling负例agreement={:.4f} "
        "spearman={:.4f}".format(agreement_pos, agreement_neg, spear)
    )
    print(
        "分歧样本: review={}/{} ({:.1%}), 类型分布={}".format(
            len(review_rows), len(classified), len(review_rows) / max(len(classified), 1),
            dict(sorted(review_types_all.items())),
        )
    )

    print("\n=== 对照表(test fold, 规则标签为参照) ===")
    header = "{:<34}{:>8}{:>12}{:>12}"
    print(header.format("signal", "n", "与规则一致", "规则内召回"))
    print(header.format("-" * 34, "-" * 8, "-" * 12, "-" * 12))

    def print_signal(name: str, passed: int, hit_rule: int, rule_total: int) -> None:
        precision = hit_rule / max(passed, 1)
        recall = hit_rule / max(rule_total, 1)
        print(header.format(name, str(passed), f"{precision:.4f}", f"{recall:.4f}"))

    bge_pos_hits = sum(
        1 for item in rule_pos if item["bge_cos"] >= bge_thresholds["theta"]
    )
    bge_pos_n = sum(1 for item in classified if item["bge_cos"] >= bge_thresholds["theta"])
    qwen_pos_hits = sum(
        1 for item in rule_pos if item["qwen_cos"] >= qwen3_thresholds["theta"]
    )
    qwen_pos_n = sum(1 for item in classified if item["qwen_cos"] >= qwen3_thresholds["theta"])
    bge_neg_hits = sum(
        1 for item in rule_neg if item["bge_cos"] < bge_thresholds["theta_low"]
    )
    bge_neg_n = sum(1 for item in classified if item["bge_cos"] < bge_thresholds["theta_low"])
    qwen_neg_hits = sum(
        1 for item in rule_neg if item["qwen_cos"] < qwen3_thresholds["theta_low"]
    )
    qwen_neg_n = sum(1 for item in classified if item["qwen_cos"] < qwen3_thresholds["theta_low"])
    print_signal("P1规则(定义层) 正例", n_pos, n_pos, n_pos)
    print_signal("BGE cos>=θ_bge", bge_pos_n, bge_pos_hits, n_pos)
    print_signal("Qwen3 cos>=θ_qwen", qwen_pos_n, qwen_pos_hits, n_pos)
    print_signal("三信号共识 gold_proxy_positive", n_gold_pos, n_gold_pos, n_pos)
    print_signal("P1规则(定义层) 负例", n_neg, n_neg, n_neg)
    print_signal("BGE cos<θ_bge_low", bge_neg_n, bge_neg_hits, n_neg)
    print_signal("Qwen3 cos<θ_qwen_low", qwen_neg_n, qwen_neg_hits, n_neg)
    print_signal("三信号共识 gold_proxy_negative", n_gold_neg, n_gold_neg, n_neg)

    run = open_run(
        "build_gold_proxy",
        {
            "pairs": str(PAIRS_PATH),
            "snapshot_dir": str(SNAPSHOT_DIR),
            "qwen3_model_dir": str(QWEN_MODEL_DIR),
            "out_dir": str(out_dir),
            "fold_map": {doc: fold for doc, fold in sorted(fold_map.items())},
            "fold_map_source": fold_map_source,
            "primary_q": PRIMARY_Q,
            "low_q": LOW_Q,
            "review_top_n": REVIEW_TOP_N,
            "expected_test_docs": sorted(EXPECTED_TEST_DOCS),
            "n_dev_pairs": len(dev_pairs),
            "n_test_pairs": len(test_pairs),
            "n_dev_scored": len(dev_bge),
            "n_test_scored": len(classified),
            "thresholds": {
                "bge": bge_thresholds,
                "qwen3": qwen3_thresholds,
            },
            "qwen3_protocol": "embed_docs双侧, 输入=快照200字符截断文本",
        },
        RUNS_ROOT,
    )
    run.save_result(summary)
    run.log(
        gold_positive=n_gold_pos, gold_negative=n_gold_neg, review_total=len(review_rows),
        verification_violations=len(verification["violations"]),
    )
    print(f"\n产出: {out_dir}")
    print(f"  gold_proxy_pairs.jsonl  n={n_gold} (正{n_gold_pos}/负{n_gold_neg})")
    print(f"  review_queue.jsonl     n={n_review} (review_total={len(review_rows)})")
    print("  summary.json + manifest.json")
    print(f"run saved: {run.path}")


if __name__ == "__main__":
    main()
