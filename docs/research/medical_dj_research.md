# 医疗多模态数据知识库冲突检测 — Data-Juicer 调研与实现规划

> 调研时间: 2026-07-01 | 工作目录: `data_clean/` | Data-Juicer 源码: `../data-juicer/`

---

## 一、Data-Juicer 框架分析

### 1.1 算子体系（基类 + 注册机制）

算子基类定义于 `data-juicer/data_juicer/ops/base_op.py`，体系如下：

| 基类 | 职责 | 核心方法 | 数据流向 |
|------|------|----------|----------|
| `OP` (`base_op.py:289`) | 根基类 | `run(dataset)` | — |
| **`Mapper(OP)`** (`base_op.py:606`) | 数据编辑/增补字段 | `process_single(sample) → sample` | 样本→样本（可增删改字段） |
| **`Filter(OP)`** (`base_op.py:717`) | 过滤 | `compute_stats_single(sample) → sample` + `process_single(sample) → bool` | 先算统计，再按布尔保留/丢弃 |
| `Deduplicator(OP)` (`base_op.py:867`) | 去重 | `compute_hash(sample)` + `process(dataset)` | 数据集级去重 |
| `Selector(OP)` (`base_op.py:933`) | 选择 | `process(dataset)` | 数据集→数据集 |
| `Grouper/Aggregator` (`base_op.py:975/1020`) | 分组/聚合 | `process` | 多样本聚合 |
| `Pipeline(OP)` (`base_op.py:1083`) | 管道嵌套 | `run(dataset)` | 子算子串行 |

**Filter 的两阶段运行机制**（`base_op.py:832-864` `Filter.run`）：
```
第一遍: dataset.map(compute_stats)   → 计算统计量写入 sample[Fields.stats]
第二遍: dataset.filter(process)      → process_single 返回 True 保留 / False 丢弃
```
- `compute_stats_single(sample, context=False)` (`base_op.py:811`)：接收样本，计算统计指标后写回 `sample[Fields.stats]`，返回 sample。
- `process_single(sample)` (`base_op.py:823`)：从 `sample[Fields.stats]` 读取统计量，返回布尔值决定保留/丢弃。
- 两阶段分离的好处：统计量可被 `stats_export_path` 导出供分析，且多个 Filter 可复用已算好的 stats。

**Mapper 的单阶段运行机制**（`base_op.py:685-714` `Mapper.run`）：
```
单遍: dataset.map(process)   → process_single 直接改写 sample（增/删/改字段）
```
- `process_single(sample)` (`base_op.py:676`)：接收样本，处理后返回新样本。常用于增补特征字段写入 `sample[Fields.meta]`。

> 关键约束：子类**不可**重写 `process` / `compute_stats`（`base_op.py:639-648`、`base_op.py:771-781` 会抛 `TypeError`），必须实现 `_single` 后缀方法。

**注册机制**：
- `OPERATORS = Registry("Operators")` (`base_op.py:22`)，基于 modelscope 的 `Registry` 类。
- 装饰器注册：`@OPERATORS.register_module("op_name")` 将类注入注册表。
- YAML 配置引用：`process:` 列表中直接写算子名，框架经 `load_ops` 从注册表实例化。
- **自定义算子加载**：YAML 顶层 `custom_operator_paths: [绝对路径]` 让框架 import 外部 .py 文件并触发装饰器注册，**无需 fork 源码**。

### 1.2 数据格式（JSONL + Fields.stats）

- 输入输出：**JSONL**，每行一条记录。
- 标准字段（`OP.__init__` `base_op.py:396-409`）：
  - `text`（文本，默认 key=`"text"`）
  - `images`（图片路径列表，默认 key=`"images"`）
  - `audios` / `videos`（多模态路径列表）
  - `meta`（用户自定义 dict，放业务字段）
- DJ 内部特殊字段（`data-juicer/data_juicer/utils/constant.py:19-37`）：
  - `Fields.stats = "__dj__stats__"` — Filter 写入统计量的 dict 字段
  - `Fields.meta = "__dj__meta__"` — Mapper 写入元数据的 dict 字段
  - `Fields.source_file = "__dj__source_file__"` — 溯源字段
  - `Fields.batch_meta = "__dj__batch_meta__"` — Aggregator 聚合字段
- 底层载体：`NestedDataset`，基于 HuggingFace `datasets` 的 Arrow 格式，支持 `from_json` / `map` / `filter`。
- `StatsKeys`（`constant.py:317-403`）定义了大量预置统计键名常量（如 `llm_quality_score`、`image_text_similarity` 等），自定义算子可直接用字符串 key 而无需引用常量类。

**Fields.stats 工作示例**：
```python
# compute_stats_single 中写入
stats = sample.get(Fields.stats, {})
stats["my_metric"] = 0.85          # 中间结果
stats["my_reason"] = "某原因"       # 可放任意可序列化对象
sample[Fields.stats] = stats
return sample

# process_single 中读取
stats = sample.get(Fields.stats, {})
return stats.get("my_metric", 0) < threshold
```

### 1.3 YAML 编排方式

```yaml
dataset_path: /path/to/input.jsonl      # 输入数据
work_dir: /path/to/output               # 工作目录
np: 1                                   # 进程数
custom_operator_paths:                  # 外部算子注册（import 时触发 @OPERATORS.register_module）
  - /abs/path/to/my_operators.py
stats_export_path: /path/to/report.json # 全局统计报告导出

process:                                # 算子按顺序串行执行
  - operator_name_1:                    # Mapper 先行：增补特征
      param1: value1
  - operator_name_2:                    # Filter 随后：基于特征过滤
      param2: value2
      stats_export_path: /path/to/op2_stats.json  # 每个Filter可单独导出stats
```

编排要点：
1. `custom_operator_paths` 指向自定义 .py，import 时触发注册。
2. 算子顺序遵循"**Mapper 丰富特征 → Filter 消费特征**"的管道设计。
3. 每个 Filter 可设 `stats_export_path` 导出该算子的统计报告（含被过滤样本的统计信息）。
4. 算子参数直接在算子名下缩进书写，框架传给构造函数 `__init__`。

### 1.4 现有自定义算子分析

#### 1.4.1 `timeseries_operators.py`（386行，3个算子，焊接场景）

| 算子 | 基类 | 注册名 | 输入 | 处理 | 输出 |
|------|------|--------|------|------|------|
| `TimeSeriesAnomalyFilter` | Filter | `time_series_anomaly_filter` | `meta.csv_path` | IsolationForest检测4路时序异常点，算异常比例 | stats: `ts_anomaly_score`/`ts_anomaly_reason`/`ts_signal_stats` |
| `TimeSeriesStatsMapper` | Mapper | `time_series_stats_mapper` | `meta.csv_path` | 筛选焊接段(电流>10A)，算CO2/压力/电流/电压统计 | `meta.ts_stats` |
| `CrossModalConflictFilter` | Filter | `cross_modal_conflict_filter` | `images[0]`+`meta.csv_path`+`meta.defect_label` | CLIP零样本图像分类 + 时序异常 + 标签，三模态两两校验冲突 | stats: `clip_pred_label`/`ts_anomaly_score`/`cross_modal_conflict`/`cross_modal_conflict_reasons` |

关键设计模式（可复用于医疗场景）：
- **CLIP 模型缓存于类属性** `_CLIP_CACHE`（`timeseries_operators.py:227`），避免每条样本重复加载。
- **stats 幂等检查**：`if "xxx" in stats: return sample`（`:93`、`:364`），防止重复计算。
- **冲突判定与原因记录分离**：`_detect_conflict()` 返回 `(是否冲突, 原因列表)`，原因列表写入 stats 供报告使用。
- **process_single 不一定丢弃**：冲突检测可设为仅标记（返回 True 保留），将过滤决策交给下游。

#### 1.4.2 `welding_conflict_filter.py`（128行，1个算子）

- 基类：Filter，注册名：`welding_conflict_filter`
- 规则引擎式冲突检测：`_check_conflict()` 按标签分支（烧穿/裂纹/熔合不良/正常），用硬编码阈值（如电流峰值≥150A）判定传感器数据与标签是否冲突。
- `process_single` 恒返回 True（`:127`）— **统计累积型 Filter**，仅标记冲突不做真正过滤，适合"体检报告"场景。
- 局限：阈值硬编码、逐样本读 CSV 无 batched 版本。

### 1.5 内置 LLM / 知识相关算子清单

Data-Juicer 内置 **6 个 LLM Filter** + **2 个 LLM/MLLM Mapper**，但**无医疗/规则引擎专用算子**。

#### LLM Filter 算子（`data-juicer/data_juicer/ops/filter/`）

| 算子文件 | 注册名 | 功能 | 知识库支持 |
|----------|--------|------|-----------|
| `llm_analysis_filter.py` | `llm_analysis_filter` | LLM多维度评分(clarity/relevance/usefulness/fluency 1-5分)+标签+建议 | 否 |
| `llm_quality_score_filter.py` | `llm_quality_score_filter` | 继承LLMAnalysisFilter，评分维度改为accuracy/grammar/informativeness/coherence | 否 |
| `llm_difficulty_score_filter.py` | `llm_difficulty_score_filter` | LLM评估样本难度 | 否 |
| `llm_perplexity_filter.py` | `llm_perplexity_filter` | LLM计算困惑度 | 否 |
| `llm_task_relevance_filter.py` | `llm_task_relevance_filter` | LLM评估任务相关性 | 否 |
| **`llm_condition_filter.py`** | `llm_condition_filter` | **用户给定自然语言条件，LLM返回yes/no过滤** | **✓ 支持 `knowledge_grounding_key`/`knowledge_grounding_fixed`** |

> **`llm_condition_filter` 是最契合知识库冲突检测的内置算子**：它支持 `knowledge_grounding_fixed`（固定知识字符串）和 `knowledge_grounding_key`（每条样本动态知识字段），可将医学知识库作为 grounding 注入 LLM prompt（`llm_condition_filter.py:111-118`、`120-165`）。

#### LLM/MLLM Mapper 算子（`data-juicer/data_juicer/ops/mapper/`）

| 算子文件 | 注册名 | 功能 |
|----------|--------|------|
| `llm_extract_mapper.py` | `llm_extract_mapper` | LLM结构化抽取，用户自定义 `output_schema`，结果写入 `meta` |
| `mllm_mapper.py` | `mllm_mapper` | 多模态LLM（MLLM），可对图像+文本联合推理，**可用于CXR胸片分析** |

#### 可复用的非LLM算子

| 算子 | 文件 | 可复用场景 |
|------|------|-----------|
| `specified_numeric_field_filter` | `specified_numeric_field_filter.py` | 按指定数值字段范围过滤（支持多级key，`meta.xxx`），**可做单指标范围检查** |
| `specified_field_filter` | `specified_field_filter.py` | 按指定字段值过滤 |
| `image_text_similarity_filter` | `image_text_similarity_filter.py` | 图文相似度（CLIP），可做CXR与诊断文本一致性校验 |

---

## 二、医疗多模态数据现状

### 2.1 数据模态构成（4模态）

数据文件：`medical_data/medtvt/train.csv`（10000行 × 110列）

| 模态 | 字段 | 说明 |
|------|------|------|
| **胸片CXR（图像）** | `cxr_path` | 相对路径 `files/p17/p17628012/s51943003/xxx.jpg`，指向MIMIC-CXR-JPG |
| **心电ECG（时序）** | `ecg_path` | 相对路径 `files/p1762/p17628012/s46857043/46857043`，指向MIMIC-IV-ECG |
| **血检（表格）** | 50个itemid列（`51221`...`52135`） | 数值型，含缺失值；另有50个对应 `_percentile` 列 |
| **诊断标签** | 6个二值/三值列 | `Atelectasis`/`Cardiomegaly`/`Edema`/`Lung Opacity`/`No Finding`/`Pleural Effusion` |

**诊断标签编码**（1.0=阳性 / -1.0=不确定 / 空=阴性）：

| 标签 | 阳性(1.0) | 不确定(-1.0) | 阴性(空) |
|------|-----------|-------------|---------|
| Atelectasis（肺不张） | 2867 | 588 | 6427 |
| Cardiomegaly（心脏肥大） | 3346 | 450 | 5318 |
| Edema（水肿） | 2067 | 834 | 5327 |
| Lung Opacity（肺部阴影） | 3108 | 223 | 6494 |
| **No Finding（无异常）** | **1368** | 0 | 8632 |
| Pleural Effusion（胸腔积液） | 3618 | 371 | 4310 |

### 2.2 文件可用性

**CXR 和 ECG 文件均不存在**：
- `train.csv` 中 `cxr_path`/`ecg_path` 指向 MIMIC-IV 数据集的相对路径（如 `files/p17/...`）。
- 实测检查前20条样本：CXR 存在=0，ECG 存在=0。`medtvt/` 目录下无 `files/` 目录。
- 这些文件需要 **PhysioNet 凭证审批 + MIMIC-IV 数据访问权限**（Credentialed Health Data License）才能下载。
- **结论**：当前阶段只能基于**血检表格 + 诊断标签**两个模态做冲突检测；CXR/ECG 模态需等 PhysioNet 审批后才能纳入跨模态校验。

### 2.3 50项血检指标清单 + 关键指标正常范围

CSV 中 50 个 lab itemid（MIMIC-IV `d_labitems` 编码），其中 **5 个与已有冲突检测直接相关**：

| itemid | 中文名 | 英文名 | 正常范围 | 单位 | 冲突方向 | 数据统计(min/max/missing) |
|--------|--------|--------|----------|------|----------|---------------------------|
| **50893** | 乳酸 | Lactate | 0.5–2.0 | mmol/L | 偏高=酸中毒 | 2.70 / 18.70 / 1116 |
| **51237** | 肌酐 | Creatinine | 0.6–1.2 | mg/dL | 偏高=肾功能异常 | 0.80 / 16.60 / 1224 |
| **50931** | 血糖 | Glucose | 70–100(空腹)/<140(随机) | mg/dL | 偏高=高血糖 | 7.00 / 1426.00 / 117 |
| **50971** | 钾 | Potassium | 3.5–5.0 | mEq/L | 偏高=高钾血症 | 1.30 / 10.00 / 46 |
| **50820** | pH | pH | 7.35–7.45 | — | 偏低=酸中毒 | 6.55 / 7.67 / 5281 |

> 注：乳酸列 min=2.70，说明该数据集可能已对乳酸异常样本做了筛选/增强（MedTVT benchmark 常见做法）。

其余 45 个 itemid 涵盖血常规/电解质/肝功能/凝血等（部分映射）：

| 类别 | itemid（部分） |
|------|---------------|
| 血常规 | 51221(Hematocrit), 51222(Hemoglobin), 51250(MCV), 51256(RBC), 51301(WBC), 51265(Platelet), 51254(RDW) |
| 电解质 | 50912(Chloride), 50983(Sodium), 50882(Bicarbonate), 50868(Anion Gap), 50960(Magnesium), 50970(Phosphate) |
| 肝功能 | 50861(ALT), 50878(AST), 50863(Alkaline Phosphatase), 50885(Bilirubin), 51146(Bilirubin Total) |
| 凝血 | 51274(PTT), 51275(PT/INR) |
| 血气 | 50821(pO2), 50818(pCO2), 50804(Calculated Total CO2) |
| 其他 | 51006(Urea Nitrogen/BUN), 51200(Eosinophils), 51244(Lymphocytes), 50862(Albumin) |

`labs_means.json` 提供了全部50项的**百分位统计**（各 itemid 的 `_percentile` 值，范围0-1），可用于数据驱动的异常阈值（如取 P95/P99 作为异常上限）。

### 2.4 已有冲突检测结果

结果文件：`medical_data/medtvt/results/medical_conflict_results.json`

```
总样本数:        10000
异常样本数:      1000   (n_anomalies)
标签冲突数:      1368   (n_label_conflicts)
跨模态冲突数:    1444   (n_cross_modal_conflicts)  ← 14.44%
```

**冲突类型分布**（`conflict_by_type`）：

| 冲突类型 | 数量 | 严重度 | 涉及指标 | 正常范围 | 判定逻辑 |
|----------|------|--------|----------|----------|----------|
| 乳酸酸中毒漏诊 | 1160 | CRITICAL | 乳酸(50893) | 0.5–2.0 mmol/L | 乳酸>2.0 但诊断=No Finding |
| 肾功能异常漏诊 | 132 | HIGH | 肌酐(51237) | 0.6–1.2 mg/dL | 肌酐>1.2 但诊断=No Finding |
| 高血糖漏诊 | 68 | MEDIUM | 血糖(50931) | 70–100 mg/dL | 血糖>200 但诊断=No Finding |
| 高钾血症漏诊 | 50 | CRITICAL | 钾(50971) | 3.5–5.0 mEq/L | 钾>5.0 但诊断=No Finding |
| 严重酸中毒漏诊 | 34 | CRITICAL | pH(50820) | 7.35–7.45 | pH<7.35 但诊断=No Finding |

**严重度分布**：CRITICAL=1244，HIGH=132，MEDIUM=68。

> 所有冲突的共性：**血检指标明显异常，但诊断标签为"No Finding（无异常）"** — 即化验结果与放射诊断标签矛盾。这是"化验-诊断"跨模态（表格↔标签）冲突的典型模式。

验证：手动统计 `乳酸(50893)>2.0 且 No Finding` = 1162 例（与检测结果1160基本吻合，差异因缺失值处理）。

---

## 三、知识库冲突检测方案

### 3.1 医学知识库构建方案

#### 3.1.1 知识库内容（三层）

| 层 | 内容 | 形式 | 用途 |
|----|------|------|------|
| **L1 指标正常范围** | 50项血检的itemid→中文名→正常区间→单位→异常方向 | Python dict / JSON | 单指标越界检测 |
| **L2 指标-诊断对应规则** | 异常指标→提示疾病→与诊断标签的冲突判定 | 规则表（条件→结论） | 血检异常 vs 诊断标签 |
| **L3 指标间一致性** | 多指标协同约束（如pH低+Bicarbonate低=代谢性酸中毒；肌酐高+BUN高=肾功能衰竭） | 规则组（多条件AND） | 指标间逻辑一致性 |

#### L1 知识库示例（Python dict）
```python
LAB_RANGES = {
    "50893": {"name": "乳酸", "en": "Lactate", "unit": "mmol/L",
              "normal": (0.5, 2.0), "abnormal_dir": "high",
              "severity_high": {2.0: "MEDIUM", 5.0: "CRITICAL"}},
    "51237": {"name": "肌酐", "en": "Creatinine", "unit": "mg/dL",
              "normal": (0.6, 1.2), "abnormal_dir": "high",
              "severity_high": {1.2: "HIGH", 3.0: "CRITICAL"}},
    "50931": {"name": "血糖", "en": "Glucose", "unit": "mg/dL",
              "normal": (70, 140), "abnormal_dir": "high",
              "severity_high": {200: "MEDIUM", 400: "CRITICAL"}},
    "50971": {"name": "钾", "en": "Potassium", "unit": "mEq/L",
              "normal": (3.5, 5.0), "abnormal_dir": "high",
              "severity_high": {5.0: "HIGH", 6.0: "CRITICAL"}},
    "50820": {"name": "pH", "en": "pH", "unit": "",
              "normal": (7.35, 7.45), "abnormal_dir": "low",
              "severity_low": {7.35: "MEDIUM", 7.20: "CRITICAL"}},
    # ... 其余45项
}
```

#### L2 知识库示例（指标-诊断规则）
```python
LAB_DIAGNOSIS_RULES = [
    {"itemid": "50893", "threshold": 2.0, "direction": "high",
     "suspected": "乳酸酸中毒", "conflict_if": "No Finding",
     "severity": "CRITICAL"},
    {"itemid": "51237", "threshold": 1.2, "direction": "high",
     "suspected": "肾功能异常", "conflict_if": "No Finding",
     "severity": "HIGH"},
    {"itemid": "50931", "threshold": 200, "direction": "high",
     "suspected": "高血糖", "conflict_if": "No Finding",
     "severity": "MEDIUM"},
    {"itemid": "50971", "threshold": 5.0, "direction": "high",
     "suspected": "高钾血症", "conflict_if": "No Finding",
     "severity": "CRITICAL"},
    {"itemid": "50820", "threshold": 7.35, "direction": "low",
     "suspected": "严重酸中毒", "conflict_if": "No Finding",
     "severity": "CRITICAL"},
]
```

#### L3 知识库示例（多指标协同）
```python
CROSS_LAB_RULES = [
    {"name": "代谢性酸中毒", "conditions": [
        {"itemid": "50820", "op": "<", "val": 7.35},
        {"itemid": "50882", "op": "<", "val": 22}],  # Bicarbonate低
     "severity": "CRITICAL"},
    {"name": "肾功能衰竭", "conditions": [
        {"itemid": "51237", "op": ">", "val": 1.2},
        {"itemid": "51006", "op": ">", "val": 20}],  # BUN高
     "severity": "HIGH"},
]
```

#### 3.1.2 知识库来源
- **MIMIC-IV `d_labitems` 表**：itemid→检验项目名称/单位的标准映射（已通过 itemid 反查确认 5 个关键指标）。
- **医学参考范围**：各指标正常区间来自临床检验标准（如 UpToDate、Mayo Clinic 参考值），已在 `medical_conflict_results.json` 的 detail 字段中验证（如"肌酐 正常0.6-1.2"）。
- **数据驱动补充**：`labs_means.json` 提供的百分位统计可用于校准阈值（如取全队列 P99 作为异常上限，避免阈值过严）。
- **现成医学知识库 Python 库**：目前无轻量级、可直接 `pip install` 的医学检验参考范围库。SNOMED CT / UMLS / RadLex 属于大型术语体系（需授权，且面向概念编码非数值范围），不适合直接用于本场景的"数值范围+规则"冲突检测。因此采用**自建轻量知识库**（上述 Python dict），可控且可解释。

### 3.2 怎么编码为 Data-Juicer 算子

将知识库封装为算子类属性或外部 JSON，在 `compute_stats_single` 中查表判定：

```python
@OPERATORS.register_module("lab_diagnosis_conflict_filter")
class LabDiagnosisConflictFilter(Filter):
    # 知识库作为类常量（或从JSON加载）
    LAB_RANGES = { ... }           # L1
    LAB_DIAGNOSIS_RULES = [ ... ]  # L2

    def __init__(self, lab_key_prefix="meta.labs",
                 diag_key="meta.diagnosis", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lab_key_prefix = lab_key_prefix
        self.diag_key = diag_key

    def compute_stats_single(self, sample):
        meta = sample.get("meta", {})
        labs = meta.get("labs", {})        # {"50893": 7.2, "51237": 2.4, ...}
        diagnosis = meta.get("diagnosis", {})
        stats = sample.get(Fields.stats, {})
        if "lab_diag_conflict" in stats:
            return sample

        conflicts = []
        for rule in self.LAB_DIAGNOSIS_RULES:
            val = labs.get(rule["itemid"])
            if val is None:
                continue
            is_abnormal = (val > rule["threshold"]) if rule["direction"]=="high" \
                          else (val < rule["threshold"])
            if is_abnormal and diagnosis.get(rule["conflict_if"]) == 1.0:
                conflicts.append({
                    "type": f"{rule['suspected']}漏诊",
                    "itemid": rule["itemid"],
                    "lab_value": val,
                    "threshold": rule["threshold"],
                    "diagnosis": rule["conflict_if"],
                    "severity": rule["severity"],
                })
        stats["lab_diag_conflict"] = len(conflicts) > 0
        stats["lab_diag_conflict_list"] = conflicts
        stats["lab_diag_conflict_count"] = len(conflicts)
        sample[Fields.stats] = stats
        return sample

    def process_single(self, sample):
        # 仅标记不丢弃（体检报告模式），或返回 not conflict 做过滤
        return True
```

### 3.3 冲突检测逻辑设计

| 冲突类型 | 检测逻辑 | 涉及模态 | 算子归属 |
|----------|----------|----------|----------|
| **A. 单指标越界** | 血检值超出正常范围（L1知识库） | 血检（表格） | `MedicalLabRangeFilter` |
| **B. 血检异常 vs 诊断标签** | 指标异常但诊断=No Finding（L2知识库） | 血检↔标签 | `LabDiagnosisConflictFilter` |
| **C. 多指标协同一致性** | 多指标组合违反医学逻辑（L3知识库，如pH低+Bicarbonate低） | 血检内部 | `CrossLabConsistencyFilter` |
| **D. 诊断标签间一致性** | 同时标注互斥诊断（如No Finding + Atelectasis） | 标签内部 | `DiagnosisConsistencyFilter` |
| **E. CXR vs 标签（未来）** | CLIP/MLLM分析胸片与诊断标签比对 | CXR↔标签 | 待PhysioNet审批后实现 |
| **F. ECG vs 血检（未来）** | 心电异常与钾/肌钙蛋白等比对 | ECG↔血检 | 待PhysioNet审批后实现 |

**严重度分级**：
- CRITICAL：危及生命，必须立即干预（如乳酸>5.0、钾>6.0、pH<7.20）
- HIGH：显著异常需处理（如肌酐>1.2）
- MEDIUM：需关注（如血糖>200）

### 3.4 需要哪些新算子

基于以上设计，需开发 **4个自定义算子 + 1个数据转换工具**：

| 算子/工具 | 基类 | 功能 |
|-----------|------|------|
| `medtvt_data_mapper` | Mapper | CSV→JSONL格式转换，组装 labs/diagnosis/meta 字段 |
| `medical_lab_range_filter` | Filter | L1：单指标正常范围检测 |
| `lab_diagnosis_conflict_filter` | Filter | L2：血检异常 vs 诊断标签冲突 |
| `cross_lab_consistency_filter` | Filter | L3：多指标协同一致性 |
| `diagnosis_consistency_filter` | Filter | D：诊断标签间互斥性检查 |

---

## 四、实现规划

### 4.1 需要开发的自定义算子清单

| # | 算子名 | 基类 | 输入字段 | 处理逻辑 | 输出（写入stats/meta） |
|---|--------|------|----------|----------|------------------------|
| 1 | `medtvt_data_mapper` | Mapper | `meta`（含原始CSV行数据） | 解析50个lab itemid为 `meta.labs` dict；解析6个诊断列为 `meta.diagnosis` dict；保留 cxr_path/ecg_path | `meta.labs`、`meta.diagnosis`、`meta.subject_id` |
| 2 | `medical_lab_range_filter` | Filter | `meta.labs` | 遍历L1知识库，检测每个指标是否越界，记录异常项及严重度 | stats: `lab_abnormal_list`、`lab_abnormal_count`、`lab_abnormal_max_severity` |
| 3 | `lab_diagnosis_conflict_filter` | Filter | `meta.labs`+`meta.diagnosis` | L2规则：指标异常且诊断=No Finding → 冲突 | stats: `lab_diag_conflict`、`lab_diag_conflict_list`、`lab_diag_conflict_count` |
| 4 | `cross_lab_consistency_filter` | Filter | `meta.labs` | L3规则：多指标组合违反医学逻辑 | stats: `cross_lab_conflict`、`cross_lab_conflict_list` |
| 5 | `diagnosis_consistency_filter` | Filter | `meta.diagnosis` | No Finding与其他诊断互斥；同时检查标签编码异常 | stats: `diag_consistency_conflict`、`diag_conflict_reason` |

所有 Filter 的 `process_single` 默认返回 True（**仅标记不丢弃**，体检报告模式），冲突信息全部写入 `Fields.stats` 供报告导出。如需过滤，可配置 `drop_conflict: true`。

### 4.2 YAML 配置设计

```yaml
# config_medical.yaml
dataset_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/medtvt_dj.jsonl
work_dir: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/output_dj
np: 4

custom_operator_paths:
  - /Users/gexuancheng/Desktop/research2/data_clean/medical_operators.py

stats_export_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/output_dj/global_report.json

process:
  # 步骤1 (Mapper): 解析CSV行数据，组装labs/diagnosis结构
  - medtvt_data_mapper:
      lab_itemids: ["50893","51237","50931","50971","50820"]  # 先聚焦5个关键指标
      diagnosis_labels: ["Atelectasis","Cardiomegaly","Edema","Lung Opacity","No Finding","Pleural Effusion"]

  # 步骤2 (Filter): L1 单指标正常范围检测
  - medical_lab_range_filter:
      knowledge_base_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_kb.json
      stats_export_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/output_dj/lab_range_stats.json

  # 步骤3 (Filter): L2 血检异常 vs 诊断标签冲突
  - lab_diagnosis_conflict_filter:
      knowledge_base_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_kb.json
      stats_export_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/output_dj/lab_diag_conflict_stats.json

  # 步骤4 (Filter): L3 多指标协同一致性
  - cross_lab_consistency_filter:
      knowledge_base_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_kb.json
      stats_export_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/output_dj/cross_lab_stats.json

  # 步骤5 (Filter): 诊断标签间一致性
  - diagnosis_consistency_filter:
      stats_export_path: /Users/gexuancheng/Desktop/research2/data_clean/medical_data/medtvt/output_dj/diag_consistency_stats.json
```

### 4.3 数据准备（MedTVT CSV → Data-Juicer JSONL 转换）

需编写转换脚本 `convert_medtvt_to_jsonl.py`，将 `train.csv` 转为 Data-Juicer 兼容的 JSONL：

```python
# 每条 JSONL 记录结构
{
  "text": "",                          # 可放空或患者摘要文本
  "images": ["files/p17/.../xxx.jpg"], # CXR路径（文件暂不存在，保留路径占位）
  "meta": {
    "subject_id": 17628012,
    "hadm_id": 25296721,
    "cxr_path": "files/p17/...",
    "ecg_path": "files/p1762/...",
    "labs": {                          # 50个血检指标
      "50893": 7.2, "51237": 2.4, "50931": 332.0,
      "50971": 6.9, "50820": 7.17, ...
    },
    "diagnosis": {                     # 6个诊断标签（1=阳性,0=阴性,-1=不确定）
      "Atelectasis": 1, "Cardiomegaly": 0, "Edema": 1,
      "Lung Opacity": 1, "No Finding": 0, "Pleural Effusion": 1
    }
  }
}
```

转换要点：
1. 诊断标签 `1.0`→`1`，`空`→`0`，`-1.0`→`-1`（保留不确定标记）。
2. 血检缺失值（空字符串）→ JSON 中省略该 key 或设为 `null`。
3. `text` 字段可生成患者摘要（如"患者肌酐2.4mg/dL，诊断肺不张"），供未来 LLM 算子使用。
4. `images` 保留 CXR 路径（即使文件不存在），供未来跨模态算子使用。

### 4.4 测试计划

| 阶段 | 数据量 | 目的 | 验证方法 |
|------|--------|------|----------|
| **阶段1** | 5条（手工选取） | 验证算子基本功能 | 选取已知冲突样本（如 subject_id=12468016 肌酐2.4+No Finding）+已知正常样本，确认冲突检出/无误报 |
| **阶段2** | 100条 | 验证边界情况 | 随机抽50条 + 5类冲突各取10条，确认召回率与已有1444冲突结果一致 |
| **阶段3** | 10000条全量 | 产出完整报告 | 与 `medical_conflict_results.json` 对比，确认检出数≥1444且分类一致 |

**阶段1测试数据选取**（基于已有冲突结果）：
- 冲突样本：12468016（肌酐2.4+No Finding）、19931382（乳酸7.2+No Finding、pH7.17）、16574411（血糖332+No Finding）、17782126（钾6.9+No Finding）
- 正常样本：从 No Finding 中选血检全正常者；从有诊断中选血检匹配者

### 4.5 预期输出

| 输出文件 | 格式 | 内容 |
|----------|------|------|
| `output_dj/lab_range_stats.json` | JSON | L1指标越界统计：各指标异常样本数/分布 |
| `output_dj/lab_diag_conflict_stats.json` | JSON | L2冲突报告：冲突类型/数量/严重度/样本明细 |
| `output_dj/cross_lab_stats.json` | JSON | L3多指标冲突报告 |
| `output_dj/diag_consistency_stats.json` | JSON | 诊断标签一致性报告 |
| `output_dj/global_report.json` | JSON | 全局汇总：总冲突数/冲突率/分类统计 |
| `output_dj/conflict_report.html` | HTML | 可视化报告：冲突类型饼图/严重度分布/Top异常指标表格 |
| `output_dj/filtered_dataset.jsonl` | JSONL | 处理后数据集（含全部stats字段） |

**预期冲突检出**（与已有结果对齐）：
- 乳酸酸中毒漏诊: ~1160
- 肾功能异常漏诊: ~132
- 高血糖漏诊: ~68
- 高钾血症漏诊: ~50
- 严重酸中毒漏诊: ~34
- 总计: ~1444（14.44%）

### 4.6 与已有 `medical_conflict_results.json` 的关系

已有结果是**单脚本一次性检测**的产物，仅覆盖 L2（血检 vs 标签）中5个关键指标。本次规划将其**系统化为 Data-Juicer 算子管道**，扩展为：
- L1 单指标范围检测（覆盖全部50项，不仅5项）
- L2 血检-诊断冲突（复现已有1444结果 + 可扩展更多指标）
- L3 多指标协同一致性（新增，检测复合异常）
- 诊断标签一致性（新增）
- 可复用、可配置、可并行（Data-Juicer 的 `np` 多进程 + Ray 支持）
- 统计报告可导出、可追溯（`stats_export_path` + tracer）

---

## 附录：关键文件索引

| 文件 | 说明 |
|------|------|
| `data-juicer/data_juicer/ops/base_op.py` | 算子基类（Filter/Mapper/Deduplicator等） |
| `data-juicer/data_juicer/utils/constant.py` | Fields/StatsKeys/MetaKeys 常量定义 |
| `data-juicer/data_juicer/ops/filter/llm_condition_filter.py` | 支持知识库grounding的LLM条件过滤算子 |
| `data-juicer/data_juicer/ops/filter/specified_numeric_field_filter.py` | 可复用的数值字段范围过滤 |
| `data_clean/timeseries_operators.py` | 焊接场景自定义算子（参考模板） |
| `data_clean/welding_conflict_filter.py` | 规则引擎式冲突检测（参考模板） |
| `data_clean/config_timeseries.yaml` | YAML配置示例 |
| `data_clean/medical_data/medtvt/train.csv` | 10000条医疗多模态数据 |
| `data_clean/medical_data/medtvt/labs_means.json` | 50项血检百分位统计 |
| `data_clean/medical_data/medtvt/results/medical_conflict_results.json` | 已有冲突检测结果（1444条） |
