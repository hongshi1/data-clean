# Top 5 论文精读报告

> 日期: 2026-07-24
> 5篇论文并行精读，每篇提取了方法架构、数据集、结果、可复用性

---

## 1. Okamoto & Kusumoto (2025) — LLM for SRS Standardization

| 项目 | 内容 |
|---|---|
| **会议** | IEEE SANER 2025 (扩展版投Requirements Engineering期刊) |
| **任务** | 用LLM将SRS重构为符合ISO/IEC/IEEE 29148标准的格式 |
| **方法** | 两种zero-shot prompt: Pall(整体生成) / Peach(逐章生成) |
| **LLM** | GPT-4o, GPT-5, Gemini-2.5-flash/pro |
| **数据** | PURE数据集7份SRS (纯文本, 无表格图片) |
| **评测** | RQ1: 蕴含式P/R (RoBERTa FV + 贝叶斯校正); RQ2: 人工checklist |
| **结果** | Peach+GPT: 覆盖率>90%, 有效性>90%; Pall精度~90% |
| **代码** | Zenodo (匿名) |

### 可复用性 for GJB 438C
- **可直接复用**: Pall/Peach prompt模式（替换标准结构即可）、评测框架
- **必须修改**: 替换为GJB 438C章节结构、重建checklist、中文NLI/FV模型、处理表格图片
- **核心启示**: 标准是标准无关的(standard-agnostic)，swap结构定义即可适配GJB

---

## 2. ChartVE (ACL 2024) — Chart Visual Entailment

| 项目 | 内容 |
|---|---|
| **arXiv** | 2312.10160 |
| **任务** | 判断图表是否蕴含文字描述 (binary: Entail/NotEntail) |
| **模型** | UniChart-base-960 (~140M参数), Swin Transformer + BART |
| **数据** | CHOCOLATE: 1,187图表-标题对, 5,323句子, 7种错误类型 |
| **方法** | 图表→Swin编码 → "Does the image entail this statement?" → yes/no logits |
| **C2TFEC** | 两阶段纠错: 图表→表格→GPT-4修正 |
| **结果** | Kendall's Tau=0.178 (Lvlm split, 最佳); C2TFEC: 43%→81%正确率(Ft split) |
| **代码** | https://khuangaf.github.io/CHOCOLATE/ |

### 可复用性 for SRS图片
- **不可直接用**: UniChart预训练在数据图表上，不处理架构图/状态图
- **可迁移的框架**: VE判定模式、表格引导的负样本生成、两阶段分解(图→结构→推理)
- **适配路径**: 替换为LLaVA/InternVL → 定义SRS图片错误类型 → 合成训练数据 → 微调

---

## 3. FloCA (2026) — Flowchart Reasoning

| 项目 | 内容 |
|---|---|
| **arXiv** | 2602.14035 |
| **实际任务** | 流程图导向对话(FOD)，**不是**流程图-文字一致性检查 |
| **方法** | LLM + 确定性图推理工具 (NodeAttr/OutEdgeAttr/NextHop/TerminalCheck) |
| **数据** | FLODIAL (1,212流程图) + PFDial (440+80+80, PlantUML) |
| **结果** | PFDial: TNGA 98.3%, PCA 94.3% |
| **代码** | https://github.com/Jinzi-Zou/FloCA-flowchart-reasoning |

### 可复用性 for SRS
- **重要纠正**: FloCA做的是对话引导，不是图文一致性检查
- **可复用**: 流程图图表示 F=(V,E,X) 和四种图查询函数 → 适用于SRS状态图/活动图
- **需要补充**: 文本-图对齐层 (SRS需求句子 → 节点/边属性匹配)
- **不适用**: 序列图(消息交换非状态转移)、类图/ER图(无转移语义)

---

## 4. ReqV / Vuotto (2018) — LTL for Requirements Consistency

| 项目 | 内容 |
|---|---|
| **arXiv** | 1804.10486 (4页概述) + 1712.04162 (15页完整论文) |
| **任务** | 检查功能需求集合是否可同时满足 (LTL可满足性) |
| **方法** | NL→PSP(D_C)→LTL→布尔化→LTL求解器 (aalta/NuSMV) |
| **关键纠正** | **不用Z3/SMT**，用LTL求解器; NL→PSP是**手工的** |
| **数据** | 75条机器人臂需求 + 6个注入故障 + 2560个合成benchmark |
| **结果** | 6/6故障正确检测; 1920条需求<500秒; aalta最快 |
| **代码** | github.com/SAGE-Lab/robot-arm-usecase (仅数据) |

### 可复用性 for GJB SRS
- **可复用**: LTL可满足性框架、PSP模式分类法、数值变量布尔化技术
- **最大瓶颈**: 手工NL→PSP翻译 → 需要LLM自动化
- **建议改进**: 用SMT(Z3 QF_LRA)替代LTL布尔化 → 避免阈值爆炸 + 获得unsat core
- **GJB特有需求**: 中文NL→形式化、实时约束(MTL)、更大规模

---

## 5. Chen (2025) — LLM + SMT for String Requirements

| 项目 | 内容 |
|---|---|
| **arXiv** | 2506.16639 |
| **会议** | IEEE RE 2025 |
| **任务** | 自然语言字符串需求的可满足性检查 |
| **方法** | LLM生成检查器(Python+SMT) → 反馈循环(验证+反例+解释) → CVC5求解 |
| **LLM** | GPT-4o, GPT-4o-mini, DeepSeek-V3, Llama3.1-8b |
| **数据** | 340组需求 (12类: Email/Password/ISBN等), 283 SAT + 57 UNSAT |
| **结果** | F1=93.04% (GPT-4o + Hybrid + VFE); Python检查器100%测试精度 |
| **代码** | Zenodo: 10.5281/zenodo.15679384 |

### 可复用性 for SRS
- **架构可迁移**: LLM生成检查器 + 反馈循环 + 混合验证
- **范围限制**: 仅字符串理论(str.contains, regex)，不处理数值/时序/物理约束
- **适配路径**: 替换SMT理论为QF_LRA(线性实数) → 新的prompt模板 → 新的ground truth
- **核心启示**: LLM可以自动完成NL→形式化的翻译，解决ReqV的手工瓶颈

---

## 跨论文方法对比

| 维度 | Okamoto | ChartVE | FloCA | ReqV | Chen |
|---|---|---|---|---|---|
| **检测层** | 语法 | 语义(图文) | 语义(流程图) | 逻辑 | 逻辑 |
| **方法** | LLM | VE模型 | LLM+图工具 | LTL求解 | LLM+SMT |
| **自动化** | 全自动 | 全自动 | 全自动 | **手工** | 全自动 |
| **数据规模** | 7文档 | 5,323句 | 1,212图 | 75需求 | 340组 |
| **中文支持** | 否 | 否 | 否 | 否 | 否 |
| **代码开源** | Zenodo | GitHub | GitHub | 仅数据 | Zenodo |
| **直接可用** | ★★★★ | ★★★ | ★★ | ★★ | ★★★ |

## 对我们方案的启示

### 语法层
- 直接参考Okamoto的Pall/Peach模式，替换为GJB 438C结构
- 用LLM检查SRS章节是否齐全、内容是否符合GJB要求

### 语义层
- **文本↔表格**: ChartVE的两阶段分解思路(表→结构化→推理)可迁移
- **文本↔图片**: 需要自建SRS图片VE模型(ChartVE不直接适用)，可用LLaVA/InternVL + 合成数据
- **流程图**: FloCA的图表示F=(V,E,X)可复用，但需补充文本-图对齐层

### 逻辑层
- Chen(2025)的LLM→SMT架构解决了ReqV的手工瓶颈
- 但Chen仅处理字符串，需扩展到数值约束(QF_LRA)
- 建议用Z3(而非CVC5)，获得unsat core做冲突解释
