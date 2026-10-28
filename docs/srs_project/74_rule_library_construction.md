# 74 规则库构建方法与新标准replay指南

> 主题：`knowledge/gjb_438c_rules_full.json`（120条规则）是怎么建出来的；
> 换一个新标准（GJB 438B/其他行业规范）如何**replay**同样的构建链；
> 规则库如何与"新文档一键接入"（`tools/onboard_new_document.py`，
> 01号端到端演示）衔接成完整的标准级→文档级配置流。
> （编号说明：68-73号已被并行会话占用，本文取74号。）

相关文档：67号（L1规则模板层技术架构，规则**引擎**侧）· 64号（rulepack
设计，配置**载体**侧）· 本文（规则**库**的构建方法与replay）。

---

## 0. 一句话定位

规则库是"标准说了什么"的结构化沉淀（**标准级知识**）；rulepack的
gjb段（`gjb_rule_library_path` + `gjb.rule_clusters`簇映射）把库接到
引擎上（**接线级知识**）；onboarding归纳的是"这份文档长什么样"
（**文档级知识**）。三层各自动、各自校验，互不越界——本文讲第一层
怎么建、怎么replay、怎么接到后两层。

```
GJB 438C标准PDF ──MinerU OCR──> 标准条文 ──LLM辅助抽取+人工核验──>
knowledge/gjb_438c_rules_full.json (120条, 标准级)
        │ rulepack.gjb_rule_library_path (srs_gjb_v1.json, 接线级)
        │ rulepack.gjb.rule_clusters (GJB-01~11簇映射)
        ▼
gjb_rule_engine.compile_rule → 87条SRS适用 → 55可编译/32manual
        ▼
audit_document/aggregate_clusters → 分簇verdict (audit_gjb_compliance
  / onboard_new_document第5步复用)
```

---

## 1. 现有库的构建链（GJB 438C-2021 → 120条规则）

### 1.1 构建链五步

1. **标准获取**：GJB 438C-2021《军用软件开发文档通用要求》PDF（81页
   有效正文）。
2. **OCR解析**：MinerU把PDF解析为markdown（正文+表格+章节锚点）。
   注意：构建期的OCR产物**未随库入库**（当前仓库无`data/gjb_438c/ocr/`
   目录）；原文锚点由每条规则的`original_text`字段承载，
   `_source_verified`字段如实记录"未做逐字核对"。
3. **规则抽取**：逐章节阅读编码——识别规范句（含"应/必须/宜"等情态
   标记的条文），拆成单条可判定的规则，并标注类型/来源/适用文档。
   提取脚本未保存（`_extraction_method`如实记录），这是本库最大的
   工程债：**不可脚本重放**。§2的replay流程即为此偿还——新标准的
   抽取走"LLM辅助+prompt模板"，可重放可审计。
4. **Schema定型**：13个字段（§4），其中`rule_id`/`type`/`source`/
   `description`/`original_text`为必填核心，`_`前缀字段为构建期元数据
   （置信度/核验状态/抽取方法）。
5. **核验**：逐条人工复核`description`与`original_text`的对应（重叠率
   写入`_confidence_reason`），`_confidence`三档记录抽取把握。

### 1.2 库的实测口径（v2.0）

| 维度 | 分布 |
| --- | --- |
| 总数 | 120条（`GJB-RULE-001`~`GJB-RULE-120`，编号即排序键） |
| type | content 53 / structure 24 / interface 21 / format 14 / parameter 8 |
| severity | HIGH 74 / MEDIUM 39 / LOW 7 |
| modality | MUST 19 / MAY 8 / SHOULD 2 / 无标记 91（"应"在中文原文里，规则句未显式分档） |
| applies_to | SRS 87 / ALL 25 / IRS 23 / SSS 18 / SDD 10 / IDD 9 / STP 6 / SSDD 6 / SDP 5 / OCD 4 / DATABASE 4 / ELECTRONIC 4 |
| applies_role | 无 118 / 订购方 1 / 承制方 1 |
| source | 正文4.3~4.4 + 第5章 + 附录J（SRS模板）为主 |

### 1.3 `_confidence`字段的含义

`_confidence`是**抽取置信度**（不是规则本身的可信度——规则都是标准
原文）：HIGH=原文含标准格式且重叠率高（当前120条全HIGH，因为都经过
人工编码）；伴随两个字段：

- `_confidence_reason`：判定依据（如"原文含标准格式, 重叠率94%"——
  description对original_text的覆盖率）；
- `_source_verified`：核验状态——**如实记录未完成项**（"未找到OCR
  原始文件做逐字核对"）。这是诚实账：库可信度的边界在哪，字段里写着。

### 1.4 引擎侧的消费口径

`gjb_rule_engine.load_rule_library()`只取`applies_to`含SRS的87条；
`compile_rule()`把其中55条编译为presence检查、32条判manual（跨文档
规则/无规范句/无可提取宾语——诚实报告不可编译，见67号§5.2）。簇映射
（`srs_gjb_v1.json`的`gjb.rule_clusters`，GJB-01~11）在这87条里取材，
一条规则可服务多簇（如041同属GJB-02/06/08/09）。

---

## 2. 新标准replay步骤（OCR→LLM辅助抽取→人工核验→入库）

目标：把§1.1第3步的"人工阅读编码（不可重放）"替换为**可重放的
LLM辅助抽取**。流程对任何"条文式"标准（GJB其他分册/行业规范）通用。

### 2.1 步骤总览

```
新标准PDF → MinerU OCR(markdown) → 按章节切条文块
  → LLM抽取(prompt模板, 逐块) → JSON草稿 → 确定性后校验(脚本)
  → 人工核验(抽样全检+全量抽查) → 入库(编号/统计/版本) → 回归测试
```

硬规则：LLM调用走`algorithms/llm_client.py`的缓存接口（cache=True，
禁裸调用——不可复现）；后校验与入库是确定性脚本；人工核验留下记录
（核验清单入库或入runs）。

### 2.2 LLM抽取prompt模板

输入=一个条文块（含章节号锚点），输出=JSON数组，每项遵守§4 schema：

```text
你是军用软件文档标准的规则抽取器。把下面的标准条文拆解为原子规则。

要求：
1. 只抽取含规范性情态的条文（应/必须/宜/可以），一条原子规则=一个
   可独立判定的要求；复合句拆成多条。
2. type取值：format(文档格式)/structure(章节结构)/content(内容要求)/
   interface(接口要求)/parameter(参数值要求)。
3. applies_to取值：ALL/SRS/SSS/IRS/SDD/IDD/STP/SSDD/SDP/OCD/
   DATABASE/ELECTRONIC，按条文针对的文档类型；通用的填ALL。
4. modality：原文"必须"→MUST，"应"→MUST(默认，中文国军标"应"即
   强制)，"宜"→SHOULD，"可/可以"→MAY；无明示则null。
5. description=改写为单句规则（保留量词与枚举项，不省略"每条/全部"）；
   original_text=条文原文逐字摘录（含上下限定语）。
6. source=条文的标准章节号（如"4.3.7.1"或"附录J 3.2.X"）。
7. 拿不准的字段填null并在notes里说明，不要编造。

输出JSON数组，字段：type/source/severity/modality/applies_to/
applies_role/description/original_text/notes。

条文块：
<{章节号} {原文}>
```

（severity建议规则：违反会导致验收不通过→HIGH；影响质量评估→
MEDIUM；建议性→LOW。）

### 2.3 确定性后校验（脚本，LLM输出不直接入库）

1. JSON可解析、字段枚举合法（type/modality/applies_to白名单）；
2. original_text非空且**在OCR markdown中可定位**（子串或规范化后子串
   匹配——定位失败的人工复核，_source_verified记"OCR定位失败"）；
3. description与original_text的重叠率（字符bigram覆盖率）写入
   `_confidence_reason`，低于阈值（如70%）降_confidence为MEDIUM；
4. rule_id统一分配（入库时按序编号，LLM不产ID）；
5. 跨文档主语检测：条文主语是其他文档（SSS/IRS…）而applies_to不含
   本库目标文档的，单独标记（引擎侧会判manual）。

### 2.4 人工核验流程

- **全量快检**：每条读description+original_text对（10秒/条量级），
  确认"改写没改义"；
- **抽样深检**：按置信度分层抽样（每层≥10%），回OCR原文核对上下文
  截取是否引入/丢失限定语；
- **核验记录**：核验人/日期/结论入库的`_confidence`/`_source_verified`
  更新，或存runs（`tools/run_utils.py`协议）。

### 2.5 入库与回归

1. 合并进`knowledge/<standard>_rules_full.json`（新标准新文件，不
   覆盖旧库）；更新顶层`version/standard/total_rules/statistics`；
2. `python tools/build_data_manifest.py`更新数据资产清单并同步快照
   （库受tests/test_manifest.py保护）；
3. 回归：`python -m pytest tests/test_gjb_rule_engine.py`——引擎对新
   库跑compile/audit的编译覆盖率与簇裁决不回退。

---

## 3. 与onboarding工具的衔接（新库→rulepack→簇映射→审计）

onboarding（`tools/onboard_new_document.py`，归纳引擎
`algorithms/consistency/onboarding.py`）从**新文档**归纳文档级配置；
标准级知识的接线方式：

1. **库指向**：rulepack的`gjb_rule_library_path`指向规则库文件
   （srs_gjb_v1与01号草稿均指向`knowledge/gjb_438c_rules_full.json`）。
   换新标准=新库文件+新rulepack基座（或v2 pack改指向）。
2. **簇映射**：`gjb.rule_clusters`（簇id+rule_ids+映射理由）。新标准
   replay后需重建簇映射——把taxonomy/检查项语义映射到新库的rule_id，
   每簇写明reason；**rule_ids必须全部存在于库中**。
3. **缺口#3校验**（本工具链补上的验证器）：
   `onboarding.validate_cluster_rule_ids(draft, library)`返回簇映射中
   不存在于库的rule_id列表——rulepack的schema校验不做库交叉核对，
   这个函数补上（load_rulepack通过+返回空 ⇒ 引用全部真实存在）。
4. **标准级知识不动校验**：`validate_gjb_section_unchanged(draft,
   base)`保证onboard草稿的gjb段+库路径与基pack逐字一致——审计引擎
   （`gjb_rule_engine`）按默认pack读簇映射，草稿若改了gjb段，引擎裁决
   会与草稿声明失真；工具侧发现分歧即失败退出，不静默。
5. **审计复用**：`tools/audit_gjb_compliance.py`的`load_doc_blocks/
   audit_with_pack`已参数化（pack提供库路径），onboarding第5步用它跑
   新文档审计并附04号基线对比——**同标准不同文档的合规差异本身是
   有意义的输出**（01号实测：11簇中10簇同结论，GJB-04审计日志簇
   01号satisfied/04号partial，源于01号表28安全性需求含审计追踪条款）。

01号演示事实（2026-10-28实测，runs/`onboard_new_document_*`）：
344块/71表→24表头簇（use_case 20×/interface 16×/qualification 1×
零改动覆盖，trace 2×触发方向变体）；ID根PZXQ→ZZSJHQZHFW（自身303次/
19族，外部JCYY-等33次不进join范围）；草稿7项变更+23项_needs_review；
校验全绿后审计跑通。

---

## 4. schema字段规范（填写标准）

| 字段 | 必填 | 填写标准 |
| --- | --- | --- |
| `rule_id` | ✅ | `GJB-RULE-NNN`三位连续编号；入库时统一分配，抽取期不产ID |
| `type` | ✅ | 枚举`format/structure/content/interface/parameter`；一条规则只归一类，复合的拆条 |
| `source` | ✅ | 标准章节锚点（`4.3.7.1`/`附录J 3.2.X`）；可在OCR中回定位 |
| `severity` | ✅ | `HIGH/MEDIUM/LOW`（§2.2建议规则）；缺省HIGH仅当违反即验收不通过 |
| `modality` | ⬜ | `MUST/SHOULD/MAY`；原文"应"→MUST（国军标默认强制）；无明示填null，**不猜** |
| `applies_to` | ✅ | 文档类型数组（§2.2白名单）；通用填`["ALL"]`；一条规则可多文档 |
| `applies_role` | ⬜ | `订购方/承制方`；绝大多数规则无角色限定填null |
| `description` | ✅ | 单句规则改写；**保留量词（每条/全部）与枚举项**——引擎的量词封顶partial与枚举模式提取都吃这里 |
| `original_text` | ✅ | 条文原文逐字摘录（含限定语）；是核验与`_confidence_reason`重叠率的分母 |
| `_confidence` | ✅ | `HIGH/MEDIUM/LOW`抽取置信度；判定依据必须同步写进`_confidence_reason` |
| `_confidence_reason` | ✅ | 如"原文含标准格式, 重叠率94%"；MEDIUM/LOW必须写明降档原因 |
| `_source_verified` | ✅ | 核验状态如实记录（含"未做逐字核对"这类未完成项——诚实账） |
| `_extraction_method` | ✅ | 抽取链路记录（现库=人工编码；replay=LLM+prompt模板版本号） |

红线：`description`不得丢量词/枚举（引擎语义依赖）；`original_text`
不得改写；拿不准的字段填null+notes，不编造；`_`前缀字段是构建期元
数据，引擎不消费但核验流程依赖。

---

## 5. 诚实账与已知限制

1. **现库不可脚本重放**（提取脚本未保存）：§2的replay流程只对新标准
   生效；GJB 438C库的重放=重跑人工编码，成本已知。
2. **OCR原文未入库**：`original_text`是唯一原文锚点，`_source_verified`
   记录了逐字核对未完成——replay流程的后校验（§2.3第2条）在新库上
   补齐这一点。
3. **91条modality为空**：中文"应"未显式分档是标准原文形态，不是抽取
   缺陷；引擎侧用句式分析器从description/original_text自行定位情态
   标记（67号§5.1），不依赖modality字段。
4. **簇映射是语义判断**：rule_ids→GJB-01~11的映射带reason供审计，
   但映射本身无金标准；换标准replay时簇定义需随taxonomy重审。
5. **onboard草稿≠全自动**：01号23项_needs_review（表头变体/新表型
   归型）留给人工裁决——工具把"可检查的草稿"做出来，判断仍是人的。
