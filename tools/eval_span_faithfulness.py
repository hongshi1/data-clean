r"""E1: span忠实率评测——ALCE口径citation precision/recall上violations-17.

99号统一行动方案Phase 0-E1(设计依据96号§5): 评测系统输出的violations[]
(定位span)是否真的指向支撑判定的文本. ALCE(arXiv 2305.14627)口径:

  - citation precision: 系统refute判定引用的证据块中, 属于人工gold定位的比例
  - citation recall:    人工gold定位块中, 被系统refute判定引用的比例

gold锚点(violation_evalset_v1.jsonl实测, 17条全有, 无缺字段):
  - gold_evidence_refs: 人工block级定位(1-5块/条, ⊆实例证据)——ALCE的"该引集合"
  - target_keywords:    violation_desc关键词(如LJCCSH/LJCPZ)——desc锚点重叠
  - GOLD_ROOT_CAUSE(tools/eval_root_cause.py): violation_category/item_id
    →两层根因gold(构造者视角, 17条全映射)

三个span检查(96号§5三件套的静态件):
  (a) 字面忠实——span在原文中确实存在(两个正交事实分开计量):
        quote∈answer(字面本体) + span区间切片精确(copy精度,
        2610.28393口径的LLM逐字复制弱点);
        expert路径:  answer_span/claim_text; 证据ref块∈输入证据,
                    语句级ref(#sN)∈linearize_context语句集
        student路径: quote/span; evidence_ref ev-N可解析且在证据范围内
  (b) gold对齐——citation P/R(refute定位的cited块 vs gold_evidence_refs)
      +target_keywords锚点重叠率(violation_desc锚点)
  (c) 根因类别——分类准确率:
        expert路径:  localization.root_cause.operation vs GOLD_ROOT_CAUSE
        student路径: issue.rule_id vs row.item_id(同taxonomy 40项)

被评系统路径(两条, 均为集成推理的真实输出):
  expert   QAConsistencyModule(use_experts=True)的localizations——L0/L1
           专家族(集成裁决refute的确定性来源, ~0.1s/例, 测试可快照)
  student  (可选--d3-adapter)D3学生judge()的issues——生成式定位
           (quote/span/evidence_ref/rule_id)
           ⚠️ violations-17在D3 v2b训练语料内(d3_teacher_labels_v1含此
           17条), student口径按96号警示属"训练集内参考", 结果显式标注

指标语义:
  - macro P/R: 逐实例P/R的均值(分母=有cited块的refute实例 / 全部17条)
  - micro P/R: 块计数池化(refute实例口径, 与eval_violations的
    localization P/R可交叉核对)
  - 未检出实例(非refute): 无violations[]可评→不计入P的macro分母,
    计入R的全量分母(该引的未引, recall=0), 如实分开报告

落盘: runs协议(tools/run_utils.py open_run), 逐实例明细+汇总.

用法: $env:PYTHONUTF8='1'; python tools/eval_span_faithfulness.py
      python tools/eval_span_faithfulness.py --d3-adapter models/llm/d3_student_v2b
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.eval_lib import (  # noqa: E402
    build_qa_input,
    read_jsonl,
)
from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.eval_root_cause import GOLD_ROOT_CAUSE  # noqa: E402
from tools.run_utils import open_run  # noqa: E402

EVALSET = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"

#: 违例类别→典型根因操作(粗粒度对照表; 精粒度gold=GOLD_ROOT_CAUSE逐条)
CATEGORY_TYPICAL_OPERATIONS: dict[str, tuple[str, ...]] = {
    "identifier": ("dual_registration", "value_substitution"),
    "enumeration": ("scope_leakage", "value_substitution"),
    "traceability": ("relation_inversion", "negation_mismatch",
                     "value_substitution"),
    "exception_template": ("exception_flow_mismatch", "entity_substitution"),
    "document_name": ("value_substitution",),
    "function_coverage": ("compliance_gap",),
    "qualification_coverage": ("compliance_gap",),
}


# ── 纯函数内核(测试覆盖) ─────────────────────────────────────────────────


def block_ref(ref: str) -> str:
    """语句级ref('ev-000222#s7') → 块级ref('ev-000222')(与eval_violations一致)."""
    return str(ref).split("#", 1)[0]


def parse_ev_index(evidence_ref: str, n_evidence: int) -> int | None:
    """student路径evidence_ref('ev-3')→0-based下标; 非法/越界→None."""
    text = str(evidence_ref).strip()
    if not text.startswith("ev-"):
        return None
    digits = text[len("ev-"):]
    if not digits.isdigit():
        return None
    index = int(digits) - 1
    return index if 0 <= index < n_evidence else None


def answer_side_check(span: tuple[int, int] | list[int] | None,
                      quote: str, answer: str) -> dict[str, Any]:
    """answer侧字面检查(两个正交事实, 96号copy约束口径区分).

    quote_in_answer: 引用文本逐字见于answer——(a)字面忠实的本体
    span_exact:      span区间切片逐字==quote——copy精度(2610.28393:
                     逐字复制是LLM已知弱点, 单独计量不给字面忠实兜底)
    status四态(诊断): span_exact / span_inexact_text_found(区间错但文本
    在) / span_missing_text_found(无span但文本在) / text_absent(文本不在
    answer——合成claim_text类通道的典型形态).
    """
    text = str(quote)
    quote_in_answer = bool(text) and text in answer
    has_span = (span is not None and isinstance(span, (tuple, list))
                and len(span) == 2)
    span_exact = False
    if has_span:
        start, end = int(span[0]), int(span[1])
        span_exact = (0 <= start < end <= len(answer)
                      and answer[start:end] == text)
    if span_exact:
        status = "span_exact"
    elif quote_in_answer and has_span:
        status = "span_inexact_text_found"
    elif quote_in_answer:
        status = "span_missing_text_found"
    else:
        status = "text_absent"
    return {"status": status, "quote_in_answer": quote_in_answer,
            "span_exact": span_exact}


def citation_pr(cited: set[str], gold: set[str]) -> dict[str, Any]:
    """ALCE单实例citation precision/recall(块级).

    precision = |cited∩gold|/|cited| (无cited→None, 不给假0)
    recall    = |cited∩gold|/|gold|  (无gold→None)
    """
    hits = cited & gold
    return {
        "n_cited": len(cited),
        "n_gold": len(gold),
        "n_hit": len(hits),
        "precision": round(len(hits) / len(cited), 4) if cited else None,
        "recall": round(len(hits) / len(gold), 4) if gold else None,
        "cited_blocks": sorted(cited),
        "hit_blocks": sorted(hits),
        "missed_gold_blocks": sorted(gold - cited),
    }


def anchor_overlap(cited_blocks: set[str],
                   evidence_text_by_id: dict[str, str],
                   target_keywords: list[str]) -> dict[str, Any]:
    """(b)辅助: cited块文本与violation_desc锚点关键词的重叠.

    ALCE precision的gold块口径之外, desc锚点回答"引用的块是否真的
    含违例词元"——cited∩gold=0但关键词命中的引用是'相关但非gold'的
    信号(如引用了矛盾的另一侧), 单独报告不并入precision.
    """
    keywords = [str(kw) for kw in target_keywords if str(kw)]
    hits = sorted(block for block in cited_blocks
                  if block in evidence_text_by_id
                  and any(kw in evidence_text_by_id[block]
                          for kw in keywords))
    return {
        "n_keywords": len(keywords),
        "n_cited": len(cited_blocks),
        "n_cited_with_keyword": len(hits),
        "cited_with_keyword": hits,
    }


def no_citation_pr(gold: set[str]) -> dict[str, Any]:
    """无refute判定时的citation记录: 无引用可评, recall记0(该引未引)."""
    return {
        "n_cited": 0, "n_gold": len(gold), "n_hit": 0,
        "precision": None, "recall": 0.0,
        "cited_blocks": [], "hit_blocks": [],
        "missed_gold_blocks": sorted(gold),
    }


def expert_literal_checks(localization: Any, answer: str,
                          evidence_ids: set[str],
                          statement_ids: set[str]) -> dict[str, Any]:
    """(a)expert路径逐localization的字面忠实检查.

    answer侧: answer_span切片==claim_text(四态口径).
    证据侧: 每个evidence定位的块id∈输入证据集; 语句级statement_id
    (#sN)∈linearize_context产出的语句集(块级ref无#后缀, 只查块).
    """
    loc = localization
    refs: list[dict[str, Any]] = []
    refs_ok = True
    for ev in loc.evidence:
        block_ok = str(ev.evidence_id) in evidence_ids
        stmt_text = str(ev.statement_id)
        stmt_ok = ("#" not in stmt_text
                   or stmt_text in statement_ids)
        refs_ok = refs_ok and block_ok and stmt_ok
        refs.append({
            "statement_id": stmt_text,
            "block_exists": block_ok,
            "statement_exists": stmt_ok,
        })
    side = answer_side_check(loc.answer_span, loc.claim_text, answer)
    return {
        "claim_id": str(loc.claim_id),
        "method": str(loc.method),
        "answer_side": side["status"],
        "quote_in_answer": side["quote_in_answer"],
        "span_exact": side["span_exact"],
        "answer_faithful": side["quote_in_answer"],
        "evidence_refs": refs,
        "evidence_refs_ok": refs_ok,
        "literal_faithful": side["quote_in_answer"] and refs_ok,
    }


def student_literal_checks(issue: dict[str, Any], answer: str,
                           n_evidence: int) -> dict[str, Any]:
    """(a)student路径逐issue的字面忠实检查(quote/span/evidence_ref)."""
    quote = str(issue.get("quote", ""))
    raw_span = issue.get("span")
    side = answer_side_check(raw_span, quote, answer)
    index = parse_ev_index(str(issue.get("evidence_ref", "")), n_evidence)
    return {
        "quote": quote[:80],
        "answer_side": side["status"],
        "quote_in_answer": side["quote_in_answer"],
        "span_exact": side["span_exact"],
        "answer_faithful": side["quote_in_answer"],
        "evidence_ref": str(issue.get("evidence_ref", "")),
        "evidence_index": index,
        "evidence_ref_ok": index is not None,
        "rule_id": str(issue.get("rule_id", "")),
        "literal_faithful": side["quote_in_answer"] and index is not None,
    }


def _row_context(row: dict[str, Any]) -> tuple[set[str], set[str],
                                                dict[str, str]]:
    """行证据→(块id集, 语句id集, 块id→文本). 纯派生, 不跑模块."""
    evidence = row["evidence"]
    evidence_ids = {str(item["evidence_id"]) for item in evidence}
    statement_ids = {st.statement_id for st in
                     linearize_context(build_qa_input(row).evidence)}
    texts = {str(item["evidence_id"]): str(item["text"])
             for item in evidence}
    return evidence_ids, statement_ids, texts


# ── 逐实例评测 ───────────────────────────────────────────────────────────


def evaluate_instance_expert(row: dict[str, Any],
                             result: Any) -> dict[str, Any]:
    """expert路径单实例: (a)(b)(c)三检查 + citation P/R."""
    iid = str(row["instance_id"])
    evidence_ids, statement_ids, texts = _row_context(row)
    gold = {str(ref) for ref in row["gold_evidence_refs"]}
    gold_cause = GOLD_ROOT_CAUSE[iid]
    loc_checks = [expert_literal_checks(loc, str(row["answer"]),
                                        evidence_ids, statement_ids)
                  for loc in result.localizations]
    cited = {block_ref(ev.statement_id)
             for loc in result.localizations for ev in loc.evidence}
    detected = result.verdict == "refute"
    pr = citation_pr(cited, gold) if detected else no_citation_pr(gold)
    overlap = anchor_overlap(cited, texts,
                             list(row.get("target_keywords", [])))
    operations = [str((loc.root_cause or {}).get("operation", ""))
                  for loc in result.localizations]
    sources = [str((loc.root_cause or {}).get("source", ""))
               for loc in result.localizations]
    return {
        "instance_id": iid,
        "path": "expert",
        "violation_category": str(row["violation_category"]),
        "item_id": str(row["item_id"]),
        "expected_verdict": str(row["expected_verdict"]),
        "predicted_verdict": str(result.verdict),
        "detected": detected,
        "n_localizations": len(result.localizations),
        "literal": {
            "n_localizations": len(loc_checks),
            "n_answer_faithful": sum(int(c["answer_faithful"])
                                     for c in loc_checks),
            "n_span_exact": sum(int(c["span_exact"]) for c in loc_checks),
            "n_refs_ok": sum(int(c["evidence_refs_ok"])
                             for c in loc_checks),
            "n_literal_faithful": sum(int(c["literal_faithful"])
                                      for c in loc_checks),
            "answer_side_states": [c["answer_side"] for c in loc_checks],
            "localizations": loc_checks,
        },
        "citation": pr,
        "anchor_overlap": overlap,
        "root_cause": {
            "gold": {"source": gold_cause["source"],
                     "operation": gold_cause["operation"]},
            "predicted_operations": operations,
            "predicted_sources": sources,
            "operation_any_hit": (detected
                                  and gold_cause["operation"] in operations),
            "source_any_hit": (detected
                               and gold_cause["source"] in sources),
            "operation_per_localization": round(
                sum(int(op == gold_cause["operation"])
                    for op in operations) / len(operations), 4)
            if operations else None,
        },
    }


def evaluate_instance_student(row: dict[str, Any], verdict: str,
                              issues: list[dict[str, Any]]
                              ) -> dict[str, Any]:
    """student路径单实例: (a)(b)(c)三检查 + citation P/R."""
    iid = str(row["instance_id"])
    evidence = row["evidence"]
    gold = {str(ref) for ref in row["gold_evidence_refs"]}
    gold_cause = GOLD_ROOT_CAUSE[iid]
    detected = verdict == "refute"
    checks = [student_literal_checks(issue, str(row["answer"]),
                                     len(evidence))
              for issue in issues]
    cited: set[str] = set()
    for issue, check in zip(issues, checks):
        if check["evidence_index"] is not None:
            cited.add(str(evidence[check["evidence_index"]]["evidence_id"]))
    pr = citation_pr(cited, gold) if detected else no_citation_pr(gold)
    texts = {str(item["evidence_id"]): str(item["text"])
             for item in evidence}
    overlap = anchor_overlap(cited, texts,
                             list(row.get("target_keywords", [])))
    item_id = str(row["item_id"])
    rule_ids = [str(issue.get("rule_id", "")) for issue in issues]
    return {
        "instance_id": iid,
        "path": "student",
        "violation_category": str(row["violation_category"]),
        "item_id": item_id,
        "expected_verdict": str(row["expected_verdict"]),
        "predicted_verdict": verdict,
        "detected": detected,
        "n_issues": len(issues),
        "literal": {
            "n_issues": len(checks),
            "n_answer_faithful": sum(int(c["answer_faithful"])
                                     for c in checks),
            "n_span_exact": sum(int(c["span_exact"]) for c in checks),
            "n_refs_ok": sum(int(c["evidence_ref_ok"]) for c in checks),
            "n_literal_faithful": sum(int(c["literal_faithful"])
                                      for c in checks),
            "answer_side_states": [c["answer_side"] for c in checks],
            "issues": checks,
        },
        "citation": pr,
        "anchor_overlap": overlap,
        "root_cause": {
            "gold": {"item_id": item_id,
                     "operation": gold_cause["operation"]},
            "predicted_rule_ids": rule_ids,
            "rule_id_any_hit": detected and item_id in rule_ids,
        },
    }


# ── 汇总 ─────────────────────────────────────────────────────────────────


def aggregate_details(details: list[dict[str, Any]],
                      unit: str = "localization") -> dict[str, Any]:
    """P/R macro+micro + 字面忠实率 + 根因准确率 + 类别分组.

    分母口径(显式, 不混算):
      detected = predicted_verdict==refute的实例(有violations[]可评)
      macro P  = mean(逐实例precision | precision非None)
      macro R(detected) = mean(逐实例recall, 未检出=0, 分母=detected数)
      macro R(all)      = mean(逐实例recall, 分母=全部实例)
      micro = 块计数池化(仅detected实例, 与eval_violations可交叉核对)
    """
    detected = [d for d in details if d["detected"]]
    precisions = [d["citation"]["precision"] for d in detected
                  if d["citation"]["precision"] is not None]
    recalls_detected = [float(d["citation"]["recall"] or 0.0)
                        for d in detected]
    recalls_all = [float(d["citation"]["recall"] or 0.0) for d in details]
    n_cited_total = sum(d["citation"]["n_cited"] for d in detected)
    n_gold_total = sum(d["citation"]["n_gold"] for d in detected)
    n_hit_total = sum(d["citation"]["n_hit"] for d in detected)
    literal = [d["literal"] for d in detected]
    unit_key = "n_localizations" if unit == "localization" else "n_issues"
    n_units = sum(lit[unit_key] for lit in literal)
    n_faithful = sum(lit["n_literal_faithful"] for lit in literal)
    n_answer = sum(lit["n_answer_faithful"] for lit in literal)
    n_refs = sum(lit["n_refs_ok"] for lit in literal)
    n_span_exact = sum(lit.get("n_span_exact", 0) for lit in literal)
    anchor_hits = [d["anchor_overlap"]["n_cited_with_keyword"]
                   for d in detected]
    anchor_cited = [d["anchor_overlap"]["n_cited"] for d in detected]

    def _round(value: float | None, n: int) -> float | None:
        return round(value / n, 4) if n else None

    op_hits = sum(int(d["root_cause"].get("operation_any_hit",
                                          False)) for d in detected)
    rule_hits = sum(int(d["root_cause"].get("rule_id_any_hit",
                                            False)) for d in detected)
    # 根因指标按路径二选一: expert有operation无rule_id, student反之;
    # 非适用键置None(避免0/N的误导性读数)
    has_operations = any("predicted_operations" in d["root_cause"]
                         for d in details)
    has_rule_ids = any("predicted_rule_ids" in d["root_cause"]
                       for d in details)
    by_category: dict[str, dict[str, Any]] = {}
    for category in sorted({d["violation_category"] for d in details}):
        group = [d for d in details
                 if d["violation_category"] == category]
        group_detected = [d for d in group if d["detected"]]
        by_category[category] = {
            "n": len(group),
            "n_detected": len(group_detected),
            "macro_recall_detected": _round(
                sum(float(d["citation"]["recall"] or 0.0)
                    for d in group_detected), len(group_detected)),
            "n_operation_any_hit": sum(
                int(d["root_cause"].get("operation_any_hit", False))
                for d in group_detected) if has_operations else None,
            "n_rule_id_any_hit": sum(
                int(d["root_cause"].get("rule_id_any_hit", False))
                for d in group_detected) if has_rule_ids else None,
            "ids": [d["instance_id"] for d in group],
        }
    return {
        "n_instances": len(details),
        "n_detected": len(detected),
        "citation": {
            "macro_precision": _round(sum(precisions), len(precisions)),
            "macro_recall_detected": _round(sum(recalls_detected),
                                            len(recalls_detected)),
            "macro_recall_all": _round(sum(recalls_all),
                                       len(recalls_all)),
            "micro_precision": (round(n_hit_total / n_cited_total, 4)
                                if n_cited_total else None),
            "micro_recall": (round(n_hit_total / n_gold_total, 4)
                             if n_gold_total else None),
            "micro_counts": {
                "cited_blocks": n_cited_total,
                "gold_blocks": n_gold_total,
                "hit_blocks": n_hit_total,
            },
            "denominators": {
                "macro_precision": f"{len(precisions)}实例(有cited的refute)",
                "macro_recall_detected": f"{len(recalls_detected)}detected",
                "macro_recall_all": f"{len(recalls_all)}全部",
                "micro": "detected实例块计数池化(与eval_violations同口径)",
            },
        },
        "anchor_overlap": {
            "n_cited_blocks": sum(anchor_cited),
            "n_cited_with_keyword": sum(anchor_hits),
            "rate": _round(sum(anchor_hits), sum(anchor_cited)),
        },
        "literal": {
            "unit": unit,
            "n_units": n_units,
            "n_literal_faithful": n_faithful,
            "literal_faithful_rate": _round(n_faithful, n_units),
            "n_answer_faithful": n_answer,
            "answer_faithful_rate": _round(n_answer, n_units),
            "n_span_exact": n_span_exact,
            "span_exact_rate": _round(n_span_exact, n_units),
            "n_evidence_refs_ok": n_refs,
            "evidence_refs_ok_rate": _round(n_refs, n_units),
            "answer_side_states": [state for lit in literal
                                   for state in lit["answer_side_states"]],
        },
        "root_cause": {
            "operation_any_hit": _round(op_hits, len(detected))
            if has_operations else None,
            "operation_any_hit_fraction": (
                f"{op_hits}/{len(detected)}" if has_operations else None),
            "rule_id_any_hit": _round(rule_hits, len(detected))
            if has_rule_ids else None,
            "rule_id_any_hit_fraction": (
                f"{rule_hits}/{len(detected)}" if has_rule_ids else None),
        },
        "by_category": by_category,
        "undetected_ids": [d["instance_id"] for d in details
                           if not d["detected"]],
    }


# ── runner ───────────────────────────────────────────────────────────────


def run_expert_config(rows: list[dict[str, Any]]
                      ) -> list[dict[str, Any]]:
    """expert路径: QAConsistencyModule(use_experts=True)真实推理."""
    module = QAConsistencyModule(use_experts=True)
    return [evaluate_instance_expert(row, module.verify(build_qa_input(row)))
            for row in rows]


def run_student_config(rows: list[dict[str, Any]],
                       adapter: str) -> list[dict[str, Any]]:
    """student路径: D3学生judge()真实推理(懒加载, GPU).

    ⚠️ violations-17在d3_student_v2b训练语料内(d3_teacher_labels_v1),
    该路径指标属"训练集内参考"(96号§1判读3: 超过0.7先怀疑泄漏).
    """
    import tools.eval_d3_student as student  # 懒加载: 避免默认路径import期I/O

    student._ADAPTER = str(Path(adapter))
    details: list[dict[str, Any]] = []
    for row in rows:
        verdict, issues, _elapsed = student.judge(
            str(row["question"]), str(row["answer"]),
            [str(e["text"]) for e in row["evidence"]])
        details.append(evaluate_instance_student(row, verdict, issues))
    return details


def _print_summary(tag: str, summary: dict[str, Any]) -> None:
    citation = summary["citation"]
    literal = summary["literal"]
    root = summary["root_cause"]
    op_text = (f"operation any-hit={root['operation_any_hit_fraction']}"
               if root["operation_any_hit_fraction"] is not None else "")
    rule_text = (f"rule_id any-hit={root['rule_id_any_hit_fraction']}"
                 if root["rule_id_any_hit_fraction"] is not None else "")
    joiner = " " if op_text and rule_text else ""
    print(f"[{tag}] detected={summary['n_detected']}/{summary['n_instances']}"
          f" | macroP={citation['macro_precision']}"
          f" macroR(det)={citation['macro_recall_detected']}"
          f" macroR(all)={citation['macro_recall_all']}"
          f" | microP={citation['micro_precision']}"
          f" microR={citation['micro_recall']}"
          f" ({citation['micro_counts']['hit_blocks']}/"
          f"{citation['micro_counts']['cited_blocks']}"
          f" vs {citation['micro_counts']['hit_blocks']}/"
          f"{citation['micro_counts']['gold_blocks']})")
    print(f"  字面忠实(quote∈answer): {literal['n_literal_faithful']}/"
          f"{literal['n_units']}"
          f"({literal['literal_faithful_rate']}) | "
          f"span区间精确={literal['span_exact_rate']} "
          f"证据ref={literal['evidence_refs_ok_rate']}")
    print(f"  根因: {op_text}{joiner}{rule_text}")
    print(f"  锚点重叠: {summary['anchor_overlap']['n_cited_with_keyword']}/"
          f"{summary['anchor_overlap']['n_cited_blocks']}"
          f"({summary['anchor_overlap']['rate']})")
    print(f"  未检出: {summary['undetected_ids'] or '无'}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--d3-adapter", default="",
        help="D3学生adapter路径(空=只跑expert路径; "
             "如 models/llm/d3_student_v2b)")
    parser.add_argument("--limit", type=int, default=0,
                        help="只跑前N条(冒烟测试用)")
    args = parser.parse_args()

    rows = read_jsonl(EVALSET)
    if args.limit:
        rows = rows[:args.limit]

    configs: dict[str, dict[str, Any]] = {}
    started = time.time()
    expert_details = run_expert_config(rows)
    expert_summary = aggregate_details(expert_details, "localization")
    configs["expert"] = {"details": expert_details,
                         "summary": expert_summary}
    _print_summary("expert(L0/L1 localizations)", expert_summary)

    if args.d3_adapter:
        student_details = run_student_config(rows, args.d3_adapter)
        student_summary = aggregate_details(student_details, "issue")
        student_summary["caveat"] = (
            "violations-17在d3_student_v2b训练语料内"
            "(d3_teacher_labels_v1含此17条); 该路径数字为训练集内参考, "
            "按96号§1判读3(>0.7先怀疑评测泄漏)解读")
        configs["d3_student"] = {"details": student_details,
                                 "summary": student_summary}
        _print_summary("d3_student(生成式issues, 训练集内)", student_summary)

    report = {
        "schema": "span_faithfulness_eval_v1",
        "evalset": str(EVALSET.relative_to(BASE)),
        "alce_reference": "arXiv 2305.14627 (citation precision/recall)",
        "design_refs": ["99号Phase0-E1", "96号§5/§7.3"],
        "gold_anchor_fields": ["gold_evidence_refs(block级人工定位)",
                               "target_keywords(violation_desc锚点)",
                               "GOLD_ROOT_CAUSE(eval_root_cause根因gold)"],
        "engine": {
            "expert": "QAConsistencyModule(use_experts=True)",
            "d3_student": args.d3_adapter or None,
        },
        "configs": configs,
    }
    run = open_run("eval_span_faithfulness", {
        "evalset": str(EVALSET.relative_to(BASE)),
        "n": len(rows),
        "engine_expert": "QAConsistencyModule(use_experts=True)",
        "d3_adapter": args.d3_adapter or None,
        "limit": args.limit or None,
        "elapsed_s": round(time.time() - started, 1),
    })
    run.save_result(report)
    print(f"\nruns落盘 → {run.path}")


if __name__ == "__main__":
    main()
