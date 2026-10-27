r"""S7人工gold标注工作台(任务3): 双人κ与分歧清单 + gold最终导出.

子命令:
  kappa  第二标注轮一致性(协议§5): verdict三类Cohen'sκ + 定位二值κ +
         Jaccard/span一致率(复用build_localization_gold_template.
         inter_annotator_report) + 分歧清单(仲裁用, 写
         localization_gold/arbitration_list_v1.json);
  export gold_v1.jsonl → data/gjb_438c/qa_frozen/scene1_gold_v1.jsonl:
         逐行协议终检(validate_gold_row)→加is_gold:true→补齐silver兼容字段,
         与silver标签(final_labels.jsonl)同目录, 评测工具切换标签源:
         python tools/eval_qa_module_vs_silver.py --labels gold

gold定稿后须注册MANIFEST(协议§5 R4): python tools/build_data_manifest.py.

用法:
  python tools/finalize_gold.py kappa --gold-a A.jsonl --gold-b B.jsonl
  python tools/finalize_gold.py export
  python tools/finalize_gold.py export --gold gold_v1.jsonl \
      --out data/gjb_438c/qa_frozen/scene1_gold_v1.jsonl

设计约束: 模块顶层零I/O; open()一律encoding="utf-8"; 无裸except; 无类型抑制;
导出文件内容确定性(无时间戳, 测试可快照); 校验失败必须可读报错.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from tools.build_localization_gold_template import (  # noqa: E402
    gold_claim_refs,
    inter_annotator_report,
    jaccard_ratio,
    parse_gold_rows,
    read_jsonl,
    span_char_f1,
    write_jsonl,
)
from tools.collect_gold_annotation import validate_gold_row  # noqa: E402

DEFAULT_GOLD = (BASE / "data/gjb_438c/localization_gold" / "gold_v1.jsonl")
DEFAULT_EXPORT = (BASE / "data/gjb_438c/qa_frozen" / "scene1_gold_v1.jsonl")
DEFAULT_ARBITRATION = (BASE / "data/gjb_438c/localization_gold"
                       / "arbitration_list_v1.json")

TOOL_VERSION = "s7_finalize_gold_v1"
QA_TASK_TYPE = "qa_verdict"


# ---------------------------------------------------------------- κ与分歧清单
def _best_span_f1(spans_a: Sequence[str],
                  spans_b: Sequence[str]) -> float | None:
    if not spans_a or not spans_b:
        return None
    return max(span_char_f1(gold, pred)
               for gold in spans_a for pred in spans_b)


def disagreement_entries(rows_a: Sequence[dict[str, Any]],
                         rows_b: Sequence[dict[str, Any]],
                         ) -> list[dict[str, Any]]:
    """分歧清单(协议§5.3仲裁输入): verdict不同 / refs集合不同 / span不同.

    只覆盖两份标注共有的实例; 单侧独有的实例由κ报告的only_in_a/b列出.
    """
    records_a = {record.instance_id: record
                 for record in parse_gold_rows(rows_a)}
    records_b = {record.instance_id: record
                 for record in parse_gold_rows(rows_b)}
    entries: list[dict[str, Any]] = []
    for iid in sorted(set(records_a) & set(records_b)):
        record_a, record_b = records_a[iid], records_b[iid]
        verdict_diff = record_a.gold_verdict != record_b.gold_verdict
        refs_a = gold_claim_refs(record_a)
        refs_b = gold_claim_refs(record_b)
        refs_diff = set(refs_a) != set(refs_b)
        spans_a = [claim.gold_span for claim in record_a.claims
                   if claim.gold_span]
        spans_b = [claim.gold_span for claim in record_b.claims
                   if claim.gold_span]
        span_diff = spans_a != spans_b
        if not (verdict_diff or refs_diff or span_diff):
            continue
        entries.append({
            "instance_id": iid,
            "diff_kinds": [kind for kind, differs in (
                ("verdict", verdict_diff), ("refs", refs_diff),
                ("span", span_diff)) if differs],
            "verdict": [record_a.gold_verdict, record_b.gold_verdict],
            "refs": [list(refs_a), list(refs_b)],
            "jaccard": round(jaccard_ratio(refs_a, refs_b), 4),
            "span_best_f1": _best_span_f1(spans_a, spans_b),
            "arbitration_rule": "verdict分歧→第三人独立三态; refs分歧→"
                                "重执最小充分集判据; span分歧→取更短(协议§5.3)",
        })
    return entries


def run_kappa(gold_a: Path, gold_b: Path,
              arbitration_path: Path = DEFAULT_ARBITRATION,
              ) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    """κ报告 + 分歧清单落盘; 返回(报告, 分歧清单, 清单路径)."""
    rows_a = read_jsonl(gold_a)
    rows_b = read_jsonl(gold_b)
    report = inter_annotator_report(rows_a, rows_b)
    entries = disagreement_entries(rows_a, rows_b)
    report = dict(report)
    report["n_disagreements"] = len(entries)
    report["disagreement_instance_ids"] = [
        entry["instance_id"] for entry in entries]
    arbitration_path.parent.mkdir(parents=True, exist_ok=True)
    arbitration_path.write_text(
        json.dumps({
            "tool_version": TOOL_VERSION,
            "gold_a": str(gold_a),
            "gold_b": str(gold_b),
            "n_disagreements": len(entries),
            "entries": entries,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    return report, entries, arbitration_path


# ---------------------------------------------------------------- gold导出
def export_row(row: dict[str, Any]) -> dict[str, Any]:
    """gold行→导出行: 补齐silver兼容字段(评测工具复用)+is_gold标记.

    校验已由validate_gold_row把关(claim_verdict/gold_evidence_refs一致),
    此处只做字段补齐(setdefault, 不覆盖已有值).
    """
    out = dict(row)
    out.setdefault("final_verdict", str(row["gold_verdict"]))
    out.setdefault("final_model", "human")
    out.setdefault("label_source", "human_annotation_workbench_v1")
    out.setdefault("status", "final_human_gold")
    claims = [dict(claim) for claim in row.get("claims") or []]
    for claim in claims:
        claim.setdefault("verdict",
                         claim.get("claim_verdict", row["gold_verdict"]))
        claim.setdefault("evidence_refs",
                         list(claim.get("gold_evidence_refs") or []))
    out["claims"] = claims
    out["is_gold"] = True
    return out


def run_export(gold_path: Path, out_path: Path) -> dict[str, Any]:
    """gold_v1.jsonl→scene1_gold_v1.jsonl(逐行协议终检+is_gold+兼容字段)."""
    if out_path.resolve() == gold_path.resolve():
        raise ValueError("out_path不得与gold输入路径相同")
    rows = read_jsonl(gold_path)
    if not rows:
        raise ValueError(f"gold文件为空: {gold_path}")
    errors: list[str] = []
    for row in rows:
        errors.extend(validate_gold_row(row))
    if errors:
        raise ValueError(
            "gold行协议终检失败, 未导出(逐条修复后重跑):\n  "
            + "\n  ".join(errors))
    exported = [export_row(row) for row in rows]
    write_jsonl(out_path, exported)
    task_dist: dict[str, int] = {}
    verdict_dist: dict[str, int] = {}
    for row in exported:
        task = str(row.get("task_type", QA_TASK_TYPE))
        task_dist[task] = task_dist.get(task, 0) + 1
        verdict = str(row.get("gold_verdict", ""))
        verdict_dist[verdict] = verdict_dist.get(verdict, 0) + 1
    return {
        "tool_version": TOOL_VERSION,
        "gold_path": str(gold_path),
        "out_path": str(out_path),
        "n_exported": len(exported),
        "task_distribution": dict(sorted(task_dist.items())),
        "verdict_distribution": dict(sorted(verdict_dist.items())),
        "notes": [
            "导出前逐行通过协议终检(validate_gold_row: 三态/NIE refs空/"
            "refs存在/span子串/status=completed)",
            "评测切换: python tools/eval_qa_module_vs_silver.py --labels gold",
            "gold定稿后注册MANIFEST: python tools/build_data_manifest.py"
            "(协议§5 R4, tests/test_manifest.py保护)",
        ],
    }


# ---------------------------------------------------------------- CLI
def _reconfigure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace(
            "-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S7人工gold标注工作台(任务3): κ(kappa) + 最终导出(export)")
    sub = parser.add_subparsers(dest="command", required=True)
    kappa = sub.add_parser(
        "kappa", help="双人标注一致性(κ/Jaccard)+分歧清单(仲裁用)")
    kappa.add_argument("--gold-a", type=Path, required=True,
                       help="标注A JSONL(第一标注轮)")
    kappa.add_argument("--gold-b", type=Path, required=True,
                       help="标注B JSONL(第二标注轮)")
    kappa.add_argument("--out-list", type=Path, default=DEFAULT_ARBITRATION,
                       help=f"分歧清单输出(默认{DEFAULT_ARBITRATION})")
    export = sub.add_parser("export", help="gold_v1→qa_frozen/scene1_gold")
    export.add_argument("--gold", type=Path, default=DEFAULT_GOLD,
                        help=f"待导出gold JSONL(默认{DEFAULT_GOLD})")
    export.add_argument("--out", type=Path, default=DEFAULT_EXPORT,
                        help=f"导出路径(默认{DEFAULT_EXPORT})")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _reconfigure_stdout()
    args = build_arg_parser().parse_args(argv)
    if args.command == "kappa":
        try:
            report, entries, list_path = run_kappa(
                args.gold_a, args.gold_b, arbitration_path=args.out_list)
        except FileNotFoundError as exc:
            sys.exit(f"输入文件不存在: {exc.filename}(两份标注JSONL均须存在)")
        from tools.run_utils import open_run

        run = open_run("finalize_gold_kappa", {
            "gold_a": str(args.gold_a), "gold_b": str(args.gold_b),
            "arbitration_list": str(args.out_list),
            "tool_version": TOOL_VERSION})
        run.save_result(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"分歧清单: {list_path}({len(entries)}条, 供仲裁)")
        print(f"result.json: {run.path / 'result.json'}")
        return
    try:
        summary = run_export(args.gold, args.out)
    except FileNotFoundError as exc:
        sys.exit(f"gold输入不存在: {exc.filename}"
                 "(先运行 python tools/collect_gold_annotation.py)")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"导出: {args.out}({summary['n_exported']}行, is_gold=true)")


if __name__ == "__main__":
    main()
