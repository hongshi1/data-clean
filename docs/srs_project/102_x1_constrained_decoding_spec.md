# X1实施规格：D3输出端约束解码（自研LogitsProcessor，零新依赖）

> 99号方案Phase 1的X1。基于2026-11-24对D3推理路径的实证检查。
> 前置：Agent A的E1评测完成（正在收尾）——E1用的是当前无约束推理，
> 中途改码会污染其数字。

## 实证依据（已验证的三个事实）

1. **结构失败被静默掩盖成NIE**：`tools/eval_d3_student.py:133` 无效
   verdict默认`"not_in_evidence"`——JSON解析失败与真实NIE判定混淆。
   `_parse`的三级抢救（strip think→fenced提取→raw_decode扫描）说明
   结构失败是常态而非异常。
2. **NIE塌缩的量化**：d3_student_eval_v1.json test46——student预测
   **100% NIE**（support/refute P/R/F全零，acc 0.8043全靠NIE多数类
   承载）；violations17仅3/17 refute正确（confusion：7个refute被预测
   为support、7个为NIE）。n_issues=3（17条里只产3条定位）。
3. **依赖约束**：环境只有transformers 5.17+torch 2.11（无outlines/
   xgrammar/vllm）→ 必须自研`LogitsProcessor`（trie式约束），
   零新依赖，符合96号§4"约束解码消除0.6B-4B结构失败"（2609.23742）。

## 设计

### 新模块 algorithms/consistency/d3_constrained.py

**约束FSM（trie）分三层：**

1. **verdict枚举trie**：生成`"verdict": "`后强制三值
   `support|refute|not_in_evidence`——从源头消除无效verdict
   （不再有"默认NIE"这个失败模式）
2. **JSON骨架约束**：`{"verdict": <enum>, "issues": [<issue>...]}`
   骨架的token级trie（issue对象的五字段quote/span/rule_id/
   evidence_ref/explanation按schema约束key名与类型）
3. **span/quote后验对齐**（不做token级copy trie——复杂度过高，
   96号允许后验对齐）：生成完成后机械校验quote⊂answer（字面）、
   span区间在answer范围内、evidence_ref索引有效——不合格的issue
   降级为诊断（不删除，标`span_verified: false`），**不再默认NIE**

**接口：**
```python
def constrained_generate(model, tokenizer, prompt: str,
                         answer: str, evidences: list[str],
                         max_new_tokens: int = 512) -> dict
```
返回`{verdict, issues, parse_fail: bool, constraint_log}`——
**parse_fail成为一等公民指标**（X1前后对比的核心数字）。

### 集成点（三处judge/adapter统一）

- `tools/eval_d3_student.py:judge`（主评测路径）
- `tools/eval_d3_ensemble.py`（集成评测路径）
- `tools/eval_span_faithfulness.py --d3-adapter`（E1用的adapter——
  Agent A交付后确认其结构再接线）

集成方式：新模块+各脚本可选开关`--constrained`（默认off保持
向后兼容，论文数字不动；X1评测显式开启）。

### 验收

| 指标 | X1前（当前） | X1后目标 |
|------|-------------|---------|
| parse_fail率 | 未计量（被NIE掩盖）→ **先加计量再约束** | **0** |
| verdict无效→默认NIE | 存在 | 消除（三值trie强制） |
| violations17 refute | 3/17（v1）/ 4/17（v2b，E1） | 结构性下限抬升（真实refute不再被解析失败吞掉） |
| n_issues产出 | 3/17 | 骨架约束下issues字段必产（可为空数组但结构在） |
| span忠实率 | E1最终数字 | 后验对齐≥E1基线 |

**重要**：X1只保证**输出结构可靠性**，不直接提升语义准确率——
语义提升靠Phase 2重训。X1的价值=消除NIE混杂+让结构失败可计量+
为重训提供可靠的verdict分布（重训后才能看到真实的三类分布）。

## 执行顺序

1. **等Agent A的E1完成**（正在收尾）+ 交付验证
2. Step A：给现有judge加parse_fail计量（半跑量基线，不改行为）
3. Step B：实现d3_constrained.py + tests（trie FSM的确定性快照）
4. Step C：`--constrained`开关接入三处，跑X1前后对比
5. ruff零报错 + pytest全绿 + 现有无约束路径完全不变
