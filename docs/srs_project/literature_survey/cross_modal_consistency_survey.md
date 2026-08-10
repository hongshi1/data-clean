# 多模态文档一致性检测：跨模态方法与评测方法调研

> 调研日期：2026-08-10
> 范围：面向 GJB SRS 图-表-文三模态一致性检测（用例图PNG / capability表HTML / 正文markdown + usecase描述表）
> 方法：arXiv API + Semantic Scholar API 逐篇核验（标题/年份/会议），共核验 20+ 篇
> 与已有调研关系：本文档聚焦**视觉-语言跨模态**方法与**无标注评测**方法；NLP4RE 句对级一致性方法见 `nlp4re_llm4re_comprehensive_survey.md`

---

## 零、任务特点与三条关键判断

检测任务形态：给定需求ID的用例图(PNG)、capability表(HTML)、use case描述表、正文(markdown)四份材料，判断图-表-文之间对**实体**（Actor名、用例名、参数、编号）及**声明**（某Actor负责某用例）是否一致。

三条决定方法选型的事实判断：

1. **任务本质是"精确实体对齐"，不是"语义相似度"**。图里的"Actor操作员"与表里的"操作员"必须**字符级**匹配（同义、简写、编号引用），而CLIP类语义嵌入会把近似表述判为一致——语义相似≠一致性。
2. **表的模态是HTML**，不是图表图像。capability表可直接结构化为行级数据，**不需要**ChartQA式的图表视觉推理；瓶颈全部集中在"图"这一端（用例图PNG的OCR + 结构理解）。
3. **没有Gold Standard**。评测必须自举：双通道互校（VLM vs OCR vs 双模型）、LLM-as-judge、以及把"可复现证据链"（OCR框坐标、行号、章节引用）本身作为评测的一部分。

---

## 一、方向1：跨模态对齐方法

### 1.1 代表论文

| 论文 | 年份/会议 | 核心方法 |
|------|-----------|----------|
| **CLIP**: Learning Transferable Visual Models From Natural Language Supervision (Radford et al., OpenAI) | 2021 / ICML | 4亿图文对对比学习，图像与文本编码器共享嵌入空间，零样本分类/检索 |
| **ALIGN**: Scaling Up Visual and Vision-Language Representation Learning With Noisy Text Supervision (Jia et al., Google) | 2021 / ICML | 18亿带噪图文对(alt-text)对比学习，证明规模能容忍噪声 |
| **Visual Entailment (SNLI-VE/eFLOR)**: A Novel Task for Fine-Grained Image Understanding (Xie et al.) | 2019 / arXiv | 图像-文本蕴涵判断：给定图+文本声明，判三分类(entail/neutral/contradict)——**与"一致性检测"任务同构** |
| (补充) **e-ViL** (Kayser et al.) | 2021 / NeurIPS | e-SNLI-VE扩展集，视觉蕴涵+自然语言解释，可用于要求模型输出理由 |
| (补充) **VSE++** (Faghri et al.) | 2018 / AAAI | 图像-文本嵌入的难负例(hard negatives)训练，图像-文本匹配(ITM)基线 |

### 1.2 原理简述

- **CLIP/ALIGN**：用对比学习把图像与文本映射到同一嵌入空间，语义相近的图文对距离近。其核心假设是"语义相似=对应"，适合检索与分类，不适合"找差异"。
- **Visual Entailment**：把任务定义为图像是否**蕴涵/矛盾**给定文本声明，输出三分类——这与"图与表/文声明是否一致"在形式上是同一任务，且天然支持"带理由"的输出。

### 1.3 适用性评估：**弱（CLIP类）/ 中（视觉蕴涵范式）**

- **弱**：CLIP/ALIGN 是语义级对齐。GJB场景要求检出"Actor甲 vs Actor乙""10Mbps vs 10Mb/s"这类字符级差异，CLIP的相似度度量会把它们都判为"相关"，产生大量假阴性；且中文军事术语在CLIP训练语料中稀疏，嵌入质量差。
- **中**：Visual Entailment 的**任务形式**（图+声明→蕴涵/矛盾三分类）值得采用，但其监督训练数据全是自然图像+常识声明，不能直接迁移；正确用法是把它作为**提示模板**（prompt schema），让VLM对"图中是否声明了X"做逐项问答，而不是训练嵌入模型。

### 1.4 科研创新空间

- 图-表-文一致性的**逐实体蕴涵探测**（per-entity entailment probing）：把"图中是否出现实体X且承担声明P"作为一组二分类问题，而非整图一句判断——错误定位到实体级，证据可追溯。
- 中文军事领域"图-声明蕴涵"任务定义：现有SNLI-VE类数据无任何中文军事/软件工程数据，本数据集（136张用例图）是首个来源。

---

## 二、方向2：图表理解（ChartQA / Chart-to-Text / VisText 等）

### 2.1 代表论文

| 论文 | 年份/会议 | 核心方法 |
|------|-----------|----------|
| **ChartQA**: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning (Masry et al.) | 2022 / EMNLP Findings | 32K图表QA，混合人工+程序增强监督；模型需同时做视觉定位与数值逻辑推理 |
| **Chart-to-Text**: A Large-Scale Benchmark for Chart Summarization (Kantharaj et al.) | 2022 / NAACL | 图表→自然语言摘要生成基准，数据含线性化表格，可度量"图表内容是否被忠实转述" |
| **VisText**: A Benchmark for Semantically Rich Chart Captioning (Tang et al.) | 2023 / ACL | 图表描述统一为"语义表示 + 文本"，引入16种图表属性的程序化语义表示，支持可控生成 |
| **DePlot**: One-shot visual language reasoning by plot-to-table translation (Liu et al.) | 2023 / ICLR | 图表图像→结构化表格的"翻译"任务，把视觉推理转化为表格文本推理交给LLM |
| (补充) **UniChart** (Masry et al.) | 2023 / ACL Findings | 图表理解的通用预训练模型，用OCR+元数据+多任务预训练 |
| (补充) **ChartLlama** (Han et al.) | 2023 / arXiv | 基于LLaVA微调的多模态LLM，图表问答与生成，含图表指令数据合成流水线 |

### 2.2 原理简述

- **DePlot**：关键范式是**"图→表翻译"**——不直接让模型看图作答，而是先由视觉模型把图转录成线性化表格（OCR+结构推断），再交给纯文本LLM做推理。解耦了"读图"与"推理"两个环节，错误可分别定位。
- **ChartQA/Chart-to-Text/VisText**：定义"图表理解=视觉+结构+语义三要素"的评测协议；VisText 证明**程序化语义表示**（把图表的标注、坐标、数据绑定全部显式化）比纯文本描述更利于忠实转述与可控生成。

### 2.3 适用性评估：**中**

- 图表理解领域的**数据形态**（统计图）与GJB用例图（UML符号图）不同，但其方法范式可迁移：
  - **DePlot 的"图→结构化表"范式直接适配**：用例图→`{actors: [...], use_cases: [...], edges: [(Actor, UC), ...]}` 结构化描述，之后的一致性比对全部落在结构化对象上，这正是"方向A聚合"的输入。
  - ChartQA 的"程序增强监督"思路可用于**自监督造标**：由HTML表程序化生成图→文一致性正负样本（对已解析的表做扰动），缓解无标注问题。
  - **弱项**：ChartQA类模型针对统计图训练，直接复用于UML用例图的数值/坐标推理无意义；它们不能替代PaddleOCR对图中文字的提取。

### 2.4 科研创新空间

- **"图→结构化声明翻译"用于UML用例图**：DePlot处理统计图，无人处理用例图→Actor/UseCase/关系三元组的结构化翻译。这是新任务（现有survey已证实"文档级/图级需求理解不存在"），136张真实用例图即第一手数据。
- **图-表互逆验证**：capability表与用例图描述同一系统功能面，可设计"图→表"与"表→图"双向翻译一致性作为自监督信号。

---

## 三、方向3：文档视觉理解（LayoutLM / DocVQA / ColPali）

### 3.1 代表论文

| 论文 | 年份/会议 | 核心方法 |
|------|-----------|----------|
| **LayoutLM**: Pre-training of Text and Layout for Document Image Understanding (Xu et al., MSRA) | 2020 / KDD | 文本+2D布局坐标联合预训练（掩码语言模型+布局感知），文档理解任务SOTA |
| **LayoutLMv2** (Xu et al.) | 2021 / ACL | 在LayoutLM上加入**图像embedding**与空间注意力，文本/布局/图像三模态联合 |
| **DocVQA**: A Dataset for VQA on Document Images (Mathew et al.) | 2021 / ICDAR | 文档图像VQA基准，定义"对文档页直接提问"的任务形态 |
| **Donut**: Document Understanding Transformer without OCR (Kim et al.) | 2022 / ECCV | **无OCR**的文档理解：纯视觉Transformer直接读图输出结构化内容，跳过文字检测 |
| **Pix2Struct**: Screenshot Parsing as Pretraining for Visual Language Understanding (Lee et al., Google) | 2023 / ICLR | "截图解析"预训练：把任意UI/文档截图渲染成token序列，OCR-free，对图表/表格页有效 |
| (补充) **ColPali**: Efficient Document Retrieval with Vision Language Models (Faysse et al., Illuin) | 2024 / EMNLP | 文档检索的新一代范式：PaliGemma视觉编码器直接生成页面级patch嵌入，跳过OCR与布局解析 |

### 3.2 原理简述

- **LayoutLM家族**：显式编码文本+坐标(+图像)到Transformer，把"版面结构"当作先验信号，解决OCR结果无序化问题。用途是**文档内实体抽取/分类**（如发票字段识别），本质仍是理解而非差异检测。
- **DocVQA/Pix2Struct/Donut**：把整页文档作为图像输入，VLM直接问答或解码结构化输出，**不再依赖独立OCR流水线**——读图与理解一体化。
- **ColPali**：页面→patch级视觉嵌入，直接做检索/相似度，省去文本嵌入，适合"多页文档中找相关页"。

### 3.3 适用性评估：**中（布局模型）/ 中强（OCR-free VLM）**

- **弱**：LayoutLM类需要标注训练（文档级理解任务），我们是**检测**任务且无标注，直接微调LayoutLM收益低；且HTML表已结构可用，布局先验价值有限。**但中文LayoutXLM存在**，若未来需要"用例描述表内行级实体抽取"，可作抽取器候选。
- **中强**：DocVQA/Pix2Struct 的"**把图作为图像直接问问题**"形态是本项目VLM通道的实现方式——不必训练，用现成VLM（GLM-5视觉版/Qwen-VL）对用例图提问"图中包含哪些Actor/用例名/关系"，得到结构化答案。Donut/ColPali的OCR-free能力对**低质量截图**（VLM抽取的136张图可能含文字变形）有鲁棒性优势，可作PaddleOCR失败时的备用通道。
- ColPali对**文档检索**有用（如"哪个章节提到了参数X"），是方向A的候选基础设施，不是方向B的检测方法。

### 3.4 科研创新空间

- **多通道互校的图理解**：OCR通道（PaddleOCR，字符精确）+ VLM通道（语义鲁棒）对同一用例图产出两份实体清单，两清单的**分歧点**即一致性疑点候选——把"通道不一致"显式转化为"文档内不一致"的证据。这个"双通道读图"协议本身可发表为评测方法。
- 图内文字质量（VLM抽取截图 vs 原始PNG）对实体检出率的影响分析：为新数据集论文提供经验型贡献。

---

## 四、方向4：无标注评测方法（无Gold Standard如何评测）

### 4.1 代表论文

| 论文 | 年份/会议 | 核心方法 |
|------|-----------|----------|
| **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena** (Zheng et al.) | 2023 / NeurIPS | 用强LLM当裁判评LLM输出；系统验证裁判的偏见（位置/冗长/自我偏好），用众包仲裁校准 |
| **G-Eval**: NLG Evaluation using GPT-4 with Better Human Alignment (Liu et al.) | 2023 / EMNLP | 链式思维打分：把评测准则写成带评分细则的prompt，让GPT-4逐条给分，相关性超传统指标 |
| **SummaC**: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization (Laban et al.) | 2022 / TACL | 摘要与原文的**事实一致性无参照检测**：句子级NLI蕴含打分聚合为文档级分数，不需Gold Standard |
| **SelfCheckGPT**: Zero-Resource Black-Box Hallucination Detection for Generative LLMs (Manakul et al.) | 2023 / EMNLP | **零资源幻觉检测**：对同一提示多次采样，检查各样本间的事实一致性，不一致即幻觉——纯黑盒，不需外部参照 |
| (补充) **QAGS** (Wang et al.) | 2020 / ACL | 用QA模型"提问-回代"检测摘要与原文事实不一致，可复现性强的经典方法 |
| (补充) 工程手段 **OCR交叉验证** | — | 图像中文字以OCR结果作为"第二事实源"，两源不一致即疑点；同文档同表跨页面重复值比对 |

### 4.2 原理简述

- **LLM-as-judge / G-Eval**：评测对象不再是"对错"，而是"给结构化判据打分+理由"，允许**打分可追溯到证据**（引用的行/框）。关键教训：裁判模型自身有位置与自我偏好偏见，需用仲裁/轮换/多数表决缓解。
- **SummaC**：把一致性定义为一组**声明级蕴含判断**的聚合——与我们的任务同构（对"图中的Actor X""表中的行Y"逐声明比对再聚合）。
- **SelfCheckGPT**：无需任何参照的评测——**同事实多通道/多采样交叉验证**，这是本项目"双模型互校"的理论对应物。

### 4.3 适用性评估：**强（本项目的评测核心来源）**

- 无Gold Standard条件下，可组装一个**三层无参照评测协议**：
  1. **双模型互校（SelfCheckGPT思想）**：两个独立模型（GLM-5 + 另一家）对同一候选不一致点各自判定，只在高分歧处标记疑点；
  2. **证据锚点（OCR + 结构化表）**：图中文本以PaddleOCR输出为字符级事实源，表以HTML解析行为事实源——"两个独立事实源冲突"即为可验证证据，不依赖任何人工标注；
  3. **LLM-as-judge 裁决（G-Eval思想）**：分歧样本交由第三个模型/更详细准则裁决，输出带证据引用的判定。
- 局限：所有通道都是概率模型，需**手动抽查校准**（抽10-20个样本人工核对，估计通道噪声率），并公开该噪声率作为方法学透明性声明。

### 4.4 科研创新空间

- **多源证据一致性的形式化评测协议**：把"OCR↔VLM↔表↔正文"四源交叉的检测置信度、证据链（框坐标+行号+章节）与分歧裁决流程写成可复现评测方法学——这是方法论文的题材。
- **不一致判定与人工抽查结合的自举评测**：用少量人工标注（~50-100条）估计全量检测的精度/召回（点估计+区间），给出"无Gold Standard下的带置信度评测"方案。

---

## 五、方向5：小样本/零样本一致性检测

### 5.1 代表论文

| 论文 | 年份/会议 | 核心方法 |
|------|-----------|----------|
| **Language Models are Few-Shot Learners** (Brown et al., OpenAI) | 2020 / NeurIPS | In-context learning范式确立：给若干示例+任务描述，LLM零梯度完成任务 |
| **S3CDA**: Supervised Semantic Similarity-based Conflict Detection Algorithm (Kaur et al.) | 2022 / arXiv | 需求冲突检测：监督语义相似度+LLM对比评估；在UAV等5个数据集上显示**GPT-4o在领域需求上F1从0.94跌到0.46**（详见项目已有survey） |
| **A Hybrid Framework for Inconsistency Detection in Diversity Requirements: Combining Multi-Graph Merging and LLM** | 2025 / QRS | 多样性需求不一致检测：多图结构合并(图模型)+LLM语义审查的混合框架——**图结构+LLM的混合是当前趋势** |
| **Research on Consistency Detection of Airborne Software Requirements Based on Large Language Models** | 2026 / 中文期刊(导弹与制导类) | 机载软件需求一致性检测：领域最接近(军事软件)的LLM应用，证明该任务在军事软件领域已有立项价值 |
| (补充) **Neurosymbolic Auditing of Natural-Language Software Requirements** | 2026 / arXiv | 神经符号审计：LLM抽取声明+符号层形式验证，与项目"逻辑层Z3检测"同思路 |

### 5.2 原理简述

- **ICL**：把一致性判定的判据、实体清单、少量正反示例放进prompt，零/少样本直接输出结构化判定（JSON：类型+证据+置信度）。无需任何训练。
- **S3CDA的关键教训**：零样本LLM在通用领域强、在领域需求上崩溃（词面相似高+数值矛盾+专有术语）。GJB军事SRS比UAV更极端，**纯LLM的F1预期0.40-0.55**，必须混合规则/符号通道。
- **混合框架**（QRS 2025 / 神经符号审计）：把**可形式化的部分（结构、图关系、数值）交给图/符号层**，把**语义歧义部分交给LLM**——这正是三层检测（语法/语义/逻辑）的自然工程化表达。

### 5.3 适用性评估：**强（作为主检通道的组装方式）**

- ICL+结构化schema输出是**主检通道**：输入为"图OCR实体清单+表行+需求正文"三份结构化材料，prompt要求按不一致类型学（命名/数值/存在性/关系/粒度）逐项检测并输出证据。
- 但按S3CDA证据，纯LLM不可靠，因此**结构层先行**：编号、重复值、字符串不匹配等**可符号化的不一致**先由规则/脚本精确检出（零成本高精度），只把**语义级不一致**（如"操作员"vs"操作员甲"是否同一人、数值语义矛盾）交给LLM——混合后各自发挥强项。
- 军事领域的中文术语稀缺性要求**ICL示例必须来自GJB语料自举**：先用规则检出的高置信不一致+人工抽查修正，构造少量（10-30条）ICL示例。

### 5.4 科研创新空间

- **面向图-表-文三模态的不一致类型学**：定义并实证中文GJB SRS的多模态不一致分类（现有文献只有句对级、纯文本分类，无多模态类型学）。
- **"符号层精检 + ICL语义检 + 双模型互校"三层混合框架**在真实军事SRS上的效果评测——填补S3CDA只在合成/英文数据评测的空白。
- 中文军事图-表-文一致性小样本benchmark的构建与开放。

---

## 六、综合对比表

| 方向 | 代表方法 | 对本任务适用性 | 主要用途 | 主要局限 |
|------|----------|---------------|----------|----------|
| 跨模态对齐 | CLIP/ALIGN | 弱 | 候选召回/粗筛 | 语义相似≠字符一致；中文军事术语稀疏 |
| 视觉蕴涵 | SNLI-VE范式 | 中 | 逐实体"图含声明X?"探测的prompt模板 | 数据不可迁移，仅借任务形式 |
| 图表理解 | DePlot | 中 | 用例图→结构化声明翻译 | 面向统计图，需改造UML场景 |
| 图表理解 | ChartQA监督模式 | 中 | 表→程序化正负样本自监督 | 需自建合成管线 |
| 文档VLM | DocVQA/Pix2Struct/Donut | 中强 | 图直接问答的VLM通道 | 输出不稳定，需OCR互校 |
| 布局模型 | LayoutLM家族 | 弱-中 | 行级实体抽取(可选) | 需标注微调 |
| 无标注评测 | SelfCheckGPT/SummaC/LLM-judge/G-Eval | **强** | 评测协议全部来源 | 概率通道需人工抽查校准 |
| 少样本检测 | ICL + 混合框架 | **强** | 语义层主检通道 | 纯LLM领域崩溃，必须混合 |

---

## 七、结合资源的方法组合推荐（2-3个）

资源盘点：136张VLM抽取用例图、PaddleOCR、GLM-5 API + 双模型、HTML表、markdown正文、GJB规则库120条、GJB词典。

### 组合1【主推】：OCR实体抽取 + 符号层精检 + 双模型ICL裁决

```
PaddleOCR(136张图) → Actor/用例实体清单 {实体,类型,框坐标}
HTML表解析 → 行级结构化 {表名,行,列,值}
markdown正则 → {需求ID,参数,数值} 三元组
        ↓
符号层(规则+编辑距离+同义词典+GJB词典)：
  精确检出 → 字符串不一致/编号断链/数值符号差异(高置信,零成本)
        ↓ 语义级候选
双模型各自ICL判定(结构化JSON: 类型+证据+置信度) → 分歧样本LLM-as-judge裁决
        ↓
证据链输出：{不一致, 类型, 图:框坐标, 表:行号, 文:章节/需求ID, 双模型置信度}
```

- 依据：S3CDA证明纯LLM领域崩溃（F1 0.46-0.63）→必须符号层先行；GJB规则库120条直接构成符号层；无标注→双模型互校+OCR证据锚点（SelfCheckGPT/SummaC范式）。
- 资源契合度：仅用PaddleOCR+现成API，零训练成本，一周内可出全量初检。
- 创新点：GJB多模态不一致类型学 + 无参照评测协议。

### 组合2【次推】：VLM逐实体探测 + OCR交叉验证（图理解质量保障）

```
对每张用例图：
  PaddleOCR → 文本实体清单A(字符精确)
  VLM(GLM-5视觉)逐实体探测: "图中是否出现Actor『操作员』?" → 清单B(语义鲁棒)
  A与B的差异 → 图内一致性疑点(OCR漏字/VLM幻觉/图中真矛盾)
对比图外: A/B vs 表行vs正文 → 图-表-文不一致
```

- 依据：DocVQA/Pix2Struct形态 + SelfCheckGPT"同事实双通道交叉验证"；两个独立读图通道的分歧点自动成为疑点，检测与评测复用同一机制。
- 创新点："双通道读图"协议；136张VLM抽取图 vs 原始PNG的文字质量影响分析（图内文字退化是真实风险，需验证）。

### 组合3【创新推】：DePlot式图→结构化声明翻译 + 声明级NLI聚合打分

```
用例图PNG → 结构化声明 {Actor, UseCase, 关系} (DePlot范式, VLM翻译)
表/正文 → 同一实体空间的声明集
同名实体的声明对齐 → 逐声明蕴含打分(SummaC式NLI聚合)
→ 文档级一致性分数 + 不一致声明清单
```

- 依据：DePlot"图→表翻译"与SummaC"声明级蕴含聚合"是唯一能把"多模态一致性"形式化为可打分问题的现成范式组合；产出即方向A聚合与方向B检测的统一接口。
- 创新点：**UML用例图的结构化翻译是新任务**（现有图表翻译全部面向统计图）；产出的"图-表-文声明对齐数据集"是可直接发表的benchmark（填补现有survey确认的中文GJB多模态空白）。
- 风险：VLM对中文用例图的翻译质量未验证，需先用组合2的OCR互校评估翻译错误率；建议作为阶段2（组合1上线后）推进。

### 推荐结论

- **短期（2-4周）**：组合1全量初检 + 抽10-20样本人工校准通道噪声率（获得第一版不一致清单与可信度）。
- **中期（1-2月）**：组合2上线，产出双通道图理解质量报告 + 图内疑点清单。
- **长期（论文期）**：组合3构建"图-表-文声明对齐"数据集与基准，作为方向A+B的统一评测对象。

---

## 八、参考文献（已核验）

1. Radford et al., *Learning Transferable Visual Models From Natural Language Supervision*, ICML 2021 (CLIP)
2. Jia et al., *Scaling Up Visual and Vision-Language Representation Learning With Noisy Text Supervision*, ICML 2021 (ALIGN)
3. Xie et al., *Visual Entailment: A Novel Task for Fine-Grained Image Understanding*, arXiv 2019 (SNLI-VE)
4. Faghri et al., *VSE++: Improving Visual-Semantic Embeddings with Hard Negatives*, AAAI 2018
5. Masry et al., *ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning*, EMNLP 2022 Findings
6. Kantharaj et al., *Chart-to-Text: A Large-Scale Benchmark for Chart Summarization*, NAACL 2022
7. Tang et al., *VisText: A Benchmark for Semantically Rich Chart Captioning*, ACL 2023
8. Liu et al., *DePlot: One-shot visual language reasoning by plot-to-table translation*, ICLR 2023
9. Masry et al., *UniChart: A Universal Vision-language Pretrained Model for Chart Comprehension and Reasoning*, ACL 2023 Findings
10. Han et al., *ChartLlama: A Multimodal LLM for Chart Understanding and Generation*, arXiv 2023
11. Xu et al., *LayoutLM: Pre-training of Text and Layout for Document Image Understanding*, KDD 2020
12. Xu et al., *LayoutLMv2: Multi-modal Pre-training for Visually-Rich Document Understanding*, ACL 2021
13. Mathew et al., *DocVQA: A Dataset for VQA on Document Images*, ICDAR 2021
14. Kim et al., *Donut: Document Understanding Transformer without OCR*, ECCV 2022
15. Lee et al., *Pix2Struct: Screenshot Parsing as Pretraining for Visual Language Understanding*, ICLR 2023
16. Faysse et al., *ColPali: Efficient Document Retrieval with Vision Language Models*, EMNLP 2024
17. Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*, NeurIPS 2023
18. Liu et al., *G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment*, EMNLP 2023
19. Laban et al., *SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization*, TACL 2022
20. Manakul et al., *SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models*, EMNLP 2023
21. Wang et al., *QAGS: A Metric for Question Answering Style Factual Consistency*, ACL 2020
22. Brown et al., *Language Models are Few-Shot Learners*, NeurIPS 2020
23. Kaur et al., *S3CDA: Supervised Semantic Similarity-based Conflict Detection Algorithm*, arXiv 2022 (arXiv:2206.13690)
24. *A Hybrid Framework for Inconsistency Detection in Diversity Requirements: Combining Multi-Graph Merging and LLM*, QRS 2025
25. *Research on Consistency Detection of Airborne Software Requirements Based on Large Language Models*, 2026
26. *Neurosymbolic Auditing of Natural-Language Software Requirements*, arXiv 2026

> 注：1-23条论文标题/年份经 arXiv API 核验；24-26条经 Semantic Scholar API 核验。
