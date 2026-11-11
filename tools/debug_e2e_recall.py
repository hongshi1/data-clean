"""Debug e2e recall: inspect hits and gold for the first QA instance."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.blackboard.hybrid_recall import HybridRecaller
from algorithms.consistency.eval_lib import load_frozen_qa
from tools.e2e_recall_verify import DOC, gold_block_set, hit_to_prefix_chunk_ids


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    records = load_frozen_qa()
    rec = records[0]
    gold = gold_block_set(rec)
    print(f"instance: {rec['instance_id']}")
    print(f"gold blocks: {sorted(gold)}")
    print(f"question: {rec['question'][:60]}")

    recaller = HybridRecaller()
    for query in (rec["question"],
                  rec["question"] + " " + rec["answer"][:200]):
        result = recaller.recall(query, doc=DOC, top_k=10)
        print(f"\nquery={query[:50]}...")
        for rank, hit in enumerate(result.get("hits", [])[:10], 1):
            blocks = hit_to_prefix_chunk_ids(hit)
            in_gold = "★" if blocks & gold else " "
            print(f" {in_gold} rank{rank} {hit.get('chunk_id', '')[-14:]} "
                  f"type={hit.get('type', '')} "
                  f"sec={str(hit.get('section', ''))[:12]} "
                  f"score={hit.get('rrf_score', 0):.4f} "
                  f"tier={hit.get('tier', '')}")
            print(f"      snippet: {str(hit.get('snippet', ''))[:60]}")


if __name__ == "__main__":
    main()
