"""Inspect crossdoc teacher refute labels for sanity."""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path("data/gjb_438c/distillation/teacher_labels_crossdoc.jsonl")


def main() -> None:
    lines = [json.loads(line) for line in
             PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    refutes = [rec for rec in lines if rec["teacher_verdict"] == "refute"]
    print(f"refute claims: {len(refutes)}")
    for rec in refutes[:8]:
        print(f"--- {rec['instance_id']} "
              f"(conf={rec['teacher_confidence']})")
        print(f"  claim: {rec['claim_text'][:70]}")
        print(f"  rationale: {rec['teacher_rationale'][:110]}")


if __name__ == "__main__":
    main()
