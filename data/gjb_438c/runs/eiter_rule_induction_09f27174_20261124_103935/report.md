# P3 Eiter回路试点报告: 教师归纳rulepack vs 人工doc06_v1

> 生成: tools/eiter_rule_induction.py (99号Phase 3 / 97号§3.4)

## 评测口径

- deterministic配置 `QAConsistencyModule(use_experts=True)`
- 每pack评测于**全新子进程**(lru_cache身份盲污染排除, 见负面发现)
- 闸门(CLP式修订不回退): 91QA逐实例零回退+聚合不降; crossdoc06零新增错例+错例数单调; 专家运行时异常一票否决

## 主对照表 (crossdoc06 × 91QA回归)

| pack | crossdoc06 macro-F1 | acc | wrong | 91QA macro-F1 | acc | wrong |
|---|---|---|---|---|---|---|
| generic srs_gjb_v1 | 0.2619 | 0.3333 | 20 | 0.7212 | 0.9121 | 20 |
| manual doc06_v1 | 0.1481 | 0.2667 | 22 | 0.7212 | 0.9121 | 22 |
| teacher doc06_eiter_v1 | 0.407 | 0.4333 | 17 | 0.7212 | 0.9121 | 17 |

## 规则条目质量

- 教师pack变更数: 1
- 人工pack相对generic的diff落点数: 5
- 落点重叠: []
- 教师落点: ['extraction_templates.enum_device']
- 人工落点: ['$.join_params.id_join.id_family_prefixes+', '$.table_schemas.trace_table.canon_map.任务书名称/标识+', '$.table_schemas.trace_table.canon_map.任务书章节号+', '$.table_schemas.trace_table.canon_map.本文档名称/标识+', '$.table_schemas.trace_table.canon_map.本文档章节号+']

## 回路成本

- 教师调用: 9次 (缓存命中 9, 真实API 0)
- 评测子进程: 50次
- 墙钟: 179.1s

## 方法学负面发现

- 每个pack评测都在全新子进程中执行: numeric_z3_expert._unit_table是@lru_cache(maxsize=1)无pack身份键, gjb_presence_expert的词表正则缓存同样身份盲——进程内切换pack会继承首个pack的派生配置(历史eval_crossdoc5_onboard的in-process切换受此污染), 子进程隔离是唯一可靠口径
- 人工doc06_v1是M33时代的fork, 缺srs_gjb_v1后续新增的numeric_z3/coverage/gjb段——standalone子进程口径下crossdoc06回退(macro_f1低于generic), 历史'无差异'结论部分是缓存污染假象
- deterministic配置(QAConsistencyModule(use_experts=True))是L1规则包效应的隔离口径; 91QA主评测当前数字0.7212/0.9121

## 第1轮明细

- 失败例: 20 ({'capability_device': 6, 'capability_state': 4, 'interface_flow': 5, 'trace_binding': 5})
- 提案变更(合并后): 6, 接受: 6, 剪枝: 5, 拒绝: 0

### 教师批次[capability_device] (5失败例)
- diagnosis: 根因是enum_device模板items捕获组最小长度6: 06号answer形态『在平板、手持设备上使用』/『在桌面、平板设备上使用』中, 去掉尾缀『设备』后items仅5字符, 懒惰回溯被迫把『设备』吞入items, 成员变为『手持设备』/『平板设备』, 不在enum_terminal_bases值域→kind=functional, join不发生, refute实例(011/012)无法检出集合冲突。将最小长度降到4后, 尾缀组可正确剥离『设备/终端』, 成员归一为值域成员, kind=terminal, 与注册表封闭集合比较即产生refute。至于001/002/003三个support实例: 声明已正确提取且与注册表完全一致, 按引擎契约enum_join输出空、交回旧通道, 而旧通道无三态判定能力——此部分超出L1规则层能力, 规则层无法将其变为support。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_device', 'pattern': '在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{4,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:运行|使用|提供|均可|实施)', 'flags': 32} — items最小长度6迫使『在平板、手持设备上使用』把尾缀『设备』吞入成员(剥离尾缀后仅5字符), 降到4使可选尾缀组正常剥离设备/终端, 成员归一入terminal值域; 04号长items形态因懒惰回溯仍匹配原值, 兼容
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[capability_device] (1失败例)
- diagnosis: 失败机理: answer侧enum_device成功提取了声明, 但成员'手持设备'/'手持终端'带设备/终端尾缀, 引擎只自动剥'版'尾, 这些尾缀形态不在enum_terminal_bases值域内, 导致answer侧kind被判为functional; 而证据侧'方式名称'字段注册表kind=terminal, kind不匹配使enum_join根本不发生, 声明退回旧通道判not_in_evidence。修复只需让带尾缀的终端形态成员归入terminal值域, 使kind一致后join即可检测出answer多出的'手持'成员与注册表{桌面}的集合冲突。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_terminal_bases', 'words': ['手持设备', '手持终端', '桌面设备', '桌面终端', '平板设备', '平板终端']} — answer侧设备枚举成员带'设备/终端'尾缀(引擎不剥此类尾缀), 不在值域导致kind=functional与证据侧terminal注册表kind不匹配, join不发生; 将尾缀形态纳入值域使分类一致, join后多出的手持成员即触发refute, 且不影响04号裸词形态
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[capability_state] (4失败例)
- diagnosis: 06号文档能力表的『运行状态』列出现『集成阶段』, 而enum_phase_bases值域与enum_phase_words词模式均只含开发/运行阶段: 证据侧注册表构建时『集成阶段』成员被丢弃(如重要信息提示/运行状态只剩{开发阶段,运行阶段}), answer侧含『集成阶段』的阶段枚举声明也无法被识别为phase形态, 导致enum_join不发生集合比对, 全部claim落入semantic_unresolved。补齐『集成阶段』后, refute类(r_state_member_drop/swap)的answer声明成员集与注册表穷举绑定即可产生集合冲突被refute。gold=support的两例按引擎契约(注册表与声明一致时enum_join输出空、交回旧通道)在L1规则层无修复手段。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段']} — 06号文档运行状态列含『集成阶段』, 不在阶段值域导致证据侧成员被丢弃、kind=phase分类失败
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_phase_words', 'pattern': '开发阶段|集成阶段|运行阶段', 'flags': 32} — answer侧阶段枚举声明识别词模式缺『集成阶段』, 补齐后含三阶段的声明可被提取并与注册表join
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[interface_flow] (5失败例)
- diagnosis: 五例均出在接口流向族。006/007的根因是answer侧ID声明主体提取带垃圾尾缀：claimed subject为『系统运行监控与日志服务接口通过接口』/『消息服务与日志服务接口通过接口』，而ID注册表主体为纯接口名——『通过接口』不在id_subject_stopwords中，主体归一失败导致id_join无法确认绑定，conservative通道回退为not_in_evidence。016/017是发送方换值refute：answer的(主体,ID)绑定与注册表完全一致，冲突值在『由X发送至Y』的发送方字段，而现有模板没有任何answer侧发送方声明提取通道，id_join只做(主体,ID)绑定比对，无法产生绑定冲突refute。026是效果性断言(加密传输/高并发)无证据，support来自旧通道identifier_exact_match的ID字面命中，L1专家无法压制旧通道的support判定。后三类超出L1规则层能力。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'id_subject_stopwords', 'words': ['通过接口']} — answer侧『X通过接口PZXQ-…』形态中『通过接口』被并入claimed subject，加停用词使主体归一为纯接口名，与ID注册表主体一致以完成绑定确认
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[trace_binding] (5失败例)
- diagnosis: 本批4个trace_binding失败的共同机理: 06号文档中任务书章节号均以行内形态出现——证据侧为能力表字段语句『X的对应的任务书功能性能：4.1.2a）』(章节号跟在冒号后), answer侧为『追溯至任务书4.1.2 c）』(章节号跟在『任务书』后)。基线模板trace_taskbook_section使用^行首锚, 在这两种形态下均无法提取任何任务书章节token, 导致trace双向join通道完全静默, 判定退化为旧通道(identifier_exact_match只证ID在场/sequence_alignment不适用)。修复只需放宽该模板的锚定条件(行首或『任务书』/冒号后)并纳入可选字母尾缀, 使a)/b)/c)级行级区分成为可能(这是C06QA-019/020跨行污染refute的判定前提)。C06QA-029(gold=not_in_evidence)的support误判来自旧通道identifier_exact_match对ID在场的过度触发, 与L1规则包无关, 规则层无法修复。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'trace_taskbook_section', 'pattern': '(?:(?<=任务书)|(?<=：)|(?<=:)|^)4(?:\\.\\d+)+\\s*[a-hA-H]?[)）]?', 'flags': 32} — 06号文档任务书章节号以『任务书4.1.2c）』(answer侧)与『…功能性能：4.1.2a）』(证据侧字段语句)行内形态出现, ^行首锚提取不到任何token; 改为行首/任务书后/冒号后三种锚定并纳入可选字母尾缀以支持行级a/b/c区分, 无字母形态与04号兼容
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

## 第2轮明细

- 失败例: 17 ({'capability_device': 3, 'capability_state': 4, 'interface_flow': 5, 'trace_binding': 5})
- 提案变更(合并后): 4, 接受: 4, 剪枝: 4, 拒绝: 0

### 教师批次[capability_device] (3失败例)
- diagnosis: 三例均为gold=support且错判来自semantic_unresolved旧通道。引擎实际视图显示answer侧枚举声明已被正确提取(成员归一为桌面/平板/手持, kind=terminal, 与上一轮接受的enum_device修复一致)。C06QA-001中证据注册表已含『应用界面集成/方式名称={桌面、平板、手持}』, 声明与注册表完全一致——按引擎输出契约, enum_join在集合一致时输出空并将claim交回旧通道, 不产生support判定, 故not_in_evidence来自旧通道无三态判定能力, 规则层无法修复。C06QA-002/003中目标主体(日志清理、数据库连接状态提示)的ID注册表条目存在但方式名称枚举注册表条目缺失(仅需求重用被注册), 然而即便补齐该注册表条目使join发生并确认一致, 输出契约仍为空而非support, 同样无法改变判定。此为L1规则层能力边界之外的失败。
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[capability_state] (4失败例)
- diagnosis: 四个失败同根：06号文档运行状态列与answer均含『集成阶段』，但它不在enum_phase_bases值域且enum_phase_words不识别，导致证据侧成员被丢弃、answer侧阶段声明提取/分类失败，join不发生。上一轮直接补词被剪枝，推断04号回退源于answer侧散文中孤立出现的『集成阶段』被误识别为阶段枚举声明；本轮改为仅在顿号列表上下文锚定识别『集成阶段』，并同步补值域与主体窗口垃圾词（『在/仅在』连接词污染主体候选）。C06QA-004/005为support标签：即使提取与join完全一致，enum_join契约只输出空、claim交回无三态判定能力的旧通道，规则层无法产出support，此两例在L1层无解；变更仅修复014/015两例refute。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段']} — 06号运行状态列与answer成员含集成阶段，不在阶段值域导致证据侧成员丢弃、answer侧kind分类失败，join不发生；04号证据无该词故值域扩展无回退风险
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_phase_words', 'pattern': '开发阶段|运行阶段|(?<=[、，,])集成阶段|集成阶段(?=[、，,])', 'flags': 32} — 补识别集成阶段但仅限顿号列表上下文（前后邻分隔符），避免04号answer散文中孤立『集成阶段』被误提取为阶段枚举声明造成回退
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_subject_garbage_infixes', 'words': ['在', '仅在']} — answer侧『X功能(仅)在开发阶段…』的主体候选窗口把连接词『在/仅在』吞入主体，与注册表主体（如重要信息提示）不一致导致join失败，加停用词使主体归一
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[interface_flow] (5失败例)
- diagnosis: 本批5例均超出L1规则层能力。C06QA-006/007(gold=support): ID注册表已正确建立(如PZXQ-NBJK-YXZCFW-XTYXJKRZFWJK→系统运行监控与日志服务接口), answer侧声明也已提取且claimed subject经包含关系与注册表主体一致, id_join按契约输出空交回旧通道; 最终not_in_evidence来自conservative_unresolved旧通道聚合, 规则层无法产出support。C06QA-016/017(gold=refute): 错判support来自identifier_exact_match旧通道; answer侧可提取的(主体,ID)绑定(人机交互接口,RJJHJK)与注册表完全一致, 冲突在于发送方字段值(用户vs界面集成框架), 而id_join只建模(主体,ID)绑定, answer侧『由X发送至Y』形态无任何id_*/enum_*模板可提取为可join的声明, 无法构造绑定冲突。C06QA-026(gold=not_in_evidence): answer为效果性断言(加密传输/高并发), claimed subject=None, id_join无绑定可检, support同样来自identifier_exact_match旧通道。三类的判定来源与所需判定语义均在L1契约之外。
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[trace_binding] (5失败例)
- diagnosis: 本批trace_binding失败的核心是追溯join从未发生：证据侧章节信息以能力表字段语句『<主体>的对应的任务书功能性能：4.1.2a）』形态存在，answer侧以『…追溯至任务书4.1.2 c）』形态存在，基线trace_taskbook_section的^行首锚两者都匹配不到。上一轮仅放宽锚定提取裸章节token被剪枝（零修复），重新诊断发现真正缺口是token缺少主体绑定——裸token无法与ID注册表的(主体,ID)绑定关联，join无从发生；因此本轮在模板中增加subj命名组，使证据侧提取(主体,章节)对、answer侧经『任务书』锚提取章节并与同句ID配对，再经ID注册表完成三方绑定，refute类(019/020)的跨行章节冲突即可被检出。gold=support的009/010按引擎契约trace专家一致时输出空、交回旧通道，规则层无能为力；029的support误判来自identifier_exact_match旧通道对效果性断言的过触发，不在L1旋钮范围内。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'trace_taskbook_section', 'pattern': '(?:(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,24})的对应的任务书功能性能[：:])|(?:^|任务书)(?P<sec>4(?:\\.\\d+)+[a-hA-H]?[)）]?)', 'flags': 0} — 证据侧字段语句需带主体绑定提取(主体,章节)对以关联ID注册表，answer侧经『任务书』锚提取章节，保留^行首分支兼容04号裸章节号形态
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

## 教师最终pack变更(原文摘录)

- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_device', 'pattern': '在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{4,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:运行|使用|提供|均可|实施)', 'flags': 32}
  - reason: items最小长度6迫使『在平板、手持设备上使用』把尾缀『设备』吞入成员(剥离尾缀后仅5字符), 降到4使可选尾缀组正常剥离设备/终端, 成员归一入terminal值域; 04号长items形态因懒惰回溯仍匹配原值, 兼容
  - source_failures: ['C06QA-001', 'C06QA-002', 'C06QA-003', 'C06QA-011', 'C06QA-012']
