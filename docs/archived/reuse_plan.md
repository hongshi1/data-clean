# SRS一致性检测Agent——最大程度复用方案

> 核心原则: 能复用的不改，能改配置的不写代码，必须写的要有源码参考
> 每个模块标注: [直接复用] / [改配置] / [最小改造] / [必须新写]

---

## 一、复用清单总览

| 模块 | 复用方式 | 源码参考 | 我们要做什么 |
|------|---------|---------|------------|
| **三阶段流水线引擎** | [直接复用] | AgentFlow `synthesis/pipeline.py` | 不改一行代码 |
| **轨迹采样器** | [直接复用] | AgentFlow `synthesis/core/sampler.py` | 不改一行代码 |
| **轨迹选择器** | [直接复用] | AgentFlow `synthesis/core/selector.py` | 不改一行代码 |
| **报告合成器** | [直接复用] | AgentFlow `synthesis/core/synthesizer.py` | 不改一行代码 |
| **动作去重** | [直接复用] | AgentFlow `sampler.py:320` | 不改 |
| **质量检查** | [直接复用] | AgentFlow `synthesizer.py:65-123` | 不改 |
| **Sandbox框架** | [直接复用] | AgentFlow `sandbox/` | 不改 |
| **工具注册机制** | [直接复用] | AgentFlow `sandbox/server/core/tool_executor.py` | 不改 |
| **LLM调用层** | [直接复用] | DataFlow `serving/api_llm_serving_request.py` | 不改，改api_url |
| **Storage层** | [直接复用] | DataFlow `utils/storage.py FileStorage` | 不改 |
| **Pipeline编排** | [直接复用] | DataFlow `pipeline/Pipeline.py` | 不改 |
| **配置加载** | [直接复用] | AgentFlow `sandbox/server/config_loader.py` | 不改 |
| **一致性检测Prompt** | [改配置] | DataFlow-KG `prompts/consistency.py` | 移植prompt模板，改SRS领域词 |
| **NLI判断Prompt** | [改配置] | DataFlow-KG `prompts/hallucination.py` | 移植prompt模板 |
| **Sampling配置** | [改配置] | AgentFlow `configs/synthesis/doc_config.json` | 仿照写srs_config.json |
| **Synthesis配置** | [改配置] | AgentFlow `configs/synthesis/doc_config.json` | 仿照写srs_check.json |
| **SRS文档解析** | [最小改造] | DocDancer `PDF_preprocess/3_get_outline_and_root.py` | 改输入格式(md→xml) |
| **SRS检索工具** | [最小改造] | DocDancer `sandbox/.../doc_tool.py:436` | 改数据源(SRS章节) |
| **SRS读取工具** | [最小改造] | DocDancer `sandbox/.../doc_tool.py:575` | 改输出格式 |
| **Z3校验工具** | [必须新写] | 无（AgentFlow/DataFlow均无Z3） | 参考z3-py文档 |
| **语法Lint工具** | [必须新写] | 无 | 参考GJB规则 |

**统计**: 直接复用12个模块 / 改配置4个 / 最小改造3个 / 必须新写2个

---

## 二、[直接复用] 模块详解——这些不改一行代码

### 2.1 AgentFlow三阶段引擎

**直接import使用，不改任何代码**：

```python
# 我们的主入口脚本 (tools/srs_detect.py)
from synthesis import synthesize  # ← AgentFlow的函数，直接import
from rollout import pipeline      # ← AgentFlow的函数，直接import

# 阶段A+B+C全部由AgentFlow的synthesize完成
# 我们只传config路径
synthesize(config_path="configs/synthesis/srs_config.json")
```

**AgentFlow的synthesize内部做了什么**（我们不需要改，但需要理解）：

```
synthesize() → SynthesisPipeline.run_async()  (pipeline.py:66)
    │
    ├─ 对每个seed:
    │   ├─ 重建sandbox session  (pipeline.py:110-143)
    │   ├─ TrajectorySampler.sample_trajectory_tree()  (sampler.py:20)
    │   │   └─ 循环: LLM生成动作 → 执行工具 → 记录观察 → 去重 → 递归
    │   ├─ TrajectorySelector.select_trajectories()  (selector.py:25)
    │   │   └─ 叶→根回溯 → 打分(深度+信息量+多样性) → 去相似
    │   └─ QASynthesizer.synthesize_qa()  (synthesizer.py:27)
    │       └─ LLM生成报告 → 质量检查(≥3 hops, evidence grounded) → 重试
    │
    └─ 输出: synthesized_qa.jsonl + trajectories.jsonl
```

**为什么能直接复用**：AgentFlow把领域知识全部外置到config的`sampling_tips`/`synthesis_tips`/`available_tools`，sampler/selector/synthesizer的代码完全通用。

### 2.2 DataFlow的LLM调用层

**直接复用APILLMServing_request**：

```python
# 我们的config中直接引用DataFlow的LLM Serving
from dataflow.serving import APILLMServing_request

llm_serving = APILLMServing_request(
    api_url="https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions",
    key_name_of_api_key="GLM_API_KEY",  # export GLM_API_KEY=xxx
    model_name="ep-glsztk-1778496696841467392",
    max_workers=20,  # 并发20个LLM调用
)
```

**复用的功能**（来自`api_llm_serving_request.py:14-302`）：
- ThreadPoolExecutor并发（max_workers=20）
- 指数退避重试（max_retries=5, sleep 2^i秒）
- 连接池（HTTPAdapter, pool_maxsize=max_workers）
- API key从环境变量读取（安全）
- 支持json_schema结构化输出
- 支持`<think>...</think><answer>...</answer>`格式

### 2.3 DataFlow的Storage层

**直接复用FileStorage的step()机制**：

```python
from dataflow.utils.storage import FileStorage

storage = FileStorage(
    first_entry_file_name="srs_input.jsonl",  # [{doc_id, doc_path}]
    cache_path="./.cache/srs_check",
    file_name_prefix="srs_step",
    cache_type="jsonl",
)

# 每个算子调用 storage.step() 自动管理中间状态
# step0=srs_input.jsonl → step1=解析输出 → step2=聚合输出 → step3=检测输出...
# 可断点续跑: pipeline.forward(resume_step=2)
```

---

## 三、[改配置] 模块详解——只改配置文件，不改代码

### 3.1 上下文关联配置（仿doc_config.json）

**参考**: AgentFlow `configs/synthesis/doc_config.json`

**我们的配置** `configs/synthesis/srs_aggregate.json`：

```json
{
  "model": {
    "name": "glm-5",
    "api_key_env": "GLM_API_KEY",
    "base_url": "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
  },
  "max_depth": 15,
  "branching_factor": 3,
  "depth_threshold": 3,
  "available_tools": ["srs:search", "srs:read_section", "srs:read_table"],
  
  "sampling_tips": [
    "你的任务是聚合SRS文档中描述同一需求实体的所有相关信息",
    "对每个需求实体(功能/参数/接口)，用srs:search找到所有出现位置",
    "用srs:read_section读取每个位置的详细内容",
    "用srs:read_table读取合格性表和追溯表中对应的行",
    "一条轨迹=一个需求实体的完整跨章节证据链",
    "需求ID可能不一致(如SJCS/SJCSKZ/SJSF三个ID指同一需求)，需要归一化",
    "章节号可能系统性偏移(第4章比第3章整体+1)，需要容错匹配",
    "图片为OLE嵌入对象，只能通过章节归属关联"
  ],
  
  "resource_types": ["srs"],
  "resource_init_configs": {
    "srs": {
      "outline_path": "data/srs_outline/{doc_id}_outline.xml",
      "content_path": "data/srs_outline/{doc_id}_content.xml"
    }
  },
  
  "seeds_file": "seeds/srs_seeds.jsonl"
}
```

**与doc_config.json的diff**：

| 字段 | doc_config.json (原) | srs_aggregate.json (我们) |
|------|---------------------|------------------------|
| available_tools | ["doc-search","doc-read"] | ["srs:search","srs:read_section","srs:read_table"] |
| sampling_tips | DocDancer的文档QA tips | SRS上下文关联tips |
| resource_types | ["doc"] | ["srs"] |
| max_depth | 20 | 15 (SRS比PDF短) |

### 3.2 一致性检测Prompt（移植DataFlow-KG）

**参考**: DataFlow-KG `prompts/consistency.py` 的三个prompt

**我们的Prompt** `prompts/srs_consistency.py`：

```python
# 直接移植 DataFlow-KG 的 KGRelationTripleConsistencyPrompt
# 只改领域词: "知识图谱三元组" → "SRS需求条目"

SRS_CONSISTENCY_PROMPT = """
你是一个SRS一致性检测专家。判断以下两个条目是否一致。

条目A (来自章节{section_a}):
{text_a}

条目B (来自章节{section_b}):
{text_b}

判断标准:
- CONSISTENT: 两个条目描述的同一参数/功能/接口的值和含义一致
- INCONSISTENT: 两个条目存在矛盾(不同值/不同含义/逻辑冲突)
- UNRELATED: 两个条目不描述同一事物

注意区分:
- 合理差异(不同设备形态的配置差异) → 不是不一致
- 真实矛盾(同一参数同一位置的不同值) → 是不一致

输出JSON: {{"verdict":"CONSISTENT"|"INCONSISTENT"|"UNRELATED", "reason":"...", "evidence":"..."}}
"""
# ↑ 这个prompt结构直接来自DataFlow-KG，只改了领域词

# 直接移植 DataFlow-KG 的 KGHallucinationEvaluationPrompt
SRS_EVIDENCE_CHECK_PROMPT = """
判断以下检测结论是否有文档证据支撑:

检测结论: {claim}
文档证据: {evidence}

输出NLI三分类:
- Supported: 证据直接支撑结论
- Contradicted: 证据与结论矛盾
- Not Mentioned: 证据中未提及结论相关内容

输出JSON: {{"nli":"Supported"|"Contradicted"|"Not Mentioned", "reason":"..."}}
"""
# ↑ 直接来自DataFlow-KG，零修改
```

---

## 四、[最小改造] 模块详解——基于源码文件改

### 4.1 SRS文档解析（改自DocDancer的PDF预处理）

**参考源码**: `projects/DocDancer/PDF_preprocess/3_get_outline_and_root.py`

DocDancer的脚本把PDF转为`outline.xml`+`all_content.xml`，节点用栈维护层级。我们改输入为markdown：

```python
# tools/srs_to_xml.py
# 改自 projects/DocDancer/PDF_preprocess/3_get_outline_and_root.py
# 改动点: 输入从PDF改为markdown，去掉OCR相关代码

# ===== 直接复用的部分 (来自3_get_outline_and_root.py:21-105) =====
class SRSOutlineBuilder:
    """从SRS markdown构建outline.xml + all_content.xml"""
    
    def __init__(self):
        self.section_stack = []  # 栈维护层级 (复用3_get_outline_and_root.py:71)
    
    def build(self, md_path: str):
        md_text = Path(md_path).read_text(encoding='utf-8')
        lines = md_text.split('\n')
        
        outline_root = ET.Element("Outline")
        content_root = ET.Element("Document")
        
        for line_no, line in enumerate(lines, 1):
            # 章节标题检测 (改自3_get_outline_and_root.py:71-105的Heading检测)
            m = re.match(r'^(#{2,5})\s+(\d+(?:\.\w+)*)\s+(.+)', line)
            if m:
                number = m.group(2)
                title = m.group(3).strip()
                level = number.count('.')
                
                # 弹栈到当前层级 (直接复用3_get_outline_and_root.py:75-80)
                while self.section_stack and self.section_stack[-1][1] >= level:
                    self.section_stack.pop()
                self.section_stack.append((number, level))
                
                # 创建Section节点 (改自3_get_outline_and_root.py:146)
                sec_outline = ET.SubElement(outline_root, "Section")
                sec_outline.set("section_id", number)
                sec_outline.set("title", title)
                sec_outline.set("start_line", str(line_no))
                
                sec_content = ET.SubElement(content_root, "Section")
                sec_content.set("section_id", number)
                sec_content.set("title", title)
            else:
                # 段落 (改自3_get_outline_and_root.py:156)
                if line.strip() and self.section_stack:
                    para = ET.SubElement(sec_content, "Paragraph")
                    para.set("line", str(line_no))
                    para.text = line.strip()
        
        return outline_root, content_root
```

**改动量**: ~50行新代码，核心逻辑(栈维护层级+XML构建)直接来自DocDancer

### 4.2 SRS检索工具（改自DocDancer的doc_tool.py）

**参考源码**: `sandbox/server/backends/tools/doc_tool.py:436-503`

DocDancer的`single_search`遍历`all_content.xml`做关键词命中。我们改数据源为SRS的章节/表格：

```python
# sandbox/server/backends/tools/srs_tool.py
# 改自 doc_tool.py:436-503 (single_search) 和 doc_tool.py:575-653 (_single_read)

from sandbox.server.backends.tools.base_tool import BaseApiTool, register_api_tool

@register_api_tool("srs:search")
class SRSSearchTool(BaseApiTool):
    """全局检索SRS内容"""
    # 改自 doc_tool.py:504 SearchTool → single_search (doc_tool.py:436)
    
    async def execute(self, query: str, **kwargs):
        seed_path = kwargs.get("seed_path", self.config.get("content_path"))
        content = ET.parse(seed_path).getroot()
        
        results = []
        # 遍历所有Section (复用doc_tool.py:436-470的遍历逻辑)
        for section in content.findall('.//Section'):
            section_id = section.get('section_id', '')
            title = section.get('title', '')
            
            # 搜索标题 (复用doc_tool.py:446)
            if query in title:
                results.append({
                    "section_id": section_id,
                    "type": "section_title",
                    "snippet": title
                })
            
            # 搜索段落 (复用doc_tool.py:451-456)
            for para in section.findall('Paragraph'):
                if query in (para.text or ''):
                    snippet = para.text[:100]  # 复用doc_tool.py:81 make_snippet
                    results.append({
                        "section_id": section_id,
                        "type": "paragraph",
                        "snippet": snippet
                    })
            
            # 搜索表格行 (SRS特有，doc_tool没有)
            for table in section.findall('Table'):
                for row_idx, row in enumerate(table.findall('Row')):
                    row_text = ' '.join(cell.text or '' for cell in row.findall('Cell'))
                    if query in row_text:
                        results.append({
                            "section_id": section_id,
                            "type": "table_row",
                            "table_id": table.get('table_id', ''),
                            "row_index": row_idx,
                            "snippet": row_text[:100]
                        })
        
        return results


@register_api_tool("srs:read_section")
class SRSReadSectionTool(BaseApiTool):
    """读取章节内容"""
    # 改自 doc_tool.py:569 ReadTool → _single_read (doc_tool.py:575)
    
    async def execute(self, section_id: str, **kwargs):
        seed_path = kwargs.get("seed_path", self.config.get("content_path"))
        content = ET.parse(seed_path).getroot()
        
        # 查找章节 (复用doc_tool.py:580)
        section = content.find(f'.//Section[@section_id="{section_id}"]')
        if section is None:
            return {"error": f"Section {section_id} not found"}
        
        # 提取文本 (复用doc_tool.py:585-590)
        paragraphs = [p.text for p in section.findall('Paragraph') if p.text]
        text = '\n'.join(paragraphs)
        
        # 提取表格 (SRS特有)
        tables = []
        for table in section.findall('Table'):
            headers = [c.text for c in table.find('Headers').findall('Cell')] if table.find('Headers') else []
            rows = [[c.text for c in row.findall('Cell')] for row in table.findall('Row')]
            tables.append({
                "table_id": table.get('table_id', ''),
                "type": table.get('type', ''),
                "headers": headers,
                "rows": rows
            })
        
        # 提取图片引用 (复用doc_tool.py:139 extract_image_and_table_items)
        images = [{"image_id": img.get('image_id', ''), "caption": img.get('caption', '')}
                  for img in section.findall('Image')]
        
        return {
            "section_id": section_id,
            "title": section.get('title', ''),
            "text": text,
            "tables": tables,
            "images": images
        }


@register_api_tool("srs:read_table")
class SRSReadTableTool(BaseApiTool):
    """读取表格行(合格性表/追溯表)"""
    # SRS特有，doc_tool没有对应物
    
    async def execute(self, table_type: str, **kwargs):
        seed_path = kwargs.get("seed_path", self.config.get("content_path"))
        content = ET.parse(seed_path).getroot()
        
        results = []
        for table in content.findall(f'.//Table[@type="{table_type}"]'):
            rows = table.findall('Row')
            for row_idx, row in enumerate(rows):
                cells = [c.text for c in row.findall('Cell')]
                results.append({
                    "section": table.get('section', ''),
                    "table_type": table_type,
                    "row_index": row_idx,
                    "cells": cells
                })
        return results
```

**改动量**: ~120行新代码，search和read_section的核心逻辑直接来自doc_tool.py

---

## 五、[必须新写] 模块——且说明为什么不能复用

### 5.1 Z3校验工具

**为什么不能复用**: AgentFlow和DataFlow都没有Z3约束求解工具。这是我们的独创点。

```python
@register_api_tool("srs:z3_check")
class Z3CheckTool(BaseApiTool):
    """逻辑层校验: Z3约束可满足性"""
    
    async def execute(self, constraints: list, **kwargs):
        """
        输入: [{"param":"执行时间","operator":"≤","value":5,"unit":"ms"}, ...]
        输出: {"result":"sat"|"unsat"|"unknown","unsat_core":"..."}
        """
        from z3 import Solver, Real, sat, unsat
        
        solver = Solver()
        var_map = {}
        
        for c in constraints:
            param = c["param"]
            if param not in var_map:
                var_map[param] = Real(param)
            var = var_map[param]
            val = float(c["value"])
            op = c["operator"]
            
            if op == "≤": solver.add(var <= val)
            elif op == "≥": solver.add(var >= val)
            elif op == "=": solver.add(var == val)
            elif op == "<": solver.add(var < val)
            elif op == ">": solver.add(var > val)
        
        result = solver.check()
        if result == unsat:
            return {"result": "unsat", "unsat_core": str(solver.unsat_core())}
        elif result == sat:
            return {"result": "sat"}
        else:
            return {"result": "unknown"}
```

**代码量**: ~30行。Z3 API简单，且有现有项目`srs_consistency_checker_v2.py`中的Z3使用经验参考。

### 5.2 语法Lint工具

**为什么不能复用**: GJB格式的语法规则(章节编号/需求ID/合格性方法)是领域特有的，AgentFlow/DataFlow没有对应工具。

```python
@register_api_tool("srs:lint")
class SRSLintTool(BaseApiTool):
    """语法层校验"""
    
    async def execute(self, check_type: str, **kwargs):
        if check_type == "duplicate_section":
            # 章节编号去重: 统计section_id出现次数
            sections = kwargs.get("sections", [])
            counts = Counter(sections)
            dups = {s: c for s, c in counts.items() if c > 1}
            return {"duplicates": dups}
        
        elif check_type == "phantom_requirement":
            # 幽灵需求: referenced - defined
            defined = set(kwargs.get("defined_sections", []))
            referenced = set(kwargs.get("referenced_sections", []))
            phantoms = referenced - defined
            return {"phantoms": list(phantoms)}
        
        elif check_type == "systematic_offset":
            # 系统性偏移: 尝试offset=-2..2找最佳匹配
            ch_a = kwargs.get("sections_a", [])
            ch_b = kwargs.get("sections_b", [])
            best_offset, best_rate = 0, 0
            for offset in range(-2, 3):
                matched = sum(1 for s in ch_b if f"{s}+{offset}" in ch_a or 
                              adjust_section(s, offset) in ch_a)
                rate = matched / max(1, len(ch_b))
                if rate > best_rate:
                    best_offset, best_rate = offset, rate
            return {"offset": best_offset, "match_rate": best_rate,
                    "is_systematic": best_offset != 0 and best_rate > 0.8}
```

**代码量**: ~40行。逻辑简单(集合运算+Counter)。

---

## 六、总结：复用比例

| 类别 | 模块数 | 代码量(估) | 说明 |
|------|--------|-----------|------|
| [直接复用] | 12个 | ~5000行 | import即用，不改代码 |
| [改配置] | 4个 | ~200行 | 写config/prompt文件 |
| [最小改造] | 3个 | ~170行 | 基于源码文件改 |
| [必须新写] | 2个 | ~70行 | Z3+Lint，逻辑简单 |
| **总计** | 21个 | **~5440行中复用5000+行** | **复用率>92%** |

### 我们实际要写的代码

1. `tools/srs_to_xml.py` (~50行) — 改自DocDancer的`3_get_outline_and_root.py`
2. `sandbox/server/backends/tools/srs_tool.py` (~120行) — 改自DocDancer的`doc_tool.py`
3. `prompts/srs_consistency.py` (~50行) — 移植DataFlow-KG的prompt
4. `configs/synthesis/srs_aggregate.json` (~30行) — 仿doc_config.json
5. `configs/synthesis/srs_check.json` (~30行) — 仿doc_config.json
6. Z3工具 (~30行) — 新写
7. Lint工具 (~40行) — 新写

**总计新写/改造: ~350行代码**，其余~5000行直接复用。

### 为什么这样更靠谱

1. **核心引擎(三阶段流水线)是AgentFlow的已验证代码** — 在DocDancer/RAGShaper等多个项目中验证过
2. **LLM调用/存储/编排是DataFlow的已验证代码** — 7.2k GitHub stars，100+CCF-A论文
3. **一致性检测prompt是DataFlow-KG的已验证prompt** — 在知识图谱一致性检测中验证过
4. **我们只写SRS领域特有的部分** — 文档解析(改自DocDancer) + Z3工具(简单) + Lint工具(简单)
5. **每个新写的模块都有源码参考** — 不是从零设计，是改造已验证的代码
