"""Evaluate the learned cascade router on the 91-QA corpus (C4, learning half).

Three-config comparison against GLM-5.3 silver labels, mirroring
tools/eval_cascade.py's fixed-cascade protocol:

  fixed_cascade  = use_cascade=True (the status quo: L2 on every residual,
                   refute candidates escalate to L3)         e.g. 0.7185 / 15 LLM
  learned_router = use_learned_router=<router.joblib> (per-instance route
                   decision after L1: accept_l1 / accept_l2 / call_l2 /
                   escalate_l3)
  pareto sweep   = the learned router's cost_alpha knob
                   (argmax P(route) / (1 + cost)^alpha) swept over
                   [0 .. 8]: LLM invocations vs macro-F1 / refute-F1, the
                   RefuteRecall@Budget material for the paper.

Reference configs (baseline / l2_nli / l3_llm) are re-measured on the same
pipeline so the cost-quality table is internally consistent. The table also
carries an "oracle_router (analysis ceiling)" row: the probe's minimum-cost
correct routes replayed over the 91 QA — the routing formulation's upper
bound, separating "the routing formulation has headroom" from "the learner
failed to capture it". LLM invocations are counted by wrapping llm_json
(cached interface: warm cache -> api_calls 0, invocations stay the stable
per-instance call count). Results are saved through the runs protocol
(open_run).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    QA_FROZEN,
    SILVER,
    accuracy,
    confusion_dict,
    load_frozen_qa,
    load_silver_labels,
    macro_f1,
    per_class_metrics,
    read_jsonl,
    score_outcomes,
)
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.router import LearnedRouter  # noqa: E402
from tools.eval_cascade import run_with_llm_counting  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

RUNS_ROOT = BASE / "data/gjb_438c/runs"
NLI_GATE = 0.70
ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 8.0)


def find_latest_router() -> Path:
    """Latest router_train_* run by the timestamp in the dir name.

    Lexical sort would order by the config hash first and can pick an older
    run (e.g. a 5-row smoke probe) over the real training run.
    """
    candidates = []
    for path in RUNS_ROOT.glob("router_train_*/router.joblib"):
        match = re.search(r"(\d{8}_\d{6})(?:_\d+)?$", path.parent.name)
        if match:
            candidates.append((match.group(1), path))
    if not candidates:
        raise SystemExit(
            "找不到router.joblib (先跑 python tools/build_router_dataset.py)")
    return max(candidates, key=lambda item: item[0])[1]


def oracle_router_simulation(dataset: list[dict]) -> dict:
    """Routing-formulation ceiling: the oracle router replayed over the probe.

    Uses the probe's per-route verdicts and LLM call counts (the same
    production code paths the eval runs); no-residual instances keep their
    v_l1 verdict at 0 calls. This is an analysis row for the paper — the
    gap between this ceiling and the learned router isolates how much of
    the miss is the learner (training-distribution shift) vs the routing
    formulation itself.
    """
    route_to_key = {"accept_l1": "v_l1", "accept_l2": "v_l2",
                    "call_l2": "v_cascade", "escalate_l3": "v_l3"}
    confusion: Counter = Counter()
    llm_calls = 0
    for row in dataset:
        if row.get("features") is None:
            confusion[(row["route_verdicts"]["v_l1"], row["gold"])] += 1
            continue
        key = route_to_key[row["oracle_route"]]
        confusion[(row["route_verdicts"][key], row["gold"])] += 1
        if key == "v_cascade":
            llm_calls += int((row.get("route_llm_calls") or {}).get(key, 0) or 0)
        elif key == "v_l3":
            llm_calls += max(1, int((row.get("route_llm_calls") or {})
                                    .get(key, 0) or 0))
    per_class = per_class_metrics(confusion)
    return {
        "macro_f1": macro_f1(confusion),
        "accuracy": accuracy(confusion, len(dataset)),
        "refute_precision": per_class["refute"]["precision"],
        "refute_recall": per_class["refute"]["recall"],
        "refute_f1": per_class["refute"]["f1"],
        "llm_invocations": llm_calls,
        "confusion[predicted, silver]": confusion_dict(confusion),
    }


def route_distribution(outcomes: dict[str, dict], rows: list[dict]) -> dict[str, int]:
    counts: Counter = Counter()
    for row in rows:
        for entry in outcomes[row["instance_id"]]["diagnostics"]:
            if entry.startswith("router_decision:"):
                counts[entry.split(":", 1)[1]] += 1
    return dict(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", default="egt_finetuned_v2",
                        help="MODELS注册表的checkpoint key")
    parser.add_argument("--nli-gate", type=float, default=NLI_GATE,
                        help="L2 NLI门控(默认0.70, 与固定级联参照一致)")
    parser.add_argument("--router", default="",
                        help="router.joblib路径(默认最新router_train_*运行)")
    parser.add_argument("--skip-sweep", action="store_true",
                        help="跳过alpha扫描(快速模式)")
    args = parser.parse_args()

    rows = load_frozen_qa(QA_FROZEN)
    silver = load_silver_labels(SILVER)
    checkpoint = MODELS[args.model_key]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        print(f"checkpoint不存在: {checkpoint} "
              f"(先跑 python tools/train_residual_nli.py)")
        sys.exit(1)
    router_path = Path(args.router) if args.router else find_latest_router()
    router = LearnedRouter.load(router_path)

    configs: dict[str, QAConsistencyModule] = {
        "baseline": QAConsistencyModule(use_experts=True),
        "l2_nli": QAConsistencyModule(
            use_experts=True, use_nli_residual=True,
            nli_model_path=checkpoint, nli_gate=args.nli_gate),
        "l3_llm": QAConsistencyModule(
            use_experts=True, use_llm_residual=True),
        "fixed_cascade": QAConsistencyModule(
            use_experts=True, use_cascade=True,
            nli_model_path=checkpoint, nli_gate=args.nli_gate),
        "learned_router": QAConsistencyModule(
            use_experts=True, use_learned_router=str(router_path),
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

    pareto_points: list[dict] = []
    if not args.skip_sweep:
        for alpha in ALPHAS:
            module = QAConsistencyModule(
                use_experts=True, use_learned_router=str(router_path),
                nli_model_path=checkpoint, nli_gate=args.nli_gate)
            if module.router is None:
                raise SystemExit("router加载失败, 无法扫描")
            module.router.cost_alpha = alpha
            out, stats = run_with_llm_counting(module, rows)
            score = score_outcomes(out, rows, silver)
            point = {
                "alpha": alpha,
                "macro_f1": score["macro_f1"],
                "refute_f1": score["per_class"]["refute"]["f1"],
                "refute_recall": score["per_class"]["refute"]["recall"],
                "llm_invocations": stats["invocations"],
                "llm_api_calls": stats["api_calls"],
                "route_distribution": route_distribution(out, rows),
            }
            pareto_points.append(point)
            print(f"alpha={alpha}: macro_f1={point['macro_f1']} "
                  f"refute_f1={point['refute_f1']} "
                  f"llm_invocations={point['llm_invocations']}")

    learned = scores["learned_router"]
    fixed = scores["fixed_cascade"]
    cost_quality_table = [{
        "config": name,
        "macro_f1": scores[name]["macro_f1"],
        "refute_precision": scores[name]["per_class"]["refute"]["precision"],
        "refute_recall": scores[name]["per_class"]["refute"]["recall"],
        "refute_f1": scores[name]["per_class"]["refute"]["f1"],
        "llm_invocations": llm_stats[name]["invocations"],
        "llm_api_calls": llm_stats[name]["api_calls"],
    } for name in configs]
    probe_dataset_path = router_path.parent / "router_dataset.jsonl"
    oracle_row = None
    if probe_dataset_path.exists():
        probe_rows = read_jsonl(probe_dataset_path)
        qa_probe_rows = [row for row in probe_rows
                         if row.get("split") == "qa_test"]
        if len(qa_probe_rows) == len(rows):
            oracle_row = oracle_router_simulation(qa_probe_rows)
            oracle_row["config"] = "oracle_router (analysis ceiling)"
            cost_quality_table.append({
                "config": oracle_row["config"],
                "macro_f1": oracle_row["macro_f1"],
                "refute_precision": oracle_row["refute_precision"],
                "refute_recall": oracle_row["refute_recall"],
                "refute_f1": oracle_row["refute_f1"],
                "llm_invocations": oracle_row["llm_invocations"],
                "llm_api_calls": 0,
            })
    targets = {
        "learned_macro_f1_ge_0.70": learned["macro_f1"] >= 0.70,
        "learned_llm_invocations_le_15":
            llm_stats["learned_router"]["invocations"] <= 15,
        "learned_vs_fixed_macro_f1_delta":
            round(learned["macro_f1"] - fixed["macro_f1"], 4),
        "learned_vs_fixed_llm_delta":
            llm_stats["learned_router"]["invocations"]
            - llm_stats["fixed_cascade"]["invocations"],
        "learned_beats_fixed_on_quality_and_cost":
            (learned["macro_f1"] >= fixed["macro_f1"]
             and llm_stats["learned_router"]["invocations"]
             < llm_stats["fixed_cascade"]["invocations"]),
    }

    report = {
        "n": len(rows),
        "label_type": "glm53_silver_not_gold",
        "checkpoint": checkpoint,
        "nli_gate": args.nli_gate,
        "router_path": str(router_path),
        "router": {
            "kind": router.kind,
            "model_type": router.model_type,
            "meta": router.meta,
        },
        "configs": scores,
        "llm_stats": llm_stats,
        "cost_quality_table": cost_quality_table,
        "learned_route_distribution": route_distribution(
            outcomes["learned_router"], rows),
        "oracle_router_ceiling": oracle_row,
        "pareto_points": pareto_points,
        "targets": targets,
    }

    run = open_run("eval_router", {
        "input": "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl",
        "labels": str(SILVER.relative_to(BASE)),
        "n": len(rows),
        "use_experts": True,
        "configs": list(configs),
        "model_key": args.model_key,
        "checkpoint": checkpoint,
        "nli_gate": args.nli_gate,
        "router_path": str(router_path),
        "alphas": list(ALPHAS),
        "llm": "glm-json-cache",
    })
    run.save_result(report)

    print(json.dumps({
        "n": report["n"],
        "router": {
            "path": str(router_path),
            "model_type": router.model_type,
            "train_meta": router.meta,
        },
        "cost_quality_table": cost_quality_table,
        "learned_route_distribution": report["learned_route_distribution"],
        "oracle_router_ceiling": oracle_row,
        "confusion_learned": learned["confusion[predicted, silver]"],
        "confusion_fixed_cascade": fixed["confusion[predicted, silver]"],
        "pareto_points": pareto_points,
        "targets": targets,
        "run": str(run.path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
