# 05 方法路线：上下文关联与召回 (Method Roadmap)

> 最后更新: 2026-08-12
> 定位: 方向A(上下文关联)的方法设计、数据集构建、质量保证的系统性说明
> 对应代码: `algorithms/semantic/scene1/kg_context_matcher.py` + `tools/`

---

## 〇、问题定义与总体路线

### 问题
SRS文档中，同一个需求/实体分布在多个位置——3.2.1节的文字描述、能力标识表、接口图、合格性表、追溯表。如何把这些**分散的、多模态的内容聚合成一个条目**，使一致性校验有明确的检测对象？

### 总体路线（三段式）

```
┌─────────────┐   ┌──────────────┐   ┌──────────────┐
│ 数据层       │ → │ 召回层(方向A) │ → │ 检测层(方向B) │
│ 16份SRS结构化│   │ 双图融合聚合器 │   │ 语法/语义/逻辑│
│ 切片+图谱    │   │ 4通道召回     │   │ 三层校验      │
└─────────────┘   └──────────────┘   └──────────────┘
```

本文档覆盖：数据层构建（第1节）+ 召回层方法（第2节）+ 评测方法（第3节）+ 质量保证（第4节）+ 演进与局限（第5节）。

---

## 一、数据层：从16份.doc到结构化资产

### 1.1 解析管线

```
16份.doc (GJB 438C格式)
    │ textutil (Apple官方, 独立源)
    ▼
dual_source/*.html (双源之一)
    │ MinerU (深度文档解析)
    ▼
mineru_standard/16份/office/
    ├── *_content_list.json  ← 结构化条目流(文本/表格/图片/页脚)
    ├── *.md
    └── images/fig_001.png   ← 381张真实图片
```

### 1.2 结构化切片 (srs_chunker.py)

**切片原则：结构边界优先，而非纯文本滑动窗口。**

| 条目类型 | 处理策略 | 理由 |
|---------|---------|------|
| text | 500 token窗口 + 50 token重叠，句子边界(`。；;`)优先 | 长文本拆分但保留语义完整性 |
| table | **整体保留不切分** | 一个表格行=一个需求，表格是完整语义单元 |
| image | 标记`[图片] {caption}` + image_path | 图片是独立模态，后续VLM理解 |
| footer/index | 过滤丢弃 | 非需求内容 |

**关键设计**：
- **章节跟踪**：正则`^(\d+(\.\d+)*)\s+`从文本提取章节号并**持续下传**——表格/图片继承当前章节
- **可溯源**：每个chunk带 `doc/chunk_id/type/section/page/anchor/meta`

**产出**：`srs_chunks.json` — **5231条**（3643文本 + 1207表格 + 381图片）

### 1.3 知识图谱构建 (LightRAG + kimi)

```
srs_chunks → kimi-k2.6实体/关系抽取(JSON模式, 7s/chunk)
    → 11872实体 + 23449关系
    → 图谱: graphml + 实体chunk映射 + 关系列表 + 向量库(bge-small-zh)
```

**中文领域适配**：实体类型guidance定制为`软件功能/需求编号/接口/数据项/硬件设备`，比默认英文类型抽取质量显著提升（每个chunk抽2-30实体）。

### 1.4 多模态图片理解 (vlm_image_analyzer.py)

**方法**：kimi-k2.6视觉API批量分析379张SRS图片。
- 输出：`figure_type`(用例图158/流程图138/架构图28/数据流图25/活动图17) + `key_elements`(图内实体) + `summary`
- **工程可靠性**：3次重试+5s退避、断点续跑(按image_path去重)、磁盘+内存双层合并防覆盖丢失

**价值**：图片变成**可检索的结构化对象**——"结构化数据归集"出现在架构图中和正文中，就是图文实体对齐的证据。

### 1.5 数据资产全景

| 资产 | 规模 | 用途 |
|------|------|------|
| srs_chunks.json | 5231条 | 检索对象/评测标注 |
| srs_image_analyses.json | 379张 | 多模态关联 |
| lightrag_store/ | 11872实体+23449关系 | 语义召回 |
| id_document_graph.json | 2181节点(568实体+1613mention) | ID硬桥召回 |
| retrieval_evalset.json | 300查询对 | 检索评测 |
| multimodal_qa_evalset.json | 48图文QA | 端到端评测 |

---

## 二、召回层：双图融合聚合器 (方向A核心)

### 2.1 设计动机

先有Agentic RAG（Planner-Researcher-Aggregator + LLM工具调用），评测暴露问题：
- 全库扫描 O(条目数) + LLM调用，不可规模化
- LLM工具调用不可复现、成本不可控
- 名称→ID跳依赖正则提取，脆弱

**收敛为**：预计算索引 + 确定性多路查询。

### 2.2 四通道召回

```
查询(实体名/ID)
    │
    ├─① ID-Graph硬桥 ──────────────────────────────
    │   · 数据: id_document_graph.json (568实体+1613mention)
    │   · 匹配: ID哈希直查 → 8类位置mention
    │   · 位置类型: 正文/能力表/接口表/合格性表/追溯表/用例表
    │   · 优势: GJB需求ID是全局唯一锚点, 零误报确定性关联
    │   · 局限: 只对含ID查询有效, mention context仅46字符
    │
    ├─② LightRAG语义图 ────────────────────────────
    │   · 数据: 11872实体 + entity→chunk映射
    │   · 匹配: 双向子串包含(名称变体)
    │   · 补充: 关系邻居(一跳上下文)
    │   · 优势: 语义泛化(中英/缩写变体)
    │   · 局限: 子串噪声大("分系统"命中所有)
    │
    ├─③ VLM图片匹配 ───────────────────────────────
    │   · 数据: 379张图 key_elements
    │   · 匹配: 实体名 ∈ key_elements
    │   · 价值: 图片可检索, 图文实体对齐
    │
    └─④ 结构化chunks ─────────────────────────────
        · 数据: 5231 chunks带section
        · 匹配: 实体名子串 / ID / 关键词回退(前2词同时出现)
        · 价值: 精确位置(章节)+类型(文本/表格)
```

### 2.3 融合与聚合条目

```
四通道结果
    → 去重(按 location+section+snippet前30字)
    → 位置分类(text_table/figure/trace/other)
    → chain_completeness = |{text_table,figure,trace}∩loc_set| / 3
    ▼
聚合条目 = {
  entity, entity_id,
  occurrences: [{location, section, snippet, doc, source}],
  locations: [...],
  chain_completeness: 0-1
}
```

### 2.4 评测结果（300条查询对）

| 方法 | avg_recall | entity_found | section_recall | loc_recall | 耗时 |
|------|:---:|:---:|:---:|:---:|:---:|
| M1 naive (纯向量) | 0.577 | 0.467 | 0.305 | 0.959 | 0.04s |
| M2 local (图谱邻域) | 0.652 | 0.513 | 0.461 | 0.980 | 0.50s |
| M3 mix (图+向量) | 0.654 | 0.520 | 0.457 | 0.984 | 0.52s |
| M4 ID-Graph (ID硬桥) | 0.000 | 0.000 | 0.000 | 0.000 | 0.00s |
| **M5 双图融合(Ours)** | **0.809** | **1.000** | **0.500** | 0.926 | **0.01s** |

**结论与警示**：
- M5 avg_recall 0.809 领先 M3 达 +15.5pp，且速度快两个数量级
- **M4得0分是评测设计缺陷而非能力为零**：300条查询仅3条含ID(1%)，ID方法无测试场景；且ID正则首段限8字符连自身目标场景也匹配失败
- **entity_found对M5结构性必中**（输出自带entity字段），需在论文中正视此偏向
- loc_recall对文本方法送分（"图"字启发式），区分度≈0

---

## 三、评测集构建（LLM生成 + 确定性标注）

### 3.1 检索评测集 (gen_retrieval_evalset.py)

```
① 采样100实体 (seed=42)
   ├─ 60% 有ID实体 (ID-Graph entity, 期望标注最可靠)
   └─ 40% 语义实体 (LightRAG中文实体, 测语义召回)

② kimi生成3种问法/实体
   ├─ 功能定义型: "X是什么功能?"
   ├─ 结构型: "X有哪些子功能?"
   └─ 溯源型: "X在文档哪些位置被提到?"

③ 三通道确定性标注期望召回
   ├─ 结构chunks字符串匹配 → chunk_ids/sections
   ├─ ID-Graph mentions → sections
   └─ VLM图片 key_elements → locations

④ 难度标注: sections≤2 → easy(78) / else hard(222)
```

**产出**：300查询对，每条含 `query/entity/entity_id/expected{chunk_ids,sections,locations,docs}/difficulty`

### 3.2 多模态QA对 (gen_multimodal_qa.py)

```
① 从379张图采样48张 (seed=42, 过滤有key_elements的)
② kimi看图生成QA对
   - prompt要求"问题必须只能通过看图才能回答"
   - 真实图片base64传入(视觉模态)
   - 输出JSON{question, answer}
③ 图片存在性校验: 48/48通过
```

**产出**：48图文QA，覆盖15份文档，22用例图/15流程图/7架构图/2数据流图

### 3.3 评测指标 (eval_retrieval.py)

| 指标 | 定义 | 评判 |
|------|------|------|
| entity_found | 实体名/ID是否在结果中 | 对结构化方法有偏向(见2.4) |
| section_recall | 期望章节命中率 | 文本方法靠正则抽取, 尺度不同 |
| loc_recall | 位置类型覆盖率 | 文本方法"图"字启发式送分 |
| avg_recall | 三者平均 | 综合 |

---

## 四、质量保证体系

### 4.1 不一致性Gold Standard的三重互证（已完成）

| 验证 | 方法 | 结果 | 局限 |
|------|------|------|------|
| V1 双源交叉 | MinerU+textutil独立解析 | 31/31=100% | 只验证"都存在且不同", 不验证"同一事物" |
| V2 双模型标注 | kimi+claude独立判断 | 92%一致 | 共享训练偏误未被检验 |
| V3 VLM-OCR | tesseract独立OCR | 10/10无幻觉 | 10/10抽样外推417个"潜在幻觉" |
| V6 评测协议v2 | 防假高分层+holdout | 综合97.5% | hard仍100%→标定失效 |
| V5 语法×GS交叉 | S2重复ID vs GS实体 | 8/15命中 | 覆盖不全 |
| V7 基线对比 | vs B1_char | **完全相同F1=0.969** | **名称级问题字符级可解** |

### 4.2 检索评测集的质量风险（新体系）

| 风险 | 说明 | 修复方向 |
|------|------|---------|
| 循环评估 | 期望由matcher自己生成, "自我确认" | 用textutil独立解析生成期望 |
| 指标偏向 | entity_found/loc_recall对文本方法送分 | 结构化证据匹配 |
| M4错配 | ID方法无ID测试场景 | 分层报告+扩充含ID查询 |
| 无人类仲裁 | 全链无需求工程师介入 | 人工抽检+Kappa |

### 4.3 已验证的质量成果（对照原文）

- 语法层S2检出`PZXQ-GN-JMJCKJ-JMJC-KJCK`重复定义 → **正是Gold Standard矛盾对**(快捷操控/触摸操控)
- 逻辑层L1检出"存储256GB vs 56GB" → 同表内真实矛盾
- 多模态QA 48/48图片存在
- 图片分析379张0失败

---

## 五、技术演进与已知局限

### 5.1 演进路线

```
v1 Agentic RAG (Planner-Researcher-Aggregator)
    → 问题: 慢(全库扫描)/不可复现(LLM)/名称跳脆弱
v2 双图融合 (KGContextMatcher 4通道)
    → 解决: 预计算索引(0.01s)/确定性(可复现)/构建期ID桥
v3 (规划) 评测公平性修复 + 跨文档召回
```

### 5.2 已知局限

1. **名称清洗正则脆弱**：依赖问句模板穷举，未覆盖句式导致实体名含噪
2. **向量通道死代码**：`channel_vector`未接入aggregate（声称4通道实为3.5通道）
3. **section缺失**：VLM通道section硬编码空；表格chunk反查可能返回空
4. **跨文档召回未评测**：expected.docs从未参与计算
5. **chain_completeness缺陷**：location归一化只认精确"trace"，`table_traceability`落入other
6. **ID正则限制**：`[A-Z]{2,8}`首段限8字符，长前缀ID漏检
7. **LightRAG邻居召回结构错配**：full_relations按文档名组织，代码按关系ID遍历
8. **API key硬编码**：4个脚本含同一moonshot key

### 5.3 下一步（P0优先级）

- [ ] 修复评测公平性（分层报告/ID正则/结构化loc_recall）
- [ ] 打破循环评估（textutil独立期望+双LLM交叉）
- [ ] 人工抽检协议（需求工程师+Kappa≥0.8）
- [ ] 扩充含ID查询至≥30条
- [ ] 启用chunk_ids做chunk级recall

---

## 附：文件索引

| 文件 | 说明 |
|------|------|
| algorithms/semantic/scene1/kg_context_matcher.py | 双图融合聚合器(4通道) |
| algorithms/semantic/scene1/agentic_rag.py | 旧版Agentic RAG(v1) |
| tools/srs_chunker.py | 结构化切片器 |
| tools/vlm_image_analyzer.py | VLM图片分析 |
| tools/gen_retrieval_evalset.py | 检索评测集生成 |
| tools/gen_multimodal_qa.py | 多模态QA生成 |
| tools/eval_retrieval.py | 5方法评测 |
| algorithms/syntax/syntax_checker.py | 语法层校验 |
| algorithms/logic/logic_checker.py | 逻辑层校验 |
| data/gjb_438c/data_assets/ | 所有数据资产 |
