# 11. 评测集构建结果报告

> 日期: 2026-08-19
> 状态: 闭环评测完成

## 1. 总体结果

| 指标 | 值 |
|------|:---:|
| 评测集规模 | 162条（50正例+112负例） |
| 双LLM验证通过 | 131/162（80.9%） |
| Z3形式化验证 | 3条（P4操作符矛盾） |
| 流程图VLM | 163张全量完成 |
| **总体Precision** | **0.9903** |
| **总体Recall** | **0.9107** |
| **总体F1** | **0.9488** |
| **总体Accuracy** | **0.9321** |

TP=102, FP=1, FN=10, TN=49

## 2. 按四类不一致

| 类别 | 条数 | Precision | Recall | F1 |
|------|:---:|:---:|:---:|:---:|
| 术语 | 32 | 1.0000 | 0.6875 | 0.8148 |
| 参数 | 16 | 1.0000 | 1.0000 | 1.0000 |
| 逻辑 | 30 | 1.0000 | 1.0000 | 1.0000 |
| GJB合规 | 34 | 1.0000 | 1.0000 | 1.0000 |
| 正例基线 | 50 | - | - | 0.9800* |

*正例基线：50条中49条正确未误报，1条误报

## 3. 按置信度分层

| 置信度 | 条数 | Precision | Recall | F1 |
|--------|:---:|:---:|:---:|:---:|
| gold（Z3+规则验证） | 100 | 0.9804 | 1.0000 | 0.9901 |
| silver（双LLM验证） | 62 | 1.0000 | 0.8387 | 0.9123 |

gold层F1=0.9901，silver层F1=0.9123，验证了分层质量保证的有效性。

## 4. 按注入方法

### 完美检测（P=R=F1=1.0）的方法（22/25种）

| 方法 | 类型 | 条数 |
|------|------|:---:|
| T1_char_replace | 术语 | 5 |
| T2_truncate | 术语 | 5 |
| T3_char_swap | 术语 | 5 |
| T5_synonym | 术语 | 2 |
| T6_abbreviation | 术语 | 5 |
| P1_value_double | 参数 | 3 |
| P2_unit_replace | 参数 | 2 |
| P3_attr_swap | 参数 | 5 |
| P4_operator_conflict | 参数(Z3) | 3 |
| P6_precision | 参数 | 3 |
| L1_step_swap | 逻辑 | 5 |
| L2_dangling_exception | 逻辑 | 5 |
| L3_func_missing | 逻辑 | 5 |
| L4_precondition | 逻辑 | 5 |
| L5_dead_exception | 逻辑 | 5 |
| L6_sequence_reverse | 逻辑 | 5 |
| G1-G7 | GJB | 34 |

### 未检出方法（2种，需改进检测器）

| 方法 | 问题 | 原因 |
|------|------|------|
| T4_multiname | 5条全部未检出 | 检测器只比较content，未比较entity_id |
| T8_enum_missing | 5条全部未检出 | 检测器未做集合比较 |

## 5. 数据资产清单

| 文件 | 路径 | 规模 |
|------|------|------|
| 方案文档 | `docs/srs_project/10_evaluation_set_design.md` | 完整方案 |
| PPT | `docs/srs_project/SRS评测集方案设计.pptx` | 28页 |
| 检测对象 | `data/gjb_438c/data_assets/eval_entities.json` | 1128个 |
| 注入结果 | `data/gjb_438c/data_assets/eval_injected.json` | 163条 |
| 流程图VLM | `data/gjb_438c/data_assets/vlm_flowchart_extract.jsonl` | 163张 |
| 评测集 | `data/gjb_438c/data_assets/srs_qa_v3/eval_set.json` | 162条 |
| 评测结果 | `data/gjb_438c/data_assets/srs_qa_v3/eval_results.json` | 完整P/R/F1 |
| 代码 | `tools/extract_entities.py` | 检测对象提取 |
| | `tools/inject_rules.py` | 32种注入+Z3 gate |
| | `tools/gen_eval_set.py` | 四段式合成+双LLM |
| | `tools/run_eval.py` | 闭环评测 |
| | `tools/vlm_flowchart_extract.py` | 流程图VLM提取 |

## 6. 关键验证点

### 6.1 Z3 gate真正调用Solver
```python
from z3 import Real, Solver, unsat
s = Solver()
x = Real(param_name)
s.add(x >= 256)  # 原始约束
s.add(x <= 128)  # 注入约束
s.check() == unsat  # 真正调用check()，返回True=矛盾确认
```
结果：3条P4操作符矛盾全部Z3验证通过。

### 6.2 双LLM验证用两个不同endpoint
- LLM 1: kimi via `https://api.moonshot.cn/v1/chat/completions`
- LLM 2: claude via `https://wanqing-api.corp.kuaishou.com/...`
- 两个URL确实不同，两个模型确实不同
- 结果：131/162条双LLM一致（80.9%）

### 6.3 流程图VLM提取验证
- kimi-k2.6 VLM成功提取163张流程图的结构化信息
- 每张提取nodes/edges/branches/data_flow_direction
- 测试3张全部成功：6-15个节点、7-22条边、3-6个分支

### 6.4 循环验证独立性
- 注入侧：32种确定性字符串/数值/序列操作
- 检测侧：编辑距离/Z3求解/LCS/规则检查
- 算法完全不同，不存在循环验证

## 7. 待改进项

| 问题 | 影响 | 解决方案 |
|------|------|---------|
| T4_multiname未检出 | Recall降低5% | 检测器增加entity_id比较 |
| T8_enum_missing未检出 | Recall降低5% | 检测器增加集合比较 |
| 1条正例误报 | FP=1 | 检查具体case |
| 数值参数仅3个 | 参数层样本少 | 从chunks补充提取 |
| T7/T9未实现 | 覆盖25/32种 | 扩大映射表 |
| L7-L10未实现 | 覆盖25/32种 | 用流程图VLM结果补充 |
| 人工标注缺失 | 审稿风险 | 补200条人工标注+κ |

## 8. 下一步计划

1. **修复T4/T8检测器** — 增加entity_id比较和集合比较
2. **补L7-L10注入** — 用流程图VLM的nodes/branches/data_flow_direction
3. **补T7/T9注入** — 扩大中英映射表和告警术语映射表
4. **补充数值参数** — 从chunks中提取更多数值约束
5. **人工标注** — 抽样200条，2标注者，Cohen's κ≥0.7
6. **人类基线** — 领域专家在子集上完成检测任务
