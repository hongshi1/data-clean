# 跨文档泛化评测 (06号 × 构造性sound标签)

- evalset: `C:\Users\12488\Desktop\data_clean\data\gjb_438c\qa_frozen\crossdoc06_evalset_v1.jsonl` (30行, S/R/N各10)
- label: **constructive_sound (label_proof; no LLM silver)** (构造性sound, label_proof背书)
- reference: eval_cascade_1e92cdce_20261027_124941

## deterministic

- n=30 accuracy=0.2667 macro_f1=0.1524 llm_invocations=0 (api_calls=0)

| class | precision | recall | f1 |
|---|---|---|---|
| support | 0.0 | 0.0 | 0.0 |
| refute | 0.0 | 0.0 | 0.0 |
| not_in_evidence | 0.32 | 0.8 | 0.4571 |

混淆矩阵 (pred|gold):
`{"support|refute": 2, "support|not_in_evidence": 2, "refute|support": 1, "not_in_evidence|support": 9, "not_in_evidence|refute": 8, "not_in_evidence|not_in_evidence": 8}`

## cascade

- n=30 accuracy=0.5333 macro_f1=0.5309 llm_invocations=11 (api_calls=0)

| class | precision | recall | f1 |
|---|---|---|---|
| support | 0.4444 | 0.4 | 0.4211 |
| refute | 0.7143 | 0.5 | 0.5882 |
| not_in_evidence | 0.5 | 0.7 | 0.5833 |

混淆矩阵 (pred|gold):
`{"support|support": 4, "support|refute": 3, "support|not_in_evidence": 2, "refute|support": 1, "refute|refute": 5, "refute|not_in_evidence": 1, "not_in_evidence|support": 5, "not_in_evidence|refute": 2, "not_in_evidence|not_in_evidence": 7}`

## 泛化落差 (06号 − 04号同配置)

| config | 04 macro-F1 | 06 macro-F1 | Δ | Δsupport-F1 | Δrefute-F1 | ΔNIE-F1 |
|---|---|---|---|---|---|---|
| deterministic | 0.6381 | 0.1524 | -0.4857 | -0.25 | -0.7143 | -0.4929 |
| cascade | 0.7185 | 0.5309 | -0.1876 | 0.0211 | -0.2118 | -0.3721 |

## 检出通道归因 (deterministic, 按gold标签)

| gold | 触发的claim methods |
|---|---|
| support | `{"semantic_unresolved": 5, "conservative_unresolved": 3, "l0_entity_detector:TERM-07": 4, "numeric_z3_expert": 1, "identifier_exact_match": 1, "sequence_alignment": 2}` |
| refute | `{"semantic_unresolved": 5, "identifier_exact_match": 4, "l0_entity_detector:TERM-07": 4, "conservative_unresolved": 1, "sequence_alignment": 2}` |
| not_in_evidence | `{"semantic_unresolved": 7, "identifier_exact_match": 2, "l0_entity_detector:TERM-07": 3, "conservative_unresolved": 1, "sequence_alignment": 1}` |

误判实例 (gold→pred):
- C06QA-001 [capability_device/s_device_narrative] support→not_in_evidence methods=['semantic_unresolved']
- C06QA-002 [capability_device/s_device_narrative] support→not_in_evidence methods=['semantic_unresolved']
- C06QA-003 [capability_device/s_device_narrative] support→not_in_evidence methods=['semantic_unresolved']
- C06QA-004 [capability_state/s_state_narrative] support→not_in_evidence methods=['semantic_unresolved']
- C06QA-005 [capability_state/s_state_narrative] support→not_in_evidence methods=['semantic_unresolved']
- C06QA-006 [interface_flow/s_interface_narrative] support→not_in_evidence methods=['conservative_unresolved', 'l0_entity_detector:TERM-07']
- C06QA-007 [interface_flow/s_interface_narrative] support→not_in_evidence methods=['conservative_unresolved', 'l0_entity_detector:TERM-07']
- C06QA-008 [param_value/s_param_narrative] support→refute methods=['numeric_z3_expert']
- C06QA-009 [trace_binding/s_trace_narrative] support→not_in_evidence methods=['identifier_exact_match', 'l0_entity_detector:TERM-07', 'sequence_alignment']
- C06QA-010 [trace_binding/s_trace_narrative] support→not_in_evidence methods=['conservative_unresolved', 'l0_entity_detector:TERM-07', 'sequence_alignment']
- C06QA-011 [capability_device/r_device_member_drop] refute→not_in_evidence methods=['semantic_unresolved']
- C06QA-012 [capability_device/r_device_member_add] refute→not_in_evidence methods=['semantic_unresolved']
- C06QA-013 [capability_device/r_device_member_add] refute→not_in_evidence methods=['semantic_unresolved']
- C06QA-014 [capability_state/r_state_member_drop] refute→not_in_evidence methods=['semantic_unresolved']
- C06QA-015 [capability_state/r_state_member_swap] refute→not_in_evidence methods=['semantic_unresolved']
- C06QA-016 [interface_flow/r_sender_swap] refute→support methods=['identifier_exact_match', 'l0_entity_detector:TERM-07']
- C06QA-017 [interface_flow/r_sender_swap] refute→support methods=['identifier_exact_match', 'l0_entity_detector:TERM-07']
- C06QA-018 [param_value/r_value_swap] refute→not_in_evidence methods=['conservative_unresolved']
- C06QA-019 [trace_binding/r_task_swap] refute→not_in_evidence methods=['identifier_exact_match', 'l0_entity_detector:TERM-07', 'sequence_alignment']
- C06QA-020 [trace_binding/r_task_swap] refute→not_in_evidence methods=['identifier_exact_match', 'l0_entity_detector:TERM-07', 'sequence_alignment']
- C06QA-026 [interface_flow/n_effect_claim] not_in_evidence→support methods=['identifier_exact_match', 'l0_entity_detector:TERM-07']
- C06QA-029 [trace_binding/n_effect_claim] not_in_evidence→support methods=['identifier_exact_match', 'l0_entity_detector:TERM-07']
