# Visio建模图与文本协同的文献调研：先例、谱系与我们的定位

> 调研问题：把.doc内嵌Visio图解析为类型化结构化图模型（节点/边/坐标/类型），再与用例表格、正文文本做一致性比对——这种"Visio作为中间建模语言"的技术，之前有人做过吗？建模图+文本一致性有直接先例吗？
>
> 检索工具：arXiv API / DBLP API / OpenAlex API（2026-08检索）。所有条目已核实出处；个别凭领域常识引用的已在§8标注。

## 0. 一句话结论

**"Visio作为建模画布"有零散学术先例（2003-2009年MDE浪潮），"建模图+文本一致性检测"有直接先例（van der Aa et al. 2016，BPM领域）；但"解析文档内嵌Visio矢量对象→类型化图模型→与文本/表格做一致性比对"这条完整链路，未检索到任何先例。** 我们的位置处在三条已验证路线的交点上，且拥有它们都没有的东西：矢量级真值（无需从像素推断）。

---

## 1. 方向1：Visio作为建模工具的学术工作

DBLP中以"visio"为完整词的文献仅约89条（多为vision的前缀噪声之外的应用类文章），学术体量很小，但存在一条清晰的"Visio+模型工程"短线：

| 工作 | 出处 | 机制 | 与我们的关系 |
|---|---|---|---|
| Kern, Kremß, Kühne. *Modellinteroperabilität zwischen Microsoft Visio und Eclipse EMF als Mittel zur modellgetriebenen Integration*（Visio与Eclipse EMF的模型互操作） | GI Jahrestagung 2009, pp.3303-3307（DBLP: conf/gi/KernKK09） | 把Visio中的模型导出/转换为EMF元模型实例，实现Visio与模型驱动工程(MDE)工具链互操作 | **最接近的Visio+MDE学术工作**。说明"Visio图→元模型实例"的转换20年前就被认为可行且有价值；但方向是建模工具互操作，不是文档理解 |
| Halpin. *Database Modeling with Microsoft Visio for Enterprise Architects* | Morgan Kaufmann, 2003（OpenAlex核实） | Visio for Enterprise Architects（VS.NET 2003内置）作为ORM/ER数据库建模官方前端，图形→DDL生成 | 微软曾把Visio产品化为"企业建模工具"，Visio图形承载严格的语义模型（ORM）——"Visio=建模语言"的工业合法性依据 |
| *Designing Simulation Graphic Modeling Environment Based on Microsoft Visio 2002* | 2003（OpenAlex有记录，无DOI，被引1次） | 用Visio 2002做仿真领域的图形化建模环境 | Visio做领域DSL画布的早期例子，影响力低 |
| Lin, Chen, Sun, Dromey. *Leveraging Single-User Microsoft Visio for Multi-user Real-Time Collaboration* | CDVE 2007（DOI:10.1007/978-3-540-74780-2_48） | 把单机Visio改造为实时协同建模画布 | Visio作为建模画布的协同扩展，与一致性无关 |

**工业事实（非论文，引用时标注）**：
- David Parker《Microsoft Visio 2010 Business Process Diagramming and Validation》(Packt, 2010)：Visio 2010起内置Validation Engine，可对BPMN图做规则校验，规则以表达式挂在stencil的master shape上——**"规则化校验Visio图"已被产品化**，但只校验图自身合规性，不与文本比对。
- 微软Visio"Export to Power Automate"：流程图→可执行工作流，说明"Visio图→机器可读模型"是微软自己的官方场景。
- GJB/军工体系内Visio模板（stencil）广泛用于接口图、部署图——这正是我们数据集的形态。

**谱系背景（常识引用，见§8）**：Visio-as-DSL属于meta-CASE/DSM工具家族（MetaEdit+、AToM3、GME，及微软自己的Visual Studio DSL Tools，Cook/Jones/Kent/Wills 2007）。这个家族的核心思想——"画布+元模型+生成器"——正是我们"Visio XML→类型化图模型"的理论依据。

**小结**：Visio作为建模**前端**有先例；Visio作为**文档理解的中间语言**（从文档中反向解析）没有先例。

---

## 2. 方向2：建模图与文本的协同——一致性检测（核心）

### 2.1 最直接先例：BPM领域

- **★ van der Aa, Leopold, Reijers (2016). *Comparing textual descriptions to process models – The automatic detection of inconsistencies*. Information Systems, DOI:10.1016/j.is.2016.07.010（被引61）**
  - 机制：将流程模型的活动（activity）与自然语言文本描述做对齐（activity-label matching），自动检测两类不一致——文本提到但模型没有的活动、文本与模型矛盾的行为（顺序/分支）。
  - **这是"建模图 vs 文本"一致性检测的标志性工作，必引。**
  - 局限：模型已是机器可读的BPMN XML（建模工具产物），不从文档解析；粒度为活动级；无表格模态。

### 2.2 RE领域：多视图一致性谱系

- **Nuseibeh, Kramer, Finkelstein (1994). *A framework for expressing the relationships between multiple views in requirements specification*. IEEE TSE 20(10), DOI:10.1109/32.328995（被引545）**：多视图需求（文字视图、图形视图……）间关系的形式化表达+不一致管理——我们"图/表/文三视图一致性"的理论源头，写Related Work时的开篇引用。
- **Kamalrudin, Grundy, Hosking (2010). *Managing Consistency between Textual Requirements, Abstract Interactions and Essential Use Cases*. COMPSAC 2010, DOI:10.1109/COMPSAC.2010.40**：文本需求与Essential Use Case模型间的一致性管理工具（EUCM），与我们的"用例图 vs 文本"最贴近，但模型由人维护。
- **Yue, Briand, Labiche：aToucan**（MODELS 2015工具论文，DOI:10.1145/2699697，被引100；Yue 2010年Carleton博士论文同题）：从结构化文本用例自动推导UML分析模型（类图/顺序图/用例图）——"文本→模型"方向的经典，反面印证"文本与模型应可互检"。

### 2.3 UML一致性规则谱系（模型-模型为主，可借其规则类型学）

- Torre, Labiche, Genero. *UML consistency rules*. EASE 2014（DOI:10.1145/2601248.2601292）
- **Torre, Labiche, Genero, Elaasar (2018). *A systematic identification of consistency rules for UML diagrams*. JSS, DOI:10.1016/j.jss.2018.06.029（被引46）**：系统化梳理UML图间一致性规则（类图vs顺序图vs状态图……），有专门workshop（WUCOR 2015, DOI:10.1145/2894784.2894801）。
- Engels, Hausmann, Heckel, Sauer. *Rule-Based Specification of Behavioral Consistency Based on the UML Meta-model*. 2001（DOI:10.1007/3-540-45441-1_21，被引90）：基于元模型的行为一致性规则——**"在元模型层定义一致性规则"的方法论原型**，可直接迁移到我们的Visio图模型。
- 意义：这一支证明了"图-图一致性规则"可以系统枚举和机器执行，但**几乎不做"图-自由文本"**——后者正是我们的空档。

### 2.4 LLM时代（2023-2026）：生成侧反推一致性需求

- **Ferrari, Abualhaija, Arora (2024). *Model Generation with LLMs: From Requirements to UML Sequence Diagrams*. REW 2024, arXiv:2404.06371（被引67）**：ChatGPT从28份需求文档生成顺序图，发现当需求含ambiguity/**inconsistency** smells时生成图的正确性/完整性显著劣化——**从生成侧证明"文本-模型一致性"是真实痛点**，是我们立论的直接外部证据。
- Matei et al. (2026). *Ambiguity Detection and Elimination in Automated Executable Process Modeling*. arXiv:2604.10884：反复生成可执行BPMN并仿真，用KPI分布差异检测文本↔模型行为不一致，回溯定位到文本片段——"重复生成做一致性检测"的新范式（与我们"多源互检"思路互补）。
- Rouabhia, Hadjadj (2024). *Enhancing Class Diagram Dynamics: A Natural Language Approach with ChatGPT*. arXiv:2406.11002：**从用例表格**驱动ChatGPT增量生成PlantUML类图——"表格→图"生成先例，与我们的"用例表格 vs 图"检测方向互为镜像。

### 2.5 与我们的差异（写论文时的对照表）

| 维度 | van der Aa 2016 | Kamalrudin 2010 | Ferrari 2024 | **我们** |
|---|---|---|---|---|
| 模型来源 | BPMN XML（工具产物） | 人工维护的EUC | LLM生成 | **从.doc内嵌Visio矢量解析** |
| 模态 | 图+文本 | 图+文本 | 文本→图 | **图+表格+文本三模态** |
| 检测对象 | 活动缺失/行为矛盾 | 用例-需求偏差 | 生成质量分析 | **参数/接口/逻辑三层不一致** |
| 文档域 | 公开流程描述 | 学术案例 | 28份公开需求 | **16份真实GJB军事SRS** |

---

## 3. 方向3：中间表示/中间建模语言的谱系

我们"Visio XML→类型化图模型"在如下谱系中：

1. **图的图解析：Diagram Parse Graphs (DPG)**——Kembhavi, Salvato, Kolve, Seo, Hajishirzi, Farhadi. *A Diagram Is Worth A Dozen Images*. ECCV 2016, arXiv:1603.07396：把图示解析为带类型节点/有向关系的图，在其上做QA与推理；配套AI2D数据集（5000+图全标注）。**"图→类型化图模型"的思想源头，从像素解析。**
2. **文本的图IR：AMR**（Banarescu et al., LAW 2013，常识引用）：句子→语义图，证明"跨模态统一到图结构再推理"的有效性。
3. **视觉的图IR：Scene Graph / Visual Genome**（Krishna et al., IJCV 2017，常识引用）：图像→场景图，视觉-语言对齐的中间层。
4. **建模语言的原生中间层：MOF/Ecore/EMF**（OMG标准；Steinberg et al., *Eclipse Modeling Framework*, 2008，常识引用）：一切模型皆有元模型——我们的"类型化图模型"本质上是一个小型Ecore风格元模型（VisioShape/VisioEdge/VisioDiagram）。
5. **文本化图IR：Graphviz DOT / PlantUML / Mermaid**。近两年有实证比较：
   - **Brissard, Cuppens, Zouaq (2025). *What is the Best Process Model Representation? A Comparative Analysis for Process Modeling with LLMs*. AI4BPM 2025, arXiv:2507.11356**：9种流程模型表示对比，**Mermaid综合得分最高**；
   - **Licardo, Tankovic, Etinger (2025). *BPMN Assistant*. arXiv:2509.24592**：专为LLM设计的JSON中间表示在编辑任务上**显著优于直接操作BPMN XML**（token省75%+，延迟降43%）；
   - Härer (2023). *Conceptual Model Interpreter for Large Language Models*. ER Forum 2023, arXiv:2311.07605：LLM生成PlantUML/Graphviz文本语法→自动渲染。
   - **启示：我们的图模型应同时输出JSON（机器消费）与Mermaid类文本（LLM消费+复用现有评测生态）。**
6. **生成侧的同构思想**：DiagrammerGPT（Zala, Lin, Cho, Bansal. COLM 2024, arXiv:2310.12128）用LLM先产生结构化"diagram plan"再渲染图——**图=结构化中间表示的投影**，与我们"图=Visio XML的投影"互为正反方向。同类：LegalViz（Onami et al., NAACL 2025, arXiv:2502.06147，法律文本→DOT图，7010对，图结构+内容双评测）；DiagramAgent（Wei et al. 2024, arXiv:2411.11916，含Diagram-to-Code逆向agent）；GeoLoom（Wei et al. 2025, arXiv:2512.08180，形式语言GeoLingua+约束求解器生成几何图）。

**我们的位置**：**矢量级DPG（authoring-format-level parsing）**。DPG从像素推断结构；我们从OLE内嵌的Visio XML直接获得节点/边/坐标/连接/形状类型的**精确真值**——把"识别问题"变成"解析问题"。在谱系上这是DPG思想的严格上溯（像素级→创作格式级），且比DOT/Mermaid多出几何与类型信息。

---

## 4. 方向4：企业工作流中的模型抽取（图→模型）

### 4.1 文本→BPMN（活跃赛道，可借其评测协议）

- Kourani, Berti, Schuster, **van der Aalst**. *Process Modeling With Large Language Models*. 2024, arXiv:2403.07541：LLM+迭代精化生成流程模型，导出BPMN/Petri网。
- InstruBPM（Çelikmasat, Özgövde, Aydemir. 2025, arXiv:2512.12063）：指令微调开源模型生成BPMN，用**Relative Graph Edit Distance**做结构保真评测——评测指标可借。
- 综述：Bettencourt, Guerreiro (2026). *LLMs to Enhance Business Process Modeling: Past, Present, and Future Trends*. arXiv:2604.14034；评测框架：BEF4LLM（Lauer et al., Information Systems 2026, arXiv:2601.21787，语法/语用/语义/效度四维）。

### 4.2 图像→模型（我们的直接竞品路线）

- **FloCo / FloCo-T5**（Shukla et al., ICDAR 2023, arXiv:2501.17441）：流程图图像→可执行Python代码，11884对图像-代码数据集。
- **FlowLearn**（Pan, Zhang, Caragea, Dragut, Latecki. ECAI 2024, arXiv:2407.05183）：3858张科学流程图+10000合成图，**标注含Mermaid代码**——图像→Mermaid的benchmark。
- **FlowVQA**（Singh et al., ACL 2024 Findings, arXiv:2406.19237）：2272张流程图+22413个QA对。
- **FlowCE**（Zhang et al. 2024, arXiv:2406.10057，360 AI Lab）：首个MLLM流程图能力多维评测，**含Logical Verification（逻辑校验）维度**——GPT-4o仅56.63分，说明任务远未解决。
- **EdgeFlow**（Dou, Hassani, Wei. 2026, arXiv:2605.27332）：用Canny边缘图作结构先验增强VLM做**工业需求文档中的**流程图→Mermaid转换（自建IndusReqFlow真实需求数据集），节点F1提升17.39pp——**与我们域最接近的工作**，但仍在和像素歧义搏斗。
- Arrow-Guided VLM（Omasa et al. 2025, arXiv:2505.07864）：箭头方向显式编码增强VLM流程图理解。

### 4.3 缺口

- **未检索到任何"从Visio图库/Visio文件做process mining或BPMN抽取"的学术论文**（DBLP/OpenAlex/arXiv多检索式下均无）——企业确有海量Visio流程资产（微软官方导出场景为证），但学术上是空白；**我们的Visio解析恰好落在这个空白里**。

---

## 5. 方向5：多模态文档理解中的图+表+文联合（2024-2026）

- **SciVer**（Wang, Shen, Kuang, Cohan, Zhao. 2025, arXiv:2506.15569）：3000例专家标注的科学论文多模态断言验证，**要求模型在图+文中定位支持/反驳证据**——"图文一致性验证benchmark化"的代表作，其证据标注设计可借鉴到我们的Gold Standard。
- **DeepSpecs**（Ganapathy Manvattira et al. 2025, arXiv:2511.01305）：5G规范专家级QA，**递归解析交叉引用**+规范演化追踪——与SRS跨章节关联（方向A）同构，证明"结构化+引用解析"路线在标准文档上的价值。
- **AssertCoder**（Tian et al. 2025, arXiv:2507.10338）：多模态硬件设计规格（**文本/表格/图/公式**）→模态感知解析→结构化语义表示→SVA断言生成——四模态规格解析的先例（硬件域），其"modality-sensitive preprocessing"命名与我们的问题几乎同构。
- **VisRAG**（Yu et al. 2024, arXiv:2410.10594）：文档页面直接以图像嵌入做RAG（规避解析损失），端到端超越文本RAG 20-40%——代表"不解析、整页进模型"的相反哲学；我们代表"深度解析"一极，二者构成光谱两端，可作 framing。
- **TelcoAI**（Ghosh et al. 2025, arXiv:2601.16984）：3GPP规范的多模态agentic RAG，文本+图联合检索。
- 基础设施层：DocVQA（Mathew et al., WACV 2021, DOI:10.1109/WACV48630.2021.00225，被引439）；Chart-to-Text（Obeid & Hoque 2020, arXiv:2010.09142；Kantharaj et al., ACL 2022, arXiv:2203.06486）——图→文本生成侧的规模化先例（图表captioning）。

---

## 6. 核心问题回答

### a. "Visio作为中间建模载体"有学术先例吗？

**半有。**"Visio作为建模前端/互操作源"有先例：Kern 2009（Visio↔EMF互操作，学术）、Halpin 2003（Visio for Enterprise Architects，微软产品化的ORM建模）、Visio 2010 Validation Engine（工业，规则校验Visio图）。**但"把文档内嵌的Visio当作中间建模语言反向解析"——即Visio XML→类型化图模型→支撑文档级一致性分析——没有任何先例。** DBLP上"visio"完整词仅约89条命中，无文档理解方向工作。我们的提法有工业合法性（微软自己把Visio当建模语言），无学术占位（空白）。

### b. "建模图+文本一致性"有直接先例吗？

**有，且必须引用并划清差异。**最直接的是 van der Aa, Leopold, Reijers (2016, Information Systems)：流程模型 vs 文本描述的不一致自动检测。向上可追溯到 Nuseibeh/Kramer/Finkelstein (1994) 的多视图一致性框架和 Kamalrudin et al. (2010) 的文本-用例模型一致性管理。**与我们的四点差异**：
1. **模型来源**：先例的模型都是机器可读的建模工具产物（BPMN/UML XML）或人工维护；我们从.doc内嵌Visio对象解析——多出一个完整的"文档图抽取"子问题（方向A的贡献空间）；
2. **模态**：先例是图+文本两模态；我们是图+表格+文本三模态（GJB SRS以表格见长）；
3. **不一致类型学**：先例集中在活动/行为级；我们做参数值级（同参数不同值）到逻辑级（约束可满足性）的三层检测；
4. **文档域与评测**：先例用公开/合成数据；我们用16份真实GJB军事SRS（数据本身是贡献）。

### c. 最接近的工作清单（必引）

| # | 工作 | 为什么必引 |
|---|---|---|
| 1 | van der Aa, Leopold, Reijers 2016 (IS) | 图-文一致性检测的直接先例 |
| 2 | Nuseibeh, Kramer, Finkelstein 1994 (TSE) | 多视图一致性理论源头 |
| 3 | Kembhavi et al. 2016 (ECCV) | DPG：图的类型化图模型思想源头 |
| 4 | TextFlow (Ye et al. 2024, arXiv:2412.16420) | 中间文本表示优于端到端VLM的实证 |
| 5 | EdgeFlow (Dou et al. 2026, arXiv:2605.27332) | 工业需求流程图→模型的最新竞品（像素路线） |
| 6 | FloCo (ICDAR 2023) / FlowLearn (ECAI 2024) | 流程图→代码/Mermaid的benchmark |
| 7 | Ferrari, Abualhaija, Arora 2024 (REW) | 需求smells（含不一致）损害图生成的证据 |
| 8 | Torre et al. 2018 (JSS) | UML一致性规则的系统化类型学 |
| 9 | Yue et al. aToucan 2015 (MODELS) | 文本用例→UML模型的经典（反向） |
| 10 | Kern et al. 2009 (GI) | Visio↔EMF互操作，Visio+MDE唯一直接学术先例 |
| 11 | Halpin 2003 (MK book) | Visio作为正式建模载体的工业合法性 |
| 12 | Brissard et al. 2025 (AI4BPM) | 中间表示选型的实证比较（Mermaid最佳） |
| 13 | BPMN Assistant 2025 (arXiv:2509.24592) | 专用JSON IR优于原始XML的实证 |
| 14 | DiagrammerGPT (COLM 2024) / LegalViz (NAACL 2025) | 文本→图生成侧的结构化中间表示 |
| 15 | DeepSpecs 2025 / AssertCoder 2025 / SciVer 2025 | 多模态规格解析与断言验证的近期趋势 |
| 16 | Kamalrudin et al. 2010 (COMPSAC) | RE域文本-用例模型一致性管理 |

---

## 7. 对我们"深化Visio解析能力"路线的启示

1. **中间表示路线已被独立反复验证**——TextFlow（文本IR优于端到端VLM）、BPMN Assistant（JSON IR优于XML）、PMR对比（Mermaid最佳）、LegalViz（DOT）。我们的图模型应设计为**双出口**：类型化JSON（供规则/Z3/图算法）+ Mermaid类文本投影（供LLM消费，并直接接入FlowVQA/FlowLearn式评测生态）。
2. **核心差异化论点：矢量真值 vs 像素推断**。EdgeFlow用Canny边缘先验才换来17pp的F1提升；我们从OLE内嵌Visio XML直接拿到节点/边/坐标/形状类型的精确真值，**把识别问题变成解析问题**。这应作为论文的立论句，并可设计"同一批图：Visio通道 vs VLM通道"的对照实验量化优势。
3. **双通道架构作为对冲与贡献点**：并非所有插图都是Visio（存在EMF/WMF/位图）。可规划"Visio矢量解析为主、EdgeFlow式VLM为兜底"的双通道，两通道输出到同一图模型元模型——这既是工程对冲，也是天然的消融实验。
4. **一致性规则类型学可从UML谱系移植**：Torre et al. 2018与Engels et al. 2001的"元模型层定义一致性规则"方法论，可直接套用到Visio图模型上（图-图、图-表、图-文三类规则分开定义）；Visio 2010 Validation Engine"规则挂在master shape上"的机制说明stencil/masterr形状是天然的规则锚点。
5. **评测空白=数据贡献**：RE域不存在"文档内图-表-文一致性"的gold standard。SciVer的证据标注设计、FlowCE的Logical Verification维度、InstruBPM的Graph Edit Distance指标均可借鉴；16份真实SRS+标注可成为首个此类benchmark（与项目Gold Standard计划衔接）。
6. **论文framing建议**：相关工作分三支（model-text consistency / diagram parsing→IR / multimodal doc understanding），把我们定位为 **"authoring-format-level diagram parsing for RE consistency"**——与pixel-level（FloCo/EdgeFlow）和text-level（van der Aa）构成二维矩阵中的第三象限，即：真实文档+矢量解析+三模态一致性。
7. **风险提示**：VSD（二进制OLE）与VSDX（OOXML）解析难度差异大；形状→语义类型（用例/状态/接口）映射依赖stencil识别，GJB定制模板可能无公开schema，需要从数据集归纳（这本身可成为贡献：GJB图元模型）。

---

## 8. 出处核实说明

- **arXiv API核实**：DiagrammerGPT(2310.12128)、DeepSpecs(2511.01305)、DiagramAgent(2411.11916)、LegalViz(2502.06147)、GeoLoom(2512.08180)、AssertCoder(2507.10338)、Kembhavi DPG(1603.07396)、SciVer(2506.15569)、TextFlow(2412.16420)、FloCo(2501.17441)、FlowLearn(2407.05183)、FlowVQA(2406.19237)、FlowCE(2406.10057)、EdgeFlow(2605.27332)、Arrow-Guided VLM(2505.07864)、Ferrari(2404.06371)、Rouabhia(2406.11002)、Härer(2311.07605)、Kourani(2403.07541)、InstruBPM(2512.12063)、BPMN Assistant(2509.24592)、BEF4LLM(2601.21787)、BPM综述(2604.14034)、PMR对比(2507.11356)、Matei(2604.10884)、VisRAG(2410.10594)、TelcoAI(2601.16984)、Chart-to-Text(2010.09142/2203.06486)。
- **DBLP核实**：Kern 2009（conf/gi/KernKK09）、Lin 2007（CDVE）；DBLP词补全显示"visio"完整词约89条。
- **OpenAlex核实**：van der Aa 2016（含作者/期刊）、Nuseibeh 1994、Kamalrudin 2010（含作者）、Torre 2014/2018（含作者）、aToucan(10.1145/2699697)、Yue 2010博士论文、WUCOR 2015、Engels 2001、Halpin 2003（年份/第一作者）、DocVQA(WACV 2021)、仿真建模环境2003、"Microsoft Visio"检索的全部标题。
- **常识引用（未走API，但为领域公认）**：AMR(Banarescu et al. 2013)、Visual Genome(Krishna et al. 2017)、EMF/Ecore(Steinberg et al. 2008)、OMG MOF、MetaEdit+(Kelly & Tolvanen 2008)、AToM3(de Lara & Vangheluwe 2002)、VS DSL Tools书(Cook et al. 2007)、Parker的Visio 2010 Validation书(2010)、微软Power Automate导出功能——引用时建议二次核对版本年份。
- **不确定/未找到**："process mining from Visio"无学术结果（多检索式）；DBLP引号精确检索"visio"返回500错误，89条数字来自词补全统计，供参考。
