"""Planner(HTN)与Critic单元测试: 蓝图/预算/弃权/open semantic."""
from __future__ import annotations

from algorithms.blackboard.blackboard import Blackboard
from algorithms.blackboard.critic import Critic
from algorithms.blackboard.evidence_store import EvidenceStore
from algorithms.blackboard.planner import plan, infer_scene
from algorithms.blackboard.schemas import (Channel, ConfSource, Epistemic,
                                            EvidenceItem, Plan, Provenance,
                                            TaskSpec, TaskType)


def _task(task_type: TaskType, pair_id: str = "1_001") -> TaskSpec:
    return TaskSpec(task_id=f"t_{pair_id}", task_type=task_type, pair_id=pair_id)


def test_scene_inference_from_pair_prefix():
    assert infer_scene("1_001") == "sc1_usecase_capability"
    assert infer_scene("2_041") == "sc2_flowchart_usecase"
    assert infer_scene("3_001") == "sc3_interface_interface"
    assert infer_scene("9_999") == ""


def test_completeness_blueprint_checklist():
    store = EvidenceStore()
    p = plan(_task(TaskType.COMPLETENESS_CHECK), store)
    keys = [r.key for r in p.requirements]
    assert keys == ["table_structure", "diagram_structure",
                    "element_correspondence", "prose_features", "drift_status"]
    crit = [r.key for r in p.requirements if r.critical]
    assert crit == ["table_structure", "diagram_structure", "element_correspondence"]
    assert p.budget >= 1


def test_sc3_open_semantic_note():
    store = EvidenceStore()
    p = plan(_task(TaskType.COMPLETENESS_CHECK, "3_001"), store)
    assert any("语义" in n for n in p.notes)


def test_sc8_honest_exclusion():
    store = EvidenceStore()
    p = plan(_task(TaskType.COMPLETENESS_CHECK, "8_001"), store)
    assert p.requirements == ()
    assert any("排除" in n for n in p.notes)


def test_recall_blueprint():
    store = EvidenceStore()
    t = TaskSpec(task_id="r", task_type=TaskType.CONTEXT_RECALL, entity="数据获取")
    p = plan(t, store)
    keys = {r.key for r in p.requirements}
    assert keys == {"entity_mentions", "chunk_occurrences", "image_hits"}
    # 无entity_id时entity_mentions非关键
    em = next(r for r in p.requirements if r.key == "entity_mentions")
    assert em.critical is False


def test_parameter_blueprint_prose_critical():
    store = EvidenceStore()
    p = plan(_task(TaskType.PARAMETER_CHECK), store)
    prose = next(r for r in p.requirements if r.key == "prose_features")
    assert prose.critical is True


def test_unknown_task_type_falls_back_to_recall():
    store = EvidenceStore()
    t = TaskSpec(task_id="x", task_type=TaskType.CONTEXT_RECALL, entity="x")
    p = plan(t, store)
    assert {r.key for r in p.requirements} >= {"chunk_occurrences"}


# ═══════════════════════════════════════════════════════════════
# Critic
# ═══════════════════════════════════════════════════════════════

def _evidence(subject: str, conf: float = 1.0) -> EvidenceItem:
    return EvidenceItem(
        subject=subject, channel=Channel.KT, epistemic=Epistemic.FACT,
        confidence=conf, conf_source=ConfSource.DETERMINISTIC,
        payload={"k": 1}, provenance=Provenance(source="t", locator="t"))


def test_critic_continue_when_missing_and_budget_left():
    task = _task(TaskType.COMPLETENESS_CHECK)
    bb = Blackboard(task, plan(task, EvidenceStore()))
    c = Critic().review(bb, bb.plan)
    assert c.verdict == "continue"
    assert "table_structure" in c.missing_critical
    assert c.escalation  # 有可调agent
    assert any(a.startswith("table_agent") for a in c.escalation)


def test_critic_abstain_when_budget_exhausted():
    task = _task(TaskType.COMPLETENESS_CHECK)
    bb = Blackboard(task, plan(task, EvidenceStore()))
    for _ in range(3):
        bb.bump_iteration()
    c = Critic().review(bb, bb.plan)
    assert c.verdict == "abstain"
    assert "预算耗尽" in " ".join(c.reasons)


def test_critic_satisfied_when_critical_covered():
    task = _task(TaskType.COMPLETENESS_CHECK)
    bb = Blackboard(task, plan(task, EvidenceStore()))
    bb.plan = Plan(task, tuple(
        r for r in bb.plan.requirements
        if r.key in ("table_structure", "diagram_structure",
                     "element_correspondence")), budget=3)
    for key in ("table_structure", "diagram_structure", "element_correspondence"):
        bb.write("test", _evidence(key))
    c = Critic().review(bb, bb.plan)
    assert c.verdict == "satisfied"


def test_critic_confidence_escalation():
    task = _task(TaskType.COMPLETENESS_CHECK)
    bb = Blackboard(task, plan(task, EvidenceStore()))
    bb.plan = Plan(task, tuple(
        r for r in bb.plan.requirements if r.key == "diagram_structure"), budget=3)
    bb.write("vision_agent", _evidence("diagram_structure", conf=0.4))
    # 未标记agent运行 → 可升级
    c = Critic().review(bb, bb.plan)
    assert "vision_agent:diagram_structure" in c.escalation
    assert any("升级" in r for r in c.reasons)


def test_critic_open_semantic_dedup_for_sc3():
    task = _task(TaskType.COMPLETENESS_CHECK, "3_001")
    p = plan(task, EvidenceStore())
    bb = Blackboard(task, p)
    c = Critic().review(bb, p)
    assert c.open_semantic
    assert len(c.open_semantic) == len(set(c.open_semantic))  # 无重复
