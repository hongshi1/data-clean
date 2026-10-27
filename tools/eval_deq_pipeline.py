"""Run DEQ-Pipe on 91 real QA pairs and measure evidence utilization."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.deq_pipeline import deq_pipeline  # noqa: E402
from tools.build_answer_mutation_candidates import request_from_dict  # noqa: E402

FROZEN = BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"
SILVER = (BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
           / "final_labels.jsonl")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def main() -> None:
    rows = read_jsonl(FROZEN)
    silver = {r["instance_id"]: r for r in read_jsonl(SILVER)}

    stats = {
        "total": len(rows),
        "original_evidence": 0,
        "gated_evidence": 0,
        "rejected_evidence": 0,
        "empty_after_gate": 0,
        "pairs_generated": 0,
    }
    gate_reductions = []
    silver_vs_gate = Counter()

    for row in rows:
        request = request_from_dict(row)
        result = deq_pipeline(
            question=request.question,
            answer=request.answer,
            evidence_blocks=request.evidence,
        )
        stats["original_evidence"] += result.original_count
        stats["gated_evidence"] += result.gated_count
        stats["rejected_evidence"] += (
            result.original_count - result.gated_count)
        stats["pairs_generated"] += len(result.aligned_pairs)
        if result.gated_count == 0:
            stats["empty_after_gate"] += 1
        gate_reductions.append(
            1 - result.gated_count / max(result.original_count, 1))

        verdict = silver.get(row["instance_id"], {}).get("final_verdict", "?")
        silver_vs_gate[f"{verdict}|gate={result.gated_count > 0}"] += 1

    avg_reduction = (
        sum(gate_reductions) / len(gate_reductions) if gate_reductions else 0
    )
    print(json.dumps({
        **stats,
        "avg_gate_reduction": round(avg_reduction, 4),
        "empty_after_gate_pct": round(
            stats["empty_after_gate"] / stats["total"] * 100, 1),
        "silver_vs_gate": dict(silver_vs_gate),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
