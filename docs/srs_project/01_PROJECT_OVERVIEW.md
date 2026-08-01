# 01 - 项目概述

## 做什么

从62个SRS PDF文档中检测五层不一致性:

```
一、语法不一致 — 文档结构问题(章节缺失/引用断裂/单位不统一/命名漂移)
二、语义不一致 — 内容自相矛盾(同参数不同值/接口矛盾/术语不一致/需求重复)
三、逻辑不一致 — 逻辑不可满足(约束集矛盾/时序环/物理约束矛盾)
四、特征提取与上下文关联 — 知识图谱构建+需求追溯链路(未实现)
五、图片-文本不一致 — 图文矛盾(内容矛盾/引用断裂/流程图结构问题)
```

## 数据集

| 数据 | 数量 | 来源 | 位置 |
|---|---|---|---|
| 原始PDF | 62个 | [PURE](https://zenodo.org/records/1414117) | `data/srs_requirements/req/` |
| 解析JSON | 62个 | pdfplumber解析 | `data/srs_requirements/parsed/` |
| 银标准(训练) | 4,070句 | 正则规则自动标注(~70%精度) | `data/srs_requirements/bert_crf/silver_standard.json` |
| 金标准(评估) | 100句 | GLM-5标注(~90%精度) | `data/srs_requirements/bert_crf/gold_standard_fixed.json` |
| 知识库 | 374实体 | 人工构建(23参数/13接口/67单位) | `knowledge/srs_kb.json` |
| 知识图谱 | 1,580节点 | NetworkX构建 | `data/srs_requirements/knowledge_graph.json` |
| 页面截图 | 14,610张 | pdfplumber渲染 | `data/srs_requirements/images_hd/` |

## 方法谱系

| 家族 | 方法 | 实现 | F1(金标准) |
|---|---|:---:|:---:|
| F1 规则 | 正则模式匹配(12组) | ✅ | 0.32 |
| F3 BERT-CRF | MiniLM+CRF弱监督训练 | ✅ | 0.05 |
| F4 Span-Based | embedding+LR(SpERT思路) | ✅ | 0.54 |
| F5 生成式UIE | GLM-5 SSI schema | ✅ | P~0.95 |
| F6 LLM-Based | GLM-5验证+Kimi-K2.6多模态 | ✅ | — |
| F7 知识增强 | KB embedding实体链接 | ✅ | — |
| F8 文档结构 | pdfplumber表格+图片 | ✅ | — |
| F9 混合级联 | 多层编排 | ✅ | — |
| F10 需求专用 | EARS模板+shall模式 | ✅ | — |

## 复现的11篇论文

| 论文 | arXiv | 方法 | F1/结果 |
|---|---|---|---|
| ReXCL | 2504.07562 | SRS抽取+MLM适配 | 分类F1=0.61 |
| BERT-CRF | 1508.01991 | 序列标注 | F1=0.05 |
| SpERT | 1909.07755 | Span+关系联合抽取 | F1=0.54 |
| UIE | 2203.12277 | 生成式统一IE | P~0.95 |
| SummaC/NLI | 2111.09525 | NLI矛盾检测 | 1条真矛盾 |
| Z3 Solver | — | SMT约束求解 | 0条真矛盾 |
| FloCA | 2602.14035 | 流程图路径一致性 | 37个问题 |
| DFD规则 | 1011.0278 | DFD规则检查 | 4个违反 |
| Visual Entailment | 1901.06706 | 图文蕴含 | 1个矛盾 |
| ChartVE | 2312.10160 | 图表数值一致性 | 0个冲突 |
| TraceLLM | 2602.01253 | 追溯链路 | 4孤立+14幻影 |
