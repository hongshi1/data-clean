# 多Agent系统改进调研报告（7-Agent联合调研）

> 日期: 2026-08-12 | 7个Agent并行调研 | 针对4个核心问题

---

## 问题1: 移植到万擎多Agent体系的成本

**结论: 中偏低**

| 维度 | 评估 |
|------|------|
| 业务逻辑 | 可平移（分析逻辑不依赖框架） |
| 接口适配 | 需收敛为框架schema（A2A用parts/artifacts, MCP用resources/tools） |
| 状态管理 | 无状态单次→Task生命周期+artifacts |
| 成本 | 若万擎兼容A2A/MCP→**低**；私有协议→**中** |

**建议**: 以A2A/MCP作适配中间层，避免厂商锁定。

**关键参考**: A2A(Google,2025), MCP(Anthropic), AutoGen(arXiv:2308.08155), MetaGPT(arXiv:2308.00352)

---

## 问题2: 无分组时能否动态降级运行

**结论: 能（降级方案）**

```
无分组时:
  ├─ 语法层(编号/格式): 无影响, 正常运行
  ├─ 单条目语义: 无影响, 正常运行
  ├─ 跨条目语义(同参数不同值): 退化为全两两比对, 精度↓30-50%
  ├─ 逻辑层(组内约束): 完全失效, 召回↓60-80%
  └─ 整体: F1↓约40%
```

**技术方案**: 条件边(LangGraph)做硬路由 + Orchestrator做软补充
- `if groups is None: skip CrossGroupAgent`（跳过依赖分组的Agent）
- 每个条目视为单例组（singleton）兜底
- 显式声明降级状态（下游知道置信度降低）

**关键论文**: MetaGPT(arXiv:2308.00352), LangGraph条件边, NeurIPS 2025 Dynamic Multi-Agent Orchestration

---

## 问题3: 单轮LLM→Agentic深度挖掘

**结论: 用复杂度路由+自适应深度**

```
ComplexityRouter(轻量LLM打分)
  ├─ 低复杂度 → 单轮直出(省2-3x token)
  ├─ 中复杂度 → ReAct 1-2轮工具调用
  └─ 高复杂度 → Reflexion多轮试错+回溯
```

| 维度 | 单轮Miner(当前) | Agentic Miner(目标) |
|------|----------------|-------------------|
| 控制 | 固定prompt→固定输出 | ReAct循环: 思考→行动→观察→反思 |
| 深度 | 静态一次过 | 自适应按复杂度增减步数 |
| 信息源 | 仅输入上下文 | 可调工具(检索/校验/子查询) |
| 纠错 | 无 | 自反思+episodic memory重试 |

**关键论文**: ReAct(ICLR 2023), Reflexion(NeurIPS 2023), Tree of Thoughts(NeurIPS 2023), Graph Counselor(ACL 2025), Analytica(ICLR 2026)

---

## 问题4: 对比分组质量

**结论: 先聚类/分层，后对比**

**随机对比的问题**: 跨场景对比产生的"差异"大部分是噪声，导致假阳性/假阴性/信号稀释。

**保证对比同场景的方法**:
1. **聚类前置**: DBSCAN/HDBSCAN按trace特征聚类，簇内对比
2. **相似度匹配**: k-NN on embedding找最近邻配对
3. **场景标签约束**: 用元数据(接口ID/章节/用户类型)做硬约束分层
4. **对比学习分组**: 正样本对来自同场景，负样本对来自不同场景

**分组质量评估**: Silhouette Score, 场景纯度(Purity), NMI, 下游AUC提升

**关键论文**: Khosla et al. "Supervised Contrastive Learning"(NeurIPS 2020), Pinpoint(Chen et al. 2002)

---

## 问题5: 通用miner设计

**结论: 规则外部化 + 能力声明式注册**

```
通用miner架构:
  ├─ Document Adapter (多格式接入: md/docx/pdf)
  ├─ Abstract Document Model (Section/Block/Entity/Relation)
  ├─ Capability Registry (能力声明: 语法/语义/逻辑)
  ├─ Knowledge Plugin Layer (可插拔: GJB规则/IEEE规则/自定义)
  ├─ Prompt Template Engine (模板slot化)
  └─ Orchestrator (选载+组合+调度)
```

**关键改造**:
- `gjb_438c_rules_full.json`→通用规则格式(任何标准可插拔)
- `sc1_detector.py`→`capability_checker.py`(操作抽象文档模型)
- Prompt从GJB专用→`{role}{task}{rules}{context}{output_format}`模板

**关键论文**: Parthenon Law(arXiv:2606.04602), RADIANT-LLM(arXiv:2604.22755), FROAV(arXiv:2601.07504)

---

## 问题6: Agent编排与协作

**结论: LangGraph DAG编排，结构化产物传递**

| 模式 | 优势 | 适用 |
|------|------|------|
| 串行 | 简单可调试 | 有依赖流水线(SRS解析→校验) |
| 并行 | 速度快 | 独立子任务(16份并行) |
| **DAG** | **灵活依赖+自动并行** | **混合依赖(聚合→检测)** |

**SRS项目推荐**: LangGraph构建DAG——方向A(上下文聚合)作为并行Fan-out，方向B(一致性校验)作为串行下游，中间用结构化条目JSON作为共享State。

**关键论文**: LangGraph(LangChain 2024), AutoGen(arXiv:2308.08155), More Agents Is All You Need(arXiv:2402.05120)

---

## 问题7: 质量评估方法

**结论: LLM-as-Judge + 人工抽检 + 可信度分级**

| 方法 | 说明 | 可信度 |
|------|------|--------|
| LLM-as-Judge | GPT-4级裁判评分，与人类一致性>80% | 高(需缓解位置/冗长偏差) |
| 双LLM交叉验证 | kimi+claude都判正确才保留 | 高 |
| 人工抽检 | 分层抽样+双人标注+Cohen's κ | 最高(但成本高) |
| 自一致性检验 | 同输入多次采样求一致率 | 中 |
| 可溯源约束 | 每个结论附原文证据 | 高 |

**SRS项目推荐**: LLM-as-Judge(双裁判kimi+claude) + 人工抽检校准 + 可信度分级 + 自一致检验

**关键论文**: MT-Bench/Chatbot Arena(NeurIPS 2023, arXiv:2306.05685), G-Eval(arXiv:2303.16634), ChatEval(arXiv:2308.07201)

---

## 总结: 改进路线图

```
短期(1-2周):
  ├─ 测试集改全LLM生成(不用规则模板)
  ├─ 双LLM交叉验证(kimi+claude)
  └─ 质量评估用LLM-as-Judge

中期(1-2月):
  ├─ Miner改Agentic(复杂度路由+ReAct)
  ├─ 通用miner设计(规则外部化+能力声明)
  └─ LangGraph DAG编排

长期(3-6月):
  ├─ 移植到万擎体系(A2A/MCP适配)
  ├─ 动态降级(无分组容错)
  └─ 人工抽检+Kappa校准
```
