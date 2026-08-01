# SRS 需求文档不一致检测系统

> **一句话**: 从62个SRS PDF文档中检测语法/语义/逻辑/图片四层不一致性
> **数据集**: PURE (https://zenodo.org/records/1414117)
> **代码**: `tools/srs_*.py` (17个文件, 10,818行)
> **复现论文**: 11篇

---

## 快速导航

| 你想了解... | 看这个文件 |
|---|---|
| 项目整体做了什么 | [01_PROJECT_OVERVIEW.md](docs/srs_project/01_PROJECT_OVERVIEW.md) |
| 数据集怎么构建的 | [02_DATASET.md](docs/srs_project/02_DATASET.md) |
| 每层检测做了什么 | [03_DETECTION_DETAILS.md](docs/srs_project/03_DETECTION_DETAILS.md) |
| 复现了哪些论文 | [04_PAPER_REPRODUCTION.md](docs/srs_project/04_PAPER_REPRODUCTION.md) |
| 评测结果 | [05_EVALUATION.md](docs/srs_project/05_EVALUATION.md) |
| 怎么运行代码 | [06_OPERATION_MANUAL.md](docs/srs_project/06_OPERATION_MANUAL.md) |
| 交接给别人 | [07_HANDOFF.md](docs/srs_project/07_HANDOFF.md) |

---

## 核心结果

### 检测到的不一致

| 层 | 类型 | 数量 | 可信度 | 方法 |
|---|---|:---:|:---:|---|
| 语法 | 章节缺失 | 36 | ✅ | ReXCL规则 |
| 语法 | 引用断裂 | 177 | ✅ | 正则+索引 |
| 语法 | 单位不统一 | 3 | ✅ | 知识库换算表 |
| 语法 | 命名漂移 | 2 | ✅ | NER+同义词典 |
| 语法 | 图片引用断裂 | 16 | ✅ | 正则+VLM |
| 语义 | **availability矛盾** | **1** | ✅ | **NLI(GLM-5)** |
| 语义 | 需求重复 | 22 | ⚠️ | embedding相似度 |
| 图片 | 图文矛盾 | 18 | ⚠️ | VLM(Kimi-K2.6) |
| 图片 | 流程图问题 | 37 | ⚠️ | FloCA+NetworkX |
| 逻辑 | Z3约束 | 0 | ✅ | 全假阳性(已审计) |

### 唯一真矛盾

```
文件: 0000 - gamma j.pdf (GAMMA-J Web Store)
位置1: 第1.4节 — "Have an availability of 99.999%"
位置2: 第5.4节 — "The system shall have an availability of 99.99%"
检测: NLI判断contradiction(置信度0.95) + Z3判断UNSAT
确认: 同一系统的两种可用性要求 → 真实矛盾
```

### 核心瓶颈

参数抽取精度不足(F1=0.54)导致Z3约束求解的8个UNSAT全是假阳性(把章节号/标准号误提取为参数值)。

---

## 项目结构

```
data_clean/
├── tools/                           # 代码(17个文件)
│   ├── srs_consistency_check.py     # 正则版校验v2
│   ├── srs_keie_pipeline.py         # 知识增强IE流水线v4
│   ├── srs_unified_pipeline.py      # 统一流水线v5
│   ├── srs_llm_extract.py           # LLM直接抽取
│   ├── srs_image_text_check.py      # 图片-文本检测(6篇论文)
│   ├── srs_bert_crf.py              # BERT-CRF训练
│   ├── srs_rexcl.py                 # ReXCL复现
│   ├── srs_rexcl_mlm.py             # MLM领域适配
│   ├── srs_ner_v2.py                # NER v2
│   ├── srs_mapping.py               # 映射系统
│   ├── srs_gold_annotator.py        # Gold standard标注
│   ├── srs_consistency_integrated.py # L1+L2+L3校验
│   └── ... (共17个)
├── knowledge/
│   └── srs_kb.json                  # 知识库(23参数/374实体)
├── data/srs_requirements/
│   ├── req/                         # 62个原始PDF
│   ├── parsed/                      # 62个解析JSON
│   ├── bert_crf/                    # 训练数据(银标准+金标准)
│   ├── keie_output/                 # 检测结果
│   ├── images_hd/                   # 页面截图+图片检测结果
│   └── visualization/               # 可视化图表
├── docs/srs_project/                # 项目文档(7个文件)
└── ie_taxonomy/                     # 方法谱系调研
```

---

## 关键限制

1. **知识库手工构建**: 23个参数+同义词是人工写的, 无自动化构建流水线
2. **银标准噪声严重**: ~70%精度, 导致BERT-CRF F1=0.05
3. **金标准量少**: 仅100句, 无法训练强模型
4. **Z3全假阳性**: 参数抽取把章节号/标准号误提取为参数值
5. **图片检测覆盖低**: 5/248页(2%)
6. **无人工标注**: 银标准(规则)和金标准(LLM)都不是人工标注的ground truth
7. **初步结果**: 所有结果仅在PURE单一数据集上验证, 需补充QuRE/PURE-MMQA/ReqEval
