# 用LLM从需求文档中提取结构化实体与关系 — 技术调研报告

> 调研日期: 2026-07-30
> 调研目标: 为"用LLM从自然语言SRS中提取需求实体(Actor/Action/Object/Condition/Constraint)与关系(depends-on/conflicts-with/refines)"提供方法依据与prompt策略
> 检索范围: arXiv API + 项目已有调研(知识融合/数据治理/一致性检测共128篇), 重点关注2023–2026年工作
> 与已有调研关系: 本文聚焦"抽取环节的LLM prompt策略", 补充`知识融合技术调研报告.md`(聚焦规则/本体验证)与`SURVEY_SUMMARY.md`(聚焦一致性检测)未覆盖的抽取方法学

---

## 0. 速览：核心结论

| 子问题 | 最佳实践(2023–2026共识) | 关键论文 |
|---|---|---|
| LLM-IE最佳prompt模式 | **Few-shot + CoT + 结构化输出schema**, 复杂关系加Self-Consistency投票 | 2312.17617, 2407.12994 |
| 输出结构化JSON | **Function calling / JSON mode** 优先; 无该能力时用**Grammar-Constrained Decoding(GCD)**硬保证格式 | 2305.13971, 2411.15100, 2505.04016 |
| 长文档处理 | **章节分块 + 层级抽取**; 跨块用RAG/预实体查询解决共指与"长上下文遗忘" | 2504.09823, 2412.20072, 2407.07799 |
| 减少幻觉 | **本体/词典约束解码 + 逐条证据quote + 置信度过滤 + 多版本保留** | 2408.02361, 2606.00994, 2606.00898 |
| 需求关系/冲突识别 | LLM做**关系抽取(RE)**效果好; 冲突检测需**形式化兜底**(Dung论辩/Z3), 纯LLM易漏检 | 2604.23124, 2403.16289 |
| 本体约束输出 | **Schema-constrained generation**: 把GJB本体作为input-dependent grammar注入解码 | 2305.13971, 2510.01409 |
| 证据溯源 | 每条抽取值绑定**verbatim原文quote + 章节号/页码**, 三层校验(子串匹配→quote支持值→人工) | 2606.00994, 2407.07799 |
| LLM在RE中表现好/差 | **问答/生成/合规**好; **精确实体边界/数值约束/冲突判定**差, 需符号兜底 | 2307.07381, 2507.03405 |

---

## 一、LLM-IE的prompt策略分类与最佳实践

### 1.1 prompt模式谱系(基于2312.17617《LLMs for Generative IE: A Survey》与2407.12994《Prompt Engineering Survey》)

该综述将LLM做信息抽取(IE)的技术分为四代范式, 现阶段LLM-IE主要采用**生成式范式**:

| 范式 | 机制 | 代表 | 适用 |
|---|---|---|---|
| 规则/监督 | 正则+BERT-CRF/BiLSTM | 传统OpenIE | 有标注、关系封闭 |
| Prompt-tuning | 软提示/前缀调优 | LAMA | 中等规模、可微调 |
| **In-Context Learning(本调研重点)** | zero/few-shot + CoT, 不更新参数 | GPT-4/Claude/GLM | 无标注、快速迁移、**SRS场景** |
| Instruction-tuning | 用IE指令微调LLM | InstructUIE, TechGPT-2.0 | 有一定指令数据 |

#### (a) Zero-shot vs Few-shot
- **Few-shot稳定优于zero-shot**: 综述与项目实测一致。few-shot示例同时承担**任务定义+输出格式示范+边界case**三重作用, 对IE这种"输出空间需精确定义"的任务尤其关键。
- **示例数**: 2–4个即可收敛; 超过8个边际收益骤降且挤占上下文。关键不是数量而是**覆盖度**——示例应覆盖所有关系类型与至少一个"无目标/空输出"负例。
- **示例选择**: 优先选**与当前输入同章节类型**的示例(retrieval-based few-shot), 而非固定示例, 可再提升3–8%F1(类比RAGTAG 2404.12772的检索增强思路)。

#### (b) Chain-of-Thought(CoT)
- CoT对**关系抽取与冲突推理**收益最大(需多步推理: 先识别实体→判断关系类型→校验方向); 对**简单实体抽取**收益小甚至有害(增加输出长度、引入噪声)。
- **Constrained CoT**(2408.02361): 在CoT解码分支空间中, 把推理路径**约束在本体术语/关系词表内**, 选置信度超阈的分支。这是把CoT与本体约束结合的典范, 直接降低幻觉, 在one-shot设定下仍提升泛化。
- **Self-Consistency**: 对同一输入采样N条CoT推理(temperature=0.7), 多数投票出最终三元组, 显著降低关系方向/类型错误。代价是N倍API调用, 建议仅对"高价值/有歧义"条目启用。

#### (c) 最佳prompt模式(综合建议)
```
[角色] + [任务定义+输出schema] + [本体/词表约束] + [2-4个few-shot示例(含负例)] 
+ [待抽取文本(带章节号/页码锚点)] + [要求:逐条附verbatim原文quote]
```
这与项目现有`EXTRACTION_PROMPT`结构高度一致, 差异在于: 现有prompt缺**本体约束声明**、缺**逐条quote**、示例未含负例。

### 1.2 结构化JSON输出: function calling / JSON mode / 约束解码

| 方法 | 原理 | 格式保证 | 推荐度 |
|---|---|---|---|
| **Function calling / Tools API** | 把输出schema定义为function参数, 模型填充 | 框架级强保证 | ★★★★★(若API支持) |
| **JSON mode** | 强制输出合法JSON | 保证合法JSON, 不保证schema | ★★★★ |
| **Grammar-Constrained Decoding(GCD)** | token级掩码, 保证输出符合CFG/正则/JSON Schema | **数学级100%保证** | ★★★★★(无FC时) |
| 纯prompt"只输出JSON" | 靠指令约束 | 无保证, 偶发包裹文字/注释 | ★★(项目现状) |

- **2305.13971(GCD, EPFL)**: 提出**input-dependent grammar**——grammar可依赖输入(如实体候选集), 用CFG描述输出空间, 无需微调即可让off-the-shelf LLM在IE/实体消歧/句法分析上**超越任务专用微调模型**。这是"schema-constrained generation"的代表。
- **2411.15100(XGrammar)**: 高效结构化生成引擎, 平衡约束严格度与生成质量, 支持复杂嵌套JSON, 适合Agent/IE场景。
- **2505.04016(SLOT)**: 专门解决"LLM输出偏离预定义schema"问题, 对IE等结构化关键应用尤其重要。
- **权衡警示(2603.03305)**: 约束解码有**"对齐税"**——过度严格的token级掩码会扭曲生成分布、损害内容质量。建议schema约束**只锁结构不锁语义值**(锁键名/类型/枚举, 放开自由文本字段), 并优先用FC/JSON mode这种"软约束"而非硬掩码, 除非格式失败率高。

> **项目现状**: `srs_constraint_extract.py`用纯prompt"只输出JSON数组"+`temperature=0.1`, 靠低温+示例约束格式, 偶发包裹```json```围栏。GLM-5若支持JSON mode/function calling应优先启用; 否则用GCD兜底。

### 1.3 长文档处理: chunking / 层级抽取 / RAG

SRS动辄数十页, 远超上下文窗口, 三类策略:

| 策略 | 方法 | 解决的核心问题 | 代表 |
|---|---|---|---|
| **章节分块** | 按GJB章节树切分, 块内独立抽取 | 单次输入超长 | 项目现状、2412.20072 |
| **层级抽取** | 先章节级抽实体, 再文档级抽跨章节关系 | 跨块关系丢失 | 2504.09823(RAKG) |
| **RAG增强抽取** | 用预实体/概念做query检索相关块再抽取 | 长上下文遗忘、共指消解 | 2504.09823, 2404.12772 |

- **2504.09823(RAKG)** — 最相关: 文档级RAG增强KG构建。先用文本块抽**预实体(pre-entities)**, 再以预实体为query做RAG检索相关块, 有效解决LLM**长上下文遗忘**与**共指消解**复杂度, 比GraphRAG在MINE数据集上准确率高6.2pt(95.91% vs 89.71%)。并把RAG评估框架迁移到KGC, 过滤幻觉实体/关系。
- **2412.20072(AIE框架)** — 混合长文档(文本+表格): 给出4条发现: ①有效选取并摘要HLD有用部分; ②简单表格序列化即可让LLM理解表格; ③朴素AIE在复杂场景有适应性; ④针对性prompt工程增强HLD抽取。
- **2407.07799(Attribute or Abstain)** — 长文档+归因: 在长文档(无需检索)设定下评估"归因(attribution)"。发现: **大模型/微调模型用"一步法"(生成答案+抽证据同一步)最优**; 小模型/纯prompt模型需额外检索辅助。且未发现"Lost in the Middle"对归因的影响。

> **对SRS的启示**: 项目已按章节分块(✓)。关键升级是**层级抽取**: 第1遍章节内抽实体+局部约束(现状); 第2遍把所有实体/约束作为全局context, 用RAKG式预实体查询检索跨章节依赖/冲突关系。这直接解决"约束散落各章导致Z3全假阳性"的历史痛点。

### 1.4 减少幻觉: grounding / evidence citation / constrained decoding

四类互补手段(综合2606.00994、2606.00898、2408.02361):

| 手段 | 机制 | 落地 |
|---|---|---|
| **约束解码** | 把输出值限制在本体/词表内 | GCD约束实体类型、关系类型枚举 |
| **逐条证据quote** | 每条抽取值必须附verbatim原文片段 | prompt要求+后处理子串校验 |
| **置信度过滤** | LLM自评high/medium/low, low直接丢弃 | 多版本保留, 不静默丢 |
| **子串校验+quote-supports-value审计** | 校验quote是否真是源文本子串, 再校验quote是否支持该值 | 三层递减证据强度验证 |

- **2606.00994(Registry-Bound LLM Pipeline)** — 最完整的可审计抽取范式: 四机制使每行可审计——①版本化39键**闭词汇表trait registry**(类型化schema约束每个值); ②每行**verbatim证据quote**绑定源文本; ③每行**置信度标签**(high/medium; low预持久化前丢弃); ④**多版本保留**。三层校验: 全量子串匹配90.12%→quote-supports-value审计(n=100, 100/100)→red-zone人工(n=50, 50/50)。这正是SRS抽取应模仿的"可审计抽取"框架。
- **2606.00898(Citation Grounding)**: 用**引文图谱**度量并降低LLM引文幻觉, 提出citation grounding指标。可迁移为"标准条文引用图谱", 校验LLM声称"符合GJB某条"是否真实。

---

## 二、LLM在需求工程中的具体应用(LLM4RE)

### 2.1 LLM4RE任务全景与"好/差"任务

基于2507.03405《Prompt Engineering Guidelines for LLM in RE》、2307.07381《ChatGPT for Requirements Elicitation》、2508.09648(ReqInOne):

| 任务 | LLM表现 | 说明 |
|---|---|---|
| 需求**问答/澄清/解释** | ★★★★★ 好 | 用户提到的"需求问答是LLM表现较好的任务"得到验证——ChatGPT生成需求在Abstract/Atomic/Consistent/Correct/Understandable五维接近专家(2307.07381) |
| 需求**生成/补全/改写** | ★★★★ 好 | ReqInOne(2508.09648)用LLM Agent端到端生成SRS |
| **合规性检查**(格式/结构) | ★★★★ 好 | Okamoto(2025)GPT-4查SRS是否符合标准格式 |
| 需求**分类/聚类** | ★★★★ 好 | few-shot即可 |
| 需求**实体/关系抽取** | ★★★ 中 | 关系抽取优于实体边界; 需本体约束+证据兜底 |
| **数值约束抽取** | ★★ 中差 | 数值/单位/算子易错, 需后处理Z3校验(项目历史痛点) |
| **冲突检测** | ★★ 中差 | 纯LLM易漏检隐性冲突, **必须形式化兜底** |
| **可追踪性恢复** | ★★★ 中 | 跨文档链接, RAG辅助 |

> 2507.03405结论: 现有prompt engineering指南**缺乏领域特定(尤其RE)指导**, 该文通过系统综述+专家访谈建立RE任务↔prompt策略映射, 是RE场景prompt设计的直接参考。

### 2.2 需求抽取的典型pipeline

综合各工作, LLM需求抽取的标准pipeline为:

```
SRS文档
  → [文档解析] MinerU/章节树/表格结构化(项目已完成)
  → [章节分块] 按GJB章节切分(项目已完成)
  → [第1遍: 实体抽取] 每章few-shot抽 Actor/Action/Object/Condition/Constraint
  → [第2遍: 关系抽取] 全局实体集为context, 抽 depends-on/conflicts-with/refines
  → [本体约束校验] GJB本体/SHACL校验实体类型、基数、值域
  → [证据绑定] 每条三元组附verbatim quote+章节号
  → [Z3/SMT编码] 数值/逻辑约束→Z3, 求解可满足性(项目v2已完成)
  → [一致性报告] 语法/语义/逻辑三层(项目已完成)
```
项目已覆盖解析、分块、第1遍约束抽取、Z3求解、报告; **缺第2遍关系抽取、本体约束校验、证据绑定**——这正是本调研要补的环节。

### 2.3 需求关系识别方法

- **生成式关系抽取(RE)**: 把"判断两需求间关系"建模为生成任务, prompt给出候选实体对+关系枚举, LLM输出关系类型+方向+证据。CoT+Self-Consistency提升稳定性。
- **Constrained CoT for RE(2408.02361)**: 在解码分支空间中约束关系类型于本体枚举内, 多分支选置信度超阈者, 显著降幻觉。可直接迁移到depends-on/conflicts-with/refines抽取。
- **KG补全式预测缺失关系**: 用RotatE/AnyBURL在已抽KG上预测未显式标注的依赖/追溯关系(见`知识融合技术调研报告.md`方向2), 适合SRS中"隐含依赖"发现。

### 2.4 需求冲突检测方法(关键: 不能纯靠LLM)

- **2604.23124(ArgRE)** — 最相关: 多Agent需求协商中, 把每个提案/批评/细化建模为**Dung抽象论辩**的argument, 冲突表示为有向攻击关系, 在grounded/preferred语义下计算被接受论证集。结合KAOS目标建模+多层验证+标准导向产物生成。评估: 论证级可追溯性, 决策理由评分4.32 vs 启发式3.07(p<0.001), 合规覆盖84.7% vs 基线47.6%。**启示**: 冲突检测需"显式论证+形式化语义", 而非LLM隐式聚合。
- **2403.16289(自动驾驶安全需求)**: LLM pipeline接收item定义→输出安全需求, 并**评审需求集识别冗余/矛盾需求**。设计科学多轮迭代+专家评估。证明LLM可辅助冲突初筛, 但需专家闭环。
- **ReqV(1804.10486)+Chen2025(2506.16639)**(项目已有): LLM把NL约束翻译为SMT→Z3求解矛盾。这是数值/逻辑冲突的金标准, 纯LLM判断不可靠。

> **结论**: 需求冲突检测应**分层**——LLM做粗筛(语义层矛盾/明显冲突), **形式化(Z3/Dung论辩)做精确判定**(数值/逻辑/传递依赖环路)。这与项目三层检测架构完全吻合。

---

## 三、Ontology-guided Extraction方法

### 3.1 本体如何约束LLM抽取输出

三种递进强度(综合2310.01409、2408.02361、2305.13971、2510.01409):

| 强度 | 机制 | 实现 |
|---|---|---|
| **Prompt级(软约束)** | 把本体(实体类型/关系枚举/属性)写入prompt作为"只能从以下选取"指令 | 最易落地, 无保证 |
| **Schema-constrained generation(硬约束)** | 把本体转为JSON Schema/CFG, 解码时token掩码保证输出符合 | GCD/XGrammar |
| **迭代校正(闭环)** | LLM生成→本体一致性检查(SHACL/OWL)→反馈修正→再生成 | OntoLogX式 |

- **2510.01409(OntoLogX)** — 最贴合SRS: 自主AI Agent用LLM把原始日志转为**本体接地KG**。集成**轻量级日志本体 + RAG + 迭代校正步骤**, 确保生成KG语法/语义合法。再聚合到会话级, 用LLM预测MITRE ATT&CK战术, 把低层证据链到高层目标。结论: **检索+校正对precision/recall均有益**, 代码导向模型在结构化日志分析上有效。可直接迁移为"OntoLogX-for-SRS": 轻量GJB本体+RAG+迭代校正→SRS需求KG。
- **2408.02361(Constrained CoT)**: 关系抽取时约束解码于本体术语+关系, 降幻觉(见1.1b)。
- **2307.16648(LLMs4OL) / 2410.23584(OLLM)**(项目已有): 用LLM从零构建本体分类骨架。可作为"GJB本体自动构建"的备选, 但项目已有手工GJB规则库, 更适合做**约束源**而非重建。

### 3.2 Ontology-guided vs Free-form extraction

| 维度 | Ontology-guided | Free-form(OpenIE) |
|---|---|---|
| 精度 | 高(值域受限) | 中(易幻觉) |
| 召回 | 中(只抽本体定义的) | 高(可发现新关系) |
| 可控/可验证 | ★★★★★ | ★★ |
| 适合SRS | ★★★★★(GJB有明确结构) | ★★(SRS非开放域) |
| 新颖关系发现 | 差 | 好 |

> SRS是**强结构化域**(GJB 438C规定了章节/字段/类型), 应以**ontology-guided为主**; 对"设计图描述/接口说明"等半结构化部分, 可用free-form兜底发现本体未覆盖概念, 再人工纳入本体。这正契合项目"GJB规则库+差距分析"现状。

### 3.3 Schema-constrained generation的方法栈

- **2305.13971(GCD)**: input-dependent grammar是关键创新——grammar可依赖输入(如该文档已抽实体集), 实现不同输入不同输出结构。无需微调, off-the-shelf LLM即可超越微调模型。
- **2411.15100(XGrammar)**: 平衡约束与质量, 支持复杂嵌套。
- **2604.14862(Schema Key Wording)**: 提示schema的**键名措辞本身是指令通道**, 会引导生成——设计schema键名时需谨慎(对prompt设计有直接启示: 字段命名要语义明确)。
- **2603.03305(对齐税警示)**: 约束解码可能扭曲分布、引发"幻觉雪球"。建议只锁结构、放开语义值字段。

---

## 四、Evidence-grounded Extraction方法

### 4.1 让LLM标注抽取内容来源位置

三类溯源粒度(综合2606.00994、2407.07799):

| 粒度 | 标注内容 | 实现 |
|---|---|---|
| **章节级** | 章节号/标题 | 项目已有(section_number) |
| **句段级(推荐)** | verbatim原文quote + 章节号 | prompt要求+子串校验 |
| **字符级** | 页码/行号/offset | 需解析层保留offset, 较重 |

- **最佳实践(2606.00994)**: 每条抽取值绑定**verbatim evidence quote**(逐字原文片段), 而非仅章节号。原因: 章节号粒度太粗无法定位; quote可机器校验(子串匹配)且人类可读。SRS场景建议quote+章节号双绑。
- **一步法vs两步法(2407.07799)**: 大模型用**一步法**(生成答案+抽证据同一次调用)最优; 小模型需两步(先答再检索证据)。项目用GLM-5, 建议一步法: 在extraction prompt中直接要求每条输出含`evidence_quote`字段。
- **页码/行号**: 需MinerU解析时保留页码与字符offset。项目MinerU输出含页码信息, 可在structurer阶段把章节文本与页码绑定, 抽取时回填。

### 4.2 Evidence-grounded extraction的评测方法

沿用2606.00994的三层递减证据强度校验, 迁移到SRS:

1. **全量子串校验(自动)**: 校验`evidence_quote`是否为源文本的verbatim子串(容错: 去空白/标点)。统计子串命中率(参考90.12%)。
2. **quote-supports-value审计(抽样, 自动/半自动)**: 抽n=100, 用独立LLM判断"quote是否真的支持该抽取值"。参考100/100。
3. **red-zone人工(高风险抽样)**: 对数值约束/冲突关系等高风险条目, 人工face-validity校验。参考50/50。
4. **对齐Gold Standard**: 项目已有`srs_eval.py`对齐battery/compiler/scheduler三份Gold, 按层算P/R/F1——把evidence质量作为额外维度(quote命中率)纳入评测。

### 4.3 RAG与extraction的结合方式

- **RAKG(2504.09823)**: 预实体做query的RAG, 解决长上下文遗忘+共指。**抽取阶段用RAG**(不是问答阶段), 这是与传统RAG-QA的关键区别。
- **RAGTAG(2404.12772)**: RAG把领域知识注入LLM, 生成测试场景。启示: 把**GJB标准条文作为RAG知识库**, 抽取时检索相关标准条文注入prompt, 既约束抽取(ontology-in-context)又提供合规依据。
- **结合模式**: 
  - **抽取前RAG**: 检索GJB相关条文/同类型已抽KG, 作为few-shot/约束注入。
  - **抽取后RAG-filter**: 用检索校验抽取三元组是否被源文/标准支持, 过滤幻觉(RAKG式)。

---

## 五、具体prompt设计示例(针对SRS实体关系抽取)

基于上述最佳实践, 给出可直接用于项目的两级抽取prompt设计。延续项目现有`EXTRACTION_PROMPT`风格(GLM-5, 中文, JSON输出, few-shot)。

### 5.1 输出Schema定义

```json
{
  "entities": [
    {"id": "E1", "type": "Actor|Action|Object|Condition|Constraint|Parameter",
     "name": "补偿计算模块", "normalized": "compensation_calc",
     "evidence_quote": "补偿计算时间不超过0.01ms",
     "loc": {"section": "3.2.1", "page": 12}}
  ],
  "relations": [
    {"src": "E1", "dst": "E2", "type": "depends-on|conflicts-with|refines|constrains",
     "evidence_quote": "...", "confidence": "high|medium", "loc": {...}}
  ],
  "constraints": [
    {"id": "C1", "type": "numerical|tolerance|...", "param": "...",
     "operator": "≤", "value": 0.01, "unit": "ms",
     "evidence_quote": "...", "z3_expr": "compensation_time <= 0.01", "loc": {...}}
  ]
}
```
关键设计: ①实体/关系/约束三类统一schema; ②每条都带`evidence_quote`(verbatim)+`loc`(章节/页); ③约束预生成`z3_expr`字段供下游Z3; ④`confidence`字段供过滤; ⑤实体有`normalized`规范名供跨块共指。

### 5.2 第1遍Prompt: 章节内实体+约束抽取

```
你是GJB 438C SRS文档分析专家。从以下SRS章节抽取【实体】与【约束】。

【本体约束 — 只能使用以下类型】
实体类型: Actor(执行主体), Action(动作), Object(操作对象), 
          Condition(条件/状态), Constraint(约束), Parameter(参数)
约束类型: numerical/tolerance/cumulative/temporal/conditional/default/design
关系类型: 本遍不抽关系(第2遍处理)

【输出要求】
- 严格输出JSON, 含entities[]与constraints[]
- 每条必须含evidence_quote(原文逐字片段)与loc(章节号+页码)
- 无则返回空数组
- 置信度低的标medium, 明确的标high

【示例】(few-shot, 含一个负例)
文本: "3.2.1 补偿计算模块应以0.01ms为上限完成计算。若超时进入告警。"
输出: {"entities":[{"id":"E1","type":"Actor","name":"补偿计算模块",...},
                   {"id":"E2","type":"Condition","name":"超时",...}],
       "constraints":[{"id":"C1","type":"numerical","param":"补偿计算时间",
                       "operator":"≤","value":0.01,"unit":"ms",
                       "evidence_quote":"以0.01ms为上限完成计算","z3_expr":"compensation_time<=0.01",...}]}
文本: "本节描述背景。" 
输出: {"entities":[],"constraints":[]}   ← 负例:无目标返回空

【待抽取】
章节: {section_number} {section_title}  页码: {page}
{section_text}
只输出JSON。
```

### 5.3 第2遍Prompt: 跨章节关系抽取(RAKG式全局context)

```
你是GJB 438C SRS一致性分析专家。基于已抽取的全局实体集, 识别实体间【关系】。

【关系类型 — 只能从以下选取】
- depends-on: A依赖B(B不满足则A无法实现)
- conflicts-with: A与B冲突(无法同时满足)  ← 仅标注明显冲突, 精确判定交Z3
- refines: A细化B(A是B的子需求/具体化)
- constrains: A约束B(A限制B的取值/行为)

【全局实体候选】(第1遍结果, 已去重规范化)
{global_entities_json}

【方法】对每对相关实体, 给出关系类型+方向+证据quote+置信度。
优先处理: 同章节跨实体、跨章节同名/同参数实体。
数值类潜在冲突: 列出conflicts-with候选交Z3, 不要自行判定可满足性。

【输出】{"relations":[...]} 每条含src/dst/type/evidence_quote/confidence/loc
只输出JSON。
```

### 5.4 Few-shot示例选择策略

- **Retrieval-based few-shot(推荐)**: 对每个待抽章节, 从已标注Gold(battery/compiler/scheduler)中检索**同章节类型**的示例注入。比固定示例更贴合, 参考2404.12772。
- **覆盖度优先**: 示例必须覆盖所有实体类型+所有约束类型+≥1个空输出负例。
- **边界case**: 含歧义句(如"约0.01ms"的"约"→design而非numerical)、跨章引用(如"见4.1节")。
- **数量**: 2–4个, 上下文紧张时用1个高质量+本体约束声明(参考2408.02361的one-shot设定仍有效)。

---

## 六、对项目的具体建议: 用LLM+GJB本体从SRS提取需求图谱

### 6.1 与项目现状的差距分析

项目`tools/srs_constraint_extract.py`现状(已验证良好):
- ✓ 章节分块、GLM-5、few-shot、JSON输出、temp=0.1、7类约束
- ✓ `original`字段记录原文句子(已有evidence雏形)

差距(本调研要补):
| 缺口 | 现状 | 目标 | 参考 |
|---|---|---|---|
| 实体抽取 | 只抽约束 | 抽Actor/Action/Object/Condition实体 | 2312.17617 |
| 关系抽取 | 无 | depends-on/conflicts-with/refines | 2408.02361 |
| 本体约束 | prompt内联类型 | GJB本体作为schema约束+迭代校正 | 2510.01409 |
| 证据溯源 | `original`句子 | verbatim quote+章节号+页码+子串校验 | 2606.00994 |
| 跨章节关系 | 无 | RAKG式第2遍全局关系抽取 | 2504.09823 |
| 格式保证 | 纯prompt | JSON mode/GCD兜底 | 2305.13971 |
| Z3衔接 | 手工 | 约束预生成`z3_expr`字段 | Chen2025 |
| 评测 | P/R/F1 | +quote命中率+quote-supports-value审计 | 2606.00994 |

### 6.2 推荐落地方案: 三阶段可审计抽取流水线

```
阶段0 [复用] MinerU解析→章节树+表格+页码绑定 (已完成)
阶段1 [升级] 章节内抽取: 现有constraint_extract升级为entity+constraint联合抽取
         - 启用GLM-5 JSON mode(若支持), 否则GCD兜底
         - prompt加入GJB本体类型枚举(软约束) + evidence_quote+loc字段
         - few-shot改retrieval-based(从Gold检索同类型章节)
阶段2 [新增] 跨章节关系抽取(RAKG式): 全局实体集→depends-on/conflicts-with/refines
         - Constrained CoT: 关系类型约束于枚举, 多分支选超阈
         - conflicts-with只标候选, 精确判定交Z3(项目v2已有)
阶段3 [新增] 本体迭代校正(OntoLogX式): SHACL校验→反馈修正→再生成
         - 用项目已有GJB规则库/SHACL Shapes校验实体类型/基数/值域
         - 违规项回灌LLM修正(参考xpSHACL生成解释)
阶段4 [复用+衔接] Z3求解: 约束z3_expr→可满足性(项目v2已完成)
评测 [升级] srs_eval增加evidence维度: quote子串命中率+quote-supports-value抽样审计
```

### 6.3 关键工程决策

1. **格式保证优先级**: GLM-5 JSON mode > Function calling > GCD > 纯prompt。先测GLM-5是否支持JSON mode, 支持则一步到位消除格式失败。
2. **约束解码谨慎用**: 只锁schema结构(键名/类型/枚举), 放开`evidence_quote`/`name`等自由文本字段, 避免"对齐税"(2603.03305)。
3. **冲突检测分层**: LLM只做语义矛盾初筛+conflicts-with候选标注; **数值/逻辑/传递依赖环路冲突一律交Z3/Dung论辩**(2604.23124), 这是项目v2 Z3集成的正确用法, 也解释了"之前Z3全假阳性是参数提取差"——升级阶段1的实体+约束抽取质量后Z3才有意义。
4. **证据三层校验自动化**: 全量子串校验(自动, 高覆盖)→quote-supports-value(抽样, 独立LLM)→red-zone人工(高风险)。把quote命中率作为抽取质量指标纳入`srs_eval`。
5. **本体不重建**: 项目已有GJB规则库+差距分析, 直接作为约束源, 不用OLLM从零建本体(成本高、SRS域窄)。
6. **Gold Standard扩展**: 现有3份Gold(battery/compiler/scheduler)既做评测也做retrieval-based few-shot的示例库, 一举两得。

### 6.4 风险与缓解

| 风险 | 缓解 |
|---|---|
| LLM数值/单位抽取错→Z3假阳性 | 约束预生成z3_expr后, 用原文quote反向校验数值; 低置信度不送Z3 |
| 约束解码对齐税 | 只锁结构不锁语义值; 优先JSON mode软约束 |
| 跨章节关系漏抽 | RAKG式预实体RAG检索; KG补全(RotatE)预测缺失关系 |
| 证据quote伪造 | 子串校验强制; 不匹配的标UNVERIFIED不丢弃(可审计) |
| GLM-5无JSON mode | GCD(XGrammar/GCD)兜底; 或正则后处理剥围栏 |

---

## 七、文献表(按本调研5个方向归类)

| # | 论文 | arXiv/会议 | 年 | 方向 | 要点 |
|---|---|---|---|---|---|
| 1 | LLMs for Generative Information Extraction: A Survey | 2312.17617 | 2023 | Q1 | LLM-IE生成式范式综述, 子任务+技术分类, 维护LLM4IE仓库 |
| 2 | A Survey on Open IE from Rule-based to LLM | 2208.08690 | 2022 | Q1 | OpenIE 2007–2024演进, 规则→神经→LLM |
| 3 | A Survey of Prompt Engineering Methods for NLP Tasks | 2407.12994 | 2024 | Q1 | 44篇/39方法/29任务prompt工程分类 |
| 4 | Grammar-Constrained Decoding for Structured NLP without Finetuning | 2305.13971 | 2023 | Q1/Q3 | input-dependent grammar, 无微调超微调模型, GCD代表 |
| 5 | XGrammar: Flexible Structured Generation Engine | 2411.15100 | 2024 | Q1 | 高效结构化生成, 平衡约束与质量 |
| 6 | SLOT: Structuring the Output of LLMs | 2505.04016 | 2025 | Q1 | 解决输出偏离schema问题 |
| 7 | The Hidden Cost of Structured Generation(对齐税) | 2603.03305 | 2026 | Q1 | 约束解码扭曲分布警示 |
| 8 | Schema Key Wording as Instruction Channel | 2604.14862 | 2026 | Q1 | schema键名措辞引导生成 |
| 9 | RAKG: Document-level Retrieval Augmented KG Construction | 2504.09823 | 2025 | Q1/Q4 | 预实体RAG解决长上下文遗忘+共指, 95.91% |
| 10 | Extract Info from Hybrid Long Docs: Framework+Dataset | 2412.20072 | 2024 | Q1 | HLD(文本+表格)抽取4发现, AIE框架 |
| 11 | Attribute or Abstain: LLMs as Long Document Assistants | 2407.07799 | 2024 | Q1/Q4 | 长文档归因, 一步法最优, LAB基准 |
| 12 | Registry-Bound LLM Pipeline for Evidence-Grounded Trait Extraction | 2606.00994 | 2026 | Q1/Q4 | 四机制可审计抽取+三层校验, 最完整范式 |
| 13 | Citation Grounding: Detect/Reduce LLM Citation Hallucinations | 2606.00898 | 2026 | Q1/Q4 | 引文图谱度量降幻觉 |
| 14 | Prompt Engineering Guidelines for LLM in RE | 2507.03405 | 2025 | Q2 | RE任务↔prompt策略映射, 系统综述+专家访谈 |
| 15 | Investigating ChatGPT for Requirements Elicitation | 2307.07381 | 2023 | Q2 | ChatGPT生成需求五维近专家, LLM4RE |
| 16 | ReqInOne: LLM Agent for SRS Generation | 2508.09648 | 2025 | Q2 | LLM Agent端到端生成SRS |
| 17 | Engineering Safety Requirements for AD with LLMs | 2403.16289 | 2024 | Q2 | LLM pipeline生成安全需求+识别冗余/矛盾 |
| 18 | Generating Test Scenarios from NL Requirements via RAG-LLM | 2404.12772 | 2024 | Q2/Q4 | RAGTAG工业RAG, 领域知识注入 |
| 19 | ArgRE: Formal Argumentation for Conflict Resolution in RE | 2604.23124 | 2026 | Q2 | Dung论辩+KAOS, 冲突形式化, 4.32 vs 3.07 |
| 20 | Dialogue Ontology Relation Extraction via Constrained CoT | 2408.02361 | 2024 | Q2/Q3 | CoT解码约束于本体术语, 降幻觉 |
| 21 | OntoLogX: Ontology-Guided KG Extraction from Logs with LLM | 2510.01409 | 2025 | Q3 | 轻量本体+RAG+迭代校正→合法KG, 最贴合SRS |
| 22 | LLMs4OL: LLMs for Ontology Learning | 2307.16648 | 2023 | Q3 | LLM做本体学习 |
| 23 | Meronymic Ontology Extraction via LLMs | 2510.13839 | 2025 | Q3 | 部分-整体本体抽取 |
| 24 | ConExion: Concept Extraction with LLMs | 2504.12915 | 2025 | Q3 | 文档概念抽取 |
| 25 | OLLM: End-to-End Ontology Learning with LLM | 2410.23584 | 2024 | Q3 | 微调LLM建本体骨架(项目已有) |
| 26 | xpSHACL: Explainable SHACL via RAG+LLM | 2507.08432 | 2025 | Q3 | RAG+LLM生成违规解释(项目已有) |
| 27 | Unifying LLMs and KGs: A Roadmap | 2306.08302 | 2024 | Q3 | LLM+KG三框架(项目已有) |
| 28 | TechGPT-2.0: LLM for KG Construction | 2401.04507 | 2024 | Q3 | LLM做NER/RE/PGC |
| 29 | CooperKGC: Multi-Agent Synergy for KG Construction | 2312.03022 | 2023 | Q3 | 多Agent协同KGC |
| 30 | DEFAME: Dynamic Evidence-based Fact-checking | 2412.10510 | 2025 | Q4 | 六阶段零样本多模态事实核查(项目已有) |
| 31 | AMREx: AMR for Explainable Fact Verification | 2411.01343 | 2024 | Q4 | AMR+Smatch语义包含验证(项目已有) |

---

## 八、一句话总结

> **最佳实践 = Few-shot + CoT + 本体schema约束 + 逐条verbatim证据quote + 置信度过滤 + 形式化(Z3/论辩)兜底冲突判定 + 章节分块/RAKG层级抽取处理长文档**。项目已有约束抽取+Z3+三层检测的骨架, 升级路径明确: 把`constraint_extract`扩成entity+relation+constraint联合抽取, 加evidence_quote+loc可审计字段, 用GJB本体做schema约束与SHACL迭代校正, 跨章关系用RAKG式第2遍——这正好补齐"三层一致性检测"上游的"需求图谱构建"环节, 形成完整闭环。
