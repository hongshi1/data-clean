# 105. R2 identifier通道接地概率化: "ID在场即support"信任假设的概率化修复

> 定稿日期：2026-11-24 | 任务来源：99号Phase 3（R2）· 方法学依据：97号§2.4（PL-Guard接地/策略分离）· 98号B类三切口之① · 104号§7遗留（L1协议禁support的配置面根源=本任务靶点）
> 实施脚本：`tools/calibrate_identifier_grounding.py`（校准）/ `tools/eval_identifier_grounding.py`（验收评测）
> runs：校准=`calibrate_identifier_grounding_6020e165_20261124_154409`，验收=`eval_identifier_grounding_c0a5a118_20261124_163614`
> 测试：`tests/test_identifier_grounding.py`（14项）+ `tests/test_claim_channels_rules.py`（37项，显式更新锚点）
> 接口契约由E7（M132）预留：本任务零通道层协议变更，校准产物进`config/claim_channels_rules_v1.json`的`channel_confidences.identifier_grounding`节（MANIFEST已重建）

## 0. 一句话结论

**范式落地=成立，验收三闸门全过**：`verify_identifier`的support置信度从恒定1.0改为校准的P(绑定|在场, context)（逻辑回归IRLS确定性校准，296例误判案例库，训练F1=0.876），低于阈值保守降级NIE（"在场但绑定不确定"的新语义，不是refute）；**C06QA-016/017的假support被正确降级**（support→NIE，"right detail, wrong entity"的信任假设失败模式被修复）；91QA主评测**逐位零变化**（0.9121/0.7212，CLIPR零回退=零翻转）；violations-17 refute **16/17不降**；延迟增量**0.246ms/claim**（CPU词法，零API/零GPU）。诚实代价：crossdoc06 macro-F1 0.2619→0.2600（-0.002，C06QA-016/017从假support移入NIE使NIE精确率微降；support类F1反而0.1333→0.1538）——错例数20不变（016/017的gold=refute，实例级仍错，修复的是**假support机制**而非refute检出）。**新发现（负面）**："ID在场即support"信任假设实际存在于**三处**——R2接地了其中一处（verify_identifier），另两处（L0 entity_detector TERM-07、L1 id_join裸ID support路径）经per-claim融合**否决**R2的降级，实证了C06QA-026/029不翻转的机理，把104号§7的结构性问题精确定位到融合协议层。

## 1. 误判案例库（Step 1交付）

**总数296例**（claim级、ID在场、全部可审计，落盘`data/gjb_438c/distillation/identifier_grounding_cases_v1.jsonl`，每例含question/answer/evidence/features/label/来源溯源）：

| 来源 | 数量 | label=1（绑定对） | label=0（绑定错） | 说明 |
|------|------|-----------------|-----------------|------|
| `d3_train` interface_flow族 | 257 | 104（s_interface_narrative：answer复述接口表真实流向） | 153（r_sender_swap发送方跨行污染77 + n_effect_claim效果性断言杜撰76） | **排除文档04/06**（04=91QA评测冻结文档、06=crossdoc06评测冻结文档——训练/评测文档不重叠的LODO纪律） |
| refute路径最小对（孪生） | 1 | 1（S1QA-084的孪生：answer的ID替换为该subject在证据注册的ID） | — | verify_identifier第5步same-subject-mismatch refute路径自然产出；d3_train的r_*算子只换值不换ID，refute路径实例全数据集仅91QA S1QA-084一例（violations的VIO-02..05走id_join不走该路径） |
| ID错配最小对（合成孪生） | 38 | — | 38（twin_id_sibling：answer的ID替换为同表兄弟行ID——ID在场但subject绑定错，VIO-03/04形态） | 绑定对vs绑定错只差ID一个字段；38/104对可合成（其余兄弟行ID在证据原文跨`<p>`拆分，不可达support路径，如实丢弃） |

类型分布即"ID在场但绑定错"的三类形态：**发送方跨行污染**（77）/ **效果性断言杜撰**（76+）/ **subject-ID错配**（38）。d3_train全量扫描的537条在场identifier claim中，trace_binding族（249条）**不入训练**——章节绑定（4.1.2c vs 4.1.1a）在claim层不可分（章节前缀共享），属trace专家职责；该诚实限制使C06QA-009/010/019/020的identifier claim同样被保守降级（实例原本NIE，零实例级影响）。

## 2. IdentifierGroundingJudge（Step 2交付，方案选择理由）

**选择：特征校准逻辑回归**（四维词法/邻近特征 + IRLS），而非嵌入相似或PL-Guard式token分数。理由：
1. **零远程API+零GPU**（GPU被切分器v3训练占用，任务硬约束）——特征全是确定CPU词法，延迟0.246ms/claim（约束<50ms）；
2. **推理确定性**（同输入同输出，快照测试锁定）——BGE嵌入即使磁盘缓存，首次未命中时仍需GPU前向且引入数值波动风险；
3. **特征即绑定语义**：PL-Guard的"接地谓词概率"在本域的自然对应物是"subject-ID窗口距离/谓词一致性"（99号R2任务书原话），四维特征全部可逐例审计（每例落盘特征dict）；
4. **PL-Guard式token分数**（本地小模型True/False归一化）需要一次前向/claim（本地LLM级延迟）或额外训练，收益不明确——文献同构保留在方法学叙事（97号§2.4），工程上特征校准是其"renormalized分数"的可审计简化。

**评分公式**（`algorithms/consistency/identifier_grounding.py`）：

```
P(绑定|在场, context) = sigmoid(w·f + b)
f = (subject_bind_ratio,      # answer的subject核心前缀在证据ID绑定段的最长命中占比（空subject=1.0无约束）
     predicate_hit_ratio,     # answer局部断言内容词在证据ID绑定段的命中率（无内容词=1.0）
     id_block_ratio,          # ID跨块在场广度 min(块数,3)/3
     subject_id_proximity)    # subject前缀→ID邻近距离软特征 max(0, 1-d/60)（30/100硬窗口升格为软分数）
```

绑定段=**证据ID所在表格行**（`</tr>`切分+HTML标记剥离+空白折叠；非表格块整段）——绑定（接口→发送方）是行内关系，跨行命中是污染而非佐证（C06QA-016的发送方"界面集成框架"来自同表第3行）。answer局部断言=**含ID的行/句**（列表项不跨行——"序号1：ID"的下一项不属于本ID的断言语境）。内容词=中文/字母数字连续段按**胶水词表切开**（39词模板功能词，配置化）；两个实现教训：(a) 问句回声词与subject词**不能**过滤——interface_flow族的问句（"{发送方}与{接收方}接口的接口流向是什么？"）内嵌发送方/接收方，过滤会把绑定内容词误删（实测label-1的predicate_hit_ratio被压到0.5）；(b) 中文连续段上限须≥20字——12字上限把长谓词切碎产生"用软件"式碎片假命中（C06QA-017一度因此免于降级）。

**注入契约**（照SemanticNliJudge模式，评分函数不进claim_channels）：
- `IdentifierGroundingJudge`（冻结dataclass：权重+阈值+胶水词表）经`qa_module(identifier_grounding=...)`注入，`verify_identifier(..., grounding=None)`默认不注入；
- presence保持必要条件（无在场→refute/NIE路径**逐位不变**，测试锁定）；refute路径（同subject窗口唯一不同ID）**保持确定性1.0**（B类代数本体不动，测试锁定）；
- P≥threshold→support@P（method不变`identifier_exact_match`，rationale带接地概率）；P<threshold→**保守NIE**（method=`identifier_grounding`，confidence=P，在场refs保留可审计；rationale不撞`_ACTIVE_NIE_RATIONALE_MARKERS`——降级是"无法确证绑定"不是主动负观察，dominant_70聚合下不投票）。

## 3. 校准数字（Step 3交付）

IRLS牛顿迭代（200轮+1e-12容差，L2岭λ=1截距不罚，**零随机源**——同数据同权重逐位复现）；阈值=训练F1最大化（候选=相邻分数中点，并列取更低=保守方向）：

| 项 | 值 |
|---|---|
| threshold | **0.4571** |
| w(subject_bind_ratio) | +0.5620 |
| w(predicate_hit_ratio) | **+5.4590**（判别主力：label1均值0.916 vs label0均值0.475） |
| w(id_block_ratio) | -0.6191 |
| w(subject_id_proximity) | +1.2717 |
| intercept | -5.7383 |
| 训练表现 | acc 0.8986 / P 0.8762 / R 0.8762 / **F1 0.8762**（296例） |
| 分数间隔 | **-0.754（重叠，如实报告）** |

重叠来源（错分检视）：label-0高分=**同ID多行登记**的绑定段并集病理（doc07的PZXQ-JK-BWCS三行重复=真实VIO-01双登记， polluted发送方恰在并集内→f2=1.0）27例——实例级由id_join双登记refute覆盖，无害；label-1低分=证据行与answer措辞变体（"服务支撑环境"vs"环境运行保障"）9例。**验收关键间隔**：S1QA-053（必须保留support的91QA约束实例）P=0.794 vs C06QA-016/017 P=0.289/0.337——0.46阈值居中，余量0.34。

复现命令：`python tools/calibrate_identifier_grounding.py --report`（只读报告）/`--write`（写config+案例库+runs存证）。

## 4. 三评测集前后对照（Step 4交付，judge注入 vs 不注入）

| 评测集 | 指标 | baseline（不注入） | judge注入 | 验收 |
|--------|------|------------------|-----------|------|
| crossdoc06(30) | acc / macro-F1 / wrong | 0.3333 / 0.2619 / 20 | 0.3333 / **0.2600** / 20 | C06QA-016/017修复✓（见下）；macro-F1变化如实报告 |
| 91QA(91) | acc / macro-F1 / wrong | **0.9121 / 0.7212 / 8**（=论文deterministic口径，逐位） | **0.9121 / 0.7212 / 8**（逐位相同） | CLIPR零回退✓（正确→错误翻转=0，错误→正确=0——零实例变化） |
| violations-17 | refute检出 | 16/17 | 16/17 | 不降✓ |

**C06QA-016/017逐例**（`runs/eval_identifier_grounding_c0a5a118_20261124_163614`）：

| 实例 | baseline | judge注入 | identifier claim（注入后） | 机理 |
|------|---------|----------|---------------------------|------|
| C06QA-016 | support（gold=refute，**假support**） | **not_in_evidence** | NIE@P=0.2885，method=identifier_grounding，f2=0.67（发送方"界面集成框架"不在RJJHJK行段） | 假support机制修复：降级NIE抑制了identifier support；TERM-07 support仍在但被NIE阻断聚合（refute>NIE>support） |
| C06QA-017 | support（gold=refute，**假support**） | **not_in_evidence** | NIE@P=0.3372，f2=0.67（"统一传输服务"不在YYRJ行段） | 同上 |

实例级诚实注记：016/017的gold=refute，support→NIE仍是错例（20 wrong不变）——修复的是**"ID在场即support"的误判机制**（97号§4.3归因③的"lexicon trust assumption"失效模式），refute检出（发送方swap的显式矛盾判定）需接口流向专家，不在identifier通道职权内。macro-F1 -0.0019的构成：support F1 0.1333→0.1538（假support移除后精确率0.2→0.333）；NIE F1 0.4706→0.4444（016/017移入NIE|refute混淆格使NIE精确率8/24→8/26）；refute不变。

**C06QA-026/029不翻转的机理（新发现）**：其identifier claim已被降级（P=0.060/0.0026），但answer前缀"接口"是id_join的subject停用词→claim按**裸ID声明**处理→id_join裸ID support@0.9（"ID在场且注册表命中"——同一信任假设的L1版本）经per-claim融合（refute>support>NIE，claim_text同为裸ID）**否决**了identifier通道的降级NIE；加上TERM-07 support，实例保持support（gold=NIE，维持原错例）。即："ID在场即support"活在三处——verify_identifier【R2已接地】、L0 TERM-07【未接地】、L1 id_join裸ID路径【未接地】；融合协议让未接地的L1 support压过已接地的通道降级。

## 5. 延迟增量实测

`verify_identifier`的judge增量：**0.246ms/claim**（crossdoc06+91QA全量19个identifier support路径claim，总0.0047s；纯CPU词法，零API/零模型加载/零GPU）——约束<50ms/claim，**余量200倍**。两臂全评测墙钟无可观测差异。

## 6. 与104号§7遗留（L1协议禁support）的关系

104号§7："9条support侧失败结构性不可达——enum_join/id_join只输出refute，注册表与声明一致时**静默交回旧通道**，L1输出协议不允许规则层产生support判定……修复需引擎输出协议扩展——属97号§2.4接地概率化/R2路线。"

**本任务的关系判定：部分缓解+问题精确定位。**

1. **缓解的部分**：§7描述的"静默交回旧通道"链条，其**落点**（旧通道=verify_identifier）已被接地——id_join对绑定一致的声明静默交回后，旧通道不再输出盲目的support@1.0而是P(绑定)（016/017实证：交回→接地→降级→实例NIE）。"support判定不允许出现在规则层"的协议限制被绕开的方式不是给L1加support，而是给接收交回的通道加**校准的support置信度**——这比扩展L1输出协议的侵入性小得多，且向后兼容（不注入=原行为）。
2. **未缓解的部分（实测定位）**：L1**自身**的support路径（id_join裸ID support@0.9）与L0的TERM-07 support@0.9仍未接地，且per-claim融合契约（"结构化专家的decisive verdict压过通用通道的NIE"）使它们**否决**已接地的降级（C06QA-026/029实证）。所以§7的结构性问题现在有了精确形状：不是"L1完全不能support"（裸ID路径可以），而是**"未接地的L1/L0 support在融合中压过已接地的通道降级"**。修复路径两条：(i) 把IdentifierGroundingJudge按同一注入模式接到id_join裸ID路径与TERM-07（模式已验证，工作量小）；(ii) 融合协议扩展——"grounded降级NIE"应强于"未接地bare-ID support"（需要协议变更，即§7预判的"引擎输出协议扩展"）。两者都是R2模式的直接推广，非新范式。
3. **对99号叙事的贡献**：B类三切口之①（接地概率化）从文献判断（97号§2.4 PL-Guard同构）变为**已落地的可审计实现**——四维特征+确定性校准+保守降级语义+三评测集闸门，且"信任假设三处存活、融合否决接地"的失败模式发现为分层迁移论点（97号§7"正则替代的正确叙事"）提供了新的实证细度：概率化必须**全链路一致**，单点接地会被未接地邻居的融合权重吞没。

## 7. 产物清单

| 产物 | 路径 |
|------|------|
| 评分器+judge | `algorithms/consistency/identifier_grounding.py`（特征/judge/配置数据类，模块顶层零I/O） |
| 通道接入 | `algorithms/consistency/claim_channels.py`（verify_identifier可选grounding参数+规则schema扩展） |
| 模块注入 | `algorithms/consistency/qa_module.py`（identifier_grounding参数，None=不注入） |
| 校准配置 | `config/claim_channels_rules_v1.json`（channel_confidences.identifier_grounding节：阈值+权重+胶水词表；MANIFEST已重建） |
| 校准脚本 | `tools/calibrate_identifier_grounding.py`（案例库构建+IRLS+阈值+写config） |
| 验收评测 | `tools/eval_identifier_grounding.py`（三评测集×两臂+CLIPR闸门+延迟实测） |
| 案例库 | `data/gjb_438c/distillation/identifier_grounding_cases_v1.jsonl`（296例） |
| 测试 | `tests/test_identifier_grounding.py`（14项：特征快照/逐位兼容/refute不变/降级语义/阈值边界/注入线路）+ `tests/test_claim_channels_rules.py`（显式更新：R2值钉住+8条identifier_grounding校验mutate） |
| 校准run | `data/gjb_438c/runs/calibrate_identifier_grounding_6020e165_20261124_154409` |
| 验收run | `data/gjb_438c/runs/eval_identifier_grounding_c0a5a118_20261124_163614` |

## 8. 诚实契约

- 训练/评测文档不重叠（LODO排除04/06）；评测集实例未进训练（refute路径孪生是合成对照侧、本身不在任何评测集，其91QA同源性已如实披露；ID错配孪生来自非排除文档）；
- 训练分数重叠（margin -0.754）如实报告，错分案例已逐类归因（并集病理/措辞变体）；阈值0.4571的验收关键间隔（S1QA-053 0.794 vs C06QA-016/017 0.289-0.337）显式给出；
- macro-F1微降（-0.0019）如实报告并分解到逐类F1；C06QA-016/017实例级仍错（gold=refute）如实声明——本任务修复的是假support机制，不是refute检出；
- 全套测试（65项相关）+ruff零报错；工作区含并发会话的未提交修改（e1/trace专家等），预先存在的测试失败经stash取证确认与本任务无关（route_question空stub等）；
- judge不注入=baseline臂逐位复现论文数字（0.9121/0.7212/16/17/0.2619）。
