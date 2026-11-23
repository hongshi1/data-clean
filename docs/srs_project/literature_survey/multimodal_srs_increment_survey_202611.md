# 多模态SRS文档：技术文档多模态理解与一致性科研文献增量调研（2026-08 → 2026-11）

> 调研日期：2026-11-16 | 检索渠道：arXiv API（export.arxiv.org，全部论文经摘要原文核验）
> 与已有调研关系：`cross_modal_consistency_survey.md`、`uml_diagram_understanding_survey.md`、`diagram_extraction_technology_spectrum.md`、`multimodal_qa_dataset_survey.md` 四份多模态调研均截至2026-08。本报告是**三个月增量**，聚焦四个此前未覆盖或已发生实质变化的面：
> 1. **方向B直接先例**：技术文档（专利/科学论文/工程标准）多模态一致性校验开始出现
> 2. **方向A文献支撑**：图-文-表证据关联与统一断言空间（多模态KG、entity-linked assertion graph）
> 3. **多模态长文档RAG/检索基准**：MMDocIR/MMLongBench家族/M3DocRAG生态爆发
> 4. **文档解析工具层**：0.8B统一解析模型时代 + 解析benchmark稳定性警示

---

## 0. TL;DR（六条判断）

1. **技术文档多模态一致性校验有了直接先例，但形态全部是"单文档LLM多模块"**：专利figure-reference一致性检测（balanced acc 91.2%）、sciwrite-lint（数字/表格/caption内部一致性lint范式）、AWASH/CMID（跨模态claim-evidence推理）。**无人做级联架构+确定性退出+实体级归因**——CascadeVerify的C1/C4贡献空间仍在，但related work必须新增这三个引用并做差异化。
2. **方向A的文献支撑发生质变**：GEMS-RAG（工程标准：图分解为视觉实体↔条款↔规范规则的多模态KG）与PILAR（句子/表/图事实→统一断言空间+实体链接图）与本项目的"实体注册表(主体,值,位置)+DEQ证据语句"**在表示层面几乎同构**——但两者目标都是QA/检索，不是一致性检测。方向A的方法论不再是空白，创新叙事必须从"首个聚合方法"调整为"聚合方法用于不一致检测的实证闭环（双登记定律）"。
3. **多模态长文档RAG基准在2025-2026爆发且结论清晰**：visual retriever显著优于text retriever（MMDocIR，EMNLP 2025 Main）；长文档DU仍是开放问题（MMLongBench-Doc：GPT-4o F1仅42.7%）；**KnowForge实证"角色分工智能体>合并智能体"（合并后-1.9 F1）**——与本项目级联架构和M27路由器负结果形成互证。
4. **文档解析进入小型统一模型时代**：0.8B模型在OmniDocBench v1.6达96+分（OvisOCR3=96.74、Xiaomi-OCR-0=96.83），且OvisOCR3**内置document figure captioning与跨页表格重建**——图片侧证据生产（框图/用例图/接口图→结构化描述）的本地成本骤降。**RankShift（2026-11）警告：解析benchmark排名本身随评测设计漂移（Kendall τ低至0.33），选型不能只看总分**。
5. **PILAR的诚实负结果与本项目立场一致**：视觉断言"只在locality-aware过滤后才有效"，当前收益主要由文本断言驱动——支持我们"VLM降级为抽检/仲裁位"的架构决策（场景5已确立，场景1同样适用）。
6. **SRS/RE领域本身依然纯文本**：text→UML转换SLR等经典NLP4RE线索无多模态一致性工作；arXiv上"requirements specification + multimodal"检索无直接命中——**GJB多模态SRS一致性校验的生态位仍然空着**，但周边（专利/标准/科学文档）正在快速逼近，时间窗口在收窄。

---

## 1. 方向B直接先例：技术文档多模态一致性校验（★★★★★ 本轮最重要发现）

### 1.1 Patent QA: Multi-Dimensional LLM Framework（arXiv:2510.25402，2025-10）

| 维度 | 内容 |
|---|---|
| 任务 | 专利说明书自动质量保证：**法规合规**、技术连贯性、**图-引用一致性**（figure-reference consistency）三模块+改进建议集成 |
| 数据 | 80人写+80AI生成专利，10,841句+8,924非模板句+**554张图** |
| 结果 | 三模块对专家标注的balanced accuracy：99.74% / 82.12% / **91.2%**（图-引用一致性） |
| 关键发现 | **AI生成专利的缺陷集中在图-文对齐与交叉引用的结构性错误**（人写专利多为表层错字）；机械/建筑领域claim-说明书矛盾最多 |

**对本项目的意义**：这是与SRS**文体最接近**（结构化技术文档+图+交叉引用+编号体系）的图-文一致性工作。其figure-reference consistency≈我们的TERM-05/TERM-07/追踪锚点失效（VIO-12）。差异化：纯LLM多模块、无级联、无确定性退出、无soundness保证、单一英文域；我们有9专家符号层+Z3+三态判定+17真实违例。**必引**。

### 1.2 sciwrite-lint（arXiv:2604.08501，2026-04）

- **思想**：把软件工程的**linting范式**迁移到科学写作——本地运行（消费级GPU+开放权重）、论文修订间可重跑、期刊/审稿人的自动初筛。
- **检查面**：引用存在性/元数据/撤稿状态/claim支撑+**内部一致性扩展：正文数字vs表格、摘要vs正文、图caption vs图内容、统计结果vs文字解读、悬空引用**。
- **对本项目的意义**：①"lint"框架=我们L1规则层的同型表述（GJB规则库120条=lint规则集），叙事上可借用其"linting paradigm"定位；②其caption vs content检查对应图片侧校验；③完全本地+可复现的工程约束与本项目runs协议/本地模型路线一致。**必引**。

### 1.3 AWASH/CMID（arXiv:2604.09644，2026-03）

- 任务：上市公司AI吹嘘检测，**重定义为跨模态claim-evidence推理**（而非表面相似度）——三模态（年报文+披露图+电话会视频）对齐，NLI模块做claim-evidence entailment，grounding层与专利/人才/算力等可验证物理证据交叉验证。F1=0.882。
- **对本项目的意义**：①"跨模态一致性=claim-evidence三态推理而非相似度"的方法论表态与我们完全一致（旧调研§零判断1的同型论证）；②其"证据可追溯到可验证锚点"设计=我们OCR框/表行/block号证据链。跨领域（金融披露）引用作定位。

### 1.4 数据质量侧的consistency gate（合成/清洗管线内置）

- **MedVLSynther**（2510.25867，ICLR 2026）：generator-verifier框架合成VQA，verifier多阶段门禁含**image-text consistency**——"生成物与图证据一致"作为硬门。与本场景1变异注入评测"构造性sound标签"思路同族。
- **MicroVQA++**（2511.11407）：HiCQA-Graph联合建模(图,caption,QA)做**跨模态一致性过滤**——用NLI+CLIP+agent信号筛掉不一致样本。
- **ERAF4XRD**（2609.18583，2026-09）：多智能体从文献重建实验记录，**独立验证agent**对源证据复核（98.5% precision/90.7% recall）——"抽取+独立验证分离"的agentic实例，对应我们"生产通道vs验证通道分离"。
- **DAGRI/NTCIR-19**（2611.11886，2026-11）：农业技术文档多模态理解三子任务（MinerU解析+双模态抽取+agentic跨文件检索）——又一批"垂直领域技术文档多模态智能"立项证据，说明该范式正在多领域铺开。

### 1.5 小结

| 工作 | 文档类型 | 检测对象 | 方法形态 | 与CascadeVerify差异 |
|---|---|---|---|---|
| Patent QA | 专利 | 合规/连贯/图-引用 | LLM多模块 | 无级联/无确定性退出 |
| sciwrite-lint | 科学论文 | 数字/图表/引用内部一致 | 本地lint管线 | 无NLI残差/无三态 |
| AWASH/CMID | 金融披露 | 跨模态claim-evidence | 三模态NLI+grounding | 非技术文档域 |
| MedVLSynther等 | 数据合成 | 生成物vs图 | verifier门禁 | 非检测系统本体 |
| **本项目** | **GJB SRS** | **40项taxonomy/17违例** | **级联L0-L3+Z3** | —— |

**结论**：方向B"技术文档多模态一致性"生态位从"无人区"变为"LLM整文档方法已入场，级联+符号+实体级归因仍空白"。

---

## 2. 方向A文献支撑：图-文-表证据关联与统一断言空间（★★★★★）

### 2.1 GEMS-RAG（arXiv:2610.33277，2026-10）——工程标准多模态KG，最接近的同类工作

- **对象**：工程标准MUTCD（法规条款+技术图纸+标准设备图）——"hierarchical, multimodal, densely connected through figures, tables, cross-references, normative rules"，**与GJB 438C+SRS的结构描述逐字吻合**。
- **方法**：层级解析+**细粒度视觉实体抽取**（图分解为有意义的视觉实体而非整图）+多模态KG构建+图接地混合检索（dense+sparse+visual+图扩展）。
- **关键设计**："视觉实体链接到文本条款、工程概念、规范规则"——即(图片元素, 条款, 规则)三元关联。
- **对本项目的意义**：①方向A的"图内元素↔正文↔规则"聚合已有同构实现，**related work必引且需差异化**（其目标=QA检索，无一致性检测、无三态、无级联）；②其"图不作为整体而作为实体集合"的立场=我们用例图→Actor/UC三元组解析（旧调研DePlot式翻译）的独立佐证；③MUTCD与GJB同属"安全攸关规范文档"，域迁移论证现成。

### 2.2 PILAR（arXiv:2609.32895，EMNLP 2026 Findings）——统一断言空间

- **思想**：ODQA证据表示——**把句子级、表级、图级事实映射到统一断言空间，构建entity-linked assertion graph**作为页面检索之上的受控关联层。
- **结果**：组合/跨文档/多跳问题上增益最大（+2.9组合/+5.9三跳）；**诚实负结果：当前增益主要由文本断言驱动，视觉断言只在locality-aware过滤后有效**。
- **对本项目的意义**：①"统一断言空间+实体链接图"≈DEQ证据语句+实体注册表的文献同构物（`evidence_statements.py`+`entity_detector.py`的学术表述有了锚点）；②其"视觉断言弱"的负结果支撑我们"图片侧证据走专用解析（OCR/VLM/源文件），VLM仅仲裁"的路线；③page-grounded provenance=我们的block号证据链。**必引**。

### 2.3 MMGraphRAG + SpecLink（arXiv:2507.20804）

- 视觉内容→结构化scene graph，与文本KG通过**谱聚类跨模态实体链接（SpecLink）**联合语义相似度与图结构；CMEL细粒度跨模态实体对齐benchmark；在DocBench/MMLongBench上提升复杂多模态推理。
- **对本项目的意义**：文档内（无外部KB）跨模态实体链接的方法论来源——对应L0"无KB实体聚合+同名消歧"（创新点C3）。

### 2.4 MEL（多模态实体链接）家族与表-文join

- **MERLIN**（2510.14307，多语言MEL testbed）+ **rare-entity切片**（2609.10745，EMNLP 2026 Main：SOTA在稀有实体上掉15-39.9%；reasoning+retrieval互补最佳）+ **FAST-MEL**（SIGIR 2026：固定尺寸向量化，快3个数量级）+ **DeepMEL**（多agent分工MEL）+ **MSR-MEL**（无监督多视角证据合成）。
- **LOKI**（2609.26658，2026-09）：**Text-Mediated Join Path Discovery**——文本作为 disjoint 表之间的关联证据，行级-句子级细粒度关联无需显式标注（表-行↔句关联从对比目标中涌现）。对应方向A"表行↔章节需求"的行级关联问题。
- **对本项目的意义**：MEL主流面向外部KB（Wikidata），我们是无外部KB的**文档内**链接——引用定位在"document-internal entity linking"（GEMS-RAG/PILAR/MMGraphRAG一系）；MERLIN稀有实体教训=军事专有术语（CLIP/BGE稀有性）会放大链接错误，需要BGE阈值守卫（EMB_TH_LOCAL=0.78）+确定性通道兜底。

---

## 3. 多模态长文档RAG与基准（2025-2026爆发，方向A的评测基建）

| 基准/系统 | 出处 | 规模/设定 | 关键结论 |
|---|---|---|---|
| **MMDocIR** | EMNLP 2025 Main（2501.08828） | 1,685专家标注+173,843自举问题；page级+**layout级**（段落/公式/图/表）双任务 | **visual retriever显著优于text retriever**；VLM文本优于OCR文本；训练集提升下游 |
| **M3DocRAG** | 2411.04952 | M3DocVQA：3,000+ PDF/40,000+页，open/closed-domain+单跳/多跳 | ColPali+Qwen2-VL 7B即可强基线；多页多文档证据检索 |
| **MMLongBench-Doc** | NeurIPS 2024 D&B Spotlight（2407.01523） | 1,062题/130 PDF（均值49.4页） | 33.2%跨页题、**22.8%不可回答题（防幻觉）**；GPT-4o F1仅42.7%；12/14个LVLM不如其LLM+OCR文本对应版 |
| **MMLongBench-Doc-V2** | 2608.03397（2026-08） | 修正106处标注+LLM judge替代字符串匹配 | **V1标注错误集中在"强系统能答对的题"**；字符串指标惩罚格式差异；V1/V2分数不可比 |
| **MMLongBench** | NeurIPS 2025 Spotlight（2505.10610） | 13,331例/5任务类/8K-128K token，46个LCVLM | 单任务是长上下文能力的弱代理；强推理模型长上下文更好 |
| **KnowForge** | 2610.13128（2026-10） | Locator(只搜索)/Judge(强制二跳)/Deep Reader(只读)角色分工 | 开域M3DocVQA F1 47.5（+11.0 over M3DocRAG）；**合并角色反降1.9 F1**；检索轮数4轮即台阶 |
| **CDS** | 2606.07252 | Constrained Dominant Set证据选择（query作为硬结构约束） | VisDoMBench 66.99（+37.1 over无检索）——**相关性-冗余平衡自动决定** |
| **ZipRerank** | ICML 2026（2605.11864） | 列表式多模态rerank，单forward打分 | MMDocIR上匹配SOTA，延迟降一个数量级 |
| **MM-R5** | 2506.12364 | SFT+RL推理增强rerank | MMDocIR多数指标SOTA，recall@1 +4% |
| **DocPrune** | CVPR 2026（2604.22281） | 文档token剪枝（背景/问题无关token） | M3DocRAG上吞吐3.0x/3.3x，F1反+1.0 |
| **AutoThinkRAG** | 2603.05551 | **查询复杂度路由**+感知-推理解耦（轻VLM转文本→LLM推理） | DocBench 82.13/MMLongBench 51.29，token省18.9% |

**对本项目的意义**：
1. **方向A的证据召回（evidence recall）评测**可以MMDocIR的page/layout双粒度协议为模板——"表行/图对应哪个需求"即layout级检索问题；EM/PM/MR三级匹配可直接借用。
2. **MMLongBench-Doc的22.8%不可回答题设计**=三态判定(NIE)的基准同型物——我们的NIE非"缺陷"而是任务定义的一部分，有文献锚点可引。
3. **MMLongBench-Doc-V2的标注修正教训直接命中本项目M28遗留**：其发现"标注错误集中在强系统能答对的题"（因标注产生方式偏倚）——我们的91QA gold人工标注（6-9h待做）应设计双人κ+分歧仲裁（工具链已备），否则gold会系统性偏伤强通道。
4. **KnowForge/CDS/AutoThinkRAG三篇与级联架构互证**：角色分工>合并（KnowForge）、证据选择看相关性-冗余而非纯相似度（CDS）、复杂度路由省成本（AutoThinkRAG）——级联/路由的经济学叙事有了三篇2026年新支撑；同时我们M27"学习路由器负结果"可引用KnowForge的"搜索vs阅读分工"解释为何EGT学不出QA路由。

---

## 4. 文档解析工具层（本地图片侧证据生产的成本结构改变）

### 4.1 统一小型解析模型（全部本地可跑，中文支持良好）

| 模型 | arXiv | 规模 | OmniDocBench v1.6 | 特色 |
|---|---|---|---|---|
| **OvisOCR3** | 2610.33066 | **0.8B** | 96.74 | **统一5任务：文档解析+通用OCR+KIE+图captioning+跨页表重建**；DocFigCapBench定位F1最高；OCRBench v2中英双榜第一 |
| Xiaomi-OCR-0 | 2609.36136 | 0.8B | 96.83 | 170M样本数据引擎+Mix-RL；五个OCR-VQA均值83.2 |
| Youtu-Parsing-Omni | 2610.39301 | 5B | **96.96** | 全模态（文/图/音/视频）单编码器单schema；图表解析95.02 |
| PolyOCR-Venus | 2609.37712 | 家族 | v1.6 SOTA竞争 | Competence-Guided策略优化+OCRBench v2.1 |
| WeVisDoc | 2609.20423 | 2B/4B | 95.38 | 两阶段数据中心（覆盖→残差探针定向补强） |

**对本项目的意义**：图片侧证据生产（48张功能框图/用例图/接口图）原先需要"VLM API+OCR+检测"三通道，现在**0.8B本地模型同时给出：结构化解析+图内文字+图caption+跨页表关联**——场景1的VLM前置解析层（待建清单）有了低成本落地方案；与"VLM降级为仲裁位"（场景5决策）一致。GROBID+布局mask（2609.26381）给出CPU档备选。

### 4.2 警示两条

- **RankShift**（2611.10679，2026-11）：OmniDocBench上16模型的排名随（数据构成×匹配策略×计分指标）漂移，区域级匹配下JSON vs Markdown真值τ≈0.33——**选型不能只看榜单总分，需按自身文档类型分层验证**（我们应拿16份SRS自建小型dev集对比2-3个解析器）。
- **AR-AWM水印攻击**（2610.15728）：覆盖7.98%像素的水印形扰动使Qwen2.5-VL-7B的DocVQA EM 0.899→0.150——涉密文档常带水印/密级标识，**解析鲁棒性是真实风险**，双通道互校（OCR↔VLM）因此有第二重理由。

### 4.3 表格侧

- **PrismAlign**（2609.21351，EMNLP 2026 industry）：多VLM视角对齐+表逻辑先验+贝叶斯决策，**利用"抽取错误与可计算规则违反的相关性"**做幻觉鲁棒表格OCR——"规则违反信号反哺抽取置信度"与我们的identifier/枚举join专家（证据侧双登记）思想同构，可作表格通道升级引用。

---

## 5. 图表理解与科学图数据（补充旧调研的图表线）

- **Read-Parse-Describe**（2610.20335，NeurIPS 2026）：统一"读-解析-描述"——页面→有序布局元素列表（bbox+语义标签+阅读序+文本+**视觉元素alt-text描述**）；125,218布局元素/11,338视觉实例。**"解析与视觉语义联合"是我们411块content_list的升级方向**（当前MinerU输出无视觉元素描述）。
- **OmniScience**（2602.13758）：150万figure-caption-context三元组（10+学科）+动态模型路由再caption管线——科学图理解的训练数据来源（若需微调图片侧理解）。
- **SciCap五年回顾**（2512.21789）：科学图caption领域的经验教训与五个未解挑战——**"caption与图内容忠实度"仍是开放问题**（=我们图片侧校验的理论依据之一）。
- **GENFIG1**（2604.04172）：论文Figure1视觉摘要生成benchmark——反向任务，佐证"图-文互译"双向研究价值。
- 旧调研已覆盖（不重复）：SADU、Prior Bias、DRAGON、MCC、IVT、FlowExtract、VisDoT、PP-OCRv5等（见`uml_diagram_understanding_survey.md`§附录）。

---

## 6. 映射到本项目（方向A/方向B/评测/架构/工具）

### 6.1 方向A（上下文关联）

| 文献机制 | 项目对应物 | 行动 |
|---|---|---|
| GEMS-RAG视觉实体↔条款↔规则KG | 实体注册表(主体,值,位置)+GJB规则簇 | 引用+差异化（QA vs 一致性） |
| PILAR统一断言空间+实体链接图 | DEQ证据语句+evidence_statements | 引用作方法学名 |
| MMGraphRAG SpecLink文档内链接 | L0无KB实体聚合+NIL | C3引证补强 |
| LOKI行↔句关联 | 表行↔章节需求（合格性/追踪表） | join机制的对比基线 |
| MMDocIR layout级检索 | evidence_recall模块评测协议 | 借用EM/PM/MR指标 |

### 6.2 方向B（不一致性校验）

| 文献机制 | 项目对应物 | 行动 |
|---|---|---|
| 专利figure-reference一致性 | TERM-05/07、VIO-12追踪锚点失效 | **必引**（最近邻竞品）；差异化=级联+实体级+三态 |
| sciwrite-lint内部一致性 | L1规则层+GJB规则库 | "linting paradigm"叙事借用 |
| AWASH claim-evidence三态推理 | support/refute/NIE判定形态 | 方法论表态引用 |
| PrismAlign规则违反↔抽取错误相关性 | 证据侧双登记定律 | 互证引用（M27发现的独立佐证） |

### 6.3 评测

- MMLongBench-Doc 22.8%不可回答题→NIE三态的基准先例；
- **MMLongBench-Doc-V2标注修正→91QA gold标注协议强化**（标注错误集中于强系统可答项；需双人κ+LLM-judge语义匹配而非字符串比对——工具链`build_annotation_sheet.py`已有TSV+κ，需加"语义等价判定"）；
- RankShift→解析器选型自建分层dev集；
- MedVLSynther/ERAF4XRD→构造性sound标签与独立验证agent的先例。

### 6.4 级联架构定位（49号文档§9.4的增补）

新增三篇2026互证：KnowForge（角色分工>合并，-1.9 FPI合并损失）、AutoThinkRAG（复杂度路由省18.9% token）、CDS（证据选择的相关性-冗余平衡）。级联经济学与"分工优于合并"的叙事从FrugalGPT/RouteLLM扩展到多模态文档域。

### 6.5 工具层

- 图片侧证据生产：OvisOCR3（0.8B本地，caption+解析+跨页表）替代"VLM API独走"；
- 表格侧：PrismAlign思路（规则违反信号反哺）；
- 鲁棒性：AR-AWM水印风险→双通道互校的第二重理由。

---

## 7. 竞争定位与创新点校准

**时间窗口判断**：技术文档多模态一致性从"无人区"（2026-08旧调研结论）变为"LLM整文档方法已入场（专利QA/sciwrite-lint）+工程标准多模态KG已出现（GEMS-RAG）+统一断言空间已提出（PILAR）"。**级联+确定性退出+实体级归因+三态+真实违例集**的组合仍未被占——但建议论文写作（M28遗留）尽快启动，related work需新增：

1. Patent QA（2510.25402）——最近邻，差异化：符号级/级联/中文GJB域/17真实违例
2. GEMS-RAG（2610.33277）——方向A最近邻，差异化：聚合为一致性检测服务（双登记定律实证）而非QA
3. PILAR（2609.32895）——断言空间同构，差异化：视觉断言弱→我们用确定性图片解析通道绕开
4. sciwrite-lint（2604.08501）——lint范式同型，差异化：多模态+GJB规则可溯源+Z3
5. KnowForge/AutoThinkRAG/CDS——级联经济学2026互证

**C5（真实GJB数据集）叙事更新**：从"首个中文技术文档多模态一致性Gold Standard"（multimodal_qa_dataset_survey§七的4缺口仍成立）微调为——"首个面向一致性检测（而非QA）的中文技术文档多模态评测集+构造性sound标签协议"。

---

## 8. 风险与警示（决策依据）

1. **PILAR视觉断言弱**：视觉证据直接进断言空间收益有限（需locality过滤）——图片侧证据应结构化（OCR/解析/caption）后进入，不做"VLM看图直接出断言"。
2. **MMLongBench-Doc-V2标注陷阱**：gold标注错误集中于强系统可答样本——91QA人工标注须双人+仲裁+语义等价判定（非字符串）。
3. **RankShift**：解析器榜单排名不稳定——自建SRS分层验证集再选型。
4. **AR-AWM**：水印形扰动可使DocVQA EM崩溃（0.899→0.150）——涉密文档水印是现实输入分布，互校必要性+1。
5. **生态位收窄**：周边领域（专利/标准/农业/医疗文档）多模态智能2026年下半年密集立项——论文优先级应高于新功能扩展。

---

## 9. 推荐行动（按优先级）

1. **[论文写作侧，0成本]** 49号文档related work增补§7五组引用；C5叙事微调；"双登记定律"补PrismAlign互证。
2. **[gold标注协议，0.5天]** `build_annotation_sheet.py`流程吸收MMLongBench-Doc-V2教训：答案判定用语义等价（LLM-judge/人工），标注来源偏倚记录。
3. **[工具验证，1天]** OvisOCR3(0.8B)本地部署，跑04号SRS的48张图：对比现有MinerU解析+VLM抽取，产出图caption质量抽样报告——决定图片侧证据通道是否升级（RankShift式自建dev集）。
4. **[方向A基线，可选]** MMDocIR layout级检索协议移植到16份SRS，作为evidence_recall的标准化评测（区别于内部dev集的外部可比指标）。
5. **[暂缓]** 图片侧端到端微调（OmniScience数据）——待gold标注与论文主体完成后评估。

---

## 10. 论文索引表（本轮新增，全部经arXiv API摘要核验）

| # | 论文 | arXiv ID | 年份 | 会议/状态 | 相关度 |
|---|---|---|---|---|---|
| 1 | Towards Automated QA of Patent Specifications | 2510.25402 | 2025 | 预印本v2 | ★★★★★ 方向B最近邻 |
| 2 | GEMS-RAG: Engineering Multimodal Standards RAG | 2610.33277 | 2026 | 预印本 | ★★★★★ 方向A最近邻（工程标准） |
| 3 | PILAR: Entity-Linked Assertion Graph for Multimodal ODQA | 2609.32895 | 2026 | EMNLP 2026 Findings | ★★★★★ 断言空间同构 |
| 4 | sciwrite-lint: Verification Infrastructure | 2604.08501 | 2026 | 预印本 | ★★★★★ lint范式 |
| 5 | MMDocIR: Multimodal Retrieval for Long Documents | 2501.08828 | 2025 | EMNLP 2025 Main | ★★★★ 检索评测协议 |
| 6 | MMLongBench-Doc | 2407.01523 | 2024 | NeurIPS 2024 D&B Spotlight | ★★★★ 长文档DU+不可回答题 |
| 7 | MMLongBench-Doc-V2 | 2608.03397 | 2026 | 预印本 | ★★★★ 标注质量警示 |
| 8 | M3DocRAG | 2411.04952 | 2024 | 预印本 | ★★★ 多页多文档RAG |
| 9 | MMLongBench | 2505.10610 | 2025 | NeurIPS 2025 Spotlight | ★★★ 长上下文VLM |
| 10 | KnowForge: Role-Specialized Tool Agents | 2610.13128 | 2026 | 预印本 | ★★★★ 角色分工>合并 |
| 11 | AWASH/CMID: Cross-Modal Inconsistency Detection | 2604.09644 | 2026 | 预印本 | ★★★ claim-evidence三态 |
| 12 | MMGraphRAG + SpecLink | 2507.20804 | 2025 | 预印本v3 | ★★★ 文档内跨模态链接 |
| 13 | OvisOCR3 | 2610.33066 | 2026 | 技术报告 | ★★★★ 0.8B统一解析+图caption |
| 14 | Youtu-Parsing-Omni | 2610.39301 | 2026 | 技术报告 | ★★★ 全模态解析 |
| 15 | Xiaomi-OCR-0 | 2609.36136 | 2026 | 技术报告 | ★★★ 0.8B解析 |
| 16 | PrismAlign: Hallucination-Robust Table OCR | 2609.21351 | 2026 | EMNLP 2026 industry | ★★★ 规则违反↔错误相关 |
| 17 | RankShift: Ranking Instability in Doc Parsing | 2611.10679 | 2026 | 预印本 | ★★★ 选型警示 |
| 18 | Read-Parse-Describe | 2610.20335 | 2026 | NeurIPS 2026 | ★★★ 解析+视觉描述联合 |
| 19 | CDS: Constrained Dominant Sets | 2606.07252 | 2026 | 预印本 | ★★★ 证据选择 |
| 20 | AutoThinkRAG | 2603.05551 | 2026 | 预印本 | ★★★ 复杂度路由 |
| 21 | ZipRerank | 2605.11864 | 2026 | ICML 2026 | ★★ 多模态rerank |
| 22 | MM-R5 | 2506.12364 | 2025 | 预印本 | ★★ RL rerank |
| 23 | DocPrune | 2604.22281 | 2026 | CVPR 2026 | ★★ token剪枝 |
| 24 | ERAF4XRD | 2609.18583 | 2026 | 预印本 | ★★★ 独立验证agent |
| 25 | MedVLSynther | 2510.25867 | 2025 | ICLR 2026 | ★★★ verifier门禁 |
| 26 | MicroVQA++ / HiCQA-Graph | 2511.11407 | 2025 | 预印本 | ★★ 一致性过滤 |
| 27 | OmniScience | 2602.13758 | 2026 | 预印本 | ★★ 科学图数据 |
| 28 | SciCap五年回顾 | 2512.21789 | 2025 | AAAI AI2ASE 2026 | ★★ caption忠实度开放问题 |
| 29 | GENFIG1 | 2604.04172 | 2026 | 预印本 | ★★ 图-文互译反向任务 |
| 30 | MERLIN (+rare-entity) | 2510.14307 / 2609.10745 | 2025/2026 | EMNLP 2026 Main | ★★ MEL稀有实体教训 |
| 31 | FAST-MEL / DeepMEL / MSR-MEL | 2606.11749 / 2508.15876 / 2604.20283 | 2025-2026 | SIGIR 2026等 | ★★ MEL方法族 |
| 32 | LOKI: Text-Mediated Join Path Discovery | 2609.26658 | 2026 | 预印本 | ★★★ 表-文行级关联 |
| 33 | AR-AWM水印攻击 | 2610.15728 | 2026 | 预印本 | ★★ 解析鲁棒性 |
| 34 | DAGRI/NTCIR-19 | 2611.11886 | 2026 | NTCIR-19 | ★★ 垂直域文档智能 |
| 35 | GROBID布局mask | 2609.26381 | 2026 | 预印本 | ★★ CPU档备选 |
| 36 | 多模态retrieval heads | 2605.27243 / 2610.32411 | 2026 | EMNLP 2026 | ★★ 机制研究 |

> 核验说明：以上36篇均为本轮arXiv API逐篇摘要核验（检索日期2026-11-16）；与旧调研（截至2026-08，已核验20+/40+篇）无重叠。
