"""Task 2: 基于原始SRS文本的变异算子 — 在真实文档内容上操作.

根因修复: 之前的算子在模板化pair上操作("该功能的表格包含「X」"),数值/顺序/操作符模式不存在.
正确做法: 回到原始chunks(MinerU解析的真实文本),在原始内容上做变异.

数据源:
  - table chunks(1207个,含HTML表格) → 提取约束/参数/功能
  - text chunks(3643个,正文文本) → 提取术语/条款
  - pair_dataset(366对) → 已配对的表格+图
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).parent.parent


def load_srs_corpus() -> list[dict]:
    """加载全部chunks,提取可操作的真实文本."""
    chunks = json.loads((BASE / "data/gjb_438c/data_assets/chunks/srs_chunks.json").read_text(encoding="utf-8"))
    return chunks


def extract_constraints(text: str) -> list[dict]:
    """从SRS文本中提取数值约束."""
    constraints = []
    # 从HTML表格中提取
    for m in re.finditer(r"<td><p>([^<]+)</p></td>", text):
        cell = m.group(1).strip()
        # 数值约束: "不大于Xms" / "不超过X秒" / "≥X%"
        cm = re.search(r"(不大于|不超过|不小于|不少于|至少|最多|≤|≥|>|<)\s*(\d+\.?\d*)\s*(ms|s|秒|min|分钟|GB|MB|KB|TB|%|条|个|次|种|类|套)", cell)
        if cm:
            # 找参数名(同一行前面的cell)
            context = text[max(0, m.start() - 200):m.start()]
            param_m = re.findall(r"<td><p>([^<]{2,12})</p></td>", context)
            param = param_m[-1].strip() if param_m else ""
            constraints.append({"param": param, "op": cm.group(1), "value": cm.group(2), "unit": cm.group(3), "text": cell})
    # 从纯文本中提取
    for m in re.finditer(r"([\u4e00-\u9fa5]{2,8})\s*(不大于|不超过|不小于|至少|最多)\s*(\d+\.?\d*)\s*(ms|s|秒|min|分钟|GB|MB|%)", text):
        constraints.append({"param": m.group(1), "op": m.group(2), "value": m.group(3), "unit": m.group(4), "text": m.group(0)})
    return constraints


def extract_terms(text: str) -> list[dict]:
    """从SRS文本中提取术语/功能名."""
    terms = []
    # 从功能表中提取功能名
    for m in re.finditer(r"<td><p>([\u4e00-\u9fa5A-Za-z]{2,15})[/\s<]", text):
        terms.append({"term": m.group(1), "context": text[max(0, m.start() - 50):m.start() + 50]})
    # 从用例表中提取用例名
    for m in re.finditer(r"Use Case 名称[：:]\s*([\u4e00-\u9fa5A-Za-z]{2,20})", text):
        terms.append({"term": m.group(1), "context": "usecase"})
    return terms


def extract_steps(text: str) -> list[dict]:
    """从SRS文本中提取步骤序列."""
    steps = []
    for m in re.finditer(r"步骤\s*(\d+)[：:]\s*([^\n<]{5,50})", text):
        steps.append({"num": int(m.group(1)), "content": m.group(2).strip()})
    return steps


def extract_interfaces(text: str) -> list[dict]:
    """从SRS文本中提取接口定义."""
    interfaces = []
    for m in re.finditer(r"<td><p>([\u4e00-\u9fa5A-Za-z]{2,20}接口)</p></td>", text):
        interfaces.append({"name": m.group(1)})
    return interfaces


def generate_variant_pairs(chunks: list[dict]) -> list[dict]:
    """从原始chunks生成变异pair(在真实文本上操作)."""
    variants = []

    for chunk in chunks:
        text = str(chunk.get("text", ""))
        doc = str(chunk.get("doc", ""))[:2]
        section = str(chunk.get("section", ""))

        # 1. 数值约束变异
        constraints = extract_constraints(text)
        for c in constraints:
            old_val = float(c["value"])
            new_val = old_val * 2
            if abs(new_val - old_val) < 0.01:
                continue
            premise = f"{doc}文档{section}节规定{c['param']}{c['op']}{c['value']}{c['unit']}"
            hypothesis = f"{doc}文档{section}节规定{c['param']}{c['op']}{new_val:g}{c['unit']}"
            variants.append({
                "premise": premise, "hypothesis": hypothesis,
                "label": "inconsistent", "type": "PARAM-01",
                "doc": doc, "section": section,
                "operator": "param_shift",
                "original": f"{c['op']}{c['value']}{c['unit']}",
                "mutated": f"{c['op']}{new_val:g}{c['unit']}",
            })

        # 2. 操作符翻转
        for c in constraints:
            op_flips = {"不大于": "不小于", "不超过": "不少于", "≤": "≥", "≥": "≤"}
            if c["op"] in op_flips:
                new_op = op_flips[c["op"]]
                premise = f"{doc}文档{section}节规定{c['param']}{c['op']}{c['value']}{c['unit']}"
                hypothesis = f"{doc}文档{section}节规定{c['param']}{new_op}{c['value']}{c['unit']}"
                variants.append({
                    "premise": premise, "hypothesis": hypothesis,
                    "label": "inconsistent", "type": "PARAM-06",
                    "doc": doc, "section": section,
                    "operator": "op_flip",
                    "original": f"{c['op']}{c['value']}{c['unit']}",
                    "mutated": f"{new_op}{c['value']}{c['unit']}",
                })

        # 3. 术语同义异名
        SYNONYMS = {"获取": "采集", "传输": "传送", "查询": "检索", "监控": "监视"}
        terms = extract_terms(text)
        for t in terms:
            for old, new in SYNONYMS.items():
                if old in t["term"]:
                    premise = f"{doc}文档{section}节规定「{t['term']}」"
                    new_term = t["term"].replace(old, new)
                    hypothesis = f"{doc}文档{section}节规定「{new_term}」"
                    variants.append({
                        "premise": premise, "hypothesis": hypothesis,
                        "label": "inconsistent", "type": "TERM-01",
                        "doc": doc, "section": section,
                        "operator": "term_swap",
                        "original": t["term"], "mutated": new_term,
                    })

        # 4. 步骤顺序变异
        steps = extract_steps(text)
        if len(steps) >= 2:
            s1, s2 = steps[0], steps[1]
            premise = f"表格规定执行顺序: 步骤{s1['num']}({s1['content'][:15]})→步骤{s2['num']}({s2['content'][:15]})"
            hypothesis = f"图中规定执行顺序: 步骤{s2['num']}({s2['content'][:15]})→步骤{s1['num']}({s1['content'][:15]})"
            variants.append({
                "premise": premise, "hypothesis": hypothesis,
                "label": "inconsistent", "type": "ORDER_CONFLICT",
                "doc": doc, "section": section,
                "operator": "order_swap",
                "original": f"{s1['num']}→{s2['num']}", "mutated": f"{s2['num']}→{s1['num']}",
            })

        # 5. 步骤删除
        for s in steps:
            premise = f"表格规定步骤{s['num']}: {s['content'][:30]}"
            hypothesis = f"表格中没有步骤{s['num']}对应的节点"
            variants.append({
                "premise": premise, "hypothesis": hypothesis,
                "label": "inconsistent", "type": "STEP_MISSING",
                "doc": doc, "section": section,
                "operator": "step_remove",
                "original": f"步骤{s['num']}", "mutated": "(删除)",
            })

        # 6. GJB可测试性违规
        GJB_VAGUE = ["系统应运行稳定", "系统应性能良好", "系统应可靠"]
        if len(text) > 50:
            for vague in GJB_VAGUE:
                premise = f"{doc}文档{section}节描述: {text[:80]}"
                hypothesis = f"{doc}文档{section}节描述: {text[:80]} {vague}。"
                variants.append({
                    "premise": premise, "hypothesis": hypothesis,
                    "label": "inconsistent", "type": "GJB-01",
                    "doc": doc, "section": section,
                    "operator": "gjb_vague",
                    "original": "(原始描述)", "mutated": vague,
                })
                break  # 每个chunk只生成1条

    return variants


def main() -> None:
    chunks = load_srs_corpus()
    print(f"加载chunks: {len(chunks)}条")

    variants = generate_variant_pairs(chunks)
    from collections import Counter
    types = Counter(v["type"] for v in variants)
    docs = Counter(v["doc"] for v in variants)

    print(f"\n生成变异pair: {len(variants)}条")
    print(f"类型分布: {dict(sorted(types.items()))}")
    print(f"文档覆盖: {len(docs)}份")

    # 保存
    out = BASE / "data/gjb_438c/qa_dataset_v3_variants.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"total": len(variants), "variants": variants}, f, ensure_ascii=False, indent=1)
    print(f"保存 → {out}")


if __name__ == "__main__":
    main()
