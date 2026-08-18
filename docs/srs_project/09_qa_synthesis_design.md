# 09 SRS不一致性QA合成方案设计

> 版本: v1.0 | 日期: 2026-08-18
> 状态: 设计完成, 待实现
> 基础: 4-Agent联合调研(术语/参数/逻辑/GJB) + 13个市面数据集调研
> 对应代码: `tools/gen_trusted_qa.py`(待按本文档重写)

---

## 目录

- 第一章 为什么用LLM合成（不用市面数据）
- 第二章 数据来源（三源融合）
- 第三章 四类不一致 × 三层检测 × 模态映射
- 第四章 注入方式设计（26种，带学术依据）
- 第五章 四段式合成方法
- 第六章 输出格式（MMQA风格 + 占位符）
- 第七章 可信度论证（7条）
- 第八章 预期产出

---

## 第一章 为什么用LLM合成

### 1.1 市面数据集调研结论

调研了13个软件工程/技术文档领域的多模态QA数据集：

| 数据集 | 规模 | 模态 | 能否用于四类不一致 | 缺口 |
|--------|------|------|:---:|------|
| FlowVQA (ACL'24) | 22K QA | 流程图+文 | ❌ | 无一致性检测；英文；无表格 |
| UML-VQA (MDPI'25) | 10K QA | UML类图 | ❌ | 无SRS；无表格/正文；英文 |
| UML-VQA (arXiv'26) | 16K QA | UML类图 | ❌ | 同上 |
| Multi-Modal AI for SRS | 未公开 | 需求+图 | ❌ | 仅方法论文，未开源 |
| PDF-MVQA (IJCAI'24) | 263K QA | PDF+表+图 | ❌ | 生物医学；无一致性检测；英文 |
| MultiModalQA (ICLR'21) | 30K QA | 文+表+图 | ❌ | Wikipedia；无不一致检测；英文 |
| DocVQA | 79K QA | 扫描文档 | ❌ | 通用文档；无SRS；英文 |

**4个明确缺口**（市面数据集全部不覆盖）：

1. **无SRS专用多模态QA** — 唯一的SRS研究(Mona Nasr 2025)未开源
2. **无跨模态一致性校验** — 现有都是"问答"任务，没有"检测矛盾"任务
3. **无中文技术文档QA** — 全部英文
4. **无表格-文字-图片联合一致性标注** — 没有"同一实体在不同模态的值是否一致"

**结论**：市面上没有现成数据集能满足四类不一致需求，必须自建合成数据集。

### 1.2 为什么LLM合成+规则约束是最优方案

| 方法 | 优点 | 缺点 | 适用性 |
|------|------|------|:---:|
| 纯人工标注 | 最高质量 | 成本极高(需GJB专家) | ❌ |
| 纯规则生成 | 可控可复现 | 问题不自然(模板化) | ⚠️ |
| **LLM合成+规则约束** | **自然+可控** | 需验证 | ✅ |
| 纯LLM自由生成 | 最自然 | 不可控/不可复现/答案无锚点 | ❌ |

**LLM合成的关键约束**（让它可信）：
- 事实层用规则（从真实文档提取，不LLM编）
- 注入层用规则（确定性修改，可复现）
- 语言层用LLM（自然表达，但不负责判断对错）
- 答案层用规则确定（不是LLM判断的）
- 验证层用双LLM（消除偏误）

---

## 第二章 数据来源（三源融合）

### 2.1 数据源1: Pair Dataset（366实例）

```
data/gjb_438c/pair_dataset/
├── sc1_usecase_capability/     141实例  用例图+能力表+正文
├── sc2_flowchart_usecase/       90实例  流程图+用例表+正文
├── sc3_interface_interface/     30实例  接口图+接口表+正文
├── sc4_flowchart_capability/    49实例  流程图+能力表+正文
├── sc5_function_capability/     27实例  功能图+能力表+正文
├── sc7_usecase_usecase/          9实例  用例图+用例表+正文
└── sc8_pure_image/              20实例  纯图片+正文(无表)
```

每个实例包含4个文件：
- `image.png` — 真实SRS图片（用例图/流程图/接口图）
- `table.csv` — 真实SRS表格（能力表/接口表/用例表）
- `text.txt` — 真实SRS正文段落
- `meta.json` — 元数据（章节号/图注/表注/功能名/质量分级）

### 2.2 数据源2: GJB规则库（120条）

```
knowledge/gjb_438c_rules_full.json
├── format      14条  格式规范(页号/附录编号/载体)
├── structure   24条  结构规范(6章/附录引用/裁剪)
├── content     53条  内容规范(标识/需求描述/合格性)
├── parameter    8条  参数规范(单位/值域/精度)
└── interface   21条  接口规范(字段/类型/数据元素)
```

### 2.3 数据源3: 专家词典

```
knowledge/srs_kb.json
├── param_dictionary    23个参数(响应时间/吞吐量/可用性...) + 同义词 + 值域
├── interface_dictionary 13个接口类型 + 属性
├── unit_dictionary     10个单位族 + 换算关系
├── operator_dictionary 6类操作符(≤/≥/</>/=/~) + 同义词
└── conflict_rules      冲突规则(same_param_diff_value / mutex_interfaces)
```

### 2.4 不一致规则库

```
knowledge/inconsistency_rules.json
├── terminology     3条  TERM-001/002/003
├── parameter       3条  PARAM-001/002/003
├── business_logic  3条  LOGIC-001/002/003
└── gjb_compliance  5条  GJB-001~005
```

---

## 第三章 四类不一致 × 三层检测 × 模态映射

| 不一致类型 | 检测层 | 适用场景 | 模态输入 | 数据来源 |
|-----------|--------|---------|---------|---------|
| **术语层面** | 语义层 | sc1/sc2/sc4/sc5/sc7 | {image}+{table}+{text} | pair的func_names + 表格ID + 正文功能列表 |
| **参数指标** | 语义+逻辑 | sc3/sc4/sc5 | {table}+{text} | 表格属性列 + 正文数值 + 专家词典(23参数) |
| **业务逻辑** | 逻辑层 | sc2/sc4/sc7 | {image}+{table}+{text} | 流程图步骤 + 用例表异常流 + 正文流程描述 |
| **GJB合规** | 语法层 | sc1/sc3/sc4/sc5 | {table}+{text} | GJB规则库(120条) + 表头字段 + ID格式 + 章节结构 |

---

## 第四章 注入方式设计（26种，带学术依据）

### 4.1 术语注入（7种）

**学术依据**: MulTypo(ACL'26)键盘布局模拟拼写错误；Femmer et al.(RE'14) requirement smells的Terminology/Identity分类；Belinkov & Bisk(2018)字符级扰动四类算子(插入/删除/交换/替换)；Fischbach et al.(TSE'25) requirement smells系统定义。

| # | 注入方式 | 方法 | 难度 | 示例 |
|---|---------|------|:---:|------|
| T1 | 错字(typo) | 功能名第N字替换(N=seed确定, 替换字固定映射) | easy | "开发工程生成"→"开发操程生成" |
| T2 | 截断(truncation) | 去掉首字 | medium | "与应用软件接口"→"应用软件接口" |
| T3 | 字序(charorder) | 前两字交换 | medium | "数据获取"→"据数获取" |
| T4 | 多名(multiname) | 假设两个不同ID对应同一功能名 | hard | ID-A和ID-B都叫"数据获取" |
| T5 | 同义词冲突 | 不同词指同一实体 | hard | "显示"vs"展现"vs"呈现" |
| T6 | 缩写不一致 | 全称与缩写混用 | medium | "指挥控制"vs"C2" |
| T7 | 中英混用 | 同实体一处中文一处英文 | hard | "数据获取"vs"Data Acquisition" |

**难度分级**(参照MulTypo三级)：
- easy: 单字替换，编辑距离=1，字面可恢复
- medium: 多算子组合或编辑距离≥2，需上下文消歧
- hard: 跨实体级，需全局/语义推理

**合理性保证**：
- 替换字来自键盘布局/拼音输入混淆（非随机）
- 注入后实体"仍指同一事物"（仅表层不一致）
- 每条注入标注对应requirement-smell类型

### 4.2 参数注入（6种）

**学术依据**: FSARC七类矛盾分类法(数值矛盾/单位矛盾/允许-禁止矛盾)；S3CDA(arXiv:2206.13690)实体值冲突检测；ContractCheck(arXiv:2504.18422)量纲一致性约束；srs_kb.json的operator_dictionary和conflict_rules。

| # | 注入方式 | 方法 | 难度 | 示例 |
|---|---------|------|:---:|------|
| P1 | 数值修改(value_double) | 参数值×2 | medium | 8GB→16GB |
| P2 | 单位替换(unit_replace) | 单位替换不换算数值 | medium | 8GB→8MB |
| P3 | 属性交换(attr_swap) | 接收方/类型互换 | medium | 接收方"本系统"→"高" |
| P4 | 操作符矛盾(operator_conflict) | 同参数≤vs≥ | hard | "响应时间≤5ms" vs "≥10ms" |
| P5 | 值域越界(range_violation) | 超出专家词典值域 | hard | "可用性=120%"(上限100%) |
| P6 | 精度不一致(precision_mismatch) | 近似vs精确 | hard | "≈100ms" vs "=100.00ms" |

**Z3验证gate**（关键可信度保证）：
- 注入后对约束集跑Z3，`unsat`才确认为真矛盾
- `solver.unsat_core()`返回矛盾源约束，作为gold label证据
- 避免Korn 2026(arXiv:2606.25550)指出的"合成数据不可靠"问题

**专家词典驱动**：
- 23参数的`value_range`确保注入后仍在/超出合理区间
- 10单位族的`conversions`表自动生成"换算后不等"的真矛盾
- `operator_dictionary`的同义词生成自然语言变体

### 4.3 逻辑注入（6种）

**学术依据**: FlowVQA(ACL'24)四类问题(事实检索/应用场景/引用推理/拓扑推理)；Femmer et al.(RE'14) process/behavioral inconsistency；van der Aalst WF-net soundness；程序分析经典dangling/undefined reference。

| # | 注入方式 | 方法 | 难度 | 示例 |
|---|---------|------|:---:|------|
| L1 | 步骤交换(step_swap) | 流程步骤2和3交换 | medium | 1→3→2→4 |
| L2 | 异常流悬挂(dangling_ref) | 引用不存在的异常流编号 | medium | 引用E9但未定义E9 |
| L3 | 功能缺失(func_missing) | 正文缺少表格中某功能 | medium | 表8功能，文7功能 |
| L4 | 前置条件冲突(precondition_conflict) | 删除/修改前置条件 | hard | 用例表前置条件与图不一致 |
| L5 | 死异常流(dead_exception) | 定义了但无人引用 | easy | 定义E5但无用例引用 |
| L6 | 时序矛盾(temporal_conflict) | "先A后B" vs "先B后A" | hard | 步骤顺序与正文描述矛盾 |

**FlowVQA四类问题映射**：
- Fact Retrieval(事实检索) → 正例基线(查询功能属性)
- Applied Scenario(应用场景) → L1步骤交换检测
- Flow Referential(引用推理) → L2异常流悬挂检测
- Topological(拓扑) → L3功能缺失检测

**步骤序列提取**：
- 表格侧：解析table.csv的"主事件流"编号行 → 有序序列
- 图像侧：VLM提取流程图节点序列
- 对比：LCS(最长公共子序列)/编辑距离定位偏差

### 4.4 GJB合规注入（7种）

**学术依据**: Femmer et al.(REJ'13) requirement smells首提；Veizaga, Shin & Briand(IEEE TSE'24)系统定义smell为质量准则违规；Zhigalova & Sukhov(SYRCoSe'16)文档模板合规检测；NALABS(Rajkovic & Enoiu'22) format smells检测。

| # | 注入方式 | 方法 | 难度 | GJB规则 | 示例 |
|---|---------|------|:---:|---------|------|
| G1 | 字段缺失(field_remove) | 删除表头必填字段 | medium | GJB-001 | 缺少"项目唯一标识符"列 |
| G2 | 章节缺失(chapter_remove) | 假设缺少某章 | easy | GJB-003 | 缺少第3章(需求) |
| G3 | 图表引用缺失(fig_ref_missing) | 正文未引用图/表 | medium | GJB-005 | 正文未提"见图3" |
| G4 | 追溯链断裂(trace_break) | 追溯表缺少某需求映射 | hard | RULE-078/079 | 需求ID在追溯表中缺失 |
| G5 | 合格性方法缺失(qual_missing) | 合格性表缺测试方法 | medium | RULE-077/090 | 性能需求缺"测试D"方法 |
| G6 | 占位符未替换(placeholder_unreplaced) | 模板占位符未替换 | easy | RULE-019 | 标题含"(X)(Y)"未替换 |
| G7 | 编号不连续(numbering_gap) | 章节编号跳跃 | easy | RULE-007/018 | 3.7→3.9缺少3.8 |

**注**: 原方案中的"id_lowercase"学术依据较弱(GJB未显式规定大小写)，替换为G6占位符未替换(RULE-019明确要求)和G7编号不连续(RULE-007/018)。

**120条规则覆盖**：
- 当前3种注入覆盖38条规则(format 14 + structure 24子集)
- 扩展到7种后覆盖82条(+content 53子集 + interface 21子集)
- 高频违规(基于真实数据)：章节完整性(87.5%)、接口特征不完整、合格性缺失

---

## 第五章 四段式合成方法

### 5.1 阶段1: 事实提取（确定性，可复现）

从每个pair提取5类真实事实：

```
事实类型1: 功能名(func_name)
  来源: pair的meta.func_names + 表格"Use case名称"列
  示例: {value:"开发工程生成", id:"PZXQ-GN-JMKFKJ-JMKF-KFGCSC", source:"table_row2"}
  覆盖: sc1/sc2/sc3/sc4/sc5/sc7 (346个pair)

事实类型2: 接口属性(interface_attr)
  来源: sc3接口表的发送方/接收方/接口类型列
  示例: {attr:"receiver", value:"本系统", source:"table_row1"}
  覆盖: sc3 (30个pair)

事实类型3: 数值参数(numeric_param)
  来源: 表格+正文的数值(正则提取) + 专家词典匹配
  示例: {param:"内存", value:8, unit:"GB", source:"table+text"}
  覆盖: 含数值的pair

事实类型4: 表头字段(header_field)
  来源: 表格第一行(rows[0])
  示例: {field:"项目唯一标识符", source:"table_header"}
  覆盖: 有表格的pair(sc1-sc7, 346个)

事实类型5: 正文功能列表(text_func_list)
  来源: 正文中的功能名列表(正则"包括：A、B、C"提取)
  示例: {names:["开发工程生成","组件配置填写",...], source:"text"}
  覆盖: 正文含功能列表的pair
```

### 5.2 阶段2: 规则化注入（可控，可追溯，可复现）

对每个事实，按四类不一致各生成1条正例+1条注入：

```
正例(consistent): 基于真实事实，确认一致性
  → 答案: "一致。表格和图中均使用「X」。"

注入(inconsistent): 规则化修改事实(26种方法)
  → 答案: 由规则确定(不是LLM判断)
  → method字段: 记录注入方法(可追溯)
  → seed=42: 固定随机种子(可复现)
```

### 5.3 阶段3: LLM改写（自然化中文QA，核心事实不变）

**LLM的职责**：把规则化的事实+注入改写成自然中文问答

**LLM不做的事**：
- ❌ 不决定"改什么"（规则决定）
- ❌ 不判断"对不对"（规则确定答案）
- ❌ 不编造事实（从文档提取）

**Prompt设计**：
```
你是SRS需求文档一致性校验专家。将以下结构化事实改写为自然中文QA对。

文档: {doc}
章节: {section}
图: {image_caption}
表: {table_caption}

真实事实(从文档提取):
{fact_json}

注入信息(规则化, 可复现):
{injection_json}

正确答案(规则确定, 不要修改结论):
{correct_answer}

要求:
1. 用{image}/{table}/{text}占位符表示多模态输入位置
2. 问题要自然(像真实用户提问)
3. 答案必须与"正确答案"结论一致(可以改写语言, 但结论不变)
4. 只输出JSON: {"question":"...","answer":"..."}
```

### 5.4 阶段4: 双LLM验证（消除偏误）

```
验证1(kimi): 判断QA答案是否与规则确定的correct_answer一致
验证2(claude): 判断QA问题是否自然、占位符是否正确

只保留两者都通过的QA
→ 消除单LLM偏误
```

---

## 第六章 输出格式（MMQA风格 + 占位符）

### 6.1 QA格式（17个字段）

```json
{
  "qid": "srs_trusted_sc1_00001",
  "scene": "sc1_usecase_capability",
  "split": "train",
  "pair_id": "1_004",

  "question": "表{table}中功能「开发操程生成」与图{image}的用例名称是否一致？如不一致请指出差异。",
  "placeholders": {
    "image": "data/.../image.png",
    "table": "data/.../table.csv",
    "text": "data/.../text.txt"
  },
  "modalities": ["image", "table"],

  "answer": "不一致。正确名称为「开发工程生成」，表中写为「开发操程生成」，第2字「发」被误写为「操」，属于错字。",

  "inconsistency_type": "terminology",
  "subtype": "char_replace",
  "label": "inconsistent",
  "is_injected": true,

  "inject_detail": "char_replace[pos=1, 发→操]",
  "rule_id": "TERM-001",
  "context_note": "注入场景: 原始文档未修改, inject_detail描述假设引入的错误",

  "fact": {
    "type": "func_name",
    "value": "开发工程生成",
    "id": "PZXQ-GN-JMKFKJ-JMKF-KFGCSC",
    "source": "table_row2"
  },
  "injection": {
    "original": "开发工程生成",
    "injected": "开发操程生成",
    "method": "char_replace[pos=1, 发→操]",
    "correct_answer": "不一致。第2字「发」被误写为「操」"
  },

  "evidence": {
    "doc": "02界面集成框架...",
    "section": "1.8.1",
    "image_caption": "图4 界面开发用例图",
    "table_caption": "表3 界面开发能力标识"
  },

  "difficulty": "medium",
  "source": "fact_extracted+rule_injected+llm_rewritten",
  "verified_by": ["kimi", "claude"],
  "verified": true
}
```

### 6.2 按sc1-sc8组织

```
data/gjb_438c/data_assets/srs_qa_trusted/
├── sc1_usecase_capability.json
├── sc2_flowchart_usecase.json
├── sc3_interface_interface.json
├── sc4_flowchart_capability.json
├── sc5_function_capability.json
├── sc7_usecase_usecase.json
├── sc8_pure_image.json
└── all_scenes.json
```

### 6.3 train/dev/test划分

按文档号划分（防止数据泄漏）：
- train: 文档01-10
- dev: 文档11-13
- test: 文档14-16

---

## 第七章 可信度论证（7条）

| # | 论据 | 具体保证 |
|---|------|---------|
| 1 | **事实真实性** | 从366个真实pair提取，每条事实带source(表格第N行/正文) |
| 2 | **注入可控性** | 26种注入方法全部确定性(seed=42)，每条带method字段可追溯 |
| 3 | **答案确定性** | 注入QA的答案由规则确定，LLM只改写语言不改结论 |
| 4 | **双LLM验证** | kimi+claude交叉验证，只保留两者都通过的 |
| 5 | **Z3验证gate** | 参数矛盾注入后跑Z3，unsat才确认为真矛盾(P4/P5/P6) |
| 6 | **可复现性** | 固定seed+确定性规则+固定prompt，同样输入永远同样输出 |
| 7 | **学术依据** | 每类注入有论文支撑：MulTypo(ACL'26)/Femmer(RE'14)/FlowVQA(ACL'24)/FSARC |

### 与Korn 2026(arXiv:2606.25550)负面结论的对比

Korn指出"LLM无法可靠生成requirement smells"。我们的方案解决了这个问题：
- Korn的问题：纯LLM自由生成→不可控
- 我们的方案：规则注入+LLM改写→注入可控，答案规则确定，双LLM验证

---

## 第八章 预期产出

```
366个pair × (4类不一致 × 1正例 + 1注入) = 366 × 8 = 2928条
但不是每个pair都适用四类(sc8无表, sc2无接口属性):
  实际: ~2000条(去重+过滤后)
  验证后: ~1500条(双LLM验证通过率~75%)

按场景:
  sc1: ~800条 (141pair × 5-6条/pair)
  sc2: ~500条 (90pair × 5-6条/pair)
  sc3: ~200条 (30pair × 6-7条/pair)
  sc4: ~300条 (49pair × 6条/pair)
  sc5: ~150条 (27pair × 5-6条/pair)
  sc7: ~50条 (9pair × 5-6条/pair)
  sc8: ~0条 (无表格, 需VLM生成)

正负比: 1:1 (每类正例+注入各1条)
四类均衡: 术语/参数/逻辑/GJB 各~500条
难度分布: easy ~30% / medium ~45% / hard ~25%
全部中文
全部含{image}/{table}/{text}占位符(适用时)
```

---

## 附录: 26种注入方法速查表

| # | 类型 | 方法 | 难度 | 学术依据 |
|---|------|------|:---:|---------|
| T1 | 术语 | 错字(typo) | easy | MulTypo(ACL'26) |
| T2 | 术语 | 截断(truncation) | medium | Belinkov(2018) |
| T3 | 术语 | 字序(charorder) | medium | Belinkov(2018) |
| T4 | 术语 | 多名(multiname) | hard | Femmer(RE'14) |
| T5 | 术语 | 同义词冲突 | hard | Fischbach(TSE'25) |
| T6 | 术语 | 缩写不一致 | medium | Fischbach(TSE'25) |
| T7 | 术语 | 中英混用 | hard | CompliAT(2024) |
| P1 | 参数 | 数值修改 | medium | FSARC/S3CDA |
| P2 | 参数 | 单位替换 | medium | ContractCheck(2025) |
| P3 | 参数 | 属性交换 | medium | FSARC |
| P4 | 参数 | 操作符矛盾 | hard | srs_kb operator_dict |
| P5 | 参数 | 值域越界 | hard | srs_kb value_range |
| P6 | 参数 | 精度不一致 | hard | srs_kb physics_constraint |
| L1 | 逻辑 | 步骤交换 | medium | FlowVQA(ACL'24) |
| L2 | 逻辑 | 异常流悬挂 | medium | 程序分析 |
| L3 | 逻辑 | 功能缺失 | medium | Femmer(RE'14) |
| L4 | 逻辑 | 前置条件冲突 | hard | LOGIC-002 |
| L5 | 逻辑 | 死异常流 | easy | LOGIC-003 |
| L6 | 逻辑 | 时序矛盾 | hard | LTL/CTL |
| G1 | GJB | 字段缺失 | medium | Femmer(REJ'13) |
| G2 | GJB | 章节缺失 | easy | Zhigalova(2016) |
| G3 | GJB | 图表引用缺失 | medium | RULE-010 |
| G4 | GJB | 追溯链断裂 | hard | RULE-078/079 |
| G5 | GJB | 合格性方法缺失 | medium | RULE-077/090 |
| G6 | GJB | 占位符未替换 | easy | RULE-019 |
| G7 | GJB | 编号不连续 | easy | RULE-007/018 |
