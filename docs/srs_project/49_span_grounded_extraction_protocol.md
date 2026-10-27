# 49 Span-Grounded Extraction与span标注评估协议

日期：2026-10-22 | 状态：P0执行协议 v1（评估器已落地；viewer由并行Agent开发中）

## 1. 科研定位

当前块级规则抽取存在三个缺口：

1. **无位置锚定**：feature_matrix的槽位字符串经`find()`取出后与原文脱钩，无法回指，人工无法快速判定对错；
2. **质量只有结构性代理**：slot_fill_rate均值0.497、谓词覆盖32.12%衡量"结构有没有填"，不衡量"填得对不对"；语义正确性至今没有测量；
3. **下游误差无标签**：证据图/对齐/QualityContract消费的都是候选（候选非gold铁律），抽取错误进入下游后无法归因。

**Span-Grounded Extraction**：每个抽取结果从"槽位字符串"升级为`(值, span_type, char_start, char_end, tier)`，span必须锚定原文可回指。viewer的左右对照（左侧原文/右侧提取）把抽取结果摆回原文位置，每个高亮span的✓/✗按钮把"抽取正确性"变成单键人工二分类。

与文献的三个锚点：

| 文献线 | 与本协议的关系 |
|---|---|
| span-based IE | NER/RE的BIO标注与span枚举范式（BiLSTM-CRF，Huang et al. 2015；dynamic span-indexing，Luan et al. 2019；统一结构生成UIE，Lu et al. 2022）。claim五元组是领域schema的IE实例；本协议补的是"规则抽取→span化→人工监督→模型抽取"的升级路径 |
| grounding/attribution | rationale评估（ERASER，DeYoung et al. 2020）要求答案锚定证据片段。span grounding是抽取层的attribution：抽出的每个槽位必须可指回原文证据位置 |
| XAI faithfulness | Jacovi & Goldberg（2020）区分faithfulness与plausibility。✓/✗测的是faithfulness（抽取是否忠实于原文）而非plausibility（看起来是否合理）——"高亮位置对但类型/值错"必须标✗ |

核心主张：**可视化=评估协议**（evaluation-by-visualization）。viewer不是工程附件，而是在单标注者+16份真实SRS的规模约束下，把无gold的抽取质量变成可积累、可统计的span precision测量的唯一低成本通道。

## 2. Span评估协议

标注单元：一次✓/✗=对一个高亮span的判定。

指标定义：

```text
span_precision(type) = n(verdict=correct) / n(verdict∈{correct, incorrect})   按span_type分层
总体                 = 六类pooled（未知span_type不计入）
置信区间             = Wilson score 95%（自实现，z=1.959963984540054，无scipy）
```

三条边界声明（评估器写入每份报告的notes）：

1. **precision-only**：只测"已高亮span的正确率"；未高亮文本不在分母，recall需对未抽取文本独立抽样（后续单独协议，不在本版）；
2. **分层报告**：六类不合并下结论（identifier易✓、predicate难，合并会掩盖差异）；
3. **不裁决关系层**：对齐/共指质量由48号gold-proxy与A-E矩阵独立裁决（§6）。

span_type六类与现有槽位/特征的映射：

| span_type | 对应抽取产物 | 当前来源 |
|---|---|---|
| identifier | 显式编号/型号/需求ID/章节号 | features.identifiers（ID正则） |
| quantity_unit | object_value+operator+unit_raw | features.quantities |
| predicate | predicate_candidate | 参数词典23词+功能谓词挖掘（4020条） |
| modal | 情态词（应/宜/可/必须…） | features.modal_words |
| negative | 否定词/否定短语 | **协议新增**：当前规则未系统覆盖，从零标注 |
| reference | 章节/图/表引用 | features.references |

negative是七类特征中没有的类别——它是"规则难覆盖→模型补位"的首个试点类型（§3）。

目标与达标口径：

- 目标：每类型 precision ≥ 0.90。锚定依据：L2锚点校准precision 0.9505的经验值，抽取层门槛略放宽；
- **弱达标** = 点估计≥0.90；**强达标** = Wilson 95% CI下界≥0.90。报告必须同时给出两者；
- 量级直觉：全对样本50/50下界0.9287（"全对"时n=50即强达标）；p̂=0.98在n=50仅弱达标（下界0.8950），n=53即强达标（52/53→下界0.9006）；详见附录B。

样本量：每类型≥50条标注起步（过程监控门槛，不足标"insufficient"）；结论级比较需≥200（p̂=0.9时CI下界才≥0.85，附录B）。

数据卫生（`tools/eval_span_grounding.py`强制执行）：

- 未知verdict/未知span_type/缺失字段逐项计数报告，**不静默丢弃**；
- 多文件合并；同`(span_text, span_type, block_index)`以ts最新为准；精确重复事件与verdict冲突键分别计数；
- 导出即入库：每次评估按runs协议落盘result.json（标注快照血缘，防localStorage单点丢失）。

## 3. 弱监督→监督升级路径（核心科研叙事）

| 阶段 | 监督源 | 抽取器 | 状态 |
|---|---|---|---|
| S0 弱监督 | 白名单正则+词典（参数23词+功能谓词45动词） | 规则 | 已落地：谓词覆盖32.12%（4020/12517并集） |
| S1 人工在环 | viewer✓/✗ span标注 | 规则（被测对象） | viewer并行开发；评估器已落地（本文档） |
| S2 监督学习 | S1积累的span级BIO标注 | 冻结编码器+线性CRF头 | 设计冻结；触发条件=每类型≥300标注 |

标注量测算（16份SRS）：

- **训练量**：中文序列标注文献经验为每类约500-1000 span；六类合计3000-6000 span；
- **供给量**：12517条claim的槽位候选+2552句的句子级span，量级>10^4，供给充足；
- **速率**：viewer单键判定按10-20 span/分钟计，3000-6000 span约3-8小时（单标注者1-2个工作日内可完成S1）；
- **验证**：用学习曲线（25/50/75/100%标注量）检验500-1000经验值在本领域的适配性，不直接假设成立。

模型候选（冻结骨干原则，与48号A4-gate"冻结骨干+轻头"同哲学）：

| 候选 | 结构 | 说明 |
|---|---|---|
| M1 | 冻结BERT-base-chinese + 线性CRF头 | 只训发射头+转移矩阵（参数量~10^4级） |
| M2 | 冻结BGE-large-zh token输出 + 线性CRF头 | 复用项目已有1024维冻结快照管线 |
| M3 | LLM few-shot预标 + 人工校验 | 半自动；预标质量本身须先按本协议评估，防循环论证 |

预注册对照实验（S2触发后执行）：

- 三臂：规则only / 模型only / 模型+规则约束（CRF转移约束或后验白名单过滤）；
- 主指标：每类型span precision（同一协议、同一标注分布）+ 覆盖率（基线=谓词32.12%与六类各自规则覆盖）；
- 判定：模型必须precision不降（每类型Δ≥-0.02）且覆盖提升，否则规则仍是主抽取器（负结果空间预注册）；
- 划分：文档级4-fold（沿用balance_folds的16文档分配），**标注开始前先分配fold**防泄漏；test fold文档的span不得进训练集；
- negative类是首战场：规则零覆盖，模型增益在该类最干净可测。

## 4. Confidence-aware可视化原则

槽位状态三色（来自feature_matrix，逐span渲染）：

| 颜色 | 条件 | 语义 |
|---|---|---|
| 绿 | parse_status=parsed（slot_fill_rate≥0.5） | 六槽位过半填充 |
| 黄 | parse_status=partial（0<rate<0.5） | 部分填充 |
| 红 | 无槽位/抽取失败 | 规则未命中 |

tier三色：

| 渲染 | tier | 判据 |
|---|---|---|
| 绿实底 | gold_frozen（P1/L1） | 显式ID锚定 |
| 黄 | silver（P2/结构桥接） | 结构证据 |
| 灰 | candidate（L2 fuzzy） | 未校准候选 |

四条原则：

1. **不确定性必须可见**：每个高亮span必须带(tier, parse_status)badge；禁止只渲染高置信结果——选择性呈现=隐藏误差；
2. **低置信同样可标**：红/灰span必须开放✓/✗（低置信≠不可评；tier决定"多可信"，人决定"对不对"）；
3. **页面常驻policy声明**："五元组为候选非gold"（沿用render_feature_dashboard的声明模式）；
4. **导出格式向后兼容**：`{span_text, span_type, block_index, verdict, ts}` + 可选`{tier, parse_status, slot_fill_rate}`（评估器容忍缺失字段，不因扩展破坏旧导出）。

## 5. 对齐状态可视化

三色语义（与48号锚点层级对齐）：

| 状态 | 颜色 | 判据 | 对应tier |
|---|---|---|---|
| explicit | green `#2e7d32` | 显式ID/编号共指 | L0/L1 gold_frozen（L1=846） |
| supported | amber `#f9a825` | 结构桥接（title-bridge、同表/同图兄弟约束） | silver |
| speculative | gray `#9e9e9e` | 模糊/向量候选 | candidate（L2_lexical 3940；L2_vector 12392@θ=0.5801） |

左右对照中跨模态对齐边（claim↔table_row、claim↔diagram_node、table_row↔diagram_node）的渲染规则：

1. 线型：explicit实线 / supported虚线 / speculative点线；
2. hover显示证据三元组`(candidate_generator, tier, score)`；
3. speculative边不进入页面汇总统计；点击可升级/降级（衔接48号P1/P2标注协议，不得自动传递闭包）；
4. 视觉优先级由tier决定而非连续score——离散证据义务>连续相似度（与E3契约同哲学）；
5. 边锚定到span级：连接"左侧原文span↔右侧提取槽位"而非整块（对齐边本身span-grounded）；
6. 页眉常驻explicit/supported/speculative计数条（对齐可信度画像，非gold）。

## 6. 与48号矩阵的接口

两层独立：

| 层 | 裁决对象 | 裁决者 | 指标 |
|---|---|---|---|
| 抽取层（span grounding，本协议） | 单个span抽得对不对 | 人工✓/✗ | 每类型span precision+Wilson CI |
| 关系层（gold-proxy，48号§15.1） | 两个occurrence是否同一实体 | 规则∧BGE∧Qwen3三信号 | same_identity AUC/F1/false merge |

规则：

1. span precision成为48号矩阵的**解析层新指标**（P族过程指标行，与谓词覆盖率、slot_fill_rate并列——后两者是结构性代理，span precision是语义正确性测量），不进A-E主对照；
2. 两层指标不得互相替代、不得合并为单一分数；
3. 关系层实验的误差归因必须引用抽取层precision（误差传播下界）；
4. 关系层数字不得反推抽取质量（gold-proxy的AUC 0.9018是对齐判别力，不是抽取正确率）。

## 7. 风险

| 风险 | 表现 | 缓解 |
|---|---|---|
| 标注者偏差（单标注者） | Wilson CI只覆盖抽样方差，不覆盖系统偏差 | 判定准则手册（附录A）+每类型10%延迟复标（自一致率入报告）+按ts分桶报告疲劳效应；双标注/专家裁定在M2前不可得（如实声明） |
| span边界模糊 | 中文无词边界："支持XX功能"宾语止于哪；"分辨率不低于1920×1080"的算子/数值/单位切分点 | 预注册边界规则（附录A）；✗可带可选`reason="boundary"`；±1字符容差precision仅作诊断辅助，不替代严格口径 |
| 规则高亮≠规则正确 | `find()`定位成功≠语义正确（高亮的"1920"未必是分辨率） | 这正是span precision要测的对象；判定准则必须区分boundary/type/value三类✗（附录A），否则错误分析失焦 |
| 标注-训练循环泄漏 | S2模型在训练文档上评测 | 文档级fold先行分配；LLM预标（M3）若引入须单独声明并先评估预标质量 |
| localStorage单点 | 浏览器数据丢失 | 导出即入库：每次评估存runs协议result.json |

## 8. 代码入口与首次冒烟

```text
tools/eval_span_grounding.py        评估器(合并/去重/分层precision/Wilson CI/runs协议/--output报告)
tests/test_eval_span_grounding.py   Wilson数学+类型分组+去重/冲突+空输入/不足样本(31项合成数据测试)
viewer(左侧原文/右侧提取+span级✓/✗)  并行Agent开发中, 导出格式=§2
```

用法：

```text
python tools/eval_span_grounding.py --annotations spans1.json spans2.json --output report.md
```

首次冒烟（2026-10-22，20条合成标注）：18条合法，去重后17个span（1个重标键、verdict冲突1、ts最新者胜出）；总体precision 0.8235，Wilson 95% CI [0.5897, 0.9381]；六类全部insufficient（<50，冒烟不构成精度结论）；未知类型subject=1、非法verdict=1均计数未丢弃。run：`eval_span_grounding_aa571ee7_20261022_105029`。

## 附录A span判定准则 v0（单标注者）

✓当且仅当三条件同时成立：(1)边界正确（不多不少）；(2)类型正确；(3)值与原文一致。

✗三分类（viewer可选`reason`字段，向后兼容，评估器容忍缺失）：

```text
boundary  边界错(多标/少标字符)
type      类型错(如把宾语标成predicate)
value     值错(高亮位置对但语义与槽位不符)
```

边界规则 v0：

- identifier：完整编号串（字母-数字-连字符段，如`JCYY-GN-JCYYKJYYWTX`；章节号`3.2.1`单独成span）；
- quantity_unit：数值+紧邻单位；算子（`≥`/不低于/不超过）默认并入；
- predicate：动词+宾语名词短语（口径同mine_function_predicates：轻动词剥离、宾语后缀剥离）；
- modal：单个情态词（应/宜/可/必须）；
- negative：最小否定短语（不/无/未/禁止+紧邻动词，至动词止）；
- reference：编号+类型词（`见3.2.1节`/`图3`/`表2`）。

## 附录B Wilson样本量参考表

p̂=0.9时（自实现wilson_interval计算，z=1.959963984540054）：

| n | 95% CI | 宽度 |
|---:|---|---:|
| 50 | [0.7864, 0.9565] | 0.170 |
| 100 | [0.8256, 0.9448] | 0.119 |
| 200 | [0.8506, 0.9343] | 0.084 |
| 300 | [0.8608, 0.9291] | 0.068 |
| 500 | [0.8706, 0.9233] | 0.053 |

推论：

1. n=50只能排除粗失败（p̂=0.9时下界0.7864）；下界≥0.85需n≈200；
2. 强达标（下界≥0.90）所需最低p̂随n下降：n=50需全对（1.0000→0.9287；49/50=0.98仅0.8950）；n=100需p̂≥0.96（96/100→0.9016）；n=200需p̂≥0.945（189/200→0.9042）；n=300需p̂≥0.9367（281/300→0.9032）；
3. Wilson下界恒≤p̂：p̂恰为0.90时强达标在任何有限n下不可达——强达标口径实质把门槛抬到p̂≈0.94~0.96（n=100~300区间），这是"目标≥0.90"的隐含严格性，报告时必须明示。
