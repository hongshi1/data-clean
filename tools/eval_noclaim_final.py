"""Claim-module final ablation (variant D): no claim decomposition at all.

Question under test (terminal ablation of the claim module): if the whole
answer is passed as ONE NLI hypothesis — ``decompose_claims`` replaced by
``lambda q, a: [AnswerClaim(kind="semantic", text=a)]`` — what do we lose?
Three dimensions are quantified against the recorded A_typed baseline:

1. 精度 (accuracy): acc / macro-F1 / per-class on the three frozen datasets
   (test46 / violations17 / crossdoc150). A_typed numbers are CITED from
   data/gjb_438c/distillation/decomp_ablation_v1.json (test46 mF1=0.8047,
   d1_paper_summary_v1.json) — not re-run.
2. 定位能力 (localization): on violations-17 detected refutes, the
   VerificationResult.localizations field (M84) is measured: block-level gold
   hit rate (gold_evidence_refs → block mapping, same as
   tools/measure_localization_baseline.py: A cited 16/16) + answer_span
   coverage. Under D the only claim IS the whole answer, so a claim-channel
   span covers the entire answer (ratio 1.0) — no assertion-level
   localization; sub-assertion spans can only come from the un-ablated
   L0/L1 expert channel (recorded honestly, split by origin).
3. 聚合语义 (aggregation): D has exactly one claim, so the strict ∀
   aggregation degenerates to a single-claim decision. For
   "partial-inconsistency" instances (gold=refute AND the typed decomposer
   yields ≥2 claims — the answer asserts several things and only part is
   wrong) we record whether D can attribute the refute to a specific
   assertion. It cannot via the claim channel (whole-answer span), by
   construction; expert-channel attribution is counted separately.

Granularity mismatch made explicit: the single long hypothesis goes
verify_semantic → unresolved → L2 NLI, where the premise is built by
``nli_residual.residual_premise`` under the training-time budget
(PREMISE_BUDGET=500 chars + GROUP_TOLERANCE=250) and the tokenizer truncates
the (premise, hypothesis) pair at 512 tokens — evidence gets truncated while
the hypothesis swallows the whole answer. Measured per instance
(deterministic recompute of the premise + token count via the cached
tokenizer, plus gold-evidence-in-premise coverage on violations-17).

Isolation: L0/L1 experts (id_join / enum_join / e1 / sequence / ...) consume
``answer_structure.decompose_answer`` directly and are NOT patched — the
ablation isolates exactly the per-claim typed channel + claim-level fusion
aggregation. Variant D config matches A/B:
QAConsistencyModule(use_experts=True, use_nli_residual=True,
nli_model_path="models/nli/distilled_v1", nli_gate=0.8), aggregation=strict.

Output: data/gjb_438c/distillation/noclaim_final_v1.json + console table.

Usage:
  python tools/eval_noclaim_final.py [--limit N] [--out PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import nli_residual  # noqa: E402
from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.answer_claims import (  # noqa: E402
    AnswerClaim,
    decompose_claims as typed_decompose,
)
from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.nli_residual import (  # noqa: E402
    _MAX_LENGTH as NLI_MAX_TOKENS,
)
from algorithms.consistency.nli_training import (  # noqa: E402
    PREMISE_BUDGET,
    residual_premise,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.qa_models import VerificationResult  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIOLATIONS = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
CROSSDOC_DOCS = ("05", "06", "07", "08", "10")
CROSSDOC_DIR = BASE / "data/gjb_438c/qa_frozen"
OUT_PATH = BASE / "data/gjb_438c/distillation/noclaim_final_v1.json"
DECOMP_ABLATION = BASE / "data/gjb_438c/distillation/decomp_ablation_v1.json"

NLI_MODEL_PATH = "models/nli/distilled_v1"
NLI_GATE = 0.8
DATASET_ORDER = ("test46", "violations17", "crossdoc150")

#: fallback A/B reference numbers if decomp_ablation_v1.json is missing
#: (primary source: that json itself; test46 mF1 0.8047 = d1_paper_summary_v1)
KNOWN_A_FALLBACK: dict[str, dict[str, float]] = {
    "test46": {"accuracy": 0.913, "macro_f1": 0.8047},
    "violations17": {"accuracy": 0.9412, "macro_f1": 0.3232},
    "crossdoc150": {"accuracy": 0.5133, "macro_f1": 0.5109},
}
#: A_typed localization baseline (tools/measure_localization_baseline.py run)
KNOWN_A_LOCALIZATION = {"detected_of_total": "16/17",
                        "block_hit_of_detected": "16/16",
                        "source": "cited: tools/measure_localization_baseline.py"}

#: span ratio at/above which a localization covers (essentially) the whole
#: answer — "no assertion-level localization" threshold
_WHOLE_ANSWER_RATIO = 0.999


# ── variant D: the whole answer as ONE claim ─────────────────────────────────


def noclaim_decompose(question: str, answer: str) -> list[AnswerClaim]:
    """Variant D decomposition: no claim module, the raw answer is one claim.

    ``question`` is accepted only for signature compatibility. The text is
    kept RAW (not stripped) so the M84 localization's ``answer.find`` spans
    the entire answer — that whole-answer span IS the point being measured.
    """
    del question
    if not answer.strip():
        return []
    return [AnswerClaim(kind="semantic", text=answer)]


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _answer_level_claim(result: VerificationResult, instance_id: str,
                        answer: str) -> tuple[dict[str, Any] | None, str]:
    """Locate the whole-answer claim inside the FUSED claim results.

    Order: (a) the per-claim channel's own id ``{iid}-c01``; (b) any claim
    whose compact text equals the compact answer (the D claim can be fused
    away by ``_fuse_per_claim`` when an expert emitted the same text — the
    surviving claim then carries the fused verdict).
    """
    per_claim_id = f"{instance_id}-c01"
    for claim in result.claim_results:
        if claim.claim_id == per_claim_id:
            return {"verdict": claim.verdict, "method": claim.method,
                    "confidence": claim.confidence}, "per_claim_c01"
    key = _compact(answer)
    for claim in result.claim_results:
        if _compact(claim.claim_text) == key:
            return {"verdict": claim.verdict, "method": claim.method,
                    "confidence": claim.confidence}, "fused_with_expert"
    return None, "absent"


def instance_detail(record: dict[str, Any], result: VerificationResult,
                    gold: str) -> dict[str, Any]:
    """Per-instance detail for the localization/aggregation analyses."""
    answer = str(record["answer"])
    iid = str(record["instance_id"])
    per_claim_id = f"{iid}-c01"
    claim_view, claim_source = _answer_level_claim(result, iid, answer)
    locs: list[dict[str, Any]] = []
    for loc in result.localizations:
        span = loc.answer_span
        ratio = (round((span[1] - span[0]) / len(answer), 4)
                 if span is not None and answer else None)
        locs.append({
            "claim_id": loc.claim_id,
            "origin": ("per_claim" if loc.claim_id == per_claim_id
                       else "expert"),
            "method": loc.method,
            "span": ([span[0], span[1]] if span is not None else None),
            "span_ratio": ratio,
            "blocks": sorted({el.block_id for el in loc.evidence
                              if el.block_id}),
            "n_statement_refs": sum(1 for el in loc.evidence
                                    if el.row_index >= 0),
        })
    return {
        "instance_id": iid,
        "gold": gold,
        "verdict": result.verdict,
        "answer_chars": len(answer),
        "n_fused_claims": len(result.claim_results),
        "answer_level_claim": claim_view,
        "answer_level_claim_source": claim_source,
        "localizations": locs,
    }


# ── data loading (照抄 tools/eval_decomp_ablation.py) ───────────────────────


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_datasets() -> dict[str, list[dict[str, Any]]]:
    records = load_frozen_qa()
    split = json.loads(SPLIT.read_text(encoding="utf-8"))
    test_ids = set(split["test"])
    test_recs = [r for r in records if str(r["instance_id"]) in test_ids]
    if len(test_recs) != len(test_ids):
        raise ValueError(f"test切分{len(test_ids)}条, 冻结语料只匹配到{len(test_recs)}条")
    vio_recs = read_jsonl(VIOLATIONS)
    if len(vio_recs) != 17:
        raise ValueError(f"violations评测集应17条, 实际{len(vio_recs)}条")
    cross_recs: list[dict[str, Any]] = []
    for doc in CROSSDOC_DOCS:
        rows = read_jsonl(CROSSDOC_DIR / f"crossdoc{doc}_evalset_v1.jsonl")
        if len(rows) != 30:
            raise ValueError(f"crossdoc{doc}子集应30条, 实际{len(rows)}条")
        cross_recs.extend(rows)
    if len(cross_recs) != 150:
        raise ValueError(f"crossdoc合并集应150条, 实际{len(cross_recs)}条")
    return {"test46": test_recs, "violations17": vio_recs,
            "crossdoc150": cross_recs}


def load_labels(datasets: dict[str, list[dict[str, Any]]]
                ) -> dict[str, dict[str, str]]:
    silver = load_silver_labels(SILVER)
    labels = {
        "test46": silver,
        "violations17": {str(r["instance_id"]): str(r["expected_verdict"])
                         for r in datasets["violations17"]},
        "crossdoc150": {str(r["instance_id"]): str(r["sound_label"])
                        for r in datasets["crossdoc150"]},
    }
    for name, recs in datasets.items():
        missing = [str(r["instance_id"]) for r in recs
                   if str(r["instance_id"]) not in labels[name]]
        if missing:
            raise ValueError(f"{name}缺标签实例: {missing[:5]}")
    return labels


# ── variant D run (monkeypatch + finally restore) ───────────────────────────


def claim_statistics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic claim stats for the D decomposer (1 claim/instance)."""
    total = 0
    lengths: list[int] = []
    kinds: Counter[str] = Counter()
    for record in records:
        for claim in noclaim_decompose(str(record["question"]),
                                       str(record["answer"])):
            total += 1
            lengths.append(len(claim.text))
            kinds[claim.kind] += 1
    n = len(records)
    return {
        "n_instances": n,
        "n_claims": total,
        "claims_per_instance": round(total / n, 2) if n else 0.0,
        "claim_len_avg": round(sum(lengths) / len(lengths), 1) if lengths else 0.0,
        "claim_len_max": max(lengths) if lengths else 0,
        "kind_distribution": dict(sorted(kinds.items())),
    }


def run_variant_d(datasets: dict[str, list[dict[str, Any]]],
                  labels: dict[str, dict[str, str]]
                  ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Run variant D over all datasets; monkeypatch restored in finally."""
    original = qa_module.decompose_claims
    qa_module.decompose_claims = noclaim_decompose
    try:
        module = QAConsistencyModule(
            use_experts=True,
            use_nli_residual=True,
            nli_model_path=NLI_MODEL_PATH,
            nli_gate=NLI_GATE,
        )
        if module._decomposer is not noclaim_decompose:
            raise RuntimeError(
                "variant D plumbing失效: module未捕获monkeypatch的decomposer"
                "(qa_module.decompose_claims的全局查找行为已变)")
        per_dataset: dict[str, Any] = {}
        details_by_ds: dict[str, list[dict[str, Any]]] = {}
        for ds_name in DATASET_ORDER:
            records = datasets[ds_name]
            y_true: list[str] = []
            y_pred: list[str] = []
            preds: dict[str, str] = {}
            details: list[dict[str, Any]] = []
            unavailable = False
            for record in records:
                request = build_qa_input(record)
                result = module.verify(request)
                preds[request.instance_id] = result.verdict
                if any(claim.method == "nli_residual_unavailable"
                       for claim in result.claim_results):
                    unavailable = True
                gold = labels[ds_name][request.instance_id]
                y_true.append(gold)
                y_pred.append(result.verdict)
                details.append(instance_detail(record, result, gold))
            if unavailable:
                print(f"WARNING: D_noclaim/{ds_name}: NLI残差模型不可用"
                      "(结果退化为无L2, 检查models/nli/distilled_v1)")
            metrics = classification_metrics(y_true, y_pred)
            per_dataset[ds_name] = {
                "metrics": metrics,
                "claim_stats": claim_statistics(records),
                "per_instance_verdicts": preds,
            }
            details_by_ds[ds_name] = details
            refute = metrics["per_class"]["refute"]
            stats = per_dataset[ds_name]["claim_stats"]
            print(f"[D_noclaim] {ds_name:12s} n={len(records):3d} "
                  f"acc={metrics['accuracy']:.4f} "
                  f"mF1={metrics['macro_f1']:.4f} "
                  f"refuteF1={refute['f1']:.3f} "
                  f"claims={stats['n_claims']} "
                  f"({stats['claims_per_instance']}/inst)")
        return per_dataset, details_by_ds
    finally:
        qa_module.decompose_claims = original
        assert qa_module.decompose_claims is original, (
            "variant D monkeypatch未恢复: qa_module.decompose_claims被污染")


# ── dimension 2: localization on violations-17 ───────────────────────────────


def localization_summary(
        records: list[dict[str, Any]],
        details: list[dict[str, Any]]) -> dict[str, Any]:
    """Block-level gold hit rate + answer_span coverage for D's refutes.

    gold_evidence_refs → block mapping copied from
    tools/measure_localization_baseline.py.
    """
    rec_by_id = {str(r["instance_id"]): r for r in records}
    detected = [d for d in details if d["verdict"] == "refute"]
    n_hit = 0
    n_localized = 0
    origins: Counter[str] = Counter()
    span_ratios: list[float] = []
    whole_answer_locs = 0
    sub_assertion_locs = 0
    span_unresolved = 0
    statement_refs = 0
    per_claim_locs = 0
    per_instance: list[dict[str, Any]] = []
    for detail in detected:
        record = rec_by_id[detail["instance_id"]]
        request = build_qa_input(record)
        ev_by_id = {ev.evidence_id: ev for ev in request.evidence}
        gold_blocks: set[str] = set()
        for ref in record.get("gold_evidence_refs") or []:
            ev = ev_by_id.get(str(ref))
            if ev is not None and ev.source_ref.block_id:
                gold_blocks.add(str(ev.source_ref.block_id))
        cited: set[str] = set()
        for loc in detail["localizations"]:
            cited.update(loc["blocks"])
            origins[loc["origin"]] += 1
            statement_refs += loc["n_statement_refs"]
            if loc["origin"] == "per_claim":
                per_claim_locs += 1
            if loc["span_ratio"] is None:
                span_unresolved += 1
            else:
                span_ratios.append(loc["span_ratio"])
                if loc["span_ratio"] >= _WHOLE_ANSWER_RATIO:
                    whole_answer_locs += 1
                else:
                    sub_assertion_locs += 1
        if cited:
            n_localized += 1
        hit = bool(gold_blocks and (cited & gold_blocks))
        if hit:
            n_hit += 1
        per_instance.append({
            "instance_id": detail["instance_id"],
            "n_localizations": len(detail["localizations"]),
            "localization_methods": [loc["method"]
                                     for loc in detail["localizations"]],
            "cited_blocks": sorted(cited),
            "gold_blocks": sorted(gold_blocks),
            "block_hit": hit,
            "span_ratios": [loc["span_ratio"]
                            for loc in detail["localizations"]],
        })
    n = len(detected)
    return {
        "detected": n,
        "total": len(records),
        "localized": n_localized,
        "block_hit": n_hit,
        "block_hit_rate_of_detected": round(n_hit / n, 4) if n else None,
        "localizations_by_origin": dict(sorted(origins.items())),
        "per_claim_channel_localizations": per_claim_locs,
        "whole_answer_span_localizations": whole_answer_locs,
        "sub_assertion_span_localizations": sub_assertion_locs,
        "span_unresolved_localizations": span_unresolved,
        "span_ratio_avg": (round(sum(span_ratios) / len(span_ratios), 4)
                           if span_ratios else None),
        "span_ratio_max": (max(span_ratios) if span_ratios else None),
        "statement_level_refs": statement_refs,
        "per_instance": per_instance,
    }


# ── granularity mismatch: premise budget vs whole-answer hypothesis ─────────


def _cached_tokenizer() -> Any:
    """Tokenizer from nli_residual's module cache (None if not loaded)."""
    for entry in nli_residual._MODEL_CACHE.values():
        if str(entry.get("mode", "")) not in ("", "unavailable"):
            return entry["tokenizer"]
    return None


def premise_granularity_analysis(
        records: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic recompute of the D claim's NLI premise per instance.

    The module-side premise is built by residual_premise (PREMISE_BUDGET=500
    chars + GROUP_TOLERANCE=250); the (premise, whole-answer) pair is then
    tokenized with max_length=512 truncation. Here we recompute the premise
    (pure function of frozen inputs) and count token overflow + gold
    evidence coverage, quantifying the granularity mismatch.
    """
    tokenizer = _cached_tokenizer()
    per_instance: list[dict[str, Any]] = []
    n_overflow = 0
    n_gold = 0
    n_gold_covered = 0
    for record in records:
        request = build_qa_input(record)
        statements = linearize_context(request.evidence)
        answer = str(record["answer"])
        premise, picks = residual_premise(answer, str(record["question"]),
                                          statements, PREMISE_BUDGET)
        gold_ids = {str(r) for r in record.get("gold_evidence_refs") or []}
        picked_ids = {statements[index].evidence_id for index, _ in picks}
        entry: dict[str, Any] = {
            "instance_id": str(record["instance_id"]),
            "answer_chars": len(answer),
            "premise_chars": len(premise),
            "n_premise_statements": len(picks),
        }
        if gold_ids:
            entry["gold_in_premise"] = bool(picked_ids & gold_ids)
            n_gold += 1
            n_gold_covered += int(bool(picked_ids & gold_ids))
        if tokenizer is not None and premise.strip():
            # truncation deliberately OFF: we count the pair's true token
            # length to detect the inference-side longest_first truncation
            # (verbose=False suppresses the >max_length warning)
            tokens = len(tokenizer(premise, answer, verbose=False)
                         ["input_ids"])
            entry["pair_tokens"] = tokens
            if tokens > NLI_MAX_TOKENS:
                n_overflow += 1
        per_instance.append(entry)
    answers = [e["answer_chars"] for e in per_instance]
    premises = [e["premise_chars"] for e in per_instance]
    return {
        "n_instances": len(per_instance),
        "answer_chars_avg": (round(sum(answers) / len(answers), 1)
                             if answers else 0.0),
        "premise_chars_avg": (round(sum(premises) / len(premises), 1)
                              if premises else 0.0),
        "premise_budget_chars": PREMISE_BUDGET,
        "nli_max_tokens": NLI_MAX_TOKENS,
        "tokenizer_available": tokenizer is not None,
        "pair_token_overflow": n_overflow,
        "pair_token_overflow_rate": (round(n_overflow / len(per_instance), 4)
                                     if per_instance else None),
        "gold_evidence_in_premise": (f"{n_gold_covered}/{n_gold}"
                                     if n_gold else None),
        "per_instance": per_instance,
    }


# ── dimension 3: aggregation semantics ──────────────────────────────────────


def d_claim_verdict_distribution(
        details: list[dict[str, Any]]) -> dict[str, Any]:
    """Effective verdict of the whole-answer claim across instances."""
    verdicts: Counter[str] = Counter()
    methods: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for detail in details:
        claim = detail["answer_level_claim"]
        sources[detail["answer_level_claim_source"]] += 1
        if claim is not None:
            verdicts[claim["verdict"]] += 1
            methods[claim["method"]] += 1
    return {
        "answer_level_claim_source": dict(sorted(sources.items())),
        "verdicts": dict(sorted(verdicts.items())),
        "methods": dict(sorted(methods.items())),
    }


def partial_inconsistency_analysis(
        datasets: dict[str, list[dict[str, Any]]],
        details_by_ds: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Partial-inconsistency instances under D (aggregation semantics).

    Definition: gold=refute AND the typed decomposer yields ≥2 claims —
    the answer asserts several things, at most part of them is wrong. Under
    D the claim channel has exactly one whole-answer claim, so it can never
    attribute the refute to a specific assertion (span covers the whole
    answer); expert-channel attribution is counted separately, honestly.
    """
    per_instance: list[dict[str, Any]] = []
    for ds_name in DATASET_ORDER:
        records = datasets[ds_name]
        for record, detail in zip(records, details_by_ds[ds_name]):
            if detail["gold"] != "refute":
                continue
            n_typed = len(typed_decompose(str(record["question"]),
                                          str(record["answer"])))
            if n_typed < 2:
                continue
            locs = detail["localizations"]
            claim_isolated = any(
                loc["origin"] == "per_claim" and loc["span_ratio"] is not None
                and loc["span_ratio"] < _WHOLE_ANSWER_RATIO for loc in locs)
            expert_isolated = any(
                loc["origin"] == "expert" and loc["span_ratio"] is not None
                and loc["span_ratio"] < _WHOLE_ANSWER_RATIO for loc in locs)
            per_instance.append({
                "dataset": ds_name,
                "instance_id": detail["instance_id"],
                "n_typed_claims": n_typed,
                "answer_chars": detail["answer_chars"],
                "d_verdict": detail["verdict"],
                "detected_by_d": detail["verdict"] == "refute",
                "answer_level_claim": detail["answer_level_claim"],
                "n_localizations": len(locs),
                "assertion_isolated_by_claim_channel": claim_isolated,
                "assertion_isolated_by_expert_channel": expert_isolated,
            })
    n = len(per_instance)
    return {
        "definition": ("gold=refute 且 typed分解≥2条claim (answer含多条断言, "
                       "不一致至多为部分; typed分解=variant A的断言粒度)"),
        "n_partial_instances": n,
        "n_detected_by_d": sum(1 for x in per_instance if x["detected_by_d"]),
        "n_assertion_isolated_by_claim_channel": sum(
            1 for x in per_instance
            if x["assertion_isolated_by_claim_channel"]),
        "n_assertion_isolated_by_expert_channel": sum(
            1 for x in per_instance
            if x["assertion_isolated_by_expert_channel"]),
        "claim_channel_note": ("D的claim通道只有一条整answer claim, span覆盖"
                              "全句(ratio≈1.0)或find失败, 断言级定位为0——"
                              "聚合退化为单claim判定, 无法归因到具体断言"),
        "per_instance": per_instance,
    }


# ── A→D verdict flips (A per-instance verdicts cited from v1 json) ──────────


def flip_analysis_a_to_d(
        datasets: dict[str, list[dict[str, Any]]],
        labels: dict[str, dict[str, str]],
        a_preds_by_ds: dict[str, dict[str, str]] | None,
        d_preds_by_ds: dict[str, dict[str, str]]) -> dict[str, Any] | None:
    if a_preds_by_ds is None:
        return None
    out: dict[str, Any] = {}
    for ds_name in DATASET_ORDER:
        gold = labels[ds_name]
        corrected: list[str] = []
        regressed: list[str] = []
        other: list[str] = []
        for record in datasets[ds_name]:
            iid = str(record["instance_id"])
            before = a_preds_by_ds.get(ds_name, {}).get(iid)
            after = d_preds_by_ds.get(ds_name, {}).get(iid)
            if before is None or after is None or before == after:
                continue
            if after == gold[iid]:
                corrected.append(iid)
            elif before == gold[iid]:
                regressed.append(iid)
            else:
                other.append(iid)
        out[ds_name] = {
            "n_changed": len(corrected) + len(regressed) + len(other),
            "corrected_a_wrong_d_right": corrected,
            "regressed_a_right_d_wrong": regressed,
            "moved_both_wrong": other,
        }
    return out


# ── reporting ───────────────────────────────────────────────────────────────


def device_report() -> dict[str, Any]:
    try:
        import torch
        return {"torch_cuda_available": bool(torch.cuda.is_available())}
    except (ImportError, OSError):
        return {"torch_cuda_available": False}


def git_sha() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=BASE, capture_output=True,
            text=True, timeout=10, check=False)
        return proc.stdout.strip()[:12] if proc.returncode == 0 else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def nli_cache_mode() -> str:
    for entry in nli_residual._MODEL_CACHE.values():
        mode = str(entry.get("mode", ""))
        if mode and mode != "unavailable":
            return mode
    return "not_loaded"


def load_a_reference() -> dict[str, Any] | None:
    if not DECOMP_ABLATION.exists():
        return None
    return json.loads(DECOMP_ABLATION.read_text(encoding="utf-8"))


def _fmt_metric(m: dict[str, Any] | None, key: str) -> str:
    if m is None:
        return "  n/a "
    value = m.get(key)
    return f"{value:7.4f}" if isinstance(value, float) else f"{value!s:>7s}"


def print_report(report: dict[str, Any]) -> None:
    variants = report["variants"]
    ref = report["a_reference"]
    print("\n" + "=" * 78)
    print("claim module final ablation: A_typed(cited) vs D_noclaim(new) "
          f"({NLI_MODEL_PATH}, gate={NLI_GATE})")
    print("=" * 78)
    print("[维度1 精度]")
    header = (f"{'variant':11s} {'dataset':12s} {'n':>4s} {'acc':>7s} "
              f"{'mF1':>7s} {'rF1':>6s} {'cl/inst':>8s}")
    print(header)
    print("-" * len(header))
    for variant in ("A_typed", "B_sentence", "D_noclaim"):
        for ds_name in DATASET_ORDER:
            entry = variants[variant][ds_name]
            m = entry["metrics"]
            rc = m["per_class"]["refute"]
            if entry.get("cited"):
                print(f"{variant:11s} {ds_name:12s} "
                      f"{entry['n']:4d} {_fmt_metric(m, 'accuracy')} "
                      f"{_fmt_metric(m, 'macro_f1')} "
                      f"{rc['f1']:6.3f} "
                      f"{entry['claims_per_instance']:8.2f}   (cited)")
            else:
                print(f"{variant:11s} {ds_name:12s} "
                      f"{entry['n']:4d} {m['accuracy']:7.4f} "
                      f"{m['macro_f1']:7.4f} {rc['f1']:6.3f} "
                      f"{entry['claims_per_instance']:8.2f}")
    print("\nD_noclaim per-class P/R/F1:")
    for ds_name in DATASET_ORDER:
        pc = variants["D_noclaim"][ds_name]["metrics"]["per_class"]
        cells = " | ".join(
            f"{label}: P={pc[label]['precision']:.3f} "
            f"R={pc[label]['recall']:.3f} F1={pc[label]['f1']:.3f}"
            for label in ("support", "refute", "not_in_evidence"))
        print(f"  D_noclaim   {ds_name:12s} {cells}")

    loc = report["localization_violations17"]
    d_loc = loc["D_noclaim"]
    print("\n[维度2 定位] violations-17 (gold_evidence_refs→block命中)")
    print(f"  A_typed  (cited): 检出 {loc['A_typed']['detected_of_total']}, "
          f"块级命中 {loc['A_typed']['block_hit_of_detected']}")
    print(f"  D_noclaim (new) : 检出 {d_loc['detected']}/{d_loc['total']}, "
          f"有定位 {d_loc['localized']}, "
          f"块级命中 {d_loc['block_hit']}/{d_loc['detected']}")
    print(f"    定位来源分布 {d_loc['localizations_by_origin']}; "
          f"per-claim通道定位 {d_loc['per_claim_channel_localizations']}条")
    print(f"    answer_span: 整answer span {d_loc['whole_answer_span_localizations']}"
          f"条, 子断言span {d_loc['sub_assertion_span_localizations']}条"
          f"(专家通道), find失败 {d_loc['span_unresolved_localizations']}条; "
          f"span占比均值 {d_loc['span_ratio_avg']}")
    print(f"    语句级定位引用(row_index>=0) {d_loc['statement_level_refs']}")

    prem = report["premise_granularity"]
    for ds_name in DATASET_ORDER:
        p = prem[ds_name]
        print(f"\n[粒度失配] {ds_name}: answer平均{p['answer_chars_avg']}字符 "
              f"vs premise平均{p['premise_chars_avg']}字符"
              f"(预算{p['premise_budget_chars']}); "
              f"(premise+整answer)对超{p['nli_max_tokens']}token比例 "
              f"{p['pair_token_overflow_rate']}")
        if p["gold_evidence_in_premise"] is not None:
            print(f"    gold证据语句进入premise: "
                  f"{p['gold_evidence_in_premise']}个实例")

    agg = report["aggregation_semantics"]
    print("\n[维度3 聚合语义]")
    print(f"  claims/instance: A_typed(cited) "
          f"{agg['A_typed']['claims_per_instance']} | "
          f"D_noclaim {agg['D_noclaim']['claims_per_instance']}")
    for ds_name in DATASET_ORDER:
        dist = agg["D_noclaim"]["answer_level_claim_verdicts"][ds_name]
        print(f"  {ds_name:12s} answer级claim有效判定分布: {dist['verdicts']}"
              f"  (来源 {dist['answer_level_claim_source']})")
    part = agg["D_noclaim"]["partial_inconsistency"]
    print(f"  部分不一致实例(gold refute & typed≥2 claims): "
          f"{part['n_partial_instances']}个, "
          f"D检出 {part['n_detected_by_d']}个")
    print(f"  其中定位到具体断言: claim通道 "
          f"{part['n_assertion_isolated_by_claim_channel']}/"
          f"{part['n_partial_instances']}, "
          f"专家通道兜底 "
          f"{part['n_assertion_isolated_by_expert_channel']}/"
          f"{part['n_partial_instances']}")

    flips = report.get("flips_a_to_d")
    if flips:
        print("\nverdict flips A→D:")
        for ds_name in DATASET_ORDER:
            f = flips[ds_name]
            print(f"  {ds_name:12s} changed={f['n_changed']:3d} "
                  f"corrected={len(f['corrected_a_wrong_d_right']):3d} "
                  f"regressed={len(f['regressed_a_right_d_wrong']):3d} "
                  f"both_wrong={len(f['moved_both_wrong']):3d}")
    print(f"\nA引用来源: {ref['source']}")


# ── main ────────────────────────────────────────────────────────────────────


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="每个数据集只跑前N条(冒烟测试用)")
    parser.add_argument("--out", type=Path, default=OUT_PATH,
                        help="结果json落盘路径")
    args = parser.parse_args()

    datasets = load_datasets()
    if args.limit:
        datasets = {name: recs[:args.limit]
                    for name, recs in datasets.items()}
    labels = load_labels(datasets)
    print("datasets: " + ", ".join(f"{k}={len(v)}" for k, v in datasets.items()))
    print(f"device: {device_report()}")

    ref = load_a_reference()
    a_variants = (ref["variants"]["A_typed"] if ref and
                  "A_typed" in ref.get("variants", {}) else None)
    b_variants = (ref["variants"]["B_sentence"] if ref and
                  "B_sentence" in ref.get("variants", {}) else None)
    a_preds_by_ds = ({ds: a_variants[ds]["per_instance_verdicts"]
                      for ds in DATASET_ORDER} if a_variants else None)

    # ── variant D: run all datasets under the monkeypatch ──
    d_results, details_by_ds = run_variant_d(datasets, labels)
    d_preds_by_ds = {ds: d_results[ds]["per_instance_verdicts"]
                     for ds in DATASET_ORDER}

    # ── dimension 2: localization (violations-17) ──
    d_loc = localization_summary(datasets["violations17"],
                                 details_by_ds["violations17"])

    # ── granularity mismatch (deterministic recompute; NLI cache is warm) ──
    premise = {ds: premise_granularity_analysis(datasets[ds])
               for ds in DATASET_ORDER}

    # ── dimension 3: aggregation semantics ──
    agg_d = {
        "claims_per_instance": 1.0,
        "answer_level_claim_verdicts": {
            ds: d_claim_verdict_distribution(details_by_ds[ds])
            for ds in DATASET_ORDER},
        "partial_inconsistency": partial_inconsistency_analysis(
            datasets, details_by_ds),
    }
    a_claims_per_inst = (
        {ds: a_variants[ds]["claim_stats"]["claims_per_instance"]
         for ds in DATASET_ORDER} if a_variants else
        {"test46": 4.89, "violations17": 1.0, "crossdoc150": 1.38})
    agg_a = {
        "claims_per_instance": a_claims_per_inst,
        "note": ("A_typed: strict ∀ over per-claim verdicts, refute claim的"
                 "claim_text定位到断言级(平均claim长31.3字符 vs test46 answer"
                 "平均254字符)"),
    }

    flips = flip_analysis_a_to_d(datasets, labels, a_preds_by_ds,
                                 d_preds_by_ds)

    # ── comparison assembly (A/B cited, D measured) ──
    def cited_entry(variant_data: dict[str, Any] | None,
                    ds_name: str) -> dict[str, Any]:
        if variant_data is not None:
            m = variant_data[ds_name]["metrics"]
            return {"n": len(datasets[ds_name]), "metrics": m,
                    "claims_per_instance":
                        variant_data[ds_name]["claim_stats"]
                        ["claims_per_instance"],
                    "cited": True}
        return {"n": len(datasets[ds_name]),
                "metrics": dict(KNOWN_A_FALLBACK[ds_name]),
                "claims_per_instance": None, "cited": True}

    variants_view: dict[str, dict[str, Any]] = {
        "A_typed": {ds: cited_entry(a_variants, ds)
                    for ds in DATASET_ORDER},
        "B_sentence": {ds: cited_entry(b_variants, ds)
                       for ds in DATASET_ORDER},
        "D_noclaim": {ds: {
            "n": len(datasets[ds]),
            "metrics": d_results[ds]["metrics"],
            "claims_per_instance":
                d_results[ds]["claim_stats"]["claims_per_instance"],
            "cited": False,
        } for ds in DATASET_ORDER},
    }
    precision_comparison = {
        ds: {
            "A_typed": variants_view["A_typed"][ds]["metrics"],
            "B_sentence": variants_view["B_sentence"][ds]["metrics"],
            "D_noclaim": d_results[ds]["metrics"],
            "delta_mf1_a_minus_d": round(
                float(variants_view["A_typed"][ds]["metrics"]["macro_f1"])
                - d_results[ds]["metrics"]["macro_f1"], 4),
        } for ds in DATASET_ORDER
    }

    report = {
        "experiment": ("noclaim_final_v1: claim module ablation — variant D "
                       "(whole answer as ONE NLI hypothesis, no claim "
                       "decomposition) vs A_typed, 3 dimensions "
                       "(精度/定位/聚合语义)"),
        "recorded": datetime.now().isoformat(timespec="seconds"),
        "git_sha": git_sha(),
        "config": {
            "module": ("QAConsistencyModule(use_experts=True, "
                       "use_nli_residual=True)"),
            "nli_model_path": NLI_MODEL_PATH,
            "nli_gate": NLI_GATE,
            "aggregation": "strict",
        },
        "variant_d_rule": ("qa_module.decompose_claims → "
                           "[AnswerClaim(kind='semantic', text=answer)]; "
                           "整条answer一条claim, 无typed/句子分解"),
        "isolation_note": ("L0/L1 experts use answer_structure.decompose_answer"
                           "(unpatched); 消融隔离的是per-claim通道+claim级融合"
                           "聚合粒度"),
        "a_reference": {
            "source": (str(DECOMP_ABLATION) if ref else
                       "hardcoded fallback(未找到decomp_ablation_v1.json)"),
            "test46_known": {"accuracy": 0.913, "macro_f1": 0.8047},
            "localization": KNOWN_A_LOCALIZATION,
        },
        "datasets": {name: len(recs) for name, recs in datasets.items()},
        "device": device_report(),
        "nli_cache_mode": nli_cache_mode(),
        "variants": variants_view,
        "variant_d_details": {
            ds: {
                "claim_stats": d_results[ds]["claim_stats"],
                "per_instance_verdicts":
                    d_results[ds]["per_instance_verdicts"],
            } for ds in DATASET_ORDER},
        "localization_violations17": {
            "A_typed": KNOWN_A_LOCALIZATION,
            "D_noclaim": d_loc,
        },
        "premise_granularity": premise,
        "aggregation_semantics": {
            "A_typed": agg_a,
            "D_noclaim": agg_d,
        },
        "precision_comparison": precision_comparison,
        "flips_a_to_d": flips,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    print_report(report)
    print(f"\nnli_cache_mode={report['nli_cache_mode']}")
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
