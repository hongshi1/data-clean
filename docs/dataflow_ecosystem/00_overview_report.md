# DataFlow 生态全景报告

> 北京大学 Data-Centric AI Group 开源工具链深度调研  
> 调研时间：2026-07-30 | 调研方法：5 Agent 并行 + 源码级分析  
> 主页：https://zwt233.github.io | 组织：https://github.com/OpenDCAI

## 1. 生态概览

DataFlow 生态是北京大学张文涛教授领导的 Data-Centric AI Group 构建的开源工具链，目标是为下一代模型提供**可复用、可扩展、可验证**的数据基础设施。课题组近五年发表 100+ CCF-A 论文，开源项目累计 80k+ GitHub Stars。

### 核心理念

> 从大语言模型、多模态大模型，到 Agentic LLM 与 World Model，持续布局 Data Infra，以更低成本、更低门槛和更高质量完成数据获取、解析、合成、清洗、评估与训练调度。

### 技术报告

- arXiv: https://arxiv.org/abs/2512.16676 (DataFlow Technical Report, 2025-12)

## 2. 六层架构

DataFlow 生态采用 L0-L5 六层架构，从数据入口到应用出口形成完整闭环：

```
L5  应用出口层    Paper2Any · OpenWorldLib
                   科研生产力与世界模型服务
    ─────────────────────────────────────────
L4  训练评估层    DataFlex · One-Eval · DataFlow-LoopAI
                   数据驱动闭环优化
    ─────────────────────────────────────────
L3  智能体编排层  AgentFlow · DataFlow-Skills · DataFlow-WebUI
                   智能体与工具编排
    ─────────────────────────────────────────
L2  数据资产工厂  DataFlow Core · DataFlow-MM · DataFlow-KG
                   Operator/Pipeline/Storage 抽象
    ─────────────────────────────────────────
L1  数据解析层    MinerU · MinerU-HTML · Flash-MinerU · RayOrch
                   解析与清洗中枢
    ─────────────────────────────────────────
L0  多源异构数据  PDF · HTML · CSV · 图片 · 代码 · 知识库 · 传感器

    ═════════════ 横切组件 ═════════════
    DataMind (知识管理) · MemOS (记忆OS) · Angel (分布式ML)
```

## 3. 各层组件详解

### L1 解析层（4 组件）

| 组件 | Stars | 核心功能 | 技术栈 |
|------|-------|---------|--------|
| **MinerU** | 76.2k | PDF/图片→Markdown/JSON 文档解析 | VLM(pipeline/vlm/hybrid三引擎), MinerU2.5-Pro模型 |
| **MinerU-HTML** | 279 | 网页主内容抽取 | 0.5B 轻量语言模型, ROUGE-N=0.9001 |
| **Flash-MinerU** | 65 | 高速文档解析 | Ray流水线并行, GPU利用率40%→90%+, 1.7×加速 |
| **RayOrch** | 9 | 分布式采集调度 | Ray框架, Flash-MinerU和DataFlow共同依赖 |

详见：[02_parsing_layer.md](02_parsing_layer.md)

### L2 数据资产工厂层（4 组件）

| 组件 | Stars | 核心功能 | 扩展模式 |
|------|-------|---------|---------|
| **DataFlow Core** | 7.1k | Operator/Pipeline/Storage 统一抽象 | 140+算子, 5+大Pipeline族, DataFlow-Agent |
| **DataFlow-MM** | 49 | 多模态数据资产 | 图像/视频/音频, 按modality分包 |
| **DataFlow-KG** | 43 | 知识图谱数据资产 | 9个算子包, domain_kg/graph_rag/graph_reasoning |
| **DataFlow-Table** | — | 表格数据资产 | 仓库不存在, 由Core的Text2SQL/KB清洗算子承担 |

**DataFlow Core 五大抽象**（源码级）：

| 抽象类 | 源码位置 | 核心方法 | 实现数 |
|--------|---------|---------|--------|
| `OperatorABC` | `core/operator.py:5-15` | `run(storage, keys)` | 140+ (Generic 80+/Domain 40+/Eval 20+) |
| `PipelineABC` | `pipeline/Pipeline.py:18-42` | `forward(storage)` + `compile()` | 5+族 × 3变体(API/GPU/CPU) |
| `LLMServingABC` | `core/llm_serving.py:5-35` | `generate_from_input()` | 4 (API/VertexAI/vLLM/SGLang) |
| `DataFlowStorage` | `utils/storage.py:14-68` | `read()/write()/step()` | 5 (Lazy/File/Batched/MyScaleDB/...) |
| `PromptABC` | `core/prompt.py:6-16` | `build()` | 200+ 模板 |

**Pipeline 编译-执行分离**（核心创新）：
- 编译阶段：`AutoOP` 拦截算子调用 → 构建 OperatorNode/KeyNode 依赖图 → key 累积校验
- 执行阶段：顺序执行算子，`storage.step()` 创建隔离上下文，引用计数管理 LLM 生命周期

详见：[01_dataflow_core.md](01_dataflow_core.md) · [03_data_assets.md](03_data_assets.md)

### L3 智能体编排层（3 组件）

| 组件 | Stars | 核心功能 | 技术亮点 |
|------|-------|---------|---------|
| **AgentFlow** | 129 | 统一Agent数据合成框架 | 三阶段(轨迹采样→选择→QA合成), 7种Sandbox环境 |
| **DataFlow-Skills** | — | 可复用技能库 | 6核心原语, 算子/流程/评测沉淀为可组合能力 |
| **DataFlow-WebUI** | 129 | 可视化工作台 | NL2Pipeline, 93.3%通过率, AI Agent辅助 |

**AgentFlow 三阶段合成**：
1. **轨迹采样**：LLM-driven Agent 迭代探索 Sandbox，记录工具调用与观察，构建分支轨迹树
2. **轨迹选择**：按深度/信息丰富度/工具多样性评分，选择高质量路径
3. **QA合成**：为选中路径生成多跳事实型QA，内置质量检查

**支持的 Sandbox 环境**：RAG · MM-Doc · DeepResearch · Code · GUI · Text2SQL · Embodied

**模型家族**：DocDancer(文档Agent) · RAGShaper(RAG Agent) · DeepResearch Agent · DataMix · RegMean++

详见：[04_agentic_traineval.md](04_agentic_traineval.md)

### L4 训练评估层（3 组件）

| 组件 | Stars | 核心功能 | 技术亮点 |
|------|-------|---------|---------|
| **DataFlex** | — | 动态数据选择/配比/重加权 | 基于LLaMA-Factory扩展, 11种算法 |
| **One-Eval** | — | 自动化评测框架 | NL2Eval(自然语言→评测报告), Bench Gallery |
| **DataFlow-LoopAI** | — | 闭环优化框架 | NL2Optimize, 6大Agent子图(Judge/Analyze/Obtain/Optimize/Improve/Config) |

**闭环优化流程**：
```
Start → Judge(评测) → Analyze(分析) → Obtain(获取) → Optimize(优化) → Improve(改进) → 循环
```

### L5 应用层（2 组件）

| 组件 | Stars | 核心功能 |
|------|-------|---------|
| **Paper2Any** | 2.7k | 科研资产生成（架构图/PPT/海报/Rebuttal/文献KB），13项子能力 |
| **OpenWorldLib** | 848 | 世界模型统一代码库，DataFlow/MM的世界模型扩展 |

### 横切组件（4 组件）

| 组件 | Stars | 核心功能 | 成熟度 |
|------|-------|---------|--------|
| **MemOS** | 10.4k | 大模型记忆OS，Multi-Cube+MemScheduler，35.24% token节省 | 生产级 |
| **Angel** | 6.8k | 分布式ML与图计算平台，参数服务器架构 | 成熟(3.2.0) |
| **DataMind** | 24 | Agentic知识中枢，6知识面+27工具，第二大脑 | 实验性(v0.3) |
| **DataFlow-WebUI** | 129 | NL2Pipeline可视化工作台 | 活跃迭代 |

详见：[05_apps_crosscutting.md](05_apps_crosscutting.md)

## 4. 竞品对比

| 维度 | DataFlow 生态 | Nemo-Curator | Data-Juicer |
|------|--------------|--------------|-------------|
| **数据合成** | ✅ AgentFlow多环境合成 | ❌ 无 | ❌ 无 |
| **编程范式** | PyTorch-like(Pipeline→Operator→Prompt) | 配置驱动 | 配置驱动 |
| **算子分类** | 科学多维分类(生成/过滤/评估/精炼) | 基本分类 | 基本分类 |
| **Agent能力** | ✅ DataFlow-Agent自动编排 | ❌ 无 | ❌ 无 |
| **记忆/知识管理** | ✅ DataMind + MemOS | ❌ 无 | ❌ 无 |
| **分布式训练** | ✅ Angel(参数服务器) | GPU集群 | 无 |
| **应用出口** | ✅ Paper2Any科研资产 | ❌ 无 | ❌ 无 |
| **闭环优化** | ✅ LoopAI | ❌ 无 | ❌ 无 |
| **GitHub Stars** | 80k+ | ~4k | ~4k |

## 5. 数据流全景

```
多源数据(PDF/HTML/CSV/图片/代码/知识库)
    │
    ▼ L1 解析层
MinerU/MinerU-HTML/Flash-MinerU → 结构化文档数据(Markdown/JSON)
    │
    ▼ L2 数据资产工厂
DataFlow Core Pipeline → 高质量训练数据(Operator链式处理)
    ├── DataFlow-MM → 多模态数据资产
    ├── DataFlow-KG → 知识图谱资产
    └── Text2SQL/KB清洗 → 表格/知识库资产
    │
    ▼ L3 智能体编排
AgentFlow → Agent训练数据(轨迹+QA)    DataFlow-Skills → 可复用技能
    │
    ▼ L4 训练评估
DataFlex → 动态数据选择/配比/重加权 → 微调LLM
One-Eval → 模型评测报告
    │
    ▼ L5 应用出口
Paper2Any → 科研图表/PPT/海报
OpenWorldLib → 世界模型数据服务
    │
    ▼ 闭环反馈
DataFlow-LoopAI: Judge→Analyze→Obtain→Optimize→Improve → 回到L2
```

## 6. 与 SRS 项目的结合

SRS 一致性检测项目已在使用 MinerU（L1），DataFlow 生态可系统性地增强项目各环节：

| 阶段 | SRS 现状 | DataFlow 增强 | 优先级 |
|------|---------|-------------|--------|
| 文档解析 | MinerU 基础解析 | bbox图文匹配 + 公式LaTeX→Z3 + 表格HTML直用 | P0 |
| 处理流程 | 20+ 独立脚本 | 算子化 + Pipeline编排 + 断点续跑 | P0 |
| 约束提取 | 串行调API | 并发推理 + 重试 + 限流 | P0 |
| 知识图谱 | 7720节点自研 | DataFlow-KG重构 + 链接预测 + 多跳推理 | P1 |
| Gold Standard | 仅3份 | AgentFlow合成→100+测试用例 | P1 |
| 评测 | 手动运行 | One-Eval NL2Eval自动化 | P2 |
| 假阳性优化 | 手动迭代 | LoopAI闭环(评测→分析→优化→改进) | P2 |
| 论文写作 | 手工图表 | Paper2Any架构图/PPT/海报 | P2 |

详见：[06_srs_integration.md](06_srs_integration.md)

## 7. 知识笔记索引

| 文件 | 内容 | 深度 |
|------|------|------|
| [01_dataflow_core.md](01_dataflow_core.md) | DataFlow Core 五大抽象、Registry、Pipeline系统、Agent | 源码级(行号引用) |
| [02_parsing_layer.md](02_parsing_layer.md) | MinerU/MinerU-HTML/Flash-MinerU/RayOrch | API+架构 |
| [03_data_assets.md](03_data_assets.md) | DataFlow-MM/KG扩展、扩展模式分析 | 源码+WebFetch |
| [04_agentic_traineval.md](04_agentic_traineval.md) | AgentFlow三阶段、Skills、DataFlex、One-Eval、LoopAI | 源码级(1113行) |
| [05_apps_crosscutting.md](05_apps_crosscutting.md) | Paper2Any、OpenWorldLib、DataMind、MemOS、Angel、生态全景 | WebFetch |
| [06_srs_integration.md](06_srs_integration.md) | SRS项目结合分析、分阶段路线图 | 综合分析 |

## 8. 关键发现与修正

调研过程中发现与生态主页描述的若干差异：

1. **DataFlow-Table 仓库不存在**：主页标注的 DataFlow-Table 独立仓库返回 404，OpenDCAI 全部 41 个仓库中无此仓库。表格处理由 DataFlow Core 的 Text2SQL 算子和 KB 清洗算子承担。

2. **Pipeline 族实际 6+ 族**：DeepWiki 显示不止主页描述的 5 大族，还有 PDF VQA、Code、Chemistry、Benchmark Eval 等族。

3. **论文标注需谨慎**：主页提及的 ProfiliTable (SIGKDD 2026) 和 QA-GraphRAG (VLDB 2026) 未能从 DataFlow 官方出版物中完全核实，KDD 2026 实际接收的是数学问题评估论文。

4. **AgentFlow 仍在早期**：虽然功能丰富（7种Sandbox环境、5个模型），但仅 129 stars，处于快速迭代期。

## 9. 总结

DataFlow 生态是目前最完整的 Data-Centric AI 开源工具链，覆盖从数据解析到应用出口的全生命周期。其核心创新在于：

1. **Pipeline 编译-执行分离**：AutoOP 拦截机制实现编译期 key 校验，避免运行期错误
2. **Agent 数据合成**：AgentFlow 首创统一多环境 Agent 数据合成框架
3. **闭环优化**：LoopAI 将评测-分析-优化-改进形成自动化闭环
4. **应用出口**：Paper2Any 将数据基础设施能力直接输出为科研生产力

对于 SRS 一致性检测项目，优先将核心脚本算子化（DataFlow Core）和深化 MinerU 使用即可获得显著收益，中期通过 AgentFlow 扩展 Gold Standard 和 DataFlow-KG 增强知识图谱可实现能力突破。
