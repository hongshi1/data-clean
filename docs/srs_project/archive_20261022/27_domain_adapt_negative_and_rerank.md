# 27 域适配负结果链与两阶段重排跨场景分析

日期: 2026-10-13
数据: GJB-URE-v3 (262q deep_v3 / 899q image), FeTaQA (2000q), WTQ (2000q)
全部数字经runs协议归档(`data/gjb_438c/runs/`), 可复现。

## 1. 域适配负结果链(第7-8条)

### 1.1 冻结BGE + 可训练adapter的完整失败链

| 实验 | 训练数据 | 协议 | R@1 | 结论 |
|---|---|---|:---:|---|
| v1 caption分布 | 1541 caption对 | 全量训练→deep评测 | 0.107 | 训练分布错位→负迁移 |
| v2 deep分布 | 294 deep对(含评测) | 全量训练(训练集拟合) | 0.889 | 拟合上界,不可报告 |
| v3 4折CV | 250 deep对 | 训练3折测1折 | 0.199 | 过拟合,低于基线 |
| v4 超参扫描 | 同上 | 5配置CV | 0.118-0.267 | 全配置<基线 |

基线(无adapter): R@1=0.340。

**核心发现**: 容量↓/正则↑→逼近恒等映射但永不超基线。
**恒等映射是该函数族在~250对数据下的最优点**。
L4(语体鸿沟)不可由事后轻量适配解决——需要更大训练集或改检索/交互侧。

### 1.2 机理分析

- caption→表摘要 vs deep→具体行的映射方向冲突(v1)
- 250对不足以约束525K参数的投影(v3/v4)
- fold0(test=131,train=128)退化到0.328≈基线: 同分布查询也只学回恒等

## 2. 两阶段重排: 单元聚焦设计(正结果)

### 2.1 设计

```
Stage 1: O1-unit(IDF加权max-unit) → top-50
Stage 2: BGE-Reranker-v2-m3 cross-encoder
         doc = 表内stage-1单元分top-2的单元拼接(单元聚焦)
         最终分 = rerank分 + 0.1×标准化stage1分
```

**关键失败教训**: 全表dump作rerank文档 → R@1 0.340→0.168(-17.2pt)。
长表稀释目标行, cross-encoder需短段落。单元聚焦后转正。

### 2.2 GJB深行主结果(262q)

| 方法 | R@1 | R@5 | R@10 | MRR@10 |
|---|:---:|:---:|:---:|:---:|
| O1-unit(基线) | 0.340 | 0.550 | 0.611 | 0.429 |
| **O1-unit+Rerank(top50,unit2,b0.1)** | **0.405** | **0.683** | **0.744** | **0.513** |
| Δ | +6.5pt | +13.3pt | +13.3pt | +8.4pt |

McNemar vs 基线: b=31, c=14, p=0.0056(单侧) — 显著。

### 2.3 跨场景稳健性(诚实边界)

| 场景 | Stage1 R@1 | +Rerank R@1 | Δ | p | 判定 |
|---|:---:|:---:|:---:|:---:|---|
| GJB深行 | 0.340 | 0.405 | +6.5pt | 0.0056 | ✓显著 |
| GJB图片 | 0.633 | 0.642 | +0.9pt | 0.295 | R@1无增益;R@5 +5.4pt |
| WTQ(2000q) | 0.410 | 0.440 | +3.0pt | 6.7e-04 | ✓显著 |
| FeTaQA(2000q) | 0.856 | 0.840 | -1.6pt | 0.014 | ✗一阶段已强 |

**规律**: 重排增益与一阶段R@1弱度正相关。
R@5-R@1差距(重排可操作空间): GJB深行21pt>WTQ 17.8pt>GJB图20.8pt(词级匹配
锁死头部)>FeTaQA 8.2pt。语义歧义为主的场景受益; 词级精确匹配或一阶段
已强的场景不受益甚至受损。

### 2.4 与L4瓶颈的关系

L4(语体鸿沟, 82.6%失败=语义赢家型)的正解不在训练侧(§1已证)而在
**交互侧**: cross-encoder的query-doc逐token交互直接弥合语体差异,
无需训练数据。这为O1家族补上了精度短板, 同时保持免训练/可复现。

## 3. 产出物

| 文件 | 说明 |
|---|---|
| `tools/eval/rerank_two_stage.py` | GJB深行两阶段(topk/docmode/unit_topn/blend/mcnemar可配) |
| `tools/eval/rerank_image.py` | 图片场景两阶段 |
| `tools/eval/rerank_public.py` | FeTaQA/WTQ两阶段(语言匹配协议) |
| `tools/train/domain_adapt_v2.py` | 域适配v2(deep分布,全量拟合) |
| `tools/train/domain_adapt_cv.py` | 域适配4折CV(负结果#8) |
| `results/S1_deep_v3_all.json` | +Rerank条目及负结果条目 |
| `results/S4_image_all.json` | +Token-MaxSim+Rerank条目 |
| `results/public_rerank.json` | FeTaQA/WTQ两阶段 |
| `runs/domain_adapt_negative_*` | 负结果链归档 |
| `runs/rerank_*` | 重排实验归档(全超参+McNemar) |

## 4. 下一步

1. LLM深行扩展完成后(298新增, 当前136)→V4数据集(16文档)重训/重评
2. 域适配路线封存, 除非扩展后训练对>1000
3. 两阶段重排并入hybrid_recall生产线候选(unit通道后接rerank)
4. 图片场景R@1提升需新思路(词级匹配锁死, 见S4分析)
