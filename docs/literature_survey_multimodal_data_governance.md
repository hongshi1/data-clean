# 深度文献调研：多模态数据治理、数据质量校验、跨模态冲突检测

**调研日期**: 2026-07-08
**检索源**: arXiv (9 组关键词检索 + 4 组补充检索)
**检索状态**: 完整执行 6 组指定检索 + 5 组补充检索

---

## 一、检索执行摘要

| # | 检索词 | arXiv 命中数 | 备注 |
|---|--------|------------|------|
| 1 | multimodal data quality conflict detection | 3 | 多为融合/遥感，非数据治理 |
| 2 | cross-modal inconsistency data cleaning | 3 | 含 VLM-UQBench（相关） |
| 3 | data-centric AI multimodal label noise | 0 | 无结果 |
| 4 | image text mismatch detection dataset | 17 | 核心命中来源（含 FOIL/NewsCLIPpings） |
| 5 | multimodal data validation verification | 37 | 大量推理验证/报告生成，需筛选 |
| 6 | dirty data detection vision language | 0 | 无结果 |
| 补A | Data-Juicer multimodal data processing | 1 | Data-Juicer 2.0 |
| 补B | data centric AI survey multimodal | 8 | 综述类 |
| 补C | cross-modal consistency checking dataset quality | 4 | 含 MicroVQA++（相关） |
| 补D | noisy image text pairs detection cleaning | 3 | 含 DeFT/CLIPCleaner（核心） |
| 补E | confident learning label noise vision language | 8 | 含 CLIPCleaner/DeFT |
| 补F | multimodal dataset curation quality assessment benchmark | 34 | 含 HalDec-Bench/TADS（核心） |

**关键发现**: 直接命中"多模态数据集治理/跨模态冲突检测"的精确检索（#1, #3, #6）要么仅 3 条要么为 0，说明这是一个**检索词尚未被学界固化**的方向。相关论文分散在"虚假新闻检测""幻觉检测""数据筛选""标签噪声"等邻近子领域中。

---

## 二、论文分类汇总

### A类：直接检测多模态数据集中图文不一致/冲突（核心关注）

这类论文直接以"检测图像与文本/标签之间是否存在矛盾"为目标。按"检测对象"细分两个子方向：

#### A1. 检测真实数据集中的图文错配（最接近"数据治理"）

**1. FOIL it! Find One mismatch between Image and Language caption**
- 作者: Ravi Shekhar, Sandro Pezzelle, Yauhen Klimovich, Aurelie Herbelot, Moin Nabi, Enver Sangineto, Raffaella Bernardi
- 年份: 2017 | arXiv: 1705.01359 | ACL 2017
- 摘要: 构建 FOIL-COCO 数据集，将 MSCOCO 图像与"foil caption"（仅一个词错误的描述）配对，测试 LaVi 模型在 caption 分类、foil 词检测、foil 词纠正三个任务上的能力。人类近乎完美，模型表现差。
- 意义: **最早系统性地把"图文单点不一致"作为诊断任务**的工作。但其目的是"测试模型理解能力"，不是"治理数据集"。

**2. HalDec-Bench: Benchmarking Hallucination Detector in Image Captioning**
- 作者: Kuniaki Saito, Risa Shinoda, Shohei Tanaka, Tosho Hirasawa, Fumio Okura, Yoshitaka Ushiku
- 年份: 2025 | arXiv: 2511.20515
- 摘要: 评测"caption 幻觉检测器"的 benchmark。明确指出"有效的幻觉检测对于策划训练 VLM 所需的高质量 image-caption 对至关重要"，并发现"用强 VLM 作过滤器可大幅降低数据集噪声"。
- 意义: **最接近"数据集质量校验"的 A 类工作**，但仍以"幻觉检测"为框架，未上升到"数据治理"层面。

**3. MicroVQA++: High-Quality Microscopy Reasoning Dataset with Weakly Supervised Graphs**
- 作者: Manyu Li, Ruian He, Chenxi Ma, Weimin Tan, Bo Yan
- 年份: 2025 | arXiv: 2511.11407
- 摘要: 提出 HiCQA-Graph——**首个联合建模 (image, caption, QA) 的异构图**，融合 NLI 文本蕴含、CLIP 视觉-语言对齐、agent 信号来识别并过滤不一致样本。
- 意义: 显式做了"跨模态一致性过滤"，但是领域特定（显微镜 VQA），非通用数据治理框架。

#### A2. 检测"跨模态不一致"作为下游任务（多为虚假信息/谣言检测）

这类工作技术上检测图文不一致，但应用场景是"判别新闻真伪"而非"清洗数据集"：

**4. NewsCLIPpings: Automatic Generation of Out-of-Context Multimodal Media**
- 作者: Grace Luo, Trevor Darrell, Anna Rohrbach
- 年份: 2021 | arXiv: 2104.05893 | EMNLP 2021
- 摘要: 构建大规模自动生成的"图文错配"数据集（图像和文本均未篡改但互不匹配），benchmark 多模态模型。
- 意义: "out-of-context media detection" 的标杆数据集。**技术上是图文冲突检测，但任务是虚假信息检测。**

**5. Twitter-COMMs: Detecting Climate, COVID, and Military Multimodal Misinformation**
- 作者: Giscard Biamby, Grace Luo, Trevor Darrell, Anna Rohrbach
- 年份: 2021/2022 | arXiv: 2112.08594
- 摘要: 基于 CLIP 检测"mis-captioned"图像，884k 推文。
- 意义: 同上，应用为虚假信息。

**6. Cross-modal Consistency Learning with Fine-grained Fusion Network (CFFN)**
- 作者: Jun Li, Yi Bin, Jie Zou, Guoqing Wang, Yang Yang
- 年份: 2023 | arXiv: 2311.01807
- 摘要: 将 word-region 对分为高/低相关，分别探索一致性与不一致性，用于多模态假新闻检测。
- 意义: 显式建模"不一致性得分"，但目标是假新闻分类。

**7. HNC: Leveraging Hard Negative Captions**
- 作者: Esra Dönmez, Pascal Tilli, Hsiu-Yu Yang, Thang Vu, Carina Silberer
- 年份: 2023/2026 | arXiv: 2605.06157 | CoNLL 2023
- 摘要: 自动构建"foil hard negative caption"用于 ITM 训练，提升细粒度跨模态理解与 mismatch 检测。
- 意义: 与 FOIL-COCO 一脉相承，关注"检测能力"。

**8. VLM-UQBench: A Benchmark for Modality-Specific and Cross-Modality Uncertainties in VLMs**
- 作者: Chenyu Wang, Tianle Chen, H.M. Sabbir Ahmad, Kayhan Batmanghelich, Wenchao Li
- 年份: 2026 | arXiv: 2602.09214
- 摘要: 600 真实样本，分为 clean/image/text/cross-modal uncertainty 子集，含 3 种跨模态扰动。发现现有 UQ 方法在实例级模糊性上基本失效。
- 意义: **明确把"图像-文本不对齐"作为一类不确定性来源**进行 benchmark，接近"数据质量校验"。

**9. DGM4+: Dataset Extension for Global Scene Inconsistency**
- 作者: Gagandeep Singh 等
- 年份: 2025 | arXiv: 2509.26047
- 摘要: 扩展 DGM4 数据集，引入"前景-背景错配"等全局不一致，benchmark 多模态伪造检测器。
- 意义: 检测"场景级不一致"，应用为伪造检测。

**10. GMF: Geometry-based Schrödinger Bridges for Trustworthy Multimodal Fusion**
- 作者: Jiayu Xiong 等
- 年份: 2026 | arXiv: 2605.31193 | ICML 2026
- 摘要: 不依赖模型预测，用 latent space 的"transport correction"强度评估输入可靠性，能标记噪声/不完整/冲突输入。
- 意义: **以"冲突输入检测"为可靠性信号**，但属于融合鲁棒性，非数据集治理。

---

### B类：多模态数据清洗/治理框架

**11. Data-Juicer 2.0: Cloud-Scale Adaptive Data Processing**
- 作者: Daoyuan Chen 等（阿里巴巴）
- 年份: 2025 | arXiv: 2501.14755 | NeurIPS 2025 Spotlight
- 摘要: 100+ 数据处理算子，覆盖 text/image/video/audio，支持分析/合成/标注/后训练。TB 级处理能力。
- 关键判断: **支持多模态数据处理与质量过滤，但其算子主要是单模态质量打分（如 CLIP score、图像清晰度、文本长度），没有专门的"跨模态冲突检测"算子。** 多模态部分更多是"对齐过滤"而非"冲突检测"。

**12. AITQE: Adaptive Image-Text Quality Enhancer**
- 作者: Han Huang 等
- 年份: 2024 | arXiv: 2410.16166
- 摘要: 动态评估并增强 image-text 对质量，对低质量对做文本重写，而非简单丢弃。
- 意义: 数据增强视角，非冲突检测。

**13. DOSE: Data Selection for Multi-Modal LLMs via Off-the-Shelf Models**
- 作者: Biao Wu 等
- 年份: 2026 | arXiv: 2604.16979
- 摘要: 用未见过目标数据的预训练模型评估"文本质量"和"图文对齐"，构建联合质量-对齐分布做自适应采样。
- 意义: 数据选择视角，"对齐"作为质量维度之一。

**14. TADS: Task-Aware Data Selection for Multi-Task Multimodal Pre-Training**
- 作者: Guanjie Cheng 等
- 年份: 2026 | arXiv: 2602.05251
- 摘要: 含 unimodal 和 cross-modal 算子的质量评估体系，含任务相关性、分布多样性。
- 意义: 最系统的"多模态数据质量评估"框架之一，但目标是"高效子集选择"而非"冲突检测"。

**15. Filter & Align: Leveraging Human Knowledge to Curate Image-Text Data**
- 作者: Lei Zhang 等
- 年份: 2023 | arXiv: 2312.06726
- 摘要: 用人类知识策划图文数据。
- 意义: 数据策划，非冲突检测。

**16. CHNR: Unsupervised Cross-Modal Hashing Robust to Noisy Image-Text Correspondences**
- 作者: Georgii Mikriukov, Mahdyar Ravanbakhsh, Begüm Demir
- 年份: 2022 | arXiv: 2202.13117
- 摘要: 含"噪声检测模块"，用少量干净数据元学习训练，在含噪声图文对应关系的数据上做跨模态检索。
- 意义: 显式做了"噪声对应检测"，但嵌入在检索任务中，非独立治理工具。

**17. SC-AGIQA: Text-Visual Semantic Constrained AI-Generated Image Quality Assessment**
- 作者: Qiang Li 等
- 年份: 2025 | arXiv: 2507.10432 | ACMMM 2025
- 摘要: 用 MLLM 生成图像描述并与原 prompt 比对做一致性检查。
- 意义: 针对 AI 生成图像的质量评估，含 text-image consistency。

---

### C类：标签噪声检测（image-label mismatch）

这类工作检测"图像分类标签错误"，本质是单标签噪声，非"图文语义冲突"。

**18. DeFT: Vision-Language Models are Strong Noisy Label Detectors**
- 作者: Tong Wei 等
- 年份: 2024 | arXiv: 2409.19696 | NeurIPS 2024
- 摘要: 学习正/负文本 prompt，正 prompt 揭示类特征，负 prompt 作为分离 clean/noisy 的可学习阈值。
- 意义: **用 VLM 的跨模态对齐能力做标签噪声检测**，但仍是分类标签噪声，不是"图文内容矛盾"。

**19. CLIPCleaner: Cleaning Noisy Labels with CLIP**
- 作者: Chen Feng 等
- 年份: 2024 | arXiv: 2408.10012 | ACMMM 2024
- 摘要: 用 CLIP 零样本分类器离线选干净样本，避免 in-training 模型的自确认偏差。
- 意义: 首次用 VL 模型做样本选择，但仍是分类标签清洗。

**20. CARE: Class-Adaptive Expert Consensus for Reliable Learning with Long-Tailed Noisy Labels**
- 作者: Mengke Li 等
- 年份: 2026 | arXiv: 2605.23254 | ICML 2026
- 摘要: 融合噪声标签、VLM 文本嵌入、视觉特征，类自适应专家共识。
- 意义: 标签噪声，长尾场景。

---

### D类：data-centric AI 相关但非冲突检测

**21. CLIP the Bias: How Useful is Balancing Data in Multimodal Learning?**
- 作者: Ibrahim Alabdulmohsin 等（Google DeepMind）
- 年份: 2024 | arXiv: 2403.04547 | ICLR 2024
- 摘要: 研究 CLIP 数据平衡对偏见的影响，提出 M4 算法。
- 意义: 数据平衡，非冲突检测。

**22. Multimodal Alignment and Fusion: A Survey**
- 作者: Songtao Li, Hao Tang
- 年份: 2024 | arXiv: 2411.17040 | IJCV 2025
- 摘要: 综述多模态对齐与融合，提到"cross-modal misalignment, data quality issues"为挑战。
- 意义: 综述确认该问题是"challenge"，但无解决方案。

---

### E类：其他（不相关）

包括大量：遥感变化检测、谣言检测、讽刺检测、医疗报告生成、几何题生成、视觉 bug 检测（HTML canvas）、greenwashing 检测、后门攻击等。共约 50+ 篇，均非数据治理方向。

---

## 三、重点问题回答

### Q1: 有没有人做"多模态数据集治理"的系统性工作？

**部分有，但不完整。** 最接近的是：
- **Data-Juicer 2.0**（NeurIPS 2025 Spotlight）——最系统的多模态数据处理系统，100+ 算子，但**无专门的"跨模态冲突检测"算子**，质量过滤以单模态为主。
- **TADS**（2026）——含 cross-modal 算子的质量评估体系，但目标是"高效子集选择"。
- **HalDec-Bench**（2025）——明确提出"用幻觉检测策划高质量 image-caption 对"，但仍是 benchmark，非治理框架。

**结论: 没有一篇论文以"多模态数据集治理"为框架名，将跨模态冲突检测作为核心数据质量校验方法进行系统化定义。**

### Q2: 有没有人提出"跨模态冲突检测"作为数据质量校验方法？

**没有以这个名义提出的。** 但技术上有近邻：
- "图文不一致检测"在虚假信息领域被大量研究（NewsCLIPpings、Twitter-COMMs、CFFN），但**框架是"虚假信息检测"而非"数据质量校验"**。
- "caption 幻觉检测"（HalDec-Bench）最接近，但**框架是"幻觉"而非"冲突"**。
- "噪声图文对应检测"（CHNR）嵌入在检索任务中。
- "跨模态不确定性"（VLM-UQBench）把图文不对齐作为不确定性来源。

**结论: "跨模态冲突检测"作为独立的数据质量校验方法论，目前是一个未被显式定义的研究空白。** 技术积木存在（CLIP score、NLI、foil 检测），但未被组装成"数据治理"框架。

### Q3: Data-Juicer、CleanLab、Great Expectations 是否支持多模态冲突检测？

| 工具 | 多模态支持 | 跨模态冲突检测 | 说明 |
|------|-----------|--------------|------|
| **Data-Juicer 2.0** | 支持（text/image/video/audio 算子） | **不支持** | 有图文对齐过滤（如 CLIP score 阈值），但无"语义冲突检测"算子；质量打分以单模态为主 |
| **CleanLab** | 主要单模态（分类标签） | **不支持** | 基于 confident learning 的标签噪声检测，无跨模态冲突概念；arXiv 检索 "cleanlab multimodal" 为 0 结果 |
| **Great Expectations** | 无多模态支持 | **不支持** | 传统表格数据验证框架，无视觉/语言模态概念 |

**结论: 三大主流数据治理工具均不支持"跨模态冲突检测"。** CleanLab 和 Great Expectations 甚至不支持多模态；Data-Juicer 支持多模态处理但停留在"对齐过滤"层面。

### Q4: VDC（ICLR 2024）算不算这个方向？还有没有类似方法？

**VDC 无法在 arXiv 检索中定位**（"verifying dataset correctness" 精确检索 0 结果，组合检索也未命中）。基于用户提及，VDC（ICLR 2024） likely 是用 LLM 验证数据集正确性的工作。若其验证对象是"单模态表格/文本数据集"，则**不属于多模态冲突检测**；若涉及多模态，则需确认。

类似的通用"脏数据检测"方法：
- **DeFT**（NeurIPS 2024）——用 VLM 检测分类标签噪声，最接近但仍是标签级。
- **CLIPCleaner**（ACMMM 2024）——用 CLIP 零样本选干净样本。
- **HalDec-Bench**——用 VLM 检测 caption 中的幻觉/错误。

**结论: 现有"通用脏数据检测"方法要么是单模态的（表格/文本），要么是"标签噪声"级的（分类标签），没有上升到"多模态语义冲突"层面。**

### Q5: 有没有 benchmark 专门评测多模态数据集中的冲突/不一致？

**有，但分散且框架不一：**
- **FOIL-COCO**（2017）——单词级 foil 检测，最早期。
- **NewsCLIPpings**（2021）——out-of-context 图文，大规模自动生成。
- **HalDec-Bench**（2025）——caption 幻觉检测，**最接近"数据集噪声过滤"评测**。
- **VLM-UQBench**（2026）——跨模态不确定性，含 cross-modal perturbation。
- **DGM4+**（2025）——全局场景不一致，伪造检测向。

**结论: 没有一个 benchmark 以"多模态数据集治理"为框架，系统评测"各类跨模态冲突（标签-图像、caption-图像、属性-图像、关系-图像等）的检测能力"。** 现有 benchmark 各自评测一种"不一致"，且应用目标不同（假新闻/幻觉/伪造）。

---

## 四、最终结论

### 1. 论文数量与活跃度

| 子方向 | 论文数（去重后） | 活跃度 |
|--------|----------------|--------|
| A类（图文冲突检测，含虚假信息向） | ~10 | 中等，2017 起持续有，但分散在多个应用标签下 |
| B类（多模态数据清洗/治理框架） | ~7 | 上升中，2024-2026 集中（Data-Juicer/TADS/DOSE） |
| C类（标签噪声检测，VLM 辅助） | ~5 | 活跃，NeurIPS/ICML/ACMMM 持续接收 |
| 精确命中"多模态数据治理+冲突检测" | **0** | — |

**活跃度判断**: 邻近方向（数据筛选、标签噪声、幻觉检测）活跃，但"跨模态冲突检测作为数据治理方法"本身**未被作为一个独立研究方向确立**。

### 2. A类论文完整列表

见第二节 A1/A2 详述，共 10 篇。其中**最接近"数据集治理"的是 HalDec-Bench（#2）和 MicroVQA++（#3）**；技术最经典的是 FOIL-COCO（#1）和 NewsCLIPpings（#4）。

### 3. 是否为研究空白？

**是研究空白，且是"框架性空白"而非"技术空白"。**

具体而言：
- **技术积木已存在**: CLIP score 做图文对齐、NLI 做文本蕴含、foil 检测做单词级错误、VLM 做幻觉检测、confident learning 做标签噪声。
- **框架缺失**: 没有论文将"跨模态冲突检测"定义为多模态数据集治理的核心校验方法，建立系统化的冲突类型分类（标签冲突、属性冲突、关系冲突、场景冲突等）、检测算子库、和 benchmark。
- **工具缺失**: Data-Juicer/CleanLab/Great Expectations 均不支持。
- **benchmark 缺失**: 无统一 benchmark 评测"多模态数据集冲突检测"。

**可立项的研究方向**: "面向多模态数据集治理的跨模态冲突检测框架"——定义冲突类型分类、设计检测算子、构建 benchmark、集成到 Data-Juicer 类工具。

### 4. 与"报告生成一致性"方向的区别和联系

| 维度 | 多模态数据集治理/冲突检测 | 报告生成一致性 |
|------|------------------------|--------------|
| **检测对象** | 静态数据集中的图文对（训练数据） | 模型生成的报告与输入（推理输出） |
| **冲突来源** | 数据采集/标注/爬取引入的错误 | 模型幻觉/生成错误 |
| **时间点** | 训练前（数据清洗） | 推理时/推理后（输出校验） |
| **典型方法** | CLIP score、foil 检测、NLI 蕴含 | cross-view consistency reward、verifier 模型 |
| **代表工作** | FOIL-COCO、HalDec-Bench、NewsCLIPpings | E-MRL（2606.23888）、ReLoop（2507.04943） |
| **联系** | 两者都检测"图文语义不一致"，技术可互借（如 NLI、CLIP）；数据集治理可为报告一致性提供干净训练数据 |

**关键区别**: 报告生成一致性是"检查模型输出是否与输入图像一致"（output validation），数据集治理是"检查训练数据中图文对是否本身就有矛盾"（input validation）。两者技术栈相似但**目标对象相反**——一个查输出，一个查输入。

---

## 五、检索词建议（供后续 Google Scholar 补检）

arXiv 命中率低，建议用以下词在 Google Scholar / Semantic Scholar 补检：
- "image-caption consistency" + "dataset"
- "vision-language" + "data quality" + "noise"
- "cross-modal contradiction" + "detection"
- "hallucination detection" + "data curation"
- "mislabeled image-text pairs"
- "CLIP score" + "data filtering" + "noise"
