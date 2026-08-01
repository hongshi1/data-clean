# OpenWorldLib 与 DataMind 代码级深度分析

> 本文档基于 OpenWorldLib DeepWiki（11个页面）+ DataMind 源码精读（40+ 文件）产出。
> 调研日期：2026-07-30
> OpenWorldLib: 848 stars, DataFlow L5 应用层世界模型统一代码库
> DataMind: 24 stars, DataFlow 横切组件 Agentic 知识管理中枢

---

## 第一部分：OpenWorldLib 代码级深度分析

> 信息来源：DeepWiki (https://deepwiki.com/OpenDCAI/OpenWorldLib) 共11个页面
> 源码索引时间：2026-04-07, commit a2fa3d2f

### 1. 核心架构：六层抽象

OpenWorldLib 将"世界模型"分解为六个正交层，确保无论底层是 Diffusion、LLM 还是 3DGS，交互生命周期保持一致。

| 层 | 代码目录 | 基类/接口 | 职责 |
|---|---|---|---|
| **Pipeline** | `src/openworldlib/pipelines/` | `PipelineABC` | 顶层编排，管理模型生命周期（加载/推理/流式） |
| **Operator** | `src/openworldlib/operators/` | `BaseOperator` | 输入处理，交互信号解析，感知预处理 |
| **Synthesis** | `src/openworldlib/synthesis/` | `VisualGeneration`, `VLAGeneration` | 生成任务：视频/图像/音频/VLA |
| **Reasoning** | `src/openworldlib/reasoning/` | `SpatialReasoner`, `GeneralReasoning` | 认知任务：空间理解/VQA/多模态CoT |
| **Representation** | `src/openworldlib/representations/` | `PointCloudsGeneration`, `SimulationEnvironment` | 结构化世界建模：3D点云/深度图/仿真 |
| **Memory** | `src/openworldlib/memories/` | `BaseMemory` | 跨轮次状态维护，时间连续性 |

> 来源：DeepWiki [2 Core Architecture](https://deepwiki.com/OpenDCAI/OpenWorldLib/2-core-architecture)

### 2. PipelineABC：管道生命周期

`PipelineABC` 是所有推理流程的抽象基类，定义于 `src/openworldlib/pipelines/pipeline_utils.py:5-25`。

#### 2.1 生命周期三阶段

```python
# PipelineABC 生命周期（基于 DeepWiki 2.1 还原）
class PipelineABC:
    # ── 阶段1: 初始化 ──
    @staticmethod
    def from_pretrained(model_path, **kwargs):
        """入口点：解析模型路径，实例化 Synthesis/Reasoning/
        Representation/Memory 模块，加载权重。
        复杂模型(如Cosmos)通过 required_components 字典
        同时加载 Text Encoder + VAE。"""
        ...

    # ── 阶段2: 内部引擎 ──
    def process(self, interaction_signal, perception_inputs):
        """1. 信号解析：Operator 将 "forward" 等转为张量
           2. 感知处理：准备视觉/听觉输入
           3. 模型调用：调用 Synthesis 或 Reasoning 执行计算"""
        ...

    # ── 阶段3a: 标准推理（单轮）──
    def __call__(self, **kwargs):
        """单次推理，无状态或仅内部状态。
        典型用途：生成固定长度序列。"""
        ...

    # ── 阶段3b: 流式推理（多轮有状态）──
    def stream(self, interactions, **kwargs):
        """利用 Memory 模块维持时间/对话连续性。
        第N轮最后一帧 → 第N+1轮的初始条件帧。"""
        ...
```

#### 2.2 `__call__()` vs `stream()` 对比

| 特性 | `__call__()` | `stream()` |
|---|---|---|
| 用途 | 标准推理（单次） | 多轮/交互式 |
| Memory | 无状态或仅内部 | 使用 MemoryModule (record/select) |
| 连续性 | 固定时长/输出 | 追加历史，支持无限生成 |
| 示例 | `test_lingbot_world.py:41-47` | `test_cosmos_predict2p5_stream.py:79-88` |

> 来源：DeepWiki [2.1 PipelineABC](https://deepwiki.com/OpenDCAI/OpenWorldLib/2.1-pipelineabc:-the-pipeline-lifecycle)

#### 2.3 管道注册表与映射

OpenWorldLib 用两个映射文件为 `run_benchmark.py` 等 CLI 提供统一接口：

- **`examples/pipeline_load_mapping.py`** — 工厂层，定义各模型如何初始化
  - `load_matrix_game2_pipeline`, `load_wan2p2_pipeline` 等函数
  - `_resolve_path()` 处理单字符串或字典形式的检查点路径
  - `video_gen_pipe` / `reasoning_pipe` 字典映射模型名→加载函数

- **`examples/pipeline_infer_mapping.py`** — 推理层，定义各管道如何调用 `__call__`
  - `infer_matrix_game2_pipeline`, `infer_qwen2p5_omni_pipeline` 等
  - 抽象掉参数名差异（如 `images` vs `image_path`）
  - 含后处理：根据交互信号长度计算 `num_output_frames`

### 3. Operator 层：输入处理与交互信号

> 来源：DeepWiki [2.2 Operator Layer](https://deepwiki.com/OpenDCAI/OpenWorldLib/2.2-operator-layer:-input-processing-and-interaction-signals)
> 源码：`src/openworldlib/operators/*.py`

#### 3.1 BaseOperator 生命周期方法

```python
class BaseOperator:
    def interaction_template_init(self):     # 初始化有效交互列表
    def get_interaction(self, signal):       # 验证并追加交互信号
    def check_interaction(self, signal):     # 成员检查（是否支持）
    def process_interaction(self):           # 累积信号 → 特征字典/张量
    def process_perception(self, inputs):    # 视觉信号 → 归一化RGB数组[0,1]
```

#### 3.2 统一3D交互模式（Unified 3D Interaction Schema）

跨所有导航/3D重建管道（VGGT/CUT3R/HunyuanWorld/MatrixGame）强制统一控制信号：

| 类别 | 支持的交互字符串 |
|---|---|
| **平移** | `forward`, `backward`, `left`, `right`, `forward_left`, `forward_right`, `backward_left`, `backward_right` |
| **旋转** | `camera_up`, `camera_down`, `camera_l`, `camera_r`, `camera_ul`, `camera_ur`, `camera_dl`, `camera_dr` |
| **光学** | `camera_zoom_in`, `camera_zoom_out` |

> 来源：`src/openworldlib/operators/cut3r_operator.py:18-25`

#### 3.3 具体Operator实现

| Operator | 管道 | 交互模式 | 特点 |
|---|---|---|---|
| `VGGTOperator` / `CUT3ROperator` | 3D导航/重建 | 统一3D模式 | `process_perception`归一化到[0,1]，BGR→RGB |
| `PI0Operator` / `LingBotVAOperator` | VLA机器人 | 多模态(视觉+文本) | 多视角相机键管理，动作归一化(`norm_stat`) |
| `HunyuanWorldPlayOperator` | 生成式世界 | 3D模式+自然语言 | 结合3D交互模式与文本提示驱动视频合成 |

### 4. Memory 模块：有状态多轮交互

> 来源：DeepWiki [2.3 Memory Module](https://deepwiki.com/OpenDCAI/OpenWorldLib/2.3-memory-module:-stateful-multi-turn-interaction)

#### 4.1 BaseMemory 五阶段生命周期

```python
class BaseMemory:
    def record(self, data):     # 存储：帧/token/交互 → 存储区
    def select(self):           # 检索：提取下一轮上下文（如最后一帧）
    def compress(self):         # 压缩：裁剪/摘要旧状态，适应上下文窗口
    def process(self):          # 格式化：转为模型所需张量/kv_cache/latents
    def manage(self, action):   # 管理：reset/save/load/eviction/STM→LTM转移
```

#### 4.2 两类记忆实现

**视觉合成记忆**（时间连续性）：

| 实现 | 支持模型 | 关键特性 |
|---|---|---|
| `CosmosMemory` | Cosmos-Predict2.5 | 管理 `all_frames` 缓冲；`select()`提取最后PIL帧 |
| `YumeMemory` | Yume/Yume1.5 | 存储latent历史+帧缓冲，维持相机轨迹一致性 |
| `LingBotMemory` | LingBot-World | DDP感知帧拼接，支持分布式流式 |
| `WanMemory` | Wan 2.1/2.2 | 张量→PIL转换，帧持久化 |

`stream()` 工作流：用户交互 → 生成视频块 → `memory.record(chunk)` → `memory.select()`取末帧 → 作为下一轮 `image_path` 输入。

**推理记忆**（对话状态）：存储 `List[Dict]`（含角色+内容），`manage(action="reset")` 清空历史。`OmniVinciMemory.process()` 确保前轮生成的视频在当前推理轮正确引用为视觉输入。

> 关键技术：Yume1.5 的 `predict_per_interaction` 中，当 `interaction_idx > 0` 时从上一轮记忆取出 `history_latents` 初始化扩散过程，避免朴素视频拼接的闪烁效应。
> 源码：`src/openworldlib/synthesis/visual_generation/yume/yume_1p5_synthesis.py:159-162`

### 5. Base Models：基础模型核心

> 来源：DeepWiki [2.4 Base Models](https://deepwiki.com/OpenDCAI/OpenWorldLib/2.4-base-models:-diffusion-llmmllm-and-perception-cores)

`base_models/` 分四个域：

| 域 | 包含模型 | 用途 |
|---|---|---|
| `diffusion_model` | Wan 2.1/2.2, Cosmos Predict 2.5, HunyuanVideo, DiffSynth | 视频/图像生成 |
| `llm_mllm_core` | Qwen2.5-Omni, Qwen2-VL, OmniVinci | 文本处理/视觉理解/动作token |
| `perception_core` | DepthAnything V1/V2, 3DGS | 检测/分割/深度估计 |
| `three_dimensions` | 点云处理, 3DGS渲染 | 3D场景表示 |

- Cosmos 用 `FlowUniPCMultistepScheduler`（`fm_solvers_unipc.py`）进行高效流匹配采样
- 复杂模型通过 `from_pretrained` 的 `required_components` 字典同时加载 Text Encoder + VAE
- 多GPU推理用 `init_distributed_group`（如 LingBot）

### 6. 四大功能支柱与管道类型总览

| 支柱 | 管道类型 | 代表模型 | 核心任务 | 交互信号 | DeepWiki页 |
|---|---|---|---|---|---|
| **Synthesis** | 导航视频 | MatrixGame2, LingBot, HunyuanGameCraft, Yume | 相机/自运动驱动视频生成 | 统一3D模式 | 3.1 |
| **Synthesis** | 交互视频 | CosmosPredict2.5, Wan2p2, Sora2, Veo3 | 文本/图像→视频，支持img2world/video2world | 文本+图像 | 3.2 |
| **Synthesis** | 音频生成 | MMAudio, ThinkSound | 视频配音/文本→音频 | 文本+视频 | 3.3 |
| **Representation** | 3D点云 | VGGT, CUT3R, Pi3, LoGeR, FlashWorld, HunyuanMirror | 2D→3D点云重建 | 多视图图像 | 4.1 |
| **Representation** | 仿真环境 | AI2Thor | 仿真器状态 | 环境配置 | 4.3 |
| **Reasoning** | 空间推理 | SpatialReasoner, SpatialLadder | 3D关系/坐标估计 | 图像+空间查询 | 5.1 |
| **Reasoning** | 通用多模态 | OmniVinci, Qwen2.5-Omni | 文/图/视/音多轮对话 | 多模态消息 | 5.2 |
| **VLA** | 机器人动作 | PI0, GigaBrain0, Spirit, LingBot-VA, Libero | 视觉+语言→动作序列 | 多视角+指令 | 6 |

> 来源：DeepWiki [3 Synthesis](https://deepwiki.com/OpenDCAI/OpenWorldLib/3-synthesis-pipelines:-visual-and-audio-generation) | [5 Reasoning](https://deepwiki.com/OpenDCAI/OpenWorldLib/5-reasoning-pipelines:-multimodal-and-spatial) | [6 VLA](https://deepwiki.com/OpenDCAI/OpenWorldLib/6-vision-language-action-(vla)-pipelines)

### 7. 合成管道细节

#### 7.1 导航视频生成
- 关键模型：MatrixGame2, HunyuanGameCraft, LingBot-World, Astra, Yume
- 帧数逻辑：`num_output_frames = len(interaction_signal) * 12`（`pipeline_infer_mapping.py:8-14`）
- 流式：末帧作为下一轮初始帧

#### 7.2 交互式/文本转视频
- CosmosPredict2.5：流匹配采样，支持 `img2world` / `video2world`
- `FlowUniPCMultistepScheduler` 高效采样
- API集成：Sora2, Veo3（通过API客户端）

#### 7.3 音频生成
- **MMAudio**：文本→音频 + 视频→音频，用 `BigVGANv2` 声码器 + `CLIP` 对齐
- **ThinkSound**：Chain-of-Thought分析视频内容后再生成同步音效，用 `Synchformer`

### 8. 推理管道细节

#### 8.1 空间推理
- **SpatialReasonerPipeline**：显式空间推理，坐标对齐
- **SpatialLadderPipeline**：层次化空间理解，基于 `Qwen2_5_VLForConditionalGeneration`
- 交互生命周期：`get_interaction` → `process_interaction`(均匀采样视频帧) → `inference` → `delete_last_interaction`

#### 8.2 通用多模态推理

| 管道 | 基础模型 | 特性 |
|---|---|---|
| `OmniVinciPipeline` | nvidia/omnivinci | 高保真视频/音频推理，`OmniVinciMemory` |
| `Qwen2p5OmniPipeline` | Qwen2.5-Omni-7B | 原生视频内音频支持，流式多轮 |

- 记忆管理：`QwenMemory`/`OmniVinciMemory` 维护跨轮上下文
- 环境依赖：`omnivinci_install.sh` 管理音频和缩放依赖

### 9. VLA 管道细节

> 来源：DeepWiki [6 VLA Pipelines](https://deepwiki.com/OpenDCAI/OpenWorldLib/6-vision-language-action-(vla)-pipelines)

#### 9.1 扩散VLA（PI0 & GigaBrain0）

```python
# VLA管道组件结构（基于 DeepWiki 6 还原）
# Pipeline → from_pretrained() + __call__()
#   └─ Operator → 图像resize(224x224) + norm_stat归一化 + tokenization
#       └─ Synthesis → VLM + Diffusion Head, 管理采样循环
#           └─ Model Core → PaliGemmaWithExpertModel / GigaBrain0Policy
```

- **PI0**：扩散去噪循环生成动作轨迹，双流注意力（PaliGemma），支持 Aloha/Libero/Droid 多机器人本体；PI0.5 模式用离散状态输入+分位数归一化
- **GigaBrain0**：PI0 架构演进，"知识隔离"（knowledge insulation），多本体训练通过本体专属线性层

#### 9.2 专用VLA
- **Spirit V1.5**：通用VLA
- **LingBot-VA**：`lingbot_va_synthesis` + 专用 operator，多视角相机键
- **Libero**：LIBERO基准专用，BDDL任务格式 + 专用归一化统计

### 10. 基准评估框架

> 来源：DeepWiki [7 Benchmarking](https://deepwiki.com/OpenDCAI/OpenWorldLib/7-benchmarking-and-evaluation-framework)
> 源码：`examples/run_benchmark.py`, `data/benchmarks/benchmark_loader.py`

#### 10.1 架构
- `run_benchmark.py` 为入口，`tasks_map` 注册表关联任务类型与元数据/数据路径
- `BenchmarkLoader`：解析 `.jsonl`/`.json`，自动展开相对媒体路径为绝对路径；支持 HuggingFace `snapshot_download`
- `eval_func_mapping`：任务类别→评分逻辑

#### 10.2 两阶段执行
1. **参考生成**：`run_reference` 遍历样本，用管道推理映射生成结果
2. **评估打分**：MLLM评分或确定性脚本评分

#### 10.3 任务类型与指标

| 任务类型 | 核心指标 | 评估方法 |
|---|---|---|
| `navigation_video_gen` | 保真度、一致性 | MLLM评分(1-10) |
| `text2video_generation` | 对齐度、质量 | MLLM评分(1-10) |
| `vla` | 成功率 | 确定性脚本 |
| `spatial_reasoning` | 准确率 | 精确匹配/LLM |

- MLLM评分维度：`navigation_fidelity`, `temporal_consistency`, `visual_quality`（用 Qwen2.5-Omni）
- 可恢复评估：结果持久化到 `results.json`，中断后跳过已生成样本

### 11. Vibe Coding：LLM辅助框架构建

> 来源：DeepWiki [8.1 Vibe Coding](https://deepwiki.com/OpenDCAI/OpenWorldLib/8.1-vibe-coding:-llm-assisted-framework-construction)
> 源码：`tools/vibe_code/prompts/*.py`

Vibe Coding 是用 LLM 作为"架构师级助手"，将原始模型实现转化为符合 OpenWorldLib 六层抽象的模块化组件的方法论。

#### 11.1 五个核心提示模板

| 模板 | 文件 | 强制实现 |
|---|---|---|
| General | `general_instruction.py` | Pipeline: `from_pretrained`/`process`/`__call__`/`stream`; Operator: 继承`BaseOperator` |
| Synthesis | `synthesis_instruction.py` | `BaseSynthesis.predict()` 接收Operator处理结果 |
| Reasoning | `reasoning_instruction.py` | `BaseReasoning.inference()` 多模态理解执行点 |
| Representation | `represent_instruction.py` | `BaseRepresentation.get_representation()` 输出点云/深度图/相机位姿 |
| Memory | `memory_instruction.py` | 有状态`BaseMemory`，管理跨轮交互历史 |

#### 11.2 Memory类规范（Vibe Coding模板）

| 方法 | 目的 | 实现细节 |
|---|---|---|
| `record()` | 摄入 | 每轮后存入原始数据(PIL.Image/text) |
| `select()` | 检索 | 取下一轮上下文（如最后生成帧） |
| `compress()` | 精炼 | 蒸馏关键信息（摘要/特征提取） |
| `process()` | 适配 | 转为模型就绪格式(kv_cache/latents) |
| `manage()` | 生命周期 | reset/eviction/STM→LTM转移 |

> 示例：`MatrixGame2Memory` 存储生成帧，检索 `last_frame` 维持导航时间连续性。

### 12. 训练与微调

> 来源：DeepWiki [9 Training](https://deepwiki.com/OpenDCAI/OpenWorldLib/9-training-and-fine-tuning)

- **数据格式**：`sft_demo.jsonl`（image + conversations 字段，含 `<image>` 占位符）
- **Emu3.5 SFT**：`Emu3ForCausalLM` + flash attention + bfloat16 + DeepSpeed Stage 2/3
- **HunyuanWorld-Voyager**：导航专用微调，将 `forward`/`backward`/`rotation` 信号注入扩散 U-Net/Transformer
- **open_RTFM（规划中）**：VLA微调标准化接口，针对 `PaliGemmaWithExpertModel` 的扩散动作头
- **路线图**：RLWM（合成管道作为可微环境训练推理Agent）、统一 `WorldDataset`、原生 `accelerate`/`torch.distributed` 支持

---

## 第二部分：DataMind 代码级深度分析

> 信息来源：源码精读 `dataflow_repos/DataMind/`（40+ 文件）
> DataMind DeepWiki 页面未加载成功，全部基于源码

### 1. 项目结构与模块职责

```
DataMind/
├── datamind/                        # 核心包
│   ├── core/                        # 核心架构
│   │   ├── protocols.py             # 7个Protocol + 9个DTO（Pydantic模型）
│   │   ├── registry.py              # 泛型Registry[T] + 6个全局注册表
│   │   ├── tools.py                 # ToolSpec/ToolRegistry/ToolProvider
│   │   ├── hooks.py                 # Hook框架(Allow/Deny/AskUser/Rewrite)
│   │   ├── context.py               # RequestContext(trace_id/session_id/profile)
│   │   ├── errors.py / logging.py
│   ├── capabilities/                # 六大知识面 + hooks
│   │   ├── kb/                      # 知识库RAG
│   │   │   ├── service.py           # KBService(embedding+vector_store+retriever)
│   │   │   ├── indexer.py           # 分块+嵌入+索引
│   │   │   ├── tools.py             # 4个KB工具
│   │   │   └── providers/           # chroma_store, simple/multi_query/hybrid_retriever
│   │   ├── graph/                   # GraphRAG
│   │   │   ├── service.py           # GraphService
│   │   │   ├── tools.py             # 4个Graph工具
│   │   │   └── providers/           # networkx_store
│   │   ├── db/                      # NL2SQL
│   │   │   ├── service.py           # DBService(dialect+engine+nl2sql)
│   │   │   ├── nl2sql.py            # LLM生成SQL
│   │   │   ├── safeguard.py         # 破坏性SQL防护
│   │   │   ├── tools.py             # 4个DB工具
│   │   │   └── providers/           # sqlite, mysql
│   │   ├── memory/                  # 长期记忆
│   │   │   ├── service.py           # MemoryService(短期+长期)
│   │   │   ├── extractor.py         # LLM事实抽取
│   │   │   ├── short_term.py        # 滚动窗口短期记忆
│   │   │   ├── tools.py             # 4个Memory工具
│   │   │   └── providers/           # sqlite_store
│   │   ├── skills/                  # 技能(SOP+代码工具)
│   │   │   ├── service.py           # SkillsService(知识技能+代码技能)
│   │   │   ├── loader.py            # SKILL.md解析(YAML frontmatter)
│   │   │   ├── code_skills.py       # 4个内置代码工具
│   │   │   └── tools.py             # 3个知识技能工具
│   │   ├── ingest/                  # 对话式数据导入
│   │   │   ├── service.py           # IngestService(KB+DB+Graph导入)
│   │   │   └── tools.py             # 4个Ingest工具
│   │   ├── hooks/                   # 3个安全Hook
│   │   │   ├── path_allowlist.py    # 路径白名单
│   │   │   ├── destructive_sql.py   # 破坏性SQL拦截
│   │   │   └── audit.py             # 审计日志(Merkle哈希链)
│   │   └── embedding/               # 嵌入服务
│   ├── agent/                       # Agent循环
│   │   ├── base.py                  # AgentLoopProtocol + AgentEvent
│   │   ├── loop_native.py           # 原生循环(anthropic SDK)
│   │   ├── loop_sdk.py              # SDK循环(claude-agent-sdk + CCR)
│   │   ├── options.py / prompts.py
│   ├── kernel/                      # 数据血缘内核(正交于知识面)
│   │   ├── lifecycle.py             # ArtifactRef/ChangeSet/SnapshotSet
│   │   ├── trace.py / provenance.py / effects.py / budget.py
│   │   ├── memory_mutation.py / context.py / source.py / types.py
│   ├── engine/                      # 执行引擎
│   │   ├── runtime.py / executor.py / replay.py / recording.py / fingerprint.py
│   ├── lifecycle/                   # 生命周期管理
│   │   ├── catalog.py / manager.py / serde.py / errors.py
│   ├── adapters/                    # 适配器(artifact/memory/document/sqlite/audit)
│   ├── ports/                       # 端口抽象(trace/lifecycle/source)
│   ├── dataops/                     # 数据操作(plan/operations/results/validation)
│   ├── skills/                      # 内置技能(code-review, db-ops-sop)
│   ├── scripts/                     # hello_* demo脚本(12个)
│   ├── config.py / cli.py / server.py / __main__.py
├── schema/types.py                  # 顶层schema
├── modules/                         # 旧版模块(database/memory/graphrag/agent/rag)
├── benchmark/                       # 基准测试
├── core/                            # 顶层核心(bootstrap, session)
├── main.py / server.py / config.py / benchmark.py
```

### 2. Protocol + Registry 架构

> 源码：`datamind/core/protocols.py`, `datamind/core/registry.py`

#### 2.1 Protocol 定义（契约层）

DataMind 用 `typing.Protocol` + `@runtime_checkable` 定义六大能力契约，外加共享 DTO：

```python
# datamind/core/protocols.py（节选）
from typing import Protocol, runtime_checkable

# ── DTO（Pydantic模型，跨能力共享）──
class RetrievedChunk(BaseModel):    # RAG返回的文档片段
    id: str; text: str; score: float; source: str | None; metadata: dict

class GraphTriple(BaseModel):       # 知识图谱三元组
    subject: str; relation: str; object: str; confidence: float

class MemoryItem(BaseModel):        # 记忆条目（三作用域）
    id: str
    scope: Literal["global","profile","session"] = "profile"
    kind: Literal["preference","decision","workflow","summary","skill","fact"] = "fact"
    status: Literal["active","archived"] = "active"
    content: str; score: float

# ── 能力协议 ──
@runtime_checkable
class VectorStore(Protocol):        # 向量索引
    async def add(self, ids, texts, embeddings, metadatas): ...
    async def query(self, embedding, *, top_k, where): ...
    async def get_all_texts(self): ...  # BM25重建索引用

@runtime_checkable
class GraphStore(Protocol):         # 知识图谱后端
    async def upsert_triples(self, triples): ...
    async def search_entities(self, query, *, top_k): ...
    async def traverse(self, start, *, max_hops, relation_filter): ...
    async def neighbors(self, entity, *, direction): ...

@runtime_checkable
class DatabaseDialect(Protocol):    # SQL后端
    def build_engine(self, dsn, **kwargs): ...
    async def execute_readonly(self, engine, sql, *, row_limit, timeout_s): ...
    def is_destructive(self, sql) -> bool: ...

@runtime_checkable
class MemoryStore(Protocol):        # 长期记忆（三作用域分区）
    async def save(self, content, *, scope, profile, session_id, kind): ...
    async def recall(self, query, *, profile, session_id, top_k, kinds): ...
    async def forget(self, item_id, *, hard): ...
```

#### 2.2 Registry 注册机制

```python
# datamind/core/registry.py
class Registry(Generic[T]):
    """Name -> class 注册表，带类型化工厂访问"""
    def register(self, name: str) -> Callable[[type[T]], type[T]]:
        """装饰器：注册类。重复注册抛 ConfigError"""
        def deco(cls):
            if name in self._entries:
                raise ConfigError(f"provider '{name}' already registered")
            self._entries[name] = cls
            return cls
        return deco

    def create(self, name: str, **cfg) -> T:
        """实例化指定 provider。未知名抛 ConfigError 并列出已注册项"""
        cls = self._entries.get(name)
        if cls is None:
            raise ConfigError(f"Unknown provider '{name}'. Registered: {self.known()}")
        return cls(**cfg)

# 6个全局注册表（模块级，导入provider模块即注册）
embedding_registry   = Registry("embedding")
retriever_registry   = Registry("retriever")
graph_registry       = Registry("graph")
db_registry          = Registry("database")
memory_registry      = Registry("memory")
vector_store_registry = Registry("vector_store")
```

**扩展模式**：新增一个 provider 只需 `@registry.register("name")` 装饰类，`config.py` 无需改动——配置中的字符串名自动路由到注册表。

### 3. ToolRegistry：27个工具的注册与路由

> 源码：`datamind/core/tools.py` + 各 `capabilities/*/tools.py`

#### 3.1 工具框架

```python
# datamind/core/tools.py
@dataclass(frozen=True)
class ToolSpec:
    """声明式工具描述 + 异步handler"""
    name: str                      # 会话内唯一
    description: str
    input_schema: dict             # JSON Schema (Draft 2020-12)
    handler: ToolHandler           # async callable: JSON输入 → JSON输出
    metadata: dict = field(default_factory=dict)  # {group, destructive, ...}

    def to_anthropic_tool(self) -> dict:
        """序列化为 Anthropic API 的 tools= 格式"""
        return {"name": self.name, "description": self.description,
                "input_schema": self.input_schema}

@runtime_checkable
class ToolProvider(Protocol):
    """贡献一批 ToolSpec 的 provider（MCP-server 风格）"""
    def build(self, **services) -> list[ToolSpec]: ...

class ToolRegistry:
    """运行时组装的 ToolSpec 集合"""
    def add(self, spec: ToolSpec): ...        # 名称冲突抛异常
    def extend(self, specs: list): ...
    def get(self, name: str) -> ToolSpec: ...  # 未知工具抛异常
    def as_anthropic_tools(self) -> list: ...  # 批量序列化
```

#### 3.2 工具注册代码示例

```python
# datamind/capabilities/kb/tools.py（典型注册模式）
def build_kb_tools(kb: KBService) -> list[ToolSpec]:
    async def _search(query: str, top_k: int = 5, filters: dict | None = None) -> dict:
        chunks = await kb.search(query, top_k=top_k, filters=filters)
        return {"query": query, "results": chunks, "count": len(chunks)}

    return [
        ToolSpec(
            name="kb_search",
            description="Search the knowledge base (vector RAG)...",
            input_schema={"type": "object",
                          "properties": {"query": {"type": "string"},
                                         "top_k": {"type": "integer", "default": 5}},
                          "required": ["query"]},
            handler=_search,
            metadata={"group": "kb"},
        ),
        # ... kb_list_documents, kb_count, kb_reindex
    ]

@tool_provider_registry.register("kb")       # 全局注册，供Agent组装层发现
class _KBToolProvider:
    def build(self, **services) -> list[ToolSpec]:
        kb = services["kb_service"]          # 依赖注入
        return build_kb_tools(kb)
```

#### 3.3 完整27工具清单

| 组 | 工具名 | 数量 | 源码 |
|---|---|---|---|
| **kb** | `kb_search`, `kb_list_documents`, `kb_count`, `kb_reindex` | 4 | `capabilities/kb/tools.py` |
| **graph** | `graph_search_entities`, `graph_traverse`, `graph_neighbors`, `graph_upsert_triples` | 4 | `capabilities/graph/tools.py` |
| **db** | `db_list_tables`, `db_describe_table`, `db_query_sql`, `db_query_nl` | 4 | `capabilities/db/tools.py` |
| **memory** | `memory_save`, `memory_recall`, `memory_forget`, `memory_list_profiles` | 4 | `capabilities/memory/tools.py` |
| **skill.knowledge** | `skill_search`, `skill_get`, `skill_list` | 3 | `capabilities/skills/tools.py` |
| **skill.code** | `get_current_time`, `calculator`, `analyze_text`, `unit_convert` | 4 | `capabilities/skills/code_skills.py` |
| **ingest** | `kb_add_file`, `kb_add_path`, `db_import_csv`, `graph_add_triples_from_text` | 4 | `capabilities/ingest/tools.py` |
| | **合计** | **27** | |

Agent 通过 `ToolRegistry.as_anthropic_tools()` 将全部工具的 schema 注入 LLM，LLM 根据描述自动选择调用。每个工具的 `description` 精确说明何时使用，引导 LLM 路由。

### 4. 六大知识面实现（代码级）

#### 4.1 KB（RAG）：Chroma + BM25 + RRF

> 源码：`capabilities/kb/service.py`, `providers/hybrid_retriever.py`, `providers/chroma_store.py`

```
KBService = EmbeddingProvider + VectorStore(Chroma) + Retriever
```

**HybridRetriever**（`providers/hybrid_retriever.py`）实现向量+词法混合检索：

```python
@retriever_registry.register("hybrid")
class HybridRetriever:
    """Vector search + BM25 with Reciprocal Rank Fusion"""

    async def aretrieve(self, query, *, top_k=5, filters=None):
        # 1. 向量侧：embed_query → VectorStore.query(top_k * candidate_multiplier)
        vec = await self._embed.embed_query(query)
        vec_hits = await self._store.query(vec, top_k=k_inner, where=filters)

        # 2. BM25侧：内存索引，CJK感知分词
        scores = self._bm25.get_scores(_tokenize(query))
        bm25_ranked = {id: (rank, chunk) for ...}

        # 3. RRF融合：score += weight / (rrf_k + rank + 1)
        for idmap, weight in ((vec_ranked, vector_weight), (bm25_ranked, bm25_weight)):
            for cid, (rank, ch) in idmap.items():
                contrib = weight / (self._rrf_k + rank + 1)
                fused[cid] = (fused.get(cid, (0,ch))[0] + contrib, ch)

        return sorted(fused.values(), key=lambda sc: -sc[0])[:top_k]
```

**CJK感知分词器**：`re.findall(r"[\w一-鿿]+", text.lower())`，对2字以上CJK串额外发射单字，提升中文BM25效果。

**三种检索策略**：`simple`（纯向量）、`multi_query`（LLM改写查询）、`hybrid`（向量+BM25+RRF）。

#### 4.2 Graph（GraphRAG）：NetworkX实现

> 源码：`capabilities/graph/providers/networkx_store.py`

```python
@graph_registry.register("networkx")
class NetworkXGraphStore:
    """MultiDiGraph，持久化为JSON文件（storage/<profile>/graph.json）"""

    async def search_entities(self, query, *, top_k=5):
        # 精确匹配(1.0) > 子串(0.7) > 模糊(difflib, 0.4+0.4*ratio)
        for nid, data in self._g.nodes(data=True):
            if nid.lower() == q:           score = 1.0
            elif q in nid.lower():          score = 0.7
            else: ratio = SequenceMatcher(None, q, label).ratio()
                 if ratio < 0.4: continue
                 score = 0.4 + 0.4 * ratio

    async def traverse(self, start, *, max_hops=2, relation_filter=None):
        # BFS遍历，按平均边权排序，relation_filter过滤关系类型
        # 返回 GraphPath(nodes, edges, score)
```

- 支持三元组加载（`load_from_profile` 读 `triplets/*.jsonl`）
- LLM抽取三元组（`graph_add_triples_from_text`：自然语言→JSON三元组→upsert）
- 适合10万边以内，更大规模换 Neo4j provider

#### 4.3 Database（NL2SQL）：SQLAlchemy实现

> 源码：`capabilities/db/service.py`, `nl2sql.py`, `safeguard.py`

```python
class DBService:
    async def query_nl(self, question, *, tables=None):
        # 1. 获取schema描述
        schemas = await self.describe_all()
        # 2. LLM生成SQL（nl2sql.py）
        sql = await generate_sql(client=self._llm, model=self._model,
                                 question=question, schemas=schemas,
                                 dialect_name=self.dialect.name)
        # 3. 只读执行（含is_destructive二次检查）
        result = await self.query_sql(sql)
        return {"question": question, "sql": sql, "columns": ..., "rows": ...}
```

**NL2SQL提示词策略**（`nl2sql.py`）：紧凑schema描述（列名+类型+PK+行数估计）→ "写一条只读SELECT，不输出其他内容" → 去除代码围栏 → `is_destructive`验证。

**安全**：`execute_readonly` 强制 row_limit(1000) + timeout(10s)；`is_destructive` 在执行前后双重检查。

#### 4.4 Skills：.claude/skills/ + 安全Python工具

> 源码：`capabilities/skills/service.py`, `loader.py`, `code_skills.py`

**知识技能**（Markdown SOP）：
```
.claude/skills/<name>/SKILL.md
---
name: code-review
description: 短描述，Agent据此决定何时读取
keywords: [optional, list]
---
# 技能正文（Markdown）
```
- 加载顺序：`.claude/skills/` → `datamind/skills/` → ENV覆盖
- 索引到独立Chroma collection（`chroma_skills`），复用KB基础设施做语义搜索
- YAML frontmatter手写解析（无需外部YAML库）

**代码技能**（4个安全Python工具）：
```python
# code_skills.py
get_current_time  # 当前日期时间
calculator        # 安全eval（__builtins__={}, 禁止import/exec/eval）
analyze_text      # 字符/行/段/词统计
unit_convert      # 长度/质量/温度单位转换
```

#### 4.5 Memory：SQLite + 余弦召回 + LLM事实抽取

> 源码：`capabilities/memory/service.py`, `providers/sqlite_store.py`, `extractor.py`

**三作用域分区**（v0.3多租户隔离）：

| 作用域 | 含义 | 默认预算 |
|---|---|---|
| `global` | 全局适用（"用中文回复"） | 2 |
| `profile` | 租户/项目级 | 4 |
| `session` | 单次对话 | 2 |

```python
# SQLite schema
CREATE TABLE memory_v2 (
    id TEXT PRIMARY KEY,
    scope TEXT CHECK(scope IN ('global','profile','session')),
    profile TEXT, session_id TEXT,
    kind TEXT DEFAULT 'fact',       -- preference/decision/workflow/summary/skill/fact
    status TEXT DEFAULT 'active',   -- active/archived（软删除）
    content TEXT, metadata TEXT,    -- JSON
    embedding BLOB,                 -- float32 packed
    created_at REAL, updated_at REAL, archived_at REAL
);
-- 三个部分索引（仅active行）
```

**召回逻辑**：三作用域各自top-k → 合并去重 → 按余弦相似度排序（同分时session优先于profile优先于global）。

```python
async def recall(self, query, *, profile, session_id, top_k=8):
    budgets = {"session": 2, "profile": 4, "global": 2}  # 默认2+4+2=8
    # 每个scope独立查询+打分
    # 无embedding时降级为词法匹配（词命中率）
    merged.sort(key=lambda m: (-m.score, _scope_priority(m.scope)))
```

**LLM事实抽取**（`extractor.py`）：每轮对话后用 `fallback_model`（廉价模型）提取事实，避免存储闲聊噪音。提示词要求返回JSON数组，跳过问候/道歉/填充。

**v0.2迁移**：旧 `memory` 表的 `namespace` 字段自动映射为 `scope='profile', profile=<namespace>`。

#### 4.6 Ingest：对话式数据导入

> 源码：`capabilities/ingest/service.py`

```python
class IngestService:
    async def kb_add_file(self, path, copy_to_profile=True):
        # 1. _resolve_safe_path（路径安全检查）
        # 2. 读取 → _split_text分块 → _hash去重
        # 3. embed_texts → store.add（与KB共用同一VectorStore）
        # 4. 可选：复制到 profile/uploads/ 供reindex

    async def db_import_csv(self, path, table, if_exists="append"):
        # CSV → 推断schema(全TEXT) → CREATE TABLE → 参数化INSERT
        # 表名/列名验证：[A-Za-z_][A-Za-z0-9_]{0,63}

    async def graph_add_triples_from_text(self, text, max_triples=30):
        # LLM抽取(subject,relation,object) JSON → upsert_triples → persist
```

**路径安全**：`_resolve_safe_path` 解析符号链接后做前缀检查，allow-list默认含 profile数据目录 + cwd + cwd.parent + tmp。

### 5. 可插拔Agent循环（native vs sdk）

> 源码：`datamind/agent/base.py`, `loop_native.py`, `loop_sdk.py`

```python
# datamind/agent/base.py
@runtime_checkable
class AgentLoopProtocol(Protocol):
    async def run_turn(self, *, user_message, history=None) -> dict: ...
    def stream_turn(self, *, user_message, history=None) -> AsyncIterator[AgentEvent]: ...
    # 返回 {answer, history, iterations, stop_reason, usage}
    # AgentEvent.type: text | tool_use | tool_result | hook_asks_user | hook_denied | done | error
```

| 特性 | NativeAgentLoop | SdkAgentLoop |
|---|---|---|
| 后端 | `anthropic` Python SDK 直连 | `claude-agent-sdk` → `claude` CLI → CCR → OpenAI网关 |
| 代码量 | ~280 LOC | ~460 LOC |
| 工具桥接 | 直接调 `spec.handler(**input)` | 包装为MCP server（`create_sdk_mcp_server`） |
| Hook集成 | `_dispatch_tool` 内 pre→handler→post | `_spec_to_sdk_tool` 包装器内同一chokepoint |
| 历史 | 原生 messages 列表 | 折叠为prompt前缀（SDK不接预建对话） |
| 额外能力 | 无 | Subagents/Compaction/Plan mode |
| 配置 | `DATAMIND__AGENT__BACKEND=native`（默认） | `=sdk` |

**核心：Hook对等保证**。两个后端共享同一 `HookChain`，SDK后端通过 `_spec_to_sdk_tool` 包装器在唯一chokepoint运行完整 pre-hook→handler→post-hook 管道，确保 `DestructiveSqlHook`/`PathAllowlistHook`/`AuditLogHook` 在两个后端行为一致。

**NativeAgentLoop 工具分发**（`loop_native.py:73-161`）：
```python
async def _dispatch_tool(self, name, tool_input):
    spec = self._tools.get(name)
    effective_args = dict(tool_input)
    # 1. Pre-hook链
    if self._hooks:
        decision = await self._hooks.pre(name, effective_args)
        if isinstance(decision, Deny):    → 返回结构化拒绝
        if isinstance(decision, AskUser): → 返回需确认
        if isinstance(decision, Rewrite): effective_args = decision.new_args
    # 2. Handler执行
    result = await spec.handler(**effective_args)
    # 3. Post-hook链（审计等）
    if self._hooks:
        await self._hooks.post(name, effective_args, result, err)
```

### 6. 配置系统：Profile机制

> 源码：`datamind/config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATAMIND__",
        env_nested_delimiter="__",
        env_file=(".env", ".env.datamind"),
    )
    llm: LLMConfig          # api_base, api_key(SecretStr), model, fallback_model
    embedding: EmbeddingConfig   # provider, model, dimension
    retrieval: RetrievalConfig  # strategy, top_k, chunk_size, chunk_overlap
    graph: GraphConfig          # backend, dsn
    db: DBConfig                # dialect, dsn, read_only, row_limit
    memory: MemoryConfig        # backend, short_term_turns, long_term_enabled
    data: DataConfig            # profile → data_dir, storage_dir 派生
    agent: AgentConfig          # backend(native|sdk), max_turns
    hooks: HooksConfig          # enabled, destructive_sql, path_allowlist, audit_log
```

**Profile机制**（`DataConfig`）：
```python
class DataConfig(BaseModel):
    profile: str = "default"
    @property
    def data_dir(self):    return self.base_dir / "data" / "profiles" / self.profile
    @property
    def storage_dir(self): return self.base_dir / "storage" / self.profile
```
切换 `profile` 即同步迁移数据和存储（KB索引、SQLite、graph.json、audit.jsonl）。这是多租户隔离的物理边界。

**环境变量示例**：
```bash
DATAMIND__LLM__API_BASE=http://...
DATAMIND__LLM__MODEL=claude-sonnet-4-6
DATAMIND__EMBEDDING__PROVIDER=openai
DATAMIND__DB__DIALECT=mysql
DATAMIND__RETRIEVAL__STRATEGY=hybrid
DATAMIND__AGENT__BACKEND=sdk
DATAMIND__DATA__PROFILE=tenant_acme
```

### 7. Hooks系统：沙箱化工具执行

> 源码：`datamind/core/hooks.py`, `capabilities/hooks/*.py`

#### 7.1 HookDecision 判定联合

```python
@dataclass(frozen=True)
class Allow:    pass                        # 放行（默认）
@dataclass(frozen=True)
class Deny:     reason: str                 # 阻断，Agent收到错误
@dataclass(frozen=True)
class AskUser:  prompt: str; details: dict; confirm_args: dict  # 需人工确认
@dataclass(frozen=True)
class Rewrite:  new_args: dict              # 改写参数后放行（如追加LIMIT）
```

**HookChain**：有序执行，首个非Allow决策胜出；Rewrite可组合（链式传递改写后的参数）；Post-hook总是执行（审计记录所有尝试含被拒的）。

#### 7.2 三个内置Hook

**PathAllowlistHook**（`hooks/path_allowlist.py`）：
- 拦截 `kb_add_file`/`kb_add_path`/`db_import_csv` 的 `path` 参数
- `Path.resolve(strict=False)` 解析符号链接后做前缀检查
- 不在任一允许根下 → `Deny`

**DestructiveSqlHook**（`hooks/destructive_sql.py`）：
- 用 `sqlglot.parse()` 解析SQL AST（比正则鲁棒，处理注释/引号/换行）
- 决策树：
  ```
  SELECT/WITH               → Allow
  INSERT/CREATE TABLE/INDEX → Allow（增量操作）
  UPDATE/DELETE (有WHERE)   → AskUser
  UPDATE/DELETE (无WHERE)   → AskUser（标注"ALL ROWS"）
  DROP/TRUNCATE/ALTER       → AskUser
  DROP DATABASE/SCHEMA      → Deny（彻底拒绝）
  无法解析                   → Deny（偏执默认）
  ```
- `confirm_destructive=True` 短路AskUser分支回Allow
- 仅拦截 `db_query_sql`（NL2SQL最终也走此工具）

**AuditLogHook**（`hooks/audit.py`）：
- 每次工具调用产生 pre + post 两条记录，写入 `storage/<profile>/audit.jsonl`
- **Merkle哈希链**：`record_hash = SHA-256(canonical(prev_hash || record))`，篡改任一记录会破坏后续所有 `record_hash`
- 密钥脱敏：key匹配 `api_key|password|token|secret|...` 的值替换为 `[REDACTED]`
- `verify_audit_log(path)` 端到端验证哈希链完整性

### 8. Kernel 层：数据血缘内核（额外发现）

> 源码：`datamind/kernel/lifecycle.py`

DataMind 除六大知识面外，还有一个正交的 **Kernel 层**，实现不可变artifact版本管理：

```python
@dataclass(frozen=True)
class ArtifactRef:        # artifact身份：artifact_id + version
class ArtifactManifest:   # 内容无关元数据：ref + source + checksum(SHA-256) + locator + lineage
class ChangeSet:          # 乐观幂等变更集：source + base_version + changes + idempotency_key
class SnapshotSet:        # 每源不可变快照绑定
class SyncReceipt:        # 变更应用审计回执
```

- 支持 `add`/`update`/`delete` 三种变更类型
- 乐观并发：`base_version` + `idempotency_key`
- 数据血缘：`lineage: Tuple[ArtifactRef, ...]`（不可重复）
- 快照绑定：`SnapshotSet` 确保计划执行期间数据不变

这一层为 DataMind 提供了可追溯、可重放的数据治理能力，与六大知识面的 CRUD 操作正交。

---

## 第三部分：对SRS项目的深度应用价值

### 1. OpenWorldLib 的 PipelineABC 设计模式如何借鉴到 SRS 处理流程

#### 1.1 映射：世界模型管道 → SRS处理管道

OpenWorldLib 的 `PipelineABC` 生命周期（`from_pretrained → process → __call__/stream`）可完整映射到 SRS 一致性检测流程：

| OpenWorldLib 概念 | SRS 对应 | 借鉴价值 |
|---|---|---|
| `PipelineABC` | `SrsPipelineABC`（SRS处理管道基类） | 统一 MinerU解析/约束提取/一致性检测/评测 的接口 |
| `from_pretrained()` | 加载规则库(GJB 438C) + Gold Standard + 知识图谱 | 一次加载，多文档复用 |
| `Operator` 层 | `SrsOperator`：解析SRS文档结构(章节/表格/图片)为内部schema | 输入归一化，统一GJB/IEEE830/PURE格式 |
| `process()` | 约束提取 + 同值/文本-表格/逻辑检测 | 内部引擎：信号解析→感知处理→模型调用 |
| `__call__()` | 单文档一次性检测 | 无状态，适合批量评测 |
| `stream()` | 增量检测：多轮交互式调试（如先查语法→再查语义→再查逻辑） | 有状态，记忆前序检测结果 |
| `Memory` | `SrsMemory`：记录已检测的约束/已发现的冲突/已应用的规则 | 避免重复检测，支持跨文档知识积累 |
| `Base Models` | Z3求解器 + LLM(GLM-5) + VLM(Kimi) | 可替换的检测核心 |

#### 1.2 具体借鉴：Memory 五阶段 → SRS检测记忆

OpenWorldLib 的 `BaseMemory` 五阶段（record/select/compress/process/manage）可直接映射到 SRS 检测：

```python
class SrsDetectionMemory(BaseMemory):
    def record(self, detection_result):
        """记录每轮检测结果：约束集/冲突/规则应用"""
    def select(self):
        """检索相关上下文：同文档已检约束 + Gold Standard先例"""
    def compress(self):
        """压缩：将已确认无冲突的约束标记为已验证，聚焦未决项"""
    def process(self):
        """格式化：转为Z3断言列表 / LLM提示上下文"""
    def manage(self, action):
        """reset(新文档) / save(持久化报告) / load(恢复会话)"""
```

这比当前 `srs_consistency_checker_v2.py` 的无状态检测更适合交互式调试场景。

#### 1.3 具体借鉴：Vibe Coding → SRS检测器开发

OpenWorldLib 的 Vibe Coding 方法论（用LLM+提示模板将论文实现转化为符合六层抽象的模块）可直接用于 SRS 项目：

- 写 `srs_detection_instruction.py` 模板，让LLM将学术论文中的新检测算法转化为符合 `SrsPipelineABC` 的模块
- 写 `srs_rule_instruction.py` 模板，让LLM将GJB 438C的规则文本转化为可执行检查器
- 强制实现 `from_pretrained`/`process`/`__call__`/`stream`，保证新检测器与现有评测框架兼容

### 2. DataMind 的六知识面如何管理 SRS 的规则库/知识图谱/检测经验

#### 2.1 六知识面 → SRS知识管理映射

| DataMind 知识面 | SRS 项目对应 | 具体应用 |
|---|---|---|
| **KB (RAG)** | SRS文档库 + GJB标准文本 | 将359份SRS + GJB 438C OCR结果分块嵌入Chroma，`kb_search`检索相似需求段落 |
| **Graph (GraphRAG)** | `srs_kb_graph_v2.json`(7720节点) | 用NetworkX存储规则-章节-约束关系图，`graph_traverse`查询规则到需求的追溯路径 |
| **Database (NL2SQL)** | 检测结果统计 + Gold Standard数据 | `db_query_nl`自然语言查询"哪些文档有逻辑冲突"，`db_import_csv`导入评测数据 |
| **Skills** | GJB检测SOP + 检测器使用指南 | 将检测流程写成`.claude/skills/gjb-consistency-check/SKILL.md`，Agent按SOP执行 |
| **Memory** | 检测经验 + 用户偏好 + 误报修正 | `memory_save`记录"该规则在battery_srs上误报"，`memory_recall`避免重复误报 |
| **Ingest** | SRS文档/规则/约束导入 | `kb_add_path`批量导入SRS集合，`graph_add_triples_from_text`从规则文本抽取关系 |

#### 2.2 三作用域记忆 → SRS检测经验分层

DataMind 的三作用域记忆模型天然适配 SRS 检测经验的分层管理：

```python
# global: 适用于所有SRS文档的通用规则
memory_save(content="GJB 438C要求每个CSCI有唯一标识",
            scope="global", kind="fact")

# profile: 某类SRS文档（如航空电子系统）的特定约定
memory_save(content="battery_srs的SOC约束范围0-100，超出为逻辑冲突",
            scope="profile", profile="avionics", kind="decision")

# session: 当前检测会话的临时上下文
memory_save(content="用户确认该表格的单位应为毫秒而非秒",
            scope="session", session_id="check_001", kind="preference")
```

召回时自动合并三层（默认2+4+2=8条），session级修正优先于profile约定优先于global规则，避免误报。

#### 2.3 HybridRetriever → SRS规则检索

SRS项目的GJB规则库有4类规则，当前 `srs_gjb_compliance_scan.py` 是精确匹配。借鉴 `HybridRetriever` 的向量+BM25+RRF：

```python
# 将GJB规则文本嵌入Chroma + BM25索引
# 检测时：hybrid检索最相关规则 → 应用到当前SRS段落
# RRF融合解决"语义相似但用词不同"和"精确关键词命中"的平衡
```

这对中文GJB规则（CJK感知分词器已内置）特别有效。

### 3. DataMind 的 Protocol+Registry 架构如何扩展为 SRS 专用知识面

#### 3.1 新增 SRS 专用 Protocol

```python
# srs_protocols.py
@runtime_checkable
class ConsistencyChecker(Protocol):
    """一致性检测器协议（对应三层检测）"""
    layer: Literal["syntax", "semantic", "logic"]
    async def check(self, document: SrsDocument,
                    constraints: list[Constraint]) -> list[Violation]: ...

@runtime_checkable
class RuleProvider(Protocol):
    """规则源协议（GJB标准/IEEE 830/自定义）"""
    async def load_rules(self) -> list[Rule]: ...
    async def match_rules(self, context: str) -> list[Rule]: ...

@runtime_checkable
class GoldStandardStore(Protocol):
    """Gold Standard管理协议"""
    async def add(self, doc_id: str, violations: list[Violation]): ...
    async def align(self, detected: list[Violation]) -> AlignmentResult: ...
```

#### 3.2 注册 SRS 专用 Provider

```python
# srs_registry.py
checker_registry = Registry("consistency_checker")
rule_registry = Registry("rule_provider")
gold_standard_registry = Registry("gold_standard")

# 注册三层检测器
@checker_registry.register("syntax")
class SyntaxChecker:
    layer = "syntax"
    async def check(self, document, constraints): ...

@checker_registry.register("z3_logic")
class Z3LogicChecker:
    layer = "logic"
    async def check(self, document, constraints):
        # 调用现有 srs_consistency_checker_v2.py 的Z3求解
        ...

# 注册规则源
@rule_registry.register("gjb_438c")
class GJB438CRuleProvider:
    async def load_rules(self):
        # 加载 knowledge/gjb_438c_rules_full.json
        ...
```

#### 3.3 扩展为 SRS 专用工具（接入 DataMind Agent）

```python
# srs_tools.py
def build_srs_tools(checker_registry, rule_registry, gold_standard):
    async def _check_consistency(doc_path, layer="all"):
        """检测SRS文档一致性"""
        ...

    async def _search_rules(query, top_k=5):
        """检索GJB规则"""
        ...

    async def _align_gold_standard(doc_id, detected):
        """对齐Gold Standard，计算P/R/F1"""
        ...

    return [
        ToolSpec(name="srs_check_consistency", ..., metadata={"group": "srs"}),
        ToolSpec(name="srs_search_rules", ..., metadata={"group": "srs"}),
        ToolSpec(name="srs_eval", ..., metadata={"group": "srs"}),
    ]

@tool_provider_registry.register("srs")
class _SrsToolProvider:
    def build(self, **services):
        return build_srs_tools(
            services["checker_registry"],
            services["rule_registry"],
            services["gold_standard_store"],
        )
```

这样 SRS 检测能力可作为 DataMind 的第七个知识面，与现有6个知识面共享 Agent循环/Hook系统/配置系统/审计日志。

#### 3.4 复用 DataMind 的安全基础设施

| DataMind 基础设施 | SRS 场景复用 |
|---|---|
| `PathAllowlistHook` | 限制SRS文档读取范围在 `data/gjb_438c/` 内 |
| `DestructiveSqlHook` | 防止误操作删除Gold Standard数据 |
| `AuditLogHook` | 记录所有检测操作，Merkle哈希链确保报告不可篡改（满足GJB合规审计需求） |
| `Profile` 机制 | 不同SRS子集（GJB格式/IEEE830/PURE）用不同profile隔离 |
| `AgentLoopProtocol` | SRS检测Agent可选native（轻量）或sdk（功能全）后端 |

#### 3.5 综合架构建议

```
SRS一致性检测Agent（基于DataMind扩展）
├── 知识面（7个）
│   ├── kb          → SRS文档库RAG（359份文档）
│   ├── graph       → 规则-需求追溯图（7720节点）
│   ├── db          → 检测结果+Gold Standard
│   ├── memory      → 检测经验（三作用域：通用/文档类/会话）
│   ├── skills      → GJB检测SOP + 检测器使用指南
│   ├── ingest      → SRS文档/规则/约束导入
│   └── srs（新增） → 一致性检测 + 规则检索 + 评测
├── 核心架构
│   ├── Protocol+Registry → 可插拔检测器/规则源/Gold Standard
│   ├── ToolRegistry → 30+工具（27原有 + SRS专用）
│   ├── Hooks → 路径白名单 + 审计日志（GJB合规）
│   └── Agent Loop → native/sdk可切换
└── 借鉴OpenWorldLib
    ├── PipelineABC → SrsPipelineABC统一检测流程
    ├── Memory五阶段 → 交互式检测的记忆管理
    └── Vibe Coding → LLM辅助新检测器开发
```

这一架构将 SRS 项目从"脚本集合"升级为"可交互、可扩展、可审计的 Agentic 系统"，同时保持与 DataFlow 生态的一致性。

---

## 附录：关键源码文件索引

### OpenWorldLib（DeepWiki引用的源码路径）

| 文件 | 内容 | DeepWiki页 |
|---|---|---|
| `src/openworldlib/pipelines/pipeline_utils.py:5-25` | PipelineABC定义 | 2, 2.1 |
| `examples/pipeline_load_mapping.py:4-114` | 管道加载工厂 | 2.1, 2.4 |
| `examples/pipeline_infer_mapping.py:7-142` | 推理映射 | 2.1 |
| `src/openworldlib/operators/cut3r_operator.py:12-175` | Operator基类+3D交互 | 2.2 |
| `src/openworldlib/memories/visual_synthesis/yume/yume_1p5_memory.py` | 视觉记忆 | 2.3 |
| `src/openworldlib/memories/reasoning/qwen/qwen_memory.py` | 推理记忆 | 2.3 |
| `src/openworldlib/synthesis/vla_generation/pi0/pi0_synthesis.py` | PI0合成 | 6.1 |
| `src/openworldlib/synthesis/vla_generation/giga_brain_0/.../modeling_giga_brain_0.py:13-76` | GigaBrain0模型 | 6.1 |
| `examples/run_benchmark.py:16-180` | 基准评估入口 | 7 |
| `data/benchmarks/benchmark_loader.py:14-210` | 数据加载器 | 7.1 |
| `examples/evaluation_tasks/navigation_video_generation.py:58-134` | MLLM评估 | 7.2 |
| `tools/vibe_code/prompts/general_instruction.py:40-150` | Vibe Coding通用模板 | 8.1 |
| `tools/vibe_code/prompts/memory_instruction.py:18-159` | Memory模板 | 8.1 |

### DataMind（本地源码路径）

| 文件 | 行数 | 内容 |
|---|---|---|
| `datamind/core/protocols.py` | 300 | 7 Protocol + 9 DTO |
| `datamind/core/registry.py` | 105 | Registry泛型 + 6全局注册表 |
| `datamind/core/tools.py` | 112 | ToolSpec/ToolRegistry/ToolProvider |
| `datamind/core/hooks.py` | 293 | Hook框架 + HookChain |
| `datamind/config.py` | 273 | 10子配置 + Profile机制 |
| `datamind/agent/base.py` | 108 | AgentLoopProtocol + AgentEvent |
| `datamind/agent/loop_native.py` | 372 | 原生Agent循环 |
| `datamind/agent/loop_sdk.py` | 464 | SDK Agent循环(CCR) |
| `datamind/capabilities/kb/providers/hybrid_retriever.py` | 162 | BM25+向量+RRF混合检索 |
| `datamind/capabilities/kb/service.py` | 145 | KBService工厂 |
| `datamind/capabilities/graph/providers/networkx_store.py` | 262 | NetworkX图存储 |
| `datamind/capabilities/db/nl2sql.py` | 85 | LLM生成SQL |
| `datamind/capabilities/db/service.py` | 129 | DBService+NL2SQL编排 |
| `datamind/capabilities/memory/providers/sqlite_store.py` | 495 | SQLite记忆+三作用域+余弦 |
| `datamind/capabilities/memory/extractor.py` | 82 | LLM事实抽取 |
| `datamind/capabilities/skills/loader.py` | 127 | SKILL.md解析 |
| `datamind/capabilities/skills/code_skills.py` | 165 | 4个代码工具 |
| `datamind/capabilities/ingest/service.py` | 505 | 对话式数据导入 |
| `datamind/capabilities/hooks/path_allowlist.py` | 111 | 路径白名单Hook |
| `datamind/capabilities/hooks/destructive_sql.py` | 225 | 破坏性SQL Hook(sqlglot) |
| `datamind/capabilities/hooks/audit.py` | 265 | 审计日志(Merkle哈希链) |
| `datamind/kernel/lifecycle.py` | 325 | 数据血缘内核(Artifact/ChangeSet) |
