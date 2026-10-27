"""Calibrated Blackboard: 基于黑板的Agentic RAG上下文关联运行时.

架构(用户2026-09设计 + 项目资产落地):
  Planner(HTN) → Context Blackboard(版本化状态+决策日志) →
  Router(选择性路由) → 5个确定性Agent(κ_T/锚点/VLM/OCR/κ_P/ID-Graph) →
  Critic(覆盖+置信度门控+预算+弃权) → Final Context(视图)

区别于通用Blackboard Agentic RAG的核心主张:
  每条证据写入 = 一次带已测量误差模型的测量 (confidence有CALIBRATED来源),
  不是LLM自报的感觉值. 可解释性 = 每条边可回溯(谁写入/什么通道/什么置信度/谁裁决过).
"""
from .adjudication import AdjudicationStore
from .blackboard import Blackboard
from .confidence import ConfidenceModel
from .critic import Critic
from .decoder import Decoder, decode_element
from .embedding_channel import EmbeddingChannel
from .evidence_store import EvidenceStore
from .planner import plan
from .router import initial, route
from .schemas import (Channel, ConfSource, Critique, Epistemic, EvidenceItem,
                      Invocation, Plan, Provenance, Requirement, TaskSpec,
                      TaskType)

# 注意: runner不在此导入(避免 python -m algorithms.blackboard.runner 的
# 双重导入告警); 用 from algorithms.blackboard.runner import run_task

__version__ = "0.1.0"

__all__ = [
    "AdjudicationStore", "Blackboard", "ConfidenceModel", "Critic",
    "Decoder", "decode_element", "EmbeddingChannel",
    "EvidenceStore", "plan", "initial", "route",
    "Channel", "ConfSource", "Critique", "Epistemic", "EvidenceItem",
    "Invocation", "Plan", "Provenance", "Requirement", "TaskSpec", "TaskType",
]
