# AGENTS.md — SRS一致性检测项目导航

## 项目目标

对GJB 438C格式的SRS文档进行三层一致性检测（语法/语义/逻辑），构建数据集与评测体系，产出论文初稿。

## 项目结构

```
data_clean/
├── tools/                              # 代码
│   ├── srs_mineru_parse.py             # MinerU解析(单文档)
│   ├── srs_collection_mineru_parse.py  # MinerU批量解析SRS数据集
│   ├── srs_structurer.py               # MinerU输出→结构化JSON
│   ├── srs_table_parser.py             # HTML表格→结构化数据
│   ├── srs_collection_table_extract.py # 批量表格提取
│   ├── srs_constraint_extract.py       # LLM提取7种约束
│   ├── srs_constraint_extract_more.py  # 扩展约束提取
│   ├── srs_constraint_extract_collection.py # 批量约束提取
│   ├── srs_gjb_rule_extract.py         # 从GJB 438C OCR结果提取规则
│   ├── srs_gjb_compliance_scan.py      # GJB规则合规扫描
│   ├── srs_kb_graph_builder.py         # 构建知识图谱
│   ├── srs_consistency_checker_v2.py   # 三层一致性检测v2(含Z3实际求解)
│   ├── srs_eval.py                     # 评测框架(P/R/F1, 对齐Gold Standard)
│   ├── srs_image_text_matcher.py       # 图片-文本匹配v3(VLM辅助)
│   ├── srs_unified_processor.py        # 统一文档处理(章节/约束/表格/图片整合)
│   ├── srs_unified_dataset_builder.py  # 统一数据集构建
│   ├── srs_dedup_documents.py          # 基于内容指纹的文档去重
│   ├── srs_dataset_catalog.py          # 数据集编目
│   ├── srs_dataset_stats.py            # 数据集统计
│   ├── srs_metadata_collector.py       # 元数据采集
│   ├── srs_public_metadata_collect.py  # 公开元数据采集
│   ├── srs_ieee830_analyze.py          # IEEE 830分析
│   ├── cmapss_multiroute_detection.py  # C-MAPSS多路由检测(上游用)
│   ├── real_multiroute_detection.py    # H4R焊接多路由检测(上游用)
│   └── archive/                        # 归档脚本(19个: 17 PURE + v1 checker + compliance_check)
│
├── data/gjb_438c/                      # GJB数据(当前工作, 16个子目录)
│   ├── source_pdfs/                    # GJB标准原始PDF
│   ├── ocr/                            # GJB 438C-2021 MinerU OCR结果(81页)
│   ├── ocr_7p/                         # GJB 1330A MinerU OCR结果
│   ├── demo/                           # 5份公开GJB格式SRS PDF
│   ├── 438B-2009全套模板/              # 33个GJB 438B DOCX模板
│   ├── 438C-2021全套模板/              # 20个GJB 438C DOCX模板
│   ├── mineru_srs/                     # 3份SRS的MinerU解析结果
│   ├── extracted_constraints/          # LLM提取的约束
│   ├── extracted_tables/               # 表格结构化数据
│   ├── consistency_reports/            # 一致性检测报告(v1+v2)
│   ├── gold_standard/                  # Gold Standard(battery/compiler/scheduler)
│   ├── image_text_matches/             # 图片-文本匹配结果
│   ├── processed_documents/            # 统一处理后的文档
│   ├── srs_collection/                 # 多源SRS集合(9+来源)
│   ├── unified_dataset/                # 统一数据集(359份: 65 GJB + 294通用)
│   └── dataset/                        # 数据集catalog/metadata/rules
│
├── data/srs_requirements/              # PURE数据集(旧,开发用)
│   ├── req/                            # 62个原始PURE PDF
│   ├── mineru_parsed/                  # MinerU解析
│   ├── structured/                     # 结构化JSON
│   └── (旧目录: parsed/ ner_output/ bert_crf/ 等)
│
├── knowledge/                          # 知识库
│   ├── gjb_438c_rules.json             # GJB规则库(4类规则)
│   ├── gjb_438c_rules_full.json        # GJB完整规则库
│   ├── gjb_rules_gap_analysis.json     # 规则差距分析
│   ├── gjb_rules_part1_chapters.json   # 规则-第1部分(正文章节)
│   ├── gjb_rules_part2_appendix_j.json # 规则-第2部分(附录J)
│   ├── gjb_rules_part3_other_appendices.json # 规则-第3部分(其他附录)
│   ├── srs_kb_graph_v2.json            # 知识图谱v2(7720节点)
│   └── srs_kb.json                     # 旧知识库(23参数)
│
├── docs/srs_project/                   # 项目文档
│   ├── README.md                       # 项目入口
│   ├── 01_PROJECT_OVERVIEW.md          # 项目概览
│   ├── 02_DATASET.md                   # 数据集说明
│   ├── 03_DETECTION_DETAILS.md         # 检测细节
│   ├── 04_PAPER_REPRODUCTION.md        # 论文复现
│   ├── 05_EVALUATION.md                # 评测说明
│   ├── 06_OPERATION_MANUAL.md          # 操作手册
│   ├── 07_HANDOFF.md                   # 交接文档
│   ├── ARCHITECTURE_DESIGN.md          # 架构设计
│   ├── DESIGN_V2.md                    # 方案设计v2(多角度)
│   ├── SRS_DATASET_SURVEY.md           # 数据集调研
│   ├── DATA_AGENT_ANALYSIS.md          # 数据分析
│   ├── literature_survey/              # 文献调研(128篇+专题报告)
│   │   ├── SURVEY_SUMMARY.md           # 调研汇总
│   │   ├── TOP5_DEEP_READ.md           # Top5论文精读
│   │   └── (16个专题调研报告)
│   ├── merged/                         # 融合方案文档(G1/G2/G9/G10)
│   └── reading_reports/                # 读书报告
│
└── (Data-Juicer框架代码 — 上游,不修改)
```

## 当前状态

### 已完成
- MinerU环境搭建(Python 3.12 venv, CPU模式)
- GJB 438C-2021标准OCR(81页) + 规则提取(4类) + 完整规则库 + 差距分析
- SRS数据集构建: 359份文档(65 GJB格式 + 294通用), 来自buaa/gjb438b/ieee830/nasa/radar等9+来源
- 三层一致性检测引擎v2: 同值/文本-表格/逻辑, **Z3实际求解已集成**
- Gold Standard构建: 3份(battery_srs / compiler_srs / scheduler_srs)
- 评测框架就绪: `srs_eval.py` 对齐Gold Standard, 按层计算P/R/F1
- 图片-文本匹配v3: Markdown引用提取 + VLM描述兜底
- 统一文档处理 + 基于内容指纹的文档去重
- 文献调研(5方向128篇) + Top5精读 + merged方案文档(G1/G2/G9/G10)

### 进行中
- 一致性检测假阳性优化
- 扩展Gold Standard到更多文档

### 环境
- MinerU venv: `~/mineru-env/bin/python`
- GLM-5 API: `https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions`
- Kimi-K2.6 API: 多模态(文本+图片)

## 常用命令

```bash
# MinerU解析(单文档)
MINERU_MODEL_SOURCE=huggingface ~/mineru-env/bin/python tools/srs_mineru_parse.py

# MinerU批量解析(数据集)
MINERU_MODEL_SOURCE=huggingface ~/mineru-env/bin/python tools/srs_collection_mineru_parse.py

# 统一文档处理(章节/约束/表格/图片整合)
python3 tools/srs_unified_processor.py

# 图片-文本匹配
python3 tools/srs_image_text_matcher.py

# 文档去重
python3 tools/srs_dedup_documents.py

# 约束提取
python3 tools/srs_constraint_extract.py

# 表格解析
python3 tools/srs_table_parser.py

# 一致性检测(v2, 含Z3实际求解)
python3 tools/srs_consistency_checker_v2.py

# 评测(对齐Gold Standard, 输出P/R/F1)
python3 tools/srs_eval.py

# GJB规则提取
~/mineru-env/bin/python tools/srs_gjb_rule_extract.py

# 知识图谱构建
~/mineru-env/bin/python tools/srs_kb_graph_builder.py
```
