# 正则替换目标地图（代码库侧审计）

> 配套三份文献调研（95/96/97）的代码库侧分析。文献调研回答"有哪些方法"，
> 本文档回答"我们的代码里哪些正则值得换、哪些不该换、换的优先级"。

## 审计总览

| 指标 | 数值 |
|------|------|
| algorithms/consistency/ 内正则调用点 | **401** |
| 全管线 if 语句（M103审计） | 1653（12.3% 决策型 / 87.7% 管道型） |
| 已验证的正则→模型先例 | claim切分器v2（F1 0.796 vs 正则0.562） |
| 先例的接线状态 | **未接入生产**（monkeypatch接口存在，qa_module只支持typed/sentence） |

## 分类框架：四类正则，四种命运

### A类：推理路径决策正则（**换模型的主战场**）

直接影响 verdict 判定，跨域泛化差，有已验证的模型替代品。

| 文件 | 正则 | 问题 | 替换方案 | 优先级 |
|------|------|------|----------|--------|
| answer_claims.py:decompose_claims | typed claim提取（numeric/enum/identifier/quoted回退链） | F1 0.562，跨域负资产 | **切分器v2接入qa_module**（已有模型，只差接线） | ★★★ |
| answer_claims.py:_NEGATIVE | 否定标记枚举 | 枚举不可枚举（域外否定词漏检→假support） | NLI蒸馏已覆盖大部分；残余走D3学生 | ★★ |
| claim_channels.py:_EXPLICIT_NEGATION | 同上（验证侧） | 同上 | 同上 | ★★ |
| entity_detector.py:span提取 | 中文run/枚举表/用例提及正则 | L0召回的上限受词法约束 | 词典已外置；span提取可换序列标注（128M级） | ★ |
| answer_claims.py:_QUOTED/主语提取 | 「」引用与"XX的"主语截取 | GJB文法域绑定 | D3学生叙事化重训覆盖 | ★★ |

### B类：推理路径守卫/数学正则（**保留，是确定性地基**）

M103结论：87.7%管道型正则是数学/审计地基，模型替代会更差。

| 文件 | 正则 | 为什么保留 |
|------|------|-----------|
| claim_channels.py:verify_numeric | 区间包含/不相交代数 | 精确数学，NLI做数值比较不可靠 |
| templates.py:normalize_unit | 单位归一化（ms/s/min/GB） | 确定性变换 |
| ID正则（PZXQ格式） | 标识符格式匹配 | 结构化语法，非语义任务 |
| gjb_rule_engine.py（34处） | GJB标准结构合规 | 标准条款是确定性逻辑（章节缺失/编号断续） |

### C类：数据生成正则（**与推理性能无关，不动**）

生成训练/评测数据的变异算子——不在推理路径上。

egt_synthesis.py（30处）、qa_mutation_ops.py、structural_mutations.py、
answer_mutations.py、gjb_mutations.py、logic_mutations.py、term_mutations.py、
param_mutations.py —— 全部是构造minimal pairs的模板工具。

### D类：召回侧正则（**已配置外置，可增量学习化**）

| 文件 | 现状 | 增量方向 |
|------|------|----------|
| ner_lexicon.py | 词表已外置config/ner_lexicons/*.json | 词表可从文档图谱动态提取（NER面板M114已做前端版） |
| evidence_compiler.py | 证据编译19处 | 保留（结构化解析） |
| coverage_expert.py | 覆盖检查15处 | 部分决策型，观察 |

## 关键发现：最大性价比动作不是训练新模型

**切分器v2已经训练好（F1 0.796）但没有接进生产管线。**
qa_module.py:342 只允许 `decomposer in ("typed", "sentence")`——
"typed"是正则，"sentence"是SummaC式域中立切分，两者都不是蒸馏模型。
tools/claim_segmenter.py 的 `distilled_decompose_claims` 提供了
monkeypatch接口（`qa_module.decompose_claims`替换），说明当初设计
过接入路径，但生产配置从未切换。

第一步应该是：**给qa_module加 `decomposer="distilled"` 选项**，
在violations-17 + E3端到端上测refuteF1/violation定位，与typed对比。
这是一个零训练成本的实验。

## 决策正则的统一替换架构（目标态）

```
当前:  typed正则分解 ──┬→ L0 NER(词典) → L1规则专家(正则守卫) → L2 NLI → 融合
                       └→ 跨域时12个假support（域绑定）

目标:  D3学生(叙事化) ──→ claim span + 类型标注 + 解释   ← 一次性产三样
         │
         ├→ 确定性通道保留: verify_numeric/ID格式/单位归一  （B类，不换）
         └→ 残余语义 → L2 NLI + 词典命中检查（A类换学生）
```

核心论点（供论文）：不是"全模型替代正则"，而是**声明式分解——
把"什么算一个claim/什么算否定"从正则文法迁移到蒸馏模型，把
"数值区间/ID格式/单位"保留在确定性层**。这与M103审计的
12.3%/87.7%分割完全对应：换掉的是那12.3%的决策型，保留87.7%的
管道型。可解释性来自D3学生的span定位+叙事解释，性能来自
L1/L0 refute覆盖的确定性下限。

## 实验路线（按性价比排序）

| # | 实验 | 成本 | 预期收益 |
|---|------|------|----------|
| 1 | 切分器v2接入qa_module（`decomposer="distilled"`） | 零训练，1天 | claim识别F1 0.562→0.796，跨域假support消除 |
| 2 | D3学生叙事化重训（1638条数据已就绪） | 过夜GPU | support类性能+解释质量（已有锁定命令） |
| 3 | D3学生替换A类否定/引用正则（推理时学生输出含这些槽位） | 依赖#2 | A类★★正则全部退役 |
| 4 | 否定检测专项蒸馏（若#2不够） | 训练数据构造 | _NEGATIVE枚举退役 |
| 5 | entity_detector span提取换序列标注 | 需标注 | L0召回上限提升 |

## 与文献调研的对接点

- 95号调研（claim算法）→ 决定#3/#5用什么分解粒度方法
- 96号调研（可解释NLI）→ 决定D3学生解释生成的训练协议
- 97号调研（正则替代）→ 决定B类/C类的边界是否有新证据需要修正
