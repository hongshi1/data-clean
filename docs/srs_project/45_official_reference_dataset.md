# 45. 场景1官方参考数据集（scene1_official_reference_v1）

> 版本：v1 | 构建：2026-10-22 | 状态：**项目官方标准参考数据 + 本会话全链派生资产整合**
> 资产：`data/gjb_438c/qa_frozen/scene1_official_reference_v1.jsonl`（91 行，已进 MANIFEST）
> 构建：`python tools/build_official_reference_dataset.py` | 测试：`tests/test_official_reference_dataset.py`

## 1. 官方补发包（数据来源，不可修改）

场景1补发包位于 `docs/doc11/场景1-软件需求规格辅助生成场景补发数据/`，是**项目官方提供的标准参考数据**：

| 文件 | 作用 |
|---|---|
| 高质量问答对（配套…04数据统一访问服务…）.json | **91 条 Alpaca 格式 QA 对**（instruction/input/output/system） |
| 2-某项目的合同、需归文档/数据服务软件需求规格说明.docx | 04号 SRS 原始文档 |
| 2-某项目的合同、需归文档/1-某大数据典型应用系统集成支撑合同-20240513.docx | 项目合同 |
| 1-438C软件需求规格相关模板/09_软件需求规格说明.docx 等 | GJB 438C 模板三份 |

## 2. 官方 QA 对的字段语义（逐条核实，91/91）

```json
{"instruction": "<问题文本>", "input": "", "output": "<answer>", "system": ""}
```

- `instruction` = **问题本身**：与 `scene1_qa_audit` 的 question 逐条 100% 一致
- `input` = **空（0/91）**：answer 生成时未记录任何检索上下文
- `system` = **空（0/91）**：answer 生成时未记录任何系统指令
- `output` = answer

**数据事实**：input/system 全空说明这批 answer **非检索式生成**（未按 question 召回后作答）——这解释了 answer 中大量跨用例混编（S1QA-013 的 E1 转移）与凭空内容（S1QA-002 编造步骤）。三重校验框架中的 A↔I（instruction 约束）关系在此数据上**无素材可评测**。

## 3. 整合的派生资产（每行记录包含）

| 字段 | 来源 | 内容 |
|---|---|---|
| `official_alpaca` | 官方源 JSON | 四字段逐字保留 |
| `context_freeze_id` + `evidence` | `scene1_qa_frozen_v1` | 574 条块级冻结证据（含 source_ref/scope/completeness） |
| `linearized_statements` | evidence_statements 线性化 | 6758 条字段级语句（statement_id/field_name/scope_key/row_index 行级定位） |
| `silver_label` | GLM-5.3 复核 final_labels | 三态判定 + 逐 claim + 双标历史（**is_gold=False，升 gold 需人工双标+仲裁**） |

silver 分布：support 6 / refute 8 / not_in_evidence 77。

## 4. 血缘（metadata 记录）

- 官方包 6 个文件的 sha256
- 三个输入工件哈希：source_qa / frozen / labels
- 标签 run：`runs/review_qa_with_glm53_582b51e5_20261021_145212`

## 5. 复用方式

- **标注**：人工双标 pilot 直接消费此数据集（question/answer/证据/语句/silver 参考齐全）
- **评测**：evaluator 与 baseline 以 `silver_label.final_verdict` 为参考（报告必须注明 silver 非 gold）
- **变异**：answer-only 算子输入即 `official_alpaca.output` + `evidence`
- **禁改**：`official_alpaca` 字段为官方原始数据，任何脚本不得覆写；重生成派生字段后须重跑 MANIFEST

## 6. 相关资产链

```text
官方补发包(源) → scene1_qa_audit(审计) → scene1_qa_frozen_v1(冻结输入)
                                            ↓
              review_qa_with_glm53(silver标签) → scene1_official_reference_v1(本数据集)
```
