# sc2_flowchart_usecase 技术方案
## 流程图与用例描述表一致性校验

> 目标: 对90个{image.png, table.csv, text.txt}三元组，检测流程图与用例描述表之间的不一致性
> 数据: 5份SRS文档, 90张流程图(全部为Visio源嵌入), 90个用例描述表
> 关键发现: 5份文档的docx中共有172个Visio嵌入(42+48+44+31+7), 与90张pair_dataset图片有确定性映射关系

---

## 一、数据结构分析

### 1.1 sc2_flowchart_usecase数据结构

每个样本包含:
```
2_001/
├── image.png       # 流程图(从.doc中提取的渲染图, 252x695~504x839)
├── table.csv       # 用例描述表(UseCase名称/Actors/概述/前置条件/主事件流/异常流/后置条件)
├── text.txt        # 所在章节的正文描述
└── meta.json       # 元信息(instance_id/doc/section/image_caption/func_names/match_quality)
```

### 1.2 数据分布

| 维度 | 分布 |
|------|------|
| 总样本 | 90 |
| 来源文档 | 04数据统一(33) > 02界面(22) = 07报文(22) > 12文电(8) > 09数据同步(5) |
| 图类型 | 全部为流程图(caption含"流程图") |
| match_quality | strong: 56, medium: 34 |
| func_names | min=8, max=38, avg=11.1 |
| Visio嵌入 | 172个(5份文档), 可确定性提取 |

### 1.3 一致性校验的核心问题

给定一个样本，需要回答:
1. **节点集合一致性**: 流程图中有哪些步骤节点? 用例表的主事件流列出了哪些步骤? 集合是否对齐?
2. **流程顺序一致性**: 流程图的拓扑顺序 vs 用例表的步骤编号顺序是否一致?
3. **参与者一致性**: 流程图中的Actor(参与者/系统) vs 用例表的Actors字段是否对齐?
4. **异常流一致性**: 流程图中的分支/异常路径 vs 用例表的异常流(E1/E2)是否对齐?
5. **正文描述一致性**: text.txt中描述的功能 vs 流程图+表格展示的功能是否一致?

---

## 二、双路技术路线

### 路线A: Visio源提取(Deterministic Path) — 主路

**核心**: .doc → LibreOffice → .docx → word/embeddings/oleObject*.bin → OLE2 Package流 → Visio ZIP → page1.xml → 精确提取Shape/Text/Connect

**已验证的提取能力**:
```python
# 从oleObject3.bin提取的Visio数据(02界面文档):
# 形状: 33个(系统边界/用例/参与者/归纳)
# 文本: 13个("界面集成框架","界面开发","界面集成","界面定制","界面监控",
#             "界面展现","开发人员","使用人员","应用软件","服务集成框架",
#             "软件部署管理","运行支撑服务","数据统一访问服务")
# 连接: 40条(FromSheet→ToSheet, 含方向信息)
```

**技术步骤**:
1. 批量转换: .doc → .docx (LibreOffice soffice)
2. 解压docx: 提取word/embeddings/*.bin
3. OLE解析: olefile → Package流 → ZIP
4. Visio解析: page1.xml → ElementTree解析
5. 结构提取: Shape(ID/Type/Name/Text/PinX/PinY) + Connect(FromSheet/ToSheet/FromCell/ToCell)
6. 构建图: networkx.DiGraph(节点=Shape, 边=Connect)
7. 与pair_dataset映射: 按顺序/位置/caption匹配oleObject → image.png

**映射策略** (oleObject*.bin → pair_dataset的image.png):
- 按文档分组: 同一docx的嵌入对应同一文档的图片
- 按出现顺序: docx中嵌入的顺序通常与文档中出现顺序一致
- 按内容匹配: 提取的Shape文本与meta.json中的func_names匹配

### 路线B: 视觉理解(Perception Path) — 辅路/对比基线

**核心**: 不依赖源文件，从渲染图(image.png)中感知内容

**三级漏斗** (对齐DataFlow-MM设计):
```
Level 1: OCR提取(PaddleOCR/RapidOCR)
  → 提取图片中的所有文字标签(节点名称/条件/注释)
  → 输出: 文字列表+位置坐标

Level 2: VLM结构化(GLM-4V/kimi-k2.6 API)
  → 输入: 图片 + "提取流程图中的所有节点、分支和连接关系, 输出JSON"
  → 输出: {nodes: [{id, text, type}], edges: [{from, to, label}]}

Level 3: VLM验证(VisualGroundingRefiner模式)
  → 对可疑节点做Yes/No验证: "图中是否包含名为'XXX'的节点?"
```

**双路融合策略**:
- 有Visio源 → 路线A为主, 路线B用于验证
- 无Visio源 → 路线B独立运行
- A/B结果对比 → 差异本身也是发现(图片与源文件不一致)

---

## 三、一致性检测算法

### 3.1 节点集合匹配(Node Set Matching)

**输入**: 流程图节点集合V_img, 用例表步骤集合V_table
**输出**: 匹配结果(对齐/多余/缺失)

```python
# 用例表步骤提取(从table.csv)
def extract_table_steps(table_csv):
    """
    从用例描述表中提取主事件流步骤
    格式: Actor的动作列 + 系统的动作列
    """
    steps = []
    for row in rows:
        for cell in row[:2]:  # Actor动作 + 系统动作
            # 匹配编号: "1.开发人员打开..." → 步骤1
            m = re.match(r'(\d+)[\.．]\s*(.+)', cell)
            if m:
                steps.append({"num": int(m.group(1)), "text": m.group(2)})
    return steps

# 流程图节点提取(从Visio page1.xml)
def extract_visio_nodes(page_xml):
    """
    从Visio XML提取流程图节点
    区分: 用例节点(Type=Shape, Name含"用例") vs 参与者(Name含"参与者")
    """
    nodes = []
    for shape in shapes:
        text = get_text(shape)
        name = shape.get('Name', '')
        node_type = 'usecase' if '用例' in name else 'actor' if '参与者' in name else 'other'
        if text:
            nodes.append({"id": shape.get('ID'), "text": text, "type": node_type})
    return nodes

# 匹配
def match_nodes(visio_nodes, table_steps):
    """
    四层匹配:
    1. 精确匹配: "打开软件开发ide工具" == "打开软件开发ide工具"
    2. 关键词匹配: "打开IDE" ∈ "打开软件开发ide工具(包括webstrom)"
    3. Embedding匹配: bge-zh余弦相似度 > 0.7
    4. LLM仲裁: GLM-5判断两个描述是否指同一步骤
    """
    matched = []      # (visio_node, table_step)
    img_only = []     # 流程图有但表格没有
    table_only = []   # 表格有但流程图没有
    return matched, img_only, table_only
```

### 3.2 流程拓扑匹配(Flow Topology Matching)

**输入**: 流程图的Connect关系 → networkx.DiGraph, 用例表的步骤编号序列
**输出**: 拓扑一致性

```python
def check_flow_consistency(visio_graph, table_steps):
    """
    1. 从用例表提取隐含的顺序: 步骤1→步骤2→...→步骤N
    2. 从流程图Connect提取拓扑: 节点A→节点B
    3. 比较两个有向图的拓扑序
    """
    # 流程图拓扑序
    visio_order = list(nx.topological_sort(visio_graph))
    
    # 用例表顺序
    table_order = [s['num'] for s in sorted(table_steps, key=lambda x: x['num'])]
    
    # 对齐后比较
    # 异常: 流程图有分支但表格是线性的
    # 异常: 表格步骤N对应的节点在流程图中位于步骤N-1之前
    return inconsistencies
```

### 3.3 异常流匹配(Exception Flow Matching)

**输入**: 流程图中的分支节点/异常路径, 用例表的"异常流E1/E2"描述
**输出**: 异常流覆盖一致性

```python
def check_exception_flows(visio_graph, table_rows):
    """
    用例表: "异常流E1: 组件无法被正常加载, 用例结束"
    流程图: 需要有对应的分支/终止节点
    
    检测:
    - 表格中有异常流E1但流程图无对应分支 → 缺失
    - 流程图有分支但表格无异常流描述 → 多余
    """
    # 从表格提取异常流
    exception_flows = re.findall(r'异常流(\w+)[：:](.+)', table_text)
    
    # 从流程图中找分支节点(出度>1的节点)
    branch_nodes = [n for n in visio_graph.nodes() if visio_graph.out_degree(n) > 1]
    
    return coverage_analysis
```

### 3.4 参与者匹配(Actor Matching)

**输入**: 流程图中的参与者节点(Visio Name含"参与者"), 用例表的Actors字段
**输出**: 参与者一致性

```python
def check_actors(visio_actors, table_actors):
    """
    流程图: [开发人员, 使用人员, 应用软件, 服务集成框架, ...]
    用例表: "Actors：开发人员"
    
    检测: 流程图有5个参与者但用例表只列了1个 → 可能不完整
    """
```

### 3.5 正文描述匹配(Text Description Matching)

**输入**: text.txt中的功能描述, 流程图+表格的联合信息
**输出**: 描述一致性

```python
def check_text_consistency(text, visio_nodes, table_content):
    """
    text.txt: "开发工程生成是提供用户进行基于界面框架二次开发的模板工程..."
    
    检测: 正文提到的功能是否在流程图/表格中体现
    方法: 关键词提取 + NLI判断
    """
```

---

## 四、Gold Standard构建

### 4.1 基于Visio源的确定性Gold Standard

Visio源提取是100%确定的(非猜测), 可以作为:
- **节点提取的Gold Standard**: OCR/VLM提取的节点 vs Visio源的精确节点
- **连接关系的Gold Standard**: VLM提取的边 vs Visio的Connect

### 4.2 人工标注的不一致性Gold Standard

对90个样本，人工标注:
1. 节点集合差异: 流程图多了哪些节点? 表格多了哪些步骤?
2. 顺序差异: 哪些步骤顺序不同?
3. 异常流差异: 哪些异常流缺失/多余?
4. 参与者差异: 哪些参与者未在表格中列出?

### 4.3 评测指标

| 指标 | 计算方式 |
|------|---------|
| Node Alignment P/R/F1 | 匹配的节点数 / (提取的节点数, 真实节点数) |
| Flow Consistency | 拓扑序一致的比例 |
| Exception Coverage | 检出的异常流差异 / 真实异常流差异 |
| Overall Accuracy | 所有不一致性类型的综合准确率 |

---

## 五、实施计划

### M1: Visio源提取与映射 (3天)

| 任务 | 产出 |
|------|------|
| 批量提取: 5份docx → 172个oleObject → 172个Visio结构 | visio_structures.json |
| 建立映射: oleObject → pair_dataset image.png | mapping.json |
| 解析Visio: Shape/Text/Connect → networkx.DiGraph | graphs/ |
| 验证: 与pair_dataset的func_names对比 | 映射准确率 |

### M2: 视觉感知对比 (2天)

| 任务 | 产出 |
|------|------|
| PaddleOCR提取图片文字 | ocr_results.json |
| GLM-4V提取节点/边结构 | vlm_results.json |
| 与Visio源对比: OCR/VLM vs Ground Truth | 方法对比报告 |

### M3: 一致性检测流水线 (5天)

| 任务 | 产出 |
|------|------|
| 节点集合匹配(四层) | node_matching.py |
| 流程拓扑匹配 | flow_matching.py |
| 异常流匹配 | exception_matching.py |
| 参与者匹配 | actor_matching.py |
| 整合为Pipeline | sc2_pipeline.py |

### M4: Gold Standard与评测 (4天)

| 任务 | 产出 |
|------|------|
| 人工标注30个样本 | gold_standard.json |
| 运行检测流水线 | detection_results.json |
| 计算P/R/F1 | evaluation_report.md |

---

## 六、代码架构

```
tools/
├── sc2_visio_extract.py      # M1: Visio源提取
│   ├── doc_to_docx()          # .doc → .docx (LibreOffice)
│   ├── extract_ole_objects()  # docx → oleObject*.bin
│   ├── parse_visio_xml()      # oleObject → Shape/Text/Connect
│   └── build_graph()          # → networkx.DiGraph
│
├── sc2_visual_perception.py   # M2: 视觉感知(OCR+VLM)
│   ├── ocr_extract()          # PaddleOCR提取文字
│   ├── vlm_extract()          # GLM-4V提取节点/边
│   └── vlm_verify()           # Yes/No验证
│
├── sc2_consistency.py         # M3: 一致性检测
│   ├── match_node_sets()      # 节点集合匹配
│   ├── match_flow_topology()  # 流程拓扑匹配
│   ├── match_exception_flows()# 异常流匹配
│   ├── match_actors()         # 参与者匹配
│   └── match_text_description()# 正文匹配
│
└── sc2_evaluate.py            # M4: 评测
    ├── load_gold_standard()
    ├── run_detection()
    └── compute_prf()
```

---

## 七、风险与缓解

| 风险 | 概率 | 缓解 |
|------|------|------|
| oleObject→image映射不精确 | 中 | 用Shape文本与func_names匹配验证 |
| 小图OCR/VLM召回低(已实证~0.2) | 高 | 主路用Visio源(100%保真), 视觉路仅对比 |
| 用例表步骤格式不统一 | 中 | 多种正则模式+LLM兜底解析 |
| 流程图分支复杂难以线性化 | 中 | 只比较拓扑序不比较精确路径 |
| 90样本可能不够统计显著 | 低 | 用bootstrap重采样估计置信区间 |
