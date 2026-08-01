# 三层不一致检测：挑战、范围与边界深度分析

> 数据来源：`evaluation_results.json`、`gold_standard/_summary.json` + 3 份文档级 Gold Standard、`consistency_reports/*_report_v2.json`（3 份）、`knowledge/gjb_438c_rules_full.json`（120 条）、`srs_consistency_checker_v2.py`、`srs_eval.py`、`srs_gjb_compliance_scan.py`、`gjb_rules_gap_analysis.json`
>
> 评测日期：2026-07-29 ｜ Checker v2.2 ｜ 3 份文档（battery / compiler / scheduler）

---

## 0. 总体评测画像（先看全局）

| 指标 | 值 | 解读 |
|------|-----|------|
| GT 总数 | 22（8 真矛盾 + 14 正值确认一致） | 正值占 64%，说明 Gold Standard 以“确认一致”为主，真矛盾样本偏少 |
| TP | 6 | |
| FP | 7 | **全部集中在 logic 层** |
| FN | 2 | 1 semantic + 1 logic |
| TN | 14 | |
| Precision | 0.4615 | 低，主要被 logic 层 7 个 FP 拖累 |
| Recall | 0.75 | 中等 |
| F1 | 0.5714 | |

### 分层数据（核对原始 `evaluation_results.json`）

| 层 | TP | FP | FN | TN | P | R | F1 | 结论 |
|----|----|----|----|----|---|---|----|------|
| **语法 syntax** | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 | **完全空白**：既无检测器又无 GT |
| **语义 semantic** | 2 | 0 | 1 | 11 | 1.0 | 0.667 | 0.80 | 高精度、漏 1 个 |
| **逻辑 logic** | 4 | 7 | 1 | 3 | 0.364 | 0.80 | 0.50 | **FP 爆炸**，是当前最大瓶颈 |

> **重要事实校正**（对提问前提的核实）：
> - 提问中“语义层 7 个 FP”与实际不符。**7 个 FP 全部在 logic 层**，semantic 层 FP=0。
> - 提问中“逻辑层 1 个 FN（scheduler 忙等待）检不到”与实际不符。**scheduler 忙等待是 TP**（scheduler GT-002 ↔ ISSUE-001，已正确检出）。logic 层真正的 FN 是 **battery GT-008 跨文档冲突**（battery CPU<5% vs scheduler CPU<10%）。
> - 提问中“2 个 FN 在语义层”与实际不符。2 个 FN = 1 semantic（battery GT-007 表格 OCR 断裂）+ 1 logic（battery GT-008 跨文档）。

---

## 1. 语法层（syntax）：完全空白

### 1.1 现状：TP=FP=FN=TN=0 的根因

**答案是“双重缺失”——既没有检测器，也没有 GT。**

**(a) 没有检测器。** `srs_consistency_checker_v2.py` 的 `check_document()` 只跑了 4 个检查：
1. `check_same_value_consistency` → semantic
2. `check_text_table_consistency` → semantic
3. `check_logic_consistency_z3` → logic
4. `check_cross_section_consistency` → logic

没有任何函数输出 syntax 层的 `check_type`。`srs_eval.py` 的 `CHECK_TYPE_TO_LAYER` 定义了 5 个 syntax 类型（`missing_qualification_entry` / `missing_text_section` / `missing_table` / `missing_chapter` / `structure`），但 **没有任何检测器产生这些类型**，映射表形同虚设。

**(b) 没有 GT。** Gold Standard 的 22 条 GT 类型分布为：`same_param_same_value`(10)、`logic_satisfiable`(3)、`text_table_conflict`(3)、`logic_contradiction`(2)、`logic_incomplete`(1)、`logic_unsatisfiable`(1)、`same_value_diff_semantics`(1)、`cross_document_conflict`(1)。`GT_TYPE_TO_LAYER` 把它们全部映射到 semantic/logic，**没有任何一条映射到 syntax**。所以即使有检测器，也无 GT 可对齐。

### 1.2 当前能检测什么
- **零**。语法层在端到端评测管线中完全不产生信号。

### 1.3 不能检测什么
GJB 438C 的 120 条规则中，与语法/格式/结构直接相关的：
- **format: 14 条**（页号唯一、罗马数字/阿拉伯数字分段编号、附录大写字母标记、条编号格式…）
- **structure: 24 条**（文档构成=封面+修改页+目录+正文+附录、每附录须在正文引用、目录须含章/条/附录编号…）

合计 **38 条（占 120 条的 32%）在当前评测中零覆盖**。

### 1.4 被忽视的事实：合规扫描器已存在但未接入
`srs_gjb_compliance_scan.py` **已经实现了 7 类语法检查**：
- `check_section_completeness`（章节完整性）
- `check_requirement_ids`（需求唯一标识）
- `check_qualification_methods`（合格性方法）
- `check_traceability`（可追踪性）
- `check_numbering_format`（编号格式 X.Y.Z）
- `check_table_completeness`（表格完整性）
- `check_content_fields`（内容字段）

但它**独立运行、输出不进入 `consistency_reports/`，也不被 `srs_eval.py` 消费**。这是当前最大的“已建未用”缺口。

### 1.5 核心挑战
1. **管线断裂**：合规扫描结果未接入一致性检测→评测闭环。
2. **GT 缺失**：需人工标注语法层正/负样本（如“缺第 4 章”“编号非 X.Y.Z”）。
3. **GJB 规则可判定性**：14 条 format + 24 条 structure 中，约 28 条可由结构化解析（MinerU 已提供 section tree）+ 正则判定；约 6 条涉及“适用时”等模糊条件需人工/LLM 裁定。

### 1.6 GJB 规则覆盖率（语法层）
| 类别 | 总数 | 已自动化（合规扫描） | 接入评测 | 可自动化潜力 |
|------|------|----------------------|----------|--------------|
| format | 14 | ~5（编号/页号/附录标记） | ❌ 未接入 | ~10 |
| structure | 24 | ~6（章节完整性/文档构成） | ❌ 未接入 | ~18 |
| **小计** | **38** | **~11** | **0** | **~28** |

---

## 2. 语义层（semantic）：高精度但漏报 1 个

### 2.1 现状：TP=2, FP=0, FN=1, TN=11

这是三层中**精度最高**的一层（P=1.0），但召回有缺口（R=0.667）。

### 2.2 当前能检测什么（TP=2，均来自 compiler_srs）
两条 TP 都是 `empty_table_placeholder`（占位符检测），由 `check_text_table_consistency` + `PLACEHOLDER_CELLS` 集合实现：

| GT | 检测 | 内容 | 检测器 |
|----|------|------|--------|
| compiler GT-004 | ISSUE-001 | 4 合格性规定表全为占位符（“合规性方法/级别/章节号 3.3.1”） | 占位符集合匹配 |
| compiler GT-005 | ISSUE-007 | 5 需求可追踪性正/逆向表全为占位符 | 占位符集合匹配 |

**结论**：语义层目前**唯一有效的“真矛盾”检测能力 = 表格占位符/空表识别**。

### 2.3 不能检测什么

**(a) FN=1：battery GT-007（text_table_conflict，OCR 导致表格断裂）**
> 4 合格性规定表中“SOC 状态更新”行的合格性方法列被 OCR 解析为两行（“单元测”和“试+对比验证”），导致单元格断裂、合格性方法值不完整。

**为什么检不到**：占位符检测器（`_is_placeholder_cell`）只识别“空 / 已知占位符词”，无法识别“**单元格被 OCR 物理拆分成两行**”这种结构性损坏。断裂后的两个片段“单元测”“试+对比验证”都不是占位符词，于是通过检查。这是一个**与占位符检测完全不同的失败模式**——不是“内容缺失”而是“结构损坏”，需要单元格级结构完整性校验（行/列对齐、跨行检测、单元格合并还原）。

**(b) 10 条 `same_param_same_value` 全是正值（TN），没有任何 `same_param_diff_value` 真矛盾 GT。**
意味着：同值一致性检测器（`check_same_value_consistency`）的“**检出真值冲突**”能力**从未被测试过**。它正确地没对 10 条一致的正值报警（贡献 10 个 TN），但它能不能抓到“同一参数两处不同值”完全没有 GT 验证。这是一个评测盲区。

**(c) `same_value_diff_semantics`（同值不同义）无检测器。**
scheduler GT-005（超时阈值 25ms 与调度周期 25ms 数值相同但语义不同）是正值 TN，但系统没有任何机制能区分“同值同义”与“同值不同义”——这需要语义角色标注，当前缺失。

### 2.4 为什么 FP=0
语义层只有两个检测器，其中 `same_value_consistency` 在值一致时“不报”（v2 修复项#1/#3），只有值不一致才报 HIGH；而 GT 中同参数都是一致的，所以它一次都没触发。`text_table_consistency` 的占位符集合非常specific（精确匹配“需求名称/合格性方法”等词），误报率极低。**FP=0 是“检测器保守 + GT 无值冲突样本”共同作用的结果，不代表检测能力强。**

### 2.5 核心挑战
1. **表格结构损坏检测缺失**：OCR 引起的单元格分裂/合并/错位无法识别（GT-007）。
2. **值冲突召回未被测试**：缺 `same_param_diff_value` GT，同值检测器的真正抓错能力未知。
3. **语义角色区分缺失**：同值不同义（25ms 作为周期 vs 作为阈值）无法判定。
4. **检测器种类少**：语义层实质只有“值比较 + 占位符”两种，覆盖面窄。

### 2.6 GJB 规则覆盖率（语义层）
GJB 的 content(53) + parameter(8) + interface(21) = 82 条偏语义。
- parameter(8)：数值比较覆盖 ~6 条（响应时间/吞吐/精度/容量等数值参数的跨章节一致性）。
- content(53)：表格完整性/占位符覆盖 ~5 条；需求唯一标识覆盖 ~2 条；其余 ~46 条（接口字段完整性、可测试性描述方式、保密性/安全性需求等）**未自动化**。
- interface(21)：字段提取覆盖 ~3 条；~18 条需深度语义理解，未自动化。
- gap_analysis 显示总体覆盖率 45.2%（33/73 条款），其中 33 条完全缺失、12 条不精确。

| 类别 | 总数 | 已自动化 | 可自动化潜力 |
|------|------|----------|--------------|
| content | 53 | ~7 | ~30 |
| parameter | 8 | ~6 | ~6 |
| interface | 21 | ~3 | ~12 |
| **小计** | **82** | **~16** | **~48** |

---

## 3. 逻辑层（logic）：FP 爆炸——当前最大瓶颈

### 3.1 现状：TP=4, FP=7, FN=1, TN=3

精度仅 0.364（7 个误报 vs 4 个真报），是拉低整体 F1 的主因。但需区分**两种检测器**：

| 检测器 | TP | FP | 精度 | 来源 |
|--------|----|----|------|------|
| **Z3 形式化求解**（`logic_unsatisfiable`） | 1 | 0 | **1.00** | `check_logic_consistency_z3` |
| **LLM 跨章节**（`cross_section_*`） | 3 | 7 | **0.30** | `check_cross_section_consistency` |

> **关键发现：FP 100% 来自 LLM 跨章节检测；Z3 检测零误报。** 这直接指明优化方向。

### 3.2 当前能检测什么（TP=4）

| GT | 检测 | 类型 | 检测器 | 内容 |
|----|------|------|--------|------|
| compiler GT-003 | ISSUE-002 | `logic_unsatisfiable` | **Z3** | 三阶段各≤5s 串行=15s > 总编译≤10s，Z3 求出反例 |
| compiler GT-001 | ISSUE-003 | `cross_section_declaration_contradiction` | LLM | 3.1 声明“单一状态” vs 3.1.2/3.1.3 列出维护/调试状态 |
| compiler GT-002 | ISSUE-004 | `cross_section_promise_implementation_mismatch` | LLM | 1.2 承诺 6 项功能 vs 3.2 仅定义 3 项 |
| scheduler GT-002 | ISSUE-001 | `cross_section_policy_contradiction` | LLM | 3.4.1 允许“忙等待”降级 vs 3.12 禁止忙等待 |

Z3 擅长：**可量化的算术不可满足**（时间求和超限）。
LLM 擅长：**显式文本对立**（声明 vs 列举、承诺 vs 实现、允许 vs 禁止）——当矛盾是“字面直接冲突”时 LLM 有效。

### 3.3 不能检测什么

**(a) FN=1：battery GT-008（cross_document_conflict，跨文档）**
> battery_srs 3.10.2 声明电池模型 CPU 占用率低于 5%（25ms 周期）；scheduler_srs 3.10.2 声明 CPU 占用率不超过 10%（含电池模型计算）。两文档对电池模型 CPU 测量基准不一致。

**为什么检不到**：`check_document()` 是**逐文档独立运行**的（`for doc_name in docs`），每个文档只加载自己的 constraints/sections。Z3 和 LLM 检测都只看到单一文档的约束，**没有任何跨文档约束关联机制**。要检出此矛盾，需要：
- 识别两文档共享实体（“电池模型”同时出现在 battery_srs 和 scheduler_srs）；
- 把两文档的相关约束放进同一求解/比较上下文；
- 识别“基准不一致”（5% 是模型自身 vs 10% 是含模型总量）这种语义级冲突。

当前架构三条件全无。

### 3.4 7 个 FP 逐一剖析（全部来自 LLM 跨章节检测）

| # | 文档 | ISSUE | 检测类型 | LLM 的指控 | 为什么是误报 |
|---|------|-------|----------|-----------|--------------|
| 1 | battery | 001 | declaration_contradiction | `battery_step(double I_out, double dt)` vs `battery_step(I_out)` 签名不一致 | **简写 vs 形式签名**：3.3.1 的 `battery_step(I_out)` 是叙述性简写，3.4.2 是正式 C 签名；LLM 不区分“叙述简写”与“声明” |
| 2 | battery | 002 | policy_contradiction | “25ms 固定步长 + DT=0.025” vs `dt` 作为输入参数 | **默认值 vs 可配置**：有 `dt` 参数不代表步长可变，可设默认值=0.025；LLM 把“有参数”等同于“可变策略” |
| 3 | battery | 003 | declaration_contradiction | 3.2.5 输入只列 `I_out` vs 3.4.2 要求 `I_out+dt` | 与 #1 同族，功能描述省略次要参数 ≠ 接口矛盾 |
| 4 | compiler | 005 | policy_contradiction | 3.12“无特殊设计约束” vs 3.9“须用 C/C++” | **模糊限定词**：“无特殊设计约束”是软表述，语言要求是否算“特殊”取决于作者意图；LLM 把任何文字张力都判为矛盾 |
| 5 | compiler | 006 | value_contradiction | 最低内存 512MB vs 编译占用≤500MB | **最低配置 vs 实际占用**：512MB 是硬件最低门槛，500MB 是软件占用，剩 12MB 给 OS 虽紧但非严格矛盾；LLM 不做“预算可分配性”推理 |
| 6 | scheduler | 002 | value_contradiction | 5ms/25ms=20% > CPU 上限 10% | **上界 vs 典型值**：5ms 是执行时间上界（worst-case），非恒定值；正常 CPU 占用远低于 20%；LLM 把上界当确定值做除法 |
| 7 | scheduler | 003 | value_contradiction | 3.2.4 输出含 SOC vs 3.2.5 输出缺 SOC | **不同输出函数不同字段**：3.2.4 是主循环全量输出，3.2.5 是降采样精简输出，字段差异可能是有意设计；LLM 假设所有输出格式必须一致 |

### 3.5 FP 根因归纳

**根因 1：LLM 把“文字张力”当“逻辑矛盾”。**
`check_cross_section_consistency` 的 prompt 明确要求 LLM 找 4 类矛盾，LLM 倾向于**最大化召回**——任何两处文字不完全一致就报。它缺少“这是否构成真正不可满足”的判定。

**根因 2：缺乏工程语义区分。** 4 类混淆模式反复出现：
- 简写 vs 形式声明（#1, #3）
- 上界/最坏情况 vs 恒定值（#6）
- 最低配置 vs 实际占用（#5）
- 模糊限定词（“无特殊”）（#4）
- 不同上下文的合理差异（#7）

**根因 3：无正值约束感知。** LLM 不知道哪些参数对是“故意一致”的，无法用“确认一致”作为反例抑制误报。

**根因 4：Z3 与 LLM 割裂。** 当 LLM 报 `value_contradiction`（#5, #6）时，这些本是数值矛盾，本可转 Z3 验证实际不可满足性——但 LLM 报完即止，不触发 Z3 复核。Z3 能判定“5ms 上界 + 10% 上限”是否真不可满足（答案：可满足，因 5ms 是上界非定值），从而杀掉 #6。

### 3.6 GJB 规则覆盖率（逻辑层）
GJB 120 条规则中**没有“跨章节矛盾检测”这一类型**——逻辑一致性是文档内容的涌现属性，非标准条款。因此逻辑层的“规则覆盖率”不适用传统统计。但可对应：
- `logic_unsatisfiable`：GJB 3.2.X 能力需求参数的数值自洽（参数类规则 8 条的隐含延伸）。
- `cross_section_*`：GJB 3.1 状态方式、1.2 概述 vs 3.2 能力需求的“承诺-实现”一致性（content 类部分规则的延伸）。
- `cross_document_conflict`：GJB 5 可追踪性的跨文档延伸（structure 类 2 条的延伸）。

逻辑层实质是把 GJB 内容规则**跨章节/跨文档联合**检验，自动化潜力取决于约束提取质量与形式化能力。

---

## 4. GJB 120 条规则自动化总览

| 层 | 规则类别 | 条数 | 已自动化 | 接入评测 | 可自动化潜力 | 当前主要缺口 |
|----|----------|------|----------|----------|--------------|--------------|
| syntax | format | 14 | ~5 | 0 | ~10 | 合规扫描未接入 |
| syntax | structure | 24 | ~6 | 0 | ~18 | 合规扫描未接入 + 无 GT |
| semantic | content | 53 | ~7 | ~7 | ~30 | 46 条未自动化（接口/保密/安全/可测试性） |
| semantic | parameter | 8 | ~6 | ~6 | ~6 | 值冲突召回未测试 |
| semantic | interface | 21 | ~3 | ~3 | ~12 | 18 条需深度语义 |
| logic | （涌现属性） | — | 2 检测器 | 2 检测器 | — | LLM FP 高 + 无跨文档 |
| **合计** | | **120** | **~27** | **~16** | **~76** | |

- **gap_analysis 结论**：总体覆盖率 45.2%（33/73 条款），33 条缺失、12 条不精确，建议扩至 ~80 条全覆盖。
- **当前评测闭环内实际生效**：仅 ~16 条（semantic 的占位符+参数比较），占 120 条的 **13%**。

---

## 5. 突破方向（按投入产出排序）

### 优先级 1：接入语法层合规扫描（零新代码，立即生效）
- 把 `srs_gjb_compliance_scan.py` 的 7 类检查输出转为 `consistency_reports/{doc}_syntax.json`，`check_type` 用 `missing_*`/`structure`/`numbering_format`。
- 在 `srs_eval.py` 的 `CHECK_TYPE_TO_LAYER` 已有映射，**只需补 GT**：为 3 份文档标注语法层正/负样本（如“缺第 4 章”“编号非 X.Y.Z”）。
- 预期：syntax 层从 0/0/0/0 变为有信号，覆盖率 +11 条规则。

### 优先级 2：LLM 跨章节 FP 抑制（直击 7 个 FP）
**2a. Z3 复核闸门**：LLM 报 `cross_section_value_contradiction` 时，自动转 Z3 验证“是否真不可满足”。能杀掉 #5（512 vs 500 可分配）、#6（5ms 是上界非定值，可满足）。
**2b. 工程语义消歧 prompt**：在 cross-section prompt 中增加“排除以下非矛盾模式”指令：简写 vs 形式签名、上界 vs 典型值、最低配置 vs 占用、模糊限定词、不同函数不同字段。能杀掉 #1/#3/#4/#7。
**2c. 正值感知**：把 Gold Standard 的确认一致对（或检测器自己判一致的参数对）作为“已知一致，勿报”上下文喂给 LLM。
- 预期：logic 层 FP 7→~1-2，P 从 0.36 升至 ~0.7+。

### 优先级 3：跨文档检测（补 logic FN=1）
- 在 `check_document` 之上加 `check_document_collection(docs)`：加载多文档 constraints，按共享实体（“电池模型”/参数名）关联，把跨文档同实体约束对送 Z3/LLM 联合判定。
- 直接命中 battery GT-008（battery CPU<5% vs scheduler CPU<10%）。
- 预期：logic 层 FN 1→0，R 从 0.8 升至 1.0。

### 优先级 4：表格结构完整性检测（补 semantic FN=1）
- 在 `check_text_table_consistency` 中增加“单元格断裂检测”：比对提取表格的行列数与预期 schema，识别 OCR 把单格拆成多行的情况（GT-007：“单元测”+“试+对比验证”应为“单元测试+对比验证”）。
- 预期：semantic 层 FN 1→0，R 从 0.667 升至 1.0。

### 优先级 5：补齐评测盲区
- 标注 `same_param_diff_value` 真矛盾 GT（同参数两处不同值），测试同值检测器真正的抓错能力（当前 0 样本）。
- 标注 `same_value_diff_semantics` 负样本，测试语义角色区分。
- 扩展 Gold Standard 到更多文档（当前仅 3 份 22 条 GT，统计显著性不足）。

### 优先级 6：扩展 GJB 规则覆盖
- 按 gap_analysis 的 priority_1/2/3 补全 ~34 条缺失规则（状态方式、数据元素组合体、保密性、安全性、可追踪性反向等）。
- 重点把 interface(21) 的字段完整性检查自动化（当前仅 3 条）。

---

## 6. 边界与局限声明

1. **Gold Standard 规模小**：3 文档 22 条 GT，其中真矛盾仅 8 条。任何 P/R/F1 都有高方差，不宜过度解读小数点。
2. **正值占比高（64%）**：TN=14 拉高了“正确率”观感，但真正的矛盾检出能力（TP=6）仍弱。
3. **OCR 质量是隐性变量**：GT-007 的 FN 本质是 MinerU/OCR 损坏，非检测器逻辑错误——评测的是“含 OCR 噪声的端到端能力”，这对方法公平性有影响。
4. **LLM 随机性**：cross-section 检测依赖 LLM（temperature=0.1），结果非完全可复现，FP 数量可能随运行波动。
5. **Z3 依赖 LLM 生成代码**：`check_logic_consistency_z3` 用 LLM 生成 Z3 Python 代码再执行——当 LLM 无法生成代码时回退（battery 报告中 `logic_analysis` INFO“无法生成 Z3 代码”），此时 Z3 优势失效。battery 的 102 条约束就因 Z3 代码生成失败而未做形式化验证。

---

## 7. 一句话总结

> **语法层空白（检测器+GT 双缺，但合规扫描器已存在待接入）；语义层高精度但只靠占位符检测、漏 OCR 表格断裂；逻辑层 FP 爆炸全部来自 LLM 跨章节检测，而 Z3 零误报——破局关键是用 Z3 复核 LLM 的数值矛盾、用工程语义消歧抑制文本张力误报、并新增跨文档检测补召回。**
