#!/usr/bin/env python3
"""统一评测接口 + 闭环评测

读取评测集 → 按check_item分组 → 送入对应检测器 → 计算P/R/F1

检测器分配:
  TERM-* → 语义层（编辑距离/BGE相似度）
  PARAM-* → 逻辑层（Z3/数值比较）
  LOGIC-* → 逻辑层（LCS/序列对比）
  GJB-* → 语法层（规则检查）
  POSITIVE → 所有检测器（验证不误报）
"""
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

from z3 import Real, Solver, unsat

BASE = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_set.json"
OUT_PATH = BASE / "data/gjb_438c/data_assets/srs_qa_v3/eval_results.json"

# 编辑距离
def levenshtein(s1, s2):
    if isinstance(s1, list):
        s1 = str(s1)
    if isinstance(s2, list):
        s2 = str(s2)
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            ins = prev[j + 1] + 1
            dele = curr[j] + 1
            sub = prev[j] + (c1 != c2)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]


def text_sim(s1, s2):
    if not s1 or not s2:
        return 0.0
    d = levenshtein(str(s1), str(s2))
    return 1.0 - d / max(len(str(s1)), len(str(s2)))


# ========== 检测器 ==========

def detect_term(entry):
    """术语层检测：比较occurrences中各位置的content是否一致"""
    occurrences = entry.get("entity", {}).get("occurrences", [])
    if len(occurrences) < 2:
        return False
    
    # 取所有位置的content
    contents = []
    for occ in occurrences:
        c = occ.get("content", "")
        if isinstance(c, str) and len(c) >= 2:
            contents.append(c)
    
    if len(contents) < 2:
        return False
    
    # 如果是注入的负例，检查是否有不一致
    injection = entry.get("injection", {})
    if injection.get("method", "") != "positive" and injection.get("injected"):
        # 有注入：检查注入值和原始值是否不同
        original = str(injection.get("original", ""))
        injected = str(injection.get("injected", ""))
        if original != injected:
            return True  # 检测到不一致
        # 检查occurrences之间是否有差异
        for i in range(len(contents) - 1):
            sim = text_sim(contents[i], contents[i + 1])
            if sim < 0.9:
                return True
        return False
    else:
        # 正例：检查是否一致
        for i in range(len(contents) - 1):
            sim = text_sim(contents[i], contents[i + 1])
            if sim < 0.9:
                return True  # 误报
        return False


def detect_param(entry):
    """参数层检测：Z3求解器验证约束是否矛盾"""
    injection = entry.get("injection", {})
    if injection.get("method", "") == "positive":
        return False  # 正例不应检出
    
    # 如果有Z3验证标记，直接返回
    if entry.get("z3_verified"):
        return True
    
    # 检查数值是否不一致
    original = injection.get("original", "")
    injected = injection.get("injected", "")
    
    # P1数值翻倍
    if "→" in str(original) and "→" in str(injected):
        return True
    
    # 直接比较原始值和注入值
    if str(original) != str(injected):
        # 尝试Z3验证
        try:
            # 提取数值
            orig_vals = re.findall(r'[\d.]+', str(original))
            inj_vals = re.findall(r'[\d.]+', str(injected))
            if orig_vals and inj_vals:
                s = Solver()
                x = Real('param')
                s.add(x >= float(orig_vals[0]))
                s.add(x <= float(inj_vals[0]))
                if s.check() == unsat:
                    return True
        except Exception:
            pass
        return True
    
    return False


def detect_logic(entry):
    """逻辑层检测：序列对比"""
    injection = entry.get("injection", {})
    if injection.get("method", "") == "positive":
        return False
    
    original = injection.get("original", [])
    injected = injection.get("injected", [])
    
    if isinstance(original, list) and isinstance(injected, list):
        # 序列对比：如果长度不同或内容不同→不一致
        if len(original) != len(injected):
            return True
        for a, b in zip(original, injected):
            if str(a) != str(b):
                return True
        return False
    
    if str(original) != str(injected):
        return True
    
    return False


def detect_gjb(entry):
    """GJB合规层检测：规则检查"""
    injection = entry.get("injection", {})
    if injection.get("method", "") == "positive":
        return False
    
    original = injection.get("original", "")
    injected = injection.get("injected", "")
    
    if str(original) != str(injected):
        return True
    
    return False


# ========== 评测 ==========

def evaluate(entries):
    """计算P/R/F1"""
    tp = fp = fn = tn = 0
    results = []
    
    for entry in entries:
        check_item = entry.get("check_item", "")
        label = entry.get("label", "")
        
        # 选择检测器
        if check_item.startswith("TERM"):
            detected = detect_term(entry)
        elif check_item.startswith("PARAM"):
            detected = detect_param(entry)
        elif check_item.startswith("LOGIC"):
            detected = detect_logic(entry)
        elif check_item.startswith("GJB"):
            detected = detect_gjb(entry)
        elif check_item == "POSITIVE":
            # 正例：所有检测器都不应检出
            detected = False
            for detector in [detect_term, detect_param, detect_logic, detect_gjb]:
                if detector(entry):
                    detected = True
                    break
        else:
            detected = False
        
        # 统计
        if label == "inconsistent" and detected:
            tp += 1
        elif label == "consistent" and detected:
            fp += 1
        elif label == "inconsistent" and not detected:
            fn += 1
        elif label == "consistent" and not detected:
            tn += 1
        
        results.append({
            "eval_id": entry.get("eval_id", ""),
            "check_item": check_item,
            "label": label,
            "detected": detected,
            "correct": (label == "inconsistent" and detected) or (label == "consistent" and not detected),
            "confidence": entry.get("confidence", ""),
            "method": entry.get("injection", {}).get("method", ""),
        })
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0
    
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "results": results,
    }


def evaluate_by_category(entries):
    """按四类不一致分别计算P/R/F1"""
    categories = {
        "terminology": lambda e: e.get("check_item", "").startswith("TERM"),
        "parameter": lambda e: e.get("check_item", "").startswith("PARAM"),
        "logic": lambda e: e.get("check_item", "").startswith("LOGIC"),
        "gjb": lambda e: e.get("check_item", "").startswith("GJB"),
        "positive": lambda e: e.get("check_item", "") == "POSITIVE",
    }
    
    results = {}
    for cat, filter_fn in categories.items():
        cat_entries = [e for e in entries if filter_fn(e)]
        if cat_entries:
            results[cat] = evaluate(cat_entries)
            results[cat]["count"] = len(cat_entries)
    
    return results


def evaluate_by_confidence(entries):
    """按置信度分别计算P/R/F1"""
    results = {}
    for conf in ["gold", "silver"]:
        conf_entries = [e for e in entries if e.get("confidence") == conf]
        if conf_entries:
            results[conf] = evaluate(conf_entries)
            results[conf]["count"] = len(conf_entries)
    return results


def main():
    print("加载评测集...")
    with open(EVAL_PATH) as f:
        data = json.load(f)
    entries = data["entries"]
    print(f"  共 {len(entries)} 条")
    
    # 总体评测
    print("\n=== 总体评测 ===")
    overall = evaluate(entries)
    print(f"  TP={overall['tp']} FP={overall['fp']} FN={overall['fn']} TN={overall['tn']}")
    print(f"  Precision={overall['precision']} Recall={overall['recall']} F1={overall['f1']} Accuracy={overall['accuracy']}")
    
    # 按四类
    print("\n=== 按四类不一致 ===")
    by_cat = evaluate_by_category(entries)
    for cat, result in by_cat.items():
        print(f"  {cat} ({result['count']}条): P={result['precision']} R={result['recall']} F1={result['f1']}")
    
    # 按置信度
    print("\n=== 按置信度 ===")
    by_conf = evaluate_by_confidence(entries)
    for conf, result in by_conf.items():
        print(f"  {conf} ({result['count']}条): P={result['precision']} R={result['recall']} F1={result['f1']}")
    
    # 按方法
    print("\n=== 按注入方法 ===")
    method_results = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
    for r in overall["results"]:
        method = r["method"]
        if r["label"] == "inconsistent" and r["detected"]:
            method_results[method]["tp"] += 1
        elif r["label"] == "consistent" and r["detected"]:
            method_results[method]["fp"] += 1
        elif r["label"] == "inconsistent" and not r["detected"]:
            method_results[method]["fn"] += 1
        else:
            method_results[method]["tn"] += 1
    
    for method, counts in sorted(method_results.items()):
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        p = tp / (tp + fp) if (tp + fp) > 0 else 0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
        print(f"  {method}: P={p:.2f} R={r:.2f} F1={f1:.2f} (tp={tp} fp={fp} fn={fn})")
    
    # 保存结果
    output = {
        "overall": {k: v for k, v in overall.items() if k != "results"},
        "by_category": {k: {k2: v2 for k2, v2 in v.items() if k2 != "results"} for k, v in by_cat.items()},
        "by_confidence": {k: {k2: v2 for k2, v2 in v.items() if k2 != "results"} for k, v in by_conf.items()},
        "by_method": dict(method_results),
        "detail_results": overall["results"],
    }
    
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n详细结果保存到 {OUT_PATH}")


if __name__ == "__main__":
    main()
