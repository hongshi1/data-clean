# 46 解析联邦与结构化特征层：Visio XML + MinerU/textutil + 专家知识

日期：2026-10-22 | 状态：研究架构设计 v1

## 0. 结论

现有的Visio→XML、MinerU、textutil和专家结构知识不应被Agent当成几个普通工具随意调用，而应组成一个**解析联邦（parser federation）**：

```text
原始资产
  ├─ Visio/OLE → XML结构与拓扑观测
  ├─ MinerU → 页面布局、表格、图片和阅读顺序观测
  └─ textutil → 线性文本、章节和兼容性观测
                 ↓
       专家结构知识/规则约束
                 ↓
       统一Anchor + Observation层
                 ↓
       Entity/Claim/Event/Relation特征层
                 ↓
       数据质量Agent
```

核心原则：

1. 确定性解析器恢复可回归的事实；Agent不替代XML拓扑、坐标、页码、表格结构和哈希记录。
2. 多条解析链路的结果并存，不选择一个结果静默覆盖另一个结果。
3. 所有规范化和语义推断均保留原文、来源、方法、版本和不确定性。
4. 低置信关联只能产生候选，不能直接产生“矛盾”“不存在”或“违规”。
5. 质量Agent先判断证据是否足够，再决定是否进入语义检测或人工复核。

## 1. 现有链路的正确定位

### 1.1 Visio→XML：图结构事实主链路

优先使用当前改进的锚点解析链路：

```text
DOCX/OLE → VSDX ZIP → page XML + masters.xml → Shape/Connect/Geometry
```

主要入口和资产：

- `tools/m0_anchor_extract_all.py`
- `tools/m11_full_parser.py`
- `data/gjb_438c/anchor_v2/anchors_v2.json`
- `data/gjb_438c/anchor_v3/anchors_v3.json`

当前可用的结构事实包括：

- 页面尺寸、嵌入对象和页面标识；
- Shape ID、文本、Master类型、父组/层级的部分信息；
- `bbox/cx/cy/w/h/rx/ry`几何字段；
- Connect记录和connector ID；
- `src/dst`、边标签、`via`恢复方式；
- 部分箭头、UML关系类型和waypoints；
- dangling ends、geo边、原始Shape/Connect数量等解析质量信号。

应区分：

```text
Visio XML直接事实       Shape ID、Cell、Connect、Master、坐标、路径
解析器派生事实           节点类型、边方向、geo吸附、父组传播
Agent语义假设            “该矩形是数据处理模块”“该边是数据流”
```

旧版`sc2_visio_extract.py`、`sc_visio_expand.py`和旧`visio_extracted`资产保留作历史对照和误差分析，不应作为新主链路的唯一真值来源。

### 1.2 MinerU：页面布局和多模态块主链路

优先消费原始`content_list.json`，再生成二次结构化结果：

```text
data/gjb_438c/mineru_standard/<doc>/office/*_content_list.json
```

直接保留：

- `type`；
- 原始文本；
- `page_idx`；
- `text_level`；
- 表格HTML；
- 图片路径和caption；
- 块顺序及原始payload。

`tools/srs_mineru_parse.py`生成的章节、表格分类、约束、版本和需求ID是**派生观测**，有用但必须保留原始输入和启发式来源。尤其是：章节继承、表格类型、约束参数名、版本抽取和跨页表格不能直接当人工确认事实。

### 1.3 textutil：线性文本和兼容性观测链路

textutil主要承担：

- 正文线性顺序；
- 段落和标题兼容性；
- 章节编号候选；
- 需求ID、图表引用和术语覆盖；
- 与历史数据处理结果的可比性。

它不应承担：

- 复杂表格结构恢复；
- 图片和文本框视觉绑定；
- Visio拓扑恢复；
- 图像坐标定位。

当前工作区没有找到`tools/srs_doc_batch_parse.py`和`parsed_srs_dataset`，但`data/gjb_438c/dual_source/`中存在16份textutil HTML结果。因此已有textutil解析资产可进入联邦；批量重建入口和配置尚不可复现，接入时先将这些HTML作为冻结ParserArtifact，不假定原生成脚本仍可运行。

## 2. 解析联邦的统一契约

### 2.1 原始解析观测

每条解析产物先转换成不丢信息的`ParserObservation`，不直接写入Entity或Claim：

```json
{
  "observation_id": "obs-04-visio-p2-s60",
  "asset_id": "doc-04",
  "source_version": {
    "content_hash": "sha256:...",
    "parser_id": "visio_xml",
    "parser_version": "m11",
    "config_hash": "..."
  },
  "modality": "diagram_node",
  "raw_payload": {"id": "60", "text": "..."},
  "locator": {
    "section_id": "3.2.1",
    "page": 18,
    "embed_index": "oleObject7.bin",
    "page_id": "page1.xml",
    "shape_id": "60",
    "bbox": [1.2, 2.3, 4.5, 5.6]
  },
  "status": "observed|partial|ambiguous|unparsed",
  "method_kind": "deterministic|heuristic|calibrated|llm|vlm",
  "confidence": null,
  "parent_observation_ids": []
}
```

不同模态的稳定定位：

| 模态 | 最小定位组合 |
|---|---|
| 正文 | `asset + page_idx + section_id + block_id + text_hash` |
| 表格 | `asset + page_idx + table_id + row_id + cell_id` |
| 图片 | `asset + page_idx + image_path + figure_ref` |
| Visio节点 | `asset + embed_index + page_id + shape_id + bbox` |
| Visio边 | `asset + embed_index + page_id + connector_id + src/dst + via` |
| 时序记录 | `stream + sequence_id + event_index + event_time` |

MinerU当前常有页码而无bbox，必须明确保存“bbox unavailable”，不能生成伪坐标。

Visio的`embed_index/page_id`不自动等于Word中的图号、图题、章节或MinerU页码。必须单独建立`figure_alignment`候选对象，保存匹配依据（OLE顺序、文档关系、caption、渲染图相似度、页面位置）及确认状态；未经确认不能把某个嵌入图的XML结构绑定到相邻图题。

### 2.2 规范化对象

从Observation派生以下对象：

```text
Occurrence       一次原始出现
EntityCandidate  可能指向的工程实体
Claim            原子事实
Event            时序事件或观测
CandidateLink    类型化、带方向的关系候选
Item             经过关联决策的Occurrence集合
```

规范化必须满足：

- `display/raw`、`normalized`、`semantic`三种文本并存；
- 原始值和单位、规范值和单位并存；
- `missing/unknown/not_applicable/unparsed`分开；
- `explicit/supported/speculative`对齐状态分开；
- 解析置信度、关联置信度、事实置信度、检测置信度分开。

## 3. 结构化特征提取分层

不要把全部特征压进一个宽表。使用对象表、观测表、关系表、数值表和对齐表分离存储。层级定义为：L0原始观测，L1规范化语义，L2关系/图，L3质量信号，L4解析器间对齐，L5跨模态语义对齐。

### L0：原始观测特征

#### 文档和定位

```text
asset_id, file_hash, file_type, version, page, section,
block_id, paragraph_index, table_id, row_id, cell_id,
figure_ref, image_path, embed_index, page_id, shape_id,
connector_id, bbox, text_hash, reading_order
```

#### 正文

```text
raw_text, sentence_spans, paragraph_type_candidate,
requirement_id, terminology_strings, modality_words,
negation_spans, numeric_strings, unit_strings,
cross_reference_expressions, list_depth, condition_spans
```

#### 表格

```text
row_count, column_count, header_tree, row_id, cell_raw_text,
rowspan, colspan, empty_cell_state, row_role_candidate,
row_number, continuation_candidate, table_caption
```

#### Visio页面、Shape和Connector

```text
page_id, page_size, page_order, layer_ids,
shape_id, master_id, master_type, parent_id, depth,
raw_text, text_spans, bbox, cx, cy, w, h, rotation,
fill, line_style, font_style, custom_properties,
connector_id, begin/end_point, waypoints, label, label_pos,
begin_arrow, end_arrow, via, from_part, to_part,
dangling_end, raw_shape_count, raw_connect_count
```

这些是最值得优先补齐的Visio底层字段。尤其不能丢：

- `parent/depth/master_id`；
- connector完整路径和标签位置；
- 原始箭头与恢复方向证据；
- 图内编号文本及其bbox；
- 泳道/容器候选及节点归属；
- Shape与Word图题/章节的映射。

### L1：规范化语义特征

#### 实体

```text
entity_id, entity_type, canonical_name, aliases,
granularity, scope, mode, state, variant,
responsible_actor, type_instance_status
```

实体类型至少覆盖：

```text
system, subsystem, module, function, interface,
device, actor, parameter, data_item, requirement,
constraint, event, state, test_item
```

#### 行为和功能

```text
function_id, action_type, inputs, outputs,
preconditions, postconditions, success_condition,
failure_handling, requirement_strength
```

#### 接口和数据

```text
interface_id, endpoints, direction, operation_type,
protocol, data_format, payload, parameter_set,
sync_mode, frequency, reliability, security_level
```

#### 数值和约束

```json
{
  "raw": "不大于100 ms",
  "operator": "<=",
  "value": 100,
  "unit_raw": "ms",
  "unit_canonical": "millisecond",
  "dimension": "time",
  "approximate": false,
  "tolerance": null,
  "condition": "",
  "scope": ""
}
```

保留：比较方向、近似词、模态词、条件、作用域和验证方法。不能把“约100ms”静默变成严格`100ms`。

### L2：关系和图特征

建议拆成四个互补图，而不是一个无类型混合图：

```text
Entity Graph       系统、模块、接口、参数和数据对象
Behavior Graph     流程、状态、活动和时序事件
Interface Graph    端点、连接器、数据流和协议
Evidence Graph     来源、Occurrence、Claim、解析和对齐边
```

关系类型：

```text
contains, same_identity, mentions, supports,
explicit_reference, structural_membership,
participates_in, calls, sends, receives, depends_on,
precedes, enables, constrains, maps_to, refines,
traces_to, semantic_neighbor, conflicts_with
```

图指标：

```text
in_degree, out_degree, reachability, path_length,
cycle_count, branch_factor, SCC, orphan_count,
graph_density, hierarchy_depth, unnamed_edge_ratio,
cross_lane_edge_count, dangling_connector_ratio
```

图指标只能在确定边和候选边分层后计算：

```text
core_graph       仅高置信边
extended_graph   加入支持性弱边
candidate_graph  包含所有候选边
```

如果一个质量结论只在candidate_graph中成立，输出应为`review_required`，不应作为确认缺陷。

### L3：质量特征

#### 解析质量

```text
ocr_confidence, text_readability, shape_class_confidence,
connector_endpoint_confidence, text_shape_alignment_confidence,
table_structure_confidence, reading_order_confidence,
diagram_type_distribution
```

#### 完整性和可验证性

```text
has_subject, has_action, has_object, has_condition,
has_measurement, node_naming_rate, edge_naming_rate,
interface_endpoint_completeness, parameter_unit_completeness,
requirement_evidence_coverage, citation_resolution_rate
```

#### 风险特征

```text
same_name_multi_value_risk, unit_conflict_risk,
direction_conflict_risk, order_conflict_risk,
orphan_reference_risk, unsat_constraint_risk,
cross_modal_difference_risk
```

这些是质量分析的筛选信号，不是最终缺陷标签。

### L4：跨解析器对齐

在跨模态语义对齐之前，先对齐不同解析器观察到的同一源内容：

```text
textutil paragraph ↔ MinerU text block
MinerU table/image ↔ document page region
Word embedded OLE ↔ Visio page XML ↔ rendered figure/caption
textutil heading ↔ MinerU heading block ↔ canonical section
```

特征至少包括：`content_hash/text_hash`、页码映射、章节一致性、局部文本相似度、bbox重叠、顺序偏差、图题候选、解析器间数量差异和对齐状态。缺少锚点时保持unmatched，不允许通过最近邻强制一一对应。

### L5：跨模态对齐特征

所有对齐均保存为关系对象：

```json
{
  "alignment_id": "align-1",
  "source_id": "text-occ-1",
  "target_id": "visio-shape-17",
  "alignment_type": "mentions_same_entity",
  "features": {
    "id_match": 1.0,
    "term_similarity": 0.82,
    "embedding_similarity": 0.88,
    "section_compatibility": 1.0,
    "layout_proximity": 0.24,
    "type_compatibility": 1.0,
    "scope_conflict": 0.0
  },
  "status": "explicit|supported|speculative|rejected",
  "evidence_refs": ["..."],
  "confidence": 0.86
}
```

对齐类型至少包括：

- 正文实体 ↔ 图元；
- 正文需求 ↔ 表格行；
- 图接口 ↔ 接口表行；
- 图功能 ↔ 需求项；
- 图事件 ↔ 时序记录；
- 图题/图号 ↔ Visio嵌入对象；
- 表格字段 ↔ 时序数据字段。

## 4. 按图类型提取的专有特征

### 4.1 用例图

```text
actors
use_cases
system_boundaries
actor_usecase_associations
include/extend/generalization/dependency
boundary_membership
stereotype
multiplicity
relation_style
```

重要边界：左右位置只能作为角色候选，不能直接证明“主参与者/外部系统”；`include/extend`不能只由边标签判断，还应结合虚线、箭头和连接端点。

### 4.2 流程图/活动图

```text
start/end
process
decision
branch_condition
fork/join
loop_entry/loop_exit
off_page_reference
step_display_number
main_path_candidate
exception_flow_candidate
lane/pool/partition
node_lane
cross_lane_edge
```

必须区分：

- 图中显示的步骤编号；
- 解析器根据拓扑推断的顺序；
- 仅由坐标得到的空间顺序。

`main_path`和异常流是派生候选，不是原始事实。

### 4.3 接口图/架构图/数据流图

```text
systems
modules
ports
interfaces
source_endpoint
target_endpoint
direction
protocol
payload/data_item
sync_mode
interface_version
data_store
data_flow
```

不能把当前`system_a/system_b`的无向连接直接当作发送/接收关系。必须保留connector端点、箭头、方向证据和接口属性。

### 4.4 时序图

当前代码库尚未形成专用时序图模型。应在后续单独增加：

```text
lifelines
participants
messages
sender/receiver
message_order
activation_bars
return_messages
guard_conditions
alt/opt/loop/par_fragments
create/destroy
```

底层`Message`或Connector文本可以作为候选输入，但当前不能把一般有向图直接声称为时序图。流程图空间上下顺序也不能替代真实事件时间。

### 4.5 状态图和功能分解图

状态图：

```text
initial/final/state
transition_event
guard
action
entry/exit/do
composite_state
concurrent_region
```

功能图：

```text
root
parent_child
function_number
input/output
dependency
cross_level_edge
orphan
```

## 5. 专家结构知识如何进入Agent

专家知识不是一个“提示词”，而是三种可执行资产：

### 5.1 解析规则

约束Shape分类、表格角色、章节层级、需求ID、单位和引用存在性。

### 5.2 关联先验

规定哪些证据可以支持哪些关系：

```text
显式ID/引用 > 结构成员关系 > 类型/单位/作用域 > 语义相似
```

### 5.3 质量契约

每类质量检查定义：

```text
quality_type
target_schema
preconditions
evidence_obligations
counterevidence_conditions
validator
abstain_policy
output_schema
```

Agent只能选择适用的契约，不能自由发明检查对象。

## 6. Agent的正确职责

### 6.1 Agent可以做什么

- 根据任务契约选择解析产物和特征层；
- 生成高召回候选实体和关系；
- 解释文本、图形和表格的语义；
- 生成待验证的质量假设；
- 发现证据缺口；
- 选择下一步最能区分根因的验证动作；
- 生成最小证据包和人工复核任务；
- 形成修复建议但不默认修改原始数据。

### 6.2 Agent不能做什么

- 不能替代XML确定性解析；
- 不能把VLM观察直接当作结构事实；
- 不能把图形空间邻近直接变成语义关系；
- 不能把未观察到解释为不存在；
- 不能把`geo`吸附边与`glued`边等价处理；
- 不能把流程图空间顺序当作事件时间；
- 不能在作用域、版本或实体身份不确定时强判冲突；
- 不能让LLM独立生成gold或最终缺陷结论。

## 7. 解析质量优先级

在跨模态质量检测之前，Agent应该先运行解析质量Contract：

| Contract | 关键检查 |
|---|---|
| `document_integrity` | 输入哈希、文件版本、解析器版本、输出哈希 |
| `section_recovery` | 标题层级、编号、目录—正文映射、章节归属 |
| `table_structure` | 行列数、表头、合并单元格、续表、空单元格 |
| `diagram_topology` | Shape/Connect数量、端点、方向证据、悬空边 |
| `diagram_semantics` | 图类型、节点类别、泳道、编号、图例 |
| `cross_parser_alignment` | textutil/MinerU/Visio来源映射和冲突 |
| `claim_extraction` | subject/predicate/value/unit/condition/scope |
| `evidence_traceability` | 每个对象能否回到原始资产 |

若解析质量不达标，业务检测应降级为：

```text
partial / review_required / evidence_insufficient
```

而不是输出“文档没有问题”。

## 8. 推荐的Agent控制循环

```text
1. 冻结资产和解析版本
2. 运行三链路Parser并保存Observation
3. 执行专家结构规则和解析质量Contract
4. 生成统一Occurrence/Claim/Event
5. 构造core/extended/candidate多层证据图
6. 召回实体、字段、关系和质量假设候选
7. 检查质量假设的evidence obligations
8. 选择信息价值最高的验证动作
9. 运行确定性规则、单位归一、图算法或SMT
10. 必要时调用LLM/VLM做局部语义裁决
11. 输出Finding + EvidenceBundle + 根因候选
12. 证据不足则弃权或生成专家VerificationTask
13. 保存可重放轨迹，不覆盖原始输入
```

主动验证优先级可定义为：

```text
priority = uncertainty
         + impact
         + propagation
         + coverage_gain
         + parser_disagreement
         - review_cost
```

## 9. 论文级实验主线

### RQ1：解析联邦是否优于单一解析链

```text
textutil only
MinerU only
Visio XML only
textutil + MinerU
textutil + MinerU + Visio
```

指标：章节恢复、表格结构、图拓扑、引用定位、解析失败率和锚点稳定性。

### RQ2：专家结构知识是否改善跨模态关联

```text
embedding-only
规则 + embedding
规则 + embedding + 专家知识
规则 + embedding + 专家知识 + LLM/VLM
```

指标：实体链接F1、Item完整率、图文/图表对齐、校准误差和错误合并率。

### RQ3：解析质量门控是否减少误报

对比：

```text
无解析门控
仅固定置信度阈值
解析QualityContract门控
解析门控 + 根因归因
```

指标：质量Finding Precision、解析错误误报率、证据不足识别率、选择性风险。

### RQ4：主动验证是否降低专家成本

对比固定top-k、随机、uncertainty sampling和VOI策略。

指标：达到目标质量F1所需标注量、单个正确结论动作数、人工升级率、信息增益和高严重性确认率。

## 10. 近期实现顺序

1. 将`m0/m11`的Visio输出、MinerU`content_list`和textutil结果转换为统一`ParserObservation`。
2. 对齐`algorithms/mmqa/atoms.py`的`bbox`与anchor实际`cx/cy/w/h/bbox`字段，补齐section和figure映射。
3. 将`glued/glue_formula/geo/geo_arrow`作为不同方向证据保留，不再只输出一个`src/dst`。
4. 把`parent/depth/master_id/exploded_from`、图内编号、泳道候选和connector几何加入标准图schema。
5. 建立20至50个正文—表格—图片/Visio的人工对齐gold，先测解析联邦和A2链接质量。
6. 先实现四个解析质量Contract：`document_integrity`、`section_recovery`、`table_structure`、`diagram_topology`。
7. 再实现参数/单位、接口端点、图表引用和流程结构四类QualityContract。
8. 最后增加LLM/VLM局部裁决和主动验证；时序图/外部时序数据另设数据集，不从静态流程图推导。

## 10.1 已落地的确定性构建器

入口：

```text
tools/build_structured_corpus.py
```

输出目录：

```text
data/gjb_438c/structured_corpus_v1/
```

当前构建器已全量读取并保存：

| 输出 | 含义 |
|---|---|
| `documents.jsonl` | 16份MinerU文档资产及解析计数 |
| `sections.jsonl` | 章节、父章节、标题、页码来源；包含可回源章节节点 |
| `requirements.jsonl` | 需求ID候选、`REQ-章节号`合成条款候选、正文/表格行来源和数值特征 |
| `observations.jsonl` | MinerU text/table/image原始解析观测 |
| `tables.jsonl` | 表格caption、二维行列、表头候选、行列计数和解析状态 |
| `images.jsonl` | 图片路径、图题、章节、页码和来源 |
| `claims.jsonl` | 正文/表格候选原子Claim及数值、单位、模态词、引用特征 |
| `diagrams.jsonl` | Visio图、嵌入对象、页面尺寸、解析meta和对齐状态 |
| `diagram_nodes.jsonl` | Visio Shape节点、类型候选、文字、几何特征 |
| `diagram_edges.jsonl` | Visio connector边、端点、标签、`via`和原始边payload |
| `textutil_observations.jsonl` | 16份冻结textutil HTML的hash、字符数、表格/图片计数和观测状态 |
| `qa.jsonl` | 6189条QA、Question/Answer、Answer候选claims、图表引用和来源字段 |
| `frozen_qa.jsonl` | 91条冻结QA、证据文本、`scope_id`、`completeness`和source_ref |
| `training_pairs.jsonl` | 2813条canonical训练pair，保留label、angle、provenance和split |
| `summary.json` | 输入资产、知识库hash、数量和状态策略 |
| `manifest.json` | 每个输出JSONL和summary的SHA256 |

当前一次全量构建的规模快照：

```text
documents=16, sections=1444, requirements=2451,
tables=1207, images=381, claims=12517,
visio_diagrams=373, visio_nodes=5165, visio_edges=2557,
qa=6189, qa_answer_claims=9728, frozen_qa=91,
textutil_documents=16, training_pairs=2813
```

这里的`requirements`、`claims`和QA`answer_claims`都是结构化候选，不是专家gold。`REQ-3.2.1`这类ID表示“章节级条款候选”，与文档显式需求ID分开；后续实体/Claim裁决不得把两者静默混为同一ID。

## 11. 不应声称的能力

- 当前已有图解析字段不等于所有图类型都已完成语义解析；
- `scene_models`是场景摘要，不是完整图结构；
- 流程图`order`不等于原图显示编号；
- `src/dst`不总是语义方向；
- 接口图当前系统对可能是无向配对，不能直接当发送/接收；
- VLM节点和边是候选观察，不能替代Visio XML证据；
- 静态16份SRS不能支撑真实时序质量检测和跨项目时序泛化。
