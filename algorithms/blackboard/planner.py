"""Planner: HTN路由表 (四类不一致×8场景 → 证据checklist). 纯确定性, 零LLM.

设计: 任务类型先查BLUEPRINT(静态表, 覆盖GJB SRS的规约性任务),
不命中表的自由任务才需要LLM fallback —— 本MVP不实现LLM规划,
未命中即按任务类型兜底蓝图执行(诚实降级, 不编造).
"""
from __future__ import annotations

from typing import Any

from .evidence_store import EvidenceStore, SCENE_PREFIX
from .schemas import Channel, Plan, Requirement, TaskSpec, TaskType

SC3_OPEN_SEMANTIC = (
    "sc3比较语义未定义: 接口表(registry全列) vs 接口图(结构可视化)的超集关系"
    "需领域裁决(M17: 163条裁决118条uncertain, 双模型一致率38%)"
)
SC8_EXCLUDED = "sc8诚实排除: 无表格(无κ_T对象)且无Visio锚点, 非本黑板任务"

BUDGET_DEFAULT = 3


def _pair_requirements(prose_critical: bool,
                       correspondence_critical: bool = True) -> tuple[Requirement, ...]:
    """配对式任务的通用checklist(方向A轨道二)."""
    return (
        Requirement("table_structure", agents=("table_agent",),
                    channels=(Channel.KT,), critical=True,
                    detail="κ_T编译配对表格"),
        Requirement("diagram_structure", agents=("vision_agent",),
                    channels=(Channel.ANCHOR, Channel.VLM), critical=True,
                    detail="锚点XML直读; 无锚点降级VLM(HYPOTHESIS)"),
        Requirement("element_correspondence", agents=("graph_agent",),
                    channels=(Channel.TIER1,), critical=correspondence_critical,
                    detail="预计算Tier1: 表元素↔图节点对应+分歧"),
        Requirement("prose_features", agents=("prose_agent",),
                    channels=(Channel.KP,), critical=prose_critical,
                    detail="κ_P正文特征(行为/枚举/约束/引用)"),
        Requirement("drift_status", agents=("graph_agent",),
                    channels=(Channel.DRIFT_CENSUS,), critical=False,
                    detail="M14源-渲染drift状态"),
    )


def _recall_requirements(has_entity_id: bool) -> tuple[Requirement, ...]:
    """查询式召回checklist(方向A轨道一)."""
    return (
        Requirement("entity_mentions", agents=("entity_agent",),
                    channels=(Channel.ID_GRAPH,), critical=has_entity_id,
                    detail="ID-Graph硬桥: ID→全部mention位置"),
        Requirement("chunk_occurrences", agents=("entity_agent",),
                    channels=(Channel.CHUNKS,), critical=True,
                    detail="结构化chunks字面召回"),
        Requirement("image_hits", agents=("entity_agent",),
                    channels=(Channel.VLM,), critical=False,
                    detail="VLM图片分析key_elements匹配"),
    )


def _completeness_plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    scene = task.scene or (store.scene_of(task.pair_id) if task.pair_id else "")
    if scene == "sc8_pure_image":
        return Plan(task, (), BUDGET_DEFAULT, (SC8_EXCLUDED,))
    notes: tuple[str, ...] = ()
    if scene == "sc3_interface_interface":
        notes = (SC3_OPEN_SEMANTIC,)
    return Plan(task, _pair_requirements(prose_critical=False), BUDGET_DEFAULT, notes)


def _flow_plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    scene = task.scene or (store.scene_of(task.pair_id) if task.pair_id else "")
    if scene == "sc8_pure_image":
        return Plan(task, (), BUDGET_DEFAULT, (SC8_EXCLUDED,))
    return Plan(task, _pair_requirements(prose_critical=False), BUDGET_DEFAULT)


def _terminology_plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    scene = task.scene or (store.scene_of(task.pair_id) if task.pair_id else "")
    if scene == "sc8_pure_image":
        return Plan(task, (), BUDGET_DEFAULT, (SC8_EXCLUDED,))
    reqs = list(_pair_requirements(prose_critical=False, correspondence_critical=False))
    if task.entity or task.entity_id:
        reqs.insert(0, Requirement(
            "entity_mentions", agents=("entity_agent",),
            channels=(Channel.ID_GRAPH,), critical=False,
            detail="ID-Graph: 实体全部出现位置(名称变差的观察面)"))
    return Plan(task, tuple(reqs), BUDGET_DEFAULT)


def _parameter_plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    reqs = list(_pair_requirements(prose_critical=True, correspondence_critical=False))
    return Plan(task, tuple(reqs), BUDGET_DEFAULT,
                ("参数层检测的观察面: κ_P约束(正文) + κ_T表格值; 数值比对在方向B"))


def _recall_plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    return Plan(task, _recall_requirements(bool(task.entity_id)), BUDGET_DEFAULT,
                ("查询式召回(轨道一): 复用M5资产(ID-Graph/chunks/VLM图片分析)",))


def _compliance_plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    reqs = (
        Requirement("syntax_detections", agents=("syntax_agent",),
                    channels=(Channel.SYNTAX,), critical=True,
                    detail="GJB语法层7类规则检测(algorithms/syntax, 112条历史产出)"),
        Requirement("chunk_occurrences", agents=("entity_agent",),
                    channels=(Channel.CHUNKS,), critical=False,
                    detail="章节结构观察面(chunks按section)"),
        Requirement("table_structure", agents=("table_agent",),
                    channels=(Channel.KT,), critical=False,
                    detail="表格结构(供合规规则消费)"),
    )
    return Plan(task, reqs, BUDGET_DEFAULT,
                ("GJB合规检测本体=algorithms/syntax(确定性规则); "
                 "黑板负责证据聚合与上下文供给"))


_BLUEPRINTS: dict[TaskType, Any] = {
    TaskType.COMPLETENESS_CHECK: _completeness_plan,
    TaskType.FLOW_CONSISTENCY: _flow_plan,
    TaskType.TERMINOLOGY_CHECK: _terminology_plan,
    TaskType.PARAMETER_CHECK: _parameter_plan,
    TaskType.CONTEXT_RECALL: _recall_plan,
    TaskType.GJB_COMPLIANCE: _compliance_plan,
}


def plan(task: TaskSpec, store: EvidenceStore) -> Plan:
    """HTN主入口: 任务→蓝图→checklist+预算+注意事项. 确定性."""
    blueprint = _BLUEPRINTS.get(task.task_type)
    if blueprint is None:
        # 未命中蓝图的兜底: 按召回处理(诚实降级, 不LLM编造)
        return _recall_plan(task, store)
    return blueprint(task, store)


def infer_scene(pair_id: str) -> str:
    return SCENE_PREFIX.get(pair_id.split("_")[0], "")
