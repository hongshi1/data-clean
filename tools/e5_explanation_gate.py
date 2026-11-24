"""E5 Step 1: 教师解释质量闸门 (docs/srs_project/100号规格 Step 1).

对 d3_train_v3f.jsonl + d3_teacher_labels_v1.jsonl 合并去重(按instance_id,
v3f优先——512个重叠id经实证逐字节一致)后所有带非空issues的条目(约505条)
做教师三reward评分(faithful/truthful/useful, 各1-3分):

  1. 机械检查先行(本地代码, 不耗API): quote字面包含于answer / span区间与
     quote一致 / evidence_ref指向的ev-N在范围内. 不通过的issue直接
     faithful=1, 不送教师;
  2. 教师只评机械检查不了的维度: GLM-5.3经 tools/llm_teacher.llm_json_teacher
     (cache=True, 兼容历史缓存; response_contract=json_final_content_v2 +
     reasoning_effort=low — 与d3_teacher_labels同一教师调用契约);
  3. 低分不删除只降权(降采样而非剔除): verdict采样权重表——
     refute行 any(faithful<2 or truthful<2) → downweight=True +
     sample_weight=0.3, 其余1.0.

产物(只新增, 不改既有文件):
  data/gjb_438c/distillation/d3_train_v3f_gated.jsonl
      1336行原v3f行(顺序/字段不变), 带issues行每条issue追加
      "quality": {faithful, truthful, useful, gate_reason, scored_by},
      全行追加 sample_weight/downweight 两个字段;
  runs/e5_explanation_gate_*/gate_scores_union.jsonl
      合并去重后全部带issues条目的完整行+quality(含v3f之外的
      teacher-only条目, 供e5_minimal_pairs.py --extra-gate 使用);
  runs/e5_explanation_gate_*/result.json
      质量分布报告(机械过滤量/API调用量/缓存命中率/数据质量例证).

用法: $env:PYTHONUTF8='1'; python tools/e5_explanation_gate.py
      [--limit N] [--dry-run] [--resume-run runs/e5_explanation_gate_...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

BASE = Path(__file__).resolve().parents[1]
for _p in (str(BASE), str(BASE / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from run_utils import RunHandle, open_run  # noqa: E402
from tools.llm_teacher import llm_json_teacher  # noqa: E402

V3F = BASE / "data/gjb_438c/distillation/d3_train_v3f.jsonl"
TEACHER_LABELS = BASE / "data/gjb_438c/distillation/d3_teacher_labels_v1.jsonl"
OUT_GATED = BASE / "data/gjb_438c/distillation/d3_train_v3f_gated.jsonl"
UNION_ARTIFACT = "gate_scores_union.jsonl"

#: verdict采样权重表: 低分refute降采样(0.3)而非剔除
VERDICT_BASE_WEIGHTS = {"support": 1.0, "refute": 1.0, "not_in_evidence": 1.0}
LOW_QUALITY_WEIGHT = 0.3

MAX_TOKENS = 6000
TEMPERATURE = 0.1
EXTRA_PAYLOAD = {"response_contract": "json_final_content_v2",
                 "reasoning_effort": "low"}
RETRY_SUFFIX = ("\n\n上一次输出无法解析。请严格只输出一个JSON对象"
                "（形如{\"scores\": [{\"idx\": 0, \"faithful\": 3, "
                "\"truthful\": 3, \"useful\": 3, \"reason\": \"...\"}]}），"
                "不要markdown代码块。")

TeacherFn = Callable[..., tuple[dict, str, bool]]

#: 网络错误退避序列(秒; 测试里monkeypatch为0)
_NET_RETRY_DELAYS: tuple[int, ...] = (0, 8, 20, 45)


class TeacherUnavailable(RuntimeError):
    """网络错误重试耗尽(该条目保持pending不落盘, 续跑可补评分)."""

SYSTEM = (
    "你是SRS一致性校验的解释质量审查员。下面给你一条已判定refute的校验记录"
    "（问题、待校验answer、全部证据、教师判定、若干条定位issue）。"
    "对每条issue的教师解释做三维度评分（各1-3分，只依据给定材料，不引入外部知识）：\n"
    "faithful（引用忠实）：\n"
    "  3=quote是answer中承载该矛盾的准确片段，且evidence_ref指向的证据确实"
    "包含与quote矛盾的内容；\n"
    "  2=引用基本成立但有偏差（quote过长或过短、包含与矛盾无关的成分，"
    "或evidence_ref不是矛盾所在的最佳证据）；\n"
    "  1=引用不忠实（quote与该矛盾无关，或evidence_ref指向的证据不含"
    "支撑该矛盾的内容）。\n"
    "truthful（内容真实）：\n"
    "  3=explanation与证据内容一致、与refute判定自洽；\n"
    "  2=大体正确但有超出证据的措辞或轻微夸大；\n"
    "  1=与证据矛盾、引入证据外信息、或与判定不自洽。\n"
    "useful（解释有用）：\n"
    "  3=指明差异的具体所在（数值级/枚举成员级/绑定级，点名冲突的值、"
    "成员或对象）；\n"
    "  2=指明差异方向但不够具体；\n"
    "  1=泛泛而谈或仅复述判定。\n"
    "只输出JSON。"
)
SPEC = ('输出JSON：{"scores": [{"idx": issue编号, "faithful": 1-3, '
        '"truthful": 1-3, "useful": 1-3, "reason": "一句话理由"}]}，'
        "scores按输入issues的编号逐条给出，不得遗漏。")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_union(v3f_path: Path = V3F,
               teacher_path: Path = TEACHER_LABELS) -> list[dict]:
    """两文件合并去重(按instance_id, v3f优先)→带非空issues的条目(确定序)."""
    merged: dict[str, dict] = {}
    for row in read_jsonl(teacher_path):
        merged[str(row["instance_id"])] = dict(row)
    for row in read_jsonl(v3f_path):
        merged[str(row["instance_id"])] = dict(row)
    entries = [r for r in merged.values() if r.get("issues")]
    entries.sort(key=lambda r: str(r["instance_id"]))
    return entries


def mechanical_check(answer: str, issue: dict,
                     n_evidence: int) -> tuple[bool, str]:
    """机械检查(不耗API): quote在场/span一致/evidence_ref在范围内."""
    quote = str(issue.get("quote", ""))
    if not quote.strip():
        return False, "mechanical_fail:empty_quote"
    if quote not in answer:
        return False, "mechanical_fail:quote_not_in_answer"
    span = issue.get("span")
    if not (isinstance(span, list) and len(span) == 2):
        return False, "mechanical_fail:span_invalid"
    start, end = int(span[0]), int(span[1])
    if not (0 <= start < end <= len(answer) and answer[start:end] == quote):
        return False, "mechanical_fail:span_invalid"
    match = re.search(r"ev-(\d+)", str(issue.get("evidence_ref", "")))
    if not match:
        return False, "mechanical_fail:evidence_ref_unparseable"
    if not (1 <= int(match.group(1)) <= max(n_evidence, 1)):
        return False, "mechanical_fail:evidence_ref_out_of_range"
    return True, ""


def build_gate_prompt(entry: dict, indices: list[int]) -> str:
    evidence = [re.sub(r"\s+", " ", str(e)).strip()
                for e in (entry.get("evidence") or [])]
    lines = [f"【问题】{entry.get('question', '')}", "",
             "【待校验answer】", str(entry.get("answer", "")), "", "【证据】"]
    for k, ev in enumerate(evidence, 1):
        lines.append(f"ev-{k}: {ev[:800]}")
    lines += ["", f"【教师判定】{entry.get('verdict', '')}", "", "【待评分issues】"]
    for k, j in enumerate(indices):
        issue = entry["issues"][j]
        lines.append(f"issue {k}:")
        lines.append(f"  quote: {issue.get('quote', '')}")
        lines.append(f"  span: {issue.get('span')}")
        lines.append(f"  rule_id: {issue.get('rule_id', '')}")
        lines.append(f"  evidence_ref: {issue.get('evidence_ref', '')}")
        lines.append(f"  explanation: {issue.get('explanation', '')}")
    lines += ["", SPEC]
    return "\n".join(lines)


def parse_scores(payload: dict) -> list[dict]:
    """教师payload→有效评分列表(无效条目丢弃)."""
    raw = payload.get("scores")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("idx"))
            faithful = int(item.get("faithful"))
            truthful = int(item.get("truthful"))
            useful = int(item.get("useful"))
        except (TypeError, ValueError):
            continue
        if not (1 <= faithful <= 3 and 1 <= truthful <= 3 and 1 <= useful <= 3):
            continue
        out.append({"idx": idx, "faithful": faithful, "truthful": truthful,
                    "useful": useful,
                    "reason": str(item.get("reason", ""))[:200]})
    return out


def call_teacher(prompt: str, teacher_fn: TeacherFn,
                 stats: Counter) -> list[dict] | None:
    """教师调用(网络错误退避重试+解析失败一次重试).

    网络错误(URLError/TimeoutError/RuntimeError)按(0,8,20,45)秒退避重试,
    耗尽换严格后缀再试一轮; 仍耗尽抛TeacherUnavailable——条目保持pending
    不落盘, 续跑可补. 返回评分列表或None(两次解析失败).
    """
    last_error: Exception | None = None
    for attempt, suffix in enumerate(("", RETRY_SUFFIX)):
        last_error = None
        parsed_ok = False
        for delay in _NET_RETRY_DELAYS:
            if delay:
                time.sleep(delay)
            try:
                payload, _model, cache_hit = teacher_fn(
                    prompt + suffix, SYSTEM,
                    max_tokens=MAX_TOKENS, temperature=TEMPERATURE,
                    extra_payload=dict(EXTRA_PAYLOAD), cache=True)
            except (RuntimeError, OSError) as exc:
                last_error = exc
                stats["network_errors"] += 1
                print(f"  network error #{stats['network_errors']}: "
                      f"{type(exc).__name__}: {str(exc)[:120]}", flush=True)
                continue
            if cache_hit:
                stats["cache_hits"] += 1
            else:
                stats["llm_requests"] += 1
            if attempt > 0:
                stats["retry_calls"] += 1
            scores = parse_scores(payload)
            if scores:
                return scores
            parsed_ok = True            # 调用成功但解析失败
            break
        if last_error is not None:
            if attempt == 0:
                continue                # 换严格后缀(网络也再给一轮)
            raise TeacherUnavailable(f"{type(last_error).__name__}: "
                                     f"{str(last_error)[:200]}")
        if parsed_ok and attempt == 0:
            continue                    # 解析失败→严格后缀重试
    return None


def gate_entry(entry: dict, teacher_fn: TeacherFn,
               stats: Counter) -> dict:
    """单条目闸门: 机械检查先行, 通过者送教师评分."""
    answer = str(entry.get("answer", ""))
    n_evidence = len(entry.get("evidence") or [])
    issues = [dict(i) for i in entry["issues"]]
    pass_idx: list[int] = []
    for j, issue in enumerate(issues):
        ok, reason = mechanical_check(answer, issue, n_evidence)
        if ok:
            pass_idx.append(j)
        else:
            issues[j]["quality"] = {
                "faithful": 1, "truthful": None, "useful": None,
                "gate_reason": reason, "scored_by": "mechanical"}
            stats["mechanical_fail_issues"] += 1
    stats["issues_total"] += len(issues)
    if pass_idx:
        stats["issues_sent_to_teacher"] += len(pass_idx)
        stats["entries_sent_to_teacher"] += 1
        prompt = build_gate_prompt(entry, pass_idx)
        scores = call_teacher(prompt, teacher_fn, stats)
        by_idx = {item["idx"]: item for item in scores} if scores else {}
        if not by_idx:
            stats["teacher_parse_fail_entries"] += 1
        for k, j in enumerate(pass_idx):
            item = by_idx.get(k)
            if item is None:
                issues[j]["quality"] = {
                    "faithful": None, "truthful": None, "useful": None,
                    "gate_reason": "teacher_no_valid_score",
                    "scored_by": "teacher_parse_fail"}
            else:
                issues[j]["quality"] = {
                    "faithful": item["faithful"],
                    "truthful": item["truthful"],
                    "useful": item["useful"],
                    "gate_reason": item["reason"],
                    "scored_by": "teacher"}
    else:
        stats["entries_all_mechanical_fail"] += 1
    out = dict(entry)
    out["issues"] = issues
    return out


def row_weight(verdict: str, issues: list[dict]) -> tuple[float, bool]:
    """verdict采样权重表: refute行任一issue faithful<2或truthful<2→降权."""
    base = VERDICT_BASE_WEIGHTS.get(str(verdict), 1.0)
    if str(verdict) != "refute":
        return base, False
    for issue in issues:
        quality = issue.get("quality") or {}
        faithful, truthful = quality.get("faithful"), quality.get("truthful")
        if (faithful is not None and faithful < 2) or \
                (truthful is not None and truthful < 2):
            return LOW_QUALITY_WEIGHT, True
    return base, False


def build_gated_rows(v3f_rows: list[dict],
                     scored_union: dict[str, dict]) -> list[dict]:
    """v3f原行序+原字段, 追加issue级quality与行级采样权重."""
    out: list[dict] = []
    for row in v3f_rows:
        new = dict(row)
        scored = scored_union.get(str(row["instance_id"]))
        if scored is not None and row.get("issues"):
            new["issues"] = scored["issues"]
            weight, low = row_weight(str(scored.get("verdict", "")),
                                     scored["issues"])
        else:
            weight = VERDICT_BASE_WEIGHTS.get(str(row.get("verdict", "")), 1.0)
            low = False
        new["sample_weight"] = round(weight, 2)
        new["downweight"] = bool(low)
        out.append(new)
    return out


def _score_distribution(issues: list[dict]) -> dict[str, dict[str, int]]:
    dist: dict[str, Counter] = {"faithful": Counter(), "truthful": Counter(),
                                "useful": Counter()}
    for issue in issues:
        quality = issue.get("quality") or {}
        for dim in ("faithful", "truthful", "useful"):
            value = quality.get(dim)
            key = str(value) if value is not None else "null"
            dist[dim][key] += 1
    return {dim: dict(sorted(counter.items())) for dim, counter in dist.items()}


def _data_quality_findings(scored_union: dict[str, dict]) -> list[dict]:
    """数据质量问题例证(quote不在answer/解析失败等, 每类给instance_id)."""
    findings: dict[str, list[str]] = {}
    for sid, row in scored_union.items():
        for issue in row.get("issues", []):
            quality = issue.get("quality") or {}
            reason = str(quality.get("gate_reason", ""))
            if reason.startswith("mechanical_fail") or \
                    reason == "teacher_no_valid_score":
                findings.setdefault(reason, []).append(sid)
    return [{"problem": reason, "n_issues": len(ids),
             "example_instance_ids": ids[:3]}
            for reason, ids in sorted(findings.items())]


def build_report(scored_union: dict[str, dict], stats: Counter,
                 gated_rows: list[dict], v3f_only: int,
                 teacher_only: int) -> dict:
    union_issues = [i for row in scored_union.values()
                    for i in row.get("issues", [])]
    teacher_issues = [i for i in union_issues
                      if (i.get("quality") or {}).get("scored_by") == "teacher"]
    downweighted = sum(1 for r in gated_rows if r.get("downweight"))
    weight_dist = Counter(r.get("sample_weight") for r in gated_rows)
    requests = stats["llm_requests"]
    hits = stats["cache_hits"]
    return {
        "task": "e5_step1_explanation_gate",
        "inputs": {
            "v3f": str(V3F.relative_to(BASE)),
            "teacher_labels": str(TEACHER_LABELS.relative_to(BASE)),
        },
        "union": {
            "entries_with_issues": len(scored_union),
            "from_v3f": v3f_only,
            "from_teacher_labels_only": teacher_only,
            "issues_total": len(union_issues),
            "issues_teacher_scored": len(teacher_issues),
        },
        "mechanical_gate": {
            "fail_issues": stats["mechanical_fail_issues"],
            "entries_all_mechanical_fail": stats["entries_all_mechanical_fail"],
        },
        "teacher": {
            "model": "glm-5.3",
            "interface": "tools/llm_teacher.llm_json_teacher(cache=True)",
            "extra_payload": EXTRA_PAYLOAD,
            "entries_sent_to_teacher": stats["entries_sent_to_teacher"],
            "llm_requests": requests,
            "cache_hits": hits,
            "cache_hit_rate": round(hits / (hits + requests), 3)
            if (hits + requests) else 0.0,
            "retry_calls": stats["retry_calls"],
            "parse_fail_entries": stats["teacher_parse_fail_entries"],
            "network_errors": stats["network_errors"],
            "entries_network_failed_pending": stats[
                "entries_network_failed"],
        },
        "score_distribution_all_union_issues": _score_distribution(union_issues),
        "score_distribution_teacher_scored": _score_distribution(teacher_issues),
        "gated_file": {
            "path": str(OUT_GATED.relative_to(BASE)),
            "rows": len(gated_rows),
            "rows_with_issue_quality": sum(1 for r in gated_rows if r.get("issues")),
            "refute_rows": sum(1 for r in gated_rows if r.get("verdict") == "refute"),
            "downweighted_rows": downweighted,
            "sample_weight_distribution": {str(k): v
                                           for k, v in weight_dist.items()},
            "low_quality_weight": LOW_QUALITY_WEIGHT,
            "verdict_base_weights": VERDICT_BASE_WEIGHTS,
        },
        "data_quality_findings": _data_quality_findings(scored_union),
    }


def _dry_run(entries: list[dict]) -> None:
    """--dry-run: 只跑机械检查并打印统计, 不发API不落盘."""
    stats: Counter = Counter()
    for entry in entries:
        answer = str(entry.get("answer", ""))
        n_ev = len(entry.get("evidence") or [])
        stats["entries"] += 1
        stats["issues"] += len(entry["issues"])
        ok_any = False
        for issue in entry["issues"]:
            ok, reason = mechanical_check(answer, issue, n_ev)
            if ok:
                ok_any = True
            else:
                stats["fail_issues"] += 1
                stats[reason] += 1
        if not ok_any:
            stats["entries_all_fail"] += 1
    print(f"[dry-run] {dict(stats)}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0,
                        help="只处理前N条(调试用, 0=全部)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只做机械检查统计, 不发教师调用不落盘")
    parser.add_argument("--resume-run", type=Path, default=None,
                        help="续跑既有run目录(runs/e5_explanation_gate_*)")
    args = parser.parse_args()

    entries = load_union()
    if args.dry_run:
        if args.limit:
            entries = entries[:args.limit]
        _dry_run(entries)
        return

    config = {
        "task": "e5_step1_explanation_gate",
        "inputs": {"v3f": str(V3F.name), "teacher": str(TEACHER_LABELS.name)},
        "model": "glm-5.3",
        "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
        "extra_payload": EXTRA_PAYLOAD,
        "verdict_base_weights": VERDICT_BASE_WEIGHTS,
        "low_quality_weight": LOW_QUALITY_WEIGHT,
        "limit": args.limit,
    }
    if args.resume_run is not None:
        run_dir = args.resume_run.resolve()
        if not run_dir.is_dir():
            raise SystemExit(f"resume目录不存在: {run_dir}")
        meta_path = run_dir / "config.json"
        meta = (json.loads(meta_path.read_text(encoding="utf-8"))
                if meta_path.exists() else
                {"script": "e5_explanation_gate", "config": config,
                 "git_sha": "resumed", "config_hash": "resumed",
                 "opened_at": round(time.time(), 1)})
        run: RunHandle = RunHandle(run_dir, meta)
    else:
        run = open_run("e5_explanation_gate", config)

    union_path = run.path / UNION_ARTIFACT
    done_ids: set[str] = set()
    if union_path.exists():
        for row in read_jsonl(union_path):
            done_ids.add(str(row["instance_id"]))

    v3f_ids = {str(r["instance_id"]) for r in read_jsonl(V3F)}
    union_ids = {str(e["instance_id"]) for e in entries}
    stats: Counter = Counter()
    n_new = 0
    started = time.time()
    with open(union_path, "a", encoding="utf-8") as fout:
        for entry in entries:
            sid = str(entry["instance_id"])
            if sid in done_ids:
                continue
            if args.limit and n_new >= args.limit:
                break
            try:
                scored = gate_entry(entry, llm_json_teacher, stats)
            except TeacherUnavailable as exc:
                stats["entries_network_failed"] += 1
                print(f"  SKIP {sid}: {exc}", flush=True)
                continue
            fout.write(json.dumps(scored, ensure_ascii=False) + "\n")
            fout.flush()
            done_ids.add(sid)
            n_new += 1
            if n_new % 25 == 0:
                print(f"[{n_new}] {sid} ({time.time() - started:.0f}s, "
                      f"req={stats['llm_requests']} "
                      f"hit={stats['cache_hits']})", flush=True)

    # 汇总: 全量union评分(含续跑前已完成)
    scored_union: dict[str, dict] = {}
    for row in read_jsonl(union_path):
        scored_union[str(row["instance_id"])] = row
    v3f_rows = read_jsonl(V3F)
    gated_rows = build_gated_rows(v3f_rows, scored_union)
    with open(OUT_GATED, "w", encoding="utf-8") as f:
        for row in gated_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = build_report(scored_union, stats, gated_rows,
                          v3f_only=len(union_ids & v3f_ids),
                          teacher_only=len(union_ids - v3f_ids))
    run.save_result(report)
    pending = len(entries) - len(scored_union)
    print(f"新增评分{n_new}条 → {union_path}")
    if pending:
        print(f"⚠ 仍有{pending}条pending(网络失败未落盘)——"
              f"重跑可续: python tools/e5_explanation_gate.py "
              f"--resume-run {run.path}")
    print(f"gated训练文件: {OUT_GATED} ({len(gated_rows)}行)")
    print(f"run目录: {run.path}")
    print(json.dumps({k: report[k] for k in
                      ("union", "mechanical_gate", "teacher",
                       "score_distribution_teacher_scored", "gated_file")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
