"""Check VIO-08 evidence completeness (closed-scope licensing)."""
from __future__ import annotations

import json
from pathlib import Path

VIO = (Path(__file__).resolve().parents[1]
       / "data/gjb_438c/localization_gold/violation_evalset_v1.jsonl")


def main() -> None:
    vio = {json.loads(line)["instance_id"]: json.loads(line)
           for line in VIO.read_text(encoding="utf-8").splitlines()
           if line.strip()}
    for iid in ("DOC04-VIO-08", "DOC04-VIO-16"):
        rec = vio[iid]
        print(f"== {iid}")
        for ev in rec["evidence"]:
            print(f'  {ev["evidence_id"]}: '
                  f'completeness={ev.get("completeness", "")} '
                  f'proof={str(ev.get("completeness_proof", ""))[:60]}')
        print(f"  gold: {rec['gold_evidence_refs']}")


if __name__ == "__main__":
    main()
