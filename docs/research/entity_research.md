# 多模态一致性检测调研报告

> 调研日期：2026-07-02
> 调研目的：搞清楚医疗多模态场景下"图片 vs 报告"不一致检测的真实做法，评估 NER、知识图谱、LLM 各自的角色，为项目选择务实方案。

---

## 一、医疗领域多模态一致性检测是怎么做的？

### 1.1 核心事实：主流方法不是 NER+规则，而是深度学习/MLLM

调研中发现，医疗影像-报告一致性检测存在**三条技术路线**，且 NER+规则**不是主流**：

| 路线 | 代表工作 | 核心机制 | 是否用 NER |
|------|----------|----------|------------|
| 特征对齐+去噪 | **FAMDR** (AAAI 2026) | 深度特征对齐 + 检索增强 + 像素/短语级定位 | **否** |
| 跨模态对比学习 | C2M-DoT (2026)、ICON (EMNLP 2024) | 多视图对比学习 + 语义匹配优化 | 否 |
| MLLM 推理 | **VDC** (ICLR 2024)、RADAR benchmark (2026) | 大模型生成问题→回答→评估一致性 | 否 |

### 1.2 FAMDR (AAAI 2026) 详细剖析

**论文**：FAMDR: Feature-Aligned Multimodal Denoising for Reliable Diagnostic Reconciliation
**作者**：Xun Liang, Zhiying Li, Hongxun Jiang（中国人民大学）
**链接**：https://ojs.aaai.org/index.php/AAAI/article/view/37623

**FAMDR 不用 NER**。它的核心观点是：现有方法把影像发现与临床病史之间的跨模态不一致当作"噪声"丢弃，但这些不一致其实是**临床有意义的信号**。框架包含四个协同组件：

1. **Noise-aware multimodal alignment（噪声感知多模态对齐）**：在对齐过程中保留判别性的差异特征，同时确保语义连贯性——即不是简单消除差异，而是"保留有意义的差异"。
2. **Cross-modal retrieval augmentation（跨模态检索增强）**：利用外部医学知识检索来解决模糊病例。
3. **Granular localization（粒度定位）**：使用自适应阈值（adaptive thresholding）在**像素级和短语级**定位噪声。
4. **Uncertainty quantification（不确定性量化）**：提供可靠的置信度估计。

**评估数据集**：扩展的 MIMIC-CXR 数据集，加入了专家标注的噪声和纵向记录。

**关键结论**：FAMDR 是纯深度学习方法，做的是特征空间的对齐和去噪，**完全没有用 NER 提取实体**，也不用规则判断矛盾。它把"不一致"当作需要定位和量化的信号，而不是需要规则匹配的实体对。

### 1.3 其他相关工作

- **RADAR (arXiv 2603.06681, 2026)**：3D影像放射报告审查的多模态 benchmark，评估一致性检测（agreement detection）、严重程度评估、编辑类型分类，模拟"初诊→审核"工作流。
- **ICON (EMNLP 2024 Findings)**：改进放射报告生成的报告间一致性，方法是从图像中提取病灶并检查特征——这里的"提取"是检测器/分割器，不是文本 NER。
- **C2M-DoT (2026)**：用多视图对比学习做跨模态一致性优化，通过域迁移网络增强图像-报告的语义匹配。

---

## 二、NER 在医疗冲突检测中的真实角色

### 2.1 NER 确实有用，但角色是"信息抽取前置步骤"，不是"冲突判断器"

调研发现，NER 在医疗文本处理中广泛使用（提取疾病、症状、药物、解剖部位等实体），但**NER 本身不判断矛盾**。典型流程是：

```
报告文本 → NER提取实体 → 实体链接到KG/ontology → 推理/比较 → 判断是否冲突
                              ↑
                         冲突判断在这里发生，不在 NER
```

### 2.2 实体矛盾判断的真实方法

实体提取出来之后，判断矛盾的方法有三种层次：

| 方法 | 机制 | 是否手写 | 代表 |
|------|------|----------|------|
| **规则/模板** | 预定义冲突表（如"肺炎"和"正常"互斥） | 是 | 早期临床决策支持系统 |
| **嵌入相似度** | 实体编码为向量，计算余弦相似度/距离 | 否（学习的） | 医学BERT、BioBERT |
| **LLM 推理** | 把两个实体/描述交给LLM判断是否矛盾 | 否（模型推理） | GPT-4、医学MLLM |

**关键发现**：现代系统倾向于用**嵌入相似度 + LLM 推理**的组合，而非纯规则。纯规则方法的瓶颈是医疗知识的组合爆炸——你无法穷举所有矛盾对。

### 2.3 医学NER工具的现实

医学 NER 有成熟工具：
- **scispaCy**（Allen AI）：医学领域 NER，链接到 UMLS/SNOMED CT
- **MedBERT/BioBERT**：预训练医学BERT，可微调做NER
- **AWS Comprehend Medical**：商用医学实体提取

但这些都是**抽取工具**，抽取后的矛盾判断仍需额外模块。

---

## 三、知识图谱在冲突检测中的真实用法

### 3.1 KG 不是用"contradicts 边"直接查的

调研中发现一个重要事实：**SNOMED CT 等 ontology 本身没有显式的 "contradicts" 关系边**。KG 的真实用法是：

1. **实体规范化（Entity Normalization）**：把"心影增大"、"cardiomegaly"、"心脏扩大"映射到同一个 SNOMED CT 概念节点，解决同义词问题。
2. **关系推理（Relational Reasoning）**：利用 "caused by"、"treats"、"belongs to" 等语义关系做**多跳推理**，判断两个诊断是否逻辑自洽。
3. **知识增强生成（Knowledge-Grounded Generation）**：用 KG 约束 LLM 输出的逻辑一致性。

### 3.2 SNOMED CT-powered KG (arXiv 2510.16899, 2025)

这篇2025年的工作清楚展示了KG的真实用法：
- 用 **SNOMED CT + Neo4j** 构建结构化医学知识图谱
- 临床实体（疾病、症状、药物）作为**节点**
- 语义关系（"caused by"、"treats"、"belongs to"）作为**边**，类型映射自 SNOMED CT 的正式关系概念（如 `Causative agent`、`Indicated for`）
- 支持**多跳推理**和术语一致性
- 从临床文本抽取并标准化实体-关系对，生成结构化JSON数据
- 用这些数据**微调LLM**，显著提升输出的临床逻辑一致性

**关键**：这里 KG 的角色是"提供结构化诊断路径来约束/微调 LLM"，不是直接用 SPARQL 查"contradicts"边。

### 3.3 三种 KG 使用方式的对比

| 方式 | 机制 | 适用场景 | 复杂度 |
|------|------|----------|--------|
| 直接查询（SPARQL/Cypher） | 查询预定义的互斥关系 | 已知冲突模式有限时 | 低 |
| 图神经网络（GNN/KGE） | 学习实体嵌入，预测关系 | 大规模隐式关系发现 | 高 |
| KG增强LLM | 用KG约束/检索增强LLM推理 | 复杂临床推理 | 中 |

**调研结论**：纯 SPARQL 查 "contradicts" 边的做法**不现实**，因为标准 ontology 没有这类边。实际做法是 KG 做规范化 + 关系推理，配合 LLM 或嵌入做矛盾判断。

---

## 四、实体链接在多模态场景怎么做

### 4.1 图片模型输出与文本NER输出的对齐

这是多模态冲突检测的核心难题。调研发现的实际做法：

**方法一：共享嵌入空间对齐（主流深度学习方法）**
- 图片通过 CNN/ViT 编码为视觉特征向量
- 文本通过 BERT/MLLM 编码为文本特征向量
- 在共享空间计算相似度（对比学习，如 CLIP 范式）
- **FAMDR、C2M-DoT 都用这个思路**

**方法二：MLLM 直接推理（新兴方法）**
- 把图片和文本都交给多模态大模型（如 GPT-4V、LLaVA-Med）
- 模型直接判断两者是否一致
- **VDC 用这个思路**

**方法三：多模态知识图谱（MEDMKG）**
- MEDMKG (arXiv 2505.17214) 构建医学多模态KG，统一视觉和文本医学信息
- 通过多阶段pipeline把影像数据与临床概念链接起来
- 图片中的疾病区域和文本中的疾病概念链接到同一个KG节点

### 4.2 医学多模态实体链接

- **Medical multimodal entity linking under modality missingness**：研究在模态缺失（隐私限制、采集失败）情况下的医学多模态实体链接
- **HMEA**：层次化医学KG实体对齐模型，把医学KG表示为层次异构图
- 核心挑战：图片模型输出的是"disease probability"，文本NER输出的是"disease mention"，两者需要通过**实体链接到统一的概念空间**才能比较

---

## 五、现有的开源多模态冲突检测框架

### 5.1 VDC (Versatile Data Cleanser) —— 最接近的开源框架

**论文**：VDC: Versatile Data Cleanser based on Visual-Linguistic Inconsistency by Multimodal Large Language Models (ICLR 2024)
**代码**：https://github.com/zihao-ai/vdc
**论文链接**：https://arxiv.org/abs/2309.16211

**VDC 是目前最现成的开源多模态冲突检测框架**，其pipeline为三个连续模块：

1. **Visual Question Generation (VQG)**：基于标签，用LLM（ChatGPT）生成两类问题：
   - 通用问题（粗粒度，如"请简述图片内容"）
   - 标签特定问题（细粒度，如"图片中的物体是否设计用于空中飞行？"）
   
2. **Visual Question Answering (VQA)**：用MLLM（InstructBLIP）回答生成的问题，获取图像语义

3. **Visual Answer Evaluation (VAE)**：评估回答与预期答案的匹配度
   - 标签特定问题：字符串匹配（yes/no）
   - 通用问题：用ChatGPT作为评估器
   - **投票集成**：正确回答的比例作为匹配分数，低于阈值(α=0.5)则判定为脏样本

**VDC 的局限**：
- 不是医学专用（在CIFAR-10/ImageNet上验证）
- 检测的是"图片-标签"不一致，不是"图片-报告段落"不一致
- 但**架构可直接迁移到医疗场景**：把标签换成报告，VQG针对报告内容生成问题

### 5.2 其他相关资源

| 资源 | 类型 | 适用性 |
|------|------|--------|
| FAMDR | 论文（未开源） | 医疗专用，但代码未公开 |
| RADAR benchmark | 数据集+benchmark | 可作为评估基准 |
| MEDMKG | 多模态医学KG | 可作为知识层 |
| scispaCy | 医学NER工具 | 可作为文本抽取层 |
| SNOMED CT + Neo4j | 知识图谱 | 可作为规范化层 |

**结论**：没有开箱即用的医疗多模态冲突检测框架，但 VDC 的架构可以作为基础，配合医学NER和KG进行领域适配。

---

## 六、核心问题回答

### Q1：真实系统是用 NER+规则？还是深度学习模型？还是 LLM？

**答：真实系统正在从深度学习模型向 LLM/MLLM 迁移。**
- **不是 NER+规则**：FAMDR、VDC、C2M-DoT、ICON 都不用 NER+规则
- **深度学习（特征对齐/对比学习）**：FAMDR、C2M-DoT 代表当前医疗专用SOTA
- **LLM/MLLM 推理**：VDC 代表通用框架趋势，RADAR benchmark 显示评估也在向MLLM对齐
- NER 仅作为**前置信息抽取**步骤存在，不是冲突判断的核心

### Q2：实体矛盾判断是手写的还是学习的？

**答：主流是学习的（嵌入/模型推理），手写规则仅用于简单已知冲突模式。**
- 手写规则：只能处理预定义的互斥对（如"正常"vs"肺炎"），无法泛化
- 嵌入相似度：医学BERT编码后比较，可泛化但缺乏可解释性
- LLM推理：当前最灵活，可处理复杂临床逻辑，FAMDR和VDC都倾向此方向
- **趋势：嵌入 + LLM 混合**，KG提供规范化支撑

### Q3：知识图谱在其中扮演什么角色？

**答：KG 扮演"规范化 + 关系推理 + 知识约束"角色，不是直接查"contradicts"边。**
- 标准ontology（SNOMED CT、ICD-10）**没有显式矛盾边**
- KG用于：实体规范化（解决同义词）、多跳关系推理（"caused by"→"treats"链）、LLM知识增强
- KG不直接判断矛盾，而是为矛盾判断提供**结构化背景知识**

### Q4：对我们的项目，最务实的方案是什么？

基于调研，推荐**分层架构，以 LLM/MLLM 为核心**：

```
┌─────────────────────────────────────────────────┐
│  Layer 1: 信息抽取（轻量）                       │
│  - 文本：scispaCy 医学NER 提取疾病/症状/部位实体  │
│  - 图像：预训练疾病分类器输出 disease probability │
├─────────────────────────────────────────────────┤
│  Layer 2: 规范化（KG辅助，可选）                  │
│  - 实体链接到 SNOMED CT / UMLS 统一概念空间       │
│  - 解决同义词问题（"心影增大"=cardiomegaly）       │
├─────────────────────────────────────────────────┤
│  Layer 3: 冲突检测（核心，MLLM驱动）              │
│  - 借鉴 VDC pipeline：针对报告内容生成问题 →       │
│    MLLM看图回答 → 评估一致性                      │
│  - 或借鉴 FAMDR：特征对齐 + 不确定性量化          │
├─────────────────────────────────────────────────┤
│  Layer 4: 置信度与输出                            │
│  - 投票集成 / 不确定性量化                        │
│  - 输出：冲突位置 + 冲突类型 + 置信度              │
└─────────────────────────────────────────────────┘
```

**务实建议**：

1. **不要从零写 NER+规则**：手写冲突规则在医疗领域不可扩展，维护成本高
2. **直接用 MLLM 做核心检测**：参考 VDC 的 VQG→VQA→VAE 三段式，把标签换成报告文本
3. **NER 作为辅助而非核心**：用 scispaCy 做实体提取，主要用于**定位**和**解释**冲突（告诉用户哪里冲突），而非判断冲突
4. **KG 可选，先跳过**：SNOMED CT 集成成本高，如果数据集中疾病词表有限，可用简单字典规范化替代
5. **评估对齐 RADAR benchmark**：如果做chest X-ray，可参考 RADAR 的 agreement detection + severity + edit type 三维评估

**最务实的 MVP**：用 MLLM（如 LLaVA-Med 或 GPT-4V）直接做"图片-报告"一致性判断，用 scispaCy 做实体提取辅助解释，暂不引入KG。验证有效后再逐步加 KG 规范化层。

---

## 参考文献索引

1. **FAMDR** - Liang et al., "FAMDR: Feature-Aligned Multimodal Denoising for Reliable Diagnostic Reconciliation in Medical Imaging", AAAI 2026. https://ojs.aaai.org/index.php/AAAI/article/view/37623
2. **VDC** - Zhu et al., "VDC: Versatile Data Cleanser based on Visual-Linguistic Inconsistency by Multimodal Large Language Models", ICLR 2024. https://arxiv.org/abs/2309.16211 | Code: https://github.com/zihao-ai/vdc
3. **RADAR** - "RADAR: A Multimodal Benchmark for 3D Image-Based Radiology Report Review", arXiv 2603.06681, 2026.
4. **SNOMED KG** - Liu et al., "SNOMED CT-powered Knowledge Graphs for Structured Clinical Data and Diagnostic Reasoning", arXiv 2510.16899, 2025.
5. **MEDMKG** - "MEDMKG: Benchmarking Medical Knowledge Exploitation with Multimodal Knowledge Graph", arXiv 2505.17214, 2025.
6. **ICON** - "ICON: Improving Inter-Report Consistency in Radiology Report Generation", EMNLP 2024 Findings.
7. **C2M-DoT** - "C2M-DoT: Cross-modal consistent multi-view medical report generation", 2026.
8. **HMEA** - "HMEA: A hierarchical medical knowledge graph entity alignment model", Artificial Intelligence in Medicine, 2025.
9. **Medical KG Review** - "A Review on Knowledge Graphs for Healthcare", arXiv 2306.04802.
10. **Medical Multimodal Entity Linking** - "Medical multimodal entity linking under modality missingness", AIH.
