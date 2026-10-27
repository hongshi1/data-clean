# EVC-Verifier: 证据注意力约束类型化验证算法
**E**vidence-attended, constraint-typed **V**erifier for SRS inconsistency **C**hecking

> 版本: 设计稿 v2.0 | 2026-10-08
> 原则: 每类不一致用其**最小完备复杂度**的求解器; 统计判别只处理随机残差; 证据检索提供可解释依据

---

## 1. 问题形式化

**输入**: SRS文档 $D$, 证据单元集 $U = \{(u_i, m_i, \ell_i)\}_{i=1}^{N}$,
其中 $u_i$为单元文本(表格行/图节点/正文条款), $m_i \in \{\text{text},\text{table},\text{diag}\}$为模态,
$\ell_i$为位置(章节)。

**声明**: $c = (s, r, o)$ — 主体-关系-宾语三元组(由claim编译器产生), 文本记 $\bar{c}$。

**待检对**: $(c^p, c^h)$ — 两处对同一实体 $s$ 的声明。

**输出**: $y \in \{\text{inc}, \text{con}, \text{abstain}\}$ + 求解器 $\sigma$ + 证据链 $\mathcal{E}$ + 置信 $\gamma$。

**核心假设(设计依据)**: 不一致类型空间 $\mathcal{T} = \{\text{NUM}, \text{LOGIC}, \text{RULE}, \text{TERM}, \text{STRUCT}, \text{SEM}\}$,
前五类存在**可靠多项式时间判定器**(形式化/规则/度量), 仅SEM类(语义惯例歧义)存在不可约随机性
——故算法的任务是**正确分派 + 证据检索 + 残差统计推断**。

---

## 2. 架构总览

```
(c^p, c^h) ──→ [M1 证据召回] ─→ E_k ⊂ U (top-k)
                    │
              [M2 子注意力重排] ─→ α ∈ Δ^k, coverage κ
                    │
              [M3 约束类型化] ─→ τ ∈ T
                    │
              [M4 异构求解] ─→ σ ∈ {SMT, RULE, DIST, SET, NLI}
                    │
              [M5 证据融合] ─→ Dempster-Shafer组合 → y, γ, 证据链
```

---

## 3. 模块设计

### M1 证据召回(多通道, 排序学习)

$$\text{score}(u_i, c) = \lambda_1 \cos\big(f_d(u_i), f_d(\bar{c})\big) + \lambda_2 \cdot \text{BM25}(u_i, \bar{c}) + \lambda_3 \cdot \mathbb{1}[\ell_i \sim \ell_c]$$

- $f_d$: BGE-large-zh稠密编码器(冻结, 局部微调可选)
- 三通道线性加权, $\lambda$ 在验证集上由 **rankregression** (NDCG@k目标) 优化
- 复杂度: ANN检索 $O(N\log N)$

### M2 子注意力重排(核心创新①: 证据感知的声明表示)

证据单元分解为**子跨度** $u_i = \{u_{i,1},...,u_{i,n_i}\}$(行→单元格/节点→标签/条款→分句),
**IDF加权子注意力**:

$$\alpha_{i,j} = \frac{\exp(\langle q, k_{i,j}\rangle / \sqrt{d}) \cdot \text{idf}(u_{i,j})}{\sum_{i',j'} \exp(\langle q, k_{i',j'}\rangle / \sqrt{d}) \cdot \text{idf}(u_{i',j'})}$$

- $q = f_q(\bar{c})$ (query投影), $k_{i,j} = f_k(u_{i,j})$ (key投影) — **双线性对齐**, $f_q, f_k$ 可训练(LoRA on BGE)
- 输出: 重排序证据 $\tilde{\mathcal{E}}$、注意力热图 $\alpha$、**覆盖率** $\kappa = \max_{i,j}\text{sim}(q, k_{i,j})$

**理论意义**: $\kappa$ 是"缺失声称"的**语义级核验统计量** —
确定性核验(字符串匹配)只覆盖精确匹配, 子注意力把核验推广到语义匹配
(我们在数据中发现19.4%的"缺失"声称被精确匹配反驳, $\kappa$把此推广到近似匹配)。

### M3 约束类型化(分派函数)

$$\tau = g(c^p, c^h) \in \arg\max_{t \in \mathcal{T}} P_\theta(t \mid c^p, c^h, \mathcal{E})$$

- 轻量分类器(逻辑回归/小MLP) on 手工特征: 数值单位计数、时序词、规则关键词、引号实体、缺失句式
- **不确定性感知分派**: 若 $\max_t P < \theta_\tau$, 标记多类型并行求解(容错)

### M4 异构求解(每类最小完备复杂度)

| τ | 求解器 σ | 判定 | 复杂度 | 输出置信 |
|---|---|---|---|---|
| NUM | SMT(Z3): $\varphi = \bigwedge_i \text{unit-normalize}(c_i) $ | $\text{UNSAT} \Rightarrow \text{inc}$ (**带proof**) | 多项式(线性算术) | 1.0 |
| LOGIC | SMT时序/图拓扑(seqlen/seqdiff) | 环/序矛盾 $\Rightarrow$ inc | 多项式 | 1.0 |
| RULE | 规则引擎(120条GJB, 可追溯) | 规则命中 $\Rightarrow$ inc | 线性扫描 | 1.0 |
| TERM | 编辑距离+词典投影 | $d(a,b) \le \theta_T$ 且词典不同条目 | 线性 | 0.95 |
| STRUCT | 集合比对+证据核验 | 精确反驳 $\Rightarrow$ con; $\kappa \ge \theta_\kappa$ 软反驳 $\Rightarrow$ con | 线性 | 0.9/κ |
| SEM | NLI后验(唯一统计通道) | $p = P(\text{inc} \mid \bar{c}^p, \bar{c}^h; \theta)$ | 推理 | 见M5 |

**SEM通道的NLI**以**证据调制后验**:
$$p' = p \cdot \big(1 - \lambda_g \cdot \max(0, \kappa - \kappa_0)\big)$$
(注意力门控: 证据覆盖率越高, 对"矛盾"判断越谨慎 — 软核验的决策论形式)

### M5 证据融合(核心创新②: Dempster-Shafer多求解器证据组合)

各求解器输出**信念质量函数** $m_\sigma: 2^{\Theta} \to [0,1]$ ($\Theta = \{\text{inc}, \text{con}\}$):
- 确定性求解器: $m_\sigma(\text{inc}) = 1$ (Z3 UNSAT) 或 $m_\sigma(\text{con}) = 1$
- TERM/STRUCT: $m_\sigma(\text{inc}) = r_\sigma$, $m_\sigma(\Theta) = 1 - r_\sigma$ (可靠性留不确定)
- NLI: $m(\text{inc}) = p'^2, m(\text{con}) = (1-p')^2, m(\Theta) = 2p'(1-p')$ (置信度平方折扣, 模糊性显式化)

**Dempster组合规则**(多求解器冲突消解):
$$m_{1 \oplus 2}(A) = \frac{\sum_{B \cap C = A} m_1(B) m_2(C)}{1 - K}, \quad K = \sum_{B \cap C = \emptyset} m_1(B) m_2(C)$$

- 冲突度 $K$ **本身是信号**: $K > \theta_K$ → 触发 **abstain**(升级LLM/人工) — 冲突=不可判别的形式化定义
- 决策: $\arg\max_A \text{Bel}(A)$, 置信 $\gamma = \text{Bel} - \text{Pl}$ (信念-似真差)

**性质**: 确定性证据(质量1)在组合中**支配**统计证据 — 形式化了"Z3短路NLI";
abstain率-精度权衡由 $(\theta_\kappa, \theta_K)$ 控制, 可画risk-coverage曲线。

---

## 4. 训练目标(仅统计通道可训练)

$$\mathcal{L} = \underbrace{\mathcal{L}_{\text{cls}}}_{\text{SEM通道NLI}} + \lambda_1 \underbrace{\mathcal{L}_{\text{rank}}}_{\text{M1检索}} + \lambda_2 \underbrace{\mathcal{L}_{\text{align}}}_{\text{M2注意力}} + \lambda_3 \underbrace{\mathcal{L}_{\text{calib}}}_{\text{M5置信}}$$

- $\mathcal{L}_{\text{cls}}$: CE + **难例负样本**(良性省略作consistent难负) + CCT反事实一致性($\lambda\cdot$对称KL) + PAWS释义难负(治"表面异→误报"病)
- $\mathcal{L}_{\text{rank}} = -\log \frac{e^{\text{score}(u^+, c)}}{\sum_j e^{\text{score}(u_j, c)}}$ — 证据检索的对比排序(正例=同锚点证据, 负例=同文档其他单元)
- $\mathcal{L}_{\text{align}}$: 子注意力对齐监督(α应集中于支撑claim的子跨度 — 来自锚点对齐的弱标注)
- $\mathcal{L}_{\text{calib}}$: 置信校准(ECE惩罚) — 服务abstain决策的可靠性

**非对称可靠性建模**(可选扩展): 银标噪声下, 正侧(双LLM一致)可信度高、负侧(单LLM)低 → nnPU风险估计器(π=场景先验)

---

## 5. 推理流程与复杂度

```
单个(c^p,c^h): 检索O(N log N) → 注意力O(k·n̄·d) → 类型化O(|F|) → 求解O(多调Z3/线性) → 融合O(|σ|²)
文档级批量: 检索引共享(一次索引, 多claim查询), Z3增量求解(push/pop)
```

## 6. 与"微调NLI"基线的本质区别(设计性声明)

| 维度 | 微调NLI | EVC-Verifier |
|---|---|---|
| 形式化 | 黑盒后验 | 类型化约束求解+DS融合, 确定性支配性可证明 |
| 证据 | 无 | 双线性子注意力+IDF, coverage统计量有决策论语义 |
| 错误结构 | 均匀统计误差 | NUM/LOGIC/RULE=0(形式化), 误差集中在SEM残差(可abstain) |
| 可解释 | 概率 | Z3证明/规则条目/注意力热图/DS信念分解 |
| abstain | 无 | 冲突度K触发(形式化定义) |

## 7. 消融设计(每模块贡献可测)

1. 完整EVC vs 去M5(平均融合) — DS融合的价值
2. 去M2(无子注意力, 检索top-1) — 注意力核验的价值
3. 去M4分派(全SEM通道) — 异构求解的价值(预期: NUM类从1.0降到~0.95)
4. 去M1-3(纯claim, 无证据) — 证据链的价值
5. $\kappa$门控开/关 — 软核验决策论的价值
