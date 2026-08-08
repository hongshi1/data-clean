# SRS一致性检测Agent——基于源码理解的方法设计

> 基于DataFlow/AgentFlow/DataFlow-KG的源码级分析
> 所有设计都有对应的源码参考点和代码片段

---

## 一、核心架构决策：复用AgentFlow三阶段 + DataFlow算子模式

### 1.1 关键发现（来自源码分析）

**AgentFlow的核心设计**（`synthesis/pipeline.py:66`）：
- 三阶段（Sampling→Selection→Synthesis）代码**完全通用**
- 领域知识全部外置到config的`sampling_tips`/`synthesis_tips`/`available_tools`
- 新增领域只需：实现Backend+tools + 写config，**不改sampler/selector/synthesizer一行代码**

**DataFlow的核心设计**（`dataflow/core/operator.py:1-28`）：
- Operator极简：只有一个`run()`抽象方法
- Storage的step()机制：自动管理中间状态，可断点续跑
- Pipeline的compile时键校验：防止input_key/output_key拼写错误

**DataFlow-KG的一致性检测**（`dataflow-kg/operators/evaluation/`）：
- 三件套：三元组一致性(LLM判CONSISTENT/INCONSISTENT) + NLI三分类 + 子图打分
- 实体/关系抽取两阶段LLM，prompt硬约束"宁缺毋滥"

### 1.2 架构决策

**采用AgentFlow三阶段 + DataFlow算子模式的混合架构**：

```
SRS文档 → [阶段A: 上下文关联(=Trajectory Sampling改造)]
              │  seed=SRS outline.xml
              │  工具: srs:search + srs:read_section + srs:read_table
              │  产出: 聚合条目(同一实体的跨章节证据链)
              ↓
         [阶段B: 不一致性校验(=Selection改造+校验工具)]
              │  选择: 具备校验价值的候选对
              │  工具: srs:z3_check + srs:value_compare + srs:lint
              │  产出: 检测结果+证据
              ↓
         [阶段C: 报告合成(=QA Synthesis改造)]
              │  LLM生成检测报告(含reasoning_steps+evidence)
              │  质量检查: 证据可追溯、拒绝臆造
              │  产出: 最终报告
```

---

## 二、方向A：上下文关联——基于AgentFlow Sampling改造

### 2.1 SRS outline.xml生成（仿DocDancer的PDF预处理）

**参考源码**: `projects/DocDancer/PDF_preprocess/3_get_outline_and_root.py:21-211`

DocDancer把PDF预处理为`outline.xml`（层级树）+`all_content.xml`（全部内容），节点类型含Section/Paragraph/Image/HTML_Table。我们照搬这个设计：

```python
# tools/srs_to_xml.py (新建，仿3_get_outline_and_root.py)
# 输入: parsed_srs_dataset/*.md (已解析的SRS markdown)
# 输出: outline.xml + all_content.xml

def md_to_outline_xml(md_path: str) -> tuple[str, str]:
    """
    把SRS markdown转为outline.xml + all_content.xml
    
    节点类型 (仿DocDancer):
    - Section(section_id="3.2.1", title="数据获取", start_line=N)
    - Paragraph(line=N, text="...")
    - Table(table_id="T1", section="4", type="qualification", headers=[...], rows=[...])
    - Image(image_id="F1", section="3.3.1", caption="接口图")
    
    section_id用GJB章节号: 1, 1.1, 3.2.1, 3.2.X等
    """
    md = Path(md_path).read_text()
    lines = md.split('\n')
    
    # 用栈维护章节层级 (仿3_get_outline_and_root.py:71-105)
    section_stack = []
    outline_nodes = []
    content_nodes = []
    
    for line_no, line in enumerate(lines, 1):
        m = re.match(r'^(#{2,5})\s+(\d+(?:\.\w+)*)\s+(.+)', line)
        if m:
            number = m.group(2)
            title = m.group(3)
            level = number.count('.')
            # 弹栈到当前层级
            while section_stack and section_stack[-1][1] >= level:
                section_stack.pop()
            section_stack.append((number, level))
            
            outline_nodes.append(f'<Section section_id="{number}" title="{title}" start_line="{line_no}"/>')
            content_nodes.append(f'<Section section_id="{number}" title="{title}">')
    
    return build_xml(outline_nodes), build_xml(content_nodes)
```

### 2.2 SRS Backend + Tools实现（仿DocDancer的doc_tool.py）

**参考源码**: `sandbox/server/backends/tools/doc_tool.py:338-829`

DocDancer实现了两个工具：`doc:search`(全局检索)和`doc:read`(VLM局部理解)。我们实现SRS专用工具：

```python
# sandbox/server/backends/tools/srs_tool.py (新建，仿doc_tool.py)

class SRSTool:
    """SRS文档工具 (仿DocDancer的DocTool)"""
    
    def __init__(self, config):
        self.outline_path = config["outline_path"]  # outline.xml
        self.content_path = config["content_path"]  # all_content.xml
        self._load_documents()
    
    def _load_documents(self):
        """加载SRS的outline和content (仿doc_tool.py:351)"""
        self.outline = ET.parse(self.outline_path).getroot()
        self.content = ET.parse(self.content_path).getroot()
        self.section_dict = {}  # section_id → Element
        for sec in self.content.findall('.//Section'):
            self.section_dict[sec.get('section_id')] = sec


@register_api_tool("srs:search")
class SRSSearchTool(BaseApiTool):
    """全局检索SRS内容 (仿doc_tool.py:436 single_search)"""
    
    async def execute(self, query: str, **kwargs):
        """
        关键词检索SRS的章节/表格/图片
        
        返回: Search_Result XML，含section_id/table_id/image_id + snippet
        """
        results = []
        for section in self.content.findall('.//Section'):
            # 搜索章节标题
            if query in section.get('title', ''):
                results.append({"section_id": section.get('section_id'),
                               "snippet": section.get('title')})
            # 搜索段落文本
            for para in section.findall('Paragraph'):
                if query in para.text:
                    snippet = make_snippet(para.text, query)  # 仿doc_tool.py:81
                    results.append({"section_id": section.get('section_id'),
                                   "snippet": snippet})
            # 搜索表格内容
            for table in section.findall('Table'):
                for row in table.findall('Row'):
                    row_text = ' '.join(cell.text for cell in row.findall('Cell'))
                    if query in row_text:
                        results.append({"section_id": section.get('section_id'),
                                       "table_id": table.get('table_id'),
                                       "snippet": row_text[:100]})
        return results


@register_api_tool("srs:read_section")
class SRSReadSectionTool(BaseApiTool):
    """读取章节内容 (仿doc_tool.py:575 _single_read)"""
    
    async def execute(self, section_id: str, **kwargs):
        """
        读取指定章节的完整内容，包括文字/表格行/图片引用
        
        返回: {section_id, title, text, tables:[...], images:[...]}
        """
        section = self.section_dict.get(section_id)
        if not section:
            return {"error": f"Section {section_id} not found"}
        
        text = '\n'.join(p.text for p in section.findall('Paragraph'))
        tables = [{"table_id": t.get('table_id'), "type": t.get('type'),
                   "headers": [...], "rows": [...]} 
                  for t in section.findall('Table')]
        images = [{"image_id": i.get('image_id'), "caption": i.get('caption')}
                  for i in section.findall('Image')]
        
        return {"section_id": section_id, "title": section.get('title'),
                "text": text, "tables": tables, "images": images}


@register_api_tool("srs:read_table")
class SRSReadTableTool(BaseApiTool):
    """读取表格行 (仿doc_tool.py的表格处理)"""
    
    async def execute(self, table_type: str, row_index: int = None, **kwargs):
        """
        读取合格性表/追溯表/接口表的行
        
        table_type: qualification/traceability/interface
        """
        tables = self.content.findall(f'.//Table[@type="{table_type}"]')
        results = []
        for table in tables:
            rows = table.findall('Row')
            if row_index is not None:
                rows = [rows[row_index]] if row_index < len(rows) else []
            for row in rows:
                results.append({
                    "table_type": table_type,
                    "section": table.get('section'),
                    "cells": [cell.text for cell in row.findall('Cell')]
                })
        return results
```

### 2.3 上下文关联的Sampling配置

**参考源码**: `configs/synthesis/doc_config.json`

```json
{
  "model": {"name": "glm-5", "api_key_env": "GLM_API_KEY"},
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
    "注意:需求ID可能不一致(SJCS/SJCSKZ/SJSF)，需要归一化",
    "注意:章节号可能系统性偏移(第4章比第3章整体+1)"
  ],
  "seeds_file": "seeds/srs_seeds.jsonl"
}
```

**Seed格式**（仿DocDancer的outline.xml作为seed）：
```jsonl
{"content": "<outline xml of SRS document>", "kwargs": {"doc_id": "01数据获取"}}
```

### 2.4 动作去重（直接复用AgentFlow）

**参考源码**: `synthesis/core/sampler.py:320-357`

AgentFlow的动作去重机制直接可用：
- `_action_signature`: `tool_name(md5(canonical_json(parameters)))[:10]`
- 已执行动作回灌prompt: "[Already Explored Actions - Do NOT Repeat]"

对SRS的适配：避免重复读同一章节/同一表格行。

---

## 三、方向B：不一致性校验——基于DataFlow-KG一致性范式

### 3.1 校验工具实现

**参考源码**: DataFlow-KG的`operators/evaluation/`一致性三件套

```python
@register_api_tool("srs:z3_check")
class Z3CheckTool(BaseApiTool):
    """逻辑层校验: Z3约束可满足性 (我们的独创，AgentFlow没有)"""
    
    async def execute(self, constraints: list, **kwargs):
        """
        输入: 约束列表 [{"param":"执行时间","operator":"≤","value":5,"unit":"ms"}, ...]
        输出: {"result":"sat"|"unsat"|"unknown", "unsat_core":[...]}
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


@register_api_tool("srs:value_compare")
class ValueCompareTool(BaseApiTool):
    """语义层校验: 同一参数的跨章节值比较 (参考DataFlow-KG的一致性检测)"""
    
    async def execute(self, param_name: str, locations: list, **kwargs):
        """
        输入: 参数名 + 多个位置的值
        输出: {"consistent": true/false, "values":[...], "conflicts":[...]}
        
        关键: 只比较同semantic_role的值
        - threshold(阈值)必须一致
        - config(配置)可以不同
        """
        values = [(loc["section"], loc["value"], loc.get("role", "unknown")) 
                  for loc in locations]
        
        # 按semantic_role分组
        by_role = defaultdict(list)
        for sec, val, role in values:
            by_role[role].append((sec, val))
        
        conflicts = []
        for role, vals in by_role.items():
            if role == "threshold" and len(set(v for _, v in vals)) > 1:
                conflicts.append({
                    "role": role,
                    "conflict": f"阈值不一致: {vals}",
                    "severity": "HIGH"
                })
        
        return {"consistent": len(conflicts) == 0, "conflicts": conflicts}


@register_api_tool("srs:lint")
class SRSLintTool(BaseApiTool):
    """语法层校验: 编号/ID/格式规则检测"""
    
    async def execute(self, check_type: str, **kwargs):
        """
        check_type: duplicate_section / id_split / systematic_offset / 
                     phantom_requirement / coverage
        """
        if check_type == "duplicate_section":
            return self._check_duplicate_sections(**kwargs)
        elif check_type == "id_split":
            return self._check_id_split(**kwargs)
        elif check_type == "systematic_offset":
            return self._check_systematic_offset(**kwargs)
        elif check_type == "phantom_requirement":
            return self._check_phantom(**kwargs)
        elif check_type == "coverage":
            return self._check_coverage(**kwargs)
    
    def _check_phantom(self, defined_sections: list, referenced_sections: list):
        """幽灵需求: 被引用但未定义的章节"""
        phantoms = set(referenced_sections) - set(defined_sections)
        return {"phantoms": list(phantoms), "count": len(phantoms)}
    
    def _check_systematic_offset(self, ch4_sections: list, ch3_sections: list):
        """系统性偏移检测 (参考方法设计文档3.1节)"""
        best_offset = 0
        best_rate = 0
        for offset in [-2, -1, 0, 1, 2]:
            matched = sum(1 for s in ch4_sections 
                          if adjust(s, offset) in ch3_sections)
            rate = matched / max(1, len(ch4_sections))
            if rate > best_rate:
                best_offset, best_rate = offset, rate
        if best_offset != 0 and best_rate > 0.8:
            return {"offset": best_offset, "match_rate": best_rate, "is_systematic": True}
        return {"is_systematic": False}
```

### 3.2 一致性检测的LLM Prompt（参考DataFlow-KG一致性三件套）

**参考源码**: DataFlow-KG的`prompts/consistency.py`

DataFlow-KG有三个一致性检测prompt，我们直接移植为SRS版本：

```python
# 移植自 DataFlow-KG KGRelationTripleConsistencyEvaluator
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

# 移植自 DataFlow-KG KGHallucinationEvaluationPrompt  
SRS_NLI_PROMPT = """
判断以下检测结论是否有文档证据支撑:

检测结论: {claim}
文档证据: {evidence}

输出NLI三分类:
- Supported: 证据直接支撑结论
- Contradicted: 证据与结论矛盾
- Not Mentioned: 证据中未提及结论相关内容

输出JSON: {{"nli":"Supported"|"Contradicted"|"Not Mentioned", "reason":"..."}}
"""
```

### 3.3 校验配置

```json
{
  "model": {"name": "glm-5"},
  "available_tools": ["srs:search", "srs:read_section", "srs:read_table", 
                       "srs:z3_check", "srs:value_compare", "srs:lint"],
  "selection_criteria": {
    "min_evidence_count": 2,
    "require_cross_section": true,
    "score_weights": {"depth": 0.3, "conflict_signal": 0.4, "diversity": 0.3}
  },
  "synthesis_tips": [
    "对每个候选不一致对，生成检测报告",
    "报告必须包含: inconsistency_type, severity, evidence_chain, conclusion",
    "evidence_chain每条必须附section_id和verbatim quote",
    "至少3个推理步骤(reasoning_steps)",
    "如果无法确定，输出'uncertain'而非编造结论"
  ]
}
```

---

## 四、报告合成（阶段C）——基于AgentFlow QA Synthesis改造

**参考源码**: `synthesis/core/synthesizer.py:15-196`

AgentFlow的QA Synthesis生成多跳QA对，我们改为生成检测报告：

```python
# 改造自 QASynthesizer.synthesize_qa (synthesizer.py:27)

class SRSReportSynthesizer:
    """检测报告合成 (仿QASynthesizer)"""
    
    def synthesize_report(self, trajectory, candidate_pairs):
        """
        从校验轨迹和候选对生成检测报告
        
        仿synthesizer.py的synthesize_qa，但输出检测报告而非QA
        """
        prompt = self._build_report_prompt(trajectory, candidate_pairs)
        
        for attempt in range(3):  # 最多3次重试 (仿synthesizer.py:36)
            result = self.llm.generate(prompt, temperature=0.7 + 0.1 * attempt)
            report = self._parse_report(result)
            
            if self._quality_check(report):  # 质量检查 (仿synthesizer.py:65)
                return report
            
            # 失败原因回灌prompt (仿synthesizer.py:190-196)
            prompt = self._build_report_prompt(trajectory, candidate_pairs, 
                                               failure_reason=self._last_failure)
        
        return None
    
    def _quality_check(self, report):
        """质量检查 (仿synthesizer.py:65-123)"""
        # 1. 证据可追溯: 每条evidence必须有section_id
        for step in report.get("evidence_chain", []):
            if not step.get("section_id"):
                return False
        # 2. 推理步骤>=3 (仿synthesizer.py:89)
        if len(report.get("reasoning_steps", [])) < 3:
            return False
        # 3. 结论非空 (仿synthesizer.py:123)
        if not report.get("conclusion"):
            return False
        return True
```

**报告输出格式**：
```json
{
  "inconsistency_type": "semantic/parameter_value_conflict",
  "severity": "HIGH",
  "description": "达梦数据库版本在3.9.1(运行环境)为V7.2，在3.10.3(计算机软件需求)为V7.6",
  "evidence_chain": [
    {"hop": 1, "section_id": "3.9.1", "evidence": "达梦数据库V7.2", "verbatim": "达梦数据库版本：V7.2"},
    {"hop": 2, "section_id": "3.10.3", "evidence": "达梦数据库V7.6", "verbatim": "达梦数据库版本：V7.6"},
    {"hop": 3, "section_id": "3.9.1+3.10.3", "evidence": "同一参数两个不同值", "verbatim": "V7.2≠V7.6"}
  ],
  "reasoning_steps": [
    "在3.9.1运行环境中找到达梦数据库版本V7.2",
    "在3.10.3计算机软件需求中找到达梦数据库版本V7.6",
    "同一参数(达梦数据库版本)在两个章节的值不一致(V7.2≠V7.6)",
    "这不是设备形态差异(两个章节描述的是同一运行环境)，是真实矛盾"
  ],
  "conclusion": "INCONSISTENT",
  "verdict": "真实矛盾"
}
```

---

## 五、落地实施路径

### Step 1: SRS outline.xml生成（1天）
- 写`tools/srs_to_xml.py`，把16份markdown转为outline.xml + all_content.xml
- 仿DocDancer的`3_get_outline_and_root.py`

### Step 2: SRS Backend + Tools实现（2天）
- 写`sandbox/server/backends/tools/srs_tool.py`
- 实现`srs:search`/`srs:read_section`/`srs:read_table`/`srs:z3_check`/`srs:value_compare`/`srs:lint`
- 仿DocDancer的`doc_tool.py` + DataFlow-KG的一致性范式

### Step 3: 配置文件（半天）
- 写`configs/synthesis/srs_config.json`（上下文关联配置）
- 写`configs/synthesis/srs_check_config.json`（不一致性校验配置）
- 编码领域知识到`sampling_tips`/`synthesis_tips`

### Step 4: 运行+调优（2天）
- 在2-3份SRS上运行AgentFlow的synthesize pipeline
- 人工审核产出，校准tips
- 评测用LLM-as-Judge（仿DocDancer的eval_score.py）

### 总计：~5天

### 关键优势
1. **不改AgentFlow核心代码**——只需实现SRS的Backend+tools+config
2. **每步有源码参考**——不是从零设计，是改造已验证的代码
3. **证据约束内置**——复用AgentFlow的质量检查机制
4. **可断点续跑**——复用DataFlow的step()存储机制
