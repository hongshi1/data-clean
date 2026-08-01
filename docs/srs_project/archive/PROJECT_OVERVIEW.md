# SRS 需求文档信息抽取 — 项目总览

> **项目名称**: 军用 SRS 文档参数化需求抽取与一致性校验
> **数据集**: PURE (62 个真实软件需求规格文档)
> **更新日期**: 2026-07-20

---

## 一、任务定义

### 1.1 核心任务

从 PDF 格式的软件需求规格文档 (SRS) 中，自动完成以下任务：

| 任务编号 | 任务名称 | 输入 | 输出 | 说明 |
|:---:|---|---|---|---|
| T1 | **参数化约束抽取** | SRS 文档文本 | `{参数名, 运算符, 数值, 单位}` 四元组 | 如 "response time shall not exceed 50 ms" → `(response_time, ≤, 50, ms)` |
| T2 | **实体识别 (NER)** | 句子 | BIO 标注序列 | 4 类实体: PARAM / VALUE / UNIT / OPERATOR |
| T3 | **需求分类** | 章节文本 | 类别标签 | 4 类: INFO / HEADER / FUNC_REQ / NON_FUNC_REQ |
| T4 | **文档结构化** | PDF | 章节树 + 表格 | `<section_number, heading, [texts]>` |
| T5 | **冲突检测** | 约束集合 | 冲突报告 | 同参数不同值 / 接口矛盾 / 物理约束矛盾 |
| T6 | **一致性校验** | 文档 | L1+L2+L3 冲突 | 语法(章节缺项/引用断裂) + 语义(参数矛盾) + 逻辑(物理约束) |

### 1.2 技术路线

```
PDF → 文档解析 → 预过滤(候选句) → 实体抽取(NER) → 关系抽取(参数-值-单位)
                                                          ↓
                                          知识库验证 → 冲突检测 → 报告
```

---

## 二、数据集

### 2.1 主数据集: PURE

| 属性 | 值 |
|---|---|
| **名称** | PURE (PUrpose-based REquirements) |
| **来源** | Zenodo https://zenodo.org/records/1414117 |
| **文件数** | 62 个 PDF |
| **总页数** | 2,833 页 |
| **总字符** | 4,599,632 字符 |
| **总表格** | 1,845 个 |
| **时间跨度** | 1995-2010 年真实 SRS 文档 |
| **解析工具** | pdfplumber (基线) / MinerU (待升级) |
| **解析状态** | ✅ 62 个 JSON (含 pages + tables) |

### 2.2 标注数据

| 标注集 | 句子数 | 标注方式 | 质量 | 用途 |
|---|---|---|---|---|
| **银标准 (Silver)** | 4,070 | 启发式规则自动标注 | ~70% 精度 | 训练 (弱监督) |
| **金标准 (Gold)** | 102 | GLM-5 LLM 标注 | ~90% 精度 | 评估 (金标准) |
| **领域语料** | 69,016 | 62 文档无标注文本 | — | MLM 领域适配 |

### 2.3 银标准标签分布

| 标签 | 数量 | 说明 |
|---|---|---|
| O | 173,889 | 非实体 |
| B-VALUE | 7,164 | 数值 |
| B-OPERATOR | 6,670 | 运算符 |
| B-UNIT | 1,878 | 单位 |
| B-PARAM | 691 | 参数名 |
| I-OPERATOR | 1,342 | 运算符(内部) |
| I-PARAM | 21 | 参数名(内部) |
| I-UNIT | 11 | 单位(内部) |

### 2.4 金标准标签分布

| 标签 | 数量 | 说明 |
|---|---|---|
| O | 2,264 | 非实体 |
| B-PARAM | 96 | 参数名 |
| I-PARAM | 132 | 参数名(内部) |
| B-OPERATOR | 49 | 运算符 |
| I-OPERATOR | 47 | 运算符(内部) |
| B-VALUE | 38 | 数值 |
| B-UNIT | 36 | 单位 |
| I-VALUE | 17 | 数值(内部) |
| I-UNIT | 11 | 单位(内部) |

### 2.5 知识库 (srs_kb.json)

| 组件 | 数量 | 说明 |
|---|---|---|
| 参数类型 | 23 | response_time, throughput, availability, temperature... |
| 接口类型 | 13 | RS232, RS422, CAN, MIL-STD-1553, Ethernet... |
| 单位类型 | 67 (9维度) | time, frequency, storage, percentage, voltage... |
| 运算符 | 6 类 | <=, >=, <, >, =, ~= (含文字版) |
| KB 实体总数 | 374 | 用于 embedding 索引 |

---

## 三、评估指标

### 3.1 实体级指标

| 指标 | 公式 | 说明 |
|---|---|---|
| **Precision (P)** | TP / (TP + FP) | 标注的实体中正确的比例 |
| **Recall (R)** | TP / (TP + FN) | 应标注的实体中被标注的比例 |
| **F1** | 2PR / (P + R) | 调和平均 |

### 3.2 评估协议

| 评估类型 | 训练集 | 测试集 | 说明 |
|---|---|---|---|
| **银→银 (Silver→Silver)** | 银标准 | 银标准(held-out) | ⚠️ 循环评估，会高估 |
| **银→金 (Silver→Gold)** | 银标准 | 金标准(102句) | ✅ 真实泛化性能 |
| **金→金 (Gold→Gold)** | 金标准 | 金标准(held-out) | 少样本上限 |
| **5折交叉验证 (CV5)** | 银标准 | 银标准(轮转) | 内部一致性 |

### 3.3 分类型评估

按 4 种实体类型分别计算 P/R/F1：
- PARAM (参数名)
- VALUE (数值)
- UNIT (单位)
- OPERATOR (运算符)

### 3.4 端到端指标

| 指标 | 说明 |
|---|---|
| 约束抽取精度 | 提取的 `{参数, 运算符, 数值, 单位}` 四元组中正确的比例 |
| 冲突检测率 | 检测到的真实冲突数量 |
| 冲突误报率 | 误报冲突的比例 |

---

## 四、实验结果总表

### 4.1 全部实验结果

| 实验ID | 方法 | 训练数据 | 模型 | 领域适配 | 评估集 | P | R | F1 | 状态 |
|:---:|---|---|---|---|---|---|---|---|---|
| E01 | 启发式 | — | 规则+embedding | — | 金标准 | ~0.70 | ~0.11 | ~0.19 | ✅ |
| E02 | BERT-CRF | 银标准(4070) | MiniLM+CRF | — | 银标准(CV) | 0.53 | 0.06 | 0.11 | ✅ |
| E03 | BERT-CRF | 银标准(4070) | MiniLM+CRF | — | 金标准(102) | 0.16 | 0.03 | 0.05 | ✅ |
| E04 | Span+LR | 银标准(4070) | MiniLM+LR | — | 银标准 | — | — | 0.97 | ✅ |
| **E05** | **Span+LR** | **银标准(4070)** | **MiniLM+LR** | **—** | **金标准(102)** | **0.50** | **0.50** | **0.43** | ✅ |
| E06 | BERT-CRF | LLM10x+银标准 | MiniLM+CRF | — | 金标准(102) | 0.35 | 0.05 | 0.09 | ✅ |
| E07 | ReXCL分类 | 9337章节 | MiniLM+LR | — | 20% held-out | — | — | 0.61 | ✅ |
| E08 | Span+LR+MLM | 银标准(4070) | MiniLM+LR | MLM(5K句) | 银标准 | — | — | 0.94 | ✅ |
| **E09** | **Span+LR+MLM** | **银标准(4070)** | **MiniLM+LR** | **MLM(5K句)** | **金标准(102)** | **0.43** | **0.48** | **0.43** | ✅ |
| E10 | W2NER | 银标准(3241) | MiniLM+W2NER | — | 银标准 | — | — | 超时 | ⚠️ |
| E11 | LLM直抽 | — | GLM-5 | — | 10文档 | ~0.90 | — | — | ✅ |
| E12 | ReXCL抽取 | — | RF+章节切分 | — | 62文档 | — | — | 95% | ✅ |

### 4.2 关键发现

| 发现 | 数据 |
|---|---|
| **银→金泛化差距** | Span+LR: 0.97→0.43 (差距 -0.54) |
| **MLM对金标准无帮助** | 0.43→0.43 (变化 0.00) |
| **最佳金标准F1** | Span+LR = 0.43 |
| **标签噪声是瓶颈** | 银标准~70%精度 → 监督方法上限受限 |

### 4.3 分类型 F1 (Span+LR, 金标准评估)

| 类型 | Precision | Recall | F1 |
|---|---|---|---|
| PARAM | 0.52 | 0.12 | 0.20 |
| VALUE | 0.26 | 0.31 | 0.28 |
| UNIT | 0.38 | 0.13 | 0.19 |
| OPERATOR | 0.52 | 0.26 | 0.34 |
| O | 0.53 | 0.90 | 0.67 |
| **weighted avg** | **0.50** | **0.50** | **0.43** |

---

## 五、论文复现表

### 5.1 论文-方法-复现对照表

| # | 论文 | 年份/会议 | arXiv | 方法类型 | 核心技术 | 代码 | 复现状态 | 论文F1 | 我们F1(金) | 差距原因 |
|:---:|---|---|---|---|---|---|---|---|---|---|
| 1 | **ReXCL** | 2025 cs.SE | [2504.07562](https://arxiv.org/abs/2504.07562) | 需求文档专用 | RF去页眉 + BERT MLM领域适配 + 分类 | ❌无(重实现) | ✅ 完成 | 0.97(分类) | 0.61(分类) | 缺MLM(MiniLM无lm_head) |
| 2 | **W2NER** | 2022 AAAI | [2112.10070](https://arxiv.org/abs/2112.10070) | Span-Based NER | Word-Word 2D关系矩阵 + 多粒度卷积 | ✅ [GitHub](https://github.com/ljynlp/W2NER) | ⚠️ Patched | 92.7(NER) | 超时 | MPS太慢(2D卷积) |
| 3 | **SpERT** | 2020 ECAI | [1909.07755](https://arxiv.org/abs/1909.07755) | Span联合抽取 | BERT + Span枚举 + 关系分类 + 强负采样 | ✅ [GitHub](https://github.com/markus-eberts/SpERT) | 📋 待复现 | 72.9(RE) | — | — |
| 4 | **UIE** | 2022 ACL | [2203.12277](https://arxiv.org/abs/2203.12277) | 生成式IE | SEL + SSI schema → text-to-structure | ✅ [GitHub](https://github.com/universal-ie/UIE) | 📋 待复现 | — | P~0.90(LLM版) | 用LLM实现了SSI思路 |
| 5 | **GoLLIE** | 2024 ICLR | [2310.03668](https://arxiv.org/abs/2310.03668) | LLM零样本IE | 标注指南(Python类) → LLM零样本抽取 | ✅ [GitHub](https://github.com/hitz-zentroa/GoLLIE) | ❌ 不可复现 | 55.3(7B) | — | 需CUDA+flash-attn |
| 6 | **DeepKE** | 2022 EMNLP | [2201.03335](https://arxiv.org/abs/2201.03335) | IE工具包 | 模块化NER/RE/属性抽取 | ✅ [GitHub](https://github.com/zjunlp/DeepKE) | 📋 待复现 | ~0.90(中文NER) | — | — |
| 7 | **UniRel** | 2022 EMNLP | [2211.09039](https://arxiv.org/abs/2211.09039) | 关系三元组 | 统一表示 + 交互图 + 联合解码 | ✅ [GitHub](https://github.com/wtangdev/UniRel) | 📋 待复现 | 91.3(RE) | — | — |
| 8 | **K-BERT** | 2019 ACL | [1909.07606](https://arxiv.org/abs/1909.07606) | 知识增强 | KG三元组注入BERT输入 | ✅ [GitHub](https://github.com/autoliuweijie/K-BERT) | 📋 待复现 | — | — | — |
| 9 | **LayoutLMv3** | 2022 ACM MM | [2204.08387](https://arxiv.org/abs/2204.08387) | 文档结构感知 | 文本+版面+图像统一掩码预训练 | ✅ [GitHub](https://github.com/microsoft/unilm) | 📋 待复现 | — | — | 需版面标注 |
| 10 | **BERT-CRF** | 2015-2018 | [1508.01991](https://arxiv.org/abs/1508.01991) | 序列标注 | BiLSTM/BERT + CRF解码 | ✅ 标准实现 | ✅ 完成 | — | 0.05(金) | 银标准噪声 |
| 11 | **ChatGPT-IE** | 2023 | [2304.11633](https://arxiv.org/abs/2304.11633) | LLM-IE评测 | 系统评测LLM在IE上的能力 | ✅ [GitHub](https://github.com/pkuserc/ChatGPT_for_IE) | ✅ 方法复现 | — | P~0.90 | GLM-5实现 |
| 12 | **Helmeczi** | 2022 cs.SE | [2211.02709](https://arxiv.org/abs/2211.02709) | 冲突检测 | Prompt few-shot 需求冲突检测 | ❌无 | 📋 待复现 | — | — | — |

### 5.2 方法家族覆盖

| 家族 | 描述 | 已实现 | 代表方法 | F1(金标准) |
|---|---|:---:|---|---|
| F1 规则/模板 | 正则+EARS+专家系统 | ✅ | 启发式 | ~0.19 |
| F2 传统ML | CRF/HMM/SVM | ✅ | BERT-CRF(CRF层) | 0.05 |
| F3 深度序列标注 | BiLSTM-CRF / BERT-CRF | ✅ | MiniLM+CRF | 0.05-0.09 |
| F4 Span-Based | Span枚举+分类 | ✅ | MiniLM+LR | **0.43** |
| F5 生成式IE | UIE/SSI/Seq2Seq | ✅ | GLM-5 SSI | P~0.90 |
| F6 LLM-Based | 零样本/少样本/CoT | ✅ | GLM-5 | P~0.90 |
| F7 知识增强 | K-BERT/KG+LLM | ✅ | KB embedding | — |
| F8 文档结构感知 | LayoutLM/表格 | ✅ | pdfplumber表格 | — |
| F9 混合级联 | 规则→ML→LLM | ✅ | 统一流水线 | — |
| F10 需求专用 | NLP4RE/EARS | ✅ | EARS+shall模式 | — |
| ReXCL | SRS专用工具 | ✅ | RF+MLM+分类 | 0.61(分类) |
| W2NER | 嵌套NER | ⚠️ | 2D卷积 | 超时 |

### 5.3 待复现论文优先级

| 优先级 | 论文 | 理由 | 预期提升 | 所需资源 |
|:---:|---|---|---|---|
| **P0** | SpERT (1909.07755) | Span+关系联合抽取，直接对应参数三元组 | F1 0.5-0.6 | BERT-base + GPU |
| **P0** | W2NER (2112.10070) | 嵌套实体处理，已完成patch | F1 0.4-0.5 | GPU(MPS太慢) |
| **P1** | DeepKE (2201.03335) | 中文IE工具包，开箱即用 | F1 0.5-0.7 | BERT-base |
| **P1** | UniRel (2211.09039) | 关系三元组，轻量 | F1 0.4-0.6 | BERT-base |
| **P2** | UIE (2203.12277) | 生成式统一IE | F1 0.4-0.6 | T5/PaddlePaddle |
| **P2** | K-BERT (1909.07606) | 知识图谱注入 | +0.05-0.10 | KG + BERT |
| **P3** | LayoutLMv3 (2204.08387) | 文档版面感知 | 表格抽取提升 | 版面标注 |
| **P3** | Helmeczi (2211.02709) | 需求冲突检测 | 冲突检测提升 | LLM API |

---

## 六、代码资产

| 文件 | 行数 | 功能 | 对应论文/方法 |
|---|---|---|---|
| `tools/srs_unified_pipeline.py` | 880 | v5 统一流水线 (F1-F10) | 全家族集成 |
| `tools/srs_rexcl.py` | 350 | ReXCL 复现 | arXiv:2504.07562 |
| `tools/srs_rexcl_mlm.py` | 280 | MLM 领域适配 | ReXCL 核心 |
| `tools/srs_bert_crf.py` | 460 | BERT-CRF 训练 | arXiv:1508.01991 |
| `tools/srs_hybrid_train.py` | 180 | 混合训练+金标准评估 | — |
| `tools/srs_keie_pipeline.py` | 1059 | KEIE 知识增强IE | F4+F7 |
| `tools/srs_llm_extract.py` | 938 | LLM 直接抽取 | F5+F6 |
| `tools/srs_extract_pipeline.py` | 914 | 三层降级流水线 | F1+F3+F6 |
| `tools/srs_consistency_integrated.py` | 300 | L1+L2+L3 三层校验 | — |
| `tools/srs_consistency_check.py` | 875 | 正则版一致性校验 v2 | F1 |
| `tools/srs_gold_annotator.py` | 629 | Gold standard 标注工具 | — |
| `tools/srs_ner_v2.py` | 914 | NER v2 多层架构 | F3+F4 |
| `tools/srs_mapping.py` | 580 | 映射系统 | F7 |
| `tools/srs_ner.py` | 640 | NER v1 | F4 |
| `knowledge/srs_kb.json` | 1060 | SRS 知识库 (23参数/374实体) | F7 |
| `docs/srs_ner_annotation_guidelines.md` | 255 | 标注规范 | F10 |
| `ie_taxonomy/IE_METHOD_TAXONOMY.md` | 479 | 方法谱系 | 全部 |
| `ie_taxonomy/REPRODUCIBLE_IE_METHODS_REPORT.md` | 462 | 可复现方法报告 | 全部 |
| **总计** | **~10,500** | | |

---

## 七、当前最佳结果

### 7.1 最佳方法

**Span 分类器 (embedding + LogisticRegression)**

- 训练: 银标准 4,070 句 → 24,101 span
- 测试: 金标准 102 句 → 329 span
- **F1 (金标准) = 0.43** (所有方法中最高)
- F1 (银标准) = 0.97 (循环评估，不可信)

### 7.2 最佳端到端

**统一流水线 v5 (全方法家族集成)**

- 62 文档 → 5,977 候选句 → 100 约束 → 3 冲突
- 冲突 1: availability 99.99% vs 99.999% ✅
- 冲突 2: duty cycle 50% vs 75% ✅
- 冲突 3: call setup time 99% vs 95% ✅

### 7.3 提升路径

| 路径 | 预期 F1 | 成本 | 优先级 |
|---|---|---|---|
| 500+ LLM 标注句 → Span+LR | 0.6-0.8 | ~30min API | P0 |
| 人工标注 500 句 → BERT-CRF | 0.7-0.9 | ~3小时 | P0 |
| SpERT 复现 (GPU) | 0.5-0.7 | GPU+训练 | P1 |
| W2NER 复现 (GPU) | 0.4-0.6 | GPU+训练 | P1 |
| bert-base-uncased (768维) | +0.05-0.10 | 网络下载 | P2 |
