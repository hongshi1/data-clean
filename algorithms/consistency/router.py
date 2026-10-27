"""Learned cascade router (paper C4: the "learning" half of the FrugalGPT /
RouteLLM pattern generalized to heterogeneous verifiers).

The fixed S5 cascade routes every residual claim the same way (L2 NLI judges
all, its refute candidates escalate to L3). This module replaces that fixed
policy with a learned per-instance decision made once, after the
deterministic L0/L1 channels and before any residual judge runs:

  accept_l1    skip the residual channels entirely (cost 0)
  accept_l2    run the local L2 NLI, trust its verdicts, never escalate (cost 1)
  call_l2      run L2, escalate its refute candidates to L3 per the fixed
               S5 policy (cost 2 + 10 per escalated LLM call)
  escalate_l3  skip L2, judge the residual claims directly with the L3 LLM
               channel (cost 10 per batched call)

Route costs follow the task spec (L1=0, local L2=1, LLM call=10); call_l2
carries base cost 2 because escalation is part of its semantics.

Oracle labels (training supervision) are the minimum-cost correct route:
L1 correct -> accept_l1; otherwise the cheapest route whose end-to-end
verdict matches gold (ties broken by cost then label order); when no route
is correct the label is accept_l2 (the cheapest non-trivial acceptance,
per spec). Unprobed routes count as not-correct: the probe skips them only
when they provably cannot be the minimum-cost correct route.

Feature extraction is pre-L2 only (L1 verdict/expert counts, residual
count, claim-kind mix, check-item families, question/answer shape, evidence
stats) 鈥?exactly the state ``QAConsistencyModule.verify`` holds at the
decision point, so training and serving see the same feature distribution.
NLI three-class probabilities are recorded by the probe tool as analysis
columns but deliberately NOT model inputs (the decision precedes L2).

Hard rules honored: no I/O at import time, utf-8 everywhere, explicit
exception types, seed=42 training.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROUTE_LABELS: tuple[str, ...] = ("accept_l1", "accept_l2", "call_l2", "escalate_l3")

ROUTE_COSTS: dict[str, float] = {
    "accept_l1": 0.0,
    "accept_l2": 1.0,
    "call_l2": 2.0,
    "escalate_l3": 10.0,
}

LLM_CALL_COST = 10.0

RESIDUAL_METHODS = ("semantic_unresolved", "conservative_unresolved")

EXPERT_METHOD_PREFIXES: tuple[str, ...] = (
    "l0_entity_detector:",
    "e1_template_match",
    "sequence_alignment",
    "trace_bidirectional_join",
    "gjb_presence_check",
    "id_join_registry",
    "enum_join_registry",
)

FEATURE_ORDER: tuple[str, ...] = (
    "n_evidence",
    "evidence_table_fraction",
    "question_len",
    "answer_len",
    "n_claims",
    "claim_numeric",
    "claim_identifier",
    "claim_enum",
    "claim_quoted",
    "claim_semantic",
    "n_check_items",
    "check_term",
    "check_param",
    "check_logic",
    "check_gjb",
    "l1_support",
    "l1_refute",
    "l1_nie",
    "l1_expert_hits",
    "residual_count",
)

PAYLOAD_FORMAT = "learned_router_v1"

_TRAIN_EXCEPTIONS = (OSError, ValueError, KeyError, AttributeError, ImportError,
                     RuntimeError)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def extract_route_features(
        question: str,
        answer: str,
        evidence: tuple,
        claim_results: tuple,
        claim_kinds: tuple[str, ...],
        check_items: tuple[str, ...]) -> dict[str, float]:
    """Feature vector phi(instance) at the post-L1 / pre-L2 decision point.

    ``claim_results`` is the pre-fusion L0/L1 state (per-claim results plus
    expert-channel results) exactly as ``verify`` holds it when the router
    fires; ``claim_kinds`` are the decomposed answer-claim kinds.
    """
    n_evidence = len(evidence)
    table = sum(1 for ev in evidence if getattr(ev, "source_type", "") == "table")
    kinds = Counter(claim_kinds)
    items = Counter(check_items)
    verdicts = Counter(r.verdict for r in claim_results)
    expert_hits = sum(1 for r in claim_results
                      if r.method.startswith(EXPERT_METHOD_PREFIXES))
    residual = sum(1 for r in claim_results if r.method in RESIDUAL_METHODS)

    def family(prefix: str) -> float:
        return float(sum(v for k, v in items.items() if k.startswith(prefix)))

    return {
        "n_evidence": float(n_evidence),
        "evidence_table_fraction": (table / n_evidence) if n_evidence else 0.0,
        "question_len": float(len(_compact(question))),
        "answer_len": float(len(_compact(answer))),
        "n_claims": float(len(claim_kinds)),
        "claim_numeric": float(kinds.get("numeric", 0)),
        "claim_identifier": float(kinds.get("identifier", 0)),
        "claim_enum": float(kinds.get("enum", 0)),
        "claim_quoted": float(kinds.get("quoted", 0)),
        "claim_semantic": float(kinds.get("semantic", 0)),
        "n_check_items": float(len(items)),
        "check_term": family("TERM-"),
        "check_param": family("PARAM-"),
        "check_logic": family("LOGIC-"),
        "check_gjb": family("GJB-"),
        "l1_support": float(verdicts.get("support", 0)),
        "l1_refute": float(verdicts.get("refute", 0)),
        "l1_nie": float(verdicts.get("not_in_evidence", 0)),
        "l1_expert_hits": float(expert_hits),
        "residual_count": float(residual),
    }


def feature_vector(features: dict[str, float],
                   order: tuple[str, ...] = FEATURE_ORDER) -> list[float]:
    return [float(features.get(name, 0.0)) for name in order]


def oracle_route(
        v_l1: str | None,
        v_l2: str | None,
        v_cascade: str | None,
        v_l3: str | None,
        gold: str,
        *,
        escalation_calls: int = 0,
        l3_direct_calls: int = 0) -> str:
    """Minimum-cost correct route label (all routes wrong -> accept_l2).

    Unprobed route verdicts (None) count as not-correct: the lazy probe only
    skips a route when it cannot be the minimum-cost correct one (L1 correct
    makes every other route more expensive; L2 correct beats call_l2/escalate
    on cost).
    """
    if v_l1 == gold:
        return "accept_l1"
    candidates: list[tuple[str, float]] = []
    if v_l2 == gold:
        candidates.append(("accept_l2", ROUTE_COSTS["accept_l2"]))
    if v_cascade == gold:
        candidates.append(
            ("call_l2",
             ROUTE_COSTS["call_l2"] + LLM_CALL_COST * escalation_calls))
    if v_l3 == gold:
        candidates.append(
            ("escalate_l3",
             ROUTE_COSTS["escalate_l3"]
             + LLM_CALL_COST * max(0, l3_direct_calls - 1)))
    if not candidates:
        return "accept_l2"
    return min(candidates, key=lambda item: (item[1],
                                             ROUTE_LABELS.index(item[0])))[0]


class LearnedRouter:
    """Loaded router artifact; decides route = argmax over P(route|phi).

    ``cost_alpha`` > 0 turns the decision cost-sensitive:
    argmax P(route) / (1 + ROUTE_COSTS[route]) ** cost_alpha, the knob the
    eval sweep uses for the cost-quality Pareto curve (0 = plain argmax).
    Scripted payloads (``kind="scripted"``) always return ``fixed_route``
    and optionally record the phi they were queried with 鈥?the probe tool
    builds its per-route runs on exactly this instrumentation.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise ValueError("router payload must be a dict")
        if payload.get("format") != PAYLOAD_FORMAT:
            raise ValueError(f"unsupported router payload format: "
                             f"{payload.get('format')!r}")
        kind = payload.get("kind")
        if kind not in ("learned", "scripted"):
            raise ValueError(f"unsupported router kind: {kind!r}")
        if kind == "scripted" and payload.get("fixed_route") not in ROUTE_LABELS:
            raise ValueError("scripted router needs a valid fixed_route")
        if kind == "learned" and payload.get("model") is None:
            raise ValueError("learned router payload has no model")
        order = tuple(payload.get("feature_order") or FEATURE_ORDER)
        if not order or len(set(order)) != len(order):
            raise ValueError("router feature_order must be non-empty and unique")
        self.kind = kind
        self.model = payload.get("model")
        self.model_type = payload.get("model_type")
        self.fixed_route = payload.get("fixed_route")
        self.feature_order = order
        self.cost_alpha = float(payload.get("cost_alpha", 0.0))
        self.record = bool(payload.get("record", False))
        self.recorded_features: list[dict[str, float]] = []
        self.meta = payload.get("meta") or {}

    @classmethod
    def load(cls, path: str | Path) -> "LearnedRouter":
        import joblib

        return cls(joblib.load(Path(path)))

    def save(self, path: str | Path) -> Path:
        import joblib

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": PAYLOAD_FORMAT,
            "kind": self.kind,
            "model": self.model,
            "model_type": self.model_type,
            "fixed_route": self.fixed_route,
            "feature_order": self.feature_order,
            "cost_alpha": self.cost_alpha,
            "record": self.record,
            "meta": self.meta,
        }
        joblib.dump(payload, target)
        return target

    def probabilities(self, features: dict[str, float]) -> dict[str, float]:
        """P(route = r | phi) over ROUTE_LABELS (missing classes -> 0.0)."""
        probs = {label: 0.0 for label in ROUTE_LABELS}
        if self.kind == "scripted":
            assert self.fixed_route is not None
            probs[self.fixed_route] = 1.0
            return probs
        assert self.model is not None
        matrix = [feature_vector(features, self.feature_order)]
        raw = self.model.predict_proba(matrix)[0]
        classes = [str(c) for c in self.model.classes_]
        for label, prob in zip(classes, raw):
            if label in probs:
                probs[label] = float(prob)
        return probs

    def route(self, features: dict[str, float]) -> str:
        if self.record:
            self.recorded_features.append(dict(features))
        probs = self.probabilities(features)
        if self.cost_alpha <= 0.0:
            return max(probs, key=probs.__getitem__)
        return max(
            probs,
            key=lambda label: probs[label]
            / ((1.0 + ROUTE_COSTS[label]) ** self.cost_alpha),
        )


def save_scripted_router(path: str | Path, route: str, *,
                         record: bool = False) -> Path:
    if route not in ROUTE_LABELS:
        raise ValueError(f"unknown scripted route: {route!r}")
    payload = {
        "format": PAYLOAD_FORMAT,
        "kind": "scripted",
        "model": None,
        "model_type": None,
        "fixed_route": route,
        "feature_order": FEATURE_ORDER,
        "cost_alpha": 0.0,
        "record": record,
        "meta": {"note": "probe instrumentation; returns a fixed route"},
    }
    router = LearnedRouter(payload)
    return router.save(path)


def nli_probe_features(prob_rows: list[dict[str, float]]) -> dict[str, float]:
    """Aggregate raw three-class NLI probabilities (analysis columns)."""
    n = len(prob_rows)
    if not n:
        return {"n_pairs": 0.0, "mean_contradiction": 0.0,
                "max_contradiction": 0.0, "mean_entropy": 0.0,
                "mean_max_prob": 0.0}
    contra = [float(row.get("contradiction", 0.0)) for row in prob_rows]
    entropies = []
    maxes = []
    for row in prob_rows:
        ps = [max(1e-12, float(row.get(k, 0.0)))
              for k in ("entailment", "neutral", "contradiction")]
        total = sum(ps)
        ps = [p / total for p in ps]
        entropies.append(-sum(p * math.log(p) for p in ps))
        maxes.append(max(ps))
    return {
        "n_pairs": float(n),
        "mean_contradiction": sum(contra) / n,
        "max_contradiction": max(contra),
        "mean_entropy": sum(entropies) / n,
        "mean_max_prob": sum(maxes) / n,
    }


def train_router(rows: list[dict[str, Any]], seed: int = 42
                 ) -> tuple[dict[str, Any], dict[str, Any]]:
    """Train the route classifier on probe rows (features + oracle_route).

    Trains both a GradientBoostingClassifier and a LogisticRegression with
    seed=42, selects by stratified 5-fold CV macro-F1 (accuracy reported
    too), refits the winner on all rows. A single-class training set
    degrades to a scripted majority router. Returns (payload, report).
    """
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    usable = [row for row in rows
              if row.get("features") and row.get("oracle_route") in ROUTE_LABELS]
    if not usable:
        raise ValueError("no usable training rows (features + oracle_route)")
    x = [feature_vector(row["features"]) for row in usable]
    y = [str(row["oracle_route"]) for row in usable]
    distribution = Counter(y)
    report: dict[str, Any] = {
        "seed": seed,
        "n_train_rows": len(usable),
        "route_distribution": dict(distribution),
        "feature_order": list(FEATURE_ORDER),
        "models": {},
        "selected_model": None,
    }
    if len(distribution) == 1:
        majority = next(iter(distribution))
        payload = {
            "format": PAYLOAD_FORMAT,
            "kind": "scripted",
            "model": None,
            "model_type": "majority_single_class",
            "fixed_route": majority,
            "feature_order": FEATURE_ORDER,
            "cost_alpha": 0.0,
            "record": False,
            "meta": {"note": "single route class in training data"},
        }
        report["selected_model"] = "majority_single_class"
        return payload, report

    min_class = min(distribution.values())
    models: dict[str, Any] = {
        "gradient_boosting": GradientBoostingClassifier(
            random_state=seed, n_estimators=200, max_depth=3,
            learning_rate=0.1),
        "logistic_regression": LogisticRegression(
            max_iter=2000, random_state=seed),
    }
    can_cv = min_class >= 2
    n_splits = max(2, min(5, min_class)) if can_cv else 0
    splitter = (StratifiedKFold(n_splits=n_splits, shuffle=True,
                                random_state=seed) if can_cv else None)
    best_name: str | None = None
    best_f1 = -1.0
    for name, model in models.items():
        try:
            if can_cv:
                assert splitter is not None
                predictions = cross_val_predict(model, x, y, cv=splitter)
            else:
                model.fit(x, y)
                predictions = model.predict(x)
            macro = float(f1_score(y, predictions, average="macro"))
            accuracy = float(sum(p == t for p, t in zip(predictions, y))
                             / len(y))
        except _TRAIN_EXCEPTIONS as exc:
            report["models"][name] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        report["models"][name] = {
            "cv_macro_f1" if can_cv else "in_sample_macro_f1":
                round(macro, 4),
            "cv_accuracy" if can_cv else "in_sample_accuracy":
                round(accuracy, 4),
            "cv_splits": n_splits if can_cv else 0,
        }
        if macro > best_f1:
            best_name, best_f1 = name, macro
    if best_name is None:
        raise RuntimeError("both router model candidates failed CV training")
    final = models[best_name]
    final.fit(x, y)
    payload = {
        "format": PAYLOAD_FORMAT,
        "kind": "learned",
        "model": final,
        "model_type": best_name,
        "fixed_route": None,
        "feature_order": FEATURE_ORDER,
        "cost_alpha": 0.0,
        "record": False,
        "meta": {
            "seed": seed,
            "n_train_rows": len(usable),
            "route_distribution": dict(distribution),
            "cv": report["models"][best_name],
        },
    }
    report["selected_model"] = best_name
    return payload, report


def router_metrics(rows: list[dict[str, Any]], router: LearnedRouter,
                   ) -> dict[str, Any]:
    """Routing predictions vs oracle labels + simulated route outcomes.

    ``rows`` are probe rows (features, oracle_route, route_verdicts,
    route_llm_calls, gold). The simulated verdict/cost uses each row's
    probed per-route outcomes, so the end-to-end quality of the learned
    policy can be estimated without re-running the module.
    """
    route_to_key = {"accept_l1": "v_l1", "accept_l2": "v_l2",
                    "call_l2": "v_cascade", "escalate_l3": "v_l3"}
    n = len(rows)
    confusion: Counter = Counter()
    route_counts: Counter = Counter()
    oracle_counts: Counter = Counter()
    agreement = 0
    correct = 0
    llm_calls = 0
    oracle_llm_calls = 0
    for row in rows:
        route = router.route(dict(row["features"]))
        route_counts[route] += 1
        oracle_counts[row["oracle_route"]] += 1
        if route == row["oracle_route"]:
            agreement += 1
        key = route_to_key[route]
        verdict = (row.get("route_verdicts") or {}).get(key)
        gold = row.get("gold", "")
        if verdict is not None:
            confusion[(verdict, gold)] += 1
            if verdict == gold:
                correct += 1
        if key == "v_cascade":
            llm_calls += int((row.get("route_llm_calls") or {}).get(key, 0) or 0)
        if key == "v_l3":
            llm_calls += max(1, int((row.get("route_llm_calls") or {}).get(key, 0) or 0))
        okey = route_to_key[row["oracle_route"]]
        if okey == "v_cascade":
            oracle_llm_calls += int(
                (row.get("route_llm_calls") or {}).get(okey, 0) or 0)
        if okey == "v_l3":
            oracle_llm_calls += max(1, int(
                (row.get("route_llm_calls") or {}).get(okey, 0) or 0))
    return {
        "n": n,
        "routing_agreement": round(agreement / n, 4) if n else 0.0,
        "route_distribution": dict(route_counts),
        "oracle_distribution": dict(oracle_counts),
        "simulated_accuracy": round(correct / n, 4) if n else 0.0,
        "simulated_confusion": {f"{p}|{g}": c for (p, g), c in
                                sorted(confusion.items())},
        "simulated_llm_calls": llm_calls,
        "oracle_llm_calls": oracle_llm_calls,
    }


__all__ = [
    "EXPERT_METHOD_PREFIXES",
    "FEATURE_ORDER",
    "LLM_CALL_COST",
    "ROUTE_COSTS",
    "ROUTE_LABELS",
    "RESIDUAL_METHODS",
    "LearnedRouter",
    "extract_route_features",
    "feature_vector",
    "oracle_route",
    "router_metrics",
    "nli_probe_features",
    "save_scripted_router",
    "train_router",
]
