# 评测方案（上下文关联 + 一致性校验）——论文表格 v2 定稿

> 数字来源: 上下文关联=跨模态链接方向实测(表1原样); 一致性校验=2026-10-30同批运行
> (eval_public_matrix_921b0139 / eval_crossdoc5_e020b13f / fill_crossdoc5_cells / eval_paper_matrix_c409df7f_20261030 / eval_cascade_1e92cdce_20261030 / GLM-5违例直推补测)

---

## 数据集

**自建（上下文关联）**：16份真实GJB 438C军用SRS，构建"表格深度检索"（438查询×1,207表格）与"软件图片"（899查询×379图）两个场景。

**自建（一致性校验）**：16份真实GJB 438C军用SRS，构建三个场景——"答案一致性校验"（91查询×574证据块，真实QA+silver三态标签）、"跨文档泛化"（05/06/07/08/10五文档×30查询，构造性sound标签，跨行污染/支撑删除逐条程序化断言）、"真实违例检测"（17条人工深读违例×构造断言QA）。

**XNLI-zh**：跨语言NLI中文测试集（Conneau et al., EMNLP 2018），2,000查询（抽样自5,010）。
**OCNLI**：中文原生态NLI基准（Hu et al., EMNLP 2020），2,950查询（全量官方test）。
**CMNLI**：中文匹配自然语言推理（CLUE家族），2,000查询（抽样自12,241）。

（一致性校验的文档级三态任务在公开文献无先例基准——自建基准本身即贡献。）

---

## 表1 证据召回 R@1 对比

| 方法 | 自建-表格深度检索 | 自建-软件图片 | WTQ | FeTaQA | DuRetrieval |
|---|---|---|---|---|---|
| BM25-doc | 0.183 | 0.685 | 0.282 | 0.706 | 0.836 |
| BM25-unit | 0.158 | 0.543 | 0.277 | 0.788 | 0.744 |
| BGE-dense | 0.078 | 0.660 | 0.333 | 0.836 | 0.879 |
| LightRAG-dense | 0.144 | 0.596 | 0.334 | 0.883 | 0.865 |
| Ours | **0.486** | 0.642 | **0.464** | 0.860 | **0.954** |

---

## 表2 答案一致性校验 macro-F1 对比

| 方法 | XNLI-zh | OCNLI | CMNLI-test | 自建-91QA | 自建-跨文档×5 |
|---|---|---|---|---|---|
| BGE三元中心 | 0.538 | 0.500 | 0.511 | 0.117 | 0.348 |
| Erlangshen-330M零样本 | 0.798 | 0.792 | 0.826 | 0.415 | 0.380 |
| mDeBERTa零样本 | 0.793 | 0.723 | 0.848 | 0.295 | 0.485 |
| CMNLI微调mDeBERTa | **0.810** | 0.728 | **0.867** | 0.276 | 0.596 |
| GLM-5直推 | 0.761 | **0.827** | 0.770 | 0.611 | **0.888** |
| Ours-L2(EGT域适配) | 0.750 | 0.694 | 0.798 | 0.297 | 0.468 |
| **Ours级联** | — | — | — | **0.786** | 0.597 |

注：
- 公开三列为语句级NLI（premise, hypothesis三态判定），级联为文档级架构（L0-L3级联+证据定位）不适配语句级任务标"—"
- CMNLI微调=公开监督数据（50k训练）的代表；Ours-L2=域数据（EGT合成）的代表——**公开监督公开列最强(0.810/0.867)但91QA崩塌(0.276, refute F1=0.0)，公开数据≠域数据的正反对照**
- 跨文档×5为构造性sound标签（叙事型声明），适合LLM直读（GLM-5达0.888）；Ours的L1确定性层迁移受表格线性化层配置化不完全的限制（诚实局限，见讨论节）
- 91QA的held-out测试集（29主题簇切分46条）：Ours级联0.829, refute P=1.0

## 表3 真实违例检测与成本对比

| 方法 | 自建-17真实违例(检出率) | 91QA-refute精确率 | LLM调用(91QA) |
|---|---|---|---|
| B3确定性规则 | **0.941** (16/17) | 1.000 | 0 |
| GLM-5直推 | 0.118 (2/17) | 0.714 | 91 |
| B4全配置(无路由) | — | 0.778 | 83 |
| **Ours级联** | **0.941** (16/17) | **1.000** | **15** |

注：
- **GLM-5直推在真实违例上崩溃（2/17, 12个假support）而构造型跨文档上最强（0.888）——真实矛盾是跨位置双登记（同ID两处冲突/正逆追踪矛盾），矛盾信号需结构化join才浮现；构造型任务是单侧干净声明，LLM直读即判。此为方法辖区划分的核心实证**
- 级联的经济学：18%的LLM成本(15/83)取得全场最优refute F1=0.857且精确率1.000

---

## D1 LLM仲裁蒸馏（训练期LLM教师，推理纯本地）

> 2026-11-09实测。管线：tools/distill_teacher_labels.py（教师标签，GLM-5.3离线+磁盘缓存可复现）→ tools/train_distilled_nli.py（微调，run: train_distilled_nli_b3838652_20261109_200219）→ tools/eval_distilled.py + tools/calibrate_distilled_gate.py（评测）；checkpoint注册于 algorithms/consistency/nli_local.py MODELS["distilled_v1"]；数字登记：data/gjb_438c/distillation/d1_paper_summary_v1.json（提取层：tools/paper_data.py get_d1_distillation()）。

**方法**：LLM arbitration distillation——把L3 LLM仲裁能力（一次性、离线、缓存可复现）蒸馏进本地NLI残差通道。教师GLM-5.3按重建的pre-M66 L3 prompt（开放世界/锚定/值判定规则system prompt，10-claim分块）对dev-45的179条残差claim给出三态判定；学生egt_finetuned_v2继续微调（EGT合成回放2:1防灾难遗忘+refute过采样3×，lr=1e-5/4epochs/batch16/seed42，160.4秒）；gate在dev上校准=0.8。推理时算法保持纯本地三层（L0 NER+L1规则+L2 NLI）**零API调用**。教师标签全量355条claim（239 NIE/103 support/13 refute，premise覆盖率0.8448），训练只见dev-45（test-46的176条claim/violations-17/crossdoc-150训练不可见）。

**表4 D1蒸馏 held-out对照（test-46，29主题簇切分，训练未见）**

| 系统 | gate | acc | macro-F1 | refute F1 (P/R) | 推理时LLM调用 |
|---|---|---|---|---|---|
| egt_finetuned_v2（EGT-only，旧L2） | 0.7 | 0.7826 | 0.5911 | 0.500 (0.333/1.000) | 0 |
| distilled_v1（同gate对照） | 0.7 | 0.8913 | 0.7758 | 0.727 (0.571/1.000) | 0 |
| **distilled_v1（dev校准gate）** | **0.8** | **0.9130** | **0.8047** | **0.800 (0.67/1.00)** | **0** |

参考（全91QA自评口径，含dev-45训练数据，**不可与test-46直接对比**）：旧cascade（L2 NLI→L3 GLM复核，推理需远程API）acc=0.9231/macroF1=0.7860/refuteF1=0.857；旧l3_llm（GLM-5.3直推L3，91次远程直推）acc=0.9451/macroF1=0.8747/refuteF1=0.824；fast纯确定性acc=0.9121/macroF1=0.7212/refuteF1=0.769。

读数：蒸馏带来macro-F1 **+0.1847**（同gate口径0.5911→0.7758）/**+0.2136**（dev校准gate口径→0.8047），refute精确率**+0.34**（0.33→0.67，召回1.00保持）——蒸馏修的是NLI开放世界三态错校准（refute过度触发：EGT-only在test-46预测的12个refute里8个为伪），且以零推理API在held-out上逼近含远程LLM系统的水平。

**表5 D1蒸馏专项集（held-out）**

| 评测集 | n | 结果 | 说明 |
|---|---|---|---|
| violations-17（真实违例） | 17 | 检出16/17；refute F1=0.9697（P=1.000/R=0.941） | 与旧系统持平（确定性refute短路残差派发；gate=0.7评测口径） |
| crossdoc-150（5文档sound答案） | 150 | acc=0.5133 | 弱项：训练未见跨文档数据；E2 leave-one-doc-out蒸馏待做（跨文档教师标签已生成：teacher_labels_crossdoc.jsonl） |

---

## E2 跨文档迁移分析（leave-one-doc-out蒸馏，诚实负结果）

> 2026-11-10实测。设计：每fold训练于qa91-dev-45教师标签+crossdoc教师标签**减去1个文档**（tools/train_distilled_nli.py新增--base-dir/--exclude-doc），评测held-out文档（30实例）+test-46（域内回归检查）。前置发现：crossdoc-150实为**平衡构造集**（support/refute/NIE各50，"sound_label"为构造性标签）；教师GLM-5.3在156条claim中标42个refute，抽查验证正确（设备/阶段集合值冲突，如C05QA-011：证据"桌面、平板"vs答案"桌面、平板、手持"）。数字登记：data/gjb_438c/distillation/e2_paper_summary_v1.json（提取层：tools/paper_data.py get_e2_loo()；结果文件：e2_loo_results_v1.json / e2_loo_curriculum_results_v1.json / e2_loo_mixed_noos_results_v1.json）。

**表6 E2三变体（held-doc acc为5文档留一折均值 / test-46 macro-F1为域内回归）**

| 训练配方 | held-doc acc | test-46 macro-F1（域内代价） |
|---|---|---|
| D1基线（无crossdoc训练） | 0.5133 | 0.8047 |
| v1 单阶段+refute过采样3× | 0.5667 | 0.6562 |
| v2 两阶段课程（crossdoc泛化→qa91-dev域内退火） | 0.5600 | 0.7014 |
| v3 单阶段无过采样 | 0.5667 | 0.6921 |

**gate扫描排除门控失配**：D1 distilled_v1在crossdoc-150上gate∈{0.5, 0.6, 0.7, 0.8}扫描，acc=0.5200/0.5133/0.5200/0.5133——平坦（极差0.0067），弱项非门控失配，是premise分布漂移。

读数（诚实结论）：LLM蒸馏跨文档迁移收益**+0.05 acc**（0.5133→0.5667），但一致付出域内**-0.10~-0.15 macroF1**代价；278M学生+~300教师标签训练对规模下，蒸馏能力是**域绑定的**——课程学习（v2把域内代价收窄到-0.10）/过采样控制（v3无过采样域内反而优于v1）只能部分缓解，无一变体同时守住两端。

---

## 双NLI共识门控（消融，负结果）

> 2026-11-09实测（tools/eval_consensus.py，run: eval_consensus_8624d45a_20261109_225618）。设计：distilled_v1判refute（gate≥0.8）**且**零样本Erlangshen-330M也判contradiction（p_contra≥erlang_gate）才保留refute——双模型共识作为refute精确率补丁。数字登记：data/gjb_438c/distillation/e2_paper_summary_v1.json（提取层：tools/paper_data.py get_consensus_ablation()）。

**表7 共识门控 test-46消融（erlang_gate=0.4，dev-best）**

| 系统 | macro-F1 | refute P/R | 说明 |
|---|---|---|---|
| distilled_v1（gate=0.8，基线） | 0.8047 | 0.67/1.00 | D1主结果 |
| +Erlangshen共识门控 | 0.7885 | 0.75/0.75 | **净降-0.0162** |

dev-45扫描erlang_gate∈{0.4, 0.5, 0.6, 0.7}全并列（macroF1 0.7056，dev基线0.6694——dev上的"提升"是假象，四档同值取dev-best=0.4）。test-46诚实结果：refute精确率0.67→0.75但召回1.00→0.75，**误杀1条真refute（S1QA-063，Erlangshen p_contra=0.0045判neutral）**。

根因：零样本Erlangshen与distilled的refute一致率仅**33%（dev 0%）**——门控退化为近全盘否决；两模型分歧由域适配差异主导（distilled域内微调 vs Erlangshen零样本残差premise分布），非distilled的错误。未来方向：域适配异构集成（egt_finetuned_v2+distilled_v1）。

---

## 三组对照实验（支撑表格的科学论点）

| 对照 | 结论 |
|---|---|
| CMNLI微调 vs Ours-L2 | 公开监督数据公开列赢、域列崩——域适配必须用域数据（EGT构造性合成） |
| GLM-5: 跨文档×5 vs 17违例 | 构造型0.888 vs 真实违例0.118——LLM直读胜任干净声明、崩溃于跨位置矛盾——双登记定律 |
| B3(0成本) vs 级联(15调用) vs B4(83调用) | refute精确率1.000/1.000/0.778——路由花在召回不在精确，级联是成本-质量Pareto点 |
