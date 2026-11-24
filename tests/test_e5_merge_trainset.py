"""Tests for tools/e5_merge_trainset.py (E5 Step 3 data prep)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.e5_merge_trainset import fixed_row, load_jsonl  # noqa: E402

BASE = Path(__file__).resolve().parents[1]
GATED = BASE / "data/gjb_438c/distillation/d3_train_v3f_gated.jsonl"
PAIRS = BASE / "data/gjb_438c/distillation/e5_minimal_pairs_v1.jsonl"
MERGED = BASE / "data/gjb_438c/distillation/d3_train_v4.jsonl"


def _pair_sample() -> dict:
    pairs = load_jsonl(PAIRS)
    assert pairs, "minimal pairs file missing"
    return pairs[0]


def test_fixed_row_shape() -> None:
    pair = _pair_sample()
    row = fixed_row(pair)
    # training-script consumed fields present
    for field in ("corpus", "instance_id", "question", "answer",
                  "evidence", "verdict", "issues"):
        assert field in row, field
    assert row["verdict"] == "support"
    assert row["issues"] == []
    assert row["answer"] == pair["fixed_answer"]
    assert row["instance_id"] == f"{pair['pair_id']}-fix"
    assert row["orig_label"] == pair["orig_verdict"]
    assert row["source"] == "minimal_pair_fix"


def test_fixed_row_consumable_by_train_script() -> None:
    """merge产物必须能被train_d3_student的encode路径消费(字段齐全)."""
    sys.path.insert(0, str(BASE / "tools"))
    from train_d3_student import _target_message  # noqa: E402
    row = fixed_row(_pair_sample())
    target = json.loads(_target_message(row))
    assert target["verdict"] == "support"
    assert target["issues"] == []


def test_merged_file_counts() -> None:
    merged = load_jsonl(MERGED)
    gated = load_jsonl(GATED)
    pairs = load_jsonl(PAIRS)
    assert len(merged) == len(gated) + len(pairs)
    # 前段与gated逐行同序
    assert [r["instance_id"] for r in merged[:len(gated)]] \
        == [r["instance_id"] for r in gated]
    # 追加段全部是fix行
    tail = merged[len(gated):]
    assert all(r.get("source") == "minimal_pair_fix" for r in tail)
    assert all(r["verdict"] == "support" for r in tail)


def test_merged_verdict_distribution() -> None:
    merged = load_jsonl(MERGED)
    counts = {"not_in_evidence": 0, "refute": 0, "support": 0}
    for r in merged:
        counts[r["verdict"]] += 1
    # 1336行分布(843/219/274) + 286 support
    assert counts == {"not_in_evidence": 843, "refute": 219,
                      "support": 560}
