# L1规则模板层技术架构详解

> 版本 v1.0 | 配套: 65号架构文档§2.2 | 实现: `algorithms/consistency/`（rulepack.py + evidence_statements/evidence_compiler + 九专家）+ `config/rulepacks/srs_gjb_v1.json`
> 本文讲清楚: L1管线每一步做什么、注册表思想的确切形态、GJB规则引擎的编译链与诚实覆盖率、配置与引擎的精确边界（三个暂缓项迁移后的最新状态）、每个设计决策的代价账

---

## 0. 一句话定位

L1是一个**确定性符号join层**：把冻结证据线性化为`(主体, 值, 位置)`注册表，answer声明与注册表做跨位置比对，矛盾信号从"分散在多处的各自无辜语句"变成"同键不同值的显式冲突"，产出参数/逻辑/合规类（PARAM/LOGIC/GJB族）的三态检测。

**它不是**：正则规则堆（九个专家共享一个注册表思想+一个规则库编译器，不是九套独立关键词清单）；也不是配置的被动执行器（join裁决、Z3求解、NW对齐、三态聚合这些"怎么判"锁在引擎里，配置只管"检查什么"）。

---

## 1. 管线总图（四个阶段）

```
输入: (Question, Answer, 冻结证据块E)

阶段① 表格线性化+证据编译       ← evidence_statements + evidence_compiler
  E的HTML表格 ──→ 行级短语句(EvidenceStatement) / 类型化表模式(TableSchema)
  "X的{字段}：{值}"语句 + 7表型签名分类 + Mermaid图解析

阶段② 注册表构建                ← 各专家内部（阶段①输出的消费侧）
  语句 ──→ {ID注册表|值域注册表|数值事实表|E1模板表|步骤序列|追踪行|合格性行}

阶段③ join裁决                  ← 引擎核心（"怎么比、怎么判"）
  answer声明 ──→ 主体聚簇/精确优先分层/字符重合配对/Z3三态求解/逐要素比对

阶段④ ClaimResult               ← 统一输出协议
  (verdict, check_item_candidates, evidence_refs, rationale, method, confidence)
  ──→ qa_module的per-claim融合(refute>support>NIE) + 跨claim聚合(refute>NIE>support)
```

关键设计：**先物化、后比对**——所有检查都发生在阶段②产出的注册表上，而不是在原文上反复做局部正则。这使每次冲突都能指认到`(证据块, 行, 字段)`。

---

## 2. 阶段①：表格线性化与证据编译

### 2.1 evidence_statements（行级语句化）

冻结证据57%是HTML表格。`linearize_evidence`按表型分四路：

| 表型判定（硬编码启发式） | 线性化路径 | 真实示例（04号） |
|---|---|---|
| 首行含"标识符+需求描述"或"方式名称+运行状态" | 能力表路径（位置保持，空序号列不左移） | `SQL访问功能的方式名称：平板、桌面、手持` |
| 首行含"单位+最大值/最小值" | 数据表路径：每行=主体列+`{主体}的{列名}：{值}` | `最大连接数的最大值：200`（06号表97） |
| 首行含"发送方+接收方" | 接口表路径 | 接口需求行级绑定 |
| 其余 | 用例表路径（字段行`Use Case名称：X`+表头zip） | `异常流E1：系统提示连接失败，用例结束。` |
| 非表格文本 | 句子切分（≥8字符保留） | `5 需求可追踪性` |

每条语句带`statement_id/evidence_id/field_name/scope_key/row_index`——scope_key（行主体）是后续所有join的主体来源。

### 2.2 evidence_compiler（类型化表模式+聚焦视图）

pack的7表型签名（`classify_order`顺序判定：能力→接口→值域→合格性→追踪→用例→兜底）把每张表编译为`TableSchema`（kind+规范列+行），列名经`canon_map`规范化（"Usecase名称"→"Use case名称"）。每个claim类型有`column_profiles`聚焦列集（identifier→[Use case名称,项目唯一标识符]），focus_views只把相关行列喂给下游。**换场景=换签名JSON**（doc06_v1已验证：06号表116逆向表头"本文档名称/标识"（无"的"）由doc06 pack规范化，默认pack不动）。

---

## 3. 核心机制：注册表思想

九个专家不是九套独立逻辑，而是同一思想的九个实例化——**先从证据构建带位置键的登记表，answer声明按主体聚簇后与表内同键条目比对**：

```
注册表条目 = (主体, 值, 位置)
  ID注册表:   ID → [(主体, 语句位置, 字段)]           id_join_expert
  值域注册表: (父主体, 字段) → {封闭值集, 行位置}       enum_join_expert
  数值事实表: (主体, 字段类) → [op+值+单位族, 语句位置]  numeric_z3_expert
  E1模板表:   (用例名, E编号) → (提示内容, 处置, 行位置) e1_expert
  步骤序列:   (用例名) → [(编号, 文本, 位置, 异常标记)]  sequence_expert
  追踪行:     (方向) → [(任务书章节, 本文档ID, 行位置)]  trace_expert
  合格性行:   (章节元组) → (需求名, 方法, 行位置)        coverage_expert
```

**双登记检测**正是这个思想的直接推论：同一个主体在证据的多处登记了不同的值（ID注册表两行同ID不同主体、值域表两行同主体不同值集），join时同键冲突即刻显形——这是17真实违例检出16/17、identifier族5/5的机制根源。

---

## 4. 六个检查族（机制+真实数据走查）

### 4.1 Z3数值约束族（numeric_z3_expert，PARAM-01/03/05/06/07）

**机制**：answer数值断言`(主体, op, 值, 单位)`经单位族换算（中文别名→srs_kb英文token→族基准，量纲不同先换算再比），与同主体同族同**字段类**的证据事实合取后交Z3：E∧C UNSAT→refute（附unsat core与SMT-LIB）；C∧¬E UNSAT→support（answer解集⊆证据解集）；其余SAT→NIE（部分重叠不裁决）。聚合声明（subject含"总/之和"等）走Σ(分量)联查。

**字段类join键（C06QA-008修复引入）**：数据表同一数据项的最大值/最小值/精度是**三个不同的量**。字段式事实携带量纲类（max/min/precision）；answer主体的字段限定词（"最大连接数的最大值"→核心主体"最大连接数"+类max）同样解析。join按类过滤：带限定的声明只与同类事实（或同向算子式事实）比对；无限定声明（值本身）与max/min/算子式事实比对；precision只与"X的精度"式声明同类。

**真实走查（06号表97，C06QA-008）**：
```
证据语句: 最大连接数的最大值：200 / 最小值：0 / 精度：1
answer:  "最大连接数的最大值为200" → claim(subject=最大连接数的最大值, eq, 200)
         → 剥离限定词: (core=最大连接数, class=max)
join:    只命中 max类事实 x≤200（min行ge0与精度行eq1被字段类隔离）
Z3:      E=[x≤200], C=[x=200] → E∧C sat; C∧¬E unsat → support
         rationale附 ev0(最大连接数≤200) + 完整SMT-LIB
```
修复前三行池进同一变量，eq200∧eq1撞UNSAT→伪refute。同形态还翻正了C06QA-018（r_value_swap：文档max=0/min=2，answer声称max=100→eq100只与le0比对→正确refute；修复前证据自身UNSAT→NIE掩蔽了矛盾）。跨文档det macro-F1 0.1524→0.2619。

### 4.2 E1模板+序列对齐族（e1_expert+sequence_expert，LOGIC-02/03）

**E1机制**：field_name含"异常流"的语句按`E条目头`切分（b207四条挤压在一个单元格也能切），`异常流(?P<id>E\d?)：(?P<prompt>...)(?P<ending>...)`解析出提示内容+处置。answer侧从提示动词（提示/显示/给出/返回/弹出）锚定声称，与scope用例的模板做三级匹配：exact→substring→keyword（双边去通用词后取**字符二元组**交集）。处置声称（继续/恢复 vs 结束/终止）与模板处置比对，语义反向→refute。

**触发-提示混淆判定**（`_trigger_swap_part`）：answer声称的"提示文本"在证据中仅作为触发条件出现（"如果X，提示Y"的X子句）→ refute——且仅当问题问的是提示文本本身（`prompt_q`模式）才是决定性矛盾，异常种类问题里同一措辞降级NIE（S1QA-016 vs S1QA-052锚点）。lenient-strict分支：非异常聚焦的顺带提及若在其他用例有文档登记→降级NIE（跨用例引用不硬驳）。

**真实走查（04号，S1QA-021/028锚点）**：
```
模板:    异常流E1：系统提示连接失败，用例结束。 → prompt=连接失败, ending=用例结束
answer:  "连接错误" → 去通用词(错误∈e1_generic_words)后剩"连接"，二元组{"连接"}
         ∩ 模板prompt去通用词(失败)后{"连接"} = {"连接"} → keyword匹配 → support（S1QA-021, silver=support）
answer:  "连接错误" vs scope用例(二维数组输出)E1模板"获取失败"
         → {"连接"} ∩ {"获取"} = ∅ → no → 与模板矛盾 → refute（S1QA-028, silver=refute）
```

**序列机制**：`(\d+)[.．、]`统一编号标点切步骤，answer步骤与主事件流步骤按字符重合≥0.28（det）或BGE句级≥0.60配对，NW全局对齐（gap罚分-0.5）检查顺序单调性；异常流位置基准10000保证其恒排在主流程后。编号跳变/换序→LOGIC-03。04号真实形态：`Actor的动作：1.应用软件调用数据库初始化接口输入相关参数；3.应用软件输出数据库初始化状态`。

### 4.3 ID注册表族（id_join_expert，TERM-07）

**机制**：证据侧两类绑定语句（"X的项目唯一标识符：ID"语句级绑定+节标题"3.2.1名称（ID）"）构建`ID → [(主体, 位置, 字段)]`注册表。answer声明（ID模式+绑定语句/32字符窗口主体提取）与注册表join：claimed (主体,ID)精确命中→support；同主体不同ID（注册表内或邻域窗口）→refute；裸ID出现→support。**精确绑定优先**：精确命中时跳过包含式主体的冲突检查（父子层级非双登记）。ID族前缀过滤（doc06 pack限定PZXQ-YXZCFW族）。

**真实走查（04号）**：
```
注册表:  SQL访问功能的项目唯一标识符：PZXQ-GN-SQLFW → {PZXQ-GN-SQLFW: [(SQL访问功能, 语句位置, 标识符)]}
answer:  "SQL访问功能的项目唯一标识符为PZXQ-GN-SQLFW" → (SQL访问, PZXQ-GN-SQLFW)
         精确命中 → support
answer:  同主体声明PZXQ-GN-SQLFW-SJXG → 同主体注册表两值 → 双登记 refute（DOC04真实违例形态）
```

### 4.4 枚举注册表族（enum_join_expert，TERM-03）

**机制**：值域注册表按`(父主体, 字段)`聚簇——封闭值域词表（方式名称{桌面,平板,手持}、运行状态{开发阶段,运行阶段}）+散文枚举句（"X包括A、B、C"）+能力表行值（按`(parent, evidence_id)`块隔离聚合，同父ID多表不并集）。answer成员集与注册表集合比对：缺成员/多成员→refute（成员级定位）；错字（编辑距离=1）宽容。DEV形态（"支持在A、B上运行"）独立窗口主体提取。

**真实走查（04号）**：注册表行`SQL访问功能的方式名称：平板、桌面、手持`；answer声称"平板和手持"→集合缺"桌面"→refute并列出缺失成员（enumeration族4/4检出的机制）。

### 4.5 追溯+覆盖族（trace_expert+coverage_expert，GJB-01/04/05/06）

**追踪机制**：追踪表方向由首列前缀"任务书"判定（正表任务书→本文档，逆表反之），行按`{方向}`解析为(任务书章节, 本文档名称/标识)对；正文claim的任务书章节号（`^4(\.\d+)+`）与表行做正逆向双向join——claim的映射在表内无行→缺失；表内两行同键不同值→双登记refute。非追踪注记（"不跟踪/不追溯/不追踪"）的行剔除。

**覆盖机制**（coverage_join）：三段流水线——①覆盖关系构建（合格性表行+章节标题事实+能力清单，全部从冻结证据推导，不读content_list）；②answer覆盖声明提取（范围声明"X至Y章节所有需求均有合格性方法"/全称声明/精确断言/GJB-04/06正极性条款声明，复用gjb_presence的封闭清单触发词）；③三项检查：范围内已知章节无合格性行→refute并列缺口清单；精确断言主体在能力清单但无合格性行→refute；GJB-06报警要素逐项比对（缺任一声称要素→refute）。

**真实走查（VIO-17，04号）**：
```
answer:  "3.1至3.17全部需求均规定了合格性方法"（范围声明, start=(3,1), end=(3,17)）
证据:    表80合格性行仅6行覆盖3.2.1~3.2.6；章节事实含"3.3 XXX""3.4 XXX"标题
判定:    3.3/3.4在声称范围内、无路径重叠的合格性行 → 覆盖缺口 → refute
         rationale列出缺口章节与已覆盖集[GJB-01]
```

### 4.6 GJB规则引擎族（gjb_rule_engine，GJB-01~11）——见§5专节

---

## 5. GJB规则引擎专节

### 5.1 编译链：检查逻辑100%从规则原文推导

```
knowledge/gjb_438c_rules_full.json（120条规则, 87条applies_to含SRS）
  → compile_rule: 规范句定位（必须/应/宜，过滤词内"应"如适应/对应）
  → 主语提取（跨文档主语SSS/IRS/SDD…判manual——单文档审计无法核验）
  → 支配动词（指明/描述/注明/列出/包括…长词优先）后的宾语短语
  → 「包括：」「如…等」枚举项 + a)b)c)子项整句
  → 分词清洗（剥功能前缀/动词前缀/的-短语/括号注解/ASCII枚举号, 泛称词表过滤）
  → CompiledCheck(patterns, source_anchor, cluster, quantified)
  → audit_document: 模式在证据语句上子串匹配
      全命中=satisfied；含量词（每条/每个/全部）封顶partial（存在性命中≠逐条覆盖达成）；
      部分命中=partial；零命中=violated；manual=不可编译（诚实标记）
```

句式分析器只含语言学模板与泛称词表，**不含任何GJB检查内容词**——规则层的知识源是标准本身（120条规则可逐条追溯到OCR行号），不是手编关键词清单。编译确定性：同输入同输出。

### 5.2 诚实覆盖率：87条中55可编译 / 32 manual

manual的32条中：26条跨文档规则（主语是SSS/IRS等其他文档类型）、6条规范句宾语无可提取内容词。**不假装可检**——manual规则单列在簇审计的`manual_rule_ids`里，不参与聚合，rationale带不可编译原因。

### 5.3 簇映射（GJ-02迁移后：rule pack的gjb.rule_clusters段）

11簇=taxonomy GJB-01~11，映射到20条规则引用（一条规则可服务多簇：GJB-RULE-041同属GJB-02/06/08/09）。每簇带**映射理由字段**（如GJB-04="GJB 438C无审计日志专项规则，以安全保密簇承载——034要求1.3描述使用相关安全保密要求…"）。簇裁决=best-of（satisfied>partial>violated，OR语义）。簇映射经`rule_clusters()`惰性读取（缺簇报可读ValueError不静默跳过）。

### 5.4 04号审计实测（frozen证据全量）

| 簇 | verdict | 命中/缺失模式（节选） |
|---|---|---|
| GJB-01 合格性 | partial | 命中：合格性方法/可追踪性/可靠性/测试性/维护性；缺：质量特性方面/合格性检验方法 |
| GJB-02 容错 | partial | 命中：安全性；缺：异常条件/错误处理/超限条件 |
| GJB-03/04/05/07/10/11 | partial | 各有部分模式命中（如GJB-05命中可追踪性，GJB-11命中空闲/活动/状态、缺降级） |
| **GJB-06/08/09** | **violated** | 报警要素/掉电保护/输入防护全部模式零命中（04号真实缺失，与taxonomy doc04_violation一致） |

answer侧校验：簇violated+answer称有→refute（如"本文档规定了掉电场景的错误处理需求"→GJB-09簇refute，rationale带GJB-RULE-041+附录J锚点+全部缺失模式）；簇有内容+answer称有→support；簇violated+answer称无→closed上下文support否则NIE（open证据不保证穷尽）。

---

## 6. 配置与引擎的精确边界（三个暂缓项迁移后的最新状态）

### 6.1 边界表

```
┌─ 配置(srs_gjb_v1.json, 换场景改这里) ──────────────────┐  ┌─ 引擎(通用逻辑, 永不改) ─────────┐
│ table_schemas      7表型签名+列语义+聚焦列画像          │  │ 注册表join+主体聚簇               │
│ extraction_templates  57个提取正则(逐字迁移)            │  │ 精确优先分层/字符重合配对/NW对齐  │
│ term_vocabularies  19个词表(含本次新迁10项)            │─→│ Z3三态判定+unsat core            │
│ join_params         7专家参数(e1/id/enum/seq/trace     │  │ HTML网格rowspan重建/Mermaid解析  │
│                     /numeric_z3/coverage)              │  │ claim类型路由+三态聚合语义       │
│ thresholds          14个阈值(0~1)                      │  │ scope定位/触发-提示混淆判定      │
│ gjb.rule_clusters  11簇映射(带理由) ←── 本次迁移       │  │ 字段类兼容判定+GJB_CHECKS封闭清单│
│ gjb_rule_library_path → knowledge/120条规则库          │  │ 句式分析器语言学模板             │
│ coverage词表/numeric词典 ←── 本次迁移                  │  │ coverage声明模式正则/单位token文法│
└────────────────────────────────────────────────────────┘  └──────────────────────────────────┘
```

### 6.2 三个暂缓项迁移纪要（64号盘点CV-01/NZ-01/GJ-02）

| 暂缓项 | 迁移内容 | 留引擎部分与理由 |
|---|---|---|
| CV-01 coverage词表 | `_QUALIFICATION_TARGETS`(6词,有序)/`_GENERIC_SUBJECTS`(19词)/`_ALARM_ELEMENTS`(5组标签+同义词)→term_vocabularies+join_params.coverage；`_ABSENCE_RE`极性词表与gjb_presence共享同一配置源（**解耦了coverage→gjb_presence的词表import**） | `_RANGE/_UNIVERSAL/_HEADING`等声明模式正则（与极性裁决语义强耦合，行为保持优先） |
| NZ-01 numeric词典 | `_CN_UNIT_ALIASES`(7)/`_EXTRA_UNIT_FACTORS`(13)/`_FIELD_NAME_OPS`(7,键序即字段alternation序)/`_AGGREGATE_MARKERS`(5)→join_params.numeric_z3 | `Z3_TIMEOUT_MS`（求解器资源限制，同SQ-06/07算法参数）；`_UNIT_TOKEN`单位token文法（抽取语法）；`_FIELD_CLASS`（字段类join语义，本修复引入） |
| GJ-02 GJB簇映射 | `RULE_CLUSTERS`常量→gjb.rule_clusters段（11簇/20规则引用/映射理由，程序化提取逐字一致） | —（句式分析器GJ-03原本就留引擎） |

**行为保持验证**：迁移后91QA 0.9121/0.7212、违例16/17、跨文档det 0.2619逐位不变（全部重跑确认）。

### 6.3 srs_gjb_v1.json实测内容清单

7表型签名（capability/use_case/interface/value_domain/qualification/trace/generic）· 57模板正则 · 19词表（e1族4/enum族5/id族1/seq族3/trace族1 + 本次新迁5：gjb_absence_words(23)/gjb_presence_words(25)/gjb_rule_presence_words(21)/coverage_qualification_targets(6)/coverage_generic_subjects(19)）· join_params 7专家（e1/id_join/enum_join/sequence/trace/numeric_z3/coverage）· 14阈值 · gjb段11簇 · gjb_rule_library_path→120条规则库。

### 6.4 配置化覆盖度更新

64号盘点60项硬编码域知识：原48项已迁入+本次10项（coverage 5+numeric 4+GJB簇 1）=**58/60（≈97%）**；仍留代码的为分层原则判定的算法项（coverage声明模式正则簇、Z3_TIMEOUT_MS、单位token文法）——它们是裁决语义/求解器参数/抽取语法，不是"因文档而异"的域知识。

---

## 7. 诚实账（设计决策的收益vs代价）

| 决策 | 收益 | 代价 |
|---|---|---|
| 注册表先行（先物化后比对） | 双登记类冲突检测率1.0；每次判定可指认(块,行,字段) | 内存里持有全量行级事实；join键设计错一处影响整族（字段类缺失正是C06QA-008的教训） |
| Z3三态而非区间算术 | 单位换算/聚合/unsat core可溯源；部分重叠诚实NIE不硬驳 | 求解器依赖+500ms超时防线；support语义=answer⊆证据（answer弱于文档→NIE，非直觉） |
| 字段类join键（本次修复） | max/min/精度三量不互撞；C06QA-008/018翻正 | 裸形"上限/下限"不剥离（防"告警上限"式数据项名误伤）→该形态按值本身处理（保守NIE方向） |
| 规则库驱动编译（非手编清单） | 知识源=标准本身；120条可追溯OCR行号；换标准版本重编译即可 | 32条manual诚实不可检（26跨文档+6无可提取内容）；量词规则封顶partial |
| 配置化（rulepack） | 06号变体只需换JSON（doc06_v1验证）；行为保持可逐位验证 | 配置本身仍需人工归纳（正则文法不跨文档迁移——65号已声明的结构性gap）；专家侧_build_config校验在首次调用才报错 |
| coverage声明模式留引擎 | 极性判定与模式强耦合，拆分行为风险大 | 06号式变体声明（"均须规定"）需改代码而非换配置 |
| presence词表双版本（25全表/21引擎子集） | 引擎子集缺"应/自动*"是行为保持的历史校准结果 | 同一语义两份配置清单，新增词需同步两处（迁移时已把两份都显式外置，漂移可审计） |
| 三态聚合refute>NIE>support | 保守方向：任一NIE claim阻断support | answer弱声明（"不能超过此限值"类总结句）会把support压成NIE——由dominant_70变体在P1研究中处理 |

**双登记定律的边界声明**（65号§2.2，实验依据）：L1符号层专责**证据内部**跨位置冲突（双登记，检出率1.0）；answer侧单边破坏归语义层（394注入对照检出0.05-0.53）。L1不是万能检测器——它的高检出率集中在"证据多处登记互相矛盾"这一形态上，answer侧幻觉/单边篡改要靠L2/L3。

---

## 8. 已知问题与演进路径

| 已知问题 | 现状 | 演进路径 | 代价 |
|---|---|---|---|
| 跨文档正则文法不迁移（04→06泛化落差） | det 0.2619（修复后）；06号narrative族大面积NIE | ①per-doc pack已就位（doc06_v1）②正则→语义匹配升级（05号路线）③pack生成工具化（从content_list统计表头归纳） | 配置归纳成本；语义匹配引入非确定性需置信门控 |
| 量词规则partial封顶 | GJB-RULE-037"每条需求应注明合格性方法"存在性命中≠逐条覆盖 | **逐条覆盖归coverage_join**（架构选择：GJB-01范围声明的逐章缺口检测已就位，VIO-17验证） | 两个通道各管一半语义，rationale需互指 |
| evidence_statements表型启发式硬编码 | 线性化层的表型判定（"单位+最大值"→数据表等）与pack的table_schemas签名重复，改pack不影响线性化 | linearize_evidence改从pack取签名 | 行为风险大（所有专家吃statements），需91QA逐位回归护航 |
| 字段类覆盖不全 | 配置新增字段名（field_name_ops）缺省类""（值幅度类） | 新字段若属max/min/precision量纲需在_FIELD_CLASS登记 | 缺省方向保守（并入值幅度类join） |
| 裸形限定词不剥离 | "X上限"式数据项名保护 | 无（有意为之） | 同形态限定声明按值本身比对（NIE方向） |
| GJB-04簇语义承载弱 | GJB 438C无审计日志专项规则，以安全保密簇承载 | 规则库扩充（人工补审计专项规则） | 知识源偏离"纯标准推导"原则 |

**配置化架构的意义**：这些升级动的是引擎局部或配置生成，不是推倒重来——doc06_v1演示了换配置不换代码，本次三暂缓项迁移演示了词表/词典/簇映射的增量外置（每次迁移带行为保持验证）。

---

## 9. 与L0 NER层/总体架构的互引

- **L0（66号文档）**：L0产出TERM族（01/02/05/07/08）的术语类检测，其文档词典是**运行时归纳**（从证据学用例名/接口ID）；L1的注册表是**声明式物化**（阶段②一次性构建）。两层共享"先建表后比对"的形态，但L0的表来自文档特有实体（每份SRS不同），L1的表来自GJB结构化模板（表型跨文档同构）——这正是L0配置（srs_scene1.json）与L1配置（rulepack）分层的原因。TERM-07在两层均有活跃通道（L0实体层ID族比对+L1 id_join注册表），同claim_text的分歧由per-claim融合仲裁。
- **总体架构（65号§2.2）**：L1在级联中的位置=确定性前置层（零成本、refute精确率0.83），残余claim交给L2 NLI（本地）与L3 LLM（路由升级）。L1把可形式化的检测做完，L2/L3只处理L1声明的"semantic_unresolved/conservative_unresolved"残余——C1残差原则：已裁决的claim永不进LLM。
- **设计文档（64号）**：配置化的分层原则、盘点表与行为保持铁律的原始设计；本文§6是其实施后的最新状态回填（三个暂缓项已迁移，覆盖度58/60）。
