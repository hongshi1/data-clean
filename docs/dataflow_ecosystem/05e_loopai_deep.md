# DataFlow-LoopAI 代码级深度分析

> 源码位置：`dataflow_repos/Dataflow-LoopAI/` ｜ 17 stars, 646 commits ｜ v0.1.0 (2026-05 开源)
> 分析方法：源码精读（Graph/Node/State/Agent 全量代码）+ README + 配置文件

---

## 0. 总览：LoopAI 是什么

LoopAI 是 DataFlow 生态的**闭环优化框架**，把"大模型优化"这条传统上需要人工串联的流水线（评测→分析→取数→清洗→训练）重构为一个**图执行框架（Graph / Node / State）**，由若干智能体（Agent）协作完成，用户只需用自然语言描述目标即可。

核心定位：

```
User ⇄ Starter (Supervisor) ⇄ Sub-Agent
              │
              ├── Common Question → 直接对话回复
              └── Complex Task → Graph 执行
                             (评测 → 分析 → 取数 → 清洗 → 训练)
```

一句话总结：**NL2Optimize**——自然语言到优化工作流的自动规划与执行。

技术栈关键词：LangGraph 状态图、LangChain ReAct、Pydantic 状态建模、vLLM 本地推理、LLaMA-Factory/verl 训练、One-Eval 评测、Chroma RAG、Playwright 爬虫、FastAPI WebUI。

---

## 1. Graph 执行框架（核心！）

LoopAI 的全部智能体行为都建模为 **LangGraph StateGraph**。理解 Graph/Node/State 三者关系是理解整个系统的钥匙。

### 1.1 State 数据模型（`loopai/schema/states.py`）

LoopAI 的全局状态 `LoopAIState` 继承自 LangGraph 的 `MessagesState`，所有 Agent 共享这一份状态字典，通过 **reducer（归约器）** 控制字段如何被更新。

```python
# loopai/schema/states.py:1777
class LoopAIState(MessagesState):
    # === 全局属性 ===
    task_id: str
    language: str
    mined_data: str
    max_context_len: str
    prompt_template_dir: str
    output_dir: str

    # === 各 Agent 模块（用 merge_dict reducer 深合并）===
    obtainer: Annotated[Dict[str, Any], merge_dict]
    constructor: Annotated[Dict[str, Any], merge_dict]
    configer: Annotated[Dict[str, Any], merge_dict]
    judger: Annotated[Dict[str, Any], merge_dict]
    analyzer: Annotated[Dict[str, Any], merge_dict]
    trainer: Annotated[Dict[str, Any], merge_dict]
    webcrawler: Annotated[Dict[str, Any], merge_dict]

    bench: Annotated[Any, replace_value]

    # === 图控制属性 ===
    current: str                                          # 当前执行节点名
    next_to: Annotated[str, replace_value]                # 下一跳节点
    automated_query: Annotated[str, replace_value]        # Starter 注入的自动指令
    obtainer_subtask_query: Annotated[str, replace_value] # Obtainer 子任务驱动
    exception: Annotated[str, replace_value]              # 异常标记
```

两个核心 reducer：

```python
# loopai/schema/states.py:11
def replace_value(current, new):
    """非 None 即替换"""
    return new if new is not None else current

def merge_dict(current, new):
    """深合并：两者都是 dict 则递归合并；否则替换。
       支持 Pydantic Model（自动 model_dump(exclude_unset=True)）。"""
    ...
```

设计要点：
- 每个 Agent 的配置是一个嵌套 dict（如 `state["judger"]`、`state["trainer"]`），用 `merge_dict` 保证子图更新只覆盖其产出的字段，不会清掉别人写的字段。
- `next_to` + `current` + `exception` 是图路由的三件套，所有条件边都读 `state["next_to"]`。
- `automated_query` 是 **Starter 在不经过人类 interrupt 的情况下给 LLM 注入下一条"用户话"** 的通道——这是闭环自动衔接的关键机制（后面详解）。

每个 Agent 还有独立的 **Pydantic State 子模型**（`JudgerState`、`AnalyzerState`、`ObtainerState`、`ConstructorState`、`TrainerState`、`WebCrawlerState`、`ConfigerState`），带 `json_schema_extra`（`ui_type`/`ui_group`）用于前端表单自动渲染：

```python
# loopai/schema/states.py:993  JudgerState 示例
class JudgerState(BaseModel):
    eval_model_path: str = Field(default=None, title="评估模型路径",
        json_schema_extra={"ui_type": "file_path", "ui_group": "评估模型"})
    eval_task_type: str = Field(default="code", title="评估任务类型",
        json_schema_extra={"ui_type": "list", "ui_group": "评估模型",
                           "allowed_values": ["code", "text2sql", "general_text"]})
    ...
```

`get_state_config_schema()` 把这些 Pydantic 模型转成 JSON Schema，供 ConfigerAgent 注入到系统提示词里，让 LLM 知道"系统有哪些可配置字段"。

### 1.2 Node 与 ReAct 节点（`loopai/agents/BaseAgent/`）

所有 Agent 继承自抽象基类 `BaseAgent`：

```python
# loopai/agents/BaseAgent/base_agent.py:15
class BaseAgent(ABC):
    def __init__(self, tools, model_name, base_url, api_key, temperature, top_p,
                 max_completion_tokens, prompt_template_dir, checkpointer, store):
        ...
        self.llm_tag = f"{self.role_name}-LLM"
        self.agent_event = AgentEvent()
        self.prompt_loader = PromptLoader(prompt_template_dir)
        if self.model_name is not None:
            self.create_llm_node()

    @property
    @abstractmethod
    def role_name(self) -> str: ...
    @property
    @abstractmethod
    def system_prompt_type(self) -> str: ...
    @property
    @abstractmethod
    def system_prompt_name(self) -> str: ...

    @staticmethod
    def set_current(func):
        """装饰器：自动给 state['current'] 写入 func.__qualname__"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            state = args[0]
            state['current'] = func.__qualname__
            return func(*args, **kwargs)
        return wrapper

    def create_llm_node(self):
        """创建 ChatOpenAI + ReAct_Node（LLM+工具循环子图）"""
        self.llm = ChatOpenAI(base_url=..., model=..., tags=[self.llm_tag])
        self.llm_node = ReAct_Node(model=self.llm, tools=self.tools,
                                   prompt=self.compute_prompt())

    @abstractmethod
    def init_graph(self): ...   # 子类定义节点和边并 compile
    @abstractmethod
    def __call__(self): ...     # 返回编译好的 graph
```

`ReAct_Node`（`loopai/agents/BaseAgent/nodes/react_node.py`）是一个**标准 ReAct 循环子图**：`agent → should_continue → tools → agent → ...`，它本身就是一个 `StateGraph(AgentState)`：

```python
# loopai/agents/BaseAgent/nodes/react_node.py:29
def ReAct_Node(model, tools, prompt, messages_key="messages", ...):
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)   # 调 LLM
    workflow.add_node("tools", tool_node)    # 执行工具
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue,
        {"continue": "tools", "end": END})
    workflow.add_edge("tools", "agent")
    return workflow.compile(...)
```

关键细节：`call_model` 会通过 `get_stream_writer()` 发出 `stream_message_state: start/finished` 的 custom event，前端据此判断"LLM 是否在流式输出"。`max_context_len` 控制传给 LLM 的历史消息窗口（弱模型可设小值增强指令遵循）。

### 1.3 Graph 如何组装：Starter 主图

每个 Agent 的 `__call__` 返回一个编译好的子图，Starter 把这些子图**当作普通节点** add_node 进主图：

```python
# loopai/agents/Starter/starter_agent.py:124
def init_graph(self, **kwargs):
    config_node = ConfigerAgent(...)(**kwargs)     # 返回子图
    judge_node = JudgerAgent(...)(**kwargs)
    analyze_node = AnalyzerAgent(...)(**kwargs)
    train_node = TrainerAgent(...)(**kwargs)
    obtainer_node = ObtainerAgent(...)(**kwargs)
    constructor_node = ConstructorAgent(...)(**kwargs)
    webcrawler_node = WebCrawlerAgent(...)(**kwargs)

    builder = StateGraph(LoopAIState, context_schema=RuntimeContext)
    builder.add_node("query_node", self.query_node)
    builder.add_node("llm_node", self.llm_node)          # ReAct LLM
    builder.add_node("feedback_node", self.feedback_node)
    builder.add_node("route_node", self.route_node)
    builder.add_node("train_node", train_node)
    builder.add_node("obtain_node", obtainer_node)
    builder.add_node("constructor_node", constructor_node)
    builder.add_node("evaluate_node", self.evaluate_node)
    builder.add_node("config_node", config_node)
    builder.add_node("judge_node", judge_node)
    builder.add_node("analyze_node", analyze_node)
    builder.add_node("webcrawler_node", webcrawler_node)
    builder.add_node("end_node", self.end_node)

    builder.set_entry_point("query_node")
    builder.set_finish_point("end_node")
    # query_node / feedback_node / route_node 都是条件边，读 state["next_to"]
    builder.add_conditional_edges("query_node", self.conditional_edge)
    builder.add_edge('llm_node', 'feedback_node')
    builder.add_edge('evaluate_node', 'query_node')
    builder.add_edge('train_node', 'route_node')
    builder.add_edge('obtain_node', 'route_node')
    builder.add_edge('constructor_node', 'route_node')
    builder.add_edge('config_node', 'query_node')
    builder.add_edge('judge_node', 'route_node')
    builder.add_edge('analyze_node', 'route_node')
    builder.add_edge('webcrawler_node', 'route_node')
    builder.add_conditional_edges("feedback_node", self.conditional_edge)
    builder.add_conditional_edges("route_node", self.conditional_edge)

    self.graph = builder.compile(checkpointer=..., store=..., **kwargs)
```

`RuntimeContext` 只有一个字段 `exception_navigate`，子图遇到缺失配置时用 `Command(goto=runtime.context['exception_navigate'], graph=Command.PARENT)` 跳回父图的 `route_node`，再由 `route_node` 转到 `config_node`——这是统一的**异常→配置补全**回流机制。

### 1.4 State 在 Node 间的传递

LangGraph 的核心机制：每个 node 返回一个 dict（或 `Command`），框架用 reducer 把它 merge 进当前 state。所以：
- 普通字段（`next_to`/`current`/`exception`）用 `replace_value`，最后一次写入生效。
- Agent 模块字段（`judger`/`trainer`/...）用 `merge_dict`，多节点增量更新同一块配置。
- `messages` 用 LangGraph 内置 `add_messages` reducer，追加消息。

`Command`（LangGraph 提供）允许节点**同时更新 state 并指定下一跳**，跨子图跳转用 `graph=Command.PARENT`。这是 Configer 补全流程能从子图回到父图的关键。

---

## 2. NL2Optimize 机制（核心！）

"自然语言→优化工作流"的真正实现非常精巧，核心是 **`check_motivation` 工具 + feedback_node 路由**。

### 2.1 check_motivation 工具（`loopai/agents/Starter/tools/check_motivation.py`）

```python
MotivationType = Literal[
    "chat", "train", "judge", "analyze", "obtain", "constructor",
    "webcrawler", "config", "finish",
]

@tool(args_schema=CheckMotivationInput)
def check_motivation(motivation: MotivationType) -> dict:
    """根据用户意图确定下一个工作流节点。"""
    mapping = {
        "train": "train_node", "judge": "judge_node",
        "analyze": "analyze_node", "obtain": "obtain_node",
        "constructor": "constructor_node", "webcrawler": "webcrawler_node",
        "config": "config_node", "finish": "end_node", "chat": "query_node",
    }
    return {"motivation": motivation, "next_to": mapping.get(motivation, "query_node")}
```

Starter 的 LLM（`llm_node`，一个绑定了 `check_motivation` 工具的 ReAct 循环）在听完用户的话后，调用这个工具把意图归一到 9 个枚举之一，工具返回 `next_to`。

### 2.2 feedback_node：工具结果→图路由

```python
# loopai/agents/Starter/starter_agent.py:82
def feedback_node(state):
    messages = state["messages"]
    last_message = messages[-1]                  # LLM 最终回复
    maybe_tool_message = messages[-2]            # 工具返回
    if hasattr(maybe_tool_message, 'tool_call_id'):
        tool_res = json.loads(maybe_tool_message.content)
        state["next_to"] = tool_res.get("next_to", "query_node")
        last_message.content = '<cmd>根据用户指令执行: ' + \
            tool_res.get("motivation", "chat") + '</cmd>\n' + last_message.content
    else:
        state["next_to"] = "query_node"          # 没调工具→闲聊
    return state
```

`feedback_node` 之后是条件边 `conditional_edge`（返回 `state["next_to"]`），于是图就跳到对应 Agent 子图。这就是 NL2Optimize 的完整闭环：**LLM 理解自然语言 → 调工具输出结构化意图 → feedback_node 改写 next_to → 条件边路由**。

### 2.3 闭环自动衔接：automated_query

闭环里 Agent 之间不能依赖人类每次发话。LoopAI 的解法是 `automated_query`：

- 一个 Agent 子图执行完，在 `end_node` 里把"下一步该干什么"写成一条指令塞进 `state["automated_query"]`，并设 `next_to="query_node"`。
- `query_node` 检测到 `automated_query` 非空，就**不 interrupt**，直接把它当用户输入送给 LLM：

```python
# loopai/agents/Starter/starter_agent.py:54
def query_node(state):
    if "automated_query" in state and state["automated_query"]:
        value = state["automated_query"]      # 不打断，自动续跑
    else:
        value = interrupt('input the human query')  # 等人类
    ...
    return {'messages': [{'role': 'user', 'content': value}],
            'automated_query': '', 'next_to': 'llm_node'}
```

例如 Obtainer 完成后：
```python
# loopai/agents/Obtainer/obtainer_agent.py:1001
state["automated_query"] = (
    "请进入数据构造流程：对已下载数据做清洗与格式映射，生成训练可用数据。"
    "请调用 check_motivation，motivation 使用 constructor。"
)
state["next_to"] = "query_node"
```
Constructor 完成后又写 `<cmd>根据用户指令执行: train</cmd>` 引导训练。这样整个 评测→分析→取数→清洗→训练 链条就能自动跑完，**Human-in-the-Loop 只在 `interrupt` 点介入**。

### 2.4 route_node：异常回流

```python
# loopai/agents/Starter/starter_agent.py:104
def route_node(state):
    if state.get("exception") == 'ConfigerError':
        state['exception'] = ""
        state["next_to"] = "config_node"     # 缺配置→去 Configer
    else:
        state["next_to"] = "query_node"      # 正常→回对话
    return state
```

所有 Agent 子图执行完都连到 `route_node`，统一处理"缺配置→补全→恢复"的回流。

---

## 3. 六个核心 Agent 逐一代码分析

> 注：实际有 8 个 Agent（含 Constructor、WebCrawler），README 的"6 个"是把 Obtainer+WebCrawler、Constructor 合并表述。下表按实际代码列出。

### 3.1 Agent 职责总表

| Agent | role_name | 职责 | 输入 | 输出 | 依赖环境 | 源码 |
|-------|-----------|------|------|------|----------|------|
| **StarterAgent** | Starter | Supervisor：对话、意图解析、编排下游 | 用户消息 | next_to 路由 | 核心(Python3.12) | `agents/Starter/starter_agent.py` |
| **ConfigerAgent** | Configer | 配置补全：缺失字段交互式收集 | configer_error | revised_config | 核心 | `agents/Configer/configer_agent.py` |
| **JudgerAgent** | Judger | 评测：生成样例+执行评测 | eval_model_path, eval_problem_path | output_result_path, bench | vLLM(Python3.10) | `agents/Judger/judger_agent.py` |
| **AnalyzerAgent** | Analyzer | 分析：统计+失败模式+诊断报告 | eval_result_path/bench | analysis_summary, suggestions | vLLM(Python3.10) | `agents/Analyzer/analyzer_agent.py` |
| **ObtainerAgent** | Obtainer | 数据获取：任务分解+搜索+下载+RAG | user_query | download_results, subtasks | 核心(+playwright) | `agents/Obtainer/obtainer_agent.py` |
| **ConstructorAgent** | Constructor | 数据构造：后处理+清洗+格式映射 | downloads | mapping_results(output_file) | 核心 | `agents/Constructor/Constructor_agent.py` |
| **WebCrawlerAgent** | WebCrawler | 网页爬取+数据集生成 | query | dataset_sft/pt_path | 核心(+playwright) | `agents/WebCrawler/webcrawler_agent.py` |
| **TrainerAgent** | Trainer | 训练：数据检查+配置生成+执行 | train_input_dataset_path | training_checkpoints, step_losses | LLaMA-Factory/verl(Python3.10) | `agents/Trainer/trainer_agent.py` |

### 3.2 StarterAgent（Supervisor）

主图编排者。核心节点：
- `query_node`：interrupt 等用户输入，或读 `automated_query` 自动续跑。
- `llm_node`：ReAct LLM，绑定 `check_motivation` 工具。
- `feedback_node`：解析工具返回，设 `next_to`。
- `route_node`：异常→config_node；正常→query_node。
- `evaluate_node`：占位节点（直接回 query_node）。

`__call__` 用 `graph.stream(Command(resume=input), subgraphs=True, stream_mode=["updates","messages","custom"])` 流式执行，三类事件分别处理：`messages`（LLM token 流）、`custom`（子图进度）、`updates`（状态变更）。`agent_event` 累积这些信息供前端轮询。

### 3.3 ConfigerAgent（配置补全）

```python
# loopai/agents/Configer/configer_agent.py
class ConfigerAgent(BaseAgent):
    def compute_prompt(self):
        # 把 LoopAIState 注解 + 所有 State 模型的 JSON Schema 注入系统提示
        system_prompt = self.prompt_loader("system", "configer_prompt")
        state_dict = {k: str(v) for k,v in LoopAIState.__annotations__.items()}
        fields_statement = get_state_config_schema()
        return system_prompt.format(state_dict=..., fields_statement=...)
```

图结构：`configer_query_node → configer_llm_node(ReAct) →(条件) confirm_node / configer_query_node`。
- 工具 `check_config(config_data, user_status)`：`user_status="accept"` 时 `confirm=True`，返回 `revised_config`。
- `confirm_node` 把 `revised_config` 写回 state（被 `merge_dict` 合并）。
- 触发场景：任何子图检测到缺失字段→设 `exception='ConfigerError'`→`automated_query` 塞提示→跳 config_node→Configer 收集→回原节点。

### 3.4 JudgerAgent（评测）

支持三种任务类型，图结构按 `eval_task_type` 分流：

```
check_required_fields → check_param_type →(条件)
   ├─ to_vllm_kill → vllm_kill →(条件) → vllm_start → data_format → generate_code →(条件) evaluate →(条件) → END
   └─ to_data_format → data_format → generate_code → ...
generate_code →(条件)
   ├─ code/text2sql → evaluate → ...
   └─ general_text → eval_general_text → END
```

关键代码：
- **vLLM 本地推理集成**（`agents/Judger/utils/oj/vllm_starter.py`）：当 `eval_base_url` 为空时，用 `eval_vllm_env_path` 指定的 Python 解释器在 subprocess 启动 vLLM OpenAI 兼容服务，参数含 `tensor_parallel_size`/`gpu_memory_utilization`/`eval_env_configs`。`vllm_kill_node` 先杀旧进程，`vllm_start_node` 起新进程。
- **评测执行**：code 用 `generate_sample_code`+`evaluate_sample_code`（OJ 沙箱执行），text2sql 用 SQL 执行比对，general_text 用 **One-Eval 的 `DataFlowEvalTool`**（`one_eval.toolkits.dataflow_eval_tool`）。
- **One-Eval 集成**（`nodes/eval_general_text_node.py`）：构建 `BenchAdapter` + `ModelConfig`，在子进程里调 `tool.run_eval(bench, model_config)`，支持 `key1_text_score`/`key2_qa`/`key3_q_choices_a` 等 eval_type。结果写 `output_result_path` 和 `bench`（供 Analyzer）。
- **Trainer 联动**：若 Judger 没给 `eval_model_path`，但 Trainer 已产出 checkpoint，自动选 loss 最低的 checkpoint 评测（`find_best_checkpoint`）。

### 3.5 AnalyzerAgent（分析）

双链路按 `analyze_task_type` 路由：

```
check_required_fields → route_eval →(条件)
   ├─ code/text2sql: eval_model → analyze_result → draw_conclusion → finish
   └─ general_text:  metric_recommend → metric_score → analyze_metric_report → finish
```

- **code/text2sql 链**（`nodes/eval_model.py`、`analyze_result.py`、`draw_conclusion.py`）：
  - `eval_model_node`：用 `LLMJudge`（`utils/llmaj.py`）对失败样本做 LLM-as-Judge 评分，识别 `stage`（assert/runtime/timeout 等）、`tags`、`io_diff`。
  - `analyze_result_node`：抽取失败样例（`pick_failure_examples`），构建 prompt（含 pass_rate、failure_stage_distribution、loc_distribution、kw_distribution），让 LLM 生成诊断。
  - `draw_conclusion_node`：聚合统计（`make_final_json`）、生成背景介绍、改进建议（`build_suggestion_prompt`）、Obtainer 数据缺口建议（`build_obtainer_stats`/`build_obtainer_prompt`，算 fail_bias_tags 指导补数）。
- **general_text 链**（`metric_recommend_node.py`、`metric_score_node.py`、`analyze_metric_report_node.py`）：
  - `metric_recommend_node`：用 `metric_dispatcher` 按 bench_name 推荐指标（exact_match/token_f1/extraction_rate 等），有 `_fallback_metrics` 按 eval_type 兜底。
  - `metric_score_node`：跑指标，写 `metric_eval_results`。
  - `analyze_metric_report_node`：生成结构化 `analysis_summary` + 数据构造建议 `analyze_output_data_plan_text_path`。

输出：`final_report_*.json`、`final_report_*.txt`、`*.suggestions.txt`、`*.obtainer.txt`，存到 `output_dir/<task_id>/analyzer/`。

### 3.6 ObtainerAgent & 数据获取

图结构（多子任务循环）：

```
start_node → task_decomposer_node → websearch_node →(条件)
   ├─ download_node → check_next_task_node →(条件)
   │       ├─ next_task_node → websearch_node (下一任务)
   │       └─ end_node
   └─ check_next_task_node → ...
```

关键逻辑：
- **start_node**：从 messages 里找最后一条 HumanMessage 提取 user_query；调 `ObtainQueryNormalizer`（LLM）把"评测式建议"改写成"数据集请求"；调 `CategoryClassifier` 判定 PT/SFT 类别；初始化搜索/RAG/Kaggle 配置。
- **task_decomposer_node**：调 `TaskDecomposer`（LLM）把用户目标拆成最多 5 个子任务，第一个任务写入 `obtainer_subtask_query` 驱动；每任务独立判 category、清 RAG collection。
- **websearch_node**（`nodes/websearch_node.py`）：用 Tavily/DuckDuckGo 搜索，`RAGManager`（Chroma + OpenAIEmbeddings）存网页内容，`URLSelector` 选 top-k，`DownloadMethodDecision` 决定下载方式（HF/Kaggle/直接下载）。
- **download_node**（`nodes/download_node.py`）：`HFManager`/`KaggleManager`/`PlaywrightManager` 执行下载，结果写 `downloads/`，subtasks 记 `status`。
- **end_node**：生成摘要 AIMessage，设 `automated_query` 引导进入 Constructor。

RAG 实现（`utils/rag_manager.py`）：`OpenAIEmbeddings` + `Chroma` 向量库，`RecursiveCharacterTextSplitter` 切分，`clear_collection` 在每子任务前清空防串。

### 3.7 ConstructorAgent（数据构造）

图结构（双入口）：

```
start_node →(条件 route_after_start)
   ├─ WebCrawler 数据 → data_cleaning_start →(条件) data_cleaning → data_cleaning_end →(条件) mapping → end
   └─ Obtainer 下载   → postprocess_node → data_cleaning_start → ... → mapping → end
```

- **postprocess_node**：`postprocess_version="agent_v2"`（默认）走 `Postprocess` 子 Agent（`agents/Postprocess/`）：router→dispatch（每数据集 LLM 判 related）→merge，导出到 `related_jsonl/`；`"legacy"` 走旧 `postprocess_node`。
- **CleaningSubgraph**（`nodes/filter_node.py`）：数据清洗工具链，含 `cot_filter_tool`、`data_filter_tools`，支持 benchmark 去重、ShareGPT 改写。
- **MappingSubgraph**（`mapping/mapping_subgraph.py`）：格式映射，`list_formats_node`→`inquiry_node`→`preset_format_node`/`custom_format_node`→`llm_mapping_node`/`script_mapping_node`→`confirmation_node`→`summary_node`。`default_mapping_format="alpaca"` 时自动跳过交互。
- **end_node**：写摘要 AIMessage，设 `automated_query` 引导训练（`<cmd>根据用户指令执行: train</cmd>`）。

Constructor 的核心价值：把异构下载/WebCrawler 数据统一清洗+映射成 LLaMA-Factory 可用的 alpaca/sharegpt 格式，输出 `mapping_results.output_file` 自动填给 Trainer。

### 3.8 WebCrawlerAgent（网页爬取+数据集生成）

线性图：`start_node → crawl_node → webcrawler_dataset_node → end_node`。

- `crawl_node`（`nodes/crawl_node.py`）：`CrawlOrchestrator`（`utils/crawl_orchestrator.py`）编排，`PlaywrightManager` 多页并发爬取，`ContentAnalyzer`（LLM）打相关性分，`LogManager` 记录。
- `webcrawler_dataset_node`（`nodes/webcrawler_dataset_node.py`）：`DatasetGenerator`（LLM）把网页内容生成 SFT/PT 记录，`DatasetMapping` 映射成 `jsonl_sft`/`jsonl_pt`，输出 `dataset_sft_path`/`dataset_pt_path`。

配置（`WebCrawlerState`）：默认用 DeepSeek，支持 `max_pages`/`crawl_depth`/`max_links_per_page`/`concurrent_pages`/`min_text_length`/`min_relevance_score` 等爬取策略参数。

### 3.9 TrainerAgent（训练）

图结构：

```
check_required_fields → data_check →(条件)
   ├─ config_generation →(条件) training_execution → end
   └─ end
```

- **check_required_fields**：必填 `train_framework`/`train_input_dataset_path`/`train_input_task_description`/`train_input_config_template_path`/`train_input_model_name`；llamafactory 还需 `llamafactory_dir`。**自动从 Obtainer/Constructor 的 `mapping_results.output_file` 填 `train_input_dataset_path`**。
- **data_check_node**（`utils/data_checker.py`）：验证数据集格式符合 LLaMA-Factory 要求。
- **config_generation_node**（`utils/config_generator.py`）：LLM 根据任务描述+模板生成 YAML 训练配置（学习率/epoch/LoRA rank 等）。
- **training_execution_node**（`nodes/training_execution_node.py`）：核心是 **`TaskManager`**（`utils/task_manager.py`）——本地异步任务管理，把 LLaMA-Factory/verl 当 subprocess 启动，流式读日志，30s 轮询状态，解析 `TrainingLogParser` 提取进度/step/loss。
  - 训练完扫描 checkpoint 目录、读 `trainer_log.jsonl` 提取 `training_step_losses`。
  - 这些 checkpoint/loss 信息会被 Judger 复用（选最佳 checkpoint 评测），形成 **训练→评测** 闭环。

环境隔离：`llamafactory_env_path`/`verl_env_path` 指向独立 conda 环境的 bin 目录，`TaskManager` 用 subprocess 调对应框架的 CLI。

---

## 4. 配置系统

### 4.1 starter.yaml 全景（`examples/config/starter.yaml`）

```yaml
system:                         # Starter 模型 + 全局凭证
  api_port: 8855
  starter_api_key: "sk-..."
  starter_model_path: "gpt-4o-mini"
  starter_model_name: "gpt-4o-mini"
  starter_base_url: "http://.../v1"
  llamafactory_dir: "..."
  llamafactory_env_path: ".../bin/"
  CUDA_VISIBLE_DEVICES: "0,1"
  swanlab_api_key: ""
  tavily_api_key: ""            # 搜索引擎
  kaggle_username: "..."
  kaggle_key: ""

default_states:                 # 各 Agent 默认配置
  task_id: "default"
  language: "en"
  prompt_template_dir: "./loopai/common/prompts"
  output_dir: "./outputs"

  judger:                       # 评测模型/任务类型/vLLM 参数
    eval_model_path: "/home/.../Qwen2.5-14B-Instruct/"
    eval_base_url: "http://127.0.0.1:8911/v1"
    eval_problem_path: "./data/human-eval-...jsonl"
    eval_batch_size: 10
    eval_task_type: code/text2sql/general_text
    eval_vllm_tensor_parallel_size: 2
    eval_vllm_gpu_memory_utilization: 0.9

  analyzer:                     # 分析模型/批量/采样
    analyze_model_path: ...
    analyze_base_url: ...
    output_brief: true
    analyze_sampling_top_k: 5
    analyze_batch_size: 20

  obtainer:                     # 数据获取模型/搜索/爬取/RAG/Kaggle
    model_path/base_url/api_key
    search_engine: tavily
    max_urls: 6
    category: SFT/PT
    default_mapping_format: alpaca

  webcrawler:                   # 爬虫模型/策略/输出
    deepseek_api_key/tavily_api_key
    max_pages: 10000
    crawl_depth: 3
    sft_mapping_format: jsonl_sft

  constructor:                  # 后处理/清洗/映射
    postprocess_version: agent_v2
    benchmark_pool_size: 500
    default_mapping_format: alpaca
    max_samples_before_cleaning: 300

  trainer:                      # 训练框架/数据/模型
    train_framework: llamafactory
    llamafactory_dir/env_path
    train_input_dataset_path: ...
    train_input_model_name: ...
    train_input_config_template_path: ./api/examples/bird.yaml
```

### 4.2 配置优先级与流转

1. `starter.yaml` → 启动时读入 `default_states`。
2. WebUI 模式：`StarterConfig`/`TaskModel`（Tortoise ORM，SQLite）持久化，`init_manager` 加载。
3. 运行时 state 里的值 > yaml 默认值。
4. 子图 `check_required_fields` 检测缺失 → ConfigerAgent 交互补全 → `merge_dict` 合并回 state。
5. Pydantic State 模型既做校验又做前端表单 schema（`ui_type`/`ui_group`）。

### 4.3 多环境配置

| 环境 | Python | 用途 | 配置字段 |
|------|--------|------|----------|
| loopai (核心) | 3.12 | Starter/Configer/Obtainer/Constructor/WebCrawler/API | `pip install -e .` |
| loopai-vllm | 3.10 | Judger/Analyzer 本地推理 | `judger.eval_vllm_env_path` |
| loopai-llamafactory | 3.10 | Trainer (LLaMA-Factory) | `trainer.llamafactory_env_path` |
| loopai-verl | 3.10 | Trainer (verl) | `trainer.verl_env_path` |

通信方式：**subprocess + OpenAI 兼容 API**。vLLM 由 Judger 用 subprocess 起 OpenAI 服务，Trainer 用 subprocess 调 LLaMA-Factory CLI，Analyzer 通过 `analyze_base_url` 调 vLLM 服务。核心环境不直接 import vllm/llamafactory。

---

## 5. WebUI API 服务

### 5.1 入口与启动

`api/start.py`：读 `starter.yaml`，切到 LLaMA-Factory 目录，用 `subprocess.Popen` 启 `uvicorn api.app.main:app --port 8855`，设 PYTHONPATH 含项目目录和 LLaMA-Factory 目录。

前端 dist 通过 `scripts/download_ui_release.py` 下载到 `api/dist/`，FastAPI 用 `StaticFiles` 挂载 `/assets`，根路径返回 `index.html`。

### 5.2 API 端点（`api/app/controllers/`）

| 路由 | 方法 | 功能 |
|------|------|------|
| `/starter/agent/start` | POST | 启动 Agent（按 task_id 加载配置，起 StarterManager） |
| `/starter/agent/input` | POST | 发送用户输入 |
| `/starter/agent/stop` | POST | 停止并保存 state |
| `/starter/agent/status` | GET | 轮询状态（含 running_tasks/interrupt_value/stream_message） |
| `/starter/agent/message/stream` | GET(SSE) | 流式消息 |
| `/starter/agent/hardware_usage` | GET | GPU/CPU/内存 |
| `/config/...` | - | 配置 CRUD |
| `/task/...` | - | 任务管理 |
| `/train/...` | - | 训练任务状态/日志 |
| `/resource/...` | - | 资源 |

### 5.3 StarterManager + Worker（`api/app/utils/starter/`）

`StarterManager` 在独立进程跑 `agent_worker`（`worker.py`），通过两个 Queue 通信：
- `cmd_q`（主→Agent）：START/INPUT/STOP。
- `state_q`（Agent→主）：状态快照（`extract_state` 提取 running/current/interrupt_value/stream_message/custom_info）。

`agent_worker` 内部 `sg = StarterAgent(...); sg.init_graph(); sg.start(default_state, config)`，然后循环：等 interrupt → 把状态推 state_q → 等输入 → `sg(query, config=config)` 流式跑 → 推状态。

---

## 6. 记忆系统（`loopai/memory/`）

### 6.1 两种实现

- **内存版**（默认，`saver.py`/`store.py`）：`InMemorySaver()` + `InMemoryStore()`，进程内，重启丢失。
- **SQLite 持久化版**（`sqlite_tools/saver.py`）：`AsyncSqliteSaver`，基于 **Tortoise ORM + aiosqlite**，实现 LangGraph `BaseCheckpointSaver` 接口。

### 6.2 AsyncSqliteSaver 关键方法

```python
# loopai/memory/sqlite_tools/saver.py
class AsyncSqliteSaver(BaseCheckpointSaver[str]):
    async def aget_tuple(config) -> CheckpointTuple  # 取最新/指定 checkpoint
    async def alist(config, filter, before, limit)   # 列 checkpoints
    async def aput(config, checkpoint, metadata, new_versions)  # 存
    async def aput_writes(config, writes, task_id)   # 存中间 writes
    async def adelete_thread(thread_id)              # 删线程
```

表结构（`db_models/base.py`）：`CheckpointModel`（thread_id/checkpoint_ns/checkpoint_id/parent_checkpoint_id/type/checkpoint/metadata）+ `WriteModel`（thread_id/checkpoint_id/task_id/idx/channel/type/value）。

### 6.3 记忆在闭环中的作用

LangGraph checkpointer 在**每个 super-step 自动保存** state 快照。配合 `thread_id`（终端模式用 "1"，WebUI 用 task_id），实现：
- **中断恢复**：`interrupt` 后用户可随时回来继续（`> $resume$`）。
- **Human-in-the-Loop**：长时间训练后回来继续对话。
- **跨会话经验**：同一 thread_id 的历史 state 可被 `alist` 检索。

注意：LoopAI 的"记忆"目前主要是**图状态持久化**（checkpoint），不是跨任务的"经验积累知识库"。Postprocess 子 Agent 有个 `PostprocessMemoryManager`（`agents/Postprocess/memory/manager.py`）用 LangGraph store 做更细粒度的记忆，但范围有限。

---

## 7. 完整闭环流程图

下面是从用户输入到模型改进的完整数据流（含所有 Agent 和关键状态字段）：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            用户自然语言输入                              │
│                  "帮我提升模型的代码生成能力"                            │
└──────────────────────────────┬──────────────────────────────────────────┘
                               ▼
                     ┌─────────────────────┐
                     │  StarterAgent       │
                     │  query_node         │ ← interrupt 等输入 / automated_query 自动续跑
                     │  ↓                  │
                     │  llm_node (ReAct)   │ ← 绑定 check_motivation 工具
                     │  ↓                  │
                     │  feedback_node      │ ← 解析工具返回 → state["next_to"]
                     └──────────┬──────────┘
                                │ next_to
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
   ┌──────────────┐     ┌──────────────┐      ┌──────────────┐
   │ JudgerAgent  │     │AnalyzerAgent │      │ ObtainerAgent│
   │ (评测)       │     │ (分析)       │      │ (取数)       │
   │              │     │              │      │ start→decomp │
   │ check_fields │     │ check_fields │      │ →websearch   │
   │ →vllm_kill   │     │ →route_eval  │      │ →download    │
   │ →vllm_start  │     │  ├code链:    │      │ →check_next  │
   │ →data_format │     │  eval_model  │      │ →next_task   │
   │ →generate    │     │  →analyze    │      │ (循环)       │
   │ →evaluate    │     │  →conclusion │      │ →end         │
   │ /eval_gen_txt│     │  └gen_text链:│      │              │
   │              │     │  metric_rec  │      │ RAG(Chroma)  │
   │ vLLM子进程   │     │  →score      │      │ HF/Kaggle    │
   │ One-Eval     │     │  →report     │      │ Playwright   │
   └──────┬───────┘     └──────┬───────┘      └──────┬───────┘
          │ output_result_path │ analysis_summary    │ download_results
          │ bench              │ suggestions         │ subtasks
          ▼                     ▼                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                       route_node (异常→config_node)              │
   └──────────────────────────────┬───────────────────────────────────┘
                                  ▼
                         ┌────────────────┐
                         │  query_node    │ ← automated_query 自动引导下一步
                         └──────┬─────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │ConstructorAg │ │WebCrawlerAg  │ │TrainerAgent  │
        │ (数据构造)   │ │ (网页爬取)   │ │ (训练)       │
        │              │ │              │ │              │
        │ start→route  │ │ start→crawl  │ │ check_fields │
        │ ├postprocess │ │ →dataset_gen │ │ →data_check  │
        │ │ (v2子Agent)│ │ →end         │ │ →config_gen  │
        │ ├cleaning    │ │              │ │ →training    │
        │ └mapping     │ │ Playwright   │ │   (TaskMgr)  │
        │ →end         │ │ LLM生成SFT/PT│ │ →end         │
        │              │ │              │ │              │
        │ 输出:        │ │ 输出:        │ │ 输出:        │
        │ output_file  │ │ sft/pt_path  │ │ checkpoints  │
        │ (alpaca格式) │ │              │ │ step_losses  │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                │                │
               └────────────────┼────────────────┘
                                ▼
                    ┌───────────────────────┐
                    │  route_node → query   │
                    │  automated_query 引导 │
                    │  "请进入训练..."       │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  TrainerAgent 执行    │
                    │  → checkpoints        │
                    │  → step_losses        │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  automated_query 引导 │
                    │  "请评测新模型..."     │
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  JudgerAgent 复跑评测 │ ← 用 best checkpoint
                    │  (find_best_checkpoint)│
                    └───────────┬───────────┘
                                ▼
                    ┌───────────────────────┐
                    │  AnalyzerAgent 再分析 │ ← 对比改进前后
                    └───────────┬───────────┘
                                ▼
                        闭环继续 / 用户介入
```

**Human-in-the-Loop 介入点**：
1. `query_node` 的 `interrupt`（无 automated_query 时等用户）。
2. `ConfigerAgent` 的 `configer_query_node`（缺配置时交互收集）。
3. `MappingSubgraph` 的格式确认（`default_mapping_format` 为空时）。
4. 任何 Agent 执行后用户可在 WebUI 介入打断。

---

## 8. 关键源码文件索引

| 模块 | 文件 | 作用 |
|------|------|------|
| 状态 | `loopai/schema/states.py` | LoopAIState + 各 Agent State 模型 + reducer |
| 事件 | `loopai/schema/events.py` | AgentEvent/StreamEvent（流式通信） |
| 基类 | `loopai/agents/BaseAgent/base_agent.py` | BaseAgent 抽象基类 |
| ReAct | `loopai/agents/BaseAgent/nodes/react_node.py` | LLM+工具循环子图 |
| Starter | `loopai/agents/Starter/starter_agent.py` | 主图编排 |
| 意图 | `loopai/agents/Starter/tools/check_motivation.py` | NL2Optimize 核心 |
| Configer | `loopai/agents/Configer/configer_agent.py` | 配置补全 |
| Configer | `loopai/agents/Configer/tools/check_config.py` | 配置确认工具 |
| Judger | `loopai/agents/Judger/judger_agent.py` | 评测图 |
| Judger | `loopai/agents/Judger/nodes/eval_general_text_node.py` | One-Eval 通用评测 |
| Judger | `loopai/agents/Judger/utils/oj/vllm_starter.py` | vLLM 子进程启动 |
| Analyzer | `loopai/agents/Analyzer/analyzer_agent.py` | 分析图（双链路） |
| Analyzer | `loopai/agents/Analyzer/nodes/draw_conclusion.py` | 报告生成+建议 |
| Analyzer | `loopai/agents/Analyzer/nodes/metric_recommend_node.py` | 指标推荐 |
| Analyzer | `loopai/agents/Analyzer/eval_metrics/` | One-Eval 指标库 |
| Obtainer | `loopai/agents/Obtainer/obtainer_agent.py` | 取数图（多任务循环） |
| Obtainer | `loopai/agents/Obtainer/utils/rag_manager.py` | Chroma RAG |
| Obtainer | `loopai/agents/Obtainer/utils/hf_manager.py` | HuggingFace 下载 |
| Obtainer | `loopai/agents/Obtainer/utils/kaggle_manager.py` | Kaggle 下载 |
| Constructor | `loopai/agents/Constructor/Constructor_agent.py` | 数据构造图 |
| Constructor | `loopai/agents/Constructor/mapping/mapping_subgraph.py` | 格式映射子图 |
| Postprocess | `loopai/agents/Postprocess/postprocess_agent.py` | v2 后处理子 Agent |
| WebCrawler | `loopai/agents/WebCrawler/webcrawler_agent.py` | 爬虫图 |
| WebCrawler | `loopai/agents/WebCrawler/utils/crawl_orchestrator.py` | 爬取编排 |
| Trainer | `loopai/agents/Trainer/trainer_agent.py` | 训练图 |
| Trainer | `loopai/agents/Trainer/nodes/training_execution_node.py` | 训练执行 |
| Trainer | `loopai/agents/Trainer/utils/task_manager.py` | 本地任务管理 |
| Trainer | `loopai/agents/Trainer/utils/training_log_parser.py` | 日志解析 |
| 记忆 | `loopai/memory/saver.py` / `store.py` | 内存版 |
| 记忆 | `loopai/memory/sqlite_tools/saver.py` | SQLite 持久化 |
| API | `api/app/main.py` | FastAPI 应用 |
| API | `api/app/controllers/starter.py` | Agent 控制端点 |
| API | `api/app/utils/starter/worker.py` | 多进程 Worker |
| 配置 | `examples/config/starter.yaml` | 完整配置示例 |
| 终端 | `examples/scripts/run_starter.py` | 终端模式入口 |

---

## 9. 对 SRS 项目的深度应用价值

SRS 一致性检测项目当前痛点：**假阳性优化是手工的**——跑 `srs_consistency_checker_v2.py` → 看 `consistency_reports/` → 人工调规则/prompt → 重跑 `srs_eval.py` 对齐 Gold Standard。这正是一个**典型的"评测→分析→改进"闭环**，LoopAI 的框架可以直接套用，把人工环节自动化。

### 9.1 总体思路：把 SRS 检测系统变成 LoopAI 的"被优化对象"

LoopAI 原生面向"大模型优化"（评测模型输出→分析失败→取训练数据→微调）。SRS 项目的"模型"是**一致性检测引擎**（规则库+约束提取 prompt+Z3 求解），"训练"是**优化规则阈值/约束提取 prompt**（不一定是梯度训练，而是 prompt/规则迭代）。两者闭环结构同构：

| LoopAI 原生 | SRS 适配 |
|-------------|----------|
| 被评测的 LLM | SRS 一致性检测引擎 (`srs_consistency_checker_v2.py`) |
| 评测任务 (code/text2sql) | 三层一致性检测 (语法/语义/逻辑) |
| 评测集 (human-eval) | Gold Standard (battery/compiler/scheduler) |
| pass@k 指标 | P/R/F1 (`srs_eval.py`) |
| 失败模式 (stage/tags) | 假阳性类型 (规则误触/prompt 误提/Z3 误判) |
| 训练数据集 | 对抗样本/规则补丁/prompt 改写 |
| 微调 (LLaMA-Factory) | 规则库更新/prompt 迭代 (`knowledge/gjb_438c_rules.json`) |

### 9.2 JudgerAgent 如何调用 srs_eval.py

JudgerAgent 的 `eval_general_text_node` 已经集成 One-Eval 的 `DataFlowEvalTool`，其 `bench_dataflow_eval_type` 支持 `key2_qa` 等。SRS 适配方案：

**方案 A（推荐）：包装 srs_eval.py 为 One-Eval bench**

`DataFlowEvalTool.run_eval(bench, model_config)` 的 `bench` 是 `BenchAdapter`，`model_config` 是 `ModelConfig`。SRS 的"模型"不是 LLM 而是检测引擎，需把检测引擎包装成"可被调用的预测器"：

```python
# 伪代码：srs_bench_adapter.py
class SRSConsistencyBench(BenchAdapter):
    """把 SRS 一致性检测包装成 One-Eval bench"""
    bench_name = "srs_consistency"
    bench_dataflow_eval_type = "key2_qa"  # input=文档, pred=检测结果, target=Gold

    def run_model(self, inputs):
        # 调 srs_consistency_checker_v2.py 跑每份 SRS
        # 返回 [{task_id, pred_issues, ...}]
```

然后在 `starter.yaml` 配置：
```yaml
judger:
  eval_task_type: general_text
  bench_dataflow_eval_type: key2_qa
  eval_problem_path: "./data/gjb_438c/gold_standard/"  # 3 份 Gold SRS
  key_mapping:
    input_question_key: "doc_path"      # SRS 文档路径
    input_pred_key: "pred_issues"       # 检测引擎输出
    input_target_key: "gold_issues"     # Gold Standard 标注
```

Judger 会自动跑检测引擎、收集结果、写 `output_result_path` 和 `bench`。

**方案 B（更轻量）：扩展 eval_task_type 增加 "srs_consistency"**

在 `JudgerAgent.generate_node` 的 match 里加一个 case：
```python
case "srs_consistency":
    from srs_consistency_checker_v2 import run_check
    from srs_eval import evaluate
    res = run_check(state)            # 跑检测
    eval_result = evaluate(res, gold) # 跑评测
    state["judger"]["output_result_path"] = eval_result["result_path"]
    goto = "evaluate"
```

这样无需 One-Eval，直接复用现有 `srs_eval.py`。

### 9.3 AnalyzerAgent 如何分析假阳性模式

AnalyzerAgent 的 `draw_conclusion_node` 已经在做"失败模式识别"。SRS 假阳性分析可直接复用其统计框架：

**复用 `enhance_stats_with_oj` / `build_obtainer_stats` 的逻辑**：
- `failure_stage_distribution` → **假阳性按层分布**（语法层/语义层/逻辑层各多少假阳性）。
- `failure_tag_top` → **假阳性按规则类型分布**（如 GJB 规则 R-xxx 误触、约束类型误提）。
- `fail_bias_tags` → **哪些规则/约束类型假阳性偏置最严重**，指导优先修复。
- `common_fail_io_snippets` → **典型假阳性样例**（输入文档片段+误报问题+Gold 标注）。

适配做法：让 `srs_eval.py` 输出的每条假阳性记录带上 `judge.stage`（语法/语义/逻辑）和 `judge.tags`（规则ID/约束类型），Analyzer 的统计代码就能直接跑。

`build_suggestion_prompt` 生成的改进建议会变成："主要假阳性来自语义层 R-xxx 规则误触，建议放宽阈值 X→Y"。`build_obtainer_prompt` 生成的数据缺口建议会变成："需补充 N 份含边界条件的 SRS 对抗样本"。

### 9.4 ObtainerAgent 如何用 AgentFlow 合成对抗样本

ObtainerAgent 原生做"下载公开数据集"。SRS 场景的"取数"应是**合成对抗样本**——专门触发假阳性的 SRS 片段。这里需扩展 Obtainer 的取数策略：

**方案：新增 "synth" 下载方式**

Obtainer 的 `DownloadMethodDecision`（`utils/download_method_decision.py`）当前决定 HF/Kaggle/直接下载。增加 `synth` 类型，调 LLM 合成：

```python
# 伪代码：srs_synth_node.py
def synth_adversarial_srs(state):
    """根据 Analyzer 的假阳性模式，合成对抗 SRS 片段"""
    false_positive_patterns = state["analyzer"]["analysis_summary"]["fail_bias_tags"]
    prompt = f"""
    已知以下规则产生假阳性: {false_positive_patterns}
    当前规则: {load_rules('knowledge/gjb_438c_rules.json')}
    请合成 10 份 SRS 片段，它们应满足:
    1. 语法上合规（不触发语法层）
    2. 但当前规则会误报 {false_positive_patterns}
    3. Gold 标注应为: 无问题
    输出 alpaca 格式。
    """
    samples = llm.invoke(prompt)
    # 写入 downloads/srs_synth/
```

配合 ConstructorAgent 的清洗+映射，自动生成训练/验证集。这比手工扩展 Gold Standard 高效得多。

### 9.5 TrainerAgent 如何优化检测规则/约束提取 prompt

SRS 的"训练"不是梯度微调，而是**规则库/prompt 迭代**。两种路径：

**路径 1：prompt 迭代（把约束提取 prompt 当"模型"）**

约束提取用 GLM-5 API（`srs_constraint_extract.py`）。把"约束提取 prompt"视为可训练参数，TrainerAgent 的 `config_generation_node` 改为"用 LLM 根据假阳性分析改写 prompt"：

```python
# 伪代码：srs_prompt_trainer.py
def generate_improved_prompt(state):
    false_positives = state["analyzer"]["analysis_summary"]["representative_failure_samples"]
    current_prompt = load_prompt("tools/srs_constraint_extract_prompts/")
    improved = llm.invoke(f"""
    当前约束提取 prompt 产生以下假阳性: {false_positives}
    当前 prompt: {current_prompt}
    请改写 prompt 以避免这些假阳性，保持不漏检。
    """)
    save_prompt(improved, "tools/srs_constraint_extract_prompts/v2/")
```

**路径 2：规则阈值调优（把规则库当"模型"）**

`knowledge/gjb_438c_rules.json` 的规则带阈值/权重。TrainerAgent 用 LLM 或网格搜索调阈值：

```python
# 伪代码：srs_rule_trainer.py
def tune_rule_thresholds(state):
    eval_result = state["judger"]["output_result_path"]
    # 用 Z3/网格搜索找使 F1 最大的阈值组合
    best_thresholds = grid_search(eval_result, rule_space)
    update_rules("knowledge/gjb_438c_rules.json", best_thresholds)
```

两种路径都复用 TrainerAgent 的 `data_check → config_generation → training_execution` 三段式：data_check 验证假阳性数据可用，config_generation 生成改进方案，training_execution 执行改进并产出新版规则/prompt。`training_checkpoints`/`training_step_losses` 对应"规则版本号"和"F1 提升曲线"。

### 9.6 完整的 SRS 假阳性优化闭环方案设计

```
┌──────────────────────────────────────────────────────────────────────┐
│  用户: "降低 SRS 一致性检测的假阳性率"                                │
└────────────────────────────┬─────────────────────────────────────────┘
                             ▼
                    ┌────────────────┐
                    │ StarterAgent   │ check_motivation → "judge"
                    └───────┬────────┘
                            ▼
                    ┌─────────────────────────────────────────┐
                    │ JudgerAgent (SRS 适配)                  │
                    │  eval_task_type: "srs_consistency"      │
                    │  1. 跑 srs_consistency_checker_v2.py    │
                    │     对 gold_standard/ 3 份 SRS          │
                    │  2. 跑 srs_eval.py 算 P/R/F1            │
                    │  3. 输出每条假阳性带 stage(层)/tags(规则)│
                    │  → output_result_path, bench            │
                    └───────┬─────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────┐
                    │ AnalyzerAgent (SRS 适配)                │
                    │  1. 假阳性按层分布 (语法/语义/逻辑)     │
                    │  2. 假阳性按规则分布 (R-xxx 误触 Top)   │
                    │  3. fail_bias_tags: 哪些规则偏置最重    │
                    │  4. LLM 生成诊断: "语义层 R-xxx 阈值过严"│
                    │  5. 数据缺口建议: "需 N 份边界条件 SRS" │
                    │  → analysis_summary, suggestions        │
                    └───────┬─────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────┐
                    │ ObtainerAgent (SRS 适配)                │
                    │  DownloadMethod: "synth"                │
                    │  1. 根据 fail_bias_tags 合成对抗 SRS    │
                    │     (应合规但触发假阳性的片段)          │
                    │  2. 也可从 srs_collection/359 份里检索  │
                    │     相似边界 case (RAG)                 │
                    │  → downloads/srs_synth/                 │
                    └───────┬─────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────┐
                    │ ConstructorAgent (复用)                 │
                    │  1. postprocess: 清洗合成样本           │
                    │  2. mapping: 映射成 {doc, gold_issues}  │
                    │     格式供评测                          │
                    │  → 扩展后的 Gold Standard               │
                    └───────┬─────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────┐
                    │ TrainerAgent (SRS 适配)                 │
                    │  train_framework: "srs_rule_tune"       │
                    │  1. data_check: 验证对抗样本可用        │
                    │  2. config_generation: LLM 改写         │
                    │     - 约束提取 prompt (避免假阳性)      │
                    │     - 规则阈值 (网格搜索最优)           │
                    │  3. training_execution: 更新            │
                    │     - knowledge/gjb_438c_rules.json     │
                    │     - tools/srs_constraint_extract*.py  │
                    │  → rules_v2.json, prompt_v2             │
                    └───────┬─────────────────────────────────┘
                            ▼
                    ┌─────────────────────────────────────────┐
                    │ 回到 JudgerAgent 复跑评测               │
                    │  (用 rules_v2 + prompt_v2)              │
                    │  对比 F1 提升 → 决定是否继续迭代        │
                    └─────────────────────────────────────────┘
```

### 9.7 落地步骤建议

1. **最小闭环（1-2 周）**：先做 Judger+Analyzer 适配。写一个 `srs_judger_node.py` 包装 `srs_consistency_checker_v2.py`+`srs_eval.py`，让 Analyzer 的统计代码直接吃 `srs_eval` 输出。验证能自动产出"假阳性分布报告"。
2. **取数闭环（2-3 周）**：扩展 Obtainer 的 `synth` 下载方式，用 GLM-5 合成对抗 SRS。先用 `srs_collection/` 现有 359 份做 RAG 检索，再合成。
3. **训练闭环（2-3 周）**：实现 `srs_rule_trainer`（阈值网格搜索）和 `srs_prompt_trainer`（LLM 改写 prompt）。先做规则阈值（确定性强），再做 prompt 迭代。
4. **全闭环集成（1 周）**：配 `starter.yaml` 的 SRS 专用 profile，用终端模式 `run_starter.py` 跑通"降假阳性"全流程。
5. **WebUI（可选）**：起 FastAPI，用 LoopAI 自带前端观察闭环迭代曲线。

### 9.8 关键收益

- **自动化假阳性优化**：从手工调规则变成自然语言驱动的自动迭代。
- **可复现**：LangGraph checkpointer 保存每轮 state，规则/prompt 版本可回溯。
- **可扩展 Gold Standard**：Obtainer 合成对抗样本自动扩充评测集，解决 Gold Standard 只有 3 份的瓶颈。
- **多策略对比**：闭环可并行跑"调阈值"vs"改 prompt"两条路径，用 F1 选优。
- **论文素材**：闭环优化过程本身就是论文的"自优化系统"实验，LoopAI 提供框架，SRS 提供领域场景，二者结合是完整的"自动化检测优化"贡献。

---

## 10. 局限与注意事项

1. **记忆系统偏弱**：LoopAI 的"记忆"主要是图状态持久化，缺乏跨任务的"经验知识库"。SRS 闭环里"上一轮假阳性模式"不会自动影响下一轮取数策略，需自己加 `PostprocessMemoryManager` 式的 store 用法。
2. **vLLM 依赖重**：Judger/Analyzer 的本地推理强绑 vLLM，SRS 场景若用 GLM-5 API 而非本地模型，需绕过 vllm_starter 逻辑（设 `eval_base_url` 跳过本地启动）。
3. **训练框架假设**：TrainerAgent 假设"训练=微调 LLM"。SRS 的"训练=改规则/prompt"需自定义 `train_framework`，`TaskManager` 的 subprocess 模型要重写。
4. **One-Eval 耦合**：general_text 评测强依赖 `one_eval` 包（`setup.py` 里 `one-eval @ git+...`），SRS 评测用 `srs_eval.py`，需选方案 A（包装成 bench）或方案 B（加 eval_task_type）。
5. **recursion_limit**：Obtainer 多任务循环 + 子图嵌套容易触 LangGraph 递归上限，`run_starter.py` 默认设 100，复杂闭环需调高。
6. **配置复杂度**：8 个 Agent × 几十个字段，`starter.yaml` 学习成本高。SRS 适配建议先写一个精简的 `srs_starter.yaml` 只含必要字段。

---

## 附录：核心依赖（`setup.py`）

- 图框架：`langgraph>=0.6.7`、`langchain>=0.3.27`、`langchain-openai`、`langchain-community`、`langchain-text-splitters`
- RAG：`chromadb>=0.4.0`
- 数据：`huggingface_hub`、`datasets`、`kaggle`、`kagglehub`、`playwright`
- 评测：`one-eval @ git+https://github.com/OpenDCAI/One-Eval.git@main`、`open-dataflow==1.0.10`
- 训练：`vllm>=0.4.0`（LLaMA-Factory/verl 单独装）
- Web：`fastapi`、`uvicorn`、`tortoise-orm`、`aiosqlite`
- 代码解析：`tree_sitter` + 16 种语言（Python/JS/Java/C++/C/Go/Rust/...）—— 用于 Judger 的 code 评测和 Constructor 的代码清洗
- 其他：`omegaconf`（yaml）、`pydantic`、`rich`、`tenacity`、`mcp`、`psutil`、`func-timeout`

Python 要求 `>=3.12`（核心环境）。
