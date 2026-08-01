#!/usr/bin/env python3
"""
SRS DataFlow Integration: 多模态冲突检验 + 上下文关联
基于 DataFlow 生态的真实API，在SRS文档上运行冲突检测和知识图谱构建。

使用方法:
  ~/dataflow-env/bin/python tools/srs_dataflow_integration.py

依赖:
  - ~/dataflow-env (Python 3.12 + open-dataflow + dataflow-kg)
  - DF_API_KEY 环境变量 (GLM-5 API key)
  - MinerU已解析的SRS文档 (data/gjb_438c/mineru_srs/)
"""

import os
import sys
import json
import time
from pathlib import Path

# ============================================================
# 1. 环境配置
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
MINERU_SRS_DIR = REPO_ROOT / "data" / "gjb_438c" / "mineru_srs"
OUTPUT_DIR = REPO_ROOT / "data" / "gjb_438c" / "dataflow_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
API_KEY = os.environ.get("DF_API_KEY", "n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7")
MODEL_NAME = "ep-glsztk-1778496696841467392"

os.environ["DF_API_KEY"] = API_KEY

# DataFlow imports (LazyLoader模式: 从父模块导入类名)
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage
from dataflow.core import OperatorABC
from dataflow.pipeline import PipelineABC
from dataflow.utils.registry import OPERATOR_REGISTRY

print("✅ DataFlow imports successful")


# ============================================================
# 2. MinerU输出加载器
# ============================================================

def _extract_text_from_block(block: dict) -> str:
    """从MinerU block中提取文本（lines[].spans[].content拼接）。"""
    parts = []
    for line in block.get("lines", []):
        for span in line.get("spans", []):
            content = span.get("content", "")
            if content:
                parts.append(content)
    return " ".join(parts)


def _extract_table_html(block: dict) -> str:
    """从MinerU table block中提取HTML。table_body的spans中type=table的html字段。"""
    html = ""
    caption = ""
    for sub in block.get("blocks", []):
        sub_type = sub.get("type", "")
        if sub_type == "table_caption":
            caption = _extract_text_from_block(sub)
        elif sub_type == "table_body":
            for line in sub.get("lines", []):
                for span in line.get("spans", []):
                    if span.get("type") == "table" and span.get("html"):
                        html = span["html"]
                        break
    return html, caption


def load_mineru_output(doc_name: str) -> dict:
    """加载MinerU解析结果，返回结构化数据。"""
    pdf_dir = MINERU_SRS_DIR / f"{doc_name}.pdf" / "auto"
    middle_json_path = pdf_dir / f"{doc_name}.pdf_middle.json"
    md_path = pdf_dir / f"{doc_name}.pdf.md"
    images_dir = pdf_dir / "images"

    if not middle_json_path.exists():
        raise FileNotFoundError(f"MinerU output not found: {middle_json_path}")

    with open(middle_json_path, "r", encoding="utf-8") as f:
        middle_data = json.load(f)

    md_text = ""
    if md_path.exists():
        md_text = md_path.read_text(encoding="utf-8")

    pdf_info = middle_data.get("pdf_info", [])

    sections = []
    tables = []
    images = []
    formulas = []

    for page_idx, page in enumerate(pdf_info):
        page_no = page.get("page_idx", page_idx)
        # MinerU uses para_blocks (or preproc_blocks)
        blocks = page.get("para_blocks", page.get("preproc_blocks", []))

        for block in blocks:
            block_type = block.get("type", "")

            if block_type in ("text", "title"):
                text = _extract_text_from_block(block)
                if text.strip():
                    sections.append({
                        "page": page_no,
                        "type": block_type,
                        "text": text,
                        "bbox": block.get("bbox", []),
                    })

            elif block_type == "table":
                html, caption = _extract_table_html(block)
                tables.append({
                    "page": page_no,
                    "type": "table",
                    "html": html,
                    "caption": caption,
                    "bbox": block.get("bbox", []),
                })

            elif block_type == "image":
                img_path = ""
                for sub in block.get("blocks", []):
                    if sub.get("type") == "image_body":
                        for line in sub.get("lines", []):
                            for span in line.get("spans", []):
                                if span.get("type") == "image":
                                    img_path = span.get("image_path", span.get("content", ""))
                caption = ""
                for sub in block.get("blocks", []):
                    if sub.get("type") == "image_caption":
                        caption = _extract_text_from_block(sub)
                images.append({
                    "page": page_no,
                    "type": "image",
                    "path": str(images_dir / img_path) if img_path else "",
                    "caption": caption,
                    "bbox": block.get("bbox", []),
                })

            elif block_type in ("equation", "interline_equation"):
                latex = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        c = span.get("content", "")
                        if c:
                            latex = c
                if latex.strip():
                    formulas.append({
                        "page": page_no,
                        "type": "formula",
                        "latex": latex,
                        "bbox": block.get("bbox", []),
                    })

    result = {
        "doc_name": doc_name,
        "markdown": md_text,
        "sections": sections,
        "tables": tables,
        "images": images,
        "formulas": formulas,
        "total_pages": len(pdf_info),
    }

    print(f"  📄 {doc_name}: {len(sections)} text blocks, {len(tables)} tables, "
          f"{len(images)} images, {len(formulas)} formulas")
    return result


# ============================================================
# 3. SRS专用DataFlow算子
# ============================================================

class SRSConstraintExtractor(OperatorABC):
    """从SRS文本中提取约束（使用GLM-5 API）。"""
    
    def __init__(self, llm_serving):
        self.llm_serving = llm_serving
    
    def run(self, storage, input_key="sections", output_key="constraints"):
        data = storage.read(input_key)
        constraints = []
        
        prompts = []
        for section in data:
            text = section.get("text", "")
            if len(text) < 20:
                continue
            prompt = f"""请从以下SRS文本中提取所有约束条件，输出JSON数组。每条约束包含type, param, operator, value, unit, original字段。
约束类型: numerical(数值), tolerance(容差), temporal(时序), conditional(条件), default(默认值), design(设计参数)

文本: {text[:2000]}

只输出JSON数组:"""
            prompts.append(prompt)
        
        if prompts:
            results = self.llm_serving.generate_from_input(
                user_inputs=prompts,
                system_prompt="你是SRS文档分析专家。只输出JSON。"
            )
            for i, result in enumerate(results):
                if result:
                    try:
                        import json_repair
                        items = json_repair.loads(result)
                        if isinstance(items, list):
                            for item in items:
                                item["source_section_idx"] = i
                                constraints.append(item)
                    except Exception:
                        pass
        
        storage.write(constraints, output_key)
        return constraints


class SRSMultimodalConflictDetector(OperatorABC):
    """检测文本-表格-图片之间的多模态冲突。"""
    
    def __init__(self, llm_serving):
        self.llm_serving = llm_serving
    
    def run(self, storage, input_key="constraints", output_key="conflicts"):
        constraints = storage.read(input_key)
        tables = storage.read("tables") if "tables" in storage.read_keys() else []
        
        conflicts = []
        
        # 策略1: 约束vs表格数值冲突
        if constraints and tables:
            for constraint in constraints:
                param = constraint.get("param", "")
                value = constraint.get("value", "")
                operator = constraint.get("operator", "")
                unit = constraint.get("unit", "")
                
                if not param or not value:
                    continue
                
                prompt = f"""请检查以下约束与表格数据是否一致。

约束: {param} {operator} {value} {unit}
约束原文: {constraint.get('original', '')}

表格数据(HTML):
{tables[0].get('html', '')[:3000]}

如果不一致，输出JSON: {{"conflict": true, "reason": "...", "constraint": "...", "table_value": "..."}}
如果一致，输出: {{"conflict": false}}

只输出JSON:"""
                
                result = self.llm_serving.generate_from_input(
                    user_inputs=[prompt],
                    system_prompt="你是SRS一致性检测专家。只输出JSON。"
                )
                
                if result and result[0]:
                    try:
                        import json_repair
                        item = json_repair.loads(result[0])
                        if isinstance(item, dict) and item.get("conflict"):
                            item["conflict_type"] = "text_table"
                            item["constraint"] = constraint
                            conflicts.append(item)
                            print(f"  ⚠️ 冲突发现: {param} {operator} {value} vs 表格")
                    except Exception:
                        pass
        
        # 策略2: 约束间冲突检测
        if len(constraints) > 1:
            for i in range(len(constraints)):
                for j in range(i + 1, len(constraints)):
                    c1, c2 = constraints[i], constraints[j]
                    if c1.get("param") == c2.get("param") and c1.get("param"):
                        if c1.get("value") != c2.get("value"):
                            conflicts.append({
                                "conflict_type": "constraint_constraint",
                                "constraint_1": c1,
                                "constraint_2": c2,
                                "reason": f"参数'{c1['param']}'在不同位置有不同值: {c1.get('value')} vs {c2.get('value')}"
                            })
                            print(f"  ⚠️ 约束冲突: {c1['param']} = {c1.get('value')} vs {c2.get('value')}")
        
        storage.write(conflicts, output_key)
        return conflicts


class SRSTripleExtractor(OperatorABC):
    """从SRS文本中提取知识图谱三元组（用于上下文关联）。"""
    
    def __init__(self, llm_serving):
        self.llm_serving = llm_serving
    
    def run(self, storage, input_key="sections", output_key="triples"):
        data = storage.read(input_key)
        all_triples = []
        
        prompts = []
        for section in data:
            text = section.get("text", "")
            if len(text) < 20:
                continue
            prompt = f"""请从以下SRS文本中提取知识图谱三元组，格式为JSON数组，每个元素为 {{"head": "...", "relation": "...", "tail": "..."}}。

关系类型包括: contains(包含), requires(需要), constrains(约束), references(引用), implements(实现), interfaces_with(接口), depends_on(依赖)

文本: {text[:2000]}

只输出JSON数组:"""
            prompts.append(prompt)
        
        if prompts:
            results = self.llm_serving.generate_from_input(
                user_inputs=prompts,
                system_prompt="你是知识图谱构建专家。只输出JSON。"
            )
            for i, result in enumerate(results):
                if result:
                    try:
                        import json_repair
                        items = json_repair.loads(result)
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict) and "head" in item and "relation" in item and "tail" in item:
                                    item["source_section"] = i
                                    all_triples.append(item)
                    except Exception:
                        pass
        
        storage.write(all_triples, output_key)
        print(f"  📊 提取三元组: {len(all_triples)} 条")
        return all_triples


class SRSContextAssociator(OperatorABC):
    """基于三元组构建上下文关联，识别"应该一致"的数据组。"""
    
    def __init__(self):
        pass
    
    def run(self, storage, input_key="triples", output_key="associations"):
        triples = storage.read(input_key)
        
        # 构建邻接表
        import networkx as nx
        G = nx.MultiDiGraph()
        for t in triples:
            G.add_edge(t["head"], t["tail"], relation=t["relation"], source=t.get("source_section", -1))
        
        # 发现关联组：同一实体的所有邻居应该一致
        associations = []
        for node in G.nodes():
            neighbors = list(G.successors(node)) + list(G.predecessors(node))
            if len(neighbors) >= 2:
                # 检查这个节点是否有多个关联实体
                assoc = {
                    "entity": node,
                    "related": list(set(neighbors)),
                    "relation_count": len(neighbors),
                }
                associations.append(assoc)
        
        # 按关联数排序
        associations.sort(key=lambda x: x["relation_count"], reverse=True)
        
        storage.write(associations, output_key)
        print(f"  🔗 发现关联组: {len(associations)} 个")
        print(f"  📈 图谱: {G.number_of_nodes()} 节点, {G.number_of_edges()} 边")
        return associations


# ============================================================
# 4. SimpleStorage (简化版，不依赖DataFlow Pipeline编译)
# ============================================================

class SimpleStorage:
    """简化存储，用于直接调用算子。"""
    def __init__(self):
        self._data = {}
    def write(self, data, key):
        self._data[key] = data
    def read(self, key):
        return self._data.get(key, [])
    def read_keys(self):
        return list(self._data.keys())
    def step(self):
        return self


# ============================================================
# 5. 主流程
# ============================================================

def main():
    print("=" * 60)
    print("SRS DataFlow Integration: 多模态冲突检验 + 上下文关联")
    print("=" * 60)
    
    # 5.1 配置LLM
    print("\n📋 1. 配置GLM-5 LLM Serving...")
    llm = APILLMServing_request(
        api_url=API_URL,
        key_name_of_api_key="DF_API_KEY",
        model_name=MODEL_NAME,
        max_workers=5,
    )
    print("  ✅ LLM configured")
    
    # 5.2 加载已解析的SRS文档
    print("\n📋 2. 加载MinerU已解析的SRS文档...")
    documents = {}
    for doc_name in ["battery_srs", "compiler_srs", "scheduler_srs"]:
        try:
            doc = load_mineru_output(doc_name)
            documents[doc_name] = doc
        except FileNotFoundError as e:
            print(f"  ⚠️ Skip {doc_name}: {e}")
    
    if not documents:
        print("❌ No documents found. Run MinerU first.")
        return
    
    # 5.3 对每个文档运行冲突检测 + 三元组提取
    all_results = {}
    
    for doc_name, doc_data in documents.items():
        print(f"\n{'='*60}")
        print(f"📋 3. 处理文档: {doc_name}")
        print(f"{'='*60}")
        
        storage = SimpleStorage()
        storage.write(doc_data["sections"], "sections")
        storage.write(doc_data["tables"], "tables")
        storage.write(doc_data["images"], "images")
        storage.write(doc_data["formulas"], "formulas")
        
        # 3.1 约束提取
        print(f"\n  🔍 3.1 约束提取...")
        t0 = time.time()
        extractor = SRSConstraintExtractor(llm)
        constraints = extractor.run(storage, input_key="sections", output_key="constraints")
        print(f"  ✅ 提取约束: {len(constraints)} 条 ({time.time()-t0:.1f}s)")
        
        # 3.2 多模态冲突检测
        print(f"\n  🔍 3.2 多模态冲突检测...")
        t0 = time.time()
        detector = SRSMultimodalConflictDetector(llm)
        conflicts = detector.run(storage, input_key="constraints", output_key="conflicts")
        print(f"  ✅ 检测冲突: {len(conflicts)} 个 ({time.time()-t0:.1f}s)")
        
        # 3.3 三元组提取 (知识图谱构建)
        print(f"\n  🔍 3.3 知识图谱三元组提取...")
        t0 = time.time()
        triple_extractor = SRSTripleExtractor(llm)
        triples = triple_extractor.run(storage, input_key="sections", output_key="triples")
        print(f"  ✅ 提取三元组: {len(triples)} 条 ({time.time()-t0:.1f}s)")
        
        # 3.4 上下文关联
        print(f"\n  🔍 3.4 上下文关联分析...")
        associator = SRSContextAssociator()
        associations = associator.run(storage, input_key="triples", output_key="associations")
        
        # 3.5 保存结果
        result = {
            "doc_name": doc_name,
            "total_pages": doc_data["total_pages"],
            "sections_count": len(doc_data["sections"]),
            "tables_count": len(doc_data["tables"]),
            "images_count": len(doc_data["images"]),
            "formulas_count": len(doc_data["formulas"]),
            "constraints": constraints,
            "conflicts": conflicts,
            "triples": triples,
            "associations": associations[:20],  # top 20
        }
        
        output_path = OUTPUT_DIR / f"{doc_name}_dataflow_result.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n  💾 结果已保存: {output_path}")
        
        all_results[doc_name] = result
    
    # 5.4 汇总报告
    print(f"\n{'='*60}")
    print(f"📊 汇总报告")
    print(f"{'='*60}")
    print(f"{'文档':<20} {'约束':>6} {'冲突':>6} {'三元组':>8} {'关联组':>8}")
    print(f"{'-'*50}")
    for doc_name, result in all_results.items():
        print(f"{doc_name:<20} {len(result['constraints']):>6} {len(result['conflicts']):>6} "
              f"{len(result['triples']):>8} {len(result['associations']):>8}")
    
    # 5.5 保存汇总
    summary_path = OUTPUT_DIR / "summary.json"
    summary = {
        doc_name: {
            "constraints": len(r["constraints"]),
            "conflicts": len(r["conflicts"]),
            "triples": len(r["triples"]),
            "associations": len(r["associations"]),
        }
        for doc_name, r in all_results.items()
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n💾 汇总已保存: {summary_path}")
    print(f"\n✅ 全部完成!")


if __name__ == "__main__":
    main()
