#!/usr/bin/env python3
"""启发式参数敏感性扫描: 语句预算/粒度界/平行表阈值.

对应文档: 81号. 目标: 把"拍的"参数升级为"校准的"(平坦性论证).

扫描1: max_statements(语句预算) × _MAX_ATOMIC_CHARS(粒度界)
  → 17违例评测集: statement模式提纯 → NLI直判refute查全
    + gold保留 + 平均语句数 → 平坦性曲线
扫描2: min_shared(平行表配对阈值)
  → tables.jsonl: 平行对数/findings数/doc10真冲突保留

用法: python tools/sweep_heuristics.py [--skip-nli]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import torch  # noqa: E402,F401 (顺序约束)

import algorithms.consistency.evidence_subtractor as es  # noqa: E402
from algorithms.consistency.evidence_subtractor import subtract  # noqa: E402

VIO = BASE / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl"
TABLES = BASE / "data/gjb_438c/structured_corpus_v1/tables.jsonl"
OUT = BASE / "data/gjb_438c/localization_gold/heuristic_sweep_v1.json"

TAU = 0.5
STM_GRID = [10, 15, 20, 25, 35, 50]
CHAR_GRID = [80, 120, 160, 200, 280]
SHARED_GRID = [1, 2, 3, 4]


def sweep_nli(records, nli) -> list[dict]:
    """扫描1: (max_statements × max_atomic_chars) → refute查全/gold/语句数."""
    rows: list[dict] = []
    orig_chars = es._MAX_ATOMIC_CHARS  # noqa: SLF001 — 实验扫描的模块级覆写
    try:
        for chars in CHAR_GRID:
            es._MAX_ATOMIC_CHARS = chars  # noqa: SLF001
            for stm in STM_GRID:
                n_refute = n_gold = n_all = n_stmts = 0
                for r in records:
                    pack = subtract(r["question"], r["answer"],
                                    r["evidence"], max_statements=stm)
                    premises = [s for k in pack["kept"]
                                for s in k["statements"]]
                    n_stmts += len(premises)
                    if premises:
                        probs = nli.predict(
                            [(p, r["answer"]) for p in premises])
                        if max(p.get("p_contra", 0.0)
                               for p in probs) > TAU:
                            n_refute += 1
                    kept_ids = {k["evidence_id"] for k in pack["kept"]}
                    gold = set(r["gold_evidence_refs"])
                    n_gold += len(gold & kept_ids)
                    n_all += len(gold)
                rows.append({
                    "max_chars": chars, "max_statements": stm,
                    "refute_recall": round(n_refute / len(records), 3),
                    "gold_retention": round(n_gold / max(n_all, 1), 3),
                    "stmts_per_inst": round(n_stmts / len(records), 1),
                    "nli_pairs": n_stmts,
                })
                print(f"  chars={chars:>3} stm={stm:>2} → "
                      f"refute={n_refute}/17 gold={n_gold}/35 "
                      f"stmts/inst={n_stmts / len(records):.1f}")
    finally:
        es._MAX_ATOMIC_CHARS = orig_chars  # noqa: SLF001
    return rows


def sweep_shared(tables) -> list[dict]:
    """扫描2: min_shared → 平行对/findings/doc10真冲突保留."""
    from algorithms.consistency.coverage_detector import (
        compare_tables,
        find_parallel_tables,
        table_scope_rows,
    )
    rows: list[dict] = []
    for ms in SHARED_GRID:
        pairs = find_parallel_tables(tables, min_shared=ms)
        findings = []
        for a, b, shared in pairs:
            findings.extend(compare_tables(a, b, shared))
        # doc10真冲突保留: 表83/84主频2.2vs2.5 + 分辨率1280vs1600
        t10 = [t for t in tables if t.get("doc_id") == "10"]
        scopes_83 = table_scope_rows(next(t for t in t10
                                          if t["section"] == "3.9.1"))
        scopes_84 = table_scope_rows(next(t for t in t10
                                          if t["section"] == "3.10.1"))
        real_kept = 0
        if any("2.2" in str(v) for s in scopes_83.values()
               for v in s.values()) and \
           any("2.5" in str(v) for s in scopes_84.values() for v in s.values()):
            real_kept = 1
        rows.append({
            "min_shared": ms, "n_pairs": len(pairs),
            "n_findings": len(findings),
            "doc10_real_kept": real_kept,
        })
        print(f"  min_shared={ms} → 平行对{len(pairs)} "
              f"findings{len(findings)} doc10真冲突保留={real_kept}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-nli", action="store_true")
    args = ap.parse_args()
    records = [json.loads(line) for line in VIO.open(encoding="utf-8")]

    print("== 扫描2: 平行表配对阈值(纯计算) ==")
    tables = [json.loads(line) for line in TABLES.open(encoding="utf-8")]
    shared_rows = sweep_shared(tables)

    nli_rows: list[dict] = []
    if not args.skip_nli:
        print("\n== 扫描1: 语句预算×粒度界(NLI直判) ==")
        from algorithms.consistency.nli_local import NliLocal
        nli = NliLocal("mdeberta")
        if nli.ensure() not in ("cuda", "gpu", "cpu"):
            print(f"NLI不可用: {nli.last_error}")
            return 1
        nli_rows = sweep_nli(records, nli)

    OUT.write_text(json.dumps({
        "tau": TAU, "stm_grid": STM_GRID, "char_grid": CHAR_GRID,
        "nli_sweep": nli_rows, "shared_sweep": shared_rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n结果已写入: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
