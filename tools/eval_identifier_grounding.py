"""R2验收评测: identifier接地概率化——judge注入 vs 不注入的三评测集对照.

任务来源: docs/srs_project/99_unified_action_plan.md Phase 3(R2)验收标准.

三评测集×两臂:
  crossdoc06   crossdoc06_evalset_v1.jsonl(sound标签)——C06QA-016/017
               ("ID在场但绑定错")逐例对照;
  91QA         scene1_qa_frozen_v1.jsonl(silver标签, 论文口径
               deterministic 0.7212/0.9121)——CLIPR约束: 逐实例
               零回退(正确→错误翻转数必须=0);
  violations   violation_evalset_v1.jsonl——refute检出16/17不降.

延迟: verify_identifier的judge增量(每claim毫秒级, CPU词法特征,
  零远程API/零模型加载)——对全量identifier support路径claim计时.

落盘: runs协议(open_run), result.json含逐实例/逐claim明细.

用法:
  python tools/eval_identifier_grounding.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE / "tools"), str(BASE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from run_utils import open_run  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from algorithms.consistency.answer_claims import decompose_claims  # noqa: E402
from algorithms.consistency.claim_channels import (  # noqa: E402
    default_rules,
    verify_identifier,
)
from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    classification_metrics,
    load_silver_labels,
    read_jsonl,
)
from algorithms.consistency.identifier_grounding import (  # noqa: E402
    IdentifierGroundingJudge,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_violations import load_rows, run_module  # noqa: E402

CROSSDOC06 = BASE / "data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl"
QA91 = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
VIOLATIONS = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"

#: 验收聚焦实例(crossdoc06 "ID在场但绑定错"与"效果性断言"两类)
FOCUS_INSTANCES: tuple[str, ...] = (
    "C06QA-016", "C06QA-017", "C06QA-026", "C06QA-029")


def build_judge() -> IdentifierGroundingJudge:
    """从规则资产(E7挂点: JSON第一真源/内置回退)构建校准器."""
    return IdentifierGroundingJudge.from_config(
        default_rules().identifier_grounding)


def eval_crossdoc(judge: IdentifierGroundingJudge | None) -> dict[str, Any]:
    rows = read_jsonl(CROSSDOC06)
    labels = {r["instance_id"]: r["sound_label"] for r in rows}
    module = QAConsistencyModule(use_experts=True,
                                 identifier_grounding=judge)
    y_true: list[str] = []
    y_pred: list[str] = []
    verdicts: dict[str, str] = {}
    claims: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        result = module.verify(build_qa_input(row))
        verdicts[row["instance_id"]] = result.verdict
        claims[row["instance_id"]] = [{
            "claim_text": c.claim_text[:80],
            "verdict": c.verdict,
            "method": c.method,
            "confidence": round(c.confidence, 4),
            "rationale": c.rationale[:160],
        } for c in result.claim_results]
        y_true.append(labels[row["instance_id"]])
        y_pred.append(result.verdict)
    metrics = classification_metrics(y_true, y_pred)
    return {"metrics": metrics, "verdicts": verdicts, "claims": claims,
            "wrong": [iid for iid, gold in labels.items()
                      if verdicts[iid] != gold]}


def eval_qa91(judge: IdentifierGroundingJudge | None) -> dict[str, Any]:
    rows = read_jsonl(QA91)
    silver = load_silver_labels()
    module = QAConsistencyModule(use_experts=True,
                                 identifier_grounding=judge)
    y_true: list[str] = []
    y_pred: list[str] = []
    verdicts: dict[str, str] = {}
    for row in rows:
        result = module.verify(build_qa_input(row))
        verdicts[row["instance_id"]] = result.verdict
        y_true.append(silver[row["instance_id"]])
        y_pred.append(result.verdict)
    metrics = classification_metrics(y_true, y_pred)
    return {"metrics": metrics, "verdicts": verdicts,
            "wrong": [iid for iid, gold in silver.items()
                      if verdicts[iid] != gold]}


def eval_violations(judge: IdentifierGroundingJudge | None) -> dict[str, Any]:
    module = QAConsistencyModule(use_experts=True,
                                 identifier_grounding=judge)
    outcomes = run_module(module, load_rows())
    detected = sum(1 for v in outcomes.values() if v["verdict"] == "refute")
    return {"refute_detected": detected, "total": len(outcomes),
            "verdicts": {iid: v["verdict"] for iid, v in outcomes.items()}}


def measure_latency() -> dict[str, float]:
    """judge增量: 对全量identifier support路径claim计时(每claim毫秒)."""
    judge = build_judge()
    cases = 0
    total_seconds = 0.0
    for path in (CROSSDOC06, QA91):
        for row in read_jsonl(path):
            request = build_qa_input(row)
            for index, claim in enumerate(
                    decompose_claims(request.question, request.answer), 1):
                if claim.kind != "identifier":
                    continue
                if claim.text not in "".join(
                        ev.text for ev in request.evidence):
                    continue  # 非support路径, judge不可及
                cases += 1
                start = time.perf_counter()
                verify_identifier(request, claim, index, (), grounding=judge)
                total_seconds += time.perf_counter() - start
    return {"n_identifier_support_claims": cases,
            "total_seconds": round(total_seconds, 4),
            "ms_per_claim": round(1000.0 * total_seconds / cases, 3)
            if cases else 0.0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-latency", action="store_true")
    args = parser.parse_args()
    judge = build_judge()
    print(f"judge: threshold={judge.threshold} "
          f"w=({judge.subject_bind_weight}, {judge.predicate_hit_weight}, "
          f"{judge.id_block_weight}, {judge.proximity_weight}) "
          f"b={judge.intercept}")

    print("\n[arm1] baseline(judge不注入, R2前行为)")
    base06 = eval_crossdoc(None)
    base91 = eval_qa91(None)
    basevio = eval_violations(None)
    print(f"  crossdoc06: acc={base06['metrics']['accuracy']:.4f} "
          f"macroF1={base06['metrics']['macro_f1']:.4f} "
          f"wrong={len(base06['wrong'])}")
    print(f"  91QA:       acc={base91['metrics']['accuracy']:.4f} "
          f"macroF1={base91['metrics']['macro_f1']:.4f} "
          f"wrong={len(base91['wrong'])}")
    print(f"  violations: refute {basevio['refute_detected']}"
          f"/{basevio['total']}")

    print("\n[arm2] judge注入(接地概率化)")
    judge06 = eval_crossdoc(judge)
    judge91 = eval_qa91(judge)
    judgevio = eval_violations(judge)
    print(f"  crossdoc06: acc={judge06['metrics']['accuracy']:.4f} "
          f"macroF1={judge06['metrics']['macro_f1']:.4f} "
          f"wrong={len(judge06['wrong'])}")
    print(f"  91QA:       acc={judge91['metrics']['accuracy']:.4f} "
          f"macroF1={judge91['metrics']['macro_f1']:.4f} "
          f"wrong={len(judge91['wrong'])}")
    print(f"  violations: refute {judgevio['refute_detected']}"
          f"/{judgevio['total']}")

    # ── CLIPR闸门: 91QA逐实例零回退 ────────────────────────────────
    regressions = [iid for iid in base91["verdicts"]
                   if iid in judge91["verdicts"]
                   and (base91["verdicts"][iid]
                        == load_silver_labels()[iid]
                        != judge91["verdicts"][iid])]
    improvements = [iid for iid in base91["verdicts"]
                    if iid in judge91["verdicts"]
                    and (base91["verdicts"][iid]
                         != load_silver_labels()[iid]
                         == judge91["verdicts"][iid])]
    print(f"\n[CLIPR] 91QA 正确→错误翻转: {regressions or '无(零回退✓)'}"
          f" | 错误→正确: {improvements or '无'}")

    # ── C06QA-016/017/026/029逐例对照 ──────────────────────────────
    print("\n[焦点实例] crossdoc06 (base → judge)")
    for iid in FOCUS_INSTANCES:
        print(f"  {iid}: {base06['verdicts'].get(iid)} → "
              f"{judge06['verdicts'].get(iid)}")
        for claim in judge06["claims"].get(iid, []):
            print(f"    {claim['verdict']:<18} {claim['method']:<26}"
                  f" conf={claim['confidence']:<8}"
                  f" {claim['claim_text'][:44]}")

    flipped = [iid for iid in base06["verdicts"]
               if base06["verdicts"][iid] != judge06["verdicts"][iid]]
    print(f"\n  crossdoc06实例级变化: {flipped or '无'}")

    latency: dict[str, float] = {}
    if not args.skip_latency:
        latency = measure_latency()
        print(f"\n[延迟] identifier support路径claim {latency['n_identifier_support_claims']}个, "
              f"judge增量 {latency['ms_per_claim']}ms/claim "
              f"(总 {latency['total_seconds']}s, CPU词法, 零API)")

    run = open_run("eval_identifier_grounding", {
        "judge": {
            "threshold": judge.threshold,
            "subject_bind_weight": judge.subject_bind_weight,
            "predicate_hit_weight": judge.predicate_hit_weight,
            "id_block_weight": judge.id_block_weight,
            "proximity_weight": judge.proximity_weight,
            "intercept": judge.intercept,
        },
        "evalsets": ["crossdoc06", "91QA", "violations-17"],
    })
    run.save_result({
        "baseline": {
            "crossdoc06": base06["metrics"],
            "qa91": base91["metrics"],
            "violations_refute": basevio["refute_detected"],
        },
        "judge": {
            "crossdoc06": judge06["metrics"],
            "qa91": judge91["metrics"],
            "violations_refute": judgevio["refute_detected"],
        },
        "clipr_regressions_91qa": regressions,
        "clipr_improvements_91qa": improvements,
        "crossdoc06_flipped": flipped,
        "crossdoc06_verdicts_base": base06["verdicts"],
        "crossdoc06_verdicts_judge": judge06["verdicts"],
        "focus_claims": {iid: judge06["claims"].get(iid, [])
                         for iid in FOCUS_INSTANCES},
        "latency": latency,
    })
    print(f"\n[写入] {run.path}")


if __name__ == "__main__":
    main()
