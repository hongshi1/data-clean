# 48 对齐Gold、Hard Negative与三组召回预注册协议

日期：2026-10-22 | 状态：P0执行协议 v1

## 1. 研究对象

研究对象固定为Occurrence pair关系，不是最终QA一致性分数。标签至少区分：

```text
same_identity
semantic_neighbor
explicit_reference
not_same_identity
unknown
```

P1/P2是不同用途的对齐gold：

| 层 | 定义 | 用途 |
|---|---|---|
| P1 | 完整ID或显式引用支持的高置信候选锚点 | 确定性基线、Procrustes锚点候选 |
| P2 | 人工判断的语义/结构对齐 | 主关系评测、hard-negative边界 |

自动生成的`candidate_links`、`items`、`accepted`和embedding分数都不是gold。

## 2. 对齐对象

第一版只标注三类pair：

```text
claim ↔ table_row
claim ↔ diagram_node
table_row ↔ diagram_node
```

每条边独立标注。不能因为`claim→table_row`和`claim→diagram_node`都通过，就自动把`table_row→diagram_node`标为正例。

每条样本必须保存：

```text
source_id, target_id
doc_id
source_ref, target_ref
raw_text_snapshot
candidate_generator
candidate_features
tier=P1/P2
gold_relation
unknown_reason
annotator/adjudication
split_group
```

## 3. Hard Negative分层

候选池必须包含四类结构困难负例：

1. 同名异义：名称相同但定义、角色或作用域不同；
2. 同表兄弟行：同表、同表头、相邻或近似行但不同实体；
3. 同图兄弟节点：同图、同类型、相邻或同层节点但不同实体；
4. 同参数不同scope：参数族相同但模块、模式、设备、版本或接口作用域不同。

`unknown`不作为强负例；属性值不同但实体相同的pair仍然是`same_identity`，另建事实冲突标签。

## 4. Split与泄漏

切分顺序固定为：

```text
对象分组 → 文档/实体族分配fold → split内生成候选pair
```

同一`doc_id`、同一source fact、同一semantic/entity family、同一图、同一表、同一hard-negative group不能跨split。主结果采用文档级4-fold；strict surface-held-out作为探索性结果。

报告必须同时分开：

```text
candidate generation recall
candidate ranking/link classification
same_identity false merge rate
unknown coverage/risk
```

## 5. 三组主对照

| 组 | 定义 | 作用 |
|---|---|---|
| native-only | 单一冻结backbone原生空间，不投影、不结构门控 | 回答原生语义相似能否召回 |
| deterministic Procrustes | 只用训练P1锚点拟合正交映射 | 回答确定性跨空间对齐是否增益 |
| shared projection + structural gate | 共享输出空间加ID、scope、role、source和结构硬门控 | 回答结构是否降低错误合并 |

所有组使用同一候选池、同一split、同一评测关系和同一阈值校准协议。不得因模型不同而删除未召回样本。

## 6. 后续扩展顺序

```text
三组主对照
  → late interaction
  → identity boundary loss + hard negative mining
  → relation-level calibration
  → QualityContract evidence obligations/counterevidence
  → minimal sufficient evidence
```

每一步只回答一个问题：

- native：冻结编码器原生召回；
- Procrustes：无训练空间对齐；
- structural gate：身份/作用域安全性；
- late interaction：局部字段/节点/表头证据；
- boundary loss：相似但不同实体的边界；
- calibration：分数是否具有概率语义；
- QualityContract：证据是否足以确认Finding。

## 7. 主指标与统计

主指标：

```text
same_identity macro-F1
same_identity precision
false merge rate
Recall@1/5/10
MRR@10
Hard-negative recall
ECE/Brier（校准阶段）
risk-coverage AURC（拒判阶段）
confirmed precision / unsupported-confirmation rate（QualityContract）
```

文档级宏平均是主汇总；pair级pooled结果只作补充。置信区间使用文档级paired bootstrap，不能把pair当成独立观测单位。确认性比较固定为：完整模型vsnative、gate增益、boundary loss增益、calibration增益、QualityContract增益；其余为探索性并用Holm校正。

## 8. Silver弱监督落地（跳过人工标注的替代路线）

人工标注未完成期间，以下确定性信号可作silver弱监督，但不是gold：

| 信号 | 层级 | 依据 |
|---|---|---|
| 同doc、两个不同kind对象共享完整显式ID | silver positive（P1锚点） | 显式ID共指是确定性same_identity证据 |
| 同表相邻行、双方显式ID集非空且不相交 | silver negative | 不同显式ID=确定性不同实体 |
| 同图兄弟节点（同diagram同type、文本不同） | silver negative | 不同节点文本=不同图实体 |
| 同doc同section、显式ID不同 | silver negative | 同上 |
| 同规范化名称但无ID区分 | excluded（unknown） | 不能当正例或负例 |

已落地资产：

```text
data/gjb_438c/alignment_annotation_v1/    P1/P2候选(78705, gold=null)
data/gjb_438c/alignment_pilot_v1/          标注pilot(720, pending)
data/gjb_438c/training_pairs_v1/           silver训练对(27694: pos 13489 / neg 14205)
data/gjb_438c/feature_snapshot_v1/         BGE冻结向量快照(28127×1024, cuda)
data/gjb_438c/feature_snapshot_fake_v1/    伪向量冒烟快照(不用于论文)
data/gjb_438c/evidence_graph_v2/           silver链接升级+并查集items+契约义务检查
```

## 9. 首个训练对照结果（silver, run=train_shared_projection）

配置：冻结BGE-large-zh向量(1024d) → 共享投影(Linear-LN-GELU-Linear, 256d) → InfoNCE(τ=0.07) + identity boundary loss(margin=0.10, w=0.5)；train=10675对，20 epochs，Adam 1e-4。阈值策略：dev负例分数95%分位数（目标false merge≤5%，错误合并比漏召回更危险；F1最大化阈值在fold不均衡下会退化）。

| 配置 | test AUC | test false merge | test precision | test recall | test F1 |
|---|---:|---:|---:|---:|---:|
| native-only（冻结BGE直接余弦） | 0.9568 | 0.0307 | — | — | — |
| +shared projection（本方法） | 0.9754 | 0.0360 | 0.9043 | 0.8067 | 0.8527 |

结论与边界：

1. 投影头在排序质量上提升AUC +0.019，false merge 3.6%控制在目标内；
2. dev fold上投影低于native（0.6119 vs 0.6414）而test fold上反超——16份文档hash分fold导致fold间分布方差大，dev/test结论方向不一致必须如实报告，后续应改用人工平衡fold或LODO；
3. AUC整体偏高部分来自显式ID任务的词面捷径（共享ID的文本词面相似），协议要求最终报告"无ID子集"表现，当前数字不能外推为真实身份判别能力；
4. fold间正负比例严重不均衡（dev≈68%正例、test≈31%正例），任何按F1/准确率选阈值的方法都会退化，分位数阈值是当前唯一稳定策略；
5. Procrustes对照组尚未运行（需第二编码器空间的P1锚点向量，候选为Qwen3 embedding）。

## 10. 代码入口

```text
tools/build_evidence_graph_v2.py       silver升级+并查集items+契约义务检查
tools/build_feature_snapshot.py        BGE冻结向量快照(--fake/--limit冒烟)
tools/build_training_pairs.py          silver训练对+文档级fold
tools/train_shared_projection.py       投影头训练+native对照评测(runs协议,--fold-map)
algorithms/context_linking/alignment/  procrustes/structural_gate/late_interaction
```

## 11. 还债实验结果（A矩阵补齐+协议修复）

### 11.1 fold重平衡（修复dev/test方向矛盾）

`tools/balance_folds.py`贪心+局部搜索分配16文档→4 fold（doc02独占34%正例是纯贪心失败根因）。`train_shared_projection.py --fold-map`重训：

| 指标 | 旧(hash fold) | 新(均衡fold) |
|---|---|---|
| dev AUC / 正例率 | 0.6119 / 68% | **0.8539 / 47%** |
| test AUC / 正例率 | 0.9754 / 31% | **0.9193 / 45%** |
| test false merge | 0.0360 | **0.0193** |
| dev-test AUC差 | 0.364(方向矛盾) | **0.065(矛盾消除)** |

旧test AUC 0.9754是fold不均衡虚高；重平衡后test fm降至1.93%（更安全），投影与native在同分布fold下结论可信。

### 11.2 无ID子集（量化显式ID捷径）

`tools/eval_no_id_subset.py`：**无ID子集正例=0**（所有P1正例都含显式ID——ID共指既是监督基础也是词面捷径）。对照量化：

```text
正例含ID vs 负例不含ID:  AUC 0.8743
双侧均含ID对照:          AUC 0.6385
ID捷径贡献:              Δ=0.2358（约24个AUC点的表面可分性）
```

结论：当前silver任务的部分性能来自词面捷径；最终评测必须报告含ID/不含ID分层，或引入无ID正例（需P2人工标注或结构等价正例）。

### 11.3 Procrustes对照（A矩阵A2行，1500锚点）

`tools/eval_procrustes.py`（train P1锚点1500对拟合，anchor_hash=3910bdd1）：

| 配置 | test AUC |
|---|---:|
| native-BGE | 0.9568 |
| native-Qwen3 | **0.9806** |
| Procrustes(BGE→Qwen3空间) | 0.9471 |

发现：Qwen3-0.6B原生判别力超过BGE-large；跨空间正交映射损失约1个AUC点后仍保留判别信号。**负发现**：在单一文本模态任务上Procrustes不优于native——其价值应在跨模态（文本↔图节点）场景验证，已列为后续方向。

## 12. 一键特征矩阵与可视化（七类特征全落地）

```text
tools/build_feature_matrix.py         一键提取七类特征→feature_matrix_v1/
tools/render_feature_dashboard.py     自包含HTML dashboard(零外部依赖)
data/gjb_438c/feature_matrix_v1/dashboard.html
```

全量规模：document 16 / text 2552句 / table 1207表（**4410合并单元格**、空值状态8616 inherit+6799 empty+1116 dash、行角色分布）/ visio 373图 / 图语义373（匹配率100%，flowchart 167/usecase 107/function 75/interface 17）/ **claim五元组12517**（平均slot_fill_rate 0.497，谓词命中411条如`分辨率>=1920`）/ 质量信号16文档 / 对齐21650链接。

质量信号为风险非缺陷；五元组为候选非gold；dashboard含policy声明。

## 13. 完整消融矩阵（B/C/D/A4/E补齐，均衡fold, seed=42, test n=6848）

### 13.1 表征/门控/损失消融（tools/eval_ablation_matrix.py）

| 配置 | AUC | F1 | precision | false merge | 备注 |
|---|---:|---:|---:|---:|---|
| A1-native | 0.8774 | 0.5887 | 0.9458 | 0.0198 | 无训练基线 |
| A3-projection | 0.9193 | 0.5997 | 0.9484 | 0.0193 | 逐位复现存档run |
| **A4-gate-clean** | 0.9114 | 0.5853 | 0.9542 | **0.0164** | 论文主行；gate不含identifier |
| A4-gate-leak | 0.9825 | 0.8190 | 0.9722 | 0.0164 | oracle上限（identifier泄漏） |
| B1-late-interaction | 0.8479 | 0.6924 | 0.9011 | 0.0499 | **负结果**：token MaxSim排序劣于单向量 |
| C2-InfoNCE-only | 0.9063 | 0.6013 | 0.9506 | 0.0185 | |
| C3-boundary-only | 0.9155 | 0.5868 | 0.9656 | **0.0122** | **boundary项是主要贡献** |
| D-calibration | 0.9193 | — | — | — | ECE 0.2662→0.2660（τ≈1，诚实零结果） |

发现：(1)A4-leak−A4-clean=**+0.0711 AUC**——gate使用identifier等于直接喂标签，identifier捷径在门控层的量化；(2)clean gate以AUC微降换false merge最低0.0164和precision最高0.9542；(3)B1是可靠负结果——该任务上token级交互不如单向量（池内判别vs深语义的边界）；(4)D证明误校准非温度问题（残差校准是后续方向）。

### 13.2 跨模态Procrustes（tools/eval_crossmodal_procrustes.py，test 175查询/288 gold对/405锚点）

| 组 | R@1 | MRR@10 | AUC |
|---|---:|---:|---:|
| G0 doc-doc（上界） | 0.9143 | 0.9526 | 0.9923 |
| G1 prefix-doc（O1现状） | 0.9257 | 0.9600 | 0.9891 |
| **G2 procrustes** | **0.9429** | **0.9686** | 0.9917 |

- G2在全部排序指标最优；诊断变体（7486锚点）AUC 0.9930完全恢复并超过G0上界
- **语体鸿沟量化**：跨模态场景鸿沟远小于单模态（ΔAUC仅-0.0032），前缀在跨模态反而略有益；Procrustes恢复鸿沟的81%
- 勘验偏差（已写入notes）：快照节点文本0/2831含regex ID→gold链经requirements title桥接（claim ID→requirement行→title→同doc归一相等节点）

### 13.3 E矩阵：QualityContract风险-覆盖（tools/eval_contract_risk_coverage.py）

| 指标 | E0强制分类 | E3契约+abstention |
|---|---:|---:|
| confirmed precision | 0.9458 | **1.0000** |
| false merge rate | 0.0198(75 FP) | **0.0000** |
| abstention rate | 0.0 | 0.0388 |
| coverage | 1.0 | 0.9612 |

- **75/75高风险FP全部被契约拯救（100%）**；代价=191正例因缺scope/value义务弃权
- findings实例验证：3505条numeric insufficient中**203条(5.79%)**若按E0相似度法会被误确认
- 诚实声明：identity义务与负例构造相关，precision=1.0是银标注上界；关系分数用native cos（隔离判定策略而非投影质量）

## 14. 当前预注册矩阵完成度

A矩阵6/6（A1/A2/A3/A4-clean/A4-leak/A6由C3近似）、B 1/5（B1负结果）、C 3/5、D 1/4（零结果）、E 2/4（E0/E3）、跨模态检索新增1组。主因果链每环已有可引用数字：native→projection(+0.042 AUC)→gate(fm最低)→boundary(主要贡献)→contract(FP 100%拯救)。

## 15. 科研层todo修复（调研→实现→出数，2026-10-22）

### 15.1 多信号gold-proxy（tools/build_gold_proxy.py）

三信号一致（规则∧BGE∧Qwen3，θ各自dev校准）构建外生评测集（仅test fold，exogenous_only）：

| 类别 | 计数 |
|---|---:|
| gold_proxy_positive（P1∧双编码器≥θ） | 1181 |
| gold_proxy_negative（sibling∧双编码器<θ_low） | 1810 |
| review_queue（分歧样本，8类分歧型） | 3857 |

发现：Qwen3 test AUC **0.9018** > BGE 0.8774；双编码器Spearman 0.8952；分歧主动复核排序键=\|bge−qwen3\|。局限：无ID正例=0→gold-proxy仅ID锚定层有效；后续用gold_proxy重测条件校准的ECE（当前silver上的0.0006可能是标签构造规律泄漏）。

### 15.2 条件校准（tools/eval_conditional_calibration.py）——零结果根因修复

| 校准器 | test ECE |
|---|---:|
| raw sigmoid | 0.3815 |
| 温度缩放(D1) | 0.4578 |
| 等渗(D2) | 0.4104 |
| **条件校准（kind_pair×same_section桶LR）** | **0.0006** |

- **数学修正**：预注册的"分桶ECE加权和≪全局"方向被三角不等式证伪不可能（global≤weighted恒成立，实测0.5501 vs 0.3815反向）；修正检验=全局isotonic 0.4104→桶内isotonic加权和0.0000，**混合根因证实**（9桶标签全纯、误差符号相反在全局抵消）
- **警示**：ECE 0.0006是silver标签近oracle所致（条件校准学到标签构造规律），真实概率语义需gold-proxy子集重测
- Conformal E50双轴（α=0.1 Mondrian）：covered∧契约满足1095条全TP；契约轴与conformal轴互补关系已量化

### 15.3 B族消融补全（tools/eval_late_interaction_variants.py）——负结果族确立

| 行 | AUC | 判读 |
|---|---:|---|
| B1-idf-maxsim | 0.8479（精确复现） | |
| B2-topk3/5 | 0.8342/0.8289 | 聚合松弛有害（max捕获单token精确匹配） |
| B2-noidf | 0.8280 | 同向 |
| B4-gate | 0.7985 | <A4-clean 0.9114→**门控增益与表征正交** |

B族结论：短pair身份判别粒度上单向量+结构门控优于token级late interaction（与文献"late interaction优势在长文档"一致）——可写的边界声明。

### 15.4 谓词挖掘（tools/mine_function_predicates.py）

45动词白名单+轻动词黑名单+宾语后缀剥离：谓词覆盖**3.28%→32.12%**（4020/12517并集；白名单原始命中47.7%经规则过滤至31.1%）。动词Top：提供470/传输406/显示258/查询254。

### 15.5 锚点扩展（tools/expand_diagram_anchors.py）——三层bootstrapping

| 层 | 计数 | tier |
|---|---:|---|
| L0 explicit | 0 | 协议完备性 |
| L1 title-bridge | 846（精确复现校验） | gold_frozen |
| L2 fuzzy_lexical | 3940 | candidate |
| L2 fuzzy_vector(θ=0.5801) | 12392 | candidate |

node覆盖率**29.88%→84.56%**；L2校准precision 0.9505（L1种子+同doc错配负例ROC）；multi_match降级16095条宁缺勿滥。

## 16. 七类特征逐格补齐（v2系列，2026-10-22）

用户清单40格逐格盘点后补齐：✅19→**33**，⚠️12→6，❌9→1（父组/深度原始产物缺失已声明）。

### 16.1 正文/表格格（tools/build_feature_matrix_v2.py → feature_matrix_v2/）

| 格 | 补齐结果 |
|---|---|
| 句子字符span | 2552句{block_idx,char_start,char_end}，找不到标unlocated |
| 否定词位置化 | negations[{word,pos}]（不得/不能/禁止/不允许等9词） |
| 条件提取 | 42命中（当…时16/如果…则16/在…下6/若…则4）；28句含条件，**命中率仅1.1%如实报告** |
| 引用解析到目标ID | 1537条resolved{ref,target_id} |
| 多级表头树 | header_tree（rowspan/colspan展开） |
| 单元格坐标 | cell_id="r{row}c{col}"+rowspan/colspan |
| scope实体候选 | "XX模块/服务/接口/分系统"模式 |

### 16.2 Visio格（tools/build_visio_features_v2.py → visio_features_v2/，v2+v3锚点合并）

| 格 | 补齐结果 |
|---|---|
| Master | master_type（v2独有，node匹配率72.6%，373图对齐失败0） |
| 路径waypoints | 2518条（98.5%覆盖，v2独有） |
| 标签位置 | label_pos 173条（6.8%——原始数据即少） |
| 箭头 | begin/end_arrow 2557全量+方向四档：forward 316/backward 57/bidirectional 10/none 2174（**可判定率15%，2124条因图本身无箭头**） |
| bbox | v2合并补回 |
| 父组/深度 | **声明not_available_in_artifacts**（m11内部有但产物丢弃，未重跑解析器） |
| 两版字段漂移 | edge端点192条不一致已记录field_drift（诚实声明v2/v3解析器差异） |

### 16.3 图语义/实体/对齐格（tools/build_semantic_features_v2.py → semantic_features_v2/）

| 格 | 补齐结果 |
|---|---|
| 泳道 | 72图检出（271带）/301图无泳道 |
| 循环 | 42图（46环=31SCC+15自环，Tarjan） |
| fork/join | fork 51/join 0 |
| include/extend | 5条全unknown（scene_models的kind分类弱，**诚实弱点**） |
| 接口图方向/协议/数据项 | 69元组（协议命中17/数据项26/方向unknown 38+undirected 27） |
| 状态图 | 候选41图、迁移116条 |
| 实体类型分类 | 20133条（功能14131/数据项3548/接口1773/参数400/分系统191/模块90） |
| 接口图↔接口表对齐 | 25/69匹配（36.2%），方向一致性全unknown |
| explicit/supported/speculative三档 | explicit 846(L1)/supported 16332(L2)/speculative 0 |
