# GJB SRS研究项目指南

> 版本：10.1 | 更新：2026-10-30
> 状态：**CascadeVerify v2审计响应收口（M28）**。可信度审计→P0/P1修复→诚实数字完整链条已固化：持久dev/test切分+test侧诚实评测（修复后test=0.8286）、P1三项确定性修复（support召回2/6→5/6）、06号跨文档sound评测集与gap量化（-0.486）；级联全链路（DEQ→L0→L1专家族9个→per-claim融合→L2 NLI→级联升级→L3 LLM）实现并在91QA上完成论文矩阵评测；结果总览见 `49_cascadeverify_v2_results.md`（论文数字唯一权威来源，审计响应=其§10）。
> 本文件是当前项目入口。旧文档已归档至 `archive_20261022/`（91份）。

## 1. 权威数据源（不可修改，不可派生覆盖）

### 源A：实施方案文档（40项校验的原始定义）

- 文件：`docs/srs_project/软件需求规格说明辅助生成场景微调数据应用设计与落地实施文档.docx`
- 关键章节：**技术三——面向武器装备科研数据的多层级跨模态一致性校验技术功能需求**（段[116]-[211]）
- 内容：四层校验体系（术语8+参数10+业务逻辑11+国军标合规11=40项），每项带原始示例
- 原始意图：**跨文档、跨资料比对检测**，作为数据质量审校规则、负样本构造规则和问答对过滤标准
- GJB层参照标准：国军标841、国军标2438、国军标438C等（不仅438C）

### 源B：官方QA对 + 04号SRS

- QA对：`docs/doc11/场景1-*/高质量问答对（配套…04数据统一访问服务…）.json`（91条Alpaca格式）
- SRS原始：`docs/doc11/场景1-*/2-某项目的合同、需归文档/数据服务软件需求规格说明.docx`
- 解析后：`data/gjb_438c/mineru_standard/04…/office/*content_list.json`（411块：text235+table82+image48+list43）
- 官方整合资产：`data/gjb_438c/qa_frozen/scene1_official_reference_v1.jsonl`（91行：Alpaca源+冻结证据+语句+silver标签）

### 已删除的派生文档（2026-10-22，偏离原始意图）

以下文档曾对40项进行了错误改造（丢失跨模态维度、GJB层虚构了7项不存在的标准条款、把跨文档校验改成单文档内校验），已全部删除：

- `knowledge/consistency_taxonomy_v2.json` → 已被 **taxonomy v3** 替代
- `knowledge/inconsistency_rules.json` → 旧规则库，与原文不符
- `docs/srs_project/14_strict_40_design.md` / `14_strict_40_items_design.md` → 注入设计，基于错误分类
- `docs/srs_project/13_alignment_analysis.md` / `13_dataset_synthesis_progress.md` → 对齐分析，基于错误基准

## 2. 当前taxonomy（v3）

- 文件：`knowledge/consistency_taxonomy_v3.json`
- 内容：40项，每项包含：
  - `original_example`：实施方案文档的原始示例（逐字引用）
  - `cross_modal_pair`：该项校验的跨模态对象（如「文本术语 vs 框图术语」）
  - `doc04_evidence`：04号SRS中的实际证据形态（具体block/表）
  - `qa_coverage`：91条QA对中触及该项的instance_id列表
  - `doc04_violations`：深读04号SRS发现的**真实不一致**（17个）
  - `note`：该项在04号上是否适用（7项零证据不适用）

### 04号SRS上的真实不一致清单（17个，全部来自深读）

| 类别 | 违例 | 相关项 | block |
|---|---|---|---|
| 标识符 | 连接池配置/初始化同ID | TERM-07 | b220/225 |
| 标识符 | 数据库关闭ID跨位置矛盾 | TERM-07 | b057/040 |
| 标识符 | 表48前缀SJTBGX vs 节标题SJTYFW | TERM-07 | b267/268 |
| 标识符 | 表53组件顺序颠倒 | TERM-07 | b285/286 |
| 标识符 | 表23 BLOB子项ID缺段 | TERM-07 | b139/140 |
| 枚举 | 3.2.1文本5项 vs 表3仅4行 | TERM-03 | b032/b035 |
| 枚举 | 「缓存修改」vs「缓存更新」 | TERM-03 | b181/b184 |
| 枚举 | 1.2两套分类法 vs 3.2六项分类 | TERM-03 | b011/b024 |
| 枚举 | 表9「平版」错别字 | LOGIC-05 | b067/087 |
| 追溯 | 表81/82正逆追踪矛盾 | GJB-05 | b407/408 |
| 追溯 | 追踪锚点失效(3.2.1.7不存在) | GJB-05 | b407 |
| 追溯 | 同行矛盾(映射非空+说明不追踪) | GJB-05 | b407 |
| 异常流 | E1内容与用例主题错位 | LOGIC-02 | b192/222/227 |
| 异常流 | 申请/释放句柄错误归属 | LOGIC-02 | b237/242 |
| 文档名 | 误写「数据同步共享服务」 | TERM-05 | b348 |
| 功能 | 1.2声称审计日志但3.2无对应 | GJB-04 | b011 |
| 合格性 | 表80覆盖缺口(3.3~3.17无方法) | GJB-06 | b404 |

### 91条QA与40项的映射统计

```text
LOGIC-02 异常处置 → 16条QA触及（R样本最集中区）
LOGIC-03 事件时序 → 14条QA
TERM-03 枚举集合 → 9条QA
TERM-07 接口标识 → 5条QA
前置条件 → 7条QA
参数/接口 → 15条QA
状态/设备 → 6条QA
```

## 3. 04号SRS文档结构（411块）

| 内容类型 | 块数 | 具体形态 | 可校验面 |
|---|---|---|---|
| 正文 | 235 | 章节描述、「包括」枚举句 | 文本枚举↔表成员比对 |
| 能力表 | 10张 | 表2/3/4/9/13/23/27/32/36/39/45/48 | ID+需求描述+方式+运行状态+任务书映射 |
| 用例表 | ~30张 | 表5~47（Use Case名称/Actors/前置/主事件流/异常流E1/后置） | E1模板+步骤编号+字段比对 |
| 接口表 | ~16张 | 表48~61（外部4+内部8+数据元素） | 接口ID双登记+数据特征 |
| 数据表 | 6张 | 表63~67（min/max/精度/单位） | 值域区间判定 |
| 追溯表 | 2张 | 表81正向+表82逆向 | 双向join+矛盾检测 |
| 合格性表 | 1张 | 表80（6行） | 覆盖完备性 |
| 质量/安全/保密 | 3张 | 表73/68/69 | 封闭清单成员检查 |
| 环境/交付/优先级 | 3张 | 表70/71、78、79 | 硬件跨表+优先级 |
| 图片 | 48张 | 功能框图(图1)+用例图(图2-47)+接口图(图48) | 跨模态（需VLM前置解析） |

## 4. 40项在04号上的适用性

| 适用性 | 项数 | 项 |
|---|---|---|
| 有丰富证据 | 14 | TERM-01/02/03/04/06/07/08, LOGIC-01/02/03/04/05/08/11 |
| 有稀缺证据 | 7 | PARAM-01/05/06/07/10, LOGIC-09/10 |
| 零证据（不适用） | 7 | PARAM-02/03/04/08/09, LOGIC-06/07 |
| 有无检查（GJB） | 11 | GJB-01~11（全部可做封闭清单有无比对） |
| GJB缺失真实样本 | 3 | GJB-04/08/10（审计/掉电/升级条款完全缺失） |

## 5. 当前架构组件

```text
已建（保留）:
  answer_structure.py      answer→原子claim+scope槽
  evidence_statements.py   evidence→字段级语句+行级ref
  qa_module.py             统一校验器（4通道+聚合+statement精确匹配）
  nli_local.py             本地NLI（mDeBERTa/Erlangshen）
  nli通道                  scope+槽位配对+阈值守卫（需校准）
  identifier通道           精确ID匹配（已抓到S1QA-084）
  54个变异算子             按五线路组织（L1值/L2集合/L3数值/L4结构/L5语义）
  /api/verify              服务API
  官方参考数据集            scene1_official_reference_v1.jsonl

待建:
  GJB"有无"专家             11项封闭清单成员检查
  E1模板专家                模板匹配+引用双向join
  序列专家                  编号提取+重排校验
  追踪表join专家            表81↔82双向
  证据门控                  每项先验探针（6零证据项拦截）
```

## 6. 数据与结果状态

| 资产 | 状态 |
|---|---|
| `scene1_official_reference_v1.jsonl` | 91行官方整合（Alpaca+证据+语句+silver） |
| silver标签 | GLM-5.3复核：S6/R8/N77（**非gold**） |
| 17个真实文档违例 | 04号深读发现（real_observed候选） |
| 6个baseline | B0/B2/B3已跑（全部坍缩NIE） |
| 当前方法评测 | acc 82.4%, macro-F1 0.432（确定性通道） |
| **M26评测矩阵（2026-10-27）** | B0-B5六基线+8消融+3对bootstrap：B4 acc **0.9011**/macro-F1 0.6997；cascade refute F1 **0.7143**@17次LLM调用（`runs/eval_paper_matrix_0fabaced_20261027_023711`、`runs/eval_cascade_1e92cdce_20261027_024429`） |
| **EGT合成数据+微调NLI** | v3叙事文法4500样本→egt_finetuned_v2：L2 refute召回0.375→**0.875**（`runs/build_egt_dataset_8a8716bb_20261027_003528`、`runs/train_residual_nli_acfead4b_20261027_013647`） |
| **L3 LLM残差通道** | 历史参照macro-F1 0.7799（`runs/eval_llm_residual_5dd69927_20261026_173434`，旧线性化）；同管线当日0.6997 |
| **M28诚实评测（2026-10-27晚）** | 冻结dev/test切分（29主题簇，dev45/test46）+test一次评测：修复后**test=0.8286/acc 0.9348**（refute P=1.0/F1=0.8571）；乐观偏差量化+0.0145（2%）；06号跨文档sound集gap det -0.486/cascade -0.188（`runs/eval_test_honest_6740ed5c_20261027_195753`、`runs/eval_crossdoc_27e8ce32_20261027_195859`） |

> 以上M26行的完整表格、数字核对记录与负结果集见 `docs/srs_project/49_cascadeverify_v2_results.md`。

## 7. 实施路线

| 阶段 | 目标 | 状态 |
|---|---|---|
| M-1 权威源锚定 | taxonomy v3+删除派生+project_guide | ✅ 本轮完成 |
| M0 方法架构重设计 | 五线路架构（L1值/L2集合/L3数值/L4结构/L5语义） | 设计完成 |
| M1 GJB有无专家 | 11项封闭清单检查 | ✅ M26实现（gjb_presence_expert.py） |
| M2 结构专家 | E1模板+序列+追踪join | ✅ M26实现（e1/sequence/trace_expert.py+entity_detector.py） |
| M3 NLI校准 | 阈值扫描+域微调 | ✅ M26实现（EGT合成+egt_finetuned_v2，gate=0.7） |
| M4 数据集构建 | 17真实违例+变异+标注 | ⬜ EGT合成已完成（4500样本）；17违例转化集+gold标注待做 |
| M5 评测+论文 | baseline矩阵+消融 | ✅ M26评测矩阵完成（B0-B5+8消融+bootstrap+级联五配置）；论文写作进行中 |

## 8. 文档导航

| 文档 | 状态/职责 |
|---|---|
| `docs/srs_project/49_cascadeverify_v2_results.md` | **M26-M28结果总览（论文数字唯一权威来源）**：架构/主表/消融/bootstrap/EGT演化/科研发现/审计响应与诚实评测（§10）/runs清单 |
| `docs/srs_project/50_support_recall_analysis.md` | support召回失败分析+P1三项修复落地结果（§7） |
| `docs/srs_project/93_scenario5_recall_paradigm_and_algorithm_design.md` | **场景五召回范式与算法设计**：question↔image↔chunk三层关联本质；方向A约束解析召回+方向B分解-接地-校验；P1/P2/P3路线 |
| `docs/srs_project/94_scenario5_dev_progress_template.md` | **场景五开发进度模板**：5阶段跟踪（数据集/QA生成/格式对齐/方向A开发/方向B调研），陈同学(上下文关联)+胡同学(一致性校验)填写区 |
| `knowledge/consistency_taxonomy_v3.json` | **当前taxonomy**（40项原始定义+04号证据+QA映射+17违例） |
| `docs/srs_project/45_official_reference_dataset.md` | 官方参考数据集规范 |
| `docs/srs_project/42_mutation_coverage_diagnosis.md` | 变异覆盖诊断（历史参考） |
| `docs/srs_project/implementation_doc_analysis.md` | 实施方案文档分析（历史参考，其中部分结论基于已删除的旧分类） |
| `docs/srs_project/40_method_reconstruction_plan.md` | 方法重构计划（历史参考，部分基于旧taxonomy） |
| `docs/srs_project/28_answer_evidence_task_reconstruction_plan.md` | 数据重构方案（历史参考） |

**项目优先事项**：实现级联架构三层（L0 NER检测→L1 符号验证→L2 残差NLI），每层检测到→报告→提前退出。

## 9. 级联验证架构（CascadeVerify）

### 9.1 三层设计

```text
Layer 0: Entity Detection (NER检测层)
  检测: answer中的实体/术语与证据是否一致
  项: TERM-01同义异名/TERM-02同名异义/TERM-05指令名称/
      TERM-07接口标识/TERM-08缩写代号
  检测到 → 报告{检测项ID+错误内容+证据位置} → 退出
  方法: GLiNER式NER + 文档内实体链接 + NIL决策(GenDecider式)

Layer 1: Symbolic Verification (符号验证层)
  检测: 结构化比对 + 国军标合规
  项: TERM-03枚举/TERM-04状态/TERM-06量纲/PARAM-01~10数值/
      LOGIC-01/02/03/05结构/GJB-01~11有无
  检测到 → 报告{规则ID+GJB标准OCR行号+证据单元格} → 退出
  方法: ID精确join + 集合运算 + 区间算术 + E1模板 +
        序列比对 + Chain-of-Table + Logic-LM(Z3) + GJB有无检查

Layer 2: Residual NLI (残差NLI层)
  检测: 剩余语义矛盾
  项: LOGIC-02残差/LOGIC-04流向/LOGIC-08仲裁/LOGIC-11重搜
  三态判定 → 报告{NLI概率+不确定度+人工复核建议}
  方法: 只在残差集R上训练的域适配NLI + conformal校准
  残差集定义: R = {claim对 | L0对齐成功 ∧ L1规则未触发 ∧ L1不可形式化}
```

### 9.2 每层退出输出

| 退出类型 | 触发条件 | 报告内容 | 可靠性 |
|---|---|---|---|
| 确定性退出 | L0/L1规则/Z3判定 | 规则ID+OCR行号+证据单元格+判定 | soundness保证 |
| 置信度退出 | L2 NLI校准概率超阈值 | NLI概率+不确定度+复核建议 | P(误报)≤α |
| 弃权 | L2不确定 | 路由人工审阅 | — |

### 9.3 算法创新点（论文贡献）

| # | 创新点 | 层 | 文献空白 |
|---|---|---|---|
| C1 | 残差NLI训练范式 | L2 | 层间可计算函数定义残差集+残差集专门微调 |
| C2 | GJB域Logic-LM管线 | L1 | 需求→Z3+可形式化边界显式刻画 |
| C3 | 文档内实体链接+NIL | L0 | 无外部KB的实体聚合+同名消歧 |
| C4 | 双模式退出+层级归因 | 层间 | 确定性/统计两档可靠性+退出报告设计 |
| C5 | 真实GJB数据集 | 评测 | 91条官方QA+17个真实违例 |

### 9.4 相关文献锚点

| 创新 | 核心引证 |
|---|---|
| 级联+提前退出 | FrugalGPT(2023), RouteLLM(ICLR'25), GPTScan(ICSE'24) |
| NLI只做残差 | MiniCheck(EMNLP'24), Setty(SIGIR'24), ContractNLI(EMNLP'21) |
| 实体链接前置 | BEAR-FACT(EACL'24), GenDecider(EMNLP'23), 定义增强(TACL) |
| 层级错误归因 | Factcheck-Bench(EMNLP'24), GREEN(EMNLP'24F), AVeriTeC(NeurIPS'23) |
| 神经符号混合 | Lemur(ICLR'24), Logic-LM(EMNLP'23F), ProgramFC(ACL'23) |
| 表格推理 | Chain-of-Table(ICLR'24), TART(NAACL'25), TabFormer(SIGIR'25) |
| 最近竞品 | SAGE(arXiv'26, 必须引用+差异化), TSRCDF-SS(arXiv'25, 纯语义基线) |

## 10. 里程碑记录

### M26（2026-10-26/27）：CascadeVerify v2全栈实现与评测

**范围**：把§9的三层级联设计从图纸变成全栈可评测系统，完成S1-S6全部实施步（对齐方法设计文档§6.8的实施顺序）。

**实现**（algorithms/consistency/新模块，均配测试）：
- DEQ证据管线（deq_pipeline.py）+ 证据线性化修复（evidence_statements.py：能力表列错位124/181表+thead误派发两个premise bug）
- L0/L1确定性专家族5个：entity_detector / e1_expert / sequence_expert / trace_expert / gjb_presence_expert
- EGT三态合成管线（egt_synthesis.py：v1近拷贝117→v2语句3000→v3叙事4500）
- L2 NLI残差（nli_residual.py+egt_finetuned_v2本地ckpt，gate=0.7）
- L3 LLM残差（llm_residual.py，llm_json缓存接口）+ L2→L3级联升级路由（use_cascade）+conformal档
- per-claim通道融合（fuse_per_claim）+ 跨claim聚合

**评测**（91QA vs GLM-5.3 silver，S6/R8/N77）：
- B0-B5六基线+8消融+3对bootstrap（`runs/eval_paper_matrix_0fabaced_20261027_023711`）
- 级联五配置含conformal两档（`runs/eval_cascade_1e92cdce_20261027_024429`）
- 头条数字：B4 acc 0.9011；cascade refute F1 0.7143（P 0.8333）仅17次LLM调用；EGT叙事文法把L2 refute召回从0.375拉到0.875

**科研发现**（按重要性）：EGT文法设计定律（dev≈0.97与真实迁移脱钩，叙事文法定召回）/ 两个premise bug及修复 / 级联经济学 / 负结果集（零样本NLI坍缩0.327、L2单独0.5437、conformal高置信档P≤0.33、fp16训练波动±0.05、silver边界模糊）/ per-claim融合放大器（-0.152消融）/ 068/074 claim级归因错位。

**详细结果、全部数字的run溯源与核对记录**：`docs/srs_project/49_cascadeverify_v2_results.md`（论文数字唯一权威来源）。

**遗留**：91条gold人工标注（最高优先级）、068/074 claim锚定闭合、v2代码git提交、论文写作。

**Wave 5进展（2026-10-27午，17真实违例驱动的专家补全收口）**：L1专家族5→7（新增`id_join_expert.py`/`enum_join_expert.py`两个跨位置join专家），17违例检出52.9%→**88.2%**（15/17，`runs/eval_violations_5d5c92a8_20261027_124733`），91QA确定性基线macro-F1 **0.6381**、cascade refute F1 0.800（论文矩阵全量重跑：`runs/eval_paper_matrix_c409df7f_20261027_125551`、`runs/eval_cascade_1e92cdce_20261027_124941`，数字以49号文档为准）。

### M27（2026-10-27晚）：Wave 6设计组件全量补全与稳健性诊断

**范围**：L1专家族补至设计§6.3全量9行（+`numeric_z3_expert.py`/`coverage_expert.py`），17违例检出**16/17（94.1%）**；完成设计§6.5的变异注入评测（robustness漏检率矩阵）与设计§6.4的学习路由器（C4学习半边）——后两者产出负结果/诊断性结果，如实报告。**算法侧（设计§6组件清单）至此全部完成**；剩余遗留=人工项（gold标注）、论文写作、可选VIO-15、代码提交。

**实现**（algorithms/consistency/新模块，均配测试）：
- `numeric_z3_expert.py`（600行+21测试）：量纲换算/区间三态Z3判定（PARAM-03/06/07）/跨参数聚合（PARAM-01/05）；SMT-LIB+unsat core完整输出协议（防scope laundering）；04号全文档92条数值事实、91QA冻结证据**0条**（证据构成发现：scene1 QA不含数值声明，PARAM类检测在该评测集结构性无对象）
- `coverage_expert.py`（693行+32测试）：合格性逐章覆盖+条款覆盖join（GJB-01/04/06）；**VIO-17闭合**（表80合格性仅覆盖3.2.1~3.2.6 vs answer声称3.1-3.17全覆盖）→违例集检出15/17→**16/17（94.1%）**（`runs/eval_violations_5d5c92a8_20261027_165400`）
- `router.py`+`build_router_dataset.py`+`eval_router.py`（23测试）：**学习路由器负结果**——91QA路由一致率0.0875（EGT监督学不出；EGT内样本0.8233），oracle上限**0.7867 macro-F1@2次调用** vs 固定级联0.7185@15次；三重归因=特征分布外推（EGT单claim短问句1.02/10/24.06 vs QA 5.01/20.64/218.34）/通道强度漂移（L2 EGT dev 0.9056 vs QA refute P 0.3684）/gold先验漂移（EGT均衡 vs QA 85% NIE）；严格防泄漏体制（qa实例零进训练+10条问题重叠行剔除）
- `build_mutation_injection_eval.py`+`eval_mutation_detection.py`（7测试）：48注册算子×91QA→**394条注入**，总检出率**10.4%**；族级GJB 25% > TERM 19.4% > BASE 9.4% > STRUCT 8.1% > LOGIC 5.5% > **PARAM 0%**（证据无数值事实）

**科研发现**：**证据侧双登记**（论文级）——真实违例=证据侧多处登记冲突（identifier 5/5、enumeration 4/4），answer侧单边注入破坏同通道近乎失明（0.526/1/24=0.042）→**符号层检出能力依赖证据侧冲突登记的存在=方向A上下文聚合的实证论据**（§6.7闭环的反方向一环）；学习路由负结果与零样本NLI坍缩、conformal不可信并列第三大负结果。

**零回归**：9专家栈91QA四配置与Wave 5定稿逐位一致（B3 0.9011/0.6381、cascade 0.7185@15；两新专家91QA零触发，`runs/eval_router_2b76c358_20261027_170640`核验）。

**runs**：`router_train_7a90549c_20261027_165644`、`eval_router_2b76c358_20261027_170640`、`eval_mutation_detection_750b7b7d_20261027_165008`、`eval_violations_5d5c92a8_20261027_165400`。

**详细结果、全部数字的run溯源与核对记录（verify脚本412项PASS）**：`docs/srs_project/49_cascadeverify_v2_results.md` §8（Wave 6章节）——论文数字唯一权威来源。

**遗留**：91条gold人工标注（最高优先级，人工项；claim级归因评测侧挂起于此）、论文写作、代码提交（HEAD停在ff0d4950）、可选VIO-15文档名通道（17违例唯一未检出）。

### M28（2026-10-27晚）：审计响应收口——切分/诚实数字/三项修复/跨文档gap

**范围**：对49号文档全部声明做可信度审计→P0/P1修复→诚实数字的完整链条落地，把评测效度（dev-on-test、跨文档零验证、silver非gold、support召回）从审计发现变成已量化/已修复/已排期三类状态。**审计-响应对照表终版见 `49_cascadeverify_v2_results.md` §10.4（八项）。**

**落地**（全部runs协议落盘，git_sha=ff0d4950）：

- **持久切分与诚实评测（P0-1）**：`data/gjb_438c/qa_frozen/dev_test_split_v1.json`（`tools/build_dev_test_split.py`，seed=42，29功能主题簇整簇原子分配，dev=45[S3/R4/N38]/test=46[S3/R4/N39]，同主题零跨侧）；dev扫参60配置只在冻结dev上（`tools/calibrate_on_dev.py`，阈值空间被压平——60配置仅3个macro-F1值）；test一次评测（`tools/eval_test_honest.py`）。**修复前test=0.704 vs legacy全91自评0.7185——乐观偏差仅+0.0145（2%）；修复后test=0.8286/acc 0.9348**（refute P=1.0/F1=0.8571）；dev调参在test零分歧。口径警告：修复后run的`optimistic_bias=-0.1101`是"legacy（旧代码自评）−test（新代码）"混合口径（含代码改进），非纯乐观偏差。
- **P1三项确定性修复**（失败分析=`50_support_recall_analysis.md`）：①融合键剥离编号前缀（qa_module）②序列专家适用性门（sequence_expert）③id_join精确绑定+TERM-07护栏（id_join/entity_detector）——**support召回2/6→5/6**（053/066/069翻正，077留P2证据投递缺口）；全91确定性0.9011/0.6381→**0.9121/0.7212**；**违例集16/17零回退**（定位gold 24→23，VIO-03第二锚点，机制已注明）；dev侧B4=0.8875。诚实声明：诊断用了全91失败分析（含test侧053/066），oracle验证零副作用——test数字纯净度有此折扣。
- **跨文档泛化（P1）**：06号30条**构造性sound标签**评测集（S/R/N各10，`crossdoc06_evalset_v1.jsonl`，label_proof逐条可溯，零LLM silver）；**deterministic 0.1524 vs 04号0.6381（Δ=-0.486）、cascade 0.5309 vs 0.7185（Δ=-0.188）**。四条失效归因（answer文法不迁移/numeric_z3跨行伪refute/identifier在场即support假设失效/cascade保留L1终态误判）；P1修复对06号零改善（修复前后两run逐位一致）——**泛化缺口是正则文法层的结构性问题，升级路线=语义匹配（P2）**。
- **gold标注工作台（响应"silver非gold"）**：`build_annotation_sheet.py`→`collect_gold_annotation.py`→`finalize_gold.py`三工具链（108实例/525 claim预填+TSV+校验+双人κ+gold_v1导出；速查手册`gold_annotation_sheet_v1.md`，协议48号）——**待人工标注（估6-9小时）**。

**runs**：`calibrate_on_dev_a069227d_20261027_185110`、`eval_test_honest_6740ed5c_20261027_185819/195753`、`eval_qa_module_silver_f119425e_20261027_190326/195515`、`eval_qa_dev_split_6d4e96bb_20261027_195532`、`eval_violations_5d5c92a8_20261027_195407/195501`、`eval_crossdoc_27e8ce32_20261027_190259/195859`、`build_crossdoc_evalset_1a7c8719_20261027_190350`。

**详细数字、口径声明与审计-响应对照表（verify脚本583项PASS，含Wave 7新增171项核对）**：`49_cascadeverify_v2_results.md` §10（Wave 7章节）；修复逐claim机制=`50_support_recall_analysis.md` §7。

**遗留**：gold人工标注（工作台已建，待人工6-9h，最高优先级人工项）、077 L3证据投递（P2）、跨文档正则文法升级=语义匹配（P2）、论文写作、代码提交（HEAD停在ff0d4950）。

### M36（2026-10-28）：L1规则层深挖审计+numeric跨行伪refute修复+三暂缓项配置迁移+67号详解文档

**范围**：对L1规则模板层（rulepack+九专家）做逐文件深挖审计（对标66号NER文档工作方式），修复M28跨文档四失效归因中的**numeric_z3跨行伪refute**（C06QA-008），完成64号盘点的三个暂缓项（CV-01/NZ-01/GJ-02）配置迁移，产出67号规则层详解文档。

**修复（行为变化，有意）**：numeric_z3字段类join键——数据表同一数据项的最大值/最小值/精度是三个不同的量，字段式事实携带量纲类（max/min/precision），answer主体的字段限定词（"X的最大值为200"→核心主体+类max）同样解析并按类过滤join。修复前answer的eq声明与"精度：1"行误join→UNSAT伪refute。**C06QA-008（伪refute→support）与C06QA-018（NIE→refute，证据自身UNSAT曾掩蔽矛盾）双双翻正**；跨文档det macro-F1 **0.1524→0.2619**、cascade **0.5309→0.6052**（`runs/eval_crossdoc_3c602510_20261028_180422`）；91QA numeric_z3零触发（0条数值声明）故91QA/违例零影响。

**三暂缓项迁移（行为保持，程序化提取逐字一致）**：coverage词表（_QUALIFICATION_TARGETS/_GENERIC_SUBJECTS/_ALARM_ELEMENTS+共享_ABSENCE_RE——解耦gjb_presence词表import）/numeric词典（_CN_UNIT_ALIASES/_EXTRA_UNIT_FACTORS/_FIELD_NAME_OPS/_AGGREGATE_MARKERS）/GJB簇映射（RULE_CLUSTERS→pack的gjb.rule_clusters段，11簇20引用带理由）。**配置化覆盖度60项中48→58项（≈97%）**。行为保持验证：91QA **0.9121/0.7212**（`runs/eval_qa_module_silver_f119425e_20261028_180400`）、违例**16/17**（`runs/eval_violations_5d5c92a8_20261028_180406`）逐位不变。

**审计要点（仅记录未修）**：evidence_statements表型启发式与pack签名重复（线性化层不吃配置）；gjb_presence(25词)与gjb_rule_engine(21词)presence词表双版本（行为保持的历史校准结果，已双双显式外置可审计）；GJB-04簇以安全保密簇承载（438C无审计专项规则）。

**文档**：`docs/srs_project/67_rule_layer_architecture.md`（管线四阶段/注册表思想/六检查族真实走查/GJB引擎编译链55+32诚实覆盖率/配置引擎边界/代价账含双登记定律/演进路径）；64号§7完成度表同步回填。

**测试**：rulepack/coverage/numeric_z3/gjb_rule_engine/e1/qa_consistency_module 154 passed+相关面152 passed；ruff零报错。

### M130（2026-11-24）：多agent调研-验证-执行闭环（M116-M129综合条目）

> 注：M37-M121的逐里程碑记录散见于各commit message与docs/srs_project/95-108号
> 文档，本条目只收口本轮（三文献调研+代码库审计+七agent并行执行）。

**范围**：回答"如何提升可解释性/性能/减少嵌入正则"——三份文献调研
（95 claim算法/96可解释NLI/97正则替代）+代码库侧正则审计（98号：401个
调用点四类分级）+统一行动方案（99号四阶段）+七agent并行实施与逐一验收。

**验收结论（全部独立复核：测试亲自跑+数字从runs核对+预先存在失败经
干净HEAD worktree取证）**：
- **A·测量基建（M122）**：E1 citation P/R（expert macroP 0.8021/R 0.8792，
  字面忠实0.5652损失集中于两通道合成claim_text；学生copy精度0/4）+
  E2消融四条件（b翻转0.8125、c定位稳定0.647最弱、d=1.0）——Phase 2
  验收基线锁定，六系统弱点入册
- **B·P1桥接（M123）**：**0.8047未达标**（0.7496，桥接仅3条typed claim
  可对齐）→**两层粒度契约发现**（字段层：识别胜利区域与typed字段区域
  不相交，ID span覆盖0.0；命题层：NLI能entail整句不能entail原子）——
  Alignment Bottleneck定律的域内精确化，可发表；修复在训练目标→P1-v2
  重定向（103号：蒸馏A_regex分解行为，G已产标签identifier覆盖1.0）
- **C·Eiter回路（M128）**：**"归纳规则≥人工规则"达标**——教师pack
  0.407 vs 人工0.1481（vs generic 0.2619），91QA零回退逐位；三迭代
  反馈通道消融（v1幻觉/v2诊断对旋钮错/v3超oracle）；6条方法学负面
  发现（lru_cache pack污染/doc06_v1陈旧性/反馈保真度第一/诊断≠旋钮/
  L1协议禁support输出=R2根源/并发编辑中断）
- **D·E5数据（M126+M127）**：质量闸门（505条union，14机械拦截，教师
  评分区分度弱如实报告）+286最小变更对+合并v4训练集（1622行，
  support 20.5%→34.5%）——Step 3重训数据就绪
- **M129 pack身份缓存修复**：_unit_table/极性正则的身份追踪（单pack
  行为逐位一致45测试，路由失败经worktree取证为M104族预先存在）

**执行中的下一格**：X1约束解码（E，parse_fail基线+trie LogitsProcessor
102号规格）、E7表驱动外置（F，29契约测试+行为等价双证）、P1-v2标签
（G，812实例，字段覆盖0.0→1.0）。GPU释放后：D3重训（M127数据）+
切分器v3重训（103号）；F完成后：R2接地概率化。

**文档**：95/96/97调研+98审计+99方案+100(E5)/102(X1)/103(P1v2)规格+
101实验效度发现+104 Eiter报告（原100号重命名）。

**测试**：本轮新增26+19+49+20+3+4=121个测试全绿；ruff零报错。

## 11. 场景5确立架构（受控内容）

> ⚠️ **受控声明**：本节内容为用户确立的场景5技术架构，**未经用户批准不得修改、不得向本节添加任何其他内容**。日常分析/调研/临时笔记一律放 `temp/`（已gitignore），不进本文件。场景5交接细节见79号文档，本节只固化架构本身。

**确立日期**：2026-10-30 | **确立人**：用户 | **上下文**：场景5(科研生产现场智能监管)图片-QA违规告警一致性校验

### 11.1 三角色架构（原文确立）

```
特征提取   = 检测→跟踪→属性→动作的CV栈（不是VLM）
             产出: 个体轨迹{person_id, 属性序列, 动作段, 空间位移}
上下文关联 = 同camera内跨帧个体关联（tracklet）——"同一个人"就是关联主键
一致性校验 = 轨迹属性/动作段 vs QA evidence/answer vs 判定标准块编译的规则
```

### 11.2 架构蕴含的关键决策（与三角色一体确立）

| 决策 | 内容 |
|---|---|
| 不用VLM做感知 | 图片侧证据由专用CV管线（检测+跟踪+属性+动作）生产，本地GPU可跑、输出结构化；VLM降级为抽检/仲裁位 |
| 上下文=时序个体连续性 | 场景5本质是视频抽帧，方向A的聚合单元=个体tracklet（行为类）+ 场景单元(camera,时间窗)（区域类），双粒度互补 |
| 时序谓词可计算化 | 睡岗="长时间静止"从自然语言约束变为轨迹谓词（位移方差<阈值持续N帧）——判定标准块编译目标扩展到时序谓词查询 |
| 范式同构 | 个体注册表=(主体=person_id, 值=属性/动作/等级, 位置=时间段)——与场景1(主体,值,章节位置)同构，方向B join/聚合全套平移 |
| 四态语义 | support/refute/NIE + 可疑——轨迹内属性翻转（ID漂移）、跨样本冲突不判refute，送人工仲裁 |

### 11.3 已识别的约束与坑（不可遗忘）

1. **当前672条样例无帧序列**：32张图是增广变体（night/fog/strong_light/flip），非时间连续帧——tracklet方案需外部时序数据集（调研进行中）
2. 增广变体≠时序近邻，不得混入平滑性检测
3. 第一版限定同camera跟踪；跨camera Re-ID不做（公认难题）
4. 跟踪ID切换→轨迹内属性假翻转→必须走"可疑"态兜底
5. 隐患等级必须由判定标准块编译的规则引擎推导，不得用另一模型输出当标准

### 11.4 场景5的9个安全校验场景（用户确认 2026-11-17）

| # | 场景 | 视觉检测目标 | 主要校验项 | 静态图可判性 |
|---|---|---|---|---|
| S1 | 安全帽佩戴 | 头部是否有安全帽（hardhat/no-hardhat） | B1/B2/B4/B5/B6 | 可判（PPE检测） |
| S2 | 人员倾倒 | 人员姿态（倒地/跌倒/倾斜） | B3/D2 | 可判（姿态代理）；摔倒事件需时序→NIE |
| S3 | 防静电服穿戴 | 服装颜色/类型识别 | B1/B3/B6 | 可判（需域内标注） |
| S4 | 口罩佩戴 | 面部口罩检测 | B1/B4/B6 | 可判（需域内标注） |
| S5 | 人员睡岗 | 姿态（趴伏/长时间静止） | B3/D2 | 趴伏可判；"长时间"单图NIE |
| S6 | 抽烟检测 | 手部/面部烟头检测 | B1/B2/B5 | 可判（需域内标注） |
| S7 | 接打电话 | 手持手机/耳边动作 | B1/B3/B5 | 可判（需域内标注） |
| S8 | 通道占用 | 区域内物体/人员占用 | B4/B5/B7/B8 | 可判（需ROI标注） |
| S9 | 定员检测 | 区域内人员数量 | B7计数 | 可判（检测计数） |

> 以上9个场景对应实施文档的需求1（段[12]），是QA问答对生成的业务背景。每个场景共享同一套特征提取管线（T0-T11），差异在检测模型的类别和判定标准块的内容。

### 11.5 工作区与产物纪律

- 场景5开发隔离于 `scenario5/`（data/数据集落点·gitignored，cv_stack/管线代码，tools/脚本）
- 日常md→`temp/`；确立性结论→经用户批准后进本节
