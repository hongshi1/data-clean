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
| teacher doc06_eiter_v1 | 0.2619 | 0.3333 | 20 | 0.7212 | 0.9121 | 20 |

## 规则条目质量

- 教师pack变更数: 2
- 人工pack相对generic的diff落点数: 5
- 落点重叠: []
- 教师落点: ['extraction_templates.enum_field_value', 'extraction_templates.id_pattern']
- 人工落点: ['$.join_params.id_join.id_family_prefixes+', '$.table_schemas.trace_table.canon_map.任务书名称/标识+', '$.table_schemas.trace_table.canon_map.任务书章节号+', '$.table_schemas.trace_table.canon_map.本文档名称/标识+', '$.table_schemas.trace_table.canon_map.本文档章节号+']

## 回路成本

- 教师调用: 13次 (缓存命中 1, 真实API 12)
- 评测子进程: 70次
- 墙钟: 834.9s

## 方法学负面发现

- 每个pack评测都在全新子进程中执行: numeric_z3_expert._unit_table是@lru_cache(maxsize=1)无pack身份键, gjb_presence_expert的词表正则缓存同样身份盲——进程内切换pack会继承首个pack的派生配置(历史eval_crossdoc5_onboard的in-process切换受此污染), 子进程隔离是唯一可靠口径
- 人工doc06_v1是M33时代的fork, 缺srs_gjb_v1后续新增的numeric_z3/coverage/gjb段——standalone子进程口径下crossdoc06回退(macro_f1低于generic), 历史'无差异'结论部分是缓存污染假象
- deterministic配置(QAConsistencyModule(use_experts=True))是L1规则包效应的隔离口径; 91QA主评测当前数字0.7212/0.9121

## 第1轮明细

- 失败例: 20 ({'capability_device': 6, 'capability_state': 4, 'interface_flow': 5, 'trace_binding': 5})
- 提案变更(合并后): 8, 接受: 8, 剪枝: 7, 拒绝: 0

### 教师批次[capability_device] (5失败例)
- diagnosis: 本批失败根因有二：其一，06号文档能力标识表的枚举列表头被拆成多个<p>段(『方式』+『名称』、『运行』+『状态』、『需求』+『重用』)，线性化后表头与字段标签不再是连续的『方式名称/运行状态』，导致enum_join证据侧行枚举注册表(依赖enum_field_value的连续字段名和field_kinds键)构建失败，所有claim落入semantic_unresolved；其二，answer侧第二句『在…终端上均可以使用』中『上均可以』不匹配enum_device的动词集(仅有『均可』)，第二句声明无法提取。修复以增量方式兼容04号形态。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求\\s*重用|方式\\s*名称|运行\\s*状态|对应的\\s*任务书\\s*功能\\s*性能)[：:](?P<value>.+)', 'flags': 32} — 06号表头『方式/名称』等被拆分为多段，字段名线性化后含空白，允许字段名内空白以匹配行枚举，04号连续形态仍兼容
- `add_canon_map` {'op': 'add_canon_map', 'kind': 'capability_table', 'entries': {'方式 名称': '方式名称', '运行 状态': '运行状态', '需求 重用': '需求重用', 'Use case 名称': 'Use case名称', '对应的 任务书 功能/性能': '对应任务书'}} — 归一06号多段表头到规范列名，使field_kinds/列profile路由生效
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_device', 'pattern': '在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{6,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:均\\s*可\\s*以|均\\s*可|均\\s*可以|均|运行|使用|提供|实施)', 'flags': 32} — answer句式『在…终端上均可以使用』中『上均可以』不在原动词集，扩展动词交替并保留items命名组，04号原形态仍匹配
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段']} — 06号能力表运行状态列含『集成阶段』，补齐阶段值域以便后续phase类join
- llm: {'invocations': 1, 'cache_hits': 1, 'api_calls': 0}

### 教师批次[capability_device] (1失败例)
- diagnosis: 失败根因在证据侧而非answer侧：06号文档能力表的『方式名称』『运行状态』表头在原文中被拆分为多个<p>段(方式/名称、运行/状态)，线性化后表头与join_params.enum_join.field_kinds及enum_field_value模板所依赖的规范列名『方式名称』『运行状态』不匹配，导致terminal枚举注册表未构建，enum_join无法给出三态判定，落入semantic_unresolved的not_in_evidence。answer侧enum_device模板可正常匹配『在桌面、手持设备上使用』，无需改动。最小修复是在capability_table的canon_map中补充拆分表头到规范列名的映射。
- `add_canon_map` {'op': 'add_canon_map', 'kind': 'capability_table', 'entries': {'方式 名称': '方式名称', '运行 状态': '运行状态', '方式\n名称': '方式名称', '运行\n状态': '运行状态'}} — 06号文档能力表表头『方式名称』『运行状态』被拆分为多个p段，线性化后带空格/换格形式无法命中field_kinds的规范列名，补canon映射使terminal/phase枚举注册表能构建
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_state] (4失败例)
- diagnosis: 失败集中于capability_table『运行状态』列的phase枚举join: 06号文档出现『集成阶段』, 而基线词表enum_phase_bases与模板enum_phase_words仅覆盖04号形态的『开发阶段/运行阶段』, 导致证据侧行枚举成员校验失败、answer侧阶段声明也无法提取, 全部落入semantic_unresolved。表格分类与列映射本身正常(表头含项目唯一标识符/需求描述, 签名命中)。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段']} — 06号文档运行状态列出现『集成阶段』, 证据侧行枚举成员因不在封闭值域而被丢弃, 导致not_in_evidence
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_phase_words', 'pattern': '开发阶段|集成阶段|运行阶段', 'flags': 32} — answer侧阶段词提取需同样覆盖『集成阶段』, 纯增分支保持04号形态兼容
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[interface_flow] (5失败例)
- diagnosis: 06号文档接口表中接口标识被拆分为两个<p>元素(如『PZXQ-NBJK-YXZCFW-』+『XTYXJKRZFWJK』), 线性化后标识内部含空白, 导致id_pattern/id_binding只能截取到前半段, ID注册表无法建立完整(主体,ID,发送方)绑定: support用例因标识未命中而conservative_unresolved, refute用例因无绑定而无法检测跨行发送方冲突, 效果性断言用例因仅剩identifier_exact_match通道而误判support。修复为在ID正则中允许连字符后可选空白(04号连续形态完全兼容), 使注册表能重建完整绑定。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_pattern', 'pattern': 'PZXQ-[A-Z0-9]+(?:\\s*-\\s*[A-Z0-9]+)*-?', 'flags': 0} — 06号表格中ID跨<p>拆分, 连字符后出现空白, 需容许段间空白以捕获完整标识; 04号连续形态不受影响
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_binding', 'pattern': '(?P<name>[A-Za-z0-9\\u4e00-\\u9fff][A-Za-z0-9\\u4e00-\\u9fff-]{0,40}?)的(?:项目唯一标识符|唯一标识符|接口需求标识|接口标识|功能标识|标识符|标识|编号|代号)(?:(?:分别|均|都|也|是|为)[：:]?)*[：:]?(?P<id>PZXQ-[A-Z0-9]+(?:\\s*-\\s*[A-Z0-9]+)*-?)', 'flags': 0} — 表格行线性化为『X的接口需求标识：PZXQ-...-\n后半段』, 绑定提取需容许ID内部空白以建立完整(主体,ID)注册表, 进而支撑发送方绑定冲突检测
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_section_title', 'pattern': '(?P<sec>\\d+(?:\\.\\d+)+)(?P<name>[\\u4e00-\\u9fffA-Za-z][\\u4e00-\\u9fffA-Za-z0-9-]{0,40}?)[（(]\\s*(?P<id>PZXQ-[A-Z0-9]+(?:\\s*-\\s*[A-Z0-9]+)*-?)\\s*[）)]', 'flags': 0} — 06号章节标题中ID形如『PZXQ-NBJK-YXZCFW- JCXXFWRZFWJK』含内部空格, 需容许空白以从标题侧补充ID注册表
- llm: {'invocations': 2, 'cache_hits': 0, 'api_calls': 2}

### 教师批次[trace_binding] (5失败例)
- diagnosis: 前四个实例的追溯绑定证据位于能力标识表的『对应的任务书功能/性能』列(线性化为『X的对应的任务书功能性能：4.1.2 c）』形态)，而基线enum_field_value的字段白名单只含无斜杠的『对应的任务书功能性能』且不含canon化后的『对应任务书』，导致trace注册表未构建出(主体,任务书章节)绑定，support/refute均判为not_in_evidence。C06QA-029的误判来自L0 identifier_exact_match通道仅凭标识符在场即判support，压制了正确的not_in_evidence，属L1规则层之外，无法通过规则包修复。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求重用|方式名称|运行状态|对应的任务书功能/性能|对应的任务书功能性能|对应任务书|任务书功能/性能)[：:](?P<value>.+)', 'flags': 32} — 06号文档能力表追溯列原文含斜杠形态『对应的任务书功能/性能』及canon化列名『对应任务书』，原白名单均未覆盖，导致trace绑定注册表构建失败；新增字段变体并保留原命名组，04号无斜杠形态仍兼容
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

## 第2轮明细

- 失败例: 20 ({'capability_device': 6, 'capability_state': 4, 'interface_flow': 5, 'trace_binding': 5})
- 提案变更(合并后): 9, 接受: 9, 剪枝: 8, 拒绝: 0

### 教师批次[capability_device] (5失败例)
- diagnosis: 本批失败均为capability_device族：证据侧能力表行枚举(『应用界面集成的方式名称：桌面、平板、手持』)可正常构建，但answer侧enum_device提取的设备项虽可匹配，主体窗口截取得到『应用界面集成功能支持』『计算机内存状态详细信息功能仅在』『软件状态监控功能支持』等带『功能/支持/仅在』尾巴的主体，与证据主体(Use case名)不一致导致join失败；此外第二句『终端上均可以使用』的动词形态不在enum_device动词白名单内。修复为：向enum_dev_tail_strip追加主体尾缀词，并增量扩展enum_device动词alternation(保留命名组，04号形态为超集兼容)。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_dev_tail_strip', 'words': ['功能', '仅', '仅在', '可以']} — answer侧设备枚举主体窗口含『功能支持/功能仅在』等尾缀，证据主体为纯Use case名，追加尾缀剥离词使两侧主体归一(剥离双侧对称应用，04号主体含功能时两侧同剥仍匹配)
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_device', 'pattern': '在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{6,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:运行|使用|提供|均可|均可以|可以|实施)', 'flags': 32} — 06号answer第二句形态『在…终端上均可以使用该功能』的『均可以使用』未被原动词alternation覆盖，新增该形态并保留items命名组，04号原有形态仍匹配
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_device] (1失败例)
- diagnosis: 失败根因在answer侧设备枚举提取: enum_device的items下限为6字符, 而『桌面、手持』仅5字符导致第一句不触发; 第二句『在桌面、手持终端上均可以使用』中『上』后接『均可以使用』, 原模板只允许运行|使用|提供|均可|实施紧跟『上』, 也不匹配。两处均未提取出设备成员集合, enum_join无从与证据行『方式名称：桌面』比对, 落入semantic_unresolved的not_in_evidence。证据侧行绑定(方式名称)上一轮已修复可用。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_device', 'pattern': '在(?P<items>[\\u4e00-\\u9fffA-Za-z0-9、和]{2,60}?)(?:等)?(?:种版本|版本|设备|终端|平台)?上(?:均)?(?:可以|可)?(?:运行|使用|提供|实施|均可)', 'flags': 32} — items下限由6降至2以覆盖『桌面、手持』等短枚举, 并允许『上(均)(可)以…』形态; 均为原匹配的超集, 04号长形态仍兼容, 使answer侧设备成员可提取并与证据行方式名称封闭集合比对出手持为多余成员
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[capability_state] (4失败例)
- diagnosis: 本批4例均为capability_state族：证据侧能力表『运行状态』列的单元格值被拆分为多个<p>段(如『运行』『阶段』)，线性化后成员含内部空白，且值域出现基线词表未收录的『集成阶段』(enum_phase_bases仅开发/运行阶段，enum_phase_words模板同样缺失)，导致运行状态穷举绑定注册表构建失败，answer侧声明无法join，全部落入semantic_unresolved。修复为增量扩充阶段值域并容忍成员内空白，04号原有连续形态不受影响。
- `add_vocabulary_words` {'op': 'add_vocabulary_words', 'vocab': 'enum_phase_bases', 'words': ['集成阶段', '开发 阶段', '集成 阶段', '运行 阶段']} — 06号能力表运行状态列出现『集成阶段』且单元格拆分线性化后成员含内部空白(『运行 阶段』)，基线值域仅开发/运行阶段且无空白形态，穷举绑定注册表构建失败
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_phase_words', 'pattern': '开发\\s*阶段|集成\\s*阶段|运行\\s*阶段', 'flags': 32} — answer侧阶段声明含『集成阶段』且证据侧成员可能含内部空白，原模板仅匹配开发/运行阶段，无法提取阶段成员参与join；无命名组，04号连续形态仍匹配
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

### 教师批次[interface_flow] (5失败例)
- diagnosis: 006/007失败机理：06号接口需求表中接口标识被拆分为两个<p>段（如『PZXQ-NBJK-YXZCFW-』+『XTYXJKRZFWJK』），线性化后标识符内部含空白，id_pattern/id_binding等模板的PZXQ-[A-Z0-9-]+无法命中完整ID，导致ID注册表缺失、conservative_unresolved误判not_in_evidence；放宽ID模式容忍段间空白即可修复（假定引擎比较前对ID做空白归一化）。016/017（发送方跨行污染需subject-发送方值级绑定冲突检测）与026（效果性断言加密传输/高并发无证据词）需要answer侧发送方/效果断言提取模板与值冲突通道，现有可替换模板均无对应命名组，超出L1纯符号规则能力，本轮不处理。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_pattern', 'pattern': 'PZXQ-[A-Z0-9-]+(?:\\s+[A-Z0-9-]+)*', 'flags': 32} — 06号接口表ID跨<p>段拆分，线性化后标识符内部含空白，原模式无法命中完整ID导致注册表缺失与not_in_evidence误判；允许段间空白后04号无空白形态仍兼容
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_binding', 'pattern': '(?P<name>[A-Za-z0-9\\u4e00-\\u9fff][A-Za-z0-9\\u4e00-\\u9fff-]{0,40}?)的(?:项目唯一标识符|唯一标识符|接口需求标识|接口标识|功能标识|标识符|标识|编号|代号)(?:(?:分别|均|都|也|是|为)[：:]?)*[：:]?(?P<id>PZXQ-[A-Z0-9-]+(?:\\s+[A-Z0-9-]+)*)', 'flags': 32} — 同上，ID绑定注册表构建需容忍拆分段间的空白，保留原name/id命名组，04号连续形态兼容
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_id_binding', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20}?)的(?:项目唯一标识符|唯一标识符|接口需求标识|接口标识|功能标识)[：:](?P<id>PZXQ-[A-Z0-9-]+(?:\\s+[A-Z0-9-]+)*)', 'flags': 32} — 同上，枚举侧ID绑定提取需容忍拆分段空白，保留原subj/id命名组
- llm: {'invocations': 3, 'cache_hits': 0, 'api_calls': 3}

### 教师批次[trace_binding] (5失败例)
- diagnosis: 本批5例均属trace绑定注册表构建链路断裂：能力表『对应的任务书功能/性能』列在06号线性化后存在两种形态——保留斜杠的『对应的任务书功能/性能』与去斜杠/规范化的『对应任务书』，当前enum_field_value字段白名单仅覆盖无斜杠连续形态，导致(主体,任务书章节)证据对无法注册(009/019/020)；此外06号表格单元格内标识符被拆分为多个<p>段(如PZXQ-YXZCFW-GN-与YWGL分两段)，id_pattern不允许ID内部空白，ID注册表与identifier通道均无法命中(010)，且029中拆分ID依赖标题处未拆分形态被identifier通道误判support而绕过状态值域校验。修复为增量扩展字段变体与ID模式空白容忍，04号连续无斜杠形态仍原样匹配。
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求\\s*重用|方式\\s*名称|运行\\s*状态|对应\\s*的?\\s*任务书\\s*功能\\s*/?\\s*性能|对应任务书)[：:](?P<value>.+)', 'flags': 32} — 06号能力表追溯列线性化后同时存在含斜杠形态『对应的任务书功能/性能』与canon化列名『对应任务书』，原白名单仅匹配无斜杠连续形态，trace绑定注册表构建失败；新增两变体并保留原命名组，04号连续形态仍兼容
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_pattern', 'pattern': 'PZXQ-[A-Z0-9-]+(?:\\s+[A-Z0-9-]+)*', 'flags': 0} — 06号表格单元格内标识符被拆分为多个<p>段(如PZXQ-YXZCFW-GN-与YWGL)，线性化后ID内部含空白导致id_pattern无法命中、ID注册表与identifier通道失效；允许段间空白，04号连续ID匹配结果不变
- `add_canon_map` {'op': 'add_canon_map', 'kind': 'capability_table', 'entries': {'对应的任务书功能性能': '对应任务书', '对应任务书': '对应任务书'}} — 补充去斜杠及规范形态表头到『对应任务书』规范列名的映射，确保该列在能力表线性化与列路由中被识别为追溯列
- llm: {'invocations': 1, 'cache_hits': 0, 'api_calls': 1}

## 教师最终pack变更(原文摘录)

- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求\\s*重用|方式\\s*名称|运行\\s*状态|对应的\\s*任务书\\s*功能\\s*性能)[：:](?P<value>.+)', 'flags': 32}
  - reason: 06号表头『方式/名称』等被拆分为多段，字段名线性化后含空白，允许字段名内空白以匹配行枚举，04号连续形态仍兼容 | 同落点冲突弃用: {'op': 'replace_extraction_template', 'name': 'enum_field_value', 'pattern': '(?P<subj>[\\u4e00-\\u9fffA-Za-z0-9]{2,20})的(?P<field>需求重用|方式名称|运行状态|对应的任务书功能/性能|对应的任务书功能性能|对应任务书|任务书功能/性能)[：:](?P<value>.+)', 'flags': 32, 'reason': '06号文档能力表追溯列原文含斜杠形态『对应的任务书功能/性能』及canon化列名『对应任务书』，原白名单均未覆盖，导致trace绑定注册表构建失败；新增字段变体并保留原命名组，04号无斜杠形态仍兼容', 'source_failures': ['C06QA-009', 'C06QA-010', 'C06QA-019', 'C06QA-020', 'C06QA-029']}
  - source_failures: ['C06QA-001', 'C06QA-002', 'C06QA-003', 'C06QA-011', 'C06QA-012', 'C06QA-009', 'C06QA-010', 'C06QA-019', 'C06QA-020', 'C06QA-029']
- `replace_extraction_template` {'op': 'replace_extraction_template', 'name': 'id_pattern', 'pattern': 'PZXQ-[A-Z0-9-]+(?:\\s+[A-Z0-9-]+)*', 'flags': 32}
  - reason: 06号接口表ID跨<p>段拆分，线性化后标识符内部含空白，原模式无法命中完整ID导致注册表缺失与not_in_evidence误判；允许段间空白后04号无空白形态仍兼容 | 同落点冲突弃用: {'op': 'replace_extraction_template', 'name': 'id_pattern', 'pattern': 'PZXQ-[A-Z0-9-]+(?:\\s+[A-Z0-9-]+)*', 'flags': 0, 'reason': '06号表格单元格内标识符被拆分为多个<p>段(如PZXQ-YXZCFW-GN-与YWGL)，线性化后ID内部含空白导致id_pattern无法命中、ID注册表与identifier通道失效；允许段间空白，04号连续ID匹配结果不变', 'source_failures': ['C06QA-009', 'C06QA-010', 'C06QA-019', 'C06QA-020', 'C06QA-029']}
  - source_failures: ['C06QA-006', 'C06QA-007', 'C06QA-016', 'C06QA-017', 'C06QA-026', 'C06QA-009', 'C06QA-010', 'C06QA-019', 'C06QA-020', 'C06QA-029']
