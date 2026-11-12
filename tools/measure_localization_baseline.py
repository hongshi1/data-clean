"""Localization quality on violations-17 via the new
VerificationResult.localizations field (block-level gold hit rate)."""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import json  # noqa: E402

from algorithms.consistency.eval_lib import build_qa_input  # noqa: E402
from algorithms.consistency.qa_module import QAConsistencyModule  # noqa: E402

VIO = (BASE / "data/gjb_438c/localization_gold"
       / "violation_evalset_v1.jsonl")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    vio = [json.loads(line) for line in
           VIO.read_text(encoding="utf-8").splitlines() if line.strip()]
    module = QAConsistencyModule(
        use_experts=True, use_nli_residual=True,
        nli_model_path="models/nli/distilled_v1", nli_gate=0.8)

    n_detected = 0
    n_localized = 0
    n_hit = 0
    n_statement_level = 0
    for rec in vio:
        req = build_qa_input(rec)
        res = module.verify(req)
        ev_by_id = {ev.evidence_id: ev for ev in req.evidence}
        gold_blocks: set[str] = set()
        for ref in rec.get("gold_evidence_refs") or []:
            ev = ev_by_id.get(str(ref))
            if ev is not None and ev.source_ref.block_id:
                gold_blocks.add(str(ev.source_ref.block_id))
        if res.verdict != "refute":
            continue
        n_detected += 1
        cited_blocks: set[str] = set()
        for loc in res.localizations:
            for ev_loc in loc.evidence:
                if ev_loc.block_id:
                    cited_blocks.add(ev_loc.block_id)
                if ev_loc.row_index >= 0:
                    n_statement_level += 1
        if cited_blocks:
            n_localized += 1
        if gold_blocks and (cited_blocks & gold_blocks):
            n_hit += 1
        mark = "✓" if (cited_blocks & gold_blocks) else "✗"
        print(f"{rec['instance_id']}: locs={len(res.localizations)} "
              f"cited={sorted(cited_blocks)} hit={mark}")
    print(f"\n检出 {n_detected}/17 | 有定位 {n_localized} | "
          f"块级命中gold {n_hit}/{n_detected} | "
          f"语句级定位引用 {n_statement_level}")


if __name__ == "__main__":
    main()
