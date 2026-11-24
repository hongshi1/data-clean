# 统一行动方案：可解释性↑ · 性能↑ · 正则↓

> 三份调研（95/96/97）+代码库审计（98）的最终合成。回答原始问题：
> "如何提升本地一致性校验的可解释性和性能，减少嵌入代码的正则"。

## 总路线图（四阶段，测量先行）

```
Phase 0 测量基建（半天-2天, 零训练）
  └→ E1 span忠实率ALCE口径 + E2 消融翻转率上violations-17
        ↓ 有了尺子才能验证后面每一步
Phase 1 对齐修复+输出可靠性（1-2周, 零/低训练）
  └→ P1 claim→typed通道桥接（SAE）+切分器接入
  └→ X1 D3输出端约束解码（JSON schema+copy约束）
Phase 2 蒸馏重训（一次训练, 三收益合并）
  └→ P2+X2 教师解释结构一致化+多reward蒸馏复训D3
        （= 已锁定的1638条叙事化重训, 加上96号协议改进）
Phase 3 范式升级（各半天-一周, 可并行）
  └→ R2 identifier接地概率化（B类切口①）
  └→ P3 Eiter回路试点（rulepack从失败例归纳）
  └→ R1 A类正则退役（依赖Phase 2）
  └→ E7 claim_channels表驱动外置（纯工程, 随时可做）
远期（论文级消融）
  └→ E6 ReaComp DSL程序蒸馏对照 + U4跨域混合分解
```

## 核心答案的三句话

1. **性能**：瓶颈不在分解器在对齐——先修claim→typed通道桥接
   （SRE→SAE），切分器的识别优势（0.70 vs 0.24）才能变现为下游
   增益；否则0.7496<0.8047重现（95号Alignment Bottleneck定律）。

2. **可解释性**：D3学生做**结构化解释的组装者而非作者**——
   格式层用约束解码保证（XGrammar/Outlines消0.6B-4B结构失败），
   span逐字层用copy约束保证（2610.28393），理由层靠教师蒸馏+质量
   闸门（FLamE警示：蒸馏解释提准确率但不构成判定理由，须三reward
   把关）。HART四阶段协议与我们的字段协议同构，**missing_condition
   是文献空位=我们的差异点**。

3. **正则**：分层迁移不是全替代——A类语义判定（12.3%决策型）
   交给D3学生退役；B类代数本体零学习但三切口（接地概率化/弃权
   学习/GBDT阈值）；D类词典FLAT化+规则Eiter回路化。**verdict的
   确定性下限永远由符号层保底**（numeric_z3 refute精确率1.000）。

## 详细任务表（合并98号实验路线+96号E1-E7）

| 阶段 | 任务 | 成本 | 直接来源 | 验收标准 |
|------|------|------|---------|---------|
| 0 | **E1** span忠实率改ALCE口径（citation precision/recall，gold=17条人工block定位） | 半天 | 96号§5 | 评测脚本进tests/快照 |
| 0 | **E2** 消融翻转率+反事实四条件上violations-17（68变体自动构造，扰动算子表驱动化） | 1-2天 | 96号FAE/EviScope | 每条violation有翻转率数字 |
| 1 | **P1** claim→typed通道桥接：切分器claim接typed字段接口+证据侧SAE对齐，然后`decomposer="distilled"`接入qa_module | 1-2天 | 95号+98号#1 | 下游macro-F1≥0.8047（正则typed基线） |
| 1 | **X1** D3输出端约束解码：JSON schema（XGrammar/Outlines）+difference_type枚举trie约束+span字段copy约束或后验对齐 | 2-3天 | 96号E4 | 结构失败率→0；span忠实率不降 |
| 2 | **P2+X2** 教师解释结构一致化+多reward蒸馏复训D3：统一字段模板；忠实/真实/有用三reward；EGT加最小变更对；教师标签重生成走缓存 | 一周内（含过夜训练） | 96号E5+项目既定1638条重训 | 联合评分（准确+忠实）；FLamE闸门过 |
| 3 | **R2** identifier接地概率化：在场→绑定概率（PL-Guard式renormalized分数） | 阈值校准 | 97号§2.4 | C06QA-016/017修复 |
| 3 | **P3** Eiter回路试点：教师从06号30条crossdoc失败例归纳rulepack变体，与人工doc06_v1.json对比 | 半天 | 97号§3.4 | 归纳规则≥人工规则的表现 |
| 3 | **R1** A类正则退役：D3学生输出含否定/引用/主语槽位，替换_NEGATIVE/_QUOTED/主语提取 | 依赖Phase 2 | 98号#4 | A类退役清单+回归全绿 |
| 3 | **E7** claim_channels规则表驱动外置：规则→JSON数据+通用执行器 | 纯工程 | 96号E7 | MANIFEST保护+快照 |
| 远 | **E6** ReaComp DSL程序蒸馏对照（论文消融） | 远期 | 96号§6 | 程序产物vs权重蒸馏对比 |
| 远 | **U4** 跨域混合分解（GLiNER零样本+切分器） | 需验证 | 97号§1.2 | 跨文档零配置可用 |

## 训练数据构造备选（95号§7.3，供Phase 2扩容）

- **MiniCheck幂集增广**：零API成本，claim子集→verdict标签传播；
- **SYNTHVERIFY NEI模糊化**：NIE边界样本（我们missing_condition
  差异点的配套数据）；
- **FISCAL误归属模块**：right- detail-wrong-entity类（identifier
  接地概率化的训练数据）。

## 论文叙事框架（三调研合并后的统一故事）

**主张**：GJB军事SRS一致性校验的正确架构=**分层迁移**：
蒸馏模型管语义判定（claim分解/否定/实体），符号层管确定性数学
（区间/单位/编号），学习管两者之间的信任权重。

**三个文献同构+域先例空位**：
- PL-Guard（接地/策略分离）→我们的L0词典+L1规则
- TRACK（模型调度数学工具95% vs 纯编码器58%）→我们的模型+Z3
- Eiter系（LLM归纳规则+求解器验证）→我们的教师→rulepack→L1
- **均无GJB/SRS域先例**

**差异化贡献点**：
1. missing_condition字段（开放世界三态，文献错误类型学空位，
   2509.22582证明NIE边界恰是公认失败模式）
2. SAE对齐修复（把Alignment Bottleneck定律从解释变成方法）
3. violations-17免标注评测套件（citation P/R+消融翻转+反事实
   四条件+根因准确率）
4. identifier接地概率化（"在场即support"信任假设跨域失效无文献
   先例——95/97两调研独立指出）

## 已锁定的既定动作（不变）

- D3叙事化重训命令（1638条，过夜）——升级为Phase 2的P2+X2合并版
  （在重训前先做教师解释结构一致化，避免二次重训）

## 实验结果附录（2026-11-24，Phase 0/1落地后更新）

### Phase 0（Agent A，M122）：✅ 完成

E1/E2基线全部锁定（详见runs/eval_span_faithfulness_61449821与
eval_ablation_flip_de9cd555）。六项系统弱点入册，最重要的是：
- ~~两通道claim_text合成断言→43%字面不忠实损失~~（已修复，见下方
  "E1字面忠实修复"条目——**基线刷新至0.8696**）
- D3学生copy精度0/4（quote逐字但区间全错）
- 引用欠覆盖（enum判定依赖未引用块）

### E1字面忠实修复（E1弱点#1，2026-11-24）：✅ 完成——基线刷新

e1_template_match/trace_bidirectional_join两通道的文档侧违例（主题
错位/正逆矛盾/锚点失效/同行矛盾）claim_text原为合成断言（拼接文本），
answer侧完全不可定位。修复（algorithms/consistency/answer_anchor.py）：
claim_text锚定answer逐字引用——违例标识词元（用例名/E1提示文本/追踪
章节号）在answer中的最小覆盖span，字面契约answer[span]==text；原合成
断言移入rationale（解释信息不丢弃）；verdict/method/confidence/
evidence_refs全部不动（判定逻辑零变更）。

**验收（三步，tools/verify_e1_fix_acceptance.py对照两个run）**：
- 修复前基线复现：字面忠实 **13/23=0.5652**
- 修复后（**基线刷新**，Phase 2 Step 4验收以此为准）：
  **20/23=0.8696**（runs/eval_span_faithfulness_add8863a_20261124_163132）
  citation P/R（macro 0.8021/0.8792/0.8275, micro 0.7297/0.7941）、
  根因any-hit 12/16、锚点重叠29/37全部逐位不变
- 判定无回归：violations-17检出16/17逐位不变
  （runs/eval_violations_664fe616_20261124_163147，summary全字段
  一致）；91QA deterministic 0.9121/0.7212逐位不变
  （result.json全字段+per_row全行一致；91QA集零文档侧e1/trace触发）

**残余3/23字面损失（诚实口径）**：VIO-10-trace02/VIO-11-trace01/
VIO-12-trace01——文档内违例（表81 row20同行矛盾/3.2.4正逆矛盾）的
违例章节号在answer中零提及，answer侧无关联文本可锚定。根因=这三项
文档侧检查本身不依赖answer（纯文档内缺陷检测），answer只覆盖查询的
目标行；除非强行把定位锚到无关answer片段（造假），不可逐字锚定。


### P1桥接（Agent B，M123）：❌ 未达标 + 重大科学发现

**验收结果**：macro-F1≥0.8047 **未达标**（0.7496，与裸切分器完全
一致——桥接仅抽出3条typed claim，SAE机制无对象可对齐）；识别F1
0.6975达标。三臂基线逐位复现（sanity全过）。

**两层粒度契约**（Alignment Bottleneck定律的精确化，可发表）：
claim必须同时满足两层才产生下游增益——
1. **字段层**：claim文本须覆盖typed通道可验证的字段文本（ID/
   数值/枚举的原文span）。实证：5个含ID实例的identifier span
   覆盖率=0.0（教师原子claim=叙事粒度，typed字段全在切分器O区
   ——识别F1的胜利区域与typed字段区域不相交）；
2. **命题层**：语义单元须为NLI可判定的完整命题。实证：S1QA-006
   的句级claim全部被NLI entail（support），原子claim全部
   semantic_unresolved（NIE一票否决）——**NLI能entail整句、
   不能entail原子**。

**路线修正**：识别F1≥0.60（原子）与下游≥0.8047（typed+句级）
在本语料互斥，修复不在claim集构造在**训练目标**——Phase 2成为
关键路径：教师标签需含字段claim+完整命题单元（切分器重训侧），
D3叙事化重训（学生侧）承载判定能力。E7/R2照常（与B结论正交）。

**意外收益**：桥接版推理快10×（25.0s vs 252.7s，原子跳过NLI
premise配对）——若Phase 2重训后识别优势变现，时延优势保留。
