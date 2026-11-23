"""Replicate the agent eval counting to find the gold_hit bug."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def _chunk_to_block(chunk_id: str) -> str:
    pos = chunk_id.rfind("_T")
    if pos < 0:
        return ""
    tail = chunk_id[pos + 2:].split("_")[0]
    if not tail.isdigit():
        return ""
    return f"block-{int(tail):06d}"


def main() -> None:
    r = json.loads((BASE / "data/gjb_438c/distillation"
                    / "agent_scenario_v1.json").read_text(encoding="utf-8"))
    vio = [json.loads(line) for line in
           (BASE / "data/gjb_438c/localization_gold"
            / "violation_evalset_v1.jsonl").read_text(encoding="utf-8")
           .splitlines() if line.strip()]
    gold_hit = 0
    for rec, report in zip(vio, r["reports"]):
        gold_blocks = {str((ev.get("source_ref") or {}).get("block_id", ""))
                       for ev in rec["evidence"]
                       if str((ev.get("source_ref") or {}).get(
                           "block_id", "")).startswith("block-")}
        cited = {_chunk_to_block(e["block"])
                 for rr in report["inconsistencies"]
                 for e in rr["evidence"] if rr["evidence"]}
        cited.discard("")
        inter = cited & gold_blocks
        if gold_blocks and inter:
            gold_hit += 1
        if report["verdict"] == "refute" and not inter:
            print(f"  MISS {report['instance_id']}: "
                  f"cited={sorted(cited)[:3]} gold_n={len(gold_blocks)} "
                  f"locs={len(report['inconsistencies'])}")
    print(f"gold_hit replica: {gold_hit}")


if __name__ == "__main__":
    main()
