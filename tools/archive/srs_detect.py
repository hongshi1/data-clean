#!/usr/bin/env python3
"""
SRS不一致性校验 (方向B) — 基于条目的三层检测
=============================================
重写: 基于方向A(srs_context.py)产出的Item列表做检测

三层检测:
  B1 语法层: 直接在content.xml上检测(不需要条目) — 保持不变
  B2 语义层: 在Item.features上做值比较(基于条目) — 重写
  B3 逻辑层: 在Item.features的约束上做Z3求解(跨章节) — 重写

用法:
  python3 tools/srs_detect.py                          # 全部文档
  python3 tools/srs_detect.py --doc 03服务集成          # 单文档
  python3 tools/srs_detect.py --syntax-only            # 仅语法层
"""
import json
import re
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "prompts"))

from srs_context import (
    Item, ItemOccurrence, ItemFeature,
    run_context_aggregation,
    CONSTRAINT_RE, CONSTRAINT_RE_GE, _extract_param_name, _classify_role,
)
from srs_tool import srs_search, srs_read_section, srs_z3_check

BASE = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "configs/srs_config.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


# ── B1: 语法层检测(保持不变,直接在XML上检测) ──────────────────

def detect_syntax(content_xml_path: str) -> list[dict]:
    """语法层: 6项规则检测(不需要条目)"""
    from srs_tool import srs_lint
    config = load_config()
    checks = config.get("tools", {}).get("syntax_checks", [
        "duplicate_section", "id_split", "phantom_requirement",
        "systematic_offset", "coverage", "section_completeness"
    ])
    violations = []
    for check in checks:
        result = srs_lint(check, content_xml_path)
        if result.get("is_violation", False):
            violations.append({
                "layer": "syntax",
                "check": check,
                "severity": "HIGH" if check in ["duplicate_section", "id_split", "phantom_requirement"] else "MEDIUM",
                "description": _describe(check, result),
                "detail": {k: v for k, v in result.items() if k != "check"},
            })
    return violations


def _describe(check, result):
    if check == "duplicate_section":
        d = result.get("duplicates", {})
        return f"章节编号重复(≥3次): {', '.join(f'{s}({c}次)' for s, c in list(d.items())[:5])}"
    elif check == "id_split":
        return f"需求ID分裂: {result.get('total_splits', 0)}组"
    elif check == "phantom_requirement":
        p = result.get("phantoms", [])
        return f"幽灵需求: {len(p)}个({', '.join(p[:3])})"
    elif check == "systematic_offset":
        o = result.get("best_offset", 0)
        r = result.get("match_rate", 0)
        return f"章节号系统性偏移: offset={o:+d}, 匹配率={r:.0%}" if result.get("is_systematic") else ""
    elif check == "coverage":
        u4 = result.get("uncovered_by_ch4", [])
        u5 = result.get("uncovered_by_ch5", [])
        return f"覆盖缺失: 第4章缺{len(u4)}个, 第5章缺{len(u5)}个"
    elif check == "section_completeness":
        m = result.get("missing_chapters", [])
        return f"缺少必需章节: {', '.join(m)}"
    return ""


# ── B2: 语义层检测(基于Item.features做值比较) ─────────────────

def detect_semantic(items: list[Item], phantoms: list[str]) -> list[dict]:
    """语义层: 在条目对features上做值比较"""
    violations = []
    
    # 按param_name分组所有features
    param_features = defaultdict(list)
    for item in items:
        for feature in item.features:
            param_features[feature.param_name].append((item, feature))
    
    # 对每个参数,检查同参数不同位置的值一致性
    for param_name, item_features in param_features.items():
        if len(item_features) < 2:
            continue
        
        for (item_a, f_a), (item_b, f_b) in combinations(item_features, 2):
            # 只对threshold角色报冲突(config/capacity可以不同)
            if f_a.semantic_role != "threshold" or f_b.semantic_role != "threshold":
                continue
            
            # 同一章节不比较(同一位置的约束)
            if f_a.section == f_b.section:
                continue
            
            # 值比较
            if f_a.param_value != f_b.param_value:
                violations.append({
                    "layer": "semantic",
                    "check": "param_value_conflict",
                    "severity": "HIGH",
                    "description": f"参数'{param_name}'的阈值不一致: "
                                 f"{f_a.param_value}{f_a.param_unit}({f_a.section}) "
                                 f"vs {f_b.param_value}{f_b.param_unit}({f_b.section})",
                    "param": param_name,
                    "locations": [
                        {"section": f_a.section, "value": f_a.param_value, 
                         "unit": f_a.param_unit, "text": f_a.original_text[:60]},
                        {"section": f_b.section, "value": f_b.param_value,
                         "unit": f_b.param_unit, "text": f_b.original_text[:60]},
                    ],
                })
    
    # 幽灵需求(从方向A传入)
    for phantom in phantoms:
        violations.append({
            "layer": "semantic",
            "check": "phantom_requirement",
            "severity": "HIGH",
            "description": f"幽灵需求: 章节{phantom}被引用但从未定义",
            "section": phantom,
        })
    
    return violations


# ── B3: 逻辑层检测(基于Item.features的约束做Z3求解) ───────────

def detect_logic(items: list[Item]) -> list[dict]:
    """逻辑层: 跨章节约束Z3求解"""
    violations = []
    
    # 收集所有约束特征
    all_constraints = []
    for item in items:
        for feature in item.features:
            if feature.operator:  # 有操作符的是约束
                all_constraints.append({
                    "param": feature.param_name,
                    "operator": feature.operator,
                    "value": feature.param_value,
                    "unit": feature.param_unit,
                    "section": feature.section,
                    "original": feature.original_text[:60],
                })
    
    # 按参数分组做Z3求解
    param_groups = defaultdict(list)
    for c in all_constraints:
        param_groups[c["param"]].append(c)
    
    for param, constraints in param_groups.items():
        if len(constraints) < 2:
            continue
        z3_result = srs_z3_check(constraints)
        if z3_result.get("result") == "unsat":
            violations.append({
                "layer": "logic",
                "check": "z3_unsatisfiable",
                "severity": "HIGH",
                "description": f"参数'{param}'的{len(constraints)}条约束逻辑不可满足(UNSAT)",
                "constraints": constraints,
                "unsat_core": z3_result.get("unsat_core", ""),
            })
    
    # 串行时间之和检测
    violations.extend(_detect_serial_sum(items))
    
    return violations


def _detect_serial_sum(items: list[Item]) -> list[dict]:
    """检测串行执行时间之和>总预算"""
    exec_times = []
    total_budget = None
    
    for item in items:
        for feature in item.features:
            if any(kw in feature.param_name for kw in ["执行时间", "分析时间", "计算时间"]):
                exec_times.append((feature.section, feature.param_value, feature.param_unit))
            if "总" in feature.param_name and "时间" in feature.param_name:
                total_budget = (feature.param_value, feature.param_unit)
    
    if len(exec_times) >= 2 and total_budget:
        total = sum(t[1] for t in exec_times)
        budget = total_budget[0]
        if total > budget:
            return [{
                "layer": "logic",
                "check": "serial_sum_exceeds_budget",
                "severity": "HIGH",
                "description": f"串行执行时间之和{total}{exec_times[0][2]} > 总预算{budget}{total_budget[1]}",
                "exec_times": exec_times,
                "total_budget": total_budget,
            }]
    return []


# ── 主流程 ────────────────────────────────────────────────────

def detect_document(doc_name: str, config: dict, syntax_only: bool = False) -> dict:
    """对单份文档执行完整检测"""
    doc_id = doc_name[:20]
    content_xml_path = str(BASE / config["data"]["outline_dir"] / f"{doc_id}_content.xml")
    
    if not Path(content_xml_path).exists():
        return {"error": f"content.xml不存在: {content_xml_path}"}
    
    print(f"\n[{doc_name[:35]}]")
    all_violations = []
    
    # B1: 语法层(不需要条目)
    print(f"  B1 语法层检测...")
    syntax_v = detect_syntax(content_xml_path)
    all_violations.extend(syntax_v)
    print(f"    {len(syntax_v)}条违规")
    for v in syntax_v[:3]:
        print(f"    [{v['check']}] {v['description'][:60]}")
    
    if syntax_only:
        return _generate_report(doc_id, all_violations)
    
    # 方向A: 上下文关联+特征提取
    print(f"  方向A: 上下文关联+特征提取...")
    items, phantoms = run_context_aggregation(content_xml_path)
    print(f"    {len(items)}个条目, {sum(len(i.features) for i in items)}个特征, {len(phantoms)}个幽灵需求")
    
    # B2: 语义层(基于条目)
    print(f"  B2 语义层检测(基于条目)...")
    semantic_v = detect_semantic(items, phantoms)
    all_violations.extend(semantic_v)
    print(f"    {len(semantic_v)}条违规")
    for v in semantic_v[:3]:
        print(f"    [{v['check']}] {v['description'][:60]}")
    
    # B3: 逻辑层(基于条目约束)
    print(f"  B3 逻辑层检测(基于条目约束)...")
    logic_v = detect_logic(items)
    all_violations.extend(logic_v)
    print(f"    {len(logic_v)}条违规")
    for v in logic_v[:3]:
        print(f"    [{v['check']}] {v['description'][:60]}")
    
    report = _generate_report(doc_id, all_violations)
    print(f"\n  总计: {len(all_violations)}条 (语法{len(syntax_v)}+语义{len(semantic_v)}+逻辑{len(logic_v)})")
    return report


def _generate_report(doc_id, violations):
    by_layer = Counter(v["layer"] for v in violations)
    by_severity = Counter(v["severity"] for v in violations)
    return {
        "doc_id": doc_id,
        "detect_date": datetime.now().isoformat(),
        "total_violations": len(violations),
        "by_layer": dict(by_layer),
        "by_severity": dict(by_severity),
        "violations": violations,
    }


def main():
    parser = argparse.ArgumentParser(description="SRS一致性校验(方向B)")
    parser.add_argument("--doc", type=str)
    parser.add_argument("--syntax-only", action="store_true")
    args = parser.parse_args()
    
    config = load_config()
    output_dir = BASE / config["data"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("SRS一致性校验 (方向B: 基于条目的三层检测)")
    print("=" * 60)
    
    if args.doc:
        report = detect_document(args.doc, config, args.syntax_only)
        out = output_dir / f"{args.doc[:20]}_report.json"
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n报告: {out}")
    else:
        outline_dir = BASE / config["data"]["outline_dir"]
        docs = sorted(set(f.name.replace("_content.xml", "")
                         for f in outline_dir.glob("*_content.xml")))
        all_reports = []
        for doc_id in docs:
            report = detect_document(doc_id, config, args.syntax_only)
            all_reports.append(report)
        
        total = sum(r.get("total_violations", 0) for r in all_reports)
        print(f"\n{'='*60}")
        print(f"汇总: {len(all_reports)}份文档, {total}条违规")
        (output_dir / "_summary.json").write_text(
            json.dumps(all_reports, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
