#!/usr/bin/env python3
r"""49号协议: span-grounded extraction的标注评估器.

viewer(左侧原文/右侧提取对照界面)为每个高亮span提供✓/✗按钮, 标注存
localStorage并导出JSON:

    [{"span_text": ..., "span_type": ..., "block_index": ...,
      "verdict": "correct" | "incorrect", "ts": ...}]

本脚本把一份或多份导出合并成span precision报告(49号协议§2):

    1. 记录级校验: 未知verdict/未知span_type/缺失字段逐项计数, 不静默丢弃;
    2. 去重: 同(span_text, span_type, block_index)的重复标注以ts最新为准,
       精确重复与verdict冲突分别计数;
    3. 按 span_type 分层统计 n_correct/n_incorrect/precision/Wilson 95% CI
       (自实现, 无scipy依赖), 另给六类pooled总体;
    4. 每类型 n < MIN_SAMPLE(50) 标 "insufficient" (49号协议样本量门槛);
    5. 输出: runs协议result.json + 终端markdown表 (+ --output 报告文件).

指标边界(诚实声明): span precision只测"已高亮span的正确率"(抽取层),
不含recall(未高亮文本不在分母), 也不裁决关系层对齐质量(48号gold-proxy
与A-E矩阵独立裁决, 两层不得互相替代).

用法:
    python tools/eval_span_grounding.py --annotations spans1.json spans2.json
    python tools/eval_span_grounding.py --annotations spans.json --output report.md
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE / "tools"))
from run_utils import open_run  # noqa: E402

SPAN_TYPES = (
    "identifier",
    "quantity_unit",
    "predicate",
    "modal",
    "negative",
    "reference",
)
VALID_VERDICTS = ("correct", "incorrect")
MIN_SAMPLE = 50
TARGET_PRECISION = 0.90
Z95 = 1.959963984540054
SIGNATURE_FIELDS = ("span_text", "span_type", "block_index", "verdict", "ts")


# --------------------------------------------------------------------------
# 纯统计与记录逻辑(单测覆盖; 模块顶层零I/O).
# --------------------------------------------------------------------------


def wilson_interval(k: int, n: int, z: float = Z95) -> tuple[float, float] | None:
    """Wilson score interval(双侧) for k successes in n bernoulli trials.

    自实现无scipy; p接近0/1时比正态近似诚实. n==0时区间无定义, 返回None
    (而不是骗人的(0,0)). k/n越界抛ValueError(防御性, 静默吞错会污染统计).
    """

    if n < 0 or k < 0 or k > n:
        raise ValueError(f"wilson_interval requires 0 <= k <= n, got k={k}, n={n}")
    if n == 0:
        return None
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    spread = (z / denom) * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    # p=1时上界数学上恰为1, p=0时下界恰为0; 显式钉住, 避免浮点误差(1-1e-16).
    lower = 0.0 if p == 0.0 else max(0.0, center - spread)
    upper = 1.0 if p == 1.0 else min(1.0, center + spread)
    return lower, upper


def normalize_verdict(raw: Any) -> str:
    """correct/incorrect(大小写与空白宽容); 其余返回空串(非法)."""

    text = str(raw if raw is not None else "").strip().lower()
    return text if text in VALID_VERDICTS else ""


def normalize_span_type(raw: Any) -> str:
    """span_type归一(小写去空白); 不限定取值——未知类型由上层计数."""

    return str(raw if raw is not None else "").strip().lower()


def record_status(record: Any) -> str:
    """单条导出记录的校验状态, 优先级: malformed > missing_field >
    invalid_verdict > unknown_type; 只有ok进入指标计算."""

    if not isinstance(record, dict):
        return "malformed"
    if (
        not str(record.get("span_text") or "").strip()
        or not str(record.get("span_type") or "").strip()
        or record.get("verdict") is None
    ):
        return "missing_field"
    if normalize_verdict(record.get("verdict")) == "":
        return "invalid_verdict"
    if normalize_span_type(record.get("span_type")) not in SPAN_TYPES:
        return "unknown_type"
    return "ok"


def _record_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    """全字段签名: 判定精确重复事件(与去重键区分)."""

    return tuple(record.get(field) for field in SIGNATURE_FIELDS)


def span_key(record: dict[str, Any]) -> tuple[str, str, str]:
    """去重键: (span_text, 归一span_type, 归一block_index)."""

    block_index = record.get("block_index")
    return (
        str(record.get("span_text") or ""),
        normalize_span_type(record.get("span_type")),
        str(block_index if block_index is not None else ""),
    )


def _ts_sort_key(record: dict[str, Any]) -> tuple[int, float | str]:
    """ts排序键: 数值/字符串时间戳分别可比, 缺失视为最早."""

    raw = record.get("ts")
    if raw is None or isinstance(raw, bool):
        return (0, 0.0)
    if isinstance(raw, (int, float)):
        return (1, float(raw))
    return (2, str(raw))


def dedup_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    """合并重复标注: 同键以ts最新为准(平ts时后出现者胜).

    返回kept列表(保持首次出现顺序)+数据卫生计数:
    n_duplicate_events = 与其他记录全字段相同的纯重复事件;
    n_reannotated_keys  = 至少出现两种不同签名的键(真重标);
    n_conflicting_keys  = 键内verdict发生翻转的键.
    """

    grouped: dict[tuple[str, str, str], list[tuple[int, dict[str, Any]]]] = {}
    for index, record in enumerate(records):
        grouped.setdefault(span_key(record), []).append((index, record))
    kept: list[dict[str, Any]] = []
    n_duplicate_events = 0
    n_reannotated_keys = 0
    n_conflicting_keys = 0
    for entries in grouped.values():
        signatures = {_record_signature(record) for _, record in entries}
        n_duplicate_events += len(entries) - len(signatures)
        if len(signatures) > 1:
            n_reannotated_keys += 1
        verdicts = {normalize_verdict(record.get("verdict")) for _, record in entries}
        if len(verdicts) > 1:
            n_conflicting_keys += 1
        latest = max(entries, key=lambda pair: (_ts_sort_key(pair[1]), pair[0]))
        kept.append(latest[1])
    return {
        "kept": kept,
        "n_keys": len(grouped),
        "n_duplicate_events": n_duplicate_events,
        "n_reannotated_keys": n_reannotated_keys,
        "n_conflicting_keys": n_conflicting_keys,
        "n_dropped": len(records) - len(kept),
    }


def type_metrics(
    records: list[dict[str, Any]],
    min_sample: int = MIN_SAMPLE,
    target: float = TARGET_PRECISION,
) -> dict[str, Any]:
    """一个span_type(或pooled总体)的precision + Wilson 95% CI + 门槛判定."""

    n = len(records)
    n_correct = sum(
        1 for record in records if normalize_verdict(record.get("verdict")) == "correct"
    )
    n_incorrect = n - n_correct
    precision = (n_correct / n) if n else None
    interval = wilson_interval(n_correct, n)
    return {
        "n": n,
        "n_correct": n_correct,
        "n_incorrect": n_incorrect,
        "precision": round(precision, 4) if precision is not None else None,
        "ci95": [round(interval[0], 4), round(interval[1], 4)] if interval else None,
        "sufficiency": "ok" if n >= min_sample else "insufficient",
        "target_met": (precision >= target) if precision is not None else None,
        "ci_lower_meets_target": (interval[0] >= target) if interval is not None else None,
    }


def build_conclusion(
    overall: dict[str, Any],
    by_type: dict[str, Any],
    min_sample: int,
    target: float,
) -> str:
    """一段式结论: 总体精度+达标口径+样本不足清单(result.json与报告共用)."""

    if overall["n"] == 0:
        return (
            "无有效标注(span_type在协议六类内且verdict合法的记录数为0): "
            "precision未定义, 全部类型为insufficient。"
        )
    ci = overall["ci95"]
    ci_text = f", Wilson 95% CI [{ci[0]:.4f}, {ci[1]:.4f}]" if ci else ""
    verdict = "达标" if overall["target_met"] else "未达标"
    if overall["target_met"] and overall["ci_lower_meets_target"]:
        verdict += "(CI下界亦达标, 强达标)"
    elif overall["target_met"]:
        verdict += "(仅点估计达标, CI下界未达标, 弱达标)"
    insufficient = [t for t, m in by_type.items() if m["sufficiency"] == "insufficient"]
    ins_text = (
        f"样本不足(<{min_sample})的类型: {', '.join(insufficient)}。"
        if insufficient
        else f"全部类型样本量>={min_sample}。"
    )
    return (
        f"总体span precision = {overall['n_correct']}/{overall['n']} = "
        f"{overall['precision']:.4f}{ci_text}, 目标>={target}: {verdict}。{ins_text}"
    )


def evaluate(
    records: list[Any],
    min_sample: int = MIN_SAMPLE,
    target: float = TARGET_PRECISION,
) -> dict[str, Any]:
    """主评估(纯函数): 记录校验 -> 去重 -> 分层统计 -> 汇总结果."""

    status_counts = Counter(record_status(record) for record in records)
    valid_records = [
        record
        for record in records
        if isinstance(record, dict) and record_status(record) == "ok"
    ]
    dedup = dedup_records(valid_records)
    kept = dedup["kept"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in kept:
        grouped.setdefault(normalize_span_type(record.get("span_type")), []).append(record)
    by_type: dict[str, Any] = {
        span_type: type_metrics(grouped.get(span_type, []), min_sample, target)
        for span_type in SPAN_TYPES
    }
    overall = type_metrics(kept, min_sample, target)
    unknown_counts = Counter(
        normalize_span_type(record.get("span_type"))
        for record in records
        if isinstance(record, dict) and record_status(record) == "unknown_type"
    )
    return {
        "protocol": "49 span-grounded extraction: viewer ✓/✗ annotation evaluation",
        "span_types": list(SPAN_TYPES),
        "min_sample": min_sample,
        "target_precision": target,
        "n_records": len(records),
        "record_status_counts": dict(sorted(status_counts.items())),
        "unknown_type_counts": dict(sorted(unknown_counts.items())),
        "dedup": {key: value for key, value in dedup.items() if key != "kept"},
        "n_evaluated": len(kept),
        "overall": overall,
        "by_type": by_type,
        "insufficient_types": [
            t for t, m in by_type.items() if m["sufficiency"] == "insufficient"
        ],
        "notes": [
            "指标边界: span precision只测已高亮span的正确率(抽取层), 不含recall"
            "(未高亮文本不在分母), 不裁决关系层对齐(48号gold-proxy独立, 两层互推禁止)。",
            f"统计: Wilson score interval(z={Z95}, 95%双侧)自实现无scipy; "
            f"每类型样本量门槛>={min_sample}条标注。",
            "合并规则: 同(span_text, span_type, block_index)以ts最新为准; "
            "精确重复与verdict冲突单独计数, 不静默丢弃任何记录。",
            "样本量不足(insufficient)类型的precision仅作过程监控, 不进入论文结论。",
        ],
        "conclusion": build_conclusion(overall, by_type, min_sample, target),
    }


def render_markdown(result: dict[str, Any]) -> str:
    """终端与报告文件共用的markdown渲染(纯函数)."""

    lines: list[str] = []
    lines.append("# Span Grounding 标注评估(49号协议)")
    lines.append("")
    status_text = ", ".join(
        f"{key}={value}" for key, value in result["record_status_counts"].items()
    )
    lines.append(f"- 标注记录: {result['n_records']}条(状态: {status_text or '无记录'})")
    if result["unknown_type_counts"]:
        unknown_text = ", ".join(
            f"{key}={value}" for key, value in result["unknown_type_counts"].items()
        )
        lines.append(f"- 未知span_type(已排除, 未静默丢弃): {unknown_text}")
    dedup = result["dedup"]
    lines.append(
        f"- 去重后评估span: {result['n_evaluated']}个"
        f"(精确重复事件{dedup['n_duplicate_events']}, "
        f"重标键{dedup['n_reannotated_keys']}, "
        f"verdict冲突键{dedup['n_conflicting_keys']})"
    )
    lines.append("")
    lines.append("## 总体(六类pooled)")
    lines.append("")
    overall = result["overall"]
    if overall["n"] == 0:
        lines.append("precision = —(无有效标注)")
    else:
        ci = overall["ci95"]
        ci_text = f", Wilson 95% CI [{ci[0]:.4f}, {ci[1]:.4f}]" if ci else ""
        verdict = "达标" if overall["target_met"] else "未达标"
        lines.append(
            f"precision = {overall['precision']:.4f} "
            f"({overall['n_correct']}/{overall['n']}){ci_text}, "
            f"目标 >= {result['target_precision']}: {verdict}"
        )
    lines.append("")
    lines.append("## 分span_type")
    lines.append("")
    lines.append(
        "| span_type | n | correct | incorrect | precision | Wilson 95% CI | 样本量 | 目标 |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---|---|")
    for span_type, metrics in result["by_type"].items():
        ci = metrics["ci95"]
        ci_text = f"[{ci[0]:.4f}, {ci[1]:.4f}]" if ci else "—"
        precision_text = "—" if metrics["precision"] is None else f"{metrics['precision']:.4f}"
        if metrics["target_met"] is None:
            target_text = "—"
        else:
            target_text = "达标" if metrics["target_met"] else "未达标"
        lines.append(
            f"| {span_type} | {metrics['n']} | {metrics['n_correct']} | "
            f"{metrics['n_incorrect']} | {precision_text} | {ci_text} | "
            f"{metrics['sufficiency']} | {target_text} |"
        )
    lines.append("")
    lines.append("## 注")
    lines.append("")
    for note in result["notes"]:
        lines.append(f"- {note}")
    lines.append("")
    lines.append(result["conclusion"])
    return "\n".join(lines)


# --------------------------------------------------------------------------
# I/O与CLI(只在main()内调用; import期零I/O).
# --------------------------------------------------------------------------


def load_annotation_file(path: Path) -> list[Any]:
    """读一份viewer导出: 顶层JSON数组, 或含annotations数组的对象."""

    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("annotations"), list):
        return payload["annotations"]
    raise ValueError(
        f"{path}: expected a JSON list of annotations or an object with an "
        f"'annotations' list, got {type(payload).__name__}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="49号协议span评估器: 合并viewer✓/✗导出, 分层precision+Wilson CI."
    )
    parser.add_argument(
        "--annotations",
        nargs="+",
        required=True,
        type=Path,
        help="viewer导出的标注JSON路径(可多份, 自动合并)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="markdown报告输出路径(缺省仅打印终端)",
    )
    parser.add_argument(
        "--min-sample",
        type=int,
        default=MIN_SAMPLE,
        help=f"每类型样本量门槛(默认{MIN_SAMPLE})",
    )
    parser.add_argument(
        "--target-precision",
        type=float,
        default=TARGET_PRECISION,
        help=f"precision目标(默认{TARGET_PRECISION})",
    )
    return parser


def main() -> None:
    # 管道/重定向时Python默认用本地GBK编码, 中文+特殊符号会乱码; 钉死UTF-8.
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    records: list[Any] = []
    per_file: dict[str, int] = {}
    for path in args.annotations:
        file_records = load_annotation_file(path)
        per_file[str(path)] = len(file_records)
        records.extend(file_records)
    result = evaluate(
        records, min_sample=args.min_sample, target=args.target_precision
    )
    result["annotation_files"] = per_file
    markdown = render_markdown(result)
    run = open_run(
        "eval_span_grounding",
        {
            "annotations": [str(path) for path in args.annotations],
            "output": str(args.output) if args.output else None,
            "min_sample": args.min_sample,
            "target_precision": args.target_precision,
        },
    )
    run.save_result(result)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    print(markdown)
    print()
    print(f"result.json: {run.path / 'result.json'}")
    if args.output is not None:
        print(f"report: {args.output}")


if __name__ == "__main__":
    main()
