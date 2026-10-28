# 64. L1规则层配置化改造：rule pack设计文档

> 主题：把L1确定性专家的硬编码域知识（表格签名/列映射/模板正则/词表/阈值/窗口）从
> Python源码迁出到声明式rule pack配置，引擎从配置执行。
> 铁律：**行为保持优先于配置化彻底性**——91QA(0.9121/0.7212)、违例评测(16/17)、
> 跨文档回归数字逐位不变；公开API不变（只允许追加可选`rulepack`注入参数）。

## 1. 改造动机

L1层专家（evidence_compiler/e1/id_join/enum_join/sequence/trace）的检查逻辑中
混着两类知识：

- **"检查什么、匹配什么"**（域知识）：能力表表头签名、`PZXQ-` ID模式、
  "系统提示X，用例结束"的E1模板正则、通用词表、配对阈值0.28……
  这些知识**因文档而异**（04号vs06号的表头变体、ID族前缀），却硬编码在
  源码里——换一份文档就要改代码。
- **"怎么比、怎么判"**（引擎能力）：注册表join、主体聚簇、NW对齐、Z3求解、
  三态裁决语义。这些与具体文档无关，是可复用的算法资产。

现状问题：`gjb_rule_engine`（120条规则库驱动）已证明"检查内容进配置、
句式分析留引擎"可行（半配置化范本），但其余6个专家的域知识仍锁在源码里。
跨文档泛化评测（crossdoc06）显示04号拟合的签名/词表在06号上大面积失效，
而修复手段只能是改代码——配置化后，06号变体只需要一份`doc06_v1.json`。

## 2. 盘点表（逐项硬编码域知识盘点）

配置化难度：**易**=纯数据搬移；**中**=需要schema建模；**引擎**=按分层原则留在
引擎（算法/语法解析）；**暂缓**=可配置化但本次不动（行为保持优先/不在改造清单）。

### 2.1 evidence_compiler.py（表格类型签名+列语义映射）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| EC-01 | L46-48 | 列签名 | `USE_CASE_COLUMNS` 用例表7字段 | 易 | `table_schemas.use_case_table.columns` |
| EC-02 | L49 | 列签名 | `FLOW_SUBCOLUMNS` 主事件流3子列 | 易 | `table_schemas.use_case_table.flow_subcolumns` |
| EC-03 | L59-64 | 模板正则 | `_USECASE_NAME/_ACTORS/_USECASE_FIELD`（用例字段行模式） | 易 | `table_schemas.use_case_table.use_case_fields` |
| EC-04 | L65 | 列映射 | `_FIELD_CANON`（简要说明→概述） | 易 | 同上`.field_canon` |
| EC-05 | L66-67 | 模板正则 | `_FLOW_HEADER/_SUBHEADER`（主事件流/子表头） | 易 | 同上`.flow_header_pattern/.subheader_pattern` |
| EC-06 | L69 | 词表 | `_MINMAX_HEADERS`（最大值/最大差/最小值/最小差） | 易 | 值域表签名的`any_header_groups` |
| EC-07 | L70 | 模板正则 | `_USECASE_SIG` | 易 | 用例表签名`raw_regex` |
| EC-08 | L72-77 | 列映射 | `_CAPABILITY_CANON`（Usecase名称→Use case名称等4条） | 易 | `table_schemas.capability_table.canon_map` |
| EC-09 | L78 | 列映射 | `_VALUE_DOMAIN_CANON`（最大差→最大值等2条） | 易 | `table_schemas.value_domain_table.canon_map` |
| EC-10 | L79-85 | 列映射 | `_TRACE_CANON`（5条追踪表头规范化） | 易 | `table_schemas.trace_table.canon_map` |
| EC-11 | L86-91 | 列映射 | `_QUALIFICATION_CANON`（4条） | 易 | `table_schemas.qualification_table.canon_map` |
| EC-12 | L99-104 | 键列 | `_KEY_COLUMNS`（4种表的行键列） | 易 | 各`.key_columns` |
| EC-13 | L106-122 | 列画像 | `_COLUMN_PROFILES`（表型×claim类型→聚焦列集） | 易 | 各`.column_profiles` |
| EC-14 | L370-391 | 分类签名 | `_classify_table`：能力/接口/值域/合格性/追踪/用例6种表头匹配（含caption"追踪性"、raw含"主事件流"线索） | 中 | 各`.signatures`+`classify_order` |
| EC-15 | L399-408 | 方向判定 | 追踪表方向=首列前缀"任务书"；正/逆键列序 | 易 | `.direction_first_column_prefix/.trace_key_columns` |
| EC-16 | L124-133 | 提示正则 | `_IDENTIFIER_TOKEN/_EXCEPTION_HINT/_NUMERIC_HINT/_STEP_HINT/_ENUM_*`（claim类型路由） | 引擎 | 留引擎：claim路由是聚焦视图的**下游判定语义**，与表型无关 |
| EC-17 | L138-147 | 语法正则 | `_MM_NODE/_MM_EDGE`（Mermaid图语法解析） | 引擎 | 留引擎：图语法是解析器能力，非域知识 |
| EC-18 | L51-57 | 语法正则 | `_TR/_CELL_TAG/_ATTR`（HTML网格重建） | 引擎 | 留引擎：文档格式力学 |

### 2.2 e1_expert.py（E1异常流模板专家）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| E1-01 | L52 | 模板正则 | `_E_ENTRY_HEAD`（E条目头切分） | 易 | `extraction_templates.e1_entry_head` |
| E1-02 | L53-55 | 模板正则 | `_E_ENTRY_PARSE`（异常流E1：系统提示X，用例结束） | 易 | `extraction_templates.e1_entry_parse` |
| E1-03 | L57 | 词表正则 | `_EXCEPTION_CLAIM`（异常claim触发词，含`E\d`） | 中 | `extraction_templates.e1_exception_claim`（含模式片段） |
| E1-04 | L58 | 模板正则 | `_CLAIMED_E_ID` | 易 | `extraction_templates.e1_claimed_e_id` |
| E1-05 | L59-62 | 模板正则 | `_ANSWER_PROMPT_QUOTED`（**提示动词表**提示/显示/给出/返回/弹出+引号结构） | 中 | `extraction_templates.e1_answer_prompt_quoted`（动词表内嵌于结构，拆分会引入行为风险，整式承载） |
| E1-06 | L63-64 | 模板正则 | `_ANSWER_PROMPT_PLAIN` | 中 | `extraction_templates.e1_answer_prompt_plain`（同上） |
| E1-07 | L65-67 | 模板正则 | `_PROMPT_CONNECTIVE`（连接词截断） | 易 | `extraction_templates.e1_prompt_connective` |
| E1-08 | L70-73 | 模板正则 | `_GENERIC_PROMPT_TEXT`（通用名词短语丢弃） | 易 | `extraction_templates.e1_generic_prompt_text` |
| E1-09 | L76-78 | 词表 | `_INVALID_PROMPT_WORDS`（**无效词表**24词，纯平铺交替） | 易 | `term_vocabularies.e1_invalid_prompt_words` |
| E1-10 | L81-82 | 模板正则 | `_PROMPT_Q`（问题问提示文本本身的指示） | 易 | `extraction_templates.e1_prompt_q` |
| E1-11 | L85-87 | 模板正则 | `_EVIDENCE_PROMPT_VERB`（证据侧提示动词span） | 中 | `extraction_templates.e1_evidence_prompt_verb` |
| E1-12 | L88-90 | 模板正则 | `_EVIDENCE_TRIGGER`（**触发条件模式**如果/若/当/在…时） | 易 | `extraction_templates.e1_evidence_trigger` |
| E1-13 | L91 | 处置词表 | `_CONTINUE_WORDS`（继续/恢复/重试/重新(执行\|开始\|处理)） | 中 | `extraction_templates.e1_continue_words`（含结构化片段，整式承载） |
| E1-14 | L92 | 处置词表 | `_END_WORDS`（结束/终止/中止，纯平铺） | 易 | `term_vocabularies.e1_end_words` |
| E1-15 | L96-102 | 处置模式 | `_CONTINUE_CLAIM/_END_CLAIM`（处置动词×用例名词邻接的前瞻断言） | 中 | `extraction_templates.e1_continue_claim/e1_end_claim` |
| E1-16 | L103-104 | 模板正则 | `_ENDING_ONLY` | 易 | `extraction_templates.e1_ending_only` |
| E1-17 | L106-108 | 词表 | `_GENERIC_WORDS`（**通用词表**15词，纯平铺） | 易 | `term_vocabularies.e1_generic_words` |
| E1-18 | L109 | 模板正则 | `_PUNCT`（标点类） | 易 | `extraction_templates.e1_punct` |
| E1-19 | L110 | 修剪字符 | `_TRIM_EDGES`（strip字符集） | 易 | `join_params.e1.trim_edges` |
| E1-20 | L112 | 字段表 | `_FLOW_FIELDS`（Actor的动作/系统的动作/动作约束） | 易 | `term_vocabularies.e1_flow_fields` |
| E1-21 | L114-120 | 阈值 | `_CONF_*` 7个置信度 | 易 | `thresholds.e1_conf_*` |
| E1-22 | L554-556 | 模板正则 | `_E1_ASSERTION/_EXCEPTION_Q` | 易 | `extraction_templates.e1_e1_assertion/e1_exception_q` |

### 2.3 id_join_expert.py（ID→主体注册表join）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| IJ-01 | L49 | ID模式 | `PZXQ_ID_RE`（`PZXQ-[A-Z0-9-]+`域标识符） | 易 | `extraction_templates.id_pattern` |
| IJ-02 | L53-57 | 绑定策略 | `_BINDING_RE`（"X的项目唯一标识符：ID"语句级绑定，含系词组合） | 易 | `extraction_templates.id_binding` |
| IJ-03 | L60-63 | 绑定策略 | `_SECTION_TITLE_RE`（节标题"3.2.x名称（ID）"） | 易 | `extraction_templates.id_section_title` |
| IJ-04 | L67-70 | 绑定策略 | `_ROLE_TAIL_RE`（answer侧角色词尾） | 易 | `extraction_templates.id_role_tail` |
| IJ-05 | L73-74 | 绑定策略 | `_BRACKET_SUBJECT_RE`（括号主体别名） | 易 | `extraction_templates.id_bracket_subject` |
| IJ-06 | L77 | 窗口 | `_ID_WINDOW=32`（ID前主体提取窗口，源码实际值为32字符） | 易 | `join_params.id_join.id_window` |
| IJ-07 | L78-83 | 模板正则 | `_SEGMENT_SPLIT/_NOUN_RUN/_WINDOW_TAIL_STRIP/_LEADING_TABLE_REF/_SUBJECT_ROLE_TRIM`（主体提取配套模式） | 易 | `extraction_templates.id_*` |
| IJ-08 | L81 | 修剪字符 | `_SEGMENT_EDGE_STRIP` | 易 | `join_params.id_join.segment_edge_strip` |
| IJ-09 | L86-91 | 词表 | `_SUBJECT_STOPWORDS`（泛指词/引导词→无主体，30词） | 易 | `term_vocabularies.id_subject_stopwords` |
| IJ-10 | L126-129 | 族过滤 | `_id_family`前两段（PZXQ-GN/PZXQ-JK） | 易 | `join_params.id_join.family_segments=2` |
| IJ-11 | L111-119 | 主体匹配 | `_subject_match`≥3字符包含 | 引擎 | 精确优先分层/包含方向是join算法语义；`subject_contain_min_chars=3`进join_params，分层策略留引擎 |
| IJ-12 | L440-448 | 阈值 | 裸ID support 0.9/NIE 0.5 | 易 | `thresholds.id_join_*` |
| IJ-13 | — | （新增能力） | 可选`id_family_prefixes`：限定本pack关注的ID族（doc06=PZXQ-YXZCFW） | 中 | `join_params.id_join.id_family_prefixes`（缺省=不过滤，即04行为） |

### 2.4 enum_join_expert.py（枚举join）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| EJ-01 | L55 | 值域 | `_TERMINAL_BASES`（{桌面,平板,手持}终端形态封闭值域） | 易 | `term_vocabularies.enum_terminal_bases` |
| EJ-02 | L56 | 值域 | `_PHASE_BASES`（{开发阶段,运行阶段}） | 易 | `term_vocabularies.enum_phase_bases` |
| EJ-03 | L59-70 | 字段语义 | `_KIND_BY_FIELD/_FIELD_LABEL`（字段→声明kind/描述标签） | 易 | `join_params.enum_join.field_kinds/field_labels` |
| EJ-04 | L73-76 | 字段模式 | `_FIELD_VALUE_RE`（需求重用/方式名称/运行状态/对应的任务书功能性能） | 易 | `extraction_templates.enum_field_value` |
| EJ-05 | L80-83 | 枚举句模式 | `_ENUM_RE`（"X包括A、B、C"） | 易 | `extraction_templates.enum_sentence` |
| EJ-06 | L86-94 | 模板正则 | `_ID_BINDING_RE/_SECTION_TITLE_RE`（行主体→父主体聚合） | 易 | `extraction_templates.enum_id_binding/enum_section_title` |
| EJ-07 | L97-100 | 模板正则 | `_DEVICE_ENUM_RE`（"支持在A、B上运行"） | 易 | `extraction_templates.enum_device` |
| EJ-08 | L102-105 | 模板正则 | `_QUESTION_SUBJECT_RE`（问题主题回退） | 易 | `extraction_templates.enum_question_subject` |
| EJ-09 | L107-116 | 模板正则 | `_MEMBER_VALID/_MEMBER_SPLIT/_COUNT_FUNCTION_SUFFIX/_SUBJECT_ROLE_SUFFIX/_LEADING_TABLE/_GENERIC_SUBJECT` | 易 | `extraction_templates.enum_*` |
| EJ-10 | L119-129 | 词表 | `_SUBJECT_GARBAGE_INFIXES`（13词）+`_GENERIC_SUBJECTS`（37词） | 易 | `term_vocabularies.enum_subject_garbage_infixes/enum_generic_subjects` |
| EJ-11 | L131-134 | 词表 | `_DEV_TAIL_STRIP`（DEV声明尾部剥离词表，含标点） | 易 | `term_vocabularies.enum_dev_tail_strip` |
| EJ-12 | L253 | 阶段切词 | `re.findall(r"开发阶段|运行阶段")`（内联） | 易 | `extraction_templates.enum_phase_words` |
| EJ-13 | L465 | 成员切分 | `re.split(r"[、和]")`（内联DEV成员切分） | 易 | `extraction_templates.enum_member_split_device` |
| EJ-14 | L417-418 | 主体窗口 | DEV局部主体窗口24字符+名词run模式（内联） | 易 | `join_params.enum_join.device_subject_window` + `extraction_templates.enum_device_subject_run` |
| EJ-15 | 错字距离 | `levenshtein(...)==1`两处 | **错字距离=1** | 易 | `join_params.enum_join.typo_distance=1` |
| EJ-16 | L311-320 | 块隔离 | row_enum按(parent, evidence_id)分块聚合（同父ID多表不并集） | 中 | `join_params.enum_join.row_enum_block_isolated=true`（分块语义留引擎，开关进配置） |

### 2.5 sequence_expert.py（序列对齐）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| SQ-01 | L52 | 步骤正则 | `_STEP_RE`（`(\d+)[.．、]`编号标点混用统一捕获） | 易 | `extraction_templates.seq_step` |
| SQ-02 | L61 | 阈值 | `_MATCH_TH_DET=0.28`（字符重合配对阈值） | 易 | `thresholds.seq_pair_det` |
| SQ-03 | L62-64 | 阈值 | `_MATCH_TH_BGE=0.60`（BGE句级阈值，≠EMB_TH_LOCAL=0.78） | 易 | `thresholds.seq_pair_bge` |
| SQ-04 | L53-54 | 字段表 | `_FLOW_FIELDS/_EXCEPTION_FIELD_RE` | 易 | `term_vocabularies.seq_flow_fields`+`extraction_templates.seq_exception_field` |
| SQ-05 | L55-58 | 模板正则 | `_QUESTION_SCOPE_RE/_PREAMBLE_RE/_PUNCT_RE` | 易 | `extraction_templates.seq_*` |
| SQ-06 | L65 | 算法参数 | `_GAP_PENALTY=-0.5`（NW罚分） | 引擎 | 留引擎：NW对齐算法参数（"怎么比"） |
| SQ-07 | L66 | 算法参数 | `_EXCEPTION_BASE=10000`（异常流位置基准） | 引擎 | 留引擎 |
| SQ-08 | L67 | 窗口 | `_MIN_STEP_CHARS=8` | 易 | `join_params.sequence.min_step_chars` |
| SQ-09 | L70-71 | 模板正则 | `_FLOW_QUESTION_RE`（流程型问题指示词） | 易 | `extraction_templates.seq_flow_question` |
| SQ-10 | L73 | 词表 | `_FAILURE_KEYWORDS`（失败/错误/异常） | 易 | `term_vocabularies.seq_failure_keywords` |
| SQ-11 | L75-77 | 词表 | `_TEMPORAL_CONNECTORS`（然后/随后/…8词） | 易 | `term_vocabularies.seq_temporal_connectors` |
| SQ-12 | L78 | 窗口 | `_PARALLEL_ITEM_AVG_LEN=40`（并列长项平均长度阈值） | 易 | `join_params.sequence.parallel_item_avg_len` |
| SQ-13 | L80 | 阈值 | `_FAILURE_KEYWORD_RATIO=0.5` | 易 | `thresholds.seq_failure_keyword_ratio` |
| SQ-14 | L83 | 模板正则 | `_SUBSTANTIVE_STEP_RE`（≥2连续汉字） | 易 | `extraction_templates.seq_substantive_step` |
| SQ-15 | L576 | 阈值 | 通道置信度0.9(确定性)/0.8(BGE) | 易 | `thresholds.seq_conf_det/seq_conf_bge` |

### 2.6 trace_expert.py（追踪表join）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| TR-01 | L42 | 词表 | `_NON_TRACK_NOTES`（不追踪/不跟踪/不追溯） | 易 | `term_vocabularies.trace_non_track_notes` |
| TR-02 | L43-44 | 窗口 | `_NOTE_COLUMN_COUNT=5`/`_MAX_ANSWER_PAIRS=4` | 易 | `join_params.trace.note_column_count/max_answer_pairs` |
| TR-03 | L98-103 | 表头签名+方向判定 | `_table_direction`（表头"任务书"早于"本文档"→正向） | 易 | `table_schemas.trace_table.direction_markers`（顺序比较逻辑留引擎） |
| TR-04 | L46-52 | 模板正则 | `_SECTION_SPLIT/_SEGMENT_SPLIT/_RELATION_WORDS/_TRACE_RELATION_WORDS/_SECTION_TOKEN/_TASKBOOK_SECTION/_HEADING_NUMBER` | 易 | `extraction_templates.trace_*` |
| TR-05 | L106-130 | 行分类 | `_classify_row`空单元格剔除后的列数启发 | 引擎 | 留引擎：解析器容错启发式（"怎么解析"） |

### 2.7 gjb_rule_engine.py（半配置化范本）

| # | 位置 | 类型 | 内容 | 难度 | 去向 |
|---|------|------|------|------|------|
| GJ-01 | L59 | 规则库路径 | `RULE_LIBRARY_PATH`（120条规则库） | 易 | `RulePack.gjb_rule_library_path`（引擎`load_rule_library(path=None)`改从pack取默认路径） |
| GJ-02 | L66-105 | 簇映射 | `RULE_CLUSTERS`（GJB-01~11→rule_id映射+理由） | 暂缓 | 审计知识映射，已有常量文档化；进配置需设计簇schema，本次不动（行为保持优先） |
| GJ-03 | L116+ | 语言学模板 | 情态标记/宾语提取句式分析器 | 引擎 | 留引擎：句式分析是编译器能力，**不含GJB检查内容词**（范本的设计原则） |

### 2.8 coverage_expert.py / numeric_z3_expert.py（参数化点盘点，本次暂缓）

| # | 文件 | 参数化点 | 决定 |
|---|------|----------|------|
| CV-01 | coverage | `_QUALIFICATION_TARGETS`（合格性覆盖声明触发词6项）、`_ALARM_ELEMENTS`（GJB-06报警要素封闭清单5组同义词）、`_GENERIC_SUBJECTS`、`_RANGE/_UNIVERSAL/_HEADING`等声明模式 | 暂缓：不在本次专家改造清单；且coverage与gjb_presence_expert存在词表import耦合（`_ABSENCE_RE/_answer_gjb_claims`），拆表需同步两处，风险/收益比不佳 |
| NZ-01 | numeric_z3 | `_CN_UNIT_ALIASES`（中文单位别名）、`_EXTRA_UNIT_FACTORS`（补充单位因子13项）、`_FIELD_NAME_OPS`（字段→算子7项）、`_AGGREGATE_MARKERS`、`Z3_TIMEOUT_MS=500` | 暂缓：单位族知识已有`srs_kb.json`半配置载体（函数内读取+lru_cache），域词典统一进rule pack属后续词典层整合 |

**盘点汇总**：6个专家+2个暂缓模块共约60项硬编码域知识；其中**约48项可配置化**
（本次全部迁入`srs_gjb_v1.json`），**9项按分层原则留引擎**（join/NW/Z3/HTML与
Mermaid语法解析/claim路由），**3项暂缓**（coverage词表、numeric词典、GJB簇映射）。

## 3. rule pack schema设计

```
config/rulepacks/srs_gjb_v1.json
├── pack_id: "srs_gjb_v1"                     # 唯一标识
├── description: str                          # 人类可读说明
├── gjb_rule_library_path: "knowledge/gjb_438c_rules_full.json"
├── classify_order: [kind, ...]               # 表型分类的签名判定顺序(语义敏感)
├── table_schemas: {                          # 表格签名+列语义映射
│     capability_table: {
│       signatures: [SignatureSpec, ...]      # 备选签名, 命中任一即该型
│       canon_map: {原始表头: 规范列名}
│       key_columns: [行键列]
│       column_profiles: {claim类型: [聚焦列]}   # 缺"default"为兜底
│     },
│     use_case_table: {
│       signatures: [...]
│       columns: [7字段]                       # USE_CASE_COLUMNS
│       flow_subcolumns: [3子列]
│       use_case_fields: {name/actors/field/flow_header/subheader模式, field_canon}
│     },
│     interface_table / value_domain_table: {signatures, canon_map, key_columns, column_profiles},
│     trace_table: {signatures, canon_map, key_columns, column_profiles,
│                   direction_first_column_prefix, direction_markers,
│                   trace_key_columns: {forward: [...], reverse: [...]}},
│     qualification_table: {...},
│     generic_table: {signatures: []}          # 兜底型, 无签名
│   }
├── extraction_templates: {name: {pattern, flags}}   # 带命名组的正则模板(逐字迁移)
├── term_vocabularies: {name: [word, ...]}           # 平铺词表(成员判定/剥离/词干)
├── join_params: {expert: {param: value}}            # 窗口/距离/段数/开关/字符集
└── thresholds: {name: float}                        # 配对/置信/占比阈值(0~1)
```

`SignatureSpec`（一个备选签名，全部在场条件同时成立才命中）：

| 字段 | 语义 |
|------|------|
| `all_headers` | 每个列名都在规范化表头集合中（精确成员） |
| `any_header_groups` | 每组内至少一个列名在表头集合中 |
| `any_header_substring_groups` | 每组内至少有一个表头**包含**组内某子串 |
| `caption_contains_any` | 表标题含任一子串 |
| `raw_contains_any` | 原始HTML含任一子串 |
| `raw_regex` | 原始HTML命中正则 |

**词表两种引擎消费形态**（配置形态统一为字符串元组，消费点按原语义）：
1. 成员/子串/剥离判定（stopwords、garbage infixes、tail strip、temporal
   connectors…）：引擎直接`in`/`endswith`/遍历；
2. 平铺交替正则（`e1_generic_words`等原为`re.compile("A|B|C")`的词表）：
   引擎`"|".join(map(re.escape, words))`编译——词均为纯CJK/ASCII无元字符，
   编译结果与源码逐字节一致。

## 4. 配置化分层原则

- **进配置**（"检查什么、匹配什么"）：表头签名、列名规范映射、键列、列画像、
  E1/步骤/追踪行/绑定等模板正则、提示动词/通用词/无效词/处置词表、封闭值域、
  配对阈值、主体窗口、错字距离、族段数、块隔离开关、置信度。
- **留引擎**（"怎么比、怎么判"）：注册表join与主体聚簇、精确优先分层匹配、
  NW全局对齐与gap罚分、Z3三态判定、HTML网格/rowspan重建、Mermaid语法解析、
  claim类型路由、三态聚合语义（refute>NIE>support）、scope定位策略。
- **暂缓**（可配置化但行为保持优先）：coverage词表（双模块词表耦合）、
  numeric单位词典（srs_kb半配置载体）、GJB规则簇映射。

## 5. 引擎侧结构（algorithms/consistency/rulepack.py）

- `Template(name, pattern, flags)`（frozen dataclass）+ 模块级`compile_pattern`
  缓存（`(pattern, flags) -> re.Pattern`，同模式跨专家共享编译）。
- `TableSchemaSpec / SignatureSpec / UseCaseFields`（frozen dataclass）。
- `RulePack`（frozen dataclass）：`pack_id / table_schemas /
  extraction_templates / term_vocabularies / join_params / thresholds /
  gjb_rule_library_path` + 访问器：
  - `pack.template(name)` → 编译后正则（缓存，不存在→可读KeyError）
  - `pack.vocabulary(name)` / `pack.vocabulary_regex(name)`（平铺交替编译）
  - `pack.join_param(expert, key, default)` / `pack.threshold(key, default)`
  - `pack.table_spec(kind)` / `pack.classify_order`
- `load_rulepack(path) -> RulePack`：schema校验（**正则可编译**——报错带
  pack_id+模板名+re.error；**阈值∈[0,1]**；**非generic表型签名非空**；
  词表项非空字符串；pack_id非空；gjb_rule_library_path非空）+ 按解析路径缓存。
- `default_rulepack()`：惰性加载`config/rulepacks/srs_gjb_v1.json`
  （**模块顶层零I/O**，import期不读文件；首次调用时加载并缓存）。
- 专家侧统一模式：模块内`_Config`frozen dataclass + `_cfg()`惰性构建
  （`default_rulepack()`→编译），内部引用从`_cfg().xxx`取；公开函数签名
  不变。`evidence_compiler`与`id_join`额外提供可选`rulepack=None`注入参数
  （跨场景演示用，缺省走默认pack——所有既有调用行为不变）。

## 6. 跨场景配置演示（config/rulepacks/doc06_v1.json）

06号运行支撑服务相对04号的已核实变体：

1. **追踪表头变体**：06号表115/116的正向表用"本文档**的**名称/标识"（同04），
   但逆向表头为"本文档名称/标识"（**无"的"**）——默认pack的`_TRACE_CANON`
   不含该形态，列名不规范化（聚焦列画像失配）；`doc06_v1`在
   `trace_table.canon_map`追加该变体→列名规范化为`本文档名称标识`。
2. **ID族**：04号ID族为PZXQ-GN/PZXQ-JK/PZXQ-NBJK，06号全文档为
   **PZXQ-YXZCFW**族（如`PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL-GZKXXLR`）；
   `doc06_v1`把`id_pattern`收窄为`PZXQ-YXZCFW-[A-Z0-9-]+`并在
   `join_params.id_join.id_family_prefixes`声明族前缀。
3. **能力表/用例表签名**：06号能力表（表31等20张）表头与04号逐字相同
   （序号/Usecase名称/项目唯一标识符/需求描述/需求重用/方式名称/运行状态/
   对应的任务书功能/性能）——同一签名零改动覆盖；ID单元格分两个`<p>`标签
   （`<p>PZXQ-YXZCFW-GN-GZKWHGL</p><p>-GZKXXLR</p>`）由引擎
   `_strip_tags`去标签拼接为完整ID（引擎能力，无需配置）。
4. 用例表（53张"Use Case 名称：X"行式）签名/字段模式与04号一致。

演示（tests/test_rulepack.py）：同一`compile_evidence`引擎（零改动）分别用
`srs_gjb_v1`与`doc06_v1`编译06号真实content_list证据——能力表22张/用例表
53张均识别；`doc06_v1`下06号逆向追踪表列名完成规范化而默认pack不规范化
（可观察的配置差异）。

## 7. 迁移完成度与行为保持验证（执行后回填）

| 专家 | 配置化项 | 留引擎项 | 迁移状态 |
|------|----------|----------|----------|
| evidence_compiler | EC-01~15 | EC-16~18 | ✅完成（`compile_evidence/focus_views/compile_and_focus`追加可选`rulepack`注入参数，缺省走默认pack） |
| e1_expert | E1-01~22 | 三态聚合/scope策略/触发-提示混淆判定 | ✅完成 |
| id_join_expert | IJ-01~10,12,13 | IJ-11精确优先分层 | ✅完成（`build_id_registry/extract_id_claims/verify_id_joins`追加可选`rulepack`参数；新增`id_family_prefixes`族范围限定） |
| enum_join_expert | EJ-01~16 | Levenshtein/集合比对/归因策略 | ✅完成 |
| sequence_expert | SQ-01~05,08~15 | SQ-06/07（NW罚分/异常位置基准） | ✅完成 |
| trace_expert | TR-01~04 | TR-05行分类启发 | ✅完成 |
| gjb_rule_engine | GJ-01路径+GJ-02簇映射 | GJ-03句式分析 | ✅完成（GJ-02簇映射迁入pack的gjb.rule_clusters段, 带映射理由; 67号文档§6） |
| coverage_expert | CV-01词表（_QUALIFICATION_TARGETS/_GENERIC_SUBJECTS/_ALARM_ELEMENTS/共享_ABSENCE_RE） | 声明模式正则(_RANGE/_UNIVERSAL/_HEADING等, 极性裁决语义耦合) | ✅完成（词表外置+解耦gjb_presence词表import; 67号文档§6） |
| numeric_z3_expert | NZ-01词典（_CN_UNIT_ALIASES/_EXTRA_UNIT_FACTORS/_FIELD_NAME_OPS/_AGGREGATE_MARKERS） | Z3_TIMEOUT_MS(求解器资源限制)+_UNIT_TOKEN文法+_FIELD_CLASS(join语义) | ✅完成（词典外置到join_params.numeric_z3; 67号文档§6） |

> 2026-10-28更新：三个暂缓项迁移完成（程序化提取逐字一致+行为保持验证：
> 91QA 0.9121/0.7212、违例16/17、跨文档det逐位不变）。配置化覆盖度
> 60项中58项（≈97%），详见67号文档§6.4。

### 7.1 产出文件清单

| 文件 | 内容 |
|------|------|
| `algorithms/consistency/rulepack.py` | RulePack/Template/TableSchemaSpec/SignatureSpec/UseCaseFields + load_rulepack（校验+缓存）+ default_rulepack（惰性, import期零I/O） |
| `config/rulepacks/srs_gjb_v1.json` | 默认pack：7表型签名/57模板正则/14词表/5专家join_params/14阈值（**生成方式：从迁移前源码常量程序化提取，逐字一致**） |
| `config/rulepacks/doc06_v1.json` | 06号变体pack：追踪表头变体canon + ID族PZXQ-YXZCFW声明 |
| `tests/test_rulepack.py` | 19条测试：加载/校验可读报错/访问器/签名判定语义/doc06演示/import零I/O |### 7.2 行为保持验证（逐位不变，全部通过）

| 验证 | 命令 | 改造前 | 改造后 |
|------|------|--------|--------|
| 91QA | `$env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/eval_qa_module_vs_silver.py` | acc **0.9121** / macro-F1 **0.7212**（混淆矩阵与claim_methods分布逐位一致） | ✅0.9121/0.7212 |
| 违例 | `python tools/eval_violations.py` | **16/17**（deterministic与cascade一致；定位P/R 0.8/0.7059；检出通道计数一致；未检出DOC04-VIO-15） | ✅16/17 |
| 跨文档 | `python tools/eval_crossdoc.py` | n=30, deterministic macro-F1 **0.1524** / cascade **0.5309**（泛化落差、逐实例失配清单一致） | ✅0.1524/0.5309 |
| 单测 | `python -m pytest tests/test_rulepack.py tests/test_e1_expert.py tests/test_evidence_compiler.py tests/test_id_join_expert.py tests/test_enum_join_expert.py tests/test_sequence_expert.py tests/test_trace_expert.py -q` | 116 passed（6专家） | ✅135 passed（116+19规则包测试，全过） |
| 回归面 | qa_module/violation_evalset/crossdoc_evalset/gjb_rule_engine/coverage/numeric_z3/deq_pipeline/egt_synthesis/manifest等 | — | ✅176+52 passed |
| Lint | `python -m ruff check algorithms` | 零报错 | ✅零报错（含rulepack.py） |

### 7.3 doc06_v1演示结果（同一引擎零改动）

- **06号真实content_list（476块, 88张表）用doc06_v1编译**：能力表22张、
  用例表53张、值域表8张、追踪表2张全部识别——能力表表头与04号逐字相同，
  同一签名零改动覆盖；表31"故障库信息录入"行的ID单元格分两个`<p>`标签
  （`PZXQ-YXZCFW-GN-GZYJXF-GZKWHGL`+`-GZKXXLR`）由引擎`_strip_tags`
  去标签拼接为完整ID注册。
- **追踪表头变体**：06号表116逆向追踪表头"本文档名称/标识"（无"的"）——
  默认pack不规范化（列名原样保留），doc06_v1把它canon到
  "本文档名称标识"，正逆两方向判定均正确，聚焦列画像（5列）完整命中
  （`focus_views`返回任务书章节号=4.1.2的行）。
- **ID族范围限定**：`extract_id_claims("...PZXQ-YXZCFW-...", rulepack=doc06)`
  提取（主体=故障库信息录入）；`("...PZXQ-GN-SQLFW...", rulepack=doc06)`
  返回空（族不在声明范围）；同一answer用默认pack则照常提取——
  配置差异可观察、默认行为不变。

