"""Compare S1QA-024 vs S1QA-028 evidence composition to calibrate E1 refutes."""
from __future__ import annotations

import json

FROZEN = "data/gjb_438c/qa_frozen/scene1_qa_frozen_v1.jsonl"


def main() -> None:
    frozen = {
        json.loads(line)["instance_id"]: json.loads(line)
        for line in open(FROZEN, encoding="utf-8")
    }
    for qid in ("S1QA-024", "S1QA-028"):
        rec = frozen[qid]
        print("====", qid, "evidence count:", len(rec["evidence"]))
        for ev in rec["evidence"]:
            text = ev["text"].replace("\n", " ")
            has_conn = "连接错误" in text or "连接失败" in text
            has_e1 = "异常流" in text
            scope = ev.get("scope_id", "")[-30:]
            print(f"  {ev['evidence_id'][-14:]} scope={scope}"
                  f" conn={has_conn} E1={has_e1} len={len(text)}")


if __name__ == "__main__":
    main()
