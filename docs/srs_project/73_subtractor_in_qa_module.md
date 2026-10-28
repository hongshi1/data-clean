# 73 减法模块接入一致性校验管线：方法、基线对比与图表1

日期：2026-10-28 | 实现：`qa_module.py`的`use_subtractor`分支 | 图：`fig73_qa_module.png`

---

## 一、方法详解（接入真实一致性校验系统）

### 1.1 被接入的系统

`QAConsistencyModule.verify(QAInput) → 三态裁决(support/refute/not_in_evidence)`

```text
question + answer + 证据块
   → [证据过滤层]           ← 减法模块的接入点(与deq同一槽位)
   → linearize_evidence     ← 管线自带的表格类型感知行级化
        (能力表/数据表/接口表/用例表分别解析)
   → L1专家通道(entity/E1模板/序列对齐/id_join/枚举join/Z3/覆盖)
   → L2 NLI残差通道(未决claim进mDeBERTa)
   → 三态聚合
```

### 1.2 减法模块（`evidence_subtractor.py`，本工作）

```text
F1 作用域: 锚点匹配(PZXQ式ID/英文词/中文4-gram, 大小写不敏感)
           删与问题/答案无共享锚点的干扰证据块
           + ID豁免: 标识符类检测项的含ID证据不删(多实体比对必需)
F2 粒度:   表格→"表头：值"行语句, 长文→句切(独立NLI场景用)
F3 形态:   无锚点命中的纯指针("见表X所示")删除
护栏:      删光回退; 每次删除带{stage, reason_code}审计记录
```

### 1.3 集成方式（两次迭代的教训）

```text
第一次(错误): 删块+把证据文本重写为行语句
  → 违例查全0.94→0.41崩塌: 重写破坏了linearize_evidence的
    表格类型检测("标识符+需求描述"等模式失配), 专家通道失效
  → 但假refute从14→1(refute精确率0.583→0.875)
第二次(修正): 只删块不改写(max_statements=∞关闭语句预算)
  → 粒度归一交给管线自己的类型感知linearize(它比我通用的F2更领域化)
  → 安全但本数据上无增益(见下)
```

---

## 二、基线对比（同一NLI/同一阈值/同一标签，只换证据过滤层）

### 2.1 评测设置

```text
评测集: 108实例 = 91冻结QA(silver标签, GLM-5.3复核, 非人工gold)
                  + 17真实违例(设计gold=refute, 源文档已块级验证)
配置: RAW(无过滤) / DEQ(现有E0+E1软管线) / SUBTRACTOR(本文F1+F3删除)
NLI: mDeBERTa本地, 双阈值0.6(模块默认)
```

### 2.2 主结果（提纯率 × 精度保持框架）

| 配置 | 块提纯率 | 语句提纯率 | accuracy | macro-F1 | 违例refute查全 |
|---|---:|---:|---:|---:|---:|
| RAW(不过滤基线) | 0%(664块) | 0%(9214语句) | 0.7685 | 0.6203 | 0.9412 |
| **DEQ(现有E0门)** | **-17.8%**(删118块) | -5.7% | **0.7685** | **0.6203** | **0.9412** |
| SUBTRACTOR(本文F1+F3) | -10.8%(删72块) | -2.1% | 0.7593 | 0.6111 | 0.8824 |

**图表1**：`docs/srs_project/fig73_qa_module.png`
（提纯率条形图×精度保持标注，RAW=不过滤基线）

```text
提纯模块的判据 = 删掉的证据量 × 精度不降:
  DEQ:      删17.8%块, 三项指标全部不变  ← 无损提纯(本数据上的优胜者)
  SUBTRACTOR: 删10.8%块, acc-0.9pt/违例-1 ← 删得更少反而删到了needed块
```

---

## 三、四个诚实结论

### 结论1：RAW基线已经很强——专家通道+类型感知linearize解决了粒度问题

71号独立实验的+29.4pt增益来自"NLI直入原始表格HTML"的失败模式；
而真实管线里`linearize_evidence`已做表格类型感知行级化+L1专家
(id_join确定性比对ID)——**粒度问题在系统层面已被处理**。

### 结论2（修正）：DEQ的E0门是无损提纯器——删17.8%块,判决零变化

DEQ在50/108实例上共删118块, 三项指标与RAW逐位相同。
**现有管线已经是一个安全提纯模块**；此前"DEQ零拒绝"的说法有误
(误读了诊断计数字段), 本节为修正版。

### 结论3：本文减法模块在精选池上删到needed块——提纯指标上输给DEQ

F1+F3删10.8%但造成acc-0.9pt/违例-1: 删除准则(锚点+指针)是为
"NLI直判"场景设计的, 对专家通道所需的枚举/比对证据过于激进。
**在提纯率×精度保持的判据下, 现有DEQ优于本文实现**。

### 结论4：减法模块的增益条件=真实噪声召回池（评测集构造局限）

```text
71号(独立NLI直判):     +29.4pt查全  — 坏证据直入NLI时减法有效
73号(完整管线,精选池):  -0.9pt     — 管线已解决粒度+DEQ已做无损提纯
→ 下一步: 用O1-unit真实召回top-50(含真实干扰块)重跑本对比,
  在真噪声下比较DEQ vs SUBTRACTOR的提纯率×精度保持
```

---

## 四、产物

| 资产 | 位置 |
|---|---|
| 集成 | `algorithms/consistency/qa_module.py` `use_subtractor`参数 |
| 模块 | `algorithms/consistency/evidence_subtractor.py`(7回归测试) |
| 实验 | `tools/eval_subtractor_qa.py` |
| **图表1** | `docs/srs_project/fig73_qa_module.png` |
| 结果 | `data/gjb_438c/localization_gold/subtractor_qa_eval_v1.json` |

局限：91QA为silver标签；违例17条全为refute类；证据池为冻结邻域块
而非真实召回输出(结论3的原因)。
