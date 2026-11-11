"""Inspect frozen QA evidence structure for retrieval gold mapping."""
from __future__ import annotations

import json
from pathlib import Path

QA = (Path(__file__).resolve().parents[1]
      / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")


def main() -> None:
    recs = [json.loads(line) for line in
            QA.read_text(encoding="utf-8").splitlines() if line.strip()]
    rec = recs[0]
    print(f"instance: {rec['instance_id']}")
    print(f"n evidence: {len(rec['evidence'])}")
    for ev in rec["evidence"][:4]:
        ref = ev["source_ref"]
        print(f"  eid={ev['evidence_id']} type={ev['source_type']} "
              f"doc={ref.get('doc_id', '')} "
              f"sec={str(ref.get('section', ''))[:20]} "
              f"block={ref.get('block_id', '')} "
              f"row={ref.get('row_id', '')}")
        print(f"    text: {ev['text'][:70]}")
    n_ev = [len(r["evidence"]) for r in recs]
    print(f"evidence per instance: min={min(n_ev)} max={max(n_ev)} "
          f"mean={sum(n_ev) / len(n_ev):.1f}")
    ids = {ev["evidence_id"] for r in recs for ev in r["evidence"]}
    print(f"distinct evidence ids: {len(ids)}")
    print("sample ids:", sorted(ids)[:8])


if __name__ == "__main__":
    main()
