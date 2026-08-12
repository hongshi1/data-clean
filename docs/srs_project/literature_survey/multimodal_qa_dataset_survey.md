# 软件工程/技术文档领域多模态QA数据集调研报告

> 调研日期：2026-08-12
> 调研目的：为SRS一致性校验项目寻找可借鉴的多模态QA数据集，了解现有数据集的模态组合、任务定义和评测方式
> 搜索关键词：software engineering multimodal QA dataset、UML diagram question answering dataset、software requirement specification multimodal benchmark

---

## 一、调研概述

本次调研通过DuckDuckGo搜索引擎（Google需JavaScript无法直接抓取）搜索三组关键词，共发现**13个**与软件工程/技术文档/图表理解相关的多模态QA数据集。按与SRS场景的相关性分为三类：

| 相关性等级 | 数据集 | 说明 |
|-----------|--------|------|
| **高相关** | FlowVQA、UML-VQA(MDPI)、UML-VQA(arXiv)、Multi-Modal AI for SRS Validation | 直接涉及流程图/UML图/需求文档 |
| **中相关** | PDF-MVQA、DocVQA、ScreenQA、DiagramQG、UML-Class-Diagram-Dataset | 涉及文档/图表/截图理解 |
| **低相关(可参考方法)** | MultiModalQA、InfographicVQA、ChartQA、DocVQA-2026 | 通用多模态QA，方法论可借鉴 |

---

## 二、高相关性数据集（直接涉及SE/需求/图表）

### 2.1 FlowVQA — 流程图视觉问答基准

| 属性 | 内容 |
|------|------|
| **名称** | FlowVQA: Mapping Multimodal Logic in Visual Question Answering with Flowcharts |
| **来源** | ACL 2024 Findings |
| **规模** | 2,272张流程图 + 22,413个QA对 |
| **模态** | 图（流程图图像）+ 文（Mermaid脚本、标签化文本表示）+ 代码（FloCo代码片段转换的流程图） |
| **任务类型** | 视觉问答（VQA），含4类问题：Fact Retrieval（事实检索）、Applied Scenario（应用场景推理）、Flow Referential（流程引用推理）、Topological（拓扑结构推理） |
| **数据来源** | WikiHow文章(1,121篇)、Instructables DIY博客(701篇)、FloCo代码片段(450个) |
| **开源地址** | https://github.com/flowvqa/flowvqa 、 https://flowvqa.github.io/ |
| **SRS相关性** | **★★★★★** SRS文档中大量使用流程图描述系统行为/数据处理流程。FlowVQA的拓扑推理任务（如"流程图有多少节点"）和应用场景推理任务（如"执行某操作后下一步是什么"）与SRS中的逻辑一致性校验高度吻合。其"流程图→Mermaid脚本→标签化文本"的转换pipeline可直接用于SRS流程图的结构化解析。 |

**关键发现**：
- GPT-4在Few-shot directive prompting下仅达到68.42%的Majority Voting准确率，说明流程图理解仍是开放挑战
- 问题类型设计（事实检索vs拓扑推理）为SRS一致性检测的问题设计提供了分类框架
- 流程图生成pipeline（文本→Mermaid→图像）可逆向用于SRS流程图的结构化解析

---

### 2.2 UML-VQA (MDPI 2025) — UML类图复杂度分析VQA

| 属性 | 内容 |
|------|------|
| **名称** | Automatic Complexity Analysis of UML Class Diagrams Using Visual Question Answering |
| **来源** | MDPI Computer Sciences & Mathematics Forum, Vol.4, No.4, Art.22, 2025 |
| **规模** | 1,300张UML类图 + 10,338个QA对 |
| **模态** | 图（UML类图图像） |
| **任务类型** | VQA，聚焦UML类图复杂度分析 |
| **数据来源** | 自动生成+人工标注的UML类图 |
| **开源地址** | https://www.mdpi.com/2674-113X/4/4/22 （论文页面，403需其他方式获取） |
| **SRS相关性** | **★★★★☆** SRS文档中的接口设计章节常包含UML类图/序列图。该数据集是首个专为UML类图VQA构建的数据集，其复杂度分析任务（如类间关系数量、继承深度等）可用于SRS中接口一致性的自动校验。 |

---

### 2.3 UML-VQA (arXiv 2605.11634, 2026) — UML类图VLM理解基准

| 属性 | 内容 |
|------|------|
| **名称** | Unlocking UML Class Diagram Understanding in Vision Language Models |
| **来源** | arXiv:2605.11634, 2026年5月 |
| **规模** | 16,000个 图像-问题-答案三元组（训练集），另含benchmark测试集 |
| **模态** | 图（UML类图图像）+ 文（QA文本） |
| **任务类型** | VQA，评估VLM对UML类图的理解能力 |
| **数据来源** | 大规模自动构造 |
| **开源地址** | https://arxiv.org/abs/2605.11634 |
| **SRS相关性** | **★★★★☆** 与2.2互补，规模更大(16K vs 10K)。关键发现：LoRA微调后的小模型即可超越Qwen 3.5 27B，说明UML图理解需要领域适配而非单纯依赖模型规模。这为SRS场景下的小模型微调策略提供了依据。 |

---

### 2.4 Multi-Modal AI for Software Requirements Validation — 需求验证多模态AI

| 属性 | 内容 |
|------|------|
| **名称** | Multi-Modal AI for Software Requirements Validation |
| **来源** | ResearchGate（Mona Nasr等，2025年发表） |
| **规模** | 未公开（论文级别，非标准数据集） |
| **模态** | 文（需求文本）+ 图（需求相关图表/截图） |
| **任务类型** | 需求验证（Requirements Validation），利用NLP+计算机视觉的多模态偏差检测 |
| **数据来源** | 软件需求规格说明文档 |
| **开源地址** | https://www.researchgate.net/profile/Mona-Nasr-4/publication/393004516 （403需登录） |
| **SRS相关性** | **★★★★★** 这是本次调研中**唯一直接针对SRS需求验证**的多模态AI研究。其核心思路——"利用NLP和计算机视觉的多模态偏差来验证软件需求"——与我们的SRS一致性校验方向B高度一致。虽然无法获取全文细节，但其存在证明该方向具有研究价值且尚属空白。 |

---

## 三、中相关性数据集（文档/图表/截图理解）

### 3.1 PDF-MVQA (MMVQA) — 多页PDF多模态信息检索VQA

| 属性 | 内容 |
|------|------|
| **名称** | PDF-MVQA: A Dataset for Multimodal Information Retrieval in PDF-based Visual Question Answering |
| **来源** | IJCAI 2024 / arXiv:2404.12720 |
| **规模** | 3,146篇多页PDF文档（30,239页） + 262,928个QA对 |
| **模态** | 图（PDF页面图像）+ 文（段落文本）+ 表（表格实体）+ 图（图片/图表实体） |
| **任务类型** | 多模态文档信息检索（DIR），跨页定位包含答案的语义实体（段落/表格/图片） |
| **数据来源** | PubMed Central生物医学期刊开放获取文章 |
| **开源地址** | https://github.com/adlnlp/mmvqa 、 https://arxiv.org/html/2404.12720v1 |
| **SRS相关性** | **★★★★☆** SRS是典型的多页、多模态（文字+表格+图片+流程图）文档。PDF-MVQA的"跨页语义实体检索"任务与SRS的"上下文关联"（方向A）高度吻合——需要将分散在多页的段落、表格、图片关联起来。其Super-Section概念（Introduction/M&M/R&D/Conclusion）可映射到SRS的章节结构（3.1功能/3.2接口/3.3约束等）。Joint-grained框架（粗粒度实体+细粒度token）对SRS条目聚合有参考价值。 |

**关键发现**：
- 最佳模型ViLT的Exact Match仅23.47%，说明多页文档理解仍极具挑战
- 表格/图片相关问题的回答需要跨页推理，与SRS中"合格性表中的行对应哪个需求"的问题一致
- 评测指标设计（EM/PM/MR三级匹配）可为SRS一致性检测的评测提供参考

---

### 3.2 DocVQA — 文档视觉问答基准

| 属性 | 内容 |
|------|------|
| **名称** | DocVQA: A Dataset for VQA on Document Images |
| **来源** | WACV 2021 / ICDAR竞赛系列 |
| **规模** | 50,000+ 文档图像 + 79,000+ QA对（原始DocVQA）；后续扩展为MP-DocVQA（多页）、DUDE（文档理解）等 |
| **模态** | 图（扫描文档图像） |
| **任务类型** | 文档图像上的VQA，提取文档中的文本信息回答问题 |
| **数据来源** | 真实行业文档（表单、发票、合同等） |
| **开源地址** | https://www.docvqa.org/ |
| **SRS相关性** | **★★★☆☆** DocVQA系列是文档VQA的奠基性工作。其多页扩展版MP-DocVQA与SRS多页文档场景相关。但DocVQA主要面向信息抽取（"文档里写了什么"），而非一致性校验（"文档内部是否矛盾"），任务定义不同。其文档布局分析方法可借鉴。 |

---

### 3.3 ScreenQA — 屏幕内容理解VQA

| 属性 | 内容 |
|------|------|
| **名称** | ScreenQA: A Dataset for Screen Content Understanding via QA |
| **来源** | Google Research |
| **规模** | 基于Rico数据集的屏幕截图，含大量QA对 |
| **模态** | 图（UI截图）+ 文（UI元素文本） |
| **任务类型** | 屏幕截图VQA，理解UI布局和交互元素 |
| **数据来源** | Rico数据集（Android应用截图） |
| **开源地址** | https://github.com/google-research-datasets/screen_qa |
| **SRS相关性** | **★★★☆☆** SRS文档中的"人机交互界面"章节常包含UI截图/原型图。ScreenQA的屏幕理解能力可用于校验SRS中界面描述与界面截图的一致性。但ScreenQA聚焦移动端UI，与SRS的桌面/嵌入式系统界面有差异。 |

---

### 3.4 DiagramQG — 图表问题生成数据集

| 属性 | 内容 |
|------|------|
| **名称** | DiagramQG: A Dataset for Generating Concept-Focused Questions from Diagrams |
| **来源** | arXiv:2411.17771, 2024年11月 |
| **规模** | 8,372张图表 + 19,475个问题（44,472个 图表-问题-约束 三元组） |
| **模态** | 图（教学图表）+ 文（目标文本约束、概念约束、问题） |
| **任务类型** | 视觉问题生成（VQG），给定图表+目标文本+概念，生成概念聚焦的问题 |
| **数据来源** | 整合AI2D、DVQA、IconQA、SciTalon等已有图表QA数据集 + Google Image Search + 中学课程材料 |
| **覆盖范围** | 4学科(自然科学/地球科学/应用科学/社会科学) × 15课程 × 169概念 |
| **开源地址** | https://dxzxy12138.github.io/diagramqg-home |
| **SRS相关性** | **★★★☆☆** 虽然是问题生成（而非回答）数据集，但其"概念聚焦"的问题设计思路可借鉴——SRS一致性检测可以建模为"给定SRS条目，生成检测不一致性的问题"。其分层知识提取框架(HKI-DQG: 多尺度patch→VLM知识提取→知识筛选→融合生成)对SRS图表理解有方法论参考价值。 |

---

### 3.5 UML-Class-Diagram-Dataset — UML类图大规模数据集

| 属性 | 内容 |
|------|------|
| **名称** | UML Class Diagram Dataset |
| **来源** | GitHub (NilsBaumgartner1994), ENASE 2024 |
| **规模** | 爬取>200,000图表 → 识别>155,000 UML图 → 104,604 UML类图（104,602已解析） |
| **模态** | 图（UML类图图像）+ 结构化数据（解析后的类/属性/关系信息） |
| **任务类型** | 非QA数据集，用于UML图分析、机器学习训练、软件设计模式理解 |
| **数据来源** | GenMyModel公共API爬取 |
| **开源地址** | https://github.com/NilsBaumgartner1994/UML-Class-Diagram-Dataset |
| **SRS相关性** | **★★★☆☆** 可作为SRS中UML图解析的训练数据来源。其UML图解析pipeline（图像→结构化类信息）可用于SRS中接口/类图的结构化提取，为一致性校验提供结构化输入。非QA数据集，但可作为QA数据集构建的基础。 |

---

## 四、低相关性数据集（方法论可参考）

### 4.1 MultiModalQA (MMQA) — 跨模态复杂问答

| 属性 | 内容 |
|------|------|
| **名称** | MultiModalQA: Complex Question Answering over Text, Tables and Images |
| **来源** | NAACL 2021 / arXiv:2104.06039 |
| **规模** | 包含文本、表格、图像的跨模态QA |
| **模态** | 文（Wikipedia段落）+ 表（Wikipedia表格）+ 图（Wikipedia图片） |
| **任务类型** | 跨模态联合推理，需要同时利用文本+表格+图片回答复杂问题 |
| **开源地址** | https://arxiv.org/abs/2104.06039 |
| **SRS相关性** | **★★☆☆☆** SRS同样包含文字+表格+图片三种模态。MMQA的跨模态联合推理框架（如何将不同模态的信息关联起来回答问题）可为SRS条目聚合（方向A）提供方法论参考。但MMQA基于Wikipedia通用知识，与SRS的技术文档领域差异大。 |

---

### 4.2 InfographicVQA — 信息图VQA

| 属性 | 内容 |
|------|------|
| **名称** | InfographicVQA |
| **来源** | WACV 2022 / arXiv:2104.12756 |
| **规模** | ~30,000信息图 + ~30,000 QA对 |
| **模态** | 图（信息图，含文本+图形+视觉元素组合） |
| **任务类型** | 信息图VQA |
| **开源地址** | https://www.docvqa.org/datasets/infographicvqa |
| **SRS相关性** | **★★☆☆☆** 信息图与SRS中的系统架构图/数据流图有相似的"图文混合"特征。其文档布局分析方法可借鉴。 |

---

### 4.3 ChartQA — 图表VQA

| 属性 | 内容 |
|------|------|
| **名称** | ChartQA: A Benchmark for Question Answering about Charts |
| **来源** | ACL 2022 |
| **规模** | 9,600图表 + 20,882 QA对（人工+增强） |
| **模态** | 图（柱状图/折线图/饼图等） |
| **任务类型** | 图表VQA，含数值推理和视觉推理 |
| **开源地址** | https://github.com/vis-nlp/ChartQA |
| **SRS相关性** | **★★☆☆☆** SRS中的性能指标章节常包含图表。ChartQA的数值推理能力可用于校验SRS中图表数据与文字描述的数值一致性。 |

---

### 4.4 DocVQA-2026 — ICDAR 2026多域文档推理竞赛

| 属性 | 内容 |
|------|------|
| **名称** | DocVQA 2026: ICDAR2026 Competition on Multimodal Reasoning over Documents in Multiple Domains |
| **来源** | ICDAR 2026 竞赛 |
| **规模** | 覆盖8个领域的文档（含**工程图纸**） |
| **模态** | 图（多类型文档图像） |
| **任务类型** | 多域文档多模态推理 |
| **数据来源** | 商业报告、科学论文、幻灯片、海报、地图、漫画、信息图、**工程图纸** |
| **开源地址** | https://github.com/VLR-CVC/DocVQA2026 |
| **SRS相关性** | **★★★☆☆** 首次将"工程图纸"(engineering drawings)纳入DocVQA领域，与SRS中的技术图纸/接口图最为接近。值得持续关注其数据集发布。 |

---

## 五、综合分析与对SRS项目的启示

### 5.1 数据集模态组合对比

| 数据集 | 文本 | 图像 | 表格 | 代码 | 流程图/UML | 多页 |
|--------|:----:|:----:|:----:|:----:|:----------:|:----:|
| FlowVQA | ✅ | ✅ | ❌ | ✅ | ✅(流程图) | ❌ |
| UML-VQA(MDPI) | ✅ | ✅ | ❌ | ❌ | ✅(UML) | ❌ |
| UML-VQA(arXiv) | ✅ | ✅ | ❌ | ❌ | ✅(UML) | ❌ |
| PDF-MVQA | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| DocVQA | ✅ | ✅ | ❌ | ❌ | ❌ | 部分 |
| ScreenQA | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| DiagramQG | ✅ | ✅ | ❌ | ❌ | ✅(教学图) | ❌ |
| MMQA | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **SRS(我们的)** | **✅** | **✅** | **✅** | **✅** | **✅** | **✅** |

**关键发现**：现有数据集中**没有一个**同时覆盖SRS的全部模态组合（文字+图片+表格+代码+流程图/UML+多页）。这证明我们的SRS多模态一致性校验方向具有**数据集层面的创新空间**。

### 5.2 任务类型对比

| 任务类型 | 代表数据集 | 与SRS一致性校验的关系 |
|---------|-----------|---------------------|
| 事实检索(Fact Retrieval) | FlowVQA, DocVQA | → SRS参数值提取（"某参数的值是多少？"） |
| 拓扑/结构推理 | FlowVQA(Topological) | → SRS章节结构校验（"3.2节有多少子节？"） |
| 应用场景推理 | FlowVQA(Applied Scenario) | → SRS逻辑一致性（"某操作后系统状态如何？"） |
| 跨页实体检索 | PDF-MVQA | → SRS上下文关联（"表格X对应哪个需求？"） |
| 复杂度分析 | UML-VQA(MDPI) | → SRS接口复杂度校验 |
| 问题生成 | DiagramQG | → SRS不一致性检测问题自动生成 |
| 需求验证 | Multi-Modal AI for SRS | → 直接对应SRS一致性校验 |

### 5.3 对方向A（上下文关联）的启示

1. **PDF-MVQA的Super-Section概念**可直接映射到SRS章节结构：SRS的3.1(功能)/3.2(接口)/3.3(性能)等章节类比于论文的Intro/M&M/R&D
2. **PDF-MVQA的Joint-grained框架**（粗粒度实体+细粒度token）适合SRS条目聚合：先将SRS切分为语义实体（段落/表格行/图片），再用细粒度token做关联
3. **FlowVQA的Mermaid脚本中间表示**提供了"流程图→结构化文本"的转换方法，可用于SRS流程图的结构化解析后与文字描述对比

### 5.4 对方向B（不一致性校验）的启示

1. **FlowVQA的4类问题分类**（事实检索/应用场景/流程引用/拓扑）可作为SRS不一致性检测问题的分类框架
2. **DiagramQG的问题生成方法**可用于自动生成SRS一致性检测问题
3. **Multi-Modal AI for SRS Validation**证明该方向有研究价值但尚属空白——我们的工作可填补这一空白
4. **UML-VQA的LoRA微调发现**（小模型+微调 > 大模型zero-shot）提示SRS场景需要领域适配

### 5.5 评测方法借鉴

| 评测方法 | 来源 | 对SRS的适用性 |
|---------|------|-------------|
| Exact Match / Partial Match / Multi-Label Recall | PDF-MVQA | 适合SRS条目检索评测（精确匹配/部分匹配/多标签召回） |
| Majority Voting Accuracy | FlowVQA | 适合SRS一致性判断（多次投票减少随机性） |
| Diagram Element Hit Number (DEHN) | DiagramQG | 可改造为"SRS条目覆盖数"，衡量检测是否覆盖所有相关条目 |
| ANLS (Average Normalized Levenshtein Similarity) | DocVQA | 适合SRS文本答案的模糊匹配评测 |

---

## 六、推荐优先参考

按对SRS项目的参考价值排序：

1. **FlowVQA** — 流程图推理的任务设计和评测方法最贴近SRS逻辑一致性检测
2. **PDF-MVQA** — 多页多模态文档的跨页实体检索与SRS上下文关联高度吻合
3. **UML-VQA(arXiv 2605.11634)** — UML图理解的小模型微调策略
4. **Multi-Modal AI for SRS Validation** — 唯一直接针对SRS的研究（需获取全文）
5. **DiagramQG** — 问题自动生成方法可用于SRS检测问题构建
6. **DocVQA-2026** — 含工程图纸域，值得关注后续发布

---

## 七、数据集缺口与我们的机会

通过调研发现以下**明确的数据集缺口**：

1. **无SRS专用多模态QA数据集** — Multi-Modal AI for SRS Validation是方法论文非标准数据集
2. **无跨模态一致性校验数据集** — 现有数据集均为"问答"任务，无"检测矛盾"任务
3. **无中文技术文档多模态QA数据集** — 现有数据集均为英文
4. **无表格-文字-图片联合一致性标注** — 现有数据集不标注"同一实体在不同模态的值是否一致"

**我们的机会**：基于16份真实GJB格式SRS构建首个**中文技术文档多模态一致性校验Gold Standard**，填补上述全部4个缺口。

---

## 附录：数据集快速索引

| # | 数据集 | 规模 | 模态 | 开源地址 |
|---|--------|------|------|---------|
| 1 | FlowVQA | 2,272图+22,413 QA | 流程图+文+代码 | github.com/flowvqa/flowvqa |
| 2 | UML-VQA(MDPI) | 1,300图+10,338 QA | UML类图+文 | mdpi.com/2674-113X/4/4/22 |
| 3 | UML-VQA(arXiv) | 16,000 QA三元组 | UML类图+文 | arxiv.org/abs/2605.11634 |
| 4 | Multi-Modal AI for SRS | 未公开 | 需求文本+图 | ResearchGate(需登录) |
| 5 | PDF-MVQA | 3,146文档+262,928 QA | PDF+表+图+文 | github.com/adlnlp/mmvqa |
| 6 | DocVQA | 50,000+图+79,000+ QA | 扫描文档 | docvqa.org |
| 7 | ScreenQA | 基于Rico | UI截图+文 | github.com/google-research-datasets/screen_qa |
| 8 | DiagramQG | 8,372图+19,475 Q | 教学图表+文 | dxzxy12138.github.io/diagramqg-home |
| 9 | UML-Class-Diagram-DS | 104,604 UML图 | UML类图 | github.com/NilsBaumgartner1994/UML-Class-Diagram-Dataset |
| 10 | MultiModalQA | 跨模态QA | 文+表+图 | arxiv.org/abs/2104.06039 |
| 11 | InfographicVQA | ~30,000图+QA | 信息图 | docvqa.org/datasets/infographicvqa |
| 12 | ChartQA | 9,600图+20,882 QA | 数据图表 | github.com/vis-nlp/ChartQA |
| 13 | DocVQA-2026 | 8域文档(含工程图纸) | 多域文档 | github.com/VLR-CVC/DocVQA2026 |
