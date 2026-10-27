#!/usr/bin/env python3
"""三层检测器统一运行入口(盲测协议)

按entity_type路由(不含答案信息),检测器只看occurrences_injected。
评测协议分层:
  --mode eval        检测器盲测(L3): 报P/R/F1+技术分解
  --mode verify      注入有效性验证(L1): 元数据+Z3重跑,认证数据集
  --mode context     真实文档检测(无label)
"""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.consistency_check.base import load_expert_knowledge, load_eval_entries, load_context_results
from algorithms.consistency_check.syntax.syntax_checker_v2 import SyntaxChecker
from algorithms.consistency_check.semantic.term_checker import TermChecker
from algorithms.consistency_check.logic.logic_checker_v2 import LogicChecker

OUT_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/pipeline_results.json"


class DetectionPipeline:
    """三层检测器流水线(盲测协议)"""

    def __init__(self, expert_knowledge=None):
        if expert_knowledge is None:
            expert_knowledge = load_expert_knowledge()
        self.syntax_checker = SyntaxChecker(expert_knowledge)
        self.term_checker = TermChecker(expert_knowledge)
        self.logic_checker = LogicChecker(expert_knowledge)

    def _route(self, entity_type: str):
        """按entity_type路由(无答案信息泄漏;POSITIVE正例也走真实类型)"""
        return {
            "function_name": self.term_checker,
            "interface": self.term_checker,
            "numeric_param": self.logic_checker,
            "flow_sequence": self.logic_checker,
            "table_header": self.syntax_checker,
        }.get(entity_type, self.syntax_checker)

    def evaluate(self, eval_entries):
        """检测器盲测: label只评分,detect只看occurrences_injected"""
        # 按entity_type分组路由
        groups = defaultdict(list)
        for entry in eval_entries:
            etype = entry.get("entity", {}).get("entity_type", "")
            groups[etype].append(entry)

        results_by_type = {}
        all_results = []
        for etype, entries in groups.items():
            detector = self._route(etype)
            result = detector.evaluate(entries)
            results_by_type[etype] = {k: v for k, v in result.items() if k != "results"}
            all_results.extend(result["results"])

        tp = sum(r.get("tp", 0) for r in results_by_type.values())
        fp = sum(r.get("fp", 0) for r in results_by_type.values())
        fn = sum(r.get("fn", 0) for r in results_by_type.values())
        tn = sum(r.get("tn", 0) for r in results_by_type.values())
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        # 按check_item细分(诊断用,不参与路由)
        by_ci = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        for res in all_results:
            ci = res.get("check_item", "?")
            if res["label"] == "inconsistent" and res["detected"]:
                by_ci[ci]["tp"] += 1
            elif res["label"] == "consistent" and res["detected"]:
                by_ci[ci]["fp"] += 1
            elif res["label"] == "inconsistent" and not res["detected"]:
                by_ci[ci]["fn"] += 1
            else:
                by_ci[ci]["tn"] += 1

        # 技术分解
        tech_counts = defaultdict(int)
        for res in all_results:
            if res.get("detected"):
                tech_counts[res.get("technique", "?")] += 1

        return {
            "protocol": "blind",
            "overall": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                        "precision": round(p, 4), "recall": round(r, 4),
                        "f1": round(f1, 4)},
            "by_entity_type": results_by_type,
            "by_check_item": {ci: self._prf(c) for ci, c in by_ci.items()},
            "technique_breakdown": dict(tech_counts),
            "detail_results": all_results,
        }

    def _prf(self, c):
        p = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) > 0 else 0
        r = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        return {"tp": c["tp"], "fp": c["fp"], "fn": c["fn"],
                "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)}

    def detect_from_context(self, context_results):
        results = []
        for ctx in context_results:
            detector = self._route(ctx.get("entity_type", ""))
            result = detector.detect_from_context([ctx])[0]
            results.append(result)
        return results


def main():
    parser = argparse.ArgumentParser(description="三层检测器统一运行(盲测协议)")
    parser.add_argument("--mode", choices=["eval", "context"], default="eval")
    args = parser.parse_args()

    print("初始化检测器(盲测协议:只看occurrences_injected)...")
    pipeline = DetectionPipeline()

    if args.mode == "eval":
        eval_entries = load_eval_entries()
        print(f"加载评测集 {len(eval_entries)} 条")
        results = pipeline.evaluate(eval_entries)

        o = results["overall"]
        print("\n=== 检测器盲测(L3协议) ===")
        print(f"TP={o['tp']} FP={o['fp']} FN={o['fn']} TN={o['tn']}")
        print(f"P={o['precision']} R={o['recall']} F1={o['f1']}")

        print("\n=== 按entity_type ===")
        for t, r in results["by_entity_type"].items():
            print(f"  {t}: P={r['precision']} R={r['recall']} F1={r['f1']}")

        print("\n=== 按check_item(诊断) ===")
        for ci, r in sorted(results["by_check_item"].items()):
            print(f"  {ci}: P={r['precision']} R={r['recall']} F1={r['f1']} (tp={r['tp']} fp={r['fp']} fn={r['fn']})")

        print("\n=== 技术分解 ===")
        for tech, n in sorted(results["technique_breakdown"].items(), key=lambda x: -x[1]):
            print(f"  {tech}: {n}")

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n保存到 {OUT_PATH}")

    elif args.mode == "context":
        ctx = load_context_results()
        print(f"加载上下文结果 {len(ctx)} 条")
        results = pipeline.detect_from_context(ctx)
        detected = sum(1 for r in results if r.get("detected"))
        print(f"检测到 {detected}/{len(results)} 个不一致")
        by_type = defaultdict(lambda: {"total": 0, "detected": 0})
        for r in results:
            t = r.get("entity_type", "?")
            by_type[t]["total"] += 1
            if r.get("detected"):
                by_type[t]["detected"] += 1
        for t, d in sorted(by_type.items()):
            print(f"  {t}: {d['detected']}/{d['total']}")


if __name__ == "__main__":
    main()
