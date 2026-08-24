# Visio/Office图形对象解析先例调研 —— 我们是孤例还是有先驱？

> 调研日期：2026-08-24 | 检索渠道：arXiv API（元数据级，条目均经API摘要核实）+ OpenAlex API + DBLP API + GitHub/PyPI/微软官方文档直接抓取核实；DDG/Bing/Mojeek均遭反爬，已用一手来源替代
> 用途：为"从.doc的OLE嵌入对象中提取Visio XML源（page*.xml的Shape/Cell/Connect）作为流程图/用例图100%保真结构锚点"这一路线寻找学术与工业先例，确认novelty定位、必引文献与可复用工具
> 关系：与《diagram_extraction_technology_spectrum.md》互补——该报告覆盖提取方法谱系（检测式/VLM/OCR+几何），本报告回答"**源码直读这条路线本身有没有人做过**"；VLM可信度证据见《uml_diagram_understanding_survey.md》

---

## 0. TL;DR

| 问题 | 结论 |
|------|------|
| "Visio XML作下游任务结构化数据源"有无学术先例？ | **无直接先例**（arXiv/DBLP/OpenAlex三重检索零命中，见§1.3）。最近邻是Shiinoki et al. 2025（Office源文件形状元数据→LLM，arXiv:2502.04389），但载体是xlsx/pptx/docx的DrawingML，非Visio |
| 邻近领域最接近的先驱？ | ①Shiinoki 2025；②ChemScraper（IJDAR 2024，born-digital PDF矢量指令直读，98.4%）；③FloorPlanCAD/SymPoint系（CAD矢量原生解析）；④SketchGraphs（CAD源文件→约束图） |
| 工程上是否孤例？ | **远非孤例**：微软官方文档把"读Visio工作流图执行业务逻辑"列为vsdx格式的开发者场景；python-vsdx/POI XDGF/libvisio/Aspose均有成型解析能力 |
| 我们的定位 | 不是新算法，而是**首个（据检索所见）把成熟工程能力学术化为研究方法**：嵌入源码回收→保真锚点→一致性校验检测对象。novelty应写成"锚点用法+覆盖度量+增益量化"，不可写"首个Visio解析"（会被工具库反驳） |

---

## 1. 方向1：Visio文件格式解析

### 1.1 格式与规范（事实基础，全部一手核实）

| 条目 | 出处 | 要点 |
|------|------|------|
| [MS-VSDX]: Visio Graphics Service VSDX File Format | MS Open Specifications: learn.microsoft.com/en-us/openspecs/sharepoint_protocols/ms-vsdx/ | vsdx权威规范；2012年v0.1起持续修订至v11.3（2025-11），归入SharePoint协议族，提供PDF下载 |
| Introduction to the Visio file format (.vsdx) | MS Learn: office/client-developer/visio/introduction-to-the-visio-file-formatvsdx | vsdx=OPC打包的ZIP+XML，取代.vsd（二进制）与.vdx（XML）；**ShapeSheet全部参数编码为Cell/Row/Section元素（N属性区分，如`<Cell N="PinX" U="IN" V="2"/>`）**；官方开发者场景原文："build a tool that reads a Visio workflow diagram and then executes its own business logic based upon that workflow"——**微软自己背书"Visio文件即结构化数据源"** |
| 标准化状态 | 同上 + ECMA-376体系 | 打包层复用OPC（ECMA-376-2/ISO 29500-2），但**Visio绘图schema不是ECMA-376/ISO 29500组成部分**（后者仅Word/Excel/PPT），只由微软开放规范文档化——回答"vsdx算不算OOXML标准家族"：容器算、内容不算 |
| .vdx（DatadiagramML） | 同上 | Visio 2002-2010的XML格式（单文件XML），schema与vsdx同源，Windows元素等直接沿用 |
| LoC FDD fdd000021 | loc.gov/preservation/digital/formats/fdd/fdd000021.shtml | 美国国会图书馆格式登记：VSDX为Visio 2013起原生格式 |

### 1.2 解析库（工程现状）

| 库 | 出处 | 机制 | 与我们的关系 |
|----|------|------|------------|
| python-vsdx（PyPI: vsdx） | github.com/dave-howard/vsdx，BSD-3，v0.6.1（2026-01），103星 | 纯Python解包OPC+对象模型：VisioFile/Page/Shape，暴露child_shapes、**Connect对象与Page.get_connectors_between()**、master形状继承、Shape Data属性 | **首选复用候选**：Connect封装与我们的Shape/Cell/Connect直读可互为校验；局限：只吃.vsdx/.vsdm，不处理OLE嵌入与VSD二进制 |
| libvisio | DLP项目： github.com/LibreOffice/libvisio，MPL 2.0 | C++读取+转换；二进制.vsd/.vss全版本为**逆向工程**成果（GSoC 2011起步，早于任何官方规范），后按微软文档增补vsdx；LibreOffice Draw的Visio导入过滤器 | 唯一能兜底**旧版VSD二进制嵌入**的开源实现；经librevenge输出SVG |
| Apache POI HDGF/XDGF/POIFS | poi.apache.org/components/ | HDGF=VSD二进制（低层读+简单文本抽取，scratchpad）；XDGF=vsdx（poi-ooxml，"slightly more support than HDGF"）；POIFS=纯Java CFB读写 | Java生态等价物；POIFS即OLE解包层组件 |
| Aspose.Diagram | pypi.org/project/aspose-diagram/（多语言） | 商业闭源：Visio创建/操作/转换/渲染全家桶 | 工业级能力参照系（付费，不可复现） |
| docx4j | github.com/plutext/docx4j | JAXB的docx/pptx/xlsx OOXML库 | **不支持vsdx**（README明确仅docx/pptx/xlsx）——排除该候选 |
| libvisio-ng / visio_bridge / visiopy | PyPI/GitHub（2025-2026小型项目） | 各自的Python解析尝试（形状/页面/元数据抽取，部分支持VSD） | 佐证"Visio解析库"生态存在但小众、均无学术产出 |

### 1.3 学术检索证据（负结果，novelty支撑）

- arXiv API `all:"Microsoft Visio"`：**0命中**；`abs:Visio`共53个命中，全部是visio-linguistic/visio-haptic等同形词噪声（唯一真提到Visio的是2017年一篇用Visio 2007画界面图的处方系统论文，与解析无关）
- DBLP：无Visio格式解析相关论文（"Visio*"命中5.8万条均为vision噪声）
- OpenAlex全文检索"Visio vsdx diagram parsing file format"：仅3个命中且均非Visio解析（P&ID生成copilot、BPM框架、§3.1的XML-LLM论文）
- **结论**：Visio格式解析在学术上是无人区；工程界解决了"能不能解析"，无人研究"解析结果当结构化锚点/金标准/评测对象"
- 证据局限（写作时须声明）：arXiv API为元数据检索不覆盖全文，DBLP/OpenAlex对小众venue收录不全；表述用"经arXiv/DBLP/OpenAlex检索未见"，不用"不存在"

---

## 2. 方向2：Office嵌入对象提取（OLE/数字取证视角）

### 2.1 规范传统（我们提取层的"理论依据"全是现成的）

| 条目 | 出处 | 要点 |
|------|------|------|
| [MS-CFB] Compound File Binary File Format | MS Open Specs: learn.microsoft.com/en-us/openspecs/windows_protocols/ms-cfb/ | OLE2复合文档的二进制结构规范（扇区/FAT/目录项/流-存储树）；.doc/.xls/.ppt及一切OLE嵌入对象的容器 |
| [MS-OLEDS] | learn.microsoft.com/en-us/openspecs/windows_protocols/ms-oleds/ | OLE嵌入对象持久化结构：CompObj/Ole流+原生数据流（CONTENTS，或Ole10Native"Package"流）——正是我们从.doc里挖出的东西 |
| [MS-DOC] | learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/ | 官方定义"Word二进制格式即[MS-CFB]复合文档"→.doc内嵌Visio=CFB套CFB/ZIP的多层嵌套；docx侧则以word/embeddings/oleObjectN.bin部件承载（oledump文档中有真实样例：oleObject4.bin内的\x01Ole10Native流） |

### 2.2 取证/安全工具链（"嵌入对象提取"是DFIR成熟问题）

| 工具 | 出处 | 机制 | 与我们的关系 |
|------|------|------|------------|
| olefile | decalage.info / PyPI: olefile | Python CFB解析器（目录/流遍历、元数据），oletools的底座 | OLE解包层的直接依赖（大概率已在用） |
| oletools | PyPI: oletools v0.60.2（Philippe Lagadec） | **oleobj：专司"从OLE文件提取嵌入对象"**；另有olevba/rtfobj/oleid/olebrowse/oledir/olemap；被CAPE、Cuckoo、Cortex XSOAR、REMnux等数十个平台集成 | 嵌入对象定位与转储的工业标准；与我们的差异仅在目的（取证找payload vs 回收图结构） |
| oledump.py | Didier Stevens: blog.didierstevens.com/programs/oledump-py/ | 流级分析+YARA+插件体系，可定位嵌入对象流并管道式转储 | 流探查利器；其社区讨论直接展示embeddings/*.bin与Ole10Native的实战操作 |
| Apache POI POIFS | poi.apache.org（见§1.2） | 纯Java CFB读写+嵌入文档支持 | Java路线备选 |

### 2.3 学术侧（薄弱但存在）

- Casino et al., "Analysis and Correlation of Visual Evidence in Campaigns of Malicious Office Documents"（arXiv:2103.16143, 2021）：恶意Office文档分析学术线代表——关注视觉伪造线索与campaign关联，不做嵌入对象结构化
- Godiah, "Forensic analysis of office open XML spreadsheets"（2017，OpenAlex收录）：OOXML取证个案
- 判断：**"嵌入对象提取"在学术上是工具/实践知识，不构成研究问题**；没有论文把"嵌入图形对象源码回收"用于文档理解——我们借用取证工具链做语义提取，方向上是新的

---

## 3. 方向3：图表的矢量/源码级解析（不限Visio）

### 3.1 代表工作

| 工作 | 出处 | 机制 | 与我们场景的关系 |
|------|------|------|----------------|
| **ChemScraper** | Shah et al., IJDAR 27(3):395-414, 2024（arXiv:2311.12161），RIT | 直读born-digital PDF图形指令（字符/线/多边形的显式坐标，前端为同组Symbol Scraper，Shah et al. ICDAR 2021）→图变换→分子图/SMILES；USPTO基准98.4%，无需GPU/OCR/矢量化；再用直读结果自动标注光栅图、训练神经识别器 | **方法论同构的旗舰先例**："源指令直读→图结构"替代"图像识别"；且同样把直读结果用作训练数据生产者——与我们"Visio XML做silver标注机"同源 |
| pdfplumber | github.com/jsvine/pdfplumber（10.7k星），基于pdfminer.six | 暴露PDF每个char/line/rect/curve对象的坐标与属性；表格检测思路源自Nurminen硕士论文/Tabula | "矢量对象级读取"的工具化大众版；表格域已成事实标准 |
| Camelot | camelot-dev/camelot（Vinayak Mehta，MIT） | lattice（线框）/stream（空白）/network/ml四种表格解析；engine="combined"融合PDF原生矢量线与OpenCV检测 | 同上，证明该范式的工业成熟度 |
| VectorGraphNET | Carrara et al., arXiv:2410.01336 | PDF→SVG→几何特征图→图注意力网络做技术图线级语义分割，FloorPlanCAD上SOTA（wF1） | PDF矢量+GNN的桥梁；证明"源码级图→图神经网络"在AEC领域成立 |
| GenAI-DrawIO-Creator | Yu & Jiang, arXiv:2601.05162 | LLM（Claude 3.7）生成/操纵draw.io结构化XML（流程图/网络架构），输入为自然语言/代码/图像 | drawio XML作LLM结构化媒介（**生成方向**）；与我们的提取方向互为逆问题 |
| SAGE | Sivertsen et al., arXiv:2607.01102 | 自然语言编辑draw.io/Mermaid图：图→可编辑表示→结构化编辑意图→**XML校验与修复** | 其XML校验修复模块对解析鲁棒性设计有直接参考价值 |
| Diagram-MMU | Bo et al., arXiv:2608.12262 | 3.7k图表多模态基准：diagram-to-code解析/编辑+QA；结论：模型"能推理图表但难以解析编辑图表" | 源码直读路线的价值论据（解析瓶颈的实证） |
| P&ID copilot | Gowaikar et al., arXiv:2412.12898（AAAI'25 workshop） | 多步agentic工作流从自然语言生成工程P&ID图 | 工程图XML生成线的又一例（全文提及vsdx生态） |
| DeepSVG | Carlier et al., NeurIPS 2020（arXiv:2007.11301） | SVG图标层次化生成网络+SVG操作库 | SVG深度表示学习代表（生成侧）；解析侧即我们的问题 |
| **XML-driven LLM** | Shiinoki et al., arXiv:2502.04389, 2025 | **从xlsx（及pptx/docx）源文件抽取图表形状元数据→文本→LLM**，回答业务结构问题，胜过VLM基线；开源galirage/spreadsheet-intelligence | **最近邻先例**：证明"Office源文件→图表结构→LLM"可行且优于视觉路线；但载体是表格/DrawingML形状bbox，未涉及Visio XML、OLE嵌入与流程图拓扑 |

### 3.2 对照线：图像based图表解析（主流，输在保真上）

- FigureSeer（Siegel & Horvitz, ECCV 2016，allenai/figureseer）：论文结果图端到端解析（定位/分类/子图结构+CNN相似度的图推理）
- A Diagram Is Worth A Dozen Images（Kembhavi et al., ECCV 2016，arXiv:1603.07396）：定义Diagram Parse Graph与图表句法解析任务，5000+图全标注——"diagram parsing"一词的学术源头
- 该线输入永远是光栅图像/渲染PDF，与源码直读路线正交；VLM/检测式方法谱系详见《diagram_extraction_technology_spectrum.md》（含FlowExtract节点F1 98.8% vs 最优VLM 34.0%的实证）

---

## 4. 方向4：CAD/工程图源码级理解（"矢量源直读"传统最深的领域）

| 工作 | 出处 | 机制 | 与我们的关系 |
|------|------|------|------------|
| FloorPlanCAD | Fan et al., ICCV 2021（arXiv:2105.07147） | 1万+真实**矢量格式**CAD平面图数据集（30类细粒度标注），提出panoptic symbol spotting任务，CNN+GCN基线 | **矢量原生数据集范本**：CAD天然矢量→标注免费且精确，与"Visio XML免费金标准"同构 |
| GAT-CADNet | Zheng et al., arXiv:2201.00625 | 图注意力网络：原语为顶点，实例 spotting=子图检测（邻接矩阵预测） | 矢量图→GNN代表作 |
| SymPoint | Liu et al., ICLR 2024（arXiv:2401.10556） | 原语采样为2D点集→点云Transformer，FloorPlanCAD上PQ超GAT-CADNet 9.6点 | 该线持续演进的证据（另有CADSpotting+LS-CAD、VecFormer、ArchCAD-400K、TextCAD，2024-2026密集产出） |
| SketchGraphs | Seff et al., 2020（arXiv:2007.08506） | 从1500万真实CAD模型源提取草图**约束图**（顶点=几何原语，边=设计者施加的几何约束） | 与我们最像的数据构造：**从创作工具源文件直接获得图结构+语义**，零标注成本 |
| Deep Vectorization of Technical Drawings | Egiazarian et al., NeurIPS 2020（arXiv:2003.05471） | 光栅工程图→矢量原语（清洗+transformer+优化） | 逆问题参照：没有源时恢复矢量代价多大——反衬源码直读的价值 |
| DXF/DWG工程传统 | Autodesk DXF Reference（开放文档）；libdxfrw/LibreDWG（开源）；ODA（商业） | CAD界40年"源文件即数据"传统：DXF为公开格式，解析器遍地 | 领域范式先例：矢量源直读可支撑一个研究社区；我们将其移植到SRS文档域 |

---

## 5. 核心问题回答

### a. "Visio XML作下游任务结构化数据源"有没有先例？

**学术上无直接先例；工程上有官方背书的先例；间接学术先例到2024-2025年才出现。**

- 直接先例：三库零命中（§1.3）。注意证据等级：arXiv API为元数据级检索，ICDAR/DI等venue旧文可能漏检；表述用"经arXiv/DBLP/OpenAlex检索未见"。
- 间接先例三层：
  1. **微软官方**（MS Learn开发者文档）把"读Visio工作流图执行业务逻辑"列为vsdx格式的设计目标场景——工程合法性无懈可击，且说明"没人做"的原因是它被当作平凡的工程任务而非研究问题；
  2. **Shiinoki et al. 2025**把同类思路做成论文（Office源文件形状元数据→LLM），证明该方向的可发表性；但差异明确：载体（DrawingML形状bbox vs Visio完整ShapeSheet+Connect拓扑）、深度（形状清单 vs 参数级+连接级结构）、用途（业务问答 vs 需求一致性校验锚点）；
  3. **ChemScraper 2024**证明"born-digital矢量指令直读"在另一格式（PDF）与领域（化学）可发期刊——我们相当于该范式在"Office嵌入对象+软件工程图"上的首例。
- **novelty写法建议**：不宣称"首个解析Visio的方法"（python-vsdx/POI/libvisio都是现成反例）；宣称"**首个（据我们所知）将Office文档中嵌入的图表源码回收为需求一致性校验的保真锚点，并系统量化其覆盖率与对检测/评测管线的增益**"——锚点用法、覆盖度量、增益实验才是贡献。

### b. 邻近领域最接近的先驱（必引清单）

1. **Shiinoki et al. 2025**（arXiv:2502.04389）——最近邻，相关工作首段必引并明确差异
2. **ChemScraper**（Shah et al., IJDAR 2024）——矢量指令直读的方法论同构先例
3. **FloorPlanCAD**（Fan et al., ICCV 2021）+ **SymPoint**（ICLR 2024）——矢量原生解析传统的旗帜
4. **SketchGraphs**（Seff et al., 2020）——"创作工具源文件→图数据集"的构造范式
5. **Kembhavi et al. ECCV 2016** + **FigureSeer**（ECCV 2016）——diagram parsing任务定义与图像线对照
6. **GenAI-DrawIO-Creator / SAGE**（2026）——图表XML与LLM交互的新兴线（逆问题）
7. 工程与规范基础（脚注/工程相关工作）：[MS-VSDX]、MS Learn Visio file format reference、oletools/oleobj、python-vsdx、libvisio、Apache POI XDGF

### c. 现成可用的工具（工程价值，全部即插即用）

- **OLE解包层**（.doc→嵌入对象字节流）：olefile（CFB遍历）；oletools的oleobj（嵌入对象转储，pip即装）；oledump.py（流级探查，定位CONTENTS/Ole10Native）
- **Visio解析层**（vsdx→结构）：python-vsdx（首选：Python对象模型、Connect关系直查）；Apache POI XDGF（Java备选）；libvisio（遇VSD二进制嵌入的兜底，可转SVG）；Aspose.Diagram（商业兜底，渲染保真）
- **对照验证层**：渲染PNG后跑检测式pipeline（见《diagram_extraction_technology_spectrum.md》），与XML锚点对齐以量化"源码直读增益"——可直接作为论文实验设计
- 风险提示：①嵌入对象可能是旧版VSD二进制（无page*.xml），需libvisio/HDGF路径兜底并统计其在16份数据集中的占比；②python-vsdx对master页继承的连接覆盖不完整时，回退原始XML直读；③vsdx坐标Cell默认单位英寸（U="IN"），与渲染像素对齐需显式DPI假设

---

## 6. 我们在版图上的坐标（一图收束）

```
"源码可直读"的图表载体谱系（保真度从参数级到形状级）：
  CAD源文件约束图(SketchGraphs) ──┐
  CAD矢量原语(FloorPlanCAD/SymPoint) ──┤
  PDF矢量指令(ChemScraper/VectorGraphNET) ──┼── 参数级保真：坐标/连接/约束齐全
  SVG(DeepSVG) ──┤
  drawio XML(GenAI-DrawIO/SAGE) ──┤
  Office DrawingML(Shiinoki) ──┘ 形状级保真：bbox+文本
  ▲ Visio XML(我们)：OLE嵌入回收 + ShapeSheet全参数库 + Connect显式拓扑
    —— 唯一同时具备"嵌入态回收路径/参数级语义/连接级拓扑"三重结构的载体，
       且从未被作为研究对象的那个空白格
```

一句话：**工具链每层都有人修过路（微软规范/取证工具/解析库），但从没有人把整条路走到"需求一致性校验"这个终点——我们是路径的组合者与首个目的地到达者，不是筑路者。**
