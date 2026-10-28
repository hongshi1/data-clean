#!/usr/bin/env python3
"""分析atom_candidates_v1候选池构成."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

p = Path("data/gjb_438c/atom_candidates_v1/candidates.jsonl")
pairs = [json.loads(line) for line in p.open(encoding="utf-8")]
print("冲突候选总数:", len(pairs))
print()
print("按参数分布:")
for param, n in Counter(x["param"] for x in pairs).most_common():
    strong = sum(1 for x in pairs
                 if x["param"] == param and x["decision"] == "conflict_same_scope")
    print(f"  {param:20s} {n:5d} (强{strong})")
print()
print("按文档分布(前8):",
      dict(Counter(x["doc_id"] for x in pairs).most_common(8)))
print()
print("=== doc02 response_time全部候选(已知真实冲突) ===")
for x in pairs:
    if x["doc_id"] == "02" and x["param"] == "response_time":
        left, right = x["left"], x["right"]
        print(f"  {left['scope_hint']}{left['param_surface']}"
              f"{left['operator']}{left['value']}{left['unit']}@{left['section']}"
              f"  vs  {right['operator']}{right['value']}{right['unit']}"
              f"@{right['section']}  -> {x['decision']}")
print()
same_sec = [x for x in pairs
            if x["same_section"] and x["decision"] == "conflict_same_scope"]
print("=== 同章节同作用域冲突(最强嫌疑) ===")
print("数量:", len(same_sec))
for x in same_sec[:5]:
    left = x["left"]
    print(f"  doc{x['doc_id']} {x['param']} @{left['section']}")
    print(f"    L: {left['context'][:70]}")
    print(f"    R: {x['right']['context'][:70]}")
