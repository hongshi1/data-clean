# 28 · Answer-Evidence 一致性校验任务重构方案

> **适用性提示（2026-10-20）**：本文是较早answer-evidence数据方案，字段和流程未完整保留原QA question，也未统一冻结上游retrieved context。本会话输入边界以[40_method_reconstruction_plan.md](40_method_reconstruction_plan.md)为准；本文内容需按QA/context契约迁移后执行。本会话不负责重做上游检索。

> 版本：v1.0 | 日期：2026-10-20
> 状态：架构与数据重构方案；执行状态见project_guide和39号审计
> 适用范围：方向A（上下文关联）与方向B（answer-evidence一致性校验）

## 1. 重构结论

项目的核心检测任务统一定义为：

```text
给定一个待验证的 answer / 条目声明 A，
以及由解析后的 SRS 内容形成的证据上下文 E，
判断 A 与 E 的关系：support / refute / not_in_evidence。
```

正文、表格、图片、追溯表不是一致性检测的两个比较端。它们是证据来源，经过解析和声明化后共同组成 `E`。表格与图片之间的实体链接、位置邻接和条目聚合属于方向A，不能直接作为方向B的评测标签或检测目标。

### 1.1 三个必须分开的任务

| 任务 | 输入 | 输出 | 当前处理方式 |
|---|---|---|---|
| 上下文关联 | SRS片段、表格行、图片元素、章节位置 | 聚合条目和候选证据 | 方向A，保留跨模态关联 |
| Answer-evidence校验 | answer声明 + SRS证据上下文 | S/R/N三态、差异类型、证据定位 | 方向B，本文重点重构 |
| 单位置质量/合规审查 | 单个SRS片段 + GJB规则 | 合规/不合规或缺陷类型 | 单独任务，不混入S/R评测 |

第三类如果保留，必须明确写成 `rule-evidence compliance`，不能伪装成表格与图片一致性，也不能直接和方向B的三态分数合并。

## 2. 新任务本体

### 2.1 输入契约

```json
{
  "instance_id": "AE-000001",
  "answer": {
    "text": "系统响应时间不超过200ms。",
    "claims": [
      {
        "claim_id": "c1",
        "text": "系统响应时间不超过200ms。",
        "predicate": "parameter_constraint",
        "subject": "系统响应时间",
        "value": 200,
        "unit": "ms",
        "operator": "le"
      }
    ],
    "origin": "candidate_item"
  },
  "evidence": {
    "scope": {
      "document": "doc01",
      "sections": ["3.2.1", "3.10.2"],
      "is_exhaustive": false
    },
    "claims": [
      {
        "evidence_id": "e1",
        "text": "系统响应时间应不超过0.2秒。",
        "source_type": "text",
        "source_ref": "doc01@3.2.1:p12",
        "extraction": "textutil",
        "confidence": 1.0
      }
    ]
  },
  "gold": {
    "label": "support",
    "discrepancy_types": [],
    "rationale": "200ms与0.2秒等值"
  }
}
```

### 2.2 语义约束

1. `answer` 是唯一待验证对象。检测器不得把 `answer.origin` 当作判定依据。
2. `evidence.claims` 是 SRS 中已解析的声明，`source_type` 只用于溯源、路由和误差分析。
3. 一个样本可以包含多个证据声明，但它们共同验证一个 answer，不表示证据之间需要互相比较。
4. 多证据上下文必须有明确 `scope`。没有范围边界时，缺失只能判 `not_in_evidence`，不能判 `refute`。
5. `refute` 必须有显式反证，或有明确的闭世界/穷举范围证明；“没有检索到”默认是 `not_in_evidence`。
6. 图片证据缺失默认是 `not_in_evidence`，除非图解析结果被声明为完整且经过质量审计。
7. 表格只有在表格语义确实是穷举列表、且行集合完整时才允许闭世界判定；普通表格字段缺失不得自动判 `refute`。
8. `gold.discrepancy_types` 描述 answer 与证据的关系类型，不描述证据来源组合。

### 2.3 三态定义

| 标签 | 判定条件 | 例子 |
|---|---|---|
| `support` | 证据明确蕴含answer，或经领域等价归一化后蕴含 | `0.2秒`支持`200ms` |
| `refute` | 证据明确给出互斥值、关系或否定事实 | 证据为`300ms`，answer为`200ms` |
| `not_in_evidence` | 证据不足以确认或反驳answer | 图解析未发现某节点，但图提取非穷举 |

## 3. 40+类型重构原则

原40项不能继续按“表格 vs 图”定义。每项必须改写成五元组：

```text
待验证answer谓词 + 证据所需事实 + 判定逻辑 + 允许的世界假设 + 差异类型
```

### 3.1 术语类

原定义“表格名称 vs 图名称”改为：

```text
answer：该条目/功能/接口名称为X。
evidence：SRS证据中对应实体名称为Y。
判断：X与Y是否同指、等价、冲突或无法确认。
```

类型包括：

- `TERM-01` 同义异名：默认 `support`，除非规则要求严格同名
- `TERM-02` 同名异义：answer包含定义/属性，证据定义冲突时 `refute`
- `TERM-03` 枚举集合：answer声明集合是否被证据完整支持
- `TERM-04` 状态/告警术语
- `TERM-05` 指令名称
- `TERM-06` 单位和量纲
- `TERM-07` 接口名称
- `TERM-08` 缩写与全称

### 3.2 参数类

answer 是参数约束，evidence 是一个或多个SRS参数声明。差异类型仍保留原PARAM ID，但不再叫“跨模态冲突”。

- `PARAM-01` 响应时间
- `PARAM-02` 周期
- `PARAM-03` 阈值
- `PARAM-04` 多源对齐误差
- `PARAM-05` 资源占用
- `PARAM-06` 值域
- `PARAM-07` 存储容量/保存时长
- `PARAM-08` 守时精度
- `PARAM-09` 降级阈值
- `PARAM-10` 故障持续时长

每条参数样本必须有结构化字段：`subject/operator/value/unit`，并通过确定性归一化和Z3/区间关系验证。不能只把两段自然语言交给LLM判断。

### 3.3 逻辑类

answer 是一个逻辑事实、顺序、权限或策略声明，evidence 是SRS中支持该事实的文本化步骤/节点/边/规则。

- `LOGIC-01` 模式优先级
- `LOGIC-02` 异常处置策略
- `LOGIC-03` 事件顺序
- `LOGIC-04` 数据流方向
- `LOGIC-05` 工况/分支覆盖
- `LOGIC-06` 互斥关系
- `LOGIC-07` 原子性/可中断性
- `LOGIC-08` 主备仲裁
- `LOGIC-09` 权限路径
- `LOGIC-10` 故障恢复方式
- `LOGIC-11` 重搜范围

图像只在上游被转成节点、边、分支、角色等声明。方向B判断 answer 是否被这些声明支持，不直接进行图表结构diff。

### 3.4 GJB/规则类

这部分必须拆成两个子任务：

1. `GJB-cross-location`：answer是“需求存在追溯关系/章节引用/标识映射”，evidence是解析后的追溯表、需求表或正文声明，可进入S/R/N评测。
2. `GJB-single-location`：answer是“该SRS片段满足GJB规则”，evidence是该片段和规则条款，单独输出`compliant/non_compliant/unknown`，不计入answer-evidence三态主分数。

原GJB-01/02/03/04/06/07/08/09/10/11多数属于第二类，不能因为证据缺失就统一标成`refute`。

## 4. 数据资产重构

### 4.1 资产分层

| 层 | 资产 | 用途 | 是否进入主评测 |
|---|---|---|---|
| L0 | 原始16份SRS、原始图片、原始表格 | 追溯和复核 | 是，作为最终来源 |
| L1 | 解析块：text/table/figure/trace | 上游解析 | 是 |
| L2 | 原子证据声明 | 统一证据表示 | 是 |
| L3 | 聚合条目/候选answer | 方向A输出、方向B输入 | 是 |
| L4 | answer-evidence样本 | 主评测 | 是 |
| L5 | 规则合规样本 | 单独评测 | 否，不混入主三态 |
| L6 | 旧pair/表图差异样本 | 历史研究、重建素材 | 否，直到完成迁移 |

### 4.2 样本来源组成

主评测集必须分层报告，不能简单合并一个数字：

1. `real_observed`：真实SRS中人工确认的answer-evidence关系。
2. `real_derived`：从真实SRS解析内容确定性派生的正例或显式反例。
3. `controlled_mutation`：基于真实SRS事实做规则变异，gold由变异证明和验证器确定。
4. `hard_negative`：语义相近但不支持、粒度不一致、合理省略、同义改写等难例。
5. `not_in_evidence`：证据范围内确实未覆盖，但不能证明全局不存在的样本。

每一层独立报告，禁止用合成集结果替代真实集结果。

### 4.3 family C的处理

原family C的293条“表格↔图”记录不是直接报废，而是作为重建素材：

- 从原始图或VLM/Visio解析结果提取图侧原子声明
- 将原 hypothesis 改写为可验证answer，例如“该流程图包含参与者节点‘开发人员’”
- evidence 改为图侧声明集，而不是表格 premise
- 如果answer来自表格事实，则answer必须明确表达该事实，证据仍然必须是用于验证answer的SRS内容
- 无法从原始来源恢复独立证据的样本进入 `quarantine`，不进入主评测

## 5. 数据生成流水线

### 阶段A：建立事实和证据中间表示

输入：16份SRS解析结果、图片、表格、章节结构。

输出：`srs_atomic_claims_v1.jsonl`，每条声明包含：

- `claim_id`
- `doc_id/section/page/source_ref`
- `source_type`
- `predicate`
- `subject/object/value/operator`
- `surface_text`
- `extraction_method`
- `extraction_confidence`
- `scope/exhaustiveness`

验收：每个声明可回到原始Markdown、表格行或图片区域；不允许只有LLM生成文本而无来源。

### 阶段B：建立条目聚合结果

输出：`srs_items_v1.jsonl`。

```json
{
  "item_id": "ITEM-001",
  "entity_key": "响应时间|数据获取服务",
  "canonical_claims": [],
  "occurrences": [],
  "candidate_answers": [],
  "aggregation_confidence": 0.0
}
```

方向A只负责找“哪些声明可能属于同一条目”，不提前把差异判为矛盾。聚合器输出候选边和置信度，保留人工复核入口。

### 阶段C：构造answer

answer来源分三类：

1. `source_claim`：直接从某个真实SRS声明抽取。
2. `derived_claim`：由结构化SRS事实确定性生成，如单位归一化、集合重述。
3. `mutated_claim`：对真实声明做可审计变异。

每个answer必须有 `claim_ir`，自然语言只是表面表达。LLM只能负责语言改写，不能决定gold。

### 阶段D：选择证据上下文

证据选择必须独立于标签：

- `positive_context`：包含支持answer的声明
- `explicit_refutation_context`：包含冲突值、否定事实或互斥规则
- `insufficient_context`：相关但不足以支持或反驳
- `scope_closed_context`：明确穷举范围，可支持缺失反驳

必须防止把产生answer的原始事实无条件泄漏给所有样本。评测时记录证据是否来自同一章节、同一文档和同一解析通道。

### 阶段E：确定gold

优先级：

1. 数值、集合、顺序、图结构声明：规则/程序验证
2. 逻辑约束：结构化IR + Z3/图关系验证
3. 术语同指：词典、实体链接、人工裁决
4. 语义残差：双标注者 + 第三方仲裁

LLM不得单独作为gold生成器。LLM可以提出候选、改写或辅助审查，但必须保留裁决证据。

## 6. 正负例与难例设计

### 6.1 support样本

- 同值异单位
- 同义表达
- 集合重排
- 合法粒度差异
- 图解析中明确存在的节点/边
- 正文中的明确蕴含

### 6.2 refute样本

- 参数值或操作符冲突
- 明确否定
- 互斥策略
- 顺序/方向相反
- 闭世界枚举中answer声称的元素被明确排除
- 规则约束导致不可满足

### 6.3 not_in_evidence样本

- 证据范围没有该实体
- 图解析未提取到但图不是穷举
- 正文片段未覆盖该参数
- 证据只包含相关实体但没有该属性

### 6.4 必须加入的对抗样本

- “未提及”与“明确不存在”区分
- 同义但表面不同
- 词面相似但实体不同
- 表格列名相同但行对象不同
- 单位相同但参数主体不同
- 图中合法省略参与者
- answer包含多个合取声明，其中一个支持、一个NIE、一个refute
- 证据检索召回错误章节

## 7. 评测协议

### 7.1 主指标

- 三态 `macro-F1`
- `F1_support/F1_refute/F1_NIE`
- 三态准确率
- 按差异类型的macro-F1
- 按来源类型的结果：text/table/figure/trace
- 按数据层：real_observed/real_derived/mutation/hard_negative

### 7.2 额外指标

- evidence grounding precision/recall：是否引用了正确SRS证据
- claim decomposition accuracy：answer拆分是否正确
- discrepancy type macro-F1
- explanation entailment：解释是否引用真实证据
- source attribution accuracy：来源类型和位置是否正确

### 7.3 划分规则

- 文档级隔离：同一SRS文档不能同时进入train和test
- 来源实体级隔离：同一原始约束的变体不能跨split
- 模板级隔离：同一自然语言模板不能跨split作为唯一线索
- 图像级隔离：同一图片的不同VLM转写不能跨split
- 所有split生成后运行泄漏审计并保存报告

## 8. 算法接口重构

```python
verify(answer: Answer, evidence: EvidenceContext) -> VerdictResult
```

`EvidenceContext` 必须包含：

- `claims`
- `scope`
- `source_refs`
- `source_type`
- `exhaustiveness`
- `extraction_confidence`

`verify_multi`可以保留，但名称和文档必须明确：它是“多个证据共同验证一个answer”，不是“多模态一致性比较器”。

算法层次固定为：

1. claim decomposition
2. entity/attribute grounding
3. evidence sufficiency and scope gate
4. deterministic channels：numeric/term/enum/order/graph/rule
5. NLI/LLM semantic fallback
6. tri-state aggregation
7. evidence and discrepancy explanation

任何检测器都不得读取 `gold`、`injected`、`discrepancy_type` 或 `origin` 字段。

## 9. 实施阶段和验收标准

### M0：任务冻结

交付：本文档、数据契约、字段说明、旧资产隔离清单。

验收：所有样本都能回答“answer是什么、证据是什么、为什么是S/R/N”。

### M1：原子证据层

交付：`srs_atomic_claims_v1`、来源追溯、范围和穷举性标注。

验收：抽样200条，来源可回溯率100%，声明字段解析准确率由人工确认；没有无来源声明。

### M2：40+类型映射

交付：`inconsistency_taxonomy_v2.json`，每项包含claim模板、证据模板、gold规则、世界假设、所需数据源。

验收：40+项全部有明确状态：`implemented / needs_data / invalid_for_main_task / separate_compliance_task`，不允许继续使用模糊的“跨模态冲突”描述。

### M3：数据生成器

交付：原子声明、answer构造、证据选择、变异、gold验证、泄漏审计五个独立步骤。

验收：固定seed可复现；每条样本都有变异证明或人工裁决记录；参数矛盾通过solver/规则验证。

### M4：真实与合成金标

交付：主评测集v2、隔离的合规集、family C重建集。

验收：真实集和合成集分开报告；双标注者对难例κ≥0.7；没有把缺失误标为refute。

### M5：算法和baseline

交付：Ours、BM25/词面、NLI、BGE、规则、LLM三态baseline矩阵。

验收：所有方法使用同一answer-evidence输入契约；结果按数据层、来源、类型和三态报告。

### M6：方向A/B联合实验

交付：有无上下文聚合、有无图证据、有无范围门控的消融。

验收：同时报告聚合指标和校验指标，证明方向A错误会如何影响方向B，而不是把二者分数混为一个指标。

## 10. 当前资产处置决定

### 可复用

- 16份真实SRS及其解析结果
- `Evidence`/`verify()`三态内核
- 数值归一化、Z3、术语词典、VLM/Visio解析结果
- `answer_evidence_evalset_v1`中A1、A3及合格的family A/B/D/E/F样本
- MANIFEST、泄漏测试和runs协议

### 必须隔离或重建

- family C表格↔图直接反推样本
- 把`modality_combo`当作任务定义的统计字段
- 直接把旧pair premise/hypothesis当成answer/evidence
- 用LLM答案文本直接作为gold
- 只依据“未命中”判定refute的样本
- 将单位置GJB质量审查混入三态主分数

## 11. 下一步执行顺序

本方案的执行门由项目架构审计 [39_project_architecture_audit.md](39_project_architecture_audit.md) 管理。实施顺序修正为：

1. 冻结任务级语义：原子/复合answer、证据内部冲突、范围与闭世界证明、ACDD是否独立。
2. 建立 `knowledge/inconsistency_taxonomy_v2.json`，分别记录任务归属、实现成熟度和数据成熟度。
3. 建立统一 `SourceRef/ParsedBlock/AtomicClaim/Item/EvidenceContext/VerdictResult` schema，并完成至少一个解析adapter。
4. 完成旧数据逐条保留/修复/隔离清单，再重建answer-evidence v2和family C可恢复子集。
5. 补齐泄漏审计、来源回溯、gold证明、manifest与runs的数据哈希。
6. 接通最小离线A→B管线并通过契约/端到端测试。
7. 冻结benchmark后再迁移baseline、运行盲测和论文实验。

在taxonomy、source refs、范围语义、数据版本和端到端接口的门通过前，不扩大旧`answer_evidence_evalset_v1`；其历史分数只作为迁移诊断，不作为最终论文结果。
