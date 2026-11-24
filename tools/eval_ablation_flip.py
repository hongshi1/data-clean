r"""E2: 证据消融翻转率 + 反事实四条件上violations-17.

99号统一行动方案Phase 0-E2(设计依据96号§5 FAE/EviScope口径):
对每条violation, 把判定所引用的关键证据从输入中移除/替换, 证据依赖的
refute判定应翻转——测"判定是否真用证据"(FAE, arXiv 2609.08943:
LLM验证器常靠参数知识而非给定证据), 不需要任何新标注.

判定引擎(真实推理, 禁止模拟):
  QAConsistencyModule(use_experts=True)——集成裁决refute的确定性来源
  通道(L0/L1专家族, ~0.1s/例); 17条×(1原始+4变体)=85次verify.

关键证据定义: 原始运行中refute定位(localizations)引用的证据块
(系统自己的citations——FAE口径: 消融"系统引用的证据");
未检出实例(原始verdict≠refute)无citations可消融→(b)(d)记n/a.

表驱动扰动算子(4个, 17×4=68变体, EviScope quartet增/删/换/扰):
  remove_cited       移除系统引用的关键证据块(删)
  replace_cited      关键证据块原位替换为无关干扰块(换, 同文档其他实例)
  remove_irrelevant  移除无关块(既非cited也非gold), 保留关键+gold(消融无关)
  add_distractor     追加无关干扰块(增/干扰)

反事实四条件(96号§5口径, 逐实例):
  (a) 原判定保持: 无关扰动(remove_irrelevant+add_distractor)下verdict不变
  (b) 判定翻转:   remove_cited后refute→非refute(证据依赖的直接证据)
  (c) 定位稳定:   无关扰动下定位签名(引用块集+answer span集)不变
  (d) 定位跟随:   replace_cited后签名迁移或verdict翻转
                  子状态: flipped(翻转)/migrated(迁移, 换块仍refute——
                  干扰块诱发的伪refute, 稳健性弱点)/unchanged_fail

定位签名 = (refute localizations引用的块级id排序, answer_span排序);
比较跨变体同构(语句id {evidence_id}#s{N}基于evidence_id, 删其他块
不重编号; 扰动变体的新块携带新id, 命中即"迁移").

落盘: runs协议(tools/run_utils.py open_run), 逐实例四条件+逐算子
verdict/签名+汇总翻转率.

用法: $env:PYTHONUTF8='1'; python tools/eval_ablation_flip.py [--limit N]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"

#: 每实例预取的干扰块池大小(替换算子按cited块数消耗, 上限冗余)
DISTRACTOR_POOL_SIZE = 10
#: add_distractor算子追加的干扰块数(EviScope干扰条件, 固定预算可比较)
ADD_DISTRACTOR_BUDGET = 3

#: 扰动算子的方向语义(声明式; 汇总翻转率时标注"应翻转/应保持")
OPERATOR_EXPECTATION = {
    "remove_cited": "should_flip",
    "replace_cited": "should_flip",
    "remove_irrelevant": "should_keep",
    "add_distractor": "should_keep",
}


# ── 纯函数内核(测试覆盖) ─────────────────────────────────────────────────


def normalize_text(text: Any) -> str:
    """文本归一(去全部空白)——跨实例证据重叠判定用."""
    return re.sub(r"\s+", "", str(text))


def block_ref(ref: str) -> str:
    """语句级ref('ev-000222#s7') → 块级ref('ev-000222')."""
    return str(ref).split("#", 1)[0]


def cited_blocks(result: Any) -> set[str]:
    """refute localizations引用的块级id集合(系统citations=关键证据)."""
    return {block_ref(ev.statement_id)
            for loc in result.localizations for ev in loc.evidence}


def result_signature(result: Any) -> dict[str, Any]:
    """定位签名: (引用块集, answer span集)——跨变体定位稳定性比较单元."""
    blocks = sorted({block_ref(ev.statement_id)
                     for loc in result.localizations
                     for ev in loc.evidence})
    spans = sorted([list(loc.answer_span) for loc in result.localizations
                    if loc.answer_span is not None])
    return {"cited_blocks": blocks, "answer_spans": spans,
            "n_localizations": len(result.localizations)}


def distractor_pool(rows: list[dict[str, Any]], index: int,
                    pool_size: int = DISTRACTOR_POOL_SIZE
                    ) -> list[dict[str, Any]]:
    """确定性干扰块池: 同文档其他实例证据, 去文本重叠, 轮转取够.

    "无关"的构造性定义: 块文本不出现于当前实例任何证据(同doc04的其他
    实例证据, 域内风格同构但与当前question/answer无关).
    """
    own = [str(item["evidence_id"]) for item in rows[index]["evidence"]]
    seen_texts = {normalize_text(item["text"])
                  for item in rows[index]["evidence"]}
    seen_ids = set(own)
    pool: list[dict[str, Any]] = []
    for offset in range(1, len(rows)):
        source = rows[(index + offset) % len(rows)]
        for item in source["evidence"]:
            text = normalize_text(item["text"])
            evidence_id = str(item["evidence_id"])
            if text in seen_texts or evidence_id in seen_ids:
                continue
            seen_texts.add(text)
            seen_ids.add(evidence_id)
            pool.append(dict(item))
            if len(pool) >= pool_size:
                return pool
    return pool


# ── 表驱动扰动算子(声明式注册) ────────────────────────────────────────────


def op_remove_cited(row: dict[str, Any], cited: set[str],
                    pool: list[dict[str, Any]]
                    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """删: 移除系统引用的关键证据块(FAE核心消融)."""
    evidence = list(row["evidence"])
    kept = [item for item in evidence
            if str(item["evidence_id"]) not in cited]
    return kept, {
        "operator": "remove_cited",
        "n_before": len(evidence),
        "n_removed": len(evidence) - len(kept),
        "removed_ids": sorted(cited),
    }


def op_replace_cited(row: dict[str, Any], cited: set[str],
                     pool: list[dict[str, Any]]
                     ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """换: 关键证据块原位替换为无关干扰块(定位跟随检测)."""
    evidence = list(row["evidence"])
    new_evidence: list[dict[str, Any]] = []
    replaced: list[str] = []
    pool_pos = 0
    for item in evidence:
        if (str(item["evidence_id"]) in cited
                and pool_pos < len(pool)):
            new_evidence.append(pool[pool_pos])
            replaced.append(str(item["evidence_id"]))
            pool_pos += 1
        else:
            new_evidence.append(item)
    return new_evidence, {
        "operator": "replace_cited",
        "n_cited": len(cited),
        "n_replaced": len(replaced),
        "n_pool": len(pool),
        "replaced_ids": sorted(replaced),
        "pool_exhausted": len(replaced) < len(cited),
    }


def op_remove_irrelevant(row: dict[str, Any], cited: set[str],
                         pool: list[dict[str, Any]]
                         ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """消融无关: 移除既非cited也非gold的块(关键+gold全保留)."""
    evidence = list(row["evidence"])
    gold = {str(ref) for ref in row["gold_evidence_refs"]}
    keep = cited | gold
    kept = [item for item in evidence
            if str(item["evidence_id"]) in keep]
    return kept, {
        "operator": "remove_irrelevant",
        "n_before": len(evidence),
        "n_removed": len(evidence) - len(kept),
        "keep_ids": sorted(keep),
        "no_irrelevant_blocks": len(kept) == len(evidence),
    }


def op_add_distractor(row: dict[str, Any], cited: set[str],
                      pool: list[dict[str, Any]]
                      ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """增/干扰: 追加无关干扰块(无关扰动, 定位应稳定)."""
    evidence = list(row["evidence"])
    added = [dict(item) for item in pool[:ADD_DISTRACTOR_BUDGET]]
    return evidence + added, {
        "operator": "add_distractor",
        "n_before": len(evidence),
        "n_added": len(added),
        "added_ids": [str(item["evidence_id"]) for item in added],
    }


#: 扰动算子注册表(表驱动; 新算子=加一个函数+一行注册)
PERTURBATION_OPERATORS: dict[
    str, Callable[[dict[str, Any], set[str], list[dict[str, Any]]],
                  tuple[list[dict[str, Any]], dict[str, Any]]]] = {
    "remove_cited": op_remove_cited,
    "replace_cited": op_replace_cited,
    "remove_irrelevant": op_remove_irrelevant,
    "add_distractor": op_add_distractor,
}


# ── 四条件与汇总(纯函数, 测试覆盖) ───────────────────────────────────────


def four_conditions(original: dict[str, Any],
                    variants: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """反事实四条件(96号§5口径).

    original/variants元素: {"verdict": str, "signature": dict}.
    (b)(d)仅对原始refute实例有定义(未检出→None=n/a, 不进分母);
    (a)(c)对全部实例有定义(无关扰动不应改变任何原始判定/定位).
    """
    stable_ops = ("remove_irrelevant", "add_distractor")
    a = all(variants[op]["verdict"] == original["verdict"]
            for op in stable_ops)
    c = all(variants[op]["signature"] == original["signature"]
            for op in stable_ops)
    applicable = original["verdict"] == "refute"
    if not applicable:
        return {
            "a_verdict_stable_irrelevant": a,
            "b_key_removal_flips": None,
            "c_localization_stable_irrelevant": c,
            "d_localization_follows_replacement": None,
            "d_status": "n/a_undetected",
        }
    b = variants["remove_cited"]["verdict"] != "refute"
    replaced = variants["replace_cited"]
    if replaced["verdict"] != "refute":
        d, d_status = True, "flipped"
    elif replaced["signature"] != original["signature"]:
        d, d_status = True, "migrated"
    else:
        d, d_status = False, "unchanged_fail"
    return {
        "a_verdict_stable_irrelevant": a,
        "b_key_removal_flips": b,
        "c_localization_stable_irrelevant": c,
        "d_localization_follows_replacement": d,
        "d_status": d_status,
    }


def aggregate_conditions(details: list[dict[str, Any]]) -> dict[str, Any]:
    """逐算子翻转率 + 四条件达成数 + 类别分组."""
    detected = [d for d in details if d["original"]["verdict"] == "refute"]
    flip_rates: dict[str, dict[str, Any]] = {}
    for operator, expectation in OPERATOR_EXPECTATION.items():
        flipped = [d for d in details
                   if d["variants"][operator]["verdict"]
                   != d["original"]["verdict"]]
        if expectation == "should_flip":
            applicable = detected
            n_flip = sum(
                1 for d in applicable
                if d["variants"][operator]["verdict"] != "refute")
            denominator = len(applicable)
        else:
            applicable = details
            n_flip = len(flipped)
            denominator = len(details)
        flip_rates[operator] = {
            "expectation": expectation,
            "n_applicable": denominator,
            "n_verdict_changed": n_flip,
            "flip_rate": round(n_flip / denominator, 4) if denominator
            else None,
            "changed_ids": [d["instance_id"] for d in flipped],
        }
    condition_keys = ("a_verdict_stable_irrelevant", "b_key_removal_flips",
                      "c_localization_stable_irrelevant",
                      "d_localization_follows_replacement")
    conditions: dict[str, dict[str, Any]] = {}
    for key in condition_keys:
        values = [d["conditions"][key] for d in details
                  if d["conditions"][key] is not None]
        conditions[key] = {
            "n_satisfied": sum(int(bool(v)) for v in values),
            "n_applicable": len(values),
            "rate": round(sum(int(bool(v)) for v in values) / len(values), 4)
            if values else None,
        }
    d_statuses: dict[str, int] = {}
    for d in detected:
        d_statuses[d["conditions"]["d_status"]] = (
            d_statuses.get(d["conditions"]["d_status"], 0) + 1)
    by_category: dict[str, dict[str, Any]] = {}
    for category in sorted({d["violation_category"] for d in details}):
        group = [d for d in details
                 if d["violation_category"] == category]
        by_category[category] = {
            "n": len(group),
            "ids": [d["instance_id"] for d in group],
            **{key: f"{sum(int(bool(d['conditions'][key]))
                          for d in group
                          if d['conditions'][key] is not None)}"
                   f"/{sum(1 for d in group
                           if d['conditions'][key] is not None)}"
               for key in condition_keys},
            "b_fail_ids": [d["instance_id"] for d in group
                           if d["conditions"]["b_key_removal_flips"] is
                           False],
            "d_status_counts": {
                status: sum(1 for d in group
                            if d["conditions"]["d_status"] == status)
                for status in ("flipped", "migrated", "unchanged_fail")},
        }
    return {
        "n_instances": len(details),
        "n_detected": len(detected),
        "n_variants": len(details) * len(PERTURBATION_OPERATORS),
        "flip_rates": flip_rates,
        "four_conditions": conditions,
        "d_status_distribution": d_statuses,
        "by_category": by_category,
    }


# ── runner(真实推理) ──────────────────────────────────────────────────────


def run_ablation(rows: list[dict[str, Any]],
                 module: QAConsistencyModule) -> list[dict[str, Any]]:
    """逐实例: 原始verify + 4扰动变体verify(共5×17次真实推理)."""
    details: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        original_result = module.verify(build_qa_input(row))
        cited = cited_blocks(original_result)
        pool = distractor_pool(rows, index)
        variants: dict[str, dict[str, Any]] = {}
        for name, operator in PERTURBATION_OPERATORS.items():
            new_evidence, meta = operator(row, cited, pool)
            variant_row = dict(row, evidence=new_evidence)
            variant_result = module.verify(build_qa_input(variant_row))
            variants[name] = {
                "verdict": str(variant_result.verdict),
                "signature": result_signature(variant_result),
                "n_evidence": len(new_evidence),
                "meta": meta,
            }
        original = {
            "verdict": str(original_result.verdict),
            "signature": result_signature(original_result),
            "cited_blocks": sorted(cited),
            "n_evidence": len(row["evidence"]),
        }
        conditions = four_conditions(original, variants)
        details.append({
            "instance_id": str(row["instance_id"]),
            "violation_category": str(row["violation_category"]),
            "item_id": str(row["item_id"]),
            "expected_verdict": str(row["expected_verdict"]),
            "gold_evidence_refs": [str(r) for r in
                                   row["gold_evidence_refs"]],
            "original": original,
            "variants": variants,
            "conditions": conditions,
        })
        print(f"{row['instance_id']}: {original['verdict']:>17s} "
              f"cited={len(cited)} | "
              + " ".join(f"{name}→{variants[name]['verdict']}"
                         for name in PERTURBATION_OPERATORS)
              + f" | a={int(conditions['a_verdict_stable_irrelevant'])}"
              f" b={conditions['b_key_removal_flips']}"
              f" c={int(conditions['c_localization_stable_irrelevant'])}"
              f" d={conditions['d_localization_follows_replacement']}"
              f"({conditions['d_status']})")
    return details


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0,
                        help="只跑前N条(冒烟测试用)")
    args = parser.parse_args()

    rows = read_jsonl(EVALSET)
    if args.limit:
        rows = rows[:args.limit]

    module = QAConsistencyModule(use_experts=True)
    started = time.time()
    details = run_ablation(rows, module)
    summary = aggregate_conditions(details)

    for operator, stat in summary["flip_rates"].items():
        print(f"\n[{operator}] expectation={stat['expectation']} "
              f"翻转={stat['n_verdict_changed']}/{stat['n_applicable']}"
              f"({stat['flip_rate']})")
    for key, stat in summary["four_conditions"].items():
        print(f"[{key}] 达成={stat['n_satisfied']}/{stat['n_applicable']}"
              f"({stat['rate']})")
    print(f"[d子状态] {summary['d_status_distribution']}")

    report = {
        "schema": "ablation_flip_eval_v1",
        "evalset": str(EVALSET.relative_to(BASE)),
        "design_refs": ["99号Phase0-E2", "96号§5(FAE 2609.08943/"
                        "EviScope 2609.17081)"],
        "engine": "QAConsistencyModule(use_experts=True)真实推理"
                  f"({len(rows)}×{1 + len(PERTURBATION_OPERATORS)}次verify)",
        "operators": {
            name: OPERATOR_EXPECTATION[name]
            for name in PERTURBATION_OPERATORS},
        "distraction": {
            "source": "同evalset其他实例证据块(同doc04, 文本不重叠)",
            "pool_size": DISTRACTOR_POOL_SIZE,
            "add_budget": ADD_DISTRACTOR_BUDGET,
        },
        "summary": summary,
        "details": details,
    }
    run = open_run("eval_ablation_flip", {
        "evalset": str(EVALSET.relative_to(BASE)),
        "n": len(rows),
        "engine": "QAConsistencyModule(use_experts=True)",
        "operators": list(PERTURBATION_OPERATORS),
        "distractor_pool_size": DISTRACTOR_POOL_SIZE,
        "add_distractor_budget": ADD_DISTRACTOR_BUDGET,
        "limit": args.limit or None,
        "elapsed_s": round(time.time() - started, 1),
    })
    run.save_result(report)
    print(f"\nruns落盘 → {run.path}")


if __name__ == "__main__":
    main()
