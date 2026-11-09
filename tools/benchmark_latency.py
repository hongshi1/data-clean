"""Benchmark per-instance verification latency across pipeline configs.

Measures wall time for each of the 91 frozen QA instances under:
  A. fast            (L0+L1+fusion, zero model — pure deterministic)
  B. standard-egt    (+L2 NLI residual: egt_finetuned_v2, EGT-only)
  C. standard-distill(+L2 NLI residual: distilled_v1, GLM-teacher distilled)
One-time costs (model loading, import warmup) reported separately.
Also measures baseline NLI models' raw pair-inference throughput for
cost context (not part of the pipeline).

Post-M66 architecture: no LLM at inference (L3 removed); the historical
cascade/LLM latency is reported from the pre-M66 run record instead.
"""
from __future__ import annotations

import json
import statistics
import time

from algorithms.consistency.eval_lib import build_qa_input, load_frozen_qa
from algorithms.consistency.nli_residual import DEFAULT_MODEL_KEY
from algorithms.consistency.qa_module import QAConsistencyModule
from tools.run_utils import open_run


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


def run_config(records, module, warmup: int = 2) -> list[float]:
    times: list[float] = []
    for index, record in enumerate(records):
        request = build_qa_input(record)
        start = time.perf_counter()
        module.verify(request)
        elapsed = time.perf_counter() - start
        if index >= warmup:
            times.append(elapsed)
    return times


def bench_pair_throughput(model_dirs: list[tuple[str, str]],
                           n_pairs: int = 512) -> dict[str, dict]:
    """Raw (premise, hypothesis) pair-inference throughput per model."""
    from algorithms.consistency.nli_local import NliLocal

    premise = ("数据库访问功能的方式名称为平板、桌面；修改数据功能的方式"
               "名称为平板、桌面；查询数据功能支持在运行阶段使用。")
    hypothesis = "所有操作均支持在桌面和平板设备上运行"
    out: dict[str, dict] = {}
    for key, path in model_dirs:
        try:
            nli = NliLocal(key)
            nli.ensure()
            pairs = [(premise, hypothesis)] * n_pairs
            start = time.perf_counter()
            nli.predict(pairs)
            elapsed = time.perf_counter() - start
            out[key] = {"pairs_per_s": round(n_pairs / elapsed, 1),
                        "ms_per_pair": round(elapsed / n_pairs * 1000, 2)}
        except (OSError, RuntimeError, ValueError) as exc:
            out[key] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


def main() -> None:
    records = load_frozen_qa()
    print(f"loaded {len(records)} frozen QA instances")

    # ---- warmup imports / caches outside the measurement ----
    t0 = time.perf_counter()
    module = QAConsistencyModule(use_experts=True)
    module.verify(build_qa_input(records[0]))
    import_ms = (time.perf_counter() - t0) * 1000
    print(f"[warmup] imports + first verify: {import_ms:.0f} ms (excluded)")

    # ---- A. fast (deterministic) ----
    det = QAConsistencyModule(use_experts=True)
    det_times = run_config(records, det)
    print("A. fast(deterministic L0+L1+fusion):", stats_ms(det_times))

    # ---- B. standard: egt_finetuned_v2 (model load timed separately) ----
    t0 = time.perf_counter()
    from algorithms.consistency.nli_residual import _load_model  # noqa: PLC0415
    _load_model(f"models/nli/{DEFAULT_MODEL_KEY}")
    egt_load_s = time.perf_counter() - t0
    print(f"[one-time] L2 egt_finetuned_v2 load: {egt_load_s:.1f} s")
    egt = QAConsistencyModule(use_experts=True, use_nli_residual=True,
                              nli_model_path=f"models/nli/{DEFAULT_MODEL_KEY}")
    egt_times = run_config(records, egt)
    print("B. standard-egt:", stats_ms(egt_times))

    # ---- C. standard: distilled_v1 ----
    t0 = time.perf_counter()
    _load_model("models/nli/distilled_v1")
    dist_load_s = time.perf_counter() - t0
    print(f"[one-time] L2 distilled_v1 load: {dist_load_s:.1f} s")
    dist = QAConsistencyModule(use_experts=True, use_nli_residual=True,
                               nli_model_path="models/nli/distilled_v1",
                               nli_gate=0.8)
    dist_times = run_config(records, dist)
    print("C. standard-distilled:", stats_ms(dist_times))

    # ---- D. baseline pair throughput (context) ----
    print("D. baseline pair-inference throughput (512 pairs)...")
    throughput = bench_pair_throughput([
        ("erlangshen-330m", "models/nli/Erlangshen-Roberta-330M-NLI"),
        ("mdeberta", "models/nli/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"),
        ("cmnli_finetuned", "models/nli/cmnli_finetuned_mdeberta"),
        ("egt_finetuned_v2", f"models/nli/{DEFAULT_MODEL_KEY}"),
        ("distilled_v1", "models/nli/distilled_v1"),
    ])
    for key, entry in throughput.items():
        print(f"   {key}: {entry}")

    summary = {
        "n_instances": len(records),
        "one_time": {
            "import_warmup_ms": round(import_ms),
            "egt_model_load_s": round(egt_load_s, 1),
            "distilled_model_load_s": round(dist_load_s, 1),
        },
        "fast_deterministic": stats_ms(det_times),
        "standard_egt_v2": stats_ms(egt_times),
        "standard_distilled_v1": stats_ms(dist_times),
        "baseline_pair_throughput": throughput,
        "note": "post-M66: no inference-time LLM; historical L3 cascade "
                "latency (~15-30s/escalated instance, network-bound) "
                "eliminated by design",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    run = open_run("benchmark_latency", summary)
    print(f"→ {run.path}")


if __name__ == "__main__":
    main()
