# CascadeVerify 技术架构文档

> 版本 v1.0 | 2026-10-28 | 配图: `paper/figures/fig0_research_framework.png`
> 状态: 算法侧完成, 1351测试全绿, 数字锁定于 49号文档(583项核对)
> 读者: 论文写作参照 / 技术评审 / 新场景接入者

---

## 0. 一页总览

**做什么**: 校验LLM生成的答案是否与军事SRS文档(GJB 438C格式)的冻结证据一致——三态判定(support/refute/NIE) + 证据定位 + 检测项归因。

**怎么分层**(按检测的不一致性类型分工):

```
检测对象: 40项不一致性体系
  术语类TERM×8 ──→ L0 NER实体层      (词典gazetteer链路, 配置驱动)
  参数/逻辑/合规类 ─→ L1 符号规则层   (rulepack引擎 + GJB规则库, 配置驱动)
  其余语义型 ────→ L2 NLI语义层      (EGT三态合成训练的域适配模型)
  层间: 残差派发 + per-claim融合 + 开放世界聚合
```

**三个技术性质**(设计目标, 均有保证机制):
- **确定性**: L0/L1零模型调用、jieba固定HMM=False——同输入永远同输出
- **可追溯**: 每个判定可回溯到(证据块/行, 检测项ID, GJB规则ID+标准章节锚)
- **场景可迁移**: 域知识全部外置为两个JSON(词典+规则包), 换场景不换代码

**支撑数字**: 91QA acc 0.912/macro-F1 0.721(确定性层, 零LLM成本) | 真实违例16/17 | held-out test 0.829 | 级联(含LLM仲裁)refute F1 0.800@18%成本

---

## 1. 任务定义

**输入**: 三元组 (Q, A, E)
- Q: 用户问题; A: 待校验的答案; E: 冻结证据块集合(检索阶段已固定, 每块带`evidence_id/类型/source_ref/完整性协议`)

**输出**: 每个answer一个判定包
```
(verdict, evidence_refs, check_item_ids, justification)
 verdict ∈ {support, refute, not_in_evidence}
```

**三态的部署语义**(为什么必须三分而不是二分):

| verdict | 含义 | 下游动作 | 错误代价 |
|---|---|---|---|
| support | 证据明确支持 | 放行 | 假support漏检错误答案 |
| refute | 证据明确反对 | **拒绝该答案** | 假refute杀死正确答案(代价最高) |
| NIE | 开放世界不可判定 | 人工复核/重检索 | 假NIE仅浪费复核 |

开放世界假设: 证据completeness=open时, "证据中没有"≠"文档中不存在"——这是NIE与refute的分界, 也是整个系统保守性的根基。

**检测对象**: 40项不一致性体系(taxonomy v3, 源自官方实施方案):
- 术语类 TERM-01~08(同义异名/同名异义/枚举集不匹配/ID冲突/缩写)
- 参数类 PARAM-01~10(同参数异值/量纲/区间/聚合约束)
- 逻辑类 LOGIC-01~11(异常处置矛盾/事件时序/约束可满足性)
- 合规类 GJB-01~11(标准条款有无/追溯/合格性覆盖)

---

## 2. 架构分层

### 2.1 L0 NER实体层 —— 检测术语类

**职责**: 实体抽取→文档词典→实体链接→术语冲突检测。覆盖TERM-01/02/05/07/08(全部为实体级比对: 名称/ID/缩写/定义)。

**技术链路**(领域自适应词典gazetteer, 垂直域无标注场景的业内标准打法; **详解见66号文档**):

```
配置(可替换)                    引擎(通用, 不随场景变)
config/ner_lexicons/xxx.json    algorithms/consistency/
  domain_terms   域术语表          entity_detector.py   抽取/链接/冲突检测
  id_patterns    标识符正则         ner_lexicon.py       schema+加载+校验
  value_domains  值域闭集           jieba链路: 自定义词典(HMM=False)
  stopwords/entity_categories/    build_document_lexicon: 运行时从证据
  alias_patterns/...                 归纳实体表(动态gazetteer)
```

**为什么选这条链路**(而不是UIE/GLiNER零样本NER):
1. 实体形态是封闭集/模式化的(PZXQ标识符、{桌面,平板,手持}值域、用例名可从表格枚举)——词典/正则不输深度模型, 深度模型的优势(开放域泛化)用不上
2. 确定性硬约束: L0是级联第一层, jieba固定HMM=False, 零随机性污染下游
3. 零NER标注: 军事SRS域无span标注数据
4. 成本结构: L0免费(纯CPU), 预算留给L2/L3
5. 可审计: 每个实体命中可指认词典行/正则

**链接算法**: exact → 别名(括号定义对) → 前缀(最长公共前缀) → NIL(未链接, 不视为错误)。

**业内定位(诚实)**: 第一代确定性分支, 对标spaCy EntityRuler的"词典即配置"模式; 不是最先进(那是UIE/GLiNER), 但对本任务的实体形态和约束是正确选择。已知边界: 开放类型/高变体表述/零配置冷启动需升级到零样本模型(可作为词典未命中时的回退层)。

### 2.2 L1 符号规则层 —— 检测参数+逻辑+合规类

**职责**: 把证据线性化为**(主体, 值, 位置)注册表**, answer声明与注册表做跨位置join——矛盾信号从"分散在两处的各自无辜语句"变成"同键不同值的显式冲突"。

**技术形态**(rulepack引擎, 配置驱动):

```
配置(可替换)                        引擎(通用)
config/rulepacks/xxx.json           注册表构造 + join裁决 + 求解
  table_schemas   7表型签名+列语义      (怎么比/怎么判 留在引擎)
  extraction_templates  57个提取正则
  term_vocabularies    14个词表
  join_params/thresholds
  gjb_rule_library_path ──→ knowledge/gjb_438c_rules_full.json
                              (120条规则: rule_id/type/source/severity/
                               original_text, 87条适用SRS)
```

**六个检查族**(九专家=一个注册表思想+一个GJB规则引擎):

| 检查族 | 覆盖检测项 | 机制 | 可追溯输出 |
|---|---|---|---|
| Z3数值约束 | PARAM-01/03/05/06/07 | 区间包含/量纲换算/聚合约束, 求解器输出 | **SMT-LIB + unsat core**(防伪符号推理) |
| E1模板+序列对齐 | LOGIC-02/03 | 异常流模板提取比对; 事件流编号配对+单调性 | 模板字段级定位 |
| ID join | TERM-07 | ID→主体注册表; 双登记/父子绑定/段序 | 注册位置对 |
| 枚举join | TERM-03 | 值域注册表; 集合比对/错字(编辑距离=1) | 行级定位 |
| 追溯/覆盖 | GJB-01/04/05/06 | 双向追踪join/逐章覆盖/封闭清单 | 行级+规则ID |
| **GJB规则引擎** | GJB-01~11 | **从120条规则库编译检查**(55条可自动编译, 32条诚实标记manual) | **rule_id + 标准章节锚(附录J 3.X)** |

**GJB规则引擎的编译链**(这是规则层的知识来源声明):
```
规则原文(附录J规范句"应指明/应描述/应注明X")
  → 规范动词定位 → 跨文档主语判manual → 宾语短语提取
  → 「包括:」「如…等」枚举展开 → CompiledCheck(patterns, source_anchor)
  → 文档审计: 每规则verdict(satisfied/partial/violated/unknown)+证据refs
```
检查逻辑**100%从规则原文程序化推导**——不是手编关键词清单(这是M32重建修正的核心: 规则层的知识源必须是标准本身)。

**性质**: 纯确定性(零模型调用) | refute精确率0.83 | 单元格级定位 | 17真实违例检出16/17。

**已知边界(双登记定律)**: 符号层专责**证据内部**跨位置冲突(双登记, 检出率1.0); answer侧单边破坏归语义层(检出0.05-0.53, 394注入对照)——这是层间分工的实验依据。

### 2.3 L2 NLI语义层 —— 检测其余语义型

**职责**: 规则不可形式化的answer-vs-证据语义比对(措辞错配/跨行值断言/效果性声明)。

**技术形态**: mDeBERTa(278M)域适配微调, premise=聚焦证据语句, hypothesis=claim, 三分类+概率门控。

**训练数据来源(EGT三态构造性合成)**:
```
S样本 ← 已验证种子+改写(构造保证: claim说的就是证据写的)
R样本 ← 跨行污染(同文档另一行的真实值绑到错误主体——sound矛盾)
N样本 ← 支撑span删除(开放世界缺≠矛盾)
4500样本, 叙事文法
```
**文法定律**(EGT的科学发现): v1近拷贝文法在合成分布dev=0.965但真实迁移0.50(模型学到"找diff"); v2叙事文法(claim形态匹配真实答案)使refute召回0.375→0.875。**合成数据的claim形态分布与标签sound性同等重要。**

### 2.4 层间机制(架构的粘合剂)

```
C1残差原则: 上层已决的claim永不下沉
  (经济: 免费且更准; 代价已测量: confident-but-wrong不可下游修复)

per-claim融合: 同claim文本的多通道结果取 refute > support > NIE
  (弱通道的"unresolved NIE"不否决强通道的已验证support)
  消融验证: 去除融合→macro-F1 -0.152(单一最大组件)

实例聚合: 任一refute→R | 全support→S | 否则NIE(开放世界)
  (与silver的GLM宽松语义有已量化的差异, gold标注将终裁)

[工程旁路, 非算法组件] L3 LLM仲裁: L2的refute候选实例级升级到
  glm-5.3复核(缓存), 15次调用=18%成本→refute F1 0.800
```

---

## 3. 场景迁移(配置化架构的核心主张)

**接入新场景(新文档/新领域) = 写两个JSON, 零代码改动**:

| 配置 | 内容 | 已验证的迁移演示 |
|---|---|---|
| `config/ner_lexicons/<scene>.json` | 域术语/ID正则/值域/停用词/实体类别 | 06号场景: 同引擎换配置, 域词命中38→174(CPU/WPS/运行状态监控仅在06配置命中) |
| `config/rulepacks/<scene>.json` | 表型签名/提取模板/词表/join参数/阈值 | 06号场景: 同引擎识别88张表(双`<p>`标签ID拼接/表头变体/PZXQ-YXZCFW族过滤) |

**分层配置原则**(什么进配置/什么留引擎):
- 进配置: 签名/模式/词表/阈值/窗口——"检查什么、匹配什么"(48项已迁移)
- 留引擎: join算法/NW对齐/Z3求解/聚合语义——"怎么比、怎么判"(9项)
- 暂缓: 3项(coverage词表耦合/srs_kb单位词典/规则簇映射), 设计文档64号有记录

---

## 4. 端到端数据流走查(S1QA-056真实案例)

**输入**: Q="SQL访问的修改数据功能包括哪些操作" A="…支持在桌面、平版和平板设备上运行" E=8块冻结证据(含能力表)

```
① answer分解 → 原子claim: "修改数据功能支持在{桌面,平版,平板}设备上运行"
② L0 NER层:
   词典配置(srs_scene1) → 抽出实体: 修改数据(用例名, 文档词典命中)
   桌面/平板(值域闭集命中) 平版(未命中值域——NIL, 移交下层)
③ L1 规则层(enum_join族):
   rulepack的字段模式(需求重用列) → 从证据构建值域注册表:
   修改数据 → {平板, 桌面} @能力表行
   answer枚举声明 vs 注册表比对:
   - "平版"不在注册表, 与值域词"平板"编辑距离=1 → 疑似错字 → refute信号
   - 集合比对: 声明集{桌面,平版,平板} vs 注册集{平板,桌面} → 污染成员"平版"
④ 判定: refute (TERM-03枚举集不匹配)
   输出: evidence_refs=[能力表块ID] + check_item=TERM-03
   + rationale="多出疑似错字成员『平版』→平板; 该行需求重用={平板,桌面}"
⑤ 聚合: 该claim refute → 实例verdict=refute
```

**同例走L2路径**(若L1未决): EGT训练的NLI读(premise=能力表行语句, hypothesis=设备声明) → contradiction概率0.9 > 门控 → refute。

---

## 5. 设计决策记录(ADR摘要)

| # | 决策 | 备选 | 理由 | 证据 |
|---|---|---|---|---|
| D1 | NER用词典gazetteer链路 | UIE/GLiNER零样本 | 封闭实体集+确定性约束+零标注 | 跨场景命中38→174; 业内对标见§2.1 |
| D2 | L1规则库驱动(从120条规则编译) | 手编关键词清单 | 知识源必须是标准本身; 可追溯性 | 04号审计7项exact命中taxonomy |
| D3 | 三态而非二分类 | MiniCheck式二元 | 假refute与假NIE代价不对称 | 部署语义表§1 |
| D4 | EGT叙事文法 | 近拷贝扰动 | claim形态分布决定迁移 | 0.375→0.875召回 |
| D5 | per-claim融合优先于全局聚合 | 全局refute>NIE>support | 弱通道不可否决同claim强通道 | 消融-0.152 |
| D6 | C1残差派发 | 全claim过语义层 | 经济+正确(弱判官重判已决引入错误) | 15次调用vs83次 |
| D7 | Z3输出unsat core | 仅verdict | 防"伪符号推理"(scope laundering) | Know Your Limits审计结论 |
| D8 | 开放世界聚合(缺≠矛盾) | 封闭世界 | 检索证据不穷举文档 | silver的NIE语义实证 |

---

## 6. 技术性质保证

| 性质 | 保证机制 | 验证 |
|---|---|---|
| 确定性 | L0/L1零模型; jieba HMM=False; 无随机种子依赖 | 91QA逐位复现; 实体digest全局锁定(678199a3) |
| 可追溯 | ClaimResult四元组(判定+refs+检测项+rationale); GJB规则带rule_id+标准章节锚 | 17违例逐条可指认位置 |
| 可复现 | 全部评测走runs协议(配置+git_sha+result); LLM走缓存 | 重跑字节级一致 |
| 成本可控 | L0/L1免费; L2本地(12s全corpus); L3被路由(15次) | RefuteRecall@成本曲线(fig3) |
| 行为保持重构 | 评测作为回归oracle | 三次大重构(拆分/配置化)混淆矩阵逐位不变 |

---

## 7. 评测数字支撑(全部可溯至runs)

| 维度 | 数字 | 来源 |
|---|---|---|
| 91QA确定性层(算法本体) | acc 0.912 / macro-F1 0.721 / 零LLM | eval_qa_module_vs_silver |
| held-out test(修复后) | **0.829**, refute P=1.0 | eval_test_honest |
| 17真实违例 | **16/17 (94.1%)**, 演进52.9→94.1 | eval_violations |
| 级联(含L3仲裁旁路) | refute F1 0.800 @18%成本 | eval_cascade |
| 跨文档泛化(诚实局限) | 06号det 0.152 vs 04号0.638 | eval_crossdoc |
| dev-on-test偏差 | +0.0145 (2%) | 冻结切分29簇 |

---

## 8. 已知边界(诚实声明)

1. **跨文档gap是结构性的**: L1正则按04号文法调优, 06号确定性层0.152——升级路线=正则→语义匹配(配置化已把迁移成本从改代码降到换json, 但配置本身仍需人工归纳)
2. **L1的confident-but-wrong不可下游修复**: C1残差原则的代价(跨文档的in-presence误support即此类)
3. **silver仍是唯一标签源**: gold人工标注工作台已就绪(108实例/525claim预标注)
4. **少数类统计功效**: S=6/R=8, 单条翻转±0.1 F1

---

*实现文件索引: L0=entity_detector/ner_lexicon | L1=rulepack/gjb_rule_engine/e1/sequence/id_join/enum_join/trace/coverage/numeric_z3/evidence_compiler | L2=egt_synthesis/nli_training/nli_residual | 层间=qa_module(answer_claims/claim_channels/eval_lib) | 配置=config/ner_lexicons + config/rulepacks | 设计文档=64号 | 结果总览=49号*
