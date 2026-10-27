# 项目数据管理重构方案

## 一、问题诊断

当前项目的数据管理存在三个核心问题：

1. **数据产出脚本分散**：37个evalsets JSON来自20+个不同脚本，同一场景有多个"版本"的数字（如M3-colbert在deep_v1有三个值：0.347/0.364/0.372），没有唯一权威来源
2. **废弃数据未清理**：大量历史产物（qgpt_oracle、deep_v2_variants等）仍在evalsets目录，与新数据混在一起
3. **构建脚本无归档机制**：246个tools脚本中约200个是一次性实验脚本，废弃后仍留在主目录

## 二、新目录结构

```
data/gjb_438c/data_assets/
├── evalsets/
│   ├── V3/                              # ← 当前唯一活跃版本
│   │   ├── gjb_ure_v3.json             # 自有数据集(修复S2+S3后)
│   │   ├── wtq_ure.json                # 公开数据集(不变)
│   │   ├── fetaqa_ure.json             # 公开数据集(不变)
│   │   ├── duret_ure.json              # 公开数据集(不变)
│   │   └── pure_mmqa_ure.json          # 公开数据集(不变)
│   ├── archive/                          # 归档(不再使用, 可追溯)
│   │   ├── v1/                          # 所有v1版本
│   │   ├── v2/                          # 所有v2版本
│   │   └── experiments/                 # 一次性实验产物
│   └── results/                          # 评测结果(每个方法一个JSON)
│       ├── S1_deep_v2_all_methods.json  # 统一262q全方法
│       ├── S2_caption_all_methods.json
│       ├── S3_deep_v1_all_methods.json
│       ├── S4_image_all_methods.json
│       ├── WTQ_all_methods.json
│       ├── FeTaQA_all_methods.json
│       ├── DuRetrieval_all_methods.json
│       ├── PURE_MMQA_all_methods.json
│       └── _matrix.json                 # 汇聚矩阵(从上述JSON生成)
```

## 三、数据生命周期规范

### 3.1 数据版本规则

每个数据集有唯一"当前版本"（V3/），历史版本进archive/。版本号递增在以下情况触发：
- gold标注方式变更（如S3的image gold从共址改为内容验证）
- 查询集变更（如S2的深行查询扩展到16文档）
- 协议变更（如统一查询前缀）

### 3.2 评测结果规则

1. **每个场景一个JSON**，所有方法在同一查询集上跑完
2. **JSON内必须记录查询集哈希**：`"query_set_sha": "..."`，拼表时自动校验
3. **per-query预测存档**：每次评测的top-20预测ID列表入runs/目录
4. **单一来源**：汇聚矩阵只能从`results/`下的JSON生成，不能手动填数字

### 3.3 脚本生命周期规则

```
tools/
├── build/          # 数据构建脚本(有且仅有一个入口)
├── eval/           # 评测脚本(每个场景一个)
├── analysis/       # 分析/可视化脚本
├── archive/        # 归档脚本(按日期分目录)
│   ├── 2026_09/    # 9月的实验脚本
│   └── 2026_10/    # 10月的实验脚本
└── ai_config.py    # 配置(不归档)
```

## 四、修复S1-S3的行动计划

### S1修复：统一重跑

```bash
# 在262q上重跑所有方法，产出 S1_deep_v2_all_methods.json
python tools/eval/unified_eval.py --scene deep_v2 --all-methods
```

### S2修复：扩展深行查询

```bash
# 生成16文档×每表≤5条=约300条查询
python tools/build/gen_deep_v3.py --docs all --max-per-table 5 --anti-copy
```

### S3修复：image gold内容验证

```bash
# 用VLM/锚点内容验证gold，替换共址代理
python tools/build/fix_image_gold.py --method content_verification
```

## 五、MANIFEST规范

MANIFEST只保护`V3/`和`results/`下的文件。archive/下的文件不保护（可自由删除）。MANIFEST条目增加：

```json
{
  "path": "evalsets/V3/gjb_ure_v3.json",
  "sha256": "...",
  "built_by": "tools/build/build_gjb_v3.py",
  "built_at": "2026-10-10T...",
  "query_count": {"image": 1007, "table_caption": 500, "table_deep_v3": 300},
  "supersedes": "evalsets/archive/v2/gjb_ure_v2.json"
}
```
