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

#: 校验层命名(用户口径): 输入构造→L0 NER→L1规则→L2 NLI→融合聚合
#: 6a/6b是L2的子项(非独立层)
LAYERS = (
    "L0_NER层校验",
    "L1_规则层校验",
    "L2_NLI判定",
    "融合聚合",
)
STAGES = (
    "1_路由与claim分解",
    "2_证据线性化",
    "3_per-claim通道",
    "4_L0_NER",
    "5_L1_规则",
    "6_L2_NLI",
    "6a_NLI_premise构造",
    "6b_NLI_模型推理",
    "7_融合",
    "7_聚合",
)
LAYER_OF_STAGE = {
    "1_路由与claim分解": "输入构造",
    "2_证据线性化": "输入构造",
    "3_per-claim通道": "L1_规则层校验",
    "4_L0_NER": "L0_NER层校验",
    "5_L1_规则": "L1_规则层校验",
    "6_L2_NLI": "L2_NLI判定",
    "7_融合": "融合聚合",
    "7_聚合": "融合聚合",
}


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
    # 专家注册表按L0(NER)/L1(规则)分组计时: entity→L0, 其余→L1
    original_registry = qa_module._expert_registry

    def grouped_registry(use_bge: bool):
        specs = original_registry(use_bge)
        wrapped = []
        for spec in specs:
            layer = "4_L0_NER" if spec.name == "entity" else "5_L1_规则"
            wrapped.append(qa_module.ExpertSpec(
                name=spec.name,
                runner=timed(layer, spec.runner),
                takes_claims=spec.takes_claims,
                takes_bge=spec.takes_bge))
        return tuple(wrapped)

    qa_module._expert_registry = grouped_registry
    nli_residual.verify_residual_claims_nli = timed(
        "6_L2_NLI", nli_residual.verify_residual_claims_nli)
    nli_residual.residual_premise = timed(
        "6a_NLI_premise构造", nli_residual.residual_premise)
    nli_residual._infer = timed("6b_NLI_模型推理", nli_residual._infer)
    # _fuse_per_claim是staticmethod: 包装后须以staticmethod挂回类,
    # 否则实例访问会把self绑定为首参
    QAConsistencyModule._fuse_per_claim = staticmethod(timed(
        "7_融合", QAConsistencyModule._fuse_per_claim))
    QAConsistencyModule._aggregate = timed(
        "7_聚合", QAConsistencyModule._aggregate)


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
                + ms["3_per-claim通道"] + ms["4_L0_NER"]
                + ms["5_L1_规则"] + ms["6_L2_NLI"]
                + ms["7_融合"] + ms["7_聚合"])
    other_ms = max(0.0, total * 1000 - additive)
    layer_ms = {layer: sum(ms[stage] for stage in STAGES
                           if LAYER_OF_STAGE.get(stage) == layer)
                for layer in ("输入构造",) + LAYERS}
    layer_ms["其他开销"] = other_ms
    return {
        "n": len(records),
        "total_s": round(total, 2),
        "mean_ms_per_instance": round(total / len(records) * 1000, 1),
        "median_ms": round(statistics.median(per_instance) * 1000, 1),
        "p95_ms": round(sorted(per_instance)[
            min(int(len(per_instance) * 0.95), len(per_instance) - 1)] * 1000, 1),
        "layer_total_ms": {k: round(v, 1) for k, v in layer_ms.items()},
        "layer_mean_ms": {k: round(v / len(records), 2)
                          for k, v in layer_ms.items()},
        "stage_total_ms": {k: round(v, 1) for k, v in ms.items()},
        "stage_mean_ms": {k: round(v / len(records), 2) for k, v in ms.items()},
        "nli_breakdown_ms": {
            "premise": round(ms["6a_NLI_premise构造"], 1),
            "model_infer": round(ms["6b_NLI_模型推理"], 1),
        },
        "nli_calls": COUNTS.get("6_L2_NLI", 0),
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

    # ── markdown table: layer × corpus (mean ms/instance + total) ──
    layer_keys = ["输入构造", *LAYERS, "其他开销"]
    names = list(corpora)
    header = ("| 层 | " + " | ".join(
        f"{n} (ms/例)" for n in names)
        + " | " + " | ".join(f"{n} 整集(s)" for n in names) + " | 占比* |")
    sep = "|------|" + "---|" * (len(names) * 2 + 1)
    print("\n" + header)
    print(sep)
    for layer in layer_keys:
        cells = [f"{results[n]['layer_mean_ms'][layer]:.2f}"
                 for n in names]
        totals = [f"{results[n]['layer_total_ms'][layer] / 1000:.2f}"
                  for n in names]
        share = (results['qa91']['layer_total_ms'][layer]
                 / max(1e-9, sum(results['qa91']['layer_total_ms'].values()))
                 * 100)
        print(f"| {layer} | " + " | ".join(cells) + " | "
              + " | ".join(totals) + f" | {share:.1f}% |")
    row_total = [f"**{results[n]['mean_ms_per_instance']:.1f}**"
                 for n in names]
    row_seconds = [f"**{results[n]['total_s']:.2f}**" for n in names]
    print("| **总计/例** | " + " | ".join(row_total) + " | "
          + " | ".join(row_seconds) + " | 100% |")
    print("*占比按qa91列计算\n")

    # 子阶段明细(层内部构成)
    stage_keys = ["1_路由与claim分解", "2_证据线性化", "3_per-claim通道",
                  "4_L0_NER", "5_L1_规则", "6_L2_NLI", "7_融合", "7_聚合"]
    print("子阶段明细(ms/例):")
    for stage in stage_keys:
        cells = [f"{results[n]['stage_mean_ms'][stage]:.2f}"
                 for n in names]
        print(f"  {stage:16s} " + " | ".join(cells))

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
