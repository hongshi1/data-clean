# 04 - 论文复现详情

## 复现的11篇论文

### 1. ReXCL — SRS文档抽取与分类

| 项 | 内容 |
|---|---|
| 论文 | [arXiv:2504.07562](https://arxiv.org/abs/2504.07562) |
| 年份 | 2025, Bosch Research |
| 解决问题 | 把SRS文档自动结构化+分类需求条目 |
| 核心创新 | 领域自适应MLM预训练(F1: 0.25→0.97) |
| 我们复现 | RF去页眉+正则切章节+MLM适配 |
| 代码 | [`tools/srs_rexcl.py`](../../tools/srs_rexcl.py) + [`tools/srs_rexcl_mlm.py`](../../tools/srs_rexcl_mlm.py) |
| 论文F1 | 0.97(分类) |
| 我们F1 | 0.61(分类), MLM无提升(0.43→0.43) |
| 差距原因 | MiniLM无MLM head; 基线已强 |

### 2. BERT-CRF — 序列标注

| 项 | 内容 |
|---|---|
| 论文 | [arXiv:1508.01991](https://arxiv.org/abs/1508.01991) |
| 年份 | 2015 |
| 解决问题 | NER不需要手工特征, 端到端学习 |
| 核心创新 | BiLSTM(双向上下文)+CRF(标签转移约束) |
| 我们复现 | 弱监督标注+MiniLM+CRF训练 |
| 代码 | [`tools/srs_bert_crf.py`](../../tools/srs_bert_crf.py) |
| 论文F1 | ~97%(POS, 人工标注数据) |
| 我们F1 | 0.05(金标准) |
| 差距原因 | 银标准噪声(~70%精度)导致模型学到错误 |

### 3. SpERT — Span联合抽取

| 项 | 内容 |
|---|---|
| 论文 | [arXiv:1909.07755](https://arxiv.org/abs/1909.07755) |
| 年份 | 2020, ECAI |
| 解决问题 | 用span枚举替代BIO, 支持嵌套实体+联合关系抽取 |
| 核心创新 | Span枚举+局部上下文+强负采样 |
| 我们复现 | span枚举+embedding+LR(简化版) |
| 代码 | [`tools/srs_keie_pipeline.py`](../../tools/srs_keie_pipeline.py) |
| 论文F1 | 88.9%(实体, BERT+人工标注) |
| 我们F1 | 0.54(span分类, MiniLM+银标准) |
| 差距原因 | MiniLM(384维) vs BERT(768维); 银标准 vs 人工标注 |

### 4. UIE — 生成式统一IE

| 项 | 内容 |
|---|---|
| 论文 | [arXiv:2203.12277](https://arxiv.org/abs/2203.12277) |
| 年份 | 2022, ACL |
| 核心创新 | SSI(schema)+SEL(结构化输出语言)→text-to-structure生成 |
| 我们复现 | 用GLM-5实现SSI思路(schema→JSON) |
| 代码 | [`tools/srs_llm_extract.py`](../../tools/srs_llm_extract.py) |
| 结果 | P~0.95(精度最高), 召回低(8.5%) |

### 5. SummaC/NLI — 矛盾检测

| 项 | 内容 |
|---|---|
| 论文 | [arXiv:2111.09525](https://arxiv.org/abs/2111.09525) |
| 年份 | 2021 |
| 核心创新 | NLI模型判断句子对是否矛盾 |
| 我们复现 | GLM-5判断40对约束, 6条矛盾, 1条真矛盾 |
| 结果 | **唯一发现真矛盾的方法(availability 99.99% vs 99.999%)** |

### 6-11. 图片-文本检测(6篇)

| 论文 | arXiv | 检测什么 | 结果 |
|---|---|---|---|
| FloCA | 2602.14035 | 流程图路径一致性 | 37个问题 |
| DFD规则 | 1011.0278 | DFD规则检查 | 4个违反 |
| Visual Entailment | 1901.06706 | 图文蕴含 | 1个矛盾 |
| ChartVE | 2312.10160 | 图表数值 | 0个冲突 |
| Z3 Solver | — | 状态机验证 | 1个失败 |
| TraceLLM | 2602.01253 | 追溯链路 | 4孤立+14幻影 |

代码: [`tools/srs_image_text_check.py`](../../tools/srs_image_text_check.py)

---

## 三篇核心论文对比

| | ReXCL | BERT-CRF | SpERT |
|---|---|---|---|
| 解决什么 | 需求文档结构化 | NER序列标注 | 实体+关系联合抽取 |
| 核心创新 | 领域自适应MLM | BiLSTM+CRF端到端 | Span枚举替代BIO |
| 输入 | PDF文档 | token序列 | 句子 |
| 输出 | 章节+分类 | BIO标签 | 实体+关系 |
| 论文F1 | 0.97 | ~97% | 88.9% |
| 我们F1 | 0.61 | 0.05 | 0.54 |
| 差距原因 | 无MLM head | 银标准噪声 | MiniLM+银标准 |
| 在系统中的角色 | 语法层(章节抽取) | 语义层(参数NER) | 语义层(span分类) |
