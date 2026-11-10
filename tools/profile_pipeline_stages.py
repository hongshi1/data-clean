"""Stage-by-stage latency profile of the consistency verification pipeline.

Instruments every architectural component of QAConsistencyModule.verify()
and reports per-stage wall time on each evaluation corpus:

  qa91 (04号, 91实例) / violations (17实例) / crossdoc-150 (5文档×30)

Stages (additive, per instance):
  1 问题路由+claim分解   route_question + decompose_claims
  2 证据线性化           linearize_context (evidence→statements)
  3 per-claim通道        _verify_claim loop (numeric/quoted/enum/id/semantic)
  4 L0 NER+L1专家        _expert_channels (9 experts, 确定性)
  5 L2 NLI残差           verify_residual_claims_nli (整体)
    ├ premise构造        residual_premise (确定性, L2的子项)
    └ 模型推理           _infer (GPU, L2的子项)
  6 融合+聚合            _fuse_per_claim + _aggregate
  7 其他开销             total − sum(1..6)

Usage:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
  python tools/profile_pipeline_stages.py [--tier distilled_v1|fast]
"""
from __future__ import annotations

import argparse
import functools
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency import nli_residual  # noqa: E402
from algorithms.consistency import qa_module  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    load_frozen_qa,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

TIMES: dict[str, float] = defaultdict(float)
COUNTS: dict[str, int] = defaultdict(int)

STAGES = (
    "1_路由与claim分解",
    "2_证据线性化",
    "3_per-claim通道",
    "4_L0NER与L1专家",
    "5_L2NLI残差",
    "5a_NLI_premise构造",
    "5b_NLI_模型推理",
    "6_融合",
    "6_聚合",
)


def timed(stage: str, fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            TIMES[stage] += time.perf_counter() - start
            COUNTS[stage] += 1

    return wrapper


def install_probes() -> None:
    qa_module.route_question = timed("1_路由与claim分解",
                                     qa_module.route_question)
    qa_module.decompose_claims = timed("1_路由与claim分解",
                                       qa_module.decompose_claims)
    qa_module.linearize_context = timed("2_证据线性化",
                                        qa_module.linearize_context)
    QAConsistencyModule._verify_claim = timed(
        "3_per-claim通道", QAConsistencyModule._verify_claim)
    QAConsistencyModule._expert_channels = timed(
        "4_L0NER与L1专家", QAConsistencyModule._expert_channels)
    nli_residual.verify_residual_claims_nli = timed(
        "5_L2NLI残差", nli_residual.verify_residual_claims_nli)
    nli_residual.residual_premise = timed(
        "5a_NLI_premise构造", nli_residual.residual_premise)
    nli_residual._infer = timed("5b_NLI_模型推理", nli_residual._infer)
    # _fuse_per_claim是staticmethod: 包装后须以staticmethod挂回类,
    # 否则实例访问会把self绑定为首参
    QAConsistencyModule._fuse_per_claim = staticmethod(timed(
        "6_融合", QAConsistencyModule._fuse_per_claim))
    QAConsistencyModule._aggregate = timed(
        "6_聚合", QAConsistencyModule._aggregate)


def load_corpora() -> dict[str, list[dict]]:
    corpora: dict[str, list[dict]] = {"qa91": load_frozen_qa()}
    vio = (BASE / "data/gjb_438c/localization_gold"
           / "violation_evalset_v1.jsonl")
    corpora["violations17"] = [
        json.loads(line) for line in
        vio.read_text(encoding="utf-8").splitlines() if line.strip()]
    cross: list[dict] = []
    for doc in ("05", "06", "07", "08", "10"):
        p = BASE / f"data/gjb_438c/qa_frozen/crossdoc{doc}_evalset_v1.jsonl"
        cross += [json.loads(line) for line in
                  p.read_text(encoding="utf-8").splitlines() if line.strip()]
    corpora["crossdoc150"] = cross
    return corpora


def profile_corpus(module: QAConsistencyModule,
                   records: list[dict]) -> dict:
    for key in TIMES:
        TIMES[key] = 0.0
        COUNTS[key] = 0
    per_instance: list[float] = []
    for record in records:
        request = build_qa_input(record)
        start = time.perf_counter()
        module.verify(request)
        per_instance.append(time.perf_counter() - start)
    total = sum(per_instance)
    ms = {stage: TIMES.get(stage, 0.0) * 1000 for stage in STAGES}
    additive = (ms["1_路由与claim分解"] + ms["2_证据线性化"]
                + ms["3_per-claim通道"] + ms["4_L0NER与L1专家"]
                + ms["5_L2NLI残差"] + ms["6_融合"] + ms["6_聚合"])
    other_ms = max(0.0, total * 1000 - additive)
    stage_ms = {k: round(v, 1) for k, v in ms.items() if k not in (
        "5a_NLI_premise构造", "5b_NLI_模型推理")}
    stage_ms["7_其他开销"] = round(other_ms, 1)
    return {
        "n": len(records),
        "total_s": round(total, 2),
        "mean_ms_per_instance": round(total / len(records) * 1000, 1),
        "median_ms": round(statistics.median(per_instance) * 1000, 1),
        "p95_ms": round(sorted(per_instance)[
            min(int(len(per_instance) * 0.95), len(per_instance) - 1)] * 1000, 1),
        "stage_total_ms": stage_ms,
        "stage_mean_ms": {k: round(v / len(records), 2)
                          for k, v in stage_ms.items()},
        "nli_breakdown_ms": {
            "premise": round(ms["5a_NLI_premise构造"], 1),
            "model_infer": round(ms["5b_NLI_模型推理"], 1),
        },
        "nli_calls": COUNTS.get("5_L2NLI残差", 0),
        "claim_verifies": COUNTS.get("3_per-claim通道", 0),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="distilled_v1",
                        choices=["distilled_v1", "egt_v2", "fast"])
    args = parser.parse_args()

    install_probes()
    if args.tier == "fast":
        module = QAConsistencyModule(use_experts=True)
        model_note = "fast: 纯确定性(L0+L1), 无L2"
    else:
        path = ("models/nli/egt_finetuned_v2"
                if args.tier == "egt_v2" else "models/nli/distilled_v1")
        module = QAConsistencyModule(
            use_experts=True, use_nli_residual=True,
            nli_model_path=path,
            nli_gate=0.8 if args.tier == "distilled_v1" else 0.7)
        model_note = f"standard: L2={args.tier}"
    # warmup (model load + import, excluded)
    warm = load_frozen_qa()[0]
    module.verify(build_qa_input(warm))
    print(f"tier={args.tier} ({model_note}), warmup excluded\n")

    corpora = load_corpora()
    results: dict[str, dict] = {}
    for name, records in corpora.items():
        results[name] = profile_corpus(module, records)
        r = results[name]
        print(f"[{name}] n={r['n']} total={r['total_s']}s "
              f"mean={r['mean_ms_per_instance']}ms/例 "
              f"(median {r['median_ms']} p95 {r['p95_ms']})")

    # ── markdown table: stage × corpus (mean ms/instance) ──
    stage_keys = ["1_路由与claim分解", "2_证据线性化", "3_per-claim通道",
                  "4_L0NER与L1专家", "5_L2NLI残差", "6_融合", "6_聚合",
                  "7_其他开销"]
    names = list(corpora)
    header = "| 阶段 | " + " | ".join(
        f"{n} (ms/例)" for n in names) + " | 占比* |"
    sep = "|------|" + "---|" * (len(names) + 1)
    print("\n" + header)
    print(sep)
    for stage in stage_keys:
        cells = [f"{results[n]['stage_mean_ms'][stage]:.2f}"
                 for n in names]
        share = (results['qa91']['stage_total_ms'][stage]
                 / max(1e-9, sum(results['qa91']['stage_total_ms'].values()))
                 * 100)
        print(f"| {stage} | " + " | ".join(cells) + f" | {share:.1f}% |")
    totals = [f"**{results[n]['mean_ms_per_instance']:.1f}**" for n in names]
    print("| **总计** | " + " | ".join(totals) + " | 100% |")
    print("*占比按qa91列计算\n")

    for name in names:
        r = results[name]
        print(f"[{name}] L2内部分解: premise构造 "
              f"{r['nli_breakdown_ms']['premise'] / max(1, r['n']):.2f}ms/例, "
              f"模型推理 {r['nli_breakdown_ms']['model_infer'] / max(1, r['n']):.2f}ms/例 "
              f"(NLI调用{r['nli_calls']}次, claim判定{r['claim_verifies']}次)")

    out = {"tier": args.tier, "corpora": results}
    from tools.run_utils import open_run  # noqa: PLC0415
    run = open_run("profile_pipeline_stages", out)
    print(f"→ {run.path}")


if __name__ == "__main__":
    main()
