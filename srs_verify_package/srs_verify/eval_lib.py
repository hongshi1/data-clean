"""Shared evaluation infrastructure for the frozen scene1 QA corpus (Wave 8-H1).

Deduplication home of the load → build → run → score skeleton previously
copy-pasted across tools/eval_*.py. Every function is a pure extraction of
existing tool code; the behavior-preservation contract is that all recorded
evaluation numbers stay bit-identical (regression fixtures live in
tests/test_eval_lib.py; the frozen-corpus numbers are re-verified by the
per-tool before/after diffs of the refactoring run).

Conventions frozen from the extracted tools:
- macro-F1 = round(mean of UNROUNDED per-class F1, 4).  One historical
  lineage (eval_cascade et al.) averaged the *rounded* per-class F1s;
  on every recorded run of the frozen corpus the two coincide, and the
  single recorded divergence (eval_paper_matrix "-e1_expert" = 0.8289)
  requires the unrounded mean — so the unrounded mean is the one canonical
  form here.
- per-class P/R/F1 and accuracy are rounded to 4 decimals.
- confusion dict keys are "pred|gold" (non-zero cells only), iterated in
  LABELS order (support/refute/not_in_evidence).
- QAInput field mapping follows the request_from_dict contract
  (completeness defaults to "unknown"; source_ref/scope_id required).

Module-level I/O: none — all file access happens inside functions.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from srs_verify.qa_models import (
    QAInput,
    RetrievedEvidence,
    SourceRef,
    VerificationResult,
)

BASE = Path(__file__).resolve().parents[2]
QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")

#: three-way verdict classes, iteration order of every metric loop
LABELS: tuple[str, ...] = ("support", "refute", "not_in_evidence")

#: verdict column candidates, first present key wins (silver: final_verdict)
DEFAULT_VERDICT_KEYS: tuple[str, ...] = ("final_verdict", "gold_verdict")

_ROW_REQUIRED = ("instance_id", "question", "answer", "context_freeze_id",
                 "evidence")
_EVIDENCE_REQUIRED = ("evidence_id", "text", "source_type", "source_ref",
                      "scope_id")

Metrics = dict[str, Any]


# ── data loading ────────────────────────────────────────────────────────────


def read_jsonl(path: Path) -> list[dict]:
    """jsonl→list[dict] (空行跳过, 与既有各评测工具的读取一致)."""
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def _check_frozen_row(row: dict, path: Path, index: int) -> None:
    if not isinstance(row, dict):
        raise ValueError(f"{path}第{index + 1}行不是JSON对象: {type(row).__name__}")
    missing = [key for key in _ROW_REQUIRED if key not in row]
    if missing:
        raise ValueError(f"{path}第{index + 1}行缺字段: {missing}")
    iid = str(row["instance_id"] or "")
    if not iid:
        raise ValueError(f"{path}第{index + 1}行instance_id为空")
    evidence = row["evidence"]
    if not isinstance(evidence, list):
        raise ValueError(f"{path}第{index + 1}行({iid})evidence不是列表")
    for position, item in enumerate(evidence):
        absent = [key for key in _EVIDENCE_REQUIRED if key not in item]
        if absent:
            raise ValueError(
                f"{path}第{index + 1}行({iid})evidence[{position}]缺字段: {absent}")
        if not isinstance(item["source_ref"], dict):
            raise ValueError(
                f"{path}第{index + 1}行({iid})evidence[{position}]"
                f"source_ref不是对象")


def load_frozen_qa(path: Path = QA_FROZEN) -> list[dict]:
    """读取冻结QA语料(jsonl+schema校验: 行/证据必填字段与id唯一性)."""
    rows = read_jsonl(path)
    seen: set[str] = set()
    for index, row in enumerate(rows):
        _check_frozen_row(row, path, index)
        iid = str(row["instance_id"])
        if iid in seen:
            raise ValueError(f"{path}instance_id重复: {iid}")
        seen.add(iid)
    return rows


def label_verdict(label_row: dict, iid: str,
                  verdict_keys: Sequence[str] = DEFAULT_VERDICT_KEYS) -> str:
    """标签行→三态verdict(依次取第一个存在键; 非法值报错, 不静默)."""
    verdict = None
    for key in verdict_keys:
        if key in label_row:
            verdict = label_row[key]
            break
    if verdict not in LABELS:
        raise ValueError(
            f"{iid}: 标签verdict非法: {verdict!r}(合法: {LABELS})")
    return verdict


def load_silver_labels(path: Path = SILVER,
                       verdict_keys: Sequence[str] = ("final_verdict",)
                       ) -> dict[str, str]:
    """silver标签文件→{instance_id: verdict}(重复id/缺id/非法verdict报错)."""
    labels: dict[str, str] = {}
    for row in read_jsonl(path):
        iid = str(row.get("instance_id", "") or "")
        if not iid:
            raise ValueError(f"标签文件{path}含缺instance_id的行")
        if iid in labels:
            raise ValueError(f"标签文件{path}instance_id重复: {iid}")
        labels[iid] = label_verdict(row, iid, verdict_keys)
    return labels


def load_label_rows(path: Path = SILVER) -> dict[str, dict]:
    """silver标签文件→{instance_id: 原始行}(需claims等完整字段时用)."""
    rows: dict[str, dict] = {}
    for row in read_jsonl(path):
        iid = str(row.get("instance_id", "") or "")
        if not iid:
            raise ValueError(f"标签文件{path}含缺instance_id的行")
        if iid in rows:
            raise ValueError(f"标签文件{path}instance_id重复: {iid}")
        rows[iid] = row
    return rows


# ── QAInput construction (SourceRef six-field mapping lives here) ───────────


def build_qa_input(record: dict[str, Any]) -> QAInput:
    """dict→QAInput: 与request_from_dict逐字段一致的唯一权威映射.

    SourceRef按kwargs映射六字段(doc_id/section/page/block_id/row_id/
    region_id, 缺省字段用dataclass默认); completeness缺省"unknown";
    source_ref/scope_id为必填(缺失即报错, 不静默).
    """
    evidence = tuple(
        RetrievedEvidence(
            evidence_id=str(item["evidence_id"]),
            text=str(item["text"]),
            source_type=item["source_type"],
            source_ref=SourceRef(**item["source_ref"]),
            scope_id=str(item["scope_id"]),
            completeness=item.get("completeness", "unknown"),
            completeness_proof=str(item.get("completeness_proof", "")),
            extraction_method=str(item.get("extraction_method", "")),
            extraction_confidence=item.get("extraction_confidence"),
        ) for item in record["evidence"]
    )
    return QAInput(
        instance_id=str(record["instance_id"]),
        question=str(record["question"]),
        answer=str(record["answer"]),
        context_freeze_id=str(record["context_freeze_id"]),
        evidence=evidence,
    )


def iter_qa_inputs(records: Iterable[dict[str, Any]]) -> Iterator[QAInput]:
    for record in records:
        yield build_qa_input(record)


# ── metrics (confusion keys are (predicted, gold) tuples) ───────────────────


def prf(confusion: Counter, label: str,
        labels: Sequence[str] = LABELS) -> tuple[float, float, float]:
    """单类precision/recall/f1(不取整, 供macro聚合与bootstrap用)."""
    tp = confusion[(label, label)]
    fp = sum(confusion[(label, gold)] for gold in labels if gold != label)
    fn = sum(confusion[(pred, label)] for pred in labels if pred != label)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if precision + recall else 0.0)
    return precision, recall, f1


def per_class_metrics(confusion: Counter,
                      labels: Sequence[str] = LABELS) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for label in labels:
        precision, recall, f1 = prf(confusion, label, labels)
        out[label] = {"precision": round(precision, 4),
                      "recall": round(recall, 4), "f1": round(f1, 4)}
    return out


def macro_f1_raw(confusion: Counter, labels: Sequence[str] = LABELS) -> float:
    """未取整macro-F1(bootstrap差值/未取整打印场景)."""
    return sum(prf(confusion, label, labels)[2]
               for label in labels) / len(labels)


def macro_f1(confusion: Counter, labels: Sequence[str] = LABELS) -> float:
    return round(macro_f1_raw(confusion, labels), 4)


def accuracy(confusion: Counter, n: int,
             labels: Sequence[str] = LABELS) -> float:
    if n <= 0:
        raise ValueError(f"accuracy分母n须>0: n={n}")
    correct = sum(confusion[(p, g)] for p in labels for g in labels if p == g)
    return round(correct / n, 4)


def confusion_dict(confusion: Counter,
                   labels: Sequence[str] = LABELS) -> dict[str, int]:
    """Counter→"pred|gold"键的非零格字典(LABELS序, 与既有输出一致)."""
    return {f"{p}|{g}": confusion[(p, g)]
            for p in labels for g in labels if confusion[(p, g)]}


def confusion_of(y_pred: Sequence[str], y_true: Sequence[str],
                 labels: Sequence[str] = LABELS) -> Counter:
    """逐对构造(predicted, gold)计数器; 非法verdict报错."""
    if len(y_pred) != len(y_true):
        raise ValueError(f"y_pred与y_true长度不一致: {len(y_pred)} vs {len(y_true)}")
    confusion: Counter = Counter()
    for pred, gold in zip(y_pred, y_true):
        if pred not in labels or gold not in labels:
            raise ValueError(f"verdict超出三态契约: pred={pred!r} gold={gold!r}")
        confusion[(pred, gold)] += 1
    return confusion


def confusion_matrix(y_true: Sequence[str], y_pred: Sequence[str],
                     labels: Sequence[str] = LABELS) -> dict[str, int]:
    """"pred|gold"非零格混淆矩阵(输入为标签列表)."""
    return confusion_dict(confusion_of(y_pred, y_true, labels), labels)


def classification_metrics(y_true: Sequence[str], y_pred: Sequence[str],
                           labels: Sequence[str] = LABELS) -> Metrics:
    """三态分类指标: accuracy/macro_f1/per_class/confusion("pred|gold")."""
    confusion = confusion_of(y_pred, y_true, labels)
    return {
        "accuracy": accuracy(confusion, len(y_true), labels),
        "macro_f1": macro_f1(confusion, labels),
        "per_class": per_class_metrics(confusion, labels),
        "confusion": confusion_dict(confusion, labels),
    }


# ── corpus run + scoring (公共骨架) ─────────────────────────────────────────


def run_module_corpus(module, records: Iterable[dict]) -> dict[str, dict]:
    """跑module.verify于全部records→{instance_id: outcome}.

    outcome含verdict/status/diagnostics与claim明细(rationale截断200,
    与eval_cascade/eval_nli_residual/eval_llm_residual的既有schema一致).
    """
    outcomes: dict[str, dict] = {}
    for record in records:
        request = build_qa_input(record)
        result: VerificationResult = module.verify(request)
        outcomes[request.instance_id] = {
            "verdict": result.verdict,
            "status": result.status,
            "diagnostics": list(result.diagnostics),
            "claims": [{
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "verdict": claim.verdict,
                "method": claim.method,
                "confidence": claim.confidence,
                "evidence_refs": list(claim.evidence_refs),
                "rationale": claim.rationale[:200],
            } for claim in result.claim_results],
        }
    return outcomes


def score_outcomes(outcomes: dict[str, dict], records: Sequence[dict],
                   labels: dict[str, str]) -> Metrics:
    """已跑outcomes+silver标签→指标dict(eval_cascade系score_config的schema)."""
    confusion: Counter = Counter()
    methods: Counter = Counter()
    for record in records:
        iid = record["instance_id"]
        confusion[(outcomes[iid]["verdict"], labels[iid])] += 1
        methods.update(claim["method"] for claim in outcomes[iid]["claims"])
    return {
        "accuracy": accuracy(confusion, len(records)),
        "macro_f1": macro_f1(confusion),
        "per_class": per_class_metrics(confusion),
        "confusion[predicted, silver]": confusion_dict(confusion),
        "claim_methods": dict(methods),
    }


@dataclass
class EvalResult:
    """evaluate_module的产物: 逐实例明细+聚合指标(缺标签实例不进指标分母)."""

    n: int
    n_evaluated: int
    missing_labels: list[str]
    confusion: Counter
    methods: Counter
    statuses: Counter
    per_row: list[dict]
    metrics: Metrics


def evaluate_module(module, records: Sequence[dict],
                    labels: dict[str, str], **module_kwargs) -> EvalResult:
    """跑全部实例+聚合指标——单配置eval工具的公共骨架.

    module需提供verify(QAInput); module_kwargs原样转发给verify(默认不用).
    缺标签实例照常verify并进per_row(label=None), 但不进confusion/
    methods/statuses/指标分母(与eval_qa_module_vs_silver的gold语义一致);
    全部缺标签时抛ValueError(调用方决定如何退出).
    """
    confusion: Counter = Counter()
    methods: Counter = Counter()
    statuses: Counter = Counter()
    per_row: list[dict] = []
    missing_labels: list[str] = []
    for record in records:
        request = build_qa_input(record)
        result: VerificationResult = module.verify(request, **module_kwargs)
        gold = labels.get(request.instance_id)
        per_row.append({
            "instance_id": request.instance_id,
            "predicted": result.verdict,
            "label": gold,
            "status": result.status,
            "claim_methods": [claim.method for claim in result.claim_results],
            "claims": [{
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "verdict": claim.verdict,
                "method": claim.method,
                "confidence": claim.confidence,
                "evidence_refs": list(claim.evidence_refs),
                "rationale": claim.rationale,
            } for claim in result.claim_results],
            "diagnostics": list(result.diagnostics),
        })
        if gold is None:
            missing_labels.append(request.instance_id)
            continue
        confusion[(result.verdict, gold)] += 1
        methods.update(claim.method for claim in result.claim_results)
        statuses[result.status] += 1
    n_evaluated = len(records) - len(missing_labels)
    if n_evaluated == 0:
        raise ValueError("标签与冻结QA无共同instance_id, 无法评测")
    y_true = [row["label"] for row in per_row if row["label"] is not None]
    y_pred = [row["predicted"] for row in per_row if row["label"] is not None]
    return EvalResult(
        n=len(records),
        n_evaluated=n_evaluated,
        missing_labels=missing_labels,
        confusion=confusion,
        methods=methods,
        statuses=statuses,
        per_row=per_row,
        metrics=classification_metrics(y_true, y_pred),
    )
