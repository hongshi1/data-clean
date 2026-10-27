# 50 · P1 support召回失败分析（2/6漏检4条）

> 状态：**分析完成+P1修复落地（2026-10-27晚）**——§6路线图P1两条c修+P2的a修（id_join精确绑定提前）已实施，修复后状态见§7。数字来源：`runs/diagnose_support_misses_159abe4c_20261027_185946`（`tools/diagnose_support_misses.py`，B4配置`use_experts=True, use_llm_residual=True`，L3全部走llm_json磁盘缓存）；全量参照`runs/eval_paper_matrix_c409df7f_20261027_125551`（B4：acc 0.9121 / macro-F1 0.7257 / S P 0.667 R 0.333 F1 0.444）。变体选型只在冻结dev split上做；test侧数字由后续诚实评测（`tools/eval_test_honest.py`线）报告。
>
> 结论先行：**4条漏检里没有一条是"聚合语义太严"单独造成的**。16条阻断claim中9条是我们自己的分解碎片（c类，序列专家把编号列表重析为"1．"前缀claim、表格残片claim），5条是通道语义与silver的claim级判定错配（a类，id_join父子主体混淆、序列通道对非时序内容判"凭空步骤"），2条是L3判了NIE（b类，且根因是L3的30条语句选择没把能力表行送进prompt）。**聚合变体在dev上被否决**（dominant_70召回+1条换24条假support，no_minor_block零效果）；**确定性修复（融合键剥离编号前缀）恰好恢复066/069两条且对其余89条零副作用**——修复杠杆在通道/分解层，不在聚合层。

## 1. 问题定义与口径

91QA silver（GLM-5.3 review）：S=6 / R=8 / N=77。当前系统（B4）support检出2/6：

| 实例 | 检出路径 | claim构成（fused） |
|---|---|---|
| S1QA-006 | L3残差（4条语义claim全部llm_residual support） | 4/4 support |
| S1QA-021 | 融合（单claim：l0_entity_detector:TERM-05 support，「异常流E1」在证据明确出现） | 1/1 support |
| S1QA-053 | **漏检→误refute** | 5条：2 support + 2 refute + 1 NIE |
| S1QA-066 | 漏检→NIE | 7条：4 support + 3 NIE |
| S1QA-069 | 漏检→NIE | 10条：6 support + NIE×4 |
| S1QA-077 | 漏检→NIE | 7条：1 support + 6 NIE |

**聚合语义事实核对**：silver的实例级聚合同样是refute>NIE>support的严格∀（`tools/validate_final_labels.py`断言；6条support实例的GLM per-claim判定全是support，strict-∀自然得support）。所以"silver用更宽松聚合语义"的假设不成立——**差异全部在claim分解与claim级语义**：GLM不会产生碎片claim，且GLM的claim级判定（开放列表"包括"非穷尽、父子主体不混淆、看到的是完整证据）与我们通道不同。这直接改变了修复方向：不是改聚合追silver，而是修分解与通道。

阻断原因分类口径（每条非support的fused claim归一类，按序判定）：

- **c 分解粒度**：我们的分解产生了GLM不会单独断言的claim——编号前缀重复claim（"1．X"与已被L3判support的"X"同内容不同文本，逐字融合键合不上）、表格残片claim（表头行、"4．1.1"单元格）。
- **b 能力缺口**：残差L3被问过且判了NIE（LLM也认为不可判定）。
- **a 聚合语义错配**：claim内容有silver support对应（含ID、包含式匹配，bigram Jaccard≥0.5或silver-claim覆盖率≥0.6），但我们的通道判NIE（或误refute，标"refute级"）。

## 2. 4条漏检的逐claim剖析

### S1QA-053（silver=support，预测=refute）— id_join父子主体混淆的误refute

问题："修改数据记录的功能标识表中包含哪些内容？" answer是ev-000067（删除/增加/修改数据记录功能标识表）的忠实复述，其中"修改数据记录→PZXQ-GN-SQLFW-TJSW"与ev-000067逐字一致。

| # | verdict | method | claim | 归类 | 机制 |
|---|---|---|---|---|---|
| 1 | support | identifier_exact_match | PZXQ-GN-SQLFW-SJXG | — | ID字面命中ev-000067 |
| 2 | support | identifier_exact_match | PZXQ-GN-SQLFW-ZXSW | — | 同上 |
| 3 | **refute** | id_join_registry | PZXQ-GN-SQLFW-TJSW | **a（refute级）** | `_check_subject_binding`：注册表中ev-000035的父功能"修改数据→XGSJ"经包含式主体匹配（`_subject_match`允许≥3字符包含）命中answer声称的子功能主体"修改数据记录"，判"ID绑定冲突"。**精确绑定（修改数据记录，TJSW）本身就在ev-000067注册表里**——包含式匹配把父子两级混为同主体 |
| 4 | **refute** | l0_entity_detector:TERM-07 | 表头残片"…\| 序号 \| Use case名称 \|…" | **c** | TERM-07拿answer表头+父行ID比对（SJXG vs XGSJ），同样是父子混淆；claim本身是表格残片 |
| 5 | **NIE** | sequence_alignment | "4．1.1 \|" | **c** | 表格单元格被当作时序步骤 |

注意：053的refute还使残差派发整体跳过（`qa_module.verify`的`not any(refute)`前置条件），L3从未介入——**误refute是最高代价的失败模式，它同时屏蔽了语义层的纠错机会**。

### S1QA-066（silver=support，预测=NIE）— 编号前缀重复claim否决L3已验证内容

问题："热点数据缓存功能有什么特点"。L3残差把4条语义claim全部判support（ev-000030明确支持查询结果缓存/可配置缓存大小/动态刷新）；**序列专家又把answer的编号列表重析为3条"1．/2．/3．"前缀claim**，因证据无用例主事件流而NIE（"时序不可核对"）。融合键是精确文本——"1．查询结果缓存：…"≠"查询结果缓存：…"，无法与L3已判support的同内容claim合并，3条NIE碎片否决整体。

| # | verdict | method | claim（截断） | 归类 |
|---|---|---|---|---|
| 1-4 | support | llm_residual | 热点数据缓存功能有以下特点 / 查询结果缓存：… / 可配置的缓存大小：… / 动态刷新机制：… | — |
| 5 | **NIE** | sequence_alignment | 1．查询结果缓存：提供对查询结果的数据缓存功能… | **c（编号前缀重复）** |
| 6 | **NIE** | sequence_alignment | 2．可配置的缓存大小：… | **c** |
| 7 | **NIE** | sequence_alignment | 3．动态刷新机制：… | **c** |

### S1QA-069（silver=support，预测=NIE）— 同066机制

L3判6条语义claim全部support（含"这些操作通过数据对象方式实现，支持在应用软件中进行相应的操作"）；序列专家的4条"1．添加：…/2．删除：…/3．修改：…/4．查询：…"前缀claim NIE否决。归类：4条全部**c（编号前缀重复）**。

### S1QA-077（silver=support，预测=NIE）— b+a复合，L3语句选择是隐藏根因

问题："SQL访问功能包括哪些核心操作？"

| # | verdict | method | claim（截断） | 归类 | 机制 |
|---|---|---|---|---|---|
| 1 | **NIE** | conservative_unresolved | 初始化、读取配置文件连接、数据库连接和关闭功能 | **b** | 枚举成员"数据库连接和关闭功能"未字面命中（证据是"数据库连接、数据库关闭"）；进残差后L3判NIE："ev-23列出的SQL访问功能…未包含初始化和关闭功能；ev-4仅以前置条件提及初始化"。**但ev-000035的能力表行"数据库操作功能包括数据库初始化、读取配置文件连接、数据库连接、数据库关闭功能"就在冻结证据里且字面支持该claim（silver claim 1引用的就是它）——L3的30条语句选择没选中这一行** |
| 2 | support | llm_residual | 错误信息获取、二维输出、JSON输出、DML输出以及逐行获取… | — | L3判support（ev-22） |
| 3 | **NIE** | conservative_unresolved | 插入、删除和查询BLOB（大型对象块）数据记录 | **b** | 枚举1成员未命中；L3判NIE："ev-23仅提及BLOB数据操作功能存在…"。**同样：ev-000030"提供大字段（BLOB）数据的删除、更新、查询以及添加功能"在冻结证据里但未被选入L3的prompt** |
| 4 | **NIE** | sequence_alignment | 1．数据库操作：包括初始化、… | **a** | 序列通道把编号功能项当步骤，"凭空步骤"NIE；silver claim"数据库操作包括初始化、读取配置文件连接、数据库连接和数据库关闭功能"判support |
| 5 | **NIE** | sequence_alignment | 2．修改数据：涉及删除、增加或修改数据库中的记录 | **a** | 同上（silver support对应） |
| 6 | **NIE** | sequence_alignment | 3．查询数据：不仅限于常规查询，还包括… | **a** | 同上（合并了silver claim 3+4的内容） |
| 7 | **NIE** | sequence_alignment | 4．BLOB数据操作：包括插入、删除和查询BLOB… | **a** | 同上 |

**L3语句选择根因（复核）**：`_select_statements`按（scope命中→主体重合→并集重合）排序取30/134条。077的残差claim文本不含"数据库操作"字样→能力表行scope不命中（rank=1组），被scope命中的用例流（ev-000049，"读取配置文件连接"字样在claim里）与查询子功能表（ev-000087）挤出前30。**判定能力不是缺口，证据投递是缺口**——这是b类的子归因（b-select），修复是确定性的排序/配额问题而非模型问题。

## 3. 阻断原因分布与机制汇总

4条漏检共**16条阻断claim**：

| 类 | 条数 | 实例分布 | 机制 |
|---|---|---|---|
| **a 聚合语义错配** | **5** | 053×1（id_join误refute，父子主体混淆）、077×4（序列通道对非时序编号项判"凭空步骤"） | 通道语义比silver严格或锚错层级 |
| **b 能力缺口（L3判NIE）** | **2** | 077×2（枚举claim） | 表面是语义判定，根因是**L3语句选择未投递能力表行**（b-select）；silver有字面支持对应 |
| **c 分解粒度** | **9** | 053×2（表格残片）、066×3、069×4（编号前缀重复） | 序列专家重析编号列表+融合键精确匹配，碎片claim否决已验证内容 |

三个系统级教训：

1. **c类占多数（9/16）且全部可确定性修**——序列专家对非时序answer的claim生成是碎片源头（066/069的7条重复+077的4条错位+053的1条单元格残片）。
2. **误refute比NIE更伤**（053）：refute同时触发聚合refute、屏蔽残差派发、并造成refute|support混淆单元。
3. **L3的support判定本身不足以做实例级信号**（见§5 dominant_70的24条假support）——严格∀聚合当前恰好是精度的保护壳。

## 4. claim分解粒度对比（GLM silver vs 我们）

| 口径 | GLM平均claim数 | 我们（fused） | 倍率 |
|---|---|---|---|
| 全corpus（n=91） | 5.58 | 7.66 | 1.37× |
| 6条support实例 | 4.00 | 5.67 | 1.42× |

逐实例（our/GLM）：006 4/3、021 1/2、053 5/4、066 7/3、069 10/6、077 7/6。

超额来源分解（fused口径）：066多出的4条里3条是序列前缀重复；069多出4条全是；077的4条序列claim内容上是silver claim的带前缀改写（GLM没有把编号列表二次分解成"步骤"）。**粒度差不是"我们分解更细所以更严格"，而是"序列通道把非时序内容二次分解成GLM不存在的claim"**——前者是设计选择，后者是通道适用性缺陷。

## 5. 聚合变体实验（dev split，选型只看dev）

### 切分

复用冻结切分`data/gjb_438c/qa_frozen/dev_test_split_v1.json`（`tools/build_dev_test_split.py`：seed=42，29个功能主题簇整簇原子分配防泄漏，dev n=45：S=3/R=4/N=38；test n=46：S=3/R=4/N=39）。4条漏检的分布：053/066在test侧，069/077在dev侧；006在test、021在dev。

### 变体定义（`QAConsistencyModule(aggregation=...)`，默认strict向后兼容）

1. **strict-∀**（现状）：任何NIE→NIE，refute最先。
2. **dominant_70**：无refute时，decidable claim（support/refute判定，或rationale含主动负观察标记的NIE——"凭空步骤/未全部命中/未在冻结context命中"等；`semantic_unresolved`与"时序不可核对"类无能力NIE不计入分母）中support占比≥70%→support。
3. **no_minor_block**：无refute且核心claim（非效果性/总结性——`_MINOR_CLAIM_MARKERS`文本标记+长度<6的残片）全support→support；无核心claim时回退strict。

### dev数字（B4配置，L3全缓存命中，0次新API调用）

| 变体 | acc | macro-F1 | S P/R/F1 | R-F1 | N-F1 | 假support增量 |
|---|---|---|---|---|---|---|
| strict（现状） | 0.9333 | **0.7833** | 1.000/0.333/0.500 | 0.889 | 0.961 | —（0） |
| dominant_70 | 0.4222 | 0.5089 | 0.077/0.667/0.138 | 0.889 | 0.500 | **+24**（25次翻转：24假+069真） |
| no_minor_block | 0.9333 | 0.7833 | 1.000/0.333/0.500 | 0.889 | 0.961 | +0（零翻转） |

变体在4条漏检上的规则级效果（机制诊断，聚合strict run的已融合claim，非test评测）：053三变体全refute；066 dominant_70→support；069 dominant_70→support；077三变体全NIE。

**选型结论：保持strict（默认）。** dominant_70用1条真恢复（069）换24条假support（silver=NIE的实例里L3对部分claim判support、其余claim无能力NIE——占比≥70%即翻转），S精度坍到0.077、macro-F1 -0.274，**否决**。no_minor_block在dev零翻转——效果性/总结性标记在当前阻断claim上不命中（066在test侧；其"确保…"碎片只是3条阻断之一，前缀碎片本身是核心claim），**无收益也无代价，否决**。两个变体保留为`AGGREGATION_VARIANTS`实验接口（`tests/test_aggregation_variants.py`，18个用例锁定行为），默认关闭。

### c类确定性修复的oracle探针（对照）

模拟"融合键剥离编号前缀"（`_fuse_per_claim`的group key从精确文本改为去"1．"前缀文本，"1．X"与"X"同组合并、refute>support>NIE取胜者，聚合仍strict）：**全corpus恰2条翻转——066 NIE→support、069 NIE→support（均silver=support），其余89条零变化**。同样的恢复目标，聚合层实现（dominant_70）代价是24条假support，融合层实现（c-fix）代价是零——**修复杠杆位置的直接证据**。

## 6. 修复路线图

按"确定性可修→语义层→评测标准"排序（预期收益按§2/§5机制推演，正式数字以修复后重跑为准）：

| 优先级 | 类 | 修复 | 位置 | 预期效果 |
|---|---|---|---|---|
| P1 | c | **融合键剥离编号前缀**：`_fuse_per_claim`的分组key去"N．/N./N、"前缀 | `algorithms/consistency/qa_module.py`（`_fuse_per_claim`） | oracle探针：+2（066/069），89条零副作用；claim数从7.66向GLM的5.58收敛 |
| P1 | c | **序列专家适用性门**：answer编号项非"步骤序列"形态（问题非流程型/证据无用例主事件流）时不生成"凭空步骤"claim；表格残片（表头行、纯编号单元格）在claim出口过滤 | `algorithms/consistency/sequence_expert.py`、`algorithms/consistency/qa_module.py`（claim出口） | 消除077的4条a-阻断与053的2条c-阻断；sequence_alignment在全corpus的225条claim大量是这类错位产物 |
| P2 | a | **id_join精确绑定优先**：claimed (主体,ID) 在注册表精确命中时跳过包含式主体的冲突检查（父子层级非双登记） | `algorithms/consistency/id_join_expert.py`（`_check_subject_binding`） | 修053的误refute（顺带恢复该实例的残差派发）；TERM-07实体检测器同款父子混淆同修 |
| P2 | b | **L3语句选择修投递**：能力表行按内容重合参与排序（不只scope字面命中），或对枚举类残差claim强制纳入其scope_key邻域行 | `algorithms/consistency/llm_residual.py`（`_select_statements`） | 077的2条b-阻断——证据在冻结context内（ev-000035/ev-000030），L3被问过但没看到 |
| P3 | a/b | **gold标注语义澄清**：①"包括"列表按非穷尽开放列表判（成员部分命中+无反例→support？）；②功能ID的父子层级（修改数据vs修改数据记录）不同主体不同ID是常态；③效果性/总结性扩展在实例级聚合中是否豁免。053/077是黄金边界案例，人工gold复核时优先钉死 | gold标注协议（`docs/srs_project/`标注手册线） | a类本质是"评测标准谁对"——若gold采GLM语义，则通道语义要向gold对齐；若gold采严格语义，silver的053/077标签需复核 |

**执行顺序建议**：P1两条c修先做（确定性、零副作用、互相独立），完成后support召回预期2/6→4/6（006/021/066/069），053/077留待P2/P3。P2的id_join修复需同步重跑17违例集（id_join是违例集15/17检出的主力专家，防止修91QA的053时破坏04号文档的identifier检出——回归口径见`49_cascadeverify_v2_results.md`§7）。（**落地状态见§7：P1两条c修+P2的a修已于当晚实施，实际效果优于该预期——053同步翻正，5/6。**）

## 7. P1修复落地结果（修复后状态，2026-10-27晚）

**落地修复**（§6路线图前三行，全部确定性改动、无新模型调用）：

| # | 修复 | 位置 | 状态 |
|---|---|---|---|
| P1-c | 融合键剥离编号前缀：`_fuse_per_claim`分组key去"N．/N./N、"前缀，"1．X"与已验证"X"同组合并（refute>support>NIE取胜者）；claim_text不动 | `algorithms/consistency/qa_module.py`（`_FUSION_PREFIX_RE`） | ✅ |
| P1-c | 序列专家适用性门：问题须含流程/步骤/时序指示词；编号项为异常类型枚举（失败关键词占比≥0.5）或带标签长并列项（无时序连接词且平均长度>40字符）时整实例跳过 | `algorithms/consistency/sequence_expert.py` | ✅ |
| P2-a（提前） | id_join精确绑定：`_binding_candidates`精确优先分层，包含回退方向固定为claimed⊂registered（父功能注册不仲裁子功能声称）；TERM-07同步加全证据命中优先护栏（ID在冻结证据全文逐字出现→support，主体归属交id_join仲裁） | `algorithms/consistency/id_join_expert.py`、`algorithms/consistency/entity_detector.py`（`_check_interface_ids`） | ✅ |
| P2-b | L3语句选择修投递（077的b-select） | `algorithms/consistency/llm_residual.py`（`_select_statements`） | ⬜ 留P2 |

**修复后数字**（全部runs协议落盘，git_sha=ff0d4950）：

| 口径 | 修复前 | 修复后 | run |
|---|---|---|---|
| support召回（B4配置，6条support实例） | 2/6（006/021） | **5/6**（+053/066/069；077仍NIE留P2-b） | 六实例现场复现（L3全缓存） |
| 全91确定性（experts-only） | 0.9011 / 0.6381 | **0.9121 / 0.7212**（+0.0831） | `eval_qa_module_silver_f119425e_20261027_190326→195515`（194154复测一致） |
| dev侧B4（冻结dev 45条） | —（strict变体0.7833为修复前诊断口径） | **acc 0.9556 / macro-F1 0.8875**（S P1.0/R0.667；R P0.8/R1.0） | `eval_qa_dev_split_6d4e96bb_20261027_195532` |
| test侧（cascade，current-default） | 0.704 / 0.913（R P0.75） | **0.8286 / 0.9348**（refute P=1.0/F1=0.8571，S R=0.667） | `eval_test_honest_6740ed5c_20261027_185819→195753` |
| 17违例集（deterministic+cascade） | 16/17 | **16/17零回退**（逐实例通道归因不变） | `eval_violations_5d5c92a8_20261027_195407/195501` |
| 跨文档06号（sound 30条） | det 0.1524 / cas 0.5309 | **逐位一致（零改善）** | `eval_crossdoc_27e8ce32_20261027_190259→195859` |

- **翻正机制对照§2的剖析**：053=双误refute消除（id_join父子混淆的`id_join_registry`误refute+TERM-07表头残片误refute，a-fix；误refute消除同时恢复残差派发）；066/069=前缀碎片claim不再否决L3已验证内容（c-fix：融合键合并+序列门不再生成"1．"claim）。077的b类（L3判NIE）与a类阻断原样保留——**证据投递修复（P2-b）是077的唯一路径**。
- **违例集回归的定位侧小代价**：gold命中24/34→23/34（P 0.80→0.7931、R 0.7059→0.6765）——VIO-03第二个冲突锚点ref（ev-000271）不再输出（精确绑定收窄冲突锚登记面）；检出/通道归因/target_hit零变化。id_join作为违例集检出主力的地位未被破坏（identifier 5/5维持）。
- **test侧066的口径注明**：test诚实评测走cascade配置（L2先判、无refute候选不升级L3），066在该路径仍NIE；support召回5/6是B4（L3直连）口径——cascade与B4在066上的分歧如实记录（49号文档§10.1）。
- **跨文档零改善的解读**：三项修复全部是04号answer文法的特异性bug修（引号标识符+包括式枚举的形态假设），对06号自然复述式answer无效——泛化缺口在正则文法层（49号文档§10.3的结构性归因），与本文修复无冲突。
- **诚实声明**：本分析的失败诊断（§2）用了**全91失败分析（含test侧实例053/066）**；c-fix的oracle探针（§5）验证零副作用（全corpus恰2条翻转、其余89条零变化）。**test侧数字（195753）的"纯净度"有此折扣**——诊断阶段看过test侧失败实例；test评测发生在修复定稿之后、只跑一次（test split协议见49号文档§10.1）。

**复现**（数字核对入口）：

```
# 行为回归（含适用性门/融合键/精确绑定的单元锁定）
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python -m pytest tests/test_qa_consistency_module.py -q
# 全91确定性（修复后 0.9121/0.7212）
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/eval_qa_module_vs_silver.py
# test一次评测（cascade，修复后 0.8286）
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/eval_test_honest.py
# 违例回归（16/17零回退）
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/eval_violations.py
```

## 8. 复现与数字核对

```
# 诊断+变体实验（L3全缓存，无新API调用）
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/diagnose_support_misses.py
# 变体行为单元测试+默认回归
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python -m pytest tests/test_aggregation_variants.py tests/test_qa_consistency_module.py -q
# ruff
python -m ruff check tools/diagnose_support_misses.py tools/build_dev_test_split.py tests/test_aggregation_variants.py algorithms/consistency/qa_module.py
```

- 数字主run：`runs/diagnose_support_misses_159abe4c_20261027_185946`（result.json含4条漏检的逐claim表+归类、粒度对比、dev三变体指标+逐实例翻转、变体规则级效果、c-fix探针）
- 全量B4参照：`runs/eval_paper_matrix_c409df7f_20261027_125551`（B4 macro-F1 0.7257 / S 0.444）
- 切分：`data/gjb_438c/qa_frozen/dev_test_split_v1.json`（与P0 dev/test效度线共享的冻结资产）
- L3 raw判定与077语句选择的取证：诊断脚本对`llm_residual.verify_residual_claims`的capture包装（同缓存prompt）；选择复核为独立探针（134条语句中前30不含ev-000035/ev-000030能力表行）
- 本文全部数字于2026-10-27由上述result.json逐项重读核对。**变体选型只用了dev侧数字；`variant_effect_on_missed`与c-fix探针是跨全corpus的机制诊断（失败分析），不构成test侧评测声明——test侧数字由`tools/eval_test_honest.py`线在修复落地后诚实报告（已完成：`runs/eval_test_honest_6740ed5c_20261027_195753`，test=0.8286，见§7）。**

## 9. 对任务的诚实修正

1. 任务背景假设"silver(GLM)用更宽松聚合语义"**不成立**：silver实例级聚合同为strict-∀（`validate_final_labels.py`断言）。宽度差异在claim分解（GLM无碎片claim）与claim级判定，不在聚合规则。
2. 任务背景中"053是identifier通道×2 support被sequence_alignment的NIE否决"**不准确**：实际阻断是id_join/TERM-07的**两条误refute**（父子主体混淆），sequence的NIE只是第三阻断；且refute使残差派发整体跳过。
3. dominant_70不是"用宽容换召回"的可行折中——dev上它是精度灾难（24假support）。召回的正确路径是c类确定性修复（探针已验证零副作用）+ b类证据投递修复。
