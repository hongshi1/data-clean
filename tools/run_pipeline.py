#!/usr/bin/env python3
"""三层检测器统一运行入口

组合语法层+语义层+逻辑层检测器，接收评测集或上下文关联结果，
按check_item自动分配到对应检测器，输出统一P/R/F1报告。

使用方式:
  # 1. 评测集闭环评测
  python tools/run_pipeline.py --mode eval

  # 2. 从上下文关联结果检测
  python tools/run_pipeline.py --mode context

  # 3. 单层评测
  python tools/run_pipeline.py --mode eval --layer syntax
"""
import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from algorithms.base import load_expert_knowledge, load_eval_entries, load_context_results
from algorithms.syntax.syntax_checker_v2 import SyntaxChecker
from algorithms.semantic.term_checker import TermChecker
from algorithms.logic.logic_checker_v2 import LogicChecker

EVAL_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
OUT_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/pipeline_results.json"


class DetectionPipeline:
    """三层检测器流水线

    架构:
      评测集/上下文结果 → 按check_item分配 → 对应检测器 → DetectionResult → P/R/F1

    专家知识注入:
      GJB规则库 → 语法层(章节/ID/引用/结构检测)
      专家词典 → 逻辑层(参数定义/单位族/操作符)
      不一致规则 → 所有层(14条规则指导检测)

    上下文关联输入:
      双图融合聚合器输出的occurrences → 直接作为检测器输入
      检测器不需要自己做实体提取
    """

    def __init__(self, expert_knowledge=None):
        if expert_knowledge is None:
            expert_knowledge = load_expert_knowledge()

        # 初始化三层检测器，注入专家知识
        self.syntax_checker = SyntaxChecker(expert_knowledge)
        self.term_checker = TermChecker(expert_knowledge)
        self.logic_checker = LogicChecker(expert_knowledge)

        # check_item → 检测器映射
        self.dispatcher = {
            "GJB": self.syntax_checker,
            "TERM": self.term_checker,
            "PARAM": self.logic_checker,
            "LOGIC": self.logic_checker,
            "POSITIVE": self.syntax_checker,  # 正例用语法层做默认
        }

    def _get_detector(self, check_item):
        """根据check_item选择检测器"""
        prefix = check_item.split("-")[0] if "-" in check_item else check_item
        return self.dispatcher.get(prefix, self.syntax_checker)

    def evaluate(self, eval_entries):
        """评测集闭环评测

        Args:
            eval_entries: 评测集条目列表

        Returns:
            {overall: {P/R/F1}, by_category: {四类P/R/F1}, by_confidence: {gold/silver}}
        """
        # 按check_item分组
        groups = defaultdict(list)
        for entry in eval_entries:
            prefix = entry.get("check_item", "").split("-")[0] if "-" in entry.get("check_item", "") else entry.get("check_item", "")
            groups[prefix].append(entry)

        # 每组用对应检测器评测
        results_by_category = {}
        all_results = []

        for prefix, entries in groups.items():
            detector = self._get_detector(prefix)
            result = detector.evaluate(entries)
            results_by_category[prefix] = {k: v for k, v in result.items() if k != "results"}
            all_results.extend(result["results"])

        # 总体统计
        tp = sum(r.get("tp", 0) for r in results_by_category.values())
        fp = sum(r.get("fp", 0) for r in results_by_category.values())
        fn = sum(r.get("fn", 0) for r in results_by_category.values())
        tn = sum(r.get("tn", 0) for r in results_by_category.values())

        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0

        # 按置信度
        gold_results = [res for res in all_results if res.get("confidence") == "gold"]
        silver_results = [res for res in all_results if res.get("confidence") == "silver"]

        return {
            "overall": {
                "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(p, 4),
                "recall": round(r, 4),
                "f1": round(f1, 4),
            },
            "by_category": results_by_category,
            "by_confidence": {
                "gold": self._calc_prf(gold_results),
                "silver": self._calc_prf(silver_results),
            },
            "detail_results": all_results,
        }

    def _calc_prf(self, results):
        """从检测结果列表计算P/R/F1"""
        tp = sum(1 for r in results if r.get("label") == "inconsistent" and r.get("detected"))
        fp = sum(1 for r in results if r.get("label") == "consistent" and r.get("detected"))
        fn = sum(1 for r in results if r.get("label") == "inconsistent" and not r.get("detected"))
        tn = sum(1 for r in results if r.get("label") == "consistent" and not r.get("detected"))
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r_val = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r_val / (p + r_val) if (p + r_val) > 0 else 0
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                "precision": round(p, 4), "recall": round(r_val, 4), "f1": round(f1, 4)}

    def detect_from_context(self, context_results):
        """从上下文关联结果检测

        上下文关联(双图融合聚合)输出的每个条目:
            {entity_id, entity_type, occurrences[{location, section, content}]}

        每个条目送入对应类型的检测器
        """
        results = []
        for ctx in context_results:
            entity_type = ctx.get("entity_type", "")
            # 根据entity_type选择检测器
            if entity_type == "function_name":
                detector = self.term_checker
            elif entity_type == "numeric_param":
                detector = self.logic_checker
            elif entity_type == "flow_sequence":
                detector = self.logic_checker
            elif entity_type == "table_header":
                detector = self.syntax_checker
            elif entity_type == "interface":
                detector = self.logic_checker
            else:
                detector = self.syntax_checker

            entry = {
                "check_item": entity_type,
                "label": "unknown",
                "entity": ctx,
                "injection": {"method": "context", "original": "", "injected": ""},
            }
            result = detector.detect(entry)
            results.append({
                "entity_id": ctx.get("entity_id", ""),
                "entity_type": entity_type,
                **result.to_dict(),
            })

        return results


def main():
    parser = argparse.ArgumentParser(description="三层检测器统一运行")
    parser.add_argument("--mode", choices=["eval", "context"], default="eval",
                       help="eval=评测集闭环评测, context=从上下文关联结果检测")
    parser.add_argument("--layer", choices=["syntax", "semantic", "logic", "all"], default="all",
                       help="指定单层检测器")
    args = parser.parse_args()

    print("初始化检测器...")
    pipeline = DetectionPipeline()

    if args.mode == "eval":
        print("加载评测集...")
        eval_entries = load_eval_entries()
        print(f"  共 {len(eval_entries)} 条")

        print("运行三层检测器评测...")
        results = pipeline.evaluate(eval_entries)

        print(f"\n=== 总体 ===")
        o = results["overall"]
        print(f"TP={o['tp']} FP={o['fp']} FN={o['fn']} TN={o['tn']}")
        print(f"P={o['precision']} R={o['recall']} F1={o['f1']}")

        print(f"\n=== 按四类 ===")
        for cat, r in results["by_category"].items():
            print(f"  {cat}: P={r['precision']} R={r['recall']} F1={r['f1']}")

        print(f"\n=== 按置信度 ===")
        for conf, r in results["by_confidence"].items():
            print(f"  {conf}: P={r['precision']} R={r['recall']} F1={r['f1']}")

        # 保存
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果保存到 {OUT_PATH}")

    elif args.mode == "context":
        print("加载上下文关联结果...")
        context_results = load_context_results()
        print(f"  共 {len(context_results)} 个条目")

        print("运行三层检测器...")
        results = pipeline.detect_from_context(context_results)

        detected = sum(1 for r in results if r.get("detected"))
        print(f"\n检测结果: {detected}/{len(results)} 检测到不一致")
        print(f"按类型:")
        by_type = defaultdict(lambda: {"total": 0, "detected": 0})
        for r in results:
            t = r.get("entity_type", "unknown")
            by_type[t]["total"] += 1
            if r.get("detected"):
                by_type[t]["detected"] += 1
        for t, d in sorted(by_type.items()):
            print(f"  {t}: {d['detected']}/{d['total']}")


if __name__ == "__main__":
    main()
