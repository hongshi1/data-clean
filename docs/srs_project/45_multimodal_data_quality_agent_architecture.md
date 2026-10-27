# 45 多模态数据质量科研Agent架构：来源感知证据图与主动验证

日期：2026-10-21 | 状态：研究架构草案 v1 | 范围：文档、图片、表格、时序数据的数据质量

## 0. 核心主张

本项目不把Agent定义为“LLM + 若干工具调用”，也不把数据质量压缩成一个总分。核心研究主张是：

> 将数据质量问题表示为**带来源、类型、方向、作用域和时间语义的证据图上的可验证质量假设**，由Agent主动选择最能区分竞争假设的验证动作，并输出最小充分证据、根因归因和可审计的不确定状态。

因此，系统必须区分：

```text
解析观测是否可靠？
实体/字段是否正确关联？
事实之间是否冲突？
时序约束是否违反？
是否有足够证据作出判断？
```

这些问题不能被一个LLM置信度或一个质量分数替代。

## 1. 系统边界

### 1.1 目标输入

系统输入不是只有文本，而是带版本的异构资产：

| 资产 | 例子 | 质量对象 |
|---|---|---|
| 文档正文 | 段落、需求句、章节 | 术语、Claim、条件、范围 |
| 表格 | 表头、行、单元格、续表 | 字段、值、单位、枚举、结构 |
| 图片/Visio | 图题、节点、边、区域、坐标 | 实体、关系、流向、图表引用 |
| 时序数据 | 采样值、事件、日志、指标 | 时间戳、事件顺序、漂移、缺测、变化 |
| 版本信息 | 修订号、有效期、采集时间 | 版本继承、适用范围、时效 |

### 1.2 输出分层

```text
原始资产（只读）
  → 解析观测与结构化Claim
  → 来源感知多模态时空证据图
  → 质量假设与验证结果
  → 根因诊断 / 修复建议 / 人工升级
```

输出严格分成四类：

1. `detection`：是否发现可验证的质量异常；
2. `diagnosis`：异常涉及哪些Claim、关系或解析步骤，可能根因是什么；
3. `recommendation`：建议如何补证、修正或重新解析；
4. `repair`：实际修改，仅在显式授权、可回滚且复检通过时允许。

默认只输出前3类，不自动修改原始数据。

## 2. 统一数据模型：时空证据图

采用有类型、有方向、带版本、带来源的属性多重图。节点与边都可以携带置信度、方法、来源、适用范围和有效时间。

### 2.1 节点

```text
SourceVersion
  = {source_id, version_id, parent_version, content_hash,
     parser_id, parser_version, created_at, valid_time}

SourceRef
  = {source_version, modality, document/stream_id,
     section, page, block, table, row, cell, node, region,
     event_index, timestamp, raw_asset_ref}

Occurrence
  = {occurrence_id, source_ref, raw_value, normalized_value,
     parse_status, extraction_method, extraction_confidence}

EntityCandidate
  = {candidate_id, entity_type, canonical_name, aliases,
     scope, alternatives}

Claim
  = {claim_id, subject, predicate, object/value, operator,
     unit, condition, scope, valid_time, source_spans, status}

Value
  = {raw_text, typed_value, unit, precision, interval,
     missingness, applicability}

Event
  = {event_id, event_type, event_time, observation_time,
     sequence_id, value_refs, window, quality_flags}

QualityHypothesis
  = {hypothesis_id, quality_type, target_refs, obligations,
     counterevidence, validator, status, confidence}
```

`EntityCandidate`仍然只是解析候选；构件2的`Item`是上下文关联后的Occurrence集合；`QualityHypothesis`则是质量Agent准备验证的对象。三者不得合并。

### 2.2 关系

关系必须有类型和方向：

| 关系 | 含义 | 约束 |
|---|---|---|
| `mentions` | Occurrence提及EntityCandidate | 可撤销候选 |
| `supports` | Occurrence支持Claim | 保留来源和跨度 |
| `contradicts` | 一个Claim对另一个Claim提供反证 | 只能由验证器产生，不能由相似度产生 |
| `same_identity` | 两个Occurrence可能指向同一实体 | 需要ID、引用、作用域等证据 |
| `explicit_reference` | 正文、图、表、追溯项的有向引用 | 保留source→target |
| `structural_membership` | 单元格属于表、节点属于图、采样属于窗口 | 不等于实体共指 |
| `semantic_neighbor` | 语义相近或类似证据 | 默认不能合并 |
| `observes` | 时序Event观测实体/Claim | 区分规范值与观测值 |
| `before/after` | 事件偏序 | 不默认等价于真实因果 |
| `revises/derived_from` | 版本和派生关系 | 不覆盖旧版本 |
| `field_alignment` | 文档字段与时序字段的候选映射 | 需要单位、实体、时间粒度证据 |
| `hasField/underHeader` | 表格结构关系 | 显式保存列头语义 |

### 2.3 开放世界与局部封闭世界

默认采用开放世界：

```text
没有观察到 ≠ 不存在
没有召回 ≠ 文档中不存在
解析失败 ≠ 源数据错误
```

只有当证据明确提供枚举完整性、时间窗完整性或范围闭合证明时，才允许对局部scope使用封闭世界。`completeness`必须挂在具体证据和scope上，不能由`table`、`image`或`text`类型自动推导。

## 3. 四层算法架构

### L0：冻结、血缘与可重放层

职责：生成输入快照、内容哈希、解析器版本和派生链。

硬约束：

- 原始资产只读；任何规范化都是新版本；
- 每条证据可回到页、行、单元格、图区域或时序窗口；
- 每次Agent动作记录输入hash、工具、参数、输出、错误和前序；
- 评测运行记录dataset hash、split hash、schema版本和run id。

### L1：多模态感知与原子声明层

使用解析器、OCR/VLM、表格结构恢复、Visio/XML适配器和时序读取器，输出Occurrence、Claim、Value和Event。

核心原则：

- 同时保存raw value和normalized value；
- 明确区分`missing`、`unknown`、`not_applicable`和`unparsed`；
- 解析不确定性不直接变成质量缺陷；
- 图像区域、表格结构和时序窗口都是一等证据对象。

### L2：来源感知关联与上下文构造层

这是现有方向A的升级版：

```text
2a 需求满足式证据召回：question → EvidenceContext
2b Occurrence关系推断：Occurrence → typed CandidateLink → Item
```

关联采用分层证据优先级：

```text
显式ID/引用 > 结构关系 > 作用域/类型/单位匹配 > 语义近邻
```

输出竞争候选和拒判结果，不强制选择唯一实体。关联置信度必须能够追溯到支持它的边和解析状态。

### L3：质量假设、验证与诊断层

质量检查不是自由生成的提示词，而是可插拔的`QualityContract`：

```text
QualityContract
  = {quality_type,
     target_schema,
     preconditions,
     evidence_obligations,
     counterevidence_conditions,
     validator,
     abstain_policy,
     output_schema}
```

例如“同一接口的协议值冲突”必须声明：

- 目标：两个已关联的接口参数Claim；
- 前置：接口身份、端点、版本和scope已匹配；
- 证据义务：至少两条带来源的Claim；
- 反证条件：规范化后协议值不兼容；
- 弃权条件：身份、版本或解析状态不确定；
- 验证器：字段匹配 + 枚举兼容规则；
- 输出：缺陷、证据、根因候选和人工复核状态。

## 4. Agent控制循环

Agent不是“一次性回答器”，而是受权限和预算约束的验证控制器：

```text
任务契约解析
  → 选择待检对象
  → 生成竞争质量假设
  → 计算证据缺口
  → 选择最有区分力的验证动作
  → 调用受许可工具
  → 校验工具输出和来源
  → 更新证据图/假设状态
  → 通过、拒判、补证或人工升级
```

### 4.1 验证动作

动作必须是白名单工具，例如：

- 回源读取指定页/行/图区域；
- 补充OCR或图结构解析；
- 重建表头、合并单元格和续表关系；
- 单位、区间和枚举归一化；
- 查询同scope、同版本的Occurrence；
- 对时序窗口执行缺测、重复、乱序、突变、漂移检测；
- 对偏序、资源预算和逻辑约束执行规则/SMT验证；
- 请求人工确认实体链接或证据充分性。

### 4.2 主动验证策略

对竞争假设`H={真实缺陷, 错误解析, 错误关联, 证据不足}`，选择动作`a`最大化：

```text
VOI(a) = 预期假设区分收益
        - λ × 验证成本
        - μ × 新增误导风险
```

这比“让LLM继续搜索”更适合成为科研算法贡献。系统应优先寻找能区分根因的证据，而不是无限扩展上下文。

### 4.3 证据义务与最小充分证据

对每个质量假设`h`定义证据义务集合：

```text
O(h) = {身份对齐, 作用域匹配, 值/关系解析, 反证条件, 完整性证明}
```

候选证据`e`只覆盖其中一部分义务，并且多个证据可能共享同一个解析器、来源文件或抽取链。系统不应简单把置信度相乘或把重复来源当成独立投票，而应求解来源依赖约束下的最小充分证据集：

```text
E*(h) = argmin_E [cost(E) + redundancy(E) + uncertainty(E)]
        subject to coverage(E, O(h)) >= required_coverage(h)
                   and provenance_consistent(E)
```

若没有任何`E`满足证据义务，输出`evidence_insufficient`或`ambiguous`，而不是低置信度地判定缺陷。若多个互斥证据集分别支持竞争假设，输出最小冲突集合及其来源依赖。

这一层是本方法区别于普通RAG/LLM判定的关键：目标不是生成最长解释，而是找到**足以完成质量判定、且能被人工逐项复核的最小证据集**。

## 5. 数据质量问题空间

不先设计40个孤立规则，而是采用可扩展的质量维度和根因分解。

### 5.1 质量维度

| 维度 | 判定对象 | 典型例子 |
|---|---|---|
| 准确性 | Claim/Value与源资产是否一致 | OCR把200ms读成20ms |
| 完整性 | 预期对象/字段/关系是否存在 | 续表漏行、图中节点未解析 |
| 一致性 | 同一scope下多个Claim是否兼容 | 正文协议与表格协议冲突 |
| 唯一性 | 是否存在不应重复的实体/版本/事件 | 重复需求ID或重复采样 |
| 有效性 | 值、单位、类型、范围是否合法 | 单位不匹配、值域越界 |
| 时效性 | 时间和版本是否适用 | 旧版本约束被用于新配置 |
| 可追溯性 | 是否能回到原始证据 | 无页码、无图区域、无窗口 |
| 语义合理性 | Claim关系在领域约束下是否可解释 | 端点方向或状态转移错误 |

### 5.2 根因类别

系统输出的根因不能只写“检测到异常”，至少区分：

```text
source_defect          源数据本身缺陷
cross_view_conflict    多视图/多来源事实冲突
parse_uncertainty      OCR、表格、图结构或时序解析不确定
linking_error          实体、字段或Occurrence错误关联
scope_version_error    版本、配置、适用范围错误
evidence_insufficient  证据不足，无法裁决
```

其中`evidence_insufficient`是有效输出，不是失败；不能把证据不足强行转成缺陷。

## 6. 时序数据的专门处理

时序数据不能被简单序列化成文本后使用文档检索方法。至少保留：

```text
event_time       事件发生时间
observation_time 记录/采集时间
sequence_id      序列或设备上下文
sampling_window  采样窗口
valid_time       规范/配置有效期
```

时序质量检查分为：

- 结构：缺测、重复、乱序、时间戳不单调、采样间隔异常；
- 统计：突变、漂移、分布变化、跨源不同步；
- 语义：事件顺序、状态转移、超时、资源预算和版本约束；
- 文档对齐：文档规范值/约束与实际观测字段、单位、时间粒度是否对应。

当前16份SRS静态快照不能支撑“真实时序质量检测”结论。时序主张必须新增有序采样、事件日志或多版本配置数据；流程图的箭头顺序不能直接当成时间序列。

## 7. 科研创新主线与可证伪假设

主线建议固定为：**来源感知多模态证据图 + 证据义务驱动的主动质量验证**。

### 7.1 论文级贡献

1. **统一对象贡献**：用Occurrence/Claim/Event/Value/SourceVersion统一正文、表格、图像和时序观测，并显式表达作用域、版本和不确定性。
2. **关联贡献**：类型化、带方向的候选链接与证据链，避免语义相似造成错误合并。
3. **质量推理贡献**：将质量类型形式化为证据义务、反证条件、弃权策略和验证器，而非自由生成判断。
4. **Agent贡献**：以信息价值选择下一步验证动作，主动区分真实缺陷、解析错误、关联错误和证据不足。
5. **可审计贡献**：输出最小充分证据集、根因候选和完整重放轨迹。

### 7.2 可证伪假设

| 假设 | 对照 | 主指标 |
|---|---|---|
| H1 类型化链接减少错误合并 | kNN/无类型连通分量 | 错误合并率、链接F1 |
| H2 证据义务减少过度判定 | LLM直接判定、普通规则 | 缺陷Precision、选择性风险 |
| H3 主动验证降低人工成本 | 固定top-k搜索、随机动作 | 单个正确结论的动作数/人工率 |
| H4 根因分解减少误把解析错当源错 | 只输出异常类别 | 根因macro-F1、误归因率 |
| H5 最小证据集提升可审计性 | 全文解释、LLM长解释 | 证据定位准确率、充分性评分 |

## 8. 评测设计

### 8.1 三个oracle层级

```text
O1 金标准Occurrence/Claim → 测质量验证器上限
O2 金标准Item/Link → 测质量检测对关联的依赖
O3 原始资产端到端 → 测真实Agent系统
```

必须报告O1→O2→O3性能下降，不能把解析、关联和验证误差混成一个数字。

### 8.2 基线族

- 字段/ID/引用确定性规则；
- BM25、dense、无类型kNN和普通聚类；
- 类型化链接 + 规则/图约束；
- 单模态文本/表格/图像方法；
- 普通LLM/VLM直接判定；
- 证据约束但不主动选择动作的Agent；
- 本方法：类型化证据图 + QualityContract + 主动验证。

所有方法必须使用相同的输入权限和相同的冻结快照，禁止让baseline读取gold、mutation记录或私有解析结果。

### 8.3 指标

| 阶段 | 指标 |
|---|---|
| 解析 | 实体/字段/Claim/Event P/R/F1、槽位准确率、回源率、歧义保留率 |
| 关联 | 链接P/R/F1、错误合并率、Item完整率、类型/方向准确率 |
| 检测 | 按质量类型P/R/F1、PR-AUC、文档级bootstrap区间 |
| 诊断 | 根因macro-F1、根因混淆矩阵、最小冲突集命中率 |
| 证据 | 定位准确率、证据充分性双人评分、证据冗余度 |
| Agent | 正确结论动作数、人工升级率、selective risk、验证成本 |
| 建议 | 可接受率、引入新错率、专家采纳率 |

数据按文档/项目分组切分，不能把同一文档的行或受控变异拆到训练和测试。16份真实SRS适合文档外测试和宽置信区间，不足以支撑强跨项目泛化声明。

## 9. 现有资产与新增资产

### 可直接复用

- 16份GJB SRS及解析后的正文、表格、图片资产；
- A1 evidence_recall、统一BM25/BGE baseline和冻结评测协议；
- B2 v4类型阈值/容量约束聚合原型；
- GJB词典、规则库和SourceRef回源素材；
- 现有runs、manifest和因果探针机制。

### 必须新增

- 构件1统一Occurrence/Claim/Value/Event schema及gold；
- A2链接级gold：同一、显式引用、仅相似、不确定；
- 真实或专家确认的多模态质量缺陷与反例；
- 证据充分性和根因标签；
- 多版本/有序时序数据及文档字段对齐标注；
- 修复建议可接受性和引入新错标注。

合成缺陷可以用于受控敏感性实验，但不能单独支撑真实缺陷检测结论。

## 10. 实施顺序

1. 冻结`SourceRef/Occurrence/Claim/Value/Event/CandidateLink/Item/EvidenceContext`统一schema。
2. 修正`EvidenceStore.from_ure()`的source_type，并补齐source_ref、scope、completeness、freeze_id。
3. 从16份SRS抽取一批正文—表格—图片跨模态Occurrence，进行双人链接标注。
4. 实现A2链接gold评测，先验证类型化链接是否真的减少错误合并。
5. 将质量规则封装为`QualityContract`，先实现参数、接口、表格结构和引用四类确定性验证器。
6. 实现最小证据集与根因分解，加入解析不确定、错误关联、证据不足三种弃权路径。
7. 在静态SRS上完成O1/O2/O3实验，再扩展多版本和时序数据。
8. 最后实现主动验证策略，并以动作成本、人工升级率和选择性风险验证Agent创新。

## 11. 硬边界

- LLM可以提出假设、生成计划和解释，但不能单独确证质量缺陷；
- 语义相似不能单独证明身份、事实一致或冲突；
- 缺失、未召回和解析失败不能直接判源数据错误；
- 建议不能包装成修复，自动修复必须显式授权且复检；
- 文档静态快照不能支撑时序泛化声明；
- A1/A2的召回和聚合指标不能与B的answer校验或C的GJB合规指标合成总分。
