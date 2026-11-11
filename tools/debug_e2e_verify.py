"""Debug e2e verification: per-instance verdicts vs silver (first N)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.blackboard.hybrid_recall import HybridRecaller
from algorithms.consistency.eval_lib import (
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule
from tools.e2e_recall_verify import DOC, build_request

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    records = load_frozen_qa()[:5]
    silver = load_silver_labels(SILVER)

    recaller = HybridRecaller()
    store_chunks = {}
    from algorithms.blackboard.evidence_store import EvidenceStore
    for cid, chunk in EvidenceStore()._chunk_by_id().items():
        store_chunks[cid] = str(chunk.get("text", ""))

    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)

    for rec in records:
        query = str(rec["question"]) + " " + str(rec["answer"])[:300]
        result = recaller.recall(query, doc=DOC, top_k=8)
        hits = [h for h in result.get("hits", [])
                if h.get("type") in ("text", "table")][:8]
        full_hits = [{**h, "snippet_full": store_chunks.get(
            str(h.get("chunk_id", "")), "")} for h in hits]
        request = build_request(rec, full_hits)
        res = module.verify(request)
        truth = silver.get(rec["instance_id"], "not_in_evidence")
        mark = "✓" if res.verdict == truth else "✗"
        print(f"{mark} {rec['instance_id']} truth={truth:16s} "
              f"pred={res.verdict:16s} n_ev={len(request.evidence)}")
        for ev in request.evidence[:3]:
            print(f"   ev[{ev.evidence_id[-2:]}] "
                  f"{ev.source_type:5s} {ev.text[:50]}")
        print(f"   methods: {[c.method for c in res.claim_results][:6]}")


if __name__ == "__main__":
    main()
