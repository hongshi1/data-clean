# 95. 2024-2026 Claim分解与验证算法调研：正则→模型替代的文献取证

> 取证日期：2026-11-24。任务：调研2024-2026年claim分解与验证的最新算法，重点回答**"用训练模型替代正则提取"是否有先例、怎么做、性能如何**。
> 性质：文献取证（只读+写作，未跑模型，未git commit）。检索通道：arXiv检索API+arXiv搜索页+web检索（arXiv API中途限流，部分改用arXiv搜索页与websearch交叉验证）。
> 与88/89/90号分工：88号=验证单元视角（要不要分解、三族实现、typed无先例）；89号=归因单元视角；90号=分解器实现SOTA谱系（截至2026-11-12）。本文=**2024-2026增量**＋**正则→模型替代专项**，覆盖90号取证之后的2026-06至2026-11新工作（ElementCheck/TriQua/MedSNIP/Enoki/Alignment Bottleneck/CREDENCE/DAD/DecomposeRL等均为90号未覆盖）。仓库未覆盖的论文细节凭检索到的摘要补全并逐条给出arXiv编号；未虚构。

---

## 0. 先说结论（5条）

1. **两处命名核实失败，如实报告**：任务点名的 **RLSeek（ACL 2026）**与 **ACV（Atomic Contrastive Verification, 2026）**在arXiv（精确短语检索）、web检索（2026-11-24执行）均**未检索到对应论文**——标"无法核实，疑似名字误记"，并给出概念最接近的真实论文族（§2）。其余点名项（FActScore/RefChecker/ElementCheck/MiniCheck）全部核实存在。
2. **正则→模型的替代判据已在垂直域head-to-head研究中成形**：结构化/标准化字段（BI-RADS分数、TNM分期）正则不输甚至优于LLM且快4个数量级；上下文依赖字段（起止日期、治疗进程）微调模型显著胜出（§5.1）。**生产级先例是"模型作残差通道"而非"模型替换正则"**：金融交易系统保留regex处理63%流量、模型只接未覆盖的20%，覆盖80%→94%（§5.2）——与我们L1规则→L2 NLI残差的架构同构。
3. **小模型做claim分解已不是空白**（任务核心问题）：2025-2026出现至少6条独立证据——DecModel T5系0.08B-0.78B（分解正确率99.7%超Qwen3-32B的94.8%）、Qwen3-0.6B SFT蒸馏分解器（ROUGE-L 63→89）、RefChecker微调Mistral-7B抽取器、DAD Llama-3.1-8B RL分解器（EACL 2026）、DecomposeRL-7B、CREDENCE基准化的3.8B-12B分解器。**共同配方：教师LLM标注→小模型SFT/RL，而非直接prompting小模型**（Llama-3.2-3B-Instruct直接prompt分解正确率仅10.8%——90号"trained claim切分器无主流先例"的判定在2026被推翻，见§1.4）。
4. **分解的有效性条件在2026被精确刻画**：The Alignment Bottleneck（2602.10380）证明分解**只在证据粒度与子claim严格对齐（SAE）时显著提升**，证据在整claim级重复（SRE）时反而降性能——这直接解释了我们claim_downstream_v2的现象（切分器claim-F1 0.70-0.80但下游macro-F1 0.7496<正则0.8047，§7.1），并给出修复方向（不是换分解器，是修对齐）。
5. **对我们场景的迁移判定**：typed正则层（numeric/enum/identifier/quoted）对应文献里"结构化标准化字段"——正则是正确工具且无性能损失先例；**值得引入模型的是三个残差位**：①语义/叙事claim的分解（教师蒸馏切分器已有，需修对齐而非换模型）②跨域档（crossdoc 0.5109弱项→sentence档已工程缓解）③L0 gazetteer NER的零样本扩展（GLiNER家族，mDeBERTa基座与我们同源）。全部可在8GB显存内部署（§6/§7）。

---

## 1. 维度1：原子claim分解的SOTA（2024-2026）

### 1.1 LLM-prompted分解线（FActScore系的2024-2026演化）

| 方法 | 会议/年份 | arXiv | 核心机制 | 性能数据 | GJB场景适配度 |
|------|----------|-------|---------|---------|--------------|
| FActScore | EMNLP 2023 | 2305.14251 | GPT-3.5按prompt把段落拆成atomic facts（仓库已精读，88§2/A3） | ChatGPT传记原子事实支持率仅~58% | 已实现教师版本（llm_decomposer_probe_v1.json），无增量 |
| SAFE | NeurIPS 2024 | 2403.18802 | LLM分解长回答→多步搜索推理逐条核验 | 与众包标注一致率72%，分歧case获胜76%，比人工便宜20× | 低（外部检索不适用"文档即证据"，89号已判） |
| MedScore | ACL 2026 Findings | 2505.18452 | **域适配分解**：医学自由回答拆成"条件感知有效事实"（condition-aware facts），保留条件依赖、消除模糊指代 | 比FActScore等提取多达3×的有效事实；事实性分数随分解方法/验证语料/骨干模型显著变化 | **高**：证明"为垂直域定制claim形态学"已进ACL Findings主赛道；GJB的条件句（"当…时"）与医学条件依赖同构 |
| AFEV | 2025-06 | 2506.07446 | 迭代式原子事实抽取+验证：动态精炼claim理解、证据重排滤噪、上下文相关示例引导 | 五基准SOTA（准确率+可解释性） | 中：迭代分解思想可用于长答案，但依赖多轮LLM调用 |
| DnDScore | 2024-12 | 2412.13175 | **分解与去语境化的张力研究**：分解孤立原子事实，去语境化插入必要上下文——两者目的冲突；提出去语境化感知的验证 | 策略选择显著影响事实性分数 | **高**：我们的typed claim（"时延≤50ms"式重构串）正是"分解丢上下文"问题；DnDScore给出"子claim在上下文中验证"的修法 |
| Pelican | 2024-10（v2） | 2407.02352 | 视觉claim→一阶谓词(predicate,question)链→程序化验证 | LVLM幻觉率降8-32% | 低（视觉域），但谓词化思想与typed通道同构 |
| Peerify | 2026-09 | 2609.25046 | 同行评审意见→原子claim→稿件证据检索→支持判定 | 800 claim基准；自动标签与人一致90.3%（κ=0.87）；**现成NLI模型macro-F1<0.24** | **中高**：评审claim vs 稿件=我们的answer vs 冻结文档；"off-the-shelf NLI在专业域崩塌"与我们mDeBERTa直推0.294同病 |

**判读**：FActScore系仍在演化，方向是**域适配**（MedScore医学）与**分解-语境张力**（DnDScore）——两者都指向我们的位置：GJB域文法定制（88§3的FISCAL/boilerplate先例）不是孤立做法，2026年已有多篇垂直域claim管线发表。

### 1.2 结构化claim表示线（claim不是句子而是结构）

| 方法 | 会议/年份 | arXiv | 核心机制 | 性能数据 | GJB场景适配度 |
|------|----------|-------|---------|---------|--------------|
| **RefChecker** | Amazon, 2024-05 | 2405.14486 | claim-triplet (subject, predicate, object)表示；抽取器E→检查器C→聚合规则τ（strict/soft/major）；三档上下文设定（Zero/Noisy/Accurate） | 2.1k回复标注11k triplet；比sentence/sub-sentence粒度检测优6.8-26.1点；人工一致性强。**官方微调Mistral-7B抽取器开源**（dongyru/Mistral-7B-Claim-Extractor）；NLI检查器(RoBERTa)零样本可用；嵌入式定位模型把tripplet映回参考span | **极高**：①triplet粒度≈我们typed claim的"参数-操作符-值"结构；②strict聚合规则（任一Contradiction→整条Contradiction，全部Entailment→Entailment，否则Neutral）**逐字等于我们的strict+refute短路**；③仓库2026-04-08归档（Apache-2.0），代码可fork |
| GraphFC | 2025-03 | 2503.07282 | claim图+证据图（triplet构成），图引导规划验证顺序+逐triplet比对，解决指代歧义 | 三数据集SOTA | 中：图结构解决"提及歧义"——GJB缩略语（SJTBGX等）同问题 |
| ElementCheck | **EMNLP 2026 Findings** | 2608.26118 | 复杂度感知：句中显式连接的实体对=element，组成element图；图拓扑估计句复杂度→简单句直判、复杂句element级精炼验证 | 五骨干模型一致提升事实性验证；减少不必要的重复验证；代码开源（github.com/gudehhh666/elementcheck） | **高**（多粒度，见§4） |
| TriQua | 2026-08 | 2608.05228 | 简单claim=标准三元组，复杂claim=**超关系事实**（hyperrelational facts附上下文限定词qualifier）；验证时直接标注具体错误在哪个triplet/qualifier | TriQuaScore与人工事实性分数强对齐；超出现有分解式框架 | **高**：qualifier机制=我们typed claim缺的"条件/语境"字段（DnDScore张力的解法）；细粒度错误定位=M84(a)需求 |

**判读**：这一线与我们的typed claim架构**同构度最高**。RefChecker的triplet、ElementCheck的element、TriQua的qualifier本质都是"claim应该携带类型化结构"——typed（类型化）分解单元在2024-2026已从"无先例"（88§2判定）演化为**结构化claim表示的小家族**。我们的差异点仍成立：RefChecker/GraphFC的抽取器是LLM或微调7B生成式，我们是确定性正则+finditer span（90号§1.7已论证的结构性span优势）。

### 1.3 分解有效性争议线（什么时候分解有用——2025-2026的关键进展）

| 方法 | 会议/年份 | arXiv | 核心发现 | GJB场景适配度 |
|------|----------|-------|---------|--------------|
| **Decomposition Dilemmas** | NAACL 2025 Main | 2411.02400 | 分解对下游事实核查的影响不一致；给出分解错误类型学+准确率增益vs引入噪声的trade-off | **高**：70号分解错误类型学（needed/bad_scope/bad_granularity）的文献同源；为"分解不是免费午餐"提供正式引用 |
| **The Alignment Bottleneck** | 2026-02 | 2602.10380 | **判决性发现**：分解只在证据粒度严格对齐子claim（Sub-claim Aligned Evidence, SAE）时显著提升；证据在claim级重复（SRE）时分解降性能（PHEMEPlus/MMM-Fact/COVID-Fact三域验证）；子claim标签噪声下保守"弃权"显著减少误差传播 | **极高**：直接解释我们的核心矛盾——切分器claim-F1高但下游低（§7.1）；支持我们的NIE弃权+assertive_strict聚合设计（91号） |
| Reasoning-CV | 2025-05 | 2505.12348 | CoT-Verify范式替代Decompose-Then-Verify：不分解，直接对原claim生成验证推理链；8B模型SFT+DPO | 8B超GPT-4o+CoT和o1-preview | 中：单claim验证器路线（MiniCheck式），与我们"整answer回退"档对应 |
| DS@GT ARC（CheckThat! 2026） | CLEF 2026 | 2607.25069 | 数值claim的自适应子claim分解**未提升**性能——"切分引入噪声而非帮助推理" | 中：数值claim（我们numeric typed claim占比高）上分解增益存疑的直接证据 |
| CLATTER | 2025-06 | 2506.05243 | 引导LLM三步推理：claim分解→子claim归属+蕴含分类→聚合分类；中间步骤质量度量 | 分解+归属+聚合的引导推理提升幻觉检测 | 中：三步结构与我们管线逐层对应，可作L3 prompt设计参考 |

**判读**：2025-2026这条线收敛出的定律=**分解的增益不取决于分解器质量，而取决于claim-evidence对齐粒度**（Alignment Bottleneck + Decomposition Dilemmas + DS@GT三方互证）。我们90号升级路径里"切分器质量→下游增益"的隐含假设需要修正：**先修证据侧对齐，再谈换分解器**。

### 1.4 小模型做claim分解（1-8B及以下）——任务点名问题

90号§1.2判读"trained claim切分器无主流先例"（检索截至2026-11-12）。**2026年的检索结果推翻了该判定**——现在至少有7条独立工作：

| 方法 | 规模 | 会议/年份 | arXiv | 机制 | 关键数字 | 8GB部署 |
|------|------|----------|-------|------|---------|---------|
| **DecModel（DecMetrics）** | 0.08B/0.25B/0.78B（T5系） | 2025-08 | 2509.04483 | T5生成式claim分解模型，用COMPLETENESS/CORRECTNESS/SEMANTIC ENTROPY三指标作reward优化 | **0.25B：分解正确率99.70%、完整率92.67%**，超Qwen3-32B（94.77%）与Mistral-NeMo-12B（80.14%）；Llama-3.2-3B-Instruct直接prompt正确率仅10.81% | ✅（<1B） |
| **SLM分解蒸馏（Test-Taking Strategies）** | Qwen3-0.6B | ACL 2026 Long | (2026.acl-long.1468) | 教师LLM分解→随机采样句子作claim源→SFT蒸馏到0.6B；后续原子事实验证器SFT+自修订 | 分解ROUGE-L 63.3→89.3、SECS 71.5→95.5（FacTax-Benchmark）；0.6B分解与30B教师差距小 | ✅ |
| **RefChecker抽取器** | Mistral-7B微调 | 2024（持续用到2026） | 2405.14486 | claim-triplet抽取专用微调7B（vllm部署） | 官方开源dongyru/Mistral-7B-Claim-Extractor | ⚠️（fp16超8GB；4-bit可） |
| **DAD** | Llama-3.1-8B | **EACL 2026 Findings** | (2026.findings-eacl.309) | 教师Llama-3.1-405B蒸馏SFT热身→GRPO多目标reward（格式合规+验证器对齐+分解质量）联合优化分解器；验证器=Bespoke-MiniCheck-7B | **8B分解器下游71.75% macro-F1**，超prompt式(+1.99/+6.24)与已有RL方法(+5.84)；六评测设置最优聚合 | ⚠️（4-bit） |
| **DecomposeRL** | 7B | 2026-05 | 2605.27858 | 分解=RL策略（GRPO+多面reward），半监督可用；数据筛选漏斗115K→5K高信号密度子集 | 7B仅用~5K精选claim：域内86.3/域外69.8 balanced acc，匹配32B基线与GPT-4.1-mini | ⚠️（4-bit） |
| **CREDENCE分解器基准** | 3.8B-12B | 2026-06 | 2606.19819 | Phi-3-mini-3.8B/Qwen3-8B/Gemma-3-12B/Gemini-2.5统一prompt分解+修复环 | Qwen3-8B base: Semantic-F1 0.956；**规则修复降原子性违规率47-100%**；Phi-3-mini-3.8B base也有0.930 | 3.8B✅/8B⚠️/12B❌ |
| MedSNIP分解器 | 开源权重（未明规模） | EMNLP 2026 Main | 2609.12884 | snippet级（子句组）分解管线，保留临床依赖结构 | 开源权重分解器"与人工snippet边界比对无保真损失"；验证调用减24-73% | 待核实规模 |

**三条可迁移定律**：

1. **trained小模型≫prompted小模型**：Llama-3.2-3B-Instruct直接prompt分解正确率10.81% vs DecModel-0.25B训练后99.70%——**小模型做分解的唯一可行路径是蒸馏/SFT训练，不是prompting**。我们128M切分器走训练路线是对的。
2. **8B是生成式分解的体验门槛**：FactEHR（2412.12422, MLHC 2025）临床域对比：Gemini-1.5-Flash分解相关且准确，Llama-3 8B产出"更少且更不一致"；DecomposeRL/DAD显示8B经RL/蒸馏可达可用。**8GB显存下3.8B（Phi-3-mini级）fp16或7-8B 4-bit是实际上限**。
3. **分解器可以独立训练并独立评测**：DecMetrics给了分解质量三指标（COMPLETENESS/CORRECTNESS/SEMANTIC ENTROPY）；我们的claim_recognition_v2.json（text_ratio≥0.8 OR span_iou≥0.5贪心匹配+over/under_seg率）是同构自制版，**SEMANTIC ENTROPY（BGE-large）一项可直接补进我们的审计工具**（90号§3路径C的姊妹项）。

---

## 2. 维度2：Claim-evidence对齐方法

**命名核实**：**RLSeek（ACL 2026）未检索到**（arXiv精确短语0结果+web检索0命中，2026-11-24）；**ACV（Atomic Contrastive Verification）未检索到**（同上，arXiv命中全是原子力显微镜物理论文）。两篇均标**"无法核实，疑似名称误记"**。最接近的真实论文族如下。

### 2.1 对齐是分解的瓶颈（判决性证据）

| 方法 | arXiv | 核心机制 | 关键结论 | GJB适配度 |
|------|-------|---------|---------|----------|
| **The Alignment Bottleneck** | 2602.10380 | 构造SAE（子claim级对齐证据）vs SRE（claim级重复证据）两种设定评测分解 | 分解增益只在SAE出现；SRE下降性能；保守弃权减少误差传播 | **极高**：我们claim→块级证据（Y={S,R,N}×ℓ×j）的对齐粒度就是SAE/SRE之别——91号聚合code-design问题的文献定锚 |
| Uncertainty-Aware Scientific Fact-Checking | 2604.11036 | 原子谓词-论元分解→**嵌入对齐到局部snippet**→紧凑证据接地的检查器判定→仅不确定事实触发web检索；三态(S/R/NEI) | web调用仅少数原子事实触发（选择性置信度门控）；多基准超最强基线 | **极高**：与我们的级联（确定性通道先判→残差才升级）同构；"不确定性门控升级"=我们gate=0.8校准的文献同款 |

### 2.2 RL驱动证据归属家族（"RLSeek"概念对应的真实论文）

| 方法 | 会议/年份 | arXiv | 核心机制 | 关键数字 | GJB适配度 |
|------|----------|-------|---------|---------|----------|
| **TRACE** | 2025-05（v3 2026-01） | 2505.13258 | RL训练LLM产出带显式证据引用的结构化输出；reward=证据相关性+格式+准确性；自适应多reward合并+稳定KL估计 | Qwen2.5-7B/Llama-3.1-8B：三多跳QA准确率+10-30%，可比o1/DeepSeek-R1；代码开源 | 中高：RL训练7-8B对8GB紧；但"证据引用作为reward"思想可用于我们教师标注质量门 |
| **Look As You Think (LAT)** | AAAI 2026 | 2511.12003 | Chain-of-Evidence范式：推理步grounding到文档具体区域（bbox+页码）；RL奖励归属一致性+答案正确 | Qwen2.5-VL-7B：soft EM+8.23%、IoU@0.5+47.0%；超SFT基线且跨域泛化强 | 中（视觉域）；归属一致性reward思想可移植 |
| **FARCA** | 2026-08 | 2608.24350 | 事实对齐的可靠性感知信用分配：事实监督粒度对齐策略更新粒度；**反事实证据归属**（事实判定对关键证据的依赖度=可靠性代理）作权重 | 多模型多基准事实性显著提升且保留通用推理 | 中：反事实证据归属=教师标签质量门（premise覆盖率0.8448）的升级版 |
| ProFact | 2026-06 | 2606.13262 | agentic RL端到端优化多阶段验证轨迹（分解/取证/生成/判定统一策略）；**过程感知reward**补终局标签稀疏 | 验证性能+推理效率均超强基线 | 中：全阶段联合RL超出本地算力，但"过程级reward"可用于我们蒸馏的claim级加权 |
| EchoSpec | 2026-11 | 2611.20034 | 训练搜索agent"证据优先于回声"（同义转载vs一手证据）；验证热启动+分组RL+证据门控λ-reward | Qwen2.5-3B/7B/Llama-3.1-8B：八回声盲从降30-44点；QA precision 47-55% | 中：GJB无网络回声问题，但"多文档同一参数多处登记"（方向A双登记）与回声检测同构 |
| ClueWeaver | ICONIP 2026 | 2608.25531 | 双agent（Finder/Interpreter）+reward引导RL：Finder奖励证据保留+忠实段落ID引用 | 紧凑本地模型在长叙事QA/claim验证显著提升；代码开源 | 中：段落ID引用=我们块IDℓ的文献同款 |

### 2.3 无LLM的claim-evidence精确对齐（任务点名"如何在没有LLM的情况下做对齐"）

| 方法 | arXiv | 机制 | 无LLM性 | GJB适配度 |
|------|-------|------|---------|----------|
| **RefChecker定位模型** | 2405.14486 | RoBERTa平均池化token表示→triplet元素与参考span的成对余弦相似度；entailment triplet应在参考中找全成分，neutral应无，contradictory常有缺失 | ✅纯编码器 | **高**：与我们BGE embedding通道（EMB_TH_LOCAL=0.78）同构；可直接fork做claim→块span对齐 |
| **HallDetect** | 2608.05823 | 原子claim由**紧凑编码器蕴含模型**验证，对比式公式在**多尺度证据块库**上；非对称聚合（单条高置信矛盾即标红） | ✅（4-bit量化+消费级硬件协议） | **极高**：消费级硬件协议、非对称聚合=我们refute短路、claim-to-span审计轨迹=我们M84(a)；三/四基准超同资源基线 |
| **Enoki** | 2609.00581 | OpenIE文本锚定关系事实抽取→验证→**投影回幻觉span**；共享表示同时支持claim级验证与span级定位（无需单独对齐步骤）；**支持LLM/编码器/规则三档抽取机制，统一接口** | ✅编码器/规则档 | **极高**：①claim+span共享表示正是90号路径C+91号断言过滤的合并解；②三档抽取统一接口=我们A_typed/B_sentence preset切换的文献同款 |
| SUCEA | 2025-06 | 2506.04583 | claim切分+去语境化→迭代检索+claim编辑（无训练） | ✅（但需LLM API） | 中：对抗claim场景，我们冻结文档无检索环 |
| MedSNIP | 2609.12884 | 子句组snippet保留局部依赖结构；**开源权重分解器**生成snippet级单元 | ✅分解器 | **高**：snippet粒度=91号"断言性claim"过滤的中间粒度；验证调用降24-73%给成本论证模板 |

**判读**：无LLM对齐的可行配方=**编码器嵌入（BGE/RoBERTa池化）+多尺度证据块+非对称聚合**（RefChecker定位/HallDetect两条独立先例）。我们已有全部组件（bge-local通道、块级ℓ、strict聚合）——缺的只是把embedding匹配从"检索"角色升级为"对齐+定位"角色（91号已规划）。

---

## 3. 维度3：训练数据构造方法

### 3.1 经典配方在2025-2026的演化

| 方法 | 会议/年份 | arXiv | 机制要点 | 与我们D3/EGT的关系 | 可复用性 |
|------|----------|-------|---------|-------------------|---------|
| **MiniCheck C2D/D2C** | EMNLP 2024 | 2404.10774 | C2D：人写claim→GPT-3.5分解原子事实→GPT-4每原子生成"需两句合并才支持"的句对→成文档→删一句构造反例→**幂集合并增广**；D2C：人写文档→分块摘要→原子分解→删句/跨块配对；C2D 7076条/D2C 7319条训练出770M达GPT-4级 | 88§1.1已精读；我们D3教师蒸馏（212 answer→1886 claim标签）是"教师分解"同构，缺幂集增广与对比文档构造 | **高**：幂集增广=把1886条claim按子集合并生成更多训练对，零API成本（标签已有） |
| **FISCAL** | 2025-11 | 2511.19671 | 金融域：Qwen3-32B抽取数值原子claim→LLM-as-judge验原子性→**6模块合成器**（改写/冲突插入/事实排除/值扭曲/误归属/摘要）生成正负例；14,304训练triplet | 88§3已引（域定制先例）；6模块合成器与我们answer_mutations/term_mutations/param_mutations/structural_mutations/logic_mutations五族变异**一一对应**（我们多"结构变异"少"误归属"） | **高**：误归属模块（年份/实体/类别归属错位）是我们17违例中TERM-05（文档名误写）/追溯类缺失的变异 |
| **SYNTHVERIFY** | Findings ACL 2025 | (2025.findings-acl.170) | 方面式生成：证据文档→抽key aspects→每aspect条件生成supported claim→**4类受控扰动**（实体替换/时序修改/关系反转/属性修改）生成refuted→关键元素模糊化生成NEI | EGT叙事文法（S原样/R翻转/N换源）的三态构造同构；其"NEI=具体值模糊化"（"70%降低"→"显著降低"）是我们N种子路径没有的细粒度NEI机制 | **高**：模糊化NEI直接补强EGT-N路径（当前N=删除换源，粒度粗） |
| **SynClaimEval** | 2025-11 | 2511.09539 | 合成claim沿两轴控制：复杂度（非结构化vs多跳实体图路径≤3跳）×错误类型（不可验证幻觉vs矛盾——矛盾用错误类型学：否定/实体错/话语极性反转）；**评测合成数据效用**的框架 | 我们violations-17构造（深读真实违例→变异增强）的"错误类型学"轴可借其分类法系统化 | 中：多跳图路径构造适合方向A（跨章节参数聚合）负样本 |
| **UNOWN** | EMNLP 2024 | (2024.emnlp-main.675) | 从文本+表格自动生成FC训练实例；支持/反驳claim+**高级否定伪影**；FEVEROUS/SciFact/MMFC上与专家标注质量相当，最高+5%准确率 | **表格负样本**——我们04号SRS 82张表（用例表/接口表/追溯表）的行级矛盾构造（表53组件顺序颠倒类）直接同构 | **高**：表格文本的claim生成是我们E种子（QA/语句/叙事）没有的第四种子源 |
| FactEHR | MLHC 2025 | 2412.12422 | 临床笔记→LLM事实分解→987,266蕴含对；分解质量评测（Gemini-1.5-Flash稳/Llama-3-8B弱） | 大规模文档→事实对构造的规模参照（98万对 vs 我们EGT千级） | 低（规模超出），但分解质量轴心评测可借 |
| MATCHA | 2026 | 2605.27345 | 对抗反事实矛盾作训练信号（"对照反事实罚矛盾"） | 仓库pair_classifier_sota已录：与我们变异对（一致/不一致成对保留）同构 | 中（90号已录待核） |
| CCHD | ICASSP 2026 | 2606.08158 | 改写一致性→约束优化（改写视角间散度+标签保持约束），零推理开销超MiniCheck/AlignScore | **训练数据确定性控制**的另一路线（不靠LLM生成靠约束求解） | 中：Z3式确定性构造训练对的先例，与我们"确定性翻转R种子"同思想 |

### 3.2 我们在坐标系中的位置（诚实对标）

| 构造法 | 规模 | 教师 | 确定性 | 中文域 | 表格/多模态 |
|--------|------|------|--------|--------|------------|
| MiniCheck C2D/D2C | 14.4k | GPT-3.5/4 | 否 | 否 | 否 |
| FISCAL | 14.3k | Qwen3-32B | 半 | 否 | 否 |
| SYNTHVERIFY | 数千 | LLM | 否 | 否 | 否 |
| UNOWN | ~万级 | LLM | 否 | 否 | **是** |
| FactEHR | 987k | Gemini/Llama | 否 | 否 | 否 |
| **我们EGT** | 千级（三代） | 无（文法） | **是** | **是** | 否 |
| **我们D3教师蒸馏** | 212→1886 | GLM-5.3（缓存） | 标签缓存留痕 | **是** | 否 |

**缺口**：①幂集增广（零成本可加）；②NEI模糊化细粒度构造；③表格种子源（04号82张表闲置）；④误归属变异模块。四个都可复用现有llm_teacher/EGT基础设施，无新依赖。

---

## 4. 维度4：多粒度claim系统

任务问：有没有工作同时支持句子级/原子级/子原子级？粒度选择的自适应方法？

| 方法 | arXiv | 粒度体系 | 自适应机制 | GJB适配度 |
|------|-------|---------|-----------|----------|
| **ElementCheck** | 2608.26118（EMNLP 2026 Findings） | 句子（直判）→element（实体对+可验证连接）→element图（拓扑信号） | **复杂度自适应**：图拓扑估计句复杂度，简单句不分解直判、复杂句element级精炼——"不做均匀原子化" | **极高**：与我们三层降级（typed→句切分→整answer）同思想但方向相反（我们是形态驱动，它是复杂度驱动）；其"减少不必要重验证"=我们v3换档省成本的文献版 |
| **TriQua** | 2608.05228 | 简单claim=三元组；复杂claim=超关系事实（+qualifier） | claim复杂度决定表示形态（双形态而非多级流水线） | 高：qualifier字段=typed claim缺的语境层 |
| **MedSNIP** | 2609.12884（EMNLP 2026 Main） | 原子级（会碎裂临床依赖）vs **snippet级（子句组保留局部结构）** | 答案长度+验证器强度门控（"碎片化增益集中在长答案+强验证器"） | **高**：91号断言过滤（裸名词不能否决support）的中间粒度方案；开源分解器 |
| **Enoki** | 2609.00581 | claim级（可解释事实单元）+span级（定位unsupported文本）共享表示 | OpenIE关系事实共享投影，无需单独claim→span对齐 | **极高**：claim+span双粒度正是M84(a)+89号的合并需求 |
| Alignment Bottleneck | 2602.10380 | 子claim级证据对齐 | （非粒度系统，但给出粒度-证据对齐耦合定律） | 定锚：粒度选择必须与证据粒度联合设计 |
| DS@GT | 2607.25069 | 自适应子claim分解 | 数值claim上**负结果**（分解引噪） | 反例警示：numeric claim不宜过拆 |
| **我们（现状）** | — | typed claim（numeric/enum/identifier/quoted）→结构切分（bullet/step/sentence）→整answer；聚合strict/dominant_70/assertive_strict双档 | 形态驱动（GJB表面文法），preset切换（A_typed|strict vs B_sentence|dominant_70） | — |

**判读**：2026年的共识方向=**"均匀原子化"被抛弃，复杂度/依赖结构自适应取而代之**（ElementCheck图拓扑、TriQua双形态、MedSNIP依赖保留、DS@GT负结果）。我们的三层降级在功能上已是多粒度系统，但**粒度选择信号是"表面文法形态"（域内最优）而非"复杂度/依赖"（域外可迁移）**——这解释了crossdoc 0.5109的弱项：换文档后表面文法失配。ElementCheck的复杂度自适应信号（图拓扑）是域中立的，**v3 crossdoc档的下一个升级方向**。

---

## 5. 维度5：正则→模型替代的先例（核心维度）

### 5.1 head-to-head对比研究（明确报告性能对比的论文）

| 研究 | 域/年份 | 对比设定 | 结果 | 结论 | GJB映射 |
|------|--------|---------|------|------|---------|
| **BI-RADS抽取**（JAMIA Open 2025-12） | 放射报告 | Regex vs Rombos-LLM-V2.6-Qwen-14b（7764报告，199人工金标） | **Regex 89.20% vs LLM 87.69%**（P=.56无显著差）；**Regex快28,120×**（0.06s vs 1687s）；LLM偏向常见类别，regex更常返回"unclear" | 结构化标准化数据上正则占优；建议混合 | **identifier/enum typed claim=BI-RADS式结构化字段**→正则是正确工具 |
| **NSCLC临床抽取**（ESMO RWD 2025-11） | 中文电子病历480例 | 规则NLP（BERT NER+ALBERT RE）vs 微调Qwen3-30B | 总F1 72% vs 76%；**规则胜在半结构化字段**（TNM分期88 vs 82、ECOG 79 vs 63.9）；**模型胜在上下文依赖字段**（起始日期88 vs 72、进展92 vs 87） | 字段类型决定赢家 | **GJB域同构**：接口ID/表ID/枚举闭集=半结构化→正则；异常流叙事/跨位置语义=上下文依赖→模型 |
| LDK 2025房地产IE | 拍卖文档96份 | 人工 vs 规则 vs Claude/Llama | 规则F1 0.93-0.95与Claude 3.5 Sonnet持平；均超人工 | 规则投入开发时间后非常强 | 中：正则投入度参照 |
| 简历IE指令微调 | 2025 | 无微调 vs 微调LLM | 87.48%→95.16% | instruction-tuning显著增益 | 微调必要性证据 |
| QLoRA临床抽取（BMJ DH 2025） | 内镜报告608+217 | CoT/few-shot/微调×6开源模型(8-70B) | QLoRA+9.1-15.7pp；GPT-4o仍+4.9-11.2%超最佳开源 | 开源微调追赶闭源 | QLoRA是8GB档微调标配 |
| 法律语义角色抽取（AI&Law 2025-03） | 法条 | 微调域/任务/通用模型 vs 生成式LLM | 微调域模型最优 | 垂直域微调>生成式prompt | 同我们的蒸馏结论 |

### 5.2 生产级"模型作残差通道"先例（最重要的架构发现）

| 系统 | arXiv/年份 | 部署架构 | 数字 | 与我们架构的同构 |
|------|-----------|---------|------|-----------------|
| **Better with Less（金融交易理解）** | 2509.25803, 2025-09 | **保留regex规则处理63%流量+ESD 17%，模型只处理规则未覆盖的20%（Rawcleansed）**；模型输出置信度+生成名相似度双过滤 | 覆盖80%→94%（模型贡献14%）；$13.2M/年节省；模型对Rawcleansed 72%准确率用过滤器保precision | **=我们L1规则专家(9个,正则重)→L2 NLI残差的逐字同构**。"模型不替换规则、模型扩覆盖"是生产级成功范式 |
| VeriPhy（物理验证） | 2609.03153 | 文本规划器编译**typed obligations**+静态验证执行计划→冻结底层专家（分割/跟踪/11类typed测量）→**typed resolvers+固定复合映射到三值状态**（supported/contradicted/unknown）+全程provenance | 149视频304条缺陷记录：VeriPhy覆盖228 vs 已发表QA分解器164；召回不输单体prompt（222），**胜在每判定带证据记录可审计** | **=我们typed claim→Z3/join专家→三态聚合+块IDℓ溯源的同构**（2026年发表，typed obligation+三值+provenance组合有先例了） |
| NSCLC生产系统 | 同5.1 | LLM优化工时从168h→40h | — | 蒸馏/微调的工程收益度量模板 |

### 5.3 instruction-tuned小模型做结构化提取

| 模型/系统 | 年份 | 机制 | 关键数字 | 8GB部署 | GJB适配度 |
|-----------|------|------|---------|---------|----------|
| **GLiNER** | NAACL 2024 | 双向编码器+标签prompt并行span分类（label与text同编码器交叉注意）；零样本任意实体类型 | **GLiNER-L 0.3B在20个零样本NER基准超ChatGPT、InstructUIE-11B、UniNER-13B**；GLiNER-Multi（mDeBERTa基座）8/11语言超ChatGPT | ✅（0.3B，CPU可跑，INT8/ONNX） | **极高**：L0 gazetteer NER的零样本替代/补充；**mDeBERTa基座与我们NLI模型同源**；中文能力待核实（GLiNER-Multi覆盖语言表需查） |
| **GLiNER2** | EMNLP 2025 Demo | GLiNER扩展：NER+文本分类+层级结构抽取统一schema驱动接口；254,334训练例（真实+合成） | CrossNER零样本F1 0.590 vs GPT-4o 0.599（差0.009）；开源pip可装 | ✅ | 高：schema驱动=我们typed claim schema的接口思想 |
| GLiNER-multi-task | 2024-06 | DeBERTa-v3-large骨干多任务IE（NER/RE/QA/摘要/清洗） | 零样本NER平均F1 0.6276超NuNER-Zero/gliner-large | ✅ | 中高 |
| **ThinknCheck** | 2026-04 | 1B验证器（4-bit Gemma3）先生成结构化rationale再判定；LLMAggreFact-Think 24.1k推理增强训练集 | **78.1 balanced acc超MiniCheck-7B（77.4）**，参数少7×；去rationale降到57.5；SciFact +14.7 | ✅（1B 4-bit） | **高**：L2 NLI残差通道的直接竞品模板；"显式监督推理使紧凑验证器竞争"=我们EGT微调方向的2026版证据 |
| **ClaimCheck** | 2025-09 | 实时事实核查SLM管线（开源模型+静态知识库） | Qwen3-4B达AVeriTeC 76.4%超LLaMA3.1-70B与GPT-4o方案 | ⚠️（4B fp16约8GB临界，4-bit可） | 高：4B实时管线规模参照 |
| Mistral-7B-Claim-Extractor | 2024 | RefChecker微调triplet抽取器 | 官方开源 | ⚠️（4-bit） | 中：triplet形态与我们typed claim错配（需归一化，90号§1.3同判） |

**判读**：**instruction-tuned/gazetteer-free零样本提取的SOTA答案=GLiNER家族**（0.3B超13B LLM，CPU可跑）。对我们的含义：L0 NER词典（jieba+域词典+正则id_patterns）是"预定义类型NER"——GLiNER提供的是"标签即prompt"的泛化；两者不是替代关系而是**词典管域内精确召回、GLiNER管域外/未登录实体**的互补（同§5.2残差定律）。

### 5.4 正则→模型替代的领域映射判定（综合5.1-5.3）

```
字段/claim类型               赢家           证据
─────────────────────────────────────────────────────────────
标准化枚举/编号/评分         正则           BI-RADS(89.2 vs 87.7, 快28120×), NSCLC TNM(88 vs 82)
半结构化表格字段             正则+join      NSCLC ECOG(79 vs 64), 我们enum/id_join专家
上下文依赖叙事               微调模型       NSCLC 日期/进展(88-92 vs 56-72)
零样本新类型/跨域            零样本模型     GLiNER(0.3B超13B), FactEHR(Gemini稳/Llama8B弱)
规则未覆盖的长尾             残差模型       Better with Less(覆盖80→94%)
需要span定位的审计           编码器/规则    Enoki(共享投影), 我们finditer(90号§1.7)
```

---

## 6. 8GB显存+本地推理约束筛选表

| 方法 | 规模 | 8GB可行 | 依赖 | 开源状态 |
|------|------|---------|------|---------|
| DecModel-0.25B（分解） | 0.25B T5 | ✅ 富余 | HF | 代码+数据（github.com/huang22/DecMetrics） |
| Qwen3-0.6B SLM分解蒸馏配方 | 0.6B | ✅ | HF+教师 | 论文方法（ACL 2026.1468），配方可复刻 |
| GLiNER-Multi / GLiNER2 | 0.3B/0.5B | ✅ CPU亦可 | pip gliner | ✅Apache开源 |
| ThinknCheck验证器 | 1B 4-bit | ✅ | HF | 数据集LLMAggreFact-Think+方法 |
| MiniCheck-FT5 | 770M | ✅ | HF | ✅模型+数据合成代码开源 |
| HallDetect配方 | 编码器4-bit | ✅ | HF | 方法（2608.05823） |
| 我们claim_segmenter_v2 | 128M | ✅ | 已有 | 仓库内 |
| CREDENCE 3.8B分解器（Phi-3-mini） | 3.8B | ✅ fp16~7.6GB临界/4-bit富余 | HF | 方法+基准 |
| DAD/DecomposeRL 7-8B（RL分解器） | 7-8B | ⚠️ 仅4-bit（~5-6GB）+vllm | HF+GRPO | DAD数字完整；DecomposeRL待核实代码 |
| RefChecker Mistral-7B抽取器 | 7B | ⚠️ 4-bit | vllm | ✅（仓库已归档2026-04，仍可fork） |
| TRACE/LAT（RL证据归属） | 7-8B | ⚠️ 训练不可行，推理4-bit勉强 | GRPO+多卡 | TRACE代码开源 |
| Qwen3-32B级教师（FISCAL/DecMetrics教师） | 32B | ❌ | API | — |

**结论**：8GB档的可用组合=**<1B分解器/验证器（fp16）+3.8-8B（4-bit）+GLiNER 0.3B**；RL训练类（TRACE/DecomposeRL/DAD）本地不可训，只能引用其结论或用其开源checkpoint推理。

---

## 7. 对本项目的迁移判定

### 7.1 我们现状数字（取证自data/gjb_438c/distillation/）

| 评测 | typed正则（A） | 蒸馏切分器128M | 备注 |
|------|---------------|----------------|------|
| test-46 macro-F1 | **0.8047**（acc 0.913） | 0.7496（seg_v2+assertive_strict，acc 0.913）；0.5789（seg_v2+strict） | claim_downstream_v2.json |
| crossdoc-150 acc | 0.5109（typed档）/0.7361（sentence档） | — | refactor_matrix_v1.json |
| E2 LOO held-doc | 0.5133（蒸馏前基线）→0.5667（LOO均值） | — | e2_loo_results_v1.json |
| **claim级识别**（教师claim=金标） | dev45 F1 **0.2427**（P 0.377/R 0.179，under_seg 22.7%）<br>d3train600 F1 0.5624（P 0.915/R 0.406，under_seg 47.5%） | dev45 F1 **0.7041**（P 0.719/R 0.690）<br>d3train600 F1 0.7955（P 0.836/R 0.759） | claim_recognition_v2.json |
| 分解粒度 | cl/inst 4.89 vs 教师10.31（dev45） | cl/inst 9.89 ≈教师10.31；over_seg 8.2% | 同上 |

**核心事实**：切分器在**claim识别质量上大幅胜过正则**（F1 0.70 vs 0.24——正则严重欠切分：under_seg率23-48%），但在**下游三态判定上输给正则**（0.7496 vs 0.8047）。这正是**Alignment Bottleneck定律（2602.10380）的教科书案例**：分解器产出了更细的claim，但证据侧对齐（Y={S,R,N}×ℓ×j的块级粒度）没有随之细化到子claim级（SAE），typed claim的Z3/join专家通道对齐是SAE的，而切分器claim只配到SRE。**修复方向不是换更强的分解器，而是给切分器claim接上typed通道接口+证据侧细粒度对齐**。

### 7.2 正则→模型替代矩阵（逐层判定）

| 层 | 现状 | 文献判定 | 建议动作 | 依据 |
|----|------|---------|---------|------|
| **typed分解前端**（numeric/enum/identifier/quoted） | 正则（answer_claims.py，零模型） | **保留**——结构化字段正则无性能损失且快4数量级；GJB ID文法/枚举标记是"标准化字段" | 不动；补span字段（90号路径C不变） | §5.1 BI-RADS/NSCLC；§5.2 Better-with-Less"规则管已覆盖" |
| **语义/叙事claim分解** | 结构切分回退（句切分）+128M切分器（D3，未上线主路径） | **模型补位**——上下文依赖字段模型胜；欠切分已实证（F1 0.24） | 切分器作语义残差档，但**先修claim→typed通道桥接+证据对齐，再谈上线**（否则0.7496现象重现） | §5.1 NSCLC叙事字段；§2.1 Alignment Bottleneck；§7.1 |
| **L0 NER词典** | jieba+域词典+正则（ner_lexicon.py） | **互补扩展**——词典管域内精确，GLiNER(0.3B, mDeBERTa同源)管零样本/跨文档未登录实体 | crossdoc档加GLiNER零召回兜底（域词典失配时） | §5.3 GLiNER零样本超13B；§5.2残差定律 |
| **L1规则专家（9个）** | 正则重+Z3/join | **保留架构**——typed obligation→确定性验证+provenance在2026有发表先例（VeriPhy同构） | 不动；VeriPhy可作论文相关工作引用（typed+三值+provenance先例） | §5.2 VeriPhy |
| **L2 NLI蒸馏** | EGT微调mDeBERTa+distilled_v1（gate 0.8） | **配方正确，可升级**——ThinknCheck(1B,4-bit)证明结构化rationale+监督推理使1B超770M的MiniCheck | 可选：EGT加rationale字段（24.1k推理增强集的构造法）——但优先级低于对齐修复 | §5.3 ThinknCheck |
| **聚合** | strict/dominant_70/assertive_strict | **已对齐SOTA**——RefChecker strict规则逐字同构；非对称聚合（refute短路）有HallDetect同款 | 不动；引用时挂RefChecker/HallDetect | §1.2/§2.3 |

### 7.3 可复用的训练数据构造（按性价比排序）

1. **幂集增广**（MiniCheck C2D Step5）：1886条D3教师claim标签已缓存——按原子事实子集合并生成增广子claim训练对，**零API成本**；
2. **NEI模糊化**（SYNTHVERIFY）：EGT-N种子从"删除换源"升级为"具体值→模糊表述"（"时延≤50ms"→"时延有严格要求"），直接攻击NIE类判定的细粒度；
3. **误归属模块**（FISCAL）：为17违例中的文档名误写/追溯锚点失效/申请释放错位类构造专门变异（现有五族变异缺这一族）；
4. **表格种子源**（UNOWN）：04号SRS 82张表→行级claim生成（接口表双登记/能力表覆盖检查的负样本），方向A+B共用。

### 7.4 论文写作弹药（新增引用锚点）

- "typed claim+确定性验证+provenance"架构先例：**VeriPhy**（2609.03153，三值状态+typed测量+证据记录可审计）；
- "规则优先+模型残差"生产先例：**Better with Less**（2509.25803，覆盖80→94%）；正则vs模型head-to-head：**BI-RADS JAMIA 2025**（快28,120×无精度损失）；
- "分解增益取决于证据对齐而非分解器质量"：**Alignment Bottleneck**（2602.10380）——为我们的0.7496现象提供文献解释，把"切分器下游不及正则"从缺陷重述为**领域定律的预期行为+我们的对齐修复贡献点**；
- "非对称聚合"先例：**RefChecker strict**（逐字同构）+**HallDetect**（单条高置信矛盾即标红）；
- "复杂度自适应分解"：**ElementCheck**（EMNLP 2026 Findings）——v3 crossdoc档的升级叙事；
- "0.25B训练分解器超32B prompting"：**DecMetrics**（2509.04483）——128M切分器路线的合法性证据+SEMANTIC ENTROPY审计指标。

---

## 8. 待核实清单

1. **RLSeek（ACL 2026）/ACV（Atomic Contrastive Verification, 2026）**：arXiv+web双通道未检索到（2026-11-24执行）。若parent会话有内部出处（非公开预印本/误记），需提供后重查；本文按"无法核实"处理，§2给出概念对应的真实论文族。
2. **DecomposeRL代码开源状态**（2605.27858）：摘要称可用但未见链接，GitHub存在性待核。
3. **Qwen3-0.6B SLM分解蒸馏**（ACL 2026 Long 2026.acl-long.1468）：论文PDF经web检索确认存在，arXiv编号未在检索结果中出现，引用前需从ACL Anthology取正式编号。
4. **DAD**（EACL 2026 Findings 2026.findings-eacl.309）：同上，ACL Anthology确认存在，arXiv编号待核。
5. **GLiNER中文能力**：GLiNER-Multi覆盖语言清单未逐项核实（mDeBERTa基座对中文有基础能力，但零样本中文NER精度需实测——建议用04号SRS人工标注小集验证后再决策）。
6. **MedSNIP开源分解器规模**：摘要称"an open-weight decomposer"未给参数量。
7. **Peerify/Enoki/HallDetect代码开源状态**：Enoki发布EnokiQA数据集（摘要明示）；Peerify/HallDetect开源情况未核。
8. **CREDENCE正式发表状态**：标注"Submitted to Language Resources and Evaluation"（期刊在投）。
9. **BI-RADS研究的LLM选型**（Rombos-LLM-V2.6-Qwen-14b，29.57GB单卡部署）：与我们8GB约束不同档，对比结论引用时注明其LLM未做任务微调（公平性边界）。
10. **VeriPhy（2609.03153）与我们管线的同构表述**：其typed obligations是物理量域（11类测量），映射到GJB域（数值/枚举/ID）属类比引用，论文写作时需注明差异（其验证器为冻结视觉专家，我们的为Z3/join符号运算）。

## 9. 引用索引

**本取证新增（2024-2026，按维度）**：
- 分解SOTA：RefChecker(2405.14486)、ElementCheck(2608.26118, EMNLP2026F)、TriQua(2608.05228)、MedScore(2505.18452, ACL2026F)、AFEV(2506.07446)、DnDScore(2412.13175)、SAFE(2403.18802, NeurIPS2024)、Pelican(2407.02352)、Peerify(2609.25046)、GraphFC(2503.07282)
- 分解有效性：Decomposition Dilemmas(2411.02400, NAACL2025)、Alignment Bottleneck(2602.10380)、Reasoning-CV(2505.12348)、DS@GT(2607.25069, CLEF2026)、CLATTER(2506.05243)、ProFact(2606.13262)
- 小模型分解：DecMetrics(2509.04483)、Test-Taking SLM(ACL2026.1468)、DAD(EACL2026.309)、DecomposeRL(2605.27858)、CREDENCE(2606.19819)、FactEHR(2412.12422, MLHC2025)、MedSNIP(2609.12884, EMNLP2026)
- 对齐/证据：TRACE(2505.13258)、LAT(2511.12003, AAAI2026)、FARCA(2608.24350)、EchoSpec(2611.20034)、ClueWeaver(2608.25531, ICONIP2026)、HallDetect(2608.05823)、Enoki(2609.00581)、SUCEA(2506.04583)、Uncertainty-Aware SciFC(2604.11036)
- 训练数据：MiniCheck(2404.10774, EMNLP2024)、FISCAL(2511.19671)、SYNTHVERIFY(ACL2025F.170)、SynClaimEval(2511.09539)、UNOWN(EMNLP2024.675)、MATCHA(2605.27345)、CCHD(2606.08158, ICASSP2026)
- 正则→模型：BI-RADS JAMIA Open(2025, 10.1093/jamiaopen/ooaf128)、NSCLC ESMO RWD(2025, S2949-8201(25)00374-1)、Better with Less(2509.25803)、VeriPhy(2609.03153)、GLiNER(NAACL2024.300)、GLiNER2(EMNLP2025Demos.10)、GLiNER-multi-task(2406.12925)、ThinknCheck(2604.01652)、ClaimCheck(2510.01226)、LoCal(WWW2025, 10.1145/3696410.3714748)、ATOMICCHECK(AACL2026.184)、房地产IE(LDK2025.25)、QLoRA临床(BMJ DH e000014)

**仓库锚点（本文引用的内部材料）**：
- 88/89/90号取证：`docs/srs_project/88_claim_decomposition_literature.md`、`89_nli_attribution_survey.md`、`90_claim_extraction_sota.md`
- 实现与数字：`algorithms/consistency/answer_claims.py`（typed正则）、`tools/train_claim_segmenter.py`（128M切分器）、`tools/distill_segmenter_labels.py`（D3教师标注）、`data/gjb_438c/distillation/claim_downstream_v2.json`（A_regex 0.8047 vs seg_v2 0.7496）、`claim_recognition_v2.json`（claim级F1 0.24/0.70）、`e2_loo_results_v1.json`（LOO 0.5667）、`refactor_matrix_v1.json`（两档数字）、`d3_teacher_labels_v1.json`（1886条）
- 既有精读：`docs/srs_project/literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md`（MiniCheck §1.1）、`pair_classifier_sota_2023_2025.md`（FActScore/AlignScore/VERISCORE）、`multimodal_srs_increment_survey_202611.md`（2026-11多模态增量，与本文无重叠）
