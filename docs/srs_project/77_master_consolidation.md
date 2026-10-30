# CascadeVerify 项目总汇——所有相关信息一页化

> 定稿日期: 2026-10-30 | 提交链: M28→M43 (git: f1060cf6)
> 数字口径: 2026-10-30同批实测; 评测命令与runs见§8
> 用途: 论文写作的唯一权威参考 / 新人接手的完整入口 / 汇报材料底稿

---

## 目录

1. [评测表格定稿（论文主表）](#1-评测表格定稿)
2. [架构总览](#2-架构总览)
3. [科研贡献与实证定律](#3-科研贡献与实证定律)
4. [数据集与基准资产](#4-数据集与基准资产)
5. [Baseline与运行环境](#5-baseline与运行环境)
6. [关键数字速查](#6-关键数字速查)
7. [延迟与成本](#7-延迟与成本)
8. [复现命令与runs索引](#8-复现命令与runs索引)
9. [代码资产索引](#9-代码资产索引)
10. [文档体系索引](#10-文档体系索引)
11. [里程碑时间线](#11-里程碑时间线)
12. [诚实边界与遗留项](#12-诚实边界与遗留项)
13. [场景5前瞻](#13-场景5前瞻)

---

## 1. 评测表格定稿

### 数据集

**自建（上下文关联）**：16份真实GJB 438C军用SRS，构建"表格深度检索"（438查询×1,207表格）与"软件图片"（899查询×379图）两个场景。

**自建（一致性校验）**：16份真实GJB 438C军用SRS，构建三个场景——"答案一致性校验"（91查询×574证据块，真实QA+silver三态标签）、"跨文档泛化"（05/06/07/08/10五文档×30查询，构造性sound标签）、"真实违例检测"（17条人工深读违例×构造断言QA）。

**公开基准**：XNLI-zh（Conneau et al., EMNLP 2018，2,000查询）；OCNLI（Hu et al., EMNLP 2020，2,950查询全量）；CMNLI-test（CLUE家族，2,000查询）；WTQ/FeTaQA/DuRetrieval（表1用）。

### 表1 证据召回 R@1 对比（上下文关联部分）

| 方法 | 自建-表格深度检索 | 自建-软件图片 | WTQ | FeTaQA | DuRetrieval |
|---|---|---|---|---|---|
| BM25-doc | 0.183 | 0.685 | 0.282 | 0.706 | 0.836 |
| BM25-unit | 0.158 | 0.543 | 0.277 | 0.788 | 0.744 |
| BGE-dense | 0.078 | 0.660 | 0.333 | 0.836 | 0.879 |
| LightRAG-dense | 0.144 | 0.596 | 0.334 | 0.883 | 0.865 |
| Ours | **0.486** | 0.642 | **0.464** | 0.860 | **0.954** |

### 表2 答案一致性校验 macro-F1 对比

| 方法 | XNLI-zh | OCNLI | CMNLI-test | 自建-91QA | 自建-跨文档×5 |
|---|---|---|---|---|---|
| BGE三元中心 | 0.538 | 0.500 | 0.511 | 0.117 | 0.348 |
| Erlangshen-330M零样本 | 0.798 | 0.792 | 0.826 | 0.415 | 0.380 |
| mDeBERTa零样本 | 0.793 | 0.723 | 0.848 | 0.295 | 0.485 |
| CMNLI微调mDeBERTa | **0.810** | 0.728 | **0.867** | 0.276 | 0.596 |
| GLM-5直推 | 0.761 | **0.827** | 0.770 | 0.611 | **0.888** |
| Ours-L2(EGT域适配) | 0.750 | 0.694 | 0.798 | 0.297 | 0.468 |
| **Ours级联** | — | — | — | **0.786** | 0.597 |

注: 级联为文档级架构(L0-L3)，语句级公开NLI列标"—"；91QA held-out测试集(46条)上Ours级联=0.829。

### 表3 真实违例检测与成本对比

| 方法 | 自建-17真实违例 | 91QA-refute精确率 | LLM调用(91QA) |
|---|---|---|---|
| B3确定性规则 | **0.941** (16/17) | 1.000 | 0 |
| GLM-5直推 | 0.118 (2/17, 12假support) | 0.714 | 91 |
| B4全配置(无路由) | — | 0.778 | 83 |
| **Ours级联** | **0.941** (16/17) | **1.000** | **15** |

### 三组核心对照实验

| 对照 | 结论 |
|---|---|
| CMNLI微调 vs Ours-L2 | 公开监督数据公开列赢(0.810/0.867)、域列崩(0.276, refute F1=0.0)——**公开数据≠域数据，域适配必须EGT构造性合成** |
| GLM-5: 跨文档×5 vs 17违例 | 构造型0.888 vs 真实违例0.118——**LLM直读胜任干净单侧声明、崩溃于跨位置双登记矛盾——方法辖区划分的核心实证** |
| B3(0调用) vs 级联(15) vs B4(83) | refute精确率1.000/1.000/0.778——**级联是成本-质量Pareto点(18%成本最优refute F1=0.857)** |

### 内部消融（10项，基于91QA）

per-claim融合 **-0.152**（单一最大组件）| L3残差 -0.088 | E1专家 -0.039 | enum_join -0.026 | all_experts -0.017 | 其余中性 | DEQ on +0.007

### 统计显著性（1000次paired bootstrap, seed=42）

B4 vs B3: +0.154 [-0.020, +0.343] p=0.076 | B4 vs B5: +0.166 [+0.067, +0.307] p<0.001 | B4 vs B2: +0.264 p=0.002 | B4 vs no_join: +0.027 p=0.666

---

## 2. 架构总览

```
输入 (Question, Answer, 冻结证据E)
  ↓
L0 NER实体层 —— 检测术语类(TERM-01/02/05/07/08)
  词典gazetteer链路: 配置词典(15字段schema)+jieba(HMM=False预置通路)+运行时文档词典归纳
  场景迁移=换config/ner_lexicons/<scene>.json
  ↓ 残差
L1 符号规则层 —— 检测参数+逻辑+合规类(PARAM/LOGIC/GJB)
  机制: 证据线性化→(主体,值,位置)注册表→跨位置join裁决
  九专家: ID join/枚举join/E1模板/序列对齐/追踪/覆盖/GJB规则引擎/Z3数值/实体
  GJB规则引擎: 120条标准规则→编译55条可执行检查(rule_id+标准章节锚可追溯)
  场景迁移=换config/rulepacks/<scene>.json; 配置化覆盖58/60项(97%)
  ↓ 残差(C1原则: 已决不下沉)
L2 NLI语义层 —— 检测其余语义型
  mDeBERTa + EGT三态合成训练(4500样本, 叙事文法)
  ↓ refute候选实例级升级
L3 LLM仲裁(工程旁路) —— glm-5.3(缓存), 15次调用=18%成本
  ↓
per-claim融合(同claim: refute>support>NIE) + 实例聚合(任一R→R|全S→S|否则NIE)
  ↓
输出: 三态verdict + 证据定位(块/行/span) + 检测项ID + justification
```

**对外封装**: `CascadeVerifier(preset, scene).verify(question, answer, evidence)` → VerdictResult
- preset: fast(8ms/条,零模型) / standard(+L2, 120ms) / full(+L3级联)
- scene: srs_scene1 / doc01 / doc06 / ... (onboarding生成)

**配置化主张**: 接入新GJB文档 = 一条命令(`onboard_new_document.py --doc NN`)自动归纳表头签名/ID族/值域→生成两份配置→审计跑通（01号演示端到端0.3秒）。

---

## 3. 科研贡献与实证定律

### 五条论文贡献

| # | 贡献 | 证据 |
|---|---|---|
| C1 | EGT三态构造性合成范式（首个三态分离；MiniCheck/Auto-GDA/FISCAL全二元） | refute召回0.375→0.875 |
| C2 | 残差NLI域适配（Auto-GDA配方在军标域实例+负结果+级联修复） | L2召回0.875, 精确0.37→级联1.000 |
| C3 | E1异常流模板专家（用例表异常流一致性检测，2023-2025文献空白） | 消融-0.039 |
| C4 | 异构验证器级联路由（FrugalGPT范式推广+固定策略有效+学习路由负结果） | 18%成本最优refute F1 |
| C5 | GJB-SRS基准（16文档+91QA+17违例+40项taxonomy+54算子+150条跨文档sound集） | 全部runs可复现 |

### 三条实证定律

| 定律 | 内容 | 实验证据 |
|---|---|---|
| ①双登记定律 | 证据侧双登记冲突join可裁决(1.0)；answer侧单边破坏0.05-0.53；LLM直推违例2/17 | 394注入对照+GLM-5违例崩溃 |
| ②文法定律 | 合成claim形态分布与标签sound性同等重要 | v1近拷贝dev0.965/真实0.50 vs v2叙事0.875 |
| ③路由空间 | oracle路由0.787@2次调用存在，但EGT监督学不出(一致率0.0875)——需域内路由监督 | 三重归因: 特征外推/通道漂移/先验漂移 |

### 六条诚实负结果

零样本NLI坍缩(0.327) | EGT-v1迁移失败(0.50) | 学习路由(0.0875) | conformal两档(P=0.29) | fp16训练波动(±0.05) | silver边界模糊(GLM自不自洽)

### 其他关键机制发现

- **per-claim融合放大器**: 弱通道NIE不否决同claim强通道support——消融-0.152为单一最大组件
- **两个premise级bug修复**: 能力表空序号列错位(124/181表受影响)+thead误派发
- **dev-on-test偏差仅2%**: 29主题簇冻结切分量化(0.719自评vs 0.704 held-out)
- **乐观偏差口径**: legacy 0.7185(旧代码全91) - test 0.8286(新代码held-out)含代码改进

---

## 4. 数据集与基准资产

| 资产 | 规模 | 位置 |
|---|---|---|
| 16份GJB SRS(MinerU解析) | 5,423块 | data/gjb_438c/mineru_standard/ |
| 91官方QA(冻结) | 91查询×574证据块 | data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl |
| silver标签 | S=6/R=8/N=77 | data/gjb_438c/runs/review_qa_with_glm53_*/final_labels.jsonl |
| dev/test持久切分 | 29簇, dev45/test46 | data/gjb_438c/qa_frozen/dev_test_split_v1.json |
| 17真实违例评测集 | 17条×90证据块 | data/gjb_438c/localization_gold/violation_evalset_v1.jsonl |
| 跨文档×5 sound集 | 150条(S/R/N各50) | data/gjb_438c/qa_frozen/crossdoc5_evalset_v1.jsonl |
| 变异注入集 | 394条×48算子 | data/gjb_438c/mutation_injection_evalset_v1.jsonl |
| EGT训练集v2 | 4,500样本(叙事文法) | runs/build_egt_dataset_8a8716bb_*/ |
| GJB规则库 | 120条(87条适用SRS) | knowledge/gjb_438c_rules_full.json |
| taxonomy v3 | 40项检测体系 | knowledge/consistency_taxonomy_v3.json |
| 定位gold工作台 | 108实例/525claim预标注 | data/gjb_438c/localization_gold/ |
| 公开NLI测试 | XNLI-zh/OCNLI/CMNLI | data/gjb_438c/public_nli/ |

---

## 5. Baseline与运行环境

| Baseline | 实现 | 说明 |
|---|---|---|
| BGE三元中心 | bge-large-zh(本地) | fit池=OCNLI2000+CMNLI3000, 零泄漏校验 |
| Erlangshen-330M | models/nli/(本地) | 中文NLI代表, 零样本 |
| mDeBERTa零样本 | models/nli/(本地) | 多语言NLI, 零样本 |
| CMNLI微调 | 50k训练+28min GPU | 公开监督代表, dev 0.823 |
| GLM-5直推 | llm_json(cache=True) | glm-5.3, 928次API全缓存 |
| B0/B3/B4/B5/L2 | 内部配置 | 消融与架构组件 |

运行环境: Windows, Python 3.12(Anaconda), RTX 4060 8GB, torch 2.11+cu128, jieba 0.42.1(HMM=False)

---

## 6. 关键数字速查

| 指标 | 数值 | 口径 |
|---|---|---|
| 91QA acc / macro-F1(确定性B3) | 0.9121 / 0.7212 | silver, 零LLM |
| 91QA macro-F1(级联) | 0.786 (refute F1 0.857, P=1.000) | 15次LLM |
| 91QA macro-F1(B4上限) | 0.875 | 83次LLM |
| held-out test(46条) | 0.829, refute P=1.0 | 冻结切分终评 |
| 17真实违例 | 16/17 (94.1%) | B3与级联同 |
| GLM-5违例检出 | 2/17 (12假support) | 直推对照 |
| 跨文档×5(级联/GLM-5) | 0.597 / 0.888 | sound标签 |
| 变异注入总检出 | 6.1% (24/394) | answer侧单边破坏 |
| EGT R样本sound性 | 0.932 | 模块复判 |
| 支持召回 | 5/6 (仅S1QA-077遗留) | 机制口径 |
| 40项检测体系 | TERM8+PARAM10+LOGIC11+GJB11 | taxonomy v3 |

---

## 7. 延迟与成本

| 配置 | 逐条延迟 | 一次性成本 | 吞吐 |
|---|---|---|---|
| fast(L0+L1) | 均值7.8ms / p95 12.4ms | import预热1.6s | ~128条/秒 |
| standard(+L2) | 均值119ms / p95 263ms | 模型加载35s | ~8.4条/秒 |
| full级联(LLM缓存) | 均值115ms | 同上 | — |
| full级联(真实API) | ~650ms均摊(16/91条升级×~3s) | — | — |
| 新文档onboarding | 全文档端到端0.3s | — | 01号实测 |

级联经济学: 90%的claim在免费层8ms解决, LLM只花在16%需仲裁的实例上。

---

## 8. 复现命令与runs索引

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'
python tools/eval_qa_module_vs_silver.py          # 91QA主评测
python tools/eval_paper_matrix.py                 # B0-B5+消融+bootstrap
python tools/eval_cascade.py                      # 五配置级联
python tools/eval_test_honest.py                  # held-out诚实评测
python tools/eval_violations.py                   # 17违例
python tools/eval_crossdoc5.py                    # 跨文档×5
python tools/eval_public_matrix.py                # 公开基准5方法
python tools/eval_mutation_detection.py           # 变异注入矩阵
python tools/benchmark_latency.py                 # 延迟基准
python tools/onboard_new_document.py --doc 01     # 新文档接入
python tools/demo_verifier.py                     # facade演示
python tools/make_paper_figures.py                # 论文图(6张)
python tools/make_paper_tables.py                 # 论文表(LaTeX)
```

关键runs: eval_paper_matrix_c409df7f_20261030 | eval_cascade_1e92cdce_20261030 | eval_public_matrix_921b0139_20261030 | eval_crossdoc5_e020b13f_20261030 | eval_test_honest_6740ed5c | eval_violations_5d5c92a8 | build_egt_dataset_8a8716bb | train_cmnli_nli(28min)

全部测试: **1460+ passed**; ruff: algorithms零报错。

---

## 9. 代码资产索引

```
algorithms/consistency/
  verifier.py            CascadeVerifier facade(fast/standard/full × 场景)
  qa_module.py           L0-L3编排+融合+级联(683行)
  answer_claims.py       claim抽取 | claim_channels.py 五通道
  ner_lexicon.py         L0词典schema(15字段)+jieba通路
  entity_detector.py     L0实体层(TERM五项)
  rulepack.py            L1规则包引擎(58/60项配置化)
  evidence_compiler.py   表格schema+聚焦视图 | evidence_statements.py 线性化
  id_join/enum_join/e1/sequence/trace/coverage/gjb_presence/gjb_rule_engine
  numeric_z3_expert.py   Z3+unsat core
  egt_synthesis.py       EGT三态合成 | nli_training.py | nli_residual.py
  llm_residual.py        L3通道 | public_baselines.py 公开baseline
  eval_lib.py            评测共享库 | onboarding.py 新文档归纳
config/ner_lexicons/     场景词典(4个) | config/rulepacks/ 规则包(7个)
server/main.py           FastAPI(已收编facade)
tests/                   1460+测试
```

---

## 10. 文档体系索引

| 文档 | 内容 |
|---|---|
| 本文(77号) | 总汇一页化 |
| 49号 | 实验结果总览(583数字核对) |
| 65号 | 技术架构文档(分层/选型/ADR) |
| 66号 | NER层详解 | 67号 | 规则层详解 |
| 64号 | rulepack设计(60项盘点) | 74号 | 规则库构建指南 |
| 50号 | support分析 | 75/76号 | 场景5分析与需求深拆 |
| paper/cascadeverify_main_v1.md | 论文骨架(7章) |
| paper/evaluation_tables.md | 评测表v2 | paper/figures/ 6图 | paper/tables.tex 9表 |
| project_guide.md | 项目黄金文档(v10, M28-M43) |

---

## 11. 里程碑时间线

| 提交 | 内容 |
|---|---|
| M28 | CascadeVerify v2全栈实现+诚实评测体制(3356文件) |
| M29 | Wave8重构(行为保持): eval_lib去重+qa_module拆分+ruff 242→0 |
| M30/M31 | 论文骨架+图表资产(数字程序化提取) |
| M32 | GJB规则引擎重建(120条规则驱动)+框架图(类型驱动视角) |
| M33 | 双层配置化: NER词典模块+jieba+rulepack引擎(48项迁移) |
| M34/M35 | 技术架构文档(65)+NER详解(66) |
| M36 | 规则层审计+修复(C06QA-008 bug+三暂缓项迁移, 58/60配置化)+67号 |
| M37 | 新文档一键接入工具+01号演示+74号指南 |
| M38 | 延迟基准(8ms/120ms/650ms) |
| M39 | CascadeVerifier facade(场景切换真实生效+缓存缺陷修复) |
| M40-M42 | 场景5分析(75/76)+需求深拆+评测表v1 |
| M43 | 论文真表: 5代表性baseline+3公开NLI基准+跨文档×5+GLM违例对照 |

---

## 12. 诚实边界与遗留项

| 边界/遗留 | 状态 |
|---|---|
| silver仍是唯一标签源 | gold人工标注工作台就绪(108实例/525claim, 预标注完成, 约6-9h人工) |
| 跨文档L1迁移受限 | 线性化层(evidence_statements)未配置化——M36审计已知问题#1, 升级路线明确 |
| 跨文档×5上GLM-5更强(0.888 vs 0.597) | 构造型sound任务适合LLM直读; 诚实呈现+辖区分析 |
| 少数类统计功效(S=6/R=8) | 单条翻转±0.1 F1, bootstrap CI已报 |
| L1为手调正则栈 | 阈值在同一批数据标定, 06号gap是账单; 语义匹配升级路线已定 |
| 变异注入6.1% | 双登记定律的对照面(answer侧单边破坏归语义层) |
| S1QA-077支持样本 | L3证据投递缺口(P2) |
| VIO-15文档名 | 唯一未检出违例(单case) |

---

## 13. 场景5前瞻（下一战场）

**任务**: 图片-QA违规告警问答对的一致性校验（科研生产现场智能监管）。

**核心判断**: 场景1范式的"换证据形态"迁移——文档指定架构(上下文关联与特征提取+特征校验全局召回比对)与方向A/B同构。

**17项检测的归类**（76号深拆）:
- 纯文本4项(零图片零VLM) | 对象识别5项 | 图片理解4项(行为/场景) | 跨样本3项 | 规则驱动2项
- 新方向: 完备性检查("该说没说")×3 + 场景错配 + 跨样本矛盾

**关键技术映射**:
- "对象识别+图片理解" = 场景5的方向A: 图片→结构化清单(实体/状态/计数/场景/时间戳)→注册表
- 判定标准块 = 场景5的规则库(类比GJB 120条): 每task自带, 可编译(条件→场景域/结论→预期判定/枚举→值域)
- 时序元数据(camera,timestamp) = 跨样本聚类的免费主键
- EGT范式 → ③困难负样本构造

**三阶段方案**: ①纯文本侧(配置迁移+文档4对种子评测) ②图片侧(VLM抽取+描述冻结保复现) ③跨样本时序管道。

**判定语义扩展**: 三态+第四档"可疑"(跨样本冲突/属性丢失不判对错, 送人工仲裁)。
