# CascadeVerify v2 全栈实现与评测结果总览

> 定稿日期：2026-10-27（Wave 7收口：可信度审计→P0/P1修复→诚实数字——持久dev/test切分+test侧诚实评测、P1三项确定性修复support召回2/6→5/6、06号跨文档sound评测集与gap量化，审计-响应对照见§10；Wave 6收口：L1专家族补至设计§6.3全量9行+变异注入漏检率矩阵+学习路由器诊断；Wave 5主表/消融数字经9专家栈零回归核验后全部保持）| 数据来源：`data/gjb_438c/runs/`（runs协议落盘，git_sha=ff0d4950）
> 评测集：91条官方冻结QA（`data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl`）vs GLM-5.3 silver标签（S=6 / R=8 / N=77，**非gold**，标注来源run: `review_qa_with_glm53_582b51e5_20261021_145212`）+ 17条真实违例转化集（`data/gjb_438c/localization_gold/violation_evalset_v1.jsonl`）+ 06号跨文档sound评测集30条（`data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl`，§10.3）
> 方法设计：`docs/srs_project/literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §6
> **本文档是论文数字的唯一权威来源。所有数字逐项取自result.json，每个数字标注来源run目录。**

---

## 1. 架构总览（已实现的完整级联）

```text
输入 QAInput = (question, answer, 冻结证据块)           [91条QA × 平均6.3块/条]
  │
  ├─ [DEQ证据管线·可选]  deq_pipeline.py
  │    E0 scope门(实体+范围匹配拒错域证据) → E1 检测项感知评分(40项→证据形态需求)
  │    → E2 语句对齐(claim×statement最优配对)；纯确定性
  │
  ├─ [问题路由] qa_router.py → 40项检测项(检测项=先验路由信号)
  ├─ [答案分解] answer_structure.py → 原子claim集 Decomp(A)
  ├─ [证据线性化] evidence_statements.py：表格HTML→字段级语句(位置保持解析,
  │    行级定位row_index+scope key)；能力/数据/接口表按表头签名派发
  │
  ├─ [per-claim基础通道] qa_module.py._verify_claim
  │    exact_statement / identifier_exact_match / explicit_quote_polarity /
  │    数值区间 / semantic_unresolved / conservative_unresolved
  │
  ├─ [L0/L1确定性专家族(9个)] qa_module.py._expert_channels
  │    ├ entity_detector.py    L0实体冲突  (TERM-05/07/08; method=l0_entity_detector:*)
  │    ├ e1_expert.py          E1模板专家  (LOGIC-02; method=e1_template_match)
  │    ├ sequence_expert.py    序列对齐    (LOGIC-03; method=sequence_alignment)
  │    ├ trace_expert.py       追溯join    (GJB-05)
  │    ├ gjb_presence_expert.py GJB有无    (GJB-01~11 封闭清单)
  │    ├ id_join_expert.py     ID注册表join (TERM-07跨位置ID; method=id_join_registry)
  │    ├ enum_join_expert.py   枚举值域join (TERM-03封闭集合; method=enum_join_registry)
  │    ├ numeric_z3_expert.py  Z3数值约束  (PARAM-01/03/05/06/07; method=numeric_z3_expert)
  │    └ coverage_expert.py    覆盖完备join (GJB-01/04/06; method=coverage_join)
  │
  ├─ [残差派发·C1原则] 仅 semantic_unresolved/conservative_unresolved 且当前无refute时
  │    ├ L2 NLI残差  nli_residual.py（本地mDeBERTa微调ckpt=egt_finetuned_v2,
  │    │   gate=0.7；premise构造与训练共享 nli_training.build_premise）
  │    ├ 级联升级(use_cascade) L2的refute候选→L3复检(判决整体替换L2该claim);
  │    │   support/NIE直通；conformal档(keep_confidence=0.95)高置信refute免升级
  │    └ L3 LLM残差  llm_residual.py（残差claim批量进一个聚焦prompt,
  │        ≤30语句按行分组选择；llm_json(cache=True)）
  │
  ├─ [per-claim融合] qa_module.py._fuse_per_claim：同一claim多通道判定
  │    refute > support > NIE（无能力判定不得否决已验证判定）
  └─ [跨claim聚合] ∃refute→refute；∀support→support；否则NIE（开世界假设）
```

支撑模块（非在线通道）：`evidence_compiler.py`（GJB表格→类型化关系schema+按claim-kind聚焦视图：能力/用例/接口/值域/追溯/合格6型）、`egt_synthesis.py`（EGT三态合成数据）、`nli_training.py`（合成数据→NLI训练对，premise管线与推理共享）、`router.py`（学习路由器：post-L1特征+四路由决策，Wave 6负结果见§8.3）、`baselines.py`、`nli_local.py`（本地NLI加载）、54变异算子族（`term/param/numeric/logic/structural/gjb/answer_mutations.py`）。

**L1能力齐备声明（Wave 6）**：9个专家模块覆盖设计§6.3专家族表的**全部9行**（ID join/集合运算/区间算术/数值聚合/E1模板/序列对齐/追溯join/覆盖完备/GJB有无——其中区间算术+数值聚合两行由numeric_z3一并承载、覆盖完备行=coverage）；按能力粒度计L0/L1确定性能力共**11项**（7个既有专家各1项+numeric_z3的3项能力增量[量纲换算/区间三态Z3判定/跨参数聚合]+coverage的覆盖join）。两个新专家在91QA零触发（触发前提=冻结证据含数值约束或合格性覆盖声明，见§8.1/§8.2），主表数字不变（§2零回归核验）。

每个新模块均有独立测试（`tests/test_evidence_compiler.py`、`test_e1_expert.py`、`test_entity_detector.py`、`test_sequence_expert.py`、`test_trace_expert.py`、`test_gjb_presence_expert.py`、`test_id_join_expert.py`、`test_enum_join_expert.py`、`test_numeric_z3_expert.py`、`test_coverage_expert.py`、`test_router.py`、`test_egt_synthesis.py`、`test_evidence_statements.py`、`test_deq_pipeline.py`、`test_nli_residual.py`、`test_llm_residual.py`、`test_violation_evalset.py`、`test_mutation_injection.py`、`test_qa_consistency_module.py`等，tests/共121个测试文件）。

---

## 2. 主结果表（91QA vs silver）

来源：`runs/eval_paper_matrix_c409df7f_20261027_125551/result.json`（B0–B5+消融+bootstrap，7专家栈全量重跑）+ `runs/eval_cascade_1e92cdce_20261027_124941/result.json`（L2/cascade两行，同栈同日）。LLM调用数格式：invocations(api/缓存命中)。

| 系统 | acc | macro-F1 | S: P/R/F1 | R: P/R/F1 | N: P/R/F1 | LLM调用 |
|---|---|---|---|---|---|---|
| B0 majority-NIE（坍缩基线） | 0.8462 | 0.3056 | .0/.0/.0 | .0/.0/.0 | .846/1.0/.917 | 0(0/0) |
| B1 零样本NLI残差（raw mDeBERTa，无专家） | 0.5714 | 0.3272 | .118/.333/.174 | .067/.125/.087 | .831/.636/.721 | 0(0/0) |
| B2 LLM直推（每QA一次调用，无级联） | 0.7143 | 0.6105 | .214/1.0/.353 | .714/.625/.667 | .964/.701/.812 | 91(0/91) |
| B3 确定性通道（7专家族，无残差） | 0.9011 | **0.6381** | .500/.167/.250 | .833/.625/.714 | .916/.987/.950 | 0(0/0) |
| B4 全级联（最强L3配置=7专家+L3） | **0.9121** | **0.7257** | .667/.333/.444 | .700/**.875**/.778 | .949/.961/.955 | 83(0/83) |
| B5 纯LLM残差（无确定性专家） | 0.8681 | 0.7085 | .385/.833/.526 | .714/.625/.667 | .972/.896/.932 | 86(0/86) |
| L2 NLI（EGT-v2叙事微调，gate=0.7）† | 0.8022 | 0.5437 | .333/.167/.222 | .368/**.875**/.519 | .942/.844/.890 | 0(0/0) |
| cascade（L2→L3升级路由）† | **0.9121** | 0.7185 | .500/.333/.400 | **.857**/.750/**.800** | .938/.974/.955 | **15(0/15)** |
| cascade_conformal（keep=0.95）† | 0.8462 | 0.5836 | .333/.167/.222 | .467/.875/.609 | .945/.896/.920 | 13(0/13) |

† 四配置（baseline/l2_nli/l3_llm/cascade）及conformal档均取自 `eval_cascade_1e92cdce_20261027_124941`（checkpoint=egt_finetuned_v2，nli_gate=0.7，keep_confidence=0.95）；该run中baseline/l3_llm配置与paper_matrix的B3/B4数字一致（0.9011/0.6381、0.9121/0.7257），两run互为印证。

**头条读数**：
- accuracy最优=B4/cascade 0.9121（91条中83条对）；**macro-F1最优=B4 0.7257**——7专家栈下B4首次在macro-F1上反超B5（0.7085，+0.0172）：确定性refute（id_join/enum_join的跨位置join命中）短路了残差派发并抬高refute召回（B4 R-recall 0.875，B5只有0.625）；
- **refute F1最优=cascade 0.8000**（P=0.8571），仅15次LLM调用（全量L3需83次，调用率15/91≈16.5%）——级联经济学见§6.3；
- L2叙事NLI单独把refute召回拉到**0.875**（7/8），代价是精度坍到0.368（19个预测refute里12个伪）——这正是升级路由要修的失败模式；
- 两join专家是B3从0.5628（5专家栈，`eval_paper_matrix_0fabaced_20261027_023711`）升到**0.6381**的全部增量来源（enum_join在91QA贡献-enum_join消融-0.026、id_join的claim级命中被其他通道冗余覆盖，详见§3与§7）。

**L3参照漂移声明**（来自 `eval_cascade_1e92cdce_20261027_124941/result.json` 的 `llm_reference_drift` 字段）：10-26的L3历史参照 `runs/eval_llm_residual_5dd69927_20261026_173434`（macro-F1 0.7799、acc 0.9341、refute P=1.0/R=0.875）基于当时的语句线性化；`evidence_statements.py` 在10-26 20:52（该L3评测17:34之后）被修改（premise bug修复，见§6.2），当前管线下L3提示词未命中旧缓存、当日重采样；且当日有并行会话共享llm_cache。**四配置对比以124941同管线同日测量为准（L3=0.7257），0.7799仅作历史参照保留。**

**Wave 6零回归核验（9专家栈）**：`runs/eval_router_2b76c358_20261027_170640`在9专家栈（+numeric_z3/coverage）上重测四配置——baseline（确定性）0.9011/**0.6381**、l3_llm 0.9121/**0.7257**、fixed_cascade **0.7185@15次**LLM调用，与Wave 5定稿run（125551/124941）逐位一致；该run全部claim_methods中无`numeric_z3_expert`/`coverage_join`条目——**两个新专家在91QA零触发零回归**（触发前提是冻结证据含数值约束/合格性覆盖声明；91QA冻结证据的数值事实数=0，这一"证据构成发现"见§8.1）。主表与§3消融表因此保持Wave 5数字、不重跑。

---

## 3. 消融表（10项，基于B4=最强L3配置）

来源：`runs/eval_paper_matrix_c409df7f_20261027_125551/result.json` 的 `ablations`。单专家消融=expert_filter传"7专家全集去该项"（与B4仅差被移除的一个专家）。

| 消融 | acc | macro-F1 | Δ macro-F1 | LLM调用 |
|---|---|---|---|---|
| B4（基准） | 0.9121 | 0.7257 | — | 83(0/83) |
| -e1_expert（去E1模板专家） | 0.9011 | 0.6869 | **-0.039** | 84(0/84) |
| -entity_detector（去L0实体检测） | 0.9121 | 0.7257 | +0.000 | 83(0/83) |
| -sequence_expert（去序列专家） | 0.8791 | 0.7290 | +0.003 | 83(0/83) |
| -trace_expert（去追溯专家） | 0.9121 | 0.7257 | +0.000 | 83(0/83) |
| -id_join_expert（去ID注册表join专家） | 0.9121 | 0.7257 | +0.000 | 83(0/83) |
| -enum_join_expert（去枚举值域join专家） | 0.9011 | 0.6997 | **-0.026** | 85(0/85) |
| -per_claim_fusion（去per-claim融合） | 0.8901 | 0.5735 | **-0.152** | 83(0/83) |
| -llm_residual（关L3，≡B3） | 0.9011 | 0.6381 | **-0.088** | 0(0/0) |
| -all_experts（全专家关，≡B5） | 0.8681 | 0.7085 | **-0.017** | 86(0/86) |
| DEQ on（use_deq=True vs B4默认off） | 0.9121 | 0.7329 | +0.007 | 82(0/82) |

要点：四项消融造成实质损失——**per-claim融合（-0.152）、L3残差（-0.088）、E1专家（-0.039）、enum_join专家（-0.026）**；entity/sequence/trace/id_join在91QA的macro-F1上是中性（id_join在91QA仅1次claim级触发且被其他refute通道冗余覆盖，其价值由17真实违例集的identifier类5条承载，见§7——**91QA silver里跨位置join信号稀薄、17违例集是定向探针**，两个评测集互补）。-all_experts从5专家栈时代的+0.009翻成-0.017：专家族的确定性refute开始净贡献。DEQ开启时refute F1从0.7778→0.8000（P .667/R 1.0），全缓存命中（0次API调用），维持证据质量-成本权衡项定位。

**Wave 6注**：消融表保持Wave 5的10项口径**不重跑**——新增numeric_z3/coverage两专家在91QA零触发（§2零回归核验），对其消融必然中性（0判定变化、0调用变化）；两个新专家的效果证据定向在17违例集（§7：coverage闭合VIO-17，检出15/17→16/17）与变异注入矩阵（§8.4）。

---

## 4. 统计显著性（paired bootstrap，macro-F1）

来源：`runs/eval_paper_matrix_c409df7f_20261027_125551/result.json` 的 `bootstrap`（1000次重采样，seed=42，双侧p）。第四对B4 vs -join_experts=同run的`join_experts_off`配置（7专家族去id_join+enum_join，macro-F1 0.6997）。

| 对比 | Δ macro-F1 | 95% CI | p |
|---|---|---|---|
| B4 vs B3 | +0.0876 | [-0.0511, +0.2666] | 0.276 |
| B4 vs B5 | +0.0172 | [-0.1641, +0.2094] | 0.834 |
| B4 vs B2 | +0.1151 | [-0.0980, +0.3130] | 0.314 |
| B4 vs no_join_experts | +0.0260 | [+0.0000, +0.1019] | 0.666 |

**结论**：四对比较在p<0.05下均不显著。n=91且refute只有8条正类，macro-F1的检验功效不足；两join专家的paired delta（+0.026，CI下界恰好触0）在91QA上的功效同样不足——其效果证据在17真实违例集上（§7，检出+35.3pp，n=17的配对符号检验口径）。论文表述应使用"consistent improvement, not individually significant at n=91"的措辞，显著性声明留给EGT合成数据上的受控实验或17真实违例专项集。

---

## 5. EGT数据集演化（v1近拷贝 → v2叙事，R样本sound性）

来源：`runs/build_egt_dataset_3a52cd3f_20261026_154036`、`build_egt_dataset_721c8665_20261026_165547`、`build_egt_dataset_8a8716bb_20261027_003528`；训练：`runs/train_residual_nli_ade325ae_20261026_195906`（v1模型）、`runs/train_residual_nli_acfead4b_20261027_013647`（v2模型定稿）。真实评测：`runs/eval_nli_residual_4971ceba_20261026_201247`（v1模型）、`runs/eval_cascade_1e92cdce_20261027_024429`（v2模型=l2_nli配置；124941同配置数字一致互证）。

| 代际 | 版本 | 合成路径 | 规模 | 训练ckpt | dev | 91QA真实 | refute R |
|---|---|---|---|---|---|---|---|
| EGT v1 | `egt_synthesis_v1`（3a52cd3f） | QA种子97条（5种子方法）近拷贝改写 | 117（39×3平衡；raw 141/39/159） | —（仅数据实验） | — | — | — |
| EGT v2 | `egt_synthesis_v2`（721c8665，16文档语句路径；中间版2f65089e为04单文档714样本） | 91QA种子 + 16文档statement路径 | 3000（1000×3） | `egt_finetuned`（ade325ae，n_train 2718/n_dev 282，4ep） | acc 0.9645 / macroF1 **0.9648** | macroF1 **0.4963**（acc 0.8132） | **0.375** |
| EGT v3 | `egt_synthesis_v3_narrative`（8a8716bb） | statement路径 + 叙事路径 + 混合（叙事占比 S .60/R .80/N .60） | **4500**（1500×3；raw 3631/2851/4628） | `egt_finetuned_v2`（acfead4b_013647定稿，n_train 4067/n_dev 432，4ep；同日3ep/5ep变体见§9.4） | acc 0.9722 / macroF1 0.9722 | macroF1 **0.5437**（l2_nli配置） | **0.875** |

**R样本sound性**（v3 statement路径，8a8716bb的`acceptance`字段）：refute种子17569 → 不可翻转结构跳过14569 → 自检跳过248（自检通过率**0.9052**）→ 模块门拒377 → 保留2397条R样本，其中模块复核判为refute 2234（**refute率0.932**）、NIE 157、support 6。R标签是构造性sound的（算子翻转语义已知），模块门只是额外质检。

**叙事路径构成**（8a8716bb的`narrative_path`）：7237个叙事样本，6族——usecase_e1 1340 / interface_flow 433 / capability_device 1865 / capability_state 1548 / trace_binding 1286 / param_value 765。终版按来源：statement 1405 + narrative 2999（其余为QA种子路径贡献）。

---

## 6. 科研发现（按重要性排序）

### 6.1 EGT文法设计定律：合成文法决定迁移，dev分数与真实迁移完全脱钩

- 近拷贝文法（EGT v2，从证据语句近拷贝改写claim）：dev macro-F1 **0.9648**（ade325ae训练run），91QA真实 **0.4963**，refute召回仅 **0.375**（`eval_nli_residual_4971ceba_20261026_201247`）。
- 叙事文法（EGT v3，按GJB表格语义族生成自然叙事句+成员级扰动）：dev 0.9722（同量级），91QA真实 **0.5437**，refute召回 **0.875**（`eval_cascade_1e92cdce_20261027_024429` l2_nli）。
- **定律**：dev分数在两种文法下都≈0.97（合成分布内可分），对真实迁移毫无预测力；**refute召回从0.375翻到0.875的全部增量来自训练文法从"近拷贝"换成"叙事"**——模型学到的是"如何读GJB表格的叙事化陈述并比对成员集合"，而不是词面复制检测。论文EGT节的核心claim。
- 附注：v1→v3的macro-F1增量（0.4963→0.5437）远小于refute召回增量，因为叙事NLI的refute精度坍缩（0.375→0.368）——迁移的是召回能力不是校准能力，这正是升级路由（§6.3）的输入假设。

### 6.2 两个premise bug及其修复（证据忠实性 > 指标）

**Bug A：能力表列错位（124/181表）**。旧解析`_table_rows`为用例表语义剔除空单元格，但能力/数据/接口表的`序号`列常为空——剔除后数据行整体左移，表头按位置zip时『方式名称』读到『运行状态』的值。普查（91QA冻结证据330个表格块）：**124/181**张能力型表的数据行含空单元格（会话census记124/181；本文复核签名口径为124/180，±1来自表头签名边界）。修复：`table_rows_positional`位置保持解析（空单元格占位），能力/数据/接口表走表头签名派发的位置保持路径（`evidence_statements.py:61-74`）。
**Bug B：thead误派发**。GJB表格两表型——表头式433张（首行=thead）与键值式774张（用例描述表，无thead、首行即"Use Case名称：…"数据行；表型census见`docs/srs_project/archive_20261022/18_feature_extraction_late_interaction_report.md`）。旧派发默认首行即表头，键值式表/表头不在首行的表被误派发到错误线性化器（能力表落入用例键值路径时表头行被当数据行输出、字段名与值错位配对）。修复：`linearize_evidence`按表头签名四路派发（标识符+需求描述/方式名称+运行状态→能力；单位+最大最小→数据；发送方+接收方→接口；其余→用例），并在用例线性化器内嵌能力表表头识别（`_HEADER_LABEL`覆盖能力表全部列名）作防御。残留：追溯表签名未覆盖（复核1/330落用例路径，场景1无影响）。
**对管线的影响**：修复改变了全部下游premise（L2训练对+L3提示词）——这是L3从历史参照0.7799漂移的直接原因之一（§2漂移声明；5专家栈当日重采样为0.6997，7专家栈现值0.7257）；修复后premise忠实于表格真值，指标下降被接受（premise忠实性优先于metric）。L3提示词中保留"字段标签可能错位，判定以语句内容为准"的防御性声明（`llm_residual.py:60`）。

### 6.3 级联经济学：refute F1最优@16.5%调用成本

来源：`runs/eval_cascade_1e92cdce_20261027_124941` 的 `cost_quality_table`。

| 配置 | macro-F1 | refute P | refute R | LLM invocations |
|---|---|---|---|---|
| baseline（7专家） | 0.6381 | 0.833 | 0.625 | 0 |
| l2_nli | 0.5437 | 0.368 | 0.875 | 0 |
| l3_llm | 0.7257 | 0.700 | 0.875 | 83 |
| **cascade** | **0.7185** | **0.857** | 0.750 | **15** |
| cascade_conformal | 0.5836 | 0.467 | 0.875 | 13 |

- cascade用**15次LLM调用（全量L3的18%；按91条QA计调用率16.5%；13条实例触发升级）**取得五配置最高refute F1 **0.8000**与最高refute精度0.8571——升级路由只复检L2的refute候选（L2唯一silver失败模式：R=0.875但P=0.368），support/NIE直通，LLM只为伪refute付费。
- 升级统计（124941的`cascade_escalation`）：L2判定395条claim，升级75条claim/13条实例，0条LLM失败。L2→cascade翻转：**纠偏11条**（伪refute回到silver，如S1QA-006/007/020/030/033/034/040/044/067/076/078——多为NIE边界被L2误判refute），**回退1条**（S1QA-063，见§6.6——074已由enum_join在L1确定性层短路，不再进入升级路径）。
- 目标核对（124941的`targets`）：macro-F1≥0.75 ✗（0.7185）、refute P≥0.9 ✗（0.8571）、LLM调用≤30 ✓（15）。**结论：成本目标达成，质量目标未达——论文级联节如实报告，质量缺口归因于§6.6的claim归因错位与silver边界而非路由本身。**

### 6.4 负结果集（如实报告，论文Negative Results节素材）

1. **零样本NLI坍缩**：B1（raw mDeBERTa直推）macro-F1 **0.3272**、refute F1 0.087（`eval_paper_matrix_c409df7f_20261027_125551`）——通用NLI模型在GJB域三态任务上接近多数类坍缩，域适配必要性的直接证据。
2. **L2单独不成系统**：叙事NLI单独（l2_nli）macro-F1 0.5437低于纯确定性baseline的0.6381（`eval_cascade_1e92cdce_20261027_124941`）——召回0.875的增益被19个预测refute里12个伪refute的精度坍缩抵消；NLI是召回引擎不是裁决器，必须配升级路由。
3. **conformal高置信档不可信**：conformal档（keep_confidence=0.95）把高置信refute免升级直通——7专家栈定稿run（124941）kept档n=1、P=0.0；同日三次更早run（`eval_cascade_1e92cdce_20261027_022407/023405/023644`，5专家栈）kept档n=7、P=**0.2857**（2/7）。两值不一致源于共享llm_cache在paper_matrix run（023711）期间被写入39条新API响应（两档间的唯一管线状态变化）。**无论取哪个口径，高置信档refute精度(≤0.33)远低于升级档(0.857)与L3复检(0.7)——NLI的softmax置信度不承载refute精度信息，conformal提前退出在当前L2上不可用**（与cascade_conformal整体macro-F1 0.5836<cascade 0.7185一致）。
4. **fp16训练波动**：egt_finetuned_v2同配置重训（fp16, seed 42），dev metric漂移（同config_hash acfead4b两次运行dev macro-F1 0.9696 vs 0.9722，`acfead4b_20261027_003550` vs `acfead4b_20261027_013647`）；91QA真实macro-F1在12次同日评测（`eval_nli_residual_2996af6b_20261026_212915`…`20261027_015457`）中波动**0.4325–0.5298（极差≈0.10，±0.05）**。论文需报告：fp16非确定性使单checkpoint数字不可复现到±0.05，v2定稿数字以013647+024429/124941链条为准。
5. **silver边界模糊（GLM的NIE/refute边界不自洽）**：silver标签由GLM-5.3按answer-vs-**全文档**复核产生；级联内L3残差判定answer-vs-**冻结证据**。同一模型家族在两种证据观下对同批边界样本给出相反判定——7专家栈升级run中S1QA-063（silver=refute，依据"文档级设备集合矛盾"）被GLM残差通道把两条claim全判support→实例翻回NIE（`eval_cascade_1e92cdce_20261027_124941`的regressed列表，rationale为"平板、平板、手持版三种终端支持不同数据访问方式…均一致"）；10-26 L3参照run亦有false_support S1QA-064（`eval_llm_residual_5dd69927_20261026_173434`）。原同为边界案例的S1QA-074已由enum_join在确定性层闭合（§6.6）。开放世界假设的边界（"证据里没有≠文档里没有"）本身是标注分歧源——**gold人工标注是当前最大缺口**（§11，标注工作台已建）。
6. **学习路由器学不出（Wave 6）**：EGT监督训练的梯度提升路由器（20维post-L1特征，5折CV macro-F1 0.456/acc 0.6933）在91QA held-out的**路由一致率仅0.0875**（7/80；EGT内样本一致率0.8233，一出EGT即崩）——80条可路由实例中70条被路由escalate_l3，oracle为73条accept_l1；端到端macro-F1 0.7257@**73次**LLM调用。对照：**oracle路由上限0.7867 macro-F1@2次调用**（refute P 0.8889/R 1.0）vs 固定级联0.7185@15次——路由信息确实存在（+0.068 macro-F1且-13次调用），但EGT监督学不出。**严格防泄漏体制下学习路由不值得部署**；三重归因（特征分布外推/通道强度漂移/gold先验漂移）与修复方向见§8.3，与零样本NLI坍缩、conformal不可信并列为本项目三大负结果。

### 6.5 per-claim融合是放大器（-0.152消融）

去掉per-claim融合（`fuse_per_claim=False`，直接聚合原始通道判定）macro-F1从0.7257跌到**0.5735**（-0.152，10项消融中最大单项损失；`eval_paper_matrix_c409df7f_20261027_125551`）。机制：专家通道与残差通道会判定**同一claim文本**——结构专家给出support/refute的已验证判定，通用通道留下"unresolved NIE"；融合规则（refute>support>NIE per claim）保证"无能力判定不得否决已验证判定"。关掉后S类召回从0.333清零（消融行per_class：support P/R/F1=0/0/0）——语义unresolved的NIE把identifier_exact_match等已验证的support全部吞掉。**这是"异构验证器输出协议"层面的设计贡献，不是模型贡献。**

### 6.6 063/074 claim级归因错位：074已被enum_join闭合，063仍是边界

来源：`runs/eval_nli_residual_2996af6b_20261027_013232/015457`（v2 NLI单独评测的claim级flip明细）、`eval_cascade_1e92cdce_20261027_024429`（5专家栈regressed列表：[S1QA-063, S1QA-074]）与 `eval_cascade_1e92cdce_20261027_124941`（7专家栈regressed列表：[S1QA-063]）。

- **S1QA-074（已闭合）**：silver=refute，真矛盾=LOB数据操作的设备集合仅"平板、桌面"而answer声称"桌面/平板/手持"。5专家栈中L2 NLI把refute(p=0.90)骑在效果性claim上、承载真矛盾的claim（设备集合）被判support(p=0.93)——升级复检后实例从refute翻回NIE（regressed）。7专家栈中enum_join在**L1确定性层**以主体值域注册表的同主体封闭集合比对直接锚定设备集合claim判refute——确定性refute短路整个残差派发（C1原则），实例不再进入L2/L3，regressed列表随之从两条缩到一条。**claim归因错位这一失败模式对该类实例有了确定性修复路径：把"集合比对"做成符号层专家，refute天然骑在正确的claim上。**
- **S1QA-063（仍开放）**：silver=refute（文档级设备集合矛盾）。L2判refute；升级复检的L3把两条claim（"平板、平板、手持版三种终端支持不同数据访问方式…"/"初始化数据库…"）均判support（rationale引数据库管理的方式名称字段）→实例翻回NIE（regressed）。这是§6.4-5的silver边界样本：矛盾依据存在于文档级证据观、冻结证据观下GLM判一致。
- **S1QA-068**（silver=refute，真矛盾=产物"数据对象"vs"目标语言代码"）：L2的refute骑在"该功能适用于…构建API或业务逻辑…"(p=0.999)等解释性claim上；124941中068未出现在翻转列表（实例级维持refute），但归因claim错误的模式未在推理侧闭合（对照：10-26 L3参照run把refute正确锚在"系统转换数据结构…转化为对应的目标语言代码"上，`eval_llm_residual_5dd69927_20261026_173434`的corrected明细）。
- **模式**：实例级any-refute聚合让"判定对但理由错"的样本不可见；一旦升级路由让更强判定器重判全部claim，错误归因就显形为实例级回退（074的旧形态、063）或幸运存活（068）。**修复方向（遗留）**：NLI判定需绑定锚定claim（问题主体→功能行绑定，nli_training的question-anchored premise已做训练侧，推理侧claim级锚定未闭合）；评测需引入claim级归因指标（判定∧归因claim正确联合评分，AVeriTeC式）。

### 6.7 评测驱动的专家补全闭环：17真实违例作为诊断基准反哺方法设计

来源：`runs/eval_violations_5d5c92a8_20261027_113100`（5专家栈9/17）→ `120749`（+id_join 12/17）→ `124733`（+enum_join 15/17）；91QA侧 `eval_paper_matrix_0fabaced_20261027_023711`（旧栈）→ `eval_paper_matrix_c409df7f_20261027_125551`（7专家栈）与 `eval_cascade_1e92cdce_20261027_024429` → `124941`。

- **闭环全链**：17条真实违例（04号文档人工深读产出）先作为**诊断基准**跑5专家栈 → 检出52.9%（9/17）→ 失败归因到通道级：identifier类5条中3条未检出，根因是旧identifier通道只做"ID字面出现→support"的单向匹配，**ID字面存在≠answer声称的绑定关系成立**；enumeration类4条中3条未检出，根因是旧enum通道逐成员子串匹配，**成员级命中掩盖集合级冲突** → 两个缺口都指向"符号层跨位置join"（同一主体/同一ID在表与节标题/正文的封闭注册关系比对）→ 补建id_join/enum_join两个L1确定性专家（分别做四项/三项检查，各配独立测试）→ 复测违例集检出**88.2%（15/17，+35.3pp）**，91QA侧B3 macro-F1 0.5628→**0.6381**、cascade refute F1 0.7143→**0.8000**——两个评测集同向受益且91QA无假阳性恶化（B3 refute P 0.750→0.833）。
- **方法论价值**：这是AGENTS调研1（"SRS中实际存在哪些不一致性"）反哺检测方法设计的完整循环——真实数据先行定义检测对象（TERM-07同ID双指/前缀错配/段序颠倒、TERM-03封闭集合冲突/两套分类法、LOGIC-05错字），方法侧再为每类失败模式定制符号层通道，而非先设计通道再找数据。**"失败归因到通道级→定向补专家→双评测集复测"**本身是可复用的研究流程贡献。
- **边界如实报告**：id_join在91QA的消融Δ=+0.000（仅1次claim级触发且被冗余覆盖）、enum_join Δ=-0.026——91QA silver的跨位置join信号稀薄（8条refute里只有2条属于该形态），join专家的必要性主要由17违例集承载（identifier 5/5、enumeration 4/4）。论文表述：两专家是**违例集驱动的定向设计**，91QA上的中性消融与违例集上的大幅检出共同构成证据链（见§3要点、§7）。
- **反方向证据（Wave 6变异注入矩阵，§8.4）**：把同类不一致性以**answer侧单边破坏**的方式注入（证据不动），同通道检出率骤降——identifier真实违例5/5（1.0）vs 注入10/19（0.526）；enumeration真实4/4 vs 注入1/24（0.042）。**符号层的检出能力依赖证据侧冲突登记的存在**：真实违例的矛盾在证据侧多处登记（表间行/节标题/正文），join专家据此锚定发起比对；注入只破坏answer侧时锚点完好但join无从发起，answer侧单边破坏在同通道上近乎失明。**这是方向A上下文聚合的实证论据——检出率的上游是"证据里有没有可join的冲突结构"**，闭环故事至此补上反方向一环。

### 6.8 两个join专家的设计要点：注册表 + 族过滤 + 块隔离

- **id_join的注册表设计**（`id_join_expert.py`）：先把冻结证据的线性化语句聚合成**ID注册表**——ID→[(主体, 位置, 字段)]三元组（语句级绑定"X的项目唯一标识符：ID"+节标题绑定"3.2.1.1.1.4 数据库关闭（PZXQ-…）"两个提取来源）；对answer的每条ID声明执行四项检查：①双登记冲突（同一ID绑定>1个互不包含主体→唯一性被违反，VIO-01同ID双用例共用）；②subject-ID错配（answer声称"X的ID是Y"，同族注册中X登记的是其他ID）；③组件段比对（同主体注册ID与claimed ID逐段比对：段序颠倒VIO-04/缺段VIO-05/家族错配VIO-02/前缀错配VIO-03）；④裸ID匹配（无主体短语时保持旧通道行为）。**族过滤**是关键守卫：冲突比对限定同族ID（前两段相同，如PZXQ-GN/PZXQ-JK），避免把父子层级（能力ID vs 接口ID）的合理前缀关系误判为冲突——这是precision守卫，17违例集假阳性0。
- **enum_join的块隔离行聚合**（`enum_join_expert.py`）：主体值域注册表三个确定性来源（表格字段语句"X的方式名称：平板、桌面"/正文枚举句"X包括A、B、C"/能力表行主体按ID父段聚合）。**行聚合的跨块合并陷阱**：真实04文档中表9的行ID（PZXQ-GN-SQLFW-SJXG）与表3的行共用父段PZXQ-GN-SQLFW——若按父ID全局聚合，两张表的行集会被错并成一个"封闭能力集合"，表3的4行封闭性比对立即失真。实现以**(父ID, 证据块ID)为聚合键做块隔离**（`enum_join_expert.py`分组键），跨表行集永不合并。错字检测锚在封闭值域{桌面,平板,手持}/{开发阶段,运行状态}上，编辑距离1的成员归因为错字（VIO-09"平版"、S1QA-056）。
- 两专家共享同一设计契约：claim_text与被修复的旧通道一致（per-claim融合refute>support>NIE中新专家的refute直接压制旧通道的误support）、完全确定性（无模型调用/无检索/无文件读取）、METHOD名进refute通道归因统计（id_join_L1 5条/enum_join_L1 3条，§7）。

---

## 7. 17真实违例评测（violation_evalset_v1，违例检出与定位）

**评测集**：`data/gjb_438c/localization_gold/violation_evalset_v1.jsonl`（构建：`tools/build_violation_evalset.py`，协议：`docs/srs_project/48_localization_gold_protocol.md`）——04号文档人工深读发现的17条真实违例转化为QA实例，期望verdict全部为refute；7类：identifier 5 / enumeration 4 / traceability 3 / exception_template 2 / document_name 1 / function_coverage 1 / qualification_coverage 1；answer形态：14条断言违例内容+3条断言正确内容的被反驳形态；定位gold预填35个块级refs（评测的localization口径只统计检出实例，§7.2的gold_refs_total=34——16/17终态口径）。**与91QA的区别：这是真实缺陷检测能力的direct证据（real_observed），区别于合成变异与silver边界。**

**评测工具**：`tools/eval_violations.py`（两配置：deterministic=9专家族裸检测0次LLM调用；cascade=级联全系统LLM缓存通道）。

### 7.1 检出演进（专家补全闭环的复测序列，全部deterministic配置）

| 阶段 | run（`runs/`下） | 检出 | 检出率 | identifier | enumeration | traceability | 未检出 |
|---|---|---|---|---|---|---|---|
| 5专家栈 | `eval_violations_5d5c92a8_20261027_113100` | 9/17 | 52.9% | 2/5 | 1/4 | 3/3 | 03,04,05,06,07,09,15,17 |
| +id_join | `eval_violations_5d5c92a8_20261027_120749` | 12/17 | 70.6% | **5/5** | 1/4 | 3/3 | 06,07,09,15,17 |
| +enum_join | `eval_violations_5d5c92a8_20261027_124733` | 15/17 | 88.2% | 5/5 | **4/4** | 3/3 | 15,17 |
| +coverage（终态） | `eval_violations_5d5c92a8_20261027_165400` | **16/17** | **94.1%** | 5/5 | 4/4 | 3/3 | **15** |

（同阶段另有同config_hash的664fe616系列与5d5c92a8的复测run，数字一致；引用取5d5c92a8系列，16/17的复测run=664fe616_20261027_160651。）cascade配置同样**16/17=94.1%**——级联不损失确定性检出（确定性refute短路残差派发）。

### 7.2 终态分类检出与通道归因（165400，9专家栈）

| 违例类别 | n | 检出 | 裁决通道 |
|---|---|---|---|
| identifier（TERM-07） | 5 | 5 | id_join_L1×5（VIO-01/02另有e1/entity冗余） |
| enumeration（TERM-03/LOGIC-05） | 4 | 4 | enum_join_L1×3 + gjb_L1×1（VIO-08两套分类法） |
| traceability（GJB-05） | 3 | 3 | trace_L1×3 |
| exception_template（LOGIC-02） | 2 | 2 | e1_L1×2 |
| function_coverage（GJB-04） | 1 | 1 | gjb_L1×1 |
| qualification_coverage（GJB-01） | 1 | **1** | **coverage_L1×1（Wave 6新增，闭合VIO-17）** |
| document_name（TERM-05） | 1 | 0 | —（误判support，唯一未检出，§7.3） |

辅助口径（165400）：目标命中检出（refute且理由/定位命中该实例target_keywords，区分"检出目标违例"与"检出共享证据中的兄弟违例"）=13/17=**76.5%**；假阳性=0（17条全期望refute，结构性为0；期望非refute上的假阳性在91QA另行测量，B3 refute P=0.833）；定位（块级，系统evidence_refs×预填gold refs）P=**0.80**/R=**0.7059**（gold_refs_hit 24/34；10/16检出实例gold全命中）——定位分母/gold命中数较Wave 5（P 0.8519/R 0.697，23/33）变化源于coverage专家对VIO-17新增3个refute_block_refs（gold命中其中1个，见数字核对记录）。

### 7.3 剩余1条未检出的归因（VIO-17已闭合）

- **VIO-17（qualification_coverage，已闭合）**：表80合格性规定仅6行（覆盖3.2.1~3.2.6），3.3~3.17全部需求无合格性方法——合格性覆盖缺口；answer断言"3.1至3.17全覆盖"，封闭6行的证据在开世界假设下原本无法反证（Wave 5判NIE，§6.4-5的保守性）。Wave 6的coverage_expert以**覆盖join**闭合：合格性表行解析为(需求,章节,方法)覆盖图 + 章节能力清单（标识符表）+ 章节标题存在性三者join——3.3/3.4章节在证据中存在却无合格性行，"全覆盖"声明对封闭覆盖图不可满足→coverage_L1 refute（目标命中、定位gold ev-000404全命中）。**这把"开世界下不可证伪"的缺口转化为"封闭覆盖图上的可判定join"——GJB-01规则库先验（所有需求应有合格性方法）作为封闭性前提进入符号层。**
- **VIO-15（document_name，误判support，唯一剩余）**：3.9.1节把本文档写作"数据同步共享服务"，实际全称"数据统一访问服务"——文档名误写。answer断言误写名，判定系统在冻结证据里找到该误写名字面出现→旧语义判support。检出需要**文档元数据/自引用名称通道**（本文档自称与全文档表caption/引用句的一致性join），现有9专家无覆盖；属"文档级自反一致性"，与证据块级比对正交——**可选项，算法侧不阻塞**（§11）。

---

## 8. Wave 6：设计补全与稳健性诊断（2026-10-27晚）

**范围**：把设计§6.3的L1专家族表补至全量（numeric_z3承载"区间算术+数值聚合"两行、coverage承载"覆盖完备"行），完成设计§6.5的变异注入评测（robustness漏检率矩阵）与设计§6.4路由器的学习半边（C4）——后两者产出的是负结果/诊断性结果，如实报告。全部数字取自：`runs/router_train_7a90549c_20261027_165644`、`runs/eval_router_2b76c358_20261027_170640`、`runs/eval_mutation_detection_750b7b7d_20261027_165008`、`runs/eval_violations_5d5c92a8_20261027_165400`。

### 8.1 Z3数值专家（numeric_z3_expert.py：设计§6.3"区间算术+数值聚合"两行）

600行+21测试（`tests/test_numeric_z3_expert.py`）。作为独立专家通道加入`_expert_channels`（不替换`qa_module._verify_numeric`原通道——原通道继续负责answer算子式声明与同单位族快速路径，per-claim融合自动仲裁两通道对同一声明的分歧）。三项能力增量：

1. **量纲换算**：srs_kb单位族（time/storage/frequency/data_rate/…）+中文别名（毫秒/秒/分钟/小时/字节/天/日）+count族（条/个/次/种/路/项/类/台），单位不一致时换算到族基准后比较；未知单位退化为同名族（仅同串可比、绝不跨族猜测）；temperature族为仿射换算（乘法因子表不可表达），显式跳过。
2. **区间三态Z3判定**（PARAM-03/06/07）：answer约束C_a与同subject证据约束E（合取）——E∧C_a UNSAT→refute；C_a∧¬E UNSAT→support（answer解集⊆证据解集）；其余SAT→NIE（部分重叠不可判定）；E自身UNSAT→NIE（context内部数值矛盾，不仲裁answer）。
3. **跨参数聚合检查**（PARAM-01/05，Logic-LM式程序合成）：answer含聚合声明（subject含"总/之和/合计/总计/总共"）而证据有同单位族≥2个互异subject的分量约束时，Z3构造Σ(分量)聚合约束与分量约束联查——UNSAT→refute（unsat core指明参与矛盾的分量）；分量保证聚合成立→support。91条QA中无此形态，能力由合成测试证明（对16份文档的能力声明）。

- **输出协议防scope laundering**（Know Your Limits教训，设计§6.3的L1输出协议要求）：每条refute/support附**完整SMT-LIB程序+unsat core**（指明参与矛盾的事实/分量）——判定可独立复核，solver日志强制输出；Z3求解timeout=500ms（防坏约束挂死），unknown/异常→NIE+诊断（不静默）。
- **证据构成发现（数字为复核脚本重derive）**：04号全文档证据（content_list 360块+图证据64条，经`evidence_compiler`加载）线性化后数值事实**92条**；91QA冻结证据（574个去重块）数值事实**0条**；17违例集证据（90个去重块）**22条**（全部来自数据表min/max行）。**scene1 QA的冻结证据不含数值声明——PARAM类检测在该评测集上结构性无对象**：numeric_z3在91QA零触发是必然而非巧合（§2零回归核验的claim_methods无`numeric_z3_expert`条目佐证），且与§8.4变异矩阵PARAM族注入0%检出同根源（证据侧无数值事实可join，answer侧数值扰动无从反证——"数值证据缺失型漏检"，修复前置=参数约束抽取+跨块聚合，即方向A）。

### 8.2 覆盖完备专家（coverage_expert.py：设计§6.3"覆盖完备"行）

693行+32测试（`tests/test_coverage_expert.py`）。`gjb_presence_expert`只查表/条款的**存在性**（表80在不在），本专家是它的逐章覆盖深化，三段流水线：

1. **覆盖关系构建**（纯确定性符号解析）：表头含「合格性」的表格按列对齐解析为(需求名称, 章节号, 合格性方法)行；方法列为「无/-」的行只登记章节事实（已知需求无方法=覆盖缺口），不计入已覆盖行；章节能力清单=表头含「标识符+需求描述」的能力表(Use case名称, 项目唯一标识符)清单。
2. **章节清单join**：合格性覆盖图×章节能力清单×章节标题存在性三方join。
3. **answer覆盖声明判定**（method=coverage_join，CHECK_ITEMS=GJB-01/04/06）：全覆盖声明（"3.1至3.17全部需求均规定了合格性方法"）vs 封闭覆盖图——声称区间内存在无合格性行的章节→refute；GJB-04/06条款覆盖声明同协议（条款缺失时answer声称全覆盖→refute）。

- **VIO-17闭合**：表80合格性6行（3.2.1~3.2.6）vs answer声称3.1-3.17全覆盖，证据中3.3/3.4章节标题存在却无合格性行→coverage_join refute（目标命中、定位gold ev-000404全命中，refute_block_refs含ev-000262/280/404三个锚点）。17违例检出**15/17→16/17（94.1%）**，91QA零回归（§2零回归核验；§7）。
- 设计契约与两join专家一致：完全确定性（无模型调用/无检索）、claim_text与旧通道同构（per-claim融合兼容）、METHOD=coverage_join进通道归因统计。

### 8.3 学习路由器（router.py + tools/build_router_dataset.py + tools/eval_router.py，23测试）：负结果

**任务**（设计§6.4组件C学习半边，FrugalGPT/RouteLLM的"学习路由"推广到异构验证器）：把固定级联（L2判全部残差+refute候选升级L3）换成**post-L1单次实例级路由**——accept_l1（跳过残差通道，成本0）/accept_l2（跑L2、信任其判定、不升级，成本1）/call_l2（跑L2+固定升级策略）/escalate_l3（跳过L2直接L3，成本10/批）。oracle标签=最小成本正确路由（全错→accept_l2）；20维特征严格取决策点状态（L1判定/expert命中数/残差计数/claim-kind混合/检测项族/问题答案形状/证据统计）——训练与服务同一特征分布；NLI概率只作分析列、不作特征（决策先于L2）。

**训练**：EGT NLI dev split的422实例中122条无残差决策点被排除，得300特征行；gradient_boosting（seed=42）5折CV macro-F1 **0.456**/acc 0.6933，优于logistic（0.3326）。**防泄漏体制**（任务效度核心）：91QA实例零进训练（qa_instance_ids_in_train=0）；EGT训练池中与91QA问题文本重叠的10行剔除（train_split=egt_nli_dev_split_minus_qa_question_overlap）；EGT样本取NLI dev split——被探测的L2是未见过训练集的诚实checkpoint。

**结果**（`router_train_7a90549c_20261027_165644` + `eval_router_2b76c358_20261027_170640`，91QA vs silver，checkpoint=egt_finetuned_v2，gate=0.7）：

| 配置 | macro-F1 | refute P/R | LLM调用 | 路由一致率 |
|---|---|---|---|---|
| 固定级联（fixed_cascade） | 0.7185 | .857/.750 | **15** | —（无学习路由） |
| 学习路由（learned_router） | 0.7257 | .700/.875 | 73 | **0.0875**（7/80） |
| **oracle上限（分析用）** | **0.7867** | **.889/1.0** | **2** | 1.0（定义） |

- **held-out路由一致率0.0875**：EGT内样本路由一致率0.8233、仿真acc 0.7867@5次调用（`train_routing_in_sample`），一出EGT即崩——80条可路由QA中70条被路由escalate_l3，oracle是73条accept_l1。learned_router端到端0.7257@73次调用：quality追平l3_llm（0.7257@83次）但调用成本4.9倍于固定级联，且refute精度(0.700)低于固定级联(0.857)。
- **oracle上限0.7867@2次调用**（refute P 0.8889/R 1.0/F1 0.9412，acc 0.9451）：比固定级联+0.068 macro-F1且-13次调用——**路由信息存在但EGT监督学不出**。pareto扫描（α=0~8）：α≥5才降到≤14次调用但macro-F1跌至0.62~0.6381（退化回baseline）。
- **三重归因**（数字全部取自router_train run）：
  1. **特征分布外推**：EGT单claim短问句（n_claims均值**1.02**、question_len恒**10**、answer_len均值**24.06**）vs QA多claim长问句（**5.01**/**20.64**/**218.34**）——训练特征空间是QA特征空间的一个角落，梯度提升外推失败。
  2. **通道强度漂移**：L2在EGT dev的路由探测acc **0.9056**（180条）vs 91QA上L2 refute精度**0.3684**（19个预测refute里12个伪）——"L2能不能信"在两个分布上答案相反，而accept_l2是EGT oracle的主类（174/300）。
  3. **gold先验漂移**：EGT oracle均衡（accept_l2 174/accept_l1 120/escalate 6）vs QA oracle 91% accept_l1（73/80）——silver 85% NIE先验下，最小成本正确路由多为"什么都不做"，学习器把EGT的"L2优先"先验带进了QA。
- **结论**：**严格防泄漏体制下，学习路由不值得部署**（learned macro-F1≥0.70达标但调用73≫15、质量-成本全面劣于固定级联与oracle）。修复方向（已记录，不阻塞论文）：①多claim合成探测——EGT文法补多claim长问句形态（v3叙事路径已含多claim样本的种子扩展）；②OOD鲁棒回退——路由置信度低于阈值时回退固定级联策略。论文表述：与零样本NLI坍缩（§6.4-1）、conformal不可信（§6.4-3）并列的第三大负结果，共同刻画"什么在当前数据规模学不出"。

### 8.4 变异注入漏检率矩阵（tools/build_mutation_injection_eval.py + tools/eval_mutation_detection.py，7测试）：稳健性诊断

**协议**（设计§6.5 robustness行）：48个注册算子（41个refute语义+7个support对照）×91条冻结QA的answer→**394条注入**实例（`data/gjb_438c/mutation_injection_evalset_v1.jsonl`；两级算子执行：strict=算子库证明门直接发gold、adaptive=answer侧受控扰动且期望refute来自注入协议）；被测系统=纯确定性符号层（`QAConsistencyModule(use_experts=True)`，9专家，0次LLM调用——变异注入测符号层能力，不跑L2/L3）；期望verdict=refute，判support/NIE均计漏检。

**总检出率10.4%**（41/394）；漏检353条中NIE 344条、误support 9条。族级矩阵：

| 族 | 注入n | 检出 | 检出率 | 主检出通道 |
|---|---|---|---|---|
| GJB | 20 | 5 | **25.0%** | gjb_L1 |
| TERM | 67 | 13 | **19.4%** | entity_L0 / id_join_L1 |
| BASE | 64 | 6 | 9.4% | entity_L0 / id_join_L1 |
| STRUCT | 148 | 12 | 8.1% | enum_join_L1 / sequence_L1 |
| LOGIC | 91 | 5 | 5.5% | enum_join_L1 / e1_L1 |
| PARAM | 4 | 0 | **0.0%** | —（证据无数值事实，§8.1） |
| **总计** | **394** | **41** | **10.4%** | — |

**核心发现（论文级）：真实违例=证据侧双登记；注入=answer侧单边破坏，同通道近乎失明**——同通道对照（run的`violation_cross_reference`，真实列=165400口径）：

| 类别 | 真实违例检出 | 同形态注入检出 | 差距 |
|---|---|---|---|
| identifier | **5/5（1.0）** | 10/19（**0.526**） | -47.4pp |
| enumeration | **4/4（1.0）** | 1/24（**0.042**） | -95.8pp |
| exception_template | 2/2（1.0） | 5/91（0.055） | -94.5pp |
| traceability | 3/3（1.0） | 0/0（无适用算子） | — |

机制：真实违例的矛盾在**证据侧多处登记**（表间行/节标题/正文互相冲突），join专家据此锚定发起比对；注入只破坏answer侧、证据侧完好——answer侧单边破坏时，符号层join通道的锚点仍在但比对对象（answer声明）与证据的冲突登记不再对应，同通道检出率骤降（identifier 0.526）或近乎归零（enumeration 0.042）。**符号层检出能力依赖证据侧冲突登记的存在——这是方向A上下文聚合的实证论据**：检出率的上游是"证据里有没有可join的冲突结构"（§6.7闭环的反方向一环）；answer侧单边破坏的语义级冲突需要L2/L3（与级联架构的残差设计一致）。

**漏检结构**（`miss_reason_stats`）：NIE漏检344条的主要裁决method为semantic_unresolved（claim级607次）/conservative_unresolved（148次）——开放scope证据下步骤重排/枚举删元不可证伪（需closed-scope证据或计数型枚举声明检测）；误support 9条主要由identifier_exact_match（claim级19次）造成——ID/术语字面命中掩盖绑定关系破坏（与§6.7的旧identifier通道失败模式同根源）。run内`capability_gaps`结论：LOGIC族缺语义级处置动作比对（需L2/L3）；STRUCT族枚举删元开放scope不可证伪；BASE/PARAM族数值证据缺失型漏检（修复前置=方向A的参数约束抽取+跨块聚合）。

runs：`eval_mutation_detection_750b7b7d_20261027_165008`（终态；同日3次更早run 161528/164306/164708为开发迭代，数字以165008为准）。

---

## 9. 文件与runs清单

**runs统一协议**：`tools/run_utils.py`（config+git_sha+result，不覆盖写）。**全部runs（含Wave 6/7新run）的git_sha=ff0d4950（config.json字段，最后一次commit）——CascadeVerify v2的Wave 5+6+7全部新代码仍在工作区未提交，为最大复现性风险项（见§11）。**

### 9.1 实现模块（algorithms/consistency/）

| 模块 | 职责 | 测试 |
|---|---|---|
| `deq_pipeline.py` | DEQ证据管线（E0范围门/E1检测项感知评分/E2语句对齐） | test_deq_pipeline.py |
| `entity_detector.py` | L0实体冲突（TERM-05/07/08） | test_entity_detector.py |
| `e1_expert.py` | E1异常流模板专家（LOGIC-02） | test_e1_expert.py |
| `sequence_expert.py` | 序列对齐专家（LOGIC-03） | test_sequence_expert.py |
| `trace_expert.py` | 追溯join专家（GJB-05） | test_trace_expert.py |
| `gjb_presence_expert.py` | GJB有无专家（GJB-01~11封闭清单） | test_gjb_presence_expert.py |
| `id_join_expert.py` | ID→主体注册表join专家（TERM-07跨位置ID四项检查，§6.8） | test_id_join_expert.py |
| `enum_join_expert.py` | 枚举主体值域join专家（TERM-03封闭集合三项检查，§6.8） | test_enum_join_expert.py |
| `numeric_z3_expert.py` | Z3数值约束专家（PARAM-01/03/05/06/07；量纲换算+区间三态+跨参数聚合，SMT-LIB+unsat core输出协议，§8.1） | test_numeric_z3_expert.py（21个） |
| `coverage_expert.py` | 覆盖完备专家（GJB-01/04/06；合格性逐章覆盖+条款覆盖，§8.2） | test_coverage_expert.py（32个） |
| `router.py` | 学习路由器（post-L1特征+四路由决策+oracle标注，§8.3负结果） | test_router.py（23个） |
| `evidence_compiler.py` | 表格→类型化schema+聚焦视图（Chain-of-Table符号子集） | test_evidence_compiler.py |
| `evidence_statements.py` | 表格HTML→字段语句线性化（位置保持+表头签名派发；premise bug修复处） | test_evidence_statements.py |
| `egt_synthesis.py` | EGT三态合成（v1近拷贝/v2语句/v3叙事，3248行） | test_egt_synthesis.py |
| `nli_training.py` | 合成数据→NLI训练对（premise管线训练/推理共享） | test_qa_consistency_module.py覆盖 |
| `nli_residual.py` | L2 NLI残差通道（gate守卫） | test_nli_residual.py |
| `llm_residual.py` | L3 LLM残差通道（聚焦prompt+行分组语句选择） | test_llm_residual.py |
| `qa_module.py` | 统一校验器（9专家通道编排+per-claim融合+聚合+级联升级） | test_qa_consistency_module.py |
| 其余既有 | `baselines.py`/`nli_local.py`/`qa_router.py`/`answer_structure.py`/7个变异算子族 | 各自测试 |

### 9.2 评测与构建工具（tools/）

`build_egt_dataset.py`（EGT合成）、`train_residual_nli.py`（NLI微调，本地GPU）、`eval_nli_residual.py`（L2评测+gate扫描）、`eval_llm_residual.py`（L3评测）、`eval_paper_matrix.py`（S6论文矩阵：B0-B5+10消融+4对bootstrap）、`eval_cascade.py`（S5级联路由五配置+conformal两档）、`build_violation_evalset.py`（17违例→QA转化集构建）、`eval_violations.py`（17违例检出/定位/通道归因评测）、`build_router_dataset.py`（Wave 6：路由训练集全通道探测+防泄漏训练）、`eval_router.py`（Wave 6：学习路由五配置+oracle上限+pareto扫描）、`build_mutation_injection_eval.py`（Wave 6：48算子×91QA→394条注入集构建）、`eval_mutation_detection.py`（Wave 6：变异漏检率矩阵评测）、`print_cascade_summary.py`（结果速览）。

### 9.3 模型与数据资产

- `models/nli/egt_finetuned`（v1模型，训练run ade325ae_20261026_195906）
- `models/nli/egt_finetuned_v2`（v2模型定稿，训练run acfead4b_20261027_013647；同日变体24ea638f_005544[3ep, dev 0.9674]、5e6a315f_011013[5ep, dev 0.9675]、acfead4b_003550[4ep, dev 0.9696]）
- EGT数据集jsonl：各build_egt_dataset run目录内`egt_dataset.jsonl`（v3=4500行）
- 91QA冻结集+silver标签：`data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl`、`runs/review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl`
- **17真实违例评测集**：`data/gjb_438c/localization_gold/violation_evalset_v1.jsonl`（17条refute期望实例+7类分布+35个定位gold refs+target_keywords，测试tests/test_violation_evalset.py；上游违例清单=`knowledge/consistency_taxonomy_v3.json` doc04_violations，协议=48号文档）
- **变异注入评测集（Wave 6）**：`data/gjb_438c/mutation_injection_evalset_v1.jsonl`（394条注入实例+算子族/模式/变异rationale元数据，测试tests/test_mutation_injection.py 7个）
- **学习路由器资产（Wave 6）**：`router_train_7a90549c_20261027_165644/`内`router.joblib`（训练产物）+`router_dataset.jsonl`（513行探测数据：EGT 422+QA 91）+4个scripted_router joblib（逐路由探测桩）

### 9.4 关键runs目录（全部已Test-Path验证存在）

| run目录（data/gjb_438c/runs/下） | 内容 |
|---|---|
| `eval_paper_matrix_c409df7f_20261027_125551` | §2主表B0-B5、§3消融(10项)、§4 bootstrap(4对)（7专家栈定稿run） |
| `eval_cascade_1e92cdce_20261027_124941` | §2 L2/cascade/conformal行、§6.3、§6.4-3、§6.6、L3漂移声明（7专家栈定稿run） |
| `eval_violations_5d5c92a8_20261027_113100` | §7.1演进表第1行（5专家栈9/17） |
| `eval_violations_5d5c92a8_20261027_120749` | §7.1演进表第2行（+id_join 12/17） |
| `eval_violations_5d5c92a8_20261027_124733` | §7.1演进表第3行（+enum_join 15/17） |
| `eval_violations_5d5c92a8_20261027_165400` | §7.1演进表第4行/§7.2终态/§8.2（+coverage **16/17=94.1%**，Wave 6定稿run；复测664fe616_20261027_160651一致） |
| `router_train_7a90549c_20261027_165644` | §8.3路由训练+held-out分析（EGT 422/300特征行、防泄漏体制、三重归因数字） |
| `eval_router_2b76c358_20261027_170640` | §8.3五配置+oracle上限+pareto扫描；§2零回归核验（9专家栈四配置与Wave 5定稿一致） |
| `eval_mutation_detection_750b7b7d_20261027_165008` | §8.4变异注入漏检率矩阵（394注入/41检出/双登记对照；开发迭代161528/164306/164708） |
| `eval_paper_matrix_0fabaced_20261027_023711` | 5专家栈论文矩阵（B3=0.5628，§6.7闭环对照的历史基线） |
| `eval_cascade_1e92cdce_20261027_024429` | 5专家栈cascade定稿run（regressed=[063,074]的旧形态对照，§6.6/§6.7） |
| `eval_cascade_1e92cdce_20261027_022407/023405/023644` | 同日更早三次cascade复现（conformal kept档P=0.2857×3） |
| `eval_llm_residual_5dd69927_20261026_173434` | L3历史参照（macro-F1 0.7799/refute P=1.0/R=0.875，旧线性化） |
| `build_egt_dataset_3a52cd3f_20261026_154036` | EGT v1（117近拷贝） |
| `build_egt_dataset_2f65089e_20261026_163247` | EGT v2中间版（04单文档714） |
| `build_egt_dataset_721c8665_20261026_165547` | EGT v2（16文档3000，v1模型训练数据） |
| `build_egt_dataset_8a8716bb_20261027_003528` | EGT v3叙事（4500，v2模型训练数据+R样本sound性数字） |
| `train_residual_nli_ade325ae_20261026_195906` | v1模型训练（dev 0.9648） |
| `train_residual_nli_acfead4b_20261027_013647` | v2模型定稿训练（dev 0.9722） |
| `eval_nli_residual_4971ceba_20261026_201247` | v1模型91QA真实（0.4963/refute R 0.375；同config更早两次0.4553/0.4866） |
| `eval_nli_residual_2996af6b_20261026_212915…20261027_015457`（12个） | v2模型91QA同日12次评测（macro-F1 0.4325–0.5298，fp16波动） |
| `build_dev_test_split.py`产物 | **dev_test_split_v1.json**（Wave 7：29主题簇，dev45/test46，seed=42，同主题零跨侧） |
| `calibrate_on_dev_a069227d_20261027_185110` | §10.1 dev扫参60配置（仅3个macro-F1值）+dev_tuned_config_v1.json冻结指针 |
| `eval_test_honest_6740ed5c_20261027_185819` | §10.1 修复前test诚实数字（0.704 vs legacy 0.7185，乐观偏差+0.0145） |
| `eval_test_honest_6740ed5c_20261027_195753` | §10.1 修复后test诚实数字（**0.8286/acc 0.9348**；optimistic_bias口径警告） |
| `eval_qa_module_silver_f119425e_20261027_190326/195515` | §10.2 修复前后全91确定性（0.9011/0.6381→0.9121/0.7212；194154为复测） |
| `eval_qa_dev_split_6d4e96bb_20261027_195532` | §10.2 修复后dev侧B4（0.8875） |
| `eval_violations_5d5c92a8_20261027_195407/195501` | §10.2 P1修复后违例回归（16/17零回退+定位23/34；664fe616_194204同数字） |
| `eval_crossdoc_27e8ce32_20261027_190259/195859` | §10.3 跨文档泛化（修复前后逐位一致：det 0.1524/cascade 0.5309） |
| `build_crossdoc_evalset_1a7c8719_20261027_190350` | §10.3 06号30条sound评测集构建（crossdoc06_evalset_v1.jsonl） |

---

## 10. Wave 7：审计响应与诚实评测（可信度审计→P0/P1修复→诚实数字，2026-10-27晚）

**背景**：Wave 6收口后对本文档全部声明做了一轮可信度审计，八项审计发现与响应对照见§10.4。三项P0/P1响应在本轮落地：①持久dev/test切分+test侧诚实评测（修dev-on-test）；②P1三项确定性bug修复（修support召回2/6）；③06号跨文档sound评测集（补跨文档零验证）。本节全部数字取自：`runs/eval_test_honest_6740ed5c_20261027_185819`（修复前test）、`runs/eval_test_honest_6740ed5c_20261027_195753`（修复后test）、`runs/calibrate_on_dev_a069227d_20261027_185110`（dev扫参60配置）、`runs/eval_qa_module_silver_f119425e_20261027_190326/195515`（修复前后全91确定性）、`runs/eval_qa_dev_split_6d4e96bb_20261027_195532`（修复后dev侧B4）、`runs/eval_violations_5d5c92a8_20261027_195407/195501`（违例回归）、`runs/eval_crossdoc_27e8ce32_20261027_190259/195859`（跨文档修复前后）。

### 10.1 持久切分与诚实评测（P0-1：dev-on-test修复）

**切分**：`data/gjb_438c/qa_frozen/dev_test_split_v1.json`（`tools/build_dev_test_split.py`，seed=42）：91条QA按**29个功能主题簇整簇原子分配**——dev=45（S=3/R=4/N=38）、test=46（S=3/R=4/N=39），**同主题零跨侧**（每个簇只落一侧，防主题泄漏）；silver类型如实登记为`glm53_silver_not_gold`。

**扫参协议**（`tools/calibrate_on_dev.py`，只在dev上）：3参数网格 nli_gate(5)×cascade_keep_confidence(3)×llm_refute_gate(4)=**60配置**，全部L3判定走llm_json缓存；选优=max dev macro-F1→并列选LLM调用少→并列选网格序；冻结指针`dev_tuned_config_v1.json`。**阈值空间在dev上被压平：60配置只出现3个macro-F1值**（0.6626×40 / 0.6678×5 / 0.7353×15，`calibrate_on_dev_a069227d_20261027_185110`）——级联对这几个阈值的敏感度极低（多数配置共享同一判定路径），可调自由度名存实亡。最优配置nli_gate=0.9/keep=None/refute_gate=0.6（dev macro-F1 0.7353@4次调用）。

**test侧协议**（`tools/eval_test_honest.py`）：test split只在test评测时整批运行一次（current-default=legacy同配置 + dev-tuned两行），不参与任何扫参/选型；legacy全91数字直接读既有run不重跑。

| 口径 | macro-F1 | acc | R: P/R/F1 | S: P/R/F1 | LLM调用 |
|---|---|---|---|---|---|
| legacy全91自评（fixed_cascade，`eval_router_2b76c358_20261027_170640`） | 0.7185 | 0.9121 | .857/.750/.800 | .500/.333/.400 | 15 |
| test诚实（修复前，185819，current-default） | 0.704 | 0.913 | .750/.750/.750 | .500/.333/.400 | 10(0/10) |
| **test诚实（修复后，195753，current-default）** | **0.8286** | **0.9348** | **1.0/.750/.8571** | .667/.667/.667 | 10(0/10) |
| test（dev-tuned，195753） | 0.8286 | 0.9348 | 1.0/.750/.8571 | .667/.667/.667 | 7(0/7) |

- **乐观偏差仅+0.0145（2.0%）**：legacy全91自评0.7185 vs 修复前test同配置0.704（185819的`optimistic_bias`字段：macro_f1=+0.0145、refute_f1=+0.05）——**dev-on-test的历史隐患被量化为很小**：全91数字基本可在held-out兑现。机制：91QA上阈值空间本身被压平（60配置仅3个F1值），可供过拟合的自由度有限。dev调参在test零分歧（dev_tuned−current_default：macro-F1与refute F1差均为0.0，两配置test判定逐条一致，仅LLM调用10→7）。
- **修复后test=0.8286/acc 0.9348**（refute P=1.0/F1=0.8571、NIE F1=0.962、S R=0.667）：§10.2的P1三项bug修复传导到test侧——S1QA-053从误refute翻正为support（id_join精确绑定+TERM-07护栏），refute精度0.75→1.0（误refute消除）。**S1QA-066在test侧（cascade路径）仍NIE**：序列碎片claim已被适用性门消除，但cascade先走L2、L2判NIE且无refute候选不升级L3；B4直连L3配置下066为support（§10.2，support召回5/6即B4口径）——cascade与B4在support召回上的这一分歧如实记录。
- **口径警告（optimistic_bias字段的-0.1101）**：修复后run（195753）的`optimistic_bias.macro_f1=-0.1101`是"**legacy（旧代码全91自评）−test（新代码held-out）**"的混合口径——旧代码0.7185与新代码0.8286的差值同时包含held-out效应与代码修复效应，**负号来自"代码改进大于乐观偏差"，不是"held-out比自评高15.3%"**。纯乐观偏差读修复前run（185819）的+0.0145。

### 10.2 P1三项确定性修复（support召回2/6→5/6）

修复内容（失败分析→定位→代码，逐claim剖析与机制见50号文档§2/§6/§7）：

1. **融合键剥离编号前缀**（`qa_module.py`的`_FUSION_PREFIX_RE`，c-fix）：per-claim融合的分组key剥离"N．/N./N、"前缀——"1．X"与已验证的"X"claim同组合并，refute>support>NIE取融合胜者；claim_text本身不动，只改分组。
2. **序列专家适用性门**（`sequence_expert.py`，c-fix）：序列通道只处理"事件时序"形态——问题须含流程/步骤/时序指示词；编号项构成异常类型枚举（失败/错误/异常关键词占比≥0.5）或带标签长并列项（无时序连接词且平均长度>40字符）时整实例跳过——消除"1．"前缀碎片claim与"凭空步骤"NIE对L0/L3已验证内容的否决。
3. **id_join精确绑定+TERM-07护栏**（`id_join_expert.py`的`_binding_candidates`精确优先分层 + `entity_detector.py`的`_check_interface_ids`全证据命中优先护栏，a-fix）：claimed(主体,ID)在注册表精确命中时在精确层仲裁（VIO-02~05全部经由精确层检出不变）；包含回退方向固定为claimed⊂registered（answer用注册条目的简写/上位形态），**父功能注册不仲裁子功能声称的ID**（修053的父子混淆误refute）；TERM-07的ID在冻结证据全文逐字出现→support（ID存在性成立，主体归属交id_join仲裁）。

**效果**（修复前→修复后，runs协议落盘）：

- **support召回2/6→5/6**（B4配置=experts+L3残差）：053误refute→support（id_join与TERM-07双误refute消除，残差派发恢复）；066/069 NIE→support（前缀碎片claim不再否决L3已验证内容）；**077留P2**（L3证据投递缺口：能力表行ev-000035/ev-000030未进30条语句选择，`llm_residual.py`的`_select_statements`排序只按scope字面命中）。
- 全91确定性（`eval_qa_module_silver_f119425e_20261027_190326`→`eval_qa_module_silver_f119425e_20261027_195515`）：acc 0.9011→**0.9121**、macro-F1 0.6381→**0.7212**（+0.0831；S F1 0.25→0.40与误refute消除的联合效应；193733/194108为修复落地过程中的中间迭代，定稿取195515，同配置复测194154一致）。
- dev侧B4（`eval_qa_dev_split_6d4e96bb_20261027_195532`，冻结dev 45条）：acc 0.9556、macro-F1 **0.8875**（S P=1.0/R=0.667；R P=0.8/R=1.0）。
- **违例集16/17零回退**（`eval_violations_5d5c92a8_20261027_195407/195501`：deterministic与cascade均16/17、逐实例refute通道归因与Wave 6终态165400完全一致）：id_join精确绑定没有破坏04号违例检出。**定位侧小代价如实报告**：gold命中24/34→23/34（P 0.80→0.7931、R 0.7059→0.6765）——VIO-03（前缀错配）的第二个冲突锚点ref（ev-000271）不再输出（精确绑定收窄了冲突锚登记面），检出/target_hit/通道归因零变化。
- **诚实声明**：修复的失败诊断（50号文档§2）用的是**全91失败分析（含test侧实例053/066）**，c-fix的oracle探针验证零副作用（全corpus恰2条翻转、其余89条零变化）；**test侧数字（195753）的"纯净度"有此折扣**——诊断阶段看过test侧失败实例，test评测发生在修复定稿之后且只跑一次，如实注明。

### 10.3 跨文档泛化（P1：06号sound评测集与gap量化）

**评测集**：`data/gjb_438c/qa_frozen/crossdoc06_evalset_v1.jsonl`（`tools/build_crossdoc_evalset.py`，构建run `build_crossdoc_evalset_1a7c8719_20261027_190350`）：06号（**运行支撑服务**SRS，476块=315文本+116表+33图，与04号同为结构完整文档）**30条，构造性sound标签S/R/N各10**——每条附`label_proof`（如"构造性S: b253#cap2行字面『应用界面集成的方式名称：桌面、平板、手持』在冻结证据中"），**不依赖LLM silver，标签由构造协议证明**。6族叙事事实（capability_device 9/trace_binding 6/capability_state 6/interface_flow 5/param_value 3/usecase_e1 1）。**04号参照**：deterministic=B3 0.6381、cascade=0.7185（`eval_cascade_1e92cdce_20261027_124941`，silver口径）。

| 配置 | 04号（91QA, silver） | 06号（30条, sound） | Δ macro-F1 |
|---|---|---|---|
| deterministic（9专家栈） | 0.6381 | **0.1524**（acc 0.2667） | **-0.4857** |
| cascade（L2→L3升级） | 0.7185 | **0.5309**（acc 0.5333） | **-0.1876** |

（`eval_crossdoc_27e8ce32_20261027_195859`；P1修复前（190259）与修复后（195859）两run数字**逐位一致——P1三项修复对06号零改善**：三项修的都是04号特异文法的bug。）

**失效归因**（run的attribution/misclassified明细，四条）：

1. **answer文法不迁移**：04号91QA的answer是Alpaca源文法（引号标识符+"包括"式枚举清单），06号是自然复述式（"应用界面集成功能支持在桌面、平板、手持设备上使用。也就是说…"）——E1/entity/enum/序列等正则通道对自然复述几乎全部失声，deterministic的support与refute召回均**0/10**（22条误判中18条判NIE）。
2. **numeric_z3跨行误join伪refute**：C06QA-008（gold=support）被判refute，decisive=`numeric_z3_expert`——answer的"最大连接数的最大值 为200"与冻结证据中其他参数行跨行误join出数值冲突；该伪refute在cascade下经L1短路原样保留。
3. **identifier在场即support的L1信任假设跨文档不成立**：C06QA-016/017（gold=refute，ID在场但绑定错误）被判support，decisive=`identifier_exact_match`+`l0_entity_detector:TERM-07`——04号上"ID字面在场→标识真实"的信任在06号的构造性refute标签下成为误判。
4. **cascade恢复叙事S/R但L1终态误判保留**：cascade把support召回0→0.4、refute召回0→0.5（L2/L3残差对自然复述有效），但②③两类L1终态误判经C1短路原则原样保留（cascade的14条误判中，numeric_z3伪refute与identifier误support各就各位）。

**结论**：跨文档泛化缺口是**正则文法层的结构性问题**（对04号answer文法的过拟合），不是可经bug修复消除的缺陷——P1修复（04特异性bug）对06号零改善即是直接证据。**升级路线=语义匹配（P2）**：跨文法的成员/绑定比对交BGE/NLI语义层承担，06号评测集作为泛化持续回归探针保留（后续每次栈改动复跑）。

### 10.4 审计-响应对照表（本轮审计收口）

| 审计发现 | 响应 | 状态 |
|---|---|---|
| silver非gold（主表数字本质vs-silver，§6.4-5边界不自洽） | 标注工作台：`tools/build_annotation_sheet.py`/`collect_gold_annotation.py`/`finalize_gold.py`三工具（108实例/525 claim预填→TSV表单→回收校验→双人κ→gold_v1导出；速查手册`gold_annotation_sheet_v1.md`+48号协议） | **待人工标注（估6-9小时）** |
| dev-on-test（legacy阈值在91条上看着调） | 冻结切分+dev扫参+test一次评测（§10.1） | 偏差2%已量化；修复后test=0.8286 |
| 少数类统计功效（n=91且refute仅8条） | bootstrap CI已有（§4）；切分后每侧更小（dev R=4/test R=4）——功效进一步受限，注明局限 | 已记录（§4措辞维持"not individually significant"） |
| 违例循环性（17违例既驱动专家设计又当评测集） | 变异注入矩阵（§8.4，总检出10.4%）作反例对照：同通道对answer侧单边破坏近乎失明 | 已有（§8.4证据侧双登记发现） |
| support召回0.33（2/6） | P1三项修复（§10.2）→5/6 | **已修**（077留P2证据投递） |
| 跨文档零验证（全部结论仅在04号） | 06号30条sound标签评测集+gap量化（§10.3） | 已建（结构性缺口公开） |
| L3缓存漂移/fp16波动（复现性风险） | §2漂移声明+§6.4-4负结果（同日12次评测极差0.4325–0.5298） | 已记录（§2/§6.4） |
| 启发式清单（E1/实体/序列等正则栈脆弱性） | 06号gap实证（§10.3归因①③：正则通道对自然复述失声、identifier在场假设失效） | **已实证**；升级路线=语义匹配（P2） |

---

## 11. 遗留项（Wave 7收口：审计响应后的清单）

**算法侧完成声明（Wave 7收口）**：对照方法设计文档§6的组件清单，**算法/实现/评测侧全部完成**（三个负结果也是"完成"——完成的是诚实的评测与归因）；Wave 7补齐了评测效度侧（持久切分/test诚实数字/跨文档泛化探针）：

| 设计§6组件 | 实现 | 评测证据 |
|---|---|---|
| §6.2 组件A：EGT合成管线（三态构造性gold） | `egt_synthesis.py`（v1/v2/v3三文法） | §5：v3 4500样本、R样本sound性0.932、叙事文法定召回（§6.1） |
| §6.3 组件B：L1专家族表9行 | 9模块：id_join/enum_join/numeric_z3/e1/sequence/trace/coverage/gjb+L0 entity | §7.2：17违例**16/17（94.1%）**；§2：B3 0.6381；§8.1/§8.2 |
| §6.4 组件C学习半边：学习路由器 | `router.py`+build/eval工具（23测试） | §8.3：**负结果**（一致率0.0875、oracle 0.7867@2 vs 固定0.7185@15），三重归因+修复方向已记录 |
| §6.4 组件C统计半边：conformal校准退出 | qa_module conformal档 | §6.4-3：**负结果**（高置信档P≤0.33），如实报告 |
| §6.5 实验设计：91QA主集 | paper_matrix+cascade评测 | §2/§3/§4（B0-B5+10消融+4对bootstrap+五配置） |
| §6.5 实验设计：17真实违例专项集 | build/eval_violations | §7（演进52.9%→94.1%） |
| §6.5 实验设计：变异注入集（robustness） | build/eval_mutation工具+394注入集（7测试） | §8.4：漏检率矩阵10.4%+**证据侧双登记发现** |
| §6.3 L1输出协议（unsat core/求解日志防scope laundering） | numeric_z3的SMT-LIB+unsat core完整输出 | §8.1 |
| §6.8 实施顺序S1-S6 | 全部完成 | §8/§9各节 |
| §6.8 S7：定位gold标注 | 48号协议已固化，**人工项未做** | ⬜（见下） |

剩余遗留（人工项/写作项/可选深化——**无算法侧阻塞项**；Wave 7新增两项P2技术债）：

1. **gold人工标注（最高优先级，人工项）**：91条silver（S6/R8/N77）非gold；§6.4-5显示GLM在两种证据观下NIE/refute边界不自洽——所有主表数字本质是vs-silver。**标注工作台已建**（Wave 7，§10.4第一行）：`tools/build_annotation_sheet.py`→`collect_gold_annotation.py`→`finalize_gold.py`三工具链（108实例/525 claim预填+TSV表单+回收校验+双人κ+gold_v1导出；速查手册`docs/srs_project/gold_annotation_sheet_v1.md`，协议=48号文档），**待人工标注（估6-9小时）**。证据观协议已预固化（answer-vs-frozen-evidence，开放世界）。**claim级归因闭合（063/068模式，§6.6）的评测侧（判定∧归因claim正确的AVeriTeC式联合评分）依赖人工gold，挂起于此**；074类已由enum_join确定性闭合。
2. **077 L3证据投递修复（P2，技术项）**：`llm_residual.py`的`_select_statements`按scope字面命中排序，能力表行（ev-000035/ev-000030）被挤出前30条——判定能力不是缺口、证据投递是缺口（50号文档§2的b-select归因）；修复=内容重合参与排序或枚举类残差claim强制纳入scope邻域行。
3. **跨文档正则文法升级（P2，技术项）**：06号gap（§10.3，deterministic -0.4857）证明E1/entity/enum/identifier等正则通道对自然复述式answer结构性失声——升级路线=语义匹配（BGE/NLI承担跨文法成员比对）；06号sound评测集（30条）作为泛化持续回归探针，每次栈改动复跑。
4. **论文写作**：主表/消融/bootstrap/级联经济学/EGT定律（§6.1）/评测驱动专家补全闭环（§6.7）/变异注入矩阵与证据侧双登记（§8.4——方向A的实证论据）/学习路由负结果（§8.3）已可成文（数字以本文档为准）；**Wave 7新材料**：诚实评测协议（§10.1）/审计-响应对照表（§10.4）/跨文档泛化gap（§10.3，作为limitations与方向A论据）；§6.4负结果集（含路由器）作为独立小节；L3漂移声明写入实验设置（reproducibility声明）。
5. **代码提交**：CascadeVerify v2的Wave 5+6+7全部代码（algorithms/consistency/新模块+tools/新脚本+tests）在工作区未提交，所有runs的git_sha停留在ff0d4950——论文复现性要求尽快commit。
6. **可选VIO-15文档名通道**：17违例中唯一未检出项（§7.3）；文档级自反一致性（本文档自称×全文档引用join），与证据块级比对正交——可选项，不阻塞算法完成声明。
7. （次要）追溯表线性化签名缺失（1/330）；DEQ的证据质量-成本权衡（+0.007 macro-F1，0次API调用全缓存）待在更大评测集上复测；conformal需换校准信号（非softmax最大概率）后再试（当前以负结果报告）。

---

## 数字核对记录

本文档§2主表、§3消融表、§4 bootstrap、§6、§7、§8、§10全部数字已于2026-10-27（Wave 7收口）由脚本从下列result.json逐项重读核对：`eval_paper_matrix_c409df7f_20261027_125551`、`eval_cascade_1e92cdce_20261027_124941`、`eval_violations_5d5c92a8_20261027_113100/120749/124733/165400/195407`、`eval_router_2b76c358_20261027_170640`、`router_train_7a90549c_20261027_165644`、`eval_mutation_detection_750b7b7d_20261027_165008`、`eval_paper_matrix_0fabaced_20261027_023711`（历史对照）、`eval_cascade_1e92cdce_20261027_024429`（及022407/023405/023644）、`eval_llm_residual_5dd69927_20261026_173434`、`build_egt_dataset_3a52cd3f_20261026_154036`、`build_egt_dataset_721c8665_20261026_165547`、`build_egt_dataset_8a8716bb_20261027_003528`、`train_residual_nli_ade325ae_20261026_195906`、`train_residual_nli_acfead4b_20261027_013647`、`eval_nli_residual_4971ceba_20261026_201247`、`eval_nli_residual_2996af6b_*`（12个），以及Wave 7新run：`eval_test_honest_6740ed5c_20261027_185819/195753`、`calibrate_on_dev_a069227d_20261027_185110`、`eval_qa_module_silver_f119425e_20261027_190326/195515`、`eval_qa_dev_split_6d4e96bb_20261027_195532`、`eval_violations_5d5c92a8_20261027_195501`、`eval_crossdoc_27e8ce32_20261027_190259/195859`、`build_crossdoc_evalset_1a7c8719_20261027_190350`。§9.4全部run目录Test-Path验证存在；S1QA-074/056的确定性refute经`QAConsistencyModule(use_experts=True)`单实例复现验证（enum_join_registry裁决）；§8.1的数值事实计数（04全文档92条/91QA 0条/违例集22条）经复核脚本重derive（`evidence_compiler`加载04号360块+图64条→`extract_numeric_facts`）；§8.3的特征分布数字（EGT 1.02/10/24.06 vs QA 5.01/20.64/218.34）从`router_train`的router_dataset.jsonl重算；§10.1的dev/test切分侧分布（S3/R4/N38、S3/R4/N39）与29簇零跨侧从`dev_test_split_v1.json`+`final_labels.jsonl`重derive；§10.2的support召回5/6（B4配置，006/021/053/066/069检出、077漏检）经`QAConsistencyModule(use_experts=True, use_llm_residual=True)`六实例现场复现验证（L3全缓存命中）。**数字已核对。**

发现的数字不一致（如实记录）：
1. **conformal高置信档精度**：7专家栈定稿run 124941为P=0.0（kept档n=1）；briefing口径0.286来自同日三次更早run（022407/023405/023644，kept档n=7、P=0.2857，5专家栈）。处置：§6.4-3两个口径并列报告，定稿run为准、三次复现值为旁证；差异归因=共享llm_cache在023711（paper_matrix，含39次新API写入）前后状态变化。
2. **能力表列错位普查分母**：会话census记124/181；本文复核（同签名口径）为124/180。处置：§6.2按124/181报告并注明复核口径差异（±1来自表头签名边界）。
3. **cascade macro-F1（5专家栈时期）**：同日三次更早run（022407-023644）均为0.6266，5专家栈定稿run 024429为0.6879。处置：历史记录保留；7专家栈重跑后（124941）cascade=0.7185成为当前定稿值，差异链（0.6266→0.6879→0.7185）中前两跳归因缓存演化、末跳归因两join专家，均已写入§2/§6.7。
4. **B0/B1/B2/B5在7专家栈重跑中数字不变**（0.8462/0.3056、0.5714/0.3272、0.7143/0.6105、0.8681/0.7085）：符合预期——四配置均不经过L0/L1专家族（B2的LLM调用全缓存命中）；B4的LLM invocations从85降到83、B2的api/cache从90/1变为0/91，均因llm_cache状态演化（提示词命中的缓存更多），判定结果不受影响。
5. **违例集定位口径随VIO-17闭合而变化**（Wave 6，预期演化而非不一致）：15/17口径（124733）定位P=0.8519/R=0.697、gold_refs_total=33（23命中、9/15全命中）；16/17口径（165400）P=0.80/R=0.7059、gold_refs_total=34（24命中、10/16全命中）——分母+1=VIO-17的gold ref进入统计（此前未检出不计）；P下降0.05源于coverage专家对VIO-17输出3个refute_block_refs（gold命中其中1个，ev-000262/280为章节存在性锚点非定位gold）。处置：§7.2按165400终态报告，差异与机制如实注明。
6. **P1修复后违例定位gold命中24→23**（Wave 7，165400→195407）：id_join精确绑定使VIO-03不再输出第二个冲突锚点ref（ev-000271）；检出16/17、逐实例通道归因、target_hit全部零变化，仅定位P 0.80→0.7931/R 0.7059→0.6765。处置：§7.2仍按165400（Wave 6终态）报告、§10.2按195407（P1修复后回归）并列报告并注明机制。
7. **eval_test_honest两run的optimistic_bias字段符号相反**（Wave 7，口径混淆点）：修复前run（185819）+0.0145=纯乐观偏差（同代码：legacy自评−held-out）；修复后run（195753）-0.1101=混合口径（旧代码legacy自评−新代码held-out，差值含代码改进）。处置：§10.1以+0.0145为乐观偏差定读数，-0.1101的口径在正文显式警告。
