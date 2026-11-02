#!/usr/bin/env python3
"""表格行原子化全量运行: tables.jsonl → 表源原子 → 冲突候选 + 与claims源对账.

对应文档: 79号(表格通道原子化). 输出:
  data/gjb_438c/atom_candidates_v1/table_atoms.jsonl
  data/gjb_438c/atom_candidates_v1/table_candidates.jsonl + summary对比
用法: python tools/build_table_atoms.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_linking.atomizer import (  # noqa: E402
    Atom, atomize_tables, block_by_param, pair_groups,
)
from tools.build_atom_conflict_candidates import load_surface_map  # noqa: E402


def atom_to_row(a: Atom) -> dict:
    return {
        "param": a.param, "param_surface": a.param_surface,
        "operator": a.operator, "value": a.value, "unit": a.unit,
        "scope_hint": a.scope_hint, "claim_id": a.claim_id,
        "doc_id": a.doc_id, "section": a.section, "context": a.context,
    }


def main() -> int:
    tables = [json.loads(line) for line in
              (BASE / "data/gjb_438c/structured_corpus_v1/tables.jsonl")
              .open(encoding="utf-8")]
    surface_map = load_surface_map(BASE / "knowledge/srs_kb.json")
    atoms = atomize_tables(tables, surface_map)
    print(f"tables: {len(tables)} → 表源原子: {len(atoms)}")

    groups = block_by_param(atoms)
    pairs = pair_groups(groups)
    by_decision = Counter(p.decision for p in pairs)
    print(f"groups: {len(groups)} | pairs: {len(pairs)}")
    print("决策分布:", dict(by_decision))

    out_dir = BASE / "data/gjb_438c/atom_candidates_v1"
    with (out_dir / "table_atoms.jsonl").open("w", encoding="utf-8") as f:
        for a in atoms:
            f.write(json.dumps(atom_to_row(a), ensure_ascii=False) + "\n")

    def pair_to_row(p) -> dict:
        return {
            "doc_id": p.left.doc_id, "param": p.left.param,
            "decision": p.decision, "gap": p.gap,
            "same_section": p.same_section,
            "left": atom_to_row(p.left), "right": atom_to_row(p.right),
        }

    conflict_pairs = [p for p in pairs if p.decision.startswith("conflict")]
    conflict = [pair_to_row(p) for p in conflict_pairs]
    with (out_dir / "table_candidates.jsonl").open("w", encoding="utf-8") as f:
        for row in conflict:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # 与claims源候选对账: 同(doc,param,左值,右值)键的重叠
    claims_conf = [json.loads(line) for line in
                   (out_dir / "candidates.jsonl").open(encoding="utf-8")]

    def key(doc, param, lv, rv):
        return (doc, param, round(float(lv), 3), round(float(rv), 3))

    claims_keys = {key(c["doc_id"], c["param"],
                       c["left"]["value"], c["right"]["value"])
                   for c in claims_conf}
    table_keys = {key(c["doc_id"], c["param"],
                      c["left"]["value"], c["right"]["value"])
                  for c in conflict}
    overlap = claims_keys & table_keys
    new_only = table_keys - claims_keys
    print(f"\n对账: 表源冲突{len(table_keys)}键 vs claims源"
          f"{len(claims_keys)}键")
    print(f"  重叠: {len(overlap)} | 表源独有: {len(new_only)}")

    strong = [p for p in conflict_pairs
              if p.decision == "conflict_same_scope"]
    print(f"\n=== 表源强候选(同作用域) {len(strong)}对, 前5例 ===")
    for p in strong[:5]:
        print(f"  [doc{p.left.doc_id} {p.left.param}] "
              f"{p.left.scope_hint}{p.left.param_surface}"
              f"{p.left.operator}{p.left.value}{p.left.unit}"
              f"({p.left.section}) vs {p.right.operator}"
              f"{p.right.value}{p.right.unit}({p.right.section})")

    summary = {
        "n_tables": len(tables), "n_atoms": len(atoms),
        "n_groups": len(groups), "n_pairs": len(pairs),
        "pairs_by_decision": dict(by_decision),
        "n_conflict": len(conflict),
        "claims_keys": len(claims_keys), "table_keys": len(table_keys),
        "overlap": len(overlap), "table_only": len(new_only),
    }
    (out_dir / "table_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\n结果已写入: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
