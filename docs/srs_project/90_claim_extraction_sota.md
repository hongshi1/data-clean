# 90. Claim/原子事实提取器的SOTA谱系、我们的位置与升级路径

> 取证日期：2026-11-12。任务：调研"claim/原子事实分解器"**实现本身**的SOTA谱系（7线），定位我们的正则+回退实现，给出升级路径矩阵与判定。
> 性质：文献取证（只读+写作，未跑模型，未git commit）。
> 与88/89号分工：88号回答**验证单元**视角（要不要分解、三族实现、typed无先例、(b)判定）；89号回答**归因单元**视角（定位单元≡验证单元、verdict≠span）。本文回答**实现视角**：分解器作为一个模块，SOTA怎么做、我们处在哪、怎么升。88/89已展开的论证只引用不重复。仓库未覆盖的论文细节凭知识补全并标"待核实"（沿88§7口径），未虚构。

---

## 0. 三问一句话答案（详证见§1-§4）

1. **SOTA谱系**：2023年后长文本事实精度的主流分解器是**prompted LLM**（FActScore系），全族claim=LLM改写文本、**不带原文span/offset**（FActScore已知局限，89号已录"映射回answer需自建provenance"）；trained分解器集中在**问题化范式的QG**（QAFactEval/QuestEval），产出question而非claim；OpenIE（SPO三元组）已退出主赛道且中文生态弱；**"分解器原生输出claim span"在主流实现中不存在**——span要么是标注协议（ContractNLI/FICLE）、要么是事后diff（RARR）、要么靠自建provenance。
2. **我们的位置**：正则typed+回退（v1）+审计修复层（v2）+域中立句切分档（v3）＝**域文法前端，非SOTA**——原子性质量低于LLM分解器，但占据"确定性可审计+推理零成本零LLM+typed通道原生接口"的组合位（该组合位无竞争者，Kontrast架构先例，88§3）。硬缺口一处：**AnswerClaim无span字段**，M84(a)断言级定位目前不成立。跨域弱项（0.5109）已由v3换档工程性缓解（sentence+dominant_70→0.7361），但E2判决性实验地位不变（88§4.3）。
3. **升级判定**：**路径C（span补全）性价比最高**——finditer的match位置已在手，只差记录+字段+测试，~一天工程，直接落地M84(a)；**论文叙事最强的是C强化后的"可审计确定性claim层"**（88§5已定调，C把可审计性从"通道裁决级"升级到"字符级provenance"）。"distilled claim segmenter"（路径A）作为主贡献点风险高：E2已证小规模蒸馏域绑定，需先过A'低风险变体（教师分解仅用于EGT增广＝MiniCheck D2C同构）；路径B（OpenIE）域错配+仓库先验已判质量瓶颈，放弃。

---

## 1. 七线SOTA证据表

**列定义**：分解器实现=拆分机制本体；带span=claim是否携带原文offset/字符区间（可定位回源文本）；可本地化=推理期可否脱离API在本地权重上运行；适配度=对我们"冻结文档+长答案+三态+typed通道"场景。仓库锚点给路径；无锚点条目凭知识补全并标"待核实"。

### 1.1 LLM-prompted原子分解线

| 方法 | 年份/会议 | 分解器实现 | 带span | 可本地化 | GJB场景适配度 |
|------|----------|-----------|--------|---------|--------------|
| FActScore | EMNLP 2023 | GPT-3.5-Instruct按prompt把段落拆成atomic facts（生物域，每句多原子） | **否**（LLM改写文本，无offset——已知局限） | 否（推理期需API） | 中：分解质量最高，但破坏我们确定性/可审计口径（缓存可复现，分解本身非确定） |
| SAFE | arXiv 2403.18802, Google DeepMind【待核实】 | LLM生成独立claim+多步搜索推理逐条核验 | 否 | 否（依赖搜索引擎） | 低（89号A6注：外部检索不适用"文档即证据"场景） |
| VERISCORE | arXiv 2406.19276 | LLM分解+可核验性过滤（上下文无关/客观），弃权思想 | 否 | 否 | 中（repo A4精读：弃权换precision与我们NIE开放世界有结构亲缘） |
| D-FActScore | EACL 2024【待核实】 | LLM原子分解+**说话人归因**（对话域：每个原子挂speaker） | 间接（对话turn级天然可定位）【待核实】 | 否 | 中：证明"分解时保留语用角色（谁断言的）"是可发表扩展——我们attr字段同位置 |
| Factcheck-GPT | arXiv 2305.13534【venue待核实】 | LLM claim抽取（带/不带检索上下文两变体）+RAG搜索逐条验证 | 否 | 否 | 中：**它把"claim抽取"作为独立模块单独消融**（抽取变体影响下游）——"分解器质量被单独评测"的先例，我们audit→v2循环同构 |

**判读**：该线是2023+长文本事实精度的**事实标准**（88§2）；但claim是改写文本，provenance全部要用户自建（FActScore的工程用法即如此，89号Q1已录）。适配我们的冻结证据场景需把检索换成context join——分解器本身仍非确定、仍需API。

### 1.2 训练式分解器线

| 方法 | 年份/会议 | 分解器实现 | 带span | 可本地化 | GJB场景适配度 |
|------|----------|-----------|--------|---------|--------------|
| QAFactEval | NAACL 2022 | **微调QG模型**（T5系问题生成器）对摘要句生成问题→过滤→QA从源文档取答→答案比较 | 间接（question→来源句映射） | 是（开源权重，英文中心） | 低：产出question非claim，typed通道（Z3/join）消费不了问题；中文军事域QG不存在需自训 |
| QuestEval | EMNLP 2021【待核实】 | 交替QG/QA+遮罩，trained QG+QA双模型，问题相关性加权 | 间接 | 是（英文） | 同上 |
| CoVe | arXiv 2309.11495 (Meta) | **校正：CoVe分解器是prompted LLM非trained model**（自生验证问题，`id_graph_positioning_survey.md` 表1行1"LLM自生验证问题"） | 否 | 否 | factored独立回答>joint的结论对残差派发设计有参考 |

**判读**：此线"trained"部分几乎全是**QG**——问题化范式的分解单元是question。文献中不存在"trained claim切分器"的主流先例（claim检测线见1.4是分类器不是分解器）——这对路径A是个双刃事实：**无先例=新贡献空间，也无先例=无可直接搬运的基线**（标"检索范围内未见"，非"不存在"）。

### 1.3 OpenIE线（经典结构化提取）

| 方法 | 年份/会议 | 分解器实现 | 带span | 可本地化 | GJB场景适配度 |
|------|----------|-----------|--------|---------|--------------|
| OpenIE6 | AAAI 2020【待核实】 | 迭代网格标注+self-supervised，谓词连词切分 | **句内天然可恢复**（主/谓/宾=原句子串，位置即span） | 是（开源，**英/西语**） | 低 |
| SpanIE | ACL 2024【待核实】 | span-based OpenIE：BIO式联合实体关系标注，RE语料（NYT/CoNLL04）训练 | **是**（token级span输出） | 是（**英文**） | 低 |
| 中文替代 | — | 无强开源神经OpenIE；候选=UIE（EMNLP 2022，Baidu，schema引导生成式，中文权重已发布）或LTP/HanLP依存SVO | UIE靠生成文本映射回原文（非token分类）【机制待核实】；依存SPO带词级位置 | 是 | 中低 |

**判读**：①OpenIE的SPO粒度与typed通道错配——"时延≤50ms"式数值+操作符断言落不进干净SPO，Z3消费前仍需归一化（等于白加一层）；②仓库先验：`literature_survey/agentic_rag_survey.md` L352已判"OpenIE抽取质量是瓶颈；对我们可用'参数族词典+规则'替代"（针对检索图，质量担忧同样适用于分解前端）；③域漂移（新闻/wiki→军标缩略语+表格文本）。**适配度全线最低。**

### 1.4 claim检测/规范化线（事实核查前端）

| 方法 | 年份/会议 | 分解器实现 | 带span | 可本地化 | GJB场景适配度 |
|------|----------|-----------|--------|---------|--------------|
| ClaimBuster | IEEE TKDE 2019【待核实】 | check-worthiness**句子分类**（SVM/dense特征），政治演讲域 | n/a（不分解，判"哪句值得查"） | 是（小分类器） | 低：解决"哪句值得查"≠"怎么拆" |
| CLEF CheckThat! | 2018-持续共享任务 | Task1 check-worthiness；2022-2023起**claim matching**（同一claim不同表述的归一/去重/匹配） | n/a | 是 | **对方向A高**：claim matching与"跨章节同一实体/参数聚合"直接同构（交叉引用，不在本文展开） |

**判读**：对M84无直接用（check-worthy检测在分解**之前**的前端，我们QA场景每条answer都需分解，无选择问题）；claim matching对方向A（上下文关联）有方法参考价值。

### 1.5 需求工程线（RE域）

| 先例 | 出处 | 与claim分解的关系 |
|------|------|-----------------|
| ISO/IEC/IEEE 29148 atomic requirement | 2011/2018（章节号待核实） | **域级本体先例**：需求原子性（单一、可测量、可验证陈述）是标准自身的质量要求——"分解到原子"不是NLP发明而是需求工程的本体约束 |
| Femmer/Fucci需求气味 | JSS 2017（repo已录） | **方法学先例**：~53%质量规则可用模式自动化（88§3已引）＝"正则处理需求文本"的RE合法性来源 |
| requirement modularization | 近年【存在性待核实】 | 大规格需求模块化分解以保障质量——分解粒度作为设计变量的RE线 |
| GJB 438C合格性规定 | `knowledge/gjb_438c_rules_full.json`（"针对第3章中的每个需求指定合格性检验方法"） | **文档结构先例**：军标按"每个需求可单独检验"组织规格说明——我们的identifier/enum claim形态正源于这种文档结构 |

**判读**：RE线不提供分解器**实现**，提供分解**合法性**（为什么必须原子化）与正则方法的域先例——这正是88§3为typed层辩护时已用的弹药，此处不重复。

### 1.6 训练期分解合成线

| 方法 | 出处 | 机制 |
|------|------|------|
| MiniCheck C2D/D2C | EMNLP 2024（repo精读`five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1） | 分解**只用于训练数据构造**（原子事实集+否定对比+幂集增广），推理期不分解；消融证推理期分解无益 |
| 我们：EGT合成 | `algorithms/consistency/egt_synthesis.py` + `tools/build_egt_dataset.py` | 三种子路径（QA/语句/叙事），S原样/R确定性翻转（值污染+scope锚定）/N删除换源 |

**判读**：**同构已成立**——都从证据文档侧构造原子级三态训练对；差异=MiniCheck用GPT-3.5/4生成claim，我们用文法模板。EGT一代近拷贝文法的负迁移教训（77号：dev 0.965/真实迁移0.50）与MiniCheck"对比构造质量决定判别器质量"是同一条定律的两面。**此线不是升级选项而是已有坐标**；A'变体（§3路径A）的文献锚点。

### 1.7 带span的归因提取线

| 方法 | 出处 | span机制 |
|------|------|---------|
| RARR | EMNLP 2023【89§5.1待核实】 | masked span+证据搜索+不变性约束改写；定位=input与revision的事后diff |
| ContractNLI | EMNLP 2021 Findings（repo §1.3） | 证据span**多标签标注协议**（集合分类，非start/end回归） |
| FICLE | ECML-PKDD 2023（repo E4） | 不一致span+类型+claim成分三层标注；**分阶段流水线打败联合多任务；DeBERTa判别式最好span、T5生成式最好三元组** |

**判读**：分解+span联合输出的先例存在，但**没有一个是"分解器原生输出claim span"**——span要么是标注协议、要么是diff副产品、要么自建。**我们的正则实现在此坐标有结构性优势：match.span()是免费副产物**（OpenIE式表面字符串定位，FActScore要自建的东西我们本来就持有）——这是路径C的文献依据。

---

## 2. 我们的位置图

### 2.1 实现事实（代码层，三层）

- **v1 typed正则+回退**（`algorithms/consistency/answer_claims.py`，224行，docstring明示"patterns only, no model calls"）：numeric（操作符字典+GJB单位字典ms/GB/条/路…）→ enum（包括/包含/分别为+顿号）→ identifier（GJB编号文法`[A-Z]{2,8}(-…)`)→ quoted（「」+否定前缀）→ 结构回退（`answer_structure.py` bullet/step/sentence）→ 整answer语义回退；
- **v2 审计修复层**（`answer_claims_v2.py`，178行，仍零模型）：colon split（修37%题名：描述融合claim，S1QA-066/069/077 support失败根因）+framework filter（3%噪声）+subject inheritance+open-list enum降级——审计= `tools/audit_claim_extraction.py`（91QA），消融=`tools/eval_decomp_ablation.py`，测试=`tests/test_answer_claims_v2.py`；
- **v3 域中立档**（`answer_claims.py:184` `decompose_claims_sentences`）：crossdoc preset（`PRESETS["crossdoc"]`＝sentence分解+dominant_70聚合，`tests/test_v3_profiles.py`契约锁定）；
- **两档实测**（`data/gjb_438c/distillation/refactor_matrix_v1.json`）：A_typed|strict——test46 macroF1 **0.8047** / crossdoc150 **0.5109**；B_sentence|dominant0.60-1.00——crossdoc150 **0.7361** / test46 0.4205（B_sentence|strict 0.5038，support召回坍缩）。
- **span现状：无。** `AnswerClaim`字段=kind/text/attr/operator/value/unit/negative——无offset；numeric claim文本是**重构串**（`f"{attr} {operator}{value}{unit}"`，`answer_claims.py:147`）非原文子串；quoted/identifier的match位置在手（`answer_claims.py:149,158`）但未记录；结构回退句切分可算累计偏移但未算。

### 2.2 SOTA坐标定位（诚实版）

| 维度 | 我们v1+v2 | LLM分解器（FActScore系） | trained QG（QAFactEval系） | OpenIE/SpanIE | span标注线（FICLE系） |
|------|-----------|--------------------------|---------------------------|---------------|---------------------|
| 原子性质量 | 中低（colon融合已修；叙事改写claim靠v2半修） | **最高** | 高（问题粒度） | 低（SPO错配typed） | 任务定义级 |
| claim带span | **无（缺口）** | 无（自建provenance） | 间接（→来源句） | 句内天然 | 一等（但=标注不是分解器） |
| 跨域 | typed档0.5109弱（v3换档0.7361） | **天然跨域**（换prompt） | 英文域 | 域漂移大 | — |
| 确定性/可审计 | **完全**（逐claim可trace到通道裁决） | 非确定（缓存缓解） | 推理确定 | 确定 | — |
| 推理成本 | **零模型零API** | 每次分解API | 本地GPU | 本地GPU | — |
| typed通道接口（Z3/join） | **原生**（`extract_numeric_claims`被numeric_z3复用） | 需再parse | 无 | 需再归一化 | 无 |

**一句话定位**：域文法前端，非SOTA；但在"确定性+零推理成本+typed通道原生接口"组合位上无竞争者（Kontrast两阶段架构先例，88§3）。crossdoc弱项已被v3**换前端**工程性缓解——注意这是"换档"不是"typed前端跨域变强"，E2 leave-one-doc-out判决性实验地位不变（88§4.3）。相对1.1-1.7各线：比LLM线少原子性多确定性，比QG线多claim形态少生态，比OpenIE线多域适配少通用性，比span线少标注协议多免费span潜力。

### 2.3 M84三需求支持现状

| M84需求 | 现状 | 缺口性质 |
|---------|------|---------|
| (a) 断言级定位（answer span） | **✗** 无span字段 | 唯一硬缺口，恰好是路径C免费可补的 |
| (b) 证据侧语句级归因 | △ 块ID级ℓ已有（Y={S,R,N}×ℓ×j契约）；证据侧span未做 | 89号已论证定位是独立能力，属证据侧模块职责 |
| (c) 三态聚合 | ✓ claim级strict/dominant_70双档（50号选型记录） | 无 |

---

## 3. 升级路径矩阵

| 路径 | 方法 | 预期收益（span/原子性/跨域） | 成本（训练/API） | D1蒸馏管线复用度 | 主要风险 | 文献锚点 |
|------|------|------------------------------|------------------|------------------|----------|----------|
| **A：LLM教师分解→蒸馏本地切分器** | `tools/llm_teacher.py`（离线训练数据专用，缓存兼容）让GLM-5.3对91QA答案+16文档语句标注原子claim+span（claim边界）；学生=mDeBERTa 278M token级claim边界标注器（复用`train_distilled_nli.py`训练环+runs协议）；推理分解=本地一次前向 | span=token级（最优）；原子性=跨域；跨域=主攻0.5109弱项 | 教师API一次性（数千句，缓存留痕）+本地微调（分钟级GPU）；推理每answer+一次前向 | **高**：llm_teacher/train_distilled/runs/EGT语句种子四件全复用 | **E2阴影**：278M+小规模标签=域绑定（`paper/evaluation_tables.md` E2节）；须leave-one-doc-out从第一天进评测；须beat两档基线（typed 0.8047域内+sentence 0.7361跨域）才可作贡献点 | Factcheck-GPT的抽取模块独立消融先例；D-FActScore说话人归因（=attr字段）；1.2判读：trained claim切分器无主流先例（双刃） |
| **A'（A的低风险变体）** | 教师分解**只用于EGT增广**：给EGT加第四种子路径（LLM分解的原子claim做S/R/N三态翻转），推理管线不变 | 跨域（EGT覆盖面）；不动推理架构 | 教师API一次性；训练=既有EGT流程 | **完全**：EGT+llm_teacher原样 | 教师分解噪声进入训练数据（一代文法教训77号需复检）；收益上限=EGT质量 | **MiniCheck D2C完全同构**（1.6） |
| **B：OpenIE/神经span提取器** | 中文候选=UIE零样本（schema引导）或LTP依存SVO（英文OpenIE6/SpanIE直接排除——无中文） | span=token级；原子性=SPO粒度（与"≤50ms"式claim错配） | 无训练但新增GPU模型通道（延迟+weights+依赖） | 低：仅embedding_channel式惰性加载模式可参考 | 域漂移（新闻/wiki→军标）；仓库先验已判OpenIE质量瓶颈（`agentic_rag_survey.md` L352） | OpenIE6/SpanIE/UIE（1.3） |
| **C：保持正则+补span追踪** | `AnswerClaim`加`span: tuple[int,int]|None`（answer内偏移）+可选attr_span；各extractor已有finditer/match.span()只需记录（`answer_claims.py:86,91,102,149`）；identifier已有position（:159）；结构回退句切分累计偏移；v2 colon split子claim继承父span再切；输出契约Y的ℓ从块ID细化到块ID+字符区间 | **M84(a)直接落地**；审计叙事升级为字符级provenance；相对FActScore系=免费获得其需自建的provenance | **~一天工程**+快照测试更新；零推理成本 | 完全（=v2审计循环的下一次迭代：audit→fix→test） | 不提升原子性/跨域（另一条轴）；v2切分后子claim的span语义需定义（重构文本vs原文区间） | 1.7判读：match.span()是正则的结构性span优势 |

**判定**：

1. **性价比：C ≫ A' > A > B。** C是唯一同时满足"零推理成本不变+M84(a)落地+叙事增强"的路径，且延续仓库已验证的audit→fix→test循环（v2先例）；A'以最小风险试探教师分解价值（不动推理架构，E2实验设计可直接套用）；A须过两档基线+E2阴影才配作贡献；B域错配放弃。
2. **叙事：C胜出。** "domain grammar front-end + span provenance"把88§5宣称点（可审计确定性实现）从架构级升到字符级——与FICLE"判别式最好span"的结论呼应：**确定性前端天然是判别式定位器**（正则match即span判定），而LLM分解器是生成式（span需后验对齐）。"distilled claim segmenter"字面更新，但1.2判读显示trained claim切分器无主流先例=同时缺基线和缺方法合法性铺垫，加上E2的域绑定阴影——**建议降格为A'先行，若A'在crossdoc打开缺口再升格A**。这与88§5"不宣称分解是新贡献、宣称可审计确定性实现"的定调一致。

---

## 4. 仓库材料索引（本取证引用）

| 材料 | 路径 | 用途 |
|------|------|------|
| 88号（分解文献取证） | `docs/srs_project/88_claim_decomposition_literature.md` | 验证单元视角结论（三条件/Kontrast先例/(b)判定/§5定调），本文§2/§3引用 |
| 89号（归因单元取证） | `docs/srs_project/89_nli_attribution_survey.md` | FActScore无span局限、verdict≠span、定位是独立能力 |
| v1/v2/v3实现 | `algorithms/consistency/answer_claims.py`、`answer_claims_v2.py` | §2.1代码事实（含span现状：无） |
| 两档实测 | `data/gjb_438c/distillation/refactor_matrix_v1.json` | 0.8047/0.5109/0.7361 |
| v3档位契约 | `tests/test_v3_profiles.py`、`algorithms/consistency/verifier.py` PRESETS | crossdoc preset=sentence+dominant_70 |
| 分解审计/消融 | `tools/audit_claim_extraction.py`、`tools/eval_decomp_ablation.py`、`tests/test_answer_claims_v2.py` | v2缺陷驱动循环 |
| D1/E2蒸馏基础设施 | `tools/llm_teacher.py`、`tools/train_distilled_nli.py`、`paper/evaluation_tables.md` D1/E2节 | 路径A/A'复用度+域绑定风险 |
| EGT合成 | `algorithms/consistency/egt_synthesis.py`、`tools/build_egt_dataset.py` | 1.6同构+A'锚点 |
| MiniCheck精读 | `literature_survey/five_direction_method_survey_and_cascadeverify_v2_design.md` §1.1 | C2D/D2C+推理期分解消融 |
| FActScore/VERISCORE/SAFE条目 | `literature_survey/pair_classifier_sota_2023_2025.md` A3/A4/A6 | 1.1表 |
| FICLE精读 | `literature_survey/modular_verification_architecture_survey.md` E4 | 1.7 span判别式结论 |
| ContractNLI | 同上文献线§1.3（`five_direction…`） | 1.7 |
| OpenIE先验判断 | `literature_survey/agentic_rag_survey.md` L352 | 1.3/路径B风险 |
| Femmer需求气味 | `literature_survey/inconsistency_history_survey.md` | 1.5 |
| GJB规则库 | `knowledge/gjb_438c_rules_full.json` | 1.5合格性规定先例 |
| EGT文法定律（一代教训） | `docs/srs_project/77_master_consolidation.md` | 1.6/A'风险 |
| 聚合选型 | `docs/srs_project/50_support_recall_analysis.md` | §2.1 strict/dominant双档 |

## 5. 待核实清单

1. **D-FActScore**：EACL 2024、说话人归因机制、turn级定位细节——仓库零覆盖，引用前必核。
2. **Factcheck-GPT**：arXiv 2305.13534、正式venue（NAACL 2025 Findings?）、抽取变体消融细节——仓库零覆盖。
3. **SAFE**：arXiv 2403.18802、机制——沿89§5.4。
4. **OpenIE6**：AAAI 2020、英/西语支持——常识性记忆，作者列表需核对。
5. **SpanIE**：venue（ACL 2024/Findings/EACL?）、语料、中文支持（无）——仓库零覆盖。
6. **UIE**：EMNLP 2022（Baidu）、中文权重可用性、生成式span映射回原文机制——凭知识，引用前必核。
7. **ClaimBuster**：TKDE年份（2019/2020）与特征集——仓库零覆盖。
8. **CLEF CheckThat!**：各年度task结构（claim matching是2023 Task 2）——凭记忆。
9. **QuestEval**：EMNLP 2021、QG/QA模型配置——仓库零覆盖。
10. **ISO 29148**：atomic requirement定义的原文与章节号——凭记忆。
11. **requirement modularization**：近年论文存在性与出处——未核实，仅作方向性提及。
12. **"trained claim切分器无主流先例"**（1.2判读）：检索范围内结论，标"未见"而非"不存在"——若上溯knowledge editing/span-based IE邻域可能有边缘先例，路径A立项前应补一轮检索。
