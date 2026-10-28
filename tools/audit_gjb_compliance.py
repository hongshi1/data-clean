"""GJB规则引擎的04号SRS全量合规审计（文档级，L1确定性）。

输入:
  data/gjb_438c/mineru_standard/04数据统一访问服务软件需求规格说明-终稿
    /office/*_content_list.json（411块全量，表块=表体HTML+caption，
    与build_violation_evalset.block_text同一冻结口径）
  knowledge/gjb_438c_rules_full.json（120条规则，87条applies_to含SRS，
    经gjb_rule_engine.compile_rule程序化编译为presence检查）
  knowledge/consistency_taxonomy_v3.json（GJB-01~11的doc04_evidence
    引文，用于一致性核对）

产出（runs协议落盘 result.json + 控制台报告）:
  1. 编译覆盖率: 87条SRS规则中可编译N条(按type分布)/manual M条
     (按compile_note分布)——诚实报告不可编译的规则
  2. 逐规则审计: satisfied/partial/violated/manual + matched/missed
     模式 + evidence_refs（块级定位）
  3. 分簇报告: GJB-01~11各簇规则级verdict（best-of聚合，OR语义）
  4. taxonomy一致性核对: 引擎簇裁决 vs doc04_evidence标注状态
     （exact/direction/mismatch三级，掉电/降级/追溯/合格性等命中数）

用法:
  $env:PYTHONUTF8='1'; $env:PYTHONPATH='.'; python tools/audit_gjb_compliance.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from glob import glob
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.evidence_statements import (  # noqa: E402
    linearize_context,
)
from algorithms.consistency.gjb_rule_engine import (  # noqa: E402
    CHECK_ITEMS,
    aggregate_clusters,
    audit_document,
    load_rule_library,
    compile_rule,
)
from algorithms.consistency.qa_models import (  # noqa: E402
    RetrievedEvidence,
    SourceRef,
)
from tools.run_utils import open_run  # noqa: E402

CONTENT_LIST_GLOB = ("data/gjb_438c/mineru_standard/"
                     "04*/office/*_content_list.json")
TAXONOMY_PATH = BASE / "knowledge/consistency_taxonomy_v3.json"
DOC04_ID = "04数据统一访问服务软件需求规格说明-终稿"

#: taxonomy v3 GJB-01~11的doc04_evidence状态判定（簇id -> (期望状态,
#: 判定依据引文关键词)）。期望状态三值: present/partial/absent；判定
#: 依据=doc04_evidence/doc04_violations字段的人工状态归纳，核对表在
#: 报告中并排展示引擎裁决与taxonomy原文供人工复核。
_TAXONOMY_EXPECTATIONS: dict[str, tuple[str, str]] = {
    "GJB-01": ("partial", "表80合格性规定仅6行覆盖3.2.1~3.2.6，"
                         "3.3~3.17全部需求无合格性方法"),
    "GJB-02": ("partial", "表68安全性(故障检测+重连)——有容错但不完备"),
    "GJB-03": ("partial", "表69保密性——有但无权限等级划分"),
    "GJB-04": ("absent", "无审计日志章节/表(1.2仅概述级提及，3.2无对应)"),
    "GJB-05": ("present", "表81正向+表82逆向——有双向追溯表"),
    "GJB-06": ("absent", "用例表E1仅提示文本，无时间戳/位置/等级/建议要素"),
    "GJB-07": ("partial", "表68 row1系统自检——有自检但无周期自检"),
    "GJB-08": ("absent", "无掉电保护条款(表68仅故障检测+重连)"),
    "GJB-09": ("absent", "表63-67有值域约束但无显式输入校验声明"),
    "GJB-10": ("absent", "无升级条款(3.15保障需求仅「软件升级」一行b383)"),
    "GJB-11": ("absent", "3.1只有一个运行状态，无降级模式声明"),
}

_MATCH_MATRIX = {
    ("satisfied", "present"): ("exact", "存在性一致"),
    ("partial", "partial"): ("exact", "部分达成一致"),
    ("violated", "absent"): ("exact", "缺失一致"),
    ("partial", "present"): ("direction", "簇内容存在，引擎见规则粒度缺口"
                                      "(量词/枚举要素)"),
    ("violated", "partial"): ("direction", "均判缺陷方向，引擎判更严格"),
    ("partial", "absent"): ("direction", "taxonomy要求的专项内容缺失方向"
                                     "一致，引擎在簇内见其他关联内容"),
    ("satisfied", "absent"): ("mismatch", "引擎判满足而taxonomy判缺失"),
    ("violated", "present"): ("mismatch", "引擎判缺失而taxonomy判存在"),
    ("manual", "present"): ("mismatch", "簇内无可审计规则"),
    ("manual", "partial"): ("mismatch", "簇内无可审计规则"),
    ("manual", "absent"): ("mismatch", "簇内无可审计规则"),
}


def load_doc04_blocks() -> tuple[RetrievedEvidence, ...]:
    """04号content_list -> 冻结证据块（表体+caption，text块原文）。"""
    paths = [p for p in glob(str(BASE / CONTENT_LIST_GLOB))]
    if len(paths) != 1:
        raise FileNotFoundError(
            f"预期1个04号content_list，实际{len(paths)}: {paths}")
    items = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
    blocks: list[RetrievedEvidence] = []
    for index, item in enumerate(items):
        kind = str(item.get("type", ""))
        if kind == "table":
            body = str(item.get("table_body") or "")
            caption = item.get("table_caption") or []
            text = body + (f"\n{caption[0]}" if caption else "")
            source_type = "table"
        elif kind == "text":
            text = str(item.get("text") or "")
            source_type = "text"
        else:
            continue
        if not text.strip():
            continue
        blocks.append(RetrievedEvidence(
            evidence_id=f"ev-b{index:03d}",
            text=text,
            source_type=source_type,
            source_ref=SourceRef(
                doc_id=DOC04_ID, block_id=f"block-{index:06d}"),
            scope_id=f"{DOC04_ID}:block-{index:06d}",
            completeness="open",
        ))
    return tuple(blocks)


def taxonomy_gjb_items() -> dict[str, dict]:
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in taxonomy["items"]
            if str(item.get("id", "")).startswith("GJB")}


def consistency_table(audits: dict) -> list[dict]:
    """引擎簇裁决 vs taxonomy doc04_evidence 的一效性核对行。"""
    taxonomy = taxonomy_gjb_items()
    rows: list[dict] = []
    for cluster in CHECK_ITEMS:
        state = audits[cluster]
        expected, basis = _TAXONOMY_EXPECTATIONS[cluster]
        level, note = _MATCH_MATRIX.get(
            (state.verdict, expected), ("mismatch", "未知组合"))
        item = taxonomy.get(cluster, {})
        rows.append({
            "cluster": cluster,
            "engine_verdict": state.verdict,
            "taxonomy_expectation": expected,
            "match_level": level,
            "note": note,
            "taxonomy_doc04_evidence": item.get("doc04_evidence", ""),
            "taxonomy_doc04_violations": item.get("doc04_violations", []),
            "expectation_basis": basis,
            "engine_matched": list(state.matched_patterns),
            "engine_missed": list(state.missed_patterns),
        })
    return rows


def main() -> None:
    blocks = load_doc04_blocks()
    statements = linearize_context(blocks)
    rules = load_rule_library()
    checks = [compile_rule(rule) for rule in rules]
    results = audit_document(statements, checks)
    audits = aggregate_clusters(results)

    compiled = [c for c in checks if c.check_type != "manual"]
    manual = [c for c in checks if c.check_type == "manual"]
    type_dist = Counter(c.check_type for c in compiled)
    manual_notes = Counter(c.compile_note for c in manual)
    verdict_dist = Counter(r.verdict for r in results)
    table = consistency_table(audits)
    exact = sum(1 for row in table if row["match_level"] == "exact")
    direction = sum(1 for row in table if row["match_level"] == "direction")
    mismatch = sum(1 for row in table if row["match_level"] == "mismatch")

    run = open_run("audit_gjb_compliance", {
        "doc04_content_list": CONTENT_LIST_GLOB,
        "rule_library": "knowledge/gjb_438c_rules_full.json",
        "taxonomy": str(TAXONOMY_PATH.relative_to(BASE)),
        "blocks": len(blocks),
        "statements": len(statements),
        "rules_total": len(rules),
    })
    run.save_result({
        "summary": {
            "rules_total": len(rules),
            "compilable": len(compiled),
            "manual": len(manual),
            "compilable_by_type": dict(type_dist),
            "manual_by_note": dict(manual_notes),
            "rule_verdicts": dict(verdict_dist),
            "cluster_verdicts": {c: audits[c].verdict for c in CHECK_ITEMS},
            "consistency": {
                "exact": exact, "direction": direction,
                "mismatch": mismatch},
            "blocks": len(blocks),
            "statements": len(statements),
        },
        "clusters": {
            c: {
                "verdict": audits[c].verdict,
                "rule_ids": list(audits[c].rule_ids),
                "audited_rule_ids": list(audits[c].audited_rule_ids),
                "manual_rule_ids": list(audits[c].manual_rule_ids),
                "matched_patterns": list(audits[c].matched_patterns),
                "missed_patterns": list(audits[c].missed_patterns),
                "evidence_refs": list(audits[c].evidence_refs),
                "note": audits[c].note,
            } for c in CHECK_ITEMS},
        "consistency_table": table,
        "rules": [
            {"rule_id": r.rule_id, "check_type": r.check_type,
             "verdict": r.verdict, "requirement": r.requirement,
             "source_anchor": r.source_anchor,
             "patterns": list(r.patterns),
             "matched": list(r.matched), "missed": list(r.missed),
             "evidence_refs": list(r.evidence_refs),
             "cluster": r.cluster,
             "rationale": r.rationale,
             "quantified": next(c.quantified for c in checks
                                if c.rule_id == r.rule_id),
             "compile_note": next(c.compile_note for c in checks
                                  if c.rule_id == r.rule_id),
            } for r in results],
    })
    run.log(blocks=len(blocks), statements=len(statements),
            rules=len(rules), compilable=len(compiled), manual=len(manual))

    print("04号SRS全量GJB合规审计（规则库驱动，非手编清单）")
    print(f"  证据块 {len(blocks)} 条，线性化语句 {len(statements)} 条")
    print()
    print("== 编译覆盖率（87条SRS适用规则） ==")
    print(f"  可编译 {len(compiled)} 条: "
          + "、".join(f"{t}×{n}" for t, n in sorted(type_dist.items())))
    print(f"  manual {len(manual)} 条: "
          + "、".join(f"{n}条 {note}" for note, n in manual_notes.most_common()))
    print("  逐规则裁决: "
          + "、".join(f"{v}×{n}" for v, n in verdict_dist.most_common()))
    print()
    print("== 分簇报告（GJB-01~11，best-of聚合） ==")
    for cluster in CHECK_ITEMS:
        state = audits[cluster]
        print(f"  {cluster} {state.verdict:9s} "
              f"规则[{('、'.join(state.audited_rule_ids))}]"
              + (f" manual[{('、'.join(state.manual_rule_ids))}]"
                 if state.manual_rule_ids else ""))
        if state.matched_patterns:
            print(f"      命中: {'、'.join(state.matched_patterns[:8])}"
                  + ("..." if len(state.matched_patterns) > 8 else ""))
        if state.missed_patterns:
            print(f"      缺失: {'、'.join(state.missed_patterns[:8])}"
                  + ("..." if len(state.missed_patterns) > 8 else ""))
    print()
    print("== taxonomy doc04_evidence 一致性核对 ==")
    for row in table:
        marker = {"exact": "HIT ", "direction": "dir~",
                  "mismatch": "MISS"}[row["match_level"]]
        print(f"  [{marker}] {row['cluster']} "
              f"engine={row['engine_verdict']:9s} "
              f"taxonomy={row['taxonomy_expectation']:7s} {row['note']}")
    print(f"  命中: exact {exact} + direction {direction} / "
          f"mismatch {mismatch}")
    key_findings = {
        "掉电(GJB-08)": audits["GJB-08"].verdict,
        "降级模式(GJB-11)": "降级" in audits["GJB-11"].missed_patterns,
        "追溯(GJB-05)": audits["GJB-05"].verdict,
        "合格性(GJB-01)": audits["GJB-01"].verdict,
        "输入防护(GJB-09)": audits["GJB-09"].verdict,
        "报警要素(GJB-06)": audits["GJB-06"].verdict,
    }
    print("  关键发现: " + "、".join(
        f"{k}={v}" for k, v in key_findings.items()))
    print()
    print(f"runs落盘 -> {run.path}")


if __name__ == "__main__":
    main()
