# 无人工标注的数据质量验证与评测——文献调研报告

> 面向：GJB SRS一致性检测数据集（223条Gold Standard，无人工标注）
> 调研范围：LLM-as-judge / 无标注数据集验证 / 标注一致性度量 / 基准数据集构建 / 评测统计显著性
> 日期：2026-08-10
> 性质：只做调研分析，产出建议，不涉及代码

---

## 0. 结论速览（回答五个关键问题）

| # | 问题 | 结论 |
|---|------|------|
| 1 | 双模型交叉标注替代人工是否被认可？ | **范式被认可（LLM-as-annotator是活跃研究领域），但"无任何人工锚点"的纯机器标注基准在顶会层面不被视为最终证据。** ACL 2025 专门提出 *Alternative Annotator Test*，要求用**少量人工标注子集**做统计检验来"证明"LLM可替代人类——这已成为该方向的标准答案 |
| 2 | 92%一致率是否充分？ | **不充分。一致率是信度（reliability）不是效度（validity）。** 需补：(a) Cohen's kappa/Krippendorff α（扣除随机一致）；(b) 逐类一致率；(c) 第三方模型仲裁分歧；(d) 同模型多次采样自一致性（SelfCheckGPT思路）；(e) 明确"一致≠正确"的论证 |
| 3 | 无人工标注如何达到论文可接受可信度？ | **三条路径组合**：(1) 采集最小人工子集（约50-100条，哪怕1个研究者自标）做alt-test锚定；(2) 强化已有的"确定性验证锚点"（双源解析31/31、OCR 10/10）并扩展；(3) 全流程透明化（发布prompt、标注准则、证据链、Datasheet），论文措辞用"machine-annotated silver standard"并诚实声明局限 |
| 4 | 评测协议（分层/真实单独/hold-out）缺什么？ | **缺的是"证据强度"而非"结构"**：统计检验尚未落地、无人类判断上界参照、无跨文档泛化（leave-one-doc-out）、无judge模型自身偏差分析（self-preference）、无prompt/温度敏感性分析、无与已有RE工具（ARTA等）的对比 |
| 5 | 223条够吗？ | **作为评测集够（MT-Bench仅80题），作为统计检验样本勉强。** McNemar估算：223条约能可靠检测≥10个百分点的F1差异（95%置信、80%功效），检测5%差异约需780+条。必须报告bootstrap 95%CI（Deutsch et al. TACL 2021证明小样本CI很宽），并按不一致类型保证每类≥10-20条 |

---

## 1. 五个方向的代表论文

### 1.1 方向一：LLM-as-judge 评测

#### (1) G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment
- **作者/年份/会议**：Yang Liu et al.，2023，EMNLP 2023（arXiv:2303.16634）
- **方法**：用LLM（GPT-4）做reference-free评测器：把评估准则写成prompt，让模型按CoT（chain-of-thought）+ form-filling范式生成分维度打分。不用人工参考答案。
- **结论**：GPT-4做judge在摘要生成任务上与人类Spearman相关0.514，大幅超过此前所有自动指标。**但作者明确警告：LLM评测器对LLM生成文本有系统性偏好（self-enhancement bias）。**
- **对本项目**：支持"LLM作为质量评估器"的可行性，同时是"LLM判断有偏差"的最早警示之一。

#### (2) Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena
- **作者/年份/会议**：Lianmin Zheng et al.，2023，NeurIPS 2023 Datasets & Benchmarks Track（arXiv:2306.05685）
- **方法**：系统分析LLM-as-judge的四大缺陷——**位置偏差（position bias）、冗长偏差（verbosity bias）、自我增强偏差（self-enhancement bias）、推理能力有限**；提出缓解方案（交换顺序、引用答案等）；构造MT-Bench（80道多轮问题）+ Chatbot Arena（众包对战平台）验证。
- **结论**：强LLM judge与人类偏好达到80%+一致（≈人与人之间的一致水平），"LLM-as-judge是可扩展、可解释的近似人类偏好方法"。**关键前提：judge与evaluatee不能是同一个模型，且偏差已被检测和缓解。**
- **对本项目**：直接支持"双模型交叉标注"的正当性（kimi+claude是异族模型，规避了self-enhancement）。同时提醒：80%≈人类间一致，92%的双模型一致已超过人类间基准，但不能据此宣称高于人类质量。

#### (3) A Survey on LLM-as-a-Judge
- **作者/年份/会议**：Jiawei Gu et al.，2024-2025（arXiv:2411.15594，2025年3月v5）
- **方法**：综述LLM-as-judge的可靠性建设：一致性提升、偏差缓解、多场景适配，并提出评测LLM-judge自身可靠性的基准。
- **结论**：可靠LLM-judge需要系统设计（judge选择、prompt模板、偏差缓解、meta-evaluation），当前无统一标准。
- **对本项目**：提供方法论框架：应当**同时评估"judge自身"的可靠性**（如judge对同一输入多次判定的一致性、对prompt扰动的稳定性）。

#### 补充：SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative LLMs
- **作者/年份/会议**：Potsawee Manakul et al.，2023，EMNLP 2023（arXiv:2303.08896）
- **方法**：**零资源幻觉检测**：同一模型对同一问题采样多条回答，用"采样间一致性"判断幻觉——事实性内容采样稳定一致，幻觉内容采样发散矛盾。
- **结论**：无外部知识库、无人工标注，仅靠采样一致性即可显著优于grey-box方法（AUC-PR显著提升）。
- **对本项目**：这是"无人工标注验证"的**最直接先例**：我们的"双模型一致92%"本质上就是SelfCheckGPT思想的跨模型版本；建议**补上同模型多次采样自一致性**作为第三层证据。

#### 补充：LLM Evaluators Recognize and Favor Their Own Generations
- **作者/年份/会议**：Arjun Panickssery, Samuel Bowman, Shi Feng，2024（arXiv:2404.13076）
- **方法**：研究self-preference偏差：LLM judge对**自己**生成的输出打分偏高（对人类同等质量的输出），且模型能"认出"自己的输出（self-recognition），两者线性相关。
- **结论**：LLM评估自身输出会系统性偏差；**评估时judge与evaluatee必须解耦**。
- **对本项目**：为"标注用kimi+claude两个不同族模型"提供了坚实理论依据；也警告：若评测时检测器与标注器是同一模型，可能虚高。

### 1.2 方向二：无人工标注的数据集验证

#### (1) Data Programming: Creating Large Training Sets, Quickly
- **作者/年份/会议**：Alexander Ratner et al.，2016，NeurIPS 2016（arXiv:1605.07723）
- **方法**：用**标签函数（labeling functions）**表达弱监督策略/领域启发式，多个噪声且可能冲突的标签函数覆盖数据；将标注过程显式建模为**生成式模型（label model）**，在**无ground truth**的情况下对噪声标签去噪（denoise）并估计各标签函数准确率。
- **结论**：理论证明可恢复生成模型参数；TAC-KBP 2014上胜过当时state-of-the-art；非专家也能快速建模型。
- **对本项目**：**核心方法论支撑**：Snorkel的label model说明"无人工标注时，可以用多个弱信号的结构化组合估计标注质量"——我们的"双源解析+双模型+OCR"正是多信号交叉，只是尚未形式化（未估计每个信号各自的准确率）。

#### (2) Snorkel: Rapid Training Data Creation with Weak Supervision
- **作者/年份/会议**：Alexander Ratner et al.，2017，PVLDB 11(3)（arXiv:1711.10160）
- **方法**：Data Programming的系统实现：用户写标签函数（可含未知准确率与相关性），系统自动去噪，无需手标任何训练数据。与FDA/VA合作验证。
- **结论**：专家用Snorkel建模快2.8倍、性能平均提升45.5%；与大规模人工精心标注集仅差3.60%。
- **对本项目**：证明"无人工标注"在工业界被认可，且给出了可借鉴的质量估计机制（**用label model估计每个标注源的精度**，即"信号可信度"，而非只报告一致率）。

#### (3) Constitutional AI: Harmlessness from AI Feedback
- **作者/年份/会议**：Yuntao Bai et al.，2022，Anthropic（arXiv:2212.08073）
- **方法**：RLAIF（RL from AI Feedback）：用AI模型互相评价（preference model）替代人类反馈训练无害AI，人类只提供"宪法"（规则列表）而不提供危害标注。
- **结论**：大幅减少人工标签仍能训练高质量无害助手。
- **对本项目**：说明"AI监督AI"在大厂主流实践中被接受；但注意——**宪法AI的前提是规则（constitution）由人类撰写**，类比到我们：GJB 438C规则库（120条，可追溯OCR行号）正是我们的"宪法"，应强调这一点。

#### (4) Large Language Models for Data Annotation and Synthesis: A Survey
- **作者/年份/会议**：Zhen Tan et al.，2024，EMNLP 2024（arXiv:2402.13446）
- **方法**：系统综述LLM标注三大方面：标注生成（LLM-Based Annotation Generation）、**标注质量评估（LLM-Generated Annotations Assessment）**、标注利用。含数据类型的完整分类、学习策略综述、挑战与局限。
- **结论**：LLM标注已广泛用于NLP/医学/社科；**核心开放挑战正是"如何评估LLM标注质量本身"（gold-free quality assessment）**。
- **对本项目**：这是引用时最核心的综述性文献，直接定义了我们所处的研究缺口（无人工标注时的质量评估），也说明我们的场景是公认难题。

#### (5) The Alternative Annotator Test for LLM-as-a-Judge: How to Statistically Justify Replacing Human Annotators with LLMs ★最关键
- **作者/年份/会议**：Nitay Calderon, Roi Reichart, Rotem Dror，2025，**ACL 2025 Main**（anthology: 2025.acl-long）
- **方法**：提出 **alt-test** 统计流程：只需**一小部分人工标注样本**（modest subset），用统计检验（配对检验，基于两annotator在同一子集上的标注差异）判定"LLM标注能否替代人类标注"。同时提出可解释的替代性度量。在10个数据集（语言+视觉语言）、6个LLM、4种prompt上验证。
- **结论**：闭源LLM（如GPT-4o）**有时**可以替代人类，开源LLM通常不行；prompt方法影响大。**论文核心观点：不能用"LLM之间一致"替代"LLM与人类一致"，必须用统计检验锚定。**
- **对本项目**：**直接决定我们方案的可信度等级**——我们目前的"双模型92%一致"在alt-test框架下属于"未完成"状态，缺一个最小人工锚定子集。好消息：alt-test只需"modest subset"（论文中约几十到百条量级），成本远低于全量人工标注。

#### 补充：Are LLMs Better than Reported? Detecting Label Errors and Mitigating Their Effect on Model Performance
- **作者/年份/会议**：Omer Nahum, Nitay Calderon et al.，2025，EMNLP 2025
- **方法**：用**LLM集成（ensemble of LLMs）作为judge**检测现有基准数据集（TRUE benchmark、SummEval）中的标签错误；对比专家、众包、LLM三类标注的一致性与质量。
- **结论**：发现大量标签错误，修正后模型报告性能显著上升——**很多"LLM犯的错"实为数据集标签错误**。
- **对本项目**：这是"LLM集成检测标注错误"的直接先例，方法论与我们的双模型交叉完全同构；可作为引用支撑。

#### 补充：On the Limitations of Reference-Free Evaluations of Generated Text
- **作者/年份/会议**：Daniel Deutsch, Rotem Dror, Dan Roth，2022，EMNLP 2022
- **方法**：理论上证明**reference-free指标（一个生成模型评估另一个生成模型）存在固有偏差**：(1) 可被测试时优化；(2) 偏向与自己相似的模型；(3) 可能歧视更高质量输出（包括人类写的）。
- **结论**：reference-free评估应仅作诊断工具，不宜作为"任务完成度"度量。
- **对本项目**：**最重要的反面警告**：我们的LLM-based标注也是"模型评估模型"，必须承认这一根本局限，并用确定性锚点（双源、OCR、规则）来对冲。

### 1.3 方向三：标注一致性度量

#### (1) Inter-Coder Agreement for Computational Linguistics
- **作者/年份/会议**：Ron Artstein, Massimo Poesio，2008，Computational Linguistics 34(4)
- **方法**：NLP标注一致性度量的权威综述：Cohen's kappa（2个标注者）、Fleiss' kappa（多个）、**Krippendorff's alpha（任意标注者数、可处理缺失值、任意度量级别）**；讨论chance correction、类别不平衡对kappa的影响；给出各种度量在NLP中的适用性。
- **结论**：报告标注质量必须用**chance-corrected**指标（kappa/alpha），原始一致率（raw agreement）会被类别分布误导；NLP任务kappa<0.67通常视为不可靠。
- **对本项目**：**直接缺口**：我们报告"92%一致"是raw agreement。223条中若负例占比高（如正53:负118），即使随机标注也能有较高raw agreement；必须补报Cohen's kappa/Krippendorff α，并按正/负类分别报告。

#### (2) Computing Krippendorff's Alpha-Reliability
- **作者/年份/会议**：Andrew F. Hayes, Klaus Krippendorff，2007，Communication Methods and Measures 1(1)
- **方法**：给出Krippendorff's alpha的计算公式与流程，支持任意标注者数、缺失数据、名义/序数/区间/比率尺度。
- **结论**：alpha是可广泛使用的一致性指标；惯例阈值：**α≥0.8 可接受（某些领域要求α≥0.9才可靠）**。
- **对本项目**：两个模型的标注可视为"两个标注者"，直接可用Krippendorff α（n=2退化为类kappa）；0.9阈值是论文可引用的标准。

#### (3) FEVER（作为IAA应用案例，详见1.4）
- FEVER报告其人工标注 **Fleiss κ=0.6841**——即185k条claims的人工一致性也只到0.68；**我们双模型一致92%（raw）换算成kappa很可能在0.7-0.85区间，与人工标注者水平相当**。这既是参照也是警告：人工标注本身也不完美，benchmark可接受性不要求100%一致。

### 1.4 方向四：基准数据集构建

#### (1) FEVER: a large-scale dataset for Fact Extraction and VERification
- **作者/年份/会议**：James Thorne et al.，2018，NAACL 2018（arXiv:1803.05355）
- **方法**：用Wikipedia句子**自动生成185,445条claims**（alteration），再由**人工标注者**（无证据来源知识）标注Supported/Refuted/NotEnoughInfo，并记录**证据句子**（evidence spans）。报告的Fleiss κ=0.6841。公布数据+评测脚本+排行榜。
- **结论**：大规模基准的核心三要素——**明确的任务定义、可验证的标注流程（含IAA报告）、证据链输出**；"自动生成+人工验证"是构建大基准的标准管线。
- **对本项目**：三点借鉴：(1) 我们"注入样本（自动生成）+双源双模型验证"与FEVER"自动生成+人工验证"同构，只是验证者从人换成模型；(2) **FEVER要求每条标注附证据（evidence）**——我们已输出证据链（02文档），应在数据集格式中强制保留；(3) IAA报告是benchmark论文的标准章节。

#### (2) ContractNLI: A Dataset for Document-level NLI for Contracts
- **作者/年份/会议**：Yuta Koreeda, Christopher Manning，2021，Findings of EMNLP 2021（arXiv:2110.01799）
- **方法**：法律合同**文档级NLI**：给定合同+假设（hypothesis），判Entailed/Contradicted/NotMentioned并定位**证据span**。标注协议：**专家（律师）+ 外行双标注 + 仲裁**；607份合同。
- **结论**：法律文档NLI可行但难（现有模型大幅失败）；例外/否定（如"除非条款"）是难点。
- **对本项目**：与SRS最相似的领域基准（长文档、法律/规范语言、需要证据定位）。**其"专家+外行双标注+仲裁"的协议设计，可类比我们的"kimi+claude+争议排除"**——差别仅在"专家"缺位。

#### (3) GLUE: A Multi-Task Benchmark and Analysis Platform for NLU
- **作者/年份/会议**：Alex Wang et al.，2019，ICLR 2019（arXiv:1804.07461）
- **方法**：多任务NLU基准+**人工设计的诊断集（diagnostic test suite）**，用于细粒度语言能力分析；提供公开leaderboard。
- **结论**：基准应包含"诊断维度"（按能力分层）而非单一总分——**直接呼应我们的easy/medium/hard分层设计**。
- **对本项目**：GLUE证明"按能力维度分层报告"是基准设计的最佳实践，我们已采用；建议补"诊断式错误分析"（每类不一致类型的检出率矩阵）。

#### (4) Datasheets for Datasets
- **作者/年份/会议**：Timnit Gebru et al.，2021，CACM（arXiv:1803.09010）
- **方法**：倡导每个数据集附**datasheet**：动机、构成、收集过程、标注过程、推荐用途、伦理与局限等。
- **结论**：数据集文档化是社区义务，显著提升透明度与负责任使用。
- **对本项目**：**发布配套Datasheet**（含无人工标注声明、双源/双模型/OCR验证细节、分歧处理、局限）是顶会审稿人可接受的"透明化"策略，成本极低。

### 1.5 方向五：统计显著性

#### (1) The Hitchhiker's Guide to Testing Statistical Significance in NLP
- **作者/年份/会议**：Rotem Dror, Gili Baumer, Segev Shlomov, Roi Reichart，2018，ACL 2018
- **方法**：NLP显著性检验的权威指南：建立基本概念；分析NLP任务/实验设计/评测指标对检验选择的影响；给出**检验选择协议**；调查ACL/TACL 2017论文发现显著性检验常被忽略或误用。
- **结论**：给出实用决策树：配对数据用配对检验（McNemar/配对bootstrap/permutation）；多数据集用Replicability Analysis；报告效应量与置信区间。
- **对本项目**：**评测协议v2中"bootstrap 95%CI + McNemar"的权威依据**，必须落地并写明检验选择理由。

#### (2) A Statistical Analysis of Summarization Evaluation Metrics Using Resampling Methods
- **作者/年份/会议**：Daniel Deutsch, Rotem Dror, Dan Roth，2021，TACL 9
- **方法**：用**bootstrap与permutation**计算评测指标相关性的置信区间并做假设检验；通过仿真验证方法适用性。
- **结论**：**置信区间相当宽**——小样本下指标差异常不显著；很多指标对ROUGE无显著提升。**"无显著差异"是常态，应诚实报告。**
- **对本项目**：223条样本上F1的bootstrap CI会相当宽（±5-8个百分点），报告时应预期并接受；这比宣称精确的数字更可信。

#### (3) Approximate Statistical Tests for Comparing Supervised Classification Learning Algorithms
- **作者/年份/会议**：Thomas Dietterich，1998，Neural Computation 10(7)
- **方法**：比较5种检验在分类器对比中的表现（10折CV配对t、5×2 CV、McNemar等），分析type I error。
- **结论**：**McNemar检验**（基于配对样本的不一致计数）在小样本上统计功效好且type I error可控，适合"两方法在同一测试集上比较"。
- **对本项目**：McNemar实现简单（只需要b、c两个不一致计数），223条完全可做；与配对bootstrap互补。

#### 经典补充（无arXiv，直接引用）
- Berg-Kirkpatrick, Burkett, Klein (2012). "An Empirical Investigation of Statistical Significance in NLP." EMNLP 2012 —— **randomization/permutation检验**在NLP的奠基实证。
- Cohen (1960) kappa；Fleiss (1971) kappa——一致性度量原始文献。

---

## 2. "无人工标注"方案的学术定位与可信度评估

### 2.1 定位：这是一个被研究的范式，而非无先例的冒险

学术界当前状态可归纳为三层：

1. **范式层（被认可）**：LLM做标注/评测（LLM-as-annotator/judge）已是主流研究领域（Tan et al. 2024综述；Zheng et al. 2023）。多模型交叉（ensemble）检测标签错误有直接先例（Nahum et al. 2025）。
2. **证据层（被质疑）**：多篇工作证明LLM评估存在系统性偏差——self-enhancement/self-preference（Liu et al. 2023；Panickssery et al. 2024）、reference-free评估固有偏差（Deutsch et al. 2022）。**审稿人默认"LLM一致≠正确"**。
3. **标准层（正在形成）**：Calderon et al. 2025（ACL 2025）提出alt-test——**用少量人工标注子集+统计检验证明LLM可替代人类**。这正在成为该领域的默认要求。

**结论：我们的方案（双源解析+双模型交叉+OCR验证）属于范式层中质量很高的工程实践，但停留在"证据层"的自证（模型内部一致），未触及"标准层"（与人类锚定）。**

### 2.2 我们方案与先例的对应关系

| 我们的组件 | 学术界对应 | 对应强度 |
|-----------|-----------|---------|
| 双源独立解析（mineru+textutil）验证31/31 | 确定性/结构性验证（类似程序测试oracle） | ★★★★ 强：非LLM证据，不受judge偏差影响 |
| kimi+claude双模型交叉标注（92%） | LLM ensemble标注（Nahum et al. 2025） | ★★★ 中：有先例，但"一致"不等"正确" |
| OCR交叉验证VLM（10/10） | 多模态交叉验证 | ★★★★ 强：独立信号 |
| 120条GJB规则库 | Constitutional AI的"宪法"（人类提供的规则） | ★★★★ 强：人类知识以规则形式注入 |
| 排除disputed、分层、hold-out | 基准构建最佳实践（FEVER/GLUE） | ★★★★ 强 |
| 无任何人类标注锚点 | **alt-test缺口**（Calderon et al. 2025） | ★ 弱：当前最大短板 |

### 2.3 92%一致率的正确解读

- 92%是 **raw agreement（原始一致率）**，不是chance-corrected。按文档数据（正例约53/118、负例约118/171，比例不均衡），**必须补报Cohen's kappa/Krippendorff α**。若负例占多，随机标注都可能达到较高raw agreement。
- 文档已暴露一个关键信号：**双模型一致率92% vs gold符合率84%**（注入子集89%一致/78%符合）——**一致率和真实标签符合率之间存在8-11个百分点的gap**，说明"两模型一致"包含"两模型一起错"的情况。这正是审稿人会抓的点，必须正面分析。
- 经验参照：FEVER人工标注Fleiss κ=0.6841、MT-Bench人类间一致约80%、GLUE任务人工基线约80-90%。我们的raw 92%换算kappa后大概率落在0.7-0.85，**处于"与人工标注者相当"的水平——这是好事，但要报告kappa才能让人信服**。

### 2.4 可信度缺口清单（按严重程度排序）

1. **无人类锚点**（最严重）：alt-test要求的最小人工子集缺失。缓解：采集50-100条人工标注（可研究者自标+盲审），用alt-test证明或量化LLM-人类差距。
2. **无kappa/alpha报告**：raw agreement不足以支撑"92%一致"声明。
3. **无自一致性报告**：同一模型温度采样多次判定是否稳定（SelfCheckGPT思路），可证明判定非偶然。
4. **无judge偏差分析**：未报告kimi/claude对正/负类的系统倾向（如claude判一致更多？kimi判不一致更多？），未做位置/顺序扰动测试。
5. **"一致≠正确"未量化**：92%一致+84%符合的gap未正面分析。
6. **无跨文档评估**：16份文档之间检测难度差异未知（leave-one-doc-out）。
7. **统计检验未落地**：文档自述"bootstrap/McNemar待补"。

---

## 3. 具体改进建议

### 3.1 数据质量层面（建议按优先级实施）

**P0（论文必需）：**
1. **补报chance-corrected一致性**：对双模型标注计算Cohen's kappa + Krippendorff α（n=2标注者），按正/负类、按难度分层、按来源（真实/注入）分别报告。阈值参考α≥0.8可接受（Hayes & Krippendorff 2007）。
2. **补同模型自一致性**：从223条中抽样30-50条，同一模型（kimi）温度>0采样3-5次，报告自一致性。与跨模型一致率（92%）并列展示："自一致性X% / 跨模型一致性92%"——若两者接近，说明判定稳定。
3. **分歧样本第三方仲裁**：环境中有GLM-5 API（glm系列被判"过宽"已排除，但可作为**仲裁者**而非标注者使用），对disputed 10条+随机20条一致样本做第三方判定，报告第三方与各方的符合率。

**P1（强烈建议）：**
4. **采集最小人工锚定子集**：50-100条（覆盖各层/各类型），由1-2人按已发布的标注准则独立标注，计算人类-LLM一致率与kappa。若资源允许，对全量做"研究者自标+LLM辅助复核"（研究者可审计，成本可控）。
5. **正面分析"一致≠正确"**：对92%一致/84%符合的gap做归因（错字型、语义近似型分别如何），在论文中作为限制性分析章节。
6. **发布Datasheet**（Gebru et al. 2021）：动机、构成、收集、标注协议、分歧处理、局限、使用建议。

**P2（加分项）：**
7. 将"双源+双模型+OCR"三个信号形式化为**Snorkel式label model**：为每个信号估计精度与相关性（即使简化版），输出每个样本的"多信号置信度"。这比单一一致率强得多，且是独立方法论贡献。
8. 每条gold样本附带**证据链字段**（引用位置、双源截断、模型判定理由），保证可审计——FEVER要求evidence spans，这是benchmark格式惯例。

### 3.2 评测协议层面

**P0：**
1. **落地统计检验**：所有主指标（F1/检出率）附bootstrap 95%CI（1000-10000次，按样本重采样）；方法两两比较用McNemar（精确二项版本）；报告检验选择理由（遵循Dror et al. 2018决策树）。
2. **人类判断上界参照**：哪怕只对20-30条子集报告人类判断准确率，作为"上界"参照——审稿人非常看重这一点。
3. **跨文档泛化**：leave-one-doc-out（16折），报告每份文档的检出率方差——识别"易文档/难文档"。

**P1：**
4. **judge自身偏差审计**：对kimi/claude检测器做self-preference检验（若检测器与标注器同模型则高风险）、位置/顺序扰动、prompt版本敏感性（Mizrahi et al. TACL 2024 "State of What Art?"——单一prompt评测不可靠）。
5. **完整指标矩阵**：不再只报检出率——报告precision/recall/F1/混淆矩阵，正例偏少（53 vs 118）时prec/rec分离很关键。
6. **与RE领域工具对比**：ARTA等需求质量检测工具作为baseline（若适用）。
7. **难度分层校准**：文档自述"hard仍100%检出，标注不够hard"——需引入描述级/逻辑级更强矛盾样本（描述级NLI 19/20已接近；逻辑层Z3尚待开发）。

---

## 4. 下一步该做什么（数据层面，按顺序）

| 步骤 | 动作 | 工作量 | 依据 |
|------|------|--------|------|
| 1 | 对现有223条补报Cohen's kappa / Krippendorff α + 分层一致率 | 小（半天，纯计算） | Artstein & Poesio 2008; Hayes & Krippendorff 2007 |
| 2 | 采样30-50条做同模型自一致性（kimi，温度采样3-5次） | 小（1天） | SelfCheckGPT; Wang et al. 2023 |
| 3 | 分歧10条+随机20条第三方（GLM-5）仲裁 | 小（半天） | Nahum et al. 2025（LLM集成仲裁先例） |
| 4 | **采集最小人工子集50-100条**（研究者自标，发布准则后盲标） | 中（2-3天） | **Calderon et al. 2025 alt-test（ACL 2025）** |
| 5 | 用alt-test流程做"LLM标注 vs 人类标注"统计检验 | 小（1天，等步骤4数据） | Calderon et al. 2025 |
| 6 | 正面分析"一致≠正确"gap（92% vs 84%）并归因 | 中（1-2天） | Deutsch et al. 2022（reference-free局限） |
| 7 | 编写Datasheet for Dataset | 中（1-2天） | Gebru et al. 2021 |
| 8 | 评测协议补：bootstrap CI + McNemar + leave-one-doc-out + 人类上界参照 | 中（2-3天） | Dror et al. 2018; Dietterich 1998; Deutsch et al. 2021 |

**优先级判断**：步骤1-3（一致性度量补齐）与步骤4-5（人工锚点）是论文可信度的**必要条件**，应在投稿前完成；步骤7-8决定论文"评测严谨性"评分。步骤4是唯一需要"人力"的步骤，且只需50-100条（占总量的20-40%），与全量人工标注有本质区别——这是无人工标注条件下成本最低、收益最高的可信度投资。

---

## 附录：论文速查表

| 方向 | 论文 | 会议/年份 | arXiv/ID |
|------|------|-----------|----------|
| LLM-as-judge | G-Eval | EMNLP 2023 | 2303.16634 |
| LLM-as-judge | Judging LLM-as-a-Judge (MT-Bench) | NeurIPS 2023 D&B | 2306.05685 |
| LLM-as-judge | A Survey on LLM-as-a-Judge | arXiv 2024 | 2411.15594 |
| LLM-as-judge | SelfCheckGPT | EMNLP 2023 | 2303.08896 |
| LLM-as-judge | LLM Evaluators Recognize and Favor Their Own Generations | arXiv 2024 | 2404.13076 |
| 无标注验证 | Data Programming | NeurIPS 2016 | 1605.07723 |
| 无标注验证 | Snorkel | PVLDB 2017 | 1711.10160 |
| 无标注验证 | Constitutional AI (RLAIF) | arXiv 2022 | 2212.08073 |
| 无标注验证 | LLM for Data Annotation & Synthesis Survey | EMNLP 2024 | 2402.13446 |
| 无标注验证 | **Alternative Annotator Test** | **ACL 2025** | aclanthology 2025.acl-long |
| 无标注验证 | Are LLMs Better than Reported? (label errors) | EMNLP 2025 | — |
| 无标注验证 | Limitations of Reference-Free Evaluations | EMNLP 2022 | — |
| 一致性度量 | Inter-Coder Agreement for CL | CL 34(4) 2008 | 期刊（无arXiv） |
| 一致性度量 | Computing Krippendorff's Alpha-Reliability | CMM 1(1) 2007 | 期刊（无arXiv） |
| 基准构建 | FEVER | NAACL 2018 | 1803.05355 |
| 基准构建 | ContractNLI | Findings-EMNLP 2021 | 2110.01799 |
| 基准构建 | GLUE | ICLR 2019 | 1804.07461 |
| 基准构建 | Datasheets for Datasets | CACM 2021 | 1803.09010 |
| 统计显著性 | Hitchhiker's Guide to Testing Significance in NLP | ACL 2018 | aclanthology P18（Dror et al.） |
| 统计显著性 | Resampling Methods for Eval Metrics | TACL 9, 2021 | aclanthology（Deutsch et al.） |
| 统计显著性 | Approximate Statistical Tests | Neural Computation 10(7) 1998 | 期刊（Dietterich） |
