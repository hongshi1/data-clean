# 问题重新梳理：基于DataFlow生态的SRS上下文关联

## 一、当前状态

### 已完成
- L1: MinerU标准解析(16份.doc→LibreOffice→.docx→MinerU→content_list.json)
  - 1444章节 / 1207表格(HTML结构) / 381图片(含caption) / 763约束 / 407版本号
- DataFlow生态全部clone到本地(references/目录)
  - DataFlow Core (OperatorABC/PipelineABC/FileStorage)
  - DataFlow-MM (CLIPScoreFilter/ImageConsistencyFilter/VisualGroundingRefiner)
  - DataFlow-KG (KGEntityExtractor/KGTripleExtraction/graph_reasoning)
  - ProfiliTable (7-Agent表格处理闭环)
  - AgentFlow (三阶段Agent数据合成)
  - DataMind (CONTRADICTS矛盾关系+双时态Memory)
  - QA-GraphRAG (RAPTOR树+MLP路由器)

### 核心问题
当前L2处理(srs_mineru_parse.py)是自己写的简单脚本，**没有复用DataFlow Core的Operator/Pipeline/Storage**。用户要求直接用DataFlow生态的原生组件。

## 二、长程上下文关联的技术难点

### 难点1: 超长上下文 — 文档级
**问题**: 单份SRS文档4000+行(~50KB)，MinerU解析出100+章节、70+表格、20+图片。无法用LLM一次性"看到"整个文档。
**影响**: 无法做端到端的"给定整个文档，找出所有不一致"。
**DataFlow生态的解决思路**:
- DataFlow Core的KBCChunkGenerator可以把长文本切分为raw_chunk
- DataFlow-KG的KGEntityExtractor可以在chunk级别提取实体
- QA-GraphRAG的RAPTOR树可以构建多层级聚合(叶层=原始片段,摘要层=功能级)

### 难点2: 长程关联 — 跨章节
**问题**: 同一参数(如"达梦数据库版本")在3.9.1(运行环境)和3.10.3(计算机软件需求)出现，相隔1000+行。同一功能(如"服务开发支撑")在3.2概述、3.2.1专节、第4章合格性表、第5章追溯表出现，跨章节距离上千行。
**影响**: 局部处理(单章节或滑动窗口)无法覆盖同一实体的所有出现位置。
**DataFlow生态的解决思路**:
- DataFlow-KG的三元组抽取(entity-relation-entity)可以建立跨章节的实体关联
- DataMind的CONTRADICTS关系可以声明并浮现矛盾对
- DataFlow Core的Pipeline可以编排"提取→关联→检测"的多步流程

### 难点3: 多模态关联 — 文字+表格+图片
**问题**: 同一需求"数据获取功能"的描述分布在: 3.2.1文字段落 + 用例描述表(HTML表格) + 接口图(图片) + 合格性表行 + 追溯表行。
**影响**: 纯文本处理无法关联表格行和图片。
**DataFlow生态的解决思路**:
- MinerU的content_list已经分离了text/table/image类型
- DataFlow-MM的ImageConsistencyFilter可以做图文NLI检测
- ProfiliTable的7-Agent闭环可以处理表格

### 难点4: 上下文感知的关联判断
**问题**: 如何判断两段文字描述的是"同一事物"？ID可能不一致(SJCS/SJCSKZ)、名称可能有别名("故障探测预警"="故障预警修复")、章节号可能偏移。
**影响**: 单一信号(ID/名称/章节号)都不可靠，需要多信号融合。
**DataFlow生态的解决思路**:
- DataFlow-KG的KGEntityExtractor用LLM提取实体(语义理解)
- DataFlow Core的embedding可以做语义相似度匹配
- DataMind的双时态Memory可以记录同一实体的不同版本

### 难点5: GJB章节结构作为上下文
**问题**: GJB 438C的6章18子章结构定义了语义关系: 3.2定义能力→4验证能力→5追溯能力。这种结构本身就是上下文——"第4章合格性表中的行应该对应3.2.X中的需求"。
**影响**: 理解这种结构是做上下文关联的前提。
**解决思路**: 这是GJB领域特有知识，需要编码为Pipeline中的自定义Operator。

## 三、基于DataFlow生态的Pipeline设计

### 架构

```
L1: MinerU标准解析 (已完成)
    content_list.json (text/table/image with type tagging)
    ↓
L2: DataFlow Core Pipeline
    ├── Operator 1: ContentListReader (读取MinerU content_list → DataFrame)
    ├── Operator 2: SectionExtractor (从text_level标题提取章节树)
    ├── Operator 3: TableExtractor (从table_body提取结构化表格)
    ├── Operator 4: ConstraintExtractor (从text+table提取约束)
    ├── Operator 5: VersionExtractor (从text+table提取版本号)
    ├── Operator 6: ImageAssociator (关联图片到章节)
    ↓
L2/L3: 上下文关联 (自定义Operator)
    ├── Operator 7: EntityIndexer (构建文档级实体倒排索引)
    ├── Operator 8: LongRangeAssociator (长程关联: embedding+多信号融合)
    ├── Operator 9: ContextItemBuilder (构建聚合条目)
    ↓
L3: GJB标准检测 (自定义Operator)
    ├── Operator 10: GJBChecker (7项GJB标准检测)
    └── Operator 11: ReportGenerator (生成检测报告)
```

### 关键设计决策

1. **直接import DataFlow本地源码** — 不pip安装，用`sys.path.insert(0, 'references/DataFlow')`
2. **继承OperatorABC** — 每个处理步骤是一个Operator，通过input_key/output_key声明数据流
3. **使用FileStorage** — step()机制实现链式存储和断点续跑
4. **Pipeline编排** — compile时做键完整性校验
5. **自定义Operator** — L2/L3的上下文关联和GJB检测是自定义的，继承DataFlow的OperatorABC

### 超长上下文的处理策略

不是让LLM看全文，而是:
1. **文档级结构索引**: 从MinerU的text_level标题构建章节树(117个标题/份)
2. **全局倒排索引**: 扫描全文，按参数名/需求ID/版本号构建倒排索引
3. **Embedding辅助关联**: 对实体名称做embedding，用余弦相似度发现"名称不同但语义相同"的实体
4. **GJB结构作为上下文**: 3.2.X→4→5的章节关系作为关联线索
5. **Pipeline分步处理**: 每个Operator只处理一个维度，不依赖LLM看全文

## 四、实施步骤

1. 创建srs_pipeline.py — 继承DataFlow的OperatorABC，实现L2/L3 Pipeline
2. 验证Pipeline.compile()的键完整性校验
3. 验证FileStorage的step()机制
4. 在16份文档上运行完整Pipeline
5. 对比MinerU标准解析 vs textutil方案的检测质量
