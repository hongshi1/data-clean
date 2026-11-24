# 实验效度发现：pack切换的进程内缓存污染（Eiter试点中期报告）

> 来源：Agent C（Eiter回路试点）中期报告，2026-11-24。
> 完整实验仍在运行，此为已确证的发现记录。

## 发现1：lru_cache身份盲污染（主仓库bug）

`algorithms/consistency/numeric_z3_expert.py` 的 `_unit_table` 使用
`@lru_cache(maxsize=1)` **但没有pack身份键**；`gjb_presence_expert`
的vocab正则同样身份盲。

**后果**：同一进程内切换rulepack（eval_crossdoc5_onboard式流程）时，
第二个pack**继承第一个pack的派生配置**（单位表/vocab正则未随pack
重建）——历史"换pack无差异"的结论部分是缓存污染伪影。

**规避**（Agent C的Eiter管线已采用）：每个pack评测用全新子进程。
**主修复**（排队中，等Agent B交付后执行——B的评测在用这些专家，
不能中途改代码）：给`_unit_table`的缓存键加pack identity（如pack
文件内容的hash）；gjb_presence_expert同样处理。

## 发现2：doc06_v1陈旧性

`config/rulepacks/doc06_v1.json` 是M33时代的fork，**缺失**srs_gjb_v1
后来新增的numeric_z3/coverage/gjb部分。独立运行时在crossdoc06上
**退化**：macro-F1 0.1481（doc06_v1）vs 0.2619（通用srs_gjb_v1）。

**推论**：历史"doc06_v1与通用pack无差异"的记录部分由发现1的
缓存污染掩盖——干净子进程下差异显著。

## 影响

1. **历史数字复查**：所有进程内多pack对比实验需要标注污染风险
   （论文实验效度部分）
2. **Eiter回路的对比基线**：教师归纳的rulepack变体应与**修复缓存
   后**的干净基线对比，而非历史数字
3. **待办**：主仓库修复（lru_cache键+vocab重建）——排在Agent B
   （P1桥接，正在用专家评测）交付之后，避免中途改码污染其数字

## 教师调用契约（实证修复）

GLM-5.3思维模式会在max_tokens内耗尽token：必须传
`response_contract: json_final_content_v2, reasoning_effort: low`
（仓库现有教师调用者的做法）。已同步给Agent D。
