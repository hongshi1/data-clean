"""Build the router training dataset and train the learned cascade router (C4).

Full-channel probing: every instance (EGT dev-split sample for training +
the 91 QA frozen corpus for held-out analysis) is run through the module
with a scripted router pinned to each route, recording the route's end-to-end
verdict and cost —

  accept_l1   L0/L1 experts only (0 LLM)
  accept_l2   + local L2 NLI, no escalation (0 LLM)
  call_l2     + L2 with the fixed S5 refute escalation (LLM on refutes)
  escalate_l3 direct L3 LLM on the residual claims (1+ LLM)

The oracle label is the minimum-cost correct route (router.oracle_route);
all-wrong instances map to accept_l2. Probing is lazy: L2 only runs when L1
is wrong, L3 only when L2 cannot fix it, so the probe spends LLM calls only
where the oracle label depends on them. LLM calls go through the cached
llm_json interface (first probe of the EGT rows pays real API calls, every
later run is a cache hit).

Leakage guards (the task's validity core): the learner trains ONLY on EGT
rows — the 91 QA rows are probed for held-out analysis, never trained on;
EGT rows whose question text matches a 91-QA question are dropped from the
training pool; the EGT sample is the NLI dev split, so the probed L2 is the
honest (not train-set-fitted) checkpoint.

Output (runs protocol, run dir router_train_*):
  router_dataset.jsonl  probe rows (features + route verdicts + oracle)
  router.joblib         trained router artifact for use_learned_router
  result.json           dataset scale, oracle distributions, CV report,
                        held-out 91-QA routing metrics
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import algorithms.common.llm_client as llm_client  # noqa: E402
from algorithms.consistency import nli_residual  # noqa: E402
from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.nli_training import is_dev_sample  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from algorithms.consistency.router import (  # noqa: E402
    FEATURE_ORDER,
    LearnedRouter,
    ROUTE_LABELS,
    nli_probe_features,
    oracle_route,
    router_metrics,
    save_scripted_router,
    train_router,
)
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

EGT_DATASET = (BASE / "data/gjb_438c/runs/build_egt_dataset_8a8716bb_20261027_003528"
               / "egt_dataset.jsonl")
QA_FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
          / "final_labels.jsonl")
NLI_GATE = 0.70
SEED = 42


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


def egt_request(row: dict[str, Any]):
    """EGT row -> QAInput: claim_text is the answer, evidence already frozen."""
    from algorithms.consistency.qa_models import QAInput, RetrievedEvidence, SourceRef

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
        ) for item in row["evidence"]
    )
    return QAInput(
        instance_id=str(row["sample_id"]),
        question=str(row["question"]),
        answer=str(row["claim_text"]),
        context_freeze_id=str(row.get("context_freeze_id") or "egt-frozen"),
        evidence=evidence,
    )


@contextmanager
def llm_counting() -> Iterator[dict[str, int]]:
    """Count llm_json invocations and real (cache-missing) API calls."""
    stats = {"invocations": 0, "stores": 0}
    original_llm_json = llm_client.llm_json
    original_store = llm_client._store

    def counting_llm_json(prompt, *args, **kwargs):
        stats["invocations"] += 1
        return original_llm_json(prompt, *args, **kwargs)

    def counting_store(ck, content, model):
        stats["stores"] += 1
        return original_store(ck, content, model)

    llm_client.llm_json = counting_llm_json
    llm_client._store = counting_store
    try:
        yield stats
    finally:
        llm_client.llm_json = original_llm_json
        llm_client._store = original_store


@contextmanager
def nli_probe_capture() -> Iterator[dict[str, list]]:
    """Capture the raw three-class NLI probabilities of one run."""
    captured: dict[str, list] = {"probs": []}
    original_infer = nli_residual._infer

    def recording_infer(entry, pairs):
        probs = original_infer(entry, pairs)
        captured["probs"].extend(probs)
        return probs

    nli_residual._infer = recording_infer
    try:
        yield captured
    finally:
        nli_residual._infer = original_infer


class RouteProber:
    """Lazy full-channel probe over one corpus via the production verify path.

    Each scripted router pins one route; the accept_l1 router also records
    phi(instance) — the exact features the production router is queried
    with — so training and serving share one feature pipeline.
    """

    def __init__(self, checkpoint: str, nli_gate: float, run_dir: Path) -> None:
        self.checkpoint = checkpoint
        self.nli_gate = nli_gate
        scripted = {}
        for route in ROUTE_LABELS:
            path = run_dir / f"scripted_{route}.joblib"
            save_scripted_router(path, route, record=(route == "accept_l1"))
            scripted[route] = path
        self.modules = {
            route: QAConsistencyModule(
                use_experts=True, use_learned_router=str(path),
                nli_model_path=checkpoint, nli_gate=nli_gate)
            for route, path in scripted.items()
        }
        self.llm_total = {"invocations": 0, "stores": 0}

    def _run(self, route: str, request) -> tuple[str, dict[str, int], dict | None]:
        """One verify() run pinned to `route`; returns (verdict, llm stats,
        recorded features when the accept_l1 recorder fired)."""
        module = self.modules[route]
        recorder = module.router
        recorded = len(recorder.recorded_features) if recorder is not None else 0
        features: dict | None = None
        with llm_counting() as stats:
            result = module.verify(request)
        if recorder is not None and len(recorder.recorded_features) > recorded:
            features = recorder.recorded_features[-1]
        self.llm_total["invocations"] += stats["invocations"]
        self.llm_total["stores"] += stats["stores"]
        return result.verdict, stats, features

    def probe(self, request, gold: str) -> dict[str, Any]:
        v_l1, llm_l1, features = self._run("accept_l1", request)
        row: dict[str, Any] = {
            "instance_id": request.instance_id,
            "gold": gold,
            "route_verdicts": {"v_l1": v_l1},
            "route_llm_calls": {},
            "nli_probe": None,
            "features": None,
            "oracle_route": None,
            "excluded": None,
        }
        if features is None:
            row["excluded"] = "no_residual_decision_point"
            return row
        row["features"] = features
        if v_l1 == gold:
            row["oracle_route"] = "accept_l1"
            return row
        with nli_probe_capture() as captured:
            v_l2, llm_l2, _ = self._run("accept_l2", request)
        row["route_verdicts"]["v_l2"] = v_l2
        row["nli_probe"] = nli_probe_features(captured["probs"])
        if v_l2 == gold:
            row["oracle_route"] = "accept_l2"
            return row
        v_cascade, llm_cascade, _ = self._run("call_l2", request)
        row["route_verdicts"]["v_cascade"] = v_cascade
        row["route_llm_calls"]["v_cascade"] = llm_cascade["invocations"]
        v_l3, llm_l3, _ = self._run("escalate_l3", request)
        row["route_verdicts"]["v_l3"] = v_l3
        row["route_llm_calls"]["v_l3"] = llm_l3["invocations"]
        row["oracle_route"] = oracle_route(
            v_l1, v_l2, v_cascade, v_l3, gold,
            escalation_calls=llm_cascade["invocations"],
            l3_direct_calls=llm_l3["invocations"])
        return row


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    feature_rows = [r for r in rows if r["features"] is not None]
    excluded = Counter(r["excluded"] for r in rows if r["excluded"])
    outcome_accuracy = {}
    for key in ("v_l1", "v_l2", "v_cascade", "v_l3"):
        probed = [r for r in feature_rows if key in r["route_verdicts"]]
        outcome_accuracy[key] = {
            "n_probed": len(probed),
            "accuracy": (round(sum(1 for r in probed
                                   if r["route_verdicts"][key] == r["gold"])
                               / len(probed), 4) if probed else None),
        }
    return {
        "n_instances": len(rows),
        "n_feature_rows": len(feature_rows),
        "excluded": dict(excluded),
        "oracle_distribution": dict(Counter(
            r["oracle_route"] for r in feature_rows)),
        "route_outcome_accuracy": outcome_accuracy,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-key", default="egt_finetuned_v2",
                        help="MODELS注册表的checkpoint key")
    parser.add_argument("--nli-gate", type=float, default=NLI_GATE,
                        help="L2 NLI门控(默认0.70, 与固定级联参照一致)")
    parser.add_argument("--egt-limit", type=int, default=0,
                        help="EGT抽样上限(0=全部dev split, 调试用)")
    parser.add_argument("--qa-limit", type=int, default=0,
                        help="91 QA探测上限(0=全部, 调试用)")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    checkpoint = MODELS[args.model_key]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        print(f"checkpoint不存在: {checkpoint} (先跑 python tools/train_residual_nli.py)")
        sys.exit(1)

    qa_rows = read_jsonl(QA_FROZEN)
    silver = {row["instance_id"]: row["final_verdict"]
              for row in read_jsonl(SILVER)}
    qa_questions = {row["question"] for row in qa_rows}
    if args.qa_limit:
        qa_rows = qa_rows[:args.qa_limit]

    egt_rows = [row for row in read_jsonl(EGT_DATASET)
                if is_dev_sample(row["sample_id"])]
    n_dev = len(egt_rows)
    egt_rows = [row for row in egt_rows
                if row["question"] not in qa_questions]
    n_overlap_removed = n_dev - len(egt_rows)
    if args.egt_limit:
        egt_rows = egt_rows[:args.egt_limit]

    run = open_run("router_train", {
        "egt_dataset": str(EGT_DATASET.relative_to(BASE)),
        "qa_frozen": str(QA_FROZEN.relative_to(BASE)),
        "labels": str(SILVER.relative_to(BASE)),
        "model_key": args.model_key,
        "checkpoint": checkpoint,
        "nli_gate": args.nli_gate,
        "seed": args.seed,
        "n_egt_dev": n_dev,
        "n_egt_after_qa_question_filter": len(egt_rows),
        "n_qa": len(qa_rows),
        "egt_limit": args.egt_limit,
        "qa_limit": args.qa_limit,
        "llm": "glm-json-cache",
    })
    print(f"run dir: {run.path}")

    prober = RouteProber(checkpoint, args.nli_gate, run.path)
    egt_probe: list[dict[str, Any]] = []
    for i, row in enumerate(egt_rows, 1):
        egt_probe.append(prober.probe(egt_request(row), str(row["label"])))
        if i % 50 == 0 or i == len(egt_rows):
            print(f"EGT probe: {i}/{len(egt_rows)} "
                  f"(llm invocations so far: {prober.llm_total['invocations']})")

    qa_probe: list[dict[str, Any]] = []
    for i, row in enumerate(qa_rows, 1):
        request = request_from_dict(row)
        qa_probe.append(prober.probe(request, silver[request.instance_id]))
        if i % 25 == 0 or i == len(qa_rows):
            print(f"QA probe: {i}/{len(qa_rows)} "
                  f"(llm invocations so far: {prober.llm_total['invocations']})")

    for row in egt_probe:
        row["split"] = "egt_train"
        row["source"] = "egt"
    for row in qa_probe:
        row["split"] = "qa_test"
        row["source"] = "qa_frozen"
    all_rows = egt_probe + qa_probe
    dataset_path = run.path / "router_dataset.jsonl"
    with open(dataset_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    train_rows = [r for r in egt_probe if r["features"] is not None]
    test_rows = [r for r in qa_probe if r["features"] is not None]
    train_ids = {r["instance_id"] for r in train_rows}
    qa_ids = {r["instance_id"] for r in qa_probe}
    leakage = {
        "qa_instance_ids_in_train": len(train_ids & qa_ids),
        "qa_questions_in_train_pool": n_overlap_removed,
        "train_split": "egt_nli_dev_split_minus_qa_question_overlap",
    }
    if train_ids & qa_ids:
        raise RuntimeError("leakage guard failed: QA instance ids in training rows")

    payload, train_report = train_router(train_rows, seed=args.seed)
    router_path = LearnedRouter(payload).save(run.path / "router.joblib")
    router = LearnedRouter.load(router_path)

    report = {
        "n": {"egt": len(egt_probe), "qa": len(qa_probe)},
        "egt": summarize(egt_probe),
        "qa_test": summarize(qa_probe),
        "training": train_report,
        "train_routing_in_sample": router_metrics(train_rows, router),
        "heldout_qa_routing": router_metrics(test_rows, router),
        "llm_probe": {
            "invocations": prober.llm_total["invocations"],
            "api_calls": prober.llm_total["stores"],
            "cache_hits": prober.llm_total["invocations"]
            - prober.llm_total["stores"],
        },
        "leakage_guards": leakage,
        "router_path": str(router_path),
        "feature_order": list(FEATURE_ORDER),
    }
    run.save_result(report)

    print(json.dumps({
        "run": str(run.path),
        "egt": report["egt"],
        "qa_test": report["qa_test"],
        "training": {
            "selected_model": train_report["selected_model"],
            "n_train_rows": train_report["n_train_rows"],
            "route_distribution": train_report["route_distribution"],
            "cv": {k: v for k, v in train_report["models"].items()},
        },
        "heldout_qa_routing": report["heldout_qa_routing"],
        "llm_probe": report["llm_probe"],
        "leakage_guards": leakage,
        "router_path": str(router_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
