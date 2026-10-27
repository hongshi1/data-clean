# 33 Baseline系统化整理: 复现方法注册表与统一头架构

日期: 2026-10-14
定位: 方向A全部复现baseline的权威注册表(实现位置/覆盖场景/锁定数字/遗留问题)

## 一、统一头架构(本次整理的核心)

所有baseline收进`algorithms/context_linking/baselines/`, 与
evidence_recall头**同接口**: `build(store) → score_query(query) →
per-owner分数向量`. 评测harness按名迭代(`make_baseline`),
与我们的方法同管线对比(同语料/同查询/同指标/同哈希).

```python
from algorithms.context_linking import make_baseline
head = make_baseline("BM25-unit", store)      # 词面系免编码器
head = make_baseline("B1-dense", store, encoder=enc)  # 稠密系注入
head = make_baseline("Token-MaxSim", store, token_encoder=enc)
sc = head.score_query("查询")   # → np.ndarray(n_owners,)
```

## 二、注册表(全部复现baseline)

### 已进统一头包(7个确定性测试覆盖)

| 方法 | 家族 | 实现 | 数学 |
|---|---|---|---|
| BM25-doc | 词面 | `baselines`(=LexicalHead) | 文档级BM25, k1=1.5/b=0.75, CJK二元组+拉丁词 |
| BM25-unit | 词面 | `baselines.BM25UnitHead` | 单元级BM25, owner分=max单元分 |
| B1-dense | 稠密 | `evidence_recall.DenseHead` | 全文512截断余弦(编码器注入: zh/en语言匹配) |
| Token-MaxSim | 后期交互 | `baselines.TokenMaxSimHead` | Σ_qt max_dt cos, 512窗口, torch可选GPU |

### 模型门控系(留评测脚本, lazy加载+fp16细节)

| 方法 | 家族 | 实现位置 | 覆盖场景 | 代表数字(R@1) |
|---|---|---|---|---|
| M3-dense | 稠密SOTA | tools/eval_sota_m3.py, unified_eval.py | 全场景 | GJB深行0.107, FeTaQA 0.883 |
| M3-dense@4096 | 稠密SOTA | unified_eval.py | GJB深行 | 0.145(截断贡献仅+3.8pt) |
| M3-sparse | 稀疏SOTA | unified_eval.py | 全场景 | zh正常, **en异常**(见§四) |
| M3-colbert | 后期交互SOTA | unified_eval.py | 全场景 | GJB深行0.072 |
| Contriever-MS | 稠密SOTA | tools/eval_sota_baselines.py | 全场景 | GJB 0.000(跨语言), WTQ 0.336 |
| ColBERTv2 | 后期交互里程碑 | tools/eval_sota_baselines.py | 单查询验证 | gold 9.04>非gold 5.2-8.5(批量被PLAID阻塞) |
| E5-dense | 稠密 | tools(mE5) | v2场景 | 见旧表 |
| Cell-BM25 | 词面 | tools(单元格级) | v2场景 | 见旧表 |

### 学习式(负结果资产, 已归档/文档化)

| 方法 | 结论 | 出处 |
|---|---|---|
| CMSC投影头 | 跨折负迁移; 折内+2.3pt | 文档27, cmsc_fuse=0默认 |
| 域适配adapter | 负结果#7/#8(恒等最优) | 文档27, algorithms/archive |
| UAA聚合器 | 收敛回固定公式(不动点) | unit_attention+快照测试 |

### 精排与路由

| 方法 | 结论 | 位置 |
|---|---|---|
| BGE-Reranker(全表dump) | **负**(-17.2pt, 长表稀释) | S1记录 |
| BGE-Reranker(单元聚焦) | 正(+12.1pt, p=6.7e-08) | evidence_recall/rerank |
| ROUTE4/5 | zh有效en不外推 | tools, 仅作鲁棒降级 |

## 三、覆盖矩阵(方法×场景, 锁定R@1)

| 方法 | GJB深v3 | GJB深v4 | GJB图 | WTQ | FeTaQA | DuRet | PURE |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| BM25-doc | 0.069 | 0.352 | 0.685 | 0.282 | 0.706 | 0.836 | 0.319 |
| BM25-unit | 0.095 | 0.250 | 0.543 | 0.277 | 0.789 | 0.744 | 0.295 |
| B1-dense | 0.046 | 0.125 | 0.660 | 0.333 | 0.836 | 0.879 | 0.319 |
| M3-dense | 0.088 | 0.227 | 0.596 | — | — | 0.865 | 0.295 |
| Token-MaxSim | — | — | 0.633 | — | — | — | 0.319 |
| Contriever-MS | 0.000 | 0.000 | 0.120 | 0.336 | — | — | — |
| **O1-unit(我们)** | **0.340** | **0.403** | 0.583 | **0.410** | **0.856** | 0.837 | 0.283 |
| O1+Rerank(我们) | **0.405** | **0.608** | 0.642 | **0.440** | 0.840 | 新 | 新 |

(完整R@5/R@10/MRR见各S*文件与full_results_matrix.json)

## 四、遗留优化项(优先级排序)

1. **M3-sparse英文异常**: WTQ=0.003/FeTaQA=0.004(zh正常) — 疑fp16
   精度或tokenization问题, 未调查. 需GPU.
2. **ColBERTv2批量评测**: 需PLAID/DiskANN索引基建 — 单机内存限制,
   单查询验证已通过. 暂缓.
3. **Contriever zh=0.000**: 跨语言预期行为(非bug), 文档化即可.
4. E5/Cell-BM25: v2时代遗留, 场景已演进 — 建议下次全量评测时
   用统一头接口重跑或明确废弃.

## 五、真数据逐位验证(2026-10-14)

统一头包在GJB-URE-v4联合438q(表池1207)上与S6锁定值**逐位一致**:
- BM25-doc(框架): R@1=0.183 R@5=0.306 MRR=0.238 = 锁定值 ✓
- BM25-unit(框架): R@1=0.158 R@5=0.331 MRR=0.231 = 锁定值 ✓
(纯CPU 8秒完成, 不受GPU争抢影响; 语义头/Token头验证随S7/S8)

## 六、产出物

| 文件 | 说明 |
|---|---|
| `algorithms/context_linking/baselines/` | 统一头包(make_baseline注册表) |
| `tests/test_baselines_heads.py` | 7确定性测试(one-hot词表, 无模型依赖) |
| 本文档 | 注册表+覆盖矩阵+验证+遗留项 |
