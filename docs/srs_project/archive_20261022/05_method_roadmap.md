# 05 方法路线：上下文关联与召回 (Method Roadmap)

> 最后更新: 2026-08-12
> 定位: 方向A(上下文关联) + 方向B(一致性检测) 的方法设计、数据集构建、指标计算与质量保证
> 对应代码: `algorithms/semantic/scene1/kg_context_matcher.py` + `algorithms/{syntax,logic}/` + `tools/`
> 数据: `data/gjb_438c/data_assets/`

---

## 〇、问题定义与总体路线

### 0.1 问题

SRS文档中，同一个需求/实体分布在多个位置——3.2.1节的文字描述、能力标识表、接口图、合格性表、追溯表。如何把这些**分散的、多模态的内容聚合成一个条目**，使一致性校验有明确的检测对象？

### 0.2 总体路线（三段式流水线）

```
┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
│ 数据层       │ → │ 召回层(方向A) │ → │ 检测层(方向B)     │
│ 16份SRS结构化│   │ 双图融合聚合器 │   │ 语法/语义/逻辑    │
│ 切片+图谱    │   │ 4通道召回     │   │ 三层校验          │
└─────────────┘   └──────────────┘   └──────────────────┘
    5231 chunks     聚合条目           检测结果
    11872实体        (occurrences)     (conflict reports)
```

### 0.3 文档覆盖

| 章节 | 内容 | 关键指标 |
|------|------|---------|
| 一 | 数据层：从.doc到结构化资产 | 5231 chunks / 11872实体 / 379图 |
| 二 | 召回层：双图融合聚合器 | avg_recall 0.809 / 0.01s |
| 三 | 评测集构建 | 300查询 / 48图文QA |
| 四 | 语义层数据集构建（方向B对象） | 223条GS / 546描述级 |
| 五 | 质量保证体系 | 31/31双源 / 92%双模型 / 97.5%协议 |
| 六 | 技术演进与已知局限 | 8项局限 / P0修复清单 |

---

## 一、数据层：从16份.doc到结构化资产

### 1.1 解析管线（双源独立解析）

```
16份.doc (GJB 438C格式, 军事信息系统SRS)
    │
    ├── textutil (Apple官方命令行, 与MinerU无关的独立解析源)
    │       ▼
    │   dual_source/*.html          ← 双源之一(用于交叉验证)
    │
    └── MinerU (深度文档解析, 版面/表格/图片识别)
            ▼
        mineru_standard/16份/office/
            ├── *_content_list.json ← 结构化条目流(黄金输入)
            ├── *.md
            └── images/fig_XXX.png  ← 381张真实图片
```

**content_list.json 条目类型分布**（03号文档示例, 共359条）：

| 类型 | 数量 | 说明 |
|------|:---:|------|
| text | 244 | 正文段落, 含`text_level`(标题层级) |
| table | 89 | 含`table_caption`/`table_body`(HTML) |
| image | 21 | 含`image_caption`/`image_path` |
| footer | 2 | 页脚(过滤) |
| index | 1 | 目录(过滤) |

### 1.2 结构化切片 (tools/srs_chunker.py)

**切片原则：结构边界优先，而非纯文本滑动窗口。**

#### 1.2.1 Token估算公式

```python
def num_tokens(text):
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))   # 中文字符: 1字=1token
    other = len(re.sub(r"[\u4e00-\u9fff\s]", "", text)) # 其他字符: 4字符=1token
    return cjk + other // 4
```

**示例**：文本"本功能实现创建服务工程，用户可配置工程名称。" 
- CJK字数 = 22 → 22 tokens
- 其他字符 = 2（逗号、句号不计空白）→ 0 tokens
- 总 ≈ 22 tokens

#### 1.2.2 切片策略表

| 条目类型 | 处理策略 | 参数 | 理由 |
|---------|---------|------|------|
| text | token滑动窗口 | 窗口500 / 重叠50 | 长文本拆分但保留语义完整性 |
| table | **整体保留不切分** | — | 一个表格行=一个需求，表格是完整语义单元 |
| image | 标记`[图片] {caption}` + image_path | — | 图片是独立模态，后续VLM理解 |
| footer/index | 过滤丢弃 | — | 非需求内容 |

#### 1.2.3 滑动窗口算法（句子边界优先）

```python
def split_on_tokens(text, chunk_size=500, overlap=50):
    if num_tokens(text) <= chunk_size:
        return [text]
    parts = re.split(r"(?<=[。；;])", text)   # 中文句末标点切分
    chunks, cur, cur_len = [], [], 0
    for p in parts:
        p_len = num_tokens(p)
        if cur_len + p_len > chunk_size and cur:
            chunks.append("".join(cur))
            tail = "".join(cur)[-overlap * 4:]  # 保留尾部重叠(~200字符)
            cur, cur_len = [tail], num_tokens(tail)
        cur.append(p)
        cur_len += p_len
    if cur:
        chunks.append("".join(cur))
    return chunks
```

**重叠的作用**：跨chunk实体（如"创建服务工程"被切到两个chunk边界）仍能在两个chunk中都完整出现，保证召回不丢。

#### 1.2.4 章节跟踪

```python
def section_of(item, current_section):
    if item["type"] == "text":
        m = re.match(r"^(\d+(?:\.\d+)*)\s+", item["text"].strip())
        if m:
            return m.group(1)   # 提取章节号
    return current_section      # 非标题 → 继承当前章节
```

**关键设计**：表格/图片继承"当前章节"——即使表格本身无章节号，也能定位到它所属的3.2.x。

#### 1.2.5 产出统计

**srs_chunks.json — 5231条 = 3643文本 + 1207表格 + 381图片**

| 文档 | chunks | 文档 | chunks |
|------|:---:|------|:---:|
| 01数据获取转换 | 339 | 09数据同步共享 | 328 |
| 02界面集成框架 | 441 | 10动态名录 | 387 |
| 03服务集成框架 | 354 | 11语音综合 | 207 |
| 04数据统一访问 | 365 | 12文电处理 | 344 |
| 05软件部署管理 | 418 | 13统一传输 | 216 |
| 06运行支撑服务 | 464 | 14传输服务 | 247 |
| 07报文处理 | 317 | 15实时传输 | 193 |
| 08数据运维管理 | 399 | 16流媒体传输 | 212 |

**chunk样例**：
```json
{
  "doc": "01数据获取转换分系统需求规格说明-终稿",
  "chunk_id": "01数据获取转换分系统需求规格说明-终稿_T0015_0",
  "type": "text",
  "section": "1.2.2",
  "text": "数据转换根据某典型应用的数据使用需求，提供对引接获取的数据进行预处理...",
  "text_level": 0, "page": 1, "anchor": "", "meta": {"level": 0}
}
```

### 1.3 知识图谱构建 (LightRAG + kimi-k2.6)

#### 1.3.1 实体抽取配置

- **模型**：kimi-k2.6（moonshot API），`thinking: {"type": "disabled"}` 加速
- **格式**：`entity_extraction_use_json=True`（JSON结构化输出，比delimiter格式稳定）
- **性能**：约7.3s/chunk（vs GLM-5.2的16s，快2.2倍）
- **超时**：`default_embedding_timeout=600`（默认60s不够，MPS上embedding慢）
- **关键坑**：macOS上LightRAG内置chunker死锁 → 改用`ainsert_custom_chunks`（我们自己的结构化chunks）

#### 1.3.2 中文领域实体类型guidance（替换默认英文）

```
使用以下类型对每个实体分类。若无合适类型, 使用`其他`。
- 软件功能: 系统提供的功能/操作/服务(如创建服务工程、数据采集)
- 需求编号: 需求标识符(如PZXQ-GN-FWKFZC-CJFWGC)
- 接口: 系统接口(如数据获取接口、统一访问接口)
- 数据项: 数据/参数/字段(如工程名称、文件大小、波特率)
- 硬件设备: 物理设备(如服务器、终端、采集设备)
- 软件系统: 软件系统/子系统(如服务集成框架、数据获取分系统)
- 单位: 度量单位(如MB、ms、Mbps)
```

**效果对比**（同一chunk "3.2.1 创建服务工程"）：
- 默认英文类型（organization/person/geo...）→ GLM返回空实体
- 中文领域类型 → 6实体+5关系（创建服务工程/工程管理界面/工程名称/工程描述/用户/服务工程）

#### 1.3.3 图谱规模（13/16份文档索引完成）

| 指标 | 数值 | 每文档平均 |
|------|:---:|:---:|
| 向量chunks | 4067 | 313 |
| 实体 | **11872** | 913 |
| 关系 | **23449** | 1804 |
| 图谱节点/边 | 11872 / 23449 | — |

**实体名样例**（01号文档）：`数据获取` `数据转换` `结构化数据归集` `流式数据引接` `某数据中台` `数据保障人员` `工程管理界面`...

### 1.4 多模态图片理解 (tools/vlm_image_analyzer.py)

#### 1.4.1 方法

kimi-k2.6视觉API批量分析379张SRS图片，prompt：

```
你是SRS软件需求规格说明文档的图表分析专家。请分析这张图, 输出JSON:
{"figure_type": "图类型(用例图/接口图/流程图/状态图/时序图/架构图/数据流图/其他)",
 "key_elements": ["图中的关键元素列表(参与者/功能名称/接口名称/状态名称等)"],
 "summary": "一句话总结图的内容(50字内)"}
```

#### 1.4.2 图类型分布（379张）

| 图类型 | 数量 | 占比 |
|--------|:---:|:---:|
| 用例图 | 158 | 41.7% |
| 流程图 | 138 | 36.4% |
| 架构图 | 28 | 7.4% |
| 数据流图 | 25 | 6.6% |
| 活动图 | 17 | 4.5% |
| 状态图 | 5 | 1.3% |
| 接口图 | 4 | 1.1% |
| 其他混合 | 4 | 1.1% |

#### 1.4.3 工程可靠性机制

- **3次重试 + 5s退避**（API失败自动重试）
- **断点续跑**：按`image_path`去重，已分析的不重复调用
- **双层合并**：`_save()`同时合并磁盘已有结果+本次新增（修复了覆盖丢失bug）
- **结果**：379张0失败，1张"未知"

#### 1.4.4 分析质量样例

```json
{"figure_type": "架构图",
 "key_elements": ["数据获取转换服务", "数据获取", "数据转换", "结构化数据归集", "半结构化数据归集", "非结构化数据归集", "流式数据引接", "数据组织管理", "数据订阅推送"],
 "summary": "数据获取转换服务的功能架构图，包含数据获取与数据转换两大模块及其子功能。"}
```

**关键价值**：图片中的"结构化数据归集"与正文中的同一实体——**图文实体对齐**的证据。

### 1.5 数据资产全景

| 资产 | 规模 | 用途 |
|------|------|------|
| srs_chunks.json | 5231条 | 检索对象/评测标注 |
| srs_image_analyses.json | 379张 | 多模态关联 |
| lightrag_store/ | 11872实体+23449关系 | 语义召回 |
| id_document_graph.json | 2181节点(568实体+1613mention) | ID硬桥召回 |
| retrieval_evalset.json | 300查询对 | 检索评测 |
| multimodal_qa_evalset.json | 48图文QA | 端到端评测 |
| syntax_detections.json | 112条 | 语法层检测 |
| logic_detections.json | 5条 | 逻辑层检测 |

---

## 二、召回层：双图融合聚合器 (方向A核心)

### 2.1 设计动机

先有Agentic RAG（Planner-Researcher-Aggregator + LLM工具调用），评测暴露问题：

| 问题 | 表现 |
|------|------|
| 效率低 | 每次查询全库扫描 O(条目数) + LLM调用 |
| 不可复现 | LLM工具调用结果随机 |
| 名称→ID跳脆弱 | 依赖正则从snippet提取ID，文本排版一变就断 |

**收敛为**：预计算索引 + 确定性多路查询。

### 2.2 四通道召回（详细算法）

#### 通道① ID-Graph硬桥 (channel_id_graph)

**数据源**：`id_document_graph.json`（2181节点 = 568实体E_ + 1613 mention M_ + appearance边）

**构建索引**：
```python
def _build_id_graph_index(self):
    for e in self.id_edges:
        if e["source"].startswith("E_") and e["target"].startswith("M_"):
            ent_id = e["source"][2:]
            self.entity_mentions[ent_id].append(self.id_nodes[e["target"]])
            # 从mention context反向提取原始ID
            idm = ID_RE.search(node["context"])
            self.entity_ids[ent_id] = idm.group(0)
```

**mention位置类型分布（1613个）**：

| location | 数量 | 含义 |
|----------|:---:|------|
| text | 561 | 正文段落 |
| table_capability | 465 | 能力标识表 |
| table_unknown | 193 | 未分类表格 |
| table_interface | 150 | 接口需求表 |
| table_traceability | 114 | 追溯表 |
| table_qualification | 110 | 合格性规定表 |
| table_usecase | 20 | 用例描述表 |

**查询**：`entity_mentions[entity_id]` 哈希直查 → 全部mention位置。
**特性**：GJB需求ID是全局唯一锚点 → **零误报确定性关联**。
**局限**：只对含ID查询有效（300条评测仅3条含ID）；mention context平均仅46字符。

#### 通道② LightRAG语义图 (channel_lightrag)

**匹配算法**：双向子串包含（名称变体召回）
```python
if name.lower() in ent_name.lower() or ent_name.lower() in name.lower():
    chunk_ids.extend(ent_data["chunk_ids"])
```

**关系邻居**：从`full_relations`找src/tgt含name的关系对。
**优势**：语义泛化（中英/缩写/变体，如"数据获取"="Data Acquisition"）。
**局限**：子串噪声大（实体"分系统"命中所有含"分系统"的chunk）；关系存储结构按文档名组织，与代码按关系ID遍历错配（邻居召回实际空转）。

#### 通道③ VLM图片匹配 (channel_images)

```python
for a in img_analyses:
    elements = a["analysis"]["key_elements"]
    if any(name.lower() in str(e).lower() or str(e).lower() in name.lower() for e in elements):
        results.append({...})
```
**价值**：图片变成可检索对象——"结构化数据归集"在架构图中命中即召回该图。

#### 通道④ 结构化chunks匹配（三层判定）

```python
for c in struct_chunks:
    c_text = c["text"]
    hit = False
    if name in c_text or (entity_id and entity_id in c_text):
        hit = True                        # ① 实体名/ID精确子串
    elif kw and len(kw) >= 2 and all(k in c_text for k in kw[:2]):
        hit = True                        # ② 关键词回退(前2词同时出现)
    if hit:
        occurrences.append({location: c["type"], section: c["section"], ...})
```

**关键词提取**：
```python
keywords = [part for part in re.split(r"[的、和与及,，。;；]", name)
            if len(part) >= 2 and part not in stopwords]
```

### 2.3 融合与聚合条目

```
四通道结果
    → 去重(按 location + section + snippet前30字)
    → 位置分类(text_table/figure/trace/other)
    → chain_completeness = |{text_table, figure, trace} ∩ loc_set| / 3
    ▼
聚合条目 = {
  entity, entity_id,
  occurrences: [{location, section, snippet, doc, source}],
  locations: [...],
  chain_completeness: 0-1
}
```

**chain_completeness 计算示例**：
- 实体"创建服务工程"召回：text(3.2.1.1) + table(3.2.1) + figure(用例图)
- loc_set = {text_table, figure}
- chain_completeness = |{text_table, figure, trace} ∩ {text_table, figure}| / 3 = 2/3 = **0.67**
- 若还召回追溯表：3/3 = 1.0

### 2.4 名称清洗（多轮正则）

```python
for _ in range(4):
    cleaned = re.sub(
        r"(主要)?(是)?(用来|用于)?(做什么的|干什么的|做什么|干什么|...|"
        r"这个功能在文档的哪个章节有详细说明|在文档哪些位置被提到|"
        r"包含哪些子功能或者模块|这个概念|在哪个章节|在哪里)$",
        "", name).strip()
    if cleaned == name: break
    name = cleaned
```

**示例**：
- "查询收件箱和发件箱接口主要是用来做什么的" → 清洗后 "查询收件箱和发件箱接口"（+关键词回退匹配）
- "数据库会话监控包含哪些子功能或者模块" → "数据库会话监控"

### 2.5 评测结果（300条查询对）

#### 2.5.1 指标定义与计算公式

| 指标 | 公式 | 说明 |
|------|------|------|
| entity_found | `1 if (实体名∈结果 or ID∈结果) else 0` | 实体是否被找到 |
| section_recall | `|期望章节 ∩ 结果章节| / |期望章节|` | 章节命中率 |
| loc_recall | `|期望位置类型 ∩ 结果位置类型| / |期望位置类型|` | 位置类型覆盖率 |
| avg_recall | `(entity_found + section_recall + loc_recall) / 3` | 综合 |

**计算示例**（查询"查询收件箱和发件箱接口..."，期望sections=[3.3.1,3.3.5,3.3.5.1,3.3.5.4,4]）：
- M5 fusion召回到 [3.3.1,3.3.5,3.3.5.1,3.3.5.4,4,1.8.2.3,...]
- section_recall = 5/5 = 1.0
- 期望locations=[table,text]，M5命中{table,text} → loc_recall = 2/2 = 1.0
- entity_found = 1.0（实体名在输出中）
- avg_recall = (1.0+1.0+1.0)/3 = 1.0

#### 2.5.2 总体结果（300条）

| 方法 | entity_found | section_recall | loc_recall | **avg_recall** | 耗时/查询 |
|------|:---:|:---:|:---:|:---:|:---:|
| M1 naive (纯向量) | 0.467 | 0.305 | 0.959 | 0.577 | 0.04s |
| M2 local (图谱邻域) | 0.513 | 0.461 | 0.980 | 0.652 | 0.50s |
| M3 mix (图+向量) | 0.520 | 0.457 | 0.984 | 0.654 | 0.52s |
| M4 ID-Graph (ID硬桥) | 0.000 | 0.000 | 0.000 | 0.000 | 0.00s |
| **M5 双图融合(Ours)** | **1.000** | **0.500** | 0.926 | **0.809** | **0.01s** |

**M5 vs M3 提升计算**：0.809 - 0.654 = **+0.155 (+15.5个百分点)**；速度提升 0.52s/0.01s = **52倍**。

#### 2.5.3 结果解读与警示（论文必须正视）

1. **M5的entity_found=1.0结构性必中**：M5输出自带`entity`字段，`eval_recall`的`combined = " ".join(texts) + result_text`必然含实体名。M1-M3是chunk文本，实体名分散出现（如"查询收件箱接口"与"查询发件箱接口"分开）整串不命中。
2. **M4得0分是评测设计缺陷**：300条查询仅3条含ID(1%)，ID方法无测试场景；且`ID_RE=[A-Z]{2,8}`首段限8字符，`ZZSJHQZHFW-JK-NB`(10字符前缀)连自身目标场景都匹配失败。
3. **loc_recall对文本方法送分**：文本方法只要出现"图"字/“表格”字就算命中（中文文档几乎必现），M1-M3的0.96+区分度≈0。
4. **循环评估**：期望由同一matcher生成——"用自己的索引确认自己"。

---

## 三、评测集构建（LLM生成 + 确定性标注）

### 3.1 检索评测集 (tools/gen_retrieval_evalset.py)

#### 3.1.1 采样策略（100实体, seed=42）

```
60% (60个) 有ID实体 ← ID-Graph entity_mentions
    - 从mention context正则 <p>([^<]{2,30})</p> 提取中文名
    - 期望标注最可靠(有ID锚点)
40% (40个) 语义实体 ← LightRAG中文实体
    - 3~20字, 排除"数据获取/分系统/系统"等泛词
    - 测纯语义召回
```

**实际采样样例**：
| 实体 | ID | 来源 |
|------|-----|------|
| 查询收件箱和发件箱接口 | PZXQ-WBJK-WDCLFW-RJJH-CXSF | ID-Graph |
| 服务运行控制 | PZXQ-GN-FWYXKZ | ID-Graph |
| 表格显控展现 | (无) | LightRAG |
| 统一接收处理 | (无) | LightRAG |

#### 3.1.2 LLM查询生成（kimi, 3种问法/实体）

```
prompt = f"""请为实体"{entity}"生成3个不同的中文检索查询问题, 覆盖:
1. 功能定义型(问它是什么)
2. 结构型(问它的子功能/组成)
3. 溯源型(问它在文档哪里出现)
要求: 自然口语化, 每个一行, 不要编号。"""
```

**实际生成样例**（实体"查询收件箱和发件箱接口"）：
1. "查询收件箱和发件箱接口主要是用来做什么的"
2. "查询收件箱和发件箱接口里面包含哪些具体的功能模块或者子接口"
3. "查询收件箱和发件箱接口在需求文档的哪个章节或者哪个部分有详细描述"

#### 3.1.3 期望召回标注（三通道确定性合并）

```python
def annotate_expected(matcher, entity, entity_id):
    expected = {"chunks": [], "sections": [], "locations": set(), "docs": set()}
    # ① 结构chunks字符串匹配
    for c in matcher.struct_chunks:
        if entity in c["text"] or (entity_id and entity_id in c["text"]):
            expected["chunks"].append(c["chunk_id"]); expected["sections"].append(c["section"])
            expected["locations"].add(c["type"]); expected["docs"].add(c["doc"])
    # ② ID-Graph mentions
    if entity_id:
        for m in matcher.channel_id_graph(entity_id):
            expected["sections"].append(m["section"]); expected["locations"].add(...)
    # ③ VLM图片
    for img in matcher.channel_images(entity):
        expected["locations"].add("figure")
    return {...}
```

**样例**（q_0000, hard难度）：
```json
{"id": "q_0000", "query": "查询收件箱和发件箱接口主要是用来做什么的",
 "entity": "查询收件箱和发件箱接口", "entity_id": "PZXQ-WBJK-WDCLFW-RJJH-CXSF",
 "expected": {"chunk_ids": ["12文电处理..._T0103", "..._T0143_0", "..._T0145_0", "..._T0146", "..._T0153"],
              "sections": ["3.3.1", "3.3.5", "3.3.5.1", "3.3.5.4", "4"],
              "locations": ["table", "text"],
              "docs": ["", "12文电处理需求规格说明-终端"]},
 "difficulty": "hard"}
```

#### 3.1.4 难度标注公式

```python
difficulty = "easy" if len(expected["sections"]) <= 2 else "hard"
```

**分布**：easy 78 (26%) / hard 222 (74%)；期望位置类型：table 276 / text 273 / figure 222（多模态覆盖）

### 3.2 多模态QA对 (tools/gen_multimodal_qa.py)

#### 3.2.1 生成流程

```
① 采样48张 (seed=42, 从379张中过滤有key_elements的)
② kimi看图生成QA对
   - 真实图片base64 → image_url传入(视觉模态)
   - prompt要求"问题必须只能通过看图才能回答"
   - response_format=json_object
③ 图片存在性校验: os.path.exists逐一验证 → 48/48通过
```

#### 3.2.2 QA样例（质量展示）

```json
{"id": "mm_0001", "doc": "01数据获取转换分系统...",
 "image_path": "data/gjb_438c/mineru_standard/01.../office/images/fig_009.png",
 "figure_type": "用例图", "caption": ["图 9 数据转换用例图"],
 "question": "在图9数据转换用例图中，参与者'数据保障人员'与用例'数据转换'边界内的四个用例之间的关联关系有何共同特征？",
 "answer": "数据保障人员与数据结构转换、典型应用专题库管理、数据组织发布、数据订阅推送四个用例均采用直接关联线（实线）连接，且均为单向发起关系...",
 "difficulty": "medium"}
```

**验证**：问题确实需要看图才能回答（涉及图中连线/参与者关系）。

### 3.3 评测指标计算细节 (tools/eval_retrieval.py)

```python
def eval_recall(result_text, expected, entity_name=""):
    # 结构化输出(fusion/id_graph)解析occurrences的section/location
    # 文本输出(M1-M3)启发式: 含"表格"/<table → table; 含"图" → figure; 前100字符含字母 → text
    avg = (entity_hit + sec_hits / n_sec + loc_hits / n_loc) / 3
    return {"entity_found", "section_recall", "loc_recall", "avg_recall"}
```

---

## 四、语义层数据集构建 (方向B检测对象)

> 语义层 = 检测"同一参数/概念在不同位置的值/含义是否一致"，如正文与表格矛盾、同实体不同名称。
> 数据集 = 不一致性Gold Standard（负例=矛盾，正例=一致）+ 对应的检测评测框架。

### 4.1 总体结构：3场景 Gold Standard (multi_scene_gold_standard.json)

**223条 = 170负例(矛盾) + 53正例(一致)**

| 场景 | 负例 | 正例 | 检测对象 | 子类型分布 |
|------|:---:|:---:|---------|-----------|
| scene1 名称不一致 | 122 | 23 | 同一需求ID在不同位置的名称 | typo24 / multiname34 / truncation26 / semantic_conflict15 / charorder23 |
| scene2 异常流 | 28 | 20 | 用例图的异常流描述 | dangling_exception 8 / dead_exception 20 |
| scene3 接口属性 | 20 | 10 | 接口属性跨位置矛盾 | interface_attr_conflict |

**来源构成**：real真实矛盾79 + injected注入91
**难度分层**：easy 113 (50.7%) / medium 22 (9.9%) / hard 35 (15.7%)
**划分**：train 98（文档01-08）/ test 125（文档09-16）——**按文档划分防止数据泄漏**

### 4.2 scene1 名称不一致（核心场景）构建方法

#### 4.2.1 构建流程

```
① ID-Graph构建 (tools/id_graph.py)
   - 正则 [A-Z]{2,8}(-[A-Z0-9]{2,8}){2,} 提取需求ID
   - ID → 所有mention位置(8类: 正文/能力表/接口表/合格性表/追溯表/用例表)
   - 产出: 2181节点(568实体+1613mention) + appearance边

② 实体名称提取 (algorithms/common/load_entity_names)
   - 同一ID每个mention提取名称(正则从context提取)
   - 过滤出现<2次的ID → 508实体
   - 产出: entity_id → {名称集合}
     例: PZXQ-GN-JMJCKJ-JMJC-KJCK → {快捷操控(1.8.3.4), 触摸操控(1.8.5.4)}

③ 矛盾标注
   - real: 同一ID出现≥2个不同名称 → 双源+双模型确认为矛盾(31个)
   - injected: 选取一致实体, 注入5种子类型名称
     · typo错字: "触摸操控"→"触摸操拄"
     · multiname: 一名多用/多名一用
     · truncation: 名称截断("服务工程创建"→"服务工程")
     · semantic_conflict: 语义冲突("允许"vs"禁止"同操作)
     · charorder字序: "数据获取"→"获取数据"

④ 双重质量验证 (见4.5)
```

#### 4.2.2 负例样例

```json
{"scenario": 1, "type": "name_inconsistency", "subtype": "typo",
 "entity_id": "PZXQ-GN-JMJCKJ-JMJC-KJCK", "doc": "02界面集成框架软件需求规格说明-终稿",
 "correct_name": "快捷操控", "wrong_names": ["触摸操控"],
 "difficulty": "easy", "source": "real"}
```

### 4.3 描述级数据集 (desc_full_entries → sc1_desc_full_samples)

**动机**：名称级矛盾本质是"字符级可解"（对比实验Ours≡B1_char，见5.1-V7），需要更难任务——**描述级一致性**（名称相同但描述矛盾）。

#### 4.3.1 构建流程

```
① desc_full_entries.json (273条)
   - 从16份文档提取capability全量描述条目 {name, desc, doc}
   - 每条 = 功能名 + 其完整描述文本

② sc1_desc_full_samples.json (546条 = 273正 + 273负)
   - 正例: 273条原始条目(描述一致)
   - 负例: 对每条描述做单点扰动(修改一个参数/行为)
     · "支持FTP" → "不支持FTP"
     · "响应时间≤100ms" → "响应时间≥100ms"
     · "支持加密" → "不支持加密"
   - 难度: hard为主(描述级语义判断比名称级难)
```

**样例**：
```json
{"name": "界面开发功能",
 "desc": "提供包括界面开发模板、二次开发接口、公共组件库、依赖文件、打包编译工具的界面开发环境。",
 "label": "consistent", "source": "real", "difficulty": "hard",
 "type": "desc_consistency"}
```

### 4.4 scene2/scene3 构建方法

**scene2 异常流**（28负+20正）：
```
- 从用例描述中提取异常流引用(E1/E2/...)
- dangling_exception(8): 引用了不存在的异常流编号
  · 例: "系统安装包维护"用例引用E1, 但文档中无E1定义
- dead_exception(20): 异常流存在但从未被任何用例引用
- 验证: 与文档用例图/用例描述交叉核对
```

**scene3 接口属性**（20负+10正）：
```
- 从接口描述中提取属性(发送方/接收方/类型/方向)
- 同一接口在不同位置属性值矛盾
- 例: 态势数据组织应用接口, 接收方在3.3.1是"高"、3.3.4.1是"中" → 矛盾
```

### 4.5 语义层质量验证指标计算

| 验证 | 方法 | 结果计算 |
|------|------|---------|
| V1 双源交叉 | MinerU+textutil独立解析 | 31/31 = 100% |
| V2 双模型标注 | kimi+claude独立判断132对 | 122/132 = **92.4%** |
| V3 VLM-OCR | tesseract独立OCR | 453/870 = 52%支持, 抽样10/10无幻觉 |
| V5 语法×GS交叉 | S2重复ID vs GS矛盾实体 | 8/15 = 53.3%命中 |
| V6 评测协议v2 | 防假高分层+holdout | 115/118 = **97.5%** |
| V7 基线对比 | vs B1_char字符级 | F1完全相同0.969 |

**V7指标计算**（名称级检测）：
```
P = TP/(TP+FP) = 0.959, R = TP/(TP+FN) = 0.979
F1 = 2PR/(P+R) = 2×0.959×0.979/(0.959+0.979) = 0.969
Ours与B1_char四项指标完全相同 → 名称级问题字符级可解
```

**关键警示（V7）**：名称级检测与字符级基线无差异——论文创新必须转向**描述级**(4.3)或**逻辑级**(4.6)才有区分度。

### 4.6 逻辑层检测对象（专家知识+知识图谱）

```
L1 参数约束冲突: 专家词典(23参数+4硬件参数)识别 → 区间交集 → 矛盾
   · 检出: "存储" 下界256GB > 上界56GB (同一表格内, 4条约束)
L2 允许/禁止矛盾: 规则初筛 → kimi LLM语义验证(消除语境差异误报)
   · 候选2条均判定为"语境差异" → 0误报
L3 阈值越界: 文档取值 vs 专家词典值域
   · 检出: 存储8GB低于词典下限10GB 等4条
```

**L1检测算法**：
```python
def _interval_of(cons):
    lo, hi = -inf, +inf
    for con in cons:
        if con["op"] in ("ge", "gt"): lo = max(lo, con["value"])
        elif con["op"] in ("le", "lt"): hi = min(hi, con["value"])
        elif con["op"] == "eq": lo = max(lo, v); hi = min(hi, v)
    return (lo, hi) if lo <= hi else None  # None = 矛盾(无可行解)
```

**L1矛盾判定示例**（"存储"参数, 4条约束）：
- 约束: eq 56GB, ge 1TB, eq 256GB, eq 256GB
- 归一化后区间: lo = max(56, 1024, 256, 256) = 1024, hi = min(56, 1024, 256, 256) = 56
- lo(1024) > hi(56) → **矛盾** ✓

**语义层与方向A的关系**：
```
方向A(聚合条目) → 方向B(检测)
  聚合出实体所有位置 → 名称/描述/属性/约束跨位置对比
  如: KJCK实体聚合出{快捷操控(1.8.3.4), 触摸操控(1.8.5.4)}
      → 检测层判定名称不一致 ✓
```

---

## 五、质量保证体系

### 5.1 不一致性Gold Standard的三重互证

| 验证 | 方法 | 结果 | 局限 |
|------|------|------|------|
| V1 双源交叉 | MinerU+textutil独立解析 | 31/31=100% | 只验证"都存在且不同", 不验证"同一事物" |
| V2 双模型标注 | kimi+claude独立判断 | 92.4%(122/132) | 共享训练偏误未被检验 |
| V3 VLM-OCR | tesseract独立OCR | 10/10无幻觉 | 10/10抽样外推417个"潜在幻觉" |
| V6 评测协议v2 | 防假高分层+holdout | 综合97.5% | hard仍100%→标定失效 |
| V5 语法×GS交叉 | S2重复ID vs GS实体 | 8/15=53.3%命中 | 覆盖不全(39个GS ID仅8个被S2覆盖) |
| V7 基线对比 | vs B1_char | 完全相同F1=0.969 | **名称级问题字符级可解** |

### 5.2 检索评测集的质量风险（新体系）

| 风险 | 说明 | 修复方向 |
|------|------|---------|
| 循环评估 | 期望由matcher自己生成, "自我确认" | 用textutil独立解析生成期望 |
| 指标偏向 | entity_found/loc_recall对文本方法送分 | 结构化证据匹配 |
| M4错配 | ID方法无ID测试场景 | 分层报告+扩充含ID查询 |
| 无人类仲裁 | 全链无需求工程师介入 | 人工抽检+Kappa≥0.8 |

### 5.3 已验证的质量成果（对照原文）

- 语法层S2检出`PZXQ-GN-JMJCKJ-JMJC-KJCK`重复定义 → **正是Gold Standard矛盾对**(快捷操控/触摸操控)
- 逻辑层L1检出"存储256GB vs 56GB" → 同表内真实矛盾
- 多模态QA 48/48图片存在
- 图片分析379张0失败
- 语法层112条 = S1(1) + S2(15) + S4(90) + S5(5) + S7(1)

---

## 六、技术演进与已知局限

### 6.1 演进路线

```
v1 Agentic RAG (Planner-Researcher-Aggregator)
    → 问题: 慢(全库扫描)/不可复现(LLM)/名称跳脆弱
v2 双图融合 (KGContextMatcher 4通道)
    → 解决: 预计算索引(0.01s)/确定性(可复现)/构建期ID桥
v3 (规划) 评测公平性修复 + 跨文档召回
```

### 6.2 已知局限（8项）

1. **名称清洗正则脆弱**：依赖问句模板穷举，未覆盖句式导致实体名含噪
2. **向量通道死代码**：`channel_vector`未接入aggregate（声称4通道实为3.5通道）
3. **section缺失**：VLM通道section硬编码空；表格chunk反查可能返回空
4. **跨文档召回未评测**：expected.docs从未参与计算
5. **chain_completeness缺陷**：location归一化只认精确"trace"，`table_traceability`落入other
6. **ID正则限制**：`[A-Z]{2,8}`首段限8字符，长前缀ID漏检
7. **LightRAG邻居召回结构错配**：full_relations按文档名组织，代码按关系ID遍历
8. **API key硬编码**：4个脚本含同一moonshot key

### 6.3 下一步（P0优先级）

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
| algorithms/semantic/scene1/detectors.py | 方向B语义检测器(7种图方法) |
| algorithms/syntax/syntax_checker.py | 语法层校验 |
| algorithms/logic/logic_checker.py | 逻辑层校验(专家知识+LLM) |
| algorithms/common/__init__.py | 共享工具(load_entity_names/load_gold_conflicts) |
| tools/srs_chunker.py | 结构化切片器 |
| tools/vlm_image_analyzer.py | VLM图片分析 |
| tools/gen_retrieval_evalset.py | 检索评测集生成 |
| tools/gen_multimodal_qa.py | 多模态QA生成 |
| tools/eval_retrieval.py | 5方法评测 |
| tools/id_graph.py | ID-Graph构建 |
| data/gjb_438c/data_assets/ | 所有数据资产 |
| data/gjb_438c/data_assets/gold_standard/ | 语义层Gold Standard(223条主GS+描述级546) |
| data/gjb_438c/data_assets/retrieval_evalset.json | 300查询对(方向A评测) |
| data/gjb_438c/data_assets/multimodal_qa_evalset.json | 48图文QA(端到端) |
