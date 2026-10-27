# 48 证据定位Gold标注协议（S7：AVeriTeC式"判定∧定位"联合评分）

日期：2026-10-26 | 状态：P0执行协议 v1 | 里程碑：S7（定位gold标注 91+17）

## 1. 研究对象与动机

当前系统（`algorithms/consistency/qa_module.py`）的`ClaimResult`已输出
`evidence_refs`（证据块ID），但没有gold定位标注来评估定位质量。

AVeriTeC（NeurIPS'23 D&B，arXiv 2305.13117）的核心结论：**判定正确≠
定位正确，两者弱相关**（"AVeriTeC得分=判定正确∧证据质量达标"）。本session
调研再次确认（arXiv 2610.06962：只verdict无证据标注的后训练，span F1 0.564
vs accuracy 0.896，verdict对≠span对）。论文的定位维度评测需要**定位gold**。

S7的输出是一个可评测的定位gold数据集 + 一套"判定∧定位"联合评分协议，
使本项目数据集成为"需求域的AVeriTeC"。

## 2. 评测对象

| 对象 | 规模 | 来源 | 判定gold初值 | 定位gold |
|---|---|---|---|---|
| 官方QA | 91条（S=6/R=8/N=77） | `data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl` | silver（GLM-5.3复核，**非gold**）：`data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl` | 人工标注（本协议） |
| 真实文档违例 | 17条 | `knowledge/consistency_taxonomy_v3.json` doc04_violations（canonical清单见§6） | `refute`（违例为真实存在的不一致） | 违例位置（预填，人工确认） |

QA条目的**证据块**来自上游冻结上下文（`S1QA-XXX-ev-000NNN`，携带
`SourceRef`六字段：doc_id/section/page/block_id/row_id/region_id 与
evidence_id/text/source_type/scope_id/completeness/completeness_proof）。
违例条目的证据块由04号SRS解析块（content_list 411块）快照生成，ID形如
`DOC04-VIO-XX-ev-000NNN`，`source_ref.block_id`指向`block-000NNN`。

## 3. 标注schema（`s7_localization_gold_v1`）

每条标注记录（模板JSONL一行，dataclass见
`tools/build_localization_gold_template.py`的`GoldAnnotationRecord`）：

```json
{
  "schema": "s7_localization_gold_v1",
  "instance_id": "S1QA-001",
  "task_type": "qa_verdict | doc_violation",
  "question": "...",
  "answer": "...",
  "gold_verdict": "refute | support | not_in_evidence",
  "claims": [
    {
      "claim_id": "c1",
      "claim_text": "...",
      "claim_verdict": "refute | support | not_in_evidence",
      "gold_evidence_refs": ["S1QA-001-ev-000043"],
      "gold_span": "系统提示连接失败，用例结束",
      "gold_nie_consulted_refs": [],
      "annotation_note": "标注理由",
      "silver_hint": {"verdict": "...", "evidence_refs": [...], "confidence": 0.9}
    }
  ],
  "evidence_index": [ {"evidence_id": "...", "text": "...", "source_type": "...",
                        "source_ref": {"doc_id": "...", "section": "...", "page": 1,
                                        "block_id": "block-000043", "row_id": "",
                                        "region_id": ""}, "scope_id": "...",
                        "completeness": "open", "completeness_proof": "..."} ],
  "system_prefill": {"verdict": "...", "evidence_refs": [...], "claims": [...]},
  "gold_verdict_init": "not_in_evidence",
  "gold_verdict_init_source": "glm53_silver(final_labels.jsonl, 非gold, 人工须复核)",
  "annotator": null, "annotator_confidence": null,
  "annotation_status": "pending", "round": 1
}
```

字段语义：

| 字段 | 语义 | 模板初值 |
|---|---|---|
| `gold_verdict` | 实例级三态判定（人工确认后才是gold） | silver（QA）/ refute（违例） |
| `claims[].claim_verdict` | claim级三态判定 | silver（QA）/ refute（违例） |
| `gold_evidence_refs` | **判定依据**证据块ID（见§4.1，只能选`evidence_index`内的ID） | QA留空；违例预填违例位置 |
| `gold_span` | 证据块内最小支撑句/行（见§4.2，可选） | 空 |
| `gold_nie_consulted_refs` | NIE时"检索过但无匹配"的块（§4.3，可选，不进主指标） | 空 |
| `silver_hint` | silver级建议（**非gold**，仅供参照，可忽略） | silver claims |
| `system_prefill` | 当前系统（qa_module, use_experts=True）的claim_results预填建议（**非gold**） | 系统输出 |
| `annotation_status` | pending → completed（填完全部gold字段后改） | pending |

**预填≠gold**：`gold_verdict_init`/`silver_hint`/`system_prefill`三个字段
都是给标注员的建议与初值，标注员必须逐条确认或改判；评分只认`gold_verdict`
与`gold_evidence_refs`。

## 4. 标注指南

### 4.1 什么算"支持证据"（gold_evidence_refs）

`gold_evidence_refs` = **删掉它，你的判定依据就受损的证据块**。操作判据：

1. 对support claim：逐块问"这一块单独能否（与其他块联合）支撑该claim"，
   能则入选；只提供背景/主题相关但不参与判定的块**不选**；
2. 对refute claim：选"与claim冲突"的块（如同参数不同值的两处表格行
   所在块、同subject声明不同标识符的块）；两处冲突位置都要标（缺一处，
   冲突关系就不成立）；
3. **最小充分集**：在满足1/2的前提下选最小集合（通常1~4块）；宁缺毋滥
   ——多标的块会稀释micro precision基线的语义；
4. 只能引用`evidence_index`中列出的`evidence_id`（工具会校验）。

### 4.2 什么算gold_span（块内定位）

`gold_span` = **证据块text内足以支撑判定的最小连续文本**：

- 文本块：最小支撑句（按中文句号/分号切分后的单句）；
- 表格块（HTML）：最小支撑行——直接复制该`<tr>...</tr>`内的纯文本（去
  标签），或"单元格1：值；单元格2：值"式行摘录；
- 可选字段：时间紧可只标块级（`gold_evidence_refs`），span覆盖密度单独
  报告（`n_span_scored`），不混入主指标；
- 不确定/多句联合支撑：标参与判定的最小句组，`annotation_note`说明。

### 4.3 NIE的定位标注

NIE（not_in_evidence）的定位语义是"**冻结证据中没有可支持或反驳该
claim的内容**"：

- `gold_evidence_refs`**留空**（默认）：无可定位证据；
- 可选填`gold_nie_consulted_refs`：标注员确认过"检索过但无匹配"的块
  （例如claim提到某用例，而最相关的那一块确实不含它）——只作诊断与
  hard-negative分析，**不进入任何主指标**；
- 评分约定（§7）：gold侧为空时，系统也不引用任何块=正确定位（1.0）；
  引用任何块=0.0。即"正确弃权"计为定位正确，"无中生有"计为定位错误。

### 4.4 违例条目的标注（17条）

违例条目的claim即违例描述，`gold_verdict=refute`（真实存在的不一致）。
模板已按违例位置预填`gold_evidence_refs`（涉及的全部冲突块）。标注员：

1. 核对每个预填块的快照是否确实参与该违例（删掉哪个块违例就不成立）；
   不参与的可删，遗漏的从`evidence_index`补（违例的evidence_index即
   预填块，需增块时在note记块号，仲裁阶段统一补快照）；
2. 表81/82类行级违例（V10~V12）：块级refs保持表块（b407/408），行级
   位置（"row11"）写进`gold_span`或`annotation_note`；
3. `gold_span`：冲突双方的原文摘录（各一句/一行），用`；`分隔。

## 5. 双人标注+仲裁流程

### 5.1 流程

```text
R1 两名标注员独立标注同一模板(不同副本, 不看对方结果, 可看silver_hint/system_prefill)
R2 一致性检查: kappa子命令 → verdict κ / 定位κ / Jaccard / span一致率
R3 分歧仲裁: κ<0.7或单条分歧 → 第三人(仲裁者)逐条裁决, 仲裁结果=gold
R4 gold定稿: annotation_status=completed + 注册MANIFEST(重跑tools/build_data_manifest.py)
```

### 5.2 κ系数计算方法（`kappa`子命令，Cohen's κ）

| 维度 | 标签 | κ类型 | 门槛 |
|---|---|---|---|
| 判定 | 双方`gold_verdict`（3类：support/refute/NIE） | 多类Cohen's κ | ≥0.7效度充分；0.4~0.7需仲裁；<0.4体系存疑 |
| 定位 | 双方"是否给出定位"（refs非空=located）二值 | 二值Cohen's κ | 同上 |
| 定位质量 | 双方均located的实例上Jaccard均值（对称\|A∩B\|/\|A∪B\|） | 描述统计 | 报告值，无硬门槛 |
| span | 双方都填span的实例上最佳char-F1均值 | 描述统计 | 报告值 |

注：κ用双方**独立标签向量**计算（定位κ=双方各自的located/not_located
向量），不是双方refs的重合率本身；重合率用对称Jaccard单独报告——评分
用的单向gold覆盖率（§7）只面向gold×system，不用于标注者间一致。

### 5.3 仲裁规则

- verdict分歧：仲裁者重读问题/答案/证据块，独立判三态，可与两方之一
  相同也可都不相同；
- refs分歧：取"并集-明显不参与判定的块"（仲裁者重新执行§4.1的最小
  充分集判据）；
- span分歧：取更短的那个（最小支撑原则）；
- 仲裁轮次记`round: 2`，`annotation_note`保留两方分歧摘要。

## 6. 17个真实违例的标注规范

**canonical 17**以`docs/srs_project/project_guide.md` §2"04号SRS上的真实
不一致清单（17个，全部来自深读）"为准，逐条锚定到taxonomy v3的
`doc04_violations`条目（工具校验唯一定位）：

| ID | 类别 | taxonomy项 | 块位置 | 违例 |
|---|---|---|---|---|
| VIO-01 | identifier | TERM-07 | b220/225 | 连接池配置/初始化同ID PZXQ-GN-LJCGL-LJCCSH |
| VIO-02 | identifier | TERM-07 | b057/040 | 数据库关闭ID跨位置矛盾（SJKGB vs SJKGBGN） |
| VIO-03 | identifier | TERM-07 | b267/268/271/274/277 | 表48前缀SJTBGX vs 节标题SJTYFW |
| VIO-04 | identifier | TERM-07 | b285/286 | 表53组件顺序颠倒 |
| VIO-05 | identifier | TERM-07 | b139/140/145/150 | 表23 BLOB子项ID缺BLOBSJCZ段 |
| VIO-06 | enumeration | TERM-03 | b032/035 | 3.2.1文本5项 vs 表3仅4行 |
| VIO-07 | enumeration | TERM-03 | b181/184 | 「缓存修改」vs「缓存更新」 |
| VIO-08 | enumeration | TERM-03 | b011/024 | 1.2两套分类法 vs 3.2六项分类 |
| VIO-09 | enumeration | LOGIC-05 | b067/087 | 表9「平版」错别字 |
| VIO-10 | traceability | GJB-05 | b407/408 | 表81/82正逆追踪矛盾 |
| VIO-11 | traceability | GJB-05 | b407 | 追踪锚点失效（3.2.1.7不存在） |
| VIO-12 | traceability | GJB-05 | b407 | 同行矛盾（映射非空+说明不追踪） |
| VIO-13 | exception_template | LOGIC-02 | b192/222/227 | E1内容与用例主题错位 |
| VIO-14 | exception_template | LOGIC-02 | b237/242 | 申请/释放句柄错误归属 |
| VIO-15 | document_name | TERM-05 | b348 | 误写「数据同步共享服务」 |
| VIO-16 | function_coverage | GJB-04 | b011 | 1.2声称审计日志但3.2无对应 |
| VIO-17 | qualification_coverage | GJB-01 | b404 | 表80合格性覆盖缺口 |

**违例位置即gold定位**（预填`gold_evidence_refs`），标注员按§4.4确认。

### 6.1 数据源差异声明（诚实边界）

- taxonomy v3各item的`doc04_violations`合计**34条字符串**，而canonical
  计数为**17**（`doc04_summary.total_real_violations`与project_guide §2
  一致）。差异来源：(a) 同一违例在多项下重复记录（同ID双指在TERM-02与
  TERM-07、E1错位在TERM-04与LOGIC-02），canonical只计一次；(b) 收录范围
  ——canonical 17限定为"跨位置可验证的不一致"，taxonomy中另17条
  （TERM-06量纲、TERM-08大小写、PARAM-05、LOGIC-03细节、LOGIC-08、
  GJB-02/06/08/10/11等"条款有无"类发现）在taxonomy中保留但不进S7
  canonical集；
- VIO-15（文档名）：taxonomy的TERM-05 `doc04_violations`为空，本条依据
  project_guide §2并已独立核验块b348内容（"数据同步共享服务软件环境需求
  见表70。"——04号应为"数据统一访问服务"）；工具中以`taxonomy_ref: null`
  标记该来源缺口；
- VIO-17（表80）：project_guide §2记为GJB-06，taxonomy v3记录在GJB-01，
  **以taxonomy为准**；
- 类别计数5/4/3/2/1/1/1=17与`doc04_summary.violation_distribution`
  （identifier5/enumeration4/traceability3/exception_template3/
  document_name1/completeness1）在后5类的归组口径不同（guide把功能/
  合格性分列，distribution把E1模板类合并），总数两边都是17；S7模板采用
  guide口径（`category`字段），差异在此声明。

## 7. 评分定义（`score`子命令）

输入：标注完成的gold JSONL + 系统输出JSONL（如`system_output_v1.jsonl`，
含`instance_id/verdict/evidence_refs/claims`）。指标：

```text
VerdictAccuracy        = 判定正确的实例比例（3态）
LocalizationPrecision  = Σ|gold∩sys| / Σ|sys|     （micro, sys非空实例）
LocalizationRecall     = Σ|gold∩sys| / Σ|gold|     （micro, gold非空实例）
overlap(实例)          = |gold∩sys| / |gold|
                         gold为空时: sys为空=1.0(正确弃权), 否则=0.0(无中生有)
AVeriTeCScore(τ)       = 判定正确 ∧ overlap ≥ τ 的实例比例（τ默认0.5）
SpanF1                 = 字符级(多重集)重叠F1的宏平均
                         （仅双方都提供span的实例; 每实例取最佳配对）
```

关键约定：

1. **定位粒度=证据块级**：系统侧的语句级引用（`#s`后缀，如
   `ev-000043#s5`）归一到父块；gold即块级；
2. **系统定位集合**=行级`evidence_refs`（或判定性claim——support/refute
   ——的refs并集）；NIE claim的refs是"检索过未决"诊断，**不是**定位主张；
3. **τ=0.00即VerdictAccuracy**（`averitec_by_threshold`给出τ∈{0,0.25,
   0.5,0.75,1.0}扫描）；
4. **条件分解**：`localization_pass_rate_given_verdict_correct`（判定
   正确样本中定位达标率）是"判定≠定位"的主诊断量——它<1的程度即两者
   的弱相关性；另按gold verdict分层报告（S/R/NIE各自accuracy/averitec/
   mean overlap）；
5. 违例条目无系统输出时计入`missing_system_ids`（S7阶段违例检测系统未
   接线，由S3专家族后续补），不进指标分母；
6. 未匹配ID（gold有/系统无、系统有/gold无）单独列出，不静默丢弃。

## 8. 与AVeriTeC评分的对齐说明

| 维度 | AVeriTeC | S7（本协议） | 理由 |
|---|---|---|---|
| 联合得分 | 判定正确∧证据质量达标（阈值0.5） | 判定正确∧overlap≥τ（默认0.5） | 同一构造：判定与证据/定位取∧ |
| 证据单元 | 从web检索到的自由文本QA对证据 | 上游冻结的离散证据块（block ID） | 本任务证据单元本来就是冻结块，无文本切分歧义 |
| 证据相似度 | gold与预测证据间的文本相似度聚合（ROUGE类） | 块ID精确集合重合 | 离散块ID匹配无模糊性；不需要文本相似度兜底 |
| 覆盖方向 | gold证据被预测证据覆盖 | overlap=\|gold∩sys\|/\|gold\|（gold覆盖向） | gold refs是"标注员确认的最小充分集"而非"全部合法证据"，precision对系统多引合法块不公平；召回向才是"是否落在判定依据上" |
| NIE/弃权 | 声明不可验证类 | gold空∧sys空=正确定位 | "正确弃权"是三态任务的合法输出，须计分 |
| 粒度归一 | — | 语句级#s后缀归一到父块 | 系统可引用更细粒度，评分统一到gold粒度 |

一句话对齐声明（论文可引用）：**S7的AVeriTeCScore保持"判定∧定位"的
联合构造与阈值语义，把AVeriTeC的自由文本证据相似度实例化为离散证据块
的集合重合**——因为本任务的证据单元是上游冻结的块，块ID匹配即证据匹配，
无需文本相似度近似。

## 9. 代码入口与复现

```text
tools/build_localization_gold_template.py   build(默认)/score/kappa 三合一
tests/test_localization_gold_template.py    24项: 评分手算fixture+模板+canonical锁定
data/gjb_438c/localization_gold/
  annotation_template_v1.jsonl              108行(91 QA + 17违例)待标注模板
  system_output_v1.jsonl                    91行系统预填输出(评分即用)
  annotation_template_v1_metadata.json      lineage(输入sha256+计数+配置)
```

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/build_localization_gold_template.py
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/build_localization_gold_template.py score --gold <填好的gold.jsonl> --system data/gjb_438c/localization_gold/system_output_v1.jsonl
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/build_localization_gold_template.py kappa --gold-a <A.jsonl> --gold-b <B.jsonl>
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python -m pytest tests/test_localization_gold_template.py -q
```

score/kappa的结果按runs协议落盘（`data/gjb_438c/runs/score_localization_*`
与`kappa_localization_*`，含config+git sha）。

## 10. 边界与诚实声明

1. **silver初值不是gold**：`gold_verdict_init`来自GLM-5.3复核（S=6/R=8/
   N=77），标注员必须逐条确认或改判；未完成的标注不得进入score的论文
   数字（模板直评只作管线冒烟）；
2. **预填建议可能锚定偏差**：silver_hint与system_prefill都写在模板里
   （标注效率与可用性权衡），标注员可忽略；κ是防锚定的第一道检查；
3. **违例17的系统侧缺失**：S7只交付gold侧与评分协议，违例检测系统
   （S3专家族）接线后补`system_output`的17行；在此之前违例条目只进
   missing计数；
4. **gold注册时点**：模板是确定性构建（元数据含输入sha256，测试锁定
   108行与分布），不进MANIFEST；**人工标注完成的gold定稿后**须重跑
   `python tools/build_data_manifest.py`注册保护；
5. **定位粒度声明**：主指标在块级；行级/span级定位是gold_span的补充
   维度（SpanF1条件报告），不与块级混算；
6. **κ样本量**：91+17=108的样本量下κ的95%CI较宽（|κ|≈0.7时约±0.1量级），
   论文报告κ须带区间或声明该局限。
