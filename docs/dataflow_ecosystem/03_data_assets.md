# DataFlow 生态 L2 数据资产工厂层扩展组件调研

> 调研对象：北京大学 Data-Centric AI Group（OpenDCAI）开源的 DataFlow 工具链
> 调研范围：L2 数据资产工厂层的三类扩展组件 —— 多模态（MM）、知识图谱（KG）、表格（Table）
> 调研日期：2026-07-30
> 调研方法：WebFetch 抓取 GitHub 仓库 + 本地 DataFlow 源码分析 + DeepWiki 算子框架文档

---

## 0. 调研结论速览（重要）

在正式展开前，先给出一条关键事实校验结论，避免后续误导：

| 任务预设的扩展组件 | 实际是否存在 | 说明 |
| --- | --- | --- |
| **DataFlow-MM**（多模态） | ✅ 存在 | [github.com/OpenDCAI/DataFlow-MM](https://github.com/OpenDCAI/DataFlow-MM)，49★ |
| **DataFlow-KG**（知识图谱） | ✅ 存在 | [github.com/OpenDCAI/DataFlow-KG](https://github.com/OpenDCAI/DataFlow-KG)，43★ |
| **DataFlow-Table**（表格数据） | ❌ **不存在** | `https://github.com/OpenDCAI/DataFlow-Table` 返回 404；OpenDCAI 组织 41 个仓库中无此仓库 |
| **DataFlow-Graph** | ❌ 不作为独立仓库 | KG 即图谱组件，无单独 DataFlow-Graph 仓库 |
| **ProfiliTable (SIGKDD 2026)** | ❌ **未找到** | DataFlow 官方出版物列表中无此论文；KDD 2026 收录的是数学问题评估论文 |
| **QA-GraphRAG (VLDB 2026)** | ❌ **未找到** | DataFlow 官方出版物列表中无此论文；DataFlow-KG 的 GraphRAG 能力来自 `graph_rag` 算子包 |

**因此，本笔记对三类组件的处理方式为：**
1. **DataFlow-MM / DataFlow-KG**：基于实际仓库内容做深度分析；
2. **DataFlow-Table**：明确标注"未找到独立仓库"，转而分析 DataFlow 生态中**实际承担表格/结构化数据处理职责**的组件（Text2SQL 流水线、知识库清洗流水线、`pandas_operator` 等），为任务中"表格数据资产"需求提供等价落点；
3. **论文标注**：仅引用经核实的 DataFlow 官方出版物，对任务提及但未核实的论文明确标注"未核实"。

---

## 1. DataFlow 生态与 L2 层定位

### 1.1 DataFlow 套件四层结构

DataFlow README 将整个工具链描述为"由四个紧密集成的层组成"：

| 层 | 组件 | 角色 |
| --- | --- | --- |
| 基础设施 | [DataFlow](https://github.com/OpenDCAI/DataFlow) Core（7.1k★） | 核心算子框架：Operator / Pipeline / Storage / LLMServing 抽象 |
| 技能层 | [DataFlow-Skills](https://github.com/OpenDCAI/DataFlow-Skills) | 算子开发、流水线构建教程 |
| 可视化层 | [DataFlow-WebUI](https://github.com/OpenDCAI/DataFlow-WebUI) | 拖拽式 pipeline 编辑 + 自然语言交互工作台 |
| 分发层 | **DataFlow-Ecosystem** | 标准化算子注册的模块化分发层，允许领域模块（DataFlow-MM、DataFlow-AI4S 等）在统一抽象下贡献可扩展库 |
| 编排层 | [RayOrch](https://github.com/OpenDCAI/RayOrch) | 基于 Ray 的分布式计算调度与资源管理 |

### 1.2 L2 数据资产工厂层的含义

按本项目调研框架的分层约定，DataFlow 生态可映射为：

- **L1 解析层**：MinerU 集成、PDF→Markdown/VQA 转换（Core 内 `pdf2vqa`、`knowledge_cleaning` 算子 + [Flash-MinerU](https://github.com/OpenDCAI/Flash-MinerU) 加速层）；
- **L2 数据资产工厂层**：以 Core 为基础，扩展出面向特定数据形态的资产处理能力，即本笔记聚焦的 **MM（多模态资产）/ KG（图谱资产）/ 表格类资产** 三类；
- **L3/L4 下游层**：数据评测（[One-Eval](https://github.com/OpenDCAI/One-Eval)、[Data-Preparation-Bench](https://github.com/OpenDCAI/Data-Preparation-Bench)）、数据为中心训练（[DataFlex](https://github.com/OpenDCAI/DataFlex)）、RAG 应用（[DataMind](https://github.com/OpenDCAI/DataMind)）。

L2 扩展组件的核心价值在于：**复用 Core 的 Operator/Pipeline/Storage 抽象，把某类数据资产的"解析→清洗→生成→评测"流程封装为可分发、可组合的算子库**。

### 1.3 三组件对比总表

| 维度 | DataFlow-MM | DataFlow-KG | 表格类资产（无独立仓库） |
| --- | --- | --- | --- |
| 仓库 | [DataFlow-MM](https://github.com/OpenDCAI/DataFlow-MM) | [DataFlow-KG](https://github.com/OpenDCAI/DataFlow-KG) | 无；由 Core 内 Text2SQL / KB清洗 / pandas 算子承担 |
| Stars / Commits | 49★ / 78 commits | 43★ / 125 commits | — |
| 数据形态 | 图像 / 视频 / 音频 / 图像生成 | 知识图谱（7种范式） | 结构化表格、SQL 数据库 |
| CLI 入口 | `dataflowmm init` | `dfkg init` | `dataflow init`（Core） |
| 算子组织 | 按 modality 分包 | 按图谱范式分 9 个包 | 按任务域分（text2sql/knowledge_cleaning） |
| Python 版本 | 3.12 | ≥3.10 | ≥3.10 |
| 可选依赖 | `[audio]` / `[image]` | `[vllm]`（本地GPU） | Core requirements |
| 与 Core 关系 | 继承 OperatorABC，注册到 OPERATOR_REGISTRY | 继承 OperatorABC，独立 CLI（dfkg）但同构 | Core 原生算子 |

---

## 2. DataFlow-MM（多模态数据资产）

### 2.1 核心功能

[DataFlow-MM](https://github.com/OpenDCAI/DataFlow-MM) 是 DataFlow 的**多模态扩展版本**，定位为"为多模态大模型（MLLM）准备数据"。其核心目标是从图像、视频、音频等噪声源中解析、生成、处理并评测高质量多模态数据。

支持的四类模态资产（对应 HuggingFace demo 数据集）：
- **图像**：[dataflow-demo-image](https://huggingface.co/datasets/OpenDCAI/dataflow-demo-image)
- **视频**：[dataflow-demo-video](https://huggingface.co/datasets/OpenDCAI/dataflow-demo-video)
- **音频**：[dataflow-demo-audio](https://huggingface.co/datasets/OpenDCAI/dataflow-demo-audio)
- **图像生成**：[dataflow-demo-image-gen](https://huggingface.co/datasets/OpenDCAI/dataflow-demo-image-gen)

### 2.2 算子类型与 Pipeline

DataFlow-MM 完全沿用 Core 的算子分类法（生成 / 过滤 / 评测 / 精炼），并扩展到多模态场景。从 Core 中可观察到的多模态相关算子基类包括：
- `core_vision/generate/prompted_vqa_generator.py` —— 视觉问答生成
- `core_speech/generate/speech2text_generator.py` —— 语音转文本
- `pdf2vqa/` —— PDF 视觉 QA 提取（PDF_Merger / MinerU2LLMInputOperator / QA_Merger）

可选依赖按模态隔离：`pip install -e ".[audio]"` 或 `pip install -e ".[image]"`，体现"按需装载"的模块化设计。

### 2.3 与 DataFlow Core 的关系

DataFlow-MM 是**典型的 L2 扩展**：
1. **继承抽象**：复用 Core 的 `OperatorABC`、`DataFlowStorage`、`LLMServingABC`；
2. **独立 CLI**：提供 `dataflowmm init` 初始化工作空间（类比 Core 的 `dataflow init`）；
3. **注册机制**：通过 Ecosystem 分发层，算子扫描注册到主仓库 `OPERATOR_REGISTRY`；
4. **文档独立**：有独立的 [DataFlow-MM-Doc](https://OpenDCAI.github.io/DataFlow-MM-Doc/)。

### 2.4 多模态数据质量评估方法

DataFlow 系统的评测算子覆盖六个维度（难度/正确性/质量/类别/格式/多样性）。多模态场景下，相关的已发表论文为 **MM-Verify (ACL 2025)** —— "Enhancing Multimodal Reasoning with Chain-of-Thought Verification"，用于多模态推理的数据处理与评估验证。

---

## 3. DataFlow-KG（知识图谱数据资产）

### 3.1 核心功能

[DataFlow-KG](https://github.com/OpenDCAI/DataFlow-KG)（DataFlow Knowledge Graph）是**LLM 驱动的知识图谱处理库**，构建在 DataFlow 生态之上。它把图谱工作流从"孤立脚本"组织为"按图谱类型分组的算子包"，可组合成端到端 pipeline，覆盖：

- 知识图谱构建（construction）
- 图谱丰富（enrichment）
- 图推理（reasoning）
- 图检索（retrieval）
- 领域专用图谱应用

### 3.2 算子包结构（9 类图谱范式）

DataFlow-KG 的 `dataflow/operators/` 目录按图谱范式分为 9 个算子包，这是其最关键的设计特征：

| 算子包 | 图谱范式 | 典型场景 |
| --- | --- | --- |
| `general_kg` | 通用知识图谱 | 实体/关系抽取、三元组构建 |
| `commonsense_kg` | 常识知识图谱 | 常识推理数据准备 |
| `temporal_kg` | 时序知识图谱 | 带时间维度的图谱推理 |
| `multi_model_kg` | 多模态知识图谱 | 跨模态实体对齐 |
| `hyper_relation_kg` | 超关系知识图谱 | n-ary 关系表达 |
| `graph_rag` | GraphRAG | 图增强检索生成 |
| `graph_reasoning` | 图推理 | 路径推理、链接预测 |
| `domain_kg` | 领域专用知识图谱 | 垂直领域定制 |
| `pdf2text` | PDF→文本 | 图谱构建的前置解析（对接 L1） |

### 3.3 Pipeline 设计

DataFlow-KG 采用 **"代码生成 + 自定义修改 + 脚本执行"** 工作流，并提供两档资源需求的 pipeline 变体：

| Pipeline 目录 | 所需资源 | 适用场景 |
| --- | --- | --- |
| `api_pipelines` | CPU + LLM API | 快速上手、无本地 GPU |
| `gpu_pipelines` | CPU + API + 本地 GPU | 大规模、低延迟推理（vllm） |

初始化后只需配置两处即可运行：
1. **输入数据路径**：`FileStorage(first_entry_file_name="<path>")`
2. **LLM serving 配置**：通过 `DF_API_KEY` 环境变量接入 API，或替换为本地模型后端。

### 3.4 与 GraphRAG 的关系

DataFlow-KG 把 **GraphRAG 作为一种图谱范式**（`graph_rag` 算子包）纳入统一框架，而非独立项目。这与 [DataMind](https://github.com/OpenDCAI/DataMind)（OpenDCAI 的 RAG/GraphRAG/NL2SQL 智能助手）形成上下游互补：
- DataFlow-KG 负责 **GraphRAG 的数据准备**（图谱构建、丰富、检索算子）；
- DataMind 负责 **GraphRAG 的运行时应用**。

> ⚠️ 任务提及的 "QA-GraphRAG (VLDB 2026)" 论文**未在 DataFlow 官方出版物中核实到**。DataFlow 官方出版物中与 RAG 相关的是 *AgenticRAGTracer*（ACL Findings 2026）。本笔记不对未核实论文做内容引述。

### 3.5 与 DataFlow Core 的关系

DataFlow-KG 同样继承 Core 抽象，但**独立性更强**：
- 提供独立 CLI `dfkg`（`dfkg init` / `dfkg -v` / `dfkg env`）；
- 通过 PyPI 分发：`uv pip install dataflow-kg`（可选 `[vllm]`）；
- 目录结构与 Core 同构（core / operators / pipeline / prompts / serving / utils / wrapper），说明它是"复制 Core 骨架 + 替换算子域"的扩展模式。

---

## 4. 表格数据资产（关于 DataFlow-Table）

### 4.1 事实校验：DataFlow-Table 不存在

任务预设的 [DataFlow-Table](https://github.com/OpenDCAI/DataFlow-Table) 仓库**返回 404**，且 OpenDCAI 组织全部 41 个仓库中无此仓库。任务提及的 **ProfiliTable (SIGKDD 2026)** 论文也未在 DataFlow 官方出版物列表中出现（KDD 2026 收录的是 *Let's Verify Math Questions Step by Step*）。

> 因此，下文不杜撰 DataFlow-Table 的功能，而是分析 DataFlow 生态中**实际承担表格/结构化数据资产处理**的组件，作为"表格数据资产工厂"的等价落点。

### 4.2 生态中实际的表格数据处理能力

DataFlow Core 内已具备较完整的表格/结构化数据处理能力，分散在三个方向：

| 能力 | 承载组件 | 说明 |
| --- | --- | --- |
| **Text2SQL** | `operators/text2sql/` + Text2SQL Pipeline | 自然语言→SQL，含 SQL 生成/变异/执行过滤；对应论文 *Text2SQL-Flow*（ICDE 2026） |
| **向量SQL** | [Text2VectorSQL](https://github.com/OpenDCAI/Text2VectorSQL) | 统一向量搜索与 SQL 查询接口 |
| **知识库表格清洗** | `operators/knowledge_cleaning/` + KB清洗Pipeline | 从表格、PDF、Word 中提取知识条目，转为 RAG/QA 可用资产 |
| **Pandas 算子** | `operators/core_text/refine/pandas_operator.py` | 表格数据的程序化精炼 |
| **数据库存储** | `dataflow/utils/storage.py` + Database Management | FileStorage / 数据库存储连接器，支持结构化数据 I/O |

### 4.3 Agentic Workflow 的等价体现

任务提到"取数、处理、分析三类 Agentic Workflow"。DataFlow 生态中对应的是：
- **取数**：Text2SQL 流水线（NL→SQL→执行→结果）+ 数据库连接器；
- **处理**：KB 清洗流水线（表格/PDF→结构化条目）+ pandas_operator 精炼；
- **分析**：评测算子（SQL 分类、执行正确性、难度评估）+ [One-Eval](https://github.com/OpenDCAI/One-Eval) 自动化评测。

此外，[DataFlow-Agent](https://github.com/OpenDCAI/DataFlow-Agent) 与 [DataFlow-WebUI](https://github.com/OpenDCAI/DataFlow-WebUI) 的 "NL2Pipeline" 能力，可动态组装上述算子，构成 Agentic 表格工作流。

> 结论：DataFlow 当前**未把表格数据资产抽离为独立 L2 扩展仓库**，而是作为 Core 的原生算子域存在。若需类似 DataFlow-Table 的独立模块，可参照第 5 节的扩展模式自建。

---

## 5. L2 层扩展模式分析

这一节是本笔记的方法论核心：**如何基于 DataFlow Core 开发新的 L2 数据资产模块**。

### 5.1 Core 的三大抽象（扩展基石）

| 抽象 | 定义位置 | 作用 |
| --- | --- | --- |
| `OperatorABC` | `dataflow/core/operator.py` | 所有算子的抽象基类，唯一需实现 `run()` 方法 |
| `DataFlowStorage` | `dataflow/utils/storage.py` | 存储抽象（FileStorage / LazyFileStorage / BatchedFileStorage / StreamBatchedFileStorage） |
| `LLMServingABC` | `dataflow/core/llm_serving.py` | LLM 服务抽象（API / 本地GPU / VLM / Embedding） |

`OperatorABC` 的核心契约（来自本地源码 `dataflow/core/operator.py:5`）：

```python
class OperatorABC(ABC):
    def __init__(self):
        self.logger = get_logger()
        self.ALLOWED_PROMPTS = tuple([type[DIYPromptABC | PromptABC]])

    @abstractmethod
    def run(self) -> None:
        """Main function to run the operator."""
        pass
```

### 5.2 算子执行模型：Storage Step 机制

每个算子通过 `storage.step()` 获得隔离上下文，形成可追溯的数据血缘：

| Storage Step | 数据来源 | 数据去向 | 用途 |
| --- | --- | --- | --- |
| `step=0` | 初始数据集文件 | — | 加载输入 |
| `step=N` | `cache_step_{N}.jsonl` | `cache_step_{N+1}.jsonl` | 读 N 写 N+1 |
| `step=final` | 最后算子输出 | — | 最终输出 |

收益：自动血缘追踪、崩溃恢复、中间结果可检查。

### 5.3 算子注册与 Pipeline 复用机制

**注册**：扩展仓库默认扫描 `<package>/operator` 路径下所有算子，注册到主仓库 `OPERATOR_REGISTRY`：

```python
from dataflow.utils.registry import OPERATOR_REGISTRY
import df_123  # 导入扩展包即触发注册
print(OPERATOR_REGISTRY._obj_map.keys())  # 扩展算子即出现
```

**Pipeline 复用**：通过 `AutoOP` 包装器在编译期记录算子调用，构建 `OperatorNode` 图，并做 **key 校验**（input_key 必须匹配前序算子的 output_key 或数据集原始 key），实现编译期错误检测。

**LLM 生命周期管理**：Pipeline 编译期检测算子内的 `LLMServingABC` 实例，引用计数管理 `start_serving()` / `cleanup()`，对本地 GPU 场景（模型加载昂贵）尤为重要。

### 5.4 标准化分发层（DataFlow-Ecosystem）

Ecosystem 的官方定义（来自 [扩展文档](https://opendcai.github.io/DataFlow-Doc/en/guide/df_ecosystem/)）：

> **Operator Library + Prompt Library + Pipeline Library = `<DataFlow-Extension>`**
> **`<DataFlow-Extension>` + ... + `<DataFlow-Extension>` = `<DataFlow-Ecosystem>`**

标准建仓流程通过脚手架 CLI：

```shell
dataflow init repo
# 交互式填写：repo_name / package_name / author / description /
#             init_version / license / python_version / 是否含示例算子
```

生成完整仓库模板后 `pip install -e .` 即可与主仓库无缝集成，实现"即插即用"。DataFlow-MM 与 DataFlow-KG 即是此模式产出的两个官方扩展。

### 5.5 两种扩展深度对比

| 扩展模式 | 代表 | 特征 |
| --- | --- | --- |
| **轻量扩展** | DataFlow-MM | 复用 Core 的 CLI 骨架与 registry，加 `dataflowmm init` 入口，算子按模态分包 |
| **深度独立** | DataFlow-KG | 复制 Core 全套目录结构（core/operators/pipeline/prompts/serving/utils/wrapper），提供独立 `dfkg` CLI 与 PyPI 包，近乎"分叉式扩展" |

这说明 Ecosystem 允许从"纯算子插件"到"近乎独立的同构子项目"的连续谱系。

---

## 6. 与其他层的接口

### 6.1 上游接口（接收 L1 解析层输出）

| L2 组件 | 上游 L1 来源 | 接口形式 |
| --- | --- | --- |
| DataFlow-MM | MinerU PDF→Markdown/VQA；Flash-MinerU 加速 | `pdf2vqa` 算子（PDF_Merger / MinerU2LLMInputOperator）消费 MinerU 输出 |
| DataFlow-KG | PDF→文本解析 | 独立 `pdf2text` 算子包，对接 L1 文本解析 |
| 表格类 | MinerU 表格 HTML；数据库 | KB清洗算子消费表格；Database Connector 直连结构化源 |

### 6.2 下游接口（为 L3/L4 提供数据资产）

| 下游组件 | 消费的 L2 资产 |
| --- | --- |
| [One-Eval](https://github.com/OpenDCAI/One-Eval) / [Data-Preparation-Bench](https://github.com/OpenDCAI/Data-Preparation-Bench) | 评测算子产出的质量/难度/类别标签 |
| [DataFlex](https://github.com/OpenDCAI/DataFlex) | 清洗后的训练样本（数据为中心训练） |
| [DataMind](https://github.com/OpenDCAI/DataMind) | RAG/GraphRAG 知识库（含 KG 资产） |
| LLaMA-Factory | SFT/RL 训练数据 |

L2 产出的统一交付物是 `cache_step_final.jsonl`（或数据库表），通过 `output_key` 追加列的方式承载资产字段，下游按 key 读取。

---

## 7. 对 SRS 项目的价值

本节回归本项目（GJB 438C SRS 一致性检测），分析 DataFlow L2 扩展组件的可迁移价值。

### 7.1 DataFlow-KG 用于 SRS 知识图谱构建（高价值）

本项目已有 `knowledge/srs_kb_graph_v2.json`（7720 节点的知识图谱，v2.0，构建于 2026-07-24，数据源含 GJB 438C-2021 标准、既有图谱、MinerU 解析的 SRS 文档）。该图谱节点类型包括 `Standard`、`DocumentType`（SDP/SIP/STrP/STP/OCD/SSS/IRS 等 GJB 文档类型）等。

DataFlow-KG 的 `domain_kg`（领域专用 KG）算子包**天然契合 SRS 领域图谱**，可提供：

1. **图谱构建标准化**：把当前 `tools/srs_kb_graph_builder.py` 的自研构建逻辑，迁移到 DataFlow-KG 的 Operator/Pipeline 抽象，获得 storage step 血缘追踪、崩溃恢复、LLM 生命周期管理；
2. **图谱丰富与补全**：用 `general_kg` / `graph_reasoning` 算子对 7720 节点做链接预测、关系补全，增强 SRS 需求-约束-章节间的隐含关联；
3. **GraphRAG 下游对接**：`graph_rag` 算子包可直接为 SRS 一致性检测的检索增强提供支撑（如基于图谱检索相关约束做语义层检测）；
4. **一致性检测的图推理化**：`graph_reasoning` 算子可把当前 Z3 求解的逻辑层检测，扩展为图谱上的多跳推理，发现跨章节的逻辑冲突。

**落地路径建议**：参照第 5.4 节，用 `dataflow init repo` 脚手架创建 `srs-kg` 扩展包，把 GJB 规则库（`knowledge/gjb_438c_rules*.json`）与现有图谱作为 `domain_kg` 算子的输入，复用 DataFlow-KG 的 `api_pipelines`（CPU + GLM-5 API）快速验证。

### 7.2 DataFlow-Table 能力用于 SRS 表格解析增强（中高价值）

虽然 DataFlow-Table 独立仓库不存在，但 DataFlow Core 的表格处理能力可增强本项目现有的 `tools/srs_table_parser.py`（当前从 MinerU HTML 表格提取 modification/reference/qualification/traceability/interface 等结构化数据）：

1. **Text2SQL 范式迁移**：SRS 的合格性规定表、正/逆向追踪表本质是结构化查询需求。可借鉴 `operators/text2sql/` 的 SQL 生成/执行过滤算子，把"需求 ID→合格性方法"等查询自然语言化，支持一致性检测的动态问答；
2. **KB 清洗算子复用**：`operators/knowledge_cleaning/` 的 `kbc_text_cleaner`、`kbc_chunk_generator`、`qa_extract` 可直接处理 SRS 表格→QA 对，扩充 Gold Standard 数据集（当前仅 3 份 battery/compiler/scheduler）；
3. **pandas_operator 精炼**：对 `data/gjb_438c/extracted_tables/` 的结构化表格做程序化清洗与对齐；
4. **Database Storage 对接**：用 DataFlow 的数据库存储连接器替换当前的 JSONL 文件存储，支持多 SRS 文档的联合表格查询。

### 7.3 DataFlow-MM 用于 SRS 图片-文本匹配（中等价值）

本项目已有 `tools/srs_image_text_matcher.py`（v3，Markdown 引用提取 + VLM 描述兜底）。DataFlow-MM 的 `core_vision` 与 `pdf2vqa` 算子可提供：
- VQA 生成算子标准化图片描述流程；
- 复用 Core 的 VLM serving 抽象（本项目已配 Kimi-K2.6 多模态 API），统一图片-文本匹配的 LLM 调用。

### 7.4 总体迁移建议

| 优先级 | 动作 | 依据 |
| --- | --- | --- |
| P0 | 用 DataFlow-KG `domain_kg` 重构 SRS 知识图谱构建 | 直接命中 7720 节点图谱的丰富/推理/GraphRAG 需求 |
| P1 | 用 KB 清洗算子扩充 Gold Standard 表格资产 | 解决当前 Gold Standard 仅 3 份的瓶颈 |
| P2 | 用 DataFlow-MM VQA 算子标准化图片-文本匹配 | 提升现有 matcher 的可维护性 |
| P3 | 评估自建 `srs-table` 扩展包（参照 Ecosystem 模式） | 若表格需求持续增长，按第 5 节模式独立分发 |

---

## 8. 参考资源

### 仓库
- DataFlow Core: https://github.com/OpenDCAI/DataFlow
- DataFlow-MM: https://github.com/OpenDCAI/DataFlow-MM ｜ 文档 https://OpenDCAI.github.io/DataFlow-MM-Doc/
- DataFlow-KG: https://github.com/OpenDCAI/DataFlow-KG ｜ 文档 https://zhp-li197.github.io/DataFlow-KG-Doc/zh/
- DataFlow-Ecosystem 指南: https://opendcai.github.io/DataFlow-Doc/en/guide/df_ecosystem/
- DeepWiki 算子框架: https://deepwiki.com/OpenDCAI/DataFlow/3.1-operators-framework

### 经核实的 DataFlow 官方出版物
| 论文 | 组件 | 会议 | 年份 |
| --- | --- | --- | --- |
| AgenticRAGTracer | Agentic RAG 数据合成 | ACL Findings | 2026 |
| Text2SQL-Flow | Text2SQL 数据增强 | ICDE | 2026 |
| Let's Verify Math Questions Step by Step | 数学问题质量评估 | KDD | 2026 |
| MM-Verify | 多模态推理验证 | ACL | 2025 |
| Efficient Pretraining Data Selection | 多角色协同数据选择 | ACL | 2025 |
| DataFlow (arXiv:2512.16676) | 核心框架 | preprint | 2025 |

> 注：任务提及的 *ProfiliTable (SIGKDD 2026)* 与 *QA-GraphRAG (VLDB 2026)* **未在官方出版物中核实**，本笔记不做内容引述，待后续确认。

### 本项目相关资产
- SRS 知识图谱 v2: `knowledge/srs_kb_graph_v2.json`（7720 节点）
- GJB 规则库: `knowledge/gjb_438c_rules*.json`
- 表格解析器: `tools/srs_table_parser.py`
- 图片-文本匹配器: `tools/srs_image_text_matcher.py`
- 本地 DataFlow 源码: `dataflow_repos/DataFlow/`
