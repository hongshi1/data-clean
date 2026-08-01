# DataFlow-KG 与 DataMind 代码提取：知识图谱 / 图推理 / 上下文关联检测

> 本文档提取 DataFlow-KG 和 DataMind 的**实际可复现代码**，覆盖知识图谱构建、图推理、GraphRAG、NL2SQL、Memory、Hybrid RAG 等全部核心 API，最后给出基于真实 API 的 SRS 文档上下文关联检测完整代码示例。
>
> 源码版本：
> - DataFlow-KG: main 分支 (v1.0.1)，已克隆到临时目录阅读
> - DataMind: 本地 `dataflow_repos/DataMind/`，含两层架构（`modules/` LlamaIndex 层 + `datamind/capabilities/` 协议层）

---

## 目录

- [Part 1: DataFlow-KG](#part-1-dataflow-kg)
  - [1.1 安装与 CLI](#11-安装与-cli)
  - [1.2 核心抽象](#12-核心抽象)
  - [1.3 9 个算子包总览](#13-9-个算子包总览)
  - [1.4 general_kg：三元组抽取](#14-general_kg三元组抽取)
  - [1.5 graph_reasoning：多跳路径推理](#15-graph_reasoning多跳路径推理)
  - [1.6 graph_rag：图谱检索增强问答](#16-graph_rag图谱检索增强问答)
  - [1.7 domain_kg：领域知识图谱](#17-domain_kg领域知识图谱)
  - [1.8 一致性评估算子](#18-一致性评估算子)
  - [1.9 Pipeline 编排模式](#19-pipeline-编排模式)
- [Part 2: DataMind](#part-2-datamind)
  - [2.1 双层架构概览](#21-双层架构概览)
  - [2.2 安装与启动](#22-安装与启动)
  - [2.3 协议层定义](#23-协议层定义)
  - [2.4 Graph 工具完整 API](#24-graph-工具完整-api)
  - [2.5 NetworkX 图存储实现](#25-networkx-图存储实现)
  - [2.6 NL2SQL 完整 API](#26-nl2sql-完整-api)
  - [2.7 Memory 完整 API](#27-memory-完整-api)
  - [2.8 HybridRetriever RRF 融合](#28-hybridretriever-rrf-融合)
  - [2.9 Agent 循环](#29-agent-循环)
- [Part 3: SRS 上下文关联检测完整代码](#part-3-srs-上下文关联检测完整代码)

---

## Part 1: DataFlow-KG

### 1.1 安装与 CLI

**安装**（来源：`README.zh.md`）：

```bash
conda create -n dfkg python=3.10
conda activate dfkg
pip install uv
uv pip install dataflow-kg

# 启用本地 GPU 推理
uv pip install dataflow-kg[vllm]
```

> DataFlow-KG 支持 Python >= 3.10。

**CLI 命令**（来源：`pyproject.toml:38-39`）：

```toml
[project.scripts]
dfkg = "dataflow.cli:main"
```

```bash
dfkg -v          # 检查版本
dfkg env         # 查看环境
dfkg init        # 初始化项目（生成 api_pipelines/ 和 gpu_pipelines/）
```

`dfkg init` 生成的目录结构：

| 目录 | 所需资源 |
|------|---------|
| `api_pipelines/` | CPU + LLM API |
| `gpu_pipelines/` | CPU + API + 本地 GPU |

每个 pipeline 是一个 Python 文件，设置 API Key 后直接 `python xxx_pipeline.py` 运行：

```bash
export DF_API_KEY=sk-xxxxx
python graph_rag_pipeline.py
```

### 1.2 核心抽象

DataFlow-KG 的所有算子继承自三个核心抽象类。

#### OperatorABC — 算子基类

> 源码：`dataflow/core/operator.py:5-15`

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

每个算子实现 `run(storage, input_key, output_key)` 方法，从 `storage` 读取 DataFrame，处理后写回。

#### LLMServingABC — LLM 服务基类

> 源码：`dataflow/core/llm_serving.py:5-35`

```python
class LLMServingABC(ABC):
    @abstractmethod
    def generate_from_input(self, user_inputs: List[str], system_prompt: str) -> List[str]:
        """Generate data from input. input: List[str]"""
        pass

    @abstractmethod
    def start_serving(self):
        """Start the serving."""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup the generator and garbage collect all GPU/CPU memory."""
        pass
```

实际使用中最常用的是 `APILLMServing_request`（API 调用后端）：

```python
from dataflow.serving import APILLMServing_request

llm_serving = APILLMServing_request(
    api_url="http://your-api-endpoint/v1/chat/completions",
    model_name="gpt-4o",
    max_workers=8,
    temperature=0.0,
)
```

#### DataFlowStorage — 数据存储基类

> 源码：`dataflow/utils/storage.py:13-34`

```python
class DataFlowStorage(ABC):
    @abstractmethod
    def get_keys_from_dataframe(self) -> list[str]: ...

    @abstractmethod
    def read(self, output_type) -> Any:
        """Read data from file. type: "dataframe", List[dict], etc."""
        pass

    @abstractmethod
    def write(self, data: Any) -> Any: ...
```

最常用的实现是 `FileStorage`，它按 step 串联 pipeline 各步骤的输出：

```python
from dataflow.utils.storage import FileStorage

storage = FileStorage(
    first_entry_file_name="input.json",   # 初始输入数据
    cache_path="./kg_output",              # 中间结果缓存目录
    file_name_prefix="kg_step",            # 步骤前缀
    cache_type="json",                     # json | jsonl | csv | parquet | pickle
)

# 每个 .step() 返回 storage 自身，表示推进到下一步
operator.run(storage=storage.step(), input_key="raw_chunk", output_key="triple")
```

### 1.3 9 个算子包总览

> 源码目录：`dataflow/operators/`

| 算子包 | 子目录 | 用途 |
|--------|--------|------|
| `general_kg` | generate / filter / eval / refinement | 通用 KG 构建、QA 生成、质量评估、实体对齐 |
| `commonsense_kg` | — | 常识知识图谱 |
| `temporal_kg` | — | 时序知识图谱 |
| `hyper_relation_kg` | — | 超关系知识图谱 |
| `multi_model_kg` | — | 多模态知识图谱 |
| `graph_rag` | generate / filter / eval | GraphRAG 检索增强问答 |
| `graph_reasoning` | generate / filter / eval | 图推理（多跳路径搜索） |
| `domain_kg` | financial / geospatial / legal / medical / scholar | 领域知识图谱 |
| `pdf2text` | — | PDF 文本提取 |

每个算子包内部的 `generate / filter / eval` 分类：

- **generate**：生成型算子（三元组抽取、路径搜索、答案生成）
- **filter**：过滤型算子（质量筛选、去重、路径长度过滤）
- **eval**：评估型算子（一致性评分、相关性评分、拓扑评估）

### 1.4 general_kg：三元组抽取

#### KGTripleExtraction — 从文本抽取三元组

> 源码：`dataflow/operators/general_kg/generate/kg_triple_extractor.py:25-269`

```python
@OPERATOR_REGISTRY.register()
class KGTripleExtraction(OperatorABC):
    """从原始文本 + 实体列表抽取知识图谱三元组。"""

    def __init__(
        self,
        llm_serving: LLMServingABC,
        seed: int = 0,
        triple_type: str = "attribute",  # "attribute" | "relation"
        lang: str = "en",                # "en" | "zh"
        num_q: int = 5,
    ):
        self.rng = random.Random(seed)
        self.llm_serving = llm_serving
        self.lang = lang
        # 根据 triple_type 选择不同的 prompt 模板
        if triple_type == "attribute":
            self.prompt_template = KGAttributeTripleExtractionPrompt(lang=self.lang)
        elif triple_type == "relation":
            self.prompt_template = KGRelationTripleExtractionPrompt(lang=self.lang)

    def run(
        self,
        storage: DataFlowStorage = None,
        input_key: str = "raw_chunk",      # 输入：原始文本
        input_key_meta: str = "entity",     # 输入：合法实体列表
        output_key: str = "triple",         # 输出：三元组列表
    ):
        dataframe = storage.read("dataframe")
        texts = dataframe[input_key].tolist()
        entity_lists = dataframe[input_key_meta].tolist()
        outputs = self.process_batch(texts, entity_lists)
        dataframe[output_key] = [o.get(output_key, []) for o in outputs]
        output_file = storage.write(dataframe)
        return [output_key]
```

**输入数据格式**（JSON 文件，每行一个记录）：

```json
[
  {
    "raw_chunk": "电池系统的工作电压范围为 9V-16V，额定电压为 12V。",
    "entity": ["电池系统", "工作电压", "额定电压", "12V"]
  }
]
```

**输出数据格式**：

```json
[
  {
    "raw_chunk": "电池系统的工作电压范围为 9V-16V...",
    "entity": ["电池系统", "工作电压", "额定电压", "12V"],
    "triple": [
      "<subj> 电池系统 <obj> 9V-16V <rel> 工作电压范围",
      "<subj> 电池系统 <obj> 12V <rel> 额定电压"
    ]
  }
]
```

三元组字符串格式为 `<subj> {subject} <obj> {object} <rel> {relation}`。

**文本预处理**（`kg_triple_extractor.py:224-268`）：包含中文范围检测、特殊字符比例检查、句号计数等质量门控。

#### KGExtractionPipeline — 完整 KG 抽取流水线

> 源码：`dataflow/statics/pipelines/api_pipelines/kg_extraction_pipeline.py:12-85`

```python
class KGExtractionPipeline:
    def __init__(self):
        self.storage = FileStorage(
            first_entry_file_name="../example_data/KGExtractionPipeline/input.json",
            cache_path="./kg_extraction",
            file_name_prefix="kg_extraction_pipeline",
            cache_type="json",
        )
        self.llm_serving = APILLMServing_request(
            api_url="http://123.129.219.111:3000/v1/chat/completions",
            model_name="gpt-4o",
            max_workers=20,
        )
        # Step 1: 实体抽取
        self.entity_extractor_step1 = KGEntityExtraction(
            llm_serving=self.llm_serving, lang="en")
        # Step 2: 三元组抽取
        self.triple_extractor_step2 = KGTripleExtraction(
            llm_serving=self.llm_serving, triple_type="relation", lang="en")
        # Step 3: 关系三元组推理
        self.triple_inference_step3 = KGRelationTripleInference(
            llm_serving=self.llm_serving, lang="en", merge_to_input=True)
        # Step 4: 去重
        self.tuple_dedup_step4 = KGTupleRemoveRepeated(lang="en")
        # Step 5: 有效性验证
        self.tuple_validation_step5 = KGTupleValidity(
            llm_serving=self.llm_serving, lang="en", triple_type="relation")

    def forward(self):
        self.entity_extractor_step1.run(
            storage=self.storage.step(), input_key="raw_chunk", output_key="entity")
        self.triple_extractor_step2.run(
            storage=self.storage.step(), input_key="raw_chunk",
            input_key_meta="entity", output_key="triple")
        self.triple_inference_step3.run(
            storage=self.storage.step(), input_key="triple", output_key="inferred_triple")
        self.tuple_dedup_step4.run(
            storage=self.storage.step(), input_key="triple", output_key="triple")
        self.tuple_validation_step5.run(
            storage=self.storage.step(), input_key="triple", output_key="valid_triple")
```

### 1.5 graph_reasoning：多跳路径推理

#### KGReasoningPathSearch — 多跳路径搜索

> 源码：`dataflow/operators/graph_reasoning/generate/reasoning_path_search.py:15-192`

```python
@OPERATOR_REGISTRY.register()
class KGReasoningPathSearch(OperatorABC):
    """在知识图谱中搜索目标实体对之间的所有多跳路径。

    输入列:
        - triplet: List[str]            # 三元组列表
        - target_entity: str 或 List[List[str]]  # 目标实体对

    输出列:
        - mpath: List[List[List[str]]]  # 按实体对分组的路径
    """

    def __init__(self, max_hop: int = 10):
        self.max_hop = max_hop
        self.rel_pattern = re.compile(
            r"<subj>\s*(.+?)\s*<obj>\s*(.+?)\s*<rel>\s*(.+?)$"
        )

    def run(
        self,
        storage: DataFlowStorage = None,
        input_key: str = "triple",
        output_key: str = "mpath",
    ) -> List[str]:
        df = storage.read("dataframe")
        # ... BFS 搜索所有路径 ...
        df[output_key] = all_paths
        output_file = storage.write(df)
        return [output_key]
```

**核心算法**：构建无向图邻接表，BFS 搜索两个目标实体之间的所有简单路径（路径长度 ≤ max_hop）。

```python
# reasoning_path_search.py:85-93 — 构建无向图
def _build_graph(self, triplets: List[str]):
    adj = defaultdict(list)
    for t in triplets:
        h, r, o = self._parse_triplet(t)
        if h is None:
            continue
        adj[h].append((o, t))
        adj[o].append((h, t))  # 无向
    return adj

# reasoning_path_search.py:98-123 — BFS 路径搜索
def _find_paths_between(self, adj, src: str, tgt: str) -> List[List[str]]:
    paths = []
    queue = deque()
    queue.append((src, [], {src}))  # node, path(triples), visited set
    while queue:
        cur, cur_path, visited = queue.popleft()
        if len(cur_path) > self.max_hop:
            continue
        if cur == tgt and cur_path:
            paths.append(cur_path)
            continue
        for nxt, triple in adj.get(cur, []):
            if nxt in visited:
                continue
            queue.append((nxt, cur_path + [triple], visited | {nxt}))
    return paths
```

#### KGReasoningConstrainedPathSearch — 约束路径搜索

> 源码：`dataflow/operators/graph_reasoning/generate/reasoning_constrained_path_search.py:15-169`

```python
@OPERATOR_REGISTRY.register()
class KGReasoningConstrainedPathSearch(OperatorABC):
    """带约束的多跳路径搜索。

    约束条件:
        - must_pass_entities: 路径必须经过的实体
        - allowed_relations: 只允许的关系类型
        - required_entity_types: 必须包含的实体类型
    """

    def __init__(
        self,
        llm_serving: LLMServingABC = None,
        max_hop: int = 3,
        must_pass_entities: List[str] = None,
        allowed_relations: List[str] = None,
        required_entity_types: List[str] = None,
        entity_type_map: Dict[str, str] = None,
    ):
        self.max_hop = max_hop
        self.must_pass_entities = set(must_pass_entities or [])
        self.allowed_relations = set(allowed_relations or [])
        self.required_entity_types = set(required_entity_types or [])
        self.entity_type_map = entity_type_map or {}

    # 约束检查 — reasoning_constrained_path_search.py:98-105
    def _check_constraints(self, path_entities: List[str]) -> bool:
        if self.must_pass_entities and not self.must_pass_entities.issubset(set(path_entities)):
            return False
        if self.required_entity_types:
            types_in_path = {self.entity_type_map.get(e) for e in path_entities}
            if not self.required_entity_types.intersection(types_in_path):
                return False
        return True
```

#### KGReasoningRelationGeneration — 基于路径推断关系

> 源码：`dataflow/operators/graph_reasoning/generate/reasoning_rel_generator.py:17-154`

```python
@OPERATOR_REGISTRY.register()
class KGReasoningRelationGeneration(OperatorABC):
    """基于多跳路径，用 LLM 推断目标实体对之间的关系。

    输入列:
        - target_entity: List[List[str]]  # 如 [["Henry, Berlin"]]
        - mpath: List[List[List[str]]]    # 对应的路径

    输出列:
        - inferred_triplets: List[List[str]]
    """

    def __init__(
        self,
        llm_serving: LLMServingABC,
        restrict_to_path_rel: bool = True,  # 只从路径中收集候选关系
        lang: str = "en",
    ):
        self.llm_serving = llm_serving
        self.restrict_to_path_rel = restrict_to_path_rel
        self.prompt = KGReasoningRelationInferencePrompt(lang=self.lang)
```

#### GraphReasoningPipeline — 完整图推理流水线

> 源码：`dataflow/statics/pipelines/api_pipelines/graph_reasoning_pipeline.py:15-90`

```python
class GraphReasoningPipeline(PipelineABC):
    """图推理流水线: 目标实体对 -> 多跳路径 -> 路径过滤 -> 推断关系"""

    def __init__(self, lang="en", max_hop=4, min_length=2, max_length=4,
                 restrict_to_path_rel=True):
        llm_serving = APILLMServing_request(
            api_url="http://123.129.219.111:3000/v1/chat/completions",
            model_name="gpt-4o", max_workers=8, temperature=0.0)
        self.storage = FileStorage(
            first_entry_file_name="../example_data/GraphReasoningPipeline/input.json",
            cache_path="./graph_reasoning", file_name_prefix="graph_reasoning_pipeline_step",
            cache_type="json")
        # Step 1: 多跳路径搜索
        self.path_search_step1 = KGReasoningPathSearch(max_hop=max_hop)
        # Step 2: 路径长度评估
        self.path_length_step2 = KGReasoningPathLengthEvaluator()
        # Step 3: 路径长度过滤
        self.path_filter_step3 = KGReasoningPathLengthFilter(
            min_length=min_length, max_length=max_length)
        # Step 4: 关系推断
        self.relation_generation_step4 = KGReasoningRelationGeneration(
            llm_serving=llm_serving, restrict_to_path_rel=restrict_to_path_rel, lang=lang)

    def forward(self):
        self.path_search_step1.run(storage=self.storage.step(),
            input_key="triple", output_key="mpath")
        self.path_length_step2.run(storage=self.storage.step(),
            input_key="mpath", output_key="mpath_length")
        self.path_filter_step3.run(storage=self.storage.step(),
            mpath_key="mpath", length_key="mpath_length", output_path_key="filtered_mpath")
        self.relation_generation_step4.run(storage=self.storage.step(),
            target_key="target_entity", path_key="filtered_mpath", output_key="inferred_triples")
```

### 1.6 graph_rag：图谱检索增强问答

#### KGGraphRAGQueryExtraction — 从问题抽取检索实体

> 源码：`dataflow/operators/graph_rag/generate/graphrag_query_extractor.py:21-158`

```python
@OPERATOR_REGISTRY.register()
class KGGraphRAGQueryExtraction(OperatorABC):
    """从用户问题中抽取 GraphRAG 检索所需的实体和关系。

    输入: question (str 或 List[str])
    输出: entities (List[str]), relations (List[str])
    """

    def __init__(self, llm_serving: LLMServingABC, seed: int = 0, lang: str = "en"):
        self.llm_serving = llm_serving
        self.prompt_template = KGQueryExtractionPrompt(lang=self.lang)

    def _extract(self, question: str) -> Dict[str, List[str]]:
        user_prompt = self.prompt_template.build_prompt(question)
        system_prompt = self.prompt_template.build_system_prompt()
        responses = self.llm_serving.generate_from_input(
            user_inputs=[user_prompt], system_prompt=system_prompt)
        cleaned = re.sub(r"```json|```|\n", "", responses[0])
        parsed = json.loads(cleaned)
        return {"entities": parsed.get("entities", []),
                "relations": parsed.get("relations", [])}

    def run(self, storage=None, input_key="question",
            output_keys=["entities", "relations"]):
        dataframe = storage.read("dataframe")
        # ... 对每行问题抽取实体和关系 ...
        dataframe["entities"] = entities_col
        dataframe["relations"] = relations_col
        storage.write(dataframe)
        return output_keys
```

#### KGGraphRAGSubgraphRetrieval — 子图检索与 prompt 生成

> 源码：`dataflow/operators/graph_rag/generate/graphrag_prompt_generator.py:13-255`

```python
@OPERATOR_REGISTRY.register()
class KGGraphRAGSubgraphRetrieval(OperatorABC):
    """围绕问题实体检索 k-hop 子图并生成 GraphRAG prompt。

    输入列: question, entities, triple
    输出列: subgraph_prompt
    """

    def __init__(self, hop: int = 1):
        self.hop = hop

    # k-hop BFS 子图采样 — graphrag_prompt_generator.py:78-109
    @classmethod
    def _k_hop_subgraph(cls, triples, start_entity, hop):
        adj = defaultdict(list)
        for t in triples:
            h, r, o = cls._parse_triple(t)
            if h is None:
                continue
            adj[h].append((o, t))
            adj[o].append((h, t))  # 无向

        visited_entities = {start_entity}
        visited_triples = set()
        queue = deque([(start_entity, 0)])
        while queue:
            cur, depth = queue.popleft()
            if depth == hop:
                continue
            for nxt, raw_t in adj.get(cur, []):
                visited_triples.add(raw_t)
                if nxt not in visited_entities:
                    visited_entities.add(nxt)
                    queue.append((nxt, depth + 1))
        return list(visited_triples)

    # Prompt 构建 — graphrag_prompt_generator.py:114-171
    def _build_single_prompt(self, question, entities, triples):
        entity_catalog = self._build_entity_catalog(triples)
        seed_entities = [e for e in entities if e in entity_catalog]
        # 降级: 无匹配实体时取 KG 中第一个实体
        if not seed_entities and entity_catalog:
            seed_entities = [next(iter(entity_catalog))]
        # 采样子图
        subgraphs = {}
        for ent in seed_entities:
            subgraphs[ent] = self._k_hop_subgraph(triples, ent, self.hop)
        # 组装 prompt
        lines = ["You are given a question and relevant knowledge graph facts.",
                 "Use ONLY the provided facts to answer the question.\n",
                 "Question:", question.strip() + "\n"]
        for ent, sg in subgraphs.items():
            lines.append(f"Subgraph centered at [{ent}]:")
            for t in sg:
                lines.append(f"- {t}")
            lines.append("")
        lines.append("Answer the question based on the above knowledge graph subgraphs.")
        return "\n".join(lines)
```

#### KGGraphRAGGetAnswer — 基于子图 prompt 生成答案

> 源码：`dataflow/operators/graph_rag/generate/graphrag_get_answer.py:13-129`

```python
@OPERATOR_REGISTRY.register()
class KGGraphRAGGetAnswer(OperatorABC):
    """基于 GraphRAG 子图 prompt 用 LLM 生成答案。

    输入列: question (str 或 List[str]), subgraph_prompt (str 或 List[str])
    输出列: answer (str 或 List[str])
    """

    def __init__(self, llm_serving: LLMServingABC, lang: str = "en"):
        self.llm_serving = llm_serving

    def _generate_answer(self, prompt: str) -> str:
        response = self.llm_serving.generate_from_input(
            user_inputs=[prompt],
            system_prompt="You are a knowledge graph reasoning assistant. "
                          "Answer based ONLY on the provided facts.")
        answer = response[0]
        answer = re.sub(r"```.*?```", "", answer, flags=re.DOTALL).strip()
        return answer
```

#### GraphRAGPipeline — 完整 GraphRAG 流水线

> 源码：`dataflow/statics/pipelines/api_pipelines/graph_rag_pipeline.py:17-108`

```python
class GraphRAGPipeline(PipelineABC):
    """GraphRAG pipeline: question -> subgraph retrieval -> answer -> filtering"""

    def __init__(self, lang="en", hop=1,
                 plausibility_min_score=0.95, plausibility_max_score=1.0):
        llm_serving = APILLMServing_request(
            api_url="http://123.129.219.111:3000/v1/chat/completions",
            model_name="gpt-4o", max_workers=8, temperature=0.0)
        self.storage = FileStorage(
            first_entry_file_name="../example_data/GraphRAGPipeline/input.json",
            cache_path="./graph_rag", file_name_prefix="graph_rag_pipeline_step",
            cache_type="json")
        # Step 1: 从问题抽取实体/关系
        self.query_extraction_step1 = KGGraphRAGQueryExtraction(
            llm_serving=llm_serving, lang=lang)
        # Step 2: 子图检索 + prompt 生成
        self.subgraph_retrieval_step2 = KGGraphRAGSubgraphRetrieval(hop=hop)
        # Step 3: 答案生成
        self.answer_generation_step3 = KGGraphRAGGetAnswer(
            llm_serving=llm_serving, lang=lang)
        # Step 4: 问题难度评估
        self.question_difficulty_step4 = KGRAGQuestionDifficultyEvaluation(
            llm_serving=llm_serving, lang=lang)
        # Step 5: 答案可信度评估
        self.answer_plausibility_step5 = KGRAGQuestionPlausibilityEvaluation(
            llm_serving=llm_serving, lang=lang)
        # Step 6: 答案过滤
        self.answer_filter_step6 = KGRAGAnswerPlausibilityFilter(merge_to_input=False)

    def forward(self):
        self.query_extraction_step1.run(storage=self.storage.step(),
            input_key="question", output_keys=["entities", "relations"])
        self.subgraph_retrieval_step2.run(storage=self.storage.step(),
            output_key="subgraph_prompt")
        self.answer_generation_step3.run(storage=self.storage.step(),
            input_keys=["question", "subgraph_prompt"], output_key="answer")
        self.question_difficulty_step4.run(storage=self.storage.step(),
            question_key="question", output_key="question_difficulty")
        self.answer_plausibility_step5.run(storage=self.storage.step(),
            question_key="question", answer_key="answer",
            output_key="question_plausibility_score")
        self.answer_filter_step6.run(storage=self.storage.step(),
            input_key="answer", score_key="question_plausibility_score",
            output_key="filtered_answer",
            min_score=self.plausibility_min_score, max_score=self.plausibility_max_score)
```

### 1.7 domain_kg：领域知识图谱

`domain_kg` 包含 5 个领域子包：`financial_kg`、`geospatial_kg`、`legal_kg`、`medical_kg`、`scholar_kg`。

#### SchoKGTripleExtraction — 学术领域三元组抽取（带本体约束）

> 源码：`dataflow/operators/domain_kg/scholar_kg/generate/schokg_triple_extractor.py:23-353`

与通用 `KGTripleExtraction` 的关键区别：**支持本体（Ontology）约束**。

```python
@OPERATOR_REGISTRY.register()
class SchoKGTripleExtraction(OperatorABC):
    """学术领域知识图谱三元组抽取，基于本体约束。

    输入: raw_chunk (文本), ontology (本体定义)
    输出: triple (三元组列表), entity_class (实体分类列表)
    """

    def __init__(self, llm_serving, seed=0, triple_type="relation", lang="en", num_q=5):
        self.prompt_template = SchoKGRelationExtractorPrompt(lang=self.lang)

    def run(
        self,
        storage: DataFlowStorage = None,
        ontology_lists=None,                           # 本体约束
        input_key: str = "raw_chunk",
        input_key_meta: Union[str, List[str]] = "ontology",
        output_key: str = "triple",
        output_key_meta: str = "entity_class",
    ):
        dataframe = storage.read("dataframe")
        texts = dataframe[input_key].tolist()
        ontology_lists = self._resolve_ontology(ontology_lists, input_key_meta)
        outputs = self.process_batch(texts, ontology_lists)
        dataframe[output_key] = [o.get(output_key, []) for o in outputs]
        dataframe[output_key_meta] = [o.get(output_key_meta, []) for o in outputs]
```

**本体格式**（JSON）：

```json
{
  "entity_type": {
    "researcher": ["name", "affiliation", "field"],
    "paper": ["title", "venue", "year"]
  },
  "relation_type": {
    "authored_by": ["researcher", "paper"],
    "cites": ["paper", "paper"]
  }
}
```

### 1.8 一致性评估算子

`general_kg/eval/` 包含 10 个评估算子，与 SRS 一致性检测直接相关：

#### KGRelationTripleConsistencyEvaluator — 三元组逻辑一致性评估

> 源码：`dataflow/operators/general_kg/eval/kg_rel_triple_consistency_eval.py:12-380`

```python
class KGRelationTripleConsistencyEvaluator(OperatorABC):
    """评估知识图谱关系三元组的逻辑一致性。

    策略:
      1. 从三元组构建图
      2. 采样边，获取每条边的局部上下文（邻居关系）
      3. 用 LLM 判断该边的关系在上下文中是否一致

    输入列: triple (List[str])
    输出列: logical_consistency_score (float [0,1]), evaluated_sample_indices (List[int])
    """

    def __init__(self, llm_serving, sample_rate=1, max_samples=10, lang="en"):
        self.llm_serving = llm_serving
        self.sample_rate = sample_rate
        self.max_samples = max_samples
        self.prompt_manager = KGRelationConsistencyEvaluationPrompt(lang)

    # 获取边的局部上下文 — kg_rel_triple_consistency_eval.py:100-129
    def _get_local_context(self, G, u, v, limit=5):
        context_facts = []
        # subject 的邻居
        for n in G.neighbors(u):
            if n == v:
                continue
            if G.has_edge(u, n):
                data = G.get_edge_data(u, n)
                rel = data.get("relation", "related_to")
                context_facts.append(f"- {u} {rel} {n}")
                if len(context_facts) >= limit:
                    break
        # object 的邻居
        for n in G.neighbors(v):
            if n == u:
                continue
            if G.has_edge(v, n):
                data = G.get_edge_data(v, n)
                rel = data.get("relation", "related_to")
                context_facts.append(f"- {v} {rel} {n}")
                if len(context_facts) >= limit * 2:
                    break
        if not context_facts:
            return "No specific context available (Isolated Edge)."
        return "\n".join(context_facts)

    # LLM 一致性判断 — kg_rel_triple_consistency_eval.py:148-187
    def _check_consistency(self, context_desc, subject, object_entity, relation):
        if context_desc == "No specific context available (Isolated Edge).":
            return 0
        system_prompt = self.prompt_manager.build_system_prompt()
        user_prompt = self.prompt_manager.build_prompt(
            context_desc=context_desc, subj=subject,
            obj=object_entity, relation=relation)
        responses = self.llm_serving.generate_from_input(
            user_inputs=[user_prompt], system_prompt=system_prompt)
        res_json = self._safe_parse_json(responses[0])
        judgment = res_json.get("judgment", "").upper()
        if judgment == "CONSISTENT":
            return 1
        elif judgment == "INCONSISTENT":
            return 0
        return 0
```

#### 其他评估算子一览

| 算子 | 源码文件 | 评估维度 |
|------|---------|---------|
| `KGRelationTripleConsistencyEvaluator` | `kg_rel_triple_consistency_eval.py` | 三元组逻辑一致性 |
| `KGQACorrelationEvaluator` | `kg_qa_correlation_eval.py` | QA 对相关性 |
| `KGRelationTripleStrengthEvaluator` | `kg_rel_triple_strength_eval.py` | 三元组强度 |
| `KGRelationTripleTopologyEvaluator` | `kg_rel_triple_topology_eval.py` | 拓扑结构 |
| `KGSubgraphConnectivityEvaluator` | `kg_subgraph_connectivity_eval.py` | 子图连通性 |
| `KGSubgraphConsistenceEvaluator` | `kg_subgraph_consistence_eval.py` | 子图一致性 |
| `KGSubgraphScaleEvaluator` | `kg_subgraph_scale_eval.py` | 子图规模 |

### 1.9 Pipeline 编排模式

DataFlow-KG 的 Pipeline 模式核心是 **`storage.step()` 串联**：

```python
from dataflow.utils.storage import FileStorage
from dataflow.serving import APILLMServing_request

# 1. 初始化存储和 LLM
storage = FileStorage(
    first_entry_file_name="srs_input.json",
    cache_path="./srs_kg_output",
    cache_type="json",
)
llm = APILLMServing_request(
    api_url="https://your-api/v1/chat/completions",
    model_name="gpt-4o", max_workers=8,
)

# 2. 串联算子（每步 .step() 推进存储版本）
KGTripleExtraction(llm_serving=llm, triple_type="relation", lang="zh").run(
    storage=storage.step(), input_key="raw_chunk",
    input_key_meta="entity", output_key="triple")

KGReasoningPathSearch(max_hop=5).run(
    storage=storage.step(), input_key="triple", output_key="mpath")

KGGraphRAGSubgraphRetrieval(hop=2).run(
    storage=storage.step(), output_key="subgraph_prompt")
```

---

## Part 2: DataMind

### 2.1 双层架构概览

DataMind 包含**两层架构**：

| 层 | 路径 | 特点 |
|----|------|------|
| **modules/** 层 | `modules/graphrag/`, `modules/database/`, `modules/memory/`, `modules/rag/` | 基于 LlamaIndex，简单直接，`main.py` 入口 |
| **datamind/** 层 | `datamind/capabilities/graph/`, `datamind/capabilities/db/`, ... | 协议驱动（Protocol + Registry + Provider），Anthropic SDK 原生，支持多后端 |

`modules/` 层是早期版本，基于 LlamaIndex 封装；`datamind/capabilities/` 层是重构后的 v0.3 版本，采用 Protocol + Provider 模式，所有工具以 `ToolSpec`（Anthropic tool_use 格式）暴露给 Agent。

本文重点提取 `datamind/capabilities/` 层的代码（功能更完整、API 更清晰），同时给出 `modules/` 层的对应关系。

### 2.2 安装与启动

#### modules/ 层（LlamaIndex 版）

> 源码：`main.py:1-80`

```bash
# 安装依赖
pip install -r requirements.txt

# 配置
cp .env.example .env
# 编辑 .env:
#   LLM_API_BASE=https://api.deepseek.com/v1
#   LLM_MODEL=deepseek-chat
#   LLM_API_KEY=sk-xxx

# 启动
python main.py
```

#### datamind/ 层（v0.3 协议版）

> 源码：`datamind/config.py:230-251`

配置使用嵌套 pydantic-settings，环境变量前缀 `DATAMIND__`，分隔符 `__`：

```bash
# .env.datamind
DATAMIND__LLM__API_BASE=http://35.220.164.252:3888
DATAMIND__LLM__API_KEY=sk-xxx
DATAMIND__LLM__MODEL=claude-sonnet-4-6
DATAMIND__LLM__FALLBACK_MODEL=claude-haiku-4-5-20251001

DATAMIND__EMBEDDING__PROVIDER=openai
DATAMIND__EMBEDDING__MODEL=text-embedding-3-small

DATAMIND__GRAPH__BACKEND=networkx
DATAMIND__DB__DIALECT=sqlite
DATAMIND__MEMORY__BACKEND=sqlite
DATAMIND__RETRIEVAL__STRATEGY=hybrid

DATAMIND__DATA__PROFILE=default
DATAMIND__AGENT__BACKEND=native
DATAMIND__AGENT__MAX_TURNS=12
```

#### 配置体系完整定义

> 源码：`datamind/config.py:38-273`

```python
class LLMConfig(BaseModel):
    api_base: AnyUrl = Field(default=AnyUrl("http://35.220.164.252:3888"))
    api_key: SecretStr
    model: str = "claude-sonnet-4-6"
    fallback_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 4096
    temperature: float = 1.0
    timeout_s: float = 60.0

class EmbeddingConfig(BaseModel):
    provider: str = "openai"       # key into embedding_registry
    api_base: AnyUrl | None = None
    api_key: SecretStr | None = None
    model: str = "text-embedding-3-small"
    dimension: int | None = None
    batch_size: int = 32

class RetrievalConfig(BaseModel):
    strategy: str = "simple"       # simple | multi_query | hybrid
    top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 64
    rerank: bool = False
    rerank_model: str | None = None

class GraphConfig(BaseModel):
    backend: str = "networkx"      # networkx | neo4j | ...
    dsn: str | None = None         # bolt://user:pw@host:7687
    embed_entities: bool = False

class DBConfig(BaseModel):
    dialect: str = "sqlite"        # sqlite | mysql | postgres | ...
    dsn: str | None = None         # mysql+pymysql://user:pw@host/db
    read_only: bool = True
    row_limit: int = 1000
    query_timeout_s: float = 10.0

class MemoryConfig(BaseModel):
    backend: str = "sqlite"        # sqlite | redis | postgres | ...
    dsn: str | None = None
    short_term_turns: int = 20
    long_term_enabled: bool = True

class DataConfig(BaseModel):
    profile: str = "default"
    base_dir: Path = _REPO_ROOT
    # data_dir = base_dir/data/profiles/<profile>/
    # storage_dir = base_dir/storage/<profile>/

class AgentConfig(BaseModel):
    backend: Literal["native", "sdk"] = "native"
    max_turns: int = 12
```

### 2.3 协议层定义

> 源码：`datamind/core/protocols.py:1-300`

所有能力的接口契约定义在此文件中。

#### GraphStore 协议

```python
# protocols.py:195-215
@runtime_checkable
class GraphStore(Protocol):
    """Knowledge graph backend (NetworkX / Neo4j / ArangoDB / ...)."""

    async def upsert_triples(self, triples: Sequence[GraphTriple]) -> None: ...

    async def search_entities(self, query: str, *, top_k: int = 5) -> list[Entity]: ...

    async def traverse(
        self, start: str, *,
        max_hops: int = 2,
        relation_filter: list[str] | None = None,
    ) -> list[GraphPath]: ...

    async def neighbors(
        self, entity: str, *,
        direction: str = "both",
    ) -> list[Edge]: ...
```

#### 数据传输对象（DTO）

```python
# protocols.py:33-64
class GraphTriple(BaseModel):
    subject: str
    relation: str
    object: str
    subject_type: str = "entity"
    object_type: str = "entity"
    confidence: float = 1.0
    source: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)

class Entity(BaseModel):
    id: str
    label: str
    type: str = "entity"
    score: float = 0.0
    properties: dict[str, Any] = Field(default_factory=dict)

class Edge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)

class GraphPath(BaseModel):
    nodes: list[str]
    edges: list[Edge]
    score: float = 0.0
```

#### DatabaseDialect 协议

```python
# protocols.py:218-248
@runtime_checkable
class DatabaseDialect(Protocol):
    name: str

    def build_engine(self, dsn: str, **kwargs: Any) -> Any: ...

    async def list_tables(self, engine: Any) -> list[str]: ...

    async def describe(self, engine: Any, table: str) -> TableSchema: ...

    async def execute_readonly(
        self, engine: Any, sql: str, *,
        row_limit: int = 1000, timeout_s: float = 10.0,
    ) -> QueryResult: ...

    def is_destructive(self, sql: str) -> bool: ...
```

#### MemoryStore 协议

```python
# protocols.py:251-300
@runtime_checkable
class MemoryStore(Protocol):
    """三作用域记忆存储: global / profile / session"""

    async def save(
        self, content: str, *,
        scope: Literal["global", "profile", "session"] = "profile",
        profile: str | None = None,
        session_id: str | None = None,
        kind: Literal["preference", "decision", "workflow", "summary", "skill", "fact"] = "fact",
        metadata: dict[str, Any] | None = None,
    ) -> str: ...

    async def recall(
        self, query: str, *,
        profile: str | None = None,
        session_id: str | None = None,
        top_k: int = 8,
        kinds: Sequence[str] | None = None,
        include_archived: bool = False,
    ) -> list[MemoryItem]: ...

    async def forget(self, item_id: str, *, hard: bool = False) -> bool: ...

    async def list_profiles(self) -> list[str]: ...
```

#### MemoryItem DTO

```python
# protocols.py:86-111
class MemoryItem(BaseModel):
    id: str
    scope: Literal["global", "profile", "session"] = "profile"
    profile: str | None = None
    session_id: str | None = None
    kind: Literal["preference", "decision", "workflow", "summary", "skill", "fact"] = "fact"
    status: Literal["active", "archived"] = "active"
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
```

### 2.4 Graph 工具完整 API

#### GraphService — 图谱服务层

> 源码：`datamind/capabilities/graph/service.py:19-125`

```python
class GraphService:
    def __init__(self, *, store: GraphStore, data_dir: Path, storage_dir: Path):
        self.store = store
        self.data_dir = data_dir
        self.storage_dir = storage_dir

    async def load_from_profile(self) -> dict[str, int]:
        """从 data_dir/triplets/*.jsonl 加载三元组到图存储。"""
        triplets_dir = self.data_dir / "triplets"
        count = 0
        batch: list[GraphTriple] = []
        if triplets_dir.is_dir():
            for jsonl in sorted(triplets_dir.glob("*.jsonl")):
                with jsonl.open("r", encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        line = line.strip()
                        if not line:
                            continue
                        obj = json.loads(line)
                        batch.append(GraphTriple(**obj))
                        count += 1
                        if len(batch) >= 500:
                            await self.store.upsert_triples(batch)
                            batch = []
        if batch:
            await self.store.upsert_triples(batch)
        await self.store.persist()
        return {"triples_loaded": count}

    async def search_entities(self, query: str, *, top_k: int = 5) -> list[dict]:
        return [e.model_dump() for e in await self.store.search_entities(query, top_k=top_k)]

    async def traverse(self, start: str, *, max_hops: int = 2,
                       relation_filter: list[str] | None = None) -> list[dict]:
        paths = await self.store.traverse(start, max_hops=max_hops,
                                          relation_filter=relation_filter)
        return [p.model_dump() for p in paths]

    async def neighbors(self, entity: str, *, direction: str = "both") -> list[dict]:
        edges = await self.store.neighbors(entity, direction=direction)
        return [e.model_dump() for e in edges]

    async def upsert(self, triples: list[dict]) -> dict[str, int]:
        parsed = [GraphTriple(**t) for t in triples]
        await self.store.upsert_triples(parsed)
        await self.store.persist()
        return {"upserted": len(parsed)}
```

#### GraphService 工厂函数

```python
# service.py:106-122
def build_graph_service(settings: Settings) -> GraphService:
    storage_dir = settings.data.storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    backend = settings.graph.backend
    if backend == "networkx":
        store = graph_registry.create(
            "networkx",
            persist_path=str(storage_dir / "graph.json"),
        )
    else:
        store = graph_registry.create(backend, dsn=settings.graph.dsn)
    return GraphService(store=store, data_dir=settings.data.data_dir,
                        storage_dir=storage_dir)
```

#### 4 个 Graph 工具（Agent 可调用）

> 源码：`datamind/capabilities/graph/tools.py:11-137`

```python
def build_graph_tools(graph: GraphService) -> list[ToolSpec]:

    async def _search(query: str, top_k: int = 5) -> dict:
        entities = await graph.search_entities(query, top_k=top_k)
        return {"query": query, "count": len(entities), "entities": entities}

    async def _traverse(start: str, max_hops: int = 2,
                        relation_filter: list[str] | None = None) -> dict:
        paths = await graph.traverse(start, max_hops=max_hops,
                                     relation_filter=relation_filter)
        return {"start": start, "max_hops": max_hops, "count": len(paths), "paths": paths}

    async def _neighbors(entity: str, direction: str = "both") -> dict:
        edges = await graph.neighbors(entity, direction=direction)
        return {"entity": entity, "direction": direction,
                "count": len(edges), "edges": edges}

    async def _upsert(triples: list[dict]) -> dict:
        return await graph.upsert(triples)

    return [
        ToolSpec(
            name="graph_search_entities",
            description="Find entities in the knowledge graph by name or alias.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                },
                "required": ["query"],
            },
            handler=_search,
        ),
        ToolSpec(
            name="graph_traverse",
            description="Walk the knowledge graph from a starting entity, up to N hops.",
            input_schema={
                "type": "object",
                "properties": {
                    "start": {"type": "string"},
                    "max_hops": {"type": "integer", "minimum": 1, "maximum": 5, "default": 2},
                    "relation_filter": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["start"],
            },
            handler=_traverse,
        ),
        ToolSpec(
            name="graph_neighbors",
            description="Return every edge incident to an entity.",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string"},
                    "direction": {"type": "string",
                                  "enum": ["out", "in", "both"], "default": "both"},
                },
                "required": ["entity"],
            },
            handler=_neighbors,
        ),
        ToolSpec(
            name="graph_upsert_triples",
            description="Add or update (subject, relation, object) triples in the graph.",
            input_schema={
                "type": "object",
                "properties": {
                    "triples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "subject": {"type": "string"},
                                "relation": {"type": "string"},
                                "object": {"type": "string"},
                                "subject_type": {"type": "string", "default": "entity"},
                                "object_type": {"type": "string", "default": "entity"},
                                "confidence": {"type": "number", "default": 1.0},
                                "source": {"type": ["string", "null"]},
                            },
                            "required": ["subject", "relation", "object"],
                        },
                    },
                },
                "required": ["triples"],
            },
            handler=_upsert,
            metadata={"group": "graph", "destructive": True},
        ),
    ]
```

### 2.5 NetworkX 图存储实现

> 源码：`datamind/capabilities/graph/providers/networkx_store.py:30-262`

这是 `GraphStore` 协议的默认实现，使用 NetworkX `MultiDiGraph`，持久化为 JSON 文件。

#### 持久化格式

```json
// storage/<profile>/graph.json
{
  "nodes": [
    {"id": "电池系统", "label": "电池系统", "type": "component", "props": {}}
  ],
  "edges": [
    {"src": "电池系统", "dst": "12V", "rel": "额定电压", "w": 1.0, "props": {}}
  ]
}
```

#### 完整实现

```python
@graph_registry.register("networkx")
class NetworkXGraphStore:
    """DiGraph that persists to a single JSON file per profile."""

    def __init__(self, *, persist_path: str | Path, autoload: bool = True):
        self._path = Path(persist_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()
        self._dirty = False
        if autoload and self._path.exists():
            self._load()

    # ---- 写入三元组 ----
    # networkx_store.py:117-139
    async def upsert_triples(self, triples: Sequence[GraphTriple]) -> None:
        for t in triples:
            for side, node_id, node_type in (
                ("subject", t.subject, t.subject_type),
                ("object", t.object, t.object_type),
            ):
                if not self._g.has_node(node_id):
                    self._g.add_node(node_id, label=node_id, type=node_type)
            self._g.add_edge(
                t.subject, t.object,
                key=t.relation,
                relation=t.relation,
                weight=float(t.confidence),
                **{f"p_{k}": v for k, v in (t.properties or {}).items()},
            )
        self._dirty = True

    # ---- 实体搜索（精确 > 子串 > 模糊） ----
    # networkx_store.py:147-177
    async def search_entities(self, query: str, *, top_k: int = 5) -> list[Entity]:
        q = query.lower().strip()
        if not q:
            return []
        scored: list[tuple[float, str, dict]] = []
        for nid, data in self._g.nodes(data=True):
            label = str(data.get("label", nid))
            if nid.lower() == q or label.lower() == q:
                score = 1.0                          # 精确匹配
            elif q in nid.lower() or q in label.lower():
                score = 0.7                          # 子串匹配
            else:
                ratio = difflib.SequenceMatcher(None, q, label.lower()).ratio()
                if ratio < 0.4:
                    continue
                score = 0.4 + 0.4 * ratio            # 模糊匹配
            scored.append((score, nid, data))
        scored.sort(key=lambda x: -x[0])
        return [Entity(id=nid, label=str(data.get("label", nid)),
                       type=str(data.get("type", "entity")), score=score,
                       properties={k: v for k, v in data.items() if k not in {"label", "type"}})
                for score, nid, data in scored[:top_k]]

    # ---- 邻居查询 ----
    # networkx_store.py:179-194
    async def neighbors(self, entity: str, *, direction: str = "both") -> list[Edge]:
        if not self._g.has_node(entity):
            return []
        edges: list[Edge] = []
        if direction in {"out", "both"}:
            for u, v, d in self._g.out_edges(entity, data=True):
                edges.append(self._edge(u, v, d))
        if direction in {"in", "both"}:
            for u, v, d in self._g.in_edges(entity, data=True):
                edges.append(self._edge(u, v, d))
        return edges

    # ---- BFS 多跳遍历 ----
    # networkx_store.py:196-240
    async def traverse(self, start: str, *, max_hops: int = 2,
                       relation_filter: list[str] | None = None) -> list[GraphPath]:
        if not self._g.has_node(start):
            return []
        allowed = set(relation_filter) if relation_filter else None
        paths: list[GraphPath] = []
        visited: set[tuple[str, ...]] = set()
        frontier: list[tuple[str, list[Edge], set[str]]] = [(start, [], {start})]
        depth = 0
        while frontier and depth < max_hops:
            next_frontier = []
            for node, edges_so_far, seen in frontier:
                for u, v, d in self._g.out_edges(node, data=True):
                    rel = d.get("relation", "related")
                    if allowed is not None and rel not in allowed:
                        continue
                    if v in seen:
                        continue
                    edge_obj = self._edge(u, v, d)
                    path_edges = edges_so_far + [edge_obj]
                    nodes = [start] + [e.target for e in path_edges]
                    key = tuple(nodes)
                    if key in visited:
                        continue
                    visited.add(key)
                    paths.append(GraphPath(
                        nodes=nodes, edges=path_edges,
                        score=sum(e.weight for e in path_edges) / len(path_edges)))
                    next_frontier.append((v, path_edges, seen | {v}))
            frontier = next_frontier
            depth += 1
        paths.sort(key=lambda p: -p.score)  # 权重最高的路径优先
        return paths

    # ---- 持久化 ----
    # networkx_store.py:79-113
    async def persist(self) -> None:
        if not self._dirty:
            return
        def _run():
            doc = {
                "nodes": [{"id": nid, "label": d.get("label", nid),
                            "type": d.get("type", "entity"),
                            "props": {k: v for k, v in d.items() if k not in {"label", "type"}}}
                          for nid, d in self._g.nodes(data=True)],
                "edges": [{"src": u, "dst": v, "rel": d.get("relation", "related"),
                            "w": float(d.get("weight", 1.0)),
                            "props": {k: val for k, val in d.items()
                                      if k not in {"relation", "weight"}}}
                          for u, v, d in self._g.edges(data=True)],
            }
            self._path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        await asyncio.to_thread(_run)
        self._dirty = False

    def stats(self) -> dict[str, int]:
        return {"nodes": self._g.number_of_nodes(), "edges": self._g.number_of_edges()}
```

### 2.6 NL2SQL 完整 API

#### DBService — 数据库服务层

> 源码：`datamind/capabilities/db/service.py:28-129`

```python
class DBService:
    def __init__(self, *, dialect: DatabaseDialect, engine: Engine,
                 db_cfg: DBConfig, llm_client=None, llm_model=None):
        self.dialect = dialect
        self.engine = engine
        self.db_cfg = db_cfg
        self._llm = llm_client
        self._model = llm_model

    async def list_tables(self) -> list[str]:
        return await self.dialect.list_tables(self.engine)

    async def describe(self, table: str) -> TableSchema:
        return await self.dialect.describe(self.engine, table)

    async def describe_all(self) -> list[TableSchema]:
        names = await self.list_tables()
        return [await self.describe(t) for t in names]

    async def query_sql(self, sql: str) -> QueryResult:
        return await self.dialect.execute_readonly(
            self.engine, sql,
            row_limit=self.db_cfg.row_limit,
            timeout_s=self.db_cfg.query_timeout_s)

    async def query_nl(self, question: str, *, tables: list[str] | None = None) -> dict:
        """NL -> SQL -> result. Returns {sql, result, columns, rows}."""
        schemas = await self.describe_all()
        if tables:
            wanted = set(tables)
            schemas = [s for s in schemas if s.name in wanted]
        sql = await generate_sql(
            client=self._llm, model=self._model,
            question=question, schemas=schemas,
            dialect_name=self.dialect.name)
        result = await self.query_sql(sql)
        return {"question": question, "sql": sql,
                "columns": result.columns, "rows": result.rows,
                "truncated": result.truncated, "elapsed_ms": result.elapsed_ms}
```

#### NL2SQL 生成器

> 源码：`datamind/capabilities/db/nl2sql.py:51-85`

```python
async def generate_sql(*, client: AsyncAnthropic, model: str,
                       question: str, schemas: Sequence[TableSchema],
                       dialect_name: str = "sql") -> str:
    """Return a single SELECT statement answering `question`."""
    schema_text = _schema_block(schemas)
    prompt = (
        "You are an expert SQL author. Convert the user's question into ONE "
        f"read-only SQL SELECT statement for a {dialect_name} database.\n\n"
        "Rules:\n"
        "- Output ONLY the SQL statement — no commentary, no markdown fences.\n"
        "- Never write INSERT/UPDATE/DELETE/DDL.\n"
        "- Use columns that exist in the schema below.\n"
        "- Prefer explicit column names over SELECT *.\n"
        "- Limit to the data necessary to answer.\n\n"
        f"Schema:\n{schema_text}\n\n"
        f"Question: {question}\n\n"
        "SQL:"
    )
    resp = await client.messages.create(
        model=model, max_tokens=512,
        messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    sql = _extract_sql(text)
    return sql

# schema 描述构建 — nl2sql.py:32-41
def _schema_block(schemas: Sequence[TableSchema]) -> str:
    lines: list[str] = []
    for t in schemas:
        cols = ", ".join(
            f"{c.name} {c.type}{' PK' if c.primary_key else ''}"
            f"{' NOT NULL' if not c.nullable else ''}"
            for c in t.columns)
        cnt = f" (~{t.row_count_estimate} rows)" if t.row_count_estimate is not None else ""
        lines.append(f"TABLE {t.name}{cnt}:\n  {cols}")
    return "\n\n".join(lines)
```

#### SQL 安全防护

> 源码：`datamind/capabilities/db/safeguard.py:16-93`

```python
_DESTRUCTIVE_VERBS = frozenset({
    "INSERT", "UPDATE", "DELETE", "REPLACE",
    "DROP", "CREATE", "ALTER", "TRUNCATE", "RENAME",
    "GRANT", "REVOKE", "ATTACH", "DETACH",
    "CALL", "EXEC", "EXECUTE",
    "BEGIN", "COMMIT", "ROLLBACK", "SAVEPOINT", "RELEASE",
    "LOAD", "COPY", "KILL", "LOCK", "UNLOCK", "PRAGMA",
})

def is_destructive_sql(sql: str) -> bool:
    """True if sql would modify data / schema / session state."""
    verb = leading_verb(sql)
    if verb in _DESTRUCTIVE_VERBS:
        return True
    cleaned = strip_comments(sql).lower()
    if re.search(r"\binto\s+(outfile|dumpfile|temp(orary)?\s+table|table)\b", cleaned):
        return True
    return False

def contains_multiple_statements(sql: str) -> bool:
    """Reject payloads that try to chain SELECT ...; DELETE ..."""
    cleaned = strip_comments(sql)
    masked = re.sub(r"'(?:''|[^'])*'", "''", cleaned)
    masked = re.sub(r'"(?:""|[^"])*"', '""', masked)
    masked = masked.strip().rstrip(";")
    return bool(_STATEMENT_SEP_RE.search(masked))

def ensure_row_limit(sql: str, row_limit: int) -> str:
    """Wrap sql so its result can never exceed row_limit rows."""
    cleaned = strip_comments(sql).strip().rstrip(";")
    return f"SELECT * FROM ( {cleaned} ) AS _dm_safe LIMIT {int(row_limit)}"
```

#### 4 个 DB 工具（Agent 可调用）

> 源码：`datamind/capabilities/db/tools.py:11-100`

```python
def build_db_tools(db: DBService) -> list[ToolSpec]:

    async def _list_tables() -> dict:
        return {"tables": await db.list_tables()}

    async def _describe(table: str) -> dict:
        schema = await db.describe(table)
        return schema.model_dump()

    async def _query_sql(sql: str) -> dict:
        result = await db.query_sql(sql)
        return result.model_dump()

    async def _query_nl(question: str, tables: list[str] | None = None) -> dict:
        return await db.query_nl(question, tables=tables)

    return [
        ToolSpec(name="db_list_tables", ...,
            input_schema={"type": "object", "properties": {}},
            handler=_list_tables),
        ToolSpec(name="db_describe_table", ...,
            input_schema={"type": "object", "properties": {"table": {"type": "string"}},
                          "required": ["table"]},
            handler=_describe),
        ToolSpec(name="db_query_sql", ...,
            input_schema={"type": "object", "properties": {"sql": {"type": "string"}},
                          "required": ["sql"]},
            handler=_query_sql),
        ToolSpec(name="db_query_nl", ...,
            input_schema={"type": "object",
                "properties": {"question": {"type": "string"},
                               "tables": {"type": "array", "items": {"type": "string"}}},
                "required": ["question"]},
            handler=_query_nl),
    ]
```

### 2.7 Memory 完整 API

#### MemoryService — 记忆服务层

> 源码：`datamind/capabilities/memory/service.py:37-196`

```python
class MemoryService:
    """统一短期+长期记忆; 长期记忆按 scope 分区。"""

    def __init__(self, *, short_term: ShortTermMemory, long_term: MemoryStore,
                 default_profile: str | None = None,
                 llm_client=None, llm_model=None):
        self.short_term = short_term
        self.long_term = long_term
        self._default_profile = default_profile
        self._llm = llm_client
        self._model = llm_model

    # ---- 长期记忆 ----
    async def save(self, content: str, *,
                   scope: Scope = "profile",
                   profile: str | None = None,
                   session_id: str | None = None,
                   kind: Kind = "fact",
                   metadata: dict | None = None) -> str:
        return await self.long_term.save(
            content, scope=scope,
            profile=profile or (self._default_profile if scope == "profile" else None),
            session_id=session_id, kind=kind, metadata=metadata)

    async def recall(self, query: str, *,
                     profile: str | None = None,
                     session_id: str | None = None,
                     top_k: int = 8,
                     kinds: Sequence[str] | None = None,
                     include_archived: bool = False) -> list[dict]:
        hits = await self.long_term.recall(
            query, profile=profile or self._default_profile,
            session_id=session_id, top_k=top_k, kinds=kinds,
            include_archived=include_archived)
        return [h.model_dump() for h in hits]

    async def forget(self, item_id: str, *, hard: bool = False) -> bool:
        return await self.long_term.forget(item_id, hard=hard)

    async def list_profiles(self) -> list[str]:
        return await self.long_term.list_profiles()

    # ---- 事实自动抽取 ----
    async def extract_and_save(self, *, user_turn: str, assistant_turn: str,
                               scope: Scope = "session", **kwargs) -> list[str]:
        if not self._llm or not self._model:
            return []
        facts = await extract_facts(
            client=self._llm, model=self._model,
            user_turn=user_turn, assistant_turn=assistant_turn)
        for f in facts:
            await self.save(f, scope=scope, kind="fact",
                            metadata={"_source": "auto_extracted"})
        return facts
```

#### SQLite 记忆存储 — 三作用域余弦召回

> 源码：`datamind/capabilities/memory/providers/sqlite_store.py:104-495`

```python
@memory_registry.register("sqlite")
class SQLiteMemoryStore:
    """Embedding-aware, scope-typed memory store in a single SQLite file."""

    # 表结构
    # sqlite_store.py:135-168
    """
    CREATE TABLE memory_v2 (
        id          TEXT PRIMARY KEY,
        scope       TEXT NOT NULL CHECK(scope IN ('global','profile','session')),
        profile     TEXT,
        session_id  TEXT,
        kind        TEXT NOT NULL DEFAULT 'fact',
        status      TEXT NOT NULL DEFAULT 'active',
        content     TEXT NOT NULL,
        metadata    TEXT,                   -- JSON
        embedding   BLOB,                   -- float32 packed
        created_at  REAL NOT NULL,
        updated_at  REAL NOT NULL,
        archived_at REAL
    );
    CREATE INDEX idx_mem2_scope_profile ON memory_v2(scope, profile) WHERE status='active';
    CREATE INDEX idx_mem2_scope_session ON memory_v2(scope, session_id) WHERE status='active';
    CREATE INDEX idx_mem2_scope_global  ON memory_v2(scope) WHERE status='active' AND scope='global';
    """

    # save — sqlite_store.py:231-277
    async def save(self, content, *, scope="profile", profile=None, session_id=None,
                   kind="fact", metadata=None) -> str:
        if scope == "profile" and not profile:
            raise CapabilityError("memory", "scope='profile' requires profile= argument")
        if scope == "session" and not session_id:
            raise CapabilityError("memory", "scope='session' requires session_id= argument")
        item_id = uuid.uuid4().hex
        ts = time.time()
        meta_json = json.dumps(metadata or {}, ensure_ascii=False)
        emb = None
        if self._embedding is not None and content.strip():
            vec = await self._embedding.embed_query(content)
            emb = _pack(vec)  # struct.pack(f"{len(vec)}f", *vec)
        # INSERT INTO memory_v2 ...
        return item_id

    # recall — 三作用域联合召回 — sqlite_store.py:281-361
    async def recall(self, query, *, profile=None, session_id=None, top_k=8,
                     kinds=None, include_archived=False, per_scope=None) -> list[MemoryItem]:
        # 默认每作用域预算: session=2 + profile=4 + global=2 = 8
        budgets = {"session": 2, "profile": 4, "global": 2}
        if per_scope:
            budgets.update(per_scope)

        scoring = self._score_with_embedding if self._embedding else self._score_lexical
        qv = await self._embedding.embed_query(query) if self._embedding else None

        merged = []
        seen = set()

        # session scope
        if session_id and budgets["session"] > 0:
            for item in await self._slice("session", "scope='session' AND session_id=?",
                                          [session_id], budgets["session"]):
                if item.id not in seen:
                    seen.add(item.id); merged.append(item)
        # profile scope
        if profile and budgets["profile"] > 0:
            for item in await self._slice("profile", "scope='profile' AND profile=?",
                                          [profile], budgets["profile"]):
                if item.id not in seen:
                    seen.add(item.id); merged.append(item)
        # global scope
        if budgets["global"] > 0:
            for item in await self._slice("global", "scope='global'", [], budgets["global"]):
                if item.id not in seen:
                    seen.add(item.id); merged.append(item)

        # 按 score 降序排列; 同分时 session > profile > global
        merged.sort(key=lambda m: (-m.score, _scope_priority(m.scope)))
        return merged[:top_k]

    # 余弦相似度 — sqlite_store.py:70-78
    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # forget — sqlite_store.py:365-380
    async def forget(self, item_id: str, *, hard: bool = False) -> bool:
        if hard:
            cur = conn.execute("DELETE FROM memory_v2 WHERE id=?", (item_id,))
        else:
            cur = conn.execute(
                "UPDATE memory_v2 SET status='archived', archived_at=?, updated_at=? "
                "WHERE id=? AND status='active'", (ts, ts, item_id))
        return cur.rowcount > 0
```

#### 事实抽取器

> 源码：`datamind/capabilities/memory/extractor.py:47-82`

```python
async def extract_facts(*, client: AsyncAnthropic, model: str,
                        user_turn: str, assistant_turn: str,
                        max_facts: int = 6) -> list[str]:
    prompt = """You extract durable facts worth remembering from a conversation turn.
    Return a JSON array of strings. Each string is ONE self-contained statement...
    Skip: greetings, apologies, filler, questions the user asked...
    If there is nothing worth saving, return [].
    User: {user}
    Assistant: {assistant}
    JSON:"""
    resp = await client.messages.create(
        model=model, max_tokens=400,
        messages=[{"role": "user", "content": prompt.format(
            user=user_turn, assistant=assistant_turn)}])
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()
    m = _JSON_RE.search(text)
    parsed = json.loads(m.group(0) if m else text)
    return [item.strip() for item in parsed if isinstance(item, str) and item.strip()][:max_facts]
```

#### 4 个 Memory 工具（Agent 可调用）

> 源码：`datamind/capabilities/memory/tools.py:21-180`

```python
def build_memory_tools(memory: MemoryService, *, request_context=None) -> list[ToolSpec]:

    async def _save(content: str, scope: str = "profile", kind: str = "fact",
                    profile: str | None = None, session_id: str | None = None,
                    metadata: dict | None = None) -> dict:
        item_id = await memory.save(content, scope=scope,
            profile=profile or ctx_profile, session_id=session_id or ctx_session,
            kind=kind, metadata=metadata)
        return {"id": item_id, "scope": scope, "kind": kind}

    async def _recall(query: str, top_k: int = 8,
                      scope_filter: list[str] | None = None,
                      kinds: list[str] | None = None, **kwargs) -> dict:
        hits = await memory.recall(query, top_k=top_k, kinds=kinds, **kwargs)
        return {"query": query, "count": len(hits), "results": hits}

    async def _forget(item_id: str, hard: bool = False) -> dict:
        ok = await memory.forget(item_id, hard=hard)
        return {"id": item_id, "deleted": ok, "hard": hard}

    async def _list_profiles() -> dict:
        return {"profiles": await memory.list_profiles()}

    return [
        ToolSpec(name="memory_save",
            description="Persist a durable fact/preference/decision to long-term memory. "
                        "scope: 'global' | 'profile' | 'session'",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "scope": {"type": "string", "enum": ["global", "profile", "session"],
                              "default": "profile"},
                    "kind": {"type": "string",
                             "enum": ["preference", "decision", "workflow", "summary", "skill", "fact"],
                             "default": "fact"},
                    "metadata": {"type": "object", "additionalProperties": True},
                },
                "required": ["content"],
            },
            handler=_save),

        ToolSpec(name="memory_recall",
            description="Look up relevant memories by semantic similarity, "
                        "automatically merging session/profile/global scope items.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                    "scope_filter": {"type": "array",
                        "items": {"type": "string", "enum": ["global", "profile", "session"]}},
                    "kinds": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["query"],
            },
            handler=_recall),

        ToolSpec(name="memory_forget",
            description="Soft-delete a memory item by id (status='archived'). "
                        "Pass hard=true to remove the row outright.",
            input_schema={
                "type": "object",
                "properties": {"item_id": {"type": "string"},
                               "hard": {"type": "boolean", "default": False}},
                "required": ["item_id"],
            },
            handler=_forget),

        ToolSpec(name="memory_list_profiles",
            description="List every profile (tenant) that currently has stored memories.",
            input_schema={"type": "object", "properties": {}},
            handler=_list_profiles),
    ]
```

### 2.8 HybridRetriever RRF 融合

> 源码：`datamind/capabilities/kb/providers/hybrid_retriever.py:44-162`

```python
@retriever_registry.register("hybrid")
class HybridRetriever:
    """Vector search + BM25 with Reciprocal Rank Fusion."""

    def __init__(self, *, vector_store: VectorStore, embedding: EmbeddingProvider,
                 rrf_k: int = 60, vector_weight: float = 1.0,
                 bm25_weight: float = 1.0, candidate_multiplier: int = 3):
        self._store = vector_store
        self._embed = embedding
        self._rrf_k = rrf_k          # RRF 平滑常数, 默认 60
        self._vw = vector_weight
        self._bw = bm25_weight
        self._cm = candidate_multiplier
        self._bm25: BM25Okapi | None = None  # 惰性构建
        self._lock = asyncio.Lock()

    # CJK 感知分词器 — hybrid_retriever.py:25-40
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase + split on non-word runs, keep CJK chars.
        For CJK runs longer than 1, also emit unigrams — helps BM25 on zh."""
        toks = re.findall(r"[\w一-鿿]+", text.lower())
        out: list[str] = []
        for t in toks:
            out.append(t)
            if re.match(r"[一-鿿]{2,}$", t):
                out.extend(list(t))  # 中文按字拆分
        return out

    # RRF 融合检索 — hybrid_retriever.py:94-162
    async def aretrieve(self, query: str, *, top_k: int = 5,
                        filters: dict | None = None) -> list[RetrievedChunk]:
        await self._ensure_lexical()
        k_inner = top_k * self._cm  # 内部召回更多候选

        # 向量检索
        vec = await self._embed.embed_query(query)
        vec_hits = await self._store.query(vec, top_k=k_inner, where=filters)
        vec_ranked = {ch.id: (rank, ch) for rank, ch in enumerate(vec_hits)}

        # BM25 检索
        if self._bm25 is not None and self._ids:
            scores = self._bm25.get_scores(_tokenize(query))
            order = sorted(range(len(scores)), key=lambda i: -scores[i])[:k_inner]
            bm25_ranked = {
                self._ids[i]: (rank, RetrievedChunk(
                    id=self._ids[i], text=self._texts[i],
                    score=float(scores[i]), source=self._metas[i].get("source"),
                    metadata=self._metas[i]))
                for rank, i in enumerate(order) if scores[i] > 0
            }
        else:
            bm25_ranked = {}

        # Reciprocal Rank Fusion: weight / (rrf_k + rank + 1)
        fused: dict[str, tuple[float, RetrievedChunk]] = {}
        for idmap, weight in ((vec_ranked, self._vw), (bm25_ranked, self._bw)):
            for cid, (rank, ch) in idmap.items():
                contrib = weight / (self._rrf_k + rank + 1)
                if cid in fused:
                    prev_score, prev_ch = fused[cid]
                    fused[cid] = (prev_score + contrib, prev_ch)
                else:
                    fused[cid] = (contrib, ch)

        top = sorted(fused.values(), key=lambda sc: -sc[0])[:top_k]
        return [RetrievedChunk(id=ch.id, text=ch.text, score=float(score),
                               source=ch.source, metadata=ch.metadata)
                for score, ch in top]
```

#### KB 工具

> 源码：`datamind/capabilities/kb/tools.py:23-100`

```python
def build_kb_tools(kb: KBService) -> list[ToolSpec]:

    async def _search(query: str, top_k: int = 5, filters: dict | None = None) -> dict:
        chunks = await kb.search(query, top_k=top_k, filters=filters)
        return {"query": query, "top_k": top_k, "results": chunks, "count": len(chunks)}

    return [
        ToolSpec(name="kb_search",
            description="Search the knowledge base (vector RAG).",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5},
                    "filters": {"type": "object", "additionalProperties": True},
                },
                "required": ["query"],
            },
            handler=_search),
        ToolSpec(name="kb_list_documents", ..., handler=_list_documents),
        ToolSpec(name="kb_count", ..., handler=_count),
        ToolSpec(name="kb_reindex", ..., handler=_reindex),
    ]
```

### 2.9 Agent 循环

#### NativeAgentLoop — 工具使用循环

> 源码：`datamind/agent/loop_native.py:51-372`

```python
class NativeAgentLoop:
    """Anthropic SDK 原生工具使用循环。

    协议:
      1. 发送 [history + user_message] + tools=[...] 到 /v1/messages
      2. 如果 stop_reason == "tool_use":
           - 对每个 tool_use block:
               - 运行 PreToolUse hooks (Deny / AskUser / Rewrite / Allow)
               - 调用 ToolRegistry[name].handler(**input)
               - 运行 PostToolUse hooks (audit log)
               - 追加 tool_result block
           - 回到步骤 1
      3. 否则: 输出最终文本, 返回
    """

    def __init__(self, *, client: AsyncAnthropic, tools: ToolRegistry,
                 config: AgentLoopConfig, hooks: HookChain | None = None):
        self._client = client
        self._tools = tools
        self._cfg = config
        self._hooks = hooks

    async def run_turn(self, *, user_message: str,
                       history: list[dict] | None = None) -> dict[str, Any]:
        conv = list(history or [])
        conv.append({"role": "user", "content": user_message})

        for iteration in range(self._cfg.max_tool_turns):
            resp = await self._client.messages.create(
                model=self._cfg.model,
                max_tokens=self._cfg.max_tokens,
                temperature=self._cfg.temperature,
                system=self._cfg.system_prompt or None,
                tools=self._tools.as_anthropic_tools() or None,
                messages=conv)

            assistant_blocks = [self._block_to_dict(b) for b in resp.content]
            conv.append({"role": "assistant", "content": assistant_blocks})

            if resp.stop_reason != "tool_use":
                text = "".join(b["text"] for b in assistant_blocks
                               if b.get("type") == "text")
                return {"answer": text, "history": conv, "iterations": iteration + 1,
                        "stop_reason": resp.stop_reason, "usage": {...}}

            # 分发每个 tool_use block
            tool_results = []
            for b in assistant_blocks:
                if b.get("type") != "tool_use":
                    continue
                result, err, _ = await self._dispatch_tool(b["name"], b["input"])
                tool_results.append(self._tool_result_block(b["id"], result, err))
            conv.append({"role": "user", "content": tool_results})
```

#### AgentLoopConfig

> 源码：`datamind/agent/base.py:52-60`

```python
@dataclass
class AgentLoopConfig:
    model: str
    max_tokens: int = 4096
    temperature: float = 1.0
    system_prompt: str = ""
    max_tool_turns: int = 10  # 硬上限, 防止无限循环
```

#### 工具注册表

> 源码：`datamind/core/tools.py:31-104`

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]       # JSON Schema (Anthropic API 格式)
    handler: ToolHandler               # async callable
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_anthropic_tool(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description,
                "input_schema": self.input_schema}

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def add(self, spec: ToolSpec): ...
    def extend(self, specs: list[ToolSpec]): ...
    def get(self, name: str) -> ToolSpec: ...
    def as_anthropic_tools(self) -> list[dict[str, Any]]:
        return [t.to_anthropic_tool() for t in self._tools.values()]
```

---

## Part 3: SRS 上下文关联检测完整代码

基于上述真实 API，以下是使用 DataFlow-KG + DataMind 进行 SRS 文档上下文关联检测的完整代码。

### 方案架构

```
SRS 文档
  │
  ├─ DataFlow-KG: 三元组抽取 (KGTripleExtraction)
  │     → SRS 知识图谱 (三元组列表)
  │
  ├─ DataMind GraphService: 图谱构建 (graph_upsert_triples)
  │     → NetworkX 图存储 (graph.json)
  │
  ├─ DataMind GraphService: 关联检测
  │     ├─ graph_search_entities → 找实体
  │     ├─ graph_neighbors → 一跳关联
  │     └─ graph_traverse → 多跳关联
  │
  ├─ DataMind DBService: 表格数据查询
  │     └─ db_query_nl → 自然语言查询结构化约束
  │
  ├─ DataMind KBService: 语义检索
  │     └─ kb_search → Hybrid RAG (BM25 + 向量 + RRF)
  │
  ├─ DataMind MemoryService: 关联规则积累
  │     └─ memory_save / memory_recall
  │
  └─ DataFlow-KG: 一致性评估 (KGRelationTripleConsistencyEvaluator)
        → logical_consistency_score
```

### 完整代码

```python
"""
SRS 文档上下文关联检测 — 基于 DataFlow-KG + DataMind 真实 API

依赖:
  pip install dataflow-kg           # DataFlow-KG
  # DataMind 需要从源码安装 (pip install -e dataflow_repos/DataMind/)
  pip install anthropic networkx chromadb rank-bm25 pydantic pydantic-settings

环境变量:
  DF_API_KEY=sk-xxx                 # DataFlow-KG LLM API
  DATAMIND__LLM__API_KEY=sk-xxx     # DataMind LLM API
  DATAMIND__LLM__API_BASE=https://api.anthropic.com
  DATAMIND__LLM__MODEL=claude-sonnet-4-6
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# ============================================================
# Part A: 用 DataFlow-KG 从 SRS 文本抽取三元组
# ============================================================

def extract_srs_triplets_with_dataflow_kg(srs_chunks: list[dict]) -> list[str]:
    """使用 DataFlow-KG 的 KGTripleExtraction 算子从 SRS 文本抽取三元组。

    Args:
        srs_chunks: [{"raw_chunk": "电池系统工作电压为9V-16V...", "entity": ["电池系统", "电压"]}]

    Returns:
        三元组字符串列表, 格式: "<subj> 电池系统 <obj> 9V-16V <rel> 工作电压范围"
    """
    from dataflow.serving import APILLMServing_request
    from dataflow.utils.storage import FileStorage
    from dataflow.operators.general_kg.generate.kg_triple_extractor import KGTripleExtraction
    from dataflow.operators.general_kg.generate.kg_entity_extractor import KGEntityExtraction

    # 1. 初始化 LLM 服务
    llm_serving = APILLMServing_request(
        api_url=os.environ.get("DF_API_URL", "https://api.openai.com/v1/chat/completions"),
        model_name=os.environ.get("DF_MODEL", "gpt-4o"),
        max_workers=8,
        temperature=0.0,
    )

    # 2. 准备输入数据
    input_file = "/tmp/srs_kg_input.json"
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(srs_chunks, f, ensure_ascii=False, indent=2)

    # 3. 初始化存储
    storage = FileStorage(
        first_entry_file_name=input_file,
        cache_path="/tmp/srs_kg_cache",
        file_name_prefix="srs_kg_step",
        cache_type="json",
    )

    # 4. Step 1: 实体抽取 (如果 SRS chunks 没有 entity 字段)
    if not all("entity" in c for c in srs_chunks):
        entity_extractor = KGEntityExtraction(
            llm_serving=llm_serving, lang="zh")
        entity_extractor.run(
            storage=storage.step(),
            input_key="raw_chunk",
            output_key="entity",
        )

    # 5. Step 2: 三元组抽取
    triple_extractor = KGTripleExtraction(
        llm_serving=llm_serving,
        triple_type="relation",  # "relation" 或 "attribute"
        lang="zh",
    )
    triple_extractor.run(
        storage=storage.step(),
        input_key="raw_chunk",
        input_key_meta="entity",
        output_key="triple",
    )

    # 6. 读取结果
    import pandas as pd
    df = storage.read("dataframe")
    all_triples = []
    for triples in df["triple"].tolist():
        if isinstance(triples, list):
            all_triples.extend(triples)

    return all_triples


def parse_dataflow_kg_triple(triple_str: str) -> dict | None:
    """解析 DataFlow-KG 三元组字符串。

    "<subj> 电池系统 <obj> 9V-16V <rel> 工作电压范围"
    -> {"subject": "电池系统", "object": "9V-16V", "relation": "工作电压范围"}
    """
    import re
    pattern = re.compile(r"<subj>\s*(.+?)\s*<obj>\s*(.+?)\s*<rel>\s*(.+?)$")
    m = pattern.search(triple_str)
    if not m:
        return None
    return {
        "subject": m.group(1).strip(),
        "object": m.group(2).strip(),
        "relation": m.group(3).strip(),
    }


# ============================================================
# Part B: 用 DataMind GraphService 构建 SRS 知识图谱
# ============================================================

async def build_srs_knowledge_graph(triples: list[str], profile: str = "srs"):
    """使用 DataMind 的 GraphService 构建知识图谱。

    Args:
        triples: DataFlow-KG 抽取的三元组字符串列表
        profile: 数据 profile 名称

    Returns:
        GraphService 实例
    """
    from datamind.config import Settings, LLMConfig
    from datamind.capabilities.graph.service import build_graph_service
    from datamind.core.protocols import GraphTriple

    # 1. 构建配置 (最小化配置)
    settings = Settings(
        llm=LLMConfig(
            api_base=os.environ["DATAMIND__LLM__API_BASE"],
            api_key=os.environ["DATAMIND__LLM__API_KEY"],
            model=os.environ.get("DATAMIND__LLM__MODEL", "claude-sonnet-4-6"),
        ),
    )
    settings.data.profile = profile
    settings.ensure_dirs()

    # 2. 构建 GraphService
    graph_service = build_graph_service(settings)

    # 3. 将 DataFlow-KG 三元组转换为 DataMind GraphTriple 格式并写入
    graph_triples = []
    for t_str in triples:
        parsed = parse_dataflow_kg_triple(t_str)
        if parsed is None:
            continue
        graph_triples.append(GraphTriple(
            subject=parsed["subject"],
            relation=parsed["relation"],
            object=parsed["object"],
            subject_type="component",
            object_type="value",
            confidence=1.0,
            source="srs_document",
        ))

    # 4. 批量写入图存储 (每批 500 条)
    batch_size = 500
    for i in range(0, len(graph_triples), batch_size):
        batch = graph_triples[i:i + batch_size]
        await graph_service.store.upsert_triples(batch)
    await graph_service.store.persist()

    print(f"[SRS-KG] 构建完成: {graph_service.stats()}")
    return graph_service


# ============================================================
# Part C: 上下文关联检测 — 使用 Graph 工具
# ============================================================

async def detect_context_correlations(graph_service, entity_name: str) -> dict:
    """检测指定实体的上下文关联。

    使用 graph_search_entities + graph_neighbors + graph_traverse

    Args:
        graph_service: GraphService 实例
        entity_name: 实体名称 (如 "电池系统")

    Returns:
        {
            "entity": ...,
            "neighbors": [...],
            "multi_hop_paths": [...],
        }
    """
    # 1. 搜索实体 (获取精确 ID)
    entities = await graph_service.search_entities(entity_name, top_k=5)
    if not entities:
        return {"error": f"Entity '{entity_name}' not found"}
    entity_id = entities[0]["id"]

    # 2. 查询一跳邻居 (直接关联)
    neighbors = await graph_service.neighbors(entity_id, direction="both")

    # 3. 多跳遍历 (间接关联, 最多 3 跳)
    paths = await graph_service.traverse(
        entity_id,
        max_hops=3,
        relation_filter=None,  # 不限制关系类型
    )

    return {
        "entity": entities[0],
        "neighbors": neighbors,
        "multi_hop_paths": paths[:20],  # 取前 20 条路径
        "total_paths": len(paths),
    }


async def detect_cross_section_correlations(graph_service, entities_a: list[str],
                                             entities_b: list[str]) -> list[dict]:
    """检测两组实体之间的跨章节关联。

    使用 graph_traverse 搜索两组实体之间的多跳路径

    Args:
        entities_a: 章节 A 中的实体列表
        entities_b: 章节 B 中的实体列表

    Returns:
        关联路径列表
    """
    correlations = []
    for ea in entities_a:
        # 搜索实体 A
        found_a = await graph_service.search_entities(ea, top_k=1)
        if not found_a:
            continue
        start_id = found_a[0]["id"]

        for eb in entities_b:
            # 搜索实体 B
            found_b = await graph_service.search_entities(eb, top_k=1)
            if not found_b:
                continue
            target_id = found_b[0]["id"]

            # 遍历搜索 A -> B 的路径
            paths = await graph_service.traverse(start_id, max_hops=4)
            # 过滤出到达 B 的路径
            for path in paths:
                if target_id in path["nodes"]:
                    correlations.append({
                        "entity_a": ea,
                        "entity_b": eb,
                        "path": path,
                    })

    return correlations


# ============================================================
# Part D: 用 DBService 查询 SRS 表格约束
# ============================================================

async def query_srs_table_constraints(db_service, question: str) -> dict:
    """使用 NL2SQL 查询 SRS 文档中的结构化约束表格。

    Args:
        db_service: DBService 实例
        question: 自然语言问题, 如 "电池系统的额定电压是多少?"

    Returns:
        {"question": ..., "sql": ..., "columns": [...], "rows": [...]}
    """
    # 自然语言转 SQL 并执行
    result = await db_service.query_nl(question)
    return result


async def setup_srs_database(srs_tables_sql: str, profile: str = "srs"):
    """初始化 SRS 表格数据库。

    Args:
        srs_tables_sql: CREATE TABLE + INSERT 语句的 SQL 文件内容
        profile: 数据 profile

    Returns:
        DBService 实例
    """
    from datamind.config import Settings, LLMConfig, DBConfig
    from datamind.capabilities.db.service import build_db_service
    from anthropic import AsyncAnthropic

    settings = Settings(
        llm=LLMConfig(
            api_base=os.environ["DATAMIND__LLM__API_BASE"],
            api_key=os.environ["DATAMIND__LLM__API_KEY"],
            model=os.environ.get("DATAMIND__LLM__MODEL", "claude-sonnet-4-6"),
        ),
    )
    settings.data.profile = profile
    settings.ensure_dirs()

    # 写入 SQL 文件到 profile 的 tables 目录
    tables_dir = settings.data.data_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    (tables_dir / "srs_constraints.sql").write_text(srs_tables_sql, encoding="utf-8")

    # 构建 DBService
    client = AsyncAnthropic(
        api_key=os.environ["DATAMIND__LLM__API_KEY"],
        base_url=str(settings.llm.api_base))
    db_service = build_db_service(settings, llm_client=client)

    return db_service


# ============================================================
# Part E: 用 KBService 做语义检索 (Hybrid RAG)
# ============================================================

async def setup_srs_kb(profile: str = "srs"):
    """构建 SRS 文档的 Hybrid RAG 知识库。

    Returns:
        KBService 实例 (使用 hybrid 检索策略)
    """
    from datamind.config import Settings, LLMConfig, EmbeddingConfig, RetrievalConfig
    from datamind.capabilities.kb.service import build_kb_service
    from anthropic import AsyncAnthropic

    settings = Settings(
        llm=LLMConfig(
            api_base=os.environ["DATAMIND__LLM__API_BASE"],
            api_key=os.environ["DATAMIND__LLM__API_KEY"],
            model=os.environ.get("DATAMIND__LLM__MODEL", "claude-sonnet-4-6"),
        ),
        retrieval=RetrievalConfig(strategy="hybrid", top_k=5),
    )
    settings.data.profile = profile
    settings.ensure_dirs()

    client = AsyncAnthropic(
        api_key=os.environ["DATAMIND__LLM__API_KEY"],
        base_url=str(settings.llm.api_base))

    kb_service = build_kb_service(settings, llm_client=client)
    return kb_service


async def semantic_search_srs(kb_service, query: str) -> list[dict]:
    """使用 Hybrid RAG (BM25 + 向量 + RRF) 语义检索 SRS 文档。

    Args:
        query: 查询, 如 "电池系统过压保护机制"

    Returns:
        检索到的文档片段列表
    """
    chunks = await kb_service.search(query, top_k=5)
    return chunks


# ============================================================
# Part F: 用 MemoryService 积累关联检测规则
# ============================================================

async def setup_srs_memory(profile: str = "srs"):
    """初始化 SRS 关联检测的记忆服务。"""
    from datamind.config import Settings, LLMConfig
    from datamind.capabilities.memory.service import build_memory_service
    from anthropic import AsyncAnthropic

    settings = Settings(
        llm=LLMConfig(
            api_base=os.environ["DATAMIND__LLM__API_BASE"],
            api_key=os.environ["DATAMIND__LLM__API_KEY"],
            model=os.environ.get("DATAMIND__LLM__MODEL", "claude-sonnet-4-6"),
        ),
    )
    settings.data.profile = profile
    settings.ensure_dirs()

    client = AsyncAnthropic(
        api_key=os.environ["DATAMIND__LLM__API_KEY"],
        base_url=str(settings.llm.api_base))

    memory_service = build_memory_service(settings, llm_client=client)
    return memory_service


async def save_correlation_rule(memory_service, rule: str, profile: str = "srs"):
    """保存一条关联检测规则到 profile 作用域记忆。

    Args:
        rule: 规则文本, 如 "电池系统额定电压12V必须与充电模块输入电压匹配"
    """
    item_id = await memory_service.save(
        rule,
        scope="profile",
        profile=profile,
        kind="decision",
        metadata={"type": "correlation_rule"},
    )
    return item_id


async def recall_correlation_rules(memory_service, query: str, profile: str = "srs"):
    """召回相关关联规则。"""
    hits = await memory_service.recall(
        query, profile=profile, top_k=5, kinds=["decision"])
    return hits


# ============================================================
# Part G: 用 DataFlow-KG 评估三元组一致性
# ============================================================

def evaluate_srs_consistency(triples: list[str], profile: str = "srs") -> dict:
    """使用 DataFlow-KG 的 KGRelationTripleConsistencyEvaluator 评估 SRS 三元组一致性。

    Args:
        triples: 三元组列表

    Returns:
        {"logical_consistency_score": float, "evaluated_sample_indices": [...]}
    """
    from dataflow.serving import APILLMServing_request
    from dataflow.utils.storage import FileStorage
    from dataflow.operators.general_kg.eval.kg_rel_triple_consistency_eval import (
        KGRelationTripleConsistencyEvaluator,
    )

    llm_serving = APILLMServing_request(
        api_url=os.environ.get("DF_API_URL", "https://api.openai.com/v1/chat/completions"),
        model_name=os.environ.get("DF_MODEL", "gpt-4o"),
        max_workers=4,
        temperature=0.0,
    )

    # 准备输入
    input_data = [{"triple": triples, "test_triple": None}]
    input_file = f"/tmp/srs_consistency_input.json"
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(input_data, f, ensure_ascii=False)

    storage = FileStorage(
        first_entry_file_name=input_file,
        cache_path="/tmp/srs_consistency_cache",
        cache_type="json",
    )

    evaluator = KGRelationTripleConsistencyEvaluator(
        llm_serving=llm_serving,
        sample_rate=1.0,
        max_samples=20,
        lang="zh",
    )

    evaluator.run(storage=storage.step(), input_key="triple")

    df = storage.read("dataframe")
    return {
        "logical_consistency_score": df["logical_consistency_score"].iloc[0],
        "evaluated_sample_indices": df["evaluated_sample_indices"].iloc[0],
    }


# ============================================================
# Part H: 完整的 SRS 上下文关联检测主流程
# ============================================================

async def main():
    """SRS 文档上下文关联检测主流程。

    步骤:
      1. DataFlow-KG 抽取三元组
      2. DataMind 构建知识图谱
      3. 图谱关联检测 (neighbors + traverse)
      4. 表格约束查询 (NL2SQL)
      5. 语义检索 (Hybrid RAG)
      6. 关联规则积累 (Memory)
      7. 一致性评估 (DataFlow-KG)
    """

    # ===== 示例 SRS 文本 =====
    srs_chunks = [
        {
            "raw_chunk": "电池系统的工作电压范围为9V至16V，额定电压为12V。"
                         "系统具备过压保护功能，当电压超过16V时自动断开。"
                         "充电模块的输入电压应与电池系统额定电压匹配。",
            "entity": ["电池系统", "工作电压", "额定电压", "12V", "过压保护",
                       "16V", "充电模块", "输入电压"],
        },
        {
            "raw_chunk": "充电模块支持12V和24V两种输入电压模式。"
                         "在12V模式下，充电电流不超过10A。"
                         "充电模块通过CAN总线与电池管理系统通信。",
            "entity": ["充电模块", "12V", "24V", "输入电压", "充电电流", "10A",
                       "CAN总线", "电池管理系统"],
        },
    ]

    print("=" * 60)
    print("Step 1: DataFlow-KG 三元组抽取")
    print("=" * 60)
    triples = extract_srs_triplets_with_dataflow_kg(srs_chunks)
    print(f"抽取到 {len(triples)} 条三元组:")
    for t in triples:
        print(f"  {t}")

    print("\n" + "=" * 60)
    print("Step 2: DataMind 知识图谱构建")
    print("=" * 60)
    graph_service = await build_srs_knowledge_graph(triples, profile="srs")

    print("\n" + "=" * 60)
    print("Step 3: 上下文关联检测")
    print("=" * 60)
    # 检测"电池系统"的关联
    correlations = await detect_context_correlations(graph_service, "电池系统")
    print(f"实体: {correlations['entity']['label']}")
    print(f"一跳邻居数: {len(correlations['neighbors'])}")
    print(f"多跳路径数: {correlations['total_paths']}")
    for nb in correlations["neighbors"]:
        print(f"  邻居: {nb['source']} --{nb['relation']}--> {nb['target']}")

    # 跨章节关联检测
    print("\n跨章节关联检测:")
    cross_correlations = await detect_cross_section_correlations(
        graph_service,
        entities_a=["电池系统", "额定电压"],
        entities_b=["充电模块", "输入电压"],
    )
    for cc in cross_correlations:
        path_nodes = " -> ".join(cc["path"]["nodes"])
        print(f"  {cc['entity_a']} ↔ {cc['entity_b']}: {path_nodes}")

    print("\n" + "=" * 60)
    print("Step 4: 表格约束查询 (NL2SQL)")
    print("=" * 60)
    # SRS 表格 SQL (示例)
    srs_sql = """
    CREATE TABLE IF NOT EXISTS srs_constraints (
        id INTEGER PRIMARY KEY,
        component TEXT NOT NULL,
        parameter TEXT NOT NULL,
        value TEXT NOT NULL,
        unit TEXT,
        section TEXT
    );
    INSERT OR IGNORE INTO srs_constraints VALUES
        (1, '电池系统', '工作电压范围', '9-16', 'V', '3.2.1'),
        (2, '电池系统', '额定电压', '12', 'V', '3.2.1'),
        (3, '充电模块', '输入电压', '12/24', 'V', '3.3.2'),
        (4, '充电模块', '最大充电电流', '10', 'A', '3.3.2');
    """
    db_service = await setup_srs_database(srs_sql, profile="srs")
    result = await query_srs_table_constraints(db_service, "电池系统的额定电压是多少?")
    print(f"SQL: {result['sql']}")
    print(f"结果: {result['rows']}")

    print("\n" + "=" * 60)
    print("Step 5: 语义检索 (Hybrid RAG)")
    print("=" * 60)
    kb_service = await setup_srs_kb(profile="srs")
    chunks = await semantic_search_srs(kb_service, "电池过压保护")
    for ch in chunks:
        print(f"  [score={ch['score']:.4f}] {ch['text'][:80]}...")

    print("\n" + "=" * 60)
    print("Step 6: 关联规则积累 (Memory)")
    print("=" * 60)
    memory_service = await setup_srs_memory(profile="srs")
    # 保存关联规则
    rule_id = await save_correlation_rule(
        memory_service,
        "电池系统额定电压12V必须与充电模块12V输入模式匹配",
        profile="srs",
    )
    print(f"保存规则 ID: {rule_id}")
    # 召回相关规则
    rules = await recall_correlation_rules(memory_service, "电压匹配", profile="srs")
    for r in rules:
        print(f"  [score={r['score']:.4f}] {r['content']}")

    print("\n" + "=" * 60)
    print("Step 7: DataFlow-KG 一致性评估")
    print("=" * 60)
    consistency = evaluate_srs_consistency(triples)
    print(f"逻辑一致性得分: {consistency['logical_consistency_score']:.4f}")
    print(f"评估的样本索引: {consistency['evaluated_sample_indices']}")

    print("\n" + "=" * 60)
    print("SRS 上下文关联检测完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

### 直接使用 DataMind 工具（不经过 Agent 循环）

如果不需要 Agent 自动调度，可以直接调用 Service 层 API：

```python
import asyncio
from datamind.config import Settings, LLMConfig
from datamind.capabilities.graph.service import build_graph_service
from datamind.core.protocols import GraphTriple

async def direct_graph_usage():
    """直接使用 GraphService API (不经过 Agent)。"""

    settings = Settings(
        llm=LLMConfig(
            api_base="https://api.anthropic.com",
            api_key="sk-xxx",
            model="claude-sonnet-4-6",
        ),
    )
    settings.data.profile = "srs"
    settings.ensure_dirs()

    graph = build_graph_service(settings)

    # 1. 写入三元组
    await graph.upsert([
        {"subject": "电池系统", "relation": "额定电压", "object": "12V",
         "subject_type": "component", "object_type": "value", "confidence": 1.0},
        {"subject": "电池系统", "relation": "过压保护阈值", "object": "16V",
         "subject_type": "component", "object_type": "value", "confidence": 1.0},
        {"subject": "充电模块", "relation": "输入电压", "object": "12V",
         "subject_type": "component", "object_type": "value", "confidence": 1.0},
        {"subject": "充电模块", "relation": "通信接口", "object": "CAN总线",
         "subject_type": "component", "object_type": "interface", "confidence": 1.0},
        {"subject": "充电模块", "relation": "通信对象", "object": "电池管理系统",
         "subject_type": "component", "object_type": "system", "confidence": 1.0},
    ])

    # 2. 搜索实体
    entities = await graph.search_entities("电池", top_k=3)
    print(f"找到 {len(entities)} 个实体:")
    for e in entities:
        print(f"  {e['label']} (type={e['type']}, score={e['score']:.2f})")

    # 3. 查询邻居
    battery_id = entities[0]["id"]
    neighbors = await graph.neighbors(battery_id, direction="both")
    print(f"\n'{battery_id}' 的邻居:")
    for nb in neighbors:
        print(f"  {nb['source']} --[{nb['relation']}]--> {nb['target']}")

    # 4. 多跳遍历 (发现间接关联)
    paths = await graph.traverse(battery_id, max_hops=3)
    print(f"\n从 '{battery_id}' 出发的 {len(paths)} 条多跳路径:")
    for p in paths[:10]:
        path_str = " -> ".join(p["nodes"])
        print(f"  [score={p['score']:.3f}] {path_str}")

    # 5. 约束遍历 (只跟踪特定关系)
    constrained_paths = await graph.traverse(
        battery_id, max_hops=2,
        relation_filter=["额定电压", "输入电压"])
    print(f"\n约束遍历 (额定电压/输入电压): {len(constrained_paths)} 条路径")

    print(f"\n图谱统计: {graph.stats()}")

asyncio.run(direct_graph_usage())
```

### 使用 Agent 循环自动检测

```python
import asyncio
from anthropic import AsyncAnthropic
from datamind.config import Settings, LLMConfig
from datamind.core.tools import ToolRegistry
from datamind.capabilities.graph.tools import build_graph_tools
from datamind.capabilities.db.tools import build_db_tools
from datamind.capabilities.kb.tools import build_kb_tools
from datamind.capabilities.memory.tools import build_memory_tools
from datamind.agent.base import AgentLoopConfig
from datamind.agent.loop_native import NativeAgentLoop
from datamind.capabilities.graph.service import build_graph_service
from datamind.capabilities.db.service import build_db_service
from datamind.capabilities.kb.service import build_kb_service
from datamind.capabilities.memory.service import build_memory_service

SRS_SYSTEM_PROMPT = """\
你是 SRS 文档一致性检测助手。你可以使用以下工具:

图谱工具:
- graph_search_entities: 搜索知识图谱中的实体
- graph_neighbors: 查询实体的直接关联
- graph_traverse: 多跳遍历发现间接关联
- graph_upsert_triples: 添加新的三元组

数据库工具:
- db_list_tables: 列出数据库表
- db_describe_table: 查看表结构
- db_query_sql: 执行 SQL 查询
- db_query_nl: 自然语言查询

知识库工具:
- kb_search: 语义检索 SRS 文档

记忆工具:
- memory_save: 保存关联检测规则
- memory_recall: 召回相关规则

检测流程:
1. 用 graph_search_entities 找到相关实体
2. 用 graph_neighbors 检查直接关联是否一致
3. 用 graph_traverse 发现间接关联
4. 用 db_query_nl 查询表格约束验证
5. 用 kb_search 检索原文上下文
6. 用 memory_save 保存发现的关联规则
7. 综合所有信息判断是否存在不一致
"""

async def agent_based_detection():
    """使用 DataMind Agent 自动检测 SRS 上下文关联。"""

    settings = Settings(
        llm=LLMConfig(
            api_base="https://api.anthropic.com",
            api_key="sk-xxx",
            model="claude-sonnet-4-6",
        ),
    )
    settings.data.profile = "srs"
    settings.ensure_dirs()

    client = AsyncAnthropic(
        api_key=settings.llm.api_key.get_secret_value(),
        base_url=str(settings.llm.api_base))

    # 构建所有 Service
    graph_svc = build_graph_service(settings)
    db_svc = build_db_service(settings, llm_client=client)
    kb_svc = build_kb_service(settings, llm_client=client)
    memory_svc = build_memory_service(settings, llm_client=client)

    # 构建工具注册表
    registry = ToolRegistry()
    registry.extend(build_graph_tools(graph_svc))
    registry.extend(build_db_tools(db_svc))
    registry.extend(build_kb_tools(kb_svc))
    registry.extend(build_memory_tools(memory_svc))

    # 创建 Agent
    agent = NativeAgentLoop(
        client=client,
        tools=registry,
        config=AgentLoopConfig(
            model=settings.llm.model,
            max_tokens=4096,
            temperature=0.0,
            system_prompt=SRS_SYSTEM_PROMPT,
            max_tool_turns=12,
        ),
    )

    # 运行检测
    result = await agent.run_turn(
        user_message="请检查电池系统和充电模块之间的电压参数是否一致。"
                     "搜索知识图谱中的电池系统和充电模块实体，"
                     "检查它们的电压相关参数是否匹配，"
                     "并查询数据库中的约束表格验证。"
    )

    print(f"Answer: {result['answer']}")
    print(f"Iterations: {result['iterations']}")
    print(f"Stop reason: {result['stop_reason']}")

asyncio.run(agent_based_detection())
```

### JSONL 三元组文件格式

DataMind GraphService 从 `data/profiles/<profile>/triplets/*.jsonl` 自动加载三元组：

```jsonl
{"subject": "电池系统", "relation": "工作电压范围", "object": "9V-16V", "subject_type": "component", "object_type": "range", "confidence": 1.0, "source": "srs_section_3.2.1"}
{"subject": "电池系统", "relation": "额定电压", "object": "12V", "subject_type": "component", "object_type": "value", "confidence": 1.0, "source": "srs_section_3.2.1"}
{"subject": "电池系统", "relation": "过压保护", "object": "16V", "subject_type": "component", "object_type": "threshold", "confidence": 0.95, "source": "srs_section_3.2.1"}
{"subject": "充电模块", "relation": "输入电压", "object": "12V", "subject_type": "component", "object_type": "value", "confidence": 1.0, "source": "srs_section_3.3.2"}
{"subject": "充电模块", "relation": "通信接口", "object": "CAN总线", "subject_type": "component", "object_type": "interface", "confidence": 1.0, "source": "srs_section_3.3.2"}
{"subject": "充电模块", "relation": "通信对象", "object": "电池管理系统", "subject_type": "component", "object_type": "system", "confidence": 1.0, "source": "srs_section_3.3.2"}
```

### NetworkX 图谱持久化格式

> 来源：`datamind/capabilities/graph/providers/networkx_store.py:83-111`

```json
{
  "nodes": [
    {"id": "电池系统", "label": "电池系统", "type": "component", "props": {}},
    {"id": "12V", "label": "12V", "type": "value", "props": {}},
    {"id": "充电模块", "label": "充电模块", "type": "component", "props": {}}
  ],
  "edges": [
    {"src": "电池系统", "dst": "12V", "rel": "额定电压", "w": 1.0, "props": {}},
    {"src": "充电模块", "dst": "12V", "rel": "输入电压", "w": 1.0, "props": {}}
  ]
}
```

---

## 附录：DataFlow-KG 与 DataMind 功能对比

| 功能 | DataFlow-KG | DataMind |
|------|-------------|----------|
| **三元组抽取** | `KGTripleExtraction` (LLM + prompt) | `graph_upsert_triples` (直接写入) |
| **实体搜索** | 无独立算子 | `graph_search_entities` (精确/子串/模糊) |
| **多跳路径搜索** | `KGReasoningPathSearch` (BFS) | `graph_traverse` (BFS + 权重排序) |
| **约束路径搜索** | `KGReasoningConstrainedPathSearch` (DFS + 约束) | `graph_traverse` + `relation_filter` |
| **关系推断** | `KGReasoningRelationGeneration` (LLM) | 无（需通过 Agent LLM 调用） |
| **GraphRAG** | `KGGraphRAGQueryExtraction` + `KGGraphRAGSubgraphRetrieval` + `KGGraphRAGGetAnswer` | `graph_traverse` + `kb_search` (Agent 编排) |
| **一致性评估** | `KGRelationTripleConsistencyEvaluator` | 无（需通过 Agent LLM 调用） |
| **NL2SQL** | 无 | `db_query_nl` (Anthropic + SQLAlchemy) |
| **向量检索** | 无 | `kb_search` (Chroma + Hybrid RRF) |
| **长期记忆** | 无 | `memory_save` / `memory_recall` (3-scope) |
| **图存储后端** | 内存 (pandas DataFrame) | NetworkX (JSON 持久化) / Neo4j (可扩展) |
| **编排方式** | Pipeline (storage.step() 串联) | Agent 循环 (工具自动调度) |
| **LLM 后端** | `APILLMServing_request` (OpenAI 兼容) | `AsyncAnthropic` (Anthropic SDK) |

**推荐组合使用方式**：

1. **用 DataFlow-KG 做数据准备**：三元组抽取、QA 生成、一致性评估（批量离线处理）
2. **用 DataMind 做在线检测**：图谱构建、关联查询、NL2SQL、语义检索、规则积累（实时交互）
3. **DataFlow-KG 的输出直接喂给 DataMind**：将 `<subj> X <obj> Y <rel> Z` 格式的三元组解析后写入 `triplets/*.jsonl`，DataMind GraphService 自动加载
