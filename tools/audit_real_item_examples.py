"""Extract real per-item examples from the official reference dataset.

For each of the 40 taxonomy items, collect the QA rows whose silver claims
carry that item (by GPT check_items or question routing), with evidence
text excerpts and rationale — the raw material for scenario curation.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from algorithms.consistency.qa_router import route_question  # noqa: E402

REF = BASE / "data/gjb_438c/qa_frozen/scene1_official_reference_v1.jsonl"
GPT = (BASE / "data/gjb_438c/runs/annotate_frozen_qa_dual_llm_72379ff3_20261021_122221"
       / "raw_gpt5_6_sol.jsonl")

ALL_ITEMS = ([f"TERM-{i:02d}" for i in range(1, 9)]
             + [f"PARAM-{i:02d}" for i in range(1, 11)]
             + [f"LOGIC-{i:02d}" for i in range(1, 12)]
             + [f"GJB-{i:02d}" for i in range(1, 12)])


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def main() -> None:
    ref = {row["instance_id"]: row for row in read_jsonl(REF)}
    gpt = {row["instance_id"]: row for row in read_jsonl(GPT)}

    item_rows: dict[str, list] = defaultdict(list)
    for instance_id, record in ref.items():
        routed = route_question(record["official_alpaca"]["instruction"])
        gpt_items = set()
        for claim in gpt.get(instance_id, {}).get("claims", []):
            gpt_items.update(
                item for item in claim.get("check_items", [])
                if item in ALL_ITEMS)
        for item in sorted(gpt_items | set(routed)):
            evidence_by_id = {e["evidence_id"]: e for e in record["evidence"]}
            claims = [claim for claim in record["silver_label"]["claims"]
                      if claim.get("verdict") in ("refute", "support")]
            item_rows[item].append({
                "instance_id": instance_id,
                "question": record["official_alpaca"]["instruction"][:60],
                "silver": record["silver_label"]["final_verdict"],
                "n_evidence": len(record["evidence"]),
                "decisive_claims": [
                    {
                        "verdict": claim["verdict"],
                        "text": claim["claim_text"][:70],
                        "refs": claim.get("evidence_refs", [])[:2],
                        "evidence_excerpt": evidence_by_id[
                            claim["evidence_refs"][0]]["text"][:90]
                        if claim.get("evidence_refs")
                        and claim["evidence_refs"][0] in evidence_by_id else "",
                        "rationale": claim.get("rationale", "")[:110],
                    }
                    for claim in claims
                ],
            })

    for item in ALL_ITEMS:
        rows = item_rows.get(item, [])
        refutes = [r for r in rows if r["silver"] == "refute"]
        supports = [r for r in rows if r["silver"] == "support"]
        nies = [r for r in rows if r["silver"] == "not_in_evidence"]
        print(f"== {item}: rows={len(rows)} R={len(refutes)} S={len(supports)} N={len(nies)}")
        for kind, bucket in (("R", refutes[:1]), ("S", supports[:1])):
            for row in bucket:
                print(f"  [{kind}] {row['instance_id']} Q={row['question']}")
                for claim in row["decisive_claims"][:1]:
                    print(f"       A: {claim['text']}")
                    print(f"       E: {claim['evidence_excerpt']}")
                    print(f"       why: {claim['rationale']}")


if __name__ == "__main__":
    main()
