# AGENTS.md — SRS一致性校验与上下文关联研究项目

## 项目定位

基于16份真实GJB格式SRS文档，研究**一致性校验**与**上下文关联**两个正交技术方向。

这不是工程项目，是科研项目。目标是产出有技术创新的方法和可评测的结果，面向RE/ICSE/FSE级别论文。

## 两个核心方向

### 方向A：上下文关联（不一致性校验的前置准备）

**问题**：SRS文档中，同一个需求/实体可能分布在多个位置——3.2.1节的文字描述、接口图、合格性表中的行、追溯表中的映射。如何把这些分散的、多模态的内容**聚合成一个条目**，使得一致性校验有明确的检测对象？

**本质**：多模态上下文聚合 / 跨章节实体链接

**输入**：一份SRS文档（markdown + 图片 + 表格）
**输出**：条目列表，每个条目 = {文字片段, 关联图片, 关联表格行, 章节位置, 语义角色}

**关键挑战**：
- 如何判断两段文字描述的是"同一个事物"？
- 图片和文字如何关联（markdown引用？位置邻接？语义相似？）
- 表格中的哪一行对应哪个需求？
- "同一个事物"的粒度是什么（一个参数？一个功能？一个接口？）

### 方向B：不一致性校验（对聚合条目执行检测）

**问题**：给定一个聚合条目（或一对条目），如何检测其中存在的不一致性？

**三个层面**：
- **语法层**：格式、编号、结构是否合规（如章节缺失、编号不连续、需求ID重复）
- **语义层**：同一参数/概念在不同位置的值/含义是否一致（如同参数不同值、正文与表格矛盾）
- **逻辑层**：约束之间是否逻辑可满足（如子模块时间之和≤总预算、允许vs禁止矛盾）

**当前状态**：具体的不一致性类型**尚未定义**——需要先调研16份数据集中实际存在哪些不一致性，再定义检测方法。

**关键挑战**：
- 如何区分"合理差异"（如不同设备形态的配置差异）和"真实矛盾"？
- 逻辑层矛盾如何形式化（Z3？NLI？混合？）
- 没有Gold Standard如何评测？

### 两个方向的关系

```
方向A(上下文关联) → 产出条目对 → 方向B(不一致性校验) → 产出检测结果
```

是流水线关系，但**各自有独立的技术贡献**：
- 方向A的贡献 = 准确的条目聚合方法（如何判断"同一个事物"）
- 方向B的贡献 = 准确的不一致性检测方法（如何判断"不一致"）

## 数据集

### 主数据集：16份真实GJB格式SRS

```
data/软件需归样例数据集/
├── 01数据获取转换分系统需求规格说明-终稿.doc
├── 02界面集成框架软件需求规格说明-终稿.doc
├── ...
└── 16流媒体传输服务软件需求规格说明-终稿.doc
```

- 16份真实军事信息系统SRS，GJB 438C格式
- 涵盖数据获取、传输、处理、部署等多个子系统
- 已用textutil解析为markdown：`data/gjb_438c/parsed_srs_dataset/`
- 13份结构完整（6章+3.1~3.18），3份格式异常

### 辅助数据

| 数据 | 路径 | 说明 |
|------|------|------|
| GJB 438C标准OCR | `data/gjb_438c/ocr/` | 81页标准原文MinerU解析 |
| GJB规则库 | `knowledge/gjb_438c_rules_full.json` | 120条规则(可追溯到OCR行号) |
| GJB词典 | `knowledge/srs_kb.json` | 23参数+13接口+10单位族 |
| Gold Standard(旧) | `data/gjb_438c/gold_standard/` | 3份合成SRS的22条标注(8真矛盾+14正值) |
| MinerU解析(旧) | `data/gjb_438c/mineru_srs/` | 3份合成SRS的MinerU解析 |

### 数据预处理脚本

| 脚本 | 说明 |
|------|------|
| `tools/srs_doc_batch_parse.py` | .doc→markdown批量解析(目录映射恢复编号) |

## 待完成的调研工作

### 调研1：SRS中实际存在哪些不一致性？

**目的**：定义方向B的具体检测对象

**方法**：人工阅读2-3份SRS文档，记录所有发现的不一致性
- 01数据获取转换分系统（最大文档，接口最多）
- 03服务集成框架（需求项最多）
- 06运行支撑服务（约束最多）

**产出**：不一致性类型清单 + 每种类型的示例

### 调研2：SRS中"同一事物"的分布模式

**目的**：定义方向A的聚合粒度和关联方法

**方法**：分析同一参数/功能/接口在文档中的出现位置
- 同一参数在哪些章节出现？
- 图片在哪些章节被引用？
- 表格中的行对应哪些章节的需求？

**产出**：条目聚合规则 + 聚合粒度定义

### 调研3：现有方法调研

**目的**：明确技术创新点

**方法**：调研NLP4RE领域的一致性检测和上下文关联方法
- ARTA数据集的requirement smells检测方法
- Bendík 2017的依赖图+SAT方法
- LLM-based requirement relation extraction
- 多模态文档理解(图文关联)

**产出**：技术路线对比 + 创新点定位

## 项目结构

```
data_clean/
├── data/
│   ├── 软件需归样例数据集/              # ★主数据集(16份真实GJB SRS .doc)
│   └── gjb_438c/
│       ├── parsed_srs_dataset/          # ★解析后markdown(16份)
│       ├── ocr/                         # GJB 438C标准OCR
│       ├── mineru_srs/                  # 3份旧Gold Standard的MinerU解析
│       ├── gold_standard/               # 旧Gold Standard(3份合成SRS)
│       └── (旧数据目录: extracted_constraints/ extracted_tables/ 等)
│
├── knowledge/                           # 基础知识库
│   ├── gjb_438c_rules.json             # GJB规则库(v1.0, 46条)
│   ├── gjb_438c_rules_full.json        # GJB完整规则库(v2.0, 120条)
│   ├── gjb_rules_gap_analysis.json     # 规则差距分析
│   ├── gjb_rules_part1/2/3*.json       # 规则分部文件
│   ├── srs_kb_graph_v2.json            # 旧知识图谱(7720节点)
│   └── srs_kb.json                     # 旧词典(23参数)
│
├── tools/                               # 工具脚本
│   ├── srs_doc_batch_parse.py          # .doc批量解析(数据预处理)
│   ├── srs_mineru_parse.py             # MinerU解析(单文档)
│   ├── srs_structurer.py               # MinerU输出→结构化JSON
│   ├── srs_table_parser.py             # HTML表格→结构化数据
│   ├── srs_constraint_extract.py       # LLM提取约束
│   ├── srs_gjb_rule_extract.py         # GJB规则提取
│   ├── srs_gjb_compliance_scan.py      # GJB合规扫描
│   ├── srs_consistency_checker_v2.py   # 三层一致性检测v2(含Z3)
│   ├── srs_eval.py                     # 评测框架
│   ├── srs_image_text_matcher.py       # 图片-文本匹配
│   ├── srs_unified_processor.py        # 统一文档处理
│   └── archive/                        # 归档脚本
│
├── docs/srs_project/                    # 项目文档
│   ├── literature_survey/              # 文献调研
│   └── (旧文档: 01-07_*.md 等)
│
└── .sisyphus/                          # 审计报告(已清理)
```

## 环境

- Python: **系统 Python 3.12 (Anaconda, Windows) — 唯一可用解释器**; `.venv`/`.venv-srs` 为macOS残留(可删), `.venv-embed` 仅含numpy
- 依赖锁定: `pip install -r requirements.txt`
- Lint: `ruff check algorithms` 必须零报错(tools增量偿还, 只许减少不许新增)
- 测试: `python -m pytest`(tests/ + algorithms/; 论文数字快照在 tests/test_gold_assets.py)
- **密钥: 统一 `from ai_config import ...`(tools/ai_config.py 读 .env; .env已gitignore, 模板见.env.example); 代码中出现密钥字面量 = 违规**
- API端点/模型: 见 `tools/ai_config.py` 与 `.env.example`
- **本地深度模型**(torch 2.11+cu128 GPU版已装于系统Python): `models/nli/`(mDeBERTa多语言NLI + Erlangshen中文NLI) + `models/embedding/bge-large-zh-v1.5`(1024维, GPU校验: tools/test_bge_gpu.py); 本地embedding走 `algorithms/bge_local.py`(惰性加载+磁盘缓存), 通道入口 `algorithms/blackboard/embedding_channel.py`(live API→local BGE→cache四级降级, BGE阈值EMB_TH_LOCAL=0.78经tools/bge_threshold_sweep.py校准); 下载新模型参考 `tools/download_embedding_model.py`(含Windows系统代理继承)

## 代码质量硬规则

1. **密钥**: 只有 tools/ai_config.py 允许读 .env; 任何 .py 出现密钥字面量立即修复(旧密钥已泄漏进git历史, 需在API平台轮换)
2. **无类型抑制**(as any式), **无裸 `except:`**; 静默吞错是科研结果被污染的常见源头
3. **模块顶层零I/O**: import期不读文件/不发请求(m1的emb_cache加载是历史包袱, 新代码禁止)
4. **open()必须 `encoding="utf-8"`**(Windows默认GBK, macOS上跑通的代码在Windows会静默乱码/崩溃)
5. **新功能配测试**: 确定性内核进 tests/ 快照回归(论文数字: θ/F1/规模计数已锁定)
6. **数据资产受MANIFEST保护**(tests/test_manifest.py); 有意重生成后跑 `python tools/build_data_manifest.py` 并同步快照
7. **LLM/VLM调用走缓存接口**(algorithms/llm_client.py 的 cache=True / m1 emb_cache)——禁止裸调用(不可复现)
8. **实验产出走runs协议**(tools/run_utils.py: config+git_sha+result, 不覆盖写)

## 当前状态

> ⚠️ 本清单为项目早期快照(历史存档), **实际进度以 `docs/srs_project/project_guide.md`(黄金文档) 为准**——项目已推进至ACDD M25里程碑(锚点校准管线/多场景裁决/论文草稿), 上方"⬜未开始"多项实际已完成.

- ✅ 数据准备：16份真实SRS已解析为markdown
- ✅ 基础知识：GJB 120条规则 + 词典
- ⬜ 调研1：SRS中实际不一致性类型（未开始）
- ⬜ 调研2：SRS中"同一事物"分布模式（未开始）
- ⬜ 调研3：现有方法调研（部分完成，需更新）
- ⬜ 方向A方法设计（待调研后开始）
- ⬜ 方向B方法设计（待调研后开始）
- ⬜ Gold Standard构建（待方法设计后开始）
