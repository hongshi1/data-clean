"""X1前后对比评测(102号规格Step A+C): D3学生约束解码off/on.

两个模式(--mode):
  baseline    = 无约束judge + parse_fail计量(Step A基线; 生成路径与
                既有无约束评测逐位一致, 可与E1/v2b的violations17记录
                交叉核对)
  constrained = X1约束解码(judge(constrained=True): verdict枚举trie+
                JSON骨架掩码+span/quote后验对齐)

指标(对比口径):
  - 结构失败率: baseline = parse_fail(解析全失败/非dictJSON) ∪
    verdict默认NIE清洗 ∪ issues缺失(三者分别报+复合);
    constrained = 骨架未收尾/JSON非法(parse_fail), 目标0
  - verdict分布与refute检出(violations17全gold refute)
  - n_issues产出与span后验对齐(exact区间/字面find/证据ref有效;
    两模式同口径计算, constrained另报其自带flag)
  - 延迟(贪心解码, 约束增量目标<10%)
  - 约束干预率: 掩码改变argmax的步数占比(constrained特有)

产出(runs协议): data/gjb_438c/runs/eval_d3_x1_<hash>_<ts>/
用法:
  python tools/eval_d3_x1.py --mode baseline
  python tools/eval_d3_x1.py --mode constrained
  python tools/eval_d3_x1.py --mode constrained --determinism-check
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    classification_metrics,
    load_frozen_qa,
    load_silver_labels,
)
from tools import eval_d3_student  # noqa: E402
from tools.eval_d3_student import judge  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
SPLIT = BASE / "data/gjb_438c/qa_frozen/dev_test_split_v1.json"
VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"

VERDICTS = ("support", "refute", "not_in_evidence")


def _issue_stats(issues: list[dict], answer: str) -> dict:
    """span/quote后验对齐(两模式同口径): exact=answer[s:e]==quote;
    find=exact或quote⊂answer; constrained的issue另有自带flag
    (span_verified/literal_faithful/evidence_ref_ok)在details里."""
    n = 0
    n_exact = 0
    n_find = 0
    n_ref_ok = 0
    n_flagged = 0
    for issue in issues:
        quote = str(issue.get("quote", ""))
        span = issue.get("span")
        exact = False
        if isinstance(span, list) and len(span) == 2:
            start, end = int(span[0]), int(span[1])
            exact = 0 <= start < end <= len(answer) \
                and answer[start:end] == quote
        find_ok = exact or (bool(quote) and quote in answer)
        n += 1
        n_exact += exact
        n_find += find_ok
        if "span_verified" in issue:
            n_flagged += 1
            n_ref_ok += bool(issue.get("evidence_ref_ok"))
    return {"n_issues": n, "span_exact": n_exact, "span_find": n_find,
            "evidence_ref_ok": n_ref_ok, "n_flagged": n_flagged}


def _run_corpus(records: list[dict], labels: dict[str, str],
                constrained: bool, tag: str = "",
                log=None) -> list[dict]:
    details: list[dict] = []
    eval_d3_student.JUDGE_TRACE.clear()
    for rec in records:
        answer = str(rec["answer"])
        evidences = [str(e["text"]) for e in rec["evidence"]]
        instance_id = str(rec["instance_id"])
        verdict, issues, elapsed = judge(
            str(rec["question"]), answer, evidences,
            constrained=constrained)
        row = {
            "instance_id": instance_id,
            "gold": labels.get(instance_id, "not_in_evidence"),
            "verdict": verdict,
            "elapsed_s": round(float(elapsed), 3),
        }
        row.update(_issue_stats(issues, answer))
        details.append(row)
        print(f"  {instance_id} gold={row['gold']:16s} "
              f"pred={verdict or '<结构未完成>':16s} "
              f"issues={row['n_issues']} "
              f"(exact {row['span_exact']}/{row['n_issues']}) "
              f"{row['elapsed_s']}s", flush=True)
    traces = eval_d3_student.JUDGE_TRACE
    if len(traces) != len(details):
        raise RuntimeError(
            f"trace与实例数不一致: {len(traces)} vs {len(details)}")
    for row, trace in zip(details, traces):
        row["stage"] = trace.get("stage")
        row["parse_fail"] = bool(trace.get("parse_fail", False))
        row["verdict_defaulted"] = bool(
            trace.get("verdict_defaulted", False))
        row["issues_missing"] = bool(trace.get("issues_missing", False))
        row["content_head"] = trace.get("content_head", "")
        clog = trace.get("constraint_log")
        if clog:
            row["constraint_log"] = {
                "steps": clog["steps"],
                "interventions": clog["interventions"],
                "completed": clog["completed"],
                "n_new_tokens": clog["n_new_tokens"]}
        if trace.get("stage") in ("fail", "parsed_non_dict"):
            row["parse_fail"] = True          # baseline结构失败口径
        if log is not None:
            log.log(tag=tag, **row)           # 逐实例流式落盘
    return details


def _aggregate(details: list[dict], constrained: bool,
               n_records: int) -> dict:
    """汇总: 结构失败率/verdict分布/检出/n_issues/span/延迟/干预."""
    n = len(details)
    stages = Counter(d["stage"] for d in details)
    parse_fail = sum(bool(d["parse_fail"]) for d in details)
    defaulted = sum(bool(d["verdict_defaulted"]) for d in details)
    issues_missing = sum(bool(d["issues_missing"]) for d in details)
    composite = sum(bool(d["parse_fail"] or d["verdict_defaulted"]
                         or d["issues_missing"]) for d in details)
    verdicts = Counter(d["verdict"] or "<结构未完成>" for d in details)
    valid = [d for d in details if d["verdict"] in VERDICTS]
    y_true = [d["gold"] for d in valid]
    y_pred = [d["verdict"] for d in valid]
    metrics = classification_metrics(y_true, y_pred) if valid else {}
    refute_gold = [d for d in valid if d["gold"] == "refute"]
    refute_hit = sum(d["verdict"] == "refute" for d in refute_gold)
    n_issues = sum(d["n_issues"] for d in details)
    span_exact = sum(d["span_exact"] for d in details)
    span_find = sum(d["span_find"] for d in details)
    ref_ok = sum(d["evidence_ref_ok"] for d in details)
    latencies = [d["elapsed_s"] for d in details]
    steps = sum((d.get("constraint_log") or {}).get("steps", 0)
                for d in details)
    interventions = sum(
        (d.get("constraint_log") or {}).get("interventions", 0)
        for d in details)
    completed = sum(
        bool((d.get("constraint_log") or {}).get("completed"))
        for d in details)
    summary = {
        "n_records": n_records,
        "n_valid_verdicts": len(valid),
        "structural_failure": {
            "parse_fail": parse_fail,
            "verdict_defaulted_to_nie": defaulted,
            "issues_missing": issues_missing,
            "composite_any": composite,
            "rate_composite": round(composite / max(1, n), 4),
        },
        "verdict_distribution": dict(verdicts),
        "refute_recall_on_gold_refute": {
            "gold_refute": len(refute_gold) + (n - len(valid)),
            "refute_correct": refute_hit,
        },
        "n_issues_total": n_issues,
        "instances_with_issues": sum(d["n_issues"] > 0 for d in details),
        "span_alignment": {
            "n_issues": n_issues,
            "span_exact": span_exact,
            "span_find": span_find,
            "rate_exact": round(span_exact / max(1, n_issues), 4),
            "rate_find": round(span_find / max(1, n_issues), 4),
            "evidence_ref_ok": ref_ok,
        },
        "stage_counts": dict(stages),
        "latency": {
            "mean_s": round(statistics.fmean(latencies), 3) if latencies
            else None,
            "median_s": round(statistics.median(latencies), 3)
            if latencies else None,
            "total_s": round(sum(latencies), 1),
        },
    }
    if metrics:
        summary["classification_on_valid"] = metrics
    if constrained:
        summary["constraint"] = {
            "completed": completed,
            "steps_total": steps,
            "interventions_total": interventions,
            "intervention_rate": round(
                interventions / max(1, steps), 4),
        }
    return summary


def _determinism_check(records: list[dict]) -> bool:
    """同输入复跑贪心解码, 比对(verdict, issues)序列(102号验收:
    GPU贪心复跑同结果)."""
    eval_d3_student.JUDGE_TRACE.clear()
    runs = []
    for _ in range(2):
        seq = []
        for rec in records:
            verdict, issues, _elapsed = judge(
                str(rec["question"]), str(rec["answer"]),
                [str(e["text"]) for e in rec["evidence"]],
                constrained=True)
            seq.append((verdict, json.dumps(issues, ensure_ascii=False,
                                             sort_keys=True)))
        runs.append(seq)
    return runs[0] == runs[1]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["baseline", "constrained"],
                        required=True)
    parser.add_argument("--corpus", choices=["violations", "test46", "both"],
                        default="violations")
    parser.add_argument("--adapter", default="models/llm/d3_student_v2b")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--determinism-check", action="store_true",
                        help="constrained模式下复跑两遍比对(贪心确定性)")
    args = parser.parse_args()

    constrained = args.mode == "constrained"
    eval_d3_student._ADAPTER = str(BASE / args.adapter)

    corpora: list[tuple[str, list[dict], dict[str, str]]] = []
    if args.corpus in ("violations", "both"):
        vio = [json.loads(line) for line in
               VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
        if args.limit:
            vio = vio[:args.limit]
        corpora.append(("violations17", vio, {
            str(r["instance_id"]): str(r["expected_verdict"])
            for r in vio}))
    if args.corpus in ("test46", "both"):
        silver = load_silver_labels(SILVER)
        split = json.loads(SPLIT.read_text(encoding="utf-8"))
        dev_ids = set(split["dev"])
        test = [r for r in load_frozen_qa()
                if r["instance_id"] not in dev_ids]
        if args.limit:
            test = test[:args.limit]
        corpora.append(("test46", test, silver))

    run = open_run("eval_d3_x1", {
        "mode": args.mode,
        "corpus": args.corpus,
        "adapter": args.adapter,
        "limit": args.limit or None,
        "max_new_tokens": 512,
        "determinism_check": bool(args.determinism_check),
        "decoding": "greedy(do_sample=False)",
    })
    print(f"X1对比评测 mode={args.mode} corpus={args.corpus} "
          f"adapter={args.adapter}")
    print(f"run目录: {run.path.name}")
    started = time.time()

    result: dict = {
        "schema": "d3_x1_eval_v1",
        "mode": args.mode,
        "adapter": args.adapter,
        "spec": "docs/srs_project/102_x1_constrained_decoding_spec.md",
    }
    for tag, records, labels in corpora:
        print(f"[{tag}] n={len(records)}")
        details = _run_corpus(records, labels, constrained, tag=tag,
                              log=run)
        summary = _aggregate(details, constrained, len(records))
        result[tag] = {"summary": summary, "details": details}
        sf = summary["structural_failure"]
        sa = summary["span_alignment"]
        lat = summary["latency"]
        print(f"[{tag}] 结构失败(复合) {sf['composite_any']}/{summary['n_records']}"
              f" rate={sf['rate_composite']} "
              f"(parse_fail {sf['parse_fail']}, "
              f"默认NIE {sf['verdict_defaulted_to_nie']}, "
              f"issues缺失 {sf['issues_missing']})")
        print(f"[{tag}] verdict分布 {summary['verdict_distribution']} "
              f"refute检出 {summary['refute_recall_on_gold_refute']}")
        print(f"[{tag}] issues {summary['n_issues_total']} "
              f"span exact {sa['span_exact']}/{sa['n_issues']}"
              f"(rate {sa['rate_exact']}) "
              f"find {sa['span_find']}/{sa['n_issues']}"
              f"(rate {sa['rate_find']})")
        print(f"[{tag}] 延迟 mean={lat['mean_s']}s median={lat['median_s']}s"
              f" total={lat['total_s']}s")
        if constrained:
            con = summary["constraint"]
            print(f"[{tag}] 约束: completed {con['completed']}/"
                  f"{summary['n_records']}, 干预率 "
                  f"{con['intervention_rate']}"
                  f"({con['interventions_total']}/{con['steps_total']}步)")

    if args.determinism_check:
        if not constrained:
            print("--determinism-check仅在constrained模式有效, 跳过")
        else:
            tag, records, _labels = corpora[0]
            print(f"[{tag}] 确定性复跑核对(2遍)...")
            same = _determinism_check(records)
            result["determinism_check"] = {
                "identical": same, "corpus": tag}
            print(f"[{tag}] 复跑同结果: {same}")

    result["elapsed_s"] = round(time.time() - started, 1)
    run.save_result(result)
    print(f"→ {run.path / 'result.json'} ({result['elapsed_s']}s)")


if __name__ == "__main__":
    main()
