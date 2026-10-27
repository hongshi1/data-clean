# 52 科研设计方案：模板残差表征×弱标签去捷径

日期：2026-10-22 | 状态：设计方案 | 依赖：51号文档（两个关键技术定义）+ 48号文档（已有实验体系）

---

## 一、研究问题体系（6个可证伪RQ）

### 关键技术一：模板残差表征

| RQ | 问题 | 可证伪形式 |
|---|---|---|
| RQ1 | 残差表征是否在无ID子集上比原始表征更具身份判别力？ | AUC(residual) > AUC(raw) on ID-free subset |
| RQ2 | 模板扣除是否降低跨文档性能方差？ | Levene检验：Var(AUC_LODO | residual) < Var(AUC_LODO | raw) |
| RQ3 | 原始⊕残差融合是否优于任一单用？ | F1(fusion) > max(F1(raw), F1(residual)) |

### 关键技术二：去捷径迁移+证据级判定

| RQ | 问题 | 可证伪形式 |
|---|---|---|
| RQ4 | 去捷径训练是否压缩ID分层AUC差？ | Δ_ID(post) < Δ_ID(pre)，当前基线Δ=0.2358 |
| RQ5 | silver训练的表征在gold-proxy/LODO上是否不劣于内fold？ | AUC(LODO) ≈ AUC(inner)，Wilson CI重叠 |
| RQ6 | 判定∧定位联合分是否揭示纯verdict掩盖的性能损失？ | F1_loc|verdict_correct < F1_verdict（差值即定位缺口） |

---

## 二、模板残差表征的数学形式化

### 基线估计（留一文档防泄漏）

```
输入：条目i有冻结向量x_i ∈ R^1024，元组(kind_i, section_i, doc_i)

模板基线（按kind×章节格估计）：
  μ_{k,s}^{(-d)} = (1/15) Σ_{d'≠d} mean{x_i : kind=k, section=s, doc=d'}

残差表征：
  r_i = x_i − μ^{(-d(i))}_{kind_i, section_i}

可选白化：
  r̃_i = Σ^{-1/2} · r_i

融合表征：
  z_i = [x_i ; λ·r_i]，λ为可调权重
```

### 基线三档消融

| 基线 | 定义 | 来源 |
|---|---|---|
| (a) 统计均值 | μ_{k,s}按kind×section格均值 | feature_snapshot现有数据 |
| (b) 章节模板文本中心 | 16份文档对齐章节的聚心 | sections.jsonl章节树 |
| (c) GJB规则约束模板 | 120条规则转译的结构约束投影 | gjb_438c_rules_full.json |

### 与现有A矩阵的扩展

```
现有A矩阵：A1(native) / A2(Procrustes) / A3(projection) / A4(gate) / A4-leak(oracle)
新增行：  A1r(native+residual) / A3r(projection+residual) / A4r(gate+residual)
新增列：  ID分层（含ID列 / 不含ID列 / 全集列）
```

### 预期增益最大的场景

跨模态G2（Procrustes恢复81%语体鸿沟）——模板扣除后残差应更好地编码"哪些内容偏离了模板共性"，在跨模态对齐中提供额外区分信号。

---

## 三、去捷径实验协议

### 捷径量化

```
Δ_ID = AUC_full − AUC_IDmask
  其中AUC_IDmask = 输入遮蔽ID token后重编码的AUC
按fold分解捷径依赖度
silver正例ID占比 = 100%（当前所有P1正例都含ID）
```

### 修复三路

| 路径 | 方法 | 数据基础 |
|---|---|---|
| ① ID降权 | 含ID正例在训练中降低权重 | training_pairs现有标签 |
| ② 注入无ID正例 | L1 title-bridge 846条(gold) + L2 fuzzy(校准P=0.9505) | anchor_expansion_v1 |
| ③ 强制分层报告 | 含/不含ID分层AUC作为所有实验的标准列 | 48号预注册 |

### 证据级判定指标

```
联合分 J = F1_verdict × F1_loc

F1_loc定义：
  - 每条verdict输出对应证据块引用（evidence_refs）
  - 与gold证据块计算overlap F1
  - NIE正确弃权 → F1_loc = 1.0
  - 无中生有（有verdict无证据）→ F1_loc = 0

辅助指标：
  - AVeriTeC分：判定对 ∧ overlap ≥ 0.5
  - 条件量F1_loc|verdict_correct：判定≠定位的主诊断量
```

---

## 四、实验总矩阵（2×3×3增广设计）

| 表征 | ID条件 | 评测域 | 主指标 |
|---|---|---|---|
| raw (A1) | 含ID | 内fold | AUC, F1, FM |
| raw (A1) | 不含ID | 内fold | 同上 |
| residual (A1r) | 含ID | 内fold | 同上 |
| residual (A1r) | 不含ID | 内fold | 同上 |
| fusion (A1f) | 全集 | 内fold | 同上 |
| 各最优配置 | 全集 | gold-proxy | AUC + Wilson CI |
| 各最优配置 | 全集 | LODO-16 | AUC + 学习曲线 |
| 各最优配置 | 全集 | 跨模态G2 | R@1, MRR |

**统计检验**：文档级paired bootstrap + Holm校正（6个RQ的多重比较）

---

## 五、论文贡献定位

| 关键技术 | 贡献类型 | 具体内容 |
|---|---|---|
| KT1 模板残差 | **method** + **finding** | 刚性模板文档的共性/个性分解表征 + 模板淹没度首次量化（Δ_AUC可引用） |
| KT2 去捷径迁移 | **benchmark/protocol** + **method** | ID分层+LODO+判定∧定位联合评测协议 + 去捷径训练方法 |

### 投稿定位

| 目标 | 级别 | 理由 |
|---|---|---|
| 主投 | REFSQ / REJ | RE方法创新 + 真实军事语料 |
| 拆投 | NLP4RE / ACL Findings | 证据级评测协议（AVeriTeC式） + 108条定位gold |
| 协议贡献 | benchmark track | ID分层+LODO+联合分评测基准 |

### 诚实边界声明

- 16域统计功效弱：只报Wilson CI + 学习曲线，不宣称普适迁移
- 模板残差在"无格式约束的通用文档"上不适用（GJB刚性结构是前提）
- 证据级判定的gold仅108条（在建），不足以支撑大规模benchmark声明

---

## 六、执行排期（与现有体系衔接）

| 阶段 | 任务 | 依赖 | 预估 |
|---|---|---|---|
| Phase 1 | 实现模板残差计算（基线a统计均值版） | feature_snapshot_v1 | 1天 |
| Phase 2 | A1r/A3r/A4r三行消融 | 现有train_shared_projection | 2天 |
| Phase 3 | ID遮蔽重编码 + Δ_ID量化 | feature_snapshot + 后处理 | 1天 |
| Phase 4 | 去捷径训练（降权+注入） | training_pairs + anchor_expansion | 2天 |
| Phase 5 | gold-proxy / LODO评测 | 现有评测框架 | 1天 |
| Phase 6 | 证据级判定指标实现 | 48号E矩阵框架 | 2天 |
| Phase 7 | 论文撰写与统计检验 | 全部实验结果 | 5天 |
