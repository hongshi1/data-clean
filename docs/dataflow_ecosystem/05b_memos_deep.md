# MemOS 代码级深度分析

> 调研对象：MemTensor/MemOS（10.4k stars，版本 2.0.25 Stardust，commit e8204062）
> 调研日期：2026-07-30
> 调研方法：DeepWiki（60+ 页代码级文档）+ arXiv 论文（2507.03724 长版 / 2505.22101 短版）
> 数据来源：DeepWiki 页面索引（last indexed 2026-07-25）、GitHub 源码引用、arXiv 摘要
> 关联文档：`05_apps_crosscutting.md` 第 4 节为 README 级概览，本文档为其代码级深度补充

---

## 目录

1. [概览与定位](#1-概览与定位)
2. [项目结构与包导出](#2-项目结构与包导出)
3. [MOS 架构：核心类层次（核心）](#3-mos-架构核心类层次核心)
4. [Memory Cube 架构](#4-memory-cube-架构)
5. [系统分层架构](#5-系统分层架构)
6. [REST API 与集成方式](#6-rest-api-与集成方式)
7. [记忆处理 Pipeline](#7-记忆处理-pipeline)
8. [记忆搜索与检索系统](#8-记忆搜索与检索系统)
9. [存储后端架构](#9-存储后端架构)
10. [TreeTextMemory 数据结构](#10-treetextmemory-数据结构)
11. [MemScheduler 异步调度系统](#11-memscheduler-异步调度系统)
12. [插件生态：OpenClaw + Reflect2Evolve](#12-插件生态openclaw--reflect2evolve)
13. [L1/L2/L3 记忆架构与技能结晶化](#13-l1l2l3-记忆架构与技能结晶化)
14. [评估框架](#14-评估框架)
15. [对 SRS 项目的深度应用价值](#15-对-srs-项目的深度应用价值)

---

## 1. 概览与定位

### 1.1 核心定位

MemOS 是面向 LLM 和 AI Agent 的**记忆操作系统**（Memory Operating System），将"记忆"提升为一等公民（first-class）系统资源。它统一长期记忆的 **存储 / 检索 / 管理**，构建在图数据库与向量数据库之上，提供结构化、可检视的记忆系统。

> 来源：[DeepWiki 1-overview] README.md L34-44

### 1.2 OS 隐喻映射

MemOS 将传统操作系统概念映射到记忆管理域：

| OS 功能 | MemOS 对应 | 实现实体 |
|---------|-----------|----------|
| 进程管理 | 多用户/多租户编排 | `MOSCore`、`UserManager` |
| 内存管理 | Memory Cube 分配与生命周期 | `GeneralMemCube`、`MOSCore` |
| 文件系统 | 图谱化记忆存储 | `TreeTextMemory`、`BaseGraphDB` |
| 调度器 | 异步记忆处理 | `GeneralScheduler`、`SchedulerFactory` |
| I/O 系统 | 记忆读写操作 | `MemReaderFactory`、`Searcher` |
| API 层 | 用户接口 | FastAPI routers + handlers |

> 来源：[DeepWiki 1-overview] src/memos/mem_os/core.py L38-55

### 1.3 论文核心论点

- **短版**（arXiv:2505.22101）："Memory-Augmented Generation (MAG)"概念首次提出，将记忆分为 parametric / activation / plaintext 三类，MemCube 作为标准化记忆抽象
- **长版**（arXiv:2507.03724，36 页 10 图）：扩展为完整系统设计，强调 MemOS 带来 controllability（可控性）、plasticity（可塑性）、evolvability（可演化性），为持续学习与个性化建模奠基

> 来源：arXiv:2507.03724 摘要、arXiv:2505.22101 摘要

### 1.4 版本与依赖

| 属性 | 值 |
|------|-----|
| 包名 | `MemoryOS`（import 名 `memos`） |
| 版本 | 2.0.25 |
| Python | >= 3.10 |
| 许可证 | Apache 2.0 |
| 核心依赖 | `openai`>=1.77、`fastapi[all]`、`sqlalchemy`、`redis` |

> 来源：[DeepWiki 1.1-project-structure] pyproject.toml

---

## 2. 项目结构与包导出

### 2.1 仓库布局

```
MemOS/
├── src/memos/                          # 主 Python 包
│   ├── mem_os/                         # MOS 编排层（core.py / main.py / product.py）
│   ├── mem_cube/                       # Memory Cube（general.py）
│   ├── multi_mem_cube/                 # 多 Cube 视图（single_cube / composite_cube / views）
│   ├── mem_scheduler/                  # 异步调度器（general_scheduler / optimized_scheduler）
│   ├── mem_reader/                     # 记忆读取器（simple_struct / multi_modal_struct）
│   ├── memories/textual/               # 文本记忆（tree.py / item.py / preference.py）
│   │   └── tree_text_memory/           # 树文本记忆
│   │       ├── organize/               # 组织（manager / reorganizer）
│   │       └── retrieve/               # 检索（searcher / recall / advanced_searcher）
│   ├── graph_dbs/                      # 图数据库后端（neo4j / neo4j_community / polardb / postgres）
│   ├── vec_dbs/                        # 向量数据库（milvus / qdrant）
│   ├── chunkers/                       # 分块器（markdown / charactertext / sentence）
│   ├── reranker/                       # 重排序器（cosine_local / http_bge / noop）
│   ├── api/                            # REST API 层（server_api / routers / handlers / mcp_serve）
│   ├── configs/                        # 配置系统（mem_os / mem_cube / graph_db / vec_db）
│   ├── templates/                      # Prompt 模板
│   └── dream/                          # Dream 记忆固化系统
├── apps/                               # 插件应用
│   ├── memos-local-plugin/             # Reflect2Evolve（L1/L2/L3 本地记忆引擎，TypeScript）
│   └── memos-local-openclaw/           # OpenClaw 集成插件（TypeScript + SQLite）
├── evaluation/                         # 评估框架脚本
├── tests/                              # 测试套件
└── pyproject.toml                      # Poetry 依赖管理
```

> 来源：[DeepWiki 1.1-project-structure]

### 2.2 包导出（`__init__.py`）

```python
# src/memos/__init__.py
from memos.configs.mem_cube import GeneralMemCubeConfig
from memos.configs.mem_os import MOSConfig
from memos.configs.mem_scheduler import SchedulerConfigFactory
from memos.mem_cube.general import GeneralMemCube
from memos.mem_os.main import MOS
from memos.mem_scheduler.general_scheduler import GeneralScheduler
from memos.mem_scheduler.scheduler_factory import SchedulerFactory
```

| 导出类 | 模块 | 用途 |
|--------|------|------|
| `MOS` | `memos.mem_os.main` | 主记忆编排器（CoT 增强入口） |
| `GeneralMemCube` | `memos.mem_cube.general` | 记忆容器 |
| `GeneralMemCubeConfig` | `memos.configs.mem_cube` | Cube 配置 |
| `GeneralScheduler` | `memos.mem_scheduler.general_scheduler` | 异步任务调度器 |
| `SchedulerFactory` | `memos.mem_scheduler.scheduler_factory` | 调度器工厂 |
| `MOSConfig` | `memos.configs.mem_os` | MOS 配置 |

> 来源：[DeepWiki 1.1-project-structure] src/memos/__init__.py L1-21

### 2.3 可选依赖组（模块化安装）

MemOS 通过 Poetry optional groups 支持模块化安装：
- **图数据库**：`neo4j`、`polardb`（Apache AGE）、`postgres`
- **LLM 提供商**：`openai`、`ollama`、`huggingface`
- **向量存储**：`milvus`、`qdrant`、原生 DB 向量

> 来源：[DeepWiki 1.1-project-structure] pyproject.toml L68-145

---

## 3. MOS 架构：核心类层次（核心）

### 3.1 三层类继承结构

MOS 编排层由三个渐进增强的类构成：

```
MOSCore (base, 单用户基础)
  └── MOS (CoT 增强, 库使用入口)
  └── MOSProduct (多用户服务端编排, LRU 缓存 + 流式)
```

> 来源：[DeepWiki 3.3-mos-architecture]

### 3.2 MOSCore：单用户基础类

**文件**：`src/memos/mem_os/core.py:38-43`

**职责**：管理单用户上下文的记忆操作，编排 `MemCube` 实例，协调记忆读取/存储/检索。

**核心组件**：

| 组件 | 类型 | 职责 | 源码位置 |
|------|------|------|----------|
| `config` | `MOSConfig` | 系统配置 | core.py:46 |
| `chat_llm` | `LLMFactory` | 聊天 LLM | core.py:49 |
| `mem_reader` | `MemReaderFactory` | 记忆提取器 | core.py:50 |
| `mem_cubes` | `OptimizedThreadSafeDict` | 线程安全的 Cube 注册表 | core.py:53 |
| `user_manager` | `UserManager` | 用户验证与权限 | core.py:59-62 |
| `_mem_scheduler` | `GeneralScheduler` | 异步记忆摄入 | core.py:73-78 |

**关键方法签名**：

```python
class MOSCore:
    def __init__(self, config: MOSConfig): ...
    def add_memory(self, user_id, mem_cube_id, messages, ...): ...
    def search_memory(self, user_id, query, mem_cube_id, ...): ...
    def chat(self, user_id, query, mem_cube_id, ...): ...
    def get_memory(self, user_id, mem_cube_id, ...): ...
    def mem_scheduler_on(self): ...   # core.py:141-167
    def mem_scheduler_off(self): ...
```

**初始化与验证流程**：
1. 初始化 `LLMFactory` 和 `MemReaderFactory`
2. 通过 `UserManager` 验证用户存在性（防止未授权访问）
3. 懒加载 `GeneralScheduler`：当 `enable_mem_scheduler=True` 时初始化 `chat_llm`、`process_llm`、`db_engine`

> 来源：[DeepWiki 3.3-mos-architecture] core.py L38-139

**任务提交标签**（调度器入口）：

| 任务标签 | 源码 | 用途 |
|----------|------|------|
| `ADD_TASK_LABEL` | core.py:20 | 异步处理新记忆项 |
| `MEM_READ_TASK_LABEL` | core.py:22 | 触发后台记忆读取 |
| `ANSWER_TASK_LABEL` | core.py:21 | 从 AI 回答提取长期记忆 |
| `QUERY_TASK_LABEL` | core.py:24 | 跟踪查询频率，用于工作记忆提升 |

### 3.3 MOS：CoT 增强扩展

**文件**：`src/memos/mem_os/main.py:24-28`

**职责**：在 `MOSCore` 基础上增加 Chain-of-Thought（CoT）查询分解和自动配置，是开发者通过 `MOS.simple()` 使用库的推荐入口。

**CoT 增强机制（PRO_MODE）**：

```python
class MOS(MOSCore):
    @classmethod
    def simple(cls, ...): ...  # main.py:80-106 自动配置入口

    def chat(self, ...):
        if self.PRO_MODE:
            sub_questions = self.cot_decompose(query)  # main.py:159
            sub_answers = self.get_sub_answers(sub_questions)  # main.py:179-185
            # ContextThreadPoolExecutor 并行搜索+回答子问题
```

**关键 CoT 函数**：
- `cot_decompose`：使用 `COT_DECOMPOSE_PROMPT` 将复杂查询分解为独立子问题
- `get_sub_answers`：用 `ContextThreadPoolExecutor` 并行执行子问题搜索与回答
- `_auto_configure`：从环境变量（`OPENAI_API_KEY`、`MOS_TEXT_MEM_TYPE`）自动拉取配置

> 来源：[DeepWiki 3.3-mos-architecture] main.py L24-231

### 3.4 MOSProduct：多用户服务端编排

**文件**：`src/memos/mem_os/product.py:92-96`

**职责**：面向服务器环境的多用户编排器，具备 LRU 实例缓存、持久化用户管理、流式支持。

### 3.5 工具编排层

| 工具 | 文件 | 功能 |
|------|------|------|
| `clean_json_response` | `utils/format_utils.py:10` | 防御性清除 LLM 输出的 markdown 标记 |
| `split_continuous_references` | `utils/reference_utils.py:6` | 规范化流式/批量文本中的引用标签 |
| `analyze_tree_structure_enhanced` | `utils/format_utils.py:28` | 评估层级记忆结构的质量与密度 |

> 来源：[DeepWiki 3.3-mos-architecture]

---

## 4. Memory Cube 架构

### 4.1 三种记忆类型

Memory Cube（MemCube）是 MemOS 中隔离的记忆容器，封装不同类型的记忆存储与检索能力。

| 记忆类型 | 实现类 | 职责 | 源码位置 |
|----------|--------|------|----------|
| **TreeTextMemory** | `TreeTextMemory` | 图谱化持久存储（WorkingMemory + LongTermMemory + UserMemory） | tree.py:39-42 |
| **ActivationMemory** | `ActivationMemory` | 短期上下文与激活轨迹 | core.py:27 |
| **PreferenceMemory** | `PreferenceTextualMemory` | 用户偏好与人格 | pyproject.toml:99-103 |

> 来源：[DeepWiki 1-overview] [DeepWiki 3.2-memory-cubes]

### 4.2 NaiveMemCube 内部架构

`NaiveMemCube`（及其生产实现 `GeneralMemCube`）是组合对象，协调多种记忆子系统：

```
NaiveMemCube
├── text_mem  (TreeTextMemory)
│   ├── WorkingMemory    (短期, 默认 20 条, FIFO 清理)
│   ├── LongTermMemory   (长期, 默认 1500 条, 定期重组)
│   ├── UserMemory       (用户画像, 默认 480 条)
│   ├── SkillMemory      (工具技能)
│   └── PreferenceMemory (用户偏好)
├── act_mem   (ActivationMemory, 短期交互状态)
├── para_mem  (ParametricMemory, 模型适配参数)
├── tool_mem  (ToolMemory, API schema 与工具轨迹)
└── skill_mem (SkillMemory, 可复用任务策略)
```

> 来源：[DeepWiki 3.2-memory-cubes] memory_handler.py L54-87

### 4.3 Multi-Cube 访问模式：View 抽象

MemOS 通过 `MemCubeView` 接口抽象单 Cube 与多 Cube 集合的差异：

| View 类 | 源码位置 | 行为 |
|---------|----------|------|
| `SingleCubeView` | `single_cube.py:48-56` | 限定单个 `cube_id`，直接交互 `NaiveMemCube` + `SimpleStructMemReader` + `OptimizedScheduler` |
| `CompositeCubeView` | `composite_cube.py:18-28` | 聚合多个 `SingleCubeView`，用于多租户或共享知识库访问 |

**并行执行与合并**：`CompositeCubeView` 使用 `ContextThreadPoolExecutor` 跨所有关联 Cube 并行搜索，结果合并为统一结构（含 `text_mem`、`act_mem`、`para_mem`、`tool_mem`、`skill_mem`、`pref_mem`）。

> 来源：[DeepWiki 3.2-memory-cubes] composite_cube.py L46-83

### 4.4 隔离与多租户机制

- **Cube 标识**：`cube_id`（亦称 `mem_cube_id`）作为规范标识符
- **权限作用域**：`ChatRequest` 指定 `readable_cube_ids` 和 `writable_cube_ids` 强制访问边界
- **向量隔离**：`QdrantVecDB` 使用特定 collection 名 + payload 过滤器（`user_name`、`memory_type`）确保共享基础设施内的数据隔离

> 来源：[DeepWiki 3.2-memory-cubes] product_models.py L88-91, L146-151; qdrant.py L25-32

---

## 5. 系统分层架构

### 5.1 四层架构总览

```
┌─────────────────────────────────────────────────┐
│  Layer 1: API 层 (FastAPI)                       │
│  server_api.py → server_router.py → handlers     │
│  RequestContextMiddleware (trace_id 注入)          │
├─────────────────────────────────────────────────┤
│  Layer 2: 核心 MOS 层                            │
│  MOSCore (基础) → MOS (CoT增强) → MOSProduct      │
│  UserManager (验证) + mem_cubes (线程安全注册表)    │
├─────────────────────────────────────────────────┤
│  Layer 3: 记忆调度系统                           │
│  GeneralScheduler → ScheduleTaskQueue             │
│  ├── SchedulerRedisQueue (生产, Redis Streams)    │
│  └── SchedulerLocalQueue (开发, 内存)             │
│  SchedulerDispatcher (ContextThreadPoolExecutor)  │
├─────────────────────────────────────────────────┤
│  Layer 4: 存储与检索层                           │
│  GeneralMemCube (隔离容器)                        │
│  ├── GraphDB: Neo4j / PolarDB / PostgreSQL        │
│  └── VecDB:  Milvus / Qdrant / 原生              │
└─────────────────────────────────────────────────┘
```

> 来源：[DeepWiki 4.1-overall-architecture]

### 5.2 请求处理流程

```
HTTP 请求
  → RequestContextMiddleware (生成/提取 trace_id, 设置全局 RequestContext)
    → server_router (路由到 /product/add, /product/search, /product/chat/stream 等)
      → HandlerDependencies (依赖注入容器, 预热组件)
        → AddHandler / SearchHandler / ChatHandler (类处理器)
          → SingleCubeView / CompositeCubeView (记忆访问抽象)
            → TreeTextMemory (图谱操作) + Searcher (混合检索)
```

> 来源：[DeepWiki 4.2-api-layer-and-request-handling] server_api.py L14-48, server_router.py L68-81

### 5.3 组件初始化（`init_server()`）

`component_init.py` 中的 `init_server()` 集中初始化所有后端组件：
- **Redis 客户端**：当 `MEMSCHEDULER_USE_REDIS_QUEUE` 启用时初始化，用于任务跟踪
- **语言模型**：通过 `LLMFactory` 初始化 extraction / chat / feedback 三类 LLM
- **记忆系统**：实例化 `NaiveMemCube` + 准备 `OptimizedScheduler`
- **插件发现**：通过 `plugin_manager` 发现并初始化系统插件

> 来源：[DeepWiki 4.2-api-layer-and-request-handling] component_init.py L109-210

---

## 6. REST API 与集成方式

### 6.1 端点总览

所有端点前缀 `/product`，使用 Pydantic 模型验证。

#### 记忆操作端点

| 端点 | 方法 | 请求模型 | 响应模型 | 说明 |
|------|------|----------|----------|------|
| `/product/add` | POST | `APIADDRequest` | `MemoryResponse` | 从消息/文件/文本添加记忆 |
| `/product/search` | POST | `APISearchRequest` | `SearchResponse` | 混合检索策略搜索记忆 |
| `/product/get_memory` | POST | `GetMemoryRequest` | `GetMemoryResponse` | 分页+过滤获取记忆 |
| `/product/get_memory/{id}` | GET | Path param | `GetMemoryResponse` | 按 ID 获取单条记忆 |
| `/product/get_all` | POST | `GetMemoryPlaygroundRequest` | `MemoryResponse` | 获取全部/子图用于可视化 |

#### 聊天端点

| 端点 | 方法 | 请求模型 | 响应格式 | 说明 |
|------|------|----------|----------|------|
| `/product/chat/complete` | POST | `APIChatCompleteRequest` | JSON | 非流式记忆增强聊天 |
| `/product/chat/stream` | POST | `ChatRequest` | SSE | 流式聊天 + 记忆检索 |

#### 调度器监控端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/product/scheduler/allstatus` | GET | 所有任务聚合指标 |
| `/product/scheduler/task_queue_status` | GET | 实时队列深度指标 |
| `/product/scheduler/wait` | POST | 阻塞等待用户队列空闲 |

> 来源：[DeepWiki 5.1-rest-api-endpoints]

### 6.2 核心请求模型

```python
# src/memos/api/product_models.py
class BaseResponse[T]:  # L20-25
    code: int
    message: str
    data: T

class ChatRequest:  # L136-175
    query: str
    readable_cube_ids: list[str]
    writable_cube_ids: list[str]
    mode: str          # fast / fine / mixture / deep
    relativity: float  # 默认 0.45, 相关性阈值

class APISearchRequest:  # L17-20
    query: str
    top_k: int
    dedup: str          # "sim" | "mmr"
    relativity: float

class APIADDRequest:  # L58-64
    user_id: str
    memory_content: str
    async_mode: bool    # 默认 True, 异步摄入
```

> 来源：[DeepWiki 5.1-rest-api-endpoints] [DeepWiki 4.2-api-layer-and-request-handling]

### 6.3 SSE 流式格式

`/product/chat/stream` 返回 SSE 结构：
- `type`：`status` | `reference` | `text` | `error`
- `data`：实际内容块或元数据对象

> 来源：[DeepWiki 5.1-rest-api-endpoints] docs/.../chat.md L57-60

### 6.4 四种集成方式

| 集成方式 | 适用场景 | 关键类/文件 |
|----------|----------|-------------|
| **Cloud API** | 全托管应用接入 | `MemOSClient`（src/memos/api/client.py:33） |
| **Self-Hosted REST** | 私有部署 | FastAPI server_api + HandlerDependencies |
| **Python SDK** | 深度集成 | 直接使用 `MOS.simple()` + `MOSCore` API |
| **MCP Server** | AI Agent / MCP 兼容客户端 | `MOSMCPServer`（src/memos/api/mcp_serve.py） |

> 来源：[DeepWiki 5.4-client-integration] [DeepWiki 5.5-mcp-server]

### 6.5 MCP 服务器

`MOSMCPServer` 基于 `FastMCP` 框架，将 MOS 内部功能暴露为可发现的 MCP 工具：

| 工具名 | 内部函数 | 说明 |
|--------|----------|------|
| `chat` | `mos_core.chat()` | 使用记忆 + 可选 CoT 生成回答 |
| `add_memory` | `mos_core.add_memory()` | 摄入内容到用户默认 Cube |
| `search_memory` | `mos_core.search_memory()` | 跨可访问 Cube 混合搜索 |
| `create_user` | `mos_core.create_user()` | 创建用户及关联记忆空间 |
| `create_mem_cube` | `mos_core.create_mem_cube()` | 创建专用记忆 Cube |

**配置加载**：`load_default_config` 从环境变量映射到 `MOSConfig`，自动处理 Neo4j Community Edition 约束（`use_multi_db=False`、`neo4j_auto_create=False`）。

> 来源：[DeepWiki 5.5-mcp-server] mcp_serve.py L18-160

### 6.6 客户端 SDK（MemOSClient）

```python
# src/memos/api/client.py
class MemOSClient:
    def __init__(self, api_key, ...): ...  # L33-61
    def add(self, user_id, messages, mem_cube_id, ...): ...  # L142-156
    def search(self, query, user_id, ...): ...  # L192-205
```

- 认证：`Authorization: Token <api_key>` 头
- 参数验证：`user_id` 和 `agent_id` 必须提供恰好一个

> 来源：[DeepWiki 5.4-client-integration] client.py L33-205

---

## 7. 记忆处理 Pipeline

### 7.1 Pipeline 总览

记忆处理 Pipeline 将原始多模态输入（文本、聊天历史、文件、图像）转化为结构化、可搜索、语义增强的记忆项（`TextualMemoryItem`）。

```
原始输入 (文本/文件/图像/聊天)
  → MemReaderFactory (选择 reader)
    → MultiModalParser (路由到子解析器)
      ├── StringParser / TextContentParser (纯文本)
      ├── UserParser / AssistantParser / SystemParser / ToolParser (角色消息)
      ├── FileContentParser (文档: PDF/DOCX/Markdown, 下载+解析+分块)
      └── ImageParser (图像: VLM 描述提取)
    → 模式选择: Fast (直接提取) 或 Fine (LLM 增强)
    → _build_node (LLM 提取 + JSON 解析 + 嵌入生成)
    → TextualMemoryItem (结构化记忆项 + TreeNodeTextualMemoryMetadata)
```

> 来源：[DeepWiki 4.3-memory-processing-pipeline] [DeepWiki 6.1-memory-extraction-and-reading]

### 7.2 MemReader 类层次

```
BaseMemReader (base.py)
  └── SimpleStructMemReader (simple_struct.py:166)    # 基础文本+聊天
        └── MultiModalStructMemReader (multi_modal_struct.py:34)  # 扩展文件+图像
```

- `SimpleStructMemReader`：管理主 LLM（提取）和 `Embedder`（向量化）
- `MultiModalStructMemReader`：增加 `MultiModalParser` 支持 + `image_parser_llm`（视觉模型）

> 来源：[DeepWiki 6.1-memory-extraction-and-reading]

### 7.3 Fast vs Fine 模式

| 模式 | LLM 使用 | 逻辑 | 适用场景 |
|------|----------|------|----------|
| **Fast** | 无 | `_extract_text_from_content` 提取原始文本，按角色分配 `memory_type`，`embedder.embed` 生成嵌入，自动标签 `mode:fast` | 实时聊天 |
| **Fine** | 高 | LLM 共指消解（"I"→"The user"）、时态规范化、主题标签、`SIMPLE_STRUCT_MEM_READER_PROMPT` 提取经验/信念/计划 | 高质量结构化记忆 |

> 来源：[DeepWiki 6.1-memory-extraction-and-reading] [DeepWiki 6.2-multi-modal-content-processing]

### 7.4 多模态解析器路由

`MultiModalParser._get_parser()` 路由逻辑（`multi_modal_parser.py:103-137`）：

1. 字符串消息 → `StringParser`
2. 有 `type` 字段 → 查 `type_parsers` 字典（`text`、`file`、`image_url`、`tool_input` 等）
3. 有 `role` 字段 → 查 `role_parsers` 字典（`system`、`user`、`assistant`、`tool`）

| 解析器 | 文件 | 职责 |
|--------|------|------|
| `FileContentParser` | file_content_parser.py:50 | URL 下载、Markdown 直取、文档解析（markitdown）、分块 |
| `ImageParser` | image_parser.py:142 | VLM 描述提取（`IMAGE_ANALYSIS_PROMPT_EN/ZH`） |
| `SystemParser` | system_parser.py:113 | `<tool_schema>` 提取、递归移除 description 减少 token |
| `UserParser` | user_parser.py:63 | 多模态部件语言检测 + `SourceMessage` 创建 |
| `AssistantParser` | assistant_parser.py:146 | 处理 `refusal` 和 `tool_calls` |
| `ToolParser` | tool_parser.py:28 | 工具调用输出处理 |

> 来源：[DeepWiki 6.2-multi-modal-content-processing]

### 7.5 聊天窗口与分块

- **Token 计数**：`count_tokens_text` 测量消息大小，`chat_window_max_tokens`（默认 1024）定义窗口边界
- **滑动窗口**：长对话按窗口分组，每个窗口送 LLM 提取
- **文档分块**：`MarkdownChunker`（感知标题结构）、`CharacterTextChunker`（递归字符分割）、`SimpleTextSplitter`（兜底）
- **默认分块参数**：`chunk_size`=1280 tokens，`chunk_overlap`=200 tokens
- **并行处理**：`ContextThreadPoolExecutor` 并行处理窗口/分块

> 来源：[DeepWiki 6.1-memory-extraction-and-reading] [DeepWiki 4.3-memory-processing-pipeline]

### 7.6 TextualMemoryItem 数据结构

Pipeline 最终输出 `TextualMemoryItem`，封装处理后的记忆及其元数据：

```python
# src/memos/memories/textual/item.py
class TextualMemoryItem:  # L34-38
    memory: str                    # 精炼后的文本内容
    metadata: TreeNodeTextualMemoryMetadata

class TreeNodeTextualMemoryMetadata:
    user_id: str
    session_id: str
    memory_type: str               # LongTermMemory / UserMemory / SkillMemory ...
    status: str                    # activated / archived
    key: str                       # 记忆的唯一简明标题
    tags: list[str]                # 主题关键词
    embedding: list[float]         # 向量表示
    type: str                      # 节点类型: fact / experience / topic
    sources: list[SourceMessage]   # 原始消息引用
    background: str                # 上下文摘要, 常含 [working_binding:<uuid>]
    confidence: float              # 默认 0.99
    created_at: datetime
    updated_at: datetime
    version: int
```

> 来源：[DeepWiki 4.3-memory-processing-pipeline] [DeepWiki 6.5-tree-text-memory] item.py L5-38

### 7.7 记忆质量与去重

质量控制在三个阶段实施：

| 阶段 | 机制 | 实现 |
|------|------|------|
| **提取时** | 幻觉过滤 + 记忆重写 | `SimpleStructMemReader` 双 LLM（主提取 + general_llm 质量任务） |
| **添加前** | 冲突检测 + 关键词替换判断 | `MemFeedback.add_before_search` |
| **检索时** | 相似度去重 + MMR 去重 | `SearchHandler`（sim: cosine 0.92 阈值; mmr: 多样性平衡） |

**更新过滤逻辑**（`should_keep_update`）：

| 条件 | 阈值 | 动作 |
|------|------|------|
| `old_len < 200` tokens | `change_ratio < 0.7` | 保留更新 |
| `old_len >= 200` tokens | `change_ratio < 0.2` | 保留更新 |
| `change_ratio == 0` | - | 跳过（无变化） |

> 来源：[DeepWiki 6.4-memory-quality-and-deduplication] feedback.py, utils.py L30-61

---

## 8. 记忆搜索与检索系统

### 8.1 搜索架构

`Searcher` 类是所有搜索操作的主编排器，协调任务解析、多路径并行检索、重排序和去重。

```
用户查询
  → Searcher.search (模式选择: fast/fine/mixture/deep)
    → TaskGoalParser (查询解析)
      ├── _parse_fast: FastTokenizer 简单分词
      └── _parse_fine: LLM 提取 memories/keys/tags/internet_search
    → GraphMemoryRetriever.retrieve (混合并行检索)
      ├── _graph_recall: 结构化 keys/tags 图谱匹配
      ├── _vector_recall: 嵌入向量相似度搜索
      ├── _bm25_recall: EnhancedBM25 关键词匹配
      └── _fulltext_recall: 数据库原生全文搜索
    → _maybe_rerank (BaseReranker 重排序)
    → post_retrieve (去重 + 排序 + 使用追踪)
```

> 来源：[DeepWiki 4.5-search-and-retrieval-system] [DeepWiki 6.3-memory-search-and-retrieval]

### 8.2 四种搜索模式

| 模式 | 速度 | 精度 | 描述 | 源码 |
|------|------|------|------|------|
| `fast` | 高 | 中 | 简单分词 + 向量相似度，适合实时聊天 | searcher.py:190 |
| `fine` | 低 | 高 | LLM 结构化查询分析 + 多路径召回 | searcher.py:191 |
| `mixture` | 中 | 高 | 结合 fast 和 fine 的平衡模式 | general_types.py:95 |
| `deep` | 极低 | 最高 | 多阶段推理（最多 3 阶段），迭代扩展搜索短语 | advanced_searcher.py:53-58 |

**Deep 搜索三阶段**（`AdvancedSearcher`）：
1. Stage 1：扩展（expansion）
2. Stage 2：重写（rewriting）
3. Stage 3：假设（hypothesizing）

每阶段用 `stage_retrieve` 判断当前记忆是否足够回答，不足则生成新检索短语。

> 来源：[DeepWiki 6.3-memory-search-and-retrieval]

### 8.3 混合检索策略

`GraphMemoryRetriever`（`recall.py:59-183`）实现并行混合检索：

| 方法 | 策略 | 描述 |
|------|------|------|
| `_graph_recall` | 结构化 | 匹配 `ParsedTaskGoal` 的 keys/tags 与节点元数据 |
| `_vector_recall` | 相似度 | 跨 memory_scope 的嵌入向量搜索 |
| `_bm25_recall` | 关键词 | `EnhancedBM25` 词频统计评分 |
| `_fulltext_recall` | 全文 | 数据库原生全文索引（如 PostgreSQL `tsquery`） |

### 8.4 重排序器

`RerankerFactory`（`factory.py:23-72`）支持多后端：

| 后端 | 类 | 描述 |
|------|-----|------|
| `http_bge` | `HTTPBGEReranker` | 远程 BGE 重排服务 |
| `cosine_local` | `CosineLocalReranker` | 本地 numpy 余弦相似度，支持 level_weights |
| `noop` | `NoopReranker` | 禁用重排 |

`CosineLocalReranker` 支持按记忆粒度加权（`level_weights`: `{"topic": 1.0, "concept": 1.0, "fact": 1.0}`）。

> 来源：[DeepWiki 4.5-search-and-retrieval-system] [DeepWiki 6.3-memory-search-and-retrieval]

### 8.5 去重策略

| 策略 | 逻辑 | 阈值 |
|------|------|------|
| `sim` | `_dedup_text_memories` 余弦相似度过滤 | 0.92 |
| `mmr` | `_mmr_dedup_text_memories` 最大边际相关性 | 平衡相关性与多样性 |

> 来源：[DeepWiki 4.5-search-and-retrieval-system] search_handler.py L110-116

### 8.6 专用记忆作用域

| 作用域 | 用途 | 默认容量 |
|--------|------|----------|
| `WorkingMemory` | 近期对话上下文，活跃会话状态 | 20（FIFO 清理） |
| `LongTermMemory` | 持久事实与知识 | 1500（定期重组） |
| `UserMemory` | 用户画像、偏好、个人信息 | 480（定期重组） |
| `SkillMemory` | 工具使用技能或程序性知识 | 专用 `skill_mem_top_k` |
| `PreferenceMemory` | 从交互中提取的用户偏好 | 专用 `pref_mem_top_k` |

> 来源：[DeepWiki 6.5-tree-text-memory] manager.py L67-81

---

## 9. 存储后端架构

### 9.1 存储后端对比

| 后端 | 实现类 | 向量索引 | 多数据库 | 适用场景 |
|------|--------|----------|----------|----------|
| **Neo4j Enterprise** | `Neo4jGraphDB` | 原生 HNSW（>= 5.18） | 支持（物理隔离） | 企业部署 |
| **Neo4j Community** | `Neo4jCommunityGraphDB` | 外部 VecDB | 不支持 | 社区部署 + Qdrant |
| **PolarDB** | `PolarDBGraphDB` | pgvector（IVFFlat/HNSW, 1024 维） | 支持 | PostgreSQL 兼容引擎 |
| **PostgreSQL** | `PostgresGraphDB` | pgvector | 支持 | 标准 PG 部署 |
| **Milvus** | `MilvusVecDB` | 混合（Dense + Sparse/BM25） | - | 混合向量搜索 |
| **Qdrant** | `QdrantVecDB` | HNSW | - | 高性能向量后端 |

> 来源：[DeepWiki 8.1-graph-database-architecture] [DeepWiki 8.4-vector-search-implementation]

### 9.2 BaseGraphDB 抽象接口

`BaseGraphDB`（`base.py:11-210`）定义所有图数据库实现必须履行的契约：

- **节点管理**：`add_node`、`update_node`、`delete_node`、`get_node`
- **边管理**：`add_edge`、`delete_edge`、`edge_exists`
- **图遍历**：`get_neighbors`、`get_path`、`get_subgraph`、`get_context_chain`
- **搜索操作**：`search_by_embedding`、`get_by_metadata`

### 9.3 GraphStoreFactory 后端映射

```python
# src/memos/graph_dbs/factory.py:14-27
backend_map = {
    "neo4j":           Neo4jGraphDB,            # neo4j.py:99
    "neo4j-community": Neo4jCommunityGraphDB,   # neo4j_community.py:22
    "polardb":         PolarDBGraphDB,          # polardb.py:125
    "postgres":        PostgresGraphDB,         # postgres.py:8
}
```

> 来源：[DeepWiki 8.1-graph-database-architecture] factory.py L14-27

### 9.4 多租户隔离策略

| 策略 | 配置 | 机制 |
|------|------|------|
| **物理隔离** | `use_multi_db = True` | 每租户独立数据库实例（Neo4j Enterprise 多库 / PolarDB 连接池指向租户 `db_name`） |
| **逻辑隔离** | `use_multi_db = False` | 共享单库，每节点标记 `user_name` 属性，查询自动注入 `WHERE n.user_name = $user_name` |

> 来源：[DeepWiki 8.1-graph-database-architecture] [DeepWiki 8.2-neo4j-backend]

### 9.5 Neo4j 双实现对比

| 特性 | `Neo4jGraphDB`（Enterprise） | `Neo4jCommunityGraphDB`（Community） |
|------|------------------------------|--------------------------------------|
| 向量搜索 | 原生 `vector.similarity.cosine()` | 外部 `VecDBFactory`（如 Qdrant） |
| 多数据库 | 支持（物理隔离） | 不支持（`use_multi_db` 必须为 `False`） |
| 索引创建 | 原生向量索引 + 属性索引 | 仅基础属性索引 |
| 约束 | - | `auto_create` 必须 `False`，需提供 `vec_config` |

**Community 双存储策略**：图数据存 Neo4j（节点/边），向量数据委托外部 `VecDB`（如 Qdrant），写入时同步双写。

> 来源：[DeepWiki 8.2-neo4j-backend]

### 9.6 Milvus 混合搜索

`MilvusVecDB`（`milvus.py:13-203`）支持多功能 schema：

- **Dense Search**：`FLAT` 或 `HNSW` 索引于 `vector` 字段
- **Sparse Search**：`SPARSE_INVERTED_INDEX` 索引于 `sparse_vector` 字段，内置 `BM25` 函数计算
- **Hybrid Search**：`RRFRanker`（倒数排名融合）或 `WeightedRanker` 合并结果

> 来源：[DeepWiki 8.4-vector-search-implementation] milvus.py L35-81, L198-200

### 9.7 数据规范化与批处理

**Neo4j 元数据处理**：
- `_prepare_node_metadata`：确保 `created_at`/`updated_at` ISO 8601 格式
- `_flatten_info_fields`：将 `info` 字典嵌套键展平到顶层元数据
- `_sanitize_neo4j_value`：字典/列表转 JSON 字符串（Neo4j 属性不支持嵌套结构）

**批处理**：
- `Neo4jCommunityGraphDB.add_nodes_batch`：单次 `UNWIND` 查询批量插入 + 同步更新向量库
- `PolarDBGraphDB`：专用批处理逻辑构建返回列与解码值

> 来源：[DeepWiki 8.2-neo4j-backend] [DeepWiki 4.4-storage-layer]

---

## 10. TreeTextMemory 数据结构

### 10.1 架构概览

`TreeTextMemory`（`tree.py:39-42`）是 MemOS 中文本记忆的层级图谱实现，将记忆组织为图数据库中的节点，通过父子关系构建多级树结构，同时支持语义相似度搜索和结构遍历。

| 类 | 文件 | 职责 |
|-----|------|------|
| `TreeTextMemory` | tree.py:39-40 | 主控制器，编排记忆操作 |
| `MemoryManager` | organize/manager.py:54-55 | 记忆添加（批量/并行）+ 初始组织 |
| `GraphStructureReorganizer` | organize/reorganizer.py:81-82 | 周期性聚类与层级构建（消费者循环） |
| `Searcher` | retrieve/searcher.py:46-47 | 基础搜索类，混合检索 |
| `AdvancedSearcher` | retrieve/advanced_searcher.py:12-13 | 扩展搜索器，多阶段推理 |
| `GraphMemoryRetriever` | retrieve/recall.py:59-60 | 统一检索器（图+向量+全文） |

> 来源：[DeepWiki 6.5-tree-text-memory]

### 10.2 层级组织机制

`TreeTextMemory` 通过父子边构建层级关系：父节点摘要语义相关的子节点簇，形成多级树。

**组织 Pipeline**：
```
新记忆到达
  → MemoryManager.add_memory / _add_memories_batch
  → 初始组织（分配 memory_type, 构建 working_binding）
  → GraphStructureReorganizer (周期性消费者循环)
    → 聚类语义相关节点
    → 构建父节点摘要
    → 重建层级结构
  → 清理临时 WorkingMemory 节点（通过 working_binding 标签链接）
```

> 来源：[DeepWiki 6.5-tree-text-memory] manager.py L138-197

### 10.3 记忆演化与归档

```python
# src/memos/memories/textual/item.py
class ArchivedTextualMemory:  # L49-92
    # 当记忆因冲突或重复被更新时，前一版本保存在节点历史的 ArchivedTextualMemory 中
```

记忆非静态：更新时旧版本归档到 `ArchivedTextualMemory`，支持反馈驱动的检索与渐进精炼。

> 来源：[DeepWiki 3-core-concepts] item.py L49-92

### 10.4 PreferenceMemory 专门提取

```python
# src/memos/memories/textual/prefer_text_memory/extractor.py
class NaiveExtractor:  # L12-16
    # 使用 NAIVE_EXPLICIT_PREFERENCE_EXTRACT_PROMPT 提取 explicit_preference
    # 使用 NAIVE_IMPLICIT_PREFERENCE_EXTRACT_PROMPT 提取 implicit_preference
    # 存储为 PreferenceTextualMemoryMetadata (L138-140)
```

> 来源：[DeepWiki 3-core-concepts] extractor.py L64-116

### 10.5 Dream 系统（记忆固化）

MemOS 包含记忆固化机制（"Dream"系统），可通过插件扩展（如 `CommunityDreamPlugin`，通过 entry points 注册）。Dream 系统处理长期记忆维护与优化。

**Hook 常量**：

| Hook | 用途 |
|------|------|
| `H.ADD_BEFORE` | 记忆添加到存储前触发 |
| `H.SEARCH_AFTER` | 记忆检索后后处理触发 |
| `H.DREAM_EXECUTE` | 执行记忆固化 Pipeline 触发 |

> 来源：[DeepWiki 3-core-concepts] pyproject.toml L65-66

---

## 11. MemScheduler 异步调度系统

### 11.1 架构概览

`GeneralScheduler`（`general_scheduler.py:16-17`）继承 `BaseScheduler`，管理异步任务执行，具备优先级路由、并行分发和分布式队列处理能力。

```
MOSCore 提交任务 (ADD_TASK_LABEL / QUERY_TASK_LABEL / ...)
  → ScheduleTaskQueue (facade)
    ├── SchedulerRedisQueue (生产: Redis Streams, 分布式)
    │   └── Stream Key: {prefix}:{user_id}:{mem_cube_id}:{task_label}
    └── SchedulerLocalQueue (开发: 内存队列)
  → SchedulerDispatcher (ContextThreadPoolExecutor)
    → _create_task_wrapper (包装 handler 调用)
    → set_request_context (传播 trace_id + user_context)
    → TaskStatusTracker (更新任务状态: waiting → in_progress → completed/failed)
    → metrics.observe_task_wait_duration (记录队列等待时长)
```

> 来源：[DeepWiki 4.6-memory-scheduling-system]

### 11.2 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| `GeneralScheduler` | general_scheduler.py:16-17 | 主实现，注册任务标签到 handler 的分发映射 |
| `ScheduleTaskQueue` | task_queue.py:24-49 | 队列 facade，抽象底层实现 |
| `SchedulerRedisQueue` | redis_queue.py:34-44 | Redis Streams 生产实现 |
| `SchedulerLocalQueue` | local_queue.py:25-30 | 内存队列开发实现 |
| `SchedulerDispatcher` | dispatcher.py:81-83 | 执行引擎，管理 `ContextThreadPoolExecutor` |
| `TaskStatusTracker` | status_tracker.py | Redis 追踪任务状态 |

### 11.3 Redis Streams 策略

当 `use_redis_queue` 启用时（`DEFAULT_USE_REDIS_QUEUE`）：

- **Stream Key 模式**：`{prefix}:{user_id}:{mem_cube_id}:{task_label}`（逻辑分区）
- **连接管理**：自动初始化 Redis 连接，检查 `xautoclaim` 特性
- **任务补充**：内部 `_refill_thread` 异步从 Redis 拉取消息包维持本地缓存
- **编排**：集成 `SchedulerOrchestrator` 管理任务依赖与流程

> 来源：[DeepWiki 4.6-memory-scheduling-system] redis_queue.py L38-132

### 11.4 OptimizedScheduler

`OptimizedScheduler`（`optimized_scheduler.py:37-38`）扩展 `GeneralScheduler`，为 API 驱动的记忆操作提供专用逻辑：

- **混合搜索**："fast search + async fine search" 模式——快速返回初始结果，后台任务处理深度推理
- **历史管理**：`history_memory_turns` 将前序对话上下文纳入记忆检索
- **异步任务**：专门处理 `API_MIX_SEARCH_TASK_LABEL` 用于后台记忆增强

> 来源：[DeepWiki 4.6-memory-scheduling-system] optimized_scheduler.py L37-123

---

## 12. 插件生态：OpenClaw + Reflect2Evolve

### 12.1 双插件体系

MemOS 仓库包含两个 TypeScript 插件应用：

| 插件 | 路径 | 定位 | 存储 |
|------|------|------|------|
| `memos-local-openclaw` | apps/memos-local-openclaw/ | OpenClaw 生态全写本地记忆实现 | SQLite（better-sqlite3） |
| `memos-local-plugin` | apps/memos-local-plugin/ | Reflect2Evolve 高性能本地记忆引擎（L1/L2/L3） | SQLite |

> 来源：[DeepWiki 13.1-memos-local-openclaw-architecture] [DeepWiki 14-memos-local-plugin-(reflect2evolve)]

### 12.2 memos-local-openclaw 架构

**摄入 Pipeline**：
```
原始对话轮
  → captureMessages (过滤系统样板/心跳/工具结果, 剥离 thinking 标签)
  → IngestWorker (后台处理队列)
  → Summarizer (优先链: Strong Config → Plugin Config → OpenClaw Fallback)
  → 去重 (findActiveChunkByHash 精确匹配 + findTopSimilar 语义重复)
  → Embedder (向量生成)
  → SQLite 存储
```

**SQLite Schema**：

| 表 | 用途 | 关键列 |
|----|------|--------|
| `chunks` | 记忆段主文本与元数据 | `id`, `content`, `summary`, `session_key`, `dedup_status` |
| `chunks_fts` | FTS5 虚拟表（trigram 分词） | `summary`, `content` |
| `embeddings` | 向量表示（BLOB 存储） | `chunk_id`, `vector`, `dimensions`, `provider`, `model` |
| `tasks` | 高级对话目标与摘要 | `id`, `title`, `status`, `started_at` |
| `hub_memories` | 团队 Hub 同步记忆 | `id`, `content`, `source_agent`, `original_owner` |

**性能优化**：
- WAL 模式（`PRAGMA journal_mode = WAL`）允许并发读写
- Trigram 分词器支持部分匹配和非英文
- SQLite 触发器自动同步 FTS 索引

> 来源：[DeepWiki 13.1-memos-local-openclaw-architecture] sqlite.ts L14-172

### 12.3 RecallEngine（混合检索）

`RecallEngine`（`engine.ts:31-170`）实现平衡相关性、多样性和新近性的检索策略：

| 阶段 | 方法 | 描述 |
|------|------|------|
| 候选收集 | FTS Search + Vector Search + Pattern Search | Trigram 关键词 + 余弦相似度 + LIKE 兜底 |
| 融合 | `rrfFuse` | RRF（倒数排名融合）合并不同方法排名 |
| 重排 | `mmrRerank` | MMR 惩罚过于相似的候选 |
| 新近衰减 | `applyRecencyDecay` | 时间衰减函数（半衰期）偏好新记忆 |

> 来源：[DeepWiki 13.1-memos-local-openclaw-architecture] engine.ts L31-170

### 12.4 Hub 团队共享

`HubServer`（`server.ts:27-48`）作为团队中心协调器：
- **Hub 角色**：管理用户（`HubUserManager`）、存储共享记忆
- **Client 角色**：通过 `connectToHub` 发布本地记忆或拉取团队技能
- **身份认证**：`identityKey` 标识用户，`hub-auth.json` 管理 token

> 来源：[DeepWiki 13.1-memos-local-openclaw-architecture] server.ts L178-194

### 12.5 Reflect2Evolve 插件架构

**核心组件**：

| 组件 | 文件 | 职责 |
|------|------|------|
| `MemoryCore` | core/pipeline/memory-core.ts:1-24 | 主接口 facade，封装 PipelineHandle |
| `Orchestrator` | core/pipeline/orchestrator.ts:4-27 | 内部引擎，管理会话/episode 生命周期与事件总线 |
| SQLite Storage | memory-core.ts:80-87 | `TraceRow`、`SkillRow`、`EpisodeRow` 持久化 |

**适配器集成**：

| 适配器 | 集成方式 | 运行时数据路径 |
|--------|----------|----------------|
| **OpenClaw** | 直接 TypeScript 插件 | `~/.openclaw/memos-plugin/` |
| **Hermes** | Python JSON-RPC 桥 | `~/.hermes/memos-plugin/` |

JSON-RPC 桥（`bridge.cts` 守护进程）将 `MemoryCore` 接口映射为 RPC 方法，允许远程 Agent 管理会话与轮次。

> 来源：[DeepWiki 14-memos-local-plugin-(reflect2evolve)]

### 12.6 LLM 客户端与断路器

`LlmClient`（TypeScript）管理主提供商调用与回退：

- **断路器**（`LlmCircuitBreakerConfig`）：终端错误（401 Unauthorized、余额不足）时跳闸，防止重复失败请求
- **主机回退**：主提供商（如 OpenAI）失败时回退到主机提供的 LLM 桥
- **输出韧性**：`malformedRetries` 预算（默认 1）用于 `completeJson` 调用，LLM 返回无效 JSON 时自动重试

> 来源：[DeepWiki 5.4-client-integration] client.ts L50-190

---

## 13. L1/L2/L3 记忆架构与技能结晶化

### 13.1 三层层级模型

Reflect2Evolve 算法将记忆组织为三个抽象层级，由 `MemoryCore` Pipeline 管理：

| 层级 | 名称 | 数据实体 | 内容 | 持久化逻辑 |
|------|------|----------|------|------------|
| **L1** | Trace（轨迹） | `TraceRow` | 步级 (s, a, o, ρ, r) 记录 | 从 `EpisodeSnapshot` 经 `step-extractor.ts` 提取 |
| **L2** | Policy（策略） | `PolicyRow` | 战术策略（"当 X 时，做 Y"） | 从 `l2_candidate_pool` 簇经 `runL2` 诱导 |
| **L3** | World Model（世界模型） | `WorldModelRow` | 压缩域约束 | 从多个活跃策略经 `runL3` 抽象 |

> 来源：[DeepWiki 14.1-l1l2l3-memory-architecture]

### 13.2 L1：接地轨迹

L1 记忆是原子构建块，每条轨迹代表单一决策点（工具调用或最终文本响应）。

**五元组结构**（`step-extractor.ts:27-29`）：
- $s$（State）：状态
- $a$（Action）：动作
- $o$（Observation）：观察
- $\rho$（Reflection）：反思
- $r$（Value）：价值

**捕获模式**：
- `runLite`：逐轮提取
- `runReflect`：话题结束合成

> 来源：[DeepWiki 14.1-l1l2l3-memory-architecture] step-extractor.ts L7-32

### 13.3 L2：战术策略

L2 策略在系统检测到成功模式重复出现时诱导生成。

**诱导流程**（`l2.ts:5-13`）：
1. 入站高价值轨迹与现有策略通过向量签名余弦相似度比较
2. 未匹配轨迹进入 `l2_candidate_pool`
3. 桶达到 `minEpisodesForInduction` 阈值时，LLM 诱导新策略草案

### 13.4 L3：世界模型

L3 代表 Agent 的"智慧"，聚类相关 L2 策略形成对环境动态或用户偏好的更广泛理解。

- **抽象**：从多个活跃策略经 `runL3` 抽象

### 13.5 MemoryCore Pipeline 数据流

```
适配器原始消息
  → MemoryCore (facade)
    → Orchestrator (事件总线 + 订阅者)
      → extractSteps (capture.ts:135-147, 会话→StepCandidate)
      → batchScoreReflections (batch-scorer.ts:1-17, 单次 LLM 调用完成 episode 级反思合成 + α 评分)
      → runL2 (高价值轨迹→策略诱导)
      → runL3 (多策略→世界模型抽象)
      → 技能结晶化 (crystallize.ts:75-158)
```

> 来源：[DeepWiki 14.1-l1l2l3-memory-architecture] orchestrator.ts L4-27

### 13.6 MemoryCore 接口

```typescript
// agent-contract/memory-core.ts
class MemoryCore {
    onTurnStart(...): turnStartRetrieve(...)  // 检索 L1/L2/L3 上下文注入 LLM prompt
    onTurnEnd(...): runLite + 准备 runReflect   // 捕获结果 + 准备 episode
}
```

> 来源：[DeepWiki 14.1-l1l2l3-memory-architecture] memory-core.ts L161-165

### 13.7 多层检索策略

系统根据 Agent 当前状态采用不同检索入口：

| 触发器 | Tier 1 (Skill) | Tier 2 (Trace) | Tier 3 (World) | 用途 |
|--------|-----------------|-----------------|-----------------|------|
| `turn_start` | 是 | 是 | 是 | 完整上下文注入 |
| `tool_driven` | 否 | 是 | 是 | 即时工具指导 |
| `skill_invoke` | 主 | 是 | 否 | 特定技能引导 |
| `sub_agent` | 否 | 是 | 是 | 子 Agent 上下文 |
| `decision_repair` | 是 | 是 | 否 | 解除失败循环 |

> 来源：[DeepWiki 14.1-l1l2l3-memory-architecture] retrieve.ts L1-182

### 13.8 技能结晶化机制

技能结晶化是将 L2 策略和 L1 证据打包为正式可执行 `Skill` 的过程。

**结晶化流程**（`crystallize.ts:75-158`）：

1. **起草**：`crystallizeDraft` 接收 `PolicyRow` + 支持 `TraceRow` 证据
2. **LLM 生成**：`SKILL_CRYSTALLIZE_PROMPT` 引导 LLM 生成结构化技能定义（参数、步骤、示例）
3. **语言导向**：检测证据主导语言，引导 LLM 以同语言输出人类面向字段（title/steps/examples）
4. **规范化**：sanitize 文本，确保 `steps` 和 `examples` 结构正确
5. **拒检检测**：显式检测模型拒绝或安全触发，避免将"我无法满足此请求"持久化为技能

**SkillDTO 结构**（`dto.ts:246-270`）：

```typescript
interface SkillDTO {
    skillId: string
    title: string           // 人类面向标题
    description: string     // 技能描述
    parameters: Param[]     // 参数定义
    steps: Step[]           // 执行步骤
    examples: Example[]     // 使用示例
    evidence: TraceRef[]    // L1 证据引用
    sourcePolicy: PolicyRef // 源 L2 策略引用
}
```

> 来源：[DeepWiki 14.2-retrieval-and-skill-crystallization] crystallize.ts L75-158

### 13.9 LLM 相关性过滤

机械检索（向量/FTS）常有噪声，系统采用 LLM 精度过滤：

- **实现**：`llmFilterCandidates` 发送查询 + 编号候选列表给 LLM
- **Prompt**：`RETRIEVAL_FILTER_PROMPT` 指示模型按有用性排名，剔除"脚手架闲聊"和表面关键词匹配
- **充分性检查**：LLM 报告 `sufficient` 布尔值，指示保留候选是否足够回答查询
- **安全截断**：LLM 调用失败时回退到基于相关性分数的机械"安全截断"
- **救援路径**：LLM 过滤返回空集但结果非空时，"救援"顶部信息候选避免空注入

> 来源：[DeepWiki 14.2-retrieval-and-skill-crystallization] llm-filter.ts L113-234

### 13.10 决策指导与注入

- **决策指导**：`decisionGuidance` 存储结构化偏好与反模式，渲染为注入包的专用段落
- **抑制冗余**：若 Tier-1 Skill 已覆盖，抑制 Tier-2 经验（除非经验比技能更新）
- **安全分隔符**：注入记忆用不可信上下文通知包裹（Markdown 标题 + XML 标签）防止历史数据的 prompt 注入

> 来源：[DeepWiki 14.2-retrieval-and-skill-crystallization] injector.ts L38-260

---

## 14. 评估框架

### 14.1 评估 Pipeline 架构

评估框架是综合基准测试套件，支持多个行业标准数据集，提供统一接口将 MemOS 与其他记忆框架（`mem0`、`zep`、`memobase`、`memu`、`supermemory`）对比。

**四阶段流程**：
```
原始数据集
  → Ingestion (摄入历史对话到记忆系统)
  → Search (记忆增强检索)
  → Response Generation (基于检索上下文生成 LLM 回答)
  → Metric Calculation (NLP 指标 + LLM-as-a-Judge 评分)
```

> 来源：[DeepWiki 15-evaluation-framework] [DeepWiki 15.1-evaluation-benchmarks]

### 14.2 支持的基准

| 基准 | 关注领域 | 主要指标 |
|------|----------|----------|
| **LoCoMo** | 长上下文对话记忆（35+ 会话） | BLEU、ROUGE、METEOR、BERTScore、LLM-as-a-Judge |
| **LongMemEval** | 跨会话特定事实检索 | F1、METEOR、BERTScore、语义相似度 |
| **PrefEval** | 用户偏好提取与保留 | 检索精度、响应一致性 |
| **PersonaMem** | 一致性人格属性回忆 | 多选准确率（a/b/c/d） |
| **Long_Bench-v2** | 极端长上下文理解 | 知识检索准确率（A/B/C/D） |

> 来源：[DeepWiki 15.1-evaluation-benchmarks]

### 14.3 OmniMemEval 综合评测

通过 OmniMemEval 评测 14 个商业记忆产品跨 10 个数据集（来源：`05_apps_crosscutting.md` 第 4.4 节）：

| 基准 | MemOS 得分 |
|------|-----------|
| LoCoMo | 88.83 |
| LongMemEval | 89.20 |
| PersonaMem v2 | 40.58 |
| HaluMem | 80.91 |
| BEAM-10M | 56.75 |
| GDPVal | 62.07 |
| LiveCodeBench | 64.96 |
| OmniMath | 61.00 |
| SWE-Bench | 38.46 |
| BrowseComp-Plus | 23.85 |

**关键成果**：MemOS 使 OpenClaw 在 5 个 Agent 任务上平均完成率从 36.63% 提升至 50.87%；实现 **35.24% token 节省**。

### 14.4 统一客户端接口

```python
# evaluation/scripts/utils/client.py
class MemosApiClient:  # L145-197
    def add(self, user_id, messages, mem_cube_id, conversation_id): ...  # /product/add
    def search(self, query, user_id, ...): ...  # /product/search, 默认 fast 模式

# 外部基线客户端
class ZepClient: ...       # L19-48
class Mem0Client: ...      # L51-92
class MemobaseClient: ...  # L95-142
```

### 14.5 评估指标实现

| 指标 | 实现实体 | 用途 |
|------|----------|------|
| ROUGE | `calculate_rouge_scores` | n-gram 重叠（1/2/L） |
| BLEU | `calculate_bleu_scores` | n-gram 精度（带平滑） |
| METEOR | `calculate_meteor_score` | 对齐翻译质量 |
| 语义相似度 | `calculate_semantic_similarity` | `SentenceTransformer`（Qwen3-Embedding-0.6B）+ 余弦距离 |
| LLM-as-a-Judge | `locomo_grader` | `gpt-4o-mini` 验证事实正确性（CORRECT/WRONG） |

> 来源：[DeepWiki 15.1-evaluation-benchmarks] locomo_eval.py L74-174

### 14.6 PrefEval 噪声注入测试

PrefEval 可注入 10 或 300 条无关对话轮（`irre_10`、`irre_300`），压力测试记忆的噪声过滤能力。

> 来源：[DeepWiki 15.1-evaluation-benchmarks] pref_memos.py L44-47

---

## 15. 对 SRS 项目的深度应用价值

> 本节分析 MemOS 如何用于 SRS 一致性检测项目（详见 `AGENTS.md`），以及与 DataMind 的互补关系。

### 15.1 SRS 一致性检测的跨会话记忆需求

SRS 一致性检测项目当前面临的核心痛点之一是**检测经验的不可积累性**：每次检测会话独立运行，假阳性模式、规则适用经验、文档特异性无法跨会话保留。MemOS 的记忆管理能力可直接解决此问题。

**当前痛点映射**：

| SRS 痛点 | MemOS 能力 | 对应机制 |
|----------|-----------|----------|
| 假阳性模式无法积累 | 检测结果反馈驱动记忆精炼 | `MemFeedback` + `add_before_search` 冲突检测 |
| 规则适用经验丢失 | 跨会话长期记忆持久化 | `TreeTextMemory` + `LongTermMemory` 作用域 |
| 文档特异性未知 | 用户/文档画像记忆 | `UserMemory` + `PreferenceMemory` |
| 检测策略无演化 | 轨迹→策略→世界模型层级积累 | Reflect2Evolve L1/L2/L3 架构 |

### 15.2 L1/L2/L3 记忆架构在一致性检测中的应用

Reflect2Evolve 的三层架构可直接映射到 SRS 一致性检测的经验积累：

#### L1 traces（轨迹记忆）→ 检测轨迹

**映射**：每次一致性检测的执行轨迹（输入文档→检测规则→检测结果→人工判定）作为 L1 trace。

```python
# 概念映射
L1_trace = {
    "state": "SRS文档: battery_srs, 章节: 3.2 约束提取",
    "action": "应用规则: same_value_check(文本vs表格)",
    "observation": "检测到3处不一致, 2处假阳性",
    "reflection": "假阳性源于数值精度差异(0.1 vs 0.10)",
    "value": 0.8  # 检测有效率
}
```

**具体应用**：`srs_consistency_checker_v2.py` 的每次检测结果（同值/文本-表格/逻辑三层）记录为 L1 trace，包含：
- 检测的文档 ID 与章节
- 触发的检测规则（Z3 求解器约束）
- 检测结果（真阳性/假阳性）
- 假阳性根因分析

#### L2 policies（策略记忆）→ 检测策略

**映射**：从多个 L1 检测轨迹中诱导出"当遇到 X 类型文档时，采用 Y 检测策略"。

**潜在策略示例**：
- "当 SRS 文档含 GJB 438C 格式表格时，文本-表格一致性检查应忽略数值精度差异"
- "当约束涉及时间约束时，Z3 求解前应先进行时态规范化"
- "当文档来自 buaa 来源时，章节编号可能不连续，跨章节逻辑检查需放宽"

**诱导机制**：`runL2` 从 `l2_candidate_pool` 中聚类相似检测场景，当达到 `minEpisodesForInduction` 阈值时 LLM 诱导新策略。

#### L3 world models（世界模型记忆）→ 领域知识

**映射**：从多个 L2 检测策略抽象出 SRS 一致性检测的领域规律。

**潜在世界模型示例**：
- "GJB 438C SRS 文档的约束类型分布: 时序约束 30% / 数值约束 25% / 结构约束 20% / 语义约束 25%"
- "SRS 一致性假阳性的三大根因: 数值精度(40%) / 同义异表(30%) / 上下文依赖(30%)"
- "不同来源 SRS 的检测难度排序: buaa > ieee830 > nasa"

**抽象机制**：`runL3` 从多个活跃 L2 策略抽象领域约束。

### 15.3 技能结晶化在一致性检测中的应用

Reflect2Evolve 的技能结晶化机制可将高频检测模式打包为可复用技能：

**潜在结晶化技能**：

| 技能 | 来源 L2 策略 | 参数 | 步骤 |
|------|-------------|------|------|
| `gjb_table_consistency_check` | "GJB 表格一致性检查策略" | 文档路径、章节范围 | 1.提取表格 2.提取文本约束 3.对齐 4.精度容差过滤 |
| `z3_temporal_constraint_solve` | "时序约束 Z3 求解策略" | 约束列表、时间范围 | 1.时态规范化 2.Z3 编码 3.求解 4.反例生成 |
| `false_positive_filter` | "假阳性过滤策略" | 检测结果、文档元数据 | 1.精度差异检测 2.同义异表检测 3.上下文依赖检测 |

**结晶化流程**：
1. `crystallizeDraft`：从高价值 L2 检测策略 + L1 证据起草
2. `SKILL_CRYSTALLIZE_PROMPT`：LLM 生成结构化检测技能定义
3. 语言导向：检测 SRS 文档语言（中文/英文），以同语言输出技能描述
4. 规范化：确保检测步骤与示例结构正确
5. 持久化为 `SkillDTO`，可供后续检测会话直接调用

### 15.4 与现有 SRS 工具链的集成路径

#### 路径 A：MemOS 作为检测经验记忆后端

```
srs_consistency_checker_v2.py (检测)
  → 检测结果 + 人工反馈
    → MemOS.add_memory (L1 trace 摄入)
      → MemScheduler 异步处理
        → TreeTextMemory 存储 (WorkingMemory → LongTermMemory)

下次检测前
  → MemOS.search_memory (检索相关检测经验)
    → Searcher 混合检索 (向量 + 图谱 + BM25)
      → 返回相关 L1 traces + L2 policies
        → 注入检测 prompt 上下文
```

#### 路径 B：Reflect2Evolve 插件作为检测策略演化引擎

```
多次检测会话 (L1 traces 积累)
  → runL2 (检测策略诱导)
    → runL3 (领域知识抽象)
      → crystallize (检测技能结晶化)
        → SkillDTO 持久化
          → 后续检测会话直接调用结晶化技能
```

#### 路径 C：MCP Server 集成

通过 `MOSMCPServer` 将 SRS 检测能力暴露为 MCP 工具：
- `detect_consistency`：调用 `srs_consistency_checker_v2.py` 检测
- `search_detection_experience`：检索历史检测经验
- `add_detection_result`：记录新检测结果

### 15.5 具体实现建议

1. **短期（PoC）**：使用 `MOS.simple()` 本地部署，将 `srs_consistency_checker_v2.py` 的检测结果作为 `TextualMemoryItem` 摄入，`memory_type` 设为 `LongTermMemory`，在下次检测前用 `search_memory` 检索相关经验

2. **中期**：引入 Reflect2Evolve 插件架构，将检测轨迹结构化为 L1 traces，配置 `minEpisodesForInduction` 触发 L2 策略诱导

3. **长期**：构建 SRS 一致性检测专用 MemCube，隔离检测经验；通过 `CompositeCubeView` 跨 Cube 检索（如同时检索 GJB 规则库 Cube + 检测经验 Cube）

### 15.6 与 DataMind 的互补关系

> 参考 `05_apps_crosscutting.md` 第 4.6 节

| 维度 | DataMind | MemOS |
|------|----------|-------|
| **定位** | 生态内轻量级知识中枢 | 独立生产级大模型记忆 OS |
| **记忆类型** | 六知识面融合（静态知识检索） | 动态记忆生命周期管理（存储/检索/演化） |
| **记忆持久性** | 会话级知识检索 | 跨会话持久记忆 + 演化 |
| **自演化** | 无 | L1→L2→L3→技能结晶化 |
| **图谱化** | 无（向量检索为主） | TreeTextMemory 图谱化可编辑 |
| **多模态** | 有限 | 原生文本/图像/工具轨迹/人格 |
| **生产级** | 开发用 | 异步调度 + 多租户 + Redis Streams |

**SRS 项目中的互补定位**：
- **DataMind**：负责 SRS 相关知识的即时检索（GJB 规则、文献、Gold Standard）——"知道什么"
- **MemOS**：负责一致性检测经验的跨会话积累与演化——"学到什么"

两者在 SRS 项目中可形成"知识检索（DataMind）+ 经验积累（MemOS）"的双层智能增强架构。

### 15.7 关键风险与注意事项

1. **LLM 成本**：MemOS 的 Fine 模式和 Reflect2Evolve 的 L2/L3 诱导均依赖大量 LLM 调用，需评估 API 成本
2. **基础设施**：生产部署需 Neo4j + Qdrant + Redis，增加运维复杂度；PoC 阶段建议用 Neo4j Community + 本地模式
3. **中文支持**：MemOS 的 Prompt 模板有中英双语版本（`SIMPLE_STRUCT_MEM_READER_PROMPT_ZH`），但 Reflect2Evolve 插件的语言检测可能需适配 SRS 文档特性
4. **与 Z3 求解器的集成**：当前 MemOS 无约束求解能力，Z3 检测逻辑需保留在 `srs_consistency_checker_v2.py` 中，MemOS 仅负责经验记忆

---

## 附录：DeepWiki 页面索引

| 页面 | URL | 核心内容 |
|------|-----|----------|
| 1-overview | /1-overview | OS 隐喻映射、MOS 类层次、Memory Cube 架构 |
| 1.1-project-structure | /1.1-project-structure | 仓库布局、包导出、可选依赖 |
| 3-core-concepts | /3-core-concepts | 记忆类型层次、MemCube、MOS、多租户 |
| 3.2-memory-cubes | /3.2-memory-cubes | Multi-Cube View、隔离、摄入 Pipeline |
| 3.3-mos-architecture | /3.3-mos-architecture | MOSCore/MOS/MOSProduct 类层次、CoT |
| 4.1-overall-architecture | /4.1-overall-architecture | 四层架构、请求流、组件汇总 |
| 4.2-api-layer | /4.2-api-layer-and-request-handling | API Pipeline、依赖注入、Pydantic 模型 |
| 4.3-memory-processing-pipeline | /4.3-memory-processing-pipeline | MemReader 层次、Fast/Fine、分块嵌入 |
| 4.4-storage-layer | /4.4-storage-layer | 图DB抽象、PolarDB/Neo4j、多租户 |
| 4.5-search-and-retrieval | /4.5-search-and-retrieval-system | Searcher、GraphMemoryRetriever、去重重排 |
| 4.6-memory-scheduling | /4.6-memory-scheduling-system | GeneralScheduler、Redis Streams、Dispatcher |
| 5.1-rest-api-endpoints | /5.1-rest-api-endpoints | 端点列表、请求/响应模型、SSE |
| 5.4-client-integration | /5.4-client-integration | 四种集成方式、MemOSClient、断路器 |
| 5.5-mcp-server | /5.5-mcp-server | MOSMCPServer、MCP 工具、配置加载 |
| 6.1-memory-extraction | /6.1-memory-extraction-and-reading | Reader 层次、Fast/Fine、多模态解析 |
| 6.2-multi-modal | /6.2-multi-modal-content-processing | Parser 路由、文件/图像/系统解析 |
| 6.3-memory-search | /6.3-memory-search-and-retrieval | 搜索模式、混合检索、重排序、过滤 |
| 6.4-quality-dedup | /6.4-memory-quality-and-deduplication | 三阶段质量控制、冲突检测、去重 |
| 6.5-tree-text-memory | /6.5-tree-text-memory | TreeTextMemory、MemoryManager、层级组织 |
| 8.1-graph-database | /8.1-graph-database-architecture | BaseGraphDB、GraphStoreFactory、多租户 |
| 8.2-neo4j-backend | /8.2-neo4j-backend | Enterprise vs Community、向量搜索策略 |
| 8.4-vector-search | /8.4-vector-search-implementation | Milvus 混合搜索、Qdrant HNSW |
| 13.1-openclaw | /13.1-memos-local-openclaw-architecture | SQLite 存储、RecallEngine、Hub 共享 |
| 14-reflect2evolve | /14-memos-local-plugin-(reflect2evolve) | MemoryCore、Orchestrator、适配器 |
| 14.1-l1l2l3 | /14.1-l1l2l3-memory-architecture | L1/L2/L3 层级、Pipeline、检索策略 |
| 14.2-crystallization | /14.2-retrieval-and-skill-crystallization | 多层检索、LLM 过滤、技能结晶化 |
| 15-evaluation | /15-evaluation-framework | 评估 Pipeline、统一客户端、LLM-as-a-Judge |
| 15.1-benchmarks | /15.1-evaluation-benchmarks | LoCoMo/LongMemEval/PrefEval/PersonaMem |

---

> **文档版本**：v1.0（2026-07-30）
> **数据截止**：DeepWiki last indexed 2026-07-25（commit e8204062）
> **源码引用**：所有源码位置标注格式 `文件路径:行号`，对应 GitHub commit e8204062
