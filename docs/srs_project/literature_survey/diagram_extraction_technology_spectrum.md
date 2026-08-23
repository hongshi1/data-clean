# 多模态图表结构提取技术谱系 —— Visio XML之外的完整方法版图

> 调研日期：2026-08 | 检索渠道：arXiv API（论文均经摘要核实）+ GitHub仓库核实 + 工具文档
> 用途：为SRS项目"流程图/用例图结构提取"提供Visio XML直读之外的全部备选与互补路线，并给出多通道融合架构与归一化方案
> 关系：与《uml_diagram_understanding_survey.md》（三通道互校的学术依据）和《cross_modal_consistency_survey.md》（跨模态对齐与评测）互补——本报告聚焦**结构提取的方法版图**与**融合工程**，前两份聚焦VLM可信度与一致性检测评测
> 重要数据点：FlowExtract实测 节点F1 98.8% vs 最优VLM 34.0%、边F1 66.7% vs VLM 10.7%（工业ISO流程图，APMS 2026投稿，GitHub开源）

---

## 0. TL;DR 速览

| 方向 | 一句话原理 | 代表工作 | 节点/边精度预期 | 与Visio XML关系 | 实现复杂度 |
|------|-----------|---------|----------------|----------------|-----------|
| 1 检测式Pipeline | YOLO检测节点+OCR取文字+几何追踪边 | FlowExtract (2604.06770) | 节点F1≈98%，边F1≈67%（同域数据） | **互补+可被Visio反向训练**（silver标签） | 中（标注~100图+训练1天GPU） |
| 2 VLM端到端 | 大模型直接看图输出结构化JSON/DOT | EdgeFlow (2605.27332), FloCA (2602.14035) | 节点F1 30-70%，边F1 10-40%（域内实证差异大） | 互补（覆盖100%图）+需被验证 | 低（纯API调用） |
| 3 OCR+几何推理 | 纯OCR+Hough/形态学恢复连接 | FlowExtract的边模块、经典图形学文档分析 | 节点文字高、边方向低（交叉/折线脆弱） | 兜底通道+独立验证源 | 低-中（零训练，纯OpenCV） |
| 4 图表专用模型 | 图像→文本seq2seq预训练模型 | Pix2Struct (2210.03347), Donut (2111.15664), DePlot (2212.10505) | 面向数据图表，拓扑图需自行微调 | 无直接关系（技术储备） | 中-高（微调需数据+GPU） |
| 5 多源融合 | Dawid-Skene/truth discovery/加权投票 | 复杂标注在线聚合 (2401.15116) | 决定整体上限 | **Visio=锚点+仲裁者** | 中（仲裁逻辑~500行） |
| 6 图匹配 | VF2同构/GED编辑距离/二部匹配 | networkx内置全套 | 结构diff→不一致信号 | Visio图与正文比对的核心工具 | 低（现成库） |
| 7 端到端学习 | CLIP式对比/三模态attention | ColPali (2407.01449), LayoutLM系 | 16份文档无法支撑，仅轻量对齐头可行 | 无直接关系 | 高（数据量瓶颈） |

**三条核心判断**：
1. **学术界的方向已经收敛**：2024-2026年的论文几乎一致证明——VLM对拓扑图（流程图/用例图/架构图）的**边恢复能力是系统性短板**（probing证据：边信息在视觉编码器中线性不可分，2603.02865），而**检测式pipeline在同域数据上节点F1可达98%+**（FlowExtract）。VLM的正确用法是"感知语义+生成候选"，不是"拓扑权威"。
2. **Visio XML的独特价值被低估了**：它不仅是金标准，还可以是（a）检测模型的**自动标注机**（silver labels，省掉全部人工标注）、（b）VLM输出的**验证锚点**、（c）融合层的**仲裁tiebreaker**。一条数据三条用途。
3. **融合的关键不是投票而是对齐**：四个通道输出格式完全不同（XML坐标/Mermaid文本/bbox+OCR/线段端点），核心工程问题是**跨通道实体对齐（entity resolution）+ 统一schema（UDG）+ 带provenance的逐元素置信度**，投票只是最后一步。

---

## 1. 全景图：技术谱系定位

```
                        语义深度 →
  ┌────────────────────────────────────────────────────────────┐
  │  端到端学习(方向7)          VLM(方向2)      专用模型(方向4)   │
  │  CLIP对比/三模态attention   GPT-4o/Qwen-VL  Pix2Struct系    │
  │  (需要海量数据)             (零训练,API)    (需微调)         │
  │                                                              │
  │            ▲ 通用性高、精度不可控、无坐标                      │
  │            │                                                 │
  │  ──────────┼──────────────────────────────────────────      │
  │            │                                                 │
  │            ▼ 专用性高、精度可测、有坐标                        │
  │                                                              │
  │  born-digital直读           检测式(方向1)     OCR+几何(方向3)  │
  │  Visio XML / drawio XML    YOLO+OCR+追踪    PaddleOCR+Hough  │
  │  (精度≈100%,覆盖受限)      (需标注训练)     (零训练,脆弱)     │
  └────────────────────────────────────────────────────────────┘
                        工程确定性 →

  融合层(方向5): 多通道对齐 → 分歧检测 → 仲裁 → 统一图(UDG)
  应用层(方向6): UDG vs 正文步骤/表格 → 图匹配/GED → 不一致性信号(方向B)
```

选择逻辑：**覆盖率与精度的乘积**。Visio XML对"有嵌入源的图"精度≈100%但覆盖率受限于文档嵌入方式；VLM覆盖100%但边拓扑不可信；检测式两者居中且**可用Visio XML自动训练**。任何单一通道都不足以支撑一致性校验的检测对象构建——这直接论证了多通道融合的必要性。

---

## 2. 方向1：检测式Pipeline（Detection-based）

### 2.1 核心方法描述（技术原理）

三段式架构，每段独立可测：

```
PNG图 ──► [Stage 1: 元素检测] ──► 节点bbox+类别(矩形/菱形/椭圆/箭头)
       └► [Stage 2: OCR]     ──► 节点内文字 + 文字bbox
              │
              ▼
       [Stage 3: 连接恢复]
         3a. 箭头头部定位 + 朝向分类 → 得到有向边的"终点端"
         3b. 从箭头尾部反向沿线追踪（线段/折线段拼接）
         3c. 追踪终止于某节点bbox → 该节点即"源节点"
         3d. (src, dst) 对 + 中间文字标签(如"是/否") = 完整有向边
```

关键子问题的技术选择：

| 子问题 | 技术选项 | 说明 |
|--------|---------|------|
| 节点检测 | YOLOv8/v11单阶段 / Detectron2(R-CNN系) / RT-DETR | 流程图节点是大目标、类别少（5-10类），YOLOv8s足够；**实例分割**(Mask R-CNN)对重叠/异形节点更稳 |
| 箭头检测 | 单独训练"箭头"类 + 箭头头部小目标检测 | FlowExtract的创新点：检测箭头并分析**箭头朝向**（头部/尾部几何特征），再反向追踪 |
| 线段提取 | Hough变换(LSD变体) / 形态学细化+骨架化 / Douglas-Peucker折线简化 | 流程图边多为正交折线，Hough对直线段有效；曲线边（用例图泛化箭头）需骨架化 |
| 线拼接 | 端点距离贪心拼接 / 共线检测 | 折线由多段组成，需拼成长路径 |
| 端点吸附 | 线端点→最近节点bbox贪心 / 匈牙利匹配 | 距离阈值调参是精度敏感点 |
| 文字关联 | OCR bbox落在节点bbox内 → 归属 | IoU或中心点包含判定 |

**为什么它比VLM强**（FlowExtract的实证，同域ISO 5807流程图）：
- 节点检测 F1 = 98.8%（最优VLM仅34.0%）
- 边检测 F1 = 66.7%（最优VLM仅10.7%），边Precision = 85.5%
- 设计哲学：**高precision优先于recall**，为HITL（人机协同校验）提供可靠骨架，人只补完整性、不纠正幻觉

### 2.2 代表性工作/工具

| 工作 | 出处 | 要点 |
|------|------|------|
| **FlowExtract** | arXiv:2604.06770，APMS 2026投稿，GitHub: guille-gil/FlowExtract (MIT) | 本方向当前最佳参照系：YOLOv8s+EasyOCR+Hough追踪，数据见上；代码含完整pipeline/训练/评测脚本 |
| **Arrow-Guided VLM** | arXiv:2505.07864 | 检测与VLM的混合形态：7阶段pipeline（箭头感知的节点/箭头端点检测→OCR→构造结构化prompt喂给VLM），把检测结果作为VLM的"视觉脚手架"，准确率显著提升——检测式与VLM不是对立而是可组合 |
| **Symbol detection with Faster R-CNN** | arXiv:1712.04833 | 在线手写图形符号检测的早期系统评测，证明Faster R-CNN可作通用符号检测器 |
| **Symbol as Points** | arXiv:2401.10556 | CAD矢量图的panoptic symbol spotting，点云表示+局部连接——对"边由几何基元组成"的矢量场景适用（SRS图是栅格化的，仅思想借鉴） |
| **GAT-CADNet / FloorPlanCAD** | arXiv:2201.00625 / 2105.07147 | 图注意力网络做符号实例分割，CAD大规模数据集 |
| 工具链 | ultralytics YOLOv8/v11, Detectron2, MMDetection, PaddleDetection; 标注: Label Studio/CVAT/X-AnyLabeling | 全部成熟开源；YOLOv8单卡训练万级实例仅需小时级 |

前置工作也值得注意：同一团队的 arXiv:2601.22754 先用VLM（两种prompt策略）做工业排障指南抽取，发现model-specific的布局敏感性/语义鲁棒性权衡，才转向检测式——这个"从VLM退回检测"的研究路径本身就是证据。

### 2.3 在本项目中的适用性

- **SRS流程图**：GJB文档流程图 = 标准矩形/菱形/圆角矩形 + 正交折线箭头 + "是/否"标签，与FlowExtract的ISO 5807域**高度同构**。可直接复用其pipeline结构（节点类改为：start/end/process/decision/io，5类）。精度预期：节点F1 >95%（-born-digital渲染清晰、无扫描噪声，比工业PDF更友好），边F1 60-75%（交叉线少的图更高）。
- **UML用例图**：椭圆节点可检测（YOLO对椭圆外接框没问题），但**参与者小人图标+泛化空心三角箭头+include/extend虚线箭头**类别要自定义；虚线边对Hough不友好，边F1预期明显低于流程图（~40-55%）。作为"C4通道"可用但不做主力。
- **标注预算**：本项目独有的优势——**Visio XML可自动生成silver标签**。对有Visio嵌入的图，`page1.xml`的Shape坐标直接转换为YOLO bbox标注（Shape类型→节点类别，Connect对→边），零人工标注获得训练集；再用少量人工核对。这是别人没有的数据闭环（详见§9.3）。
- **风险**：跨文档样式差异（不同分系统的流程图模板不同）→ 用Visio自动标注正好覆盖所有模板，因为训练标签就来自所有模板。

### 2.4 与Visio XML路线的关系

**互补+共生**。Visio XML提供（a）训练标签（b）融合锚点；检测式pipeline提供（a）对**无Visio源的图**的覆盖（b）独立于XML解析bug的第二意见。不是替代关系——对有Visio源的图，XML仍是最优通道；检测式是对覆盖率缺口的填补。

### 2.5 实现复杂度

- 代码量：~800-1500行Python（复用FlowExtract可减半；标注转换脚本~200行）
- 依赖：ultralytics + opencv + paddleocr/easyocr + pyyaml；训练需1张消费级GPU（M系列Mac亦可，YOLOv8s级）
- 数据：Visio自动标注（免费）+ 20-50图人工质检；训练时间单卡数小时
- 维护：低——模型权重固定后推理纯本地，无API成本、可复现

---

## 3. 方向2：VLM端到端理解

### 3.1 核心方法描述（技术原理）

VLM处理图表有三种用法，可信度递增：

1. **直接问答（最弱）**："这个流程图的第二步是什么？"——只用于探测，不用于结构提取。
2. **结构化输出（主流）**：让VLM输出DOT/Mermaid/自定义JSON图结构，配合constrained decoding（OpenAI structured outputs / outlines / xgrammar）保证语法合法，再解析为图。语法合法≠拓扑正确，**可解析性只是最低门槛**。
3. **中间表示+外部推理（最强）**：VLM只做"感知→文本化"，拓扑推理交给外部确定性组件。

### 3.2 证据链：为什么VLM不能单独当权威（本项目必须知道的实证）

| 证据 | 出处 | 结论 |
|------|------|------|
| **Nodes Are Early, Edges Are Late** | arXiv:2603.02865 | probing实验：**边信息在视觉编码器中线性不可分**，直到文本token层才被编码——VLM拓扑短板是表征层面的，不是prompt能修的 |
| Prior Bias on UML | arXiv:2607.02853 | 只反转箭头方向（类名布局不变），8个开源VLM关系方向准确率平均降33.48%——**VLM在"读先验"而不是"读图"** |
| Do VLMs Really Understand Visual Language? | arXiv:2410.00193 | 综合测试套件：LVLM在图解任务上大量依赖文本先验 |
| SADU (架构图benchmark) | arXiv:2604.04009 | 最佳商用VLM仅70.18%，gpt-4o-mini仅17.77% |
| FlowCE | arXiv:2406.10057 | 首个MLLM流程图多维评测（推理/定位/信息抽取），各维均显著弱于其一般能力 |
| FlowLearn | arXiv:2407.05183 | 3,858科学流程图+10,000模拟流程图，含Mermaid标注；当前LVLM表现远未可靠 |
| VLM on troubleshooting guides | arXiv:2601.22754 | 两种prompt策略均呈model-specific的布局敏感/语义鲁棒权衡——换模型=换失败模式 |
| VLM自校验弱 | IVT（见uml_diagram_understanding_survey） | VLM内部置信度与正确性相关r≈0.22——**自我置信度不可用作融合权重** |

### 3.3 增强技术（把VLM从"不可信"提升到"可用"）

| 技术 | 出处 | 原理 | 对本项目的用法 |
|------|------|------|--------------|
| **EdgeFlow（边缘图先验）** | arXiv:2605.27332 | 把原图+**确定性提取的Canny边缘图**一起给VLM，边缘图作为结构先验，零训练提升流程图→Mermaid质量 | ★直接可抄：PIL+OpenCV生成边缘图，双图输入现有kimi/GLM API |
| **Set-of-Mark (SoM)** | arXiv:2310.11441 | SAM分区+编号标记叠图 → VLM grounding大幅增强 | 用检测通道的bbox给节点编号叠图，VLM照着编号报边——**检测与VLM的组合标准做法** |
| **Graph-of-Mark (GoM)** | arXiv:2603.06663 | 指出SoM把对象当孤立实体，GoM在marks间加关系边（像素级图结构提示） | 同上升级版，适合让VLM只做"确认/否认候选边"而非自由生成 |
| **TextFlow（中间文本表示）** | arXiv:2412.16420 | 两阶段：Vision Textualizer把图转中间文本，下游任务基于中间文本——可控可解释，错误可归因 | 与本项目"UDG中间层"理念一致，互为佐证 |
| **FloCA（外挂图执行器）** | arXiv:2602.14035 | LLM管意图理解，拓扑推理交给外部图执行器（topology-constrained graph execution），杜绝幻觉转移 | 一致性校验时的推理引擎模式：结构来自多通道融合图，LLM只在图上做受约束的查询 |
| **结构化输出/constrained decoding** | 工具：OpenAI structured outputs, outlines, xgrammar | 解码时约束输出符合JSON schema | 强制VLM输出UDG schema的节点/边列表（见§10），杜绝格式漂移 |
| **Mermaid/DOT可渲染校验** | 工具：mermaid-cli, graphviz | 生成物可编译=语法层通过 | 免费的语法层验证器（前调研已提过PlantUML同理） |
| **Recall_OCR参考无关评测** | arXiv:2602.13376 | 用OCR文字集合度量生成代码的内容覆盖率+结构一致性，无需真值 | ★直接用于线上监控VLM输出质量：VLM报的节点标签必须在OCR文字集中（不在=幻觉） |

### 3.4 在本项目中的适用性

- SRS流程图/用例图：VLM（现有kimi-k2.6/GLM-4V/Qwen-VL通道）**必须保留**，因为（a）覆盖100%图片（b）中文语义理解无人能替（判断图类型、读模糊小字、理解"是/否"分支语义）（c）成本最低。但要**按3.3增强并降级为"候选生成器"**——它的输出进融合层投票，不直接进检测对象。
- 精度预期（结合实证）：节点标签F1 60-85%（清晰大图高、密集小图低），边F1 15-40%（无增强时）；加SoM/EdgeFlow增强后边F1可望40-60%（Arrow-Guided VLM证明混合式显著优于裸VLM）。
- **推荐组合**：SoM叠图（来自检测通道bbox）+ EdgeFlow边缘图 + constrained JSON输出 + Recall_OCR质量闸门。

### 3.5 与Visio XML路线的关系

**互补+被验证**。VLM通道的价值是覆盖与语义；Visio XML在有源图上天然是VLM的老师（训练few-shot示例、评测基准、融合仲裁）。同时VLM是唯一能处理"无源图"的语义通道。

### 3.6 实现复杂度

- 代码量：~300行（API调用+prompt模板+JSON解析+重试）；SoM叠图+100行；EdgeFlow+50行
- 依赖：API key（已有）；Pillow/OpenCV
- 计算：零本地算力；成本≈每图$0.01-0.05，160图级别可忽略
- 维护：中——prompt工程随模型版本漂移，需固定模型版本+定期回归（Recall_OCR监控）

---

## 4. 方向3：OCR + 图结构推理（经典CV，零训练）

### 4.1 核心方法描述（技术原理）

不训练任何模型，纯规则+几何算法：

```
[OCR全图] ──► 文字块(bbox, text) ──► [聚类分组成节点] ──► 节点集合
[二值化/去文字] ──► [Hough/LSD线段检测] ──► [折线拼接] ──► 候选边路径
                                          │
[箭头模板匹配/小分类器] ──► 方向 ─────────┤
                                          ▼
                        [端点吸附: 线端→最近节点] → 边(src→dst)
```

1. **文字→节点**：OCR文字块按空间近邻聚类（DBSCAN，eps≈行距）→ 一个簇=一个节点的文字；节点边界=簇外接矩形扩padding。**用例图的椭圆**：对文字簇周围做轮廓检测（findContours+椭圆拟合）确认节点形状与范围。
2. **线提取**：图去文字（inpainting或白色填充OCR区域）→ 二值化 → HoughLinesP找直线段（正交流程图适用）/ LSD线段检测器 / 骨架化（morphology+skimage.skeletonize）处理曲线与虚线。
3. **箭头方向**：经典做法（a）箭头头部模板匹配（多尺度、旋转）（b）小CNN二分类线段两端谁是头（c）几何特征：箭头端局部像素密度/三角形拟合。
4. **边组装**：折线拼接（共线+端点邻接）→ 路径两端吸附最近节点 → 有向边。
5. **标签归属**：路径中点附近的文字（"是/否/Y/N"）→ 边标签。

### 4.2 代表性工作/工具

| 项目 | 说明 |
|------|------|
| **PaddleOCR (PP-OCRv4/v5)** | 检测(DBNet)+识别(CRNN/SVTR)+方向分类；**中文最强**；附PP-Structure版面分析；MinerU底层即PaddleOCR——本项目mineru解析结果已含其输出，可复用 |
| **EasyOCR** | CRAFT检测+CRNN识别，PyTorch，易装易用；FlowExtract选它做节点文字 |
| **Tesseract 5** | LSTM引擎；对流程图小字/中文/竖排弱；优势是零依赖问题、有TSV布局输出 |
| **RapidOCR** | PaddleOCR的ONNXRuntime移植，免Paddle重依赖 |
| **Surya** | 多语言文档OCR+版面（MinerU生态新选项） |
| OpenCV | HoughLinesP / LSD / morphologyEx / findContours / minAreaRect |
| **Reading Industrial Inspection Sheets** (arXiv:1812.07104) | 从手标检查表推断视觉关系的早期系统性工作——"OCR+关系推断"范式的文档分析代表 |
| 经典图形学文档分析谱系 | 1990s-2010s：图解解析（Futrelle等）、符号识别+关系语法、手绘流程图数据集hdFlowChart（Awal等）——箭头/线分析的几何算法库来源 |

### 4.3 在本项目中的适用性

- **流程图**：可行。SRS流程图是born-digital渲染（非扫描），文字清晰、线条规整，Hough+端点吸附的精度会比扫描件场景好不少。预期：节点文字召回>90%（PaddleOCR中文强），边F1 40-60%（正交折线好、交叉/标签压线差）。
- **用例图**：弱。椭圆轮廓、参与者小人、虚线include/extend、空心三角泛化箭头——规则链每一环都脆。此通道对用例图只提供文字锚点，不做结构。
- **独特价值**：零训练、零标注、纯本地、完全可解释。作为（a）检测模型训练好**之前**的过渡通道（b）永远保留的**独立第三/第四意见**（与YOLO通道错误不相关——YOLO可能系统性漏某类节点，规则不会）。

### 4.4 与Visio XML路线的关系

**兜底+独立验证**。它与其他所有通道的错误模式都不相关（不学任何东西，只算几何），是融合层里最有价值的"多样性投票者"。同时对Visio不可见的图是零成本起步方案。

### 4.5 实现复杂度

- 代码量：~600-1000行（OCR调用~50行、聚类~100行、线提取+拼接+吸附~400行、箭头~150行）——主要成本在**调参**（阈值、padding、eps）
- 依赖：paddleocr（已有MinerU venv）+ opencv + scikit-learn + scipy
- 计算：CPU可跑全量；每图秒级
- 维护：高维护成本样式敏感——每个分系统模板可能要单独调参，故定位为辅助通道而非主力

---

## 5. 方向4：图表专用预训练模型

### 5.1 核心方法描述（技术原理）

图像→文本的seq2seq transformer，用"图表derendering"目标预训练（图→结构化文本的映射），再下游微调。谱系：

```
Pix2Struct (2022) ── 屏幕截图解析预训练(截图→简化HTML)
Donut (2021) ────── OCR-free文档理解(SwTR encoder-decoder, 图→JSON)
MatCha (2022) ───── +数学推理+图表derendering(图→表格/代码)
DePlot (2022) ───── plot→线性化表格(模态转换) + LLM推理(两步法)
UniChart (2023) ─── 图表理解+推理统一预训练
ChartAssisstant (2024) ─ chart-to-table预训练+多任务指令微调
Nemotron-Parse 1.1 (2025) ─ 885M通用文档解析(含图表/图形文字提取+bbox+语义类)
```

**与本项目任务的本质错位**：这一族模型面向**数据图表**（bar/line/pie/scatter：视觉元素编码数值，结构=坐标系+图例），而SRS的流程图/用例图是**拓扑图**（视觉元素编码实体与关系，结构=图论结构）。数据图表的"derendering"输出是表格；拓扑图需要输出的是节点/边列表——预训练分布不含这种映射，**直接zero-shot使用会失败**（FloCo-T5论文即针对此缺口：流程图被OCR引擎当图形忽略，arXiv:2501.17441，用transformer把流程图转可执行Python代码）。

### 5.2 代表性工作/工具（含对本项目 relevancy）

| 工作 | 出处 | 对本项目 |
|------|------|---------|
| **Pix2Struct** | arXiv:2210.03347 | 架构可借鉴：小图encoder(补丁化)+文本decoder，微调流程图→DOT任务技术上可行 |
| **Donut** | arXiv:2111.15664（稀疏化DONUT-hole 2311.05778、蒸馏2509.26235） | JSON直出与UDG schema天然契合；但需自建训练数据（可用Visio XML生成 thousands级合成对！） |
| **MatCha / DePlot / UniChart / ChartAssisistant** | 2212.09662 / 2212.10505 / 2305.14761 / 2401.02384 | 方法论参照：derendering预训练目标设计；数据图表任务与本项目无关 |
| **FloCo-T5** | arXiv:2501.17441 | **唯一同任务**（流程图→代码）的专用transformer；证明该路线可行且效果与训练数据规模强相关 |
| **PlotPick** | arXiv:2605.06021 | 重要信号：6个通用VLM在chart-to-table上**全部超过**DePlot——专用小模型红利正在被通用VLM吃掉，专用路线性价比下降 |
| Nemotron-Parse 1.1 | arXiv:2511.20478 | 现代统一文档解析模型（含diagram文字提取+bbox），可作为比PaddleOCR更强的OCR/版面底座试用 |

### 5.3 在本项目中的适用性

- 直接用：**不推荐**（任务错位+需要训练数据+被VLM追平）。
- 唯一值得考虑的形态：**Donut/Pix2Struct微调"流程图→UDG JSON"**，训练对由Visio XML自动生成（§9.3闭环）+合成图增广（FlowLearn simulated模式、JSynFlow arXiv:2602.04142的LLM合成法）。若未来要发"专用解析器"论文，这是可挖的点，但**优先级低于方向1**（YOLO路线标注同样来自Visio、精度更可控、可解释性更好）。
- Nemotron-Parse值得单独试验作为OCR替代底座（对图中文字+bbox质量高于纯OCR时，全线受益）。

### 5.4 与Visio XML路线的关系

**技术储备**。Visio XML在这里的角色是"微调数据发生器"。当前阶段不投入。

### 5.5 实现复杂度

高：需要微调框架（HuggingFace）+ 数千训练对 + GPU（A100级数小时-数天）+ 评测集。约2000行+一次完整的ML工程迭代。

---

## 6. 方向5：多信息源融合与归一化

### 6.1 核心方法描述（技术原理）

融合谱系（按假设强度递增）：

| 层级 | 方法 | 假设 | 出处 |
|------|------|------|------|
| L1 | 多数投票 | 通道等权 | 古典 |
| L2 | 加权投票（权重=通道历史精度） | 通道精度可估计且稳定 | 经典ensemble |
| L3 | **Dawid-Skene EM** | 每通道有混淆矩阵，真值未知；EM交替估计通道可靠性与真值后验 | Dawid & Skene 1979（众包标注金标准方法） |
| L4 | **Truth discovery** | 源可靠性应与"接近真值"联合估计；支持分层/在线 | Frustratingly Easy Truth Discovery (arXiv:1905.00629)；分层知识融合 (1904.10217)；**复杂标注(bounding box/路径)在线聚合 (2401.15116)** |
| L5 | 概率图/贝叶斯融合 | 通道间条件独立可显式建模，可注入先验 | Bayesian model fusion |
| L6 | Source-aware（先验证后融合） | 融合前先评估每个源的当条可靠性 | Trust Before Fusion (arXiv:2607.10798，多模态RAG场景) |

**本项目的重要约束**（来自前调研的IVT结论）：VLM自我报告的置信度与正确性相关仅r≈0.22 → **不能把VLM自报置信度当融合权重**；权重必须来自通道的外部历史表现（如"该VLM在本文档其他图上与Visio锚点的符合率"）。

### 6.2 跨通道实体对齐（Entity Resolution）——融合的前置难题

四个通道的"同一个节点"长得完全不同：
- Visio XML：Shape ID + 坐标 + 文字
- VLM：文本标签（无坐标！）
- YOLO+OCR：bbox + OCR文字
- 经典CV：bbox + OCR文字

对齐键设计（多级匹配，级联过滤）：
1. **文字键**：规范化标签（全半角/繁简/去空白/同义词典——可复用`knowledge/srs_kb.json`的23参数词典）精确匹配
2. **空间键**：bbox IoU > 阈值（有坐标的通道间）
3. **组合键**：标签匹配但多个同名节点 → 用邻接上下文消歧（相邻节点集合的Jaccard）
4. 匹配算法：二部图最大匹配（scipy `linear_sum_assignment`），代价 = α·(1-文字相似度) + β·(1-IoU)

相关工作：Juno跨模态实体匹配（arXiv:2303.00720，视觉富文档）、实体匹配benchmark重建（2205.05889）、多模态共指（2504.14321）。方法论上众包的复杂标注聚合（2401.15116：证明标注者期望平均相似度与其准确率线性相关）可直接移植为"通道期望一致度→通道权重"的理论依据。

### 6.3 图级融合算法（本项目定制设计）

```
输入: 通道图集合 {G_visio?, G_vlm, G_det, G_cv}
Phase A 节点融合:
  1. 跨通道节点对齐（§6.2级联键）→ 对齐组（每组=同一实体）
  2. 每组: label = 权重投票(Visio/VLM/OCR文字), bbox = 均值, type = 投票
  3. 单通道独有的节点 → 疑似漏检/幻觉 → 进入冲突报告(不直接丢弃)
Phase B 边融合:
  1. 节点对齐后把各通道边映射到统一节点ID
  2. 边(u,v,dir,label)逐条投票:
     - ≥2通道一致 → 采纳(confidence=投票强度)
     - 仅Visio有 → 采纳(金标准锚)
     - 仅VLM有 → 低置信候选(Recall_OCR/几何验证后再定)
     - 方向冲突 → 仲裁(Visio优先; 无Visio时检测通道优先)
  3. 通道独有边 → 冲突报告
Phase C 输出:
  UDG图 + 每元素provenance(哪些通道支持) + 冲突清单
```

**冲突报告的双重价值**：通道间分歧既可能是提取误差（管线bug），也可能是**文档本身的不一致**（如正文说A→B而图画成B→A）——融合层不区分二者，把分歧连同证据链交给方向B的一致性检测器判定。这是融合层与研究目标的接口。

### 6.4 在本项目中的适用性 / 与Visio的关系 / 复杂度

- 适用性：**这是本项目真正的技术贡献点所在**（方向A上下文关联的核心组件）。多通道提取是工程，跨通道对齐+带provenance融合+分歧→不一致信号映射是方法。
- 与Visio关系：Visio是融合层的**锚点+仲裁者**（有Visio的图上，其他通道与其对齐并计分；无Visio的图上，通道间互相计分，权重迁移用"文档内同模板图"的符合率）。
- 复杂度：中。仲裁器~500-800行Python（networkx+scipy），无训练；难点在对齐调参与通道权重初始化（用Visio锚点自动校准可解）。

---

## 7. 方向6：图匹配与一致性判定

### 7.1 核心方法描述

提取出UDG图后，与正文步骤序列/表格/其他章节图比对——这是方向B检测的执行器。工具全部现成：

| 任务 | 算法/工具 | 本项目API |
|------|----------|----------|
| 图相等/包含判定（Visio图 vs 融合图） | **VF2** (Cordella et al. 2004)；大图用ISMAGS | `networkx.algorithms.isomorphism.GraphMatcher/DiGraphMatcher.subgraph_is_isomorphic()`；已验证本机networkx 3.6.1可用 |
| 结构相似度（正文流程描述 vs 图） | **图编辑距离GED**（NP-hard，小图精确可行） | `nx.similarity.graph_edit_distance()` / `optimize_edit_paths()`（已验证可用）；|V|≤50的流程图秒-分钟级 |
| GED近似（大图/批量） | GEDLIB库；神经近似SimGNN (arXiv:1808.05689) | 相似度排序场景才需要 |
| 节点集对齐 | 匈牙利算法 | `scipy.optimize.linear_sum_assignment`（已验证） |
| 步骤序列比较 | LCS/编辑距离 | `difflib.SequenceMatcher`；**注意**：流程图有分支，先做"入口到出口的所有路径枚举"再逐路径LCS，或直接用GED |
| 超越结构的等价 | **功能等价匹配** (arXiv:2505.21988) | 思想借鉴：EDA电路中综合变换改变拓扑但功能不变→只比结构会产生假阳性；SRS中"正文用文字描述子流程、图中用宏节点折叠"即此类 |

### 7.2 结构diff → 不一致类型映射（连回方向B）

GED/匹配的编辑脚本（node/edge insert/delete/substitute操作序列）可直接映射为候选不一致类型：

| 编辑操作 | 可能的不一致类型 | 需排除的提取误差 |
|---------|----------------|----------------|
| 节点在文本通道存在、图中缺失 | 正文步骤未入图 / 图过时 | 节点漏检（查该节点OCR证据） |
| 边方向反转 (u→v vs v→u) | 流程顺序矛盾 | 箭头方向分类错误（查bbox证据） |
| 边标签/条件值不同 ("否"vs"是") | 条件分支语义矛盾 | OCR错字（文字编辑距离1以内疑OCR） |
| 边在一通道存在另一通道无 | 隐藏依赖/图不完整 | 边漏检 |
| 节点标签同但语义角色不同 | 概念歧义 | 对齐错误 |

**这正是"无Gold Standard评测"的解法之一**：提取通道间一致的部分=高置信结构；分歧部分=要么管线误差要么文档不一致——人工抽检分歧即可低成本构建gold standard（比全量标注便宜一个量级，前调研"分歧驱动标注"同思路）。

### 7.3 复杂度

低。纯库调用~300行；VF2/GED对本项目图规模（10-50节点）完全实时。**这是性价比最高的方向，建议立即纳入**。

---

## 8. 方向7：端到端学习方案

### 8.1 核心方法描述

| 路线 | 原理 | 代表 |
|------|------|------|
| 多模态对比学习 | 图文对的正负对对比，学共享嵌入空间 | CLIP (2103.00020)范式；文档版：VLCDoC (2205.12029)、DocMMIR (2505.19312) |
| 文档多模态预训练 | 文本+布局(+图像patch)联合预训练 | **LayoutLM** (1912.13318) → v2 (2012.14740，+图像对齐/匹配任务) → v3；MarkupLM (2110.08518，HTML/XML结构) |
| 视觉文档检索 | 跳过OCR直接页级视觉检索 | **ColPali** (2407.01449，PaliGemma+late interaction) |
| 单-混模态对齐 | 图像encoder对齐到MLLM表示 | M4Doc (2507.07572)；对齐增强微调AETNet (2211.14777) |
| 三模态cross-attention | 图+表+文token级attention做一致性打分 | 研究方向级（尚无成熟开源工作直接针对SRS三模态一致性） |

### 8.2 在本项目中的适用性（现实评估）

- **端到端训练一致性模型：不可行**。16份文档≈160图+数千需求条目，不足以训练任何端到端多模态模型；SRS域无公开数据集可迁移。
- **可行的轻量形态**：
  1. **冻结embedding+度量学习**：用CLIP中文版/Chinese-CLIP或Qwen-VL的视觉embedding，对"图节点文字 vs 正文需求条目"算相似度做候选关联（方向A的召回器），在Visio锚点对上校准阈值——零训练或只训一个projection head（几百个样本即可）。
  2. **合成数据扩容**（若要走向学习式）：FlowLearn simulated子集（脚本合成1万流程图）/ JSynFlow (2602.04142，LLM合成日文流程图VQA) / PlanSDG (2305.01323，流程图→对话) 证明**图结构合成廉价**——可用Graphviz/mermaid从模板反向渲染无限"图+UDG真值"对，训练方向4的解析器或方向7的对齐头。**注意合成→真实的domain gap是主要风险**（样式分布）。
  3. LayoutLMv3可用于SRS文档页面级任务（如需求块分类），但与图表结构提取关系不大。
- 与Visio关系：Visio对（图,UDG）是天然的对比学习正对来源。

### 8.3 复杂度

高（训练路线）：数据构建+训练框架+GPU周级。低（冻结embedding路线）：~200行调用+阈值校准。

---

## 9. 推荐的多通道融合架构

### 9.1 总体架构（DIAG-FUSE：四通道分层融合）

```
                     SRS文档 (.doc/.docx)
                    /       |         \
          [嵌入对象提取]  [MinerU图片]  [正文/表格解析]
                |              |            \
        C1 Visio XML      (PNG图池)          \
        born-digital直读    |    \            \
        精度≈100%          |     \            \
                |          |      \            |
                |     C2 VLM通道   C3 检测式通道   C4 经典CV通道
                |     (增强:SoM+   (YOLO+OCR+     (PaddleOCR+
                |      EdgeFlow+   线追踪)        Hough+规则)
                |      约束JSON)
                |          |          |            |
                v          v          v            v
             [Adapter]  [Adapter]  [Adapter]   [Adapter]     ← §10 归一化
                \          |          |          /
                 \         v          v         /
                  └──► [统一UDG schema图 × 4通道]
                                |
                    [融合仲裁器 FUSION]
                    A. 节点: 级联键对齐(文字/空间/邻接)
                       + Dawid-Skene式加权投票
                    B. 边: 逐条投票 + Visio锚点仲裁
                    C. 分歧 → 冲突报告(带provenance)
                                |
                 ┌──────────────┼──────────────┐
                 v              v              v
          [高置信UDG图]   [冲突清单]     [通道质量仪表盘]
          (方向A检测对象)  (→方向B不一致    (通道权重在线更新
                           候选+gold标准     by Visio锚点符合率)
                           抽检来源)
```

### 9.2 通道可用性与角色矩阵

| 通道 | 覆盖率 | 精度（预期） | 角色 | 启动成本 |
|------|--------|------------|------|---------|
| C1 Visio XML | 仅嵌入Visio的图（当前5份文档sc2场景） | ≈100% | **金标准锚+训练标签源+仲裁者** | 已实现(sc2_visio_extract) |
| C2 VLM增强 | 100%图 | 节点中-高/边低-中 | 语义理解+候选生成（图类型判断/中文标签/分支语义） | 1-2天 |
| C3 YOLO检测 | 100%图 | 节点高/边中 | 结构主力（无Visio图的拓扑权威） | 1-2周（含训练） |
| C4 经典CV | 100%图 | 低-中 | 独立多样性投票+零成本兜底+上线前过渡 | 3-5天 |
| C5 (可选) Nemotron-Parse | 100% | 未知（待测） | OCR/版面底座升级，替代C4的OCR段 | 1天试用 |

### 9.3 Visio XML的三重复用（本架构的核心洞察）

1. **作为训练数据发生器（silver labels）**：`page1.xml` Shape坐标/类型/Connect关系 → 自动生成YOLO训练标注（坐标转换：Visio内部坐标→PNG像素，需按图片分辨率标定一次缩放比例）。**零人工标注**覆盖所有已有Visio图的全部节点/边 → 训练C3 → C3推广到全部160+图。
2. **作为通道权重校准器**：在有Visio锚点的图上，测量C2/C3/C4的节点/边符合率（即自动算出Dawid-Skene的混淆矩阵初始值）→ 权重用于无锚点图。
3. **作为仲裁tiebreaker**：无Visio图上通道冲突时，用"该图所属文档的其他有锚点图上表现最好的通道"仲裁（文档内模板同质假设）。

### 9.4 实施顺序（依赖关系）

```
Phase 0 (已有): C1 Visio提取 ✓
Phase 1 (1周):  C2 VLM增强(SoM+EdgeFlow+约束JSON) + C4经典CV
              → 立即形成"三通道互校"最小闭环(无训练通道x2 + 锚点)
Phase 2 (1-2周): UDG schema + 四Adapter + 融合仲裁器 + Recall_OCR质量闸门
Phase 3 (1-2周): C3 YOLO训练(Visio silver labels) → 四通道全量
Phase 4 (持续):  冲突清单人工抽检 → gold standard积累 → 通道权重再校准
```

理由：Phase 1不动训练即可验证融合框架；C3依赖Phase 2的schema稳定后再训练（标注格式即UDG节点/边定义）。

---

## 10. 归一化方案：统一UDG Schema

### 10.1 UDG (Unified Diagram Graph) 完整定义

```json
{
  "diagram_id": "doc02_fig3_p2",
  "doc_id": "02界面集成框架",
  "diagram_type": "flowchart | usecase | state | interface | architecture",
  "source": {
    "image_path": "...png",
    "image_size": [1654, 2339],
    "visio_source": "path/to/page1.xml | null",
    "section_ref": "3.2.1"
  },
  "nodes": [
    {
      "uid": "n_0001",
      "label": "接收外部报文",
      "label_normalized": "接收外部报文",
      "node_type": "process | decision | start | end | io | actor | usecase | note",
      "bbox": [x1, y1, x2, y2],
      "confidence": 0.97,
      "channel_votes": {
        "visio": {"found": true, "raw_id": "Shape.12"},
        "vlm":  {"found": true, "label": "接收外部报文"},
        "det":  {"found": true, "bbox_iou": 0.91},
        "cv":   {"found": true}
      }
    }
  ],
  "edges": [
    {
      "uid": "e_0001",
      "src": "n_0001",
      "dst": "n_0002",
      "edge_type": "flow | association | include | extend | generalization",
      "label": "是",
      "waypoints": [[x,y], ...],
      "confidence": 0.85,
      "channel_votes": {
        "visio": {"found": true, "dir_confirmed": true},
        "vlm":   {"found": true},
        "det":   {"found": false, "note": "line broken"},
        "cv":    {"found": true, "dir": "forward"}
      }
    }
  ],
  "conflicts": [
    {
      "type": "edge_direction | node_missing | label_mismatch | edge_missing",
      "elements": ["e_0007"],
      "detail": "vlm: A->B; det: B->A; visio: absent",
      "requires_human": true
    }
  ],
  "meta": {"extracted_at": "...", "tool_versions": {...}}
}
```

### 10.2 各通道Adapter（输出→UDG）

| 通道 | 原始输出 | Adapter要点 | 难度 |
|------|---------|------------|------|
| C1 Visio XML | Shape/Connect/坐标 | 已有sc2_visio_extract产出图结构→补bbox坐标转换与UDG字段映射（~150行改造） | 低 |
| C2 VLM | 文本（JSON/DOT/Mermaid） | **建议约束VLM输出DOT而非Mermaid**（graphviz DOT语法更简单稳定，`pydot`解析成熟→networkx）；constrained decoding用UDG节点/边JSON schema；VLM无坐标→bbox字段留null，由对齐阶段从C3/C4借用 | 低 |
| C3 YOLO+OCR | bbox+类别+OCR文字+线追踪 | 直接映射；文字→label，bbox原生 | 低 |
| C4 经典CV | 文字簇+线段+方向 | 同上，置信度由规则启发式（Hough投票数/箭头匹配分数） | 中 |

### 10.3 归一化规则（跨通道对齐的公共基础）

1. **坐标归一化**：全部统一到原始PNG像素坐标。Visio坐标需一次标定（Shape外接框 vs PNG图框缩放比，可用两个已知Shape手工标定或自动回归）。VLM无坐标节点在对齐时从匹配上的有坐标通道**继承**bbox。
2. **文本规范化**（对齐前必做）：全角→半角、去首尾空白、压缩内部空白、繁简统一（opencc）、大小写不敏感（英文接口名）、同义词典归一（`srs_kb.json`参数词典，如"报文/消息"）。
3. **ID生成与消歧**：图内label唯一→label即键；label重复→`label#序号`+邻接消歧（用邻接节点集合Jaccard>0.5才合并跨通道同label节点）。
4. **类型映射表**：各通道类型词表→UDG枚举（Visio的Shape类型如"Process/Decision"→process/decision；YOLO类别训练时即用UDG枚举，天然一致；VLM输出schema直接约束为UDG枚举）。
5. **方向约定**：所有edge的src/dst以"箭头指向为dst"为唯一约定；各通道adapter内完成翻转（Visio的Connect有Begin/End，YOLO的箭头朝向，VLM的输出约定）。

### 10.4 图类型特定扩展

- **flowchart**：node_type用五类（start/end/process/decision/io）+ edge.label承载条件值（"是/否"）——条件值是方向B语义层检测的关键字段（同参数不同值检查点）
- **usecase**：node_type三分类（actor/usecase/note）+ edge_type四分类（association/include/extend/generalization）——泛化方向（Prior Bias论文证明VLM最易错处）设为高敏感字段，方向冲突一律进conflicts

---

## 11. 与两个已有调研的关系与增量

| 已有调研 | 覆盖 | 本报告增量 |
|---------|------|-----------|
| uml_diagram_understanding_survey.md | VLM不可信证据、三通道互校学术依据、born-digital路线论证 | 完整7方向版图（含检测式/专用模型/端到端）、FlowExtract等2026新实证、融合算法细节、UDG schema、Visio三重复用 |
| cross_modal_consistency_survey.md | 跨模态对齐、chart理解、LayoutLM、无标注评测 | 面向"图结构提取"的工程路线图、通道权重校准方法、结构diff→不一致类型映射 |

---

## 12. 参考文献（本报告新核验）

**方向1**
- FlowExtract: Procedural Knowledge Extraction from Maintenance Flowcharts — arXiv:2604.06770 | GitHub: guille-gil/FlowExtract（节点F1 98.8%/边F1 66.7%/边P 85.5%，vs最优VLM 34.0%/10.7%）
- Arrow-Guided VLM: Enhancing Flowchart Understanding via Arrow Direction Encoding — arXiv:2505.07864
- Symbol detection in online handwritten graphics using Faster R-CNN — arXiv:1712.04833
- Symbol as Points: Panoptic Symbol Spotting via Point-based Representation — arXiv:2401.10556
- GAT-CADNet — arXiv:2201.00625 | FloorPlanCAD — arXiv:2105.07147

**方向2**
- FloCA: Towards Faithful and Logically Consistent Flowchart Reasoning — arXiv:2602.14035
- EdgeFlow: Edge-Map Augmented VLM-Based Flowchart Processing for Industrial Requirements Engineering — arXiv:2605.27332
- Nodes Are Early, Edges Are Late: Probing Diagram Representations in LVLMs — arXiv:2603.02865
- Do Vision-Language Models Really Understand Visual Language? — arXiv:2410.00193
- FlowCE: First Multi-Dimensional Evaluation of Flowchart Comprehension for MLLMs — arXiv:2406.10057
- FlowLearn: Evaluating LVLMs on Flowchart Understanding — arXiv:2407.05183
- TextFlow: Beyond End-to-End VLMs, Intermediate Text Representations — arXiv:2412.16420
- SRA: Semantic Relation-Aware Flowchart QA — arXiv:2602.13771
- Online Reference-Free Evaluation for Flowchart Image-to-Code — arXiv:2602.13376
- JSynFlow: Japanese Synthesised Flowchart VQA Dataset — arXiv:2602.04142
- Code-Vision: Evaluating MLLMs Logic Understanding and Code Generation — arXiv:2502.11829
- Procedural Knowledge Extraction from Industrial Troubleshooting Guides Using VLMs — arXiv:2601.22754
- Set-of-Mark Prompting — arXiv:2310.11441 | Graph-of-Mark — arXiv:2603.06663
- （承前调研）Prior Bias UML 2607.02853 | SADU 2604.04009 | XML-driven LLM 2502.04389 | ERUnderstand 2607.24707 | Enginuity 2606.03410 | Unlocking UML 2605.11634

**方向3**
- Reading Industrial Inspection Sheets by Inferring Visual Relations — arXiv:1812.07104
- 工具：PaddleOCR / EasyOCR / Tesseract 5 / RapidOCR / Surya / OpenCV(HoughLinesP, LSD, morphology)

**方向4**
- Pix2Struct — arXiv:2210.03347 | Donut — arXiv:2111.15664 | DONUT-hole — arXiv:2311.05778 | Donut蒸馏 — arXiv:2509.26235
- MatCha — arXiv:2212.09662 | DePlot — arXiv:2212.10505 | DePlot微调 — arXiv:2501.04675 | GenPlot — arXiv:2306.11699
- UniChart — arXiv:2305.14761 | ChartAssisstant — arXiv:2401.02384 | PlotPick — arXiv:2605.06021
- FloCo-T5: Towards Making Flowchart Images Machine Interpretable — arXiv:2501.17441
- Nemotron-Parse 1.1 — arXiv:2511.20478

**方向5**
- Dawid & Skene 1979（EM标注聚合，经典）
- Frustratingly Easy Truth Discovery — arXiv:1905.00629 | 分层知识融合 — arXiv:1904.10217 | 公平性分析 — arXiv:2304.12573 | **复杂标注在线聚合 — arXiv:2401.15116**
- Juno: Cross-Modal Entity Matching for Visually Rich Documents — arXiv:2303.00720 | EM benchmark重建 — arXiv:2205.05889 | 多模态共指 — arXiv:2504.14321
- Trust Before Fusion — arXiv:2607.10798

**方向6**
- VF2: Cordella et al., IEEE TPAMI 2004（networkx 3.6.1 GraphMatcher/ISMAGS已验证本机可用；graph_edit_distance/optimize_edit_paths已验证）
- On the Complexity of Graph Edit Distance in Restricted Graph Classes — arXiv:2607.18914
- Convex Graph Invariant Relaxations for GED — arXiv:1904.08934
- Fast Subgraph Matching by Exploiting Search Failures — arXiv:2012.14420 | BB-Graph — arXiv:1706.06654 | Dual MPNN for Subgraph Isomorphism — arXiv:2112.08764
- Functional Matching of Logic Subgraphs: Beyond Structural Isomorphism — arXiv:2505.21988
- SimGNN — arXiv:1808.05689

**方向7**
- CLIP范式；LayoutLM — arXiv:1912.13318 | LayoutLMv2 — arXiv:2012.14740 | MarkupLM — arXiv:2110.08518
- VLCDoC — arXiv:2205.12029 | DocMMIR — arXiv:2505.19312 | ColPali — arXiv:2407.01449 | M4Doc — arXiv:2507.07572 | AETNet — arXiv:2211.14777
- PlanSDG: Turning Flowchart into Dialog — arXiv:2305.01323

**综合**
- FloCA/EdgeFlow/FlowExtract三角 = "VLM感知+确定性结构"混合范式的三个变体（外挂执行器/边缘先验/纯检测），是本报告推荐架构的文献支点
