"""E3b-union diagnostic: recall ∪ frozen evidence, isolate failure mode.

E3b (pure recall) agreement was 8/14 on the S/R instances. Two possible
causes: (a) the recall did not surface the decisive blocks (recall
insufficiency), or (b) extra recalled blocks pollute the verification
(evidence pollution). Feeding the UNION (recall top-8 + all frozen
evidence blocks) separates them:

  union ≈ frozen baseline (14/14)  → (a): recall insufficiency
  union ≈ pure recall (8/14)       → (b): pollution dominates
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.blackboard.hybrid_recall import HybridRecaller  # noqa: E402
from algorithms.consistency.eval_lib import (  # noqa: E402
    load_frozen_qa,
    load_silver_labels,
)
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402
from tools.e2e_recall_verify import (  # noqa: E402
    DOC,
    build_request,
)

SILVER = (BASE / "data/gjb_438c/runs/"
          "review_qa_with_glm53_582b51e5_20261021_145212/final_labels.jsonl")
K = 8


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    silver = load_silver_labels(SILVER)
    qa = load_frozen_qa()
    sr_recs = [r for r in qa
               if silver.get(r["instance_id"], "not_in_evidence")
               in ("support", "refute")]

    from algorithms.blackboard.evidence_store import EvidenceStore
    full = {cid: str(chunk.get("text", ""))
            for cid, chunk in EvidenceStore()._chunk_by_id().items()}

    recaller = HybridRecaller()
    recaller.recall("数据库访问", doc=DOC, top_k=5)
    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)

    agree = 0
    details: list[str] = []
    for rec in sr_recs:
        iid = str(rec["instance_id"])
        query = f"{rec['question']} {str(rec['answer'])[:400]}"
        result = recaller.recall(query, doc=DOC, top_k=K)
        hits = [h for h in result.get("hits", [])
                if h.get("type") in ("text", "table")][:K]
        # 冻结证据块 → chunk形式, 追加在召回之后(去重按block)
        seen_blocks = set()
        for hit in hits:
            cid = str(hit.get("chunk_id", ""))
            pos = cid.rfind("_T")
            if pos >= 0:
                seen_blocks.add(cid[pos + 2:].split("_")[0])
        union_hits = list(hits)
        for ev in rec["evidence"]:
            block = str(ev["source_ref"].get("block_id", ""))
            num = block.replace("block-", "")
            if not num.isdigit() or num in seen_blocks:
                continue
            chunk_cid = f"{DOC}_T{int(num):04d}"
            text = full.get(chunk_cid) or str(ev["text"])
            union_hits.append({
                "chunk_id": chunk_cid,
                "type": str(ev["source_type"]),
                "section": str(ev["source_ref"].get("section", "")),
                "doc": DOC,
                "snippet_full": text,
            })
        request = build_request(rec, iid, str(rec["question"]),
                                str(rec["answer"]), union_hits, full)
        res = module.verify(request)
        ok = res.verdict == silver.get(iid)
        agree += ok
        details.append(f"{'✓' if ok else '✗'} {iid} "
                       f"truth={silver.get(iid):8s} "
                       f"pred={res.verdict:8s} "
                       f"n_ev={len(union_hits)}")
    print(f"E3b-union SR-{len(sr_recs)}: agreement {agree}/{len(sr_recs)} "
          f"({agree / len(sr_recs) * 100:.0f}%)")
    print("对照: 纯召回 8/14 (57%), 冻结证据 = 14/14 (定义)")
    for line in details:
        print(f"   {line}")


if __name__ == "__main__":
    main()
