# 91. 逐claim聚合语义文献取证 + assertion-aware聚合设计规范（codesign）

> 取证日期：2026-11-16。任务：调研"N条per-fact判定→1个整体判定"的聚合语义文献（7维度），特别找"弃权(NIE)不应一票否决"的先例；给出**assertion-aware聚合**的形式化规范（断言性测试+两个聚合公式候选+风险分析+与现有三变体的关系）。
> 性质：文献取证+设计文档（只读+写作，未跑模型，未git commit，未上网）。
> 与50/88/89/90号分工：50号是**聚合变体选型的dev实验记录**（strict保默认的依据）；88号回答**验证单元**（要不要分解）；89号回答**归因单元**（定位）；90号回答**分解器实现**。本文回答**聚合语义**——单元级判定如何合成实例级判定，及"单元不是断言时聚合怎么办"。
> 口径声明：仓库覆盖的论文细节给仓库锚点；仓库未覆盖的凭知识补全并标"待核实"（沿88§7口径），未虚构。**M82 C实验/M87 D2实验的具体run记录与蒸馏切分器产出的claim样例不在仓库内**——问题定义按任务口径转述（含"添加"裸名词示例），标"任务口径输入"。

---

## 0. 一句话答案（详证见§1-§4）

1. **"弃权不一票否决"有强先例，但都不在我们这条管线上**：最直接的是**Viva La Vida**（多agent证明搜索，全体一致×fail-closed＝"永远拒绝的惰性验证器"，结论=弃权与拒绝必须是不同布尔值且聚合含弃权须告警，repo B4精读）与**VERISCORE**（2024，不可核验claim进弃权带不进分母——**前聚合成员测试**的直接先例，repo A4）；理论侧是**选择性预测**（Chow 1970拒绝选项：弃权是独立动作不是负票；Geifman & El-Yaniv 2017，repo已有引用锚点）；审计侧是**ISA审计意见三分法**（无法表示意见≠否定意见，凭知识待核实）。FActScore本身是反例——unsupported计入分母（精度导向），但FActScore→VERISCORE的演化正是"NIE入罪→可核验性门"的文献轨迹。
2. **我们的问题要拆成两种NIE，文献先例只覆盖其中一种**：**(i) 片段NIE**——claim不是命题（裸名词"添加"无谓词结构、无真值条件），NLI输出neutral是**任务伪迹**（89号Q2的标签良定义约束：无谓词的hypothesis三态标签不良定义），聚合前就该出局；**(ii) 断言性inability-NIE**——claim是真断言但通道判不了（50号的b类：L3没看到证据行），50号dev实验证明这类NIE**必须保留否决权**（dominant_70把它也豁免掉→24条假support、S精度坍到0.077、被否决）。**现有一变体对一堵墙、三堵墙对另一堵墙**：strict两堵墙都塌support；dominant_70修(i)毁(ii)被否决；no_minor_block词汇标记不命中裸名词（且全片段实例core=∅回退strict）。
3. **修复杠杆位置与50号结论一致：单元层，不是语义层**。claim侧聚合的逻辑对象是合取（answer=claim₁∧…∧claimₙ，support(合取)=∀support——50号已核实silver聚合同为strict-∀），弱化合取=制造假support；正确修法=**把非合取项（非命题片段）从合取里删掉**。这把50号的c-fix（融合键剥前缀，零副作用恢复066/069）从模式特异修复升级为有语言学依据的**断言性门（assertiveness gate）**。推荐公式：**A. assertive-filter strict**（断言集内strict-∀，片段不投票但带告警进弃权带）作域内默认候选；**B. assertive-ratio**（断言+decidable集内支持率≥τ，τ=dev校准）作crossdoc档（v3现用dominant_70）的升级替换。

---

## 1. 问题重述：两堵墙的精确定义

### 1.1 任务口径的问题（M82 C / M87 D2，仓库无run记录）

蒸馏切分器（学生模型）产出原子claim，其中混有**裸名词片段**（如"添加"——列表项标签、表头残片、动名词短语单独成条）。NLI（mDeBERTa系）对这类输入输出NIE——**注意这不是"断言无法判定"而是"输入不是断言"**：hypothesis侧无谓词结构时三态标签不良定义（89号Q2：标注协议保证标准NLI的hypothesis是完整单句；短单句是任务定义排除出的需求）。strict-∀聚合下NIE一票否决→support类塌方。

### 1.2 两种NIE的区分（本文全部设计的支点）

| | 片段NIE | 断言性inability-NIE |
|---|---|---|
| claim形态 | 裸名词/列表标签/表头残片（无谓词结构） | 完整命题（有谓词+论元） |
| NIE语义 | **任务伪迹**：标签不良定义，NLI默认neutral | 真实判定：通道能力缺口或证据投递缺口（50号b类） |
| 50号证据 | c类（9/16阻断claim，全部可确定性修，c-fix零副作用恢复066/069） | b类（077的L3判NIE，根因是语句选择没投递能力表行；**保留否决权是精度保护壳**） |
| 正确处理 | 聚合前出局（进弃权带+告警） | 保留strict否决权；修复在通道/证据投递层（P2-b） |

**关键推论**：dominant_70在dev被否决（24假support）的原因恰好是把(ii)也豁免了——它按"decidable"过滤，断言性inability-NIE（semantic_unresolved）不进分母→silver=NIE的实例里L3部分判support即翻转。而(i)片段NIE本就不该进任何分母。**现需要的是只豁免(i)不豁免(ii)的门**——这正是"assertive-filter + strict"的形状。

### 1.3 silver口径核对（50号§1，防走错方向）

silver（GLM-5.3 review）的实例级聚合同为refute>NIE>support的strict-∀（`tools/validate_final_labels.py`断言）。silver不会塌support的原因不在聚合宽松而在**claim生成干净**（GLM不产生片段claim，全corpus平均5.58条 vs 我们7.66条）。所以目标语义＝"在干净单元集上跑strict"＝**断言性门+strict**，而非任何更宽的聚合。

---

## 2. 聚合语义文献表（7维度取证）

**列定义**：聚合公式=单元判定→整体判定的合成规则（含分母定义）；弃权处理=单元级"无法判定"在公式里的地位；适配=对我们"三态开放世界NIE+claim级分解+冻结证据"管线的可迁移性。仓库锚点优先；无锚点标待核实。

| # | 方法 | 出处 | 聚合公式 | 弃权处理 | 与我们场景的适配 |
|---|------|------|---------|---------|----------------|
| 1 | **FActScore** | EMNLP 2023（repo A3【√API】） | **被支持原子比例**：FS=｜supported｜/｜全部原子事实｜，逐原子二元判定（支持/不支持）。**分母含unsupported**——判不了的原子按"不支持"计数入罪【分母细节待核实：检索无果时原子的计法原文未核】 | 弃权＝失败（精度导向：事实性度量惩罚不可核验） | **反例先例**：原子为LLM改写的命题性短句（分解prompt强制declarative，90号1.1），**没有片段问题**；其"NIE入罪"语义与我们三态分类目标错配。ChatGPT传记58%原子被支持（repo A3数字） |
| 2 | **VERISCORE** | 2024（repo A4【√API】） | **可核验性门+分母换轨**：LLM分解后先过可核验性过滤（上下文无关/客观），**只对可核验claim打分**；不可核验claim弃权带单独报告（repo A4："不可核验claim弃权；可核验claim逐条判定"、"弃权带换precision"） | **弃权＝独立带，不入分母**——前聚合成员测试的直接先例 | ★★★最高适配：我们要的门（claim-membership gate）与其同构，差异=VERISCORE的核验性是**语义判定**（LLM判上下文无关性），我们是**句法断言性**（谓词结构，确定性零模型）——定位为"VERISCORE语义门的确定性句法版" |
| 3 | **SummaC-ZS** | TACL 2022（repo E2精读） | **列max→行均值**：M×N句对蕴含矩阵，每个摘要句取列max（最强支撑），文档分=各摘要句max的均值；二值决策用校准阈值 | 证据侧弃权=低分单元：某摘要句无任何文档句匹配→其max低→**拉低均值但不一票否决**；阈值在benchmark上校准 | ★★两个可搬运件：(a) **列max=证据侧"neutral不否决entailment"**（多前提OR聚合，见维度6）；(b) 分数级均值+校准阈值≠硬票否决——**聚合的整体性来自平均+校准**。但它是二值语义无三态 |
| 4 | **SummaC-Conv** | 同上 | 每列分箱50-bin直方图→1D卷积（H=50参数）→均值——**可学习聚合器**（合成FactCC 10K子样本训练） | 学习型聚合可隐式学到"某类低分列不该一票否决"（分布形状而非单点） | ★小样本可学习聚合的先例（50参数），支持"极小融合层"可行性；但训练标签是二值一致性，无弃权语义 |
| 5 | **TRUE** | Findings NAACL 2022（repo 89号表1【待核实：仓库零精读】） | 任务重格式化为(input,output)pair整判（T5-11B），**无单元级聚合**——聚合问题被数据集粒度吸收 | 无弃权（二值） | 低：整单元直判，无三态、无聚合语义可搬；仅作"直判族无聚合"的坐标引用 |
| 6 | **MiniCheck** | EMNLP 2024（repo §1.1精读） | claim-doc二元概率，无聚合（单claim直判）；**折叠contradiction进二值**（89号判读） | 无弃权 | 低（聚合维度）；但其C2D/D2C证明分解质量决定判别器质量——片段进训练数据的教训与我们蒸馏场景同构 |
| 7 | **Chow拒绝选项** | IEEE Trans. IT 1970（凭知识【待核实】；repo method_framing L174已引"Chow规则"） | 最优识别：max后验<τ→**拒绝动作**（转更强判决器/人工），拒绝区不计错误——coverage-accuracy权衡的理论基点 | **弃权=第三种动作，非负票**——选择性预测全部后续工作的公理 | ★★★概念基座：我们的NIE在"实例级"的角色＝拒绝动作（转人工/残差），不是负票。注意粒度错位：Chow是**单分类器**的弃权；我们是**单元门**（某些claim根本不构成问题）+实例弃权两层 |
| 8 | **选择性预测** | El-Yaniv & Wiener 2010/2011（理论基础）；Geifman & El-Yaniv NeurIPS 2017（DNN版，repo technical_landscape L67、method_framing L174已引） | risk-coverage曲线；softmax响应弃权；弃权区独立评测 | 同上：弃权区不算错，算覆盖率代价 | ★★给"精度保护壳"以理论语言：strict-∀+NIE弃权=低coverage高precision operating point；聚合变体=沿risk-coverage曲线移动——**50号的24假support=coverage换risk买贵了** |
| 9 | **Viva La Vida** | arXiv 2610.04829, 2026（repo B4全文精读） | 三模型验证器**全体一致**且fail-closed（解析失败/API错=不通过）→12次验证事件10次在数学内容被读前"算术上不可能通过"——**保守错误处理×保守聚合规则=永远拒绝的惰性验证器，且对操作员静默** | 设计规则：**弃权与拒绝必须是不同布尔值**；聚合含弃权时实时告警；分歧是承重墙（Gemini 3次挡住GPT放行的open problem错误） | ★★★最直接的"弃权一票否决=塌方"事故记录：与我们strict-∀下片段NIE否决support同构（fail-closed×unanimity）。其"弃权≠拒绝+告警"规则直接进我们的公式A规范（§4） |
| 10 | **Alignment Bottleneck** | arXiv 2602.10380, 2026（repo B3） | 分解式验证的有效性前提=claim与证据span粒度对齐；不对齐反降性能 | **保守弃权显著减少误差传播**（repo B3原句）；不可对齐样本进弃权而非硬标（repo B-Ⅰ） | ★★为"门"的位置背书：对齐性/可核验性测试在**判定之前**；片段claim=不可对齐的极端情形（连配对的资格都没有） |
| 11 | **加权投票族** | RaRE（repo B1：逆方差置信加权+drop-on-disagreement，τ=0.30/0.40）；MCP-MAS（repo B2：w_i=(1−m_i)/Σ(1−m_j)误分类率解析权重；"两裸模型平均→全判fake"警告）；HybridFC（repo B3：小样本解析权重>学习元融合器）；B5 NB投票（repo B5：log-odds权重+"沉默也是证据"） | 置信/可靠性加权平均；分歧超阈值→弃权带 | 弃权/分歧=从票池剔除（RaRE drop）或路由升级 | ★可选扩展：按claim类型加权（typed>semantic）有解析权重先例；但v1不推荐（dev的S=3太小，权重估不稳，HybridFC小样本教训） |
| 12 | **多前提NLI聚合** | 经典蕴含语义＋RTE/FEVER惯例 | **蕴含的单调性**：Γ⊨H ⇒ Γ∪{P}⊨H（加中性前提不破坏蕴含）——证据侧聚合语义上应为OR/并；SummaC列max即此；FEVER证据集判定＝claim对证据全集判（GEAR图聚合，repo表1）【FEVER逐证据→claim级聚合的max/多数/联合打分细节待核实】；ContractNLI＝span多标签→hypothesis级聚合【span→label的合成规则待核实】 | 证据侧：neutral前提不否决entailment（单调性保证）；claim侧：hypothesis是合取，反单调 | ★★★维度6的正解：**"neutral不否决entailment"在证据侧是语义正确**（我们per-claim融合`_fuse_per_claim`的refute>support>NIE就是这个语义，claim级已实现）；**在claim侧它不成立**——合取的support是∀，弱化它=假support（50号dominant_70实证）。修法=删非合取项 |
| 13 | **法律/审计** | ISA 705意见类型（凭知识【条款号待核实】）；ISO/IEC 27001 SoA适用性声明（凭知识【待核实】）；GJB 438C合格性per-requirement（repo `knowledge/gjb_438c_rules_full.json`） | **ISA三分意见**：{无保留意见/保留·否定意见/**无法表示意见**}——"查不了"是与"不合格"不同的意见类型；**SoA适用性门**：控制项逐条标适用/不适用（附理由），审计结论只覆盖适用项——**不适用项出局+留痕，不入符合率分母**；GJB：每个需求单独指定合格性检验方法（90号1.5"域级本体先例"） | 弃权=独立意见类型（无法表示意见≠否定）；不适用=前聚合出局+书面理由 | ★★★域合法性双先例：SoA=**applicability gate before aggregation**（与公式A的结构同构：片段=不适用条目，出局但带理由留痕）；ISA三分=我们三态的社会学合法性的审计学对应 |
| 14 | **Self-RAG** | ICLR 2024（repo 89号表1） | segment级证据支持度**三级分级**（fully/partially/no support）+段级beam | 分级而非硬票；no support段有独立信号 | ★参考：三级分级给了"partial"的中间形态；我们不采用（三态判定已是通道契约），但其"段级支持度作为一等输出"的口径与我们的claim_results明细一致 |

### 判读（四条）

1. **文献轨迹=从"NIE入罪"到"前聚合成员门"**：FActScore（2023，unsupported进分母）→VERISCORE（2024，可核验性门+弃权带单独报告）→B3（2026，对齐前提+保守弃权）。我们要的门在这条轨迹上，但**全线的门都是语义判定（LLM判可核验性），检索范围内无"句法断言性（谓词结构）作为门"的先例**（ClaimBuster的check-worthiness是句子分类先例但解决"哪句值得查"，非"这条是不是命题"，90号1.4已录）——组合位空着，且我们恰好需要确定性实现（90号2.2坐标：LLM门破坏零成本/可审计口径）。
2. **聚合公式只有三个族**：硬票族（strict-∀/多数/加权投票——FActScore的比例是软化变体）、均值族（SummaC列max行均值——分数级平均+校准阈值）、可学习族（Conv直方图卷积/HybridFC MLP）。**三态开放世界+弃权带告警的组合无一实现**（最接近的Viva La Vida是反面事故记录）。
3. **维度6的答案=位置问题不是公式问题**："neutral不否决entailment"的正确实现位置是**证据侧/同claim多通道**（我们已实现：`_fuse_per_claim`），claim侧的正确做法是单元出局（SoA/VERISCORE式），不是投票规则放宽——50号dominant_70的24假support是这条定律的dev实证。
4. **审计邻域给了最完整的聚合规范形态**：适用性门（出局+理由留痕）+三分意见（弃权≠否定）+逐条可检验（GJB合格性）——公式A直接按这个形态写。

---

## 3. 断言性测试的形式化规范（assertiveness test）

### 3.1 语言学依据：谓词=断言的核心

1. **真值适格性（truth-aptness）**：只有含谓词结构的陈述句才有真值——"添加"是NP/动名词片段，指称一个动作概念，不断言任何事（经典逻辑/语言哲学共识；Frege函数-论元分析、Searle 1969断言式以命题真值为真诚条件【原著章节号待核实】；Huddleston & Pullum 2002 CGEL区分clause（谓词结构）与phrase【待核实】；朱德熙《语法讲义》：汉语句子核心是谓词性成分，名词性独词句是呼语等特殊形态，非命题【凭记忆，待核实】）。
2. **NLI标签良定义性**（89号Q2，仓库已证）：三态标签假设hypothesis相对premise有唯一真值；裸名词hypothesis无真值条件→**标签不良定义→mDeBERTa的NIE是任务伪迹不是判定**。这是"片段NIE≠断言性inability-NIE"的机制解释。
3. **谓词缺失=合取项缺失**：answer=claim₁∧…∧claimₙ只在每个claim是命题时成立；非命题片段不是合取项（没有真值可合取）——从聚合公式里删除它**不改变逻辑语义**，只修复单元错误。这是公式A在逻辑上无罪的论证。
4. **RE域本体先例**（90号1.5已录）：ISO/IEC/IEEE 29148原子需求="单一、可测量、可验证的**陈述**"（statement，非片段）【章节号待核实】；GJB 438C合格性规定=每个需求单独检验。需求域的"条目"定义本来就要求命题性。
5. **类型化claim自带谓词**：numeric claim的operator（≤/≥/为）是关系谓词，enum是成员谓词（∈），identifier是同一性谓词，quoted是存在性谓词——我们的typed通道产出的claim**构造性断言**。

### 3.2 判定规则（确定性、零模型、按来源分层）

断言性判定函数 `assertive(r) -> bool`，输入为融合后的ClaimResult（`claim_text`+`method`）：

```
1. method快速通道：method ∈ typed通道方法族（numeric/enum/identifier/quoted各verify_*产出的
   method名，实现时以claim_channels.py的方法名常量作allowlist）→ assertive=True
   （类型化claim构造性断言，§3.1.5；避免文本测试误伤）
2. 文本谓词测试（kind=semantic/结构回退/蒸馏切分器/专家通道产出的claim）：
   t = 剥离枚举前缀后的claim_text（复用_FUSION_PREFIX_RE，与融合键同口径）
   a. 类型化值谓词：t含 数值+操作符（_NUMERIC_PREFIX/_NUMERIC_POSTFIX命中）→ True
   b. 系词/谓词结构：t含【谓词词元+非谓词内容】——谓词词元表（域动词词典：是/为/属于/
      提供/支持/包括/要求/应/具有/达到/满足/实现/处理/存储/传输/管理/显示/查询/删除/修改/
      返回/触发/完成/位于/连接/…）且存在可充当论元的实词内容（t去谓词词元后仍有
      ≥2个实词字符）且len(t)≥4 → True
   c. 全句形态：t以句号/分号结尾且含谓词词元 → True
   d. 否则 → False（片段）
3. （可选升级，二阶段）依赖句法root-POS：LTP/HanLP解析，root词性=v/a（动词/形容词）→
   clause→True；root=n（名词）→片段→False。作为词元正则的校准/替代，非首版依赖。
```

**边界案例表**（校准用例，进单元测试）：

| claim_text | 判定 | 机制 |
|---|---|---|
| 添加 | **片段** | 单谓词词元无论元（"函数无实参，无真值"），len<4 |
| 数据记录的添加功能 | **片段** | NP短语无谓词词元（规则2b不命中）——**7字以上裸NP是现有no_minor_block（len≤6）的漏网区** |
| 支持8路视频流 | 断言 | 谓词+论元 |
| 时延不大于50ms | 断言 | 规则2a（+typed通道出身） |
| 包括初始化、读取配置文件 | 断言 | 成员谓词+论元（enum出身优先走方法通道） |
| 确保系统兼容性 | 断言但属效果性框架 | 规则2b命中（确保=谓词）——**与现有_MINOR_CLAIM_MARKERS是两个正交维度**（断言性=有没有谓词；效果性=是不是可对证据验证的实质断言），见§4.4 |
| 4．1.1 | 片段 | 表格单元格残片，无谓词词元 |
| 序号\|Use case名称\|… | 片段 | 表头残片（50号053的TERM-07误判claim，此门在聚合层二次兜底） |

**设计取向**：保守——测试只把**明显无谓词结构**的判为片段（false negative优先于false positive：误判真断言为片段会放大support，见§4.5风险）。词元表是GJB域文法的延伸（沿answer_claims.py的域词典路线），跨域时随档位换配置。

### 3.3 实现位置

**首版放在聚合侧**（`_aggregate`入口前的过滤层，作用于`_fuse_per_claim`之后的fused ClaimResult）：(a) 对三种decomposer（typed/sentence/蒸馏）与专家通道产出**统一生效**（ClaimResult无kind字段，文本测试+method通道是唯一公共接口）；(b) 保留全量claim_results明细→可审计（Viva La Vida告警规则）；(c) 不动现有分解器/通道与论文已锁数字。**可选二期**：蒸馏切分器训练数据里加片段负例（D2C同构，让切分器学会不产片段——属M82/M87侧工作，非本文规范）；分解器出口过滤（省判定成本）仅当聚合侧方案在dev验证后按需追加。

---

## 4. 聚合公式候选（两个）+ 与现有变体的关系 + 风险

### 4.0 公共记号

- `R` = 融合后全部ClaimResult；`A = {r ∈ R | assertive(r)}`；`F = R \ A`（片段集）
- `v(r) ∈ {support, refute, not_in_evidence}`；refute全局优先权保留（安全第一，三变体已有共识，test_refute_wins_in_every_variant锁定）

### 4.1 公式A：assertive-filter strict（`assertive_strict`）

```
输入: R（fused）
A, F := 按assertive(r)划分
diagnostics := []
1. if ∃ r ∈ A: v(r) = refute → return refute                    # 断言性refute否决一切
2. if ∃ r ∈ F: v(r) = refute → diagnostics.append(
       "agg_fragment_refute_demoted:<claim_id>")                 # 片段refute降级+告警（见设计决策D1）
3. if ∃ r ∈ A: v(r) = not_in_evidence → return NIE               # 断言性NIE(含inability)保留strict否决权
4. if A ≠ ∅ and ∀ r ∈ A: v(r) = support:
       diagnostics.append(f"agg_fragment_band_{len(F)}_of_{len(R)}")   # 片段进弃权带+计数告警
       return support
5. if A = ∅: return NIE, diagnostics.append("agg_no_assertive_claim")  # 全片段: fail-open到弃权,不fail-open到support
6. 否则(= A非空且全为NIE已被3捕获; 空R由上游处理) → NIE
```

**设计决策**：
- **D1 片段refute降级而非直接生效**：50号053的TERM-07表头残片误refute证明"片段上的refute大概率是通道伪迹"；真矛盾必然伴随断言性claim承载（矛盾内容是断言）——片段only-refute以高概率是误报。降级+告警（不静默，Viva La Vida规则）+可选升级路由（进残差判定）。风险与替代（片段refute仍直接生效=更保守）在§4.5。
- **D2 片段NIE不进任何分母**： VERISCORE弃权带语义+SoA不适用项语义——出局但留痕计数。
- **D3 全片段实例→NIE**： fail-open到弃权/人工，绝不fail-open到support（SummaCConv警示的保守侧）。

### 4.2 公式B：assertive-ratio（`assertive_ratio`）

```
输入: R, 阈值τ(默认候选0.70, dev校准)
A, F := 同上; refuse处理同公式A的1/2步
D := {r ∈ A | v(r) ∈ {support, refute} 或 _is_active_nie(r)}      # decidable: 复用dominant_70口径
if D = ∅ → return NIE, "agg_assertive_ratio_no_decidable"
ratio := |{r ∈ D: v(r) = support}| / |D|
return (support if ratio ≥ τ else NIE), f"agg_assertive_ratio_{ratio:.2f}_tau_{τ}"
```

与dominant_70的**唯一差异**：分母先过断言性门。inability-NIE（断言性）与片段（非断言）都不进分母——前者是dominant_70原有语义（50号已否决其作域内默认），后者是新增豁免。

### 4.3 与现有机制的关系：两条血统各升级一次，非并行实验

| 现有机制 | 公式A的关系 | 公式B的关系 |
|---|---|---|
| `strict`（默认，50号保精度依据） | **升级**：strict的单元集从R换成A——语义不变（∀），单元修复（删非合取项）。50号c-fix（融合键剥前缀）是它的模式特异先驱：c-fix修"N．前缀"片段，公式A修一切无谓词片段 | 不动（B不含strict路径） |
| `no_minor_block`（dev零翻转，已否决） | **取代并泛化**：_MINOR_CLAIM_MARKERS是断言性测试的词汇特例（效果性框架⊂非可判定单元）；len≤6的长度兜底只覆盖超短片段，7字+裸NP漏网（§3.2案例2）。公式A把"什么不是断言"从词表升级为谓词结构测试 | 同左（B也继承门） |
| `dominant_70`（dev 24假support，已否决作域内默认；v3 crossdoc档在用） | 不动 | **升级**：dominant_70+断言性门=crossdoc档的替换候选（该档已接受ratio语义，0.7361实测基线）；域内仍不用 |
| `_is_active_nie` | 原样复用（公式A第3步对active/inability-NIE一律保留否决权——active-NIE在A里直接走第3步refute-like阻断，在50号dev上这正是保精度的部分） | 原样复用（decidable分母口径） |
| `_fuse_per_claim`（claim级refute>support>NIE） | **不动**——它就是"neutral不否决entailment"在文献里的正确位置（证据侧/同claim多通道，§2判读3）；聚合门在其**之后** | 同左 |
| `_FUSION_PREFIX_RE`/序列适用性门/`answer_claims_v2`审计层 | 共存：分解/融合层的确定性修复继续做（50号教训：杠杆在通道层）；公式A是**聚合层的第二道防线**（表头残片等专家通道片段只有这层能拦） | 同左 |

**升级还是并行的判定**：并行=三变体+两新变体共五个`AGGREGATION_VARIANTS`作实验接口，**默认strict不动**（全部论文数字受保护）；选型结论按50号协议在冻结dev上做（§4.6）。公式A若通过dev门→接替strict候选；公式B只在crossdoc preset里替换dominant_70。

### 4.4 断言性 vs 效果性：两个正交维度，首版不合并

`_is_minor_claim`判"效果性/总结性"（"确保/旨在"——有谓词但不可对证据验证的框架话），`assertive`判"命题性"（有无谓词结构）。集合关系：效果性⊂断言性（大多含谓词），片段∩效果性=∅。**首版公式A只用命题性测试**（目标故障=蒸馏片段）；效果性标记保留为独立开关（50号dev上它零翻转，耦合进来只会污染归因）。合并成统一"可判定单元"判定（assertive∧非效果性）留作消融扩展。

### 4.5 风险分析（每公式：假support风险/丢refute召回/其他）

| 风险 | 公式A | 公式B | 缓解 |
|---|---|---|---|
| **假support**（precision坍塌，50号dominant_70前车之鉴） | 低——构造上不豁免任何断言性NIE；残余风险=断言性测试FN（真断言误判片段→其NIE失否决权）。实测上这恰是dominant_70 24假support实例**不受影响**的原因：那些阻断claim全是断言性inability-NIE，公式A第3步照拦 | **高（继承dominant_70血统）**——断言性inability-NIE不进分母，silver=NIE的实例可能部分support达阈值翻转。50号dev实测+24假support是直接预期 | A：测试保守取向（只拦明显无谓词者）+dev翻转审计逐条归因（50号oracle探针协议）；B：τ从高侧起步（0.8-0.9候选），τ-sweep曲线随结果报告，只在crossdoc档启用 |
| **丢refute召回** | 中——D1片段refute降级；若真矛盾仅由片段承载（如id_join对孤立ID片段的refute）会漏。**注意identifier claim走方法通道=断言**，实际风险集中在entity_detector表头类残片（50号053证明那恰是误refute源——降级是收益不是损失） | 同A | D1的告警诊断+残差路由；17违例集回归（id_join主力地位零回退是50号§7已建立的回归口径） |
| **τ过拟合** | 不适用（无阈值） | 高——dev侧S类仅3条（冻结切分事实），τ自由度不可信 | 汇报τ-sweep全曲线而非单点；τ默认值继承dominant_70的0.70血统并在crossdoc 150上二次验证（refactor_matrix口径） |
| **全片段实例误NIE** | 存在（A=∅→NIE）——蒸馏切分器整体失败的实例会被判NIE而非support | 同 | 诚实行为：fail-open到弃权+诊断`agg_no_assertive_claim`，同时是切分器质量的免费探针（该诊断频率=蒸馏片段率的监控指标） |
| **测试本体维护成本** | 中文谓词词元表的域维护（跨域随档换配置）；2b规则对"谓词+论元"的词法近似有灰区（"数据添加"类NP化复合词） | 同 | 边界案例表进快照测试；二期LTP root-POS校准（规则3）；灰区默认判断言（保守取向） |

### 4.6 评测与落地协议（沿50号既有协议，防数字污染）

1. **默认不动**：constructor默认strict；`assertive_strict`/`assertive_ratio`追加进`AGGREGATION_VARIANTS`（test_aggregation_variants.py增锁行为：片段NIE不否决断言support/断言inability-NIE仍否决/片段refute降级+告警/全片段回退NIE/断言性测试边界案例表）。
2. **dev翻转审计（选型唯一依据）**：冻结dev 45条（`data/gjb_438c/qa_frozen/dev_test_split_v1.json`），逐实例翻转表+假support增量（50号§5口径：dominant_70的24假support就是这么暴露的）。**通过门=假support增量为0且support召回有增益**；oracle探针先行（对既有run的fused claim_results离线重放聚合规则，零新API成本——50号§5 c-fix探针同法）。
3. **crossdoc档**：`PRESETS["crossdoc"]`里dominant_70→assertive_ratio候选替换，refactor_matrix口径（crossdoc150）复测。
4. **回归**：全91确定性+17违例集+tests全绿；runs协议落盘（tools/run_utils.py）。
5. **论文口径**：聚合层改动作为"assertion-aware aggregation"小节，文献定位=VERISCORE语义门的确定性句法版+Viva La Vida弃权≠拒绝规则的实例化（§2判读1的血统足够诚实且不越界——不宣称聚合本身是novelty，novelty在确定性断言性门+与strict的组合位）。

---

## 5. 推荐判定（一句话）

**推荐公式A（assertive-filter strict）作为域内默认的候选接替者**：它用单元层修复（片段出局+告警弃权带）精确命中M82/M87的裸名词一票否决，同时不豁免任何断言性NIE——50号dev实验证明这正是dominant_70崩掉的那条红线；公式B（assertive-ratio）仅在crossdoc档替换dominant_70（该档已接受ratio语义），τ高侧起步+dev/crossdoc双校准。两者都通过oracle探针+dev翻转审计（假support增量为0的门）才落默认。

---

## 6. 仓库材料索引（本取证引用）

| 材料 | 路径 | 用途 |
|---|---|---|
| 50号（聚合变体dev实验） | `docs/srs_project/50_support_recall_analysis.md` | §1.2两种NIE/§1.3 silver=strict-∀/§5 dominant_70 24假support+no_minor_block零翻转+c-fix零副作用/§7修复回归口径 |
| 88号（分解文献） | `docs/srs_project/88_claim_decomposition_literature.md` | 分解三条件/MiniCheck消融澄清（§1引用不重复） |
| 89号（归因单元） | `docs/srs_project/89_nli_attribution_survey.md` | Q2标签良定义（§3.1.2依据）/Self-RAG三级/MiniCheck折叠contradiction |
| 90号（分解器SOTA） | `docs/srs_project/90_claim_extraction_sota.md` | ISO 29148原子需求=statement（§3.1.4）/ClaimBuster定位（§2判读1） |
| 聚合实现 | `algorithms/consistency/qa_module.py`（`_aggregate`/`_fuse_per_claim`/`_is_active_nie`/`_is_minor_claim`/`_FUSION_PREFIX_RE`） | §1/§4代码事实 |
| 分解器 | `algorithms/consistency/answer_claims.py`（typed/sentence两档+span） | §3.2规则2的域词典路线先例/§3.3实现位置 |
| 变体契约测试 | `tests/test_aggregation_variants.py` | refute全局优先/默认strict锁定（§4.0/4.6） |
| Viva La Vida精读 | `literature_survey/modular_verification_architecture_survey.md` B4 | 弃权≠拒绝+告警规则（§2#9/§4.1 D2） |
| SummaC精读 | 同上 E2 | 列max行均值/Conv/粒度研究（§2#3/#4） |
| RaRE/MCP-MAS/HybridFC/B5 | 同上 B1/B2/B3（角度B）、`cascade_innovation_expansion_survey.md` B5 | 加权投票族（§2#11） |
| FActScore/VERISCORE/MiniCheck | `literature_survey/pair_classifier_sota_2023_2025.md` A3/A4/A1 | §2#1/#2/#6 |
| B3对齐瓶颈/ElementCheck | `literature_survey/cascade_innovation_expansion_survey.md` B3/B4 | §2#10 |
| 选择性预测/Chow | `literature_survey/method_framing_and_novelty_check.md` L174、`technical_landscape_acdd_positioning.md` L67 | §2#7/#8 |
| GJB合格性规定 | `knowledge/gjb_438c_rules_full.json` | §2#13/§3.1.4 |
| 聚合输出契约Y={S,R,N}×ℓ×j | `literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` | §4.6评测口径（判定+定位联合） |

## 7. 待核实清单

1. **FActScore分母细节**：检索无果原子的计法（repo A3只录"被支持原子比例"）——是否全部unsupported均入分母、有无coverage例外，引用前必核原文§3。
2. **VERISCORE门位置**：repo A4录"不可核验claim弃权"，其可核验性判定的具体标准（上下文无关/客观性的操作定义）与门在判定前后（本文按"分解后判定前"理解）需核原文。
3. **Chow 1970/El-Yaniv & Wiener 2010**：标题与年份凭知识（repo已引"Chow规则"与Geifman & El-Yaniv 2017，后者锚定；前两者引用前核对）。
4. **ISA 705/ISO 27001 SoA**：意见三分法与适用性门是审计学常识，具体条款号/年版未核——论文引用前须核对原文（或改引二手综述）。
5. **RTE/FEVER多前提聚合惯例**：FEVER逐证据→claim级聚合（max/多数/联合）与GEAR的图聚合细节、RTE长文本任务的entailed-by-any惯例——凭印象，引用前必核。
6. **ContractNLI span→hypothesis聚合规则**：span多标签如何合成条款级NLI标签（repo 89号表2只录span多标签标注协议）。
7. **Searle/Frege/CGEL/朱德熙**：断言式/函数-论元/clause vs phrase/谓词性核心——经典共识但章节号页码未核，论文引用时给出精确出处。
8. **QAFactEval聚合加权**（若§2需要扩展）：per-question分数到摘要级分数的合成方式（含QuestEval的问题相关性加权）——沿89§5.2待核实口径。
9. **M82 C/M87 D2实验记录与蒸馏claim样例**：任务口径输入，仓库无run/数据——公式落地前须以实际蒸馏产出跑§3.2边界案例表的校准集（预期分布：裸名词片段占比、"数据添加"型NP化复合词的灰区占比）。
10. **谓词词元表初版**：§3.2规则2b的域动词词典需从16份SRS词频+GJB规则库动词清单构建（`knowledge/gjb_438c_rules_full.json`+`srs_kb.json`），本文只给结构未给全表。
