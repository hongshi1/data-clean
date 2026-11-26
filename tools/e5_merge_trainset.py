"""Merge minimal pairs (fixed support rows) into the gated D3 training set.

E5 Step 3 data prep (100号spec): the 286 minimal-change pairs contribute
their FIXED answers as support-verdict training rows — attacking the
support-class gap (B's finding: Δmacro-F1 all in support class) and the
NIE class imbalance (A's finding: 63% NIE → 52%).

Usage:
    python tools/e5_merge_trainset.py \
        [--gated data/gjb_438c/distillation/d3_train_v3f_gated.jsonl] \
        [--pairs data/gjb_438c/distillation/e5_minimal_pairs_v1.jsonl] \
        [--out data/gjb_438c/distillation/d3_train_v4.jsonl]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
GATED = BASE / "data/gjb_438c/distillation/d3_train_v3f_gated.jsonl"
PAIRS = BASE / "data/gjb_438c/distillation/e5_minimal_pairs_v1.jsonl"
OUT = BASE / "data/gjb_438c/distillation/d3_train_v4.jsonl"

#: 训练脚本消费的字段（tools/train_d3_student.py: _user_message +
#: _target_message）——只保留这些+溯源字段，其余(quality/repairs)不进
_TRAIN_FIELDS = ("corpus", "instance_id", "question", "answer",
                 "evidence", "verdict", "issues")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fixed_row(pair: dict) -> dict:
    """最小变更对 → support训练行（fixed_answer, 空issues, 溯源标记）."""
    row = {k: pair[k] for k in _TRAIN_FIELDS if k in pair}
    row["instance_id"] = f"{pair['pair_id']}-fix"
    row["answer"] = pair["fixed_answer"]
    row["verdict"] = "support"
    row["issues"] = []
    row["orig_label"] = pair.get("orig_verdict", "refute")
    row["source"] = "minimal_pair_fix"
    return row


def main() -> None:
    sys = __import__("sys")
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--gated", type=Path, default=GATED)
    parser.add_argument("--pairs", type=Path, default=PAIRS)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--paired-only", action="store_true",
                        help="只保留原始refute侧在gated集内的配对(89对): "
                             "确保每条fixed(support)行都有其对照original("
                             "refute)行在训练集内。v3塌因: 197对只有"
                             "support侧, 模型学到'→support'表面模式")
    args = parser.parse_args()

    gated = load_jsonl(args.gated)
    pairs = load_jsonl(args.pairs)
    gated_ids = {r["instance_id"] for r in gated}

    existing_ids = {r["instance_id"] for r in gated}
    added, skipped = [], []
    for pair in pairs:
        row = fixed_row(pair)
        if row["instance_id"] in existing_ids:
            skipped.append(row["instance_id"])
            continue
        if not row.get("evidence") or not row.get("answer"):
            skipped.append(row["instance_id"])
            continue
        if args.paired_only and pair["instance_id"] not in gated_ids:
            skipped.append(row["instance_id"])
            continue
        added.append(row)

    merged = gated + added
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged)
        + "\n", encoding="utf-8")

    vd = Counter(r["verdict"] for r in merged)
    print(f"gated={len(gated)} pairs={len(pairs)} "
          f"added={len(added)} skipped={len(skipped)}")
    print(f"out={args.out} n={len(merged)} verdict_dist={dict(vd)}")
    before = Counter(r["verdict"] for r in gated)
    print(f"support share: {before.get('support', 0)}/{len(gated)}"
          f"={before.get('support', 0) / len(gated):.3f} -> "
          f"{vd.get('support', 0)}/{len(merged)}"
          f"={vd.get('support', 0) / len(merged):.3f}")


if __name__ == "__main__":
    main()
