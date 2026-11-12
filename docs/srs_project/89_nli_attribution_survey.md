# 89. NLI验证系统的归因/定位单元取证：长answer怎么定位，claim模块是否必需

> 取证日期：2026-11-12。任务：回答三个追问——(1)主流NLI验证系统输出"哪里不一致"时用什么单元？(2)标准NLI的hypothesis为什么天然是短单句，长hypothesis在学界叫什么、怎么处理？(3)给定"长answer三态验证+不一致定位输出"的需求，claim/sentence/answer三种验证单元的必要性矩阵。
> 性质：文献取证（只读+写作，未跑模型，未git commit）。
> 与88号的关系：`88_claim_decomposition_literature.md`回答**验证单元**视角（要不要分解、分解三族、typed无先例）；本文回答**归因/定位单元**视角+教科书范式+必要性矩阵。88已论证的结论（MiniCheck推理期分解消融、分解三条件、(b)判定）直接引用不重复展开。仓库未覆盖的论文细节凭知识补全并标"待核实"（沿88§7口径），未虚构。

---

## 0. 三问一句话答案（详证见§1-§4）

1. **归因单元与验证单元同构（或落在证据侧span）——定位不是判定的免费伴生输出**。检索范围内所有"能定位"的系统，其定位单元要么=分解单元（FActScore/VERISCORE/Peerify的原子claim、QAFactEval的问题、SummaC的句子、RARR的被改写span），要么=证据侧span（FEVER证据句、ContractNLI证据span、Kontrast证据对），要么=符号核（Bendík的SAT最小不可满足子集）；而验证单元=整体直判的系统（MiniCheck/TRUE/经典NLI）**均无原生定位**。反向证据：verdict对≠span对（span F1 0.564 vs acc 0.896）、CiteVQA归因幻觉（最强模型Strict Attributed Accuracy仅76.0）——定位是独立能力，必须单独设计。
2. **标准NLI的hypothesis短单句是标注协议+标签良定义的产物**：标注者被要求"写/改一个句子"，且三态标签假设整个hypothesis相对premise有唯一真值（复合hypothesis会产生partial entailment，单标签无法良定义）。长hypothesis没有单一学界命名，最接近的术语是**granularity mismatch**（SummaC诊断用语）与**document-level NLI**（DocNLI）；处理路径五条（训练粒度上移/推理切分聚合/推理分解聚合/问题化/长上下文LLM直判），前三条正是88§2的分解三族坐标。
3. **claim模块 = (b)为定位服务的工程选择**，并因typed证据通道接口成为架构必需；不是(a)全局必需（MiniCheck消融证明短claim直判即够）；**不能被句子切分完全替代**——复合句（一句多claim）定位不到具体值、跨句claim（枚举句+列表）被句切分拆碎、三态聚合语义与typed通道接口两处降级。句子切分是正确的**降级回退层**（已是我们管线第二层），层级关系而非替代关系。

---

## 1. 归因单元证据表（主取证）

**列定义**：验证单元=送入判定器的**假设侧**单元；归因/定位单元=系统输出"哪里不一致"时指向的单元。证据锚点给仓库路径；仓库未覆盖条目凭知识补全并标"待核实"。

### 表1：NLP事实核查/摘要一致性/验证系统

| 方法 | 出处 | 验证单元（假设侧） | 归因/定位单元 | 长answer（复合陈述）处理 | 定位能力与证据锚点 |
|------|------|---------------------|---------------|---------------------------|---------------------|
| 经典NLI (SNLI/MNLI/XNLI/CMNLI/ANLI) | 2015-2020 | 单句hypothesis | **无**（pair级标签，任务定义不含定位） | 不处理（短单句是数据构造约束，§3） | 无定位输出；88§2行1 |
| FEVER | NAACL 2018 | claim（输入即短claim） | **证据句集合**（文档侧） | 任务外（claims由Wikipedia句改造，天然短） | 标注协议强制每条claim附evidence spans，κ=0.6841；`no_human_annotation_eval_survey.md` §1.4 |
| GEAR（FEVER后续） | ACL 2020 | claim | 证据句（claim+证据句建图→GAT聚合） | 多句证据推理，claim仍短 | `graph_representation_consistency_survey.md` |
| SummaC | TACL 2022 | **句子**（摘要句×文档句pair） | **句×句NLI矩阵**（中间产物） | 摘要确定性切句→M×N pair→聚合（ZS：列max行均值；Conv：50-bin直方图+1D卷积） | 定位=读矩阵（哪个摘要句的列max低）；矩阵=可审计中间结构、可热图可视化；句级粒度最优（§5.3.3段落/双句块均更差）；`modular_verification_architecture_survey.md` E2 |
| TRUE | Findings NAACL 2022 | sentence/摘要（任务给定的output整体） | **无原生定位**（重格式化为pair直判）【待核实】 | 11个数据集统一为(input,output) pair，T5-11B直判 | 仓库未覆盖；88§7待核实项1 |
| QAFactEval | NAACL 2022 | **question**（对摘要句生成的问题） | **失配的QA对→映射回其来源摘要句** | 摘要句→QG→从源文档QA取答→答案对齐比较→聚合 | 仓库未覆盖，机制凭知识（QG-QA-比较三段，Salesforce线）；细节待核实（同88§7项2） |
| FActScore | EMNLP 2023 | **原子事实** | **原子事实**逐条verified/unsupported——可指出"哪条事实挂了" | LLM分解长文本→逐条检索KB验证→聚合为"被支持原子比例" | `pair_classifier_sota_2023_2025.md` A3（"定位到具体不一致原子"）；注意：原子事实是LLM生成的**文本**，不带原文span/offset，映射回answer需自建provenance |
| AlignScore | ACL 2023 | **chunk**（~350token机械切块） | chunk级对齐分（聚合为整段分数，不输出span） | 双侧chunk切分+统一"信息对齐"二元打分 | 88§2行8；chunk内部配对机制细节待核实（arXiv 2305.16739） |
| CoVe | arXiv 2023 (Meta) | **验证问题** | 失配的验证问题→映射回draft中的相应声明 | 草案→规划验证问题→factored独立回答（隔离上下文）→交叉检查修正 | `id_graph_positioning_survey.md` 表1行1（factored>joint>两步；开放型问题>yes/no） |
| RARR (Attribution) | EMNLP 2023【待核实，仓库零覆盖】 | **masked span**（证据条件下的改写单元） | **被改写的span**（input与revision的diff=不可归因部分）+证据引用 | 证据搜索→遮罩-再生成（invariance约束：无关span不动）→输出最小修订文本 | 全部凭记忆（Gao et al., Google；arXiv 2210.08726），引用前必核；定位=事后diff，粒度=span |
| VERISCORE | arXiv 2024 | **可验证claim** | 不可核验claim弃权；可核验claim逐条判定 | LLM分解+可核验性过滤→检索验证→聚合 | `pair_classifier_sota_2023_2025.md` A4（弃权带换precision） |
| MiniCheck | EMNLP 2024 | **claim整体**（推理期不分解） | **无原生定位**（claim-doc二元概率，不输出evidence span）；需要定位时由调用方外部切分（句/原子）后逐条调用，定位单元=外部切分单元 | 训练期管粒度（C2D/D2C原子级构造）；推理期直判；**推理期分解消融=无益**（GPT-4 +0.3，专用-1.9~+1.2，成本×2-4） | `five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1；88§4.1澄清：其claim≈原子级，MiniCheck否定的是"把短claim再拆碎"而非"把长answer拆到claim级"；组合用法先例待核实 |
| ProgramFC | ACL 2023 | claim（复杂claim→验证程序） | 程序步骤调用的证据段 | 复杂claim分解为程序、函数库逐段执行验证 | `cascade_innovation_expansion_survey.md` B2；原文细节未读，定位描述按仓库概括 |
| Self-RAG | ICLR 2024 | **segment**（生成段落） | segment级**证据支持度分级**（fully/partially/no support）+引用来源 | 分段生成+按段反思token+段级beam search | `id_graph_positioning_survey.md` 表1行2（evidence-gated验证标准范式） |
| SAFE | arXiv 2024【待核实】 | 原子claim | 原子claim+搜索证据 | 分解+搜索引擎逐条核验 | 仓库仅A6注提及（依赖外部检索，不适用"文档即证据"场景，未列） |

### 表2：文档NLI/法律邻域/RE域/评测协议（定位视角）

| 方法 | 出处 | 验证单元 | 归因/定位单元 | 长answer处理 | 证据锚点 |
|------|------|----------|---------------|--------------|----------|
| ContractNLI | EMNLP 2021 Findings | statement（条款级假设，单句） | **证据span多标签**（span集合分类，非start/end回归） | hypothesis=条款级statement，长answer非其对象 | `five_direction_method_survey_and_cascadeverify_v2_design.md` §1.3；标注=律师+外行双标注+仲裁（607份） |
| Verdicts Without Annotated Evidence | arXiv 2610.06962, 2026 | verdict | （研究对象即定位）label-only后训练：**span F1 0.564 vs acc 0.896——判定对≠定位对，两者弱相关** | — | 同上§1.3；AVeriTeC结论再次确认 |
| AVeriTeC | NeurIPS 2023 D&B | claim | **QA对证据+文本justification**；得分=**判定正确∧证据质量达标**（联合评分协议） | 4568真实声明 | `cascade_innovation_expansion_survey.md` B1；CLEF共享任务21队证明协议社区接受度 |
| FICLE | ECML-PKDD 2023 | claim（表+文联合证据） | **不一致span+类型+claim三元组成分+实体类型**三层标注；M2专司span预测（EM/IoU报告齐全） | — | `modular_verification_architecture_survey.md` E4：分阶段流水线打败联合多任务；T5生成式最好三元组、**DeBERTa判别式最好span** |
| LegalWiz | arXiv 2510.03418, 2025 | 条款/句 | 6类矛盾+**证据span** | — | `inconsistency_history_survey.md`（法律邻域率先恢复多类型+证据定位） |
| Kontrast | arXiv 2607.25959, 2026 | 值/集合级声明（正文vs表格模态级） | **证据对+不一致类型+严重度+解释**（两阶段：规则匹配→LLM兜底） | 模态级不一致检测 | `id_graph_positioning_survey.md` 方向5行1（产出格式可直接借鉴） |
| CiteVQA | arXiv 2605.12882, 2026 | QA | **Strict Attributed Accuracy**：判定正确∧证据区域正确；最强模型SAA仅76.0（答案准确率远高于此）=**Attribution Hallucination** | 多模态 | `dataset_enhancement_method_upgrade_survey.md`：证据定位是独立能力，必须单独测 |
| Alignment Bottleneck | arXiv 2602.10380, 2026 | 子claim | —（研究分解有效性前提） | **分解只在证据粒度严格对齐时有效；不对齐反降性能；保守弃权显著减少误差传播** | `cascade_innovation_expansion_survey.md` B3 |
| ElementCheck | EMNLP 2026 Findings | 句→元素图（实体对） | **复杂度自适应**：简单句句级直验、复杂句元素级精验 | 长句复杂度感知粒度选择 | 同上B4 |
| Peerify | arXiv 2609.25046, 2026 | **原子声明** | 稿件内取证（span级）+蕴含判定 | 审稿意见→原子声明→稿件内检索→逐条判定 | 同上B9（"文档内验证+自动标签审计"与我们场景同构） |
| FARCA | arXiv 2608.24350, 2026 | 判定 | **反事实证据归因**（"判定对关键证据的依赖度"作可靠性代理） | — | 同上E3 |
| Bendík & Wolf | ISSTA 2017 | 需求（依赖约束） | **最小不可满足子集（MUS）**——SAT求解器免费给出"哪几条需求构成最小冲突集" | NL→逻辑翻译需人工 | `inconsistency_history_survey.md` 时代3；`technical_landscape_acdd_positioning.md` F3 |
| Reder & Egyed | TSE 2013 | 模型变更 | 引发不一致的**最小变更/模型元素集**（检测–诊断分离） | — | `inconsistency_history_survey.md` 时代2 |
| UML/Analyzer (Egyed) | ICSE 2006/07 | 模型元素×规则 | 违反的**规则+受影响元素**（增量即时检查） | 模型级（XMI），NL不在射程 | 同上时代2、§4a（"能指出违反哪条规则"vs LLM只能给判断+自由文本） |
| Femmer需求气味 | JSS 2017 | 需求句 | 命中的**句法/词汇模式**（≈规则级定位，约53%规则可自动化） | — | 同上时代3 |
| S3CDA / TSRCDF-SS | 2022 / 2025 | **给定句对**（pair分类） | **无**（输出=句对二分类标签；对齐误差被评测协议假设为1，P(align)不可见） | 句对粒度 | `technical_landscape_acdd_positioning.md` F4；`inconsistency_history_survey.md` §5.2 |

### 表的判读（三条）

1. **归因单元≡验证单元（或证据侧span）**：16+个系统中凡有定位输出的，定位单元与验证单元同构（FActScore原子/QAFactEval问题/SummaC句/Self-RAG段），或定位落在**证据侧**（FEVER证据句/ContractNLI span/Kontrast证据对），或由符号引擎给出**因果核**（Bendík MUS；我们L1的Z3 unsat core同构，`cascade_innovation_expansion_survey.md` E-Ⅰ）。凡整单元直判的（MiniCheck/TRUE/经典NLI/S3CDA系）均无原生定位——**"判对"和"指出哪里错"在文献里是两个任务**（Verdicts Without Annotated Evidence；CiteVQA SAA 76.0）。
2. **长answer的两条标准路+一个空位**：(i) 推理期切到与证据粒度对齐的单元再验证（SummaC句切/FActScore原子/QAFactEval问题化）；(ii) 训练期把粒度吞进模型（MiniCheck C2D/D2C、DocNLI、ContractNLI），推理期直判。**路线(ii)只给verdict不给定位；路线(i)给定位**。"长answer直判（不开分解）+claim级定位输出+三态"的组合在检索范围内无先例——我们管线占的正是这个组合位。
3. **2026年前沿把"分解粒度"变成显式研究对象**：B3对齐瓶颈（分解≠自动有益，需证据span配对）、B4 ElementCheck（复杂度自适应粒度）、B6 CFMS（粗到细）。"总是分解"与"从不分解"都被否定——粒度选择本身是设计变量。这支持我们把claim/句/answer做成**三层降级**而非单一定死（`algorithms/consistency/answer_claims.py`结构，88§4.3）。

---

## 2. 三问详细回答

### Q1：每个方法输出"哪里不一致"时用什么单元？长answer时定位怎么实现？

逐方法速查（详表见§1，此处只补表未尽之义）：

- **FEVER**：claim是输入（天然短），定位=**证据侧**支撑/反驳句集合。claim侧无需定位——claim本来就只有一个。它确立的惯例是"每条判定必须附evidence"（`no_human_annotation_eval_survey.md`："FEVER要求每条标注附证据，我们已输出证据链应在数据集格式中强制保留"）。
- **FActScore**：**能**指出哪条事实挂了——每条原子事实独立判定，挂掉的原子即定位输出。但注意两个工程细节：(a) 原子事实是LLM生成的文本，**不带原文span/offset**，映射回answer位置需自建provenance；(b) 头条输出是"被支持比例"（聚合分数），逐条明细在管线内部。我们的answer→claim分解保留来源切分（结构回退层来自句切分，天然带位置），定位质量优于裸FActScore用法。
- **SummaC**：定位=读句×句矩阵（哪个摘要句的列max蕴含分低）。头条输出是文档级分数——**句级定位是中间产物的副产品**，需要主动暴露矩阵才能服务定位（E2映射："可审计、可人工抽查、可热图可视化"）。
- **QAFactEval**：哪个question的答案与源文档答案不匹配→该question来自哪个摘要句=定位。定位单元=问题（粒度由QG覆盖密度决定）。
- **AlignScore**：chunk级分数（~350token机械块）——粒度粗于句子，无span输出；要定位需instrument中间chunk分。
- **MiniCheck**：**推理期不分解且无原生定位**——输出只有claim-doc二元概率。长answer要定位时，责任外包给调用方：外部切分（句/原子）后逐条调MiniCheck，定位单元=外部切分单元。即MiniCheck的用户**想要定位就必须自己搭分解层**——这与我们的架构（分解层+残差NLI）同构，只是它把分解留给用户。88§4.1已澄清：其消融否定的是"把短claim再拆碎"，未否定"把长answer拆到claim级"。
- **RARR**：定位=被改写的span（input与revision的事后diff）+证据引用；其任务本身就是attribution（最小编辑使文本可归因），验证单元=masked span。
- **RE域**：定位传统来自**符号侧**——Bendík的MUS（最小冲突需求子集）、Reder & Egyed的最小致因元素集、Egyed的"违反哪条规则+Femmer的模式命中"。RE的NLP线（S3CDA/TSRCDF-SS句对分类）**全部无定位**；定位输出2025-2026才由法律邻域带回RE视野（LegalWiz/ContractNLI的span，`inconsistency_history_survey.md`§2.2："2025-2026年法律邻域率先恢复多类型+证据定位，RE领域尚未跟进"）。
- **评测协议侧**：AVeriTeC（判定∧证据联合评分）与CiteVQA（SAA）把"定位对"升格为**一等评测维度**——只报P/R/F1不报证据定位的检测器会被审稿人质疑（`dataset_enhancement_method_upgrade_survey.md`风险信号）。

### Q2：标准NLI的hypothesis为什么短单句？长hypothesis叫什么问题、怎么处理？

**为什么短——两个构造性原因**：

1. **标注协议**：SNLI（一人为图写premise、另一人据此写hypothesis）、MNLI（多genre句+标注者改写）、ANLI（众包写hypothesis骗模型）、XNLI（MNLI翻译）、CMNLI/OCNLI（中文句对）——标注者的任务就是**"写/改一个句子"**，hypothesis短单句是数据构造的直接产物，不是对"验证单元"的原则性选择。
2. **标签良定义约束**：三态标签假设整个hypothesis相对premise有**唯一真值**。复合hypothesis（多原子断言）会产生partial entailment（一部分被蕴含、一部分被反驳/未提及），单标签无法良定义——所以短单句是被任务定义**排除**出的需求，不是模型能力的边界。

**长hypothesis在学界叫什么**：无单一通用名称。最接近的锚定：**granularity mismatch**（SummaC对"NLI句对粒度vs文档任务粒度"的诊断用语，`nlp4re_llm4re_comprehensive_survey.md`："2021 SummaC: 诊断粒度失配"）；**document-level NLI**（DocNLI，"句对级限制了NLI应用"，`open_problems_analysis.md`）；RTE传统中compound hypothesis的讨论【待核实】；事实核查侧长文本叫**long-form factuality**（FActScore/VERISCORE任务名）。我们场景（长answer=多原子claim复合体 vs 冻结文档）在文献坐标里同时踩中granularity mismatch与long-form factuality。

**五条处理路径**：

| 路径 | 代表 | 粒度落点 | 定位能力 |
|------|------|----------|----------|
| 1 训练粒度上移 | DocNLI；MiniCheck C2D/D2C；ContractNLI | 训练期对齐，推理期直判 | 无 |
| 2 推理期切分+聚合 | SummaC（句）；AlignScore（chunk） | 句/chunk | 句/chunk级（读中间产物） |
| 3 推理期分解+逐claim+聚合 | FActScore；VERISCORE；Peerify；SAFE | 原子claim | **claim级** |
| 4 问题化 | QAFactEval；CoVe | question | 问题级→映射回句/声明 |
| 5 长上下文LLM直判 | GPT-4等 | answer级 | 无（且不可靠） |

路径5的负面证据（仓库已核验）：ContraDoc长文档自矛盾不可靠（arXiv 2311.09182）、ECon"无理由偏向一方"（arXiv 2410.04068）、Two Truths最佳模型中位仅检出47%（`modular_verification_architecture_survey.md` E3）。路径3/4即88§2的"LLM原子分解/问题化"两族，路径1/5即"整单元直判"族——88已论证此处不重复。**没有一条路径在"直判长answer"的同时给出answer内部定位。**

### Q3：claim/sentence/answer三种验证单元的必要性矩阵

我们的需求：长answer三态验证（S/R/N，开放世界NIE）+**不一致定位输出**（Y = {S,R,N}×ℓ(块ID+行/span)×j(触发规则/推理trace)，`five_direction_method_survey_and_cascadeverify_v2_design.md`）。

| 验证单元 | (a)判定精度（长answer三态） | (b)定位粒度 | (c)聚合语义 | (d) typed证据通道接口（项目特有） |
|----------|------------------------------|-------------|--------------|-----------------------------------|
| **answer整判** | △ 直判粒度失配：单点矛盾被复合陈述稀释（mDeBERTa直推0.294坍缩；SummaC粒度诊断）；MiniCheck证明仅当answer≈原子claim时直判够用 | **✗** 无定位输出（verdict≠span：0.564 vs 0.896；CiteVQA归因幻觉） | ✗ 无聚合（单票），三态边界只能整answer猜 | ✗ Z3/join无法消费整answer |
| **sentence切分** | ✓ SummaC证明句级粒度最优（段落/双句块更差）；确定性无模型 | △ 句级：**复合句**（"时延≤50ms且支持8路"）定位不到具体值；**跨句claim**（"包括以下三种：a/b/c"）被句切分拆碎 | △ 需自建聚合器（SummaC列max行均值/直方图卷积是二值族先例）；**三态开放世界聚合无先例**（MiniCheck折叠contradiction） | ✗ 句子非类型化，进Z3/join前仍需parse |
| **typed claim分解** | ✓ 粒度=NLI训练粒度（短单claim）；可与证据粒度显式配对（B3对齐瓶颈=前提；Chain-of-Table聚焦证据视图）；EGT三态合成在claim级构造R/N | ✓ claim级+可映射回answer位置（分解保留切分来源）；AVeriTeC式判定∧定位联合评分可落地 | ✓ 显式聚合语义（全support→S；∃证据承载的refute→R；否则NIE）；FActScore式"被支持比例"是聚合先例 | ✓ numeric→Z3区间；enum/identifier→join（`answer_claims.py`） |

**判定**：

1. **对(a)（精度）**：claim不是全局必需——短claim或证据已对齐时句级/直判即够（MiniCheck消融是最强反例，须诚实引用）；长复合answer+证据粒度失配时claim有条件增益（0.6105→0.8047的组合增益中分解只是接口之一，88§4.1已声明）。B3进一步警告：分解增益的**前提是claim与证据span对齐**，不对齐反伤——我们的"聚焦证据视图"（每claim配最小表格视图）正是对该前提的满足。
2. **对(b)（定位）**：claim是**为定位服务的必要选择**——判读1（§1）显示定位单元=分解单元是文献常态，句子切分只能给句级粗定位且在复合句/跨句claim上失真，answer直判完全不提供。
3. **对(c)（聚合）**：claim级三态聚合语义（全S→S / ∃R→R / 否则N）在claim单元上良定义且可审计；句级可近似但标签噪声更大（复合句的三态标签本身不良定义，同Q2的标签良定义约束）；answer级无聚合可言。
4. **对(d)（通道接口，超出用户三问但为本管线架构约束）**：typed claim是符号通道（Z3/join）的唯一可消费形态——88§4.1"条件3：typed证据通道，异构确定性专家只能消费类型化claim"。

**结论：claim模块=(b)——为定位（并因typed通道接口成为架构必需）服务的工程选择**。句子切分可降级支撑(a)与粗定位，但(b)(c)(d)三处降级，是回退层而非替代品（我们管线已把它实现为第二回退层，`answer_structure.py`；answer整判为第三层——三层各对齐一个文献范式，88§5）。对用户质疑"一定要claim吗"的准确回答：**为三态verdict不一定，为"指出哪里不一致"一定**——文献中没有系统能在不开分解/切分的情况下输出answer内部的定位。

---

## 3. 对外表述口径（答辩/论文用语）

1. "一般NLI怎么做？"——标准NLI的hypothesis是短单句（标注协议+标签良定义的产物），我们的answer是多原子claim复合体，**不是同一任务形态**；长hypothesis的文献处理五路径中无一"硬直判还要求定位"。
2. "一定要claim吗？"——为verdict不必（引MiniCheck消融，诚实承认反例）；为定位必需（引判读1+Verdicts≠spans 0.564/0.896+CiteVQA SAA 76.0）。我们的claim层=定位与typed通道的接口，句切分是降级回退、answer直判是最终回退——**三层降级结构本身对齐2026前沿的复杂度自适应粒度方向（ElementCheck/B6）**。
3. 最强三证据组合：MiniCheck推理分解消融（反例自认）+ verdict≠span（定位是独立能力）+ B3对齐瓶颈（分解有效的前提是证据配对——我们已满足）。三条同时引用=既不神话分解也不虚无分解。

---

## 4. 仓库材料索引（本取证引用）

| 材料 | 路径 | 用途 |
|------|------|------|
| 88号（分解文献取证） | `docs/srs_project/88_claim_decomposition_literature.md` | 验证单元视角结论（三条件/MiniCheck澄清/(b)判定），本文不重复 |
| MiniCheck全文精读 | `literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1 | MiniCheck行+Q3 |
| SummaC精读 | `literature_survey/modular_verification_architecture_survey.md` E2 | 句切分/矩阵/粒度最优 |
| FICLE精读 | 同上 E4 | span三层标注+分阶段vs联合 |
| Two Truths（LLM上限） | 同上 E3 | 路径5负面证据 |
| FActScore/VERISCORE/AlignScore/CoVe/SAFE注 | `literature_survey/pair_classifier_sota_2023_2025.md` A2/A3/A4/A6 | 表1 |
| ContractNLI+后继（CLAUSE/Verdicts Without Annotated Evidence/Know Your Limits） | `five_direction_method_survey_and_cascadeverify_v2_design.md` §1.3 | 文档NLI定位线 |
| CoVe/Self-RAG精读 | `literature_survey/id_graph_positioning_survey.md` 表1 | 表1 |
| Kontrast/法规不一致 | 同上 方向4/方向5 | 表2 |
| AVeriTeC/B3/B4/B6/B9/FARCA | `literature_survey/cascade_innovation_expansion_survey.md` B1/B3/B4/B9/E3、B-Ⅱ/Ⅲ | 评测协议+2026粒度前沿 |
| RE四十年史（Bendík/Reder&Egyed/Femmer/LegalWiz/S3CDA系） | `literature_survey/inconsistency_history_survey.md` | 表2 RE行+Q2粒度欠账 |
| FEVER/ContractNLI标注协议 | `literature_survey/no_human_annotation_eval_survey.md` §1.4 | FEVER行 |
| CiteVQA归因幻觉 | `literature_survey/dataset_enhancement_method_upgrade_survey.md` | 定位是独立能力 |
| GEAR | `literature_survey/graph_representation_consistency_survey.md` | 表1 |
| DocNLI/粒度诊断 | `literature_survey/nlp4re_llm4re_comprehensive_survey.md`、`open_problems_analysis.md` | Q2 |
| 句对级无定位/聚合误差不可见 | `technical_landscape_acdd_positioning.md` F4、`inconsistency_history_survey.md` §5.2 | 表2末行 |
| 管线输出契约Y={S,R,N}×ℓ×j | `five_direction_method_survey_and_cascadeverify_v2_design.md` | Q3需求定义 |

## 5. 待核实清单

1. **RARR**：仓库零覆盖。标题"RARR: Researching and Revising what Language Models Say, Responsibly"、EMNLP 2023、arXiv 2210.08726、Gao et al.(Google)、invariance约束与PIBB指标——全部凭记忆，引用前必核原文。
2. **TRUE/QAFactEval**：沿88§7待核实项1/2（仓库无材料；QAFactEval的QG模型配置、答案比较器细节未核）。
3. **AlignScore**：chunk内部配对机制（双侧切块后如何配对打分、聚合方式）需回原文（arXiv 2305.16739）；88仅记"chunk机械切分"。
4. **SAFE**：arXiv编号与机制凭记忆（约2403.18802），仓库仅一句注提；引用前必核。
5. **"compound hypothesis"作为RTE/NLI文献术语**：凭印象（RTE传统讨论），未在仓库或在线核验到出处。
6. **经典NLI数据集构造细节**（SNLI标注流程/ANLI轮次/CMNLI构成）：常识性记忆，作者列表与数字引用前需核对（沿88§7.3口径）。
7. **2026前沿论文编号**（B3/B4/B6/B9/FARCA/Kontrast/CiteVQA等）：沿用仓库调研登记，本取证未二次核验（沿88§7.5口径）。
8. **ProgramFC**：定位能力描述基于仓库B2一句话概括，原文未读。
9. **MiniCheck用于长answer定位的组合先例**（外部切分+逐条MiniCheck的系统化用法）："由调用方自建"是从其接口形态的推断，具体组合系统待核实。
