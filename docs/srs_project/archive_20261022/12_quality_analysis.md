# 12. SRS评测集质量分析报告

> 日期: 2026-08-19
> 分析对象: `data/gjb_438c/data_assets/srs_qa_v3/eval_set.json`（162条）
> 多LLM标注: `data/gjb_438c/data_assets/srs_qa_v3/multi_llm_annotations.json`（3个LLM独立标注）
> 检测器评测: `data/gjb_438c/data_assets/srs_qa_v3/eval_results.json`

---

## 一、评测集概览

| 维度 | 数值 |
|------|------|
| 总条目 | 162条 |
| 正例（consistent） | 50条 |
| 负例（inconsistent） | 112条 |
| gold层（Z3+规则验证） | 100条 |
| silver层（双LLM验证） | 62条 |
| 双LLM验证通过 | 131/162（80.9%） |
| Z3形式化验证 | 3条（P4操作符矛盾） |
| 注入方法数 | 25种 + positive对照 |
| 覆盖校验项 | 16个（TERM-001/002/003/008, PARAM-001/002/003, LOGIC-001/002/003, GJB-001/002/003/004/005） |

---

## 二、多LLM标注结果

### 2.1 各LLM独立标注准确率

3个LLM在不提供注入信息的情况下，独立判断每条QA的occurrences是否存在不一致：

| LLM | API endpoint | 标注数 | 准确率 | Precision | Recall | F1 |
|-----|-------------|:---:|:---:|:---:|:---:|:---:|
| **kimi** | moonshot直接 | 159 | **79.87%** | 0.9753 | 0.7248 | **0.8316** |
| glm | wanqing(kimi模型) | 147 | 78.91% | 0.9583 | 0.7113 | 0.8166 |
| claude | wanqing | 161 | 65.84% | **1.0000** | 0.5045 | 0.6707 |
| 多数投票 | - | 161 | 79.50% | - | - | - |

**关键发现**：
- kimi最均衡（F1=0.83），准确率和召回率都好
- claude最保守（P=1.0但R=0.5），只检测确定的不一致，不冒险
- 多数投票准确率79.5%，说明评测集不是trivial的（不是100%）

### 2.2 LLM间Cohen's κ

| LLM对 | κ值 | 一致性程度 |
|-------|:---:|:---:|
| kimi vs glm | 0.7790 | 高度一致 |
| claude vs glm | 0.6163 | 中等一致 |
| kimi vs claude | 0.5748 | 中等一致 |
| **平均** | **0.6567** | **中等一致** |

### 2.3 三人一致性

| 指标 | 数值 |
|------|:---:|
| 三人全一致 | 109/162（67.28%） |
| 三人全一致且与gold一致 | 88/109（80.73%） |
| 三人有分歧 | 53/162（32.72%） |

**32.7%的条目三人有分歧**——说明评测集有区分度，不是所有case都trivial。

---

## 三、按注入方法的质量评级

### 3.1 评级标准

| 评级 | 标准 | 含义 |
|------|------|------|
| **A级（优秀）** | majority准确率≥80% 且 三人一致率≥60% | 注入有效，LLM能可靠检测 |
| **B级（良好）** | majority准确率≥60% 或 三人一致率≥40% | 注入有效，LLM能部分检测 |
| **C级（需改进）** | majority准确率<60% 且 三人一致率<40% | 注入方式有问题 |
| **D级（无效）** | majority准确率=0% | 注入完全不可见 |

### 3.2 评级结果

| 评级 | 方法数 | 条数 | 占比 | 代表方法 |
|------|:---:|:---:|:---:|------|
| **A级** | 8种 | 82条 | 50.6% | T3/T5/T6/T8, L1/L4/L5, G1/G5, positive |
| **B级** | 14种 | 61条 | 37.7% | T1/T2, L2/L3/L6, G2/G3/G4, P1/P2/P4/P6 |
| **C级** | 2种 | 9条 | 5.6% | G6_placeholder, G7_num_gap |
| **D级** | 2种 | 10条 | 6.2% | T4_multiname, P3_attr_swap |

**A+B级覆盖88.3%的条目**——评测集整体质量可用。

### 3.3 逐方法详细统计

#### 术语层（T1-T9）

| 方法 | 条数 | kimi | claude | glm | majority | 三人一致 | 评级 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| T1_char_replace | 5 | 5/5 | 4/5 | 3/5 | 5/5 | 3/5 | B |
| T2_truncate | 5 | 5/5 | 4/5 | 5/5 | 5/5 | 4/5 | A |
| T3_char_swap | 5 | 5/5 | 5/5 | 3/5 | 5/5 | 3/5 | A |
| T4_multiname | 5 | 0/5 | 0/5 | 0/5 | 0/5 | 5/5 | **D** |
| T5_synonym | 2 | 2/2 | 2/2 | 1/2 | 2/2 | 1/2 | A |
| T6_abbreviation | 5 | 5/5 | 3/5 | 4/5 | 5/5 | 3/5 | A |
| T8_enum_missing | 5 | 5/5 | 2/5 | 5/5 | 5/5 | 3/5 | A |

**术语层分析**：
- T1/T2/T3（字符级操作）有效——LLM能看到字符差异
- T5/T6/T8（同义词/缩写/枚举缺失）有效——语义差异可见
- **T4（多名）完全无效**——injected与original完全相同，occurrences中无差异

#### 参数层（P1-P6）

| 方法 | 条数 | kimi | claude | glm | majority | 三人一致 | 评级 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| P1_value_double | 3 | 1/3 | 2/3 | 2/3 | 2/3 | 1/3 | B |
| P2_unit_replace | 2 | 1/2 | 1/2 | 1/2 | 1/2 | 1/2 | B |
| P3_attr_swap | 5 | 1/5 | 0/5 | 0/5 | 0/5 | 4/5 | **D** |
| P4_operator_conflict | 3 | 1/3 | 1/3 | 2/3 | 2/3 | 1/3 | B |
| P6_precision | 3 | 2/3 | 1/3 | 1/3 | 1/3 | 1/3 | B |

**参数层分析**：
- P1/P2/P4/P6有效但准确率偏低——数值差异在occurrences中不够明显
- **P3（属性交换）完全无效**——每条只有1个occurrence，无参照对象
- P4（操作符矛盾）有Z3验证，但LLM看不到运算符差异

#### 逻辑层（L1-L6）

| 方法 | 条数 | kimi | claude | glm | majority | 三人一致 | 评级 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| L1_step_swap | 5 | 5/5 | 2/5 | 3/5 | 4/5 | 2/5 | A |
| L2_dangling_exception | 5 | 5/5 | 3/5 | 4/5 | 5/5 | 3/5 | B |
| L3_func_missing | 5 | 5/5 | 3/5 | 4/5 | 4/5 | 3/5 | B |
| L4_precondition | 5 | 4/5 | 2/5 | 4/5 | 4/5 | 2/5 | A |
| L5_dead_exception | 5 | 5/5 | 2/5 | 4/5 | 4/5 | 2/5 | A |
| L6_sequence_reverse | 5 | 5/5 | 3/5 | 3/5 | 4/5 | 3/5 | B |

**逻辑层分析**：
- **6种方法全部A/B级**——逻辑层注入质量最好
- kimi在逻辑层表现最好（几乎全部5/5）
- claude在逻辑层偏保守（2-3/5）
- 步骤交换/异常流悬挂/功能缺失/前置条件冲突/死异常流/序列反转都有效

#### GJB合规层（G1-G7）

| 方法 | 条数 | kimi | claude | glm | majority | 三人一致 | 评级 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| G1_field_missing | 5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | A |
| G2_section_missing | 5 | 5/5 | 4/5 | 5/5 | 5/5 | 4/5 | A |
| G3_ref_missing | 5 | 3/5 | 1/5 | 3/5 | 3/5 | 1/5 | B |
| G4_trace_broken | 5 | 2/5 | 1/5 | 2/5 | 1/5 | 1/5 | B |
| G5_qual_missing | 5 | 5/5 | 2/5 | 4/5 | 4/5 | 2/5 | A |
| G6_placeholder | 5 | 1/5 | 0/5 | 2/5 | 1/5 | 1/5 | **C** |
| G7_num_gap | 4 | 0/4 | 0/4 | 1/4 | 1/4 | 0/4 | **C** |

**GJB层分析**：
- G1/G2/G5有效——字段缺失/章节缺失/合格性缺失在occurrences中可见
- G3/G4部分有效——引用缺失/追溯断裂在occurrences中不够明显
- **G6/G7无效**——占位符和编号跳变未出现在occurrences的content中

#### 正例对照（positive）

| 方法 | 条数 | kimi | claude | glm | majority | 三人一致 | 评级 |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| positive | 50 | 48/50 | 50/50 | 47/50 | 48/50 | 47/50 | A |

**正例分析**：
- claude在正例上表现最好（50/50，零误报）
- kimi有2条误报，glm有3条误报
- 正例质量可靠

---

## 四、无效注入方法的根因分析

### 4.1 D级方法（完全无效）

#### T4_multiname（同名异义）

**现象**：5条全部0/3 LLM检出，majority准确率=0%

**根因**：injected与original**完全相同**

```
injection.original = "服务程序调试"
injection.injected = "服务程序调试"  ← 完全相同！
injection.detail = "same name assigned to different IDs"
```

occurrences中所有位置的content都是"服务程序调试"，LLM看到的是完全一致的文本，正确判断为consistent。T4的意图是制造"同名异义"（同一名称对应不同entity_id），但entity_id未呈现给LLM，occurrences只暴露content字段。

**改进方向**：T4应在occurrences中至少一处显示不同名称，或显式呈现entity_id冲突。例如：
- 位置1: [table] entity_id=PZXQ-A, content="服务程序调试", definition="软件服务调试功能"
- 位置2: [text] entity_id=PZXQ-B, content="服务程序调试", definition="硬件诊断调试功能"

#### P3_attr_swap（属性交换）

**现象**：5条全部0/3 LLM检出（majority），4/5三人一致判断consistent

**根因**：每条只有1个occurrence，无参照对象

```
entity.occurrences = [
  {"location": "table", "content": {"sender": "传输控制模块", "receiver": "文件传输通道模块"}}
]
```

LLM的判定逻辑是"多位置对比"，单位置无法对比。注入改变了occurrence内部的sender/receiver，但缺少原始方向的参照。

**改进方向**：P3应至少有2个occurrence，一个保留原始方向，一个写入交换后的方向：
- 位置1: [table] sender=A, receiver=B（原始）
- 位置2: [text] sender=B, receiver=A（注入交换）

### 4.2 C级方法（需改进）

#### G6_placeholder（占位符未替换）

**现象**：5条中只有1条被majority检出，准确率20%

**根因**：注入点与occurrences呈现点错位

```
injection.original = "数据获取模块"
injection.injected = "XXX待定"
injection.inject_location = "text"
entity.entity_type = "table_header"  ← 表头字段，不是正文！
entity.occurrences[0].content = ["序号", "Use case名称", "项目唯一标识符", ...]  ← 表头列名
```

"数据获取模块"和"XXX待定"在任何occurrence中都不出现。注入作用于text位置的占位符文本，但occurrences抽取的是表格表头。

**改进方向**：G6的entity_type应改为text/module_name，occurrences应包含正文段落，其中一处将"数据获取模块"替换为"XXX待定"。

#### G7_num_gap（编号不连续）

**现象**：4条中只有1条被majority检出，准确率25%

**根因**：与G6同类问题——章节编号跳变未反映在occurrences的content中

```
injection.original = "3.7→3.8→3.9"
injection.injected = "3.7→3.9(缺3.8)"
injection.inject_location = "document"
entity.occurrences[0].content = ["序号", "需求标识符", ...]  ← 表头列名，无章节号
```

**改进方向**：G7的occurrences应包含章节号序列，如["1范围", "2引用文件", "3要求", "5交付", "6说明"]（缺第4章）。

### 4.3 PARAM-001中准确率为0的条目

条目0032/0042/0047的3个LLM全部判断consistent，但gold label是inconsistent。

**根因**：注入值未回写到occurrences

```
# 条目0032 (P1_value_double)
injection.original = "50.0"
injection.injected = "100.0"
occurrences = [
  {"content": "50"},  ← 原始值，未替换为"100.0"
  {"content": "50"},
  {"content": "50"},
  {"content": "50"}
]
```

4个occurrence全部显示"50"，LLM看到的是一致的数据。

**改进方向**：注入后必须将injected值回写到至少一个occurrence的content中。

---

## 五、gold/silver分层质量差异

| 层 | 条数 | kimi准确率 | claude准确率 | glm准确率 | majority准确率 |
|----|:---:|:---:|:---:|:---:|:---:|
| gold | 100 | 71.0% | 71.0% | 78.0% | 74.0% |
| silver | 62 | 90.3% | 56.5% | 61.3% | 87.1% |

**反直觉发现**：silver层（LLM验证）的majority准确率（87.1%）**高于**gold层（74.0%）。

**原因**：
- silver层多为术语/逻辑类（T*/L*），注入的语义差异明显且呈现在occurrences content中
- gold层含G6/G7/P3等呈现层不可见的结构性注入，拉低了准确率
- kimi在silver层达90.3%，说明LLM构建的条目对LLM友好

**启示**：gold/silver分层不应仅按"验证方式"分，还应考虑"注入可见性"。

---

## 六、规则检测器 vs LLM标注的差异

| 方法 | 规则检测器F1 | LLM majority准确率 | 差异分析 |
|------|:---:|:---:|------|
| T4_multiname | 0.00 | 0% | 一致：都未检出 |
| P3_attr_swap | 1.00 | 0% | **矛盾**：规则检测器比对injection元数据，LLM只看occurrences |
| G6_placeholder | 1.00 | 20% | **矛盾**：规则检测器比对injection，LLM看occurrences |
| G4_trace_broken | 1.00 | 20% | **矛盾**：同上 |
| T1_char_replace | 1.00 | 100% | 一致：都正确检出 |

**关键发现**：规则检测器对P3/G6/G4报告F1=1.0，但LLM准确率接近0。这是因为规则检测器在比对injection元数据（original≠injected→检出），而LLM只看occurrences content（内容一致→未检出）。

**这说明**：当前的规则检测器存在"元数据泄漏"问题——它不是在检测occurrences中的不一致，而是在比对injection字段。这是一个需要修复的设计缺陷。

---

## 七、总体质量评价

### 7.1 优点

1. **88.3%的条目由有效方法生成**——A+B级覆盖143/162条
2. **逻辑层质量最好**——6种方法全部A/B级
3. **术语层字符操作有效**——T1/T2/T3/T5/T6/T8都有效
4. **正例对照组可靠**——50条中48条零误报
5. **Z3形式化验证可用**——3条P4操作符矛盾数学证明
6. **双LLM验证80.9%通过**——kimi+claude交叉验证

### 7.2 问题

1. **4种方法（19条）注入不可见**——T4/P3/G6/G7的注入未回写到occurrences
2. **规则检测器有元数据泄漏**——比对injection而非occurrences
3. **数值参数太少**（3个）——参数层样本不足
4. **T7/T9/L7-L10未实现**——6种注入方法缺失
5. **人工标注缺失**——审稿风险

### 7.3 改进建议

| 优先级 | 改进项 | 影响 | 工作量 |
|:---:|------|------|:---:|
| P0 | 修复T4/P3/G6/G7的occurrences回写 | 消除19条无效数据 | 0.5天 |
| P0 | 修复规则检测器的元数据泄漏 | 检测器F1更真实 | 0.5天 |
| P1 | 补充数值参数（从chunks提取） | 参数层样本+30条 | 0.5天 |
| P1 | 补T7/T9注入 | 覆盖+10条 | 0.5天 |
| P1 | 补L7-L10注入（用流程图VLM） | 覆盖+20条 | 1天 |
| P2 | 人工标注200条+κ | 审稿必须 | 待资源 |

### 7.4 结论

**评测集整体质量可用**：
- 88.3%的条目由有效注入方法生成
- 多LLM标注验证了评测集有区分度（不是trivial的）
- Cohen's κ=0.57-0.78（中等至高度一致）
- gold/silver分层合理

**主要质量问题是4种方法的"注入不可见"缺陷**，根因是注入逻辑只写injection元数据、未回写occurrences。修复后预计A+B级覆盖率可从88.3%提升到95%+。

---

## 附录：数据文件索引

| 文件 | 说明 |
|------|------|
| `eval_set.json` | 162条评测集（完整QA+注入信息+验证结果） |
| `eval_set.jsonl` | 同上（逐行JSON，用于增量写入） |
| `eval_results.json` | 规则检测器评测结果（P/R/F1） |
| `multi_llm_annotations.json` | 3LLM独立标注结果（含κ统计） |
| `multi_llm_progress.jsonl` | 标注进度文件（逐条写入） |
| `eval_entities.json` | 1128个检测对象 |
| `eval_injected.json` | 163条注入结果 |
| `vlm_flowchart_extract.jsonl` | 163张流程图VLM提取 |
