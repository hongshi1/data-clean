"""端到端集成测试: 真实pair上的完整agent loop.

覆盖三个代表性任务:
  1. completeness 1_001 (sc1: 能力表+用例图+κ_P正文+Tier1)
  2. flow 2_001 (sc2: 用例表+流程图+VLM+OCR+drift)
  3. recall 数据获取 (轨道一: ID-Graph+chunks)
依赖真实数据资产, 缺失时跳过.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from algorithms.blackboard.blackboard import Blackboard
from algorithms.blackboard.evidence_store import PAIR_ROOT
from algorithms.blackboard.runner import run_task
from algorithms.blackboard.schemas import TaskSpec, TaskType

pytestmark = pytest.mark.skipif(
    not (PAIR_ROOT / "sc1_usecase_capability" / "1_001" / "meta.json").exists(),
    reason="真实pair_dataset缺失")


def test_completeness_check_on_sc1_pair(tmp_path: Path):
    task = TaskSpec(task_id="it_completeness_1_001",
                    task_type=TaskType.COMPLETENESS_CHECK,
                    query="判断「数据获取」功能在用例图与能力表之间是否存在遗漏",
                    pair_id="1_001")
    final, bb = run_task(task, out_root=tmp_path, save=True)

    assert final["verdict"] == "satisfied"
    subjects = final["subjects"]
    # 配对式核心三件套 + κ_P正文 + 三通道
    for key in ("table_structure", "diagram_structure",
                "element_correspondence", "prose_features"):
        assert key in subjects, f"缺少证据: {key}"
    assert "vlm_extraction" in subjects          # VLM通道同图观测
    assert "discrepancy_set" in subjects         # Tier1分歧
    # 置信度语义: 锚点FACT=1.0; VLM=校准值
    assert subjects["table_structure"]["best_confidence"] == 1.0
    assert subjects["diagram_structure"]["channels"] == ["anchor"]
    # κ_P: 1_001正文的四大归集枚举
    digest = subjects["prose_features"]["digest"]
    assert "结构化数据归集" in digest["enumeration_items"]
    # 决策日志可回放
    log = tmp_path / task.task_id / "decision_log.jsonl"
    records = [json.loads(line) for line in
               log.read_text(encoding="utf-8").strip().splitlines()]
    actions = [r["action"] for r in records]
    assert "plan" in actions and "write" in actions and "critic" in actions
    assert actions[-1] == "final"
    # 状态可重建(回放一致性)
    bb2 = Blackboard.load(tmp_path / task.task_id / "state.json", bb.plan)
    assert len(bb2.evidence) == len(bb.evidence)


def test_flow_consistency_on_sc2_pair(tmp_path: Path):
    task = TaskSpec(task_id="it_flow_2_001",
                    task_type=TaskType.FLOW_CONSISTENCY,
                    query="「开发工程生成」流程图与用例描述表是否一致",
                    pair_id="2_001")
    final, bb = run_task(task, out_root=tmp_path, save=True)

    assert final["verdict"] == "satisfied"
    subjects = final["subjects"]
    # sc2: 三通道齐全(锚点/VLM/OCR)
    assert "vlm_extraction" in subjects
    assert "ocr_extraction" in subjects
    # 2_001在Tier1 v2中有真实分歧(STEP_MISSING/ACTOR_MISSING/EXC_MISSING)
    assert final.get("n_discrepancies", 0) >= 1
    dtypes = {d["dtype"] for disc in final.get("discrepancies", []) for d in disc}
    assert dtypes & {"STEP_MISSING", "ACTOR_MISSING", "EXC_MISSING"}
    # 用例表编译: 步骤+异常流
    tdigest = subjects["table_structure"]["digest"]
    assert tdigest.get("n_exceptions", 0) >= 1 or tdigest.get("uc_name")


def test_context_recall_on_entity(tmp_path: Path):
    task = TaskSpec(task_id="it_recall_shujuhuoqu",
                    task_type=TaskType.CONTEXT_RECALL,
                    query="「数据获取」在文档哪些位置出现",
                    entity="数据获取")
    final, bb = run_task(task, out_root=tmp_path, save=True)

    assert final["verdict"] == "satisfied"
    subjects = final["subjects"]
    assert "chunk_occurrences" in subjects
    assert subjects["chunk_occurrences"]["digest"]["n_occurrences"] >= 1
    # ID-Graph硬桥命中(数据获取是01文档核心实体)
    assert "entity_mentions" in subjects
    assert subjects["entity_mentions"]["digest"]["n_mentions"] >= 1


def test_abstain_on_missing_pair(tmp_path: Path):
    """不存在pair → 关键证据缺失+agent无产出 → 预算耗尽后弃权(不编造)."""
    task = TaskSpec(task_id="it_abstain_9_999",
                    task_type=TaskType.COMPLETENESS_CHECK,
                    pair_id="9_999")
    final, bb = run_task(task, out_root=tmp_path, save=True)
    assert final["verdict"] == "abstain"
    assert final["missing_critical"]
    assert any("弃权" in r for r in final["reasons"])


# ═══════════════════════════════════════════════════════════════
# 检测闭环: 译码阶段(裁决查表/类型先验)
# ═══════════════════════════════════════════════════════════════

def test_flow_task_produces_detection_verdicts(tmp_path: Path):
    """FLOW任务(2_001): 分歧→裁决查表→detection判决齐全."""
    task = TaskSpec(task_id="it_detect_2_001",
                    task_type=TaskType.FLOW_CONSISTENCY,
                    query="「开发工程生成」流程图与用例描述表是否一致",
                    pair_id="2_001")
    final, bb = run_task(task, out_root=tmp_path, save=True)
    det = final.get("detection")
    assert det is not None, "检测闭环未触发"
    s = det["summary"]
    assert s["n_verdicts"] == final["n_discrepancies"] == 4
    assert s["n_adjudicated"] == 4          # 2_001四条分歧全部被M22裁决覆盖
    assert s["n_report"] >= 1               # 2_001_02/03=real_bug → report
    # 决策日志含decode记录
    actions = [r.action for r in bb.records]
    assert "decode" in actions
    # 证据项挂在detection_verdicts主题, 通道=裁决
    items = bb.by_subject("detection_verdicts")
    assert items and items[0].channel.value == "adjudication"
    # ACTOR_MISSING那条: benign(4/5票) → pass, 证据链可追溯
    actor = next(v for v in det["verdicts"]
                 if v["dtype"] == "ACTOR_MISSING")
    assert actor["action"] == "pass"
    assert actor["label_source"] == "adjudicated"


def test_gjb_compliance_task_wires_syntax(tmp_path: Path):
    """GJB_COMPLIANCE实接语法层: syntax_agent产出doc级检测."""
    task = TaskSpec(task_id="it_compliance_01",
                    task_type=TaskType.GJB_COMPLIANCE,
                    doc="01数据获取转换分系统需求规格说明-终稿")
    final, bb = run_task(task, out_root=tmp_path, save=True)
    assert final["verdict"] == "satisfied"
    subjects = final["subjects"]
    assert "syntax_detections" in subjects
    digest = subjects["syntax_detections"]["digest"]
    assert digest["doc"].startswith("01")
    assert digest["n_detections"] >= 0       # 检测数可为0(该文档合规项)
    assert subjects["syntax_detections"]["channels"] == ["syntax"]
    assert subjects["syntax_detections"]["best_confidence"] == 1.0


def test_batch_report(tmp_path: Path):
    """批量模式: 场景级聚合报告(裁决覆盖率/π/report率)."""
    from algorithms.blackboard.runner import run_batch
    report = run_batch(scenes=["sc1_usecase_capability"], limit=3,
                       save=False)
    assert report["n_rows"] == 3
    s = report["by_scene"]["sc1_usecase_capability"]
    assert s["n_pairs"] == 3
    assert s["n_satisfied"] >= 1
    # sc1裁决覆盖低(M17只裁决27条) → 报告如实呈现
    assert "adjudicated_rate" in s and "report_rate" in s
    for row in report["rows"]:
        assert row["verdict"] in ("satisfied", "abstain", "error")
