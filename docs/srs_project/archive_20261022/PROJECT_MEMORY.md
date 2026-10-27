# 项目研究记忆索引

> 更新：2026-10-20
> 本文件只记录时间线和历史实验索引，不定义当前任务、指标或架构。当前规范见 [project_guide.md](project_guide.md)、[00_requirements_and_route_overview.md](00_requirements_and_route_overview.md)；架构审计见 [39_project_architecture_audit.md](39_project_architecture_audit.md)。

## 当前事实

- 研究数据基础：16份真实GJB格式SRS及多种解析/结构化资产。
- 两个研究方向：A上下文关联；B answer vs SRS evidence 三态校验。
- 单位置GJB合规为独立任务；ACDD/图表来源差异不自动并入B。
- 当前没有统一的解析→AtomicClaim→关联/召回→EvidenceContext→Verifier→服务端到端链。
- 40/48项是历史候选分类，等待taxonomy v2逐项审查。
- AEE v1当前1443条（S783/R535/N125）是迁移审计资产，不是冻结的最终benchmark。其旧runs规模不同，旧指标不能直接引用到当前快照。
- 场景1对方示例QA（91条，doc11目录）已完成取证审计：90条可在04号SRS定位证据，`scene1_qa_audit.json`入MANIFEST+快照；为real_observed层首选候选源，gold待M3人工双标。
- taxonomy v2落地（`knowledge/consistency_taxonomy_v2.json`+快照）：40项全字段操作化，main_B 29+compliance 11，无一项validated；module_assignment/data_readiness待人审。
- AEE question恢复审计完成（`aee_question_recovery.json`入MANIFEST+快照）：868/1443可恢复原始question，574条family无question；重放与AEE文件1443条全等验证；发现B1分支实际0命中。
- M3标注手册v1.0完成（41号文档）：三态决策树+04号真实判例10个+Kappa口径；pilot执行待上游冻结context。
- 核心重构prototype已落地：`QAConsistencyModule`统一消费question+answer+frozen context并返回evidence chain/context hash；`answer_mutations`只改answer，旧pair/MMQA算子由`legacy_answer_mutation_audit.json`隔离。当前仅少量数值/单位算子有自动proof，40项生成器和旧入口退役尚未完成。
- family v1是旧pair任务；family C跨表图样本需隔离或重建。

## 历史任务线

| 时期/资产 | 输入契约 | 状态与解释 |
|---|---|---|
| 早期语法/语义/逻辑检查 | 单文档规则、pair或occurrence | 历史算法和数据，不代表当前B契约 |
| family_evalset_v1 | premise/hypothesis、六族二分类 | 历史pair benchmark；存在训练重叠审计问题，C族为表图差异 |
| ACDD/Blackboard | 多通道结构观察、锚点校准、分歧译码 | 独立来源差异/感知误差研究，不与B三态直接合分 |
| URE v1–v4 | 检索query→文档单元 | 方向A检索实验；不能证明方向B已端到端接通 |
| answer_evidence_evalset_v1 | answer + 文本化evidence claims | 迁移基线；证据位置、scope、gold和runs需继续审计 |

历史分数只有在同时指明数据版本、输入契约、split、gold来源和run id时才可引用。不同任务版本不组成单一性能曲线。

## 关键历史修正

- 2026-10-20：明确方向B的目标是answer vs SRS evidence；图、表、正文是证据来源，不是相互比较的两端。
- 2026-10-20：AEE v1隔离family C旧跨表图反推样本，当前快照1443条；先前1611/1735规模runs不代表此快照。
- 2026-10-20：发现服务入口引用不存在的`algorithms.check_engine`；旧API不等于新Verifier服务。
- 2026-10-20：新增`QAConsistencyModule` facade与独立answer mutation prototypes；`verify.py`改为显式completeness proof且旧binary NLI不再为新QA模块判S/R。旧pair算子保持legacy隔离；全40项算子、正式benchmark和API迁移未完成。
- 2026-10-20：确认`verify.py`存在默认表格闭世界和语义高重合非蕴含判refute等待修语义；规范要求按范围证明完整性和显式反证。

## 后续记录格式

新研究决定按日期追加，并包含：决策、依据、受影响任务/数据版本、修改文件、验证命令及结果。不要在本文件复制大段当前规范、旧模型成绩或未经运行记录验证的指标。
