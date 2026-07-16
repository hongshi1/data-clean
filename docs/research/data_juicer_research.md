# Data-Juicer 时序数据算子调研与实践报告

> 实践时间: 2026-07-01 | 实践目录: `data_clean/` | Data-Juicer 源码: `../data-juicer/`

---

## 1. Data-Juicer 框架架构分析

### 1.1 安装状态
Data-Juicer **未通过 pip 安装**到系统 Python,但工作区存在本地克隆源码:
- 源码路径: `/Users/gexuancheng/Desktop/research2/data-juicer/`
- 配套 venv: `data-juicer/.venv/` (含 sklearn 1.9.0 / transformers 5.12.1 / torch 2.12.1 / pandas 3.0.4)
- 通过 `sys.path.insert(0, ".../data-juicer")` 即可 import,`run_pipeline.py` 即采用此方式。

### 1.2 算子体系 (Operators)
算子基类定义于 `data_juicer/ops/base_op.py`,体系如下:

| 基类 | 职责 | 核心方法 | 数据流向 |
|------|------|----------|----------|
| `OP` | 根基类 | `run(dataset)` | — |
| **`Mapper(OP)`** | 数据编辑 | `process_single(sample) → sample` | 样本→样本(可增删改字段) |
| **`Filter(OP)`** | 过滤 | `compute_stats_single(sample) → sample` + `process_single(sample) → bool` | 先算统计,再按布尔保留/丢弃 |
| `Deduplicator(OP)` | 去重 | `compute_hash(sample)` + `process(dataset)` | 数据集级去重 |
| `Selector(OP)` | 选择 | `process(dataset)` | 数据集→数据集 |
| `Grouper/Aggregator` | 分组/聚合 | `process` | 多样本聚合 |

关键运行机制 (`base_op.py:832-864` Filter.run):
```
dataset.map(compute_stats)   # 第一遍: 计算统计量写入 Fields.stats
    ↓
dataset.filter(process)      # 第二遍: process_single 返回 True 保留 / False 丢弃
```
Mapper.run (`base_op.py:685-714`) 则单遍 `dataset.map(process)` 直接改写样本。

### 1.3 注册机制
- `OPERATORS = Registry("Operators")` (`base_op.py:22`),基于 modelscope 的 `Registry` 类。
- 装饰器注册: `@OPERATORS.register_module("op_name")` 将类注入注册表。
- YAML 配置引用: `process:` 列表中直接写算子名,框架经 `load_ops` 从注册表实例化。
- **自定义算子加载**: YAML 顶层 `custom_operator_paths: [绝对路径]` 让框架 import 外部 .py 文件并触发装饰器注册,**无需 fork 源码**。

### 1.4 数据格式
- 输入输出: **JSONL**,每行一条记录。
- 标准字段: `text`(文本)、`images`(图片路径列表)、`audios`/`videos`(多模态)。
- 用户自定义: `meta`(dict,放 csv_path / defect_label 等业务字段)。
- DJ 内部特殊字段(`data_juicer/utils/constant.py`):
  - `Fields.stats = "__dj__stats__"` — Filter 写入统计量的字段
  - `Fields.meta = "__dj__meta__"` — Mapper 写入元数据的字段
  - `Fields.source_file = "__dj__source_file__"`
- 底层载体: `NestedDataset`,基于 HuggingFace `datasets` 的 Arrow 格式,支持 `from_json` / `map` / `filter`。

---

## 2. 现有自定义算子 welding_conflict_filter.py 分析

文件: `welding_conflict_filter.py` (128行)

| 维度 | 说明 |
|------|------|
| **基类** | `Filter` (`from data_juicer.ops.base_op import OPERATORS, Filter`) |
| **注册** | `@OPERATORS.register_module("welding_conflict_filter")` |
| **CSV读取** | `_read_csv_stats()` 用 `csv.DictReader` 读取,提取4列: `Primary Weld Current` / `Secondary Weld Voltage` / `Pressure` / `CO2 Weld Flow` |
| **统计** | 手写计算 mean/max/min/std (纯 Python,无 pandas) |
| **冲突检测** | `_check_conflict()` 规则引擎,按 `defect_label` 分支:<br>• 烧穿: 要求电流峰值≥150A、电压≥40V<br>• 裂纹: 要求电流std≥50、峰值≥150A<br>• 熔合不良: 要求电流均值≤150A、峰值≤220A<br>• 正常: 要求峰值≤250A、std≤120A |
| **输入** | JSONL 记录: `meta.csv_path` 指向 CSV, `meta.defect_label` 为标签 |
| **输出** | 写入 `Fields.stats`: `welding_sensor_stats` / `welding_conflict` / `welding_conflict_reason` |
| **process_single** | 恒返回 `True`(保留全部) — 实际是"统计累积型"Filter,不做真正过滤,仅记录冲突供下游分析 |

**特点与局限**:
1. 阈值硬编码(如 150A),缺乏数据驱动自适应。
2. 逐样本读 CSV,I/O 为瓶颈;未用 batched 版本。
3. `process_single` 不丢弃样本,仅标记,适合"体检报告"场景。

---

## 3. 新增三个时序算子设计与实现

文件: `timeseries_operators.py` (实践产物)

### 3.1 TimeSeriesAnomalyFilter — 时序异常检测 Filter
- **继承**: `Filter`
- **注册名**: `time_series_anomaly_filter`
- **输入**: `meta.csv_path` → CSV 时序文件
- **处理**:
  1. `_read_csv_series()` 读取 4 路信号(电流/电压/气压/CO2)
  2. 每个时间点视为 4 维样本,构建特征矩阵
  3. `sklearn.ensemble.IsolationForest` 拟合并预测异常时间点
  4. `anomaly_score = 异常时间点数 / 总时间点数` (0~1)
  5. 同时计算各路信号的 `mean/std/max/min`
- **输出**: 写入 `Fields.stats` → `ts_anomaly_score` / `ts_anomaly_reason` / `ts_signal_stats`
- **过滤**: `process_single` 返回 `anomaly_score < threshold`(默认 0.5)
- **参数**: `threshold=0.5`, `contamination=0.1`, `random_state=42`

### 3.2 TimeSeriesStatsMapper — 焊接段统计 Mapper
- **继承**: `Mapper`
- **注册名**: `time_series_stats_mapper`
- **输入**: `meta.csv_path` → CSV
- **处理**:
  1. 读取 CSV
  2. **筛选焊接段**: `Primary Weld Current > 10A`(非焊接区间电流≈0,需剔除)
  3. 在焊接段内计算: `CO2均值` / `压力均值` / `电流std` / `电压std` / `电流均值` / `电压均值`
- **输出**: 写入 `sample['meta']['ts_stats']`(Mapper 直接改写样本)
- **特点**: 与 Filter 不同,Mapper 不丢弃样本,而是**增补字段**,供下游算子或训练使用。

### 3.3 CrossModalConflictFilter — 跨模态冲突检测 Filter
- **继承**: `Filter`
- **注册名**: `cross_modal_conflict_filter`
- **输入**: `images[0]`(图片) + `meta.csv_path`(时序) + `meta.defect_label`(文本标签)
- **处理** (三模态两两校验):
  1. **图像侧(CLIP零样本分类)**: 用 4 类缺陷候选文本(裂纹/熔合不良/正常/烧穿,中英双 prompt)与图片算 CLIP 相似度,softmax 后取概率最高者为"图像预测缺陷类型"。模型缓存于类属性 `_CLIP_CACHE`,避免重复加载。
  2. **时序侧**: 复用 IsolationForest 算 `ts_anomaly_score`
  3. **冲突判定** `_detect_conflict()`:
     - 图像-标签冲突: CLIP 预测类型 ≠ 标签 且 预测概率 ≥ 0.2
     - 时序-标签冲突: 标签"正常"但异常分>0.3;或标签为缺陷但异常分<0.02(时序几乎无异常却标缺陷)
- **输出**: `Fields.stats` → `clip_pred_label` / `clip_label_scores` / `ts_anomaly_score` / `cross_modal_conflict` / `cross_modal_conflict_reasons`
- **过滤**: `process_single` 返回 `not conflict`(有冲突则丢弃)

---

## 4. 测试结果

测试脚本: `run_timeseries_test.py` (直接调用算子,与 `run_dj_pipeline.py` 验证方式一致)
测试数据: `h4r_welding.jsonl` (4 条样本: 裂纹 / 熔合不良 / 正常 / 烧穿)
结果文件: `output_ts/ts_operators_results.json`

### 4.1 TimeSeriesStatsMapper (焊接段统计)
| 标签 | 焊接段点数 | 占比 | CO2均值 | 压力均值 | 电流std | 电压std |
|------|-----------|------|---------|----------|---------|---------|
| 裂纹 | 202 | 0.667 | 13.226 | 0.281 | 12.956 | 1.389 |
| 熔合不良 | 181 | 0.653 | 47.643 | 2.056 | 38.406 | 6.041 |
| 正常 | 242 | 0.720 | 14.256 | 0.138 | 15.906 | 1.340 |
| 烧穿 | 218 | 0.688 | 12.669 | 0.074 | 20.528 | 3.074 |

> 熔合不良样本 CO2均值(47.6)和压力均值(2.06)显著偏高,电压std(6.04)最大,符合"气体/电压不稳导致熔合不良"的物理直觉。

### 4.2 TimeSeriesAnomalyFilter (IsolationForest 异常检测)
| 标签 | 异常分 | 保留 | 电流mean/std/max | 说明 |
|------|--------|------|------------------|------|
| 裂纹 | 0.1023 | ✓ | 171.3 / 121.4 / 267.9 | 31/303点异常 |
| 熔合不良 | 0.1011 | ✓ | 106.8 / 83.7 / 254.3 | 28/277点异常 |
| 正常 | 0.1012 | ✓ | 124.4 / 78.6 / 229.9 | 34/336点异常 |
| 烧穿 | 0.1009 | ✓ | 106.8 / 73.8 / 205.0 | 32/317点异常 |

> contamination=0.1,故各样本异常分≈0.10,均<0.5阈值全部保留。裂纹样本电流std(121.4)最高,波动最大,与其"电流不稳致裂"特征一致。

### 4.3 CrossModalConflictFilter (跨模态冲突检测)
| 标签 | CLIP预测 | 保留 | 冲突 | 冲突原因 |
|------|----------|------|------|----------|
| 裂纹 | 正常(p=0.42) | ✗ | ✓ | 图像-标签冲突: CLIP判为正常,标签为裂纹 |
| 熔合不良 | 正常(p=0.38) | ✗ | ✓ | 图像-标签冲突: CLIP判为正常,标签为熔合不良 |
| 正常 | 正常(p=0.51) | ✓ | ✗ | 无冲突 |
| 烧穿 | 烧穿(p=0.51) | ✓ | ✗ | 无冲突 |

> **检出 2 条冲突**: 裂纹和熔合不良的图像在 CLIP 看来视觉上接近"正常焊缝",与缺陷标签矛盾。烧穿图像因有孔洞特征,CLIP 正确识别。这是一个有意义的跨模态信号 —— 提示这两条数据的图像可能不足以支撑其缺陷标签,需人工复核。

### 4.4 汇总
```
异常检测保留: 4/4   (阈值0.5,均通过)
冲突检测保留: 2/4   (检出2条图像-标签冲突)
检出冲突:     2/4
```

---

## 5. YAML 配置示例

文件: `config_timeseries.yaml`
```yaml
dataset_path: .../h4r_welding.jsonl
work_dir: .../output_ts
np: 1
custom_operator_paths:
  - .../timeseries_operators.py      # 外部算子注册
stats_export_path: .../ts_stats_report.json
process:
  - time_series_stats_mapper:         # Mapper: 焊接段统计
      current_threshold: 10.0
  - time_series_anomaly_filter:       # Filter: IsolationForest异常
      threshold: 0.5
      contamination: 0.1
      stats_export_path: .../anomaly_stats.json
  - cross_modal_conflict_filter:      # Filter: CLIP+时序+标签
      hf_clip: openai/clip-vit-base-patch32
      clip_score_threshold: 0.2
      ts_anomaly_threshold: 0.3
      stats_export_path: .../conflict_stats.json
```

配置要点:
1. `custom_operator_paths` 指向 `timeseries_operators.py`,import 时触发 3 个 `@OPERATORS.register_module` 注册。
2. 算子顺序: **Mapper 先行**(增补 `ts_stats`)→ 异常 Filter → 冲突 Filter,符合"先丰富特征再过滤"的管道设计。
3. 每个 Filter 可设 `stats_export_path` 导出统计报告。

---

## 6. 对三层治理框架的贡献 (L1/L2/L3)

| 层级 | 定义 | 可用算子 | 作用 |
|------|------|----------|------|
| **L1 单模态质量** | 单一模态内部的基础质量校验 | `TimeSeriesAnomalyFilter`(时序)<br>`TimeSeriesStatsMapper`(时序特征)<br>DJ内置: `language_id_filter`/`text_length_filter`/`image_aspect_ratio_filter` | 时序信号统计、IsolationForest异常点检测、焊接段特征提取 |
| **L2 跨模态一致性** | 多模态间的相互校验 | `CrossModalConflictFilter`(图像↔时序↔标签)<br>`welding_conflict_filter`(时序↔标签)<br>DJ内置: `image_text_similarity_filter`(图像↔文本) | CLIP零样本分类对比标签、时序异常对比标签、图文相似度 |
| **L3 全局治理** | 数据集级去重/溯源/版本/合规 | DJ内置: `minhash_deduplicator`/`document_deduplicator`(去重)<br>`Selector`(数据集选择)<br>`stats_export_path` + tracer(溯源) | 时序指纹去重、统计报告导出、处理轨迹追踪 |

**关键洞察**:
- 新增的 3 个算子填补了 Data-Juicer 在**时序模态**上的空白(原框架仅原生支持文本/图像/音频/视频)。
- `TimeSeriesStatsMapper`(L1) 为 L2 的 `CrossModalConflictFilter` 提供特征基础 —— 体现"Mapper 丰富特征 → Filter 消费特征"的管道协作。
- `CrossModalConflictFilter` 实现了真正的**三模态联合校验**(图像CLIP + 时序IsolationForest + 文本标签),是 L2 的核心。

---

## 7. 产物清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `timeseries_operators.py` | 代码 | 3 个新算子实现 (TimeSeriesAnomalyFilter / TimeSeriesStatsMapper / CrossModalConflictFilter) |
| `config_timeseries.yaml` | 配置 | 时序处理管道 YAML |
| `run_timeseries_test.py` | 测试 | 算子直调测试脚本 |
| `output_ts/ts_operators_results.json` | 结果 | 测试输出 (4样本完整结果) |
| `data_juicer_research.md` | 报告 | 本调研报告 |
