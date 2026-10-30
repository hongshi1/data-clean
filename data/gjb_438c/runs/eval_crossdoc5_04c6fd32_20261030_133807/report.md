# 跨文档泛化评测 (自建-跨文档×5, 构造性sound标签)

- evalset: `C:\Users\12488\Desktop\data_clean\data\gjb_438c\qa_frozen\crossdoc5_evalset_v1.jsonl` (150行 = 5文档×30, S/R/N各50)
- label: **constructive_sound (label_proof; no LLM silver)** (label_proof逐条背书, 零LLM silver)
- bge_threshold: —: tools/public_baselines.py不存在, BGE嵌入阈值基线按任务口径跳过

## 分文档 × 分配置 macro-F1 矩阵

| doc | b3_deterministic | l2_egt_nli | ours_cascade | mdeberta_zeroshot | n |
|---|---|---|---|---|---|
| 05 | 0.4 | 0.4975 | 0.6388 | 0.5405 | 30 |
| 06 | 0.2619 | 0.4966 | 0.6052 | 0.4685 | 30 |
| 07 | 0.2624 | 0.4483 | 0.5185 | 0.4258 | 30 |
| 08 | 0.4 | 0.4625 | 0.6111 | 0.4408 | 30 |
| 10 | 0.2402 | 0.4258 | 0.6033 | 0.5934 | 30 |
| overall | 0.3169 | 0.4681 | 0.5971 | 0.4997 | 150 |

## b3_deterministic

- n=150 accuracy=0.3733 macro_f1=0.3169 llm_invocations=0 (api_calls=0)

| class | precision | recall | f1 |
|---|---|---|---|
| support | 0.3125 | 0.2 | 0.2439 |
| refute | 0.75 | 0.12 | 0.2069 |
| not_in_evidence | 0.3636 | 0.8 | 0.5 |

混淆矩阵 (pred|gold):
`{"support|support": 10, "support|refute": 13, "support|not_in_evidence": 9, "refute|support": 1, "refute|refute": 6, "refute|not_in_evidence": 1, "not_in_evidence|support": 39, "not_in_evidence|refute": 31, "not_in_evidence|not_in_evidence": 40}`

## l2_egt_nli

- n=150 accuracy=0.4733 macro_f1=0.4681 llm_invocations=0 (api_calls=0)

| class | precision | recall | f1 |
|---|---|---|---|
| support | 0.4878 | 0.4 | 0.4396 |
| refute | 0.4697 | 0.62 | 0.5345 |
| not_in_evidence | 0.4651 | 0.4 | 0.4301 |

混淆矩阵 (pred|gold):
`{"support|support": 20, "support|refute": 11, "support|not_in_evidence": 10, "refute|support": 15, "refute|refute": 31, "refute|not_in_evidence": 20, "not_in_evidence|support": 15, "not_in_evidence|refute": 8, "not_in_evidence|not_in_evidence": 20}`

## ours_cascade

- n=150 accuracy=0.5933 macro_f1=0.5971 llm_invocations=58 (api_calls=0)

| class | precision | recall | f1 |
|---|---|---|---|
| support | 0.4884 | 0.42 | 0.4516 |
| refute | 0.9118 | 0.62 | 0.7381 |
| not_in_evidence | 0.5068 | 0.74 | 0.6016 |

混淆矩阵 (pred|gold):
`{"support|support": 21, "support|refute": 11, "support|not_in_evidence": 11, "refute|support": 1, "refute|refute": 31, "refute|not_in_evidence": 2, "not_in_evidence|support": 28, "not_in_evidence|refute": 8, "not_in_evidence|not_in_evidence": 37}`

## mdeberta_zeroshot

- n=150 accuracy=0.5333 macro_f1=0.4997 llm_invocations=0 (api_calls=0)

| class | precision | recall | f1 |
|---|---|---|---|
| support | 0.4839 | 0.9 | 0.6294 |
| refute | 0.6667 | 0.24 | 0.3529 |
| not_in_evidence | 0.5897 | 0.46 | 0.5169 |

混淆矩阵 (pred|gold):
`{"support|support": 45, "support|refute": 25, "support|not_in_evidence": 23, "refute|support": 2, "refute|refute": 12, "refute|not_in_evidence": 4, "not_in_evidence|support": 3, "not_in_evidence|refute": 13, "not_in_evidence|not_in_evidence": 23}`

## 06号子集复现 (vs 旧eval_crossdoc单文档运行)

| config | 06子集 macro-F1 | 旧运行 macro-F1 | 复现 |
|---|---|---|---|
| b3_deterministic | 0.2619 | 0.2619 | ✓ |
| ours_cascade | 0.6052 | 0.6052 | ✓ |

## 误判实例 (按配置)

### b3_deterministic (94条)
- C05QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C05QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C05QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C05QA-004 [capability_state/s_state_narrative] support→not_in_evidence
- C05QA-005 [capability_state/s_state_narrative] support→not_in_evidence
- C05QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C05QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C05QA-012 [capability_device/r_device_member_drop] refute→not_in_evidence
- C05QA-014 [capability_state/r_state_member_swap] refute→not_in_evidence
- C05QA-015 [capability_state/r_state_member_drop] refute→not_in_evidence
- C05QA-016 [interface_flow/r_sender_swap] refute→support
- C05QA-017 [interface_flow/r_sender_swap] refute→support
- C05QA-018 [param_value/r_value_swap] refute→support
- C05QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C05QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C05QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C05QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C06QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C06QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C06QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C06QA-004 [capability_state/s_state_narrative] support→not_in_evidence
- C06QA-005 [capability_state/s_state_narrative] support→not_in_evidence
- C06QA-006 [interface_flow/s_interface_narrative] support→not_in_evidence
- C06QA-007 [interface_flow/s_interface_narrative] support→not_in_evidence
- C06QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C06QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C06QA-011 [capability_device/r_device_member_drop] refute→not_in_evidence
- C06QA-012 [capability_device/r_device_member_add] refute→not_in_evidence
- C06QA-013 [capability_device/r_device_member_add] refute→not_in_evidence
- C06QA-014 [capability_state/r_state_member_drop] refute→not_in_evidence
- C06QA-015 [capability_state/r_state_member_swap] refute→not_in_evidence
- C06QA-016 [interface_flow/r_sender_swap] refute→support
- C06QA-017 [interface_flow/r_sender_swap] refute→support
- C06QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C06QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C06QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C06QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C07QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-004 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-005 [capability_state/s_state_narrative] support→not_in_evidence
- C07QA-006 [capability_state/s_state_narrative] support→not_in_evidence
- C07QA-008 [interface_flow/s_interface_narrative] support→refute
- C07QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C07QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C07QA-011 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-012 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-013 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-014 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-015 [capability_state/r_state_member_drop] refute→not_in_evidence
- C07QA-016 [capability_state/r_state_member_drop] refute→not_in_evidence
- C07QA-017 [interface_flow/r_sender_swap] refute→support
- C07QA-019 [trace_binding/r_task_swap] refute→support
- C07QA-020 [trace_binding/r_task_swap] refute→support
- C07QA-027 [interface_flow/n_effect_claim] not_in_evidence→support
- C07QA-030 [usecase_e1/n_effect_claim] not_in_evidence→refute
- C08QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-004 [capability_state/s_state_narrative] support→not_in_evidence
- C08QA-005 [capability_state/s_state_narrative] support→not_in_evidence
- C08QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C08QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C08QA-011 [capability_device/r_device_member_drop] refute→not_in_evidence
- C08QA-014 [capability_state/r_state_swap] refute→not_in_evidence
- C08QA-015 [capability_state/r_state_swap] refute→not_in_evidence
- C08QA-016 [interface_flow/r_sender_swap] refute→support
- C08QA-017 [interface_flow/r_sender_swap] refute→support
- C08QA-018 [param_value/r_value_swap] refute→support
- C08QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C08QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C08QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C08QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C10QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-004 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-005 [capability_state/s_state_narrative] support→not_in_evidence
- C10QA-006 [capability_state/s_state_narrative] support→not_in_evidence
- C10QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C10QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C10QA-011 [capability_state/r_state_member_drop] refute→not_in_evidence
- C10QA-012 [capability_state/r_state_member_swap] refute→not_in_evidence
- C10QA-013 [capability_state/r_state_member_drop] refute→not_in_evidence
- C10QA-014 [capability_state/r_state_swap] refute→not_in_evidence
- C10QA-015 [capability_state/r_state_member_drop] refute→not_in_evidence
- C10QA-016 [capability_state/r_state_swap] refute→not_in_evidence
- C10QA-017 [interface_flow/r_sender_swap] refute→support
- C10QA-018 [interface_flow/r_sender_swap] refute→support
- C10QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C10QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C10QA-027 [interface_flow/n_effect_claim] not_in_evidence→support
- C10QA-029 [trace_binding/n_effect_claim] not_in_evidence→support

### l2_egt_nli (79条)
- C05QA-001 [capability_device/s_device_narrative] support→refute
- C05QA-002 [capability_device/s_device_narrative] support→refute
- C05QA-003 [capability_device/s_device_narrative] support→refute
- C05QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C05QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C05QA-016 [interface_flow/r_sender_swap] refute→support
- C05QA-017 [interface_flow/r_sender_swap] refute→support
- C05QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C05QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C05QA-021 [capability_device/n_value_absent] not_in_evidence→refute
- C05QA-022 [capability_device/n_value_absent] not_in_evidence→refute
- C05QA-025 [capability_state/n_effect_claim] not_in_evidence→refute
- C05QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C05QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
- C05QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C06QA-001 [capability_device/s_device_narrative] support→refute
- C06QA-002 [capability_device/s_device_narrative] support→refute
- C06QA-003 [capability_device/s_device_narrative] support→refute
- C06QA-007 [interface_flow/s_interface_narrative] support→not_in_evidence
- C06QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C06QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C06QA-016 [interface_flow/r_sender_swap] refute→support
- C06QA-017 [interface_flow/r_sender_swap] refute→support
- C06QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C06QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C06QA-024 [capability_state/n_value_absent] not_in_evidence→refute
- C06QA-025 [capability_state/n_effect_claim] not_in_evidence→refute
- C06QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C06QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
- C06QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C07QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-002 [capability_device/s_device_narrative] support→refute
- C07QA-003 [capability_device/s_device_narrative] support→refute
- C07QA-004 [capability_device/s_device_narrative] support→refute
- C07QA-006 [capability_state/s_state_narrative] support→not_in_evidence
- C07QA-008 [interface_flow/s_interface_narrative] support→refute
- C07QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C07QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C07QA-017 [interface_flow/r_sender_swap] refute→support
- C07QA-019 [trace_binding/r_task_swap] refute→support
- C07QA-020 [trace_binding/r_task_swap] refute→support
- C07QA-021 [capability_device/n_value_absent] not_in_evidence→refute
- C07QA-026 [capability_state/n_effect_claim] not_in_evidence→refute
- C07QA-027 [interface_flow/n_effect_claim] not_in_evidence→support
- C07QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C07QA-030 [usecase_e1/n_effect_claim] not_in_evidence→refute
- C08QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-002 [capability_device/s_device_narrative] support→refute
- C08QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C08QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C08QA-016 [interface_flow/r_sender_swap] refute→support
- C08QA-017 [interface_flow/r_sender_swap] refute→support
- C08QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C08QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C08QA-021 [capability_device/n_value_absent] not_in_evidence→refute
- C08QA-022 [capability_device/n_value_absent] not_in_evidence→refute
- C08QA-024 [capability_state/n_value_absent] not_in_evidence→refute
- C08QA-025 [capability_state/n_effect_claim] not_in_evidence→refute
- C08QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C08QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
- C08QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C10QA-001 [capability_device/s_device_narrative] support→refute
- C10QA-002 [capability_device/s_device_narrative] support→refute
- C10QA-003 [capability_device/s_device_narrative] support→refute
- C10QA-004 [capability_device/s_device_narrative] support→refute
- C10QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C10QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C10QA-017 [interface_flow/r_sender_swap] refute→support
- C10QA-018 [interface_flow/r_sender_swap] refute→support
- C10QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C10QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C10QA-021 [capability_device/n_value_absent] not_in_evidence→refute
- C10QA-022 [capability_device/n_value_absent] not_in_evidence→refute
- C10QA-023 [capability_device/n_value_absent] not_in_evidence→refute
- C10QA-025 [capability_state/n_value_absent] not_in_evidence→refute
- C10QA-026 [capability_state/n_effect_claim] not_in_evidence→refute
- C10QA-027 [interface_flow/n_effect_claim] not_in_evidence→support
- C10QA-029 [trace_binding/n_effect_claim] not_in_evidence→support

### ours_cascade (61条)
- C05QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C05QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C05QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C05QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C05QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C05QA-016 [interface_flow/r_sender_swap] refute→support
- C05QA-017 [interface_flow/r_sender_swap] refute→support
- C05QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C05QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C05QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C05QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C06QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C06QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C06QA-007 [interface_flow/s_interface_narrative] support→not_in_evidence
- C06QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C06QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C06QA-016 [interface_flow/r_sender_swap] refute→support
- C06QA-017 [interface_flow/r_sender_swap] refute→support
- C06QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C06QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C06QA-024 [capability_state/n_value_absent] not_in_evidence→refute
- C06QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C06QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C07QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-004 [capability_device/s_device_narrative] support→not_in_evidence
- C07QA-006 [capability_state/s_state_narrative] support→not_in_evidence
- C07QA-008 [interface_flow/s_interface_narrative] support→refute
- C07QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C07QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C07QA-017 [interface_flow/r_sender_swap] refute→support
- C07QA-019 [trace_binding/r_task_swap] refute→support
- C07QA-020 [trace_binding/r_task_swap] refute→support
- C07QA-027 [interface_flow/n_effect_claim] not_in_evidence→support
- C07QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C07QA-030 [usecase_e1/n_effect_claim] not_in_evidence→refute
- C08QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C08QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C08QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C08QA-016 [interface_flow/r_sender_swap] refute→support
- C08QA-017 [interface_flow/r_sender_swap] refute→support
- C08QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C08QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C08QA-024 [capability_state/n_value_absent] not_in_evidence→support
- C08QA-026 [interface_flow/n_effect_claim] not_in_evidence→support
- C08QA-029 [trace_binding/n_effect_claim] not_in_evidence→support
- C10QA-001 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-002 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-003 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-004 [capability_device/s_device_narrative] support→not_in_evidence
- C10QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence
- C10QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence
- C10QA-017 [interface_flow/r_sender_swap] refute→support
- C10QA-018 [interface_flow/r_sender_swap] refute→support
- C10QA-019 [trace_binding/r_task_swap] refute→not_in_evidence
- C10QA-020 [trace_binding/r_task_swap] refute→not_in_evidence
- C10QA-027 [interface_flow/n_effect_claim] not_in_evidence→support
- C10QA-029 [trace_binding/n_effect_claim] not_in_evidence→support

### mdeberta_zeroshot (70条)
- C05QA-008 [param_value/s_param_narrative] support→not_in_evidence
- C05QA-011 [capability_device/r_device_member_add] refute→support
- C05QA-012 [capability_device/r_device_member_drop] refute→not_in_evidence
- C05QA-013 [capability_device/r_device_member_add] refute→support
- C05QA-014 [capability_state/r_state_member_swap] refute→support
- C05QA-016 [interface_flow/r_sender_swap] refute→support
- C05QA-017 [interface_flow/r_sender_swap] refute→not_in_evidence
- C05QA-018 [param_value/r_value_swap] refute→not_in_evidence
- C05QA-021 [capability_device/n_value_absent] not_in_evidence→support
- C05QA-022 [capability_device/n_value_absent] not_in_evidence→support
- C05QA-024 [capability_state/n_value_absent] not_in_evidence→support
- C05QA-027 [param_value/n_effect_claim] not_in_evidence→support
- C05QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
- C06QA-008 [param_value/s_param_narrative] support→not_in_evidence
- C06QA-010 [trace_binding/s_trace_narrative] support→refute
- C06QA-011 [capability_device/r_device_member_drop] refute→not_in_evidence
- C06QA-012 [capability_device/r_device_member_add] refute→support
- C06QA-013 [capability_device/r_device_member_add] refute→not_in_evidence
- C06QA-015 [capability_state/r_state_member_swap] refute→support
- C06QA-016 [interface_flow/r_sender_swap] refute→support
- C06QA-017 [interface_flow/r_sender_swap] refute→support
- C06QA-018 [param_value/r_value_swap] refute→not_in_evidence
- C06QA-020 [trace_binding/r_task_swap] refute→support
- C06QA-021 [capability_device/n_value_absent] not_in_evidence→support
- C06QA-022 [capability_device/n_value_absent] not_in_evidence→support
- C06QA-024 [capability_state/n_value_absent] not_in_evidence→support
- C06QA-025 [capability_state/n_effect_claim] not_in_evidence→support
- C06QA-028 [trace_binding/n_value_absent] not_in_evidence→support
- C07QA-011 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-012 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-013 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-014 [capability_device/r_device_member_drop] refute→not_in_evidence
- C07QA-016 [capability_state/r_state_member_drop] refute→not_in_evidence
- C07QA-017 [interface_flow/r_sender_swap] refute→support
- C07QA-018 [interface_flow/r_sender_swap] refute→support
- C07QA-019 [trace_binding/r_task_swap] refute→support
- C07QA-020 [trace_binding/r_task_swap] refute→support
- C07QA-021 [capability_device/n_value_absent] not_in_evidence→support
- C07QA-022 [capability_device/n_value_absent] not_in_evidence→support
- C07QA-023 [capability_device/n_value_absent] not_in_evidence→support
- C07QA-025 [capability_state/n_value_absent] not_in_evidence→support
- C07QA-026 [capability_state/n_effect_claim] not_in_evidence→support
- C07QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
- C08QA-008 [param_value/s_param_narrative] support→not_in_evidence
- C08QA-012 [capability_device/r_device_member_add] refute→not_in_evidence
- C08QA-013 [capability_device/r_device_member_add] refute→support
- C08QA-014 [capability_state/r_state_swap] refute→support
- C08QA-015 [capability_state/r_state_swap] refute→support
- C08QA-016 [interface_flow/r_sender_swap] refute→support
- C08QA-017 [interface_flow/r_sender_swap] refute→support
- C08QA-018 [param_value/r_value_swap] refute→not_in_evidence
- C08QA-019 [trace_binding/r_task_swap] refute→support
- C08QA-020 [trace_binding/r_task_swap] refute→support
- C08QA-021 [capability_device/n_value_absent] not_in_evidence→support
- C08QA-022 [capability_device/n_value_absent] not_in_evidence→support
- C08QA-024 [capability_state/n_value_absent] not_in_evidence→support
- C08QA-025 [capability_state/n_effect_claim] not_in_evidence→support
- C08QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
- C10QA-010 [trace_binding/s_trace_narrative] support→refute
- C10QA-012 [capability_state/r_state_member_swap] refute→support
- C10QA-014 [capability_state/r_state_swap] refute→support
- C10QA-016 [capability_state/r_state_swap] refute→support
- C10QA-017 [interface_flow/r_sender_swap] refute→support
- C10QA-018 [interface_flow/r_sender_swap] refute→support
- C10QA-021 [capability_device/n_value_absent] not_in_evidence→support
- C10QA-022 [capability_device/n_value_absent] not_in_evidence→support
- C10QA-023 [capability_device/n_value_absent] not_in_evidence→support
- C10QA-025 [capability_state/n_value_absent] not_in_evidence→support
- C10QA-026 [capability_state/n_effect_claim] not_in_evidence→support
- C10QA-028 [trace_binding/n_value_absent] not_in_evidence→refute
