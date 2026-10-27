"""Evaluate the L3 LLM residual channel on the 91-QA frozen corpus.

Runs the frozen scene1 corpus twice against GLM-5.3 silver labels:
  baseline = QAConsistencyModule(use_experts=True)                     (no LLM)
  residual = QAConsistencyModule(use_experts=True, use_llm_residual=True)

Reports accuracy / macro-F1 / confusion / claim-method distribution, the
per-instance flips (corrected vs regressed, with claim-level detail), and
LLM call statistics: invocations are counted by wrapping llm_json, real API
calls are measured as llm_cache.jsonl line growth, the rest are disk-cache
hits. Results are saved through the runs protocol (open_run).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.common.llm_client as llm_client  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
LLM_CACHE = BASE / "data/gjb_438c/llm_cache/llm_cache.jsonl"
LABELS = ("support", "refute", "not_in_evidence")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def cache_lines() -> int:
    if not LLM_CACHE.exists():
        return 0
    return sum(1 for line in LLM_CACHE.open(encoding="utf-8") if line.strip())


def class_metrics(confusion: Counter) -> dict[str, dict]:
    out = {}
    for label in LABELS:
        tp = confusion[(label, label)]
        fp = sum(confusion[(label, gold)] for gold in LABELS if gold != label)
        fn = sum(confusion[(pred, label)] for pred in LABELS if pred != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (2 * precision * recall / (precision + recall)
              if precision + recall else 0.0)
        out[label] = {"precision": round(precision, 4),
                      "recall": round(recall, 4), "f1": round(f1, 4)}
    return out


def macro_f1(confusion: Counter) -> float:
    return round(sum(m["f1"] for m in class_metrics(confusion).values())
                 / len(LABELS), 4)


def accuracy(confusion: Counter, n: int) -> float:
    correct = sum(confusion[(p, g)] for p in LABELS for g in LABELS if p == g)
    return round(correct / n, 4)


def confusion_dict(confusion: Counter) -> dict[str, int]:
    return {f"{p}|{g}": confusion[(p, g)]
            for p in LABELS for g in LABELS if confusion[(p, g)]}


def run_corpus(module: QAConsistencyModule, rows: list[dict]) -> dict[str, dict]:
    outcomes: dict[str, dict] = {}
    for row in rows:
        request = request_from_dict(row)
        result = module.verify(request)
        outcomes[request.instance_id] = {
            "verdict": result.verdict,
            "status": result.status,
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


def flip_detail(instance_id: str, silver: str, before: str, after: str,
                outcomes: dict[str, dict]) -> dict:
    llm_claims = [claim for claim in outcomes[instance_id]["claims"]
                  if claim["method"].startswith("llm_residual")]
    return {
        "instance_id": instance_id,
        "silver": silver,
        "before": before,
        "after": after,
        "llm_claims": [{
            "claim_text": claim["claim_text"][:80],
            "verdict": claim["verdict"],
            "confidence": claim["confidence"],
            "evidence_refs": claim["evidence_refs"],
            "rationale": claim["rationale"][:160],
        } for claim in llm_claims],
    }


def main() -> None:
    rows = read_jsonl(QA_FROZEN)
    silver = {row["instance_id"]: row["final_verdict"]
              for row in read_jsonl(SILVER)}

    baseline = run_corpus(QAConsistencyModule(use_experts=True), rows)

    call_stats = {"invocations": 0}
    original_llm_json = llm_client.llm_json

    def counting_llm_json(prompt, *args, **kwargs):
        call_stats["invocations"] += 1
        return original_llm_json(prompt, *args, **kwargs)

    lines_before = cache_lines()
    llm_client.llm_json = counting_llm_json
    try:
        residual = run_corpus(
            QAConsistencyModule(use_experts=True, use_llm_residual=True), rows)
    finally:
        llm_client.llm_json = original_llm_json
    lines_after = cache_lines()

    confusion_before: Counter = Counter()
    confusion_after: Counter = Counter()
    methods_before: Counter = Counter()
    methods_after: Counter = Counter()
    for row in rows:
        instance_id = row["instance_id"]
        gold = silver[instance_id]
        confusion_before[(baseline[instance_id]["verdict"], gold)] += 1
        confusion_after[(residual[instance_id]["verdict"], gold)] += 1
        methods_before.update(claim["method"]
                              for claim in baseline[instance_id]["claims"])
        methods_after.update(claim["method"]
                             for claim in residual[instance_id]["claims"])

    api_calls = lines_after - lines_before
    invocations = call_stats["invocations"]
    failed_claims = sum(
        1 for row in rows for claim in residual[row["instance_id"]]["claims"]
        if claim["method"] == "llm_residual_failed")

    corrected, regressed, moved = [], [], []
    for row in rows:
        instance_id = row["instance_id"]
        before = baseline[instance_id]["verdict"]
        after = residual[instance_id]["verdict"]
        if before == after:
            continue
        gold = silver[instance_id]
        detail = flip_detail(instance_id, gold, before, after, residual)
        if after == gold:
            corrected.append(detail)
        elif before == gold:
            regressed.append(detail)
        else:
            moved.append(detail)

    false_refutes = [row["instance_id"] for row in rows
                     if residual[row["instance_id"]]["verdict"] == "refute"
                     and silver[row["instance_id"]] != "refute"]
    false_supports = [row["instance_id"] for row in rows
                      if residual[row["instance_id"]]["verdict"] == "support"
                      and silver[row["instance_id"]] != "support"]
    support_recall = confusion_after[("support", "support")] / max(
        1, sum(confusion_after[(p, "support")] for p in LABELS))

    report = {
        "n": len(rows),
        "label_type": "glm53_silver_not_gold",
        "baseline": {
            "accuracy": accuracy(confusion_before, len(rows)),
            "macro_f1": macro_f1(confusion_before),
            "per_class": class_metrics(confusion_before),
            "confusion[predicted, silver]": confusion_dict(confusion_before),
            "claim_methods": dict(methods_before),
        },
        "residual": {
            "accuracy": accuracy(confusion_after, len(rows)),
            "macro_f1": macro_f1(confusion_after),
            "per_class": class_metrics(confusion_after),
            "confusion[predicted, silver]": confusion_dict(confusion_after),
            "claim_methods": dict(methods_after),
            "support_recall": round(support_recall, 4),
        },
        "llm_stats": {
            "invocations": invocations,
            "api_calls": api_calls,
            "cache_hits": invocations - api_calls,
            "llm_residual_failed_claims": failed_claims,
        },
        "flips": {
            "corrected": corrected,
            "regressed": regressed,
            "moved": moved,
        },
        "false_refutes": false_refutes,
        "false_supports": false_supports,
    }

    run = open_run("eval_llm_residual", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(SILVER.relative_to(BASE)),
        "n": len(rows),
        "use_experts": True,
        "use_llm_residual": True,
        "refute_confidence_gate": 0.8,
        "llm": "glm-json-cache",
    })
    run.save_result(report)

    print(json.dumps({
        "n": report["n"],
        "baseline": {"accuracy": report["baseline"]["accuracy"],
                     "macro_f1": report["baseline"]["macro_f1"]},
        "residual": {"accuracy": report["residual"]["accuracy"],
                     "macro_f1": report["residual"]["macro_f1"],
                     "per_class": report["residual"]["per_class"],
                     "support_recall": report["residual"]["support_recall"]},
        "confusion_before": confusion_dict(confusion_before),
        "confusion_after": confusion_dict(confusion_after),
        "claim_methods": dict(methods_after),
        "llm_stats": report["llm_stats"],
        "corrected": [f"{d['instance_id']}({d['before']}->{d['after']})"
                      for d in corrected],
        "regressed": [f"{d['instance_id']}({d['before']}->{d['after']})"
                      for d in regressed],
        "moved": [f"{d['instance_id']}({d['before']}->{d['after']})"
                  for d in moved],
        "false_refutes": false_refutes,
        "false_supports": false_supports,
    }, ensure_ascii=False, indent=2))
    print(f"run: {run.path}")


if __name__ == "__main__":
    main()
