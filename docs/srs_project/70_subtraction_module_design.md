# 70 证据减法模块设计与评测协议 v2：三级过滤 × 反循环金标

日期：2026-10-28 | 状态：设计定稿（三agent并行设计综合）| 取代69号的评测构造

---

## 一、承认：69号的评测构造是错的

```text
69号做法: 从S1原子冲突对(自产候选)采样48对 → 人工标注 → 评NLI门控
诊断:     被评对象与标签来源同源(循环构造), 标签混入了抽取质量
正确任务: 检测项 → 召回top-50 → [减法模块] → 精选证据 → NLI裁决
          评的是"池质量"与"裁决提点/掉点", gold锚定在文档级事实
```

**用户给出的三个池污染源（减法要删的三类坏证据）**：

| # | 问题 | 文献锚点 | 现象 |
|---|---|---|---|
| 1 | 错误scope的干扰证据 | Dong 2021式(待核对,近邻:AmbigQA/EntityQuestions) | 查"BLOB插入"召回"数据库初始化"证据——文本相似但实体不对 |
| 2 | 粒度错配 | SumMaC 2022 | NLI句级训练，整行/整段直入失效；文档侧粒度必须≥声明侧 |
| 3 | 检测项特异性 | 文献空白(本文贡献) | TERM-03枚举需要能力表("包括"句+表行)，LOGIC-02异常需要用例表(E1行+动作约束列)——通用相似度区分不了"实体对但形态缺" |

**架构缺口**：精排/重排=排序(ordering)；缺的是**减法(subtraction)**模块。

---

## 二、减法模块设计：Evidence Subtractor

### 2.1 定位：软评分原型的硬否决进化

代码库已有软评分雏形（本设计是其确定性升级）：
- `deq_pipeline.py` E0/E1（scope/form/density加权——只软排序，不删）
- `evidence_compiler.py` focused view（粒度工程雏形）
- `atomizer.py` scope_hint（表行首格=作用域）

**减法 = 三谓词合取：**

```text
keep(e) ⟺ F1(e, q) ∧ F2(e) ∧ F3(e, 检测项i)
任一失败 → 删除 + RemovalRecord{stage, reason_code, signals}
```

### 2.2 形式化：检测项→证据形态合同

```text
检测项 i → 合同 C(i) = ⟨K_i表型集, R_i行角色集, F_i字段集,
                        M_i标记词, G_i粒度界, n_i最小载体数⟩

证据单元 e → 形态向量 σ(e) = (source_kind, table_kind, row_role,
                              field_name, enum_score, has_E1,
                              长度, 句数)
```

**合同来源**（不新建taxonomy，复用现有）：
- `consistency_taxonomy_v3.json`：40项检测项（TERM/LOGIC/…），已含
  `cross_modal_pair`与`doc04_evidence`字段
- `DETECTION_EVIDENCE_REGISTRY`：现有40条无类型dict → 升级为冻结合同
  JSON（`config/evidence_contracts_v1.json`，受MANIFEST保护+快照测试）
- **与QualityContract的关系**：合同=QualityContract.evidence_obligations
  （六路义务字符串）在**检索期的实例化**——ob_id同时出现在domain层
  义务串与合同JSON，同一机制两层

### 2.3 三级过滤器

**F1 scope过滤（删Dong式干扰）**——三信号级联：

```text
(1) 领域词硬约束: 查询实体集E(q)(复用_extract_question_entities)
    域词(PZXQ-*/BLOB/SQL等)不在证据文本
    (含"过程/操作/时"后缀剥离与4字前缀回退) → 删 scope_mismatch
(2) scope键绑定: 证据scope键(用例名表头/表行首格/首个ID,
    复用atomizer行首单元格逻辑) 与claim的scope_hint双向包含
(3) entity_hits/|E(q)| == 0 且无overlap → 删; < 0.15 → 降权不删
护栏: E(q)为空或全停用词 → F1直通(防误删)
```

**F2 粒度过滤（解SumMaC式失效）**——NLI可消费性=句级原子性：

```text
默认粒度界 G = {句数≤2, 长度≤160字}
超界处理序:
  (a) 枚举载体(分隔符≥2或含"包括") → 按、；切成员语句, 保留计数
  (b) 普通粗文本 → 句子级切分(复用_linearize_text)
  (c) 无边界不可切 → 删 granularity_too_coarse
整表/整段禁止直入NLI, 必须先经focus(行/句级)
SumMaC方向性检查: premise/hypothesis长度比>3且premise多句 → 强制拆分
子句带split_from链; 父块全部子句被删才整块删
```

**F3 形态过滤（本文新贡献，删"实体对但形态缺"）**：

```text
硬条件(全满足才keep):
  table_kind ∈ K_i (非空时)
  row_role/field ∈ R_i ∪ F_i
  例: TERM-03需enum载体(enum_score≥2或含"包括"句)
      LOGIC-02需field∈{异常流E1, 动作约束, 前置条件}的行
违反 → 删 shape_violation:
  子类 missing_structure = 实体对但无所需结构  ← 通用相似度测不出的
  子类 wrong_kind       = 形态整体错误(正文 vs 用例表行合同)
M_i标记词只加权不否决(防词典覆盖不足误删)
n_i最小载体数在包级检查(不足=义务不满足, 不是删证据)
```

### 2.4 输出契约：EvidencePack

```json
{
  "kept": [ ≤10块/≤25语句:
    {"evidence_id", "statements", "granularity_class",
     "matched_obligations", "role": "enum_member_source|E1_row|premise_candidate",
     "score", "provenance": "owner→block→row/句", "split_from"}],
  "removed": [ 每条带:
    {"evidence_id", "stage": "F1|F2|F3",
     "reason_code": "scope_mismatch|granularity_too_coarse|shape_violation.*",
     "detail", "signals"}],
  "obligation_coverage": {"item": "satisfied|unsatisfiable"},
  "stats": {}
}
```

**`unsatisfiable`→弃权路由**：义务不满足时不硬喂NLI，填
QualityContract.abstain_policy——**减法的下游价值核心**：
三态裁决(一致/不一致/证据不足)中"证据不足"的正确来源。

### 2.5 集成点

- 主点：`qa_module.py:394` use_deq分支：subtract(question, answer,
  request.evidence, I) → EvidencePack，kept喂E2/statement_alignment与L2 NLI
- 次点：`evidence_recall/pipeline.py`精排后可选scope快筛(F1+F2)压缩下游token
- 实施前提：**统一证据身份层**——URE块(`srs_chunks.json`, chunk_id=
  `doc_T0004_0`式)与冻结QA证据块(`block-000NNN`式)是两套ID，先建映射

---

## 三、评测协议 v2（反循环）

### 3.1 反循环三原则

```text
① gold锚定文档级事实: 标注员面对全文档(不见top-50), 按协议
   "删掉该块裁决依据受损"准则从全文枚举检测项的最小充分证据集
② 检测项不得来自被评系统输出(S1候选/NLI判定)
③ 模块所有阈值只在训练文档拟合(4折doc级CV)
召回快照冻结进runs(git_sha+config), 标签挂(检测项d, 块ID)上
```

### 3.2 Gold集构建

```text
检测项d来源:
  (a) localization_gold 108实例(91 QA+17违例, 48号协议表单已就绪,
      silver预填, 人工确认即成doc04种子) — needed集须按全文重枚举
      (原冻结池8块非全集)
  (b) 其余15文档各分层抽8条(参数:能力:接口≈2:4:2), 抽样框=
      claims.jsonl(L0产物, 非被评对象), 人工剔除抽取错误(剔除率
      单独报告=L0质量, 不进模块指标)

池标注(每d取冻结top-50, 5类+other, 随机顺序盲标, 不显示召回排名):
  needed / bad_scope(Dong式) / bad_granularity(SummaC式) /
  wrong_shape / background(相关非必需)
  20%双人重标, κ≥0.6否则修schema

裁决gold: 三态(consistent/inconsistent/insufficient)
  刻意纳入硬负例(同名参数跨设备/跨子功能——B0必翻车的case)

规模: 108+120=228检测项×50≈1.1万(d,e)判断, 约35人时
  分两期: 4文档(32项)pilot校κ → 全量
```

### 3.3 指标体系

| 层 | 指标 | 回答什么 |
|---|---|---|
| 池级 | **needed保留率**(误删needed=致命) | 安全底线 |
| 池级 | 删除精确率(删掉的确实gold-bad) | 删对了吗 |
| 池级 | 三类失败分列P/R | scope被F1删对了吗/粒度被F2处理了吗/形态被F3删对了吗 |
| 端级 | **三态macro-F1的Δ(ours−B0)**@固定NLI+prompt | 头条:提点/掉点 |
| 端级 | 逐项翻转归因(verdict变化因误删needed还是清除bad) | 删对了吗(因果) |
| 成本 | 压缩率/NLI调用量/token | 值不值 |
| 对照 | **随机删除@同压缩率** | 排除"少即是多"伪效应 |

### 3.4 基线（同一冻结池/同一NLI/同一prompt，只换减法层）

```text
B0 不减法(按排名截断至token预算)
B1 BGE相似度<τ删(通用RAG式, τ训练折调)
B2 LLM listwise选留
B3 三级过滤(ours)
B4 oracle(gold直删, 上限)
B5 随机删@同压缩率(伪效应对照)
```

### 3.5 统计设计

```text
4折doc级CV(参数只见训练折); 端级配对McNemar(B3 vs B0, 预注册)
功效: 228项下+10pp≈23个discordant对, McNemar α=0.05可检出
不一致正例仅25~40 → 报Wilson CI+明示功效限制
(诚实声明: 池级指标为主证据, 端级Δ为确证性证据)
```

---

## 四、文献定位（Agent 3调研）

### 4.1 三问题的文献地图

| 问题 | 脉络 | 与我们的差异 |
|---|---|---|
| 错误scope | DPR hard negatives→ANCE/RocketQA(训练侧); FEVER NEI主因=主题相关但不足; VitaminC近邻证据微编翻转标签; Shi 2023无关上下文拖垮推理 | 文献=训练期梯度或相关性排序; 我们=**推理期scope契约驱动的逐条删除** |
| 粒度错配 | SumMaC(TACL 2022, 仓库已精读: 句级切分最优); DocNLI; TabFact/TAPAS/FEVEROUS | 文献=统一句/段切分; 我们=**领域结构单位(表行+行头scope+字段)且按检测项裁粒度** |
| 检测项特异性 | Adaptive-RAG(路由策略非schema)/Self-Ask/DecomP(分解子查询不约束证据类型)/ProgramFC/FacTool(源≠形态); DO-178C"需求类型→验证方法"是工程惯例 | **显式空白基本成立**: 检测项→证据形态(模态×粒度×scope)的约束映射无先例 |

### 4.2 减法 vs 重排的理论正源

```text
ERASER(DeYoung et al., ACL 2020): comprehensiveness =
  "删除rationale补集应翻转预测" — 删除式充分性的正统出处
CRAG/RECOMP/MAGE-RAG: 既有删除以相关性/压缩率为目标
我们: 以检测项scope契约为条件, 逐条删除且逐条归因(入VerificationPack)
     + 数据侧复用减法(删证据→sound NIE标签)
主要差异化 = 推理期条件化删除 + 训练期标签构造的双重减法
```

### 4.3 引文风险

- "Dong 2021"无法唯一识别[投稿前核对] — 建议锚点换AmbigQA(Min 2020)
  + EntityQuestions(Sciavolino 2021)
- SumMaC的61.3/72.1[待核对] — 仓库核验数字是SummaCConv 74.4 balanced acc
- 2025后agentic RAG进展需投稿前撞车复核

---

## 五、实施路线

```text
P0(本周):
  1. 统一证据身份层(URE块ID ↔ QA证据块ID映射表)
  2. 检测项合同注册表v1(40项taxonomy→evidence_contracts_v1.json)
  3. EvidenceSubtractor骨架+F1(纯确定性, 零模型)
P1:
  4. F2粒度(枚举切分/句子切分/方向性检查)
  5. F3形态(合同匹配三态)
  6. 减法on/off消融(pilot: doc04的108实例)
P2:
  7. Gold v1全量(228检测项, 35人时)
  8. 六基线对比+McNemar
  9. 论文实验节
```

---

## 六、与既往文档的关系

```text
62-64号: 证据打分设计(充分性/原子化/信号独立) → 减法是它们的工程形态
65-67号: 原子化+拆配判 → scope_hint/行头单元格 = F1的信号基础
68-69号: 打分器对比+端到端 → 69号评测构造被本文§一取代,
         68号的打分器族成为B1基线的实现
70号(本文): 减法模块设计 + 反循环评测协议 → 下一阶段的执行蓝图
```
