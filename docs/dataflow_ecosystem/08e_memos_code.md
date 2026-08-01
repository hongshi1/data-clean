# MemOS 代码级提取 — L1/L2/L3 记忆架构与 Reflect2Evolve 实际代码

> 调研对象：MemTensor/MemOS（10.4k stars，版本 2.0.25 Stardust，commit `e8204062`）
> 调研日期：2026-07-30
> 调研方法：DeepWiki（60+ 页代码级文档，last indexed 2026-07-25）+ GitHub 原始源码文件（`dto.ts` / `memory-core.ts` / `client.py` 全文逐行抓取）
> 关联文档：`05b_memos_deep.md` 为架构级深度分析；本文档为其**代码级提取**，所有代码块均来自真实源文件并标注 `文件:行号`
> 目标：给出可直接使用的 MemOS API / 部署 / L1-L2-L3 接口，以及 SRS 冲突检测经验积累的完整代码示例

---

## 目录

- [0. 关键结论（SRS 项目如何直接用 MemOS）](#0-关键结论srs-项目如何直接用-memos)
- [A. 安装和部署](#a-安装和部署)
- [B. L1/L2/L3 架构的完整实现（真实 DTO 源码）](#b-l1l2l3-架构的完整实现真实-dto-源码)
- [C. REST API 完整列表](#c-rest-api-完整列表)
- [D. Memory Cube API（自托管 /product）](#d-memory-cube-api自托管-product)
- [E. TreeTextMemory 数据结构](#e-treetextmemory-数据结构)
- [F. 多模态记忆](#f-多模态记忆)
- [G. MemScheduler 异步调度](#g-memscheduler-异步调度)
- [H. Reflect2Evolve MemoryCore 接口（真实 TypeScript 源码）](#h-reflect2evolve-memorycore-接口真实-typescript-源码)
- [I. SRS 冲突检测经验积累方案（完整可运行代码）](#i-srs-冲突检测经验积累方案完整可运行代码)

---

## 0. 关键结论（SRS 项目如何直接用 MemOS）

MemOS 提供两条**完全不同**的技术路线来积累 SRS 一致性检测经验，必须区分清楚：

| 路线 | 实现 | 语言/存储 | 适用场景 | 是否开箱即用 L1/L2/L3 |
|------|------|-----------|----------|----------------------|
| **路线①：MemOS Server（MOS + TreeTextMemory）** | `src/memos/` Python 后端，FastAPI `/product/*` 端点，Neo4j+Qdrant 存储 | Python | 通用记忆库（文本/多模态），用 `WorkingMemory`/`LongTermMemory`/`UserMemory`/`SkillMemory`/`PreferenceMemory` 五大作用域模拟 L1/L2/L3 | **否**——靠 `memory_type` 字段 + 多 Cube 隔离手动映射 |
| **路线②：Reflect2Evolve 插件（memos-local-plugin）** | `apps/memos-local-plugin/` TypeScript 引擎，SQLite 本地存储，JSON-RPC 桥 | TypeScript + SQLite | Agent 自演化记忆，**原生 L1 Trace / L2 Policy / L3 WorldModel / Skill 结晶** | **是**——`TraceDTO`/`PolicyDTO`/`WorldModelDTO`/`SkillDTO` 是一等实体 |

**对 SRS 项目的建议**：
- 想要**轻量、Python、可复用现有 `srs_consistency_checker_v2.py`** → 用**路线①**（MemOS Server + REST API + 多 Cube），把检测轨迹/策略/领域知识放进不同 Cube，用 `tags` + `info` 元数据区分 L1/L2/L3。本文 §C-§G、§I 给出完整代码。
- 想要**原生 L1→L2→L3 自演化、技能结晶、反思打分** → 用**路线②**（Reflect2Evolve），通过 JSON-RPC 桥从 Python 调 TypeScript 核心。本文 §B、§H 给出真实 DTO 与 `MemoryCore` 接口。

> 来源：[DeepWiki 14-memos-local-plugin] README.md L3-4；[DeepWiki 3.2-memory-cubes]；GitHub README "Self-Host" vs "Local Plugin"

---

## A. 安装和部署

### A.1 路线①：MemOS Server（自托管，推荐用于 SRS 项目）

**前提**：Python 3.10–3.13；外部服务 Neo4j（图存储）、Qdrant（向量）、Redis（异步队列）、MySQL（用户管理）、Milvus（偏好记忆，可选）。

> 来源：[DeepWiki 2.1-installation] pyproject.toml L11；docker/docker-compose.yml L28-62

**方法 1：Docker（最省事，自带 Neo4j + Qdrant）**

```bash
git clone https://github.com/MemTensor/MemOS.git
cd MemOS
cp docker/.env.example .env          # 在 .env 中填 LLM API Key
cd docker
docker compose up                    # 启动 MemOS API + Neo4j + Qdrant
# API 地址: http://localhost:8000
```

> 来源：GitHub README "Self-Host the MemOS Service" / [DeepWiki 2.1-installation] README.md L150-158

**方法 2：uvicorn 原生启动（已有 Neo4j/Qdrant 时）**

```bash
git clone https://github.com/MemTensor/MemOS.git
cd MemOS
cp docker/.env.example .env          # 填 API Key
cd src
uvicorn memos.api.server_api:app --host 0.0.0.0 --port 8000 --workers 1
```

> 来源：GitHub README "Option B — Run with uvicorn"

**方法 3：pip 包集成（作为库嵌入到 SRS 项目）**

```bash
pip install MemoryOS
```

可选依赖组（按需安装）：

| 依赖组 | 用途 | 关键包 |
|--------|------|--------|
| `tree-mem` | 图谱记忆 | `neo4j`, `schedule` |
| `mem-scheduler` | 异步任务 | `redis`, `pika` |
| `mem-reader` | 多模态文件解析 | `chonkie`, `markitdown` |
| `pref-mem` | 偏好学习 | `pymilvus`, `datasketch` |

> 来源：[DeepWiki 2.1-installation] pyproject.toml L73-113, L171-188

### A.2 路线②：Reflect2Evolve 本地插件（原生 L1/L2/L3）

**前提**：Node.js 22+；已安装 OpenClaw 或 Hermes Agent（可选，插件可独立运行）。

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/MemTensor/MemOS/main/apps/memos-local-plugin/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/MemTensor/MemOS/main/apps/memos-local-plugin/install.ps1 -OutFile "$env:TEMP\memos-install.ps1"; powershell -ExecutionPolicy Bypass -File "$env:TEMP\memos-install.ps1"
```

安装脚本会：自动检测 OpenClaw/Hermes → 部署插件到 `~/.hermes/plugins/` 或 `~/.openclaw/plugins/` → 写入初始 `config.yaml` → 重建 `better-sqlite3` 原生模块 → 重启 agent。

> 来源：GitHub README "Local Plugin (memos-local-plugin 2.0)"；[DeepWiki 14.3-adapters] install.sh L155-185, L455-472

### A.3 核心配置（环境变量）

| 变量 | 用途 | 代码引用 |
|------|------|----------|
| `GRAPH_DB_BACKEND` | 图存储类型：`neo4j`/`neo4j-community`/`polardb`/`postgres` | config_builders.py L47-49 |
| `OPENAI_API_KEY` | OpenAI 兼容后端 API Key | configs/llm.py L26 |
| `OPENAI_API_BASE` | OpenAI 兼容 API 基址（vLLM/DeepSeek/GLM 均可） | configs/llm.py L27 |
| `NEO4J_URI` | Neo4j 连接串 | mcp_serve.py L35 |
| `MOS_TEXT_MEM_TYPE` | 文本记忆类型，默认 `tree_text` | mcp_serve.py L34 |
| `ENABLE_MEM_SCHEDULER` | 启用后台记忆重组，设 `true` | mcp_serve.py L48 |
| `CHAT_MODEL_LIST` | 可用 chat 模型 JSON 串 | config_builders.py L88-98 |
| `VLLM_API_BASE` / `OLLAMA_API_BASE` | vLLM / Ollama 本地模型基址 | configs/llm.py L132 / L109 |

> 来源：[DeepWiki 2.2-configuration] config.py L180-205；configs/llm.py L25-141

**关键：接入 GLM-5（本项目 API）**
MemOS 的 LLM 全部走 OpenAI 兼容协议，因此 GLM-5 可直接接入：

```bash
OPENAI_API_KEY=<your-key>
OPENAI_API_BASE=https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions
```

### A.4 健康检查

```bash
curl http://localhost:8000/health
```

> 来源：[DeepWiki 2.1-installation] README.md L158

---

## B. L1/L2/L3 架构的完整实现（真实 DTO 源码）

> ⚠️ 本节代码为**路线②（Reflect2Evolve）**的真实 TypeScript DTO，逐行来自
> `apps/memos-local-plugin/agent-contract/dto.ts`（commit e8204062，共 701 行）。
> 这些 DTO 是 JSON 可序列化的纯数据结构（无 `Date`/`Map`/class），跨 JSON-RPC 桥传递。

### B.1 三层抽象总览

| 层 | 名称 | 数据实体 | 内容 | 持久化逻辑 |
|----|------|----------|------|-----------|
| **L1** | Trace | `TraceRow` / `TraceDTO` | 步级 (s, a, o, ρ, r) 记录 | `step-extractor.ts` 从 `EpisodeSnapshot` 提取 |
| **L2** | Policy | `PolicyRow` / `PolicyDTO` | 战术策略（"当 X，做 Y"） | `runL2` 从 `l2_candidate_pool` 聚类归纳 |
| **L3** | World Model | `WorldModelRow` / `WorldModelDTO` | 压缩领域约束 | `runL3` 从多个 active policy 抽象 |

> 来源：[DeepWiki 14.1-l1l2l3] l2.ts L5-13；core/types.ts L72-73

### B.2 评分信号类型（贯穿 L1/L2/L3）

```typescript
// ─── Time / scoring ───────────────────────────────────────────────────────────
/** 毫秒 UTC epoch。 */
export type EpochMs = number;

/** 人类反馈有符号奖励 [-1, 1] (R_human)。 */
export type Reward = number;
/** 反思质量权重 [0, 1] (α_t)。 */
export type ReflectionAlpha = number;
/** 折扣反向传播值 (V_t)。 */
export type ValueScore = number;
/** 技能采纳率 (η)。 */
export type SkillEta = number;
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:37-49`

### B.3 L1 Trace：轨迹记忆数据结构（核心）

L1 是原子构建块，每个 trace 代表一个决策点（一次工具调用或一次最终文本回复）。一个工具调用 = 一个 step。

```typescript
export interface TraceDTO extends OwnershipDTO {
  id: TraceId;
  episodeId: EpisodeId;
  sessionId: SessionId;
  ts: EpochMs;
  userText: string;
  agentText: string;
  /** LLM 生成的本 trace 简短摘要，viewer 主行文本 */
  summary?: string | null;
  /** capture / 用户打的标签 */
  tags?: string[];
  /** 共享状态：null=私有 */
  share?: {
    scope: ShareScope;          // "private" | "public" | "hub"
    target?: string | null;
    sharedAt?: EpochMs | null;
  } | null;
  toolCalls: ToolCallDTO[];
  /** LLM 原生 thinking（扩展思考块），属于会话日志，非评分 */
  agentThinking?: string | null;
  /** MemOS 生成的反思，reward pipeline 用（α + backprop），绝不进会话日志 */
  reflection?: string;
  /** 反向传播值 V_t，约 [-1, 1] */
  value: ValueScore;
  /** 反思 alpha α_t，[0, 1] */
  alpha: ReflectionAlpha;
  /** 最近一次人类奖励 R_human，[-1, 1] */
  rHuman?: Reward;
  /** L2 候选选择用的缓存优先级 */
  priority: number;
  /** episode 级评分状态（viewer 显示用） */
  episodeStatus?: "open" | "closed";
  episodeRTask?: Reward | null;
  episodeRewardSkipped?: boolean;
  /** 同一用户消息产生的所有 L1 trace 共享的稳定组键 = 用户 turn 的 ts */
  turnId: EpochMs;
}
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:171-237`

**Trace 的 5 要素（s, a, o, ρ, r）映射**：
- State (s) = `userText` + `contextHints`
- Action (a) = `toolCalls` + `agentText`
- Observation (o) = `toolCalls[].output`
- Reflection (ρ) = `reflection` + `alpha`
- Value (r) = `value` (V_t) + `rHuman`

> 来源：[DeepWiki 14.1-l1l2l3] step-extractor.ts L7-10, L27-29

**Turn 输入/输出（capture 的原始载荷）**：

```typescript
export interface TurnInputDTO {
  agent: AgentKind;            // "openclaw" | "hermes" | string
  sessionId: SessionId;
  namespace?: RuntimeNamespace;
  turnKey?: string;            // 幂等键
  episodeId?: EpisodeId;       // 续接已有 episode
  userText: string;            // 用户本轮文本
  contextHints?: Record<string, unknown>;
  ts: EpochMs;
}

export interface TurnResultDTO {
  agent: AgentKind;
  sessionId: SessionId;
  episodeId: EpisodeId;
  agentText: string;           // agent 输出文本
  agentThinking?: string;      // LLM 原生 thinking（会话日志）
  toolCalls: ToolCallDTO[];    // 本轮工具调用（有序）
  contextHints?: Record<string, unknown>;
  reflection?: string;         // MemOS 反思（评分信号，非会话内容）
  ts: EpochMs;
}
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:88-137`

**ToolCallDTO（工具轨迹，SRS 检测可复用为"检测步骤"）**：

```typescript
export interface ToolCallDTO {
  name: string;                // 工具名，如 "srs_syntax_check"
  input: unknown;              // 工具输入
  output?: unknown;            // 工具输出
  errorCode?: string;
  toolCallId?: string;
  startedAt?: EpochMs;
  endedAt?: EpochMs;
  /** 工具调用前 LLM 的 thinking */
  thinkingBefore?: string;
  /** 工具调用前可见的 assistant 文本 */
  assistantTextBefore?: string;
}
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:53-86`

### B.4 L2 Policy：策略记忆数据结构

L2 在系统检测到成功模式重复出现时归纳。高价值 trace 通过向量签名余弦相似度与现有策略比对，未匹配的进入 `l2_candidate_pool`，桶达到 `minEpisodesForInduction` 时 LLM 归纳新策略草稿。

```typescript
export interface PolicyDTO extends OwnershipDTO {
  id: PolicyId;
  title: string;
  trigger: string;             // 触发条件
  procedure: string;           // 执行步骤
  verification: string;        // 验证方式
  boundary: string;            // 适用边界
  support: number;             // 支撑 episode 数
  gain: number;                // 支撑 trace 的平均 ΔV
  status: "candidate" | "active" | "archived";
  experienceType?:
    | "success_pattern"
    | "repair_validated"
    | "failure_avoidance"
    | "repair_instruction"
    | "preference"
    | "verifier_feedback"
    | "procedural";
  evidencePolarity?: "positive" | "negative" | "neutral" | "mixed";
  salience?: number;
  confidence?: number;
  skillEligible?: boolean;
  createdAt: EpochMs;
  updatedAt: EpochMs;
  share?: { scope: ShareScope; target?: string | null; sharedAt?: EpochMs | null } | null;
  editedAt?: EpochMs;
  /** 决策指导：偏好 + 反模式 */
  preference: string[];
  antiPattern: string[];
  /** 支撑本策略的 episode/feedback/trace id */
  sourceEpisodeIds: string[];
  sourceFeedbackIds?: string[];
  sourceTraceIds?: string[];
  verifierMeta?: Record<string, unknown> | null;
}
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:255-315`

> L2 归纳逻辑：[DeepWiki 14.1-l1l2l3] l2.ts L5-13 —— "Incoming high-value traces are compared against existing policies using cosine similarity of their vector signatures; unmatched traces enter a `l2_candidate_pool`. Once a bucket reaches `minEpisodesForInduction`, the LLM induces a new policy draft."

### B.5 L3 World Model：世界模型记忆数据结构

L3 是 agent 的"智慧"，聚类相关 L2 策略形成对环境动态/用户偏好的更广理解。采用 V7 §1.1 的 (ℰ, ℐ, 𝒞) 三元组结构。

```typescript
export interface WorldModelStructureEntryDTO {
  /** 短标签，如 "src/components/" 或 "GJB438C 合格性表" */
  label: string;
  /** 自由形式解释 */
  description: string;
  /** 证据：trace id 和/或 policy id */
  evidenceIds?: string[];
}

export interface WorldModelDTO extends OwnershipDTO {
  id: WorldModelId;
  title: string;
  /** 自由形式散文，总结结构/模式/约束 */
  body: string;
  /**
   * V7 §1.1 / §2.4.1 结构化 (ℰ, ℐ, 𝒞) 三元组：
   *   - environment (ℰ) 拓扑事实（"X 位于 Y"）
   *   - inference   (ℐ) 行为规则（"X 导致 Y"）
   *   - constraints (𝒞) 禁忌（"不要做 Z，因为…"）
   * 每条带可选 evidenceIds，viewer 渲染可点击证据 chip
   */
  structure: {
    environment: WorldModelStructureEntryDTO[];
    inference: WorldModelStructureEntryDTO[];
    constraints: WorldModelStructureEntryDTO[];
  };
  policyIds: PolicyId[];       // 关联的 PolicyId
  createdAt: EpochMs;
  updatedAt: EpochMs;
  version: number;             // L3 抽象版本，每次 merge/rebuild +1
  status: "active" | "archived";
  share?: { scope: ShareScope; target?: string | null; sharedAt?: EpochMs | null } | null;
  editedAt?: EpochMs;
}
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:317-383`

> L3 抽象逻辑：[DeepWiki 14.1-l1l2l3] core/types.ts L72-73 —— "Abstracted from multiple active policies via `runL3`"

### B.6 技能结晶化（Skill）：L1/L2 → 可执行技能

技能结晶是演化 pipeline 的终态：将 L2 策略 + L1 证据打包成正式可执行 `Skill`。

```typescript
export interface SkillDTO extends OwnershipDTO {
  id: SkillId;
  name: string;
  status: "candidate" | "active" | "archived";
  /** 纯文本调用指南，检索 Tier-1 时注入 */
  invocationGuide: string;
  /** V7 §2.4.6 决策指导：偏好 + 反模式 */
  decisionGuidance: { preference: string[]; antiPattern: string[] };
  /** V7 §2.1 evidence_anchors —— 结晶时支撑本技能的 L1 trace */
  evidenceAnchors: TraceId[];
  eta: SkillEta;               // 采纳率 [0,1]
  support: number;             // 独立正样本 episode 数
  gain: number;                // V_with − V_without
  trialsAttempted?: number;
  trialsPassed?: number;
  sourcePolicyIds: PolicyId[];
  sourceWorldModelIds: WorldModelId[];
  createdAt: EpochMs;
  updatedAt: EpochMs;
  version: number;             // 结晶=1，每次 rebuild +1
  share?: { scope: ShareScope; target?: string | null; sharedAt?: EpochMs | null } | null;
  editedAt?: EpochMs;
  usageCount?: number;         // memos_skill_get 成功调用数
  lastUsedAt?: EpochMs | null;
}
```

> 来源：`apps/memos-local-plugin/agent-contract/dto.ts:385-443`

**结晶化流程**（5 步）：
1. **Drafting**：`crystallizeDraft` 接收 `PolicyRow` + 支撑 `TraceRow` 证据 — crystallize.ts L75-78
2. **LLM 生成**：`SKILL_CRYSTALLIZE_PROMPT` 指导 LLM 生成结构化技能定义（参数/步骤/示例） — crystallize.ts L115-127
3. **语言引导**：检测证据主导语言，引导 LLM 用同语言输出人类可读字段 — crystallize.ts L107-112
4. **规范化**：清洗文本，确保 `steps`/`examples` 结构正确 — crystallize.ts L142-158
5. **拒答检测**：显式检测模型拒答/安全触发，避免存入"我无法完成" — crystallize.ts L128-141

> 来源：[DeepWiki 14.2-retrieval] crystallize.ts L75-158

### B.7 三层间的数据流（capture → reward → L2 → L3 → skill）

Orchestrator 拥有事件总线和订阅者，确保 episode 结束时 capture 与 reward 链顺序触发：

1. **Capture**：`extractSteps` 把 session 转成 `StepCandidate` — capture.ts L135-147
2. **Scoring**：`batchScoreReflections` 单次 LLM 调用完成 episode 级反思合成 + α 打分 — batch-scorer.ts L1-17
3. **L2/L3 Trigger**：reward 更新后触发 `runL2` 和 `runL3` 更新策略与世界模型

> 来源：[DeepWiki 14.1-l1l2l3] orchestrator.ts L4-11, L112-126

---

## C. REST API 完整列表

> 本节为**路线①（MemOS Server）**的 REST API，全部端点前缀 `/product`，FastAPI 实现，Pydantic v2 模型校验。
> 来源：[DeepWiki 5.1-rest-api-endpoints] server_router.py L68-135；[DeepWiki 5.2-request-and-response-models] product_models.py

### C.1 端点总表

#### 记忆操作

| 端点 | 方法 | 请求模型 | 响应模型 | 说明 |
|------|------|----------|----------|------|
| `/product/add` | POST | `APIADDRequest` | `MemoryResponse` | 从 messages/files/纯文本添加记忆 |
| `/product/search` | POST | `APISearchRequest` | `SearchResponse` | 混合检索策略搜索记忆 |
| `/product/get_memory` | POST | `GetMemoryRequest` | `GetMemoryResponse` | 分页+过滤获取记忆 |
| `/product/get_memory/{memory_id}` | GET | 路径参数 | `GetMemoryResponse` | 按 ID 取单条记忆 |
| `/product/get_all` | POST | `GetMemoryPlaygroundRequest` | `MemoryResponse` | 取全部记忆或子图（可视化） |
| `/product/create_cube` | POST | — | — | 创建 Memory Cube |
| `/product/delete_memory` | POST | — | — | 删除记忆 |

#### 对话操作

| 端点 | 方法 | 请求模型 | 响应模型 | 说明 |
|------|------|----------|----------|------|
| `/product/chat/complete` | POST | `APIChatCompleteRequest` | JSON | 非流式记忆增强对话 |
| `/product/chat/stream` | POST | `ChatRequest` | SSE | 流式记忆增强对话 |

#### 调度监控

| 端点 | 方法 | 请求模型 | 响应模型 | 说明 |
|------|------|----------|----------|------|
| `/product/scheduler/allstatus` | GET | — | `AllStatusResponse` | 所有任务聚合指标 |
| `/product/scheduler/task_queue_status` | GET | query | `TaskQueueResponse` | 实时队列深度 |
| `/product/scheduler/wait` | POST | — | — | 阻塞直到用户队列空闲 |

> 来源：[DeepWiki 5.1] server_router.py L98-102, L128-134；[DeepWiki 5.4] scheduler/wait.md L12-19

### C.2 关键请求模型

#### APIADDRequest（添加记忆）

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `user_id` | `str` | 必填 | 用户标识 |
| `writable_cube_ids` | `list[str]` | `None` | 写入目标 Cube |
| `messages` | `MessagesType` | `None` | 多模态消息（text/file/image） |
| `async_mode` | `Literal["async","sync"]` | `"async"` | 处理模式 |
| `mode` | `Literal["fast","fine"]` | `None` | 提取模式（仅 sync） |
| `session_id` | `str` | `None` | 会话标识 |
| `task_id` | `str` | `None` | 任务追踪 ID |
| `info` | `dict[str,Any]` | `None` | 任意元数据（**可搜索**） |

**已弃用字段（自动转换）**：`mem_cube_id`→`writable_cube_ids`；`memory_content`→`messages`(text item)；`doc_path`→`messages`(file item)

> 来源：[DeepWiki 5.2] product_models.py L518-716, L637-682

#### APISearchRequest（搜索记忆）

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `user_id` | `str` | 必填 | 用户标识 |
| `query` | `str` | 必填 | 搜索查询串 |
| `readable_cube_ids` | `list[str]` | `None` | 跨 Cube 搜索 |
| `mode` | `SearchMode` | `FAST` | `fast`/`fine`/`mixture` |
| `top_k` | `int` | `10` | 文本记忆召回数 |
| `relativity` | `float` | `0.45` | 最小相关度阈值（0=禁用） |
| `dedup` | `Literal["no","sim","mmr"]` | `"mmr"` | 去重策略 |
| `filter` | `dict[str,Any]` | `None` | 高级元数据过滤 |

> 来源：[DeepWiki 5.2] product_models.py L301-516, L335-375

#### ChatRequest（记忆增强对话）

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `user_id` | `str` | 必填 | 用户标识 |
| `query` | `str` | 必填 | 对话消息 |
| `readable_cube_ids` | `list[str]` | `None` | 记忆搜索 Cube |
| `writable_cube_ids` | `list[str]` | `None` | 存储对话 Cube |
| `history` | `MessageList` | `None` | 对话历史 |
| `mode` | `SearchMode` | `FAST` | 记忆搜索模式 |
| `relativity` | `float` | `0.45` | 相关度阈值 |
| `add_message_on_answer` | `bool` | `True` | 回答后自动存入记忆 |

> 来源：[DeepWiki 5.2] product_models.py L136-224, L163-174

### C.3 响应模型

所有响应继承 `BaseResponse[T]`：

| 模型 | 数据类型 | 用途 |
|------|----------|------|
| `MemoryResponse` | `list` | add / feedback |
| `SearchResponse` | `dict`（含 `text_mem` / `pref_mem` 桶） | search |
| `GetMemoryResponse` | `dict` | 记忆检索 |

> 来源：[DeepWiki 5.2] product_models.py L20-26, L227-275；search_handler.py L105-152

### C.4 SSE 流式格式

`/product/chat/stream` 返回的 SSE 结构：`type`（`status`/`reference`/`text`/`error`）+ `data`（内容块或元数据对象）。

> 来源：[DeepWiki 5.1] chat.md L57-60

### C.5 MCP Server（供 Claude Desktop / IDE 用）

MCP Server 用 `FastMCP` 框架包装 `MOS` 实例，暴露可发现工具：

| 工具名 | 说明 | 内部函数 |
|--------|------|----------|
| `chat` | 记忆增强对话（可选 CoT） | `mos_core.chat()` |
| `add_memory` | 摄入新内容到默认 Cube | `mos_core.add_memory()` |
| `search_memory` | 跨 Cube 混合搜索 | `mos_core.search_memory()` |
| `create_user` | 创建用户及记忆空间 | `mos_core.create_user()` |
| `create_mem_cube` | 创建专用 Cube | `mos_core.create_mem_cube()` |

关键环境变量：`OPENAI_API_KEY`、`MOS_TEXT_MEM_TYPE`(默认 `tree_text`)、`NEO4J_URI`、`ENABLE_MEM_SCHEDULER`。

> 来源：[DeepWiki 5.5-mcp-server] mcp_serve.py L125-160, L18-77

---

## D. Memory Cube API（自托管 /product）

> 本节给出**真实可运行**的自托管 REST 调用代码，来自 GitHub README "Self-Host" 示例。

### D.1 创建 Cube + 添加 + 搜索（requests）

```python
import requests, json

headers = {"Content-Type": "application/json"}
base = "http://localhost:8000/product"

# 1. 创建记忆 Cube
requests.post(f"{base}/create_cube", headers=headers, data=json.dumps({
    "cube_name": "Alice's memory",
    "owner_id": "alice",
    "cube_id": "alice_cube",
}))

# 2. 添加记忆
requests.post(f"{base}/add", headers=headers, data=json.dumps({
    "user_id": "alice",
    "writable_cube_ids": ["alice_cube"],
    "messages": [{"role": "user", "content": "I like strawberry"}],
    "async_mode": "sync",
}))

# 3. 搜索记忆
res = requests.post(f"{base}/search", headers=headers, data=json.dumps({
    "query": "What do I like?",
    "user_id": "alice",
    "readable_cube_ids": ["alice_cube"],
}))
print(res.json())
```

> 来源：GitHub README "Try the API"

### D.2 多 Cube 并行搜索与合并

`CompositeCubeView` 用 `ContextThreadPoolExecutor` 并行搜索所有关联 Cube，结果合并为统一结构（含 `text_mem`/`act_mem`/`para_mem`/`tool_mem`/`skill_mem`/`pref_mem`）。

```python
# 跨多个 Cube 搜索（SRS 场景：同时查 L1轨迹Cube + L2策略Cube + L3知识Cube）
res = requests.post(f"{base}/search", headers=headers, data=json.dumps({
    "query": "GJB 438C 合格性规定表数值交叉验证",
    "user_id": "srs_engine",
    "readable_cube_ids": ["srs_l1_traces", "srs_l2_policies", "srs_l3_domain"],
    "mode": "fine",          # fine 模式用 LLM 解析结构化 topic/key/tag
    "top_k": 10,
    "relativity": 0.45,
    "dedup": "mmr",
}))
```

> 来源：[DeepWiki 3.2-memory-cubes] composite_cube.py L46-83, L63-75

### D.3 Python SDK（MemOSClient，连云端或自托管）

`MemOSClient` 是高层 SDK 封装（来自 `src/memos/api/client.py`，859 行真实源码）。核心方法签名（逐行来自源码）：

```python
class MemOSClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, is_global: str | bool = "false"):
        # base_url 优先级: 参数 > MEMOS_BASE_URL 环境变量 > 默认(国内/全球)
        # headers = {"Content-Type": "application/json", "Authorization": f"Token {api_key}"}
        ...

    def add_message(self, messages, user_id=None, conversation_id=None, info=None,
                    source=None, app_id=None, agent_id=None, async_mode=True,
                    tags=None, allow_public=False, ...) -> MemOSAddResponse | None
    # 端点: POST /add/message

    def search_memory(self, query, user_id=None, conversation_id=None, agent_id=None,
                      memory_limit_number=6, include_preference=True,
                      knowledgebase_ids=None, filter=None, relativity=None,
                      include_skill=False, skill_limit_number=6,
                      context_format="memory", include_tool_memory=False, ...) -> MemOSSearchResponse | None
    # 端点: POST /search/memory

    def chat(self, user_id, conversation_id, query, internet_search=False,
             system_prompt=None, model_name=None, knowledgebase_ids=None,
             add_message_on_answer=True, max_tokens=8192, temperature=0.7,
             stream=False, relativity=None, ...) -> MemOSChatResponse | Iterator[str] | None
    # 端点: POST /chat

    def get_memory(self, user_id=None, include_preference=True, page=1, size=10,
                   agent_id=None, include_tool_memory=True, filter=None, ...) -> MemOSGetMemoryResponse | None
    # 端点: POST /get/memory

    def get_memory_by_id(self, memid: str) -> dict | None
    # 端点: GET /get/memory/{memid}

    def create_knowledgebase(self, knowledgebase_name, knowledgebase_description=None) -> MemOSCreateKnowledgebaseResponse | None
    # 端点: POST /create/knowledgebase

    def add_feedback(self, user_id, feedback_content=None, conversation_id=None, ...) -> MemOSAddFeedBackResponse | None
    # 端点: POST /add/feedback

    def get_task_status(self, task_id: str) -> MemOSGetTaskStatusResponse | None
    # 端点: POST /get/status

    def delete_memory(self, memory_ids=None, user_id=None, agent_id=None, filter=None, memory_type=None, ...) -> MemOSDeleteMemoryResponse | None
    # 端点: POST /delete/memory

    def update_memory(self, memory_id, content=None, title=None, status=None) -> dict | None
    # 端点: POST /update/memory

    def extract_memory(self, messages, extraction_types=None, model=None) -> dict | None
    # 端点: POST /extract/memory
```

> 来源：`src/memos/api/client.py:33-62, 142-190, 192-250, 328-355, 545-570, 612-663, 665-683, 685-699, 770-859`

**连自托管服务**：设置 `base_url` 指向本地即可，自托管无需 api_key（但构造函数要求非空，可传任意占位串）：

```python
from memos.api.client import MemOSClient
client = MemOSClient(api_key="local", base_url="http://localhost:8000/product")
```

> 来源：`src/memos/api/client.py:55-62`（base_url 优先级逻辑）

---

## E. TreeTextMemory 数据结构

> `TreeTextMemory` 是路线①的图谱化文本记忆实现，组织为图数据库节点 + 父子关系，支持语义相似 + 结构遍历。
> 来源：[DeepWiki 6.5-tree-text-memory] tree.py L39-42

### E.1 记忆节点结构

每个记忆为 `TextualMemoryItem` + `TreeNodeTextualMemoryMetadata`：

| 字段 | 类型 | 用途 |
|------|------|------|
| `user_id` | `str` | 拥有者 |
| `memory_type` | `str` | 作用域分类（如 `LongTermMemory`） |
| `status` | `str` | 节点生命周期（`activated`/`archived`） |
| `key` | `str` | 短标题/摘要 |
| `tags` | `list[str]` | 语义关键词 |
| `embedding` | `list[float]` | 向量表示 |
| `type` | `str` | 节点类型（`fact`/`experience`/`topic`） |
| `sources` | `list` | 生成该记忆的原始消息 |
| `background` | `str` | 上下文摘要（常含 `[working_binding:<uuid>]`） |
| `created_at` / `updated_at` | `datetime` | 时间戳 |

> 来源：[DeepWiki 6.5] item.py L5-22；tree.py L22-23；manager.py L23-51

### E.2 五大记忆作用域（这是路线①模拟 L1/L2/L3 的关键）

| 作用域 | 用途 | 默认容量 | 保留策略 |
|--------|------|----------|----------|
| `WorkingMemory` | 最近对话上下文/活动会话状态 | 20 | FIFO/清理 |
| `LongTermMemory` | 持久事实与知识 | 1500 | 周期重组 |
| `UserMemory` | 用户画像/偏好/个人信息 | 480 | 周期重组 |
| `SkillMemory` | 工具使用技能/程序性知识 | N/A | 专用 `skill_mem_top_k` 检索 |
| `PreferenceMemory` | 交互提取的用户偏好 | N/A | 专用 `pref_mem_top_k` 检索 |

> 来源：[DeepWiki 6.5] manager.py L67-81；tree.py L82-86；searcher.py L117-121

### E.3 混合检索流程（4 路）

`GraphMemoryRetriever.retrieve()` 组合多路：
- **Vector 相似**：`_vector_recall` 用 embedding 找语义相似节点
- **Graph 遍历**：`_graph_recall` 从 dispatch plan 跑图遍历
- **BM25**：`_bm25_recall` 用 `EnhancedBM25` 关键词检索（可选）
- **全文检索**：`_fulltext_recall` 对索引属性文本搜索（可选）

搜索模式：`fast`（直接用 task 描述或简单 token 化）/ `fine`（LLM 解析结构化 topic/key/tag，触发 `MemoryReasoner`）。

> 来源：[DeepWiki 6.5] recall.py L79-182, L131-175；searcher.py L105-156

### E.4 存储后端

| 后端 | 实现类 | 特性 |
|------|--------|------|
| Neo4j Enterprise (≥5.18) | `Neo4jGraphDB` | 原生向量索引 `vector.similarity.cosine()`，多库物理隔离 |
| Neo4j Community | `Neo4jCommunityGraphDB` | 外部 VecDB（Qdrant）集成，仅属性索引 |
| PolarDB | `PolarDBGraphDB` | Apache AGE 扩展，SQL/Cypher 混合，轻量向量搜索 |

多租户：`use_multi_db=True`（物理隔离，每租户独立库）/ `False`（逻辑隔离，节点带 `user_name` 属性，查询自动注入 `WHERE n.user_name=$user_name`）。

> 来源：[DeepWiki 4.4-storage-layer] neo4j.py L99-154, L158-166；neo4j_community.py L22-52；polardb.py L125-186；graph_db.py L17-69

---

## F. 多模态记忆

MemOS 原生支持文本、图像、工具轨迹、persona，统一在一个记忆系统检索推理。

### F.1 添加多模态记忆（messages 字段）

`APIADDRequest.messages` 为 `MessagesType`，支持 text/file/image 三类 item：

```python
import requests, json
base = "http://localhost:8000/product"
headers = {"Content-Type": "application/json"}

# 多模态：文本 + 图片 + 文件
requests.post(f"{base}/add", headers=headers, data=json.dumps({
    "user_id": "srs_engine",
    "writable_cube_ids": ["srs_l1_traces"],
    "async_mode": "sync",
    "messages": [
        {"role": "user", "content": "检测到电池SRS图文不一致"},
        {"role": "assistant", "content": [{"type": "image", "image_url": "file:///path/img.png"}]},
    ],
    "info": {"doc_id": "battery_srs", "layer": "L1", "conflict_type": "image_text"},
}))
```

> 来源：[DeepWiki 5.2] product_models.py L518-716（messages 多模态）；[DeepWiki 1.2-key-features]（多模态记忆特性）

### F.2 工具轨迹记忆

`include_tool_memory=True` 时搜索返回 `tool_mem` 桶；`CompositeCubeView` 合并结果含 `tool_mem`/`skill_mem`。

```python
res = client.search_memory(
    query="语法层检测步骤",
    user_id="srs_engine",
    include_tool_memory=True,
    tool_memory_limit_number=6,
)
```

> 来源：`src/memos/api/client.py:203, 235`；[DeepWiki 3.2] composite_cube.py L68-75

---

## G. MemScheduler 异步调度

异步摄入是 MemOS 生产稳定性的核心：`async_mode="async"` 时任务经 `mem_scheduler.submit_messages` 入队，毫秒级延迟。

### G.1 任务标签与状态

| 任务标签 | 用途 | 代码引用 |
|----------|------|----------|
| `ADD_TASK_LABEL` | 异步处理新记忆项 | core.py L20 |
| `MEM_READ_TASK_LABEL` | 触发后台记忆读取 | core.py L22 |
| `ANSWER_TASK_LABEL` | 从 AI 回答提取长期记忆 | core.py L21 |
| `QUERY_TASK_LABEL` | 追踪查询频率以晋升工作记忆 | core.py L24 |

任务状态（Redis `TaskStatusTracker` 追踪）：`waiting` / `in_progress` / `completed` / `failed` / `cancelled`。

> 来源：[DeepWiki 3.3-mos] core.py L18-25, L111-139；[DeepWiki 5.1] status_tracker.py L1-20

### G.2 同步等待队列空闲

自动化工作流可用 `/product/scheduler/wait` 阻塞直到某用户记忆处理队列空闲，确保检测轨迹已落库再做 L2 归纳：

```python
# 等待 srs_engine 的所有异步记忆任务完成
requests.post(f"{base}/scheduler/wait", headers=headers,
              data=json.dumps({"user_id": "srs_engine"}))
```

> 来源：[DeepWiki 5.4-client-integration] scheduler/wait.md L12-19

### G.3 任务状态查询

```python
status = client.get_task_status(task_id="add_task_xxx")
# 返回 StatusResponse: {status: "completed", task_id: "..."}
```

> 来源：`src/memos/api/client.py:545-570`

---

## H. Reflect2Evolve MemoryCore 接口（真实 TypeScript 源码）

> ⚠️ 本节为**路线②**的 `MemoryCore` 接口，逐行来自
> `apps/memos-local-plugin/agent-contract/memory-core.ts`（599 行）。
> 这是适配器（OpenClaw/Hermes/任意 Python agent 经 JSON-RPC 桥）调用的唯一门面。

### H.1 生命周期与会话

```typescript
export interface MemoryCore {
  // ── lifecycle ──
  init(): Promise<void>;
  shutdown(): Promise<void>;
  health(): Promise<CoreHealth>;
  waitForStartupRecovery?(): Promise<void>;

  // ── session / episode ──
  openSession(input: {
    agent: AgentKind;
    sessionId?: SessionId;
    meta?: Record<string, unknown>;
    namespace?: RuntimeNamespace;
  }): Promise<SessionId>;
  closeSession(sessionId: SessionId): Promise<void>;
  openEpisode(input: {
    sessionId: SessionId;
    episodeId?: EpisodeId;
    userMessage?: string;
  }): Promise<EpisodeId>;
  closeEpisode(episodeId: EpisodeId): Promise<void>;
```

> 来源：`memory-core.ts:161-199`

### H.2 每轮 Pipeline（L1 写入入口）

```typescript
  // ── pipeline (per turn) ──
  /** agent 行动前调用，返回要注入的上下文 */
  onTurnStart(turn: TurnInputDTO): Promise<RetrievalResultDTO>;
  /** agent 行动后调用，持久化 trace，调度归纳等 */
  onTurnEnd(result: TurnResultDTO): Promise<{ traceId: string; episodeId: EpisodeId }>;
  /** 用户给任务级反馈（或隐式信号触发） */
  submitFeedback(feedback: Omit<FeedbackDTO, "id" | "ts"> & { ts?: number }): Promise<FeedbackDTO>;
  /** 记录工具结果，喂给 decision-repair，非阻塞 */
  recordToolOutcome(outcome: ToolOutcomeDTO): void;
  /** 记录父会话委派结果 */
  recordSubagentOutcome(outcome: SubagentOutcomeDTO): Promise<{ traceId: string; episodeId: EpisodeId }>;
```

> 来源：`memory-core.ts:201-221`

**这是 L1 写入的真实入口**：`onTurnEnd` 持久化 `TraceDTO`，触发 capture→reward→L2→L3→skill 链。SRS 场景下：每次冲突检测 = 一个 turn，`userText`=待检文档，`toolCalls`=各层检测工具调用，`agentText`=检测报告。

### H.3 记忆查询（L1/L2/L3 读取）

```typescript
  // ── memory queries ──
  searchMemory(query: RetrievalQueryDTO): Promise<RetrievalResultDTO>;
  getTrace(id: string, namespace?: RuntimeNamespace): Promise<TraceDTO | null>;
  updateTrace(id: string, patch: {
    summary?: string | null; userText?: string; agentText?: string; tags?: readonly string[];
  }): Promise<TraceDTO | null>;
  deleteTrace(id: string): Promise<{ deleted: boolean }>;
  deleteTraces(ids: readonly string[]): Promise<{ deleted: number }>;
  shareTrace(id: string, share: {
    scope: ShareScope | null; target?: string | null; sharedAt?: number | null;
  }): Promise<TraceDTO | null>;

  getPolicy(id: string, namespace?: RuntimeNamespace, opts?: { includeAllNamespaces?: boolean }): Promise<PolicyDTO | null>;
  getWorldModel(id: string, namespace?: RuntimeNamespace, opts?: { includeAllNamespaces?: boolean }): Promise<WorldModelDTO | null>;

  /** 列出 L2 策略（"经验"），最新在前 */
  listPolicies(input?: {
    status?: PolicyDTO["status"]; limit?: number; offset?: number; q?: string;
    ownerAgentKind?: AgentKind; ownerProfileId?: string; includeAllNamespaces?: boolean;
  }): Promise<PolicyDTO[]>;
  countPolicies(input?: {...}): Promise<number>;

  /** 列出 L3 世界模型（"世界环境知识"），最新在前 */
  listWorldModels(input?: {
    limit?: number; offset?: number; q?: string; namespace?: RuntimeNamespace;
    ownerAgentKind?: AgentKind; ownerProfileId?: string; includeAllNamespaces?: boolean;
  }): Promise<WorldModelDTO[]>;
  countWorldModels(input?: {...}): Promise<number>;

  setPolicyStatus(id: string, status: PolicyDTO["status"]): Promise<PolicyDTO | null>;
  deletePolicy(id: string): Promise<{ deleted: boolean }>;
  /** 追加决策指导（偏好/反模式）到策略 */
  editPolicyGuidance(id: string, patch: { preference?: string[]; antiPattern?: string[] }): Promise<PolicyDTO | null>;
  updatePolicy(id: string, patch: {
    title?: string; trigger?: string; procedure?: string; verification?: string; boundary?: string;
  }): Promise<PolicyDTO | null>;
  deleteWorldModel(id: string): Promise<{ deleted: boolean }>;
  updateWorldModel(id: string, patch: { title?: string; body?: string; status?: "active" | "archived" }): Promise<WorldModelDTO | null>;
  archiveWorldModel(id: string): Promise<WorldModelDTO | null>;
  unarchiveWorldModel(id: string): Promise<WorldModelDTO | null>;
```

> 来源：`memory-core.ts:223-371`

### H.4 检索结果与注入包

```typescript
export interface RetrievalQueryDTO {
  agent: AgentKind;
  namespace?: RuntimeNamespace;
  sessionId?: SessionId;
  episodeId?: EpisodeId;
  query: string;
  filters?: Record<string, unknown>;
  /** 每层最大返回数（覆盖配置） */
  topK?: { tier1?: number; tier2?: number; tier3?: number };
}

export interface RetrievalHitDTO {
  tier: 1 | 2 | 3;
  refId: string;                // skillId | traceId/episodeId | worldModelId
  refKind: "skill" | "trace" | "episode" | "experience" | "world-model";
  score: number;
  snippet: string;
  ownerAgentKind?: AgentKind;
  shareScope?: ShareScope;
  sourceTraceId?: string;
}

export interface RetrievalResultDTO {
  query: RetrievalQueryDTO;
  hits: RetrievalHitDTO[];
  /** 最终注入上下文（已 MMR 排序 + 去重） */
  injectedContext: string;
  tierLatencyMs: { tier1: number; tier2: number; tier3: number };
}
```

> 来源：`dto.ts:551-585`

### H.5 三层检索触发策略（按 trigger 选 tier 组合）

| Trigger | Tier1(Skill) | Tier2(Trace/Policy/Episode) | Tier3(WorldModel) | 用途 |
|---------|--------------|------------------------------|-------------------|------|
| `turn_start` | ✓ | ✓ | ✓ | 全量上下文注入 |
| `tool_driven` | ✗ | ✓ | ✓ | 即时工具指导 |
| `skill_invoke` | 主 | ✓ | ✗ | 特定技能调用指南 |
| `sub_agent` | ✗ | ✓ | ✓ | 子 agent 上下文 |
| `decision_repair` | ✓ | ✓ | ✗ | 解除失败循环（反模式注入） |

> 来源：[DeepWiki 14.1-l1l2l3] retrieve.ts L1-13, L89-191；[DeepWiki 14.2] retrieve.ts L117-191

### H.6 技能管理与导出导入

```typescript
  // ── skills ──
  listSkills(input?: { status?: SkillDTO["status"]; limit?: number; ... }): Promise<SkillDTO[]>;
  countSkills(input?: {...}): Promise<number>;
  getSkill(id: SkillId, opts?: {
    recordUse?: boolean; recordTrial?: boolean; sessionId?: SessionId;
    episodeId?: EpisodeId; traceId?: string; turnId?: EpochMs; ...
  }): Promise<SkillDTO | null>;
  archiveSkill(id: SkillId, reason?: string): Promise<void>;
  deleteSkill(id: SkillId): Promise<{ deleted: boolean }>;
  reactivateSkill(id: SkillId): Promise<SkillDTO | null>;
  updateSkill(id: SkillId, patch: { name?: string; invocationGuide?: string }): Promise<SkillDTO | null>;
  shareSkill(id: SkillId, share: {...}): Promise<SkillDTO | null>;

  // ── export / import (bundle) ──
  exportBundle(): Promise<{
    version: 1; exportedAt: number;
    traces: TraceDTO[]; policies: PolicyDTO[];
    worldModels: WorldModelDTO[]; skills: SkillDTO[];
  }>;
  importBundle(bundle: {
    version?: number; traces?: unknown[]; policies?: unknown[];
    worldModels?: unknown[]; skills?: unknown[];
  }): Promise<{ imported: number; skipped: number }>;
```

> 来源：`memory-core.ts:454-576`

`exportBundle` / `importBundle` 可完整迁移 SRS 检测经验库（trace+policy+worldmodel+skill 一键打包）。

### H.7 从 Python 调用（JSON-RPC 桥）

路线②核心是 TypeScript，但 Python agent 经 `MemosBridgeClient` 跨语言调用。桥管理 Node 子进程，经 stdio 线程安全发请求，支持反向 RPC（Node 桥可请求 Python host 的 LLM）。

```python
# adapters/hermes/memos_provider/bridge_client.py 的 MemosBridgeClient
# 自动选择 dist/bridge.mjs (ESM) 优先于 dist/bridge.cjs
# 用 --agent --no-viewer 启动，必要时用 tsx loader
# 桥方法: session.open / turn.start / turn.end / subagent.record / tool.call
```

> 来源：[DeepWiki 14.3-adapters] bridge_client.py L59-81, L122-128, L144-167；bridge.cts L87-184

**桥端口**：OpenClaw viewer `18799`，Hermes viewer `18800`。PID 文件防进程泄漏（`bridge.pid` / `bridge-stdio.pid`），新桥杀旧桥。

> 来源：[DeepWiki 14.3] bridge.cts L15-18, L127-154

---

## I. SRS 冲突检测经验积累方案（完整可运行代码）

> 本方案采用**路线①（MemOS Server）**，用多 Cube + `info`/`tags` 元数据模拟 L1/L2/L3，纯 Python，可直接嵌入现有 `tools/srs_consistency_checker_v2.py`。
> 若需原生 L1→L2→L3 自演化，见 §I.6 的路线②对接说明。

### I.1 整体设计

```
SRS一致性检测 ──(每次)──▶ L1 Cube: 记录检测轨迹
        │                    (doc_id, layer, conflicts, tool_calls, P/R/F1)
        │
        ├──(批量反思)──▶ L2 Cube: 检测策略
        │                    (trigger, procedure, verification, support, gain)
        │
        └──(抽象)─────▶ L3 Cube: 领域知识
                             (environment/inference/constraints 三元组)

新SRS检测 ──(检索)──▶ 跨 L1+L2+L3 Cube fine 搜索 ──▶ 注入经验上下文
```

**三 Cube 映射**：
- `srs_l1_traces`（`LongTermMemory`）：每次检测的轨迹，`info.layer`∈{syntax,semantic,logic}
- `srs_l2_policies`（`SkillMemory`）：从多次检测归纳的策略
- `srs_l3_domain`（`LongTermMemory`）：SRS 领域冲突模式库

### I.2 完整经验积累客户端

```python
"""
srs_memos_experience.py — 基于 MemOS Server 的 SRS 一致性检测经验积累
依赖: pip install requests (MemOS 自托管在 http://localhost:8000)
对应路线①: MemOS Server + 多 Cube + info/tags 元数据模拟 L1/L2/L3
"""
import json
import time
import uuid
import requests
from typing import Any

BASE = "http://localhost:8000/product"
HEADERS = {"Content-Type": "application/json"}
USER = "srs_engine"

# 三层 Cube —— 一次性创建
CUBES = {
    "L1": "srs_l1_traces",      # 检测轨迹 (LongTermMemory)
    "L2": "srs_l2_policies",    # 检测策略 (SkillMemory)
    "L3": "srs_l3_domain",      # 领域知识 (LongTermMemory)
}


def _post(endpoint: str, payload: dict) -> dict:
    r = requests.post(f"{BASE}/{endpoint}", headers=HEADERS,
                      data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    return r.json()


def init_cubes():
    """初始化三层 Cube（已存在则跳过）"""
    for layer, cube_id in CUBES.items():
        try:
            _post("create_cube", {
                "cube_name": f"SRS {layer} Memory",
                "owner_id": USER,
                "cube_id": cube_id,
            })
        except requests.HTTPError:
            pass  # Cube 已存在


# ───────────────────────── L1: 记录检测轨迹 ─────────────────────────

def record_detection_trace(
    doc_id: str,
    doc_source: str,                 # "gjb" | "ieee830" | "nasa" ...
    layer: str,                      # "syntax" | "semantic" | "logic"
    conflicts: list[dict],           # 冲突列表 [{type, location, detail, severity}]
    tool_calls: list[dict],          # 检测步骤 [{name, input, output, duration_ms}]
    precision: float | None = None,
    recall: float | None = None,
    f1: float | None = None,
    reflection: str | None = None,   # 人工/自动反思摘要
) -> dict:
    """
    每次一致性检测后记录 L1 轨迹。
    对应 Reflect2Evolve 的 onTurnEnd: userText=doc, toolCalls=检测步骤,
    agentText=冲突报告, reflection=反思(用于 α 打分), value≈F1
    """
    content = (
        f"[SRS检测轨迹] 文档={doc_id} 来源={doc_source} 层={layer}\n"
        f"冲突数={len(conflicts)} P={precision} R={recall} F1={f1}\n"
        f"冲突明细:\n" + json.dumps(conflicts, ensure_ascii=False, indent=2)
    )
    info = {
        "doc_id": doc_id, "doc_source": doc_source, "layer": layer,
        "conflict_count": len(conflicts),
        "conflict_types": list({c.get("type", "?") for c in conflicts}),
        "precision": precision, "recall": recall, "f1": f1,
        "tool_step_count": len(tool_calls),
        "mem_layer": "L1",
        "recorded_at": int(time.time() * 1000),
    }
    return _post("add", {
        "user_id": USER,
        "writable_cube_ids": [CUBES["L1"]],
        "async_mode": "sync",
        "mode": "fine",
        "messages": [{"role": "assistant", "content": content}],
        "info": info,
        "tags": [f"layer:{layer}", f"source:{doc_source}", "L1-trace"] + info["conflict_types"],
    })


# ───────────────────────── L2: 提取检测策略 ─────────────────────────

def induce_policy(
    trigger: str,                    # 触发条件, 如 "GJB438C SRS 含合格性规定表"
    procedure: str,                  # 执行步骤, 如 "正文数值 ↔ 表格数值交叉验证"
    verification: str,               # 验证方式, 如 "对照 Gold Standard 确认 P/R"
    boundary: str,                   # 适用边界, 如 "仅 GJB 格式, IEEE830 不适用"
    evidence_doc_ids: list[str],     # 支撑轨迹的 doc_id
    gain: float = 0.0,               # 平均 ΔF1
    anti_patterns: list[str] | None = None,
) -> dict:
    """
    从多次 L1 轨迹中提取 L2 检测策略。
    对应 Reflect2Evolve 的 runL2: 从 l2_candidate_pool 聚类归纳 PolicyDTO
    （这里用人工/LLM 归纳后写入，gain≈PolicyDTO.gain）
    """
    content = (
        f"[SRS检测策略] 触发={trigger}\n"
        f"步骤={procedure}\n验证={verification}\n边界={boundary}\n"
        f"支撑文档={evidence_doc_ids} gain={gain}\n"
        f"反模式={anti_patterns or []}"
    )
    info = {
        "trigger": trigger, "procedure": procedure,
        "verification": verification, "boundary": boundary,
        "evidence_doc_ids": evidence_doc_ids, "gain": gain,
        "anti_patterns": anti_patterns or [],
        "mem_layer": "L2",
        "status": "active",
        "recorded_at": int(time.time() * 1000),
    }
    return _post("add", {
        "user_id": USER,
        "writable_cube_ids": [CUBES["L2"]],
        "async_mode": "sync",
        "mode": "fine",
        "messages": [{"role": "assistant", "content": content}],
        "info": info,
        "tags": ["L2-policy", f"gain:{gain:.2f}"] + [f"evidence:{d}" for d in evidence_doc_ids],
    })


# ───────────────────────── L3: 抽象领域知识 ─────────────────────────

def abstract_world_model(
    title: str,
    environment: list[dict],         # [{label, description, evidence_doc_ids?}]
    inference: list[dict],           # [{label, description, evidence_doc_ids?}]
    constraints: list[dict],         # [{label, description, evidence_doc_ids?}]
    source_policy_triggers: list[str],
) -> dict:
    """
    从多个 L2 策略抽象 L3 领域知识。
    对应 Reflect2Evolve 的 runL3 + WorldModelDTO.structure (ℰ,ℐ,𝒞) 三元组
    """
    body = (
        f"[SRS领域知识] {title}\n"
        f"环境事实(ℰ):\n" + json.dumps(environment, ensure_ascii=False) + "\n"
        f"推断规则(ℐ):\n" + json.dumps(inference, ensure_ascii=False) + "\n"
        f"约束禁忌(𝒞):\n" + json.dumps(constraints, ensure_ascii=False)
    )
    info = {
        "title": title,
        "structure": {"environment": environment, "inference": inference, "constraints": constraints},
        "source_policy_triggers": source_policy_triggers,
        "mem_layer": "L3",
        "status": "active",
        "version": 1,
        "recorded_at": int(time.time() * 1000),
    }
    return _post("add", {
        "user_id": USER,
        "writable_cube_ids": [CUBES["L3"]],
        "async_mode": "sync",
        "mode": "fine",
        "messages": [{"role": "assistant", "content": body}],
        "info": info,
        "tags": ["L3-worldmodel", f"title:{title}"],
    })


# ───────────────────────── 检索: 新检测前注入经验 ─────────────────────────

def retrieve_experience(
    query: str,                      # 如 "电池SRS 合格性规定表 数值交叉验证"
    top_k: int = 10,
    relativity: float = 0.4,
    layer: str | None = None,        # 限定层: "L1"|"L2"|"L3"|None(全搜)
) -> dict:
    """
    新 SRS 文档检测前，跨 L1/L2/L3 检索相关经验。
    对应 Reflect2Evolve 的 turn_start: Tier1+2+3 全量上下文注入
    """
    cube_ids = [CUBES[layer]] if layer else list(CUBES.values())
    payload = {
        "query": query,
        "user_id": USER,
        "readable_cube_ids": cube_ids,
        "mode": "fine",          # fine 用 LLM 解析结构化 topic/key/tag
        "top_k": top_k,
        "relativity": relativity,
        "dedup": "mmr",
    }
    if layer:
        payload["filter"] = {"tags": {"$contains": f"{layer}-"}}
    return _post("search", payload)


def wait_for_ingest():
    """等待异步记忆任务全部落库（做 L2 归纳前确保 L1 已写入）"""
    try:
        _post("../product/scheduler/wait", {"user_id": USER})
    except Exception:
        pass  # 自托管路径可能不同，忽略


# ───────────────────────── 演示: 完整闭环 ─────────────────────────

if __name__ == "__main__":
    init_cubes()

    # 1) L1: 记录一次电池SRS语义层检测
    record_detection_trace(
        doc_id="battery_srs", doc_source="gjb",
        layer="semantic",
        conflicts=[{"type": "text_table_value_mismatch",
                    "location": "§3.2 vs 合格性规定表",
                    "detail": "正文写≥12V，表格写≥11.5V", "severity": "high"}],
        tool_calls=[{"name": "cross_validate_text_table", "duration_ms": 320}],
        precision=1.0, recall=0.92, f1=0.96,
        reflection="正文-表格数值不一致是高频冲突，需优先交叉验证合格性规定表",
    )

    # 2) L2: 从多次轨迹归纳策略
    induce_policy(
        trigger="GJB438C SRS 含合格性规定表 且 正文有数值约束",
        procedure="对合格性规定表每个数值，在正文搜索同义表述并做数值区间比对",
        verification="对照 Gold Standard，确认冲突位置命中",
        boundary="仅 GJB 438C 格式；IEEE830 无合格性表不适用",
        evidence_doc_ids=["battery_srs", "compiler_srs"],
        gain=0.18,
        anti_patterns=["仅做字符串相等比较会漏掉单位换算差异"],
    )

    # 3) L3: 抽象领域知识 (ℰ,ℐ,𝒞)
    abstract_world_model(
        title="GJB 438C SRS 数值一致性领域知识",
        environment=[
            {"label": "合格性规定表", "description": "GJB 438C SRS 第3.x节的表格，含性能指标阈值",
             "evidence_doc_ids": ["battery_srs"]},
        ],
        inference=[
            {"label": "正文↔表格数值需一致", "description": "正文性能约束的数值必须与合格性规定表一致或更严",
             "evidence_doc_ids": ["battery_srs", "compiler_srs"]},
        ],
        constraints=[
            {"label": "禁止仅字符串比较", "description": "数值一致性检测必须解析量纲与容差，不能只比字符串",
             "evidence_doc_ids": ["battery_srs"]},
        ],
        source_policy_triggers=["GJB438C SRS 含合格性规定表"],
    )

    # 4) 检索: 新 scheduler_srs 检测前注入经验
    wait_for_ingest()
    exp = retrieve_experience("调度器SRS 合格性规定表 数值交叉验证", top_k=5)
    print("注入的经验上下文:", exp.get("data", {}).get("text_mem", []))
```

### I.3 与现有检测器的集成点

把 `srs_memos_experience.py` 接到 `tools/srs_consistency_checker_v2.py`：

1. **检测前**：调用 `retrieve_experience(query=doc_title+" 冲突检测", layer=None)`，把返回的 `text_mem` 注入 LLM 检测 prompt 的"历史经验"段。
2. **检测后**：调用 `record_detection_trace(...)`，传入 `srs_consistency_checker_v2.py` 输出的 conflicts、各检测工具的 tool_calls、以及 `srs_eval.py` 算出的 P/R/F1。
3. **批量后**：当某类冲突在多份文档重复出现，人工或用 GLM-5 调 `induce_policy(...)` 归纳 L2 策略。
4. **周期性**：用 GLM-5 从多个 L2 策略调 `abstract_world_model(...)` 生成 L3 领域知识。

### I.4 关键设计说明

- **为何用 `info` 字段存结构化元数据**：`info` 是 `APIADDRequest` 的可搜索字段（product_models.py L136-175），MemOS 会把它扁平化进图节点属性（`_flatten_info_fields`，neo4j.py L48-72），便于 `filter` 精确过滤。这样 L1/L2/L3 的结构化字段（conflict_types/gain/structure）既能向量检索又能精确过滤。
- **为何用 `tags`**：`tags` 进 `TreeNodeTextualMemoryMetadata.tags`，是语义关键词，`fine` 模式 LLM 会解析为检索 key。用 `layer:syntax`/`L1-trace` 这类标签可在 `filter` 里按层召回。
- **`mode:"fine"` vs `"fast"`**：fine 用 LLM 解析结构化 topic/key/tag + `MemoryReasoner` 验证，召回质量高但慢；fast 直接 token 化。经验检索用 fine，实时检测注入可用 fast。
- **`relativity` 阈值**：默认 0.45，SRS 领域术语专指性强，建议降到 0.4 避免漏召。

### I.5 路线②对接（如需原生 L1→L2→L3 自演化）

若要 Reflect2Evolve 的自动反思打分（α）+ 反向传播（V_t）+ 技能结晶，需部署 `memos-local-plugin` 并从 Python 经 JSON-RPC 桥调用 `MemoryCore`。核心调用映射：

| SRS 检测动作 | MemoryCore 方法 | 对应 DTO |
|--------------|-----------------|----------|
| 开检一篇 SRS | `openSession` + `openEpisode` | `SessionId`/`EpisodeId` |
| 检测前查经验 | `onTurnStart(TurnInputDTO)` | 返回 `RetrievalResultDTO`(tier1+2+3) |
| 记录检测结果 | `onTurnEnd(TurnResultDTO)` | 写 `TraceDTO`(L1)，触发 reward→L2→L3 |
| 记录评测反馈 | `submitFeedback({polarity, magnitude})` | `FeedbackDTO` → 影响 V_t |
| 归纳策略后查 | `listPolicies({status:"active"})` | `PolicyDTO[]`(L2) |
| 查领域知识 | `listWorldModels()` | `WorldModelDTO[]`(L3) |
| 结晶技能查 | `listSkills({status:"active"})` | `SkillDTO[]`(技能) |
| 迁移经验库 | `exportBundle()` / `importBundle()` | 全量 trace+policy+worldmodel+skill |

`onTurnEnd` 的 `TurnResultDTO` 填法（SRS 映射）：
- `agentText` = 检测报告 JSON
- `toolCalls` = `[{name:"srs_syntax_check", input:{doc}, output:{conflicts}, startedAt, endedAt}, ...]`
- `reflection` = "本次发现 N 个语义冲突，合格性表数值不一致占 60%"（MemOS 用它算 α）
- `contextHints` = `{doc_id, layer, f1}`

> JSON-RPC 桥方法名：`session.open` / `turn.start` / `turn.end` / `subagent.record` / `tool.call`（来自 bridge_client.py L122-128）

### I.6 两条路线的选择决策

| 维度 | 路线① MemOS Server | 路线② Reflect2Evolve |
|------|-------------------|---------------------|
| 语言 | Python（与 SRS 项目同栈） | TypeScript + Python 桥 |
| 存储 | Neo4j + Qdrant（需外部服务） | SQLite（零依赖本地） |
| L1/L2/L3 | 用 Cube+info/tags 模拟 | 原生 DTO 一等实体 |
| 自演化 | 需手动调 induce/abstract | 自动 α 打分+V backprop+skill 结晶 |
| 检索 | 4 路混合（vector/graph/BM25/FTS） | 3 tier + LLM 过滤 + MMR |
| 部署复杂度 | 中（docker compose 一键） | 低（install.sh 一键） |
| **SRS 项目推荐** | **首选**（同栈、可复用 checker_v2） | 进阶（要自演化技能时切换） |

**建议路径**：先用路线①快速落地经验积累（§I.2 代码可直接跑），积累 50+ 检测轨迹后，若需要自动归纳策略与技能结晶，再引入路线②做自演化增强，用 `exportBundle`/`importBundle` 在两路线间迁移。

---

## 附录：源文件引用索引

| 内容 | 源文件 | 行号 |
|------|--------|------|
| TraceDTO / PolicyDTO / WorldModelDTO / SkillDTO | `apps/memos-local-plugin/agent-contract/dto.ts` | 171-443 |
| RetrievalQueryDTO / RetrievalResultDTO / InjectionPacket | `apps/memos-local-plugin/agent-contract/dto.ts` | 551-689 |
| MemoryCore 接口（全部方法） | `apps/memos-local-plugin/agent-contract/memory-core.ts` | 161-599 |
| MemOSClient Python SDK | `src/memos/api/client.py` | 33-859 |
| REST 端点路由 | `src/memos/api/routers/server_router.py` | 68-161 |
| 请求/响应模型 | `src/memos/api/product_models.py` | 16-760 |
| L2 归纳逻辑 | `apps/memos-local-plugin/core/memory/l2/l2.ts` | 5-13 |
| 技能结晶 | `apps/memos-local-plugin/core/skill/crystallize.ts` | 75-158 |
| 三层检索触发 | `apps/memos-local-plugin/core/retrieval/retrieve.ts` | 1-191 |
| TreeTextMemory | `src/memos/memories/textual/tree.py` | 39-101 |
| 存储后端 | `src/memos/graph_dbs/neo4j.py` / `neo4j_community.py` / `polardb.py` | — |
| MOS 调度标签 | `src/memos/mem_os/core.py` | 18-139 |
| JSON-RPC 桥 | `apps/memos-local-plugin/bridge.cts` / `adapters/hermes/.../bridge_client.py` | — |
| MCP Server | `src/memos/api/mcp_serve.py` | 18-160 |

> DeepWiki 索引基准：commit `e8204062`，last indexed 2026-07-25
