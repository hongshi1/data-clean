r"""S7效率支撑: 定位gold标注的LLM预标注工具(pre-annotation).

背景: S7需人工标注108条定位gold(91 QA + 17违例, 协议见
docs/srs_project/48_localization_gold_protocol.md). 人工验证LLM建议比从零
标注快3-5倍——本工具生成suggest_前缀的预标注建议, gold字段保持空.

对91条QA条目(annotation_template_v1.jsonl):
  1. 运行QAConsistencyModule(use_experts=True, use_llm_residual=True)
     (复用build_localization_gold_template的冻结QA加载模式);
  2. claim级建议: verdict/evidence_refs/rationale, 全部来自系统输出;
  3. span细化: 对判定性claim(带引用的support/refute), 用llm_json问
     "该证据块中支撑/反驳此claim的最小文本片段"(每claim一次调用,
     输出{"span": ...}), 供人工核对(比块级更精确的定位建议);
  4. 写新文件pre_annotated_v1.jsonl(绝不覆盖模板).

LLM调用预算: span细化默认上限350次(全部cache=True, 重跑零成本); 超预算
时优先silver=refute/support的实例, NIE实例只填系统建议不做span细化.

17违例条目不是标准QA, 系统无法直接跑 → 保持模板原样(记skipped).

同工具自检: 系统verdict×silver混淆 / span子串校验(span是否真的在其
引用的证据块文本中) / 统计JSON按runs协议落盘(tools/run_utils.py).

用法:
  python tools/preannotate_localization_gold.py
  python tools/preannotate_localization_gold.py --span-budget 200

设计约束: 模块顶层零I/O; LLM只走llm_json(cache=True); open()一律
encoding="utf-8"; 无类型抑制; 无裸except; 输出不覆盖annotation_template.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_models import QAInput  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402
from tools.build_localization_gold_template import (  # noqa: E402
    FROZEN_QA,
    VERDICTS,
    parse_gold_row,
    read_jsonl,
    sha256_file,
    system_row_from_result,
    write_jsonl,
)

TOOL_VERSION = "s7_preannotate_localization_gold_v1"
TEMPLATE_PATH = (BASE / "data/gjb_438c/localization_gold"
                 / "annotation_template_v1.jsonl")
PREANNOTATED_OUT = (BASE / "data/gjb_438c/localization_gold"
                    / "pre_annotated_v1.jsonl")
DEFAULT_SPAN_BUDGET = 350
DECISIVE_VERDICTS = ("support", "refute")
QA_TASK_TYPE = "qa_verdict"

_STATEMENT_REF = re.compile(r"#s\d+$")


# ---------------------------------------------------------------- 纯函数内核
def block_ref(ref: str) -> str:
    """语句级引用(ev-...#s5)归一到父证据块(与评分协议§7的块级粒度一致)."""
    return _STATEMENT_REF.sub("", ref)


def span_prompt(claim_text: str, verdict: str,
                blocks: Sequence[tuple[str, str]]) -> str:
    """span细化prompt(纯函数): 声明+系统判定+引用证据块原文."""
    lines = [
        f"【声明】{claim_text}",
        f"【系统判定】{verdict}",
        "",
        "【证据块原文】",
    ]
    lines += [f"{evidence_id}: {text}" for evidence_id, text in blocks]
    lines += [
        "",
        "【任务】在证据块原文中找出支撑或反驳该声明的最小连续文本片段，"
        "必须从原文逐字复制（不改写、不翻译、不总结；表格块可取某一单元格"
        "或某一行内的连续文字）。若判定依据是两处相互冲突的证据，"
        "用；连接两处摘录。证据中找不到时span为空字符串。",
        "",
        '输出JSON：{"span": "..."}',
    ]
    return "\n".join(lines)


def parse_span_payload(payload: Any) -> str:
    """{"span": ...}→span字符串; 非法/缺失→""(空建议, 不静默转str)."""
    if not isinstance(payload, dict):
        return ""
    span = payload.get("span")
    return span.strip() if isinstance(span, str) else ""


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def span_in_block(span: str, block_text: str) -> bool:
    """严格子串校验: 整段span(空白归一)出现在单个证据块文本中."""
    needle = _compact(span)
    return bool(needle) and needle in _compact(block_text)


def span_in_evidence(span: str, block_texts: Sequence[str]) -> bool:
    """span有效性: 整段命中任一引用块, 或按；切分的各段分别命中某块
    (refute冲突对摘录形态, 协议§4.4); 空span/空块列表一律False."""
    if not block_texts:
        return False
    if any(span_in_block(span, text) for text in block_texts):
        return True
    parts = [part for part in (
        piece.strip() for piece in re.split(r"[；;]", span)) if part]
    if len(parts) < 2:
        return False
    return all(
        any(span_in_block(part, text) for text in block_texts)
        for part in parts)


def verdict_confusion(silver_verdicts: Sequence[str],
                      system_verdicts: Sequence[str]) -> dict[str, Any]:
    """silver×system的3类混淆(行=silver, 列=system)+原始一致率."""
    if len(silver_verdicts) != len(system_verdicts):
        raise ValueError(
            f"混淆矩阵要求等长verdict序列, got {len(silver_verdicts)}"
            f" vs {len(system_verdicts)}")
    matrix = {silver: {system: 0 for system in VERDICTS}
              for silver in VERDICTS}
    for silver, system in zip(silver_verdicts, system_verdicts):
        if silver not in VERDICTS or system not in VERDICTS:
            raise ValueError(f"非法verdict: {silver!r}/{system!r}")
        matrix[silver][system] += 1
    n = len(silver_verdicts)
    agreement = sum(matrix[verdict][verdict] for verdict in VERDICTS)
    return {
        "n": n,
        "confusion_silver_x_system": matrix,
        "agreement_rate": round(agreement / n, 4) if n else 0.0,
    }


@dataclass
class SpanBudget:
    """span细化LLM调用预算计数器(超预算时按优先级跳过)."""

    limit: int
    calls: int = 0
    skipped: int = 0

    def take(self) -> bool:
        """占用一次调用额度; False=预算耗尽(调用方跳过span细化)."""
        if self.calls >= self.limit:
            return False
        self.calls += 1
        return True


_SPAN_SYSTEM = (
    "你是GJB军事软件需求文档的证据定位助手。任务是在证据块原文中定位"
    "支撑或反驳某声明的最小文本片段，必须逐字复制原文。只输出JSON。"
)


def _call_span_llm(prompt: str) -> dict[str, Any]:
    """一次缓存llm_json调用(硬规则: cache=True); 惰性import(ai_config读.env).

    与L3残差通道(llm_residual._call_llm)同一模型与JSON契约, 含其验证过的
    reasoning_effort=low省token配置; 失败由调用方记录并降级为空span.
    """
    from algorithms.common.llm_client import llm_json

    payload, _model = llm_json(
        prompt, system=_SPAN_SYSTEM, prefer="glm", cache=True,
        allow_fallback=False, model_override="glm-5.3",
        max_tokens=4000, timeout=300,
        extra_payload={
            "response_contract": "json_final_content_v2",
            "reasoning_effort": "low",
        })
    return payload if isinstance(payload, dict) else {}


# ---------------------------------------------------------------- 预标注主流程
def preannotate(
    template_path: Path = TEMPLATE_PATH,
    frozen_path: Path = FROZEN_QA,
    out_path: Path = PREANNOTATED_OUT,
    span_budget: int = DEFAULT_SPAN_BUDGET,
    use_experts: bool = True,
    use_llm_residual: bool = True,
) -> dict[str, Any]:
    """生成pre_annotated JSONL(不覆盖模板)并返回自检统计.

    QA条目: 运行QAConsistencyModule→claim级suggest字段(全部来自系统输出)
    +判定性claim的LLM span建议; 违例条目原样保留(记skipped);
    gold字段保持空(人工仍需逐条填).
    """
    from algorithms.consistency.qa_module import QAConsistencyModule

    if out_path.resolve() == template_path.resolve():
        raise ValueError("out_path不得指向template_path(绝不覆盖标注模板)")
    template_rows = read_jsonl(template_path)
    for row in template_rows:
        parse_gold_row(row)  # schema校验: 非法模板立即报错, 不静默产出
    qa_rows = [row for row in template_rows
               if str(row.get("task_type", "")) == QA_TASK_TYPE]
    skipped_rows = [row for row in template_rows
                    if str(row.get("task_type", "")) != QA_TASK_TYPE]

    frozen_rows = read_jsonl(frozen_path)
    requests: dict[str, QAInput] = {}
    for frozen_row in frozen_rows:
        iid = str(frozen_row["instance_id"])
        if iid in requests:
            raise ValueError(f"冻结QA instance_id重复: {iid}")
        requests[iid] = request_from_dict(frozen_row)
    missing = [str(row["instance_id"]) for row in qa_rows
               if str(row["instance_id"]) not in requests]
    if missing:
        raise ValueError(f"冻结QA缺失模板实例(无法运行系统): {missing[:5]}")

    module = QAConsistencyModule(use_experts=use_experts,
                                 use_llm_residual=use_llm_residual)
    silver_by_id = {str(row["instance_id"]): str(row.get("gold_verdict", ""))
                    for row in qa_rows}
    # 预算优先级: silver判定性实例(refute/support)在前, NIE在后
    order = sorted(
        range(len(qa_rows)),
        key=lambda i: (
            0 if silver_by_id[str(qa_rows[i]["instance_id"])]
            in DECISIVE_VERDICTS else 1, i))

    budget = SpanBudget(limit=max(int(span_budget), 0))
    span_failures: list[dict[str, str]] = []
    suggest_by_id: dict[str, dict[str, Any]] = {}
    n_claims_total = 0
    n_decisive_claims = 0
    n_span_candidates = 0
    n_span_returned = 0
    n_span_valid = 0
    n_span_strict = 0
    residual_instances = 0
    residual_failed_instances = 0

    for index in order:
        row = qa_rows[index]
        iid = str(row["instance_id"])
        result = module.verify(requests[iid])
        system_row = system_row_from_result(result)
        evidence_text = {ev.evidence_id: ev.text
                         for ev in requests[iid].evidence}
        methods = {claim.method for claim in result.claim_results}
        if any(method.startswith("llm_residual") for method in methods):
            residual_instances += 1
        if "llm_residual_failed" in methods:
            residual_failed_instances += 1

        suggest_claims: list[dict[str, Any]] = []
        for claim in result.claim_results:
            refs = sorted({block_ref(ref) for ref in claim.evidence_refs if ref})
            blocks = [(ref, evidence_text[ref]) for ref in refs
                      if ref in evidence_text]
            n_claims_total += 1
            decisive = claim.verdict in DECISIVE_VERDICTS
            if decisive:
                n_decisive_claims += 1
            span = ""
            verified = False
            if decisive and blocks:
                n_span_candidates += 1
                if budget.take():
                    try:
                        payload = _call_span_llm(span_prompt(
                            claim.claim_text, claim.verdict, blocks))
                    except Exception as exc:  # 记入stats, 不静默吞
                        span_failures.append({
                            "instance_id": iid,
                            "claim_id": claim.claim_id,
                            "note": f"{type(exc).__name__}: {exc}",
                        })
                        payload = {}
                    span = parse_span_payload(payload)
                    if span:
                        n_span_returned += 1
                        verified = span_in_evidence(
                            span, [text for _, text in blocks])
                        n_span_valid += int(verified)
                        n_span_strict += int(any(
                            span_in_block(span, text) for _, text in blocks))
                else:
                    budget.skipped += 1
            suggest_claims.append({
                "claim_id": claim.claim_id,
                "claim_text": claim.claim_text,
                "method": claim.method,
                "confidence": float(claim.confidence),
                "system_suggest_verdict": claim.verdict,
                "system_suggest_refs": refs,
                "system_suggest_rationale": claim.rationale,
                "llm_suggest_span": span,
                "llm_suggest_span_verified": verified,
            })
        suggest_by_id[iid] = {
            "pre_annotation_status": "pre_annotated",
            "system_suggest_verdict": str(result.verdict),
            "system_suggest_refs": list(system_row["evidence_refs"]),
            "system_suggest_claims": suggest_claims,
        }

    out_rows: list[dict[str, Any]] = []
    for row in template_rows:
        out = dict(row)
        if str(row.get("task_type", "")) == QA_TASK_TYPE:
            out.update(suggest_by_id[str(row["instance_id"])])
        else:
            out["pre_annotation_status"] = "skipped"
        out_rows.append(out)
    write_jsonl(out_path, out_rows)

    silver = [silver_by_id[str(row["instance_id"])] for row in qa_rows]
    system = [suggest_by_id[str(row["instance_id"])]["system_suggest_verdict"]
              for row in qa_rows]
    n_gold_prefilled = sum(
        1 for row in qa_rows
        if any(claim.get("gold_evidence_refs") for claim in row["claims"]))
    return {
        "tool_version": TOOL_VERSION,
        "module": {
            "name": "QAConsistencyModule",
            "use_experts": use_experts,
            "use_llm_residual": use_llm_residual,
        },
        "paths": {
            "template": str(template_path),
            "frozen": str(frozen_path),
            "out": str(out_path),
        },
        "inputs": {
            "template_sha256": sha256_file(template_path),
            "frozen_sha256": sha256_file(frozen_path),
        },
        "counts": {
            "template_rows": len(template_rows),
            "qa_pre_annotated": len(qa_rows),
            "violations_skipped": len(skipped_rows),
            "qa_rows_with_gold_refs_prefilled": n_gold_prefilled,
            "system_claims": n_claims_total,
            "decisive_claims": n_decisive_claims,
        },
        "llm_calls": {
            "span_calls": budget.calls,
            "span_budget": budget.limit,
            "span_budget_skipped_claims": budget.skipped,
            "llm_residual_instances_estimate": residual_instances,
            "llm_residual_failed_instances": residual_failed_instances,
        },
        "system_vs_silver": verdict_confusion(silver, system),
        "span_quality": {
            "n_span_candidates": n_span_candidates,
            "n_span_returned": n_span_returned,
            "n_span_valid": n_span_valid,
            "span_valid_rate": (round(n_span_valid / n_span_returned, 4)
                                if n_span_returned else None),
            "n_span_strict_block_substring": n_span_strict,
            "span_strict_block_rate": (round(n_span_strict / n_span_returned, 4)
                                       if n_span_returned else None),
        },
        "span_call_failures": span_failures,
        "notes": [
            "gold字段保持空: suggest_前缀字段只是建议, 人工须逐条填gold(协议§3)",
            "span细化只做判定性claim(support/refute且带引用); NIE claim的refs是诊断信息(协议§7)",
            "LLM全部走llm_json(cache=True): 残差通道按实例批量(每实例≤1次), span每claim一次",
            "超span预算时优先silver=refute/support实例, NIE实例只填系统建议",
            "17违例条目非标准QA, 预标注跳过, 保持模板原样(协议§10.3)",
        ],
    }


# ---------------------------------------------------------------- CLI
def _reconfigure_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout.reconfigure(encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="S7定位gold的LLM预标注工具(suggest_前缀建议, gold保持空)")
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH,
                        help="标注模板JSONL(只读, 绝不覆盖)")
    parser.add_argument("--frozen", type=Path, default=FROZEN_QA,
                        help="冻结QA JSONL(系统输入)")
    parser.add_argument("--out", type=Path, default=PREANNOTATED_OUT,
                        help="预标注输出JSONL(新文件)")
    parser.add_argument("--span-budget", type=int, default=DEFAULT_SPAN_BUDGET,
                        help=f"span细化LLM调用上限(默认{DEFAULT_SPAN_BUDGET})")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    _reconfigure_stdout()
    args = build_arg_parser().parse_args(argv)
    stats = preannotate(template_path=args.template, frozen_path=args.frozen,
                        out_path=args.out, span_budget=args.span_budget)
    from tools.run_utils import open_run

    run = open_run("preannotate_localization_gold", {
        "template": str(args.template), "frozen": str(args.frozen),
        "out": str(args.out), "span_budget": args.span_budget,
        "tool_version": TOOL_VERSION})
    run.save_result(stats)
    compact = {key: value for key, value in stats.items()
               if key != "span_call_failures"}
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    print(f"result.json: {run.path / 'result.json'}")


if __name__ == "__main__":
    main()
