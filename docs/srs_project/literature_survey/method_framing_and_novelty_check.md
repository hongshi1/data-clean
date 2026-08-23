# ACDD方法框架定位与撞车检查报告
## Anchor-Calibrated Disagreement Decoding：新颖性验证、理论挂靠与贡献声明设计

> 调研日期：2026-08-24
> 性质：纯文献调研，不写代码
> 检索渠道：arXiv API（30+组关键词，全部命中结果经摘要核实）、DBLP API（会议论文）、Crossref API、DuckDuckGo/Marginalia web检索、conf.researchr.org（RE 2025程序委员会页面直查）。OpenAlex当日限额、Semantic Scholar持续429、Bing/Mojeek反爬，已用其余渠道交叉补齐。
> 与已有调研关系：建立在 `nlp4re_llm4re_comprehensive_survey.md`（NLP4RE全景）、`diagram_extraction_technology_spectrum.md`（图表提取谱系）、`uml_diagram_understanding_survey.md`（VLM可信度）、`cross_modal_consistency_survey.md`（跨模态一致性）之上，本文档只回答ACDD方法层面的撞车/理论/写法问题。

---

## 0. ACDD方法回顾（作为检查基准）

1. **锚点**：军事 .doc 文档内嵌 Visio XML 源文件可 100% 保真提取图表结构，作为 born-digital 金标准锚点。
2. **校准**：用锚点免费估计各感知通道（VLM/OCR/检测器）的（结构化）错误模型。
3. **解码**：把"通道输出 vs 文本"的分歧解码为 P(提取误差) vs P(文档真实不一致) 的后验。
4. **弃权**：后验不确定时弃权转人工（selective prediction）。
5. **理论挂靠**：LUPI（训练时有源文件、推理时无）。

---

## 任务A：撞车检查

### A.1 检索总览（12个方向）

| # | 方向 | 检索词代表 | 直接撞车 | 最近邻工作 |
|---|------|-----------|---------|-----------|
| 1 | 需求不一致检测×LLM | "requirement inconsistency/conflict detection" + LLM | **无**（无文档级多模态工作） | TSRCDF、AraREQ、RE2025 Fantechi等8篇（见A.2） |
| 2 | born-digital ground truth | "born-digital" + parsing/ground truth | 无（作为"校准锚点"用途无先例） | ChemScraper（born-digital PDF原语做解析） |
| 3 | silver labels图表解析 | "silver labels" + diagram/document | 无 | FlowExtract（检测式提取）、PWS系列 |
| 4 | anchor calibration / PI文档AI | "anchor"+"calibration"；"privileged information" | 无（PI×文档AI零命中） | HarmTrace（**术语撞车**：Anchor-Calibrated） |
| 5 | noise-aware verification / 提取误差vs内容误差 | "extraction error"、"noise-aware verification" | 无（该二分法的后验解码无先例） | Cox回归校准AI提取误差（生物统计） |
| 6 | LUPI近年应用 | "learning using privileged information" | 无（文档AI场景零命中） | PI×label noise三篇（见A.4，**框架级威胁**） |
| 7 | Visio XML/嵌入对象提取 | Visio / vsdx / VDX / OLE embedded | **无**（arXiv全库零命中Visio XML解析） | GenAI-DrawIO-Creator（drawio XML生成图）、NTT XML-driven LLM |
| 8 | 模型分歧→错误检测 | "model disagreement"+"error detection" | 无（分歧→因果归因解码无先例） | Selective Prediction from Agreement、GUI agents双通道 |
| 9 | 弃权式信息抽取 | "selective prediction"+IE / abstention+document | 无 | AgentFinVQA（chart QA弃权）、selective classification系列 |
| 10 | 图-文/流程图-表一致性 | diagram+consistency (cs.SE) | 无（渲染图vs正文的一致性无先例） | 经典UML模型间一致性检查（2003-2015，模型对模型） |
| 11 | 意图-呈现漂移 / 源-渲染diff | provenance drift / source vs render / stale | **无**（该命名的不一致类型无先例） | code-doc过时检测线、GUI pixels-vs-structure |
| 12 | RE/REFSQ/ICSE 2024-2026矛盾检测 | DBLP venue检索 | 无（见A.2逐篇） | — |

**总体判断**：没有任何一篇论文同时占据"文档内多模态 + born-digital锚点校准 + 分歧→误差/不一致归因 + 弃权"这个组合。但**每一个单件都有成熟先例**，撞车风险全部是"组合被拆解"型而非"整体被做掉"型。

### A.2 方向1&12：需求矛盾检测（Ezzini线/Bendík线的最新延续）

| 工作 | 出处 | 核心机制 | 与ACDD差异 | 威胁 |
|------|------|---------|-----------|------|
| **TSRCDF-SS**: A transfer learning approach for conflicts detection in requirement sentence pairs based on dual encoders | arXiv:2511.23007 (2025) | 双编码器+迁移学习，句对冲突/重复分类 | 句对级、纯文本、无锚点无校准 | 中（拥有"ML做需求冲突检测"的赛道话语权） |
| **AraREQ**: A Dataset and End-to-End System for Conflict Detection and Resolution in Software Requirements | LREC 2026 | 数据集+端到端冲突检测与消解系统 | Ezzini团队（KFUPM）新延续；句级、纯文本（阿拉伯语域） | 中（投稿前必须精读全文） |
| Combining Established and Emerging Techniques to Detect Inconsistencies in Requirements | RE 2025 RE@Next (Fantechi/Gnesi/Semini) | 规则聚类+LLM混合，RE Open Data安全需求文档，**注入式**不一致 | 纯文本、注入矛盾、无误差模型 | 中低 |
| Automatic conflict detection and resolution in digital service network requirement models using LLMs | Service Oriented Computing and Appl. 2026 | LLM对需求模型做冲突检测+消解 | 模型级（非文档级） | 低 |
| A Hybrid Framework for Inconsistency Detection in Diversity Requirements: Multi-Graph Merging + LLM | QRS 2025 | 多图合并+LLM | 纯文本 | 低 |
| Requirements Conflicts Detection: Advancing with Conversational AI | RE Workshops 2024 | 对话式AI辅助 | 交互式、纯文本 | 低 |
| Enabling Efficient Real-Time Requirements Inconsistency Detection for Safety-Critical Systems | RE Workshops 2024 | 实时化工程 | 纯文本工程化 | 低 |
| Inconsistency Detection in NL Requirements using ChatGPT: Preliminary Evaluation | RE 2023 | ChatGPT直接判不一致 | 初步评测，证明LLM可行但不可靠 | 低 |
| Conflict Detection of Functional Requirements Based on Clustering and Rule-Based System | IEEE Access 2024 | 聚类+规则 | 纯文本 | 低 |
| Detecting DTC Requirement-Implementation Inconsistencies Using LLMs | IEEE Software 2025 (Waterloo) | 需求vs代码不一致 | 对象是code不是文档内多模态 | 低（引用即可） |
| LLM-based Satisfiability Checking of String Requirements | RE 2025 (McGill) | LLM+约束生成做可满足性检查 | 逻辑层单点，无多模态 | 低 |
| QUARE: Quality-Aware Requirements Analysis via Multi-Agent Dialectical Negotiation | arXiv:2603.11890 | 多智能体辩证协商做质量分析 | 质量属性权衡，非矛盾检测 | 低 |
| Bendík 2017依赖图+SAT线 | （旧调研已收录） | 依赖图+SAT可满足性 | 需人工形式化，无感知误差问题 | 低（作为逻辑层模块引用） |

**结论**：RE领域的矛盾检测全部停留在**句对/文本级**；没有任何工作处理"同一实体散布在正文+图+表"的文档级聚合（与旧调研结论一致，2024-2026无变化）。Ezzini本人已转向text-to-SQL/阿拉伯NLP（DBLP作者页核实），其线由AraREQ延续。**"文档级多模态需求一致性"的任务定义本身仍是空白**——这是ACDD的赛道红利。

### A.3 方向2/3/7：born-digital锚点、silver标签、Visio/嵌入对象

| 工作 | 出处 | 核心机制 | 与ACDD差异 | 威胁 |
|------|------|---------|-----------|------|
| **ChemScraper** | arXiv:2311.12161, ICDAR 2024 | 用born-digital PDF图形指令（线/字/多边形原语）直接解析分子图，并衍生训练数据（MolScraper） | born-digital源做**解析/训练**的先例；不做误差校准、不做一致性 | **中**（"born-digital=免费金标准"的思想先例，必须引用并划界） |
| TrueType Transformer | arXiv:2203.05338 | outline矢量格式字符识别（born-digital字体轮廓） | 字符级识别 | 低 |
| XML-driven LLM Solutions (NTT) | arXiv:2502.04389 | 从xlsx/pptx/docx源文件提取形状元数据→LLM推理，绕开视觉 | 提取源文件结构做**问答**，未做校准/一致性 | **中**（Office系源文件提取的最近先例；旧调研已收录，本报告再确认） |
| FlowExtract | arXiv:2604.06770 (APMS 2026) | YOLO检测+OCR+几何追踪提取流程图；节点F1≈98% | 检测式提取；被旧调研定位为"可被Visio反向训练silver标签" | 中（感知通道之一，非竞争） |
| DocAtlas | arXiv:2605.12623 | 80+语言高保真OCR数据集构建框架 | 数据集构建，模型标注管线 | 低 |
| GRAFT | arXiv:2508.15690 | 程序化生成图表+渲染表格，配对结构，评测视觉-文本对齐 | 程序化GT评测图文对齐的先例（但为合成基准，非真实文档锚点校准） | 中低 |
| SciFlow-Bench | arXiv:2602.09809 | 逆解析(inverse parsing)评测结构感知的图生成 | 渲染↔结构双向思想的先例（生成方向） | 低 |
| GenAI-DrawIO-Creator | arXiv:2601.05162 | LLM在drawio XML结构上自动生成/操纵图 | XML作为图的结构化表示层（生成方向） | 低 |
| **Visio XML解析** | arXiv全库检索 Visio/vsdx/VDX | — | **零命中**（"Visio"仅匹配visio-linguistic假阳性） | **无** |

**结论**：
- **"嵌入式Visio XML作为born-digital锚点"在学术上是零先例的数据资源发现**——这可以作为资源型贡献，但要把声明收窄为"首次将.doc内嵌Visio对象用作SRS图表结构金标准"，不能说"首次发现born-digital可当GT"（ChemScraper已用PDF原语当GT）。
- ACDD相对ChemScraper/NTT的**真正增量**是：锚点不用于解析本身，而用于（a）校准多通道**误差模型**，（b）给"分歧"提供**因果归因**（提取误差vs真实不一致）。这两点在方向2/3/7的检索中零命中。

### A.4 方向4/5/6/8/9：校准、噪声、LUPI、分歧、弃权（方法核心的威胁区）

| 工作 | 出处 | 核心机制 | 与ACDD差异 | 威胁 |
|------|------|---------|-----------|------|
| **Transfer and Marginalize: Explaining Away Label Noise with Privileged Information** | arXiv:2202.09244 (ICLR'22线) | 用训练时特权信息（如标注者ID）解释掉标签噪声 | **"PI区分噪声与信号"的思想先例**；但PI是特征级、目标是标签去噪，不是感知通道误差模型 | **中高（框架级）** |
| When does Privileged Information Explain Away Label Noise? | arXiv:2303.01806 | 分析PI何时/为何能消除标签噪声 | 理论分析 | 中高（同上，必须引用并划界） |
| **Pi-DUAL** | arXiv:2310.06600 | 双网络用PI区分clean/noisy标签 | 同上，方法实例 | 中高 |
| Rethinking Knowledge Transfer in LUPI | arXiv:2408.14319 | 系统分析LUPI中知识传递机制 | 理论参照系 | 低（引用支撑） |
| LUPI近期应用（目标检测2601.02016、垃圾检测2508.04124、冷启动2607.17070、医学预后2601.00626、时序2505.02138） | 2024-2026 | teacher-student式注入特权信息 | 全部是**训练增强**用途；无文档AI场景；无"误差归因"用途 | 低（证明LUPI范式活跃，引用3-4篇即可） |
| **Bias-corrected Cox regression with AI-extracted covariates via calibration summary statistics** | arXiv:2607.25868 | 数据商在金标样本上验证AI提取精度→下游用校准统计量修正回归 | **"金标子集校准提取误差"的统计学先例**（测量误差修正/回归校准传统）；但为标量精度、单通道、生物统计场景 | **中（作为替代理论框架比作为撞车更危险）** |
| 程序化弱监督（Snorkel系；Refining LFs with Limited Labeled Data arXiv:2505.23470；Reliable PWS with CIs arXiv:2508.03896） | 2016-2026 | 多个噪声标注函数+小规模标注子集→概率标签 | **最接近"锚点校准+多通道融合"的现成机制**（见A.6详述） | **高（审稿人最可能的一句话否决）** |
| Dawid-Skene / truth discovery | 经典+持续活跃 | 多标注者混淆矩阵→逐条后验 | 同上 | 高（同上） |
| **Selective Prediction from Agreement** | arXiv:2605.02611 | 模型间一致性→选择性预测（Lipschitz版本空间） | "分歧→弃权"的思想先例；但分歧只触发弃权，不归因、不校准 | **中** |
| Deep Ensembles分歧→OOD/误差（Lakshminarayanan 2017；Jiang et al. 2022 disagreement估计泛化） | 经典 | 集成分歧作为不确定性代理 | 不确定性代理≠因果归因 | 中低（必须引用） |
| **Do GUI Agents Believe Their Eyes? Pixels versus Structure** | arXiv:2607.04334 | GUI智能体的"渲染像素vs DOM结构"双通道信念诊断 | **方法论最近的表亲**：同样面对"像素vs结构化源"双冗余通道；但只做诊断（agent依赖哪条），不做校准/一致性输出 | **中（必须显式对比）** |
| Dual-Confidence Contrastive Decoding for RAG | arXiv:2607.00570 | 对陈旧/噪声/冲突证据的双置信对比解码 | "disagreement/contrastive decoding"词汇相邻；证据为文本文档 | 中低 |
| AgentFinVQA | arXiv:2606.19782 | 金融chart QA多智能体管线，输出可信度分层 | chart QA中的弃权先例 | 中低 |
| Uncertainty-Aware Decision Making in MLLMs | arXiv:2608.17084 | 多模态证据的不确定性综述/框架 | 弃权机制参照 | 低 |
| HarmTrace: **Anchor-Calibrated** Decoupled Optimization | arXiv:2608.16622 | 有害meme检测中的细粒度目标识别 | **纯术语撞车**（anchor=检测锚点，完全不同域） | 低（考虑改名或加脚注） |
| 高精地图先验线（Scene Reconstruction as Mapping Priors 2605.22997；Compressed Map Priors 2601.00139；Neural Map Prior 2304.08481；DiffMap 2405.02008） | 2023-2026 | 用地图先验校正车载感知 | **邻域类比**：先验锚定感知误差在自动驾驶是成熟思想；但地图是环境先验而非"同一信号的GT"，且不做误差vs真值归因 | 中低（审稿人可能拿来类比，宜主动引用并划界） |

### A.5 方向10/11：图文一致性、意图-呈现漂移

| 工作 | 出处 | 核心机制 | 与ACDD差异 | 威胁 |
|------|------|---------|-----------|------|
| 经典UML模型间一致性检查（约30篇，2003-2015） | ECOOP/ICSE/TCS等 | 类图vs状态图vs顺序图的形式化一致性（pi-calculus/Datalog/模型检查） | **模型对模型**（XMI级），不处理渲染图像、不处理正文文本 | 低（相关工作一节引用3篇代表） |
| Composite consistency rules for UML | arXiv:2603.24726 (2026) | 组合一致性规则自动化 | 同上 | 低 |
| Detecting Architectural Drift in Safety-Critical Firmware | arXiv:2607.03135 | 架构设计vs运行时轨迹漂移 | "drift"词汇先例；对象是runtime | 低 |
| **Wait, wasn't that code here before? Detecting Outdated Software Documentation** | arXiv:2307.04291 | 检测代码文档过时 | "源（代码）动了、呈现（文档）没跟上"的**精神先例**；但code-doc、无born-digital锚点、无概率解码 | **中低（provenance drift最近的表亲）** |
| Detecting Outdated Code Element References | arXiv:2212.01479 | 检测文档中失效代码引用 | 同上 | 低 |
| Catching Transpilation Drift (quantum) | arXiv:2608.08248 | 源码vs转译产物漂移的CI/CD检测 | drift词汇先例（编译器域） | 低 |
| Marginalia/Bing全网检索 "provenance drift" / "intent presentation drift" / 嵌入源-渲染diff | 2026-08 | — | **零学术命中**（仅随机噪声结果） | 无 |

### A.6 两个具体思想的新颖性判定

#### （1）anchor masking protocol（屏蔽锚点当作无锚样本，评测校准质量）

**检索**：arXiv "anchor masking"/"mask ground truth"/评测协议组合；web检索；crowdsourcing金标准题（gold questions/honey pots）文献线。
**判定：未发现该协议的命名先例，可以"提出/形式化"名义声明，但机制上等价于hold-out评测，声明措辞必须诚实。**

- 最近邻1：**众包金标准题**（Snow et al. 2008起；AMT标准实践）——用已知答案的题目估计标注者可靠性。ACDD的锚点≈永不犯错的标注者。但众包文献里没有人把"**扣留金标题目→检验可靠性估计能否外推到非金标题**"提炼为一个命名的评测协议。
- 最近邻2：**交叉验证/留一法**——机器上同构，审稿人可能说"这就是hold-out"。
- 最近邻3：Refining Labeling Functions with Limited Labeled Data（arXiv:2505.23470）——用小规模标注子集精化弱监督LF，精神相近但目的不同（提升标签而非评测校准迁移）。

**非平凡性辩护理由（论文中必须写明）**：anchor masking测的不是"拟合优度"而是**校准的分布外迁移**——锚点文档（有嵌入Visio的图）与无锚文档（扫描图/位图）之间存在协变量偏移，masked-anchor子集能否代表non-anchored分布，本身是方法有效性的前提假设。该协议把这个假设变成可测量对象。**建议措辞**："we formalize an anchor-masking evaluation protocol that measures the transferability of channel error models from anchored to anchor-free documents"，避免"first/novel protocol"的强声明。

#### （2）provenance drift（嵌入源与渲染/依赖内容之间的diff作为真实不一致类型）

**检索**：arXiv（provenance+drift、source+render、stale+figure/outdated+documentation、figure+text mismatch）；DBLP；Marginalia/Bing全网。
**判定：作为命名的SRS不一致类型无先例，概念novelty较高；但存在两支精神先例，且面临实证频率风险。**

- 精神先例1：**code-doc过时检测线**（2307.04291、2212.01479）——"源演化了，下游呈现未同步"的结构完全同构，只是对象是代码↔文档。ACDD的差异：以嵌入图表源为"意图证据"，检测对象是文档内部的图文依赖。
- 精神先例2：GUI pixels-vs-structure（2607.04334）——渲染像素与结构化源的冗余双通道，但方向是智能体诊断。
- **风险**：①技术传播领域（technical communication, tcworld/SIGDOC）的"single sourcing/内容复用不一致"实践文献未经arXiv覆盖，**投稿前必查**；②Word中嵌入Visio的渲染EMF预览通常由嵌入源即时生成，"源-渲染"间漂移可能罕见，**provenance drift的真正形态是"嵌入源已改、依赖它的正文/表格没改"**（即源vs正文，非源vs渲染）——论文定义时必须精确到这一点，否则会被工程师用"渲染由源生成、不会漂移"一句话反驳。
- **建议措辞**：把provenance drift定义为"born-digital意图源与其依赖陈述（dependent prose/table）之间的演化不同步"，并在文中报告该类型在16份GJB文档中的实证频率（若频率过低则降级为case study而非可评测类别）。

### A.7 撞车检查小结

**没有任何工作占据ACDD的组合**。威胁排序（从高到低）：
1. **弱监督/Dawid-Skene + PI-explains-noise的组合式质疑**（审稿人："= Dawid-Skene加一个完美标注者 + selective prediction"）
2. ChemScraper/NTT线对"born-digital源文件利用"的思想先例
3. TSRCDF/AraREQ对"ML需求冲突检测"赛道的定义权
4. GUI pixels-vs-structure、Selective-Prediction-from-Agreement对"双通道分歧"的词汇先例
5. 术语撞车（HarmTrace的"Anchor-Calibrated"）

---

## 任务B：LUPI理论挂靠是否成立

### B.1 Vapnik原始LUPI设定 vs ACDD场景逐条对照

经典LUPI（Vapnik & Vashist 2009, Neural Networks 21(10); 源流为Vapnik《Estimation of Dependences Based on Empirical Data》与SVM+）：

| LUPI要件 | 经典设定 | ACDD场景 | 是否符合 |
|---------|---------|---------|---------|
| 特征空间 | 训练样本 (x, x*, y)，x*为特权特征 | x=感知通道输出（像素级观测），x*=Visio XML源 | ✅ 类似 |
| x*可用性 | **逐样本**在训练时可用，测试时**一律不可得** | 锚点仅对**子集文档**可用；且对该子集，测试时其实也可得（源文件一直在.doc里） | ⚠️ **部分符合**：是"部分特权"（partially privileged）而非经典LUPI |
| x*的角色 | 与y相关的额外特征，用于收缩假设空间（SVM+的松弛控制） | 锚点主要用作（a）通道误差的**标签源**，（b）蒸馏教师信号 | ⚠️ 偏离：经典LUPI的x*是特征不是标签 |
| 目标 | 训练一个只依赖x的预测器 | 训练（a）误差模型 + （b）分歧解码器，部署到无锚文档 | ✅ 形态一致（train-with/test-without） |
| 理论产物 | SVM+泛化界 | 无对应 | ❌ ACDD给不出LUPI式泛化界 |

**判定：严格LUPI不成立。** 两处硬伤：
1. **可用性结构不符**：ACDD是"子集样本带特权信息、其余不带"（部分特权），而非经典"训练全体带、测试全体不带"。这更接近混合了标注子集监督的设定（arXiv检索"partially privileged"在ML意义下零命中——这本身是个可声明的小缺口，但也意味着没有现成理论可用）。
2. **角色不符**：锚点被用来**标注**（产生通道误差的训练标签），而经典LUPI的特权信息是**特征**。若审稿人说"你这就是在一个有金标的子集上做监督校准"，仅靠LUPI无法反驳。

### B.2 更合适/必须并列的理论框架

| 框架 | 与ACDD的对应 | 作用 | 代表文献 |
|------|------------|------|---------|
| **广义蒸馏（Generalized Distillation）** | 锚点=看到x*的教师（看到源文件），感知通道/解码器=只见x的学生；蒸馏β插值 | **LUPI的正确挂靠姿势**：López-Paz et al. ICLR 2016证明LUPI与蒸馏统一，ACDD走蒸馏分支即严格落入其框架 | arXiv:1511.03643 |
| **测量误差修正（measurement error / regression calibration）** | 锚点子集=金标验证样本；通道=带误差测量；估计误差参数后修正下游推断 | 锚点校准步骤的最精确统计框架；且有2024-2026活跃现代应用 | Carroll et al.《Measurement Error in Nonlinear Models》；arXiv:2607.25868 |
| **Dawid-Skene / truth discovery** | 通道=标注者，锚点=金标题；逐条后验P(提取误差vs真实不一致)≈DS后验 | 后验解码步骤的机制先例；**也是最大威胁来源** | Dawid & Skene 1979；truth discovery综述 |
| **程序化弱监督（PWS/Snorkel）** | 通道=标注函数；锚点=小标注集估计LF精度 | 与ACDD机制最接近的现成体系，必须显式对比 | Ratner et al. 2016/2017；Fu et al. 2020；arXiv:2505.23470、2508.03896 |
| **带标注子集的噪声标签学习** | 锚点=clean subset估计噪声转移 | PI×label noise线（2202.09244/2303.01806/Pi-DUAL）已占"特权信息区分噪声"的话语 | 见A.4 |
| **选择性预测/弃权** | 后验不确定→弃权（Chow规则） | 弃权机制的现成理论，不需要重新发明 | Chow 1970；Geifman & El-Yaniv NeurIPS 2017 |
| **协变量偏移下的conformal prediction** | 锚点文档→无锚文档的分布迁移；弃权保证需在偏移下成立 | anchor masking协议的理论背书 | 需选定具体文献（投稿前补） |

### B.3 推荐的理论叙事（论文写法）

**不要单挂LUPI**。推荐三层叙事：

1. **顶层（范式）**：LUPI/广义蒸馏——"渲染图像由隐藏源文件生成；锚点文档让我们在训练期观测生成过程本身，推理期只观测渲染结果"，引Vapnik & Vashist 2009 + López-Paz 2016，并明确声明ACDD是其"部分特权"实例（诚实声明可用性结构）。
2. **中层（机制）**：测量误差修正 + DS式后验——锚点子集估计各通道**结构化**误差模型（按元素类型/空间区域/内容条件化，非标量精度），这是对经典DS（混淆矩阵）与经典回归校准（标量）的具体化推广。
3. **底层（保证）**：selective prediction + 协变量偏移——弃权阈值与覆盖保证，anchor masking协议测量校准迁移。

这样既保留"LUPI挂靠"的叙事吸引力，又堵住"这只是子集监督"的审稿人攻击。**"PI×文档AI"的空缺仍然可以声明**（检索零命中），但要限定为"首次将特权信息范式应用于文档感知通道校准"，而不是"首次将LUPI用于噪声区分"（后者被2202.09244线占据）。

---

## 任务C：贡献声明句式模板（从2024-2026方法论文提炼）

以下5个模式均以本次调研核实的论文为实例。

### 模式1：限定范围的"首个"（Scoped Firstness）
> **"We present [X], the first [approach/framework] that [capability] for [task], where [key challenge] has prevented prior work."**
- 实例：ChartArena (arXiv:2606.01348) "…benchmarking chart parsing across languages, scenarios, and formats"；SADU (arXiv:2604.04009) "Benchmarking and Evaluating VLMs for Software Architecture Diagram Understanding"。
- ACDD实例："We present ACDD, the first framework that decomposes cross-channel disagreement in requirement documents into *extraction error* versus *genuine content inconsistency*, using born-digital anchors available only at calibration time."
- **要点**：first后面的从句必须精确到能力+场景，禁止单独说"first to use anchors"。

### 模式2：量化缺陷→修复（Quantified Limitation → Fix）
> **"Recent work shows that [method class] fails on [regime] (quantified evidence). We address this by [mechanism], which turns [liability] into [asset]."**
- 实例：FlowExtract (arXiv:2604.06770)（VLM边恢复系统性失败→检测式管线）；Prior Bias (arXiv:2607.02853)（VLM读UML=读先验，反转箭头准确率降33.48%）。
- ACDD实例："VLM/OCR channels misread 20–40% of diagram elements (SADU, Prior Bias), so raw disagreement between channels and text conflates perception noise with genuine defects; ACDD uses born-digital anchors to calibrate per-channel error models and decode disagreement into a posterior over its two causes."

### 模式3：问题形式化（Formalization）
> **"We formalize [vague phenomenon] as [precise problem], and cast [existing ad-hoc practice] as [special case / inference in this formalism]."**
- 实例：TGCM (arXiv:2606.18651) "We formulate this setting as Unknown-K Interleaved Sequence Demixing (UKISD)"；Selective Prediction from Agreement (arXiv:2605.02611) 把选择性预测形式化为版本空间一致性。
- ACDD实例："We formalize requirement-document consistency checking as anchor-calibrated disagreement decoding: given channels with estimated error models, the posterior P(content error | disagreement) is computed per item, with abstention when it falls below threshold."
- **要点**：形式化声明必须让现有方法成为特例（如"无锚点时退化为纯投票"），这是抗"你只是DS"质疑的关键。

### 模式4：新旧嫁接（Established × Emerging Hybrid）
> **"We combine [established technique A] with [emergent technique B], showing that A compensates for B's [known weakness] and vice versa."**
- 实例：RE 2025 Fantechi et al.（规则聚类帮助LLM聚焦）；TSRCDF（迁移学习×双编码器）；QUARE（多智能体辩证×需求质量）。
- ACDD实例："We combine classical measurement-error calibration with LLM-based perception channels: anchors supply the validation data that classical calibration requires and that LLM pipelines lack."

### 模式5：实证规律揭示（Empirical Law / Diagnosis）
> **"Through systematic analysis of [N real artifacts], we provide the first empirical characterization of [phenomenon], finding that [quantified, counterintuitive result]."**
- 实例：Do GUI Agents Believe Their Eyes? (arXiv:2607.04334)；When does PI Explain Away Label Noise? (arXiv:2303.01806)；S3CDA（GPT-4o领域需求F1暴跌0.936→0.462）。
- ACDD实例："Across 16 real GJB SRS documents and [N] anchored diagrams, we characterize the empirical distribution of provenance drift and channel disagreement, finding that [X%] of raw disagreements are attributable to extraction error—without calibration, [Y%] of reported 'inconsistencies' are false alarms."

**组合建议**：ACDD论文的Intro贡献列表宜用 模式2(动机) + 模式3(方法) + 模式1(框架声明) + 模式5(实证) 的顺序；模式4用于related work的定位句。

---

## 最终结论

### 1. ACDD真正novel的部分（按可辩护强度排序）

1. **分歧的因果归因解码**（方法核心）：把"通道vs文本的分歧"解码为 P(提取误差) vs P(文档真实不一致) 的后验——该二分法及其后验处理在全部12个方向检索中零命中。**这是论文的第一贡献句。**
2. **嵌入式Visio XML作为born-digital锚点用于误差校准**（资源+机制）：Visio XML解析在arXiv零命中；born-digital源当GT有先例（ChemScraper），但**用于多通道误差模型校准**无先例。声明须限定为"校准用途"。
3. **provenance drift作为SRS不一致类型**（概念）：无命名先例；定义必须精确为"嵌入意图源 vs 依赖陈述"，且需要实证频率支撑，否则降级为case study。
4. **anchor masking评测协议**（协议）：机制上是holdout的变体，novelty弱；价值在于把"校准能否从锚点分布迁移到无锚分布"这一隐含假设变为可测对象。以"形式化"而非"首创"措辞声明。
5. 弃权机制——**不是novelty**（Chow/Geifman-El-Yaniv/selective prediction现成），只能作为工程性质贡献，切勿写进novelty列表。

### 2. 最脆弱的撞车点

**"ACDD = Dawid-Skene/truth discovery（一个完美标注者）+ PI-explains-away-label-noise（2202.09244/Pi-DUAL线）+ selective prediction"**。这三件单品都有成熟理论与2024-2026活跃文献，审稿人可以在一段话内完成拼装。**预防措施（写进论文的显式对比表）**：
- vs DS/PWS：通道误差是**结构化的**（按元素类型/几何区域/内容条件化，可从锚点免费监督），不是标量混淆矩阵；目标输出是**因果归因**（误差vs真值）而非标签聚合；锚点只在校准期可得，且存在anchored→non-anchored协变量偏移（PWS假设LF在无标注全域均匀适用，ACDD必须显式检验该假设——正是anchor masking协议的意义）。
- vs PI-noise线：他们的PI是**特征**（标注者ID等），目标是**标签去噪**；ACDD的锚点是**同一信号的隐藏生成源**，目标是**感知误差归因**，且部分特权结构不同。
- vs GUI pixels-vs-structure：他们诊断agent依赖哪条通道；ACDD校准并用双通道输出做一致性判定。

### 3. 投稿前必须重查的关键词（按紧迫度）

| # | 关键词/动作 | 防的是什么 |
|---|------------|-----------|
| 1 | "programmatic weak supervision" + vision/multimodal/document（2024-2026）| 弱监督线在多模态的最新扩展 |
| 2 | "privileged information" + OCR / document parsing / perception calibration | PI×文档AI的零命中结论需在投稿当周复核 |
| 3 | **AraREQ全文**（LREC 2026）+ RE 2026 / REFSQ 2026 程序（"inconsistency"/"conflict"/"multimodal"） | 需求矛盾检测赛道的最新占位（DBLP索引滞后约半年） |
| 4 | "single sourcing" / "content reuse inconsistency"（SIGDOC、tcworld、technical communication期刊） | provenance drift在技术传播实践文献的可能先例（arXiv盲区） |
| 5 | digital forensics: "embedded object" / "OLE" / "embedded Visio" | 取证领域可能处理过嵌入对象一致性 |
| 6 | "measurement error correction" + annotation/NLP + "gold standard validation set" | 生物统计框架在NLP的最新迁移 |
| 7 | "partially privileged information" / "privileged features on a subset" | 部分特权设定是否已有理论（本检索零命中，需复核） |
| 8 | "conformal prediction" + "covariate shift" + abstention | 弃权保证的理论引用选定 |
| 9 | "anchor" + "calibration" + perception（自动驾驶高精地图先验线的新作） | 邻域类比被反用的风险 |
| 10 | crowdsourcing "gold questions" / "honey pots" + reliability transfer | anchor masking协议的最近邻复核 |

### 4. 一句话总结

ACDD的核心新颖性不在任何单件技术，而在**"用文档自带的生成源免费校准感知误差，从而把分歧从噪声升级为证据"**这一因果反转——检索证实该组合及其两个具体协议（anchor masking、provenance drift）均无先例，但论文必须以"形式化+划界对比"的防守姿态写作，因为Dawid-Skene、PI-noise、born-digital三条先例线各自距离ACDD都只有一步之遥。
