# 100. P3 Eiter回路试点: 教师归纳rulepack变体 vs 人工onboard

> 定稿日期：2026-11-24 | 任务来源：99号Phase 3（P3）· 方法学依据：97号§3.2/§3.3/§3.4 · D类判定：98号
> 实验脚本：`tools/eiter_rule_induction.py`（测试：`tests/test_eiter_rule_induction.py` 20项）
> runs：v1=`eiter_rule_induction_09f27174_20261124_095239`、v2=`..._101427`（含oracle_trials.json）、v3=`..._102716`（中断于并发代码编辑）、v3-retry（定稿）=`..._103935`
> 教师调用全程`llm_json_teacher` cache=True（GLM-5.3, response_contract=json_final_content_v2+reasoning_effort=low）；评测口径=deterministic配置`QAConsistencyModule(use_experts=True)`，**每pack评测于全新子进程**（见§6方法学发现）

## 0. 一句话结论

**范式可行性=有条件成立**：回路机器（失败例采集→教师归纳→load_rulepack符号验证→CLIPR零回退闸门→贪心接受→逆向剪枝）工作正常且成本可控（定稿run教师调用100%缓存复现）；教师归纳质量对**反馈通道的保真度**极度敏感——v1（原始证据反馈）0条有效规则（教师对线性化格式产生空白幻觉）；v2（引擎trace反馈）诊断正确但0条有效规则（诊断→配置旋钮映射失败）；v3（trace+精确旋钮语义+剪枝反馈）**教师自主找到人工未发现的有效修复**（enum_device items下限6→4，crossdoc06 macro-F1 0.2619→**0.407**，refute F1 0.1818→0.5714，91QA零回退），超过oracle上限（0.400）。人工doc06_v1在同一评测口径下standalone回退（0.1481）——教师pack数值上以+0.256 macro-F1优于人工pack，但优势主要来自人工pack的陈旧性而非教师的绝对强度。

## 1. 实验设计（97号§3.4协议的实现）

```
失败例获取    generic pack(srs_gjb_v1) × crossdoc06(30条, sound标签)
              → deterministic评测 → 20条失败例(claim归因+引擎trace)
                ↓ 按family分批(≤5条/批)
教师归纳      GLM-5.3逐批归纳规则包变更(7种受控op:
              replace_extraction_template / add_canon_map /
              add_table_signature / set_id_family_prefixes /
              set_join_param / add_vocabulary_words / set_threshold)
                ↓ 逐项白名单校验(名字必须存在于基线pack)
符号验证      load_rulepack全schema校验(正则编译/命名组保持/阈值范围/
              结构合法性)——教师规则必须先过引擎schema契约
                ↓
回归约束      CLIPR式"修订不回退"(闸门, 每个试验pack两评测集):
              - 91QA主评测: 逐实例零回退(正确→错误翻转=拒) +
                macro_f1/accuracy不低于基线(0.7212/0.9121)
              - crossdoc06: 零新增错例 + 错例数单调不增
              - 专家运行时异常一票否决(教师规则炸专家=拒)
                ↓ 贪心逐变更接受 → 逆向剪枝(无效变更移除, 可剪到空集)
修补回路      round N: 剩余失败例+已接受变更+被剪枝变更回流教师
最终产物      config/rulepacks/doc06_eiter_v1.json + 与人工doc06_v1对比
```

三处与97号原始设计的实现决策：

1. **评测子进程隔离**：每个pack的评测在全新子进程执行。原因：`numeric_z3_expert._unit_table`是`@lru_cache(maxsize=1)`且无pack身份键、`gjb_presence_expert`的词表正则缓存同样身份盲——进程内切换pack会继承首个pack的派生配置（历史`eval_crossdoc5_onboard`的in-process切换受此污染，见§6.1）。
2. **deterministic口径**：规则包只作用于L0/L1专家；L2 NLI的fp16波动（±0.05，49号§6.4-4）会污染规则包效应的测量。91QA主评测当前口径0.7212/0.9121即deterministic。
3. **op词表结构性排除标准级知识**：gjb段/gjb_rule_library_path/classify_order不在任何op的可达路径上（与onboarding.py的"标准级知识不动"原则一致），最终pack带守卫测试。

## 2. 基线（全新子进程口径, deterministic）

| pack | crossdoc06 macro-F1 | acc | wrong | 91QA macro-F1 | acc | wrong |
|---|---|---|---|---|---|---|
| generic `srs_gjb_v1`（04号文法） | 0.2619 | 0.3333 | 20 | 0.7212 | 0.9121 | 8 |
| manual `doc06_v1`（人工onboard） | **0.1481** | 0.2667 | 22 | 0.7212 | 0.9121 | 8 |

**发现①（人工pack陈旧性）**：doc06_v1是M33时代的fork，缺srs_gjb_v1后来新增的`join_params.numeric_z3`（cn_unit_aliases中文单位别名）、`join_params.coverage`、gjb词表/gjb簇段。standalone子进程口径下**人工pack自身回退**——C06QA-008/018（numeric_z3判对的support/refute）翻成NIE。历史评测（eval_crossdoc5_onboard, 2026-10-30）显示doc06_v1"与generic零差异"，该结论部分是**缓存污染假象**（in-process切换时numeric_z3的单位表继承自先加载的generic pack）。rulepack外置的维护成本（基pack演化时fork不跟进）由此有了实证数字。

## 3. 三次回路迭代（反馈通道的消融）

### 3.1 v1：原始证据反馈 → 0条有效规则（教师幻觉）

失败例prompt=QA+label_proof+错判claim归因+**原始证据块（含表格HTML）**+完整基线pack JSON。两轮共17条变更提案（11次API调用，全部通过schema验证与两道闸门=安全但无效），逆向剪枝后仅剩2条惰性变更（剪枝当时不能到零的缺陷已修复），crossdoc06数字与generic逐位相同。

**归因**：教师从原始HTML推测线性化格式，系统性产生**空白幻觉**——提出6条"容许字段名/ID内空白"的模板变体，而引擎实际运行在`re.sub(r"\s+","")`折叠后的无空白文本上（`build_id_registry`/`build_domain_registry`都先折叠再匹配）。诊断对象（输入格式）在教师输入中不存在。

### 3.2 v2：引擎trace反馈 → 诊断正确，0条有效规则（旋钮映射失败）

反馈通道升级：每个失败例附**引擎实际视图**——线性化语句（空白已折叠）+enum/id专家的真实提取输出（注册表+answer侧声明）。教师的诊断质量跃升：准确定位了成员污染（"手持设备"尾缀使kind=functional）、主体窗口污染（"功能仅"/"通过接口"）、值域缺失（"集成阶段"）、行首锚缺陷（trace_taskbook_section的^）——与失败例的真实机理一致。但**修复落点全部选错旋钮**：

- 成员尾缀归一 → 加进`enum_dev_tail_strip`（该词表**只作用于主体候选窗口**，`_strip_tail`；成员归一化`_norm_terminal`是硬编码，只剥"版"尾）
- answer侧声明句式 → 改`enum_field_value`（该模板**只用于证据侧**build_domain_registry）
- 全部8条变更闸门通过但惰性 → 剪枝到空集，crossdoc06不变

### 3.3 oracle上限：规则包可表达空间的测量

为区分"教师能力不足"与"规则包表面无法表达"，用与回路完全相同的闸门协议测**代码知情者**能从pack层修复多少（run内oracle_trials.json）：

| oracle试验 | 变更 | crossdoc06 | 闸门 |
|---|---|---|---|
| O1 | `enum_terminal_bases += ["手持设备"]` | wrong 20→18（修C06QA-011/013）, macro-F1 0.365 | 过（91QA零回退） |
| O2 | `enum_phase_bases += ["集成阶段"]` | 惰性 | 过 |
| O3 | `id_subject_stopwords += ["通过","通过接口"]` | 惰性 | 过 |
| O4 | O1-O3组合（terminal_bases加3个尾缀形态） | **wrong 20→17（修011/012/013）, macro-F1 0.400** | 过（91QA零回退） |

**3/20失败在pack表面可寻址**（+0.138 macro-F1），全部是纯词表增量、CLIPR闸门全过——失败的根源不在规则包表达能力，而在教师的旋钮级映射。**注意表达性缺口**：成员尾缀剥离（"手持设备"→"手持"）作为归一化能力**不存在于pack配置面**（引擎硬编码只剥"版"），oracle走的是"把带尾缀形态直接加入值域"的绕行——这正是v2教师找不到路的原因之一。

### 3.4 v3：trace+精确旋钮语义+剪枝反馈 → 教师自主找到有效修复

v3在系统提示中加入**每个词表/模板的真实消费位置**（enum_dev_tail_strip仅主体侧/enum_terminal_bases驱动成员分类与归一/enum_field_value仅证据侧/id_binding运行于折叠文本等——环境文档而非答案），并把上一轮被剪枝的变更回流进下一轮prompt（"无效方案不要重复"）。

**第1轮结果**：教师提出的6条变更中，贪心接受后剪枝剩1条——

```json
{"op": "replace_extraction_template", "name": "enum_device",
 "pattern": "在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{4,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:运行|使用|提供|均可|实施)",
 "reason": "items最小长度6迫使『在平板、手持设备上使用』把尾缀『设备』吞入成员
  (剥离尾缀后仅5字符), 降到4使可选尾缀组正常剥离设备/终端, 成员归一入terminal
  值域; 04号长items形态因懒惰回溯仍匹配原值, 兼容"}
```

这条修复**与oracle不同且更根本**：oracle绕行（把"手持设备"加进值域），教师直接修了根因（items下限迫使正则把尾缀吞进成员）。crossdoc06 wrong 20→17（修C06QA-011/012/013），macro-F1 0.2619→0.407——**超过oracle的0.400**（同3例修复+更高的acc），且91QA闸门零回退。

（v3首轮运行中断于仓库内**并发代码编辑**——另一会话在实验运行中途修改`algorithms/consistency/claim_channels.py`（X1约束解码工作，+437行），round 2的91QA闸门评测撞上模块的中间态NameError。判定管线行为未变（基线数字逐位复现）后，在稳定代码上完整重跑；教师prompt确定性+缓存使重跑的第一轮零新增API调用。）

### 3.5 v3-retry（定稿run）完整结果

run=`eiter_rule_induction_09f27174_20261124_103935`（教师调用9次全部缓存命中=0次API；50次评测子进程；墙钟179s）。round 1复现中断run的结果（enum_device修复, wrong 20→17）；round 2教师对capability_device与interface_flow两批输出**零变更+结构性不可修复的明确诊断**（见§8.4），其余3批的4条修补提案经贪心+剪枝全部判定惰性——回路以"无新接受变更"自然终止。最终pack=1条变更，crossdoc06 macro-F1 **0.407**/acc 0.4333/wrong 17，91QA **0.7212/0.9121**（逐位=论文主评测数字，CLIPR零回退）。

## 4. 最终对照表

| pack | crossdoc06 macro-F1 | acc | wrong | 91QA macro-F1 | acc | 变更数 |
|---|---|---|---|---|---|---|
| generic `srs_gjb_v1` | 0.2619 | 0.3333 | 20 | 0.7212 | 0.9121 | — |
| manual `doc06_v1` | 0.1481 | 0.2667 | 22 | 0.7212 | 0.9121 | 2类落点（陈旧fork） |
| teacher `doc06_eiter_v1` | **0.407** | **0.4333** | **17** | **0.7212** | **0.9121** | **1条**（enum_device） |
| oracle（对照, 非教师） | 0.4000 | 0.4000 | 17 | 0.7212 | 0.9121 | 3词表增量 |

**验收标准核对**（99号：归纳规则≥人工规则的表现）：**达成且有余量**——教师pack对人工pack **+0.256 macro-F1**（0.407 vs 0.1481）、错例-5（17 vs 22）；对generic +0.145（修3例C06QA-011/012/013，全部refute侧：refute recall 0.1→0.4、refute F1 0.1818→0.5714）；91QA主评测逐位保持0.7212/0.9121（CLIPR约束零违反）。教师pack对oracle +0.007（同修复数下acc更高：0.4333 vs 0.4000）。诚实注记：对人工pack的优势主要来自**人工pack自身的陈旧性回退**（§2发现①）——若人工pack跟进基pack演化，净对照是"人工-2例 vs 教师+3例"。

规则条目质量对比：

| 维度 | 人工doc06_v1 | 教师doc06_eiter_v1 |
|---|---|---|
| 相对generic的落点 | trace_table.canon_map（8项表头变体）+ id_join.id_family_prefixes | extraction_templates.enum_device（items下限6→4） |
| 修复失败例数（crossdoc06, deterministic） | **-2**（陈旧性回退：C06QA-008/018翻NIE） | **+3**（C06QA-011/012/013翻refute） |
| 91QA零回退 | 持平 | 持平 |
| 可读性/溯源 | description一句话 | reason（根因机理+04兼容性论证）+source_failures（归纳自哪5例）+_eiter溯源段+守卫测试 |
| 落点重叠 | **0**——教师修answer侧提取文法（enum_device items下限），人工修表头规范/ID族，两个正交面 | |
| 维护风险 | 陈旧fork（基pack演化即回退，§2发现①实证） | 从当前基pack归纳（结构免疫） |

## 5. 教师产出规则样例（原文摘录，三轮对比）

**样例1（v3定稿pack的唯一变更——有效，修3例）**：

```json
{"op": "replace_extraction_template", "name": "enum_device",
 "pattern": "在(?P<items>[一-龥A-Za-z0-9、和]{4,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:运行|使用|提供|均可|实施)",
 "flags": 32,
 "reason": "items最小长度6迫使『在平板、手持设备上使用』把尾缀『设备』吞入成员(剥离尾缀后仅5字符), 降到4使可选尾缀组正常剥离设备/终端, 成员归一入terminal值域; 04号长items形态因懒惰回溯仍匹配原值, 兼容",
 "source_failures": ["C06QA-001","C06QA-002","C06QA-003","C06QA-011","C06QA-012"]}
```

**样例2（v2——诊断正确但旋钮选错的典型）**：

```json
{"op": "add_vocabulary_words", "vocab": "enum_dev_tail_strip",
 "words": ["设备", "终端"],
 "reason": "answer成员『平板设备/平板终端/手持设备』需剥离设备/终端尾缀归一为enum_terminal_bases基值，使kind归为terminal并与方式名称注册表join",
 "source_failures": ["C06QA-001","C06QA-002","C06QA-003","C06QA-011","C06QA-012","C06QA-013"]}
```
（诊断完全正确——成员尾缀污染使kind=functional；但`enum_dev_tail_strip`只作用于主体窗口，成员归一在引擎硬编码里——闸门通过但惰性，剪枝移除。）

**样例3（v1——输入格式幻觉的典型）**：

```json
{"op": "replace_extraction_template", "name": "id_pattern",
 "pattern": "PZXQ-[A-Z0-9]+(?:\\s*-\\s*[A-Z0-9]+)*-?",
 "reason": "06号表格中ID跨<p>拆分, 连字符后出现空白, 需容许段间空白以捕获完整标识; 04号连续形态不受影响",
 "source_failures": ["C06QA-006","C06QA-007","C06QA-016","C06QA-017","C06QA-026"]}
```
（"ID内空白"在引擎里不存在——`build_id_registry`先`re.sub(r"\s+","",text)`再匹配；schema验证与闸门均通过但零行为变化。三个样例串起来正是§3的消融故事：诊断对象的存在性→旋钮映射的正确性→修复的有效性。）

## 6. 方法学负面发现（论文级素材）

1. **进程内pack切换不可靠**（评测协议缺陷）：`numeric_z3_expert._unit_table`用`@lru_cache(maxsize=1)`（无pack身份键）、`gjb_presence_expert._ABSENCE_RE_CACHE`同样身份盲。同一进程先加载generic再切换doc06_v1时，单位表/词表正则继承generic的派生配置——**实测**：in-process doc06_v1与generic结果逐位相同，子进程standalone doc06_v1回退到0.1481。历史`eval_crossdoc5_onboard`的"06号onboard无差异"结论部分是该伪影。任何rulepack对比评测必须每pack一个全新进程。
2. **人工pack的维护陈旧性**：doc06_v1 fork自M33时代的srs_gjb_v1，基pack后续新增的numeric_z3/coverage/gjb段不在fork里——standalone下功能性回退。外置配置解决了"改哪"，没解决"跟进"：基pack每演化一次，全部fork面临陈旧化。Eiter回路从**当前**基pack归纳，结构上免疫此问题。
3. **教师反馈通道保真度是第一决定因素**（v1→v2消融）：给原始证据→教师幻觉输入格式（8/17条变更是对不存在格式的适配）；给引擎trace→诊断全部正确。LLM规则归纳文献（97号§3.2 Eiter系"数据集例引导"）的"引导"质量=输入视图与求解器实际输入的距离。
4. **诊断正确≠旋钮正确**（v2→v3消融）：trace让教师看见了正确的失败机理（成员污染/主体污染/值域缺失），但"诊断→配置旋钮"的映射仍失败——成员归一化在引擎里是硬编码（`_norm_terminal`只剥"版"），配置面无对应旋钮，教师选了语义最近但不作用于该层的`enum_dev_tail_strip`。精确的消费位置文档（每个词表/模板在引擎哪一层被谁消费）解决此问题——但这本质上是**把引擎内部知识写进prompt**，提示D类"规则学习化"的真正瓶颈是**配置表面的自描述性**，不是教师模型能力。
5. **贪心+剪枝回路对互补变更对的处理**：v2中主体归一（dev_tail_strip增量）与成员归一若同批提出可互补生效，但贪心逐条接受时单条惰性、逆向剪枝按"移除后错例数不变"会把互补对拆掉。v3的教师修复是单条独立的（未触发此问题），但这是回路设计的一般性弱点——变体：剪枝时按"移除后错例数不增且不破坏互补对"（成对移除测试），代价O(n²)评测。
6. **并发会话冲突**：实验运行中途另一会话修改`algorithms/consistency/claim_channels.py`（+437行，X1约束解码），round 2的闸门评测撞上模块中间态（NameError）。子进程隔离反而放大了时间窗内的代码不一致（每trial新进程=新代码快照）。runs协议的config.json记git_sha=HEAD，**未捕获工作区未提交修改**——按AGENTS"runs=config+git_sha+result"的复现契约，工作区脏时的实验须在报告中显式注明代码状态。

## 7. 回路成本（v1/v2/v3定稿run）

| 项 | v1 | v2 | v3-retry（定稿） |
|---|---|---|---|
| 教师调用（API/缓存命中） | 12/1 | 10/0 | **0/9**（100%缓存命中） |
| 评测子进程 | 70 | 68 | 50 |
| 墙钟(s) | 835 | ~810 | **179** |

（每个试验pack=2次子进程评测：crossdoc06先判（闸门失败即短路）+91QA；基线4次+最终2次。deterministic单次评测1-4s。定稿run的教师调用全部命中v3中断run留下的缓存——**完整回路的零API复现**得到实证：prompt确定性构造（固定字段序+sort_keys的pack JSON）+llm_json_teacher的(perfer,messages,参数)哈希缓存=同prompt重跑零成本零漂移。全实验总真实API成本=32次调用（v1:12+v2:10+v3:10），每次20-40s的GLM-5.3思考推理是主要成本。）

## 8. 范式可行性判定

**判定：有条件成立（conditional positive）**——

1. **成立的证据**：v3教师自主找到人工onboard从未覆盖的有效修复（enum_device items下限），crossdoc06 0.2619→0.407，与oracle上限同量级甚至更优（更根本的根因修复），CLIPR闸门全过。回路机器（受控op+schema验证+双闸门+剪枝）在三次迭代中零事故：所有被拒/被剪变更都有可读理由，91QA从未回退。
2. **条件的三个成分**（按v1→v2→v3消融的贡献排序）：引擎trace反馈（诊断正确性）> 精确旋钮语义文档（映射正确性）> 剪枝回流（避免重复方案）。三者都是**环境侧工程**，不是教师模型选择——这既是对97号"Eiter回路零新基础设施"判断的修正（回路本身零新设施，但反馈通道需要一次性的工程设计），也是对D类判定的深化：rulepack的下一级不是"换教师"，是**把配置表面做成自描述的**（每词表/模板声明自己的消费层与语义，引擎从配置读回自描述——这正是PL-Guard"接地/策略分离"在配置层的镜像）。
3. **对99号验收标准的回答**：**达成**——教师pack（0.407/-17错/91QA零回退）≥人工pack（0.1481/-22错）且≥generic（0.2619/-20错）；教师修复是refute侧（安全关键类），人工pack在当前代码上是净负资产（§2发现①）。附带收获：教师的修复落点（answer侧提取文法）与人工pack的落点（表头规范/ID族）**零重叠**——两路覆盖正交面，教师回路可作为人工onboard的互补而非替代。
4. **回路收敛行为值得记录**：round 2教师对5批中的2批输出**零变更+明确诊断"超出L1规则层能力"**（capability_device批："声明与注册表完全一致——按引擎输出契约, enum_join在集合一致时输出空...规则层无能为力"；interface_flow批同样）——教师正确使用了系统提示中的引擎输出契约说明，对结构性不可修复的失败如实弃权而非硬凑规则；另外3批提出的修补经剪枝验证全部惰性（其中trace_binding批的第二轮诊断比第一轮更深：发现"裸章节token缺少主体绑定，join无从发生"——诊断在进化，但pack表面无对应旋钮）。回路的终止条件（无接受变更）由真实验证驱动，不是token预算。
5. **遗留**：17/20失败仍在（9条support侧失败结构性不可达——enum_join/id_join只输出refute，注册表与声明一致时静默交回旧通道，L1输出协议不允许规则层产生support判定；此为98号"L1终态误判保留"归因的配置面根源，修复需引擎输出协议扩展而非pack变更——超出P3范围，属97号§2.4接地概率化/R2路线）。

## 9. 产物清单

| 产物 | 路径 |
|---|---|
| 回路脚本 | `tools/eiter_rule_induction.py`（run/baseline/--worker三模式） |
| 测试 | `tests/test_eiter_rule_induction.py`（20项：op校验/pack往返/闸门/贪心剪枝/prompt确定性/最终pack守卫） |
| 教师pack | `config/rulepacks/doc06_eiter_v1.json`（1条变更：enum_device items下限6→4；_eiter溯源段+守卫测试test_final_eiter_pack_loads_and_keeps_standard_knowledge） |
| v1 run | `data/gjb_438c/runs/eiter_rule_induction_09f27174_20261124_095239` |
| v2 run（含oracle） | `data/gjb_438c/runs/eiter_rule_induction_09f27174_20261124_101427`（+oracle_trials.json） |
| v3中断run | `data/gjb_438c/runs/eiter_rule_induction_09f27174_20261124_102716`（中断于并发代码编辑；round1.json保留了教师首轮修复） |
| v3定稿run | `data/gjb_438c/runs/eiter_rule_induction_09f27174_20261124_103935`（result.json/report.md/全部trial packs；教师调用100%缓存命中） |
