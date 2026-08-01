# SRS一致性检测项目 — 项目指南

> 本文件是项目的唯一入口文档，涵盖项目概述、结构、运行方式、数据说明和版本管理。

## 1. 项目概述

对GJB 438C格式的SRS（软件需求规格说明）文档进行**三层一致性检测**（语法/语义/逻辑），并引入DataFlow生态技术增强**多模态冲突检验**和**上下文关联**能力。

**核心能力**：
- 文档解析：MinerU解析PDF→结构化JSON（文本/表格/图片/公式）
- 约束提取：LLM从需求文本中提取6类约束（numerical/tolerance/temporal/conditional/default/design）
- 冲突检测：文本↔表格冲突、约束间冲突、跨章节冲突
- 知识图谱：三元组提取→图谱构建→多跳关联推理
- 上下文关联：识别"应该一致"的数据组（需求→约束→表格→图片→公式）
- 评测：对齐Gold Standard，按层计算P/R/F1

## 2. 项目结构

```
data_clean/
├── tools/                              # 代码（37个Python脚本）
│   ├── srs_mineru_parse.py             # MinerU解析(单文档)
│   ├── srs_structurer.py               # MinerU输出→结构化JSON
│   ├── srs_table_parser.py             # HTML表格→结构化数据
│   ├── srs_constraint_extract.py       # LLM提取约束
│   ├── srs_consistency_checker_v2.py   # 三层一致性检测(含Z3)
│   ├── srs_eval.py                     # 评测框架(P/R/F1)
│   ├── srs_image_text_matcher.py       # 图片-文本匹配
│   ├── srs_kb_graph_builder.py         # 知识图谱构建
│   ├── srs_unified_processor.py        # 统一文档处理
│   ├── srs_dataflow_integration.py     # DataFlow生态集成
│   ├── srs_dataflow_pipeline.py        # DataFlow冲突检测Pipeline
│   └── ...                             # 其余26个工具脚本
│
├── data/
│   ├── gjb_438c/                       # GJB数据(主工作目录)
│   │   ├── real_gjb_srs/               # ★ 16份真实GJB SRS(.doc)  ← 新数据
│   │   ├── source_pdfs/                # GJB标准原始PDF
│   │   ├── ocr/                        # GJB 438C-2021 OCR结果(81页)
│   │   ├── mineru_srs/                 # 3份SRS的MinerU解析结果
│   │   ├── extracted_constraints/      # LLM提取的约束
│   │   ├── extracted_tables/           # 表格结构化数据
│   │   ├── consistency_reports/        # 一致性检测报告(v1+v2)
│   │   ├── gold_standard/              # Gold Standard(3份)
│   │   ├── dataflow_output/            # DataFlow Pipeline输出
│   │   ├── srs_collection/             # 多源SRS集合(378 PDF, 1.6GB)
│   │   ├── unified_dataset/            # 统一数据集(359份)
│   │   └── ...
│   ├── srs_requirements/               # PURE数据集(开发用)
│   └── 438B-2009全套模板/              # GJB 438B模板
│
├── knowledge/                          # 知识库(9个JSON)
│   ├── gjb_438c_rules.json             # GJB规则库(4类规则)
│   ├── gjb_438c_rules_full.json        # GJB完整规则库
│   ├── srs_kb_graph_v2.json            # 知识图谱v2(7720节点)
│   └── ...
│
├── docs/                               # 文档
│   ├── srs_project/                    # SRS项目文档(架构/数据集/检测/评测)
│   ├── dataflow_ecosystem/             # DataFlow生态调研(代码级)
│   ├── feishu/                         # 场景调研报告
│   └── survey/                         # 技术方案报告
│
├── AGENTS.md                           # 项目导航(给AI agent用)
├── PROJECT_GUIDE.md                    # ← 本文件
├── CHANGELOG.md                        # 版本变更记录
└── .gitignore
```

## 3. 环境配置

### 3.1 Python环境

| 环境 | 路径 | 用途 |
|------|------|------|
| MinerU env | `~/mineru-env/` (Python 3.12) | MinerU PDF解析 |
| DataFlow env | `~/dataflow-env/` (Python 3.12) | DataFlow生态(open-dataflow + dataflow-kg + DataMind + MemOS) |

### 3.2 API配置

```bash
# GLM-5 API (内网，需VPN)
export DF_API_KEY="n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
# API URL: https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions
# Model: ep-glsztk-1778496696841467392

# Kimi-K2.6 API (多模态，文本+图片)
# 配置见 tools/srs_image_text_matcher.py
```

### 3.3 DataFlow生态安装

```bash
# 创建venv
~/mineru-env/bin/python -m venv ~/dataflow-env
# 安装DataFlow Core + KG (合并安装，含200+算子)
uv pip install --python ~/dataflow-env/bin/python open-dataflow dataflow-kg
# 安装DataMind
uv pip install --python ~/dataflow-env/bin/python -e dataflow_repos/DataMind
# 安装MemOS
uv pip install --python ~/dataflow-env/bin/python MemoryOS
# 修复缺失的__init__.py + 安装json_repair
uv pip install --python ~/dataflow-env/bin/python json_repair
```

## 4. 运行方式

### 4.1 MinerU解析

```bash
# 单文档
~/mineru-env/bin/python tools/srs_mineru_parse.py

# 批量解析
MINERU_MODEL_SOURCE=huggingface ~/mineru-env/bin/python tools/srs_collection_mineru_parse.py
```

### 4.2 SRS处理流程

```bash
# 统一文档处理(章节/约束/表格/图片整合)
python3 tools/srs_unified_processor.py

# 三层一致性检测(含Z3求解)
python3 tools/srs_consistency_checker_v2.py

# 评测(对齐Gold Standard)
python3 tools/srs_eval.py
```

### 4.3 DataFlow Pipeline（多模态冲突检验+上下文关联）

```bash
# 需要先启动VPN（GLM-5 API为内网）
export DF_API_KEY="n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
~/dataflow-env/bin/python tools/srs_dataflow_pipeline.py
```

Pipeline执行4步：
1. **约束提取** — GLM-5从SRS需求章节提取6类约束
2. **冲突检测** — 文本↔表格冲突(API) + 约束间冲突(本地)
3. **三元组提取** — GLM-5构建知识图谱三元组
4. **上下文关联** — NetworkX图谱多跳关联分析

### 4.4 DataFlow import方式

DataFlow使用LazyLoader，**必须从父模块导入类名**（不能按文件路径导入）：

```python
# ✅ 正确
from dataflow.operators.core_text import PromptedGenerator
from dataflow.operators.general_kg import KGTripleExtraction
from dataflow.serving import APILLMServing_request

# ❌ 错误（会报ModuleNotFoundError）
from dataflow.operators.core_text.generate.prompted_generator import PromptedGenerator
```

## 5. 数据说明

### 5.1 真实GJB数据（新）

`data/gjb_438c/real_gjb_srs/` 包含16份真实GJB格式SRS文档(.doc)，覆盖：
- 数据获取转换、界面集成框架、服务集成框架
- 数据统一访问、软件部署管理、运行支撑服务
- 报文处理、数据运行维护、数据同步共享
- 动态名录、语音综合处理、文电处理
- 统一传输、传输服务、实时信息传输、流媒体传输

### 5.2 已有数据集

| 数据集 | 数量 | 说明 |
|--------|------|------|
| srs_collection | 378 PDF | 多源SRS集合(9+来源) |
| unified_dataset | 359份 | 65 GJB + 294通用 |
| gold_standard | 3份 | battery/compiler/scheduler |
| mineru_srs | 3份 | 已MinerU解析 |
| knowledge graph | 7720节点 | srs_kb_graph_v2.json |

### 5.3 待处理

- 16份真实GJB SRS(.doc) → 需转为PDF → MinerU解析 → DataFlow Pipeline
- Gold Standard仅3份 → 需扩展
- 仅3份文档MinerU解析 → 需批量解析

## 6. 版本管理

- **分支策略**：`main`(稳定) / `gxc_dev`(开发) / `cleanup-restructure`(当前清理分支)
- **版本记录**：见 [CHANGELOG.md](CHANGELOG.md)
- **未提交文件**：SRS项目文件此前未纳入git，本次清理后统一提交

## 7. 关键技术文档索引

| 主题 | 文档位置 |
|------|---------|
| SRS项目概览 | `docs/srs_project/01_PROJECT_OVERVIEW.md` |
| 数据集说明 | `docs/srs_project/02_DATASET.md` |
| 检测细节 | `docs/srs_project/03_DETECTION_DETAILS.md` |
| 评测说明 | `docs/srs_project/05_EVALUATION.md` |
| 架构设计 | `docs/srs_project/ARCHITECTURE_DESIGN.md` |
| DataFlow生态全景 | `docs/dataflow_ecosystem/00_overview_report.md` |
| DataFlow Core代码级 | `docs/dataflow_ecosystem/01_dataflow_core.md` |
| 多模态冲突检验方案 | `docs/dataflow_ecosystem/07_multimodal_conflict_context.md` |
| AgentFlow复现代码 | `docs/dataflow_ecosystem/08a_agentflow_code.md` |
| VLM冲突检测代码 | `docs/dataflow_ecosystem/08b_pdf2vqa_vlm_code.md` |
| KG+DataMind代码 | `docs/dataflow_ecosystem/08c_kg_datamind_code.md` |
| DataFlow Pipeline代码 | `docs/dataflow_ecosystem/08d_core_pipeline_code.md` |
| MemOS记忆系统代码 | `docs/dataflow_ecosystem/08e_memos_code.md` |
| 场景技术方案 | `docs/survey/`, `docs/feishu/research/` |
