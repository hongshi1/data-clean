"""L2 NLI residual verification channel (S4: residual domain adaptation).

Mirrors ``llm_residual`` (L3) on the same C1 residual principle: only claims
the deterministic channels left unresolved (``semantic_unresolved`` /
``conservative_unresolved``) are judged, and every returned ClaimResult reuses
the residual claim's id so the caller's per-claim fusion can replace the
unresolved NIE. The judge is the locally fine-tuned mDeBERTa checkpoint
(tools/train_residual_nli.py, EGT v3-narrative corpus) — pure local
inference, no LLM calls, ~1/10 of the LLM channel's cost.

Premise construction is SHARED with training (``nli_training.select_statements``
+ ``build_premise``): statements are ranked per claim by scope hit + bigram
overlap with claim+question (the question anchors the scope object, as in the
LLM prompt), capped at the same character budget and restored to document
order — the S4 calibration lesson: an inference premise out of the training
distribution (larger, purely relevance-ordered) buys lexical-coverage
shortcuts (false support/refute), so both sides run one pipeline.

Gating: a verdict is only emitted when softmax max-probability reaches the
gate (default 0.6); below it the claim stays NIE — under-confident refutes
are suppressed instead of being guessed.

Hard rules: lazy model loading with a module-level cache (no repeat loads, no
I/O at import time), failures surface through ``nli_residual_unavailable``
ClaimResults (never silent), utf-8 everywhere.
"""
from __future__ import annotations

import re
from typing import Any

from algorithms.consistency.evidence_statements import EvidenceStatement
from algorithms.consistency.nli_local import MODELS, normalize_label
from algorithms.consistency.nli_training import (
    PREMISE_BUDGET,
    residual_premise,
)
from algorithms.consistency.qa_models import ClaimResult, QAInput

RESIDUAL_METHODS = ("semantic_unresolved", "conservative_unresolved")
VERDICTS = ("support", "refute", "not_in_evidence")

NLI_TO_VERDICT = {"entailment": "support", "contradiction": "refute",
                  "neutral": "not_in_evidence"}

DEFAULT_GATE = 0.7
DEFAULT_MODEL_KEY = "egt_finetuned_v2"
_MAX_LENGTH = 512
_BATCH_GPU = 16
_BATCH_CPU = 8


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


_MODEL_CACHE: dict[str, dict[str, Any]] = {}


def _load_model(model_path: str) -> dict[str, Any]:
    """惰性加载微调checkpoint (模块级缓存; 失败显式记录, 不静默)."""
    if model_path in _MODEL_CACHE:
        return _MODEL_CACHE[model_path]
    entry: dict[str, Any] = {"mode": "unavailable", "error": ""}
    try:
        import torch
        from transformers import (AutoModelForSequenceClassification,
                                  AutoTokenizer)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_path, local_files_only=True)
        model.to(device)
        model.eval()
        entry = {
            "mode": device,
            "tokenizer": tokenizer,
            "model": model,
            "torch": torch,
            "id2label": {int(k): normalize_label(str(v))
                         for k, v in model.config.id2label.items()},
            "error": "",
        }
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
    _MODEL_CACHE[model_path] = entry
    return entry


def _infer(entry: dict[str, Any], pairs: list[tuple[str, str]]
           ) -> list[dict[str, float]]:
    """批量 (premise, hypothesis) → 归一化三标签概率."""
    torch = entry["torch"]
    batch = _BATCH_GPU if entry["mode"] == "gpu" else _BATCH_CPU
    out: list[dict[str, float]] = []
    for start in range(0, len(pairs), batch):
        chunk = pairs[start:start + batch]
        enc = entry["tokenizer"](
            [p for p, _ in chunk], [h for _, h in chunk],
            padding=True, truncation="longest_first",
            max_length=_MAX_LENGTH, return_tensors="pt")
        enc = {k: v.to(entry["mode"]) for k, v in enc.items()}
        with torch.no_grad():
            logits = entry["model"](**enc).logits
            probs = torch.softmax(logits, dim=-1).float().cpu().tolist()
        for row in probs:
            named = {"entailment": 0.0, "neutral": 0.0, "contradiction": 0.0}
            for idx, prob in enumerate(row):
                label = entry["id2label"].get(idx, "neutral")
                named[label] = named.get(label, 0.0) + float(prob)
            out.append(named)
    return out


def verify_residual_claims_nli(
        request: QAInput,
        residual_results: list[ClaimResult],
        statements: list[EvidenceStatement],
        model_path: str = "",
        *,
        gate: float = DEFAULT_GATE,
) -> list[ClaimResult]:
    """用微调NLI模型判定残差claim (L2语义残差通道).

    Only unresolved claims (method semantic_unresolved/conservative_unresolved
    with NIE verdicts) belong in ``residual_results`` — the same C1 residual
    principle as the LLM channel. Returned results reuse the residual claim
    ids/texts; softmax最大概率低于gate时保守NIE.
    """
    if not residual_results or not statements:
        return []
    unique: list[ClaimResult] = []
    seen: set[str] = set()
    for result in residual_results:
        key = _compact(result.claim_text)
        if key and key not in seen:
            seen.add(key)
            unique.append(result)
    if not unique:
        return []

    path = model_path or MODELS[DEFAULT_MODEL_KEY]["dir"]
    entry = _load_model(path)
    if entry["mode"] == "unavailable":
        return [ClaimResult(
            claim_id=result.claim_id,
            claim_text=result.claim_text,
            verdict="not_in_evidence",
            check_item_candidates=result.check_item_candidates,
            evidence_refs=(),
            rationale=(f"NLI残差通道不可用({path}): {entry['error']}; 保守NIE"),
            method="nli_residual_unavailable",
            confidence=0.0,
        ) for result in unique]

    selected: list[list[tuple[int, str]]] = []
    premises: list[str] = []
    for result in unique:
        premise, picks = residual_premise(result.claim_text, request.question,
                                          statements, PREMISE_BUDGET)
        premises.append(premise)
        selected.append(picks)
    pairs = [(premise, result.claim_text)
             for premise, result in zip(premises, unique)
             if premise.strip()]
    probs = _infer(entry, pairs)

    results: list[ClaimResult] = []
    position = 0
    for result, premise, picks in zip(unique, premises, selected):
        if not premise.strip():
            results.append(ClaimResult(
                claim_id=result.claim_id,
                claim_text=result.claim_text,
                verdict="not_in_evidence",
                check_item_candidates=result.check_item_candidates,
                evidence_refs=(),
                rationale="NLI残差判定：premise构造为空，保守NIE",
                method="nli_residual",
                confidence=0.0,
            ))
            continue
        prob = probs[position]
        position += 1
        label = max(prob, key=lambda k: prob[k])
        confidence = prob[label]
        evidence_refs = tuple(sorted({statements[index].evidence_id
                                      for index, _ in picks}))
        notes: list[str] = []
        verdict = NLI_TO_VERDICT[label]
        if confidence < gate:
            notes.append(f"softmax最大概率{confidence:.2f}低于门控{gate:.2f}"
                         "，保守NIE")
            verdict = "not_in_evidence"
        if verdict == "not_in_evidence":
            evidence_refs = ()
        rationale = (f"NLI残差判定：{label}(p={confidence:.2f})，"
                     f"premise含{len(picks)}条证据语句")
        if notes:
            rationale += "（" + "；".join(notes) + "）"
        results.append(ClaimResult(
            claim_id=result.claim_id,
            claim_text=result.claim_text,
            verdict=verdict,
            check_item_candidates=result.check_item_candidates,
            evidence_refs=evidence_refs,
            rationale=rationale,
            method="nli_residual",
            confidence=round(confidence, 4),
        ))
    return results


__all__ = [
    "DEFAULT_GATE",
    "DEFAULT_MODEL_KEY",
    "RESIDUAL_METHODS",
    "VERDICTS",
    "verify_residual_claims_nli",
]
