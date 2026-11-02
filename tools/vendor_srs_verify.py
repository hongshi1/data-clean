#!/usr/bin/env python3
"""vendor算法栈进srs_verify包: 上下文关联+提纯+覆盖检测+DEQ.

复制源模块→srs_verify包内, 重写跨包import(algorithms.*→srs_verify*).
幂等: 目标存在则覆盖. 产物:
  srs_verify/context/{evidence,heads,recall,rerank,pipeline}.py  (O1-unit召回)
  srs_verify/context/{atomizer,pair_scorers,bge_local}.py
  srs_verify/{evidence_purifier,evidence_subtractor,coverage_detector,deq_pipeline}.py
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path("algorithms")
PKG = Path("srs_verify_package/srs_verify")

# (源, 目标, 重写规则列表[(pattern, replacement)])
COPIES = [
    # 上下文关联栈(O1-unit召回)
    (SRC / "context_linking/evidence_recall/evidence.py",
     PKG / "context/evidence.py", []),
    (SRC / "context_linking/evidence_recall/heads.py",
     PKG / "context/heads.py", []),
    (SRC / "context_linking/evidence_recall/recall.py",
     PKG / "context/recall.py", []),
    (SRC / "context_linking/evidence_recall/rerank.py",
     PKG / "context/rerank.py",
     [("from algorithms.blackboard.reranker import BgeReranker",
       "raise ImportError('BgeReranker未vendor, 精排降级直通')")]),
    (SRC / "context_linking/evidence_recall/pipeline.py",
     PKG / "context/pipeline.py",
     [("from algorithms.common import bge_local",
       "from srs_verify.context import bge_local"),
      ("from algorithms.blackboard.reranker import BgeReranker",
       "from srs_verify.context.reranker_stub import BgeReranker")]),
    # 原子化+打分
    (SRC / "context_linking/atomizer.py", PKG / "context/atomizer.py", []),
    (SRC / "context_linking/pair_scorers.py",
     PKG / "context/pair_scorers.py", []),
    # BGE客户端(模型目录改cwd相对, 与nli_local部署契约一致)
    (SRC / "common/bge_local.py", PKG / "context/bge_local.py",
     [("BASE = Path(__file__).resolve().parents[2]",
       "BASE = Path.cwd()  # 部署契约: models/与运行目录同级(见README)")]),
    # 提纯+覆盖检测+DEQ
    (SRC / "consistency/evidence_subtractor.py",
     PKG / "evidence_subtractor.py", []),
    (SRC / "consistency/evidence_purifier.py",
     PKG / "evidence_purifier.py",
     [("from algorithms.consistency.evidence_subtractor import",
       "from srs_verify.evidence_subtractor import"),
      ("from algorithms.consistency.deq_pipeline import",
       "from srs_verify.deq_pipeline import"),
      ("from algorithms.consistency.qa_models import",
       "from srs_verify.qa_models import"),
      ("from algorithms.consistency.qa_router import",
       "from srs_verify.qa_router import")]),
    (SRC / "consistency/coverage_detector.py",
     PKG / "coverage_detector.py", []),
    (SRC / "consistency/deq_pipeline.py", PKG / "deq_pipeline.py",
     [("from algorithms.consistency.answer_structure import",
       "from srs_verify.answer_structure import"),
      ("from algorithms.consistency.evidence_statements import",
       "from srs_verify.evidence_statements import"),
      ("from algorithms.consistency.qa_models import",
       "from srs_verify.qa_models import"),
      ("from algorithms.consistency.qa_router import",
       "from srs_verify.qa_router import")]),
]


def main() -> int:
    (PKG / "context").mkdir(parents=True, exist_ok=True)
    for src, dst, rules in COPIES:
        text = src.read_text(encoding="utf-8")
        for pat, rep in rules:
            if pat not in text and "reranker_stub" not in rep:
                print(f"  警告: {src.name} 未找到模式 {pat[:50]!r}")
            text = text.replace(pat, rep)
        dst.write_text(text, encoding="utf-8")
        print(f"  vendored: {dst.relative_to(PKG.parent)}")
    # __init__与精排stub
    init = PKG / "context/__init__.py"
    init.write_text(
        '"""上下文关联栈: O1-unit召回 + 原子化 + 打分(vendored from '
        'algorithms.context_linking)."""\n', encoding="utf-8")
    stub = PKG / "context/reranker_stub.py"
    stub.write_text(
        '"""精排器stub: 包内未vendor BGE-Reranker, 触发即降级直通."""\n'
        "\n\nclass BgeReranker:  # noqa: D101\n"
        "    def __init__(self) -> None:\n"
        "        raise ImportError(\n"
        "            'BgeReranker未vendor进srs_verify包; '\n"
        "            '召回走直通序(精排增益见repo内algorithms版本)')\n",
        encoding="utf-8")
    print("  created: context/__init__.py, context/reranker_stub.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
