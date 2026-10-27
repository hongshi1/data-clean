# 17. UML不一致性检测器套件：图谓词落地与变异检测评测（P4）

> 日期: 2026-09-09 ｜ 对应§九形式化的检测侧落地 ｜ 代码: `tools/uml_detector_suite.py`
> 使命: 把"0.978评测是oracle自检"的循环论证变成**独立检测器**的真证据——UML/逻辑族图算法检测器 + mutation detection score

---

## 一、任务形式化

```
图事实   G_s = (V, E),  e = (a, b, r, arr_e, arr_b),  r ∈ 9种UML关系
声明     c = (a, b, r̂, d̂, k)  从「问题+答案断言段」解析
         k ∈ {relation, direction, nav, dep, impl, nodetype, label, cycle, lifecycle}
检测器   T_k: c × G_s → verdict,  矛盾即 T_k(c, G_s) = ⊥
融合     T = ⋃_k T_k（任一触发 → inconsistent）
引擎质量 score(k) = |detected ∩ op_k| / |op_k|（P4: 变异检测得分）
```

**非循环论证协议**（本评测的核心设计）：

| 项 | 规则 |
|---|---|
| 检测器输入 | 仅 question + answer的**断言段** |
| 标签泄漏防护 | 答案内嵌的「（实际：…）」纠正段**剥离**后才抽取声明 |
| 禁读元数据 | label / inject_type / uml_type / evidence.* 一律不进检测器 |
| 实体解析 | 问题「」引号实体 → 图节点（截断/换行归一 + 前10字≤1差异模糊匹配，容源文档错字如"跟据"） |
| 边级宽容规则 | doc级同名实体对的多候选边：**任一候选支持声明即不触发**（防跨结构歧义误报） |

## 二、检测器套件（9个图谓词）

| 检测器 | 判定逻辑 | 可判理论 |
|--------|---------|---------|
| D_type | 声明关系r̂ ∉ {候选边uml_type}（含DIRECTED-on-arrowed-ASSOCIATION特例） | 一阶图谓词 |
| D_dir | 声明方向d̂ vs 可导航方向（end/begin_arrow∈NAV集合）；全候选无向+方向声明→触发 | 图谓词 |
| D_impl | 「X实现了Y」→ 须存在X→Y可导航边 | 图谓词 |
| D_nav | 「A可访问B」→ 须A→B可导航 | 图谓词 |
| D_dep | 「A依赖B」→ 须依赖族(DEPENDENCY/INCLUDE/EXTEND)可导航边 | 图谓词 |
| D_nodetype | 声明节点类型 vs 节点type（类型词取自问题尾部，防实体名内嵌词） | 结构核验 |
| D_label | 声明条件 vs 邻接边标注（归一化包含匹配） | 字符串核验 |
| D_cycle | 声明循环依赖(A→B且B→A) vs 有向边存在性 | 图谓词 |
| D_lifecycle | 「可独立存在」vs 组合关系(COMPOSITION寿命语义) | UML语义 |

声明抽取为模板语法敏感的模式匹配（9种声明种类判定优先级链 + 关系/方向/依赖/类型的文本模式）。

## 三、评测设置

- 语料: `uml_qa_full.json` 11,930条（正6,227/负5,703，12种注入算子族，easy 4,339/medium 4,354/hard 3,237）
- 图证据: `anchors_v3.json`（born-digital Visio直读: 373结构/5,165节点/2,557边）
- 双定位设置: **doc级**（真实场景: 实体检索doc全部图） vs **embed限定**（RAG定位上界）
- 基线: B0全consistent / B1答案句极性
- 统计: bootstrap 1000次95% CI（seed=42）；消融: 单检测器×8 + 局部性
- 仲裁协议: 对每个FN核验图事实是否支持声明 → 区分真漏检 vs 语料标签噪声

## 四、结果

### 4.1 主结果

| 设置 | P | R | F1 | CI95 | 特异度 |
|------|---|---|----|------|--------|
| doc级（无检索oracle） | 0.9887 | 0.9842 | **0.9865** | [0.9844, 0.9886] | 0.9897 |
| embed限定（RAG定位） | — | — | **0.9913** | — | 0.9961 |
| **仲裁修正**（89条标签噪声改判） | 0.9889 | 0.9998 | **0.9943** | — | — |
| 基线B0/B1 | — | 0 | 0.0 | — | — |

### 4.2 P4变异检测得分（按注入算子族, doc级 / embed限定）

| 算子族 | n | doc级 | embed | 说明 |
|--------|---|------|-------|------|
| relationship_type_confusion | 1,545 | 1.000 | 1.000 | D_type |
| dependency_fabrication | 1,545 | 1.000 | 1.000 | D_dep |
| realization_vs_generalization | 79 | 1.000 | 1.000 | D_type |
| navigation_error | 26 | 1.000 | 1.000 | D_nav |
| circular_dependency | 22 | 1.000 | 1.000 | D_cycle |
| composition_vs_aggregation | 10 | 1.000 | 1.000 | D_type |
| lifecycle_error | 10 | 1.000 | 1.000 | D_lifecycle |
| condition_swap | 77 | 0.987 | 1.000 | D_label |
| usecase_vs_state | 437 | 0.979 | 1.000 | D_nodetype |
| actor_vs_component | 302 | 0.990 | 1.000 | D_nodetype |
| direction_reversal | 105 | 0.905 | 0.905 | D_impl（10条双双向边，图事实不可判） |
| direction_fabrication | 1,545 | 0.957 | 0.958 | **67条为语料标签噪声（见4.4）** |

### 4.3 消融

- **局部性gap**: embed限定 − doc级 = +0.0048 F1（检索定位的价值）
- **单检测器F1**: D_type 0.446 / D_dep 0.426 / D_dir 0.417 / D_nodetype 0.225 / 其余<0.03 —— 任一单检测器都不足以覆盖12族，**融合是必要的**（各检测器分管自己的声明种类）

### 4.4 关键发现：检测器发现语料标签噪声（89条）

仲裁显示90个FN中89个**图事实支持声明而语料标为inconsistent**：

| 归因 | n | 根因 |
|------|---|------|
| graph_supports_direction | 67 | direction_fabrication模板按uml_type=ASSOCIATION当"无方向"生成负例，但**未检查begin_arrow**——真值边的箭头事实支持被"捏造"的方向声明 |
| graph_bidirectional | 10 | 判定分支节点间存在双向边，"X实现Y"声明图上成立（模板以为反向） |
| node_type_ambiguous | 12 | doc内存在同名文本节点其类型恰为声明类型（doc级检索歧义，embed限定下全检出） |

**含义**：①P1"标签零噪声"声明需修正为"oracle确证的标签仍需图事实仲裁"——本套件即仲裁器；②67条的根源是uml_type分类与箭头事实在锚点层的**不一致**（ASSOCIATION带filled_triangle begin箭头），提示锚点层的关系分类规则需修正或uml_type需信任箭头；③这本身是论文可写的发现（受控合成的标签噪声 + 确定性检测器的仲裁价值）。

### 4.5 残余错误

- FP 64/6,227（特异度0.9897）: 主要是label_positive的条件文本与边标注的表述差（如「上传」vs 边标注变体）
- 真漏检1条（condition_swap）
- 局限（如实声明）: ①声明抽取是模板语法敏感的，新表述形态需LLM分支（对应52项中llm-mode项）；②doc级检索歧义 inherent（2,389次多候选事件）；③评测语料为模板生成，措辞多样性有限

## 五、与既有体系的关系

| 项 | 状态变化 |
|----|---------|
| UML-01(关联方向)/UML-02(实现方向)/UML-03(组合聚合)/UML-06(多模态UML一致) | **auto检测器已落地**（D_dir/D_impl/D_type/D_nav） |
| P4(变异检测得分) | **已落地**：12算子族逐族得分表 |
| 0.978评测的循环论证问题 | **已解决**: 本评测中检测器与注入器完全独立（文本声明 vs 图事实） |
| Slide 3检测架构的"图算法引擎"分支 | 分支C统计之外新增UML图谓词分支的实测证据 |

## 六、复现

```bash
python tools/uml_detector_suite.py --ablation   # 全量11,930条 + 消融 + 仲裁 (~40s)
# 输出: data/gjb_438c/anchor_v3/uml_detection_eval.json
```

## 七、后续（优先级）

1. 修正direction_fabrication生成器：ASSOCIATION选边时排除带箭头者（或信任箭头重判uml_type）→ 语料修复后重跑
2. 把仲裁器接入合成流水线（P1的升级版: oracle确证 + 图事实仲裁双门）
3. LLM分支声明抽取（自然表述泛化）→ 覆盖UML-05/08（llm-mode项）
4. 环/拓扑序/分支覆盖三个图不变量检测器（LOGIC族流程图QA侧）
