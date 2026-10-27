r"""算法层双模块重组: 方向A(context_linking) ∥ 方向B(consistency).

结构:
  algorithms/
  ├── llm_client.py / bge_local.py / base.py / common/   ← 共享基础设施(原地)
  ├── context_linking/    ← 方向A: 上下文关联(聚合/实体链接/图文/召回)
  ├── consistency/        ← 方向B: 一致性校验(六通道/κ_D/NLI/baselines)
  └── qa_synthesis/       ← Task 2: QA对合成

归档(零外部引用的旧引擎): pair_checker, check_engine, llm_checks, srs_verifier,
  mermaid_graph, context_graph(若无存活引用), nli_discrepancy_review?
迁移步骤: 建包→移文件→批量import重写→测试验证(由调用方跑pytest)
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")
ALG = BASE / "algorithms"
ARCH = BASE / "tools/archive/2026_10/legacy_algorithms"

# import重写映射(顺序敏感: 具体在前)
REWRITE = [
    ("algorithms.consistency.checker", "algorithms.consistency.checker"),
    ("algorithms.consistency.nli_local", "algorithms.consistency.nli_local"),
    ("algorithms.consistency.nli_pair_claims", "algorithms.consistency.nli_pair_claims"),
    ("algorithms.consistency.nli_discrepancy_review", "algorithms.consistency.nli_discrepancy_review"),
    ("algorithms.consistency.srs_calib", "algorithms.consistency.srs_calib"),
    ("algorithms.consistency.semantic", "algorithms.consistency.semantic"),
    ("algorithms.consistency.syntax", "algorithms.consistency.syntax"),
    ("algorithms.consistency.logic", "algorithms.consistency.logic"),
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
    ("algorithms.qa_synth", "algorithms.qa_synthesis.qa_synth"),
    ("algorithms.qa_mutation_ops", "algorithms.qa_mutation_ops"),
]


def move(src: str, dst_dir: Path) -> None:
    s = ALG / src
    if not s.exists():
        print(f"  跳过(不存在): {src}")
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    d = dst_dir / s.name
    shutil.move(str(s), str(d))
    print(f"  {src} → {d.relative_to(ALG)}")


def rewrite_imports() -> int:
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
            for old, new in REWRITE:
                text = text.replace(old, new)
            if text != orig:
                f.write_text(text, encoding="utf-8")
                n += 1
    return n


def main() -> None:
    print("═══ Stage 1: 方向B consistency/ ═══")
    s = ALG / "consistency_checker.py"
    if s.exists():
        (ALG / "consistency").mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(ALG / "consistency/checker.py"))
        print("  consistency_checker.py → consistency/checker.py")
    for m in ("nli_local.py", "nli_pair_claims.py", "nli_discrepancy_review.py", "srs_calib.py"):
        move(m, ALG / "consistency")
    for pkg in ("semantic", "syntax", "logic"):
        move(pkg, ALG / "consistency")

    print("═══ Stage 2: 方向A context_linking/ ═══")
    for m in ("context_pipeline.py", "context_graph.py", "unit_retrieval.py",
              "unit_attention.py", "table_late.py", "va_colpali.py", "sqr.py"):
        move(m, ALG / "context_linking")
    for pkg in ("blackboard", "trimodal", "mmqa"):
        move(pkg, ALG / "context_linking")

    print("═══ Stage 3: Task2 qa_synthesis/ ═══")
    for m in ("qa_synth.py", "qa_mutation_ops.py"):
        move(m, ALG / "qa_synthesis")

    print("═══ Stage 4: 归档零引用旧引擎 ═══")
    ARCH.mkdir(parents=True, exist_ok=True)
    for m in ("pair_checker.py", "check_engine.py", "llm_checks.py",
              "srs_verifier.py", "mermaid_graph.py"):
        s = ALG / m
        if s.exists():
            shutil.move(str(s), str(ARCH / m))
            print(f"  归档 {m}")
    # evidence_recall残留(此前已归档, 目录重复)
    er = ALG / "evidence_recall"
    if er.exists():
        shutil.rmtree(er)
        print("  删除evidence_recall残留")

    print("═══ Stage 5: 包初始化与模块地图 ═══")
    (ALG / "context_linking/__init__.py").write_text(
        '"""方向A: 上下文关联 — 多模态上下文聚合/跨章节实体链接.\n\n'
        '输入: SRS文档(markdown+图+表格) → 输出: 聚合条目/Pair对(带上下文元数据)\n'
        '子模块: blackboard(ACDD多源融合) / trimodal(图文对齐) / mmqa(多模态QA)\n'
        '        context_pipeline(聚合管线) / unit_retrieval+unit_attention(单元召回)\n'
        '        table_late(表结构) / va_colpali(视觉检索) / sqr(结构化查询)\n'
        '"""\n', encoding="utf-8")
    (ALG / "consistency/__init__.py").write_text(
        '"""方向B: 一致性校验 — 对Pair对执行六族检测.\n\n'
        '输入: Pair对(premise, hypothesis) → 输出: 判定+条目+类型+位置+证据\n'
        '核心: checker.py(v4.1六通道: numeric/quote/term/enum/verify/nli, κ_D条件化)\n'
        '语义/语法/逻辑三层: semantic/ syntax/ logic/ (legacy)\n'
        'NLI: nli_local.py(本地推理) / nli_pair_claims.py\n'
        '"""\n', encoding="utf-8")
    (ALG / "qa_synthesis/__init__.py").write_text(
        '"""Task 2: QA对合成 — 从Pair数据集合成训练/评测QA.\n\n'
        'qa_synth.py(六级流水线) / qa_mutation_ops.py(48算子中的18个已实现)\n'
        '"""\n', encoding="utf-8")
    # 顶层__init__模块地图
    (ALG / "__init__.py").write_text(
        '"""GJB SRS一致性校验算法层.\n\n'
        "模块地图(两个平行方向 + 共享设施):\n"
        "  context_linking/  方向A: 上下文关联(聚合/实体链接/图文) → 产出Pair\n"
        "  consistency/      方向B: 一致性校验(六通道+κ_D) → 产出判定\n"
        "  qa_synthesis/     Task 2: QA对合成\n"
        "  llm_client.py / bge_local.py / base.py / common/  共享基础设施\n"
        '数据流: 文档 → [context_linking] → Pair → [consistency] → 判定\n'
        '"""\n', encoding="utf-8")

    print("\n═══ Stage 6: 批量import重写 ═══")
    n = rewrite_imports()
    print(f"  重写{n}个文件")

    # 清pycache
    for pc in ALG.rglob("__pycache__"):
        shutil.rmtree(pc, ignore_errors=True)
    print("\n完成. 请跑: python -m pytest tests/ -q")


if __name__ == "__main__":
    main()
