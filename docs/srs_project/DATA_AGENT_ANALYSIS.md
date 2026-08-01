# 基于SRS项目构建Data Agent — 可行性分析与开发路线

> 基于ACL 2026 Tutorial《Data Frontier for LLMs》+ SRS不一致检测项目

---

## 一、PPT核心内容梳理

这个Tutorial分5个部分，与我们项目相关的关键点：

### Part 2: 数据选择与质量过滤
- **5代质量过滤演进**: 启发式→困惑度→分类器→LLM-as-Judge→多维评分
- **data-juicer**: 100+算子，云规模数据处理（NeurIPS 2025 Spotlight）
- **Meta-rater**: 多维质量评分（ACL 2025 Best Theme Paper）

### Part 3: 数据合成
- **Self-Instruct→Evol-Instruct→Multi-agent→Self-generation** 五代指令合成
- **AgentInstruct**: 多Agent流水线从原始文档生成25M指令对
- **DataFlow Agent**: LLM驱动的自动数据流水线组装

### Part 4: 开源工具
- **MinerU**: PDF→Markdown解析（64K stars）
- **DataFlow**: 端到端数据准备+LLM Agent
- **data-juicer**: 100+算子的数据处理框架
- **OpenDataArena**: 数据集价值评测平台

### Part 5: 未来方向
- **AI Data Curator**: 自主Agent管理数据流水线
- **Self-improving systems**: 模型评估→筛选→训练→重复
- **Multi-agent synthesis at scale**: 专业化生成Agent团队

---

## 二、什么是Data Agent

PPT中提到的Data Agent有两层含义：

### 2.1 DataFlow Agent（PPT Slide 104）
> "LLM-powered assistant that auto-assembles data pipelines from descriptions"

用户用自然语言描述需求，Agent自动组装数据处理流水线。

### 2.2 AI Data Curator（PPT Slide 113）
> "Autonomous agents for data pipeline management"

Agent自主管理数据质量：检测问题→诊断原因→修复数据→验证修复。

### 2.3 我们的定位

基于SRS项目，我们可以构建一个**SRS文档质量Data Agent**：

```
用户: "检查这批SRS文档有没有不一致"
  ↓
Agent自主决策:
  1. 用MinerU解析PDF → 结构化文本
  2. 检测语法不一致(章节缺失/引用断裂)
  3. 提取参数约束(正则+Span+LLM)
  4. 检测语义矛盾(NLI)
  5. 检测图文不一致(VLM)
  6. 生成报告
  ↓
输出: 不一致检测报告 + 修复建议
```

---

## 三、与现有项目的关系

### 3.1 我们已有的"工具"（Agent可调用的）

| 工具 | 功能 | 代码 | 对标PPT中的 |
|---|---|---|---|
| PDF解析 | PDF→文本+表格 | pdfplumber | MinerU(Slide 102) |
| 章节抽取 | 文档→结构化章节 | srs_rexcl.py | DataFlow算子 |
| 参数抽取 | 句子→{参数,运算符,数值,单位} | srs_keie_pipeline.py | 质量过滤(Slide 48) |
| NLI矛盾检测 | 句子对→矛盾/中立 | 内嵌 | LLM-as-Judge(Slide 48) |
| Z3约束求解 | 约束集→SAT/UNSAT | 内嵌 | — |
| 图文检测 | 页面截图→图文一致性 | srs_image_text_check.py | 多模态(Slide 40-47) |
| 知识库 | 23参数/374实体 | srs_kb.json | — |
| 知识图谱 | 1580节点/4800边 | knowledge_graph.json | — |

### 3.2 我们缺的（Agent需要但还没有的）

| 缺失 | 说明 | PPT中的参考 |
|---|---|---|
| **Agent决策层** | LLM决定调用哪些工具、按什么顺序 | DataFlow Agent(Slide 104) |
| **工具注册机制** | 把现有工具注册为Agent可调用的函数 | data-juicer算子框架 |
| **反馈循环** | Agent从检测结果中学习，改进后续检测 | Self-improving(Slide 74) |
| **多Agent协作** | 不同Agent负责不同检测层 | AgentInstruct(Slide 58) |
| **报告生成** | Agent自动生成人类可读的检测报告 | — |
| **主动学习** | Agent标注不确定的检测结果，请求人工确认 | cleanlab(Slide 106) |

---

## 四、难点分析

### 难点1: 工具选择与编排（核心难点）

**问题**: 62个文档，每个文档可能需要不同的检测策略。Agent需要决定：
- 这个文档有图片吗？→ 需要图文检测
- 这个文档有表格吗？→ 需要正文↔表格配对
- 这个文档有状态图吗？→ 需要流程图检测
- 这个文档的参数抽取结果可信吗？→ 需要决定是否做Z3

**为什么难**:
- 现有工具的调用不是独立的，有依赖关系（参数抽取→NLI→Z3）
- 工具的输出质量不确定（Span分类器F1=0.54，Agent需要判断何时信任）
- 不同文档的特征不同，不能用固定流程

**可能的解法**:
```
Agent收到文档 → 
  Step 1: 快速扫描(文档类型/有无图片/有无表格/有无状态图)
  Step 2: 根据扫描结果选择检测策略
  Step 3: 执行检测，收集结果
  Step 4: 评估结果可信度(置信度<0.5的标记为"需人工确认")
  Step 5: 如果发现新问题，动态调整检测策略
```

### 难点2: 不确定性管理

**问题**: 我们的检测结果有很多假阳性（Z3的8个UNSAT全是假的）。Agent需要：
- 知道每个工具的精度和局限
- 在多个工具结果矛盾时做决策
- 标记不确定的结果请求人工确认

**为什么难**:
- Span分类器说"response_time=238"，但238实际是文档编号
- Z3说"UNSAT(矛盾)"，但实际是参数抽取错误
- NLI说"neutral(不矛盾)"，但实际可能是真矛盾只是上下文不够

**可能的解法**:
```
多工具交叉验证:
  Z3说UNSAT → 不直接报告，先让NLI验证
  NLI说contradiction → 高置信度报告
  NLI说neutral → 标记为"Z3假阳性，已排除"
  NLI说不确定 → 标记为"需人工确认"
```

### 难点3: 多模态推理

**问题**: SRS文档同时包含文本、表格、图片。Agent需要：
- 理解表格结构与正文的关系
- 理解图片内容与文字描述的关系
- 在三种模态之间做一致性推理

**为什么难**:
- 当前图文检测完全依赖VLM API，成本高
- 表格结构化质量差（pdfplumber的None率38%）
- 没有跨模态的关联图谱

**可能的解法**:
```
构建多模态知识图谱:
  节点: 正文段落 + 表格行 + 图片区域
  边: 引用关系 + 参数关联 + 位置邻近
  Agent在图谱上做多跳推理发现跨模态矛盾
```

### 难点4: 知识库自动化

**问题**: 当前知识库是手工构建的23个参数。Agent需要：
- 自动发现新参数类型
- 自动挖掘同义词
- 自动估计值范围
- 持续更新知识库

**为什么难**:
- 没有标注数据来训练参数发现模型
- 同义词挖掘需要语义理解（"latency"="response time"）
- 值范围估计需要统计+领域知识

**可能的解法**:
```
Agent遇到未识别参数 →
  1. 用embedding聚类找相似参数
  2. 用LLM判断是否是新参数
  3. 自动生成同义词+值范围
  4. 标记为"待人工确认"加入知识库
```

### 难点5: 与data-juicer集成

**问题**: data-juicer有100+算子和成熟的流水线框架。我们的工具需要：
- 封装为data-juicer的Operator
- 支持data-juicer的配置驱动模式
- 与data-juicer的现有算子（去重/过滤/质量评分）协同

**为什么难**:
- data-juicer的算子接口有固定格式
- 我们的工具输出格式不统一
- 需要理解data-juicer的内部架构

---

## 五、开发路线

### Phase 1: 工具封装（2周）

把现有17个脚本封装为统一的工具接口：

```python
# tools/srs_agent/tools.py
class SRSToolRegistry:
    """注册所有SRS检测工具"""
    
    tools = {
        "parse_pdf": pdfplumber_parse,           # PDF→JSON
        "extract_sections": rexcl_extract,        # 章节抽取
        "extract_params": keie_extract,           # 参数抽取
        "check_syntax": syntax_check,             # 语法检测
        "check_nli": nli_check,                   # NLI矛盾检测
        "check_z3": z3_check,                     # Z3约束求解
        "check_image_text": vlm_check,            # 图文检测
        "check_duplicate": duplicate_check,        # 需求重复
        "build_graph": build_knowledge_graph,     # 知识图谱
    }
    
    def call(self, tool_name, **kwargs):
        """Agent调用工具的统一接口"""
        return self.tools[tool_name](**kwargs)
```

### Phase 2: Agent决策层（3周）

用LLM实现Agent的决策逻辑：

```python
# tools/srs_agent/agent.py
class SRSDataAgent:
    def __init__(self, llm_backend, tool_registry):
        self.llm = llm_backend  # GLM-5
        self.tools = tool_registry
    
    def run(self, document):
        # Step 1: 快速扫描
        doc_features = self._scan_document(document)
        # → {has_images: True, has_tables: True, has_state_diagram: False, ...}
        
        # Step 2: LLM决策检测策略
        strategy = self.llm.decide_strategy(doc_features)
        # → ["parse_pdf", "extract_sections", "check_syntax", "extract_params", "check_nli"]
        
        # Step 3: 执行检测
        results = {}
        for tool_name in strategy:
            results[tool_name] = self.tools.call(tool_name, document)
        
        # Step 4: 交叉验证
        validated = self._cross_validate(results)
        # Z3的UNSAT → 用NLI验证 → 排除假阳性
        
        # Step 5: 生成报告
        report = self.llm.generate_report(validated)
        return report
```

### Phase 3: 多Agent协作（4周）

不同Agent负责不同检测层：

```
Orchestrator Agent (协调)
  ├── Syntax Agent (语法检测)
  │   ├── 章节缺失检测
  │   ├── 引用断裂检测
  │   └── 单位不统一检测
  ├── Semantic Agent (语义检测)
  │   ├── 参数抽取
  │   ├── NLI矛盾检测
  │   └── 需求重复检测
  ├── Logic Agent (逻辑检测)
  │   ├── Z3约束求解
  │   └── 时序环检测
  └── Visual Agent (图片检测)
      ├── 图文矛盾检测
      ├── 流程图路径检测
      └── 追溯链路检测
```

### Phase 4: 反馈循环（3周）

Agent从检测结果中学习：

```
检测 → 发现假阳性 → 分析原因 → 更新策略 → 重新检测
  例: Z3报告"response_time=238矛盾"
      → NLI验证"238是文档编号"
      → Agent学习"response_time>200时可能是文档编号"
      → 下次自动过滤
```

### Phase 5: data-juicer集成（2周）

封装为data-juicer算子：

```yaml
# config/srs_agent.yaml
- name: srs_syntax_check
  type: mapper
  parameters:
    check_items: [chapter_missing, broken_reference, unit_inconsistency]

- name: srs_semantic_check  
  type: mapper
  parameters:
    extraction_method: keie  # or llm
    nli_verification: true
    z3_verification: true
    cross_validate: true

- name: srs_image_text_check
  type: mapper
  parameters:
    vlm_model: kimi-k2.6
    detectors: [floca, ve, chartve, tracellm]
```

---

## 六、最难的3个开发点

### 1. 工具编排的可靠性（最难）

Agent决定调用哪些工具，但工具的输出可能不可靠。核心挑战是**不确定性传播**：

```
参数抽取(F1=0.54) → 52%的约束是错的
  → Z3基于错误约束求解 → 100%假阳性
    → Agent需要知道"Z3的UNSAT不可信，因为输入不可信"

解法: 置信度传播
  参数抽取置信度=0.54 → Z3结果置信度=0.54×0.5=0.27
  → 低于阈值0.5 → 标记为"低置信度，需NLI验证"
  → NLI验证通过 → 置信度提升到0.9 → 报告
```

### 2. 跨模态关联推理

```
正文: "response time ≤ 50ms" (第3.2节)
表格: "response time ≤ 100ms" (表格4)
图片: 折线图显示响应时间在80ms左右

→ Agent需要推理: 正文说50ms，表格说100ms，图表显示80ms
→ 三者不一致 → 但是否是同一参数？同一工况？
→ 需要知识图谱关联 + 多模态推理
```

### 3. 主动学习与知识库更新

```
Agent遇到"jitter budget = 5ms"
  → 知识库中没有"jitter budget"
  → Agent判断: 这是"jitter"的变体吗？还是新参数？
  → 用embedding聚类: "jitter budget" ≈ "jitter"(0.82) → 可能是同义词
  → 自动添加到知识库，标记为"待确认"
  → 下次遇到"jitter budget"时自动识别
```

---

## 七、与PPT的对应关系

| PPT中的概念 | 我们项目中的对应 | 开发点 |
|---|---|---|
| DataFlow Agent(Slide 104) | SRS Data Agent决策层 | Phase 2 |
| 多Agent合成(Slide 58/72) | 多Agent协作检测 | Phase 3 |
| Self-improving(Slide 74) | 反馈循环 | Phase 4 |
| data-juicer算子(Slide 106) | 工具封装为算子 | Phase 5 |
| Meta-rater多维评分(Slide 48) | 多工具置信度融合 | 难点1 |
| LLM-as-Judge(Slide 48) | NLI矛盾检测 | 已实现 |
| 多模态数据(Slide 40-47) | 图文不一致检测 | 已实现 |
| MinerU(Slide 102) | PDF解析 | 已实现(pdfplumber) |
| OpenDataArena(Slide 84) | 评测结果 | 已实现 |

---

## 八、建议的准备工作

### 8.1 立即可做
1. 把17个脚本的功能整理成统一的函数签名
2. 为每个工具定义输入/输出格式
3. 定义工具间的依赖关系图

### 8.2 需要学习的
1. data-juicer的算子接口规范
2. Multi-agent框架(LangChain/AutoGen/CrewAI)
3. 工具调用(Tool Calling)的prompt工程

### 8.3 需要解决的
1. 知识库自动化构建流水线
2. 置信度传播机制
3. 跨模态知识图谱
