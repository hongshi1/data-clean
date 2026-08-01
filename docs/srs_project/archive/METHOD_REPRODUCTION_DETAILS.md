# 各方法复现详情 — 代码与流程

> 每个方法附核心代码片段和流程说明

---

## 方法1: ReXCL — 章节抽取+分类+MLM适配

**论文**: [arXiv:2504.07562](https://arxiv.org/abs/2504.07562) (Bosch Research, 2025)
**代码**: [`tools/srs_rexcl.py`](tools/srs_rexcl.py)
**复现内容**: RF去页眉 + 正则切章节 + BERT分类 + MLM领域适配

### 核心流程

```python
# Step 1: Random Forest去页眉页脚
class ReXCLExtractor:
    SECTION_RE = re.compile(r'^(\d+\.?\d*\.?\d*)\s+([A-Z][^\n]{2,80})', re.MULTILINE)
    
    def extract(self, doc_data):
        # 统计文本频率(高频短文本=页眉页脚)
        for line in all_lines:
            self.text_frequency[line] += 1
        
        # RF分类器(频率+位置特征)
        self.header_footer_clf = RandomForestClassifier(n_estimators=50)
        self.header_footer_clf.fit(features, labels)  # 高频+短文本=页眉
        
        # 正则切分章节
        for m in SECTION_RE.finditer(line):
            if self._is_header_footer(line):  # RF判断
                continue
            current_section = {
                "section_number": m.group(1),    # "3.2.1"
                "heading": m.group(2).strip(),   # "Functional Requirements"
                "texts": [],                      # 章节正文
            }

# Step 2: 章节分类(INFO/HEADER/FUNC_REQ/NON_FUNC_REQ)
    def _classify_section(self, section):
        heading = section["heading"].lower()
        if "functional requirement" in heading: return "FUNC_REQ"
        if "performance" in heading: return "NON_FUNC_REQ"
        # ...

# Step 3: MLM领域适配(ReXCL核心创新)
class DomainAdaptiveMLM:
    def train(self, corpus, epochs=3):
        # 在69K句SRS语料上做Masked Language Model预训练
        for epoch in range(epochs):
            for batch in loader:
                # 15%的token被mask
                masked = torch.bernoulli(torch.full(ids.shape, 0.15)).bool()
                ids[masked] = MASK_ID
                # 模型预测被mask的词
                loss = mlm_model(input_ids=ids, labels=labels).loss
                loss.backward()
```

**结果**: 62文档→9337章节, 分类F1=0.61, MLM无提升(0.43→0.43)

---

## 方法2: Span分类器 — embedding+LR

**论文思路**: [SpERT, arXiv:1909.07755](https://arxiv.org/abs/1909.07755)
**代码**: [`tools/srs_keie_pipeline.py`](tools/srs_keie_pipeline.py)
**F1(金标准)**: 0.54

### 核心流程

```python
class SpanDetector:
    # 参数关键词(用于筛选候选span)
    PARAM_KEYWORDS = re.compile(
        r'(?:time|rate|temperature|voltage|memory|frequency|availability|...)',
        re.IGNORECASE)
    
    def detect(self, sentence):
        doc = self.nlp(sentence)
        candidates = []
        
        # 枚举1-5 gram span
        for i in range(len(tokens)):
            for j in range(i+1, min(i+6, len(tokens)+1)):
                span_text = doc[i:j].text
                if not self.PARAM_KEYWORDS.search(span_text):
                    continue  # 只保留含参数关键词的span
                candidates.append(span_text)
        
        # 用KB embedding做语义匹配
        linked = self.embedder.link_batch(candidates, threshold=0.55)
        # "latency" → cosine_similarity → "response_time"(KB) → 0.82 > 0.55 → 匹配
        
        return [{text, type:"PARAM", confidence:link["similarity"]} 
                for link in linked if link]

# 训练分类器
encoder = SentenceTransformer("all-MiniLM-L6-v2")
train_embs = encoder.encode(train_spans)  # 编码每个span
clf = LogisticRegression(max_iter=1000, class_weight="balanced")
clf.fit(train_embs, train_labels)  # 学习: 这个span是PARAM还是VALUE还是O?

# 评估
preds = clf.predict(test_embs)
# P=0.65 R=0.59 F1=0.54 (金标准)
```

---

## 方法3: BERT-CRF — 弱监督训练

**论文**: [arXiv:1508.01991](https://arxiv.org/abs/1508.01991) + [arXiv:1810.04805](https://arxiv.org/abs/1810.04805)
**代码**: [`tools/srs_bert_crf.py`](tools/srs_bert_crf.py)
**F1(金标准)**: 0.05

### 核心流程

```python
# Step 1: 弱监督标注(用规则自动生成训练数据)
class WeakLabeler:
    PARAM_KW = re.compile(r'(?:response\s*time|throughput|availability|...)')
    VALUE_RE = re.compile(r'\b\d+\.?\d*\b')
    UNIT_RE = re.compile(r'(?:ms|sec|MHz|%|...)')
    OP_RE = re.compile(r'(?:shall\s+not\s+exceed|at\s+least|of|within|...)')
    
    def label_document(self, doc_data):
        for sentence in sentences:
            if not (VALUE_RE.search(sent) and SPEC_CTX.search(sent)):
                continue
            # 用正则标注每个token
            entities = self._extract_entities(text)  # 正则找VALUE/UNIT/OPERATOR/PARAM
            tokens, tags = self._to_bio(text, entities)  # 转BIO格式
            labeled_sentences.append({tokens, tags})
        # 产出: 4070句银标准

# Step 2: BERT-CRF训练
class NerModel(nn.Module):
    def __init__(self):
        self.encoder = AutoModel.from_pretrained("all-MiniLM-L6-v2")
        self.classifier = nn.Linear(384, 9)  # 9个标签: O+B-PARAM+I-PARAM+...
        self.crf = CRF(9, batch_first=True)
    
    def forward(self, ids, mask, labels=None):
        out = self.encoder(input_ids=ids, attention_mask=mask)
        emissions = self.classifier(out.last_hidden_state)
        if labels is not None:
            return -self.crf(emissions, labels, mask=mask.bool())  # CRF损失
        return self.crf.decode(emissions, mask=mask.bool())  # 预测

# Step 3: 评估
# 银标准训练 → 金标准评估
# F1(银)=0.11, F1(金)=0.05 → 银标准噪声太严重
```

---

## 方法4: LLM直接抽取 — GLM-5 SSI schema

**论文思路**: [UIE, arXiv:2203.12277](https://arxiv.org/abs/2203.12277)
**代码**: [`tools/srs_llm_extract.py`](tools/srs_llm_extract.py)
**精度**: ~95%

### 核心流程

```python
class WQBackend(LLMBackend):
    API_URL = "https://wanqing-api.corp.kuaishou.com/api/gateway/v1/endpoints/chat/completions"
    MODEL = "ep-glsztk-1778496696841467392"
    
    EXTRACTION_PROMPT = """You are an expert at analyzing SRS documents.
Extract parameterized constraints: parameter name + operator + value + unit.

Rules:
- ONLY extract real parameter specifications with explicit numeric values
- Section numbers like "5.4 Availability" are NOT values
- List numbers like "1. The system shall..." are NOT values
- Only mark REAL specs: "response time shall not exceed 50 ms"

Return JSON: [{"param":"response time","operator":"<=","value":50,"unit":"ms"}]"""

    def extract(self, sentences):
        resp = requests.post(API_URL, json={
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": self.EXTRACTION_PROMPT},
                {"role": "user", "content": f"Analyze:\n{sentences}"}
            ],
            "enable_thinking": False, "temperature": 0.1
        })
        # GLM-5返回: [{"param":"availability","operator":"=","value":99.99,"unit":"%"}]
        return self._parse_response(resp)

# 优势: LLM能理解"5.4 Availability Requirements"中5.4是章节号不是参数值
# 劣势: 每句调用一次API, 成本高, 召回低(8.5%)
```

---

## 方法5: NLI矛盾检测 — SummaC思路

**论文**: [SummaC, arXiv:2111.09525](https://arxiv.org/abs/2111.09525)
**代码**: 内嵌在实验脚本中
**结果**: 40对检测, 1条真矛盾, 精度~90%

### 核心流程

```python
NLI_PROMPT = """You are an expert at detecting contradictions in SRS documents.

Given two requirement sentences, determine their relationship:
- "contradiction": same parameter, different values, same system
- "neutral": different systems/contexts/phases, or threshold vs objective
- "entailment": one is more specific version of the other

Return JSON: {"label":"contradiction"/"neutral"/"entailment",
              "reason":"...","confidence":0.0-1.0}"""

# 构造检测对: 同参数不同值的约束对
pairs = []
for (file, param), constraints in grouped.items():
    if len(constraints) < 2: continue
    for i in range(len(constraints)):
        for j in range(i+1, len(constraints)):
            if constraints[i]["value"] != constraints[j]["value"]:
                pairs.append({
                    "s1": constraints[i]["sentence"],
                    "s2": constraints[j]["sentence"],
                    "param": param
                })

# 逐对调用GLM-5
for pair in pairs:
    resp = requests.post(API, json={
        "model": "ep-glsztk-1778496696841467392",
        "messages": [
            {"role": "system", "content": NLI_PROMPT},
            {"role": "user", "content": f'S1: "{pair["s1"]}"\nS2: "{pair["s2"]}"'}
        ],
        "enable_thinking": False, "temperature": 0.1
    })
    # 返回: {"label":"contradiction","reason":"same system, 99.99≠99.999","confidence":0.95}

# NLI能排除的假阳性(规则无法排除):
# jitter 2.0 vs 1.0 → neutral (Phase 1 vs Phase 2, 不同阶段)
# response_time 238 vs 1.0 → neutral (238是文档编号)
# duty_cycle 50 vs 100 → neutral (不同时钟配置)
```

---

## 方法6: Z3约束求解 — SMT形式化验证

**工具**: [Z3 Solver](https://github.com/Z3Prover/z3)
**代码**: 内嵌在多个脚本中
**结果**: 8组UNSAT, 但全部是假阳性

### 核心流程

```python
from z3 import *

# 把参数约束转为SMT公式
for (file, param), constraints in grouped.items():
    if len(constraints) < 2: continue
    
    x = Real(f"{param}_{file[:8]}")  # 创建实数变量
    solver = Solver()
    
    for c in constraints:
        val = c["value"]
        op = c.get("operator", "=")
        
        # 转为Z3约束
        if op in ("<=", "<", "≤"):
            solver.add(x <= val)     # x <= 50
        elif op in (">=", ">", "≥"):
            solver.add(x >= val)     # x >= 99.99
        else:
            solver.add(x == val)     # x == 99.999
    
    result = solver.check()
    # SAT = 约束可同时满足(无矛盾)
    # UNSAT = 约束不可同时满足(存在矛盾)
    
    # 例: availability
    # solver.add(x == 99.999)  ← 约束1
    # solver.add(x == 99.99)   ← 约束2
    # result = unsat  ← 99.999 ≠ 99.99, 矛盾!

# 问题: Z3的精度完全依赖参数抽取质量
# response_time=238 被误提取为参数值 → Z3认为238≠1 → UNSAT(假阳性)
# 实际238是文档编号"TCS 238", 不是响应时间
```

---

## 方法7: FloCA — 流程图路径一致性

**论文**: [arXiv:2602.14035](https://arxiv.org/abs/2602.14035)
**代码**: [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py)
**结果**: 37个路径问题

### 核心流程

```python
class FloCAChecker:
    def extract_diagram(self, image_b64, page_text):
        # 用VLM(Kimi-K2.6)从页面截图中提取流程图结构
        prompt = """Extract flowchart structure. Return JSON:
        {"nodes":[{"id":"n1","label":"STARTUP","type":"start"}],
         "edges":[{"source":"n1","target":"n2","condition":"init complete"}],
         "text_steps":["system starts in STARTUP","after init enters OPERATIONS"]}"""
        
        resp = requests.post(VLM_API, ...)
        return diagram  # {nodes, edges, text_steps}
    
    def check_path_consistency(self, diagram):
        G = nx.DiGraph()
        for node in nodes: G.add_node(node["id"])
        for edge in edges: G.add_edge(edge["source"], edge["target"])
        
        issues = []
        
        # 检查1: 可达性 — 所有节点从起始节点可达?
        for start in initial_nodes:
            reachable = set(nx.descendants(G, start))
            for node in all_nodes:
                if node not in reachable:
                    issues.append("不可达节点")
        
        # 检查2: 死锁 — 非终止节点有出边?
        for node in G.nodes():
            if node not in final_nodes and G.out_degree(node) == 0:
                issues.append("死锁节点")
        
        # 检查3: 完整性 — 图中所有边在文本中有描述?
        for edge in edges:
            if not described_in_text(edge):
                issues.append("图中有边但文本未描述")
        
        return issues
```

---

## 方法8: 图片-文本检测 — 6检测器完整流水线

**论文**: VE(1901.06706) + ChartVE(2312.10160) + FloCA(2602.14035) + DFD(1011.0278) + TraceLLM(2602.01253) + Z3
**代码**: [`tools/srs_image_text_check.py`](tools/srs_image_text_check.py)

### 核心流程

```python
# 对每个页面运行6个检测器
for page in test_pages:
    # 1. pdfplumber渲染页面为200dpi PNG
    img = page.to_image(resolution=200)
    b64 = base64.b64encode(open(img_path, "rb").read())
    
    # 2. FloCA: VLM提取节点+边 → NetworkX图 → 可达/死锁/完整性
    floca_result = floca.check_path_consistency(diagram)
    
    # 3. Visual Entailment: 文字描述 vs 图片内容 → 蕴含/矛盾/中立
    ve_result = ve.check(b64, page_text)
    # "Figure 1 shows document structure" vs 图片实际是"风电系统图" → contradiction
    
    # 4. ChartVE: 提取图表数值 → 比对表格数值
    chartve_result = chartve.check(b64, page_text)
    
    # 5. DFD规则: 孤立节点 + 数据流平衡
    dfd_result = dfd.check(diagram)
    
    # 6. Model Checking + Z3: 状态机覆盖/可达/死锁 + 约束求解
    mc_result = model_checker.check(diagram)
    # Z3: solver.add(Implies(state_vars["STARTUP"], state_vars["OPERATIONS"]))
    
    # 7. TraceLLM: 需求↔图节点匹配 → 孤立需求 + 幻影图节点
    trace_result = tracellm.check(b64, page_text)
```

---

## 方法9: MLM领域适配 — ReXCL核心

**论文**: [ReXCL, arXiv:2504.07562](https://arxiv.org/abs/2504.07562)
**代码**: [`tools/srs_rexcl_mlm.py`](tools/srs_rexcl_mlm.py)
**结果**: F1(金) 0.43→0.43 (无提升)

### 核心流程

```python
# Step 1: 构建SRS领域语料(69K句无标注文本)
corpus = []
for pf in sorted(PARSED.glob("*.json")):
    text = "\n".join(p["text"] for p in doc.get("pages", []))
    for line in text.split("\n"):
        if 20 <= len(line) <= 500:
            corpus.append(line)
# 共69,016句

# Step 2: MLM训练(在SRS语料上做Masked Language Model)
mlm_model = AutoModelForMaskedLM.from_pretrained("all-MiniLM-L6-v2")
optimizer = AdamW(mlm_model.parameters(), lr=5e-5)

for epoch in range(3):
    for ids, mask in loader:
        # 手动MLM masking: 15%的token被mask
        prob = torch.full(ids.shape, 0.15)
        masked = torch.bernoulli(prob).bool()
        ids[masked] = MASK_ID  # 替换为[MASK]
        labels[~masked] = -100  # 只计算masked位置的loss
        
        loss = mlm_model(input_ids=ids, attention_mask=mask, labels=labels).loss
        loss.backward()
        optimizer.step()
    # Loss: 5.33 → 4.15 → 3.77 (模型在学习SRS领域语言)

# Step 3: 用适配后的BERT编码span → Span分类器
# 结果: F1(金) 0.43 → 0.43 (无提升)
# 原因: 基线已强(0.43), MLM适配反而扰乱了已有的表示空间
# 论文F1: 0.25→0.97 (基线弱时MLM有效, 基线强时无效)
```

---

## 方法10: 正则模式匹配 — 12组模式

**代码**: [`tools/srs_extract_pipeline.py`](tools/srs_extract_pipeline.py)
**F1(金标准)**: 0.32

### 核心流程

```python
class PatternMatcher:
    UNITS = r'(ms|sec|MHz|%|MB|...)?'
    
    PATTERNS = [
        # A: "X shall not exceed Y Z"
        (r'([a-z][a-z\s\-]{2,40}?)\s+(?:shall\s+not\s+exceed|not\s+exceed)\s+(\d+\.?\d*)\s*' + UNITS,
         '<=', 'A:shall_not_exceed'),
        # B: "X of Y Z"
        (r'([a-z][a-z\s\-]{2,40}?)\s+of\s+(\d+\.?\d*)\s*' + UNITS,
         '=', 'B:of'),
        # C: "X shall be Y Z"
        (r'([a-z][a-z\s\-]{2,40}?)\s+shall\s+be\s+(\d+\.?\d*)\s*' + UNITS,
         '=', 'C:shall_be'),
        # D-K: 共12组模式...
    ]
    
    def match(self, sentence):
        results = []
        for pattern, op, name in self.PATTERNS:
            for m in re.finditer(pattern, sentence, re.IGNORECASE):
                groups = m.groups()
                # groups[0]=参数名, groups[1]=数值, groups[2]=单位
                results.append({
                    "param_text": groups[0].strip(),
                    "operator": op,
                    "value": float(groups[1]),
                    "unit": groups[2] or "",
                })
        return results
# 只能匹配固定句式, 无法处理"alternating 500Hz and 700Hz"等复杂表述
```

---

## 评测结果汇总

| 方法 | 论文 | P | R | F1 | 代码 |
|---|---|:---:|:---:|:---:|---|
| LLM直接抽取 | UIE (2203.12277) | **0.95** | 0.43 | **0.59** | [`srs_llm_extract.py`](tools/srs_llm_extract.py) |
| Span分类器 | SpERT (1909.07755) | 0.65 | **0.59** | 0.54 | [`srs_keie_pipeline.py`](tools/srs_keie_pipeline.py) |
| MLM适配 | ReXCL (2504.07562) | 0.43 | 0.48 | 0.43 | [`srs_rexcl_mlm.py`](tools/srs_rexcl_mlm.py) |
| 正则匹配 | — | 0.32 | 0.35 | 0.32 | [`srs_extract_pipeline.py`](tools/srs_extract_pipeline.py) |
| BERT-CRF(LLM+银) | 1508.01991 | 0.35 | 0.05 | 0.09 | [`srs_bert_crf.py`](tools/srs_bert_crf.py) |
| BERT-CRF(银) | 1508.01991 | 0.16 | 0.03 | 0.05 | [`srs_bert_crf.py`](tools/srs_bert_crf.py) |
| **NLI检测** | SummaC (2111.09525) | **0.90** | — | — | 内嵌 |
| Z3求解 | Z3 Solver | 0* | — | — | 内嵌 |
| FloCA | 2602.14035 | — | — | — | [`srs_image_text_check.py`](tools/srs_image_text_check.py) |
| VE | 1901.06706 | — | — | — | [`srs_image_text_check.py`](tools/srs_image_text_check.py) |

*Z3精度0%: 8个UNSAT全是假阳性(参数抽取误提取)
