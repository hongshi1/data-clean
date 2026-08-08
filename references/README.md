# 参考代码与论文

> 张文涛课题组(PKU-DAIR/OpenDCAI)核心技术参考
> 用于SRS一致性校验与上下文关联项目

## 论文

| 论文 | 会议 | arxiv | 核心技术 |
|------|------|-------|---------|
| ProfiliTable | KDD 2026 | 2605.12376 | 表格数据处理Agent闭环(7-Agent协作+GT隔离+Summarizer复验) |
| RARE | KDD 2026 | 2503.23513 | 检索增强推理训练(y=k⊕r分解+隐式masked loss) |
| DataFlow | 技术报告 | 2512.16676 | LLM数据准备系统(Operator-Pipeline-Storage三层抽象) |

## 仓库

### 1. ProfiliTable/ — 表格Agent闭环

**论文**: arXiv:2605.12376 (KDD 2026)
**核心参考**:
- `main/ProfiliTable.py` — 7-Agent闭环入口
- `table_agent/` — Agent定义(Profiler/Evaluator/Summarizer等)
- `table_agent/utils/` — TableState黑板、ReAct探查

**SRS对接**: 改造为SRS表格一致性检测——Profiler探查合格性表/追溯表→Evaluator脚本比对值→Summarizer复验"合理差异vs真实矛盾"

**关键设计**:
- Evaluator非LLM(纯subprocess跑eval.py) — GT隔离保证客观性
- Summarizer用ReAct找discrepancies — 不打分只找问题
- 四层防御(脚本timeout→Debugger→外层重试→Finalizer兜底) — 100%可运行率

### 2. Query-Adaptive-GraphRAG/ — 自适应图检索

**论文**: VLDB 2026 (基于RAPTOR)
**核心参考**:
- `raptor/` — RAPTOR递归抽象树构建
- `train_mlp.py` — MLP路由器训练(768→384→384→3, gumbel_softmax硬路由)
- `evaluator.py` — 评估逻辑
- `build_tree.py` — 树构建入口

**SRS对接**: RAPTOR树用于SRS上下文关联——章节文字→递归抽象树→不同层级聚合不同粒度的"同一事物"。MLP路由器按查询复杂度选择检索深度。

**关键设计**:
- 硬路由(gumbel_softmax hard=True) — 离散选一层，直通估计器反传
- 训练用HotpotQA的oracle F1作隐式监督 — "简单→摘要层/复杂→叶层"从数据学得
- 即插即用 — 路由器训练一次迁移，不重训LLM

### 3. RARE/ — 检索增强推理

**论文**: arXiv:2503.23513 (KDD 2026)
**核心参考**:
- `train/sft.py` — masked loss训练实现
- `process/` — 数据处理(y=k⊕r分解)
- `inference/` — 推理逻辑
- `eval/` — 评测

**SRS对接**: 后续方向——GJB规则作检索知识，训练"比对→判矛盾"推理链。需要微调+算力。

**关键设计**:
- y=k⊕r: ⊕是concatenation，知识k和推理r拼接
- 隐式masked loss: 注入R(x)使p(k|x,R(x))≫p(k|x)，知识损失自然坍缩，推理损失主导
- 训练和推理都需要检索
- 8B模型在PubMedQA 75.8%超GPT-4+RAG

### 4. DataMind/ — 上下文记忆+矛盾关系

**核心参考**:
- `datamind/kernel/` — 核心引擎(Memory管理)
- `datamind/adapters/memory.py` — _conflicts()矛盾对收集(行664-682)
- `datamind/kernel/memory.py` — MemoryLinkKind.CONTRADICTS定义(行98-107)
- `docs/adr/` — 架构决策记录

**SRS对接**: CONTRADICTS关系建模SRS中"允许vs禁止"矛盾对。需把"声明矛盾"升级为"检测后声明矛盾"。

**关键设计**:
- 矛盾对在Recall后自动收集 — 仅当双方都被词法token-overlap召回时
- 双时态governed Memory — Assert/Supersede/Retract
- 检索用词法(非向量) — 保证零依赖、确定性、可Replay

### 5. DataFlow-MM/ — 多模态图文一致性

**核心参考**:
- `dataflow/operators/` — ImageConsistencyFilter(NLI蕴含), CLIPScoreFilter, VisualGroundingRefiner
- 多模态质量评估算子

**SRS对接**: NLI蕴含检测移植为SRS图文一致性。需换中文NLI模型+补OCR数值比对兜底层。

**关键设计**:
- 三层漏斗: NLI层(bart-large-mnli,阈值0.35) → CLIP/LongCLIP层 → VLM Yes/No层
- ImageConsistencyFilter: "图文一致性"转化为"caption+question→answer的文本蕴含"
- LongCLIP: 位置编码插值把77→248 token

### 6. DataFlow/ — 数据准备系统(主仓库)

**论文**: arXiv:2512.16676 (技术报告)
**核心参考**:
- `dataflow/operators/knowledge_cleaning/` — KB Cleaning Pipeline(MinerU→分块→清洗→QA)
- `dataflow/operators/core_text/` — 文本处理算子(PromptedGenerator等)
- `dataflow/pipeline/` — Pipeline编排(compile/forward+键校验)
- `dataflow/utils/storage.py` — FileStorage(step()链式存储)
- `dataflow/serving/` — LLM调用层(APILLMServing_request)
- `dataflow/prompts/kbcleaning.py` — KnowledgeCleanerPrompt(8条清洗规则)

**SRS对接**: KB Cleaning Pipeline用于SRS文档处理流水线。Operator-Pipeline-Storage模式用于检测Agent架构。

**关键设计**:
- Operator极简(只有一个run()抽象方法) — 签名由子类定义
- step()机制 — 每个算子storage.step()自动管理中间状态，可断点续跑
- compile时键校验 — 防止input_key/output_key拼写错误
- KB Cleaning 4算子: MinerU解析→分块→LLM清洗→QA生成
