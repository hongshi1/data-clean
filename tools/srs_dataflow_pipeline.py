#!/usr/bin/env python3
"""
SRS DataFlow Pipeline - 优化版
分步骤执行，每步保存中间结果，避免超时。
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DF_API_KEY'] = 'n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7'

from srs_dataflow_integration import load_mineru_output
from dataflow.serving import APILLMServing_request
import json_repair, networkx as nx
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "gjb_438c" / "dataflow_output"
OUT.mkdir(parents=True, exist_ok=True)

llm = APILLMServing_request(
    api_url="https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions",
    key_name_of_api_key="DF_API_KEY",
    model_name="ep-glsztk-1778496696841467392",
    max_workers=3,
)

def parse_llm_response(raw):
    """Parse LLM response that may contain <think>/<answer> tags."""
    if not raw:
        return []
    # GLM-5 returns <think>...</think><answer>...</answer> format
    # Extract content after <answer> tag or find JSON array directly
    import re
    # Try to extract from <answer> tag first
    answer_match = re.search(r'<answer>(.*?)</answer>', raw, re.DOTALL)
    if answer_match:
        raw = answer_match.group(1).strip()
    # Remove <think> blocks
    raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
    # Try to find JSON array in the text
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)
    # Parse with json_repair
    try:
        result = json_repair.loads(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
    except Exception:
        pass
    return []

def call_api(prompt, system="你是SRS分析专家。只输出JSON，不要思考过程。"):
    """Single API call with error handling."""
    try:
        r = llm.generate_from_input([prompt[:6000]], system)
        if r and r[0]:
            return parse_llm_response(r[0])
    except Exception as e:
        print(f"  API error: {e}")
    return []

def select_req_sections(doc):
    """Select sections with actual requirements."""
    return [s for s in doc["sections"] if s["page"] >= 5 and len(s["text"]) > 30
            and any(kw in s["text"] for kw in
                    ["需求","应","必须","≤","≥","不超过","约束","规定","性能","接口","输入","输出","ms","周期","函数","参数","范围","时间"])]

def step1_constraints(doc_name, sections):
    """Extract constraints from sections."""
    print(f"\n[Step 1] Constraint extraction for {doc_name}...")
    text = "\n".join([s["text"][:300] for s in sections])[:4000]
    prompt = f"""提取以下SRS文本中的所有约束条件。输出JSON数组，每条含type,param,operator,value,unit,original。
类型: numerical(数值≤≥), tolerance(±容差), temporal(时序), conditional(条件), default(默认值), design(设计约束)

文本:
{text}

只输出JSON数组:"""
    t0 = time.time()
    items = call_api(prompt)
    constraints = [c for c in items if isinstance(c, dict)]
    print(f"  ✅ {len(constraints)} constraints ({time.time()-t0:.0f}s)")
    for c in constraints[:8]:
        print(f"    {c.get('type','?'):12s} {c.get('param',''):20s} {c.get('operator','')} {c.get('value','')} {c.get('unit','')}")
    return constraints

def step2_conflicts(doc_name, constraints, tables):
    """Detect text-table and constraint-constraint conflicts."""
    print(f"\n[Step 2] Conflict detection for {doc_name}...")
    all_conflicts = []

    # 2a: Constraint-constraint (local, no API)
    for i in range(len(constraints)):
        for j in range(i+1, len(constraints)):
            c1, c2 = constraints[i], constraints[j]
            if c1.get("param") and c1["param"] == c2.get("param") and c1.get("value") != c2.get("value"):
                all_conflicts.append({"type": "param_conflict", "param": c1["param"],
                                      "val1": c1.get("value"), "val2": c2.get("value"),
                                      "reason": f"{c1['param']}: {c1.get('value')} vs {c2.get('value')}"})
                print(f"  ⚠️ param conflict: {c1['param']}={c1.get('value')} vs {c2.get('value')}")

    # 2b: Text-table (API)
    table_html = "".join([t["html"] for t in tables if t.get("html") and len(t["html"]) > 50])[:3000]
    if table_html and constraints:
        csum = "\n".join([f"- {c.get('param','')} {c.get('operator','')} {c.get('value','')} {c.get('unit','')}" for c in constraints[:15]])
        prompt = f"""检查以下SRS约束与表格数据是否一致。对每个冲突输出JSON: {{"param":"","constraint_value":"","table_value":"","reason":""}}
无冲突则输出 []

约束:
{csum}

表格HTML:
{table_html}

只输出JSON数组:"""
        t0 = time.time()
        items = call_api(prompt, "你是SRS一致性检测专家。只输出JSON。")
        for c in items:
            if isinstance(c, dict) and c.get("param"):
                c["type"] = "text_table_conflict"
                all_conflicts.append(c)
                print(f"  ⚠️ text-table: {c.get('param')} 约束={c.get('constraint_value')} vs 表格={c.get('table_value')}")
        print(f"  text-table check done ({time.time()-t0:.0f}s)")

    print(f"  Total conflicts: {len(all_conflicts)}")
    return all_conflicts

def step3_triples(doc_name, sections):
    """Extract KG triples."""
    print(f"\n[Step 3] Triple extraction for {doc_name}...")
    text = "\n".join([s["text"][:300] for s in sections])[:4000]
    prompt = f"""提取知识图谱三元组。输出JSON数组，每个: {{"head":"","relation":"","tail":""}}
关系: contains,requires,constrains,references,implements,interfaces_with,depends_on,outputs,inputs

文本:
{text}

只输出JSON数组:"""
    t0 = time.time()
    items = call_api(prompt, "你是知识图谱专家。只输出JSON。")
    triples = [t for t in items if isinstance(t, dict) and "head" in t and "relation" in t and "tail" in t]
    print(f"  ✅ {len(triples)} triples ({time.time()-t0:.0f}s)")
    for t in triples[:8]:
        print(f"    {t['head']:20s} --{t['relation']:15s}--> {t['tail']}")
    return triples

def step4_associations(triples):
    """Build context associations from triples."""
    print(f"\n[Step 4] Context association...")
    G = nx.MultiDiGraph()
    for t in triples:
        G.add_edge(t["head"], t["tail"], relation=t["relation"])
    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    assocs = []
    for node in G.nodes():
        neighbors = list(set(list(G.successors(node)) + list(G.predecessors(node))))
        if len(neighbors) >= 2:
            assocs.append({"entity": node, "related": neighbors, "count": len(neighbors)})
    assocs.sort(key=lambda x: x["count"], reverse=True)
    print(f"  {len(assocs)} association groups")
    for a in assocs[:5]:
        print(f"    [{a['count']}] {a['entity']} -> {a['related'][:4]}")
    return assocs

def process_doc(doc_name):
    """Process a single document through all steps."""
    print(f"\n{'='*60}")
    print(f"Processing: {doc_name}")
    print(f"{'='*60}")

    doc = load_mineru_output(doc_name)
    sections = select_req_sections(doc)
    print(f"  {len(sections)} requirement sections selected (pages 5+)")

    if not sections:
        print("  ⚠️ No requirement sections found, skipping")
        return None

    # Run steps
    constraints = step1_constraints(doc_name, sections)
    save_intermediate(doc_name, "constraints", constraints)

    conflicts = step2_conflicts(doc_name, constraints, doc["tables"])
    save_intermediate(doc_name, "conflicts", conflicts)

    triples = step3_triples(doc_name, sections)
    save_intermediate(doc_name, "triples", triples)

    assocs = step4_associations(triples)

    # Final result
    result = {
        "doc": doc_name,
        "total_pages": doc["total_pages"],
        "sections_used": len(sections),
        "tables_found": len(doc["tables"]),
        "constraints": constraints,
        "conflicts": conflicts,
        "triples": triples,
        "associations": assocs[:20],
    }
    out_path = OUT / f"{doc_name}_dataflow_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  💾 Saved: {out_path}")
    return result

def save_intermediate(doc_name, step, data):
    """Save intermediate results for resume capability."""
    p = OUT / f"{doc_name}_{step}.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 60)
    print("SRS DataFlow Pipeline (Optimized)")
    print("=" * 60)

    all_results = {}
    for doc_name in ["battery_srs", "compiler_srs", "scheduler_srs"]:
        try:
            result = process_doc(doc_name)
            if result:
                all_results[doc_name] = result
        except Exception as e:
            print(f"\n❌ Error processing {doc_name}: {e}")
            import traceback; traceback.print_exc()

    # Summary
    print(f"\n{'='*60}")
    print("📊 Summary")
    print(f"{'='*60}")
    print(f"{'Document':<20} {'Constraints':>12} {'Conflicts':>10} {'Triples':>10} {'Assocs':>8}")
    print("-" * 62)
    for name, r in all_results.items():
        print(f"{name:<20} {len(r['constraints']):>12} {len(r['conflicts']):>10} {len(r['triples']):>10} {len(r['associations']):>8}")

    summary = {n: {"constraints": len(r["constraints"]), "conflicts": len(r["conflicts"]),
                   "triples": len(r["triples"]), "associations": len(r["associations"])}
               for n, r in all_results.items()}
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Summary saved: {OUT / 'summary.json'}")
    print("✅ Done!")

if __name__ == "__main__":
    main()
