#!/usr/bin/env python3
"""P3: Evidence-level evaluation — joint verdict×localization scoring.

Implements the evidence-level metrics from 52_research_design:
  - J = F1_verdict × F1_loc
  - F1_loc | verdict_correct (conditional localization)
  - AVeriTeC score (verdict correct ∧ overlap ≥ 0.5)
  - Hallucination rate (verdict without evidence)

Evaluates on frozen QA data (91 pairs) with evidence_refs from qa_module output.
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

FROZEN_QA = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
RUNS_ROOT = BASE / "data/gjb_438c/runs"


def load_frozen_qa():
    with FROZEN_QA.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def compute_overlap(pred_refs, gold_refs):
    """Compute overlap between predicted and gold evidence references."""
    if not pred_refs or not gold_refs:
        return 0.0
    pred_set = set(str(r) for r in pred_refs)
    gold_set = set(str(r) for r in gold_refs)
    if not pred_set or not gold_set:
        return 0.0
    return len(pred_set & gold_set) / len(pred_set | gold_set)


def evaluate_evidence_level(predictions, golds):
    """Compute evidence-level metrics.

    Args:
        predictions: list of {verdict, evidence_refs} dicts
        golds: list of {verdict, evidence_refs} dicts
    """
    n = len(predictions)
    if n == 0:
        return {}

    # Verdict-level metrics
    verdict_tp = sum(1 for p, g in zip(predictions, golds) if p["verdict"] == g["verdict"])
    verdict_accuracy = verdict_tp / n

    # Evidence-level metrics
    overlaps = []
    correct_verdict_overlaps = []
    hallucinated = 0
    no_evidence = 0

    for p, g in zip(predictions, golds):
        pred_refs = p.get("evidence_refs", [])
        gold_refs = g.get("evidence_refs", [])

        overlap = compute_overlap(pred_refs, gold_refs)
        overlaps.append(overlap)

        if p["verdict"] == g["verdict"]:
            correct_verdict_overlaps.append(overlap)

        # Hallucination: has verdict but no evidence
        if p["verdict"] != "not_in_evidence" and not pred_refs:
            hallucinated += 1

        # No evidence: explicitly abstained
        if p["verdict"] == "not_in_evidence":
            no_evidence += 1

    # Localization metrics
    avg_overlap = np.mean(overlaps) if overlaps else 0
    avg_overlap_correct = (np.mean(correct_verdict_overlaps)
                           if correct_verdict_overlaps else 0)

    # F1_loc: treat overlap ≥ threshold as "correctly localized"
    loc_threshold = 0.5
    loc_correct = sum(1 for o in overlaps if o >= loc_threshold)
    loc_precision = loc_correct / max(sum(1 for p in predictions
                                          if p.get("evidence_refs")), 1)
    loc_recall = loc_correct / max(sum(1 for g in golds
                                       if g.get("evidence_refs")), 1)
    f1_loc = (2 * loc_precision * loc_recall / max(loc_precision + loc_recall, 1e-12)
              if loc_precision + loc_recall > 0 else 0)

    # AVeriTeC-style score
    averitec_score = sum(1 for p, g in zip(predictions, golds)
                        if p["verdict"] == g["verdict"]
                        and compute_overlap(p.get("evidence_refs", []),
                                          g.get("evidence_refs", [])) >= 0.5) / n

    # Joint score
    # F1_verdict approximated by accuracy (binary task)
    f1_verdict = verdict_accuracy
    joint_score = f1_verdict * f1_loc

    # Conditional localization: F1_loc | verdict_correct
    cond_loc = avg_overlap_correct

    return {
        "n": n,
        "verdict_accuracy": round(verdict_accuracy, 4),
        "f1_verdict": round(f1_verdict, 4),
        "f1_loc": round(f1_loc, 4),
        "joint_score_J": round(joint_score, 4),
        "avg_overlap": round(avg_overlap, 4),
        "avg_overlap_given_correct": round(cond_loc, 4),
        "averitec_score": round(averitec_score, 4),
        "hallucination_rate": round(hallucinated / n, 4),
        "abstention_rate": round(no_evidence / n, 4),
        "loc_precision": round(loc_precision, 4),
        "loc_recall": round(loc_recall, 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", type=Path, default=RUNS_ROOT)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    qa_data = load_frozen_qa()
    print(f"Frozen QA pairs: {len(qa_data)}")

    # Build gold from frozen QA (evidence_refs from the frozen context)
    golds = []
    for qa in qa_data:
        evidence = qa.get("evidence", [])
        evidence_ids = [e.get("evidence_id", "") for e in evidence if e.get("evidence_id")]
        # Gold verdict: we don't have human gold, so use "supported" as default
        # (the QA answers were generated from these evidence blocks)
        golds.append({
            "verdict": "supported",  # default gold (evidence supports answer)
            "evidence_refs": evidence_ids,
        })

    # Simulated predictions: use the evidence from QA (oracle-like)
    # In real usage, this would be the QA module's output
    predictions_oracle = []
    for qa in qa_data:
        evidence = qa.get("evidence", [])
        evidence_ids = [e.get("evidence_id", "") for e in evidence if e.get("evidence_id")]
        predictions_oracle.append({
            "verdict": "supported",
            "evidence_refs": evidence_ids,
        })

    # Oracle evaluation (should be near-perfect)
    print("\n--- Oracle (uses same evidence as gold) ---")
    oracle_results = evaluate_evidence_level(predictions_oracle, golds)
    for k, v in oracle_results.items():
        print(f"  {k}: {v}")

    # Simulated predictions with degraded evidence (partial evidence)
    predictions_partial = []
    for qa in qa_data:
        evidence = qa.get("evidence", [])
        # Take only first half of evidence
        half = evidence[:max(1, len(evidence) // 2)]
        evidence_ids = [e.get("evidence_id", "") for e in half if e.get("evidence_id")]
        predictions_partial.append({
            "verdict": "supported",
            "evidence_refs": evidence_ids,
        })

    print("\n--- Partial Evidence (50% of gold evidence) ---")
    partial_results = evaluate_evidence_level(predictions_partial, golds)
    for k, v in partial_results.items():
        print(f"  {k}: {v}")

    # Simulated predictions with no evidence (hallucination test)
    predictions_no_ev = []
    for qa in qa_data:
        predictions_no_ev.append({
            "verdict": "supported",
            "evidence_refs": [],
        })

    print("\n--- No Evidence (hallucination test) ---")
    no_ev_results = evaluate_evidence_level(predictions_no_ev, golds)
    for k, v in no_ev_results.items():
        print(f"  {k}: {v}")

    # Simulated with wrong evidence (mismatched)
    predictions_wrong = []
    for i, qa in enumerate(qa_data):
        # Use evidence from a different QA pair
        wrong_idx = (i + 1) % len(qa_data)
        wrong_evidence = qa_data[wrong_idx].get("evidence", [])
        evidence_ids = [e.get("evidence_id", "") for e in wrong_evidence
                        if e.get("evidence_id")]
        predictions_wrong.append({
            "verdict": "supported",
            "evidence_refs": evidence_ids,
        })

    print("\n--- Wrong Evidence (mismatched) ---")
    wrong_results = evaluate_evidence_level(predictions_wrong, golds)
    for k, v in wrong_results.items():
        print(f"  {k}: {v}")

    # Summary table
    print(f"\n{'='*70}")
    print("EVIDENCE-LEVEL EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"{'Condition':<25} {'Verdict Acc':<13} {'F1_loc':<10} {'Joint J':<10} {'AVeriTeC':<10} {'Overlap':<10}")
    print(f"{'-'*25} {'-'*13} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
    for name, r in [("Oracle", oracle_results), ("Partial 50%", partial_results),
                    ("No Evidence", no_ev_results), ("Wrong Evidence", wrong_results)]:
        print(f"{name:<25} {r.get('verdict_accuracy', 'N/A'):<13} "
              f"{r.get('f1_loc', 'N/A'):<10} {r.get('joint_score_J', 'N/A'):<10} "
              f"{r.get('averitec_score', 'N/A'):<10} {r.get('avg_overlap', 'N/A'):<10}")
    print(f"{'='*70}")

    # Save
    results = {
        "oracle": oracle_results,
        "partial_50pct": partial_results,
        "no_evidence": no_ev_results,
        "wrong_evidence": wrong_results,
        "config": {
            "n_qa": len(qa_data),
            "loc_threshold": 0.5,
            "metrics": ["verdict_accuracy", "f1_loc", "joint_score_J",
                        "averitec_score", "avg_overlap", "hallucination_rate"],
        },
    }

    run = open_run("evidence_level_eval", results["config"], args.runs_root)
    run.save_result(results)
    print(f"\nSaved to: {run.path}")


if __name__ == "__main__":
    main()
