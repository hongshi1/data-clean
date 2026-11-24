"""场景1: 上下文关联(方向A) — KG双图融合条目聚合.

模块:
  kg_context_matcher.py - LightRAG+ID-Graph双图融合的实体条目聚合
                          (tools/gen_retrieval_evalset.py 评测集生成 +
                          tests/test_kernel_snapshots.py 快照锁定)

历史: M28的 detectors.py(7种图方法)与 agentic_rag.py(MAGE-RAG风格)
已在死代码审计中删除(零消费者; 图方法被claim_channels等QA链路替代,
Agentic检索被 blackboard/hybrid_recall 替代).
"""
