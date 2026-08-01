# DataFlow 生态能力 → SRS 多模态冲突检验与上下文关联 映射分析

> 本文件分析 DataFlow 生态中哪些具体能力可应用于 SRS 项目的两个核心需求：
> 1. **多模态数据冲突检验**：检验 SRS 表格、文本、图片等潜在的不一致冲突
> 2. **上下文关联**：理解上下文并识别哪些数据应该匹配、应该一致

---

## 需求 1：多模态数据冲突检验

### 场景定义

SRS 文档中存在多种模态的数据，它们之间可能存在不一致：

| 冲突类型 | 示例 |
|---------|------|
| 文本 ↔ 表格 | 正文说"最大延时≤5ms"，合格性规定表写"≤10ms" |
| 文本 ↔ 图片 | 正文描述的数据流方向与架构图箭头方向相反 |
| 表格 ↔ 图片 | 追踪表的接口ID与接口关系图的节点ID不对应 |
| 文本 ↔ 公式 | 正文描述的约束条件与公式推导结果矛盾 |
| 跨章节文本 | 3.2节说"支持8路"，4.1节说"支持16路" |
| 表格 ↔ 表格 | 合格性规定表与逆向追踪表对同一需求项的描述不一致 |

### 能力映射（按直接相关度排序）

#### Tier 1：直接可用 ★★★

**1. AgentFlow MM-Doc 环境 + DocDancer 模型**
- **能力**：DocDancer 专为多页文档跨模态推理设计——在文本/表格/图表间导航、提取、推理
- **源码**：`AgentFlow/sandbox/` 的 Doc 工具后端（`doc_tools.py`），`projects/DocDancer/`
- **性能**：MMLongBench-Doc 54.4% acc（接近人类 65.8%），DocBench 81.2 LasJ
- **SRS 应用**：
  ```
  SRS文档 → AgentFlow Sandbox(Doc后端)
     │
     ├── 轨迹采样：Agent导航SRS文档，检索相关约束/表格/图片
     │   ├── 从需求3.2.1出发 → 检索到约束4.1.3 → 检索到表格5.2 → 检索到图片6.1
     │   └── 构建多跳依赖链，发现跨模态关联
     │
     ├── 冲突检测QA合成：
     │   "约束A规定延时≤5ms，合格性规定表B中写≤10ms，是否一致？"
     │   "架构图C的数据流方向为A→B→C，正文3.2节描述为A→C→B，是否冲突？"
     │
     └── 对抗样本：修改sampling_tips引导Agent探索边界——约束冲突、表格矛盾、逻辑死锁
  ```
- **配置**：参照 `configs/synthesis/rag_config.json`，创建 `srs_config.json`，`available_tools` 设为SRS专用（约束检索/表格查询/章节导航/图片理解）

**2. DataFlow-MM 的 core_vision + pdf2vqa 算子**
- **能力**：多模态数据资产处理，视觉问答生成，PDF视觉QA提取
- **源码**：`DataFlow/dataflow/operators/core_vision/generate/prompted_vqa_generator.py`，`pdf2vqa/`
- **关键算子**：
  | 算子 | 功能 | SRS冲突检验应用 |
  |------|------|----------------|
  | `PromptedVQAGenerator` | 视觉问答生成 | 针对SRS图片生成问题（"图中接口ID有哪些？"），与文本/表格对比 |
  | `MinerU2LLMInputOperator` | MinerU输出→LLM格式 | 将SRS的content_list.json转为LLM可理解格式，统一处理 |
  | `QA_Merger` | QA合并 | 合并跨页/跨模态的QA对 |
  | `VQAFormatter` | VQA格式化 | 标准化视觉QA输出，便于与文本约束对比 |
- **VLM Serving**：`APIVLMServing_openai`（OpenAI兼容多图API）或 `LocalVLMServing_vllm`（本地VLM），用户已有 Kimi-K2.6 多模态 API 可直接接入

**3. DataFlow Core 评测算子 + Pipeline 编排**
- **能力**：20+评测算子可适配为冲突检测算子，Pipeline编译期key校验
- **源码**：`DataFlow/dataflow/operators/*/eval/`，`dataflow/wrapper/auto_op.py`
- **SRS 应用**：将三层冲突检测建模为Pipeline算子链：
  ```
  Pipeline: SRSMultimodalConflictDetection
    │
    ├── Operator 1: SRSMinerUParser (input: pdf_path → output: content_list)
    ├── Operator 2: SRSStructurer   (input: content_list → output: structured_json)
    ├── Operator 3: SRSTableExtractor (input: content_list → output: table_data)
    ├── Operator 4: SRSImageExtractor (input: content_list → output: image_refs)
    ├── Operator 5: SRSConstraintExtractor (input: structured_json → output: constraints)
    │
    ├── Eval Operator 6: TextTableConflictChecker
    │     (input: constraints + table_data → output: text_table_conflicts)
    ├── Eval Operator 7: TextImageConflictChecker
    │     (input: constraints + image_refs + VLM → output: text_image_conflicts)
    └── Eval Operator 8: CrossTableConflictChecker
          (input: table_data → output: cross_table_conflicts)
  ```
- **编译期校验**：AutoOP拦截算子调用，构建key依赖图，确保 `constraints` 和 `table_data` 正确传递给冲突检测算子，避免运行期字段不匹配

#### Tier 2：需要适配 ★★

**4. DataFlow-KG graph_reasoning（图推理冲突检测）**
- **能力**：在知识图谱上做多跳推理，发现跨模态隐含冲突
- **源码**：`DataFlow-KG/` 的 `graph_reasoning` 算子包
- **SRS 应用**：
  ```
  构建 SRS 知识图谱：
    需求节点 ──合格性规定──▶ 表格节点
    需求节点 ──引用──▶ 图片节点
    约束节点 ──约束于──▶ 需求节点
    表格节点 ──追踪──▶ 需求节点

  图推理检测冲突：
    路径推理：需求A →约束"≤5ms" →合格性表 →"≤10ms" → 发现数值冲突
    链接预测：预测哪些需求应该有对应表格但缺失
    多跳推理：跨3+章节的间接冲突链
  ```
- **与现有Z3的关系**：Z3做精确的逻辑层求解，graph_reasoning做模糊的语义层发现，互补

**5. Paper2Any 的 DataFlow-Agent 框架（多Agent协作检测）**
- **能力**：41个角色Agent，含VLM Agent、表格抽取Agent、图表验证Agent
- **源码**：`Paper2Any/dataflow_agent/agentroles/`
- **可复用的角色Agent**：
  | Agent | 原始用途 | SRS冲突检验用途 |
  |-------|---------|----------------|
  | `table_extractor_agent` | 论文表格抽取 | SRS表格结构化提取 |
  | `diagram_vlm_validator` | 图表VLM校验 | SRS图片内容与文本描述对比 |
  | `imagetextbboxagent` | 图文框检测 | SRS图片中文字与正文对比 |
  | `chart_type_recommender` | 图表类型推荐 | 识别SRS图表类型以选择检测策略 |
  | `common_agents` | 通用Agent | 自定义冲突检测Agent |
- **执行策略**：`ReactLoop`策略适合冲突检测——Agent迭代检索文档内容，每次发现潜在冲突就记录

**6. MinerU 深化（跨模态数据提取）**
- **bbox/page_idx**：精确空间匹配——文本描述的"图3"通过bbox定位到具体图片区域
- **表格HTML**：`table_body`字段直接提供结构化表格数据，与文本约束对比
- **公式LaTeX**：MinerU输出的公式LaTeX可直接转Z3约束，实现公式级逻辑一致性检测
- **VLM模型(MinerU2.5-Pro)**：视觉理解图表内容，提取图表中的数值/标签与文本对比

#### Tier 3：辅助增强 ★

**7. MemOS L1/L2/L3（冲突模式积累）**
- **L1 Traces**：记录每次检测的轨迹——哪些跨模态冲突被发现了、Agent怎么找到的
- **L2 Policies**：从轨迹中提取策略——"GJB 438C SRS中，合格性规定表的数值通常需要与3.x节正文交叉验证"
- **L3 World Models**：领域知识——SRS文档的常见冲突模式库
- **技能结晶化**：高频检测策略自动转化为可复用Skill

**8. LoopAI AnalyzerAgent（漏检分析）**
- 分析哪些类型的跨模态冲突被漏检（false negatives）
- 统计冲突类型分布（文本-表格 vs 文本-图片 vs 表格-表格）
- 闭环优化：漏检→分析→合成新测试用例→调整检测规则

### 冲突检验完整方案

```
┌─────────────────────────────────────────────────────────────────┐
│                  SRS 多模态冲突检验 Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─── 数据提取层 ────────────────────────────────────────────┐  │
│  │ MinerU解析 → content_list.json                             │  │
│  │   ├── 文本：section_text (阅读顺序+章节层次)               │  │
│  │   ├── 表格：table_body (HTML结构化)                        │  │
│  │   ├── 图片：image_path + bbox + page_idx                  │  │
│  │   └── 公式：formula_latex                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌─── 上下文关联层 ───────────────────────────────────────────┐  │
│  │ DataFlow-KG domain_kg 构建 SRS 结构图谱                     │  │
│  │   需求 ←→ 约束 ←→ 表格 ←→ 图片 ←→ 公式                     │  │
│  │ graph_reasoning: 链接预测 + 多跳推理发现隐含关联            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌─── 冲突检测层 ─────────────────────────────────────────────┐  │
│  │                                                             │  │
│  │  文本↔表格:  PromptedGenerator + 规则对比                   │  │
│  │    "约束X≤5 vs 表格值7" → 数值冲突                          │  │
│  │                                                             │  │
│  │  文本↔图片:  VLM (Kimi-K2.6) 视觉理解 + 文本对比            │  │
│  │    "正文说A→B→C vs 架构图箭头A→C→B" → 方向冲突             │  │
│  │                                                             │  │
│  │  表格↔表格:  NL2SQL跨表查询 + 数据对比                      │  │
│  │    "合格性表接口ID vs 追踪表接口ID" → ID不对应              │  │
│  │                                                             │  │
│  │  文本↔公式:  LaTeX→Z3约束 + 逻辑求解                       │  │
│  │    "正文约束 vs 公式推导" → 逻辑矛盾                        │  │
│  │                                                             │  │
│  │  AgentFlow DocDancer: 多跳跨模态推理发现深层冲突            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌─── 闭环优化层 ─────────────────────────────────────────────┐  │
│  │ LoopAI: Judger(评测) → Analyzer(分析漏检) →                │  │
│  │         Obtainer(合成对抗样本) → Trainer(调优规则)          │  │
│  │ MemOS: L1(轨迹) → L2(策略) → L3(领域知识)                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 需求 2：上下文关联

### 场景定义

SRS 文档中的数据存在复杂的关联关系，需要理解上下文才能识别哪些数据"应该一致"：

| 关联类型 | 示例 |
|---------|------|
| 需求→约束 | 需求3.2.1"系统应支持8路输入" → 约束"输入路数≤8" |
| 需求→表格 | 需求3.2.1 → 合格性规定表第3行 → 逆向追踪表第5行 |
| 需求→图片 | 需求3.2.1"系统架构如图3所示" → 图3 |
| 约束→公式 | 约束"延时≤5ms" → 公式"T = T1 + T2 + T3" |
| 跨章节引用 | 4.1节"见3.2.1节" → 3.2.1节内容 |
| 隐含关联 | 接口表"RS-422" → 正文"串行接口" → 图中"UART"（同一概念不同表述） |

### 能力映射（按直接相关度排序）

#### Tier 1：直接可用 ★★★

**1. DataFlow-KG domain_kg + graph_reasoning（核心能力）**
- **能力**：领域专用KG构建 + 图推理（路径推理、链接预测、关系补全）
- **源码**：`DataFlow-KG/` 的 `domain_kg`、`graph_reasoning`、`graph_rag` 算子包
- **SRS 应用**：
  ```
  Step 1: 构建SRS文档结构知识图谱
  ┌─────────────────────────────────────────────────┐
  │  节点类型：                                      │
  │    Section(章节) / Requirement(需求) /          │
  │    Constraint(约束) / Table(表格) /              │
  │    TableRow(表格行) / Figure(图片) /             │
  │    Formula(公式) / Interface(接口)               │
  │                                                  │
  │  关系类型：                                      │
  │    section_contains / req_refers_to /            │
  │    constraint_applies_to / table_tracks /        │
  │    figure_shows / formula_derives /              │
  │    cross_reference / implies                     │
  └─────────────────────────────────────────────────┘

  Step 2: graph_reasoning 多跳推理
  ┌─────────────────────────────────────────────────┐
  │  链接预测：预测哪些需求应该有对应表格但缺失      │
  │    输入: 需求3.2.1 (无对应表格)                  │
  │    推理: 同类需求3.2.2有表格 → 3.2.1应该也有    │
  │    输出: "需求3.2.1可能缺失合格性规定表"         │
  │                                                  │
  │  关系补全：补全未显式标注的交叉引用              │
  │    输入: 正文提到"串行接口"，接口表有"RS-422"    │
  │    推理: 语义相似度 + 领域知识 → 同一概念        │
  │    输出: "正文'串行接口' = 表格'RS-422'"          │
  │                                                  │
  │  路径推理：发现跨章节的间接关联                  │
  │    路径: 需求3.2 →约束4.1 →表格5.2 →图片6.1     │
  │    含义: 这四个元素应该保持一致                  │
  └─────────────────────────────────────────────────┘

  Step 3: graph_rag 检索增强
  ┌─────────────────────────────────────────────────┐
  │  检测某需求时，从图谱检索所有关联元素：          │
  │  "需求3.2.1" → [约束4.1.3, 表格5.2行3, 图3,     │
  │                 公式(2), 接口I3]                 │
  │  → 这些元素应该一致 → 逐一对比检测              │
  └─────────────────────────────────────────────────┘
  ```
- **与现有项目的对接**：用户已有 `srs_kb_graph_v2.json`（7720节点），可直接用 `domain_kg` 算子重构并增强

**2. MinerU 阅读顺序 + 章节层次 + 交叉引用提取**
- **能力**：MinerU解析保留文档结构信息
- **SRS 应用**：
  | MinerU输出 | 上下文关联应用 |
  |-----------|--------------|
  | 阅读顺序 | 还原文档逻辑流，理解前后文关系 |
  | 章节标题层次 | 构建 Section 层次树（3→3.2→3.2.1），确定上下文范围 |
  | Markdown引用 | 提取 `[图3]`、`见表5`、`见3.2.1节` 等交叉引用 |
  | bbox/page_idx | 空间上下文——同一页的元素更可能相关 |
  | content_list类型 | 区分text/table/image/formula，确定关联类型 |

**3. AgentFlow RAG环境 + 轨迹采样（上下文探索）**
- **能力**：Agent基于上下文检索相关内容，构建多跳依赖链
- **源码**：`AgentFlow/sandbox/server/backends/resources/rag.py`
- **SRS 应用**：
  ```
  Agent从需求3.2.1出发：
    Step 1: 检索"3.2.1"相关内容 → 找到约束4.1.3
    Step 2: 检索"4.1.3"相关内容 → 找到表格5.2第3行
    Step 3: 检索"表格5.2"相关内容 → 找到图片6.1
    Step 4: 检索"图片6.1"相关内容 → 找到公式(2)

  构建依赖链：3.2.1 → 4.1.3 → 表格5.2.3 → 图片6.1 → 公式(2)
  结论：这5个元素构成一个"应该一致"的关联组
  ```
- **配置**：SRS知识图谱构建为Faiss索引作为Sandbox RAG后端

**4. DataMind GraphRAG + Memory（图谱检索+记忆）**
- **能力**：GraphRAG图谱遍历找关联 + Memory跨会话积累
- **源码**：`DataMind/modules/graph/tools.py`，`DataMind/modules/memory/tools.py`
- **SRS 应用**：
  | DataMind知识面 | 上下文关联应用 |
  |---------------|--------------|
  | **GraphRAG** | `graph_search_entities` 搜索需求节点 → `graph_neighbors` 找所有关联节点 → `graph_traverse` 遍历关联链 |
  | **NL2SQL** | "查找合格性规定表中与需求3.2.1相关的行" → 自动生成SQL查询表格 |
  | **Memory (global)** | 跨文档积累："GJB 438C SRS中，每个需求项通常关联1个约束+1个表格行+0-1个图片" |
  | **Memory (profile)** | 按SRS类型积累："battery_srs的3.x节通常关联电池参数表" |
  | **KB (RAG)** | 检索GJB规则："哪些GJB规则要求需求与表格必须对应" |
  | **Skills** | 调用"上下文关联检测"技能，自动执行关联分析 |

#### Tier 2：需要适配 ★★

**5. MemOS L2 Policies（关联规则积累）**
- **能力**：从检测轨迹中提取"什么应该匹配"的策略规则
- **SRS 应用**：
  ```
  L2 Policy 示例（从多次检测中自动学习）：
  ┌──────────────────────────────────────────────────────┐
  │ Rule 1: 需求项ID格式为"3.x.y" → 应在合格性规定表     │
  │         中有对应行                                     │
  │ Rule 2: 正文出现"如图N所示" → 图N应存在且内容匹配    │
  │ Rule 3: 接口表的每个接口ID → 应在接口关系图中有节点  │
  │ Rule 4: 约束中的数值参数 → 应在表格中有对应列         │
  │ Rule 5: 正/逆向追踪表 → 应双向覆盖所有需求项         │
  └──────────────────────────────────────────────────────┘
  ```

**6. DataFlow Core Pipeline key chain（关联关系建模）**
- **能力**：编译期key校验，建模"应该一致"的关系
- **SRS 应用**：
  ```python
  # Pipeline定义中，通过key链建模关联关系
  class SRSContextAssociationPipeline(PipelineABC):
      def forward(self, storage):
          # 编译期自动校验key链
          sections = self.section_parser(storage.step(), input_key="content_list",
                                         output_key="sections")
          requirements = self.req_extractor(storage.step(), input_key="sections",
                                            output_key="requirements")
          # key链: content_list → sections → requirements → constraints
          # 如果requirements缺失，编译期就报错
          constraints = self.constraint_extractor(storage.step(),
                                                  input_key="requirements",
                                                  output_key="constraints")
          # 关联组：requirements + constraints + tables 必须key对齐
          associations = self.association_builder(storage.step(),
              input_keys=["requirements", "constraints", "tables", "figures"],
              output_key="associations")  # 输出"应该一致"的关联组
  ```

**7. OpenWorldLib Memory模块（有状态上下文积累）**
- **能力**：PipelineABC的stream()方法支持多轮交互，memory.select()检索上下文
- **SRS 应用**：
  ```
  多轮检测中积累上下文：
    Round 1: 检测需求3.2.1 → memory记录关联组[3.2.1, 4.1.3, 表5.2.3]
    Round 2: 检测需求3.2.2 → memory.select()检索Round 1的上下文
             → 发现3.2.2与3.2.1结构相似 → 预期也有类似关联组
    Round 3: 检测需求4.1.1 → memory检索到与3.x节的交叉引用
  ```

#### Tier 3：辅助增强 ★

**8. Paper2Any Knowledge Base（RAG上下文理解）**
- **能力**：文档摄入→向量嵌入→语义检索
- **SRS 应用**：将SRS文档摄入KB，语义检索"与需求3.2.1相关的所有内容"

**9. DataFlow-WebUI NL2Pipeline（自然语言生成关联检测）**
- **能力**：NL2Pipeline自然语言→可执行Pipeline
- **SRS 应用**：
  ```
  用户输入: "找出需求3.2节中所有应该与表格匹配但缺失的项目"
  → NL2Pipeline自动生成:
    1. 提取3.2节所有需求项
    2. 查询合格性规定表中对应的行
    3. 对比找出缺失项
    4. 生成报告
  ```

### 上下文关联完整方案

```
┌─────────────────────────────────────────────────────────────────┐
│                  SRS 上下文关联识别 Pipeline                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─── 文档结构提取 ──────────────────────────────────────────┐  │
│  │ MinerU → content_list.json                                 │  │
│  │   ├── 章节层次树: 3→3.2→3.2.1 (Section上下文)             │  │
│  │   ├── 阅读顺序: 元素出现顺序 (顺序上下文)                  │  │
│  │   ├── 交叉引用: "见图3""见表5""见3.2.1节" (显式关联)      │  │
│  │   └── bbox/page_idx: 空间共现 (空间上下文)                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌─── 知识图谱构建 ──────────────────────────────────────────┐  │
│  │ DataFlow-KG domain_kg                                      │  │
│  │   节点: Section/Requirement/Constraint/Table/Figure/...   │  │
│  │   边: contains/refers_to/tracks/shows/derives/implies     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌─── 关联发现 ──────────────────────────────────────────────┐  │
│  │                                                             │  │
│  │  显式关联: 交叉引用解析 ("见图3" → 图3)                    │  │
│  │  结构关联: 同一章节/同一表格的元素                          │  │
│  │  语义关联: graph_reasoning链接预测 (隐含关联)              │  │
│  │  上下文关联: AgentFlow轨迹采样 (多跳依赖链)               │  │
│  │  规则关联: MemOS L2 Policies (GJB规则驱动的关联)          │  │
│  │                                                             │  │
│  │  → 输出: 关联组列表                                        │  │
│  │    [{req:3.2.1, constraint:4.1.3, table:5.2.3,            │  │
│  │      figure:3, formula:(2)}, ...]                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌─── 一致性检测 ────────────────────────────────────────────┐  │
│  │ 对每个关联组，检测元素间是否一致:                           │  │
│  │   文本 vs 表格: 数值/描述对比                               │  │
│  │   文本 vs 图片: VLM视觉理解对比                            │  │
│  │   表格 vs 表格: NL2SQL跨表查询对比                         │  │
│  │   约束 vs 公式: LaTeX→Z3逻辑求解                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 能力-需求映射总表

| DataFlow能力 | 多模态冲突检验 | 上下文关联 | 优先级 |
|-------------|--------------|-----------|--------|
| **AgentFlow MM-Doc + DocDancer** | ★★★ 跨模态推理检测冲突 | ★★ 轨迹采样构建关联链 | P0 |
| **DataFlow-KG domain_kg + graph_reasoning** | ★★ 图推理发现跨模态冲突 | ★★★ 链接预测+多跳推理发现关联 | P0 |
| **DataFlow-MM core_vision + pdf2vqa** | ★★★ VQA生成+VLM对比 | ★ 间接支持 | P0 |
| **DataFlow Core 评测算子 + Pipeline** | ★★★ 算子化冲突检测Pipeline | ★★ key链建模关联关系 | P0 |
| **MinerU深化(bbox/HTML/LaTeX/VLM)** | ★★★ 跨模态数据精确提取 | ★★★ 章节层次+交叉引用+空间上下文 | P0 |
| **DataMind GraphRAG + NL2SQL + Memory** | ★★ GraphRAG检索关联内容 | ★★★ 图谱遍历+NL2SQL+跨会话记忆 | P1 |
| **Paper2Any DataFlow-Agent框架** | ★★ 多Agent协作(VLM/表格/图表) | ★ KB语义检索 | P1 |
| **MemOS L1/L2/L3** | ★ 冲突模式积累 | ★★ 关联规则策略积累 | P2 |
| **OpenWorldLib Memory模块** | ★ 间接支持 | ★★ 有状态多轮上下文积累 | P2 |
| **LoopAI AnalyzerAgent** | ★ 漏检分析 | ★ 关联漏检分析 | P2 |
| **DataFlow-WebUI NL2Pipeline** | ★ 自然语言生成检测流程 | ★ 自然语言生成关联检测 | P2 |

---

## 落地建议

### Phase 0：立即可做（1-2周）

1. **MinerU深化**：保留bbox/page_idx/表格HTML/公式LaTeX，为跨模态对比提供精确数据
2. **DataFlow-MM pdf2vqa算子**：用 `PromptedVQAGenerator` 对SRS图片生成问题，与文本约束对比

### Phase 1：短期构建（2-4周）

3. **DataFlow Core Pipeline算子化**：将冲突检测建模为Pipeline算子链
4. **DataFlow-KG知识图谱**：用 `domain_kg` 重构SRS结构图谱，`graph_reasoning` 做链接预测发现隐含关联

### Phase 2：中期增强（1-2月）

5. **AgentFlow MM-Doc环境**：配置SRS Sandbox，用DocDancer做多跳跨模态冲突推理
6. **DataMind知识管理**：GraphRAG检索关联内容，NL2SQL查询表格，Memory积累关联规则

### Phase 3：长期闭环（2-3月）

7. **MemOS L1/L2/L3**：积累冲突模式和关联规则
8. **LoopAI闭环**：漏检分析→对抗样本合成→规则调优
