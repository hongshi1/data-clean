# SRS一致性校验与上下文关联——方法设计补充

> 本文档补充调研报告中缺失的"具体方法"部分
> 基于DataFlow/AgentFlow代码深度调研 + 真实SRS文档调研发现

---

## 一、技术参考：DataFlow/AgentFlow代码级分析

### 1.1 DataFlow的Operator-Pipeline-Storage模式

DataFlow的核心设计是**类似PyTorch的模块化数据流水线**：

```python
# DataFlow的代码模式（来自GitHub README）
from dataflow.operators.core_text import PromptedGenerator
from dataflow.utils.storage import FileStorage
from dataflow.serving import APILLMServing_request

# 1. Storage: 管理数据输入输出（JSON/JSONL/CSV）
storage = FileStorage(first_entry_file_name="./input.json")

# 2. LLM Serving: 封装LLM调用
llm_serving = APILLMServing_request(api_url="https://api.openai.com/...")

# 3. Operator: 封装一个数据处理任务
operator = PromptedGenerator(
    llm_serving=llm_serving,
    system_prompt="Please solve this math problem."
)

# 4. 运行: 读input_key列，写output_key列
operator.run(
    storage=storage.step(),
    input_key="problem",
    output_key="solution"
)
```

**关键设计模式**：
- **Operator是原子单元**：每个Operator封装一个LLM调用+数据处理逻辑
- **Pipeline编排多个Operator**：按顺序执行，前一个的output是后一个的input
- **Storage管理中间状态**：`storage.step()`自动管理每步的输入输出文件
- **算子分类**：generation(生成)/evaluation(评估)/filtering(过滤)/refinement(精炼)

**Knowledge Base Cleaning Pipeline**（与我们最相关）：
- 从非结构化来源（表格/PDF/Word）提取结构化知识
- 输出可直接用于RAG或QA对生成

### 1.2 AgentFlow的三阶段方法

AgentFlow的核心是**Trajectory Sampling → Selection → QA Synthesis**三阶段：

1. **Trajectory Sampling**: LLM驱动的Agent在sandbox中迭代探索
   - 每步：提出工具调用→执行→记录观察→构建分支轨迹树
   - 支持并发扩展+动作去重
   
2. **Trajectory Selection**: 对所有根到叶路径打分
   - 评分维度：深度、信息丰富度、工具多样性
   - 选择策略确保高质量内容

3. **QA Synthesis**: 为选定路径生成多跳QA对
   - 基于收集的观察生成
   - 内置质量检查

**DocDancer**（文档Agent，与我们最相关）：
- 回答多页文档的复杂问题
- 跨文本/表格/图表做多跳推理
- 在MMLongBench-Doc上达到54.4%准确率（接近人类65.8%）

### 1.3 对我们项目的直接启示

| DataFlow/AgentFlow技术 | 我们的对接方式 |
|----------------------|-------------|
| Operator模式 | 每种不一致性检测封装为一个Operator |
| Pipeline编排 | 上下文关联→不一致性校验→证据标注的Pipeline |
| Storage中间状态 | 每步检测结果+证据可追溯 |
| KB Cleaning Pipeline | SRS文档→结构化需求条目的提取 |
| AgentFlow三阶段 | 关联采样→校验选择→报告合成的三阶段检测 |
| DocDancer跨模态推理 | SRS中文本/表格/图片的跨模态一致性检测 |

---

## 二、方向A：上下文关联——具体方法

### 2.1 问题形式化

**输入**：一份SRS文档的解析后markdown（含章节/表格/图片引用）
**输出**：条目列表，每个条目 = 聚合了"描述同一事物"的文字片段、表格行、图片的单元

**形式化定义**：
```
条目(Item) = {
    entity_id: str,          // 实体标识（需求ID或功能名称）
    entity_type: str,        // function/parameter/interface/state
    text_refs: [TextRef],    // 文字描述位置 {section, line, text}
    table_refs: [TableRef],  // 表格行位置 {table_type, row_index, section}
    image_refs: [ImageRef],  // 图片位置 {figure_number, section, caption}
    semantic_role: str,      // threshold/config/capacity/description
}
```

### 2.2 方法：多信号融合的条目聚合

#### Step 1: 实体识别——从文档中提取候选实体

**不是正则截取**，而是用LLM理解语义后提取：

```
LLM Prompt（参考DataFlow的PromptedGenerator模式）:
"""
你是一个GJB 438C SRS文档分析专家。请从以下章节文本中提取所有需求实体。

每个实体包含：
- entity_id: 需求标识符（如PZXQ-GN-FWKFZC），如果没有则用功能名称
- entity_name: 功能/参数/接口的名称
- entity_type: function(功能需求)/parameter(性能参数)/interface(接口)/state(状态)
- section: 所在章节号
- text: 原文片段（verbatim quote）

文本:
{section_text}

输出JSON数组。
"""
```

**关键技术点**：
- 按章节分块提取（每章一次LLM调用，控制上下文长度）
- verbatim quote确保可溯源（参考RARE的证据约束思路）
- entity_id可能缺失或不一致——后续用归一化处理

#### Step 2: ID归一化——处理ID分裂

**问题**：同一需求有3个ID（SJCS/SJCSKZ/SJSF），因为缩写词混乱

**方法**：基于缩写词展开的ID归一化

```python
def normalize_id(raw_id: str, context: str) -> str:
    """
    ID归一化: 处理缩写词不一致
    
    策略:
    1. 构建缩写词映射表 (从文档上下文学习)
       如: SJCS="数据传输", SJCSKZ="数据传输控制", SJSF="数据收发"
    2. 对每个ID, 找到最长的缩写词匹配
    3. 展开为完整名称
    4. 用完整名称的hash作为归一化ID
    """
    # 从context中学习缩写词
    abbrev_map = extract_abbreviations(context)
    # 展开
    expanded = expand_abbreviations(raw_id, abbrev_map)
    return expanded
```

**具体算法**：
1. 从3.2概述文字和能力标识表中提取"缩写=全称"映射
2. 对每个ID，用最长匹配展开缩写词
3. 展开后的字符串作为归一化ID
4. 如果两个ID展开后相同 → 判定为同一实体

#### Step 3: 章节号容错匹配——处理系统性偏移

**问题**：第4章合格性表的章节号比第3章整体+1（因幽灵需求占位）

**方法**：偏移检测+容错匹配

```python
def match_sections_with_offset(sec_a: str, sec_b: str, 
                                all_secs_a: list, all_secs_b: list) -> tuple:
    """
    章节号容错匹配: 检测系统性偏移
    
    策略:
    1. 对两个章节列表做序列对齐
    2. 检测是否存在常数偏移(offset = +1, -1, 0)
    3. 如果偏移一致, 则sec_a匹配sec_b+offset
    """
    # 检测偏移
    for offset in [0, 1, -1]:
        adjusted = adjust_section(sec_b, offset)
        if adjusted in all_secs_a:
            # 验证: 检查多个点是否都满足同一偏移
            if verify_offset_consistency(all_secs_a, all_secs_b, offset):
                return (True, offset)
    return (False, 0)
```

**具体算法**：
1. 取第4章所有章节号列表和第3章所有章节号列表
2. 尝试offset=0/1/-1，检查哪个offset能使最多章节号匹配
3. 如果某个offset的匹配率>80%，判定为系统性偏移
4. 后续匹配时自动应用该offset

#### Step 4: 多信号融合——综合判断"同一事物"

```python
def aggregate_items(entities: list, tables: list, images: list) -> list[Item]:
    """
    多信号融合聚合
    
    对每对实体，计算关联分数:
    - ID归一化匹配: +0.4
    - 名称字符串相似度>0.8: +0.3  
    - 章节号容错匹配: +0.2
    - 位置邻接(同章节): +0.1
    
    分数>=0.5 → 聚合为同一条目
    """
    items = []
    used = set()
    
    for i, e in enumerate(entities):
        if i in used:
            continue
        
        item = Item(entity_id=e.id, entity_type=e.type,
                    text_refs=[e.ref], table_refs=[], image_refs=[])
        
        for j, e2 in enumerate(entities):
            if j <= i or j in used:
                continue
            
            score = 0
            # 信号1: ID归一化
            if normalize_id(e.id, e.context) == normalize_id(e2.id, e2.context):
                score += 0.4
            # 信号2: 名称相似度
            if string_similarity(e.name, e2.name) > 0.8:
                score += 0.3
            # 信号3: 章节号容错
            if match_sections_with_offset(e.section, e2.section, ...)[0]:
                score += 0.2
            # 信号4: 位置邻接
            if e.section == e2.section or adjacent(e.section, e2.section):
                score += 0.1
            
            if score >= 0.5:
                item.text_refs.append(e2.ref)
                used.add(j)
        
        # 关联表格行
        for t in tables:
            if table_matches_item(t, item):
                item.table_refs.append(t.ref)
        
        # 关联图片
        for img in images:
            if img.section in [r.section for r in item.text_refs]:
                item.image_refs.append(img.ref)
        
        items.append(item)
        used.add(i)
    
    return items
```

#### Step 5: 幽灵需求检测——被引用未定义的实体

```python
def detect_phantom_requirements(items: list, all_references: list) -> list:
    """
    幽灵需求检测: 被引用但从未定义的实体
    
    策略:
    1. 收集所有"定义位置"(3.2.X节的实体)
    2. 收集所有"引用位置"(第4/5章/3.3/3.4中的引用)
    3. 引用位置指向的章节号在定义位置中不存在 → 幽灵需求
    """
    defined_sections = {item.text_refs[0].section for item in items 
                        if item.entity_type == "function"}
    
    phantoms = []
    for ref in all_references:
        if ref.target_section not in defined_sections:
            phantoms.append({
                "referenced_section": ref.target_section,
                "referenced_from": ref.source_section,
                "description": f"章节{ref.target_section}被{ref.source_section}引用但未定义"
            })
    
    return phantoms
```

---

## 三、方向B：不一致性校验——具体方法

### 3.1 语法层检测（规则检测算子）

#### S1: 章节编号重复检测

```python
def check_duplicate_sections(items: list) -> list[Violation]:
    """检测同一文档内重复的章节编号"""
    section_counts = Counter(item.text_refs[0].section for item in items)
    violations = []
    for sec, count in section_counts.items():
        if count > 1:
            violations.append(Violation(
                rule="S1", severity="HIGH",
                description=f"章节{sec}出现{count}次",
                evidence=[r for item in items if item.text_refs[0].section == sec 
                          for r in item.text_refs]
            ))
    return violations
```

#### S3: 合格性表章节号系统性偏移检测

```python
def check_systematic_offset(ch4_sections: list, ch3_sections: list) -> list[Violation]:
    """
    检测合格性表(第4章)章节号是否与第3章系统性偏移
    
    方法: 对齐两个章节列表, 检测常数偏移
    """
    # 找到最佳偏移
    best_offset = 0
    best_match_rate = 0
    for offset in range(-2, 3):
        matched = sum(1 for s in ch4_sections 
                      if adjust(s, offset) in ch3_sections)
        rate = matched / len(ch4_sections)
        if rate > best_match_rate:
            best_offset = offset
            best_match_rate = rate
    
    if best_offset != 0 and best_match_rate > 0.8:
        return [Violation(
            rule="S3", severity="HIGH",
            description=f"合格性表章节号系统性偏移{best_offset:+d} (匹配率{best_match_rate:.0%})",
            evidence=f"第4章章节号与第3章不一致, 整体偏移{best_offset}"
        )]
    return []
```

#### S5: 需求ID分裂检测

```python
def check_id_split(items: list) -> list[Violation]:
    """
    检测同一需求实体有多个不同ID
    
    方法: 用Step 2的ID归一化, 如果两个不同raw_id归一化后相同 → ID分裂
    """
    id_groups = defaultdict(list)
    for item in items:
        normalized = normalize_id(item.entity_id, item.context)
        id_groups[normalized].append(item.entity_id)
    
    violations = []
    for normalized, raw_ids in id_groups.items():
        if len(set(raw_ids)) > 1:
            violations.append(Violation(
                rule="S5", severity="HIGH",
                description=f"需求ID分裂: {set(raw_ids)} 指向同一实体",
                evidence=f"归一化ID={normalized}, 原始ID={raw_ids}"
            ))
    return violations
```

### 3.2 语义层检测（值比较+LLM）

#### M1: 同一参数不同值检测

```python
def check_param_value_conflict(items: list) -> list[Violation]:
    """
    检测同一参数在不同位置的值是否一致
    
    关键: 只比较同semantic_role的参数
    - threshold(阈值)必须一致
    - config(配置)可以不同
    - capacity(能力)可以不同
    """
    violations = []
    param_groups = defaultdict(list)
    
    for item in items:
        if item.entity_type == "parameter":
            for ref in item.text_refs:
                param_groups[(item.entity_id, item.semantic_role)].append(ref)
    
    for (param, role), refs in param_groups.items():
        if role == "threshold" and len(refs) > 1:
            values = [extract_value(ref.text) for ref in refs]
            if len(set(values)) > 1:
                violations.append(Violation(
                    rule="M1", severity="HIGH",
                    description=f"参数{param}的阈值不一致: {values}",
                    evidence=refs
                ))
    
    return violations
```

#### M4: 用例概述内容错位检测（需要LLM）

```python
def check_usecase_summary_misalignment(items: list, llm_serving) -> list[Violation]:
    """
    检测用例概述与用例名称不匹配(copy-paste错误)
    
    方法: LLM判断概述内容是否与功能名称语义一致
    """
    prompt = """
    判断以下用例的概述内容是否与用例名称匹配。
    
    用例名称: {usecase_name}
    概述内容: {summary}
    
    如果概述描述的是另一个功能(疑似copy-paste错误), 输出:
    {{"match": false, "reason": "概述描述的是{其他功能}, 与{用例名称}不匹配"}}
    
    如果匹配, 输出:
    {{"match": true}}
    """
    
    violations = []
    for item in items:
        if item.entity_type == "function":
            for ref in item.text_refs:
                if "概述" in ref.text:
                    result = llm_serving.call(prompt.format(
                        usecase_name=item.entity_name,
                        summary=ref.text[:200]
                    ))
                    if "false" in result:
                        violations.append(Violation(
                            rule="M4", severity="HIGH",
                            description=f"用例概述错位: {item.entity_name}",
                            evidence=ref
                        ))
    return violations
```

### 3.3 逻辑层检测（Z3+NLI）

#### L1: 约束逻辑可满足性检测

```python
from z3 import *

def check_logic_satisfiability(items: list) -> list[Violation]:
    """
    检测约束之间是否逻辑可满足
    
    方法: 
    1. 提取所有数值约束
    2. 用Z3建模约束
    3. 检查可满足性
    """
    solver = Solver()
    var_map = {}
    
    for item in items:
        if item.entity_type == "parameter":
            # 创建Z3变量
            var = Real(item.entity_id)
            var_map[item.entity_id] = var
            
            # 添加约束
            for ref in item.text_refs:
                value, operator, unit = parse_constraint(ref.text)
                if value is not None:
                    if operator == "≤":
                        solver.add(var <= value)
                    elif operator == "≥":
                        solver.add(var >= value)
                    elif operator == "=":
                        solver.add(var == value)
    
    # 检查可满足性
    if solver.check() == unsat:
        return [Violation(
            rule="L1", severity="HIGH",
            description="约束逻辑不可满足(UNSAT)",
            evidence=str(solver.unsat_core())
        )]
    return []
```

#### L2: 允许vs禁止矛盾检测（需要NLI）

```python
def check_allow_vs_prohibit(items: list, llm_serving) -> list[Violation]:
    """
    检测"允许X" vs "禁止X"的语义矛盾
    
    方法: 
    1. 从3.2.X提取"允许"类约束
    2. 从3.12提取"禁止"类约束
    3. 用NLI判断是否构成矛盾
    """
    allows = [item for item in items if "允许" in item.get_modal_text()]
    prohibits = [item for item in items if "禁止" in item.get_modal_text() or "不应" in item.get_modal_text()]
    
    violations = []
    for allow in allows:
        for prohibit in prohibits:
            # NLI判断: allow和prohibit是否关于同一行为
            prompt = """
            判断以下两条约束是否构成矛盾:
            
            约束A(允许): {allow_text}
            约束B(禁止): {prohibit_text}
            
            如果A允许的行为被B禁止, 输出: {{"contradiction": true}}
            否则输出: {{"contradiction": false}}
            """
            result = llm_serving.call(prompt.format(
                allow_text=allow.text, prohibit_text=prohibit.text
            ))
            if "true" in result:
                violations.append(Violation(
                    rule="L2", severity="HIGH",
                    description=f"允许vs禁止矛盾: {allow.text} vs {prohibit.text}",
                    evidence=[allow.ref, prohibit.ref]
                ))
    return violations
```

### 3.4 结构层检测（跨章关联）

#### X1: 幽灵需求检测

```python
def check_phantom_requirement(items: list, all_refs: list) -> list[Violation]:
    """
    检测被引用但从未定义的需求
    
    方法: 
    1. defined = {3.2.X节的所有功能}
    2. referenced = {第4/5章引用的章节号}
    3. referenced - defined = 幽灵需求
    """
    defined = {item.text_refs[0].section for item in items 
               if item.entity_type == "function" and item.text_refs[0].section.startswith("3.2")}
    
    referenced = {ref.target_section for ref in all_refs}
    
    phantoms = referenced - defined
    violations = []
    for p in phantoms:
        if p.startswith("3.2"):
            violations.append(Violation(
                rule="X1", severity="HIGH",
                description=f"幽灵需求: 章节{p}被引用但从未定义",
                evidence=[ref for ref in all_refs if ref.target_section == p]
            ))
    return violations
```

---

## 四、检测Agent架构（基于DataFlow/AgentFlow模式）

### 4.1 整体架构

```
SRS文档 → [Pipeline: 检测流水线]
              │
              ├─ Operator 1: 文档解析 (MinerU/textutil)
              │     └─ input: .doc → output: markdown
              │
              ├─ Operator 2: 实体识别 (LLM)
              │     └─ input: markdown → output: entities.json
              │
              ├─ Operator 3: 上下文关联 (多信号融合)
              │     └─ input: entities+tables+images → output: items.json
              │
              ├─ Operator 4: 语法层检测 (规则算子)
              │     └─ input: items → output: syntax_violations.json
              │
              ├─ Operator 5: 语义层检测 (值比较+LLM)
              │     └─ input: items → output: semantic_violations.json
              │
              ├─ Operator 6: 逻辑层检测 (Z3+NLI)
              │     └─ input: items → output: logic_violations.json
              │
              ├─ Operator 7: 结构层检测 (跨章关联)
              │     └─ input: items → output: structure_violations.json
              │
              └─ Operator 8: 证据标注+报告生成
                    └─ input: all_violations → output: report.json
```

### 4.2 Operator接口设计（参考DataFlow模式）

```python
class DetectionOperator:
    """检测算子基类 (参考DataFlow的Operator设计)"""
    
    def __init__(self, llm_serving=None, config=None):
        self.llm_serving = llm_serving
        self.config = config or {}
    
    def run(self, storage, input_key, output_key):
        """
        执行检测算子
        - storage: 数据存储(管理输入输出)
        - input_key: 从哪列读数据
        - output_key: 写到哪列
        """
        input_data = storage.read(input_key)
        results = self.detect(input_data)
        storage.write(output_key, results)
    
    def detect(self, input_data) -> list[Violation]:
        """子类实现具体检测逻辑"""
        raise NotImplementedError


class DuplicateSectionChecker(DetectionOperator):
    """S1: 章节编号重复检测"""
    def detect(self, items) -> list[Violation]:
        # 具体实现见3.1节
        pass


class ParamValueConflictChecker(DetectionOperator):
    """M1: 同一参数不同值检测"""
    def detect(self, items) -> list[Violation]:
        # 具体实现见3.2节
        pass


class LogicSatisfiabilityChecker(DetectionOperator):
    """L1: 约束逻辑可满足性检测"""
    def detect(self, items) -> list[Violation]:
        # 具体实现见3.3节
        pass
```

### 4.3 Pipeline编排

```python
class ConsistencyDetectionPipeline:
    """一致性检测流水线 (参考DataFlow的Pipeline设计)"""
    
    def __init__(self, llm_serving):
        self.llm = llm_serving
        self.operators = [
            EntityRecognitionOperator(llm_serving),
            ContextAggregationOperator(),
            DuplicateSectionChecker(),           # S1
            SystematicOffsetChecker(),            # S3
            IDSplitChecker(),                     # S5
            ParamValueConflictChecker(),          # M1
            UseCaseMisalignmentChecker(llm_serving),  # M4
            LogicSatisfiabilityChecker(),         # L1
            AllowVsProhibitChecker(llm_serving),  # L2
            PhantomRequirementChecker(),          # X1
            CoverageChecker(),                    # X2
            EvidenceAnnotationOperator(llm_serving),
        ]
    
    def run(self, doc_path: str) -> dict:
        """执行完整检测流水线"""
        storage = FileStorage(doc_path)
        
        for op in self.operators:
            op.run(
                storage=storage.step(),
                input_key="items",
                output_key="violations"
            )
        
        return storage.read("final_report")
```

---

## 五、方法与DataFlow/AgentFlow的技术对接总结

### 5.1 直接复用的设计模式

| DataFlow/AgentFlow模式 | 我们的实现 | 具体对接 |
|----------------------|-----------|---------|
| Operator基类 | DetectionOperator | 每种检测规则封装为一个Operator |
| Pipeline编排 | ConsistencyDetectionPipeline | 按顺序执行所有检测Operator |
| Storage中间状态 | FileStorage | 每步检测结果+证据可追溯 |
| APILLMServing_request | LLM调用封装 | 复用GLM-5 API配置 |
| KB Cleaning Pipeline | EntityRecognitionOperator | SRS文档→结构化需求条目 |
| AgentFlow三阶段 | 关联→校验→报告三阶段 | 采样=关联, 选择=校验, 合成=报告 |
| DocDancer跨模态推理 | 图文一致性检测 | 跨文本/表格/图片的多跳检测 |
| RARE证据约束 | EvidenceAnnotationOperator | 每条违规附verbatim quote+行号 |

### 5.2 我们的独创部分

| 我们的方法 | DataFlow/AgentFlow没有的 | 技术难点 |
|-----------|------------------------|---------|
| ID归一化(缩写词展开) | 无 | 缩写词映射需要从上下文学习 |
| 章节号系统性偏移检测 | 无 | 需要序列对齐+偏移验证 |
| 幽灵需求检测 | 无 | 需要跨章引用-定义集合运算 |
| semantic_role区分 | 无 | 需要LLM判断参数是threshold还是config |
| 多信号融合聚合 | 无 | 需要设计融合策略和阈值 |
