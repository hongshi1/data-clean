# 21 · 三态一致性校验评测协议与 baseline 矩阵（answer vs SRS证据）

> **执行状态：历史协议草案，需按00与project_guide v5.0重新审定后方可作为正式实验协议。** 其基线和样本分组不自动继承为有效结果；当前主协议原则见 [00_requirements_and_route_overview.md](00_requirements_and_route_overview.md)。

> 日期: 2026-10-20 ｜ 类型: 评测协议设计 ｜ 状态: 设计稿（待用户裁定后实施）
> 前置: 当前定位：算法检测 answer/待校验条目 vs 解析后的 SRS 证据。正文、表格、图片是证据来源，不是互相比较的两端；模态转换和跨位置聚合在上游完成，校验阶段只做声明级文本比对。
> 旧评测: `docs/srs_project/family_eval_results.md`（pair 级 896 条六族×9 方法，bAcc 0.901）

---

## 0. 任务形式化

**输入**：QA 对 `(question, answer)` + 证据集 `E = {e_text, e_table, e_image}`（上游已声明化：表格 HTML 行解析 / VLM key_elements / 正文段落 → 文本声明，各带来源标注 §章节/表caption/图caption）。

**输出**：三态判定 `ŷ ∈ {support, refute, not_in_evidence}`：

| 态 | 中文 | 定义 | 与旧二分类的关系 |
|---|---|---|---|
| **support (S)** | 支持 | 证据明确证实 answer 的声称（含领域等价豁免：同值异表面、单位换算、同集重排） | ≈ consistent |
| **refute (R)** | 反驳 | 证据与 answer 声称矛盾：值突变、名称冲突、条目多余（answer 说无而证据有） | ≈ inconsistent |
| **not_in_evidence (N/NIE)** | 证据未涵盖 | 证据中找不到 answer 声称的内容：检索失败、提取失败、实体不存在于证据 | **旧协议无此态**（被迫二选一） |

标签体系与文献对齐：FEVER 的 SUPPORTS/REFUTES/NEI、ClaimVer/NLI 族的 supported/refuted/NEI（`20_verification_operations_survey.md` ④族）、项目语义层既定的 entailed/contradicted/baseless 三态（`project_guide.md:393`）。统一采用 **support / refute / not_in_evidence**。

**三态必要性的直接实证（A1/A3 端到端）**：
- A1 的 44 个"错例"全部是 QA 生成器对象错位（Actor 名当功能名）→ X 真的不在表/图中 → 系统判"证据不支持"**行为正确**，但被全 support 的二分类金标记为误报（`qa_e2e_a1.json`：表侧缺失 64 / 图侧缺失 125，quote 通道 289 + NLI 57）。二分类协议在惩罚正确的弃权。
- A3 的 223 条负例本质是"正文未提及"→ NIE，不是矛盾（正文里没有冲突声称，只是找不到）。二分类把它当 inconsistent 混淆了"矛盾"与"缺证据"两个语义不同的错误。

---

## 1. 指标体系

### 1.1 主指标：三态 macro-F1（macroF3）

记混淆矩阵 `M[i,j] = #{ŷ=i, y=j}`（i=预测，j=真值），三类 c ∈ {S, R, N}：

$$P_c = \frac{M[c,c]}{\sum_j M[c,j]}, \qquad R_c = \frac{M[c,c]}{\sum_i M[i,c]}, \qquad F1_c = \frac{2P_cR_c}{P_c+R_c}$$

$$\boxed{\;\mathrm{macroF3} = \frac{1}{3}\left(F1_{\mathrm{sup}} + F1_{\mathrm{ref}} + F1_{\mathrm{nie}}\right)\;}$$

**论证（为什么是 macroF3 而非其他候选）**：

| 候选 | 否决理由 |
|---|---|
| 三态 accuracy | 失衡敏感——合成 refute 源注入量可任意改变先验 π_R，跨来源/跨配置的 acc 不可比（旧协议弃 F1 保 bAcc 的同一逻辑在三态的推广） |
| macro-recall（=3bAcc） | 不惩罚滥报：refute 是高代价强判定（冤枉 answer 造假），全报 refute 的 recall=1 却 precision=π_R；F1 同时钳制两个方向 |
| 折叠成二分类（NIE 并入 S 或 R） | 两个方向都丢信息：NIE→S 则丢"弃权能力"度量（A1 44 错例的教训）；NIE→R 则把"证据不足"与"证据矛盾"混为一谈（A3 223 负例的教训）。折叠仅作诊断视图（§1.3） |
| 代价敏感矩阵 | 代价权重主观，审稿风险；用 P/R 分报告代替 |

**退化参考线**（报告必须明示，类比旧协议"全报单类 bAcc=0.5"）：
- 全报 NIE：`macroF3 = 2π_N / (3(1+π_N))`。π_N=0.3 → **0.154**；π_N=0.4 → 0.190。一个检索全失败、永远弃权的系统在主指标上被充分惩罚。
- 全报 refute：同式代入 π_R。
- 均匀随机：期望 ≈ 0.11–0.15（随分布）。

### 1.2 次指标：3bAcc（与旧 bAcc 直接可比）

$$\mathrm{3bAcc} = \frac{1}{3}\left(R_{\mathrm{sup}} + R_{\mathrm{ref}} + R_{\mathrm{nie}}\right)$$

bAcc 的三态自然推广（二分类时 `3bAcc ≡ bAcc`），用于新旧能力对照。每态 P/R/F1 全量报告（诊断退化模式，见报告表 1b）。

### 1.3 两个折叠二分类（诊断视图，非主指标）

| 折叠 | 正类 | 指标 | 回答的问题 |
|---|---|---|---|
| **矛盾折叠** | refute（NIE∪S 为负） | `bAcc_ref = ½(R_ref + R_{¬ref})`，R_¬ref = (M[S,S]+M[N,S]+M[S,N]+M[N,N]) / (n_S+n_N) | "矛盾检出"这一旧 Task 1 核心能力在新形态下是否保住——与 family_evalset 的 bAcc 语义对齐 |
| **证据性折叠** | NIE（S∪R 为负） | `bAcc_nie = ½(R_nie + R_{¬nie})` | "有据可查"判定——RAG 忠实性（grounding）能力 |

### 1.4 item 级定位指标（A3 缺失清单）

answer 声称多项内容（如"表格 8 个功能正文全提及"）时，逐项 grounding，缺失项集合 `Ĉ_mis` vs 金标 `G_mis`：

$$P_{\mathrm{mis}} = \frac{|\hat{C}_{\mathrm{mis}} \cap G_{\mathrm{mis}}|}{|\hat{C}_{\mathrm{mis}}|}, \quad R_{\mathrm{mis}} = \frac{|\hat{C}_{\mathrm{mis}} \cap G_{\mathrm{mis}}|}{|G_{\mathrm{mis}}|}, \quad F1_{\mathrm{mis}} = \frac{2P_{\mathrm{mis}}R_{\mathrm{mis}}}{P_{\mathrm{mis}}+R_{\mathrm{mis}}}$$

现状基线：R_mis=0.297（A3，QA 生成器参考正文范围不可精确重建——见 §2.4 重标协议）。定位型指标与判定型指标分开报告（对应 Task 2 QA 类型中的判别型/定位型）。

### 1.5 管线分层指标（端到端 ≠ 校验器）

新形态是三段管线（锚点检索 → 特征提取 → 声明级校验），必须分层报告，否则校验器能力被上游误差污染：

| 指标 | 定义 | 现状值 |
|---|---|---|
| **ESR** 证据齐备率 | 检索+提取成功（证据声明非空）的条目占比 | A1: 346/346=1.00；A3: 304/344=0.88 |
| **CVacc** 条件判定正确率 | P(ŷ=y \| ESR)，证据齐备子集上的 acc | A1: 0.873；A3: 0.97——旧端到端数字实为此指标 |
| **macroF3_e2e** | 全量（含证据缺失条目）的三态主指标 | 新协议主成绩 |

**协议决策（证据缺失 → 强制 NIE）**：ESR 失败的条目系统唯一合理输出是 NIE（与 RAG 检索失败→NEI 一致）。金标侧对应决策见 §2.4（可及范围协议）。

### 1.6 统计检验

- 总体：2000 次 bootstrap 的 95% CI（macroF3 上）。
- 两方法配对比较：**Stuart-Maxwell 检验**（三态边际齐性，McNemar 的多类推广）；分态诊断用每态二值化的 McNemar（沿用 `mcnemar_p`）。

---

## 2. 三态金标构建（数据集 v1）

### 2.1 来源 × 模态组合 × 三态分布

| 来源 | n | 模态组合 | 三态构造 | 质量动作 |
|---|---|---|---|---|
| ① A1 QA 真实 | 346 | 文本-表格+图片 | S×~302 + **N×~44（对象错位重标）** | 44 条人审确认 + 双 LLM 复核抽样 10% |
| ② A3 QA 真实 | 344 | 文本-表格+文本 | S×91 + N×223（"正文未提及"=NIE） | N 金标按 §2.4 可及范围重标 |
| ③ QA 合成（A1v 305 + 假设类 1105） | ~700 入集 | 文本-表格(+图) | R（**需变异落地改造**，见 §2.3） | 变异真实化 + 源级去重 |
| ④ family_evalset 反推 | 896 | 文本-文本（声明对） | 类型→态映射（§2.5） | 冻结快照 + 映射规则回归锁 |
| ⑤ Visio 结构对 | 26 | 文本-图片（结构） | P4 删除节点→N，恒等→S | 已冻结 |

总量 ~2300，三态先验目标 S:R:N ≈ 40:35:25（各来源内部均衡构造，避免合成源倾斜先验——macroF3 对先验稳健，但 P/R 分报告仍需注明）。

**分模态组合的报告维度**：文本-文本（④+②的正文侧）/ 文本-表格（②③表侧）/ 文本-图片（①⑤）/ 表+图组合（①全形态）。**分来源**：QA 真实 / QA 合成 / 金标反推。所有方法均吃"声明化证据"（模态转换在上游），模态差异体现为上游转换质量——评测中作为报告维度而非方法维度；图片侧加 oracle 对照（VLM key_elements vs 人工标注图元素）测提取上界。

### 2.2 A1 的 44 条重标（金标纠错）

QA 生成器把 Actor 名当功能名 → X 不在表/图证据中 → 真值应为 **N** 而非 S。重标流程：表侧缺失∪图侧缺失的条目（64+125 有重叠，实际 44 条判错项）→ 人审确认"证据中确实无该实体" → 改标 N。**报告同时给重标前后两套数字**（旧二分类协议下系统被冤枉 −12.7pp，新协议下应回收）——这本身是论文中"二分类协议不可用"的论据。

### 2.3 合成 refute 源的变异落地（A1v 陷阱）

A1v 的负例是**文字假设**（"若表格误写为…"）而表格实际未变异——直接使用会让系统看到真实未变异证据判 S，对 gold R 全漏。改造为两个正交子方向（各半配额）：

| 子方向 | 构造 | 语义角色 | 对应文献 |
|---|---|---|---|
| **E 侧变异** | 对证据声明注入表面变异（错字/值突变/单位异表面），answer 保持正确声称 | 检测"证据有错"（文档校对方向） | family_evalset synth_s1 复用 |
| **A 侧变异** | 对 answer 注入变异（虚构值/错误名称），证据保持真实 | 检测"answer 不忠实"（RAG 忠实性方向） | FActScore/RAG 忠实性 |

沿用 synth_s1 的确定性变异算子 + 三表面模板（T1/T2/T3）+ 源级去重（每源每标签每子方向 1 条）。E 侧直接复用 family_evalset 合成资产；A 侧为新增算子（QA 对的 output 变异）。

### 2.4 可及范围协议（A3 教训的协议化）

A3 的 R_mis=0.297 根源：QA 生成器标注"缺失"时参考的正文范围 ≠ 系统可检索范围（父树/兄弟节点不可精确重建）。三态金标统一协议：

- **strict（主协议）**：真值以"系统可及证据范围"（当前 chunk 索引：锚点 caption+section 可检索的块）为证据边界，边界外声称 → N。
- **full-doc（参考协议）**：以全文档为证据边界，报参考列。两档差异 = 检索边界的敏感度分析。

### 2.5 family_evalset 类型→态映射（金标反推规则）

premise = 证据声明，hypothesis = answer 声称（方向固定：P=evidence, H=answer）：

| 旧族/类型 | 旧标签 | 新态 | 理由 |
|---|---|---|---|
| A/D/F 突变值（PARAM-01/03、TERM-01、ENUM-01） | inconsistent | **R** | 证据与声称值/成员冲突 |
| A/D/F 同值异表面（PARAM-02、TERM-02、ENUM-02、F 全部） | consistent | **S** | 领域等价豁免 |
| B 顺序/E 合规 | inconsistent | **R** | 顺序颠倒/合规冲突=矛盾 |
| C 缺失类（TABLE_ITEM_MISSING/ACTOR_MISSING/STEP_MISSING/DIAGRAM_EXTRA） | inconsistent | **N** | 一方有一方无=证据未涵盖（**这是 C 族在二分类下 0.824 上限的结构性原因之一**：GLM 把良性省略判矛盾、我方 STEP_MISSING 0.618——缺失≠矛盾） |
| C 值冲突类（其余 55） | inconsistent | **R** | 跨模态内容冲突 |
| ②' F 残差（同声称异表面） | consistent | **S** | 等价复述 |

反推后估算：S≈394+52、R≈286、N≈216（896 内）——**族×态交叉验证映射正确性**（人工抽检 10%）。family_evalset_v2 增列 `tri_label`，二分类列保留兼容。

---

## 3. baseline 矩阵迁移

### 3.1 迁移总表

| # | baseline | 类别 | 三态机制 | 适配要点 |
|---|---|---|---|---|
| B1 | mDeBERTa ZS | 零样本 NLI | **entail/neutral/contradict → S/N/R 直接映射**（天然三分类头） | P=evidence 声明序列化，H=answer(+question)；max_length 128→512（evidence 长输入），超长滑窗取含 answer 实体的块 |
| B2 | Erlangshen ZS | 零样本 NLI | 同上（contra_idx=0, entail/neutral 索引映射） | 同 B1 |
| B3 | v12 NLI | 领域微调 | **方案 a**：三分类头重训（三态 QA 对微调，同款协议）；**方案 b**：NIE 门控 + 二分类（先 grounding 判 N，非 N 再判 S/R）。报告 a，b 作为消融 | 二分类头在 N 上语义未定义——重训是干净路线 |
| B4 | TSRCDF-SS | 领域训练 | 同 B3 方案 b（双编码器对 (P,H)，无 N 训练信号，门控前置） | 保持与 v12 同款协议对照 |
| B5 | GLM-5 ZS | LLM | 三态 prompt（§3.2），temp 0.1，缓存接口 | 全量（旧评测是抽样 180，新集 ~2300 规模下分层抽样 300 或预算内全量） |
| B6 | GLM-5 + κD | LLM | 三态 prompt + 领域等价约定段（同/异表面豁免） + "无证据判 N"指令强化 | 对照 κD 知识在三态下的边际贡献 |
| B7 | QG-QA | 生成式校验 | **天然三态**：问题模板→证据中抽答案→抽不到=N / 值不同=R / 相同=S | DROP round-trip 本就是三态逻辑，旧二分类实现反而砍掉了 N |
| B8 | Z3-SMT | 形式化 | 声明集形态：answer 声明编译为约束，在 evidence 声明集上**匹配→SAT/UNSAT 判定（S/R），无可匹配声明→N** | 旧 `_claims` 解析复用；N 判据=answer 声明的量纲/属性在 evidence 中无对应锚点 |
| B9 | 集合比对 | 结构 | 实体集差 + 方向规则：answer 有而 evidence 无→N；answer 否认而 evidence 有→R；同集→S | 表格/图片声明集 |
| B10 | LCS/编辑距离 | 序列/词面 | 序列差→R（κ3 盲区保留）；无法对齐（无公共项）→N | 词典消解保留 |
| B11 | GJB 规则引擎 | 规则 | 规则触发→R；未触发且可对齐→S；无可检查对象→N | 检测可溯源规则编号 |
| **B12** | **BM25 grounding**（新增） | 检索 | answer 实体/值在 evidence 中检索：未命中→N；命中且词面同→S；命中但值冲突→R | RAG naive 基线；旧评测被移出矩阵（表面相似≠一致性）——**新形态下 grounding 是同任务**，重新入矩阵并预计其在 S/R 区分上失效（实验论点） |
| **B13** | **BGE embedding 匹配**（新增） | 检索 | sim < τ→N（τ=0.78 已校准）；≥τ→S；值抽取冲突→R | 语义相似≠一致：预计同值异表面 S 上强于 BM25、值突变 R 上弱（"19 种"vs"38 种"sim≈0.99） |
| **B14** | **SatLM**（LLM 编译→Z3） | LLM+形式化 | LLM 把 (answer, evidence) 编译为 SMT → 三态同 B8 | 已实现待跑（旧报告 §7），直接迁移 |
| Ours | v4.3 三态化 | 我方 | **NIE 门控前置**（锚点 grounding：answer 实体在 evidence 声明中无锚点→N）→ 有锚点走 v4.3 二分类（consistent→S / inconsistent→R） | 见 §4 |

### 3.2 GLM 三态 prompt 草案

```
SYS: 你是SRS文档的答案核验专家。给定问题、候选答案和证据声明（文本段落/
表格行/图元素，已统一为文本，各带来源标注），判定答案与证据的三态关系。

PROMPT:
证据声明：
{evidence_claims}   # 按模态分组序列化：[表3|§3.2.1.2|图3] 前缀，每模态限k条

问题：{question}
候选答案：{answer}

判定（三选一）：
- support: 证据明确证实答案的声称
- refute: 证据与答案声称矛盾（值/条目/名称冲突）
- not_in_evidence: 证据中找不到答案声称的内容（既未证实也未反驳）

只回答JSON: {"verdict": "...", "evidence_refs": [...], "reason": "..."}
```

KD 变体追加（沿用旧 SYS_KD 的 κD 域约定）：单位换算/同义算子/同集重排视为 support（防把 F 类误报为 refute）；"证据未涵盖≠矛盾，宁可判 not_in_evidence"。

### 3.3 每模态组合的 baseline 分派

所有文本形态方法全模态可跑（模态转换在上游）；受限项标注原因：

| 模态组合 | 全覆盖 | 受限/特化 |
|---|---|---|
| 文本-文本 | B1–B13 全部 | — |
| 文本-表格 | B1–B13 | B8/B9/B11 最适配（结构化声明） |
| 文本-图片 | B1/B2/B5/B6/B12/B13 + B9(Visio) | B8/B10/B11 不适用（图声明无算子/序列/规则形态）；B12/B13 吃 VLM key_elements |
| 表+图组合 | B1/B2/B5/B6 + Ours | 单证据方法取拼接证据 |
| oracle 对照 | — | 图片侧人工图元素 vs VLM key_elements（提取上界差） |

---

## 4. 我方方法（v4.3 → 三态）迁移

```
answer + evidence声明集
  → [0] NIE门控（锚点grounding）: answer实体/值在evidence声明中无锚点 → N
       （A1 44错例的"表侧缺失/图侧缺失"信号即此门控的雏形；
        doc_absence通道本就是文档级缺失检测器 → 输出改N）
  → [1] v4.3 六通道二分类（quote/numeric/term/enum/count/numbered/...）
       consistent → S；inconsistent → R
  → [2] NLI兜底（v12三态头或二分类+门控）
```

通道级三态化映射：quote/enum 命中恒等→S；quote/enum 集合差→按缺失方向判 N（evidence 缺 answer 声称的项）或 R（answer 否认 evidence 有的项）；numeric 值冲突→R、值等价→S；doc_absence→N。**这是设计增量**：现有通道的"缺失"信号在二分类下被迫报 inconsistent（C 族 STEP_MISSING 0.618 的结构性原因），三态化后应显著回收。

---

## 5. 与旧评测（family_evalset）的关系：三层并存，非替代

```
L1 内核级: family_evalset_v1(二分类) ──反推映射──> family_evalset_v2(+tri_label)
           保留: 校验器组件能力评测 + 通道消融 + 回归锁投资
L2 端到端级: tri_state_evalset_v1(新, ~2300条) ──> 本协议主实验
L0 (废弃): qa_e2e单跑 acc(A1 0.873/A3 0.970) ──被吸收为──> L2 的管线基线行(表8)
```

**保留 L1 的四理由**：(1) 端到端误差混杂上游（检索/提取），L2 无法归因校验器本身；(2) 通道消融（−numeric→−0.108 等）必须在声明级干净数据上做；(3) 896 条冻结快照/回归锁/MANIFEST 投资不可弃；(4) 论文需要组件级证据支撑"领域知识条件化分派"论点。

**迁移方案**：
1. family_evalset_v2：加 `tri_label` 列（§2.5 映射），二分类列保留；`tests/test_family_evalset.py` 快照更新 + MANIFEST 重登（`build_data_manifest.py`）。
2. 旧报告 `family_eval_results.md` 定位改为"组件级评测报告（v2 三态标签反推）"，论文中为消融/内核分析章节。
3. L2 为主表实验；A1/A3 的 0.873/0.970 转为表 8 的管线分层基线（CVacc 指标），不再作为独立成绩引用。
4. `tools/eval_qa_e2e.py` 归档（其 A1/A3 逻辑由新评测入口吸收）。

---

## 6. 新实验报告表格草案（`tri_state_eval_results.md`）

| 表 | 内容 | 行 × 列 |
|---|---|---|
| **表0** 数据集构成 | 来源×模态组合×三态分布 | 来源 5 行 × (n, 模态, S/R/N 计数, 质量动作) |
| **表1** 总表·主指标 | 全方法对比 | 方法(Ours+B1–B14) × [F1_S, F1_R, F1_N, **macroF3**, 95%CI, 3bAcc]，参考行：NIE 退化线/全报 refute 线 |
| **表1b** 每态 P/R 诊断 | 退化模式 | 方法 × [P_S,R_S,P_R,R_R,P_N,R_N]（诊断"全报警/全弃权"失效形态） |
| **表2** 折叠与旧能力对照 | 新旧桥接 | 方法 × [bAcc_ref, bAcc_nie, 旧 family bAcc 列]——"保住旧矛盾检出 + 新增弃权能力" |
| **表3** 分模态组合 | 模态泛化 | 模态组合(文本-文本/文本-表格/文本-图片/表+图) × 方法 × macroF3 + VLM vs oracle 图侧对照 |
| **表4** 分来源 | 分布鲁棒性 | 来源(QA真实/合成/金标反推) × 方法 × macroF3 + A1 重标审计小节（44 条处置前后） |
| **表5** 通道检出（我方） | 可解释性 | 通道(NIE门控/quote/numeric/enum/...) × [命中率%, 三态正确率, 前置阶段] × 模态 |
| **表6** 消融 | 组件贡献 | full / −NIE门控 / −quote / −numeric / −enum / 纯NLI(三态头) / 二分类形态(旧) × macroF3（L1+L2 双列） |
| **表7** 定位型 | item 级 | A3 缺失项 P_mis/R_mis/F1_mis × 方法（现基线 R=0.297） |
| **表8** 端到端归因瀑布 | 管线分层 | 阶段(定位失败→提取失败→校验错误) × [率, 条件指标] + ESR/CVacc/macroF3_e2e（A1/A3 旧数字在此行） |
| **表9** 效率 | 成本 | 方法 × [耗时, NLI/LLM 调用量, 缓存命中率] |

统计：表1 报 bootstrap 95%CI；表2/3/4 关键对比报 Stuart-Maxwell + 每态 McNemar。

---

## 7. 实施清单

| 步骤 | 产出 | 依赖 |
|---|---|---|
| 1 | `tools/build_tri_state_evalset.py`（五源汇聚 + A1 44 条重标 + 变异落地 + 类型映射） | 人审 44 条 |
| 2 | `family_evalset_v2.json`（+tri_label）+ 快照/回归锁更新 | §2.5 映射抽检 |
| 3 | `algorithms/consistency/baselines_tri.py`（B7–B13 三态包装器；B12/B13 新增） | — |
| 4 | `tools/eval_glm_tri_sample.py`（B5/B6 三态 prompt + 缓存） | — |
| 5 | v12 三态头微调（B3 方案 a）+ Ours NIE 门控接入 checker | 三态训练对 |
| 6 | `tools/eval_tri_state.py`（评测入口：表 0–9 + CI + Stuart-Maxwell） | 1–5 |
| 7 | `docs/srs_project/tri_state_eval_results.md`（首版报告） | 6 |

风险与预判：(a) 三态训练数据仅 ~2300 条，v12 三态头可能欠拟合 N 态——先跑方案 b（门控+二分类）保底；(b) 合成 R 源的表面变异与真实 R 分布差异（QA 真实源中 R≈0）——表 4 分来源即为该风险的显式度量；(c) 44 条重标引入人审主观性——保留重标前后双版本数字。
