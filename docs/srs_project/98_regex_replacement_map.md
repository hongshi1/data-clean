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

### B类：推理路径守卫/数学正则（**保留，但边界内三切口学习化**）

M103结论：87.7%管道型正则是数学/审计地基，模型替代会更差。
97号§2.5给出加强证据（arXiv 2504.05262：12个前沿LLM两位数加法
系统性失败；TRACK：模型调度数学工具95% vs 纯编码器58%）——
**文献支持我们的"保留"判定，且给出加强而非削弱的证据**。

| 文件 | 正则 | 命运 |
|------|------|------|
| claim_channels.py:verify_numeric | 区间包含/不相交代数 | **代数本体零学习**（numeric_z3 refute精确率1.000@零成本） |
| templates.py:normalize_unit | 单位归一化（ms/s/min/GB） | 同上 |
| ID正则（PZXQ格式） | 标识符格式匹配 | 格式保留；**接地概率化**（见下） |
| gjb_rule_engine.py（34处） | GJB标准结构合规 | 结构逻辑保留 |

**三切口学习化**（97号§2.5，学习的不是代数而是代数的输入与弃权）：
1. **接地概率化**：词典命中0/1→谓词概率（PL-Guard式）。identifier
   通道的"字面在场→1.0"应变为"绑定成立概率"——06号C06QA-016/017
   （ID在场但绑定错误）的修复路径；
2. **弃权学习**：ternary UNKNOWN（可微逻辑门2026已有三值变体）——
   只在需要弃权语义处学习；
3. **融合阈值GBDT化**：通道融合的固定阈值→学习权重（RLIE：规则+
   学习权重直接作分类器 > 规则再喂回LLM）。

### C类：数据生成正则（**与推理性能无关，不动**）

生成训练/评测数据的变异算子——不在推理路径上。

egt_synthesis.py（30处）、qa_mutation_ops.py、structural_mutations.py、
answer_mutations.py、gjb_mutations.py、logic_mutations.py、term_mutations.py、
param_mutations.py —— 全部是构造minimal pairs的模板工具。

### D类：召回侧正则（**词典FLAT化 + 规则Eiter回路化**）

| 文件 | 现状 | 增量方向（97号判定） |
|------|------|----------|
| ner_lexicon.py | 词表已外置config/ner_lexicons/*.json | **FLAT化**：词典不删除、进模型——词汇信息与Transformer双向增强；`ner_lexicons/*.json`保留为标注资产，消费方式升级 |
| rulepacks | 每文档人工onboard（doc01/05/06/07/08/10六份） | **Eiter回路**：教师从失败例归纳rulepack条目+求解器/回归验证修补——"谁写规则"从人工升级为教师+验证回路 |
| evidence_compiler.py | 证据编译19处 | 保留（结构化解析） |
| coverage_expert.py | 覆盖检查15处 | 部分决策型，观察 |

## 关键发现（v2，经95号调研+本地数字修正）

> ⚠️ **v1判断已被本地实验推翻**：v1曾认为"接线切分器v2是零成本收益"。
> 但 `data/gjb_438c/distillation/claim_downstream_v2.json` 显示该实验
> **已经跑过**——切分器claim识别质量大幅胜出（F1 0.7041 vs 正则
> 0.2427，正则严重欠切分under_seg 23-48%），却**输掉下游判定**
> （macro-F1 0.7496 < 正则0.8047，strict聚合下更差0.5789）。

**这不是切分器的问题，是对齐的问题——Alignment Bottleneck定律
（arXiv 2602.10380，2026-02）的教科书案例：**

- 分解的增益**不取决于分解器质量**，而取决于证据粒度是否与子claim
  严格对齐（Sub-claim Aligned Evidence, SAE）；
- 证据只在整claim级重复（SRE）时，更细的分解反而**降低**下游性能
  （PHEMEPlus/MMM-Fact/COVID-Fact三域验证）；
- 我们的管线里，**typed正则claim天然满足SAE**（typed通道的Z3/join
  专家就是按typed字段粒度对齐证据的），而切分器的叙事claim只配到
  SRE——所以"更强的分解器+更粗的对齐=更差的下游"。

**修复方向：不是换更强的分解器，而是给切分器claim接上typed通道
接口 + 证据侧细粒度对齐（SRE→SAE）。** 先修对齐，再谈上线。

切分器v2确实仍未接进生产（qa_module.py:342只支持typed/sentence，
tools/claim_segmenter.py的monkeypatch接口闲置）——但接线的前提是
先建claim→typed通道桥接，否则0.7496现象重现。

## 决策正则的统一替换架构（目标态）

```
当前:  typed正则分解 ──┬→ L0 NER(词典) → L1规则专家(正则守卫) → L2 NLI → 融合
                       └→ 跨域时C06QA-016/017"ID在场即support"误判（域绑定）

目标:  D3学生(叙事化) ──→ claim span + 类型标注 + 解释   ← 一次性产三样
         │                （先经typed通道桥接, SAE对齐）
         ├→ 确定性通道保留: verify_numeric/ID格式/单位归一 （B类, 代数零学习）
         ├→ 信任权重学习: identifier接地概率/融合阈值GBDT   （B类三切口）
         └→ 残余语义 → L2 NLI + 词典命中检查（A类换学生）
```

核心论点（供论文）：不是"全模型替代正则"，而是**分层迁移**——
把"什么算一个claim/什么算否定/哪个词是实体"（语义判定，12.3%的
决策型if）交给蒸馏模型，把"区间怎么包含/单位怎么换算/章节怎么
编号"（确定性数学，87.7%的管道型if）留在符号层，把两者之间的
**信任权重**（identifier在场→support的置信度、规则条目的权重）
交给学习。文献上有三个直接同构（97号§7）：PL-Guard（接地/策略
分离）、TRACK（模型调度数学工具）、Eiter系（LLM归纳规则+求解器
验证）——**均无GJB/SRS域先例，迁移空间属于我们**。可解释性来自
D3学生的span定位+叙事解释，性能来自L1/L0 refute覆盖的确定性下限。

> **事实修正（97号发现）**："identifier通道跨域产生12假support"
> 属于GLM-5直推于真实违例集的现象（77号）；identifier通道自身的
> 跨域失效是06号C06QA-016/017两例"ID在场但绑定错误"误判（49号）。
> 修复路径=上文B类三切口之①接地概率化。

## 实验路线（按性价比排序，95+97合并修订）

| # | 实验 | 成本 | 预期收益 | 依据 |
|---|------|------|----------|------|
| 1 | **claim→typed通道桥接**：切分器claim接上typed通道接口+证据侧细粒度对齐（SRE→SAE），然后才接入qa_module | 桥接代码+评测，1-2天 | 0.7496→≥0.8047的必要条件；识别优势(0.70 vs 0.24)变现 | 95号Alignment Bottleneck；claim_downstream_v2.json |
| 2 | **Eiter回路试点**：教师从06号30条crossdoc失败例归纳rulepack变体，与人工doc06_v1.json对比（教师API已缓存、rulepack注入接口、eval_cro 交叉评测设施全现成） | 半天 | D类"谁写规则"的范式验证；零新基础设施 | 97号§3.4首要行动② |
| 3 | D3学生叙事化重训（1638条数据已就绪） | 过夜GPU | support类性能+解释质量（已有锁定命令） | 项目既有路线 |
| 4 | D3学生替换A类否定/引用正则（推理时学生输出含这些槽位） | 依赖#3 | A类★★正则全部退役 | 95号§5.1叙事字段模型胜出+16-35pp |
| 5 | identifier接地概率化：在场→绑定概率（B类切口①） | 阈值校准 | C06QA-016/017类误判修复 | 97号§2.4 PL-Guard同构 |
| 6 | entity_detector span提取FLAT化/GLiNER化（D类词典进模型） | 需标注/零样本 | L0召回上限+跨域零配置 | 97号§1.1.4；GLiNER 0.3B CPU可跑 |

> 调和说明：97号把"U0切分器接入"列为首要行动①，但95号+本地
> 数字证明**裸接入会重现0.7496<0.8047**。两份调研的合并结论=
> 接入是对的，但**必须带桥接**（实验#1的形态），这是分歧的消解。

## 与文献调研的对接点（已完成2/3）

- 95号调研（claim算法）✅ → 已回填：Alignment Bottleneck修正#1，
  小模型分解先例（DecModel-0.25B 99.7%）、训练数据构造（MiniCheck
  幂集增广）备选#4/#6
- 96号调研（可解释NLI）⏳ → 待回填：D3学生解释生成的训练协议
- 97号调研（正则替代）✅ → 已回填：B类三切口、D类FLAT+Eiter回路、
  分层迁移论点、实验#2/#5/#6
