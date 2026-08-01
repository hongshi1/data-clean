# 业内先进不一致检测方法调研与数据集策略分析

> 调研日期: 2026-07-29
> 数据来源: arXiv (2024-2026) + 本项目 `data/gjb_438c/` 实际数据

---

## Part 1: 最新方法调研 (arXiv 2024-2026)

### 1.1 检索概览

对 arXiv 执行 5 组关键词检索, 覆盖: 文档多模态一致性、图文矛盾检测、需求冲突检测(LLM)、表文一致性验证、视觉蕴含(文档图表)。命中 51 篇, 筛选出与 SRS 一致性检测高度相关的 **10 篇** 核心论文, 归纳为 4 个技术方向。

### 1.2 需求冲突检测 (直接相关)

#### P1. NLI for Requirements Engineering
- **论文**: Lessons from the Use of Natural Language Inference (NLI) in Requirements Engineering Tasks
- **arXiv**: 2405.05135 (2024-05, cs.SE/cs.CL/cs.LG)
- **方法**: 将自然语言推理 (NLI) 的蕴含/中立/矛盾三分类框架引入需求工程, 覆盖三个任务: 需求分类、规约缺陷识别、**需求冲突检测**。将需求对构造为 NLI premise-hypothesis 对, 用 NLI 模型判定矛盾关系。
- **数据集**: 公开需求基准数据集 (论文未具名, 但与 PURE、CCHIT 等同类)
- **指标**: Accuracy / F1 (冲突检测子任务)
- **关键结论**: NLI 方法在需求规约分析中**全面超越** classical NLP、LLM chatbot (GPT系列) 和概率模型; 在零样本设定下仍具竞争力。
- **与 SRS 的关联**: ★★★★★ 直接对应我们的"语义层一致性检测"。NLI 的三分类(蕴含/中立/矛盾)可直接映射到 SRS 约束对的同值/无关/冲突判定。我们的 `srs_consistency_checker_v2.py` 当前用 LLM 做 zero-shot 判定, 可引入 NLI 模型做轻量级预筛。

#### P2. PassionNet
- **论文**: PassionNet: An Innovative Framework for Duplicate and Conflicting Requirements Identification
- **arXiv**: 2412.01657 (2024-12, cs.SE/cs.AI)
- **方法**: 三类预测管线: (1) 纯 LLM (8种); (2) 多模型相似度知识驱动 (传统相似度 + LLM 向量相似度); (3) **混合管线** (LLM 上下文 + 多模型相似度)。在 6 个公开基准上测试 760 种管线组合。
- **数据集**: 6 个公开基准需求冲突/重复数据集
- **指标**: F1-score
- **关键结论**: 混合管线 (LLM 上下文 + 相似度知识) **一致最优**, 比现有 SOTA 高 **13% F1**。
- **与 SRS 的关联**: ★★★★★ 验证了我们的架构方向——"约束提取(相似度) + LLM 上下文判定"的混合管线优于纯 LLM。我们的三层检测(语法→语义→逻辑)正是混合策略的分层版本。论文的 6 个基准数据集可作为我们扩充 Gold Standard 的参照。

#### P3. GPT-4 Regulatory Compliance
- **论文**: NLP-based Regulatory Compliance -- Using GPT 4.0 to Decode Regulatory Documents
- **arXiv**: 2412.20602 (2024-12, cs.CL)
- **方法**: 用 GPT-4.0 检测法规文档中的不一致与矛盾。与领域专家合作, 在精选语料中**人工注入歧义和矛盾**, 用 P/R/F1 评测。
- **数据集**: 策展语料 + **人工注入矛盾** (建筑师/合规工程师协作设计)
- **指标**: Precision / Recall / F1
- **关键结论**: GPT-4.0 有效检测法规不一致; 人工注入矛盾是可行的数据集构建策略; 需更大规模数据和领域微调。
- **与 SRS 的关联**: ★★★★☆ 与我们场景高度吻合——法规文档 ≈ GJB 标准 SRS。**人工注入矛盾**的策略直接适用于我们扩充 Gold Standard (当前仅 8 个真矛盾)。论文验证了"注入矛盾 → P/R/F1 评测"的范式。

### 1.3 文档多模态一致性 (核心方向)

#### P4. C&P Knowledge Conflicts (EMNLP 2025)
- **论文**: Is Cognition Consistent with Perception? Assessing and Mitigating Multimodal Knowledge Conflicts in Document Understanding
- **arXiv**: 2411.07722 (2024-11, cs.AI, EMNLP 2025)
- **方法**: 定义**认知-感知 (C&P) 知识冲突**——MLLM 在文档 VQA (认知) 中生成的答案与其自身 OCR (感知) 识别的视觉内容不匹配。系统评估 C&P 冲突, 提出 Multimodal Knowledge Consistency Fine-tuning 缓解。
- **数据集**: 文档理解基准 (DocVQA 等)
- **指标**: C&P 一致性准确率
- **关键结论**: 即使 **GPT-4o 也仅 75.26%** 的 C&P 一致性; 微调可降低冲突。
- **与 SRS 的关联**: ★★★★☆ 这是多模态冲突检测的理论基础。SRS 中的图文一致性正是 C&P 冲突: 文字描述(认知)与图片内容(感知)是否匹配。75.26% 的 baseline 说明当前 MLLM 在文档场景远非完美, 我们的图文一致性检测有明确价值。

#### P5. VisDoM (consistency-constrained fusion)
- **论文**: VisDoM: Multi-Document QA with Visually Rich Elements Using Multimodal RAG
- **arXiv**: 2412.10704 (2024-12, cs.CL)
- **方法**: 多文档 QA, 提出 **consistency-constrained modality fusion** 机制, 在推理时对齐文本和视觉 RAG 管线的推理过程, 确保跨模态一致性。含 VisDoMBench (首个多文档多模态 QA 基准, 含表格/图表/幻灯片)。
- **数据集**: VisDoMBench (多文档, 含 tables/charts/slides)
- **指标**: QA 准确率 (比单模态/长上下文 LLM 高 12-20%)
- **与 SRS 的关联**: ★★★☆☆ "consistency-constrained fusion" 思想可借鉴——在跨章节/跨模态推理时, 强制对齐不同信息源的一致性。多文档场景映射到我们的"跨文档冲突"(如 Gold Standard GT-008)。

#### P6. MatViX
- **论文**: MatViX: Multimodal Information Extraction from Visually Rich Articles
- **arXiv**: 2410.20494 (2024-10, cs.CL)
- **方法**: 多模态信息抽取 (MIE) 基准, 从全文文档的文本/表格/图片中提取结构化 JSON。324 篇论文 + 1688 个复杂 JSON。评估曲线相似度和层次结构对齐。基准 VLM 零样本能力, 用 DePlot 改善曲线提取。
- **数据集**: 324 篇全文论文, 1688 个专家标注 JSON
- **指标**: 曲线相似度 / 层次结构对齐
- **与 SRS 的关联**: ★★★☆☆ SRS 表格中的参数曲线/性能图与文字描述的一致性检测可参考其评估方法。DePlot 等专用模型可辅助图表信息提取。

### 1.4 表文一致性验证

#### P7. HIPPO (hybrid-modal table)
- **论文**: HIPPO: Enhancing the Table Understanding Capability of LLMs through Hybrid-Modal Preference Optimization
- **arXiv**: 2502.17315 (2025-02, cs.CL)
- **方法**: 用**文本+图像双模态**表示表格, 通过 DPO (Direct Preference Optimization) 训练 MLLM, 设计 modality-consistent sampling 增强多样性、减少模态偏差。在表格 QA 和**表格事实验证**任务上评测。
- **数据集**: TabFact / FEVEROUS 等表格事实验证基准
- **指标**: 表格推理准确率 (+4%)
- **与 SRS 的关联**: ★★★★☆ 直接对应"文本-表格一致性检测"。SRS 中表格常以 HTML/图片两种形式存在, 双模态表示可提升一致性检测鲁棒性。

#### P8. SCITAB (EMNLP 2023)
- **论文**: SCITAB: A Challenging Benchmark for Compositional Reasoning and Claim Verification on Scientific Tables
- **arXiv**: 2305.13186 (2023-05, EMNLP 2023)
- **方法**: 1.2K 专家验证的科学声明, 每条声明配科学表格作为证据, 标注 supports/refutes/not enough info。要求组合推理。除 GPT-4 外所有模型接近随机猜测。
- **数据集**: 1.2K 科学声明 + 科学表格
- **指标**: Label accuracy / F1
- **与 SRS 的关联**: ★★★★☆ SRS 表格参数与文字描述的矛盾正是"声明 vs 表格"的验证问题。SCITAB 的数据格式 (claim, table, label) 可直接作为我们 Gold Standard 中 `text_table_conflict` 类型的模板。

#### P9. FEVEROUS (NeurIPS 2021)
- **论文**: FEVEROUS: Fact Extraction and VERification Over Unstructured and Structured information
- **arXiv**: 2106.05707 (2021-06, NeurIPS 2021 D&B)
- **方法**: 87,026 条已验证声明, 每条标注文本句子和/或表格单元格作为证据, 标签 supports/refutes/NEI。同时验证非结构化(文本)和结构化(表格)信息。
- **数据集**: 87K 声明 (Wikipedia)
- **指标**: Label accuracy + evidence F1
- **与 SRS 的关联**: ★★★☆☆ 大规模文本+表格事实验证的标杆。其证据标注方式 (sentence/cell 级) 启发我们 Gold Standard 应记录矛盾证据的精确位置 (section_id + table_id + cell)。

#### P10. sciwrite-lint
- **论文**: sciwrite-lint: Verification Infrastructure for the Age of Science Vibe-Writing
- **arXiv**: 2604.08501 (2026-04, cs.DL/cs.CL/cs.SE)
- **方法**: 将软件工程的 linting 范式应用于学术论文验证: 引用存在性、元数据准确性、撤稿状态、声明支持度。扩展到**内部一致性**: 文中数字 vs 表格、摘要 vs 正文、**图题 vs 内容**、统计结果 vs 文字解读、结构交叉引用(悬空引用/orphan references)。
- **数据集**: 30 篇未见论文 + 错误注入
- **指标**: Per-reference 可靠性评分 / 误报率
- **与 SRS 的关联**: ★★★★☆ "linting" 范式与我们 GJB 规则合规扫描 (`srs_gjb_compliance_scan.py`) 思路一致。其内部一致性检查项 (text vs table, caption vs content, dangling references) 几乎一一对应我们的语法/语义层检测。

### 1.5 方法调研汇总表

| # | 论文 | 方向 | 核心方法 | 数据规模 | 与 SRS 关联度 |
|---|------|------|----------|----------|--------------|
| P1 | NLI for RE (2405.05135) | 需求冲突 | NLI 三分类 | 公开基准 | ★★★★★ |
| P2 | PassionNet (2412.01657) | 需求冲突 | LLM+相似度混合管线 | 6 基准/760管线 | ★★★★★ |
| P3 | GPT-4 Regulatory (2412.20602) | 法规矛盾 | GPT-4 + 注入矛盾 | 人工注入语料 | ★★★★☆ |
| P4 | C&P Conflicts (2411.07722) | 多模态冲突 | C&P 一致性评估 | DocVQA | ★★★★☆ |
| P5 | VisDoM (2412.10704) | 多模态 QA | 一致性约束融合 | VisDoMBench | ★★★☆☆ |
| P6 | MatViX (2410.20494) | 多模态 IE | VLM 零样本+DePlot | 324 篇 | ★★★☆☆ |
| P7 | HIPPO (2502.17315) | 表文验证 | 双模态 DPO | TabFact/FEVEROUS | ★★★★☆ |
| P8 | SCITAB (2305.13186) | 表文验证 | 组合推理验证 | 1.2K 声明 | ★★★★☆ |
| P9 | FEVEROUS (2106.05707) | 表文验证 | 文本+表格验证 | 87K 声明 | ★★★☆☆ |
| P10 | sciwrite-lint (2604.08501) | 内部一致性 | Linting 范式 | 30 篇+注入 | ★★★★☆ |

### 1.6 关键启示

1. **NLI 是需求冲突检测的有效范式** (P1): 三分类(蕴含/中立/矛盾)天然适配约束对判定, 可作为轻量级预筛器降低 LLM 调用成本。

2. **混合管线优于纯 LLM** (P2): "相似度预筛 + LLM 上下文判定"的混合策略比纯 LLM 高 13% F1——我们三层检测的分层设计方向正确。

3. **人工注入矛盾是可行的数据集构建策略** (P3, P10): 多篇论文采用此策略扩充评测集, 验证了我们在 Gold Standard 中"植入矛盾"的可行性。

4. **多模态一致性远未解决** (P4): GPT-4o 仅 75.26% C&P 一致性, 图文一致性检测有显著研究空间。

5. **表格事实验证需要组合推理** (P8): SRS 表格参数验证不是简单的值匹配, 而是需要跨单元格、跨行的组合推理。

---

## Part 2: 本项目数据集分析

### 2.1 数据集现状

数据来源: `data/gjb_438c/processed_documents/_summary.json`

| 维度 | 数值 | 说明 |
|------|------|------|
| 总文档数 | 346 | 去重后 (去重前 371, 移除 25 个重复) |
| GJB 格式文档 | 22 | 含 battery/compiler/scheduler 等 |
| 通用文档 | 324 | 来自 9+ 来源 (buaa/gjb438b/ieee830/nasa/radar 等) |
| 总章节 | 15,653 | 结构化提取的章节数 |
| LLM 提取约束 | 948 | 7 种约束类型 |
| 规则提取约束 | 224 | GJB 规则扫描所得 |
| 总表格 | 3,155 | 结构化 HTML 表格 |
| 总图片 | 1,584 | 含 caption/context 的图文对 |
| 有 caption 图片 | 832 (53%) | |
| 有 context 图片 | 1,259 (80%) | |

**来源分布**: gjb_demo (3) + collection_mineru (113) + collection_raw (230)

**系统类型分布**: unknown(172) / web(101) / aerospace(32) / communication(25) / compiler(5) / education(4) / embedded(4) / defense(3)

**语言分布**: 中文 83 / 英文 263

### 2.2 Gold Standard 现状

数据来源: `data/gjb_438c/gold_standard/_summary.json`

| 文档 | 系统类型 | 约束数 | GT 总数 | 真矛盾 | 正值 |
|------|----------|--------|---------|--------|------|
| scheduler_srs | 嵌入式实时调度器 | 65 | 7 | 1 | 6 |
| compiler_srs | 桌面编译器工具 | 30 | 7 | 5 | 2 |
| battery_srs | 嵌入式电池仿真模型 | 102 | 8 | 2 | 6 |
| **合计** | | **197** | **22** | **8** | **14** |

**冲突率**: 36.4% (8/22)

**按严重度**: HIGH(6) / MEDIUM(2) / LOW(1) / INFO(13, 即正值)

**按冲突类型**:
| 类型 | 数量 | 说明 |
|------|------|------|
| same_param_same_value | 10 | 同参数同值 (正值为主) |
| text_table_conflict | 3 | 文本-表格冲突 |
| logic_satisfiable | 3 | 逻辑可满足 (正值) |
| logic_contradiction | 2 | 逻辑矛盾 |
| logic_incomplete | 1 | 逻辑不完整 |
| logic_unsatisfiable | 1 | 逻辑不可满足 |
| same_value_diff_semantics | 1 | 同值不同语义 |
| cross_document_conflict | 1 | 跨文档冲突 |

### 2.3 数据集规模评估

**与业内基准对比**:

| 基准 | 规模 | 类型 |
|------|------|------|
| FEVEROUS (P9) | 87K 声明 | 文本+表格验证 |
| SCITAB (P8) | 1.2K 声明 | 科学表格验证 |
| MatViX (P6) | 324 篇 / 1688 JSON | 多模态 IE |
| PassionNet (P2) | 6 基准 / 760 管线 | 需求冲突 |
| **本项目** | **346 文档 / 948 约束 / 22 GT** | SRS 一致性 |

**评估**: 文档规模(346)与 MatViX(324)相当, 但 Gold Standard (22 GT) 远小于 SCITAB(1.2K)。约束级数据(948)具备一定规模, 但标注的 GT 仅 22 条, 评测统计功效不足。

### 2.4 数据集 Split 策略建议

当前 22 GT 集中在 3 份文档, 无法做传统 train/dev/test split。建议:

**策略 A: 文档级 Split (推荐, 适用于扩充后)**
```
Train (70%): ~240 文档 — 用于约束提取器调优、规则库构建
Dev   (15%): ~50 文档  — 用于检测器阈值调优、假阳性优化
Test  (15%): ~56 文档  — 用于最终评测 (含 Gold Standard)
```
- Gold Standard 的 3 份文档固定在 Test 集
- 按 system_type 分层抽样, 确保各类型有代表

**策略 B: 约束对级 Split (当前可用)**
```
22 GT → 5-fold cross-validation
每折 ~4-5 GT, 确保每折含至少 1 个真矛盾
```
- 适用于当前小规模评测
- 报告 5 折平均 P/R/F1 ± std

**策略 C: 混合策略 (最优)**
- 文档级 split 防止信息泄露
- 在 Train 集上用"注入矛盾"生成合成 GT (参考 P3 方法)
- Test 集仅含人工标注的真实 GT

### 2.5 数据集扩充策略

基于调研, 提出三条扩充路径:

#### 路径 1: 合成 SRS + 植入矛盾 (参考 P3, P10)
- **方法**: 以现有 22 份 GJB SRS 为模板, 用 LLM 生成结构相似的合成 SRS, 人工/半自动植入已知类型的矛盾
- **植入矛盾类型** (覆盖 Gold Standard 现有 8 种):
  - 同参数不同值 (same_param_diff_value)
  - 逻辑矛盾 (logic_contradiction)
  - 文本-表格冲突 (text_table_conflict)
  - 跨文档冲突 (cross_document_conflict)
  - 引用断裂 (reference_broken) — 新增
- **目标**: 每份合成 SRS 植入 3-5 个矛盾, 生成 50 份 → 150-250 个合成 GT
- **优势**: 可控、可大规模生成、覆盖所有冲突类型
- **风险**: 合成数据可能与真实分布有偏差, 需在 Test 集保留真实 GT

#### 路径 2: 更多公开 SRS (扩充文档池)
- **来源**: 
  - NASA SRS 数据集 (已有部分, 可扩充)
  - IEEE 830 示例 (已有)
  - OpenCoss SRS benchmark
  -requirements-gathering-public (GitHub)
  - Promised/Landauer 需求冲突数据集 (PassionNet P2 使用的 6 个基准)
- **目标**: 扩充到 500+ 文档, 丰富 system_type 覆盖
- **处理**: MinerU 解析 → 统一处理器 → 约束提取

#### 路径 3: 人工标注真实 GT (提升质量)
- 从 346 文档中筛选 20-30 份高质量 GJB 格式 SRS
- 领域专家标注真实不一致 (参考 SCITAB 的专家标注流程)
- 每份文档标注 5-10 个 GT (含矛盾+正值)
- **目标**: 真实 GT 从 22 扩充到 150-200

**建议优先级**: 路径 1 (合成注入) > 路径 3 (人工标注) > 路径 2 (扩充文档池)

---

## Part 3: 多模态冲突检测可行性分析

### 3.1 图文数据现状

数据来源:
- `image_text_matches/_summary.json` (94 文档, 已匹配)
- `processed_documents/_summary.json` (346 文档, 全量)

| 维度 | 已匹配集 (94 文档) | 全量集 (346 文档) |
|------|-------------------|-------------------|
| 总图片 | 467 | 1,584 |
| 有 caption | 455 (97%) | 832 (53%) |
| 有 context | 462 (99%) | 1,259 (80%) |
| 有图号 | 218 (47%) | — |

**关键发现**:
- 已匹配集 caption 率 97%, context 率 99% — 匹配器效果良好
- 全量集 caption 率仅 53% — 约 750 张图片无 caption (orphaned)
- GJB 格式 SRS (22 份) 的图片多数无规范 caption — 这是 GJB 文档的常见问题

**图片类型分布** (已匹配集):
figure(多数) / flowchart / state_diagram / interface_diagram / architecture_diagram / data_diagram / context_diagram / unnamed

### 3.2 GJB SRS 图片的 Orphaned 问题

**问题**: 24 份 GJB SRS 有图片但 caption 缺失或不规范, 导致无法直接做图文一致性。

**根因**:
1. GJB 438C 对图题的要求是"图N 标题", 但实际文档常省略图题或格式不规范
2. MinerU OCR 对图题的提取依赖版面分析, 图题与图片的关联可能断裂
3. 部分图片为扫描件中的截图, 无结构化图题

**解决方案 (分级)**:

| 级别 | 方法 | 适用场景 | 准确率预期 |
|------|------|----------|-----------|
| L1 | 上下文恢复 | 图前/后段落含"如图N所示" | 高 (90%+) |
| L2 | 图号提取 | 图片上方/下方有"图N"文字 | 中高 (80%+) |
| L3 | VLM 描述生成 | 无任何图题, 用 Kimi-K2.6 生成描述 | 中 (70%+) |
| L4 | 跨文档推理 | 同类系统 SRS 交叉参照 | 低 (50%+) |

### 3.3 VLM 图文一致性检测流程设计

基于 C&P 冲突框架 (P4) 和项目已有基础设施, 设计如下流程:

```
输入: SRS 文档 (含图片 + 文字)
  │
  ├─ Step 1: 图文对构建 (已完成, srs_image_text_matcher.py)
  │   ├─ 提取图片 + caption + context
  │   └─ 对 orphaned 图片执行 L1-L3 caption 恢复
  │
  ├─ Step 2: VLM 图像理解 (Kimi-K2.6)
  │   ├─ 输入: 图片 + "请描述这张图的内容、关键参数、数据流"
  │   ├─ 输出: 结构化图片描述 (JSON)
  │   └   └─ {type, entities, parameters, relationships, data_flow}
  │
  ├─ Step 3: 文字-图片一致性判定 (LLM)
  │   ├─ 输入: caption + context (文字侧) + VLM 描述 (图片侧)
  │   ├   └─ + 约束知识库 (同参数/同实体)
  │   ├─ Prompt: "判断文字描述与图片内容是否一致, 输出 {consistent, conflict_type, evidence}"
  │   └─ 输出: 一致性判定 + 冲突类型 + 证据
  │
  ├─ Step 4: 多模态冲突分类
  │   ├─ 语法层: 引用断裂 (图N 不存在)
  │   ├─ 语义层: 图中参数与文字描述不符
  │   └─ 逻辑层: 图中数据流与文字逻辑矛盾
  │
  └─ Step 5: 评测对齐 Gold Standard
      └─ P/R/F1 (多模态冲突子任务)
```

### 3.4 数据准备清单

| 数据项 | 当前状态 | 需要准备 |
|--------|----------|----------|
| 图片文件 | ✅ 已提取 (1584 张) | — |
| Caption | ✅ 53% 已有 | 对 752 张 orphaned 执行恢复 |
| Context | ✅ 80% 已有 | 补充 325 张缺 context 的 |
| VLM 描述 | ❌ 未生成 | 对 1584 张图片调用 Kimi-K2.6 生成描述 |
| 图文对标注 | ❌ 无 | 人工标注 50-100 对图文一致性 GT |
| 图文矛盾对 | ❌ 无 | 合成 30-50 对图文矛盾 (参考 3.6) |

### 3.5 多模态冲突评测集构建

**方案: 合成图文矛盾对**

参考 P3 (人工注入矛盾) 和 P4 (C&P 冲突), 构建:

1. **正对 (consistent)**: 从已匹配的 467 图文对中, 人工确认 100 对一致的图文对
2. **矛盾对 (conflict)**: 对 50 对图文对, 人工修改文字描述使其与图片内容矛盾:
   - 修改参数值 (图中显示 5V, 文字改为 12V)
   - 修改数据流方向 (图中 A→B, 文字改为 B→A)
   - 修改实体名称 (图中"传感器A", 文字改为"传感器B")
   - 增删图中不存在的元素
3. **格式**: `{image_path, text_description, label, conflict_type, evidence}`

**规模**: 150 对 (100 正 + 50 负), 与 SCITAB (1.2K) 相比小, 但作为初始评测集可行。

---

## Part 4: 语法层面多模态冲突分析

### 4.1 定义

"语法层面的多模态冲突"指文档中**跨模态引用的结构性/格式性不一致**, 不涉及深层语义, 可通过规则或模式匹配检测。区别于:
- 语义层: 内容含义矛盾 (参数值不同)
- 逻辑层: 逻辑约束不可满足 (A>B 且 B>A)

### 4.2 冲突类型详析

#### 4.2.1 图片编号引用断裂
- **定义**: 正文出现"如图N所示"/"见图N", 但文档中找不到对应编号的图片
- **检测方法**: 
  1. 正则提取正文中所有 `图\s*\d+` 引用
  2. 提取所有图片的图号 (caption 中的"图N")
  3. 集合差集 = 断裂引用
- **GJB 要求**: GJB 438C 规定所有图片均需编号并在正文中引用
- **当前工具**: `srs_gjb_compliance_scan.py` 可扩展
- **难度**: ★☆☆☆☆ (纯规则)

#### 4.2.2 表格引用断裂
- **定义**: 正文出现"见表N"/"如表N所示", 但文档中找不到对应编号的表格
- **检测方法**: 同 4.2.1, 替换为 `表\s*\d+`
- **GJB 要求**: GJB 438C 规定所有表格均需编号并在正文中引用
- **难度**: ★☆☆☆☆ (纯规则)

#### 4.2.3 图片格式不符合 GJB 要求
- **定义**: 图片缺少图题/编号不规范/位置错误
- **子类型**:
  - 缺图题: 图片无"图N XXXX"格式的标题
  - 编号不连续: 图1, 图2, 图4 (缺图3)
  - 编号重复: 两个"图3"
  - 图题位置错误: GJB 要求图题在图下方
- **检测方法**: 
  1. 检查每张图片是否有匹配的 caption
  2. 检查图号是否连续且唯一
  3. 检查 caption 相对图片的位置
- **GJB 规则**: `knowledge/gjb_438c_rules.json` 中的图题规则
- **难度**: ★★☆☆☆ (规则 + 版面分析)

#### 4.2.4 表格格式不符合 GJB 要求
- **定义**: 表格缺表题/编号不规范/格式错误
- **子类型**:
  - 缺表题: 表格无"表N XXXX"格式的标题
  - 编号不连续/重复
  - 表题位置错误: GJB 要求表题在表上方
  - 表格跨页未续表题
- **检测方法**: 同 4.2.3, 针对表格
- **难度**: ★★☆☆☆ (规则 + 版面分析)

#### 4.2.5 图文交叉引用格式错误
- **定义**: 引用格式不符合 GJB 规范
- **子类型**:
  - 使用"下图"而非"图N" (GJB 要求用编号引用)
  - 使用"上图"而非"图N"
  - 引用编号格式不统一 (图1 vs 图一 vs Figure 1)
- **检测方法**: 正则匹配 + 规则校验
- **难度**: ★☆☆☆☆ (纯规则)

#### 4.2.6 公式/符号引用断裂
- **定义**: 正文引用"式(N)"但找不到对应公式
- **检测方法**: 同 4.2.1, 针对公式
- **难度**: ★★☆☆☆ (需公式提取)

### 4.3 检测优先级与实现路径

| 优先级 | 冲突类型 | 实现方式 | 预计 GT 数 | 检测精度 |
|--------|----------|----------|-----------|----------|
| P0 | 图片引用断裂 (4.2.1) | 正则 + 集合差 | 10-20 | ~100% |
| P0 | 表格引用断裂 (4.2.2) | 正则 + 集合差 | 10-20 | ~100% |
| P1 | 图片格式不合规 (4.2.3) | 规则 + 版面 | 15-30 | ~95% |
| P1 | 表格格式不合规 (4.2.4) | 规则 + 版面 | 15-30 | ~95% |
| P2 | 引用格式错误 (4.2.5) | 正则 + 规则 | 5-10 | ~90% |
| P3 | 公式引用断裂 (4.2.6) | 正则 + 公式提取 | 5-10 | ~90% |

### 4.4 与三层检测框架的整合

```
语法层 (Syntax)
├─ 纯文本语法: 拼写/标点/术语一致性 (现有)
├─ 结构引用: 图/表/公式引用断裂 (4.2.1, 4.2.2, 4.2.6) ← 新增
└─ 格式合规: 图题/表题/编号规范 (4.2.3, 4.2.4, 4.2.5) ← 新增

语义层 (Semantic)
├─ 同值检测: 同参数同值/不同值 (现有)
├─ 文本-表格: 参数值文字 vs 表格 (现有)
└─ 文本-图片: 文字描述 vs 图片内容 (Part 3, VLM) ← 新增

逻辑层 (Logic)
├─ 约束可满足性: Z3 求解 (现有)
├─ 逻辑矛盾: A>B 且 B>A (现有)
└─ 跨文档冲突: 多文档参数矛盾 (现有)
```

**语法层多模态冲突**的定位: 语法层的"多模态"体现为**跨模态引用的结构完整性**, 而非内容语义。这是最低成本、最高精度的检测层, 应作为检测引擎的第一道过滤。

### 4.5 实现建议

1. **立即可做** (P0): 扩展 `srs_gjb_compliance_scan.py`, 增加 图/表引用断裂检测。输入: 正则提取引用 + 图表编号列表; 输出: 断裂引用报告。预计 1-2 小时开发。

2. **短期** (P1): 利用 MinerU 版面分析结果, 检查图题/表题的存在性和位置。需访问 `mineru_parsed/` 中的 layout 信息。

3. **中期** (P2-P3): 整合到统一处理管线 `srs_unified_processor.py`, 作为语法层的标准检测项, 输出到 consistency_reports。

---

## 总结与行动项

### 核心发现

1. **NLI + 混合管线** 是需求冲突检测的主流方向 (P1, P2), 我们的三层混合架构方向正确
2. **多模态一致性** 远未解决 (GPT-4o 仅 75%), VLM 辅助检测有明确价值 (P4)
3. **人工注入矛盾** 是业内通用的评测集构建策略 (P3, P10), 可解决 Gold Standard 不足问题
4. **表格事实验证** 需组合推理 (P8), 我们的 `text_table_conflict` 检测需增强
5. **语法层多模态冲突** (引用断裂/格式不合规) 是低成本高回报的检测项, 应优先实现

### 建议行动项 (按优先级)

| 优先级 | 行动项 | 依据 | 预期产出 |
|--------|--------|------|----------|
| P0 | 实现图/表引用断裂检测 | Part 4 | 语法层检测能力 +10-20 GT |
| P0 | 合成 50 份注入矛盾的 SRS | P3, Part 2.5 | Gold Standard 扩充到 150-250 GT |
| P1 | 引入 NLI 模型做约束对预筛 | P1 | 检测效率提升, LLM 调用减少 |
| P1 | 生成 1584 张图片的 VLM 描述 | Part 3.3 | 多模态检测数据基础 |
| P2 | 构建图文矛盾评测集 (150 对) | Part 3.5 | 多模态冲突评测能力 |
| P2 | 表格组合推理增强 | P8 | text_table_conflict 检测精度提升 |
| P3 | 人工标注 20 份真实 SRS 的 GT | Part 2.5 | 真实评测基准 |

---

## 附录: arXiv 论文完整索引

| 编号 | arXiv ID | 标题 | 发表 |
|------|----------|------|------|
| P1 | 2405.05135 | Lessons from the Use of NLI in Requirements Engineering Tasks | 2024 |
| P2 | 2412.01657 | PassionNet: Duplicate and Conflicting Requirements Identification | 2024 |
| P3 | 2412.20602 | NLP-based Regulatory Compliance -- Using GPT 4.0 | 2024 |
| P4 | 2411.07722 | Is Cognition Consistent with Perception? (C&P Conflicts) | EMNLP 2025 |
| P5 | 2412.10704 | VisDoM: Multi-Document QA with Multimodal RAG | 2024 |
| P6 | 2410.20494 | MatViX: Multimodal Information Extraction | 2024 |
| P7 | 2502.17315 | HIPPO: Hybrid-Modal Table Understanding | 2025 |
| P8 | 2305.13186 | SCITAB: Scientific Table Claim Verification | EMNLP 2023 |
| P9 | 2106.05707 | FEVEROUS: Fact Extraction and VERification | NeurIPS 2021 |
| P10 | 2604.08501 | sciwrite-lint: Verification Infrastructure | 2026 |
