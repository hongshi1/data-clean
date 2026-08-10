# 数据集构建路线图 v1.0

> 日期: 2026-08-10
> 目的: 明确数据集层面的构建方向 + 统一的格式设计

---

## 一、数据集构建现状

| 层次 | 状态 | 内容 |
|------|------|------|
| 原始数据 | ✅ 完成 | 16份SRS(mineru_standard: md+content_list+372图) |
| 结构化资产 | ✅ 完成 | stage0_assets(971ID/1207表/381图/1022追溯) |
| 8场景模态 | ✅ 完成 | semantic_modality_data(381实例) |
| 配对数据集 | ✅ 完成 | pair_dataset(319实例: 图+表CSV+文TXT) |
| Gold Standard | ⚠️ 部分 | 3场景223条(名称/接口/异常流) |
| VLM/特征 | ✅ 完成 | usecase_features(406) + vlm提取(136) |
| 网络增强 | ⚠️ 少量 | ChartArena中文(1209条, source=network) |

---

## 二、待构建方向（按优先级）

### 方向A: 上下文关联评测数据（最大缺口）

**问题**: 目前只有静态聚合(知道哪些位置属于同一实体), 没有"给定查询→召回上下文"的评测数据。

**需要构建**:
```
实体查询数据集:
  {query_entity, doc, gold_context}
  
query_entity: "创建服务工程" 或 "PZXQ-GN-FWKFZC-CJFWGC"
gold_context: {
  text: {section: "3.2.1.1", snippet: "..."},
  image: {caption: "图5 服务开发用例图", path: "..."},
  table_rows: [{table: "表3", row: [...]}],
  qualification_row: {table: "合格性表", row: [...]},
  traceability_row: {table: "追溯表", row: [...]}
}
```

**来源**: stage0的id_registry(971个ID, 每个有全部出现位置)

**规模**: 抽样200-300个多位置ID

**评测**: 给定query, 模型召回上下文, 与gold对比计算P/R/F1(按模态分别)

---

### 方向B: 不一致性Gold Standard补全

**当前6种类型覆盖情况**:

| 不一致类型 | 层 | 状态 | 需要 |
|-----------|-----|------|------|
| 名称不一致 | 语义 | ✅ 16真实+91注入 | — |
| 接口属性矛盾 | 语义 | ✅ 20条 | — |
| 异常流悬挂 | 逻辑 | ✅ 28条 | — |
| 版本矛盾 | 语义 | ⚠️ 2个(未标注) | 补Gold Standard条目 |
| 追溯断裂 | 逻辑 | ⚠️ 450个(未验证) | 人工验证+筛选 |
| 约束矛盾 | 逻辑 | ❌ 未做 | 从3.9/3.10环境表提取 |

**待补**:
- 版本矛盾: 从stage0 version_pairs(25条, 2个真实矛盾)构建标注
- 追溯断裂: 从450个候选中人工验证
- 约束矛盾: 从环境表/软件清单表提取数值约束, 检测约束冲突

---

### 场景覆盖补全

**8场景Gold Standard现状**:

| 场景 | Gold Standard | 需要 |
|------|--------------|------|
| sc1 用例图+capability表 | ✅ 145条 | — |
| sc2 流程图+usecase表 | ✅ 48条 | — |
| sc3 接口图+interface表 | ✅ 30条 | — |
| sc4 流程图+capability表 | ❌ | 从sc1同构构建(图类型不同) |
| sc5 功能图+capability表 | ❌ | 同上 |
| sc6 功能框架图+其他表 | ❌ | 8实例少, 可做few-shot |
| sc7 用例图+usecase表 | ❌ | 从sc2同构构建 |
| sc8 纯图片+正文 | ❌ | 图片标题一致性(已有29条QA可转) |

---

### 评测基础设施

1. **正式train/test划分**: 文档级隔离(01-08/09-16), 已有雏形需固化
2. **评测runner**: 统一输入输出格式, 自动计算P/R/F1/统计显著性
3. **baseline库**: 多数类/字符级/LLM零样本/NLI
4. **消融配置**: 无图/无表/无文/纯LLM

---

## 三、统一数据集格式设计

### 核心原则
- **来源标注**: 每个条目必须标注 `source: native | network`
- **可追溯**: 每个条目可追溯到原始文档位置
- **分层**: 原始数据 → 聚合条目 → 评测数据, 层次清晰

### 1. 聚合条目格式 (Entry)

```json
{
  "entry_id": "E0001",
  "entity_id": "PZXQ-GN-FWKFZC-CJFWGC",
  "entity_name": "创建服务工程",
  "doc": "03服务集成框架软件需求规格说明-终稿",
  "source": "native",
  "positions": {
    "text": {"section": "3.2.1.1", "snippet": "创建服务工程...", "file": "md/03.md#3.2.1.1"},
    "capability_table": {"table": "表3", "row": [["1","创建服务工程","PZXQ-GN-..."], ...], "file": "cl/03.json"},
    "usecase_table": {"table": "表4", "uc_name": "创建服务工程", "actors": "开发人员", "file": "cl/03.json"},
    "qualification_table": {"table": "合格性表", "row": [...], "file": "cl/03.json"},
    "traceability_table": {"table": "追溯表", "row": [...], "file": "cl/03.json"},
    "image": {"caption": "图5 服务开发用例图", "path": "images/fig_005.png", "type": "usecase_diagram", "file": "cl/03.json"}
  }
}
```

### 2. 不一致性Gold Standard格式

```json
{
  "entry_id": "E0001",
  "inconsistencies": [
    {
      "type": "name_inconsistency",
      "subtype": "typo | truncation | charorder | multiname | semantic_conflict",
      "severity": "high | medium | low",
      "location_a": {"position": "text", "value": "创建服务工程"},
      "location_b": {"position": "traceability_table", "value": "创建服务工程管理"},
      "description": "...",
      "detection_difficulty": "easy | medium | hard",
      "verified": true,
      "source": "real | injected"
    }
  ]
}
```

### 3. 评测数据格式

```json
{
  "task_id": "T0001",
  "direction": "A | B | end2end",
  "scene": "sc1",
  "input": {...},       // 方向A: query; 方向B: 聚合条目; end2end: QA对
  "gold": {...},        // 方向A: gold_context; 方向B: inconsistencies; end2end: label
  "split": "train | test",
  "source": "native | network"
}
```

### 4. 目录结构

```
data/gjb_438c/data_assets/
├── stage0_assets.json          # 原始结构化资产(不动)
├── semantic_modality_data.json # 场景定义(不动)
├── pair_dataset/               # 配对数据(不动)
├── entries/                    # ★ 聚合条目层
│   ├── native_entries.json     #   原生聚合条目(971个ID)
│   └── entry_index.json        #   条目索引
├── gold_standard/
│   ├── inconsistencies/        # ★ 不一致性Gold Standard
│   │   ├── name_inconsistency.json
│   │   ├── interface_attr.json
│   │   ├── exception_flow.json
│   │   ├── version_conflict.json
│   │   ├── trace_break.json
│   │   └── constraint_conflict.json
│   └── context_retrieval/      # ★ 方向A评测数据
│       ├── train.json
│       └── test.json
└── benchmark/
    ├── benchmark_config.json   # 划分/指标/基线配置
    ├── splits/                 # train/test划分
    └── results/                # 实验结果
```

---

## 四、构建路线图

### Phase 1: 聚合条目层 (方向A基础)
1. 从id_registry构建971个聚合条目(含全部位置内容)
2. 抽样200-300个多位置ID做上下文关联评测数据
3. 定义方向A评测协议(按模态P/R/F1)

### Phase 2: 不一致性Gold Standard补全 (方向B)
1. 版本矛盾: 25条version_pairs标注(2真实+23一致)
2. 追溯断裂: 450个候选人工验证筛选
3. 约束矛盾: 从环境表提取数值约束, 检测冲突
4. sc4/sc5/sc7/sc8场景补全

### Phase 3: Benchmark固化
1. 正式train/test划分(文档级)
2. 评测runner实现
3. baseline库(多数类/字符级/LLM/NLI)
4. 统计显著性(bootstrap+McNemar)

### Phase 4: 论文实验
1. 方向A评测(上下文关联)
2. 方向B评测(不一致检测)
3. 端到端评测(QA对)
4. 消融实验
