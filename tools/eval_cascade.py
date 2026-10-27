"""Evaluate the S5 L2→L3 cascade escalation routing on the 91-QA corpus (C4).

Cascade (paper contribution C4: the FrugalGPT/RouteLLM cost-quality routing
pattern generalized to heterogeneous verifiers): the cheap local L2 NLI
judges every residual claim; only its refute candidates — the one
silver-measured failure mode (refute R=0.875 but P=0.368) — are re-checked
by the L3 LLM channel (refute P=1.0), whose verdict fully replaces the L2
one on that claim. NLI support/NIE verdicts pass through untouched, so the
LLM only pays for the pseudo-refutes.

Five configurations against GLM-5.3 silver labels:
  baseline          = use_experts=True                          (0 LLM)
  l2_nli            = use_nli_residual=True, nli_gate=0.70      (0 LLM)
  l3_llm            = use_llm_residual=True                     (85 LLM)
  cascade           = use_cascade=True, nli_gate=0.70           (target)
  cascade_conformal = cascade + cascade_keep_confidence=0.95     (bonus)

Cascade targets: macro-F1>=0.75 AND refute precision>=0.9 AND LLM
invocations<=30. Reports per-config accuracy / macro-F1 / confusion /
per-class / claim-method distribution, the cost-quality table
(macro-F1, refute P/R, LLM calls) for the paper, the L2→cascade flip lists
(corrected vs regressed pseudo-refutes), the per-instance escalation stats,
and the conformal two-tier refute precision. LLM invocations are counted by
wrapping llm_json; real API calls are measured as llm_cache.jsonl line
growth (cache=True keeps every call reproducible). Results are saved
through the runs protocol (open_run).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.common.llm_client as llm_client  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    load_frozen_qa,
    load_silver_labels,
    run_module_corpus,
    score_outcomes,
)
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
RUNS_ROOT = BASE / "data/gjb_438c/runs"
NLI_GATE = 0.70          # L2参照数(macro-F1 0.5437, refute P=0.368)取自gate=0.70
KEEP_CONFIDENCE = 0.95   # conformal高置信档: >=0.95直接refute, 不升级


REFERENCE_RUN = "eval_llm_residual_5dd69927_20261026_173434"  # 任务给定的L3参照(0.7799)


def llm_reference() -> dict:
    """任务给定的10-26 L3参照数(当前管线下已过期)."""
    path = RUNS_ROOT / REFERENCE_RUN / "result.json"
    if not path.exists():
        runs = sorted(RUNS_ROOT.glob("eval_llm_residual_*/result.json"))
        if not runs:
            return {}
        path = runs[-1]
    result = json.loads(path.read_text(encoding="utf-8"))
    return {
        "run": path.parent.name,
        "macro_f1": result["residual"]["macro_f1"],
        "accuracy": result["residual"]["accuracy"],
        "refute_recall": result["residual"]["per_class"]["refute"]["recall"],
        "refute_precision": result["residual"]["per_class"]["refute"]["precision"],
    }


def run_with_llm_counting(module: QAConsistencyModule, rows: list[dict]
                          ) -> tuple[dict[str, dict], dict]:
    """Count llm_json invocations and REAL per-process API calls.

    ``api_calls`` counts ``llm_client._store`` writes inside this process
    (a store happens exactly once per cache-missing API call), so the
    metric is immune to concurrent processes appending to the shared
    llm_cache.jsonl; on a warm cache api_calls=0 while invocations stays
    the stable per-instance call count (the cost metric comparable with
    the 10-26 reference's 85).
    """
    call_stats = {"invocations": 0, "stores": 0}
    original_llm_json = llm_client.llm_json
    original_store = llm_client._store

    def counting_llm_json(prompt, *args, **kwargs):
        call_stats["invocations"] += 1
        return original_llm_json(prompt, *args, **kwargs)

    def counting_store(ck, content, model):
        call_stats["stores"] += 1
        return original_store(ck, content, model)

    llm_client.llm_json = counting_llm_json
    llm_client._store = counting_store
    try:
        outcomes = run_module_corpus(module, rows)
    finally:
        llm_client.llm_json = original_llm_json
        llm_client._store = original_store
    invocations = call_stats["invocations"]
    api_calls = call_stats["stores"]
    stats = {"invocations": invocations, "api_calls": api_calls,
             "cache_hits": invocations - api_calls}
    return outcomes, stats


def diag_count(diagnostics: list[str], prefix: str) -> int:
    for entry in diagnostics:
        if entry.startswith(prefix):
            return int(entry.rsplit("_", 1)[1])
    return 0


def escalation_stats(outcomes: dict[str, dict],
                     rows: list[dict]) -> dict:
    """Per-instance cascade bookkeeping parsed from the diagnostics."""
    escalated_claims = kept_claims = nli_claims = 0
    escalated_instances: list[str] = []
    kept_only_instances: list[str] = []
    llm_failed = 0
    for row in rows:
        instance_id = row["instance_id"]
        diag = outcomes[instance_id]["diagnostics"]
        n_escalated = diag_count(diag, "cascade_llm_calls_")
        n_kept = diag_count(diag, "cascade_high_confidence_kept_")
        escalated_claims += n_escalated
        kept_claims += n_kept
        nli_claims += diag_count(diag, "cascade_nli_claims_")
        if any(entry == "llm_residual_call_failed" for entry in diag):
            llm_failed += 1
        if n_escalated:
            escalated_instances.append(instance_id)
        elif n_kept:
            kept_only_instances.append(instance_id)
    return {
        "nli_claims_judged": nli_claims,
        "escalated_claims": escalated_claims,
        "kept_high_confidence_claims": kept_claims,
        "escalated_instances": escalated_instances,
        "kept_only_instances": kept_only_instances,
        "instances_with_llm_failure": llm_failed,
    }


def tier_precision(outcomes: dict[str, dict], silver: dict[str, str],
                   instances: list[str]) -> dict:
    """Instance-level refute precision on a cascade tier subset."""
    predicted_refute = [iid for iid in instances
                        if outcomes[iid]["verdict"] == "refute"]
    correct = [iid for iid in predicted_refute if silver[iid] == "refute"]
    return {
        "n_instances": len(instances),
        "n_predicted_refute": len(predicted_refute),
        "n_correct": len(correct),
        "precision": (round(len(correct) / len(predicted_refute), 4)
                      if predicted_refute else None),
    }


def cascade_claim_detail(outcomes: dict[str, dict], instance_id: str) -> list:
    claims = outcomes[instance_id]["claims"]
    return [{
        "claim_text": claim["claim_text"][:80],
        "verdict": claim["verdict"],
        "method": claim["method"],
        "confidence": claim["confidence"],
        "rationale": claim["rationale"][:160],
    } for claim in claims
        if claim["method"].startswith("llm_residual")
        or (claim["method"] == "nli_residual"
            and claim["verdict"] == "refute")]


def flips_between(before_out: dict[str, dict], after_out: dict[str, dict],
                  rows: list[dict], silver: dict[str, str]) -> dict:
    corrected, regressed, moved = [], [], []
    for row in rows:
        instance_id = row["instance_id"]
        before = before_out[instance_id]["verdict"]
        after = after_out[instance_id]["verdict"]
        if before == after:
            continue
        gold = silver[instance_id]
        detail = {
            "instance_id": instance_id,
            "silver": gold,
            "before": before,
            "after": after,
            "cascade_claims": cascade_claim_detail(after_out, instance_id),
        }
        if after == gold:
            corrected.append(detail)
        elif before == gold:
            regressed.append(detail)
        else:
            moved.append(detail)
    return {"corrected": corrected, "regressed": regressed, "moved": moved}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", default="egt_finetuned_v2",
                        help="MODELS注册表的checkpoint key")
    parser.add_argument("--nli-gate", type=float, default=NLI_GATE,
                        help="L2 NLI门控(默认0.70, 与S4参照数一致)")
    parser.add_argument("--keep-confidence", type=float,
                        default=KEEP_CONFIDENCE,
                        help="conformal高置信档阈值(默认0.95)")
    args = parser.parse_args()

    rows = load_frozen_qa(QA_FROZEN)
    silver = load_silver_labels(SILVER)
    checkpoint = MODELS[args.model_key]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        print(f"checkpoint不存在: {checkpoint} "
              f"(先跑 python tools/train_residual_nli.py)")
        sys.exit(1)

    configs: dict[str, QAConsistencyModule] = {
        "baseline": QAConsistencyModule(use_experts=True),
        "l2_nli": QAConsistencyModule(
            use_experts=True, use_nli_residual=True,
            nli_model_path=checkpoint, nli_gate=args.nli_gate),
        "l3_llm": QAConsistencyModule(
            use_experts=True, use_llm_residual=True),
        "cascade": QAConsistencyModule(
            use_experts=True, use_cascade=True,
            nli_model_path=checkpoint, nli_gate=args.nli_gate),
        "cascade_conformal": QAConsistencyModule(
            use_experts=True, use_cascade=True,
            cascade_keep_confidence=args.keep_confidence,
            nli_model_path=checkpoint, nli_gate=args.nli_gate),
    }

    outcomes: dict[str, dict[str, dict]] = {}
    llm_stats: dict[str, dict] = {}
    for name, module in configs.items():
        out, stats = run_with_llm_counting(module, rows)
        outcomes[name] = out
        llm_stats[name] = stats
        print(f"{name}: macro_f1="
              f"{score_outcomes(out, rows, silver)['macro_f1']} "
              f"llm_invocations={stats['invocations']} "
              f"api_calls={stats['api_calls']}")

    scores = {name: score_outcomes(out, rows, silver)
              for name, out in outcomes.items()}

    cost_quality_table = [{
        "config": name,
        "macro_f1": scores[name]["macro_f1"],
        "refute_precision": scores[name]["per_class"]["refute"]["precision"],
        "refute_recall": scores[name]["per_class"]["refute"]["recall"],
        "llm_invocations": llm_stats[name]["invocations"],
        "llm_api_calls": llm_stats[name]["api_calls"],
    } for name in configs]

    cascade_esc = escalation_stats(outcomes["cascade"], rows)
    conformal_esc = escalation_stats(outcomes["cascade_conformal"], rows)
    l2_to_cascade = flips_between(outcomes["l2_nli"], outcomes["cascade"],
                                  rows, silver)
    conformal_two_tier = {
        "kept_tier_ge_keep_confidence": tier_precision(
            outcomes["cascade_conformal"], silver,
            conformal_esc["kept_only_instances"]),
        "escalated_tier": tier_precision(
            outcomes["cascade_conformal"], silver,
            conformal_esc["escalated_instances"]),
    }
    cascade_cfg = scores["cascade"]
    targets = {
        "macro_f1_ge_0.75": cascade_cfg["macro_f1"] >= 0.75,
        "refute_precision_ge_0.9":
            cascade_cfg["per_class"]["refute"]["precision"] >= 0.9,
        "llm_invocations_le_30": llm_stats["cascade"]["invocations"] <= 30,
    }
    reference = llm_reference()
    reference_drift = {
        "l3_reference_1026": reference,
        "l3_current": {
            "macro_f1": scores["l3_llm"]["macro_f1"],
            "refute_precision":
                scores["l3_llm"]["per_class"]["refute"]["precision"],
            "refute_recall":
                scores["l3_llm"]["per_class"]["refute"]["recall"],
        },
        "note": ("10-26的L3参照(0.7799/refute P=1.0)基于当时的语句线性化; "
                 "evidence_statements.py在10-26 20:52(最后一次L3评测17:34之后)"
                 "被修改, 当前管线下L3提示词未命中旧缓存(今日重新采样); 另有"
                 "并行会话在同一llm_cache上评测eval_llm_residual(相同提示词), "
                 "共享缓存后写覆盖前写, 今日L3数(本表l3_llm)为当前缓存状态的"
                 "确定值(两次独立运行复现一致); 四配置对比以本次同管线同日"
                 "测量为准"),
    } if reference else {}

    report = {
        "n": len(rows),
        "label_type": "glm53_silver_not_gold",
        "checkpoint": checkpoint,
        "nli_gate": args.nli_gate,
        "keep_confidence": args.keep_confidence,
        "configs": scores,
        "llm_stats": llm_stats,
        "cost_quality_table": cost_quality_table,
        "cascade_escalation": cascade_esc,
        "cascade_conformal_escalation": conformal_esc,
        "l2_to_cascade_flips": l2_to_cascade,
        "conformal_two_tier": conformal_two_tier,
        "llm_reference_drift": reference_drift,
        "targets": targets,
    }

    run = open_run("eval_cascade", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(SILVER.relative_to(BASE)),
        "n": len(rows),
        "use_experts": True,
        "configs": list(configs),
        "model_key": args.model_key,
        "checkpoint": checkpoint,
        "nli_gate": args.nli_gate,
        "keep_confidence": args.keep_confidence,
        "llm": "glm-json-cache",
    })
    run.save_result(report)

    print(json.dumps({
        "n": report["n"],
        "nli_gate": args.nli_gate,
        "cost_quality_table": cost_quality_table,
        "cascade_escalation": {k: v for k, v in cascade_esc.items()
                               if not isinstance(v, list)},
        "cascade_conformal_escalation": {
            k: v for k, v in conformal_esc.items()
            if not isinstance(v, list)},
        "confusion_cascade": scores["cascade"]["confusion[predicted, silver]"],
        "claim_methods_cascade": scores["cascade"]["claim_methods"],
        "l2_to_cascade_corrected": [
            f"{d['instance_id']}({d['before']}->{d['after']})"
            for d in l2_to_cascade["corrected"]],
        "l2_to_cascade_regressed": [
            f"{d['instance_id']}({d['before']}->{d['after']})"
            for d in l2_to_cascade["regressed"]],
        "conformal_two_tier": conformal_two_tier,
        "llm_reference_drift": reference_drift,
        "targets": targets,
        "run": str(run.path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
