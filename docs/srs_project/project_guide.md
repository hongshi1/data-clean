# GJB SRS数据一致性校验项目指导文档

> 版本：v3.0 | 日期：2026-08-12
> 状态：四类不一致框架确立 + Pair Dataset重建(366实例) + QA数据集(6189条)
> 数据源：16份真实GJB 438C SRS + MinerU标准解析 + 温老师会议反馈
> 更新: 根据温老师8/12会议反馈, 项目范围聚焦四类不一致合规

---

## 项目全貌（v3.0 更新）

```
输入: SRS文档(16份) + 问答对(含{image}/{table}/{text}占位符) + 专家知识(规则形式)
  ↓
问题 → 上下文召回(从SRS文档召回相关的图+表+正文)
  ↓
四类不一致校验:
  1.术语层面: 同名实体/多实体映射 (图/表/文功能名一致性)
  2.参数指标: 参数/单位/数字一致 (接口属性/数值/单位对比)
  3.业务逻辑: 时序/流程一致 (流程图步骤vs正文/表描述)
  4.GJB合规: 模板/接口定义规范 (表头字段/ID格式/章节结构)
  ↓
输出: 四类一致性校验结果(每类含issues列表, 每个issue含类型/证据/修复建议)
```

### 输入输出格式（v3.0 更新）

**输入（问答对，含多模态占位符）**：
```json
{
  "id": "qa_0001_01",
  "inconsistency_type": "terminology",
  "label": "inconsistent",
  "is_injected": true,
  "question": "表{table}中功能「结操化数据归集」与图{image}中的用例名称是否一致？",
  "placeholders": {
    "image": "data/.../image.png",
    "table": "data/.../table.csv",
    "text": "data/.../text.txt"
  },
  "answer": "不一致。图中为「结构化数据归集」，表中写为「结操化数据归集」，第2字错字。",
  "evidence": {"image_caption": "图3...", "table_caption": "表3...", "section": "3.2.1.2"}
}
```
```

**输出（一致性校验结果）**：
```json
{
  "id": "case_001",
  "consistency_results": {
    "syntax": {"status": "pass", "issues": []},
    "semantic": {
      "status": "fail",
      "issues": [{
        "type": "version_conflict",
        "description": "回答称达梦V7.6，但文档3.10.3软件清单表标注V7.2",
        "evidence": {"recall_sections": ["3.9.1", "3.10.3"],
                     "doc_values": [{"section":"3.9.1","value":"V7.6"},
                                    {"section":"3.10.3","value":"V7.2"}]},
        "resolution": "回答应说明3.9.1运行环境与3.10.3软件清单的版本不一致"
      }]
    },
    "logic": {"status": "pass", "issues": []}
  }
}
```

---

## 一、数据集

### 1.1 SRS文档

- 16份GJB 438C SRS，MinerU正确解析（content_list.json）
- 数据路径：`data/gjb_438c/mineru_correct/`
- 文档结构共性：6大章 + 3.1~3.18标准18节 + 15种表型 + 7种图型
- 总量：329张图片 + 1119张表格 + 1029个需求ID + 33组版本对(9组冲突) + 433张用例表(87个悬空引用)

**3个离群点**：

| 文档 | 离群特征 | 影响 |
|------|----------|------|
| doc01(数据获取转换) | 不同ID前缀(ZZSJHQZHFW) + 3.7/3.8语义对调 + 章节标题用旧版GJB 438B命名 | 需按标题语义而非编号对齐 |
| doc11(语音综合处理) | 3.1被误编为3.3(编号bug) → 3.3出现2次、3.1缺失、3.8保密性整节缺失 | 编号断裂 |
| doc05(软件部署管理) | 缺3.1"要求的状态和方式" | 3.1在14/16中存在 |

**表格类型分布（15种）**：

| 表型 | 数量 | 占比 | 所在章节 |
|------|------|------|---------|
| 用例表(usecase) | 442 | 39.5% | 3.2.x |
| 追踪表(traceability) | 166 | 14.8% | 第5章 |
| 数据规格表(data_spec) | 149 | 13.3% | 3.3/3.4/3.5 |
| 其他表(other) | 80 | 7.1% | 3.1/3.9/3.10/3.12 |
| 数据约束表(data_constraint) | 69 | 6.2% | 3.3/3.4 |
| 接口表(interface) | 58 | 5.2% | 3.3.1/3.4.1 |
| 环境表(environment) | 29 | 2.6% | 3.10 |
| 软件清单表(software_list) | 26 | 2.3% | 3.10 |
| 设计约束表(design_constraint) | 20 | 1.8% | 3.3/3.4 |
| 合格性表(qualification) | 16 | 1.4% | 第4章 |
| 引用文档表(reference) | 14 | 1.3% | 第2章 |
| 质量表(quality) | 14 | 1.3% | 3.6 |
| 支持表(support) | 14 | 1.3% | 3.12 |
| 培训表(training) | 12 | 1.1% | 3.12 |
| 能力标识表(capability) | 10 | 0.9% | 3.2.x |

**图片类型分布（7种）**：

| 图型 | 数量 | 占比 | 所在章节 |
|------|------|------|---------|
| 用例图 | 134 | 40.7% | 3.2.x |
| 流程图 | 125 | 38.0% | 3.2.x |
| 接口图 | 29 | 8.8% | 3.3/3.4 |
| 其他 | 13 | 4.0% | 各处 |
| 活动图 | 13 | 4.0% | 3.1.2 |
| 功能图 | 13 | 4.0% | 3.2 |
| 功能框架图 | 2 | 0.6% | 3.2.x.1 |

> 注：329张图片全部有caption（HD替换后从Visio OLE对象提取）。

### 1.2 问答对（已生成）

- **格式**：`{id, instruction, output, label, layer, inconsistency_type, evidence}`
- **总量**：2170条（原生1221 + 增强946 + 多模态3）
  - **原生QA对**（1221条，来自16份GJB SRS，8场景多模态）：
    - 正例592 / 负例629
    - 场景分布：0:188 / 1:691 / 2:173 / 3:54 / 4:54 / 5:14 / 7:18 / 8:29（8场景全覆盖）
    - 负例类型：name_inconsistency(376) + dangling_exception(117) + qualification_mismatch(91) + interface_type_mismatch(27) + image_caption_mismatch(14) + version_conflict(4)
    - 三层：semantic 850(正429/负421) / logic 191(正74/负117) / syntax 180(正89/负91)
    - image_path完整：除sc0(纯文本)外全部100%覆盖
  - **增强QA对**（946条，来自4个外部数据集）：
    - ContractNLI 546条（正432/负114）— 合同NLI，场景0(纯文本)
    - Fault-prone SRS 200条（正49/负151）— 需求歧义，场景0(纯文本)
    - FinBalance 200条（正100/负100）— 会计不一致，场景0(纯文本)
    - ScholScan 3条（正2/负1）— 学术论文，场景6/8(内容级多模态)
  - **场景0(纯文本)**：946条外部数据，无图片/表格模态
  - **场景1-8(多模态)**：1221条原生（8场景全覆盖，caption级+image_path） + ScholScan 3 内容级
  - **8场景定义(按精确模态组合)**：sc1用例图+capability表 / sc2流程图+usecase表 / sc3接口图+interface表 / sc4流程图+capability表 / sc5功能图+capability表 / sc6功能框架图+其他表 / sc7用例图+usecase表 / sc8纯图片+正文
  - **数据集划分**：train 832条(文档01-08) / test 389条(文档09-16)，0指令跨split泄漏
- **正负比**：1:0.85（正1175/负995）
- **设计原则**：外部数据正负例output统一(不泄露标签)，模型必须查文档判断claim是否成立
- **警示**：负例必须人工验证（Korn 2026, arXiv:2606.25550 证明LLM无法可靠生成requirement smells）
- **数据路径**：`data/gjb_438c/data_assets/native_qa_pairs.json` + `external_qa_pairs.json` + `external_multimodal_qa.json`

### 1.3 专家知识

| GJB标准 | 内容 | 当前状态 | 对检测层的贡献 |
|---------|------|---------|--------------|
| GJB 438C-2021 | 《军用软件开发文档通用要求》 | **已有120条规则** | 语法层(A+B类) + 逻辑层 |
| GJB 439A-2013 | 《军品软件质量保证通用要求》 | 待扩充 | 逻辑层(质量保证规则) |
| GJB/Z 102A-2012 | 《军用软件安全性设计指南》 | 待扩充 | 逻辑层(安全约束) |
| GJB 2786A-2009 | 《军用软件开发通用要求》 | 待扩充 | 逻辑层(开发流程一致性) |
| GJB 1268A-2004 | 《军用软件验收要求》 | 待扩充 | 逻辑层(合格性与验收对齐) |
| GJB 5235-2004 | 《军用软件配置管理》 | 待扩充 | 逻辑层(版本管理一致性) |
| GJB 1267-1991 | 《军用软件维护》 | 待扩充 | 逻辑层(可维护性) |

**已有资源**：
- `knowledge/gjb_438c_rules_full.json`：GJB 438C的120条规则（可追溯到OCR行号）
- `knowledge/srs_kb.json`：术语词典（23参数 + 13接口 + 10单位族）

---

## 二、上下文关联与特征提取

### 2.1 规则化关联信号（12种）

| # | 信号 | 类型 | 说明 | 数据规模 |
|---|------|------|------|---------|
| 1 | ID精确匹配 | 结构化 | 正则提取7位置ID | 标题539 + 功能表707 + 接口表211 + 合格性113 + 追踪217 + 正文351 + 表格57 |
| 2 | 追踪表章节号映射 | 结构化 | 5列追踪表的上级章节号↔本文档章节号显式映射 | 16/16份有追踪表, 2042条边 |
| 3 | 合格性表章节号桥接 | 结构化 | 合格性表"本文档章节号"→section_registry→ID | 16/16份有合格性表 |
| 4 | 正文交叉引用解析 | 结构化 | "见表X"/"如图X"/"见X节"→图号/表号/章节号索引 | doc03: 82处表引用 + 16处图引用 |
| 5 | 接口表拓扑构建 | 结构化 | 发送方/接收方→跨文档接口拓扑图 | 58个接口表, 325条接口, 10个跨文档共享ID |
| 6 | 版本跨表对齐 | 结构化 | 3.9环境表 vs 3.10软件清单表按软件名对齐 | 29个环境表 + 26个软件清单表, 33组版本对, 9组冲突 |
| 7 | 位置邻接 | 启发式 | 同一3.2.X.Y子节内的图+表+文字归属 | 329张图片全在第3章 |
| 8 | 语义相似度匹配 | 语义化 | embedding匹配回答内容与文档内容 | TODO: 接入Embedding API |
| 9 | 表格结构解析 | 结构化 | colspan/rowspan展开→行列对齐→单元格提取 | 77/115个表格含合并单元格 |
| 10 | 图片caption解析 | 结构化 | 图号索引+图片类型分类+图文引用边 | 329/329张有caption(100%) |
| 11 | 章节层级遍历 | 结构化 | 父子章节关系(3.2→3.2.1→3.2.1.1) | 16份文档, 1249个标题, 平均78个/份 |
| 12 | 跨文档ID注册表 | 结构化 | 全局ID→多文档出现位置 | 5个ID出现在2+份文档 |

### 2.2 高级召回方法（TODO - 待研究）

基于Agentic RAG前沿调研（2025-2026），以下技术可增强上下文召回：

| 方法 | 用途 | 参考工作 | 优先级 |
|------|------|---------|--------|
| **结构化文档图+在线证据子图激活** | 12种规则信号编码为图边，查询时按预算激活证据子图 | MAGE-RAG(arXiv:2606.15906), LAD-RAG(arXiv:2510.07233) | P1 |
| **VLM图片内容理解** | 理解用例图/流程图/接口图的内容，与文字描述比对 | TechRAG(arXiv:2606.01613), ColSmol视觉检索 | P1 |
| **Evidence-gated多Agent** | Planner/Researcher/Writer/Critic四Agent+证据充分性评分+drift-guarded重试 | TechRAG(arXiv:2606.01613) | P2 |
| **多跳推理+工具调用** | 回答→表格→章节号→ID→另一表格的链式追溯，Agent用search/read/link-following工具 | LLM-Wiki(arXiv:2605.25480), N2N-GQA(arXiv:2601.06603) | P2 |
| **IsConsistent判断器** | 改造Self-RAG的IsSup为"多源证据间是否一致"判断，区分合理差异vs真实矛盾 | Self-RAG(arXiv:2310.11511), Self-Correcting RAG(arXiv:2604.10734) | P2 |
| **工业标准文档原子命题分解** | 把SRS条件规则/数值约束分解为原子命题入本体KG | Industrial Standards KG(arXiv:2512.08398) | P3 |
| **Table QA模型** | TAPAS/TabFact类模型验证回答claim与表格内容的一致性 | — | P3 |
| **文档布局分析** | 理解图/表/文字的空间关系，辅助位置邻接 | DeCoRAG(arXiv:2607.24554) | P3 |

**核心创新点**：GJB SRS的12种规则关联信号是确定性、可追溯的图边源——GraphRAG的图构建从"LLM抽取(昂贵且噪声)"变成"规则产边(确定性且可追溯)"，这是相对现有Agentic RAG工作的独特优势。

### 2.3 特征提取（按表型）

| 表型 | 提取特征 |
|------|---------|
| **usecase表** | usecase_name, actors, overview, preconditions, main_flow[], exception_flows[{id, definition, triggered}], postconditions, action_constraints[] |
| **capability表** | function_name, project_id, requirement_description, reuse_type, run_modes, run_stage, task_ref |
| **interface表** | interface_id, name, type, sender, receiver, content, priority |
| **data_spec表** | dataset_name, data_composition, data_constraint |
| **环境表** | device_name, hardware_req, software_req(含版本号) |
| **合格性表** | req_section, methods{A,D,T,I,S}, level |
| **追踪表** | upstream_section, this_doc_section, note, direction |

### 2.4 聚合输出

```python
RequirementItem = {
    item_id: str,           # 规范化后的需求ID
    item_type: str,         # function|interface|parameter|version|quality
    doc_id: str,
    occurrences: [{         # 每个位置一条
        section: str,
        location_type: str, # title|func_table|interface_table|qualification|traceability
        features: dict,     # 按表型的特征schema
        evidence_snippet: str  # 原文片段
    }],
    media: [{image_id, role, confidence}],
    trace: {upstream_section, status},
    qualification: {methods, level, status},
    chain_completeness: {has_title, has_func, has_qualification, has_trace, score}
}
```

---

## 三、数据不一致检查

### 3.1 语法层（不依赖上下文，直接与GJB一对一校验）

**特点**：拿回答直接和GJB标准比对，不需要理解回答在说什么功能、引用了哪个表格。纯粹是格式/术语/编号的正则匹配和规则校验。

#### A类：正则表达式检测（一个正则 = 一个检测器）

| 检测器 | 正则 | 检测内容 | 真实例子 |
|--------|------|---------|---------|
| ID格式 | `[A-Z]{4,}-[A-Z]{2,}-[A-Z0-9-]+` | 回答中的ID格式是否规范 | 回答写"PZXQ-GN-FWGC"(层级不足) |
| ID占位符 | `X{4,}` | 回答中的ID是否含XXXX占位符 | 回答引用"...XXXX" |
| 章节号 | `^(\d+(?:\.\d+)*)\s+(.+)` | 回答引用的章节号格式 | 回答写"3.2.1"(应写"3.2.1.1") |
| 图号引用 | `(?:如图\|见图\|图)\s*(\d+)` | 回答引用的图号是否存在 | 回答"如图4所示"但图4不存在 |
| 表号引用 | `(?:如表\|见表\|表)\s*(\d+)` | 回答引用的表号是否存在 | 回答"见表37"但表37不存在 |
| caption格式 | `(图\|表)\s*(\d+)\s*(.*)` | 回答中的图表编号格式 | 回答"图3-1"(应为"图3") |
| 版本号 | `(达梦\|银河麒麟\|WPS\|Qt)[^。]*?(V?\d+\.?\d*)` | 回答中的版本号格式 | 回答"达梦7.6"(应为"达梦V7.6") |
| 约束格式 | `(?:不低于\|≥)\s*(\d+\.?\d*)\s*(unit)?` | 回答中的约束表达格式 | 回答"≥256"(缺单位) |
| 异常流定义 | `异常流\s*(E\d+)[：:]` | 回答中的异常流编号格式 | 回答"异常流E1:"(格式正确) |
| 异常流引用 | `(?:进入\|执行\|转)\s*异常流\s*(E\d+)` | 回答引用的异常流是否存在 | 回答"执行异常流E2"但E2未定义 |

#### B类：GJB标准规则校验（依赖GJB 438C规则库120条）

| 检测器 | GJB规则 | 检测内容 | 真实例子 |
|--------|---------|---------|---------|
| 章节完整性 | 3.1~3.18必须存在 | 回答引用的章节是否都在文档中存在 | 回答引用"3.8保密性"但doc11缺3.8 |
| 章节顺序 | 3.7=适应性/3.8=安全性/3.9=保密性 | 回答中的章节顺序描述是否正确 | 回答"3.7是保密性"(实际应3.7=安全性) |
| 用例表结构 | 必须含概述/前置条件/主事件流/异常流/后置条件 | 回答描述的用例结构是否完整 | 回答缺少异常流描述 |
| 追踪表完整性 | 必须有正向+逆向 | 回答是否提到逆向追踪 | 回答只提正向追踪 |
| 合格性表结构 | 必须含需求标识/章节号/方法/级别 | 回答描述的合格性信息是否完整 | 回答缺少合格性级别 |

### 3.2 语义层（依赖上下文，涉及文本+表格+图片）

**特点**：需要先召回文档中的相关多模态内容，再把回答和召回的内容做比对。

#### 8个场景

| # | 场景 | 实例数 | strong | 图片 | 表格 |
|---|------|--------|--------|------|------|
| 1 | 用例图+capability表+正文 | 120 | 99 | 用例图 | capability表 |
| 2 | 流程图+usecase表+正文 | 78 | 70 | 流程图 | usecase表 |
| 3 | 接口图+interface表+正文 | 29 | 27 | 接口图 | interface表 |
| 4 | 流程图+capability表+正文 | 49 | 34 | 流程图 | capability表 |
| 5 | 功能图+capability表+正文 | 25 | 23 | 功能图/功能框架图 | capability表 |
| 6 | 功能框架图+其他表+正文 | 1 | 0 | 功能框架图 | 其他表 |
| 7 | 用例图+usecase表+正文 | 15 | 10 | 用例图 | usecase表 |
| 8 | 纯图片+正文 | 18 | 0 | 活动图/功能图/其他 | (无表) |

> 注：另有29个unclassified实例（图片类型无法确定），全部为weak匹配。场景6实例极少（1个），因功能框架图多与capability表关联而非其他表。

#### 检测内容（待确认）

| 候选检测项 | 说明 | 真实例子 |
|-----------|------|---------|
| 名称一致性 | 回答中的功能名 vs 标题/正文/caption/表内名。例：doc03的3.2.1.6节，章节标题="服务工程编译"，但正文="服务插件编译用例场景"，表格caption="服务插件编译用例描述"，表内概述="对服务插件代码进行编译"——四个位置全部写成了"服务插件编译"，与标题的"服务工程编译"矛盾（两个是完全不同的功能，疑似复制粘贴3.2.1.5后未修改） |
| 值一致性 | 回答中的参数值/版本号 vs 文档表格值 | 回答"达梦V7.6"但3.10表写"V7.2" |
| 引用完整性 | 回答引用的表/图/章节是否存在 | 回答"见表37"但表37不存在 |
| 跨表值比对 | 回答是否同时考虑多个表格中的值 | 回答只引用3.9的V7.6未提及3.10的V7.2 |
| 图表内容对齐 | 回答描述的内容 vs 引用的图片/表格 | 回答"步骤1-5"但用例表有步骤1-9 |
| 接口描述一致性 | 回答的接口类型/发送方/接收方 vs 接口表 | 回答"API接口"但文档写"HTTP接口" |

### 3.3 逻辑层（依赖上下文，但与多模态文字内容无关，专家知识）

**特点**：需要上下文（知道问题在问什么），但检测本身不是比文字/表格/图片内容，而是用专家知识做逻辑推理。

#### 专家知识来源

| 来源 | 知识类型 | 检测内容 |
|------|---------|---------|
| GJB 438C(120条) | 文档格式/结构规则 | 章节完整性/编号连续/ID规范 |
| GJB 439A | 质量保证规则 | 合格性方法合理性(性能需求应有D测试) |
| GJB/Z 102A | 安全性设计指南 | 安全约束可满足性 |
| GJB 2786A | 开发通用要求 | 开发流程一致性 |
| GJB 1268A | 验收要求 | 合格性与验收要求对齐 |
| GJB 5235 | 配置管理 | 版本管理一致性 |
| GJB 1267 | 软件维护 | 可维护性检查 |

#### 检测内容（待确认）

| 候选检测项 | 专家知识 | 真实例子 |
|-----------|---------|---------|
| 异常流定义-引用一致性 | GJB用例表结构规则 | 回答提到E2但E2未定义 |
| 约束可满足性 | GJB约束规范 | 回答"≥3000且≤2000"(矛盾) |
| 追溯链路完整性 | GJB追溯要求 | 回答说"3.2.1.1对应任务书4.1.1"但追踪表无此映射 |
| 合格性方法合理性 | GJB 439A/1268A | 性能需求回答只有A(分析)无D(测试) |
| 版本管理一致性 | GJB 5235 | 回答的版本号与配置管理基线不一致 |

---

## 四、评测方案

| 维度 | 方案 |
|------|------|
| Gold Standard | 从真实矛盾构建：版本冲突4处 + 悬空异常流59个 + 名称不一致261条 + 接口类型矛盾23条 + 合格性章节不匹配91条(已过滤15条方法列误提取) + 幽灵引用16条 + 追溯不对称9条 |
| 语法层评测 | 二分类（合规/不合规），P/R/F1 |
| 语义层评测 | 按场景分别评测，claim三态标注（entailed/contradicted/baseless） |
| 逻辑层评测 | 二分类（有逻辑漏洞/无漏洞），P/R/F1 |
| 消融实验 | 有无上下文召回对比 / 有无图片对比 / 纯LLM vs 混合方法 |
| 数据集划分 | 原生1221条(train 832/test 389, 文档级隔离) + 增强949条(泛化测试) |

---

## 五、文献定位

| 空白 | 证据 | 我们的贡献 |
|------|------|-----------|
| SRS文档级理解不存在 | arXiv全库0条"document-level requirement" | 首个面向GJB SRS的多模态QA一致性校验 |
| LLM4RE缺陷检测从#1跌至#8 | Zadenoori 2025 SLR(74篇, arXiv:2509.11446) | 填补LLM4RE一致性检测空白 |
| GJB标准学术零覆盖 | arXiv检索"GJB"返回0条 | 首个GJB SRS QA benchmark |
| 无中文/军事SRS数据集 | 无公开中文需求NLP数据 | 16份真实GJB SRS + QA对 |
| 合理差异vs矛盾未被讨论 | LegalWiz Specificity最接近但归为矛盾 | 首次形式化区分准则 |
| Agentic RAG面向QA不面向一致性检测 | 现有RAG都面向"找答案证据" | 检索目标从"找答案"变成"找矛盾证据对" |

**关键竞品**：

| 竞品 | arXiv | 与我们的差异 |
|------|-------|-------------|
| TSRCDF-SS | 2511.23007 | 句对级(我们文档级) + 纯文本(我们多模态) + 合成数据(我们真实GJB) |
| DeepSpecs | 2511.01305 | 显式引用解析(我们隐式关联) + QA(我们一致性检测) |
| ContractCheck | 2504.18422 | 法律合同(我们军事SRS) + 仅逻辑层(我们三层) |
| ContractNLI | 2110.01799 | 文档级NLI(我们多模态) + 法律(我们GJB) |
| DoRA | 2604.17943 | 防务文档QA(我们SRS一致性) + 单模态(我们多模态) |

---

## 六、待确认/待补充

| 项目 | 状态 | 说明 |
|------|------|------|
| 问答对格式 | **已确定** | {id, instruction, output, label, layer, inconsistency_type, evidence} |
| 回答是否可引用图表 | **已确定** | 含引用（evidence含image_caption+table_caption） |
| 专家知识范围 | **待与老师确认** | 是否仅GJB 438C还是7个标准 |
| 语义层检测内容 | **待确认** | 候选6项，需确认哪些做 |
| 逻辑层检测内容 | **待确认** | 候选5项，需确认哪些做 |
| 6个GJB标准规则提取 | **待扩充** | 目前只有438C的120条 |
| 高级召回方法 | **TODO** | VLM/GNN/多跳推理/结构化RAG/Agentic RAG |
| 评测方式 | **待与老师确认** | 逐条二分类 vs claim三态 |
| 负例注入策略 | **已完成** | 原生QA对已按3种类型注入(name_inconsistency/dangling_exception/interface_type_mismatch) |

---

## 附录：关键文献清单

| 优先级 | 论文 | arXiv | 精读重点 |
|--------|------|-------|----------|
| 1 | DeepSpecs | 2511.01305 | 跨引用递归解析方法论 |
| 2 | S3CDA | 2206.13690 | GPT-4o领域退化数据 |
| 3 | Zadenoori LLM4RE SLR | 2509.11446 | LLM4RE全景 |
| 4 | DoRA | 2604.17943 | 防务文档QA benchmark构建 |
| 5 | QAssist | 2302.04793 | 唯一RE领域QA |
| 6 | RT4CHART | 2603.27752 | claim三态标注评测 |
| 7 | MAGE-RAG | 2606.15906 | 多粒度图证据+在线激活 |
| 8 | TechRAG | 2606.01613 | 技术文献多模态Agentic RAG |
| 9 | Self-RAG | 2310.11511 | reflection tokens→IsConsistent |
| 10 | LAD-RAG | 2510.07233 | 符号化文档图+跨页依赖 |
| 11 | LLM-Wiki | 2605.25480 | 可编译结构+工具调用多跳 |
| 12 | ContractCheck | 2504.18422 | 本体+FOL+SMT逻辑层 |
| 13 | ContractNLI | 2110.01799 | 文档级NLI+证据span |
| 14 | Korn 2026 | 2606.25550 | 合成smell不可靠(负面结果) |
| 15 | Industrial Standards KG | 2512.08398 | 工业标准文档KG-RAG(镜像问题) |

---

*本文档基于多Agent调研（6组arXiv检索+8篇竞品深挖+3篇方法论专题+Agentic RAG前沿调研）+ 16份真实GJB SRS数据验证。所有真实例子可通过.venv-srs/bin/python从content_list.json复现。*

---

## ★ 四类不一致框架（v3.0 核心 — 温老师8/12会议反馈）

### 背景

2026-08-12与温老师会议确认，项目范围聚焦**四个合规方向**的不一致性校验：

| # | 合规方向 | 检测内容 | 对应现有工作 | Pair Dataset场景 |
|---|---------|---------|-------------|-----------------|
| 1 | **术语层面** | 同名实体(上下文中)、多实体映射为一个 | scene1名称不一致 + 语法层S2 | sc1用例图+能力表 |
| 2 | **参数指标** | 前后文参数数据/单位/数字是否一致 | 逻辑层L1/L3 | sc3接口表 |
| 3 | **业务逻辑** | 时序逻辑(文本流程与时序是否一致) | scene2异常流(部分) | sc2流程图+用例表 |
| 4 | **GJB合规** | 根据模板的接口定义等规范 | 语法层S1-S7 | sc3接口表 |

### 待同步项

1. **温老师将分享目标文档** — 进一步同步项目范围
2. **207所前驱合同/约束** — 207所会尝试提供部分前驱合同，是否使用留作后续讨论（已在规则库预留接口）
3. **6个GJB附加标准PDF** — 待老师提供，到后补充为规则

---

## ★ 专家知识规则库（v3.0 — 规则形式存放）

**文件**: `knowledge/inconsistency_rules.json`
**格式**:
```json
{
  "rule_id": "TERM-001",
  "type": "terminology",           // 四类之一
  "description": "同一需求ID在不同位置的名称应完全一致",
  "check_method": "字符串精确匹配",    // 检测方法
  "inject_methods": ["typo改一字", "truncation截断", ...],  // 注入方法
  "applies_to": ["capability_table", "usecase_diagram"],     // 适用模态
  "severity": "HIGH",
  "example": "ID=KJCK, 1.8.3.4='快捷操控', 1.8.5.4='触摸操控'"
}
```

**规则统计**: 14条 = 术语3 + 参数3 + 逻辑3 + GJB合规5
**207所预留**: `reserved.207所前驱合同` 字段待材料到位后追加

---

## ★ QA数据集（v3.0 — 含多模态占位符 + 四类注入）

**文件**: `data/gjb_438c/data_assets/srs_qa_final.json`
**规模**: 6189条 = 3481(pair生成) + 2708(四类注入)

### QA格式（含占位符）
```json
{
  "id": "qa_0001_01",
  "pair_id": "1_001",
  "inconsistency_type": "terminology",    // 四类之一
  "subtype": "name_typo",
  "label": "inconsistent",                // consistent / inconsistent
  "is_injected": true,                    // 是否注入
  "inject_detail": "功能名「结构化数据归集」被改为「结操化数据归集」",
  "rule_id": "TERM-001",
  "question": "表{table}中功能「结操化数据归集」与图{image}中的用例名称是否一致？",
  "placeholders": {                       // 多模态占位符
    "image": "data/.../image.png",
    "table": "data/.../table.csv",
    "text": "data/.../text.txt"
  },
  "answer": "不一致。图中为「结构化数据归集」，表中为「结操化数据归集」，错字。",
  "evidence": {"image_caption": "图3...", "table_caption": "表3...", "section": "3.2.1.2"},
  "difficulty": "medium"
}
```

### 四类注入QA统计

| 类型 | 正例 | 注入(不一致) | 合计 |
|------|:---:|:---:|:---:|
| 术语层面 | 366 | 589 | 955 |
| 参数指标 | 37 | 51 | 88 |
| 业务逻辑 | 366 | 360 | 726 |
| GJB合规 | 223 | 716 | 939 |
| **合计** | **992** | **1716** | **2708** |

### 现有pair生成QA统计（3481条）

| 类型 | 数量 | 说明 |
|------|:---:|------|
| T2 表格事实检索 | 1623 | 功能名↔ID/描述 |
| T7 矛盾检测 | 462 | 图文计数/功能缺失/ID重复 |
| T4 功能溯源 | 346 | 功能在表/图/文位置 |
| T3 跨模态计数 | 336 | 功能数量 |
| T5 正文理解 | 265 | 功能列表 |
| T8 跨场景关联 | 251 | 跨章节引用 |
| T1 视觉一致性 | 198 | VLM看图→参与者/用例 |

---

## ★ Pair Dataset（v3.0 — 多模态配对数据）

**路径**: `data/gjb_438c/pair_dataset/`
**规模**: 366实例 × 4文件(image.png + table.csv + text.txt + meta.json)

| 场景 | 配对组合 | 实例数 |
|------|---------|:---:|
| sc1 | 用例图+能力表+正文 | 141 |
| sc2 | 流程图+用例表+正文 | 90 |
| sc3 | 接口图+接口表+正文 | 30 |
| sc4 | 流程图+能力表+正文 | 49 |
| sc5 | 功能图+能力表+正文 | 27 |
| sc7 | 用例图+用例表+正文 | 9 |
| sc8 | 纯图片+正文 | 20 |

**构建脚本**: `tools/build_pair_dataset.py`（从mineru_standard重建，表格清洗+正文兄弟章节补全+质量分级）

---

## 文件索引（v3.0 更新）

| 文件 | 说明 |
|------|------|
| knowledge/inconsistency_rules.json | ★四类不一致专家知识规则(14条) |
| data/gjb_438c/data_assets/srs_qa_final.json | ★最终QA数据集(6189条) |
| data/gjb_438c/data_assets/injected_qa.json | 四类注入QA(2708条) |
| data/gjb_438c/data_assets/srs_multimodal_qa.json | pair生成QA(3481条) |
| data/gjb_438c/pair_dataset/ | 多模态配对数据(366实例) |
| tools/build_pair_dataset.py | Pair Dataset构建脚本 |
| tools/gen_srs_qa.py | pair生成QA脚本(8类型) |
| tools/gen_injected_qa.py | ★四类注入QA脚本 |
| algorithms/syntax/syntax_checker.py | 语法层校验(112条) |
| algorithms/logic/logic_checker.py | 逻辑层校验(专家知识+Z3+LLM) |
| algorithms/semantic/scene1/kg_context_matcher.py | 双图融合聚合器(方向A) |
