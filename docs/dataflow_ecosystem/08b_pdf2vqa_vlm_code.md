# DataFlow pdf2vqa / VLM Serving 实际可复现代码提取

> 本文件从 DataFlow 克隆源码（`dataflow_repos/DataFlow/`）中逐文件精读，提取**实际可调用**的 API 签名、`run()` 实现、输入输出格式与完整 Pipeline 组装代码，用于驱动 SRS 文档的图片-文本对比与冲突检测。
>
> 所有代码块均标注源文件路径与行号，可直接对照查阅。

---

## 目录

1. [架构与调用关系总览](#1-架构与调用关系总览)
2. [Storage 使用方式](#2-storage-使用方式)
3. [pdf2vqa 算子完整 API](#3-pdf2vqa-算子完整-api)
4. [core_vision 算子完整 API](#4-core_vision-算子完整-api)
5. [VLM / LLM Serving 完整 API](#5-vlm--llm-serving-完整-api)
6. [KB Cleaning 算子完整 API](#6-kb-cleaning-算子完整-api)
7. [Prompt 模板](#7-prompt-模板)
8. [Pipeline 组装完整代码](#8-pipeline-组装完整代码)
9. [完整调用示例](#9-完整调用示例)
10. [SRS 图片-文本冲突检测方案](#10-srs-图片-文本冲突检测方案)

---

## 1. 架构与调用关系总览

```
┌─────────────────────────────────────────────────────────────┐
│ Pipeline (PipelineABC)                                       │
│   __init__: 实例化 storage + serving + operators            │
│   forward():  依次 op.run(storage.step(), in_key, out_key)  │
└─────────────────────────────────────────────────────────────┘
        │ 依赖
        ▼
┌──────────────┐   read/write/step   ┌──────────────────────┐
│ FileStorage  │ ◄──────────────────► │ OperatorABC.run()    │
│ (step计数器) │                      │  读 dataframe        │
└──────────────┘                      │  调 serving.generate │
                                      │  写回 dataframe      │
                                      └──────────┬───────────┘
                                                 │ 调用
                                                 ▼
                                      ┌──────────────────────┐
                                      │ LLMServingABC        │
                                      │  ├ APILLMServing_*   │ 纯文本
                                      │  ├ APIVLMServing_*   │ 图文(OpenAI协议)
                                      │  └ LocalVLMServing_* │ 本地vLLM
                                      └──────────────────────┘
```

**核心抽象（`dataflow/core/__init__.py:1-18`）**：
- `OperatorABC`（`dataflow/core/operator.py`）：算子基类，约定 `run(storage, ...)`。
- `LLMServingABC`（`dataflow/core/llm_serving.py:5-35`）：serving 基类，约定 `generate_from_input(user_inputs: List[str], system_prompt: str) -> List[str]`、`start_serving()`、`cleanup()`。
- `DataFlowStorage`（`dataflow/utils/storage.py:14-69`）：存储抽象，约定 `read(output_type)`、`write(data)`、`step()`。

**关键点**：所有算子通过 `storage.read("dataframe")` 取 pandas DataFrame，处理后 `storage.write(dataframe)` 回写；每个算子调用前先 `storage.step()` 推进步号（`operator_step` 从 -1 递增）。

---

## 2. Storage 使用方式

源文件：`dataflow/utils/storage.py`

### 2.1 FileStorage（磁盘落盘版，pipeline 默认用）

`dataflow/utils/storage.py:444-698`

```python
class FileStorage(DataFlowStorage):
    def __init__(
        self,
        first_entry_file_name: str,            # step0 输入文件路径(决定读取方式:json/jsonl/csv/parquet/pickle)
        cache_path: str = "./cache",           # step>=1 缓存目录
        file_name_prefix: str = "dataflow_cache_step",  # 缓存文件名前缀
        cache_type: Literal["json","jsonl","csv","parquet","pickle"] = "jsonl",
    ):
        ...
        self.operator_step = -1   # 初始步号
```

**`step()` 实现（`storage.py:522-524`）**：
```python
def step(self):
    self.operator_step += 1
    return copy.copy(self)   # 返回浅拷贝，保持调用方式兼容
```

**`read()`（`storage.py:566-629`）**：按 `operator_step` 取对应文件路径，step0 读 `first_entry_file_name`（支持 `hf:`/`ms:` 前缀拉远端数据集），step>=1 读 `{cache_path}/{file_name_prefix}_step{step}.{cache_type}`；返回 DataFrame 或 list[dict]。

**`write()`（`storage.py:631-698`）**：把 list[dict] 或 DataFrame 写到 `operator_step + 1` 对应路径，返回该路径。

### 2.2 调用范式

```python
from dataflow.utils.storage import FileStorage

storage = FileStorage(
    first_entry_file_name="./input.jsonl",
    cache_path="./cache",
    file_name_prefix="srs_vlm",
    cache_type="jsonl",
)
# 每个算子调用前推进一步
op.run(storage.step(), input_key="source", output_key="text_path")
```

### 2.3 输入文件格式

**pdf2vqa 输入**（`dataflow/example/PDF2VQAPipeline/vqa_extract_test.jsonl`）：
```jsonl
{"input_pdf_paths": "./example_data/PDF2VQAPipeline/questionextract_test.pdf", "name": "math1"}
{"input_pdf_paths": ["./example_data/PDF2VQAPipeline/math_question.pdf", "./example_data/PDF2VQAPipeline/math_answer.pdf"], "name": "math2"}
```

**KB cleaning 输入**（`dataflow/example/KBCleaningPipeline/kbc_test_1.jsonl`）：
```jsonl
{"source": "../example_data/KBCleaningPipeline/bitter_lesson.pdf"}
{"source": "https://arxiv.org/pdf/2505.07773"}
```

---

## 3. pdf2vqa 算子完整 API

源目录：`dataflow/operators/pdf2vqa/generate/`（共 5 个算子，`__init__.py` 用 LazyLoader 暴露）。

### 3.1 MinerU2LLMInputOperator

源文件：`dataflow/operators/pdf2vqa/generate/mineru_to_llm_input_operator.py:8-76`

```python
@OPERATOR_REGISTRY.register()
class MinerU2LLMInputOperator(OperatorABC):
    def __init__(self):
        pass

    def _convert_json(self, input_file, output_file):
        # 读取 MinerU 的 *_content_list.json
        # 展平 list 项、删除 bbox/page_idx、重新编号 id
        # 写到 *_converted.json
        ...

    def run(self, storage: DataFlowStorage,
            input_markdown_path_key,          # MinerU 输出的 .md 路径列名
            output_converted_layout_key,      # 转换后 *_converted.json 路径列名
            ):
```

**逻辑**（`mineru_to_llm_input_operator.py:55-76`）：对每行，取 `md_path` 的父目录下 `*_content_list.json`，展平为 `[{"type","text","id"}, ...]`，写到 `*_converted.json`。

**输入 MinerU content_list 示例**：
```json
[
  {"type":"text","text":"第三章 需求","bbox":[...],"page_idx":0},
  {"type":"list","sub_type":"text","list_items":["需求1","需求2"],"bbox":[...],"page_idx":0},
  {"type":"image","img_path":"images/3.jpg","image_caption":"图1","bbox":[...],"page_idx":1}
]
```

**输出 converted 示例**（去 bbox/page_idx，list 展平，id 重编号）：
```json
[
  {"type":"text","text":"第三章 需求","id":0},
  {"type":"text","text":"需求1","id":1},
  {"type":"text","text":"需求2","id":2},
  {"type":"image","img_path":"images/3.jpg","image_caption":"图1","id":3}
]
```

### 3.2 PDF_Merger

源文件：`dataflow/operators/pdf2vqa/generate/pdf_merger.py:7-83`

```python
@OPERATOR_REGISTRY.register()
class PDF_Merger(OperatorABC):
    def __init__(self, output_dir: str):
        # output_dir: 合并后 PDF 存放根目录
        ...

    def run(self,
            storage: DataFlowStorage,
            input_pdf_list_key: str,   # 列名, 值为 str 或 list[str] 的 PDF 路径
            input_name_key: str,       # 列名, 用于命名的标识(如文件名/ID)
            output_pdf_path_key: str,  # 输出列名, 写入合并后路径
            ):
```

**逻辑**（`pdf_merger.py:49-81`）：用 `pypdf.PdfWriter` 顺序 `append`，输出 `{output_dir}/{name}/{name}_merged.pdf`。

### 3.3 LLMOutputParser

源文件：`dataflow/operators/pdf2vqa/generate/llm_output_parser.py:12-146`

```python
@OPERATOR_REGISTRY.register()
class LLMOutputParser(OperatorABC):
    def __init__(self,
                 output_dir,                          # 输出根目录
                 intermediate_dir: str = "intermediate",
                 ):

    def _id_to_text(self, input_ids, input_json, image_prefix="images"):
        # 把 LLM 输出的 "2,3,5" 形式 id 串 → 在 converted.json 中取 text/table_body/img_path
        # 图片转为 Markdown: ![caption](image_prefix/img_name)
        ...

    def _convert_response(self, input_response, input_json_path, image_prefix="images"):
        # 解析 LLM 响应中的 <chapter>/<qa_pair>/<title>/<question>/<answer>/<solution>/<label>
        # 返回 qa_list
        ...

    def run(self, storage: DataFlowStorage,
            input_response_path_key,                # LLM 响应 txt 路径列名
            input_converted_layout_path_key,        # converted.json 路径列名
            input_name_key,                         # 标识列名
            output_qalist_path_key,                 # 输出 extracted_vqa.jsonl 路径列名
            ):
```

**逻辑**（`llm_output_parser.py:103-145`）：读取 LLM 响应文本（含 `<chapter>/<qa_pair>` 标签），按 id 把问题/解法还原成文本+图片 Markdown，复制图片到 `{output_dir}/{name}/vqa_images/`，写出 `extracted_vqa.jsonl`。

**LLM 响应格式（由 QAExtractPrompt 约束）**：
```
<chapter><title>7</title>
<qa_pair><label>1</label><question>2,3</question>
<answer>Yes</answer><solution>5,6,7</solution></qa_pair>
</chapter>
```

**输出 extracted_vqa.jsonl 每行**：
```json
{"question":"![图1](vqa_images/3.jpg)求x使x²-1=0","answer":"Yes","solution":"由x²=1...","label":"1","chapter_title":"7"}
```

### 3.4 QA_Merger

源文件：`dataflow/operators/pdf2vqa/generate/qa_merger.py:10-84`

```python
@OPERATOR_REGISTRY.register()
class QA_Merger(OperatorABC):
    def __init__(self, output_dir, strict_title_match=False):
        ...

    def run(self, storage: DataFlowStorage,
            input_qalist_path_key,             # extracted_vqa.jsonl 路径列名
            input_name_key,                    # 标识列名
            output_merged_qalist_path_key,     # 合并后 merged_qa_pairs.jsonl 路径列名
            output_merged_md_path_key,         # 合并后 .md 路径列名
            output_qa_item_key="qa_item",      # 展开后的单条 QA 内容列名
            ):
```

**逻辑**（`qa_merger.py:31-82`）：调 `merge_qa_pair`（`utils/pdf2vqa/format_utils.py:21`）按 `(chapter_title,label)` 配对 question 与 answer/solution；`jsonl_to_md` 转 Markdown；随后 `dataframe.explode(output_qa_item_key)` 把每条 QA 展开成单独行。

### 3.5 VQAFormatter

源文件：`dataflow/operators/pdf2vqa/generate/vqa_formatter.py:16-257`

```python
@OPERATOR_REGISTRY.register()
class VQAFormatter(OperatorABC):
    def __init__(self,
                 output_json_file: Optional[str] = None,  # 输出 ShareGPT JSON 路径(可选)
                 image_placeholder: str = "<image>",      # 与 LLaMA-Factory 一致
                 ):

    def run(self,
            storage: DataFlowStorage,
            input_qa_item_key: Optional[str] = None,   # 含 question/answer/solution 的 dict 列名
            output_messages_key: str = "messages",
            output_images_key:   str = "images",
            ) -> List[str]:
```

**逻辑**（`vqa_formatter.py:185-257`）：从 QA dict 中提取 question/answer/solution，正则 `!\[.*?\]\((.*?)\)` 抽取图片路径，构建 ShareGPT 格式：
```python
messages = [
    {"role":"user","content": f"{'<image>'*len(imgs)}{question_clean}"},
    {"role":"assistant","content": f"{answer}\n\n{solution}"},
]
# images = [abs_path1, abs_path2, ...]
```
落盘为 `[{messages, images}, ...]`。

**输出 ShareGPT 示例**：
```json
[
  {
    "messages": [
      {"role":"user","content":"<image>求x使x²-1=0"},
      {"role":"assistant","content":"x=±1\n\n由x²=1得..."}
    ],
    "images": ["/abs/path/vqa_images/3.jpg"]
  }
]
```

---

## 4. core_vision 算子完整 API

源目录：`dataflow/operators/core_vision/generate/`（仅 1 个算子）。

### 4.1 PromptedVQAGenerator

源文件：`dataflow/operators/core_vision/generate/prompted_vqa_generator.py:8-67`

```python
@OPERATOR_REGISTRY.register()
class PromptedVQAGenerator(OperatorABC):
    def __init__(self,
                 llm_serving: LLMServingABC,                    # 任意 serving(含 VLM)
                 system_prompt: str = "You are a helpful assistant."
                 ):

    def run(self,
            storage: DataFlowStorage,
            input_key: str = "raw_content",       # 输入内容字段(可含图片占位/路径)
            output_key: str = "generated_content" # 输出字段
            ):
```

**逻辑**（`prompted_vqa_generator.py:48-66`）：把 `dataframe[input_key]` 收集为 list，一次性调 `llm_serving.generate_from_input(llm_inputs, self.system_prompt)`，结果写回 `dataframe[output_key]`。

**注意**：此算子本身不感知图片编码——图片处理在 serving 层。若用 `APIVLMServing_openai`，`input_key` 的值需是图片路径；若用 `APILLMServing_request`，则是纯文本。

---

## 5. VLM / LLM Serving 完整 API

源目录：`dataflow/serving/`。导出见 `dataflow/serving/__init__.py:1-29`。

### 5.1 APIVLMServing_openai（VLM，OpenAI 协议，★推荐用于 Kimi-K2.6）

源文件：`dataflow/serving/api_vlm_serving_openai.py:13-376`

```python
class APIVLMServing_openai(LLMServingABC):
    def __init__(
        self,
        api_url: str = "https://api.openai.com/v1",   # 兼容 OpenAI 协议的 base_url
        key_name_of_api_key: str = "DF_API_KEY",      # API key 的环境变量名
        model_name: str = "o4-mini",
        max_workers: int = 10,                        # 并发线程数
        timeout: int = 1800,
        temperature: float = 0.0,
    ):
        # 从 os.environ[key_name_of_api_key] 取 key
        # self.client = OpenAI(api_key=..., base_url=api_url)
```

**图片传入方式：本地文件路径 → base64**（`api_vlm_serving_openai.py:56-78`）：
```python
def _encode_image_to_base64(self, image_path: str) -> Tuple[str, str]:
    # 读文件 → base64; 仅支持 jpg/jpeg/png
    # 返回 (b64_str, fmt)  fmt∈{'jpeg','png'}
```

**单图对话**（`api_vlm_serving_openai.py:127-152`）：
```python
def chat_with_one_image(self,
                        image_path: str,          # 本地图片路径
                        text_prompt: str,
                        model: str = None,
                        timeout: int = 1800,
                        json_schema: dict = None  # 可选结构化输出
                        ) -> str:
    # 构造 content = [{"type":"text","text":...},
    #                 {"type":"image_url","image_url":{"url":f"data:image/{fmt};base64,{b64}"}}]
    # 返回 resp.choices[0].message.content
```

**批量单图并发**（`api_vlm_serving_openai.py:176-222`）：
```python
def generate_from_input_one_image(
    self,
    image_paths: List[str],        # 与 text_prompts 等长
    text_prompts: List[str],
    system_prompt: str = "",
    model: str = None,
    timeout: int = 1800,
    json_schema: dict = None
) -> List[str]:                    # 保持输入顺序
```

**多图分析**（`api_vlm_serving_openai.py:224-260`）：
```python
def analyze_images_with_gpt(self,
    image_paths: List[str],
    image_labels: List[str],       # 与 image_paths 等长
    system_prompt: str = "",
    ...
) -> str:                          # 单次返回综合分析
```

**批量多图并发**（`api_vlm_serving_openai.py:294-347`）：
```python
def generate_from_input_multi_images(
    self,
    list_of_image_paths: List[List[str]],       # 外层=批次,内层=单次请求多图
    list_of_image_labels: List[List[str]],
    system_prompt: str = "",
    user_prompts: List[str] = None,
    model: str = None,
    timeout: int = 1800,
    json_schema: dict = None
) -> List[str]:
```

**LLMServingABC 兼容方法**（`api_vlm_serving_openai.py:355-375`）：
```python
def generate_from_input(self,
    user_inputs: List[str],        # ★这里 user_inputs 是图片路径列表
    system_prompt: str = "Describe the image in detail.",
    json_schema: dict = None
) -> List[str]:
    # 并发调 chat_with_one_image_with_id(idx, user_input=图片路径, system_prompt, ...)
```

> ⚠️ 重要：`APIVLMServing_openai.generate_from_input` 把 `user_inputs` 当作**图片路径**处理，文本 prompt 用 `system_prompt` 传。这与纯文本 `APILLMServing_request` 语义不同。

#### 配置 Kimi-K2.6 多模态

Kimi-K2.6 兼容 OpenAI 协议，直接套用：
```python
import os
os.environ["DF_API_KEY"] = "<你的Kimi key>"
vlm = APIVLMServing_openai(
    api_url="https://api.moonshot.cn/v1",   # Kimi base_url
    key_name_of_api_key="DF_API_KEY",
    model_name="kimi-k2.6-vl",              # 实际模型名以文档为准
    max_workers=10,
    temperature=0.0,
)
desc = vlm.chat_with_one_image("/path/img.jpg", "用中文描述这张架构图的数据流方向")
```

### 5.2 APILLMServing_request（纯文本 LLM，OpenAI 协议）

源文件：`dataflow/serving/api_llm_serving_request.py:14-302`

```python
class APILLMServing_request(LLMServingABC):
    def __init__(self,
                 api_url: str = "https://api.openai.com/v1/chat/completions",  # 完整 endpoint
                 key_name_of_api_key: str = "DF_API_KEY",
                 model_name: str = "gpt-4o",
                 temperature: float = 0.0,
                 max_workers: int = 10,
                 max_retries: int = 5,
                 connect_timeout: float = 10.0,
                 read_timeout: float = 120.0,
                 **configs: dict,
                 ):
```

**核心方法**（`api_llm_serving_request.py:251-268`）：
```python
def generate_from_input(self,
    user_inputs: list[str],         # 纯文本 prompt 列表
    system_prompt: str = "You are a helpful assistant",
    json_schema: dict = None,       # 可选结构化输出
    ) -> list[str]:
    # 构造 [{"role":"system",...},{"role":"user","content":question}] 并发请求
```

**特性**：
- 线程池并发（`_run_threadpool`，`api_llm_serving_request.py:226-249`）
- 指数退避重试（`_api_chat_id_retry`，`api_llm_serving_request.py:218-224`）
- 区分 ConnectTimeout（抛 RuntimeError）/ ReadTimeout（warn + 返回 None）
- 支持 `reasoning_content`：若响应含推理内容，包装为 `<think>...</think>\n<answer>...</answer>`

### 5.3 LocalVLMServing_vllm（本地 VLM，vLLM 后端）

源文件：`dataflow/serving/local_model_vlm_serving.py:13-361`

```python
class LocalVLMServing_vllm(LLMServingABC):
    def __init__(self,
                 hf_model_name_or_path: str = None,        # HF 模型名/本地路径
                 hf_cache_dir: str = None,
                 hf_local_dir: str = None,
                 vllm_tensor_parallel_size: int = 1,
                 vllm_temperature: float = 0.2,
                 vllm_top_p: float = 0.9,
                 vllm_max_tokens: int = 1024,
                 vllm_max_model_len: int = None,
                 vllm_top_k: int = 40,
                 vllm_repetition_penalty: float = 1.0,
                 vllm_seed: int = None,
                 vllm_gpu_memory_utilization: float = 0.9,
                 vllm_limit_mm_per_prompt: int = 1,        # 单 prompt 最多图片数
                 trust_remote_code: bool = True,
                 enable_thinking: bool = True,
                 batch_size: int = 128,
                 ):
```

**懒加载**：`__init__` 只存参数，`backend_initialized=False`；首次推理时调 `start_serving()`（`local_model_vlm_serving.py:102-155`）下载模型、起 vLLM 引擎。

**单图批量**（`local_model_vlm_serving.py:177-235`）：
```python
def generate_from_input_one_image(self,
    image_paths: List[str],
    text_prompts: List[str],
    system_prompt: str = "Describe the image in detail.",
    model: str = None,
    timeout: int = 1800
) -> List[str]:
    # PIL.Image.open → messages=[{system},{user:[{image},{text}]}]
    # tokenizer.apply_chat_template → vllm.generate
```

**多图批量**（`local_model_vlm_serving.py:237-312`）：`generate_from_input_multi_images(list_of_image_paths, list_of_image_labels, user_prompts, system_prompt)`。

**兼容方法**（`local_model_vlm_serving.py:352-361`）：`generate_from_input(user_inputs=图片路径列表, system_prompt)` 转发到单图方法。

> ⚠️ 主要测试 Qwen-VL 系列（`local_model_vlm_serving.py:40-47` 有兼容性 Warning）。

---

## 6. KB Cleaning 算子完整 API

源目录：`dataflow/operators/knowledge_cleaning/generate/`。

### 6.1 FileOrURLToMarkdownConverterAPI（MinerU 官方 API）

源文件：`dataflow/operators/knowledge_cleaning/generate/mineru_operators.py:199-322`

```python
@OPERATOR_REGISTRY.register()
class FileOrURLToMarkdownConverterAPI(MinerUABC):
    def __init__(self,
                 intermediate_dir: str = "intermediate",
                 mineru_backend: str = "vlm",     # MinerU API model_version
                 api_key: str = None,             # None 则读 os.environ["MINERU_API_KEY"]
                 ):

    def run(self, storage: DataFlowStorage,
            input_key: str = "source",       # 值为本地路径或 URL
            output_key: str = "text_path"    # 写入解析后 .md 路径
            ):
```

**逻辑**：`MinerUABC.run`（`mineru_operators.py:171-196`）自动分类输入（PDF/图片/HTML/文本），PDF 走 `_batch_parse_pdf_with_mineru`，HTML 走 trafilatura。

### 6.2 FileOrURLToMarkdownConverterLocal（本地 MinerU CLI）

源文件：`mineru_operators.py:324-489`

```python
@OPERATOR_REGISTRY.register()
class FileOrURLToMarkdownConverterLocal(MinerUABC):
    def __init__(self,
                 intermediate_dir: str = "intermediate",
                 mineru_backend: str = "vlm-auto-engine",   # pipeline / vlm-sglang-engine / vlm-auto-engine
                 mineru_source: str = "local",
                 mineru_model_path: str = None,
                 mineru_download_model_type: str = "vlm",
                 ):
```

**内部用 subprocess 调 `mineru -p <pdf> -o <dir> -b <backend> --source local`**（`mineru_operators.py:462-468`），输出 `{intermediate_dir}/{pdf_name}/{backend}/{pdf_name}.md`。

> 与本项目的 `~/mineru-env/bin/python tools/srs_mineru_parse.py` 等价，可直接复用本地 MinerU 环境。

### 6.3 FileOrURLToMarkdownConverterFlash（Flash-MinerU GPU 加速）

源文件：`mineru_operators.py:492-626`

```python
@OPERATOR_REGISTRY.register()
class FileOrURLToMarkdownConverterFlash(MinerUABC):
    def __init__(self,
                 intermediate_dir: str = "intermediate",
                 mineru_model_path=None,        # 必填, 如 MinerU2.5-2509-1.2B
                 batch_size: int = 4,
                 replicas: int = 1,
                 num_gpus_per_replica: float = 1,
                 engine_gpu_util_rate_to_ray_cap: float = 0.9,
                 ):
```

### 6.4 KBCChunkGenerator（文本分块）

源文件：`dataflow/operators/knowledge_cleaning/generate/kbc_chunk_generator.py:18-155`

```python
@OPERATOR_REGISTRY.register()
class KBCChunkGenerator(OperatorABC):
    def __init__(self,
                 chunk_size: int = 512,
                 chunk_overlap: int = 50,
                 split_method: str = "token",          # token/sentence/semantic/recursive
                 min_tokens_per_chunk: int = 100,
                 tokenizer_name: str = "bert-base-uncased",
                 ):

    def run(self, storage: DataFlowStorage,
            input_key: str = 'text_path',     # .md 文件路径列名
            output_key: str = "raw_chunk"     # 分块文本列名
            ):
```

**逻辑**（`kbc_chunk_generator.py:107-154`）：用 `chonkie` 库（Token/Sentence/Semantic/Recursive Chunker）切分；超长文本先按词等分再 chunk；每 chunk 生成一行新记录。

### 6.5 KBCTextCleaner（知识清洗）

源文件：`dataflow/operators/knowledge_cleaning/generate/kbc_text_cleaner.py:88-208`

```python
@prompt_restrict(KnowledgeCleanerPrompt)
@OPERATOR_REGISTRY.register()
class KBCTextCleaner(OperatorABC):
    def __init__(self,
                 llm_serving: LLMServingABC,
                 lang: str = "en",                                    # en/zh
                 prompt_template: Union[KnowledgeCleanerPrompt, DIYPromptABC] = None,
                 ):

    def run(self, storage: DataFlowStorage,
            input_key: str = "raw_chunk",
            output_key: str = "cleaned_chunk"
            ):
```

**逻辑**（`kbc_text_cleaner.py:181-208`）：用 `prompt_template.build_prompt(raw_content)` 构造清洗 prompt，调 `llm_serving.generate_from_input(prompts, "")`，再用 `extract_cleaned_text` 抽取 `<cleaned_start>...<cleaned_end>` 之间的文本，剔除 prompt 泄漏。

### 6.6 QAExtractor（QA → Alpaca 格式）

源文件：`dataflow/operators/knowledge_cleaning/generate/qa_extract.py:13-241`

```python
@OPERATOR_REGISTRY.register()
class QAExtractor(OperatorABC):
    def __init__(self,
                 output_json_file: Optional[str] = None,
                 input_instruction: Optional[str] = "Please answer the following question based on the provided information."
                 ):

    def run(self, storage: DataFlowStorage,
            input_qa_key: str = "QA_pairs",
            output_instruction_key: Optional[str] = "instruction",
            output_question_key: Optional[str] = "input",
            output_answer_key: Optional[str] = "output"
            ) -> List[str]:
```

**输出 Alpaca 格式**（llamafactory 兼容）：
```json
{"instruction":"Please answer...","input":"问题文本","output":"答案文本"}
```

---

## 7. Prompt 模板

源目录：`dataflow/prompts/`。

### 7.1 QAExtractPrompt（pdf2vqa 用，让 LLM 输出 id 串）

源文件：`dataflow/prompts/pdf2vqa.py:90-161`

```python
@PROMPT_REGISTRY.register()
class QAExtractPrompt(PromptABC):
    def __init__(self): pass
    def build_prompt(self) -> str:   # 无参数, 作为 system_prompt
        ...
```

核心要求：LLM 读 converted.json，按 `<chapter>/<qa_pair>/<label>/<question>/<answer>/<solution>` 输出**id 串**（而非原文），由 `LLMOutputParser` 还原成文本+图片。

### 7.2 KnowledgeCleanerPrompt（KB 清洗用）

源文件：`dataflow/prompts/kbcleaning.py:4-201`

```python
@PROMPT_REGISTRY.register()
class KnowledgeCleanerPrompt(PromptABC):
    def __init__(self, lang: str = "en", strict_mode: bool = True):
    def build_prompt(self, raw_content: str) -> str:   # ★需要 raw_content 参数
        ...
    def _post_process(self, cleaned_text: str) -> str:
        ...
```

规则：移除冗余 HTML、规范化引号/破折号、PII 脱敏、`<img>` → `[Image: alt]`，输出包裹在 `<cleaned_start>...<cleaned_end>`。

---

## 8. Pipeline 组装完整代码

### 8.1 PDF VQA Extract Pipeline（官方完整实现）

源文件：`dataflow/statics/pipelines/api_pipelines/pdf_vqa_extract_pipeline.py:13-108`

```python
from dataflow.operators.knowledge_cleaning import FileOrURLToMarkdownConverterFlash
from dataflow.serving import APILLMServing_request
from dataflow.utils.storage import FileStorage
from dataflow.operators.pdf2vqa import MinerU2LLMInputOperator, LLMOutputParser, QA_Merger, PDF_Merger, VQAFormatter
from dataflow.operators.core_text import ChunkedPromptedGenerator
from dataflow.pipeline import PipelineABC
from dataflow.prompts.pdf2vqa import QAExtractPrompt

class PDF_VQA_extract_optimized_pipeline(PipelineABC):
    def __init__(self):
        super().__init__()
        self.storage = FileStorage(
            first_entry_file_name="./example_data/PDF2VQAPipeline/vqa_extract_test.jsonl",
            cache_path="./cache",
            file_name_prefix="vqa",
            cache_type="jsonl",
        )
        self.llm_serving = APILLMServing_request(
            api_url="http://123.129.219.111:3000/v1/chat/completions",
            key_name_of_api_key="DF_API_KEY",
            model_name="gemini-2.5-pro",
            max_workers=100,
        )
        self.vqa_extract_prompt = QAExtractPrompt()
        self.pdf_merger = PDF_Merger(output_dir="./cache")
        self.mineru_executor = FileOrURLToMarkdownConverterFlash(
            intermediate_dir="../example_data/PDF2VQAPipeline/flash/",
            mineru_model_path="<your Model Path>/MinerU2.5-2509-1.2B",
            batch_size=4, replicas=1, num_gpus_per_replica=0.5,
            engine_gpu_util_rate_to_ray_cap=0.9,
        )
        self.input_formatter = MinerU2LLMInputOperator()
        self.vqa_extractor = ChunkedPromptedGenerator(
            llm_serving=self.llm_serving,
            system_prompt=self.vqa_extract_prompt.build_prompt(),
            max_chunk_len=128000,
        )
        self.llm_output_parser = LLMOutputParser(output_dir="./cache", intermediate_dir="intermediate")
        self.qa_merger = QA_Merger(output_dir="./cache", strict_title_match=False)
        self.vqa_format_converter = VQAFormatter(output_json_file="./.cache/data/qa.json")

    def forward(self):
        self.pdf_merger.run(
            storage=self.storage.step(),
            input_pdf_list_key="input_pdf_paths", input_name_key="name",
            output_pdf_path_key="merged_pdf_path",
        )
        self.mineru_executor.run(
            storage=self.storage.step(),
            input_key="merged_pdf_path", output_key="vqa_markdown_path",
        )
        self.input_formatter.run(
            storage=self.storage.step(),
            input_markdown_path_key="vqa_markdown_path",
            output_converted_layout_key="converted_vqa_layout_path",
        )
        self.vqa_extractor.run(
            storage=self.storage.step(),
            input_path_key="converted_vqa_layout_path",
            output_path_key="extracted_llm_vqa_path",
        )
        self.llm_output_parser.run(
            storage=self.storage.step(),
            input_response_path_key="extracted_llm_vqa_path",
            input_converted_layout_path_key="converted_vqa_layout_path",
            input_name_key="name", output_qalist_path_key="extracted_vqa_path",
        )
        self.qa_merger.run(
            storage=self.storage.step(),
            input_qalist_path_key="extracted_vqa_path", input_name_key="name",
            output_merged_qalist_path_key="output_merged_vqalist_path",
            output_merged_md_path_key="output_merged_md_path",
            output_qa_item_key="vqa_pair",
        )
        self.vqa_format_converter.run(
            storage=self.storage.step(),
            input_qa_item_key="vqa_pair",
            output_messages_key="messages", output_images_key="images",
        )

if __name__ == "__main__":
    pipeline = PDF_VQA_extract_optimized_pipeline()
    pipeline.compile()
    pipeline.forward()
```

### 8.2 KB Cleaning Pipeline（官方完整实现）

源文件：`dataflow/statics/pipelines/api_pipelines/kbcleaning_pipeline.py:13-101`

```python
from dataflow.operators.knowledge_cleaning import (
    KBCChunkGenerator, FileOrURLToMarkdownConverterAPI,
    FileOrURLToMarkdownConverterFlash, FileOrURLToMarkdownConverterLocal,
    KBCTextCleaner,
)
from dataflow.operators.core_text import Text2MultiHopQAGenerator
from dataflow.utils.storage import FileStorage
from dataflow.serving import APILLMServing_request

class KBCleaningPDF_APIPipeline():
    def __init__(self):
        self.storage = FileStorage(
            first_entry_file_name="../example_data/KBCleaningPipeline/kbc_test_1.jsonl",
            cache_path="./.cache/api", file_name_prefix="knowledge_cleaning_step",
            cache_type="json",
        )
        self.llm_serving = APILLMServing_request(
            api_url="https://api.openai.com/v1/chat/completions",
            model_name="gpt-4o", max_workers=100,
        )
        self.knowledge_cleaning_step1 = FileOrURLToMarkdownConverterAPI(
            intermediate_dir="../example_data/KBCleaningPipeline/API/",
            mineru_backend="vlm", api_key=None,
        )
        self.knowledge_cleaning_step2 = KBCChunkGenerator(
            split_method="token", chunk_size=512,
            tokenizer_name="Qwen/Qwen2.5-7B-Instruct",
        )
        self.knowledge_cleaning_step3 = KBCTextCleaner(
            llm_serving=self.llm_serving, lang="en",
        )
        self.knowledge_cleaning_step4 = Text2MultiHopQAGenerator(
            llm_serving=self.llm_serving, lang="en", num_q=5,
        )

    def forward(self):
        self.knowledge_cleaning_step1.run(
            storage=self.storage.step(), input_key="source", output_key="text_path")
        self.knowledge_cleaning_step2.run(
            storage=self.storage.step(), input_key="text_path", output_key="raw_chunk")
        self.knowledge_cleaning_step3.run(
            storage=self.storage.step(), input_key="raw_chunk", output_key="cleaned_chunk")
        self.knowledge_cleaning_step4.run(
            storage=self.storage.step(), input_key="cleaned_chunk",
            output_key="QA_pairs", output_meta_key="QA_metadata")

if __name__ == "__main__":
    model = KBCleaningPDF_APIPipeline()
    model.forward()
```

---

## 9. 完整调用示例

以下为**不依赖 Pipeline 框架、直接组合算子与 serving** 的最小可运行示例（基于真实 API 签名）。

### 9.1 仅用 VLM 对 SRS 图片做描述（最简）

```python
import os
os.environ["DF_API_KEY"] = "<your-kimi-key>"

from dataflow.serving import APIVLMServing_openai

vlm = APIVLMServing_openai(
    api_url="https://api.moonshot.cn/v1",
    key_name_of_api_key="DF_API_KEY",
    model_name="kimi-k2.6-vl",   # 以实际模型名为准
    max_workers=8,
    temperature=0.0,
)

# 单图描述
desc = vlm.chat_with_one_image(
    image_path="/abs/path/srs_fig1.jpg",
    text_prompt="用中文详细描述这张架构图：包含哪些模块、数据流方向、接口名称。",
)
print(desc)

# 批量多图（每张图配一个 label 做对比）
results = vlm.generate_from_input_multi_images(
    list_of_image_paths=[["fig1.jpg","fig2.jpg"]],
    list_of_image_labels=[["图1 系统架构","图2 接口关系"]],
    system_prompt="对比这两张图，指出它们在接口ID上是否一致。",
    user_prompts=[""],
)
print(results[0])
```

### 9.2 用 pdf2vqa 全流程从 PDF 抽 VQA（复用本地 MinerU）

```python
import os
os.environ["DF_API_KEY"] = "<your-llm-key>"
os.environ["MINERU_MODEL_SOURCE"] = "huggingface"

from dataflow.utils.storage import FileStorage
from dataflow.operators.pdf2vqa import PDF_Merger, MinerU2LLMInputOperator, LLMOutputParser, QA_Merger, VQAFormatter
from dataflow.operators.knowledge_cleaning import FileOrURLToMarkdownConverterLocal
from dataflow.operators.core_text import ChunkedPromptedGenerator
from dataflow.serving import APILLMServing_request
from dataflow.prompts.pdf2vqa import QAExtractPrompt

# 1) Storage: 输入 jsonl 每行 {"input_pdf_paths":..., "name":...}
storage = FileStorage(
    first_entry_file_name="./srs_input.jsonl",
    cache_path="./cache", file_name_prefix="srs", cache_type="jsonl",
)

# 2) MinerU 本地解析(复用 ~/mineru-env)
mineru = FileOrURLToMarkdownConverterLocal(
    intermediate_dir="./intermediate",
    mineru_backend="vlm-auto-engine",
    mineru_source="huggingface",
)

# 3) LLM serving(纯文本, 用于 QAExtractPrompt)
llm = APILLMServing_request(
    api_url="https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions",
    key_name_of_api_key="DF_API_KEY",
    model_name="glm-5.2",
    max_workers=20,
)

# 4) 算子
pdf_merger = PDF_Merger(output_dir="./cache")
fmt = MinerU2LLMInputOperator()
prompt = QAExtractPrompt()
extractor = ChunkedPromptedGenerator(llm_serving=llm, system_prompt=prompt.build_prompt(), max_chunk_len=128000)
parser = LLMOutputParser(output_dir="./cache")
qa_merger = QA_Merger(output_dir="./cache", strict_title_match=False)
vqa_fmt = VQAFormatter(output_json_file="./cache/srs_vqa.json")

# 5) 运行(每步 storage.step())
pdf_merger.run(storage.step(), input_pdf_list_key="input_pdf_paths",
               input_name_key="name", output_pdf_path_key="merged_pdf_path")
mineru.run(storage.step(), input_key="merged_pdf_path", output_key="vqa_markdown_path")
fmt.run(storage.step(), input_markdown_path_key="vqa_markdown_path",
        output_converted_layout_key="converted_vqa_layout_path")
extractor.run(storage.step(), input_path_key="converted_vqa_layout_path",
              output_path_key="extracted_llm_vqa_path")
parser.run(storage.step(), input_response_path_key="extracted_llm_vqa_path",
           input_converted_layout_path_key="converted_vqa_layout_path",
           input_name_key="name", output_qalist_path_key="extracted_vqa_path")
qa_merger.run(storage.step(), input_qalist_path_key="extracted_vqa_path",
              input_name_key="name",
              output_merged_qalist_path_key="merged_vqalist_path",
              output_merged_md_path_key="merged_md_path",
              output_qa_item_key="vqa_pair")
vqa_fmt.run(storage.step(), input_qa_item_key="vqa_pair",
            output_messages_key="messages", output_images_key="images")

# 6) 读取最终 ShareGPT 输出
import json
with open("./cache/srs_vqa.json") as f:
    samples = json.load(f)
print(f"得到 {len(samples)} 条 VQA 样本")
```

---

## 10. SRS 图片-文本冲突检测方案

基于上述真实 API，给出完整的 SRS 图片-文本冲突检测代码。核心思路：从 MinerU 的 `content_list.json` 提取图片项 + 邻近文本约束，用 VLM 生成图片描述，再用 LLM 比对文本约束与图片描述是否冲突。

### 10.1 数据准备

MinerU 解析 SRS PDF 后得到 `*_content_list.json`，其中 `type=="image"` 的项含 `img_path` 与 `image_caption`。我们将每张图片与其前后文本块配对，形成 (图片, 文本约束) 对。

### 10.2 完整方案代码

```python
"""
SRS 图片-文本冲突检测
依赖: dataflow.serving.APIVLMServing_openai / APILLMServing_request
输入: MinerU 解析目录(含 *_content_list.json 与 images/)
输出: 冲突报告 JSON
"""
import os, json, base64, re
from pathlib import Path
from dataflow.serving import APIVLMServing_openai, APILLMServing_request

# ============ 配置 ============
os.environ["DF_API_KEY"] = "<your-key>"
CONTENT_LIST = "/path/to/srs_content_list.json"   # MinerU 输出
IMG_DIR      = Path(CONTENT_LIST).parent          # images/ 在同级
OUT_REPORT   = "./srs_image_conflict_report.json"

VLM = APIVLMServing_openai(
    api_url="https://api.moonshot.cn/v1",
    key_name_of_api_key="DF_API_KEY",
    model_name="kimi-k2.6-vl",     # 多模态
    max_workers=8, temperature=0.0,
)
LLM = APILLMServing_request(
    api_url="https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions",
    key_name_of_api_key="DF_API_KEY",
    model_name="glm-5.2",          # 纯文本比对
    max_workers=8, temperature=0.0,
)

# ============ 1. 从 content_list 构造 (图片, 邻近文本) 对 ============
def build_image_text_pairs(content_list_path: str) -> list[dict]:
    items = json.load(open(content_list_path, encoding="utf-8"))
    pairs = []
    for i, it in enumerate(items):
        if it.get("type") == "image":
            img_rel = it.get("img_path", "")
            img_abs = str(Path(content_list_path).parent / img_rel)
            caption = it.get("image_caption", "")
            # 取前 3 个非图片文本块作为上下文约束
            ctx = []
            for j in range(max(0, i-3), i):
                t = items[j].get("text") or items[j].get("table_body") or ""
                if t: ctx.append(t)
            ctx_text = "\n---\n".join(ctx)
            pairs.append({
                "image_path": img_abs,
                "caption": caption,
                "context_text": ctx_text,
            })
    return pairs

# ============ 2. VLM 生成图片结构化描述 ============
DESC_SCHEMA = {
    "type": "object",
    "properties": {
        "modules": {"type": "array", "items": {"type": "string"}},
        "data_flow_direction": {"type": "string"},
        "interface_ids": {"type": "array", "items": {"type": "string"}},
        "extra_notes": {"type": "string"}
    },
    "required": ["modules", "data_flow_direction", "interface_ids", "extra_notes"]
}

DESC_PROMPT = (
    "你是一名SRS文档图表分析专家。请分析给定图片(通常是系统架构图/接口关系图/状态图)，"
    "提取: 1) 图中出现的模块/节点名称列表; 2) 数据流方向描述; "
    "3) 图中标注的接口ID或信号ID列表; 4) 其他关键信息。"
    "严格按 JSON schema 输出。"
)

def describe_images(pairs: list[dict]) -> list[dict]:
    img_paths = [p["image_path"] for p in pairs]
    # generate_from_input_one_image 支持并发, 每张图配同一 DESC_PROMPT
    descs = VLM.generate_from_input_one_image(
        image_paths=img_paths,
        text_prompts=[DESC_PROMPT] * len(img_paths),
        system_prompt="你是严谨的工程文档分析助手。",
        json_schema=DESC_SCHEMA,
    )
    for p, d in zip(pairs, descs):
        p["image_desc"] = d
    return pairs

# ============ 3. LLM 比对: 文本约束 vs 图片描述 ============
COMPARE_PROMPT_SYS = (
    "你是SRS一致性检测器。给定一段文本约束和一张图的结构化描述，"
    "判断两者是否存在冲突。输出 JSON。"
)
COMPARE_SCHEMA = {
    "type": "object",
    "properties": {
        "conflict": {"type": "boolean"},
        "conflict_type": {"type": "string", "description": "interface_id_mismatch|flow_direction|module_missing|none"},
        "detail": {"type": "string"},
        "severity": {"type": "string", "enum": ["high","medium","low","none"]}
    },
    "required": ["conflict","conflict_type","detail","severity"]
}

def compare_pairs(pairs: list[dict]) -> list[dict]:
    user_inputs = []
    for p in pairs:
        user_inputs.append(
            f"【文本约束(图表前文)】\n{p['context_text']}\n\n"
            f"【图标题】{p['caption']}\n\n"
            f"【图片结构化描述(JSON)】\n{p['image_desc']}\n\n"
            f"请判断文本与图片是否冲突。"
        )
    results = LLM.generate_from_input(
        user_inputs, system_prompt=COMPARE_PROMPT_SYS, json_schema=COMPARE_SCHEMA,
    )
    for p, r in zip(pairs, results):
        p["conflict_result"] = r
    return pairs

# ============ 4. 主流程 ============
def main():
    pairs = build_image_text_pairs(CONTENT_LIST)
    print(f"提取到 {len(pairs)} 个 图片-文本 对")
    if not pairs:
        return
    pairs = describe_images(pairs)
    pairs = compare_pairs(pairs)

    # 汇总冲突
    conflicts = [p for p in pairs if _is_conflict(p["conflict_result"])]
    report = {
        "total_pairs": len(pairs),
        "conflict_count": len(conflicts),
        "conflicts": [{
            "image": p["image_path"], "caption": p["caption"],
            "result": p["conflict_result"],
        } for p in conflicts],
    }
    json.dump(report, open(OUT_REPORT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"报告写入 {OUT_REPORT}: {len(conflicts)} 处冲突")

def _is_conflict(result_str: str) -> bool:
    try:
        return json.loads(result_str).get("conflict", False)
    except Exception:
        return '"conflict": true' in result_str.lower()

if __name__ == "__main__":
    main()
```

### 10.3 输出报告示例

```json
{
  "total_pairs": 12,
  "conflict_count": 2,
  "conflicts": [
    {
      "image": "/path/images/arch.jpg",
      "caption": "图3-1 系统架构图",
      "result": "{\"conflict\":true,\"conflict_type\":\"flow_direction\",\"detail\":\"文本3.2节称数据从A流向B，但图中箭头由B指向A\",\"severity\":\"high\"}"
    },
    {
      "image": "/path/images/iface.jpg",
      "caption": "图4-2 接口关系图",
      "result": "{\"conflict\":true,\"conflict_type\":\"interface_id_mismatch\",\"detail\":\"文本表4-1列出接口IF-01~IF-08，图中仅出现IF-01~IF-06\",\"severity\":\"medium\"}"
    }
  ]
}
```

### 10.4 与本项目已有工具的衔接

| 环节 | 本项目现有工具 | DataFlow 替代/增强 |
|------|---------------|-------------------|
| PDF→Markdown/content_list | `tools/srs_mineru_parse.py`（本地 MinerU） | `FileOrURLToMarkdownConverterLocal`（封装同款 CLI） |
| 图片描述 | `tools/srs_image_text_matcher.py`（VLM 兜底） | `APIVLMServing_openai.chat_with_one_image`（更通用，支持 schema） |
| 图文比对 | 自写规则 + LLM | `APILLMServing_request.generate_from_input` + `json_schema` 结构化输出 |
| 文本约束提取 | `tools/srs_constraint_extract.py` | 可用 `KBCTextCleaner` + `KBCChunkGenerator` 预处理 |
| 端到端编排 | 手写脚本 | `PipelineABC`（`storage.step()` 自动步进、缓存） |

**推荐接入方式**：保留本项目 `srs_mineru_parse.py` 产出 `content_list.json`，之后用 §10.2 的冲突检测脚本（直接调 DataFlow serving），无需迁移到 Pipeline 框架即可获得 VLM 驱动的多模态冲突检测能力。

---

## 附：关键文件索引

| 类别 | 文件路径 | 关键类/函数 |
|------|---------|------------|
| Storage | `dataflow/utils/storage.py:444` | `FileStorage` |
| Storage | `dataflow/utils/storage.py:70` | `LazyFileStorage` |
| 基类 | `dataflow/core/llm_serving.py:5` | `LLMServingABC` |
| pdf2vqa | `dataflow/operators/pdf2vqa/generate/mineru_to_llm_input_operator.py:8` | `MinerU2LLMInputOperator` |
| pdf2vqa | `dataflow/operators/pdf2vqa/generate/pdf_merger.py:7` | `PDF_Merger` |
| pdf2vqa | `dataflow/operators/pdf2vqa/generate/llm_output_parser.py:12` | `LLMOutputParser` |
| pdf2vqa | `dataflow/operators/pdf2vqa/generate/qa_merger.py:10` | `QA_Merger` |
| pdf2vqa | `dataflow/operators/pdf2vqa/generate/vqa_formatter.py:16` | `VQAFormatter` |
| core_vision | `dataflow/operators/core_vision/generate/prompted_vqa_generator.py:8` | `PromptedVQAGenerator` |
| serving | `dataflow/serving/api_vlm_serving_openai.py:13` | `APIVLMServing_openai` |
| serving | `dataflow/serving/api_llm_serving_request.py:14` | `APILLMServing_request` |
| serving | `dataflow/serving/local_model_vlm_serving.py:13` | `LocalVLMServing_vllm` |
| KB清洗 | `dataflow/operators/knowledge_cleaning/generate/mineru_operators.py:199` | `FileOrURLToMarkdownConverterAPI/Local/Flash` |
| KB清洗 | `dataflow/operators/knowledge_cleaning/generate/kbc_chunk_generator.py:18` | `KBCChunkGenerator` |
| KB清洗 | `dataflow/operators/knowledge_cleaning/generate/kbc_text_cleaner.py:88` | `KBCTextCleaner` |
| KB清洗 | `dataflow/operators/knowledge_cleaning/generate/qa_extract.py:13` | `QAExtractor` |
| Prompt | `dataflow/prompts/pdf2vqa.py:90` | `QAExtractPrompt` |
| Prompt | `dataflow/prompts/kbcleaning.py:4` | `KnowledgeCleanerPrompt` |
| Pipeline | `dataflow/statics/pipelines/api_pipelines/pdf_vqa_extract_pipeline.py:13` | `PDF_VQA_extract_optimized_pipeline` |
| Pipeline | `dataflow/statics/pipelines/api_pipelines/kbcleaning_pipeline.py:13` | `KBCleaningPDF_APIPipeline` |
| 工具 | `dataflow/utils/pdf2vqa/format_utils.py:21` | `merge_qa_pair`, `jsonl_to_md` |
