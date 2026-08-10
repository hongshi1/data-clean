# Agentic RAG 先进实现调研报告

> 目标：为 GJB SRS 一致性检测项目提供可参考的 Agentic RAG 技术与代码架构。
> 调研方式：逐一访问 GitHub 仓库 README、源码目录结构与核心模块实现，并核对 arXiv 论文。
> 调研日期：2026-08-10
> 调研人：RAG 技术研究员（面向 SRS 一致性检测项目）

---

## 0. 调研对象一览

| # | 项目 | 定位 | 代码可用性 |
|---|------|------|-----------|
| 1 | Microsoft GraphRAG | 图索引+社区检测+全局/局部/漂移查询 | ✅ github.com/microsoft/graphrag |
| 2 | LightRAG (HKUDS) | 轻量图RAG（实体/关系抽取+双级检索） | ✅ github.com/HKUDS/LightRAG |
| 3 | RAGFlow (InfiniFlow) | 深度文档理解+Agentic RAG 引擎 | ✅ github.com/infiniflow/ragflow |
| 4 | LlamaIndex Agentic RAG | AgentWorkflow/Router/Planner/Tool | ✅ github.com/run-llama/llama_index |
| 5 | LangGraph Agent | 状态机多Agent（ReAct/Reflection/Plan-Execute） | ✅ github.com/langchain-ai/langgraph |
| 6 | MAGE-RAG (arXiv 2606.15906) | 多粒度自适应图证据+在线激活控制器 | ✅ github.com/laonuo2004/MAGE-RAG |
| 7 | TechRAG (arXiv 2606.01613) | Evidence-gated 多模态多Agent | ❌ 无公开代码（仅论文） |
| 8 | N2N-GQA (arXiv 2601.06603, AAAI'26) | 图证据组织的零样本多跳QA | ❌ 无官方代码 |
| 9 | LLM-Wiki | 增量编译式知识库（检索转编译） | ⚠️ karpathy 原仓库已下线，参考 nvk/llm-wiki |
| 10 | HippoRAG 1/2 (OSU) | 神经启发记忆：OpenIE+Personalized PageRank | ✅ github.com/OSU-NLP-Group/HippoRAG |
| 11 | Self-RAG | 反思token+按需检索+束搜索 | ✅ github.com/AkariAsai/self-rag |
| 12 | Corrective RAG (CRAG) | 检索质量评估器+纠错动作 | ✅ github.com/HuskyInSalt/CRAG |

---

## 1. 各项目深度分析

### 1.1 Microsoft GraphRAG — 图增强RAG（图索引 + 社区检测 + 三种查询）

**核心架构**
```
文档 → 文本分块 → LLM实体/关系抽取(3次共享上下文) → 知识图谱
     → Leiden社区检测(层次化) → 社区摘要(自底向上) → 社区报告
查询 → 三种搜索模式：
   Local Search  : 实体→邻域展开→关联社区报告→上下文组装
   Global Search : 社区报告 map-reduce 聚合（面向全局主题）
   DRIFT Search  : Agentic 多步图搜索（有状态、可追溯）
```

**代码组织**（`packages/` 多包结构）
```
packages/
├── graphrag/                     # 主包
│   └── graphrag/
│       ├── index/                # 离线索引流水线
│       │   ├── operations/       # 每步操作(实体抽取/社区检测/摘要/嵌入)
│       │   ├── workflows/        # 流水线编排(带依赖的workflow)
│       │   └── update/           # 增量更新
│       ├── query/                # 在线查询
│       │   └── structured_search/
│       │       ├── global_search/   # 社区报告聚合
│       │       ├── local_search/    # 实体邻域搜索
│       │       └── drift_search/    # Agentic漂移搜索
│       │           ├── state.py / action.py / search.py / primer.py
│       ├── llm/ storage/ cache/ vectors/   # 抽象存储层
│       └── cli/ config/ data_model/ prompts/
├── graphrag-common/ graphrag-llm/ graphrag-storage/ graphrag-vectors/ ...  # 解耦子包
```

**检索策略**：纯图检索。本地搜索以实体为中心做 K 跳邻域扩展；全局搜索以社区报告为单位做 map-reduce；向量仅用于实体嵌入匹配。无 BM25/混合检索。

**Agent机制**：DRIFT Search 是内置的 Agentic 检索器——`state.py` 维护检索状态（已访问实体、得分、操作历史），`action.py` 定义动作集合，搜索代理逐步选择"展开哪个实体/报告"，对成本与召回做预算控制（这与 MAGE-RAG 的控制器思想同源）。

**对我们项目的借鉴点**
- **索引/查询分离 + 结构化搜索分层**：`index` 与 `query` 完全解耦，查询端有多种"搜索策略"可插拔——对应我们"每条规则信号 = 一种搜索策略"的设计。
- **DRIFT 的 Agentic 图搜索状态机**：`state/action/search` 三段式代码结构是 Agentic 检索的最小可复用骨架。
- **社区摘要**可类比为"章节摘要层"：把 3.2.1 的文字、表格、图做成摘要节点，供全局视角查询。
- 缺点：实体抽取依赖 LLM 且成本高、有幻觉；对我们的领域，实体抽取可用确定性规则（需求ID/参数名）替代，规避其最大弱点。

---

### 1.2 LightRAG — 轻量图RAG（实体/关系抽取 + 双级检索）

**核心架构**
```
离线：分块 → LLM抽取实体/关系（含摘要）→ 图存储 + 向量存储 + KV存储
在线：查询 → (关键词提取) → 双级检索：
   local  : 实体级检索（查询→实体匹配→一阶邻域+关联chunk）
   global : 关系级检索（查询→关系匹配→关系链+关联chunk）
   naive  : 纯向量chunk检索
   hybrid/mix : 融合
→ 上下文组装(实体+关系+chunk, 按token预算裁剪) → 生成
```

**代码组织**（`lightrag/` 单包）
```
lightrag/
├── lightrag.py            # 核心类（索引+查询入口，双级检索在此组装）
├── operate.py             # 查询检索操作（local/global/naive/mix）
├── kg/                    # 图存储后端抽象（neo4j/networkx/memgraph/pgtable…）
├── llm/                   # LLM角色管理（EXTRACT/QUERY/KEYWORD/VLM四角色分离）
├── chunker/               # 四种分块策略（Fix/Recursive/Vector/Paragraph）
├── parser/                # 多模态解析引擎（MinerU/Docling/Native，侧车格式sidecar）
├── pipeline.py            # 文件处理流水线（并行调度、状态机）
├── api/ tools/ webui/ evaluation/
```

**检索策略**：图+向量混合，无 reranker 前为向量+图路径双召回；现支持 reranker（bge-reranker）。四角色 LLM 分离（抽取用快模型、生成用强模型）是工程亮点。

**Agent机制**：无显式 Agent；"查询模式选择"由用户/调用方决定。属于非 Agentic 的图RAG，但`mix`模式的多路召回融合是 Agentic RAG 中"Researcher 并行调用多工具"的雏形。

**对我们项目的借鉴点**
- **双级检索抽象**："实体级（精确、局部）"与"关系级（全局、跨段）"的二分，恰好对应我们"按需求ID精确召回"与"按功能/参数语义扩散召回"两级。
- **四角色 LLM 配置**：EXTRACT（快）/QUERY（强）分离 → 我们的"确定性信号提取（规则，零成本）"与"矛盾判定（强LLM）"分离。
- **Paragraph 语义分块 + 标题感知**：与 GJB 章节结构天然契合（3.2.1 等编号是天然边界）。
- **KV 缓存 LLM 抽取结果**：增量更新/删除时重算实体关系——我们重新解析文档时的缓存思路可照搬。
- 缺点：实体抽取质量直接决定图质量；军事术语密集的 SRS 需要定制抽取 prompt。

---

### 1.3 RAGFlow — 深度文档理解 RAG + Agentic 工作流

**核心架构**
```
文档摄入：DeepDoc(布局解析/表格结构/OCR/图理解) → 模板分块 → 向量+全文双引擎
Agentic 查询流水线（rag/advanced_rag/agentic_rag_graph.py）：
  formalize_question → route(意图路由) → pre_search(预检索) → planner(规划)
  → orchestrator_loop(循环: 工具调用/检索/评判) → formalize_answer
配套：sufficiency(证据充分性打分)、sufficiency_ladder(分级)、knowlege_compile
```

**代码组织**
```
rag/
├── advanced_rag/                # ★ Agentic 层
│   ├── agentic_rag.py           # RAGTools（工具集合）
│   ├── agentic_rag_graph.py     # Agentic状态图（上述节点流水线）
│   └── harness/                 # Agent编排器
│       ├── agent.py  route.py  planner.py  sufficiency.py  sufficiency_ladder.py
│       ├── orchestrator/  tools/  prompts/
├── flow/                        # 传统RAG流水线（chunker/parser/compiler/extractor）
├── graphrag/                    # 内置GraphRAG支持
├── llm/ nlp/ svr/               # LLM抽象/规则/服务端
deepdoc/                         # 深度文档理解（parser/vision/server）
```

**检索策略**：ES/Infinity 全文+向量双引擎（"multiple recall paired with fused re-ranking"）；工具调用（MCP、代码执行器、RAG工具）。

**Agent机制**：业界最完整的开源 Agentic RAG 之一——**意图路由 → 规划 → 编排循环 → 答案形式化**五段式；harness 中有 `planner.py`（把问题分解成子任务）与 `sufficiency.py`（检查答案证据是否充分：抽取数字/实体/谓词，检测数值冲突、实体缺失——见下）。

**对我们项目的借鉴点（本项目最值得抄工程结构的一个）**
- **`sufficiency.py` 的思路与我们的 Verifier 惊人相似**：它做 `extract_numbers → _detect_numeric_conflict`（检测数值矛盾！）、`extract_named_entities → _entity_present`（检测实体缺失）——这正是"找矛盾证据对"的雏形，可直接借鉴其实现。
- **五段式查询流水线**可直接映射为我们的检测流水线（见 §4）。
- **DeepDoc** 的表格结构还原 + 图文理解 = 我们处理能力表/合格性表/接口图的前端。
- 缺点：整体是"问答"导向而非"检测"导向，需要改造终态（输出证据对与判定而非答案）；部署重（Docker全家桶）。

---

### 1.4 LlamaIndex Agentic RAG — Agent 工作流框架

**核心架构**（`llama-index-core/llama_index/core/agent/workflow/`）
```
AgentWorkflow（预配置的Workflow）:
  FunctionAgent / ReActAgent / CodeActAgent（三种推理循环）
  → 工具调用（RouterTool路由 / PlanningTool规划 / ContextRetrieval检索 / 自定义工具）
  → 多Agent模式:
    ① AgentWorkflow swarm（线性切换，agent可handoff给其他agent）
    ② Orchestrator模式（主Agent把子Agent当工具调度）
    ③ 自定义Planner（DIY XML/JSON规划+命令式调用）
```

**代码组织**
```
llama-index-core/llama_index/core/
├── agent/workflow/          # AgentWorkflow核心
│   ├── base_agent.py  function_agent.py  react_agent.py  codeact_agent.py
│   ├── multi_agent_workflow.py  agent_context.py  workflow_events.py
│   └── prompts.py
├── query_engine/            # 非Agentic的RAG引擎(RetrieverQueryEngine等)
├── indices/  graph_stores/  postprocessor/  response_synthesizers/  # 检索组件库
└── composability/           # 子查询组合(SubQuestion等)
```

**检索策略**：工具化——检索器被包装为 Tool（QueryEngineTool/RetrieverTool），由 Agent 决定何时调用；支持 RouterTool 按描述路由、PlanningTool 拆分多步计划。

**Agent机制**：三种推理循环 + 三种多Agent模式；事件驱动（workflow_events）支持流式与人类介入。

**对我们项目的借鉴点**
- **"检索器=工具"抽象**：我们的 12 种规则信号直接包装成 12 个 Tool（ID精确匹配工具/表格行定位工具/章节层级工具/caption工具），Agent 按需调用——这是最贴合"确定性信号构建检索"的封装方式。
- **Planner（PlanningTool）+ Router（RouterTool）**的组合 = 我们 Planner/Researcher 分工的现成实现。
- **Orchestrator 多Agent**：主Agent调度"章节检索Agent/表格检索Agent/图检索Agent"。
- 缺点：框架重、抽象层级多；本地 GLM-5 API 接入需要适配（OpenAI兼容通常可直连）。

---

### 1.5 LangGraph Agent — 状态机多Agent（Planner→Executor→Verifier）

**核心架构**（`libs/langgraph/langgraph/`：Pregel 图执行引擎）
```
节点=函数，边=跳转，条件边=路由 → 状态机(StateGraph)驱动
examples/rag/ 官方Agentic RAG示例族：
  langgraph_agentic_rag.ipynb : Agent(有retriever工具) + grade_documents(相关性打分)
                                + rewrite(查询重写) + generate；条件路由循环
  langgraph_self_rag.ipynb    : Self-RAG变体（检索→生成→支持度评判→重试）
  langgraph_crag.ipynb        : Corrective RAG变体（检索质量评估→纠错）
  langgraph_adaptive_rag.ipynb: 完整闭环（路由→检索→打分→重写→生成→幻觉检查）
examples/reflection/          : 生成者+批评者双节点（Verifier）
examples/plan-and-execute/    : Planner→Executor→Replanner 循环
examples/multi_agent/         : 层级Agent团队
```

**代码组织**
```
libs/langgraph/langgraph/
├── graph/            # StateGraph/MessageGraph（状态机定义）
├── pregel/           # Pregel执行引擎（super-step、checkpoint、持久化）
├── channels/         # 状态通道（并发/合并语义）
├── func/             # 函数式agent封装
├── managed/ types.py/ stream/  # 托管状态/类型/流式
examples/              # 可运行notebook（rag/plan-and-execute/reflection/multi_agent）
```

**检索策略**：不内置检索——一切通过 ToolNode 接入（retriever、web search 都是工具）；支持与任意向量库/图库组合。

**Agent机制**：最成熟的"状态机多Agent"范式：节点即函数、显式状态、条件边路由、checkpoint 持久化；`grade_documents`（相关性评分）+ `rewrite`（查询重写）+ 条件回环 是 Planner→Researcher→Verifier 的最小闭环模板。

**对我们项目的借鉴点**
- **Plan-Execute-Replan**（examples/plan-and-execute）：Planner 生成子任务清单 → Executor 逐项执行（每项=一次"召回某需求的所有位置"）→ 结果不足则 Replan——与我们"按需求ID多路召回"的循环天然吻合。
- **Reflection 双节点**（Verifier 批评生成者）：可扩展为"矛盾检测器批评证据收集过程"。
- **条件边的显式路由**：`retrieve→grade(合格?)→generate | rewrite→retrieve` 这种图结构清晰可解释，适合论文展示。
- Pregel 的 checkpoint/流式对大规模 16 文档扫描很实用。
- 缺点：无内置索引/图；图论层面的"证据图"需自己建（可叠加在 NetworkX 上）。

---

### 1.6 MAGE-RAG（arXiv 2606.15906，github.com/laonuo2004/MAGE-RAG）★ 方法上最相近

**核心架构**
```
离线：MinerU解析PDF → 构建"多粒度证据图"：
  节点：页面节点 + 页内元素节点(段落/标题/表格/图片/图表，带摘要+bbox+图像引用)
  边：包含关系、阅读顺序、布局邻接、章节层级、语义邻居（ColPali嵌入近似）
在线（Agentic 证据控制）：
  ColPali 视觉检索 → 初始Top-k页面(ActivatePage入口)
  → 在线证据控制器：维护状态 Inactive/Active/Opened/Pruned，
    把"当前证据+候选动作+历史trace"序列化为XML交给评估器，
    迭代选择动作：ActivateNode / OpenNode / SearchEvidence / PruneNode / Stop
  → 渲染器：把非剪枝的页面与元素组织成"页面对齐XML"+页面截图/局部裁剪
    → 交给 LVLM Reader 生成（显式预算控制）
```

**代码组织**（研究型仓库，Hydra 驱动）
```
main.py / configs/            # 实验入口+配置
baselines/magerag/            # ★ 核心
├── state.py                  # 证据状态机(四态)
├── evaluator.py              # 控制器决策LLM
├── builder.py                # 证据子图构建
├── retrieval.py              # ColPali页面检索
└── renderer.py               # 结构化多模态读者输入渲染
benchmarks/evidence_graph/    # 离线图构建(节点/边/摘要/语义边/嵌入)
benchmarks/{mmlongbench,longdocurl}/  # 评测适配
analysis/                     # 论文表格/预算曲线/轨迹分析
```

**检索策略**：多粒度——页面级（ColPali 视觉召回）作入口，元素级（节点嵌入）作扩展；边类型全部结构/语义可解释；查询时按预算动态剪枝。

**Agent机制**：**显式证据状态机 + 预算控制 + 可审计轨迹**。这是所有调研项目中与我们"检索→找矛盾证据对"最接近的范式：
- 四态（Inactive/Active/Opened/Pruned）对应"该位置是否与目标需求相关"的证据生命周期；
- 动作集中的 `SearchEvidence`（语义扩展）与 `PruneNode`（噪声剪枝）正是"证据充分性 vs 上下文噪声"博弈的解法。

**对我们项目的借鉴点（最高优先级）**
- **证据图用"确定性结构边"构建**：我们的 12 种规则信号（ID匹配/表格结构/章节层级/图caption）恰好对应它的边类型——包含(章节→条款)、阅读顺序(正文↔表格↔用例)、布局邻接(图在3.2.1下方)、章节层级(3.2↔3.2.1)、语义邻居(参数名对齐)。MAGE-RAG 的图构建代码是现成的多粒度图模板。
- **状态机四态 → "一致性检测的证据生命周期"**：Active=候选矛盾位置，Opened=已读到内容，Pruned=判定无关。
- **结构化渲染**：把"同一需求的所有位置"渲染成一份结构化证据（含来源位置标记）再交给检测 LLM——这就是方向A输出"条目"的机器可读形态。
- **可审计轨迹**：激活/打开/剪枝记录 = 论文需要的"为什么召回/丢弃这些位置"的归因链。
- 缺点：面向 PDF 问答、LVLM 重（需 GPU）；改造为 markdown SRS 后视觉部分可弱化为表格/图元数据。

---

### 1.7 TechRAG（arXiv 2606.01613）— 无公开代码，仅架构参考

**核心架构**（从摘要复原，作者 Kanwar Bharat Singh，领域=技术文献推理）
```
查询意图分类 → 文本/视觉双查询重写 → 混合检索(FAISS+BM25)+cross-encoder重排
→ Neo4j知识图谱的图引导chunk遍历扩展（LLM实体抽取+OpenAlex作者验证+引文解析）
→ 视觉证据检索(ColSmol late-interaction + MUVERA固定维编码 + MaxSim重排)
→ 证据充分性评分(100分制，规则+LLM混合评审) → 不足则带漂移防护的重写重试
→ 外部学术库检索(optimize-search-vet循环) → 多模态证据合并去重 → 引文完整性校验
→ Planner / Researcher / Writer / Critic 四Agent生成 + 自纠错修订
```

**借鉴点**
- **Evidence-Gated（证据门控）**：明确"先评审证据充分性，不足才重试"的循环——这正是我们 Verifier 的核心（收集到的位置是否足够支撑"一致/不一致"判定）。
- **100 分制规则+LLM 混合评分**：与 RAGFlow 的 sufficiency 打分思路一致，可合看。
- **四Agent分工**（Planner/Researcher/Writer/Critic）是最标准的"多Agent RAG"命名，可直接映射到我们的检测流程。
- **双查询重写**：文本重写 + 视觉重写——对应我们"需求ID精确重写 + 语义扩散重写"双路径。

---

### 1.8 N2N-GQA（arXiv 2601.06603，AAAI'26 Workshop）— 无官方代码

**核心架构**（零样本，混合表格-文本多跳QA）
```
粗检索(噪声列表) → 动态证据图构建：
  节点=文档，边=语义关系（LLM判定）
  → GraphRank（语义相关分×图中心性 融合排序）
  → 结构化查询规划 → 迭代图证据收集
  → Bridge-Aware Hybrid Selector（桥接文档选择器：识别连接推理步骤的"桥"）
  → 精选上下文 → 生成叙述性答案
效果：OTT-QA 上比强基线 +19.9 EM；48.80 EM 追平微调检索系统
```

**借鉴点（概念层面极有价值）**
- **"桥接文档"概念**：多跳推理中，证据A与证据C靠"桥B"连接。映射到 SRS：正文 3.2.1 里"数据率≤10Mbps"与合格性表"数据率=5Mbps"的矛盾，桥就是"数据率"这个参数节点。**"找矛盾证据对" = "找以同一实体为桥的多条证据路径"**——这是我们可以直接写进方法论文的技术语言。
- **图中心性融合**（GraphRank）：语义分数 × 图中心性，避免只靠向量相似度。
- 缺点：无代码、细节不可复现；且面向开放域问答而非一致性判定。

---

### 1.9 LLM-Wiki（karpathy 原创已下线；参考 nvk/llm-wiki、llm-wiki-agent）

**核心思想**：**把"每次查询时检索"换成"一次性编译+增量维护"**——对原始文档做一次性深度处理，产出互链的 wiki 页面（概念页+引用+审计），查询时直接读编译产物，而不是反复 RAG。

**借鉴点**
- 与我们的**方向A（上下文聚合）**哲学一致：先离线把"同一事物"聚合好（wiki 页 = 聚合条目），检测时直接取条目对比，而非每次重新聚合。
- 其"审计（audit）+ 引用校验"流程 = 一致性检测的雏形。
- 工程上 llm-wiki-agent（SamurAIGPT）给出无需 API key 的本地实现路径。
- 注意：编译式方法对"新增/修订文档"需要增量维护，16 份 SRS 静态场景下完全够用。

---

### 1.10 HippoRAG 1/2（OSU-NLP-Group）— 联想式检索

**核心架构**
```
离线：OpenIE抽取(实体,关系)三元组 → 知识图谱 + 实体嵌入
在线：查询→实体链接(LLM) → Personalized PageRank(以查询实体为源，图上概率传播)
    → 取pagerank高分节点关联的chunk（"联想"出间接相关证据）
HippoRAG 2：结合稠密检索（NV-Embed等）检索passage → 图补充跨passage关联（关联性得分加权）
```

**代码组织**
```
src/hipporag/
├── HippoRAG.py            # 顶层：index() / rag_qa()
├── embedding_store.py     # passage/entity/fact 三套向量统一管理
├── rerank.py              # 重排+过滤
├── information_extraction/  # OpenIE(openai/vllm离线批量)
├── embedding_model/ llm/ evaluation/ prompts/ utils/
```

**检索策略**：图概率传播（PPR）——与拓扑（向量kNN）本质不同：它是"多跳联想"而不是"相似度召回"。

**借鉴点**
- **PPR 联想检索**是"找桥"的系统化方法：给定"数据率"实体，PPR 能自然落到正文+表格+合格性表中所有提到它的位置——这正是我们方向A"同一事物分布位置召回"的目标，且**不依赖LLM抽取**（可用规则构造图+实体链接）。
- 实体链接（LLM）→ 可替换为我们的确定性 ID/参数匹配。
- 代码质量高、依赖轻，是"图+RAG"里最容易改造的骨架。
- 缺点：OpenIE 抽取质量是瓶颈；对我们可用"参数族词典（srs_kb.json）+规则"替代。

---

### 1.11 Self-RAG（AkariAsai）— 反思token

**核心机制**：训练生成模型输出**反思token**：`[Retrieval](是否检索)`、`[Relevant](检索是否相关)`、`[Supported](生成是否被证据支持)`、`[Utility](整体质量)`；分段束搜索选择最优输出。按需检索（阈值0.2触发），可多次检索。

**代码组织**：`retrieval_lm/`（推理+检索器）、`data_creation/`（critic/generator 训练数据生成）、`run_short_form.py / run_long_form_static.py`。

**借鉴点**
- "**支持度判定 token**"（Supported / Groundness）≈ 我们 Verifier 的"证据对是否一致"判定——不过我们用提示词让通用 LLM 输出结构化判定即可，不必微调。
- **按需检索**：不是所有需求都要全量扫描——先快速判定"该需求在几个位置出现"，少则跳过，多则深入。
- 缺点：需要微调模型（我们应取"prompt工程版"而非"训练版"）；LangGraph 已有其免训练变体（langgraph_self_rag.ipynb）。

---

### 1.12 Corrective RAG / CRAG（HuskyInSalt）— 纠错式检索

**核心机制**：轻量**检索评估器**（T5微调）对整批检索结果打置信度 → 三态动作：
- Correct → 用"分解-重组"（decompose-then-recompose）过滤噪声后生成；
- Incorrect → 查询重写+Web检索补充；
- Ambiguous → 正确+外部知识混合。
评估器数据含正确/错误/模糊三类标签（PopQA等）。

**代码组织**：`scripts/`（internal/external/combined_knowledge_preparation）+ `run_crag_inference.sh` + 评估器训练脚本。结构简单，**评测数据制备脚本可参考**。

**借鉴点**
- **"检索结果整体质量评分 → 触发纠错动作"**：对应我们的"召回完整性检查"——若某需求只在一个位置出现（漏召回），触发重写/换工具再找。
- 三态动作（正确/错误/模糊）可映射到证据收集中"已覆盖/缺失/存疑"。
- 缺点：评估器需微调；我们可用规则（如"ID出现在TOC但正文缺失"）做免训练版本。

---

## 2. Agentic RAG 通用范式总结

对以上 12 个实现归纳，Agentic RAG 的**必备模块**（按出现频率）：

| 模块 | 作用 | 代表实现 |
|------|------|---------|
| **意图/任务解析**（formalize） | 把用户问题转成可执行的检索任务 | RAGFlow formalize_question、TechRAG intent classify、N2N-GQA query planning |
| **规划器 Planner** | 分解子任务/规划检索步骤 | RAGFlow planner、LlamaIndex PlanningTool、LangGraph plan-and-execute、TechRAG Planner |
| **多工具检索器 Researcher** | 并行/串行调用多路检索（向量/图/表格/规则/外部） | LightRAG mix、RAGFlow pre_search+orchestrator、LangGraph ToolNode、GraphRAG DRIFT |
| **证据组织层**（证据图/上下文构建） | 把检索结果组织成结构化证据，控制噪声 | MAGE-RAG 证据图+渲染器、GraphRAG 上下文构建、N2N-GQA 证据图 |
| **评估/门控 Verifier** | 评估证据充分性/相关性，决定继续检索还是生成 | TechRAG 100分制、RAGFlow sufficiency、CRAG 评估器、Self-RAG 反思token、LangGraph grade_documents |
| **纠错/重写** | 证据不足时重写查询或换工具重试 | CRAG 重写+Web、LangGraph rewrite、TechRAG drift-guarded retry、MAGE-RAG SearchEvidence |
| **生成器 + 引用/归因** | 生成终答并给出可追溯引用 | TechRAG Writer+引文校验、RAGFlow citations、MAGE-RAG trace |
| **状态与轨迹** | 全程状态管理、可审计 | LangGraph StateGraph/checkpoint、MAGE-RAG 四态+XML轨迹、GraphRAG drift state |
| **预算控制** | token/步数/成本显式约束 | MAGE-RAG budgets、GraphRAG DRIFT、TechRAG 100分制 |

**两个被反复验证的关键设计判断**：
1. **证据不是"Top-k 列表"而是"图/状态"**——GraphRAG、MAGE-RAG、N2N-GQA、HippoRAG 四条独立路线收敛到同一结论：多跳/一致性任务中，检索结果的组织方式（图结构、关系、状态）比检索本身更决定成败（N2N-GQA 的 +19.9 EM 是量化证据）。
2. **"先评估再生成，不足则重试"是闭环的核心**——Self-RAG（反思token）、CRAG（三态纠错）、TechRAG（100分门控）、RAGFlow（sufficiency）、LangGraph（grade→rewrite）全部内置这一循环。

---

## 3. 面向"SRS一致性检测"的 Agentic RAG 架构建议

### 3.1 总体设计：SRS-Evidence Agent（三层 + 确定性证据图）

```
┌────────────────────────── 离线（一次构建，类似方向A）──────────────────────────┐
│  SRS文档(markdown+图+表)                                                       │
│   → 12种确定性规则信号提取（ID匹配/表格结构/章节层级/图caption/参数族词典…）    │
│   → 构建【确定性证据图 EvidenceGraph】：                                        │
│      节点：条款/句子/表格行/图/用例步骤/追溯行/合格性行（带章节位置+来源）        │
│      边：containment(章节↔条款) · reading_order(正文↔相邻表图) ·                │
│           section_hierarchy(3.2↔3.2.1) · id_link(同一需求ID) ·                  │
│           entity_alignment(同一参数/功能名，桥接边) · caption_ref(图↔正文引用)    │
│    （图构建完全确定性、零LLM成本、可审计——用规则而非抽取，规避GraphRAG弱点）    │
└──────────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────── 在线（每需求ID一次检测任务）──────────────────────────┐
│ Planner(任务解析): 输入"需求ID/功能名" → 输出检测任务书:                        │
│     {目标实体, 检索策略清单[12种信号工具的子集], 期望位置类型[正文/能力表/       │
│      用例表/合格性表/追溯表/用例图], 预算}                                      │
│ Researcher(多路召回): 按任务书并行调用信号工具 → 证据激活(Active)               │
│     · 精确工具: 需求ID索引表(全文档扫描匹配)、表格行列定位、章节层级定位          │
│     · 语义工具: 参数名/功能名嵌入匹配、PPR联想(找桥)、图caption解析               │
│     → 证据子图收敛：以目标实体为锚，沿id_link/entity_alignment展开，             │
│       打开(Opened)所有位置的原文，剪枝(Pruned)无关内容                           │
│ Verifier(证据门控+矛盾判定): 两阶段                                   │
│     阶段1 充分性门控: 证据是否覆盖了任务书要求的全部位置类型？                  │
│          缺失→触发 Researcher 重试(改工具/语义扩散)，达到预算才停(CRAG式)        │
│     阶段2 一致性判定: 对证据对(正文,表格行)执行12类确定性规则检测                   │
│           + 剩余不确定对交给LLM（结构化输出: 一致/不一致/无法判定+理由+引用）      │
│      输出: 一致性报告{证据对列表, 判定, 矛盾类型, 归因轨迹}                       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 三个 Agent 的具体设计（对照调研结论）

**Planner（等价于 RAGFlow planner / LangGraph plan-execute / TechRAG Planner）**
- 输入：需求ID/功能名；输出：结构化任务书（JSON）。
- 关键设计：任务书显式声明"该需求应在哪些位置出现"（3.2.1正文、能力表、用例表、合格性表、追溯表、用例图）——这是领域知识（GJB 438C 章节模板）给的强先验，Planner 本质是"模板匹配+参数填充"，可主要用规则、LLM 只处理模糊名（如"数据获取"与"数据采集"是否同实体）。
- 借鉴：RAGFlow 的 `route` 节点（意图路由）+ `planner` 节点（子任务清单）。

**Researcher（等价于 MAGE-RAG 控制器 / GraphRAG DRIFT / LangGraph ToolNode）**
- 工具集 = 12 种规则信号封装成工具 + 2 个语义工具（参数名嵌入、PPR联想）。
- 关键设计：**状态机四态**（MAGE-RAG）：目标实体的每个候选位置从 Inactive→Active（信号命中）→Opened（读取原文）或 Pruned（判定无关）；动作集 = ActivateNode / OpenNode / SearchEvidence（沿桥边扩散）/ PruneNode / Stop。预算（最多打开N个位置、最多N次SearchEvidence）显式控制。
- 借鉴：MAGE-RAG `state.py / evaluator.py / builder.py / renderer.py` 的结构直接可改造；HippoRAG PPR 作为"找桥"的默认扩散算法；CRAG 三态作为"召回完整性"纠错。

**Verifier（等价于 RAGFlow sufficiency / Self-RAG 反思 / TechRAG 100分制 + 我们自己的规则检测器）**
- 阶段1 充分性：规则版"100分制"——任务书要求的位置类型是否都被证据覆盖（每类算一个覆盖率分）；低于阈值触发重试。
- 阶段2 一致性：先跑 12 类确定性规则（同一参数不同值、正文vs表格矛盾、约束违反如子时间之和>总预算、ID重复等，即项目已有的 srs_consistency_checker 逻辑），LLM 只处理规则无法定论的证据对；LLM 输出要求结构化：`{evidence_pair, claim_a, claim_b, verdict: consistent/inconsistent/undecidable, evidence_gaps}`。
- 借鉴：RAGFlow `sufficiency.py` 的数值冲突检测（`_detect_numeric_conflict`）可先抄；Self-RAG 的按需检索（少位置需求跳过阶段2）；N2N-GQA 的"桥"概念用于解释矛盾路径（矛盾 = 桥节点上两条证据链的取值分歧）。

### 3.3 与项目两个方向的关系
- **方向A（上下文关联）** = 离线确定性证据图 + 在线 Researcher 的证据子图收敛（条目=锚实体+其打开的证据集合）。
- **方向B（一致性检测）** = Planner 任务书 + Verifier 两阶段。
- 流水线不变，但 Agentic 循环让"召回不全→补充召回"成为闭环，这正是纯静态流水线做不到的。

---

## 4. 推荐参考实现（Top 3 + 1补充）

### ① MAGE-RAG（github.com/laonuo2004/MAGE-RAG）★ 方法参考首选
**理由**：唯一把"多粒度证据图 + 显式状态机 + 预算控制 + 可审计轨迹"完整实现并开源的项目；其证据图的五种边类型（包含/阅读顺序/布局邻接/章节层级/语义邻居）与我们的 12 种规则信号一一对应；`baselines/magerag/{state,evaluator,builder,retrieval,renderer}.py` 模块划分可直接映射为我们的检测流水线；MinerU 解析链路与项目现有工具栈一致。缺点（LVLM/GPU 依赖）在文本为主、图为元的 SRS 场景可裁剪。

### ② RAGFlow（github.com/infiniflow/ragflow）★ 工程参考首选
**理由**：工程最完整的开源 Agentic RAG：DeepDoc 深度文档理解（表格/图）解决我们的多模态解析；`agentic_rag_graph.py` 的五段式流水线（formalize→route→pre_search→planner→orchestrator）就是我们要的骨架；`harness/sufficiency.py` 的数值冲突与实体缺失检测与"找矛盾证据对"高度同源。重点抄：agentic 流水线组织 + sufficiency 实现 + 表格解析。

### ③ LangGraph（github.com/langchain-ai/langgraph）★ 编排参考首选
**理由**：状态机编排的工业标准；`examples/rag/langgraph_agentic_rag.ipynb`（grade+rewrite+generate 闭环）、`examples/plan-and-execute`（Planner-Executor-Replanner）、`examples/reflection`（Verifier）三个示例拼起来就是我们 Planner/Researcher/Verifier 三层的现成实现；Pregel 的 checkpoint 支持断点续扫 16 份文档；显式图结构便于论文画架构图。缺点：不含索引/图，需叠加我们的证据图。

### 补充参考：HippoRAG 2（OSU-NLP-Group/HippoRAG）
若想快速验证"图+向量"的联想召回（找桥）基线，这是最轻量的骨架：`index()/rag_qa()` 两入口、PPR 检索、依赖少，把 OpenIE 替换为我们的参数族词典+规则即可做第一个基线系统。

---

## 附：调研中确认的事实性备注
- TechRAG 与 N2N-GQA 均未找到官方公开代码（GitHub 同名仓库均为无关项目）；N2N-GQA 的 arXiv 页面亦无代码链接。
- karpathy/llm-wiki 原仓库已不可访问（404），其理念的最佳可用实现为 nvk/llm-wiki（llm-wiki.net，支持多运行时）与 SamurAIGPT/llm-wiki-agent。
- LangGraph 官方教程已迁移至 docs.langchain.com；仓库内 `examples/` 目录保留全部 RAG 示例 notebook（含 self-rag/crag/adaptive/agentic 四个变体）。
- LlamaIndex 文档已迁移至 docs.llamaindex.ai（agent workflow 相关在 /python/framework/understanding/agent/）。
