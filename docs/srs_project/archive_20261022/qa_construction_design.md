# QA对构造方案 — 完整设计文档

> 基于pair_dataset(366对×7场景)与变异算子注入的四生产线合成体系
> 数据资产: 6189条(srs_qa_final) + 11711条(UML QA) = 17900条域内QA
> 平台: EasyDataset 28,761条(域内18,119 ⊕ 外部10,642)
> 成文: 2026-09-21

---

## 一、总体架构

```
16份GJB SRS(.doc)
    │ MinerU解析
    ▼
chunks(5231: 文3643/表1207/图381) + pair_dataset(366对×7场景)
    │
    ├──→ 生产线A·Pair规则生成QA ────→ 3481条(gold, 确定性模板)
    ├──→ 生产线B·变异算子注入QA ────→ 2708条(silver, 受控变异)
    ├──→ 生产线C·UML图谓词QA ──────→ 11711条(gold+仲裁, 图结构变异)
    └──→ 生产线D·假想查询 ─────────→ 2797条(检索训练, LLM生成)
              │
              ▼
    srs_qa_final.json(A+B=6189条) + anchor_v3/uml_qa_full.json(C=11711条)
              │
              ▼
    EasyDataset平台(28761条 = 域内18119 ⊕ 外部10642)
```

**pair_dataset的7个场景**:

| 场景 | 定义 | 对数 |
|---|---|:---:|
| sc1 | 用例图 + 能力表 + 正文 | 141 |
| sc2 | 流程图 + 用例表 + 正文 | 90 |
| sc3 | 接口图 + 接口表 + 正文 | 30 |
| sc4 | 流程图 + 能力表 + 正文 | 49 |
| sc5 | 功能图 + 能力表 + 正文 | 27 |
| sc7 | 用例图 + 用例表 + 正文 | 9 |
| sc8 | 纯图片 + 正文 | 20 |
| **合计** | | **366** |

---

## 二、生产线A·Pair规则生成QA

### 2.1 定位

从pair的表格/正文/图/锚点结构中，用**确定性规则模板**直接生成事实型QA。无LLM自由发挥，答案可从pair数据中直接回溯——**天然gold标签**。

### 2.2 七种QA类型

| 类型 | 数量 | 模板逻辑 | 答案来源 | 样例 |
|---|:---:|---|---|---|
| **T2 表格事实** | 1623 | 遍历表格单元格 → "X的需求标识符是什么？" | 表格单元格值 | "界面开发功能的需求标识符是什么？" |
| **T7 一致性判断** | 462 | 表格条目 vs 正文内容 → "是否全部提到？" | 表+正文对比 | "表格列出了8个功能，正文是否全部提到？" |
| **T4 追溯定位** | 346 | 实体名在chunks中检索 → "在哪些位置出现？" | chunks命中位置 | "结构化数据归集在文档的哪些位置有描述？" |
| **T3 计数** | 336 | 表格行/列统计 → "有多少个？" | 表格行数 | "所有功能标识下有多少个子功能？" |
| **T5 文本理解** | 265 | 正文功能描述提取 → "包含哪些？" | 正文解析 | "所有功能标识包含哪些子功能？" |
| **T8 交叉引用** | 251 | 实体在多章节的出现 → "还在哪些位置？" | chunks+章节关联 | "X除了在3.2.1.2出现外还在哪些位置？" |
| **T1 视觉一致性** | 198 | 锚点图中实体关系 → "参与者与哪些用例关联？" | 锚点图结构 | "图中参与者与哪些用例存在关联关系？" |

### 2.3 生成协议

```python
for pair in pair_dataset:
    # T2: 遍历κ_T编译后的表格条目
    for item in compile_table(pair.table_csv).items:
        yield QA(question=f"{item.name}的需求标识符是什么？",
                 answer=item.id, evidence=pair.table)

    # T7: 表格条目 vs 正文段落
    mentioned = [c for c in item_names if c in prose_text]
    yield QA(question=f"表格列出了{len(items)}个功能，正文是否全部提到？",
             answer=compare(items, mentioned), evidence=pair)

    # T1: 锚点图中实体邻接关系
    for node in anchor.nodes:
        neighbors = get_edges(anchor, node.id)
        yield QA(question=f"图中「{node.text}」与哪些用例存在关联关系？",
                 answer=neighbors, evidence=pair.image)
```

### 2.4 标签质量

**gold级** — 每条QA的答案可从pair的table.csv/text.txt/visio_anchor.json中确定性回溯，无LLM参与。

---

## 三、生产线B·变异算子注入QA

### 3.1 定位

对pair的某一模态内容做**受控变异**（模拟真实文档缺陷），然后生成"这个不一致对不对"的判断QA。变异是确定性的（seed=42），注入规则可追溯到GJB 438C标准。

### 3.2 四种不一致类型 × 32种注入算子

| 不一致类型 | QA数 | 规则数 | 注入算子示例 |
|---|:---:|:---:|---|
| **术语层(TERM)** | 955 | 8 | 同义异名(TERM-01)/名称截断(TERM-02)/错字(TERM-03)/缩写不一致(TERM-05)/枚举缺失(TERM-08) |
| **GJB合规(GJB)** | 939 | 10 | 表头字段缺失(GJB-01)/ID格式违规(GJB-04)/章节缺失(GJB-06)/交叉引用悬挂(GJB-07) |
| **业务逻辑(LOGIC)** | 726 | 11 | 悬挂引用(LOGIC-01→03)/步骤顺序矛盾/分支缺失/互斥违规/时序冲突 |
| **参数层(PARAM)** | 88 | 5 | 数值冲突(PARAM-01)/单位不一致(PARAM-02)/值域越界(PARAM-03) |

### 3.3 注入QA样例

**负例(inconsistent)·1716条:**

```
[TERM-001] 表{table}中功能「结操化数据归集」与图{image}中的用例名称是否一致？
    → 不一致。图中为「结构化数据归集」，表格误写「结操化数据归集」，
      「构」被误写为「操」，属于错字变异。

[LOGIC-003] 表{table}中用例描述引用了异常流E9，但文档中未定义E9。该引用是否有效？
    → 无效。引用了未定义的异常流E9，属于悬挂引用。

[GJB-004] 表{table}中功能「X」的需求标识符为「sjhqzhfw-g」，是否符合GJB 438C规范？
    → 不符合。GJB 438C要求标识符为大写字母数字（[A-Z]{2,8}格式）。
```

**正例(consistent)·992条:**

```
[TERM-001] 表{table}中功能「结构化数据归集」的名称，与图{image}中的用例名称是否一致？
    → 一致。表格和图中均使用「结构化数据归集」。

[LOGIC-001] 根据正文{text}，结构化数据归集的主要功能是什么？
    → 提供精准可靠的数据引接汇聚工具手段，实现全域数据接入能力。
```

### 3.4 核心设计: 正负对照

**每个注入负例都有同一pair、同一模板的正例配对**——模型不能靠"表面看起来像变异"来判断，必须真正理解内容才能区分。

```
负例: "表格写「结操化数据归集」与图「结构化数据归集」是否一致？"
正例: "表格写「结构化数据归集」与图「结构化数据归集」是否一致？"
       ↑ 唯一差异: 一个字的变异 — 模型必须逐字符比较
```

### 3.5 变异注入协议

```python
for pair in pair_dataset:
    for rule in inject_rules:  # 32种, 每种可追溯到GJB规则库
        # 1. 选择注入目标(表格/正文/图/ID)
        target = select_target(pair, rule)
        # 2. 确定性变异(seed=42)
        mutated = rule.mutate(target)  # 如: '结构化' → '结操化'
        # 3. 生成负例QA
        yield QA(label="inconsistent", question=rule.question_template(mutated),
                 answer=rule.answer_template(mutated, original))
        # 4. 生成对照正例QA(同一模板, 不变异)
        yield QA(label="consistent", question=rule.question_template(original),
                 answer=rule.answer_template(original, original))
```

### 3.6 标签质量

**silver级** — 注入规则确定（变异操作确定、seed固定），但pair本身的表格/正文/图质量有噪声（真实文档非完美），可能引入少量假阳性。

---

## 四、生产线C·UML图谓词QA

### 4.1 定位

从**锚点结构**（373图/5165节点/2557边）出发，对UML图的关系类型做受控变异，生成图语义级的QA。期望答案由**9个确定性图谓词检测器**自动仲裁（F1=0.9943），不依赖LLM自评。

### 4.2 十二种UML变异算子

| 算子 | QA数 | 含义 | 检测器 |
|---|:---:|---|---|
| dependency_fabrication | 1545 | 虚构依赖关系 | D_dep |
| relationship_type_confusion | 1542 | 关系类型混淆(关联误标为依赖) | D_type |
| direction_fabrication | 1438 | 虚构方向(无箭头标为有向) | D_dir |
| usecase_vs_state | 437 | 用例图误判为状态图 | D_nodetype |
| actor_vs_component | 302 | 参与者误判为组件 | D_nodetype |
| direction_reversal | 101 | 方向反转(箭头指向反) | D_dir |
| realization_vs_generalization | 79 | 实现与泛化混淆 | D_impl |
| condition_swap | 77 | 条件交换(是/否分支互换) | D_nav |
| circular_dependency | 22 | 循环依赖(自引用环) | D_cycle |
| navigation_error | 26 | 导航路径错误 | D_nav |
| composition_vs_aggregation | 10 | 组合与聚合混淆 | D_type |
| lifecycle_error | 10 | 生命周期状态违规 | D_lifecycle |

### 4.3 九个确定性检测器

```
D_type      — 关系类型谓词(ASSOCIATION/DEPENDENCY/REALIZATION/...)
D_dir       — 方向谓词(begin_arrow/end_arrow)
D_impl      — 实现关系谓词
D_nav       — 导航路径谓词
D_dep       — 依赖关系谓词
D_nodetype  — 节点类型谓词(usecase/actor/state/component)
D_label     — 标签谓词
D_cycle     — 环检测谓词(DFS有向环)
D_lifecycle — 生命周期状态谓词
```

每个检测器是**纯确定性程序**（图算法+谓词逻辑），无任何LLM参与。检测器套件在doc级F1=0.9865，仲裁修正后F1=0.9943。

### 4.4 QA生成协议

```python
for structure in anchor_v3.structures:  # 373图
    for operator in UML_OPERATORS:      # 12种变异算子
        # 1. 提取原始UML关系
        relation = extract_relation(structure)  # 如: A --ASSOCIATION--> B
        # 2. 应用变异算子
        mutated = operator.apply(relation)
        # 3. 生成QA(答案由检测器判定)
        verdict = detector_suite.check(mutated)
        yield QA(
            question=f"图中「{mutated.src}」与「{mutated.dst}」之间是什么关系？",
            answer=verdict.to_answer(),
            label=verdict.label)  # consistent/inconsistent
        # 4. 正例对照(不变异)
        yield QA(question=same_template(relation),
                 answer=detector_suite.check(relation).to_answer(),
                 label="consistent")
```

### 4.5 标签质量

**gold+仲裁级** — 检测器套件提供确定性判定(F1=0.9943)；检测器发现的语料标签噪声(89条)已通过仲裁协议修正。

### 4.6 独特价值

打破了"LLM生成→LLM评测"的循环论证：检测器是独立于生成器的第三方判定，且检测器反过来仲裁出了语料自身的标签噪声。

---

## 五、生产线D·假想查询(检索训练用)

### 5.1 定位

面向检索模型训练的query生成——不是判断型QA，而是"chunk最可能被什么问题问到"。

### 5.2 两类查询

| 来源 | 数量 | 生成方式 | 用途 |
|---|:---:|---|---|
| 假想查询(hq) | 2000 chunk×2条 | LLM读chunk内容→生成"最可能被问到的问题" | docT5query索引 + 检索训练对 |
| 参数型查询(v2) | 797 chunk | LLM生成含具体数字的问题("图4在哪章节") | 检索评测集 + 数字校验 |

### 5.3 下游消费

- **检索训练三元组**: 9436条 (query, 宿主chunk, 15个hard negative)
  - hq来源: 4797对 / eval来源: 2859对 / alpaca来源: 1780对
- **docT5query推理期索引**: 2000 chunk的假想查询入检索索引

---

## 六、汇聚层·EasyDataset平台

### 6.1 四级链

```
UploadFiles(18) → Chunks(1451) → Questions(28761) → Datasets(28761)
  16份SRS(.md)     1413真实章节块     全部QA条目        审核+导出
  +2聚合块          +38聚合块
```

### 6.2 双池

| 池 | 条数 | 来源 |
|---|:---:|---|
| Pool A(域内) | 18,119 | 生产线A(3481) + B(2708) + C(11711) + D(2797) + 其他合成 |
| Pool B(外部) | 10,642 | 外部数据集适配(PURE 2472/NLIRE 999/歧义类317/FlowVQA 6000/LLMGen 854) |
| **合计** | **28,761** | |

### 6.3 验证

| 项 | 结果 |
|---|:---:|
| 域内导入 | PASS(18119/18119, 95s) |
| Question链接 | 28761/28761, unlinked=0 |
| 导出Round-trip | PASS(5字段多重集一致) |
| 审核流UI | PASS(截图归档) |

---

## 七、设计原则总结

| # | 原则 | 实现方式 |
|:---:|---|---|
| 1 | **多生产线互相独立** | A/B/C/D各有独立的生成机制(模板/变异/谓词/LLM)，单一生产线缺陷不影响其他线 |
| 2 | **标签可信度分层** | A=gold(确定性回溯) / C=gold+仲裁(检测器套件) / B=silver(注入规则确定但pair有噪声) / D=LLM生成(需抽检) |
| 3 | **正负对照设计** | 每条注入负例都有同pair、同模板的正例配对——消除表面捷径 |
| 4 | **可复现性** | 全链seed=42、变异算子确定、LLM走磁盘缓存——重跑零漂移 |
| 5 | **规则可追溯** | 注入规则→GJB 438C标准OCR行号；UML检测器→UML规范 |
| 6 | **规模可控** | 6189+11711+2797=17900条域内QA，涵盖四层不一致(术语/参数/逻辑/合规)×三种模态(文/表/图) |

---

## 八、数据资产清单

| 资产 | 路径 | 规模 |
|---|---|---|
| pair_dataset | `data/gjb_438c/pair_dataset/` | 366对×7场景 |
| srs_qa_final(A+B) | `data/gjb_438c/data_assets/srs_qa_final.json` | 6189条 |
| UML QA(C) | `data/gjb_438c/anchor_v3/uml_qa_full.json` | 11711条 |
| 假想查询(D) | `data/gjb_438c/data_assets/doc_queries/doc_queries.json` | 2000 chunk |
| 参数型查询(D) | `data/gjb_438c/data_assets/doc_queries/doc_queries_v2.json` | 797 chunk |
| 检索训练三元组 | `data/gjb_438c/data_assets/retrieval_train/triples.json` | 9436条 |
| 注入规则库 | `knowledge/gjb_438c_rules_full.json` | 120条(可追溯OCR行号) |
| EasyDataset全量 | `data/gjb_438c/easydataset/srs_alpaca_full.jsonl` | 28761条 |
