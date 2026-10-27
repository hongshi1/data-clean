# 模块化验证系统设计——深度调研报告

> 调研日期：2026-10-22
> 方法：arXiv API 定向检索（5角度×多查询式）→ 22篇论文全文HTML（arxiv.org/html / ar5iv）下载并**精读方法章节与消融实验**（非仅摘要）；会议信息以arXiv comment为准
> 服务对象：ACDD三层级联验证（L0 NER实体检测 → L1 符号/规则验证 → L2 NLI残差），军事SRS文档一致性校验
> 说明：用户提到的"NeuroBlocks"在arXiv检索0命中（不存在或非arXiv论文），已用 MoMa / AdapterFusion / DAM 替代覆盖该角度；"LEGO NLP"无对应论文，以 Modular Deep Learning 综述的理论框架替代。两篇仅有摘要页（E1/E3）已标注。
> 交叉引用：`cascade_innovation_expansion_survey.md`（级联+CP创新点）、`nlp4re_llm4re_comprehensive_survey.md`（NLP4RE全景）、`method_framing_and_novelty_check.md`

---

## 0. 速查表

| 角度 | 论文 | 出处 | 对本架构核心价值 |
|---|---|---|---|
| A | FrugalGPT | arXiv 2305.05176 (2023) | 级联=学习型scorer+逐层阈值+成本优化；MPI层间互补度量 |
| A | GPTScan | ICSE 2024 (2308.03314) | 规则筛选(召回优先)→LLM确认(精度优先)→静态再确认；FP过滤2/3 |
| A | LLM-Modulo | ICML 2024 (2402.01817) + 2411.14484 | sound critic给硬保证；backprompt修复回路；format critic前置 |
| A | Modular Deep Learning综述 | arXiv 2302.11529 (2023) | 4维分类法(计算/路由/聚合/训练)形式化我们的架构 |
| A | DecomposeRL | arXiv 2605.27858 (2026) | 可审计trace；leave-one-out必要性奖励；OOD鲁棒性来源 |
| B | RaRE | arXiv 2610.21179 (2026) | logprob逆方差置信加权+分歧丢弃；朴素平均无效的证据 |
| B | MCP多Agent虚假信息检测 | SYNASC 2025 (2508.10143) | 误分类率解析导出验证器权重；无gold平均失败案例 |
| B | HybridFC | ISWC 2022 (2409.06692) | 异构验证器+MLP stacking融合；逐组件消融 |
| B | Viva La Vida | arXiv 2610.04829 (2026) | 弃权≠否决；provenance/polarity必须保留；验证器失效模式解剖 |
| B | LLM集成生成网络安全需求 | arXiv 2609.10316 (2026) | CombSUM投票+Naive-Bayes对数似然权重；排序复核队列 |
| C | CoT Faithfulness | arXiv 2307.13702 (2023) | 截断/注入错误/填充token/改写四干预协议→管线忠实性审计 |
| C | ROME | NeurIPS 2022 (2202.05262) | 因果追踪(clean/corrupt/restore三运行)→模块级错误定位 |
| C | Patchscopes | ICML 2024 (2401.06102) | 中间表示可被另一prompt解码=可审计接口；表示手术修复 |
| C | How Do LLMs Cite? | ECIR 2026 (2606.28358) | AND门控分布式归因机制；定向放大/衰减修复>90%漏引 |
| C | AssumptionMiner | arXiv 2607.22898 (TSE投稿) | AssumptionRecord schema+依赖图+局部重生成 |
| D | AdapterFusion | EACL 2021 (2005.00247) | 两阶段：独立抽取+注意力组合；抗任务干扰 |
| D | MoMa | ICLR 2026 (2502.15483) | 模块Hub+kNN代理+凸优化组合(免训练)；few-shot优势 |
| D | DAM | EACL 2023 (2302.06321) | 功能模块按需插拔(防偏见adapter热交换) |
| E | SAT-solver需求矛盾检测 | SE 2024 (2405.00163)* | DO-178C语境下NL→逻辑式→SAT，与我们L1同构 |
| E | SummaC | TACL 2022 (2111.09525) | NLI粒度错配诊断+pair matrix聚合 |
| E | Two Truths and A Lie | arXiv 2609.03230 (2026)* | LLM需求质量评估不对称错误；模块复合风险警告 |
| E | FICLE | ECML-PKDD 2023 (2306.08872) | 不一致类型学+span标注+四模型分阶段流水线 |
| E | Agent4RE | ASE@POVC 2026 (2610.10628) | RE域多agent模块化趋势佐证（生成导向，与我们互补） |

*仅摘要页（无全文HTML），数字取自摘要。

---

## 角度A：模块化架构设计的理论基础

### A1. FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance
**Chen, Zaharia, Zou — arXiv 2305.05176, 2023**

**核心机制（§3-4精读）**：
- LLM cascade：按顺序调用 LLM 列表 L=[L₁..L_m]，第 i 层产生回答 f_{L_i}(q) 后由**评分函数** g(q, a)∈[0,1] 判定可靠性；score>τ_i 则 STOP 返回，否则升级到下一层（更贵更强的模型）。
- 评分函数=微调的 DistilBERT 回归器（学"这个回答是否正确"）；路由选择+阈值学习被形式化为**约束优化**：max E[质量] s.t. E[成本]≤预算，z=argmin满足阈值的层。混合整数问题难解→专用优化器：(i) 按"回答分歧小"剪枝 LLM 组合空间；(ii) 少量样本插值目标。
- 三策略可组合（prompt adaptation / LLM approximation / cascade），组合空间=成本-质量-训练成本三方折衷。

**模块化设计细节**：
- 模块边界：每个"API+scorer"对是一个自治单元；接口=(query, answer)→[0,1]分数（**分数即模块间通信协议**）；责任划分=便宜模块处理简单查询、昂贵模块只接残差。
- 级联增益的理论解释=**生成多样性**：提出 MPI 度量（LLM A 对 B 的最大性能改进=P(A对∧B错)）。

**消融/证据**：HEADLINES 上匹配 GPT-4 精度的成本节省 98.3%（33.1→0.6）；预算=1/5 GPT-4 成本时精度反超 +1.5%；GPT-4 错但便宜模型对的样本：HEADLINES 6%、COQA 13%（MPI实证）；失败模式：所有层答案一致但scorer不确定→全链路查询（开放问题）。

**与我们的映射**：
- L0→L1→L2 就是 cascade，但目前路由是**固定规则**；FrugalGPT 提示"每层应配学习型接受阈值 τ_i"，可在银标上学。
- MPI 矩阵可直接移植为**层间互补性度量**：P(L1判对∧L2漏检)、P(L0锚点对∧L2误判)——论文里用量化证据证明"级联增益来自互补而非堆叠"。
- 成本核算表（每层 token/延迟/调用数）+质量Pareto曲线 = 审稿人最爱的分析图。

### A2. GPTScan: Detecting Logic Vulnerabilities in Smart Contracts by Combining GPT with Program Analysis
**Sun, Wu, Xue, Liu, Wang, Xu, Xie, Liu — ICSE 2024, arXiv 2308.03314**

**核心机制（§3-§5精读）**：
- 三个动机实例证明分工必要性：静态分析能查 `totalSupply()` 模式但不懂语义；GPT 能认变量 `_amount`/`_shares` 但"看不懂 before/after"（对补丁版误报）。结论：**静态分析缺高层语义（低召回），GPT 缺低层信息（高误报）**。
- 漏洞类型分解：10类逻辑漏洞→**场景(scenario，功能前提)+属性(property，根因行为)** 二元组，写成完整句子（如 Risky First Deposit：场景=deposit/mint/add liquidity；属性=supply为0时把总份额设为首次存款额）。场景先批量问（一个prompt问所有场景，JSON输出），通过者再问"场景+属性"复合句（双确认），只允许 yes/no。
- 逆向分工（对我们最重要）：**GPT先做筛选（召回优先，容忍FP）→ 静态分析做最终确认（精度优先）**。GPT 被要求输出关键变量/语句（附描述；若变量不存在或描述不相关→直接判无漏洞，错误就地截断），然后由四类静态检查确认：数据流追踪(DF)、条件值比较(VC)、语句顺序(OC)、函数参数可控性(FA)。
- 鲁棒化细节：温度=0；空会话（每次查询无历史）；"mimic-in-the-background"提示（让模型后台自答5次取众数）。
- 多维过滤（YAML规则语言 FNK/FCE/FCNE/FCCE/FCNCE/FPT/FPNC/FNM/CFN + 调用图可达性分析）把36文件/项目压到少量候选函数，使 GPT-3.5 4k 上下文够用。

**消融/证据**：RQ3（静态确认的价值）：GPT匹配后647个原始候选函数→静态确认后剩221（**过滤65.84% FP**），仅损失3个GT（3 FN）；纯GPT基线（David et al.）precision 4.14% vs GPTScan 57.14%（Web3Bugs）；Slither 同类规则全部FP（13,144条警告中相关146条全误报，因不关联调用链）；发现9个人工审计漏掉的漏洞；成本 0.01 USD / 千行 / 14.39 s。
- 失败模式归因清晰：FP 主因=触发条件跨函数逻辑链（模块边界切错了上下文）；FN 主因=无别名分析。

**与我们的映射**：
- GPTScan 的方向是"**规则选候选→LLM确认→规则再确认**"，我们是 L1→L2；二者共同原则：**确定性模块永远保留否决权**（GPT 输出必须映射到可静态验证的对象上才被采信）。
- 场景+属性分解 = 我们"不一致性类型清单"的范式：每种类型拆成"检测场景（前置条件）+矛盾属性（判定式）"，使 L2 prompt 变成 yes/no 判定而非开放推理。
- "GPT输出变量不存在→就地终止"= **中间输出的可验证性契约**：L2 引用的锚点/实体若 L0 未检出，判定作废——错误传播在接口处截断。
- 上下文裁剪（callers+本函数）对应我们"条目聚合时带哪些邻近上下文进 L2"。

### A3. LLM-Modulo（ICML 2024立场论文 + 技术评测）
**Kambhampati et al. — ICML 2024 (2402.01817)；Gundawar, Valmeekam, Verma, Kambhampati — arXiv 2411.14484**

**核心机制（§3精读）**：
- generate-test-critique 循环：LLM 提案 → critic bank 评审（hard约束=正确性；soft约束=风格/偏好）→ **metacontroller 汇总所有 critique 成单条 backprompt** → 再查询 LLM，直到全部 critic 通过或预算耗尽（10轮）。
- **soundness 来自 sound critic，completeness 来自生成器**——系统保证"输出的都是对的"（若 critic 可靠），不保证"能找出所有对的"。这是我们级联保证分级的直接理论出处：L1（规则/SAT）=sound critic，L2（NLI/LLM）=heuristic critic。
- 格式 critic **最先**运行：先修 JSON/格式错误再进语义 critic——语法层前置的工程理由。
- critic 本身可由 LLM 提取：给 GPT-4-Turbo 目标+工具声明+输入JSON schema，生成的 critic 经编译器/parser critic 修语法后与手写 critic 等效（A.4）——**"验证器可以从LLM半自动增殖"**，对我们 L1 规则库扩充（GJB 120条→更多）是直接可用的方法。

**消融/证据（§4-5精读）**：Travel Planner：GPT-4o-mini 2.78%→15.00%，Claude3.5-Sonnet 4.44%→25.00%；Calendar Scheduling：GPT-4o-mini 36.90%→61.60%，Claude 72.90%→88.80%（10轮）。
- 架构变体消融（§5）：(1) 历史错误计划入上下文，收益在 n>10 后饱和，**去重反而更差**；(2) 过滤已被否决的取值（"此酒店最少住7晚"→从后续prompt删除）：GPT-4o 21.11%→36.11%（**把否定性证据转成搜索空间剪枝**）；(3) 多解树搜索 BFS 深度10：+25.8pp；(4) **反馈量消融：只给第一条critique≈给全部critique**（二元反馈显著更差）——反馈"有"比"全"重要；(5) 加"think step-by-step"：+6.9pp。

**与我们的映射**：
- 我们的级联目前是**单向检测**；LLM-Modulo 证明 backprompt 闭环能把检测系统升级为修复系统：L1 矛盾→结构化 critique→回灌 L2/人工修复建议。输出从"标签"变成"可执行的定位"。
- metacontroller = 黑板系统裁决器的理论原型：多通道 critique 的合并、优先级、pedagogical 选择都是它的设计维度。
- "critic 提取"对应：从 16 份 SRS 人工标注的矛盾对中半自动蒸馏新 L1 规则。

### A4. Modular Deep Learning（综述）
**Pfeiffer, Ruder, Vulić, Ponti — arXiv 2302.11529, 2023**

**核心理论（§1-2精读）**——"为什么要模块化而非端到端"的最系统回答：
- 端到端的三大病理：多任务**梯度干扰**（spatial crosstalk）、持续学习**灾难遗忘**（temporal crosstalk）、分布偏移下**系统性泛化失败**。
- 关键否定性证据（引用）：vanilla 网络自发模块性很弱——子网络不被复用到组合任务（Csordás 2021）；简单任务与组合任务性能**完全不相关**（Li 2022）。→ 模块性必须**显式设计**，不能指望涌现。
- 模块化四大收益：正向迁移（相似函数同模块）；**re-composition**（零样本重组已学技能：瓜拉尼语×依存句法各自训练、推理时组合）；**鲁棒性**（分布局部漂移只更新对应模块，局部更新→样本效率）；条件计算（参数/时间效率）。
- **四维分类法**：计算函数（参数/输入/函数组合）、路由（固定/学习×硬/软）、聚合（确定性/可学习）、训练（联合/持续/后置冻结）。后置冻结是当前主流（大模型预训练为稠密共享，之后"模块化"）。

**与我们的映射**：把 ACDD 放进这个坐标系（论文正式化用）：
- 计算=异构模块（规则引擎/符号求解器/NLI模型/LLM）；路由=固定（规则覆盖路由）+可学习（scorer）；聚合=裁决融合层；训练=后置冻结（各模块独立达标后只训小融合层）。
- "局部更新"是我们 OOD 故事的理论根据：新军种/新格式 SRS 到来时只更新 L0 词典或 L1 规则子集，L2 冻结。

### A5. DecomposeRL: Learning to Ask Useful, Informative, and Diverse Questions for Semi-Supervised, Traceable Claim Verification
**Dipta, Padia, Ferraro — arXiv 2605.27858 (2026)**

**核心机制（§3精读）**：
- 把声明验证显式化为迭代QA分解：策略输出结构化 trace τ=(think块, n个⟨Q,A⟩循环, verification块)，XML定界；GRPO 训练。
- **七元异构奖励集成**（两种异构性：评估器异构=确定性/嵌入/LLM-judge；粒度异构=声明级/子问题级）：format、verification（结果锚，防代理漂移）、question count（三角核）、diversity（MMR嵌入冗余惩罚）、coverage（judge 仅凭答案能否复原金标签）、**necessity（leave-one-out四态矩阵：删掉该问题裁决变坏+1必要/不变+0.5冗余/本来错删后还错0/删后反而对−1有害，按 min 聚合——不用平均，防单个有害问题躲在多数必要问题后面）**、joint（可回答×原子性×正确性**连乘**——防止用其他维度补偿）。
- 半监督：无标签路径用自一致伪标签替换 verification/coverage。

**消融/证据（§4.3精读）**：77B 模型 in-domain 86.3 / OOD 69.8；奖励消融：去 necessity → OOD **−4.8**（单项最大），去 coverage −3.9、diversity −3.2，in-domain 全部 ≤0.7；**in-domain 鲁棒而 OOD 脆弱——软质量奖励的价值几乎全部体现在分布外**；10%标签（s=0.1）超过全部 77B 基线；与 4× 大模型及 GPT-4.1-mini 打平。
- 相关工作论断（与用户问题直接对应）："**端到端分类器精确但不产生可检查的 trace；分解式方法可审计但落后**"——DecomposeRL 的贡献就是同时拿到两者。

**与我们的映射**：
- trace 结构=我们每条裁决的**证据记录**（L0 span→L1 规则命中→L2 NLI 对）应同构于 ⟨Q,A⟩ 循环：可读、可抽样审计。
- leave-one-out necessity **直接移植为模块归因协议**：对每条裁决，删除 L0 锚点/L1 规则/L2 通道后 verdict 是否翻转 → 每层"必要性分布"图。DecomposeRL 的证据（OOD −4.8）预示这类审计信号对域外鲁棒性最有价值。
- "min聚合防掩盖"和"连乘防补偿"是融合函数设计的两条戒律，可直接进我们的裁决器设计章节。

---

## 角度B：多专家/多验证器融合

### B1. RaRE: Judging the Judges——Confidence and Disagreement in Rubrics as Rewards
**Liu, Harrington, Darrell, Bai — arXiv 2610.21179 (2026)**

**核心机制（§3精读）**：
- **朴素平均失败**：HealthBench 上 Gemini+DeepSeek 均分 0.307 落在两个单判 (0.296/0.338) 之间——平均只会混合偏差，不产生增益。
- soft-Likert：judge 用单 token 输出 1-5 评分；读该位置的 top-5 **logprob** 得评分分布 p_j(k)→期望评分 E_j、逆方差置信 c_j=1/(1+Var_j)（分布集中/双峰都会降 c）；集成奖励=Σc_jE_j/Σc_j（高斯独立估计量最大似然组合的软近似）。
- drop-on-disagreement：分歧度 d=max-min归一化；d>τ 的 rollout 奖励替换为组均值→GRPO 组归一化后 advantage=0→**不产生梯度**（把不可靠样本从学习信号中剔除而非硬丢弃）。
- 两机制**正交组合**：置信加权管判内不确定性，分歧丢弃管判间不确定性；soft 无 drop 时 0.330 反而低于单判（低置信分歧的残余贡献污染 advantage 估计），soft+drop=0.364（超最佳单判 +2.5pp）。

**消融/证据（§4.3-4.4）**：τ=0.30/0.40 最优；drop alone +0.8pp；per-theme 分析：**集成继承（而非平均掉）各判的长处**——RaRE 最佳配置在每个 theme 上都达到两判各自最优的水平。

**与我们的映射**：L2 若跑多 NLI 底座（mDeBERTa+Erlangshen）或多 prompt 变体，这就是融合协议模板：(1) 从 logits/logprob 取连续分布而非 argmax 硬票；(2) 逆方差置信加权；(3) 分歧>阈值→**弃权态**并路由人工/更强通道。逐条戒律都有实证编号可引。

### B2. MCP-Orchestrated Multi-Agent System for Automated Disinformation Detection
**Avram, Groza, Lecu — SYNASC 2025, arXiv 2508.10143**

**核心机制（§V-VI精读）**：
- 四个异构 agent：经典ML（逻辑回归）、Wikipedia知识核查（**NER实体链接到KG**）、LLM coherence 检测（prompt 工程）、网页抓取三元组分析。MCP 协议共享上下文，RunnableLambda 异步链式编排（可扩展性卖点）。
- 聚合=加权平均，**权重由误分类率解析导出**：w_i=(1−m_i)/Σ(1−m_j)（无任何学习）；实测权重 19%/23%/17%/41%（数据量与新鲜度决定高低）。
- 阈值0.41处达 95.2% 准确率；**数学导出权重显著优于算法网格搜索阈值**。
- 失败模式记录（§VI-B，对我们极有教育意义）：单模型≈随机；两裸模型平均→**过度矫正，全判fake**（消除FP的代价是FN暴涨）；加入一个域内微调模型后误分类几乎消失。

**与我们的映射**：异构验证器（规则+NER+LLM）权重可在**旧gold（22条）+新增银标**上按误分类率解析估计，零学习成本；他们的"平均→过度矫正"现象=我们做黑板通道融合时的对照基线（必须报告"朴素平均"这一栏）。

### B3. HybridFC: A Hybrid Fact-Checking Approach for Knowledge Graphs
**Qudus, Roeder, Saleem, Ngonga Ngomo — ISWC 2022, arXiv 2409.06692**

**核心机制（§4精读）**：
- 三类异构事实核查家族（文本型：PageRank选证据句+SBert嵌入+来源可信度拼接成 φ_ℵ；路径型：COPAAL 给单一分 ζ；KG嵌入型：TransE 实体/关系拼接）→ **每个组件先过自己的 MLP（ϑ₁,ϑ₂），再拼接+ζ 过 ϑ₃ → sigmoid**。单一 MLP 直接融合原始特征"性能不足"（脚注5）——**分组件预处理（对齐量纲/语义）是融合前置条件**。
- 组件可替换性显式设计：文本型/路径型/嵌入型组件各自声明接口（"任何输出X的方法都可以插进来"）。

**消融/证据（§7精读）**：FactBench test 平均：TC 0.73 / PC 0.68 / EC 0.72；两两组合最高 0.82（TC+EC）；**三组件 0.86（Property 0.99）**，Wilcoxon p<0.05 显著优于所有两两组合——三个异构家族各有不可替代的贡献。BD 小数据集上 HybriFC 与两两组合同样过拟合——**融合元学习器吃数据，小样本时解析权重更稳**（与B2互补）。

**与我们的映射**：L1 规则命中向量、L2 NLI 概率、L0 证据特征（锚点数/覆盖度）三路→各自小MLP→拼接→最终裁决，就是 HybridFC 结构；消融协议（单组件/两两/全量）可直接抄为我们的融合层消融表。

### B4. Viva La Vida: Verification and Accumulation Failures in Multi-Agent Proof Search
**Xu, Zheng, Han — arXiv 2610.04829（Math Reasoning & AI Workshop, 2026）**

**核心机制（全文精读）**：对 186 小时/$5,694 的 agentic 证明搜索系统做全链路 trace 分析（51,754 条观测）：
- **Result 1（惰性验证器）**：三模型验证器要求**全体一致**且 fail-closed（解析失败/API错误=不通过）；12 次验证事件中 10 次在数学内容被读之前"算术上不可能通过"（Claude 的 10 条非结构化响应全部记为 non-approval，与实质否决不可区分）。**保守的错误处理 × 保守的聚合规则 = 永远拒绝的惰性验证器**，且对操作员完全静默。
- **Result 2（分歧是承重墙）**：Gemini 3 次批准 GPT 否决的"解决公开问题"声明——单验证器系统会 3 次宣布解决 open problem。挡住错误的是**分歧本身**，不是任何单个验证器。
- **Result 3（极性丢失污染记忆）**：lemma 提取器同时挖掘"证明"和"评审"；因为从无通过，全部评审都是驳斥；93 条入库 lemma 中 24 条（26%）来自被否证论证且**驳斥语境被剥离**（"p=4/9 而非 5/8"被存成孤立事实）；11.8% 的库检索命中这些条目。对照实验：对故意编造的论证，提取率 0.25 vs 真实论证 3.82 条/篇（15×抑制）——**证明通道有防线，批评通道没有**（从未被当作输入通道设计）。
- 设计建议：弃权与拒绝必须是**不同布尔值**且聚合含弃权时实时告警；入库带 polarity 标签；verdict 传播到后代条目；空真过滤器。

**与我们的映射**：这是**裁决协议的反面教材库**，每条都能对应到我们的设计决策：(1) 黑板各通道超时/解析失败→ABSTAIN 态（≠REJECT），聚合一票弃权→该条目路由人工；(2) 锚点库/规则库的每条记录必须带 {来源层级, polarity, 依赖verdict}；(3) 多底座分歧不是噪声而是信号（与B1 drop-on-disagreement 互为正反面：训练时丢弃、推理时升级）。

### B5. Ensembling LLMs for AI-Augmented Cybersecurity Software Requirements Generation
**Perez-Acuna, Martín, Yelmo — arXiv 2609.10316 (2026)**

**核心机制（§III-IV精读）**：
- 24 个run（12配置×4模型家族）对 ISO/IEC 27002 控制项生成需求；池化回收全部 72 条有效需求（单配置平均<一半）但混入 111 条幻觉——**融合的价值在排序而非过滤**。
- CombSUM 投票 s(u)=Σ_r w_r y_r(u)（run级二值票）；Uniform（全同权）vs **Naive-Bayes**：w_m=log(TPR_m(1−FPR_m)/FPR_m(1−TPR_m))，TPR/FPR 在专家标注宇宙上直接估计（Jeffreys +1/2 平滑防无穷权重）；**"沉默也是证据"**：闭宇宙中未生成=信息性零票，后验log-odds=Σ(票贡献−沉默贡献)——排序恰为贝叶斯后验排序；与 Dawid-Skene 噪声观察者模型同族。
- 明确声明不学 run 级个体权重：同配置的重复 run 只体现随机性，学权重=拟合偶然方差（**权重粒度选择的方法论**）。

**消融/证据（§VI精读）**：Uniform 已大幅超最佳单配置（PR-AUC/ROC-AUC +0.142/+0.118）；NB 再 +0.039/+0.052 → 0.864/0.869；F2@40 0.483→0.579（P@40 0.887→0.950, R@40 0.434→0.528）；增益在 ≥92% bootstrap 重采样中稳定。

**与我们的映射**：RE域融合的完整模板：(1) 多run LLM 验证同一批条目→票数+模型可靠性→**排序输出=人工复核优先队列**（军标审计的天然交付物）；(2) NB 权重只需每模型几条专家标注即可估计——直接复用我们的旧 gold；(3) "排序而非过滤"哲学解决"无金标准时评测"的一半困境。

---

## 角度C：可解释性与错误归因的模块化设计

### C1. Measuring Faithfulness in Chain-of-Thought Reasoning
**Lanham et al.（Anthropic）— arXiv 2307.13702, 2023**

**核心机制（§2精读）**：CoT 是否真实反映模型计算→**干预中间推理并测最终答案翻转**：
- **Early answering**：截断 CoT 到第 k 句→直接要答案；若答案不变=截断点之后的推理是事后合理化。
- **Adding mistakes**：在第 i 句注入 LLM 生成的错误版本→续采样→测答案匹配率（低=真依赖）。
- **Filler tokens**：CoT 换成"…"→精度无增益（部分任务反降）→性能提升非纯test-time compute，推理内容确实被使用。
- **Paraphrasing**：改写 CoT 测形式依赖。汇总指标 AOC（按推理长度平均的同答率）。
- 每题采样100个推理（nucleus p=0.95, T=0.8）；NLTK 分句对齐。

**关键发现**：忠实度任务间差异巨大（AQuA/LogiQA 最忠实）；与 CoT 带来的精度增益**不相关**；**模型越大越不忠实**（§3）。

**与我们的映射**：这套协议**原样移植为级联忠实性审计**：截断 L0 锚点集合/注入错误实体/替换 L1 规则命中→测 L2 裁决翻转率。若 L2 裁决在 L0 输入被破坏时不变，说明 L2 并未真正使用 L0 证据（黑箱旁路）——这是审稿人会问"级联是真分工还是装饰"的定量回答。注意其"大模型更不忠实"结论提醒：L2 用更强 LLM 不自动带来更可信的级联。

### C2. Locating and Editing Factual Associations in GPT（ROME）
**Meng, Bau, Andonian, Belinkov — NeurIPS 2022, arXiv 2202.05262**

**核心机制（§2精读）**：**因果中介分析**定位事实存储位置：
- 三次运行：clean（正常预测）／corrupted（subject 词嵌入加 σ×3 高斯噪声，预测被破坏）／**corrupted-with-restoration**（在噪声运行中把单个中间状态 h_i^(l) 钉回 clean 值）。
- TE=ℙ[o]−ℙ*[o]；**IE=修复单点后恢复的概率增益**；对1000条事实陈述求 AIE 得逐位置因果热图。
- 发现：早位点（**中层MLP、subject最后token**，AIE 8.7%@L15；MLP贡献6.6% vs attention 1.6%）+晚位点（末token attention）；切断MLP路径的对照实验确认中层MLP因果必要；**因果追踪比积分梯度等梯度归因更informative**；rank-one 权重编辑（ROME）成功定向改写该事实=定位的因果验证。

**与我们的映射**：模块级"clean/corrupt/restore"协议：把某层的输出（L0 实体表 / L1 规则命中集 / L2 逻辑分）替换为噪声/金值，测最终 verdict 的恢复量=该层对结论的**间接效应**。这给了"错误归因"一个操作定义：哪一层的 restore 能救回结论，错误就定位在哪一层。比事后解释（attention图/SHAP）更符合因果语义。

### C3. Patchscopes: A Unifying Framework for Inspecting Hidden Representations
**Ghandeharioun, Caciularu, Pearce, Dixon, Geva — ICML 2024, arXiv 2401.06102**

**核心机制（§3-5精读）**：
- 统一框架：把源运行的中间表示 h_i^ℓ **patch 进另一次推理**（目标prompt T、目标位置 i*、目标模型 M*、目标层 ℓ*、映射函数 f）——五元组 (T, i*, f, M*, ℓ*)。logit lens/tuned lens/causal tracing/attention patching 全是该框架的特例（§3.2给出逐个映射）。
- 语义：patch 后的计算可以补充信息，但**源上下文被切断**——能解码出来的信息必然已在表示中（可审计性的形式定义）。
- 新能力：换目标 prompt 即可表达性解码任意属性（"The capital of X is" 探查国家表示）；**跨模型 patch**（大模型解释小模型表示）。
- §5应用：多跳推理错误**无需生成推理链**修复——把 ω₁ 的表示 reroute 到 σ₂ 位置：vanilla 19.57% → CoT 35.71% → CoT-Patchscope **50%**（Vicuna-13B, 46样本）——**表示手术式纠错**，且只需 O(1) 次推理。

**与我们的映射**：(1) 证据记录接口设计原则：**中间产物应"可被另一个上下文解码"**——L0/L1 的输出要能独立送进 L2/人工审查界面而不依赖原运行环境（我们已部分做到，需写成显式契约）；(2) "用更强模型审计弱模块"= LLM 复核 L1 规则命中的合理性（LLM-Modulo critic 提取的同构）；(3) 表示手术→**局部修复**：错误条目只替换出问题的模块输出而非全条目重跑。

### C4. How Do LLMs Cite? A Mechanistic Interpretation of Attribution in RAG
**van Dort, Heuss — ECIR 2026, arXiv 2606.28358**

**核心机制（§3-4精读）**：
- 受控双条件设计（相关文档 vs 结构匹配的干扰文档，同题同prompt跑两次）隔离"引用行为"的驱动因素；行为量化=citation token "[" 与句号 "." 的 **logit 差**。
- 激活 patching（残差流/attention输出/MLP输出；归一化分数=(patched−corrupted)/(clean−corrupted)）定位机制：**分布式"归因集成"而非单一引用头**；AND门控结构：单头噪声化可摧毁>60%引用行为（如 L15H8），单点去噪只恢复10-30%——**易破坏、难诱导=脆弱的合取依赖**；早期实体富集→重复匹配（Var_1 位置的激活携带"已落地文档"内部标记）→中层处理枢纽(L10-20)→末期决策组装。
- **定向干预**：放大/衰减关键头+MLP → 修复 >90% 漏引、消除 69% 幻引（PopQA），HotpotQA 上增益温和（机制非数据集特异但不万能）。

**与我们的映射**：(1) "系统声称的证据来源是否真是决策依据"是我们 L2 引用锚点时的同一问题——可用其双条件协议做**引用忠实性测试**（换掉锚点文档，L2 的引用行为应翻转）；(2) AND门控脆弱性=级联失败模式预告：**多个前置条件合取时，单模块退化导致全链失效而非降级**——需要在接口处逐条件监控；(3) 定向放大/衰减=对特定验证通道做可解释的增益调节（比重训便宜得多）。

### C5. AssumptionMiner: Extracting, Tracing, and Revising Implicit Assumptions in LLM Code Generation
**Wu — arXiv 2607.22898（IEEE TSE 投稿）**

**核心机制（§III精读）**：
- **五个松耦合组件**（prompt摄取/代码生成/假设提取/依赖映射/增量重生成）由**结构化数据模型**连接（组件间只传数据不传控制）。
- AssumptionRecord JSON schema：`{id, category T1-T6, description, rationale, alternatives, code_refs[{file,start_line,end_line,ast_node}], confidence, severity}`——**同时为人类可读和下游可程序化处理设计**。
- 依赖图 G=(V_a∪V_c, E)：假设→AST节点多对多，边权=置信度；两遍构建：关键词重叠（类别约束的节点类型）→ tree-sitter 自底向上找**最小封闭子树**；LLM 可替换关键词匹配（use_llm=True，精度↑成本↑，消融§VI-D）。
- **增量重生成**：修订假设 a_i→只重生成 R(a_i) 管辖的代码区域（±5行上下文），其余保持——"外科手术式局部编辑，由显式元数据而非测试失败信号驱动"。
- 置信加权集成提取 F1 0.816（超最强离线基线 3.6×）。

**与我们的映射**：**证据记录 schema 直接借用**（改造为：`{id, 不一致类型, 描述, rationale, span/章节引用, confidence, severity, polarity, provenance-layer}`）；"假设→代码依赖图"→"**锚点→条目依赖图**"：修订一个锚点/规则→只重验证受影响条目（增量验证，成本大降——对16份大文档的迭代修复场景是刚需）。

---

## 角度D：模块化训练与模块化推理

### D1. AdapterFusion: Non-Destructive Task Composition for Transfer Learning
**Pfeiffer, Kamath, Rücklé, Cho, Gurevych — EACL 2021, arXiv 2005.00247**

**核心机制（§3精读）**：
- **两阶段学习算法**：阶段1知识抽取=每任务独立训练 adapter（ST-A），基座冻结；阶段2知识组合=冻结 Θ 和全部 Φ，只学 Ψ（每层 Q/K/V：query=基座FFN输出，key/value=各adapter输出，softmax 注意力**按上下文动态激活**有用 adapter）。
- 设计目标：绕开顺序微调的灾难遗忘与多任务学习的数据集平衡难题。

**消融/证据（§5精读）**：16个NLU任务上 Fusion w/ ST-A：15/16 任务 ≥ 单任务adapter（10/16 提升）；**11/16 优于多任务MT-A**（共享信息而不招致多任务干扰）；MT-A 先多任务再 Fusion 只能部分挽回损失（7/16）——**阶段1的独立训练质量决定阶段2上限**；并行训练、无需采样启发式、新任务可增量加入不需重训。

**与我们的映射**：验证器=独立达标的 adapter（各自在子任务上单测），融合层=轻量可学习组合器（attention over 验证器输出，按输入上下文路由）——与我们"冻结模块+训练连接层"的设想完全同构，且消融协议（vs 顺序微调/vs 多任务联合）就是"独立训练+学习组合 vs 联合训练"的对比实验模板。

### D2. MoMa: A Modular Deep Learning Framework for Material Property Prediction
**Wang et al. — ICLR 2026, arXiv 2502.15483**

**核心机制（§3精读）**：
- **MoMa Hub**：18个任务的专用模块库（full 模型或 adapter 模块两种参数化，同一预训练编码器初始化）。
- **AMC 自适应组合**（训练自由）：每模块把目标域数据编码成表示→**留一法 kNN 标签传播**估计该模块在目标任务的预测质量（探测表示空间的局部几何，无参数）→ 组合预测的代理误差 E(w)=‖Σw_j ŷ_j−y‖² 在单纯形上**凸优化**（全局最优、标准求解器、<30秒）→ **权重空间合并** g_D=Σw*_j g_j（线性模式连通性保证合并后仍是良态初始化）→ 下游微调。
- 代理可靠性：kNN 代理误差与微调后 MAE 的 Pearson r>0.6。

**消融/证据（§4.4-4.5精读）**：Select-Average/All-Average/Random 组合在 13/15/15（共17任务）上劣于 AMC（MAE +11.0/18.0/20.2%）；AMC 胜 LoRAHub（黑盒搜索）/JMP路由网络/Softmax启发式 15/17/12 任务（MAE −21.8/15.5/13.7%）；**few-shot 优势放大**：10-shot 归一化 MAE 0.5503 vs 全参微调 0.7003（full-data 差距仅 0.03）。

**与我们的映射**：军标域的模块库构想：按子系统类型（数据获取/传输/处理…）或按验证功能（参数一致性/接口一致性/结构合规…）沉淀专用模块；新文档到来→kNN 代理选组合→凸优化权重→（可选）轻调。**低资源优势**正是我们的处境（每类军标文档样本极少）；"免训练组合"意味着换域零重训成本。

### D3. Parameter-efficient Modularised Bias Mitigation via AdapterFusion（DAM）
**Kumar et al. — EACL 2023, arXiv 2302.06321**

**核心机制（摘要级，全文已下载）**：把去偏见功能封装成独立 adapter（性别/种族/年龄各自模块），**按需挂载**到冻结核心模型上；多属性场景避免灾难遗忘（联合优化多属性会互相干扰）；任务性能保持参数效率；原始/去偏模型可**即时切换**。

**与我们的映射**：验证严格性/领域词典/规则子集做成可插拔模块：GJB 合规扫描（语法层）、参数一致性（语义层）、时序约束（逻辑层）按文档类型热插拔；"多属性联合优化互相干扰"的教训=多类型不一致规则不要联合训练一个大分类头，分开模块再融合。

### D4. 理论背景（承接A4综述）
综述§6-7的要点作为我们训练协议的依据：当前主导范式=**后置模块化**（冻结预训练权重+适配模块）；§7.2 任务泛化通过组合实现；MoE 的模块塌缩/路由不稳定（§4.2.1）是学习路由的已知风险——我们若做学习型路由（裁决器），须报告路由分布稳定性。

---

## 角度E：SRS/需求工程领域的模块化系统

### E1. Logical analysis and contradiction detection in high-level requirements using SAT-solver
**Yatkın, Ovatman — SE 2024（12th Int'l Conf on SE & Trends），arXiv 2405.00163**（*仅摘要级：无全文HTML*）

**核心机制（摘要）**：DO-178C（航空软件标准）把需求一致性列为**强制验证项**；方法=利用**数据字典**把结构化高层需求转换为逻辑表达式→SAT solver 全面检测矛盾；明确做"非自然语言、系统结构化、语言无关"的需求；评测=显著缩短评审时间。

**与我们的映射**：这是我们 L1 的直接同构物，且给出军工语境合法性：DO-178C↔GJB 438C；数据字典↔我们的 `srs_kb.json`（23参数+13接口+10单位族）；"结构化→逻辑式→可满足性"↔我们的约束形式化+Z3。引用价值：证明"符号层做矛盾检测"在安全关键标准中是强制实践而非学术玩具。

### E2. SummaC: Re-Visiting NLI-based Models for Inconsistency Detection in Summarization
**Laban, Schnabel, Bennett, Hearst — TACL 2022, arXiv 2111.09525**

**核心机制（§3精读）**：
- **粒度错配诊断**：NLI 模型是句级训练的，直接用于 50+ 句的文档级一致性任务即失败——这是"L2 NLI 残差"设计者必须先回答的问题。
- NLI Pair Matrix：文档分 M 块（premise）、摘要分 N 块（hypothesis），M×N 蕴含分数矩阵=**二部图**（边权=蕴含概率，天然的中间证据结构）。
- SummaCZS（零样本）：列 max（每个摘要句取最强支撑）→行均值；SummaCConv（可学习）：每列分箱成 50-bin 直方图→1D 卷积（仅 H=50 个参数！）→均值；用 10K 合成 FactCC 子样本训练即可。
- 粒度研究（§5.3.3）：句级粒度最优（段落/双句块均更差）。

**消融/证据**：6 数据集 SummaC Benchmark 上 SummaCConv 74.4% balanced accuracy（+5pt SOTA）；训练成本极小（50参数）。

**与我们的映射**：(1) L2 的输入粒度工程=条目-锚点对齐（我们已做）正是粒度错配的解法，SummaC 是其文献锚点；(2) pair matrix=**句×句证据矩阵**可作为我们 L2 的中间产物（可审计、可人工抽查、可热图可视化）；(3) "极小融合参数即可有效"支持 B3 小融合层的可行性。

### E3. Two Truths and A Lie? Benchmarking Off-the-Shelf LLMs for Requirements Quality Assessment
**Shefa, Salado, Wach, Topcu — arXiv 2609.03230**（*仅摘要级*）

**核心机制（摘要）**：10个模型（OpenAI+Anthropic 各五代）×100次独立运行×2需求集×5温度，对抗 INCOSE 质量标准的专家金标。
**关键数字**：最佳模型中位数只检出 **47%** 的专家认定问题、误报 11%——**不对称错误剖面**（漏检≫误报）；需要SE判断的问题类型（necessity/correctness）**几乎全部漏检**；代际进步非单调（新模型不能假设更好）；温度改变行为甚微→是**特征性缺陷**而非随机性；结论：off-the-shelf LLM 不可作自主评估器；**"在专门架构中编排这些LLM模块，风险是复合缺陷而非纠正缺陷"**；近期合理定位=human-in-the-loop 决策支持。

**与我们的映射**：(1) 我们最重要的**动机论文**：L2 纯 LLM 不可信→级联+校准+HITL 的必要性有 RE 域实证；(2) "不对称错误"指导层间分工：L1 规则保 recall（LLM 漏检 53%），融合层管 precision；(3) 评测协议参考：按问题类型分解报告（我们也应按不一致类型给 per-type P/R）；(4) 它的警告=我们必须做**复合误差实验**（级联 vs 单 LLM 的错误传导对比），否则审稿人引用这篇质疑我们。

### E4. FICLE: Neural models for Factual Inconsistency Classification with Explanations
**Raha et al. — ECML-PKDD 2023, arXiv 2306.08872**

**核心机制（§3-5精读）**：
- 语言学定义 5 类事实不一致；FICLE 数据集 ~8K 样本，每样本标注：不一致 span、不一致 claim 三元组成分、粗/细实体类型——**span级+类型级+实体级三层标注**。
- **四模型流水线**：M1 预测 (S,R,T) 三元组；M2 预测上下文不一致 span（四种策略：结构无视/两步/多任务/oracle）；M3 预测类型+claim成分（个体/两步/多任务）；M4 实体类型（粗→细，含类名嵌入相似度变体）。
- 分阶段策略消融（对我们最宝贵）：**联合 6 任务端到端不如分阶段流水线**；两步（先结构后span）**反而不如结构无视**（误差传播会抵消结构信息增益）；T5 生成式最好预测三元组、DeBERTa 判别式最好预测 span——**不同子任务需要不同架构底座**。

**消融/证据**：不一致类型分类 weighted F1 ~87%；span 预测 EM/IoU 报告齐全。

**与我们的映射**：(1) gold standard 设计模板：不一致类型学+span标注+实体类型层次=我们扩充 gold 的标注 schema；(2) "分阶段打败联合多任务"=L0(span)→类型判定的分阶段架构的实证支撑；(3) "两步可能因误差传播不如无视结构"=**警告我们的 L0→L2 级联必须做传播对照**（L0 用金标 vs 预测时的端到端差异=误差传播量）。

### E5. Agent4RE 与 RE 域模块化趋势
**Tang, Li, Runkler — ASE@POVC 2026, arXiv 2610.10628**（摘要级）

自精炼多 agent 端到端 RE 系统（专业 agent 编排+双改进循环+RE-E2E 基准）：文本指标平均 +8%，人类评分最佳——RE 域正走向多模块 agent 编排，但**生成导向**，与我们**验证导向**正交互补（可作 related work 中"RE域模块化"的趋势引用）。

**工业界背景（知识性引用，未核验原文）**：NASA FRET（自然语言需求→半形式化时序逻辑→可满足性/一致性分析，模块化管线在安全关键需求上的工程实践）；Easterbrook & Nuseibeh 1996（viewpoint-based 不一致管理：不一致是需求过程的常态，应**管理**而非消灭——我们"检测+定位+弃权"而非"消灭"的哲学出处）。

---

## 横向综合：模块化验证系统的八条设计原则

从22篇的方法细节中反复出现的模式：

1. **声明式接口**：模块间只传结构化数据（AssumptionRecord式 schema：id/类型/描述/rationale/span引用/confidence/severity/polarity/provenance），不传控制流（AssumptionMiner 五组件、DecomposeRL trace、SummaC pair matrix 三例同构）。
2. **三态语义**：{accept, reject, **abstain**}，弃权≠否决且聚合含弃权时必须告警（Viva La Vida 的惰性验证器教训：fail-closed×unanimity=永远拒绝且静默）。
3. **分级保证**：sound 模块（规则/SAT/SMT）给硬保证、heuristic 模块（NLI/LLM）给软信号，融合层负责折算两级的证据强度（LLM-Modulo 的 soundness来源论）。
4. **融合戒律**：朴素平均通常无效甚至有害（RaRE 0.307<0.338；MCP-MAS 全判fake）；有效成分=可靠性加权（NB对数似然/误分类率倒数）+置信度（logprob逆方差）+分歧处理（drop/弃权）；元学习融合器吃数据，小样本用解析权重（HybridFC BD集过拟合 vs B2解析权重稳定）。
5. **归因协议三件套**：leave-one-out 必要性（DecomposeRL，OOD增益最大项）、因果恢复（ROME clean/corrupt/restore）、干预忠实性（CoT截断/注入错误）——全部可操作、全部有先例可引。
6. **两阶段训练**：先独立达标再学组合（AdapterFusion 15/16≥ST-A且11/16>MT-A）；免训练组合在低资源下优势放大（MoMa 10-shot）。
7. **反馈闭环**：critique→backprompt→**局部**重生成（LLM-Modulo 过滤已否决值 21%→36%；AssumptionMiner 只重生成受影响区域）——检测系统的输出应是"可修复的定位"。
8. **先单元测试再端到端**：模块各自在被测环境单测（GPTScan 每步中间产物审计、MOSAIC 的分模块 episode 测试，摘要级）后再跑 e2e——评测章节的结构建议。

---

## 如何用模块化思维强化我们的论文（具体建议）

**R1. 形式化升级（写作层面，零实验成本）**：用 ModularDL 综述的四维分类法把 ACDD 写成"modular verification system 的一个实例"：计算=异构验证器（符号+神经）；路由=固定（规则覆盖）+可学习（裁决器）；聚合=融合元层；训练=后置冻结。Related work 有了坐标系，novelty 有了语言。

**R2. Module Contract（设计层面）**：给 L0/L1/L2 各写显式契约：输入schema、输出verdict+evidence+confidence、保证等级（sound/soft）、弃权语义、失败行为（超时/解析失败→ABSTAIN）。把"可组合性"从口号变成可检验性质：模块替换实验（见R8）。

**R3. 层间互补性量化（新实验）**：移植 FrugalGPT 的 MPI：P(L_i判对∧L_j漏检) 矩阵 + 成本-质量Pareto曲线（每层token/延迟）。证明级联增益来自**互补**而非堆叠——这是级联论文的"为什么有效"章节。

**R4. 消融即归因（新实验）**：leave-one-out necessity per 规则/锚点/通道（DecomposeRL 协议）：对每条裁决，移除某输入→verdict是否翻转→模块必要性分布图。DecomposeRL 证据（OOD −4.8）预示这信号对域外最有价值，正好接我们的多文档OOD评测。

**R5. 融合层消融表（新实验）**：naive平均 / NB解析权重（B2, B5）/ 置信加权（B1）/ 三态弃权（B4）四栏对比——已有三篇先例的失败案例垫底（平均必败），我们的改进自带文献对照。

**R6. 管线忠实性审计（新实验）**：C1 协议移植：破坏 L0 锚点/注入错误实体/截断证据→L2 裁决翻转率。回答"级联是真分工还是黑箱旁路"——审稿人必问。配 ROME 式单点恢复实验定位错误层。

**R7. 证据链可审计性（系统层面）**：每条输出附 EvidenceRecord（含 polarity/provenance/依赖verdict）+ 依赖图；人工抽查审计成功率作为指标（B4 的 polarity 丢失=我们必须避免的具体失败模式）。

**R8. 模块替换/升级实验（新实验）**：冻结其余层，换 L2 NLI 底座（mDeBERTa↔Erlangshen↔LLM）或换 L1 规则子集，报告端到端 delta 与再校准成本（AdapterFusion 的增量加任务、MoMa 的免训练组合、DAM 的热插拔是三个先例）——"模块化红利"的直接证明。

**R9. OOD局部更新（新实验）**：留出文档域，只更新单模块 vs 全量微调（综述的局部更新论点 + MoMa few-shot 证据）——军标场景"新军种文档快速适配"的故事。

**R10. 失败模式分析章节（写作层面）**：借 Viva La Vida 的三失效模式（弃权塌缩/分歧即信号/极性丢失）+ E3 的复合缺陷警告 + E4 的两步误差传播反例，展示我们的协议如何逐一规避——把"我们知道哪里会坏"写成贡献。

---

## 可从模块化角度包装的创新点（10个）

| # | 创新点 | 文献锚点 | 强度 |
|---|---|---|---|
| IP1 | **保证分级的级联验证**（sound L1 硬保证 + heuristic L2 软信号 + 融合层折算），每条输出带保证等级标签 | LLM-Modulo（保证来源论）+ E1（DO-178C强制项） | ★★★ |
| IP2 | **三态裁决协议**：{通过/否决/弃权}，弃权≠否决、分歧路由人工、含弃权聚合实时告警——军标审计天然需要"不可判定"类别 | Viva La Vida（反面）+ B1（drop-on-disagreement正面） | ★★★ |
| IP3 | **学习型级联路由**：FrugalGPT 式逐层接受阈值 + 成本-质量Pareto（成本感知的验证深度分配） | A1 + MPI度量 | ★★ |
| IP4 | **消融式错误归因**：leave-one-out必要性 + clean/corrupt/restore因果干预→"每个结论都能回答'哪一层决定了它'" | DecomposeRL + ROME + C1 | ★★★（横跨方法与分析） |
| IP5 | **EvidenceRecord 标准**：可审计证据链 schema（polarity/provenance/依赖verdict/span引用） | AssumptionMiner + Viva La Vida | ★★ |
| IP6 | **异构验证器解析加权**：误分类率导出 NB 对数似然权重（22条旧gold即可估计）+ 排序复核队列交付 | B5 + B2 | ★★ |
| IP7 | **依赖图上的局部重验证**：改一个锚点只重跑受影响条目（增量验证，16份大文档迭代修复的成本故事） | AssumptionMiner 增量重生成 | ★★ |
| IP8 | **粒度工程**：条目级任务×句级NLI模型的粒度错配诊断与 pair-matrix 聚合解法 | SummaC | ★★ |
| IP9 | **模块热插拔的域适应**：冻结级联+领域模块（军种/文档格式变体）按需挂载 | DAM + MoMa + AdapterFusion | ★★ |
| IP10 | **检测-定位-修复闭环**：矛盾→结构化critique→backprompt局部修复建议（输出从标签升级为可执行定位） | LLM-Modulo backprompt + A3过滤已否决值 | ★★★（系统贡献） |

优先级建议：IP1/IP2/IP4/IP10 构成主干（架构+协议+归因+闭环），IP5/IP7 是系统差异化，其余按实验预算取用。

---

## 论文骨架建议（模块化视角）

```
1  Introduction
   1.1 军标SRS一致性校验：审计性与可解释性是一等公民（引E1/E3：LLM单独不可信）
   1.2 贡献：保证分级的模块化级联 + 三态裁决 + 消融式归因 + 检测-定位-修复闭环
2  Background: Modular Verification Systems
   2.1 四维分类法定位（计算/路由/聚合/训练）——我们的坐标
   2.2 Module Contract 形式定义（接口/保证等级/弃权语义/失败行为）
   2.3 与级联/集成/管线三传统的区别（FrugalGPT=同质cascade；HybridFC=并行集成；我们=异构分级cascade）
3  The ACDD Architecture（L0/L1/L2 作为契约化模块）
   3.1 L0 证据抽取 → EvidenceRecord
   3.2 L1 符号层（sound critic）：规则库+Z3，覆盖=召回优先（GPTScan式）
   3.3 L2 残差层（heuristic critic）：NLI/LLM 只接 L1 弃权子流（精度优先）
   3.4 粒度工程：条目-锚点对齐解决NLI粒度错配（SummaC锚点）
4  Fusion & Adjudication
   4.1 可靠性加权（NB解析权重）+ 置信加权 + 分歧处理
   4.2 三态裁决与人工路由（弃权≠否决）
5  Attribution & Audit
   5.1 leave-one-out必要性（每模块/每规则）
   5.2 因果干预忠实性（截断/污染/恢复）
   5.3 依赖图与局部重验证
6  Experimental Setup（按"单元测试→端到端→消融→OOD→成本"五段式）
   6.1 模块级单测（各层在金标子任务上）  6.2 端到端与基线（E2E LLM对照，等预算）
   6.3 消融：逐层去除/融合变体/路由阈值  6.4 OOD（留出文档域+局部更新）
   6.5 成本分析（每层token/延迟/调用）+ Pareto
7  Results & Analysis（含失败模式分析：弃权塌缩/误差传播/复合缺陷）
8  Related Work（五角度：级联系统/验证器集成/错误归因/模块化训练/NLP4RE）
9  Discussion & Limitations（HITL定位[E3]；模块复合风险；路由稳定性）
```

---

## 与已有调研的关系

- 与 `cascade_innovation_expansion_survey.md` 的分工：该报告解决"级联的**退出与校准**"（conformal/语义熵/双模式退出），本报告解决"级联的**模块化理论、融合、归因与训练**"——IP1/IP2/IP4/IP10 与其 CP-退出创新点正交可叠加。
- `nlp4re_llm4re_comprehensive_survey.md` 已覆盖 RE 域 LLM 应用面；本报告 E 角度只保留与"模块化验证"直接相关的 5 篇并全部给出方法级细节。

## 参考文献（arXiv ID 速查）

- 2305.05176 FrugalGPT | 2308.03314 GPTScan | 2402.01817 LLM-Modulo(ICML24) | 2411.14484 LLM-Modulo技术评测 | 2302.11529 Modular DL综述
- 2605.27858 DecomposeRL | 2610.21179 RaRE | 2508.10143 MCP-MAS(SYNASC25) | 2409.06692 HybridFC(ISWC22) | 2610.04829 Viva La Vida | 2609.10316 LLM集成需求生成
- 2307.13702 CoT Faithfulness | 2202.05262 ROME(NeurIPS22) | 2401.06102 Patchscopes(ICML24) | 2606.28358 HowLLMsCite(ECIR26) | 2607.22898 AssumptionMiner
- 2005.00247 AdapterFusion(EACL21) | 2502.15483 MoMa(ICLR26) | 2302.06321 DAM(EACL23)
- 2405.00163 SAT需求矛盾(SE24)* | 2111.09525 SummaC(TACL22) | 2609.03230 TwoTruths* | 2306.08872 FICLE(ECML-PKDD23) | 2610.10628 Agent4RE(ASE@POVC26)
- 2402.18796 MOSAIC(CoRL24，摘要级，模块单元测试先于e2e的案例) | NASA FRET / Easterbrook&Nuseibeh 1996（知识性引用，未核验原文）

*仅摘要级精读（无全文HTML）。
