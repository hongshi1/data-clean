# GJB 438C SRS一致性检测系统 — 架构设计

> 版本: 1.0
> 日期: 2026-07-24
> 状态: 设计中
> 依据: 128篇论文调研 + 5篇精读 + 3份GJB SRS数据分析

---

## 1. 系统概述

### 1.1 目标

对GJB 438C格式的SRS文档进行三层一致性检测：
- **语法层**: 文档结构/格式是否符合GJB 438C要求
- **语义层**: 文本↔表格、文本↔图片之间是否存在矛盾
- **逻辑层**: 文档中的约束在逻辑上能否同时满足

每条检测结果关联到具体GJB条款，输出带置信度的不一致报告。

### 1.2 设计约束

| 约束 | 说明 |
|---|---|
| 数据 | 3份GJB格式SRS (编译器/电池仿真/调度器)，中文 |
| 计算资源 | Mac M4 Pro, 无CUDA, Python 3.12 + 3.14 |
| API | GLM-5 (文本), Kimi-K2.6 (多模态) |
| 解析工具 | MinerU (已验证可用) |
| 求解器 | Z3 (Python API, pip安装) |
| 论文产出 | 论文初稿，需明确novelty |

### 1.3 核心架构

```
GJB 438C SRS (PDF)
        │
        ▼
   MinerU解析
        │
        ├── Markdown (章节树 + 正文)
        ├── JSON (版面结构)
        └── Images (图片文件)
        │
        ▼
┌───────────────────────────────────────────┐
│           三层一致性检测引擎                │
│                                           │
│  L1 语法层          L2 语义层     L3 逻辑层│
│  (LLM+GJB规则)    (LLM+VLM)    (LLM+Z3)  │
│       │              │              │     │
│  结构合规检查     文本↔表格矛盾   约束可满足性│
│  格式规范检查     文本↔图片矛盾   冲突解释   │
│       │              │              │     │
│       └──────────────┼──────────────┘     │
│                      ▼                    │
│            不一致报告生成器                 │
│     (GJB条款关联 + 置信度 + 定位)          │
└──────────────────────────┬────────────────┘
                           │
                           ▼
                    不一致报告 (JSON)
```

---

## 2. 知识库设计

### 2.1 知识库结构

知识库是三层检测的共同基础，分为三部分：

```
knowledge/
├── gjb_structure.json      # GJB 438C结构规则 (语法层用)
├── gjb_parameters.json     # 参数词典 (语义/逻辑层用)
└── gjb_format_rules.json   # 格式规则 (语法层用)
```

### 2.2 结构规则 (gjb_structure.json)

从GJB 438C附录J系统化提取，层次化组织：

```json
{
  "standard": "GJB 438C-2021",
  "target_doc_type": "SRS",
  "chapters": [
    {
      "number": "1",
      "title": "范围",
      "required": true,
      "sub_sections": [
        {
          "number": "1.1",
          "title": "标识",
          "required": true,
          "must_contain": ["标识号", "名称", "版本号", "发布号"]
        },
        {
          "number": "1.2",
          "title": "系统概述",
          "required": true,
          "must_contain": ["用途", "一般特性", "运行现场"]
        }
      ]
    },
    {
      "number": "3",
      "title": "需求",
      "required": true,
      "sub_sections": [
        {
          "number": "3.2",
          "title": "CSCI能力需求",
          "required": true,
          "constraint_hints": ["响应时间", "吞吐量", "精度", "容量", "优先级"]
        },
        {
          "number": "3.3",
          "title": "CSCI外部接口需求",
          "required": false,
          "constraint_hints": ["数据传送速率", "带宽", "协议"]
        }
      ]
    }
  ]
}
```

### 2.3 参数词典 (gjb_parameters.json)

从GJB 438C + 公开SRS数据自动+手工构建：

```json
{
  "parameters": [
    {
      "name_cn": "响应时间",
      "name_en": "response_time",
      "synonyms": ["反应时间", "应答时间", "延迟", "时延", "latency"],
      "unit": "ms",
      "value_range": {"min": 0.001, "max": 600},
      "gjb_clause": "附录J 3.2.X",
      "category": "performance"
    },
    {
      "name_cn": "周期",
      "name_en": "cycle_period",
      "synonyms": ["循环周期", "调度周期", "定时周期"],
      "unit": "ms",
      "value_range": {"min": 0.1, "max": 10000},
      "gjb_clause": "附录J 3.2.X",
      "category": "performance"
    }
  ]
}
```

---

## 3. L1 语法层检测

### 3.1 检测内容

| 检查项 | 说明 | GJB来源 |
|---|---|---|
| 章节完整性 | SRS是否有GJB要求的6个必需章节 | 附录J |
| 子章节完整性 | 每个章节是否有必需的子章节 | 附录J |
| 内容字段完整性 | 每个子章节是否包含必需的内容字段 | 附录J |
| 章节编号格式 | 是否使用X.Y.Z编号格式 | 4.3.7.2 |
| 需求标识符 | 每条需求是否有唯一标识符(REQ-X.Y.Z) | 附录J 3章 |
| 合格性方法 | 每条需求是否注明合格性方法 | 附录J 4章 |
| 可追踪性 | 是否有需求可追踪性章节 | 附录J 5章 |

### 3.2 方法

参考Okamoto(2025)的Peach模式，逐章节检查：

```
输入: SRS的MinerU Markdown + GJB结构规则
方法: 
  1. 从Markdown提取章节树 (标题层级)
  2. 对照GJB结构规则，检查必需章节是否存在
  3. 对每个存在的章节，检查必需内容字段
  4. 用LLM判断内容字段是否存在 (关键词匹配 + 语义判断)
输出: 缺失章节/字段列表，每条关联GJB条款
```

### 3.3 输入输出

```python
# 输入
srs_markdown = "## 1 范围\n## 1.1 标识\n本SRS适用于..."
gjb_rules = load_json("knowledge/gjb_structure.json")

# 输出
{
  "layer": "syntax",
  "issues": [
    {
      "type": "missing_chapter",
      "severity": "HIGH",
      "gjb_clause": "附录J 第4章",
      "description": "缺少必需章节: 4 合格性规定",
      "location": null
    },
    {
      "type": "missing_field",
      "severity": "MEDIUM", 
      "gjb_clause": "附录J 1.1",
      "description": "章节1.1标识缺少: 发布号",
      "location": {"section": "1.1", "line": 5}
    }
  ]
}
```

---

## 4. L2 语义层检测（核心）

### 4.1 文本↔表格矛盾检测

#### 4.1.1 流程

```
Step 1: 约束提取 (LLM)
  从正文提取所有参数约束: {参数名, 运算符, 数值, 单位, 位置}
  
Step 2: 表格解析
  从MinerU的HTML表格提取: {表头, 行数据, 表格位置}
  
Step 3: 实体链接
  将正文约束与表格行配对 (参数名同义词匹配)
  
Step 4: 矛盾判断
  对每对(正文值, 表格值)，用NLI或直接比较判断是否矛盾
  
Step 5: 报告
  输出矛盾对，含正文位置和表格位置
```

#### 4.1.2 约束提取 (LLM-based)

之前用正则只提取了39条约束（49/62文档为0）。改用LLM提取：

```python
prompt = """
从以下SRS文本中提取所有参数约束。
每个约束包含: 参数名, 运算符(≤/≥/=/</>), 数值, 单位, 原文句子

文本:
{srs_section_text}

输出JSON:
[
  {"param": "定时周期", "operator": "=", "value": 25, "unit": "ms", 
   "sentence": "定时周期（interval_ms，默认 25ms）", "line": 143}
]
"""
```

从调度器SRS的数据看，中文约束模式包括：
- "不超过±2ms" → {operator: "≤", value: 2, unit: "ms"}
- "默认 25ms" → {operator: "=", value: 25, unit: "ms"}
- "不超过50ms" → {operator: "≤", value: 50, unit: "ms"}
- "前10秒恒流10A" → {operator: "=", value: 10, unit: "A"}

#### 4.1.3 表格解析

MinerU已提取HTML表格。解析为结构化数据：

```python
# 从调度器SRS的合格性规定表
table = {
  "headers": ["需求名称", "唯一标识", "章节号", "合格性方法", "合格性级别"],
  "rows": [
    ["高精度定时器", "REQ-3.2.1", "3.2.1", "单元测试+精度测量", "关键"],
    ["时间漂移补偿", "REQ-3.2.2", "3.2.2", "长时间运行测试", "关键"],
  ]
}
```

#### 4.1.4 配对与矛盾判断

```python
# 正文约束: {param: "定时周期", value: 25, unit: "ms"}
# 表格行: 需求名称="高精度定时器", 标识="REQ-3.2.1"

# 配对: 通过章节号(3.2.1)和参数名(定时周期↔高精度定时器)关联
# 判断: 正文说25ms，表格中该需求是否提到不同值？
```

### 4.2 文本↔图片矛盾检测

#### 4.2.1 流程

```
Step 1: 图片引用解析
  从正文提取所有图片引用: "如图X所示" → {fig_id, 引用位置, 引用上下文}
  
Step 2: 图片定位
  MinerU已提取图片文件，通过图片顺序或标题匹配到引用
  
Step 3: 图片分类 (VLM)
  用Kimi-K2.6判断图片类型: 流程图/架构图/状态图/界面截图/数据图表
  
Step 4: 一致性判断 (VLM)
  将引用上下文(文字描述) + 图片 发给VLM
  VLM判断: 文字描述与图片内容是否一致?
  
Step 5: 报告
  输出不一致对，含文字位置和图片路径
```

#### 4.2.2 图片引用解析

```python
# 从Markdown提取图片引用
patterns = [
    r"如图(\d+)所示",
    r"图(\d+)[\s:：]",
    r"见图(\d+)",
    r"Figure (\d+)",
]
# 结果: [{fig_id: "3", context: "如图3所示，系统包含3个模块", line: 45}]
```

#### 4.2.3 VLM一致性判断

```python
prompt = """
判断以下文字描述与图片是否一致。

文字描述: "{text_description}"
图片: [VLM输入]

请回答:
1. 一致性判断: 一致 / 不一致 / 无法判断
2. 不一致之处: (如果不一致，描述具体矛盾)
3. 置信度: 0-1
"""
```

#### 4.2.4 图片类型适配

不同图片类型需要不同的检测策略：

| 图片类型 | 检测方法 | 参考论文 |
|---|---|---|
| 流程图/活动图 | 提取节点/边 → 与文字步骤对比 | FloCA图表示 |
| 状态图 | 提取状态/转移 → 与文字状态描述对比 | FloCA图表示 |
| 架构图 | VLM直接判断组件数量/名称是否匹配 | ChartVE思路 |
| 界面截图 | VLM判断界面元素与文字描述是否匹配 | Visual Entailment |
| 数据图表 | ChartVE思路: 图→表格→比较 | ChartVE |

---

## 5. L3 逻辑层检测

### 5.1 检测内容

检查文档中的约束在逻辑上能否同时满足。

```
示例:
  约束A: 定时周期 = 25ms
  约束B: 单循环执行时间 ≤ 5ms
  约束C: 补偿计算时间 ≤ 0.01ms
  约束D: 电流序列查询时间 ≤ 0.01ms
  
  逻辑检查: B+C+D = 5+0.01+0.01 = 5.02ms < 25ms ✓ (可满足)
  
  如果存在:
  约束E: 电池模型计算时间 ≤ 3ms
  约束F: 总执行时间 ≤ 2ms
  
  逻辑检查: E+F矛盾 (3 > 2) ✗ (不可满足)
```

### 5.2 方法 (LLM + Z3)

参考Chen(2025)的LLM→SMT架构，扩展到数值约束：

#### 5.2.1 流程

```
Step 1: 约束提取 (复用L2的LLM提取结果)
  从正文和表格提取所有数值约束
  
Step 2: 约束形式化 (LLM)
  LLM将自然语言约束转换为Z3表达式
  
Step 3: 可满足性检查 (Z3)
  Z3求解约束集合
  
Step 4: 冲突解释
  如果UNSAT: 提取unsat core，定位矛盾约束
```

#### 5.2.2 LLM约束形式化

```python
prompt = """
将以下SRS约束转换为Z3 Python表达式。

约束列表:
1. 定时周期 = 25ms
2. 单循环执行时间 ≤ 5ms (含电池模型计算)
3. 补偿计算时间 ≤ 0.01ms
4. 连续运行1000个周期后总时间误差 ≤ 50ms

Z3表达式:
```python
from z3 import *

# 变量定义
cycle_period = Real('cycle_period')
execution_time = Real('execution_time')
compensation_time = Real('compensation_time')
total_drift = Real('total_drift')

# 约束
constraints = [
    cycle_period == 25,
    execution_time <= 5,
    compensation_time <= 0.01,
    total_drift <= 50,
    # 隐含约束: 执行时间 < 周期 (否则超时)
    execution_time < cycle_period,
]
```
"""
```

#### 5.2.3 Z3求解与冲突解释

```python
solver = Solver()
for c in constraints:
    solver.add(c)

if solver.check() == unsat:
    # 提取冲突核心
    solver2 = Solver()
    for c in constraints:
        solver2.assert_and_track(c, str(c))
    solver2.check()
    unsat_core = solver2.unsat_core()
    # 报告哪些约束互相矛盾
```

---

## 6. 不一致报告格式

### 6.1 统一报告结构

```json
{
  "doc_id": "scheduler_srs",
  "check_date": "2026-07-24",
  "summary": {
    "total_issues": 15,
    "by_layer": {"syntax": 5, "semantic": 7, "logic": 3},
    "by_severity": {"HIGH": 8, "MEDIUM": 5, "LOW": 2}
  },
  "issues": [
    {
      "issue_id": "ISSUE-001",
      "layer": "syntax",
      "type": "missing_chapter",
      "severity": "HIGH",
      "gjb_clause": "附录J 第4章",
      "description": "缺少必需章节: 4 合格性规定",
      "confidence": 1.0,
      "location": {"section": null, "line": null}
    },
    {
      "issue_id": "ISSUE-006",
      "layer": "semantic",
      "type": "text_table_contradiction",
      "severity": "HIGH",
      "gjb_clause": "附录J 3.2.X",
      "description": "正文说定时周期=25ms, 表格中写30ms",
      "confidence": 0.95,
      "location": {
        "text": {"section": "3.2.1", "line": 143},
        "table": {"section": "4", "table_index": 2, "row": 1}
      }
    },
    {
      "issue_id": "ISSUE-013",
      "layer": "logic",
      "type": "constraint_unsatisfiable",
      "severity": "HIGH",
      "gjb_clause": "附录J 3.2.X",
      "description": "约束矛盾: 执行时间≤5ms 且 电池模型计算≤3ms 且 补偿≤0.01ms, 但总时间≤2ms",
      "confidence": 1.0,
      "location": {
        "constraints": [
          {"section": "3.2.4", "line": 191, "text": "单循环执行时间不超过5ms"},
          {"section": "3.2.1", "line": 147, "text": "单次定时误差不超过±2ms"}
        ]
      },
      "z3_result": "UNSAT",
      "unsat_core": ["execution_time <= 5", "total_time <= 2"]
    }
  ]
}
```

---

## 7. 评测设计

### 7.1 评测数据

| 数据集 | 用途 | 数量 |
|---|---|---|
| 3份公开GJB SRS | 开发+测试 | 3 |
| 合成GJB SRS | 扩充测试 | 5-10 (LLM生成, 植入已知不一致) |

### 7.2 评测指标

| 层 | 指标 | 说明 |
|---|---|---|
| 语法 | Precision, Recall, F1 | 章节/字段缺失检测的P/R/F1 |
| 语义 | Precision, Recall, F1 | 文本-表格/图片矛盾检测的P/R/F1 |
| 逻辑 | Precision, Recall | UNSAT检测的P/R (UNSAT即矛盾) |
| 整体 | 报告质量评分 | 人工评估: GJB条款关联准确性, 定位准确性 |

### 7.3 基线方法

| 层 | 基线 | 来源 |
|---|---|---|
| 语法 | 纯规则匹配 (正则+关键词) | 我们之前的实现 |
| 语义 | 纯NLI (SummaC) | 之前验证过的方法 |
| 逻辑 | 纯Z3 (正则提取参数) | 之前的实现 (全假阳性) |

---

## 8. 论文Novelty

### 8.1 核心贡献

1. **首个GJB 438C SRS一致性检测系统**: Google Scholar搜"GJB 438"返回0条结果，这是全新的研究领域
2. **文档内文本↔表格矛盾检测**: 现有工作(TabFact等)验证外部声明，无人做文档内部正文与表格的矛盾检测
3. **三层联合检测框架**: 首次整合语法+语义+逻辑三层检测到一个统一系统
4. **LLM+Z3混合逻辑检测**: 扩展Chen(2025)的字符串方法到数值约束，解决ReqV的手工形式化瓶颈

### 8.2 与现有工作的差异化

| 维度 | 现有工作 | 我们 |
|---|---|---|
| 标准 | ISO 29148 (Okamoto) | GJB 438C (中文军工) |
| 检测层 | 单层(语法或语义) | 三层联合 |
| 表格检测 | 外部声明验证(TabFact) | 文档内部正文↔表格 |
| 图片检测 | 数据图表(ChartVE) | SRS技术图(架构/流程/状态) |
| 逻辑检测 | 手工形式化(ReqV)或字符串(Chen) | LLM自动形式化+数值约束 |

---

## 9. 实现计划

### Phase 1: 知识库构建 (1周)
- 从GJB 438C OCR结果系统化提取结构规则
- 从3份公开SRS提取参数词典
- 构建格式规则库

### Phase 2: L1语法层 (1周)
- 实现章节树提取
- 实现GJB结构规则匹配
- 在3份SRS上测试

### Phase 3: L2语义层 (2周)
- 实现LLM约束提取
- 实现表格解析与配对
- 实现VLM图片一致性检测
- 在3份SRS上测试

### Phase 4: L3逻辑层 (1周)
- 实现LLM→Z3约束形式化
- 实现Z3求解与unsat core提取
- 在3份SRS上测试

### Phase 5: 集成与评测 (1周)
- 三层联合检测
- 生成统一报告
- 人工评估

### Phase 6: 论文撰写 (2周)
- 方法描述
- 实验结果
- 案例分析
- 相关工作对比

**总计: ~8周**
