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

## 规则条目质量

- 教师pack变更数: 0
- 人工pack相对generic的diff落点数: 5
- 落点重叠: []
- 教师落点: []
- 人工落点: ['$.join_params.id_join.id_family_prefixes+', '$.table_schemas.trace_table.canon_map.任务书名称/标识+', '$.table_schemas.trace_table.canon_map.任务书章节号+', '$.table_schemas.trace_table.canon_map.本文档名称/标识+', '$.table_schemas.trace_table.canon_map.本文档章节号+']

## 回路成本

- 教师调用: 10次 (缓存命中 0, 真实API 10)
- 评测子进程: 64次
- 墙钟: 585.3s

## 方法学负面发现

- 每个pack评测都在全新子进程中执行: numeric_z3_expert._unit_table是@lru_cache(maxsize=1)无pack身份键, gjb_presence_expert的词表正则缓存同样身份盲——进程内切换pack会继承首个pack的派生配置(历史eval_crossdoc5_onboard的in-process切换受此污染), 子进程隔离是唯一可靠口径
- 人工doc06_v1是M33时代的fork, 缺srs_gjb_v1后续新增的numeric_z3/coverage/gjb段——standalone子进程口径下crossdoc06回退(macro_f1低于generic), 历史'无差异'结论部分是缓存污染假象
- deterministic配置(QAConsistencyModule(use_experts=True))是L1规则包效应的隔离口径; 91QA主评测当前数字0.7212/0.9121

## 第1轮明细

- 失败例: 20 ({'capability_device': 6, 'capability_state': 4, 'interface_flow': 5, 'trace_binding': 5})
- 提案变更(合并后): 6, 接受: 6, 剪枝: 6, 拒绝: 0

### 教师批次[capability_device] (5失败例)
- diagnosis: 五例中三例gold=support：enum_join契约只对冲突输出refute，一致时返回空并交回无三态能力的旧通道，规则层无法将其判为support。两例gold=refute(C06QA-011/012)失败机理可修：answer侧声明主体带尾缀垃圾(『…功能支持在』『…功能仅』)无法与注册表主体(『计算机内存状态详细信息』『软件状态监控』)对齐；成员带后缀『设备/终端』(平板设备/平板终端)未归一为终端基值，导致kind判为functional而非terminal，与注册表方式名称(terminal)的join不触发，成员增删冲突漏检。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_subject_role_suffix', 'pattern': '(?:的支持方式|的方式名称|的运行状态|的功能标识表|的具体操作|的主要功能|的核心操作|的子功能|功能支持在|功能仅在|功能支持|功能仅|功能)$', 'flags': 32} — answer侧主体被enum_device截入『功能支持在/功能仅』尾缀，需在主体角色后缀裁剪中剥离以对齐注册表主体
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_dev_tail_strip', 'words': ['设备', '终端']} — answer成员『平板设备/平板终端/手持设备』需剥离设备/终端尾缀归一为enum_terminal_bases基值，使kind归为terminal并与方式名称注册表join
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_device] (1失败例)
- diagnosis: 证据侧注册表已含消息提示与管理/方式名称={桌面}(terminal类)，冲突本应可判；失效点在answer侧成员归一化：enum_device从『在桌面、手持设备上使用』提取出成员'手持设备'/'手持终端'，而enum_dev_tail_strip词表不含'设备'/'终端'后缀，导致成员无法归一为注册表封闭值'手持'，枚举join无法命中，claim落入semantic_unresolved判为not_in_evidence。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_dev_tail_strip', 'words': ['设备', '终端']} — answer侧设备枚举成员带'设备/终端'后缀(手持设备/手持终端)，需剥离后缀归一为注册表封闭值'手持'以触发terminal类成员集合冲突
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_state] (4失败例)
- diagnosis: 四例均卡在运行状态枚举join: 06号文档证据行含『集成阶段』, 但enum_phase_bases/enum_phase_words只收录开发阶段/运行阶段, 导致证据注册表把集成阶段丢弃(如C06QA-014注册表{开发,运行}而原文为{开发,集成,运行}), answer侧成员也无法通过phase值域校验, 集合冲突无法成立, 全部落入semantic_unresolved。两例gold=support(C06QA-004/005)按引擎契约即使注册表修齐也只会输出空交回旧通道, 规则层无能为力; 两例gold=refute(C06QA-014/015)在补齐集成阶段值域后, answer集合与注册表集合的成员冲突即可被enum_join检出。answer侧『运行状态绑定为X』形态与enum_field_value的冒号形态不符, 需增量兼容。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段']} — 06号文档能力表运行状态列含集成阶段, 基线值域缺失导致证据注册表丢弃该成员, 集合冲突无法成立
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_phase_words', 'pattern': '开发阶段|集成阶段|运行阶段', 'flags': 32} — answer侧阶段词提取需覆盖集成阶段, 与enum_phase_bases保持一致(04号形态为超集兼容)
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求重用|方式名称|运行状态|对应的任务书功能性能)(?:[：:]|绑定为|为)(?P<value>.+)', 'flags': 32} — 06号answer用『运行状态绑定为X』而非冒号形态声明绑定, 增量扩展分隔形态且保留全部命名组, 冒号形态仍匹配(04兼容)
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[interface_flow] (5失败例)
- diagnosis: 本批5例均超出L1规则层能力。C06QA-006/007(gold=support): ID在证据注册表中且(主体,ID)绑定一致(注册表主体'系统运行监控与日志服务接口'被answer侧声明包含)，id_join按契约输出空交回旧通道；旧通道conservative_unresolved因原始表格中ID被<p>标签拆分('PZXQ-NBJK-YXZCFW-'+'JCXXFWRZFWJK')在raw context未命中而判not_in_evidence——L1无法输出support。C06QA-016/017(gold=refute): 冲突在'发送方'字段(注册表仅建模(接口名,ID)主体绑定，answer侧'由界面集成框架发送'位于ID之后，id_window前向窗口无法捕获，且field_kinds不支持发送方字段)，id_join无绑定冲突可检。C06QA-026(gold=not_in_evidence): support来自旧通道identifier_exact_match(ID确实在证据中精确出现)，L1无权覆盖旧通道的support判定。
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[trace_binding] (5失败例)
- diagnosis: 本批trace_binding失败的核心机理是trace专家两侧映射提取断裂：证据侧的任务书章节位于capability表线性化语句中段(『X的对应的任务书功能性能：4.1.2a）』)，answer侧章节位于『追溯至任务书4.1.1c）』句中，而基线模板trace_taskbook_section带行首锚^，两侧章节token均不在行首故均未提取，导致映射比对从未发生，claim落回旧通道被判not_in_evidence。去掉行首锚后，refute类实例(019/020)的answer声明(ID→污染章节)可与证据绑定(ID→真实章节)形成冲突，由trace专家输出refute。support类实例(009/010)即使提取一致，按引擎契约trace专家输出空交回旧通道，规则层无法产生support；C06QA-029为效果性断言误判support，无集合/绑定冲突可检，均超出L1规则层能力。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'trace_taskbook_section', 'pattern': '4(?:\\.\\d+)+\\s*[a-hA-H]?[)）]?', 'flags': 32} — 去除行首锚^，使capability表行内『对应的任务书功能性能：4.1.2a）』与answer句『追溯至任务书4.1.1c）』中段的任务书章节token均可被提取，从而建立证据/answer两侧的追溯映射比对(行首形态仍为子串匹配，04号兼容)
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

## 第2轮明细

- 失败例: 20 ({'capability_device': 6, 'capability_state': 4, 'interface_flow': 5, 'trace_binding': 5})
- 提案变更(合并后): 8, 接受: 8, 剪枝: 8, 拒绝: 0

### 教师批次[capability_device] (5失败例)
- diagnosis: 本批5例中3例(support)的answer枚举声明与证据注册表已完全一致(如C06QA-001 subject'应用界面集成'/members{桌面,平板,手持}/terminal vs 注册表同集合)，按引擎输出契约enum_join输出空交回旧通道，而旧通道无三态判定器，规则层无法产出support，只能放弃。2例(refute C06QA-011/012)失败机理是answer侧设备成员带'设备/终端'后缀('平板设备','手持设备')未被剥离归一化，导致kind降为functional且成员形态与注册表terminal值域(桌面/平板/手持)不一致，集合比对无法触发；将'设备/终端'加入enum_dev_tail_strip尾部剥离词表即可把成员归一化到terminal_bases，使缺桌面(C06QA-011)与多平板(C06QA-012)的集合冲突被enum_join正确refute。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_dev_tail_strip', 'words': ['设备', '终端']} — answer侧设备枚举成员'平板设备/手持设备/平板终端'尾部后缀未剥离，归一化到terminal_bases后refute案例的成员集合冲突(缺桌面/多平板)才能被enum_join检出
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_device] (1失败例)
- diagnosis: 失败根因是answer侧设备枚举成员形态未归一化：'手持设备'/'手持终端'未被剥离尾部名词，导致既不匹配注册表成员'手持'，也无法判定为terminal值域(kind退化为functional)，enum_join无法形成'多出手持'的跨行绑定冲突，claim落入语义通道输出not_in_evidence。注册表侧(消息提示与管理/方式名称={桌面})与ID绑定均正常提取，只需在设备成员尾部剥离词表中补充'设备/终端'即可让成员归一为'手持'并触发封闭集合冲突refute。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_dev_tail_strip', 'words': ['设备', '终端']} — answer侧'手持设备/手持终端'需剥离尾部名词归一为注册表成员'手持'，方能形成封闭枚举集合冲突
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_state] (4失败例)
- diagnosis: 三类问题叠加：(1) enum_phase_bases值域缺少『集成阶段』，导致证据侧运行状态注册表把成员『集成阶段』整体丢弃(如重要信息提示/运行状态被截为{开发阶段、运行阶段})，answer含集成阶段的声明无法与注册表对齐，refute/support均失效；(2) answer侧声明句式为『该功能的运行状态绑定为X』(无冒号)，enum_field_value的[：:]分隔符匹配不上；(3) answer首句『X功能在开发阶段、集成阶段、运行阶段提供』不含『上』字，enum_device的『上(运行|提供)』锚点匹配不上，answer侧阶段集合提取为空。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段']} — 06号文档运行状态列含『集成阶段』，基线值域缺失导致注册表成员被丢弃，集合比对失效
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求重用|方式名称|运行状态|对应的任务书功能性能)(?:[：:]|绑定为|是为|为|是)(?P<value>[^，,。；;\\n]+)', 'flags': 32} — answer侧声明句式为『该功能的运行状态绑定为X』而非冒号分隔，扩展分隔符并截断到句读符，保留原命名组且冒号形态向后兼容
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_device', 'pattern': '在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{6,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?(?:上(?:运行|使用|提供|均可|实施)|阶段(?:之)?(?:提供|运行|使用|实施))', 'flags': 32} — answer句式『在开发阶段、集成阶段、运行阶段提供』无『上』字锚点，新增『阶段+提供』分支；原『上+动词』04号形态完整保留，items命名组不变
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_phase_words', 'pattern': '开发阶段|集成阶段|运行阶段', 'flags': 32} — 阶段词识别模式同步补入『集成阶段』，保证answer侧阶段成员切分与注册表值域一致
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[interface_flow] (5失败例)
- diagnosis: C06QA-006/007: answer侧ID声明提取成功但主体窗口把叙述连接词『通过接口』一并捕获(主体=『系统运行监控与日志服务接口通过接口』), 与注册表主体『系统运行监控与日志服务接口』形态不一致, 绑定无法消解, id_join落入conservative_unresolved输出NIE并压过l0的support——属主体归一化/停用词问题, 增补id_subject_stopwords即可。C06QA-016/017: gold refute依赖『发送方』字段与answer叙述(由X发送至Y)的语义比对, 而id_join只比对(主体,ID)绑定且主体 containment 已一致, 规则层无法表达发送方冲突。C06QA-026: gold NIE但ID在证据中精确在场, identifier_exact_match通道必然support, 效果性断言(加密传输/高并发)的缺席判定超出L1能力。后三类无法用7种op修复, 仅对前两类做词表增量。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'id_subject_stopwords', 'words': ['通过', '通过接口']} — answer侧叙述句『X接口通过接口<ID>实现』的ID前窗口把连接词『通过接口』并入主体, 增补停用词使主体归一化后与注册表接口名一致, 消解绑定
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[trace_binding] (5失败例)
- diagnosis: 本批核心机理: trace_binding类claim的answer侧形如『需求PZXQ-…追溯至任务书4.1.x』, 但当前trace专家没有任何带命名组的answer侧(ID,章节)提取模板——trace_trace_relation_words仅是无捕获的词表正则, 故answer的追溯映射声明从未进入trace比对, 5例中4例(009/010/019/020)trace通道静默失效, 判定退回旧通道(identifier_exact_match只看ID在场, sequence_alignment不适用)。证据侧注册表实际已完备: id_binding提取了(主体→ID), enum_field_value提取了(主体→对应的任务书功能性能:4.1.x), 链式join即可得到(ID→章节)注册表, 无需证据侧改动; 仅需让answer侧(id,sec)对被提取出来, 019/020的跨行污染值(4.1.1c/4.1.3a vs 注册表4.1.1a/4.1.3b)即可触发绑定冲突refute, 009/010一致时交回匹配通道。另注意线性化把表头『对应的任务书功能/性能』折叠为『对应的任务书功能性能』, 现有canon_map键(带斜杠)匹配不上, 需补无斜杠别名。C06QA-029(gold=N, 引擎support)是L0 identifier_exact_match/l0_entity_detector仅凭ID在场判support, 效果性断言(评审/实现完整性)不在任何L1专家值域内, 规则层无法纠正, 如实说明。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'trace_trace_relation_words', 'pattern': '(?P<id>PZXQ-[A-Z0-9-]+)[^，,。；;]{0,24}?(?:追溯|追踪|映射)(?:至|到)?任务书(?P<sec>\\d+(?:\\.\\d+)+\\s*[a-hA-H]?[)）]?)', 'flags': 32} — 原模板是无命名组的词表正则, answer侧『ID追溯至任务书4.1.x』声明从未被提取为(id,sec)对; 补命名组后trace专家可与证据侧(主体→ID)+(主体→任务书章节)链式注册表比对, 修复019/020的跨行绑定冲突refute及009/010的映射核验
- `add_canon_map` {'op': 'add_canon_map', 'kind': 'capability_table', 'entries': {'对应的任务书功能性能': '对应任务书'}} — 06号文档线性化将表头『对应的任务书功能/性能』折叠为无斜杠形态, 现有canon_map键不命中, 补别名使该列归一化为规范追溯列供trace通道识别
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}
