# SRS一致性研究：项目边界与本会话计划

> 版本：4.0 | 更新：2026-10-20
> 项目整体含上游question召回/上下文关联和下游一致性校验。本会话只负责**下游一致性校验模块**；上游由另一会话维护。
> 项目入口：[project_guide.md](project_guide.md)；本会话完整方法/实验计划：[40_method_reconstruction_plan.md](40_method_reconstruction_plan.md)；数据资产审计：[39_project_architecture_audit.md](39_project_architecture_audit.md)。

## 1. 系统关系与会话范围

```text
QA question ──→ 上游检索/上下文关联（另一会话负责）──→ frozen SRS context
QA answer  ────────────────────────────────────────────┐
                                                       ▼
                                       本会话：一致性校验模块
                                       answer vs question + context
```

**本会话输入**：原始`question`、候选`answer`、上游按question召回的冻结SRS上下文及其来源/范围metadata。

**本会话目标**：判断answer是否回答了question、是否被context支持、是否被context明确反驳或证据不足；同时识别适用的40项检查类型，引用具体证据。

**本会话不负责**：question检索、跨章节关联、表格/图片关联、item聚合、检索Recall/MRR、图像/VLM/OCR解析器设计。上游context作为输入；只协商并验证接口契约，不重做其算法。

图、表、正文、追溯行是context中的证据来源。**校验对象不是表格和图片互相是否一致，而是QA answer在question限定下是否符合召回的SRS上下文。** ACDD/来源间差异可作为独立任务，不能并入本会话校验分数。

## 2. 本模块任务契约

### 2.1 输入输出

```text
verify(question, answer, frozen_retrieved_context)
    → verdict + applicable_check_items + evidence_refs + rationale
```

候选主标签：`support / refute / not_in_evidence`。

- `support`：context中的证据在question限定下蕴含answer。
- `refute`：context对answer给出明确互斥/否定证据，或完整封闭范围可以排除answer。
- `not_in_evidence`：冻结context不足以支持或反驳。未检索到、未解析到和非穷举缺项都不能自动判refute。
- `abstain`可作为模型行为单独报告coverage/risk，不作为隐藏的第四种gold标签。

`question`不能丢掉：它决定实体、属性、范围、时间、比较对象及用户真正询问的命题。复合answer的原子化、部分支持/反驳/未知时的QA级聚合，以及context内部矛盾的输出，均需在M0冻结。

### 2.2 输入公平性

校验器和所有baseline收到完全相同的`question`、`answer`、context内容、证据顺序、来源metadata和token预算。测试时不重新检索。可另设gold-context诊断集，但必须与实际上游context条件分表，且不称为端到端召回结果。

## 3. 40项范围

当前候选清单：TERM-01~08、PARAM-01~10、LOGIC-01~11、GJB-01~11。它们来自历史需求/注入设计，不等于40项都已被证明能作为同一种answer校验任务，也不承诺40项全部有真实数据。

每项都必须按QA校验模块重新定义：

```text
check_item
question_pattern
answer claim schema
context需要的证据事实
support/refute/not_in_evidence判据
scope/completeness要求
合理差异/领域等价规则
方法族与baseline
gold来源/构造证明
样本数与数据成熟度
```

TERM/PARAM/LOGIC多可成为answer事实核验子类型，但仍要检查实体、属性和条件能否对齐。GJB项也不预先排除：当question询问answer对某条GJB要求的符合性，且规则依据显式提供时，可纳入本模块的规则型校验；须在taxonomy中标记为合规子类，独立报告，不与事实忠实性子类混为一个未经分层的总成绩。GJB-05追溯关系可用具体QA验证映射事实；整体文档符合率则是另一种评测单位，不能和单QA样本混算。

两份`14_strict_40*`仅作为历史条目来源。40项逐项重构、算法适用范围和数据可用性见 [40_method_reconstruction_plan.md](40_method_reconstruction_plan.md)。

## 4. 方法架构（本会话）

```text
question + answer + frozen_context
  → question/answer解释与claim分解
  → 40项taxonomy适用类型预测
  → context证据对齐、scope/completeness门控
  → 类型化确定性检查（术语/数值/集合/顺序/逻辑/规则）
  → NLI/LLM语义残差
  → 三态判定、类型、evidence refs、解释
```

规则/数值/集合/逻辑通道是方法候选，不代表均已完成。Verifier不能自行猜测上游未提供的范围完整性；LLM不能独立生成gold；方法异常需记录为system error，不可静默记成NIE。

## 5. 数据与标注原则

1. 每条样本保留原始question、answer、实际冻结context和source refs；原子claims作为中间表示。
2. 按`real_observed`、`real_derived`、`controlled_mutation`、`hard_negative`、`GJB-compliance`分层报告。
3. AEE v1有1443条但缺question字段，是迁移审计材料，不是目标契约benchmark；family v1和strict40是不同输入任务，不可字段改名拼接。
4. Gold需指出支持/反驳的context evidence refs和label basis；双标注、仲裁与规则/solver证明留档。
5. 注入必须实际修改answer或context，且不得让构造器标签/类型泄漏到系统输入。
6. 按document/source fact/entity/template/变异家族隔离split；冻结split和leakage报告。
7. 召回上下文按给定输入处理；本会话不把上游召回失败计算为检索器指标，但会按校验模块标签语义判断当前context是否足以支持answer。

## 6. 评测协议设计原则

具体指标选择、baseline版本、统计方法必须在M0/M5经审查冻结。候选框架：

| 维度 | 候选报告 |
|---|---|
| 标签判定 | 三态macro-F1、逐态P/R/F1、混淆矩阵、accuracy |
| 40项类型 | 每类型样本数/三态支持数/类型F1；低样本类型不强作排名 |
| QA适切性 | question relevance/answer claim decomposition准确率 |
| 证据使用 | evidence reference准确率、context内证据定位、解释可支持率 |
| 弃权 | coverage、selective risk、按scope/completeness分层 |
| 数据来源 | 真实观察、派生、变异、hard negative、GJB子类分开报告 |
| 统计区间 | 按document/source-fact group配对bootstrap；同源派生样本成组抽样 |

不直接继承旧`macroF3`、`3bAcc`或family bAcc作为冻结主协议；选择理由、估计目标、小样本类型纳入规则和区间算法都需写入最终protocol。

## 7. 方法和数据审计事实

- `verify.py`当前是字符串级三态原型，不是已完成的question-aware 40项校验器；scope/refute语义需按新契约审计。
- 当前AEE评测只跑一个Verifier，旧AEE指标对应不同规模版本；它不能支撑方法/基线排名。
- 现有family六族、strict40和GJB合规样本都使用不同输入/标签；迁移必须逐条重建question、answer、冻结context和gold。
- 服务旧入口缺少`algorithms.check_engine`，不代表本会话校验器已服务化；服务迁移晚于schema、数据和验证器契约。
- 上游检索实现、指标和改造不在本会话计划中；接口字段不完整时记录为依赖风险，不接管其算法。

## 8. 阶段链路

| 阶段 | 交付物 | Gate |
|---|---|---|
| M0 范围/标签裁决 | QA输入、answer原子化、S/R/N、混合claim、scope、GJB子任务决策表 | 边界案例有可测试的人工判据 |
| M1 40项taxonomy | 40项操作化映射、question pattern、answer schema、context requirement、方法适配性 | 所有项有归属、可用性和数据状态；不强行全纳入同一成绩 |
| M2 输入资产审计 | 原始QA/context/evidence来源/旧集迁移清单 | 样本级回源、question存在性、context冻结和标签证据审计完成 |
| M3 标注pilot | 标注手册、双标/仲裁、歧义案例和agreement | 确认S/R/N及规则子类可一致标注 |
| M4 benchmark v2 | 分层QA/context数据、group split、leakage报告、MANIFEST | 每条gold有证据引用和label basis，测试集盲化 |
| M5 方法与baseline | deterministic/NLI/LLM/type-routed方法、统一输入适配 | baseline相同QA/context预算；prompt/model/阈值固定 |
| M6 实验/消融 | 三态、类型分层、证据引用、校准/弃权、group CI | 数字由hash/run复现，错误按方法桶归因 |
| M7 C副类/服务 | GJB规则子任务或verify API（需决策） | 独立标签；API不私自重新召回 |
| M8 论文 | 单一明确主线、可复现表格和限制 | 不混旧pair、检索、ACDD及新QA校验结果 |

## 9. M0必须由项目负责人裁定的问题

1. 本模块输出是否固定`support/refute/not_in_evidence`，UI/API是否另映射`consistent/inconsistent/unknown`？
2. answer主评测是否按原子claim拆分，还是原QA级复合answer为主？建议原子主、QA级次。
3. 问题要求符合GJB时，规则文本由question内含、冻结context提供，还是固定版本知识库作为显式第三输入？不得隐式调用。
4. GJB-01~11哪些是本模块规则型校验子类、哪些需单独合规标签？40项条目归属必须由用户/领域专家审定。
5. context内部同一事实既支持又反驳时，verdict与冲突诊断如何分开？
6. 主指标采用样本三态macro-F1、40类型宏平均或二者并列？最低类型样本门槛与cluster-bootstrap group key是什么？
7. test采用document holdout还是预注册grouped CV？16份文档下各方案的estimand需先写清。

在M0、M1完成前，不继续扩充旧AEE、不运行新方法排名、不声称40项覆盖，不把旧0.688/family bAcc/strict40 1.0作为当前QA校验模块成绩。
