r"""17真实文档违例的端到端评测(设计§6.5 refute专项, real_observed).

评测对象: data/gjb_438c/localization_gold/violation_evalset_v1.jsonl
(17条真实违例转化的QA实例, 期望verdict全部为refute——区别于合成变异的
真实缺陷检测能力证据).

两配置:
  deterministic  QAConsistencyModule(use_experts=True)
                 ——L0/L1专家族的裸检测能力, 0次LLM调用
  cascade        use_experts=True + use_nli_residual=True
                 (nli_model_path=MODELS[egt_finetuned_v2]) + use_cascade=True
                 ——级联全系统(L2本地NLI残差 + L3 LLM升级, LLM调用经
                 llm_json cache=True内建通道)

指标:
  违例检出率     期望refute实例中判出refute的比例(总体/违例类别/
                 answer_pattern分组)
  目标命中检出   refute且任一refute claim的理由/文本命中该实例的
                 target_keywords——区分"检出目标违例本身"与"检出共享
                 证据中的兄弟违例"(表81/82三兄弟共用证据的诚实性守卫)
  假阳性         期望非refute实例被判refute(本集17条全期望refute,
                 该指标结构性为0, 报告中显式说明)
  定位命中       系统evidence_refs(块级, 去除#sN语句后缀)与模板预填
                 gold定位refs的交集: 实例级命中率 + 总体P/R
  检出通道       裁决refute的claim method→通道归因(entity/e1/sequence/
                  trace/gjb/id_join/nli/llm/per-claim)

落盘: runs协议(open_run), result.json含逐实例明细.

用法:
  python tools/eval_violations.py [--limit N] [--skip-cascade]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.nli_local import MODELS  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

EVALSET = (BASE / "data/gjb_438c/localization_gold"
           / "violation_evalset_v1.jsonl")
LABELS = ("support", "refute", "not_in_evidence")
DEFAULT_MODEL_KEY = "egt_finetuned_v2"

_CHANNEL_BY_METHOD = (
    ("l0_entity_detector", "entity_L0"),
    ("e1_template_match", "e1_L1"),
    ("sequence_alignment", "sequence_L1"),
    ("trace_bidirectional_join", "trace_L1"),
    ("gjb_presence_check", "gjb_L1"),
    ("gjb_rule_engine", "gjb_L1"),
    ("id_join_registry", "id_join_L1"),
    ("enum_join_registry", "enum_join_L1"),
    ("coverage_join", "coverage_L1"),
    ("nli_residual", "nli_L2"),
    ("llm_residual", "llm_L3"),
)


def channel_of(method: str) -> str:
    for prefix, channel in _CHANNEL_BY_METHOD:
        if method.startswith(prefix):
            return channel
    return "per_claim"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_rows(path: Path = EVALSET) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    if len(rows) != 17:
        raise ValueError(f"违例评测集应17条, 实际{len(rows)}")
    return rows


def run_module(module: QAConsistencyModule,
               rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """跑一个配置, 返回instance_id → 结果明细(verdict/claims/refs)."""
    outcomes: dict[str, dict[str, Any]] = {}
    for row in rows:
        request = request_from_dict(row)
        result = module.verify(request)
        refutes = [claim for claim in result.claim_results
                   if claim.verdict == "refute"]
        outcomes[request.instance_id] = {
            "verdict": result.verdict,
            "status": result.status,
            "refute_methods": sorted({claim.method for claim in refutes}),
            "refute_channels": sorted({channel_of(claim.method)
                                       for claim in refutes}),
            "evidence_refs": sorted({ref for claim in result.claim_results
                                     for ref in claim.evidence_refs}),
            "refute_rationales": [claim.rationale[:200] for claim in refutes],
            "claims": [{
                "claim_text": claim.claim_text[:120],
                "verdict": claim.verdict,
                "method": claim.method,
                "evidence_refs": list(claim.evidence_refs),
                "rationale": claim.rationale[:200],
            } for claim in result.claim_results],
        }
    return outcomes


def _block_ref(ref: str) -> str:
    """语句级ref('ev-000222#s7') → 块级ref('ev-000222')."""
    return ref.split("#", 1)[0]


def instance_metrics(row: dict[str, Any],
                     outcome: dict[str, Any]) -> dict[str, Any]:
    """单实例: 检出/目标命中/定位明细."""
    expected = row["expected_verdict"]
    predicted = outcome["verdict"]
    detected = predicted == "refute"
    gold_refs = set(row["gold_evidence_refs"])
    # 定位基准=裁决refute的claim所引用的块(决策依据块), 非全部被引用块:
    # support引用命中gold不能作为"违例定位正确"的证据
    refute_blocks = set()
    for claim in outcome["claims"]:
        if claim["verdict"] != "refute":
            continue
        refute_blocks.update(_block_ref(ref) for ref in claim["evidence_refs"]
                             if ref)
    gold_hit = gold_refs & refute_blocks if detected else set()
    # 目标命中只在refute理由(rationale)上匹配: claim文本常为answer本身,
    # 会平凡命中关键词, 不能作为"检出目标违例"的证据.
    keywords = row.get("target_keywords", [])
    refute_text = " ".join(outcome["refute_rationales"])
    target_hit = detected and any(keyword in refute_text
                                  for keyword in keywords)
    return {
        "instance_id": row["instance_id"],
        "category": row["violation_category"],
        "answer_pattern": row["answer_pattern"],
        "expected": expected,
        "predicted": predicted,
        "detected": detected,
        "false_positive": predicted == "refute" and expected != "refute",
        "target_hit": bool(target_hit),
        "refute_channels": outcome["refute_channels"],
        "refute_methods": outcome["refute_methods"],
        "gold_refs": sorted(gold_refs),
        "refute_block_refs": sorted(refute_blocks),
        "gold_hit_refs": sorted(gold_hit),
        "localization_recall": (round(len(gold_hit) / len(gold_refs), 4)
                                if gold_refs else None),
        "rationale_for_expectation": row["rationale_for_expectation"],
    }


def score_outcomes(outcomes: dict[str, dict[str, Any]],
                   rows: list[dict[str, Any]]) -> dict[str, Any]:
    """聚合指标: 检出率(分组)/假阳性/定位P/R/通道分布/逐实例明细."""
    details = [instance_metrics(row, outcomes[row["instance_id"]])
               for row in rows]
    expected_refute = [d for d in details if d["expected"] == "refute"]
    detected = [d for d in expected_refute if d["detected"]]
    targeted = [d for d in detected if d["target_hit"]]

    def rate(sub: list[dict[str, Any]], whole: list[dict[str, Any]]) -> float:
        return round(len(sub) / len(whole), 4) if whole else 0.0

    by_category: dict[str, dict[str, Any]] = {}
    for category in sorted({d["category"] for d in details}):
        group = [d for d in details if d["category"] == category]
        by_category[category] = {
            "n": len(group),
            "detected": sum(1 for d in group if d["detected"]),
            "target_hit": sum(1 for d in group if d["target_hit"]),
            "detection_rate": rate([d for d in group if d["detected"]], group),
            "ids": [d["instance_id"] for d in group],
        }
    by_pattern: dict[str, dict[str, Any]] = {}
    for pattern in sorted({d["answer_pattern"] for d in details}):
        group = [d for d in details if d["answer_pattern"] == pattern]
        by_pattern[pattern] = {
            "n": len(group),
            "detected": sum(1 for d in group if d["detected"]),
            "detection_rate": rate([d for d in group if d["detected"]], group),
        }
    gold_total = sum(len(d["gold_refs"]) for d in details if d["detected"])
    gold_hit_total = sum(len(d["gold_hit_refs"]) for d in details)
    refute_block_total = sum(len(d["refute_block_refs"]) for d in details
                             if d["detected"])
    channels: Counter[str] = Counter()
    for d in detected:
        channels.update(d["refute_channels"])
    confusion: Counter[str] = Counter()
    for d in details:
        confusion[f"{d['predicted']}|{d['expected']}"] += 1
    return {
        "n": len(details),
        "n_expected_refute": len(expected_refute),
        "n_detected": len(detected),
        "detection_rate": rate(detected, expected_refute),
        "targeted_detection_rate": rate(targeted, expected_refute),
        "false_positives": sum(1 for d in details if d["false_positive"]),
        "false_positive_note": (
            "本评测集17条全部期望refute(answer断言违例内容或其正确版本的"
            "被反驳形态), 期望非refute实例数为0, 假阳性结构性为0; 期望"
            "support/NIE上的假阳性在91条冻结QA主集上另行测量"),
        "by_category": by_category,
        "by_answer_pattern": by_pattern,
        "confusion[predicted|expected]": dict(confusion),
        "localization": {
            "gold_refs_total": gold_total,
            "gold_refs_hit": gold_hit_total,
            "refute_block_refs_total": refute_block_total,
            "precision": (round(gold_hit_total / refute_block_total, 4)
                          if refute_block_total else 0.0),
            "recall": (round(gold_hit_total / gold_total, 4)
                       if gold_total else 0.0),
            "instances_with_full_gold_hit": sum(
                1 for d in details
                if d["detected"] and d["gold_refs"]
                and set(d["gold_refs"]) <= set(d["gold_hit_refs"])),
        },
        "refute_channels": dict(channels),
        "detected_ids": [d["instance_id"] for d in detected],
        "targeted_ids": [d["instance_id"] for d in targeted],
        "undetected_ids": [d["instance_id"] for d in expected_refute
                           if not d["detected"]],
        "details": details,
    }


def build_configs(model_key: str) -> list[tuple[str, QAConsistencyModule]]:
    checkpoint = MODELS[model_key]["dir"]
    if not (Path(checkpoint) / "config.json").exists():
        raise SystemExit(
            f"NLI checkpoint不存在: {checkpoint} (先跑 train_residual_nli.py)")
    return [
        ("deterministic", QAConsistencyModule(use_experts=True)),
        ("cascade", QAConsistencyModule(
            use_experts=True, use_nli_residual=True,
            nli_model_path=checkpoint, use_cascade=True)),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="只跑前N条(冒烟测试用)")
    parser.add_argument("--model-key", default=DEFAULT_MODEL_KEY,
                        help="NLI checkpoint的MODELS注册key")
    parser.add_argument("--skip-cascade", action="store_true",
                        help="跳过级联配置(无GPU/无.env环境冒烟)")
    args = parser.parse_args()
    rows = load_rows()
    if args.limit:
        rows = rows[:args.limit]

    specs = ([("deterministic", QAConsistencyModule(use_experts=True))]
             if args.skip_cascade else build_configs(args.model_key))
    reports: dict[str, Any] = {}
    for name, module in specs:
        outcomes = run_module(module, rows)
        reports[name] = score_outcomes(outcomes, rows)
        score = reports[name]
        print(f"\n[{name}] n={score['n']} 检出={score['n_detected']}"
              f"/{score['n_expected_refute']}"
              f"(检出率{score['detection_rate']}, "
              f"目标命中{score['targeted_detection_rate']})")
        for category, stat in score["by_category"].items():
            print(f"  {category}: {stat['detected']}/{stat['n']}"
                  f"(目标命中{stat['target_hit']})")
        print(f"  定位P/R: {score['localization']['precision']}"
              f"/{score['localization']['recall']}")
        print(f"  检出通道: {score['refute_channels']}")
        print(f"  未检出: {score['undetected_ids']}")

    run = open_run("eval_violations", {
        "evalset": str(EVALSET.relative_to(BASE)),
        "n": len(rows),
        "model_key": args.model_key,
        "configs": [name for name, _ in specs],
        "deterministic": {"use_experts": True},
        "cascade": {"use_experts": True, "use_nli_residual": True,
                    "use_cascade": True,
                    "nli_model_path": MODELS[args.model_key]["dir"]},
        "limit": args.limit or None,
    })
    run.save_result({
        "evalset": str(EVALSET.relative_to(BASE)),
        "expected_verdict_note": (
            "17条真实违例转化实例, 期望verdict均为refute; 逐条理由见"
            "评测集rationale_for_expectation字段"),
        "configs": reports,
    })
    print(f"\nruns落盘 → {run.path}")


if __name__ == "__main__":
    main()
