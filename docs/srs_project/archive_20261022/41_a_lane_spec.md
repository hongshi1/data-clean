# 41 方向A车道规格：两个构件与子任务边界

日期：2026-10-20 | 最后对齐：2026-10-21 | 权威边界：00/39/40/44号文档

## 一、方向A的两个构件（顶层固定，不再混用A1/A2作顶层名）

```text
构件1 实体/事实提取与结构化展示
  原始SRS → 可回源Occurrence + EntityCandidate + Claim
                         │
构件2 上下文关联          │
  ├─ 子任务2a 需求满足式证据召回(question → evidence)
  └─ 子任务2b Occurrence关联与条目聚合(occurrence ↔ occurrence)
                         ↓
          冻结、可回源的EvidenceContext / Item链
                         ↓
          下游B消费；方向A不判answer verdict
```

项目旧称“A1=召回、A2=聚合”仍可作为**构件2内的两个子任务代号**，但不能再叫“两大构件”。本文及44号统一采用“构件1/构件2 + 子任务2a/2b”。

## 二、构件1：实体/事实提取与结构化展示

### 最小对象

| 对象 | 含义 | 责任边界 |
|---|---|---|
| SourceRef | 文档版本、来源类型、章节/页/块/行/单元格/图区域、原始资产引用 | 必须能回源 |
| Occurrence | 文本/表格/图中一次具体出现，保留raw_text、解析状态、来源 | 多次出现先分开保存，不预先合并 |
| EntityCandidate | 规范名/别名/代码等身份候选 | 候选不等于已确认同一实体 |
| Claim | 一次出现所表达的主谓宾/值/单位/条件/范围事实 | Claim不等于Entity，也不等于整段文本 |

三类source_type固定为`text_fragment/table_row/image_element`。标题、字段名、字段值、图号和图内锚点分别保留；OCR/VLM不完整、歧义、未解析须显式标记，不得静默补全。

**关键区分**：EntityCandidate是构件1提出的“可能指向哪个概念/对象”的规范化候选；Item是构件2基于多个Occurrence的链接决策形成的任务级集合。不同版本/配置的同名实体可以对应不同Item；一个Item也可能包含多个相关实体。构件1不得提前把候选合并成Item。

### 输出与指标

输出为结构化Occurrence/EntityCandidate/Claim列表及原文展示卡片。指标：实体类型P/R/F1、字段槽位准确率/填充率、规范化误合并率、source_ref回源率、表/图解析准确率、歧义保留率。当前已有chunks/词典/正则素材，但统一对象层和该层gold**未建立**。

## 三、构件2：上下文关联

### 子任务2a：需求满足式证据召回

| 项 | 契约 |
|---|---|
| 输入 | question + 可选scope + 构件1的Occurrence/Claim索引 |
| 输出 | 按信息需求排序的EvidenceContext（证据文本、source_type/source_ref、claim_refs、召回轨迹）；允许空结果、多候选和歧义，不伪造唯一答案 |
| 相关信号 | 字面R_lex、语义等价R_eq、受控推断R_inf；推断路径须可记录。相关排序不等同于“证据已充分回答问题” |
| 指标 | R@k/MRR/置信区间/分层；新增oracle-context覆盖率（检索结果覆盖gold所需证据比例） |
| 已有 | evidence_recall多头冻结投影+召回+精排；S1-S11；baseline统一头；S7/S8复现 |
| 差距 | 当前EvidenceStore来源类型与source_ref契约需补齐；oracle-context实验待B侧冻结QA/context |

### 子任务2b：Occurrence关联与条目聚合

```text
CandidateLink = {source_occurrence, target_occurrence, relation_type,
                 direction, evidence_refs, confidence, status}
Item = {item_id, entity_key?, semantic_role?, occurrences[],
        accepted_links[], unresolved_links[], completeness_status}
```

关系类型分开存：`same_identity`（身份共指）、`explicit_reference`（有向引用）、`structural_membership`（行/元素属于表/图）、`semantic_neighbor`（类似证据候选）。**semantic_neighbor不自动合并同一Item**；“类似证据”是构件2b中的候选关系/上下文，不是第三构件。

`same_identity`可为对称关系；引用、追溯、依赖必须保留source→target方向。scope/版本冲突时保留候选链接并标ambiguous/conflict，不强行合并。链扩展须有停止条件（scope内无新边、剩余边低于阈值、达到跳数/预算或遇到作用域冲突）；遍历结束不能自动宣称Item完整。未召回、未解析、scope开放均不得推成“不存在”。

指标：链接P/R/F1、错误合并率、聚合完整率、关系类型/方向准确率、跨模态链接准确率。B2 v4已能产候选条目（cap=20、ID召回0.988、1958条目带），但ID召回只是结构代理，不等于真实链接质量；链接gold待标注。

## 四、单一方法规格（新实验必须遵守）

| 项 | 标准 |
|---|---|
| 语义单元分数 | `max_u cos(q,u) × log(1+N/df(u))`，冻结编码器 |
| 词面基线 | BM25，k1=1.5/b=0.75（文档/单元口径各自声明） |
| 精排标准协议 | top-50召回、表内top-2单元、blend=0.1；旧历史实验若不同须显式标旧协议 |
| 语言 | 中文BGE+中文指令；英文bge-base-en+EN指令；其他骨干单独声明模板 |
| 指标口径 | R@k/MRR统一全排序语义；A1排序与A2链接/聚合指标分表 |
| 数据版本 | 每次记录dataset SHA、query-set hash、split hash、schema版本、run id |
| 下游边界 | EvidenceContext冻结后交B；A不判S/R/N、不判合规、不做ACDD |

## 五、场景覆盖与未覆盖边界

| 场景 | 构件1对象 | 2a召回目标 | 2b关联目标 | 当前状态 |
|---|---|---|---|---|
| 问参数/代码 | Claim含值/单位/条件/代码字段 | 含答案的行/片段 | 同参数的多处Occurrence | 检索有gold；Claim规范化未完成 |
| 同义/缩写 | raw词+规范候选+跨度 | 等价表达证据 | alias/coreference候选 | 消歧gold缺 |
| 正文图表引用 | 引用Occurrence+目标号 | 被引用图/表 | 有向引用链接 | 图N/表N原料已发现，解析覆盖待验 |
| 多处需求展开 | 多模态Occurrence+角色 | 任一相关证据 | 同Item的定义/合格性/追溯/图示 | B2原型；链接gold缺 |
| 类似兄弟项 | 类型/区分字段 | 可选辅助证据 | semantic_neighbor，不合并身份 | kNN原型，精确率待验 |
| 重复模板/同名异义 | 版本/系统/配置作用域 | scope内证据 | 身份消歧 | 多gold部分覆盖，scope不足 |
| OCR/VLM缺失 | raw asset+抽取状态 | 回源/其他模态候选 | 不完整链保留缺口 | 区域source_ref/置信度待做 |
| 多跳/版本时效 | 中间Claim/有效时间 | 指定版本/范围检索 | 有向多跳链/停止条件 | 当前静态快照，一跳为主 |
| 多意图/歧义question | 多个意图/实体/属性槽位 | 按意图分组召回，允许多个结果簇 | 结果可共享Occurrence但不强并 | 当前多为单意图，未系统评测 |
| 同Item内事实冲突 | 多Claim及各自SourceRef | 召回所有相关Occurrence | 标记冲突候选并交下游；A不裁决真伪 | 需补冲突状态与实例 |
| 不完整解析/来源不确定 | raw asset、partial/ambiguous状态 | 回源或返回其他来源候选 | 不完整链显式保留缺口 | completeness/source_ref尚未实现 |

## 六、按项目重构顺序的本车道工作

1. **schema对齐**：与39/40的`SourceRef/Occurrence/AtomicClaim/Item/EvidenceContext`字段逐项适配；区分构件1解析候选与构件2确认链接。
2. **A1/A2 gold**：A1回源证据gold；A2双人链接标注（同一/显式引用/仅相似/不确定）。
3. **oracle-context成对实验**：同一question/answer分别输入gold oracle context与实际召回context给B，测A1对下游可判性的影响；A侧只报告context覆盖，不接管B指标。
4. **A2指标升级**：链接质量、错误合并、聚合完整率，替代“只看ID召回”。

## 七、范围外（不做）

不做answer三态、GJB规则符合性、ACDD来源差异；不把A1/A2成绩与B的macro-F1混合；不把“未召回”写成“事实不存在”；不把相似近邻自动并为同一实体。

详细对象定义和场景分析见44_task_formalization_and_modeling.md；项目级边界见39_project_architecture_audit.md与40_method_reconstruction_plan.md。
