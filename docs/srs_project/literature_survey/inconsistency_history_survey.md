# 需求一致性/不一致性检测四十年学术史（1986–2026）

> 调研日期：2026-08-24
> 范围：RE领域一致性/不一致性检测的完整思想史，为RE/ICSE级论文相关工作章节提供"历史叙事+自我定位"素材
> 方法：DBLP API / Crossref API / arXiv API / ACL Anthology 逐篇核验标题·作者·年份·出处（核验口径见文末），正文引用约50篇
> 与已有调研关系：本文提供**历史纵深**；2024–2026竞品技术细节见 `nlp4re_llm4re_comprehensive_survey.md`，跨模态方法见 `cross_modal_consistency_survey.md`，开放问题分析见 `open_problems_analysis.md`。本次核验发现项目内早期文档的若干史实错误（TSRCDF归属、AraREQ团队、Spanoudakis综述出处等），已更正，见文末勘误。

---

## 一、引言：一致性检测的问题定义

**一致性检测**（consistency checking）指：给定一组需求制品（视点、规格、模型、条目、文档），依据某个参考框架判断它们能否同时成立；**不一致性管理**（inconsistency management）则进一步涵盖发现之后的诊断、容忍与消解（Hunter & Nuseibeh, TOSEM 1998）。四十年历史可概括为同一个三元组的四次重写：

- **检测对象**（粒度）：视点/规格 → 模型 → 需求句对 → ？
- **参考框架**：形式逻辑 → 元模型约束/一致性规则 → 统计学习 → LLM隐式知识
- **处置策略**：消除 → 容忍与管理 → 二值分类报告 → （消解回归中）

值得注意的是：**"一致性"始终是关系性质而非单点性质**——判断两条陈述是否一致，先要确定"哪两条陈述构成一对"，即先有**聚合**后有**检测**。这一依赖在四十年文献中被评测惯例系统性遮蔽（详见§5.2），也是本项目方向A（条目聚合）的历史依据。

| 时代 | 检测对象 | 参考框架 | 主流手段 | 代表场景 |
|------|---------|---------|---------|---------|
| 1980s–90s | 多视点形式规格 | 经典/标注逻辑 | 定理证明、标签传播 | ViewPoints框架 |
| 2000s | UML模型（XMI级） | 一致性规则（OCL式） | 规则引擎、模型检查 | UML/Analyzer |
| 2010s | 需求句对 | 标注数据（NLI式） | 特征工程/ML/SAT | S3CDA、Bendík |
| 2020–26 | 句对/提示上下文 | LLM预训练知识 | 编码器、LLM、神经符号 | TSRCDF-SS、AraREQ |

---

## 二、不一致性的本体论

### 2.1 "不一致"的三种历史定义

1. **逻辑定义**：公式集不可满足。Gabbay & Hunter "Making inconsistency respectable"（LNCS 535, JELIA'90会议文集, 1991, pp.19–32）提出不一致可被逻辑地处理而非仅被恐惧：用标注式推理（labeled formulae）在含矛盾的知识库上做非平凡推理，配套准经典逻辑（Hunter, J. Logic & Computation 10(5), 2000, pp.677–703）。该纲领后来固化为Bertossi–Hunter–Schaub主编的《Inconsistency Tolerance》（LNCS 3300, 2005）。
2. **规约定义**：违反某参考框架（表示法规则、模板、标准）。VDM/Z传统的"证明义务"（proof obligations）与GJB 438C合规检查同属此类——一致性=履行了所有证明义务/规则。
3. **语用定义**：会对下游开发造成危害的差异。Chantree et al.（RE 2006, pp.56–65）区分nocuous/benign ambiguity，首次把"差异是否有害"本身作为研究对象。

三种定义分别对应本项目三层检测的学理源头：逻辑层（Z3/SAT）、语法层（GJB规则库）、语义层+可容忍性判定（NLI+类型先验）。

### 2.2 历史上有影响力的分类法

| 分类法 | 出处 | 内容 | 覆盖缺陷类型 |
|--------|------|------|------------|
| 标注式不一致度量 | Gabbay & Hunter 1991；Finkelstein–Gabbay–Hunter–Kramer–Nuseibeh (ESEC'93 / TSE 20(8), 1994) | 视点间矛盾可计数、可传播、可测显著度 | conflict |
| 不一致管理通用框架 | Hunter & Nuseibeh (TOSEM 7(4), 1998, pp.335–367) | 检测–诊断–处置；区分潜在/实际不一致 | 全类型（元框架） |
| 强/弱冲突 | van Lamsweerde, Darimont, Letier (TSE 24(11), 1998, pp.908–926) | KAOS目标模型上：矛盾 vs 目标阻碍（弱冲突） | conflict |
| 需求交互类型 | Robinson, Pawlowski, Volkov (ACM CSUR 35(2), 2003, pp.132–190) | 干扰、冲突、不一致的交互分类与全生命周期管理 | conflict/interaction |
| 六种需求关系 | Carlshamre et al. (RE 2001, pp.84–91) 工业调查 | requires / conflicts / duplicates / details / composition / similar | 关系全谱 |
| 需求气味 | Femmer et al. (RCoSE 2014; JSS 123, 2017, pp.190–213) | 10类smell：歧义、不完整、不一致、过度复杂等 | 全类型（质量缺陷视角） |
| 矛盾类型学 | Gärtner, Fay, Göhlich (Applied Sciences 12(15):7628, 2022) | 面向工程需求矛盾的显式分类法+半自动检测 | conflict |
| （邻域）合同矛盾分类 | LegalWiz (2025, arXiv:2510.03418)；ContractNLI (2021, arXiv:2110.01799) | 法律NLP域的矛盾/蕴含类型与证据span标注 | conflict |

**类型学演化规律**：形式化时代分类精细（度量/强弱/交互），ML时代退化为二值（conflict / not conflict）；2025–2026年法律邻域率先恢复多类型+证据定位，RE领域尚未跟进。

### 2.3 conflict / ambiguity / incompleteness 三姊妹

三者是需求质量缺陷的三个正交族（Femmer JSS 2017将其统一于质量框架）：**conflict**（不能同时成立）、**ambiguity**（多种解读皆可）、**incompleteness**（信息不足以判定）。历史上三者各自成线又相互纠缠：

- **歧义线**：Wilson, Rosenberg & Hyatt (ICSE 1997, pp.161–171) 的规格自动分析 → Chantree et al. (RE 2006) nocuous ambiguity → Yang et al. (ASE 2010, pp.53–62; RE 2010, pp.25–34) 指代/并列歧义自动检测 → Ezzini et al. (ICSE 2021 领域语料; ICSE 2022 指代歧义多方案; FSE 2022 TAPHSIR工具; ICSE 2023 QA辅助)。
- **不完整线**：与一致性在形式化传统中本是一体——Heitmeyer, Jeffords & Labaw (TOSEM 5(3), 1996, pp.231–261) 的SCR一致性检查同时证明完备性（缺失情形发现）。
- **交互线**：conflict与ambiguity的交汇点即"良性差异"问题——一个差异是矛盾、歧义还是合理详略，取决于语境许可（见§5.3）。

### 2.4 多模态层的本体论空白

上述全部分类法均在单一模态（形式符号或自然语言文本）内定义。**图文表三模态之间的不一致**（正文声明 vs 表格行 vs 图中节点）从未进入任何历史分类法——RE领域说"multimodal requirements"时指多模态交互系统的需求（如arXiv:2508.14631），而非多模态文档的联合理解（此观察及证据见 `open_problems_analysis.md` §2）。定义该层的类型学（实体不一致/声明不一致/结构不一致/呈现不一致）是本体论层面的开放贡献位。

---

## 三、四个时代

### 3.1 时代1（1980s–1990s）：多视点学派与形式化黎明

**背景**：大型（多为军事/过程控制）系统的多利益相关方冲突显性化；Z/VDM等形式化方法承诺"无歧义规格"；CSCW与知识获取（KA）研究兴起——Easterbrook本人来自KA社区（其1989–1991论文均在KAW/EKAW会议），这解释了不一致管理从一开始就是**社会–技术问题**而非纯技术问题。

**代表工作**：

| 工作 | 出处 | 核心机制 | 贡献与局限 |
|------|------|---------|-----------|
| Leite & Freeman, 需求验证的视点消解 | TSE 17(11), 1991, pp.1253–1269 | 多视点冲突的协商式消解 | 最早的视点级一致性工作之一；无自动化 |
| **ViewPoints框架**：Finkelstein, Kramer, Nuseibeh, Finkelstein, Goedicke | IJSEKE 2(1), 1992, pp.31–57 | 视点=（表示风格+工作计划+规格+工作记录）的部分开发知识包，**不要求全局一致** | 把"分布式不一致"合法化为开发常态；视点间不一致延迟暴露 |
| Gabbay & Hunter, "Making inconsistency respectable" | LNCS 535, 1991（Part I）；Part II 见LNCS后续卷 | 标注式逻辑：公式带来源标签，矛盾可度量可推理 | 为SE不一致处理提供逻辑学基础 |
| **Finkelstein–Gabbay–Hunter–Kramer–Nuseibeh** | ESEC 1993, pp.84–99 / TSE 20(8), 1994, pp.569–578 | 多表示法视点规格上的标注式不一致处理：标签传播+不一致显著度 | **SE与逻辑学的历史性合流**；只在小型形式规格上演示 |
| Robinson & Fickas, 支持多视点RE | ICRE 1994, pp.206–215 | 视点间关系维护与不一致协商 | 提出"不一致处理工具"设计议程 |
| Nuseibeh, Kramer, Finkelstein | TSE 20(10), 1994, pp.760–773 | 多视点关系的显式表达框架（**MENVOIL**原型[注1]） | 多表示法（multi-lingual）视点集成 |
| Balzer, "Tolerating Inconsistency" | ICSE 1991, pp.158–165（1989年ISPW为雏形） | 论证：不一致是开发资源，过早消除破坏信息 | "容忍"范式的宣言式起点 |
| Easterbrook & Nuseibeh, 演化规格的不一致管理 | RE'95（2nd IEEE ISRE）, pp.48–55；SEJ 11(1), 1996, pp.31–43 | 工作记录（work record）：显式记录已检出不一致及处置，供变更时推理 | 不一致成为**一等公民**；案例研究规模小 |
| Hunter & Nuseibeh 不一致管理综述 | TOSEM 7(4), 1998 | 检测–容忍–处置通用框架 | 该时代的领域定名之作 |
| Heitmeyer, Jeffords, Labaw, SCR | TOSEM 5(3), 1996 | SCR需求表→自动定理证明检查一致性+完备性 | 形式化路线的工业级代表；要求完全形式化输入 |
| van Lamsweerde, Darimont, Letier, KAOS冲突管理 | TSE 24(11), 1998, pp.908–926 | 目标模型上的强/弱冲突识别与消解模式 | 目标推理成为逻辑层检测的另一源头 |
| Robinson & Pawlowski, 开发目标监视器 | TSE 25(6), 1999, pp.816–835 | 用"goal monitor"在演化中持续监视不一致 | "监视而非消灭"的操作化 |
| Nuseibeh, Easterbrook, Russo | IEEE Computer 33(4), 2000; JSS 58(2), 2001 | "让不一致变得可尊敬"：不一致在开发过程中的信息价值 | 时代总结；管理范式定型 |

（同期补充：Spanoudakis & Finkelstein, Annals of SE 3, 1997——干扰/不一致/冲突的调和方法；Spanoudakis, Finkelstein & Till, ASE期刊 6(2), 1999——重叠不一致；Grundy, Hosking & Mugridge, TSE 24(11), 1998——多视图环境的不一致管理；Sugimoto & Ohnishi, APSEC 1999——SRS不一致检测与解释；Zhu & Jin, CIT 2005——本体法检测需求不一致，中文社区的早期参与。）

**方法论特征**：哲学先行（什么算不一致、为什么不必然消除）；检测对象=视点/形式规格；手段=定理证明与标注推理；典型论证方式是小型案例+概念框架，**无评测可言**。

**局限**：形式化成本高昂；依赖专家；从未处理自然语言文档；工具全部是原型（MENVOIL、WSRE等系统名主要见诸综述转引[注1]）。

**遗产**：（i）"检测–容忍–消解"三分法沿用至今；（ii）不一致的类型学与度量传统；（iii）"不一致承载信息"思想——良性差异问题的理论源头；（iv）多视点=多利益相关方的聚合直觉（方向A的思想远祖）。

### 3.2 时代2（2000s）：UML模型一致性时代

**背景**：UML 1.0（1997）统一了建模表示法，MDA/OCL使"模型间约束"可执行；研究问题从"哲学"转向"工程"：给定类图、状态图、顺序图，如何系统化定义并自动检查它们之间的一致性。

**代表工作**：

| 工作 | 出处 | 核心机制 | 贡献与局限 |
|------|------|---------|-----------|
| Spanoudakis & Zisman 不一致管理综述 | Handbook of SE & Knowledge Engineering, 2001, pp.329–380 | 系统化"检测–容忍–消解"谱系 | 时代1的正式收束与时代2的议程设定[注2] |
| Engels, Küster, Heckel, Groenewegen | ESEC/FSE-9, 2001, pp.186–195 | UML行为模型一致性的元模型化：一致性规则=跨图约束对 | 一致性规则作为**显式制品**（可查询、可演化） |
| Jackson, Alloy | TOSEM 11(2), 2002, pp.256–290 | 一阶关系逻辑+SAT求解的轻量形式化 | "够用的严格"：把形式化检查从专家手中解放 |
| Cleland-Huang, Chang, Christensen | TSE 29(9), 2003, pp.796–810 | 事件驱动追溯：需求变更→订阅者受通知 | 追溯线与一致性线的合流（维护而非仅检测） |
| **Egyed, 即时一致性检查** | ICSE 2006, pp.381–390；工具UML/Analyzer见ICSE 2007 demo | 只检查受变更影响的规则子集（观察一致性） | 把批处理检查变为**增量/即时**检查，工业可用性跃升 |
| Egyed, 修复不一致 | ICSE 2007, pp.292–301；Egyed, Letier, Finkelstein, ASE 2008 | 修复方案生成与效用评估 | 检测之后的第一批系统化**修复**工作 |
| Reder & Egyed, 不一致成因诊断 | TSE 39(11), 2013, pp.1531–1548 | 定位引发不一致的最小变更/模型元素 | 检测–诊断分离的方法论成型 |
| Lauenroth & Pohl, 产品线动态一致性 | RE 2008, pp.193–202 | 域需求与应用工程的一致性传播 | 一致性进入产品线场景 |
| Goknil, Kurtev, van den Berg, Veldhuis | SoSyM 10, 2011, pp.31–54（在线2009） | 追溯关系语义→可推理的一致性检查 | 视点关系的形式语义复兴 |
| **Famelis, Salay, Chechik, 部分模型** | ICSE 2012, pp.573–583；Salay et al., RE 2012 / REJ 18(2), 2013 | 模型元素带"可能存在"标注，把不一致重构为**不确定性** | 不一致=部分知识；不确定性–部分性–不一致性三位一体（"trifecta"提法出自该组表述[注3]） |
| Ali, Dalpiaz, Giorgini | IST 55(1), 2013, pp.35–57 | 上下文需求（Tropos/i*）的不一致与冲突推理 | "上下文"作为一致性判定的条件变量 |
| Boiten, Bowman, Derrick, Linington, Steen | Computer Networks 2000 | ODP视点一致性 | 电信标准的视点一致性规范 |
| Mu, Jin, Liu, Zowghi, Wei | SCP 2012（DOI:10.1016/j.scico.2012.12.006） | ViewPoints框架中不一致显著度的形式度量 | 时代1度量思想在2010年代的续脉 |

**方法论特征**：**model–model**比较；一致性规则人工书写但机器执行；粒度=模型元素/图；正确性可证明。

**局限**：只处理已形式化（XMI级）的模型，**自然语言SRS完全不在射程内**；规则集覆盖有限且维护昂贵；"一致性"被窄化为结构约束；图文混排的真实文档不可表达。Egyed线的深刻教训是：一致性检查的工业可用性来自**缩小检查范围**（增量、受影响子集），而非扩大——这对文档级检测的工程化有直接借鉴意义。

**遗产**：一致性规则即约束（本项目GJB规则库的OCL式定位）；增量检查架构；诊断/修复/检测的三段分离；部分模型对"不一致=知识不完全"的重构。

### 3.3 时代3（2010s）：NLP/ML + SAT时代

**背景**：NLP复兴（词向量→BERT）；需求质量实证研究兴起（Méndez Fernández et al., "Naming the Pain in RE", EMSE 2017）；PURE等公开数据集出现；工业界真实需求文档是自然语言这一事实终于被正面接受。

**代表工作**：

| 工作 | 出处 | 核心机制 | 贡献与局限 |
|------|------|---------|-----------|
| **Chantree, Nuseibeh, de Roeck, Willis, nocuous ambiguity** | RE 2006, pp.56–65 | 用多解读危害性判据区分有害/无害歧义 | **首次显式研究"良性差异"边界**；判据依赖人工特征 |
| Femmer et al., 需求气味 | RCoSE 2014, pp.10–19；JSS 123, 2017, pp.190–213 | 10类smell的句法/词汇模式→自动检查 | 约53%质量规则可自动化；催生Qualicen Requirements Scout（少数真实商业化之一，能力止于句级文本模式） |
| Ferrari, Spagnolo, Gnesi, **PURE** | RE 2017, pp.502–505 | 79份公开需求文档、4600余条需求的基准数据集 | RE领域的第一个大规模公开语料 |
| Habib, Wagner, Graziotin（ARTA数据集） | arXiv:2108.03087, 2021（NLP4RE'21） | 气味标注+深度学习检测 | smell检测的DL化；标注质量受争议 |
| Ezzini, Abualhaija, Arora, Sabetzadeh, Briand | ICSE 2021 / ICSE 2022 / FSE 2022 / ICSE 2023 | 领域语料训练缓解歧义；指代歧义多方案消解；QA辅助分析 | 歧义线的深度学习化；从检测转向辅助 |
| Guo, Zhang, Lian | arXiv:2103.02255, 2021 | 细粒度语义分析（语义角色+相似度）检测需求冲突 | 中文社区工作；句对级 |
| **Malik, Cevik, Basar, Parikh, S3CDA** | arXiv:2206.13690, 2022（v1题为SRS文档句对冲突的transformer嵌入识别） | 两阶段：余弦相似度粗筛 + S-NER实体重叠验证 | 五个数据集F1 0.71–0.92；其GPT-4o对比实验成为LLM领域退化的经典证据（通用域0.936→航空域0.462） |
| Malik, Yildirim, Cevik | arXiv:2301.03709, 2023 | 句对冲突/重复的迁移学习 | 跨域泛化开始被关注 |
| Helmeczi, Cevik, Yildirim | arXiv:2211.02709, 2022 | 提示式少样本冲突检测 | LLM进入RE冲突检测的先声 |
| **Bendík, 需求一致性检查** | ISSTA 2017, pp.408–411 | 需求依赖→命题逻辑编码→SAT可满足性；返回最小不可满足子集 | 逻辑层检测的范式完成体；NL→逻辑翻译需人工 |
| Gärtner, Fay, Göhlich | Applied Sciences 12(15):7628, 2022 | 矛盾分类法+半自动检测 | 工程需求矛盾的类型学回归 |
| Zhao et al., NLP4RE系统映射 | REJ 2021（arXiv:2004.01099），404篇一级研究 | 任务分类学 | 权威结论：主流范式=对SRS做检测，**粒度全部在句/条目级** |

**方法论特征**：**text–text句对级**；参考框架从逻辑/规则变为标注数据；评测=自建句对集上的F1；数据靠人工构造或合成注入。

**局限**：句对粒度隐含"对已配好"假设（对齐问题被排除在指标外）；领域数据稀缺导致合成数据盛行，埋下评测危机；**Chantree之后的良性差异研究断绝**；无文档结构、无多模态。

**遗产**：数据集资产（PURE/ARTA/S3CDA五件套）；句对基准惯例（延续到LLM时代，成为负资产）；smell检测的工业落地证明"窄而可审计"胜过"宽而不可解释"。

### 3.4 时代4（2020–2026）：LLM与多模态时代

**背景**：ChatGPT（2022.11）后LLM涌入RE；文档AI与多模态模型成熟；法律NLP（ContractNLI, 2021, arXiv:2110.01799：文档级NLI+证据span）示范了"文档级+证据定位"的任务形态。

**代表工作与事件**：

| 工作/事件 | 出处 | 核心内容 | 与本史的关系 |
|------|------|---------|------------|
| Fantechi, Gnesi, Passaro, Semini | RE 2023, pp.335–340 | ChatGPT直接判NL需求不一致的初步评测 | LLM检测的第一次正式评测：可行但不可靠 |
| Zadenoori et al., LLM4RE SLR | arXiv:2509.11446, 2025，74篇一级研究 | 缺陷检测从NLP4RE的第一位**跌至第八位（约5%）**；90%依赖GPT闭源、仅16%有公开数据 | 范式转移的量化证据：LLM研究者转向生成任务 |
| **Wang, Jiang, Bai, Zou, Xue, Zhang, Luan, TSRCDF-SS** | arXiv:2511.23007, 2025 | SBERT+SimCSE双编码器→六元拼接→FFNN（Focal变体+域约束+置信惩罚）；序列+跨域迁移 | 句对冲突检测的当前最强形态；域内macro/weighted-F1 +10.4%、跨域macro-F1 +11.4%——**仍是句对级、纯文本** |
| **AraREQ**：Hasanain Hammouda, Aljabari, Hamad, Jarrar（Birzeit大学） | LREC 2026（ACL Anthology已收录） | 27K阿拉伯语需求句对：LLM半自动阿拉伯化+人工增广；评测4个LLM的零/少样本 | 数据构建本身LLM化；含"消解"输出端——**仍句级、纯文本**[注4] |
| Darif, Niu, Abdellatif, Briand等 | arXiv:2602.22456, 2026 | LLM+RAG的汽车需求依赖检测 | 检索增强进入RE一致性场景 |
| Gärtner & Göhlich | Automated Software Engineering 31:49, 2024 | 形式逻辑+LLM的混合矛盾检测 | 神经符号回潮的RE实例 |
| 法律邻域迁移 | ContractCheck（arXiv:2504.18422, 2025：本体+FOL+SMT）；LegalWiz（arXiv:2510.03418, 2025：NLI+LLM，6类矛盾+证据span） | 合同矛盾检测 | 文档级+类型化+证据定位的任务形态示范 |
| 神经符号混合线 | FormalJudge（arXiv:2602.11136）、VeriTrans（arXiv:2604.10341）、SAFER等，2025–2026 | LLM分解/翻译 + Z3/Dafny验证 | 形式化以"验证器"身份回归（见§4b） |
| **评测危机与修复** | Korn, Bartel, Unterbusch, Vogelsang（arXiv:2606.25550, 2026）证明LLM难以可靠生成/注入/检测带缺陷需求；CodeFuse-CommitEval（arXiv:2511.19875）证明规则引导的确定性mutation可行；Fantechi/Gnesi/Semini线在RE Open Data上做注入式不一致检测（RE@Next 2025） | 合成数据的可靠性本身成为研究对象 | mutation注入成为新的评测范式候选 |
| 多模态文档理解兴起 | FlowExtract（arXiv:2604.06770, APMS 2026投稿：YOLO+OCR流程图结构提取，节点F1 98.8% vs 最优VLM 34.0%，边66.7% vs 10.7%）；DeepSpecs（arXiv:2511.01305：5G规范跨引用递归解析） | 感知/聚合能力成熟，但**止步于提取与QA** | 多模态的"感知"已解决一半，"一致性"无人处理 |
| Femmer & Frattini | arXiv:2607.21319, 2026 | 把需求质量重构为信息论量 | 质量理论化的新尝试，仍单条文本级 |

**我们的发现（本项目2026年检索，证据见 `nlp4re_llm4re_comprehensive_survey.md` 与 `open_problems_analysis.md`）**：2024–2026年需求矛盾检测文献**全部**停留在句对/文本级（TSRCDF-SS句对、AraREQ句级、RE@Next纯文本安全需求、QRS 2025多图合并的"图"是概念依赖图而非图像）；"文档级多模态一致性"的任务定义本身是空白。同时LLM检测有系统性负面证据：S3CDA的GPT-4o领域退化（0.936→0.462）、ContraDoc（arXiv:2311.09182）长文档自矛盾不可靠、ECon（arXiv:2410.04068）"无理由偏向一方"。

**方法论特征**：LLM零/少样本判别与生成式消解；数据由LLM合成或规则注入；神经符号混合与检索增强并行；证据链输出开始出现（法律域）。

**局限（进行时）**：粒度未变（仍是句对）；评测分布可疑（合成偏差）；LLM领域退化与幻觉未被系统解决；文档结构（章节/表格/图）未被建模。

---

## 四、跨时代三主线

### 4a. 人工规则 → 自动学习（可解释性的持续流失与回收）

规则从未消失，只是书写者从人变为数据：时代1的证明义务、时代2的OCL式一致性规则、时代3的smell句法模式，均为**人写给机器**；时代4的LLM把规则隐式化为预训练知识，代价是UML/Analyzer能指出"违反了哪条规则"而LLM只能给出判断+自由文本解释。2025–2026的混合架构（GJB规则引擎做语法层、NLI做语义层、Z3做逻辑层）本质上是40年经验向"规则管可形式化部分、学习管语义部分"分层的收敛——GJB 438C这类标准提供的120条可执行规则存量，正是显式规则路线在LLM时代的复利。

### 4b. 形式化 → NLP → 神经符号回归（翻译成本的位置转移）

SCR/定理证明（完全形式化）→ Alloy/SAT（轻量形式化）→ Bendík的NL→逻辑→SAT（翻译瓶颈显性化）→ NLI句对（放弃形式化换取覆盖面）→ LLM+Z3/Dafny（形式化回归）。关键洞察：**形式化的成本从未消失，只是被转移到"自然语言→形式表示"的翻译环节**；LLM恰好大幅降低了翻译成本，使"LLM翻译+求解器验证"在2024年后突然可行（VeriTrans报告SAT编译正确率94.46%，FormalJudge较纯LLM提升16.6%，LLM+Lean幻觉减少59%——均见项目内调研核验）。时代1的逻辑学遗产（可满足性、最小不可满足子集）因此获得第二次生命。

### 4c. 消除不一致 → 管理不一致 → （断裂）→ 可容忍性的可学习复活

这是最具悲剧性的一条线。Balzer（1991）–Robinson & Fickas（1994）–Nuseibeh系列（1996–2001）建立了"不一致承载信息、应被监视而非消灭"的管理范式；Hunter & Nuseibeh（1998）与Spanoudakis & Zisman（2001）将其定名为领域议程。**ML时代该范式断裂**：检测器是二值分类器，没有严重性、没有可容忍性、没有归责；标注协议把benign variation当作标注噪声剔除（人们对"矛盾"容易达成一致、对"合理"各执一词——良性样本在金标准构建中被系统性丢弃，检测器被优化为不一致消除者）。AraREQ的"检测+消解"与Femmer & Frattini的质量重构是局部回归，但"该差异是否被许可"的判定仍无人处理。经典容忍框架的失效原因是它需要显式目标/视角模型作为前置输入（Robinson的goal monitor需要人工目标模型）——真实文档供给不了；而**类型先验是可从数据中校准的**（本项目M7双LLM裁决的类型×标签结构：异常流缺失π(real)≈0.79 vs 参与者缺失≈0.11，是这一方向的第一个实证信号）。这是经典容忍思想的可学习后代，也是方向B"合理差异vs真实矛盾"判定的历史正当性来源。

---

## 五、历史启示：三个从未解决的老问题

### 5.1 评测：四十年没有共享基准

时代1无数据（案例演示）；时代2各自建模（模型不可比）；时代3自建句对集（合成注入，F1之间无任何可比性却在引用链上被当作同一条进展曲线）；时代4用LLM造数据又被证伪（Korn 2026），规则mutation的修复方案（CodeFuse-CommitEval范式）尚未在RE域与真实不一致类型学对齐。**真实SRS上的gold standard从未建成**——16份真实GJB SRS（含真实矛盾：网络适配器4 vs 40、版本冲突V7.6 vs V8、ghost引用等）因此是稀缺资源；评测协议必须同时报告对齐指标与检测指标（见5.2）。

### 5.2 粒度：检测对象从未被正面回答

视点→模型→句对，每次换代的第一动作都是重新划定检测对象，但"什么构成一次检测的输入单元"从未有原则性回答。句对基准的"给定对"设计把聚合误差完全排除在指标外：所有论文报告的都是 P(detect | aligned)，而部署需要的是 P(detect) = P(detect | aligned)·P(align)——第二项被评测协议假设为1，因此**对齐误差在方法论上不可见**（本管线的pair↔图映射仅33.7%正确的教训，见 `open_problems_analysis.md` §3）。NLP界2021年已诊断并转向文档级（DocNLI、SummaC），RE领域继承NLI框架晚到、继承粒度教训更晚——本项目的"条目"（{文字片段, 关联图, 关联表行, 章节位置, 语义角色}）是对这一历史欠账的回答，GJB编号体系（需求ID/章节号/表号/图号）是天然锚点。

### 5.3 良性差异：被遗忘二十年的Chantree问题

2006年Chantree提出nocuous/benign之分后，该问题在ML时代消失（原因见§4c）。历史上三个最接近的遗产：Chantree的判据（依赖人工特征，无语境知识则失效）、经典容忍框架（需要显式目标模型）、LegalWiz的Specificity矛盾类型（把"宽窄之差"算作矛盾，回避而非解决问题）。**缺失的从来不是认识而是可操作的判定机制**——类型先验+语境许可知识（流程图惯例不画参与者、表格步骤比图节点细）是可行的形式化路径。四十年历史证明：不做此判定的工具会在第一天被工程师弃用（把所有差异报为不一致的工具）。

---

## 附A：勘误（对项目内已有调研文档）

1. **TSRCDF归属**：早期文档有"Ezzini等TSRCDF"的表述。经核验（DBLP/arXiv/引文分析）：句对冲突检测线为Guo(2021)→Malik等S3CDA(2022)→Wang等TSRCDF-SS(2025)，无更早的"TSRCDF"原始论文（该缩写系2511.23007自创，-SS指SBERT+SimCSE）；**Ezzini（Saad Ezzini，卢森堡大学）的RE贡献在歧义处理与QA（ICSE'21/22/23），其后转向text-to-SQL/阿拉伯NLP**。
2. **AraREQ团队**：非"Ezzini团队(KFUPM)"，作者为Hasanain Hammouda、Aljabari、Hamad、Jarrar（Birzeit University，LREC 2026，ACL Anthalogy已收录，27K句对）。
3. **Spanoudakis & Zisman综述出处**：非"ACM Computing Surveys 2001"，实为Handbook of Software Engineering and Knowledge Engineering书章（2001, pp.329–380, DOI:10.1142/9789812389718_0015）。
4. **S3CDA年份**：arXiv:2206.13690 v1提交于2022-06（项目内部分文档记为2020，应以2022为准）。
5. **Egyed修复论文**："Fixing Inconsistencies in UML Design Models"出处为ICSE 2007（pp.292–301），非OOPSLA。

## 附B：核验说明与不确定处标注

- **核验渠道**：DBLP publication API（Easterbrook/Robinson/Finkelstein/Nuseibeh/Küster-Egyed/Ezzini等作者页与标题检索）、Crossref API（DOI级核验：Balzer/Leite-Freeman/Lamsweerde/Heitmeyer/Engels/Alloy/Famelis/Cleland-Huang/Femmer/Ferrari/Bendík/Fantechi/Goknil/Mu/Grundy/Boiten/Ali/Zhu-Jin/Robinson-CSUR等）、arXiv API（Guo/S3CDA/Malik/Helmeczi/Zadenoori/DeepSpecs/ContractCheck/Korn/Femmer-Frattini/TSRCDF-SS等，含摘要与引文提取）、ACL Anthology（AraREQ/LREC 2026）、作者个人网站全文（Easterbrook@Toronto出版列表、RE'95论文PDF与1991年博士论文全文）。
- **[注1] MENVOIL与WSRE**：两个系统名在DBLP/OpenAlex/OpenAIRE/Google Books/作者论文与学位论文全文中均未能定位原始文献，主要经综述转引流传（如Hunter & Nuseibeh 1998；Spanoudakis & Zisman 2001）。MENVOIL应系Nuseibeh等的多种表示法视点集成环境（与TSE 1994框架论文关联）；WSRE常被归于Easterbrook，但Easterbrook本人的出版列表、RE'95论文与博士论文全文中均无"WSRE"字样，**引用时建议以两篇SEJ/TSE正式论文替代系统名**。
- **[注2] Spanoudakis & Zisman 2001**为Handbook书章（见勘误3）；该综述确立的"检测–容忍–消解"三分是本文§4c的叙事骨架。
- **[注3] "requirements trifecta"**：DBLP/arXiv/Crossref均未检索到以此为题的论文；该提法出自Famelis–Salay–Chechik组对"不确定性–部分模型–不一致"三位一体的表述（ICSE 2012/RE 2012系列），正文已按可核验论文引用。
- **[注4] AraREQ细节**（27K句对、LLM阿拉伯化+人工增广、4个LLM零/少样本评测）取自ACL Anthology收录页摘要；全文细节投稿前需精读（与既有调研建议一致）。
- **二手转引标注**：S3CDA的GPT-4o退化数据（0.936→0.462）、Korn 2026的注入不可靠结论、CodeFuse的mutation细节、FlowExtract精度、TSRCDF-SS方法细节（部分）等，来自项目内既有调研的核验记录（各文档已注明渠道），本次仅做抽查复核（抽查6篇全部属实）。
- **未能核验而谨慎使用的表述**：ViewPoints视点模板的五元结构、Egyed"只检查受影响规则子集"的机制细节，属领域公认常识性描述，未逐字核对原文。

---

*本文档为相关工作章节的历史叙事底稿。引用格式建议：正文用"作者 (年份)"，正式投稿前将文内条目转为BibTeX并复核页码。*
