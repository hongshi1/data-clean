# 58 技术可信度审计报告：特征提取与上下文关联

日期：2026-10-27 | 方法：纯代码审计+数据资产抽查（25项逐条核验）

---

## 一、总览：按可信度排序的完整清单

### D级：声明与实现不符 / 标签反转（必须修复）

| # | 问题 | 位置 | 影响 |
|---|---|---|---|
| **D1** | LODO模板基线被最后一个doc覆盖（声称留一实际没排除） | eval_residual_redesign.py:111, eval_crossmodal_residual.py:77, train_full_pipeline.py:93-97 | **所有残差AUC数字需重跑**——基线既非LODO也非一致估计 |
| **D2** | L2 fuzzy锚点被当负例（与锚点工具自身矛盾） | eval_residual_redesign.py:207-211 | no-ID测试集负例~95%错标，AUC绝对值失效 |
| **D3** | 正文claim过滤条件是死代码 | build_structured_corpus.py:296-299 | 全部句子入claims（12517条），下游统计分母污染 |
| **D4** | T1的λ在测试集上选模型 | train_full_pipeline.py:430 | 测试集模型选择，报告数字乐观有偏 |

### C级：启发式未验证（需要校准或人工验证）

| # | 问题 | 位置 | 具体缺陷 |
|---|---|---|---|
| C1 | NUM_RE数值+单位提取 | build_structured_corpus.py:36-39 | 章节号当数值；缺操作符；单位完整率仅3.6% |
| C2 | CandidateLink判定常数 | build_evidence_graph.py:179-208 | 0.7/0.15/0.32/0.28无任何校准；文档编号可伪造same_identity |
| C3 | 45动词白名单 | mine_function_predicates.py:43 | 正则first-hit-only；无精度评测；轻动词黑名单仅7词 |
| C4 | subject fallback=章节标题 | build_feature_matrix.py:469-506 | slot_fill率49.7%主要由兜底槽撑起 |
| C5 | α=5.0收缩参数 | 三个eval文件复制粘贴 | 无扫描无依据；单文档格子LODO权重仅1/6 |
| C6 | 精排融合公式 | rerank.py:73 | rmax/rrng量纲不稳定，换分布失效 |
| C7 | EMB_TH_LOCAL循环校准 | bge_threshold_sweep.py | 用词法启发式校准语义阈值，80对样本 |
| C8 | 表头假设rows[0] | 三处硬编码 | 每表系统性丢首数据行 |
| C9 | 快照200字符截断 | build_feature_snapshot.py:39 | 全部向量建立在截断文本上 |
| C10 | DenseHead查询无前缀 | heads.py:215 | 对照头协议违规，数字不可比 |
| C11 | de-bias注入跨fold泄漏 | train_full_pipeline.py:227 | 测试折对象经L1注入进训练 |
| C12 | classify_entity文档硬编码 | build_semantic_features_v2.py:458 | "-NBJK-"仅对单文档有效 |
| C13 | crossmodal非配对评测 | eval_crossmodal_residual.py:158 | 三arm共享rng，负例不同；claim↔row"正例"是章节共现 |

### B级：统计方法合理但校准有偏

| # | 问题 | 位置 | 状态 |
|---|---|---|---|
| B1 | L2 θ=0.9505校准不充分 | expand_diagram_anchors.py:343-399 | 随机易负例+同集选择；真实候选精度未知 |
| B2 | 846条L1 "gold"仅计数自验 | expand_diagram_anchoros.py:320-341 | 强信号但无外部验证 |
| B3 | Silver标签ID可分性 | build_training_pairs.py:251 | 已诚实声明：正例监督100%来自ID |
| B4 | MinerU置信度未传递 | content_list | 机会成本：全块等权 |
| B5 | IDF×max稀有主导风险 | heads.py:84-107 | 合理变体+长尾未分析 |

---

## 二、最严重的四个问题详解

### D1：残差实验的"LODO"是假的

**声称**：`docstring称"leave-one-doc-out with shrinkage"`

**实际**：
```python
# eval_residual_redesign.py:111
baselines[(kind, section)] = mu
# ← 循环遍历每个doc，每次覆盖同一个(key)
# 最终基线=排序最后的doc的LODO估计，应用于全部doc
```

**更糟**：`train_full_pipeline.py`的版本**连排除循环都没有**——包含自身的均值。

**影响**：RQ1的+2.34pt残差增益建立在这个bug上。

### D2：L2锚点标签反转

**矛盾**：
- `expand_diagram_anchoros.py`产出L2为**正向候选**（校准P=0.9505）
- `eval_residual_redesign.py:207-211`把它们标为**负例**（`label=0, basis="l2_fuzzy_negative"`）

**如果P=0.9505成立**，负例侧95%是错标→no-ID AUC不可信。

### D3：claim过滤死代码

```python
# build_structured_corpus.py:296-299
if not sentence_features["requirement_ids"] and not any(
    key in sentence_features for key in ("quantities", "modal_words")
):
    continue
```

`extract_features`返回的dict**永远含**`quantities`和`modal_words`键（可为空列表）——`"quantities" in dict`恒True→`any()`恒True→`continue`**永不触发**。

### D4：测试集模型选择

```python
# train_full_pipeline.py:430
if r["test"]["auc"] > best["test"]["auc"]:  # ← 用test AUC选λ
    best = r
```

---

## 三、修复优先级与影响评估

| 优先级 | 修复项 | 类型 | 影响范围 | 需人工？ |
|---|---|---|---|---|
| **P0** | D1 LODO基线修复 | 代码bug | 全部残差实验（3个脚本） | 否 |
| **P0** | D3 claim过滤修复 | 代码bug | structured_corpus→全部下游 | 否（但需重建资产） |
| **P0** | D2 L2语义裁决 | 设计决策 | no-ID test集 | **是**（L2到底是正例还是负例？） |
| **P1** | D4 λ选择改dev | 代码bug | T1报告数字 | 否 |
| **P1** | C11 跨fold泄漏 | 代码bug | T2/T3数字 | 否 |
| **P1** | C8 表头假设 | 代码bug | 每表丢1行×1207表 | 否 |
| **P2** | B1 L2重校准 | 校准改进 | 锚点质量 | 半（需人工抽样） |
| **P2** | B2 L1外部验证 | 标注 | 唯一"gold"底座 | **是**（抽100条双盲） |
| **P2** | C1-C13 | 各自校准 | 各自下游 | 多数可自动 |
