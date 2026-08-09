# 数据设计文档

> 版本：v1.1 | 日期：2026-08-07
> 同步project_guide.md v2.0数据；更新Stage 0完成状态、QA对已生成、外部数据集扩充

---

## 一、三个组件各自需要什么数据

### 1. 上下文关联（Agentic RAG召回）

**输入**：问题（来自问答对的instruction）

**需要的数据**：

| 数据 | 来源 | 用途 |
|------|------|------|
| SRS文档内容 | 真实(16份content_list.json) | 检索源：text/table/image条目 |
| 章节结构注册表 | 真实(从content_list提取) | 章节号→{title, req_id, doc_id}映射 |
| 图号/表号索引 | 真实(从content_list提取) | "见图X"/"见表X"的引用解析 |
| ID注册表 | 真实(从content_list提取) | 7位置ID聚合(标题539+功能表707+接口表211+合格性113+追踪217+正文351+表格57)，1029个唯一ID，5个跨文档 |
| 追踪表映射 | 真实(从第5章追踪表提取) | 上级章节号↔本文档章节号 |
| 接口拓扑 | 真实(从3.3/3.4接口表提取) | 发送方/接收方→跨文档接口图 |
| GJB规则库 | 真实(120条规则) | 结构化检索的先验知识 |
| 问答对 | 增强(LLM生成) | 问题的来源 |
| 外部领域知识 | 增强(GJB 439A等6个标准) | 扩展召回范围 |

**输出**：召回的多模态上下文（text片段 + table行 + image引用 + section位置）

---

### 2. 语法层校验（不依赖上下文，直接与GJB一对一）

**输入**：回答文本（来自问答对的output）

**需要的数据**：

| 数据 | 来源 | 用途 |
|------|------|------|
| 10个正则表达式 | 真实(GJB标准编码) | A类检测：ID格式/占位符/章节号/图号/表号/caption/版本号/约束/异常流 |
| GJB 438C规则库(120条) | 真实 | B类检测：章节完整性/顺序/用例表结构/追踪表/合格性表 |
| 文档section集合 | 真实(从content_list提取) | 校验"回答引用3.8但doc11缺3.8" |
| 图号/表号索引 | 真实(复用上下文关联的索引) | 校验"回答引用表37但表37不存在" |
| 问答对 | 增强 | 被校验的回答来源 |

**输出**：语法层issues列表（每个issue含检测器名/类型/证据/修复建议）

---

### 3. 语义层校验（依赖上下文，涉及多模态）

**输入**：回答文本 + 召回的多模态上下文

**需要的数据**：

| 数据 | 来源 |
|------|------|
| 8个场景定义 | 真实(从文档统计) |
| 场景1: 用例图+capability表+正文(120实例,strong=99) | 真实 |
| 场景2: 流程图+usecase表+正文(78实例,strong=70) | 真实 |
| 场景3: 接口图+interface表+正文(29实例,strong=27) | 真实 |
| 场景4: 流程图+capability表(49实例,strong=34) | 真实 |
| 场景5: 功能图+capability表(25实例,strong=23) | 真实 |
| 场景6: 功能框架图+其他表(1实例) | 真实 |
| 场景7: 用例图+usecase表(15实例,strong=10) | 真实 |
| 场景8: 纯图片+正文(18实例) | 真实 |
| unclassified: 图片类型未确定(29实例) | 真实 |
| 场景0: 纯文本(外部数据,946条QA) | 增强 |
| 召回的多模态上下文 | 来自上下文关联组件 |
| 问答对 | 增强 |
| 名称对齐训练数据 | 增强(正例+负例) |

**输出**：语义层issues列表

---

### 4. 逻辑层校验（依赖上下文，专家知识）

**输入**：回答文本 + 上下文 + 专家知识

**需要的数据**：

| 数据 | 来源 |
|------|------|
| GJB 438C(120条) | 真实 |
| GJB 439A | 增强(待提取) |
| GJB/Z 102A | 增强(待提取) |
| GJB 2786A | 增强(待提取) |
| GJB 1268A | 增强(待提取) |
| GJB 5235 | 增强(待提取) |
| GJB 1267 | 增强(待提取) |
| 异常流定义集/引用集 | 真实(从usecase表提取) |
| 约束集 | 真实(从3.9/3.10表提取) |
| 追溯链路 | 真实(从追踪表+合格性表提取) |
| 问答对 | 增强 |

**输出**：逻辑层issues列表

---

## 二、数据来源分类与处理方案

### Category A: 真实数据（来自16份GJB SRS）

**处理流程**：

```
16份content_list.json
    ↓
Stage 0: 结构化预处理
    ├── section_registry: {section_id → {title, req_id, doc_id}}
    ├── table_index: {table_num → table_item}
    ├── figure_index: {fig_num → image_item}
    ├── id_registry: {canonical_id → [occurrences across 5 positions]}
    ├── traceability_map: [{upstream_section, local_section, note}]
    ├── interface_topology: [{interface_id, type, sender, receiver, doc}]
    ├── version_pairs: [{software, version_3.9, version_3.10, doc}]
    └── exception_flows: [{usecase_section, defined_set, referenced_set}]
    ↓
Stage 1: 特征提取(按表型)
    ├── usecase_features: [{name, actors, flow_steps, exceptions, constraints}]
    ├── capability_features: [{name, id, description, reuse, modes}]
    ├── interface_features: [{id, type, sender, receiver, content}]
    ├── environment_features: [{device, param, op, value, unit, equipment_form}]
    ├── qualification_features: [{section, methods, level}]
    └── traceability_features: [{forward_edges, reverse_edges, completeness}]
    ↓
Stage 2: 关联图构建
    └── heterogeneous_graph: nodes={items, tables, images, sections}, edges={references, mappings, topology}
    ↓
输出: 结构化数据资产 → 供上下文关联召回 + 三层校验使用
```

**特点**：
- 全部从真实文档提取，无合成
- 可通过脚本自动构建（已有srs_correct_parse.py的基础）
- 是Ground Truth，用于校验回答的基准

---

### Category B: 增强数据（泛化增强）

**处理流程**：

```
Stage A: 问答对生成
    ├── 从真实SRS的evidence unit生成问题(6类)
    │   ├── 功能查询 → 召回场景1/2/4/5/7
    │   ├── 接口参数查询 → 召回场景3
    │   ├── 约束查询 → 召回场景2/6
    │   ├── 追溯查询 → 召回场景6(合格性+追踪)
    │   ├── 版本/配置查询 → 召回场景6
    │   └── 跨章节矛盾检测 → 跨场景
    ├── LLM生成正例回答(基于evidence,可追溯)
    └── 人工验证正例
    ↓
Stage B: 负例注入(在正例中注入不一致)
    ├── 语法层负例: 错误术语/编号/格式 → 规则生成
    ├── 语义层负例: 错误值/错误名/错误接口类型 → entity substitution
    ├── 逻辑层负例: 矛盾约束/悬空异常流/断裂追溯 → counterfactual injection
    └── 人工验证负例(必须!Korn 2026证明LLM不可靠)
    ↓
Stage C: 外部数据收集
    ├── PURE数据集(18份SRS, 2698段落, 已下载) → 预训练名称一致性模型
    ├── ContractNLI(607文档, 17假设, 已下载) → 迁移文档级NLI
    ├── GJB 439A等6个标准(待获取PDF) → 提取规则扩充专家知识
    └── DoRA(防务文档QA, arXiv:2604.17943) → 参考QA生成方法
    ↓
输出: 标注问答对数据集 + 扩充专家知识库
```

**特点**：
- 正例基于真实SRS生成，负例在正例上注入
- 必须人工验证（不能纯LLM生成）
- 外部数据用于预训练/迁移，不直接作为评测对象
- 标注格式：`{id, instruction, output, label(正/负), layer(语法/语义/逻辑), inconsistency_type}`

---

### 已下载的外部数据集

| 数据集 | 位置 | 规模 | 格式 | 用途 |
|--------|------|------|------|------|
| **ContractNLI** | `data/external_datasets/contract_nli/contract-nli/` | 607文档(train423+dev61+test123), 17个NLI假设 | JSON(text+spans+annotations) | 文档级NLI迁移；546条QA对(场景0, 含43条平衡补充) |
| **PURE** | `data/external_datasets/pure/XMLZIPFile/` | 18份SRS, 2698段落 | XML(req_document.xsd schema) | 需求分类预训练；英文SRS结构参考 |
| **Fault-prone SRS** | `data/external_datasets/fault_srs/` | 7060条标注需求(5种歧义类型) | JSON | 需求歧义检测；200条QA对(场景0) |
| **FinBalance** | `data/external_datasets/finbalance/` | 710条记录(230不一致/480一致) | JSONL | 数值不一致检测；200条QA对(场景0) |
| **ScholScan** | `data/external_datasets/scholscan/` | 1篇论文(6图+5表+95段) | MinerU解析JSON | 多模态文档理解；3条QA对(场景6/8) |
| **NLI4CT-zh** | `data/external_datasets/nli4ct_zh/` | 100条中文NLI | JSON | 中文NLI参考 |
| **M-LongDoc** | `data/external_datasets/m_longdoc/` | 长文档PDF | PDF | MinerU解析失败(文件过大) |

**ContractNLI数据格式**：
```json
{
  "documents": [{
    "id": 34,
    "file_name": "xxx.pdf",
    "text": "合同全文...",
    "spans": [{...}],          // 文本片段
    "annotation_sets": [{
      "annotations": {
        "nda-1": {"choice": "Entailment", "spans": [...]},
        "nda-2": {"choice": "Contradiction", "spans": [...]}
      }
    }]
  }],
  "labels": {
    "nda-1": {"short_description": "Explicit identification", "hypothesis": "All Confidential Information shall be expressly identified..."},
    "nda-2": {"short_description": "...", "hypothesis": "..."}
  }
}
```

**PURE数据格式**：
```xml
<req_document>
  <title>Video Search Engine</title>
  <version>1.0</version>
  <p id="1">
    <title>Introduction</title>
    <p id="1.1">
      <title>Purpose</title>
      <text_body>需求文本...</text_body>
    </p>
  </p>
</req_document>
```

---

## 三、两类数据的标记与隔离

### 数据标记方案

```python
DataItem = {
    "id": "case_001",
    "source": "real" | "augmented",     # 数据来源标记
    "doc_ref": "03服务集成框架",          # 关联的真实文档(增强数据也标注来源)
    "scenario": 2,                       # 对应8个场景中的哪个
    "instruction": "查询达梦数据库版本",
    "output": "达梦数据库版本为V7.6",
    "label": "positive" | "negative",   # 正例/负例
    "layer": "semantic",                 # 不一致所属层
    "inconsistency_type": "version_conflict",  # 不一致类型(负例才有)
    "evidence": {                        # Ground Truth证据(真实数据提供)
        "recall_sections": ["3.9.1", "3.10.3"],
        "doc_values": [...],
        "gjb_rule": "GJB-438C-3.10"
    }
}
```

### 隔离规则

- 真实数据(16份SRS)是Ground Truth，永不修改
- 增强数据(问答对)标注source="augmented"和doc_ref
- 评测时：真实数据的不一致作为Gold Standard，增强数据作为训练/扩展评测
- 真实数据中已发现的不一致(版本冲突9处/异常流87个/名称不一致92条等)直接标注为Gold Standard正例

---

## 四、专家知识库

### 4.1 GJB 438C规则（已有120条，需格式升级）

**当前格式**（旧）：
```json
{
  "rule_id": "GJB-RULE-001",
  "type": "format",           // format/structure/content/parameter/interface
  "source": "4.1",            // GJB标准章节号
  "severity": "HIGH",         // HIGH/MEDIUM/LOW
  "modality": "MUST",         // MUST/SHOULD/MAY
  "applies_to": ["ALL"],      // 适用的文档类型
  "applies_role": "订购方",    // 适用的角色
  "description": "订购方应在合同中规定所交付文档的载体以及文档的具体格式。",
  "original_text": "附录 A～附录T规定的文档格式..."
}
```

**问题**：旧格式只有type分类(format/structure/content/parameter/interface)，没有对齐三层校验框架(语法/语义/逻辑)，也没有标注检测器绑定关系。

**新格式（待设计）**：需要增加以下字段：
- `check_layer`: syntax | semantic | logic  — 对应三层校验
- `check_type`: A_regex | B_rule | C_context | D_expert  — 检测器类型
- `detector_id`: 绑定的具体检测器ID
- `check_target`: answer | document | answer_vs_document  — 校验对象
- `context_dependency`: false | true  — 是否依赖上下文召回

### 4.2 术语词典（已有）

- `knowledge/srs_kb.json`：23参数 + 13接口 + 10单位族

### 4.3 6个GJB标准（待扩充）

| GJB标准 | 内容 | 当前状态 | 获取方式 |
|---------|------|---------|---------|
| GJB 439A-2013 | 军品软件质量保证通用要求 | antpedia摘要(适用范围+术语+引用标准) | 需老师提供PDF |
| GJB/Z 102A-2012 | 军用软件安全性设计指南 | antpedia页面已知 | 需老师提供PDF |
| GJB 2786A-2009 | 军用软件开发通用要求 | antpedia页面已知 | 需老师提供PDF |
| GJB 1268A-2004 | 军用软件验收要求 | antpedia页面已知 | 需老师提供PDF |
| GJB 5235-2004 | 军用软件配置管理 | antpedia页面已知 | 需老师提供PDF |
| GJB 1267-1991 | 军用软件维护 | antpedia页面已知 | 需老师提供PDF |

**临时方案**：暂时只用GJB 438C的120条规则，6个标准后续补充。

---

## 五、真实数据中已发现的不一致（Gold Standard种子）

### 来自16份SRS的真实不一致

| 类型 | 层 | 数量 | 真实例子 |
|------|---|------|---------|
| 版本冲突(同文档内) | 语义 | 9处 | doc02: 3.9达梦V7.6 vs 3.10达梦V7.2 |
| 异常流悬空引用 | 逻辑 | 87个(55张用例表) | doc06: E2被引用但未定义 |
| 名称不一致 | 语义 | 92条 | doc03: 标题"服务工程编译" vs 正文/表"服务插件编译" |
| 接口类型矛盾 | 语义 | 23条 | doc02=API vs doc05=HTTP(同ID) |
| 合格性章节不匹配 | 语法 | 106条 | doc03合格性表章节号与正文不一致 |
| 幽灵引用(Ghost) | 语法 | 16条 | doc02追踪表引用不存在的章节 |
| 追溯不对称 | 语法 | 9条 | doc03正向126行 vs 逆向0行 |
| 死异常(定义但未引用) | 逻辑 | 244个 | doc01: E1定义但无任何引用 |

---

## 六、排期

### Phase 1（已完成）

| 任务 | 状态 | 说明 |
|------|------|------|
| 外部数据集下载 | ✅ 完成 | 7个数据集(ContractNLI/PURE/Fault-prone/FinBalance/ScholScan/NLI4CT-zh/M-LongDoc) |
| 数据设计文档 | ✅ 完成 | 本文档v1.1 |
| Stage 0结构化预处理 | ✅ 完成 | stage0_assets.json: 8类资产(329图+1119表+1029ID+1249章节) |
| 语义模态数据 | ✅ 完成 | semantic_modality_data.json: 8场景+unclassified, 364实例 |
| 原生QA对生成 | ✅ 完成 | 1221条(正592/负629), 6种负例类型(名称376+悬空117+合格性91+接口27+图片标题14+版本4), 语法/语义/逻辑三层, 8场景全覆盖 |
| 外部QA对生成 | ✅ 完成 | 946条(正581/负365), 4个数据源, 场景0 |
| 多模态QA对 | ✅ 完成 | 3条ScholScan(内容级多模态) |
| QA审计修复 | ✅ 完成 | 场景4/5覆盖补齐、FinBalance标签泄漏修复、ContractNLI假设对称化(补43正例)、doc_ref完整化、doc13后缀修复、Fault-prone指令截断修复、mm output统一化、跨场景去重、假负例清理、语法层负例补齐、sc3/sc2/sc7 image_path修复、sc8 QA生成(图片标题检测)、logic层正例补充(74条异常流一致)、场景重分类(按精确模态组合对齐8场景) |
| GJB规则格式设计 | 待做 | 旧120条规则格式升级，对齐三层校验 |
| 6个GJB标准获取 | 阻塞 | 需老师提供PDF，暂时只用438C |

### Phase 2（进行中）

| 任务 | 状态 | 说明 |
|------|------|------|
| 负例注入策略 | ✅ 完成 | 原生3种(name_inconsistency/dangling_exception/interface_type_mismatch) + 外部3种(contradiction/ambiguity/numerical) |
| 上下文关联实现 | 待做 | Agentic RAG召回(12种信号+高级方法) |
| 语法层校验实现 | 待做 | A类正则+B类GJB规则 |

### Phase 3（后续）

| 任务 | 说明 |
|------|------|
| 上下文关联实现 | Agentic RAG召回(12种信号+高级方法) |
| 语法层校验实现 | A类正则+B类GJB规则 |
| 语义层校验实现 | 8场景×候选检测项 |
| 逻辑层校验实现 | 专家知识+异常流/约束/追溯 |

---

*本文档围绕上下文关联+三层校验三个组件的数据需求设计，区分真实数据(Category A)和增强数据(Category B)，明确处理流程和隔离方案。*
