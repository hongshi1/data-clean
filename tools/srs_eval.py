#!/usr/bin/env python3
"""
SRS Consistency Detection Evaluation Framework
对一致性检测结果进行评测，计算P/R/F1指标。

评测流程:
  1. 读取Gold Standard (data/gjb_438c/gold_standard/*_gold.json)
  2. 读取检测结果 (data/gjb_438c/consistency_reports/*_report.json)
  3. 匹配检测结果与GT，计算TP/FP/FN/TN
  4. 按层(语法/语义/逻辑)分别计算Precision/Recall/F1
  5. 输出评测报告

匹配规则:
  - 位置匹配: 检测结果的location(sections)与GT的location.sections有交集
  - 类型匹配: 检测结果的check_type与GT的type对应(见TYPE_MAPPING)
  - is_conflict=false的GT项为正值，检测不应报告 → 报告则算FP
  - is_conflict=true的GT项为真矛盾，检测应报告 → 未报告则算FN

GT类型说明:
  - same_param_same_value:  同参数同值，确认一致(正值) → semantic层
  - same_value_diff_semantics: 同值不同义，确认一致(正值) → semantic层
  - logic_satisfiable:      逻辑可满足，确认一致(正值) → logic层
  - logic_contradiction:    逻辑矛盾(真矛盾) → logic层
  - logic_unsatisfiable:    逻辑不可满足(真矛盾) → logic层
  - logic_incomplete:       逻辑不完整/需求遗漏(真矛盾) → logic层
  - text_table_conflict:    文本-表格冲突(真矛盾) → semantic层
  - cross_document_conflict: 跨文档冲突(真矛盾) → logic层
"""

import json
import re
import argparse
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLD_DIR = REPO_ROOT / "data" / "gjb_438c" / "gold_standard"
REPORT_DIR = REPO_ROOT / "data" / "gjb_438c" / "consistency_reports"
OUTPUT_PATH = REPO_ROOT / "data" / "gjb_438c" / "evaluation_results.json"


# ── 类型映射: GT type → 兼容的检测 check_type ─────────────────
# 用于判断检测类型是否与GT类型对应

TYPE_MAPPING = {
    # ── 真矛盾类型(is_conflict=true) → 检测器应报出的check_type ──
    "logic_contradiction": [
        "logic_unsatisfiable",
        "cross_section_policy_contradiction",
        "cross_section_declaration_contradiction",
        "cross_section_value_contradiction",
    ],
    "logic_unsatisfiable": [
        "logic_unsatisfiable",
        "cross_section_value_contradiction",
    ],
    "logic_incomplete": [
        "logic_unsatisfiable",
        "missing_qualification_entry",
        "missing_text_section",
        "missing_chapter",
        "structure",
        "cross_section_promise_implementation_mismatch",
    ],
    "text_table_conflict": [
        "traceability_value_not_in_text",
        "text_table_name_mismatch",
        "text_table_contradiction",
        "missing_qualification_entry",
        "missing_table",
        "empty_table_placeholder",
    ],
    "cross_document_conflict": [
        # 跨文档冲突，单文档检测器难以发现
    ],

    # ── 正值类型(is_conflict=false) → 检测器不应报出的check_type ──
    "same_param_same_value": [
        "param_name_inconsistency",
        "same_value_inconsistency",
        "same_param_diff_value",
    ],
    "same_value_diff_semantics": [
        "param_name_inconsistency",
        "same_value_inconsistency",
        "same_param_diff_value",
    ],
    "logic_satisfiable": [
        "logic_unsatisfiable",
    ],
}

# 检测check_type → 层
CHECK_TYPE_TO_LAYER = {
    # syntax
    "missing_qualification_entry": "syntax",
    "missing_text_section": "syntax",
    "missing_table": "syntax",
    "missing_chapter": "syntax",
    "structure": "syntax",
    # semantic
    "param_name_inconsistency": "semantic",
    "same_value_inconsistency": "semantic",
    "same_param_diff_value": "semantic",
    "traceability_value_not_in_text": "semantic",
    "traceability_value_mismatch": "semantic",
    "text_table_name_mismatch": "semantic",
    "text_table_contradiction": "semantic",
    "empty_table_placeholder": "semantic",
    # logic
    "logic_unsatisfiable": "logic",
    "logic_analysis": "logic",
    "logic_check_failed": "logic",
    "cross_section_declaration_contradiction": "logic",
    "cross_section_value_contradiction": "logic",
    "cross_section_policy_contradiction": "logic",
    "cross_section_promise_implementation_mismatch": "logic",
}

# GT type → 层
GT_TYPE_TO_LAYER = {
    "same_param_same_value": "semantic",
    "same_value_diff_semantics": "semantic",
    "text_table_conflict": "semantic",
    "logic_contradiction": "logic",
    "logic_satisfiable": "logic",
    "logic_incomplete": "logic",
    "logic_unsatisfiable": "logic",
    "cross_document_conflict": "logic",
}

LAYER_CN = {"syntax": "语法", "semantic": "语义", "logic": "逻辑"}


# ── 工具函数 ──────────────────────────────────────────────────

def safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return round(a / b, 4)


def calc_prf(tp: int, fp: int, fn: int) -> dict:
    p = safe_div(tp, tp + fp)
    r = safe_div(tp, tp + fn)
    f1 = safe_div(2 * p * r, p + r) if (p + r) > 0 else 0.0
    return {"TP": tp, "FP": fp, "FN": fn, "P": p, "R": r, "F1": f1}


def extract_sections(text: str) -> set:
    """从文本中提取章节号集合(仅叶子节点)，如 '3.2.4 主循环调度功能' → {'3.2.4'}

    注意: 不展开父级章节号，避免3.2.2与3.2.4通过共同父级3.2误匹配。
    父子匹配由 locations_overlap 的前缀检查处理。
    使用re.ASCII使\b仅匹配ASCII边界(中文字符视为非单词字符)。
    """
    if not text:
        return set()
    sections = set()
    for m in re.findall(r'\b(\d+(?:\.\d+)*)\b', str(text), re.ASCII):
        sections.add(m)
    return sections


def get_detection_locations(issue: dict) -> set:
    """从检测结果中提取所有位置(章节号集合)

    优先从结构化字段提取，仅当结构化字段为空时从description补充。
    """
    locations = set()
    for loc in issue.get("locations", []):
        if isinstance(loc, dict):
            sec = loc.get("section", "")
            locations |= extract_sections(sec)
        elif isinstance(loc, str):
            locations |= extract_sections(loc)
    for cell in issue.get("traceability_row", []):
        locations |= extract_sections(str(cell))
    if issue.get("section_number"):
        locations |= extract_sections(issue["section_number"])
    if issue.get("section"):
        locations |= extract_sections(issue["section"])
    for c in issue.get("conflicting_constraints", []):
        if isinstance(c, str):
            locations |= extract_sections(c)
        elif isinstance(c, dict):
            locations |= extract_sections(str(c.get("section", "")))
    # 仅当结构化字段无结果时，从description补充
    if not locations:
        desc = issue.get("description", "")
        locations |= extract_sections(desc)
    return locations


def get_gt_locations(gt: dict) -> set:
    """从GT标注中提取所有位置(章节号集合)

    GT格式: "location": {"sections": ["3.2.1", "3.2.4"], "cross_document": "..."}
    优先从location.sections提取，仅当为空时从description补充。
    """
    locations = set()
    loc = gt.get("location", {})
    if isinstance(loc, dict):
        for sec in loc.get("sections", []):
            locations |= extract_sections(sec)
        if loc.get("cross_document"):
            locations |= extract_sections(loc["cross_document"])
    elif isinstance(loc, list):
        for sec in loc:
            locations |= extract_sections(sec)
    # 兼容旧格式: 直接的location数组
    for sec in gt.get("location_sections", []):
        locations |= extract_sections(sec)
    # 仅当结构化字段无结果时，从description补充
    if not locations:
        desc = gt.get("description", "")
        locations |= extract_sections(desc)
    return locations


def locations_overlap(det_locs: set, gt_locs: set) -> bool:
    """检查两个位置集合是否有交集(支持父子章节前缀匹配)

    匹配规则:
      - 精确匹配: '3.2.1' == '3.2.1'
      - 父子匹配: '3.2' 是 '3.2.4' 的前缀 → 匹配
      - 不匹配:   '3.2.2' 与 '3.2.4' 互非前缀 → 不匹配
    """
    if not det_locs and not gt_locs:
        return True
    if not det_locs or not gt_locs:
        return False
    for a in det_locs:
        for b in gt_locs:
            if a == b or a.startswith(b + ".") or b.startswith(a + "."):
                return True
    return False


def types_match(det_check_type: str, gt_type: str) -> bool:
    """检查检测类型与GT类型是否对应"""
    compatible = TYPE_MAPPING.get(gt_type, [])
    return det_check_type in compatible


def descriptions_overlap(gt_desc: str, det_desc: str) -> bool:
    """检查GT描述和检测描述是否有关键词重叠（fallback匹配）。"""
    if not gt_desc or not det_desc:
        return False
    # Extract meaningful keywords (>2 chars) from both descriptions
    gt_words = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}|\d+', gt_desc.lower()))
    det_words = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}|\d+', det_desc.lower()))
    if not gt_words or not det_words:
        return False
    overlap = gt_words & det_words
    # Need at least 2 meaningful overlapping keywords
    return len(overlap) >= 2


def get_issue_id(issue: dict, idx: int) -> str:
    """为检测结果生成ID"""
    return issue.get("id", f"ISSUE-{idx+1:03d}")


def is_info_only(issue: dict) -> bool:
    """判断检测结果是否仅为信息性(非矛盾报告)

    logic_analysis是分析摘要而非矛盾报告，不计入FP
    """
    if issue.get("check_type") == "logic_analysis":
        return True
    if issue.get("severity") == "INFO" and issue.get("check_type") != "logic_unsatisfiable":
        return True
    return False


# ── 核心评测逻辑 ──────────────────────────────────────────────

def evaluate_document(gt_data: dict, report_data: dict) -> dict:
    """对单个文档进行评测

    评测流程:
      Step 1: 对每个GT真矛盾(is_conflict=true)，查找匹配的检测 → TP/FN
      Step 2: 未匹配到GT真矛盾的检测 → FP
      Step 3: 正值GT(is_conflict=false)未被误报 → TN
    """
    # Gold Standard使用"ground_truths"字段
    gt_annotations = gt_data.get("ground_truths", gt_data.get("annotations", []))
    det_issues = report_data.get("issues", [])

    # 过滤掉纯信息性的检测结果
    det_issues_real = [iss for iss in det_issues if not is_info_only(iss)]

    # 分离GT: 真实矛盾(is_conflict=true) vs 正值(is_conflict=false)
    gt_conflicts = [g for g in gt_annotations if g.get("is_conflict", True)]
    gt_positives = [g for g in gt_annotations if not g.get("is_conflict", True)]

    matched_det_indices = set()
    # 记录每个正值GT是否被误报匹配
    positive_matched_by_detection = {}  # gt_id → detection_idx
    details = []

    tp = 0
    fp = 0
    fn = 0
    tn = 0

    layer_stats = {
        "syntax": {"TP": 0, "FP": 0, "FN": 0, "TN": 0},
        "semantic": {"TP": 0, "FP": 0, "FN": 0, "TN": 0},
        "logic": {"TP": 0, "FP": 0, "FN": 0, "TN": 0},
    }

    # ── Step 1: 对每个GT真矛盾，查找匹配的检测结果 → TP/FN ──
    for gt in gt_conflicts:
        gt_type = gt.get("type", "")
        gt_layer = GT_TYPE_TO_LAYER.get(gt_type, "semantic")
        gt_locs = get_gt_locations(gt)
        gt_id = gt.get("gt_id", gt.get("id", ""))

        best_match = None
        best_match_idx = None

        for idx, issue in enumerate(det_issues_real):
            if idx in matched_det_indices:
                continue

            det_type = issue.get("check_type", "")
            det_locs = get_detection_locations(issue)

            # Primary match: type + location
            if types_match(det_type, gt_type) and locations_overlap(det_locs, gt_locs):
                best_match = issue
                best_match_idx = idx
                break
            # Fallback match: type + description overlap
            if types_match(det_type, gt_type) and descriptions_overlap(gt.get("description", ""), issue.get("description", "")):
                best_match = issue
                best_match_idx = idx
                break

        if best_match is not None:
            tp += 1
            layer_stats[gt_layer]["TP"] += 1
            matched_det_indices.add(best_match_idx)
            issue_id = get_issue_id(best_match, best_match_idx)
            details.append({
                "gt_id": gt_id,
                "matched_detection": issue_id,
                "status": "TP",
                "layer": gt_layer,
                "gt_type": gt_type,
                "det_type": best_match.get("check_type", ""),
                "gt_desc": gt.get("description", "")[:80],
                "det_desc": best_match.get("description", "")[:80],
                "note": "正确检测",
            })
        else:
            fn += 1
            layer_stats[gt_layer]["FN"] += 1
            details.append({
                "gt_id": gt_id,
                "matched_detection": None,
                "status": "FN",
                "layer": gt_layer,
                "gt_type": gt_type,
                "det_type": "",
                "gt_desc": gt.get("description", "")[:80],
                "det_desc": "",
                "note": "漏报" if gt_type != "cross_document_conflict" else "漏报(跨文档)",
            })

    # ── Step 2: 未匹配到GT真矛盾的检测 → FP ──
    for idx, issue in enumerate(det_issues_real):
        if idx in matched_det_indices:
            continue

        det_type = issue.get("check_type", "")
        det_layer = CHECK_TYPE_TO_LAYER.get(det_type, "semantic")
        issue_id = get_issue_id(issue, idx)
        det_locs = get_detection_locations(issue)

        # 检查是否匹配到正值GT(is_conflict=false)
        matched_positive = None
        for gt in gt_positives:
            gt_type = gt.get("type", "")
            gt_locs = get_gt_locations(gt)
            if types_match(det_type, gt_type) and locations_overlap(det_locs, gt_locs):
                matched_positive = gt
                break

        fp += 1
        layer_stats[det_layer]["FP"] += 1

        if matched_positive:
            matched_gt_id = matched_positive.get("gt_id", matched_positive.get("id", ""))
            positive_matched_by_detection[matched_gt_id] = idx
            note = f"误报(匹配到正值{matched_gt_id})"
        else:
            note = "误报(无匹配GT)"

        details.append({
            "gt_id": matched_positive.get("gt_id", matched_positive.get("id", "")) if matched_positive else None,
            "matched_detection": issue_id,
            "status": "FP",
            "layer": det_layer,
            "gt_type": matched_positive.get("type", "") if matched_positive else "",
            "det_type": det_type,
            "gt_desc": matched_positive.get("description", "")[:80] if matched_positive else "",
            "det_desc": issue.get("description", "")[:80],
            "note": note,
        })

    # ── Step 3: 正值GT(is_conflict=false)未被误报 → TN ──
    for gt in gt_positives:
        gt_type = gt.get("type", "")
        gt_layer = GT_TYPE_TO_LAYER.get(gt_type, "semantic")
        gt_id = gt.get("gt_id", gt.get("id", ""))

        # 检查是否在Step 2中被误报匹配
        if gt_id in positive_matched_by_detection:
            # 这个正值被误报了，已在Step 2记为FP，不算TN
            continue

        tn += 1
        layer_stats[gt_layer]["TN"] += 1
        details.append({
            "gt_id": gt_id,
            "matched_detection": None,
            "status": "TN",
            "layer": gt_layer,
            "gt_type": gt_type,
            "det_type": "",
            "gt_desc": gt.get("description", "")[:80],
            "det_desc": "",
            "note": "正确未报(确认一致)",
        })

    # ── 计算指标 ──
    overall = calc_prf(tp, fp, fn)

    by_layer = {}
    for layer, stats in layer_stats.items():
        by_layer[layer] = calc_prf(stats["TP"], stats["FP"], stats["FN"])
        by_layer[layer]["TN"] = stats["TN"]

    return {
        "doc_name": report_data.get("doc_name", ""),
        "total_gt": len(gt_annotations),
        "total_gt_conflicts": len(gt_conflicts),
        "total_gt_positives": len(gt_positives),
        "total_detected": len(det_issues_real),
        "total_detected_raw": len(det_issues),
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": overall["P"],
        "recall": overall["R"],
        "f1": overall["F1"],
        "by_layer": by_layer,
        "details": details,
    }


# ── 文件查找 ──────────────────────────────────────────────────

def find_gold_file(doc_name: str) -> Path | None:
    candidates = [
        GOLD_DIR / f"{doc_name}_gold.json",
        GOLD_DIR / f"{doc_name}.gold.json",
        GOLD_DIR / f"{doc_name}.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_report_file(doc_name: str) -> Path | None:
    candidates = [
        REPORT_DIR / f"{doc_name}_report.json",
        REPORT_DIR / f"{doc_name}.report.json",
        REPORT_DIR / f"{doc_name}.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


# ── 主评测流程 ────────────────────────────────────────────────

def run_evaluation(doc_names: list = None, verbose: bool = True) -> dict:
    """运行评测"""
    if doc_names is None:
        doc_names = []
        if GOLD_DIR.exists():
            for f in sorted(GOLD_DIR.glob("*_gold.json")):
                name = f.stem.replace("_gold", "")
                doc_names.append(name)

    if not doc_names:
        if verbose:
            print("未找到Gold Standard文件。")
            print(f"请将标注文件放入: {GOLD_DIR}")
            print("文件命名格式: {doc_name}_gold.json")
        return {}

    all_results = []
    aggregated = {
        "syntax": {"TP": 0, "FP": 0, "FN": 0, "TN": 0},
        "semantic": {"TP": 0, "FP": 0, "FN": 0, "TN": 0},
        "logic": {"TP": 0, "FP": 0, "FN": 0, "TN": 0},
    }
    total_tp = total_fp = total_fn = total_tn = 0

    for doc_name in doc_names:
        gold_path = find_gold_file(doc_name)
        report_path = find_report_file(doc_name)

        if not gold_path:
            if verbose:
                print(f"  [SKIP] {doc_name}: Gold Standard文件未找到")
            continue
        if not report_path:
            if verbose:
                print(f"  [SKIP] {doc_name}: 检测报告文件未找到")
            continue

        if verbose:
            print(f"  [EVAL] {doc_name}")
            print(f"    Gold:      {gold_path}")
            print(f"    Report:    {report_path}")

        gt_data = json.loads(gold_path.read_text("utf-8"))
        report_data = json.loads(report_path.read_text("utf-8"))

        result = evaluate_document(gt_data, report_data)
        all_results.append(result)

        total_tp += result["TP"]
        total_fp += result["FP"]
        total_fn += result["FN"]
        total_tn += result["TN"]

        for layer in aggregated:
            for k in ("TP", "FP", "FN", "TN"):
                aggregated[layer][k] += result["by_layer"][layer].get(k, 0)

        if verbose:
            print(f"    GT: {result['total_gt']} (矛盾{result['total_gt_conflicts']}, 正值{result['total_gt_positives']})")
            print(f"    检测: {result['total_detected']} (原始{result['total_detected_raw']})")
            print(f"    TP={result['TP']} FP={result['FP']} FN={result['FN']} TN={result['TN']}")
            print(f"    P={result['precision']} R={result['recall']} F1={result['f1']}")
            for layer in ["syntax", "semantic", "logic"]:
                s = result["by_layer"][layer]
                print(f"    [{layer}] TP={s['TP']} FP={s['FP']} FN={s['FN']} TN={s.get('TN',0)} P={s['P']} R={s['R']} F1={s['F1']}")

    if not all_results:
        return {}

    overall = calc_prf(total_tp, total_fp, total_fn)
    by_layer_agg = {}
    for layer, stats in aggregated.items():
        by_layer_agg[layer] = calc_prf(stats["TP"], stats["FP"], stats["FN"])
        by_layer_agg[layer]["TN"] = stats["TN"]

    return {
        "eval_date": date.today().isoformat(),
        "eval_time": datetime.now().isoformat(),
        "num_docs": len(all_results),
        "total_gt": sum(r["total_gt"] for r in all_results),
        "total_gt_conflicts": sum(r["total_gt_conflicts"] for r in all_results),
        "total_gt_positives": sum(r["total_gt_positives"] for r in all_results),
        "total_detected": sum(r["total_detected"] for r in all_results),
        "TP": total_tp,
        "FP": total_fp,
        "FN": total_fn,
        "TN": total_tn,
        "precision": overall["P"],
        "recall": overall["R"],
        "f1": overall["F1"],
        "by_layer": by_layer_agg,
        "per_doc": all_results,
    }


# ── 输出格式化 ────────────────────────────────────────────────

def print_summary(eval_result: dict):
    """打印评测摘要"""
    print("\n" + "=" * 80)
    print("SRS一致性检测评测结果汇总")
    print("=" * 80)
    print(f"评测日期:     {eval_result['eval_date']}")
    print(f"文档数量:     {eval_result['num_docs']}")
    print(f"GT总数:       {eval_result['total_gt']} (真矛盾{eval_result['total_gt_conflicts']}, 正值{eval_result['total_gt_positives']})")
    print(f"检测总数:     {eval_result['total_detected']}")
    print("-" * 80)
    print(f"  TP={eval_result['TP']}  FP={eval_result['FP']}  FN={eval_result['FN']}  TN={eval_result['TN']}")
    print(f"  Precision={eval_result['precision']}  Recall={eval_result['recall']}  F1={eval_result['f1']}")
    print("-" * 80)
    print(f"  {'层':<12} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print(f"  {'-'*76}")
    for layer in ["syntax", "semantic", "logic"]:
        s = eval_result["by_layer"][layer]
        label = f"{layer}({LAYER_CN[layer]})"
        print(f"  {label:<12} {s['TP']:>4} {s['FP']:>4} {s['FN']:>4} {s.get('TN',0):>4} {s['P']:>10} {s['R']:>10} {s['F1']:>10}")
    print("=" * 80)

    for doc_result in eval_result.get("per_doc", []):
        print(f"\n{'─' * 80}")
        print(f"文档: {doc_result['doc_name']}")
        print(f"  GT: {doc_result['total_gt']}条 (真矛盾{doc_result['total_gt_conflicts']}, 正值{doc_result['total_gt_positives']})")
        print(f"  检测: {doc_result['total_detected']}条 (原始{doc_result['total_detected_raw']}条)")
        print(f"  TP={doc_result['TP']} FP={doc_result['FP']} FN={doc_result['FN']} TN={doc_result['TN']}")
        print(f"  P={doc_result['precision']} R={doc_result['recall']} F1={doc_result['f1']}")
        print(f"\n  {'GT_ID':<10} {'状态':>4} {'层':<10} {'GT类型':<25} {'检测类型':<30} {'说明'}")
        print(f"  {'─'*100}")
        for d in doc_result["details"]:
            gt_id = d.get("gt_id") or "-"
            status = d["status"]
            layer = d.get("layer", "")
            gt_type = d.get("gt_type", "") or "-"
            det_type = d.get("det_type", "") or "-"
            note = d.get("note", "")
            det_id = d.get("matched_detection") or "-"
            print(f"  {gt_id:<10} {status:>4} {layer:<10} {gt_type:<25} {det_type:<30} {note}")
            if det_id != "-":
                print(f"  {'':>16} 检测: {det_id} | {d.get('det_desc','')}")
            elif d.get("gt_desc"):
                print(f"  {'':>16} GT: {d.get('gt_desc','')}")


def main():
    parser = argparse.ArgumentParser(description="SRS一致性检测评测框架")
    parser.add_argument(
        "docs", nargs="*", default=None,
        help="要评测的文档名(不含后缀)。不指定则评测所有有Gold Standard的文档"
    )
    parser.add_argument(
        "-o", "--output", default=str(OUTPUT_PATH),
        help=f"输出路径 (默认: {OUTPUT_PATH})"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="只输出JSON，不打印摘要"
    )
    args = parser.parse_args()

    eval_result = run_evaluation(
        doc_names=args.docs if args.docs else None,
        verbose=not args.quiet,
    )

    if not eval_result:
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(eval_result, indent=2, ensure_ascii=False), "utf-8")

    if not args.quiet:
        print_summary(eval_result)
        print(f"\n评测结果已保存: {output_path}")


if __name__ == "__main__":
    main()
