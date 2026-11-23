# 视觉Grounding / 指代表达理解(REC)技术调研 —— 将文本描述绑定到图像区域（2024-2026）

> 调研日期：2026-11-16 | 检索渠道：arXiv API（论文摘要/全文HTML逐条核验）+ GitHub仓库（README/LICENSE逐条核验）+ Hugging Face（模型卡/API）
> 与已有调研关系：`diagram_extraction_technology_spectrum.md`（结构提取方法版图）、`cross_modal_consistency_survey.md`、`multimodal_srs_increment_survey_202611.md` 均从"文档/一致性"视角出发；本报告聚焦其底层的**文本→区域绑定能力**（visual grounding / referring expression comprehension, REC），为方向A"SRS图文条目聚合"提供定位技术选型与评测协议依据
> 核验纪律：**所有数字均给出可追溯来源**（论文表/HF模型卡/GitHub README）；未能在线核实的一律注明"未核实"或不收录。Papers with Code已于2025年下线，RefCOCO排行榜的"官方SOTA"以逐篇论文交叉验证代替

---

## 0. TL;DR（七条判断）

1. **经典RefCOCO/+/g基准已经饱和且本身有噪声**：监督微调模型在RefCOCO val达92-94%（CogVLM 92.44%、InternVL2.5-78B 93.7%、Florence-2-large-ft 93.4%），而Ref-L4（2024-06）实测三个基准的**人工标注错误率分别达14%/24%/5%**——"过93分"与"真的看懂了"已脱钩，评测正迁移向Ref-L4/Ref-Adv（ICLR 2026，最强MLLM从90%+跌至~68%）/反事实C-RefCOCO等更难基准。
2. **范式已从"专用检测器"转向"MLLM生成式grounding"**：Qwen2.5-VL-72B以生成式零样本达到RefCOCOg val 89.9 / RefCOCO val 92.7，且**同时输出bbox和point、支持JSON/XML格式、原生绝对坐标**——这使"文本→区域绑定"可以直接嵌入文档解析管线（QwenVL HTML每个元素带data-bbox），对SRS图文关联是即插即用的能力。
3. **开放词汇检测谱系的精度阶梯清晰**：GLIP(CVPR 2022, 49.8 AP zero-shot COCO) → Grounding DINO(ECCV 2024, 52.5 AP) → Grounding DINO 1.5 Pro(2024, 54.3 AP) → DINO-X Pro(2024-11, 56.0 AP, LVIS-minival 59.8)。**开源断层在1.5之后**：1.5/1.6/DINO-X均为闭源API（IDEA DeepDataSpace），本地可部署的最强开源权仍是Grounding DINO（Apache 2.0）与YOLO-World（GPL-3.0，商用需授权）。
4. **区域分割已"组合化"**：SAM 2（Apache 2.0，checkpoints+训练代码全开源，SAM 2.1-large SA-V test 79.5 J&F）本身不懂文本；事实标准是**Grounded SAM 2管线**（Grounding DINO/Florence-2出框→SAM 2出mask+视频跟踪），0.8B的Florence-2（MIT许可）一个模型同时覆盖REC/phrase grounding/指代分割/OD/OCR，微调后RefCOCO RES mIoU 80.5。
5. **多模态LLM的grounding评测要用"文档战场"而非VQAv2**：DocVQA(ANLS)是GPT-4o/Claude/Qwen的公共标尺——Qwen2.5-VL-72B 96.4 > Claude 3.5 Sonnet-0620 95.2 > Gemini 1.5 Pro 93.1 > GPT-4o-0513 91.1；VQAv2已被闭源厂商弃报（ Florence-2-large-ft仍报81.7 test-dev）。**GPT-4o/Claude均无原生bbox/point输出**，指代理解只能靠prompt诱导坐标文本；原生grounding输出是Qwen-VL系列/Ferret/Molmo等开源模型的独有接口。
6. **中文+监控场景的REC是公开数据集空白**：arXiv检索"referring expression + Chinese"无任何中文REC基准（C-RefCOCO是**英文反事实**数据集，常被误认）；工程现实=**Qwen-VL系列是唯一原生中英双语grounding训练的开放模型族**（Qwen-VL 2023即以中英caption-box对训练），监控场景只能"Qwen2.5-VL/Qwen3-VL + 自建标注评测"。
7. **"看对了地方"的评测指标族已成型**：框级Acc@IoU≥0.5 / 点级pointing accuracy（预测点落入GT框比例，Park et al. 2018起源）/ 掩码级mIoU / 检测级AP。Qwen2.5-VL自建PointGrounding基准（72B 67.5 vs Molmo-72B 69.2）说明**点级评估已成为MLLM grounding的标配**；对本项目，点级+框级双指标+相对中心偏差是可落地的评测协议。

---

## 1. 经典任务：RefCOCO / RefCOCO+ / RefCOCOg 的当前最佳

### 1.1 基准本体

| 基准 | 出处 | 特点 | 规模要点 | 标注噪声(Ref-L4实测) |
|---|---|---|---|---|
| RefCOCO | Kazemzadeh et al., EMNLP 2014 | 短表达式，ReferitGame双人游戏采集 | 19,994图/142,210表达式/50,000对象 | **14%错误率** |
| RefCOCO+ | Yu et al., 2016 | 禁止位置词（纯外观描述） | 19,992图 | **24%错误率** |
| RefCOCOg | Mao et al., CVPR 2016 | 长描述（平均~8词），多对象 | 图片较小 | **5%错误率** |
| Ref-L4 | Chen et al., arXiv 2406.16866 (2024-06) | 45,341标注/365类/平均24.2词/词汇22,813 | 清洗版RefCOCO/+/g一并发布 | github.com/JierunChen/Ref-L4 |

> 噪声数字来源：Ref-L4论文摘要原文（"labeling error rates: 14% in RefCOCO, 24% in RefCOCO+, and 5% in RefCOCOg"）。

### 1.2 监督/微调路线当前最佳（已核实数字）

| 模型 | 论文/venue/年份 | RefCOCO val | RefCOCO+ val | RefCOCOg val | 权重/许可 | 来源 |
|---|---|---|---|---|---|---|
| CogVLM-17B | arXiv 2311.03079系（2023） | 92.44 | - | - | 开源 | 经Ref-L4论文(2406.16866)引用核实 |
| InternVL2.5-78B | OpenGVLab, arXiv 2412.05271, 2024-12 | 93.7 (testA 95.6/testB 92.5) | 90.4 | **92.7** (test 92.2) | 开源(HF OpenGVLab/InternVL2_5-78B；Qwen许可=Apache 2.0派生+品牌条款) | Qwen2.5-VL技术报告Table 6（第三方横评） |
| Florence-2-large-ft (0.77B) | arXiv 2311.06242, 2023-11（微软；venue未在线核实） | 93.4 (testA 95.3/testB 92.0) | 88.3 (testA 92.9) | **91.2** (test 91.7) | **MIT**, HF | HF microsoft/Florence-2-large模型卡 |
| UNINEXT (0.74B) | CVPR 2023 | 92.6 | 85.2 | 88.7 | 开源 | Florence-2模型卡引用 |
| Ferret-13B | arXiv 2310.07704, ICLR 2024 | 89.5 | 82.8 | 85.8 | 开源(Apple ml-ferret) | Florence-2模型卡引用 |
| Grounding DINO (Swin-L, RefC微调) | arXiv 2303.05499, ECCV 2024 | 90.6 | 88.2 | 86.1 | Apache 2.0 | Qwen2.5-VL Table 6 |
| PolyFormer | CVPR 2023 | 90.4 | 85.0 | 85.8 (RES mIoU 76.9) | 开源 | Florence-2模型卡引用 |

**结论**：RefCOCOg val的可信区间已到**91-93%**（InternVL2.5-78B 92.7 / Florence-2-ft 91.2）。2025-2026的AAAI/ICML论文（C³VG AAAI 2025、CoLA ICML 2026）声称继续提升，但逐一数字未经本次在线核实，未收录；增量空间公认只剩<2个点，社区已转向更难基准（见1.3）。

### 1.3 零样本/生成式路线（MLLM as-released，不微调RefCOCO）

| 模型 | RefCOCO val | RefCOCOg val | 说明 |
|---|---|---|---|
| Qwen2.5-VL-72B | 92.7 | 89.9 | 生成式输出绝对坐标bbox |
| Qwen2.5-VL-7B | 90.0 | 87.2 | |
| Qwen2.5-VL-3B | 89.1 | 85.2 | |
| Gemini 1.5 Pro | 73.2 | 75.2 | 闭源API |
| Kosmos-2 (2023) | 52.3 | 60.6 | MLLM grounding的开端 |
| Florence-2-large (零样本) | 56.3 | 68.0 | |
| GroundingAgent (AAAI 2026, arXiv 2511.19516) | 平均65.1（RefCOCO/+/g） | - | 无微调agentic：检测器+MLLM+LLM迭代推理；用原始query替换MLLM caption后选择阶段~90% |

> 来源：Qwen2.5-VL技术报告Table 6与Florence-2 HF模型卡（两处独立来源可互校）。

### 1.4 2025-2026动态（已核实）

- **GroundingAgent**（arXiv 2511.19516, AAAI 2026）：training-free agentic grounding范式确立，"检测器提候选+LLM语义/空间推理筛选"，零样本平均65.1%，且全链路可解释。
- **CuRPO**（arXiv 2511.13924, AAAI 2026 Oral）：RL+CoT路线，gIoU奖励+课程学习，RefCOCO较Visual-RFT提升至+12.52 mAP——**RL微调MLLM grounding**是当前最活跃方向。
- **UniRES++**（arXiv 2504.01954）：多粒度RES统一模型，发布**MRES-32M**（3200万mask+caption，100万图，部分级grounding最大数据集）与RefCOCOm基准。
- **Ref-Adv**（arXiv 2602.23898, ICLR 2026）：对抗性REC基准——抑制"短表达式/少干扰物/冗余描述"三类捷径后，**在RefCOCO上90%+的模型显著下跌**（论文结论；中文社区报道称最强模型仅~68%，此百分比未经原文核实）。
- **IAG**（arXiv 2508.09456, CVPR 2026）：对VLM grounding的**多目标后门攻击**（LLaVA/InternVL/Ferret, ASR最高），grounding管线的安全风险开始被系统研究。

---

## 2. 开放词汇检测+Grounding：GLIP / Grounding DINO / YOLO-World

| 维度 | GLIP | Grounding DINO | Grounding DINO 1.5 / 1.6 | DINO-X | YOLO-World |
|---|---|---|---|---|---|
| 论文/venue/年份 | arXiv 2112.03857, **CVPR 2022 Oral + Best Paper Finalist** | arXiv 2303.05499, **ECCV 2024** | 1.5: arXiv 2405.10300 (2024-05)；1.6: 2024-12（无独立论文） | arXiv 2411.14347 (2024-11) | arXiv 2401.17270, **CVPR 2024** |
| 机构 | Microsoft | IDEA Research | IDEA Research | IDEA Research | 腾讯AI Lab+HUST |
| zero-shot COCO AP | 49.8（GLIP-L；微调60.8） | **52.5**（Swin-L论文值）；开源T=48.4/B=56.7 | Pro **54.3** | Pro **56.0** | -（评测以LVIS为主） |
| LVIS AP | 26.9 (APr, zero-shot) | - | Pro 55.7 (minival zs)；Edge 36.2 @75.2FPS(TensorRT) | minival 59.8 / val 52.4；稀有类63.3(+5.8 SOTA) | 论文35.4@52FPS(V100)；V2.1-L(800)=28.3，X(640)=28.6 |
| RefCOCOg val | - | 86.1（RefC微调后） | - | - | - |
| ODinW | GLIP-L 51.2 | 26.1 (zs, 论文) | - | - | - |
| 权重可用性 | HF harold/GLIP（仓库2026-10已归档只读） | HF IDEA-Research/grounding-dino-tiny(接入transformers)+GitHub权重 | **闭源，仅API**（deepdataspace.com, pip dds-cloudapi-sdk V2，需token） | **闭源，仅API** | HF wondervictor/YOLO-World-V2.1 + ONNX/TFLite INT8 |
| 许可证 | **MIT** | **Apache 2.0** | API商用条款 | API商用条款 | **GPL-3.0**（商用需联系 yixiaoge@tencent.com） |
| 特色 | 检测短语统一为grounding预训练 | 语言引导查询选择+跨模态解码器；被Qwen2.5-VL用作**自动标注机** | Edge版面向部署；SAHI切片推理支持4K密集小目标 | 文本/视觉/定制/免提示四种prompt；Grounding-100M训练 | **prompt-then-detect重参数化**：词汇嵌入离线编译进模型，在线零开销 |

**选型判断**（对本项目）：
1. **本地部署优先Grounding DINO（Apache 2.0）**：中文类别词可直接输入（"接口框 . 数据流 . 服务器 ."式提示），48.4 AP零样本+RefC微调能力，transformers一行加载。
2. **要速度/边缘部署选YOLO-World**（V2.1-L 800: LVIS-mini 35.2 AP, 6.6k stars），但GPL-3.0对商用集成有传染性风险。
3. **要最高精度走DINO-X API**（闭源、可复现性差，与本项目runs协议的本地可复现原则冲突——只适合离线对比实验，不适合进主管线）。
4. Grounding DINO 1.5/1.6/DINO-X均**无公开权重**，论文数字无法独立复现，引用时须注明"自报数字"。

---

## 3. 开放词汇分割：SAM 2 / Grounded SAM 2 / Florence-2

### 3.1 SAM 2（Meta FAIR, 2024-08）

| 维度 | 内容 |
|---|---|
| 论文 | arXiv 2408.00714, "SAM 2: Segment Anything in Images and Videos" |
| 能力 | 可提示视觉分割（点/框/mask提示），流式记忆的video transformer；图像视为单帧视频 |
| checkpoint指标 | SAM 2.1-large: **SA-V test 79.5 J&F**, MOSE val 74.6, LVOS v2 80.6, 224.4M参数, 39.5 FPS (A100)；tiny 38.9M/91.2 FPS；比SAM精度更高且**快6倍**（论文摘要） |
| 关键事实 | 图像分割比SAM准且快6倍；视频分割交互次数比先前方法少3倍 |
| 权重/API | GitHub facebookresearch/sam2 + HF facebook/sam2-hiera-*（9月SAM 2.1改进版）；**训练/微调代码+web demo全部开源** |
| 许可证 | **Apache 2.0**（checkpoints、demo代码、训练代码均是；SA-V数据集另有条款） |
| 语义盲区 | SAM 2**不理解文本**——必须由上游模型（Grounding DINO/Florence-2）把文本转成框/点提示 |

### 3.2 Grounded SAM 2（IDEA-Research, 2024-08）

| 维度 | 内容 |
|---|---|
| 形态 | GitHub仓库（无独立论文，引用Grounded SAM arXiv 2401.14159），3.8k stars，138 commits持续维护 |
| 管线 | Grounding DINO/1.5/1.6/DINO-X/Florence-2 出文本→框，SAM 2 出mask并**跨视频跟踪任意ID物体** |
| 亮点 | ①Florence-2全任务管线（phrase grounding/RES/OD/dense caption→SAM 2分割）；②**caption+phrase grounding自动标注闭环**（先<CAPTION>再<CAPTION_TO_PHRASE_GROUNDING>，免人工标注）；③SAHI切片推理处理4K密集小目标；④首帧grounding后全程跟踪（点/框/mask三种prompt） |
| 许可证 | Apache 2.0（+组件许可：Grounding DINO Apache 2.0 / SAM 2 Apache 2.0 / cctorch BSD-3） |
| 对本项目 | SRS接口图/架构图的**元素级mask提取**与"图-文字对应区域"证据链构建的事实标准工具链 |

### 3.3 Florence-2（Microsoft, 2023-11）

| 维度 | 内容 |
|---|---|
| 论文 | arXiv 2311.06242 "Florence-2: Advancing a Unified Representation for a Variety of Vision Tasks" |
| 规模 | base 0.23B / large 0.77B（seq2seq生成式） |
| grounding能力 | `<CAPTION_TO_PHRASE_GROUNDING>`(caption短语→框)、`<REFERRING_EXPRESSION_SEGMENTATION>`(指代文本→mask)、`<OPEN_VOCABULARY_DETECTION>`、`<OD>`、`<DENSE_REGION_CAPTION>`、`<OCR_WITH_REGION>` |
| 零样榜 | RefCOCO val 56.3 / RefCOCOg val 68.0 / Flickr30k R@1 84.4 / COCO OD 37.5（large） |
| 微调后 | **RefCOCO val 93.4 / RefCOCOg val 91.2 / RES mIoU 80.5** / COCO 43.4 / VQAv2 81.7 / TextVQA 73.5（large-ft） |
| 权/API | HF microsoft/Florence-2-{base,large}(-ft)，vLLM/SGLang可服务化 |
| 许可证 | **MIT** |
| 对本项目 | 0.77B本地单卡可跑；**caption→grounding→caption自动标注闭环**是构建SRS图-文训练数据的最低成本路径（0.1B样本继续预训练的HF版COCO OD 39.8） |

> 补充（RES侧）：指代分割(RES)的监督SOTA参照PolyFormer 76.9 mIoU（CVPR 2023），Florence-2-large-ft 80.5 mIoU已超过它；LISA等2024工作未在本次会话核实，未收录。

---

## 4. 多模态LLM的grounding能力：Qwen2.5-VL / GPT-4o / Claude

### 4.1 Qwen2.5-VL（arXiv 2502.13923, 2025-02, Apache 2.0）

| 维度 | 核实数据 |
|---|---|
| 尺寸 | 3B / 7B / 72B（2025-01-28发布）+ 32B（2025-03） |
| grounding机制 | **绝对坐标训练**（不用归一化坐标，原生感知空间尺度）；bbox+point双输出；JSON/XML格式；10000+类开放词汇检测数据 |
| REC | RefCOCO val 92.7 / testA 94.6 / testB 89.7；RefCOCO+ val 88.9；**RefCOCOg val 89.9** / test 90.3（72B，生成式） |
| point级 | 自建PointGrounding基准 67.5（72B）；CountBench计数 93.6 |
| 检测 | ODinW-13 43.1 mAP（72B，zero-shot生成式） |
| 文档战场 | **DocVQA test ANLS 96.4** / InfoVQA 87.3 / ChartQA 89.5 / OCRBench 885 / CC-OCR 79.8 / OCRBench_v2 en 61.5（72B） |
| 中文 | **MMBench-CN 87.9**（72B）；SFT数据中英为主 |
| 关键架构 | ViT从零训练+窗口注意力、原生动态分辨率、MRoPE对齐绝对时间、4.1T token预训练 |
| 文档grounding | **QwenVL HTML格式：每个段落/表格/图表/公式/图片caption均带data-bbox="x1 y1 x2 y2"**——整页文档的结构化定位输出 |
| grounding训练数据 | PixMo(Molmo pointing) + 公开检测/分割数据转pointing + Grounding DINO/SAM自动合成 |
| 许可/权重 | Apache 2.0，HF/ModelScope，AWQ/GPTQ量化版，HF下载量月均550万+(7B) |

### 4.2 Qwen3-VL（paper arXiv 2511.21631, 2025-09/11, Apache 2.0）——当前最新

- 尺寸：2B/4B/8B/32B/30B-A3B(MoE)/235B-A22B(MoE)，Instruct+Thinking双版本；Interleaved-MRoPE+DeepStack+时间戳对齐。
- grounding：官方cookbook明确**2D grounding（相对坐标，框+点+标注组合任务）与3D grounding（室内外物体3D框）**；GUI grounding（ScreenSpot系）与agent定位（移动端/电脑操作）成为一等能力。
- 2026-02 WWW论文实测：对Qwen2.5-VL-32B做两阶段点击微调，单点击任务成功率86%→94%——**元素定位不准是VLM agent主要失败模式之一**，微调可显著修复。

### 4.3 GPT-4o / Claude（闭源）

| 维度 | GPT-4o (0513) | Claude 3.5 Sonnet (0620) | Gemini 1.5 Pro |
|---|---|---|---|
| DocVQA test ANLS | 91.1 | **95.2** | 93.1 |
| InfoVQA | 80.7 | 74.3 | 81.0 |
| ChartQA | 86.7 | 90.8 | 87.2 |
| OCRBench | 736 | 788 | 754 |
| MMBench-CN | 82.1 | 83.5 | - |
| VQAv2 | **官方未报告**（前沿厂商已弃报；开源侧Florence-2-ft 81.7/Qwen2.5-VL-72B 84.9 TextVQA） | 未报告 | 未报告 |
| 原生grounding输出 | **无**（无bbox/point token，需prompt诱导坐标文本，解析易碎） | 无 | Gemini 1.5 Pro可输出bbox但精度低（RefCOCO val 73.2 vs Qwen 92.7） |

> 来源：全部取自Qwen2.5-VL技术报告Table 5/6的统一评测（第三方横评，GPT-4o为0513版、Claude为3.5 Sonnet-0620版；OpenAI/Anthropic自家卡片口径可能不同——如OpenAI博客口径的DocVQA约94-95区间，未逐一核实，以Qwen表为准并注明出处）。
> 关键结论：**闭源旗舰在"看文档答题"上与Qwen2.5-VL-72B互有胜负，但在"输出区域坐标"上无原生接口**——若评测协议要求机器可读的定位证据，闭源API只能输出自然语言描述再行解析，这是结构化grounding任务选开源模型的硬理由。

### 4.4 相关开源grounding-MLLM（经Florence-2模型卡/Qwen报告核实）

- **Ferret**（arXiv 2310.07704, ICLR 2024, Apple）：混合区域表示（离散坐标+连续特征），接受**点/框/自由形状**输入；GRIT指令集1.1M样本含95K难负例；RefCOCO val 89.5。后续：Ferret-v2(2404.07973任意分辨率)、Ferret-UI(2404.05719)/Ferret-UI 2(2410.18967, ICLR 2025)专攻UI grounding。
- **Kosmos-2**（arXiv 2306.14824, Microsoft 2023）：以markdown链接"[文本span](坐标token)"表示指代，GrIT数据，RefCOCO val 52.3——MLLM生成式grounding的起点。
- **Molmo/PixMo**（arXiv 2409.17146, AI2 2024）：**全开放（权重+数据+代码）**；PixMo含不依赖外部VLM的2D pointing数据集；Molmo-72B人类评测优于Claude 3.5 Sonnet/Gemini 1.5 Pro，仅次于GPT-4o；PointGrounding 69.2（72B）。
- **Set-of-Mark**（arXiv 2310.11441, Microsoft 2023）：SAM/SEEM分区域编号叠加标记图喂给GPT-4V，**零样本RefCOCOg超过当时全监督SOTA**——"提示工程替代训练"路线的代表（microsoft/SoM开源）。
- **InternVL2.5-78B**（OpenGVLab 2024-12，开源）：RefCOCOg val 92.7（含grounding微调数据）、DocVQA 95.1——开源侧文档+grounding双强的Qwen主要对手（数字引自Qwen2.5-VL Table 5/6）。

---

## 5. 中文监控场景的grounding：数据集与模型

### 5.1 中文REC数据集：公开文献空白（本次核实的负结论）

- arXiv全文检索 `referring expression + Chinese`（abs字段，20条）：**无任何中文指代表达理解基准**，命中均为NLP指称生成(REG)论文（OntoNotes中英RFS等）。
- 常被误引的**C-RefCOCO/+/g**（github Glacier0012/CREC, CVPR 2024, Yu & Li, pp.13438-13448, Apache 2.0）：C=**Counterfactual（反事实）**，英文数据集——在RefCOCO/+/g上构造"属性词不存在于图中"的反事实样本（正常:反事实=1:1，如C-RefCOCO train 61870/val 15566），测的是REC模型的否定/反事实推理而非中文。
- 中文多模态基准侧：**MMBench-CN**（MMBench的中文版，test 87.9被Qwen2.5-VL-72B报告）证明中文多模态理解评测存在，但**不含区域级grounding任务**；BAAI FlagEval平台提供RefCOCO/+/g的visual grounding评测赛道（英文原版数据的平台化，非中文）。

### 5.2 中文grounding模型侧：Qwen-VL系列是唯一原生双语族

- **Qwen-VL**（arXiv 2308.12966, 2023-08）：摘要明确以"multilingual multimodal cleaned corpus"+**image-caption-box三元组对齐**获得grounding能力——中英双语grounding训练自第一代即确立。
- **Qwen2.5-VL**（2502.13923）：SFT指令数据"primarily Chinese and English"；MMBench-CN 87.9、OCRBench_v2中文 63.7（72B，超Gemini 1.5 Pro中文20.6点）——中文文本+坐标输出质量是开源最强。
- 实务结论：**"中文监控场景grounding"= 无现成基准 + 有可用模型**。可行技术栈：
  1. Qwen2.5-VL-7B（中文指代→bbox/point，Apache 2.0，本地）为主通道；
  2. Grounding DINO（中文类别词翻译后作text prompt）作对照通道；
  3. 评测协议自建：中文指代描述→预测框 vs 人工框（Acc@0.5+pointing accuracy双指标，见§6）。
- 监控领域提示：监控画面典型难点（小目标、密集人群、夜间低光、视角畸变）在RefCOCO系分布之外；Qwen3-VL的SAHI式高分辨率切片推理（Grounded SAM 2仓库方案）是处理4K监控帧的已验证工程手段。若需视频时序跟踪，SAM 2的跨帧跟踪+Qwen3-VL视频grounding（时间戳级事件定位）组合可用。

---

## 6. 中心点定位评估：如何评估模型"看对了地方"

### 6.1 指标族谱（按输出形态）

| 输出形态 | 指标 | 定义 | 代表使用者（已核实） |
|---|---|---|---|
| 框 | **Acc@IoU≥0.5**（Pr@0.5） | 预测框与GT框IoU≥0.5判对，报总体精度 | RefCOCO/+/g全系（专用模型与MLLM通用） |
| 框 | mean IoU / gIoU | 平均交并比；gIoU对"预测完全miss"给负梯度 | CuRPO用gIoU作RL奖励 |
| 框 | mAP（APr/APc/APf） | 检测式平均精度，LVIS按稀有/常见/频繁类分层 | GLIP/GDino/YOLO-World/LVIS、ODinW-13 |
| **点** | **pointing accuracy**（点入率） | 预测点落在GT框/mask内的样本比例 | 起源：Park et al. "Attentive Explanations"（CVPR 2018, arXiv 1612.04757）"point to the evidence"；现役：**Qwen2.5-VL PointGrounding**（67.5/72B）、Molmo/PixMo（69.2/72B） |
| 点 | 相对中心偏差 | 预测点与GT质心的归一化距离分布（对"差多少"敏感，不只是对错） | 常作补充诊断指标（协议自定） |
| 掩码 | mIoU（overall/oIoU） | 预测mask与GT的IoU | RES任务（PolyFormer 76.9、Florence-2-ft 80.5） |
| 掩码 | J&F | 视频对象分割的region质量+边界质量 | SAM 2（SA-V test 79.5） |
| 组合 | precision/recall@box_threshold | 开放词汇检测的置信度阈值曲线 | Grounding DINO（box+text双阈值机制） |

### 6.2 评测方法学警示（2024-2026的核心教训）

1. **基准噪声**（Ref-L4, arXiv 2406.16866）：RefCOCO/+/g标注错误率14%/24%/5%——评测前先过滤问题样本，否则±2点差异无意义。
2. **捷径学习**（Ref-Adv, arXiv 2602.23898, ICLR 2026）：表达式短+干扰物少+冗余描述→"不看文字也能选对"；MLLM在RefCOCO 90%+不等于指代理解成立。
3. **生成式grounding的解析陷阱**（工程经验+Qwen报告披露的训练细节）：MLLM输出坐标的**归一化约定（绝对像素vs相对0-1000）**、坐标系（xyxy vs xywh）、越界截断、非法token——评测实现不同可造成数点差异；Qwen2.5-VL选择绝对坐标训练正是为消除该歧义。
4. **数据泄漏**（Ref-L4 + 通用认知）：InternVL2.5/Qwen等大模型的预训练语料含RefCOCOg式数据，"零样本"实为"训练分布内"——横评必须区分"未见基准"与"未见任务"。
5. **pointing比box更严苛**：Qwen2.5-VL-72B框级89.9（RefCOCOg val）但点级仅67.5（PointGrounding）——**"看对区域"与"指准位置"是两个难度层**，评估VLM证据定位必须报告点级数字。

### 6.3 对本项目的落地协议建议（SRS图-文绑定评测）

- 双指标：**Acc@IoU≥0.5**（绑定对/错）+ **pointing accuracy**（证据中心点是否落在标注元素内）；
- 报告**相对中心偏差**的中位数/P90，用于区分"绑定对但偏"与"完全错"；
- 对生成式模型统一坐标协议（绝对像素、xyxy、图像原始分辨率），解析失败率单列；
- 抽样人工复核≥10%（Ref-L4的14-24%噪声教训：不清洗的自动评测不可信）；
- 分层报告：自然图像（RefCOCOg式长描述）vs 文档图（SRS框图/接口图元素）——后者分布外，需自建小规模金标。

---

## 7. 汇总速查表（论文/venue/年份/指标/权重/API/许可）

| 模型/系统 | 论文 | venue/年份 | 关键指标 | 权重/API | 许可证 |
|---|---|---|---|---|---|
| GLIP | arXiv 2112.03857 | CVPR 2022 (Oral, Best Paper Finalist) | COCO zs 49.8 AP；LVIS 26.9 APr | HF权重（repo已归档） | MIT |
| Grounding DINO | arXiv 2303.05499 | ECCV 2024 | COCO zs 52.5；RefCOCOg val 86.1(微调)；ODinW zs 26.1 | GitHub+HF(IDEA-Research/grounding-dino-tiny) | Apache 2.0 |
| Grounding DINO 1.5 Pro/Edge | arXiv 2405.10300 | 技术报告 2024-05 | Pro: COCO 54.3/LVIS-mini 55.7；Edge: 36.2 AP@75.2FPS | **仅API**(deepdataspace) | 闭源（商用API条款） |
| DINO-X Pro | arXiv 2411.14347 | 技术报告 2024-11 | COCO 56.0/LVIS-mini 59.8/LVIS 52.4 | **仅API** | 闭源 |
| YOLO-World | arXiv 2401.17270 | CVPR 2024 | LVIS 35.4 AP@52FPS；V2.1-X 28.6 | HF wondervictor/YOLO-World-V2.1 | **GPL-3.0** |
| SAM 2 / 2.1 | arXiv 2408.00714 | 2024-08 (Meta) | SA-V test 79.5 J&F；比SAM快6倍 | GitHub+HF facebook/sam2-hiera-* | Apache 2.0 |
| Grounded SAM 2 | (repo, 引用arXiv 2401.14159) | 2024-08 (IDEA) | 文本→框→mask→跟踪管线 | GitHub | Apache 2.0(组件) |
| Florence-2 | arXiv 2311.06242 | 2023-11 (微软, 0.23B/0.77B) | zs RefCOCOg 68.0；ft 91.2/RES 80.5 | HF microsoft/Florence-2-* | **MIT** |
| Qwen2.5-VL | arXiv 2502.13923 | 技术报告 2025-02 | RefCOCOg 89.9；DocVQA 96.4；PointGrounding 67.5 | HF/ModelScope(3B/7B/32B/72B) | Apache 2.0 |
| Qwen3-VL | arXiv 2511.21631 | 技术报告 2025-11 | 2D/3D/GUI grounding cookbook | HF/ModelScope(2B~235B MoE) | Apache 2.0 |
| InternVL2.5-78B | arXiv 2412.05271 | 技术报告 2024-12 | RefCOCOg 92.7；DocVQA 95.1（Qwen表引） | HF OpenGVLab/InternVL2_5-78B | Qwen许可（Apache 2.0派生） |
| Ferret | arXiv 2310.07704 | ICLR 2024 | RefCOCO val 89.5 | GitHub apple/ml-ferret | 研究用途（Apple ml license） |
| Molmo/PixMo | arXiv 2409.17146 | 2024-09 (AI2) | PointGrounding 69.2；人评仅次GPT-4o | molmo.allenai.org 全开放 | Apache 2.0 |
| Kosmos-2 | arXiv 2306.14824 | 2023 (Microsoft) | RefCOCO val 52.3 | aka.ms/kosmos-2 | 开源（unilm仓库, 未逐条核实） |
| GroundingAgent | arXiv 2511.19516 | AAAI 2026 | zs 平均65.1 (RefCOCO/+/g) | 论文代码 | 待查 |
| CuRPO | arXiv 2511.13924 | AAAI 2026 Oral | RefCOCO +12.52 mAP vs Visual-RFT | github qyoung-yan/CuRPO | 待查 |
| C³VG | arXiv 2501.06710 | AAAI 2025 | REC+RIS联合SOTA（自报） | github Dmmm1997/C3VG | 待查 |
| UniRES++/MRES | arXiv 2504.01954 | 2025-04 | MRES-32M(3200万mask)多粒度SOTA | github Rubics-Xuan/MRES | 待查 |
| Ref-L4 | arXiv 2406.16866 | 2024-06 | RefCOCO噪声14/24/5%；新基准45,341标注 | github JierunChen/Ref-L4 | 开源 |
| Ref-Adv | arXiv 2602.23898 | ICLR 2026 | MLLM从90%+显著跌落 | 论文 | 待查 |
| C-RefCOCO/+/g (CREC) | CVPR 2024 (Yu & Li) | 2024 | 反事实REC（英文） | github Glacier0012/CREC | Apache 2.0 |
| Set-of-Mark | arXiv 2310.11441 | 2023 (Microsoft) | GPT-4V+SoM零样本超当时SOTA | github microsoft/SoM | 开源（未逐条核实） |
| IAG(后门攻击) | arXiv 2508.09456 | CVPR 2026 | 多目标后门ASR最高 | github lijunxian111/IAG | 待查 |

**未能在线核实而不收录**：ECCV 2024 "Modulating Pre-trained VLMs with GPU-efficient attention"（arXiv/作者检索均无命中，PWC已下线无法交叉验证其RefCOCOg val 92.x自报值）；LISA(GLMM系)指代分割系列；GLUE/PINTO等pointing评测早期论文的具体ID。引用上述工作前需自行到ECCV/NeurIPS官网核对。

---

## 8. 对本项目的意义（方向A：SRS图文条目聚合）

1. **"文本→区域绑定"已不再需要训练专用模型**：Qwen2.5-VL-7B（Apache 2.0、本地可跑、8.3B参数）即可接受"3.2.1节数据获取模块的接口图"这类中文指代表达并输出绝对坐标bbox/point+JSON——图片通道的条目聚合（方向A的图片侧证据生产）可从"纯VLM描述"升级为"**VLM定位+结构化证据坐标**"，使OCR框/表行/bbox进入同一坐标系做实体对齐（与`diagram_extraction_technology_spectrum.md`的UDG统一schema方案直接衔接）。
2. **自动标注闭环已成熟**：Florence-2 caption→phrase grounding→（Grounded SAM 2）分割，或Grounding DINO作标注机（Qwen团队自己的用法）——16份SRS的接口图/框图元素可在零人工标注下获得silver框标签，再按`tools/`既有runs协议评估抽检质量。
3. **评测协议必须点级+框级双指标并抽样人检**：RefCOCO噪声14-24%、Ref-Adv捷径、点级(67.5)远低于框级(89.9)三个证据共同表明——"VLM看对了地方"要用pointing accuracy+Acc@0.5+人工抽检三件套下结论，不能只看单一零样本分数。这与本项目"VLM降级为抽检/仲裁位"的架构决策（场景5）一致：VLM定位输出作为**证据坐标**进入级联，而非作为最终判定。
4. **中文监控场景若立项=数据集贡献机会**：中文REC基准空白+Qwen原生双语grounding能力，意味着"中文监控/工程图纸指代理解基准"本身可作为副产品贡献（但与本SRS主线无关，仅作记录）。
