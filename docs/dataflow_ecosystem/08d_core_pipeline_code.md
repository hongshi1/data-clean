# DataFlow Core 框架代码模板 — 用 Operator / Pipeline 构建 SRS 冲突检测

> 本文档从 DataFlow 克隆源码（`dataflow_repos/DataFlow/`）逐文件提取**真实基类代码、注册机制、编译执行机制、Storage/LLM Serving 实现**，最终给出一个可直接运行的 SRS 冲突检测 Pipeline。
> 所有代码块均标注源文件路径与行号，模板代码严格基于真实基类接口，不做臆造。

---

## 目录

- [0. 整体心智模型](#0-整体心智模型)
- [A. OperatorABC 完整定义](#a-operatorabc-完整定义)
- [B. 定义自定义算子的完整模板](#b-定义自定义算子的完整模板)
- [C. PipelineABC 完整定义（compile / forward / AutoOP）](#c-pipelineabc-完整定义)
- [D. 定义自定义 Pipeline 的完整模板](#d-定义自定义-pipeline-的完整模板)
- [E. Storage 使用方式](#e-storage-使用方式)
- [F. LLM Serving 使用方式](#f-llm-serving-使用方式)
- [G. 完整的 SRS 冲突检测 Pipeline（可直接运行）](#g-完整的-srs-冲突检测-pipeline可直接运行)
- [H. AutoOP 编译期 key 校验的实际代码](#h-autoop-编译期-key-校验的实际代码)
- [附: Prompt 模板系统 / CLI 脚手架 / WebUI 动态发现](#附-prompt-模板系统--cli-脚手架--webui-动态发现)

---

## 0. 整体心智模型

DataFlow Core 的核心抽象只有三个，外加一个 Storage 做数据流转：

```
OperatorABC  ──(run)──▶  DataFlowStorage   ◀──(run)──  PipelineABC
     │                        │  step()                     │  compile()
     │                        │  read()/write()             │  forward()
     ▼                        ▼                             ▼
LLMServingABC            pandas DataFrame              AutoOP 包装器
(generate_from_input)    (列 = key)                    (编译期 key 依赖图)
```

**关键约定（贯穿全文）：**
1. `run()` 的参数名以 `input_` 开头 = 输入 key；以 `output_` 开头 = 输出 key。这是编译期 key 校验的**唯一识别规则**（见 `pipeline/nodes.py:60-66`）。
2. `storage.step()` 返回 storage 的浅拷贝并把 `operator_step` +1；`read()` 读当前 step，`write()` 写到 `step+1`。
3. `compile()` 会调用一次 `forward()`，但 `forward` 此时已被 `AutoOP` 拦截——它**不真正执行算子**，只记录 `OPRuntime`，然后做 key 依赖图校验；之后 `self.forward` 被替换成 `_compiled_forward`（真正执行）。

---

## A. OperatorABC 完整定义

源文件：`dataflow/core/operator.py:1-28`（完整，无删减）

```python
from abc import ABC, abstractmethod
from dataflow.logger import get_logger
from .prompt import DIYPromptABC, PromptABC

class OperatorABC(ABC):
    def __init__(self):
        self.logger = get_logger()
        self.ALLOWED_PROMPTS = tuple([type[DIYPromptABC | PromptABC]])

    @abstractmethod
    def run(self) -> None:
        """
        Main function to run the operator.
        """
        pass

def get_operator(operator_name, args) -> OperatorABC:
    from dataflow.utils import OPERATOR_REGISTRY
    print(operator_name, args)
    operator = OPERATOR_REGISTRY.get(operator_name)(args)
    logger = get_logger()
    if operator is not None:
        logger.info(f"Successfully get operator {operator_name}, args {args}")
    else:
        logger.error(f"operator {operator_name} is not found")
    assert operator is not None
    print(operator)
    return operator
```

**要点：**
- `OperatorABC` 只有一个抽象方法 `run`。注意基类签名是 `run(self) -> None`，**真实算子会重载成 `run(self, storage, input_key=..., output_key=...)`**，参数名约定见上文。
- `ALLOWED_PROMPTS`：配合 `@prompt_restrict` 装饰器做 prompt 类型白名单校验。
- 注册方式：`@OPERATOR_REGISTRY.register()`（不是装饰 `OperatorABC`，而是装饰**具体子类**）。

### A.1 注册表 Registry（真实实现）

源文件：`dataflow/utils/registry.py:34-129`（核心片段）

```python
class Registry():
    def __init__(self, name):
        self._name = name
        self._obj_map = {}
        self._base_folder = Path(__file__).resolve().parents[1]
        self._sub_modules = list(os.listdir(self._base_folder / name))
        # ... 去掉 __init__.py / __pycache__ ...
        if len(self._sub_modules) > 0:
            self.loader_map = dict(zip(self._sub_modules, [None] * len(self._sub_modules)))

    def _init_loaders(self):
        for module_name in self.loader_map.keys():
            module_path = f"dataflow.{self._name}.{module_name}"
            self.loader_map[module_name] = importlib.import_module(module_path)

    def _do_register(self, name, obj):
        if name not in self._obj_map:
            self._obj_map[name] = obj

    def register(self, obj=None):
        # 可当装饰器 @REG.register() 也可当函数 REG.register(cls)
        if obj is None:
            def deco(func_or_class):
                name = func_or_class.__name__
                self._do_register(name, func_or_class)
                return func_or_class
            return deco
        name = obj.__name__
        self._do_register(name, obj)

    def get(self, name):
        ret = self._obj_map.get(name)
        if ret is None:
            if None in self.loader_map.values():
                self._init_loaders()
            for module_lib in self.loader_map.values():
                try:
                    clss = getattr(module_lib, name)
                    self._obj_map[name] = clss
                    return clss
                except AttributeError as e:
                    continue
            raise KeyError(f"No object named '{name}' found in '{self._name}' registry!")
        return ret

# 模块级两个全局注册表
OPERATOR_REGISTRY = Registry(name='operators')   # registry.py:257
PROMPT_REGISTRY = Registry(name='prompts')        # registry.py:259
```

**懒加载机制：** `Registry` 在构造时扫描 `dataflow/operators/` 和 `dataflow/prompts/` 下的子目录名，但**不立即 import**。只有当 `get(name)` 找不到时才触发 `_init_loaders()` 真正导入对应子包。`LazyLoader`（`registry.py:261-364`）进一步做到"按类名从文件加载"，避免一次性导入全部算子。

### A.2 LLMServingABC

源文件：`dataflow/core/llm_serving.py:1-35`（完整）

```python
from abc import ABC, abstractmethod
from typing import Any, List

class LLMServingABC(ABC):
    """Abstract base class for data generators. Which may be used to generate data from a model or API. Called by operators
    """
    @abstractmethod
    def generate_from_input(self, user_inputs: List[str], system_prompt: str) -> List[str]:
        """Generate data from input. input: List[str], the input of the generator"""
        pass

    @abstractmethod
    def start_serving(self):
        """Cleanup the generator and garbage collect all GPU/CPU memory."""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup the generator and garbage collect all GPU/CPU memory."""
        pass

    def load_model(self, model_name_or_path: str, **kwargs: Any):
        raise NotImplementedError("This method should be implemented by subclasses.")
```

**算子持有 LLM Serving 的方式：** 在 `__init__` 里把 `llm_serving: LLMServingABC` 存为 `self.llm_serving`。`PipelineABC.compile()` 会反射 `vars(op)` 找到所有 `LLMServingABC` 实例并纳入生命周期管理（见 `Pipeline.py:67-69`）。

---

## B. 定义自定义算子的完整模板

下面模板严格基于 DataFlow 官方脚手架 `dataflow/statics/scaffold/.../operators/core/my_prompted_generator.py`（真实文件）改写为 SRS 场景。

### B.1 官方脚手架原版（真实代码）

源文件：`dataflow/statics/scaffold/{{cookiecutter.repo_name}}/{{cookiecutter.package_name}}/operators/core/my_prompted_generator.py:8-88`

```python
from dataflow.utils.registry import OPERATOR_REGISTRY
from dataflow import get_logger
from dataflow.utils.storage import DataFlowStorage
from dataflow.core import OperatorABC
from dataflow.core import LLMServingABC

@OPERATOR_REGISTRY.register()
class MyPromptedGenerator(OperatorABC):
    '''This is an simple Operator as a template, you can modify it to meet your own needs.'''
    def __init__(self,
                llm_serving: LLMServingABC,
                system_prompt: str = "You are a helpful agent.",
                user_prompt: str = "",
                json_schema: dict = None,
                ):
        self.logger = get_logger()
        self.llm_serving = llm_serving
        self.json_schema = json_schema
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

    @staticmethod
    def get_desc(lang: str = "zh"):
        if lang == "zh":
            return ("基于用户提供的提示词（prompt）生成数据。 ...")
        elif lang == "en":
            return ("Generate data from user-provided prompts. ...")
        else:
            return "This operator generates text based on system prompt and input content."

    def run(self, storage: DataFlowStorage, input_key: str = "raw_content", output_key: str = "generated_content"):
        self.input_key, self.output_key = input_key, output_key
        self.logger.info(f"Running {self.__class__.__name__}...")
        dataframe = storage.read('dataframe')                       # 读当前 step
        llm_inputs = []
        for index, row in dataframe.iterrows():
            raw_content = row.get(self.input_key, '')
            if raw_content:
                llm_input = self.user_prompt + str(raw_content)
                llm_inputs.append(llm_input)
        generated_outputs = self.llm_serving.generate_from_input(
            user_inputs=llm_inputs, system_prompt=self.system_prompt, json_schema=self.json_schema)
        dataframe[self.output_key] = generated_outputs              # 写新列
        output_file = storage.write(dataframe)                      # 写到 step+1
        return output_key
```

### B.2 SRS 冲突检测算子模板（基于真实接口）

```python
# srs_conflict/operators/srs_conflict_detector.py
from dataflow.utils.registry import OPERATOR_REGISTRY
from dataflow import get_logger
from dataflow.utils.storage import DataFlowStorage
from dataflow.core import OperatorABC, LLMServingABC
import json

@OPERATOR_REGISTRY.register()
class SRSConflictDetector(OperatorABC):
    """
    SRS 需求项冲突检测算子。
    对每一行（一个需求项 / 一对需求项），调用 LLM 判断是否存在冲突。
    """
    def __init__(self,
                 llm_serving: LLMServingABC,
                 system_prompt: str = "你是 SRS 一致性审查专家，判断给定的需求项之间是否存在冲突。",
                 json_schema: dict = None,
                 ):
        self.logger = get_logger()
        self.llm_serving = llm_serving
        self.system_prompt = system_prompt
        self.json_schema = json_schema or {
            "type": "object",
            "properties": {
                "has_conflict": {"type": "boolean"},
                "conflict_type": {"type": "string"},
                "explanation": {"type": "string"}
            },
            "required": ["has_conflict", "explanation"]
        }

    @staticmethod
    def get_desc(lang: str = "zh"):
        return "对每行需求项调用 LLM 进行冲突检测，输出 has_conflict/explanation。"

    def run(self, storage: DataFlowStorage,
            input_key: str = "requirement_pair",      # input_ 前缀 → 编译期识别为输入 key
            output_key: str = "conflict_result"):      # output_ 前缀 → 编译期识别为输出 key
        self.logger.info("Running SRSConflictDetector...")
        dataframe = storage.read('dataframe')
        self.logger.info(f"Loading, number of rows: {len(dataframe)}")

        llm_inputs = []
        for _, row in dataframe.iterrows():
            content = row.get(input_key, '')
            if content:
                llm_inputs.append(str(content))

        generated_outputs = self.llm_serving.generate_from_input(
            user_inputs=llm_inputs, system_prompt=self.system_prompt, json_schema=self.json_schema)

        # 解析为 dict 列表
        parsed = []
        for out in generated_outputs:
            try:
                parsed.append(json.loads(out) if isinstance(out, str) else out)
            except Exception:
                parsed.append({"has_conflict": None, "explanation": str(out)})

        dataframe[output_key] = parsed
        storage.write(dataframe)
        return output_key
```

**关键遵守：**
- `run` 第一个非 self 参数必须是 `storage: DataFlowStorage`（`Pipeline.py:73` 的 assert 检查 storage 类型）。
- `input_key` / `output_key` 这类以 `input_`/`output_` 开头的**字符串型**参数才会被识别为 key（`nodes.py:61-66`），其它参数（如 `json_schema` 是 dict）会被忽略并打印警告。
- `run` 必须返回 `output_key`（供下游引用，非强制但惯例）。

---

## C. PipelineABC 完整定义

源文件：`dataflow/pipeline/Pipeline.py:18-142`（核心：`__init__` / `forward` / `compile` / `_build_operator_nodes_graph`）

### C.1 `__init__` 与抽象 `forward`

```python
# Pipeline.py:18-41
class PipelineABC(ABC):
    def __init__(self):
        # list of dict, contains `OPRuntime` class and parameters for `operator.run()`
        self.op_runtimes: list[OPRuntime] = []
        self.compiled = False
        # accumulated keys in each operators, index 0 refers to the keys before the first operator
        self.accumulated_keys = []
        self.logger = get_logger()
        self.active_llm_serving = None
        self.op_nodes_list: list[OperatorNode] = []
        self.llm_serving_list = []
        self.llm_serving_counter = Counter()

    @abstractmethod
    def forward(self):
        """Main Function to run the pipeline"""
        pass
```

### C.2 `compile()` — 编译期拦截 + key 校验（真实实现）

```python
# Pipeline.py:43-58
def compile(self):
    self.compiled = True
    # 把 self 上所有 OperatorABC 实例替换成 AutoOP 包装器
    for k, v in vars(self).items():
        if isinstance(v, OperatorABC):
            setattr(self, k, AutoOP(v, k, self))
    self.forward()                       # ← 调 forward，但此时 op 已是 AutoOP，只记录不执行
    # after call forward, call back function in AutoOP will add the OPRuntime object to self.op_runtimes

    self.forward = self._compiled_forward   # ← 替换为真正执行的版本
    self.logger.info(
        f"Compiling pipeline and validating key integrity "
        f"across {len(self.op_runtimes)} operator runtimes.")
    self._build_operator_nodes_graph()      # ← 构建 key 依赖图并校验
```

### C.3 `_build_operator_nodes_graph()` — key 依赖图与校验（核心逻辑）

```python
# Pipeline.py:60-143（关键校验段）
def _build_operator_nodes_graph(self):
    for op_runtime in self.op_runtimes:
        llm_serving_obj, storage_obj = None, None
        for _, v in vars(op_runtime.op).items():
            if isinstance(v, LLM_SERVING_CLASSES):
                llm_serving_obj = v
        storage_obj = op_runtime.kwargs.pop("storage", None)
        assert isinstance(storage_obj, DataFlowStorage), \
            f"Storage must be a DataFlowStorage object, but got {type(storage_obj)} ..."

        op_node = OperatorNode(
            op_obj=op_runtime.op, op_name=op_runtime.op_name,
            storage=storage_obj, llm_serving=llm_serving_obj,
            **op_runtime.kwargs)
        self.op_nodes_list.append(op_node)
        self.llm_serving_list.append(llm_serving_obj)
        if llm_serving_obj is not None:
            self.llm_serving_counter[llm_serving_obj] += 1

    # 初始 key = 第一个 storage 的所有列名
    first_op = self.op_nodes_list[0] if self.op_nodes_list else None
    if first_op and first_op.storage:
        iter_storage_keys = first_op.storage.get_keys_from_dataframe()
    else:
        iter_storage_keys = []
    self.accumulated_keys.append(copy.deepcopy(iter_storage_keys))

    error_msg = []
    for op_node in self.op_nodes_list:
        # ★ 校验：每个 input_key 必须出现在当前已累积的 key 集合里
        for input_key in op_node.input_keys:
            if input_key not in self.accumulated_keys[-1]:
                error_msg.append({
                    "input_key": input_key,
                    "op_name": op_node.op_name,
                    "class_name": op_node.op_obj.__class__.__name__,
                    "key_para_name": op_node.input_key_nodes[input_key].key_para_name
                })
        # 把 output_key 加入累积集合
        for output_key in op_node.output_keys:
            if output_key not in iter_storage_keys:
                iter_storage_keys.append(output_key)
        self.accumulated_keys.append(copy.deepcopy(iter_storage_keys))

    if len(error_msg) != 0:
        details = "\n".join(
            f"- Input key '{e['input_key']}' in `{e['op_name']}` "
            f"(class <{e['class_name']}>) does not match any output keys "
            f"from previous operators or dataset keys. "
            f"Check parameter '{e['key_para_name']}' in the `{e['op_name']}.run()`."
            for e in error_msg)
        msg = f"Key Matching Error in following Operators during pipeline.compile():\n{details}"
        self.logger.warning(msg)
        raise KeyError(msg)            # ← key 不匹配直接抛 KeyError
    self.final_keys = copy.deepcopy(iter_storage_keys)
    # ... 之后构建 DATASET-INPUT / DATASET-OUTPUT 哨兵节点 + KeyNode 指针 ...
```

### C.4 `_compiled_forward()` — 真正执行（真实实现）

```python
# Pipeline.py:507-541
def _compiled_forward(self, resume_step: int = 0):
    for idx, op_node in enumerate(self.op_nodes_list):
        if idx - 1 < resume_step:      # minus one since INPUT-DATA Node
            continue
        # LLM Serving 生命周期：切换时 cleanup 上一个
        if op_node.llm_serving != None:
            if self.active_llm_serving and self.active_llm_serving is not op_node.llm_serving:
                self.active_llm_serving.cleanup()
            self.active_llm_serving = op_node.llm_serving
        # 真正调用 op.run(storage=..., **kwargs)
        if op_node.op_obj != None:
            op_node.op_obj.run(storage=op_node.storage, **op_node.kwargs)
            if hasattr(op_node.op_obj, "shutdown"):
                op_node.op_obj.shutdown()
        # 引用计数归零时 cleanup
        if op_node.llm_serving != None:
            self.llm_serving_counter[self.active_llm_serving] -= 1
            if self.llm_serving_counter[self.active_llm_serving] == 0:
                self.active_llm_serving.cleanup()
                self.active_llm_serving = None
```

**`BatchedPipelineABC` / `StreamBatchedPipelineABC`**（`Pipeline.py:544-712`）继承 `PipelineABC`，重写 `_compiled_forward` 加入 `batch_size` / `resume_from_last` 断点续跑能力，但 `compile()` 机制完全复用父类。

---

## D. 定义自定义 Pipeline 的完整模板

### D.1 官方脚手架原版（真实代码）

源文件：`dataflow/statics/scaffold/.../pipelines/my_pipeline.py:1-50`

```python
from {{cookiecutter.package_name}}.operators.core.my_format_str_prompted_generator import MyFormatStrPromptedGenerator
from {{cookiecutter.package_name}}.operators.core.my_prompted_generator import MyPromptedGenerator
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage
from dataflow.pipeline import PipelineABC
from {{cookiecutter.package_name}}.prompts.core import MyFormatStringPrompt

class MySimplePipeline(PipelineABC):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage(
            first_entry_file_name="../data/example_data.json",
            file_name_prefix="dataflow{{cookiecutter.package_name}}",
            cache_path="./cache",
            cache_type="jsonl",
        )
        self.llm_serving = APILLMServing_request(
            api_url="https://api.openai.com/v1/chat/completions",
            model_name="gpt-4o"
        )
        self.prompt_template = MyFormatStringPrompt(
            f_str_template="What does a {input_role} like to {input_term}?"
        )
        self.op1 = MyFormatStrPromptedGenerator(
            llm_serving=self.llm_serving, prompt_template=self.prompt_template)
        self.op2 = MyPromptedGenerator(
            llm_serving=self.llm_serving, system_prompt="Summary this answer")

    def forward(self):
        self.op1.run(storage=self.storage.step(),
                     input_role="role", input_term="term", output_key="answer")
        self.op2.run(storage=self.storage.step(),
                     input_key="answer", output_key="summary_answer")

if __name__ == "__main__":
    model = MySimplePipeline()
    model.compile()
    model.forward()
```

> 注意：`input_role="role"` / `input_term="term"` 中，`input_role`、`input_term` 都以 `input_` 开头 → 被识别为输入 key（`nodes.py:61`），值为列名 `"role"`/`"term"`。`output_key="answer"` 产生新列 `answer`，供 op2 的 `input_key="answer"` 引用。这就是编译期 key 校验链。

### D.2 官方真实 Pipeline 示例（PDF VQA，使用 compile）

源文件：`dataflow/statics/pipelines/api_pipelines/pdf_vqa_extract_pipeline.py:13-108`

```python
from dataflow.pipeline import PipelineABC
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage
from dataflow.operators.core_text import ChunkedPromptedGenerator
# ... 其它算子 import ...

class PDF_VQA_extract_optimized_pipeline(PipelineABC):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage(
            first_entry_file_name="./example_data/PDF2VQAPipeline/vqa_extract_test.jsonl",
            cache_path="./cache", file_name_prefix="vqa", cache_type="jsonl")
        self.llm_serving = APILLMServing_request(
            api_url="http://123.129.219.111:3000/v1/chat/completions",
            key_name_of_api_key="DF_API_KEY",
            model_name="gemini-2.5-pro", max_workers=100)
        self.pdf_merger = PDF_Merger(output_dir="./cache")
        self.mineru_executor = FileOrURLToMarkdownConverterFlash(...)
        self.input_formatter = MinerU2LLMInputOperator()
        self.vqa_extractor = ChunkedPromptedGenerator(
            llm_serving=self.llm_serving, system_prompt=..., max_chunk_len=128000)
        self.llm_output_parser = LLMOutputParser(...)
        self.qa_merger = QA_Merger(...)
        self.vqa_format_converter = VQAFormatter(...)

    def forward(self):
        self.pdf_merger.run(storage=self.storage.step(),
            input_pdf_list_key="input_pdf_paths", input_name_key="name",
            output_pdf_path_key="merged_pdf_path")
        self.mineru_executor.run(storage=self.storage.step(),
            input_key="merged_pdf_path", output_key="vqa_markdown_path")
        # ... 后续算子用 input_xxx_key 引用上一步 output_xxx_key 产生的列 ...

if __name__ == "__main__":
    pipeline = PDF_VQA_extract_optimized_pipeline()
    pipeline.compile()      # 编译期 key 校验
    pipeline.forward()      # 真正执行
```

### D.3 SRS 冲突检测 Pipeline 模板（基于真实接口）

```python
# srs_conflict/pipelines/srs_conflict_pipeline.py
from dataflow.pipeline import PipelineABC
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage
from srs_conflict.operators.srs_conflict_detector import SRSConflictDetector
# 假设还有抽取算子、聚合算子（见 G 节完整版）

class SRSConflictDetectionPipeline(PipelineABC):
    def __init__(self, input_file: str, api_url: str, model_name: str):
        super().__init__()
        self.storage = FileStorage(
            first_entry_file_name=input_file,
            cache_path="./cache_srs",
            file_name_prefix="srs_step",
            cache_type="jsonl",
        )
        self.llm_serving = APILLMServing_request(
            api_url=api_url,
            key_name_of_api_key="DF_API_KEY",
            model_name=model_name,
            max_workers=20,
        )
        # 算子作为 self 属性 → compile() 会把它们包装成 AutoOP
        self.conflict_detector = SRSConflictDetector(llm_serving=self.llm_serving)

    def forward(self):
        # 第一次调用时被 AutoOP 拦截记录 OPRuntime；compile 后被替换为 _compiled_forward 真正执行
        self.conflict_detector.run(
            storage=self.storage.step(),
            input_key="requirement_pair",     # 输入 key：必须存在于输入文件列名
            output_key="conflict_result",     # 输出 key：产生新列
        )

if __name__ == "__main__":
    import os
    os.environ.setdefault("DF_API_KEY", "sk-xxx")
    pl = SRSConflictDetectionPipeline(
        input_file="./srs_input.jsonl",
        api_url="https://api.openai.com/v1/chat/completions",
        model_name="gpt-4o",
    )
    pl.compile()    # 若 input_key "requirement_pair" 不在输入文件列里 → 这里抛 KeyError
    pl.forward()
```

---

## E. Storage 使用方式

源文件：`dataflow/utils/storage.py`

### E.1 DataFlowStorage 抽象基类（`storage.py:14-35`）

```python
class DataFlowStorage(ABC):
    @abstractmethod
    def get_keys_from_dataframe(self) -> list[str]:
        """Get keys from the dataframe stored in the storage."""
        pass
    @abstractmethod
    def read(self, output_type) -> Any:
        """Read data from file. type: 'dataframe' / List[dict] ..."""
        pass
    @abstractmethod
    def write(self, data: Any) -> Any:
        pass
```

### E.2 FileStorage（`storage.py:444-698`，磁盘即时落盘）

```python
class FileStorage(DataFlowStorage):
    def __init__(self,
                 first_entry_file_name: str,
                 cache_path: str = "./cache",
                 file_name_prefix: str = "dataflow_cache_step",
                 cache_type: Literal["json","jsonl","csv","parquet","pickle"] = "jsonl"):
        self.first_entry_file_name = first_entry_file_name
        self.cache_path = cache_path
        self.file_name_prefix = file_name_prefix
        self.cache_type = cache_type
        self.operator_step = -1          # ★ 初始为 -1，必须 step() 之后才能 read/write
        self.logger = get_logger()
```

**`step()` 真实实现（`storage.py:522-524`）：**
```python
def step(self):
    self.operator_step += 1
    return copy.copy(self)   # 浅拷贝，保持与原 FileStorage 兼容的使用方式
```

**`_get_cache_file_path()`（`storage.py:512-520`）——step 与文件路径映射：**
```python
def _get_cache_file_path(self, step) -> str:
    if step == -1:
        raise ValueError("You must call storage.step() before reading or writing data. ...")
    if step == 0:
        return os.path.join(self.first_entry_file_name)          # 第 0 步 = 原始输入文件
    else:
        return os.path.join(self.cache_path,
            f"{self.file_name_prefix}_step{step}.{self.cache_type}")  # 第 N 步 = cache/xxx_stepN.jsonl
```

**`read()`（`storage.py:566-629`）签名与行为：**
```python
def read(self, output_type: Literal["dataframe", "dict"] = "dataframe") -> Any:
    # step 0 支持 "hf:" / "ms:" 远程数据集前缀；本地按扩展名(json/jsonl/csv/parquet/pickle)读取
    # 返回 pandas.DataFrame（output_type="dataframe"）或 List[dict]（output_type="dict"）
```

**`write()`（`storage.py:631-698`）签名与行为：**
```python
def write(self, data: Any) -> Any:
    # data 可以是 List[dict] 或 pd.DataFrame
    # 内部递归 clean_surrogates 清理无效 Unicode 代理对
    # 写入路径 = _get_cache_file_path(self.operator_step + 1)   ← 注意是 step+1
    # 返回写入的文件路径
```

### E.3 完整使用示例

```python
from dataflow.utils.storage import FileStorage

storage = FileStorage(
    first_entry_file_name="./srs_input.jsonl",   # 第 0 步数据源
    cache_path="./cache_srs",
    file_name_prefix="srs_step",
    cache_type="jsonl",
)

# 每个算子调用前必须 step()
s0 = storage.step()          # operator_step=0, 返回浅拷贝
df = s0.read("dataframe")    # 读 ./srs_input.jsonl → DataFrame
print(df.columns.tolist())   # 列名 = key 集合

df["new_col"] = [...]        # 算子产出新列
s0.write(df)                 # 写到 ./cache_srs/srs_step_step1.jsonl

s1 = storage.step()          # operator_step=1
df1 = s1.read("dataframe")   # 读 ./cache_srs/srs_step_step1.jsonl
```

### E.4 LazyFileStorage（`storage.py:70-398`，内存缓冲 + 退出时落盘）

与 `FileStorage` 接口完全一致，区别：
- `write()` 只写内存 `_buffers`，不触盘（`storage.py:311-348`）
- `flush_step()` / `flush_all()` 才原子落盘（`os.replace`，`storage.py:351-397`）
- 注册 `atexit` / `SIGINT` / `SIGTERM` 钩子，进程退出时自动 flush（`storage.py:168-201`）

> **SRS 场景推荐 `FileStorage`**（每步即时落盘，断点可续）；大规模数据用 `LazyFileStorage` 提速。

---

## F. LLM Serving 使用方式

源文件：`dataflow/serving/api_llm_serving_request.py`

### F.1 `APILLMServing_request.__init__`（`api_llm_serving_request.py:21-73`）

```python
class APILLMServing_request(LLMServingABC):
    def start_serving(self) -> None:
        self.logger.info("APILLMServing_request: no local service to start.")
        return

    def __init__(self,
                 api_url: str = "https://api.openai.com/v1/chat/completions",
                 key_name_of_api_key: str = "DF_API_KEY",   # ★ 从环境变量取 key
                 model_name: str = "gpt-4o",
                 temperature: float = 0.0,
                 max_workers: int = 10,                      # ★ 并发线程数
                 max_retries: int = 5,                       # ★ 重试次数
                 connect_timeout: float = 10.0,
                 read_timeout: float = 120.0,
                 **configs: dict):
        self.api_url = api_url
        self.model_name = model_name
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.timeout = (connect_timeout, read_timeout)
        self.configs = configs
        self.configs.update({"temperature": temperature})
        self.logger = get_logger()

        self.api_key = os.environ.get(key_name_of_api_key)   # ★ key 必须先放环境变量
        if self.api_key is None:
            raise ValueError(f"Lack of `{key_name_of_api_key}` in environment variables. ...")

        # requests.Session + 连接池（pool_connections=pool_maxsize=max_workers）
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=self.max_workers, pool_maxsize=self.max_workers,
                              max_retries=0, pool_block=True)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.headers = {'Authorization': f"Bearer {self.api_key}",
                        'Content-Type': 'application/json',
                        'User-Agent': 'Apifox/1.0.0 (https://apifox.com)'}
```

### F.2 `generate_from_input` — 并发 + 重试（真实实现）

```python
# api_llm_serving_request.py:251-268
def generate_from_input(self,
                        user_inputs: list[str],
                        system_prompt: str = "You are a helpful assistant",
                        json_schema: dict = None,
                        ) -> list[str]:
    task_args_list = [
        dict(id=idx,
             payload=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": question}],
             model=self.model_name,
             json_schema=json_schema)
        for idx, question in enumerate(user_inputs)
    ]
    return self._run_threadpool(task_args_list, desc="Generating responses from prompts......")

# api_llm_serving_request.py:226-249  ThreadPoolExecutor 并发
def _run_threadpool(self, task_args_list: list[dict], desc: str) -> list:
    responses = [None] * len(task_args_list)
    with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
        futures = [executor.submit(self._api_chat_id_retry, **task_args) for task_args in task_args_list]
        for future in tqdm(as_completed(futures), total=len(futures), desc=desc):
            try:
                response = future.result()          # (id, response)
                responses[response[0]] = response[1]  # 按 id 回填，保证顺序
            except Exception:
                self.logger.exception("Worker crashed unexpectedly in threadpool")
    return responses

# api_llm_serving_request.py:218-224  指数退避重试
def _api_chat_id_retry(self, id, payload, model, is_embedding=False, json_schema=None):
    for i in range(self.max_retries):
        id, response = self._api_chat_with_id(id, payload, model, is_embedding, json_schema)
        if response is not None:
            return id, response
        time.sleep(2 ** i)        # 指数退避：1,2,4,8,16s
    return id, None
```

### F.3 返回值格式

`generate_from_input` 返回 `list[str]`，与输入 `user_inputs` **等长且同序**（靠 `responses[id]` 回填）。
- 若模型返回 `reasoning_content`（思考链），`format_response`（`api_llm_serving_request.py:76-98`）会包成 `<think>...</think>\n<answer>...</answer>`。
- 若请求带 `json_schema`，payload 会加 `response_format`（`api_llm_serving_request.py:148-160`），模型应返回 JSON 字符串。

### F.4 完整使用示例

```python
import os
from dataflow.serving import APILLMServing_request

os.environ["DF_API_KEY"] = "sk-xxx"   # ★ 必须先设环境变量

llm = APILLMServing_request(
    api_url="https://api.openai.com/v1/chat/completions",
    key_name_of_api_key="DF_API_KEY",
    model_name="gpt-4o",
    max_workers=20,        # 并发
    max_retries=5,         # 重试
    temperature=0.0,
)

result = llm.generate_from_input(
    user_inputs=["判断需求A与需求B是否冲突: ...", "判断需求C与需求D是否冲突: ..."],
    system_prompt="你是 SRS 一致性审查专家。",
    json_schema={"type": "object", "properties": {"has_conflict": {"type": "boolean"}}, "required": ["has_conflict"]},
)
# result = ['{"has_conflict": true}', '{"has_conflict": false}']

llm.cleanup()   # 释放 session
```

> **错误处理约定（`api_llm_serving_request.py:176-216`）：** ConnectTimeout/ConnectionError(非读超时) 直接抛 `RuntimeError`（连不上服务器）；ReadTimeout 返回 `(id, None)`（可达但推理超时），由重试逻辑兜底。

---

## G. 完整的 SRS 冲突检测 Pipeline（可直接运行）

下面给出一个**端到端可运行**的完整代码，包含：3 个自定义算子 + Pipeline + 运行脚本 + 输入样例。严格基于真实基类接口。

### G.1 项目结构（遵循官方脚手架 `__init__.py` 自动注册机制）

```
srs_conflict/
├── __init__.py                 # 自动 import operators/* 触发注册（见附节）
├── operators/
│   ├── __init__.py
│   ├── srs_pair_builder.py     # 算子1：构建需求对
│   ├── srs_conflict_detector.py# 算子2：LLM 冲突检测
│   └── srs_conflict_aggregator.py # 算子3：聚合冲突报告
├── prompts/
│   └── core.py                 # PromptABC 模板
├── pipelines/
│   └── srs_conflict_pipeline.py
└── data/
    └── srs_input.jsonl
```

### G.2 `srs_conflict/__init__.py`（自动注册，真实模板）

来自官方脚手架 `.../{{cookiecutter.package_name}}/__init__.py:1-36`：

```python
import importlib, pkgutil

def _auto_import_operators():
    """递归 import operators.* 下所有模块，触发 @OPERATOR_REGISTRY.register()"""
    base_pkg_name = __name__ + ".operators"
    try:
        operators_pkg = importlib.import_module(base_pkg_name)
    except ImportError:
        return
    for _, module_name, is_pkg in pkgutil.walk_packages(
        operators_pkg.__path__, operators_pkg.__name__ + "."
    ):
        importlib.import_module(module_name)

_auto_import_operators()   # ★ import srs_conflict 即自动注册所有算子
```

### G.3 算子1：构建需求对（纯 Python，无 LLM）

```python
# srs_conflict/operators/srs_pair_builder.py
from dataflow.utils.registry import OPERATOR_REGISTRY
from dataflow import get_logger
from dataflow.utils.storage import DataFlowStorage
from dataflow.core import OperatorABC
import itertools, json

@OPERATOR_REGISTRY.register()
class SRSPairBuilder(OperatorABC):
    """把单条需求项两两配对，生成待检测的需求对。"""
    def __init__(self):
        self.logger = get_logger()

    @staticmethod
    def get_desc(lang: str = "zh"):
        return "把输入的 requirement 列表两两配对，输出 requirement_pair 列。"

    def run(self, storage: DataFlowStorage,
            input_key: str = "requirement",          # 输入 key：需求文本列
            input_id_key: str = "req_id",            # 输入 key：需求编号列
            output_key: str = "requirement_pair"):   # 输出 key：配对文本
        self.logger.info("Running SRSPairBuilder...")
        dataframe = storage.read('dataframe')
        reqs = [(row.get(input_id_key, str(i)), row.get(input_key, ''))
                for i, row in dataframe.iterrows() if row.get(input_key)]

        pairs = []
        for (id_a, text_a), (id_b, text_b) in itertools.combinations(reqs, 2):
            pairs.append({
                "req_id_a": id_a, "req_id_b": id_b,
                "requirement_pair": f"需求 {id_a}:\n{text_a}\n\n需求 {id_b}:\n{text_b}",
            })
        out_df = storage.read('dataframe').iloc[0:0]  # 取空结构
        import pandas as pd
        out_df = pd.DataFrame(pairs)
        storage.write(out_df)
        return output_key
```

### G.4 算子2：LLM 冲突检测（见 B.2，此处略）

### G.5 算子3：聚合冲突报告

```python
# srs_conflict/operators/srs_conflict_aggregator.py
from dataflow.utils.registry import OPERATOR_REGISTRY
from dataflow import get_logger
from dataflow.utils.storage import DataFlowStorage
from dataflow.core import OperatorABC
import pandas as pd

@OPERATOR_REGISTRY.register()
class SRSConflictAggregator(OperatorABC):
    """汇总冲突检测结果，生成冲突报告列。"""
    def __init__(self):
        self.logger = get_logger()

    @staticmethod
    def get_desc(lang: str = "zh"):
        return "统计冲突数量，输出 conflict_summary 列。"

    def run(self, storage: DataFlowStorage,
            input_key: str = "conflict_result",      # 输入 key：上一步检测结果
            output_key: str = "conflict_summary"):   # 输出 key：汇总
        self.logger.info("Running SRSConflictAggregator...")
        dataframe = storage.read('dataframe')
        conflicts = []
        for _, row in dataframe.iterrows():
            res = row.get(input_key)
            if isinstance(res, dict):
                conflicts.append(res.get("has_conflict", False))
            elif isinstance(res, str):
                import json
                try:
                    conflicts.append(json.loads(res).get("has_conflict", False))
                except Exception:
                    conflicts.append(False)
            else:
                conflicts.append(False)
        dataframe[output_key] = [
            {"total_pairs": len(conflicts),
             "conflict_count": sum(1 for c in conflicts if c),
             "is_conflict": bool(c)} for c in conflicts
        ]
        storage.write(dataframe)
        return output_key
```

### G.6 Pipeline（核心）

```python
# srs_conflict/pipelines/srs_conflict_pipeline.py
from dataflow.pipeline import PipelineABC
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage
# import srs_conflict  # 触发算子自动注册（若作为包安装则 import 即注册）

from srs_conflict.operators.srs_pair_builder import SRSPairBuilder
from srs_conflict.operators.srs_conflict_detector import SRSConflictDetector
from srs_conflict.operators.srs_conflict_aggregator import SRSConflictAggregator

class SRSConflictDetectionPipeline(PipelineABC):
    def __init__(self, input_file: str, api_url: str, model_name: str,
                 max_workers: int = 20):
        super().__init__()
        self.storage = FileStorage(
            first_entry_file_name=input_file,
            cache_path="./cache_srs",
            file_name_prefix="srs_step",
            cache_type="jsonl",
        )
        self.llm_serving = APILLMServing_request(
            api_url=api_url,
            key_name_of_api_key="DF_API_KEY",
            model_name=model_name,
            max_workers=max_workers,
            max_retries=5,
            temperature=0.0,
        )
        # 三个算子作为 self 属性 → compile() 包装成 AutoOP
        self.pair_builder = SRSPairBuilder()
        self.conflict_detector = SRSConflictDetector(llm_serving=self.llm_serving)
        self.aggregator = SRSConflictAggregator()

    def forward(self):
        # 算子1：requirement + req_id → requirement_pair
        self.pair_builder.run(
            storage=self.storage.step(),
            input_key="requirement",       # 输入 key（来自输入文件列）
            input_id_key="req_id",         # 输入 key（来自输入文件列）
            output_key="requirement_pair", # 输出 key
        )
        # 算子2：requirement_pair → conflict_result
        self.conflict_detector.run(
            storage=self.storage.step(),
            input_key="requirement_pair",  # ★ 引用算子1的输出 key（编译期校验）
            output_key="conflict_result",  # 输出 key
        )
        # 算子3：conflict_result → conflict_summary
        self.aggregator.run(
            storage=self.storage.step(),
            input_key="conflict_result",   # ★ 引用算子2的输出 key
            output_key="conflict_summary", # 输出 key
        )

if __name__ == "__main__":
    import os, json
    os.environ.setdefault("DF_API_KEY", "sk-xxx")

    pl = SRSConflictDetectionPipeline(
        input_file="./srs_conflict/data/srs_input.jsonl",
        api_url="https://api.openai.com/v1/chat/completions",
        model_name="gpt-4o",
        max_workers=20,
    )
    pl.compile()    # 编译期 key 校验：requirement/req_id 必须在输入文件列里
    pl.forward()    # 真正执行三步算子

    # 读取最终结果
    import pandas as pd
    out_path = pl.storage._get_cache_file_path(pl.storage.operator_step)
    df = pd.read_json(out_path, lines=True)
    print(json.dumps(df.iloc[0]["conflict_summary"], ensure_ascii=False, indent=2))
    print(f"输出文件: {out_path}, 共 {len(df)} 条")
```

### G.7 输入样例 `srs_input.jsonl`

```json
{"req_id": "R001", "requirement": "系统应在5秒内完成目标识别。"}
{"req_id": "R002", "requirement": "系统应在2秒内完成目标识别。"}
{"req_id": "R003", "requirement": "系统支持同时跟踪10个目标。"}
{"req_id": "R004", "requirement": "系统工作温度范围-40℃至+70℃。"}
```

> **编译期 key 校验链：** 输入文件列 = `{req_id, requirement}` → 算子1 输入 `requirement`/`req_id` ✓，输出 `requirement_pair` → 算子2 输入 `requirement_pair` ✓，输出 `conflict_result` → 算子3 输入 `conflict_result` ✓，输出 `conflict_summary`。任何一环 key 名拼错，`compile()` 立即抛 `KeyError` 指出哪个算子的哪个参数不匹配。

---

## H. AutoOP 编译期 key 校验的实际代码

### H.1 AutoOP 包装器（`dataflow/wrapper/auto_op.py:38-105` 完整）

```python
class AutoOP(Generic[P, R]):
    """自动化运行 Operator 的 Wrapper。
    在静态检查/IDE 里，AutoOp.run 的签名和 operator.run 完全一致。
    运行时，会把 operator.run 的 __doc__ 和 __signature__ 也拷过来。"""

    def __init__(self, operator: HasRun[P, R], operator_name, pipeline):
        self._operator = operator
        self._operator_name = operator_name
        self._pipeline = pipeline          # <class PipelineABC>
        self._logger = get_logger()
        self._orig_run = operator.run
        self._signature = inspect.signature(operator.run)
        self.__doc__ = self._orig_run.__doc__

    def _flatten_bound_arguments(self, bound, sig):
        """把 bound.arguments 中的 **kwargs 展平到顶层，保留调用顺序。"""
        var_kw_name = None
        for name, p in sig.parameters.items():
            if p.kind == inspect.Parameter.VAR_KEYWORD:
                var_kw_name = name
                break
        out = OrderedDict()
        for name, value in bound.arguments.items():
            if name == var_kw_name and isinstance(value, dict):
                for k, v in value.items():
                    out[k] = v
            else:
                out[name] = value
        return out

    def run(self, *args, **kwargs):
        # ★ 关键：不真正执行 operator.run，只记录 OPRuntime
        self._signature = inspect.signature(self._orig_run)
        bound_args = self._signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        final_kwargs = self._flatten_bound_arguments(bound_args, self._signature)
        self._logger.debug(final_kwargs)
        self._pipeline.op_runtimes.append(
            OPRuntime(
                operator=self._operator,
                operator_name=self._operator_name,
                args=dict(final_kwargs)     # ← 记录所有参数（含 storage, input_xxx, output_xxx）
            )
        )
        # 注意：这里没有 return、没有真正调用 self._orig_run ！
```

### H.2 OPRuntime 数据结构（`auto_op.py:20-36`）

```python
class OPRuntime:
    def __init__(self, operator, operator_name, args: Dict[str, Any]):
        self.op = operator
        self.op_name = operator_name
        self.kwargs = args          # run() 的所有实参（已展平 **kwargs）
        self.logger = get_logger()
```

### H.3 OperatorNode 如何识别 key（`dataflow/pipeline/nodes.py:59-66`）

```python
class OperatorNode(object):
    def _get_keys_from_kwargs(self):
        for k, v in self.kwargs.items():
            if k.startswith("input_") and isinstance(v, str):    # ★ 规则1
                self.input_keys.append(v)
                self.input_key_nodes[v] = KeyNode(k, v)
            elif k.startswith("output_") and isinstance(v, str): # ★ 规则2
                self.output_keys.append(v)
                self.output_keys_nodes[v] = KeyNode(k, v)
            else:
                print(f"\033[91mWarning: Unexpected key '{k}' in operator {self.op_obj.__class__.__name__}\033[0m")
```

### H.4 完整校验流程（串起来）

1. **`compile()`** 遍历 `vars(self)`，把每个 `OperatorABC` 实例替换成 `AutoOP`（`Pipeline.py:45-47`）。
2. **`compile()` 调 `self.forward()`** —— 此时 `op.run(...)` 实际调用 `AutoOP.run`，它用 `inspect.signature.bind` 把实参绑定，展平 `**kwargs`，记录到 `self._pipeline.op_runtimes`，**不执行**。
3. **`compile()` 调 `_build_operator_nodes_graph()`** —— 遍历 `op_runtimes`，为每个构造 `OperatorNode`。`OperatorNode._get_keys_from_kwargs` 按 `input_`/`output_` 前缀 + 字符串类型识别 key。
4. **key 依赖图校验**（`Pipeline.py:105-135`）：
   - 初始 `accumulated_keys[0]` = 第一个 storage 的所有列名（`get_keys_from_dataframe`）。
   - 对每个 op：所有 `input_key` 必须在 `accumulated_keys[-1]` 里，否则记入 `error_msg`；`output_key` 加入累积集合。
   - 若 `error_msg` 非空 → `raise KeyError`，错误信息精确指出哪个算子的哪个参数引用了不存在的 key。
5. **`self.forward = self._compiled_forward`** —— 之后用户再调 `forward()` 才真正按图执行。

### H.5 一个会失败的例子（演示校验）

```python
# 假设输入文件列只有 requirement, req_id
class BadPipeline(PipelineABC):
    def forward(self):
        self.pair_builder.run(
            storage=self.storage.step(),
            input_key="requirement",
            input_id_key="req_id",
            output_key="requirement_pair",
        )
        self.conflict_detector.run(
            storage=self.storage.step(),
            input_key="requirement_par",   # ← 拼错，应为 requirement_pair
            output_key="conflict_result",
        )
BadPipeline().compile()
# → KeyError: Key Matching Error in following Operators during pipeline.compile():
#   - Input key 'requirement_par' in `conflict_detector` (class <SRSConflictDetector>)
#     does not match any output keys from previous operators or dataset keys.
#     Check parameter 'input_key' in the `conflict_detector.run()`.
```

---

## 附: Prompt 模板系统 / CLI 脚手架 / WebUI 动态发现

### 附.1 PromptABC + prompt_restrict 装饰器

源文件：`dataflow/core/prompt.py:6-78`

```python
class PromptABC():
    def __init__(self):
        pass
    def build_prompt(self):
        raise NotImplementedError

class DIYPromptABC(PromptABC):
    def __init__(self):
        super().__init__()
    def build_prompt(self):
        raise NotImplementedError

def prompt_restrict(*allowed_prompts: type[DIYPromptABC]):
    """装饰器：限制 prompt_template 只能是指定 Prompt 类 或 DIYPromptABC 子类，
    并在运行时检查 & 更新 __annotations__。"""
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

**真实用法（官方脚手架 `my_format_str_prompted_generator.py:13-31`）：**

```python
from dataflow.core.prompt import prompt_restrict, DIYPromptABC
from srs_conflict.prompts.core import SRSConflictPrompt

@prompt_restrict(SRSConflictPrompt)          # 限制只能用 SRSConflictPrompt 或其 DIY 子类
@OPERATOR_REGISTRY.register()
class SRSConflictDetector(OperatorABC):
    def __init__(self, llm_serving, system_prompt="...",
                 prompt_template: Union[SRSConflictPrompt, DIYPromptABC] = SRSConflictPrompt,
                 json_schema=None):
        ...
```

**Prompt 注册（`dataflow/prompts/core_text.py:4-31` 真实示例）：**

```python
from dataflow.utils.registry import PROMPT_REGISTRY
from dataflow.core.prompt import PromptABC

@PROMPT_REGISTRY.register()
class FormatStrPrompt(PromptABC):
    def __init__(self, f_str_template: str = "{input_text}", on_missing: str = "raise"):
        self.f_str_template = f_str_template
        self.on_missing = on_missing
    def build_prompt(self, need_fields, **kwargs):
        missing = [f for f in need_fields if f not in kwargs]
        if missing and self.on_missing == "raise":
            raise KeyError(f"Missing fields for prompt: {missing}")
        prompt = self.f_str_template
        for key, value in kwargs.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        return prompt
```

### 附.2 CLI 脚手架生成（`dataflow/cli.py` + `cli_funcs/cli_init.py`）

**CLI 命令结构（`cli.py:222-280`）：**
```bash
dataflow init repo          # 用 cookiecutter 生成扩展包脚手架
dataflow init operator      # TODO（占位）
dataflow init pipeline      # TODO（占位）
dataflow init prompt        # TODO（占位）
dataflow init               # base: 复制 pipelines/example_data/playground 到当前目录
```

**`init_repo_scaffold` 真实实现（`cli_init.py:59-136`）：**
```python
def init_repo_scaffold(no_input=False, context=None):
    from cookiecutter.main import cookiecutter
    from .paths import DataFlowPath
    template_path = DataFlowPath.get_dataflow_scaffold_dir()
    output_dir = Path.cwd()
    generated_path = cookiecutter(
        template=str(template_path),
        no_input=no_input,
        extra_context=context,
        output_dir=str(output_dir),
    )
    print(f"📁 Project path: {generated_path}")
    print("Next steps:")
    print("  1. cd <project>")
    print("  2. pip install -e .   # 编辑模式安装，触发算子注册")
    print("  3. git init && git add . && git commit -m 'Initial commit'")
```

**`cookiecutter.json`（`scaffold/cookiecutter.json`）变量：** `repo_name` / `package_name` / `author` / `license` / `python_version` / `include_examples`。生成的包结构含 `operators/core/`、`pipelines/`、`prompts/`、`data/example_data.json`、`test/test_registed_op.py`。

**注册测试（`test/test_registed_op.py:32-78`）** 校验 import 扩展包后 `OPERATOR_REGISTRY`/`PROMPT_REGISTRY` 新增了条目。

### 附.3 WebUI 动态算子发现（`dataflow/webui/operator_pipeline.py`）

**`DynamicOperatorSystem`（`operator_pipeline.py:48-172`）核心：**

```python
class DynamicOperatorSystem:
    def __init__(self):
        OPERATOR_REGISTRY._get_all()          # 强制加载所有算子
        self.operators: Dict[str, OperatorInfo] = {}
        self._discover_operators()
        self._discover_pipelines()

    def _discover_operators(self):
        for name, obj in OPERATOR_REGISTRY.get_obj_map().items():
            info = self._analyze_operator(name, obj)
            self.operators[name] = info

    def _analyze_operator(self, name, obj):    # ★ 反射 __init__ 和 run 签名
        init_sig = inspect.signature(obj.__init__)
        init_params = extract(init_sig, exclude=["self"])
        run_params = []
        if hasattr(obj, "run"):
            run_sig = inspect.signature(obj.run)
            run_params = extract(run_sig, exclude=["self", "storage"])  # 排除 storage
        return OperatorInfo(name, obj, init_params, run_params, desc)

    def _discover_pipelines(self):             # 遍历 statics/pipelines/api_pipelines/*.py
        for fn in os.listdir(path):
            if fn.endswith(".py") and not fn.startswith("__"):
                info = self._analyze_pipeline(...)   # importlib 动态加载，找 *Pipeline 类
```

**WebUI 执行算子（`operator_pipeline.py:397-427`）：**
```python
def gradio_run(op_name, init_str, run_str, api_url, model_name, api_key, max_workers, ...):
    other_init = json.loads(init_str)
    run_params = json.loads(run_str)
    info = dynamic_system.get_operator_info(op_name)
    if any(p.name == "llm_serving" for p in info.init_params):
        other_init["llm_serving"] = dynamic_system.create_serving_instance("API", ...)
    op_inst = info.class_obj(**other_init)
    storage = dynamic_system.create_storage_instance(...)
    op_inst.run(storage=storage.step(), **run_params)   # ★ 单算子直接 run
```

> **对本项目的意义：** WebUI 模式**不走 compile()**，所以没有编译期 key 校验——适合快速试单个算子；生产 Pipeline 应该用 `PipelineABC.compile()` 拿到 key 依赖图校验和断点续跑。

---

## 总结：SRS 冲突检测 Pipeline 落地要点

| 关注点 | 真实接口 | 文件:行号 |
|--------|---------|----------|
| 算子基类 | `OperatorABC.run()` 唯一抽象方法 | `core/operator.py:5-15` |
| 算子注册 | `@OPERATOR_REGISTRY.register()` | `utils/registry.py:257,85-98` |
| Pipeline 基类 | `PipelineABC.forward()` 抽象 | `pipeline/Pipeline.py:18-41` |
| 编译期校验 | `compile()` → AutoOP 拦截 → key 图 | `pipeline/Pipeline.py:43-143` |
| key 识别规则 | `input_`/`output_` 前缀 + str 类型 | `pipeline/nodes.py:61-66` |
| 数据流转 | `storage.step()/read()/write()` | `utils/storage.py:522-698` |
| LLM 调用 | `llm.generate_from_input()` | `serving/api_llm_serving_request.py:251-268` |
| 运行模式 | `pl.compile(); pl.forward()` | scaffold `my_pipeline.py:48-50` |

**最小可运行路径：**
1. `pip install -e .` 安装扩展包 → import 时 `_auto_import_operators()` 自动注册算子。
2. 准备 `srs_input.jsonl`（含 `requirement`/`req_id` 列）。
3. `export DF_API_KEY=sk-xxx`。
4. `python srs_conflict/pipelines/srs_conflict_pipeline.py` → `compile()` 校验 key → `forward()` 执行三步 → 读 `cache_srs/srs_step_step3.jsonl` 取冲突报告。

**与本项目 SRS 一致性检测的对接建议：** 把 `srs_pair_builder` 的输入换成 MinerU 结构化 JSON 的 `requirement` 列；`conflict_detector` 的 `system_prompt` 换成三层（语法/语义/逻辑）检测 prompt；`aggregator` 输出对齐 Gold Standard 后用 `tools/srs_eval.py` 计算 P/R/F1。DataFlow 负责编排与并发，本项目的 Z3 求解/规则库可封装成不依赖 LLM 的算子（`__init__` 不传 `llm_serving`，`run` 内部调 Z3）。
