"""Benchmark per-instance verification latency across pipeline configs.

Measures wall time for each of the 91 frozen QA instances under:
  A. deterministic  (L0+L1+fusion, zero model/LLM)
  B. +L2 NLI        (adds local mDeBERTa inference on residual claims)
  C. +L3 cascade    (adds LLM escalation; cache-hit timing here,
                     real API latency reported separately)
One-time costs (model loading, import warmup) reported separately.
"""
from __future__ import annotations

import json
import statistics
import time

from algorithms.consistency.eval_lib import build_qa_input, load_frozen_qa
from algorithms.consistency.nli_residual import DEFAULT_MODEL_KEY
from algorithms.consistency.qa_module import QAConsistencyModule


def stats_ms(times: list[float]) -> dict[str, float]:
    ms = [t * 1000 for t in times]
    ordered = sorted(ms)
    p95_idx = min(int(len(ordered) * 0.95), len(ordered) - 1)
    return {
        "n": len(ms),
        "mean_ms": round(statistics.mean(ms), 1),
        "median_ms": round(statistics.median(ms), 1),
        "p95_ms": round(ordered[p95_idx], 1),
        "max_ms": round(max(ms), 1),
    }


def run_config(records, module, warmup: int = 1) -> list[float]:
    times: list[float] = []
    for index, record in enumerate(records):
        request = build_qa_input(record)
        start = time.perf_counter()
        module.verify(request)
        elapsed = time.perf_counter() - start
        if index >= warmup:
            times.append(elapsed)
    return times


def main() -> None:
    records = load_frozen_qa()
    print(f"loaded {len(records)} frozen QA instances")

    # ---- warmup imports / caches outside the measurement ----
    t0 = time.perf_counter()
    module = QAConsistencyModule(use_experts=True)
    module.verify(build_qa_input(records[0]))
    import_ms = (time.perf_counter() - t0) * 1000
    print(f"[warmup] imports + first verify: {import_ms:.0f} ms (excluded)")

    # ---- A. deterministic ----
    det = QAConsistencyModule(use_experts=True)
    det_times = run_config(records, det, warmup=2)
    print("A. deterministic(L0+L1+fusion):", stats_ms(det_times))

    # ---- B. +L2 NLI (model load timed separately) ----
    t0 = time.perf_counter()
    from algorithms.consistency.nli_residual import _load_model  # noqa: PLC0415
    _load_model(DEFAULT_MODEL_KEY)
    nli_load_s = time.perf_counter() - t0
    print(f"[one-time] L2 mDeBERTa model load: {nli_load_s:.1f} s")
    nli = QAConsistencyModule(use_experts=True, use_nli_residual=True)
    nli_times = run_config(records, nli, warmup=2)
    print("B. +L2 NLI:", stats_ms(nli_times))

    # ---- C. +L3 cascade (LLM from cache; real API latency separate) ----
    cas = QAConsistencyModule(use_experts=True, use_nli_residual=True,
                              use_cascade=True)
    cas_times, llm_calls = [], 0
    for index, record in enumerate(records):
        request = build_qa_input(record)
        start = time.perf_counter()
        result = cas.verify(request)
        elapsed = time.perf_counter() - start
        if index >= 2:
            cas_times.append(elapsed)
        if any("cascade_llm_calls_" in d and not d.endswith("_0")
               for d in result.diagnostics):
            llm_calls += 1
    print("C. +L3 cascade(cache-hit LLM):", stats_ms(cas_times))
    print(f"   instances with LLM escalation: {llm_calls}/{len(records)}")

    summary = {
        "n_instances": len(records),
        "one_time": {
            "import_warmup_ms": round(import_ms),
            "nli_model_load_s": round(nli_load_s, 1),
        },
        "deterministic": stats_ms(det_times),
        "nli": stats_ms(nli_times),
        "cascade_cached_llm": stats_ms(cas_times),
        "llm_escalated_instances": llm_calls,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
