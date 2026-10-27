r"""mutation_injection_evalset_v1 漏检率矩阵评测(设计§6.5 robustness).

评测对象: data/gjb_438c/mutation_injection_evalset_v1.jsonl
注入实例的answer已被算子库受控变异(strict证明门或adaptive受控扰动,
变异破坏answer对冻结evidence的grounding), 期望verdict=refute;
系统判support/NIE均计为漏检.

被测系统: QAConsistencyModule(use_experts=True)——纯确定性符号层
(L0/L1专家+逐claim通道), 零LLM调用(变异注入测符号层能力, 不跑L2/L3).

指标:
  检出率        verdict==refute比例(总体/算子族/算子级全表)
  检出通道归因   裁决refute的claim method → channel(entity/e1/sequence/
                trace/gjb/id_join/enum_join/per_claim)
  漏检形态      误support(通道给了支持) vs NIE(证据缺失/无法判定)
  漏检抽样      K个漏检实例的人工可读原因(哪个通道给了误support/NIE)
交叉引用: 17真实违例(violation_evalset_v1)同配置逐类别检出率
          vs 对应注入算子检出率(identifier注入↔VIO-01..05等)
诊断: 检出率最差的3个算子族 → 能力缺口声明(future work素材)

落盘: runs协议(result.json含算子级全表+族级矩阵+漏检抽样+交叉引用).

用法:
  python tools/eval_mutation_detection.py [--limit N] [--k-sample 10]
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Protocol

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import (  # noqa: E402
    QAInput,
    VerificationResult,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.build_mutation_injection_eval import (  # noqa: E402
    FAMILIES,
    OPERATORS,
)
from tools.eval_violations import channel_of, read_jsonl  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/mutation_injection_evalset_v1.jsonl"
VIOLATION_EVALSET = (BASE / "data/gjb_438c/localization_gold"
                     / "violation_evalset_v1.jsonl")
VERDICTS = ("support", "refute", "not_in_evidence")

# 17真实违例类别 ↔ 注入算子(受控变异的同类不一致性)交叉引用
CROSS_REFERENCE_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("identifier", ("ANSWER-TERM-07-INTERFACE-CONFLICT-V1",)),
    ("enumeration", ("ANSWER-ENUM-EXPLICIT-CONFLICT-V1",
                     "ANSWER-STRUCT-CLOSED-LIST-REMOVE-V1",
                     "ANSWER-STRUCT-ACTOR-REMOVE-REFUTE-V2")),
    ("traceability", ("ANSWER-GJB-05-TRACE-CONFLICT-V1",)),
    ("exception_template", ("ANSWER-STRUCT-EXCEPTION-OUTCOME-SWAP-V1",
                            "ANSWER-LOGIC-02-EXCEPTION-SWAP-V1")),
    ("document_name", ("ANSWER-TERM-05-COMMAND-SWAP-V1",
                       "ANSWER-TERM-02-DEFINITION-SWAP-V1")),
    ("function_coverage", ("ANSWER-GJB-02-FT-EXCLUSION-V1",
                           "ANSWER-GJB-03-ACL-EXCLUSION-V1",
                           "ANSWER-GJB-04-AUDIT-EXCLUSION-V1",
                           "ANSWER-GJB-06-ALARM-EXCLUSION-V1",
                           "ANSWER-GJB-07-SELFTEST-EXCLUSION-V1",
                           "ANSWER-GJB-08-POWERLOSS-EXCLUSION-V1",
                           "ANSWER-GJB-09-INPUTGUARD-EXCLUSION-V1",
                           "ANSWER-GJB-11-DEGRADE-EXCLUSION-V1")),
    ("qualification_coverage", ("ANSWER-GJB-01-QUANTIFIER-FABRICATION-V1",)),
)

# 检出率最差家族的能力缺口声明(结合实测数字动态拼接, 供论文future work)
_GAP_DIAGNOSIS: dict[str, str] = {
    "BASE": ("数值/引用项变异依赖evidence侧显式数值约束或显式否定; "
             "冻结证据缺少数值声明时数值通道无从比对——数值证据缺失型漏检, "
             "需要参数约束抽取与跨块聚合前置(方向A上下文关联)。"),
    "STRUCT": ("步骤重排/删除仅被sequence_alignment与e1模板通道覆盖, "
               "枚举删元在开放scope下不可证伪——需要closed-scope证据或"
               "计数型枚举声明检测。"),
    "TERM": ("标识符变异检出依赖id_join的ID→主体join与标识符精确匹配; "
             "释义/状态变异缺少术语对齐通道——需要术语级语义比对"
             "(L2/L3残差通道)。"),
    "PARAM": ("参数族门控后的数值变异在无数值证据的上下文中全部漏检——"
              "参数约束证据缺失, 符号层数值通道需要evidence侧同subject"
              "数值声明才能比对。"),
    "LOGIC": ("异常处置动作的域外替换缺少语义级处置动作比对——确定性"
              "符号层只覆盖模板级e1/时序/优先级形状, 语义级动作冲突需要"
              "L2 NLI或L3 LLM残差通道。"),
    "GJB": ("域外术语注入需要封闭清单排除推理; 开放scope证据下封闭性"
            "不可假设(证明门正确地拒绝)——需要GJB规则侧closed-scope"
            "标注或封闭性前置判定。"),
}


def load_rows(path: Path = EVALSET) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    if not rows:
        raise ValueError(f"evalset为空: {path}")
    for row in rows:
        if row.get("expected_verdict") != "refute":
            raise ValueError(f"{row['instance_id']}: 注入实例期望verdict必须为refute")
    ids = [row["instance_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("instance_id存在重复")
    return rows


# ---------------------------------------------------------------- 评测内核
class Verifier(Protocol):
    """被测系统接口(结构化类型): QAConsistencyModule及其测试替身均满足."""

    def verify(self, request: QAInput) -> VerificationResult: ...


def run_module(module: Verifier,
               rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """逐注入实例跑被测系统, 产出检出/通道归因/漏检原因记录."""
    records: list[dict[str, Any]] = []
    for row in rows:
        request = request_from_dict(row)
        result = module.verify(request)
        refutes = [claim for claim in result.claim_results
                   if claim.verdict == "refute"]
        non_refutes = [claim for claim in result.claim_results
                       if claim.verdict != "refute"][:3]
        records.append({
            "instance_id": row["instance_id"],
            "source_instance_id": row.get("source_instance_id", ""),
            "operator_name": row.get("operator_name", ""),
            "operator_family": row.get("operator_family", ""),
            "check_item": row.get("check_item", ""),
            "mode": row.get("mode", ""),
            "question": row["question"],
            "expected_verdict": row.get("expected_verdict", ""),
            "predicted_verdict": result.verdict,
            "detected": result.verdict == "refute",
            "miss_kind": ("support" if result.verdict == "support"
                          else "nie" if result.verdict == "not_in_evidence"
                          else ""),
            "refute_methods": sorted({claim.method for claim in refutes}),
            "refute_channels": sorted({channel_of(claim.method)
                                       for claim in refutes}),
            "miss_claims": [{
                "claim_text": claim.claim_text[:100],
                "verdict": claim.verdict,
                "method": claim.method,
                "rationale": claim.rationale[:160],
            } for claim in non_refutes],
            "mutation_rationale": row.get("mutation_rationale", ""),
        })
    return records


def _rate(detected: int, total: int) -> float:
    return round(detected / total, 4) if total else 0.0


def family_matrix(records: list[dict[str, Any]]) -> dict[str, Any]:
    """漏检率矩阵(论文表): 算子族×{注入数, 检出数, 检出率, 主检出通道,
    漏检形态, 漏检代表算子}."""
    matrix: dict[str, Any] = {}
    for family in FAMILIES:
        fam = [r for r in records if r["operator_family"] == family]
        detected = [r for r in fam if r["detected"]]
        channels: Counter[str] = Counter(
            ch for r in detected for ch in r["refute_channels"])
        main_channel = (f"{channels.most_common(1)[0][0]}"
                        if channels else "")
        by_op: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in fam:
            by_op[r["operator_name"]].append(r)
        worst_ops = sorted(
            ({"operator": name, "n": len(recs),
              "detected": sum(1 for r in recs if r["detected"]),
              "rate": _rate(sum(1 for r in recs if r["detected"]), len(recs))}
             for name, recs in by_op.items()),
            key=lambda x: (x["rate"], -x["n"]))[:3]
        miss_kinds = Counter(r["miss_kind"] for r in fam if not r["detected"])
        matrix[family] = {
            "n_injected": len(fam),
            "n_detected": len(detected),
            "detection_rate": _rate(len(detected), len(fam)),
            "miss_rate": round(1 - _rate(len(detected), len(fam)), 4),
            "main_detection_channel": main_channel,
            "detection_channels": dict(channels),
            "miss_kind_counts": dict(miss_kinds),
            "worst_operators": worst_ops,
            "example_miss_ids": [r["instance_id"] for r in fam
                                 if not r["detected"]][:3],
        }
    detected_total = sum(1 for r in records if r["detected"])
    matrix["OVERALL"] = {
        "n_injected": len(records),
        "n_detected": detected_total,
        "detection_rate": _rate(detected_total, len(records)),
        "miss_rate": round(1 - _rate(detected_total, len(records)), 4),
        "miss_kind_counts": dict(
            Counter(r["miss_kind"] for r in records if not r["detected"])),
    }
    return matrix


def operator_table(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """算子级检出率全表(注册表全部算子, 含0注入行与support对照行)."""
    by_op: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_op[r["operator_name"]].append(r)
    table: list[dict[str, Any]] = []
    for op in OPERATORS:
        recs = by_op.get(op.operator_id, [])
        detected = sum(1 for r in recs if r["detected"])
        entry = {
            "operator": op.operator_id,
            "family": op.family,
            "check_item": op.check_item,
            "refute_semantics": op.refute_semantics,
            "n_injected": len(recs),
            "n_detected": detected,
            "detection_rate": _rate(detected, len(recs)),
            "modes": dict(Counter(r["mode"] for r in recs)),
        }
        if recs:
            entry["refute_methods"] = sorted({
                m for r in recs for m in r["refute_methods"]})
        table.append(entry)
    return table


def sample_misses(records: list[dict[str, Any]], *, k: int = 10,
                  seed: int = 42) -> list[dict[str, Any]]:
    """漏检实例抽样(每种漏检形态至少1个 + 族间轮转, seed=42确定性)."""
    missed_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        if not r["detected"]:
            missed_by_family[r["operator_family"]].append(r)
    order = sorted(missed_by_family, key=lambda f: -len(missed_by_family[f]))
    rng = random.Random(seed)
    pools = {f: list(missed_by_family[f]) for f in order}
    for f in order:
        rng.shuffle(pools[f])
    picked: list[dict[str, Any]] = []
    # 每种漏检形态(support/NIE)至少1个样本, 优先纳入稀有的误support
    for kind in ("support", "nie"):
        if len(picked) >= k:
            break
        for f in order:
            rare = next((r for r in pools[f] if r["miss_kind"] == kind), None)
            if rare is not None:
                pools[f].remove(rare)
                picked.append(rare)
                break
    while len(picked) < k and any(pools.values()):
        for f in order:
            if pools[f] and len(picked) < k:
                picked.append(pools[f].pop())
    explanations = []
    for rec in picked:
        claims = rec["miss_claims"]
        if rec["predicted_verdict"] == "support":
            kind = "误support: 通道对变异后answer仍给出支持"
        else:
            kind = "NIE漏检: 声明未被冻结evidence判定, 系统保守返回not_in_evidence"
        explanations.append({
            "instance_id": rec["instance_id"],
            "source_instance_id": rec["source_instance_id"],
            "operator": rec["operator_name"],
            "family": rec["operator_family"],
            "question": rec["question"][:120],
            "miss_kind": kind,
            "deciding_claims": claims,
            "mutation_rationale": rec["mutation_rationale"][:200],
        })
    return explanations


def miss_reason_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """漏检形态统计: 按聚合verdict区分误support致因与NIE致因方法."""
    missed = [r for r in records if not r["detected"]]
    kinds = Counter(r["miss_kind"] for r in missed)
    support_methods: Counter[str] = Counter()
    nie_methods: Counter[str] = Counter()
    for r in missed:
        bucket = (support_methods if r["predicted_verdict"] == "support"
                  else nie_methods)
        for claim in r["miss_claims"]:
            if claim["verdict"] == r["predicted_verdict"]:
                bucket[claim["method"]] += 1
    return {
        "n_missed": len(missed),
        "miss_kinds": dict(kinds),
        "false_support_causing_methods": dict(support_methods.most_common(8)),
        "nie_causing_methods": dict(nie_methods.most_common(8)),
    }


def cross_reference(module: Verifier,
                    records: list[dict[str, Any]]) -> dict[str, Any]:
    """17真实违例同配置检出率 vs 对应注入算子检出率(交叉引用表)."""
    vio_rows = read_jsonl(VIOLATION_EVALSET)
    vio_records = run_module(module, vio_rows)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row, rec in zip(vio_rows, vio_records):
        by_category[row["violation_category"]].append(rec)
    op_detected: Counter[str] = Counter()
    op_total: Counter[str] = Counter()
    for r in records:
        op_total[r["operator_name"]] += 1
        if r["detected"]:
            op_detected[r["operator_name"]] += 1
    rows_out: list[dict[str, Any]] = []
    for category, ops in CROSS_REFERENCE_MAP:
        group = by_category.get(category, [])
        real_detected = sum(1 for r in group if r["detected"])
        inj_n = sum(op_total.get(op, 0) for op in ops)
        inj_d = sum(op_detected.get(op, 0) for op in ops)
        real_channels = sorted({ch for r in group if r["detected"]
                                for ch in r["refute_channels"]})
        rows_out.append({
            "violation_category": category,
            "vio_ids": [r["instance_id"] for r in group],
            "n_real": len(group),
            "real_detected": real_detected,
            "real_detection_rate": _rate(real_detected, len(group)),
            "real_detection_channels": real_channels,
            "injection_operators": list(ops),
            "injection_n": inj_n,
            "injection_detected": inj_d,
            "injection_detection_rate": _rate(inj_d, inj_n) if inj_n else None,
            "injection_applicable": inj_n > 0,
        })
    real_total = len(vio_records)
    real_hits = sum(1 for r in vio_records if r["detected"])
    return {
        "note": ("真实违例=real_observed(04号文档人工深读17条); 注入=受控变异"
                 "同类不一致性; 两列检出率对照反映'合成变异可检出性'与"
                 "'真实缺陷可检出性'的分布差异。"),
        "real_total": real_total,
        "real_detected": real_hits,
        "real_detection_rate": _rate(real_hits, real_total),
        "rows": rows_out,
    }


def capability_gaps(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    """检出率最差的3个算子族(n>=5) → 能力缺口声明(论文future work素材)."""
    ranked = sorted(
        ({"family": fam, **matrix[fam]} for fam in FAMILIES
         if matrix[fam]["n_injected"] >= 5),
        key=lambda x: x["detection_rate"])
    gaps = []
    for entry in ranked[:3]:
        gaps.append({
            "family": entry["family"],
            "n_injected": entry["n_injected"],
            "detection_rate": entry["detection_rate"],
            "miss_kind_counts": entry.get("miss_kind_counts", {}),
            "gap_statement": (
                f"{entry['family']}家族注入{entry['n_injected']}条, 检出率仅"
                f"{entry['detection_rate']}; "
                + _GAP_DIAGNOSIS[entry["family"]]),
        })
    return gaps


# ---------------------------------------------------------------- 主流程
def print_family_matrix(matrix: dict[str, Any]) -> None:
    print("\n| 算子族 | 注入数 | 检出数 | 检出率 | 主检出通道 | 漏检代表算子 |")
    print("|--------|--------|--------|--------|------------|--------------|")
    for family in FAMILIES:
        m = matrix[family]
        worst = ", ".join(
            f"{w['operator']}({w['detected']}/{w['n']})"
            for w in m["worst_operators"]) or "-"
        print(f"| {family} | {m['n_injected']} | {m['n_detected']} | "
              f"{m['detection_rate']} | {m['main_detection_channel'] or '-'} "
              f"| {worst} |")
    overall = matrix["OVERALL"]
    print(f"\nOVERALL: 注入{overall['n_injected']}条, "
          f"检出{overall['n_detected']}条"
          f"(检出率{overall['detection_rate']}, "
          f"漏检形态{overall['miss_kind_counts']})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evalset", default=str(EVALSET))
    parser.add_argument("--limit", type=int, default=0,
                        help="只跑前N条(冒烟测试用)")
    parser.add_argument("--k-sample", type=int, default=10,
                        help="漏检抽样实例数")
    parser.add_argument("--skip-cross", action="store_true",
                        help="跳过17真实违例交叉引用(测试环境无该数据集时)")
    args = parser.parse_args()
    rows = load_rows(Path(args.evalset).resolve())
    if args.limit:
        rows = rows[:args.limit]
    module = QAConsistencyModule(use_experts=True)
    records = run_module(module, rows)
    matrix = family_matrix(records)
    ops_table = operator_table(records)
    misses = sample_misses(records, k=args.k_sample)
    reasons = miss_reason_stats(records)
    cross = (cross_reference(module, records) if not args.skip_cross else None)
    gaps = capability_gaps(matrix)

    run = open_run("eval_mutation_detection", {
        "evalset": str(Path(args.evalset).resolve().relative_to(BASE)),
        "n": len(rows),
        "k_sample": args.k_sample,
        "module": {"use_experts": True, "residual_channels": "off"},
        "pure_deterministic": True,
        "skip_cross": bool(args.skip_cross),
    })
    run.save_result({
        "evalset": str(Path(args.evalset).resolve().relative_to(BASE)),
        "protocol": (
            "注入实例answer已受控变异(变异破坏answer对冻结evidence的"
            "grounding), 期望verdict=refute; verdict==refute计检出, "
            "support/NIE计漏检; 被测系统为纯确定性符号层"
            "(QAConsistencyModule use_experts=True, 零LLM调用)。"),
        "family_matrix": matrix,
        "operator_table": ops_table,
        "miss_reason_stats": reasons,
        "miss_samples": misses,
        "violation_cross_reference": cross,
        "capability_gaps": gaps,
        "records": records,
    })
    print_family_matrix(matrix)
    if reasons["miss_kinds"]:
        print(f"\n漏检原因统计: {reasons['miss_kinds']}; "
              f"NIE致因方法: {reasons['nie_causing_methods']}; "
              f"误support致因方法: "
              f"{reasons['false_support_causing_methods']}")
    print("\n检出率最差的3个算子族(能力缺口):")
    for gap in gaps:
        print(f"  - {gap['family']}: 检出率{gap['detection_rate']}"
              f"({gap['n_injected']}条) → {gap['gap_statement'][:80]}...")
    if cross:
        print("\n与17真实违例的交叉引用:")
        for row in cross["rows"]:
            inj_rate = row["injection_detection_rate"]
            inj_rate_text = "-" if inj_rate is None else inj_rate
            print(f"  {row['violation_category']}: 真实"
                  f"{row['real_detected']}/{row['n_real']}"
                  f"(率{row['real_detection_rate']}) vs 注入"
                  f"{row['injection_detected']}/{row['injection_n']}"
                  f"(率{inj_rate_text})")
    print(f"\n漏检抽样({len(misses)}条)与全量明细见runs → {run.path}")


if __name__ == "__main__":
    main()
