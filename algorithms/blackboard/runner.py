"""Runner: 端到端agent loop (plan → route → write → critic → 终止/弃权).

用法:
  python -m algorithms.blackboard.runner --task completeness --pair 1_001
  python -m algorithms.blackboard.runner --task flow --pair 2_001
  python -m algorithms.blackboard.runner --task recall --entity 数据获取
  python -m algorithms.blackboard.runner --demo

产出: data/gjb_438c/blackboard/runs/<task_id>/{state.json, decision_log.jsonl}
终端打印: 最终上下文的紧凑摘要(视图).
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Any

from .agents import AGENTS, AgentContext
from .adjudication import AdjudicationStore
from .blackboard import Blackboard
from .confidence import ConfidenceModel
from .critic import Critic
from .decoder import Decoder
from .embedding_channel import EmbeddingChannel
from .evidence_store import EvidenceStore
from .planner import plan as make_plan
from .router import initial, route
from .schemas import TaskSpec, TaskType

BASE = Path(__file__).resolve().parents[2]
RUNS_DIR = BASE / "data/gjb_438c/blackboard/runs"

_TASK_MAP = {
    "completeness": TaskType.COMPLETENESS_CHECK,
    "flow": TaskType.FLOW_CONSISTENCY,
    "terminology": TaskType.TERMINOLOGY_CHECK,
    "parameter": TaskType.PARAMETER_CHECK,
    "recall": TaskType.CONTEXT_RECALL,
    "compliance": TaskType.GJB_COMPLIANCE,
}

# 检测类任务: 有分歧证据时触发译码阶段(证据→裁决→判决闭环)
_DETECT_TYPES = {TaskType.COMPLETENESS_CHECK, TaskType.FLOW_CONSISTENCY,
                 TaskType.TERMINOLOGY_CHECK, TaskType.PARAMETER_CHECK}


def run_task(task: TaskSpec,
             store: EvidenceStore | None = None,
             conf: ConfidenceModel | None = None,
             embedding: EmbeddingChannel | None = None,
             out_root: Path | None = None,
             save: bool = True,
             budget: int | None = None,
             decoder: Decoder | None = None) -> tuple[dict[str, Any], Blackboard]:
    """执行一个任务的完整agent loop. 返回(最终上下文, 黑板).

    检测类任务在agent loop结束后追加译码阶段:
      discrepancy_set(HYPOTHESIS) → 裁决查表/类型先验 → detection_verdicts
    """
    store = store or EvidenceStore()
    conf = conf or ConfidenceModel.load()
    embedding = embedding or EmbeddingChannel()
    if decoder is None:
        decoder = Decoder(AdjudicationStore())

    plan = make_plan(task, store)
    if budget is not None and budget > 0:
        plan.budget = budget
    bb = Blackboard(task, plan)
    bb.embedding_mode = embedding.ensure()
    bb.log("plan", budget=plan.budget,
           requirements=[r.key for r in plan.requirements],
           notes=list(plan.notes))

    invs = initial(plan, bb)
    critic = Critic()
    critique = None
    t0 = time.time()

    while invs:
        bb.bump_iteration()
        bb.log("route", agents=[f"{i.agent}:{i.subject}" for i in invs],
               iteration=bb.iteration)
        for inv in invs:
            agent = AGENTS.get(inv.agent)
            if agent is None:
                bb.log("route_error", agent=inv.agent, subject=inv.subject,
                       error="unknown agent")
                continue
            items = agent.invoke(
                AgentContext(task, store, conf, bb, embedding), inv)
            for item in items:
                bb.write(inv.agent, item)
            if not items:
                bb.log("no_evidence", agent=inv.agent, subject=inv.subject)

        critique = critic.review(bb, plan)
        bb.log("critic", verdict=critique.verdict,
               missing=critique.missing,
               missing_critical=critique.missing_critical,
               escalation=critique.escalation, iteration=bb.iteration)
        if critique.verdict != "continue":
            break
        invs = route(critique, plan, bb)

    if critique is None:
        critique = critic.review(bb, plan)

    # ── 译码阶段: 检测闭环(分歧假设 → 裁决/先验 → 判决+弃权) ──
    if task.task_type in _DETECT_TYPES and bb.by_subject("discrepancy_set"):
        det_item = decoder.decode(bb)
        if det_item is not None:
            bb.write("decoder", det_item)
            s = det_item.payload.get("summary", {})
            bb.log("decode", agent="decoder",
                   channel=det_item.channel.value,
                   n_report=s.get("n_report", 0), n_pass=s.get("n_pass", 0),
                   n_abstain=s.get("n_abstain", 0),
                   coverage=s.get("coverage"))

    final = bb.final_context(critique)
    final["elapsed_ms"] = round((time.time() - t0) * 1000, 1)
    bb.log("final", verdict=critique.verdict,
           n_evidence=len(bb.evidence), n_records=len(bb.records))
    if save:
        out_dir = (out_root or RUNS_DIR) / _safe_name(task.task_id)
        bb.save(out_dir)
        final["output_dir"] = str(out_dir)
    return final, bb


def _safe_name(name: str) -> str:
    return re.sub(r'[^\w.-]+', '_', name)[:80]


# ═══════════════════════════════════════════════════════════════
# 批量模式: 场景级检测报告
# ═══════════════════════════════════════════════════════════════

_SCENE_TASK = {  # 场景 → 默认任务类型
    "sc1_usecase_capability": TaskType.COMPLETENESS_CHECK,
    "sc2_flowchart_usecase": TaskType.FLOW_CONSISTENCY,
    "sc3_interface_interface": TaskType.COMPLETENESS_CHECK,
    "sc4_flowchart_capability": TaskType.COMPLETENESS_CHECK,
    "sc5_function_capability": TaskType.COMPLETENESS_CHECK,
    "sc7_usecase_usecase": TaskType.FLOW_CONSISTENCY,
    # sc8: 诚实排除(无表无锚)
}


def run_batch(scenes: list[str] | None = None, limit: int = 0,
              save: bool = True) -> dict[str, Any]:
    """批量跑场景内全部pair → 场景级检测报告(共享store/conf/emb/decoder).

    报告指标: 每场景 {n_pairs, verdict分布, 分歧数, report/pass/abstain,
    裁决覆盖率, π_scene} — 系统级"自动裁决能力"的量化视图.
    """
    sys.path.insert(0, str(BASE / "tools"))
    from run_utils import open_run
    store = EvidenceStore()
    conf = ConfidenceModel.load()
    embedding = EmbeddingChannel()
    decoder = Decoder(AdjudicationStore())

    pairs = store._pair_index()
    from .adjudication import scene_num
    scene_list = scenes or [s for s in _SCENE_TASK if any(
        p.split("_")[0] == scene_num(s) for p in pairs)]
    run = open_run("blackboard_batch",
                   {"scenes": scene_list, "limit": limit})
    rows: list[dict[str, Any]] = []
    for scene in scene_list:
        prefix = scene_num(scene)
        scene_pairs = sorted(p for p in pairs if p.split("_")[0] == prefix)
        if limit:
            scene_pairs = scene_pairs[:limit]
        for pair_id in scene_pairs:
            task = TaskSpec(
                task_id=f"batch_{pair_id}", task_type=_SCENE_TASK.get(
                    scene, TaskType.COMPLETENESS_CHECK),
                pair_id=pair_id)
            try:
                final, _bb = run_task(task, store=store, conf=conf,
                                      embedding=embedding, decoder=decoder,
                                      save=False)
                det = final.get("detection", {}).get("summary", {})
                rows.append({
                    "pair_id": pair_id, "scene": scene,
                    "verdict": final["verdict"],
                    "n_evidence": final["n_evidence"],
                    "n_discrepancies": final.get("n_discrepancies", 0),
                    "n_report": det.get("n_report", 0),
                    "n_pass": det.get("n_pass", 0),
                    "n_abstain": det.get("n_abstain", 0),
                    "n_tool_issue": det.get("n_tool_issue", 0),
                    "coverage": det.get("coverage"),
                    "pi_scene": det.get("pi_scene"),
                })
                run.log(pair_id=pair_id, scene=scene,
                        verdict=final["verdict"],
                        n_report=det.get("n_report", 0))
            except Exception as e:  # 单对失败不阻塞批次(诚实记录)
                rows.append({"pair_id": pair_id, "scene": scene,
                             "verdict": "error", "error": str(e)[:120]})
                run.log(pair_id=pair_id, scene=scene, error=str(e)[:120])

    by_scene: dict[str, Any] = {}
    for r in rows:
        s = by_scene.setdefault(r["scene"], {
            "n_pairs": 0, "n_satisfied": 0, "n_abstain": 0, "n_error": 0,
            "n_discrepancies": 0, "n_report": 0, "n_pass": 0,
            "n_abstain_det": 0, "n_tool_issue": 0,
            "n_adjudicated": 0, "n_verdicts": 0})
        s["n_pairs"] += 1
        if r["verdict"] == "satisfied":
            s["n_satisfied"] += 1
        elif r["verdict"] == "abstain":
            s["n_abstain"] += 1
        else:
            s["n_error"] += 1
        s["n_discrepancies"] += r.get("n_discrepancies", 0)
        s["n_report"] += r.get("n_report", 0)
        s["n_pass"] += r.get("n_pass", 0)
        s["n_abstain_det"] += r.get("n_abstain", 0)
        s["n_tool_issue"] += r.get("n_tool_issue", 0)
        s["n_verdicts"] += (r.get("n_report", 0) + r.get("n_pass", 0)
                            + r.get("n_abstain", 0) + r.get("n_tool_issue", 0))
        s["n_adjudicated"] += round((r.get("coverage") or 0)
                                    * (r.get("n_report", 0)
                                       + r.get("n_pass", 0)
                                       + r.get("n_abstain", 0)
                                       + r.get("n_tool_issue", 0)))
    for s in by_scene.values():
        n = max(1, s["n_verdicts"])
        s["report_rate"] = round(s["n_report"] / n, 3)
        s["auto_coverage"] = round(1 - s["n_abstain_det"] / n, 3)
        s["adjudicated_rate"] = round(s["n_adjudicated"] / n, 3)

    report = {"n_rows": len(rows), "by_scene": by_scene, "rows": rows,
              "run_dir": str(run.path)}
    if save:
        run.save_result(report)
    return report


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def _build_task(args: argparse.Namespace) -> TaskSpec:
    ttype = _TASK_MAP[args.task]
    locator = args.pair or args.entity or "adhoc"
    task_id = f"{args.task}__{locator}"
    return TaskSpec(task_id=task_id, task_type=ttype, query=args.query or "",
                    pair_id=args.pair or "", entity=args.entity or "",
                    entity_id=args.entity_id or "", doc=args.doc or "")


def _print_summary(final: dict[str, Any]) -> None:
    task = final["task"]
    print(f"\n=== [{task['task_id']}] {task['task_type']} ===")
    print(f"    verdict={final['verdict']}  iterations={final['iterations']}"
          f"  evidence={final['n_evidence']}  records={final['n_records']}"
          f"  ({final['elapsed_ms']}ms)  embedding={final['embedding_mode']}")
    for key, s in final.get("subjects", {}).items():
        dig = s.get("digest", {})
        extra = ""
        if key == "table_structure":
            extra = f"type={dig.get('table_type')} items={dig.get('n_items')}"
        elif key == "diagram_structure":
            extra = f"nodes={dig.get('n_nodes')} mapping={dig.get('mapping_confidence')}"
        elif key == "element_correspondence":
            extra = f"matched={dig.get('n_matched')}/{dig.get('n_table')}"
        elif key == "prose_features":
            extra = (f"features={dig.get('n_behaviors', 0)}v+"
                     f"{dig.get('n_enumerations', 0)}enum+"
                     f"{len(dig.get('constraints', []))}cons")
        elif key == "entity_mentions":
            extra = f"id={dig.get('entity_id', '')} mentions={dig.get('n_mentions')}"
        elif key == "chunk_occurrences":
            extra = f"occurrences={dig.get('n_occurrences')}"
        elif key == "drift_status":
            extra = f"status={dig.get('status')} drift={dig.get('n_drift')}"
        elif key == "semantic_links":
            extra = f"matches={dig.get('n_matches')}"
        elif key == "detection_verdicts":
            extra = (f"report={dig.get('n_report')} pass={dig.get('n_pass')} "
                     f"abstain={dig.get('n_abstain')}")
        elif key == "syntax_detections":
            extra = f"detections={dig.get('n_detections')} {dig.get('by_rule')}"
        print(f"    {key:<26} facts={s['n_facts']} hyp={s['n_hypotheses']}"
              f" conf={s['best_confidence']:<6} [{','.join(s['channels'])}] {extra}")
    if final.get("n_discrepancies"):
        print(f"    discrepancies: {final['n_discrepancies']}条"
              f" (检测层输入, 见final_context.discrepancies)")
    det = final.get("detection")
    if det:
        s = det.get("summary", {})
        print(f"    detection: {s.get('n_report', 0)}report/"
              f"{s.get('n_pass', 0)}pass/{s.get('n_abstain', 0)}abstain/"
              f"{s.get('n_tool_issue', 0)}tool (裁决覆盖"
              f"{s.get('coverage', 0):.0%}, π_scene={s.get('pi_scene')})")
        for v in det.get("verdicts", [])[:5]:
            print(f"      [{v.get('action')}] {v.get('dtype')}: "
                  f"{v.get('reason', '')[:70]}")
    if final.get("missing"):
        print(f"    missing: {final['missing']}")
    if final.get("missing_critical"):
        print(f"    missing_critical: {final['missing_critical']}")
    for sem in final.get("open_semantic", []):
        print(f"    [open_semantic] {sem[:90]}")
    if final.get("output_dir"):
        print(f"    artifacts: {final['output_dir']}")


DEMO_TASKS: list[dict[str, Any]] = [
    {"task": "completeness", "pair": "1_001",
     "query": "判断「数据获取」功能在用例图与能力表之间是否存在遗漏"},
    {"task": "flow", "pair": "2_001",
     "query": "「开发工程生成」流程图与用例描述表是否一致(步骤/异常流)"},
    {"task": "recall", "entity": "数据获取",
     "query": "「数据获取」在文档哪些位置出现"},
]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Calibrated Blackboard runner")
    parser.add_argument("--task", choices=sorted(_TASK_MAP), default="completeness")
    parser.add_argument("--pair", default="", help="pair_id, 如 1_001")
    parser.add_argument("--entity", default="", help="实体名(查询式任务)")
    parser.add_argument("--entity-id", default="", help="GJB需求ID")
    parser.add_argument("--doc", default="")
    parser.add_argument("--query", default="")
    parser.add_argument("--budget", type=int, default=0, help="0=用蓝图默认")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--demo", action="store_true", help="跑3个代表性任务")
    parser.add_argument("--batch", action="store_true", help="批量跑场景")
    parser.add_argument("--scene", default="", help="批量模式限定场景(如sc1_usecase_capability)")
    parser.add_argument("--limit", type=int, default=0, help="批量模式每场景pair上限")
    args = parser.parse_args(argv)

    if args.batch:
        scenes = [args.scene] if args.scene else None
        report = run_batch(scenes=scenes, limit=args.limit,
                           save=not args.no_save)
        print(f"\n=== batch: {report['n_rows']}对 ===")
        for scene, s in report["by_scene"].items():
            print(f"  {scene}: pairs={s['n_pairs']} "
                  f"满足={s['n_satisfied']} 弃权={s['n_abstain']} "
                  f"分歧={s['n_discrepancies']} "
                  f"判决: report={s['n_report']} pass={s['n_pass']} "
                  f"abstain={s['n_abstain_det']} tool={s['n_tool_issue']} "
                  f"(report率={s['report_rate']}, 自动覆盖={s['auto_coverage']}, "
                  f"裁决覆盖={s['adjudicated_rate']})")
        print(f"  运行记录: {report['run_dir']}")
        return 0

    if args.demo:
        for spec in DEMO_TASKS:
            task = _build_task(argparse.Namespace(**{**vars(args), **spec}))
            final, _ = run_task(task, save=not args.no_save)
            _print_summary(final)
        return 0

    task = _build_task(args)
    final, bb = run_task(task, save=not args.no_save,
                         budget=args.budget or None)
    _print_summary(final)
    return 0 if final["verdict"] != "abstain" else 2


if __name__ == "__main__":
    raise SystemExit(main())
