# 01 数据资产 (Data Assets)

> 整合自: dataset_architecture_v2 / dataset_panorama / dataset_roadmap_v1 / data_design / network_chartarena_zh / scene_dataset_matching
> 最后更新: 2026-08-10

---

## 一、数据源与架构

### 原始数据（16份GJB 438C SRS）

```
data/gjb_438c/
├── mineru_standard/         16份文档 × 3件套(md + content_list.json + images/fig_*.png)
│   └── 01~16/office/
│       ├── *.md             Markdown(文本+表格HTML, 图片引用100%有效)
│       ├── *_content_list.json  MinerU结构化(图片路径98%有效)
│       └── images/fig_*.png  372张真实图片(LibreOffice从.doc提取)
├── dual_source/             16份textutil独立解析(HTML, 用于双源验证)
├── pair_dataset/            319实例配对(图片+表格CSV+正文TXT+meta)
└── data_assets/             结构化资产(见下)
```

### 三层数据架构

```
方向A(上下文关联) → 聚合条目 → 方向B(不一致性校验) → 检测结果
     ↓                    ↓                    ↓
  评测数据1            评测数据2            评测数据3
 (上下文关联Gold)    (不一致性Gold)        (QA对, 端到端)
```

### 来源标注原则

- `source: "native"` — 16份GJB SRS（主实验）
- `source: "network"` — 网络增强（泛化测试，隔离评测）
- 网络数据只做泛化测试，不参与主实验

---

## 二、结构化资产（data_assets/）

### 2.1 stage0_assets.json (8类资产)

| 资产 | 数量 | 说明 |
|------|------|------|
| section_registry | 1444章节 | 16文档章节层级 |
| id_registry | 971唯一ID / 2016出现位置 | 多位置聚合基础 |
| table_index | 1207表格 | capability/usecase/interface等 |
| figure_index | 381图片(372有文件) | 图片类型分类 |
| traceability_map | 1022追溯边 | 合格性表/追溯表映射 |
| interface_topology | 1414接口记录 | 接口属性(类型/发送方/接收方) |
| version_pairs | 25条(去重后) | 版本记录(2个真实矛盾) |
| exception_flows | 426异常流(8悬空) | 异常流定义/引用 |

### 2.2 semantic_modality_data.json (8场景)

| 场景 | 定义 | 实例 |
|------|------|------|
| sc1 | 用例图+capability表+正文 | 137 |
| sc2 | 流程图+usecase表+正文 | 82 |
| sc3 | 接口图+interface表+正文 | 32 |
| sc4 | 流程图+capability表+正文 | 26 |
| sc5 | 功能图+capability表+正文 | 11 |
| sc6 | 功能框架图+其他表+正文 | 8 |
| sc7 | 用例图+usecase表+正文 | 6 |
| sc8 | 纯图片+正文 | 17 |

### 2.3 其他资产

| 文件 | 内容 |
|------|------|
| dataset_inventory.json | 16文档全量统计清单 |
| capability_descriptions.json | 555行capability表(名称+描述) |
| usecase_features.json | 406条usecase特征(uc_name+actors) |
| vlm_usecase_extract.jsonl | 136张用例图VLM提取(Actor/UC名) |
| graph/ | ID-Graph方法资产(见02_method_design) |
| gold_standard/ | 评测数据(见03_quality_assurance) |

### 2.4 网络增强（source=network）

| 数据集 | 规模 | 用途 |
|--------|------|------|
| ChartArena中文 | 1209条 | 中文图表一致性泛化(流程图154条匹配sc2) |

> 已评估并排除: PURE(无图无表)/FinBalance(任务不匹配)/ScholScan(样本不足)

---

## 三、配对数据集（pair_dataset/）

```
data/gjb_438c/pair_dataset/
├── sc1_usecase_capability/   137实例
├── sc2_flowchart_usecase/    82实例
├── sc3_interface_interface/  32实例
├── sc4_flowchart_capability/ 26实例
├── sc5_function_capability/  11实例
├── sc6_framework_other/       8实例
├── sc7_usecase_usecase/       6实例
├── sc8_pure_image/           17实例
└── README.md                 索引
```

每个实例 = `image.png + table.csv + text.txt + meta.json`

---

## 四、数据质量保证（摘要）

| 验证 | 方法 | 结果 |
|------|------|------|
| 真实矛盾真实性 | 双源独立解析(mineru+textutil) | 31/31 = 100% |
| Gold Standard标注 | kimi+claude双模型交叉 | 92%一致, 真实100% |
| VLM无幻觉 | OCR交叉+claude确认 | 10/10无幻觉 |
| 图片路径 | content_list vs MD | 99%/100%有效 |

> 详细见 03_quality_assurance.md

---

## 五、网络数据集匹配结论

| 场景 | 匹配 | 说明 |
|------|------|------|
| sc1/sc7 用例图+文本 | ✅ PlantUML三件套 | 英文, 无capability表 |
| sc2 时序图+文本 | ✅ MCeT(Huawei) | 唯一带图-文不一致标注 |
| sc8 文档图文 | ✅ OmniDocBench等 | 中英文档 |
| sc3-sc6 GJB特有图型 | ❌ 无匹配 | 公开数据集无对应 |

---

## 六、待构建方向（路线图摘要）

1. **方向A评测数据**: 实体→gold上下文集(查询→召回评测) — 最大缺口
2. **不一致性类型补全**: 版本/追溯断裂/约束矛盾
3. **场景覆盖补全**: sc4/5/6/7/8的Gold Standard
4. **评测基础设施**: 正式划分/runner/baseline库/统计显著性
