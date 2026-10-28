# 66 方法学术血统调研：四支柱文献定位与形式化模型

日期：2026-10-28 | 状态：调研定稿 | 前置：65号(实证验证)

---

## 一、一句话定位

> 我们的方法 = **记录链接(1969) × 弱监督理论(2016) × 需求约束抽取(RE) × 事实验证(FEVER)**，
> 在多模态SRS文档这个从未组合过这四者的领域落地。

---

## 二、四个学术支柱

### 支柱1：记录链接 / 实体解析（我们的S1-S3级联的直接祖先）

**Fellegi & Sunter (1969) "A Theory for Record Linkage" (JASA)**——整个领域56年的地基：

```text
经典模型:
  两条记录 a, b → 比较向量 γ(a,b) = (γ₁, γ₂, ..., γₙ)  每个字段一个比较结果
  → P(γ | M) vs P(γ | U)   M=同一实体, U=不同实体
  → 似然比决定 match / nonmatch / 待人工裁决(!)

关键遗产:
  1. 分字段比较(不是整条记录整体比)         → 我们的原子槽位比较
  2. 三支输出: 匹配/不匹配/存疑送人工        → 我们的冗余/冲突互补/候选
  3. m/u概率可从标注数据估计                 → 我们的可学习路径(见第五节)
```

**现代演化——Blocking→Matching两段架构**（Papadakis et al. 2020, ACM CSUR综述）：

```text
Blocking:  廉价键约束(如参数名相同) → 高召回候选生成, 大幅缩减比较空间
Matching:  昂贵模型(深度匹配/LLM)   → 高精度裁决, 只在候选上跑

我们的映射(65号实证数据完美对上):
  Blocking = S1参数表面形式匹配
    11,869 claims → 397条通过(3.3%) → 96.7%缩减率 = ER标准指标"reduction ratio"
  Matching = S2 BGE → S3 NLI → L3 LLM 成本级联
    = Viola-Jones (2004) 级联思想: 廉价过滤在前, 昂贵判定在后
```

**深度实体匹配**：DeepMatcher (Mudgal et al., SIGMOD 2018)、Ditto (Li et al., VLDB 2020)——
但它们假设**记录已有对齐schema**。我们的差异：原子来自异构多模态源（表格行/正文句/图节点），
**scope槽必须被推断而非给定**（65号实证：subject_candidate填充率0.0%）。这就是我们的贡献空位。

**表格侧的相关工作**：TabFact (Wang et al., ACL 2019) 表格事实验证、TAPAS (Herzig et al., 2020)——
均假设"整表给定"，回避了选择问题；Sherlock (Hulsebos et al., CIKM 2019) 做列语义类型，
不做跨源单元格级比较。

---

### 支柱2：弱监督理论（64号"信号独立"的理论解释）

**Ratner et al. 2016 "Data Programming" (NeurIPS)；Snorkel (VLDB 2017)**：

```text
理论核心:
  n个标注函数(labeling functions)各自有偏但误差条件独立
  → 生成式标签模型的组合精度 > 任何单个LF
  → 误差独立性是核心假设, 违反则理论保证失效

我们的映射:
  S1(结构), S2(BGE), S3(NLI), L3(LLM) = 四个标注函数

  ★ 64号发现的"NLI既是选择器又是检测器"矛盾
    在弱监督理论中就是"标注函数误差相关"——同一模型的误差
    通过共享输入(粒子)在两个决策点间传播, 使组合的理论保证失效。
    我们在64号的解法(信号独立三层)恰好是该假设的工程化满足。
```

**这是64号架构的理论背书**：信号独立不是工程洁癖，是弱监督理论给出精度保证的前提条件。

---

### 支柱3：需求工程约束抽取（我们的原子schema领域合法性）

```text
EARS (Mavin et al., RE 2009): 需求句法模板
  "WHEN <触发> THE <系统> SHALL <响应> WHILE <状态>"
  → 我们的作用域槽(触发/状态)有RE领域正统渊源

Requirement smells (Femmer et al., RE 2017):
  人工定义需求坏味道(歧义/主观/含糊) → ARTA类数据集延续
  → 但smells是"句子级分类", 我们做"槽位级比较"——粒度差异是贡献

约束抽取线 (Schlund et al. 2022-2023, LMU):
  从需求文本抽取模板化约束(boilerplate学习)
  → 单源单模态(纯文本); 我们多源多模态(表格+文本+图)

Bendík & Braun (依赖图+SAT, 项目已有调研):
  逻辑层矛盾用SMT可满足性
  → 继承到我们的L1确定性层(Z3短路)
```

**领域空位**：RE文献的"一致性"工作绝大多数停留在**需求句子级分类**（这条需求是否有问题），
没有人做**跨章节同参异值的实体解析式检测**（哪个值和哪个值构成可比对象）。
65号在doc02发现的真实案例（响应时间3s vs 5s跨章节）恰是现有工具的盲区。

---

### 支柱4：事实验证 / 证据推理（VerificationPack的合法性）

```text
FEVER (Thorne et al., 2018):
  claim → 证据检索 → RTE判定(SUPPORTS/REFUTES/NEI)
  → NEI(证据不足)作为一等公民输出 ←→ 我们的NoEv级

AVeriTeC (Schlichtkrull et al., ACL 2024):
  verdict必须伴随可追溯证据集 ←→ 我们的VerificationPack(证据级评测)

EntailmentBank (Dalvi et al., EMNLP 2021):
  从自由文本证明树推理
  → 我们的结构化差异: 证明节点是带schema的原子, 非自由句
```

---

## 三、形式化模型（论文的方法内核）

### 3.1 原子与比较向量

定义原子（65号四槽schema）：

```text
a = (p, o, v, u, s)
    p: 参数(canonical, 来自GJB词典)
    o: 操作符(≤, ≥, =, ...)
    v: 数值
    u: 单位(归一到单位族)
    s: 作用域(主语/设备/功能绑定)  ← 状态: bound | unbound
```

两原子比较向量（Fellegi-Sunter式）：

```text
γ(a₁, a₂) = (γₚ, γₒ, γᵥ, γᵤ, γₛ)

  γₚ ∈ {agree, disagree}        参数名
  γₒ ∈ {agree, disagree, ⊥}     操作符
  γᵥ ∈ {agree, disagree, ⊥}     归一后数值(单位换算后比较)
  γᵤ ∈ {agree, disagree, ⊥}     单位族
  γₛ ∈ {same, diff, unknown}    作用域  ← 65号实证的精度瓶颈
```

### 3.2 三支决策规则（确定性部分）

```text
D(γ) → {冗余, 冲突候选, 互补, 存疑}

  (agree, *, agree, *, same)        → 冗余   (去重留代表)
  (agree, agree, disagree, *, same) → 冲突候选 (升权送检测)
  (agree, *, *, *, diff)            → 合理差异 (豁免, 如不同设备形态)
  (agree, *, disagree, *, unknown)  → 存疑 → S2/S3/L3级联
```

**豁免模式**（RE领域的hedging传统）：threshold/objective/minimum acceptable等前缀
→ 降级处理，与GJB词典conflict_rules的exempt_patterns对齐。

### 3.3 级联的代价模型

```text
四层标注函数, 单位代价 c₁≪c₂≪c₃≪c₄:
  S1 结构     c₁ ≈ 0        (确定性规则)
  S2 BGE      c₂ ≈ 0.1ms    (预计算余弦)
  S3 NLI      c₃ ≈ 50ms     (本地mDeBERTa)
  L3 LLM      c₄ ≈ 2s       (API)

总代价 = Σ cᵢ · nᵢ, 级联的意义: n₁ ≫ n₄
65号实证: 11,869 → 397 (S1) → 预计~100 (S2) → ~50 (S3) → ~10 (L3)
```

### 3.4 精度瓶颈的定理式陈述

```text
65号实证事实:
  γₛ = unknown 的比例 = 100% (subject_candidate填充率0.0%)
  裸γₚ=agree ∧ γᵥ=disagree 的精度 ≈ 低 (clock_frequency 29值全为假阳性)

推论(设计层):
  P(冲突|γₚ,γᵥ) 由 P(γₛ=same | γₚ,γᵥ) 决定
  → 方法的核心科研问题 = 作用域绑定的学习问题
  → 即: 如何把 γₛ 从 unknown 变为可判定的 same/diff
```

**这是论文的Problem Statement**：跨章节同参异值检测，精度瓶颈不在参数匹配（解了），
不在数值比较（解了），在**作用域绑定**（开放问题，本文提出三级绑定方案）。

---

## 四、与最相关工作的差异矩阵

| 维度 | Fellegi-Sunter | Ditto | FEVER/AVeriTeC | RE smells | **本文** |
|---|---|---|---|---|---|
| 比较粒度 | 记录字段 | 记录(序列化) | 句子 | 需求句 | **槽位原子** |
| Schema | 给定对齐 | 给定对齐 | 无 | 无 | **推断(含scope)** |
| 模态 | 结构化DB | 结构化DB | 纯文本 | 纯文本 | **表+文+图** |
| 三支输出 | ✓(送人工) | 二支 | ✓(NEI) | 二支 | ✓(级联消化) |
| 选择/检测分离 | — | — | ✓ | — | ✓(64号弱监督论证) |
| 代价级联 | ✓ | — | — | — | ✓(四级) |
| 领域 | 通用 | 通用 | 通用 | RE | **GJB SRS** |

---

## 五、可学习的研究设计（m/u概率估计）

Fellegi-Sunter的精华：**m/u概率不是拍脑袋，是从标注估计的**。我们的对应实验设计：

```text
阶段1: 确定性抽取γ向量 (S1, 已完成=65号)
阶段2: 人工标注~100组同参多值对 → 每组标 冗余/冲突/合理差异/存疑
阶段3: 从标注估计槽位级m/u概率:
    m_j = P(γ_j | 冲突)      u_j = P(γ_j | 非冲突)
    → 似然比 Λ = Π m_j/u_j 组合各槽证据
阶段4: 三种组合方式对比:
    (a) 固定规则(3.2节)     — 零样本基线
    (b) 学习的m/u似然比     — Fellegi-Sunter正统
    (c) LLM直接裁决         — 大模型基线
  → 若(b)≈(c)且远超(a): "56年前的理论在大模型时代仍然成立" = 强叙事
  → 若(c)≫(b): 量化LLM在结构化比较上的优势边界
```

**评测指标直接复用ER词汇**（论文免自造指标）：
- Reduction Ratio: 96.7%（S1 blocking，65号实测）
- Pair Completeness: 召回（对gold冲突对的覆盖）
- Matching Precision/Recall: 级联各层

---

## 六、论文叙事建议

```text
标题方向:
  "Scoped Constraint Linking for Cross-Section Consistency
   in Requirements Documents: A Record-Linkage Approach"

贡献主张(按证据强度排序):
  1. 问题: 首次将跨章节同参异值形式化为作用域绑定的记录链接问题
     (证据: 65号实证, scope槽0%填充=精度瓶颈的定位)
  2. 方法: 类型化原子+四级信号独立级联
     (证据: 64号弱监督理论论证 + 65号doc02真实案例)
  3. 理论: FS式m/u概率从标注估计, 对比规则/LLM
     (证据: 待第五节实验)
  4. 发现: 16份真实GJB SRS中的不一致分布
     (证据: 候选池+人工标注)
```

---

## 七、引文清单（按 pillar 分组，置信度标注）

```text
P1 记录链接:
  [Fellegi & Sunter 1969, JASA] ★★★
  [Papadakis et al. 2020, ACM CSUR blocking综述] ★★★
  [Mudgal et al. 2018 SIGMOD DeepMatcher] ★★★
  [Li et al. 2020 VLDB Ditto] ★★★
  [Hulsebos et al. 2019 CIKM Sherlock列类型] ★★☆
  [Wang et al. 2019 ACL TabFact] ★★★
  [Herzig et al. 2020 TAPAS] ★★☆

P2 弱监督:
  [Ratner et al. 2016 NeurIPS Data Programming] ★★★
  [Ratner et al. 2017 VLDB Snorkel] ★★★

P3 需求工程:
  [Mavin et al. 2009 RE EARS] ★★★
  [Femmer et al. 2017 RE smells] ★★★
  [Schlund et al. 2022-2023 约束抽取] ★★☆ (标题待精确核对)
  [Bendík et al. SAT/依赖图] ★★☆ (项目内已有调研)
  [Vovk et al. 2005 conformal] ★★★

P4 事实验证:
  [Thorne et al. 2018 NAACL FEVER] ★★★
  [Dalvi et al. 2021 EMNLP EntailmentBank] ★★★
  [Schlichtkrull et al. 2024 ACL AVeriTeC] ★★☆ (待核对卷页)
  [Viola & Jones 2004 IJCV 级联] ★★★
```

★★★=高置信可引；★★☆=方向正确，投稿前需核对准确出处（当前环境外网受限）。

---

## 八、风险与诚实处

1. **Fellegi-Sunter类比的不完美处**：FS假设字段比较结果独立给定match状态；我们的γₛ与γₚ语义耦合（同参数才谈作用域）。论文中需声明为"FS启发"而非"FS直接套用"。
2. **工作量声明**：m/u估计需~100组人工标注（已列入计划），未完成前不得写理论验证结论。
3. **Ditto式深度匹配基线**：在16份文档规模下可能过拟合，需在实验节声明数据规模限制（与LODO同样的16域统计功效问题）。
4. ★★☆引文必须核对——禁止凭记忆引卷页。
