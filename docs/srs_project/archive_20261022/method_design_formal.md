# ACDD 形式化方法设计：锚点校准的分歧解码

> 版本 v1.0 | 状态: 设计稿 | 对象: 方法论文核心（非工程 pipeline）
> 覆盖: 用户 12 项设计问题 A1–A2, B3–B6, C7–C8, D9–D11, E12（见 §0.2 映射表）
> 数据前提: 16 份 GJB SRS；约 356 个 Visio 锚点图（可直读 XML，感知层金标准免费）；用例描述表/正文提取错误率 ≈ 0；确定性变异引擎（8 类算子，见 `tools/srs_mutation_engine.py`）；75 个真实不一致（仅评测用）

---

## 0. 总览

### 0.1 对候选思想 ACDD 的裁定

**保留核心，做五处关键修补。** 候选思想的骨架是对的——"用锚点图校准感知误差，再用误差模型区分'提取误差'与'文档不一致'"——但原表述有三处概念含混，若不修补会在审稿时被打穿：

1. **缺一个潜在层（最重要）**。原文直接问"这个分歧是通道误差还是文档不一致"，跳过了中间变量：**图片实际画出的内容**。必须区分两层误差：
   - **感知层**：通道输出 vs 图片视觉内容（锚点可校准的正是且只是这一层）；
   - **文档层**：图片视觉内容 vs 文本/表格规范（这才是"不一致"）。
   修补后，"通道 vs 通道"的分歧**在逻辑上不可能**是文档不一致的证据（两通道看的是同一张图），它的正确角色是融合与迁移诊断的内部信息——这一点原框架未澄清。
2. **朴素贝叶斯融合必须放弃**（B3）。相关误差下因子化后验系统性高估置信度。修补：**对融合器做端到端锚点校准**，把相关性整体吸收进复合通道的误差模型，而不是解析地因子化。
3. **分歧不是独立同分布的原子事件**（B5）。节点对齐错误产生"星型"分歧簇，朴素噪声底 $p^k$ 严重低估。修补：节点潜在状态模型 + 块修正的指数界。

修补后的方法核心可以用一行方程概括：

$$D \;=\; \eta \;\oplus\; \varepsilon$$

**分歧 = 不一致 ⊕ 感知噪声。** 检测 = 在已知 $\varepsilon$ 分布（锚点校准）与 $\eta$ 先验（变异签名）的条件下，从观测到的 $D$ 解码 $\eta$。这与纠错码中的译码（decoding）同构：$\eta$ 是消息，$\varepsilon$ 是信道噪声，$D$ 是接收码字；锚点给了噪声分布的免费测量，变异引擎给了消息分布的先验。"Decoding"一词因此是严格而非比喻的。

### 0.2 问题 → 章节映射

| 问题 | 章节 | 问题 | 章节 |
|---|---|---|---|
| A1 形式化 | §1 | C7 分离条件 | §4.1–4.2 |
| A2 三类分歧后验 | §2 | C8 弃权价值 | §4.3 |
| B3 错误相关性 | §3.1 | D9 架构与贡献划分 | §5 |
| B4 小样本校准 | §3.2 | D10 方向A接口 | §6 |
| B5 级联误差 | §3.3 | D11 消融与评测 | §7 |
| B6 训练/测试漂移 | §3.4 | E12 命名与claims | §8 |

### 0.3 符号表

| 符号 | 含义 |
|---|---|
| $D$ | 一份 SRS 文档；$e$ 一个功能实体（条目） |
| $I_e, T_e, B_e$ | 实体 $e$ 的三个视图：流程图（PNG）、用例描述表（CSV）、正文 |
| $\mathcal{X}$ | 规范空间：带类型有向标记图 $X=(V, E, \ell, \tau, \gamma)$ |
| $X_I$ | 图片**实际画出**的过程图（感知层真值，不可直接观测） |
| $X_I^{\mathrm{vis}}$ | Visio XML 解析出的图（锚点金标准，假设 $X_I^{\mathrm{vis}} = X_I$） |
| $X_T = \kappa_T(T_e)$, $\Phi_B = \kappa_B(B_e)$ | 表格编译图 / 正文原子约束集（确定性编译） |
| $c \in \mathcal{C} = \{1,\dots,k\}$ | 感知通道（C1: VLM 结构化，C2: OCR+检测+组装，C3: YOLO+组装） |
| $\hat X_c = c(I)$ | 通道 $c$ 的输出 |
| $x_i, \hat x_{c,i}, y_i$ | 元素级视觉真值 / 通道输出 / 文本值 |
| $\varepsilon_{c,i}$ | 通道 $c$ 在元素 $i$ 上的感知误差指示 |
| $\eta_i = \mathbb{1}[x_i \not\cong y_i]$ | 元素级文档不一致指示（**检测目标**） |
| $\pi = P(\eta_i=1)$ | 元素级不一致先验（基础率） |
| $p_c(\phi, u)$ | 通道 $c$ 的错误率（依赖代理特征 $\phi$ 与随机效应 $u$） |
| $\mu$ | 节点对齐（部分匹配），匹配不确定性的来源 |
| $\Delta$ | 类型化分歧集（带归属结构） |
| $q_\delta$ | 分歧簇 $\delta$ 为真实不一致的后验 |
| $N(\cdot)$ | 良性变异规范化（容忍"合理差异"的商映射） |

标注约定：【成熟】= 直接采用已有统计/机器学习技术（给出来源）；【创新】= 本项目的组合或构造；【理由】/【备选】= 设计决策及其替代方案。

---

## 1. 形式化（A1）

### 1.1 文档、实体、视图

文档语料 $\mathcal{D} = \{D_1, \dots, D_{16}\}$。每个文档是实体的集合，实体 $e$（一个功能/用例，对应一对"流程图 + 用例描述表"）拥有视图三元组 $\mathcal{V}(e) = \{I_e, T_e, B_e\}$，由方向A聚合器 $\mathrm{Agg}$ 从文档中检索得到（§6 处理 $\mathrm{Agg}$ 的误差）。

### 1.2 两层潜在结构（对候选思想的核心修补）

生成模型按如下因果链组织：

$$
\underbrace{X_I \xrightarrow{\;\text{感知}\;} \hat X_c}_{\text{感知层：}\ \varepsilon}
\qquad
\underbrace{X_I \;\xrightarrow{\;\text{作者/文档演化}\;}\; X_T,\ \Phi_B}_{\text{文档层：}\ \eta}
$$

- **感知层**：$\hat X_c = c(I_e)$ 是 $X_I$ 的含噪观测。锚点图上 $X_I = X_I^{\mathrm{vis}}$ 已知，故 $\varepsilon$ 的分布**可测**。
- **文档层**：文档一致性即 $X_I \cong X_T$（在良性变异商 $\cong$ 下，§1.5）。$\eta$ 的取值就是检测对象，其先验由变异引擎与人工编码给出。

**这一分层是整个方法可辩护性的来源**：锚点校准有明确的目标参数（仅感知层），而检测假设（文档层）与校准假设（感知层）在模型上解耦——校准的误差不会直接污染检测假设的定义。候选思想的原始表述把两者混在一个"分歧归因"问题里，会导致"用文档自身的分歧校准通道、再用通道判断分歧"的循环论证。

【备选】单层模型（直接学 $P(\eta \mid \hat X_1..\hat X_k, X_T)$ 的判别器）。放弃原因：可解释性差、无金标准可训（75 个真实不一致太少且不可用于训练，见 §7.4）、无法做 §4 的理论。判别器保留为**基线**（裸 VLM，§7.3）。

### 1.3 规范空间：带类型有向标记图

$$X = (V, E, \ell, \tau, \gamma),\quad E \subseteq V \times V,\quad \ell: V \to \mathcal{L},\quad \tau: V \to \mathcal{T},\quad \gamma: E \to \mathcal{G}$$

其中 $\mathcal{T} = \{\text{start}, \text{end}, \text{process}, \text{decision}\}$ 为节点类型，$\ell$ 为节点标签（步骤文本），$\gamma$ 为边上的条件标签（分支"是/否"、异常流编号 E1/E2）。用例表的"主事件流 + 异常流 + Actors + 前置/后置条件"经确定性编译器 $\kappa_T$ 编译为同空间的图：步骤为 process 节点、带编号顺序边；异常流挂接为条件边；前置/后置条件编译为约束集的一部分。正文的参数值、条件值经 $\kappa_B$ 编译为原子命题集 $\Phi_B$（如 $\text{val}(\text{超时阈值}) = 5\,\mathrm{s}$，单位归一化使用 `knowledge/srs_kb.json` 的单位族）。

**元素宇宙**：比较的基本单元。规范化（§1.5）与对齐（§1.6）之后，定义类型化元素
$$i \in \Omega = \underbrace{\{\mathrm{exst}(u)\}}_{\text{节点存在}} \cup \underbrace{\{\mathrm{lab}(u)\}}_{\text{节点标签}} \cup \underbrace{\{\mathrm{type}(u)\}}_{\text{节点类型}} \cup \underbrace{\{\mathrm{dir}(u,v)\}}_{\text{边存在+方向}} \cup \underbrace{\{\mathrm{cond}(u,v)\}}_{\text{边条件/分支值}} \cup \underbrace{\{\mathrm{val}(a)\}}_{\text{参数值（正文}\Phi_B\text{ vs 图内标注）}}$$

每个元素 $i$ 有视觉值 $x_i$ 与文本值 $y_i$。**关键区分**：存在性元素（$\mathrm{exst}$）的比较不需要对齐 $\mu$（集合层面即可比较）；关系性元素（$\mathrm{dir}, \mathrm{cond}$）必须先对齐节点——级联误差（§3.3）只发生在后者。这个区分在理论上（§4.2 的块结构）和工程上（对不确定对齐的边只弃权不报分歧）都有用。

### 1.4 通道与元素级错误模型

感知通道 $c: \mathcal{I} \to \mathcal{X}$ 是随机算子。元素级错误模型：

$$P(\hat x_{c,i} = a \mid x_i = b,\ \phi_i,\ u) \;=\; \Theta^{(c)}_{ab}(\phi_i, u)$$

其中 $\phi_i$ 为**可观测代理特征**（字高/分辨率、节点密度、边交叉数、对比度——不依赖金标准即可计算），$u = (u_{\mathrm{doc}}, u_{\mathrm{img}})$ 为文档级/图片级随机效应。对二值元素（存在性、方向）：

$$P(\varepsilon_{c,i} = 1) = p_c(\phi_i, u) = \sigma\big(\alpha_c + \beta_c^\top \phi_i + u_{\mathrm{img}}\big),\quad u_{\mathrm{img}} \sim N(0, \sigma^2_{\mathrm{doc}})$$

即一个 GLMM（广义线性混合模型）参数化【成熟：Gelman & Hill 2006；lme4】。混淆结构按维度稀疏化：方向误差几乎只有"反转"一种模式；标签误差集中在数值替换与形近字；条件值误差集中在"是/否"互换——每维度估计一个小混淆矩阵而非全自由参数（§3.2 的参数量控制）。

【备选】每通道一个自由混淆张量。放弃原因：356 张锚点图撑不起（§3.2）；且维度内混淆天然稀疏，稀疏结构本身是可检验假设。

文本侧通道：$\hat X_T = \kappa_T(T_e)$ 假定错误率 $\approx 0$（表格式确定、解析可靠），但**编译器** $\kappa_T$ 本身有建模误差（"若…则…"分支的图解释），记其错误率为 $p_\kappa$，处理见 §9 脆弱点 4。

### 1.5 良性变异与规范化（"合理差异"的形式化）

正文与图对同一过程的不同表述（起始/终止哨兵节点、粒度差异、同义改写、单位写法）不是不一致。定义规范化映射 $N: \mathcal{X} \to \mathcal{X}$：

1. 删除 start/end 哨兵节点（度 $\le 1$ 且类型为端点）；
2. 标签词典规范化（`srs_kb.json` 同义词典 + 单位族归一 + 编号剥离）；
3. 度-2 无标签传递节点合并（**有条件**：仅当其标签经规范化为空，否则保留——防止掩盖真实信息）。

一致性定义为 $N(X_I) \cong N(X_T)$。$N$ 是手工构造的确定性映射，其不完美是**误报的主要现实来源**（§9 脆弱点 6）。缓解：锚点文档提供大量"同文档内图-表对"（大概率一致），可用鲁棒估计（取众数）经验刻画良性变异的分布，反过来修订 $N$；边界情形（标签相似度落在阈值附近）路由到高弃权区而非硬判。

### 1.6 分歧：对齐、类型化分歧、归属结构

对齐 $\mu: \hat V \to V_T \cup \{\bot\}$ 是部分匹配，由标签/类型/几何（流程图通常自上而下布局，坐标可作先验）相似度的指派问题求解【成熟：Kuhn 1955 匈牙利算法；相似度沿用 sc2 方案的四层匹配（精确/关键词/embedding/LLM 仲裁）】。$\mu$ 取 Top-$K$ 个匹配作为候选，后验计算对其边际化。

给定 $\mu$，类型化分歧提取器：

$$\Delta\big(N(\hat X),\, N(X_T);\, \mu\big) \subseteq \mathcal{T}_\delta \times \Omega$$

产生带类型的分歧，如 $(\text{direction-reversal}, \mathrm{dir}(u,v))$、$(\text{node-missing}, \mathrm{exst}(u))$、$(\text{value-conflict}, \mathrm{val}(a))$。每个分歧簇 $\delta$ 携带**归属结构**：以节点为顶点、以分歧元素为关联边的归属图 $G_\delta$——星型结构（多条分歧共享一个节点）是级联误差的特征信号（§3.3）。

### 1.7 不一致类型与变异签名

$H_1$ 似然 $P(\delta \mid \eta_\delta = 1)$ 需要"真实不一致如何显现为分歧"的分布——**变异签名** $\Sigma_{\mathrm{mut}}$。来源：变异引擎的 8 类算子（`mutate_id / mutate_name / mutate_value / mutate_section_shift / mutate_exception_removal / mutate_caption / mutate_logic_contradiction / mutate_semantic_preserve`）在干净对上注入已知不一致，运行整个比对管线，统计每类算子的分歧指纹（触及的元素数 $m_\delta$、类型分布、形状）。其中 `mutate_semantic_preserve`（语义保持扰动）同时提供了**良性变异的正样本**，用于 §1.5 的 $N$ 校准——这个双重用途是变异引擎的一个意外红利。

签名按"触及元素数"分档：单元素签名（值替换、方向反转、ID 改写）$m=1$；簇签名（异常流删除 → 删一个节点 + 挂接边，$m \ge 3$；章节错位 → 顺序重排，$m \approx$ 度）。§4.2 将证明 $m$ 与可检测性指数相关。

---

## 2. 三类分歧的后验计算（A2）

### 2.0 通用贝叶斯骨架

对任一分歧簇 $\delta$：

$$q_\delta \;=\; P(\eta_\delta = 1 \mid \text{观测}) \;=\; \frac{\pi_\delta\, L_1(\delta)}{\pi_\delta\, L_1(\delta) + (1-\pi_\delta)\, L_0(\delta)}$$

- $L_0(\delta) = P(\text{观测到分歧形态 }\delta \mid H_0)$：**噪声底**——一致性文档上，感知误差 + 对齐误差 + 编译误差产生该分歧形态的概率。全部统计难题（§3）都发生在 $L_0$ 里。
- $L_1(\delta) = P(\text{观测到 }\delta \mid H_1)$：**签名似然**——变异签名 $\Sigma_{\mathrm{mut}}$ 给出。
- $\pi_\delta$：簇级不一致先验（文档级分层：$\pi_d$，§3.2）。

### 2.1 类型 (a)：通道 vs 通道（同一张图）

两通道观测同一 $x_i$：$\hat x_1 = x_i \oplus \varepsilon_1$，$\hat x_2 = x_i \oplus \varepsilon_2$。**该类分歧在 $H_1$（文档不一致）下的分布与 $H_0$ 完全相同**——因为两通道看到的是同一张图，文档层无论是否一致都不影响它们。故 (a) 类分歧**不进入 $q_\delta$ 的证据链**，其正确用途有三：

1. **潜在图推断**（融合的输入）。给定两通道分歧，视觉真值的后验（条件独立假设下）：
$$P\big(x_i = \hat x_1 \,\big|\, \hat x_1 \ne \hat x_2\big) = \frac{(1-p_1)\,p_2}{(1-p_1)\,p_2 + p_1\,(1-p_2)}$$
多通道时按对数似然比累加（校准 literally 给出投票权重，见 §4.1 式 (3)）。
2. **迁移诊断**（§3.4）：目标图上实测的通道间分歧率 vs 锚点预测值的偏离度，是无标签域漂移探测器。
3. **难度探针**：分歧率本身就是 $\phi$ 之外的一个在线难度特征。

【关键警告】正相关误差下"通道一致"不等于"正确"：二值元素上两通道**同时错**意味着**一致地给出同一个错误值**，其概率 $p_{12} = P(\varepsilon_1 = \varepsilon_2 = 1)$ 随相关性上升。独立性假设会把"一致"过度解读为可靠——这正是朴素融合高估置信度的机制（§3.1）。

### 2.2 类型 (b)：通道 vs 表格/正文文本

主战场。单通道、对称噪声 $p_c$ 的基础情形即 §4.1 命题 1：

$$P(\eta = 1 \mid D = 1) = \frac{\pi\,(1-p_c)}{\pi\,(1-p_c) + (1-\pi)\,p_c}$$

工程化时做三层积分：

1. **层次后验预测**：用 $\bar p_{c,i} = E[\,p_c(\phi_i, u)\mid \text{锚点}\,]$（后验预测均值，非点估计）代入——$\theta$ 的估计不确定性自动传递为更宽的后验、更多弃权（§3.2）；
2. **对齐边际化**：$L_0(\delta) = \sum_{\mu \in \mathrm{TopK}} P(\mu)\, P(\delta \mid \mu, H_0)$，$P(\mu)$ 取指派得分的 softmax；
3. **文本侧噪声**：若承认 $p_\kappa > 0$，用两观测者公式（下面 (2.3)）替代单通道公式。

两观测者一般式（通道误差 $p_1$、编译误差 $p_2$，条件独立）：观测分歧率

$$P(D \mid H_0) = p_1 + p_2 - 2p_1 p_2, \qquad P(D \mid H_1) = (1-p_1)(1-p_2) + p_1 p_2$$

（推导：$D = \mathbb{1}[\varepsilon_1 \oplus \varepsilon_2 \ne \eta]$。）注意到等先验下 MAP 在 $D=1$ 时判不一致的充要条件是 $L_1 > L_0 \iff (1-2p_1)(1-2p_2) > 0$，即**两侧误差率都低于 1/2**——一侧退化则该比较整体无信息。

### 2.3 类型 (c)：多通道融合结果 vs 文本

**主方案：把融合器当复合通道，端到端校准。** 定义融合器 $F: (\hat X_1, \dots, \hat X_k, \phi) \mapsto \hat X_F$（逐元素加权多数 + 图合并，权重来自 $\theta$；任何**确定性** $F$ 皆可）。在**留出锚点**上运行 $F$ 并与 $X_I^{\mathrm{vis}}$ 比对，直接得到复合误差率 $\theta_F$：

$$p_F(\phi) \;=\; P\big(\hat x_{F,i} \ne x_i \mid \phi_i\big) \quad\text{（锚点实测，含全部相关效应）}$$

于是 (c) 的后验与 (b) 同式，$p_c \to p_F$。**相关性问题（§3.1）在端到端校准下自动消失**——我们从不需要把 $F$ 的误差因子化为各通道分量；相关结构被经验地吸收进 $p_F$。这是对候选思想"朴素贝叶斯组合通道证据"的系统性修补。

【备选 1】因子化联合解码：不显式构造 $\hat X_F$，直接算 $P(\eta \mid \hat x_{1,i}, \dots, \hat x_{k,i}, y_i)$。这是原理上最优的变体，但需要联合误差模型 $P(\varepsilon_1, \dots, \varepsilon_k \mid \phi)$——参数量与相关性问题都回来了。**定位**：作为消融中的"理论上界参照"实现（小 $k$、参数共享下的近似），不作为主方法。
【备选 2】保守单通道界（只用最可靠单通道，其余通道仅作弃权触发器）。作为 §3.1 的第三档回退方案保留。

**协议要求**：$F$ 的校准锚点必须与 $F$ 内部权重的拟合锚点不相交（调参/校准分离），且与 C3 的训练锚点不相交——锚点三分：C3 训练池 / 校准池 / 评测池，文档级分块切分防泄漏（§7.1）。

### 2.4 三类分歧的决策表

| 分歧类型 | $H_0$ 含义 | 噪声底来源 | 主方案 | 备选 |
|---|---|---|---|---|
| (a) 通道 vs 通道 | 同一视觉内容 | $\varepsilon_1, \varepsilon_2$ 联合 | 不作检测证据；用于融合、迁移诊断、难度探针 | — |
| (b) 通道 vs 文本 | 图文一致 | $\theta_c$ + $\mu$ 不确定 + $p_\kappa$ | 命题 1 式 + 层次后验预测 + TopK 对齐边际化 | 最坏情况界（§3.1 第三档） |
| (c) 融合 vs 文本 | 图文一致 | $\theta_F$（端到端） | 复合通道锚点校准 | 因子化联合解码（消融/上界） |

---

## 3. 统计难题与方案（B3–B6）

### 3.1 错误相关性（B3）

**问题**：VLM/OCR/YOLO 看同一张图，误差共享成因（小字、低分辨率、密集布局）。独立性假设下 $P(\text{联合误差}) = \prod_c p_c$ 系统性低估 → $L_0$ 偏小 → $q_\delta$ 虚高 → 误报。

**方案：三档递进。**

**第一档（主方案）：共享难度的分层条件化。** 误差条件独立给定 $(\phi, u)$（可观测代理 + 图片级随机效应）：

$$P(\varepsilon_1, \varepsilon_2 \mid \phi, u) = \prod_c P(\varepsilon_c \mid \phi, u)$$

**引理（共享难度的正相关）**：若 $g_c(d) = P(\varepsilon_c = 1 \mid d)$ 对潜在难度 $d$ 均不减，则
$$P(\varepsilon_1 = 1, \varepsilon_2 = 1) \;\ge\; P(\varepsilon_1 = 1)\,P(\varepsilon_2 = 1)$$
证明：$\mathrm{Cov}(\varepsilon_1, \varepsilon_2) = E[\mathrm{Cov}(\varepsilon_1, \varepsilon_2 \mid d)] + \mathrm{Cov}(g_1(d), g_2(d)) = \mathrm{Cov}(g_1, g_2) \ge 0$（同一随机变量的两个不减函数协方差非负，Chebyshev 关联不等式）。∎

含义：条件化吸收掉由 $\phi, u$ 驱动的相关性；**残余相关性**（$\phi$ 之外的共同成因，如异常视觉风格）在留出锚点上可直接检验（条件化后残差相关系数是否显著非零）。可估计参数量：每通道 $|\beta_c| + 2$ 个方差分量——356 张锚点 × 每图数十个元素 ≈ 数千条元素级观测，GLMM 完全撑得住。【成熟：GLMM / 共享脆弱模型】

**第二档：端到端吸收（结构性解法）**。如 §2.3：只要被比较的对象（融合输出）整体在锚点上校准，相关性根本不进入计算。**设计原则：能在复合层校准的，绝不解析因子化。** 因子化只在两处不可避免：(i) 融合器内部权重（用条件化模型，其误差由端到端校准兜底）；(ii) 归属分析（哪条通道错了——证据链的附属信息，用近似并做敏感性检查）。

**第三档：无独立性假设的保守界（回退/敏感性分析）**。对"至少一通道错"这类事件用 Fréchet–Hoeffding 界：
$$P(A \cup B) \le \min(1,\ p_1 + p_2) \quad\text{（联合界）}$$
直接代入 $L_0$ 得到 $q_\delta$ 的保守下界；报告主结果时同时报告该界的版本，两者差异即"相关性风险敞口"。代价是阈值变松、弃权增多，但统计上诚实。【成熟：Fréchet 界】

【备选（放弃）】Copula 联合建模：参数化优雅，但 356 锚点估 copula 参数方差过大，且端到端校准已提供更便宜的解。联合混淆张量：维度灾难。最坏情况界单独使用：浪费锚点信息，功效损失过大——降级为第三档。

### 3.2 小样本校准（B4）

**问题**：356 锚点 / 16 文档 / 每文档 5–30 图。逐文档混淆矩阵的单元计数极小，方差爆炸。

**方案：跨文档分层收缩 + 后验预测。**

1. **元素级而非图级计数**：每图 10–40 个节点/边 → 总计 $10^3$–$10^4$ 条元素级校准观测，问题的真实样本量比"356"大一个量级以上。
2. **Beta–Binomial 收缩**（标量情形）：文档级错误率 $p_{c,d}$，先验 $\mathrm{Beta}(\alpha, \beta)$ 由语料边际 MLE 拟合（经验贝叶斯），后验均值
$$\hat p_{c,d} = \frac{\alpha + e_{c,d}}{\alpha + \beta + n_{c,d}}$$
小样本文档自动向语料均值收缩。【成熟：Efron & Morris 1975】
3. **GLMM 替代**（带 $\phi$ 协变量情形）：文档随机截距 $u_{\mathrm{doc}}$ 实现同一效果且可解释（"某文档渲染质量差"→ 该文档噪声底整体上移 → 误报自动减少——一个理想的文档自适应行为）。
4. **解码用后验预测而非点估计**：$\bar p_c = E[p_c \mid \text{锚点}]$。Beta 先验下即 Laplace 平滑的后验均值；$\theta$ 的不确定区间宽 → $q_\delta$ 的不确定区间宽 → 自动流入弃权带。**估计不确定性与检测不确定性在数学上无缝衔接**，这是贝叶斯框架的直接红利。
5. **诚实方差报告**：所有 $\hat p$ 给出置信区间（Wilson / Beta 后验区间）；留一文档（LODO）交叉验证报告跨文档迁移的预测误差——这同时是对 §3.4 的域内预演。

【备选】贝叶斯层次模型全贝叶斯推断（MCMC）。作为最终实现可选，方法层面 GLMM/EB 已足够；全文档池化（不分层）：会被文档异质性打穿，放弃。

### 3.3 级联误差（B5）

**问题**：节点对齐错误污染其上挂接的所有边比较。边级分歧不是独立的：以节点为共享成因成"星型"簇。

**误差传播界。** 设节点错配率 $p_{\mathrm{mm}}$（错配 = 未匹配到正确节点，含漏配/错配），边自身误差率 $p_e$。对齐正确条件下边分歧率为 $p_e$；任一端点错配时边几乎必然分歧（$\ge 1/2$ 记为 $\rho_\star$）。联合界：

$$P\big(D_{uv} = 1 \mid H_0\big) \;\le\; 2\,p_{\mathrm{mm}} + p_e$$

**星型噪声底（本节最重要的定量结论）**：度数为 $k$ 的节点 $u$ 的全部 $k$ 条邻接边在 $H_0$ 下同时分歧的概率

$$P\big(\text{star}_k \mid H_0\big) \;\le\; p_{\mathrm{mm}} + (1 - p_{\mathrm{mm}})\, p_e^{\,k} \;\approx\; p_{\mathrm{mm}} \quad (k \text{ 大时})$$

即：**大星型分歧簇在 $H_0$ 下的概率被单节点错配率 $p_{\mathrm{mm}}$ 主导，而非朴素独立假设的 $p_e^k$。** 这揭示一个基本混淆（star confound）：一个"节点缺失"型真实不一致（$H_1$）与一次"节点错配"型感知错误（$H_0$）产生**几乎相同的分歧形态**。两者的分辨力来自：

- **难度条件化**：该节点是否难以看见（$\phi$：字小、密集区）→ 错配的先验高低；
- **跨通道证据**：$\ge 1$ 条通道找到了该节点 → 视觉上确实存在 → 剩余解释是"文本真缺失"（$H_1$）或编译遗漏；所有通道都未找到 → "感知漏检 vs 真不存在"在图像内部不可分辨，只能靠锚点校准的漏检率 + $\pi$ 后验化（§4.1）。

**结构化解法：节点潜在状态模型。** 每个节点对取潜在状态 $s \in \{\text{correct}, \text{mis-matched}, \text{spurious}, \text{missed}\}$，边分歧条件于两端节点状态独立。这是一个以节点状态为因子的小型 MRF（每实体节点数 $\le 40$，变量消除精确推断毫秒级）。输出：每个分歧簇对每个候选成因（感知错配 / 真缺失 / 真多余）的后验归属——证据链的天然内容。【创新：分歧归属的图结构化解码，思想上类比软件测试的基于谱的错误定位】

**对指数界的影响（§4.2 预告）**：$H_0$ 下分歧的独立单元不是元素而是"独立失败成因"（节点状态 + 边误差）——命题 2 的块修正版本以成因数为指数。

【备选】只比较"高置信匹配"节点的边、其余弃权：作为 MRF 的退化版（硬门限）保留在消融中。

### 3.4 无锚点通道的错误模型迁移（B6）

**问题**：C3（YOLO）在锚点图上训练——"有 Visio XML 的图"不是全体图的随机样本（选择偏差与作者工具链相关）→ 锚点估计的 $\hat p_c$ 在 PNG-only 图上可能失真；且锚点上的校准还有"训练集内乐观偏差"。双重漂移。

**方案：诊断 → 校正 → 降级的三级协议。**

**第一级（诊断）：锚点校准的一致性迁移估计。**【创新组合，技术血统见下】目标图上（无标签），三通道两两分歧率 $\gamma_{12}, \gamma_{13}, \gamma_{23}$ 可实测。模型（给定共同真值、条件独立）：

$$\gamma_{ij} = p_i + p_j - 2\,p_{ij}^{\text{both}} \quad\text{其中}\ p_{ij}^{\text{both}} = P(\varepsilon_i = \varepsilon_j = 1)$$

三个方程、三个未知数 $p_1, p_2, p_3$（$p_{ij}^{\text{both}}$ 由锚点估计的关联因子 $\lambda_{ij} = p_{ij}^{\text{both}} / (p_i p_j)$ 外推，即假设**相关结构比边缘率更可迁移**——一个较弱的、可检验的假设）。求解得目标域错误率估计 $\tilde p_c$，与锚点预测值 $\hat p_c(\phi)$ 比较：

- 落在预测区间内 → 模型迁移有效，正常解码；
- 系统性偏高 → 用 $\tilde p_c$ 替换 $\hat p_c$（在线重校准）；
- 求解失败/矛盾 → 降级。

【成熟血统：三标注者错误率从两两一致性可辨识的思想——Dawid & Skene 1979；Platanios et al. 2014 无标签精度估计；本项目的组合=用锚点估计相关因子，把不可辨识问题变成可辨识】

**第二级（校正）：代理特征空间的密度比加权。** 锚点图与目标图在 $\phi$ 空间的分布差异用密度比 $w(\phi) = P_{\mathrm{target}}(\phi)/P_{\mathrm{anchor}}(\phi)$ 估计（logistic 回归/ruLSIF），校准似然加权重估 $\theta$。**支持性检查**：目标 $\phi$ 分布的凸包超出锚点支持的区域（positivity 违反）→ 该区域弃权而非外推。【成熟：Sugiyama et al. 2012 密度比域适应】

**第三级（降级）**：诊断与校正都失效时，将 $p_c$ 替换为其置信上界（如 Wilson 上界），$q_\delta$ 整体向先验 $\pi$ 收缩（§4.3 注记 2），弃权率自动上升。**绝不静默使用过时 $\theta$。**

**协议补充**：锚点三分（§2.3）保证 C3 训练内乐观偏差被隔离；LODO 提供"整文档风格迁移"的域内模拟；$\phi$ 空间重叠度（PCA/UMAP 可视 + 凸包含率）作为可报告的漂移风险指标。

【备选（放弃）】域对抗训练/微调 YOLO 于目标图：需要目标标签或伪标签闭环，评测循环性与可信度都有问题，且不解决校准问题本身。

---

## 4. 理论结果（C7–C8）

以下均在简化模型下陈述并证明：二值元素、对称噪声、条件独立（相关性/级联的修正以推论形式给出）。简化的目的是把"何时可检测、何时必须弃权"变成可证明的命题，而非把全部工程现实塞进定理。

### 4.1 命题 1（分离条件：$\pi > p$）

**命题 1**：设元素级不一致先验 $\pi = P(\eta = 1)$，通道对称错误率 $p < 1/2$，观测分歧 $D = \eta \oplus \varepsilon$。则：

**(i)** $P(D = 1 \mid \eta = 0) = p$，$P(D = 1 \mid \eta = 1) = 1 - p$；

**(ii)** 后验 $P(\eta = 1 \mid D = 1) = \dfrac{\pi (1-p)}{\pi (1-p) + (1-\pi)\, p}$；

**(iii)** MAP 规则"见分歧即报不一致"是贝叶斯一致的当且仅当 $\pi > p$；

**(iv)** $p = 1/2$ 时 $D \perp \eta$（分歧无信息）；$p > 1/2$ 时通道反向有信息（应取反后再用）。

证明：(i)(ii) 直接 Bayes；对两个假设分别有 $D = \varepsilon$（$\eta=0$）与 $D = 1 - \varepsilon$（$\eta=1$，因 $D = \eta \oplus \varepsilon$）。(iii) $P(\eta = 1 \mid D=1) > 1/2 \iff \pi(1-p) > (1-\pi)p \iff \pi > p$。(iv) 代入 $p = 1/2$ 两分布相同；$p > 1/2$ 时 (i) 中两概率互换。∎

**推论 1.1（校准的必要性）**：后验公式只含两个量 $\pi, p$。**不知道 $p$ 就连分歧的方向性解释都不可能**（$p < 1/2$ 还是 $> 1/2$ 决定分歧是"不一致的证据"还是"一致的证据"）。未校准检测器输出的"置信度"没有概率语义——这直接论证锚点校准不是工程装饰而是方法的先决条件。

**推论 1.2（多通道似然比投票）**：$k$ 个条件独立通道时，对数后验几率 = 先验对数几率 $+\sum_c \lambda_c$，其中通道 $c$ 贡献 $\lambda_c = \pm\log\frac{1-p_c}{p_c}$（符号取决于该通道是否与文本分歧）。**校准误差率直接给出投票权重**：越可靠的通道权重越大，权重符号由分歧方向给出。【成熟：朴素 Bayes / 乘积专家；相关性下权重过计——由 §3.1 第二档端到端校准兜底】

**数值示例（讲清方法的整个故事）**：$\pi = 0.05$（元素级基础率），单通道 $p = 0.1$，一条原始分歧的后验仅 $0.045 / 0.14 = 0.32$——**单条分歧大概率是噪声**。但 3 元素簇（如异常流删除的签名）在 $H_0$ 下噪声底 $p^3 = 10^{-3}$、$H_1$ 下 $(1-p)^3 = 0.73$，后验 $= 0.05 \times 0.73 / (0.05 \times 0.73 + 0.95 \times 10^{-3}) = 0.97$。**结论：单元素不一致靠低 $p$（融合压噪声），簇不一致靠指数积累——两类检测策略在方法内自动分化。**

### 4.2 命题 2（指数分离与块修正）

**命题 2**：设目标不一致的签名触及 $m$ 个元素，$H_0$ 下各元素分歧指示条件独立、均为 $\mathrm{Bern}(p)$；$H_1$ 下签名元素分歧概率为 $1 - p$。等先验的 MAP 检验两类错误概率均满足

$$P_e \;\le\; \exp\big(-m \cdot C(p)\big), \qquad C(p) = -\tfrac{1}{2}\log\big(4p(1-p)\big)$$

其中 $C(p) \ge 0$ 且 $C(p) = 0 \iff p = 1/2$。

证明：二元简单假设、iid 观测下的 MAP 错误率由 Chernoff 界给出，指数为两分布的 Chernoff 信息；$\mathrm{Bern}(p)$ vs $\mathrm{Bern}(1-p)$ 的 Chernoff 信息在对称性下于 $s = 1/2$ 取得：$\min_s [p^s (1-p)^{1-s} + (1-p)^s p^{1-s}] = 2\sqrt{p(1-p)}$。∎【成熟：Chernoff 1952】

**数值表（错误率上限 $\exp(-mC) = (4p(1-p))^{m/2}$）**：

| $p \backslash m$ | 3 | 5 | 10 | 20 | 30 |
|---|---|---|---|---|---|
| 0.05 | 0.083 | 0.016 | $2.5\times10^{-4}$ | $6.2\times10^{-8}$ | $\sim10^{-11}$ |
| 0.10 | 0.22 | 0.078 | 0.0060 | $3.7\times10^{-5}$ | $2.2\times10^{-7}$ |
| 0.20 | 0.51 | 0.33 | 0.107 | 0.0115 | 0.0012 |
| 0.30 | 0.77 | 0.65 | 0.42 | 0.18 | 0.075 |
| 0.40 | 0.94 | 0.90 | 0.82 | 0.66 | 0.54 |

**解读**：$p \le 0.1$ 时 10 元素簇近乎无误；$p = 0.3$（困难图上的边级误差现实可达）需要 $m \ge 30$ 才进入可用区间，$p \ge 0.4$ 时元素级积累基本失效——**这给出方法的能力边界声明：单元素签名（值替换/方向反转）只有在融合后 $p_F$ 被压到 $\pi$ 以下时才可检测（命题 1），否则只能弃权送审；簇签名的可检测性由本命题的指数保证，且指数随 $p$ 恶化得很快。** 论文里这就是 honest scoping。

**推论 2.1（块修正 / 级联与相关性统一处理）**：若 $H_0$ 下 $m$ 个分歧指示由 $B$ 个独立失败成因支配（节点错配、共同难度、同一变异的多重表现——级联 §3.3 与相关 §3.1 在这里统一），则指数以**成因数**计：$P_e \le \exp(-B \cdot \bar C)$；块内多数表决的假阳性率由 Hoeffding 界 $P(\mathrm{Bin}(m_b, p) > m_b/2) \le e^{-m_b D(1/2 \| p)}$ 控制。【成熟：Hoeffding 1963；设计效应 $m_{\mathrm{eff}} = m / (1 + (\bar m - 1)\bar\rho)$ 的标准修正】

**推论 2.2（多重检验）**：扫描 $N$ 个候选簇，族级假阳性由 Bonferroni/BH 控制；$\tau^+$ 的选择改由 §4.3 的共形程序给出有限样本保证。【成熟：Benjamini & Hochberg 1995】

### 4.3 命题 3（弃权的价值）与共形阈值

**命题 3（选择性预测的支配性）**：设 $q \in [0,1]$ 为校准后验（$P(\eta = 1 \mid q) = q$）。贝叶斯行为规则下元素级条件风险为 $r(q) = \min(q, 1-q)$。选择覆盖率 $\varphi$ 的最优选择性分类器（弃权 $(1-\varphi)$ 比例的不确定样本）满足：

$$R^\ast(\varphi) = \frac{E\big[r(q)\, \mathbb{1}\{r(q) \le Q_\varphi\}\big]}{\varphi} \;\le\; R^\ast(1) = E[r(q)]$$

且 $R^\ast(\varphi)$ 对 $\varphi$ 单调不减。即：**带弃权的检测器在风险–覆盖前沿上逐点支配强制分类检测器**；当后验有内部质量（$P(q \in (0.1, 0.9)) > 0$）时严格更优。

证明：最优弃权集为不确定性最小的 $\varphi$ 比例之补（重排不等式）；保留集是 $r(q)$ 最小的 $\varphi$ 部分，其均值不超过全体均值。∎【成熟：Chow 1970 最优拒绝规则；El-Yaniv & Wiener 2010 风险–覆盖理论】

**共形阈值校准（有限样本 FPR 控制）**【成熟：Vovk et al. 2005；Angelopoulos & Bates 2021；Bates et al. 2021】：$\tau^+, \tau^-$ 不手工设定，而是在"干净锚点对 + 变异注入对"的校准集上用 Learn-then-Test 选择，使得弃权后报告的错误发现率 $\le \alpha$ 具有分布自由的有限样本保证。交换性近似成立（变异与真实不一致的可交换性是假设，§9 脆弱点 3）。

**注记 1（成本不对称）**：军事 QA 中漏检代价（现场风险）与误报代价（分析师信任损耗）不对称。Chow 规则的一般形式以 $\tau = c_{\mathrm{rej}}/(c_{\mathrm{err}} + c_{\mathrm{rej}})$ 融入成本；"弃权 = 送人工"的期望工作量 $= (1-\varphi) \times |\text{比较数}|$，可与人工预算联合优化。

**注记 2（优雅退化，命题 1 的直接推论）**：若实际错误率退化为 $p' \to 1/2$ 且模型**如实更新**（§3.4 的迁移诊断），则 $P(\eta = 1 \mid D = 1) \to \pi$、$P(\eta = 1 \mid D = 0) \to \pi$——后验退化为先验，检测器在 $\tau > \pi$ 下**自动弃权而非出错**。分布漂移下方法的失效模式是"沉默地不工作"（弃权率上升），而非"自信地报错"。前提是 $\theta$ 被更新——过时的 $\theta$ 会让后验虚高，这正是 §3.4 诊断协议存在的理由。

---

## 5. 方法整体架构（D9）

### 5.1 输入 / 输出

**输入**：文档 $D$；锚点集 $\mathcal{A}$（图 + Visio XML）；通道集 $\mathcal{C}$；变异引擎 $\mathcal{M}$；聚合器 $\mathrm{Agg}$（方向A）；阈值 $(\tau^+, \tau^-)$（共形校准）。
**输出**：按实体的不一致报告列表，每条含：类型化分歧簇、后验 $q_\delta$、归属分析（感知成因 vs 文档成因的后验分解）、证据链（视图定位、通道分歧明细、所依据的校准参数与锚点来源）；以及弃权清单（送人工）与未覆盖清单（聚合缺口，§6）。

### 5.2 算法伪代码

```
算法 1  ACDD-CALIBRATE（离线，一次性）
输入: 锚点集 A = {(I_j, XML_j)}_{j=1..356}, 通道集 C, 代理特征 φ(·)
 1  for j: X*_j ← ParseVisioXML(XML_j)                    # 路线A, 确定性
 2     渲染一致性抽查: 抽样人工/强通道核对 PNG(I_j) ≈ X*_j   # §9 脆弱点5
 3  锚点三分（文档级分块）: A_train(C3训练) / A_cal / A_eval
 4  for c ∈ C, j ∈ A_cal ∪ A_eval:
 5      X̂ ← c(I_j); (μ, Δ) ← Compare(X̂, X*_j)            # 元素级误差标注
 6  θ̂ ← GLMM-Fit({Δ}, φ(I); 随机效应 doc/img)              # §3.1–3.2 【成熟】
 7  θ̂_F ← 在 A_eval 上端到端校准融合器 F                    # §2.3 【创新协议】
 8  Σ_mut ← 变异签名(变异引擎, 仅用算子子集 T_prior)          # §1.7 反循环 §7.4
 9  验证: LODO CV; 条件化后残差相关检验; 可靠性图/ECE
10  (τ⁺, τ⁻) ← ConformalLTT(A_eval ∪ 变异校准集, α)         # §4.3 【成熟】
输出: {θ̂_c, θ̂_F, Σ_mut, τ⁺, τ⁻, 漂移诊断参考量}

算法 2  ACDD-DETECT（在线，每文档）
输入: 文档 D, 校准产物, Agg, 阈值
 1  for 实体 e: {I,T,B} ← Agg(D, e);  X_T ← κ_T(T); Φ_B ← κ_B(B)
 2  for 图 I:
 3      φ ← φ(I); 一致性迁移诊断(γ_ij 实测 vs 预测)          # §3.4 【创新】
 4      → {正常 | 在线重校准 p̃ | 降级为上界}
 5      X̂_c ← c(I) ∀c;  X̂_F ← F(X̂_1..k, φ)                # 感知+融合
 6      归一化 N(·)（良性变异商映射）;  μ_{1..K} ← TopK 指派
 7      Δ ← TypedDiscrepancies(N(X̂_F), N(X_T); μ) + 归属图
 8      for 簇 δ ∈ Δ（按归属图连通分量分簇）:
 9          节点潜在状态 MRF 推断 → 噪声底 L_0(δ)            # §3.3 【创新】
10          q_δ ← Posterior(δ; θ̂所用版, Σ_mut, π_d; μ 边际化) # §2
11          q_δ > τ⁺ → 报告(证据链);  q_δ < τ⁻ → 通过;  否则弃权
12  汇总: 报告 + 风险/覆盖率 + 弃权清单 + 聚合未覆盖清单
```

复杂度：每实体 MRF 变量消除为指数于树宽的精确推断，实际节点数 $\le 40$、树宽小，毫秒级；全语料（数百实体 × 数千比较）分钟级。计算不是瓶颈，校准数据量才是。

### 5.3 贡献划分：新 vs 复用

| 部件 | 状态 | 来源/血统 |
|---|---|---|
| Visio XML → 感知层金标准（免费锚点 + 渲染校验 + 三分协议） | 【创新】资源与协议 | 本项目路线A |
| 两层潜在模型 + $D = \eta \oplus \varepsilon$ 分歧解码 | 【创新】形式化 | 与信道译码同构 |
| 端到端复合通道校准（相关性吸收） | 【创新】设计原则 | 端到端校准思想 |
| 节点潜在状态归属解码（星型混淆的结构化解） | 【创新】 | 类比谱定位 |
| 锚点校准的一致性迁移诊断 | 【创新组合】 | Dawid–Skene / Platanios 血统 |
| GLMM / 经验贝叶斯收缩 | 【成熟】 | Gelman & Hill; Efron & Morris |
| Chernoff / Hoeffding / Fréchet 界 | 【成熟】 | 经典 |
| Chow 弃权 + 风险–覆盖 + 共形阈值 | 【成熟】 | Chow 1970; El-Yaniv & Wiener; Vovk; Angelopoulos |
| 密度比域适应 | 【成熟】 | Sugiyama et al. |
| 感知通道本体（VLM/OCR/YOLO）、匈牙利指派、四层节点匹配 | 【复用】 | sc2 方案既有 |
| 文本/表格解析与编译 $\kappa_T, \kappa_B$ | 【复用】 | 既有工具 |

**论文的方法贡献集中在**：两层模型与解码公式（§1–2）、校准协议（§2.3, §3）、归属解码（§3.3）、迁移诊断（§3.4）、三个命题（§4）。感知与匹配全部声明为可替换的工程部件——**方法不依赖任何特定 VLM/检测器，这正是它区别于"又一个 VLM pipeline"的论文身份。**

---

## 6. 与方向A（上下文聚合）的接口（D10）

**聚合 = 召回受限、可能错配的检索通道。** $\mathrm{Agg}: D \to \hat{\mathcal{V}}(e) \subseteq \mathcal{V}(e)$，其两类误差以相反方式进入框架：

1. **漏聚合（召回不足）→ 只产生漏检。** 漏掉的视图对之间的不一致**在数学上不可见**——没有任何比较发生。框架中的位置：系统级召回的因子分解
$$\mathrm{Recall}_{\mathrm{sys}} \;=\; \underbrace{P(\text{Agg 找齐相关视图对})}_{\text{方向A}} \times \underbrace{P(\text{检出} \mid \text{找齐})}_{\text{ACDD 功效}}$$
**含义**：(i) ACDD 的评测必须条件化于"聚合正确"（用 oracle 聚合或人工核对的视图对），否则测的是两个方向的乘积；(ii) 方向A的改进可独立发表，ACDD 把第二因子做到有理论保证——两个方向各自有干净的贡献边界，这是项目"两个正交方向"定位在指标层面的实现。
2. **错聚合（假视图对）→ 产生"真实的假分歧"。** 把不同实体的图和表配对，比较出的分歧是**真实的**（两份内容确实不同）但**不是文档错误**——它是实体 Resolution 误差。框架中的位置：把聚合错误率 $p_{\mathrm{agg}}$ 并入 $L_0$（噪声底的一个成因）：$L_0(\delta) \leftarrow p_{\mathrm{agg}} \cdot \mathbf{1}[\delta \text{ 可由随机视图对产生}] + \dots$。$p_{\mathrm{agg}}$ 的估计：变异引擎探测（注入已知跨实体配置）或人工抽样审计。

3. **单视图兜底**：图内自洽性（如 decision 节点分支标签完备性）与表内自洽性（步骤编号连续性——语法层检查，`srs_gjb_compliance_scan` 既有能力）不需要聚合，作为 ACDD 的退化模式保留，保证聚合缺口期方法仍有输出。

**给方向A的输出规范（契约）**：Agg 须为每个视图对输出匹配置信度；ACDD 用它门控比较（低置信 → 弃权而非比较），并把未覆盖清单回传——这是两个方向之间唯一的接口，保持松耦合。

---

## 7. 消融与评测设计（D11）

### 7.1 数据划分（防泄漏是第一原则）

- 锚点三分，**文档级分块**：C3 训练池（~50%）/ 校准池（~25%）/ 评测池（~25%），LODO 旋转使全部锚点轮流服务校准（层次模型下数据效率最大化）。
- 75 个真实不一致**只进评测、永不进训练/校准/先验**（反循环，见 7.4）。

### 7.2 变异注入设计

- **文本侧变异**（8 类算子作用于 table.csv / text.txt）：全部 16 份文档可注入。
- **图像侧变异**（重渲染 Visio 后替换 PNG）：仅锚点图可行（需 XML 可编辑）——注意图像侧变异同时检验"通道能否感知被修改的图"，等于把感知层与文档层一起测试，需与文本侧结果分开报告。
- 注入密度对齐真实基础率（$\pi \in [0.01, 0.1]$ 梯度扫描），防止评测分布人为抬高 $\pi$ 使 $\pi > p$ 过于容易。

### 7.3 基线

| 基线 | 定义 | 检验什么 |
|---|---|---|
| B1 裸 VLM | 直接问 VLM"此图与此表是否一致+置信度" | 判别式端到端的上限/下限 |
| B2 未校准多数投票 | 通道输出逐元素多数表决，分歧计数超阈值即报 | 校准的增益 |
| B3 规则检测器 | 语法层规则（编号连续、ID 重复等） | 语法层之外的增益 |
| B4 无锚一致性检测 | 纯 Platanios 式通道一致性，无金标准 | 锚点资源的价值 |
| B5 单通道校准 | 仅 C1 或仅 C3 + 命题 1 后验 | 融合的增益 |
| 上界参照 | oracle $\theta$（用评测池真值）+ 因子化联合解码 | 校准误差的代价 |

### 7.4 指标与反循环

- **检测性能**：AUROC / AUPRC（以 $q_\delta$ 为分数）、按变异类型的召回、精确率（Wilson 区间）。
- **校准性能（头牌指标）**：可靠性图 + ECE。方法的卖点即"后验有概率语义"——ECE 显著优于 B1/B2 是核心证据。
- **风险–覆盖曲线**：$R(\varphi)$ 实测 vs 命题 3 预测的前沿形状；弃权率随 §3.4 漂移诊断触发率的联动（注记 2 的实证）。
- **FPR 有限样本有效性**：共形保证的实证检查（目标 $\alpha$ vs 实测 FDR）。
- **真实 75 条**：precision@$k$ + 双人独立裁决（报告 kappa）；不做召回声明（无完备金标准）。
- **反循环协议**：$\Sigma_{\mathrm{mut}}$ 先验只用算子子集 $T_{\mathrm{prior}}$（如 id/name/value），评测在其余算子 + 真实 75 条上；另做 $\pi$ 与签名先验的敏感性分析（$\pi \in [0.005, 0.2]$），报告结论对先验误设的稳健性。
- **统计功效诚实声明**：75 条真实不一致按类型分层后每格常 < 10，任何 per-type 声明配区间；主声明用汇总指标。

### 7.5 消融矩阵

| 消融项 | 关闭什么 | 预期信号 |
|---|---|---|
| A-1 无校准 | $\theta \to$ 手工常数 | ECE 崩、FP 升 |
| A-2 无收缩 | 分层 → 全池化点估计 | 小文档上 $\theta$ 估计不稳 |
| A-3 因子化融合 | 端到端 → 独立朴素 Bayes | 相关性导致 FP 升（§3.1 实证） |
| A-4 无归属 | 星型 MRF → 平坦分歧计数 | 漏检/误报集中于星型形态 |
| A-5 强制分类 | 弃权关闭（$\tau^\pm$ 收敛） | 风险–覆盖增益消失 |
| A-6 无迁移诊断 | 锚点 $\theta$ 直用 | PNG-only 子集上性能落差 |
| A-7 无变异先验 | $\Sigma_{\mathrm{mut}} \to$ 均匀 | 稀疏签名类型的后验变保守 |
| A-8 无规范化 $N$ | 良性变异不商掉 | 标签类 FP 爆炸 |

---

## 8. 命名与贡献声明（E12）

### 8.1 候选名

1. **ACDD** — Anchor-Calibrated Disagreement Decoding（保留原名；"decoding"在 §0.1 的译码意义下是严格的）。
2. **DECAL** — Disagreement dECoding with Anchor-caLibration（短、可读、去缩写噪音）。
3. **BEACON** — Bayesian Evidence with Anchor-Calibrated Observation Noise（"beacon/锚"意象贴合，Bayesian 身份前置）。
推荐：正文用 **ACDD**（描述性最强、审稿零成本），系统名可用 DECAL。

### 8.2 贡献声明草稿（动词开头，每条一句）

- **C1**：Formalize cross-view consistency checking of GJB-style SRS documents as a two-layer latent model that separates perceptual extraction error from document-level inconsistency, with embedded Visio XML repurposed as a free perception-layer gold standard for error-model calibration.
- **C2**：Derive a provable separation condition ($\pi > p$) with Chernoff-type exponential error decay and cause-level block correction, characterizing exactly when calibrated disagreement decoding is consistent, when it degrades to abstention, and why uncalibrated confidence lacks probabilistic meaning.
- **C3**：Introduce an anchor-calibration protocol combining end-to-end composite-channel calibration (absorbing correlated errors), hierarchical shrinkage across documents, attribution decoding over latent node states (resolving the star confound), and agreement-based error transfer for anchor-free figures.
- **C4**：Demonstrate on 16 real military SRS documents with a deterministic mutation engine and 75 human-adjudicated real inconsistencies that ACDD improves precision at matched recall over uncalibrated majority voting, bare-VLM judgment, and rule-based baselines, while providing distribution-free false-discovery control via conformal thresholds.

---

## 9. 脆弱点清单（诚实标注：哪些假设最可能被现实打破）

1. **$\pi > p$ 可能不成立**（最高风险）。困难图上边级 $p$ 现实可达 0.3–0.4，而 $\pi$ 天然小。后果：单元素签名类型退化为"只能弃权"，方法从"检测器"收缩为"分诊器"。缓解：融合压 $p$、簇签名、弃权；**声明必须按签名类型分层，不做总体声明**。
2. **锚点选择偏差 + 相关性静默失效**。"有 Visio XML"与作者工具链相关 → 锚点非随机样本；最坏情形是所有通道在某种新图风格上**共享盲区**（一致地错）——此时 (a) 类诊断（基于分歧）失效。缓解：$\phi$ 空间支持性检查 + 人工抽查弃权样本。残余风险不可消除，只能诚实报告。
3. **变异先验的循环性与代表性**。$\Sigma_{\mathrm{mut}}$ 与评测共用引擎（已用 $T_{\mathrm{prior}}$ 拆分缓解）；更深的隐患是真实不一致的分布与注入分布不同（真实错误更微妙、更稀疏）。缓解：敏感性分析 + 真实 75 条上的校准检查。
4. **文本编译器 $\kappa_T$ 非零误差**。"主事件流 → 图"的编译规则有解释空间（分支语义、复合步骤拆分）；无金标准可校准。缓解：确定性编译 + 合成文本用例验证 + $p_\kappa$ 进入 $L_0$；标签粒度不一致的分歧默认路由弃权。
5. **锚点有效性假设 $X_I^{\mathrm{vis}} = X_I$**。XML 与文档实际渲染的 PNG 可能不同步（过期导出）。缓解：渲染一致性抽查（算法 1 第 2 行）；抽查发现不同步率若 > 2% 需剔除并重新评估锚点规模。
6. **良性变异边界（$N$ 的不完美）是误报的现实主源**。"合理差异 vs 真实矛盾"的边界对标签类元素本质模糊——形式化在 $\cong$ 里，但 $\cong$ 是人造的。缓解：边界相似度 → 弃权带；`mutate_semantic_preserve` 正样本校准 $N$。
7. **节点对齐歧义**。重复结构（多个"是/否"决策节点、相似步骤名）下 TopK 匹配可能都不对。缓解：坐标先验 + $\mu$ 边际化 + 歧义高时弃权边类比较；星型 MRF 部分吸收。
8. **75 条真实不一致的评测功效**。分类型后每格样本极小，任何 per-type 精度声明区间很宽；$\kappa$ 若 < 0.6 则裁决协议本身存疑。
9. **聚合召回是系统召回的天花板**。ACDD 的一切指标条件于 $\mathrm{Agg}$ 找齐视图对；论文中必须显式声明该条件化（§6 的因子分解），否则被审稿人指控夸大。

---

## 10. 参考文献（成熟技术出处）

- Chow, C.K. (1970). On optimum recognition error and reject tradeoff. *IEEE Trans. Information Theory*.
- Chernoff, H. (1952). A measure of asymptotic efficiency for tests of a hypothesis based on the sum of observations. *Ann. Math. Statist.*
- Hoeffding, W. (1963). Probability inequalities for sums of bounded random variables. *JASA*.
- Benjamini, Y. & Hochberg, Y. (1995). Controlling the false discovery rate. *JRSS-B*.
- Dawid, A.P. & Skene, A.M. (1979). Maximum likelihood estimation of observer error-rates using the EM algorithm. *JRSS-C*.
- Efron, B. & Morris, C. (1975). Data analysis using Stein's estimator and its generalizations. *JASA*.
- Gelman, A. & Hill, J. (2006). *Data Analysis Using Regression and Multilevel/Hierarchical Models*. Cambridge.
- Kuhn, H.W. (1955). The Hungarian method for the assignment problem. *Naval Research Logistics*.
- El-Yaniv, R. & Wiener, Y. (2010). On the foundations of noise-free selective classification. *JMLR*.
- Vovk, V., Gammerman, A., Shafer, G. (2005). *Algorithmic Learning in a Random World*. Springer.
- Angelopoulos, A.N. & Bates, S. (2021). A gentle introduction to conformal prediction and distribution-free uncertainty quantification. arXiv:2107.07511.
- Bates, S., Angelopoulos, A.N., et al. (2021). Distribution-free, risk-controlling prediction sets. *JACM*.
- Platanios, E., Blum, A., Paul, D., Mitchell, T. (2014). Estimating accuracy from unlabeled data. *UAI*.
- Whitehill, J., et al. (2009). Whose vote should count more: Optimal integration of labels from labelers of unknown expertise. *NeurIPS*.
- Sugiyama, M., Kanamori, T., Hachiya, T. (2012). *Density Ratio Estimation in Machine Learning*. Cambridge.
- 项目内部：`docs/srs_project/sc2_flowchart_usecase_plan.md`（路线A/B、四层匹配）；`tools/srs_mutation_engine.py`（8 类变异算子）；`knowledge/srs_kb.json`（单位族/同义词典）；Bendík 等依赖图+SAT 方向的对比定位见 `docs/srs_project/literature_survey/`（待补充正式引用）。
