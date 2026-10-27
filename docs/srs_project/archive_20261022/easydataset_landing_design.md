# 基于EasyDataset的多模态不一致性数据集合成——落地设计与实现

> 源设计：《基于 EasyDataSet 的多模态不一致性数据集合成技术方案》（用户定稿v1，2026-09-09）
> 落地架构：**B方案**——离线受控合成引擎（Python）+ EasyDataset统一资产层/审核流/导出平台（零魔改源码）
> 本文 = 设计→实现的可执行映射：每个设计模块落到哪个文件、哪张表、哪个API、什么状态

---

## 0. 总映射表（设计13节 → 落地实现）

| 设计模块（§） | 落地形态 | 承载资产/代码 | 状态 |
|---|---|---|---|
| §1 背景：多模态+跨模态推理+负例稀缺 | 问题定义 | `AGENTS.md`方向A/B、`.omo/plans/synthesis-route-plan.md` | ✅ 已定义 |
| §2-3 总体流程与EasyDataset角色 | **B方案**：EasyDataset=资产/审核/导出平台，合成引擎离线 | 见§1（本文） | ✅ 本文定稿 |
| §4 Pair数据资产（多模态证据集合） | Pair Schema v1 + 现有多模态资产 | `chunks.json`(1,413)、`pair_dataset/`(366对)、`anchors_v3` | ✅ §2 |
| §5 数据资产层双池 | EasyDataset同项目双池（tag树区分pool_A/pool_B） | 18,119域内 + 10,642外部 | ✅ 今日落地 |
| §6 Semantic Group语义组 | 离线聚合：graph_store→item条目 | `graph_store/`、`build_context_graph.py` | ✅ §3 |
| §7 受控数据增强（变异算子库） | 离线引擎：检测项族驱动的变异算子 | `inject_rules_v3.py`、`srs_mutation_engine.py` | ✅ §4 |
| §8 等价边界约束 | 注入后过滤（等价算子族+oracle自检） | `positive_synthesis.py`(P-EQUIV等)、52项检测器 | ✅ §4.3 |
| §9 领域知识约束 | GJB120+srs_kb+UML知识进配置空间 | `knowledge/gjb_438c_rules_full.json`、`srs_kb.json` | ✅ §5 |
| §10 多证据QA生成 | 离线生成（4类型QA）+EasyDataset承载evidence | `gen_srs_qa.py`等，evidence入`other`字段 | ✅ §6 |
| §11 质量控制 | 三重验证（规则/一致性/覆盖度） | 52项检测器+md5+seed=42+oracle | ✅ §7 |
| §12 最终数据输出 | Alpaca/ShareGPT双格式+平衡导出 | `srs_alpaca_full.jsonl`(28,761) | ✅ §7 |
| §13 总结 | — | — | — |

---

## 1. 架构决策：EasyDataset不内嵌合成引擎（B方案）

设计§3提出EasyDataset承担"Dataset Loader / Pair Schema Manager / Mutation Operator Library / Knowledge Constraint Module / QA Generator / Quality Evaluation"七模块。落地时做了** deliberate 的架构重分配**：

```
设计模块            → 落地位置                    理由
Dataset Loader      → EasyDataset（数据源tab）     文档/chunk浏览 ✅ 原生支持
Pair Schema Manager → 离线（pair_assets v1 JSON）  Pair含Z3/图结构，超出其schema能力
Semantic Group      → 离线（graph_store聚合）       语义聚类是我们方向A的研究贡献
Mutation Operators  → 离线（Python引擎）            变异需Z3/networkx/编辑距离，嵌入Next.js=重写
Knowledge Constr.   → 离线（knowledge/*.json）      规则可溯源OCR行号，提示词承载不了
QA Generator        → 离线（确定性算子+LLM表层）    标签必须由oracle确证（P1零噪声）
Quality Evaluation  → 双层：离线52项检测器(硬)      EasyDataset人工审核+评分(软) ✅ 原生支持
                       + EasyDataset审核流
导出/格式统一       → EasyDataset（导出tab）        Alpaca/ShareGPT/平衡导出/LLaMA Factory ✅ 原生
```

**为什么不魔改（C方案）**：①论文贡献在受控注入方法论（反问题形式化+P1-P5性质），不在工具UI；②引擎依赖Z3/networkx/52项检测器，嵌入Next.js等于重写且破坏seed=42可复现性；③AGPL+版本升级维护负担。B方案让**每层用最合适的工具**：合成在Python（可复现、可测试、可形式化验证），管理与人工审核在EasyDataset（现成UI、审核流、标签树、平衡导出）。

**EasyDataset在落地后的界面呈现**（用户可见的完整闭环）：

```
数据源tab：16份GJB SRS文档(.md) + 1,413章节块(含图表元数据) + UML/外部聚合块
问题tab：  28,761问题（按块分组，链到真实章节块）
数据集tab：28,761 QA对（双池标签、CoT、评分、审核流）
更多tab：  标签树（数据池→正负/来源→难度 四层导航）
导出：     按标签平衡导出 Alpaca/ShareGPT
```

---

## 2. Pair数据资产（设计§4落地）

### 2.1 Pair Schema v1（本文定义，与设计§4.1对齐）

```json
{
  "pair_id": "P-01-3.2.1.2-001",
  "entity": "数据获取功能",
  "semantic_role": "function",
  "evidence": {
    "text":    {"chunk_id": "...", "section": "3.2.1.2", "content": "系统支持结构化数据采集..."},
    "table":   {"caption": "表3 数据获取功能划分", "rows": [...]},
    "image":   {"caption": "图3 数据获取用例图", "path": "..."},
    "graph":   {"nodes": [...], "edges": [{"s": "...", "t": "...", "uml_type": "ASSOCIATION"}]}
  },
  "metadata": {"doc": "01数据获取转换分系统...", "doc_num": "01", "section": "3.2.1.2",
               "modality_count": {"n_images": 1, "n_tables": 2}},
  "pool": "A", "source": "GJB/SRS"
}
```

### 2.2 现有资产 → Pair的映射（零重做）

| Pair证据槽 | 现有承载 | 规模 |
|---|---|---|
| Text+Metadata | `easydataset/chunks.json`（含images[:5]/tables[:5]/section元数据） | 1,413块 |
| Text+Table+Image实证Pair | `data/gjb_438c/pair_dataset/`（8场景配对：图片+表格CSV+正文TXT） | 366对 |
| Graph（Visio直读） | `anchor_v3`：nodes/edges/uml_type | 373结构/5,165节点/2,557边 |
| 域外Pair | `external_qa_pairs.json`（含evidence.doc_text_snippet） | 946条(NLI难负例) |

即：**Pair不是新造的数据，是现有解析资产换一种组织视角**。EasyDataset侧，Pair的Text+Metadata槽落在Chunks表（1,413块带元数据），Graph槽证据随QA的`chunkContent/other`字段入库。

---

## 3. Semantic Group语义组（设计§6落地）

设计§6.1的例子（"数据获取是否存在逻辑遗漏"需要Pair1文本+Pair2功能列表+Pair3用例图+Pair4关系结构）正是**方向A（上下文关联）的研究对象**：

- **实现**：`graph_store`（6类节点+跨模态边）→ `(doc, embed_index)对齐` → `E实体→各模态出现聚合` → **item条目**（`{entity_id, aliases[], occurrences[doc, section, modality, text_preview]}`）
- **item = Semantic Group的机器表示**：一个item就是"同一语义实体的多模态Pair集合"，QA生成时按需选证据（单Pair=事实查询，多Pair=跨模态推理/不一致检测）
- EasyDataset侧呈现：Question→Chunk链（问题按章节块分组）+ QA的`other`字段记录证据指针

---

## 4. 受控数据增强（设计§7-8落地：变异算子库+等价边界）

### 4.1 检测项族→变异算子（离线引擎，v7口径52项检测器）

| 族 | 变异算子 | 可判方法 | 现有实现 |
|---|---|---|---|
| 参数族 | 区间平移/单位错换 | Z3 SMT-LIA | `inject_rules_v3.py` |
| 逻辑族 | 方向反转/删分支/引环 | 图算法(DFS环检测) | 同上+`srs_mutation_engine.py` |
| 术语族 | 别名错绑/指代替换 | 编辑距离+语义模型 | 同上 |
| 多模态族 | 计数不符/拓扑不符 | 跨模态结构核验 | `gen_multimodal_qa.py` |
| UML族 | 7类语义变换(方向反转/类型错认…) | UML关系规则 | `uml_qa_full.py` |

### 4.2 双向生成（设计的"增强Pair"）

每注入一个负例μ(P)，配对生成一个**等价正例ν(P)**（同一算子族、同一表面分布、仅可满足性不同）——这正是P2性质（消除表面捷径）。`positive_synthesis.py`的P-EQUIV/P-SYN/P-MODAL/P-SUPER/P-HARD即等价算子族。

### 4.3 等价边界（设计§8）

- 单位等价（0.2s=200ms）、集合超集（{A,B}⊃{A}）、精度容差 → **不是矛盾**
- 实现：注入后过滤（oracle自检P1）+ 等价算子族做对照正例
- 每条注入负例在EasyDataset的`other.inject_detail`记录变异细节，可人工复核边界

---

## 5. 领域知识约束模块（设计§9落地）

| 知识源 | 资产 | 在合成中的作用 | EasyDataset侧感知 |
|---|---|---|---|
| GJB规则库 | `knowledge/gjb_438c_rules_full.json`（120条，溯源OCR行号） | 生成前配置空间+注入后合规过滤 | questionLabel字段带规则/检测项ID |
| SRS-KB词典 | `knowledge/srs_kb.json`（23参数/13接口/10单位族） | 单位换算/参数域约束（Z3编码） | CoT字段含判定路径 |
| UML知识 | include/extend/泛化/依赖规则 | 合法关系约束（避免非法变异） | UML族标签（UML-state/ASSOCIATION/…） |

---

## 6. 多证据QA生成（设计§10落地）

### 6.1 四类型QA覆盖（设计§10.2 → 现有QA类型映射）

| 设计类型 | 现有承载 | 示例 |
|---|---|---|
| 判断型 | 一致性QA（consistent/inconsistent标签） | "「流媒体会话控制」是否依赖「流媒体数据传输」？" |
| 定位型 | T4_tracing/定位QA | "结构化数据归集在文档哪些位置出现？" |
| 解释型 | CoT字段+注入detail | 检测路径: TERM-01同义异名→编辑距离0.86 |
| 修改型 | 注入QA的answer含修正建议 | `inject_detail`记录变异前后对照 |

### 6.2 多样性控制（设计§10.3）

Question Intent（9关系模板×8维度）+ Template（12类外部QA模板）+ LLM Paraphrase（GLM表层实现，事实保持+事后回验）——均已实现，seed=42可复现。

### 6.3 evidence字段

设计§12.3的`"evidence": ["pair_001","pair_002"]` → 落地为Datasets表的`other` JSON字段（含doc/section/pair_id/image_caption/table_caption），审核界面通过"查看文本块"跳转至证据chunk。

---

## 7. 质量控制与最终输出（设计§11-12落地）

- **规则验证**：md5去重/长度校验/正负平衡（L5算子，`seed=42`）
- **一致性验证**：52项检测器=oracle自检（P1标签零噪声）+ EasyDataset人工审核流（confirmed/评分/备注，已验证PASS）
- **覆盖度验证**：注入空间=8维矛盾语义×7模态对×6图类型，覆盖率可计算（P3）
- **最终输出**：28,761 = 域内18,119（Pool A）⊕ 外部10,642（Pool B）；EasyDataset导出Alpaca/ShareGPT双格式+按标签平衡导出

---

## 8. B方案数据模型对接明细（今日实现）

### 8.1 EasyDataset四级链的写入映射（直写`prisma/db.sqlite`）

```
UploadFiles (18)  ← 16份SRS文档(解析后.md) + 未知来源聚合 + 外部数据池B
   ↓
Chunks (1,451)    ← 1,413真实章节块(带元数据) + 33域内聚合块(SRS-xx/UML-xx) + 5外部聚合块
   ↓                    聚合块名= dataset.chunkName精确匹配 → "查看文本块"可跳转
Questions (28,761) ← 每条QA一条，chunkId尽量链到真实章节块(other.section解析)
   ↓
Datasets (28,761)  ← 已有18,119(今日导入) + Pool B 10,642；questionId更新为真实Question.id
```

- **ID**：nanoid风格（A-Za-z0-9，21位，Python生成）
- **时间戳**：epoch毫秒整数（Prisma SQLite DateTime格式，实测createAt=1788926364493）
- **并发**：dev server运行时直写，`PRAGMA busy_timeout=30000`+短事务
- **标签树**（REST `PUT /api/projects/{id}/tags`，body=`{"tags":{label,parentId}}`）：

```
PoolA-域内真实SRS          PoolB-域外公开数据
├─ consistent-正例          ├─ 外部-PURE (2,472)
├─ inconsistent-负例        ├─ 外部-NLIRE (999)
├─ 原生 (4,473)             ├─ 外部-歧义类 (317)
├─ 注入 (1,716)             ├─ 外部-FlowVQA (6,000)
├─ UML族 (11,930)           ├─ 外部-LLMGen (854)
└─ easy/medium/hard         └─ easy/medium/hard
```

### 8.2 Pool B导入（外部10,642）

`external_alpaca.jsonl`(question/answer/input) ⊕ `external_sharegpt.jsonl`(tags=[来源,题型,难度,英文]，按行号zip) → EasyDataset记录：`{question, answer, chunkName:"EXT-{源}", chunkContent:input, tags:["pool_B",源,题型,难度,"英文"], model:"external-adapt", confirmed:true, other:{pool:"B"}}`

### 8.3 操作脚本

```bash
python tools/sync_easydataset.py            # 全流程：DB四级链+标签树+Pool B导入+Question链接+验证报告
python tools/extend_tag_tree.py             # 补充：36个questionLabel挂树（领域树视图计数点亮）
# 幂等：按项目名定位，重复执行会跳过已存在的File/Chunk/Tag（按name/label去重）
# 产出：data/gjb_438c/easydataset/sync_result.json
```

### 8.4 验证记录（2026-09-09 实测）

| 项 | 结果 |
|---|---|
| 域内导入 18,119/18,119 | PASS（95s，0失败） |
| 审核流API（PATCH confirmed切换+过滤查询） | PASS |
| 审核流UI（列表/详情/评分/标签/CoT，100.00%已确认） | PASS（截图2张） |
| 导出对照（5字段多重集+ground truth键集） | PASS |
| **B方案sync四级链** | **PASS**（sync_result.json：文件18/块1,451/Question 28,761/Dataset 28,761/未链接0；3,466条章节QA链到真实章节块） |
| **Pool B导入** | **PASS**（10,642条，72s，`external-adapt`模型+pool_B标签族） |
| **数据源tab** | PASS（「已上传18个文档」，16 SRS+unknown+外部池；1,413真实块+38聚合块可浏览） |
| **问题tab** | PASS（「问题(28,761)」，按块/数据源筛选可用） |
| **数据集tab** | PASS（「共28,761」，Pool B记录详情含pool_B/来源/难度/英文标签+CoT，"查看文本块"→EXT聚合块弹窗解析正常） |
| **领域树视图（标签树）** | PASS（52节点：PoolA 18,097题=注入族2,708+章节QA族3,481+UML族11,908；PoolB 10,384题按5源分题型） |
| UI截图归档 | `docs/srs_project/easydataset_verification/`（7张） |

已知限制：①领域树视图首次展开28,761问题时渲染较重（数据正确，纯前端性能）；②N1_冲突判别标签计数未点亮（原始label字符与树节点存在细微差异，258条可用筛选访问）；③2,708条SRS-unknown记录为早期批次未保留doc来源（已聚合至专门块）。

---

## 9. 后续路线（C级可选，按需启动）

1. **Pair/Group原生UI**（魔改）：EasyDataset加"Pair资产"tab，可视化多模态证据包（工作量1-2周）
2. **多证据QA对比视图**：变异前后Pair并排展示（依赖1）
3. **NLI-RE 137对人工对照组**独立展示（合成vs天然对照的可视化）
4. **知识库tab**：GJB120规则+srs_kb词典的可浏览化
5. **评测闭环**：EasyDataset评测tab（EvalDatasets）接入52项检测器做mutation detection score（P4）

以上均为展示层增强，**不改变合成引擎的离线定位**。
