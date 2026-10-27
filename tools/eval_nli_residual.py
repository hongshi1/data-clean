"""Evaluate the L2 NLI residual channel on the 91-QA frozen corpus (S4).

Runs the frozen scene1 corpus against GLM-5.3 silver labels:
  baseline   = QAConsistencyModule(use_experts=True)                    (no residual)
  nli_gate_g = QAConsistencyModule(use_experts=True, use_nli_residual=True,
                                   nli_gate=g)   for g in 0.50..0.80

Main report uses the default gate (0.6); the sweep table reports every gate
so the threshold choice is auditable. The L3 LLM residual reference number
(macro-F1, refute recall) is read from the latest eval_llm_residual_* run.
Reports accuracy / macro-F1 / per-class / confusion / claim-method
distribution, per-instance flips (corrected vs regressed, with claim-level
detail), and the false-refute list. Pure local inference: zero LLM calls.
Results are saved through the runs protocol (open_run).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.nli_residual import DEFAULT_GATE  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
RUNS_ROOT = BASE / "data/gjb_438c/runs"
LABELS = ("support", "refute", "not_in_evidence")
GATES = (0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


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


def llm_reference() -> dict:
    """最新eval_llm_residual_*运行的L3参照数(无则空报告)."""
    runs = sorted(RUNS_ROOT.glob("eval_llm_residual_*/result.json"))
    if not runs:
        return {}
    result = json.loads(runs[-1].read_text(encoding="utf-8"))
    return {
        "run": runs[-1].parent.name,
        "macro_f1": result["residual"]["macro_f1"],
        "accuracy": result["residual"]["accuracy"],
        "refute_recall": result["residual"]["per_class"]["refute"]["recall"],
        "refute_precision": result["residual"]["per_class"]["refute"]["precision"],
    }


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


def score_config(outcomes: dict[str, dict], rows: list[dict],
                 silver: dict[str, str]) -> dict:
    confusion: Counter = Counter()
    methods: Counter = Counter()
    for row in rows:
        instance_id = row["instance_id"]
        confusion[(outcomes[instance_id]["verdict"], silver[instance_id])] += 1
        methods.update(claim["method"]
                       for claim in outcomes[instance_id]["claims"])
    return {
        "accuracy": accuracy(confusion, len(rows)),
        "macro_f1": macro_f1(confusion),
        "per_class": class_metrics(confusion),
        "confusion[predicted, silver]": confusion_dict(confusion),
        "claim_methods": dict(methods),
    }


def flip_detail(instance_id: str, silver: str, before: str, after: str,
                outcomes: dict[str, dict]) -> dict:
    nli_claims = [claim for claim in outcomes[instance_id]["claims"]
                  if claim["method"].startswith("nli_residual")]
    return {
        "instance_id": instance_id,
        "silver": silver,
        "before": before,
        "after": after,
        "nli_claims": [{
            "claim_text": claim["claim_text"][:80],
            "verdict": claim["verdict"],
            "confidence": claim["confidence"],
            "evidence_refs": claim["evidence_refs"],
            "rationale": claim["rationale"][:160],
        } for claim in nli_claims],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", default="egt_finetuned_v2",
                        help="MODELS注册表的checkpoint key")
    args = parser.parse_args()
    rows = read_jsonl(QA_FROZEN)
    silver = {row["instance_id"]: row["final_verdict"]
              for row in read_jsonl(SILVER)}
    checkpoint = MODELS[args.model_key]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        print(f"checkpoint不存在: {checkpoint} "
              f"(先跑 python tools/train_residual_nli.py)")
        sys.exit(1)

    baseline_out = run_corpus(QAConsistencyModule(use_experts=True), rows)
    baseline = score_config(baseline_out, rows, silver)

    sweep: dict[str, dict] = {}
    outcomes_by_gate: dict[str, dict[str, dict]] = {}
    for gate in GATES:
        outcomes = run_corpus(
            QAConsistencyModule(use_experts=True, use_nli_residual=True,
                                nli_model_path=checkpoint, nli_gate=gate),
            rows)
        outcomes_by_gate[f"{gate:.2f}"] = outcomes
        sweep[f"{gate:.2f}"] = score_config(outcomes, rows, silver)
        print(f"gate={gate:.2f}: macro_f1={sweep[f'{gate:.2f}']['macro_f1']} "
              f"refuteP={sweep[f'{gate:.2f}']['per_class']['refute']['precision']}")

    main_gate = f"{DEFAULT_GATE:.2f}"
    main_out = outcomes_by_gate[main_gate]
    main_cfg = sweep[main_gate]

    corrected, regressed, moved = [], [], []
    for row in rows:
        instance_id = row["instance_id"]
        before = baseline_out[instance_id]["verdict"]
        after = main_out[instance_id]["verdict"]
        if before == after:
            continue
        gold = silver[instance_id]
        detail = flip_detail(instance_id, gold, before, after, main_out)
        if after == gold:
            corrected.append(detail)
        elif before == gold:
            regressed.append(detail)
        else:
            moved.append(detail)

    false_refutes = [row["instance_id"] for row in rows
                     if main_out[row["instance_id"]]["verdict"] == "refute"
                     and silver[row["instance_id"]] != "refute"]
    nli_claims_total = sum(
        1 for row in rows for claim in main_out[row["instance_id"]]["claims"]
        if claim["method"] == "nli_residual")
    unavailable = any(
        claim["method"] == "nli_residual_unavailable"
        for row in rows for claim in main_out[row["instance_id"]]["claims"])

    reference = llm_reference()
    report = {
        "n": len(rows),
        "label_type": "glm53_silver_not_gold",
        "checkpoint": checkpoint,
        "default_gate": DEFAULT_GATE,
        "baseline": baseline,
        "nli_residual": main_cfg,
        "gate_sweep": sweep,
        "nli_stats": {
            "nli_residual_claims": nli_claims_total,
            "model_unavailable": unavailable,
        },
        "llm_reference_l3": reference,
        "gap_to_l3": (round(main_cfg["macro_f1"] - reference["macro_f1"], 4)
                      if reference else None),
        "flips": {
            "corrected": corrected,
            "regressed": regressed,
            "moved": moved,
        },
        "false_refutes": false_refutes,
        "targets": {
            "macro_f1_ge_0.65": main_cfg["macro_f1"] >= 0.65,
            "refute_precision_ge_0.8":
                main_cfg["per_class"]["refute"]["precision"] >= 0.8,
        },
    }

    run = open_run("eval_nli_residual", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(SILVER.relative_to(BASE)),
        "n": len(rows),
        "use_experts": True,
        "use_nli_residual": True,
        "model_key": args.model_key,
        "checkpoint": checkpoint,
        "gates": list(GATES),
        "default_gate": DEFAULT_GATE,
        "llm_calls": 0,
    })
    run.save_result(report)

    print(json.dumps({
        "n": report["n"],
        "checkpoint": checkpoint,
        "baseline": {"accuracy": baseline["accuracy"],
                     "macro_f1": baseline["macro_f1"],
                     "per_class": baseline["per_class"]},
        "nli_residual": {
            "gate": DEFAULT_GATE,
            "accuracy": main_cfg["accuracy"],
            "macro_f1": main_cfg["macro_f1"],
            "per_class": main_cfg["per_class"],
            "confusion": main_cfg["confusion[predicted, silver]"],
        },
        "llm_reference_l3": reference,
        "gap_to_l3": report["gap_to_l3"],
        "gate_sweep": {g: {"macro_f1": m["macro_f1"],
                           "refute_p": m["per_class"]["refute"]["precision"],
                           "refute_r": m["per_class"]["refute"]["recall"]}
                       for g, m in sweep.items()},
        "claim_methods": main_cfg["claim_methods"],
        "nli_stats": report["nli_stats"],
        "corrected": [f"{d['instance_id']}({d['before']}->{d['after']})"
                      for d in corrected],
        "regressed": [f"{d['instance_id']}({d['before']}->{d['after']})"
                      for d in regressed],
        "false_refutes": false_refutes,
        "targets": report["targets"],
        "run": str(run.path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
