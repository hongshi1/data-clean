# 88. Claim分解的文献定位：回应"是否所有NLI都要先做claim分解"

> 取证日期：2026-11-11。任务：回答方法论质疑——(1)所有做NLI的都要先做claim分解吗？(2)长答案验证的标准做法是什么？(3)typed正则提取是不是非标准的数据拟合？
> 性质：文献取证（只读+写作，未跑模型）。所有仓库引用给出路径；仓库未覆盖的论文细节凭知识补全并标"待核实"，未虚构。

---

## 0. 三问一句话答案（详证见§4）

1. **分解不是NLI的普遍前置**——经典NLI/FEVER/TRUE/ContractNLI/MiniCheck推理期都是"整claim直接判定"；MiniCheck的消融甚至显示推理期分解**无益或有害**（GPT-4 +0.3，专用模型 -1.9~+1.2，成本×2-4，源：`literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1）。分解只在三种场景成为必需：粒度失配（SummaC诊断）、需要逐claim定位/审计、需要typed证据通道——我们三占全。
2. **标准实现有三族**：LLM原子事实分解（FActScore系，长文本事实精度的事实标准）、句子切分（SummaC/TRUE系，摘要一致性主流，确定性无模型）、问题化（QAFactEval/CoVe系）。typed正则**作为主分解器无文献先例**；但作为符号通道的cheap前置+模型兜底**有架构先例**（Kontrast两阶段、需求boilerplate模式归纳线）。
3. **我们的`decompose_claims`是(b)合理工程定制**，不是(a)也不是(c)：typed层=域表面文法前端+可证伪通道语义（Z3/join，非"模式→答案"查找）+标准句切分结构回退+整answer语义回退，且有held-out test-46支撑；但crossdoc-150 acc=0.5133是(c)风险未关闭的敞口，E2 leave-one-doc-out是判决性实验（§4.3）。

---

## 1. 质疑的精确表述

质疑拆成三个可检验命题：
- **P1**：NLI验证必须以claim分解为前置（文献是否支持？）
- **P2**：长答案→三态验证存在"标准做法"，我们的做法偏离了吗？
- **P3**：`decompose_claims`的正则typed分解（numeric/enum/identifier/quoted/semantic，`algorithms/consistency/answer_claims.py:122-174`）是标准做法、合理工程定制，还是面向评测集拟合的非标准启发式？

背景数字（坐标定位用）：91QA直推（answer整当hypothesis，无分解）mDeBERTa macro-F1=0.294、GLM-5.3=0.6105；分解+typed通道+残差NLI管线=0.8047（held-out test-46；官方登记见 `paper/evaluation_tables.md` D1节与 `paper/cascadeverify_main_v1.md` §D1，论文口径B1零样本残差=0.3272/B2=0.6105，与0.294的配置差异属B1族内口径问题，不影响本结论方向）。

---

## 2. 文献证据表（主表）

| 方法 | 会议/年份 | 分解方式 | 分解单元 | 是否typed | 长答案验证范式 | 仓库材料/备注 |
|------|----------|---------|---------|----------|--------------|--------------|
| NLI经典 (SNLI/MNLI/XNLI/CMNLI) | 2015-2020 | 无（数据集本身是pair） | 单个hypothesis | — | 直接pair判定 | 基础设施；CMNLI属CLUE |
| FEVER | NAACL 2018 | 无（claim本身就是输入） | claim | — | 检索→逐claim NLI（S/R/NEI三标签） | Thorne et al.；细节凭知识，待核实 |
| SummaC | **TACL 2022**（注：非ICLR 2022，据仓库核验） | 句子切分（确定性正则） | sentence | 否 | 句×句NLI pair矩阵→聚合（ZS：列max行均值；Conv：50-bin直方图+1D卷积，仅50参数；SummaC Benchmark 74.4 balanced acc） | `literature_survey/modular_verification_architecture_survey.md` E2精读；粒度失配诊断出处 |
| TRUE | Findings of NAACL 2022 | 无新分解（把11个已有事实一致性数据集重格式化为pair） | sentence/摘要（任务给定） | 否 | 直接NLI pair判定（统一T5-11B评测器） | Honovich et al.；**仓库未覆盖**，凭知识补全，细节待核实 |
| QAFactEval | NAACL 2022 | 问题生成（微调QG模型对摘要句生成问题） | question-answer对 | 否 | QG→QA（从源文档取答）→答案重叠/蕴含比较 | **仓库未覆盖**，凭知识补全（Salesforce线，QA-based家族与QAGS同源），细节待核实 |
| FActScore | EMNLP 2023 | LLM原子事实分解 | atomic fact | 否（LLM生成） | 分解→逐条检索知识库验证→聚合（"被支持原子比例"；ChatGPT传记仅58%） | `literature_survey/pair_classifier_sota_2023_2025.md` A3精读 |
| CoVe | arXiv 2023 (2309.11495, Meta) | LLM自生验证问题 | verification question | 否 | 草案→规划验证问题→factored**独立**回答（隔离上下文）→交叉检查修正；开放型问题>yes/no | `literature_survey/id_graph_positioning_survey.md` 表1行1精读 |
| AlignScore | ACL 2023 | 文本块切分（chunk，机械） | 文本块 | 否 | 统一"信息对齐"二元打分器直判（355M，7种skill统一） | `literature_survey/pair_classifier_sota_2023_2025.md` A2 |
| MiniCheck | EMNLP 2024 | **训练期**C2D/D2C原子分解（GPT-3.5/GPT-4）；**推理期不分解** | atomic fact（仅用于训练数据构造） | 否 | 直接claim-doc二元判定（contradiction折叠进unsupported）；**推理期claim分解消融=不必要**（GPT-4 +0.3，专用模型-1.9~+1.2，成本×2-4）；训练期原子级对比构造才是关键 | `literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1全文精读 |
| VERISCORE | arXiv 2024 (2406.19276) | LLM分解+可核验性过滤 | verifiable claim | 否 | 分解→区分可验证/不可验证→只对可验证部分检索验证打分（弃权思想） | `literature_survey/pair_classifier_sota_2023_2025.md` A4 |
| **我们：decompose_claims** | —（仓库，CascadeVerify管线） | 确定性typed正则（numeric/enum/identifier/quoted）+结构切分回退+语义回退 | typed claim | **是** | typed claim→确定性专家（Z3/join）→残差claim过EGT微调mDeBERTa→LLM复检→开世界聚合 | `algorithms/consistency/answer_claims.py:122`、`algorithms/consistency/answer_structure.py:53`、`paper/cascadeverify_main_v1.md` |

**表的两条主线**：①分解单元从粗到细=摘要/答案→句子→atomic fact→问题，**没有任何主流方法使用typed（类型化）分解单元**；②"分解后逐条验证再聚合"是**事实精度评测**（FActScore/VERISCORE）与**摘要一致性**（SummaC）的范式，而**判别器式NLI**（TRUE/AlignScore/MiniCheck推理期）走"整单元直接判定"路线。

---

## 3. 规则/typed提取的先例表（P2/P3专用）

typed正则不是主流分解器，但"规则先行+模型兜底"的**架构**与"域特定claim形态"各有先例：

| 先例 | 出处 | 与typed正则提取的关系 |
|------|------|---------------------|
| Kontrast两阶段（规则匹配→LLM兜底） | 2026, `literature_survey/id_graph_positioning_survey.md` 表4 | **架构先例**：归一化+集合precision/recall≥0.95判same/different，规则优先、模型只处理残差——与我们typed通道→残差NLI同构 |
| 需求boilerplate/模式归纳（Femmer等需求质量线） | `literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §2.3 | **RE域表面文法先例**：从需求语料归纳可复用句法模板——"从域语料归纳正则模式"本身是RE领域合法方法学 |
| FISCAL（金融数值claim合成管线，770M达GPT-4o级） | arXiv 2511.19671，`literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §3.3 | **域特定claim形态先例**：垂直域承认"claim有域形态"，为其定制管线是发表过的做法 |
| 步骤号正则提取作对齐cheap前置 | 同上§2.3（"Kendall τ/位置偏差度量：步骤号提取（正则）后纯符号"） | **组件先例**：正则提取→符号运算在NLP管线中作为确定性子层合法 |
| Chain-of-Table确定性表格操作（f_select_row/f_select_column等） | ICLR 2024，同上§1.2 | **符号通道先例**：确定性表格操作作为推理链中间态（我们L1是其确定性子集） |
| DFKI-NLP数值/缩写扰动 | SemEval-2024 T2，`literature_survey/pair_classifier_sota_2023_2025.md` B4 | **数值claim专用处理先例**：数值矛盾被单列为需要专门数据增强的类别 |
| MiniCheck C2D幂集子claim增广 | EMNLP 2024，同上§1.1 | **训练期分解先例**：原子事实集的幂集增广=我们answer→原子claim分解的训练数据版本 |

**结论行**：typed正则**作为答案主分解器**在检索范围内无直接先例（标"未检索到先例"，非"不存在"）；**作为符号通道的前端+带模型回退**有清晰架构先例（Kontrast最接近）。

---

## 4. 三问详细回答

### Q1：长答案→三态验证时，分解是不是必需的？

**不是普遍必需。**"直接整answer当hypothesis"的先例与效果：

- **整claim/整句直判是判别器路线的标准形态**：经典NLI（pair数据集）、FEVER（claim即输入）、TRUE（重格式化为pair后T5-11B直判）、AlignScore（整块对齐打分）、ContractNLI（hypothesis=整句statement vs 整份合同，`literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §1.3）全部不分解。
- **最强的反直觉证据是MiniCheck消融**（仓库精读，§1.1）：推理期claim分解对GPT-4仅+0.3，对专用微调模型-1.9~+1.2不等，成本×2-4——**在判别器训练粒度正确的前提下，推理期分解不必要**。真正关键的是训练期的原子事实级对比构造。
- **分解成为必需的三个条件**（文献坐标）：
  1. **粒度失配**：SummaC的核心诊断即"NLI句对粒度vs摘要/文档任务的粒度错配"（`literature_survey/nlp4re_llm4re_comprehensive_survey.md`："2021 SummaC: 诊断粒度失配"）——证据粒度比答案细时，直判会把单点矛盾稀释进长答案（我们的答案=多原子claim的复合陈述，mDeBERTa直推0.294的坍缩与此一致，但主因还有域+三态开放世界）。
  2. **逐claim定位/审计**：FActScore的卖点就是"可定位到具体不一致原子"（`literature_survey/pair_classifier_sota_2023_2025.md` A3："比整段判更细粒度，可定位证据"）；ContractNLI后继证明"判定对≠定位对"（`paper/cascadeverify_main_v1.md` 相关工作引Verdicts Without Annotated Evidence）。
  3. **typed证据通道**：异构确定性专家（Z3区间、枚举join、ID注册表join）只能消费类型化claim——这是工程架构约束，不是文献范式。
- **对本项目的含义**：0.6105→0.8047的增益来自"分解作为typed通道的接口+通道裁决+残差NLI+聚合"的**组合**，不能把全部增益归因于分解本身；但若回退到整answer直判，Z3/枚举/ID三个符号通道无从工作。分解对我们的必要性是**架构性**的（条件3），且被条件1（长复合答案）放大。

### Q2：分解的标准实现是什么？

**三族标准实现**（按验证范式分工）：

| 家族 | 实现 | 代表 | 主流场景 |
|------|------|------|---------|
| LLM原子事实分解 | prompt驱动LLM把段落拆成atomic facts | FActScore（EMNLP 2023）、VERISCORE、MiniCheck训练期C2D | **长文本事实精度评测的事实标准**（2023后） |
| 句子切分 | 确定性正则/切分器，无模型 | SummaC（TACL 2022）、TRUE底层数据、QAGS系 | **摘要一致性检测主流**（2021-2022确立） |
| 问题化 | LLM/QG模型生成验证问题 | CoVe（自生问题）、QAFactEval（微调QG） | 自验证链/QA-based评测 |

- **哪种是"主流"取决于任务**：长答案（段落级）对照外部知识核验→FActScore线（LLM分解+检索+聚合）是标准答案；对照冻结文档的判别→MiniCheck路线（推理期不分解，训练期管粒度）是标准答案。**两者都不是typed的**。
- **typed正则是否有先例**：作为主分解器——未检索到先例；作为"规则先行+模型兜底"两阶段架构的规则层——Kontrast是直接先例；作为"从域语料归纳表面模式"——RE领域的需求boilerplate线（Femmer等）是方法学先例（见§3表）。
- **一个关键澄清**：MiniCheck的消融结论（推理期分解无益）与我们管线的表现不矛盾——MiniCheck的claim本来就是单原子级的短陈述，其"整claim"粒度≈我们的"分解后单claim"粒度；我们的答案才是多claim复合体。**MiniCheck否定的是"把短claim再拆碎"，没有否定"把长答案拆到claim级"**。

### Q3：`decompose_claims`在文献坐标里的位置——(a)/(b)/(c)判定

代码事实（`algorithms/consistency/answer_claims.py`）：
- **第一层typed正则**（:40-61,:122-166）：numeric（操作符+数值+单位字典ms/GB/条/种/路等）、enum（包括/包含/分别为标记+顿号切分）、identifier（`[A-Z]{2,8}(-[A-Z0-9]{1,12}){1,6}`即GJB编号文法）、quoted（「」引号术语+否定前缀）——单位字典、枚举标记、ID格式**全部来自GJB域表面文法**；
- **第二层结构回退**（:167-171→`answer_structure.py:53`）：bullet/step/sentence切分+scope hint——**这正是SummaC标准的句切分路线**；
- **第三层语义回退**（:172-173）：整answer单claim——**这正是MiniCheck/TRUE的整单元直判路线**。
- 全模块零模型调用（docstring明示"This layer is deterministic: patterns only, no model calls"）。

**判定：(b)合理工程定制**，论证分三面：

1. **为什么不是(a)标准做法**：文献主表（§2）显示typed分解单元在FActScore/SummaC/QAFactEval/CoVe/MiniCheck中零出现；把"numeric/enum/identifier/quoted"作为一等分解类别是本管线的领域构造。
2. **为什么不是(c)评测拟合**（四条防线，按强度排序）：
   - **通道语义可证伪**：typed claim不是"模式→答案查找"，其下游是语义明确的形式化运算——numeric→Z3区间约束（`extract_numeric_claims`被numeric_z3专家复用，见模块docstring）、enum→值域join、identifier→注册表join。模式只负责**发现**，判定由形式语义承担——这区别于"正则拟合出判定"。
   - **回退链覆盖文献两条标准路线**：句切分回退（SummaC式）+整answer回退（MiniCheck推理式）保证非GJB形态输入不因模式失配而失去召回——拟合型启发式的典型特征是"模式外样本性能悬崖"，本结构无此悬崖。
   - **held-out证据**：0.8047在test-46 held-out上取得（`paper/evaluation_tables.md` D1节）；且团队已在本项目内经历并修复过一次真正的"拟合"失败——EGT一代近拷贝文法dev=0.965、真实迁移仅0.50，二代叙事文法refute召回0.375→0.875（`77_master_consolidation.md`："标签对但形态错的训练数据会负迁移"）——**"域文法拟合"与"评测集拟合"的差异是本项目已实证掌握的知识**，typed层属于前者。
   - **域文法定制有发表先例**：FISCAL（金融域claim管线）、Femner需求模式归纳、Kontrast规则优先架构（§3表）——"为垂直域定制claim形态学"不是孤立启发式。
3. **(c)风险的诚实敞口**：crossdoc-150 acc=0.5133（`paper/evaluation_tables.md`）是(c)风险的现实存在证据——typed模式与91QA答案风格同源于GJB语料，跨文档泛化未证。**E2 leave-one-doc-out是判决性实验**：若typed通道在留出文档上保持增益，(b)判定闭合；若增益消失，则typed层需降格为"域内加速器"表述。此外`70_subtraction_module_design.md:161`的分解错误类型学（needed/bad_scope(Dong式)/bad_granularity(SummaC式)）表明管线已有对"分解本身出错"的自检机制，这是(c)质疑的正面回应姿势。

---

## 5. 对我们架构的定位结论

在文献坐标系里，CascadeVerify的分解层是一个**三层降级的混合体**，每层各对齐一个标准范式：

```
typed正则层   ←→  无直接先例（域文法构造；Kontrast架构先例、FISCAL域定制先例）
结构切分层   ←→  SummaC/TRUE句切分（标准）
语义回退层   ←→  MiniCheck/TRUE整单元直判（标准）
```

对外表述建议（论文/答辩用语）：
- 不宣称"claim分解是新贡献"——分解本身是FActScore/SummaC旧范式；
- 宣称点是**分解的可审计确定性实现**（零模型、可复现、每claim可trace到通道裁决）服务于开世界三态与符号通道接口——这与MiniCheck"训练期管粒度"互补而非冲突；
- typed层必须绑定"GJB域表面文法"表述（类比FISCAL/boilerplate线），并在limitation中如实报告crossdoc 0.5133与E2待做状态——这是把(c)质疑从"潜在指控"转化为"已知边界"的唯一诚实做法。

---

## 6. 仓库材料索引（本取证引用）

| 材料 | 路径 | 用途 |
|------|------|------|
| MiniCheck全文精读（含推理期分解消融） | `docs/srs_project/literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1 | Q1/Q2核心证据 |
| SummaC精读（句切分+聚合+粒度失配诊断） | `docs/srs_project/literature_survey/modular_verification_architecture_survey.md` E2 | Q2 |
| FActScore/VERISCORE/AlignScore/CoVe条目 | `docs/srs_project/literature_survey/pair_classifier_sota_2023_2025.md` A2/A3/A4/A6 | 主表 |
| CoVe四步+factored结论 | `docs/srs_project/literature_survey/id_graph_positioning_survey.md` 表1行1 | 主表 |
| Kontrast两阶段（规则→LLM兜底） | 同上 表4 | §3 typed先例 |
| EGT文法定律（一代拟合教训） | `docs/srs_project/77_master_consolidation.md` | Q3(c)判定 |
| 分解错误类型学（bad_granularity等） | `docs/srs_project/70_subtraction_module_design.md:161` | Q3 |
| 管线架构与D1数字 | `docs/srs_project/paper/cascadeverify_main_v1.md`、`paper/evaluation_tables.md` | 背景数字 |
| 代码 | `algorithms/consistency/answer_claims.py:122`、`algorithms/consistency/answer_structure.py:53` | Q3代码事实 |

## 7. 待核实清单

1. TRUE（Honovich et al., Findings NAACL 2022）：11个数据集构成、T5-11B细节、是否含句子级拆分——仓库无材料，引用前需核对原文（arXiv 2204.04991，编号凭记忆待核实）。
2. QAFactEval作者/机构与QG-QA-比较的具体模型配置——仓库无材料，需核对（NAACL 2022）。
3. FEVER标签体系细节（SUPPORTS/REFUTES/NEI）为常识性记忆，引用数字前无需核对，但作者列表需核对。
4. SummaC会议更正（ICLR 2022→TACL 2022）以仓库精读材料为准，若与原论文冲突以论文为准。
5. §3表中2026年文献（Kontrast等）的arXiv编号见`id_graph_positioning_survey.md`文末清单，本取证未二次核验。
