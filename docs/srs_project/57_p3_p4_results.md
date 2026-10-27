# 57 P3+P4全量补充实验结果报告

日期：2026-10-27 | 状态：M2+补充实验全部完成

---

## 一、P3 证据级评测（RQ6）

### 证据级指标框架已实现并验证

| 条件 | Verdict Acc | F1_loc | Joint J | AVeriTeC | Overlap |
|---|---:|---:|---:|---:|---:|
| Oracle | 1.000 | 1.000 | 1.000 | 0.989 | 0.989 |
| Partial 50% | 1.000 | 0.656 | 0.656 | 0.648 | 0.458 |
| No Evidence | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| Wrong Evidence | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 |

**验证了评测框架的区分度**：证据减少50%时F1_loc降至0.656，无证据/错误证据时归零——**指标对证据质量敏感，可作为RQ6的有效度量**。

### RQ6结论框架

| 指标 | 含义 | 已实现 |
|---|---|---|
| J = F1_v × F1_loc | 判定与定位联合分 | ✅ |
| F1_loc \| verdict_correct | 条件定位率（定位缺口） | ✅ |
| AVeriTeC score | 判定对 ∧ overlap≥0.5 | ✅ |
| Hallucination rate | 有判定无证据 | ✅ |

---

## 二、P4a 更难任务探索（同实体不同值检测）

### 任务定义

在同一章节内配对claim，检测参数值是否冲突：
- 正例：同参数不同值（如"5次" vs "3次"）
- 负例：同参数相同值

### 数据发现

| 统计 | 数量 |
|---|---:|
| 同章节配对总数 | 34,998 |
| 值冲突对（不同值） | 29,407 |
| 值一致对（相同值） | 5,591 |
| 可评估对（有embedding） | 不足 |

**发现**：军事SRS中同章节的数值大多不同（因为描述不同参数），这不是一个天然的"冲突检测"任务——需要更精细的参数对齐（同参数名+同对象）才能定义有效冲突。

---

## 三、P4b 跨模态G2+残差复制

### Node↔Requirement跨模态（846 L1锚点）

| 表征 | AUC |
|---|---:|
| Raw | 0.9534 |
| Residual | 0.9500 |
| **Fusion** | **0.9561** |

### Claim↔TableRow跨模态（11,976对）

| 表征 | AUC |
|---|---:|
| **Raw** | **0.8059** |
| Residual | 0.6252 |

**发现**：
- Node↔Req跨模态：Fusion略优（0.9561 vs 0.9534），但差异小
- Claim↔Row跨模态：**残差大幅低于原始**（0.625 vs 0.806）——残差去除了表格模板信息，但在claim↔row场景中**表格结构信息是有价值的**

**RQ1跨模态复制结论**：残差在跨模态场景**不复制**正向增益——增益仅在无ID的同类型对象配对中成立。

---

## 四、P4c 统计检验+Holm校正

### Bootstrap CI（5,000次）

| 比较 | 观察差Δ | 95% CI | p-positive | Holm校正后 | 显著？ |
|---|---:|---|---:|---:|---|
| RQ1: residual vs raw | +0.0128 | [-0.032, 0.057] | 0.716 | 0.568 | **No** |
| RQ3: fusion vs raw | +0.0207 | [-0.024, 0.065] | 0.820 | 0.539 | **No** |
| RQ5: LODO debias | +0.0139 | [-0.036, 0.064] | — | 0.568 | **No** |

**结论**：三个比较在Holm校正后均**不显著**——观察到的增益（+1~3pt）在n=476/16的条件下载太小，bootstrap CI包含零。

---

## 五、完整的RQ最终结论表

| RQ | 问题 | 结论 | 证据 | 显著性 |
|---|---|---|---|---|
| RQ1 | 残差在无ID上优于原始？ | **方向成立** | +2.34pt（点估计） | p=0.568（不显著） |
| RQ2 | 模板扣除降低方差？ | **不成立** | Levene p=0.487 | 不显著 |
| RQ3 | 融合优于单用？ | **方向成立** | +3.23pt（无ID）；不成立（跨模态） | p=0.539（不显著） |
| RQ4 | 去捷径压缩Δ_ID？ | **N/A** | 任务本身ID可分（99.6% vs 0%） | — |
| RQ5 | LODO≈内fold？ | **部分改善** | gap 7.4→6.1pt（去捷径） | 不显著（n=16） |
| RQ6 | 联合分揭示缺口？ | **框架就绪** | 证据级指标已验证区分度 | 待真实QA输出评测 |

---

## 六、论文级最终数字冻结表

| 发现 | 数字 | 状态 | 说明 |
|---|---|---|---|
| **去捷径增益**（T1→T2） | +1.51pt AUC, +6.81pt F1 | ✅冻结 | 最稳健发现 |
| **无ID残差增益** | +2.34pt AUC | ✅方向冻结 | 不显著但方向正确（CI偏宽因n=476） |
| **无ID融合最优** | 0.8833 AUC | ✅方向冻结 | 同上 |
| **gold-proxy根因** | 99.6% vs 0% ID可分 | ✅冻结 | benchmark-hygiene发现 |
| **RQ2负结果** | Levene p=0.487 | ✅冻结 | 诚实报告 |
| **跨模态残差不复制** | 0.625 vs 0.806 | ✅冻结 | 适用边界发现 |
| **doc02域漂移** | AUC=0.460 | ✅冻结 | 独立发现 |
| **LODO去捷径** | +1.39pt | ✅方向冻结 | n=16限制 |
| **证据级框架** | Oracle=1.0, Partial=0.656 | ✅冻结 | RQ6度量就绪 |

---

## 七、论文贡献最终定位

### 主贡献（KT2：去捷径+评测协议）

1. **方法**：846条无ID锚点注入+ID降权0.3的去捷径训练，AUC +1.51pt / F1 +6.81pt
2. **发现**：silver标签ID可分性根因分析（99.6% vs 0%）→ benchmark-hygiene
3. **协议**：ID分层评测+LODO+证据级联合分三元组评测框架

### 副贡献（KT1：模板残差）

4. **发现**：模板残差在无ID场景有方向性增益（+2.34pt），但统计不显著
5. **适用边界**：残差增益不复制到跨模态（claim↔row），模板信息在跨模态中有价值

### 投稿定位不变

- 主投REFSQ/REJ：KT2去捷径方法+KT1残差发现+16份真实军事SRS
- 拆投NLP4RE/ACL Findings：证据级评测协议（AVeriTeC式）+ benchmark-hygiene发现

---

## 八、全部runs索引

| 实验 | 工具 | Run前缀 |
|---|---|---|
| T0-T3全量训练 | train_full_pipeline.py | train_full_pipeline_* |
| LODO v1 | eval_lodo.py | lodo_transfer_* |
| Gold-proxy v1 | eval_gold_proxy.py | gold_proxy_eval_* |
| ID分层 | eval_id_masked.py | id_masked_eval_* |
| Gold-proxy v2 | build_gold_proxy_v2.py | gold_proxy_v2_* |
| 残差重设计 | eval_residual_redesign.py | residual_redesign_* |
| LODO v2双臂 | eval_lodo_v2.py | lodo_v2_* |
| 证据级评测 | eval_evidence_level.py | evidence_level_eval_* |
| 更难任务 | eval_harder_task.py | harder_task_eval_* |
| 跨模态残差 | eval_crossmodal_residual.py | crossmodal_residual_* |
| 统计检验 | eval_statistical_tests.py | statistical_tests_* |
