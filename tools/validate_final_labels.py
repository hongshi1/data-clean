from __future__ import annotations

import collections
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE / "data/gjb_438c/runs/review_qa_with_glm53_582b51e5_20261021_145212"
frozen = {
    json.loads(line)["instance_id"]: json.loads(line)
    for line in (BASE / "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl")
    .read_text(encoding="utf-8").splitlines() if line.strip()
}
final = [json.loads(line) for line in (ROOT / "final_labels.jsonl")
         .read_text(encoding="utf-8").splitlines() if line.strip()]
assert len(final) == 91 and len({x["instance_id"] for x in final}) == 91
assert all(x["status"] == "final_glm53_reviewed" and x["final_model"] == "glm-5.3"
           for x in final)
bad_refs: list[str] = []
bad_agg: list[str] = []
for row in final:
    allowed = {e["evidence_id"] for e in frozen[row["instance_id"]]["evidence"]}
    verdicts = {c["verdict"] for c in row["claims"]}
    for claim in row["claims"]:
        if not set(claim.get("evidence_refs", [])) <= allowed:
            bad_refs.append(row["instance_id"])
    expected = ("refute" if "refute" in verdicts
                else "not_in_evidence" if "not_in_evidence" in verdicts
                else "support")
    if expected != row["final_verdict"]:
        bad_agg.append(row["instance_id"])
assert not bad_refs, bad_refs
assert not bad_agg, bad_agg
print("91/91 glm-5.3 final labels; refs OK; aggregation OK")
print("final_dist", collections.Counter(x["final_verdict"] for x in final))
print("modes", collections.Counter(str(x.get("thinking")) for x in final))
