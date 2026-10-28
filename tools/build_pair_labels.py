#!/usr/bin/env python3
"""冲突候选人工标注采样: 强候选全取 + 弱/未知分层抽样.

对应文档: 68号(打分策略对比实验的评测集构建).
产出: data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl
      (含pair_id, 供人工标签文件labels_v1.jsonl按id合并)
用法: python tools/build_pair_labels.py [--n-weak 24] [--n-unknown 12]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

CAND_PATH = BASE / "data/gjb_438c/atom_candidates_v1/candidates.jsonl"
OUT_PATH = BASE / "data/gjb_438c/atom_candidates_v1/pairs_to_label.jsonl"


def pair_id(row: dict) -> str:
    key = "|".join([
        row["doc_id"], row["param"], row["decision"],
        row["left"]["claim_id"], row["right"]["claim_id"],
        str(row["left"]["value"]), str(row["right"]["value"]),
        row["left"]["section"], row["right"]["section"],
    ])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-weak", type=int, default=24)
    ap.add_argument("--n-unknown", type=int, default=12)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = [json.loads(line) for line in CAND_PATH.open(encoding="utf-8")]
    strong = [r for r in rows if r["decision"] == "conflict_same_scope"]
    weak = [r for r in rows if r["decision"] == "conflict_scope_diff"]
    unknown = [r for r in rows if r["decision"] == "conflict_scope_unknown"]

    rng = random.Random(args.seed)
    sample = strong + rng.sample(weak, min(args.n_weak, len(weak))) \
        + rng.sample(unknown, min(args.n_unknown, len(unknown)))

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in sample:
            f.write(json.dumps({
                "pair_id": pair_id(r), "doc_id": r["doc_id"],
                "param": r["param"], "decision": r["decision"],
                "same_section": r["same_section"],
                "left": r["left"], "right": r["right"],
            }, ensure_ascii=False) + "\n")

    print(f"采样: 强{len(strong)} + 弱{min(args.n_weak, len(weak))}"
          f"/{len(weak)} + 未知{min(args.n_unknown, len(unknown))}"
          f"/{len(unknown)} = {len(sample)}对 → {OUT_PATH.name}")
    print()
    for i, r in enumerate(sample, 1):
        lf, rt = r["left"], r["right"]
        print(f"#{i:02d} [{r['doc_id']} {r['param']} {r['decision']}"
              f"{' 同节' if r['same_section'] else ''}]")
        print(f"  L@{lf['section']}: {lf['context'][:88]}")
        print(f"  R@{rt['section']}: {rt['context'][:88]}")
        print(f"  L值={lf['value']}{lf['unit']} R值={rt['value']}{rt['unit']}"
              f" scope={lf['scope_hint'][:8]!r}/{rt['scope_hint'][:8]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
