# 47 证据图数据管理与科研Agent执行协议

日期：2026-10-22 | 状态：MVP执行协议 v1

## 0. 研究主张

本项目的核心算法不定义为“多个LLM互相聊天”，而定义为：

> 在不可变数据快照上，使用冻结编码器和结构专家特征生成跨模态候选链接，再通过类型化证据图、QualityContract和证据义务验证，将解析观测逐步提升为可审计的质量Finding。

完整链路为：

```text
requirements / claims / table rows / diagram nodes
  → parser observations
  → cross-parser alignment
  → cross-modal candidate recall
  → EntityCandidate
  → typed CandidateLink
  → Item
  → QualityContract
  → evidence obligations / counterevidence
  → Finding / abstention / human review
```

必须严格区分：

```text
similarity       语义相似
candidate link   候选关系
same_identity    身份共指
Item             任务级聚合
Finding          质量问题候选或确认结果
```

## 1. 轻量科研数据湖

当前不引入Spark、Iceberg、Neo4j、Feast或在线特征服务。采用：

```text
不可变JSONL事实层
+ SHA256 manifest
+ lineage关系
+ 离线feature snapshot
+ SQLite查询索引（后续）
```

数据分层：

| 层 | 内容 | 允许覆盖 |
|---|---|---|
| Raw | 原始doc/docx/vsdx、MinerU、textutil、图片、专家材料 | 不允许 |
| Observed | ParserObservation、Shape、Connector、文本块、表格块 | 不允许，重跑生成新版本 |
| Curated | EntityCandidate、Claim、Alignment、CandidateLink、Item、gold/silver | 不允许，人工晋级生成新记录 |
| Derived | embedding、特征、数据集视图、预测、评测 | 可以删除重建，但不改上游 |

所有产物用内容hash和schema版本标识；路径不是身份。

## 2. 资产和快照协议

每个重要产物都应登记：

```json
{
  "artifact_id": "art-...",
  "logical_name": "evidence_graph_v1.candidate_links",
  "uri": "data/gjb_438c/evidence_graph_v1/candidate_links.jsonl",
  "content_sha256": "sha256:...",
  "schema_name": "candidate_link",
  "schema_version": "candidate_link_v1",
  "record_count": 21650,
  "status": "candidate",
  "quality_tier": "candidate",
  "builder": "tools/build_evidence_graph.py",
  "builder_git_sha": "...",
  "config_hash": "...",
  "parent_artifact_ids": ["..."],
  "created_at": "..."
}
```

长期关系独立记录：

```text
parsed_from
derived_from
aligned_to
feature_of
validated_by
promoted_from
supersedes
evaluated_on
failed_from
```

`runs/`记录一次执行，`artifacts`记录不可变产物，`relations`记录长期血缘；三者不能合并为一个日志文件。

## 3. 质量层级

### Candidate

以下只能是candidate：

- 仅由embedding相似得到的链接；
- 仅由VLM/OCR得到的图文匹配；
- 没有人工确认的同名实体；
- 未完成作用域/版本检查的冲突；
- 自动抽取的Claim；
- 结构门控前的语义近邻。

### Silver

可由以下方式形成silver：

- 多个确定性规则和一个模型一致；
- 两个独立模型一致且来源明确；
- 高置信解析器观察经过规则校验；
- 专家规则推导但未完成人工仲裁。

### Gold

Gold必须有：

- 原始证据定位；
- 标注依据；
- 标注者或专家来源；
- 冲突处理记录；
- 冻结版本；
- 可重放的schema和label policy。

候选图不能直接作为gold benchmark；`candidate`不能被检测器当成已确认矛盾。

## 4. 冻结编码器辅助召回

### 4.1 三视图表示

每个Occurrence保留：

```text
native     冻结编码器原生表示
shared     冻结编码器后的共享投影表示
local      token/字段/表头/节点/边的局部表示
```

基础分数：

```text
S_native = BGE/Qwen3原生相似度
S_shared = 投影共享空间相似度
S_local  = token/field/node late interaction
S_struct = ID、作用域、角色、表格、Visio拓扑特征
```

建议模型顺序：

1. lexical/ID/引用强基线；
2. BGE和Qwen3冻结向量并集；
3. 高置信锚点的Procrustes确定性投影；
4. 冻结编码器+轻量投影头；
5. identity boundary loss和hard negative mining。

投影头只能改善候选召回和边界排序，不能替代结构确认。

### 4.2 关系级门控

对每一对Occurrence，分别计算：

```text
P_link       是否存在某种关系
P_same       是否same_identity
P_neighbor   是否只是semantic_neighbor
P_reference  是否explicit_reference
```

`same_identity`必须满足：

```text
P_same > threshold_same
scope/version compatible
role compatible
至少一个身份或结构证据
不存在硬冲突
```

作用域冲突、版本冲突、角色不兼容、单位不可转换时，禁止语义相似度直接确认same_identity。

### 4.3 Hard negative

训练和评测必须包含：

- 同文档同章节的不同需求；
- 同名不同作用域；
- 同表兄弟行；
- 同图兄弟节点；
- 同参数不同配置；
- 语义相似但不同Item。

不能把`unknown`或未标注对象当成强负例，也不能把semantic_neighbor正例当成same_identity正例。

## 5. Agent黑板和权限

Agent之间不直接传自然语言结论，只读写版本化黑板对象。

| Agent | 可写对象 | 不能写入 |
|---|---|---|
| Parser | Observation、Occurrence | same_identity、contradicts、confirmed Finding |
| Aligner | CandidateLink、Alignment、EntityCandidate | confirmed Finding |
| Claim | Claim、Value、Event | 冲突结论 |
| Validator | QualityHypothesis、验证结果、Finding候选 | 无证据confirmed |
| Critic | obligation状态、abstain、escalation | 新事实 |
| Human | 版本化裁决记录 | 原始资产、历史结果覆盖 |
| Controller | 任务状态、预算、重试、停止 | 绕过权限 |

最小状态层：

```text
L0 freeze/lineage
L1 observations
L2 claims/links/items
L3 contracts/hypotheses/findings
L4 tasks/budgets/audit log
```

每个动作记录输入状态hash、工具版本、参数hash、输出hash、成本、错误和状态变化。

## 6. QualityContract执行

每个质量契约必须声明：

```text
target_schema
preconditions
evidence_obligations
counterevidence_conditions
validator
abstain_policy
output_schema
```

执行顺序：

```text
target selection
→ precondition check
→ evidence obligation resolution
→ validator
→ counterevidence search
→ root-cause candidates
→ confirmed / insufficient / ambiguous / human_pending
```

例如“同一接口参数值冲突”必须完成：

```text
same_identity
same_scope
same_predicate
value_parse
unit_normalization
condition_match
counterevidence_check
```

缺任何关键义务都只能输出`insufficient`或`ambiguous`，不能输出confirmed。

## 7. 最小充分证据

每个Finding不追求最长解释，而寻找最小充分证据集：

```text
E* = 最小成本且覆盖全部证据义务的证据集合
```

证据成本包括：

- 证据数量；
- 定位精度；
- 解析不确定性；
- 来源相关性；
- 人工复核成本。

同一个parser run、同一OCR区域、同一VLM调用和同一原始块的多个派生结果不能当成独立投票。来源依赖必须进入证据评分。

## 8. Finding与根因归因

Finding类型至少区分：

```text
duplicate_requirement_id
value_conflict
unit_conflict
scope_conflict
reference_break
graph_structure_conflict
parser_disagreement
linking_error_candidate
evidence_insufficient
```

根因候选至少包括：

```text
source_defect
cross_view_conflict
parse_uncertainty
linking_error
scope_version_error
normalization_error
evidence_insufficient
```

解析错误、对齐错误、源数据错误和证据不足不能被压缩成同一个“异常”标签。

## 9. 当前MVP与科研扩展

### 已落地MVP

入口：

```text
tools/build_evidence_graph.py
```

输入：`structured_corpus_v1`。

输出：

```text
data/gjb_438c/evidence_graph_v1/
├── nodes.jsonl
├── candidate_links.jsonl
├── entity_candidates.jsonl
├── items.jsonl
├── quality_contracts.jsonl
├── findings.jsonl
├── summary.json
└── manifest.json
```

默认MVP只使用确定性文本/ID/章节门控；`--embedding`可开启本地冻结EmbeddingChannel辅助候选召回。当前embedding结果只增加候选证据，不会把semantic_neighbor自动提升为same_identity。

本次确定性构建快照：

```text
nodes=21713
candidate_links=21650
entity_candidates=1086
items=1086
quality_contracts=2
candidate_findings=227
```

这些结果是candidate层，不是gold，也不是最终质量缺陷结论。

### 下一阶段

1. 建立正文Claim—表格行—Visio节点的P1/P2对齐gold。
2. 加入同名异义、同表兄弟行、同图兄弟节点hard negative。
3. 实现BGE/Qwen3 native/shared/local三视图特征缓存。
4. 加入Procrustes确定性投影作为无训练对照。
5. 加入轻量投影头和identity boundary loss。
6. 将CandidateLink提升为关系级校准输出。
7. 对每个QualityContract实现证据义务和counterevidence检查。
8. 实现`evidence_insufficient`和人工升级队列。
9. 最后实现主动验证和根因归因实验。

## 10. 论文级可证伪假设

| 假设 | 对照 | 指标 |
|---|---|---|
| 类型化链接降低错误合并 | 单一embedding相似度 | same precision、over-merge rate |
| 投影+局部交互提高跨模态召回 | native-only | Recall@K、alignment F1 |
| identity boundary loss改善同名/兄弟边界 | InfoNCE-only | boundary F1、false merge rate |
| 拒判降低高风险误报 | 强制Top-1 | risk-coverage、abstention precision |
| 最小充分证据降低审计成本 | 固定Top-K证据 | 证据数量、人工时间、充分性准确率 |
| 解析/对齐/源错误归因减少无效人工修改 | 只输出冲突 | root-cause F1、triage cost |

主评测必须使用文档级隔离，并进一步隔离source fact、semantic group、image/Visio对象和mutation family。随机拆分单条Claim或pair会造成泄漏。
