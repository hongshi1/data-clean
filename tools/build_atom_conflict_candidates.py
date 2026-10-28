#!/usr/bin/env python3
"""S1原子化+同参配对全量运行: claims→四槽原子→冲突候选池.

对应文档: 65号(S1可行性验证) / 66号(FS形式化).
产出: data/gjb_438c/atom_candidates_v1/{atoms,candidates}.jsonl + summary.json
用法: python tools/build_atom_conflict_candidates.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from algorithms.context_linking.atomizer import (  # noqa: E402
    Atom, AtomPair, atomize_claim, block_by_param, pair_groups,
)


def load_surface_map(kb_path: Path) -> dict[str, str]:
    """GJB词典→表面形式映射(canon+中文同义词; 表面形式为空跳过)."""
    kb = json.loads(kb_path.read_text(encoding="utf-8"))
    surface: dict[str, str] = {}
    for pname, info in kb.get("param_dictionary", {}).items():
        canon = str(info.get("canonical_cn", "")).strip()
        if canon:
            surface[canon] = pname
        for syn in info.get("synonyms_cn", []):
            syn = str(syn).strip()
            if syn:
                surface[syn] = pname
    return surface


def iter_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def atom_to_row(a: Atom) -> dict:
    return {
        "param": a.param, "param_surface": a.param_surface,
        "operator": a.operator, "value": a.value, "unit": a.unit,
        "scope_hint": a.scope_hint, "binding_status": a.binding_status,
        "quantity_hygiene": a.quantity_hygiene,
        "claim_id": a.claim_id, "doc_id": a.doc_id, "section": a.section,
        "context": a.context,
    }


def pair_to_row(p: AtomPair) -> dict:
    return {
        "doc_id": p.left.doc_id, "param": p.left.param,
        "decision": p.decision, "gap": p.gap,
        "same_section": p.same_section,
        "left": atom_to_row(p.left), "right": atom_to_row(p.right),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", default="data/gjb_438c/structured_corpus_v1")
    ap.add_argument("--kb", default="knowledge/srs_kb.json")
    ap.add_argument("--out", default="data/gjb_438c/atom_candidates_v1")
    args = ap.parse_args()

    corpus_dir = BASE / args.corpus
    out_dir = BASE / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    surface_map = load_surface_map(BASE / args.kb)
    print(f"表面形式映射: {len(surface_map)}条 "
          f"(覆盖{len(set(surface_map.values()))}参数)")

    claims_path = corpus_dir / "claims.jsonl"
    n_claims = 0
    atoms: list[Atom] = []
    for claim in iter_jsonl(claims_path):
        n_claims += 1
        atoms.extend(atomize_claim(claim, surface_map))
    print(f"claims: {n_claims} → atoms: {len(atoms)} "
          f"({len(atoms) / max(n_claims, 1) * 100:.1f}原子/百claim)")

    groups = block_by_param(atoms)
    pairs = pair_groups(groups)
    by_decision = Counter(p.decision for p in pairs)
    hygiene = Counter(a.quantity_hygiene for a in atoms)
    per_doc_conflict = Counter(
        p.left.doc_id for p in pairs if p.decision.startswith("conflict"))

    write_jsonl(out_dir / "atoms.jsonl", [atom_to_row(a) for a in atoms])
    conflict_rows = [pair_to_row(p) for p in pairs
                     if p.decision.startswith("conflict")]
    write_jsonl(out_dir / "candidates.jsonl", conflict_rows)

    summary = {
        "n_claims": n_claims,
        "n_atoms": len(atoms),
        "atoms_per_100_claims": round(len(atoms) / max(n_claims, 1) * 100, 1),
        "n_groups": len(groups),
        "n_pairs": len(pairs),
        "pairs_by_decision": dict(by_decision),
        "atom_hygiene": dict(hygiene),
        "conflicts_per_doc": dict(sorted(per_doc_conflict.items())),
        "reduction_ratio": round(1 - len(atoms) / max(n_claims, 1), 4),
        "surface_map_size": len(surface_map),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"groups: {len(groups)} | pairs: {len(pairs)}")
    print("决策分布:", dict(by_decision))
    print("原子卫生:", dict(hygiene))
    print(f"冲突候选已写入: {out_dir / 'candidates.jsonl'}")

    # 展示强候选样例(同作用域冲突)
    strong = [p for p in pairs if p.decision == "conflict_same_scope"]
    print(f"\n=== 同作用域冲突候选(强) {len(strong)}对, 前5例 ===")
    for p in strong[:5]:
        print(f"[doc{p.left.doc_id} {p.left.param}] "
              f"{p.left.scope_hint}{p.left.param_surface}"
              f"{p.left.operator}{p.left.value}{p.left.unit} "
              f"({p.left.section})  vs  "
              f"{p.right.scope_hint}{p.right.param_surface}"
              f"{p.right.operator}{p.right.value}{p.right.unit} "
              f"({p.right.section})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
