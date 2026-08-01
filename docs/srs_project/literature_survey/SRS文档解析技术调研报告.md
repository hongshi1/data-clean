# 军用 SRS（GJB 438C-2021）文档解析与结构化技术调研报告

> 目标：将大量遵循 GJB 438C-2021、以 Word/PDF 形态存在、含大量内嵌表格（性能指标表 / 接口定义表 / 数据字典）的军用软件需求规格说明书（SRS），解析为统一归一化结构化文档，并抽取表格。本报告覆盖三个技术方向：①文档解析与版面分析 ②表格抽取与结构化 ③章节切分与文档结构化，并给出端到端 pipeline 选型建议。

---

## 0. 军用 SRS 场景的特殊约束（贯穿三个方向）

1. **来源以 Word 为主、PDF 为辅**：Word 具有原生结构（样式/段落/表格对象），优先走“结构化直抽”而非 OCR；PDF 走版面分析 + OCR。两条路径必须对齐到同一中间表示。
2. **中文为主、含专业术语**：英文预训练模型（LayoutLMv3、Nougat、Table Transformer）需配合中文 OCR 或微调；优先选中文原生强的工具链（PaddleOCR/MinerU）。
3. **表格高度结构化、含合并单元格 / 嵌套表头 / 无框线表**：性能指标表多为“参数名—指标值—约束”多级表头；接口表含合并单元格；数据字典为多列表。合并单元格处理是最大难点。
4. **章节遵循 GJB 438C-2021 七大块固定模板**：标题编号（如 `3.2.1`）规范、层级稳定，规则法强基线可行。
5. **安全保密 / 离线 / 国产化**：优先纯离线、可私有化部署、Apache/MIT/AGPL 等可控许可；慎用商用闭源 API（LlamaParse 等）。

---

## 方向 1：文档解析与版面分析（Document Parsing & Layout Analysis）

### 1.1 技术方案对比表

| 工具 / 方法 | 原理 | 中文支持 | 表格能力 | 开源 / 许可 | 推荐度（军用SRS） |
|---|---|---|---|---|---|
| **MinerU**（OpenDataLab） | 版面检测(DocLayout-YOLO)+公式检测(YOLOv8)+公式识别(UniMERNet)+OCR(PaddleOCR)+表格(StructEqTable) 流水线，工程化后处理 | ★★★★ 良好（配 PaddleOCR） | ★★★★ 较强（结构化输出 HTML/MD） | Apache-2.0（核心）；依赖 PyMuPDF/部分 AGPL | ★★★★★ |
| **DocLayout-YOLO** | YOLOv10 架构 + 多样合成数据 + Global-to-Local 自适应感知，版面元素检测 | ★★★★（微调数据含中文） | 仅检测表格区域，不识别结构 | AGPL-3.0 | ★★★★（作为检测器组件） |
| **LayoutLMv3** | 多模态 Transformer，文本+版面+图像统一掩码预训练，可做版面分类/抽取 | ★★ 英文为主（中文需 LayoutXLM 2104.08836 或微调） | 仅版面分类，不识别表格结构 | MIT | ★★★ |
| **PaddleOCR PP-Structure / PP-StructureV2** | 版面+表格+OCR 一体化流水线，含 11 类版面 | ★★★★★ 中文原生最强 | ★★★★ 表格识别含结构 | Apache-2.0 | ★★★★★ |
| **Unstructured.io** | 通用文档解析框架，可挂接多种后端（YOLOX/Tesseract/PaddleOCR） | ★★★ 依赖后端 | ★★★ 基础表格 | Apache-2.0 | ★★★ |
| **DocTR**（Mindee） | 端到端 OCR + 版面，不同后端（PyTorch/TensorFlow） | ★★★ 中文可用但非强项 | ★★ 仅文本，弱表格 | Apache-2.0 | ★★ |
| **Marker**（VikParuchuri） | Surya OCR + 版面，PDF→Markdown，速度快 | ★★★ 中文一般 | ★★★ 中等 | GPL-3.0 | ★★★ |
| **Nougat**（Meta） | Swin Transformer 端到端图像→Markdown，学术 PDF 专用 | ★ 弱（英文科技文献训练） | ★★ 学术表格一般 | Apache-2.0 | ★（不适用） |
| **GOT-OCR2.0** | 580M 统一端到端 OCR-2.0，公式/表格/图表全“字符化”，输出 markdown/tikz | ★★★★ 中文良好 | ★★★ 可输出表格 markdown | Apache-2.0 | ★★★★ |
| **DocLayNet** | 大规模人工标注版面数据集（11 类，80K 页），训练检测器基线 | ★★ 数据英文为主 | 提供表格/标题/列表等区域标签 | CC-BY-4.0（数据） | ★★★（作为数据/基线） |
| **DocOwl 系列 / mPLUG-DocOwl1.5** | 多模态大模型文档理解 | ★★★★ | ★★★ | Apache-2.0 | ★★★（大模型，重） |

### 1.2 关键方案详述与优缺点

**MinerU（arXiv 2409.18839, 2024）**
- 流水线：`DocLayout-YOLO`（版面）→ `YOLOv8`（公式检测）→ `UniMERNet`（公式识别，arXiv 2404.15254）→ `PaddleOCR`（文本）→ `StructEqTable`（表格）→ 阅读序排序与后处理。
- 优点：模块化、对多文档类型鲁棒、中文友好、社区活跃（9.8k★ PDF-Extract-Kit）、输出 Markdown+JSON、可私有化。
- 缺点：依赖 AGPL 组件（PyMuPDF）；对极复杂无框线表格结构仍会出错；公式/表格串行较慢。
- 适用：PDF 版面解析主引擎。

**DocLayout-YOLO（arXiv 2410.12628, 2024）**
- 优点：版面检测 SOTA、速度快、合成数据增强泛化、含中文标注。
- 缺点：只检测元素区域（title/text/table/figure/list/formula），不做表格结构、不做 OCR；AGPL。
- 适用：作为 MinerU/自研流水线的版面检测前端。

**LayoutLMv3（arXiv 2204.08387, ACM MM 2022）**
- 优点：多模态预训练，文本+图像联合，可做版面分类与 KIE；MIT 许可友好。
- 缺点：中文需 LayoutXLM / 自行微调；本质是分类/标注模型，需配套 OCR；表头等复杂结构弱。
- 适用：作为版面元素“角色分类”与 KIE（键值抽取）补充。

**PaddleOCR PP-Structure（arXiv 2009.09941 系列，PaddlePaddle）**
- 优点：中文 OCR 第一梯队；PP-Structure 一体化输出版面+表格 HTML；国产、Apache-2.0、部署成熟（含 C++/Serving）。
- 缺点：表格对超复杂合并/嵌套表头不如专用大模型；推理链路较长。
- 适用：Word 无文本层 PDF 的中文 OCR + 表格主路径，国产化首选。

**GOT-OCR2.0（arXiv 2409.01704, 2024）**
- 优点：统一端到端，文本/公式/表格/图表一站式输出 markdown；中文良好；轻量（580M）。
- 缺点：超长表格、密集合并单元格易截断/错位；可控性弱于流水线。
- 适用：作为轻量端到端备选，或对公式/图表辅助识别。

**Unstructured.io / Marker / DocTR / Nougat**
- Nougat 面向英文学术 PDF，对中文军标文档基本不适用，仅作为对比基线。Marker/Unstructured 适合快速 PDF→MD，但表格与中文精度不及 MinerU+PP-Structure。

### 1.3 针对军用 SRS 的推荐方案

**主路径：MinerU（版面=DocLayout-YOLO + OCR=PaddleOCR）作为 PDF 解析主引擎；Word 源文档走 python-docx 结构化直抽（不进 OCR）。**

理由：
1. 军用 SRS 多有 Word 源文件，python-docx 可直接拿到段落样式、编号、表格对象，**精度远高于任何 OCR**，应作为首选；PDF 仅作兜底。
2. PDF 兜底时，MinerU 流水线中文友好、模块可替换、可离线私有化，符合保密要求。
3. 版面检测用 DocLayout-YOLO（SOTA、快），中文 OCR 用 PaddleOCR（国产、中文最强），二者正是 MinerU 默认组合，工程闭环。
4. AGPL 依赖需在合规评估后使用；若严格禁 AGPL，可替换为 PP-Structure 全栈（Apache-2.0）作为纯国产替代。

---

## 方向 2：表格抽取与结构化（Table Extraction & Structure Recognition）

### 2.1 技术方案对比表

| 工具 / 方法 | 原理 | 中文支持 | 合并单元格 / 无框线 / 嵌套 | 开源 / 许可 | 推荐度（军用SRS） |
|---|---|---|---|---|---|
| **Word 原生表格直抽**（python-docx / docx2python） | 直接读取 OOXML 表格对象，行列/合并单元格原生保留 | ★★★★★（不经过 OCR） | ★★★★★ 合并单元格原生 | MIT | ★★★★★（有源文件时首选） |
| **Camelot** | PDF 表格抽取，lattice（线框）/stream（空白）两种模式 | ★★★★（直抽文本层） | ★★ 线框表好、无框线弱、嵌套弱 | MIT | ★★★ |
| **Tabula**（tabula-py） | 基于 Java Tabula，线框表检测 | ★★★★ | ★★ 同 Camelot | MIT | ★★★ |
| **Table Transformer (TATR)** | DETR-based，表格检测+结构识别，PubTables-1M 训练 | ★★（英文训练，需 OCR+微调） | ★★★ 合并较好、无框线中 | MIT | ★★★ |
| **PubTables-1M**（arXiv 2110.00061） | 100 万表大规模数据集 + canonicalization 解决过分割 | ★★（英文科学文献） | ★★★ | MIT | ★★★（数据/基线） |
| **PaddleOCR 表格识别**（PP-Structure table） | 端到端表格结构识别，输出 HTML | ★★★★★ | ★★★★ 合并/无框线较好 | Apache-2.0 | ★★★★★ |
| **StructEqTable**（InternVL2-1B） | 视觉大模型表格→LaTeX/HTML/Markdown | ★★★★ | ★★★★ | Apache-2.0（模型权重） | ★★★★ |
| **UniTable**（arXiv 2403.04822） | 自监督预训练统一框架，结构+内容+box 三任务统一 | ★★★（英文为主，可迁移） | ★★★★ SOTA | MIT | ★★★★ |
| **TableMaster**（PingAn/ICDAR2021） | 图像→HTML 序列，注意力机制 | ★★★ | ★★★ | Apache-2.0 | ★★★ |
| **LlamaParse** | 商用闭源，PDF→结构化（含表格） | ★★★ | ★★★★ | 闭源/付费 API | ★★（保密场景不推荐） |
| **GOT-OCR2.0 表格模式** | 端到端输出 markdown 表格 | ★★★★ | ★★★ | Apache-2.0 | ★★★ |

### 2.2 关键方案详述

**Word 原生直抽（首选）**
- 用 `python-docx` 遍历 `document.tables`，每个 `table` 的 `cell` 天然含合并信息（`tc` 的 `gridSpan`/`vMerge`），可还原为二维矩阵并标注合并区域。
- 优点：无损、零 OCR 误差、合并单元格精确、可区分嵌套表（cell 内嵌 table）。
- 缺点：仅适用 `.docx`；`.doc` 旧格式需先 `libreoffice --convert`；样式噪声（隐藏格、空行）需清洗。
- **对军用 SRS：性能指标表/接口表/数据字典在 Word 中多为真实表格对象，直抽是精度上限。**

**Camelot / Tabula（规则法 PDF 表格）**
- 优点：对**有明确线框**的 PDF 表格精度极高、速度快、零模型依赖、中文无损（直接取文本层）。
- 缺点：依赖线框；无框线表（stream 模式靠空白对齐）易错乱；合并单元格还原弱；扫描版 PDF 无文本层则失效。
- 适用：作为 PDF 有框线表格的**轻量首选**，与模型法互补。

**Table Transformer / PubTables-1M（arXiv 2110.00061, 2021）**
- 微软基于 DETR（arXiv 2005.12872, ECCV 2020）的表格检测 + 结构识别 + 功能分析三任务模型；PubTables-1M 提供 ~100 万表、解决过分割，是行业标准基线。
- 优点：检测+结构一体、合并单元格建模好、有现成权重（`microsoft/table-transformer`）。
- 缺点：英文科学文献训练，中文需配 PaddleOCR 做文本填充并微调；对无框线/密集表格仍有错位。
- 适用：PDF 扫描件表格结构识别基线。

**PaddleOCR 表格识别 / StructEqTable / UniTable（模型法）**
- **PaddleOCR 表格**：中文场景工程首选，输出 HTML，含合并。
- **StructEqTable**（InternVL2-1B，arXiv 2404.07995 系列）：视觉大模型，输出多格式，中文较好，是 MinerU 1.0 默认表格引擎。
- **UniTable**（arXiv 2403.04822, Georgia Tech, NeurIPS'23/AAAI'24 系列）：自监督预训练统一框架，结构+内容+box 三任务，多个大规模数据集 SOTA；MIT，可迁移中文。
- 这些是扫描件/无文本层 PDF 表格的主力。

**LlamaParse**：商用 API，效果好但数据出域、不可私有化，**军用保密场景排除**。

### 2.3 针对军用 SRS 的推荐方案

**分层表格抽取策略（精度优先、由易到难）：**

```
1) Word 源文件 (.docx)  → python-docx 原生直抽（合并单元格无损）  [主路径，覆盖大多数]
2) PDF 有文本层 + 有框线 → Camelot (lattice) 直抽                  [轻量高精]
3) PDF 扫描件 / 无框线 / 复杂合并 → PaddleOCR 表格识别 或 StructEqTable
4) 极复杂嵌套/表头兜底      → UniTable / Table Transformer + 人工校验
```

理由：
- 军用 SRS 表格多为 Word 原生表，**直抽即得结构化数据，没必要 OCR**，这是最大性价比点。
- PDF 路径按“有框线→Camelot、无框线/扫描→PaddleOCR/StructEqTable”分工，避免对简单表用重模型、对复杂表用弱规则。
- 中文与国产化双重约束下，PaddleOCR 表格 + StructEqTable 主导，UniTable 作为高精度兜底。

---

## 方向 3：章节切分与文档结构化（Section Splitting & Document Structuring）

### 3.1 方法对比（规则法 vs 模型法）

| 方法 | 原理 | 对 GJB 438C 模板适配 | 优点 | 缺点 | 推荐度 |
|---|---|---|---|---|---|
| **规则法（编号正则 + 标题样式）** | 用 `^\d+(\.\d+)*\s*[标题]` 匹配章节号，结合 Word heading 样式 / 字体特征 | ★★★★★ 模板固定 | 精确、可解释、零模型、可审计 | 对非标编号/排版扰动敏感 | ★★★★★（强基线） |
| **模板映射法（GJB 438C 七大块锚点）** | 预置七大块标题词典（功能需求/性能指标/接口定义/数据字典/运行环境/安全保密/验收准则），章节号↔语义块映射 | ★★★★★ | 直接对齐标准、可校验完整性 | 仅适用遵循标准的文档 | ★★★★★ |
| **版面模型法（LayoutLMv3/DocLayout-YOLO 角色分类）** | 检测 title/section-header 并分类 | ★★★ | 抗排版扰动、泛化 | 需标注微调、中文需调 | ★★★ |
| **层级文本分类（Hierarchical Text Classification）** | 对段落文本分类到章节层级 | ★★★ | 处理无编号段落 | 训练数据需求大 | ★★ |
| **大模型法（LLM/VLM 章节理解）** | 用 DocOwl/GPT 类模型直接给章节语义 | ★★★★ | 鲁棒、可处理变体 | 重、可解释性弱、保密受限 | ★★★（辅助） |

### 3.2 GJB 438C-2021 七大块结构化要点

GJB 438C 规定软件需求规格说明含固定章/节，典型映射：

| 七大语义块 | 典型章节号范围 | 关键内含表格 |
|---|---|---|
| 功能需求 | 3.x | 功能/接口需求表 |
| 性能指标 | 3.x / 4.x | **性能指标表** |
| 接口定义 | 5.x（外部/内部接口） | **接口定义表** |
| 数据字典 | 6.x / 数据要求 | **数据字典表** |
| 运行环境 | 7.x | 环境约束表 |
| 安全保密 | 8.x（安全性/保密性） | 安全要求表 |
| 验收准则 | 9.x / 合格性 | 验收项表 |

**切分思路**：
1. 用编号正则 + Word heading 样式建立“章/节/条目”三级树（`3 → 3.2 → 3.2.1`）。
2. 用 GJB 模板锚点词典把章节节点映射到七大语义块，做完整性校验（缺块告警）。
3. 每个语义块下的表格按“最近章节归属”挂载到对应节点（解决表格跨页/浮动）。
4. 模型法作补充：对无编号或编号异常的子标题，用 LayoutLMv3/DocLayout-YOLO 角色分类二次判别。

### 3.3 针对军用 SRS 的推荐方案

**规则法为主（编号正则 + GJB 模板锚点）+ 版面模型为辅（角色分类兜底）+ LLM 仅做异常复核。**

理由：
- GJB 438C 模板高度规范，编号体系稳定，**规则法即可达 95%+ 切分准确率**，且完全可审计（军用合规必需）。
- 模型法仅处理规则失效的边角（缺编号、扫描错字、跨文档模板漂移）。
- LLM 因保密与可解释性约束，仅用于离线抽检/复核，不进入主链路。

---

## 关键论文与资源引用汇总

| 方向 | 工作 | arXiv / 会议 | 年份 | 要点 |
|---|---|---|---|---|
| 1 | **MinerU** | arXiv:2409.18839 | 2024 | 开源高精度文档内容抽取流水线 |
| 1 | **DocLayout-YOLO** | arXiv:2410.12628 | 2024 | 合成数据+全局到局部感知的版面检测 SOTA |
| 1 | **LayoutLMv3** | arXiv:2204.08387 (ACM MM) | 2022 | 文本+图像统一掩码多模态预训练 |
| 1 | LayoutLM | arXiv:1912.13318 (KDD) | 2020 | 文本+版面预训练奠基 |
| 1 | LayoutLMv2 | arXiv:2012.14740 (ACM MM) | 2021 | 引入图像模态 |
| 1 | LayoutXLM | arXiv:2104.08836 | 2021 | 多语言（含中文）版面理解 |
| 1 | DiT | arXiv:2203.02378 (ACM MM) | 2022 | 文档图像自监督预训练 |
| 1 | **DocLayNet** | arXiv:2206.01062 (KDD) | 2022 | 80K 人工标注、11 类版面数据集 |
| 1 | DocBank | arXiv:2004.13538 | 2020 | 50K 自动标注版面数据 |
| 1 | PubLayNet | arXiv:1908.07836 | 2019 | PubMed 版面数据集 |
| 1 | **Nougat** | arXiv:2308.13418 | 2023 | 学术 PDF 端到端 OCR→Markdown（英文） |
| 1 | **GOT-OCR2.0** | arXiv:2409.01704 | 2024 | 统一端到端 OCR-2.0（文本/公式/表格/图表） |
| 1 | UniMERNet | arXiv:2404.15254 | 2024 | 真实场景公式识别 |
| 1 | Donut | arXiv:2111.15664 | 2021 | OCR-free 文档理解 |
| 1 | Pix2Struct | arXiv:2210.03347 (ICML) | 2023 | 截图解析预训练 |
| 2 | **PubTables-1M / Table Transformer** | arXiv:2110.00061 | 2021 | 100 万表数据集 + DETR 表格结构识别 |
| 2 | DETR | arXiv:2005.12872 (ECCV) | 2020 | 端到端目标检测 Transformer |
| 2 | Deformable DETR | arXiv:2010.04159 | 2020 | 可变形注意力加速收敛 |
| 2 | **UniTable** | arXiv:2403.04822 | 2024 | 自监督预训练统一表格识别框架 SOTA |
| 2 | TSR Early Convolutions | arXiv:2311.05565 (NeurIPS W) | 2023 | 表格结构 Transformer 早卷积 |
| 2 | SSP for TSR | arXiv:2402.15578 (AAAI W) | 2024 | 表格自监督预训练 |
| 2 | InternVL / InternVL2 | arXiv:2312.14238 / 2404.07995 | 2023-24 | StructEqTable 底座视觉大模型 |
| 2 | PP-OCR | arXiv:2009.09941 | 2020 | PaddleOCR 超轻量 OCR（中文强） |
| 3 | （GJB 438C-2021） | 国家军用标准 | 2021 | SRS 内容与格式规范（非论文） |
| 3 | Hierarchical Text Classification | 多篇综述 | — | 层级文本分类（章节语义） |

---

## 技术选型：PDF/Word SRS → 归一化结构化文档 Pipeline

### 推荐 pipeline 架构（双源对齐到统一 IR）

```
                ┌─────────────────────────── 输入层 ───────────────────────────┐
  SRS.docx ─────►│ A. Word 结构化直抽路径                                       │
  SRS.pdf  ─────►│ B. PDF 版面解析路径                                         │
                └─────────────────────────────────────────────────────────────┘
                          │                                        │
        【A】 python-docx │                                        │ 【B】 MinerU/PP-Structure
        - 段落/样式/编号  │                                        │ - DocLayout-YOLO 版面检测
        - 表格对象直抽    │                                        │ - PaddleOCR 中文 OCR
        - 图/公式占位     │                                        │ - StructEqTable/PaddleOCR 表格
                          ▼                                        ▼
                ┌──────────────────── 统一中间表示 (IR) ───────────────────────┐
                │  JSON 树: doc → section(章/节/条) → {paragraph|table|figure}  │
                │  table: 二维矩阵 + 合并单元格标注 + 表头层级 + 所属章节        │
                └─────────────────────────────────────────────────────────────┘
                          │
        【C】 章节切分与对齐层（规则为主 + 模型兜底）
        - 编号正则建章/节/条树
        - GJB 438C 七大块锚点映射 + 完整性校验
        - LayoutLMv3/DocLayout-YOLO 角色分类补缺编号
        - 表格按“最近章节”归属挂载
                          │
        【D】 后处理与归一化
        - 性能指标表 → (参数名,指标值,约束,单位) 结构化
        - 接口定义表 → (接口名,类型,方向,协议,数据项) 结构化
        - 数据字典   → (数据项,类型,长度,取值,含义) 结构化
        - 校验/去重/版本/水印清洗
                          ▼
              归一化结构化文档（JSON / Markdown / 入库）
```

### 分层组件选型清单

| 层 | 首选 | 备选 | 理由 |
|---|---|---|---|
| A. Word 直抽 | `python-docx` + `docx2python` | `libreoffice` 转换 `.doc`→`.docx` | 原生表格/合并无损，精度上限 |
| B1. PDF 版面检测 | DocLayout-YOLO | LayoutLMv3（角色分类） | SOTA、快、含中文；MinerU 默认 |
| B2. PDF 中文 OCR | PaddleOCR | GOT-OCR2.0 | 国产、中文最强、Apache |
| B3. PDF 公式 | UniMERNet | GOT-OCR2.0 | 真实场景公式 SOTA |
| B4. PDF 表格 | PaddleOCR 表格 + StructEqTable | Camelot(有框线)/UniTable(兜底) | 中文+合并好；Camelot 处理线框表零成本 |
| C. 章节切分 | 规则正则 + GJB 模板锚点 | LayoutLMv3 角色分类 / LLM 复核 | 模板固定，规则法可审计达 95%+ |
| D. 归一化 | 自研 Schema 映射 | — | 对齐 GJB 七大块与三类核心表 |
| 编排 | Python pipeline / Airflow | — | 离线批处理 |

### 实施优先级建议（落地路线）

1. **P0 先吃 Word 源**：python-docx 直抽 + GJB 规则切分，覆盖 80%+ 文档，快速见效、精度最高。
2. **P1 PDF 有框线表**：Camelot + 规则切分，覆盖线框 PDF。
3. **P2 PDF 扫描/复杂表**：MinerU（DocLayout-YOLO + PaddleOCR + StructEqTable）全栈，覆盖扫描件与无框线表。
4. **P3 兜底增强**：UniTable/Table Transformer 处理失败案例 + 人工校验回流，逐步微调中文表格模型。
5. **P4 质量闭环**：建立“IR→原始页”回溯（bbox/页码标注），人工抽检反馈微调。

### 风险与注意事项

- **AGPL 合规**：DocLayout-YOLO/PyMuPDF 为 AGPL-3.0，军用封闭部署需法务评估；纯国产替代用 PP-Structure 全栈（Apache-2.0）。
- **保密性**：禁用任何外发 API（LlamaParse/在线 OCR）；全部模型本地推理。
- **表格结构变异**：性能指标表的多级表头、接口表的合并单元格是最大失分点，需在 D 层做专门 schema 校验（行/列完整性、表头跨度一致性）。
- **`.doc` 旧格式**：先统一转 `.docx`（LibreOffice headless），避免直接解析二进制 `.doc`。
- **可审计性**：规则法产出可追溯的切分依据（章节号/锚点匹配证据），满足军用文档治理审计要求；模型法需保留置信度与人工复核记录。

---

## 结论速览

- **方向 1（解析/版面）**：Word 走 python-docx 直抽；PDF 走 **MinerU（DocLayout-YOLO + PaddleOCR）**，国产替代用 PP-Structure 全栈。
- **方向 2（表格）**：**Word 原生直抽 > Camelot(有框线) > PaddleOCR/StructEqTable(扫描/无框线) > UniTable(兜底)**，分层精度优先。
- **方向 3（章节）**：**规则法（编号正则 + GJB 七大块锚点）为主，版面模型兜底**，LLM 仅离线复核。
- **Pipeline**：双源（Word/PDF）→ 统一 IR（章节树+结构化表）→ GJB 语义块映射 → 归一化入库，优先吃 Word 红利，PDF 按 P0→P4 渐进。
