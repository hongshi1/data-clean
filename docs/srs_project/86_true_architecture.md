# 86 上下文关联系统真实架构（审计修正版）

日期：2026-11-01 | 替代已删除的61/67/82号 | 基于代码级审计

---

## 一、系统全貌：三轨并存

```text
方向A "上下文关联" 实际是三个独立子系统并行：

┌─ 轨道1: 研究检索轨(evidence_recall) ─────────────────────────┐
│  用途: 论文召回评测(S系列实验)                                  │
│  位置: algorithms/context_linking/evidence_recall/             │
│  机制: 多头冻结投影(3头) + 场景路由 + 单元聚焦精排              │
│  数据: gjb_ure_v4.json (1586owner/18032单元)                  │
│  状态: 零训练, 冻结投影, WTQ/FeTaQA/DuRetrieval外部效度已测     │
└────────────────────────────────────────────────────────────────┘

┌─ 轨道2: 研究图谱轨(evidence_graph) ───────────────────────────┐
│  用途: 离线条目聚合/候选发现                                    │
│  位置: tools/build_evidence_graph.py + v2                     │
│  机制: CandidateLink四类 → 并查集 → Item → QualityContract     │
│  数据: structured_corpus_v1 (27,473对象)                      │
│  状态: v2完成(silver升级/408条目/3,732发现)                    │
└────────────────────────────────────────────────────────────────┘

┌─ 轨道3: 生产图谱轨(graph_store+ContextGraph) ─────────────────┐
│  用途: 前后端平台的实际图谱查询(/api/activate)                  │
│  位置: tools/build_context_graph.py + algorithms/context_graph.py│
│  机制: 六模态建图(5619节点/23742边) → 种子识别 → k-hop激活      │
│  数据: graph_store/{01..16,global}.json                       │
│  消费: deploy/nkuDataProject(React前端图谱查询页)              │
└────────────────────────────────────────────────────────────────┘

另有: vendored拷贝(srs_verify_package/srs_verify/context/)
      = 轨道1的分发包内冻结副本(9文件, 与algorithms/主线无同步机制)
```

---

## 二、轨道1详述：研究检索轨（核心论文贡献）

### 2.1 证据池真实构成

```text
数据源: gjb_ure_v4.json
构建链: content_list.json
        → tools/srs_chunker.py → srs_chunks.json (5231块)
        → tools/build_ure_dataset.py → gjb_ure_v2
        → tools/build/build_gjb_v3.py → v3 (S1-S4修复)
        → tools/build/build_gjb_v4_expansion.py → v4

证据池(1586 owner, 18032单元):
  表格: 1207块 → 表头:值配对行单元 (MAX_ROWS=120)
  图元素: 379块 → anchor_v2节点text + VLM key_elements
  文本: 3643块 → ⚠️ 被排除(不进证据池, 仅B2聚合时补入prose)

图单元提取: algorithms/va_colpali.py
  = anchor_v2节点(经va_colpali_img_anchor_map.json映射) + VLM描述
  (anchor_v3的5165节点不进证据池, 仅进structured_corpus)
```

### 2.2 多头冻结投影（3头，全部零训练）

| 头 | 数学 | 用途 |
|---|---|---|
| **SemanticUnitHead** | s(q,d) = max_u[cos(q,u)·log(1+N/df(u))] | 全单元类型统一打分 |
| **LexicalHead** | BM25(k1=1.5, b=0.75), CJK二元组 | 图片/图元素场景 |
| DenseHead | owner全文(title+units截512字)余弦 | 对照基线 |

### 2.3 场景路由（规则，非学习）

```python
SCENE_ROUTE = {
    "table": ["semantic_unit"],           # 表格→仅语义头
    "image": ["lexical", "semantic_unit"], # 图片→词面+语义双头
}
# pool="all"时默认走["semantic_unit"]
# 融合: 头序列内逐元素np.maximum(不是加权)
```

### 2.4 精排器

```text
模型: BGE-Reranker-v2-m3 (cross-encoder)
输入: (query, top-2单元拼接截2000字)  ← 不是全表dump(-17pt已证伪)
融合: comb = r + 0.1·(召回分minmax/rerank极差)·|rmax|
```

### 2.5 召回质量（诚实版，按场景分列）

| 场景 | 查询数 | O1 R@1 | +精排R@1 | +精排R@5 | +精排R@10 |
|---|---:|---:|---:|---:|---:|
| 表格深行v4扩展 | 176 | 0.403 | **0.608** | — | — |
| 表格深行v3 | 262 | 0.340 | 0.405 | — | — |
| **联合438查询** | 438 | 0.365 | **0.486** | 0.749 | 0.801 |
| 图片/图元素 | 899 | 0.633 | 0.642 | 0.895 | 0.944 |

⚠️ 之前文档用0.608代表全系统是选择性引用——这是v4子场景最优值，
系统级代表值是**联合场景0.486**。

### 2.6 训练组件（实际存在的学习成分）

| 组件 | 位置 | 状态 |
|---|---|---|
| 共享投影头(256维) | tools/train_shared_projection.py | InfoNCE训练(银标签) |
| KT2去捷径 | tools/train_full_pipeline.py | ID降权+锚点注入 |
| UAA子注意力 | algorithms/unit_attention.py | ~500参数MLP |
| CMSC投影 | models/cmsc_projection.pt | **已关闭**(CMSC_FUSE=0.0, 泄漏审计) |
| BGE-LoRA | algorithms/archive/ | **负结果, 归档** |
| **scope_binder学习器** | tools/train_scope_binder.py | **F1=0.837(83号)** |

---

## 三、轨道2详述：研究图谱轨

```text
输入: structured_corpus_v1 (27,473对象)
流程: build_evidence_graph.py
  → CandidateLink四类(identity/ref/membership/neighbor) 21,650条
  → build_evidence_graph_v2.py
    → 显式标识符silver升级 4,969条
    → 并查集聚合 → 408个Item
    → QualityContract义务检查 → 3,732个Finding
状态: 完成(候选层, 非gold)
```

## 四、轨道3详述：生产图谱轨

```text
输入: stage0_assets + anchor_v2 + knowledge + content_list
构建: tools/build_context_graph.py
  → graph_store/{01..16,global}.json
  → 六模态: TXT/TBL/IMG/E/SEQ/KNW
  → 5619节点 / 23742边 / 978条目

查询: algorithms/context_graph.py ContextGraph.activate()
  → 种子识别(ID正则/图表号/n-gram/全文检索)
  → 1-2跳乘积权重BFS
  → 意图定向增强(location/list/table_ref)
  → 模态分组 + 综合分(0.45路径+0.55相关性)

消费: deploy/nkuDataProject/
  → import_rich.py导入达梦DB
  → backend graph.py/activate_compat.py
  → React前端图谱查询页(/api/activate)
```

---

## 五、修正后的完整数据流DAG

```
16份GJB SRS .doc
├─ MinerU → content_list.json (text3643/table1207/image381/list...=5231块)
├─ textutil → dual_source/*.html (仅统计, 不入证据池)
├─ Visio OLE → anchor_v2(3759节点, 证据池用) + anchor_v3(5165节点, 仅corpus)
└─ VLM → srs_image_analyses.json (caption+key_elements)

── 证据池构建链(轨道1) ──
content_list → srs_chunker → srs_chunks.json
  → build_ure_dataset(单元=va_colpali图单元+表行)
  → build_gjb_v3 → build_gjb_v4 → gjb_ure_v4.json
     (1586owner: 1207表+379图, 18032单元)
     ⚠️ 3643个text块被排除

── 查询链(轨道1) ──
query → BGE编码(9.3ms) → MultiHeadRecall(3头, 13.9ms)
  → SCENE_ROUTE融合 → top-50 hits
  → UnitFocusedRerank(+50ms, 可选)
  → EvidenceHit{owner, kind, score, head, best_units}

── 语料构建链(轨道2/3共用) ──
mineru+dual_source+anchor_v3+qa → build_structured_corpus
  → structured_corpus_v1 (27,473对象)

── 图谱链(轨道2) ──
structured_corpus → build_evidence_graph → v2
  → 408 items / 3,732 findings

── 图谱链(轨道3) ──
stage0+anchor_v2+knowledge → build_context_graph → graph_store
  → ContextGraph.activate() → 前端消费

── 分发链 ──
srs_verify_package/srs_verify/context/ = 轨道1的冻结拷贝(9文件)
  → service:8400 → deploy backend → 前端
```

---

## 六、延迟（修正版，分轨道）

| 操作 | 延迟 | 说明 |
|---|---:|---|
| **轨道1: 召回查询** | 14ms(无精排)/64ms(含精排) | BGE 9.3ms + 多头 4.6ms |
| **轨道1: 精排** | +50ms | cross-encoder |
| **轨道1: 索引构建** | 76.2s/文档(离线一次性) | 11,539单元 |
| **轨道3: 图谱激活** | ~10ms | k-hop BFS |
| **新文档摄取** | 12.6s(+MinerU外部) | 结构化+编码+索引 |
| **裁决(fast)** | 8.4ms | 方向B, 不属于上下文关联 |
| **裁决(standard)** | 117.8ms | 方向B, NLI占87% |

---

## 七、已删除文档的错误清单

| 文档 | 错误 | 处置 |
|---|---|---|
| 61号 | 把训练组件(Procrustes/共享投影/残差)画进召回架构; "5423块"数字对不上; LLM-listwise标"待完成"但代码已存在 | **已删除** |
| 67号 | "346原子/1269对"过时(实际292/1175); "S2待实现"过时 | **已删除** |
| 82号 | 用v4子场景0.608代表全系统(实际联合0.486); 把方向B(提纯/裁决)画进方向A框架图; 数字混用两个资产口径 | **已删除** |

---

## 八、代码资产完整清单（含隐藏组件）

| 组件 | 位置 | 文档曾提及 |
|---|---|---|
| evidence_recall核心 | algorithms/context_linking/evidence_recall/ | ✅ |
| baselines统一头 | algorithms/context_linking/baselines/ | ❌ |
| alignment原语(Procrustes等) | algorithms/context_linking/alignment/ | ❌(61画错位置) |
| ContextGraph+graph_store | algorithms/context_graph.py + tools/ | ❌ |
| 三模块管线MFE→SAA→CR | algorithms/context_pipeline.py | ❌ |
| vendored管线拷贝 | srs_verify_package/srs_verify/context/ | ❌ |
| 数据集构建链 | tools/build/ + tools/srs_chunker.py | ❌ |
| 单元检索核心UnitIndex | algorithms/unit_retrieval.py | ❌ |
| UAA子注意力 | algorithms/unit_attention.py | ❌ |
| LLM-listwise | baselines/llm_listwise.py | ❌(标"待完成") |
| 评测套件S1-S11 | tools/eval/ | ❌ |
| B2条目聚合 | tools/eval/b2_aggregation_v4.py | ❌ |
| kg_context_matcher | consistency/semantic/scene1/ | ❌ |
| agentic_rag | consistency/semantic/scene1/ | ❌ |
| 多骨干模型(6种) | models/embedding/ | ❌ |
| scope_binder学习器 | tools/train_scope_binder.py | ✅(83号) |
