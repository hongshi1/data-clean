"""GJB SRS算法层.

平行方向(本层仅治理方向B):
  方向A 上下文关联: blackboard/ trimodal/ mmqa/ 及context_*等(原位, 待专项治理)
  方向B 一致性校验: consistency/ ← 2026-10-14治理
      checker.py(v4.1六通道κD) / nli_local / nli_pair_claims /
      nli_discrepancy_review / srs_calib / semantic|syntax|logic三层
  Task 2 QA合成: qa_synth.py / qa_mutation_ops.py(原位)
  共享设施: llm_client.py / bge_local.py / base.py / common/
数据流: 文档 → [方向A聚合] → Pair → [方向B校验] → 判定
"""
