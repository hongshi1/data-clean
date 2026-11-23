"""Print the newest check report's violation entry (readability check)."""
from pathlib import Path
import json

states = sorted(
    (BASE := Path("data/agent_checks")).glob("*/state.json"),
    key=lambda p: p.stat().st_mtime)
latest = states[-1]
d = json.loads(latest.read_text(encoding="utf-8"))
rep = d.get("report") or {}
samples = rep.get("samples") or []
print("check:", latest.parent.name, "| status:", d.get("status"),
      "| samples:", len(samples))
if not samples:
    print("报告尚无samples(任务未done)")
else:
    s0 = samples[0]
    print("=== 可读性检查 ===")
    print("question:", s0["question"][:60])
    print("answer:", s0["answer"][:60])
    print("consistency_result:", s0["consistency_result"])
    v = s0["violations"][0]
    print("item:", v["item_id"], v["item_name"])
    print("answer_context:", v["answer_context"])
    print("affected_answer:", v["affected_answer"])
    print("---description全文---")
    print(v["description"])
    print("---root_cause---")
    print(json.dumps(v["root_cause"], ensure_ascii=False))
