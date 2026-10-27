# 44 方向A任务形式化定义与建模 v4：实体提取 + 上下文关联

日期：2026-10-21 | 范围：仅方向A（A1证据检索、A2 occurrence关联/条目聚合）
依据：00_requirements_and_route_overview.md、39_project_architecture_audit.md、40_method_reconstruction_plan.md、41_a_lane_spec.md；三路审计综合修订。

## 0. 结论先行：严格只有两个构件

```text
构件1：关键实体与事实的提取、命名、结构化展示
    ↓ 提供可回源、可比较的 occurrence / claim / entity 候选
构件2：上下文关联
    ├─ A1 召回：question → 回答信息需求所需的文本/表格/图片证据
    └─ A2 关联：occurrence ↔ occurrence → 同一 item 的候选证据链/条目
```

“类似证据/推荐”**不是第三构件**。它只是构件2中的“语义近邻候选”关系：可帮助补充或展示相关上下文，但不能仅凭相似就合并为同一条目，也不能作为已经证实的同一事实。

方向A不输出 answer verdict、不做GJB合规结论、不做ACDD来源差异判定；这些边界以项目级39/40号文档为准。

## 1. 场景与目标

输入是GJB格式SRS中分散的 occurrence：正文段落、表格行/单元格、图题/图中元素、追溯项等。当前主评测集中于16份SRS的表格行和图片元素；正文块已进入B2原型。目标是：

1. 识别和结构化文档中的关键实体与事实，保留原文及来源位置；
2. 按question的信息需求找到可用证据；
3. 从命中证据继续恢复相关 occurrence，并区分同一身份、显式引用和语义近邻；
4. 输出可回源、可解释的证据链/条目，供人工查看或下游模块消费。

本任务不是开放域QA，不判断答案正确性，也不把检索R@k当成条目聚合质量。

## 2. 构件1：提取、命名与结构化解析展示

关键建模原则：**Entity（实体）、Occurrence（一次出现）、Claim（事实声明）是三个不同对象。**不能把一段文本直接压成一个“实体”，也不能把重复出现误认为已证明同一。

### 2.1 最小数据对象

```text
SourceRef
  = {doc_id, doc_version, source_type, section, page,
     block/row/cell/node/region, raw_asset_ref}

Occurrence
  = {occurrence_id, source_ref, raw_text, parsed_payload,
     parse_status, extraction_method, extraction_confidence}

EntityCandidate
  = {candidate_id, entity_type, canonical_name?, aliases?, key?}
  注：只是规范化候选，不代表已与其他候选合并。

Claim
  = {claim_id, occurrence_id, subject, predicate, object/value,
     operator, unit, condition/scope, source_spans, parse_status}
```

关系约束：Occurrence可以表达零到多条Claim；一个EntityCandidate可被多个Occurrence提及；Occurrence到Entity的身份链接由构件2判断并保留候选状态。字段值须保留原文、规范化值和来源跨度，规范化不能覆盖原文。

**EntityCandidate与Item不等价**：EntityCandidate是“文档里可能指向哪个概念/对象”的规范化候选；Item是本任务中经过构件2关联后形成的Occurrence集合。一个实体可因版本、配置或作用域不同对应多个Item；Item也可包含多个实体（例如接口及其两端）。不能在构件1抽取时预先把二者合并。

### 2.2 不同模态如何结构化

| 来源 | 需要抽取/展示的结构 | 特有风险 |
|---|---|---|
| 正文 | 段落/句子、章节路径、实体/关系/原子claim | 条件句、否定、跨句指代被切块打断 |
| 表格 | 表头、行、单元格、合并单元格覆盖、续表关系、行角色 | 丢列头会改变数值含义；跨页续表不能当新表 |
| 图片/Visio | 图号/标题、锚点、图内实体/边、区域source_ref | OCR/VLM漏检、图号重复、图中关系不完整 |
| 追溯/合格性表 | 需求ID、验证方法、阶段、追溯目标 | 同一需求ID多处出现不等于所有文本都同一实体 |

解析不出、OCR/VLM不完整、合并单元格来源不确定时，要显式标记`partial/ambiguous/unparsed`；不能补成确定事实。

### 2.3 构件1职责与指标

构件1负责：原文固证、类型识别、字段/claim解析、候选命名规范化、来源定位和解析状态展示。它不负责跨位置身份合并、不负责召回排序、不推断缺失值、不判矛盾或合规。

验收指标：实体类型P/R/F1、字段槽位准确率/填充率、规范化误合并率、source_ref回源率、图表结构解析准确率、歧义保留率和解析置信度校准。当前只有chunks/词典/正则等素材，尚无统一实体层和该层gold。

## 3. 构件2A1：需求满足式证据召回

输入：`question + 可选检索范围(scope) + 构件1的Occurrence/Claim索引`。输出：按`R_answer(q,e)`排序的文本、表格、图片证据，带source_ref和召回轨迹。

“相关”不是单一字面相似度，而是证据能否满足question的信息需求，包含三种可分辨信号：

| 关系 | 含义 | 例子 |
|---|---|---|
| R_lex 字面匹配 | 编号、代码、精确词直接命中 | “图3”找到图3 |
| R_eq 语义等价 | 同义词、缩写、语体改写 | “汇聚”匹配“归集” |
| R_inf 受控推断 | question和证据间需要明确的领域推断 | “无格式”→“非结构化”→对应功能行 |

R_inf必须保留推断依据/路径，不能把推断结果伪装成原文事实。A1主指标是答案证据Recall@k/MRR及分层；还需oracle-context覆盖率，不等于下游校验准确率。

## 4. 构件2A2：Occurrence关联与条目聚合

输入是构件1产出的Occurrence和Claim；输出是**可审计的候选链接图**，通过决策后再形成Item：

```text
CandidateLink
  = {source_occurrence, target_occurrence, relation_type,
     direction, evidence_refs, confidence, status}

Item
  = {item_id, entity_key?, semantic_role?, occurrences[],
     accepted_links[], unresolved_links[], completeness_status}
```

关系至少分为：

| 关系 | 例子 | 处理原则 |
|---|---|---|
| same_identity | 同一需求代码在用例表和合格性表出现 | 高置信键证据可支持同一条目，但保留出处 |
| explicit_reference | 正文“如图N所示”指向图N | 保留方向和原始引用；不能改成无方向相似边 |
| structural_membership | 单元格属于某表/图元素属于某图 | 构件1的结构事实，不等于实体共指 |
| semantic_neighbor | 兄弟功能、类似参数、模板相似行 | **候选相似证据；默认不合并** |

因此“类似证据”不是额外构件：它是A2的一种候选关系，可用于补充上下文；只有存在身份/引用/结构证据并通过链接准则时，才进入同一Item。

**方向与停止条件**：`same_identity`候选可以对称；`explicit_reference`、追溯映射、依赖等关系必须保留source→target方向。链扩展在以下任一条件停止：scope内无新候选边、剩余边低于预设置信阈值、达到预设跳数/预算、或遇到版本/作用域冲突。停止时输出`complete/partial/open/ambiguous`及原因；“遍历结束”不自动等于“条目完整”。

### 4.1 A2指标

链接级Precision/Recall/F1、错误合并率、聚合完整率（同一gold item的Occurrence找齐比例）、关系类型/方向准确率、跨模态链接准确率。现有B2的ID召回0.988只是结构代理，不是链接质量gold；连通分量原型也不能直接称为最终聚合准确率。

## 5. 端到端契约和输出

```text
原始SRS → 构件1: Occurrence/Claim/EntityCandidate
        → 构件2-A1: question → 排序EvidenceContext
        → 构件2-A2: Occurrence对 → typed CandidateLink → Item/证据链
        → 冻结上下文交给下游；方向A本身不产出answer verdict
```

输出应同时包括结构化实体卡片、证据链、每条链接的类型/方向/依据/置信度，以及未解析或未覆盖的范围；不能只输出ranked list或一个“已关联”标签。

## 6. 场景覆盖矩阵与遗漏

| 场景 | 构件1解析对象 | A1召回目标 | A2链接目标 | 当前可测性 |
|---|---|---|---|---|
| 问参数/代码 | 参数claim、代码槽位、单位/条件 | 含答案的行/片段 | 同一参数多处出现 | 部分；claim尚未规范化 |
| 同义/缩写/口语 | 原词+规范候选+source span | 等价表达证据 | alias/coreference候选 | 召回可测，实体消歧gold缺 |
| 图表引用 | 图号/表号/标题/区域锚点 | 被引用图表/行 | 有向引用边 | 素材有，解析覆盖待验 |
| 多处需求展开 | 各Occurrence及角色 | 任一相关证据 | 定义/合格性/追溯/图示归同Item | B2原型，链接gold缺 |
| 类似兄弟需求 | 类型和区分字段 | 可选辅助证据 | semantic_neighbor候选 | kNN原型，不可自动并同条目 |
| 重复模板/同名异义 | 文档版本/系统/配置作用域 | scope内正确证据 | 同名实体消歧 | 多gold部分覆盖，scope不足 |
| 无答案/范围不足 | 解析状态/范围 | 当前范围内最相关证据 | 保留缺口，不推断不存在 | 可记录，完整性契约未完成 |
| OCR/VLM漏检 | 原始区域+抽取状态/置信 | 回源/其他模态候选 | 不完整链保留缺口 | 置信度与区域级source_ref待实现 |
| 多跳关系 | 中间claim/关系类型 | 起点与中间证据 | 多跳链/停止条件 | 当前以一跳为主 |
| 版本/时间差异 | doc_version/valid_time | 指定版本范围 | 不同版本分开关联 | 当前静态快照，时序不可测 |
| question歧义/多意图 | 一个或多个意图、实体/属性槽位 | 每个意图分别召回并保留分组 | 各意图结果可共享Occurrence但不强并 | 当前查询多为单意图，未系统评测 |
| 同一Item内事实冲突 | 多个claim及各自source_ref | 召回所有相关Occurrence，不选边站 | 标记`conflicting_occurrences`供下游处理 | A侧保留冲突，不裁决真伪 |

## 7. 边界与验收原则

1. 顶层永远只有两个构件：构件1结构化解析；构件2召回+关联/条目。
2. 构件1的EntityCandidate不等于A2确认后的Entity/Item；Occurrence不等于Claim。
3. 相似只产生候选邻居；不得用语义近邻代替身份链接或显式引用。
4. 开放世界下“未找到”不等于“文档不存在”；A1需记录检索范围，A2需记录未解析/未覆盖项。
5. A1排序指标、A2链接/聚合指标分开；任何一个都不等于B的answer三态或C的合规成绩。
6. 当前真实空白：构件1缺统一schema/gold；A2缺链接级gold、错误合并率和链完整性停止判据；A1到下游冻结EvidenceContext契约未实现。多意图、版本时间、冲突Occurrence也尚未形成可评测任务。

详细任务边界和执行顺序见41_a_lane_spec.md；项目级审计/下游B契约见39_project_architecture_audit.md与40_method_reconstruction_plan.md。
