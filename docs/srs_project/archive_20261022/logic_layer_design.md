# 逻辑层一致性校验——模块设计文档

> 定位：三层检测（语法/语义/逻辑）的第三层完整形态。现状是初级版
> （Z3数值区间+ORDER_CONFLICT），本设计把"因果/条件抽取、依存句法、
> 规则基座可执行化、LTL时序、逻辑图谱"五个缺口归并成一条编译管线
> 建模。
> 姊妹篇：`context_feature_design.md`（召回/特征）——本文是逻辑层延伸
> 成文：2026-09-13

---

## 1 统一建模：文档→逻辑程序的编译管线

散落的技术点（依存句法/信息抽取/因果识别/知识编译/规则引擎/时序校验/
区间代数/逻辑图谱）按数据流归并为一条管线，与κ编译器同构：

```
文档三模态(文本/表格/图)
   │
   ▼ 层1 声明抽取: 依存句法基座 → LogicalStatement(5类声明)
   │
   ▼ 层2 逻辑程序编译: 声明→SMT公式(Implies/LIA) + GJB规则→可执行谓词
   │
   ▼ 层3 推演判决: Solver.check()/unsat-core + LTL检验 → 判决带(q+溯源)
   │
   ▼ 层4 逻辑图谱: 声明作边进graph_store(LOGIC节点) → 冲突定位沿图传播
```

**建模原则**（与κ一致）：抽取层只字面结构化（句法触发词+依存标记，
不做语义猜测）；语义判断全部交给求解器；每条声明带provenance——
unsat-core返回的冲突子集能直接定位到"哪章哪表哪图"。

## 2 层1·逻辑声明抽取

### 2.1 声明类型学（核心schema）

```python
LogicalStatement = {
    "kind": "constraint" | "causal" | "conditional" | "mutex" | "temporal",
    "subject": "存储容量",
    "predicate": {   # 按kind分形态:
        # constraint: {op:"ge", value:256, unit:"GB"}          [已有κ_P]
        # causal:      {cause:"链路中断", effect:"切换备份"}
        # conditional: {precond:"初始化完成", obligation:"允许写入"}
        # mutex:       {a:"手动模式", b:"自动模式"}
        # temporal:    {event:"E2异常", anchor:"步骤3", rel:"after"}
    },
    "provenance": {doc, section, modality, sent_idx},
    "polarity": "doc_supports" | "doc_violates" | "unmentioned",
}
```

三值真值（polarity）是关键设计：**"文档未提及"不进矛盾**——防止
"未说明"被误报为违反（RE域经典假阳性源）。

### 2.2 依存句法基座（HanLP挂κ_P）

- **动机**：①因果/条件抽取需要句法——触发词（若/则/当/一旦/否则）
  必须配依存标记（条件从句advcl、因果连词）才能切干净前提/结论；
  ②参数名定界（param_hint）的老问题："进行标准转换速度"三种写法
  是否同一参数，正则做不稳，句法主谓宾（nsubj-obj路径）可定界
- **接口**：`hanlp.parse(sent) → {deps, roles}`；κ_P在现有五元组
  之外新增causal/conditional/mutex/temporal四类抽取（触发词表+
  advcl依存过滤）
- **抽取规则示例**："若数据库连接正常，系统应完成数据同步"
  → conditional{precond:数据库连接正常, obligation:完成数据同步}

### 2.3 表格/图侧的声明来源

- κ_T：用例表的前置条件列（已有）→conditional；步骤序列→temporal
  （before关系）；异常流表→causal（触发事件→处置动作）
- 锚点图：边方向→temporal；状态图的迁移边→temporal（状态序）；
  流程图分支互斥（同源多出边标"或"）→mutex

## 3 层2·逻辑程序编译

### 3.1 声明→SMT/LTL编码表

| 声明 | 编码 | 引擎 | 状态 |
|---|---|---|---|
| constraint | `Real(p) >= v`（LIA，单位归一用srs_kb单位族） | Z3 | ✓已有 |
| conditional | `Implies(P, Q)` | Z3 | 新 |
| causal | `Implies(c, e)` ∧ 时序上`Before(c, e)` | Z3+序约束 | 新 |
| mutex | `Not(And(a, b))` | Z3 | 新 |
| temporal | `AG(数据写入 → EF 提交成功)` | LTL检验器 | 新 |

### 3.2 规则基座可执行化（GJB120条）

```python
Rule = {
    "id": "R-0082", "source_ocr_line": 1234,        # 溯源字段不变
    "pattern": "capability_table",                  # 作用的IR对象类型
    "predicate": lambda kt: len(kt.caps) >= 1 and ids_unique(kt),
    "violation_type": "id_inconsistency"            # 进Δ类型学
}
```
- 本质是17号UML检测器套件（9图谓词，F1=0.9943）的**推广**：从图
  谓词推广到全IR对象（表型/章节结构/ID体系）
- 属性文法路线（deep_technical设计稿）：解析错误本身成为可报告的
  语法层不一致（"步骤3有编号无内容"=GJB R-007直接实例）

## 4 层3·推演与判决

### 4.1 可满足性+unsat-core（冲突定位）

- `Solver.check()` → unsat=确证矛盾（已有实证：存储56GB vs ≥1TB，
  73组约束6个真矛盾）
- **unsat-core**（Z3原生，enable unsat_core）→ 返回**最小冲突声明
  子集**：冲突报告从"有矛盾"升级为"这3条声明互斥"——每条带
  provenance→直接定位文档位置（哪章哪表哪图）
- 增量求解：新声明`push/pop`不重跑全量（在线校验的性能保障）

### 4.2 LTL时序校验

- 流程图锚点抽象为**Kripke结构**（节点=状态，边=迁移，标签=事件）
- 检验性质公式；graph_invariants的三个检测器本来就是LTL特例，
  做形式化升级：
  | 现有检测器 | LTL性质 |
  |---|---|
  | D_cycle环检测 | `AG ¬cycle` |
  | D_topo拓扑序 | `AG(a→b边 ⟹ ¬可达b→a)` |
  | D_branch分支覆盖 | `AG(decision → (EF branch₁ ∧ EF branch₂))` |
- 新性质（GJB典型）："异常流终态可达"=`AG EF 正常终态`；
  "每条异常流有处置"=`AG(E异常 → EF 处置完成)`

### 4.3 判决汇入黑板

- Z3 unsat → q=1.0（确定性FACT）
- LTL违规 → q按性质强度（AG违反=1.0，EF违反=0.8）
- 进`detection_verdicts`判决带（q≥0.7 report/≤0.3 pass/弃权带不变）

## 5 层4·逻辑图谱（LOGIC节点进graph_store）

声明作为边进graph_store（第7类节点）：

```
参数节点 --约束边(≥256GB@3.10.1)--> 参数节点
实体A    --因果边(触发@3.2.1.3)--> 实体B
状态节点 --时序边(before/after@图5)--> 状态节点
规则R    --适用边--> 表型/图型节点
```

价值：**冲突定位沿图传播**——unsat-core的声明→图上的边→边两端
的文档位置→冲突报告自带跨模态证据链（含来源与章节）。图谱同时是
第二部分"逻辑图谱重构"的落地：κ编译产物+声明抽取产物统一为图。

## 6 落地路线与验证路径

| 优先级 | 任务 | 工作量 | 验证金标 |
|---|---|---|---|
| P0 | 因果/条件声明抽取+Z3编码 | ~1周 | 15号注入语料LOGIC-01/02/03+真实矛盾（存储56GB vs ≥1TB） |
| P0 | unsat-core冲突定位 | ~2天 | 6个已知真矛盾的最小冲突集核对 |
| P1 | 依存句法基座（HanLP挂κ_P） | ~3天 | 50条句法抽样人工核对+param_hint一致性对比 |
| P1 | 规则基座可执行化 | ~2周 | 17号UML检测器回归+F1保持≥0.98 |
| P2 | LTL形式化（invariants升级） | ~1周 | 373结构回归（环/拓扑/分支结果不变） |
| P2 | LOGIC节点进graph_store | ~3天 | 声明边计数+溯源完整率 |

## 7 与现有系统的接口

- **上游**：κ_P/κ_T/锚点（context_feature_design §3的特征输出）
  是声明抽取的输入；句法层是κ_P的新前置
- **黑板集成**：logic_agent升级为消费LogicalStatement；判决进
  detection_verdicts（与NLI通道、Tier1分歧并列成为第三类证据）
- **复用**：provenance体系全套；srs_kb单位族（约束归一）；
  Z3求解器（logic_checker_v2的"绝不信任z3_verified元数据"原则保持）

## 8 已知风险与不完备

| # | 风险 | 缓解 |
|---|---|---|
| L1 | 句法抽取的召回率（"若/则"以外的隐性条件表述） | 触发词表+LLM辅助分支（走缓存）；先召回后精度 |
| L2 | 声明实体未对齐（"手动模式"vs"手工模式"跨声明不同名） | 声明的subject进term_checker同义词归一再编码 |
| L3 | LTL状态爆炸（大流程图性质检验） | 锚点图已骨架化（3757节点级）；性质限AG/EF一类 |
| L4 | polarity判定的"unmentioned"歧义 | 三值设计本身；弃权带兜底 |
| L5 | 因果≠相关（文档中的因果连词可能只是时序叙述） | causal声明降权（q上限0.8），与temporal互证 |

## 修订记录

| 日期 | 修订 |
|---|---|
| 2026-09-13 | 初版：四层管线建模（声明/编译/推演/图谱）+落地路线 |
