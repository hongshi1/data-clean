# 变更记录

## [v0.3.0] — 2026-08-01: 项目清理与DataFlow集成

### 清理
- 删除Data-Juicer框架全部文件（upstream代码、docs、config、tests、demos等）
- 删除非SRS数据（医疗/焊接/材料等实验数据）
- 删除非SRS知识库（chexpert/loinc/medical_kb）
- 删除过时docs（research/op_doc_enhance_workflow/tutorial）
- 删除非SRS tools（analyze_data/check_ray_cluster/dj_install等12个）
- 删除archive/、.sisyphus/、.codeflicker、.omo等历史遗留
- 删除dataflow_repos/（可按需重新克隆）

### 新增
- `PROJECT_GUIDE.md` — 项目唯一入口文档
- `CHANGELOG.md` — 版本变更记录（本文件）
- `tools/srs_dataflow_integration.py` — DataFlow生态集成脚本
- `tools/srs_dataflow_pipeline.py` — DataFlow冲突检测Pipeline（优化版）
- `docs/dataflow_ecosystem/` — DataFlow生态代码级调研（13个文件，8000+行）
  - 05a-05e: 5个组件深度分析
  - 08a-08e: 5份代码级复现指南
  - 07: 多模态冲突检验+上下文关联映射方案
- `data/gjb_438c/real_gjb_srs/` — 16份真实GJB SRS文档(.doc)

### 变更
- 整理项目结构，SRS项目文件与Data-Juicer框架完全分离
- 新增DataFlow生态安装（~/dataflow-env）
- 修复MinerU解析器（para_blocks → lines[].spans[].content）
- 修复LLM响应解析（<think>/<answer>标签处理）

### 环境
- DataFlow env: `~/dataflow-env/` (Python 3.12 + open-dataflow 1.0.10 + dataflow-kg 1.0.1)
- DataMind 0.3.0, MemOS 2.0.25 已安装

---

## [v0.2.0] — 2026-07-29: DataFlow生态调研

### 新增
- DataFlow生态全景调研（5 Agent并行，产出6个知识笔记+综合报告）
- 深度补采5个组件代码级分析（Paper2Any/MemOS/OpenWorldLib+DataMind/Angel+WebUI/LoopAI）
- 多模态冲突检验与上下文关联能力映射分析
- 5份代码级复现指南（AgentFlow/pdf2vqa+VLM/KG+DataMind/Core Pipeline/MemOS）

### 安装
- 克隆DataFlow/AgentFlow/DataFlow-Skills源码
- 安装open-dataflow + dataflow-kg + DataMind + MemOS到~/dataflow-env

---

## [v0.1.0] — 2026-07-24: SRS一致性检测基础

### 核心功能
- MinerU环境搭建（Python 3.12 venv, CPU模式）
- GJB 438C-2021标准OCR（81页）+ 规则提取（4类）+ 完整规则库
- SRS数据集构建：359份文档（65 GJB + 294通用），来自9+来源
- 三层一致性检测引擎v2：同值/文本-表格/逻辑，Z3实际求解已集成
- Gold Standard构建：3份（battery_srs / compiler_srs / scheduler_srs）
- 评测框架：srs_eval.py 对齐Gold Standard，按层计算P/R/F1
- 图片-文本匹配v3：Markdown引用提取 + VLM描述兜底
- 统一文档处理 + 基于内容指纹的文档去重
- 文献调研（5方向128篇）+ Top5精读 + merged方案文档

### 工具脚本（37个）
- srs_mineru_parse.py / srs_structurer.py / srs_table_parser.py
- srs_constraint_extract.py / srs_consistency_checker_v2.py / srs_eval.py
- srs_image_text_matcher.py / srs_kb_graph_builder.py / srs_unified_processor.py
- srs_gjb_rule_extract.py / srs_gjb_compliance_scan.py
- srs_dataset_catalog.py / srs_dataset_stats.py / srs_dedup_documents.py
- srs_synthetic_conflict_gen.py / srs_pair_discovery.py
- ...等37个工具脚本
