# SRS 需求文档不一致检测系统 — 完整技术文档与操作手册

> **版本**: v5.0 | **日期**: 2026-07-22 | **作者**: 葛宣成
> **项目根**: [`data_clean/`](.) (data-juicer 项目目录)
> **代码**: [`tools/srs_*.py`](tools/) (17个文件, 10,818行)
> **数据**: [`data/srs_requirements/`](data/srs_requirements/)
> **知识库**: [`knowledge/srs_kb.json`](knowledge/srs_kb.json)

---

## 1. 项目概述

从62个SRS PDF文档中检测五层不一致性。唯一可信真矛盾：

> **availability 99.99% vs 99.999%** (gamma j.pdf, NLI置信度0.95)

---

## 2. 与 data-juicer 的关系

```
data_clean/                           ← data-juicer 项目根
├── data_juicer/                      ← data-juicer 核心
├── tools/srs_*.py                    ← ★ 我们的代码 (17个文件)
├── knowledge/srs_kb.json             ← ★ SRS知识库
├── data/srs_requirements/            ← ★ SRS数据
│   ├── req/                          ← 62个原始PDF
│   ├── parsed/                       ← 62个解析JSON
│   ├── bert_crf/                     ← 训练数据
│   ├── keie_output/                  ← 检测结果
│   ├── images_hd/                    ← 页面截图
│   └── visualization/                ← 可视化图表
└── docs/                             ← 文档
```

---

## 3. 数据集

### 3.1 原始PDF → 解析JSON

原始PDF: [`data/srs_requirements/req/`](data/srs_requirements/req/) (62个)

解析后JSON示例 ([`data/srs_requirements/parsed/0000 - gamma j.json`](data/srs_requirements/parsed/0000%20-%20gamma%20j.json)):

```json
{
  "file": "0000 - gamma j.pdf",
  "pages": [
    {"page": 1, "text": "Software Requirements\nSpecification (SRS)\nGroup Name GAMMA-J..."},
    ...
  ],
  "tables": [
    {"page": 10, "rows": 4, "cols": 7, "data": [["", "", ...], ...]}
  ]
}
```

### 3.2 银标准 (训练数据)

文件: [`data/srs_requirements/bert_crf/silver_standard.json`](data/srs_requirements/bert_crf/silver_standard.json)

```json
{
  "tokens": ["The", "system", "response", "time", "shall", "not", "exceed", "50", "ms"],
  "tags": ["O", "O", "B-PARAM", "I-PARAM", "B-OPERATOR", "I-OPERATOR", "I-OPERATOR", "B-VALUE", "B-UNIT"],
  "file": "0000 - gamma j.pdf"
}
```

- 数量: 4,070句
- 标注方式: 正则+embedding规则自动标注
- 质量: ~70%精度

### 3.3 金标准 (评估数据)

文件: [`data/srs_requirements/bert_crf/gold_standard_fixed.json`](data/srs_requirements/bert_crf/gold_standard_fixed.json)

```json
{
  "tokens": ["Data", "to", "enable", "investigation", "of", "accidents", "need", "only", "be", "stored", "for", "at", "least", "24", "hours"],
  "tags": ["O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "O", "B-OPERATOR", "I-OPERATOR", "B-VALUE", "B-UNIT"],
  "text": "Data to enable investigation of accidents need only be stored for at least 24 hours"
}
```

- 数量: 100句
- 标注方式: GLM-5直接输出token-level标签
- 质量: ~90%精度, 4%可疑率

### 3.4 知识库

文件: [`knowledge/srs_kb.json`](knowledge/srs_kb.json)

```json
{
  "param_dictionary": {
    "response_time": {
      "canonical_en": "response time",
      "synonyms_en": ["response time", "latency", "delay", "RTT", ...],
      "default_unit": "ms",
      "value_range": {"min": 0.001, "max": 600, "unit_hint": "time"}
    },
    "availability": {
      "canonical_en": "availability",
      "synonyms_en": ["availability", "uptime", "reliability", "MTBF", ...],
      "default_unit": "%",
      "value_range": {"min": 0, "max": 100, "unit_hint": "percentage"}
    }
  },
  "interface_dictionary": {
    "RS232": {"variants": ["RS232", "RS-232", "RS 232"], "mutex_with": ["RS422"]},
    "TCP": {"variants": ["TCP"], "mutex_with": ["UDP"]}
  }
}
```

- 23个参数类型, 148条同义词
- 13个接口类型, 含互斥表
- 67个单位, 9个维度, 含换算表

---

## 4. 系统架构

```
62 PDF → pdfplumber解析 → 预过滤(候选句) → 参数抽取 → 知识库验证 → 冲突检测 → 报告
                                         ↑                    ↑
                                    F1正则/F4 Span/F5 LLM    F7 KB
                                    F3 BERT-CRF              F8 表格
```

---

## 5. 五层检测详解

### 5.1 语法不一致

#### 章节缺失检测

代码: [`tools/srs_rexcl.py`](tools/srs_rexcl.py) → `ReXCLExtractor.extract()`

```python
# 核心流程
class ReXCLExtractor:
    def extract(self, doc_data):
        # 1. RF分类器去页眉页脚
        self._train_header_footer_detector(all_lines, pages)
        # 2. 正则切分章节
        for m in SECTION_RE.finditer(line):
            current_section = {"section_number": m.group(1), "heading": m.group(2)}
        # 3. 模板对标
        for req_num, req_keywords in REQUIRED_SECTIONS:
            if not found: conflicts.append("缺少标准章节")
```

结果: [`data/srs_requirements/rexcl/extracted_sections.json`](data/srs_requirements/rexcl/extracted_sections.json)
- 62文档 → 9,337个结构化章节
- 36条章节缺失

具体例子:
```
文件: 0000 - cctns.pdf
问题: 缺少第2章 (overall description/总体描述)
```

#### 引用断裂检测

代码: [`tools/srs_consistency_check.py`](tools/srs_consistency_check.py) → `check_syntax()`

结果: 177条引用断裂

```
文件: 2007 - mdot.pdf
引用: '§ 4.1' → 目标'4.1'不存在
上下文: ...ConOps § 4.1 primary purposes of...
```

### 5.2 语义不一致

#### NLI矛盾检测 (最有效方法)

技术: SummaC (arXiv:2111.09525)

结果: [`data/srs_requirements/keie_output/nli_complex_results.json`](data/srs_requirements/keie_output/nli_complex_results.json)

**唯一真矛盾**:
```json
{
  "nli_label": "contradiction",
  "nli_reason": "Both sentences specify different availability percentages (99.999% vs 99.99%) for the same system",
  "nli_confidence": 0.95,
  "param": "availability",
  "v1": 99.999, "v2": 99.99,
  "s1": "Have an availability of 99.999%",
  "s2": "The system shall have an availability of 99.99%."
}
```

**NLI排除的假阳性**:
```json
{
  "nli_label": "neutral",
  "nli_reason": "The sentences address different topics and different project phases. Sentence 1 discusses production...",
  "param": "jitter", "v1": 2.0, "v2": 1.0
}
```

#### Z3约束求解

代码: 内嵌在实验脚本中

```python
from z3 import *
x = Real("availability_gamma_j")
solver = Solver()
solver.add(x == 99.999)   # 约束1: availability = 99.999%
solver.add(x == 99.99)    # 约束2: availability = 99.99%
result = solver.check()   # → unsat (矛盾!)
```

结果: 8组UNSAT, 但经审计**全部是假阳性**:
- `response_time=238` → 实际是文档编号"TCS 238"
- `memory_size=1472` → 实际是"MIL-STD 1472"标准号
- `duty_cycle=100` → 实际是"DutyLo := 100"变量定义
- `processing_time=500` → 实际是"500,000 items per year"
- `beep_frequency=500/700` → 实际是"alternating 500Hz and 700Hz"(交替, 非矛盾)

### 5.3 图片-文本不一致

代码: [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py)

6个检测器结果: [`data/srs_requirements/images_hd/full_results.json`](data/srs_requirements/images_hd/full_results.json)

```json
{
  "file": "2001 - elsfork.pdf",
  "page": 19,
  "checks": {
    "floca": {"has_diagram": true, "nodes": 14, "edges": 11, "issue_count": 29},
    "ve": {"total": 2, "contradiction": 1, "overall": "partially_consistent"},
    "chartve": {"fig_vals": 10, "conflicts": 0, "no_conflict": true},
    "tracellm": {"reqs": 2, "elements": 9, "orphans": 0, "phantoms": 5}
  }
}
```

**图文矛盾例子**:
```
文件: 2001 - elsfork.pdf p19
Figure 1: 文字说"文档结构图" → 图片实际是"风力发电通信系统概览图"
检测: Visual Entailment → contradiction
```

### 5.4 知识图谱

文件: [`data/srs_requirements/knowledge_graph.json`](data/srs_requirements/knowledge_graph.json)

```json
{
  "nodes": [
    {"id": "0000 - gamma j.pdf", "type": "document"},
    {"id": "availability", "type": "parameter", "name": "availability"},
    {"id": "sec_1.4", "type": "section", "title": "Project Scope"},
    {"id": "RS232", "type": "interface"},
    {"id": "conflict_gamma_j_avai", "type": "conflict", "param": "availability"}
  ],
  "links": [
    {"source": "0000 - gamma j.pdf", "target": "availability", "relation": "defines"},
    {"source": "0000 - gamma j.pdf", "target": "sec_1.4", "relation": "contains"},
    {"source": "0000 - gamma j.pdf", "target": "conflict_gamma_j_avai", "relation": "has_conflict"}
  ]
}
```

- 1,580个节点 (17文档 + 17参数 + 1,459章节 + 12接口 + 30冲突)
- 4,800条边

---

## 6. 代码清单

| 文件 | 行数 | 功能 | 链接 |
|---|---|---|---|
| srs_keie_pipeline.py | 1077 | 知识增强IE流水线v4 | [`tools/srs_keie_pipeline.py`](tools/srs_keie_pipeline.py) |
| srs_image_text_check.py | 871 | 图片-文本检测(6篇论文) | [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py) |
| srs_extract_pipeline.py | 914 | 三层降级流水线v3 | [`tools/srs_extract_pipeline.py`](tools/srs_extract_pipeline.py) |
| srs_unified_pipeline.py | 871 | 统一流水线v5 | [`tools/srs_unified_pipeline.py`](tools/srs_unified_pipeline.py) |
| srs_llm_extract.py | 938 | LLM直接抽取 | [`tools/srs_llm_extract.py`](tools/srs_llm_extract.py) |
| srs_consistency_check.py | 875 | 正则版校验v2 | [`tools/srs_consistency_check.py`](tools/srs_consistency_check.py) |
| srs_ner_v2.py | 914 | NER v2多层架构 | [`tools/srs_ner_v2.py`](tools/srs_ner_v2.py) |
| srs_rexcl.py | 530 | ReXCL复现 | [`tools/srs_rexcl.py`](tools/srs_rexcl.py) |
| srs_mapping.py | 633 | 映射系统 | [`tools/srs_mapping.py`](tools/srs_mapping.py) |
| srs_ner.py | 640 | NER v1 | [`tools/srs_ner.py`](tools/srs_ner.py) |
| srs_gold_annotator.py | 629 | Gold standard标注 | [`tools/srs_gold_annotator.py`](tools/srs_gold_annotator.py) |
| srs_bert_crf.py | 470 | BERT-CRF训练 | [`tools/srs_bert_crf.py`](tools/srs_bert_crf.py) |
| srs_rexcl_mlm.py | 303 | MLM领域适配 | [`tools/srs_rexcl_mlm.py`](tools/srs_rexcl_mlm.py) |
| srs_consistency_integrated.py | 315 | L1+L2+L3校验 | [`tools/srs_consistency_integrated.py`](tools/srs_consistency_integrated.py) |
| srs_llm_annotated_train.py | 411 | LLM标注训练 | [`tools/srs_llm_annotated_train.py`](tools/srs_llm_annotated_train.py) |
| srs_hybrid_train.py | 167 | 混合训练 | [`tools/srs_hybrid_train.py`](tools/srs_hybrid_train.py) |
| srs_llm_large_train.py | 260 | 大规模LLM标注 | [`tools/srs_llm_large_train.py`](tools/srs_llm_large_train.py) |

---

## 7. 操作手册

```bash
# 0. 环境
export WQ_API_KEY="n6nbxgo0fk4g48dpdylw51plxjnv8smp6ml7"
export KMP_DUPLICATE_LIB_OK=TRUE

# 1. 语法检测
python3 tools/srs_consistency_integrated.py
# → data/srs_requirements/keie_output/conflict_report.json

# 2. 参数抽取
python3 tools/srs_keie_pipeline.py --docs 0
# → data/srs_requirements/keie_output/keie_results.json

# 3. 图片-文本检测 (需多模态API)
python3 tools/srs_image_text_check.py
# → data/srs_requirements/images_hd/full_results.json

# 4. BERT-CRF训练
python3 tools/srs_bert_crf.py
# → data/srs_requirements/bert_crf/silver_standard.json

# 5. ReXCL复现
python3 tools/srs_rexcl.py
# → data/srs_requirements/rexcl/extracted_sections.json
```

---

## 8. 可视化图集

### 8.1 检测结果总览

![检测结果总览](data/srs_requirements/visualization/overview.png)

### 8.2 唯一真矛盾详情

![真矛盾详情](data/srs_requirements/visualization/real_conflict.png)

### 8.3 方法对比

![方法对比](data/srs_requirements/visualization/method_comparison.png)

### 8.4 具体例子表格

![具体例子](data/srs_requirements/visualization/examples_table.png)

### 8.5 论文复现状态

![论文复现](data/srs_requirements/visualization/paper_reproduction.png)

### 8.6 SRS文档原始页面

#### gamma j.pdf 第5页 (含Figure 2.1上下文图)
![gamma j p5](data/srs_requirements/images_hd/0000%20-%20gamma%20j/page_5.png)

#### TCS 第19页 (状态图: STARTUP→OPERATIONS→SHUTDOWN)
![tcs p19](data/srs_requirements/images_hd/1999%20-%20tcs/page_19.png)

#### TCS 第20页 (启动模式图)
![tcs p20](data/srs_requirements/images_hd/1999%20-%20tcs/page_20.png)

#### elsfork 第19页 (风电系统图, 图文矛盾)
![elsfork p19](data/srs_requirements/images_hd/2001%20-%20elsfork/page_19.png)

#### telescope 第13页 (望远镜CCD图)
![telescope p13](data/srs_requirements/images_hd/2001%20-%20telescope/page_13.png)

---

## 9. 论文复现

| # | 论文 | arXiv链接 | 代码 | 结果 |
|:---:|---|---|---|---|
| 1 | ReXCL | [arXiv:2504.07562](https://arxiv.org/abs/2504.07562) | [`tools/srs_rexcl.py`](tools/srs_rexcl.py) | 章节9337, F1=0.61 |
| 2 | BERT-CRF | [arXiv:1508.01991](https://arxiv.org/abs/1508.01991) | [`tools/srs_bert_crf.py`](tools/srs_bert_crf.py) | F1(金)=0.05 |
| 3 | Span+LR | [arXiv:1909.07755](https://arxiv.org/abs/1909.07755) | [`tools/srs_keie_pipeline.py`](tools/srs_keie_pipeline.py) | F1(金)=0.48 |
| 4 | UIE | [arXiv:2203.12277](https://arxiv.org/abs/2203.12277) | [`tools/srs_llm_extract.py`](tools/srs_llm_extract.py) | P~0.90 |
| 5 | FloCA | [arXiv:2602.14035](https://arxiv.org/abs/2602.14035) | [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py) | 37个路径问题 |
| 6 | DFD规则 | [arXiv:1011.0278](https://arxiv.org/abs/1011.0278) | [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py) | 4个规则违反 |
| 7 | Visual Entailment | [arXiv:1901.06706](https://arxiv.org/abs/1901.06706) | [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py) | 1个图文矛盾 |
| 8 | ChartVE | [arXiv:2312.10160](https://arxiv.org/abs/2312.10160) | [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py) | 0个冲突 |
| 9 | Z3 Solver | [GitHub](https://github.com/Z3Prover/z3) | 内嵌 | 0个真矛盾 |
| 10 | MLM适配 | [arXiv:2504.07562](https://arxiv.org/abs/2504.07562) | [`tools/srs_rexcl_mlm.py`](tools/srs_rexcl_mlm.py) | 无提升 |
| 11 | NLI/SummaC | [arXiv:2111.09525](https://arxiv.org/abs/2111.09525) | 内嵌 | 1个真矛盾 |

---

## 10. 关键文件路径速查

### 数据文件
| 文件 | 说明 | 路径 |
|---|---|---|
| 原始PDF | 62个SRS文档 | [`data/srs_requirements/req/`](data/srs_requirements/req/) |
| 解析JSON | 62个 | [`data/srs_requirements/parsed/`](data/srs_requirements/parsed/) |
| 银标准 | 4070句训练数据 | [`data/srs_requirements/bert_crf/silver_standard.json`](data/srs_requirements/bert_crf/silver_standard.json) |
| 金标准 | 100句评估数据 | [`data/srs_requirements/bert_crf/gold_standard_fixed.json`](data/srs_requirements/bert_crf/gold_standard_fixed.json) |
| 知识库 | 23参数/374实体 | [`knowledge/srs_kb.json`](knowledge/srs_kb.json) |
| 知识图谱 | 1580节点/4800边 | [`data/srs_requirements/knowledge_graph.json`](data/srs_requirements/knowledge_graph.json) |

### 结果文件
| 文件 | 说明 | 路径 |
|---|---|---|
| KEIE抽取 | 60条约束 | [`data/srs_requirements/keie_output/keie_results.json`](data/srs_requirements/keie_output/keie_results.json) |
| NLI矛盾 | 6条矛盾 | [`data/srs_requirements/keie_output/nli_complex_results.json`](data/srs_requirements/keie_output/nli_complex_results.json) |
| 三层冲突报告 | 220条冲突 | [`data/srs_requirements/keie_output/conflict_report.json`](data/srs_requirements/keie_output/conflict_report.json) |
| 图片-文本检测 | 5页6检测器 | [`data/srs_requirements/images_hd/full_results.json`](data/srs_requirements/images_hd/full_results.json) |
| ReXCL章节 | 9337章节 | [`data/srs_requirements/rexcl/extracted_sections.json`](data/srs_requirements/rexcl/extracted_sections.json) |

### 可视化
| 文件 | 说明 | 路径 |
|---|---|---|
| 检测总览 | 五层柱状图 | [`data/srs_requirements/visualization/overview.png`](data/srs_requirements/visualization/overview.png) |
| 真矛盾详情 | availability对比 | [`data/srs_requirements/visualization/real_conflict.png`](data/srs_requirements/visualization/real_conflict.png) |
| 方法对比 | Span vs LLM vs NLI | [`data/srs_requirements/visualization/method_comparison.png`](data/srs_requirements/visualization/method_comparison.png) |
| 例子表格 | 12个具体例子 | [`data/srs_requirements/visualization/examples_table.png`](data/srs_requirements/visualization/examples_table.png) |
| 论文复现 | 11篇论文状态 | [`data/srs_requirements/visualization/paper_reproduction.png`](data/srs_requirements/visualization/paper_reproduction.png) |

### 文档
| 文件 | 说明 | 路径 |
|---|---|---|
| 主交接文档 | 五层检测+论文 | [`docs/INCONSISTENCY_FINAL_V2.md`](docs/INCONSISTENCY_FINAL_V2.md) |
| 标注规范 | 7实体/6关系/7错误 | [`docs/srs_ner_annotation_guidelines.md`](docs/srs_ner_annotation_guidelines.md) |
| 方法谱系 | 10大家族479行 | [`ie_taxonomy/IE_METHOD_TAXONOMY.md`](ie_taxonomy/IE_METHOD_TAXONOMY.md) |
| 可复现方法 | TOP5论文462行 | [`ie_taxonomy/REPRODUCIBLE_IE_METHODS_REPORT.md`](ie_taxonomy/REPRODUCIBLE_IE_METHODS_REPORT.md) |
| 图文文献 | 21篇论文 | [`image_text_consistency_lit_review.md`](image_text_consistency_lit_review.md) |

---

## 11. 核心代码片段

### 11.1 KEIE Pipeline 核心流程

```python
# tools/srs_keie_pipeline.py
class KEIEPipeline:
    def process_document(self, doc_data):
        # 1. 预过滤
        candidates = self.prefilter.filter(full_text)
        
        # 2. Span检测 (F4)
        entities = self.span_detector.detect(sentence)
        
        # 3. 关系抽取 (依赖解析)
        raw_constraints = self.relation_extractor.extract(sentence, entities)
        
        # 4. KB验证 (F7)
        validated = self.validator.validate(rc, file_name)
        
        # 5. LLM验证低置信度 (F6)
        if self.llm_verifier and low_confidence:
            self.llm_verifier.verify_batch(low_confidence)
```

### 11.2 图片-文本检测核心

```python
# tools/srs_image_text_check.py
class FloCAChecker:
    def check_path_consistency(self, diagram):
        G = nx.DiGraph()
        for node in nodes: G.add_node(node["id"])
        for edge in edges: G.add_edge(edge["source"], edge["target"])
        
        # 可达性
        for start in initial:
            reachable = set(nx.descendants(G, start))
            unreachable = all_nodes - reachable - {start}
        
        # 死锁
        for node in G.nodes():
            if node not in finals and G.out_degree(node) == 0:
                issues.append("死锁节点")
```

### 11.3 Z3约束求解

```python
from z3 import *
x = Real("availability")
solver = Solver()
solver.add(x == 99.999)
solver.add(x == 99.99)
result = solver.check()  # → unsat
```

### 11.4 NLI矛盾检测

```python
# 发送给GLM-5
prompt = f"""Sentence 1: "{s1}"
Sentence 2: "{s2}"
Do these sentences contradict each other?
Return: {{"label": "contradiction"/"neutral"/"entailment", "reason": "..."}}"""
```
