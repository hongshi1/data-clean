"""Router: 按critique的escalation选择下一轮agent调用 (选择性路由, 非全通道常开).

路由规则(确定性):
  1. 初始: checklist每项 → 其第一优先agent
  2. 续轮: critic的escalation令牌(agent:subject) → 未运行才调用
  3. 富集: embedding可用且表格+正文特征齐备 → prose_agent做semantic_links
     (κ_P枚举项 ↔ κ_T表格项的语义对齐, 正是"数据主动推送vs数据订阅推送"盲区的系统解)
"""
from __future__ import annotations

from .blackboard import Blackboard
from .planner import Plan
from .schemas import Critique, Invocation


def initial(plan: Plan, bb: Blackboard) -> list[Invocation]:
    """第0轮: checklist全量 → 每项一个invocation(第一优先agent).

    末尾追加语义富集(若embedding可用): 同轮内table_agent先运行,
    prose_features写完后semantic_links即可读到两侧证据.
    """
    invs: list[Invocation] = []
    keys = [r.key for r in plan.requirements]
    for req in plan.requirements:
        if not req.agents:
            continue
        invs.append(Invocation(agent=req.agents[0], subject=req.key))
        bb.mark_agent_run(req.agents[0], req.key)
    # 查询扩展轮(agentic RAG): CONTEXT_RECALL首轮召回后, 从证据提取新词二轮检索
    # (时序: 本轮内chunk_occurrences先执行写入, expanded_recall后执行可读到)
    if (bb.task.task_type.value == "context_recall"
            and "chunk_occurrences" in keys):
        invs.append(Invocation(agent="entity_agent", subject="expanded_recall"))
        bb.mark_agent_run("entity_agent", "expanded_recall")
    if (bb.embedding_mode != "unavailable"
            and "table_structure" in keys and "prose_features" in keys):
        invs.append(Invocation(agent="prose_agent", subject="semantic_links"))
        bb.mark_agent_run("prose_agent", "semantic_links")
    return invs


def route(critique: Critique, plan: Plan, bb: Blackboard) -> list[Invocation]:
    """续轮: escalation + 富集. 空列表 = 终止循环."""
    invs: list[Invocation] = []
    for token in critique.escalation:
        agent, subject = token.split(":", 1)
        if not bb.has_run(agent, subject):
            invs.append(Invocation(agent=agent, subject=subject,
                                    params={"escalated": True}))
            bb.mark_agent_run(agent, subject)

    # 语义富集: embedding通道可用 + 两侧特征齐备
    if (bb.embedding_mode != "unavailable"
            and bb.by_subject("table_structure")
            and bb.by_subject("prose_features")
            and not bb.has_run("prose_agent", "semantic_links")):
        invs.append(Invocation(agent="prose_agent", subject="semantic_links"))
        bb.mark_agent_run("prose_agent", "semantic_links")
    return invs
