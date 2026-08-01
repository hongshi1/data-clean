# DataFlow生态 L3智能体编排层 + L4训练评估层 深度知识笔记

> 北大Data-Centric AI Group开源工具链 | 源码级分析
> 调研日期: 2026-07-30

---

## 目录

1. [L3+L4 总览](#1-l3l4-总览)
2. [AgentFlow — L3 智能体数据合成](#2-agentflow--l3-智能体数据合成)
3. [DataFlow-Skills — L3 技能库](#3-dataflow-skills--l3-技能库)
4. [DataFlow-Agent — L3 核心系统Agent](#4-dataflow-agent--l3-核心系统agent)
5. [DataFlex — L4 训练数据管理](#5-dataflex--l4-训练数据管理)
6. [One-Eval — L4 评估框架](#6-one-eval--l4-评估框架)
7. [Dataflow-LoopAI — L4 闭环优化](#7-dataflow-loopai--l4-闭环优化)
8. [L3+L4 整体架构与数据流](#8-l3l4-整体架构与数据流)
9. [对SRS项目的价值](#9-对srs项目的价值)

---

## 1. L3+L4 总览

DataFlow生态按抽象层级划分为 L1（数据算子）→ L2（数据流水线）→ **L3（智能体编排）** → **L4（训练评估闭环）**。本笔记聚焦后两层：

| 层级 | 组件 | 核心职责 |
|------|------|----------|
| **L3** | AgentFlow | 跨异构环境的统一Agent数据合成（RAG/MM-Doc/Web/GUI/SQL/Code/Embodied） |
| **L3** | DataFlow-Skills | 将数据算子/流程生成/质量评测沉淀为可组合的Claude Code技能 |
| **L3** | DataFlow-Agent | 自然语言→自动选算子→自动编排Pipeline的智能助手 |
| **L4** | DataFlex | 训练循环内动态数据选择/配比/重加权（基于LLaMA-Factory） |
| **L4** | One-Eval | "一句话从需求到评测报告"的自动化评估框架（NL2Eval） |
| **L4** | Dataflow-LoopAI | 评测→分析→数据获取→训练反馈的全自动闭环优化（NL2Optimize） |

**六组件功能定位对比表：**

| 组件 | 层级 | 输入 | 输出 | 核心机制 | 技术栈 |
|------|------|------|------|----------|--------|
| AgentFlow | L3 | Seed种子 + Sandbox环境 | 合成QA对 + Agent轨迹 | 三阶段: 轨迹采样→轨迹选择→QA合成 | 自研Sandbox(HTTP服务) + OpenAI API |
| DataFlow-Skills | L3 | 目标描述 + 样例JSONL | 可执行Pipeline代码 | 6核心原语 + 算子决策表 + 字段依赖规则 | Claude Code Skills |
| DataFlow-Agent | L3 | 自然语言任务描述 | PipelineABC子类代码 | 5阶段: 分析→选算子→编排→生成→监控 | OPERATOR_REGISTRY(140+) + LangGraph |
| DataFlex | L4 | 训练数据集 + YAML配置 | 微调后模型 | 动态样本选择 + 域配比优化 + 样本重加权 | LLaMA-Factory + DeepSpeed ZeRO-3 |
| One-Eval | L4 | 自然语言评测目标 + 模型 | 多维评测报告 | NL2Eval + Graph/Node/State执行 + Bench Gallery | DataFlow算子 + LangGraph |
| Dataflow-LoopAI | L4 | 自然语言优化目标 + 模型 | 优化后模型 | NL2Optimize + 6 Agent子图协作闭环 | LangGraph + vLLM + LLaMA-Factory/verl |

---

## 2. AgentFlow — L3 智能体数据合成

> **定位**: 首个统一的Agent数据合成框架，为自定义任务提供all-in-one环境。
> **源码**: `dataflow_repos/AgentFlow/`
> **论文**: DocDancer / RAGShaper / Agent Consolidation / BrowseComp-V3

### 2.1 目录结构

```
AgentFlow/
├── synthesis/              # QA合成模块（三阶段pipeline核心）
│   ├── __init__.py         # 导出 SynthesisConfig/SandboxWorker/TrajectorySampler/TrajectorySelector/QASynthesizer
│   ├── api.py              # 轻量API: load_config() / load_seeds() / synthesize()
│   ├── pipeline.py         # SynthesisPipeline 主流程
│   └── core/
│       ├── config.py       # SynthesisConfig 配置类
│       ├── models.py       # TrajectoryNode / Trajectory / SynthesizedQA 数据模型
│       ├── sampler.py      # ★ TrajectorySampler 轨迹采样器
│       ├── selector.py     # ★ TrajectorySelector 轨迹选择器
│       ├── synthesizer.py  # ★ QASynthesizer QA合成器
│       ├── worker.py       # SandboxWorker sandbox交互层
│       └── utils.py        # LLM客户端 / XML解析 / 异步聊天
├── rollout/                # 推理/评测模块（在benchmark上运行训练好的模型）
│   ├── api.py              # rollout() / quick_rollout()
│   ├── pipeline.py         # RolloutPipeline
│   └── core/
│       ├── config.py       # RolloutConfig
│       ├── runner.py       # ★ AgentRunner 多轮工具调用执行器
│       ├── evaluator.py    # Evaluator (exact_match/f1/llm_judgement/DocBench_LasJ等)
│       └── models.py       # BenchmarkItem / TaskResult / Trajectory / RolloutSummary
├── sandbox/                # ★ All-in-One Sandbox环境
│   ├── sandbox.py          # Sandbox 门面类（用户主接口）
│   ├── client.py           # HTTPServiceClient
│   ├── protocol.py         # HTTP协议定义（Execute/Session/Init消息）
│   ├── server/
│   │   ├── app.py          # FastAPI服务
│   │   ├── routes.py       # 路由
│   │   └── backends/
│   │       ├── base.py     # Backend基类
│   │       └── resources/  # 环境后端
│   │           ├── rag.py     # RAG检索(E5+Faiss)
│   │           ├── vm.py      # VM桌面自动化(GUI)
│   │           └── mcp/       # MCP工具协议
│   └── tool_schemas/       # 工具Schema定义
│       ├── rag_tools.py    # RAG搜索工具
│       ├── web_tools.py    # Web搜索/访问工具
│       ├── doc_tools.py    # 文档处理工具
│       ├── ds_tools.py     # 数据分析工具
│       ├── sql_tools.py    # SQL工具
│       └── vm_tools.py     # VM/GUI工具
├── configs/                # 四类配置
│   ├── sandbox-server/     # 7种环境: web/rag/doc/ds/GUI/text2sql/mcp
│   ├── synthesis/          # 8种合成配置
│   ├── trajectory/         # 轨迹rollout配置
│   └── infer/              # 推理配置
├── seeds/                  # 种子数据 (doc/ds/GUI/rag/web)
├── benchmark/              # 评测基准 (doc_benchmark/rag_benchmark/web_benchmark)
├── projects/               # 项目 (BrowseComp-V3 / DocDancer)
└── examples/               # 5个示例 (DocAgent/DSAgent/RAGAgent/Text2SQL/WebAgent)
```

### 2.2 三阶段合成流程（代码级）

AgentFlow通过 **Trajectory Sampling → Trajectory Selection → QA Synthesis** 三阶段pipeline合成高质量Agent训练数据。主入口在 `synthesis/pipeline.py:SynthesisPipeline.run_async()`：

```python
# 源码: synthesis/pipeline.py:66-203 (精简展示核心三阶段)
async def run_async(self, seeds):
    worker = SandboxWorker(self.config, worker_id="main_worker")
    await worker.start(create_sessions=False)

    # 创建三阶段组件
    sampler = TrajectorySampler(worker, self.config)       # 阶段1: 采样器
    selector = TrajectorySelector(self.config)             # 阶段2: 选择器
    synthesizer = QASynthesizer(self.config)               # 阶段3: QA合成器

    for seed_idx, seed in enumerate(seeds, 1):
        seed_content = seed.get("content", "")
        source_id = generate_source_id(seed_content, seed_idx)

        # ===== 阶段1: 轨迹采样 =====
        trajectory_tree = await sampler.sample_trajectory_tree(seed_content, seed_kwargs)

        # ===== 阶段2: 轨迹选择 =====
        selected_trajectories = selector.select_trajectories(
            nodes=trajectory_tree,
            root_id=sampler.root_id,
            seed_data=seed_content,
            source_id=source_id,
            max_selected_traj=self.config.max_selected_traj
        )

        # ===== 阶段3: QA合成 =====
        for qa_idx, trajectory in enumerate(selected_trajectories):
            qa = synthesizer.synthesize_qa(trajectory, qa_idx)
            if qa:
                qa_pairs.append(qa.to_dict())

        self._save_qa_pairs(qa_pairs)        # → synthesized_qa.jsonl
        self._save_trajectories(trajectories_data)  # → trajectories.jsonl
```

#### 阶段1: Trajectory Sampling（轨迹采样）

> 源码: `synthesis/core/sampler.py` — `TrajectorySampler`类

LLM驱动的Agent从seed出发，在sandbox中迭代探索，构建**分支轨迹树**：

```python
# 源码: synthesis/core/sampler.py:45-94 — 轨迹树采样入口
async def sample_trajectory_tree(self, seed_data, seed_kwargs=None):
    # 重置树 + 加载工具schema
    self.nodes = {}
    self.available_tools = get_tool_schemas(self.config.available_tools)

    # 创建根节点
    root_id = self._generate_node_id()
    root_node = TrajectoryNode(
        node_id=root_id,
        observation=f"Starting point: {seed_data}",
        intent="Initialize exploration",
        depth=0
    )
    self.nodes[root_id] = root_node
    self.root_id = root_id

    # 异步探索（广度优先 + 并发扩展）
    await self._explore_node(root_node, seed_data)
    return self.nodes
```

```python
# 源码: synthesis/core/sampler.py:96-163 — 并发探索 + Action去重
async def _explore_node(self, node, seed_data):
    if node.depth >= self.config.max_depth:    # 深度上限
        return
    # 深度阈值内用branching_factor分支，超过则单链
    num_children = self.config.branching_factor if node.depth < self.config.depth_threshold else 1
    child_tasks = [self._create_and_explore_child(node, seed_data) for _ in range(num_children)]
    await asyncio.gather(*child_tasks, return_exceptions=True)  # 并发执行

async def _create_and_explore_child(self, parent_node, seed_data):
    # LLM生成下一步动作
    intent, action = await self._generate_next_action(parent_node, seed_data)
    # 执行工具调用
    observation = await self._execute_action(action)
    # 创建子节点并递归探索
    child_node = TrajectoryNode(observation=observation, intent=intent, action=action, ...)
    await self._explore_node(child_node, seed_data)  # 递归
```

**关键机制 — Action去重**（`sampler.py:320-355`）：每个seed维护已执行动作签名集合，通过 `tool_name + canonicalized_parameters` 的MD5哈希去重，避免重复探索：

```python
def _action_signature(self, action, intent=None):
    tool_name = str(action.get("tool_name", ""))
    parameters = action.get("parameters", {})
    safe_params = _shrink_obj(parameters)  # 长字符串用md5缩略
    params_str = json.dumps(safe_params, sort_keys=True, separators=(",", ":"))
    return f"{tool_name}({params_str})"
```

#### 阶段2: Trajectory Selection（轨迹选择）

> 源码: `synthesis/core/selector.py` — `TrajectorySelector`类

对所有root-to-leaf路径按**深度(40分) + 信息丰富度(30分) + 工具多样性(30分)** 打分，并用Jaccard相似度去冗余：

```python
# 源码: synthesis/core/selector.py:148-171 — 三维评分
def _score_path(self, path, avg_obs_length=None, min_length=0, length_range=1):
    # 1. 深度分 (满分40): 路径长度/5.0，上限1.0
    depth_score = min(len(path) / 5.0, 1.0) * 40

    # 2. 信息分 (满分30): 观测文本长度的归一化值
    normalized_length = (avg_obs_length - min_length) / length_range
    info_score = normalized_length * 30

    # 3. 多样性分 (满分30): 路径中不同工具数/总工具数
    tool_names = {node.action.get("tool_name", "") for node in path if node.action}
    diversity_score = len(tool_names) / max(total_tools, 1) * 30

    return depth_score + info_score + diversity_score
```

```python
# 源码: synthesis/core/selector.py:109-146 — Jaccard去冗余
for rank, (score, idx, path) in enumerate(scored_paths):
    if len(selected_trajectories) >= max_selected:
        break
    current_path_set = {node.node_id for node in path}
    for selected_set in selected_path_sets:
        intersection = len(current_path_set & selected_set)
        union = len(current_path_set | selected_set)
        jaccard_similarity = intersection / union if union > 0 else 0.0
        if jaccard_similarity > similarity_threshold:  # 默认0.7
            is_too_similar = True
            break
    if not is_too_similar:
        selected_trajectories.append(Trajectory(...))
```

#### 阶段3: QA Synthesis（QA合成）

> 源码: `synthesis/core/synthesizer.py` — `QASynthesizer`类

对每条选中轨迹，LLM生成**多跳factoid QA对**，内置多重质量检查：

```python
# 源码: synthesis/core/synthesizer.py:27-63 — QA合成主流程
def synthesize_qa(self, trajectory, qa_index=0):
    for attempt in range(1, max_attempts + 1):  # 最多3次重试
        prompt = self._build_prompt(trajectory, traj_description, last_failure_reason)
        response = chat_completion(self.client, model=..., response_format={"type": "json_object"})
        result = json.loads(extract_json_object(response.choices[0].message.content))

        qa_obj, failure_reason = self._build_qa_from_result(result, trajectory, qa_index, attempt)
        if qa_obj:
            return qa_obj
        last_failure_reason = failure_reason  # 反馈失败原因，下次重试时注入prompt
```

**质量检查规则**（`synthesizer.py:65-129`）：
- **答案泄露检查**: 答案文本不得出现在问题中（`_answer_leaks_into_question`）
- **问题冗长检查**: ≤85词且≤500字符（`_question_too_verbose`）
- **推理步数检查**: `reasoning_steps` ≥ 3步（`_build_qa_from_result`）
- **格式要求**: 问题≤2句，答案≤1句，须为具体事实（名称/日期/位置/数量/是否）

QA输出结构：
```python
# 源码: synthesis/core/models.py:45-65
@dataclass
class SynthesizedQA:
    question: str
    answer: str
    trajectory_id: str
    reasoning_steps: List[Dict[str, str]]  # [{hop, fact, evidence, output}, ...]
    source_id: str = ""
    qa_id: str = ""
    metadata: Dict[str, Any]  # seed_data, trajectory_depth, synthesis_date
```

### 2.3 Sandbox环境架构

> 源码: `sandbox/sandbox.py` / `sandbox/protocol.py` / `sandbox/server/`

Sandbox是AgentFlow的核心——一个**统一、可扩展的HTTP服务环境**，通过模块化后端设计支持7种异构环境：

| 环境类型 | 后端类 | 工具Schema | 应用场景 |
|----------|--------|-----------|----------|
| RAG | `RAGBackend` (E5+Faiss) | `rag_tools.py` | 文档检索问答 |
| Web | BrowserBackend | `web_tools.py` | 深度研究/网页浏览 |
| MM-Doc | (Doc工具) | `doc_tools.py` | 多模态文档理解 |
| Data Analysis | (DS工具) | `ds_tools.py` | 数据分析/表格推理 |
| Text2SQL | (SQL工具) | `sql_tools.py` | 自然语言转SQL |
| GUI/VM | `VMBackend` | `vm_tools.py` | 桌面自动化 |
| Code | `CodeExecutorBackend` | — | 代码执行沙箱 |
| MCP | MCP后端 | `mcp/` | Model Context Protocol扩展 |

**HTTP协议设计**（`sandbox/protocol.py`）：
```python
class MessageType(str, Enum):
    EXECUTE = "execute"              # 工具调用 (支持 "resource_type:action" 前缀)
    EXECUTE_BATCH = "execute:batch"  # 批量执行
    SESSION_CREATE = "session:create"    # 创建会话(长生命周期资源)
    SESSION_DESTROY = "session:destroy"
    INIT_RESOURCE = "init:resource"      # 资源初始化
    INIT_FROM_CONFIG = "init:from_config"
```

**Session机制**：支持长生命周期资源上下文（如RAG索引、VM桌面状态），TTL默认300秒，活跃时自动续期。

### 2.4 配置系统

四类配置对应完整工作流：

| 配置类型 | 路径 | 用途 | 示例 |
|----------|------|------|------|
| sandbox-server | `configs/sandbox-server/` | 启动Sandbox服务 | `rag_config.json` (E5模型+Faiss索引+语料库) |
| synthesis | `configs/synthesis/` | 合成QA数据 | `rag_config.json` (max_depth=10, branching_factor=2) |
| trajectory | `configs/trajectory/` | 轨迹rollout | `web_trajectory.json` |
| infer | `configs/infer/` | 模型推理评测 | `web_infer.json` |

**Synthesis配置关键字段**（以 `configs/synthesis/rag_config.json` 为例）：
```json
{
  "max_depth": 10,              // 轨迹树最大深度
  "branching_factor": 2,        // 分支因子
  "depth_threshold": 2,         // 深度阈值(超过后单链)
  "min_depth": 3,               // 选择时最小深度要求
  "max_selected_traj": 2,       // 最多选择轨迹数
  "path_similarity_threshold": 0.7,  // Jaccard去冗余阈值
  "resource_types": ["rag"],    // Sandbox资源类型
  "available_tools": ["rag-search"],
  "sampling_tips": [...],       // 探索策略提示
  "synthesis_tips": [...]       // QA合成策略提示
}
```

### 2.5 模型家族与Benchmark

**AgentFlow Agent Family**（均基于Qwen3-30B-A3B-Think）：

| Agent | 领域 | 关键成果 |
|-------|------|----------|
| DocDancer | MM-Doc | MMLongBench-Doc 54.4% acc (接近人类65.8%) |
| RAGShaper | RAG | Bamboogle EM 60.0% (超Search-R1的30.4%) |
| DeepResearch Agent | Web | GAIA 64.08% (Data Mixing策略) |
| Agent-DataMix | 通用 | 数据级混合训练 |
| Agent-RegMeanpp | 通用 | 参数级RegMean++训练 |

**模型整合策略**：
- **Data-level (Data Mixing)**: 多域轨迹数据混合训练
- **Parameter-level (RegMean++)**: 参数级模型合并，解决跨域灾难性遗忘

**Benchmark — BrowseComp-V3**：
- 300道手工制作的多模态问题，评估Web浏览Agent
- 深度多跳、跨模态推理，GPT-5.2仅36%准确率
- 含OmniSeeker通用多模态浏览Agent框架 + LLM-judge评测pipeline

### 2.6 Rollout推理评测

> 源码: `rollout/pipeline.py` / `rollout/core/runner.py`

训练完成后，用 `rollout` 模块在benchmark上评测：

```python
# 源码: rollout/api.py:54-110 — 一键rollout
def rollout(*, config_path, data_path=None, evaluate=True, metric=None):
    config = load_config(config_path)
    pipeline = RolloutPipeline(config=config)
    summary = pipeline.run()
    return summary.to_dict()
```

`AgentRunner`（`rollout/core/runner.py`）支持OpenAI原生function calling的多轮工具调用，评测指标包括 `exact_match / f1_score / llm_judgement / DocBench_LasJ / MMLongBench-Doc_F1` 等。

---

## 3. DataFlow-Skills — L3 技能库

> **定位**: 将DataFlow的数据算子、流程生成、质量评测沉淀为可组合的Claude Code技能。
> **源码**: `dataflow_repos/DataFlow-Skills/`
> **上游对齐**: OpenDCAI/DataFlow `main` (v1.0.10)

### 3.1 目录结构

```
DataFlow-Skills/
├── install.sh                          # 一键安装到 ~/.claude/skills/
├── docs/
│   └── install-claude-code.md          # Claude Code CLI安装指南
├── generating-dataflow-pipeline/       # ★ 技能1: Pipeline规划器
│   ├── SKILL.md                        # 完整技能定义(367行规则)
│   └── examples/                       # 4个完整工作流示例
├── dataflow-dev/                       # ★ 技能2: 开发助手
│   ├── SKILL.md                        # 路由式工作流(271行)
│   ├── context/
│   │   ├── knowledge_base.md           # 架构+API参考
│   │   └── dev_notes.md               # 开发规范+最佳实践
│   ├── diagnostics/
│   │   └── known_issues.md            # 已知问题诊断表(#001-#008)
│   └── templates/
│       └── operator_template.py       # 算子骨架模板
└── core_text/                          # ★ 技能3: 算子API参考文档
    ├── generate/                       # 8个生成算子
    ├── filter/                         # 3个过滤算子
    ├── refine/                         # 2个精炼算子
    └── eval/                           # 5个评测算子
```

### 3.2 三个技能详解

#### 技能1: `generating-dataflow-pipeline` — Pipeline规划器

**触发**: `/generating-dataflow-pipeline`
**输入**: Target(目标描述) + Sample file(JSONL样例) + Expected outputs(可选)
**输出**: 两阶段——先输出算子决策JSON，再输出完整可执行Pipeline代码

**6个核心原语**（高覆盖率的优选算子）：

| 原语 | 类型 | 功能 |
|------|------|------|
| `PromptedGenerator` | 生成 | 单字段LLM生成 |
| `FormatStrPromptedGenerator` | 生成 | 多字段模板生成 |
| `Text2MultiHopQAGenerator` | 生成 | 多跳QA对构造 |
| `PromptedFilter` | 过滤 | LLM语义质量过滤 |
| `GeneralFilter` | 过滤 | 规则确定性过滤 |
| KBC三件套 | 清洗 | `FileOrURLToMarkdownConverterFlash` → `KBCChunkGenerator` → `KBCTextCleaner` |

**算子选择优先级规则**（强制）——专用算子优先于通用算子：

```
| 任务场景                        | 必须使用的算子                    | 禁止使用              |
|--------------------------------|----------------------------------|----------------------|
| 从文本生成QA对                  | Text2MultiHopQAGenerator         | PromptedGenerator+QA |
| 文件路径/URL转文本              | KBC三件套                        | PromptedGenerator    |
| 多字段评分                      | FormatStrPromptedGenerator+GeneralFilter | PromptedFilter |
| 按规则过滤已有字段              | GeneralFilter                    | PromptedFilter       |
```

**字段依赖规则**（强制）：步骤N需要的字段X必须存在于原始数据中，或由步骤M(M<N)产出。

#### 技能2: `dataflow-dev` — 开发助手

**触发**: `/dataflow-dev`（需在DataFlow仓库内运行）
**激活步骤**: 加载知识库 → 加载开发规范 → 加载已知问题 → 探测git状态 → 报告上下文

**6条意图路由**：

| 用户意图 | 执行流程 |
|----------|----------|
| 新建算子 | 防重复检查 → 确认规格 → 生成代码(11项硬性规范checklist) → 注册提醒 |
| 新建Pipeline | 确认规格 → 标准storage.step()模式生成 |
| 新建Prompt | PromptABC/DIYPromptABC创建 + @prompt_restrict放置 |
| 报错诊断 | 匹配known_issues.md (#001-#008) |
| 代码审查 | 14项checklist(注册/run签名/get_desc等) |
| 更新知识库 | 对比本地文件与knowledge_base.md，输出更新步骤 |

#### 技能3: `core_text` — 算子API参考

**不直接调用**——被其他技能查阅的文档库。每个算子目录含：
- `SKILL.md` — 英文完整参考(构造器签名/run签名/执行逻辑/强制规则)
- `SKILL_zh.md` — 中文翻译
- `examples/good.md` — 最佳实践
- `examples/bad.md` — 常见错误

**覆盖18个算子**：
- 生成(8): PromptedGenerator / FormatStrPromptedGenerator / Text2MultiHopQAGenerator / BenchAnswerGenerator / ChunkedPromptedGenerator / EmbeddingGenerator / RandomDomainKnowledgeRowGenerator / RetrievalGenerator
- 过滤(3): GeneralFilter / KCenterGreedyFilter / PromptedFilter
- 精炼(2): PandasOperator / PromptedRefiner
- 评测(5): BenchDatasetEvaluator / BenchDatasetEvaluatorQuestion / PromptedEvaluator / Text2QASampleEvaluator / UnifiedBenchDatasetEvaluator

### 3.3 技能与DataFlow Core的关系

```
DataFlow-Skills (Claude Code技能层)
    │
    ├── 查阅 → core_text/ (18算子的API参考文档)
    │
    ├── 生成 → 标准Pipeline代码
    │         ├── from dataflow.utils.storage import FileStorage
    │         ├── from dataflow.serving import APILLMServing_request
    │         └── from dataflow.operators.core_text import PromptedGenerator, ...
    │
    └── 对齐 → DataFlow Core (v1.0.10)
              ├── OPERATOR_REGISTRY (140+算子)
              ├── PROMPT_REGISTRY (200+提示)
              ├── PipelineABC基类
              └── storage.step()缓存机制
```

技能是**知识层**，Core是**执行层**。技能生成的代码直接调用Core的算子注册表和Pipeline框架，运行时行为与手写Pipeline完全一致。

---

## 4. DataFlow-Agent — L3 核心系统Agent

> **定位**: 自然语言→自动选算子→自动编排Pipeline的智能助手。
> **源码**: `dataflow_repos/DataFlow/dataflow/example/DataflowAgent/`（测试数据）+ DeepWiki文档
> **DeepWiki**: https://deepwiki.com/OpenDCAI/DataFlow/4-dataflow-agent

### 4.1 五阶段工作流

DataFlow-Agent是标准DataFlow Pipeline系统之上的**元层自动化**：

```
用户自然语言描述
    ↓
1. Analyze    — 分析输入数据特征和期望输出格式
    ↓
2. Select     — 从OPERATOR_REGISTRY(140+)中选择算子
    ↓
3. Orchestrate — 编排算子为有序Pipeline，处理数据流依赖
    ↓
4. Generate   — 生成可执行的PipelineABC子类代码
    ↓
5. Monitor    — 监控执行，适配错误
```

### 4.2 算子选择策略

Agent查询 `OPERATOR_REGISTRY` 发现可用算子，使用4种策略选择：

1. **关键词匹配**: 解析任务描述中的领域关键词（"SQL"、"reasoning"、"conversation"）
2. **能力匹配**: 将所需变换匹配到算子能力
3. **数据类型兼容**: 确保算子能处理输入数据schema
4. **依赖解析**: 选择输出满足下游输入的算子

### 4.3 自动生成的Pipeline代码结构

```python
# 由DataFlow-Agent自动生成
from dataflow.core import PipelineABC
from dataflow.Operator import SelectedOperator1, SelectedOperator2
from dataflow.Prompt import SelectedPrompt1

class AgentGeneratedPipeline(PipelineABC):
    def __init__(self, ..., llm_serving=None, **kwargs):
        super().__init__(**kwargs)
        self.op1 = SelectedOperator1(input_keys=["key1"], output_keys=["key2"], llm_serving=llm_serving)
        self.op2 = SelectedOperator2(input_keys=["key2"], output_keys=["key3"])

    def forward(self, storage):
        self.op1.run(storage)
        storage.step()          # 缓存中间结果
        self.op2.run(storage)
        storage.step()
        return storage
```

Agent确保：正确的import路径、input_keys/output_keys连接、storage.step()调用、有效的PipelineABC继承结构。

### 4.4 与Agentic RAG算子的关系

DataFlow Core中已有Agentic RAG专用算子（`dataflow/operators/agentic_rag/`），这些是AgentFlow理念在Core层的体现：

| 算子 | 路径 | 功能 |
|------|------|------|
| `AgenticRAGAtomicTaskGenerator` | `agentic_rag/generate/` | 原子任务生成 |
| `AgenticRAGDepthQAGenerator` | `agentic_rag/generate/` | 深度问题生成（多轮迭代深化） |
| `AgenticRAGWidthQAGenerator` | `agentic_rag/generate/` | 广度问题生成 |
| `AgenticRAGQAF1SampleEvaluator` | `agentic_rag/eval/` | QA F1样本评测 |

这些算子使用 `@prompt_restrict` 绑定专用Prompt模板，通过DataFlow-Agent可自动编排为Agentic RAG Pipeline。

---

## 5. DataFlex — L4 训练数据管理

> **定位**: Data-centric LLM训练框架，在LLaMA-Factory训练循环内动态调度数据。
> **GitHub**: https://github.com/OpenDCAI/DataFlex (1.8k stars)
> **论文**: arXiv:2603.26164 (HF Daily Papers #1)

### 5.1 三大核心能力

| 能力 | 定义 | 算法 |
|------|------|------|
| **Data Selection** | 训练中动态选择样本（如聚焦"难"样本） | LESS(梯度) / NICE(梯度) / Loss / Delta Loss / NEAR(分布) / TSDS(分布) / Static / Random |
| **Data Mixture** | 训练中动态调整不同域数据配比 | DOREMI(离线) / ODM(在线) |
| **Data Reweighting** | 反向传播时动态调整样本权重 | Loss Reweighting |

### 5.2 架构设计

```
DataFlex (基于LLaMA-Factory扩展)
├── src/dataflex/          # 核心包
├── data/                  # 示例数据集
├── examples/              # YAML配置示例
│   └── train_lora/selectors/less.yaml
├── skills/                # 使用文档
│   ├── how_to_use.md
│   └── how_to_add_algorithm.md
└── pip install dataflex   # PyPI安装
```

**关键特性**：
- **完全兼容LLaMA-Factory**——drop-in替换
- **支持DeepSpeed ZeRO-3**——可训练/分析更大规模模型
- **注册系统**——通过统一基类接口注册Selector/Mixer/Weighter

### 5.3 使用方式

```bash
# 安装
pip install dataflex

# 训练（命令与LLaMA-Factory一致，YAML需含DataFlex特有参数）
dataflex-cli train examples/train_lora/selectors/less.yaml
```

### 5.4 实验结果

- **Selector/Reweightor**: 在MMLU子集上，LESS/NICE/Loss等选择算法均超过Random基线
- **Mixture**: DoReMi和ODM在SlimPajama-6B/30B上均超过默认配比，MMLU准确率提升+0.5~0.7%，PPL降低

### 5.5 与DataFlow的协作

```
DataFlow (L1/L2)                    DataFlex (L4)
原始文件 → 算子Pipeline → JSON训练数据 → 动态选择/配比/重加权 → 微调模型
                                    ↑
                        标准数据格式连接(无代码依赖)
```

DataFlex接受任何来源的训练数据——DataFlow产出、人工标注、HuggingFace数据集或自定义脚本。

---

## 6. One-Eval — L4 评估框架

> **定位**: "一句话从用户需求到模型评测报告"的自动化评估框架。
> **GitHub**: https://github.com/OpenDCAI/One-Eval (159 stars)
> **论文**: arXiv:2603.09821
> **核心技术**: NL2Eval

### 6.1 NL2Eval机制

用户只需输入自然语言目标，系统自动完成全链路评测：

```
"评估模型在数学推理任务上的表现"
        ↓ NL2Eval
1. 意图解析 → 自动规划执行路径
2. Benchmark推荐 → MATH / GSM8K / AIME ...
3. 数据准备 → 自动下载
4. 推理执行 → 调用模型
5. 指标匹配 → 自动选择评分标准
6. 多维报告 → 生成评测报告
```

### 6.2 架构设计

```
One-Eval/
├── one_eval/             # 核心包
│   └── server/app.py     # FastAPI后端
├── one-eval-web/         # Vite + React前端
├── one-eval-skill/       # ★ Claude Code便携技能
├── one_eval/             # 核心逻辑
├── docs/                 # 文档
├── HOW_TO_REGISTER_METRIC.md  # 自定义指标注册指南
└── tests/
```

**四大特性**：
- **NL2Eval**: 自然语言→评测工作流自动编排
- **端到端自动化**: 从benchmark推荐到报告生成全自动
- **Human-in-the-Loop**: 关键节点支持中断和人工干预
- **可扩展架构**: 基于DataFlow算子系统 + LangGraph状态管理

### 6.3 Bench Gallery

内置丰富的Benchmark元信息库，统一管理任务类型、数据格式、Prompt模板：

| 能力维度 | Benchmark |
|----------|-----------|
| 推理 | MATH, GSM8K, BBH, AIME |
| 通用知识 | MMLU, CEval, CMMLU |
| 指令遵循 | IFEval |

### 6.4 两种使用方式

**方式1: Claude Code技能**（零配置，推荐）：
```
Use the one-eval-skill in https://github.com/OpenDCAI/One-Eval to get us started on evaluating my model.
```

**方式2: Web UI**：
```bash
# 后端
uvicorn one_eval.server.app:app --host 0.0.0.0 --port 8000
# 前端
cd one-eval-web && npm install && npm run dev  # → localhost:5173
```

### 6.5 评测Pipeline执行

One-Eval将评测重构为**图执行过程（Graph / Node / State）**：
- **Graph**: 评测工作流的有向图
- **Node**: 图中节点（benchmark选择、推理、评分等）
- **State**: LangGraph管理的可中断状态

与DataFlow Eval的关系：One-Eval建立在DataFlow的评测算子（如 `UnifiedBenchDatasetEvaluator`、`PromptedEvaluator`）之上，通过LangGraph编排为自动化工作流。

---

## 7. Dataflow-LoopAI — L4 闭环优化

> **定位**: 评测→问题分析→数据获取→训练反馈的全自动闭环优化框架。
> **GitHub**: https://github.com/OpenDCAI/Dataflow-LoopAI (17 stars)
> **核心技术**: NL2Optimize

### 7.1 核心理念

> *"Everything that can be automated is handled by Agents."*

LoopAI将LLM优化pipeline重构为**图执行框架**，从自然语言优化目标到模型改进全自动：

```
用户 ⇄ StarterAgent(Supervisor) ⇄ Sub-Agent
            │
            ├── 普通问题 → 直接响应
            └── 复杂任务 → Graph执行
                          (评测 → 数据收集 → 训练)
```

### 7.2 六大核心Agent

每个Agent实现为**独立可组合的子图**：

| Agent | 职责 | 关键能力 |
|-------|------|----------|
| **StarterAgent** (Supervisor) | 用户交互 + 意图解析 + 编排下游Agent | 动态工作流管理 |
| **JudgerAgent** | 自动生成评测用例 + 集成外部评测系统 | LLM-based用例生成，支持vLLM本地评测 |
| **AnalyzerAgent** | 评测结果统计分析 + 失败模式识别 | 生成可解释诊断报告 |
| **ObtainerAgent** + WebCrawlerAgent | 数据获取策略 + 数据集/知识源检索 | Web搜索(Tavily) + Kaggle/HF下载 + RAG |
| **TrainerAgent** | 增量训练 + 持续学习防遗忘 | 支持LLaMA-Factory和verl |
| **ConfigerAgent** | 系统配置 + 动态参数更新 | 工作流恢复 |

### 7.3 闭环流程

```
                    ┌──────────────────────────┐
                    │     StarterAgent         │
                    │   (NL2Optimize入口)       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │     JudgerAgent          │
                    │  生成评测用例 + 执行评测   │
                    └────────────┬─────────────┘
                                 │ 评测结果
                    ┌────────────▼─────────────┐
                    │    AnalyzerAgent         │
                    │  失败模式分析 + 诊断报告   │
                    └────────────┬─────────────┘
                                 │ 缺陷分析
                    ┌────────────▼─────────────┐
                    │   ObtainerAgent          │
                    │  数据获取 + 清洗结构化     │
                    └────────────┬─────────────┘
                                 │ 训练数据
                    ┌────────────▼─────────────┐
                    │    TrainerAgent          │
                    │  增量训练 + 持续学习       │
                    └────────────┬─────────────┘
                                 │ 优化后模型
                    ┌────────────▼─────────────┐
                    │     回到JudgerAgent       │
                    │   (闭环迭代直到满意)       │
                    └──────────────────────────┘
```

### 7.4 使用方式

**WebUI API模式**（推荐）：
```bash
cp examples/config/starter.yaml ./starter.yaml  # 编辑填入API配置
python scripts/download_ui_release.py            # 安装前端
python api/start.py                              # → http://localhost:8855
```

**终端模式**：
```bash
python examples/scripts/run_starter.py
```

### 7.5 多环境架构

LoopAI推荐分离的Conda环境以避免CUDA/PyTorch冲突：

| 环境 | 用途 |
|------|------|
| `loopai` (Python 3.12) | 核心运行时 + API服务 + 图编排 |
| `loopai-vllm` (Python 3.10) | 本地OpenAI兼容推理(Judger/Analyzer) |
| `loopai-llamafactory` (Python 3.10) | LLaMA-Factory训练 |
| `loopai-verl` (Python 3.10) | verl训练 |

---

## 8. L3+L4 整体架构与数据流

### 8.1 生态全景数据流图

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                           DataFlow 生态 L3+L4 全景                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌──────────────────────── L3: 智能体编排层 ────────────────────────┐        ║
║  │                                                                │        ║
║  │  ┌──────────────┐    ┌──────────────┐    ┌────────────────┐    │        ║
║  │  │  AgentFlow   │    │DataFlow-Skills│    │ DataFlow-Agent │    │        ║
║  │  │              │    │              │    │                │    │        ║
║  │  │ Seed+Sandbox │    │ 目标+样例JSONL│    │  自然语言描述   │    │        ║
║  │  │      ↓       │    │      ↓       │    │      ↓         │    │        ║
║  │  │ 轨迹采样     │    │ 算子决策     │    │  任务分析      │    │        ║
║  │  │ 轨迹选择     │    │      ↓       │    │      ↓         │    │        ║
║  │  │ QA合成       │    │ Pipeline代码 │    │  算子选择+编排  │    │        ║
║  │  │      ↓       │    │      ↓       │    │      ↓         │    │        ║
║  │  │ 合成QA+轨迹  │    │ 可执行.py    │    │  Pipeline代码  │    │        ║
║  │  └──────┬───────┘    └──────┬───────┘    └───────┬────────┘    │        ║
║  │         │                   │                    │              │        ║
║  │         └───────────────────┼────────────────────┘              │        ║
║  │                             │                                   │        ║
║  │                    训练数据 (JSONL)                              │        ║
║  └─────────────────────────┬───────────────────────────────────────┘        ║
║                            │                                                 ║
║                            ▼                                                 ║
║  ┌──────────────────────── L4: 训练评估闭环层 ──────────────────────┐        ║
║  │                                                                 │        ║
║  │  ┌──────────────────────────────────────┐                       │        ║
║  │  │            DataFlex                  │                       │        ║
║  │  │  训练循环内动态数据调度              │                       │        ║
║  │  │  ┌──────────┬──────────┬──────────┐ │                       │        ║
║  │  │  │Selection │ Mixture  │Reweight  │ │                       │        ║
║  │  │  │LESS/NICE │DOREMI/ODM│Loss Rewe │ │                       │        ║
║  │  │  └──────────┴──────────┴──────────┘ │                       │        ║
║  │  │  基于LLaMA-Factory + DeepSpeed ZeRO-3│                       │        ║
║  │  └──────────────┬───────────────────────┘                       │        ║
║  │                 │ 微调模型                                       │        ║
║  │                 ▼                                                │        ║
║  │  ┌──────────────────────────────────────┐                       │        ║
║  │  │            One-Eval                  │                       │        ║
║  │  │  NL2Eval: 自然语言→评测报告          │                       │        ║
║  │  │  Bench Gallery + Graph/Node/State    │                       │        ║
║  │  │  Human-in-the-Loop                   │                       │        ║
║  │  └──────────────┬───────────────────────┘                       │        ║
║  │                 │ 评测报告                                       │        ║
║  │                 ▼                                                │        ║
║  │  ┌──────────────────────────────────────┐                       │        ║
║  │  │          Dataflow-LoopAI             │                       │        ║
║  │  │  NL2Optimize: 自然语言→模型优化      │                       │        ║
║  │  │                                      │                       │        ║
║  │  │  Starter → Judge → Analyze           │                       │        ║
║  │  │           → Obtain → Train → 循环    │                       │        ║
║  │  │  6 Agent子图协作闭环                 │                       │        ║
║  │  └──────────────┬───────────────────────┘                       │        ║
║  │                 │                                               │        ║
║  │                 └──────→ 优化后模型 + 新训练数据 ──→ 回到DataFlex │        ║
║  └─────────────────────────────────────────────────────────────────┘        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 8.2 关键数据流路径

**路径1: 合成训练数据（L3→L4）**
```
AgentFlow三阶段合成 → synthesized_qa.jsonl → DataFlex动态选择/配比 → 微调模型
```

**路径2: 评测反馈（L4内部）**
```
微调模型 → One-Eval(NL2Eval) → 评测报告 → LoopAI(Analyzer) → 缺陷分析
```

**路径3: 闭环优化（L4内部）**
```
缺陷分析 → LoopAI(Obtainer)获取数据 → LoopAI(Trainer)增量训练 → 回到评测
```

**路径4: 技能复用（L3内部）**
```
DataFlow-Skills(generating-dataflow-pipeline) → 生成Pipeline代码 → DataFlow-Agent验证/优化
```

### 8.3 技术栈依赖关系

| 组件 | 核心依赖 | 输出格式 |
|------|----------|----------|
| AgentFlow | 自研Sandbox(HTTP) + OpenAI API | JSONL (QA+轨迹) |
| DataFlow-Skills | Claude Code CLI | Python (.py Pipeline) |
| DataFlow-Agent | OPERATOR_REGISTRY + FastAPI | Python (.py PipelineABC) |
| DataFlex | LLaMA-Factory + DeepSpeed | 微调模型权重 |
| One-Eval | DataFlow算子 + LangGraph + FastAPI/React | 评测报告(JSON) |
| Dataflow-LoopAI | LangGraph + vLLM + LLaMA-Factory/verl | 优化后模型 |

---

## 9. 对SRS项目的价值

> SRS项目: GJB 438C格式SRS文档的三层一致性检测（语法/语义/逻辑），构建数据集与评测体系。

### 9.1 AgentFlow为SRS一致性检测合成测试用例/对抗样本

**现状痛点**: SRS项目当前Gold Standard仅3份（battery_srs / compiler_srs / scheduler_srs），测试覆盖严重不足，一致性检测引擎的假阳性优化缺乏足够样本。

**AgentFlow的适配方案**：

```
SRS文档片段(Seed)  →  AgentFlow Sandbox(RAG后端)  →  一致性检测QA合成
     ↓                        ↓                           ↓
 约束/表格/章节      轨迹采样: 检索相关条款        合成多跳一致性检测问题
                     轨迹选择: 深度+多样性打分      "约束A与表格B是否冲突?"
                     QA合成: 生成推理链             answer + reasoning_steps
```

**具体映射**：
1. **Seed输入**: SRS文档中的约束对、表格行、章节段落作为seed（复用 `seeds/` 目录结构）
2. **Sandbox环境**: 复用AgentFlow的RAG后端（`sandbox/server/backends/resources/rag.py`），将SRS知识图谱（`knowledge/srs_kb_graph_v2.json`，7720节点）构建为Faiss索引
3. **三阶段适配**：
   - **轨迹采样**: Agent探索SRS文档，检索相关约束/表格/章节，构建多跳依赖链
   - **轨迹选择**: 选择深度足够的路径（确保覆盖跨章节一致性检测）
   - **QA合成**: 生成一致性检测问题（如"约束A规定X≤5，表格B中X=7，是否一致？"）
4. **对抗样本合成**: 修改 `sampling_tips` 引导Agent探索边界情况——约束冲突、表格矛盾、逻辑死锁，合成对抗性测试用例
5. **配置适配**: 参照 `configs/synthesis/rag_config.json`，创建 `srs_config.json`，`available_tools` 设为SRS专用工具（约束检索/表格查询/章节导航）

**预期收益**: 将Gold Standard从3份扩展到100+合成测试用例，覆盖语法/语义/逻辑三层，为假阳性优化提供充分样本。

### 9.2 One-Eval对齐SRS的Gold Standard评测框架

**现状**: SRS项目已有评测框架 `srs_eval.py`（对齐Gold Standard，按层计算P/R/F1），但缺乏自动化编排和benchmark管理。

**One-Eval的适配方案**：

| One-Eval能力 | SRS项目适配 |
|-------------|-------------|
| NL2Eval | "评估一致性检测引擎在battery_srs上的语法层P/R/F1" → 自动编排 |
| Bench Gallery | 注册SRS Gold Standard为自定义benchmark（3份→扩展后100+） |
| Graph/Node/State | 将三层检测（语法→语义→逻辑）编排为可中断的图工作流 |
| Human-in-the-Loop | 在假阳性审查节点支持人工干预 |
| 自定义指标注册 | 参照 `HOW_TO_REGISTER_METRIC.md`，注册SRS专用的层间一致性指标 |

**具体对接**：
1. **Benchmark注册**: 将 `data/gjb_438c/gold_standard/` 注册为One-Eval Bench Gallery条目，元信息包含文档类型（GJB格式）、检测层级（语法/语义/逻辑）、Gold标注
2. **评测Pipeline**: One-Eval的Graph编排：加载SRS → 运行 `srs_consistency_checker_v2.py`（含Z3求解）→ 对齐Gold Standard → 计算P/R/F1 → 生成报告
3. **指标扩展**: 注册自定义指标——`ConsistencyLayerF1`（按层F1）、`FalsePositiveRate`（假阳性率）、`Z3SolverAccuracy`（Z3求解准确率）
4. **Claude Code集成**: 利用One-Eval的便携技能（`one-eval-skill`），在Claude Code中直接触发SRS评测

**预期收益**: 从手动运行 `python3 tools/srs_eval.py` 升级为"一句话触发"的自动化评测，支持多文档批量评测和报告生成。

### 9.3 DataFlow-Skills沉淀SRS处理算子为可复用技能

**现状**: SRS项目有20+处理脚本（`tools/srs_*.py`），但缺乏统一的算子抽象和可组合性，新场景需手动编写端到端脚本。

**DataFlow-Skills的适配方案**：

将SRS处理流程拆解为DataFlow算子，沉淀为Claude Code技能：

| SRS脚本 | 对应DataFlow算子类型 | 技能化方案 |
|---------|---------------------|-----------|
| `srs_mineru_parse.py` | KBC三件套入口 | `FileOrURLToMarkdownConverterFlash`的SRS适配版 |
| `srs_structurer.py` | 生成算子 | `SRSStructurer`（MinerU输出→结构化JSON） |
| `srs_table_parser.py` | 生成算子 | `SRSTableParser`（HTML表格→结构化数据） |
| `srs_constraint_extract.py` | 生成算子 | `SRSConstraintExtractor`（LLM提取7种约束） |
| `srs_consistency_checker_v2.py` | 评测算子 | `SRSConsistencyEvaluator`（三层检测+Z3求解） |
| `srs_gjb_compliance_scan.py` | 过滤算子 | `GJBComplianceFilter`（规则合规扫描） |
| `srs_eval.py` | 评测算子 | `SRSGoldStandardEvaluator`（P/R/F1计算） |
| `srs_dedup_documents.py` | 过滤算子 | `SRSContentDedupFilter`（内容指纹去重） |

**技能定义**（参照 `generating-dataflow-pipeline/SKILL.md` 格式）：

```markdown
---
name: srs-consistency-pipeline
description: GJB 438C SRS文档一致性检测Pipeline生成器
version: 1.0.0
---
# SRS一致性检测Pipeline生成器

## 核心算子（SRS专用）
1. SRSMinerUParser — PDF解析
2. SRSStructurer — 结构化JSON
3. SRSConstraintExtractor — 约束提取
4. SRSTableParser — 表格解析
5. SRSConsistencyEvaluator — 三层一致性检测
6. SRSGoldStandardEvaluator — Gold Standard评测

## 算子选择决策表
| 检测层级 | 必须使用的算子 |
|----------|---------------|
| 语法层 | SRSMinerUParser → SRSStructurer → 语法检查 |
| 语义层 | SRSConstraintExtractor → SRSTableParser → 语义对齐 |
| 逻辑层 | SRSConstraintExtractor → SRSConsistencyEvaluator(Z3) |
```

**具体步骤**：
1. **算子化**: 将 `tools/srs_*.py` 重构为继承 `OperatorABC` 的算子，注册到 `OPERATOR_REGISTRY`
2. **技能文档**: 为每个算子创建 `core_text/` 风格的API参考（`SKILL.md` + `examples/good.md` + `examples/bad.md`）
3. **Pipeline生成技能**: 创建 `srs-consistency-pipeline` 技能，参照 `generating-dataflow-pipeline` 的决策表模式
4. **开发助手**: 扩展 `dataflow-dev` 技能的knowledge_base.md，加入SRS算子列表

**预期收益**: SRS处理流程从20+独立脚本变为可组合的算子Pipeline，新场景只需描述目标即可自动生成检测流程。

### 9.4 LoopAI用于一致性检测的假阳性优化闭环

**现状**: SRS项目当前在进行"一致性检测假阳性优化"，这是一个需要反复迭代的调优过程——检测→分析误报→调整规则/阈值→重新检测。

**LoopAI的适配方案**：

将假阳性优化建模为LoopAI的闭环优化问题：

```
"优化SRS一致性检测引擎，降低假阳性率"
                    ↓ NL2Optimize
        ┌───────────────────────┐
        │   StarterAgent        │
        │   解析优化目标         │
        └───────────┬───────────┘
                    ↓
        ┌───────────────────────┐
        │   JudgerAgent         │
        │   在Gold Standard上   │
        │   运行srs_eval.py     │
        │   收集假阳性样本       │
        └───────────┬───────────┘
                    ↓ 假阳性案例
        ┌───────────────────────┐
        │   AnalyzerAgent       │
        │   分析假阳性模式:      │
        │   - 同值检测误触发     │
        │   - 表格对齐错误       │
        │   - Z3约束建模偏差     │
        └───────────┬───────────┘
                    ↓ 缺陷分析
        ┌───────────────────────┐
        │   ObtainerAgent       │
        │   获取优化数据:        │
        │   - AgentFlow合成对抗  │
        │     样本              │
        │   - 检索GJB规则补充    │
        └───────────┬───────────┘
                    ↓ 优化训练数据
        ┌───────────────────────┐
        │   TrainerAgent        │
        │   优化检测引擎:        │
        │   - 调整规则阈值       │
        │   - 优化LLM prompt     │
        │   - 扩展Z3约束建模     │
        └───────────┬───────────┘
                    ↓ 优化后引擎
              回到JudgerAgent
           (闭环迭代直到F1达标)
```

**六Agent的SRS适配**：

| LoopAI Agent | SRS假阳性优化中的角色 |
|-------------|---------------------|
| StarterAgent | 解析"降低假阳性"目标，编排优化工作流 |
| JudgerAgent | 运行 `srs_eval.py`，在Gold Standard上评测，收集假阳性案例 |
| AnalyzerAgent | 分析假阳性模式——按层（语法/语义/逻辑）分类，识别规则缺陷 |
| ObtainerAgent | 用AgentFlow合成针对性对抗样本，检索GJB 438C规则补充知识 |
| TrainerAgent | 调整检测规则阈值、优化约束提取prompt、扩展Z3约束建模 |
| ConfigerAgent | 管理检测引擎配置（如 `srs_consistency_checker_v2.py` 的参数） |

**具体对接**：
1. **评测集成**: JudgerAgent调用 `srs_eval.py`，将Gold Standard作为评测集
2. **分析集成**: AnalyzerAgent分析 `data/gjb_438c/consistency_reports/` 中的检测报告，识别假阳性模式
3. **数据获取**: ObtainerAgent调用AgentFlow（9.1节方案）合成针对性对抗样本
4. **训练优化**: TrainerAgent通过DataFlex微调约束提取LLM，或直接调整 `knowledge/gjb_438c_rules.json` 规则库
5. **闭环迭代**: 每轮优化后回到评测，直到假阳性率低于目标阈值

**预期收益**: 假阳性优化从手动迭代升级为自动化闭环，6个Agent协作完成"检测→分析→获取→优化→再检测"的全流程，大幅加速优化收敛。

### 9.5 综合价值总结

| SRS项目需求 | 对应DataFlow组件 | 价值 |
|------------|-----------------|------|
| Gold Standard扩展(3→100+) | AgentFlow三阶段合成 | 自动合成一致性检测测试用例和对抗样本 |
| 评测自动化 | One-Eval (NL2Eval) | "一句话触发"三层一致性评测+报告生成 |
| 算子复用 | DataFlow-Skills | 20+脚本沉淀为可组合算子+技能 |
| 假阳性优化 | Dataflow-LoopAI | 6 Agent闭环自动优化检测引擎 |
| 检测引擎训练 | DataFlex | 动态选择/配比SRS训练数据微调LLM |
| Pipeline自动编排 | DataFlow-Agent | 自然语言→自动生成SRS检测Pipeline |

**推荐的落地路径**：
1. **Phase 1** (短期): 用DataFlow-Skills的 `generating-dataflow-pipeline` 技能，将 `tools/srs_*.py` 算子化
2. **Phase 2** (中期): 用AgentFlow合成SRS一致性检测测试用例，扩展Gold Standard
3. **Phase 3** (中期): 用One-Eval的NL2Eval机制，自动化SRS评测流程
4. **Phase 4** (长期): 用LoopAI构建假阳性优化闭环，实现检测引擎的持续自优化

---

> **参考资料**:
> - AgentFlow源码: `dataflow_repos/AgentFlow/`
> - DataFlow-Skills源码: `dataflow_repos/DataFlow-Skills/`
> - DataFlow Core源码: `dataflow_repos/DataFlow/dataflow/`
> - AgentFlow GitHub: https://github.com/OpenDCAI/AgentFlow
> - DataFlow-Skills GitHub: https://github.com/OpenDCAI/DataFlow-Skills
> - DataFlex GitHub: https://github.com/OpenDCAI/DataFlex
> - One-Eval GitHub: https://github.com/OpenDCAI/One-Eval
> - Dataflow-LoopAI GitHub: https://github.com/OpenDCAI/Dataflow-LoopAI
> - DataFlow-Agent DeepWiki: https://deepwiki.com/OpenDCAI/DataFlow/4-dataflow-agent
> - AgentFlow文档: https://opendcai.github.io/AgentFlow-Doc/en/
