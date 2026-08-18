# SRS一致性校验项目生态图

> 参考DataFlow生态图设计，将项目分为5层+1个横向维度

```mermaid
graph TB
    subgraph L5["L5 应用出口层"]
        L5A["project_guide.md<br/>项目指南v3.0"]
        L5B["07_full_technical_report<br/>完整技术报告"]
        L5C["09_qa_synthesis_design<br/>合成方案设计"]
        L5D["knowledge_full_description<br/>知识库完整说明"]
        L5E["literature_survey/<br/>7篇调研报告"]
    end

    subgraph L4["L4 评测与验证层"]
        L4A["检索评测<br/>5方法对比<br/>M5 avg_recall=0.809"]
        L4B["LLM验证<br/>kimi+claude<br/>双LLM交叉验证"]
        L4C["质量保证<br/>双源31/31<br/>双模型92%<br/>VLM-OCR 10/10"]
        L4D["评测集<br/>300查询对<br/>696条全pair覆盖<br/>48图文QA"]
    end

    subgraph L3["L3 检测与合成层"]
        L3A["方向A: 上下文关联<br/>双图融合聚合器<br/>4通道召回(ID/语义/VLM/结构)<br/>avg_recall=0.809"]
        L3B["方向B: 不一致性检测<br/>语法层(112条 GJB规则)<br/>语义层(7图方法 F1=0.897)<br/>逻辑层(Z3+LLM 6矛盾)"]
        L3C["QA合成引擎<br/>四段式: 事实提取→规则注入→LLM改写→双LLM验证<br/>26种注入方法(术语7+参数6+逻辑6+GJB7)"]
    end

    subgraph L2["L2 数据资产生产与治理层"]
        L2A["知识库<br/>GJB规则120条(对标原文)<br/>专家词典(11参数+10单位族)<br/>不一致规则14条"]
        L2B["知识图谱<br/>LightRAG(11872实体+23449关系)<br/>ID-Graph(2181节点)<br/>语义图(508实体)"]
        L2C["多模态理解<br/>VLM图片分析(379张)<br/>Born-Digital(374图/11308Shape)<br/>BGE向量(512维)"]
        L2D["Gold Standard<br/>3场景223条<br/>双源验证31/31<br/>可信负例132条"]
        L2E["Pair Dataset<br/>366个图+表+文配对<br/>7场景(sc1-sc8)"]
    end

    subgraph L1["L1 数据入口与解析层"]
        L1A["16份真实GJB 438C SRS<br/>军事信息系统需求文档"]
        L1B["textutil<br/>Apple官方解析<br/>(双源之一)"]
        L1C["MinerU<br/>深度文档解析<br/>(双源之二)"]
        L1D["srs_chunker.py<br/>结构化切片<br/>5231条(文本3643+表格1207+图片381)"]
    end

    subgraph 横向["四类不一致 (贯穿L2-L4)"]
        H1["1.术语层面<br/>同名实体/多实体映射<br/>→语义层→图+表+文"]
        H2["2.参数指标<br/>数值/单位/属性一致<br/>→语义+逻辑层→表+文"]
        H3["3.业务逻辑<br/>流程/时序/异常流<br/>→逻辑层→图+表+文"]
        H4["4.GJB合规<br/>模板/接口定义规范<br/>→语法层→表+文"]
    end

    L1A --> L1B
    L1A --> L1C
    L1B --> L2D
    L1C --> L1D
    L1D --> L2E
    L1D --> L2B
    L1D --> L2C

    L2A --> L3B
    L2A --> L3C
    L2B --> L3A
    L2B --> L3B
    L2C --> L3A
    L2D --> L4C
    L2E --> L3C
    L2E --> L3A

    L3A --> L4A
    L3B --> L4A
    L3C --> L4B
    L3C --> L4D

    L4A --> L5B
    L4B --> L5C
    L4C --> L5D
    L4D --> L5A

    H1 -.-> L3A
    H1 -.-> L3B
    H2 -.-> L3B
    H3 -.-> L3B
    H4 -.-> L3B
    H1 -.-> L3C
    H2 -.-> L3C
    H3 -.-> L3C
    H4 -.-> L3C

    style L1 fill:#e1f5fe
    style L2 fill:#e8f5e9
    style L3 fill:#fff3e0
    style L4 fill:#fce4ec
    style L5 fill:#f3e5f5
    style 横向 fill:#fffde7
```

## 分层说明

### L1 数据入口与解析层
**数据源**：16份真实GJB 438C格式SRS文档（军事信息系统需求规格说明），涵盖数据获取、传输、处理、部署等子系统。

**双源解析**：
- textutil（Apple官方命令行工具）→ HTML文本，作为独立验证源
- MinerU（深度文档解析）→ content_list.json（结构化条目流：文本/表格/图片）+ 381张真实图片

**结构化切片**：srs_chunker.py按章节边界切片（表格整体保留），产出5231条（3643文本+1207表格+381图片），每条带章节号/类型/可溯源。

### L2 数据资产生产与治理层

**知识库**（3个文件，166条记录全部HIGH可信度）：
- GJB规则库：120条，每条有source（标准章节号）+original_text（标准原文），已逐条对标GJB 438C标准原文（98/120精确匹配）
- 专家词典：11参数（同义词全部文档验证）+10单位族（79换算）+5操作符+3冲突规则+3表格schema
- 不一致规则：14条四类不一致，每条有8字段（含真实文档example）

**知识图谱**：
- LightRAG图谱：11872实体+23449关系（kimi-k2.6抽取，中文领域适配）
- ID-Graph：2181节点（568实体+1613 mention），8类位置锚定
- 语义图：508实体，7种图方法评测

**多模态理解**：
- VLM图片分析：379张SRS图片（用例图158/流程图138/架构图28），kimi-k2.6视觉API
- Born-Digital：374图/11308 Shape（Visio OLE对象提取，含坐标+文本）
- BGE向量：bge-small-zh-v1.5（512维中文embedding）

**Gold Standard**：
- 3场景223条（名称不一致122+异常流28+接口属性20+正例53）
- 双源验证31/31=100%（MinerU+textutil独立确认）
- 双模型标注92%一致（kimi+claude）
- 可信负例132条

**Pair Dataset**：366个图+表+文配对实例，7场景（sc1用例图+能力表141 / sc2流程图+用例表90 / sc3接口图+接口表30等）

### L3 检测与合成层

**方向A（上下文关联）**：
- 双图融合聚合器：4通道召回（ID-Graph硬桥+LightRAG语义图+VLM图片+结构化chunks）
- 评测：300查询对，5方法对比，M5双图融合avg_recall=0.809（领先M3 mix +15.5pp，快52倍）

**方向B（不一致性检测）**：
- 语法层：112条检测（S1章节连续/S2 ID重复定义/S4图表引用/S5结构完整/S7交叉引用），基于GJB 120条规则
- 语义层：7种图方法（连通分量F1=0.857/图注意力F1=0.897/双空间F1=0.857），S2与Gold Standard交叉印证
- 逻辑层：专家词典+Z3求解器（824约束/73组/6真实矛盾如256GB vs 56GB）+LLM语义验证（零误报）

**QA合成引擎**（四段式）：
1. 事实提取（确定性，5类事实从pair提取）
2. 规则注入（26种方法，seed=42可复现，答案由规则确定）
3. LLM改写（kimi-k2.6，核心事实不变）
4. 双LLM验证（kimi+claude交叉，只保留两者都通过的）

### L4 评测与验证层

**评测集**：
- 检索评测：300查询对（100实体×3问法），5方法对比
- 全LLM测试集：185条（四类均衡，验证86%）
- 全pair覆盖：696条（366pair全覆盖，按sc1-sc8组织）
- 多模态QA：48条（含真实图片，48/48图片存在）

**质量保证**：
- 双源交叉验证：31/31=100%（MinerU+textutil独立确认）
- 双模型标注：92%一致（kimi+claude）
- VLM-OCR验证：10/10无幻觉（tesseract独立OCR）
- LLM-as-Judge：双LLM交叉验证

### L5 应用出口层

**文档**：project_guide.md(v3.0) + 07完整技术报告 + 09合成方案设计 + 知识库完整说明 + 7篇调研报告

**代码**：algorithms/（syntax/semantic/scene1-3/logic模块化）+ tools/（15+脚本）

### 横向维度：四类不一致（贯穿L2-L4）

| 类型 | 检测层 | 模态 | 数据来源 | 注入方法 |
|------|--------|------|---------|---------|
| 术语层面 | 语义层 | 图+表+文 | pair的功能名+ID | T1-T7（7种） |
| 参数指标 | 语义+逻辑 | 表+文 | 表格属性+正文数值+专家词典 | P1-P6（6种） |
| 业务逻辑 | 逻辑层 | 图+表+文 | 流程图+用例表+正文 | L1-L6（6种） |
| GJB合规 | 语法层 | 表+文 | GJB规则库+表头+ID | G1-G7（7种） |
