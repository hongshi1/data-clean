# 39 · 项目架构审计与重构蓝图

> 审计日期：2026-10-20 | 方法：4路并行静态审查 + 文件/导入核验
> 范围：项目级架构与旧服务/召回/校验原型静态审计。本会话范围按[40_method_reconstruction_plan.md](40_method_reconstruction_plan.md)限定为上游question召回之后的QA一致性校验；检索/上下文关联由另一会话维护。
> 方法层专项拆分、算法方法归属与论文贡献审计见 [40_method_reconstruction_plan.md](40_method_reconstruction_plan.md)。
> 注意：工作区在审计前已存在大量用户/其他任务改动。本报告只记录证据和建议，不把未核验的改动归因于本轮。

## 1. 执行摘要

当前仓库不是一个已接通的端到端系统，而是多代研究原型并存：

```text
旧图谱服务：server → ContextGraph → 缺失的 CheckEngine       [启动阻断]
方向A召回：URE → EvidenceStore → MultiHeadRecall → Rerank    [实验入口]
黑板/ACDD：pair/scenario → agents → critic/decoder           [历史独立任务]
方向B原型：answer → Verifier → checker                       [局部单测/评测]
数据构建：MinerU/VLM/Visio → chunks/anchors/pairs/QA            [多格式、无统一claim层]
```

核心缺口不是缺检测器，而是任务版本和数据契约未统一，**解析 → 原子声明 → 关联/检索 → answer-evidence验证 → 评测**没有共享稳定接口。不能把旧图表差异、URE召回、pair二分类、ACDD结果和新三态结果合并成一个“项目总成绩”。

### 当前成熟度（审计判断）

| 层 | 实际状态 | 可否声称端到端完成 |
|---|---|---|
| 原始/解析资产 | 16份SRS，多种MinerU、chunks、Visio、OCR/VLM资产 | 否。来源和格式尚未统一到claim级 |
| 方向A召回/聚合 | ContextGraph、EvidenceRecall、Blackboard等多套实现 | 否。schema不同，只有部分实验脚本/服务调用 |
| 方向B verify | `verify.py`三态原型和单测存在 | 否。证据范围、refute语义和来源定位未达规范 |
| A→B集成 | 未找到统一应用层接口 | 否 |
| 服务 | 旧API代码存在，但缺`algorithms.check_engine` | 否，当前导入即失败 |
| Benchmark | AEE v1 1443条、family v1 896条、strict40旧集235条 | 否。是不同任务/版本，不能合并 |
| 类型本体 | 40/48项历史设计文档并存 | 否。taxonomy v2尚未建立 |
| 数据血缘 | MANIFEST和runs机制存在 | 部分。当前核心AEE/family未进入MANIFEST，runs缺数据hash |

## 2. 任务边界与研究架构

权威边界以 [00_requirements_and_route_overview.md](00_requirements_and_route_overview.md) 为准：

| 工作流 | 目标对象 | 目标 |
|---|---|---|
| A. 上下文关联 | SRS中分散的occurrence/claim | 同实体、需求或约束的候选聚合与证据召回 |
| B. Answer-evidence校验 | 单一answer + SRS evidence context | support/refute/not_in_evidence |
| C. 规则合规 | SRS片段 + GJB规则 | compliant/non_compliant/unknown，独立评测 |
| ACDD/来源差异 | 已关联的异构来源结构/事实 | 感知误差校准和来源间差异，独立任务，除非重标成B样本 |

必须区分两个比较关系：

```text
方向B：answer  ↔  SRS evidence
来源差异任务：SRS source A  ↔  SRS source B
```

图/表/正文是证据来源，不自动成为B任务的两端。仅改名`premise/hypothesis`为`evidence/answer`不能完成迁移，必须重审语义、证据范围和gold。

## 3. 证据核验发现

### 3.1 服务入口有硬阻断

`server/main.py:32-33` 导入：

```python
from algorithms.context_graph import ContextGraph
from algorithms.check_engine import CheckEngine, CHECK_ITEMS
```

当前代码树没有 `algorithms/check_engine.py`，只有 `tools/archive/2026_10/legacy_algorithms/check_engine.py`。只读导入探测结果：

```text
check_engine: None
verifier: algorithms.consistency.verify 可导入
```

所以 `server.main` 不可作为已运行主服务。并且该文件在导入期实例化ContextGraph、读取QA、遍历MinerU content list、加载Mermaid，并重载上传目录，存在模块导入期I/O，与仓库治理规则冲突。

### 3.2 服务并未实现新B契约

旧 `/api/check/{doc_num}` 调用 `ENGINE.run(doc_num)`，没有answer或EvidenceContext；`/api/activate`调用ContextGraph图激活。`Verifier`当前调用方是评测脚本和测试，没有服务或召回管线接线。因此：

- 旧`/api/check`是全文/旧规则检查接口，不等于新B的verify接口。
- `EvidenceRecallPipeline`是URE实验管线，未接Verifier。
- Blackboard仍以completeness/flow/terminology/parameter等pair/scenario任务工作。

不得在前端/API中把这些端点标成新三态校验已服务化。

### 3.3 方向A有多套不兼容模型

| 实现 | 输入/输出特征 | 真实定位 |
|---|---|---|
| `algorithms/context_graph.py` | graph_store，图节点/边/激活子图/items | 旧图谱查询/可视化，服务曾依赖 |
| `algorithms/context_linking/evidence_recall/` | URE chunk，owner/kind/title/score/单元文本 | 召回实验，未接verify |
| `algorithms/blackboard/` | EvidenceStore、agent黑板、分歧集、decoder | pair/scenario/ACDD实验 |
| `algorithms/context_pipeline.py`及unit检索模块 | feature pack/检索单元 | 其他检索实验 |
| `tools/archive/srs_long_context*.py` | 自定义ContextItem、索引和检测器 | 历史归档实现 |

没有统一`Occurrence`、`AtomicClaim`、`CandidateLink`或`EvidenceContext`适配协议。`EvidenceStore.from_ure()` 甚至把除image外的chunk统标为table_row，text未有独立source type。它不能直接满足answer-evidence来源和位置追溯要求。

### 3.4 解析输出尚非原子声明层

`tools/srs_mineru_parse.py`可抽sections/tables/images/constraints/versions/req_ids，但不是规范化、逐条可回源的atomic claim store。缺失统一的predicate、subject、operator、value、unit、source_ref、解析置信度和scope/exhaustiveness。当前参数抽取含启发式前文猜测，应先作为候选而非gold事实。

该脚本还在模块导入时创建输出目录，并输出当前时间`parse_date`；若结果纳入快照，应把I/O移入显式执行入口，并避免运行时间改变内容指纹。

### 3.5 Verifier与规范有语义冲突

`algorithms/consistency/verify.py` 当前：

- `Evidence.is_exhaustive()` 默认只要`type == "table"`就闭世界；新规范要求逐样本、逐范围证明完备性。
- `verify_multi()`用`any(ev.is_exhaustive())`将多个证据块压成一个全局closed标记，会把一个闭世界表格传播到其它开放证据。
- 语义NLI不蕴含且词面重合`ov >= 0.5`会判refute；相关性不等于显式反驳，规范要求不充分时NIE。
- 枚举将多个证据文本拼接，可能跨证据/实体误命中；支持结果引用可能不是实际匹配的evidence。
- 当前数据类缺少scope、claim-level refs、extraction confidence、页/行/节点位置和结构化claim。
- 复合answer采用“任一refute主导”，但answer原子化和证据内部冲突规则尚未冻结。

当前是可研究的原型，不应描述为已实现完整三态规范。

### 3.6 数据、runs和manifest版本不闭合

- 当前`answer_evidence_evalset_v1.json`：1443条，S783/R535/N125；family C已从AEE构建器跳过。
- 旧AEE runs记录1611/1735条，不能证明1443快照指标。评测脚本现绑定实际输入SHA/数量/标签，且不再静默将异常改成NIE。
- `PROJECT_MEMORY.md`已压缩为历史索引；其它旧文档/论文仍需逐项迁移或标记。
- MANIFEST现登记AEE/family快照及AEE QA输入；taxonomy、全部生成依赖、split和leakage报告仍未闭合。
- `run_utils.open_run()`记录git SHA、config和时间，但没有强制记录dataset SHA、split SHA、taxonomy/generator版本。
- family构建依赖缺失的`synth_s1_split.json`；即使冻结JSON存在，从当前工作区也不能保证全链从源重建。
- family v1有29条和pair训练集完全重叠；AEE生成器会局部过滤这些行，但不能据此宣称原family快照无泄漏。
- family C仍是旧表格↔图pair，不是B样本；必须继续隔离或从原始图证据重建。

## 4. 文档体系治理

### 4.1 当前规范链

| 优先级 | 文档 | 职责 |
|---|---|---|
| 1 | `project_guide.md` | 当前状态、操作规则、入口和里程碑 |
| 2 | `00_requirements_and_route_overview.md` | 研究问题、任务边界、目标系统架构 |
| 3 | `28_answer_evidence_task_reconstruction_plan.md` | B数据契约与构建计划；须与00/guide同步 |
| 4 | 本文 | 多agent审计证据和架构修复蓝图，不取代实验协议 |
| 局部 | `19/30/31/33/38` | 方向A召回、治理、baseline或实验进展 |
| 草案 | `21_tri_state_eval_protocol.md` | 未冻结；macroF3与当前00有冲突，先审定再执行 |

`PROJECT_MEMORY.md`只作时间线/历史索引，不作任务定义。论文草稿、旧实验报告、40/48类注入文档不能反向定义当前任务。

### 4.2 建议整理但本轮不移动/删除

工作区已有大量用户和其它任务的未提交更改，因此本轮不移动或删除历史文件。后续集中治理时再执行：

- 将两份`14_strict_40*`合成唯一历史来源；保留原ID和审计映射。
- 将`01–17`旧任务文件移入`archive/legacy_task_definitions/`或只留索引页。
- 将`20/23/26`限定为URE schema/数据生命周期文件，不能声称是整个项目唯一规范。
- 将`24/25/35`结果按数据版本拆分，主结果只指向可重跑的run和结果JSON。
- ACDD/论文草稿在任务裁决前标记独立历史任务，不能与B三态主线混写。
- 清理重复总结、绝对路径、失效路径、过期的“实施中/已完成”标签；使用实际资产清单生成路径表。

## 5. 目标代码架构

```text
src/algorithms/domain/
  models.py            SourceRef, ParsedBlock, AtomicClaim, Item, EvidenceContext
src/algorithms/ingest/
  adapters/             MinerU, text/table, Visio/XML, OCR/VLM adapters
src/algorithms/context_linking/
  linker.py             候选occurrence/item关联；不产出矛盾标签
src/algorithms/retrieval/
  retriever.py          query + scope → 带source refs的EvidenceContext
src/algorithms/consistency/
  verify.py             answer + EvidenceContext → 三态结果
src/algorithms/compliance/
  check.py              SRS片段 + GJB规则 → 独立合规结果
src/application/
  service.py            接线和用例编排；无导入期资产加载
server/
  routes/               HTTP schema/auth，只依赖application facade
tools/
  build_*.py, eval_*.py  显式离线资产构建和实验入口
```

当前不要求按此目录立刻搬迁全部文件。先建立稳定domain schema和adapter contract，再逐个接线，旧模块保留原位作为历史实现直到替代和测试完成。

方法族与现有算法的具体归属、保留/降级决策、baseline和论文贡献映射见 [40_method_reconstruction_plan.md](40_method_reconstruction_plan.md)。

### 5.1 统一最小数据契约

```text
SourceRef: doc_id, source_type, section, page/block/row/node/region, raw_asset_ref
AtomicClaim: claim_id, source_ref, surface_text, predicate/subject/object/value/operator/unit,
             extraction_method, extraction_confidence, scope_id, exhaustiveness_proof
Item: item_id, entity_key, semantic_role, occurrences, candidate_links, link_confidence
EvidenceContext: answer_scope, claims[], retrieval_trace, completeness
VerdictResult: verdict, per_claim[], cited_evidence_ids[], discrepancy_types[], rationale
```

字段缺失不能静默填成“完备”或“闭世界”。文本、表格、图片均使用同一来源协议，但允许不同的payload adapter。

## 6. 重构计划和验收门

### M0：冻结决策

明确原子answer粒度、复合answer规则、证据内部支持/反驳冲突规则、闭世界证明、ACDD归属。没决策的规则保持`unknown`，不能硬编码成历史习惯。

### M1：taxonomy与资产盘点

产物：`inconsistency_taxonomy_v2.json`和真实路径/资产索引。历史40+项分为B主任务、A关联、C合规、ACDD独立、待证据、退役；另分开记录实现成熟度和数据成熟度。

验收：每项都有可执行的输入/输出/标签规则，或明确标记不进入B；所有资产声明可用实际文件验证。

### M2：domain schema和atomic claim

产物：解析块、claim compiler及source ref。抽样回源率100%；OCR/VLM错误可追踪；每个闭世界判断附完整性证明。

### M3：benchmark血缘

生成answer、证据上下文和gold分离；文档/实体/图片/模板隔离；自动duplicate/leakage报告；MANIFEST覆盖输入、输出、构建器和split。

### M4：最小A→B链路

用一个文档、一个text/table/figure来源adapter完成：parse → claims → retrieval → verifier。先在离线应用层接线，不立即改旧服务API。

### M5：校验语义和回归

测试显式反证、支持、NIE、scope incomplete、局部闭世界、多个证据作用域隔离、复合answer决策。未知不再由词面相似度升级成refute。

### M6：服务迁移

先修复旧服务导入阻断或将其显式隔离；新端点新增`POST /api/verify`消费answer+EvidenceContext，旧`/api/check`保持旧行为/标记legacy，只有契约测试和前后端迁移完成后才替换。

### M7：冻结结果和论文

重新运行当前数据哈希下的baselines；分A/B/C/ACDD报告；旧runs标记stale，不覆盖；只引用能够由资产和脚本重建的结果。

## 7. 优先级

| 级别 | 问题 | 动作 |
|---|---|---|
| P0 | 任务/结果版本混淆 | 重写PROJECT_MEMORY为历史索引；文档索引标权威、草案、legacy |
| P0 | 服务入口导入缺依赖 | 新增启动/import测试；不以替换API语义方式绕过 |
| P0 | refute规则不满足显式反证要求 | 修Verifier并测试；按证据块scope判断，不传播全局closed |
| P0 | AEE run配置过期 | 评测器读取数据meta/sha，保存实际规模和hash，避免吞异常 |
| P0 | 多方法族被写成单一方法 | 按40号方案拆A1/A2/B/C/ACDD/legacy并冻结各自输入输出/指标 |
| P1 | 无统一source/claim schema | 实现domain模型和一个parser adapter，先小样本验证 |
| P1 | MANIFEST/runs血缘不闭合 | 登记benchmark和构建依赖；run写入dataset/split hashes |
| P1 | 多套A实现无统一接口 | 建adapter，不立即删除旧实现；同一个固定query做一致性回归 |
| P2 | 文档重复与旧文件误导 | 在确认依赖链接后批量归档，保留历史映射和搜索入口 |

## 8. 本轮修复范围

已完成：重写00/project guide为任务边界和架构入口；将PROJECT_MEMORY压缩为历史索引；新增本架构审计；修正`tools/eval_aee.py`中过期的1611条固定配置、消除静默catch、绑定输入SHA/标签数量并在result重复记录；MANIFEST登记AEE、family及QA输入资产；增加run fingerprint回归测试。

后续仍未做：服务API迁移、旧模块物理移除、AEE重新标注、taxonomy与40项全算子覆盖、正式QA benchmark冻结、真实双人pilot。当前`QAConsistencyModule`只自动判部分精确/数值/集合claim；未实现语义类型保守NIE并标partial。旧pair模块保留供历史复现，但新包入口不将其作为完整QA校验。
