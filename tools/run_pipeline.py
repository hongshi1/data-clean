#!/usr/bin/env python3
"""数据管线统一入口: 从原始.doc到最终评测数据.

对应文档: 84号. 五段式:
  P1 parse      .doc → mineru_standard + dual_source(冻结) + anchor_v3(冻结)
  P2 corpus     多源 → structured_corpus_v1 (27,473对象)
  P3 features   corpus → 特征矩阵/语义/Visio/BGE快照
  P4 candidates corpus → 原子候选/覆盖findings/证据图
  P5 eval       候选 + QA → 评测集(localization_gold)

用法:
  python tools/run_pipeline.py --list      # 列出所有步骤
  python tools/run_pipeline.py --dry-run   # 显示执行计划
  python tools/run_pipeline.py --from raw  # 全量重建
  python tools/run_pipeline.py --from corpus --to features  # 指定段
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

# ── 管线步骤定义 ──────────────────────────────────────────

STEPS = [
    # P1: 解析层
    {
        "id": "P1.mineru",
        "phase": "parse",
        "desc": "MinerU解析: .doc→md+content_list+图",
        "tool": "tools/srs_mineru_parse.py",
        "input": "data/软件需归样例数据集/*.doc",
        "output": "data/gjb_438c/mineru_standard/<16doc>/office/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P1.dual_source",
        "phase": "parse",
        "desc": "textutil双源(冻结, macOS产物)",
        "tool": "(无脚本, 冻结资产)",
        "input": "data/软件需归样例数据集/*.doc",
        "output": "data/gjb_438c/dual_source/*.html",
        "status": "frozen",
        "frozen": True,
    },
    {
        "id": "P1.visio",
        "phase": "parse",
        "desc": "Visio提取(冻结, 脚本已归档)",
        "tool": "tools/archive/.../m0_anchor_extract_v3.py",
        "input": "data/gjb_438c/visio_docx/*.docx",
        "output": "data/gjb_438c/anchor_v3/anchors_v3.json",
        "status": "frozen",
        "frozen": True,
    },
    # P2: 结构化层
    {
        "id": "P2.corpus",
        "phase": "corpus",
        "desc": "结构化语料: 多源→27,473对象",
        "tool": "tools/build_structured_corpus.py",
        "input": "mineru_standard + dual_source + anchor_v3 + qa_frozen",
        "output": "data/gjb_438c/structured_corpus_v1/",
        "status": "done",
        "frozen": False,
    },
    # P3: 特征层
    {
        "id": "P3.feature_matrix_v1",
        "phase": "features",
        "desc": "特征矩阵v1: 7类特征",
        "tool": "tools/build_feature_matrix.py",
        "input": "structured_corpus_v1",
        "output": "data/gjb_438c/feature_matrix_v1/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P3.feature_matrix_v2",
        "phase": "features",
        "desc": "特征矩阵v2: 句span/引用",
        "tool": "tools/build_feature_matrix_v2.py",
        "input": "structured_corpus_v1",
        "output": "data/gjb_438c/feature_matrix_v2/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P3.semantic_features",
        "phase": "features",
        "desc": "语义特征: 实体分类/泳道/接口",
        "tool": "tools/build_semantic_features_v2.py",
        "input": "structured_corpus_v1 + anchor_v2/v3",
        "output": "data/gjb_438c/semantic_features_v2/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P3.visio_features",
        "phase": "features",
        "desc": "Visio特征: 节点/边/对齐",
        "tool": "tools/build_visio_features_v2.py",
        "input": "anchor_v2 + anchor_v3",
        "output": "data/gjb_438c/visio_features_v2/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P3.bge_snapshot",
        "phase": "features",
        "desc": "BGE快照: 27,473×1024维冻结向量",
        "tool": "tools/build_feature_snapshot.py",
        "input": "structured_corpus_v1",
        "output": "data/gjb_438c/feature_snapshot_v1/",
        "status": "done",
        "frozen": False,
    },
    # P4: 候选发现层
    {
        "id": "P4.evidence_graph",
        "phase": "candidates",
        "desc": "证据图: 链接/条目/发现",
        "tool": "tools/build_evidence_graph.py",
        "input": "structured_corpus_v1",
        "output": "data/gjb_438c/evidence_graph_v1/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P4.evidence_graph_v2",
        "phase": "candidates",
        "desc": "证据图v2: silver升级+合同义务",
        "tool": "tools/build_evidence_graph_v2.py",
        "input": "evidence_graph_v1",
        "output": "data/gjb_438c/evidence_graph_v2/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P4.atom_candidates",
        "phase": "candidates",
        "desc": "原子化候选: 4槽原子+同参配对",
        "tool": "tools/build_atom_conflict_candidates.py",
        "input": "structured_corpus_v1 + srs_kb.json",
        "output": "data/gjb_438c/atom_candidates_v1/",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P4.table_atoms",
        "phase": "candidates",
        "desc": "表行原子化: 双通道(表头列+格内段)",
        "tool": "tools/build_table_atoms.py",
        "input": "structured_corpus_v1/tables.jsonl + srs_kb.json",
        "output": "data/gjb_438c/atom_candidates_v1/table_*.jsonl",
        "status": "done",
        "frozen": False,
    },
    {
        "id": "P4.coverage_findings",
        "phase": "candidates",
        "desc": "覆盖差异检测: 平行表行级比对",
        "tool": "tools/build_coverage_findings.py",
        "input": "structured_corpus_v1/tables.jsonl",
        "output": "data/gjb_438c/coverage_findings_v1/",
        "status": "done",
        "frozen": False,
    },
    # P5: 评测层
    {
        "id": "P5.localization_gold",
        "phase": "eval",
        "desc": "评测集: 108实例(91QA+17违例)",
        "tool": "tools/seed_violations_to_db.py",
        "input": "violation_evalset + qa_frozen",
        "output": "data/gjb_438c/localization_gold/",
        "status": "done",
        "frozen": False,
    },
]

PHASES = ["parse", "corpus", "features", "candidates", "eval"]
PHASE_NAMES = {
    "parse": "P1 解析层",
    "corpus": "P2 结构化层",
    "features": "P3 特征层",
    "candidates": "P4 候选发现层",
    "eval": "P5 评测层",
}


def run_step(step: dict, dry_run: bool = False) -> bool:
    """执行单个管线步骤."""
    tool = step["tool"]
    if step.get("frozen") or not tool.startswith("tools/"):
        print(f"  [SKIP] {step['id']}: {step['desc']} "
              f"({'冻结' if step.get('frozen') else '外部输入'})")
        return True

    tool_path = BASE / tool
    if not tool_path.exists():
        print(f"  [MISS] {step['id']}: 工具不存在 {tool}")
        return False

    cmd = [sys.executable, "-X", "utf8", str(tool_path)]
    if dry_run:
        print(f"  [PLAN] {step['id']}: {step['desc']}")
        print(f"         → {tool}")
        return True

    print(f"  [RUN ] {step['id']}: {step['desc']}")
    print(f"         → {tool}")
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, cwd=str(BASE), timeout=1800,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        elapsed = time.perf_counter() - t0
        if r.returncode == 0:
            print(f"  [ OK ] {step['id']} ({elapsed:.1f}s)")
            return True
        print(f"  [FAIL] {step['id']} ({elapsed:.1f}s)")
        print(f"         stderr: {r.stderr[:200] if r.stderr else '无'}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [FAIL] {step['id']} (超时1800s)")
        return False
    except (OSError, ValueError) as e:
        print(f"  [FAIL] {step['id']}: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="列出所有步骤")
    ap.add_argument("--dry-run", action="store_true", help="只显示计划")
    ap.add_argument("--from", dest="from_phase", default="raw",
                    choices=["raw"] + PHASES,
                    help="起始阶段(默认raw=从头)")
    ap.add_argument("--to", dest="to_phase", default="eval",
                    choices=PHASES,
                    help="结束阶段(默认eval=全部)")
    args = ap.parse_args()

    if args.list:
        print("=" * 70)
        print("数据管线步骤清单")
        print("=" * 70)
        current_phase = ""
        for step in STEPS:
            if step["phase"] != current_phase:
                current_phase = step["phase"]
                print(f"\n{PHASE_NAMES[current_phase]}:")
                print("-" * 40)
            status = {"done": "✅", "frozen": "🔒", "pending": "⬜"}.get(
                step["status"], "?")
            print(f"  {status} {step['id']:<28s} {step['desc']}")
            print(f"     输入: {step['input']}")
            print(f"     输出: {step['output']}")
        print(f"\n总计: {len(STEPS)}步骤 "
              f"({sum(1 for s in STEPS if s['status'] == 'done')}完成, "
              f"{sum(1 for s in STEPS if s['status'] == 'frozen')}冻结)")
        return 0

    # 确定执行范围
    if args.from_phase == "raw":
        start_idx = 0
    else:
        start_idx = next(
            (i for i, s in enumerate(STEPS) if s["phase"] == args.from_phase),
            0)
    end_idx = next(
        (i for i, s in enumerate(STEPS) if s["phase"] == args.to_phase),
        len(STEPS))

    # 找到该阶段的最后一步
    end_phase = args.to_phase
    for i in range(len(STEPS) - 1, -1, -1):
        if STEPS[i]["phase"] == end_phase:
            end_idx = i + 1
            break

    print("=" * 70)
    print(f"数据管线: {args.from_phase} → {args.to_phase}")
    print(f"步骤范围: [{start_idx}:{end_idx}] ({end_idx - start_idx}步)")
    print("=" * 70)

    n_ok = n_fail = n_skip = 0
    for step in STEPS[start_idx:end_idx]:
        if run_step(step, args.dry_run):
            if step.get("frozen") or not step["tool"].startswith("tools/"):
                n_skip += 1
            else:
                n_ok += 1
        else:
            n_fail += 1
            if not args.dry_run:
                print(f"\n管线中断于: {step['id']}")
                break

    print(f"\n{'=' * 70}")
    print(f"管线{'计划' if args.dry_run else '执行'}完成: "
          f"成功{n_ok} / 失败{n_fail} / 跳过(冻结){n_skip}")
    return 1 if n_fail > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
