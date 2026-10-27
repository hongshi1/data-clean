"""Inventory legacy mutation operators against the QA answer-side contract.

This is a static audit artifact, not a gold-labelled dataset. It makes explicit
which historical operator families cannot be used as answer-side mutations.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data/gjb_438c/legacy_answer_mutation_audit.json"

ITEMS = [
    ("qa_mutation_ops", "TERM-01", "premise", "pair premise/hypothesis", "quarantined_legacy",
     "旧算子改premise并生成‘是否一致’答案；不是QA answer侧变异。"),
    ("qa_mutation_ops", "TERM-02", "hypothesis", "pair premise/hypothesis", "quarantined_legacy",
     "无定义scope证据；不能证明同名异义gold。"),
    ("qa_mutation_ops", "TERM-03", "premise", "pair premise/hypothesis", "quarantined_legacy",
     "删除枚举项未携带封闭范围证明。"),
    ("qa_mutation_ops", "TERM-06", "premise unit text", "pair premise/hypothesis", "quarantined_legacy",
     "只替换单位表面且不换算；等价单位会被伪造成冲突。"),
    ("qa_mutation_ops", "PARAM-01/02/05/07", "premise numeric", "pair premise/hypothesis", "quarantined_legacy",
     "旧正则仅局部改数，未冻结QA answer/context或完整scope proof。"),
    ("qa_mutation_ops", "PARAM-06", "premise operator", "pair premise/hypothesis", "quarantined_legacy",
     "翻转操作符未证明与同一context claim互斥。"),
    ("qa_mutation_ops", "LOGIC-01/03/05", "premise sequence/branch", "pair premise/hypothesis", "quarantined_legacy",
     "缺少条件路径、并行和完整枚举证明。"),
    ("qa_mutation_ops", "GJB-01/02/04", "premise/hypothesis text", "pair premise/hypothesis", "quarantined_compliance_pair",
     "旧二分类/模糊条款变异，没有规则context和QA answer proof。"),
    ("qa_mutation_ops", "TABLE_ITEM_MISSING/ACTOR_MISSING/STEP_MISSING", "hypothesis", "pair premise/hypothesis", "quarantined_cross_source_pair",
     "旧来源间差异标签，不是answer对冻结retrieved context的检验。"),
    ("mmqa.MutationEngine40", "TERM/PARAM/LOGIC/GJB", "virtual text/table/graph", "pair directory", "quarantined_context_mutation",
     "改变pair context而非answer；expected_label固定inconsistent且verify_gate未证明claim。"),
    ("mutation_v2", "40-item generic", "premise/hypothesis or source artifact", "pair occurrence", "quarantined_legacy",
     "同一编辑原语被复用于多个类型，缺QA answer/context proof。"),
    ("gen_injected_qa", "TERM/PARAM/LOGIC/GJB", "question/answer metadata", "original pair files", "quarantined_metadata_only",
     "inject_detail/question声称已变异，但原pair文件未被改写；存在标签泄漏。"),
    ("build_answer_evidence_evalset", "A1/A3/B3/C1/family", "synthesized answer + legacy evidence", "AEE v1", "quarantined_for_gold_rebuild",
     "缺原始question/冻结context或gold继承旧标签；只作迁移审计素材。"),
    ("answer_mutations", "ANSWER-NUM-EQ-CONFLICT-V1", "answer only", "QAInput + selected evidence", "deterministic_prototype",
     "仅支持subject/unit完全一致的显式等式数值冲突；未证明为通用算子。"),
    ("answer_mutations", "ANSWER-NUM-EQUIV-V1", "answer only", "QAInput + selected evidence", "deterministic_prototype",
     "只在冻结单位换算表内、question/subject对齐且原answer已被context支持时生成等价表面。"),
    ("answer_mutations", "ANSWER-NUM-IDENTITY-V1", "answer unchanged control", "QAInput + selected evidence", "deterministic_prototype",
     "生成数值answer冲突算子的support控制样本；question、answer、context保持原样。"),
    ("answer_mutations", "ANSWER-UNSUPPORTED-REVIEW", "answer only", "QAInput", "manual_review_candidate",
     "不自动标NIE；需人工确认context scope和是否存在隐含支持/反证。"),
]


def main() -> None:
    out = {
        "meta": {
            "version": "legacy_answer_mutation_audit_v1",
            "date": "2026-10-20",
            "scope": "answer-side QA mutation only; retrieval/context linking excluded",
            "notes": [
                "quarantined means not valid for the new benchmark without rebuilding input and gold",
                "audit statuses are engineering triage, not label gold",
            ],
            "total": len(ITEMS),
        },
        "operators": [
            {
                "source": source,
                "legacy_check_item": check_item,
                "mutated_side": side,
                "old_input_contract": contract,
                "status": status,
                "reason": reason,
            }
            for source, check_item, side, contract, status, reason in ITEMS
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"legacy mutation audit: {len(ITEMS)} rows → {OUT}")


if __name__ == "__main__":
    main()
