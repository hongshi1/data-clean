# 五方向方法调研与CascadeVerify v2方法设计

> 调研日期：2026-10-22 | 服务对象：40项校验体系 + 三层级联架构（当前refute召回1/8是核心瓶颈）
> 方法：arXiv全文HTML精读（方法节逐段）+ 检索验证。**标注约定**：[全文精读]=本session完整读过方法节；[摘要级]=读过摘要+结构元数据；[既有知识]=凭领域知识描述，写论文引用前需核对原文。
> 交叉引用：`cascade_innovation_expansion_survey.md`（A-F六方向扩展调研，含CP/多粒度/跨模态）、`nlp4re_llm4re_comprehensive_survey.md`、`pair_classifier_sota_2023_2025.md`。本文档聚焦用户指定的A-E五个新方向，与上述文档互补不重复。

---

## 0. 结论速览

| 方向 | 核心发现 | 对我们的直接价值 |
|---|---|---|
| A 结构化文档验证 | MiniCheck证明"从真实文档合成对比训练数据"可让770M小模型达到GPT-4级；表格→NLI的通用做法是"表格操作变换+聚焦视图"，不是拍平 | L1证据编译器 + NLI训练数据来源 |
| B E1模板/异常流 | **2023-2025文献空白**：无人做过用例表E1异常流模板提取与一致性检测（已检索arXiv多个查询式，无直接命中） | 空白=论文创新点；用经典对齐算法+我们的表格资产自建 |
| C NLI域适配 | Auto-GDA给出无标注域适配完整配方（合成+弱标签+选择目标函数），MiniCheck给出合成对构造法；**但都是二分类，refute/NIE不分离** | 我们的三态任务恰好是该空白：证据侧扰动→sound refute标签，证据删除→sound NIE标签 |
| D 学习型路由 | FrugalGPT评分函数=DistilBERT回归（success indicator蒸馏）；RouteLLM=偏好数据+BT胜率+阈值α，小规模in-domain数据(2%)即可大幅提升OOD | 异构验证器路由的训练配方与指标体系（PGR/APGR/CPT） |
| E 军事/安全关键 | 工业界（NASA FRET、DO-178C）走"受控自然语言→时序逻辑→SAT/监视器"路线；**无人做过端到端三态NLI验证系统** | 定位差异：我们补"语义残差"层；FRETish→Z3失败模式文献为L1提供风险清单 |

---

## 1. 方向A：结构化文档验证

### 1.1 MiniCheck [全文精读] (Tang, Laban, Durrett. EMNLP 2024, arXiv 2404.10774)

**问题**：claim-document二值事实核查（unsupported/supported），要求小模型（770M）达到GPT-4水平但成本低400倍。

**方法机制（输入→处理→输出）**：

输入 = 一批人工撰写的claim（C2D方向）或真实文档（D2C方向）。输出 = (D, c, y)三值组训练数据。两条合成管线：

**C2D（claim→doc）**，5步：
1. claim分解：GPT-3.5把claim c拆成原子事实集 {a_1..a_l}
2. 原子事实扩展：GPT-4为每个a_i生成**句子对**(s_i1, s_i2)，要求"a_i被支持 当且仅当 两句信息合并"（4-shot）
3. 支持文档生成：GPT-4把所有句子"用自己的话"写成文档D，**明确要求不陈述可推导的结论** → (D, c, y=1)。这个"不许写结论"的指令是关键：强迫模型做多句合成推理
4. 非支持文档生成：从句子对中删掉一句重新生成 D'，再用GPT-4在**短上下文**上做蕴含检查验证a_i确实不再被支持（短上下文蕴含检查比长上下文准）→ (D', c, y=0)
5. 子claim增广：对原子事实集做幂集，Merge每个子集 → 对比集(contrast set)：**同一子claim被某些文档支持、被另一些不支持**，迫使模型检查claim中的每个原子事实

**D2C（doc→claim）**，4步：文档分3块→每块GPT-4摘要句(默认y=1)→分解+幂集增广→**文档-claim增广**（迭代删除文档中每个句子，用GPT-4逐原子事实重新定标签）→**跨文档增广**（用D_j块验证c_i的原子事实，构造更难的正负例）。

**训练数据规模与比例**：C2D 7,076条（负例42%）+ D2C 7,319条（负例65%）= 14K合成 + 21K ANLI困难子集（选择标准：已有蕴含模型在ANLI构造期预测错的样本）= 35K。三个骨干（RoBERTa-L/DeBERTa-v3-L/Flan-T5-L），标准交叉熵，阈值取输出范围中点0.5（不做per-dataset阈值调优，保证零样本部署）。

**评价指标**：BAcc（平衡准确率）；10个数据集统一的LLM-AggreFact基准；成本表（$0.8/GPU-hr折算）。

**关键反直觉发现**：推理期claim分解**不必要**（GPT-4 +0.3，专用模型-1.9~+1.2不等，成本×2-4）；去语境化(decontextualization)也无稳定收益。**训练期**的原子事实级对比构造才是关键。

**与40项任务映射**：
- 其"句子对合并才蕴含"= 我们的"跨表格行+正文联合判定"（TERM-03枚举、PARAM跨表）
- 其"幂集子claim增广"= 我们的answer→原子claim分解的**训练数据**版本（answer_structure.py已有推理版）
- 其"删句→重新验证"= 我们NIE样本构造的直接模板（见§6）
- **缺口**：MiniCheck把contradiction和neutral都折叠成unsupported（footnote 2明说"contradictions are rare in our benchmark"）。我们的任务refute/NIE必须分开——这是可发表的增量

### 1.2 Chain-of-Table [全文精读] (Wang et al. ICLR 2024, arXiv 2401.04398)

**问题**：表格推理时CoT用自由文本承载中间步骤，表格语义丢失。

**方法机制**：表格本身作为推理链的中间状态。三个LLM调用循环：
1. `DynamicPlan(T, Q, chain)`：给定当前表T、问题Q、已执行操作链，从操作池采样下一个操作f（5个原子操作：f_add_column / f_select_row / f_select_column / f_group_by / f_sort_by——全部来自SQL/DataFrame惯例）
2. `GenerateArgs(T, Q, f)`：正则约束下生成f的参数
3. 程序化执行f更新T；LLM生成[E]结束标签后，用最终T+Q做最终Query

贪心搜索（不用self-consistency），查询次数比Binder少50%、比Dater少75%。TabFact 86.61%（PaLM2）。操作链长度分布：多数样本2-4步。**大表(>4k token)上优势最大（+10.25）**。

**与40项任务映射**：GJB表格（能力表/用例表/接口表/数据表）进NLI前先做**确定性表格操作**：按需求ID选行（f_select_row）、投影到answer声称的属性列（f_select_column）、值域聚合（f_group_by）。我们的L1符号层就是这些操作的确定性子集；L2残差可用LLM规划的Chain-of-Table版本。**"聚焦证据视图"（focused evidence view）概念直接采纳**——每个原子claim配一个最小表格视图，矛盾信号不再淹没在整表文本里。

### 1.3 ContractNLI系 [摘要级+既有知识]

**ContractNLI原始任务**（Koreeda & Manning, EMNLP 2021 Findings, arXiv 2110.01799）：607份合同，文档级NLI三态（entailed/contradicting/neutral）+ **证据span多标签预测**（不做start/end token回归，而是span集合的多标签分类）。难点刻画："negation by exceptions"式否定（例外条款推翻主条款）。**与我们任务同构**：(hypothesis=answer, contract=冻结证据, 三态+证据定位)。

**ContractNLI之后的新文档验证方法**（本session检索验证）：
- **CLAUSE**（arXiv 2511.00340, 2025）：7,500+扰动合同，10类异常注入，persona驱动管线生成，RAG对照官方法规验证。→ 异常注入分类学与我们的54变异算子同思路
- **Verdicts Without Annotated Evidence**（arXiv 2610.06962, 2026）：只 verdict 无证据标注的后训练——label-only训练 span F1 0.564 vs accuracy 0.896，**verdict对≠span对，两者弱相关**→ 证明"判定+定位联合评分"必要性（AVeriTeC结论再次确认）
- **Know Your Limits**（arXiv 2606.16118, 2026）：LLM/LLM+形式化/Z3求解器三范式对比，发现**scope laundering**（LLM报告solver不一致的分类却不真正执行形式推理）、implicit constraint blindness、程序合成失败三种失败模式→ 我们L1 Logic-LM管线必须输出Z3 unsat core+代码执行日志防"伪符号"
- **Breaking Bureaucracy**（arXiv 2610.06345, 2026）：开源LLM在ContractNLI/NLI4Wills上，invalid rate与温度稳定性分析
- **CPUNeSy**（arXiv 2609.37490, 2026）：神经符号推理中控制模型写入符号状态（谓词接口+证书门+弃权）→ 异构级联中"符号层输出需可验证"的实现范式
- **FICLE** [既有知识，引用前需核对]：金融域表格+文本联合claim验证（~1.4k真实claims，三态），核心发现：联合证据（表+文）验证显著难于单一模态，需要跨模态信息组合。GJB SRS的"正文+能力表+用例表"正是该设定

### 1.4 方向A小结：表格/结构化证据→NLI可用形式的三种路线

| 路线 | 代表 | 做法 | 适用我们的层 |
|---|---|---|---|
| 表格操作变换 | Chain-of-Table | 迭代选择/投影/聚合，表格=中间态 | L1确定性子集+L2残差LLM规划 |
| 证据→claim反推 | MiniCheck D2C | 从真实文档生成claim再扰动 | NLI训练数据（§6.2） |
| 结构化直译+符号 | ContractNLI span / Z3路线 | span多标签 / 约束求解 | 定位指标 / L1 Logic-LM |

**端到端三态验证系统在合同/法律文档上存在（ContractNLI+后继），但在军事需求文档（SRS+GJB）上不存在**——见方向E。

---

## 2. 方向B：E1模板匹配/异常流检测

### 2.1 文献检索结论（重要）

arXiv多查询式检索（"use case"+exception/requirements/LLM/consistency checking等）**没有找到2023-2025年任何直接做"用例表异常流(E1)模板提取与一致性验证"的工作**。相关文献散落在四条既有线上：

1. **用例规格↔用例图/序列图一致性**[既有知识]：模型驱动工程经典线（用UML状态机/行为profile做文本用例与图的比对），2023后未见NLP/LLM化更新
2. **过程挖掘conformance checking**[既有知识，经典可安全引用]（Carmona et al. 2018教材）：事件日志vs过程模型的对齐(alignment)算法——同步积上A*搜索找最小代价对齐，**这是"步骤序列比对超越编辑距离"的成熟答案**：代价矩阵可自定义（日志步/模型步/同步/隐跳），支持"最优对齐+偏差定位"
3. **需求boilerplate/模式挖掘**[既有知识]（Femmer等的需求质量线）：从需求文本中归纳可复用句法模板→我们E1模板语法的先例
4. **表格结构识别**：MinerU已解决（我们已有411块解析资产）

**判断**：E1方向是**文献空白**，且我们有直接动机资产（17个真实违例中2个是E1违例：b192/222/227 E1内容与用例主题错位、b237/242申请/释放句柄错误归属；91条QA中16条触及LOGIC-02，是R样本最集中区）。自建E1专家=论文创新点（对应project_guide待建"E1模板专家"）。

### 2.2 可借鉴的最近方法

- **Ontology-Based Process Models参数一致性** [摘要级]（arXiv 2506.16087, ETFA 2025）：SPARQL过滤取过程相关数据+期望单位标注的量纲一致性+数学表达式可求值性完备性检查。制造业过程模型。→ 三段式（过滤→单位→完备性）可平移到GJB数据表（PARAM-06单位族已有srs_kb.json）
- **序列比对算法**（经典）：Needleman-Wunsch全局对齐/Smith-Waterman局部对齐，替换矩阵用**BGE语义相似度**而非BLOSUM（步骤句嵌入cos），可定位重排/插入/删除并给出逐对齐点→LOGIC-03事件时序、表53顺序颠倒(b285/286)
- Kendall τ / 位置偏差度量：步骤号提取（正则）后纯符号，作为对齐的cheap前置

### 2.3 E1专家设计（详见§6.3组件C）

E1行模板文法（从04号SRS用例表归纳）：
```
E1 := 异常编号 + 触发条件(引用主流程步骤k / 系统状态) + 系统处置动作 + [终止/返回步骤]
```
四项检查：锚点有效性（join）、触发-主题连贯性（嵌入门+LLM复核）、处置覆盖完备性（GJB-06风格）、处置动作引用的接口存在性（TERM-07 join）。

---

## 3. 方向C：NLI域适配的具体训练策略

### 3.1 Auto-GDA [全文精读] (Leemann et al. arXiv 2410.03461, AWS AI Labs, 2024-10/2025-03)

**问题**：RAG grounding verification中，小NLI模型与真实RAG输入有~20% ROC-AUC域差；目标域无标注。

**完整训练流程（用户点名要求）**：

设定：源域有标注三元组(evidence, claim, y)；目标域只有J个**无标注**(e, c)样本（我们=91条QA对+冻结证据）。二分类（entailed vs 非entailed）。三个工具：生成器G（LLM few-shot）、变异器M（近似保标签增广）、教师T（慢但较准的打分器）。**可选极小验证集（30条）只用于超参选择**。

**Step 1 初始生成**：对目标域每个唯一evidence e，few-shot提示G(e, 目标域示例claims, ŷ)生成合成claim，ŷ由提示意图决定（ŷ=1只写有依据事实；ŷ=0混入无依据信息）。教师打初始确定性 r^(0) = T(e, ĉ)。

**Step 2 保标签增广**（3种）：LLM部分改写（随机mask 20%词让Claude Haiku填空保义）；T5整句改写（禁止5-gram以上重复）；**句子删除**（删一句应保持蕴含——只减信息）。**核心技巧=逻辑传递性的确定性更新规则**：
```
r^(i+1)(e, c') = r^(i)(e, c)·T(c, c') + (1−r^(i)(e, c))·(1−T(c, c'))
```
即通过"父claim与变异claim的蕴含概率"传播置信度——因为NLI模型在claim-claim相似对上（PAWS/MNLI风格）比在长evidence-claim对上可靠得多。**短上下文蕴含检查更准**与MiniCheck Step4结论互相印证。

**Step 3 样本选择**（离散优化）：从增广池L中选K个最小化
```
L_tot = Σ [ d(ĉ, c_min)² + λ_d·LDiv(r, ŷ) − λ_u·CE(f(e,ĉ), ŷ) ]
```
三项：与目标域最近claim的嵌入距离（分布匹配）+ 标签不确定性惩罚（r与ŷ不一致则高惩罚）− 模型效用项（当前模型f在这些样本上的交叉熵——**专门选模型还不会的**）。该目标=增强分布匹配目标（附录B证明≈KL散度−期望效用）。greedy选top-K，迭代2轮。合成数据规模=目标数据1.3-2×。

**结果**：DeBERTa-v2闭掉96%域差，达GPT-4o级ROC-AUC（0.878 vs 0.883），推理时间1/10；**学生超教师**（4个数据集中3个）；自我蒸馏（DeBERTa当教师）平均+0.15 AUC。消融：纯few-shot提示=84%差距闭合；**随机选增广样本反降**（71%）；完整Auto-GDA=96%——选择准则是关键。

**与40项任务映射**：我们无gold（silver S6/R8/N77非gold），Auto-GDA配方完全适用：91条(Q,A,E)当无标注目标分布；教师=GLM-5.3/API LLM（走algorithms/llm_client.py缓存接口）；学生=mDeBERTa/Erlangshen（models/nli/本地资产）；30条验证集超参扫描。**改造点**：合成目标从二元改三态（见6.2）。

### 3.2 MiniCheck合成策略（方向A已详述，此处补对比）

| 维度 | MiniCheck | Auto-GDA | 我们需要的 |
|---|---|---|---|
| 合成起点 | 人工claim/真实文档 | 目标域无标注(e,c) | **冻结证据块**（411块+16文档） |
| 标签来源 | 构造性（删句/删原子事实） | 提示意图+教师过滤 | **构造性算子（sound）** |
| 类别 | 二元 | 二元 | **三态** |
| 难例机制 | 幂集子claim+跨文档 | 选择目标函数+迭代 | 两者并用 |
| 规模 | 14K+21K ANLI | 目标域1.3-2× | ~5-10K三态 |

### 3.3 其他相关 [摘要级]

- **GNLI**（Hosseini et al. 2024，Auto-GDA相关工作节提及）：LLM两步合成跨域NLI（先生成目标域再prompt-tuned生成语句）——多样化域生成路线
- **CCHD**（arXiv 2606.08158, ICASSP 2026）：把改写一致性变成**约束优化**——改写视角间散度约束+标签保持约束，梯度下降-上升解拉格朗日乘子，零推理开销，超MiniCheck/AlignScore→训练数据确定性控制的另一路线
- **FISCAL**（arXiv 2511.19671, NeurIPS'25 GenAI4Fin workshop）：金融数值claim合成管线训练MiniCheck-FISCAL（770M级）达GPT-4o/Claude-3.5级——**域特定合成数据+小模型**在垂直域的又一成功例证，与我们"军标域小NLI"定位完全平行
- **HalluGuard**（arXiv 2510.00880）：FineWeb合成+ORPO偏好微调蒸馏推理到4B，证据接地justification输出——可解释性输出的近例
- **ThinknCheck**（arXiv 2604.01652）：1B先生成结构化rationale再verdict，监督推理优于CoT/偏好优化

**结论**：域适配三配方齐备（合成+选择/构造性对比/约束一致性），**三态分离无人做**——MiniCheck明确折叠contradiction、Auto-GDA二元、FISCAL二元。我们answer-refute检测失败的根因（NIE坍缩掩盖refute）恰好卡在这个空白上。

---

## 4. 方向D：级联验证系统的学习型路由

### 4.1 FrugalGPT [全文精读] (Chen, Zaharia, Zou. arXiv 2305.05176, 2023)

**评分函数怎么训练**（用户点名问题）：
- g: Q×A→[0,1] 回归"该答案是否正确"的**success indicator**。实现=**DistilBERT改造的回归模型**，在训练集的(query, LLM生成的answer, 答案是否正确)三元组上监督训练——正确性标签来自训练集gold（把每个LLM在训练查询上的输出与gold比对）。评分器本身比所有LLM便宜
- 级联：有序LLM列表L=(f_1..f_m) + 每级阈值τ_i。query先到f_1，若g(q, f_1(q))≥τ_1返回；否则升级。例：GPT-J(τ=0.96)→J1-L(τ=0.37)→GPT-4
- **(L, τ)的学习=约束优化**：max E[r(a, f_Lz(q))] s.t. E[cost]≤b, z=argmin{i: g≥τ_i}。混合整数规划，用专门优化器：(i)剪枝——答案分歧小的LLM列表忽略；(ii)在少量样本上插值近似目标。省成本最多98%（HEADLINES）
- MPI分析：廉价模型对昂贵模型的最大互补率（GPT-4错而GPT-J对≈6%）——**级联收益上限的存在性证明**

**映射**：我们的g=验证器可靠性预测器，输入(q,a,e,检测项特征)，输出"该验证器此判定正确的概率"，训练标签来自合成数据+silver的交叉验证。

### 4.2 RouteLLM [全文精读] (Ong et al. ICLR 2025, arXiv 2406.18665)

**路由器怎么学习**（用户点名问题）：

1. **偏好数据**：Chatbot Arena 80k对战→按Elo动态规划聚成10个tier缓解标签稀疏（任意两模型对比标签<0.1%）→tier0-1=强、tier3=弱；**丢弃模型回答只留模型身份**（路由发生在回答之前）
2. **数据增广**（关键发现）：gold标签数据（MMLU验证集~1500条，仅占训练量2%）→ MMLU路由大幅提升；LLM-judge标签数据（Nectar+GPT-4判官，120k，$700）→ MT Bench/GSM8K大幅提升。**小规模in-domain数据决定OOD表现**
3. **四种路由器参数化**：
   - 相似度加权BT（免训练，推理时解）：ω_i=γ^(1+S(q,q_i))指数权重(γ=10)的Bradley-Terry系数ξ，P(win)=sigmoid(ξ_w−ξ_l)
   - **矩阵分解**（最优）：评分函数双线性 s(M,q)=w2ᵀ(v_m ⊙ (W1ᵀv_q+b))，BT胜率P(win_Mw|q)=σ(s(M_w,q)−s(M_l,q))；8GB GPU 10 epochs
   - BERT分类器（CLS+sigmoid）；因果LLM分类器（Llama-3-8B，标签词表扩展，next-token预测）
4. **决策=阈值α**：R(q)=strong iff P(win_strong|q)≥α。扫α得成本-性能曲线
5. **指标**：PGR=(r(R)−r(weak))/(r(strong)−r(weak))；**APGR**（PGR对强模型调用比例的积分，即曲线下面积）；CPT(x%)=达到x% PGR所需最小强模型调用比。低数据量下高容量路由器(BERT/LLM)反而差于随机；增广后反超
6. **换模型对不重训仍泛化**（Claude3-Opus/Llama-3-8B上保持）→路由器学到的是"问题难度"而非特定模型记忆

**映射到异构验证器路由**（无人做过，=我们的C4升级）：
- 强模型↔LLM复核通道；弱模型↔规则+NLI通道。偏好对=同一(实例,检测项)上两通道的判定对错比较（合成数据上免费获得：构造性标签为gold）
- 路由特征：检测项ID、claim kind（数值/标识符/枚举/结构/语义）、证据模态、L0对齐状态、L1规则命中数、NLI概率、不确定度
- 目标改写：max **refute召回** s.t. E[LLM调用成本]≤B（比RouteLLM的对称PGR更贴我们痛点——refute是1/8召回的瓶颈类）
- 指标移植：PGR(refute)/APGR/CPT(refute-recall@budget)

### 4.3 相关 [摘要级]

- **CPUNeSy**（2609.37490）：符号状态写入控制+证书门+弃权路由——"弃权有代价时路由到未认证回退"与级联的人工审阅通道设计同构
- 项目已有A9/LYNX/CovNav（cascade_innovation_expansion_survey.md）的conformal提前退出线——与学习型路由正交可叠加

---

## 5. 方向E：军事/安全关键文档验证的实际系统

### 5.1 NASA FRET生态 [摘要级×8篇，链条完整]

- **核心范式**：受控自然语言FRETish（结构化NL：scope/component/condition/timing四槽）→自动翻译LTL/MTL→接Spot/Z3/模型检查。**PVS形式语义已证明翻译等价**（Conrad et al. arXiv 2201.03641）
- 工业闭环：FRET→Ogma→Copilot生成C99硬实时运行时监视器（ICAROUS无人机/ROS2，arXiv 2209.14030、2012.03745）；飞机发动机控制器案例（arXiv 2112.04251，Luckcuck等）
- 2023-2026演进：需求**重构**保持语义等价（Spot等价检查，2202.05816）；太空机器人需求模式目录（2511.14438）；**FRET 3.0概率需求**→PCTL翻译+自动验证框架（Mavridou et al. arXiv 2512.15788，2025-12）；"Coherency through formalisations"（2605.10462）**在检验NASA自家FRETish→MTL翻译时发现了不一致**并提出替代翻译（模型检查证明等价）
- **启示**：(a) "受控语言+可证翻译"是工业界需求形式化的标准答案，我们GJB层=发现"条款缺失"（有无检查）而非形式化全量条款——定位互补；(b) 连NASA的翻译器都有不一致——我们的L1输出必须带unsat core/执行日志（与Know Your Limits的scope laundering警告一致）

### 5.2 DO-178C/航空 [摘要级]

- **SAT求解器做HLR矛盾检测**（Yatkın & Ovatman, arXiv 2405.00163, 2024）：数据字典→高层需求转逻辑表达式→SAT查矛盾，显著省评审时间。**=我们L1 Logic-LM的直接先例**（DO-178C明确要求需求一致性为强制验证目标）
- GPT-4为保证案例生成defeaters（arXiv 2401.17991）：LLM反驳论证生成能力评估
- 跨域一致性（2608.28156, DASC 2026）：ARP-4754B/DO-178C下系统域↔MBD域↔嵌入软件域的**仓库中心CI+关系型接口数据库**，自动化一致性检查在代码生成前暴露不一致→"接口ID双登记"（TERM-07）的工业对应物
- DO-178C typed-edge需求语料上的多跳追溯RAG三重稳健性分析（2608.00705）：GraphRAG引用精度0.12-0.23、faithfulness随跳数崩塌、单judge自κ=0.137——**LLM直接验证的不可靠证据**（支持我们"LLM只做被路由的残差"）
- LLM生成代码MISRA C++合规性（2506.23535）：所有主流LLM都不合规——安全关键域LLM定位=辅助非替代

### 5.3 军标NLP/ML先例

[既有知识] 公开文献中军标（GJB系）合规检查的NLP/ML方法**几乎没有**（中文核心期刊有零星GJB 438文档模板化检查，非ML）；最接近的是DO-178C线（上述）。**"NLP/ML做军标文档一致性三态校验"在公开文献是空白**——数据集（16份真实GJB SRS+91官方QA+17真实违例）本身即贡献（C5）。

### 5.4 Siemens等工业界 [既有知识]

Siemens需求质量线（ReqAnalyzer/RQA工具族）：语法模式+质量规则（如无歧义量词、可验证动词），规则库=我们GJB 120条规则的平行物；2023后有LLM增强版（工程博客/白皮书级别，学术发表少）。NASA FRET是学术可见度最高的工业系统。

---

## 6. 科研方法设计方案：CascadeVerify v2

### 6.1 问题形式化

**实例空间**：X = Q × A × E，其中E=冻结证据块集合（doc04: 411块；每块b有类型type(b)∈{text,table,image,list}与结构化载荷payload(b)）。

**输出**：Y = {S, R, N}（support/refute/NIE）× ℓ（证据定位：块ID+行/span）× j（justification：触发规则ID或推理trace）。

**判定语义**（关键设计决策）：
1. answer分解为原子claim集 Decomp(A)={a_1..a_m}（answer_structure.py已有）；
2. claim级三态：y_i = V(a_i, E(a_i))，E(a_i)=a_i的聚焦证据视图（§6.3）；
3. **聚合规则**：∃i: y_i=R → 整体R（任一矛盾即驳回）；否则∀i: y_i=S → S；否则N。开世界假设：证据内找不到≠文档内不存在（A1检索协议同理）。

**40项检测任务**：T={τ_1..τ_40}（taxonomy v3），每项绑定(cross_modal_pair, 算子集Op_τ, 适用性探针)。检测项=先验路由信号而非独立分类任务（40项→验证器类型/规则族的映射）。

**级联结构**：
```
(x, τ) → L0 实体对齐(NER+链接+NIL) → L1 符号验证(确定性专家族) → L2 残差三态NLI(域适配) → L3 LLM仲裁(被路由)
        每层输出: (y, ℓ, j, conf)   停止条件: 确定性判定 | 校准置信 | 预算
```
残差集定义（C1，保持）：R = {(a,E) | L0对齐成功 ∧ L1规则未触发 ∧ L1不可形式化}。

### 6.2 组件A：证据编译器与三态合成训练数据（对应方向A+C，核心创新）

**证据编译**（确定性，Chain-of-Table操作的符号子集）：
- 表格→关系模式：能力表(ID,需求描述,方式,运行状态,任务书映射)、用例表(名称,Actors,前置,主事件流[],E1[],后置)、接口表(接口ID,方向,数据元素[])、数据表(参数, min, max,精度,单位)、追溯表(需求ID↔任务书ID)、合格性表(需求ID,方法)
- 聚焦视图：给每个原子claim a，按其claim-kind投影：数值claim→(参数行, min/max/精度/单位列)；枚举claim→(正文枚举句, 表成员列)；标识符claim→(ID列全集)。**视图=claim与证据的最小对**（解决"矛盾信号淹没"）
- 图（48张）前置：接口图/功能框图→VLM解析为实体+边（现有matcher资产），进图-文join

**三态合成数据生成（EGT: Evidence-Grounded Tri-state synthesis）**——把MiniCheck的构造性对比+Auto-GDA的选择框架推广到三态：

```
输入: 冻结证据单元e (块/表行/图), 算子库 Op (现有54个×5线路), 教师=LLM(缓存接口)
S样本: a = Verbalize(e, style=91条QA的answer风格)   [LLM生成, 教师过滤 r≥ρ_s]
R样本: a = o(a)   o∈Op_flip (值交换/ID交换/集合删元/顺序重排/单位替换...)
        标签sound: o的翻转语义已知 → 无需教师验证 (MiniCheck无此优势)
        或 e' = o(e), (e', a) 同样sound
N样本: (e \ span(e,a), a)   删除a的支持span/行/句 (MiniCheck D2C step3)
        语义: e中a不可判定, 但a未与e矛盾 → NIE (与我们冻结证据协议精确同构)
困难N样本: a = Verbalize(e ∪ e'), e'为同文档相关块 → (e, a)需要跨块信息→N
比例: S:R:N ≈ 1:1:1 训练期 (修复NIE坍缩的先验), 评测期按真实分布
选择目标 (Auto-GDA式): L_tot = d(â, A_target)² + λ_d·LDiv(r, ŷ) − λ_u·CE(f_θ(e,â), ŷ)
        d=嵌入距离, r=教师确定性, f_θ=当前学生(本地mDeBERTa/Erlangshen)
        + 三态约束: R样本构造性标签 → LDiv项置0 (sound标签不过滤)
规模: 16份SRS × 块级采样 ≈ 5-10K; 验证集=91条中抽30条只调超参
```

**理论卖点**：MiniCheck/Auto-GDA/FISCAL全部二元；三态分离需要**refute与NIE的构造性区分**——证据侧扰动(矛盾)vs证据侧删除(不可判定)——这是我们用已有54算子资产免费获得的、文献没有的东西。**残差NLI只在R集上训练**（C1残差训练范式：L0/L1已判定的样本不进训练分布，防止NLI学会"抢答"符号层的活）。

### 6.3 组件B：结构专家族（L1，对应方向A符号路线+B空白）

| 专家 | 检测项 | 机制（输入→输出） |
|---|---|---|
| ID join | TERM-07 | ID列↔ID列精确/前缀/模糊join→双向覆盖+冲突→违例+单元格定位（b220/225等5个真实违例可测） |
| 集合运算 | TERM-03 | 正文"包括"枚举句parse vs 表成员列→对称差→缺失/多余+span定位（b032/b035） |
| 区间算术 | PARAM-03/06/07 | (min,max,精度,单位)→区间包含/交空/量纲换算(srs_kb单位族)→Z3算术约束 |
| 数值聚合 | PARAM-01/05 | 跨表数值→Z3求和/比例约束（Logic-LM式程序合成，输出unsat core） |
| **E1模板专家** | LOGIC-02/06 | §2.3四项检查：锚点join(确定性)+主题连贯(BGE门+LLM确认)+处置覆盖+接口存在join |
| **序列对齐专家** | LOGIC-03 | 步骤句嵌入→Needleman-Wunsch(替换矩阵=BGE cos, gap罚分)→对齐分数+偏差定位; 步骤号提取→Kendallτ前置 |
| 追溯join | GJB-05 | 表81↔表82双向join→正逆矛盾（b407/408真实违例） |
| 覆盖完备 | GJB-06/04 | 合格性表覆盖3.3~3.17章节↔章节存在性；审计/掉电/升级条款↔GJB封闭清单有无检查 |
| GJB有无 | GJB-01~11 | 120条规则库OCR行号锚定的封闭清单成员检查→{缺失,存在}+规则ID+行号 |

L1输出协议：`(y, cell_ref, rule_id, gjb_ocr_line)`——每条可回溯到GJB标准OCR行号（已有knowledge/gjb_438c_rules_full.json）与证据单元格；Z3类必须附程序+求解日志（防scope laundering，Know Your Limits教训）。

### 6.4 组件C：路由与退出（对应方向D）

**异构路由器**（FrugalGPT评分+RouteLLM决策的组合）：
```
验证器通道 V = {v_rule(L1), v_nli(L2), v_llm(L3), v_human}
特征 φ(x,τ,a) = [检测项ID, claim-kind, 证据模态, L0状态, L1命中数, NLI三态概率+熵, 算子签名]
路由器 ρ(φ) = P(v判定正确 | φ)  — FrugalGPT式success indicator, DeBERTa-mini级
级联顺序: 按成本 v_rule → v_nli → v_llm; 阈值 τ_1, τ_2, τ_3
判定: 首个 P ≥ τ_i 的通道判定生效; 否则弃权→v_human
训练数据: 合成EGT(构造性gold) + silver 91条(交叉验证标签)
学习: max RefuteRecall s.t. E[cost(x)]≤B   (B=LLM调用预算)
     τ_i扫描 + 贪心; 或Dinkelbach分数规划
指标: RefuteRecall@B 曲线, APGR-analog, CPT-analog(达到目标refute召回的最小LLM调用比)
```
**校准退出**（叠加项目已有CP线）：L2 NLI概率过split-conformal；预测集单例→机器判定；非单例→按规则升级人工。P(误报)≤α保证（A7/A8风险：难例集合过大→正好落弃权通道）。

### 6.5 实验设计

**数据**：
- 训练：EGT合成（§6.2）+ 残差过滤
- 评测主集：91官方QA（5-fold，silver标签上GLM-5.3复核作为主标签+人工抽检）
- 评测refute专项：17真实违例转化集（real_observed）+ 变异注入集（54算子×91 QA，受控测量；沿用mutation_master_plan协议）
- 证据定位gold：91条+17违例标注(块ID,行/span)（AVeriTeC式判定∧定位联合评分）

**Baselines**（B0-B5+我们）：
| ID | 系统 | 说明 |
|---|---|---|
| B0 | majority-NIE | 坍缩基线（当前B2/B3现象） |
| B1 | 零样本本地NLI | mDeBERTa/Erlangshen直推（现状） |
| B2 | LLM直推三态 | GLM-5.3/GPT-4o单次prompt（成本上限参照） |
| B3 | MiniCheck式二元 | 二元合成+阈值（无三态） |
| B4 | ContractNLI式 | span多标签+三态头（文献最近邻） |
| B5 | 纯符号 | L1全开无NLI |
| Ours | CascadeVerify v2 | 全组件 |

**消融**：
1. −构造性R样本（R样本全由prompt生成+教师过滤）→ 验证sound标签价值
2. −证据删除N样本（N=随机采样）→ 验证NIE构造性
3. −聚焦证据视图（整块拍平）→ 验证证据编译
4. −残差训练（NLI在全分布训练）→ 验证C1
5. −路由（固定顺序固定阈值）→ 验证学习路由
6. −选择目标（Auto-GDA消融复制：随机选择增广样本）
7. −E1专家（LOGIC-02交给NLI）→ 验证结构专家必要性
8. 三态→二元折叠（MiniCheck式）→ 验证三态贡献

**指标**：
- 主：三态macro-F1、**refute召回**（头条指标，当前1/8）、BAcc
- 定位：AVeriTeC分数=判定正确∧定位正确；ContractNLI span F1
- 成本：RefuteRecall@LLM预算曲线、APGR/CPT-analog、推理时延
- 校准：ECE、conformal覆盖率@α
- 稳健：变异算子家族×漏检率矩阵（54算子覆盖诊断已有资产复用）

**统计**：1000次paired bootstrap，p<0.05；报告推理配置（量化/温度——CP审计A15教训）。

### 6.6 预期贡献声明（论文claim）

1. **EGT三态合成范式**：首个把构造性对比数据合成推广到support/refute/NIE三态的方法——证据侧扰动(算子sound翻转到R)与证据侧删除(到N)的分离是文献空白（MiniCheck/Auto-GDA/FISCAL均二元）
2. **残差NLI域适配**：Auto-GDA配方在军标需求文档域的首个实例+残差集专门训练（C1深化：层间可计算函数定义训练分布）
3. **E1异常流模板专家**：用例表异常流一致性检测的首个自动化方法（文献空白），含语义对齐算法（BGE替换矩阵的Needleman-Wunsch）
4. **异构验证器学习路由**：FrugalGPT/RouteLLM路由范式从(强/弱LLM)到(规则/NLI/LLM/人)异构验证器的推广，以refute召回为约束目标的成本优化
5. **GJB-SRS基准**：16份真实GJB SRS+91官方QA+17真实违例+40项taxonomy+54算子（数据集贡献）

**与最近竞品差异化**：SAGE(arXiv'26)、TSRCDF-SS(纯语义)——见project_guide 9.4表，本文档增量在EGT三态+结构专家+路由，正交。

### 6.7 风险与开放问题

| 风险 | 证据 | 缓解 |
|---|---|---|
| N标签构造的噪声（删除支持span后仍可从其他行推断） | MiniCheck用GPT-4验证N；我们span定位由编译器精确给出 | 编译器追踪span来源；教师复核低置信N |
| silver标签不可靠（91条非gold） | project_guide明示 | EGT训练不依赖silver；silver只做评测+30条超参 |
| LLM教师自身域差 | Auto-GDA表9：LLM教师不必然更好 | 教师ensemble；自我蒸馏备选（DeBERTa自蒸馏+0.15 AUC先例） |
| Z3程序合成错误 | Know Your Limits三种失败模式 | 程序+求解日志强制输出；失败→回落L2并标记 |
| 40项中7项零证据不适用 | taxonomy v3 note | 证据门控前置拦截（已有计划），评测分层报告适用子集 |
| 路由器数据稀疏（91条） | RouteLLM：低数据高容量路由器差于随机 | 路由器容量限制（矩阵分解级）；合成偏好对扩充 |
| E1模板跨文档泛化 | 16份文档模板差异 | 模板文法做成可配置+LLM few-shot抽取兜底；报告跨文档方差 |

### 6.8 实施顺序（对齐M1-M5路线）

| 步 | 内容 | 依赖 | 产出 |
|---|---|---|---|
| S1 | 证据编译器（表格schema+聚焦视图） | MinerU 411块 | E(a)编译 + span追踪 |
| S2 | EGT合成管线（复用54算子+教师走llm_client缓存） | S1 | 5-10K三态对（runs协议落盘） |
| S3 | E1/序列/追溯/覆盖专家（L1补全） | S1 | 专家族+17违例可测 |
| S4 | 残差NLI微调（Auto-GDA选择+EGT数据） | S2 | 域适配三态NLI（本地GPU） |
| S5 | 路由器+conformal退出 | S2-S4 | 成本受控级联 |
| S6 | 评测矩阵（B0-B5+消融8项+定位gold） | 全部 | 论文表格 |
| S7 | 定位gold标注（91+17） | 人工 | AVeriTeC式联合评分协议 |

---

## 附录：本session精读论文索引（方法节级）

| 论文 | arXiv | 关键机制复述（一句话） |
|---|---|---|
| Auto-GDA | 2410.03461 | 无标注域适配：few-shot合成+保标签增广（逻辑传递性置信传播r'=r·T(c,c')+(1-r)(1-T)）+分布匹配选择目标 |
| RouteLLM | 2406.18665 | 偏好数据+BT胜率+阈值α；矩阵分解双线性评分；2% in-domain数据决定OOD |
| FrugalGPT | 2305.05176 | DistilBERT回归success indicator评分+约束优化学(列表,阈值)；98%成本节省 |
| MiniCheck | 2404.10774 | C2D/D2D构造性对比合成（句子对合并蕴含/删句重验证/幂集子claim）；770M达GPT-4 |
| Chain-of-Table | 2401.04398 | 表格=推理链中间态；5原子操作动态规划贪心链 |
| ContractNLI族 | 2110.01799+5篇后继 | 文档级三态NLI+span多标签；后继：扰动基准/标签only后训练/Z3忠实性审计 |
| FRET生态 | 8篇 | FRETish→LTL/MTL+PVS语义证明+运行时监视器；FRET3.0概率化 |
| DO-178C线 | 2405.00163等6篇 | SAT做HLR矛盾检测；RAG追溯的LLM不可靠证据；跨域CI一致性 |

未决核对项（写论文引用前）：FICLE确切出处[既有知识]；TART/TabFormer细节见既有survey（project_guide 9.4已引）；Copilot-4Req确切arXiv ID[既有知识]。
