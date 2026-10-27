# 级联验证架构创新点扩展调研（A–F六方向）

> 调研日期：2026-10-22
> 方法：arXiv API逐方向精确检索（标题/摘要/日期窗）+ 已知文献核对；会议信息以arXiv comment为准，未标注会议的以arXiv编号引用
> 服务对象：ACDD三层级联架构（L0 NER实体检测 → L1 符号/规则验证 → L2 NLI残差判定），已有创新点4项（残差NLI训练 / Logic-LM管线 / 文档内实体链接+NIL / 双模式退出）
> 时间范围：用户要求2023–2025核心论文；因检索时点为2026-10，另补充2026前沿预印本（标注[2026前沿]），用于佐证趋势与差异化定位
> 交叉引用：`nlp4re_llm4re_comprehensive_survey.md`（NLP4RE全景）、`cross_modal_consistency_survey.md`（跨模态）、`no_human_annotation_eval_survey.md`（无标注评测）、`pair_classifier_sota_2023_2025.md`（句对模型）

---

## A. 不确定性与校准

### A.1 论文清单

| # | 论文 | 出处 | 核心机制 | 与本架构关系 |
|---|------|------|----------|--------------|
| A1 | Language Models with Conformal Factuality Guarantees (Mohri & Hashimoto) | arXiv 2402.10978 (2024) | 将"输出正确性"等价为蕴含集上的UQ问题，conformal back-off逐步放宽输出换取80–90%正确性保证 | ★把CP引入事实性判定通道的原型 |
| A2 | Detecting hallucinations using semantic entropy (Farquhar et al.) | Nature 630 (2024)；基础版 Kuhn et al. ICLR 2023 (arXiv 2302.09664) | 多次采样→语义等价聚类→簇分布熵作为不确定性 | L2残差判定的不确定性来源之一 |
| A3 | Semantic Entropy Probes (Kossen et al.) | arXiv 2406.15927 (2024) | 直接从单次生成隐状态回归语义熵，开销≈0，OOD泛化好于准确率探针 | ★L2的廉价弃权信号（探针替代多次采样） |
| A4 | Just Ask for Calibration (Tian et al.) | EMNLP 2023 (arXiv 2305.14975) | RLHF模型的verbalized confidence比条件概率校准更好（ECE相对降50%） | 双模式退出的置信度来源依据 |
| A5 | Do LLMs Know What They Don't Know? (Yin et al.) | ACL 2023 Findings (arXiv 2305.18153) | SelfAware数据集；自我认知与人类差距显著 | 弃权通道必要性的论据 |
| A6 | Conformal-RAG (Feng et al.) | SIGIR 2025 (arXiv 2506.20978) | 子声明级CP过滤，group-conditional覆盖，同等可靠性下多保留60%高质量子声明 | 子声明粒度的CP过滤=我们的claim级 |
| A7 | Is Conformal Factuality for RAG-based LLMs Robust? | arXiv 2603.16817 [2026前沿] | 系统性批判：高目标下输出空洞化；**轻量NLI蕴含校验器≈LLM置信度打分器，FLOPs少100×**；分布漂移破坏校准 | ★★为"L2=小NLI模型+CP"提供最强成本论证 |
| A8 | The Semantic Illusion | arXiv 2512.15068 (2025) | 嵌入式幻觉检测在真实幻觉上conformal阈值全拒（FPR 100%）；难题在语义尾部 | 提醒：CP阈值对难例保守，需要abstention通道而非硬判定 |
| A9 | LYNX: Learning Dynamic Exits for Confidence-Controlled Reasoning | arXiv 2512.05325 (2025) | 隐状态探针+split conformal控制提前退出（token降40–65%），一次训练跨任务迁移 | ★级联"提前退出"的CP化实现范式 |
| A10 | CovNav (Conformal-gated System1→System2) | arXiv 2610.27677 [2026前沿] | CP把双过程推理变成不确定性感知决策：仅12.4%查询升级到慢思考 | ★与"双模式退出"同构：快通道可信时直接退出 |
| A11 | ACSE: Adaptive Conformal Semantic Entropy | IJCAI 2026 (arXiv 2605.04295) | 语义熵聚类+conformal接受/弃权，TriviaQA AUROC 0.88 vs token熵0.65 | 连续不确定性+离散接受决策的合成示范 |
| A12 | DualStake | EMNLP 2026 (arXiv 2609.00935) | 证据置信度(E-Conf)与答案置信度(A-Conf)双路径联合校准；E-Conf更强 | ★★对应L1证据充分性 vs L2判定置信的双通道 |
| A13 | CDC: Rethinking Misalignment via Causal + Dempster-Shafer | NeurIPS 2024 (arXiv 2410.12816) | 结构因果模型+前门调整+DS证据理论评估各语义预测不确定性 | DS在现代VLM中的正面案例 |
| A14 | EDL多模态融合的诚实负结果两篇 | arXiv 2609.01742 / 2608.29235 [2026前沿] | DS融合不优于简单平均；冲突质量在低冲突数据集上失效；DBF与无折扣平均无差异 | ★设计DS融合前必读：冲突度量本身可能是惰性组件 |
| A15 | Auditing Conformal Prediction under Inference-Time Model Shift | NeurIPS 2026 (arXiv 2610.28937) | 推理配置（量化/温度）改变会破坏CP交换性，覆盖率被高估 | 校准协议须报告推理配置（可审计性） |
| A16 | 可审计AI：三层审计(Mökander et al., AI Ethics 2023)；Co-audit (arXiv 2310.01297)；SSRM半结构化推理可审计 (arXiv 2505.24217)；AdaTest++ (AIES 2023)；CALM (AAAI 2025) | 见各自arXiv | 治理审计/模型审计/应用审计三层；人机协同复核工具；结构化推理痕迹+DSL审计规则 | ★"可审计验证"的框架叙事（军工域天然契合） |

### A.2 可融入的创新点

**A-Ⅰ. Conformal级联退出（CP-wrapped cascade exit）** ★★★ 直接融入，低成本
- 做法：L2 NLI输出（支持/矛盾/中立）过split-conformal校准层；预测集为单例→机器判定；非单例→按规则升级人工。L1符号通道的覆盖率作为分组条件（per-layer exchangeability）。
- 差异化：现有CP工作都在单模型输出上（A1/A6）；"异构级联（符号层+神经层）的分层校准"无先例。A10/CovNav只做同质双过程。
- 评测：覆盖-信息量曲线（A7的批判协议）+ 人工预算节省率；A15要求报告校准配置。
- 风险：A8显示难例上集合过大→正好落到我们的弃权/人工通道，与双模式退出互补而非冲突。

**A-Ⅱ. 双通道置信度合成：离散可判定性⊕连续置信** ★★
- L1给出离散量（规则命中数/Z3可满足性），L2给出连续量（NLI概率）。合成方案：(a) DualStake式双路径联合校准（A12）；(b) DS证据融合+冲突折扣（A13），但必须按A14的负结果做对照实验（DS vs 加权平均）。
- 论文叙事："混合离散+连续置信度的合成退出判据"——用户方向A的原始提问，文献支持充分。

**A-Ⅲ. 语义熵探针作L2的廉价弃权信号** ★★
- A3在NLI头接SE探针，对"中立/矛盾"边界样本主动弃权，替代采样式语义熵（成本高）。

**A-Ⅳ. 可审计性作为一等公民输出** ★★（军工域卖点）
- 每个判定输出SSRM式半结构化审计痕迹（触发规则ID、Z3 unsat core、证据span、置信区间）；框架对齐Mökander三层审计。与B/C的evidence grounding配合。

---

## B. 多粒度/层次化验证

### B.1 论文清单

| # | 论文 | 出处 | 核心机制 | 与本架构关系 |
|---|------|------|----------|--------------|
| B1 | AVeriTeC: Real-world Claim Verification with Evidence from the Web | NeurIPS 2023 D&B (arXiv 2305.13117) | 4568真实声明+QA对证据+文本justification；**AVeriTeC得分=判定正确∧证据质量达标** | ★★评测协议模板：判定与证据联合评分 |
| B2 | ProgramFC: Fact-Checking Complex Claims with Program-Guided Reasoning | ACL 2023 (arXiv 2305.12744) | 声明→程序分解→函数库逐段执行验证 | 与Logic-LM同族；L1可程序化 |
| B3 | The Alignment Bottleneck in Decomposition-Based Claim Verification | arXiv 2602.10380 [2026前沿] | 分解只在**证据粒度严格对齐**时有效；重复声明级证据反降性能；保守弃权显著减少误差传播 | ★★为残差训练设计提供因果性证据 |
| B4 | ElementCheck: Complexity-Aware Long-Form Factuality Evaluation | EMNLP 2026 Findings (arXiv 2608.26118) | 句→元素图（实体对）；图拓扑估计复杂度：简单句直接验、复杂句元素级精验 | ★复杂度感知的验证粒度选择 |
| B5 | ProFact: Agentic RL for Multi-Stage Fact Verification | arXiv 2606.13262 [2026前沿] | 过程感知奖励（分解/取证/判定逐级监督）优化多阶段验证轨迹 | 若对级联做端到端训练的奖励设计 |
| B6 | CFMS: Coarse-to-Fine Multimodal Synthesis for Tabular Reasoning | arXiv 2604.10973 [2026前沿] | 粗阶段MLLM整体感知→生成"推理地图"→细阶段符号引擎定点操作 | ★先判大方向再定位细节的两阶段范式 |
| B7 | PARTAB: Partition-Aware Reasoning over Tables | arXiv 2608.24082 [2026前沿] | 列组+行分区的层次化证据接口，先选证据区域再组合 | 表格行→证据span的定位机制 |
| B8 | QuanTemp++ (数值声明分解+检索评测) | arXiv 2510.22055 (2025) | 人类查证员的分解式检索仿真；时间泄漏控制 | 数值类不一致（同参数不同值）的检索协议 |
| B9 | Peerify: Manuscript-Grounded Peer-Review Claim Verification | arXiv 2609.25046 [2026前沿] | 审稿意见→原子声明→稿件内取证→蕴含判定；300条人工子集审计自动监督 | ★"文档内验证+自动标签审计"与我们场景同构 |

### B.2 可融入的创新点

**B-Ⅰ. 证据对齐的残差训练（evidence-aligned residual learning）** ★★★
- 现有创新"只在L0/L1不可判定子集上训练NLI"可升级：B3证明子声明-证据粒度不对齐时分解反伤性能。残差训练样本构造时强制（子声明, 对齐证据span）配对；不可对齐样本进弃权而非硬标。
- 差异化：把"分解对齐性"作为训练数据过滤准则，在RE域无先例。

**B-Ⅱ. 复杂度感知的验证粒度（coarse-to-fine granularity）** ★★★
- L0实体图→元素图（B4式实体对+可验证连接）→复杂度评分：低复杂度条目走L1规则直判；高复杂度条目进入细粒度L2甚至行/span级定位（配合C方向）。B6/B7提供两级结构依据。
- 与现有双模式退出衔接：粒度选择本身就是"退出判据"的扩展维度。

**B-Ⅲ. AVeriTeC式判定∧证据联合评分协议** ★★★（评测贡献）
- Gold Standard标注必须含：判定 + 证据span + justification。得分=判定正确∧证据定位正确。使我们的数据集成为"需求域的AVeriTeC"；同时回应项目内`48_alignment_gold_and_retrieval_preregistration.md`的对齐要求。
- B1的CLEF共享任务（21队参赛）证明该协议社区接受度高。

**B-Ⅳ. 过程奖励** ★（若做端到端优化）
- B5的逐级奖励用于微调级联策略；纯科研加分项，工程成本高。

---

## C. 跨模态证据融合（文本+表格+图48张）

### C.1 论文清单

| # | 论文 | 出处 | 核心机制 | 与本架构关系 |
|---|------|------|----------|--------------|
| C1 | MMFakeBench: Mixed-Source Multimodal Misinformation | ICLR 2025 (arXiv 2406.08772) | **三源分类法：文本真实性失真 / 视觉真实性失真 / 跨模态一致性失真**，12子类；MMD-Agent工具调用 | ★★不一致类型学的直接模板 |
| C2 | VERITE + CHASMA | arXiv 2304.14133 (2023) | 消除单模态偏置的多模态基准；CHASMA合成跨模态对齐训练数据 | 评测设计：防止单模态捷径 |
| C3 | FKA-Owl: Knowledge-Augmented LVLMs for Fake News | ACM MM 2024 (arXiv 2403.01988) | 伪造特定知识（图文语义相关+篡改痕迹）注入LVLM | 图证据的知识增强路径 |
| C4 | ChartCheck: Explainable Fact-Checking over Charts | arXiv 2311.07453 (2023) | 1.7k图表+10.5k人写声明与解释；chart-to-table+VL基线 | ★图表声明验证的先例（48张图的对手方） |
| C5 | HIPPO: Hybrid-Modal Preference Optimization | arXiv 2502.17315 (2025) | 表格同时以文本+图像双表示，DPO学习模态一致采样，互补语义提取 | ★表格双表示偏好优化（成本低于预训练） |
| C6 | CRAFT: Counterfactual Reasoning for Tabular QA & Verification | arXiv 2606.06842 [2026前沿] | 声明+反事实变体双向验证，加权证据融合，缩小骨干模型差距 | ★★表格验证的反事实双向机制（兼E方向） |
| C7 | TableMoE: Neuro-Symbolic Routing for Multimodal Tables | arXiv 2506.21393 (2025) | 符号路由预测单元格语义角色（表头/数据/公式）→专家连接器；WildStruct鲁棒性 | 表格结构证据的神经符号路由 |
| C8 | ATF: Adaptive Table Filtering | arXiv 2506.23463 (2025) | 问题感知的列/行剪枝（省70%单元格）；但Table Fact Verification需全表 | 成本优化与全表保留的权衡证据 |
| C9 | IntroConformal (LVLM事实性的CP保证) | EMNLP 2026 (arXiv 2609.01375) | 内省信号（层间语义稳定性/自判概率）作符合度分数的CRC框架 | 多模态通道的CP校准示范 |

### C.2 可融入的创新点

**C-Ⅰ. 三源不一致类型学（SRS版MMFakeBench分类法）** ★★★
- 把SRS不一致定义为三维：**文本真实性**（正文自相矛盾/参数值冲突）、**结构真实性**（表格/编号/图内部错误）、**跨模态一致性**（正文↔表格↔图接口图矛盾），再细化子类（如"表-文参数矛盾""图-文接口数量矛盾"）。
- 价值：给"不一致性类型清单（调研1）"一个有顶会出处的形式框架；同时是数据集贡献的组织轴。

**C-Ⅱ. 表格行→证据span→图区域的层次定位** ★★★（与B-Ⅱ合并实现）
- PARTAB式分区证据接口 + ChartCheck式chart-to-table转换：接口图先转结构化事实，再进L1符号规则通道。输出定位到（行号, span, 图区域）三元组→天然满足AVeriTeC式证据质量评分（B-Ⅲ）。

**C-Ⅲ. HIPPO式双表示（文本表格+图像表格）偏好训练** ★★
- GJB表格markdown与截图双通道，DPO做模态一致优化——参数效率高，比重训MLLM现实得多。

**C-Ⅳ. CRAFT式反事实双向加权融合** ★★
- 每对条目构造反事实变体，正反两条路径证据加权融合——兼作E-Ⅱ的忠实性检查（见E方向）。

---

## D. 主动学习 / 人在回路

### D.1 论文清单

| # | 论文 | 出处 | 核心机制 | 与本架构关系 |
|---|------|------|----------|--------------|
| D1 | From Selection to Generation: Survey of LLM-based Active Learning | ACL 2025 (arXiv 2502.11767) | LLM在AL循环中的角色分类：选择/生成/标注 | 方向地图 |
| D2 | FreeAL: Human-Free Active Learning with LLMs | EMNLP 2023 (arXiv 2311.15614) | LLM粗标注+SLM过滤高质量上下文回传LLM精炼 | ★小模型过滤大模型标注=级联镜像 |
| D3 | HADAS: Hallucination Diversity-Aware Sampling | NAACL 2024 (arXiv 2404.01588) | 按幻觉类型多样性（语义框架/篇章/内容可验证性）选样本标注 | "什么样本最值得人工"的类型多样性准则 |
| D4 | AL4RAG: Active Learning on Conversation Records | arXiv 2502.09073 (2025) | 选易幻觉对话样本给专家标注；RAG专用距离度量 | 幻觉易发样本选择=残差选择的同构问题 |
| D5 | CAL: Causal-Guided Active Learning for Debiasing | ACL 2024 杰出论文 (arXiv 2408.12942) | LLM自主识别偏置样本+因果归纳偏置模式+ICL去偏 | 因果×主动学习的结合示范（兼E方向） |
| D6 | ActiveLLM | TACL (arXiv 2405.10808) | LLM直接做获取函数，解决冷启动 | LLM作选择器的基线 |
| D7 | Reassessing AL Adoption in NLP: Community Survey | EACL 2026 (arXiv 2503.09701) | 三大持续障碍：搭建复杂度/成本不确定/工具链 | 工具化贡献的论证（RE工程域卖点） |
| D8 | 混合人机标注（不确定性路由） | LAW 2024 (arXiv 2406.12114) | 模型不确定性低于阈值→LLM标注；否则→人工 | ★不确定性作为人/机标注路由器 |
| D9 | How Synthetic Labels Improve Conformal Prediction | arXiv 2609.33482 [2026前沿] | LLM合成标签池+小规模可信人工集做偏差校正→conformal化 | ★★"少量金标×LLM伪标签"的校准协议 |
| D10 | APE / Co-audit / AdaTest++ | DaSH 2024 / arXiv 2310.01297 / AIES 2023 | 人机协同审计工具族：主动选例→人复核→迭代 | 军工SRS审核界面设计原则 |

### D.2 可融入的创新点

**D-Ⅰ. 级联驱动的主动学习（cascade-aware acquisition）** ★★★
- 获取函数不再只用模型熵，而是级联结构信号：{L1规则覆盖率, L2 NLI熵, L2预测集大小(A-Ⅰ), 层间分歧}。人工只标"级联弃权/层间分歧"样本，标完直接回流L2残差训练集——闭环成"active residual learning"。
- 差异化：现有AL×LLM（D1综述分类）均为单模型不确定性；"级联分歧作为获取信号"无先例。D2(FreeAL)的SLM-过滤-LLM结构与我们的L2-L1恰成镜像，可在related work中明确对照。
- 评测：标注预算-F1曲线 + 与熵采样/随机/多样性(D3)基线比较。

**D-Ⅱ. 小金标×LLM伪标签的conformal校准协议** ★★
- D9的prediction-powered思路：人工金标（可信集）校准LLM伪标签偏差，得到带保证的阈值。直接回应项目`no_human_annotation_eval_survey.md`中"无标注评测"与军工域"少量专家标注可用"之间的现实。

**D-Ⅲ. 人机路由阈值=双模式退出的自然扩展** ★★
- D8的不确定性路由与本架构"确定性/置信度双模式退出"拼成三层：确定性规则→校准置信→人工。审计痕迹（A-Ⅳ）记录路由原因。

---

## E. 因果推理在验证中的应用

### E.1 论文清单

| # | 论文 | 出处 | 核心机制 | 与本架构关系 |
|---|------|------|----------|--------------|
| E1 | SCM-GRPO: Grounding Multi-Hop Reasoning in Structural Causal Models | arXiv 2605.01482 [2026前沿] | 证据-声明显式有向依赖图；推理链长度-准确率倒U关系；RL优化结构深度 | ★★证据图为SCM的声明级验证 |
| E2 | CRAFT (同C6) | arXiv 2606.06842 [2026前沿] | 声明+反事实变体双向验证+加权融合 | 反事实验证机制 |
| E3 | FARCA: Counterfactual Evidence Attribution | arXiv 2608.24350 [2026前沿] | 用"判定对关键证据的依赖度"作验证可靠性的经验代理→可靠性加权 | ★反事实归因=证据依赖度测量 |
| E4 | CausalMamba: Temporal Rumor Causality | arXiv 2511.16191 (2025) | Mamba+GCN+NOTEARS可微因果发现；移除top因果节点做反事实干预分析 | 因果图发现+干预式解释 |
| E5 | CDC (同A13) | NeurIPS 2024 | 结构因果模型+前门调整消解任务无关知识干扰 | 因果调整在验证管道内的用法 |
| E6 | Polyjuice: Generating Counterfactuals (Wu et al.) | ACL 2021 (arXiv 2101.00288) | 通用反事实生成（基础工作） | 反事实样本生成工具 |
| E7 | Truth or Tribe: 结构化反事实推理抑制偏差 | arXiv 2605.01329 [2026前沿] | 三种干预：身份盲指令/结构化反事实推理/异质视角集成 | 反事实作为系统级干预手段 |
| E8 | 需求域因果先例：Bendík & Wolf 2017 (SAT依赖图, 见AGENTS.md) | RE 2017 | 需求依赖+SAT可满足性 | 因果归因的RE前身=可满足性不可满足核 |

### E.2 可融入的创新点

**E-Ⅰ. 不一致性的因果归因（不只检测，还解释）** ★★★ 论文级差异化
- 两级归因机制：
  - 逻辑层：Z3 **unsat core**即精确因果核（"哪几条约束构成最小冲突集"）——求解器免费提供，却几乎无人把它当作"归因"卖点；
  - 语义层：**留一证据归因/反事实翻转**（E3式）：移除或翻转某证据span，看判定是否翻转→输出"本不一致由span X与span Y的值冲突导致"。Polyjuice(E6)生成反事实变体做探针。
- 叙事："从检测到解释：需求不一致的solver-core与反事实归因"。RE域完全空白（调研中未见任何SRS不一致归因工作）。

**E-Ⅱ. 验证器忠实性的反事实验证（meta-verification）** ★★★
- 用反事实不变性检查L2 NLI本身：把无关span改写，判定应不变；把关键值改动，判定应翻转。翻转行为正确=验证器真正"看"了证据而非表面特征。CRAFT(E2)是机制来源，但用于SRS验证器自检是新的。
- 回应审稿人最可能的质疑："你的NLI是否只是在做表层匹配？"

**E-Ⅲ. 需求依赖SCM化与干预查询** ★★
- E1的证据-声明DAG + E4的因果发现：对实体链接图加方向性，支持干预式查询（"若放宽3.2.1的时延约束，哪些冲突消失？"）——面向需求分析员的交互功能，RE会议受众多。

---

## F. 大模型时代的"小模型+规则"新范式

### F.1 论文清单

| # | 论文 | 出处 | 核心机制 | 与本架构关系 |
|---|------|------|----------|--------------|
| F1 | Logic-LM | EMNLP 2023 Findings (arXiv 2305.12295) | LLM→符号式→求解器+自修正（已有） | 我们L1的理论直系 |
| F2 | SatLM: Declarative Prompting | NeurIPS 2023 (arXiv 2305.09656) | 声明式规约比命令式程序更稳；GSM难子集+23% | 声明式与GJB规约天然契合 |
| F3 | LINC | EMNLP 2023 主会杰出论文 (arXiv 2310.15164) | **StarCoder-15.5B+一阶定理证明器 > GPT-4+CoT（ProofWriter +10%）**；两者失败模式互补 | ★★小模型+求解器胜大模型的旗舰证据 |
| F4 | SymbCoT | ACL 2024 (arXiv 2405.18357) | 符号翻译→符号规则CoT→自验证器三段式 | L1内嵌校验器设计 |
| F5 | VeriCoT: Neuro-symbolic CoT Validation | arXiv 2511.04662 (2025) | CoT步骤→FOL形式化+前提接地标注→求解器验证逻辑有效性；验证信号反哺SFT/DPO | ★★步骤级逻辑有效性检查=逻辑层的可审计细化 |
| F6 | Adaptive LLM-Symbolic Reasoning via Dynamic Logical Solver Composition | arXiv 2510.06774 (2025) | LLM预测所需形式推理策略（准确率>90%）→**动态选择/组合求解器**；超GPT-4o 27% | ★★求解器路由=级联的新自由度 |
| F7 | FrugalGPT | TMLR 2024 (arXiv 2305.05176) | LLM级联学习，成本降98%同性能 | 级联成本叙事源头 |
| F8 | RouteLLM | arXiv 2406.18665 (2024) | 偏好数据训练强弱模型路由器；换模型仍保持性能 | 路由器可迁移性证据 |
| F9 | CICLe: Conformal In-Context Learning | arXiv 2512.05732 (2025) | 轻量基分类器+CP收缩候选类→引导LLM提示；省token/用小模型 | CP作小→大模型的路由门 |
| F10 | A Survey of Small Language Models | arXiv 2410.20011 (2024) | SLM架构/压缩/评测全景 | F方向综述底座 |
| F11 | Neuro-Symbolic AI: Improving LLM Reasoning (Survey) | IJCAI 2025 (arXiv 2508.13678) | **Symbolic→LLM / LLM→Symbolic / LLM+Symbolic三分法** | ★定位图：我们=LLM→Symbolic主轴+Symbolic→LLM校准 |
| F12 | Hallucination Detection with Small Language Models | ICDE 2025 Workshop (arXiv 2506.22486) | 多个小LM"Yes"token概率集成做幻觉检测，F1+10% | 小模型集成当判定器 |
| F13 | Unifying LLMs and Knowledge Graphs: A Roadmap | TKDE 2024 (arXiv 2306.08302) | KG增强LLM三框架 | 与GJB规则库/知识图谱衔接 |
| F14 | Neurosymbolic Legal Reasoning (保险合同覆盖判定) | arXiv 2502.17638 (2025) | LLM+逻辑程序处理合同文本——与SRS同为"规约性长文档" | ★同构域成功案例（相关工作的类比支点） |
| F15 | ABACUS: Program-Guided Reasoning over Frozen Judgment Models | arXiv 2610.25963 [2026前沿] | 复用验证程序编排冻结判定模型；99.7%准确+8.4×加速 | 程序化编排冻结小模型 |
| F16 | 核心实证证据（旁证）：A7（NLI校验器≈LLM打分器，FLOPs÷100）；F3（15.5B+prover>GPT-4） | — | — | "为什么小模型+规则够用"的两条硬证据 |

### F.2 可融入的创新点

**F-Ⅰ. 动态求解器路由（solver routing）** ★★★
- F6证明LLM能高准确率预测"该用哪种形式推理策略"。L1按条目特征（含数值约束→Z3；含表→表代数；含文本蕴含→NLI前置）路由到不同求解器。这是对现有Logic-LM管线（固定Z3）的直接升级，且与L0实体类型联动。
- 差异化：需求验证域无先例；实现成本低（一个路由头+求解器接口注册表）。

**F-Ⅱ. 成本-精度-可靠性三方Pareto评测** ★★
- 用FrugalGPT/RouteLLM方法学（固定质量约束下最小成本；换骨干仍有效）评测全级联 vs 纯LLM vs 纯规则。F3+A7提供预期结论的文献依据；实验本身就是论文主表。
- 军工域加审计维度：第四轴"可审计判定比例"（A-Ⅳ）。

**F-Ⅲ. 步骤级逻辑有效性+前提接地（VeriCoT式）** ★★
- L1的Z3转换前先做"形式化步骤+前提来源标注"，求解器查逻辑有效性，人可查前提接地性——把"符号验证"细化为可审计的中间表示。

---

## 汇总：创新点优先级矩阵

| 创新点 | 方向组合 | 新颖度 | 架构契合 | 实现成本 | 文献支撑 | 建议优先级 |
|--------|----------|--------|----------|----------|----------|------------|
| B-Ⅲ AVeriTeC式判定∧证据联合评分（数据集协议） | B | 高（RE域空白） | 已有对齐基础 | 低 | B1/B9 | ★★★ 立即做 |
| E-Ⅰ 不一致因果归因（Z3 unsat core + 反事实翻转） | E | 很高（RE域完全空白） | L1已有Z3 | 低-中 | E3/E8 | ★★★ 立即做 |
| A-Ⅰ Conformal级联退出 | A×F | 高（异构级联无先例） | 双模式退出的直接升级 | 低 | A1/A6/A9/A10 | ★★★ |
| C-Ⅰ 三源不一致类型学 | B×C | 中-高（迁移自MMFakeBench） | 调研1的组织框架 | 低 | C1 | ★★★ |
| D-Ⅰ 级联驱动主动学习（人工只标残差） | D×F | 高（级联分歧获取函数无先例） | 依赖A-Ⅰ落地 | 中 | D1/D2/D8 | ★★☆ |
| B-Ⅱ 复杂度感知粒度+行→span→图区域定位 | B×C | 高 | 依赖B-Ⅰ | 中 | B4/B6/B7/C4 | ★★☆ |
| E-Ⅱ 验证器忠实性反事实验证 | E | 高（自检视角新） | L2已可做 | 低-中 | E2/E6 | ★★☆ |
| F-Ⅰ 动态求解器路由 | F | 中-高 | L1扩展 | 低 | F6 | ★★ |
| A-Ⅱ 双通道置信度合成（含DS对照实验） | A | 中 | 退出判据细化 | 低 | A12/A13/A14 | ★★ |
| A-Ⅳ 可审计输出（审计痕迹+三层审计框架） | A×B | 中（叙事价值高，军工域） | 与所有判定通道耦合 | 低 | A16组 | ★★（叙事主线） |
| F-Ⅱ 成本-精度-可审计Pareto主表 | F | 中 | 评测层面 | 低 | F3/F7/A7 | ★★（主实验表） |
| C-Ⅲ HIPPO式表格双表示DPO | C | 中 | 需训练资源 | 中-高 | C5 | ★ |
| E-Ⅲ 需求SCM化+干预查询 | E | 高 | 图谱已存在 | 高 | E1/E4 | ★（选做/vision章节） |
| B-Ⅳ 过程奖励训练级联 | B | 中 | 需RL栈 | 高 | B5 | ★（选做） |

## 组合叙事建议（论文骨架）

1. **方法主线**：`L0实体链接 → L1动态求解器路由(F-Ⅰ)+步骤级接地(F-Ⅲ) → L2残差NLI → Conformal级联退出(A-Ⅰ)`，每层产出SSRM式审计痕迹(A-Ⅳ)。
2. **问题定义**：三源不一致类型学(C-Ⅰ) × 复杂度感知粒度(B-Ⅱ)。
3. **评测协议**：AVeriTeC式判定∧证据评分(B-Ⅲ) + 成本-精度-可审计Pareto(F-Ⅱ) + A15式校准配置报告。
4. **深度差异点**：不一致因果归因(E-Ⅰ)与验证器忠实性自检(E-Ⅱ)——把"检测器"升级为"解释器"。
5. **数据扩展线**：级联主动学习闭环(D-Ⅰ)+小金标conformal校准(D-Ⅱ)解决标注稀缺。

## 风险与负结果预警（写论文时需正面回应）

- A8：CP在真实难例上集合过大→须与弃权通道联动报告"信息量-覆盖"双指标（A7协议）。
- A14：DS融合可能不优于加权平均→DS只作对照组件不作核心主张。
- A15：推理配置漂移破坏CP交换性→固定解码配置并写进实验协议。
- B3：声明分解在证据不对齐时反降性能→分解必须与证据span配对（B-Ⅰ）。
- KalshiBench等2025-12基准显示更强推理模型校准更差→若用大模型做裁判，需单独报告其校准。

## 检索记录（复现用）

arXiv API端点 `export.arxiv.org/api/query`，检索窗口 2023-01-01~2025-12-31 与 2024-01-01~2025-12-31，排序 submittedDate/relevance。核心精确标题命中：Logic-LM / SatLM / LINC / SymbCoT / RouteLLM / FrugalGPT / ProgramFC / VERITE / MMFakeBench / FreeAL / FKA-Owl / ChartCheck / AVeriTeC / Semantic Entropy Probes / Conformal Factuality 等。Semantic Scholar API 429限流未使用。未核实条目仅限记忆引用（已标注：Kuhn ICLR 2023、Farquhar Nature 2024、Polyjuice ACL 2021、FrugalGPT TMLR 2024）。
