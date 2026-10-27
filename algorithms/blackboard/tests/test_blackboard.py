"""Blackboard运行时单元测试: 写入/去重/版本/迭代/final_context/持久化回放."""
from __future__ import annotations

import json

from algorithms.blackboard.blackboard import Blackboard
from algorithms.blackboard.planner import _pair_requirements
from algorithms.blackboard.schemas import (Channel, ConfSource, Critique,
                                            Epistemic, EvidenceItem, Plan,
                                            Provenance, TaskSpec, TaskType)


def _task() -> TaskSpec:
    return TaskSpec(task_id="t1", task_type=TaskType.COMPLETENESS_CHECK,
                    pair_id="1_001")


def _plan(task: TaskSpec) -> Plan:
    return Plan(task, _pair_requirements(prose_critical=False), budget=3)


def _item(subject: str, channel: Channel = Channel.KT,
          epistemic: Epistemic = Epistemic.FACT, conf: float = 1.0,
          conf_source: ConfSource = ConfSource.DETERMINISTIC,
          payload: dict | None = None) -> EvidenceItem:
    return EvidenceItem(
        subject=subject, channel=channel, epistemic=epistemic,
        confidence=conf, conf_source=conf_source,
        payload=payload or {"k": "v"},
        provenance=Provenance(source="test", locator="t1"))


def test_write_bumps_version_and_logs():
    bb = Blackboard(_task(), _plan(_task()))
    assert bb.version == 0
    ok = bb.write("table_agent", _item("table_structure"))
    assert ok and bb.version == 1
    assert bb.records[0].action == "write"          # 黑板自身不记plan(runner记)
    assert bb.records[-1].action == "write"
    assert bb.records[-1].channel == "kt"


def test_duplicate_write_is_swallowed_but_logged():
    bb = Blackboard(_task(), _plan(_task()))
    bb.write("table_agent", _item("table_structure", payload={"k": "v"}))
    ok = bb.write("table_agent", _item("table_structure", payload={"k": "v"}))
    assert ok is False
    assert bb.version == 1                          # 版本不推进
    assert bb.records[-1].action == "duplicate"
    assert len(bb.evidence) == 1


def test_iteration_and_agent_runs():
    bb = Blackboard(_task(), _plan(_task()))
    bb.mark_agent_run("table_agent", "table_structure")
    assert bb.has_run("table_agent", "table_structure")
    assert not bb.has_run("prose_agent", "prose_features")
    bb.bump_iteration()
    bb.bump_iteration()
    assert bb.iteration == 2


def test_final_context_groups_subjects():
    bb = Blackboard(_task(), _plan(_task()))
    bb.write("table_agent", _item("table_structure",
                                  payload={"type": "capability",
                                           "nodes": [{"text": "结构化数据归集",
                                                      "type": "capability"}]}))
    bb.write("vision_agent", _item("diagram_structure", channel=Channel.ANCHOR,
                                   payload={"nodes": [{"text": "数据获取",
                                                       "type": "other"}],
                                            "edges": [], "mapping_confidence": "high"}))
    critique = Critique(verdict="continue", missing=["element_correspondence"],
                        missing_critical=["element_correspondence"],
                        iteration=1)
    ctx = bb.final_context(critique)
    assert ctx["verdict"] == "continue"
    assert "table_structure" in ctx["subjects"] and "diagram_structure" in ctx["subjects"]
    assert ctx["subjects"]["table_structure"]["n_facts"] == 1
    assert ctx["subjects"]["table_structure"]["digest"]["item_names"] == ["结构化数据归集"]
    assert ctx["missing"] == ["element_correspondence"]


def test_final_context_extracts_discrepancies():
    bb = Blackboard(_task(), _plan(_task()))
    bb.write("graph_agent", _item(
        "discrepancy_set", channel=Channel.TIER1, epistemic=Epistemic.HYPOTHESIS,
        conf=0.75, conf_source=ConfSource.HEURISTIC,
        payload={"discrepancies": [{"etype": "exst", "dtype": "TABLE_ITEM_MISSING"},
                                   {"etype": "exc", "dtype": "EXC_MISSING"}]}))
    ctx = bb.final_context(Critique(verdict="satisfied"))
    assert ctx["n_discrepancies"] == 2
    assert ctx["discrepancies"][0][0]["dtype"] == "TABLE_ITEM_MISSING"


def test_save_load_roundtrip(tmp_path):
    task = _task()
    bb = Blackboard(task, _plan(task))
    bb.write("table_agent", _item("table_structure"))
    bb.write("vision_agent", _item("diagram_structure", channel=Channel.ANCHOR))
    bb.bump_iteration()
    state_path = bb.save(tmp_path)
    log_path = tmp_path / "decision_log.jsonl"
    assert state_path.exists() and log_path.exists()

    bb2 = Blackboard.load(state_path, _plan(task))
    assert bb2.version == bb.version
    assert len(bb2.evidence) == len(bb.evidence)
    # 回放一致性: 重建黑板后指纹集合相同(确定性验证)
    assert {e.fingerprint() for e in bb2.evidence} == {e.fingerprint() for e in bb.evidence}
    # 决策日志可逐行解析
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == len(bb.records)
    for line in lines:
        rec = json.loads(line)
        assert "action" in rec and "seq" in rec
