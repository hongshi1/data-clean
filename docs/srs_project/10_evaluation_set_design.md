# 10. SRS不一致检测评测集设计方案

> 日期: 2026-08-19
> 状态: 实施中
> 前置: 09_qa_synthesis_design.md + dataset_synthesis_design.md

## 1. 目标

为路线一检测器构建可信评测集，验证"检测器能检出25项A类跨位置不一致性"。

**规模**: ~280条（250条合成 + 31条真实矛盾），质量优先。

## 2. 数据源（已验证）

| 数据 | 路径 | 规模 | 质量 |
|------|------|------|------|
| Pair Dataset | `data/gjb_438c/pair_dataset/` | 366个pair | sc1最好(141条),sc2最差(90条) |
| 用例图VLM | `vlm_usecase_extract.jsonl` | 136条 | 全量覆盖16份文档 |
| 流程图VLM | 待生成 | 140张 | kimi-k2.6提取nodes/edges/branches |
| 图片分类 | `srs_image_analyses.json` | 379条 | figure_type+key_elements |
| chunks | `srs_chunks.json` | 5231条 | 16份文档结构化切片 |
| 专家词典 | `knowledge/srs_kb.json` | 11参数 | 全部HIGH可信度 |
| GJB规则 | `knowledge/gjb_438c_rules_full.json` | 120条 | 逐条对标标准原文 |
| 不一致规则 | `knowledge/inconsistency_rules.json` | 14条 | 全部HIGH可信度 |

**可靠数据源**: sc1(141)+sc3(30)+sc4(49)+sc5(27) = 247个pair

## 3. 25项A类校验清单

从40项校验中筛选25项"跨位置/跨模态不一致性"（A类），排除15项"单位置内容质量"（B类）。

| 层 | 项数 | 校验项 | 注入方法 | 检测方法 | 置信度 |
|---|:---:|---|---|---|:---:|
| 术语 | 8 | ①同义异名 ②同名异义 ③枚举集合 ④状态告警 ⑤指令名称 ⑥量纲单位 ⑦信号接口 ⑧缩写代号 | T1-T9(9种) | 编辑距离/集合比较/词典匹配 | silver |
| 参数 | 10 | ①时间约束 ②周期 ③阈值 ④融合对齐 ⑤资源占用 ⑥值域 ⑦存储时长 ⑧守时精度 ⑨降级阈值 ⑩故障时长 | P1-P6(6种) | Z3求解器/数值归一化 | gold |
| 逻辑 | 6 | ①模式切换 ②异常处置 ③事件时序 ④数据流 ⑤工况分支 ⑥权限控制 | L1-L10(10种) | LCS/VLM提取对比/Z3 | gold/silver |
| GJB | 1 | ⑤需求可追溯性 | G1-G7(7种) | ID-Graph/规则检查 | gold |

## 4. 32种注入方法

### 术语注入（9种）
| 方法 | 操作 | 示例 |
|------|------|------|
| T1错字 | 第N字固定映射替换 | 数据获取→**发**据获取 |
| T2截断 | 去首字 | 数据获取→据获取 |
| T3字序 | 前两字交换 | 数据获取→**据数**获取 |
| T4多名 | 两不同ID赋同名 | ID-A→数据获取, ID-B→数据获取 |
| T5同义词 | 同义词替换 | 数据获取→数据**采集** |
| T6缩写 | 全称换缩写 | 结构化数据归集→**SDDC** |
| T7中英混用 | 中文换英文 | 数据获取→**DataAcquisition** |
| T8枚举缺失 | 删减模式集合 | {手动,自动,应急}→{手动,自动} |
| T9告警术语 | 同状态换术语 | "通信异常告警"→"链路故障标志" |

### 参数注入（6种，P4/P5需Z3 gate）
| 方法 | 操作 | Z3 gate |
|------|------|:---:|
| P1数值翻倍 | val×2 | ❌ |
| P2单位替换 | 换单位不换算 | ❌ |
| P3属性交换 | 接收方/类型互换 | ❌ |
| P4操作符矛盾 | ≤vs≥ | ✅ |
| P5值域越界 | 超出词典范围 | ✅ |
| P6精度不一致 | ≈vs= | ❌ |

### 逻辑注入（10种）
| 方法 | 操作 | 需流程图VLM |
|------|------|:---:|
| L1步骤交换 | 相邻步骤交换 | ❌(用text) |
| L2异常流悬挂 | 引用不存在E编号 | ❌ |
| L3功能缺失 | 删功能名 | ❌ |
| L4前置条件冲突 | 改前置条件 | ❌ |
| L5死异常流 | 定义未被引用 | ❌ |
| L6时序矛盾 | 时序冲突 | ❌ |
| L7数据流反转 | 方向反转 | ✅ |
| L8分支删除 | 删降级分支 | ✅ |
| L9模式切换冲突 | 优先级矛盾 | ✅ |
| L10权限矛盾 | 权限放宽 | ✅ |

### GJB合规注入（7种）
G1字段缺失/G2章节缺失/G3图表引用缺失/G4追溯链断裂/G5合格性方法缺失/G6占位符未替换/G7编号不连续

## 5. 四段式流水线

```
阶段1: 检测对象提取（确定性）
  输入: Pair Dataset + VLM提取 + chunks
  提取: 5类检测对象（功能名/接口属性/数值参数/流程步骤/表头字段）
  聚合: 跨pair同一实体聚合
  输出: ~200个检测对象

阶段2: 规则注入（确定性，seed=42）
  输入: 检测对象 + 32种注入方法
  执行: 每种方法确定性操作
  Z3 gate: P4/P5验证unsat
  输出: 注入后对象

阶段3: LLM改写（只改语言不改结论）
  输入: 注入后对象
  执行: kimi将结构化数据改写为自然语言QA
  输出: 自然语言question+answer

阶段4: 分层验证
  逻辑层 → Z3 solver验证unsat = gold
  语法层 → 规则确定性验证 = gold
  语义层 → kimi+claude双LLM交叉验证 = silver
```

## 6. Z3 gate（真正调用Solver）

```python
from z3 import Real, Solver, unsat

def z3_gate(param_name, constraints_original, constraints_injected):
    s = Solver()
    x = Real(param_name)
    for op, val in constraints_original + constraints_injected:
        if op == "ge":   s.add(x >= val)
        elif op == "le": s.add(x <= val)
        elif op == "gt": s.add(x > val)
        elif op == "lt": s.add(x < val)
        elif op == "eq": s.add(x == val)
    return s.check() == unsat
```

## 7. 双LLM验证（两个不同endpoint）

| LLM | URL | KEY | Model |
|-----|-----|-----|-------|
| kimi | `https://api.moonshot.cn/v1/chat/completions` | `sk-7QY7...` | kimi-k2.6 |
| claude | `https://wanqing-api.corp.kuaishou.com/...` | `WQ_API_KEY` | ep-5zazxj-... |

复用`cove_verifier.py`的CoVe范式: kimi起草→claude隔离验证→合并判定。

## 8. 循环验证解决方案

注入侧（14条不一致规则+32种确定性操作）和检测侧（120条GJB规则+Z3+LLM）使用**完全不同的算法**:
- 注入: 字符串/数值/序列的确定性修改
- 检测: 编辑距离/Z3求解/LCS/图遍历

9条术语/参数/逻辑规则是120条GJB规则之外的专家知识，天然独立。

## 9. 评测集格式

```json
{
  "eval_id": "EVAL-TERM-001-001",
  "check_item": "TERM-001",
  "label": "inconsistent",
  "doc": "01数据获取转换分系统",
  "pair_id": "1_001",
  "entity": {
    "entity_id": "PZXQ-GN-SJHQ-...",
    "entity_type": "function_name",
    "occurrences": [
      {"location": "table", "section": "3.2", "content": "结构化数据归集"},
      {"location": "text", "section": "3.2.1.2", "content": "结构化数据归集"},
      {"location": "image", "section": "3.2.1.2", "content": "结构化数据归集"}
    ]
  },
  "injection": {
    "method": "T1_char_replace",
    "original": "结构化数据归集",
    "injected": "结及化数据归集",
    "inject_location": "table",
    "seed": 42,
    "detail": "pos=1, 构→及"
  },
  "question": "...",
  "answer": "inconsistent",
  "answer_reason": "...",
  "confidence": "silver",
  "verified_by": ["kimi", "claude"],
  "difficulty": "easy"
}
```

## 10. 评测集规模

| 类别 | 校验项 | 正例 | 负例 | 合计 | 置信度 |
|------|:---:|:---:|:---:|:---:|:---:|
| 术语 | 8 | 40 | 40 | 80 | silver |
| 参数 | 10 | 50 | 50 | 100 | gold(Z3) |
| 逻辑 | 6 | 30 | 30 | 60 | gold/silver |
| GJB | 1 | 5 | 5 | 10 | gold |
| 合计 | 25 | 125 | 125 | 250 | - |

## 11. 评测协议

- 检测器×评测集交叉运行
- P/R/F1分层报告: 总体 + 按四类 + 按置信度
- 基线: 字符串精确匹配 + 纯LLM检测

## 12. API配置（已验证）

| API | URL | 状态 |
|-----|-----|:---:|
| kimi via moonshot | `https://api.moonshot.cn/v1/chat/completions` | ✅ |
| claude via wanqing旧URL | `https://wanqing-api.corp.kuaishou.com/...` | ✅ |
| 流程图VLM(kimi) | moonshot + `thinking:disabled` + `response_format:json_object` | ✅ |
