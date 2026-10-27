# 40 · 一致性校验模块完整研究与重构计划

> 版本：3.2 | 更新：2026-10-21
> **会话范围**：接收QA对与另一会话按question召回的冻结SRS上下文，只研究召回之后answer一致性校验。检索器、上下文关联、实体聚合及召回指标由另一会话负责，不在本方案重构范围。
> 执行状态：QA模块facade、`POST /api/verify`原型接口及若干answer算子已有实现/测试；M0仅部分固化，正式数据与专家裁定未完成。91条QA的正式frozen context和gold尚未生成；40项是待裁定、待评测的方法重构清单，不是已实现检测器。

## 0. 用户确认的系统边界

```text
上游（另一会话）
  question → SRS上下文召回/上下文关联 → retrieved_context
                                                │
本会话（校验模块）                              ▼
  QA(question, answer) + retrieved_context → 一致性校验
                                            → verdict + type + evidence refs
```

本会话校验的是**answer是否符合question所问的内容，并被召回的SRS上下文支持**。图、表、正文是context里的证据来源。模块不比较表格与图片，也不替代上游召回器；上游context按冻结输入消费。

本轮执行优先级已明确为：answer-only数据算子、统一校验模块facade、旧pair检查隔离。taxonomy/基线/论文内容必须服务这三项，不以文档扩写替代可验证实现。

这一定义需要进一步区分两个相关但不同的对象：

- **QA忠实性**：answer是否忠实于召回的SRS context。
- **SRS内部一致性**：answer所总结/声明的SRS事实是否被context中其它SRS事实反驳。

二者可以共用question、answer、context schema，但gold和`refute`语义不能混为一谈。每条数据必须标注`verification_target`，M0时决定主任务是否只测QA忠实性，或同时包含SRS内部矛盾检查并分层报告。

## 1. 当前审计事实、设计提案与未决决策

| 类别 | 内容 |
|---|---|
| 已核实事实 | 当前AEE v1为1443条，labels为S783/R535/N125；数据保留answer与textual evidence，但没有原始QA的question字段。 |
| 已核实事实 | 旧`qa_mutation_ops.py`是premise/hypothesis pair变异，输出answer还会直接写入“一致/不一致”结论，存在标签泄漏。 |
| 已核实事实 | 旧MMQA mutation修改pair目录的text/table/graph并固定`expected_label=inconsistent`，不证明变异后的QA answer与context关系。 |
| 已实现prototype | `qa_models.py`、`qa_module.py`提供QA+frozen-context输入和统一结果/evidence-chain；question type router只给候选类型，非gold。 |
| 已实现并测试的算子原型 | `answer_mutations.py`覆盖数值等值/冲突、单位等价、显式术语/枚举反证、缩写展开、显式范围越界、数据流反转；未证明的NIE候选只进入manual review。算子测试不等于40项全覆盖或benchmark验证。 |
| 已实现审计 | `tools/audit_legacy_answer_mutations.py`将旧pair/MMQA/metadata-only生成器标记为quarantine；不删除历史文件。 |
| 已实现prototype | `QAConsistencyModule`已输出context freeze/hash、逐claim结果、evidence chain和diagnostics；只消费冻结context，不调用retriever。 |
| 已实现prototype | `tools/build_answer_mutation_candidates.py`只接受上游QA/context JSONL；model-visible input与private proof分离，unsupported candidate不自动贴NIE。 |
| 已核实事实 | `tools/eval_qa_e2e.py`有question/answer原始QA输入，但当前A1构造器把题目改写成“表格/图中包含X”的单来源断言；A3从旧QA output解析缺失列表生成gold。它们不等于用户指定的原样QA+冻结召回context契约。 |
| 已核实事实 | `family_evalset_v1`使用premise/hypothesis pair，C族主要是表格↔图片差异；不得直接重命名字段迁移到QA校验。 |
| 已核实事实 | strict40_eval是旧rendered_context/entity.occurrences二分类输入，235条、不是当前QA三态benchmark。 |
| 已核实事实 | 原40项是8 TERM + 10 PARAM + 11 LOGIC + 11 GJB，定义并未证明全部适合单一answer校验器。 |
| 设计提案 | 模块运行输入固定为`question + answer + frozen retrieved_context`，上下文保留原始QA轮次和实际送入校验器的内容。 |
| 设计提案 | B主标签暂定S/R/NIE，系统可另行abstain；GJB条目仍属于校验模块研究范围，但设独立子任务/分层，不默认排除。 |
| M0部分固化、仍待正式裁定 | 已明确本会话接收原始question、answer和上游冻结context；S/R/N的保守原则、answer-only算子不得改question/context等已有原型契约。复合answer聚合、verification target、scope边界及GJB子任务仍需项目负责人/领域专家基于正式样本裁定。 |
| 待决 | 用户所说“40项一致性校验”中的GJB项，是要检查QA answer对GJB要求的符合性，还是检查answer对SRS中GJB条款的忠实性？两者不是同一个gold任务。 |
| 待决 | answer主要是自然语言总结，还是每个40项检查都有结构化目标answer（如参数约束/追溯边）？建议数据同时保存原始answer与解析claims，主输入不泄漏gold claims。 |
| 待决 | question是否含规范性前提（“应符合GJB”），因此规则文本可被视为evidence context的一部分？建议把适用GJB规则作为显式context source，不暗中从知识库注入。 |

## 2. 模块I/O契约

### 2.1 推理输入

```json
{
  "instance_id": "QA-000001",
  "question": "根据召回的需求上下文，系统响应时间要求是多少？",
  "answer": "系统响应时间不超过200ms。",
  "retrieved_context": {
    "freeze_id": "ctx-...",
    "items": [
      {
        "evidence_id": "e1",
        "text": "系统响应时间应不超过0.2秒。",
        "source_type": "text",
        "source_ref": {"doc_id": "doc01", "section": "3.2.1", "page": 12},
        "scope_id": "response-time-doc01",
        "completeness": "open",
        "extraction_confidence": 1.0
      }
    ]
  }
}
```

问答模块只读取以上字段。不得读取gold、type label、origin、injected、mutation record、split或人工 rationale。

### 2.2 推理输出

```json
{
  "verdict": "support|refute|not_in_evidence",
  "applicable_check_items": ["PARAM-01"],
  "claim_results": [],
  "evidence_refs": ["e1"],
  "rationale": "...",
  "abstained": false,
  "abstain_reason": null
}
```

`abstain`是系统行为，不是第四种gold。覆盖率和selective risk单独报告；弃权不能从准确率分母中删除。

## 3. 三态判定规范候选

| 标签 | 定义 | 正例条件 |
|---|---|---|
| `support` | retrieved context支持answer对question的回应 | context蕴含answer核心claim，含预先规定的单位换算/同义等价 |
| `refute` | context对answer核心claim提供显式反证，或有证明完备的封闭范围将其排除 | 同一对象、属性、条件和作用域的互斥事实；或scope内可证明穷举 |
| `not_in_evidence` | 固定context不足以支持或反驳answer | 未召回、未解析、来源不完整、scope开放且未出现、answer过度具体 |

不得将“模型找不到”“VLM没有抽到”“context没包含”直接判成事实为假。`refute`只针对answer与当前输入证据的关系；除非benchmark明确采用封闭全文档证据，否则不表示完整SRS全局不存在该事实。

### 3.1 闭世界和context范围

- 闭世界由每条evidence的`scope_id + completeness + proof`定义，不由`table/figure/text`类型默认推导。
- 多evidence分别判断范围；一个封闭表格不使另一个开放段落变闭世界。
- 有问答外部规则时，规则作为独立context source提供并记录版本；不能在校验器内部隐式读取GJB知识库。
- context内部证据互相冲突时，输出可增加`context_conflict`诊断字段；最终QA标签按预先冻结的判定表决定，不能静默使用任一证据或“矛盾主导”。

### 3.2 QA answer原子化

- 原始QA作为评测实例保留；answer claim decomposition作为方法中间输出。
- 主分类集优先建立原子claim子样本，并保留`parent_instance_id`。
- QA级总体结果单独报告，整体聚合规则需在看test前冻结。
- 对“answer回答了问题但context没提及某细节”，该细节可判NIE；answer部分内容受反证时可判R，但需固定复合回答策略。

## 4. 40项逐项方法设计矩阵

下表是**设计映射，不是已完成实现清单**。所有项目都先判断它是否属于本模块、answer如何表达、冻结context需包含什么，再确定可用方法和数据状态。

方法缩写：`Rule`词典/规则；`Num`数值/单位/区间；`Set`集合/字段；`Graph`结构关系；`Logic`规则逻辑/SAT；`NLI`蕴含/矛盾/未知模型；`LLM`结构化提示语义判断；`QA`指question-aware answer relevance/intent parsing。

### 4.1 TERM（8项）

| ID | answer检查对象 | context必要证据 | 方法与基线 | 设计决策/数据门 |
|---|---|---|---|---|
| TERM-01 同义异名 | answer中的实体/功能名是否对应question所指实体 | 同一实体的规范名、别名定义或可定位描述 | Rule词典、实体属性匹配；Exact/BM25/Emb/NLI基线 | 异名本身不判refute；只有同指/不同指可确定时判S/R，否则NIE。真实别名gold待建 |
| TERM-02 同名异义 | answer对同名术语的含义/角色解释是否正确 | 同名术语定义、属性、上下文作用域 | 属性结构+NLI/LLM；NLI与统一prompt基线 | 需排除不同实体碰巧同名；需人工definition/scope gold |
| TERM-03 枚举集合 | answer列出的成员/数量是否被context支持 | 完整集合声明或有完整性证明的枚举证据 | Set membership/数量规则；Exact/LLM | 非穷举context缺成员=NIE，封闭枚举明确排除才R；来源解析完整性待标 |
| TERM-04 状态/告警术语 | answer对状态/告警名称、触发或含义的描述 | 状态定义、触发条件、告警字段 | Rule + 属性槽位 + NLI；词面/NLI/LLM基线 | 区分state/alarm/flag/event；仅名异不自动R，数据量待盘点 |
| TERM-05 指令名称 | answer中的指令动作、对象、角色是否正确 | 指令定义、接口或操作语义 | command slot matching + Rule/NLI | “启动/开启”可能同义也可能语义不同；需动作级标注 |
| TERM-06 量纲单位 | answer中的同一参数值/约束换算后是否成立 | subject、operator、value、unit、condition | Num归一+区间蕴含/Z3；数值规则/ NLI/LLM基线 | 0.2s=200ms为S；同一约束换算后冲突才R。单位表、容差需预注册 |
| TERM-07 信号接口命名 | answer所说接口身份/端点/协议是否符合context | interface name、source、target、direction、protocol | tuple/Rule/Graph；字段Exact/NLI基线 | 接口名差异本身不等于矛盾；需endpoint/role对齐，数据待盘点 |
| TERM-08 缩写代号 | answer把全称与缩写关联是否被context证明 | context中的显式缩写定义或稳定同实体共指 | acronym lexicon + local definition + NLI | 未定义缩写=NIE，不按相似度猜；缩写gold待建 |

### 4.2 PARAM（10项）

answer候选IR：`predicate, subject, object, operator, value, unit, condition/mode, measurement_scope`。context任一必要槽位不匹配时不得数值硬判R。

| ID | answer检查对象 | context必要证据 | 方法与基线 | 设计决策/数据门 |
|---|---|---|---|---|
| PARAM-01 时间约束 | 同一操作/阶段的响应、处理或等待时间 | 时间谓词、对象、阶段、operator/value/unit | Num区间/Z3；规则、NLI、LLM基线 | end-to-end与子步骤不可错配；参数声明抽取待核验 |
| PARAM-02 周期参数 | 同一事件/对象的period/rate | event、对象、采样/处理阶段、单位 | Num + predicate matching | 采集周期与处理周期不同；需事件scope标注 |
| PARAM-03 阈值边界 | 同一指标/等级/条件的threshold | metric、condition、operator/value/unit | Num区间蕴含/Z3 | 更强约束可能蕴含较弱answer，不一定R；冻结蕴含表 |
| PARAM-04 多源融合对齐 | 同一source set/阶段的alignment error | source set、fusion stage、误差定义、单位 | Num+source tuple+Logic | 真实数据可得性未确认；先盘点，无证据不合成扩规模 |
| PARAM-05 资源占用 | 同一资源和配置的CPU/内存/网络等约束 | resource、device/config、load condition、单位 | Num+scope gate | 设计上限与运行测量值可共存；按source type分层 |
| PARAM-06 值域 | answer声明范围或某值属于范围 | lower/upper、端点开闭、值单位 | interval relation/Z3 | 拆`range-vs-range`和`value-in-range`；若范围只来自外部规则则转GJB |
| PARAM-07 存储容量/保存时长 | 两个独立谓词：capacity；retention duration | 数据对象、存储配置/保存策略、单位 | Num/Logic | 原ID合并两个参数，拆子项；不得视作一个10条类型 |
| PARAM-08 同步守时精度 | 拆sync error、clock accuracy、holdover drift | 测量定义、时间窗口、stage、单位 | Num+definition matching | 原“精度”语义过宽；无真实样本前标needs_data |
| PARAM-09 降级阈值 | 同指标/模式的degrade trigger | metric、方向、threshold、degraded mode | Num+state Logic | 与GJB-11“是否有降级模式”分开；样本需工况对齐 |
| PARAM-10 故障持续时长 | 拆fault detection、alarm delay、recovery timeout | fault type、阶段、持续时长、触发条件 | Num+temporal Logic | 不同阶段时长不矛盾；先建事件谓词数据 |

### 4.3 LOGIC（11项）

| ID | answer检查对象 | context必要证据 | 方法与基线 | 设计决策/数据门 |
|---|---|---|---|---|
| LOGIC-01 模式切换优先级 | 同condition下mode priority/preemption | priority rule或完整状态转移 | Graph/Logic/NLI | 抢占要有条件；状态机缺边默认NIE |
| LOGIC-02 异常处置 | 某exception的action sequence/fallback | exception type、trigger、动作序列 | sequence/Logic/NLI | 重试后切备可共存；不能把不同异常混为冲突 |
| LOGIC-03 事件时序 | answer中的precedence关系 | 同一流程路径的节点/有向边/编号步骤 | Graph/partial-order/Logic | 分支/并行/循环显式表示；LCS仅基线 |
| LOGIC-04 数据流方向 | source→target及data object方向 | 端点、数据对象、边类型 | typed Graph/Rule | 控制流、反馈流、数据流要区分 |
| LOGIC-05 分支完备性 | answer声称分支/状态存在或穷举 | branch声明及completeness proof | Set/Graph+scope gate | 图未抽到分支=NIE，除非完整范围证明 |
| LOGIC-06 互斥控制 | A、B在同resource/condition下mutex或parallel | 互斥/并行规则、resource和condition | Logic/SAT | 需排除不同资源或场景 |
| LOGIC-07 切换原子性 | task switch atomic/interruptible属性 | 原子性、抢占、事务或状态转移证据 | Rule/Logic/NLI | 业务原子性与调度不可抢占分开 |
| LOGIC-08 冗余仲裁 | 主备/多源选择规则 | source role、fault condition、tie-break | Graph/Logic | 主备优先可随状态变化；真实证据待查 |
| LOGIC-09 权限访问 | role×action×resource×condition permission | role、动作、对象、允许/拒绝路径 | permission tuple/Graph/Rule | “能进入页面”不蕴含“能修改” |
| LOGIC-10 故障恢复 | fault type下自动/手动/回退恢复 | trigger、恢复状态、fallback path | state machine/Logic/NLI | 自动+失败后手动可以共存 |
| LOGIC-11 追踪重搜 | 触发事件下全量/增量search scope | trigger、数据范围、执行阶段 | set/scope Logic | 不同阶段全量与增量可并存，真实样本待查 |

逻辑类方法消费上游已解析文本化/结构化context，不负责VLM解析、图片关联或重建流程图。

### 4.4 GJB（11项，仍纳入40项审查但分成校验子任务）

用户要求40项作为一致性模块的候选范围，因此不在审查阶段直接删除GJB项。它们需先区分“QA答案忠实性/规则符合性/证据缺失”：

| ID | QA-answer校验定义候选 | 方法候选 | 标签/数据设计 | 未决点 |
|---|---|---|---|---|
| GJB-01 可测试性 | answer声称某需求具备可测试的条件/判据，context或显式提供的GJB规则是否支持 | testability schema + rule/NLI/LLM | 若question明确问符合性，使用C子任务标签；若answer复述SRS事实，用B三态 | “规则输入”是否随context一并提供 |
| GJB-02 故障容错完备性 | answer声称SRS含某容错需求/机制，冻结context能否证实 | rule/slot completeness | 有明确条款S；context封闭且明确缺项才R，否则NIE | 不适用系统如何标注 |
| GJB-03 安全访问控制 | answer声称某权限控制存在/满足规则 | permission slots + rule/NLI | 事实QA走S/R/N；合规QA走compliance标签并分层 | 系统边界/责任域 |
| GJB-04 审计日志 | answer声称记录哪些事件/字段/期限 | audit schema + rule | 同上；日志存在不等于全面合规 | GJB规则具体字段映射 |
| GJB-05 需求可追溯性 | answer声称需求ID到测试/章节/上级需求的具体映射 | ID exact/link graph/表行解析 | 具体映射可进入B三态；整体合规另标C | 当前SRS是否包含测试映射 |
| GJB-06 报警要素 | answer声称报警级别/位置/原因等要素 | alarm schema + rule | 规则字段任务单列；缺context字段不自动R | 按报警类型定义必需字段 |
| GJB-07 软件自检 | answer声称某启动/运行自检机制存在 | event/requirement schema + rule | 具体事实QA S/R/N；规则合规单列 | 自检适用性与责任边界 |
| GJB-08 掉电数据保护 | answer声称掉电时保护某类数据/恢复状态 | data scope + behavior rule | 事实支持/反驳与规则符合性分开 | 软硬件职责分配 |
| GJB-09 输入数据防护 | answer声称输入校验/过滤/错误处理行为 | input type/check/failure action slots | 按具体声明判断；外部规则合规子集单列 | 拆格式/范围/权限/恶意输入 |
| GJB-10 升级安全 | answer声称升级验证、回滚或恢复行为 | upgrade state/rollback schema + rule | 明确answer事实可三态；标准要求另做C标签 | 回滚是否普遍适用 |
| GJB-11 降级运行 | answer声称降级模式存在、能力或触发条件 | mode/capability/trigger schema | 模式存在性可B；规则是否要求另标C；阈值映射PARAM-09 | 与PARAM-09拆分 |

每项必须保留legacy GJB ID，同时增加`task_subtype=B_fact_verification|C_rule_compliance|needs_decision`，不得把合规标签偷偷映射为answer矛盾标签。

## 5. 方法管线（本会话）

```text
Frozen QA input
  → Q/A interpretation (利用question限定对象、意图、条件)
  → answer claim decomposition
  → type applicability / multi-label routing (40项taxonomy)
  → context evidence sufficiency & scope gate
  → type-specific verifier
       numeric/unit/range | term/entity | enum/set | order/graph | logic | GJB rule-evidence
  → NLI/LLM semantic fallback (只处理确定性方法未解决部分)
  → label decision + cited evidence + discrepancy/check-item outputs
  → evaluator
```

### 5.1 类型识别与类型判断分开

- `check_item`是gold分类标签，检测器不允许读取。
- 方法可预测一个或多个适用类型；类型预测单独评测。
- 40项可能重叠，taxonomy要支持multi-label和“不适用/证据不足”，不能强制每条只落一个类型。
- 先判断“question是否要求本模块可检查的事实”，再判断answer与context关系；不适用不等于NIE，也不等于正确。

### 5.2 方法适用矩阵（候选）

| 方法族 | 适用类型 | 不应承担 |
|---|---|---|
| Exact/alias/ID规则 | TERM-01/07/08、GJB-05、显式编号/引用 | 单独判断复杂语义矛盾 |
| Numeric+unit+interval/Z3 | TERM-06、PARAM-01~10中可结构化子项 | 变量subject/condition未对齐时强行求解 |
| Set/enum | TERM-03、部分LOGIC-05 | 从非穷举context的缺失推R |
| Graph/state/path | LOGIC-01~11的结构化子项 | 代替上游图解析或判断未抽到即不存在 |
| GJB rule engine | GJB适用规则子任务 | 把规则违规一律改成B的refute |
| NLI | 自然语言蕴含/显式矛盾/未知残差 | 把neutral当refute；猜scope completeness |
| LLM judge | 复杂answer/question/context语义残差 | gold生成器、无引用自由裁判 |
| BM25/BGE | 固定context内候选证据排序/grounding基线 | 单靠相似度判支持或反驳 |

## 6. 数据审计和构造方案

### 6.1 现有数据解释

| 资产 | 适用性 | 当前处理 |
|---|---|---|
| AEE v1 1443条 | 有answer与textual evidence，但缺原始question字段，且证据/gold/scope需审计 | 迁移审计集，不作为目标QA benchmark |
| `srs_alpaca.jsonl` | 保留instruction/input/output，可作为QA候选；部分input是锚点/表格说明而非真实retrieved context | 原始QA来源；需恢复并冻结对应召回context |
| `qa_e2e_a1/a3.json` | 有query-derived context的旧E2E材料，但A1原始question是表图互问，A3 gold部分继承旧output | 历史诊断/候选样本，逐条审查后迁移 |
| strict40 eval 235 | entity occurrences+rendered context二分类 | legacy detector集，不是新40项B benchmark |
| family v1 896 | premise/hypothesis六族 | legacy pair素材；不可字段改名迁移 |
| 旧Gold/注入集 | 有部分真实矛盾、变异和裁决材料 | 作为源事实/候选QA素材，重新构造冻结QA context和标签依据 |

### 6.2 Benchmark分层

- `real_observed`：真实QA/answer与真实context关系，人工确认。
- `real_derived`：由真实SRS声明确定性形成QA样本，独立报告。
- `controlled_mutation`：对answer或context做可追溯变异，变异实际出现在推理输入中，独立报告。
- `hard_negative`：合理差异、近实体、错误scope、同名异义、NIE难例。
- `rule_compliance`：GJB规则QA的独立子benchmark。

answer来源和构造标签只在private lineage保存，不进入model-visible input。

### 6.3 Gold流程

1. 冻结QA和实际retrieved context，保存逐条输入及hash。
2. 两名标注者独立拆answer claims、标适用40项、判S/R/N、标引用证据和scope依据。
3. 第三方仲裁；记录初标/分歧/最终理由。
4. 数值/集合/逻辑可用solver/程序辅助验证，但保留输入事实、规范化结果和proof。
5. 证据context缺失、非穷举、抽取不完整时默认NIE；必须单列“context缺证”而不反标SRS全局事实。
6. 对GJB规则样本，规则版本与适用性由专家/规则治理确认；不让LLM自行选择适用规则。

### 6.4 Split与泄漏

- 文档级隔离为主；必要时grouped CV，并预先固定fold。
- 同源SRS事实、answer模板、实体、图像、变异算子实例/正负镜像不得跨split。
- `question`模板也要检查；不能让40项ID或固定措辞作为标签捷径。
- 保存文档、源事实、实体、模板、图像、近重复和exact QA泄漏审计。
- 校准和prompt选择仅在dev；盲测test只运行一次主协议。

## 7. Baseline计划（同契约公平比较）

所有方法统一接收`question + answer + frozen context`。如方法不使用某字段，明确记录ablation；不得给某个baseline全文或额外证据。

| ID | Baseline | 输入/机制 | 主要问题 |
|---|---|---|---|
| B0 | Majority / label prior | 仅训练集label先验 | 退化下限 |
| B1 | Q-only | question识别类型/意图，不看answer-context关系 | 测type/模板偏差 |
| B2 | Lexical answer-context | token/entity/value overlap | 词面基线，不具备矛盾理解 |
| B3 | BM25-in-context + rule | 在冻结context内部选证据，再用显式规则 | 不调用外部检索，不测上游召回 |
| B4 | BGE similarity + calibrated classifier | answer/context相似度特征 | 相似度不能单独区分S/R |
| B5 | Zero-shot NLI | premise=context，hypothesis=answer(+question) | neutral/contradiction映射需校准 |
| B6 | Fine-tuned NLI | 仅使用train split微调三态头 | 检查训练数据和领域泛化 |
| B7 | LLM structured judge | 固定prompt、缓存、证据引用约束 | 预算和随机性需控制 |
| B8 | Type experts | numeric/Z3、set、sequence、GJB规则专家 | 只在预注册适用类型上触发 |
| B9 | Proposed verifier | question-aware decomposition + scope gate + type experts + semantic fallback | 完整方法 |

仅在冻结QA v2后注册B0-B9的具体模型、模型hash、prompt、阈值、token预算、缓存键和允许字段。本表是baseline设计，不表示当前已实现/已运行。

## 8. 指标和统计方案

### 8.1 主结果候选

- 样本级三态macro-F1：`support/refute/NIE`等权。
- 逐态precision/recall/F1、accuracy、混淆矩阵。
- taxonomy coverage：有有效测试样本/有足够支持数/可进入主宏平均的40项数量。
- 类型级宏平均：仅纳入达到预注册最小支持数的类型；同时公布纳入列表、样本数和未纳入原因。
- context evidence citation precision/recall与source_ref exact/relaxed accuracy。
- abstention coverage/selective risk；abstain不得从主指标分母移除。

`3bAcc`是三态macro-recall诊断指标，不等于三态balanced accuracy，也不能与旧pair总体bAcc直接声称可比。40项是taxonomy分层，不是40个模型类别；多类型时另测check-item multi-label F1。

### 8.2 区间与显著性

- 按document/source-fact group做cluster bootstrap，派生QA/变体随源组整体重采样。
- 方法比较采用配对cluster-bootstrap分数差；报告组数、每组规模和95%区间。
- 16文档下文档级区间可能很宽；可预注册source-fact组为敏感性分析，不能事后选较窄区间。
- 40项多重检验控制family-wise或FDR；低n类型只报告描述结果，不做强显著性claim。
- 若要报概率阈值/校准，校准只用dev；报告ECE/Brier和threshold selection protocol。

### 8.3 分层表

所有结果按数据层、三态、40项legacy ID/新predicate、问题类型、context来源和completeness分层。来源分桶只解释校验器在不同证据呈现条件下的表现，不代表方法负责召回或理解原始图片。

## 9. 消融、压力测试与方法对照

固定QA和context逐项做单因素消融：

1. full proposed verifier
2. 去question（只answer+context）
3. 去scope/completeness gate
4. 去type routing
5. deterministic experts only
6. NLI only / LLM only
7. 去结构化claim decomposition
8. context内部证据冲突与复合answer处理策略对照

压力测试包括：单位等价、较强/较弱区间蕴含、同名异义、合理条件差异、非穷举图/表缺失、多个证据块scope隔离、支持/反证证据并存、answer超出question范围、问答矛盾、输入context为空/截断、evidence引用错误、不同GJB适用规则。

## 10. 计划链路与Gate

### M0：会话边界与标签决策

冻结输入`QA + frozen retrieved context`、B三态语义、abstain、复合answer、证据内部冲突、B事实忠实性与C合规的关系。

**Gate**：决策表覆盖S/R/N/不适用/上下文冲突边界案例；不实现检索器。

**执行状态（2026-10-21）**：模块范围与`question + answer + frozen retrieved_context`输入边界已部分固化，三态保守判定原则已有文档和原型测试；M0尚未正式关闭。verification target、复合answer聚合、scope/完备性边界、context冲突处理及GJB事实核验/合规子任务仍需正式数据审查和项目负责人/领域专家裁定，不能据现有设计稿标记为已冻结。

### M1：40项taxonomy v2

逐项填充`knowledge/consistency_taxonomy_v2.json`：answer schema、question pattern、context证据要求、S/R/N规则、scope、方法族、baseline、gold方法、样本量、ready status。

**已完成（2026-10-20）**：`knowledge/consistency_taxonomy_v2.json`落地（快照`tests/test_consistency_taxonomy.py`）：40项全字段操作化——module_assignment为main_B×29+compliance_subtask×11（GJB-05/GJB-11标mixed可部分走B三态）；data_readiness为derived×8+needs_data×32；method_readiness无一validated（符合设计稿约束）；与scene1_qa_audit的tentative_check_items交叉校验通过。**注意：module_assignment/data_readiness仍待M0/领域专家人审裁定，当前为设计稿状态。**

**Gate**：40项均有去留和模块归属；不得要求全部进入B主任务或预定400条样本。（结构已达成；人审裁定未完成。）

taxonomy仍是设计映射，不是40项算子完成证明；当前仅有少量数值/单位answer-side prototype。

### M2：QA/context资产取证

盘点AEE、原始QA、qa_e2e、strict40、family、旧Gold及生成器。逐样本记录：question是否真实、answer是否原样、context是否来自上游冻结输入、标签是否能独立证明、taxonomy归属、需保留/重标/quarantine。

**进展（2026-10-20）**：完成场景1对方示例QA的首批取证：
- 定位91条对方提供的高质量QA（`docs/doc11/场景1-软件需求规格辅助生成场景补发数据/`，配套04数据统一访问服务SRS，即主数据集04号文档）；doc11目录内另一份“数据服务软件需求规格说明.docx”为某领域项目文档，与QA无关。
- `tools/audit_scene1_qa.py` 产出 `data/gjb_438c/scene1_qa_audit.json`（MANIFEST登记，快照`tests/test_scene1_qa_audit.py`）：91条中90条证据可定位（领域锚点/数值65535/异常流E1/表引用命中04号解析块），1条推理性问题需人工；family分布以事实核验类为主（功能/支持21、异常/错误19、接口/参数15等）；`tentative_check_items`为40项候选初稿待M1人审；`gold_verdict`全空，留给M3双标。
- 该91条是当前唯一确认的**对方提供真实业务QA**，是real_observed层的首选候选源；后续需上游会话按question生成正式冻结context，替换审计用锚点命中。

**Gate**：形成可审计数据适配清单；确认AEE缺失question的问题及可恢复比例。

**AEE部分已完成（2026-10-20）**：`tools/audit_aee_question_recovery.py`以确定性重放构建器（1443条answer/claim/provenance全等验证）产出`data/gjb_438c/aee_question_recovery.json`（MANIFEST登记，快照`tests/test_aee_question_recovery.py`）：
- **868/1443（60.2%）可恢复原始question**（srs_alpaca instruction；A1/C1占位符已回填caption）
- 574条family派生**无源question**（来自family_evalset premise/hypothesis，按设计排除）
- 1条C1为"假设"合成模板question
- 发现：构建器B1分支实际0命中（alpaca无"表头字段"连续子串）；A1-table因dedup塌缩254条（对应346原始行，92行冗余重复）

### M3：标注手册和pilot

每类至少抽取可用真实样本pilot，双人盲标question意图、answer claims、context evidence refs、scope/completeness、verdict和类型；评估agreement并修订指南。

**手册已完成（2026-10-20）**：`docs/srs_project/41_annotation_manual_pilot.md`（v1.0）——五步标注流程、三态决策树（D0-D3）、预注册换算/同义/合理差异表、04号真实判例10个（含对象错位/封闭枚举/强弱蕴含/复合answer边界）、GJB合规A/B情形分流、context冲突诊断、双标+仲裁+Kappa口径（κ≥0.75进M4）、9条质量红线。**pilot执行未开始**：待上游冻结91条question的正式retrieved context后开标。

**Gate**：refute必须有反证或闭世界证明；NIE与检索/解析缺失语义明确；分歧仲裁可复现。

### M4：Benchmark v2及冻结split

按真实观察/派生/变异/难例构建；doc/source-fact/template/image group隔离；记录输入hash、标签、scope和泄漏报告。

**Gate**：冻结样本100%含question、answer、context、source refs、gold basis；不可回源项隔离。

answer算子Gate：question/context不可变；变异必须出现在answer实际输入；gold必须有proof或进入manual review；旧pair/MMQA/metadata-only算子不得进入新集。

**answer算子状态（2026-10-21）**：`tests/test_answer_mutations.py`覆盖数值identity/conflict、单位等价、显式术语/枚举反证、缩写展开、范围越界和数据流方向反转；这些是有窄条件与proof约束的原型算子，不构成40项覆盖，也没有形成官方评测集。unsupported/NIE proposal没有自动gold，需人工复核。91条QA目前只有locator审计，正式frozen context、双标gold及由其生成的正式候选均尚未完成；不得以locator命中替代冻结证据。

### M5：Baseline注册与校准

注册B0-B9实现、模型版本、prompt、budget和阈值；所有方法只读取同一QA/context。dev用于阈值/校准，test盲测。

**Gate**：方法输入权限、失败行为、缓存键和评估脚本经审查。

### M6：主实验和统计

报告主三态macro-F1、逐态、类型宏平均、citation、cluster CI、coverage-risk、按数据来源结果和全部消融。

**Gate**：结果可由dataset/split hash和run id重现；小样本类型不夸大。

### M7：独立副任务/论文

决定GJB compliance是否独立副benchmark；ACDD仅作为独立来源差异任务。论文method/abstract/claim与冻结任务契约一致。

## 11. 40项全量设计表的后续交付

本文第4节已给每项初步任务形态，但不是最终oracle。M1的taxonomy JSON和配套人审表还需包含以下字段并逐项补齐：

| 字段 | 要回答的问题 |
|---|---|
| `question_pattern` | 问题问的是事实复述、比较、合规还是覆盖性？ |
| `answer_claim_schema` | answer能拆成什么谓词/槽位？ |
| `context_evidence_schema` | 哪种已召回证据足以判定？必须有哪些source refs？ |
| `label_rule` | 什么事实支持、什么显式反驳、什么只能NIE？ |
| `scope_rule` | 是否需要封闭范围？如何证明？ |
| `benign_variants` | 哪些单位、模式、配置、角色或粒度差异允许共存？ |
| `method_family` | Rule/Num/Set/Graph/Logic/NLI/LLM及fallback顺序 |
| `baseline_ids` | 哪些基线在该类有资格运行？ |
| `gold_method` | 人工、确定性规则、solver或组合？ |
| `data_counts` | 真实/派生/变异/难例各有多少，来源hash是什么？ |
| `readiness` | `ready/pilot/needs_data/needs_decision/not_applicable` |

在这些字段完成并由项目负责人审定前，不宣称40项覆盖、baseline矩阵冻结或macro-F1是最终论文主指标。

## 12. 校验器prototype状态与限制

- 新入口：`algorithms.consistency.QAConsistencyModule.verify(QAInput)`；不调用上游retriever，输入context freeze id和source refs，输出逐claim verdict、适用类型候选、证据链和context hash。
- 当前自动判定：question候选类型路由、精确引用/极性、部分数值区间与枚举claim；语义残差在未有validated三态NLI前保守NIE并标partial。算子单测通过只证明窄契约，不代表各类型方法已验证。
- `POST /api/verify`位于`server/main.py`，接收调用方提交的冻结context；`tests/test_server_verify_api.py`验证成功响应、必需冻结字段和旧`/api/check`的410行为。接口可用不代表全量40项检测、正式benchmark或生产部署已完成。
- 新answer mutation proposals只修改answer，question/context freeze不变；gold/proof放在private sidecar，不能喂给评测方法。当前CLI builder只接受上游frozen QA/context JSONL；尚未从91条QA locator audit生成正式候选，因为locator命中不等于context证据，91条正式frozen context也尚未生成。
- 新代码与审计：`tests/test_qa_consistency_module.py`、`tests/test_answer_mutations.py`、`tests/test_legacy_answer_mutation_audit.py`；这些测试锁prototype contract，不代表40项通过。

## 13. 本计划明确不做的事情

- 不设计或实现question召回、证据检索、跨章节聚合、图表关联算法。
- 不把来源模态对（表格↔图、正文↔表格）当成本模块的answer校验目标。
- 不把AEE v1、family v1、strict40旧分数合并成同一方法结果。
- 不预设40项全部适用B、每项都存在真实样本或每项必须凑齐固定正负配额。
- 不在问题、scope、label和baseline输入契约未冻结前开始训练/调阈值/报告主结果。
- 不把已测试的answer mutation原型算子包装成“40项生成器/检测器已完成”。40项是重构与验证范围，不是实现状态或覆盖率声明。
