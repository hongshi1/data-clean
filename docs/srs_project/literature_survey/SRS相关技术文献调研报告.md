# SRS 文档分析相关技术文献调研报告（10 大主题）

> 目标：围绕「军用 SRS（GJB 438C-2021）文档解析 + 参数化需求条目抽取 `{参数名, 运算符, 数值, 单位, 条目类型, 引用关系}`」项目，系统检索 10 个相关技术主题的关键论文、模型与工具。
>
> 检索方法：arXiv API（ relevance 排序）+ 已验证 arXiv ID 直查。所有标注 ✅ 的 arXiv ID 均经 API 二次核验存在；标注 ⚠️ 的为基于训练知识但未在本次 API 中核验（已注明出处）。优先收录 2022–2025 年工作，兼顾少量奠基性论文。
>
> 项目相关性评分（★1–5）针对本项目「中文军工 SRS 参数化需求抽取」场景。

---

## 主题 1：NLP for Requirements Engineering (NLP4RE) — 需求工程中的自然语言处理

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | Practical Guidelines for the Selection and Evaluation of NLP Techniques in Requirements Engineering | Sabetzadeh, Arora | TOSEM 2024 | 2401.01508 | ✅ |
| 2 | Natural Language Processing for Requirements Traceability | Guo, Steghöfer, Vogelsang, Cleland-Huang | 综述章节 2024 | 2405.10845 | ✅ |
| 3 | Using LLMs in Software Requirements Specifications: An Empirical Evaluation | Krishna, Gaur, Verma, Jalote | cs.SE 2024 | 2404.17842 | ✅ |
| 4 | On Understanding the Relation of Knowledge and Confidence to Requirements Quality | Dehghani, Wnuk, Mendez, Gorschek | RE 2021 | 2103.02187 | ✅ |

### 关键模型/工具
- **NLP4RE 研究社区**：每年 NLP4RE workshop（RE 会议卫星会），系统综述见 Sabetzadeh & Arora 2024。
- **LLM-SRS 草拟**：GPT-4 / CodeLlama 生成 SRS 草稿（Krishna 2024 用 8 项准则评估）。
- **需求可追溯性**：TLR（Traceability Link Recovery）管线，含 VSM、LSI、神经检索器（Guo 2024 综述）。

### 与本项目相关性（★★★★★）
直接命中：本项目要从中文 SRS 中做需求分类、术语抽取、可追溯（正文↔表格交叉引用），Sabetzadeh 2024 的 NLP 技术选型指南是方法论锚点；Guo 2024 的 TLR 综述对应「引用关系图构建」；Krishna 2024 提供 LLM 在 SRS 任务的能力边界（本项目数据治理报告已采用「规则+BERT+LLM」分层，与此一致）。

---

## 主题 2：Requirements Consistency Checking / Conflict Detection — 需求一致性检查与冲突检测

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | A Prompt-based Few-shot Learning Approach to Software Conflict Detection | Helmeczi, Cevik, Yıldırım | cs.SE 2022 | 2211.02709 | ✅ |
| 2 | AI Techniques for Software Requirements Prioritization | Felfernig | cs.SE 2021 | 2108.00832 | ✅ |
| 3 | Using LLMs in Software Requirements Specifications（含一致性维度评估） | Krishna et al. | 2024 | 2404.17842 | ✅ |

### 关键模型/工具
- **基于提示的少样本冲突检测**：Helmeczi 2022 用 prompt-based few-shot 在 SRS 中检测需求间冲突（典型场景：同一指标不同条目给出矛盾数值，如「响应时间≤50ms」vs「响应时间≤100ms」）。
- **传统方法**：基于本体/描述逻辑的推理（与 ARIS / ReqAnalyst 工具链相关），以及基于规则的全文本一致性扫描。
- **需求优先级 AI**：Felfernig 2021 综述优先级排序中的一致性约束处理。

### 与本项目相关性（★★★★★）
极高：本项目的核心交付之一是「参数化需求条目库」，其天然应用就是冲突检测——同一参数名在不同 SRS 条目出现矛盾的 `{op, value, unit}`。Helmeczi 2022 的 prompt-based few-shot 路线可直接迁移到「同一参数的多个数值约束冲突」检测，配合本项目规则层（数值比较）做兜底。

---

## 主题 3：Information Extraction from Technical Documents — 技术文档信息抽取

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | Business Document Information Extraction: Towards Practical Benchmarks (KILE & LIR) | Skalický, Šimsa, Uřičář, Šulc | ICDAR 2022 | 2206.11229 | ✅ |
| 2 | Retrieval Augmented Structured Generation: Business Document IE As Tool Use (RASG) | Cesista, Aguiar, Kim, Acilo | cs.CL 2024 | 2405.20245 | ✅ |
| 3 | Automatic Error Analysis for Document-level Information Extraction | Das, Du, Wang, Shi | cs.CL 2022 | 2209.07442 | ✅ |
| 4 | Application of LLMs for the Extraction of Information from Particle Accelerator Technical Documentation | Dai, Ischebeck, Sapinski, Grycner | cs.IR 2025 | 2509.02227 | ✅ |
| 5 | SynJAC: Synthetic-data-driven Joint-granular Adaptation for Domain Scanned Document KIE | Ding, Han, Li, Chung | cs.CV 2024 | 2410.01609 | ✅ |

### 关键模型/工具
- **KILE / LIR 基准**：Skalický 2022 定义「Key Information Localization & Extraction」与「Line Items Recognition」两大文档 IE 任务，已成为商业文档抽取事实标准。
- **RASG**：把 BDIE 建模为 Tool Use（下游系统即工具），用 RAG + 结构化生成达到 SOTA。
- **LLM 抽取遗留技术文档**：Dai 2025 在粒子加速器技术文档上用 LLM 做知识留存抽取，与「军工 SRS 遗留文档知识保留」场景高度同构。
- **文档级 IE 误差分析**：Das 2022 提供文档级 IE 系统化误差分析框架。

### 与本项目相关性（★★★★★）
直接命中：SRS 性能指标表 / ICD 接口表 / 数据字典表就是典型的 KILE（键值定位抽取）+ LIR（行项目识别）场景。RASG 的「Tool Use + 结构化生成」范式适配本项目「表格↔正文联合抽取」；Dai 2025 的遗留技术文档 LLM 抽取经验对本项目的冷启动极具参考价值。KILE/LIR 的评测协议可直接用于构建本项目表格抽取的评测集。

---

## 主题 4：Knowledge-Enhanced Information Extraction — 知识增强的信息抽取

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | K-BERT: Enabling Language Representation with Knowledge Graph | Liu, Zhou, Zhao, Wang, Ju | ACL 2019 | 1909.07606 | ✅ |
| 2 | Unifying Large Language Models and Knowledge Graphs: A Roadmap | Pan, Luo, Wang, Chen | cs.CL 2023 | 2306.08302 | ✅ |
| 3 | OPIEC: An Open Information Extraction Corpus | Gashteovski, Wanner, Hertling, Broscheit | ACL 2019 | 1904.12324 | ✅ |
| 4 | A Knowledge-Enhanced Disease Diagnosis Method Based on Prompt Learning and BERT Integration | Zheng | cs.CL 2024 | 2409.10403 | ✅ |

### 关键模型/工具
- **K-BERT**：将知识图谱三元组注入 BERT，生成「知识增强句子树」，在领域 NER/分类任务上稳定提升；是中文领域知识注入的经典基线。
- **LLM+KG 路线图**（Pan 2023）：KG→LLM（知识注入）、LLM→KG（KG 构建）、LLM⇄KG（协同）三大范式系统梳理。
- **OPIEC**：大规模开放 IE 语料（340M 三元组），含 provenance 元数据，可作 IE→KB 构建的对照基线。
- **SKETCH**（arXiv:2412.15443 ✅）：RAG + 知识图谱混合检索，融合结构化与非结构化知识。

### 与本项目相关性（★★★★☆）
中高：本项目可构建「GJB 军工术语 KG + 参数本体」作为外部知识源，用 K-BERT 思路做领域续训提升术语 NER 边界识别；用 Pan 2023 的 LLM⇄KG 协同范式做「LLM 抽取→KB 对齐→反哺校验」闭环。OPIEC 的 provenance 元数据设计对「参数条目可追溯（GJB 5000B 配置管理）」有借鉴价值。需注意 K-BERT 原工作为英文，中文军工场景需替换为中文 KG（如军事装备本体）+ RoBERTa-wwm。

---

## 主题 5：Span-Based NER — 基于 Span 的命名实体识别

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | Span-based Joint Entity and Relation Extraction with Transformer Pre-training (SpERT) | Eberts, Ulges | ECAI 2020 | 1909.07755 | ✅ |
| 2 | Unified Named Entity Recognition as Word-Word Relation Classification (W2NER) | Li, Fei, Liu, Wu | AAAI 2022 | 2112.10070 | ✅ |
| 3 | Span-Oriented Information Extraction — A Unifying Perspective on IE | Ding, Yankoski, Weninger | cs.CL 2024 | 2403.15453 | ✅ |
| 4 | Span-based joint entity and relation extraction augmented with sequence tagging (STSN) | Ji, Li, Xu, Yu | cs.CL 2022 | 2210.12720 | ✅ |
| 5 | An Exhaustive Framework for Generating Number of Features for Span-based NER | Sohrab, Miwa | ACL 2018 | —（ACL Anthology, 非 arXiv） | ⚠️ 奠基性，未在 arXiv |

### 关键模型/工具
- **Span-based 范式**（vs BIO 序列标注）：枚举所有候选 span → span 分类 + 边界回归。优势在于天然支持嵌套实体、不依赖分词边界（中文 SRS 术语边界模糊场景关键）。
- **SpERT**：BERT + span 分类 + 局部无标记上下文 + 强负采样，联合做 NER+RE，是 span-based 联合抽取的奠基工程实现。
- **W2NER**：把统一 NER（flat/nested/discontinuous）统一为 word-word 关系分类，用一张关系矩阵同时处理三类实体。
- **Span-Oriented IE 统一视角**（Ding 2024）：把 NER/RE/EE/EE-plus 全部重述为 span 任务，提供 IE 任务统一框架综述。

### 与本项目相关性（★★★★★）
极高：本项目 `参数化条目 = (参数名 span, 运算符 span, 数值 span, 单位 span)` 本质是 span 级联合抽取。Span-based 范式相对 BIO 的优势在中文军工 SRS 尤为突出：①术语常含嵌套（「RS422 串行接口」含「RS422」+「串行接口」）；②数值+单位是连续 span 但参数名可能跨词。SpERT 可直接迁移为「参数三元组 span 联合抽取」基线；W2NER 适合处理「响应时间」「最大响应时间」等嵌套/重叠术语。

---

## 主题 6：UIE — 统一信息抽取

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | Unified Structure Generation for Universal Information Extraction (UIE) | Lu, Liu, Dai, Xiao | ACL 2022 | 2203.12277 | ✅ |
| 2 | InstructUIE: Multi-task Instruction Tuning for Unified IE | Wang, Zhou, Zu, Xia | cs.CL 2023 | 2304.08085 | ✅ |
| 3 | InstructIE: A Bilingual Instruction-based IE Dataset | Gui, Qiao, Zhang, Ye, Sun | ISWC 2024 | 2305.11527 | ✅ |
| 4 | GoLLIE: Annotation Guidelines improve Zero-Shot IE | Sainz, García-Ferrero, Agerri et al. | ICLR 2024 | 2310.03668 | ✅ |
| 5 | FSUIE: A Novel Fuzzy Span Mechanism for Universal IE | Peng, Li, Zhang, Du | cs.CL 2023 | 2306.14913 | ✅ |
| 6 | YAYI-UIE: Chat-Enhanced Instruction Tuning for UIE (中英) | Xiao, Wang, Xu, Wang | cs.CL 2023 | 2312.15548 | ✅ |
| 7 | RUIE: Retrieval-based Unified IE using LLM | Liao, Duan, Huang, Wang | cs.CL 2024 | 2409.11673 | ✅ |
| 8 | MR-UIE: Multi-Perspective Reasoning with RL for UIE | Li, Wang, Fang, Bao | cs.CL 2025 | 2509.09082 | ✅ |
| 9 | Schema as Parameterized Tools for UIE (SPT) | Liang, Zhang, Wu, Tang | cs.CL 2025 | 2506.01276 | ✅ |

### 关键模型/工具
- **UIE（Lu 2022）**：奠基性工作，提出 **SEL（Structured Extraction Language）+ SSI（Structural Schema Instructor）**，把 NER/RE/EE 统一为 text-to-structure 生成；预训练用大量异构 IE 语料。开源（HuggingFace `uie-base`，含中文权重 `uie-base-cn`）。
- **InstructUIE**：指令微调统一 IE，揭示 GPT-3.5 在标准 IE 上仍弱（Ontonotes F1 仅 18.22）。
- **InstructIE**：中英双语指令 IE 数据集，12 领域，KG2Instruction 自动生成框架——**中文指令 IE 的关键基线**。
- **GoLLIE**：用 Python 类形式的标注指南微调 LLM，零样本迁移到未见 IE 任务；消融证明「详细指南」是关键。
- **FSUIE**：模糊 span 机制，缓解 span 边界标注噪声——对人工标注的 SRS 数据鲁棒性有帮助。
- **RUIE**：检索增强 in-context learning，少样本高效泛化。
- **MR-UIE / SPT**（2025 最新）：RL 多视角推理 / schema 即工具，代表 UIE 前沿方向。

### 与本项目相关性（★★★★★）
最高：本项目数据治理报告已将 UIE 列为主力方案之一。直接价值：用 SSI 定义 `schema: [参数名, 运算符, 数值, 单位]`，一次生成完整条目，天然支持「参数+运算符+数值+单位」联合抽取。GoLLIE 可把 GJB 438C 参数书写规范写成 guideline 做零样本抽新指标类型；InstructIE 提供中文指令 IE 数据构造范式；FSUIE 的模糊 span 对人工标注边界噪声鲁棒。建议主力用 `uie-base-cn` + GoLLIE 风格 guideline，长尾用 RUIE 检索增强。

---

## 主题 7：LLM for Information Extraction — 大语言模型做信息抽取

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | An Empirical Study on Information Extraction using Large Language Models | Han, Yang, Peng, Tiwari | cs.CL 2023 | 2305.14450 | ✅ |
| 2 | Evaluating ChatGPT's Information Extraction Capabilities (Performance, Explainability, Calibration, Faithfulness) | Li, Fang, Yang, Wang, Ye | cs.CL 2023 | 2304.11633 | ✅ |
| 3 | DeepKE: A Deep Learning Based Knowledge Extraction Toolkit for Knowledge Base Population | Zhang, Xu, Tao, Yu, Ye | EMNLP 2022 Demo | 2201.03335 | ✅ |
| 4 | UniRel: Unified Representation and Interaction for Joint Relational Triple Extraction | Tang, Xu, Zhao, Mao, Liu | EMNLP 2022 | 2211.09039 | ✅ |
| 5 | Clinical IE for Low-resource Languages with Few-shot Learning using PLMs and Prompting | Richter-Pechanski et al. | cs.CL 2024 | 2403.13369 | ✅ |

### 关键模型/工具
- **LLM-IE 能力评测**：Han 2023 系统评估 GPT-4 在 NER/RE/EE 上的能力；Li 2023（ChatGPT-IE）发现 ChatGPT 在标准 IE 上弱、在 OpenIE 上强，**解释质量高但过度自信、校准低**——警示 LLM 抽取需置信度校准与人工复核。
- **DeepKE**（zjunlp）：开源知识抽取工具包，支持 NER/RE/属性抽取，含低资源、文档级、多模态，提供中文预训练权重与 PyTorch 工程化实现，开箱即用。
- **UniRel**：统一实体-关系表示与交互，用 Interaction Map 联合抽取关系三元组——`(参数名, ≤, 50)` 本质即关系三元组。
- **少样本临床 IE**：Richter-Pechanski 2024 在低资源语言上用轻量 PLM + prompting，对本项目「军工低资源中文」有方法论参考。

### 与本项目相关性（★★★★★）
极高：本项目数据治理报告已采用「规则兜底 + 领域 BERT 主力 + LLM 长尾/校验」三层架构。Li 2023 的「LLM 过度自信、校准低」结论直接支撑本项目「LLM 只做长尾+校验、不做主力」的决策（军工可审计性要求）。DeepKE 可作为工程化主力框架候选；UniRel 的关系三元组联合建模对应参数化条目的 `(参数名, 运算符, 数值)` 联合抽取。

---

## 主题 8：Entity Linking with Embeddings — 基于嵌入的实体链接

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | End-to-End Neural Entity Linking | Kolitsas, Ganea, Hofmann | EMNLP 2018 | 1808.07699 | ✅ |
| 2 | Investigating Entity Knowledge in BERT with Simple Neural End-to-End EL | Broscheit | ACL 2020 | 2003.05473 | ✅ |
| 3 | Scalable Zero-shot Entity Linking with Dense Entity Retrieval | Wu, Petroni, Josifoski, Riedel | 2019 | 1911.03814 | ✅ |
| 4 | Multilingual End to End Entity Linking (BELA) | Plekhanov, Kassner, Popat, Martin | cs.CL 2023 | 2306.08896 | ✅ |
| 5 | JEL: Applying End-to-End Neural Entity Linking in JPMorgan Chase | Ding, Chaudhri, Chittar, Konakanchi | cs.IR 2024 | 2411.02695 | ✅ |
| 6 | Graph-Embedding Empowered Entity Retrieval | Gerritse, Hasibi, de Vries | cs.IR 2020 | 2005.02843 | ✅ |
| 7 | Information Retrieval with Entity Linking | Shehata | cs.IR 2024 | 2404.08678 | ✅ |

### 关键模型/工具
- **端到端神经 EL（Kolitsas 2018）**：首个联合做 mention 检测 + 实体消歧的神经端到端 EL，考虑所有 span 为候选 mention，学习上下文相似度分数。
- **BERT 内置实体知识（Broscheit 2020）**：极简端到端 EL，验证 BERT 预训练已含大量实体知识。
- **双编码器零样本 EL（Wu/Petroni 2019）**：bi-encoder 检索 + cross-encoder 重排，实体仅用短描述定义，零样本 SOTA——**适配「军工术语 KB 无大量标注」的低资源场景**。
- **BELA**：首个覆盖 97 语言的端到端多语言 EL 模型（含中文），开源。
- **JEL**：JPMorgan 金融领域 EL 工业落地，企业 KG 链接经验。
- **图嵌入实体检索**：用 KG 图嵌入做实体检索重排。

### 与本项目相关性（★★★★☆）
高：本项目「术语归一化」（「响应时间」vs「反应时间」vs「response time」对齐到同一参数实体）本质即实体链接。Wu/Petroni 2019 的双编码器+实体描述范式最适合军工低资源（无需大规模标注，仅需参数本体+描述）；BELA 的中文支持降低门槛；JEL 的企业 KG 链接经验对应「SRS 术语→军工参数本体」映射。建议：构建「GJB 参数本体（含同义词/缩写描述）」→ 用双编码器做 mention→entity 检索 → cross-encoder 重排。

---

## 主题 9：Parameter Extraction from Requirements — 需求文档参数抽取

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | ReXCL: A Tool for Requirement Document Extraction and Classification | Bhattacharya, Chakraborty, Arumugam, Gupta | cs.SE 2025 | 2504.07562 | ✅ |
| 2 | A Prompt-based Few-shot Learning Approach to Software Conflict Detection（含参数级冲突） | Helmeczi et al. | 2022 | 2211.02709 | ✅ |
| 3 | Using LLMs in Software Requirements Specifications | Krishna et al. | 2024 | 2404.17842 | ✅ |

### 关键模型/工具
- **ReXCL**（2025 最新）：自动化需求文档抽取与分类工具，两大模块——① Extraction（启发式+预测模型把原始需求文档处理成预定义 schema）；② Classification（encoder 模型自适应微调做需求分类）。输出可导出到外部 RE 工具。
- **参数化抽取通用范式**（本项目数据治理报告已系统化）：`{参数名, 运算符, 数值, 单位}` = 实体+关系+数值属性联合抽取 = 关系三元组 `(参数名, 运算符, 数值)` + 单位槽填充。
- **规则+模型+LLM 混合管线**：正则模板（`(?P<op>[≤≥<>≈])(?P<val>\d+\.?\d*)\s*(?P<unit>ms|Mbps|路|℃)`）+ BERT-CRF NER + LLM few-shot。

### 与本项目相关性（★★★★★）
最高：这正是本项目核心任务。ReXCL（2025）是最新公开的同类工具，其「Extraction→预定义 schema + Classification→encoder 微调」双模块架构与本项目「表格/正文抽取→参数化条目库 + 条目类型分类」高度同构，可作为直接对标基线。注意：arXiv 上针对「需求文档数值参数抽取」的专题论文较少，更多散落在 NLP4RE 与冲突检测文献中——本项目数据治理报告已系统化该方向（见 `SRS数据治理技术调研报告.md` 方向 1）。

---

## 主题 10：Requirements Quality Analysis NLP — 需求文档质量分析

### 关键论文

| # | 论文 | 作者 | 会议/期刊·年 | arXiv ID | 核验 |
|---|------|------|--------------|----------|------|
| 1 | Identifying relevant Factors of Requirements Quality: an industrial Case Study | Frattini | cs.SE 2024 | 2402.00594 | ✅ |
| 2 | How Requirements Quality Makes (or Breaks) Traceability Link Recovery | Hey, Frattini | cs.SE 2026 | 2606.11834 | ✅ |
| 3 | Enhancing Requirements Traceability Link Recovery: A Novel Approach with T-SimCSE | Wang, Wang, Hu, Huang | cs.SE 2026 | 2603.11800 | ✅ |
| 4 | On Understanding the Relation of Knowledge and Confidence to Requirements Quality | Dehghani et al. | RE 2021 | 2103.02187 | ✅ |
| 5 | Natural Language Processing for Requirements Traceability（质量相关章节） | Guo et al. | 2024 | 2405.10845 | ✅ |

### 关键模型/工具
- **需求质量因子分析**：Frattini 2024 工业案例研究，识别需求质量相关因子（歧义、不完整、矛盾等），指出「质量缺陷→下游活动受损」的实证证据。
- **质量↔可追溯性耦合**：Hey & Frattini 证明需求质量缺陷直接影响 TLR 性能——本项目「正文↔表格交叉引用」质量受 SRS 写作质量制约。
- **T-SimCSE**：用 SimCSE 句嵌入做需求可追溯链接恢复，预训练语言模型+对比学习新范式。
- **知识与置信度→质量**：Dehghani 2021 研究需求工程师的知识/置信度对需求质量的影响。
- **需求质量缺陷类型**（业界共识，源自 ISO/IEC 25010、REQB、QuARS 等工具）：歧义性、完整性、一致性、可验证性、可追溯性、原子性、唯一性等。

### 与本项目相关性（★★★★★）
极高：本项目交付的「参数化需求条目库」天然可用于质量分析——①一致性（主题 2 冲突检测）；②完整性（参数是否覆盖 GJB 438C 强制项）；③可验证性（数值+单位是否可测）；④可追溯性（引用关系图是否闭环）。Hey & Frattini 的「质量↔TLR 耦合」结论直接说明：本项目抽取出的引用关系图本身既是交付物，也是 SRS 质量的度量。T-SimCSE 的句嵌入对比学习可用于「相似需求条目聚类去重」与「术语归一化」。建议：把质量分析作为参数化条目库的「上层应用」输出 SRS 质量报告。

---

## 综合技术地图（与本项目各模块映射）

| 本项目模块 | 对应主题 | 关键技术/模型 | 推荐优先级 |
|-----------|----------|--------------|-----------|
| 文档解析与表格抽取 | （见 `SRS文档解析技术调研报告.md`，本文档不覆盖） | MinerU / PP-Structure / python-docx | — |
| 领域术语 NER（接口/参数/协议） | 5 span-based NER, 6 UIE, 7 LLM-IE | SpERT + W2NER + UIE-base-cn + DeepKE | ★★★★★ |
| 参数化条目抽取 `{param,op,value,unit}` | 9 参数抽取, 6 UIE, 5 span | UIE(SSI) + UniRel 三元组 + 规则槽填充 | ★★★★★ |
| 数值-单位-运算符联合抽取 | 5, 6, 9 | BERT-CRF + 数值正则 + GoLLIE guideline | ★★★★★ |
| 术语归一化（同义词对齐） | 8 entity linking | 双编码器 EL（Wu/Petroni）+ BELA 中文 | ★★★★☆ |
| 知识增强（军工本体注入） | 4 knowledge-enhanced IE | K-BERT + LLM⇄KG 协同 + SKETCH | ★★★★☆ |
| 正文↔表格交叉引用 | 1 NLP4RE, 10 质量 | TLR（T-SimCSE）+ 引用关系图 | ★★★★★ |
| 需求冲突检测 | 2 conflict detection | 规则数值比较 + Helmeczi prompt few-shot | ★★★★★ |
| SRS 质量分析报告 | 10 requirements quality | Frattini 质量因子 + 条目库统计 | ★★★★☆ |
| 技术文档 IE 评测体系 | 3 IE tech docs | KILE/LIR 基准 + RASG Tool Use | ★★★★☆ |

## 统一架构建议（整合 10 主题）

```
SRS 文档（Word/PDF）
   │
   ├─[解析层] MinerU+PP-Structure / python-docx → 归一化结构化文档+表格
   │
   ├─[抽取层]
   │   ├─ 规则层：参数正则模板（高召回+可审计，GJB 5000B 合规）
   │   ├─ 模型层：UIE-base-cn（SSI schema=[参数名,运算符,数值,单位]）
   │   │         + SpERT span 联合抽取（嵌套术语）+ UniRel 三元组
   │   └─ LLM 层：GoLLIE guideline 零样本长尾 + RUIE 检索增强
   │
   ├─[知识层] 军工参数本体（GJB 术语 KG）
   │   ├─ K-BERT 领域续训（术语边界增强）
   │   ├─ 双编码器 EL 术语归一化（同义词/缩写对齐）
   │   └─ LLM⇄KG 协同（抽取→KB 对齐→反哺校验）
   │
   ├─[引用层] T-SimCSE 句嵌入 + 规则编号匹配 → 引用关系图
   │
   └─[应用层]
       ├─ 冲突检测：参数条目库数值冲突扫描 + Helmeczi prompt few-shot
       ├─ 质量分析：Frattini 质量因子 + KILE/LIR 评测协议
       └─ 可追溯性：引用关系图闭环校验（Hey & Frattini）
```

## 关键文献 ID 速查表（全部 ✅ 已核验）

```
NLP4RE:        2401.01508  2405.10845  2404.17842  2103.02187
Conflict:      2211.02709  2108.00832
IE-TechDoc:    2206.11229  2405.20245  2209.07442  2509.02227  2410.01609
Knowledge-IE:  1909.07606  2306.08302  1904.12324  2409.10403  2412.15443
Span-NER:      1909.07755  2112.10070  2403.15453  2210.12720
UIE:           2203.12277  2304.08085  2305.11527  2310.03668
               2306.14913  2312.15548  2409.11673  2509.09082  2506.01276
LLM-IE:        2305.14450  2304.11633  2201.03335  2211.09039  2403.13369
Entity-Link:   1808.07699  2003.05473  1911.03814  2306.08896
               2411.02695  2005.02843  2404.08678
Param-Extract: 2504.07562  2211.02709  2404.17842
Req-Quality:   2402.00594  2606.11834  2603.11800  2103.02187  2405.10845
```

## 检索方法说明与局限

1. **检索源**：arXiv API（`export.arxiv.org`），relevance 排序，每主题 5–8 篇。部分奠基性论文（如 Sohrab & Miwa 2018 span-based NER）仅在 ACL Anthology 不在 arXiv，已标注 ⚠️。
2. **核验**：所有 ✅ arXiv ID 均经 `id_list` 直查二次核验存在；速查表内 ID 全部 ✅。
3. **未覆盖源**：本次未检索 Semantic Scholar（IEEE/ACM 期刊）、Google Scholar、CNKI。建议后续补充：
   - NLP4RE 期刊论文（如 *Requirements Engineering* 期刊、IEEE TSE）多为 venue-only，不在 arXiv。
   - 中文核心期刊（计算机学报、软件学报）关于 GJB/需求工程的工作需 CNKI 检索。
   - 知识图谱增强 IE 的中文工作（如 CCKS 会议）需补充。
4. **建议补充检索关键词**（若需深化）：`NLP4RE survey`、`requirements defect detection`、`code-LLM IE GoLLIE`、`document understanding layout`、`numeric attribute extraction`、`unit extraction NLP`。

---

*报告生成于 2026-07-18，基于 arXiv API 实时检索 + 已验证 ID 直查。所有 arXiv ID 可直接用于 `https://arxiv.org/abs/<ID>` 访问。*
