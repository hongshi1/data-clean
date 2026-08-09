# 语义层不一致性检测 Gold Standard 构建与评测协议 v1.0

> 日期: 2026-08-10
> 状态: 方法论设计（待标注实施）
> 任务定位: 为"条目级跨位置语义不一致性检测"构建科学 Gold Standard 与评测协议
> 数据基础: 16 份 GJB SRS，stage0_assets（971 唯一 ID / 2016 出现位 / 1207 表 / 381 图 / 1022 追溯边 / 1414 接口记录 / 25 版本记录 / 426 异常流），已确认 14 条真实语义矛盾（12 名称 + 2 版本）
> 参照基准: ContractNLI（607 文档 / 17 假设 / 三态 E-C-NM）、ARTA（requirement smell）、FinBalance（710 记录 / 23 不一致码 / 3 标注者 / 5000 次 bootstrap）、Korn 2026（arXiv:2606.25550，LLM 不可靠生成 requirement smells）

---

## 0. 核心张力与方法论主张

真实语义负例**极度稀缺**：经 `mineru_standard` 交叉验证后仅 14 条（见 `data/gjb_438c/data_assets/gold_standard/semantic_inconsistency_gold.json`），而验证前的语义候选约 47 条（38 名称 + 9 版本，见 `docs/srs_project/semantic_inconsistency_design.md`）——**约 70% 的"矛盾"被判定为解析伪影（OCR/表格排版导致的截断、字序颠倒）而剔除**。这一事实决定了本协议的三条主线主张：

1. **分层负例构建**：真实负例（Tier-1，生态效度）+ 受控注入负例（Tier-2，FinBalance 式可复现规模）+ LLM 提议负例（Tier-3，仅作干扰，强制人工验证）。纯真实不足以支撑统计功效，纯 LLM 不可信（Korn 2026）。
2. **双有效性维度**：每条矛盾必须标注 `is_parser_artifact`（真实 vs 解析噪声）与 `is_reasonable_difference`（合理差异 vs 真实矛盾）。Gold 的正性矛盾仅取 `real ∧ ¬reasonable`；解析伪影与合理差异单列为"鲁棒性/噪声"子集，**不混入主指标**。
3. **双模式评测**：Oracle-聚合模式（给金标准聚合条目，纯测检测能力）vs. 流水线-聚合模式（先方向A聚合再检测，测端到端）。两者差值 = 方向A误差传播量，从而**把方向A与方向B的贡献解耦**——这是本 benchmark 相对 ContractNLI/ARTA/FinBalance 的核心增量。

---

## 1. 标注方案

### 1.1 标注单元

**标注单元 = 聚合条目（aggregated item）**：一个 `entity_id` 在文档所有位置（正文/章节标题/功能表/接口表/合格性表/追溯表/版本表）的全部出现，跨模态聚合为一个条目。据 stage0_assets，971 个 ID 共 2016 次出现，均值约 2.1 位/ID，聚合非平凡。每条目对应一个 Gold 记录。

### 1.2 字段定义（扩展现有 gold schema）

```jsonc
{
  "item_id": "INC-0001",
  "doc": "06运行支撑服务软件需求规格说明-终稿",
  "entity_id": "PZXQ-WBJK-YXZCFW-SJTYFWFW",
  "entity_type": "interface",            // function|interface|version|exception_flow|traceability

  // 聚合上下文：每个位置一个 entry
  "aggregated_context": [
    {"position": "section_title", "section": "3.3.7", "modality": "text",
     "field": "name", "value": "与数据统一访问服务接口",
     "raw_snippet": "3.3.7 与数据统一访问服务接口", "source_parse": "mineru_standard"},
    {"position": "interface_table", "section": "3.4.1", "modality": "table",
     "field": "name", "value": "与数据统一访问服务接口",
     "raw_snippet": "...", "source_parse": "mineru_standard"}
    // ...
  ],
  "attribute_value_sets": {              // 按属性聚合后的值集合，供比对
    "name": {"与数据统一访问服务接口": 2, "与服务集成框架接口": 2},
    "type": {"API接口": 4},
    "sender": {"数据统一访问服务": 2}, "receiver": {"运行支撑服务": 2}
  },

  // 主标签
  "label": "inconsistent",               // consistent | inconsistent | insufficient_info
  "label_mode": "binary_collapsed",      // 报告时再派生三态

  // 不一致性列表（label=inconsistent 时非空）
  "inconsistencies": [
    {"subtype": "name_multiname", "attribute": "name",
     "location_a": {"position":"section_title","section":"3.3.7","value":"与数据统一访问服务接口"},
     "location_b": {"position":"section_title","section":"3.3.8","value":"与服务集成框架接口"},
     "edit_distance": null, "severity": "high",
     "rationale": "同ID在3.3.7/3.3.8指向完全不同的被对接系统，非简称/截断，判定真实矛盾"}
  ],

  // 双有效性维度（关键）
  "is_parser_artifact": "real",          // real | parser_noise（须对 mineru_standard 源核对）
  "is_reasonable_difference": "no",      // yes | no（合理差异：简称全称/视角/空格）

  // 来源与可复现性
  "provenance": "real",                  // real | injected | llm_proposed
  "injected_code": null,                 // provenance=injected 时必填，取自 codebook
  "ground_truth_canonical_value": "与数据统一访问服务接口",  // 注入/真实的权威正确值

  // 标注元数据
  "annotators": ["A1","A2","A3"], "adjudicator": "A1",
  "agreement": {"raw_labels": ["inconsistent","inconsistent","consistent"], "adjudicated": "inconsistent"},
  "notes": ""
}
```

### 1.3 子类型分类法（codebook）

依据 `semantic_inconsistency_design.md` 的 4 模式 + 版本，定义 5 个核心子类型并预留扩展位。**每个子类型配一个确定性注入码**（FinBalance 式），供 Tier-2 复现：

| 子类型码 | 含义 | 检测信号 | 真实负例占比 | 备注 |
|---|---|---|---|---|
| `name_truncation` | 同名被截断（子串关系） | name_a⊂name_b | 11/38 候选 | **多为解析伪影**，real 过滤后接近 0 |
| `name_typo` | 形近/音近错字 | 编辑距离≤2 | 4/38 候选 | real 后保留较好 |
| `name_charorder` | 字序/空格颠倒 | 字符集合同序不同 | 2/38 候选 | **几乎全为解析伪影** |
| `name_multiname` | 完全不同功能名配同 ID | 语义不相关 | 21/38 候选 | real 后主体，最难 |
| `version_conflict` | 同软件不同版本 | 版本号集合>1 | 2 真实 / 25 记录 | 属性空间小，注入需谨慎 |
| `_ext_attr_mismatch` | 接口 type/sender/receiver/优先级矛盾 | 属性值集合>1 | 待挖 | 利用 1414 接口记录 |
| `_ext_dangling_ref` | 追溯/合格性引用断裂 | 目标章节不存在 | 8 dangling | 与语法层边界，可选 |

### 1.4 标注规则

**正例（consistent）判据**：聚合条目所有属性在所有位置值集合大小均为 1，**或**存在差异但全部落在"合理差异"清单内（简称全称且差异仅在尾部功能词"功能/服务/模块"；仅空格差异；接口表用接口名而合格性表用功能名的视角差异）。

**负例（inconsistent）判据**：存在 ≥1 属性，其值集合大小 >1，且至少一对差异**非合理差异**，且**非解析伪影**（经 mineru_standard 源核对确认差异存在于原始文档而非解析引入）。

**insufficient_info 判据**：可靠位置（source_parse=mineru_standard）<2 个，无法构成跨位置比对——此态刻画方向A聚合失败，不计入一致/不一致。

**决策树**（继承 design.md §5.3 并增解析伪影分支）：值集合=1 → consistent；>1 → 逐对差异：仅空格→合理；子串且尾部功能词→合理；编辑距离≤2且形近字→真实(typo)；字符集合同→**查源**：源亦颠倒则真实(charorder)，源正常则 parser_noise；完全不同→语义相似度<0.4→真实(multiname)；其余→人工/LLM 辅判。

### 1.5 标注者要求与一致性

- **3 名标注者**（对齐 FinBalance）：1 名 GJB/SRS 领域专家（资深，任裁决者）+ 2 名受过 RE 训练的研究生。
- **渲染为纯 Markdown 表单**（FinBalance 技巧，见 `data/external_datasets/finbalance/human_verification/`）：标注者只看聚合条目的人类可读视图 + 源核对片段，不接触 JSON/代码，降低领域专家门槛。
- **重叠设计**：25–30% 条目三人独立标注（IAA 子集），其余双人标注+专家裁决分歧。三人全部分歧由专家裁决。
- **一致性指标**：报告 Krippendorff's α（容忍三态与缺失），并按子类型报告。目标 α≥0.67（tentative）；实际值如实报告，低于 0.67 的子类型在论文中标注为"低一致性、结论探索性"。
- **验证来源**：所有矛盾必须对 `mineru_standard`（权威解析）核对 `is_parser_artifact`；不得仅凭 `mineru_correct` 判定。
- **LLM 负例强制验证**（Korn 2026）：Tier-3 的 LLM 提议负例必须经人工逐条确认为真实矛盾方可入 gold，且 `provenance=llm_proposed` 永久标记，仅作干扰项。

---

## 2. 评测协议

### 2.1 任务设定与标签空间

- **主任务（头条指标）**：二分类，条目级，正类= inconsistent。在"解析伪影-free 且合理差异-free"子集上评测。
- **次任务**：三分类（consistent / inconsistent / insufficient_info）。`insufficient_info` 刻画方向A聚合失败，与 ContractNLI 的 NotMentioned 语义不同（后者是文档未提及，前者是聚合召回不全）。
- **双模式**：
  - Oracle-聚合：输入 = gold `aggregated_context`。纯测方向B检测能力。
  - 流水线-聚合：输入 = entity_id，系统先执行方向A聚合再检测。ΔF1 = 方向A误差传播。
- 两个模式都报告，头条用 Oracle 模式（隔离方向B），端到端用流水线模式。

### 2.2 子类型分层 vs 统一

**两者都报**：统一 macro-F1 作头条；子类型分层 P/R/F1 作分析。理由：子类型难度差异极大（char-level 近平凡，multiname 最难），统一指标会掩盖方法在不同难度上的真实表现。子类型样本量小（见 §3），其指标标注宽 CI、定性解读。

### 2.3 指标

- 正类=inconsistent：Precision / Recall / F1，并报 consistent 类的 F1 与 macro-F1。
- 三态：三类 macro-F1 + 混淆矩阵（重点看 inconsistent↔insufficient_info 混淆，即"聚合失败被误判为一致/不一致"）。
- **定位加分指标**（novel）：exact-match 准确率——系统是否给出正确的 (subtype, location_a, location_b)，而非仅标记条目。这区分"会报警"与"会定位"。
- **鲁棒性子指标**：在 parser_noise 子集上报告假阳率，量化方法对解析噪声的免疫力。

### 2.4 基线

| 基线 | 设置 | 验证点 |
|---|---|---|
| B0 多数类 | 全预测 consistent | 下界 |
| B1 无上下文 | 仅 entity_id，LLM 直判 | 上下文/聚合价值 |
| B2 随机检索 | 随机位置拼凑上下文 | 检索质量价值 |
| B3 字符级 only | 仅层1（截断/错字/字序） | 语义方法相对增益 |
| B4 强 LLM 零样本 | 聚合条目直接喂 LLM 判一致 | 印证 Korn 2026（预期弱） |
| B5 全流水线 | 方向A聚合+检索+LLM | 端到端主方法 |
| B6 检索-oracle+LLM | 给金标准聚合+LLM | 方向B上界（减去聚合） |

B6−B5 = 方向A代价；B5−B4 = 检索/RAG 增益；B5−B3 = 语义层增益。

### 2.5 统计显著性

- **配对 bootstrap**（对齐 FinBalance，B=5000 重采样）报告 F1 的 95% CI。
- **配对模型比较**：McNemar 检验（条目级配对）。
- **小样本子类型**：Wilson 区间；n<20 的子类型仅定性报告。
- **功效门槛**：见 §3，主头条需 n_pos≥200 方能在 ΔF1=0.03 上达到 80% 功效。

### 2.6 消融

无上下文 / 无图 / 无表 / 纯 LLM / 仅字符级 / 仅语义级 / 仅规则级——沿用 `eval_design.md` §5 框架，叠加 §2.4 的检索-oracle 对照。

---

## 3. 数据集规模建议

### 3.1 功效分析（推导）

Recall R 的 95% CI 半宽 h = 1.96·√(R(1−R)/n_pos)。以 R=0.8 为例：

| 目标半宽 h | 所需 n_pos（正类=负例数） | 用途 |
|---|---|---|
| ±0.05 | ≈246 | 顶会头条精度 |
| ±0.08 | ≈96 | 短文/pilot |
| ±0.10 | ≈62 | smoke test |

Precision 同理需 n_neg≈同量。故**头条 F1 的 CI ±0.05 需 ~250 负例 + ~250 正例 ≈ 500 条**。配对 bootstrap 比例估计更高效，n≥300 即可支持 ΔF1=0.03 的配对比较。

### 3.2 分层构建（解决真实负例稀缺）

| Tier | 来源 | 数量 | 角色 |
|---|---|---|---|
| Tier-1 真实 | 14 条已确认 + 再挖 ~6（attr_mismatch/dangling） | ≈20 | 生态效度，单独报"real-only"子分 |
| Tier-2 受控注入 | 真实一致条目上注入 1 个 codebook 码，doc 上下文真实 | ≈230（5 码 × ~46） | 可复现规模、子类型均衡 |
| Tier-3 LLM 提议 | LLM 生成，强制人工验证 | ≈0–50（仅干扰） | 鲁棒性，不入主 gold |

Tier-2 注入规则（FinBalance 式确定性）：取一个 `attribute_value_sets` 全单值的真实一致条目 → 选定一个位置与一个属性 → 按 codebook 模板替换值（truncation 去尾；typo 换 1 形近字；charorder 乱序；multiname 换语义无关名；version 换版本号）→ 记录 `injected_code` 与 `ground_truth_canonical_value`。每条仅注入 1 处，保证可定位评测。注入模板 + 随机种子公开，**每条标签可审计可复现**。

### 3.3 规模与划分

| 集合 | 规模 | 负例 | 正例 | 用途 |
|---|---|---|---|---|
| coverage（smoke） | ≈100 | ≈40（每码≥1，每文档≥1） | ≈60 | 快速消融，对齐 FinBalance coverage 143 |
| dev | ≈100 | ≈45 | ≈55 | 阈值调参 |
| **test（主）** | **≈500** | **≈250**（5 码×~46 + 真实 20） | **≈250** | 头条评测，F1 CI ±0.05 |

- **pilot 下限**（短文/工作坊）：14 真实 + ≈90 注入负 + ≈150 正 ≈ 250 → 头条 F1 CI ±0.08，子类型 CI ±0.10–0.12（探索性）。
- **顶会下限**：≈500（上表），子类型 n≈50 → 子类型 Recall CI ±0.12（仍宽，子类型定性解读）。
- **正负比**：主集 50/50（最小化给定 CI 宽度下的总样本量）；pilot 40% 负。自然真实率极低（14/971≈1.4%），但 benchmark 注入旨在均衡估计，不追求自然先验——如实报告注入比例。

### 3.4 划分原则

- **文档级隔离**（沿用 `eval_design.md`：train 01–08 / test 09–16）：同文档所有条目入同一 split，防文档记忆泄漏。
- **子类型分层**：每 split 内子类型比例一致。
- **注入码跨 split 共享**：codebook 在所有 split 可用（防"新子类型"泄漏），但具体条目与文档不跨 split。
- benchmark 定位为**测试型**（zero/few-shot 评测）；如需微调，从 dev 再切 train，test 永不参与训练。

### 3.5 已知局限

1. `name_truncation`/`name_charorder` 真实负例近乎全为解析伪影 → real-free 后接近 0；这两个子类型应作为"解析鲁棒性"评测，而非"真实不一致"主指标。
2. `version_conflict` 真实仅 2 条、版本记录仅 25 条 → 注入空间小，需跨文档汇集同名软件（如"达梦数据库"在多文档出现）扩充。
3. 3 名含领域专家的标注者招募是瓶颈；可先用 2 名研究生 + 专家裁决的 2.5 标注者设计降配，但 IAA 子集必须含专家。

---

## 4. 与现有 benchmark 的差异化定位

| 维度 | ContractNLI | ARTA | FinBalance | **本工作** |
|---|---|---|---|---|
| 检测对象 | 文档级 NLI（整文档+外部假设→E/C/NM） | 单需求 smell（句内模式） | 多文档数值对账（账本回放） | **条目级跨位置属性一致性（同 ID 多位置聚合）** |
| 不一致来源 | 外部假设 vs 文档 | 单需求内部模式 | 跨文档数值矛盾 | **文档内跨位置/跨模态属性矛盾** |
| 负例构造 | 真实合同+人工假设 | 真实需求+人工标注 smell | 受控注入（23 码，确定性回放） | **真实 + 受控注入 + 强制人工验证（拒纯 LLM）** |
| GT 可验性 | 人工标注 | 人工标注 | 确定性回放可审计 | **注入码可复现 + 源核对去伪影** |
| 聚合依赖 | 无（直接给文档） | 无（单需求） | 无（直接给文档包） | **依赖方向A聚合 → 双模式评测解耦** |
| 噪声处理 | — | — | — | **parser-artifact 有效性维度（70% 候选为伪影）** |
| 第三态语义 | NotMentioned（文档未提） | — | — | insufficient_info（聚合召回不全，方向A误差） |

**本工作四个差异化贡献**：

1. **ID 锚定的跨位置比对**：用需求 ID 作确定性锚点（非 LLM 抽取），把多模态文档理解转化为结构化跨位置属性比对——规避 GraphRAG 依赖 LLM 抽边带来的噪声。
2. **解析伪影有效性维度**：首次把"真实矛盾 vs OCR/解析噪声"作为一等标注维度。经验上 70% 候选为伪影，若不剥离会严重高估方法能力。剥离后余下的"解析鲁棒性"子集本身是一个新评测轴。
3. **双模式评测（Oracle-聚合 vs 流水线-聚合）**：隔离方向B（检测）与方向A（聚合），用 ΔF1 量化误差传播。现有 benchmark 输入直接给定，无此结构。
4. **合理差异 vs 真实矛盾的决策框架**作为标注维度：不是"相同/不同"二分，而是区分 4 类合理差异与 4 类真实矛盾，使任务贴近真实工程判断。

---

## 5. 实施路线（接 `semantic_inconsistency_design.md` §八）

| 阶段 | 任务 | 产出 | 依赖 |
|---|---|---|---|
| S1 | 从 stage0_assets.id_registry 生成 971 个聚合条目的人类可读 Markdown 视图 | `annotation/items/*.md` | stage0_assets |
| S2 | 编写 codebook（5 码注入模板）+ 注入脚本（种子可复现） | `tools/inject_negatives.py` + codebook.json | Tier-1 真实条目 |
| S3 | 3 标注者标注 IAA 子集（25–30%）→ 报告 α → 调整指南 | `annotation/iaa_report.json` | S1,S2 |
| S4 | 全量标注 + 专家裁决 | `gold_standard/semantic_inconsistency_v2.json` | S3 |
| S5 | 实现 B0–B6 基线 + 双模式 runner | `tools/eval_runner.py` | S4 |
| S6 | bootstrap 显著性 + 子类型分层报告 | `eval_report.md` | S5 |

---

## 附：关键文件索引

- 现有真实 gold：`data/gjb_438c/data_assets/gold_standard/semantic_inconsistency_gold.json`（14 条，verified_source=mineru_standard）
- 聚合基础设施：`data/gjb_438c/data_assets/stage0_assets.json`（id_registry 971 / traceability_map 1022 / interface_topology 1414 / version_pairs 25）
- 设计草案：`docs/srs_project/semantic_inconsistency_design.md`（4 模式分类法、决策树）
- 既有 QA 评测：`docs/srs_project/eval_design.md`（三层 QA 评测，本协议为互补的条目级 benchmark）
- 参照基准：`data/external_datasets/contract_nli/`、`data/external_datasets/finbalance/`（含 human_verification 协议、23 码 codebook、bootstrap 实现）
