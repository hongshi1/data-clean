# Pair级一致性二分类(中文SRS)的2023-2025 SOTA方法调研

> 调研日期: 2026-10-09
> 任务定位: pair级二分类(premise/hypothesis → consistent/inconsistent), 中文GJB SRS域, 8GB GPU
> 选入标准: ①2023-2025发表 ②是"方法"而非数据集 ③适合pair分类 ④8GB可复现或可迁移
> 与已有调研关系: RE侧竞品全景见 `nlp4re_llm4re_comprehensive_survey.md` 与 `master_survey_inconsistency_detection.md`(已覆盖TSRCDF-SS/LegalWiz/ContractCheck/LEREDD等); 本文聚焦**方法侧**(核验器训练范式/NLI新方法/高效微调/中文backbone), 为pair分类器的选型与改进提供依据
> 引用核验: 标注【√API】= 本轮arXiv API逐条核验(ID+作者+摘要); 【√项目】= 项目既有调研已核验(DBLP/Crossref); 未标注=训练知识截止2025年中, ID未二次核验

---

## 〇、执行摘要

1. **2023-2025的核心范式转移**: "微调判别器"没有被淘汰, 但配方变了——**LLM不再当判别器, 而是当数据生成器/标注器/rationale供给者; 判别由小模型(0.3B-3B)承担**。MiniCheck/AlignScore/DSS/FreeAL四条独立证据链均指向同一结论。
2. **LoRA族2024年完成"逼近全参微调"的最后一块拼图**: DoRA(幅度/方向解耦)+rsLoRA(√r缩放)+PiSSA/LoRA-GA(SVD/梯度对齐初始化), 在peft中均为一行开关, 8GB GPU上Qwen2.5-1.5B/3B(4bit)全谱可行。
3. **RE域2023-2025没有新的需求矛盾检测方法**(TSRCDF-SS是唯一直接竞品且为句对纯文本); 方法学供给来自邻域: 事实核验(MiniCheck)、蒸馏(DSS)、弱监督(FreeAL)——迁移空间属于我们。
4. **中文pair分类器的最佳backbone = Qwen2.5/Qwen3小尺寸 + DoRA/QLoRA**; 中文NLI方法学2023-2025无新工作(数据集OCNLI/CMNLI均为2020年前), 这本身是发表空白。
5. **提示工程vs微调的最新结论(交叉证据)**: 通用域NLI上零样本大LLM不弱(Zhong 2023: ChatGPT在GLUE推理任务上大幅超BERT); 但领域文档上系统性崩溃(NLI4CT: 6个SOTA NLI模型max F1=0.627; RE域: ChatGPT/Gemini分类0.78 vs SOTA 0.96)——**领域pair分类必须微调, LLM做teacher**。

---

## 方向A: 2023-2025事实核验/矛盾检测

### A1. MiniCheck(已有模型, 配方是复现重点)
- **引用**: Tang, Laban, Durrett. "MiniCheck: Efficient Fact-Checking of LLMs on Grounding Documents." EMNLP 2024, arXiv:2404.10774【√API】
- **核心机制**: GPT-4按结构化流程生成含真实错误模式的合成claim-document对(35K), 与真实LLM输出错误数据混合, 训练小验证器(RoBERTa-large 355M / FLAN-T5 770M)。770M模型达到GPT-4精度、400x低成本; 关键实证: GPT-4零样本在合成数据上近乎完美, 在真实LLM错误上明显退化→必须"合成+真实"混合训练。
- **复现方案(pair数据)**: ①数据层: 我们的48变异算子=**确定性claim生成器**(替代其GPT-4自由生成), 真实锚点差异对=其"real claims"角色, 按MiniCheck比例混合; ②模型层: mDeBERTa-v3-base(已本地)或chinese-roberta-wwm-ext全参微调, premise/hypothesis拼接二分类; ③评测层: 沿用pair_dataset_canonical的test split, 加锚遮蔽协议(训练于变异、测试于真实锚点对=MiniCheck的"合成→真实迁移"实验的领域版); ④走runs协议(tools/run_utils.py)。
- **预期效果**: vs 标准微调(仅真实对): 合成注入缓解小数据过拟合(MiniCheck同款发现); vs 仅合成: 真实混合防止分布漂移。估计+3~8pp macro-F1(参照MiniCheck合成数据带来的增益幅度)。
- **8GB**: ✅ 355M级编码器全参微调绰绰有余; 770M FLAN-T5也可。
- **定位**: 我们已有MiniCheck模型; **可复现的是其数据配方**——且我们的确定性生成器严格优于其LLM生成(Korn 2026证明LLM生成缺陷不可靠, 见【√项目】)。

### A2. AlignScore
- **引用**: Zha, Yang, Li, Hu. "AlignScore: Evaluating Factual Consistency with a Unified Alignment Function." ACL 2023, arXiv:2305.16739【√API】
- **核心机制**: 把7种skill(NLI/QA/复述/事实验证/IR/STS/摘要)统一为"信息对齐"二分类, LLM构造4.7M训练例, 训练RoBERTa-large(355M)。355M匹配或超过ChatGPT/GPT-4式指标; 22个评测集(19个训练未见)上稳定占优。
- **复现方案(pair数据)**: ①构造中文GJB版多skill数据: 我们已有的信号天然对应skill族——参数值比对(事实验证skill)、同义术语(复述skill)、句对矛盾(NLI skill)、表-文对应(IR/QA skill); ②用GLM API(cache=True)按AlignScore式流程造对齐/非对齐例; ③mDeBERTa多skill联合训练→单一对齐打分器; ④消融: 单skill vs 多skill, 看良性差异识别是否改善(假设: 复述skill教会"语义等价但表述不同"→直接攻击我们的P4良性差异问题)。
- **预期效果**: vs 单任务微调: 未见分布上更稳(论文19/22未见集占优); 对我们, 重点是**良性差异误报率下降**(待实验验证)。
- **8GB**: ✅(355M backbone)。
- **佐证**: AlignRuScore(Zimin et al., 2025-12, arXiv:2512.06586【√API】)已示范"AlignScore移植到另一语言(俄语)可行"——中文GJB版移植同理, 但**无人做过**。

### A3. FActScore(分解式, 服务文档级/条目级检测)
- **引用**: Min et al. "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation." EMNLP 2023, arXiv:2305.14251【√API】
- **核心机制**: 把长文本分解为原子事实, 逐条对照知识库核验, 输出"被支持原子事实比例"。ChatGPT传记仅58%原子事实被支持。
- **复现方案**: ①聚合条目(方向A上下文关联的输出)→GLM API原子化为属性陈述("X的Y=Z"); ②每条原子陈述 vs 条目context(表/图/正文)过我们微调的pair分类器(A1产物); ③聚合为条目级分数+定位到具体不一致原子。这是**pair分类器走向文档级的使用方式**, 不是竞争者。
- **预期效果**: 比整段判更细粒度, 可定位证据(与ACDD证据链需求对齐)。
- **8GB**: ✅(分解走API缓存, 核验走本地小模型)。

### A4. VERISCORE
- **引用**: Song, Kim, Iyyer. "VERISCORE: Evaluating the factuality of verifiable claims in long-form text generation." 2024, arXiv:2406.19276【√API】
- **核心机制**: 区分可验证/不可验证claim, 只对可验证部分打分; 开源微调实现可用。相对FActScore多了"可核验性"维度。
- **复现方案/迁移**: 与FActScore同路; 其"不可验证claim弃权"思想直接呼应我们的证据核验机制(pair_dataset v2.1: 19.4%声称被context反驳→隔离)。在条目级管线中, 不可核验原子→进弃权带而非强行判定。
- **预期效果**: 弃权带换precision(与共形弃权框架一致); 对我们, 是**弃权协议的邻域先例引用**。
- **8GB**: ✅。

### A5. SelfCheckGPT(采样一致性→不确定性信号)
- **引用**: Manakul, Liusie, Gales. "SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models." EMNLP 2023, arXiv:2303.08896【√API】
- **核心机制**: 黑箱LLM多次随机采样, 事实正确→采样间一致, 幻觉→采样间矛盾; 用NLI/一致性度量打分, 零资源检测幻觉。
- **复现方案**: 不用于判label, 用于**校准/弃权特征**: 对每个pair, GLM判定5~10次(T=0.7), 采样间NLI互判(用本地mDeBERTa)得分歧度→作为该pair判定的不确定性特征, 接入ACDD的ε通道(感知噪声); 全程走llm_client cache=True。
- **预期效果**: 不提升 Accuracy, 提升 **AUROC/校准**(分歧度=噪声观测)——正是我们ECE实验(未校准0.577→校准0.943)证明值钱的那个量。
- **8GB**: ✅(N互判在本地; API成本走缓存, 一次性)。

### A6. CoVe(验证链, 零训练LLM管线)
- **引用**: Dhuliawala et al. "Chain-of-Verification Reduces Hallucination in Large Language Models." 2023, arXiv:2309.11495【√API】(Meta)
- **核心机制**: 草案→模型自主规划验证问题→**独立**(隔离上下文)回答→综合终答; 消除回答间相互偏见。
- **复现方案**: GLM对pair初判→生成验证问题("两侧的X值分别是? 单位是否同族?")→独立通道(仅给单侧context)回答→裁决。作为**零训练对照基线**(F5族的规范化实现), 与微调小模型对比。
- **预期效果**: vs 单步prompt: 精确率提升(论文多任务减幻觉); vs 微调小模型: 预计仍落后(S3CDA域退化证据), 但提供"LLM尽力而为"的上界对照。
- **8GB**: ✅(纯API+缓存)。

> 检索确认: 2024-2025没有出现MiniCheck之外的**通用专用矛盾检测器**新工作; 后续增量在分解式(FActScore/VERISCORE)与agentic(SAFE类, 依赖外部检索, 不适用"文档即证据"场景, 未列)。2026年出现MATCHA(对抗反事实矛盾作训练信号, arXiv:2605.27345【√API, 超窗仅作注】)——其"对照反事实罚矛盾"思想与我们变异对(一致/不一致成对保留)高度同构, 可作未来训练目标设计参考。

---

## 方向B: 2023-2025 NLI新方法

### B1. "LLM造数据+小验证器"范式(MiniCheck配方, 见A1)
超越标准微调的不是新损失函数, 是**数据配方**(合成错误注入+真实混合)。这是2023-2025 NLI/事实核验最大范式变化: NLI训练数据从人工标注语料转向LLM/规则生成的受控错误对。

### B2. Distilling Step-by-Step(rationale多任务蒸馏)
- **引用**: Hsieh et al. "Distilling Step-by-Step! Outperforming Larger Language Models with Less Training Data and Smaller Model Sizes." Findings of ACL 2023, arXiv:2305.02301【√API】(Google)
- **核心机制**: LLM生成的rationale(判定理由)作为额外监督, 小模型以多任务框架同时学"任务标签"+"rationale生成"。770M T5以80%数据超过few-shot 540B PaLM; 同数据量下优于标准微调与标准蒸馏。
- **复现方案(pair数据)**: ①GLM API为train split每条pair生成判定rationale(为什么矛盾/一致, 指出冲突参数; cache=True一次性成本); ②mDeBERTa或Qwen-0.5B双头: label头 + rationale摘要头(把rationale压成模板化理由序列); ③λ加权多任务损失; ④消融: 标准微调 vs +rationale多任务; ⑤测试集只走label头。
- **预期效果**: 小数据(我们1~2K pair量级)下最大杠杆, 论文报告同等数据下显著优于标准微调, 估计+2~5pp; 额外收益: rationale头输出=天然解释链。
- **8GB**: ✅。

### B3. FreeAL(LLM标注+SLM过滤的免人协同训练)
- **引用**: Xiao et al. "FreeAL: Towards Human-Free Active Learning in the Era of Large Language Models." EMNLP 2023 Main, arXiv:2311.15614【√API】
- **核心机制**: LLM零样本粗标注→SLM以对比学习从粗标注蒸馏→SLM筛选高质量样本反馈LLM做label精化→迭代。8个基准上同时提升SLM与LLM, 全程无人工。
- **复现方案(pair数据)**: ①GLM+kimi对未标注候选pair(方向A聚合产物)双LLM零样本标注; ②mDeBERTa对比学习训练; ③高置信+双LLM一致样本反哺prompt再标注; ④**分歧样本=active选择信号**(直接对应我们160条uncertain弃权带); ⑤收敛后与金标准test对比。
- **预期效果**: 零人工成本下接近少量标注微调(论文: 8数据集平均大幅超LLM零样本和SLM零样本); 对我们的价值=**标注预算的放大器**(把22条gold→数万弱标注)。
- **8GB**: ✅。

### B4. NLI4CT + DFKI-NLP(领域NLI竞赛的方法学)
- **引用**: ①Jullien et al. "NLI4CT: Multi-Evidence Natural Language Inference for Clinical Trial Reports." EMNLP 2023, arXiv:2305.03598【√API】(SemEval-2024 Task 2数据任务); ②Verma & Raithel. "DFKI-NLP at SemEval-2024 Task 2: Towards Robust LLMs Using Data Perturbations and MinMax Training." 2024, arXiv:2405.00321【√API】
- **核心机制**: ①NLI4CT: 临床试验报告多证据NLI, 6个SOTA NLI模型max F1=0.627——**通用NLI在领域结构化文档上崩溃的定量证据**; ②DFKI系统: Mistral + **数值/缩写扰动数据增强** + MinMax损失, 专攻数值矛盾与语义改变干预的鲁棒性。
- **复现方案(pair数据)**: DFKI配方我们**天然半具备**: 48变异算子中PARAM-02(数值)/TERM-03(术语)=其数值/缩写扰动的领域版。补两个实验: ①扰动混合比消融(0/25/50/100%变异增强); ②MinMax损失 vs CE vs Focal(TSRCDF-SS用Focal变体)。在test(真实锚点对)上看鲁棒性转移。
- **预期效果**: 数值类矛盾(PARAM)检测鲁棒性提升; 消融本身是论文素材。
- **8GB**: ✅(Mistral-7B 4bit可用, 但建议直接Qwen同尺寸)。
- **额外价值**: NLI4CT的F1=0.627是我们论证"通用NLI(Erlangshen零样本)不够、必须领域适配"的**同构邻域证据**。

### B5. 提示工程 vs 微调: 2023-2025结论(交叉证据表)

| 证据 | 设置 | 结论 |
|---|---|---|
| Zhong, Ding, Liu, Du, Tao. "Can ChatGPT Understand Too?" 2023, arXiv:2302.10198【√API】 | ChatGPT vs 4个微调BERT, GLUE | **通用域推理任务上ChatGPT大幅超过BERT**; 复述/相似任务落后 |
| El-Hajjami, Fafin, Salinesi. "Which AI Technique Is Better to Classify Requirements?" 2023, arXiv:2311.11547【√API】 | SVM/LSTM/ChatGPT(gpt-3.5/4, zero+few-shot), 5个需求数据集 | 无单一赢家; few-shot仅在zero-shot失败场景有益 |
| Saleem et al. 2024, arXiv:2412.00959【√API】 | ChatGPT/Gemini vs 任务特定SOTA, 4个RE基准 | 分类0.78 vs 0.96; NER 0.36/0.25 vs 0.92; 仅QA打平(0.91 vs 0.90) |
| MiniCheck(EMNLP 2024) | GPT-4零样本 vs 355M微调验证器, 真实LLM错误 | GPT-4在真实错误上退化, 355M微调后达到GPT-4水平 |
| NLI4CT(EMNLP 2023) | 6个SOTA NLI模型, 临床试验报告 | max F1=0.627, 领域文档上崩溃 |
| S3CDA(2022, 超窗仅作证据) | GPT-4o, 航空需求 | 0.936→0.462域退化【√项目】 |

**综合结论**: 零样本LLM在**通用域**NLI已强(Zhong), 但在**领域文档+领域术语+受控表面形态**(我们的场景三占全)上系统性落后于微调小模型。**微调是必选项; LLM的最优角色=数据生成/标注/rationale供给(见B1-B3)**。这也是我们prompt通道只配做"参照系+仲裁"的文献依据。

### B6. (次要)LLM2Vec
- BehnamGhader et al. "LLM2Vec: Large Language Models as Secret Text Encoders." COLM 2024, arXiv:2404.05961(未二次核验)。decoder→encoder双向化+无监督适配; 对我们BGE通道(召回)的升级选项, 非pair判别主战场。一行带过, 不进Top-5。

---

## 方向C: 2023-2025需求工程+LLM(方法)

### C1. TSRCDF-SS(唯一直接竞品, 必须复现的基线)
- **引用**: Wang, Jiang, Bai, Zou, Xue, Zhang, Luan. "A transfer learning approach for automatic conflicts detection in software requirement sentence pairs based on dual encoders." 2025, arXiv:2511.23007【√API】
- **核心机制**: SBERT+SimCSE**双独立编码器**→六元拼接(embedding及交互)→2层FFNN; 混合损失=Focal变体(类失衡)+域约束+置信惩罚; 序列迁移+跨域迁移两段式。域内macro/weighted-F1 +10.4%, 跨域macro-F1 +11.4%。
- **复现方案(pair数据)**: ①编码器换中文: bge-large-zh(已本地)+SimCSE版中文编码器; ②六元拼接+FFNN头(忠实复刻); ③Focal变体+置信惩罚损失; ④"跨域迁移"映射为我们的**跨场景迁移**(sc1→sc5、文档间leave-one-out)——这是我们数据协议独有的评测维度; ⑤与DoRA版Qwen分类器、mDeBERTa全参微调对比。
- **预期效果**: 作为RE SOTA基线, 预期在真实GJB对上不如在其自建数据上(合成偏差); **它的双编码器无context输入**, 对多模态条目对天然吃亏——这正是我们的超越面。
- **8GB**: ✅(编码器推理+轻头, 训练成本极低)。

### C2. RE域LLM分类实证(两条已核验证据, 见B5表)
El-Hajjami 2023【√API】与Saleem 2024【√API】: 需求分类/抽取/NER上零样本ChatGPT/Gemini系统性落后任务特定模型(0.78 vs 0.96; NER 0.36 vs 0.92)。Ezzini等ICSE 2023(NIER)的ChatGPT/BERT需求分类初评为同一线【√项目】。→ RE域"LLM判别器不可靠"与B5结论交叉锁定。

### C3. ChatGPT判需求不一致的首次正式评测
- Fantechi, Gnesi, Passaro, Semini, RE 2023, pp.335-340【√项目】。ChatGPT直接判NL需求不一致: **可行但不可靠**。其prompt协议可作我们GLM零样本通道的协议模板(对照组)。2025延续线(RE@Next, 规则聚类+LLM混合, 注入式不一致)同样停在纯文本【√项目】。
- **8GB**: ✅(API)。

### C4. 结论: RE 2024-2025矛盾检测方法供给=空
LLM4RE SLR(Zadenoori et al. 2025, arXiv:2509.11446【√项目】): 74篇中缺陷检测跌至第8位(~5%), 90%闭源API, 16%公开数据。NLP4RE 2024/2025无新矛盾检测方法论文; 2025年仅TSRCDF-SS(arXiv)与RE@Next注入式研究; LEREDD(2602.22456)/QUARE(2603.11890)均为2026且非矛盾检测【√项目】。**→ 我们的方法改进空间在RE域无竞争者, 供给全部来自邻域(A/B/D方向)迁移。**

---

## 方向D: 2023-2025高效微调

### 总表(按采用优先级)

| 方法 | 引用 | 核心机制(一句) | vs LoRA增益 | 8GB |
|---|---|---|---|---|
| **DoRA** | Liu et al., ICML 2024 Oral, arXiv:2402.09353【√API】 | 权重分解为幅度+方向, LoRA只更新方向, 幅度单独可学习 | LLaMA/LLaVA/VL-BART全线超LoRA; 逼近全参微调 | ✅ peft: use_dora=True |
| **rsLoRA** | Kalajdzievski, 2023, arXiv:2312.03732【√API】 | α/r→α/√r缩放修正高rank学习衰减 | 高rank(r≥32)下+1~2pp, 解锁更高rank | ✅ 一行配置 |
| **PiSSA** | Meng, Wang, Zhang, NeurIPS 2024 spotlight, arXiv:2404.02948【√API】 | W的SVD主成分初始化A/B, 残差冻结; QPiSSA量化误差更小 | GSM8K: Mistral-7B 72.86 vs LoRA 67.7; LLaMA3-70B QPiSSA 86.05 vs QLoRA 81.73 | ✅ peft内置, 初始化仅数秒 |
| **LoRA-GA** | Wang, Yu, Li, ICLR 2025, arXiv:2407.05000【√API】 | 初始化对齐全参微调第一步梯度 | T5-Base GLUE平均+5.69%; 收敛加速2-4x | ✅ |
| **QLoRA** | Dettmers et al., NeurIPS 2023, arXiv:2305.14314【√API】 | 4bit NF4+双重量化+分页优化器 | 内存↓使7B 4bit入8GB | ✅ 基础设施 |
| **LoRA+** | Hayou, Ghosh, Yu, ICML 2024, arXiv:2402.12354【√API】 | A/B不同学习率 | +1~2%, 训练加速至2x | ✅ 一行 |
| **VeRA** | Kopiczko et al., ICLR 2024, arXiv:2310.11454【√API】 | 全层共享冻结随机A/B+可学习缩放向量 | 参数再减10x, 性能持平 | ✅(多场景部署时才需要) |
| **NEFTune** | Jain et al., ICLR 2024, arXiv:2310.05914【√API】 | embedding加噪 | 指令微调对话评测+8~35%(分类任务未验证, 需小实验) | ✅ 一行 |

### 关键实证: LoRA vs 全参微调
- Biderman et al. "LoRA Learns Less and Forgets Less." TMLR 2024(Featured Certification), arXiv:2405.09673【√API】: 代码/数学域LoRA明显弱于全参微调(学习少), 但**遗忘也少**; 全参微调的扰动秩是典型LoRA配置的10-100x。
- **对我们的含义**: pair二分类是"窄任务+防遗忘(中文通用能力)"场景——恰好是LoRA/DoRA的友好区; 且DoRA/PiSSA/LoRA-GA正是为填补"学习少"缺口而生, 三者报告均达或近全参微调水平。**Qwen2.5-1.5B/3B + 4bit QLoRA + DoRA + rsLoRA = 8GB上的推荐配方**。

### "小模型胜大模型"的系统实证(2023-2025)
1. MiniCheck: 355M/770M微调后=GPT-4精度(真实claim上), 400x便宜【√API】
2. DSS: 770M多任务蒸馏>540B few-shot【√API】
3. AlignScore: 355M≥ChatGPT/GPT-4式指标【√API】
4. RE域: Saleem 0.78 vs 0.96; El-Hajjami无单一赢家【√API】
5. NLI4CT: 领域文档上通用模型崩溃, 适配是唯一出路【√API】
→ 五条独立证据链一致: **领域判别任务, 微调小模型是SOTA; 规模买不到领域适配**。

### 复现方案(统一)
以`tools/`新增训练脚本(走runs协议): ①数据=pair_dataset_canonical train/dev/test(排除evidence_quarantine); ②backbone=Qwen2.5-1.5B/3B-Instruct(4bit)+chat模板("判断两条陈述是否一致: ... 输出一致/不一致"), 分类头走序列首个token的约束解码或lm_head二分类; ③PEFT矩阵实验: LoRA vs LoRA+rsLoRA vs DoRA vs DoRA+PiSSA vs LoRA-GA(rank=8/16/32/64扫描, α=2√r); ④对照: mDeBERTa全参微调(编码器上界)、GLM零样本/CoVe(下界); ⑤指标: macro-F1 + AUROC + ECE(校准, ACDD需求); ⑥快照进tests/。
**预期效果**: DoRA+rsLoRA vs 标准LoRA +1~3pp; vs 全参微调(同backbone不可行于8GB, 用1.5B不量化对照)接近持平; Qwen-3B+DoRA预计为我们最强单通道分类器。

---

## 方向E: 2023-2025中文NLU

### E1. Qwen2.5 / Qwen3 / GLM-4(backbone选型)
- **Qwen2.5 Technical Report**. 2024, arXiv:2412.15115【√API】: 0.5B~72B全尺寸, 18T token预训练; 中文小尺寸(1.5B/3B)质量是同尺寸最优之一。
- **Qwen3 Technical Report**. 2025, arXiv:2505.09388【√API】: 0.6B~235B; **混合thinking/non-thinking单框架+thinking budget**; Apache 2.0; 119语言。
- **ChatGLM/GLM-4**: Team GLM. 2024, arXiv:2406.12793【√API】: 万亿级中英token; GLM-4-9B开源; 中文对齐(AlignBench)超GPT-4。
- **使用要点(分类任务)**: ①Qwen3**关thinking**(`/no_think`或chat模板开关)——pair判定是快任务, thinking只烧token不涨分; ②尺寸阶梯1.5B/3B/7B(7B需4bit QLoRA才入8GB; 3B可bf16+LoRA); ③GLM-4-9B与本地GLM API同族——**作student时注意与GLM-teacher的同族偏差**, 评测judge坚持异族(Qwen/DeepSeek), 呼应项目no_human_annotation_eval_survey的双模型协议。
- **8GB**: ✅(≤3B bf16+DoRA; 7B须4bit)。

### E2. 中文NLI/矛盾检测2023-2025: 方法学空白
- 检索确认: 2023-2025**没有**中文专用NLI新方法论文(OCNLI/CMNLI等数据集均为2020年前; Erlangshen为2022; 方法创新均在英文或语言无关层)。中文能力由Qwen/GLM backbone+语言无关方法(DoRA/QLoRA/DSS等)覆盖。
- **含义**: "中文SRS pair矛盾分类器"无先例; 我们在A/B/D方向选任何方法移植到中文GJB域, 都是**首次中文域实例化**——这既是空白证据, 也意味着没有中文基线可抄, 必须自建(基线=Qwen零样本/Erlangshen/mDeBERTa, 均已具备)。
- (辅助数据注: CMNLI/OCNLI可作中文NLI适配的中间预训练垫层——数据集非方法, 不列入, 但与"外部NLI源"的pair_dataset转换管线兼容。)

### E3. 最佳使用配方(汇总)
```
判别器:   Qwen2.5-1.5B/3B-Instruct + 4bit QLoRA(bf16 for 3B) + DoRA + rsLoRA
编码器线: mDeBERTa-v3-base + 全参微调(快速对照) / Erlangshen(零样本参照)
teacher:  GLM API(cache=True) 造rationale/弱标注/合成数据
judge:    异族(Qwen/DeepSeek) —— 评测协议, 不是判别器
校准:     温度标定+共形弃权(接ACDD), 采样分歧度(SelfCheckGPT思想)作特征
```

---

## Top-5(按 新鲜度×相关性×可实现性)

| # | 方法 | 出处 | 为什么排这里 | 复现成本 |
|---|------|------|------------|---------|
| 1 | **DoRA+rsLoRA(±QLoRA/PiSSA) on Qwen2.5-1.5B/3B** | ICML 2024 Oral / NeurIPS 2024 | pair二分类主战场的当前最优训练配方; peft一行开关; 8GB全谱可行; 与"中文backbone最优"叠加 | 低(1~2周) |
| 2 | **MiniCheck配方中文化(确定性变异生成器版)** | EMNLP 2024 | 2024最新数据配方; 我们的48算子+锚点真实对=其"合成+真实"混合的更优实现(生成确定可复现, 解Korn 2026之痛); 产出=首个中文GJB域claim级矛盾检测器 | 中(2~3周, 数据混合比消融) |
| 3 | **TSRCDF-SS复现** | 2025(arXiv:2511.23007) | RE唯一直接竞品, 论文必配基线; 复刻六元拼接+Focal变体+迁移协议; 其"给定句对+纯文本+无context"三弱点=我们的超越论证 | 低(1周) |
| 4 | **Distilling Step-by-Step rationale多任务** | Findings ACL 2023 | 1~2K pair小数据的最大杠杆; GLM API一次性成本(缓存); 770M>540B先例; rationale头输出=解释链(ACDD证据链素材) | 中(2周) |
| 5 | **FreeAL免人协同训练** | EMNLP 2023 Main | 零标注预算放大器(22条gold→数万弱标注); 与双LLM分歧/160条uncertain弃权带**架构同构**; 训练闭环=可发表的弱监督协议 | 中(2~3周) |

落选说明: AlignScore(多skill统一, 工程量最大, 作二期); FActScore/VERISCORE(是pair分类器的**使用方式**而非训练法, 进条目级管线); CoVe(零训练对照, 顺手就做); PiSSA/LoRA-GA(并入#1配方做初始化消融); VeRA/LoRA+/NEFTune(消融素材)。

---

## 我们可以在哪些方法上提出什么改进

1. **基于MiniCheck(数据配方)**: 用**确定性48变异算子**替代其GPT-4自由生成(可复现、分布受控), 用**锚点真实差异**替代其"real claims"(更强领域锚定)→"GJB-MiniCheck": 首个中文军事SRS域claim级矛盾检测器, 合成/真实混合比例+锚遮蔽迁移实验为贡献点。对Korn 2026"LLM生成缺陷不可靠"的直接回应。
2. **基于TSRCDF-SS(架构)**: 句对双编码器→**锚定条目对+多模态context编码**(context字段已挂载表/图/正文); Focal+置信惩罚→**类型条件化校准+共形弃权**(π(real)类型异质性已实测: 异常流≈0.79 vs 参与者≈0.11); 跨域迁移→**跨场景/跨文档leave-one-out**(我们数据协议独有维度)。每一项都直击其论文自认局限。
3. **基于DoRA/LoRA族(训练)**: **类型感知PEFT**——angle.type(48类)作辅助多头或分组LoRA(不同不一致类型共享底座、独立适配器), 是LoRA多任务/条件化文献在"不一致类型学"上的首次领域实例化(与B5的"领域适配是唯一出路"结论衔接)。
4. **基于DSS(蒸馏)**: rationale→**证据span监督**(呼应LegalWiz证据定位趋势): rationale中的参数/术语位置作span标注, 训练小模型同时输出label+证据定位——解释链直接进ACDD的归属证据链。
5. **基于FreeAL(弱监督)**: 把"分歧驱动选择"升级为**双LLM分歧度+锚点校准的弱监督聚合**(DS式): 分歧度不再只是弃权信号, 而是与θ误差模型联合的观测——与ACDD框架无缝对接, 这在FreeAL原文中不存在。
6. **基于DFKI-NLP(鲁棒性)**: 数值/术语扰动+MinMax损失做鲁棒性消融(数据管线零改动, 纯实验)——低成本填充论文消融节。

---

## 引用核验清单

**本轮arXiv API逐条核验(√API, 27条)**: 2302.10198(Zhong) / 2303.08896(SelfCheckGPT) / 2305.02301(DSS) / 2305.03598(NLI4CT) / 2305.14251(FActScore) / 2305.14314(QLoRA) / 2305.16739(AlignScore) / 2309.11495(CoVe) / 2310.05914(NEFTune) / 2310.11454(VeRA) / 2311.11547(El-Hajjami) / 2311.15614(FreeAL) / 2312.03732(rsLoRA) / 2402.09353(DoRA) / 2402.12354(LoRA+) / 2404.02948(PiSSA) / 2404.10774(MiniCheck) / 2405.00321(DFKI-NLP) / 2405.09673(LoRA Learns Less) / 2406.12793(GLM-4) / 2406.19276(VERISCORE) / 2407.05000(LoRA-GA) / 2412.00959(Saleem) / 2412.15115(Qwen2.5) / 2505.09388(Qwen3) / 2511.23007(TSRCDF-SS) / 2512.06586(AlignRuScore)。

**项目既有调研核验(√项目)**: Fantechi et al. RE 2023(DBLP) / S3CDA 2206.13690 / Zadenoori 2509.11446 / ContractCheck 2504.18422 / LegalWiz 2510.03418 / Korn 2606.25550 / LEREDD 2602.22456 / QUARE 2603.11890 / Ezzini ICSE'21-23线(DBLP)。

**勘误(本轮发现的自忆错误, 已修正)**: AlignScore正确ID为2305.16739(2305.13439是CMS物理论文); "Can ChatGPT Understand Too?"正确ID为2302.10198(2303.17511是Strasser的伦理文章); SAFE(Long-form factuality)ID未核验到, 已移除不列; 其结论方向也与自忆相反(通用域NLI上ChatGPT超BERT)——该修正已反映进B5结论。

**知识边界声明**: 本调研方法学知识截止2025年中; 2025年下半年-2026条目(TSRCDF-SS/Zadenoori/AlignRuScore)依赖本轮API核验与项目调研, LEREDD/QUARE等2026工作仅作窗口外注记, 未纳入选型。
