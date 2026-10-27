# 多模态一致性数据集构建·落地方案
## ——按《多模态数据集构建_技术方案设计.docx》七层体系的项目落地

> 设计日期: 2026-09-14 | 多agent设计综合（证据原子化/关系与语义组/受控变异/质量门禁四路并行设计后融合）
> 数据敏感性: 16份真实军事文档，数据集仅内部使用

---

## 0 总纲：七层对象 × 项目资产映射

| 层 | 对象 | 项目资产来源 | 规模预估 |
|---|---|---|---|
| 1 | SourceDocument | 16份GJB SRS（.doc） | 16 |
| 2 | EvidenceAtom | chunks句级+表行级+图+锚点节点/边 | **~2.2万原子** |
| 3 | Pair(7类关系) | 词法对齐+NLI+银标+变异四来源 | 数千（分gold/silver/bronze） |
| 4 | SemanticGroup | ID实体种子五层聚合 | **~568组**（发布~600-850） |
| 5 | MutationRecord | 8算子×81对锚定可信pair | **~559负例+559配对正例**（一阶段） |
| 6 | RetrievalSample | 语义组+hard negative分层 | 详见检索设计（后续） |
| 7 | QA(四类) | 判断/定位/解释/修复，gold全构造性 | ~1,680条（一阶段） |

**核心决策（设计期定死，不留可调参数）**：
1. 基本单元 = Evidence + Relation + Provenance（QA是派生物）
2. contradiction三来源分层进label_tier：mutation=gold / 银标=gold(裁决) / NLI=silver / 结构启发=bronze
3. **temporal_related砍掉**（实测无时序素材：无时序图/SEQ是拓扑序/无时间戳）——枚举保留但产出0条并标注`unsupported_in_corpus`，替代语义`process_order`归结构通道
4. 评测两套严格分开：**Suite-S（合成真值集，主表）⊥ Suite-R（银标664，副表）**，只做桥接分析不合并F1

---

## 1 证据原子层（EvidenceAtom）

**抽查实测结论**：MinerU的content_list全部有page_idx但**无bbox**（docx管线固有）；唯一带几何坐标的是Visio锚点（节点bbox+边waypoints，页内英寸坐标）。

| 源资产 | modality | 粒度 | 关键处理 |
|---|---|---|---|
| text chunk(3643) | text | 句级（。；；切分） | ~5500句；剔除标题/空段；entities从ent_appear_txt边反查 |
| table chunk(1207,HTML) | table | 表头+第i行 | ~10260行原子；HTML重解析列名:值对；262个含需求ID表重点 |
| image chunk(381) | image | 整图 | join srs_image_analyses(379条VLM分析)得entities/summary |
| 锚点节点(3759) | diagram-node | 节点 | bbox直接可用；section经graph_store IMG节点mermaid_key反查 |
| 锚点边(2680) | diagram-edge | 边 | content="{src}--{label}-->{dst}"；waypoints入provenance |

**ID规范**：`EV-{doc_num:02d}-{M}-{seq:05d}`（M=T句/R表行/G图/N节点/L边）；provenance存回溯链{source_asset, page_idx, bbox?, row_idx?, anchor?}。**id_graph的E节点(978)不造原子，作实体注册表**反向填充各原子entities。

---

## 2 关系层（Pair·7类）与语义组

### 关系构建（全部确定性信号为主，NLI只做升降档）

| 关系 | 构建信号 | 规模 | confidence来源 |
|---|---|---|---|
| equivalent | ①同ID+名称归一相同（183对种子）②pair内align≥0.9 ③semantic_preserve(292) | 数千 | deterministic |
| support | 追溯表1022+合格性桥110+交叉引用1415 | 2000-3000 | deterministic(结构边) |
| complementary | 同ID异loc-pair(能力↔文本等分工型)+BGE≥0.78吸附 | 1500-2500 | calibrated/heuristic |
| same_entity | 同ID+名称不一致（121对现成+60多别名E节点） | ~500 | **deterministic（ID是gold）** |
| contradiction | 三来源分层（§4） | 分层 | 分层 |
| unrelated | 构造性负采样分easy/medium/hard三档 | 按配比 | deterministic |
| temporal_related | **产出0条**（标注unsupported） | 0 | — |

**双标量设计**（防银标污染教训）：`relation_strength`（语义关联强度：strong1.0/medium0.75/weak0.5/hint0.25）与`confidence`（标注可靠性：deterministic/calibrated/heuristic/llm_self）。**per-why可靠性折扣写死**：text类声明的NLI信号strength上限0.75（实测AUC 0.502）。

### SemanticGroup（五层确定性聚合）

种子=E节点（978个ID实体，构造性锚）；L0同ID mention→L1宿主容器(TBL/IMG/TXT)→L2交叉引用扩展→L3 pair证据挂载(align≥0.55)→L4 BGE语义吸附(仅hypothesis级)。组=局部证据子图（evidence_ids节点集+relation_ids边集），**组内证据查全率可直接对id_registry 2016处真值评测**——语义组本身就是方向A"条目聚合"的可评测产物。

---

## 3 受控变异层（Suite-S的构造）

### 8算子库（NLI能力边界前置分流——每个算子设计期就声明可判性）

| 算子 | 变异 | issue_type | NLI可判性 | 评测通道 |
|---|---|---|---|---|
| M1 VAL-CONFLICT | 值平移200ms→500ms/比较符反转 | param.value_conflict | ✅0.98 | **NLI-强档**+Z3门 |
| M2 VAL-EQUIV | 单位族等效换算(对照) | 正例 | ✅检验不误报 | NLI-强档 |
| M3 ENUM-DROP | 闭世界清单删1项 | logic.coverage_missing | ✅1.00 | **NLI-强档** |
| M4 COND-DROP | 删条件/异常流行；情态反转 | logic.condition_missing | ✅~1.00 | **NLI-强档** |
| M5 MEM-SUB | 近邻实体替换 | terminology.entity_substitution | ❌逻辑可共存 | **词法通道** |
| M6 DIR-FLIP | 收发方交换/边方向反转 | relation.direction_reversal | ⚠️0.67 | NLI-弱档(单列)+结构通道 |
| M7 ORDER-SWAP | 相邻步骤交换 | temporal.step_order | ⚠️0.6-0.7 | 结构通道(主)+NLI-弱档 |
| M8 VIS-COUNT | 图侧删节点+**重渲染** | visual.count_conflict | ✅计数声明型 | NLI-强档+VLM集 |

**图侧变异的重渲染机制**（防"锚点与图不一致"的假警报——复刻项目映射错位教训）：变异锚点JSON→anchor→SVG确定性渲染→OCR回读门验证渲染一致→QA的image占位符指向渲染图。

### 最小对设计（防表面捷径——Korn 2026负面结果的解法）

```
每个变异负例P⁻构造三元组:
P0 = 原pair           → consistent(恒等正例)
P⁺ = 等价变异ν(P)      → consistent(扰动正例, M1配M2/删除配同义改写)
P⁻ = 冲突变异μ(P)      → inconsistent
约束: edit_dist(P⁺,P0) == edit_dist(P⁻,P0)  ← "看到diff就报矛盾"策略得0分
单变量断言: oracle验证diff恰1处(single_factor), 违者废弃
```

### 变异实体化 = 虚拟pair目录

变异后的table.csv/text.txt/visio_anchor.json/rendered.svg落盘为`mutations/{mutation_id}/`——**现有声明编译器、词法引擎、渲染管线零改动复用**，MutationRecord只是真值台账。

### 候选池与规模（一阶段：81对锚定high）

| 项 | 数值 |
|---|---|
| 负例 | ~559（M1~66/M3~160/M4~81/M5~81/M6~40/M7~50/M8~81） |
| 配对正例 | ~559 + 恒等正例81(免费) |
| 声明对级(NLI集) | ~840对 |
| QA级 | ~1,680 |
| 二阶段(重对齐后~250对) | 规模×3，解锁doc级split |

### 旧1787条mutation的收编

直接复用**0条**（缺MutationRecord字段/无配对正例）；按新算子库重生成~81%（1446条语义载荷）；**淘汰section_shift 346条**（注入人工标记行，非真实文档形态且不可回溯——构造方式污染）。旧文件标legacy归档作表面分布对照。

---

## 4 contradiction三来源的分层协调

| 来源 | label_tier | 角色 | 协调规则 |
|---|---|---|---|
| 受控变异 | gold(构造性) | 训练主力+Suite-S | expected_label由operator确定 |
| 银标real_bug(176) | gold(三轮仲裁) | Suite-R主指标 | 冲突时银标>变异>NLI |
| NLI矛盾对 | silver | 复核队列，**不直接进gold** | 升级需复核(复用五票协议) |
| 结构启发 | bronze | 候选 | — |

同(left,right)跨来源合并以银标为准；**nli_discrepancy实验的task_id对齐协议直接沿用为合并键**。

---

## 5 检测任务接口（NLI评测直接消费Pair——方案与检测的融合点）

**ClaimPair即Pair的检测视图**（收编不发明）：

```json
{
  "pair_id": "pr_1_001_e0",
  "left": "EV-01-R-00123", "right": "EV-01-N-00567",
  "relation": "equivalent",          // gold标签(防泄漏:只在answer key侧)
  "relation_strength": 0.9, "confidence": "deterministic",
  "entity": "半结构化数据归集",
  "provenance": {"origin": "structural", "claim_why": "enum", "template": "closed"},
  "evaluation": {
    "claim": {"premise": "...", "hypothesis": "..."},   // 闭世界模板渲染
    "task": "nli_3class",
    "pred": null,                     // NLI写回{fwd,rev,sym_contra,contra_score}
    "label_map": {"sym_contra":"contradiction", "sym_entail":"equivalent", "else":"neutral"}
  }
}
```

三层评测统一底座：**关系级**（全Pair）/ **声明级**（claim非空子集，NLI三分类）/ **pair级**（366对聚合，real_bug检测）。检测器只见premise/hypothesis，标签在answer key侧——评测协议先于算法。

---

## 6 四类QA（gold全构造性，零人工标注）

| 任务 | 输出 | gold来源 | 指标 |
|---|---|---|---|
| Q1判断 | consistent/inconsistent | expected_label | 按算子×通道分层P/R/F1 |
| Q2定位 | {slot, locator}证据指针 | **变异位置即gold位置**（单变量红利） | 槽位级/元素级 |
| Q3解释 | 自由文本 | MutationRecord模板渲染参考解释 | rubric三要素(位置/内容/类型)命中率 |
| Q4修复 | 修复指令 | **唯一最小修复=撤销变异** | 精确恢复率+往返一致性(修复后重跑Q1应翻转) |

抽检2.5-5%（~60-90条）人工校验标定可信度。

---

## 7 质量门禁与切分

### 六类门禁（17个检查器，fail/warn分级）

G1结构（schema/ID唯一/引用完整）→ G2语义（原文可定位≥95%/数值单位对/模态文件真实）→ G3标签（operator≡label映射/label_tier来源一致/配对完整）→ G4分布（近重复≤5%按变异家族坍缩计量/模态占比/算子覆盖）→ G5泄漏（变异家族同split/SemanticGroup不跨split）→ G6可复现（MANIFEST指纹/runs留痕/快照锁定）。

### 两阶段切分

- **阶段1**（81对，全来自doc02——doc级隔离不可用）：pair级split（57/8/16），同语义组强制同侧；card披露"仅测文档内泛化"
- **阶段2**（重对齐后~250对）：doc级split，dev=与train完全隔离的1-2个小文档；**阶段1的组内划分不带入v1.0**（防二次泄漏）
- dev用途：NLI阈值/嵌入阈值校准（两套θ：in-doc与cross-doc均入card）；test每里程碑只跑一次落runs

### 产出物

`data/gjb_438c/mmqa/`：evidence/pairs/semantic_groups/mutations/consistency/qa各jsonl + splits.json + check_reports/ + DATASET_CARD.md(+json) + MANIFEST注册。版本语义化（主=层schema或split语义变更/次=计数变化/补丁=不改标签的修复）；**fail=0才可发布，warn必须在card披露**。

---

## 8 验收对照（方案6项指标的可达性）

| 指标 | 判断 | 依据 |
|---|---|---|
| 可定位率≥95% | 高 | 81对high锚定+G2.1门禁剔除 |
| Pair精度≥90% | 有条件 | mutation天然达标；silver需抽检仲裁后声明 |
| Mutation有效≥95% | 高 | 确定性算子+diff验证+Z3门 |
| QA可证据化≥95% | 高 | 构造期强制绑定evidence ID |
| 近重复≤5% | 需定口径 | 按变异家族坍缩后计量（card定义） |
| Split泄漏=0 | 可判定 | G5全确定性检查 |

---

## 9 落地顺序（依赖排序）

```
P0-a  MutationRecord v2 schema定稿 + 虚拟pair物化协议        (零新算法, 地基)
P0-b  M3/M4/M5先行(证据最足,纯表/文侧,不需重渲染) → NLI-强档评测集成型
P0-c  M1证据扩展绑定(pair↔section chunk↔数值参数) + Z3方向修复
P1-a  anchor→SVG渲染器 + 渲染一致性门(M8/M6/M7图侧准入)
P1-b  四类QA派生器 + 人工抽检包(复用裁决包格式)
P2    237对low锚点VLM桥重对齐 → 规模×3 + doc级split
全程  runs协议留痕 + LLM判分走缓存 + 计数入tests快照
```

**一句话总纲**：变异实体化打通现有全部管线；最小对+编辑幅度平衡封死表面捷径；单变量干预换三重构造性gold（判断/定位/修复唯一解）；NLI能力边界前置分流保证每个通道只在判得了的样本上被评测。

---

## 附录·与NLI检测方案的融合说明

本数据集设计即之前NLI方案"三层评测体系"的正规化落地：
- 层1合成真值集 = Suite-S（MutationRecord，构造性真值）
- 层2银标 = Suite-R（664条，降级为真实分布参考）
- 层3人工仲裁 = 抽检校准（60-90条起步，后续160条扩展）
- 检测算法的四阶段（声明编译→对齐→NLI→聚合）消费Pair.evaluation接口——算法与数据集共用同一证据寻址空间（EV-xxx ID）。
