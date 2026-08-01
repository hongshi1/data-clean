# DataFlow Core 源码架构深度解析

> 知识笔记 · 代码级分析
> 源码位置: `/Users/gexuancheng/Desktop/research2/data_clean/dataflow_repos/DataFlow/`
> 分析版本: commit `781f4734` (DeepWiki 索引时间 2026-03-07)

---

## 0. 总览

DataFlow 是北京大学 Data-Centric AI Group 的开源 LLM 数据准备系统 (GitHub 7.1k stars),定位为 DataFlow 生态的 **L2 数据资产工厂层核心**。它通过五大抽象 (Operator / Pipeline / LLMServing / Storage / Prompt) 将数据清洗工作流变成可复现、可复用、可分享的 pipeline,并采用类 PyTorch 的 `Pipeline → Operator → Prompt` 三层结构。

核心理念: **编译-执行分离**。Pipeline 先"空跑"一遍 `forward()` 记录算子调用、构建依赖图、验证 key 兼容性(编译期),再顺序执行各算子并自动管理存储步进与 GPU 资源(执行期)。这一设计让错误在昂贵计算前被捕获。

### 五大核心抽象一览

| 抽象 | 基类 | 源码位置 | 关键方法 | 职责 |
|------|------|----------|----------|------|
| OperatorABC | `OperatorABC` | `dataflow/core/operator.py:5-15` | `run()` | 数据处理单元(计算) |
| PipelineABC | `PipelineABC` | `dataflow/pipeline/Pipeline.py:18-42` | `forward()` / `compile()` | 算子编排(调度) |
| LLMServingABC | `LLMServingABC` | `dataflow/core/llm_serving.py:5-35` | `generate_from_input()` | LLM 推理(后端) |
| DataFlowStorage | `DataFlowStorage` | `dataflow/utils/storage.py:14-68` | `read()/write()/step()` | 数据流转(存储) |
| PromptABC | `PromptABC` | `dataflow/core/prompt.py:6-16` | `build_prompt()` | 提示词模板(协议) |

> 类型别名见 `dataflow/core/__init__.py:8-9`:
> `OPERATOR_CLASSES = Union[OperatorABC, WrapperABC]`、`LLM_SERVING_CLASSES = LLMServingABC`。

---

## 1. 项目结构

```
DataFlow/
├── dataflow/                        # 核心包
│   ├── core/                        # ★ 五大抽象基类
│   │   ├── __init__.py              # 类型别名导出 (OPERATOR_CLASSES / LLM_SERVING_CLASSES)
│   │   ├── operator.py              # OperatorABC 基类 + get_operator()
│   │   ├── llm_serving.py           # LLMServingABC 基类
│   │   ├── prompt.py                # PromptABC / DIYPromptABC + prompt_restrict 装饰器
│   │   └── wrapper.py               # WrapperABC 基类 (Ray 分布式算子用)
│   ├── operators/                   # ★ 算子库 (140+)
│   │   ├── core_text/{generate,filter,eval,refine}/   # 通用文本算子
│   │   ├── general_text/            # 通用文本处理
│   │   ├── text_sft/                # SFT 数据合成
│   │   ├── text_pt/                 # 预训练数据
│   │   ├── conversations/           # 对话合成
│   │   ├── reasoning/               # 推理数据
│   │   ├── text2sql/                # Text2SQL
│   │   ├── knowledge_cleaning/      # 知识库清洗
│   │   ├── agentic_rag/             # Agentic RAG
│   │   ├── pdf2vqa/                 # PDF VQA (含 MinerU 集成)
│   │   ├── code/                    # 代码数据
│   │   ├── chemistry/               # 化学数据
│   │   ├── core_speech/             # 语音转写
│   │   └── core_vision/             # 视觉算子
│   ├── pipeline/                    # ★ Pipeline 引擎
│   │   ├── Pipeline.py              # PipelineABC / BatchedPipelineABC / StreamBatchedPipelineABC
│   │   └── nodes.py                 # OperatorNode / KeyNode (依赖图)
│   ├── serving/                     # ★ LLM 服务后端 (13 个实现)
│   ├── prompts/                     # ★ Prompt 模板库
│   ├── wrapper/                     # AutoOP 包装器 (编译期拦截)
│   │   └── auto_op.py               # AutoOP / OPRuntime
│   ├── utils/
│   │   ├── registry.py              # ★ Registry / LazyLoader + 全局注册表
│   │   ├── storage.py               # ★ Storage 实现 (5 种)
│   │   ├── text2sql/                # Text2SQL 数据库连接器
│   │   └── db_pool/                 # MyScale/ClickHouse 连接池
│   ├── statics/
│   │   ├── pipelines/               # ★ 现成 Pipeline (api/gpu/cpu 三族)
│   │   ├── playground/              # 演示脚本
│   │   └── scaffold/                # cookiecutter 脚手架模板
│   ├── cli.py                       # ★ Typer CLI 入口
│   ├── cli_funcs/                   # CLI 子命令实现 (init/eval/pdf/text/webui)
│   ├── example/                     # 各 Pipeline 的示例数据
│   ├── webui/                       # WebUI 启动逻辑
│   ├── rayorch/                     # Ray 分布式编排
│   └── logger.py                    # 日志 (loguru)
├── test/                            # 测试 (含 cpu_only / dummy_server)
├── pyproject.toml                   # 包配置 (包名 open-dataflow)
└── requirements.txt
```

### CLI 入口 (`dataflow/cli.py`)

CLI 基于 **Typer** 框架,入口函数 `app` (cli.py:19)。子命令结构:

| 命令 | 实现位置 | 功能 |
|------|----------|------|
| `dataflow init [base\|all\|reasoning]` | `cli_funcs/cli_init.py` | 初始化 pipeline 配置文件 |
| `dataflow init repo` | `cli_funcs/cli_init.py:init_repo_scaffold` | 从 cookiecutter 脚手架创建新仓库 |
| `dataflow env` | `cli_funcs/cli_env.py` | 显示环境信息 |
| `dataflow chat` | cli.py:99-167 | 交互式对话 (自动检测微调/base 模型) |
| `dataflow eval {init,api,local}` | `cli_funcs/cli_eval.py` | 模型评测 |
| `dataflow pdf2model {init,train}` | `cli_funcs/cli_pdf.py` | PDF→模型 (vqa/kbc 两种 QA 类型) |
| `dataflow text2model {init,train}` | `cli_funcs/cli_text.py` | 文本→模型 |
| `dataflow webui` | `cli_funcs/cli_webui.py` | 下载并启动 DataFlow-WebUI |

---

## 2. 五大核心抽象

### 2.1 OperatorABC —— 算子基类

**源码**: `dataflow/core/operator.py:5-15`

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

**关键点**:
- 只强制实现 `run()`,签名由子类自定义。约定第一参数为 `storage: DataFlowStorage`,并用 `input_key` / `output_key` 指定列名路由。
- `ALLOWED_PROMPTS` 属性配合 `@prompt_restrict` 装饰器做 prompt 类型校验。
- `get_operator()` (operator.py:17-28) 提供通过名字从 `OPERATOR_REGISTRY` 动态取算子的工厂方法。

#### 标准算子实现范式 (以 PromptedGenerator 为例)

**源码**: `dataflow/operators/core_text/generate/prompted_generator.py:10-90`

```python
@OPERATOR_REGISTRY.register()
class PromptedGenerator(OperatorABC):
    def __init__(self, llm_serving: LLMServingABC, system_prompt: str = "...",
                 user_prompt: str = "", json_schema: dict = None):
        self.llm_serving = llm_serving          # 持有 LLMServingABC 引用(供 pipeline 生命周期管理)
        self.system_prompt = system_prompt
        ...

    def run(self, storage: DataFlowStorage,
            input_key: str = "raw_content",
            output_key: str = "generated_content"):
        dataframe = storage.read('dataframe')               # 1. 读
        llm_inputs = [self.user_prompt + str(row[input_key])
                      for _, row in dataframe.iterrows()]   # 2. 构造输入
        outputs = self.llm_serving.generate_from_input(     # 3. 调 LLM
            user_inputs=llm_inputs, system_prompt=self.system_prompt)
        dataframe[output_key] = outputs                     # 4. 合并
        storage.write(dataframe)                            # 5. 写
        return output_key
```

这是所有算子遵循的 **读-处理-写** 五步范式。算子还提供静态方法 `get_desc(lang)` 供 Agent 读取能力描述。

#### 算子分类 (140+)

算子按 `dataflow/operators/` 子目录组织,目录名即类别:

| 类别 | 子目录 | 代表算子 | 数量 |
|------|--------|----------|------|
| **Generic 通用** | `core_text/`, `general_text/`, `text_pt/` | `PromptedGenerator`, `PerplexityFilter`, `TokenLengthFilter` | 80+ |
| **Domain 领域** | `text2sql/`, `reasoning/`, `knowledge_cleaning/`, `agentic_rag/`, `pdf2vqa/`, `conversations/`, `text_sft/`, `code/`, `chemistry/` | `SQLGenerator`, `question_generator`, `MinerU2LLMInputOperator`, `CondorGenerator` | 40+ |
| **Eval 评测** | 各目录下 `eval/` 子目录 | `question_difficulty_classifier`, `SQLComponentClassifier`, `MetaSampleEvaluator` | 20+ |

每个领域目录再细分 `generate/`(生成)、`filter/`(过滤)、`eval/`(评测)、`refine/`(精炼)四种职能,构成多维度分类法。

---

### 2.2 PipelineABC —— 管道基类

**源码**: `dataflow/pipeline/Pipeline.py:18-42`、`dataflow/pipeline/__init__.py`

```python
class PipelineABC(ABC):
    def __init__(self):
        self.op_runtimes: list[OPRuntime] = []   # 编译期记录的算子调用
        self.compiled = False
        self.accumulated_keys = []               # 每步前可用 key(校验用)
        self.op_nodes_list: list[OperatorNode] = []  # 依赖图节点
        self.llm_serving_list = []
        self.llm_serving_counter = Counter()     # 引用计数

    @abstractmethod
    def forward(self):
        """Main Function to run the pipeline"""
        pass
```

三个层次:`PipelineABC` → `BatchedPipelineABC` (Pipeline.py:544) → `StreamBatchedPipelineABC` (Pipeline.py:624)。

#### 编译阶段 (`compile()`, Pipeline.py:43-58)

```python
def compile(self):
    self.compiled = True
    for k, v in vars(self).items():
        if isinstance(v, OperatorABC):
            setattr(self, k, AutoOP(v, k, self))   # ① 用 AutoOP 替换所有算子属性
    self.forward()                                   # ② 空跑 forward(),AutoOP 拦截并记录
    self.forward = self._compiled_forward            # ③ 替换为编译后执行函数
    self._build_operator_nodes_graph()               # ④ 构建依赖图 + key 校验
```

**核心机制**: `forward()` 在编译期被 `AutoOP` 拦截——`AutoOP.run()` 不执行算子,而是用 `inspect.signature().bind()` 绑定参数,展平 `**kwargs`,把 `(算子实例, 算子名, 绑定参数)` 封装成 `OPRuntime` 追加到 `op_runtimes` (见 `dataflow/wrapper/auto_op.py:84-105`)。

#### 依赖图与 Key 校验 (`_build_operator_nodes_graph`, Pipeline.py:60-196)

1. 遍历 `op_runtimes`,从算子实例属性中 `isinstance(v, LLM_SERVING_CLASSES)` 提取 LLM serving;从 kwargs 提取 `storage`。
2. 构造 `OperatorNode`,其 `_get_keys_from_kwargs()` (nodes.py:59-68) **按命名约定**自动识别 key:参数名以 `input_` 开头且为 str → 输入 key;以 `output_` 开头 → 输出 key。
3. **Key 累积校验**: 以 step0 的 `storage.get_keys_from_dataframe()` 为初始 key 集合,逐算子检查其 `input_keys` 是否都在"已累积 key"中,并把 `output_keys` 加入集合 (Pipeline.py:104-123)。
4. 校验失败抛详细 `KeyError`,指明缺失 key、算子名、类名、参数名。
5. 构建 `KeyNode` 双向指针图:每个 key 记录"上次被修改的算子索引",建立前后算子间 `ptr` 连接,支持正向/反向遍历与可视化。

#### 执行阶段 (`_compiled_forward`, Pipeline.py:507-541)

```python
def _compiled_forward(self, resume_step: int = 0):
    for idx, op_node in enumerate(self.op_nodes_list):
        if idx - 1 < resume_step:          # 支持从指定步恢复
            continue
        # LLM 生命周期: 引用计数管理
        if op_node.llm_serving is not None:
            if self.active_llm_serving and self.active_llm_serving is not op_node.llm_serving:
                self.active_llm_serving.cleanup()   # 切换时释放上一个
            self.active_llm_serving = op_node.llm_serving
        if op_node.op_obj is not None:
            op_node.op_obj.run(storage=op_node.storage, **op_node.kwargs)  # 真正执行
            if hasattr(op_node.op_obj, "shutdown"):  # Ray 算子自动释放 actor
                op_node.op_obj.shutdown()
        # 引用计数归零则清理
        if op_node.llm_serving is not None:
            self.llm_serving_counter[self.active_llm_serving] -= 1
            if self.llm_serving_counter[...] == 0:
                self.active_llm_serving.cleanup()
                self.active_llm_serving = None
```

**要点**:
- LLM serving 用引用计数:`start_serving()` 在首次使用时触发(如加载 GPU 模型),`cleanup()` 在引用归零时触发(释放显存)。多个算子共享同一 serving 不会重复加载。
- `resume_step` 支持从缓存步恢复,配合 storage 的 step 缓存文件实现崩溃恢复。
- `draw_graph()` (Pipeline.py:252-469) 用 PyVis 生成交互式 HTML 依赖图,按步紫→蓝→青渐变着色。

#### AutoOP 包装器

**源码**: `dataflow/wrapper/auto_op.py:38-105`

```python
class AutoOP(Generic[P, R]):
    def __init__(self, operator, operator_name, pipeline):
        self._operator = operator
        self._orig_run = operator.run
        self._signature = inspect.signature(operator.run)
        self.__doc__ = self._orig_run.__doc__   # 转发文档串

    def run(self, *args, **kwargs):
        bound = self._signature.bind(*args, **kwargs)
        bound.apply_defaults()
        final_kwargs = self._flatten_bound_arguments(bound, self._signature)  # 展平 **kwargs
        self._pipeline.op_runtimes.append(
            OPRuntime(operator=self._operator, operator_name=self._operator_name,
                      args=dict(final_kwargs)))
        # 不执行,直接返回
```

`_flatten_bound_arguments()` (auto_op.py:58-82) 把 `**kwargs` 字典展平到顶层 OrderedDict,保证 key 提取能识别嵌套参数。这种"签名保持 + 调用记录"设计对算子实现完全透明。

---

### 2.3 LLMServingABC —— LLM 服务基类

**源码**: `dataflow/core/llm_serving.py:5-35`

```python
class LLMServingABC(ABC):
    @abstractmethod
    def generate_from_input(self, user_inputs: List[str], system_prompt: str) -> List[str]:
        """Generate data from input."""
        pass

    @abstractmethod
    def start_serving(self): ...   # 启动(如加载本地模型)

    @abstractmethod
    def cleanup(self): ...         # 释放 GPU/CPU 内存

    def load_model(self, model_name_or_path, **kwargs):
        raise NotImplementedError(...)
```

统一接口为 `generate_from_input(user_inputs, system_prompt) -> List[str]`,批量化输入输出。`dataflow/serving/__init__.py` 导出全部实现。

#### 四种核心实现对比

| 实现类 | 源码 | 后端 | 典型参数 | 适用场景 |
|--------|------|------|----------|----------|
| `APILLMServing_request` | `serving/api_llm_serving_request.py:14` | OpenAI 兼容 API | `api_url`, `max_workers=10`, `max_retries=5` | 远程/商用 API,无 GPU |
| `APIGoogleVertexAIServing` | `serving/api_google_vertexai_serving.py:173` | Google Vertex AI | `use_batch`(BigQuery 批量模式) | 大规模 Gemini 推理 |
| `LocalModelLLMServing_vllm` | `serving/local_model_llm_serving.py:11` | vLLM (本地 GPU) | `tensor_parallel_size`, `gpu_memory_utilization=0.9` | 本地多 GPU 高吞吐 |
| `LocalModelLLMServing_sglang` | `serving/local_model_llm_serving.py` | SGLang (本地 GPU) | RadixAttention 前缀缓存 | 长上下文/重复前缀 |

另有 VLM 变体:`APIVLMServing_openai` (多图 OpenAI API)、`LocalVLMServing_vllm` (本地视觉模型);以及 `LocalEmbeddingServing`、`LightRAGServing`、`LiteLLMServing` 等专用服务。

**API 实现要点** (api_llm_serving_request.py:59-67):用 `requests.Session` + `HTTPAdapter` 建连接池(`pool_maxsize=max_workers`),HTTP 429 限流时指数退避 `sleep(2**attempt)`,API key 从环境变量读取(安全考虑)。

**vLLM 实现要点** (local_model_llm_serving.py:74-89):`start_serving()` 时才下载/加载模型;`cleanup()` 依次调用 `destroy_model_parallel()`、`destroy_distributed_environment()`、`torch.cuda.empty_cache()`、`shutdown_ray()` 彻底释放 GPU 资源——这正是 Pipeline 引用计数要管理的高成本资源。

---

### 2.4 DataFlowStorage —— 存储基类

**源码**: `dataflow/utils/storage.py:14-68`

```python
class DataFlowStorage(ABC):
    @abstractmethod
    def get_keys_from_dataframe(self) -> list[str]: ...
    @abstractmethod
    def read(self, output_type) -> Any: ...
    @abstractmethod
    def write(self, data: Any) -> Any: ...
```

核心是 **step 机制**:每个算子调用 `storage.step()` 使 `operator_step += 1` 并返回 storage 的浅拷贝,从而算子从 step N 读、写 step N+1,形成链式数据血缘。

#### 五种 Storage 实现对比

| 实现 | 源码行 | 写入策略 | 容错 | 批处理 | 典型用途 |
|------|--------|----------|------|--------|----------|
| `LazyFileStorage` | storage.py:70-398 | 内存缓冲,退出/中断才落盘 | 原子写 `os.replace` + atexit/SIGINT 钩子 + RLock | 否 | 默认推荐,高 IO 效率 |
| `FileStorage` | storage.py:444-698 | 每次 write 立即落盘 | 无(可能产生半写文件) | 否 | 简单场景/调试 |
| `BatchedFileStorage` | storage.py:932-1078 | 按 batch 切片读写,追加写 | `_last_success_step.txt` 断点续传 | 是(切片) | 大数据集分批 |
| `StreamBatchedFileStorage` | storage.py:1080-1156 | 生成器 `iter_chunks()` 流式 | 同上 | 是(流式) | 内存放不下的数据集 |
| `MyScaleDBStorage` | storage.py:753-929 | 写 ClickHouse/MyScale | DB 事务 | 分页 | 中心化数据库管理 |

**LazyFileStorage 设计亮点** (storage.py:159-199):
- `_buffers: Dict[int, DataFrame]` 内存缓冲,`_dirty_steps: set` 脏步追踪。
- `weakref.ref(self)` + `atexit` 注册退出钩子,`signal.SIGINT/SIGTERM` 注册信号处理器,确保崩溃时也能 flush。
- `flush_step()` 用 `tempfile.mkstemp()` 写临时文件再 `os.replace()` 原子替换,杜绝半写文件。

**数据源支持**: step0 的 `first_entry_file_name` 支持三种前缀(storage.py:255-279):
- `"hf:dataset:config:split"` → HuggingFace Datasets
- `"ms:dataset:split"` → ModelScope Datasets
- 本地路径 → 按扩展名(json/jsonl/csv/parquet/pickle)读取

---

### 2.5 PromptABC —— 提示词基类

**源码**: `dataflow/core/prompt.py:6-16`

```python
class PromptABC():
    def build_prompt(self):
        raise NotImplementedError

class DIYPromptABC(PromptABC):  # 用户自定义 prompt 的基类
    def build_prompt(self):
        raise NotImplementedError
```

部分 prompt 还实现 `build_system_prompt()`。Prompt 与 Operator 解耦:Operator 持有 prompt 实例,调用 `build_prompt(**kwargs)` 生成文本,再交给 `llm_serving.generate_from_input()`。

#### prompt_restrict 装饰器 (prompt.py:28-78)

```python
def prompt_restrict(*allowed_prompts: type[DIYPromptABC]):
    def decorator(cls):
        setattr(cls, "ALLOWED_PROMPTS", tuple(allowed_prompts))
        orig_init = cls.__init__
        sig = inspect.signature(orig_init)
        @wraps(orig_init)
        def new_init(self, *args, **kwargs):
            bound = sig.bind_partial(self, *args, **kwargs)
            bound.apply_defaults()
            pt = bound.arguments.get("prompt_template", None)
            if pt is not None and not isinstance(pt, cls.ALLOWED_PROMPTS):
                if not isinstance(pt, DIYPromptABC):
                    raise TypeError(f"[{cls.__name__}] Invalid prompt_template type: ...")
            return orig_init(self, *args, **kwargs)
        cls.__init__ = new_init
        return cls
    return decorator
```

**作用**: 限制算子只能接收白名单内的 prompt 类(或 `DIYPromptABC` 子类),在实例化时做运行时类型检查,保证 prompt-operator 类型安全。例如 `@prompt_restrict(SelectSQLGeneratorPrompt, SelectVecSQLGeneratorPrompt)` 限定 SQLGenerator 只能用指定 prompt。

#### Prompt 注册与组织

`PROMPT_REGISTRY` (registry.py:259) 统一管理。Prompt 按领域文件组织在 `dataflow/prompts/`:

| 文件 | 领域 | 代表 Prompt |
|------|------|-------------|
| `general_text.py` | 通用文本 | `SFTGeneratorSeedPrompt`, `ConsistentChatPrompt`(9 意图 500+ 主题), `MetaPrompt`(6 维评分), `AlpagasusPrompt` |
| `text2sql.py` | Text2SQL | `SelectSQLGeneratorPrompt`(4 复杂度档+50 函数示例), `Text2SQLQuestionGeneratorPrompt`(3 风格) |
| `reasoning/` | 推理 | `GeneralAnswerGeneratorPrompt`, `MathPrompt` |
| `pdf2vqa.py` | PDF VQA | `QAExtractPrompt`, `VQAExtractPrompt` |
| `kbcleaning.py` | 知识库清洗 | — |
| `agenticrag.py` | Agentic RAG | — |

Prompt 使用模式:单次生成、多阶段生成(`mode="query"/"response"`)、多候选选择(生成多 embedding 选最优)。

---

## 3. Registry 系统

**源码**: `dataflow/utils/registry.py:34-364`、全局实例 registry.py:257-259

```python
OPERATOR_REGISTRY = Registry(name='operators')
PROMPT_REGISTRY = Registry(name='prompts')
```

### Registry 类核心 API

| 方法 | 行号 | 功能 |
|------|------|------|
| `__init__(name)` | 60-74 | 以 name 对应 `dataflow/{name}/` 子目录,列出子模块填 `loader_map` |
| `register(obj=None)` | 85-103 | 装饰器或函数调用两种用法,key 取 `obj.__name__` |
| `get(name)` | 104-129 | 查 `_obj_map`;未命中则触发懒加载 |
| `apply_whitelist(names)` | 131-206 | 白名单裁剪,返回 kept/removed 报告 |
| `_get_all()` | 231-235 | 急切加载全部,配合 whitelist 做生产部署瘦身 |

### 懒加载机制 (LazyLoader, registry.py:261-364)

`Registry.__init__` 时只列出子模块名(`loader_map = {"core_text": None, ...}`),不导入。首次 `get(name)` 时:
1. `_init_loaders()` (76-79) 对每个子模块 `importlib.import_module()` —— 此时各子模块的 `__init__.py` 通过 `TYPE_CHECKING` 块声明其导出类。
2. 遍历 `loader_map`,对每个模块 `getattr(module_lib, name)` 尝试取类。
3. `LazyLoader.__getattr__` (343-364) 拦截属性访问:查 `_loaded_classes` 缓存 → 查 `_import_structure` 得 `(file_path, class_name)` → `_load_class_from_file()` 用 `importlib.util.spec_from_file_location` 动态加载,缓存后返回。

**性能收益**: 启动只导入 Registry 类(~50ms),而非全部 140+ 算子(~2-3s);首次访问某类才付导入开销,后续 O(1) 缓存命中。

### 算子注册流程

```
@OPERATOR_REGISTRY.register()          # 装饰器: register(obj=None) 返回 deco
class PromptedGenerator(OperatorABC):  # 类定义完成 → deco(cls) → _do_register("PromptedGenerator", cls)
    ...                                # cls 存入 OPERATOR_REGISTRY._obj_map

# 使用时:
OPERATOR_REGISTRY.get("PromptedGenerator")  # → _obj_map 命中或触发懒加载
```

`_import_structure` 由 `generate_import_structure_from_type_checking()` (registry.py:15-31) 用 AST 解析各模块 `__init__.py` 的 `TYPE_CHECKING` 块自动生成,无需手工维护映射。

---

## 4. Pipeline 系统

### 4.1 编译 vs 执行两阶段

| 阶段 | 触发 | 关键动作 | 产出 |
|------|------|----------|------|
| **编译** | `pipeline.compile()` | AutoOP 替换算子 → 空跑 forward 记录 OPRuntime → 构 OperatorNode 图 → key 累积校验 → 替换 `forward=_compiled_forward` | `op_nodes_list`(含依赖图)、`accumulated_keys` |
| **执行** | `pipeline.forward()` | 顺序遍历 op_nodes → LLM 引用计数管理 → storage.step() 链式步进 → resume_step 恢复 | 各步缓存文件 |

### 4.2 三种 Pipeline 变体

| 类 | 源码行 | forward 签名 | 特点 |
|----|--------|--------------|------|
| `PipelineABC` | Pipeline.py:18 | `_compiled_forward(resume_step=0)` | 基础顺序执行 |
| `BatchedPipelineABC` | Pipeline.py:544 | `_compiled_forward(resume_step, batch_size, resume_from_last)` | 按 batch 切片,`_last_success_step.txt` 记 `{step},{batch}` 断点续传 |
| `StreamBatchedPipelineABC` | Pipeline.py:624 | 同上 | 生成器 `iter_chunks()` 流式,内存只持一批 |

### 4.3 五大 Pipeline 族

现成 Pipeline 位于 `dataflow/statics/pipelines/`,按 `api_pipelines/`、`gpu_pipelines/`、`cpu_pipelines/` 三种后端变体组织,同一族 pipeline 有对应 API/GPU/CPU 版本:

| Pipeline 族 | api 版 | gpu 版 | cpu 版 | 核心算子链 |
|-------------|--------|--------|--------|------------|
| **Text** (SFT/对话合成) | `text_sft_synthesis_pipeline.py`, `text_conversation_synthesis_pipeline.py` | `text_sft_synthetic.py` | `text_sft_filter.py` | PromptedGenerator → CondorGenerator → 过滤 |
| **Reasoning** (推理增强) | `reasoning_math_pipeline.py`, `reasoning_general_pipeline.py`, `reasoning_diy_pipeline.py` | `reasoning_math_pipeline.py` | `reasoning_pipeline.py` | question_generator → answer_generator(CoT) → 难度分类 |
| **Text2SQL** | `text2sql_pipeline_gen.py`, `text2sql_pipeline_refine.py`, `text2vecsql_pipeline_gen.py` | `text2sql_pipeline_gen.py`, `text2sql_pipeline_refine.py` | `text2sql_pipeline.py` | SQLGenerator → QuestionGenerator → SQLExecutionFilter → 分类 |
| **KB Cleaning** (知识库清洗) | `kbcleaning_pipeline.py` | `kbcleaning/kbcleaning_pipeline_vllm.py`, `..._sglang.py` | `kbcleaning_pipeline_url.py` | PDF转换 → KBCTextCleaner → QAExtractor |
| **Agentic RAG** | `agentic_rag_pipeline.py`, `agentic_rag_multihop_core_pipeline.py` | — | — | ExternalKnowledgeIdentifier → MultiHopQAGenerator |

另有 **PDF VQA Extraction** (`pdf_vqa_extract_pipeline.py`)、**Code**、**Chemistry**、**FuncCall**、**Speech** 等扩展族,以及 **Benchmark Eval** (`gpu_pipelines/benchmark_eval/unified_bench_eval_type{1-6}.py`) 评测族。

### 4.4 完整 Pipeline 示例 (PDF VQA, api_pipelines/pdf_vqa_extract_pipeline.py:13-108)

```python
class PDF_VQA_extract_optimized_pipeline(PipelineABC):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage(first_entry_file_name="./.../vqa_extract_test.jsonl", ...)
        self.llm_serving = APILLMServing_request(api_url=..., model_name="gemini-2.5-pro", max_workers=100)
        self.pdf_merger = PDF_Merger(output_dir="./cache")
        self.mineru_executor = FileOrURLToMarkdownConverterFlash(...)   # MinerU 集成
        self.input_formatter = MinerU2LLMInputOperator()
        self.vqa_extractor = ChunkedPromptedGenerator(llm_serving=..., system_prompt=QAExtractPrompt().build_prompt(), max_chunk_len=128000)
        self.llm_output_parser = LLMOutputParser(...)
        self.qa_merger = QA_Merger(...)
        self.vqa_format_converter = VQAFormatter(...)

    def forward(self):
        self.pdf_merger.run(storage=self.storage.step(), input_pdf_list_key=..., output_pdf_path_key=...)
        self.mineru_executor.run(storage=self.storage.step(), input_key="merged_pdf_path", output_key="vqa_markdown_path")
        self.input_formatter.run(storage=self.storage.step(), input_markdown_path_key=..., output_converted_layout_key=...)
        self.vqa_extractor.run(storage=self.storage.step(), input_path_key=..., output_path_key=...)
        self.llm_output_parser.run(storage=self.storage.step(), ...)
        self.qa_merger.run(storage=self.storage.step(), ...)
        self.vqa_format_converter.run(storage=self.storage.step(), ...)

# 使用
pipeline = PDF_VQA_extract_optimized_pipeline()
pipeline.compile()    # 编译:校验 key 链 merged_pdf_path→vqa_markdown_path→...→messages
pipeline.forward()    # 执行:7 步链式处理,每步 storage.step() 缓存
```

每个 `run(storage=self.storage.step(), input_xxx_key=..., output_xxx_key=...)` 调用都被 AutoOP 记录,key 链必须在编译期闭合。

---

## 5. DataFlow-Agent

DataFlow-Agent 是**智能助手层**,位于标准 Pipeline 系统之上,实现"自然语言任务描述 → 可执行 pipeline"的自动化。其核心能力:

1. **分析**: 解析输入数据特征与目标输出格式
2. **选择**: 从 `OPERATOR_REGISTRY`(140+ 算子)按关键词/能力/数据类型匹配选算子
3. **编排**: 确定算子顺序,保证 output_key 满足下游 input_key
4. **生成**: 产出完整 `PipelineABC` 子类代码
5. **监控**: SSE 流式反馈执行进度

### Agent 生成 Pipeline 的代码结构

Agent 生成的代码与手写 pipeline 等价,同样继承 `PipelineABC`、用 `storage.step()` 链接、经 `compile()` 校验:

```python
# 由 DataFlow-Agent 生成
class AgentGeneratedPipeline(PipelineABC):
    def __init__(self, ..., llm_serving=None, **kwargs):
        super().__init__(**kwargs)
        self.op1 = SelectedOperator1(llm_serving=llm_serving, ...)
        self.op2 = SelectedOperator2(...)
    def forward(self, storage):
        self.op1.run(storage.step(), input_key="key1", output_key="key2")
        self.op2.run(storage.step(), input_key="key2", output_key="key3")
        return storage
```

### 技术栈与后端

Agent 依赖 `fastapi`/`uvicorn`/`httpx`/`sseclient-py`/`cloudpickle` 等构建 REST 服务 (requirements.txt:61-72)。可复用任意 DataFlow LLM 后端:规划用强推理模型(GPT-4/Gemini),代码生成用代码模型。Agent 主要通过 **DataFlow-WebUI** 暴露交互界面(README:68 "WebUI supports AI-agent-assisted pipeline construction"),Core 仓库的 `dataflow/example/DataflowAgent/` 提供测试数据(`agent_test_data.json`、`mq_test_data.jsonl`)。

**局限**: 只能选已注册算子;复杂依赖可能需人工微调;prompt 选择靠启发式;不做资源预估。

---

## 6. 与生态其他组件的接口

### 6.1 MinerU 集成 (PDF VQA Pipeline)

DataFlow 在 PDF VQA 族中通过两个算子接入 MinerU:

1. **`FileOrURLToMarkdownConverterFlash` / `FileOrURLToMarkdownConverterAPI`** (knowledge_cleaning 模块): 调用 MinerU 把 PDF 转 Markdown,产出 `*_content_list.json`。Flash 版用本地 MinerU2.5-2509-1.2B 模型 + Ray/vLLM worker(`replicas`、`num_gpus_per_replica` 可配)。
2. **`MinerU2LLMInputOperator`** (`dataflow/operators/pdf2vqa/generate/mineru_to_llm_input_operator.py:8-76`): 把 MinerU 的 `content_list.json` 转为 LLM 友好格式——展平 list 项、重新编号、剔除 `bbox`/`page_idx`,输出 `*_converted.json`。

```python
# mineru_to_llm_input_operator.py:28-53 核心转换逻辑
def _convert_json(self, input_file, output_file):
    data = list(json.load(infile))
    new_data, id = [], 0
    for item in data:
        item.pop('bbox', None); item.pop('page_idx', None)
        if item.get('type','') == 'list' and item['sub_type'] == 'text':
            for list_item in item.get('list_items', []):
                new_data.append({'type':'text','text':list_item,'id':id}); id+=1
        else:
            new_data.append(item); id+=1
    json.dump(new_data, outfile, ensure_ascii=False)
```

这与本项目 `tools/srs_mineru_parse.py` + `tools/srs_structurer.py` 的 MinerU 输出后处理思路一致。

### 6.2 DataFlow-Skills / WebUI / Ecosystem 扩展模式

DataFlow Suite 四层 (README:131-141):
- **DataFlow-Skills**: 算子开发、pipeline 构建的技能与教程集合。
- **DataFlow-WebUI**: 可视化拖拽 + AI Agent 辅助的 pipeline 工作台,通过 `dataflow webui` 启动 (cli_funcs/cli_webui.py)。
- **DataFlow-Ecosystem**: 标准化算子注册的模块化分发层,领域模块(如 DataFlow-MM 多模态、DataFlow-AI4S)以独立 GitHub 仓库扩展,通过统一 `OPERATOR_REGISTRY` 注册接入。
- **RayOrch**: 基于 Ray 的高性能分布式编排层,Core 中 `dataflow/rayorch/` 与算子的 `shutdown()` 钩子(Pipeline.py:533-535)对接。

**扩展模式**: 第三方模块只需 `@OPERATOR_REGISTRY.register()` 注册算子类、`@PROMPT_REGISTRY.register()` 注册 prompt,即可被 Pipeline 编译执行和 Agent 发现。`WrapperABC` (`dataflow/core/wrapper.py`) 为 Ray 分布式算子提供基类,`shutdown()` 方法被 Pipeline 自动调用释放 actor 资源。`apply_whitelist()` 支持生产部署时只保留所需算子以降低内存。

---

## 7. 对 SRS 项目的潜在价值

DataFlow Core 的抽象与 SRS 一致性检测项目高度契合,可直接借鉴或集成:

1. **文档处理流水线化**: SRS 的"MinerU 解析 → 结构化 → 约束提取 → 表格提取 → 一致性检测"链(`srs_unified_processor.py`)本质就是 DataFlow Pipeline。可将每个 `tools/srs_*.py` 改写为 `OperatorABC` 子类,用 `storage.step()` 自动管理中间 JSON 缓存(替代手工 `processed_documents/`),获得 key 校验、断点续跑、依赖图可视化能力。

2. **约束提取算子化**: `srs_constraint_extract.py` 调 GLM API 提取 7 类约束,可直接套用 `PromptedGenerator` 范式——`input_key="section_text"`, `output_key="constraints"`,复用 `APILLMServing_request` 的并发/重试/限流退避逻辑(本项目目前多为串行调用)。

3. **三层一致性检测 pipeline**: 语法/语义/逻辑三层检测(`srs_consistency_checker_v2.py`)可建模为三个 Eval 算子串联,每层 output_key 作为下层 input_key,编译期自动校验 key 链,避免运行期才发现字段不匹配。Z3 求解可封装为不依赖 LLM 的算子。

4. **Prompt 复用与类型安全**: GJB 规则提取、约束提取等 prompt 可注册到 `PROMPT_REGISTRY`,用 `@prompt_restrict` 约束算子-prompt 配对,防止误用。`DIYPromptABC` 允许快速试验新 prompt 而不动算子代码。

5. **可复现评测**: `srs_eval.py` 的 P/R/F1 评测可纳入 Benchmark Eval Pipeline 模式,配合 `LazyFileStorage` 的原子缓存实现可复现的 Gold Standard 对齐实验,便于论文复现。

6. **Agent 辅助**: 未来可用 DataFlow-Agent 根据不同 SRS 文档类型(航空/编译器/调度器)自动组装检测 pipeline,降低人工配置成本。

**落地建议**: 优先把 `srs_constraint_extract.py` 和 `srs_consistency_checker_v2.py` 改造为 DataFlow 算子,以 `LazyFileStorage` 替代当前手工缓存管理,即可立即获得并发推理、断点续跑、key 校验三项收益,改动量小且与现有 Gold Standard 评测框架兼容。
