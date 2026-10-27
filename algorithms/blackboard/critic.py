"""Critic: 覆盖checklist + 置信度门控 + 预算控制 + 弃权判定. 确定性, 零LLM.

三个问题(用户架构的原文):
  覆盖不足? → missing (checklist差集, 确定性判定)
  模态缺失/置信不足? → escalation (低置信+存在未运行的备选agent)
  预算耗尽? → abstain (ACDD P3弃权哲学: 失效模式是"沉默地不工作",
              不是"自信地报错")
"""
from __future__ import annotations

from .blackboard import Blackboard
from .planner import Plan, SC3_OPEN_SEMANTIC
from .schemas import Critique

LOW_CONF_TH = 0.6


class Critic:

    def __init__(self, low_conf: float = LOW_CONF_TH) -> None:
        self.low_conf = low_conf

    def review(self, bb: Blackboard, plan: Plan) -> Critique:
        written = bb.subjects_written()
        satisfied: list[str] = []
        missing: list[str] = []
        missing_critical: list[str] = []
        escalation: list[str] = []      # "agent:subject" 令牌
        reasons: list[str] = []

        for req in plan.requirements:
            if req.key in written:
                satisfied.append(req.key)
                best = bb.best_confidence(req.key)
                if best < self.low_conf:
                    for agent in req.agents:
                        if not bb.has_run(agent, req.key):
                            escalation.append(f"{agent}:{req.key}")
                            reasons.append(
                                f"[{req.key}] best_conf={best:.2f}<{self.low_conf}"
                                f" → 升级 {agent}")
                            break
                    else:
                        reasons.append(
                            f"[{req.key}] best_conf={best:.2f}<{self.low_conf}"
                            f" 且无备选agent → 证据质量受限(如实报告)")
            else:
                missing.append(req.key)
                if req.critical:
                    missing_critical.append(req.key)
                for agent in req.agents:
                    if not bb.has_run(agent, req.key):
                        escalation.append(f"{agent}:{req.key}")
                        break

        open_semantic: list[str] = []
        if bb.task.scene == "sc3_interface_interface" or (
                bb.task.pair_id.startswith("3_")):
            open_semantic.append(SC3_OPEN_SEMANTIC)
        for note in plan.notes:
            if "语义" in note or "排除" in note:
                open_semantic.append(note)
        open_semantic = list(dict.fromkeys(open_semantic))

        budget_left = bb.iteration < plan.budget

        if not missing_critical:
            if missing:
                reasons.append(f"非关键证据缺失(不阻塞): {missing}")
            verdict = "satisfied"
        elif not budget_left:
            verdict = "abstain"
            reasons.append(
                f"预算耗尽(iteration={bb.iteration}>=budget={plan.budget}), "
                f"关键证据缺失: {missing_critical} → 弃权送人工")
        elif not escalation:
            verdict = "abstain"
            reasons.append(
                f"无可满足路径(相关agent均已运行), 关键证据缺失: "
                f"{missing_critical} → 弃权送人工")
        else:
            verdict = "continue"

        return Critique(
            verdict=verdict, satisfied=satisfied, missing=missing,
            missing_critical=missing_critical, escalation=escalation,
            open_semantic=open_semantic, iteration=bb.iteration, reasons=reasons)
