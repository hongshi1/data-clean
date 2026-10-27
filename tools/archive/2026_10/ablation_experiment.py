#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""消融实验框架: 逐个去掉算法组件, 测量指标变化

设计(论文核心实验表格):
  完整系统(52项三层+LLM) → 基线
  -Z3:     PARAM层退化为简单值比较(去SMT)
  -图论:   LOGIC层退化为LLM判断(去环检测/拓扑/覆盖)
  -统计:   TERM层退化为固定阈值0.5(去μ±σ动态校准)
  -LLM:    17项标记为不可执行(去GLM-5推理)
  -锚点:   mermaid_key清空(去born-digital对齐)
  -上下文: 用全文检索替代图谱激活(去k-hop召回)

每组输出: Precision / Recall / F1 / 按层分 / 发现数
"""
import json
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)


def run_ablation(doc_num="02", config="full"):
    """运行单组消融实验

    config:
      full:  完整系统
      no_z3: PARAM层去Z3(退化为值比较)
      no_graph: LOGIC层去图论(退化为计数)
      no_stat: TERM层去统计校准(固定阈值)
      no_llm: 17项LLM不可执行
      no_anchor: mermaid_key清空
      no_ctx: 用全文检索替代图谱召回
    """
    from algorithms.context_association.context_graph import ContextGraph
    from algorithms.consistency_check.check_engine import CheckEngine

    cg = ContextGraph()
    ce = CheckEngine(cg)

    # 应用消融配置
    if config == "no_z3":
        # PARAM层: 禁用Z3, 用简单值比较
        original = ce._check_params
        def simple_params(doc_num, doc, g):
            out = defaultdict(list)
            cons = ce._extract_constraints(doc)
            for pid, kws in ce.PARAM_KEYWORDS.items():
                for pname, group in cons.items():
                    if not any(k in pname for k in kws) or len(group) < 2:
                        continue
                    vals = [c["value"] for c in group]
                    if max(vals) != min(vals):
                        out[pid].append({
                            "desc": f"参数「{pname}」值不等(简单比较, 无Z3)",
                            "section": " / ".join(set(c["section"] for c in group)),
                            "evidence": " vs ".join(str(c["value"]) for c in group[:3]),
                        })
            return out
        ce._check_params = simple_params

    elif config == "no_graph":
        # LOGIC层: 禁用图论, 退化为纯计数
        original = ce._check_logic_basic
        def simple_logic(doc_num, doc, g):
            out = defaultdict(list)
            all_text = " ".join(ce.sec_texts.get(doc, {}).values())
            import re as _re
            claims = _re.findall(r"(\d+)(?:种|类|个)(?:工况|模式|场景)", all_text)
            if claims:
                out["LOGIC-05"].append({
                    "desc": f"声明{claims[0]}种(纯计数, 无图论分析)",
                    "section": "全文", "evidence": claims[0],
                })
            return out
        ce._check_logic_basic = simple_logic

    elif config == "no_stat":
        # TERM层: 固定阈值替代统计校准
        original = ce._hybrid_sim
        def fixed_sim(a, b):
            if a == b:
                return 1.0
            # 简单编辑距离
            d = ce._levenshtein(a, b)
            return 1.0 - d / max(len(a), len(b)) if max(len(a), len(b)) > 0 else 0.0
        ce._hybrid_sim = staticmethod(fixed_sim)

    elif config == "no_llm":
        # LLM结果清空
        cache_path = os.path.join(BASE, "data/gjb_438c/llm_check_results")
        llm_cache = os.path.join(cache_path, f"{doc_num}.json")
        if os.path.exists(llm_cache):
            os.rename(llm_cache, llm_cache + ".bak")
            # 恢复在函数结束时

    elif config == "no_anchor":
        # mermaid_key清空
        for n in cg.docs[doc_num]["nodes"]:
            if n["type"] == "IMG":
                n["payload"]["mermaid_key"] = None

    # 执行检测
    r = ce.run(doc_num)
    return r


def evaluate_ablation(result):
    """从检测结果提取消融指标"""
    if not result.get("ok"):
        return None
    s = result["summary"]
    # 按层统计发现
    layer_findings = {"语法": 0, "语义": 0, "逻辑": 0}
    for i in result["items"]:
        if i["n_findings"] > 0:
            cat = i["category"]
            if "语法" in cat:
                layer_findings["语法"] += i["n_findings"]
            elif "语义" in cat:
                layer_findings["语义"] += i["n_findings"]
            elif "逻辑" in cat:
                layer_findings["逻辑"] += i["n_findings"]
    total_findings = sum(i["n_findings"] for i in result["items"])
    return {
        "pass": s["pass"], "warn": s["warn"], "fail": s["fail"],
        "llm": s["llm"],
        "total_findings": total_findings,
        "layer_findings": layer_findings,
        "active_items": sum(1 for i in result["items"] if i["status"] != "pass"),
    }


def main():
    configs = ["full", "no_z3", "no_graph", "no_stat", "no_llm", "no_anchor"]
    doc = "02"
    print("=" * 70)
    print(f"消融实验 (doc{doc})")
    print("=" * 70)

    # 先备份LLM缓存
    llm_path = os.path.join(BASE, "data/gjb_438c/llm_check_results", f"{doc}.json")
    backup = llm_path + ".ablation_bak"
    if os.path.exists(llm_path):
        import shutil
        shutil.copy(llm_path, backup)

    results = {}
    for cfg in configs:
        # 恢复LLM缓存(除非是no_llm消融)
        if cfg != "no_llm" and os.path.exists(backup):
            import shutil
            shutil.copy(backup, llm_path)

        r = run_ablation(doc, cfg)
        m = evaluate_ablation(r)
        results[cfg] = m
        if m:
            print(f"\n[{cfg:12s}] pass={m['pass']} warn={m['warn']} fail={m['fail']} "
                  f"llm={m['llm']} | 发现{m['total_findings']}条 "
                  f"(语{m['layer_findings']['语法']}/语{m['layer_findings']['语义']}"
                  f"/逻{m['layer_findings']['逻辑']})")
        else:
            print(f"\n[{cfg:12s}] FAILED")

    # 恢复LLM缓存
    if os.path.exists(backup):
        import shutil
        shutil.copy(backup, llm_path)
        os.remove(backup)

    # 输出对比表
    print("\n" + "=" * 70)
    print("消融对比表(相对full的变化)")
    print("=" * 70)
    full = results.get("full", {})
    if full:
        for cfg in configs[1:]:
            m = results.get(cfg, {})
            if not m:
                continue
            df = m["total_findings"] - full["total_findings"]
            dw = m["warn"] - full["warn"]
            dl = m["llm"] - full["llm"]
            print(f"  -{cfg[3:]:10s}: 发现数{'+' if df > 0 else ''}{df:4d} | "
                  f"warn{'+' if dw > 0 else ''}{dw:3d} | "
                  f"llm待{'+' if dl > 0 else ''}{dl:3d}")

    # 保存结果
    out = os.path.join(BASE, "data/gjb_438c/ablation_results.json")
    json.dump(results, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out}")


if __name__ == "__main__":
    main()
