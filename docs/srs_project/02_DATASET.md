# 02 - 数据集详解

## 原始数据: PURE数据集

- **来源**: https://zenodo.org/records/1414117
- **内容**: 62个真实SRS文档(1995-2010年, 含PDF/DOC/HTML)
- **位置**: `data/srs_requirements/req/`
- **统计**: 2,833页 / 460万字 / 1,845个表格 / 14,610张图片

### 解析JSON格式

pdfplumber解析后每个PDF变成一个JSON:

```json
{
  "file": "0000 - gamma j.pdf",
  "pages": [
    {"page": 1, "text": "Software Requirements\nSpecification (SRS)..."},
    {"page": 2, "text": "..."}
  ],
  "tables": [
    {"page": 10, "rows": 4, "cols": 7, "data": [["", ""], ...]}
  ]
}
```

## 银标准(训练数据)

- **位置**: `data/srs_requirements/bert_crf/silver_standard.json`
- **数量**: 4,070句, 5.2MB
- **标注方式**: 用正则+embedding规则自动标注(无人工)
- **质量**: ~70%精度(规则会犯错)
- **用途**: 训练BERT-CRF/Span分类器

### BIO标注格式

```json
{
  "tokens": ["The", "system", "response", "time", "shall", "not", "exceed", "50", "ms"],
  "tags": ["O", "O", "B-PARAM", "I-PARAM", "B-OPERATOR", "I-OPERATOR", "I-OPERATOR", "B-VALUE", "B-UNIT"],
  "file": "0000 - gamma j.pdf"
}
```

### 4种实体类型

| 类型 | 含义 | 例子 |
|---|---|---|
| PARAM | 参数名 | response time, availability |
| VALUE | 数值 | 50, 99.99 |
| UNIT | 单位 | ms, %, MHz |
| OPERATOR | 运算符 | shall not exceed, at least |

完整标签集(9个): O, B-PARAM, I-PARAM, B-VALUE, I-VALUE, B-UNIT, I-UNIT, B-OPERATOR, I-OPERATOR

## 金标准(评估数据)

- **位置**: `data/srs_requirements/bert_crf/gold_standard_fixed.json`
- **数量**: 100句, 93KB
- **标注方式**: GLM-5直接输出token-level标签
- **质量**: ~90%精度, 4%可疑率

### 金标准修复历史

```
旧金标准: 102句, 27%可疑率
  问题: LLM输出字符偏移与spaCy分词不对齐
  表现: "and"被标为B-PARAM, ","被标为B-VALUE

修复方法: 改为LLM直接输出{token, label}对
  不再经过字符偏移转换

修复后: 100句, 4%可疑率
```

## 知识库

- **位置**: `knowledge/srs_kb.json`
- **构建方式**: 人工定义(非自动化)

### 内容

| 组件 | 数量 | 说明 |
|---|---|---|
| 参数类型 | 23个 | response_time, throughput, availability... |
| 参数同义词 | 148条 | latency=RTT=response time |
| 接口类型 | 13个 | RS232, RS422, CAN, TCP, UDP... |
| 接口变体 | 40条 | RS232=RS-232=RS 232 |
| 单位 | 67个(10维度) | time/frequency/storage/percentage... |
| 运算符 | 6种 | <=, >=, <, >, =, ~= |
| 值范围 | 23个参数 | response_time: 0.001~600 |
| 互斥表 | 接口对 | RS232↔RS422, TCP↔UDP |
| 单位换算 | 67条 | ms→s: ×0.001, MHz→Hz: ×1000000 |

### 局限

- 手工构建, 覆盖不全
- 无自动化构建流水线
- 遇到新参数类型无法自动识别

## 知识图谱

- **位置**: `data/srs_requirements/knowledge_graph.json`
- **节点**: 1,580个(17文档+17参数+1,459章节+12接口+30冲突)
- **边**: 4,800条(定义/包含/声明/共享/冲突)

### 边类型

| 边类型 | 含义 | 数量 |
|---|---|---|
| defines | 文档→参数(文档定义了某参数) | 30 |
| contains | 文档→章节(文档包含某章节) | 4,664 |
| declares | 文档→接口(文档声明了某接口) | 55 |
| shares_param | 文档↔文档(两文档共享某参数) | 21 |
| has_conflict | 文档→冲突(文档存在冲突) | 30 |
