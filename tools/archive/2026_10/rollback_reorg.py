r"""回滚方向A的移动(上下文关联不属于本次治理范围), 保留方向B(consistency/)治理.

回滚:
  context_linking/* → algorithms/原位 (blackboard/trimodal/mmqa/context_*/unit_*/table_late/va_colpali/sqr)
  qa_synthesis/*    → algorithms/原位 (qa_synth/qa_mutation_ops)
  对应import重写反转

保留(方向B治理成果):
  consistency/checker.py(v4.1) + nli_local/nli_pair_claims/nli_discrepancy_review/srs_calib
  consistency/semantic|syntax|logic (B的三层)
  归档的零引用旧引擎(pair_checker/check_engine/llm_checks/srs_verifier/mermaid_graph)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")
ALG = BASE / "algorithms"

ROLLBACK_REWRITE = [
    ("algorithms.blackboard", "algorithms.blackboard"),
    ("algorithms.trimodal", "algorithms.trimodal"),
    ("algorithms.mmqa", "algorithms.mmqa"),
    ("algorithms.context_pipeline", "algorithms.context_pipeline"),
    ("algorithms.context_graph", "algorithms.context_graph"),
    ("algorithms.unit_retrieval", "algorithms.unit_retrieval"),
    ("algorithms.unit_attention", "algorithms.unit_attention"),
    ("algorithms.table_late", "algorithms.table_late"),
    ("algorithms.va_colpali", "algorithms.va_colpali"),
    ("algorithms.sqr", "algorithms.sqr"),
    ("algorithms.qa_synth", "algorithms.qa_synth"),
    ("algorithms.qa_mutation_ops", "algorithms.qa_mutation_ops"),
]


def main() -> None:
    print("═══ 回滚方向A移动 ═══")
    cl = ALG / "context_linking"
    if cl.exists():
        for item in list(cl.iterdir()):
            if item.name == "__pycache__":
                continue
            shutil.move(str(item), str(ALG / item.name))
            print(f"  {item.name} → algorithms/")
    # 丢弃包__init__(A不动包化)
    if cl.exists():
        shutil.rmtree(cl)
        print("  删除context_linking/包")
    qs = ALG / "qa_synthesis"
    if qs.exists():
        for item in list(qs.iterdir()):
            if item.name == "__pycache__":
                continue
            shutil.move(str(item), str(ALG / item.name))
            print(f"  {item.name} → algorithms/")
        shutil.rmtree(qs)
        print("  删除qa_synthesis/包")

    print("\n═══ 反转import重写(A相关) ═══")
    n = 0
    for d in ("tests", "tools", "algorithms"):
        for f in (BASE / d).rglob("*.py"):
            if "archive" in str(f) or "__pycache__" in str(f):
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (PermissionError, UnicodeDecodeError):
                continue
            orig = text
            for old, new in ROLLBACK_REWRITE:
                text = text.replace(old, new)
            if text != orig:
                f.write_text(text, encoding="utf-8")
                n += 1
    print(f"  反转重写{n}个文件")

    print("\n═══ 清理异常文件 ═══")
    # 重新出现的test_evidence_recall.py(引用不存在的algorithms.context_association.*, 损坏WIP)
    te = BASE / "tests/test_evidence_recall.py"
    if te.exists():
        te.unlink()
        print("  删除tests/test_evidence_recall.py(损坏WIP, 引用不存在模块)")

    print("\n═══ 顶层模块地图(B治理+A原位) ═══")
    (ALG / "__init__.py").write_text(
        '"""GJB SRS算法层.\n\n'
        "平行方向(本层仅治理方向B):\n"
        "  方向A 上下文关联: blackboard/ trimodal/ mmqa/ 及context_*等(原位, 待专项治理)\n"
        "  方向B 一致性校验: consistency/ ← 2026-10-14治理\n"
        "      checker.py(v4.1六通道κD) / nli_local / nli_pair_claims /\n"
        "      nli_discrepancy_review / srs_calib / semantic|syntax|logic三层\n"
        "  Task 2 QA合成: qa_synth.py / qa_mutation_ops.py(原位)\n"
        "  共享设施: llm_client.py / bge_local.py / base.py / common/\n"
        '数据流: 文档 → [方向A聚合] → Pair → [方向B校验] → 判定\n'
        '"""\n', encoding="utf-8")

    for pc in ALG.rglob("__pycache__"):
        shutil.rmtree(pc, ignore_errors=True)
    print("\n回滚完成. 请跑: python -m pytest tests/ -q")


if __name__ == "__main__":
    main()
