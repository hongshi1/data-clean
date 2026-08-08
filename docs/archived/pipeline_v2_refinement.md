# Pipeline v2 细化设计方案

## 一、当前问题诊断

### 问题1: same_version对过多(1954对→应~50对)
- **根因**: 正则提取版本号太宽泛，"V5"和"V10"是不同Windows版本被当冲突
- **格式差异**: 58条是V4.0.2 vs 4.0.2(归一化后相同，不是冲突)
- **跨软件误匹配**: Windows V5 vs Windows V10 是不同版本不是冲突
- **修复**: 版本号归一化 + 只在同一软件版本归一化后不同时才生成对

### 问题2: version_conflict违规过多(1262条→应~20条)
- **根因**: 同上，格式差异+跨版本误匹配
- **修复**: 版本归一化函数 normalize_version("V7.6")="7.6"

### 问题3: text_table对无关联(623对→应~100对)
- **根因**: 同章节正文与每个表格行都配对
- **修复**: 只配对正文和表格行有共同需求ID/章节号的

### 问题4: param_value_conflict可能误报(8条)
- **根因**: 不同用例(1.8.2.1 vs 1.8.5.1.1)的不同要求被当冲突
- **修复**: 只对同章节或相邻章节的同参数配对

### 问题5: 缺失关联对类型
- **缺失**: table_table(合格性表↔追溯表同一需求)
- **缺失**: section_hierarchy(3.2概述↔3.2.X子节功能分解)

## 二、方向A细化 — 7+2类关联对

### 2.1 same_param (细化)
```
当前: 同参数名在不同章节 → 配对
细化:
  1. 只对threshold角色生成"需检测"对(config/capacity可不同)
  2. 只对不同章节(非同章节内)配对
  3. 参数名提取改进: 取约束前最近的2-8个中文字(不是前15字)
  4. Embedding补充: 同义参数名(响应时间~延迟)也配对
```

### 2.2 same_version (细化)
```
当前: 同软件名在不同章节 → 配对(1954对)
细化:
  1. 版本号归一化: normalize("V7.6")="7.6", normalize("V4.0.2")="4.0.2"
  2. 只在归一化后版本不同时才生成关联对(相同不配对)
  3. 排除跨大版本误匹配: "V5" vs "V10"如果是同一软件的不同版本不报
     → 只比较同一软件名在同一文档中的版本
预期: 1954对 → ~50对
```

### 2.3 text_table (细化)
```
当前: 同章节正文与每个表格行 → 配对(623对)
细化:
  1. 只对qualification/traceability表的行配对
  2. 正文与表格行有共同需求ID时才配对
  3. 或正文与表格行有共同章节号引用时才配对
预期: 623对 → ~100对
```

### 2.4 image_text (保持)
```
当前: 图片与所在章节文字 → 配对(355对)
保持不变: 这是合理的, 图片的上下文就是所在章节
```

### 2.5 req_id_ref (保持)
```
当前: 同需求ID在正文和表格 → 配对(223对)
保持不变: 这是精确匹配, 质量高
```

### 2.6 cross_section (细化)
```
当前: 3.12每段与3.2.X每段 → 配对(65对)
细化:
  1. 只配对有共同关键词的段落(如"忙等待"在3.4.1和3.12都出现)
  2. 用embedding做语义相似度, >0.7才配对
预期: 65对 → ~20对(更精准)
```

### 2.7 logic_constraint (细化)
```
当前: 同参数threshold约束两两 → 配对(16对)
细化:
  1. 同参数约束对(已有)
  2. 新增: "执行时间"类约束 + "总预算"类约束 → 串行约束对
     - 识别: param含"执行时间"/"分析时间" + param含"总"/"预算"/"不超过"
  3. 新增: 同章节内多个约束 → 章节内约束对
预期: 16对 → ~30对
```

### 2.8 新增: table_table
```
合格性表行 ↔ 追溯表行(同一需求ID)
  - 在qualification表和traceability表中搜索同一req_id
  - 配对: (qualification_row, traceability_row)
  - 检测: 两个表格中对同一需求的描述是否一致
```

### 2.9 新增: section_hierarchy
```
3.2概述 ↔ 3.2.X子节(功能分解一致性)
  - 3.2概述文字中提到的功能名称 ↔ 3.2.X子节标题
  - 配对: (3.2概述中提到的"服务开发支撑", 3.2.1标题"服务开发支撑")
  - 检测: 概述中承诺的功能是否都有对应子节(完整性)
  - 检测: 子节中的功能是否都在概述中提到(无多余)
```

## 三、方向B细化 — 三层检测

### 3.1 语法层 (已有, 微调)
```
7项GJB标准检测保持不变:
  R-001标识完整性 / R-002需求ID唯一 / R-003合格性方法
  R-004追溯完整性 / R-005章节结构 / R-006接口ID / R-007优先顺序

新增(可选):
  R-008引用文档完整性: 第2章引用的文档编号是否完整
```

### 3.2 语义层 (重点细化)

#### same_param对检测:
```python
# 只对threshold角色的对做值比较
# config/capacity角色的对不报(合理差异)
if pair.pair_type == "same_param":
    if source.role == "threshold" and target.role == "threshold":
        if source.value != target.value:
            # 检查是否同章节(同章节内不同值才是真矛盾)
            if source.section != target.section:
                report("参数值冲突")
```

#### same_version对检测:
```python
# 版本号归一化后比较
def normalize_version(v):
    v = v.lstrip("Vv")
    # 去尾部.0
    parts = v.split(".")
    while parts and parts[-1] == "0":
        parts.pop()
    return ".".join(parts)

if normalize(v1) != normalize(v2):
    report("版本冲突")
else:
    pass  # 归一化后相同, 不报
```

#### text_table对检测(待NLI):
```
输入: 正文描述 "支持最多1000个服务注册"
      表格行 "服务注册数量 | 500"
NLI判断: premise=正文, hypothesis=表格行
  → contradiction → 报冲突
  → entailment → 一致
  → neutral → 无法判断

Prompt设计:
  "判断以下两段描述是否矛盾:
   正文: {text}
   表格: {table_row}
   输出: contradiction/entailment/neutral"
```

#### cross_section对检测(待NLI):
```
输入: 3.4.1 "允许使用忙等待"
      3.12 "不使用忙等待"
NLI判断: 允许vs禁止 → contradiction

Prompt设计:
  "判断以下两条约束是否矛盾:
   约束A(来自{section_a}): {text_a}
   约束B(来自{section_b}): {text_b}
   如果A允许的行为被B禁止, 输出contradiction
   输出: contradiction/entailment/neutral"
```

#### image_text对检测(待VLM):
```
输入: 图片(接口图) + 文字描述 "系统有3个外部接口"
VLM判断: 图中显示几个接口? 是否与文字一致?

Prompt设计:
  "根据图片内容回答: 图中显示了多少个接口?
   文字描述说'系统有3个外部接口'。
   图片是否与文字描述一致? 输出: consistent/inconsistent"
```

### 3.3 逻辑层 (重点细化)

#### 单参数Z3(已有):
```python
# A≤5且A≥10 → UNSAT
solver = Solver()
solver.add(Real("A") <= 5)
solver.add(Real("A") >= 10)
if solver.check() == unsat:
    report("逻辑不可满足")
```

#### 串行约束之和(新增):
```python
# 识别串行关系: 同一3.2.X子节内的"执行时间"约束
# 3.2.1执行时间=5秒 + 3.2.2执行时间=5秒 + 3.2.3执行时间=5秒 = 15秒
# 3.11总预算=10秒
# 15 > 10 → UNSAT

# 识别"执行时间"类约束
exec_constraints = [c for c in constraints if any(kw in c["param"] for kw in ["执行时间","分析时间","计算时间"])]
# 识别"总预算"类约束
budget_constraints = [c for c in constraints if any(kw in c["param"] for kw in ["总","预算","不超过"]) and c["param"] != exec_constraints]

# Z3: Sum(exec_times) <= budget?
solver = Solver()
total = sum(RealVal(c["value"]) for c in exec_constraints)
budget = RealVal(budget_constraints[0]["value"])
solver.add(total > budget)  # 如果满足, 说明超预算
if solver.check() == sat:
    report("串行约束之和超过总预算")
```

#### 允许vs禁止(新增, 用NLI而非Z3):
```python
# 3.4.1 "允许忙等待" vs 3.12 "不使用忙等待"
# 这不是数值约束, 需要NLI判断
# 复用cross_section的NLI检测
```

## 四、全面性保证

### 4.1 关联对覆盖度检查

| 分布模式 | 关联对类型 | 状态 |
|---------|-----------|------|
| 文字↔文字(跨章节同参数) | same_param | ✅ |
| 文字↔文字(跨章节同版本) | same_version | ✅(需归一化) |
| 文字↔文字(3.12 vs 3.2.X) | cross_section | ✅(需精筛) |
| 文字↔表格(正文vs合格性表) | text_table | ✅(需精筛) |
| 文字↔图片 | image_text | ✅ |
| 表格↔表格(合格性表↔追溯表) | table_table | 🆕(新增) |
| 约束↔约束(同参数逻辑) | logic_constraint | ✅(需扩展) |
| 需求ID↔需求ID(正文↔表格) | req_id_ref | ✅ |
| 概述↔子节(功能分解) | section_hierarchy | 🆕(新增) |

### 4.2 检测覆盖度检查

| 层 | 检测内容 | 状态 |
|----|---------|------|
| 语法 | GJB标准7项(R-001~R-007) | ✅ |
| 语义-值比较 | same_param threshold值不一致 | ✅(需精筛) |
| 语义-版本比较 | same_version归一化后不一致 | ✅(需归一化) |
| 语义-NLI | text_table正文vs表格矛盾 | ⏳(待NLI实现) |
| 语义-NLI | cross_section允许vs禁止 | ⏳(待NLI实现) |
| 语义-VLM | image_text图文不一致 | ⏳(待VLM实现) |
| 语义-完整性 | section_hierarchy概述vs子节 | ⏳(待实现) |
| 逻辑-Z3 | 单参数约束可满足性 | ✅ |
| 逻辑-Z3 | 串行约束之和>总预算 | ⏳(待实现) |
| 逻辑-NLI | 允许vs禁止矛盾 | ⏳(待实现) |

### 4.3 质量保证措施

1. **版本归一化**: V7.6=7.6, V4.0.2=4.0.2 → 消除格式差异误报
2. **semantic_role过滤**: 只对threshold角色报值冲突(config/capacity不报)
3. **章节距离过滤**: 同章节内不配对, 只跨章节配对
4. **关键词关联**: text_table/cross_section只配对有共同关键词的
5. **Embedding精筛**: cross_section用embedding>0.7才配对
6. **归一化去重**: 同一参数在同一章节的多个约束只取一个

## 五、预期效果

| 指标 | 当前 | 细化后(预期) |
|------|------|------------|
| 关联对总数 | 4806 | ~800(精筛后) |
| same_version对 | 1954 | ~50(归一化+只配对不同) |
| text_table对 | 623 | ~100(只配对有需求ID关联的) |
| cross_section对 | 65 | ~20(embedding精筛) |
| version_conflict违规 | 1262 | ~20(归一化后) |
| param_value_conflict违规 | 8 | ~5(精筛后) |
| 总违规 | 1437 | ~200(精筛后) |
| 待NLI/VLM检测 | ~1000 | ~150(精筛后) |
