# DataFlow 生态与 SRS 一致性检测项目结合分析

> 本文件综合 5 个调研 Agent 的产出，系统分析 DataFlow 生态各层组件对 GJB 438C SRS 一致性检测项目的具体应用价值，给出分阶段落地路线图。

## 1. 项目现状回顾

| 维度 | 现状 | 痛点 |
|------|------|------|
| 文档解析 | MinerU 已用于 SRS PDF 解析 | 仅用基础解析，未利用 bbox/公式LaTeX/表格HTML |
| 处理流程 | 20+ 个 `tools/srs_*.py` 独立脚本 | 缺乏统一抽象，无并发/断点续跑/key校验 |
| 约束提取 | `srs_constraint_extract.py` 串行调 GLM API | 无重试/限流/并发管理 |
| 一致性检测 | `srs_consistency_checker_v2.py` 含 Z3 求解 | 假阳性优化需手动迭代 |
| 知识图谱 | `srs_kb_graph_v2.json` 7720 节点 | 构建逻辑自研，缺乏补全/推理能力 |
| Gold Standard | 仅 3 份(battery/compiler/scheduler) | 测试覆盖严重不足 |
| 评测框架 | `srs_eval.py` 计算 P/R/F1 | 手动运行，缺乏自动化编排 |
| 论文产出 | 目标为论文初稿 | 架构图/图表/PPT 需手工制作 |

## 2. 生态组件-SRS项目映射矩阵

| DataFlow 组件 | 层级 | SRS 项目应用 | 优先级 | 落地难度 |
|--------------|------|-------------|--------|---------|
| **DataFlow Core** | L2 | 将 20+ 脚本算子化，获得 Pipeline/Storage/LLMServing 抽象 | P0 | 中 |
| **MinerU 深化** | L1 | bbox 图文匹配、公式LaTeX→Z3、表格HTML直用 | P0-P1 | 低-中 |
| **DataFlow-KG** | L2 | 用 domain_kg 重构知识图谱，graph_reasoning 扩展逻辑检测 | P1 | 中 |
| **AgentFlow** | L3 | 合成一致性检测测试用例，Gold Standard 3→100+ | P1 | 中 |
| **DataFlow-Skills** | L3 | 沉淀 SRS 算子为可组合技能，支持自动 Pipeline 生成 | P1 | 中 |
| **One-Eval** | L4 | NL2Eval 自动化评测，Bench Gallery 管理 Gold Standard | P2 | 低 |
| **LoopAI** | L4 | 假阳性优化闭环：评测→分析→获取→优化→改进 | P2 | 中 |
| **DataMind** | 横切 | 统一管理 knowledge/ 规则库与知识图谱，支持自然语言检索 | P2 | 中 |
| **Paper2Any** | L5 | 论文架构图/图表/PPT/海报自动生成 | P2 | 低 |
| **DataFlex** | L4 | 动态选择/配比 SRS 训练数据微调约束提取 LLM | P3 | 高 |
| **Angel** | 横切 | 大规模图计算(知识图谱社区发现)与分布式训练 | P3 | 高 |

## 3. 分阶段落地路线图

### Phase 0: 立即可做（1-2 周，零依赖）

#### 3.1 MinerU 深化使用
- **保留 bbox/page_idx**：在 `srs_structurer.py` 中保留 MinerU 输出的 `bbox` 和 `page_idx` 字段，用于 `srs_image_text_matcher.py` 的精确图文匹配和版面异常检测
- **直接使用表格 HTML**：MinerU 的 `content_list.json` 中表格项已含完整 HTML `table_body`，`srs_table_parser.py` 可直接解析，减少二次解析误差
- **公式 LaTeX 输出**：保留 MinerU 的公式 LaTeX 输出，为后续 Z3 约束检测提供公式级逻辑一致性检查能力

#### 3.2 Paper2Any 辅助论文写作
- 使用 Paper2Any 在线 Demo 生成 SRS 一致性检测系统的架构图
- 生成实验对比图表（P/R/F1 跨层评测结果）
- 制作论文答辩 PPT 和海报

### Phase 1: 短期改造（2-4 周，引入 DataFlow Core）

#### 3.3 SRS 处理流程算子化

将现有 `tools/srs_*.py` 脚本改造为 DataFlow OperatorABC 子类：

```
# 目标 Pipeline 结构
SRSMinerUParser → SRSStructurer → SRSConstraintExtractor → SRSTableParser
                                                        ↓
                                            SRSConsistencyEvaluator (三层检测 + Z3)
                                                        ↓
                                            SRSGoldStandardEvaluator (P/R/F1)
```

| SRS 脚本 | 算子类型 | input_key → output_key | 收益 |
|---------|---------|----------------------|------|
| `srs_mineru_parse.py` | 生成算子 | `pdf_path → mineru_output` | 标准化解析接口 |
| `srs_structurer.py` | 生成算子 | `mineru_output → structured_json` | 结构化统一管理 |
| `srs_constraint_extract.py` | 生成算子 | `section_text → constraints` | **并发推理 + 重试 + 限流** |
| `srs_table_parser.py` | 生成算子 | `html_table → table_data` | 表格解析标准化 |
| `srs_consistency_checker_v2.py` | 评测算子 | `constraints → violations` | key 链编译期校验 |
| `srs_eval.py` | 评测算子 | `violations → prf1_report` | 可复现评测 |
| `srs_gjb_compliance_scan.py` | 过滤算子 | `structured_json → compliance_flags` | 规则合规标准化 |
| `srs_dedup_documents.py` | 过滤算子 | `documents → deduped_docs` | 去重算子化 |

**核心收益**：
1. `LazyFileStorage` 替代手工 `processed_documents/` 缓存 → **断点续跑**
2. `APILLMServing_request` 替代串行 API 调用 → **并发推理**（`ThreadPoolExecutor` + 指数退避重试）
3. Pipeline 编译期 key 校验 → **避免运行期字段不匹配**
4. `@prompt_restrict` 约束算子-prompt 配对 → **防止误用**

#### 3.4 Prompt 注册到 PROMPT_REGISTRY

将 GJB 规则提取、约束提取等 prompt 注册到 `PROMPT_REGISTRY`：
- `GJBRuleExtractPrompt`：GJB 438C 规则提取
- `SRSConstraintExtractPrompt`：7 种约束提取
- `SRSConsistencyCheckPrompt`：一致性检测判断
- 使用 `DIYPromptABC` 支持快速试验新 prompt 而不动算子代码

### Phase 2: 中期增强（1-2 月，引入 L3+L4 组件）

#### 3.5 AgentFlow 合成测试用例（Gold Standard 3→100+）

**现状痛点**：Gold Standard 仅 3 份，测试覆盖严重不足。

**方案**：利用 AgentFlow 三阶段合成流程（轨迹采样→轨迹选择→QA合成）：

```
SRS 文档片段(Seed)  →  AgentFlow Sandbox(RAG后端)  →  一致性检测QA合成
 约束/表格/章节        轨迹采样: 检索相关条款          合成多跳一致性检测问题
                      轨迹选择: 选择深度足够的路径     "约束A规定X≤5，表格B中X=7，是否一致？"
```

**实施步骤**：
1. 将 `knowledge/srs_kb_graph_v2.json`（7720 节点）构建为 Faiss 索引，作为 Sandbox RAG 后端
2. SRS 文档中的约束对、表格行、章节段落作为 seed 输入
3. Agent 探索 SRS 文档，检索相关约束/表格/章节，构建多跳依赖链
4. 合成跨章节一致性检测问题，覆盖语法/语义/逻辑三层
5. 参照 `configs/synthesis/rag_config.json`，创建 `srs_config.json`

**预期收益**：Gold Standard 从 3 份扩展到 100+ 合成测试用例，为假阳性优化提供充分样本。

#### 3.6 DataFlow-KG 重构知识图谱

**现状**：`srs_kb_graph_v2.json` 有 7720 节点，但构建逻辑自研（`srs_kb_graph_builder.py`），缺乏补全/推理能力。

**方案**：
1. 用 `domain_kg` 算子包重构图谱构建，获得 storage step 血缘追踪和崩溃恢复
2. 用 `general_kg` / `graph_reasoning` 算子做链接预测、关系补全，增强 SRS 需求-约束-章节间的隐含关联
3. 用 `graph_rag` 算子包为一致性检测的检索增强提供支撑
4. 将 Z3 逻辑检测扩展为图谱上的多跳推理，发现跨章节逻辑冲突

#### 3.7 DataFlow-Skills 沉淀算子技能

将 SRS 算子沉淀为 Claude Code 技能（参照 `generating-dataflow-pipeline` 技能格式）：

```yaml
name: srs-consistency-pipeline-generator
description: GJB 438C SRS文档一致性检测Pipeline生成器
```

支持自然语言描述需求 → 自动组装检测 Pipeline，降低人工配置成本。

#### 3.8 One-Eval 自动化评测

- 用 NL2Eval 机制：`"评估一致性检测引擎在battery_srs上的语法层P/R/F1"` → 自动编排
- 将 SRS Gold Standard 注册为自定义 benchmark
- 注册 SRS 专用的层间一致性指标
- 从手动 `python3 tools/srs_eval.py` 升级为"一句话触发"

### Phase 3: 长期闭环（2-3 月，引入 LoopAI + DataMind）

#### 3.9 LoopAI 假阳性优化闭环

**现状**：一致性检测假阳性优化是手动迭代过程。

**方案**：构建 LoopAI 闭环：

```
"优化SRS一致性检测引擎，降低假阳性率"
        │
        ▼
┌─── JudgerAgent ───┐    ┌─── AnalyzerAgent ───┐
│ 在Gold Standard上  │───▶│ 分析假阳性模式      │
│ 运行 srs_eval.py   │    │ 分类：规则误触发/   │
│ 收集假阳性案例     │    │ 约束提取错误/Z3建模 │
└────────────────────┘    └─────────────────────┘
                                    │
                                    ▼
┌─── ObtainerAgent ──┐    ┌─── TrainerAgent ────┐
│ 获取新训练数据      │───▶│ 调整检测规则阈值    │
│ AgentFlow合成对抗   │    │ 优化约束提取prompt  │
│ 样本               │    │ 扩展Z3约束建模      │
└────────────────────┘    └─────────────────────┘
                                    │
                                    ▼
                            ┌─── ConfigerAgent ───┐
                            │ 管理检测引擎配置     │
                            │ 版本化规则库         │
                            └─────────────────────┘
```

#### 3.10 DataMind 知识管理

用 DataMind 统一管理 `knowledge/` 下的资产：

| DataMind 知识面 | SRS 项目应用 |
|----------------|-------------|
| RAG | 检索 GJB 438C 规则条文 |
| GraphRAG | 基于知识图谱的跨章节关联检索 |
| Skills | 调用 SRS 检测算子 |
| Memory | 记忆历次检测结果与优化决策 |
| Wiki | GJB 438C 标准知识库 |
| NL2SQL | 查询 SRS 表格数据 |

## 4. 技术可行性评估

### 4.1 兼容性分析

| 维度 | SRS 项目现状 | DataFlow 要求 | 兼容性 |
|------|------------|-------------|--------|
| Python 版本 | Python 3 (venv) | Python ≥ 3.10 | ✅ 兼容 |
| MinerU | 已安装 `~/mineru-env/` | DataFlow 可选依赖 `[mineru]` | ✅ 已有 |
| LLM API | GLM-5 API | OpenAI-compatible API | ✅ 兼容 |
| Z3 | 已用于逻辑检测 | DataFlow 算子可封装 | ✅ 可集成 |
| 存储格式 | JSON/JSONL | DataFlow FileStorage 支持 | ✅ 兼容 |

### 4.2 风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| DataFlow Core 学习曲线 | 短期效率下降 | 从单算子改造开始，逐步迁移 |
| AgentFlow 合成数据质量 | 合成的测试用例可能不准确 | 人工审核 + 迭代优化 seed |
| 知识图谱重构工作量 | 7720 节点迁移成本 | 分批迁移，保留旧图谱作为对照 |
| LoopAI 闭环复杂度 | 需要多 Agent 协调 | 先实现 Judger+Analyzer 两步，再逐步扩展 |

## 5. 预期收益量化

| 指标 | 现状 | Phase 1 后 | Phase 2 后 | Phase 3 后 |
|------|------|-----------|-----------|-----------|
| Gold Standard 数量 | 3 份 | 3 份 | 100+ 份 | 100+ 份 |
| 约束提取并发度 | 串行 | 并发(ThreadPool) | 并发 | 并发 |
| 断点续跑 | 不支持 | 支持 | 支持 | 支持 |
| 评测自动化 | 手动 | 手动 | 一句话触发 | 闭环自动 |
| 假阳性优化 | 手动迭代 | 手动迭代 | 手动迭代 | 自动闭环 |
| 知识图谱推理 | 无 | 无 | 链接预测+多跳推理 | 闭环优化 |
| 论文图表 | 手工制作 | Paper2Any 辅助 | Paper2Any 辅助 | Paper2Any 辅助 |

## 6. 总结

DataFlow 生态与 SRS 一致性检测项目高度契合：

1. **立即可做**（Phase 0）：MinerU 深化使用 + Paper2Any 论文辅助，零改造成本
2. **短期收益**（Phase 1）：DataFlow Core 算子化改造，获得并发/断点续跑/key校验三大收益
3. **中期突破**（Phase 2）：AgentFlow 扩展 Gold Standard + DataFlow-KG 增强图谱 + One-Eval 自动评测
4. **长期闭环**（Phase 3）：LoopAI 假阳性优化闭环 + DataMind 知识管理

**核心建议**：优先将 `srs_constraint_extract.py` 和 `srs_consistency_checker_v2.py` 改造为 DataFlow 算子，以 `LazyFileStorage` 替代当前手工缓存管理，即可立即获得并发推理、断点续跑、key 校验三项收益，改动量小且与现有 Gold Standard 评测框架兼容。
