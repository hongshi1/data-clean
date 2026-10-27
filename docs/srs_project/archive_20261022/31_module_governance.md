# 31 模块治理: 上下文关联(A)与一致性校验(B)的双方向平行架构

日期: 2026-10-14(晚), v2(重写以匹配实况)
定位: `algorithms/`的权威结构规范; **本文只治理方向A**, 方向B为另一工作流治理

## 一、实际结构(2026-10-14晚快照)

```
algorithms/
├── context_linking/          ★方向A唯一规范家(本工作流治理)
│   ├── __init__.py           A命名空间声明+evidence_recall API再导出
│   └── evidence_recall/      旗舰: 多头冻结投影+召回+精排(11确定性测试)
│                             (勘验叙事见30号文档)
│
├── consistency/              ★方向B(另一工作流治理 — 禁止触碰)
│   └── syntax/ semantic/ logic/ nli_* srs_calib checker.py ...
│
├── common/                   共享基础设施(两方向单向依赖)
│   ├── bge_local.py          BGE编码客户端(自根级迁入, 全仓117处引用已同步)
│   └── llm_client.py         LLM客户端(同上)
│
├── blackboard/               生产线集成层(横切A+B, 含其自带tests/)
├── qa_synthesis/  mmqa/      B侧评测数据设施(另一工作流放置, 不动)
├── base.py                   检测器基类(B用; 已回根级原位)
├── (根级A平铺存量)           unit_retrieval/va_colpali/table_late/
│                             unit_attention/sqr/context_graph/
│                             context_pipeline/trimodal/
└── archive/                  归档(bge_domain_adapt, bge_lora_retriever)
```

## 二、治理边界(硬性, 防并发冲突)

| 路径 | 归属 | 本工作流 |
|---|---|:---:|
| `algorithms/context_linking/**` | 方向A(我) | 可写 |
| `algorithms/consistency/**` | 方向B(另一工作流) | **禁改** |
| `algorithms/common/**` | 共享 | 追加式可写(移动需全仓同步) |
| `algorithms/blackboard/**` | 集成层 | 只读 |
| 根级A平铺模块 | 存量(震荡中) | **只读**(另一工作流在迁移) |
| `tools/eval|train|build` | A侧工具 | 可写 |
| `tests/test_evidence_recall.py` 等A测试 | 我 | 可写 |

**并发会话协调规则**(已发生两次文件被删事件):
1. 本工作流产物全部落在`context_linking/`命名空间内(不再放根级)
2. 共享设施迁移(如bge_local→common/)必须全仓重写+全量测试验证后落盘
3. 任何删除前先备份到runs/或临时目录

## 三、A侧规则

1. **A不依赖B**: context_linking禁止import algorithms.consistency
2. **A可依赖**: common(bge/llm) + blackboard的reranker(集成件)
3. **新增A模块归属**: 产出"证据/排序/聚合"→context_linking/<module>
4. **import一律绝对路径**(抗目录震荡): `from algorithms.context_linking.evidence_recall import ...`
5. evidence_recall内部用Protocol注入(Encoder/Reranker), 测试用确定性Fake(无GPU/模型依赖)

## 四、根级A平铺模块的归位计划(待另一工作流稳定后执行)

```
unit_retrieval/va_colpali/table_late/unit_attention/sqr/
context_graph/context_pipeline/trimodal → context_linking/
```
前置条件: 另一工作流停止根级震荡; 届时跑
`tools/build/migrate_dual_direction.py`(A部分规则) + 全量测试.

## 五、迁移记录

| 时间 | 动作 | 结果 |
|---|---|---|
| 10-14早 | evidence_recall建包(根级) | 被并发会话删除×2 |
| 10-14晚 | 误建context_association/consistency_check重复命名空间 | 已回退(base.py归位根级, 3处引用恢复) |
| 10-14晚 | bge_local/llm_client→common/(117处引用全仓同步) | ✅229测试过 |
| 10-14晚 | evidence_recall重建于context_linking/(绝对import) | ✅11测试过 |
