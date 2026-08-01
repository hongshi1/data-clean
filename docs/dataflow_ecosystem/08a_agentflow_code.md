# AgentFlow DocDancer 代码精读：多模态文档跨模态推理的实战复现

> 源码位置：`/Users/gexuancheng/Desktop/research2/data_clean/dataflow_repos/AgentFlow/`
>
> 本文从 AgentFlow 源码中逐文件提取**真实可复现的代码**，目标是让读者能直接把 SRS 文档喂进 DocDancer/MM-Doc 沙箱，做文本↔表格↔图片的跨模态冲突检测。所有代码块均标注文件路径与行号，不接受"可以参考"这种描述。

---

## 目录

1. [整体架构与数据流](#1-整体架构与数据流)
2. [安装步骤（从 install.sh 提取）](#2-安装步骤从-installsh-提取)
3. [Sandbox Doc 后端实现](#3-sandbox-doc-后端实现)
4. [三阶段合成的完整 API](#4-三阶段合成的完整-api)
5. [Rollout 轨迹执行](#5-rollout-轨迹执行)
6. [配置文件完整结构](#6-配置文件完整结构)
7. [PDF 预处理（DocDancer）](#7-pdf-预处理docdancer)
8. [SRS 跨模态冲突检测完整方案](#8-srs-跨模态冲突检测完整方案)

---

## 1. 整体架构与数据流

AgentFlow 的 Doc 流程分五个阶段（见 `examples/DocAgent.md:24-26`）：

```
Sandbox Setup → QA Synthesis → Trajectory Synthesis → Model Training → Inference & Evaluation
```

两个核心工具（见 `examples/DocAgent.md:29-33`）：

| 工具 | 作用 | 关键参数 |
|------|------|----------|
| `doc_search`（注册名 `doc:search`） | 在文档标题/段落/表格/图片 caption 中搜索关键词 | `key_words: array`, `max_search_results: int` |
| `doc_read`（注册名 `doc:read`） | 读取指定 section，把**页面图+图片+表格图**连同文本一起喂给 VLM，返回证据+摘要 | `section_ids: array`, `goal: string`, `max_image_num: int`, `max_text_token: int` |

数据流关键点（读源码后总结）：

- **Seed 不是原始 PDF**，而是预处理后的结构化目录，含 `outline.xml`、`all_content.xml`、`figures/`、`tables/`、`page_images/`、`data.pkl`（见 `seeds/doc/seed/2210.02442v1/`）。
- `outline.xml` 是喂给 Agent 的起点（作为 seed 的 `content` 字段），`all_content.xml` 才是 `doc:read` 真正读取的全量内容。
- `seed_path`（预处理目录的绝对路径）通过 seed.jsonl 的 `kwargs` 传到 sandbox 工具，**Agent 自己不用写 seed_path**（见 `doc_tool.py:525-528`）。
- VLM（视觉语言模型）在 `doc:read` 内部被调用，用于跨模态信息抽取——这是跨模态推理的真正发生地。

---

## 2. 安装步骤（从 install.sh 提取）

源码：`install.sh`，核心依赖见 `requirements.txt`。

### 2.1 一键安装

```bash
# install.sh:73-74 核心依赖
pip install -r requirements.txt

# install.sh:100-101 Playwright 浏览器（Doc 流程不强制需要，但 web agent 需要）
python -m playwright install chromium
```

`requirements.txt` 中与 Doc 流程强相关的依赖（第 35-49 行）：

```
# 文档与文件处理
openpyxl
python-docx
python-pptx
pypdf
PyPDF2
pdf2image
pdfplumber
PyMuPDF
beautifulsoup4
easyocr
xmltodict
lxml
Pillow==10.1.0
```

以及核心通信依赖（第 6-18 行）：

```
requests
fastapi
pydantic
openai>=1.0.0
httpx
httpx-retries
pyyaml
```

### 2.2 PDF 预处理需要额外安装（用于把 SRS PDF 转成 seed）

预处理用 MinerU VLM 模型（见 `projects/DocDancer/PDF_preprocess/1_run_pdf_extract.py:8-17`）：

```bash
# 需要 GPU + vLLM
pip install 'mineru-vl-utils[vllm]' pdf2image Pillow
# vllm 需要 torch>=2.6.0（install.sh:80，需 --ml 或 --all）
pip install "torch>=2.6.0" "transformers>=4.51.1" "accelerate>=1.5.1" vllm>=0.10.0
```

### 2.3 环境变量（必须设置）

从配置文件 `configs/sandbox-server/doc_config.json:15-17` 可见，VLM 凭据用 `${VAR}` 占位，由 `sandbox/server/config_loader.py` 的 `expand_env_vars` 展开：

```bash
export VLM_API_KEY="你的OpenAI兼容API key"     # doc:read 的 VLM 调用用
export OPENROUTER_API_KEY="你的OpenRouter key"  # synthesis 主 LLM 用（见 doc_config.json:3）
```

> 注：项目本身没有 `pip install -e .` 的 setup.py，示例文档里写的 `pip install -e .` 实际靠把项目根目录加到 `PYTHONPATH`（见 `sandbox/cli/sandbox-server.py:17-20` 和 `synthesis/pipeline.py:21-22`）。运行时确保 `cwd=AgentFlow/` 即可。

---

## 3. Sandbox Doc 后端实现

这是跨模态推理的核心。文件：`sandbox/server/backends/tools/doc_tool.py`（829 行）。

### 3.1 工具注册机制

Doc 工具是**无状态 API 工具**（Stateless API Tool），通过 `@register_api_tool` 装饰器注册（见 `sandbox/server/backends/tools/__init__.py:59-119`）。注册发生在模块导入时（`__init__.py:224` 的 `from . import doc_tool`）。

注册代码在 `doc_tool.py:818-829`：

```python
# doc_tool.py:818-829
# Register tools
search = register_api_tool(
    name="doc:search",
    config_key="doc",
    description="Search for keywords in document"
)(SearchTool())

read = register_api_tool(
    name="doc:read",
    config_key="doc",
    description="Read content of specified section in document, call VLM to get useful information and return to agent"
)(ReadTool())
```

`config_key="doc"` 表示从 sandbox 配置文件的 `apis.doc` 节读取配置（见第 6 节配置文件）。配置通过 `BaseApiTool.set_config()` 注入到实例（见 `__init__.py:193-195`）。

### 3.2 DocTool：文档加载与索引

`DocTool` 类（`doc_tool.py:338-501`）负责加载预处理产物并构建索引。

**初始化加载**（`doc_tool.py:351-376`）：

```python
# doc_tool.py:351-376
def _load_documents(self):
    """Load outline.xml and all_content.xml"""
    outline_path = os.path.join(self.seed_path, "outline.xml")
    content_path = os.path.join(self.seed_path, "all_content.xml")
    
    if not os.path.exists(outline_path):
        raise ToolBusinessError(f"outline.xml not found at {outline_path}", ErrorCode.EXECUTION_ERROR)
    if not os.path.exists(content_path):
        raise ToolBusinessError(f"all_content.xml not found at {content_path}", ErrorCode.EXECUTION_ERROR)
    
    try:
        self.outline_root = ET.parse(outline_path).getroot()
        self.content_root = ET.parse(content_path).getroot()
        
        # Build section_dict
        for section in self.content_root.iter("Section"):
            section_id = section.get("section_id")
            if section_id:
                self.section_dict[section_id] = section
    except Exception as e:
        raise ToolBusinessError(f"Failed to load documents: {str(e)}", ErrorCode.EXECUTION_ERROR)
```

关键：`section_dict` 把 `section_id`（如 `"3.1.2"`）映射到 XML 节点。这是 `doc:read` 按 ID 精确定位章节的基础。

**图片/表格/页面图的获取**（`doc_tool.py:382-434`）：

```python
# doc_tool.py:382-399  获取图片（figures/ 目录）
def get_image(self, image_id: str) -> Tuple[str, str, Optional[str]]:
    figures_dir = os.path.join(self.seed_path, "figures")
    if os.path.exists(figures_dir):
        possible_names = [
            f"image_{image_id}_compressed.jpg",
            f"image_{image_id}.jpg",
            f"image_{image_id}.png",
        ]
        for name in possible_names:
            image_path = os.path.join(figures_dir, name)
            if os.path.exists(image_path):
                return process_image(image_path)
    return "", "", f"Image {image_id} not found"

# doc_tool.py:401-420  获取整页图（page_images/ 目录）
def get_page_image(self, page_num: int) -> Tuple[str, str, Optional[str]]:
    page_images_dir = os.path.join(self.seed_path, "page_images")
    index_string = "%04d" % (int(page_num) - 1)   # 0-indexed 四位补零
    possible_names = [
        f"page_{index_string}_compressed.jpg",
        f"page_{index_string}.jpg",
        f"page_{index_string}.png",
    ]
    for name in possible_names:
        image_path = os.path.join(page_images_dir, name)
        if os.path.exists(image_path):
            return process_image(image_path)
    return "", "", f"Page {page_num} image not found"

# doc_tool.py:422-434  获取表格图（tables/ 目录）
def get_table_image(self, table_id: str) -> Tuple[str, str, Optional[str]]:
    tables_dir = os.path.join(self.seed_path, "tables")
    for ext in [".png", ".jpg"]:
        table_path = os.path.join(tables_dir, f"table_{table_id}{ext}")
        if os.path.exists(table_path):
            return process_image(table_path)
    return "", "", f"Table {table_id} image not found"
```

**搜索引擎**（`doc_tool.py:436-501`）：`single_search` 遍历 `all_content.xml`，在 Section 标题、Paragraph 文本、HTML_Table 文本、Image 的子节点文本中做关键词匹配，返回 XML 格式的搜索结果，并用 `make_snippet`（`doc_tool.py:81-136`）生成上下文片段。

### 3.3 doc:search 工具实现

`SearchTool.execute`（`doc_tool.py:504-566`）：

```python
# doc_tool.py:510-566
class SearchTool(BaseApiTool):
    def __init__(self):
        super().__init__(tool_name="doc:search", resource_type="doc")
    
    async def execute(
        self,
        key_words: Union[str, List[str]],
        max_search_results: Optional[int] = None,
        **kwargs
    ) -> Any:
        # seed_path 优先来自 kwargs（seed.jsonl 传入），其次来自配置
        seed_path = kwargs.get("seed_path") or self.get_config("seed_path")
        if not seed_path:
            raise ToolBusinessError("seed_path must be provided in kwargs (from seed.jsonl)", ErrorCode.EXECUTION_ERROR)
        
        if max_search_results is None:
            max_search_results = self.get_config('max_search_results')
        if max_search_results is None:
            max_search_results = 10
        
        if isinstance(key_words, str):
            key_words = [key_words]
        
        doc_tool = DocTool(seed_path)
        search_result = ""
        for key_word in key_words:
            single_search_result = doc_tool.single_search(key_word)
            result_num = len(single_search_result)
            if result_num == 0:
                single_search_result = f"We didn't find any section or paragraph that contains the keyword `{key_word}`"
            else:
                if result_num > max_search_results:
                    for subelement in single_search_result[max_search_results:]:
                        single_search_result.remove(subelement)
                single_search_result = ET.tostring(single_search_result, encoding="unicode")
                single_search_result = minidom.parseString(single_search_result).toprettyxml(indent="  ").replace('<?xml version="1.0" ?>\n', '').strip()
            search_result += f"A Document search for `{key_word}` found {result_num} results:\n\n{single_search_result}"
            search_result += "\n\n=============================\n\n"
        return {"result": search_result}
```

注意 `kwargs.get("seed_path")`（第 525 行）——这是 seed.jsonl 的 `kwargs.seed_path` 注入点。合成时 `TrajectorySampler._execute_action` 把 `self.seed_kwargs` 作为 `**kwargs` 传给 worker（见 `sampler.py:213`）。

### 3.4 doc:read 工具实现（跨模态推理核心）

`ReadTool`（`doc_tool.py:569-815`）是跨模态推理的真正发生地。它做三件事：

1. 取出 section 的 XML 文本 + 内嵌的 Image/HTML_Table 项
2. 把页面图、图片图、表格图转 base64，组装成多模态 messages
3. 调 VLM 抽取"与 goal 相关的证据 + 摘要"

**VLM 调用 prompt**（`doc_tool.py:176-214`）——这是跨模态推理的指令：

```python
# doc_tool.py:176-214
GET_USEFUL_INFO_PROMPT = """Now you need to process the following document content (text) together with all previously provided visual inputs, including images, tables and pages, and extract relevant information based on the user goal.

## Document Content
{document_content}

## User Goal
{goal}

Before producing the final output, you must perform a careful and thorough analysis to complete the following tasks:

## Task Guidelines

1. Content Scanning for Rationale  
   Locate the specific text snippets and/or visual data (from images and tables) that are directly related to the user's goal within the document content and the previously provided visual inputs.

2. Key Extraction for Evidence  
   Identify and extract the most relevant information from both the textual content and the visual content.  
   You must not miss any important information.  
   Output the full original context of the evidence as completely as possible.  
   The evidence may contain more than three fragments.

3. Summary Output  
   Organize the extracted information into a concise, logically structured summary.  
   Prioritize clarity and explicitly judge how each piece of information contributes to achieving the user's goal.

## Final Output Format

You must return the result in JSON format with the following fields:
- "rational"
- "evidence"
- "summary"
In the final JSON output, the values should not use any special formatting structure. Simply concatenate the content in plain Markdown format.

The final JSON must be wrapped inside the following tags:

<json>
[YOUR_JSON_OUTPUT]
</json>
""".strip()
```

**多模态 message 组装**（`doc_tool.py:575-728`）——这是文本+图片+表格如何喂给 VLM 的真实代码：

```python
# doc_tool.py:575-728  _single_read 核心片段
def _single_read(self, doc_tool, section_id, goal, vlm_client, max_image_num=10, max_text_token=20000):
    if section_id not in doc_tool.section_dict:
        return f"The section_id {section_id} is not presented in the document, here is the full list of available section_id: {list(doc_tool.section_dict.keys())}."
    
    messages = [
        {'role': 'system', 'content': [{"type": "text", "text": "You are a helpful assistant."}]},
    ]
    
    xml_section_obj = doc_tool.get_section_content(section_id)
    visual_items = extract_image_and_table_items(xml_section_obj)   # 提取该 section 内的 Image/HTML_Table
    section_text = ET.tostring(xml_section_obj, encoding="unicode")
    section_text = minidom.parseString(section_text).toprettyxml(indent="  ").replace('<?xml version="1.0" ?>\n', '').strip()
    
    if len(section_text) > max_text_token:
        section_text = section_text[:max_text_token] + "\n\n... [truncated] ..."
    
    page_numbers = get_page_numbers_from_section(xml_section_obj)    # 该 section 涉及哪些页
    
    visual_object_infos = []
    # 1) 加页面图（全局视觉上下文）
    for page_num in page_numbers:
        media_type, base64_image, error_msg = doc_tool.get_page_image(page_num)
        if not error_msg:
            visual_object_infos.append({"type": "Page", "page_num": page_num,
                "media_type": media_type, "base64_image": base64_image})
    
    # 2) 加图片 + 表格图（局部视觉元素）
    for visual_item in visual_items:
        if visual_item['type'] == 'Image':
            media_type, base64_image, error_msg = doc_tool.get_image(visual_item['image_id'])
            if not error_msg:
                visual_item.update({"media_type": media_type, "base64_image": base64_image})
                visual_object_infos.append(visual_item)
        elif visual_item['type'] == 'HTML_Table':
            media_type, base64_image, error_msg = doc_tool.get_table_image(visual_item['table_id'])
            if not error_msg:
                visual_item.update({"media_type": media_type, "base64_image": base64_image})
                visual_object_infos.append(visual_item)
    
    # 3) 限制图片数量：优先丢弃 Page，再丢弃 HTML_Table，最后截断
    if len(visual_object_infos) > max_image_num:
        visual_object_infos = [item for item in visual_object_infos if item['type'] != 'Page']
        if len(visual_object_infos) > max_image_num:
            visual_object_infos = [item for item in visual_object_infos if item['type'] != 'HTML_Table']
            if len(visual_object_infos) > max_image_num:
                visual_object_infos = visual_object_infos[:max_image_num]
    
    # 4) 组装 messages：先视觉，后文本指令
    for visual_object_info in visual_object_infos:
        if visual_object_info['type'] == 'Page':
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"I have uploaded the full page images for the selected section, corresponding to the following page numbers: {visual_object_info['page_num']}."},
                {"type": "image_url", "min_pixels": 4*32*32, "max_pixels": 2048*32*32,
                 "image_url": {"url": f"data:{visual_object_info['media_type']};base64,{visual_object_info['base64_image']}"}}
            ]})
        elif visual_object_info['type'] == 'Image':
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"I have uploaded the image with image ID {visual_object_info['image_id']} from the selected section."},
                {"type": "image_url", "min_pixels": 4*32*32, "max_pixels": 2048*32*32,
                 "image_url": {"url": f"data:{visual_object_info['media_type']};base64,{visual_object_info['base64_image']}"}}
            ]})
        elif visual_object_info['type'] == 'HTML_Table':
            messages.append({"role": "user", "content": [
                {"type": "text", "text": f"I have uploaded the table with table ID {visual_object_info['table_id']} from the selected section."},
                {"type": "image_url", "image_url": {"url": f"data:{visual_object_info['media_type']};base64,{visual_object_info['base64_image']}"}}
            ]})
    
    # 5) 最终 prompt
    messages.append({'role': 'user', 'content': [
        {"type": "text", "text": GET_USEFUL_INFO_PROMPT.format(document_content=section_text, goal=goal)}
    ]})
    
    # 6) 调 VLM
    useful_info = vlm_client.get_useful_info(section_id, goal, messages)
    return useful_info
```

**VLM 客户端**（`doc_tool.py:217-335`）：`VLMClient.call_llm` 用 OpenAI SDK 调用，最多重试 10 次；`get_useful_info` 解析 `<json>...</json>` 标签，返回 `Evidence` + `Summary`。

### 3.5 HTTP API 端点

Sandbox 服务器是 FastAPI 应用（见 `sandbox/server/routes.py`）。关键端点（定义在 `sandbox/protocol.py:193-225`）：

| 端点 | 方法 | 作用 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/execute` | POST | 执行工具（核心） |
| `/api/v1/tools` | GET | 列出所有工具 |
| `/api/v1/session/create` | POST | 创建会话 |
| `/api/v1/warmup` | POST | 预热后端 |

**直接用 HTTP 调 doc:search**（绕过 SDK）：

```bash
curl -X POST http://127.0.0.1:18890/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "action": "doc:search",
    "params": {"key_words": ["温度", "工作范围"], "seed_path": "/abs/path/to/srs_seed"},
    "worker_id": "manual_test"
  }'
```

`action` 字段就是工具注册名（`doc:search` / `doc:read`），`params` 是工具参数。`seed_path` 必须放在 params 里（routes.py:62-79 把 `request.params` 透传给 `server.execute`）。

---

## 4. 三阶段合成的完整 API

入口：`synthesis/__init__.py:20` 导出 `synthesize`。实现在 `synthesis/api.py:62-84`。

### 4.1 synthesize() 入口函数

```python
# synthesis/api.py:62-84
def synthesize(
    *,
    config_path: str,
    seeds: Optional[Union[str, List[str], List[Dict[str, Any]]]] = None,
) -> None:
    """One-call wrapper to run synthesis."""
    config = load_config(config_path)
    seeds_path = config.seeds_file or os.environ.get("SEEDS_FILE")
    if seeds is None and not seeds_path:
        raise ValueError("Missing seeds: provide seeds or set seeds_file in config")
    if seeds is None:
        seeds = seeds_path
    output_dir = config.output_dir or os.environ.get("OUTPUT_DIR") or "synthesis_results"
    pipeline = SynthesisPipeline(config=config, output_dir=output_dir)
    pipeline.run(load_seeds(seeds))
```

调用方式（见 `examples/DocAgent.md:213-216`）：

```python
from synthesis import synthesize
synthesize(config_path="configs/synthesis/doc_config.json")
```

### 4.2 Seed 数据结构

`load_seeds`（`synthesis/api.py:25-59`）解析 JSONL，每行一个 dict，必须有 `content` 和 `kwargs`：

```jsonl
{"content": "<?xml version='1.0' encoding='utf-8'?>\n<Outline>...</Outline>", "kwargs": {"seed_path": "/abs/path/to/seed_dir"}}
```

- `content`：`outline.xml` 的完整内容（作为 Agent 探索起点）
- `kwargs.seed_path`：预处理目录的**绝对路径**（含 `all_content.xml`、`figures/`、`tables/`、`page_images/`）

真实示例见 `seeds/doc/seeds.jsonl`（单行，2210.02442v1 论文）。

### 4.3 三阶段流程（SynthesisPipeline）

`synthesis/pipeline.py:66-203` 的 `run_async` 是主循环。对每个 seed：

**阶段 1：轨迹树采样**（`pipeline.py:147`）

```python
# synthesis/pipeline.py:145-148
print("📊 Step 1: Sampling trajectory tree...")
trajectory_tree = await sampler.sample_trajectory_tree(seed_content, seed_kwargs)
```

**阶段 2：轨迹选择**（`pipeline.py:154-161`）

```python
# synthesis/pipeline.py:153-161
print("\n📊 Step 2: Selecting trajectories...")
selected_trajectories = selector.select_trajectories(
    nodes=trajectory_tree,
    root_id=sampler.root_id,
    seed_data=seed_content,
    source_id=source_id,
    max_selected_traj=self.config.max_selected_traj
)
```

**阶段 3：QA 合成**（`pipeline.py:167-176`）

```python
# synthesis/pipeline.py:167-176
print("\n📊 Step 3: Synthesizing QA pairs...")
qa_pairs = []
for qa_idx, trajectory in enumerate(selected_trajectories):
    try:
        qa = synthesizer.synthesize_qa(trajectory, qa_idx)
        if qa:
            qa_pairs.append(qa.to_dict())
    except Exception as e:
        print(f"  ⚠️ QA synthesis failed for trajectory {qa_idx}: {e}")
```

### 4.4 TrajectorySampler.sample_trajectory_tree()

`synthesis/core/sampler.py:45-94`：

```python
# synthesis/core/sampler.py:45-94
async def sample_trajectory_tree(
    self,
    seed_data: str,
    seed_kwargs: Optional[Dict[str, Any]] = None
) -> Dict[str, TrajectoryNode]:
    """Sample a trajectory tree starting from seed data (async)"""
    if seed_kwargs is None:
        seed_kwargs = {}
    # Reset tree
    self.nodes = {}
    self.root_id = None
    self._seed_used_action_signatures.clear()
    self._seed_used_action_signatures_ordered.clear()
    self.seed_kwargs = seed_kwargs
    
    # Load tool schemas from local tools module
    self.available_tools = get_tool_schemas(
        self.config.available_tools if self.config.available_tools else None
    )
    
    # Create root node
    root_id = self._generate_node_id()
    root_node = TrajectoryNode(
        node_id=root_id,
        observation=f"Starting point: {seed_data}",
        intent="Initialize exploration",
        action=None, parent_id=None, children_ids=[], depth=0
    )
    self.nodes[root_id] = root_node
    self.root_id = root_id
    
    # Explore tree asynchronously (BFS)
    await self._explore_node(root_node, seed_data)
    return self.nodes
```

**树形探索**（`sampler.py:96-163`）：`_explore_node` 按 `branching_factor` 创建子节点，用 `asyncio.gather` 并发；`_create_and_explore_child` 生成动作→执行→建子节点→递归。

**动作生成**（`sampler.py:165-204`）：`_generate_next_action` 用 LLM 生成 XML 格式的 `<intent>/<tool_name>/<parameters>`，由 `parse_action_xml`（`utils.py:61-97`）解析。关键的去重逻辑（`sampler.py:188-196`）用 `_action_signature` 哈希避免重复调用同一工具+参数。

**探索 prompt**（`sampler.py:247-314`）：把工具描述、历史轨迹、`sampling_tips` 拼成 prompt，要求 LLM 返回：

```
<intent>...</intent>
<tool_name>doc:search</tool_name>
<parameters>{"key_words": ["..."]}</parameters>
```

**动作执行**（`sampler.py:206-221`）——这是 Agent 与 Sandbox 的交互点：

```python
# synthesis/core/sampler.py:206-221
async def _execute_action(self, action: Dict[str, Any]) -> str:
    """Execute an action via worker (async)"""
    tool_name = action.get("tool_name", "")
    parameters = action.get("parameters", {})
    try:
        # seed_kwargs（含 seed_path）作为 **kwargs 传入
        result = await self.worker.execute_tool(tool_name, parameters, **self.seed_kwargs)
        formatted_result = format_tool_result(result, verbose=False)
        return formatted_result
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"
```

`worker.execute_tool`（`synthesis/core/worker.py:101-110`）调用 `self.sandbox.execute(tool_name, parameters, **kwargs)`，最终发 HTTP 请求到 sandbox 服务器。

### 4.5 TrajectoryNode 数据结构

`synthesis/core/models.py:9-23`：

```python
# synthesis/core/models.py:9-23
@dataclass
class TrajectoryNode:
    """Single node in a trajectory tree"""
    node_id: str
    observation: str          # 工具返回结果
    intent: str               # LLM 生成的意图说明
    action: Optional[Dict[str, Any]] = None   # {"tool_name":..., "parameters":...}
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    depth: int = 0
```

### 4.6 TrajectorySelector 选择策略

`synthesis/core/selector.py:25-65`：

1. 找所有叶子节点（`selector.py:40`）
2. 过滤深度 < `min_depth` 的（`selector.py:44`）
3. 构建从叶子到根的路径（`selector.py:67-82`）
4. 打分 + 去重（`selector.py:84-146`）

**打分函数**（`selector.py:148-171`）：

```python
# synthesis/core/selector.py:148-171
def _score_path(self, path, avg_obs_length=None, min_length=0, length_range=1):
    # Depth score（深度越深分越高，封顶 40）
    depth_score = min(len(path) / 5.0, 1.0) * 40
    # Information score（观测长度归一化，最高 30）
    normalized_length = (avg_obs_length - min_length) / length_range if length_range > 0 else 0
    info_score = normalized_length * 30
    # Diversity score（用到的不同工具数，最高 30）
    tool_names = set()
    for node in path:
        if node.action:
            tool_names.add(node.action.get("tool_name", ""))
    total_tools = len(self.config.available_tools) if self.config.available_tools else self.available_tool_total
    diversity_score = len(tool_names) / max(total_tools, 1) * 30
    total_score = depth_score + info_score + diversity_score
    return total_score
```

**去重**（`selector.py:113-132`）：用 Jaccard 相似度（节点 ID 集合的交并比）超过 `path_similarity_threshold`（默认 0.7）就跳过。

### 4.7 QASynthesizer.synthesize_qa()

`synthesis/core/synthesizer.py:27-63`：

```python
# synthesis/core/synthesizer.py:27-63
def synthesize_qa(self, trajectory: Trajectory, qa_index: int = 0) -> Optional[SynthesizedQA]:
    traj_description = self._format_trajectory(trajectory)
    max_attempts = 3
    last_failure_reason = ""
    for attempt in range(1, max_attempts + 1):
        prompt = self._build_prompt(trajectory, traj_description, last_failure_reason)
        try:
            response = chat_completion(
                self.client, model=self.config.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7 + 0.1 * (attempt - 1),
                response_format={"type": "json_object"}
            )
            result = json.loads(extract_json_object(response.choices[0].message.content))
        except Exception as e:
            last_failure_reason = f"Synthesis exception: {str(e)}"
            continue
        qa_obj, failure_reason = self._build_qa_from_result(result, trajectory, qa_index, attempt)
        if failure_reason or qa_obj is None:
            last_failure_reason = failure_reason or "Unknown validation failure."
            continue
        return qa_obj
    return None
```

**QA 生成 prompt**（`synthesizer.py:131-198`）要求返回 JSON：

```json
{
  "question": "question text",
  "answer": "short phrase or single sentence",
  "reasoning_steps": [
    {"hop": 1, "fact": "...", "evidence": "...", "output": "..."},
    {"hop": n, "fact": "...", "evidence": "...", "output": "answer"}
  ]
}
```

**质量检查**（`synthesizer.py:65-107`）：
- 问题/答案非空
- 答案不能泄漏到问题里（`_answer_leaks_into_question`，第 115-121 行）
- 问题不能太长（`_question_too_verbose`，第 123-129 行，>85 词或 >500 字符）
- `reasoning_steps` 至少 3 步

`synthesis_tips`（来自配置）会被注入 prompt，强制要求多跳、多页、视觉落地。

### 4.8 SynthesizedQA 输出结构

`synthesis/core/models.py:45-58`：

```python
# synthesis/core/models.py:45-58
@dataclass
class SynthesizedQA:
    question: str
    answer: str
    trajectory_id: str
    reasoning_steps: List[Dict[str, str]]
    source_id: str = ""
    qa_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
```

输出到 `results/synthesized_qa.jsonl` 和 `results/trajectories.jsonl`（`pipeline.py:209-219`）。

---

## 5. Rollout 轨迹执行

Rollout 用于在 benchmark 上跑 Agent 生成轨迹/推理。入口：`rollout/api.py:54-110`。

### 5.1 pipeline() 入口

```python
# rollout/api.py:54-110
def rollout(*, config_path, data_path=None, output_dir=None, model_name=None,
            max_tasks=None, task_ids=None, evaluate=True, metric=None):
    config = load_config(config_path)
    if data_path: config.data_path = data_path
    if model_name: config.model_name = model_name
    if max_tasks is not None: config.number_of_tasks = max_tasks
    if task_ids: config.task_ids = task_ids
    config.evaluate_results = evaluate
    if metric: config.evaluation_metric = metric
    final_output_dir = output_dir or config.output_dir or "rollout_results"
    from .pipeline import RolloutPipeline
    pipeline = RolloutPipeline(config=config, output_dir=final_output_dir)
    summary = pipeline.run()
    return summary.to_dict()
```

调用（见 `examples/DocAgent.md:310-313`）：

```python
from rollout import pipeline
pipeline(config_path="configs/trajectory/doc_trajectory.json")
```

### 5.2 Benchmark 数据格式

从 `examples/DocAgent.md:365-367` 可见 benchmark JSONL 格式：

```jsonl
{"doc_id": "task_001", "question": "...XML outline...\nAnswer the following question:\nWho is the commanding officer in the first figure on the second page?", "answer": "Capt. John W. Sanders", "kwargs": {"seed_path": "/abs/path/to/seed"}}
```

字段别名（`examples/DocAgent.md:381-383`）：`doc_id`/`task_id`/`id`、`question`/`query`/`input`、`answer`/`ground_truth`/`expected`。

### 5.3 AgentRunner 与 Sandbox 交互

`rollout/core/runner.py:223-323` 的 `_run_conversation` 是多轮对话循环：

```python
# rollout/core/runner.py:243-323  核心循环
while turn_count < self.config.max_turns:
    api_messages = [m.to_dict() for m in messages]
    response = await async_chat_completion(
        self.client, model=self.config.model_name,
        messages=api_messages,
        tools=self.tool_schemas if self.tool_schemas else None,   # OpenAI function calling
        max_retries=self.config.max_retries
    )
    assistant_message = response.choices[0].message
    ...
    if assistant_message.tool_calls:
        for tool_call in assistant_message.tool_calls[:1]:   # 一次执行一个
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            # task_kwargs（含 seed_path）合并进参数
            tool_result = await self._execute_tool(tool_name, tool_args, **task_kwargs)
            ...
            tool_msg = Message(role="tool", content=result_text, tool_call_id=tool_call.id, name=tool_name)
            messages.append(tool_msg)
        turn_count += 1
        continue
    else:
        # 没有工具调用 = 最终答案
        final_answer = assistant_message.content or ""
        return extract_final_answer(final_answer)
```

`_execute_tool`（`runner.py:325-350`）把 `task_kwargs`（含 `seed_path`）合并进参数后调 `self.sandbox.execute(tool_name, parameters)`。

### 5.4 quick_rollout（单题快速跑）

`rollout/api.py:113-186`，适合单文档单问题快速验证：

```python
from rollout import quick_rollout
result = quick_rollout(
    "该SRS第3.2节的温度范围与表格2是否一致？",
    tools=["doc:search", "doc:read"],
    model_name="gpt-4.1-2025-04-14",
    api_key="...", base_url="...",
    max_turns=10,
    sandbox_url="http://127.0.0.1:18890",
)
```

---

## 6. 配置文件完整结构

### 6.1 Sandbox 服务器配置（doc_config.json）

源码：`configs/sandbox-server/doc_config.json`：

```json
{
  "server": {
    "url": "http://127.0.0.1:18890",
    "port": 18890,
    "session_ttl": 300
  },
  "apis": {
    "doc": {
      "_comment_required": "Required: vlm_model / vlm_api_key / vlm_api_url (can be provided via env vars)",
      "_comment_fallback": "Fallback defaults: max_search_results / max_image_num / max_text_token / vlm_max_tokens / vlm_timeout / vlm_retry_max_attempts",
      "seed_path": "seeds/doc/seed/2210.02442v1",
      "max_search_results": 10,
      "max_image_num": 10,
      "max_text_token": 20000,
      "vlm_model": "openai/gpt-4o-mini",
      "vlm_api_key": "${VLM_API_KEY}",
      "vlm_api_url": "https://openrouter.ai/api/v1",
      "vlm_max_tokens": 16384,
      "vlm_timeout": 300,
      "vlm_retry_max_attempts": 10
    }
  }
}
```

每个字段含义（对照 `doc_tool.py` 的 `get_config` 调用）：

| 字段 | 用途 | 代码位置 |
|------|------|----------|
| `seed_path` | 默认 seed 目录（被 seed.jsonl 的 kwargs.seed_path 覆盖） | `doc_tool.py:525,749` |
| `max_search_results` | search 每关键词最大返回数 | `doc_tool.py:534` |
| `max_image_num` | read 每次最多视觉输入数 | `doc_tool.py:758` |
| `max_text_token` | read 文本最大字符数 | `doc_tool.py:764` |
| `vlm_model` | VLM 模型名 | `doc_tool.py:773` |
| `vlm_api_key` | VLM API key（`${VAR}` 会展开） | `doc_tool.py:774` |
| `vlm_api_url` | VLM API base url | `doc_tool.py:775` |
| `vlm_max_tokens` | VLM 最大输出 token | `doc_tool.py:776` |
| `vlm_timeout` | VLM 超时秒数 | `doc_tool.py:777` |
| `vlm_retry_max_attempts` | VLM 重试次数 | `doc_tool.py:778` |

### 6.2 Synthesis 配置（doc_config.json）

源码：`configs/synthesis/doc_config.json`：

```json
{
  "model_name": "openai/gpt-oss-120b",
  "api_key": "${OPENROUTER_API_KEY}",
  "base_url": "https://openrouter.ai/api/v1",
  
  "max_depth": 20,
  "branching_factor": 2,
  "depth_threshold": 2,
  "min_depth": 3,
  "max_selected_traj": 2,
  "path_similarity_threshold": 0.7,
  "number_of_seed": null,
  
  "resource_types": [],
  "resource_init_configs": {},
  
  "sandbox_server_url": "http://127.0.0.1:18890",
  "sandbox_auto_start": true,
  "sandbox_config_path": "configs/sandbox-server/doc_config.json",
  "sandbox_timeout": 300,
  
  "available_tools": ["doc-search", "doc-read"],
  "seed_description": "Outline of PDF document",
  "sampling_tips": [...],
  "synthesis_tips": [...],
  "qa_examples": [...],
  "seeds_file": "seeds/doc/seeds.jsonl",
  "output_dir": "results/doc"
}
```

字段对照 `SynthesisConfig`（`synthesis/core/config.py:11-60`）：

| 字段 | 默认 | 含义 |
|------|------|------|
| `model_name` | `gpt-4.1-2025-04-14` | 探索+合成用的主 LLM |
| `max_depth` | 5（doc 用 20） | 轨迹树最大深度 |
| `branching_factor` | 2 | 每节点子节点数（depth < depth_threshold 时） |
| `depth_threshold` | 3（doc 用 2） | 超过此深度后只生成 1 个子节点 |
| `min_depth` | 2（doc 用 3） | 轨迹被选中的最小深度 |
| `max_selected_traj` | 3（doc 用 2） | 每 seed 最多选几条轨迹 |
| `path_similarity_threshold` | 0.7 | Jaccard 去重阈值 |
| `sandbox_auto_start` | True | 自动启动 sandbox 服务器 |
| `sandbox_config_path` | - | sandbox 服务器配置（含 VLM 配置） |
| `available_tools` | [] | 工具白名单（支持 `doc-*` 通配） |
| `sampling_tips` | "" | 注入探索 prompt 的策略提示 |
| `synthesis_tips` | "" | 注入 QA 合成 prompt 的约束 |
| `qa_examples` | [] | few-shot 示例 |
| `number_of_seed` | None | 限制处理的 seed 数量 |

### 6.3 Trajectory / Infer 配置

`configs/trajectory/doc_trajectory.json`（轨迹合成）和 `configs/infer/doc_infer.json`（推理评测）结构类似，关键字段：`max_turns`（40-50）、`system_prompt`、`data_path`（benchmark 路径）、`evaluate_results`、`evaluation_metric`（如 `MMLongBench-Doc_LasJ`）。

### 6.4 工具名别名机制

注意配置里 `available_tools` 写的是 `doc-search`/`doc-read`（连字符），而注册名是 `doc:search`/`doc:read`（冒号）。`sandbox/tool_schemas/__init__.py:19-37` 的 `_tool_name_aliases` 处理这种等价：

```python
# sandbox/tool_schemas/__init__.py:19-37
def _tool_name_aliases(name: str) -> set[str]:
    aliases = {name}
    if ":" in name:
        prefix, suffix = name.split(":", 1)
        aliases.add(f"{prefix}-{suffix}")
    if "_" in name:
        prefix, suffix = name.split("_", 1)
        aliases.add(f"{prefix}-{suffix}")
    if "-" in name:
        prefix, suffix = name.split("-", 1)
        aliases.add(f"{prefix}:{suffix}")
        aliases.add(f"{prefix}_{suffix}")
    return aliases
```

所以 `doc-search`、`doc:search`、`doc_search` 三种写法等价。

---

## 7. PDF 预处理（DocDancer）

这是把 SRS PDF 转成 AgentFlow seed 格式的关键。三步流水线（`projects/DocDancer/PDF_preprocess/run_pipeline.sh`）：

```
1_run_pdf_extract.py   (MinerU OCR)  → *_ocr.json
2_process_extracted_data.py           → data.pkl + figures/ + tables/ + page_images/
3_get_outline_and_root.py             → outline.xml + all_content.xml
```

### 7.1 步骤 1：PDF 提取

`1_run_pdf_extract.py:20-36` 用 MinerU2.5 VLM 模型 + vLLM 做 OCR：

```python
# 1_run_pdf_extract.py:24-36
class MinerUPDFProcessor:
    def __init__(self, model_name="opendatalab/MinerU2.5-2509-1.2B"):
        self.llm = LLM(model=model_name, logits_processors=[MinerULogitsProcessor])
        self.client = MinerUClient(backend="vllm-engine", vllm_llm=self.llm)
    
    def process_pdf(self, pdf_path, output_dir):
        pages = convert_from_path(str(pdf_path), dpi=300)
        all_page_results = self.client.batch_two_step_extract(pages)
        # 每页的 block：bbox + type + content，保存为 *_ocr.json
```

运行（`run_pipeline.sh:100-103`）：

```bash
python 1_run_pdf_extract.py \
    --input_dir test_PDF \
    --output_dir output/ocr_json \
    --model_path opendatalab/MinerU2.5-2509-1.2B
```

### 7.2 步骤 2：数据处理

`2_process_extracted_data.py` 把 OCR JSON 转成 `data.pkl`（pandas DataFrame，每行一个元素，`style` 字段标识类型：`Heading 1/2/3`、`Text`、`Image`、`Table`、`Caption` 等），并提取 `figures/`、`tables/`、`page_images/`。还会用 VLM 给图片生成 `alt_text`（`2_process_extracted_data.py:20-81` 的 PROMPT）。

### 7.3 步骤 3：生成 outline.xml 和 all_content.xml

`3_get_outline_and_root.py:21-258` 的 `DocReader` 是核心。它读 `data.pkl`，按 Heading 层级构建 Section 树，生成两个 XML：

- `all_content.xml`：完整内容树（`<Document>` 根，含 `<Section>/<Paragraph>/<Image>/<HTML_Table>`）
- `outline.xml`：精简大纲（`<Outline>` 根，段落只保留 `first_sentence` 属性，图片只保留 `first_sentence_of_image_description`）

**Section ID 生成逻辑**（`3_get_outline_and_root.py:60-127`）：层级用点号分隔，如 `3.2.1`。同级 +1，下级加 `.1`。

**all_content.xml 节点类型**（`3_get_outline_and_root.py:129-205`）：

| style | XML 节点 | 属性 |
|-------|----------|------|
| `Heading N` | `<Section>` + `<Heading>` | `section_id`, `start_page_num`, `end_page_num` |
| `Text`/`List`/`Equation` 等 | `<Paragraph>` | `page_num` |
| `Image` | `<Image>` + `<Alt_Text>` + `<Caption>` | `image_id`, `page_num` |
| `Table` | `<HTML_Table>` | `table_id`, `page_num`（文本是 HTML 表格） |
| `Title` | `<Title>` | `page_num` |

运行（`run_pipeline.sh:131`）：

```bash
python 3_get_outline_and_root.py output/processed
```

输出目录结构（`run_pipeline.sh:143-153`）：

```
output/processed/<PDF名>/
├── data.pkl              # 结构化 DataFrame
├── <PDF名>.json
├── outline.xml           # Agent 起点（精简）
├── all_content.xml       # doc:read 读的全量内容
├── figures/              # image_0.png, image_1.png, ...
├── tables/               # table_0.png, table_1.png, ...
└── page_images/          # page_0000.png, page_0001.png, ...
```

---

## 8. SRS 跨模态冲突检测完整方案

把以上所有部分组合，用 AgentFlow 做 SRS 文档的文本↔表格↔图片跨模态冲突检测。

### 8.1 整体思路

SRS 一致性检测 = 跨模态冲突检测。AgentFlow 的 `doc:read` 已经把"文本+页面图+图片+表格图"一起喂给 VLM 做 evidence 抽取——天然适合检测跨模态冲突。我们用两种模式：

- **模式 A：合成模式**——用 `synthesize()` 自动生成"跨模态冲突检测 QA"训练数据
- **模式 B：推理模式**——用 `rollout()` 让 Agent 对 SRS 做"一致性检查"问答

### 8.2 第一步：把 SRS PDF 预处理成 seed 格式

SRS PDF → AgentFlow seed 目录。用 DocDancer 预处理流水线。

> **复用现有 MinerU**：项目已有 MinerU 环境（`~/mineru-env/bin/python`，见 AGENTS.md）。但 AgentFlow 的 `1_run_pdf_extract.py` 用的是 `mineru-vl-utils` + vLLM，和项目里的 `magic-pdf` CLI 不同。两个选择：
> - 选择 1：装 vLLM 跑 `1_run_pdf_extract.py`（需要 GPU）
> - 选择 2：用项目已有的 MinerU 输出（`data/gjb_438c/mineru_srs/`），写转换脚本生成 `data.pkl` + `outline.xml` + `all_content.xml` + 图片目录

下面给选择 2 的转换脚本（基于 `3_get_outline_and_root.py` 的格式约定）：

```python
# tools/srs_to_agentflow_seed.py
"""
把 SRS 的 MinerU 结构化输出转成 AgentFlow seed 格式。
输入：MinerU 解析结果（已有 md + json + images）
输出：outline.xml, all_content.xml, figures/, tables/, page_images/, data.pkl
"""
import os
import json
import pickle
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import pandas as pd
import fitz  # PyMuPDF


def build_data_pkl(mineru_json_path: str, pdf_path: str, output_dir: str):
    """
    构建 data.pkl（pandas DataFrame）。
    列：style, para_text, table_id, page_num
    style 取值：Heading 1/2/3, Text, Image, Table, Caption, Page_Start, Title
    """
    rows = []
    with open(mineru_json_path, "r", encoding="utf-8") as f:
        mineru_data = json.load(f)
    
    # MinerU 输出通常是 list of pages，每页有 blocks
    page_idx = 0
    for page in mineru_data:  # 按 3_get_outline_and_root.py:192-193 约定
        rows.append({"style": "Page_Start", "para_text": "", "table_id": page_idx})
        for block in page.get("blocks", []):
            btype = block.get("type", "text").lower()
            content = block.get("content", "")
            if "heading" in btype or "title" in btype:
                level = block.get("level", 1)
                rows.append({"style": f"Heading {level}", "para_text": content, "table_id": page_idx})
            elif "image" in btype:
                img_path = block.get("image_path", f"figures/image_{len(rows)}.png")
                rows.append({"style": "Image", "para_text": {"path": img_path, "alt_text": None}, "table_id": page_idx})
            elif "table" in btype:
                rows.append({"style": "Table", "para_text": {"content": content, "image_path": None}, "table_id": page_idx})
            else:
                rows.append({"style": "Text", "para_text": content, "table_id": page_idx})
        page_idx += 1
    
    df = pd.DataFrame(rows)
    os.makedirs(output_dir, exist_ok=True)
    df.to_pickle(os.path.join(output_dir, "data.pkl"))
    return df


def extract_page_images(pdf_path: str, output_dir: str, dpi: int = 200):
    """用 PyMuPDF 生成 page_images/page_0000.png ..."""
    page_dir = os.path.join(output_dir, "page_images")
    os.makedirs(page_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        pix.save(os.path.join(page_dir, f"page_{i:04d}.png"))
    doc.close()


def main(srs_pdf: str, mineru_json: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    # 1. 构建 data.pkl
    build_data_pkl(mineru_json, srs_pdf, output_dir)
    # 2. 提取页面图
    extract_page_images(srs_pdf, output_dir)
    # 3. 调用 3_get_outline_and_root.py 生成 XML
    #    （直接 import 或 subprocess 调用）
    import sys
    sys.path.insert(0, "dataflow_repos/AgentFlow/projects/DocDancer/PDF_preprocess")
    from importlib import import_module
    gen = import_module("3_get_outline_and_root")
    document = gen.DocReader(data_path=output_dir)
    outline_root = document.get_outline_root(skip_para_after_page=1000)  # SRS 通常短，不截断
    ET.ElementTree(outline_root).write(os.path.join(output_dir, "outline.xml"), encoding="utf-8", xml_declaration=True)
    ET.ElementTree(document.root).write(os.path.join(output_dir, "all_content.xml"), encoding="utf-8", xml_declaration=True)
    print(f"✅ Seed 生成完成: {output_dir}")


if __name__ == "__main__":
    main(
        srs_pdf="data/gjb_438c/mineru_srs/battery_srs.pdf",
        mineru_json="data/gjb_438c/mineru_srs/battery_srs/structured.json",
        output_dir="dataflow_repos/AgentFlow/seeds/srs/seed/battery_srs",
    )
```

> 注：`figures/` 和 `tables/` 如果 MinerU 已提取图片，直接复制即可。文件名必须是 `image_N.png` / `table_N.png`（`doc_tool.py:388-397,429`）。

### 8.3 第二步：生成 seeds.jsonl

```python
# 生成 seeds/srs/seeds.jsonl
import json
from pathlib import Path

seed_dir = Path("dataflow_repos/AgentFlow/seeds/srs/seed/battery_srs")
outline_xml = (seed_dir / "outline.xml").read_text(encoding="utf-8")

seed = {
    "content": outline_xml,                                    # outline.xml 全文
    "kwargs": {"seed_path": str(seed_dir.resolve())}          # 绝对路径
}
with open("dataflow_repos/AgentFlow/seeds/srs/seeds.jsonl", "w", encoding="utf-8") as f:
    f.write(json.dumps(seed, ensure_ascii=False) + "\n")
```

### 8.4 第三步：配置跨模态冲突检测的 synthesis

基于 `configs/synthesis/doc_config.json` 改造，重点改 `sampling_tips` 和 `synthesis_tips`，引导 Agent 做冲突检测：

```json
// configs/synthesis/srs_conflict_config.json
{
  "model_name": "gpt-4.1-2025-04-14",
  "api_key": "${OPENAI_API_KEY}",
  "base_url": "https://api.openai.com/v1",
  
  "max_depth": 15,
  "branching_factor": 2,
  "depth_threshold": 2,
  "min_depth": 3,
  "max_selected_traj": 3,
  "path_similarity_threshold": 0.6,
  "number_of_seed": null,
  
  "resource_types": [],
  "resource_init_configs": {},
  
  "sandbox_server_url": "http://127.0.0.1:18890",
  "sandbox_auto_start": true,
  "sandbox_config_path": "configs/sandbox-server/srs_config.json",
  "sandbox_timeout": 300,
  
  "available_tools": ["doc-search", "doc-read"],
  "seed_description": "GJB 438C SRS 文档大纲（软件需求规格说明书）",
  
  "sampling_tips": [
    "探索 SRS 文档，收集跨模态冲突检测的证据：文本需求 vs 表格参数 vs 图片示意图",
    "重点搜索以下关键词：温度、范围、要求、约束、接口、性能、图、表",
    "用 doc:search 找到相关章节后，用 doc:read 读取，goal 设为'提取该节的所有数值约束和接口定义'",
    "对同一个需求，至少读取 2 个不同 section（如需求描述节 + 接口表格节），以便对比",
    "特别关注：文本中写的数值 vs 表格中的数值是否一致；图片示意 vs 文字描述是否冲突",
    "收集跨页证据：需求在 A 页，对应表格/图在 B 页",
    "不要在问题里直接引用 section_id 或页码",
    "seed_path 自动从 seed.jsonl 注入，调用时不用写"
  ],
  
  "synthesis_tips": [
    "生成跨模态冲突检测的 QA：问题要求对比文本与表格/图片的一致性",
    "答案必须是具体事实：'一致'/'不一致，文本为X表格为Y'/'差值为N'",
    "必须 >=3 跳推理：先读文本需求 → 再读表格参数 → 再对比 → 得出结论",
    "必须跨 >=2 页，且至少涉及一个表格或图片",
    "问题类型示例：'某需求的温度上限与接口表中的温度范围是否一致？差值是多少？'",
    "禁止单跳查找题；禁止问页码/section_id",
    "如果轨迹证据不足以支撑冲突判断，换一个问题，不要臆测"
  ],
  
  "qa_examples": [
    {
      "question": "SRS第3.2节要求工作温度上限为70°C，而接口需求表（IRT）中列出的温度上限是85°C。这两者是否一致？",
      "answer": "不一致，表格比文本高15°C"
    },
    {
      "question": "电源需求描述的输入电压范围是5V±0.5V，而接口图（图3）标注的电压范围是5V±0.25V。两者是否冲突？",
      "answer": "冲突，图的范围更窄"
    }
  ],
  
  "seeds_file": "seeds/srs/seeds.jsonl",
  "output_dir": "results/srs_conflict"
}
```

对应的 sandbox 配置：

```json
// configs/sandbox-server/srs_config.json
{
  "server": {
    "url": "http://127.0.0.1:18890",
    "port": 18890,
    "session_ttl": 300
  },
  "apis": {
    "doc": {
      "max_search_results": 15,
      "max_image_num": 15,
      "max_text_token": 30000,
      "vlm_model": "gpt-4o",
      "vlm_api_key": "${OPENAI_API_KEY}",
      "vlm_api_url": "https://api.openai.com/v1",
      "vlm_max_tokens": 16384,
      "vlm_timeout": 300,
      "vlm_retry_max_attempts": 10
    }
  }
}
```

### 8.5 第四步：启动 sandbox + 跑合成

```bash
# 终端 1：启动 sandbox 服务器（doc 工具会被自动注册）
cd dataflow_repos/AgentFlow
export OPENAI_API_KEY="sk-..."
./start_sandbox_server.sh --config configs/sandbox-server/srs_config.json

# 终端 2：跑合成
cd dataflow_repos/AgentFlow
python -m synthesis.pipeline --config configs/synthesis/srs_conflict_config.json
```

或 Python API：

```python
from synthesis import synthesize
synthesize(config_path="configs/synthesis/srs_conflict_config.json")
```

输出在 `results/srs_conflict/synthesized_qa.jsonl`，每条是一个跨模态冲突检测 QA + reasoning_steps。

### 8.6 第五步：直接做一致性检测（推理模式）

构造 benchmark，用 `rollout` 让 Agent 对 SRS 做一致性检查：

```python
# 生成 SRS 一致性检测 benchmark
import json
from pathlib import Path

seed_dir = Path("dataflow_repos/AgentFlow/seeds/srs/seed/battery_srs")
outline_xml = (seed_dir / "outline.xml").read_text(encoding="utf-8")

tasks = [
    {
        "doc_id": "srs_conflict_001",
        "question": f"""以下是 SRS 文档大纲：
{outline_xml}

请检查：文档中关于电池工作温度范围的文本描述，与接口需求表格中的温度参数是否一致？如不一致，指出差异。
""",
        "answer": "",  # 开放式检查，无固定答案
        "answer_format": "Str",
        "kwargs": {"seed_path": str(seed_dir.resolve())}
    },
    {
        "doc_id": "srs_conflict_002",
        "question": f"""以下是 SRS 文档大纲：
{outline_xml}

检查第3节的性能需求与第5节的接口需求是否存在数值矛盾。给出具体矛盾点。
""",
        "answer": "",
        "kwargs": {"seed_path": str(seed_dir.resolve())}
    },
]

with open("dataflow_repos/AgentFlow/benchmark/srs_benchmark.jsonl", "w", encoding="utf-8") as f:
    for t in tasks:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")
```

推理配置：

```json
// configs/infer/srs_infer.json
{
  "benchmark_name": "srs_conflict",
  "model_name": "gpt-4.1-2025-04-14",
  "api_key": "${OPENAI_API_KEY}",
  "base_url": "https://api.openai.com/v1",
  "max_turns": 30,
  "available_tools": ["doc:search", "doc:read"],
  "sandbox_server_url": "http://127.0.0.1:18890",
  "system_prompt": [
    "你是 SRS 文档一致性检测专家。",
    "你会收到 SRS 文档的 XML 大纲。",
    "使用 doc:search 和 doc:read 工具检索文档，检测文本、表格、图片之间的跨模态冲突。",
    "最终回答必须明确指出冲突点（如有），引用具体证据。"
  ],
  "evaluate_results": false,
  "data_path": "benchmark/srs_benchmark.jsonl",
  "output_dir": "infer_results/srs",
  "save_results": true,
  "save_trajectories": true,
  "parallel": false
}
```

跑推理：

```python
from rollout import pipeline
pipeline(config_path="configs/infer/srs_infer.json")
```

### 8.7 单文档快速检测（最简调用）

如果只想快速检查一份 SRS，用 `quick_rollout`（`rollout/api.py:113-186`）：

```python
import asyncio
from rollout import quick_rollout

seed_dir = "/abs/path/to/srs_seed"
with open(f"{seed_dir}/outline.xml", encoding="utf-8") as f:
    outline = f.read()

# quick_rollout 不支持传 task_kwargs，需用 AgentRunner 直接调
from rollout.core.config import RolloutConfig
from rollout.core.runner import AgentRunner
from rollout.core.models import BenchmarkItem

config = RolloutConfig(
    model_name="gpt-4.1-2025-04-14",
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    max_turns=20,
    available_tools=["doc:search", "doc:read"],
    sandbox_server_url="http://127.0.0.1:18890",
    sandbox_auto_start=False,
    save_trajectories=True,
    system_prompt="你是SRS一致性检测专家。用工具检索文档，检测文本/表格/图片间的跨模态冲突。",
)

async def check_srs():
    runner = AgentRunner(config, worker_id="srs_checker")
    await runner.start()
    try:
        task = BenchmarkItem(
            id="srs_check",
            question=f"以下是SRS文档大纲：\n{outline}\n\n请检索文档，检测其中文本需求与表格参数、图片示意之间的跨模态冲突，列出所有冲突点。",
            kwargs={"seed_path": seed_dir},   # 关键：seed_path 通过 kwargs 注入 doc 工具
        )
        result = await runner.run_task(task)
        print("答案:", result.predicted_answer)
        print("轨迹:", [tc.tool_name for tc in result.trajectory.tool_calls])
        return result
    finally:
        await runner.stop()

result = asyncio.run(check_srs())
```

### 8.8 直接调用 doc 工具（不走 Agent，最底层）

如果要完全控制检索逻辑，直接用 Sandbox 客户端调 `doc:search` 和 `doc:read`：

```python
import asyncio
from sandbox import Sandbox, format_tool_result

async def manual_cross_modal_check(seed_path: str):
    sandbox = Sandbox(server_url="http://127.0.0.1:18890", auto_start_server=False)
    await sandbox.start()
    try:
        # 1. 搜索"温度"
        search_res = await sandbox.execute("doc:search", {
            "key_words": ["温度", "工作范围", "接口"],
            "seed_path": seed_path,
        })
        print("搜索结果:", format_tool_result(search_res, verbose=False)[:500])

        # 2. 读取包含温度的 section（假设搜索到 section_id="3.2"）
        read_res = await sandbox.execute("doc:read", {
            "section_ids": ["3.2", "5.1"],   # 需求节 + 接口节
            "goal": "提取该节中所有与温度相关的数值约束，以及接口表格中的温度参数，对比是否一致",
            "seed_path": seed_path,
            "max_image_num": 15,
        })
        print("VLM 抽取结果:", format_tool_result(read_res, verbose=False))
        # read_res["data"]["result"] 含 VLM 返回的 evidence + summary
    finally:
        await sandbox.close()

asyncio.run(manual_cross_modal_check("/abs/path/to/srs_seed"))
```

这就是跨模态冲突检测的最底层调用：`doc:read` 内部把 section 的页面图+图片+表格图+文本一起喂给 VLM，VLM 在 `GET_USEFUL_INFO_PROMPT` 引导下做跨模态 evidence 抽取。

---

## 附录：关键文件索引

| 功能 | 文件 | 关键行 |
|------|------|--------|
| Doc 工具实现 | `sandbox/server/backends/tools/doc_tool.py` | 全文 829 行 |
| 工具 schema | `sandbox/tool_schemas/doc_tools.py` | 11-102 |
| 工具注册 | `sandbox/server/backends/tools/__init__.py` | 59-119, 224 |
| Sandbox 门面 | `sandbox/sandbox.py` | 150-1257 |
| HTTP 路由 | `sandbox/server/routes.py` | 34-763 |
| HTTP 端点常量 | `sandbox/protocol.py` | 193-225 |
| 合成入口 | `synthesis/api.py` | 62-84 |
| 合成 pipeline | `synthesis/pipeline.py` | 39-219 |
| 轨迹采样器 | `synthesis/core/sampler.py` | 20-374 |
| 轨迹选择器 | `synthesis/core/selector.py` | 12-171 |
| QA 合成器 | `synthesis/core/synthesizer.py` | 15-228 |
| 合成配置 | `synthesis/core/config.py` | 11-168 |
| 数据模型 | `synthesis/core/models.py` | 9-65 |
| Sandbox worker | `synthesis/core/worker.py` | 18-128 |
| Rollout 入口 | `rollout/api.py` | 54-191 |
| Rollout pipeline | `rollout/pipeline.py` | 36-255 |
| Agent runner | `rollout/core/runner.py` | 30-381 |
| Rollout 配置 | `rollout/core/config.py` | 20-90 |
| PDF 预处理脚本1 | `projects/DocDancer/PDF_preprocess/1_run_pdf_extract.py` | 20-213 |
| PDF 预处理脚本2 | `projects/DocDancer/PDF_preprocess/2_process_extracted_data.py` | 1-489 |
| PDF 预处理脚本3 | `projects/DocDancer/PDF_preprocess/3_get_outline_and_root.py` | 21-303 |
| 预处理流水线 | `projects/DocDancer/PDF_preprocess/run_pipeline.sh` | 1-154 |
| Doc sandbox 配置 | `configs/sandbox-server/doc_config.json` | 1-23 |
| Doc 合成配置 | `configs/synthesis/doc_config.json` | 1-73 |
| Doc 轨迹配置 | `configs/trajectory/doc_trajectory.json` | 1-28 |
| Doc 推理配置 | `configs/infer/doc_infer.json` | 1-34 |
| Seed 示例 | `seeds/doc/seeds.jsonl` | 1 |
| 安装脚本 | `install.sh` | 1-110 |
| 启动脚本 | `start_sandbox_server.sh` | 1-87 |
| 依赖 | `requirements.txt` | 1-77 |
| DocAgent 示例文档 | `examples/DocAgent.md` | 1-541 |
